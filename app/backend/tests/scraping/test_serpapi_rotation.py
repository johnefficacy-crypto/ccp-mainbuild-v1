"""P1.1: SerpApi query rotation via the scrape_config cursor.

A permanent ``queries[:3]`` slice starves queries past index 2. The cursor in
``scrape_config.next_query_index`` rotates the window and advances every run
(even on zero-result or mid-loop failure) so no query is starved.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.scraping.runner import _select_queries_for_run, run_scraping_pass
from tests.test_scrape_runner_promote import RunnerSB

_Q5 = ["q0", "q1", "q2", "q3", "q4"]


def _src(queries, cursor=None):
    scrape_config = {} if cursor is None else {"next_query_index": cursor}
    return SimpleNamespace(adapter_config={"queries": queries}, scrape_config=scrape_config)


# ── _select_queries_for_run (pure) ──────────────────────────────────────────


def test_cursor_zero_takes_first_three():
    assert _select_queries_for_run(_src(_Q5, 0), max_per_run=3) == (["q0", "q1", "q2"], 3)


def test_cursor_three_wraps_to_one():
    assert _select_queries_for_run(_src(_Q5, 3), max_per_run=3) == (["q3", "q4", "q0"], 1)


def test_cursor_four_wraps_to_two():
    assert _select_queries_for_run(_src(_Q5, 4), max_per_run=3) == (["q4", "q0", "q1"], 2)


def test_out_of_range_cursor_normalises_via_modulo():
    # 7 % 5 == 2 → start at index 2.
    assert _select_queries_for_run(_src(_Q5, 7), max_per_run=3) == (["q2", "q3", "q4"], 0)


def test_two_queries_with_max_three_returns_both():
    assert _select_queries_for_run(_src(["a", "b"], 0), max_per_run=3) == (["a", "b"], 0)


def test_no_cursor_defaults_to_zero():
    assert _select_queries_for_run(_src(_Q5), max_per_run=3) == (["q0", "q1", "q2"], 3)


def test_empty_queries_returns_empty_and_zero():
    assert _select_queries_for_run(_src([], 0), max_per_run=3) == ([], 0)


def test_non_int_cursor_falls_back_to_zero():
    assert _select_queries_for_run(_src(_Q5, "garbage"), max_per_run=3) == (["q0", "q1", "q2"], 3)


# ── Integration: rotation across runs ───────────────────────────────────────


def _web_source_5q():
    return {
        "id": "serp-web-rot",
        "source_name": "SerpApi Web Rotation",
        "source_type": "aggregator",
        "adapter_type": "serpapi_web",
        "is_active": True,
        "discovery_only": True,
        "requires_official_confirmation": True,
        "official_url": "https://serpapi.com/search-api",
        "adapter_config": {"location": "India", "queries": list(_Q5)},
        "scrape_config": {"max_items_per_run": 10, "monthly_search_cap": 120, "daily_search_cap": 4},
    }


def _latest_cursor(sb):
    cursors = [
        u["scrape_config"].get("next_query_index")
        for u in sb.db.get("source_registry_updates", [])
        if isinstance(u.get("scrape_config"), dict) and "next_query_index" in u["scrape_config"]
    ]
    return cursors[-1] if cursors else None


def test_two_consecutive_runs_execute_different_queries(monkeypatch):
    seen: list[str] = []

    def _spy(*, engine, query, location, max_results, mock):
        seen.append(query)
        return []

    monkeypatch.setattr("app.scraping.runner._serpapi_fetch_leads", _spy)

    sb = RunnerSB()
    src = _web_source_5q()
    sb.db["source_registry"] = [src]

    run_scraping_pass(sb, mock=True)
    first = list(seen)
    assert first == ["q0", "q1", "q2"]
    # Feed the persisted cursor back in (RunnerSB doesn't mutate the seed row).
    src["scrape_config"] = {**src["scrape_config"], "next_query_index": _latest_cursor(sb)}

    seen.clear()
    run_scraping_pass(sb, mock=True)
    second = list(seen)
    assert second == ["q3", "q4", "q0"]
    # The second run runs queries the first one skipped (defeats starvation).
    assert {"q3", "q4"}.issubset(set(second))
    assert {"q3", "q4"}.isdisjoint(set(first))


def test_cursor_advances_on_zero_result_queries(monkeypatch):
    monkeypatch.setattr(
        "app.scraping.runner._serpapi_fetch_leads", lambda **kw: []
    )
    sb = RunnerSB()
    sb.db["source_registry"] = [_web_source_5q()]
    run_scraping_pass(sb, mock=True)
    # 5 queries, cursor 0, take 3 → next cursor 3 even though nothing was found.
    assert _latest_cursor(sb) == 3


def test_cursor_advances_on_mid_loop_exception(monkeypatch):
    monkeypatch.setattr("app.scraping.quota.can_use_serpapi", lambda *a, **k: True)

    calls = {"n": 0}

    def _flaky(*, engine, query, location, max_results, mock):
        calls["n"] += 1
        if calls["n"] == 2:  # second query blows up mid-loop
            raise RuntimeError("serpapi 500")
        return []

    monkeypatch.setattr("app.scraping.runner._serpapi_fetch_leads", _flaky)

    sb = RunnerSB()
    sb.db["source_registry"] = [_web_source_5q()]
    # Live path (mock=False) so the per-query try/except is exercised.
    run_scraping_pass(sb, mock=False)

    # finally still advanced the cursor past the failed query (no infinite retry).
    assert _latest_cursor(sb) == 3
    assert calls["n"] == 3  # all three selected queries attempted
