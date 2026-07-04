"""Behavioural integration test for migration 221 — the EWP pipeline fix after
migration 214 dropped the exam-scope columns from ``writing_prompts``.

Applies the FULL post-214 chain (205 → 207 → 209 → 214 → 221) to a real Postgres
and proves the three things 221 changes:

  1. Immutable prompt snapshot — ``ewp_create_writing_session`` freezes the
     prompt's scope/content (exercise_type, topic_id, prompt_text, source_text,
     rubric_dimensions) onto ``writing_sessions.prompt_snapshot``; a later edit of
     the underlying prompt does NOT change what the claim payload sees.
  2. exam_id derived from the STUDY TASK — no longer a prompt attribute (the
     column is gone after 214); ``study_tasks.exam_id`` on the session's task, and
     NULL for an ad-hoc session with no task.
  3. prompt_text / source_text are SURFACED on the claim payload (the RPC half of
     the "source_text not delivered to the evaluator" blocker), and the full
     session → claim → complete → mastery-outbox → evidence path writes evidence
     bound to the derived exam.

Also guards that ``writing_prompts.exam_id`` really is absent after 214, so a
regression that re-reads the prompt's exam column would fail loudly here.

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

_A = "00000000-0000-0000-0000-0000000000aa"
_PROMPT = "00000000-0000-0000-0000-0000000000d1"
_EXAM = "00000000-0000-0000-0000-0000000000e1"
_TASK = "00000000-0000-0000-0000-0000000000c1"

# Bootstrap mirrors the sibling evaluator harness, with the two things the
# post-214 chain needs that the pre-214 harness omits:
#   * study_tasks.exam_id (added by migration 034 in prod; the pipeline now
#     derives exam from here);
#   * exam_families (a writing_prompt_targets FK target introduced by 214).
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
CREATE TABLE IF NOT EXISTS public.exam_families (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exam_cycles (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.exam_phases (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.document_assets (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE IF NOT EXISTS public.study_tasks (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, task_type text, exam_id uuid REFERENCES public.exams(id));
CREATE TABLE IF NOT EXISTS public.subjects (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), slug text NOT NULL UNIQUE, name text NOT NULL, subject_group text, default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS public.topics (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), subject_id uuid NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE, parent_topic_id uuid REFERENCES public.topics(id) ON DELETE CASCADE, slug text NOT NULL, name text NOT NULL, level text NOT NULL DEFAULT 'topic' CHECK (level IN ('topic','microtopic','concept')), default_difficulty_level text, description text, is_active boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(subject_id, parent_topic_id, slug));
"""

# Post-214 fixtures: writing_prompts has NO exam scope column; the prompt is
# subject/topic/microtopic scoped and carries source_text (the sentence to fix).
# A study task carries the exam the practice belongs to.
_FIXTURES = f"""
INSERT INTO exams(id) VALUES ('{_EXAM}') ON CONFLICT DO NOTHING;
INSERT INTO profiles(id) VALUES ('{_A}') ON CONFLICT DO NOTHING;
INSERT INTO study_tasks(id,user_id,task_type,exam_id) VALUES ('{_TASK}','{_A}','writing','{_EXAM}') ON CONFLICT DO NOTHING;
INSERT INTO writing_prompts(id,subject_id,topic_id,microtopic_id,exercise_type,prompt_text,source_text,difficulty_level,reviewer_status,is_active,required_sentence_count)
  SELECT '{_PROMPT}',
    (SELECT id FROM subjects WHERE slug='english-language'),(SELECT id FROM topics WHERE slug='grammar'),
    (SELECT id FROM topics WHERE level='microtopic' LIMIT 1),'sentence_correction',
    'Correct the grammatical error in the sentence.','He go to school every day.',1,'verified',false,1
  WHERE NOT EXISTS (SELECT 1 FROM writing_prompts WHERE id='{_PROMPT}');
"""


def _psql(sql: str, *, expect_ok: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
                          capture_output=True, text=True)
    if expect_ok:
        assert proc.returncode == 0, f"unexpected failure:\n{proc.stderr}"
    else:
        assert proc.returncode != 0, f"expected failure but succeeded:\n{proc.stdout}"
    return proc


def _psql_file(path: Path) -> None:
    proc = subprocess.run([_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-f", str(path)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"failed applying {path.name}:\n{proc.stderr}"


def _scalar(sql: str) -> str:
    proc = subprocess.run([_PSQL, _DSN, "-t", "-A", "-X", "-c", sql], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _json(sql: str) -> dict:
    return json.loads(_scalar(sql))


def _evidence_key(*, evidence_op: str, user_id: str, evaluation_id: str,
                  issue_projection_id: str | None, microtopic_id: str | None,
                  evidence_tier: str, source_type: str,
                  review_event_id: str | None = None) -> str:
    def q(v):
        return "NULL" if v is None else f"'{v}'"
    return _scalar(
        "SELECT ewp_private.ewp_compute_evidence_key("
        f"'{evidence_op}','{user_id}','{evaluation_id}',{q(issue_projection_id)},"
        f"{q(microtopic_id)},'{evidence_tier}','{source_type}',{q(review_event_id)})")


@pytest.fixture(scope="module", autouse=True)
def _apply():
    _psql(_BOOTSTRAP)
    _psql_file(_MIG / "205_english_writing_practice_schema.sql")
    _psql_file(_MIG / "207_english_writing_practice_rpcs.sql")
    _psql_file(_MIG / "209_english_writing_practice_evaluator.sql")
    _psql_file(_MIG / "214_writing_prompt_content_scoping.sql")
    _psql_file(_MIG / "221_ewp_prompt_snapshot_and_exam_derivation.sql")
    _psql(_FIXTURES)
    yield


def _drain_pending() -> None:
    """Clear the global-oldest queues so a test's fresh job/outbox is the sole
    pending one (both claim RPCs are global-oldest)."""
    for _ in range(50):
        raw = _scalar("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
        if not raw:
            break
        c = json.loads(raw)
        _scalar(
            f"SELECT ewp_complete_language_evaluation('{c['job_id']}','{c['claim_token']}',"
            f"'v','[]'::jsonb,'{{}}'::jsonb,NULL,false,'off',NULL)")
    for _ in range(50):
        raw = _scalar("SELECT ewp_claim_mastery_outbox(900)")
        if not raw:
            break
        o = json.loads(raw)
        _scalar(
            f"SELECT ewp_complete_mastery_outbox('{o['id']}','{o['claim_token']}',NULL,NULL)")


def _micro() -> str:
    return _scalar("SELECT id FROM topics WHERE level='microtopic' LIMIT 1")


def _create_session(study_task: str | None) -> str:
    _drain_pending()
    task = f"'{study_task}'" if study_task else "NULL"
    return _scalar(
        f"SELECT (ewp_create_writing_session('{_A}','{_PROMPT}',{task},'learning',1,'immediate',"
        f"NULL,1,'{_micro()}','{{\"schema_version\":1}}'::jsonb))->>'id'")


def _submit(sid: str, answer: str, ch: str) -> None:
    _scalar(
        f"SELECT ewp_submit_writing_unit('{_A}','{sid}',1,'{answer}',3,3,'{ch}',1,'{{}}'::jsonb,'det-v1')")


def test_prompt_has_no_exam_column_after_214():
    # If this fails, the migration chain is wrong and every "exam derived from
    # the prompt" regression would silently pass — so guard it explicitly.
    assert _scalar(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_name='writing_prompts' AND column_name='exam_id'") == "0"


def test_create_session_captures_immutable_prompt_snapshot():
    sid = _create_session(_TASK)
    snap = _json(f"SELECT prompt_snapshot FROM writing_sessions WHERE id='{sid}'")
    assert snap["exercise_type"] == "sentence_correction"
    assert snap["prompt_text"] == "Correct the grammatical error in the sentence."
    assert snap["source_text"] == "He go to school every day."
    assert snap["topic_id"] == _scalar("SELECT id FROM topics WHERE slug='grammar'")
    assert snap["rubric_dimensions"] == []  # this prompt has no rubric


def test_claim_derives_exam_from_study_task_and_surfaces_prompt_and_source():
    sid = _create_session(_TASK)
    _submit(sid, "he goes to school", "b" * 64)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    # exam comes from study_tasks.exam_id (NOT the prompt — that column is gone).
    assert claim["exam_id"] == _EXAM
    assert claim["exercise_type"] == "sentence_correction"
    assert claim["topic_id"] == _scalar("SELECT id FROM topics WHERE slug='grammar'")
    # prompt/source now surfaced to the worker (the RPC half of the blocker).
    assert claim["prompt_text"] == "Correct the grammatical error in the sentence."
    assert claim["source_text"] == "He go to school every day."


def test_claim_has_null_exam_for_adhoc_session_without_task():
    sid = _create_session(None)
    _submit(sid, "ad hoc answer text", "c" * 64)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    assert claim["exam_id"] is None  # no study task => no exam; safe (key excludes it)
    assert claim["source_text"] == "He go to school every day."


def test_prompt_edit_after_session_does_not_change_claim_scope():
    sid = _create_session(_TASK)
    _submit(sid, "immutable snapshot answer", "d" * 64)
    # Mutate the underlying prompt AFTER the session was created.
    _psql(
        f"UPDATE writing_prompts SET prompt_text='EDITED PROMPT', source_text='EDITED SOURCE' "
        f"WHERE id='{_PROMPT}'")
    try:
        claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
        # The claim reflects the FROZEN snapshot, not the live (edited) prompt.
        assert claim["prompt_text"] == "Correct the grammatical error in the sentence."
        assert claim["source_text"] == "He go to school every day."
    finally:
        _psql(
            f"UPDATE writing_prompts SET prompt_text='Correct the grammatical error in the sentence.',"
            f"source_text='He go to school every day.' WHERE id='{_PROMPT}'")


def test_full_pipeline_writes_evidence_bound_to_derived_exam():
    sid = _create_session(_TASK)
    _submit(sid, "clean corrected sentence", "e" * 64)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    assert claim["exam_id"] == _EXAM
    # Clean unit → production tier, no projection, unit microtopic. Enqueue with
    # the genuine §4.12b key so the outbox completion's re-derived binding holds.
    key = _evidence_key(
        evidence_op="assert", user_id=_A, evaluation_id=claim["evaluation_id"],
        issue_projection_id=None, microtopic_id=claim.get("microtopic_id"),
        evidence_tier="production", source_type="sentence_drill")
    _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','[]'::jsonb,'{{}}'::jsonb,NULL,false,'shadow','{key}')")
    oc = _json("SELECT ewp_claim_mastery_outbox(900)")
    # The mastery drain independently derives the SAME exam from the study task.
    assert oc["exam_id"] == _EXAM
    ev = {
        "user_id": oc["user_id"], "exam_id": oc["exam_id"], "topic_id": oc["topic_id"],
        "microtopic_id": oc.get("microtopic_id"), "source_type": "sentence_drill",
        "source_entity_id": oc["source_entity_id"], "evaluation_id": oc["evaluation_id"],
        "issue_projection_id": None, "evidence_tier": "production", "score": None,
        "confidence": None, "evidence_op": "assert", "evidence_key": oc["idempotency_key"],
    }
    sh = {**{k: ev[k] for k in ev if k != "evidence_op"}, "delta_json": {}}
    out = _json(
        f"SELECT ewp_complete_mastery_outbox('{oc['id']}','{oc['claim_token']}',"
        f"'{json.dumps(ev)}'::jsonb,'{json.dumps(sh)}'::jsonb)")
    assert out["status"] == "done" and out["wrote_evidence"] is True
    # Evidence persisted with the exam derived from the study task — proving the
    # server-side re-derived context (ewp_outbox_evidence_context) agrees, since
    # ewp_complete_mastery_outbox rejects any exam mismatch against it.
    assert _scalar(
        f"SELECT exam_id FROM user_topic_mastery_evidence WHERE evidence_key='{oc['idempotency_key']}'") == _EXAM
