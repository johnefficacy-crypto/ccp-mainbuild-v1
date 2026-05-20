"""P0/P1 scraper hardening (confidence gate, auto-disable breaker, central
sanitization, model budget/timeout, single-PATCH invariant, run severity,
recruitment_events dedup).

Run-level tests drive ``run_scraping_pass`` through the ``RunnerSB`` stub and
monkeypatch ``extract_recruitment_data`` so confidence/quantity are
deterministic.
"""
from __future__ import annotations

import logging

import httpx
import pytest

import anthropic

from app.scraping import extractor as ex
from app.scraping import runner as runner_mod
from app.scraping.normalizer import (
    NormalizedRecruitment,
    sanitize_json,
    sanitize_text,
)
from app.scraping.runner import run_scraping_pass
from app.scraping.schemas import ExtractedRecruitment
from tests.test_scrape_runner_promote import RunnerSB


def setup_function(_fn):
    runner_mod._low_confidence_strikes.clear()


def _extraction(confidence, *, mock_flag=True):
    """A constant extraction fake with a valid canonical key."""

    def _fake(raw, url, name, *, mock=None, metrics=None):
        return {
            "data": ExtractedRecruitment(
                title="Combined Graduate Exam", organization_name="Test Org", year=2026
            ),
            "confidence": confidence,
            "is_mock": mock_flag,
            "provider": "mock" if mock_flag else "anthropic",
        }

    return _fake


def _direct_source(**over):
    src = {
        "id": "s-direct",
        "source_name": "Direct Official",
        "source_type": "official_html",
        "official_url": "https://x.gov.in/notice",
        "is_active": True,
        # avoid the resolved-without-host gate flipping extraction_status
        "requires_official_confirmation": True,
    }
    src.update(over)
    return src


def _high_quality(monkeypatch):
    """Force normalize_recruitment to a high score so extraction_status is
    driven only by the signal under test."""
    monkeypatch.setattr(
        runner_mod,
        "normalize_recruitment",
        lambda data: NormalizedRecruitment(
            normalized_fields={}, data_quality_score=0.9, warnings=[]
        ),
    )


# ════════════════════════════════════════════════════════════════════════
#  Task 1 — confidence gate is at-or-below (``<=``), boundary at 0.20
# ════════════════════════════════════════════════════════════════════════


def _run_direct_with_confidence(monkeypatch, confidence, *, mock=True):
    monkeypatch.delenv("MIN_CONFIDENCE_TO_QUEUE", raising=False)
    monkeypatch.setattr(runner_mod, "extract_recruitment_data", _extraction(confidence, mock_flag=mock))
    if not mock:
        monkeypatch.setattr(runner_mod, "fetch_page_text", lambda url: "BODY TEXT")
    sb = RunnerSB()
    sb.db["source_registry"] = [_direct_source()]
    run_scraping_pass(sb, source_ids=["s-direct"], mock=mock)
    return sb


@pytest.mark.parametrize("confidence,queued", [(0.19, False), (0.20, False), (0.21, True), (1.00, True)])
def test_confidence_gate_boundary(monkeypatch, confidence, queued):
    sb = _run_direct_with_confidence(monkeypatch, confidence)
    rows = sb.db.get("scrape_queue", [])
    assert bool(rows) is queued, f"confidence={confidence} expected queued={queued}"


def test_confidence_exactly_threshold_is_diverted_not_queued(monkeypatch):
    # The off-by-one this PR fixes: 0.20 used to slip through.
    sb = _run_direct_with_confidence(monkeypatch, 0.20)
    assert sb.db.get("scrape_queue", []) == []


# ════════════════════════════════════════════════════════════════════════
#  Task 3 — auto-disable breaks the in-run loop
# ════════════════════════════════════════════════════════════════════════


def test_auto_disable_halts_remaining_detail_urls(monkeypatch):
    monkeypatch.setenv("LOW_CONFIDENCE_STRIKE_LIMIT", "2")
    calls: list[str] = []

    def _fake(raw, url, name, *, mock=None, metrics=None):
        calls.append(url)
        return {
            "data": ExtractedRecruitment(title="t", organization_name="o", year=2026),
            "confidence": 0.05,
            "is_mock": True,
            "provider": "mock",
        }

    monkeypatch.setattr(runner_mod, "extract_recruitment_data", _fake)
    sb = RunnerSB()  # aggregator src-1 → 3 mock detail URLs
    out = run_scraping_pass(sb, source_ids=["src-1"], mock=True)

    # 2 strikes disables on the 2nd URL; the 3rd is skipped entirely.
    assert len(calls) == 2
    assert sb.db.get("scrape_queue", []) == []  # low-confidence never queues
    disables = [u for u in sb.db.get("source_registry_updates", []) if u.get("is_active") is False]
    assert len(disables) == 1
    assert out["status"] == "degraded"  # a mid-run disable is a hard signal


def test_disable_of_one_source_does_not_skip_another(monkeypatch):
    monkeypatch.setenv("LOW_CONFIDENCE_STRIKE_LIMIT", "2")
    calls: list[str] = []

    def _fake(raw, url, name, *, mock=None, metrics=None):
        calls.append(url)
        return {
            "data": ExtractedRecruitment(title="t", organization_name="o", year=2026),
            "confidence": 0.05,
            "is_mock": True,
            "provider": "mock",
        }

    monkeypatch.setattr(runner_mod, "extract_recruitment_data", _fake)
    sb = RunnerSB()
    sb.db["source_registry"] = [
        {"id": "src-A", "source_name": "Agg A", "source_type": "aggregator",
         "official_url": "https://a.example.com/jobs/", "is_active": True,
         "requires_official_confirmation": True},
        {"id": "src-B", "source_name": "Agg B", "source_type": "aggregator",
         "official_url": "https://b.example.com/jobs/", "is_active": True,
         "requires_official_confirmation": True},
    ]
    run_scraping_pass(sb, source_ids=["src-A", "src-B"], mock=True)
    # Each source independently gets 2 extractions before its own disable —
    # B was processed (not skipped) despite A being disabled first.
    assert len(calls) == 4
    a_calls = [c for c in calls if "a.example.com" in c]
    b_calls = [c for c in calls if "b.example.com" in c]
    assert len(a_calls) == 2 and len(b_calls) == 2


# ════════════════════════════════════════════════════════════════════════
#  Task 4 — central control-char / NUL sanitization
# ════════════════════════════════════════════════════════════════════════


def test_sanitize_text_drops_nul():
    assert sanitize_text("hello\x00world") == "helloworld"


def test_sanitize_text_keeps_tab_newline_cr():
    assert sanitize_text("ok\tline\n") == "ok\tline\n"
    assert sanitize_text("a\rb") == "a\rb"


def test_sanitize_text_drops_other_c0_controls():
    assert sanitize_text("a\x01\x02\x08\x1fb") == "ab"


def test_sanitize_text_none_and_empty():
    assert sanitize_text(None) == ""
    assert sanitize_text("") == ""


def test_sanitize_json_recurses_strings_only():
    out = sanitize_json(
        {"a": "x\x00y", "b": ["p\x00", {"c": "q\x00"}], "n": 5, "ok": None, "f": 1.5}
    )
    assert out == {"a": "xy", "b": ["p", {"c": "q"}], "n": 5, "ok": None, "f": 1.5}


def test_extracted_data_is_sanitized_before_insert(monkeypatch):
    monkeypatch.delenv("MIN_CONFIDENCE_TO_QUEUE", raising=False)

    def _fake(raw, url, name, *, mock=None, metrics=None):
        return {
            "data": ExtractedRecruitment(
                title="Clean\x00Title", organization_name="Org\x07X", year=2026
            ),
            "confidence": 0.9,
            "is_mock": True,
            "provider": "mock",
        }

    monkeypatch.setattr(runner_mod, "extract_recruitment_data", _fake)
    sb = RunnerSB()
    sb.db["source_registry"] = [_direct_source()]
    run_scraping_pass(sb, source_ids=["s-direct"], mock=True)
    row = sb.db["scrape_queue"][0]
    assert "\x00" not in row["extracted_data"]["title"]
    assert row["extracted_data"]["title"] == "CleanTitle"
    assert row["extracted_data"]["organization_name"] == "OrgX"


# ════════════════════════════════════════════════════════════════════════
#  Task 4b — queue-insert guard against a missing evidence document
# ════════════════════════════════════════════════════════════════════════


def test_queue_row_needs_review_when_document_missing(monkeypatch):
    _high_quality(monkeypatch)
    monkeypatch.setattr(runner_mod, "extract_recruitment_data", _extraction(0.9, mock_flag=False))
    monkeypatch.setattr(runner_mod, "fetch_page_text", lambda url: "BODY TEXT")
    monkeypatch.setattr(runner_mod, "_ensure_notification_document", lambda *a, **k: None)
    sb = RunnerSB()
    sb.db["source_registry"] = [_direct_source()]
    run_scraping_pass(sb, source_ids=["s-direct"], mock=False)
    row = sb.db["scrape_queue"][0]
    assert row["notification_document_id"] is None
    assert row["extraction_status"] == "needs_review"
    assert "notification_document_missing" in row["extracted_data"]["_meta"]["warnings"]


def test_queue_row_ok_when_document_present(monkeypatch):
    _high_quality(monkeypatch)
    monkeypatch.setattr(runner_mod, "extract_recruitment_data", _extraction(0.9, mock_flag=False))
    monkeypatch.setattr(runner_mod, "fetch_page_text", lambda url: "BODY TEXT")
    monkeypatch.setattr(runner_mod, "_ensure_notification_document", lambda *a, **k: "doc-1")
    sb = RunnerSB()
    sb.db["source_registry"] = [_direct_source()]
    run_scraping_pass(sb, source_ids=["s-direct"], mock=False)
    row = sb.db["scrape_queue"][0]
    assert row["notification_document_id"] == "doc-1"
    assert row["extraction_status"] == "ok"
    assert "notification_document_missing" not in (row["extracted_data"]["_meta"].get("warnings") or [])


# ════════════════════════════════════════════════════════════════════════
#  Task 5 — Anthropic timeout + per-source model budget
# ════════════════════════════════════════════════════════════════════════


def _timeout_client():
    class _Messages:
        def create(self, *a, **k):
            raise anthropic.APITimeoutError(
                request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            )

    class _Client:
        def __init__(self, *a, **k):
            self.messages = _Messages()

    return _Client


def test_extractor_timeout_returns_none_logs_and_counts(monkeypatch, caplog):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-looking-key-1234567890")
    monkeypatch.setattr(anthropic, "Anthropic", _timeout_client())
    caplog.set_level(logging.WARNING)
    metrics: dict = {}
    out = ex.extract_recruitment_data("page text", "https://x.gov.in/n", "Src", metrics=metrics)
    assert out is None
    assert metrics.get("extractor_timeout_count") == 1
    assert any("scrape.extractor_timeout" in r.getMessage() for r in caplog.records)


def test_timeout_produces_no_queue_or_low_quality_row(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-looking-key-1234567890")
    monkeypatch.setattr(anthropic, "Anthropic", _timeout_client())
    monkeypatch.setattr(runner_mod, "fetch_page_text", lambda url: "BODY TEXT")
    sb = RunnerSB()
    sb.db["source_registry"] = [_direct_source()]
    run_scraping_pass(sb, source_ids=["s-direct"], mock=False)
    assert sb.db.get("scrape_queue", []) == []
    assert sb.db.get("low_quality_extractions", []) == []


def _stub_aggregator_discovery(monkeypatch, urls):
    class _Link:
        def __init__(self, u):
            self.url = u
            self.label = ""
            self.event_type = "new_recruitment"

    class _Disc:
        def __init__(self):
            self.urls = list(urls)
            self.stats = {}
            self.lifecycle_links = []
            self.links = [_Link(u) for u in urls]

    monkeypatch.setattr(runner_mod, "fetch_page_html", lambda url: f"<html>{url}</html>")
    monkeypatch.setattr(runner_mod, "strip_html", lambda html: html)
    monkeypatch.setattr(runner_mod, "resolve_with_registry", lambda *a, **k: None)
    monkeypatch.setattr(runner_mod, "_lookup_prior_document_headers", lambda *a, **k: {})
    monkeypatch.setattr(runner_mod, "discover_aggregator_detail_urls", lambda *a, **k: _Disc())


def test_per_source_call_budget_skips_remaining(monkeypatch):
    monkeypatch.setattr(runner_mod, "MAX_MODEL_CALLS_PER_SOURCE", 2)
    monkeypatch.setattr(runner_mod, "MAX_MODEL_SECONDS_PER_SOURCE", 1e9)
    calls: list[str] = []

    def _fake(raw, url, name, *, mock=None, metrics=None):
        calls.append(url)
        return {
            "data": ExtractedRecruitment(title="t", organization_name="o", year=2026),
            "confidence": 0.9,
            "is_mock": False,
            "provider": "anthropic",
        }

    monkeypatch.setattr(runner_mod, "extract_recruitment_data", _fake)
    _stub_aggregator_discovery(monkeypatch, ["https://agg/d1", "https://agg/d2", "https://agg/d3"])
    sb = RunnerSB()  # aggregator src-1
    run_scraping_pass(sb, source_ids=["src-1"], mock=False, limit=10)
    # 3rd detail URL is skipped once the call budget (2) is reached.
    assert len(calls) == 2


def test_per_source_seconds_budget_skips_remaining(monkeypatch):
    monkeypatch.setattr(runner_mod, "MAX_MODEL_CALLS_PER_SOURCE", 999)
    monkeypatch.setattr(runner_mod, "MAX_MODEL_SECONDS_PER_SOURCE", 120.0)
    # Each extraction "takes" 50s (t0,t1 pairs differ by 50).
    ticks = iter([0, 50, 50, 100, 100, 150, 150, 200])
    monkeypatch.setattr(runner_mod.time, "monotonic", lambda: next(ticks))
    calls: list[str] = []

    def _fake(raw, url, name, *, mock=None, metrics=None):
        calls.append(url)
        return {
            "data": ExtractedRecruitment(title="t", organization_name="o", year=2026),
            "confidence": 0.9,
            "is_mock": False,
            "provider": "anthropic",
        }

    monkeypatch.setattr(runner_mod, "extract_recruitment_data", _fake)
    _stub_aggregator_discovery(
        monkeypatch, ["https://agg/d1", "https://agg/d2", "https://agg/d3", "https://agg/d4"]
    )
    sb = RunnerSB()
    run_scraping_pass(sb, source_ids=["src-1"], mock=False, limit=10)
    # acc crosses 120s after the 3rd call → 4th detail URL skipped.
    assert len(calls) == 3


# ════════════════════════════════════════════════════════════════════════
#  Task 6 — at most ONE source_registry PATCH per low-confidence call
#  (the "double-PATCH regression" premise did not exist: the strike counter
#  is in-memory, so a non-disabling call PATCHes zero times.)
# ════════════════════════════════════════════════════════════════════════


class _PatchCountingSB:
    def __init__(self, *, low_quality_ok=True):
        self.low_quality_ok = low_quality_ok
        self.source_registry_patches: list[dict] = []

    def table(self, name):
        return _PatchCountingTable(self, name)


class _PatchCountingTable:
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
        self._payload = None
        self._is_update = False

    def insert(self, payload):
        if self.name == "low_quality_extractions" and not self.parent.low_quality_ok:
            raise RuntimeError('relation "low_quality_extractions" does not exist')
        self._payload = payload
        return self

    def update(self, payload):
        self._payload = payload
        self._is_update = True
        return self

    def eq(self, *a, **k):
        return self

    def execute(self):
        if self.name == "source_registry" and self._is_update:
            self.parent.source_registry_patches.append(self._payload)

        class _R:
            data: list = []

        return _R()


def test_low_confidence_no_disable_issues_zero_registry_patches():
    sb = _PatchCountingSB()
    disabled = runner_mod._record_low_confidence_and_maybe_disable(
        sb, run_id="r", src={"id": "s"}, source_url="u",
        confidence=0.1, data_quality_score=0.1, extracted_data={},
    )
    assert disabled is False
    assert sb.source_registry_patches == []


def test_low_confidence_disable_issues_exactly_one_merged_patch(monkeypatch):
    monkeypatch.setenv("LOW_CONFIDENCE_STRIKE_LIMIT", "2")
    sb = _PatchCountingSB()
    runner_mod._record_low_confidence_and_maybe_disable(
        sb, run_id="r", src={"id": "s"}, source_url="u",
        confidence=0.1, data_quality_score=0.1, extracted_data={},
    )
    assert sb.source_registry_patches == []  # strike 1, no PATCH
    disabled = runner_mod._record_low_confidence_and_maybe_disable(
        sb, run_id="r", src={"id": "s"}, source_url="u",
        confidence=0.1, data_quality_score=0.1, extracted_data={},
    )
    assert disabled is True
    assert len(sb.source_registry_patches) == 1  # exactly one merged PATCH
    patch = sb.source_registry_patches[0]
    assert patch["is_active"] is False
    assert patch["verification_status"] == "auto_disabled_low_confidence"


# ════════════════════════════════════════════════════════════════════════
#  Task 8 — run severity scoring (pure mapping)
# ════════════════════════════════════════════════════════════════════════


def _metrics(**kw):
    base = {
        "anthropic_calls": 0,
        "low_quality_count": 0,
        "source_auto_disabled_count": 0,
        "source_registry_draft_failures": 0,
        "notification_document_failures": 0,
        "extractor_timeout_count": 0,
    }
    base.update(kw)
    return base


def test_status_completed_clean():
    assert runner_mod._compute_final_status(3, 0, _metrics(anthropic_calls=10)) == "completed"


def test_status_completed_with_warnings_at_25pct():
    assert (
        runner_mod._compute_final_status(3, 0, _metrics(anthropic_calls=100, low_quality_count=25))
        == "completed_with_warnings"
    )


def test_status_degraded_at_45pct():
    assert (
        runner_mod._compute_final_status(3, 0, _metrics(anthropic_calls=100, low_quality_count=45))
        == "degraded"
    )


def test_status_degraded_on_one_disable():
    assert (
        runner_mod._compute_final_status(3, 0, _metrics(anthropic_calls=10, source_auto_disabled_count=1))
        == "degraded"
    )


def test_status_degraded_on_one_draft_failure():
    assert (
        runner_mod._compute_final_status(3, 0, _metrics(anthropic_calls=10, source_registry_draft_failures=1))
        == "degraded"
    )


def test_status_degraded_on_one_document_failure():
    assert (
        runner_mod._compute_final_status(3, 0, _metrics(anthropic_calls=10, notification_document_failures=1))
        == "degraded"
    )


def test_status_failed_when_all_sources_errored():
    assert runner_mod._compute_final_status(3, 3, _metrics()) == "failed"


def test_status_partial_when_some_errored_no_severity():
    assert runner_mod._compute_final_status(3, 1, _metrics(anthropic_calls=10)) == "partial"


def test_status_degraded_outranks_partial():
    # one source errored AND one auto-disabled → degraded, not partial
    assert (
        runner_mod._compute_final_status(3, 1, _metrics(anthropic_calls=10, source_auto_disabled_count=1))
        == "degraded"
    )


def test_status_warning_on_extractor_timeout():
    assert (
        runner_mod._compute_final_status(3, 0, _metrics(anthropic_calls=10, extractor_timeout_count=1))
        == "completed_with_warnings"
    )


def test_status_reference_log_run_is_degraded():
    # 61% low_quality + 6 disables + 8 draft 400s, some sources errored
    metrics = _metrics(
        anthropic_calls=100,
        low_quality_count=61,
        source_auto_disabled_count=6,
        source_registry_draft_failures=8,
    )
    assert runner_mod._compute_final_status(10, 3, metrics) == "degraded"


@pytest.mark.parametrize(
    "calls,lq,expected",
    [
        (100, 20, "completed"),                 # 0.20 not > 0.20
        (100, 21, "completed_with_warnings"),   # 0.21 > 0.20
        (100, 40, "completed_with_warnings"),   # 0.40 not > 0.40, but > 0.20
        (100, 41, "degraded"),                  # 0.41 > 0.40
    ],
)
def test_ratio_boundaries(calls, lq, expected):
    assert runner_mod._compute_final_status(3, 0, _metrics(anthropic_calls=calls, low_quality_count=lq)) == expected


# ════════════════════════════════════════════════════════════════════════
#  Task 9 — recruitment_events upsert (dedup on generated event_hash)
# ════════════════════════════════════════════════════════════════════════


class _EventsSB:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.upserts: list[dict] = []

    def table(self, name):
        return _EventsTable(self, name)


class _EventsTable:
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
        self._payload = None
        self._on_conflict = None
        self._ignore = None

    def upsert(self, payload, *, on_conflict=None, ignore_duplicates=False, **_kw):
        self._payload = payload
        self._on_conflict = on_conflict
        self._ignore = ignore_duplicates
        return self

    def execute(self):
        if self.name == "recruitment_events":
            if self.parent.fail:
                raise RuntimeError("duplicate key value violates unique constraint (23505)")
            self.parent.upserts.append(
                {"payload": self._payload, "on_conflict": self._on_conflict, "ignore": self._ignore}
            )

        class _R:
            data: list = []

        return _R()


def test_lifecycle_event_upserts_on_event_hash():
    sb = _EventsSB()
    runner_mod._record_lifecycle_event(
        sb, source_id="s1", listing_id="al-1", event_type="admit_card",
        url="https://x.gov.in/a", label="Admit",
    )
    assert len(sb.upserts) == 1
    u = sb.upserts[0]
    assert u["on_conflict"] == "event_hash"
    assert u["ignore"] is True
    assert u["payload"]["event_type"] == "admit_card"
    assert u["payload"]["payload"]["discovered_url"] == "https://x.gov.in/a"


def test_lifecycle_event_skips_when_url_missing():
    sb = _EventsSB()
    runner_mod._record_lifecycle_event(
        sb, source_id="s1", listing_id=None, event_type="result", url="", label="",
    )
    assert sb.upserts == []


def test_lifecycle_event_swallows_unique_violation(caplog):
    sb = _EventsSB(fail=True)
    caplog.set_level(logging.WARNING)
    # Must not raise even when the upsert backend reports 23505.
    runner_mod._record_lifecycle_event(
        sb, source_id="s1", listing_id=None, event_type="result",
        url="https://x.gov.in/r", label="Result",
    )
    assert any("recruitment_events upsert failed" in r.getMessage() for r in caplog.records)


def test_lifecycle_event_dedup_same_link_via_runner_stub():
    sb = RunnerSB()
    for _ in range(2):
        runner_mod._record_lifecycle_event(
            sb, source_id="s1", listing_id=None, event_type="admit_card",
            url="https://x.gov.in/a", label="A",
        )
    # different event_type for the same URL is a distinct row
    runner_mod._record_lifecycle_event(
        sb, source_id="s1", listing_id=None, event_type="result",
        url="https://x.gov.in/a", label="A",
    )
    events = sb.db.get("recruitment_events", [])
    assert len(events) == 2
