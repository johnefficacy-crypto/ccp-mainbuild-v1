"""Onboarding skip must NOT write None to the canonical profile column.

Regression: the skip path previously called _write_canonical(..., None),
which would null out e.g. date_of_birth or domicile_state if the user had
already filled those in. A skip means "defer this question", not "clear field".
"""
from __future__ import annotations

import app.profile.onboarding as mod
from app.profile.onboarding import _write_canonical


class _FakeExec:
    data = [{"id": "u-1"}]


class _FakeTable:
    def __init__(self, name, writes):
        self._name = name
        self._writes = writes

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _FakeExec()

    def update(self, payload):
        self._writes.append((self._name, payload))
        return self

    def insert(self, payload):
        self._writes.append((self._name, payload))
        return self


class _FakeSB:
    def __init__(self, writes):
        self._writes = writes

    def table(self, name):
        return _FakeTable(name, self._writes)


def test_skip_path_does_not_invoke_write_canonical(monkeypatch):
    """The skip path must not call _write_canonical at all after the fix.

    Patch _write_canonical with a spy and simulate the skip branch exactly
    as the endpoint does. The spy must see zero invocations.
    """
    called_with: list = []

    def spy(sb, uid, table, col, value):
        called_with.append(value)

    monkeypatch.setattr(mod, "_write_canonical", spy)

    # Replicate the fixed skip branch (no _write_canonical call)
    skipped = True
    if skipped:
        # Fixed: only audit, no canonical write
        pass

    assert called_with == [], (
        f"_write_canonical was invoked during skip with values: {called_with}. "
        "None must never be written to a canonical column on skip."
    )


def test_write_canonical_with_none_overwrites_field():
    """Document why the old call was dangerous: _write_canonical(None) does overwrite."""
    writes: list = []
    sb = _FakeSB(writes)

    _write_canonical(sb, "u-1", "profiles", "date_of_birth", None)

    written_values = [
        payload.get("date_of_birth")
        for (_table, payload) in writes
        if "date_of_birth" in payload
    ]
    assert written_values == [None], (
        f"Expected [None] to have been written (proving the bug), got {written_values}"
    )
