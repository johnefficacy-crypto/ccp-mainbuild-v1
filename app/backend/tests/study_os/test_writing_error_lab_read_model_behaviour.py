"""Behavioural integration test for the EWP-4 Error Lab read model (migration 213).

Applies migrations 205 + 213 to a real Postgres and drives
`public.ewp_error_lab(p_user)` directly, proving the SQL-side gating and fold:

  - owner scoping (another user's issues never appear),
  - feedback release (a future-dated exam session is excluded; learning always in),
  - current-state only (`affects_current_state=false` stale findings excluded),
  - effective-review-decision fold (§4.10a): confirmed → reclassified renders the
    CORRECTED issue_type + its remapped active canonical microtopic; reclassified
    → confirmed reverts to the original; a same-timestamp `event_seq` tiebreak
    decides the winner; an effective `invalidated` issue is excluded,
  - a single call returns the whole current-state set regardless of history size
    (no unbounded per-hop ID fan-out — the walk/fold is in SQL).

Runs in CI (the backend job provides Postgres + EWP_PG_DSN); locally set
EWP_PG_DSN to a disposable superuser DB. Skips when no DB is configured.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_DSN = os.environ.get("EWP_PG_DSN")
_PSQL = shutil.which("psql")
_MIG = Path(__file__).parents[3] / "supabase/migrations"

pytestmark = pytest.mark.skipif(
    not (_DSN and _PSQL),
    reason="set EWP_PG_DSN to a disposable Postgres superuser DB (and have psql) to run",
)

_U1 = "00000000-0000-0000-0000-0000000000a1"
_U2 = "00000000-0000-0000-0000-0000000000a2"
_PROMPT = "00000000-0000-0000-0000-0000000000d1"

_BOOTSTRAP = r"""
DO $$ BEGIN CREATE ROLE authenticated LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE service_role LOGIN BYPASSRLS; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE anon LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT USAGE ON SCHEMA public TO authenticated, service_role, anon;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $fn$
  SELECT NULLIF(current_setting('ewp.uid', true), '')::uuid $fn$;
CREATE TABLE IF NOT EXISTS public.profiles (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exams (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exam_cycles (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exam_phases (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.document_assets (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.study_tasks (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, task_type text);
CREATE TABLE IF NOT EXISTS public.subjects (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), slug text NOT NULL UNIQUE, name text NOT NULL, subject_group text, default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS public.topics (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), subject_id uuid NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE, parent_topic_id uuid REFERENCES public.topics(id) ON DELETE CASCADE, slug text NOT NULL, name text NOT NULL, level text NOT NULL DEFAULT 'topic' CHECK (level IN ('topic','microtopic','concept')), default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(subject_id, parent_topic_id, slug));
"""

# One learning session for U1 + one released fixture prompt. Issue rows are
# inserted per-test with microtopics resolved through the seeded active map.
_FIXTURES = f"""
INSERT INTO profiles(id) VALUES ('{_U1}'),('{_U2}') ON CONFLICT DO NOTHING;
INSERT INTO exams(id) VALUES ('00000000-0000-0000-0000-0000000000e1') ON CONFLICT DO NOTHING;
INSERT INTO writing_prompts(id,exam_id,subject_id,topic_id,microtopic_id,exercise_type,prompt_text,difficulty_level,reviewer_status,is_active,required_sentence_count)
  SELECT '{_PROMPT}','00000000-0000-0000-0000-0000000000e1',
    (SELECT id FROM subjects WHERE slug='english-language'),(SELECT id FROM topics WHERE slug='grammar'),
    (SELECT id FROM topics WHERE level='microtopic' LIMIT 1),'sentence_construction','write',1,'verified',true,1
  WHERE NOT EXISTS (SELECT 1 FROM writing_prompts WHERE id='{_PROMPT}');
"""

_CH = "a" * 64


def _psql(sql: str) -> None:
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"unexpected failure:\n{proc.stderr}"


def _psql_file(path: Path) -> None:
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-f", str(path)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"failed applying {path.name}:\n{proc.stderr}"


def _scalar(sql: str) -> str:
    # -q suppresses the command-status notice; even so, an ``INSERT … RETURNING
    # id`` can print the returned value followed by the ``INSERT 0 1`` tag on some
    # psql builds, so take the FIRST non-empty line (the scalar) rather than the
    # whole stdout — otherwise the id comes back as "<uuid>\nINSERT 0 1" and the
    # next INSERT rejects it as an invalid uuid.
    proc = subprocess.run([_PSQL, _DSN, "-t", "-A", "-X", "-q", "-c", sql], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return lines[0] if lines else ""


def _psql_as(role: str, sql: str) -> subprocess.CompletedProcess:
    """Run `sql` with the session role reset to `role` (SET ROLE, then RESET).

    Returns the completed process so callers can assert success OR the exact
    'permission denied' failure. ON_ERROR_STOP so the SELECT's failure is fatal."""
    return subprocess.run(
        [_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c",
         f"SET ROLE {role}; {sql}"],
        capture_output=True, text=True)


def _lab(user: str = _U1) -> list[dict]:
    raw = _scalar(f"SELECT COALESCE(json_agg(t),'[]'::json) FROM public.ewp_error_lab('{user}') t")
    return json.loads(raw)


@pytest.fixture(scope="module", autouse=True)
def _apply():
    _psql(_BOOTSTRAP)
    _psql_file(_MIG / "205_english_writing_practice_schema.sql")
    _psql_file(_MIG / "213_english_writing_practice_error_lab_read_model.sql")
    _psql(_FIXTURES)
    yield


def _new_session(*, user: str = _U1, mode: str = "learning",
                 released: str | None = None) -> str:
    """A session + unit + version + evaluation for `user`; returns the eval id.

    `released` (an ISO timestamp) makes it an exam session with that
    feedback_released_at; default is an immediate learning session (always
    released)."""
    policy = "immediate" if mode == "learning" else "on_evaluation_terminal"
    rel = "NULL" if released is None else f"'{released}'"
    return _scalar(f"""
    WITH s AS (
      INSERT INTO writing_sessions(user_id,prompt_id,mode,projection_revision,
        feedback_release_policy,feedback_released_at)
      VALUES ('{user}','{_PROMPT}','{mode}',1,'{policy}',{rel}) RETURNING id
    ), u AS (
      INSERT INTO writing_session_units(session_id,unit_number,status)
      SELECT id,1,'ready' FROM s RETURNING id
    ), v AS (
      INSERT INTO writing_unit_versions(unit_id,version_number,answer_text,content_hash)
      SELECT id,1,'a sentence','{_CH}' FROM u RETURNING id
    )
    INSERT INTO writing_evaluations(unit_version_id,deterministic_status,overall_status)
    SELECT id,'completed','completed' FROM v RETURNING id;
    """)


def _add_issue(eval_id: str, issue_type: str, *, current: bool = True,
               severity: str = "must_fix") -> str:
    """Insert an issue event, resolving its microtopic via the seeded active map."""
    return _scalar(f"""
    INSERT INTO writing_issue_events(evaluation_id,issue_type,microtopic_id,lineage_id,
      quoted_text,explanation,suggested_text,severity,affects_current_state)
    VALUES ('{eval_id}','{issue_type}',
      (SELECT m.microtopic_id FROM writing_issue_type_microtopic_map m
         WHERE m.issue_type='{issue_type}' AND m.is_active LIMIT 1),
      gen_random_uuid(),'q','why','fix','{severity}',{str(current).upper()})
    RETURNING id;""")


def _review(issue_id: str, decision: str, *, corrected: str | None = None,
            reviewer_type: str = "human",
            created_at: str = "2026-06-10T00:00:00+00:00") -> None:
    """Append a review event; event_seq is IDENTITY so later inserts win a tie.

    reviewer_type is NOT NULL with CHECK IN ('human','system') in migration 205
    (no default) — a human review decision is 'human'; pass 'system' for an
    evaluator-authored decision. Omitting it made the very first INSERT fail and
    took down the whole EWP_PG_DSN suite (the backend-CI failure)."""
    corr = "NULL" if corrected is None else f"'{corrected}'"
    _psql(f"""INSERT INTO writing_issue_review_events(issue_event_id,decision,
      corrected_issue_type,reviewer_type,created_at)
      VALUES ('{issue_id}','{decision}',{corr},'{reviewer_type}','{created_at}');""")


def _name_for(issue_type: str) -> str:
    return _scalar(f"""SELECT t.name FROM writing_issue_type_microtopic_map m
      JOIN topics t ON t.id=m.microtopic_id
      WHERE m.issue_type='{issue_type}' AND m.is_active LIMIT 1""")


def test_current_state_issue_renders_with_microtopic_name():
    ev = _new_session()
    _add_issue(ev, "subject_verb_agreement")
    rows = [r for r in _lab() if r["issue_type"] == "subject_verb_agreement"]
    assert len(rows) == 1
    assert rows[0]["microtopic_name"] == _name_for("subject_verb_agreement")
    assert rows[0]["microtopic_slug"]


def test_stale_and_other_user_issues_are_excluded():
    ev = _new_session()
    stale = _add_issue(ev, "tense", current=False)          # stale — excluded
    ev_other = _new_session(user=_U2)
    other = _add_issue(ev_other, "tense")                   # other user — excluded for U1
    u1_ids = {r["id"] for r in _lab(_U1)}
    assert stale not in u1_ids
    assert other not in u1_ids
    # The other user's issue is visible only under that owner.
    assert other in {r["id"] for r in _lab(_U2)}


def test_future_released_exam_session_is_excluded():
    ev = _new_session(mode="exam", released="2999-01-01T00:00:00+00:00")
    iid = _add_issue(ev, "punctuation")
    assert all(r["id"] != iid for r in _lab())


def test_reclassify_renders_corrected_type_and_remapped_microtopic():
    ev = _new_session()
    iid = _add_issue(ev, "spelling")
    # confirmed -> reclassified(word_choice): corrected type + remapped microtopic.
    _review(iid, "confirmed", created_at="2026-06-10T00:00:00+00:00")
    _review(iid, "reclassified", corrected="word_choice", created_at="2026-06-11T00:00:00+00:00")
    row = next(r for r in _lab() if r["id"] == iid)
    assert row["issue_type"] == "word_choice"
    assert row["microtopic_name"] == _name_for("word_choice")

    # reclassified -> confirmed reverts to the ORIGINAL classification.
    _review(iid, "confirmed", created_at="2026-06-12T00:00:00+00:00")
    row = next(r for r in _lab() if r["id"] == iid)
    assert row["issue_type"] == "spelling"
    assert row["microtopic_name"] == _name_for("spelling")


def test_effective_invalidation_excludes_issue():
    ev = _new_session()
    iid = _add_issue(ev, "redundancy")
    _review(iid, "confirmed", created_at="2026-06-10T00:00:00+00:00")
    _review(iid, "invalidated", created_at="2026-06-11T00:00:00+00:00")
    assert all(r["id"] != iid for r in _lab())


def test_same_timestamp_event_seq_is_the_tiebreak():
    ev = _new_session()
    iid = _add_issue(ev, "modifier")
    # Same created_at; the LATER insert (higher event_seq) wins → invalidated.
    _review(iid, "confirmed", created_at="2026-06-10T00:00:00+00:00")
    _review(iid, "invalidated", created_at="2026-06-10T00:00:00+00:00")
    assert all(r["id"] != iid for r in _lab())


def test_large_history_returns_in_a_single_call():
    ev = _new_session()
    for _ in range(60):
        _add_issue(ev, "cohesion")
    rows = [r for r in _lab() if r["issue_type"] == "cohesion"]
    # One SQL call returns the whole current-state set (no per-hop ID fan-out).
    assert len(rows) >= 60


# --- SECURITY DEFINER privilege matrix (§ REVOKE/GRANT on public.ewp_error_lab) ---
# The function is service_role-only; authenticated/anon must be denied EXECUTE.
# A grant regression here would turn the wrapper into a cross-user oracle, so the
# denial is also asserted when the caller passes ANOTHER user's UUID.

def test_service_role_can_execute_error_lab():
    proc = _psql_as("service_role", f"SELECT count(*) FROM public.ewp_error_lab('{_U1}');")
    assert proc.returncode == 0, f"service_role must be able to execute:\n{proc.stderr}"


def test_authenticated_is_denied_error_lab_even_for_another_user():
    # Own UUID and another user's UUID must BOTH be denied at EXECUTE — the grant
    # matrix, not the WHERE clause, is the authorization boundary.
    for uid in (_U1, _U2):
        proc = _psql_as("authenticated", f"SELECT * FROM public.ewp_error_lab('{uid}');")
        assert proc.returncode != 0, f"authenticated must be denied for {uid}"
        assert "permission denied" in proc.stderr.lower(), proc.stderr


def test_anon_is_denied_error_lab_even_for_another_user():
    for uid in (_U1, _U2):
        proc = _psql_as("anon", f"SELECT * FROM public.ewp_error_lab('{uid}');")
        assert proc.returncode != 0, f"anon must be denied for {uid}"
        assert "permission denied" in proc.stderr.lower(), proc.stderr
