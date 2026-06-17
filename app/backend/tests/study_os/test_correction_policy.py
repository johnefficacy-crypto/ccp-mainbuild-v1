"""Shared mock-correction policy (§7): unit behaviour + cross-origin parity.

The point of §7: equivalent normalized evidence must yield the SAME category and
title regardless of whether it came from a manually logged mock (mocks.py) or a
generated/platform attempt (mastery_engine / MasteryWriter). These tests pin the
policy itself and the parity of both adapters, plus an E2E that both origins
land the same category into study_tasks.metadata.

Stub-only; no live DB.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.study_os import correction_policy as cp
from app.study_os import mastery_writer as mw
from app.study_os import mocks
from app.study_os.mastery_engine.correction_tasks import derive_correction_tasks
from app.study_os.mastery_engine.error_patterns import derive_error_pattern_signals
from app.study_os.mastery_engine.schemas import (
    AttemptQuestionAnalytics,
    AttemptTopicAnalytics,
    DerivedAttemptAnalytics,
)
from app.study_os.mocks import VALID_CORRECTION_CATEGORIES
from tests.persona_questions._stub import SBStub

TOPIC = "t1"
USER = "u-1"
ATTEMPT = "11111111-1111-1111-1111-111111111111"


# ── policy unit ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("concept_gap", "concept_gap"), ("concept", "concept_gap"),
        ("memory_gap", "memory_gap"), ("memory", "memory_gap"), ("recall", "memory_gap"),
        ("careless", "careless"), ("calc_error", "careless"),
        ("speed_issue", "speed_issue"), ("time", "speed_issue"), ("timeout", "speed_issue"),
        ("option_trap", "option_trap"), ("option", "option_trap"), ("trap", "option_trap"),
        ("  Option  ", "option_trap"),  # case/space-insensitive
    ],
)
def test_alias_normalization(raw, expected):
    assert cp.normalize_error_type(raw) == expected
    assert expected in VALID_CORRECTION_CATEGORIES


@pytest.mark.parametrize("raw", ["", "gibberish", "unknown_error", None])
def test_unknown_alias_is_none_not_blind_default(raw):
    assert cp.normalize_error_type(raw) is None


def test_select_category_argmax_and_stable_tiebreak():
    # highest canonical count wins
    inp = cp.CorrectionPolicyInput(topic=TOPIC, error_counts={"option_trap": 3, "concept_gap": 1})
    assert cp.select_category(inp) == "option_trap"
    # equal counts → stable tie-break order (concept_gap precedes option_trap)
    tie = cp.CorrectionPolicyInput(topic=TOPIC, error_counts={"option_trap": 2, "concept_gap": 2})
    assert cp.select_category(tie) == "concept_gap"
    assert cp.select_category(tie) == "concept_gap"  # deterministic across calls


def test_select_category_unknown_only_is_none():
    inp = cp.CorrectionPolicyInput(topic=TOPIC, error_counts={"gibberish": 9})
    assert cp.select_category(inp) is None  # never a blind concept_gap


def test_select_category_explicit_fallbacks():
    assert cp.select_category(cp.CorrectionPolicyInput(topic=TOPIC, weak_topic=True)) == "concept_gap"
    assert cp.select_category(
        cp.CorrectionPolicyInput(topic=TOPIC, attempted=3, accuracy_pct=Decimal("10"))
    ) == "concept_gap"
    assert cp.select_category(cp.CorrectionPolicyInput(topic=TOPIC, prior_error=True)) == "concept_gap"
    # no signal at all → no category
    assert cp.select_category(cp.CorrectionPolicyInput(topic=TOPIC, accuracy_pct=Decimal("100"))) is None


def test_titles():
    assert cp.correction_title("concept_gap", "t1") == "Concept drill · t1"
    assert cp.correction_title("option_trap", None) == "Distractor elimination drill"


def test_should_emit_modes():
    # summary (manual): any usable signal or weak-topic
    assert cp.should_emit(cp.CorrectionPolicyInput(topic=TOPIC, error_counts={"concept": 1}, evidence_mode="summary"))
    assert cp.should_emit(cp.CorrectionPolicyInput(topic=TOPIC, weak_topic=True, evidence_mode="summary"))
    assert not cp.should_emit(cp.CorrectionPolicyInput(topic=TOPIC, evidence_mode="summary"))
    # question_level (generated): thresholds
    assert cp.should_emit(cp.CorrectionPolicyInput(topic=TOPIC, attempted=3, accuracy_pct=Decimal("10")))
    assert cp.should_emit(cp.CorrectionPolicyInput(topic=TOPIC, error_counts={"concept_gap": 2}))
    assert not cp.should_emit(cp.CorrectionPolicyInput(topic=TOPIC, attempted=2, accuracy_pct=Decimal("10")))


# ── CROSS-ORIGIN PARITY: same normalized evidence → same category + title ─────

# (manual error_patterns key, equivalent canonical, expected category)
_PARITY = [
    ("concept", "concept_gap", "concept_gap"),
    ("option", "option_trap", "option_trap"),
    ("careless", "careless", "careless"),
    ("time", "speed_issue", "speed_issue"),
    ("memory", "memory_gap", "memory_gap"),
]


@pytest.mark.parametrize("manual_key,canonical,expected", _PARITY)
def test_cross_origin_parity_category_and_title(manual_key, canonical, expected):
    # Manual adapter (mocks) on the raw key …
    manual = mocks._draft_corrections_from_mock(
        {"error_patterns": {manual_key: 2}, "weak_topics": [TOPIC]}
    )
    assert len(manual) == 1
    m = manual[0]

    # … vs the generated adapter's classifier (correction_policy) on equivalent
    # normalized evidence for the same topic.
    g_input = cp.CorrectionPolicyInput(topic=TOPIC, error_counts={canonical: 2})
    g_cat = cp.select_category(g_input)
    g_title = cp.correction_title(g_cat, TOPIC)

    assert m["category"] == g_cat == expected
    assert m["title"] == g_title
    assert m["topic"] == TOPIC


def test_cross_origin_parity_low_accuracy_weak_topic_fallback():
    manual = mocks._draft_corrections_from_mock({"error_patterns": {}, "weak_topics": [TOPIC]})
    assert manual and manual[0]["category"] == "concept_gap"
    gen = cp.select_category(
        cp.CorrectionPolicyInput(topic=TOPIC, attempted=3, accuracy_pct=Decimal("0"))
    )
    assert gen == "concept_gap"
    assert manual[0]["title"] == cp.correction_title("concept_gap", TOPIC)


# ── generated PIPELINE really sets draft.category from evidence ───────────────

def _analytics(error_type: str, n: int) -> DerivedAttemptAnalytics:
    qs = [
        AttemptQuestionAnalytics(
            question_id=f"q{i}", topic_id=TOPIC, is_correct=False,
            difficulty="medium", source_type="authored", error_type=error_type,
        )
        for i in range(n)
    ]
    topics = [AttemptTopicAnalytics(topic_id=TOPIC, attempted=n, correct=0, accuracy_pct=Decimal("0"))]
    return DerivedAttemptAnalytics(attempt_id=ATTEMPT, user_id=USER, questions=qs, topics=topics)


@pytest.mark.parametrize(
    "error_type,n,expected",
    [("concept_gap", 2, "concept_gap"), ("option_trap", 2, "option_trap"), ("calc_error", 3, "careless")],
)
def test_generated_pipeline_sets_category(error_type, n, expected):
    analytics = _analytics(error_type, n)
    drafts = derive_correction_tasks(analytics, derive_error_pattern_signals(analytics), set())
    cats = {d.category for d in drafts if d.topic_id == TOPIC}
    assert expected in cats
    assert cats <= VALID_CORRECTION_CATEGORIES


# ── E2E: both origins land the SAME category into study_tasks.metadata ────────

def _apply_and_get_category(sb: SBStub, correction_id: str) -> str:
    applied = mocks.apply_correction_task(sb, USER, correction_id)
    task = sb.db["study_tasks"][-1]
    assert task["metadata"]["category"] == applied["category"]
    return task["metadata"]["category"]


def test_e2e_generated_and_manual_apply_same_category(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")

    # ── generated origin: submit-time write-back drafts a correction ──
    sb_gen = SBStub()
    sb_gen.db.update({
        "mock_attempts": [{"id": ATTEMPT, "user_id": USER}],
        "mock_attempt_responses": [
            {"attempt_id": ATTEMPT, "question_id": f"q{i}", "is_correct": False,
             "time_spent_sec": 5, "error_type": "concept_gap",
             "question_snapshot": {"topic_id": TOPIC, "difficulty": "medium", "source_type": "authored"}}
            for i in range(3)
        ],
        "mock_tests": [{"id": "mt-gen", "mock_attempt_id": ATTEMPT, "trust_level": "platform_verified"}],
        "mock_correction_tasks": [], "user_topic_mastery": [], "user_topic_mastery_audit": [],
        "user_topic_error_patterns": [], "mock_mastery_shadow": [], "study_plans": [], "study_tasks": [],
    })
    asyncio.run(mw.MasteryWriter(sb_gen, "live").process_attempt(ATTEMPT))
    gen_correction = sb_gen.db["mock_correction_tasks"][0]
    gen_category = _apply_and_get_category(sb_gen, gen_correction["id"])

    # ── manual origin: equivalent evidence (concept) on the same topic ──
    sb_man = SBStub()
    sb_man.db.update({
        "mock_tests": [{
            "id": "mt-man", "user_id": USER, "review_state": "reviewed",
            "error_patterns": {"concept_gap": 3}, "weak_topics": [TOPIC],
        }],
        "mock_correction_tasks": [], "study_plans": [], "study_tasks": [],
    })
    manual_drafts = mocks.draft_correction_tasks(sb_man, USER, "mt-man")
    man_correction = next(c for c in manual_drafts if c["category"] == "concept_gap")
    man_category = _apply_and_get_category(sb_man, man_correction["id"])

    # the whole point of §7: same evidence → same category, whatever the origin.
    assert gen_category == man_category == "concept_gap"
