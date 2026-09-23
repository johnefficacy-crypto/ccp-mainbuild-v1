"""Answer structures — schema, generator and the learner side.

The contract these pin:

* a model reply that is not valid structure JSON is never accepted, and is
  retried with the validator's errors fed back;
* the cost cap refuses a call that COULD cross it, retries included;
* the structure is hidden until the attempt is submitted — by the server, not
  only the browser — and only a verified structure of a verified question is
  ever returned;
* coverage ticks persist on the attempt against a named version, typed or
  handwritten alike, and roll up into My answers and Progress.

The RLS policies and the one-verified index are proven against real Postgres
in test_answer_structures_migration_behaviour.py.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.study_os import answer_structure_generation as gen
from app.study_os import answer_structures as svc
from app.study_os import descriptive as d
from app.study_os.answer_structure_schema import (
    StructureSchemaError,
    coverage_pct,
    learner_payload,
    lint_structure,
    validate_structure,
    word_budget_for,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "answer_structures"
RESPONSES = json.loads((FIXTURES / "responses.json").read_text(encoding="utf-8"))
QUESTIONS = [
    gen.QuestionInput.from_dict(json.loads(line))
    for line in (FIXTURES / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
GOOD = RESPONSES[QUESTIONS[0].id]

USER = "user-me"
OTHER = "user-else"
Q = "q-1"
Q_UNVERIFIED = "q-2"


# ── a PostgREST-shaped in-memory database ────────────────────────────────────


class Table:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self._filters: list = []
        self._update = None
        self._limit = None
        self._range = None

    def select(self, *a, **k):
        return self

    def eq(self, key, val):
        self._filters.append((key, lambda v, x=val: v == x))
        return self

    def neq(self, key, val):
        self._filters.append((key, lambda v, x=val: v != x))
        return self

    def in_(self, key, vals):
        vals = list(vals)
        self._filters.append((key, lambda v, xs=vals: v in xs))
        return self

    def order(self, *a, **k):
        return self

    def range(self, a, b):
        self._range = (a, b)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def update(self, patch):
        self._update = patch
        return self

    def execute(self):
        rows = [r for r in self.db.setdefault(self.name, [])
                if all(f(r.get(k)) for k, f in self._filters)]
        if self._update is not None:
            for r in rows:
                r.update(copy.deepcopy(self._update))
            return type("R", (), {"data": [dict(r) for r in rows]})()
        if self._range:
            a, b = self._range
            rows = rows[a:b + 1]
        if self._limit is not None:
            rows = rows[: self._limit]
        return type("R", (), {"data": [dict(r) for r in rows]})()


class DB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return Table(self.tables, name)


def _structure(version=1, status="verified", question=Q, **over):
    row = {
        "id": f"s-{question}-{version}", "pyq_question_id": question, "version": version,
        "status": status, **validate_structure(GOOD),
        "generated_by": "ai:test", "generation_meta": {"cost_usd": 0.1},
        "review_notes": "internal note",
    }
    row.update(over)
    return row


def _attempt(aid="a-1", user=USER, status="submitted", mode="typed", **over):
    row = {
        "id": aid, "user_id": user, "pyq_question_id": Q, "status": status,
        "answer_text": "my answer", "word_count": 2, "answer_mode": mode,
        "time_spent_seconds": 60, "self_scores": None, "self_total": 8,
        "started_at": "2026-09-14T10:00:00+00:00",
        "submitted_at": "2026-09-14T10:30:00+00:00" if status == "submitted" else None,
        "structure_version": None, "covered_point_ids": None,
    }
    row.update(over)
    return row


def _db(*, structures=None, attempts=None):
    return DB({
        "pyq_questions": [
            {"id": Q, "reviewer_status": "verified", "question_type": "descriptive",
             "question_text": "Q text", "pyq_paper_id": "p1", "metadata": {}},
            {"id": Q_UNVERIFIED, "reviewer_status": "pending", "question_type": "descriptive",
             "question_text": "Q2", "pyq_paper_id": "p1", "metadata": {}},
        ],
        "pyq_papers": [{"id": "p1", "year": 2023, "metadata": {"gs_paper": "2"}}],
        "answer_structures": structures if structures is not None else [_structure()],
        "descriptive_attempts": attempts if attempts is not None else [_attempt()],
        "descriptive_attempt_pages": [],
        "pyq_question_topic_tags": [],
    })


# ── schema ───────────────────────────────────────────────────────────────────


def test_every_fixture_response_validates():
    for q in QUESTIONS:
        out = validate_structure({k: v for k, v in RESPONSES[q.id].items()})
        assert out["body_points"][0]["id"] == "p1"


@pytest.mark.parametrize("mutate,needle", [
    (lambda s: s.pop("directive"), "directive is required"),
    (lambda s: s.update(body_points="p1, p2"), "body_points must be a list"),
    (lambda s: s.update(body_points=s["body_points"][:1]), "at least 2"),
    (lambda s: s["body_points"][1].update(id="p1"), "duplicated"),
    (lambda s: s["body_points"][0].update(id="Point One"), "body_points[0].id"),
    (lambda s: s["body_points"][0].update(essay="..."), "unknown keys"),
    (lambda s: s.update(model_answer="A full essay"), "unknown fields"),
    (lambda s: s.update(pitfalls=[]), "pitfalls needs at least 1"),
    (lambda s: s.update(intro_angles=[1, 2]), "intro_angles[0] must be a string"),
    (lambda s: s.update(demand="x" * 401), "demand must be at most"),
    (lambda s: s.update(word_budget={"total": -5}), "word_budget.total"),
])
def test_schema_rejects_bad_structures(mutate, needle):
    bad = copy.deepcopy(GOOD)
    mutate(bad)
    with pytest.raises(StructureSchemaError) as exc:
        validate_structure(bad)
    assert any(needle in e for e in exc.value.errors), exc.value.errors


def test_schema_rejects_non_objects():
    for bad in (None, [], "json", 3):
        with pytest.raises(StructureSchemaError):
            validate_structure(bad)


def test_schema_reports_every_error_not_just_the_first():
    bad = copy.deepcopy(GOOD)
    bad.pop("directive")
    bad.pop("demand")
    with pytest.raises(StructureSchemaError) as exc:
        validate_structure(bad)
    assert len(exc.value.errors) >= 2


def test_word_budget_prefers_the_printed_limit_then_marks_then_nothing():
    assert word_budget_for(word_limit=250, marks=10)["total"] == 250
    assert word_budget_for(word_limit=250)["basis"] == "word_limit"
    by_marks = word_budget_for(marks=10)
    assert by_marks == {"total": 150, "intro": 20, "body": 110, "conclusion": 20, "basis": "marks"}
    assert word_budget_for(marks=7) is None
    assert word_budget_for() is None


def test_lint_flags_invented_looking_specifics():
    s = validate_structure(GOOD)
    s["examples"] = ["Literacy rose to 74.04% in the census", "A 2019 report by the council"]
    kinds = {w["kind"] for w in lint_structure(s)}
    assert {"percentage", "dated_report", "named_case"} <= kinds  # Bommai v. Union in GOOD


def test_learner_payload_never_carries_internal_state():
    out = learner_payload(_structure())
    for internal in ("generated_by", "generation_meta", "review_notes", "reviewed_by", "status"):
        assert internal not in out
    assert [p["id"] for p in out["body_points"]] == ["p1", "p2", "p3", "p4", "p5"]


def test_coverage_pct():
    assert coverage_pct(["p1", "p2"], ["p1", "p2", "p3", "p4"]) == 50.0
    assert coverage_pct(["p1", "zz"], ["p1", "p2"]) == 50.0
    assert coverage_pct([], ["p1"]) == 0.0
    assert coverage_pct(None, ["p1"]) is None
    assert coverage_pct(["p1"], []) is None


# ── generator ────────────────────────────────────────────────────────────────


class Scripted:
    """A ModelCall that plays back a list of replies (or exceptions)."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts: list[str] = []

    def __call__(self, system, user):
        self.prompts.append(user)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def _reply(structure, i=1000, o=2000, stop="tool_use"):
    return gen.ModelReply(structure=structure, input_tokens=i, output_tokens=o, stop_reason=stop)


def test_generation_validates_and_attaches_budget_and_meta():
    q = QUESTIONS[0]
    res = gen.generate_one(q, Scripted([_reply(GOOD)]), model="claude-opus-5", sleep=lambda s: None)
    assert res.ok
    assert res.structure["word_budget"]["total"] == 250
    assert res.generation_meta["prompt_version"] == gen.PROMPT_VERSION
    assert res.generation_meta["uncertainty"]
    assert res.generation_meta["lint_warnings"][0]["kind"] == "named_case"
    assert res.cost_usd == pytest.approx(gen.cost_usd("claude-opus-5", 1000, 2000))


def test_a_model_supplied_word_budget_is_ignored():
    fake = {**GOOD, "word_budget": {"total": 5000, "intro": 1, "body": 1, "conclusion": 1}}
    res = gen.generate_one(QUESTIONS[2], Scripted([_reply(fake)]), model="claude-opus-5")
    assert res.ok and res.structure["word_budget"]["total"] == 150  # 10 marks


def test_malformed_output_is_retried_with_the_errors_fed_back():
    bad = copy.deepcopy(GOOD)
    bad["body_points"] = "not a list"
    call = Scripted([_reply(bad), _reply("{not json"), _reply(GOOD)])
    res = gen.generate_one(QUESTIONS[0], call, model="claude-opus-5", sleep=lambda s: None)
    assert res.ok and res.generation_meta["attempts"] == 3
    assert "body_points must be a list" in call.prompts[1]


def test_persistently_malformed_output_fails_and_is_never_returned():
    call = Scripted([_reply({"directive": "x"})] * 3)
    res = gen.generate_one(QUESTIONS[0], call, model="claude-opus-5", sleep=lambda s: None)
    assert not res.ok and res.structure is None and res.error.startswith("schema:")


def test_no_tool_call_counts_as_malformed():
    call = Scripted([_reply(None), _reply(GOOD)])
    assert gen.generate_one(QUESTIONS[0], call, model="claude-opus-5").ok


def test_transient_errors_are_retried_with_backoff_and_fatal_ones_are_not():
    slept = []
    call = Scripted([gen.TransientModelError("429"), _reply(GOOD)])
    assert gen.generate_one(QUESTIONS[0], call, model="claude-opus-5", sleep=slept.append).ok
    assert slept == [2.0]
    call = Scripted([gen.FatalModelError("401 bad key"), _reply(GOOD)])
    res = gen.generate_one(QUESTIONS[0], call, model="claude-opus-5")
    assert not res.ok and res.error.startswith("fatal") and len(call.replies) == 1


def test_a_refusal_is_a_failure_not_a_retry_loop():
    call = Scripted([_reply(None, stop="refusal"), _reply(GOOD)])
    res = gen.generate_one(QUESTIONS[0], call, model="claude-opus-5")
    assert not res.ok and res.error == "refusal"


def test_cost_cap_refuses_a_call_that_could_cross_it():
    budget = gen.CostBudget(max_usd=0.01)  # below one worst-case call
    call = Scripted([_reply(GOOD)])
    res = gen.generate_one(QUESTIONS[0], call, model="claude-opus-5", budget=budget)
    assert not res.ok and res.error == "cost_cap_reached"
    assert call.prompts == []  # the model was never called


def test_cost_cap_also_stops_retries():
    worst = gen.worst_case_cost_usd(
        "claude-opus-5", len(gen.SYSTEM_PROMPT) + len(gen.build_user_prompt(QUESTIONS[0])) + 2000, 4000)
    budget = gen.CostBudget(max_usd=worst * 1.5)
    bad = _reply({"directive": "x"}, i=20_000, o=4000)
    call = Scripted([bad, bad, bad])
    res = gen.generate_one(QUESTIONS[0], call, model="claude-opus-5", budget=budget)
    assert not res.ok and res.error == "cost_cap_reached"
    assert len(call.prompts) == 1
    assert budget.spent == pytest.approx(gen.cost_usd("claude-opus-5", 20_000, 4000))


def test_unknown_models_are_priced_pessimistically():
    assert gen.pricing_for("some-future-model") == gen.pricing_for("claude-fable-5-1")


def test_prompt_carries_every_input_and_the_no_invention_rules():
    user = gen.build_user_prompt(QUESTIONS[0])
    for needle in ("Critically examine", "GS2", "Indian Constitution", "Role of the Governor",
                   "federal structure", "Marks: 15", "Word limit: 250"):
        assert needle in user
    assert "Do NOT invent statistics" in gen.SYSTEM_PROMPT
    assert "describe the evidence TYPE" in gen.SYSTEM_PROMPT


def test_write_draft_goes_through_the_draft_only_rpc():
    calls = []

    class Sb:
        def rpc(self, name, params):
            calls.append((name, params))
            return type("X", (), {"execute": lambda self: type("R", (), {"data": {"id": "s1", "version": 2}})()})()

    res = gen.generate_one(QUESTIONS[0], Scripted([_reply(GOOD)]), model="claude-opus-5")
    out = gen.write_draft(Sb(), res, reason="batch draft run")
    assert out == {"id": "s1", "version": 2}
    name, params = calls[0]
    assert name == "cms_create_answer_structure_draft"
    assert params["p_generated_by"] == "ai:claude-opus-5"
    assert "status" not in params["p_payload"]


# ── learner: hidden before submit, verified only ─────────────────────────────


def test_structure_is_refused_before_submit():
    db = _db(attempts=[_attempt(status="draft")])
    with pytest.raises(d.DescriptiveError) as exc:
        svc.structure_for_attempt(db, USER, "a-1")
    assert exc.value.status == 409 and exc.value.code == "not_submitted"


def test_structure_is_refused_for_another_users_attempt():
    db = _db(attempts=[_attempt(user=OTHER)])
    with pytest.raises(d.DescriptiveError) as exc:
        svc.structure_for_attempt(db, USER, "a-1")
    assert exc.value.status == 404


def test_only_the_verified_structure_is_returned():
    db = _db(structures=[
        _structure(1, "rejected", review_notes="bad"),
        _structure(2, "verified"),
        _structure(3, "draft"),
        _structure(4, "in_review"),
    ])
    out = svc.structure_for_attempt(db, USER, "a-1")
    assert out["structure"]["version"] == 2
    assert "generation_meta" not in out["structure"]


@pytest.mark.parametrize("status", ["draft", "in_review", "rejected"])
def test_no_verified_structure_says_so(status):
    db = _db(structures=[_structure(1, status, review_notes="n")])
    out = svc.structure_for_attempt(db, USER, "a-1")
    assert out["structure"] is None and out["points_covered_pct"] is None


def test_a_verified_structure_of_an_unverified_question_is_not_returned():
    db = _db(structures=[_structure(1, "verified", question=Q_UNVERIFIED)],
             attempts=[_attempt(pyq_question_id=Q_UNVERIFIED)])
    assert svc.structure_for_attempt(db, USER, "a-1")["structure"] is None


# ── learner: ticks ───────────────────────────────────────────────────────────


def test_ticks_persist_on_the_attempt_in_structure_order():
    db = _db()
    out = svc.save_coverage(db, USER, "a-1", structure_version=1,
                            covered_point_ids=["p3", "p1", "p1"])
    assert out["covered_point_ids"] == ["p1", "p3"]
    assert out["points_covered_pct"] == 40.0
    row = db.tables["descriptive_attempts"][0]
    assert row["structure_version"] == 1 and row["covered_point_ids"] == ["p1", "p3"]
    again = svc.structure_for_attempt(db, USER, "a-1")
    assert again["covered_point_ids"] == ["p1", "p3"] and again["points_covered_pct"] == 40.0


def test_ticks_work_for_a_handwritten_attempt():
    db = _db(attempts=[_attempt(mode="handwritten", word_count=None, answer_text="")])
    out = svc.save_coverage(db, USER, "a-1", structure_version=1, covered_point_ids=["p2"])
    assert out["points_covered_pct"] == 20.0
    assert db.tables["descriptive_attempts"][0]["covered_point_ids"] == ["p2"]


def test_ticks_are_refused_before_submit():
    db = _db(attempts=[_attempt(status="draft")])
    with pytest.raises(d.DescriptiveError) as exc:
        svc.save_coverage(db, USER, "a-1", structure_version=1, covered_point_ids=["p1"])
    assert exc.value.code == "not_submitted"


def test_unknown_point_ids_are_refused():
    with pytest.raises(d.DescriptiveError) as exc:
        svc.save_coverage(_db(), USER, "a-1", structure_version=1, covered_point_ids=["p9"])
    assert exc.value.status == 422


def test_ticks_against_a_replaced_version_are_refused():
    db = _db(structures=[_structure(1, "rejected", review_notes="old"), _structure(2, "verified")])
    with pytest.raises(d.DescriptiveError) as exc:
        svc.save_coverage(db, USER, "a-1", structure_version=1, covered_point_ids=["p1"])
    assert exc.value.code == "structure_changed"


def test_old_ticks_are_not_carried_onto_a_new_version():
    db = _db(structures=[_structure(1, "rejected", review_notes="old"), _structure(2, "verified")],
             attempts=[_attempt(structure_version=1, covered_point_ids=["p1", "p2"])])
    out = svc.structure_for_attempt(db, USER, "a-1")
    assert out["covered_point_ids"] == [] and out["ticks_from_older_version"] is True


# ── roll-ups ─────────────────────────────────────────────────────────────────


def test_attempt_coverage_measures_against_the_version_ticked():
    db = _db(structures=[_structure(1, "rejected", review_notes="old"), _structure(2, "verified")],
             attempts=[_attempt("a-1", structure_version=1, covered_point_ids=["p1"]),
                       _attempt("a-2", structure_version=2, covered_point_ids=["p1", "p2"]),
                       _attempt("a-3")])
    cov = svc.attempt_coverage(db, db.tables["descriptive_attempts"])
    assert cov == {"a-1": 20.0, "a-2": 40.0}


def test_history_rows_and_analytics_carry_points_covered(monkeypatch):
    monkeypatch.setattr(d, "_primary_topic_names", lambda sb, ids: {})
    monkeypatch.setattr(d, "_paper_context", lambda sb, qs: ({}, {}))
    db = _db(attempts=[
        _attempt("a-1", structure_version=1, covered_point_ids=["p1", "p2"]),
        _attempt("a-2", structure_version=1, covered_point_ids=["p1", "p2", "p3", "p4"]),
        _attempt("a-3"),
    ])
    rows = {r["id"]: r for r in d._enrich_attempts(db, db.tables["descriptive_attempts"])}
    assert rows["a-1"]["points_covered_pct"] == 40.0
    assert rows["a-3"]["points_covered_pct"] is None
    stats = d.analytics(db, USER, today="2026-09-20")
    assert stats["points_covered"] == {"avg_pct": 60.0, "sample": 2}
    assert stats["weeks"][-1]["avg_points_covered_pct"] == 60.0
    assert stats["weeks"][-1]["points_sample"] == 2


def test_attempt_payload_exposes_the_ticks():
    p = d.attempt_payload(_attempt(structure_version=3, covered_point_ids=["p1"]))
    assert p["structure_version"] == 3 and p["covered_point_ids"] == ["p1"]
