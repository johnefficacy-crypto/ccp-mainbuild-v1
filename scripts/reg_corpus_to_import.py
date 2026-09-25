#!/usr/bin/env python3
r"""REG-CORPUS-03 — authored corpus JSON → the bulk-import payload.

Input:  ``workbench/corpus/reg/out/REG-CORPUS-*.json`` (reglib schema) plus a
        topics export (``--topics``) and the REG-FACTCHECK-1 results CSV.
Output: one JSON file per batch under ``--out``, each a list of rows that
        ``app/backend/app/admin/mock_import.py`` accepts after REG-CORPUS-02
        (#1216). Upload it to ``POST /api/admin/mocks/questions/import/dry-run``,
        then commit the returned token.

NO DATABASE ACCESS. ``microtopic_slug → topic_id`` comes only from the topics
export, a CSV with header ``id,slug,level,parent_topic_id,subject_id``
(``subject_id`` is needed because a mapped import must carry both ids).

Every row: ``exam_id`` absent (NULL — authored rows are scoped through
``topics.metadata.exams``), ``source_kind='authored'``, difficulty from the
JSON, and the importer writes ``reviewer_status='draft'`` unconditionally.

Fails loudly (exit 1, nothing written) on: a slug outside the corpus
catalogue (``lists/*.tsv``), a catalogue slug missing from the topics export
or whose parent topic is missing from it, a duplicate import fingerprint
within the run, and a case set whose stems do not share a stimulus.

    python scripts/reg_corpus_to_import.py --topics topics.csv --dry-run
    python scripts/reg_corpus_to_import.py --topics topics.csv \
        --batch REG-CORPUS-CST --batch REG-CORPUS-CST-PILOT
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "workbench" / "corpus" / "reg"
CORPUS_DIR = REG / "out"
LISTS_DIR = REG / "lists"
FACTCHECK_CSV = REG / "factcheck" / "REG-FACTCHECK-1_results.csv"
DEFAULT_OUT = REG / "import"
CORPUS_VERSION = "v1.1"
FACTCHECK_VERDICTS = ("confirmed", "fix_needed", "wrong_key")
NOT_FLAGGED = "not_flagged"

sys.path.insert(0, str(ROOT / "app" / "backend"))
from app.admin.mock_import import _parse_row  # noqa: E402 — the importer's own parser/fingerprint


class CorpusError(ValueError):
    pass


# ── loading ────────────────────────────────────────────────────────────────────

def load_corpus(corpus_dir: Path = CORPUS_DIR, batches: list[str] | None = None) -> dict[str, list[dict]]:
    """``{batch: [question, ...]}`` in file order, optionally restricted to ``batches``."""
    found: dict[str, list[dict]] = {}
    for path in sorted(corpus_dir.glob("REG-CORPUS-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        found[data["batch"]] = data["questions"]
    if batches:
        unknown = sorted(set(batches) - set(found))
        if unknown:
            raise CorpusError(f"unknown batch(es): {unknown}; have {sorted(found)}")
        found = {b: found[b] for b in found if b in batches}
    return found


def load_catalogue(lists_dir: Path = LISTS_DIR) -> set[str]:
    slugs: set[str] = set()
    for path in lists_dir.glob("*.tsv"):
        with path.open(encoding="utf-8") as f:
            slugs.update(r["slug"] for r in csv.DictReader(f, delimiter="\t") if r.get("slug"))
    return slugs


def load_factcheck(path: Path = FACTCHECK_CSV) -> dict[str, str]:
    with path.open(encoding="utf-8") as f:
        out = {r["id"]: r["verdict"].strip() for r in csv.DictReader(f)}
    bad = {v for v in out.values() if v not in FACTCHECK_VERDICTS}
    if bad:
        raise CorpusError(f"factcheck CSV has unknown verdict(s): {sorted(bad)}")
    return out


AMBIGUOUS = "__ambiguous__"


def load_topics(path: Path) -> dict[str, dict]:
    """``{slug: row}`` from the topics export. Slugs are unique only per
    (subject, parent), so a slug exported twice maps to ``{AMBIGUOUS: n}`` and
    fails only if a corpus row uses it."""
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        need = {"id", "slug", "level", "parent_topic_id", "subject_id"}
        missing = need - set(reader.fieldnames or [])
        if missing:
            raise CorpusError(f"topics export {path} lacks column(s) {sorted(missing)}")
        rows = list(reader)
    counts = Counter(r["slug"] for r in rows)
    by_slug: dict[str, dict] = {}
    for r in rows:
        slug = r["slug"]
        if counts[slug] > 1:
            entry = by_slug.setdefault(slug, {AMBIGUOUS: counts[slug], "ids": []})
            entry["ids"].append((r.get("id") or "").strip())
        else:
            by_slug[slug] = {k: (r.get(k) or "").strip() or None for k in need}
    return by_slug


def load_only_ids(path: Path) -> set[str]:
    return {
        line.strip() for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


# ── case sets ──────────────────────────────────────────────────────────────────

def _common_prefix(texts: list[str]) -> str:
    first, last = min(texts), max(texts)
    n = 0
    while n < min(len(first), len(last)) and first[n] == last[n]:
        n += 1
    return first[:n]


def case_splits(questions: list[dict]) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """Split each case set's shared stimulus from its stems.

    A case set is the rows of one batch sharing ``stimulus_group``. Its stimulus
    is the longest paragraph-aligned prefix every stem shares; each stem keeps
    only what follows. Returns ``({qid: (stimulus, stem)}, errors)``."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for q in questions:
        if q.get("stimulus_group"):
            groups[q["stimulus_group"]].append(q)
    splits: dict[str, tuple[str, str]] = {}
    errors: list[str] = []
    for group, qs in groups.items():
        ids = [q["id"] for q in qs]
        if len(qs) < 2:
            errors.append(f"case set {group}: only one stem ({ids[0]}), no shared stimulus")
            continue
        prefix = _common_prefix([q["stem"] for q in qs])
        cut = prefix.rfind("\n\n")
        stimulus = prefix[:cut].strip() if cut > 0 else ""
        stems = [q["stem"][cut + 2:].strip() if cut > 0 else "" for q in qs]
        if not stimulus or not all(stems):
            errors.append(f"case set {group}: stems {ids} do not share a stimulus")
            continue
        for q, stem in zip(qs, stems):
            splits[q["id"]] = (stimulus, stem)
    return splits, errors


# ── mapping (single source of truth; the #1216 import tests use it) ───────────

def to_import_row(
    q: dict,
    *,
    subject_id: str,
    topic_id: str,
    split: tuple[str, str] | None = None,
    batch: str | None = None,
    factcheck_verdict: str = NOT_FLAGGED,
) -> dict:
    """Corpus row → bulk-import JSON row. A case row's shared case text becomes
    its own stimulus copy (``split``); the stem keeps only the question part."""
    stem, stimuli = q["stem"], []
    if split:
        case_text, stem = split
        stimuli = [{
            "stimulus_type": "table" if "|---" in case_text else "passage",
            "content_text": case_text,
        }]
    expl = q["explanation"]
    row = {
        "question_text": stem,
        "correct_option": str(next(i for i, o in enumerate(q["options"]) if o["is_correct"]) + 1),
        "difficulty": q["difficulty"],
        "rubric_level": q["rubric_level"],
        "stimulus_group": q.get("stimulus_group"),
        "common_trap": expl["trap"],
        "stimuli": stimuli,
        "structured_explanation": {
            "solution_steps": expl["steps"],
            "formula_used": [expl["formula_used"]] if expl.get("formula_used") else [],
            "common_traps": [expl["trap"]],
            "option_rationales": {
                str(i): o["error"] for i, o in enumerate(q["options"]) if o.get("error")
            },
        },
        "metadata": {
            "corpus_id": q["id"],
            "batch": batch,
            "corpus_version": CORPUS_VERSION,
            "verify_fact": bool(q.get("verify_fact")),
            "factcheck_verdict": factcheck_verdict,
        },
        "source_kind": "authored",
        "subject_id": subject_id,
        "topic_id": topic_id,
        "external_id": q["id"],
    }
    for i, o in enumerate(q["options"]):
        row[f"option_{i + 1}"] = o["text"]
    return row


# ── build ──────────────────────────────────────────────────────────────────────

def _exported_ids(topics: dict[str, dict]) -> set[str]:
    ids: set[str] = set()
    for t in topics.values():
        ids.update(t.get("ids") or [t.get("id")])
    return ids


def _resolve_topic(slug: str, topics: dict[str, dict], catalogue: set[str]) -> tuple[dict | None, str | None]:
    if slug not in catalogue:
        return None, f"unknown microtopic slug {slug!r} (not in workbench/corpus/reg/lists)"
    t = topics.get(slug)
    if t and AMBIGUOUS in t:
        return None, f"ambiguous topic: slug {slug!r} appears {t[AMBIGUOUS]} times in the topics export"
    if not t or not t.get("id"):
        return None, f"missing topic: slug {slug!r} is not in the topics export"
    if not t.get("subject_id"):
        return None, f"missing topic: slug {slug!r} has no subject_id in the topics export"
    parent = t.get("parent_topic_id")
    if parent and parent not in _exported_ids(topics):
        return None, f"missing topic: parent {parent} of {slug!r} is not in the topics export"
    return t, None


def build(
    corpus: dict[str, list[dict]],
    *,
    topics: dict[str, dict],
    catalogue: set[str],
    factcheck: dict[str, str],
    only_ids: set[str] | None = None,
) -> tuple[dict[str, list[dict]], dict[str, list[str]]]:
    """``({batch: [import row]}, {batch: [error]})``. Nothing is partial: the
    caller writes files only when every batch's error list is empty."""
    rows_by_batch: dict[str, list[dict]] = {}
    errors_by_batch: dict[str, list[str]] = {}
    seen_fp: dict[str, str] = {}
    seen_id: dict[str, str] = {}
    for batch, questions in corpus.items():
        rows: list[dict] = []
        splits, errors = case_splits(questions)
        for q in questions:
            if only_ids is not None and q["id"] not in only_ids:
                continue
            if q["id"] in seen_id:
                errors.append(f"{q['id']}: duplicate corpus id (also in {seen_id[q['id']]})")
                continue
            seen_id[q["id"]] = batch
            if q.get("stimulus_group") and q["id"] not in splits:
                continue  # its case set already reported
            topic, err = _resolve_topic(q["microtopic_slug"], topics, catalogue)
            if err:
                errors.append(f"{q['id']}: {err}")
                continue
            row = to_import_row(
                q, subject_id=topic["subject_id"], topic_id=topic["id"],
                split=splits.get(q["id"]), batch=batch,
                factcheck_verdict=factcheck.get(q["id"], NOT_FLAGGED),
            )
            parsed, parse_errors = _parse_row(row, len(rows) + 2)
            if parse_errors:
                errors.append(f"{q['id']}: importer rejects row: {'; '.join(parse_errors)}")
                continue
            fp = parsed["fingerprint"]
            if fp in seen_fp:
                errors.append(f"{q['id']}: duplicate fingerprint (same as {seen_fp[fp]})")
                continue
            seen_fp[fp] = q["id"]
            rows.append(row)
        rows_by_batch[batch] = rows
        errors_by_batch[batch] = errors
    return rows_by_batch, errors_by_batch


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--topics", type=Path, required=True,
                    help="topics export CSV: id,slug,level,parent_topic_id,subject_id")
    ap.add_argument("--batch", action="append", default=None,
                    help="batch name, e.g. REG-CORPUS-CST (repeatable; default: all)")
    ap.add_argument("--only-ids", type=Path, default=None, help="file with one corpus id per line")
    ap.add_argument("--dry-run", action="store_true", help="validate and report; write nothing")
    ap.add_argument("--corpus-dir", type=Path, default=CORPUS_DIR)
    ap.add_argument("--factcheck", type=Path, default=FACTCHECK_CSV)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    try:
        corpus = load_corpus(args.corpus_dir, args.batch)
        rows_by_batch, errors_by_batch = build(
            corpus,
            topics=load_topics(args.topics),
            catalogue=load_catalogue(),
            factcheck=load_factcheck(args.factcheck),
            only_ids=load_only_ids(args.only_ids) if args.only_ids else None,
        )
    except CorpusError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    total_err = 0
    for batch in rows_by_batch:
        rows, errors = rows_by_batch[batch], errors_by_batch[batch]
        cases = sum(1 for r in rows if r["stimuli"])
        verdicts = Counter(r["metadata"]["factcheck_verdict"] for r in rows)
        print(f"{batch}: {len(rows)} rows · {cases} case rows · errors {len(errors)} · "
              f"factcheck {dict(sorted(verdicts.items()))}")
        for e in errors:
            print(f"  ERROR {e}", file=sys.stderr)
        total_err += len(errors)
    print(f"total: {sum(len(r) for r in rows_by_batch.values())} rows, {total_err} errors")
    if total_err:
        return 1
    if args.dry_run:
        return 0
    args.out.mkdir(parents=True, exist_ok=True)
    for batch, rows in rows_by_batch.items():
        path = args.out / f"{batch}.import.json"
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
