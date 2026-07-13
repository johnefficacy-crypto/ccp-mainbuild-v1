"""Service-level regressions for GQR-G6 monthly hardening."""
from __future__ import annotations

import pytest

from app.current_affairs import monthly
from tests.persona_questions._stub import SBStub, _RpcCall


def test_retry_selector_is_bound_to_exact_exam():
    captured = {}

    class _SB:
        def rpc(self, name, params):
            captured["name"] = name
            captured["params"] = params
            return _RpcCall([
                {"question_id": "retry-1"},
                {"question_id": "core-1"},
            ])

    out = monthly._eligible_retry_tail_ids(
        _SB(),
        "user-1",
        exam_id="exam-1",
        exclude=["core-1"],
        cap=10,
    )

    assert out == ["retry-1"]
    assert captured == {
        "name": "ca_eligible_retry_tail",
        "params": {"p_user": "user-1", "p_exam": "exam-1"},
    }


def test_start_uses_scoped_rpc_and_passes_frozen_rows(monkeypatch):
    monkeypatch.setattr(
        monthly,
        "resolve_eligible_bundle",
        lambda _sb, *, exam_id, cadence: {
            "id": "bundle-1",
            "cadence": cadence,
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
        },
    )
    monkeypatch.setattr(monthly, "bundle_question_ids", lambda _sb, _bid: ["core-1"])
    monkeypatch.setattr(
        monthly, "eligible_bundle_question_ids", lambda _sb, _bid: ["core-1"]
    )
    monkeypatch.setattr(
        monthly,
        "_eligible_retry_tail_ids",
        lambda _sb, _uid, *, exam_id, exclude, cap: ["retry-1"],
    )
    monkeypatch.setattr(
        monthly,
        "_freeze_rows",
        lambda _sb, qids: [
            {"question_id": qid, "question_snapshot": {"options": ["x"]}}
            for qid in qids
        ],
    )
    captured = {}

    def fake_rpc(_sb, name, params):
        captured["name"] = name
        captured["params"] = params
        return {
            "outcome": "ready",
            "attempt_id": "attempt-1",
            "core_count": 1,
            "retry_tail_count": 1,
        }

    monkeypatch.setattr(monthly, "_rpc", fake_rpc)

    out = monthly.start_monthly_current_affairs_attempt(
        object(), user_id="user-1", exam_id="exam-1"
    )

    assert out["outcome"] == "ready"
    assert captured["name"] == "ca_start_monthly_current_affairs_attempt_scoped"
    assert captured["params"]["p_exam"] == "exam-1"
    assert [row["question_id"] for row in captured["params"]["p_core_rows"]] == [
        "core-1"
    ]
    assert [row["question_id"] for row in captured["params"]["p_retry_rows"]] == [
        "retry-1"
    ]


def test_monthly_report_rejects_weekly_attempt():
    sb = SBStub(
        {
            "current_affairs_attempts": [
                {
                    "id": "attempt-weekly",
                    "user_id": "user-1",
                    "cadence": "weekly",
                    "status": "submitted",
                }
            ],
            "current_affairs_attempt_responses": [],
        }
    )

    with pytest.raises(ValueError, match="not a monthly attempt"):
        monthly.monthly_consolidation_report(
            sb, "user-1", "attempt-weekly"
        )
