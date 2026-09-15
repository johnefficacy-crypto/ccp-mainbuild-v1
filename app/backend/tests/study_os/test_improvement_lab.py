"""GQR-S6 — personalized Improvement Lab learner feeds (Quant + Reasoning).

Covers the bounded, owner-scoped, verified-only evidence feed
(`study_os.improvement_lab.build_feed`) and the two `/api/study/improvement-lab/*`
endpoints. Contract: docs/architecture/solution-strategies-improvement-lab.md §10.3.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import study_os as study_os_api
from app.core.auth import get_current_user
from app.study_os import improvement_lab as il
from tests.persona_questions._stub import SBStub


# ── fixtures ──────────────────────────────────────────────────────────────────

def _att(aid, submitted_at, *, user="u-1", status="submitted"):
    return {"id": aid, "user_id": user, "status": status, "submitted_at": submitted_at}


def _resp(aid, qid, is_correct):
    return {"id": f"r-{aid}-{qid}", "attempt_id": aid, "question_id": qid, "is_correct": is_correct}


def _qheur(hid, *, name="H", status="verified", active=True, **over):
    row = {
        "id": hid, "topic_id": "t1", "microtopic_id": None,
        "topic": {"subject": {"slug": "quantitative-aptitude", "subject_group": "numerical"}},
        "content_type": "quant_heuristic",
        "card_code": f"c-{hid}", "name": name, "card_subtype": "shortcut",
        "applicability_rule": {"op": "x"}, "formula_latex": "x", "standard_method": "s",
        "faster_method": "f", "worked_example": "e", "common_traps": "t",
        "reviewer_status": status, "reviewer_notes": "n", "reviewed_by": "a",
        "created_by": "b", "is_active": active, "updated_at": "2026-07-14T00:00:00Z",
    }
    row.update(over)
    return row


def _qlink(qid, hid, *, relevance="primary", status="verified"):
    return {"id": f"l-{qid}-{hid}", "question_id": qid, "card_id": hid,
            "relevance": relevance, "reviewer_status": status,
            "question": {"topic_id": "t1", "microtopic_id": None}}


def _rstrat(sid, *, name="S", status="verified", active=True, **over):
    row = {
        "id": sid, "topic_id": "rt1", "microtopic_id": None,
        "topic": {"subject": {"slug": "reasoning", "subject_group": "reasoning"}},
        "content_type": "reasoning_strategy",
        "card_code": f"c-{sid}", "name": name, "card_subtype": "approach",
        "applicability_rule": {"op": "x"}, "formula_latex": "x", "standard_method": "s",
        "faster_method": "f", "key_observation": "k", "worked_example": "e",
        "common_traps": "t", "reviewer_status": status, "reviewer_notes": "n",
        "reviewed_by": "a", "created_by": "b", "is_active": active,
        "updated_at": "2026-07-14T00:00:00Z",
    }
    row.update(over)
    return row


def _rlink(qid, sid, *, relevance="primary", status="verified"):
    return {"id": f"l-{qid}-{sid}", "question_id": qid, "card_id": sid,
            "relevance": relevance, "reviewer_status": status,
            "question": {"topic_id": "rt1", "microtopic_id": None}}


def _empty_sources(**tables):
    """Build a stub database for the feed.

    Migration 291 merged quant_heuristics and reasoning_strategies into one
    ``content_cards`` table. Call sites still pass ``quant_heuristics=`` /
    ``reasoning_strategies=`` because naming the subject keeps each test
    readable; both are folded into the single merged list here, which is exactly
    what the production readers now see.
    """
    base = {
        "mock_attempts": [], "mock_attempt_responses": [],
        # Migration 292 merged the three junctions too, so this is one list.
        "content_card_links": [],
        "content_cards": [],
    }
    cards, links = [], []
    for legacy in ("quant_heuristics", "reasoning_strategies"):
        cards.extend(tables.pop(legacy, []) or [])
    for legacy in ("quant_question_heuristics", "reasoning_question_strategies",
                   "reasoning_stimulus_strategies"):
        links.extend(tables.pop(legacy, []) or [])
    base.update(tables)
    if cards:
        base["content_cards"] = [*base["content_cards"], *cards]
    if links:
        base["content_card_links"] = [*base["content_card_links"], *links]
    return base


# ── builder: scope + evidence ─────────────────────────────────────────────────

def test_feed_is_owner_and_submitted_scoped():
    sb = SBStub(_empty_sources(
        mock_attempts=[
            _att("a1", "2026-07-10T00:00:00Z"),                     # u-1 submitted → q1
            _att("a2", "2026-07-11T00:00:00Z", user="other"),      # other user → q2
            _att("a3", "2026-07-12T00:00:00Z", status="in_progress"),  # u-1 unsubmitted → q3
        ],
        mock_attempt_responses=[_resp("a1", "q1", False), _resp("a2", "q2", False), _resp("a3", "q3", False)],
        quant_question_heuristics=[_qlink("q1", "h1"), _qlink("q2", "h2"), _qlink("q3", "h3")],
        quant_heuristics=[_qheur("h1", name="Own"), _qheur("h2", name="Other"), _qheur("h3", name="Draft")],
    ))
    out = il.build_feed(sb, "u-1", "quant")
    assert [s["id"] for s in out] == ["h1"]  # only the owner's SUBMITTED attempt's question


def test_feed_aggregates_evidence_across_attempts():
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z"), _att("a2", "2026-07-12T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q1", False), _resp("a2", "q1", True)],
        quant_question_heuristics=[_qlink("q1", "h1")],
        quant_heuristics=[_qheur("h1")],
    ))
    item = il.build_feed(sb, "u-1", "quant")[0]
    assert item["times_seen"] == 2
    assert item["wrong_count"] == 1
    assert item["correct_count"] == 1
    assert item["last_seen_at"] == "2026-07-12T00:00:00Z"  # most recent attempt
    assert item["source_question_ids"] == ["q1"]


def test_feed_excludes_skipped_unanswered_questions():
    # A submitted mock keeps a response row for skipped questions (is_correct=None);
    # those must NOT create strategy evidence (Codex #999) — only q-done appears.
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q-skip", None), _resp("a1", "q-done", False)],
        quant_question_heuristics=[_qlink("q-skip", "h-skip"), _qlink("q-done", "h-done")],
        quant_heuristics=[_qheur("h-skip", name="Skipped"), _qheur("h-done", name="Attempted")],
    ))
    out = il.build_feed(sb, "u-1", "quant")
    assert [s["id"] for s in out] == ["h-done"]
    assert out[0]["times_seen"] == 1 and out[0]["wrong_count"] == 1


def test_feed_unrelated_subject_outage_does_not_break_this_feed(monkeypatch):
    # A Reasoning-side outage must NOT 502 the Quant feed — the aggregator reads
    # each subject through its own reader and keeps one subject's failure to
    # that subject (Codex #999 isolation).
    #
    # WHERE that isolation lives has moved twice, and this test moved with it.
    # Originally the two subjects had separate content tables AND separate link
    # tables, so the outage could be simulated by failing a table read and the
    # isolation was a storage fact. Migration 291 merged the content tables;
    # migration 292 merged the link tables. There is now NO table that belongs
    # to one subject, so a table-level outage is a shared-dependency outage by
    # construction and would correctly take down both feeds.
    #
    # What survives — and what the Improvement Lab actually depends on — is
    # isolation in the READ PATH: solution_strategies calls each subject's
    # reader inside its own try/except, so a reasoning read that raises yields
    # empty reasoning strategies rather than failing the response. That is a
    # real, load-bearing guarantee, and failing the reasoning reader is the
    # honest way to prove it now.
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q1", False)],
        quant_question_heuristics=[_qlink("q1", "h1")], quant_heuristics=[_qheur("h1")],
    ))
    monkeypatch.setattr(
        il.solution_strategies.reasoning_strategies, "strategies_for_questions",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("reasoning source down")),
    )
    assert [s["id"] for s in il.build_feed(sb, "u-1", "quant")] == ["h1"]  # healthy, no raise
    assert _client(sb).get("/api/study/improvement-lab/quant").status_code == 200


def test_feed_excludes_unverified_strategy():
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q1", False)],
        quant_question_heuristics=[_qlink("q1", "h1")],
        quant_heuristics=[_qheur("h1", status="pending")],  # not verified → gated out
    ))
    assert il.build_feed(sb, "u-1", "quant") == []


def test_feed_is_not_a_full_library_dump():
    # A verified heuristic on a question the learner never attempted must not appear.
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q1", False)],
        quant_question_heuristics=[_qlink("q1", "h1"), _qlink("q-unseen", "h2")],
        quant_heuristics=[_qheur("h1", name="Seen"), _qheur("h2", name="Never attempted")],
    ))
    assert [s["id"] for s in il.build_feed(sb, "u-1", "quant")] == ["h1"]


def test_feed_subject_filter_quant_vs_reasoning():
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q-quant", False), _resp("a1", "q-reason", False)],
        quant_question_heuristics=[_qlink("q-quant", "h1")],
        quant_heuristics=[_qheur("h1", name="Quant one")],
        reasoning_question_strategies=[_rlink("q-reason", "s1")],
        reasoning_strategies=[_rstrat("s1", name="Reasoning one")],
    ))
    assert [s["subject_family"] for s in il.build_feed(sb, "u-1", "quant")] == ["quant"]
    assert [s["subject_family"] for s in il.build_feed(sb, "u-1", "reasoning")] == ["reasoning"]


def test_feed_ranks_wrong_associated_first():
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q-wrong", False), _resp("a1", "q-right", True)],
        quant_question_heuristics=[_qlink("q-wrong", "h-wrong"), _qlink("q-right", "h-right")],
        quant_heuristics=[_qheur("h-wrong", name="Zzz late-alpha"), _qheur("h-right", name="Aaa early-alpha")],
    ))
    out = il.build_feed(sb, "u-1", "quant")
    # h-wrong has a wrong answer → ranks before the all-correct h-right despite name order.
    assert [s["id"] for s in out] == ["h-wrong", "h-right"]


def test_feed_strips_governance_and_carries_evidence():
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q1", False)],
        quant_question_heuristics=[_qlink("q1", "h1")],
        quant_heuristics=[_qheur("h1")],
    ))
    item = il.build_feed(sb, "u-1", "quant")[0]
    assert item["subject_family"] == "quant"
    for ev in ("times_seen", "wrong_count", "correct_count", "last_seen_at", "source_question_ids"):
        assert ev in item
    for forbidden in ("applicability_rule", "reviewer_status", "reviewer_notes",
                      "reviewed_by", "created_by", "is_active", "card_code"):
        assert forbidden not in item


def test_feed_empty_history_returns_empty_and_no_user():
    sb = SBStub(_empty_sources())
    assert il.build_feed(sb, "u-1", "quant") == []
    assert il.build_feed(sb, None, "quant") == []


def test_feed_read_failure_propagates_not_disguised_as_empty():
    # A feed READ failure must surface (checkpost #999 F1), NOT be masked as an
    # empty history — otherwise the client shows "no history" during an outage.
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q1", False)],
        quant_question_heuristics=[_qlink("q1", "h1")], quant_heuristics=[_qheur("h1")],
    ))
    orig = sb.table

    def _boom(name):
        if name == "mock_attempts":
            raise RuntimeError("db down")
        return orig(name)

    sb.table = _boom  # type: ignore[assignment]
    import pytest
    with pytest.raises(RuntimeError):
        il.build_feed(sb, "u-1", "quant")


def test_feed_aggregates_strongest_relevance_regardless_of_order():
    # Strategy h1 linked to two attempted questions with different relevance; the
    # strongest (primary) must win independent of row order (checkpost #999 F3).
    def _sb(links):
        return SBStub(_empty_sources(
            mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
            mock_attempt_responses=[_resp("a1", "q1", False), _resp("a1", "q2", False)],
            quant_question_heuristics=links,
            quant_heuristics=[_qheur("h1")],
        ))
    forward = il.build_feed(_sb([_qlink("q1", "h1", relevance="related"),
                                 _qlink("q2", "h1", relevance="primary")]), "u-1", "quant")
    reverse = il.build_feed(_sb([_qlink("q2", "h1", relevance="primary"),
                                 _qlink("q1", "h1", relevance="related")]), "u-1", "quant")
    assert forward[0]["relevance"] == "primary"
    assert reverse[0]["relevance"] == "primary"


def test_feed_source_questions_are_recent_first():
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a-old", "2026-07-01T00:00:00Z"), _att("a-new", "2026-07-20T00:00:00Z")],
        mock_attempt_responses=[_resp("a-old", "q-old", False), _resp("a-new", "q-new", False)],
        quant_question_heuristics=[_qlink("q-old", "h1"), _qlink("q-new", "h1")],
        quant_heuristics=[_qheur("h1")],
    ))
    item = il.build_feed(sb, "u-1", "quant")[0]
    assert item["source_question_ids"] == ["q-new", "q-old"]  # newest-seen first
    assert item["last_seen_at"] == "2026-07-20T00:00:00Z"


def test_feed_is_deterministic_under_reordered_responses():
    resA = [_resp("a1", "q1", False), _resp("a1", "q2", True)]
    common = dict(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        quant_question_heuristics=[_qlink("q1", "h1"), _qlink("q2", "h2")],
        quant_heuristics=[_qheur("h1", name="Alpha"), _qheur("h2", name="Beta")],
    )
    a = il.build_feed(SBStub(_empty_sources(mock_attempt_responses=resA, **common)), "u-1", "quant")
    b = il.build_feed(SBStub(_empty_sources(mock_attempt_responses=list(reversed(resA)), **common)), "u-1", "quant")
    assert [s["id"] for s in a] == [s["id"] for s in b]


def test_feed_window_is_recency_bounded_older_excluded(monkeypatch):
    # Saturated window keeps the NEWEST-seen questions and drops older ones,
    # regardless of attempt storage/input order (checkpost #999 F2 overflow).
    monkeypatch.setattr(il, "_MAX_QUESTIONS", 1)

    def _sb(attempt_rows):
        return SBStub(_empty_sources(
            mock_attempts=attempt_rows,
            mock_attempt_responses=[_resp("a-old", "q-old", False), _resp("a-new", "q-new", False)],
            quant_question_heuristics=[_qlink("q-old", "h-old"), _qlink("q-new", "h-new")],
            quant_heuristics=[_qheur("h-old", name="Old"), _qheur("h-new", name="New")],
        ))

    newest = [_att("a-old", "2026-07-01T00:00:00Z"), _att("a-new", "2026-07-20T00:00:00Z")]
    assert [s["id"] for s in il.build_feed(_sb(newest), "u-1", "quant")] == ["h-new"]
    # Reversed attempt input order → same recency-selected window.
    assert [s["id"] for s in il.build_feed(_sb(list(reversed(newest))), "u-1", "quant")] == ["h-new"]


def test_feed_strategy_read_failure_propagates_not_disguised_as_empty():
    # A strategy/link table outage must surface (checkpost #999 F1 follow-up), NOT
    # be masked as an empty feed — the aggregator is called in strict mode.
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q1", False)],
        quant_question_heuristics=[_qlink("q1", "h1")], quant_heuristics=[_qheur("h1")],
    ))
    orig = sb.table

    def _boom(name):
        if name == "content_card_links":
            raise RuntimeError("strategy table down")
        return orig(name)

    sb.table = _boom  # type: ignore[assignment]
    import pytest
    with pytest.raises(RuntimeError):
        il.build_feed(sb, "u-1", "quant")


# ── endpoint wiring ───────────────────────────────────────────────────────────

def _client(sb, *, user_id="u-1"):
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id, "role": "user"}
    return TestClient(app, raise_server_exceptions=False)


def test_endpoints_return_items_and_are_owner_scoped():
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q1", False)],
        quant_question_heuristics=[_qlink("q1", "h1")],
        quant_heuristics=[_qheur("h1", name="Methods one")],
    ))
    client = _client(sb)
    r = client.get("/api/study/improvement-lab/quant")
    assert r.status_code == 200, r.text
    body = r.json()
    assert [s["id"] for s in body["items"]] == ["h1"]
    # Reasoning feed for the same learner is empty (no reasoning content attempted).
    r2 = client.get("/api/study/improvement-lab/reasoning")
    assert r2.status_code == 200 and r2.json()["items"] == []
    # A different learner sees nothing.
    assert _client(sb, user_id="other").get("/api/study/improvement-lab/quant").json()["items"] == []


def test_endpoint_maps_a_feed_read_failure_to_non_2xx():
    # An outage must reach the client as an error (checkpost #999 F1), not a 200
    # empty body — so the section renders its error state, not "nothing to revisit".
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q1", False)],
        quant_question_heuristics=[_qlink("q1", "h1")], quant_heuristics=[_qheur("h1")],
    ))
    orig = sb.table

    def _boom(name):
        if name == "mock_attempts":
            raise RuntimeError("db down")
        return orig(name)

    sb.table = _boom  # type: ignore[assignment]
    r = _client(sb).get("/api/study/improvement-lab/quant")
    assert r.status_code == 502, r.text


def test_endpoint_maps_a_strategy_read_failure_to_non_2xx():
    sb = SBStub(_empty_sources(
        mock_attempts=[_att("a1", "2026-07-10T00:00:00Z")],
        mock_attempt_responses=[_resp("a1", "q1", False)],
        quant_question_heuristics=[_qlink("q1", "h1")], quant_heuristics=[_qheur("h1")],
    ))
    orig = sb.table

    def _boom(name):
        if name == "content_cards":
            raise RuntimeError("strategy table down")
        return orig(name)

    sb.table = _boom  # type: ignore[assignment]
    assert _client(sb).get("/api/study/improvement-lab/quant").status_code == 502
