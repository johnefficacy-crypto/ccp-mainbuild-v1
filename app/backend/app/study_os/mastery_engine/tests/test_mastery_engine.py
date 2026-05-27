from __future__ import annotations

import json
import random
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.study_os.mastery_engine.schemas import AttemptQuestionAnalytics, AttemptTopicAnalytics, DerivedAttemptAnalytics
from app.study_os.mastery_engine.service import derive_from_analytics

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "reference_input.json"


def _build(inp: dict) -> DerivedAttemptAnalytics:
    return DerivedAttemptAnalytics.model_validate(inp)


def test_empty_input_returns_empty():
    a = DerivedAttemptAnalytics(attempt_id=uuid4(), user_id="u", questions=[], topics=[])
    r = derive_from_analytics(a)
    assert r.mastery_deltas == []
    assert r.correction_task_drafts == []


def test_whiplash_bounds():
    easy = DerivedAttemptAnalytics(
        attempt_id=uuid4(),
        user_id="u",
        topics=[AttemptTopicAnalytics(topic_id="t", attempted=1, correct=1, accuracy_pct=Decimal("100"))],
        questions=[AttemptQuestionAnalytics(question_id="q", topic_id="t", is_correct=True, difficulty="easy")],
    )
    hard = DerivedAttemptAnalytics(
        attempt_id=uuid4(),
        user_id="u",
        topics=[AttemptTopicAnalytics(topic_id="t", attempted=5, correct=5, accuracy_pct=Decimal("100"))],
        questions=[AttemptQuestionAnalytics(question_id=f"q{i}", topic_id="t", is_correct=True, difficulty="hard") for i in range(5)],
    )
    assert derive_from_analytics(easy).mastery_deltas[0].capped_delta <= Decimal("0.05")
    assert derive_from_analytics(hard).mastery_deltas[0].capped_delta >= Decimal("0.14")


def test_concept_review_priority_1():
    inp = json.loads(FIX.read_text())
    out = derive_from_analytics(_build(inp))
    assert len(out.correction_task_drafts) == 1
    d = out.correction_task_drafts[0]
    assert d.task_type == "concept_review"
    assert d.priority == 1


def test_pyq_weight_ratio():
    authored = DerivedAttemptAnalytics(
        attempt_id=uuid4(), user_id="u", topics=[AttemptTopicAnalytics(topic_id="t", attempted=1, correct=1, accuracy_pct=Decimal("100"))],
        questions=[AttemptQuestionAnalytics(question_id="a", topic_id="t", is_correct=True, difficulty="medium", source_type="authored")],
    )
    pyq = DerivedAttemptAnalytics(
        attempt_id=uuid4(), user_id="u", topics=[AttemptTopicAnalytics(topic_id="t", attempted=1, correct=1, accuracy_pct=Decimal("100"))],
        questions=[AttemptQuestionAnalytics(question_id="p", topic_id="t", is_correct=True, difficulty="medium", source_type="pyq", pyq_year=2026)],
    )
    da = derive_from_analytics(authored).mastery_deltas[0].raw_delta
    dp = derive_from_analytics(pyq).mastery_deltas[0].raw_delta
    ratio = (dp / da).quantize(Decimal("0.1"))
    assert ratio == Decimal("1.2")


def test_determinism_random_fixtures():
    rng = random.Random(7)
    for _ in range(100):
        qs = []
        correct = 0
        for i in range(10):
            ok = bool(rng.randint(0, 1))
            correct += 1 if ok else 0
            qs.append(AttemptQuestionAnalytics(question_id=f"q{i}", topic_id="t", is_correct=ok, difficulty=rng.choice(["easy", "medium", "hard"]), source_type=rng.choice(["authored", "pyq"]), pyq_year=2020 + rng.randint(0, 6), error_type=rng.choice([None, "concept_gap", "option_trap", "calc_error"]), confidence=Decimal("0.6")))
        a = DerivedAttemptAnalytics(attempt_id=uuid4(), user_id="u", topics=[AttemptTopicAnalytics(topic_id="t", attempted=10, correct=correct, accuracy_pct=Decimal(correct * 10))], questions=qs)
        import json
        r1 = json.dumps(derive_from_analytics(a).model_dump(mode="json"), sort_keys=True)
        r2 = json.dumps(derive_from_analytics(a).model_dump(mode="json"), sort_keys=True)
        assert r1 == r2
