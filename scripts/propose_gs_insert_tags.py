#!/usr/bin/env python3
r"""Propose one primary tag per staged GS question - proposals only.

P3 of the GS gap repair. OFFLINE and deterministic: no model, no network, no
database. Writes ``workbench/audit/gs_inserts/tag_review.csv``; a human marks
``approved=Y`` (optionally overriding the slug in ``edited_slug``), and
``scripts/load_gs_inserts.py --tags-csv`` applies the approved rows as
``reviewer_status='verified'`` primary tags on the questions it inserted.

WHY NOT ``scripts/propose_pyq_topic_tags.py``
--------------------------------------------
That proposer is built for the regulatory MCQ corpus: its candidate builder
requires ``metadata.exams`` to name SEBI/PFRDA/IFSCA, its prompt carries
options, and it calls a model. None of that fits descriptive GS questions, and
"no new AI writes" rules out a model here anyway. This script reuses what
does fit: the GS micro-theme map and ``slugify`` from
``scripts/ingest_upsc_gs_syllabus.py``, so every proposed slug is the slug that
ingest wrote to ``topics``.

CANDIDATES
----------
* GS1-GS4: ``level='microtopic'`` rows under ``upsc-cse-mains-gs<n>`` - by
  default rebuilt from ``docs/reference/syllabus/upsc_cse_mains_gs_micro_themes_v2026.3.json``;
  ``--topics`` takes a DB export instead (JSONL: subject_slug, slug, name,
  level, parent_name, description).
* Essay: active rows of ``essay_themes`` - only from ``--essay-themes`` (JSONL:
  theme_code, theme_name, description, status). The repo seeds no essay theme
  catalogue, so without the export Essay rows are written UNMAPPED.

SCORING: TF-IDF cosine between the question's content words and each
candidate's text (micro-theme + macro topic + official syllabus line), with a
fixed light stemmer. Ties break on slug. Below ``MIN_SCORE`` the row is
UNMAPPED. The runner-up is shown so a reviewer can see how close it was.

    python scripts/propose_gs_insert_tags.py
    python scripts/propose_gs_insert_tags.py --essay-themes essay_themes.jsonl
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


egm = _load("extract_gs_missing", "scripts/extract_gs_missing.py")
_ingest = _load("ingest_upsc_gs_syllabus", "scripts/ingest_upsc_gs_syllabus.py")
slugify = _ingest.slugify

STAGING_DIR = egm.OUT_DIR
TAG_REVIEW_CSV = STAGING_DIR / "tag_review.csv"
SYLLABUS_JSON = ROOT / "docs" / "reference" / "syllabus" / "upsc_cse_mains_gs_micro_themes_v2026.3.json"

PROPOSER_VERSION = "gs-insert-tag-proposer-v1"
MIN_SCORE = 0.05
_PAPER_ID = {"GS_1": "GS1", "GS_2": "GS2", "GS_3": "GS3", "GS_4": "GS4"}

FIELDS = [
    "paper_code", "content_hash", "year", "paper", "official_number", "sub_part",
    "text", "kind", "subject_slug", "status", "proposed_slug", "proposed_name", "score",
    "runner_up_slug", "runner_up_name", "runner_up_score", "proposer_version",
    "approved", "edited_slug", "essay_type", "reviewer_note",
]
HUMAN_FIELDS = ("approved", "edited_slug", "essay_type", "reviewer_note")


def subject_slug_for(paper: str) -> str:
    return f"upsc-cse-mains-{paper.lower()}"


# ── catalogues ───────────────────────────────────────────────────────────


def catalogue_from_syllabus(path: Path = SYLLABUS_JSON) -> dict[str, list[dict[str, Any]]]:
    """paper -> microtopic candidates, slugged exactly as the ingest slugged them."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[dict[str, Any]]] = {}
    for paper in doc.get("papers", []):
        pid = paper.get("paper_id", "")
        code = _PAPER_ID.get(pid)
        if not code:
            continue
        for node in paper.get("syllabus_nodes", []):
            macro = (node.get("macro_topic") or "").strip()
            line = (node.get("official_syllabus_line") or "").strip()
            for theme in node.get("micro_themes", []):
                theme = (theme or "").strip()
                if not (macro and theme):
                    continue
                out.setdefault(code, []).append({
                    "slug": slugify(f"{pid}:{macro}:{theme}"),
                    "name": theme,
                    "doc": f"{theme} {theme} {macro} {line}",
                })
    return out


def catalogue_from_export(path: Path) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("level") != "microtopic":
            continue
        m = re.fullmatch(r"upsc-cse-mains-(gs[1-4])", row.get("subject_slug") or "")
        if not m:
            continue
        for key in ("slug", "name"):
            if not row.get(key):
                raise SystemExit(f"{path.name} line {line_no}: missing {key}")
        out.setdefault(m.group(1).upper(), []).append({
            "slug": row["slug"],
            "name": row["name"],
            "doc": " ".join(filter(None, [row["name"], row["name"], row.get("parent_name"),
                                          row.get("description")])),
        })
    return out


def essay_catalogue(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("status", "active") != "active":
            continue
        out.append({
            "slug": row["theme_code"],
            "name": row.get("theme_name") or row["theme_code"],
            "doc": " ".join(filter(None, [row.get("theme_name"), row.get("theme_name"), row.get("description")])),
        })
    return out


# ── scoring (pure) ───────────────────────────────────────────────────────


def stem(word: str) -> str:
    for suffix in ("ations", "ation", "ings", "ing", "ies", "es", "ed", "ly", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


#: Directive and filler words every UPSC question carries. They say how to
#: answer, not what the question is about, so they carry no topic signal.
DIRECTIVES = frozenset("""
analyse analyze analysis assess bring comment compare critically describe
discuss distinguish elaborate elucidate enumerate evaluate examine example
examples explain highlight identify illustrate india indian justify mention
out point present regard statement substantiate suggest suitable
throw light context view way ways reference various major role
""".split())


def terms(text: str) -> list[str]:
    return [stem(w) for w in egm.content_words(text) if w not in DIRECTIVES]


def rank(question: str, candidates: list[dict[str, Any]]) -> list[tuple[float, dict[str, Any]]]:
    """[(cosine, candidate)] best first; ties on slug. Pure and deterministic."""
    if not candidates:
        return []
    docs = [terms(c["doc"]) for c in candidates]
    n = len(docs)
    df: dict[str, int] = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}

    def vec(tokens: list[str]) -> dict[str, float]:
        v: dict[str, float] = {}
        for t in tokens:
            if t in idf:
                v[t] = v.get(t, 0.0) + idf[t]
        return v

    q = vec(terms(question))
    qn = math.sqrt(sum(x * x for x in q.values()))
    out = []
    for cand, d in zip(candidates, docs):
        dv = vec(d)
        dn = math.sqrt(sum(x * x for x in dv.values()))
        dot = sum(q[t] * dv.get(t, 0.0) for t in q)
        score = dot / (qn * dn) if qn and dn else 0.0
        out.append((round(score, 4), cand))
    out.sort(key=lambda p: (-p[0], p[1]["slug"]))
    return out


def propose(question: dict[str, Any], header: dict[str, Any], gs: dict[str, list[dict[str, Any]]],
            essay: list[dict[str, Any]]) -> dict[str, Any]:
    paper = header["paper"]
    is_essay = paper == egm.ESSAY
    ranked = rank(question["text"], essay if is_essay else gs.get(paper, []))
    best = ranked[0] if ranked and ranked[0][0] >= MIN_SCORE else None
    runner = ranked[1] if len(ranked) > 1 else None
    return {
        "paper_code": header["paper_code"],
        "content_hash": question["content_hash"],
        "year": header["year"],
        "paper": paper,
        "official_number": question["official_number"],
        "sub_part": question.get("sub_part") or "",
        "text": question["text"],
        "kind": "essay_theme" if is_essay else "topic",
        "subject_slug": "" if is_essay else subject_slug_for(paper),
        "status": "MAPPED" if best else "UNMAPPED",
        "proposed_slug": best[1]["slug"] if best else "",
        "proposed_name": best[1]["name"] if best else "",
        "score": best[0] if best else "",
        "runner_up_slug": runner[1]["slug"] if runner else "",
        "runner_up_name": runner[1]["name"] if runner else "",
        "runner_up_score": runner[0] if runner else "",
        "proposer_version": PROPOSER_VERSION,
        "approved": "",
        "edited_slug": "",
        "essay_type": "",
        "reviewer_note": "",
    }


def merge_human(rows: list[dict[str, Any]], path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8-sig", newline="") as fh:
        old = {(r["paper_code"], r["content_hash"]): r for r in csv.DictReader(fh)}
    for row in rows:
        prior = old.get((row["paper_code"], row["content_hash"]))
        if prior:
            for col in HUMAN_FIELDS:
                if prior.get(col):
                    row[col] = prior[col]
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--staging-dir", default=str(STAGING_DIR))
    ap.add_argument("--topics", help="JSONL export of topics (default: rebuilt from the syllabus map)")
    ap.add_argument("--essay-themes", help="JSONL export of essay_themes")
    ap.add_argument("--out", default=str(TAG_REVIEW_CSV))
    args = ap.parse_args(argv)

    gs = catalogue_from_export(Path(args.topics)) if args.topics else catalogue_from_syllabus()
    essay = essay_catalogue(Path(args.essay_themes) if args.essay_themes else None)
    rows = []
    for (code, _h), (header, q) in sorted(
        egm_staging(Path(args.staging_dir)).items(),
        key=lambda kv: (kv[1][0]["year"], kv[1][0]["paper"], kv[1][1]["official_number"], kv[1][1].get("sub_part") or ""),
    ):
        rows.append(propose(q, header, gs, essay))
    out = Path(args.out)
    rows = merge_human(rows, out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    mapped = sum(1 for r in rows if r["status"] == "MAPPED")
    print(f"{len(rows)} proposal row(s): {mapped} mapped, {len(rows) - mapped} unmapped -> {out}")
    if not essay:
        print("no --essay-themes export: Essay rows are UNMAPPED")
    return 0


def egm_staging(staging_dir: Path) -> dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]]:
    """Every staged question (insert route), as the loader reads them."""
    out = {}
    for path in sorted(staging_dir.glob("20*_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        header = {k: v for k, v in doc.items() if k != "questions"}
        for q in doc.get("questions", []):
            out[(doc["paper_code"], q["content_hash"])] = (header, q)
    return out


if __name__ == "__main__":
    sys.exit(main())
