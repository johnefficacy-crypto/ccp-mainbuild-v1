"""Regression coverage for the ``.maybe_single()`` zero-row crash at the two
sites #923 deferred as out of scope.

postgrest-py's ``SyncMaybeSingleRequestBuilder.execute()`` (pinned
``postgrest==2.29.0``) returns bare ``None`` — not a response object with
``.data=None`` — when a ``.maybe_single()`` query matches zero rows. Both
call sites below used to chain ``.execute()).data`` directly, which crashed
with ``AttributeError: 'NoneType' object has no attribute 'data'`` on the
legitimate "not found" case (an unhandled 500) instead of resolving to the
intended 404 / ``None``:

  * ``pyq_practice_launch._owned_task`` — a genuinely missing/unowned task must
    404, never 500.
  * ``applicability._resolve_exam_family`` — a missing exam row must resolve to
    ``None`` (no family), never 500.

Both sites now route through the single shared ``app.db.utils.maybe_single``
guard (no per-module duplicate); the tests assert the shared helper directly
and via the two public call sites.

The shared unit test harness's fake Supabase client masked this: its
``execute()`` always returned an object, never bare ``None``. The fake here
DOES return bare ``None`` on an empty ``.maybe_single()`` match — matching the
real client — so the crash is actually caught.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from app.api import pyq_practice_launch as launch  # noqa: E402
from app.db.utils import maybe_single  # noqa: E402
from app.study_os.writing_practice import applicability  # noqa: E402

_USER = "u1"
_TASK = "00000000-0000-0000-0000-0000000000a1"
_EXAM = "00000000-0000-0000-0000-0000000000e1"


class _Query:
    """Real postgrest-py behaviour: ``.maybe_single().execute()`` returns bare
    ``None`` on a zero-row match; a plain ``.execute()`` returns a response
    object with ``.data``."""

    def __init__(self, rows):
        self._rows = [dict(r) for r in rows]
        self._single = False

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._rows = [r for r in self._rows if str(r.get(col)) == str(val)]
        return self

    def maybe_single(self):
        self._single = True
        return self

    def execute(self):
        if self._single:
            return type("R", (), {"data": self._rows[0]})() if self._rows else None
        return type("R", (), {"data": list(self._rows)})()


class FakeSupabase:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return _Query(self._tables.get(name, []))


# --------------------------------------------------------------------------- #
# Shared helper direct coverage (single implementation in app.db.utils; both  #
# call sites below route through it).                                          #
# --------------------------------------------------------------------------- #
class _RawMaybeSingle:
    def __init__(self, row):
        self._row = row

    def execute(self):
        if self._row is None:
            return None
        return type("R", (), {"data": self._row})()


def test_shared_maybe_single_returns_none_on_zero_rows():
    assert maybe_single(_RawMaybeSingle(None)) is None


def test_shared_maybe_single_returns_data_on_match():
    row = {"id": "x"}
    assert maybe_single(_RawMaybeSingle(row)) == row


# --------------------------------------------------------------------------- #
# _owned_task: zero-row match -> 404 HTTPException, never AttributeError.      #
# --------------------------------------------------------------------------- #
def test_owned_task_404_on_missing_row_not_attribute_error():
    fs = FakeSupabase({"study_tasks": []})
    with pytest.raises(launch.HTTPException) as exc:
        launch._owned_task(fs, _USER, _TASK)
    assert exc.value.status_code == 404


def test_owned_task_404_on_other_user_row():
    fs = FakeSupabase({"study_tasks": [{"id": _TASK, "user_id": "someone-else"}]})
    with pytest.raises(launch.HTTPException) as exc:
        launch._owned_task(fs, _USER, _TASK)
    assert exc.value.status_code == 404


def test_owned_task_returns_row_when_owned():
    row = {"id": _TASK, "user_id": _USER, "exam_id": _EXAM}
    fs = FakeSupabase({"study_tasks": [row]})
    assert launch._owned_task(fs, _USER, _TASK)["id"] == _TASK


# --------------------------------------------------------------------------- #
# _resolve_exam_family: missing exam row -> None, never AttributeError.        #
# --------------------------------------------------------------------------- #
def test_resolve_exam_family_none_on_missing_exam_not_attribute_error():
    fs = FakeSupabase({"exams": []})
    assert applicability._resolve_exam_family(fs, _EXAM) is None


def test_resolve_exam_family_none_without_exam_id_skips_query():
    # No exam_id short-circuits before any query.
    assert applicability._resolve_exam_family(FakeSupabase({}), None) is None


def test_resolve_exam_family_returns_family_when_present():
    fs = FakeSupabase({"exams": [{"id": _EXAM, "exam_family_id": "fam-1"}]})
    assert applicability._resolve_exam_family(fs, _EXAM) == "fam-1"
