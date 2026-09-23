#!/usr/bin/env python3
"""Readiness report for an idle PYQ corpus, before anything is generated for it.

Written for SSC CGL 2024 Tier I — 850 questions across 13 papers, every row
``reviewer_status='pending'``, zero topic tags, nothing projected — but nothing
here is SSC-specific. It reads the flat files ``pyq_question_review.py export``
writes and answers, per paper, the questions that decide whether tagging that
paper is worth a reviewer's afternoon:

  * how many questions, and how they split across the exam-phase sections;
  * how many are missing option rows or an answer key;
  * how many share a normalised stem with another question (the import's
    hash-collision fix embeds options into ``question_text`` for generic reused
    stems, so a duplicate AFTER that fix is a different and more serious claim
    than one before it — this counts the after);
  * how many carry non-ASCII or a run of repeated characters;
  * which ``question_number`` values are missing or repeated;
  * CATALOGUE FIT over a spread sample — how much of the corpus the existing
    shared microtopic catalogues plausibly cover, and which gaps recur;
  * PROJECTION READINESS — which papers pass ``review_pyq_paper``'s provenance
    gate and, for those that do not, the field that blocks each one.

READ-ONLY AND OFFLINE. This module opens no network connection and holds no
API client. It writes files only with ``--apply``; without it the run prints
the same report to stdout and touches nothing on disk. It never proposes a
tag, never sets a difficulty and never promotes a row: every number here is a
counter over an export, and the actions they inform are taken elsewhere
(``propose_pyq_topic_tags.py`` for proposals, ``pyq_question_review.py apply``
for writes).

    CATALOGUE FIT IS A LEXICAL SIGNAL, NOT A TAG. The fit check compares the
    significant tokens of a question stem against the significant tokens of
    each microtopic's name, slug and description. That is enough to answer
    "does this corpus look like it belongs to the catalogue we already have",
    which is the readiness question. It is NOT enough to answer "which
    microtopic does this question carry", and the report never claims it is —
    the authoritative mapping is the proposer's, reviewed by a human, and a
    row this check calls unmatched may well map fine. Treat a low fit rate as
    a prompt to read the gap list, not as a count of untaggable questions.

    PROPOSED NEW MICROTOPICS ARE CANDIDATES, NOT ADDITIONS. The gap list is
    the recurring content tokens of the unmatched sample that no catalogue row
    covers, ranked by how many sampled questions they appear in. Naming a
    microtopic from them is a taxonomy decision a human makes; nothing here
    writes to ``topics``.

Inputs — all produced by ``pyq_question_review.py export --apply``:

    questions_export.json   required. id, paper_id, section, question_number,
                            question_text, question_type, correct_option_id.
    papers_export.json      required for the projection-readiness section.
                            source_type, source_url, source_document_id,
                            question_count.
    options_export.json     optional. Without it the missing-options and
                            missing-answer-key counters report "not computed"
                            rather than zero — absence is not a pass.
    --topic-catalog         optional, a JSON list of microtopic rows (the
                            format ``pyq_question_review.py catalog`` writes,
                            or a hand-written ``[{id, text, ...}]``). Without
                            it the catalogue-fit section is skipped entirely.

Usage::

    # dry run — prints the report, writes nothing
    python scripts/ssc_cgl_readiness.py \\
        --questions review_out_ssc/questions_export.json \\
        --papers    review_out_ssc/papers_export.json \\
        --options   review_out_ssc/options_export.json \\
        --topic-catalog topic_catalog_ssc.json

    # ... same command plus --apply writes the two report files:
        --out-md  workbench/audit/ssc_cgl_readiness.md \\
        --out-csv workbench/audit/ssc_cgl_readiness.csv \\
        --apply
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

# ── deterministic text handling ──────────────────────────────────────────────

# Printable ASCII treated as clean; the three whitespace characters a stem may
# legitimately carry are allowed. Mirrors pyq_question_review.py's _PRINTABLE
# so a question flagged here is the same question flagged by the sweep.
_PRINTABLE = set(chr(c) for c in range(0x20, 0x7F)) | {"\t", "\n", "\r"}
_REPEAT_CHAR = re.compile(r"(\S)\1{3,}")

_WORD = re.compile(r"[a-z]+")

# Tokens below this length carry no topical signal in an exam stem ("the",
# "of", "is"), and including them makes every question match every microtopic.
_MIN_TOKEN_LEN = 4

# Words that clear the length bar but say nothing about a question's TOPIC.
# Deliberately small and hand-listed, and deliberately NOT a general English
# stoplist: the reasoning and English sections are ABOUT words like series,
# letter, sentence, figure, statement, position, codes and number, so dropping
# them as "generic exam vocabulary" would suppress precisely the signal those
# two sections carry and report them as uncovered by a catalogue that covers
# them well. Only instruction and connective phrasing belongs here.
_STOPWORDS = frozenset("""
about above after again against alternative among another answer answers
based because before being below between both cannot choose chosen correct
could does each either else even every exactly except find first follow
following from give given gives have here however into itself just known
least less like make many more most much must near next none only other
others over part please question questions read refer related respectively
same select shall should shown since some such than that them then there
therefore these they this those through thus towards true under upon used
uses using very what when where which while will with within without would
your
""".split())

# A microtopic matches a stem when at least this share of its OWN significant
# tokens appear in the stem. A share, not a count, so a one-word microtopic
# ("percentage") needs its one word and a three-word one ("time and work",
# reduced to time/work) is not matched on a single incidental hit.
_FIT_COVERAGE = 0.5

# Gap candidates below this many sampled questions are noise, not a recurring
# theme worth naming a microtopic for.
_MIN_GAP_SUPPORT = 3

# How many gap candidates to list per section. The list is a prompt for a
# taxonomy decision, and a hundred-line one is not read.
_GAP_LIST_CAP = 25


def normalize_text(s: str | None) -> str:
    """Lowercase + collapse whitespace. The duplicate-stem comparison key."""
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def has_non_ascii(text: str) -> bool:
    return any(ch not in _PRINTABLE for ch in text)


def significant_tokens(text: str) -> set[str]:
    """Content words of a stem or a microtopic name, for the fit check.

    Case-folded, alphabetic only (a digit is not topical: "45%" appears in
    every percentage question AND every profit-and-loss one), at least
    ``_MIN_TOKEN_LEN`` characters, and not a stopword.
    """
    return {w for w in _WORD.findall((text or "").lower())
            if len(w) >= _MIN_TOKEN_LEN and w not in _STOPWORDS}


# ── input loading ────────────────────────────────────────────────────────────


def _load_json_list(path: str, what: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list of {what} objects, "
                         f"got {type(data).__name__}")
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: {what}[{i}] is not an object")
    return data


def load_catalogue(path: str) -> list[dict]:
    """Microtopic rows, reduced to (id, label, tokens).

    Accepts both shapes in the repo: the ``catalog`` subcommand's
    ``{id, text, slug, description, ...}`` and the older hand-written
    ``{id, text}``. A row carrying an explicit non-microtopic ``level`` is
    REJECTED by name, exactly as ``load_topic_catalog`` rejects it — a
    topic-level id is the wrong granularity for a question tag, and letting one
    into the fit check would report coverage this corpus cannot actually use.
    """
    rows = _load_json_list(path, "topic")
    out: list[dict] = []
    non_leaf: list[str] = []
    for e in rows:
        tid = e.get("id")
        if not tid:
            continue
        level = e.get("level")
        if level is not None and str(level).strip().lower() != "microtopic":
            non_leaf.append(f"{tid} (level={level!r})")
            continue
        label = e.get("text") or e.get("name") or e.get("slug") or str(tid)
        blob = " ".join(str(e.get(k) or "") for k in
                        ("text", "name", "slug", "description", "macro_topic"))
        out.append({
            "id": str(tid),
            "label": str(label),
            "subject_id": e.get("subject_id"),
            "tokens": significant_tokens(blob.replace("-", " ")),
        })
    if non_leaf:
        shown = ", ".join(non_leaf[:10])
        more = f" (and {len(non_leaf) - 10} more)" if len(non_leaf) > 10 else ""
        raise ValueError(
            f"topic catalog carries {len(non_leaf)} non-microtopic row(s): "
            f"{shown}{more}. Only microtopic ids may be assigned to a question."
        )
    if not out:
        raise ValueError(f"{path}: no usable microtopic rows")
    return out


# ── P1: per-paper readiness counters ─────────────────────────────────────────


def question_number_gaps(numbers: Iterable[Any]) -> tuple[list[int], list[int], int]:
    """(missing, repeated, non_numeric) over one paper's question numbers.

    ``missing`` is every integer in ``1..max`` that no question claims —
    anchored at 1 rather than at the lowest present value, because a paper
    whose numbering starts at 7 is missing six questions, not numbered oddly.
    ``repeated`` is every value claimed more than once. Both are sorted, so the
    report is byte-stable across runs.
    """
    seen: Counter[int] = Counter()
    non_numeric = 0
    for n in numbers:
        try:
            seen[int(str(n).strip())] += 1
        except (TypeError, ValueError):
            non_numeric += 1
    if not seen:
        return ([], [], non_numeric)
    top = max(seen)
    missing = [n for n in range(1, top + 1) if n not in seen]
    repeated = sorted(n for n, c in seen.items() if c > 1)
    return (missing, repeated, non_numeric)


def paper_readiness(questions: list[dict],
                    options_by_question: dict[str, list[dict]] | None) -> dict:
    """Every P1 counter for ONE paper's questions.

    ``options_by_question`` is ``None`` when no options file was supplied. The
    two option-dependent counters then carry ``None``, which the report prints
    as "not computed" — never as zero. A check that did not run and a check
    that found nothing are different claims, and only one of them is a pass.
    """
    by_section: Counter[str] = Counter()
    norm_counts: Counter[str] = Counter()
    non_ascii = repeat_char = short = 0
    for q in questions:
        by_section[(q.get("section") or "(unsectioned)")] += 1
        text = q.get("question_text") or ""
        norm = normalize_text(text)
        if norm:
            norm_counts[norm] += 1
        if text.strip() and has_non_ascii(text):
            non_ascii += 1
        if _REPEAT_CHAR.search(text):
            repeat_char += 1
        if len(text.strip()) < 15:
            short += 1

    dup_groups = {n: c for n, c in norm_counts.items() if c > 1}
    dup_questions = sum(dup_groups.values())

    missing_options = missing_answer_key = None
    if options_by_question is not None:
        missing_options = 0
        missing_answer_key = 0
        for q in questions:
            if (q.get("question_type") or "") != "mcq":
                continue
            opts = options_by_question.get(q.get("id"), [])
            if not opts:
                missing_options += 1
            # TWO independent sources for the key, and either one satisfying it
            # is enough: `pyq_questions.correct_option_id` is the column the
            # projection's eligibility gate reads, and `pyq_options.is_correct`
            # is what the option rows themselves claim. A question with neither
            # has no answer key by any reading. A question where the two
            # DISAGREE is a different defect — the sweep's
            # multiple_options_marked_correct / mcq_no_correct_option flags
            # catch that, and this counter deliberately does not double-report
            # it.
            if not q.get("correct_option_id") and not any(
                    o.get("is_correct") is True for o in opts):
                missing_answer_key += 1

    missing_nums, repeated_nums, non_numeric = question_number_gaps(
        q.get("question_number") for q in questions)

    return {
        "questions": len(questions),
        "by_section": dict(sorted(by_section.items())),
        "missing_options": missing_options,
        "missing_answer_key": missing_answer_key,
        "duplicate_stem_groups": len(dup_groups),
        "duplicate_stem_questions": dup_questions,
        "non_ascii": non_ascii,
        "repeat_char": repeat_char,
        "empty_or_short": short,
        "question_number_missing": missing_nums,
        "question_number_repeated": repeated_nums,
        "question_number_non_numeric": non_numeric,
    }


def corpus_duplicate_stems(questions: list[dict]) -> tuple[int, int]:
    """(groups, questions) sharing a normalised stem ACROSS the whole corpus.

    Per-paper duplication and corpus-wide duplication are different findings.
    A reasoning stem legitimately recurs between shifts of the same exam; the
    same stem twice inside one paper is an import defect. Both are reported,
    and neither is presented as the other.
    """
    counts = Counter(normalize_text(q.get("question_text")) for q in questions)
    counts.pop("", None)
    groups = {n: c for n, c in counts.items() if c > 1}
    return (len(groups), sum(groups.values()))


# ── P1: catalogue fit over a spread sample ───────────────────────────────────


def spread_sample(rows: list[dict], n: int) -> list[dict]:
    """``n`` rows strided evenly across ``rows`` — never the first n.

    A paper's first twenty questions are its easiest and most formulaic; a
    sample taken from the front reports a fit rate the corpus does not have.
    """
    count = len(rows)
    if n >= count:
        return list(rows)
    if n <= 0:
        return []
    stride = count / n
    picked: list[dict] = []
    seen: set[int] = set()
    for i in range(n):
        idx = min(count - 1, int(round(i * stride)))
        while idx in seen and idx < count - 1:
            idx += 1
        seen.add(idx)
        picked.append(rows[idx])
    return picked


def allocate_sample(section_sizes: dict[str, int], total: int) -> dict[str, int]:
    """Split a sample budget across sections in proportion to their size.

    Largest-remainder, so the allocations sum to exactly ``total`` (or to the
    corpus size when it is smaller) rather than to total±3, and so the split is
    deterministic instead of depending on dict order. Every non-empty section
    gets at least one row: a section that contributes nothing to the sample
    cannot contribute a gap candidate either, and "we did not look" would read
    in the report as "nothing found".
    """
    sizes = {k: v for k, v in section_sizes.items() if v > 0}
    if not sizes or total <= 0:
        return {}
    corpus = sum(sizes.values())
    budget = min(total, corpus)
    if budget < len(sizes):
        # Not enough budget for one per section: give one each to the largest
        # sections, in a deterministic order.
        ranked = sorted(sizes, key=lambda k: (-sizes[k], k))
        return {k: 1 for k in ranked[:budget]}

    exact = {k: budget * v / corpus for k, v in sizes.items()}
    alloc = {k: max(1, int(math.floor(v))) for k, v in exact.items()}
    # floor()+the min-1 floor can overshoot or undershoot; settle by remainder.
    while sum(alloc.values()) > budget:
        # Only a section allocated more than its floor of 1 can give a row
        # back; taking the last row off a small section would drop it out of
        # the sample entirely, which is the one thing the floor exists to stop.
        givers = [k for k in sorted(alloc) if alloc[k] > 1]
        if not givers:
            break
        alloc[max(givers, key=lambda k: (alloc[k] - exact[k], alloc[k]))] -= 1
    while sum(alloc.values()) < budget:
        k = max(sorted(alloc), key=lambda k: (exact[k] - alloc[k]))
        if alloc[k] >= sizes[k]:
            remaining = [x for x in sorted(alloc) if alloc[x] < sizes[x]]
            if not remaining:
                break
            k = remaining[0]
        alloc[k] += 1
    return {k: min(v, sizes[k]) for k, v in alloc.items()}


def best_fit(question_tokens: set[str], catalogue: list[dict]) -> tuple[dict | None, float]:
    """The catalogue row this stem lexically resembles most, and its coverage.

    Coverage is |overlap| / |microtopic tokens| — the share of what the
    MICROTOPIC is about that the stem mentions, not the share of the stem the
    microtopic explains. A stem is fifty words and a microtopic name is two;
    scoring the other way round would call every question unmatched.

    Ties break on the row with fewer tokens (the more specific microtopic) and
    then on id, so the report is stable across runs.
    """
    best: dict | None = None
    best_score = 0.0
    for row in catalogue:
        tokens = row["tokens"]
        if not tokens:
            continue
        score = len(tokens & question_tokens) / len(tokens)
        if score > best_score or (
                score == best_score and best is not None and score > 0 and
                (len(tokens), row["id"]) < (len(best["tokens"]), best["id"])):
            best, best_score = row, score
    return (best, best_score)


def catalogue_fit(questions: list[dict], catalogue: list[dict],
                  sample_size: int) -> dict:
    """Sample the corpus by section and report how much the catalogue covers.

    Returns the per-section fit counts, the sampled rows with their best match,
    and the ranked gap candidates. Nothing here is a proposal — see the module
    docstring.
    """
    by_section: dict[str, list[dict]] = {}
    for q in questions:
        by_section.setdefault(q.get("section") or "(unsectioned)", []).append(q)
    # Stable order inside a section so the stride picks the same rows each run.
    for rows in by_section.values():
        rows.sort(key=lambda q: (str(q.get("paper_id")), _qnum_key(q), str(q.get("id"))))

    alloc = allocate_sample({k: len(v) for k, v in by_section.items()}, sample_size)

    covered_tokens: set[str] = set()
    for row in catalogue:
        covered_tokens |= row["tokens"]

    sampled: list[dict] = []
    per_section: dict[str, dict] = {}
    gap_tokens: dict[str, Counter] = {}
    gap_examples: dict[str, dict[str, list[str]]] = {}

    for section in sorted(alloc):
        rows = spread_sample(by_section[section], alloc[section])
        matched = 0
        for q in rows:
            tokens = significant_tokens(q.get("question_text") or "")
            row, score = best_fit(tokens, catalogue)
            fits = bool(row) and score >= _FIT_COVERAGE
            matched += 1 if fits else 0
            sampled.append({
                "question_id": q.get("id"),
                "paper_id": q.get("paper_id"),
                "section": section,
                "question_number": q.get("question_number"),
                "fit": "matched" if fits else "unmatched",
                "best_topic_id": row["id"] if row else "",
                "best_topic_label": row["label"] if row else "",
                "coverage": round(score, 3),
            })
            if not fits:
                counter = gap_tokens.setdefault(section, Counter())
                examples = gap_examples.setdefault(section, {})
                for tok in sorted(tokens - covered_tokens):
                    counter[tok] += 1
                    examples.setdefault(tok, [])
                    if len(examples[tok]) < 3:
                        examples[tok].append(str(q.get("id")))
        per_section[section] = {
            "section_questions": len(by_section[section]),
            "sampled": len(rows),
            "matched": matched,
            "unmatched": len(rows) - matched,
        }

    candidates: list[dict] = []
    for section in sorted(gap_tokens):
        ranked = sorted(gap_tokens[section].items(), key=lambda kv: (-kv[1], kv[0]))
        for token, support in ranked:
            if support < _MIN_GAP_SUPPORT:
                continue
            candidates.append({
                "section": section,
                "candidate_token": token,
                "sampled_questions": support,
                "example_question_ids": gap_examples[section][token],
            })
        # Cap per section, after ranking, so the cut falls on the weakest.
        candidates = ([c for c in candidates if c["section"] != section]
                      + [c for c in candidates if c["section"] == section][:_GAP_LIST_CAP])

    return {
        "sample_size_requested": sample_size,
        "sample_size_actual": len(sampled),
        "per_section": per_section,
        "matched": sum(v["matched"] for v in per_section.values()),
        "unmatched": sum(v["unmatched"] for v in per_section.values()),
        "sampled_rows": sampled,
        "new_microtopic_candidates": sorted(
            candidates, key=lambda c: (c["section"], -c["sampled_questions"],
                                       c["candidate_token"])),
    }


def _qnum_key(q: dict) -> tuple:
    try:
        return (0, int(str(q.get("question_number")).strip()))
    except (TypeError, ValueError):
        return (1, str(q.get("question_number")))


# ── P4: projection readiness ─────────────────────────────────────────────────

# review_pyq_paper()'s pending -> verified provenance gate, migration
# 271_review_pyq_paper_question_count_gate.sql step 6. Re-stated here, not
# inferred: (a) source_type known, (b) a provenance anchor — source_url OR
# source_document_id, (c) the attached document validates, (d) the paper
# carries at least one question.
#
# (c) is NOT evaluated here. It reads `document_assets` — scope, kind, status,
# storage and an exam-id cross-check — and no export file carries those rows.
# A paper this report calls ready may still be blocked by its document, so the
# report says so per paper rather than implying a pass it did not test.
#
# NAMING: the DB function appends 'no_questions' where the Python endpoint
# appends 'questions' for the same condition (migration 271's own note). Both
# labels are emitted so an operator can match either error message.
_GATE_LABELS = {
    "source_type": "source_type",
    "source_url": "source_url",
    "questions": "no_questions (DB) / questions (API)",
}


def projection_readiness(paper: dict) -> dict:
    """The blocking fields ``review_pyq_paper`` would report for one paper."""
    blocking: list[str] = []
    source_type = paper.get("source_type")
    if source_type in (None, "", "unknown"):
        blocking.append(_GATE_LABELS["source_type"])
    url = paper.get("source_url")
    if not (url and str(url).strip()) and not paper.get("source_document_id"):
        blocking.append(_GATE_LABELS["source_url"])
    if not (paper.get("question_count") or 0):
        blocking.append(_GATE_LABELS["questions"])
    return {
        "paper_id": paper.get("id"),
        "trust_status": paper.get("trust_status"),
        "source_type": source_type,
        "has_source_url": bool(url and str(url).strip()),
        "has_source_document_id": bool(paper.get("source_document_id")),
        "question_count": paper.get("question_count") or 0,
        "gate": "pass" if not blocking else "blocked",
        "blocking_fields": blocking,
        # (c) above: stated, never silently assumed.
        "document_checks_not_evaluated": bool(paper.get("source_document_id")),
    }


# ── report building ──────────────────────────────────────────────────────────


def paper_label(paper: dict) -> str:
    """A human handle for a paper: its code and shift, falling back to the id.

    Thirteen papers in one year are indistinguishable by year, so the label is
    what makes a per-paper table readable.
    """
    bits = [str(paper.get(k)) for k in ("paper_code", "shift", "paper_date")
            if paper.get(k)]
    return " / ".join(bits) if bits else str(paper.get("id"))


_CSV_FIELDS = [
    "paper_id", "paper_label", "year", "trust_status", "questions",
    "sections", "missing_options", "missing_answer_key",
    "duplicate_stem_groups", "duplicate_stem_questions",
    "non_ascii", "repeat_char", "empty_or_short",
    "question_number_missing_count", "question_number_missing",
    "question_number_repeated", "question_number_non_numeric",
    "projection_gate", "blocking_fields",
]

_NOT_COMPUTED = "not computed"


def _cell(value: Any) -> str:
    return _NOT_COMPUTED if value is None else str(value)


def build_report(questions: list[dict], papers: list[dict],
                 options: list[dict] | None,
                 catalogue: list[dict] | None,
                 sample_size: int) -> dict:
    """Every number in the report, as data. Rendering is separate."""
    options_by_question: dict[str, list[dict]] | None = None
    if options is not None:
        options_by_question = {}
        for o in options:
            qid = o.get("question_id")
            if qid:
                options_by_question.setdefault(qid, []).append(o)

    q_by_paper: dict[str, list[dict]] = {}
    for q in questions:
        q_by_paper.setdefault(str(q.get("paper_id") or ""), []).append(q)

    rows: list[dict] = []
    for paper in sorted(papers, key=lambda p: (str(p.get("paper_code") or ""),
                                               str(p.get("shift") or ""),
                                               str(p.get("id")))):
        pid = str(paper.get("id"))
        counters = paper_readiness(q_by_paper.get(pid, []), options_by_question)
        gate = projection_readiness(paper)
        rows.append({"paper": paper, "label": paper_label(paper),
                     "counters": counters, "gate": gate})

    # A question whose paper is not in papers_export.json would vanish from a
    # per-paper report entirely. Named rather than dropped.
    known = {str(p.get("id")) for p in papers}
    orphaned = sorted(pid for pid in q_by_paper if pid not in known)

    dup_groups, dup_questions = corpus_duplicate_stems(questions)
    fit = (catalogue_fit(questions, catalogue, sample_size)
           if catalogue else None)

    return {
        "totals": {
            "papers": len(papers),
            "questions": len(questions),
            "options_supplied": options is not None,
            "corpus_duplicate_stem_groups": dup_groups,
            "corpus_duplicate_stem_questions": dup_questions,
            "papers_gate_pass": sum(1 for r in rows if r["gate"]["gate"] == "pass"),
            "papers_gate_blocked": sum(1 for r in rows if r["gate"]["gate"] != "pass"),
        },
        "papers": rows,
        "orphaned_paper_ids": orphaned,
        "catalogue_fit": fit,
    }


def csv_rows(report: dict) -> list[dict]:
    out: list[dict] = []
    for r in report["papers"]:
        c, g, p = r["counters"], r["gate"], r["paper"]
        missing = c["question_number_missing"]
        out.append({
            "paper_id": p.get("id"),
            "paper_label": r["label"],
            "year": p.get("year"),
            "trust_status": p.get("trust_status"),
            "questions": c["questions"],
            "sections": "; ".join(f"{k}={v}" for k, v in c["by_section"].items()),
            "missing_options": _cell(c["missing_options"]),
            "missing_answer_key": _cell(c["missing_answer_key"]),
            "duplicate_stem_groups": c["duplicate_stem_groups"],
            "duplicate_stem_questions": c["duplicate_stem_questions"],
            "non_ascii": c["non_ascii"],
            "repeat_char": c["repeat_char"],
            "empty_or_short": c["empty_or_short"],
            "question_number_missing_count": len(missing),
            # Capped: a paper with no questions lists every number to its max,
            # which is a wall of text in a cell nobody reads.
            "question_number_missing": ",".join(str(n) for n in missing[:50])
                                       + (" …" if len(missing) > 50 else ""),
            "question_number_repeated": ",".join(str(n) for n in c["question_number_repeated"]),
            "question_number_non_numeric": c["question_number_non_numeric"],
            "projection_gate": g["gate"],
            "blocking_fields": ",".join(g["blocking_fields"]),
        })
    return out


def render_markdown(report: dict, *, sources: dict[str, str]) -> str:
    t = report["totals"]
    lines: list[str] = []
    add = lines.append

    add("# PYQ corpus readiness")
    add("")
    add("Generated by `scripts/ssc_cgl_readiness.py` from an offline export. "
        "Read-only: no tag, difficulty, review verdict or projection was "
        "written by this run.")
    add("")
    add("| input | file |")
    add("| --- | --- |")
    for key in sorted(sources):
        add(f"| {key} | `{sources[key]}` |")
    add("")
    add(f"- papers: **{t['papers']}**")
    add(f"- questions: **{t['questions']}**")
    add(f"- questions sharing a normalised stem corpus-wide: "
        f"**{t['corpus_duplicate_stem_questions']}** across "
        f"{t['corpus_duplicate_stem_groups']} group(s)")
    add(f"- papers passing `review_pyq_paper`'s provenance gate: "
        f"**{t['papers_gate_pass']} pass / {t['papers_gate_blocked']} blocked**")
    if not t["options_supplied"]:
        add("- **option rows were NOT supplied.** `missing_options` and "
            "`missing_answer_key` are *not computed* below — not zero. "
            "Re-run with `--options options_export.json` to evaluate them.")
    if report["orphaned_paper_ids"]:
        add(f"- questions reference {len(report['orphaned_paper_ids'])} paper id(s) "
            f"absent from the papers export: "
            f"{', '.join(report['orphaned_paper_ids'])}")
    add("")

    add("## P1 — per-paper readiness")
    add("")
    add("| paper | questions | missing options | missing answer key | dup stems "
        "(q/groups) | non-ascii | repeat-char | short | qnum missing | qnum repeated |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in report["papers"]:
        c = r["counters"]
        add(f"| {r['label']} | {c['questions']} | {_cell(c['missing_options'])} | "
            f"{_cell(c['missing_answer_key'])} | "
            f"{c['duplicate_stem_questions']}/{c['duplicate_stem_groups']} | "
            f"{c['non_ascii']} | {c['repeat_char']} | {c['empty_or_short']} | "
            f"{len(c['question_number_missing'])} | "
            f"{len(c['question_number_repeated'])} |")
    add("")

    add("### Section split")
    add("")
    add("| paper | section | questions |")
    add("| --- | --- | ---: |")
    for r in report["papers"]:
        for section, n in r["counters"]["by_section"].items():
            add(f"| {r['label']} | {section} | {n} |")
    add("")

    gapped = [r for r in report["papers"]
              if r["counters"]["question_number_missing"]
              or r["counters"]["question_number_repeated"]]
    add("### question_number gaps")
    add("")
    if not gapped:
        add("No paper has a missing or repeated `question_number`.")
    else:
        add("| paper | missing | repeated | non-numeric |")
        add("| --- | --- | --- | ---: |")
        for r in gapped:
            c = r["counters"]
            missing = c["question_number_missing"]
            shown = ", ".join(str(n) for n in missing[:50])
            if len(missing) > 50:
                shown += f", … ({len(missing)} total)"
            add(f"| {r['label']} | {shown or '—'} | "
                f"{', '.join(str(n) for n in c['question_number_repeated']) or '—'} | "
                f"{c['question_number_non_numeric']} |")
    add("")

    fit = report["catalogue_fit"]
    add("## P1 — catalogue fit (sample)")
    add("")
    if fit is None:
        add("Not run: no `--topic-catalog` was supplied.")
    else:
        add("**This is a lexical coverage signal, not a tag proposal.** A "
            "question counts as *matched* when at least "
            f"{int(_FIT_COVERAGE * 100)}% of some existing microtopic's own "
            "significant tokens appear in its stem. An *unmatched* question is "
            "not an untaggable one — it is a question the existing catalogue "
            "does not describe in words the stem repeats. The authoritative "
            "mapping is the proposer's, reviewed by a human.")
        add("")
        add(f"Sampled **{fit['sample_size_actual']}** of {t['questions']} "
            f"questions (requested {fit['sample_size_requested']}), spread "
            f"across sections in proportion to their size.")
        add("")
        add("| section | questions | sampled | matched | unmatched |")
        add("| --- | ---: | ---: | ---: | ---: |")
        for section in sorted(fit["per_section"]):
            v = fit["per_section"][section]
            add(f"| {section} | {v['section_questions']} | {v['sampled']} | "
                f"{v['matched']} | {v['unmatched']} |")
        add(f"| **total** | {t['questions']} | {fit['sample_size_actual']} | "
            f"**{fit['matched']}** | **{fit['unmatched']}** |")
        add("")
        add("### Proposed new microtopics — candidates only, nothing applied")
        add("")
        if not fit["new_microtopic_candidates"]:
            add("No recurring uncovered theme reached the "
                f"{_MIN_GAP_SUPPORT}-question support floor.")
        else:
            add("Recurring content words from the unmatched sample that NO "
                "existing microtopic's name, slug or description covers, ranked "
                "by how many sampled questions carry them. Naming a microtopic "
                "from a row here is a taxonomy decision for a human; this run "
                "wrote nothing to `topics`.")
            add("")
            add("| section | candidate term | sampled questions | example question ids |")
            add("| --- | --- | ---: | --- |")
            for c in fit["new_microtopic_candidates"]:
                add(f"| {c['section']} | `{c['candidate_token']}` | "
                    f"{c['sampled_questions']} | "
                    f"{', '.join(c['example_question_ids'])} |")
    add("")

    add("## P4 — projection readiness")
    add("")
    add("`review_pyq_paper()`'s pending → verified provenance gate (migration "
        "271, step 6): **(a)** `source_type` is set and not `unknown`, **(b)** "
        "`source_url` or `source_document_id` is present, **(d)** the paper "
        "carries at least one question. Check **(c)**, the attached document's "
        "scope / kind / status / storage / exam-id validation, reads "
        "`document_assets` and is NOT evaluated here — a paper below marked "
        "`pass` that carries a `source_document_id` may still be blocked by it.")
    add("")
    add("| paper | gate | source_type | source_url | source_document_id | "
        "questions | blocking fields |")
    add("| --- | --- | --- | :-: | :-: | ---: | --- |")
    for r in report["papers"]:
        g = r["gate"]
        add(f"| {r['label']} | **{g['gate']}** | {g['source_type'] or '—'} | "
            f"{'yes' if g['has_source_url'] else 'no'} | "
            f"{'yes' if g['has_source_document_id'] else 'no'} | "
            f"{g['question_count']} | {', '.join(g['blocking_fields']) or '—'} |")
    add("")
    doc_papers = [r["label"] for r in report["papers"]
                  if r["gate"]["document_checks_not_evaluated"]]
    if doc_papers:
        add(f"Document checks (c) unevaluated for: {', '.join(doc_papers)}.")
        add("")
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--questions", required=True,
                    help="questions_export.json from `pyq_question_review.py export`")
    ap.add_argument("--papers", required=True,
                    help="papers_export.json from the same export; carries the "
                         "provenance fields the P4 gate reads")
    ap.add_argument("--options", default=None,
                    help="options_export.json. OPTIONAL, and its absence means "
                         "the option counters did not run — not that they passed.")
    ap.add_argument("--topic-catalog", default=None,
                    help="microtopic catalogue JSON. Without it the "
                         "catalogue-fit section is skipped.")
    ap.add_argument("--sample-size", type=int, default=100,
                    help="questions to sample for the catalogue-fit check "
                         "(default 100), spread across sections in proportion "
                         "to their size")
    ap.add_argument("--out-md", default="workbench/audit/ssc_cgl_readiness.md")
    ap.add_argument("--out-csv", default="workbench/audit/ssc_cgl_readiness.csv")
    ap.add_argument("--out-fit-csv", default=None,
                    help="optionally write the sampled rows and their best "
                         "lexical match here, one row per sampled question")
    ap.add_argument("--apply", action="store_true",
                    help="write the report files; without it the run prints "
                         "the report and writes nothing")
    args = ap.parse_args(argv)

    try:
        questions = _load_json_list(args.questions, "question")
        papers = _load_json_list(args.papers, "paper")
        options = _load_json_list(args.options, "option") if args.options else None
        catalogue = load_catalogue(args.topic_catalog) if args.topic_catalog else None
    except (OSError, ValueError) as exc:
        print(f"error: cannot read inputs — {exc}", file=sys.stderr)
        return 2

    if args.sample_size < 0:
        print("error: --sample-size cannot be negative", file=sys.stderr)
        return 2

    report = build_report(questions, papers, options, catalogue, args.sample_size)
    sources = {"questions": args.questions, "papers": args.papers}
    if args.options:
        sources["options"] = args.options
    if args.topic_catalog:
        sources["topic catalogue"] = args.topic_catalog
    markdown = render_markdown(report, sources=sources)

    t = report["totals"]
    print(f"{t['papers']} paper(s), {t['questions']} question(s); "
          f"{t['papers_gate_pass']} pass the projection gate, "
          f"{t['papers_gate_blocked']} blocked.")
    if options is None:
        print("  option counters NOT computed (no --options).")
    if catalogue is None:
        print("  catalogue fit NOT computed (no --topic-catalog).")
    else:
        fit = report["catalogue_fit"]
        print(f"  catalogue fit: {fit['matched']} matched / {fit['unmatched']} "
              f"unmatched of {fit['sample_size_actual']} sampled; "
              f"{len(fit['new_microtopic_candidates'])} gap candidate(s).")

    if not args.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply to write "
              f"{args.out_md} and {args.out_csv}.\n")
        print(markdown)
        return 0

    md_path = Path(args.out_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown + "\n", encoding="utf-8")

    csv_path = Path(args.out_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(csv_rows(report))

    print(f"\nwrote {md_path}")
    print(f"wrote {csv_path}")

    fit = report["catalogue_fit"]
    if args.out_fit_csv and fit:
        fit_path = Path(args.out_fit_csv)
        fit_path.parent.mkdir(parents=True, exist_ok=True)
        with fit_path.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=[
                "question_id", "paper_id", "section", "question_number",
                "fit", "best_topic_id", "best_topic_label", "coverage"],
                extrasaction="ignore")
            w.writeheader()
            w.writerows(fit["sampled_rows"])
        print(f"wrote {fit_path}")
    elif args.out_fit_csv:
        print("--out-fit-csv ignored: no catalogue fit was computed.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
