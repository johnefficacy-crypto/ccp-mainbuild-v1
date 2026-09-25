"""REG-CORPUS-02 P2 — authored, multi-exam rows in the learner pools.

An authored bank row keeps ``exam_id`` NULL and reaches an exam's learners only
when its primary topic's ``metadata.exams`` carries that exam's key
(``authored_scope.EXAM_TOPIC_KEYS``). Covers the resolver, topic practice
(select / practiceable / start), and the blueprint + diagnostics pools, and pins
that a non-regulatory exam's PYQ pool is unchanged by authored rows existing.
"""
from __future__ import annotations

import copy

from app.exam_intelligence import authored_scope as scope
from app.exam_intelligence.diagnostics import authored_pool_rows, selectable_mcq_depth
from app.study_os import mock_engine as engine
from app.study_os import pyq_practice as svc
from app.study_os.mock_blueprint_selection import _exam_base_pool
from tests.persona_questions._stub import SBStub

SEBI = "5eb10000-0000-0000-0000-000000000001"
IFSCA = "1f5ca000-0000-0000-0000-000000000001"
UPSC = "09500000-0000-0000-0000-000000000001"
UNKNOWN = "0ff00000-0000-0000-0000-000000000001"

# Costing microtopic: tagged for all three regulators.
T_COST = "c0510000-0000-0000-0000-000000000001"
# Companies Act microtopic: SEBI + PFRDA only (not IFSCA).
T_CA = "ca000000-0000-0000-0000-000000000001"
# A UPSC topic with no regulatory tag.
T_UPSC = "09500000-0000-0000-0000-00000000000f"
SUBJ_COST = "c0510000-0000-0000-0000-0000000000aa"
SUBJ_CA = "ca000000-0000-0000-0000-0000000000aa"


def _opts(qid: str) -> list[dict]:
    return [
        {"id": f"opt-{qid}-{i}", "question_id": qid, "option_text": f"Option {i}",
         "option_index": i, "is_correct": i == 1, "display_order": i}
        for i in range(4)
    ]


def _authored(qid: str, topic: str, subject: str, *, status: str = "verified",
              group: str | None = None, **over) -> dict:
    row = {
        "id": qid, "question_text": f"Authored {qid}", "question_type": "mcq",
        "reviewer_status": status, "correct_option_id": f"opt-{qid}-1",
        "exam_id": None, "subject_id": subject, "topic_id": topic, "microtopic_id": None,
        "pyq_question_id": None, "pyq_paper_id": None, "pyq_year": None,
        "source_kind": "authored", "source_type": None, "difficulty": "hard",
        "is_current": False, "is_current_based": False, "valid_until": None,
        "metadata": {"rubric_level": "L3", **({"stimulus_group": group} if group else {})},
    }
    row.update(over)
    return row


def _pyq(qid: str, exam: str, topic: str, year: int = 2024) -> dict:
    return {
        "id": qid, "question_text": f"PYQ {qid}", "question_type": "mcq",
        "reviewer_status": "verified", "correct_option_id": f"opt-{qid}-1",
        "exam_id": exam, "subject_id": "sub-upsc", "topic_id": topic, "microtopic_id": None,
        "pyq_question_id": f"pyqq-{qid}", "pyq_paper_id": "paper-1", "pyq_year": year,
        "section_id": None, "source_kind": "pyq", "source_type": "pyq", "difficulty": "medium",
        "is_current": False, "is_current_based": False, "valid_until": None,
    }


def _db(bank: list[dict], *, stimuli: list[dict] | None = None) -> SBStub:
    return SBStub({
        "exams": [
            {"id": SEBI, "slug": "sebi-grade-a"},
            {"id": IFSCA, "slug": "ifsca-grade-a"},
            {"id": UPSC, "slug": "upsc-cse"},
            {"id": UNKNOWN, "slug": "some-new-exam"},
        ],
        "topics": [
            {"id": T_COST, "subject_id": SUBJ_COST, "metadata": {"exams": ["ifsca", "pfrda", "sebi"]}},
            {"id": T_CA, "subject_id": SUBJ_CA, "metadata": {"exams": ["pfrda", "sebi"]}},
            {"id": T_UPSC, "subject_id": "sub-upsc", "metadata": {}},
        ],
        "mock_question_bank": bank,
        "mock_question_options": [o for q in bank for o in _opts(q["id"])],
        "mock_question_stimuli": stimuli or [],
        "pyq_mock_question_projections": [
            {"mock_question_id": q["id"], "sync_status": "active"}
            for q in bank if q.get("pyq_question_id")
        ],
        "pyq_questions": [],
        "exam_phase_sections": [],
        "mock_generated_blueprints": [],
        "mock_attempts": [],
        "mock_attempt_responses": [],
    })


def _corpus() -> list[dict]:
    return [
        _authored("a-cost", T_COST, SUBJ_COST),
        _authored("a-ca", T_CA, SUBJ_CA),
        # Not learner-visible, expired, or not authored-shaped: never served.
        _authored("a-cost-draft", T_COST, SUBJ_COST, status="draft"),
        _authored("a-cost-expired", T_COST, SUBJ_COST, valid_until="2001-01-01T00:00:00+00:00"),
        _authored("a-cost-scoped", T_COST, SUBJ_COST, exam_id=UPSC),
        _authored("a-cost-int", T_COST, SUBJ_COST, question_type="integer"),
    ]


# ── resolver ─────────────────────────────────────────────────────────────────

def test_resolver_maps_the_three_regulatory_slugs():
    assert scope.topic_key_for_exam_slug("sebi-grade-a") == "sebi"
    assert scope.topic_key_for_exam_slug("pfrda-grade-a") == "pfrda"
    assert scope.topic_key_for_exam_slug("IFSCA-Grade-A ") == "ifsca"


def test_resolver_unknown_slug_gets_no_key():
    for slug in ("upsc-cse", "rbi-grade-b", "sebi", "", None):
        assert scope.topic_key_for_exam_slug(slug) is None


def test_resolve_exam_topic_key_reads_the_exam_slug():
    sb = _db([])
    assert scope.resolve_exam_topic_key(sb, SEBI) == "sebi"
    assert scope.resolve_exam_topic_key(sb, UPSC) is None
    assert scope.resolve_exam_topic_key(sb, "missing") is None
    assert scope.resolve_exam_topic_key(sb, None) is None


def test_resolve_exam_topic_key_fails_closed_on_read_error():
    class Boom:
        def table(self, _name):
            raise RuntimeError("down")
    assert scope.resolve_exam_topic_key(Boom(), SEBI) is None


def test_unknown_exam_gets_no_authored_rows_not_all():
    sb = _db(_corpus())
    calls = []
    assert scope.authored_rows_for_exam(sb, UNKNOWN, lambda: calls.append(1) or _corpus()) == []
    assert calls == []  # the pool read is not even issued


def test_topic_carries_key_requires_a_list():
    assert scope.topic_carries_key({"exams": ["sebi"]}, "sebi")
    assert not scope.topic_carries_key({"exams": "sebi"}, "sebi")
    assert not scope.topic_carries_key(None, "sebi")


# ── topic practice ───────────────────────────────────────────────────────────

def test_sebi_learner_sees_authored_costing_row():
    sb = _db(_corpus())
    rows = svc.select_practice_rows(sb, mode="topic", exam_id=SEBI, target_id=T_COST, limit=50)
    assert [r["id"] for r in rows] == ["a-cost"]


def test_ifsca_learner_does_not_see_authored_companies_act_row():
    sb = _db(_corpus())
    assert svc.select_practice_rows(sb, mode="topic", exam_id=IFSCA, target_id=T_CA, limit=50) == []
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=T_CA, exam_id=IFSCA)
    assert res["outcome"] == "empty_pool"
    # ...while the IFSCA learner still gets the costing row (topic tagged ifsca).
    rows = svc.select_practice_rows(sb, mode="topic", exam_id=IFSCA, target_id=T_COST, limit=50)
    assert [r["id"] for r in rows] == ["a-cost"]


def test_upsc_topic_pool_unchanged_by_authored_rows():
    pyq_rows = [_pyq("p1", UPSC, T_UPSC, 2019), _pyq("p2", UPSC, T_UPSC, 2023)]
    # An authored row on the SAME topic id, even one whose topic metadata were to
    # name every exam, must not reach a UPSC learner: UPSC has no key.
    stray = _authored("a-upsc-topic", T_UPSC, "sub-upsc")
    base = svc.select_practice_rows(_db(copy.deepcopy(pyq_rows)), mode="topic",
                                    exam_id=UPSC, target_id=T_UPSC, limit=50)
    with_authored = svc.select_practice_rows(_db(copy.deepcopy(pyq_rows) + [stray] + _corpus()),
                                             mode="topic", exam_id=UPSC, target_id=T_UPSC, limit=50)
    assert [r["id"] for r in base] == ["p2", "p1"]
    assert with_authored == base
    assert svc.practiceable_topic_ids(_db(pyq_rows + [stray]), exam_id=UPSC, topic_ids=[T_UPSC]) == \
        svc.practiceable_topic_ids(_db(pyq_rows), exam_id=UPSC, topic_ids=[T_UPSC]) == {T_UPSC}


def test_paper_mode_never_includes_authored_rows():
    sb = _db(_corpus() + [_pyq("p1", SEBI, T_COST)])
    rows = svc.select_practice_rows(sb, mode="paper", exam_id=SEBI, target_id="paper-1", limit=50)
    assert [r["id"] for r in rows] == ["p1"]


def test_topic_pool_orders_pyq_first_and_keeps_case_sets_contiguous():
    bank = [
        _pyq("p1", SEBI, T_COST, 2022),
        _authored("a-z", T_COST, SUBJ_COST),
        _authored("a-case-2", T_COST, SUBJ_COST, group="CST-CASE-PROC"),
        _authored("a-b", T_COST, SUBJ_COST),
        _authored("a-case-1", T_COST, SUBJ_COST, group="CST-CASE-PROC"),
    ]
    rows = svc.select_practice_rows(_db(bank), mode="topic", exam_id=SEBI, target_id=T_COST, limit=50)
    ids = [r["id"] for r in rows]
    assert ids[0] == "p1"
    assert ids.index("a-case-2") == ids.index("a-case-1") + 1


def test_practiceable_topic_ids_advertises_authored_topic_per_exam():
    sb = _db(_corpus())
    assert svc.practiceable_topic_ids(sb, exam_id=SEBI, topic_ids=[T_COST, T_CA]) == {T_COST, T_CA}
    assert svc.practiceable_topic_ids(sb, exam_id=IFSCA, topic_ids=[T_COST, T_CA]) == {T_COST}
    assert svc.practiceable_topic_ids(sb, exam_id=UPSC, topic_ids=[T_COST, T_CA]) == set()


def test_sebi_topic_practice_starts_and_freezes_the_case_stimulus():
    bank = [_authored("a-case-1", T_COST, SUBJ_COST, group="CST-CASE-PROC")]
    stimuli = [{"id": "s1", "mock_question_id": "a-case-1", "pyq_stimulus_id": None,
                "stimulus_type": "table", "content_text": "| Item | Units |\n|---|---:|\n| A | 1 |",
                "language": "en", "display_order": 1}]
    sb = _db(bank, stimuli=stimuli)
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=T_COST, exam_id=SEBI)
    assert res["outcome"] == "ready" and res["question_count"] == 1
    assert res["exam_id"] == SEBI
    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    q = state["questions"][0]
    assert q["stimuli"][0]["stimulus_type"] == "table"
    assert "| Item | Units |" in q["stimuli"][0]["content_text"]


# ── blueprint + diagnostics (selection ≡ readiness) ───────────────────────────

def test_blueprint_and_depth_include_authored_rows_for_keyed_exam_only():
    statuses = ["verified", "published", "live"]
    now = "2026-09-25T00:00:00+00:00"
    sb = _db(_corpus())
    sebi_pool = {r["id"] for r in _exam_base_pool(sb, exam_id=SEBI, selectable_statuses=statuses, now_iso=now)}
    ifsca_pool = {r["id"] for r in _exam_base_pool(sb, exam_id=IFSCA, selectable_statuses=statuses, now_iso=now)}
    upsc_pool = {r["id"] for r in _exam_base_pool(sb, exam_id=UPSC, selectable_statuses=statuses, now_iso=now)}
    assert sebi_pool == {"a-cost", "a-ca"}
    assert ifsca_pool == {"a-cost"}
    # UPSC gets only its own exam-scoped row, exactly as before this change.
    assert upsc_pool == {"a-cost-scoped"}

    depth = selectable_mcq_depth(sb, SEBI, selectable_statuses=statuses)
    assert depth["base_total"] == len(sebi_pool)


def test_authored_pool_rows_empty_for_unkeyed_exam():
    assert authored_pool_rows(_db(_corpus()), exam_id=UPSC, statuses=["verified"]) == []
