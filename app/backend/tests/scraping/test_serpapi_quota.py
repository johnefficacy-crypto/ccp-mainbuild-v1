"""SerpApi quota guard tests (acceptance: cap blocks new calls)."""
from __future__ import annotations

from datetime import datetime, timezone

from app.scraping.quota import can_use_serpapi, record_serpapi_usage


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _this_month() -> str:
    return datetime.now(timezone.utc).date().strftime("%Y-%m")


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, sb):
        self.sb = sb
        self.filters: dict = {}
        self._op = None
        self._payload = None

    def select(self, *a, **k):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self.sb.raise_on_read and self._op == "select":
            raise RuntimeError("external_api_usage read failed")
        if self._op == "select":
            rows = [r for r in self.sb.rows if all(r.get(k) == v for k, v in self.filters.items())]
            return _Result([dict(r) for r in rows])
        if self._op == "insert":
            row = {**self._payload, "id": f"usage-{len(self.sb.rows) + 1}"}
            self.sb.rows.append(row)
            return _Result([row])
        if self._op == "update":
            updated = []
            for r in self.sb.rows:
                if all(r.get(k) == v for k, v in self.filters.items()):
                    r.update(self._payload)
                    updated.append(r)
            return _Result(updated)
        return _Result([])


class FakeUsageSB:
    def __init__(self, rows=None, raise_on_read=False):
        self.rows = rows or []
        self.raise_on_read = raise_on_read

    def table(self, name):
        assert name == "external_api_usage", name
        return _Query(self)


def test_under_caps_allows():
    sb = FakeUsageSB()
    assert can_use_serpapi(sb, daily_cap=4, monthly_cap=120) is True


def test_daily_cap_blocks():
    sb = FakeUsageSB([
        {"provider": "serpapi", "usage_date": _today_iso(), "usage_month": _this_month(), "count": 4},
    ])
    assert can_use_serpapi(sb, daily_cap=4, monthly_cap=120) is False


def test_monthly_cap_blocks_even_when_daily_is_low():
    sb = FakeUsageSB([
        {"provider": "serpapi", "usage_date": _today_iso(), "usage_month": _this_month(), "count": 120},
    ])
    # daily_cap is generous so only the monthly cap can block here.
    assert can_use_serpapi(sb, daily_cap=1000, monthly_cap=120) is False


def test_other_provider_usage_does_not_count():
    sb = FakeUsageSB([
        {"provider": "someone_else", "usage_date": _today_iso(), "usage_month": _this_month(), "count": 999},
    ])
    assert can_use_serpapi(sb, daily_cap=4, monthly_cap=120) is True


def test_record_inserts_then_increments():
    sb = FakeUsageSB()
    record_serpapi_usage(sb, count=1)
    assert len(sb.rows) == 1
    assert sb.rows[0]["count"] == 1
    assert sb.rows[0]["provider"] == "serpapi"
    assert sb.rows[0]["usage_date"] == _today_iso()

    record_serpapi_usage(sb, count=1)
    assert len(sb.rows) == 1  # same (provider, month, date) → incremented, not duplicated
    assert sb.rows[0]["count"] == 2


def test_read_failure_fails_closed():
    sb = FakeUsageSB(raise_on_read=True)
    assert can_use_serpapi(sb, daily_cap=4, monthly_cap=120) is False
