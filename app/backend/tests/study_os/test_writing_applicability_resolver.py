"""Unit tests for the EWP writing-prompt applicability resolver (migration 214).

Pure-Python: no Postgres. Covers the deterministic verdict function
(`evaluate_targets`) across every rule — default-deny, explicit global,
precedence, exclusion, inert pending/rejected — plus the DB-facing wrappers and
the session-creation enforcement in `app/api/writing_practice.py` driven through
a tiny in-memory fake Supabase client.

Serial-safe (no xdist reliance); no external services.
"""
from __future__ import annotations

import pytest

from app.study_os.writing_practice import applicability

_EXAM = "00000000-0000-0000-0000-0000000000e1"
_EXAM2 = "00000000-0000-0000-0000-0000000000e2"
_FAMILY = "00000000-0000-0000-0000-0000000000f1"
_PHASE = "00000000-0000-0000-0000-0000000000c1"
_PHASE2 = "00000000-0000-0000-0000-0000000000c2"
_PROMPT = "00000000-0000-0000-0000-0000000000d1"
_TASK = "00000000-0000-0000-0000-0000000000a1"


def _t(status="active", *, is_global=False, family=None, exam=None, phase=None):
    return {
        "prompt_id": _PROMPT,
        "is_global": is_global,
        "exam_family_id": family,
        "exam_id": exam,
        "exam_phase_id": phase,
        "applicability_status": status,
    }


def _eval(targets, *, exam=_EXAM, phase=None, family=None):
    return applicability.evaluate_targets(
        targets, exam_id=exam, exam_phase_id=phase, exam_family_id=family
    )


# --------------------------------------------------------------------------- #
# DEFAULT-DENY                                                                 #
# --------------------------------------------------------------------------- #
def test_no_targets_is_not_applicable():
    assert _eval([]) is False


def test_pending_review_only_is_inert_not_applicable():
    assert _eval([_t("pending_review", exam=_EXAM)]) is False


def test_rejected_only_is_inert_not_applicable():
    assert _eval([_t("rejected", exam=_EXAM)]) is False


def test_non_matching_active_target_is_not_applicable():
    # An active exam target for a DIFFERENT exam does not apply to this context.
    assert _eval([_t("active", exam=_EXAM2)], exam=_EXAM) is False


# --------------------------------------------------------------------------- #
# EXPLICIT GLOBAL                                                              #
# --------------------------------------------------------------------------- #
def test_active_global_applies_everywhere():
    assert _eval([_t("active", is_global=True)], exam=_EXAM) is True
    assert _eval([_t("active", is_global=True)], exam=_EXAM2, phase=_PHASE) is True


def test_active_global_applies_with_no_exam_context():
    # Global is context-independent, so it is applicable even with no exam.
    assert _eval([_t("active", is_global=True)], exam=None) is True


def test_scoped_prompt_is_not_applicable_with_no_exam_context():
    # Fail-closed: without exam context a scoped (exam) active target cannot match.
    assert _eval([_t("active", exam=_EXAM)], exam=None) is False


# --------------------------------------------------------------------------- #
# MATCHING SCOPES                                                             #
# --------------------------------------------------------------------------- #
def test_active_exam_target_applies():
    assert _eval([_t("active", exam=_EXAM)], exam=_EXAM) is True


def test_active_family_target_applies_when_family_matches():
    assert _eval([_t("active", family=_FAMILY)], exam=_EXAM, family=_FAMILY) is True
    # Family target but the context resolves a different / no family.
    assert _eval([_t("active", family=_FAMILY)], exam=_EXAM, family=None) is False


def test_active_phase_target_applies_only_for_that_phase():
    tgt = [_t("active", phase=_PHASE)]
    assert _eval(tgt, exam=_EXAM, phase=_PHASE) is True
    # Phase isolation: a different phase (or exam-wide, no phase) does not match.
    assert _eval(tgt, exam=_EXAM, phase=_PHASE2) is False
    assert _eval(tgt, exam=_EXAM, phase=None) is False


def test_exam_wide_target_applies_to_any_phase_of_that_exam():
    tgt = [_t("active", exam=_EXAM)]
    assert _eval(tgt, exam=_EXAM, phase=_PHASE) is True
    assert _eval(tgt, exam=_EXAM, phase=_PHASE2) is True


# --------------------------------------------------------------------------- #
# EXCLUSION + PRECEDENCE                                                       #
# --------------------------------------------------------------------------- #
def test_exclusion_subtracts_exam_from_active_global():
    tgt = [_t("active", is_global=True), _t("excluded", exam=_EXAM)]
    # Excluded for _EXAM (more specific band wins) -> denied there...
    assert _eval(tgt, exam=_EXAM) is False
    # ...but still applicable for a different exam (only global matches there).
    assert _eval(tgt, exam=_EXAM2) is True


def test_exclusion_subtracts_phase_from_active_exam():
    tgt = [_t("active", exam=_EXAM), _t("excluded", phase=_PHASE)]
    assert _eval(tgt, exam=_EXAM, phase=_PHASE) is False   # phase carve-out
    assert _eval(tgt, exam=_EXAM, phase=_PHASE2) is True   # other phase still on


def test_more_specific_active_overrides_broader_exclusion():
    # Excluded at family, but an active exam (more specific) grants it.
    tgt = [_t("excluded", family=_FAMILY), _t("active", exam=_EXAM)]
    assert _eval(tgt, exam=_EXAM, family=_FAMILY) is True


def test_pending_at_specific_band_falls_through_to_broader_active():
    # pending at phase is inert; exam-wide active still applies.
    tgt = [_t("pending_review", phase=_PHASE), _t("active", exam=_EXAM)]
    assert _eval(tgt, exam=_EXAM, phase=_PHASE) is True


def test_pending_does_not_widen_a_denied_context():
    tgt = [_t("pending_review", is_global=True)]
    assert _eval(tgt, exam=_EXAM) is False


# --------------------------------------------------------------------------- #
# Fake Supabase — DB-facing wrappers + session-creation enforcement           #
# --------------------------------------------------------------------------- #
class _Query:
    def __init__(self, rows):
        self._rows = list(rows)

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
        if getattr(self, "_single", False):
            return type("R", (), {"data": self._rows[0] if self._rows else None})
        return type("R", (), {"data": list(self._rows)})


class _Rpc:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return type("R", (), {"data": self._result})


class FakeSupabase:
    def __init__(self, tables, rpc_result=None):
        self._tables = tables
        self._rpc_result = rpc_result
        self.rpc_calls = []

    def table(self, name):
        return _Query(self._tables.get(name, []))

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        return _Rpc(self._rpc_result)


def _fake(targets, *, exam_family=None, prompt=None, task=None, session=None):
    tables = {
        "writing_prompt_targets": targets,
        "exams": [{"id": _EXAM, "exam_family_id": exam_family}],
        "writing_prompts": [prompt] if prompt else [],
        "study_tasks": [task] if task else [],
    }
    return FakeSupabase(tables, rpc_result=session)


def test_is_prompt_applicable_reads_targets_and_family():
    fs = _fake([_t("active", family=_FAMILY)], exam_family=_FAMILY)
    assert applicability.is_prompt_applicable(
        fs, _PROMPT, exam_id=_EXAM, exam_phase_id=None
    ) is True
    fs2 = _fake([_t("active", family=_FAMILY)], exam_family=None)
    assert applicability.is_prompt_applicable(
        fs2, _PROMPT, exam_id=_EXAM, exam_phase_id=None
    ) is False


def test_resolve_applicable_prompt_ids_filters_the_set():
    p2 = "00000000-0000-0000-0000-0000000000d2"
    targets = [
        {"prompt_id": _PROMPT, "is_global": False, "exam_family_id": None,
         "exam_id": _EXAM, "exam_phase_id": None, "applicability_status": "active"},
        {"prompt_id": p2, "is_global": False, "exam_family_id": None,
         "exam_id": _EXAM, "exam_phase_id": None, "applicability_status": "pending_review"},
    ]
    fs = _fake(targets)
    got = applicability.resolve_applicable_prompt_ids(
        fs, [_PROMPT, p2], exam_id=_EXAM, exam_phase_id=None
    )
    assert got == {_PROMPT}


# --- session-creation enforcement ----------------------------------------- #
def _import_create_session():
    pytest.importorskip("fastapi")
    from app.api import writing_practice as wp
    return wp


def _prompt_row():
    return {
        "id": _PROMPT, "reviewer_status": "verified", "is_active": True,
        "required_sentence_count": 1, "microtopic_id": None,
    }


def test_create_session_rejects_non_applicable_prompt(monkeypatch):
    wp = _import_create_session()
    task = {"id": _TASK, "user_id": "u1", "exam_id": _EXAM, "exam_phase_id": None}
    # Prompt is verified+active but its ONLY target is pending_review -> not
    # applicable. Session creation must reject BEFORE calling the create RPC.
    fs = _fake([_t("pending_review", exam=_EXAM)], prompt=_prompt_row(), task=task)
    monkeypatch.setattr(wp, "get_supabase_admin", lambda: fs)

    body = wp.CreateSessionRequest(prompt_id=_PROMPT, study_task_id=task["id"], mode="learning")
    with pytest.raises(wp.HTTPException) as exc:
        wp.create_session(body, user={"id": "u1"})
    assert exc.value.status_code == 403
    assert fs.rpc_calls == [], "must not create a session for a non-applicable prompt"


def test_create_session_allows_applicable_prompt(monkeypatch):
    wp = _import_create_session()
    task = {"id": _TASK, "user_id": "u1", "exam_id": _EXAM, "exam_phase_id": None}
    session_row = {"id": "sess-1", "prompt_id": _PROMPT, "mode": "learning", "status": "in_progress"}
    fs = _fake([_t("active", exam=_EXAM)], prompt=_prompt_row(), task=task, session=session_row)
    monkeypatch.setattr(wp, "get_supabase_admin", lambda: fs)
    # _session_payload issues further reads; stub it to isolate the launch gate.
    monkeypatch.setattr(wp, "_session_payload", lambda _s, sess: {"session": sess})

    body = wp.CreateSessionRequest(prompt_id=_PROMPT, study_task_id=task["id"], mode="learning")
    out = wp.create_session(body, user={"id": "u1"})
    assert out["session"]["id"] == "sess-1"
    assert [c[0] for c in fs.rpc_calls] == ["ewp_create_writing_session"]


def test_create_session_no_task_denies_scoped_prompt(monkeypatch):
    wp = _import_create_session()
    # No study_task -> no exam context. A scoped (exam) prompt is denied fail-closed.
    fs = _fake([_t("active", exam=_EXAM)], prompt=_prompt_row())
    monkeypatch.setattr(wp, "get_supabase_admin", lambda: fs)
    body = wp.CreateSessionRequest(prompt_id=_PROMPT, mode="learning")
    with pytest.raises(wp.HTTPException) as exc:
        wp.create_session(body, user={"id": "u1"})
    assert exc.value.status_code == 403
    assert fs.rpc_calls == []


def test_create_session_no_task_allows_global_prompt(monkeypatch):
    wp = _import_create_session()
    session_row = {"id": "sess-g", "prompt_id": _PROMPT, "mode": "learning", "status": "in_progress"}
    fs = _fake([_t("active", is_global=True)], prompt=_prompt_row(), session=session_row)
    monkeypatch.setattr(wp, "get_supabase_admin", lambda: fs)
    monkeypatch.setattr(wp, "_session_payload", lambda _s, sess: {"session": sess})
    body = wp.CreateSessionRequest(prompt_id=_PROMPT, mode="learning")
    out = wp.create_session(body, user={"id": "u1"})
    assert out["session"]["id"] == "sess-g"
    assert [c[0] for c in fs.rpc_calls] == ["ewp_create_writing_session"]
