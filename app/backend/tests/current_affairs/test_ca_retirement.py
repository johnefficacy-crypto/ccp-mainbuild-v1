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
