"""CA monthly consolidation + retry-tail runtime tests (GQR-G6).

``MonthlySB`` emulates migrations 258–260: exact-exam retry selection, scoped
monthly start, atomic weekly-mistake enqueue, and newer-source-wins re-arming.
Real PostgreSQL behaviour remains covered by the rollback-only validator.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.current_affairs import bundles, monthly
from tests.persona_questions._stub import SBStub, _RpcCall

_NOW = datetime(2026, 7, 13, tzinfo=timezone.utc)
_FUTURE = (_NOW + timedelta(days=10)).isoformat()
_PAST = (_NOW - timedelta(days=1)).isoformat()


def _bank(qid: str) -> dict:
    return {
        "id": qid,
        "question_text": f"Q {qid}?",
        "question_type": "mcq",
        "correct_option_id": f"{qid}-o1",
        "source_kind": "current_event",
        "is_current_based": True,
        "reviewer_status": "verified",
        "valid_until": _FUTURE,
        "valid_from": None,
        "difficulty": "medium",
        "explanation": f"expl {qid}",
        "current_affairs_item_id": f"ev-{qid}",
    }


def _opts(qid: str) -> list[dict]:
    return [
        {
            "id": f"{qid}-o1",
            "question_id": qid,
            "option_text": "A",
            "option_index": 0,
        },
        {
            "id": f"{qid}-o2",
            "question_id": qid,
            "option_text": "B",
            "option_index": 1,
        },
    ]


def _prov(qid: str) -> dict[str, list[dict]]:
    return {
        "current_affairs_events": [
            {
                "id": f"ev-{qid}",
                "event_date": "2026-07-09",
                "status": "active",
                "relevance_from": None,
                "relevance_until": None,
            }
        ],
        "current_affairs_question_links": [
            {
                "mock_question_id": qid,
                "claim_id": f"c-{qid}",
                "event_id": f"ev-{qid}",
            }
        ],
        "current_affairs_claims": [
            {
                "id": f"c-{qid}",
                "event_id": f"ev-{qid}",
                "reviewer_status": "verified",
                "factual_status": "current",
                "superseded_at": None,
            }
        ],
        "current_affairs_claim_evidence": [
            {
                "claim_id": f"c-{qid}",
                "document_id": f"d-{qid}",
                "evidence_role": "primary",
            }
        ],
        "current_affairs_documents": [
            {
                "id": f"d-{qid}",
                "source_id": f"s-{qid}",
                "published_at": "2026-07-08T00:00:00Z",
                "final_url": f"https://pib.gov.in/{qid}",
            }
        ],
        "current_affairs_sources": [
            {
                "id": f"s-{qid}",
                "is_active": True,
                "authority_level": "primary_official",
            }
        ],
    }


def _source_key(row: dict) -> tuple[str, str, str]:
    return (
        str(row.get("source_period_end") or ""),
        str(row.get("source_started_at") or ""),
        str(row.get("source_submitted_at") or ""),
    )


class MonthlySB(SBStub):
    def rpc(self, name, params=None):
        params = params or {}
        if name == "ca_eligible_retry_tail":
            return _RpcCall(self._eligible_tail(params))
        if name in {
            "ca_start_monthly_current_affairs_attempt",
            "ca_start_monthly_current_affairs_attempt_guarded",
            "ca_start_monthly_current_affairs_attempt_scoped",
        }:
            return _RpcCall(self._start_monthly(params))
        if name == "ca_enqueue_weekly_retry_items":
            return _RpcCall(self._enqueue(params))
        return super().rpc(name, params)

    def _eligible_tail(self, params: dict) -> list[dict]:
        rows: list[dict] = []
        for item in self.db.get("current_affairs_retry_items", []):
            if item.get("user_id") != params["p_user"]:
                continue
            if item.get("exam_id") != params.get("p_exam"):
                continue
            if item.get("status") != "pending":
                continue
            if item.get("due_at") and str(item["due_at"]) > _NOW.isoformat():
                continue
            if item.get("expires_at") and str(item["expires_at"]) <= _NOW.isoformat():
                continue
            rows.append(
                {
                    "question_id": item["question_id"],
                    "due_at": item.get("due_at"),
                    "created_at": item.get("created_at"),
                }
            )
        rows.sort(key=lambda row: (row.get("due_at") or "", row.get("created_at") or ""))
        return rows

    def _verify_snapshot(self, row: dict) -> None:
        question = next(
            (
                bank_row
                for bank_row in self.db.get("mock_question_bank", [])
                if bank_row["id"] == row["question_id"]
            ),
            None,
        )
        if question is None:
            raise RuntimeError("snapshot_text_mismatch")
        snapshot = row["question_snapshot"]
        if snapshot.get("question_text") != question.get("question_text"):
            raise RuntimeError("snapshot_text_mismatch")
        if snapshot.get("explanation") != question.get("explanation"):
            raise RuntimeError("snapshot_text_mismatch")
        if str(snapshot.get("correct_option_id")) != str(question.get("correct_option_id")):
            raise RuntimeError("snapshot_answer_mismatch")
        bank_options = {
            str(option["id"]): option.get("option_text")
            for option in self.db.get("mock_question_options", [])
            if option.get("question_id") == row["question_id"]
        }
        frozen_options = {
            str(option["id"]): option.get("option_text")
            for option in snapshot.get("options") or []
        }
        if bank_options != frozen_options:
            raise RuntimeError("snapshot_options_mismatch")

    def _start_monthly(self, params: dict) -> dict:
        import uuid

        bundle = next(
            (
                row
                for row in self.db.get("current_affairs_bundles", [])
                if row["id"] == params["p_bundle"]
            ),
            None,
        )
        if bundle is None:
            raise RuntimeError("bundle_not_found")
        if bundle.get("cadence") != "monthly":
            raise RuntimeError("not_a_monthly_bundle")

        existing = next(
            (
                row
                for row in self.db.get("current_affairs_attempts", [])
                if row.get("user_id") == params["p_user"]
                and row.get("bundle_id") == params["p_bundle"]
            ),
            None,
        )
        if existing:
            if existing.get("exam_id") != params.get("p_exam"):
                raise RuntimeError("bundle_scope_mismatch")
            if existing.get("status") == "in_progress":
                snapshot = existing.get("template_snapshot") or {}
                return {
                    "outcome": "reused",
                    "attempt_id": existing["id"],
                    "question_count": existing.get("total_questions", 0),
                    "core_count": snapshot.get("core_count", 0),
                    "retry_tail_count": snapshot.get("retry_tail_count", 0),
                }
            raise RuntimeError("attempt_already_submitted")

        core = bundles.eligible_bundle_question_ids(self, params["p_bundle"], now=_NOW)
        raw = bundles.bundle_question_ids(self, params["p_bundle"])
        if core != raw:
            raise RuntimeError("bundle_degraded")
        caller_core = [row["question_id"] for row in params.get("p_core_rows") or []]
        if caller_core != core:
            raise RuntimeError("bundle_set_mismatch")
        tail = [row["question_id"] for row in params.get("p_retry_rows") or []]
        if len(tail) > 10:
            raise RuntimeError("retry_tail_cap_exceeded")
        if len(set(tail)) != len(tail):
            raise RuntimeError("retry_tail_duplicate")

        pending = {
            item["question_id"]
            for item in self.db.get("current_affairs_retry_items", [])
            if item.get("user_id") == params["p_user"]
            and item.get("exam_id") == params.get("p_exam")
            and item.get("status") == "pending"
        }
        for qid in tail:
            if qid in core:
                raise RuntimeError("retry_tail_overlaps_core")
            if qid not in pending:
                raise RuntimeError("retry_tail_not_eligible")
        for row in (params.get("p_core_rows") or []) + (params.get("p_retry_rows") or []):
            self._verify_snapshot(row)

        attempt_id = str(uuid.uuid4())
        template = {
            **(params.get("p_template_snapshot") or {}),
            "question_ids": core + tail,
            "core_question_ids": core,
            "retry_tail_question_ids": tail,
            "total_questions": len(core) + len(tail),
            "core_count": len(core),
            "retry_tail_count": len(tail),
        }
        self.db.setdefault("current_affairs_attempts", []).append(
            {
                "id": attempt_id,
                "user_id": params["p_user"],
                "exam_id": params.get("p_exam"),
                "bundle_id": params["p_bundle"],
                "cadence": "monthly",
                "status": "in_progress",
                "total_questions": len(core) + len(tail),
                "template_snapshot": template,
            }
        )
        responses = self.db.setdefault("current_affairs_attempt_responses", [])
        for role, frozen_rows in (
            ("core", params.get("p_core_rows") or []),
            ("retry_tail", params.get("p_retry_rows") or []),
        ):
            for row in frozen_rows:
                responses.append(
                    {
                        "id": str(uuid.uuid4()),
                        "attempt_id": attempt_id,
                        "mock_question_id": row["question_id"],
                        "question_snapshot": row["question_snapshot"],
                        "item_role": role,
                    }
                )
                if role == "retry_tail":
                    for item in self.db.get("current_affairs_retry_items", []):
                        if (
                            item.get("user_id") == params["p_user"]
                            and item.get("exam_id") == params.get("p_exam")
                            and item.get("question_id") == row["question_id"]
                        ):
                            item["status"] = "consumed"
        return {
            "outcome": "ready",
            "attempt_id": attempt_id,
            "question_count": len(core) + len(tail),
            "core_count": len(core),
            "retry_tail_count": len(tail),
        }

    def _enqueue(self, params: dict) -> int:
        attempt = next(
            (
                row
                for row in self.db.get("current_affairs_attempts", [])
                if row["id"] == params["p_attempt_id"]
            ),
            None,
        )
        if attempt is None:
            raise RuntimeError("attempt_not_found")
        if str(attempt["user_id"]) != str(params["p_user"]):
            raise RuntimeError("not_attempt_owner")
        if attempt.get("status") != "submitted":
            raise RuntimeError("attempt_not_submitted")
        if attempt.get("cadence") != "weekly":
            raise RuntimeError("not_a_weekly_attempt")

        incoming = {
            "source_attempt_id": params["p_attempt_id"],
            "exam_id": attempt.get("exam_id"),
            "source_period_end": attempt.get("period_end"),
            "source_started_at": attempt.get("started_at"),
            "source_submitted_at": attempt.get("submitted_at") or attempt.get("started_at"),
            "status": "pending",
        }
        store = self.db.setdefault("current_affairs_retry_items", [])
        count = 0
        for response in self.db.get("current_affairs_attempt_responses", []):
            if response.get("attempt_id") != params["p_attempt_id"]:
                continue
            if response.get("selected_option_id") is None or response.get("is_correct"):
                continue
            qid = response["mock_question_id"]
            existing = next(
                (
                    item
                    for item in store
                    if item.get("user_id") == params["p_user"]
                    and item.get("question_id") == qid
                ),
                None,
            )
            if existing and existing.get("source_attempt_id") == params["p_attempt_id"]:
                continue
            if existing and _source_key(existing) >= _source_key(incoming):
                continue
            if existing:
                existing.update(incoming)
            else:
                store.append(
                    {
                        "user_id": params["p_user"],
                        "question_id": qid,
                        **incoming,
                    }
                )
            count += 1
        return count


def _monthly_seed(
    core_ids: tuple[str, ...] = ("q1",),
    tail_items: tuple[tuple[str, str, str | None], ...] = (("qt1", "u1", "e1"),),
) -> dict:
    db: dict = {
        "exams": [{"id": "e1", "exam_family_id": None}],
        "current_affairs_bundles": [
            {
                "id": "b-m",
                "cadence": "monthly",
                "status": "published",
                "reviewer_status": "verified",
                "exam_id": None,
                "exam_family_id": None,
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "available_until": _FUTURE,
                "publish_at": _PAST,
            }
        ],
        "current_affairs_bundle_questions": [
            {"bundle_id": "b-m", "mock_question_id": qid, "display_order": index}
            for index, qid in enumerate(core_ids)
        ],
        "mock_question_bank": [],
        "mock_question_options": [],
        "mock_question_stimuli": [],
        "current_affairs_retry_items": [],
    }
    all_question_ids = list(core_ids) + [qid for qid, _, _ in tail_items]
    for qid in all_question_ids:
        db["mock_question_bank"].append(_bank(qid))
        db["mock_question_options"].extend(_opts(qid))
        for table, rows in _prov(qid).items():
            db.setdefault(table, []).extend(rows)
    for qid, user_id, exam_id in tail_items:
        db["current_affairs_retry_items"].append(
            {
                "id": f"ri-{qid}",
                "user_id": user_id,
                "exam_id": exam_id,
                "question_id": qid,
                "status": "pending",
                "due_at": _PAST,
                "expires_at": _FUTURE,
                "created_at": _PAST,
            }
        )
    return db


def test_start_monthly_freezes_core_and_capped_tail(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    sb = MonthlySB(_monthly_seed())
    result = monthly.start_monthly_current_affairs_attempt(
        sb, user_id="u1", exam_id="e1"
    )
    assert result["outcome"] == "ready"
    assert result["core_count"] == 1 and result["retry_tail_count"] == 1
    assert sorted(row["item_role"] for row in sb.db["current_affairs_attempt_responses"]) == [
        "core",
        "retry_tail",
    ]
    assert sb.db["current_affairs_retry_items"][0]["status"] == "consumed"


def test_concurrent_style_retry_reuses_after_tail_consumed(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    sb = MonthlySB(_monthly_seed())
    first = monthly.start_monthly_current_affairs_attempt(
        sb, user_id="u1", exam_id="e1"
    )
    second = monthly.start_monthly_current_affairs_attempt(
        sb, user_id="u1", exam_id="e1"
    )
    assert second["outcome"] == "reused"
    assert second["attempt_id"] == first["attempt_id"]
    assert second["retry_tail_count"] == 1
    assert len(sb.db["current_affairs_attempts"]) == 1


def test_start_monthly_no_bundle():
    sb = MonthlySB(
        {"exams": [{"id": "e1", "exam_family_id": None}], "current_affairs_bundles": []}
    )
    assert monthly.start_monthly_current_affairs_attempt(
        sb, user_id="u1", exam_id="e1"
    ) == {"outcome": "no_bundle"}


def test_start_monthly_with_no_retry_items_is_core_only(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    sb = MonthlySB(_monthly_seed(tail_items=()))
    result = monthly.start_monthly_current_affairs_attempt(
        sb, user_id="u1", exam_id="e1"
    )
    assert result["core_count"] == 1 and result["retry_tail_count"] == 0


def test_tail_is_capped_at_ten(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    tail = tuple((f"qt{index}", "u1", "e1") for index in range(15))
    result = monthly.start_monthly_current_affairs_attempt(
        MonthlySB(_monthly_seed(tail_items=tail)), user_id="u1", exam_id="e1"
    )
    assert result["retry_tail_count"] == 10


def test_tail_excludes_core_and_other_exam(monkeypatch):
    monkeypatch.setattr(bundles, "_now", lambda: _NOW)
    sb = MonthlySB(
        _monthly_seed(
            core_ids=("q1",),
            tail_items=(("q1", "u1", "e1"), ("other", "u1", "e2")),
        )
    )
    result = monthly.start_monthly_current_affairs_attempt(
        sb, user_id="u1", exam_id="e1"
    )
    assert result["retry_tail_count"] == 0


def _weekly_db(attempts: list[dict], source_attempt_id: str | None = None) -> dict:
    db = {
        "current_affairs_attempts": attempts,
        "current_affairs_attempt_responses": [
            {
                "attempt_id": attempts[-1]["id"],
                "mock_question_id": "m1",
                "selected_option_id": "wrong",
                "is_correct": False,
            }
        ],
        "current_affairs_retry_items": [],
    }
    if source_attempt_id:
        db["current_affairs_retry_items"].append(
            {
                "user_id": "u1",
                "question_id": "m1",
                "status": "consumed",
                "source_attempt_id": source_attempt_id,
                "source_period_end": "2026-06-30",
                "source_started_at": "2026-06-30T00:00:00+00:00",
                "source_submitted_at": "2026-06-30T01:00:00+00:00",
            }
        )
    return db


def test_enqueue_same_attempt_is_idempotent():
    attempt = {
        "id": "wk-1",
        "user_id": "u1",
        "exam_id": "e1",
        "status": "submitted",
        "cadence": "weekly",
        "period_end": "2026-07-06",
        "started_at": "2026-07-06T00:00:00+00:00",
        "submitted_at": "2026-07-06T01:00:00+00:00",
    }
    sb = MonthlySB(_weekly_db([attempt]))
    assert monthly.enqueue_weekly_retry_items(sb, "u1", "wk-1")["enqueued"] == 1
    assert monthly.enqueue_weekly_retry_items(sb, "u1", "wk-1")["enqueued"] == 0


def test_newer_weekly_mistake_rearms_consumed_item():
    newer = {
        "id": "wk-new",
        "user_id": "u1",
        "exam_id": "e1",
        "status": "submitted",
        "cadence": "weekly",
        "period_end": "2026-07-06",
        "started_at": "2026-07-06T00:00:00+00:00",
        "submitted_at": "2026-07-06T01:00:00+00:00",
    }
    sb = MonthlySB(_weekly_db([newer], source_attempt_id="wk-old"))
    assert monthly.enqueue_weekly_retry_items(sb, "u1", "wk-new")["enqueued"] == 1
    item = sb.db["current_affairs_retry_items"][0]
    assert item["status"] == "pending"
    assert item["source_attempt_id"] == "wk-new"
    assert item["exam_id"] == "e1"


def test_older_delayed_weekly_replay_cannot_overwrite_newer_item():
    older = {
        "id": "wk-old",
        "user_id": "u1",
        "exam_id": "e1",
        "status": "submitted",
        "cadence": "weekly",
        "period_end": "2026-06-23",
        "started_at": "2026-06-23T00:00:00+00:00",
        "submitted_at": "2026-06-23T01:00:00+00:00",
    }
    db = _weekly_db([older])
    db["current_affairs_retry_items"] = [
        {
            "user_id": "u1",
            "question_id": "m1",
            "status": "pending",
            "source_attempt_id": "wk-new",
            "source_period_end": "2026-07-06",
            "source_started_at": "2026-07-06T00:00:00+00:00",
            "source_submitted_at": "2026-07-06T01:00:00+00:00",
        }
    ]
    sb = MonthlySB(db)
    assert monthly.enqueue_weekly_retry_items(sb, "u1", "wk-old")["enqueued"] == 0
    assert sb.db["current_affairs_retry_items"][0]["source_attempt_id"] == "wk-new"


def test_monthly_report_splits_core_and_tail():
    db = {
        "current_affairs_attempts": [
            {
                "id": "att-m",
                "user_id": "u1",
                "cadence": "monthly",
                "status": "submitted",
                "score_raw": 2,
            }
        ],
        "current_affairs_attempt_responses": [
            {"attempt_id": "att-m", "item_role": "core", "is_correct": True, "selected_option_id": "a"},
            {"attempt_id": "att-m", "item_role": "core", "is_correct": False, "selected_option_id": "b"},
            {"attempt_id": "att-m", "item_role": "retry_tail", "is_correct": True, "selected_option_id": "c"},
            {"attempt_id": "att-m", "item_role": "retry_tail", "is_correct": None, "selected_option_id": None},
        ],
    }
    report = monthly.monthly_consolidation_report(MonthlySB(db), "u1", "att-m")
    assert report["core"] == {"total": 2, "attempted": 2, "correct": 1}
    assert report["retry_tail"] == {"total": 2, "attempted": 1, "correct": 1}


def test_monthly_report_rejects_non_owner_and_weekly_attempt():
    with pytest.raises(PermissionError):
        monthly.monthly_consolidation_report(
            MonthlySB(
                {
                    "current_affairs_attempts": [
                        {"id": "att-m", "user_id": "owner", "cadence": "monthly"}
                    ],
                    "current_affairs_attempt_responses": [],
                }
            ),
            "intruder",
            "att-m",
        )
    with pytest.raises(ValueError, match="not a monthly attempt"):
        monthly.monthly_consolidation_report(
            MonthlySB(
                {
                    "current_affairs_attempts": [
                        {"id": "att-w", "user_id": "u1", "cadence": "weekly"}
                    ],
                    "current_affairs_attempt_responses": [],
                }
            ),
            "u1",
            "att-w",
        )
