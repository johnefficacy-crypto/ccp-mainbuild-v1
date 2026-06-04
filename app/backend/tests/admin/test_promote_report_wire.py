"""Tests: promote_report() wires gate-PASS to promote_to_recruitments().

Concern 1 of fix/gateway-promote-wire.

Written BEFORE implementation — all three behavioural tests must fail
until the wire is added to admin_verification_reports.promote_report().
"""
from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.admin_verification_reports import PromoteRequest, promote_report
from app.core.errors import PromotionError

# ── fixtures ─────────────────────────────────────────────────────────

ADMIN = {"id": "admin-1", "role": "admin"}
REPORT_ID = "rpt-001"
QUEUE_ID = "q-001"
REC_ID = "rec-001"


def _base_report(**overrides):
    return {
        "id": REPORT_ID,
        "scrape_queue_id": QUEUE_ID,
        "recommended_action": "request_admin_review",
        "recruitment_id": None,
        "criticality_tier": "C_STANDARD_LONG_TAIL",
        "lifecycle_status": "reviewed",
        "risk_flags": [],
        "conflicts": [],
        "official_resolution_status": "resolved_verified",
        **overrides,
    }


def _effective_data():
    return {
        "title": "Senior Dev",
        "organization_name": "UPSC",
        "org_type": "central_govt",
        "year": 2025,
        "official_notification_url": "https://upsc.gov.in/notif",
        "apply_end_date": "2025-12-31",
        "posts": [{"post_name": "Engineer"}],
    }


class _FakeTable:
    def __init__(self, sb, name):
        self._sb = sb
        self._name = name
        self._filters: dict = {}
        self._mode = "select"
        self._payload: dict | None = None

    def select(self, *_):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def limit(self, _):
        return self

    def update(self, payload):
        self._mode = "update"
        self._payload = dict(payload)
        return self

    def execute(self):
        if self._name == "recruitment_verification_reports":
            pool = self._sb._reports
        elif self._name == "scrape_queue":
            pool = self._sb._queue
        else:
            pool = []

        if self._mode == "select":
            rows = [r for r in pool if all(r.get(k) == v for k, v in self._filters.items())]
            return _R(rows)

        # update
        updated = []
        for r in pool:
            if all(r.get(k) == v for k, v in self._filters.items()):
                r.update(self._payload or {})
                self._sb._update_log.append(
                    {"table": self._name, "payload": deepcopy(self._payload), "filters": deepcopy(self._filters)}
                )
                updated.append(deepcopy(r))
        return _R(updated)


class _R:
    def __init__(self, data):
        self.data = data


class _FakeSB:
    def __init__(self, reports=(), queue_rows=()):
        self._reports: list[dict] = [deepcopy(r) for r in reports]
        self._queue: list[dict] = list(queue_rows)
        self._update_log: list[dict] = []

    def table(self, name):
        return _FakeTable(self, name)


def _make_sb(report=None, source_id="src-1"):
    r = report or _base_report()
    return _FakeSB(
        reports=[r],
        queue_rows=[{"id": QUEUE_ID, "source_id": source_id}],
    )


# ── tests ─────────────────────────────────────────────────────────────


class TestPromoteReportWire:

    @patch("app.api.admin_verification_reports.get_supabase_admin")
    @patch("app.api.admin_verification_reports.build_effective_extracted_data")
    @patch("app.api.admin_verification_reports.promote_to_recruitments")
    def test_gate_pass_calls_promote_and_sets_recruitment_id(
        self, mock_promote, mock_build, mock_sb_factory
    ):
        """Gate PASS → promote_to_recruitments() called; report gets recruitment_id."""
        sb = _make_sb()
        mock_sb_factory.return_value = sb
        mock_build.return_value = _effective_data()
        mock_promote.return_value = REC_ID

        result = promote_report(
            report_id=REPORT_ID,
            payload=PromoteRequest(),
            admin=ADMIN,
        )

        # promote_to_recruitments must have been called once
        mock_promote.assert_called_once()

        # First positional arg should be a VerifiedRecruitmentForPromotion with correct data
        promo_obj = mock_promote.call_args.args[0]
        assert promo_obj.title == "Senior Dev"
        assert promo_obj.year == 2025
        assert len(promo_obj.posts) == 1

        # queue_id passed as kwarg
        assert mock_promote.call_args.kwargs.get("queue_id") == QUEUE_ID

        # Report row must have recruitment_id set to the returned rec_id
        assert sb._reports[0]["recruitment_id"] == REC_ID

    @patch("app.api.admin_verification_reports.get_supabase_admin")
    def test_gate_blocked_does_not_call_promote(self, mock_sb_factory):
        """Gate BLOCKED → 409 raised; promote_to_recruitments() never invoked."""
        # Tier A + unresolved official proof → gate blocks
        report = _base_report(
            criticality_tier="A_HIGH_STAKES",
            official_resolution_status="unresolved",
        )
        sb = _FakeSB(reports=[report])
        mock_sb_factory.return_value = sb

        with pytest.raises(HTTPException) as exc_info:
            promote_report(
                report_id=REPORT_ID,
                payload=PromoteRequest(),
                admin=ADMIN,
            )

        assert exc_info.value.status_code == 409
        # No update touched the report (gate fired before any mutation)
        assert not sb._update_log

    @patch("app.api.admin_verification_reports.get_supabase_admin")
    @patch("app.api.admin_verification_reports.build_effective_extracted_data")
    @patch("app.api.admin_verification_reports.promote_to_recruitments")
    def test_promotion_error_surfaces_cleanly_no_partial_state(
        self, mock_promote, mock_build, mock_sb_factory
    ):
        """PromotionError → 409; no partial state written to report."""
        sb = _make_sb()
        mock_sb_factory.return_value = sb
        mock_build.return_value = _effective_data()
        mock_promote.side_effect = PromotionError("duplicate")

        with pytest.raises(HTTPException) as exc_info:
            promote_report(
                report_id=REPORT_ID,
                payload=PromoteRequest(),
                admin=ADMIN,
            )

        assert exc_info.value.status_code == 409
        # recruitment_id must still be None — no partial write
        assert sb._reports[0].get("recruitment_id") is None
        # No update at all was committed for the recruitment_id field
        for entry in sb._update_log:
            assert "recruitment_id" not in entry["payload"]

    @patch("app.api.admin_verification_reports.get_supabase_admin")
    def test_no_queue_item_is_blocked(self, mock_sb_factory):
        """Report with scrape_queue_id=None → 409 no_queue_item before any promote."""
        report = _base_report(scrape_queue_id=None)
        sb = _FakeSB(reports=[report])
        mock_sb_factory.return_value = sb

        with pytest.raises(HTTPException) as exc_info:
            promote_report(
                report_id=REPORT_ID,
                payload=PromoteRequest(),
                admin=ADMIN,
            )

        assert exc_info.value.status_code == 409
        detail = exc_info.value.detail
        assert detail["reason_code"] == "no_queue_item"
        assert not sb._update_log
