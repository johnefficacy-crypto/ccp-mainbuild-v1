"""Behavioural integration test for the EWP-2B evaluator RPCs (migration 208).

Applies migrations 205 + 207 + 208 to a real Postgres and drives the async
evaluator contract end-to-end: claim (FOR UPDATE SKIP LOCKED + lease + token),
atomic complete (issue events + backend lineage/microtopic + race-safe automatic
projection + evaluation terminalisation + unit transition + mastery-outbox
enqueue + session rollup), fencing rejection, retry/terminal_partial, stale-lease
sweep, and the mastery-outbox drain writing idempotent evidence + shadow rows.

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

_FIXTURES = f"""
INSERT INTO exams(id) VALUES ('00000000-0000-0000-0000-0000000000e1') ON CONFLICT DO NOTHING;
INSERT INTO profiles(id) VALUES ('{_A}') ON CONFLICT DO NOTHING;
INSERT INTO writing_prompts(id,exam_id,subject_id,topic_id,microtopic_id,exercise_type,prompt_text,difficulty_level,reviewer_status,is_active,required_sentence_count)
  SELECT '{_PROMPT}','00000000-0000-0000-0000-0000000000e1',
    (SELECT id FROM subjects WHERE slug='english-language'),(SELECT id FROM topics WHERE slug='grammar'),
    (SELECT id FROM topics WHERE level='microtopic' LIMIT 1),'sentence_construction','write',1,'verified',true,1
  WHERE NOT EXISTS (SELECT 1 FROM writing_prompts WHERE id='{_PROMPT}');
"""

_CH = "a" * 64


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


@pytest.fixture(scope="module", autouse=True)
def _apply():
    _psql(_BOOTSTRAP)
    _psql_file(_MIG / "205_english_writing_practice_schema.sql")
    _psql_file(_MIG / "207_english_writing_practice_rpcs.sql")
    _psql_file(_MIG / "208_english_writing_practice_evaluator.sql")
    _psql(_FIXTURES)
    yield


def _drain_pending() -> None:
    """Complete every currently-pending language job so a test's freshly created
    job is the sole/oldest pending one (the claim RPC is global-oldest)."""
    for _ in range(50):
        raw = _scalar("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
        if not raw:
            break
        c = json.loads(raw)
        _scalar(
            f"SELECT ewp_complete_language_evaluation('{c['job_id']}','{c['claim_token']}',"
            f"'v','[]'::jsonb,'{{}}'::jsonb,NULL,false,'off',NULL)")


def _new_submitted_session(answer: str, ch: str) -> str:
    _drain_pending()
    sid = _scalar(
        f"SELECT (ewp_create_writing_session('{_A}','{_PROMPT}',NULL,'learning',1,'immediate',"
        f"NULL,1,(SELECT id FROM topics WHERE level='microtopic' LIMIT 1),"
        "'{\"schema_version\":1}'::jsonb))->>'id'")
    _scalar(
        f"SELECT ewp_submit_writing_unit('{_A}','{sid}',1,'{answer}',3,3,'{ch}',1,'{{}}'::jsonb,'det-v1')")
    return sid


def test_submit_enqueues_a_pending_language_job():
    sid = _new_submitted_session("hello world here", "b" * 64)
    row = _scalar(
        f"SELECT j.status||'/'||j.job_kind||'/'||e.language_status FROM writing_evaluation_jobs j "
        f"JOIN writing_evaluations e ON e.id=j.evaluation_id "
        f"JOIN writing_unit_versions v ON v.id=e.unit_version_id "
        f"JOIN writing_session_units u ON u.id=v.unit_id WHERE u.session_id='{sid}'")
    assert row == "pending/language_evaluation/queued"


def test_claim_stamps_lease_and_token_and_marks_running():
    sid = _new_submitted_session("claim me now", "c" * 64)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    assert claim["is_current"] is True and claim["claim_token"]
    assert claim["active_prior_issues"] == [] and claim["exercise_type"] == "sentence_construction"
    row = _scalar(
        f"SELECT status||'/'||(claim_token IS NOT NULL)||'/'||(locked_at IS NOT NULL) "
        f"FROM writing_evaluation_jobs WHERE id='{claim['job_id']}'")
    assert row == "running/true/true"
    # cleanup: leave it claimed (other tests create their own sessions)


def test_complete_with_must_fix_writes_issue_projection_and_transitions():
    sid = _new_submitted_session("they is here", "d" * 64)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    issues = json.dumps([{
        "issue_type": "subject_verb_agreement", "span_start_utf16": 0, "span_end_utf16": 7,
        "quoted_text": "they is", "original_text": "they is", "suggested_text": "they are",
        "explanation": "plural subject", "severity": "must_fix", "predecessor_issue_event_id": None,
    }])
    out = _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','{issues}'::jsonb,'{{\"issues\":1}}'::jsonb,NULL,false,'off',NULL)")
    assert out["status"] == "completed" and out["unit_status"] == "rewrite_required"
    eid = claim["evaluation_id"]
    assert _scalar(
        f"SELECT issue_type||'/'||severity||'/'||(microtopic_id IS NOT NULL) "
        f"FROM writing_issue_events WHERE evaluation_id='{eid}'") == "subject_verb_agreement/must_fix/true"
    assert _scalar(
        f"SELECT projection_kind||'/'||prior_occurrence_count FROM writing_issue_projections p "
        f"JOIN writing_issue_events i ON i.id=p.issue_event_id WHERE i.evaluation_id='{eid}'") == "automatic/0"
    assert _scalar(f"SELECT language_status||'/'||overall_status FROM writing_evaluations WHERE id='{eid}'") == "completed/completed"
    assert _scalar(f"SELECT status FROM writing_evaluation_jobs WHERE evaluation_id='{eid}'") == "done"


def test_complete_enqueues_mastery_outbox_only_in_shadow_or_live():
    sid = _new_submitted_session("clean sentence text", "e" * 64)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    key = "f" * 64
    _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','[]'::jsonb,'{{}}'::jsonb,NULL,false,'shadow','{key}')")
    assert _scalar(
        f"SELECT status||'/'||mastery_flag_state FROM writing_mastery_outbox WHERE idempotency_key='{key}'") == "pending/shadow"


def test_fencing_rejects_a_stale_token():
    sid = _new_submitted_session("fence me here", "1" * 64)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    _psql(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}',"
        f"'00000000-0000-0000-0000-000000000000','v','[]'::jsonb,'{{}}'::jsonb,NULL,false,'off',NULL)",
        expect_ok=False)
    # the genuine token still works
    out = _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','[]'::jsonb,'{{}}'::jsonb,NULL,false,'off',NULL)")
    assert out["status"] == "completed"


def test_retry_then_terminal_partial():
    sid = _new_submitted_session("terminal path here", "2" * 64)
    # fail three times (max_attempts=3); each claim increments attempts.
    for i in range(3):
        claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
        out = _json(
            f"SELECT ewp_fail_evaluation_job('{claim['job_id']}','{claim['claim_token']}','boom',0)")
        if i < 2:
            assert out["status"] == "requeued"
    assert out["status"] == "failed_terminal" and out["overall_status"] == "terminal_partial"
    # deterministic-complete → unit ready with a usable partial result.
    assert _scalar(
        f"SELECT status FROM writing_session_units WHERE session_id='{sid}'") == "ready"
    assert _scalar(f"SELECT evaluation_outcome FROM writing_sessions WHERE id='{sid}'") == "deterministic_only"


def test_sweep_reclaims_expired_lease():
    sid = _new_submitted_session("sweep this one", "3" * 64)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    _psql(f"UPDATE writing_evaluation_jobs SET locked_at = now() - interval '2 hours' WHERE id='{claim['job_id']}'")
    assert int(_scalar("SELECT ewp_sweep_stale_evaluation_jobs(900)")) >= 1
    assert _scalar(f"SELECT status FROM writing_evaluation_jobs WHERE id='{claim['job_id']}'") == "pending"
    # a stale worker completing now is fenced out (token cleared on sweep).
    _psql(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'v','[]'::jsonb,'{{}}'::jsonb,NULL,false,'off',NULL)", expect_ok=False)


def test_claim_and_drain_expose_microtopic_under_identical_key():
    # Guards the mastery idempotency-key parity: the evaluation-claim payload and
    # the mastery-outbox-claim payload must expose the unit microtopic under the
    # SAME field name ('microtopic_id'), with the same value, so the worker's
    # predicted key equals the drain-derived evidence key (a microtopic-bearing
    # unit — the common learning-mode case).
    sid = _new_submitted_session("microtopic parity text", "6" * 64)
    ce = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    assert ce.get("microtopic_id"), "claim payload must expose a non-null microtopic_id"
    _json(
        f"SELECT ewp_complete_language_evaluation('{ce['job_id']}','{ce['claim_token']}',"
        f"'lang-mock-v1','[]'::jsonb,'{{}}'::jsonb,NULL,false,'shadow','{'7' * 64}')")
    oc = _json("SELECT ewp_claim_mastery_outbox(900)")
    assert oc["microtopic_id"] == ce["microtopic_id"]


def test_mastery_outbox_drain_writes_evidence_and_shadow():
    sid = _new_submitted_session("mastery drain text", "4" * 64)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    key = "5" * 64
    _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','[]'::jsonb,'{{}}'::jsonb,NULL,false,'shadow','{key}')")
    oc = _json("SELECT ewp_claim_mastery_outbox(900)")
    assert oc["mastery_flag_state"] == "shadow" and oc["overall_status"] == "completed"
    key = oc["idempotency_key"]  # act on the row actually claimed (global-oldest)
    # a clean unit (no must_fix) → production evidence tier.
    ev = {
        "user_id": oc["user_id"], "exam_id": oc.get("exam_id"), "topic_id": oc["topic_id"],
        "microtopic_id": oc.get("microtopic_id"), "source_type": "sentence_drill",
        "source_entity_id": oc["source_entity_id"], "evaluation_id": oc["evaluation_id"],
        "issue_projection_id": None, "evidence_tier": "production", "score": None,
        "confidence": None, "evidence_op": "assert", "evidence_key": key,
    }
    sh = {**{k: ev[k] for k in ev if k != "evidence_op"}, "delta_json": {}}
    out = _json(
        f"SELECT ewp_complete_mastery_outbox('{oc['id']}','{oc['claim_token']}',"
        f"'{json.dumps(ev)}'::jsonb,'{json.dumps(sh)}'::jsonb)")
    assert out["status"] == "done" and out["wrote_evidence"] is True
    assert _scalar(f"SELECT evidence_tier FROM user_topic_mastery_evidence WHERE evidence_key='{key}'") == "production"
    assert _scalar(f"SELECT evidence_tier FROM writing_mastery_shadow WHERE evidence_key='{key}'") == "production"
    assert _scalar(f"SELECT status FROM writing_mastery_outbox WHERE id='{oc['id']}'") == "done"
    # idempotent re-drain would not duplicate (unique evidence_key).
    assert _scalar(f"SELECT count(*) FROM user_topic_mastery_evidence WHERE evidence_key='{key}'") == "1"


def _unit_id(sid: str) -> str:
    return _scalar(f"SELECT id FROM writing_session_units WHERE session_id='{sid}'")


def test_stale_version_suppresses_projections_and_rollup():
    # v1 job pending; append a NEWER version so v1 is stale before it is completed.
    sid = _new_submitted_session("stale version text", "8" * 64)
    unit = _unit_id(sid)
    _psql(
        "INSERT INTO writing_unit_versions(unit_id,version_number,answer_text,content_hash,submission_kind) "
        f"VALUES ('{unit}',2,'newer text here','{'9' * 64}','user')")
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    assert claim["is_current"] is False
    issues = json.dumps([{
        "issue_type": "subject_verb_agreement", "span_start_utf16": 0, "span_end_utf16": 4,
        "quoted_text": "text", "original_text": "text", "suggested_text": "text",
        "explanation": "x", "severity": "must_fix", "predecessor_issue_event_id": None,
    }])
    out = _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','{issues}'::jsonb,'{{}}'::jsonb,NULL,false,'off',NULL)")
    eid = claim["evaluation_id"]
    assert _scalar(
        f"SELECT affects_current_state FROM writing_issue_events WHERE evaluation_id='{eid}'") == "f"
    assert _scalar(
        f"SELECT count(*) FROM writing_issue_projections p "
        f"JOIN writing_issue_events i ON i.id=p.issue_event_id WHERE i.evaluation_id='{eid}'") == "0"
    assert _scalar(f"SELECT status FROM writing_session_units WHERE id='{unit}'") == "evaluation_pending"
    assert _scalar(f"SELECT status FROM writing_evaluation_jobs WHERE evaluation_id='{eid}'") == "done"


def test_sweep_terminalizes_exhausted_lease():
    sid = _new_submitted_session("exhausted lease text", "a1" + "0" * 62)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    job = claim["job_id"]
    _psql(
        f"UPDATE writing_evaluation_jobs SET attempts=max_attempts, "
        f"locked_at=now()-interval '2 hours' WHERE id='{job}'")
    assert int(_scalar("SELECT ewp_sweep_stale_evaluation_jobs(900)")) >= 1
    assert _scalar(f"SELECT status FROM writing_evaluation_jobs WHERE id='{job}'") == "failed"
    eid = claim["evaluation_id"]
    assert _scalar(f"SELECT overall_status FROM writing_evaluations WHERE id='{eid}'") == "terminal_partial"
    assert _scalar(f"SELECT status FROM writing_session_units WHERE session_id='{sid}'") == "ready"
    assert _scalar(
        "SELECT count(*) FROM writing_evaluation_jobs WHERE status='pending' AND attempts > max_attempts") == "0"


def test_mastery_outbox_fencing_and_payload_validation():
    sid = _new_submitted_session("fencing payload text", "a2" + "0" * 62)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','[]'::jsonb,'{{}}'::jsonb,NULL,false,'shadow','{'a3' + '0' * 62}')")
    oc = _json("SELECT ewp_claim_mastery_outbox(900)")
    key = oc["idempotency_key"]
    ev = {
        "user_id": oc["user_id"], "exam_id": oc.get("exam_id"), "topic_id": oc["topic_id"],
        "microtopic_id": oc.get("microtopic_id"), "source_type": "sentence_drill",
        "source_entity_id": oc["source_entity_id"], "evaluation_id": oc["evaluation_id"],
        "issue_projection_id": None, "evidence_tier": "production", "score": None,
        "confidence": None, "evidence_op": "assert", "evidence_key": key,
    }
    sh = {**{k: ev[k] for k in ev if k != "evidence_op"}, "delta_json": {}}
    # (a) wrong token → fencing failure.
    p = _psql(
        f"SELECT ewp_complete_mastery_outbox('{oc['id']}',"
        f"'00000000-0000-0000-0000-000000000000','{json.dumps(ev)}'::jsonb,'{json.dumps(sh)}'::jsonb)",
        expect_ok=False)
    assert "ewp_outbox_fencing_failed" in p.stderr
    # (b) right token but mismatched user_id → payload mismatch.
    bad = {**ev, "user_id": "00000000-0000-0000-0000-0000000000bb"}
    bad_sh = {**{k: bad[k] for k in bad if k != "evidence_op"}, "delta_json": {}}
    p = _psql(
        f"SELECT ewp_complete_mastery_outbox('{oc['id']}','{oc['claim_token']}',"
        f"'{json.dumps(bad)}'::jsonb,'{json.dumps(bad_sh)}'::jsonb)", expect_ok=False)
    assert "ewp_outbox_payload_mismatch" in p.stderr
    # (c) correct payload → done, evidence + shadow written.
    out = _json(
        f"SELECT ewp_complete_mastery_outbox('{oc['id']}','{oc['claim_token']}',"
        f"'{json.dumps(ev)}'::jsonb,'{json.dumps(sh)}'::jsonb)")
    assert out["status"] == "done" and out["wrote_evidence"] is True
    assert _scalar(f"SELECT evidence_tier FROM user_topic_mastery_evidence WHERE evidence_key='{key}'") == "production"
    assert _scalar(f"SELECT evidence_tier FROM writing_mastery_shadow WHERE evidence_key='{key}'") == "production"


def test_mastery_outbox_stale_sweep_reclaims():
    sid = _new_submitted_session("outbox stale text", "a4" + "0" * 62)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','[]'::jsonb,'{{}}'::jsonb,NULL,false,'shadow','{'a5' + '0' * 62}')")
    oc = _json("SELECT ewp_claim_mastery_outbox(900)")
    _psql(
        f"UPDATE writing_mastery_outbox SET locked_at=now()-interval '2 hours' WHERE id='{oc['id']}'")
    assert int(_scalar("SELECT ewp_sweep_stale_mastery_outbox(900)")) >= 1
    assert _scalar(f"SELECT status FROM writing_mastery_outbox WHERE id='{oc['id']}'") == "pending"


def test_review_correction_outbox_left_pending():
    # An evaluation with an issue we can hang a review event off of.
    sid = _new_submitted_session("review correction text", "a6" + "0" * 62)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    issues = json.dumps([{
        "issue_type": "subject_verb_agreement", "span_start_utf16": 0, "span_end_utf16": 4,
        "quoted_text": "text", "original_text": "text", "suggested_text": "text",
        "explanation": "x", "severity": "must_fix", "predecessor_issue_event_id": None,
    }])
    _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','{issues}'::jsonb,'{{}}'::jsonb,NULL,false,'off',NULL)")
    eid = claim["evaluation_id"]
    issue = _scalar(f"SELECT id FROM writing_issue_events WHERE evaluation_id='{eid}' LIMIT 1")
    _psql(
        "INSERT INTO writing_issue_review_events(issue_event_id,decision,reviewer_type) "
        f"VALUES ('{issue}','invalidated','system')")
    rev = _scalar(
        f"SELECT id FROM writing_issue_review_events WHERE issue_event_id='{issue}' LIMIT 1")
    _psql(
        "INSERT INTO writing_mastery_outbox(source_kind,review_event_id,evidence_op,user_id,"
        "mastery_flag_state,idempotency_key,status) "
        f"VALUES ('review_correction','{rev}','retract','{_A}','shadow','{'a7' + '0' * 62}','pending')")
    raw = _scalar("SELECT ewp_claim_mastery_outbox(900)")
    if raw:
        claimed = json.loads(raw)
        assert claimed["idempotency_key"] != ("a7" + "0" * 62)
    assert _scalar(
        f"SELECT status FROM writing_mastery_outbox WHERE idempotency_key='{'a7' + '0' * 62}'") == "pending"


def test_projection_has_canonical_error_type():
    sid = _new_submitted_session("canonical error text", "a8" + "0" * 62)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    issues = json.dumps([{
        "issue_type": "subject_verb_agreement", "span_start_utf16": 0, "span_end_utf16": 4,
        "quoted_text": "text", "original_text": "text", "suggested_text": "text",
        "explanation": "x", "severity": "must_fix", "predecessor_issue_event_id": None,
    }])
    _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','{issues}'::jsonb,'{{}}'::jsonb,NULL,false,'off',NULL)")
    eid = claim["evaluation_id"]
    row = _scalar(
        f"SELECT canonical_error_type||'/'||(projection_confidence IS NOT NULL) "
        f"FROM writing_issue_projections p JOIN writing_issue_events i ON i.id=p.issue_event_id "
        f"WHERE i.evaluation_id='{eid}'")
    assert row == "careless/true"
