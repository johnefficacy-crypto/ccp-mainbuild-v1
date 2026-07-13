"""CA monthly consolidation + retry-tail runtime tests (GQR-G6).

``MonthlySB`` emulates the migration-257 RPCs (eligible-tail selector, monthly core+tail
start, weekly-mistake enqueue) against the in-memory store so the service layer is exercised
end-to-end. Real Postgres behaviour is VERIFY DB (validate_ca_monthly_retry.sql).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.current_affairs import bundles, monthly
from tests.persona_questions._stub import SBStub, _RpcCall

_NOW = datetime(2026, 7, 13, tzinfo=timezone.utc)
_FUTURE = (_NOW + timedelta(days=10)).isoformat()
_PAST = (_NOW - timedelta(days=1)).isoformat()


def _bank(qid):
    return {"id": qid, "question_text": f"Q {qid}?", "question_type": "mcq",
            "correct_option_id": f"{qid}-o1", "source_kind": "current_event", "is_current_based": True,
            "reviewer_status": "verified", "valid_until": _FUTURE, "valid_from": None,
            "difficulty": "medium", "explanation": f"expl {qid}", "current_affairs_item_id": f"ev-{qid}"}


def _opts(qid):
    return [{"id": f"{qid}-o1", "question_id": qid, "option_text": "A", "option_index": 0},
            {"id": f"{qid}-o2", "question_id": qid, "option_text": "B", "option_index": 1}]


def _prov(qid):
    return {
        "current_affairs_events": [{"id": f"ev-{qid}", "event_date": "2026-07-09",
                                    "status": "active", "relevance_until": None}],
        "current_affairs_question_links": [{"mock_question_id": qid, "claim_id": f"c-{qid}", "event_id": f"ev-{qid}"}],
        "current_affairs_claims": [{"id": f"c-{qid}", "event_id": f"ev-{qid}",
                                    "reviewer_status": "verified", "factual_status": "current", "superseded_at": None}],
        "current_affairs_claim_evidence": [{"claim_id": f"c-{qid}", "document_id": f"d-{qid}", "evidence_role": "primary"}],
        "current_affairs_documents": [{"id": f"d-{qid}", "source_id": f"s-{qid}",
                                       "published_at": "2026-07-08T00:00:00Z", "final_url": f"https://pib.gov.in/{qid}"}],
        "current_affairs_sources": [{"id": f"s-{qid}", "is_active": True, "authority_level": "primary_official"}],
    }


class MonthlySB(SBStub):
    def rpc(self, name, params=None):
        params = params or {}
        if name == "ca_eligible_retry_tail":
            return _RpcCall(self._eligible_tail(params))
        if name == "ca_start_monthly_current_affairs_attempt":
            return _RpcCall(self._start_monthly(params))
        if name == "ca_enqueue_weekly_retry_items":
            return _RpcCall(self._enqueue(params))
        return super().rpc(name, params)

    def _eligible_tail(self, p):
        out = []
        for ri in self.db.get("current_affairs_retry_items", []):
            if ri.get("user_id") != p["p_user"] or ri.get("status") != "pending":
                continue
            if ri.get("expires_at") and str(ri["expires_at"]) <= _NOW.isoformat():
                continue
            out.append({"question_id": ri["question_id"], "due_at": ri.get("due_at"),
                        "created_at": ri.get("created_at")})
        return out

    def _verify_snapshot(self, row):
        q = next((b for b in self.db.get("mock_question_bank", []) if b["id"] == row["question_id"]), None)
        snap = row["question_snapshot"]
        if str(snap.get("question_text")) != str(q.get("question_text")) \
                or str(snap.get("explanation")) != str(q.get("explanation")):
            raise RuntimeError("snapshot_text_mismatch")
        if str(snap.get("correct_option_id")) != str(q.get("correct_option_id")):
            raise RuntimeError("snapshot_answer_mismatch")
        bank_opts = {str(o["id"]): o.get("option_text") for o in self.db.get("mock_question_options", [])
                     if o.get("question_id") == row["question_id"]}
        snap_opts = {str(o["id"]): o.get("option_text") for o in (snap.get("options") or [])}
        if bank_opts != snap_opts:
            raise RuntimeError("snapshot_options_mismatch")

    def _start_monthly(self, p):
        import uuid as _uuid
        bundle = next((b for b in self.db.get("current_affairs_bundles", []) if b["id"] == p["p_bundle"]), None)
        if bundle is None:
            raise RuntimeError("bundle_not_found")
        if bundle.get("cadence") != "monthly":
            raise RuntimeError("not_a_monthly_bundle")
        core = bundles.eligible_bundle_question_ids(self, p["p_bundle"], now=_NOW)
        raw = bundles.bundle_question_ids(self, p["p_bundle"])
        if core != raw:
            raise RuntimeError("bundle_degraded")
        core_caller = [r["question_id"] for r in (p.get("p_core_rows") or [])]
        if core_caller != core:
            raise RuntimeError("bundle_set_mismatch")
        tail = [r["question_id"] for r in (p.get("p_retry_rows") or [])]
        if len(tail) > 10:
            raise RuntimeError("retry_tail_cap_exceeded")
        if len(set(tail)) != len(tail):
            raise RuntimeError("retry_tail_duplicate")
        pending = {ri["question_id"] for ri in self.db.get("current_affairs_retry_items", [])
                   if ri.get("user_id") == p["p_user"] and ri.get("status") == "pending"}
        for qid in tail:
            if qid in core:
                raise RuntimeError("retry_tail_overlaps_core")
            if qid not in pending:
                raise RuntimeError("retry_tail_not_eligible")
        for r in (p.get("p_core_rows") or []) + (p.get("p_retry_rows") or []):
            self._verify_snapshot(r)
        aid = str(_uuid.uuid4())
        self.db.setdefault("current_affairs_attempts", []).append({
            "id": aid, "user_id": p["p_user"], "bundle_id": p["p_bundle"], "cadence": "monthly",
            "status": "in_progress", "total_questions": len(core) + len(tail),
            "template_snapshot": p.get("p_template_snapshot") or {}})
        resp = self.db.setdefault("current_affairs_attempt_responses", [])
        for r in (p.get("p_core_rows") or []):
            resp.append({"id": str(_uuid.uuid4()), "attempt_id": aid, "mock_question_id": r["question_id"],
                         "question_snapshot": r["question_snapshot"], "item_role": "core"})
        for r in (p.get("p_retry_rows") or []):
            resp.append({"id": str(_uuid.uuid4()), "attempt_id": aid, "mock_question_id": r["question_id"],
                         "question_snapshot": r["question_snapshot"], "item_role": "retry_tail"})
            for ri in self.db.get("current_affairs_retry_items", []):
                if ri["question_id"] == r["question_id"] and ri.get("user_id") == p["p_user"]:
                    ri["status"] = "consumed"
        return {"outcome": "ready", "attempt_id": aid, "question_count": len(core) + len(tail),
                "core_count": len(core), "retry_tail_count": len(tail)}

    def _enqueue(self, p):
        att = next((a for a in self.db.get("current_affairs_attempts", []) if a["id"] == p["p_attempt_id"]), None)
        if att is None:
            raise RuntimeError("attempt_not_found")
        if str(att["user_id"]) != str(p["p_user"]):
            raise RuntimeError("not_attempt_owner")
        if att.get("status") != "submitted":
            raise RuntimeError("attempt_not_submitted")
        if att.get("cadence") != "weekly":
            raise RuntimeError("not_a_weekly_attempt")
        store = self.db.setdefault("current_affairs_retry_items", [])
        have = {ri["question_id"] for ri in store if ri.get("user_id") == p["p_user"]}
        n = 0
        for r in self.db.get("current_affairs_attempt_responses", []):
            if r.get("attempt_id") != p["p_attempt_id"]:
                continue
            if r.get("selected_option_id") is None or r.get("is_correct"):
                continue
            qid = r["mock_question_id"]
            if qid in have:
                continue
            store.append({"user_id": p["p_user"], "question_id": qid, "status": "pending",
                          "source_attempt_id": p["p_attempt_id"]})
            have.add(qid)
            n += 1
        return n


def _monthly_seed(core_ids=("q1",), tail_items=(("qt1", "u1"),)):
    db: dict = {
        "exams": [{"id": "e1", "exam_family_id": None}],
        "current_affairs_bundles": [{
            "id": "b-m", "cadence": "monthly", "status": "published", "reviewer_status": "verified",
            "exam_id": None, "exam_family_id": None, "period_start": "2026-06-01", "period_end": "2026-06-30",
            "available_until": _FUTURE, "publish_at": _PAST}],
        "current_affairs_bundle_questions": [
            {"bundle_id": "b-m", "mock_question_id": q, "display_order": i} for i, q in enumerate(core_ids)],
        "mock_question_bank": [], "mock_question_options": [], "mock_question_stimuli": [],
        "current_affairs_retry_items": [],
    }
    all_qs = list(core_ids) + [q for q, _ in tail_items]
    for q in all_qs:
        db["mock_question_bank"].append(_bank(q))
        db["mock_question_options"].extend(_opts(q))
        for tbl, rows in _prov(q).items():
            db.setdefault(tbl, []).extend(rows)
    for q, u in tail_items:
        db["current_affairs_retry_items"].append(
            {"id": f"ri-{q}", "user_id": u, "question_id": q, "status": "pending",
             "due_at": _PAST, "expires_at": _FUTURE, "created_at": _PAST})
    return db


def test_start_monthly_freezes_core_and_capped_tail(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    sb = MonthlySB(_monthly_seed())
    out = monthly.start_monthly_current_affairs_attempt(sb, user_id="u1", exam_id="e1")
    assert out["outcome"] == "ready" and out["core_count"] == 1 and out["retry_tail_count"] == 1
    roles = sorted(r["item_role"] for r in sb.db["current_affairs_attempt_responses"])
    assert roles == ["core", "retry_tail"]
    # the consumed retry item flips to consumed (never deleted).
    assert sb.db["current_affairs_retry_items"][0]["status"] == "consumed"
    assert (sb.db["current_affairs_attempts"][0]["template_snapshot"]["practice_mode"]
            == "monthly_current_affairs")


def test_start_monthly_no_bundle():
    sb = MonthlySB({"exams": [{"id": "e1", "exam_family_id": None}], "current_affairs_bundles": []})
    assert monthly.start_monthly_current_affairs_attempt(sb, user_id="u1", exam_id="e1") == {"outcome": "no_bundle"}


def test_start_monthly_with_no_retry_items_is_core_only(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    sb = MonthlySB(_monthly_seed(tail_items=()))
    out = monthly.start_monthly_current_affairs_attempt(sb, user_id="u1", exam_id="e1")
    assert out["core_count"] == 1 and out["retry_tail_count"] == 0


def test_tail_is_capped_at_ten(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    tail = tuple((f"qt{i}", "u1") for i in range(15))  # 15 eligible → capped to 10
    sb = MonthlySB(_monthly_seed(tail_items=tail))
    out = monthly.start_monthly_current_affairs_attempt(sb, user_id="u1", exam_id="e1")
    assert out["retry_tail_count"] == 10


def test_tail_excludes_a_question_already_in_core(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    # q1 is both a core member AND a retry item for the learner → must not double-appear.
    sb = MonthlySB(_monthly_seed(core_ids=("q1",), tail_items=(("q1", "u1"),)))
    out = monthly.start_monthly_current_affairs_attempt(sb, user_id="u1", exam_id="e1")
    assert out["core_count"] == 1 and out["retry_tail_count"] == 0


def test_enqueue_weekly_mistakes():
    db = {
        "current_affairs_attempts": [{"id": "wk-1", "user_id": "u1", "status": "submitted", "cadence": "weekly"}],
        "current_affairs_attempt_responses": [
            {"attempt_id": "wk-1", "mock_question_id": "m1", "selected_option_id": "x", "is_correct": False},
            {"attempt_id": "wk-1", "mock_question_id": "m2", "selected_option_id": "y", "is_correct": False},
            {"attempt_id": "wk-1", "mock_question_id": "m3", "selected_option_id": "z", "is_correct": True},
            {"attempt_id": "wk-1", "mock_question_id": "m4", "selected_option_id": None, "is_correct": None},
        ],
        "current_affairs_retry_items": [],
    }
    sb = MonthlySB(db)
    out = monthly.enqueue_weekly_retry_items(sb, "u1", "wk-1")
    assert out["enqueued"] == 2  # only the two answered-wrong questions
    assert sorted(ri["question_id"] for ri in sb.db["current_affairs_retry_items"]) == ["m1", "m2"]


def test_monthly_report_splits_core_and_tail():
    db = {
        "current_affairs_attempts": [{"id": "att-m", "user_id": "u1", "cadence": "monthly",
                                      "status": "submitted", "score_raw": 2}],
        "current_affairs_attempt_responses": [
            {"attempt_id": "att-m", "item_role": "core", "is_correct": True, "selected_option_id": "a"},
            {"attempt_id": "att-m", "item_role": "core", "is_correct": False, "selected_option_id": "b"},
            {"attempt_id": "att-m", "item_role": "retry_tail", "is_correct": True, "selected_option_id": "c"},
            {"attempt_id": "att-m", "item_role": "retry_tail", "is_correct": None, "selected_option_id": None},
        ],
    }
    rep = monthly.monthly_consolidation_report(MonthlySB(db), "u1", "att-m")
    assert rep["core"] == {"total": 2, "attempted": 2, "correct": 1}
    assert rep["retry_tail"] == {"total": 2, "attempted": 1, "correct": 1}


def test_monthly_report_rejects_non_owner():
    db = {"current_affairs_attempts": [{"id": "att-m", "user_id": "owner", "cadence": "monthly"}],
          "current_affairs_attempt_responses": []}
    with pytest.raises(PermissionError):
        monthly.monthly_consolidation_report(MonthlySB(db), "intruder", "att-m")
