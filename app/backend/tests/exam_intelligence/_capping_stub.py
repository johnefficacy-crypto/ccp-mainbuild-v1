"""In-memory Supabase stub that models Supabase's server-side ``db-max-rows``
row cap AND honours ``.range()`` pagination.

The shared ``tests.persona_questions._stub.SBStub`` treats ``.range()`` as a
no-op and never caps a result set, so it cannot reproduce the verified-count
disagreement bug: a query that asks for ``.limit(20000)`` really does get every
row back. Against the live database, PostgREST silently truncates any read to
``db-max-rows`` (≈1000) unless the caller pages through ``.range()`` with a
deterministic ``.order()``. This stub reproduces exactly that behaviour so the
pagination fix can be proven:

* ``.eq`` / ``.in_`` / ``.is_`` / ``.not_.is_`` / ``.gt`` filters,
* ``.order(key, desc=)`` deterministic sort,
* ``.range(from, to)`` inclusive window (else ``.limit(n)``),
* a hard ``server_cap`` applied LAST, modelling ``db-max-rows``.

Set ``server_cap`` equal to the module ``_PAGE`` under test to model the real
production relationship (page size == server cap): a full page returns exactly
``_PAGE`` rows and the pagination loop keeps going; a partial page ends it.
"""
from __future__ import annotations

from typing import Any


class _Exec:
    def __init__(self, data: list[dict[str, Any]]):
        self.data = data


class _CapNot:
    def __init__(self, query: "_CapQuery"):
        self._q = query

    def is_(self, key: str, val: Any) -> "_CapQuery":
        self._q._filters.append((key, "not_is", val))
        return self._q


class _CapQuery:
    def __init__(self, rows: list[dict[str, Any]], cap: int):
        self._rows = rows
        self._cap = cap
        self._filters: list[tuple[str, str, Any]] = []
        self._order: str | None = None
        self._desc = False
        self._limit: int | None = None
        self._range: tuple[int, int] | None = None

    # ── builder chain ────────────────────────────────────────────────────
    def select(self, *a: Any, **k: Any) -> "_CapQuery":
        return self

    def eq(self, key: str, val: Any) -> "_CapQuery":
        self._filters.append((key, "eq", val))
        return self

    def in_(self, key: str, vals: Any) -> "_CapQuery":
        self._filters.append((key, "in", list(vals)))
        return self

    def is_(self, key: str, val: Any) -> "_CapQuery":
        self._filters.append((key, "is", val))
        return self

    def gt(self, key: str, val: Any) -> "_CapQuery":
        self._filters.append((key, "gt", val))
        return self

    def or_(self, *a: Any, **k: Any) -> "_CapQuery":
        # Not needed for the tables these tests exercise; accept and ignore.
        return self

    @property
    def not_(self) -> _CapNot:
        return _CapNot(self)

    def order(self, key: str, desc: bool = False, **k: Any) -> "_CapQuery":
        self._order = key
        self._desc = desc
        return self

    def limit(self, n: int) -> "_CapQuery":
        self._limit = n
        return self

    def range(self, from_n: int, to_n: int) -> "_CapQuery":
        self._range = (from_n, to_n)
        return self

    # ── evaluation ───────────────────────────────────────────────────────
    @staticmethod
    def _coerce(raw: Any) -> Any:
        if raw == "null":
            return None
        return raw

    def _match(self, row: dict[str, Any]) -> bool:
        for key, op, val in self._filters:
            cell = row.get(key)
            if op == "eq" and cell != val:
                return False
            if op == "in" and cell not in val:
                return False
            if op == "is" and cell is not self._coerce(val):
                return False
            if op == "not_is" and cell is self._coerce(val):
                return False
            if op == "gt" and not (cell is not None and str(cell) > str(val)):
                return False
        return True

    def execute(self) -> _Exec:
        rows = [r for r in self._rows if self._match(r)]
        if self._order:
            rows.sort(
                key=lambda r: (r.get(self._order) is None, r.get(self._order)),
                reverse=self._desc,
            )
        if self._range is not None:
            f, t = self._range
            rows = rows[f : t + 1]
        elif self._limit is not None:
            rows = rows[: self._limit]
        # Server-side db-max-rows cap — applied LAST, exactly like PostgREST.
        rows = rows[: self._cap]
        return _Exec([dict(r) for r in rows])


class _CapRpc:
    def __init__(self, value: Any = None):
        self._value = value

    def execute(self) -> _Exec:
        return _Exec(self._value)  # type: ignore[arg-type]


class CappingSB:
    """Supabase-shaped stub with a hard ``server_cap`` per read (models
    ``db-max-rows``) and real ``.range()`` pagination."""

    def __init__(self, db: dict[str, list[dict[str, Any]]], server_cap: int):
        self.db = db
        self.server_cap = server_cap

    def table(self, name: str) -> _CapQuery:
        return _CapQuery(self.db.get(name, []), self.server_cap)

    def rpc(self, name: str, params: dict[str, Any] | None = None) -> _CapRpc:
        return _CapRpc(None)
