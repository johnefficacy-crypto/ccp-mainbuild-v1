"""GQR-Q7 — quant heuristic authority: verified-only reads + review lifecycle.

The learner-feedback read must expose a heuristic only when BOTH its question
link and the heuristic row are verified (and the heuristic is active), and the
linked question scope matches the heuristic scope — defense in depth. The review
RPC wrapper must honour the transition matrix, CAS, and the verified→needs_correction
notes gate.
"""
from __future__ import annotations

import pytest

from app.study_os import quant_heuristics as qh
from tests.persona_questions._stub import SBStub


_TOKEN = "2026-07-10T00:00:00Z"  # matches the seeded heuristic's updated_at (content CAS)


def _subject(family="quant"):
    return {
        "slug": "quantitative-aptitude" if family == "quant" else "reasoning",
        "subject_group": "numerical" if family == "quant" else "reasoning",
    }


def _heuristic(
    hid,
    *,
    status="verified",
    active=True,
    name="H",
    topic="t1",
    micro=None,
    topic_family="quant",
    micro_family="quant",
    micro_parent=None,
):
    return {
        "id": hid, "topic_id": topic, "microtopic_id": micro,
        "topic": {"subject": _subject(topic_family)} if topic else None,
        "microtopic": {
            "parent_topic_id": topic if micro_parent is None else micro_parent,
            "subject": _subject(micro_family),
        } if micro else None,
        "heuristic_code": f"code-{hid}", "name": name,
        "heuristic_type": "shortcut", "applicability_rule": {},
        "reviewer_status": status, "is_active": active, "updated_at": _TOKEN,
    }


def _link(
    qid,
    hid,
    *,
    status="verified",
    relevance="primary",
    topic="t1",
    micro=None,
):
    return {
        "id": f"lnk-{hid}", "question_id": qid, "heuristic_id": hid,
        "relevance": relevance, "reviewer_status": status,
        "question": {"topic_id": topic, "microtopic_id": micro},
    }


# ── verified-only conjunctive read ────────────────────────────────────────────

def test_returns_only_double_verified_active():
    sb = SBStub({
        "quant_heuristics": [
            _heuristic("h-ok", status="verified", active=True, name="B"),
            _heuristic("h-pending", status="pending", active=True, name="A"),
            _heuristic("h-inactive", status="verified", active=False, name="C"),
        ],
        "quant_question_heuristics": [
            _link("q1", "h-ok", status="verified", relevance="primary"),
            _link("q1", "h-pending", status="verified", relevance="primary"),
            _link("q1", "h-inactive", status="verified", relevance="primary"),
        ],
    })
    out = qh.heuristics_for_question(sb, "q1")
    assert [h["id"] for h in out] == ["h-ok"]


def test_unverified_link_excluded_even_if_heuristic_verified():
    sb = SBStub({
        "quant_heuristics": [_heuristic("h-ok", status="verified")],
        "quant_question_heuristics": [_link("q1", "h-ok", status="pending")],
    })
    assert qh.heuristics_for_question(sb, "q1") == []


def test_scope_mismatch_excluded_even_if_both_rows_verified():
    sb = SBStub({
        "quant_heuristics": [_heuristic("h-ok", status="verified", topic="quant-topic")],
        "quant_question_heuristics": [
            _link("q1", "h-ok", status="verified", topic="reasoning-topic")
        ],
    })
    assert qh.heuristics_for_question(sb, "q1") == []


def test_non_quant_canonical_scope_excluded_even_when_ids_match():
    sb = SBStub({
        "quant_heuristics": [
            _heuristic("h-bad", topic="reasoning-topic", topic_family="reasoning")
        ],
        "quant_question_heuristics": [
            _link("q1", "h-bad", topic="reasoning-topic")
        ],
    })
    assert qh.heuristics_for_question(sb, "q1") == []


def test_inconsistent_topic_microtopic_parent_excluded():
    sb = SBStub({
        "quant_heuristics": [
            _heuristic("h-bad", topic="t1", micro="m1", micro_parent="other-topic")
        ],
        "quant_question_heuristics": [
            _link("q1", "h-bad", topic="t1", micro="m1")
        ],
    })
    assert qh.heuristics_for_question(sb, "q1") == []


def test_ordered_by_relevance_then_name():
    sb = SBStub({
        "quant_heuristics": [
            _heuristic("h-a", name="Alpha"),
            _heuristic("h-b", name="Beta"),
            _heuristic("h-c", name="Gamma"),
        ],
        "quant_question_heuristics": [
            _link("q1", "h-c", relevance="related"),
            _link("q1", "h-b", relevance="secondary"),
            _link("q1", "h-a", relevance="primary"),
        ],
    })
    out = qh.heuristics_for_question(sb, "q1")
    assert [h["id"] for h in out] == ["h-a", "h-b", "h-c"]
    assert [h["relevance"] for h in out] == ["primary", "secondary", "related"]


def test_no_links_returns_empty():
    sb = SBStub({"quant_heuristics": [_heuristic("h-ok")], "quant_question_heuristics": []})
    assert qh.heuristics_for_question(sb, "q1") == []


# ── topic-scoped verified list ────────────────────────────────────────────────

def test_list_topic_verified_active_only():
    sb = SBStub({
        "quant_heuristics": [
            _heuristic("h1", status="verified", active=True, topic="t1", name="Z"),
            _heuristic("h2", status="pending", active=True, topic="t1"),
            _heuristic("h3", status="verified", active=False, topic="t1"),
            _heuristic("h4", status="verified", active=True, topic="t2"),
            _heuristic("h5", status="verified", active=True, topic="t1", name="A"),
        ],
    })
    out = qh.list_verified_heuristics_for_topic(sb, topic_id="t1")
    assert [h["id"] for h in out] == ["h5", "h1"]


def test_list_requires_a_scope():
    sb = SBStub({"quant_heuristics": [_heuristic("h1")]})
    assert qh.list_verified_heuristics_for_topic(sb) == []


# ── review lifecycle RPC wrapper ──────────────────────────────────────────────

def _review_db(status="pending"):
    return SBStub({
        "quant_heuristics": [_heuristic("h1", status=status)],
        "admin_audit_logs": [],
    })


def test_review_pending_to_verified_ok():
    sb = _review_db("pending")
    res = qh.review_heuristic(
        sb, heuristic_id="h1", expected_status="pending", expected_updated_at=_TOKEN,
        new_status="verified", reviewer_notes=None, reason="clear shortcut, verified",
        actor_user_id="admin-1", actor_email="a@x",
    )
    assert res["ok"] is True and res["new_status"] == "verified"
    assert sb.db["quant_heuristics"][0]["reviewer_status"] == "verified"
    assert len(sb.db["admin_audit_logs"]) == 1
    assert sb.db["admin_audit_logs"][0]["notes"] == "clear shortcut, verified"


def test_review_invalid_transition_raises():
    sb = _review_db("pending")
    with pytest.raises(RuntimeError, match="transition_not_allowed"):
        qh.review_heuristic(
            sb, heuristic_id="h1", expected_status="pending", expected_updated_at=_TOKEN,
            new_status="pending", reviewer_notes=None, reason="a valid audit reason",
            actor_user_id="admin-1", actor_email="a@x",
        )


def test_review_stale_expected_status_raises():
    sb = _review_db("verified")
    with pytest.raises(RuntimeError, match="concurrent_modification"):
        qh.review_heuristic(
            sb, heuristic_id="h1", expected_status="pending", expected_updated_at=_TOKEN,
            new_status="verified", reviewer_notes=None, reason="a valid audit reason",
            actor_user_id="admin-1", actor_email="a@x",
        )


def test_review_stale_content_token_raises():
    sb = _review_db("pending")
    with pytest.raises(RuntimeError, match="concurrent_modification"):
        qh.review_heuristic(
            sb, heuristic_id="h1", expected_status="pending", expected_updated_at="2000-01-01T00:00:00Z",
            new_status="verified", reviewer_notes=None, reason="a valid audit reason",
            actor_user_id="admin-1", actor_email="a@x",
        )


def test_review_invalid_reason_raises():
    sb = _review_db("pending")
    with pytest.raises(RuntimeError, match="invalid_reason"):
        qh.review_heuristic(
            sb, heuristic_id="h1", expected_status="pending", expected_updated_at=_TOKEN,
            new_status="verified", reviewer_notes=None, reason="short",
            actor_user_id="admin-1", actor_email="a@x",
        )


def test_review_reopen_verified_requires_notes():
    sb = _review_db("verified")
    with pytest.raises(RuntimeError, match="invalid_reviewer_notes"):
        qh.review_heuristic(
            sb, heuristic_id="h1", expected_status="verified", expected_updated_at=_TOKEN,
            new_status="needs_correction", reviewer_notes="  ", reason="reopening for correction",
            actor_user_id="admin-1", actor_email="a@x",
        )
    res = qh.review_heuristic(
        sb, heuristic_id="h1", expected_status="verified", expected_updated_at=_TOKEN,
        new_status="needs_correction", reviewer_notes="ambiguous applicability rule",
        reason="reopening for correction", actor_user_id="admin-1", actor_email="a@x",
    )
    assert res["new_status"] == "needs_correction"


def test_review_missing_actor_raises():
    sb = _review_db("pending")
    with pytest.raises(RuntimeError, match="missing_actor_id"):
        qh.review_heuristic(
            sb, heuristic_id="h1", expected_status="pending", expected_updated_at=_TOKEN,
            new_status="verified", reviewer_notes=None, reason="a valid audit reason",
            actor_user_id=None, actor_email="a@x",
        )
