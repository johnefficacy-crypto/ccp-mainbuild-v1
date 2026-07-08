"""EWP-SP3 planner task -> writing-session launch endpoint tests.

Drives ``app.api.writing_practice.launch_writing`` through an in-memory fake
Supabase client (same shape as the applicability-resolver suite). Serial-safe;
no Postgres, no external services.

Covers: ownership 404, no-eligible -> 409 (no arbitrary fallback), deterministic
selection (same task -> same prompt), the runtime-readiness gate excluding a
non-ready active prompt, resolver default-deny (excluded/pending never selected),
idempotent re-launch reusing a live session, that creation goes through the
shared enforcement path (the create RPC + applicability re-check run), and that
the mirrored runtime-ready allowlist stays in parity with migration 226.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from app.api import writing_practice as wp  # noqa: E402

_EXAM = "00000000-0000-0000-0000-0000000000e1"
_PHASE = "00000000-0000-0000-0000-0000000000c1"
_SUBJECT = "00000000-0000-0000-0000-000000005b01"  # english-language subject
_TOPIC = "00000000-0000-0000-0000-000000007a01"
_TASK = "00000000-0000-0000-0000-0000000000a1"
_USER = "u1"

# Two ready+applicable prompts; smallest id must always win.
_P_LOW = "00000000-0000-0000-0000-0000000000d1"
_P_HIGH = "00000000-0000-0000-0000-0000000000d9"
# A runtime-NON-ready (but verified/active) prompt.
_P_PARA = "00000000-0000-0000-0000-0000000000da"


# --------------------------------------------------------------------------- #
# Fake Supabase                                                               #
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

    def in_(self, col, vals):
        wanted = {str(v) for v in vals}
        self._rows = [r for r in self._rows if str(r.get(col)) in wanted]
        return self

    def maybe_single(self):
        self._single = True
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        if self._single:
            return type("R", (), {"data": self._rows[0] if self._rows else None})
        return type("R", (), {"data": list(self._rows)})


class _Rpc:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return type("R", (), {"data": self._result})


class FakeSupabase:
    def __init__(self, tables, *, rpc_results=None):
        self._tables = tables
        self._rpc_results = rpc_results or {}
        self.rpc_calls = []

    def table(self, name):
        return _Query(self._tables.get(name, []))

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        return _Rpc(self._rpc_results.get(name))


def _prompt(pid, *, exercise_type="sentence_construction", topic_id=_TOPIC):
    return {
        "id": pid,
        "reviewer_status": "verified",
        "is_active": True,
        "exercise_type": exercise_type,
        "subject_id": _SUBJECT,
        "topic_id": topic_id,
        "required_sentence_count": 1,
        "microtopic_id": None,
    }


def _target(pid, status="active", *, exam=_EXAM, is_global=False, phase=None):
    return {
        "prompt_id": pid,
        "is_global": is_global,
        "exam_family_id": None,
        "exam_id": None if is_global else exam,
        "exam_phase_id": phase,
        "applicability_status": status,
    }


def _task(**over):
    row = {
        "id": _TASK, "user_id": _USER, "exam_id": _EXAM, "exam_phase_id": None,
        "subject_id": _SUBJECT, "topic_id": _TOPIC, "launch_context": None,
    }
    row.update(over)
    return row


def _build(*, prompts, targets, task=_TASK, sessions=None, created_session=None):
    tables = {
        "study_tasks": [task] if isinstance(task, dict) else ([_task()] if task else []),
        "writing_prompts": prompts,
        "writing_prompt_targets": targets,
        "subjects": [{"id": _SUBJECT, "slug": "english-language"}],
        "exams": [{"id": _EXAM, "exam_family_id": None}],
        "writing_sessions": sessions or [],
    }
    rpc_results = {
        "cms_writing_runtime_ready_types": ["sentence_construction"],
        "ewp_create_writing_session": created_session
        or {"id": "sess-new", "status": "active"},
    }
    return FakeSupabase(tables, rpc_results=rpc_results)


def _patch(monkeypatch, fs):
    monkeypatch.setattr(wp, "get_supabase_admin", lambda: fs)


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_ownership_404_for_foreign_task(monkeypatch):
    fs = _build(prompts=[_prompt(_P_LOW)], targets=[_target(_P_LOW)],
                task=_task(user_id="someone-else"))
    _patch(monkeypatch, fs)
    with pytest.raises(wp.HTTPException) as exc:
        wp.launch_writing(_TASK, user={"id": _USER})
    assert exc.value.status_code == 404
    assert fs.rpc_calls == []


def test_ownership_404_for_missing_task(monkeypatch):
    fs = _build(prompts=[], targets=[], task=None)
    _patch(monkeypatch, fs)
    with pytest.raises(wp.HTTPException) as exc:
        wp.launch_writing(_TASK, user={"id": _USER})
    assert exc.value.status_code == 404


def test_no_eligible_prompt_409_no_fallback(monkeypatch):
    # Prompt is verified+active+ready but its ONLY target is pending -> inert.
    fs = _build(prompts=[_prompt(_P_LOW)], targets=[_target(_P_LOW, "pending_review")])
    _patch(monkeypatch, fs)
    with pytest.raises(wp.HTTPException) as exc:
        wp.launch_writing(_TASK, user={"id": _USER})
    assert exc.value.status_code == 409
    assert exc.value.detail == "no_eligible_prompt"
    assert not [c for c in fs.rpc_calls if c[0] == "ewp_create_writing_session"], \
        "must not create a session when nothing is eligible"


def test_runtime_readiness_gate_excludes_non_ready_active_prompt(monkeypatch):
    # Only an applicable paragraph_writing prompt exists — runtime NOT ready.
    fs = _build(
        prompts=[_prompt(_P_PARA, exercise_type="paragraph_writing")],
        targets=[_target(_P_PARA)],
    )
    _patch(monkeypatch, fs)
    with pytest.raises(wp.HTTPException) as exc:
        wp.launch_writing(_TASK, user={"id": _USER})
    assert exc.value.status_code == 409


def test_default_deny_excluded_prompt_never_selected(monkeypatch):
    # _P_LOW is excluded for this exam; _P_HIGH is active -> _P_HIGH must be chosen
    # even though _P_LOW sorts first, proving the resolver gate is applied.
    fs = _build(
        prompts=[_prompt(_P_LOW), _prompt(_P_HIGH)],
        targets=[
            _target(_P_LOW, "active", is_global=True),
            _target(_P_LOW, "excluded", exam=_EXAM),
            _target(_P_HIGH, "active", exam=_EXAM),
        ],
        created_session={"id": "sess-high", "status": "active"},
    )
    _patch(monkeypatch, fs)
    out = wp.launch_writing(_TASK, user={"id": _USER})
    create = [c for c in fs.rpc_calls if c[0] == "ewp_create_writing_session"]
    assert create and create[0][1]["p_prompt"] == _P_HIGH
    assert out["session_id"] == "sess-high"


def test_deterministic_selection_smallest_id_and_shared_path(monkeypatch):
    fs = _build(
        prompts=[_prompt(_P_HIGH), _prompt(_P_LOW)],  # unsorted input
        targets=[_target(_P_LOW), _target(_P_HIGH)],
        created_session={"id": "sess-low", "status": "active"},
    )
    _patch(monkeypatch, fs)
    out = wp.launch_writing(_TASK, user={"id": _USER})
    # Shared creation path invoked (applicability re-check happens inside it).
    assert [c[0] for c in fs.rpc_calls if c[0] == "ewp_create_writing_session"]
    create = [c for c in fs.rpc_calls if c[0] == "ewp_create_writing_session"][0]
    assert create[1]["p_prompt"] == _P_LOW  # smallest id wins deterministically
    assert create[1]["p_study_task"] == _TASK
    assert out == {
        "session_id": "sess-low",
        "practice_route": "/app/study/practice/english/sess-low",
    }


def test_selection_is_stable_across_calls(monkeypatch):
    def run():
        fs = _build(
            prompts=[_prompt(_P_LOW), _prompt(_P_HIGH)],
            targets=[_target(_P_LOW), _target(_P_HIGH)],
            created_session={"id": "sess-low", "status": "active"},
        )
        _patch(monkeypatch, fs)
        wp.launch_writing(_TASK, user={"id": _USER})
        return [c for c in fs.rpc_calls if c[0] == "ewp_create_writing_session"][0][1]["p_prompt"]

    assert run() == run() == _P_LOW


def test_idempotent_relaunch_reuses_live_session(monkeypatch):
    fs = _build(
        prompts=[_prompt(_P_LOW)], targets=[_target(_P_LOW)],
        sessions=[{"id": "sess-live", "status": "active",
                   "study_task_id": _TASK, "user_id": _USER}],
    )
    _patch(monkeypatch, fs)
    out = wp.launch_writing(_TASK, user={"id": _USER})
    assert out == {
        "session_id": "sess-live",
        "practice_route": "/app/study/practice/english/sess-live",
    }
    assert fs.rpc_calls == [], "must not create a second session for the same task"


def test_terminal_session_does_not_block_new_launch(monkeypatch):
    fs = _build(
        prompts=[_prompt(_P_LOW)], targets=[_target(_P_LOW)],
        sessions=[{"id": "sess-done", "status": "completed",
                   "study_task_id": _TASK, "user_id": _USER}],
        created_session={"id": "sess-fresh", "status": "active"},
    )
    _patch(monkeypatch, fs)
    out = wp.launch_writing(_TASK, user={"id": _USER})
    assert out["session_id"] == "sess-fresh"
    assert [c[0] for c in fs.rpc_calls if c[0] == "ewp_create_writing_session"]


def test_no_task_exam_context_denies_scoped_prompt(monkeypatch):
    # Task without exam context: a scoped (exam) prompt is denied fail-closed.
    fs = _build(prompts=[_prompt(_P_LOW)], targets=[_target(_P_LOW, "active", exam=_EXAM)],
                task=_task(exam_id=None, exam_phase_id=None))
    _patch(monkeypatch, fs)
    with pytest.raises(wp.HTTPException) as exc:
        wp.launch_writing(_TASK, user={"id": _USER})
    assert exc.value.status_code == 409


# --------------------------------------------------------------------------- #
# Runtime-ready allowlist parity with migration 226                           #
# --------------------------------------------------------------------------- #
def test_runtime_ready_mirror_matches_migration_226():
    mig = (
        Path(__file__).parents[3]
        / "supabase/migrations/226_ewp_prompt_activation_lifecycle.sql"
    ).read_text()
    body = re.search(
        r"FUNCTION\s+cms_writing_runtime_ready_types\(\).*?SELECT\s+ARRAY\[(.*?)\]",
        mig, re.DOTALL | re.IGNORECASE,
    )
    assert body, "could not locate cms_writing_runtime_ready_types() in migration 226"
    sql_types = tuple(re.findall(r"'([^']+)'", body.group(1)))
    assert sql_types == wp.RUNTIME_READY_EXERCISE_TYPES


def test_runtime_ready_reads_db_function(monkeypatch):
    # When the DB function returns a widened allowlist, code uses it (no drift).
    fs = _build(prompts=[], targets=[])
    fs._rpc_results["cms_writing_runtime_ready_types"] = ["sentence_construction", "future_type"]
    assert set(wp._runtime_ready_types(fs)) == {"sentence_construction", "future_type"}


def test_runtime_ready_falls_back_to_mirror_when_db_unavailable():
    fs = _build(prompts=[], targets=[])
    fs._rpc_results["cms_writing_runtime_ready_types"] = None
    assert wp._runtime_ready_types(fs) == list(wp.RUNTIME_READY_EXERCISE_TYPES)
