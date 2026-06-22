"""PR-fix-6 Fix 3 — runtime ``criteria`` selector.

``select_questions_for_template`` must resolve a section's ``criteria`` selector
to concrete published questions, honouring bank filters and the optional
``difficulty_mix`` distribution. Before this fix only ``fixed`` selectors were
handled, so every criteria-authored template fell through to PR1's seed.
"""
from __future__ import annotations

import uuid

import pytest

from app.study_os import mock_engine as svc
from app.study_os.mock_engine import _criteria_difficulty_targets
from tests.persona_questions._stub import SBStub


def _q(difficulty: str, *, exam_family: str = "TEST", topic_id: str | None = None) -> dict:
    qid = str(uuid.uuid4())
    opts = [
        {"id": f"opt-{qid}-{i}", "question_id": qid, "option_text": f"Opt {i}", "option_index": i, "is_correct": i == 2}
        for i in range(1, 5)
    ]
    return {
        "id": qid,
        "exam_family": exam_family,
        "topic_id": topic_id,
        "question_text": f"Q {qid[:8]}",
        "question_type": "mcq",
        "difficulty": difficulty,
        "correct_option_id": opts[1]["id"],
        "reviewer_status": "published",
        "options": opts,
    }


def _db_with_section(selector: dict, question_count: int, questions: list[dict]) -> tuple[SBStub, str]:
    template_id = "tmpl-criteria-1"
    section = {
        "id": "sec-1",
        "template_id": template_id,
        "section_index": 0,
        "name": "Section A",
        "question_count": question_count,
        "selector": selector,
    }
    db = {
        "mock_template_sections": [section],
        "mock_question_bank": [dict(q) for q in questions],
        "mock_question_options": [o for q in questions for o in q["options"]],
    }
    return SBStub(db), template_id


def test_difficulty_targets_sum_to_total():
    targets = _criteria_difficulty_targets({"easy": 0.5, "medium": 0.3, "hard": 0.2}, 10)
    assert sum(targets.values()) == 10
    assert targets == {"easy": 5, "medium": 3, "hard": 2}


def test_difficulty_targets_largest_remainder():
    # 0.333.. each over 10 → floors {3,3,3}=9, remainder 1 to the largest fraction.
    targets = _criteria_difficulty_targets({"easy": 1 / 3, "medium": 1 / 3, "hard": 1 / 3}, 10)
    assert sum(targets.values()) == 10


def test_criteria_selects_by_difficulty_mix():
    questions = (
        [_q("easy") for _ in range(6)]
        + [_q("medium") for _ in range(4)]
        + [_q("hard") for _ in range(3)]
    )
    sb, template_id = _db_with_section(
        {"mode": "criteria", "filters": {"difficulty_mix": {"easy": 0.5, "medium": 0.3, "hard": 0.2}}},
        10,
        questions,
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    assert len(selected) == 10
    by_diff: dict[str, int] = {}
    for q in selected:
        by_diff[q["difficulty"]] = by_diff.get(q["difficulty"], 0) + 1
    assert by_diff == {"easy": 5, "medium": 3, "hard": 2}
    # options are attached so the attempt can render answer choices
    assert all(q["options"] for q in selected)


def test_criteria_backfills_short_bucket():
    # mix wants all-easy but only 4 easy exist; the rest backfilled from pool.
    questions = [_q("easy") for _ in range(4)] + [_q("medium") for _ in range(8)]
    sb, template_id = _db_with_section(
        {"mode": "criteria", "filters": {"difficulty_mix": {"easy": 1.0}}},
        10,
        questions,
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    assert len(selected) == 10  # 4 easy + 6 backfilled mediums


def test_criteria_without_mix_takes_question_count():
    questions = [_q("easy") for _ in range(20)]
    sb, template_id = _db_with_section(
        {"mode": "criteria", "filters": {}},
        7,
        questions,
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    assert len(selected) == 7


def test_criteria_filters_exam_family():
    questions = [_q("easy", exam_family="IBPS") for _ in range(5)] + [_q("easy", exam_family="SSC") for _ in range(5)]
    sb, template_id = _db_with_section(
        {"mode": "criteria", "filters": {"exam_family": "IBPS"}},
        5,
        questions,
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    assert len(selected) == 5
    assert all(q["exam_family"] == "IBPS" for q in selected)


def test_criteria_excludes_unpublished():
    questions = [_q("easy") for _ in range(3)]
    questions.append({**_q("easy"), "reviewer_status": "draft"})
    sb, template_id = _db_with_section(
        {"mode": "criteria", "filters": {}},
        3,  # request exactly the 3 published; fail-closed rejects under-count
        questions,
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    # only the 3 published questions are eligible; the draft is excluded
    assert len(selected) == 3


def test_criteria_excludes_fixtures_keeps_null_and_authored():
    """The criteria pool must drop ONLY source_type='e2e_fixture' rows. A plain
    `neq` would also drop NULL-provenance rows (NULL <> 'e2e_fixture' is NULL in
    Postgres), so the legacy authored questions with no source_type must still be
    eligible alongside explicit non-fixture provenance."""
    null_prov = _q("easy")                              # no source_type → NULL
    authored = {**_q("easy"), "source_type": "authored"}
    fixture = {**_q("easy"), "source_type": "e2e_fixture"}
    sb, template_id = _db_with_section(
        {"mode": "criteria", "filters": {}},
        2,  # request exactly the 2 non-fixture; fail-closed rejects under-count
        [null_prov, authored, fixture],
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    ids = {q["id"] for q in selected}
    assert fixture["id"] not in ids        # fixture excluded
    assert null_prov["id"] in ids          # NULL provenance retained
    assert authored["id"] in ids           # non-fixture retained
    assert len(selected) == 2


def test_fixed_selector_still_loads_e2e_fixtures():
    """Regression guard: isolation must not break E2E. The fixed-id selector —
    exactly how app/supabase/seeds/e2e_fixtures.sql wires its template — still
    loads source_type='e2e_fixture' rows inside the E2E DB."""
    fixtures = [{**_q("easy"), "source_type": "e2e_fixture"} for _ in range(3)]
    sb, template_id = _db_with_section(
        {"mode": "fixed", "question_ids": [q["id"] for q in fixtures]},
        3,
        fixtures,
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    assert {q["id"] for q in selected} == {q["id"] for q in fixtures}
    assert all(q["source_type"] == "e2e_fixture" for q in selected)


def test_criteria_stale_pyq_excluded_and_backfilled():
    """Regression: stale/inactive PYQ-derived rows are filtered from the criteria
    pool BEFORE allocation so they cannot displace authored questions and silently
    shorten the section.

    Pool (sorted by id, pyq-mock sorts first): pyq-mock, authored-0..authored-2.
    Without the lineage-in-pool fix, the selector picks [pyq-mock, a-0, a-1]
    then the caller's lineage guard drops pyq-mock → only 2 questions returned.
    With the fix, pyq-mock is excluded from the pool before selection, so the
    selector correctly picks authored-0..authored-2 → 3 questions returned.
    """
    # Use UUIDs that sort pyq-mock before the authored rows.
    pyq_mock_id = "00000000-0000-0000-0000-000000000001"
    authored_ids = [
        "aaaaaaaa-0000-0000-0000-000000000001",
        "aaaaaaaa-0000-0000-0000-000000000002",
        "aaaaaaaa-0000-0000-0000-000000000003",
    ]
    pyq_question_id = "pyq-src-1"

    def _q_bank(qid: str, pyq_question_id: str | None = None) -> dict:
        opts = [{"id": f"opt-{qid}-{i}", "question_id": qid, "option_text": f"Opt {i}",
                 "option_index": i, "is_correct": i == 0}
                for i in range(4)]
        return {
            "id": qid,
            "exam_family": "TEST",
            "question_text": f"Q {qid[:8]}",
            "question_type": "mcq",
            "difficulty": "medium",
            "correct_option_id": f"opt-{qid}-0",
            "reviewer_status": "published",
            "pyq_question_id": pyq_question_id,
            "options": opts,
        }

    template_id = "tmpl-criteria-stale"
    section = {
        "id": "sec-stale",
        "template_id": template_id,
        "section_index": 0,
        "name": "Stale Section",
        "question_count": 3,
        "selector": {"mode": "criteria", "filters": {}},
    }
    questions = [_q_bank(pyq_mock_id, pyq_question_id)] + [_q_bank(aid) for aid in authored_ids]
    db = {
        "mock_template_sections": [section],
        "mock_question_bank": [dict(q) for q in questions],
        "mock_question_options": [o for q in questions for o in q["options"]],
        # pyq-mock has a stale projection (sync_status != 'active') → should be excluded
        "pyq_mock_question_projections": [
            {"mock_question_id": pyq_mock_id, "sync_status": "stale"},
        ],
    }
    sb = SBStub(db)
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    selected_ids = {q["id"] for q in selected}
    assert len(selected) == 3, f"expected 3 questions, got {len(selected)}"
    assert pyq_mock_id not in selected_ids, "stale PYQ must not appear in selection"
    assert selected_ids == set(authored_ids), "all three authored questions must be selected"


def test_criteria_thin_pool_raises_lookup_error():
    """Regression: a genuinely underfilled pool must raise LookupError, not silently
    start an attempt with fewer questions than the section target.

    Setup: section wants 3; pool has 1 stale PYQ-derived + 2 authored (3 total, but
    only 2 survive the lineage filter). start_attempt() must be rejected before
    writing any attempt or response rows.
    """
    pyq_mock_id = "00000000-0000-0000-0000-000000000002"
    authored_ids = [
        "bbbbbbbb-0000-0000-0000-000000000001",
        "bbbbbbbb-0000-0000-0000-000000000002",
    ]
    pyq_question_id = "pyq-src-thin"

    def _q_bank(qid: str, pyq_question_id: str | None = None) -> dict:
        opts = [{"id": f"opt-{qid}-{i}", "question_id": qid, "option_text": f"Opt {i}",
                 "option_index": i, "is_correct": i == 0}
                for i in range(4)]
        return {
            "id": qid,
            "exam_family": "TEST",
            "question_text": f"Q {qid[:8]}",
            "question_type": "mcq",
            "difficulty": "medium",
            "correct_option_id": f"opt-{qid}-0",
            "reviewer_status": "published",
            "pyq_question_id": pyq_question_id,
            "options": opts,
        }

    template = {
        "id": "tmpl-thin-pool",
        "slug": "thin-pool-mock",
        "name": "Thin Pool Mock",
        "exam_family": "TEST",
        "total_questions": 3,
        "duration_sec": 300,
        "negative_marking": False,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.0,
        "config": {},
        "status": "active",
    }
    section = {
        "id": "sec-thin",
        "template_id": template["id"],
        "section_index": 0,
        "name": "Thin Section",
        "question_count": 3,
        "selector": {"mode": "criteria", "filters": {}},
    }
    questions = [_q_bank(pyq_mock_id, pyq_question_id)] + [_q_bank(aid) for aid in authored_ids]
    db = {
        "mock_templates": [template],
        "mock_template_sections": [section],
        "mock_question_bank": [dict(q) for q in questions],
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "pyq_mock_question_projections": [
            {"mock_question_id": pyq_mock_id, "sync_status": "stale"},
        ],
    }
    sb = SBStub(db)
    with pytest.raises(LookupError, match="criteria section requires"):
        svc.start_attempt(sb, "user-1", "thin-pool-mock")
    assert sb.db.get("mock_attempts", []) == [], "no attempt row must be written on thin-pool failure"


def test_criteria_zero_eligible_pool_does_not_fall_through_to_legacy_config():
    """Regression: when all criteria-pool rows are stale PYQ and the eligible pool is
    completely empty, start_attempt() must raise LookupError rather than falling through
    to template.config.question_ids (the legacy config fallback).

    Without the early-return fix, select_questions_for_template() returns [] and
    start_attempt() silently starts an attempt from config.question_ids.  With the fix
    the criteria requirements are checked before the early return.
    """
    pyq_ids = [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
        "00000000-0000-0000-0000-000000000003",
    ]
    legacy_ids = ["legacy-q-1", "legacy-q-2", "legacy-q-3"]

    def _q_bank(qid: str) -> dict:
        opts = [{"id": f"opt-{qid}-{i}", "question_id": qid, "option_text": f"Opt {i}",
                 "option_index": i, "is_correct": i == 0}
                for i in range(4)]
        return {
            "id": qid,
            "exam_family": "TEST",
            "question_text": f"Q {qid[:8]}",
            "question_type": "mcq",
            "difficulty": "medium",
            "correct_option_id": f"opt-{qid}-0",
            "reviewer_status": "published",
            "pyq_question_id": f"pyq-src-{qid}",
            "options": opts,
        }

    template = {
        "id": "tmpl-zero-pool",
        "slug": "zero-pool-mock",
        "name": "Zero Pool Mock",
        "exam_family": "TEST",
        "total_questions": 3,
        "duration_sec": 300,
        "negative_marking": False,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.0,
        "config": {"question_ids": legacy_ids},  # legacy fallback must NOT be used
        "status": "active",
    }
    section = {
        "id": "sec-zero",
        "template_id": template["id"],
        "section_index": 0,
        "name": "Zero Pool Section",
        "question_count": 3,
        "selector": {"mode": "criteria", "filters": {}},
    }
    questions = [_q_bank(qid) for qid in pyq_ids]
    db = {
        "mock_templates": [template],
        "mock_template_sections": [section],
        "mock_question_bank": [dict(q) for q in questions],
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        # All projections are stale → zero active IDs → entire criteria pool excluded
        "pyq_mock_question_projections": [
            {"mock_question_id": qid, "sync_status": "stale"} for qid in pyq_ids
        ],
    }
    sb = SBStub(db)
    with pytest.raises(LookupError, match="criteria section requires"):
        svc.start_attempt(sb, "user-1", "zero-pool-mock")
    assert sb.db.get("mock_attempts", []) == [], "no attempt row must be written on zero-pool failure"


# ── Multi-section deduplication ───────────────────────────────────────────────

def test_multi_section_criteria_deduplicates_across_sections():
    """Two criteria sections drawing from the same pool must receive disjoint sets.

    Without the cross-section exclude_ids fix, both sections draw from the full
    pool and can return the same IDs, violating uq_mar_attempt_question.
    """
    questions = [_q("easy") for _ in range(3)] + [_q("medium") for _ in range(3)]
    template_id = "tmpl-multi-dedup"
    sections = [
        {
            "id": "sec-a",
            "template_id": template_id,
            "section_index": 0,
            "name": "Section A",
            "question_count": 3,
            "selector": {"mode": "criteria", "filters": {}},
        },
        {
            "id": "sec-b",
            "template_id": template_id,
            "section_index": 1,
            "name": "Section B",
            "question_count": 3,
            "selector": {"mode": "criteria", "filters": {}},
        },
    ]
    db = {
        "mock_template_sections": sections,
        "mock_question_bank": [dict(q) for q in questions],
        "mock_question_options": [o for q in questions for o in q["options"]],
    }
    sb = SBStub(db)
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    ids = [q["id"] for q in selected]
    assert len(ids) == 6, f"expected 6 questions, got {len(ids)}"
    assert len(set(ids)) == 6, "duplicate question IDs across sections must not occur"


def test_multi_section_pool_exhaustion_raises_lookup_error():
    """When two criteria sections exhaust the shared pool, the underfilled second
    section raises LookupError and no attempt row is written.

    Pool has 5 questions; section A wants 3, section B wants 3. After A takes 3,
    only 2 remain for B → underfill → LookupError.
    """
    questions = [_q("easy") for _ in range(5)]
    template = {
        "id": "tmpl-exhaust",
        "slug": "exhaust-mock",
        "name": "Exhaust Mock",
        "exam_family": "TEST",
        "total_questions": 6,
        "duration_sec": 300,
        "negative_marking": False,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.0,
        "config": {},
        "status": "active",
    }
    sections = [
        {
            "id": "sec-a",
            "template_id": template["id"],
            "section_index": 0,
            "name": "Section A",
            "question_count": 3,
            "selector": {"mode": "criteria", "filters": {}},
        },
        {
            "id": "sec-b",
            "template_id": template["id"],
            "section_index": 1,
            "name": "Section B",
            "question_count": 3,
            "selector": {"mode": "criteria", "filters": {}},
        },
    ]
    db = {
        "mock_templates": [template],
        "mock_template_sections": sections,
        "mock_question_bank": [dict(q) for q in questions],
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
    }
    sb = SBStub(db)
    with pytest.raises(LookupError, match="criteria section requires"):
        svc.start_attempt(sb, "user-1", "exhaust-mock")
    assert sb.db.get("mock_attempts", []) == [], "no attempt row must be written on pool exhaustion"


def test_fixed_then_criteria_excludes_fixed_ids():
    """A criteria section following a fixed section must not reuse fixed IDs.

    Fixed section claims 3 from a pool of 5; criteria section wants 3 but only 2
    remain after excluding the fixed IDs → underfill → LookupError, no attempt written.
    """
    fixed_qs = [_q("easy") for _ in range(3)]
    extra_qs = [_q("medium") for _ in range(2)]
    all_questions = fixed_qs + extra_qs

    template = {
        "id": "tmpl-fixed-criteria",
        "slug": "fixed-criteria-mock",
        "name": "Fixed+Criteria Mock",
        "exam_family": "TEST",
        "total_questions": 6,
        "duration_sec": 300,
        "negative_marking": False,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.0,
        "config": {},
        "status": "active",
    }
    sections = [
        {
            "id": "sec-fixed",
            "template_id": template["id"],
            "section_index": 0,
            "name": "Fixed Section",
            "question_count": 3,
            "selector": {"mode": "fixed", "question_ids": [q["id"] for q in fixed_qs]},
        },
        {
            "id": "sec-criteria",
            "template_id": template["id"],
            "section_index": 1,
            "name": "Criteria Section",
            "question_count": 3,
            "selector": {"mode": "criteria", "filters": {}},
        },
    ]
    db = {
        "mock_templates": [template],
        "mock_template_sections": sections,
        "mock_question_bank": [dict(q) for q in all_questions],
        "mock_question_options": [o for q in all_questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
    }
    sb = SBStub(db)
    with pytest.raises(LookupError, match="criteria section requires"):
        svc.start_attempt(sb, "user-1", "fixed-criteria-mock")
    assert sb.db.get("mock_attempts", []) == [], "no attempt row must be written on fixed+criteria underfill"


def test_start_attempt_uses_criteria_template():
    """End-to-end: a criteria-only template no longer needs the PR1 seed fallback."""
    questions = [_q("easy") for _ in range(5)]
    template = {
        "id": "tmpl-criteria-1",
        "slug": "criteria-mock",
        "name": "Criteria Mock",
        "exam_family": "TEST",
        "total_questions": 3,
        "duration_sec": 300,
        "negative_marking": True,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.25,
        "config": {},  # no legacy question_ids — must come from the selector
        "status": "active",
    }
    section = {
        "id": "sec-1",
        "template_id": template["id"],
        "section_index": 0,
        "name": "Section A",
        "question_count": 3,
        "selector": {"mode": "criteria", "filters": {}},
    }
    sb = SBStub({
        "mock_templates": [template],
        "mock_template_sections": [section],
        "mock_question_bank": [dict(q) for q in questions],
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
    })
    result = svc.start_attempt(sb, "user-1", "criteria-mock")
    assert len(result["questions"]) == 3
