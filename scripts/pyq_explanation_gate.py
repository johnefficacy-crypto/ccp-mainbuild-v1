#!/usr/bin/env python3
"""Scope and gate the PYQ explanation lane — offline, deterministic.

The explanation lane (``workbench/reports/EXPL-LANE-STATUS.md``) has no
generator script. A drafting session reads an input JSON of verified MCQs and
writes a draft worksheet (``workbench/worksheets/<EXAM>-EXPLANATIONS-DRAFT.json``)
whose rows carry the ``pyq_question_explanations`` fields plus the drafter's own
``key_verdict`` / ``final_answer_option_id``. An operator then posts the rows to
the CMS write path, where they are born ``pending``. Nothing between the draft
and the write compares the explanation against the keyed answer: the drafter's
AGREE is self-reported, the migration-230 guard only proves
``final_answer_option_id`` belongs to the question, and the review RPC only
requires it to be non-null.

This tool fills both ends of that gap and nothing else. It opens no network
connection, holds no client and calls no model.

    input  ->  build the drafting input for ONE exam and ONE question set from
               the files ``pyq_question_review.py export --apply`` writes.
               Same row shape as ``workbench/sources/*-explanations-input.json``
               (question_id, year, question_number, question_text, options,
               correct_option_id, subject_slug, topic_name), plus paper_id,
               section and ``stimulus_text``, so a set member's shared passage,
               DI table or puzzle reaches the drafter (the missing join the lane
               status names as open item 5).

    gate   ->  compare a draft worksheet against the keyed answers in that
               input. Every draft row either PASSES, and goes into a CMS
               bulk-import body, or is QUARANTINED into a CSV shaped like the
               ``pyq_question_review.py`` worksheet with a blank ``decision``.
               Nothing quarantined is written anywhere. ``--signed`` re-reads a
               quarantine CSV an operator has filled and releases the rows
               signed ``verified`` whose flags are all soft.

What PASS means, and it is narrower than it sounds: the keyed option is known
and unambiguous, the drafter's final answer is that option, the drafter did not
dispute it, every option carries a rationale and no rationale names a foreign
option, and no sentence of the explanation announces a different option as the
answer. It does NOT mean the explanation is correct. A passing row is still
born ``pending`` and still goes through the review route before any learner can
read it (``app/backend/app/study_os/pyq_explanations.py``, verified-only gate).

Usage::

    python scripts/pyq_explanation_gate.py input \\
        --export-dir review_out_ssc \\
        --exam-id 3742f421-eae0-4a02-8fd1-ac3aa0589c9f \\
        --section-aliases workbench/audit/ssc_cgl/ssc_section_aliases.json \\
        --projected-ids projected_ids.txt \\
        --out workbench/sources/ssc-cgl-2024-t1-explanations-input.json --apply

    python scripts/pyq_explanation_gate.py gate \\
        --input workbench/sources/ssc-cgl-2024-t1-explanations-input.json \\
        --draft workbench/worksheets/SSC-CGL-EXPLANATIONS-DRAFT.json \\
        --out-dir workbench/audit/ssc_cgl/explanations --apply

See ``docs/runbooks/qre-explanations.md``.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

# The three shared QRE subjects (workbench/audit/ssc_cgl/README.md). Default
# question set for `input`; pass --subject-slug to choose another.
QRE_SUBJECTS = ("quantitative-aptitude", "general-intelligence-reasoning", "english-language")

# Kept identical to scripts/pyq_question_review.py WORKSHEET_FIELDS so a
# quarantine CSV reads like every other review worksheet in the repo.
WORKSHEET_FIELDS = [
    "row_type", "row_id", "paper_year", "question_number_or_topic_id",
    "text_preview", "flags", "sample_reason", "decision", "notes",
    "assign_topic_id", "difficulty", "stimulus_preview",
    "paper_id", "section", "current_primary_topic_id",
]
DECISIONS = {"verified", "rejected", "needs_correction"}
ROW_TYPE = "explanation"
SAMPLE_REASON = "explanation_gate"

# HARD flags cannot be released by a signature: each means the explanation and
# the key disagree, or the key itself is unusable. The only way out is a key
# repair or a redraft, followed by a fresh export and a fresh gate run.
HARD_FLAGS = {
    "unknown_question",       # draft row not in the scoped input
    "key_missing",            # no correct_option_id on the question
    "key_inconsistent",       # correct_option_id disagrees with options[].correct
    "final_answer_missing",   # drafter asserted no final answer
    "final_answer_mismatch",  # drafter's final answer is not the keyed option
    "key_disputed",           # drafter's key_verdict is not AGREE
    "rationale_foreign_option",  # a rationale is keyed to another question's option
}
# SOFT flags are lexical or coverage signals. An operator who reads the row and
# finds the explanation supports the keyed option may sign it `verified`.
SOFT_FLAGS = {
    "rationale_missing_option",  # a distractor of this question has no rationale
    "text_names_other_option",   # a sentence announces a non-keyed option as the answer
    "duplicate_draft_row",       # the same question_id appears twice in the draft
}

_PREVIEW = 140

# Sentences that announce an answer by option letter. Narrow on purpose: only a
# phrase that states which option IS the answer, never a mention of an option
# in passing ("option (b) gives 42, which is the slip of ..."). A bare letter
# after "answer is" is NOT read as an option: in seating and blood-relation sets
# "the answer is D" names a person. The letter must follow "option" or sit in
# parentheses.
_ANSWER_PHRASES = [
    re.compile(r"\banswer\s+is\s+(?:option\s+\(?([a-e])\)?|\(([a-e])\))(?![\w'])", re.I),
    re.compile(r"\bcorrect\s+(?:option|choice)\s+is\s+\(?([a-e])\)?(?![\w'])", re.I),
    re.compile(r"\boption\s+\(?([a-e])\)?\s+is\s+(?:the\s+)?(?:correct|right)\b", re.I),
    re.compile(r"\b(?:hence|so|therefore|thus)[,\s]+(?:the\s+answer\s+is\s+)?option\s+\(?([a-e])\)?(?![\w'])", re.I),
]


# ─── io ──────────────────────────────────────────────────────────────────────
def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _cell(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


def _preview(text: Any, n: int = _PREVIEW) -> str:
    s = " ".join(str(text or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _read_id_file(path: Path | None) -> set[str] | None:
    """One id per line, or a JSON list. ``None`` when no path is given."""
    if path is None:
        return None
    raw = path.read_text(encoding="utf-8-sig").strip()
    if raw.startswith("["):
        return {str(x).strip() for x in json.loads(raw) if str(x).strip()}
    return {ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.startswith("#")}


# ─── input ───────────────────────────────────────────────────────────────────
def build_input(
    questions: list[dict],
    options: list[dict],
    stimuli: list[dict],
    papers: list[dict],
    tags: list[dict],
    *,
    exam_id: str,
    section_aliases: dict[str, str],
    subjects: set[str],
    paper_ids: set[str] | None = None,
    projected_ids: set[str] | None = None,
    exclude_ids: set[str] | None = None,
    topic_names: dict[str, str] | None = None,
) -> tuple[list[dict], dict[str, int]]:
    """Scope an export to one exam and one question set; return (rows, skips).

    A question is IN when: its paper belongs to ``exam_id`` (and to
    ``paper_ids`` if given); it is ``verified``; it is an MCQ; its section maps
    to one of ``subjects``; it has at least two verified options and a key; it
    is in ``projected_ids`` if given; and it is not in ``exclude_ids`` (the ids
    that already carry an explanation). Every exclusion is counted by reason so
    an operator can reconcile the total against the expected count.
    """
    paper_by_id = {p["id"]: p for p in papers if p.get("id")}
    foreign = sorted(pid for pid, p in paper_by_id.items() if p.get("exam_id") != exam_id)
    if foreign:
        raise SystemExit(f"error: export holds paper(s) not on exam {exam_id}: {foreign}")

    opts_by_q: dict[str, list[dict]] = {}
    for o in options:
        if o.get("reviewer_status") == "verified":
            opts_by_q.setdefault(o["question_id"], []).append(o)

    stim_by_q: dict[str, list[dict]] = {}
    for st in stimuli:
        for qid in st.get("question_ids") or []:
            stim_by_q.setdefault(qid, []).append(st)

    primary_topic: dict[str, str] = {}
    for t in tags:
        if t.get("tag_role") == "primary" and t.get("reviewer_status") == "verified":
            primary_topic[t["question_id"]] = t.get("topic_id") or ""

    skips: dict[str, int] = {}

    def skip(reason: str) -> None:
        skips[reason] = skips.get(reason, 0) + 1

    rows: list[dict] = []
    for q in sorted(questions, key=lambda r: (str(r.get("paper_id")), r.get("question_number") or 0, r["id"])):
        qid = q["id"]
        if q.get("paper_id") not in paper_by_id:
            skip("paper_not_in_export"); continue
        if paper_ids is not None and q.get("paper_id") not in paper_ids:
            skip("paper_out_of_scope"); continue
        if q.get("reviewer_status") != "verified":
            skip("question_not_verified"); continue
        if (q.get("question_type") or "") != "mcq":
            skip("not_mcq"); continue
        subject = section_aliases.get(q.get("section") or "")
        if subject not in subjects:
            skip("subject_out_of_scope"); continue
        if projected_ids is not None and qid not in projected_ids:
            skip("not_projected"); continue
        if exclude_ids is not None and qid in exclude_ids:
            skip("already_explained"); continue
        opts = sorted(opts_by_q.get(qid, []),
                      key=lambda o: (str(o.get("option_label") or ""), str(o.get("id"))))
        if len(opts) < 2:
            skip("too_few_verified_options"); continue
        if not q.get("correct_option_id"):
            skip("no_answer_key"); continue

        stims = sorted(stim_by_q.get(qid, []), key=lambda s: (s.get("display_order") or 0, str(s.get("id"))))
        rows.append({
            "question_id": qid,
            "year": q.get("year"),
            "question_number": q.get("question_number"),
            "question_text": q.get("question_text") or "",
            "options": [{
                "id": o["id"],
                "label": str(o.get("option_label") or "").lower(),
                "text": o.get("option_text") or "",
                "correct": bool(o.get("is_correct")),
            } for o in opts],
            "correct_option_id": q["correct_option_id"],
            "subject_slug": subject,
            "topic_name": (topic_names or {}).get(primary_topic.get(qid, ""), ""),
            "paper_id": q.get("paper_id"),
            "section": q.get("section") or "",
            "stimulus_text": "\n\n".join(s.get("content_text") or "" for s in stims),
        })
    return rows, skips


# ─── gate ────────────────────────────────────────────────────────────────────
def _answer_labels_in_text(text: str) -> set[str]:
    found: set[str] = set()
    for pat in _ANSWER_PHRASES:
        for m in pat.finditer(text or ""):
            found.update(g.lower() for g in m.groups() if g)
    return found


def _rationale_ids(raw: Any) -> list[str]:
    """Draft rationales are a list of {option_id, label, rationale}; the table
    stores {option_id: rationale}. Accept either shape."""
    if isinstance(raw, dict):
        return [str(k) for k, v in raw.items() if isinstance(v, str) and v.strip()]
    if isinstance(raw, list):
        return [str(r.get("option_id")) for r in raw
                if isinstance(r, dict) and str(r.get("rationale") or "").strip()]
    return []


def check_row(draft: dict, q: dict | None) -> tuple[list[str], str]:
    """Return (flags, note) for one draft row against its input question."""
    if q is None:
        return ["unknown_question"], "question_id not in the scoped input"
    flags: list[str] = []
    notes: list[str] = []
    label_of = {o["id"]: o["label"] for o in q["options"]}
    key = q.get("correct_option_id")
    marked = [o["id"] for o in q["options"] if o.get("correct")]

    if not key or key not in label_of:
        flags.append("key_missing")
        notes.append("no keyed option among the verified options")
    elif marked != [key]:
        flags.append("key_inconsistent")
        notes.append(f"correct_option_id={label_of.get(key, '?')} but options marked correct="
                     f"{','.join(label_of.get(m, '?') for m in marked) or 'none'}")

    key_label = label_of.get(key, "?")
    final = draft.get("final_answer_option_id")
    if not final:
        flags.append("final_answer_missing")
        notes.append(f"keyed {key_label}; draft asserts no final answer")
    elif final != key:
        flags.append("final_answer_mismatch")
        notes.append(f"keyed {key_label}; draft final answer "
                     f"{label_of.get(final, 'not an option of this question')}")

    verdict = (draft.get("key_verdict") or "AGREE").upper()
    if verdict != "AGREE":
        flags.append("key_disputed")
        proposed = draft.get("proposed_correct_option_id")
        notes.append(f"draft key_verdict={verdict}"
                     + (f", proposes {label_of.get(proposed, '?')}" if proposed else ""))

    rat_ids = _rationale_ids(draft.get("option_rationales"))
    foreign = [r for r in rat_ids if r not in label_of]
    if foreign:
        flags.append("rationale_foreign_option")
        notes.append(f"{len(foreign)} rationale(s) keyed to options not on this question")
    # The lane's convention (every committed *-EXPLANATIONS-DRAFT.json): one
    # rationale per DISTRACTOR; the keyed option is argued in short_explanation.
    missing = [label_of[o] for o in label_of if o != key and o not in rat_ids]
    if missing:
        flags.append("rationale_missing_option")
        notes.append(f"no rationale for option(s) {','.join(sorted(missing))}")

    text = " ".join(str(draft.get(k) or "") for k in ("short_explanation", "explanation_text"))
    text += " " + " ".join(str(s) for s in (draft.get("solution_steps") or []))
    others = sorted(_answer_labels_in_text(text) - {key_label})
    if others and key_label != "?":
        flags.append("text_names_other_option")
        notes.append(f"text announces option(s) {','.join(others)} as the answer; keyed {key_label}")

    return flags, "; ".join(notes)


def to_cms_row(draft: dict, key: str, metadata: dict | None = None) -> dict:
    """Draft row -> a `pyq-question-explanations` bulk-import row.

    The fold the lane status describes (step 5): option_rationales to
    {option_id: rationale}, formula_used wrapped in an array. final_answer is
    the KEYED option — by construction equal to the draft's on a clean pass.
    reviewer_status is not sent: the import config forces 'pending'.
    """
    raw = draft.get("option_rationales")
    if isinstance(raw, list):
        rationales = {str(r["option_id"]): r["rationale"] for r in raw
                      if isinstance(r, dict) and r.get("option_id") and str(r.get("rationale") or "").strip()}
    else:
        rationales = dict(raw or {})
    formula = draft.get("formula_used")
    if isinstance(formula, str):
        formula = [formula] if formula.strip() else []
    row = {
        "question_id": draft["question_id"],
        "short_explanation": draft.get("short_explanation") or None,
        "explanation_text": draft.get("explanation_text") or None,
        "solution_steps": list(draft.get("solution_steps") or []),
        "option_rationales": rationales,
        "formula_used": list(formula or []),
        "common_traps": list(draft.get("common_traps") or []),
        "final_answer_option_id": key,
        "ambiguity_status": "none",
        "explanation_source_type": draft.get("explanation_source_type") or "platform_original",
        "license_status": draft.get("license_status") or "owned",
    }
    if metadata:
        row["metadata"] = metadata
    return row


def quarantine_row(draft: dict, q: dict | None, flags: list[str], note: str) -> dict:
    q = q or {}
    return {
        "row_type": ROW_TYPE,
        "row_id": draft.get("question_id") or "",
        "paper_year": q.get("year", draft.get("year")) or "",
        "question_number_or_topic_id": q.get("question_number", draft.get("question_number")) or "",
        "text_preview": _preview(q.get("question_text")),
        "flags": ";".join(flags),
        "sample_reason": SAMPLE_REASON,
        "decision": "",
        "notes": note,
        "assign_topic_id": "",
        "difficulty": "",
        "stimulus_preview": _preview(q.get("stimulus_text")),
        "paper_id": q.get("paper_id") or "",
        "section": q.get("section") or "",
        "current_primary_topic_id": "",
    }


def run_gate(
    inputs: list[dict],
    drafts: list[dict],
    *,
    signed: list[dict] | None = None,
) -> dict[str, Any]:
    """Split drafts into passed CMS rows and quarantine rows.

    ``signed`` is a quarantine CSV read back after an operator filled
    ``decision``. A row signed ``verified`` is released only if every one of its
    CURRENT flags is soft — the gate is re-run, not trusted from the sheet, so a
    row whose key or draft changed since signing is judged afresh.
    """
    by_id = {r["question_id"]: r for r in inputs}
    sign = {}
    for r in signed or []:
        d = _cell(r, "decision").lower()
        if d and d not in DECISIONS:
            raise SystemExit(f"error: row {_cell(r, 'row_id')}: decision {d!r} not in {sorted(DECISIONS)}")
        if _cell(r, "row_type") == ROW_TYPE and d:
            sign[_cell(r, "row_id")] = (d, _cell(r, "notes"))

    seen: dict[str, int] = {}
    for d in drafts:
        seen[d.get("question_id")] = seen.get(d.get("question_id"), 0) + 1

    passed: list[dict] = []
    released: list[dict] = []
    quarantined: list[dict] = []
    refused_signatures: list[str] = []
    flag_counts: dict[str, int] = {}
    for d in drafts:
        qid = d.get("question_id")
        q = by_id.get(qid)
        flags, note = check_row(d, q)
        if seen.get(qid, 0) > 1:
            flags.append("duplicate_draft_row")
        for f in flags:
            flag_counts[f] = flag_counts.get(f, 0) + 1
        if not flags:
            passed.append(to_cms_row(d, q["correct_option_id"]))
            continue
        decision, signed_note = sign.get(qid, ("", ""))
        hard = [f for f in flags if f in HARD_FLAGS]
        if decision == "verified" and not hard and "duplicate_draft_row" not in flags:
            released.append(to_cms_row(d, q["correct_option_id"], metadata={
                "explanation_gate": {"released_flags": flags, "operator_note": signed_note},
            }))
            continue
        if decision == "verified":
            refused_signatures.append(qid)
        row = quarantine_row(d, q, flags, note)
        if decision:
            row["decision"] = decision
            row["notes"] = "; ".join(x for x in (note, signed_note) if x)
        quarantined.append(row)

    return {
        "passed": passed,
        "released": released,
        "quarantined": quarantined,
        "refused_signatures": refused_signatures,
        "flag_counts": flag_counts,
        "not_drafted": sorted(set(by_id) - set(seen)),
    }


# ─── cli ─────────────────────────────────────────────────────────────────────
def do_input(args: argparse.Namespace) -> int:
    d = Path(args.export_dir)
    questions = _load_json(d / "questions_export.json")
    papers = _load_json(d / "papers_export.json")
    options_path = d / "options_export.json"
    if not options_path.exists():
        print("error: options_export.json is required — the gate compares against option rows",
              file=sys.stderr)
        return 1
    options = _load_json(options_path)
    stimuli_path = d / "stimuli_export.json"
    if not stimuli_path.exists():
        print("error: stimuli_export.json is required — set members are undraftable without "
              "their passage", file=sys.stderr)
        return 1
    stimuli = _load_json(stimuli_path)
    tags = _load_json(d / "tags_export.json") if (d / "tags_export.json").exists() else []
    aliases = _load_json(Path(args.section_aliases))
    topic_names = None
    if args.topic_catalog:
        topic_names = {r["id"]: r.get("name") or r.get("text") or ""
                       for r in _load_json(Path(args.topic_catalog)) if r.get("id")}

    rows, skips = build_input(
        questions, options, stimuli, papers, tags,
        exam_id=args.exam_id,
        section_aliases=aliases,
        subjects=set(args.subject_slug or QRE_SUBJECTS),
        paper_ids={p for p in (args.paper_id or [])} or None,
        projected_ids=_read_id_file(Path(args.projected_ids) if args.projected_ids else None),
        exclude_ids=_read_id_file(Path(args.exclude_ids) if args.exclude_ids else None),
        topic_names=topic_names,
    )
    by_paper: dict[str, int] = {}
    by_subject: dict[str, int] = {}
    for r in rows:
        by_paper[r["paper_id"]] = by_paper.get(r["paper_id"], 0) + 1
        by_subject[r["subject_slug"]] = by_subject.get(r["subject_slug"], 0) + 1
    print(f"In scope: {len(rows)} question(s) across {len(by_paper)} paper(s).")
    print(f"  by subject: {dict(sorted(by_subject.items()))}")
    for pid, n in sorted(by_paper.items()):
        print(f"  paper {pid}: {n}")
    print(f"  with a stimulus: {sum(1 for r in rows if r['stimulus_text'])}")
    print(f"  excluded: {dict(sorted(skips.items()))}")
    if args.projected_ids is None:
        print("  NOTE: --projected-ids not given; projection was NOT checked.")
    if args.exclude_ids is None:
        print("  NOTE: --exclude-ids not given; existing explanations were NOT excluded.")
    if args.expect is not None and len(rows) != args.expect:
        print(f"error: expected {args.expect} in-scope question(s), found {len(rows)}", file=sys.stderr)
        return 2
    if not args.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply to write", args.out)
        return 0
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", args.out)
    return 0


def do_gate(args: argparse.Namespace) -> int:
    inputs = _load_json(Path(args.input))
    drafts = _load_json(Path(args.draft))
    signed = None
    if args.signed:
        signed = list(csv.DictReader(io.open(args.signed, encoding="utf-8-sig")))
    res = run_gate(inputs, drafts, signed=signed)

    print(f"Draft rows: {len(drafts)}. Input questions: {len(inputs)}.")
    print(f"  passed:      {len(res['passed'])}")
    print(f"  released:    {len(res['released'])} (signed verified, soft flags only)")
    print(f"  quarantined: {len(res['quarantined'])}")
    print(f"  not drafted: {len(res['not_drafted'])}")
    for f, n in sorted(res["flag_counts"].items()):
        print(f"    {f:<26} {n:>5}  {'HARD' if f in HARD_FLAGS else 'soft'}")
    if res["refused_signatures"]:
        print(f"  REFUSED {len(res['refused_signatures'])} `verified` signature(s) on rows with a "
              f"hard flag — these need a key repair or a redraft, not a signature.")

    if not args.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply.")
        return 0
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    reason = args.reason or "explanation gate: draft final answer agrees with the keyed option"
    body_rows = res["passed"] + res["released"]
    (out / "cms_body.json").write_text(json.dumps(
        {"reason": reason, "entity": "pyq-question-explanations", "rows": body_rows},
        ensure_ascii=False, indent=1), encoding="utf-8")
    with io.open(out / "quarantine.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=WORKSHEET_FIELDS)
        w.writeheader()
        w.writerows(res["quarantined"])
    (out / "gate_summary.json").write_text(json.dumps({
        "draft_rows": len(drafts), "input_questions": len(inputs),
        "passed": len(res["passed"]), "released": len(res["released"]),
        "quarantined": len(res["quarantined"]), "flag_counts": res["flag_counts"],
        "refused_signatures": res["refused_signatures"], "not_drafted": res["not_drafted"],
    }, indent=1), encoding="utf-8")
    print(f"wrote {out / 'cms_body.json'} ({len(body_rows)} rows), "
          f"{out / 'quarantine.csv'}, {out / 'gate_summary.json'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("input", help="scope an export into a drafting input")
    i.add_argument("--export-dir", required=True, help="pyq_question_review.py export --out dir")
    i.add_argument("--exam-id", required=True)
    i.add_argument("--paper-id", action="append", help="repeatable; default every paper in the export")
    i.add_argument("--subject-slug", action="append", help=f"repeatable; default {', '.join(QRE_SUBJECTS)}")
    i.add_argument("--section-aliases", required=True, help="JSON {section label: subject slug}")
    i.add_argument("--projected-ids", help="pyq_question ids present in mock_question_bank")
    i.add_argument("--exclude-ids", help="pyq_question ids that already carry an explanation")
    i.add_argument("--topic-catalog", help="catalog JSON, to fill topic_name from the primary tag")
    i.add_argument("--expect", type=int, help="fail unless exactly this many questions are in scope")
    i.add_argument("--out", required=True)
    i.add_argument("--apply", action="store_true")
    i.set_defaults(func=do_input)

    g = sub.add_parser("gate", help="compare a draft against the keyed answers")
    g.add_argument("--input", required=True, help="the input JSON the draft was written from")
    g.add_argument("--draft", required=True, help="the drafting session's worksheet JSON")
    g.add_argument("--signed", help="a quarantine.csv with decisions filled")
    g.add_argument("--reason", help="bulk-import reason (audit log)")
    g.add_argument("--out-dir", required=True)
    g.add_argument("--apply", action="store_true")
    g.set_defaults(func=do_gate)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
