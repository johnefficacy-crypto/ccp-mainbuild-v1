"""Regression coverage for the ``.maybe_single()`` zero-row crash.

postgrest-py's ``SyncMaybeSingleRequestBuilder.execute()`` (pinned
``postgrest==2.29.0``, see requirements.txt) returns bare ``None`` — not a
response object with ``.data=None`` — when a ``.maybe_single()`` query matches
zero rows. Every call site in ``app.api.writing_practice`` used to chain
``.execute().data`` directly on a ``.maybe_single()`` query, which crashed with
``AttributeError: 'NoneType' object has no attribute 'data'`` on the
legitimate "not found" case instead of returning ``None`` — surfacing as an
unhandled 500 instead of the intended 404/403.

The existing test harness's fake Supabase client masked this: its
``execute()`` always returns an object (``type("R", (), {"data": ...})``),
never bare ``None``, so it never reproduced the real client's behaviour. These
tests use a fake that DOES return bare ``None`` on an empty ``.maybe_single()``
match — matching real postgrest-py — so the crash is actually caught.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from app.api import writing_practice as wp  # noqa: E402
from app.db.utils import maybe_single  # noqa: E402

_USER = "u1"
_SESSION = "00000000-0000-0000-0000-0000000000f1"
_TASK = "00000000-0000-0000-0000-0000000000a1"
_PROMPT = "00000000-0000-0000-0000-0000000000d1"


# --------------------------------------------------------------------------- #
# _maybe_single() direct unit coverage                                        #
# --------------------------------------------------------------------------- #
class _RealPostgrestMaybeSingleQuery:
    """Mimics postgrest-py 2.29.0's SyncMaybeSingleRequestBuilder.execute():
    returns bare None on a zero-row match, a response object with .data
    otherwise."""

    def __init__(self, row):
        self._row = row

    def execute(self):
        if self._row is None:
            return None
        return type("R", (), {"data": self._row})()


def test_maybe_single_helper_returns_none_on_zero_rows():
    assert maybe_single(_RealPostgrestMaybeSingleQuery(None)) is None


def test_maybe_single_helper_returns_data_on_match():
    row = {"id": "x"}
    assert maybe_single(_RealPostgrestMaybeSingleQuery(row)) == row


# --------------------------------------------------------------------------- #
# Endpoint-level regressions: a real zero-row .maybe_single() response must
# raise the intended HTTPException, never AttributeError.                     #
# --------------------------------------------------------------------------- #
class _Query:
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
            # Real postgrest-py behaviour: bare None on a zero-row match.
            return (
                type("R", (), {"data": self._rows[0]})() if self._rows else None
            )
        return type("R", (), {"data": list(self._rows)})()


class FakeSupabase:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return _Query(self._tables.get(name, []))

    def rpc(self, name, params):  # pragma: no cover - not exercised here
        raise AssertionError(f"unexpected RPC call: {name}")


def _patch(monkeypatch, fs):
    monkeypatch.setattr(wp, "get_supabase_admin", lambda: fs)


def test_owned_task_404_on_zero_row_match_not_attribute_error(monkeypatch):
    fs = FakeSupabase({"study_tasks": []})
    with pytest.raises(wp.HTTPException) as exc:
        wp._owned_task(fs, _USER, _TASK)
    assert exc.value.status_code == 404


def test_owned_session_404_on_zero_row_match_not_attribute_error():
    fs = FakeSupabase({"writing_sessions": []})
    with pytest.raises(wp.HTTPException) as exc:
        wp._owned_session(fs, _SESSION, _USER)
    assert exc.value.status_code == 404


def test_create_learning_session_404_on_unverified_prompt(monkeypatch):
    # Mirrors the EWP-SP5 e2e negative: an unverified/inactive prompt must
    # 404, never 500.
    fs = FakeSupabase({"writing_prompts": []})
    with pytest.raises(wp.HTTPException) as exc:
        wp._create_learning_session(
            fs,
            user_id=_USER,
            prompt_id=_PROMPT,
            study_task_id=None,
            exam_id=None,
            exam_phase_id=None,
        )
    assert exc.value.status_code == 404
    assert "not verified/active" in exc.value.detail


def test_english_subject_id_falls_back_when_slug_unresolved():
    fs = FakeSupabase({"subjects": []})
    task = {"subject_id": "fallback-subject"}
    assert wp._english_subject_id(fs, task) == "fallback-subject"


# --------------------------------------------------------------------------- #
# EWP-SP5 e2e negative, exact shape: the prompt ROW EXISTS and is verified but
# is_active=false. The .eq("is_active", True) filter drops it to zero rows, so
# .maybe_single() returns bare None. Proves 404 (not 500) with the row present,
# which the empty-table cases above do not exercise.                          #
# --------------------------------------------------------------------------- #
def _verified_inactive_prompt():
    return {
        "id": _PROMPT,
        "reviewer_status": "verified",
        "is_active": False,  # verified-but-inactive: hidden from launch
        "exercise_type": "sentence_construction",
        "required_sentence_count": 1,
        "microtopic_id": None,
    }


def test_create_learning_session_404_on_verified_but_inactive_prompt():
    fs = FakeSupabase({"writing_prompts": [_verified_inactive_prompt()]})
    with pytest.raises(wp.HTTPException) as exc:
        wp._create_learning_session(
            fs,
            user_id=_USER,
            prompt_id=_PROMPT,
            study_task_id=None,
            exam_id=None,
            exam_phase_id=None,
        )
    assert exc.value.status_code == 404
    assert "not verified/active" in exc.value.detail


def test_create_session_endpoint_404_on_verified_but_inactive_prompt(monkeypatch):
    # End-to-end path: create_session -> _create_learning_session -> ).data.
    # The traceback that failed e2e (AttributeError on None) must now be a 404.
    fs = FakeSupabase({"writing_prompts": [_verified_inactive_prompt()]})
    _patch(monkeypatch, fs)
    body = wp.CreateSessionRequest(prompt_id=_PROMPT, study_task_id=None, mode="learning")
    with pytest.raises(wp.HTTPException) as exc:
        wp.create_session(body, user={"id": _USER})
    assert exc.value.status_code == 404
    assert "not verified/active" in exc.value.detail
