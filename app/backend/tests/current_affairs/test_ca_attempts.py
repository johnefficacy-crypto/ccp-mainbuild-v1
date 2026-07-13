"""CA learner attempt runtime tests (GQR-G5a): freeze/start, learner view, save, submit.

``CaSB`` emulates the three atomic RPCs (start / save / submit) against the in-memory
store — including the integrity checks, seq guard, and ownership errors the PL/pgSQL
enforces — so the service layer is exercised end-to-end. Real Postgres concurrency /
replay behaviour is VERIFY DB (validate_ca_attempt_rpcs.sql).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.current_affairs import attempts, bundles
from tests.persona_questions._stub import SBStub, _RpcCall

_NOW = datetime(2026, 7, 13, tzinfo=timezone.utc)
_FUTURE = (_NOW + timedelta(days=10)).isoformat()
_PAST = (_NOW - timedelta(days=1)).isoformat()


class CaSB(SBStub):
    """SBStub + emulation of the CA start/save/submit RPCs."""

    def rpc(self, name, params=None):
        params = params or {}
        if name == "ca_start_current_affairs_attempt":
            return _RpcCall(self._ca_start(params))
        if name == "ca_save_current_affairs_answer":
            return _RpcCall(self._ca_save(params))
        if name == "ca_submit_current_affairs_attempt":
            return _RpcCall(self._ca_submit(params))
        return super().rpc(name, params)

    def _ca_start(self, p):
        import uuid as _uuid
        bundle = next((b for b in self.db.get("current_affairs_bundles", [])
                       if b.get("id") == p["p_bundle"]), None)
        if bundle is None:
            raise RuntimeError("bundle_not_found")
        if bundle.get("status") != "published":
            raise RuntimeError("bundle_not_published")
        if bundle.get("reviewer_status") != "verified":
            raise RuntimeError("bundle_not_verified")
        eligible = set(bundles.eligible_bundle_question_ids(self, p["p_bundle"], now=_NOW))
        if not eligible:
            raise RuntimeError("empty_bundle")
        caller = {r["question_id"] for r in (p.get("p_response_rows") or [])}
        if caller != eligible:
            raise RuntimeError("bundle_set_mismatch")
        attempts_store = self.db.setdefault("current_affairs_attempts", [])
        existing = next((a for a in attempts_store
                         if a.get("user_id") == p["p_user"] and a.get("bundle_id") == p["p_bundle"]), None)
        if existing is not None:
            if existing.get("status") == "in_progress":
                return {"outcome": "reused", "attempt_id": existing["id"],
                        "question_count": existing.get("total_questions")}
            raise RuntimeError("attempt_already_submitted")
        aid = str(_uuid.uuid4())
        attempts_store.append({
            "id": aid, "user_id": p["p_user"], "exam_id": p.get("p_exam"),
            "bundle_id": p["p_bundle"], "cadence": bundle.get("cadence"),
            "status": "in_progress", "template_snapshot": p.get("p_template_snapshot") or {},
            "total_questions": len(eligible),
        })
        resp_store = self.db.setdefault("current_affairs_attempt_responses", [])
        for r in p.get("p_response_rows") or []:
            resp_store.append({
                "id": str(_uuid.uuid4()), "attempt_id": aid,
                "mock_question_id": r["question_id"], "question_snapshot": r["question_snapshot"],
                "selected_option_id": None, "client_seq": 0, "is_visited": False,
            })
        return {"outcome": "ready", "attempt_id": aid, "question_count": len(eligible)}

    def _ca_save(self, p):
        att = next((a for a in self.db.get("current_affairs_attempts", [])
                    if a.get("id") == p["p_attempt_id"]), None)
        if att is None:
            raise RuntimeError("attempt_not_found")
        if str(att.get("user_id")) != str(p["p_user"]):
            raise RuntimeError("not_attempt_owner")
        if att.get("status") != "in_progress":
            raise RuntimeError("attempt_not_in_progress")
        resp = next((r for r in self.db.get("current_affairs_attempt_responses", [])
                     if r.get("attempt_id") == p["p_attempt_id"]
                     and r.get("mock_question_id") == p["p_question_id"]), None)
        if resp is None:
            raise RuntimeError("question_not_in_attempt")
        if p.get("p_selected_option_id") is not None:
            opts = (resp.get("question_snapshot") or {}).get("options") or []
            if not any(str(o.get("id")) == str(p["p_selected_option_id"]) for o in opts):
                raise RuntimeError("option_not_in_question")
        if int(p.get("p_client_seq") or 0) <= int(resp.get("client_seq") or 0) \
                and (resp.get("is_visited") or resp.get("selected_option_id")):
            return {"ok": True, "idempotent": True, "status": "already_recorded"}
        resp.update({
            "selected_option_id": p.get("p_selected_option_id"),
            "is_marked_for_review": bool(p.get("p_is_marked_for_review")),
            "is_visited": True, "time_spent_sec": max(int(p.get("p_time_spent_sec") or 0), 0),
            "client_seq": max(int(p.get("p_client_seq") or 0), 0),
        })
        return {"ok": True, "status": "recorded"}

    def _ca_submit(self, p):
        att = next((a for a in self.db.get("current_affairs_attempts", [])
                    if a.get("id") == p["p_attempt_id"]), None)
        if att is None:
            raise RuntimeError("attempt_not_found")
        if str(att.get("user_id")) != str(p["p_user"]):
            raise RuntimeError("not_attempt_owner")
        if att.get("status") == "submitted":
            return {"outcome": "already_submitted", "attempt_id": att["id"],
                    "score_raw": att.get("score_raw"), "total_correct": att.get("total_correct")}
        resps = [r for r in self.db.get("current_affairs_attempt_responses", [])
                 if r.get("attempt_id") == p["p_attempt_id"]]
        correct = wrong = unatt = 0
        for r in resps:
            sel = r.get("selected_option_id")
            key = (r.get("question_snapshot") or {}).get("correct_option_id")
            r["is_correct"] = sel is not None and str(sel) == str(key)
            if sel is None:
                unatt += 1
            elif r["is_correct"]:
                correct += 1
            else:
                wrong += 1
        att.update({"status": "submitted", "total_correct": correct, "total_wrong": wrong,
                    "total_unattempted": unatt, "score_raw": correct})
        return {"outcome": "submitted", "attempt_id": att["id"], "total_correct": correct,
                "total_wrong": wrong, "total_unattempted": unatt, "score_raw": correct}


def _start_seed():
    return {
        "exams": [{"id": "e1", "exam_family_id": None}],
        "current_affairs_bundles": [{
            "id": "b1", "cadence": "weekly", "status": "published", "reviewer_status": "verified",
            "exam_id": None, "exam_family_id": None,
            "period_start": "2026-07-06", "period_end": "2026-07-12",
            "available_until": _FUTURE, "publish_at": _PAST,
        }],
        "current_affairs_bundle_questions": [
            {"bundle_id": "b1", "mock_question_id": "q1", "display_order": 0}],
        "mock_question_bank": [{
            "id": "q1", "question_text": "Who issued the June circular?", "question_type": "mcq",
            "correct_option_id": "o1", "source_kind": "current_event", "is_current_based": True,
            "reviewer_status": "verified", "valid_until": _FUTURE, "valid_from": None,
            "difficulty": "medium", "explanation": "RBI.", "current_affairs_item_id": "ev1",
        }],
        "mock_question_options": [
            {"id": "o1", "question_id": "q1", "option_text": "RBI", "option_index": 0, "is_correct": True},
            {"id": "o2", "question_id": "q1", "option_text": "SEBI", "option_index": 1, "is_correct": False},
        ],
        "mock_question_stimuli": [],
        "current_affairs_events": [{"id": "ev1", "event_date": "2026-07-09"}],
        "current_affairs_question_links": [{"mock_question_id": "q1", "claim_id": "c1"}],
        "current_affairs_claims": [{"id": "c1", "factual_status": "current", "superseded_at": None}],
        "current_affairs_claim_evidence": [
            {"claim_id": "c1", "document_id": "d1", "evidence_role": "primary"}],
        "current_affairs_documents": [
            {"id": "d1", "published_at": "2026-07-08T00:00:00Z", "final_url": "https://pib.gov.in/x"}],
    }


def test_start_freezes_gated_set_with_provenance_and_calls_rpc(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    sb = CaSB(_start_seed())
    out = attempts.start_weekly_current_affairs_attempt(sb, user_id="u1", exam_id="e1")
    assert out["outcome"] == "ready" and out["attempt_id"]
    resp = sb.db["current_affairs_attempt_responses"][0]
    snap = resp["question_snapshot"]
    # Frozen: options + correct answer (server owns the answer) + §10 provenance envelope.
    assert snap["correct_option_id"] == "o1" and len(snap["options"]) == 2
    assert snap["current_affairs"]["event_date"] == "2026-07-09"
    assert snap["current_affairs"]["source_url"] == "https://pib.gov.in/x"
    assert (sb.db["current_affairs_attempts"][0]["template_snapshot"]["practice_mode"]
            == "weekly_current_affairs")


def test_start_returns_no_bundle_when_none_published():
    sb = CaSB({"exams": [{"id": "e1", "exam_family_id": None}], "current_affairs_bundles": []})
    assert attempts.start_weekly_current_affairs_attempt(sb, user_id="u1", exam_id="e1") == {"outcome": "no_bundle"}


def test_start_returns_empty_when_no_eligible_member(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    seed = _start_seed()
    seed["mock_question_bank"][0]["valid_until"] = _PAST  # the only member expired
    out = attempts.start_weekly_current_affairs_attempt(CaSB(seed), user_id="u1", exam_id="e1")
    assert out["outcome"] == "empty_bundle"


def test_start_is_idempotent_on_reuse(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    sb = CaSB(_start_seed())
    first = attempts.start_weekly_current_affairs_attempt(sb, user_id="u1", exam_id="e1")
    again = attempts.start_weekly_current_affairs_attempt(sb, user_id="u1", exam_id="e1")
    assert again["outcome"] == "reused" and again["attempt_id"] == first["attempt_id"]
    assert len(sb.db["current_affairs_attempts"]) == 1


def _attempt_seed(status="in_progress"):
    snap = {"correct_option_id": "o1", "options": [
        {"id": "o1", "option_text": "RBI", "option_index": 0},
        {"id": "o2", "option_text": "SEBI", "option_index": 1}],
        "question_text": "Q?", "question_type": "mcq", "explanation": "RBI.",
        "current_affairs": {"event_date": "2026-07-09", "source_published_at": "2026-07-08T00:00:00Z",
                            "source_url": "https://pib.gov.in/x", "superseded": True,
                            "supersession_note": "A more recent claim may supersede this item."}}
    return {
        "current_affairs_attempts": [{
            "id": "att-1", "user_id": "u1", "status": status, "cadence": "weekly",
            "bundle_id": "b1", "total_questions": 1,
            "template_snapshot": {"question_ids": ["q1"]},
        }],
        "current_affairs_attempt_responses": [{
            "id": "r1", "attempt_id": "att-1", "mock_question_id": "q1",
            "question_snapshot": snap, "selected_option_id": None, "client_seq": 0, "is_visited": False,
        }],
    }


def test_learner_view_hides_answer_until_submitted():
    view = attempts.get_current_affairs_attempt(CaSB(_attempt_seed("in_progress")), "u1", "att-1")
    q = view["questions"][0]
    for hidden in ("correct_option_id", "explanation", "event_date", "source_url", "supersession_note"):
        assert hidden not in q
    assert [o["id"] for o in q["options"]] == ["o1", "o2"]


def test_learner_view_reveals_envelope_after_submit():
    view = attempts.get_current_affairs_attempt(CaSB(_attempt_seed("submitted")), "u1", "att-1")
    q = view["questions"][0]
    assert q["correct_option_id"] == "o1" and q["explanation"] == "RBI."
    assert q["event_date"] == "2026-07-09" and q["source_url"] == "https://pib.gov.in/x"
    assert q["superseded"] is True and q["supersession_note"]


def test_get_rejects_non_owner():
    with pytest.raises(PermissionError):
        attempts.get_current_affairs_attempt(CaSB(_attempt_seed()), "someone-else", "att-1")


def test_save_answer_updates_response_via_rpc():
    sb = CaSB(_attempt_seed())
    out = attempts.save_current_affairs_answer(
        sb, "u1", "att-1", question_id="q1", selected_option_id="o1", client_seq=1)
    assert out.get("ok")
    row = sb.db["current_affairs_attempt_responses"][0]
    assert row["selected_option_id"] == "o1" and row["is_visited"] is True


def test_save_lower_or_equal_seq_is_idempotent_no_op():
    sb = CaSB(_attempt_seed())
    attempts.save_current_affairs_answer(sb, "u1", "att-1", question_id="q1",
                                         selected_option_id="o1", client_seq=2)
    # A stale replay with an equal/lower seq must NOT overwrite the recorded answer.
    out = attempts.save_current_affairs_answer(sb, "u1", "att-1", question_id="q1",
                                               selected_option_id="o2", client_seq=2)
    assert out.get("idempotent") is True
    assert sb.db["current_affairs_attempt_responses"][0]["selected_option_id"] == "o1"


def test_save_rejects_option_not_in_question():
    with pytest.raises(ValueError):
        attempts.save_current_affairs_answer(
            CaSB(_attempt_seed()), "u1", "att-1", question_id="q1",
            selected_option_id="o-bogus", client_seq=1)


def test_save_rejects_unknown_question():
    with pytest.raises(ValueError):
        attempts.save_current_affairs_answer(
            CaSB(_attempt_seed()), "u1", "att-1", question_id="qX", selected_option_id="o1")


def test_save_rejects_when_submitted():
    with pytest.raises(ValueError):
        attempts.save_current_affairs_answer(
            CaSB(_attempt_seed("submitted")), "u1", "att-1", question_id="q1", selected_option_id="o1")


def test_save_rejects_non_owner():
    with pytest.raises(PermissionError):
        attempts.save_current_affairs_answer(
            CaSB(_attempt_seed()), "someone-else", "att-1", question_id="q1", selected_option_id="o1")


def test_submit_scores_inline():
    sb = CaSB(_attempt_seed())
    sb.db["current_affairs_attempt_responses"][0]["selected_option_id"] = "o1"
    out = attempts.submit_current_affairs_attempt(sb, "u1", "att-1")
    assert out["outcome"] == "submitted" and out["total_correct"] == 1


def test_submit_rejects_non_owner():
    with pytest.raises(PermissionError):
        attempts.submit_current_affairs_attempt(CaSB(_attempt_seed()), "someone-else", "att-1")
