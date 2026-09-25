"""REG-CORPUS-05 — live exam slugs and explicit shared-subject eligibility.

Operator check of live data (2026-09-26): only SSC CGL and RBI Grade B carry
exam_phase_sections for the shared subjects, and no exam has general-knowledge.
EXAM_AGNOSTIC_SUBJECTS grants the QRE + GK subjects to every tiered exam for
TOPIC PRACTICE ONLY; generated mocks keep reading phase sections.
"""
from __future__ import annotations

import logging

from app.exam_intelligence import authored_scope as scope
from app.exam_intelligence.diagnostics import authored_pool_rows
from app.study_os import pyq_practice as svc
from tests.persona_questions._stub import SBStub

SSC = "55c00000-0000-0000-0000-000000000001"
SEBI = "5eb10000-0000-0000-0000-000000000001"
IFSCA = "1f5ca000-0000-0000-0000-000000000001"
UPSC = "09500000-0000-0000-0000-000000000001"
SANDBOX = "5a4d0000-0000-0000-0000-000000000001"

S_QA = "0a000000-0000-0000-0000-0000000000aa"
S_GK = "0c000000-0000-0000-0000-0000000000aa"
S_CA = "ca000000-0000-0000-0000-0000000000aa"

T_QA = "0a000000-0000-0000-0000-000000000001"  # no exams key
T_GK = "0c000000-0000-0000-0000-000000000001"  # no exams key
T_CA = "ca000000-0000-0000-0000-000000000001"  # Companies Act, keyed [sebi, pfrda]

REMOVED_SLUGS = ("ssc-cgl", "ssc-chsl", "ssc-mts", "ssc-cpo", "ssc-gd", "ibps-clerk", "sbi-clerk",
                 "ibps-rrb-clerk", "rrb-group-d", "ibps-rrb-po", "nabard-grade-a", "nabard-grade-b")


def _opts(qid: str) -> list[dict]:
    return [{"id": f"opt-{qid}-{i}", "question_id": qid, "option_text": f"Option {i}",
             "option_index": i, "is_correct": i == 1, "display_order": i} for i in range(4)]


def _authored(qid: str, topic: str, subject: str, tier: str | None = None) -> dict:
    meta = {"rubric_level": "L2", **({"exam_tier": tier} if tier else {})}
    return {
        "id": qid, "question_text": f"Authored {qid}", "question_type": "mcq",
        "reviewer_status": "verified", "correct_option_id": f"opt-{qid}-1",
        "exam_id": None, "subject_id": subject, "topic_id": topic, "microtopic_id": None,
        "pyq_question_id": None, "pyq_paper_id": None, "pyq_year": None,
        "source_kind": "authored", "source_type": None, "difficulty": "medium",
        "is_current": False, "is_current_based": False, "valid_until": None, "metadata": meta,
    }


def _bank() -> list[dict]:
    return [
        _authored("qa-f", T_QA, S_QA, "foundation"), _authored("qa-o", T_QA, S_QA, "officer"),
        _authored("gk-f", T_GK, S_GK, "foundation"), _authored("gk-o", T_GK, S_GK, "officer"),
        _authored("ca", T_CA, S_CA),
    ]


def _db(*, ssc_has_qa_section: bool = True) -> SBStub:
    bank = _bank()
    sections = [{"id": "sec-ssc-qa", "exam_phase_id": "ph-ssc", "subject_id": S_QA}] if ssc_has_qa_section else []
    sections.append({"id": "sec-sandbox-qa", "exam_phase_id": "ph-sandbox", "subject_id": S_QA})
    return SBStub({
        "exams": [
            {"id": SSC, "slug": "national-ssc-combined-graduate-level-cgl"},
            {"id": SEBI, "slug": "sebi-grade-a"}, {"id": IFSCA, "slug": "ifsca-grade-a"},
            {"id": UPSC, "slug": "upsc-cse"}, {"id": SANDBOX, "slug": "ssc-cgl-legacy-sandbox-do-not-use"},
        ],
        # SEBI / IFSCA / UPSC have no shared-subject sections, as live.
        "exam_phases": [{"id": "ph-ssc", "exam_id": SSC}, {"id": "ph-sandbox", "exam_id": SANDBOX}],
        "exam_phase_sections": sections,
        "subjects": [
            {"id": S_QA, "slug": "quantitative-aptitude"}, {"id": S_GK, "slug": "general-knowledge"},
            {"id": S_CA, "slug": "companies-act"},
        ],
        "topics": [
            {"id": T_QA, "subject_id": S_QA, "metadata": {}},
            {"id": T_GK, "subject_id": S_GK, "metadata": {}},
            {"id": T_CA, "subject_id": S_CA, "metadata": {"exams": ["sebi", "pfrda"]}},
        ],
        "mock_question_bank": bank,
        "mock_question_options": [o for r in bank for o in _opts(r["id"])],
        "mock_question_stimuli": [],
    })


def _ids(exam: str, topic: str, sb: SBStub | None = None, **kw) -> set[str]:
    rows = svc.select_practice_rows(sb or _db(), mode="topic", exam_id=exam, target_id=topic, limit=50, **kw)
    return {r["id"] for r in rows}


# ── P1 live exam slugs ────────────────────────────────────────────────────────

def test_ssc_cgl_live_slug_is_foundation_and_nabard_live_slug_is_officer():
    assert scope.exam_tier_for_slug("national-ssc-combined-graduate-level-cgl") == "foundation"
    assert scope.exam_tier_for_slug("national-nabard-grade-a") == "officer"


def test_exam_tiers_is_exactly_the_live_slug_map():
    foundation = {
        "national-ssc-combined-graduate-level-cgl", "national-ssc-combined-higher-secondary-level-chsl",
        "national-ssc-multi-tasking-staff-mts-havaldar", "national-ssc-cpo-delhi-police-capf-sub-inspector",
        "national-ssc-gd-constable", "national-ibps-clerk", "national-sbi-clerk-junior-associate",
        "national-ibps-rrb-office-assistant", "national-rrb-group-d-level-1", "national-rbi-assistant", "rrb-ntpc",
    }
    officer = {
        "ibps-po", "sbi-po", "national-ibps-rrb-officer-scale-i-ii-iii", "rbi-grade-b", "sebi-grade-a",
        "ifsca-grade-a", "pfrda-grade-a", "national-nabard-grade-a", "national-lic-aao-ado",
    }
    assert scope.EXAM_TIERS == {**{s: "foundation" for s in foundation}, **{s: "officer" for s in officer}}


def test_slugs_that_do_not_exist_live_are_gone():
    for slug in REMOVED_SLUGS:
        assert slug not in scope.EXAM_TIERS and slug not in scope.EXAM_AGNOSTIC_SUBJECTS, slug


# ── P2 explicit shared-subject eligibility (topic practice only) ──────────────

def test_sebi_learner_sees_an_authored_qa_row_and_a_gk_row():
    assert _ids(SEBI, T_QA) == {"qa-o"}
    assert _ids(SEBI, T_GK) == {"gk-o"}


def test_ifsca_learner_sees_gk():
    assert _ids(IFSCA, T_GK) == {"gk-o"}


def test_ssc_cgl_sees_foundation_qa_only():
    assert _ids(SSC, T_QA) == {"qa-f"}
    # and the same without its QA section: the config alone grants it
    assert _ids(SSC, T_QA, _db(ssc_has_qa_section=False)) == {"qa-f"}


def test_upsc_sees_no_authored_qre_or_gk_row():
    assert _ids(UPSC, T_QA, include_other_tier=True) == set()
    assert _ids(UPSC, T_GK, include_other_tier=True) == set()


def test_keyed_regulatory_rows_unchanged():
    assert _ids(IFSCA, T_CA, include_other_tier=True) == set()  # Companies Act names sebi, pfrda
    assert _ids(SEBI, T_CA) == {"ca"}


def test_readiness_advertises_configured_subjects_like_launch():
    assert svc.practiceable_topic_ids(_db(), exam_id=SEBI, topic_ids=[T_QA, T_GK, T_CA]) == {T_QA, T_GK, T_CA}
    assert svc.practiceable_topic_ids(_db(), exam_id=UPSC, topic_ids=[T_QA, T_GK]) == set()


def test_generated_mock_pool_keeps_phase_sections_only():
    # SEBI has no QA/GK section: its mock pool gets no QRE/GK rows despite the config.
    assert {r["id"] for r in authored_pool_rows(_db(), exam_id=SEBI, statuses=["verified"])} == {"ca"}
    # SSC's QA section still feeds its mock (tier-strict); GK has no section, so none.
    assert {r["id"] for r in authored_pool_rows(_db(), exam_id=SSC, statuses=["verified"])} == {"qa-f"}
    assert authored_pool_rows(_db(ssc_has_qa_section=False), exam_id=SSC, statuses=["verified"]) == []


def test_sandbox_exam_never_gets_configured_subjects(monkeypatch):
    slug = "ssc-cgl-legacy-sandbox-do-not-use"
    assert scope.configured_agnostic_subjects(slug) == frozenset()
    monkeypatch.setitem(scope.EXAM_AGNOSTIC_SUBJECTS, slug, scope.QRE_GK_SUBJECTS)
    assert scope.configured_agnostic_subjects(slug) == frozenset()
    assert not any("sandbox" in s for s in list(scope.EXAM_AGNOSTIC_SUBJECTS) if s != slug)


def test_config_names_only_the_shared_subjects_and_never_upsc():
    assert "upsc-cse" not in scope.EXAM_AGNOSTIC_SUBJECTS
    for slug, subjects in scope.EXAM_AGNOSTIC_SUBJECTS.items():
        assert subjects == scope.QRE_GK_SUBJECTS, slug
    assert scope.QRE_GK_SUBJECTS <= scope.BODY_AGNOSTIC_SUBJECTS


def test_failed_configured_subject_read_fails_closed():
    sb = _db(ssc_has_qa_section=False)
    real = sb.table

    def table(name):
        if name == "subjects":
            raise RuntimeError("boom")
        return real(name)

    sb.table = table  # type: ignore[method-assign]
    assert scope.configured_subject_ids(sb, "sebi-grade-a") == frozenset()
    assert _ids(SEBI, T_QA, sb) == set()
    assert _ids(SEBI, T_CA, sb) == {"ca"}  # keyed path unaffected


# ── P3 drift guard ────────────────────────────────────────────────────────────

def test_exam_tiers_and_agnostic_subjects_have_the_same_exams():
    assert set(scope.EXAM_TIERS) == set(scope.EXAM_AGNOSTIC_SUBJECTS)
    assert scope.agnostic_config_drift() == {"agnostic_without_tier": [], "tier_without_agnostic": []}


def test_startup_check_warns_for_agnostic_eligibility_without_a_tier(monkeypatch, caplog):
    monkeypatch.setitem(scope.EXAM_AGNOSTIC_SUBJECTS, "national-new-exam", scope.QRE_GK_SUBJECTS)
    with caplog.at_level(logging.WARNING, logger=scope.logger.name):
        assert scope.log_agnostic_config_drift() == ["national-new-exam"]
    assert "national-new-exam has body-agnostic eligibility but no EXAM_TIERS entry" in caplog.text


def test_runtime_warns_once_for_a_section_eligible_exam_without_a_tier(monkeypatch, caplog):
    monkeypatch.setattr(scope, "_WARNED_UNTIERED", set())
    with caplog.at_level(logging.WARNING, logger=scope.logger.name):
        s1 = scope.resolve_exam_scope(_db(), SANDBOX, include_configured_subjects=True)
        scope.resolve_exam_scope(_db(), SANDBOX)
    assert s1.agnostic_subject_ids == frozenset({S_QA}) and s1.tier is None  # its section only
    assert caplog.text.count("serves body-agnostic rows but has no tier") == 1


def test_server_lifespan_runs_the_drift_check():
    import inspect

    import server

    assert "log_agnostic_config_drift()" in inspect.getsource(server.lifespan)
