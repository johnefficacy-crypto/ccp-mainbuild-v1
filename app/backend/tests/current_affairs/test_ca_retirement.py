"""ca:promote-sweep retirement wrapper tests (GQR-G5b)."""
from __future__ import annotations

from app.current_affairs import retirement
from tests.persona_questions._stub import SBStub, _RpcCall


class SweepSB(SBStub):
    def __init__(self, ret):
        super().__init__({})
        self._ret = ret
        self.calls: list = []

    def rpc(self, name, params=None):
        self.calls.append((name, params))
        return _RpcCall(self._ret)


def test_sweep_returns_archived_count():
    sb = SweepSB(3)
    assert retirement.sweep_expired_current_events(sb) == {"archived": 3}
    assert sb.calls == [("ca_sweep_expired_current_events", {})]


def test_sweep_handles_none_and_nonint():
    assert retirement.sweep_expired_current_events(SweepSB(None)) == {"archived": 0}
    assert retirement.sweep_expired_current_events(SweepSB("bad")) == {"archived": 0}


def test_retry_sweep_returns_expired_count():
    sb = SweepSB(4)
    assert retirement.sweep_expired_retry_items(sb) == {"retry_expired": 4}
    assert sb.calls == [("ca_sweep_expired_retry_items", {})]
    assert retirement.sweep_expired_retry_items(SweepSB(None)) == {"retry_expired": 0}


class _MultiSweepSB(SBStub):
    """Returns per-RPC results so the merged promote-sweep job can be exercised."""
    def __init__(self, results):
        super().__init__({})
        self._results = results

    def rpc(self, name, params=None):
        return _RpcCall(self._results.get(name, 0))


def test_promote_sweep_job_merges_event_and_retry_sweeps(monkeypatch):
    from app.notifications import scheduler
    sb = _MultiSweepSB({"ca_sweep_expired_current_events": 2, "ca_sweep_expired_retry_items": 5})
    monkeypatch.setattr(scheduler, "get_supabase_admin", lambda: sb)
    assert scheduler._job_ca_promote_sweep() == {"archived": 2, "retry_expired": 5}
