"""D10 PYQ readiness shared aggregation module.

Design decision (D10): PYQ evidence is always measured exam-wide.

The exam_cycle_id on pyq_papers records *provenance* (which cycle the paper
belonged to) — it is NOT a filter.  Filtering by cycle would hide verified
questions from earlier cycles and undercount readiness, which is both
incorrect and misleading to admins.  The selected_cycle_id parameter is
surfaced in the output so callers can display it, but it never changes which
questions count as verified.

The three-gate rule (immutable):
  A distinct PYQ question counts as "verified" only when ALL THREE pass:
  1. parent pyq_papers.trust_status == "verified"
  2. pyq_questions.reviewer_status == "verified"
  3. at least one pyq_question_topic_tags row has reviewer_status == "verified"

Multiple verified tags on the same question still count that question once.

This module is pure computation: callers (work_queue.py, readiness.py, or any
future consumer) handle all database I/O and pass pre-loaded lists of dicts.
No Supabase client, no execute_or_raise, no network calls exist here.
"""
from __future__ import annotations

from typing import Any

# States that indicate a question is awaiting reviewer action.
_QUESTION_PENDING_STATES: frozenset[str] = frozenset({"pending", "needs_correction"})

# States that indicate a tag is awaiting reviewer action.
_TAG_PENDING_STATES: frozenset[str] = frozenset({"pending", "needs_correction"})

# Only "verified" and "rejected" are terminal pyq_papers.trust_status values.
# Schema: pyq_papers.trust_status IN ('pending', 'verified', 'rejected').
_PAPER_TERMINAL_STATES: frozenset[str] = frozenset({"verified", "rejected"})


def aggregate_pyq_evidence(
    *,
    papers: list[dict],
    questions: list[dict],
    topic_tags: list[dict],
    selected_cycle_id: str | None = None,
) -> dict:
    """Aggregate PYQ readiness evidence for a single exam using the D10 three-gate rule.

    Parameters
    ----------
    papers:
        All pyq_papers rows for the exam.  Each dict must have at least:
        ``id``, ``exam_cycle_id`` (nullable), ``trust_status``.
    questions:
        All pyq_questions rows for those papers.  Each dict must have at least:
        ``id``, ``pyq_paper_id``, ``reviewer_status``.
    topic_tags:
        All pyq_question_topic_tags rows for those questions.  Each dict must
        have at least ``id``, ``question_id``, ``reviewer_status``.
    selected_cycle_id:
        The cycle the caller considers "current" (for display purposes only).
        Does NOT filter any counts — paper/question/tag totals are always
        exam-wide regardless of this value.

    Returns
    -------
    dict with keys:
        scope, selected_cycle_id, papers_total, selected_cycle_papers,
        other_cycle_papers, unscoped_papers, questions_total,
        verified_question_count, questions_eligible_before_tag_gate,
        pending_question_count, pending_tag_count, papers_pending_review,
        state.

    Invariants:
        selected_cycle_papers + other_cycle_papers + unscoped_papers == papers_total
        verified_question_count never changes regardless of selected_cycle_id
        papers_total never changes regardless of selected_cycle_id
    """
    # ── Paper-level counts (exam-wide, never cycle-filtered) ─────────────────

    papers_total = len(papers)

    selected_cycle_papers = 0
    other_cycle_papers = 0
    unscoped_papers = 0
    papers_pending_review = 0
    non_rejected_papers = 0

    # paper id → trust_status for gate 1 look-up.
    verified_paper_ids: set[str] = set()

    for paper in papers:
        cycle_id_on_paper = paper.get("exam_cycle_id")
        trust_status = paper.get("trust_status") or ""
        paper_id = paper.get("id")

        # Cycle provenance bucketing.
        if cycle_id_on_paper is None:
            unscoped_papers += 1
        elif cycle_id_on_paper == selected_cycle_id:
            selected_cycle_papers += 1
        else:
            other_cycle_papers += 1

        # Paper pending review: not in terminal states (verified / rejected).
        if trust_status not in _PAPER_TERMINAL_STATES:
            papers_pending_review += 1

        if trust_status != "rejected":
            non_rejected_papers += 1

        # Gate 1: paper must be verified.
        if trust_status == "verified" and paper_id:
            verified_paper_ids.add(paper_id)

    # ── Question-level counts ────────────────────────────────────────────────

    questions_total = len(questions)
    pending_question_count = 0

    # Questions that cleared gates 1+2 (verified paper + verified question);
    # still need gate 3 (at least one verified tag).
    eligible_question_ids: set[str] = set()

    for question in questions:
        paper_id = question.get("pyq_paper_id")
        reviewer_status = question.get("reviewer_status") or ""
        question_id = question.get("id")

        if reviewer_status in _QUESTION_PENDING_STATES:
            pending_question_count += 1

        # Gates 1+2.
        if (
            question_id
            and reviewer_status == "verified"
            and paper_id in verified_paper_ids
        ):
            eligible_question_ids.add(question_id)

    questions_eligible_before_tag_gate = len(eligible_question_ids)

    # ── Tag-level counts ─────────────────────────────────────────────────────

    pending_tag_count = 0

    # Question ids that have at least one verified tag (gate 3).
    questions_with_verified_tag: set[str] = set()

    for tag in topic_tags:
        question_id = tag.get("question_id")
        reviewer_status = tag.get("reviewer_status") or ""

        if reviewer_status in _TAG_PENDING_STATES:
            pending_tag_count += 1

        # Gate 3: tag must be verified AND the question must have cleared gates 1+2.
        if (
            reviewer_status == "verified"
            and question_id in eligible_question_ids
        ):
            questions_with_verified_tag.add(question_id)

    # Final verified count: questions that cleared all three gates (distinct).
    verified_question_count = len(questions_with_verified_tag)

    # ── State derivation ─────────────────────────────────────────────────────
    # "failed" is never set here; callers set it externally when appropriate.

    # "missing": no papers at all, or every paper is rejected (no usable corpus).
    # "review_pending": at least one non-rejected paper exists but no verified question yet.
    if papers_total == 0 or non_rejected_papers == 0:
        state = "missing"
    elif verified_question_count >= 1:
        state = "ready"
    else:
        state = "review_pending"

    return {
        "scope": "exam_wide",
        "selected_cycle_id": selected_cycle_id,
        "papers_total": papers_total,
        "selected_cycle_papers": selected_cycle_papers,
        "other_cycle_papers": other_cycle_papers,
        "unscoped_papers": unscoped_papers,
        "questions_total": questions_total,
        "verified_question_count": verified_question_count,
        "questions_eligible_before_tag_gate": questions_eligible_before_tag_gate,
        "pending_question_count": pending_question_count,
        "pending_tag_count": pending_tag_count,
        "papers_pending_review": papers_pending_review,
        "state": state,
    }


def aggregate_pyq_evidence_batch(
    *,
    papers: list[dict],
    questions: list[dict],
    topic_tags: list[dict],
) -> dict[str, dict]:
    """Aggregate PYQ readiness evidence for multiple exams in a single pass.

    Uses the same D10 three-gate rule as ``aggregate_pyq_evidence``.  No cycle
    filter is applied (exam-wide counts only).  Each entry uses
    ``selected_cycle_id=None``.

    Parameters
    ----------
    papers:
        pyq_papers rows for *multiple* exams.  Each dict must have at least:
        ``id``, ``exam_id``, ``exam_cycle_id`` (nullable), ``trust_status``.
    questions:
        pyq_questions rows for those papers.  Each dict must have at least:
        ``id``, ``pyq_paper_id``, ``reviewer_status``.
    topic_tags:
        pyq_question_topic_tags rows for those questions.  Each dict must have
        at least ``id``, ``question_id``, ``reviewer_status``.

    Returns
    -------
    dict mapping exam_id (str) → aggregate_pyq_evidence result dict.
    One entry per distinct exam_id found in ``papers``.
    """
    # Partition papers by exam_id.
    exam_ids: list[str] = []
    papers_by_exam: dict[str, list[dict]] = {}
    for paper in papers:
        exam_id = paper.get("exam_id")
        if exam_id is None:
            continue
        if exam_id not in papers_by_exam:
            exam_ids.append(exam_id)
            papers_by_exam[exam_id] = []
        papers_by_exam[exam_id].append(paper)

    # Build paper_id → exam_id map for routing questions.
    paper_exam: dict[str, str] = {}
    for exam_id, exam_papers in papers_by_exam.items():
        for paper in exam_papers:
            pid = paper.get("id")
            if pid is not None:
                paper_exam[pid] = exam_id

    # Partition questions by exam_id (via paper_id).
    questions_by_exam: dict[str, list[dict]] = {eid: [] for eid in exam_ids}
    # Build question_id → exam_id map for routing tags.
    question_exam: dict[str, str] = {}
    for question in questions:
        paper_id = question.get("pyq_paper_id")
        exam_id = paper_exam.get(paper_id)  # type: ignore[arg-type]
        if exam_id is None:
            continue
        questions_by_exam[exam_id].append(question)
        qid = question.get("id")
        if qid is not None:
            question_exam[qid] = exam_id

    # Partition topic_tags by exam_id (via question_id).
    tags_by_exam: dict[str, list[dict]] = {eid: [] for eid in exam_ids}
    for tag in topic_tags:
        question_id = tag.get("question_id")
        exam_id = question_exam.get(question_id)  # type: ignore[arg-type]
        if exam_id is None:
            continue
        tags_by_exam[exam_id].append(tag)

    # Aggregate each exam independently (reuses single-exam logic).
    result: dict[str, dict] = {}
    for exam_id in exam_ids:
        result[exam_id] = aggregate_pyq_evidence(
            papers=papers_by_exam[exam_id],
            questions=questions_by_exam[exam_id],
            topic_tags=tags_by_exam[exam_id],
            selected_cycle_id=None,
        )

    return result
