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


def _evidence_key(*, evidence_op: str, user_id: str, evaluation_id: str,
                  issue_projection_id: str | None, microtopic_id: str | None,
                  evidence_tier: str, source_type: str,
                  review_event_id: str | None = None) -> str:
    """The §4.12b evidence key, computed via the shared SQL helper so the outbox
    completion's RE-DERIVED key (bound to the claimed evaluation's context)
    matches the payload key exactly. Real workers derive this from
    evidence_deriver.compute_evidence_key (byte-identical, asserted elsewhere)."""
    def q(v):  # 'NULL' or a quoted literal
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
    _psql_file(_MIG / "208_english_writing_practice_evaluator.sql")
    _psql(_FIXTURES)
    yield


def _drain_pending() -> None:
    """Complete every currently-pending language job AND every pending mastery
    outbox row so a test's freshly created job/outbox is the sole/oldest pending
    one (both claim RPCs are global-oldest). Outbox rows are acked as no-ops
    (p_evidence=NULL) — no evidence key needed to clear the backlog."""
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
    key = _evidence_key(
        evidence_op="assert", user_id=_A, evaluation_id=ce["evaluation_id"],
        issue_projection_id=None, microtopic_id=ce.get("microtopic_id"),
        evidence_tier="production", source_type="sentence_drill")
    _json(
        f"SELECT ewp_complete_language_evaluation('{ce['job_id']}','{ce['claim_token']}',"
        f"'lang-mock-v1','[]'::jsonb,'{{}}'::jsonb,NULL,false,'shadow','{key}')")
    oc = _json("SELECT ewp_claim_mastery_outbox(900)")
    assert oc["microtopic_id"] == ce["microtopic_id"]
    # Complete it so it does not linger as an unprocessed global-oldest row for a
    # later drain test (the claim RPC is global-oldest).
    ev = {
        "user_id": oc["user_id"], "exam_id": oc.get("exam_id"), "topic_id": oc["topic_id"],
        "microtopic_id": oc.get("microtopic_id"), "source_type": "sentence_drill",
        "source_entity_id": oc["source_entity_id"], "evaluation_id": oc["evaluation_id"],
        "issue_projection_id": None, "evidence_tier": "production", "score": None,
        "confidence": None, "evidence_op": "assert", "evidence_key": oc["idempotency_key"],
    }
    sh = {**{k: ev[k] for k in ev if k != "evidence_op"}, "delta_json": {}}
    _json(
        f"SELECT ewp_complete_mastery_outbox('{oc['id']}','{oc['claim_token']}',"
        f"'{json.dumps(ev)}'::jsonb,'{json.dumps(sh)}'::jsonb)")


def test_mastery_outbox_drain_writes_evidence_and_shadow():
    sid = _new_submitted_session("mastery drain text", "4" * 64)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    # Enqueue with the GENUINE §4.12b evidence key (a clean unit → production tier,
    # no projection, unit microtopic) so the outbox completion's re-derived key
    # binding is satisfied. (The trust-boundary hardening rejects synthetic keys.)
    key = _evidence_key(
        evidence_op="assert", user_id=_A, evaluation_id=claim["evaluation_id"],
        issue_projection_id=None, microtopic_id=claim.get("microtopic_id"),
        evidence_tier="production", source_type="sentence_drill")
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
    key0 = _evidence_key(
        evidence_op="assert", user_id=_A, evaluation_id=claim["evaluation_id"],
        issue_projection_id=None, microtopic_id=claim.get("microtopic_id"),
        evidence_tier="production", source_type="sentence_drill")
    _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','[]'::jsonb,'{{}}'::jsonb,NULL,false,'shadow','{key0}')")
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
    # §6: subject_verb_agreement projects to concept_gap on BOTH first and repeat
    # occurrences (a construction/usage error, never 'careless').
    assert row == "concept_gap/true"


# ---------------------------------------------------------------------------
# Round-2 review additions: regression lineage (§4.9), generation+1 recovery
# (§4.14), corruption hard-fail (§8.1), microtopic English-tree trust boundary
# (§5.3/§4.15), and a concurrent sweeper-vs-completion race (§8.0).
# ---------------------------------------------------------------------------

def _issue(issue_type: str, quoted: str, severity: str = "must_fix",
           predecessor: str | None = None) -> dict:
    return {
        "issue_type": issue_type, "span_start_utf16": 0, "span_end_utf16": len(quoted),
        "quoted_text": quoted, "original_text": quoted, "suggested_text": quoted,
        "explanation": "x", "severity": severity, "predecessor_issue_event_id": predecessor,
    }


def _claim_complete(issues: list[dict]) -> str:
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','{json.dumps(issues)}'::jsonb,'{{}}'::jsonb,NULL,false,'off',NULL)")
    return claim["evaluation_id"]


def _rewrite(sid: str, answer: str, ch: str, version: int) -> None:
    _scalar(
        f"SELECT ewp_submit_writing_unit('{_A}','{sid}',1,'{answer}',3,3,'{ch}',{version},"
        "'{}'::jsonb,'det-v1')")


def test_regressed_lineage_reuses_resolved_lineage_and_emits_regressed_event():
    # v1: SVA (must_fix) + spelling (must_fix) → unit rewrite_required.
    sid = _new_submitted_session("regress base text", "c1" + "0" * 62)
    e1 = _claim_complete([_issue("subject_verb_agreement", "they is"),
                          _issue("spelling", "teh")])
    sva1 = _scalar(
        f"SELECT id FROM writing_issue_events WHERE evaluation_id='{e1}' "
        "AND issue_type='subject_verb_agreement'")
    lineage = _scalar(f"SELECT lineage_id FROM writing_issue_events WHERE id='{sva1}'")

    # v2 rewrite: SVA gone (resolved), spelling remains (keeps rewrite_required).
    _rewrite(sid, "regress v2 text", "c2" + "0" * 62, 2)
    e2 = _claim_complete([_issue("spelling", "teh")])
    assert _scalar(
        f"SELECT outcome FROM writing_issue_resolution_events WHERE issue_event_id='{sva1}'") == "resolved"

    # v3 rewrite: SVA REAPPEARS (no predecessor supplied) → regression of lineage.
    _rewrite(sid, "regress v3 text", "c3" + "0" * 62, 3)
    e3 = _claim_complete([_issue("subject_verb_agreement", "they is"),
                          _issue("spelling", "teh")])
    sva3 = _scalar(
        f"SELECT id FROM writing_issue_events WHERE evaluation_id='{e3}' "
        "AND issue_type='subject_verb_agreement'")
    # The reappearing issue reuses the ORIGINAL resolved lineage id.
    assert _scalar(f"SELECT lineage_id FROM writing_issue_events WHERE id='{sva3}'") == lineage
    # A 'regressed' resolution event links the resolved issue → the new successor.
    assert _scalar(
        f"SELECT outcome||'/'||(successor_issue_event_id='{sva3}') "
        f"FROM writing_issue_resolution_events WHERE successor_issue_event_id='{sva3}' "
        "AND outcome='regressed'") == "regressed/true"


def test_persisted_never_points_at_a_fresh_lineage_successor():
    # v1: SVA must_fix. v2 rewrite: SVA quote changes AND a genuinely new SVA
    # appears; the fallback must not mark the prior 'persisted' against a
    # different-lineage row. With the quote changed and no predecessor supplied,
    # the prior is resolved (its lineage is not carried by the new fresh issue).
    sid = _new_submitted_session("persist base text", "c4" + "0" * 62)
    e1 = _claim_complete([_issue("subject_verb_agreement", "they is")])
    sva1 = _scalar(f"SELECT id FROM writing_issue_events WHERE evaluation_id='{e1}'")
    lin1 = _scalar(f"SELECT lineage_id FROM writing_issue_events WHERE id='{sva1}'")

    _rewrite(sid, "persist v2 text", "c5" + "0" * 62, 2)
    e2 = _claim_complete([_issue("subject_verb_agreement", "we was")])  # different quote
    new = _scalar(f"SELECT id FROM writing_issue_events WHERE evaluation_id='{e2}'")
    lin2 = _scalar(f"SELECT lineage_id FROM writing_issue_events WHERE id='{new}'")
    # The new issue carries a FRESH lineage (not the prior's).
    assert lin2 != lin1
    # The prior is 'resolved' — NOT 'persisted' pointing at the fresh-lineage row.
    res = _scalar(
        f"SELECT outcome||'/'||COALESCE(successor_issue_event_id::text,'-') "
        f"FROM writing_issue_resolution_events WHERE issue_event_id='{sva1}'")
    assert res == "resolved/-"


def test_recover_evaluation_mints_generation_2_and_requeues():
    sid = _new_submitted_session("recover base text", "c6" + "0" * 62)
    # Drive the job to terminal failure (max_attempts=3).
    for _ in range(3):
        claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
        out = _json(
            f"SELECT ewp_fail_evaluation_job('{claim['job_id']}','{claim['claim_token']}','boom',0)")
    assert out["status"] == "failed_terminal"
    eid = claim["evaluation_id"]
    # language_status is 'failed' after terminalisation.
    assert _scalar(f"SELECT language_status FROM writing_evaluations WHERE id='{eid}'") == "failed"

    rec = _json(f"SELECT ewp_recover_evaluation('{eid}')")
    assert rec["status"] == "recovered" and rec["generation"] == 2
    # a fresh pending gen=2 language job exists, attempts reset.
    assert _scalar(
        f"SELECT status||'/'||generation||'/'||attempts FROM writing_evaluation_jobs "
        f"WHERE evaluation_id='{eid}' AND generation=2") == "pending/2/0"
    # CAS moved the envelope back to queued.
    assert _scalar(f"SELECT language_status FROM writing_evaluations WHERE id='{eid}'") == "queued"
    # a second recovery is a no-op (latest job is pending, not failed).
    assert _json(f"SELECT ewp_recover_evaluation('{eid}')")["status"] == "noop"


def test_reject_corrupt_version_fails_closed_regardless_of_deterministic():
    # Deterministic completed (submit path sets deterministic_status='completed'),
    # yet a corruption reject must NOT yield terminal_partial/ready — it must be
    # overall_status='failed' and unit 'evaluation_failed'.
    sid = _new_submitted_session("corrupt fail text", "c7" + "0" * 62)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    assert _scalar(
        f"SELECT deterministic_status FROM writing_evaluations WHERE id='{claim['evaluation_id']}'") == "completed"
    out = _json(
        f"SELECT ewp_reject_corrupt_version('{claim['job_id']}','{claim['claim_token']}','content_hash_mismatch')")
    assert out["status"] == "rejected_corrupt" and out["overall_status"] == "failed"
    eid = claim["evaluation_id"]
    assert _scalar(f"SELECT overall_status FROM writing_evaluations WHERE id='{eid}'") == "failed"
    assert _scalar(f"SELECT status FROM writing_session_units WHERE session_id='{sid}'") == "evaluation_failed"
    # NOT ready — a corrupt version never becomes a usable result.
    assert _scalar(f"SELECT status FROM writing_session_units WHERE session_id='{sid}'") != "ready"


def test_microtopic_map_outside_english_tree_is_dropped_to_topic_level():
    # Point the SVA active map row at a microtopic in a NON-English subject. The
    # resolver must refuse it and store microtopic_id = NULL (topic-level).
    _psql(
        "INSERT INTO subjects(id,slug,name) VALUES "
        "('00000000-0000-0000-0000-0000000000f1','maths','Maths') ON CONFLICT DO NOTHING")
    _psql(
        "INSERT INTO topics(id,subject_id,slug,name,level,is_active) VALUES "
        "('00000000-0000-0000-0000-0000000000f2','00000000-0000-0000-0000-0000000000f1',"
        "'algebra-mt','Algebra','microtopic',true) ON CONFLICT DO NOTHING")
    # Remap the active SVA mapping to the foreign microtopic (versioned flip).
    _psql(
        "UPDATE writing_issue_type_microtopic_map SET is_active=false "
        "WHERE issue_type='subject_verb_agreement' AND is_active=true")
    _psql(
        "INSERT INTO writing_issue_type_microtopic_map(issue_type,microtopic_id,map_version,is_active) "
        "VALUES ('subject_verb_agreement','00000000-0000-0000-0000-0000000000f2',99,true)")
    try:
        sid = _new_submitted_session("foreign map text", "c8" + "0" * 62)
        e1 = _claim_complete([_issue("subject_verb_agreement", "they is")])
        assert _scalar(
            f"SELECT (microtopic_id IS NULL) FROM writing_issue_events WHERE evaluation_id='{e1}'") == "t"
    finally:
        # restore the English mapping so later tests keep a valid microtopic, and
        # remove the foreign subject/topic so shared-DB seed-count assertions in
        # other suites stay exact.
        _psql(
            "UPDATE writing_issue_type_microtopic_map SET is_active=false WHERE map_version=99")
        _psql(
            "UPDATE writing_issue_type_microtopic_map SET is_active=true "
            "WHERE issue_type='subject_verb_agreement' AND map_version=1")
        _psql(
            "DELETE FROM writing_issue_type_microtopic_map WHERE map_version=99")
        _psql("DELETE FROM topics WHERE id='00000000-0000-0000-0000-0000000000f2'")
        _psql("DELETE FROM subjects WHERE id='00000000-0000-0000-0000-0000000000f1'")


def test_concurrent_sweeper_vs_completion_no_deadlock_exactly_once():
    # Two REAL connections (two independent psql processes run in parallel — no
    # Python DB driver needed, mirroring CI which only ships psql): a worker
    # committing a claimed (running) job whose lease we expire, and a sweeper. The
    # sweeper's session-first RE-VALIDATING requeue must NOT deadlock against the
    # worker's completion (which also locks session-first), and the job must be
    # terminalised/completed EXACTLY once (the fencing token guarantees a single
    # side-effecting writer).
    import concurrent.futures as cf

    sid = _new_submitted_session("concurrent sweep text", "c9" + "0" * 62)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    job = claim["job_id"]
    tok = claim["claim_token"]
    # Expire the lease so the sweeper considers it stale.
    _psql(f"UPDATE writing_evaluation_jobs SET locked_at = now() - interval '2 hours' WHERE id='{job}'")

    def _run(sql: str) -> tuple[int, str]:
        proc = subprocess.run([_PSQL, _DSN, "-X", "-q", "-c", sql],
                              capture_output=True, text=True)
        return proc.returncode, (proc.stdout + proc.stderr)

    completion_sql = (
        f"SELECT ewp_complete_language_evaluation('{job}','{tok}','lang-mock-v1',"
        "'[]'::jsonb,'{}'::jsonb,NULL,false,'off',NULL)")
    sweep_sql = "SELECT ewp_sweep_stale_evaluation_jobs(900)"

    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        results = [f.result(timeout=30) for f in
                   (ex.submit(_run, completion_sql), ex.submit(_run, sweep_sql))]

    # No deadlock: neither process reported a deadlock error.
    for _rc, out in results:
        assert "deadlock" not in out.lower(), f"deadlock detected: {out}"

    # Exactly-once terminalisation: the job ends in a single terminal state and
    # the unit is not left half-transitioned. Depending on who won the race the
    # job is 'done' (completion won) or 'pending'/'failed' (sweeper requeued), but
    # never both applied — the fencing token guarantees a single side-effecting
    # writer. The evaluation has exactly one row and a single coherent status.
    status = _scalar(f"SELECT status FROM writing_evaluation_jobs WHERE id='{job}'")
    assert status in ("done", "pending", "failed")
    eid = claim["evaluation_id"]
    # If completion won, envelope is completed; if sweeper requeued, it is queued
    # again (running reset). Never a mixed/duplicate terminal application.
    lang = _scalar(f"SELECT language_status FROM writing_evaluations WHERE id='{eid}'")
    assert lang in ("completed", "queued", "failed", "running")
    assert _scalar(f"SELECT count(*) FROM writing_evaluations WHERE id='{eid}'") == "1"


# ---------------------------------------------------------------------------
# EWP-2B finish: per-issue projection-linked evidence (§4.12/§10.1) and the
# serialized review-correction apply pipeline (§4.12c).
# ---------------------------------------------------------------------------

def _mk_evidence_dict(*, op, user, exam, topic, micro, source_type, source_entity,
                      evaluation, tier, projection, key, review=None, supersedes=None):
    ev = {
        "user_id": user, "exam_id": exam, "topic_id": topic, "microtopic_id": micro,
        "source_type": source_type, "source_entity_id": source_entity,
        "evaluation_id": evaluation, "issue_projection_id": projection,
        "evidence_tier": tier, "score": None, "confidence": None,
        "evidence_op": op, "evidence_key": key,
    }
    if review is not None:
        ev["review_event_id"] = review
    if supersedes is not None:
        ev["supersedes_evidence_key"] = supersedes
    sh = {k: ev[k] for k in ev if k not in ("evidence_op", "review_event_id", "supersedes_evidence_key")}
    sh["delta_json"] = {}
    return ev, sh


def _drain_batch(oc, unit_tier="production"):
    """Build + apply the batch payload the worker would produce for a claimed
    evaluation outbox row: the unit-level row plus one row per issue projection."""
    pairs = []
    unit_ev, unit_sh = _mk_evidence_dict(
        op="assert", user=oc["user_id"], exam=oc.get("exam_id"), topic=oc["topic_id"],
        micro=oc.get("microtopic_id"), source_type="sentence_drill",
        source_entity=oc["source_entity_id"], evaluation=oc["evaluation_id"],
        tier=unit_tier, projection=None, key=oc["idempotency_key"])
    pairs.append({"evidence": unit_ev, "shadow": unit_sh})
    per = {}
    for proj in oc.get("issue_projections") or []:
        k = _evidence_key(
            evidence_op="assert", user_id=oc["user_id"], evaluation_id=oc["evaluation_id"],
            issue_projection_id=proj["issue_projection_id"], microtopic_id=proj.get("microtopic_id"),
            evidence_tier=proj["evidence_tier"], source_type="sentence_drill")
        ev, sh = _mk_evidence_dict(
            op="assert", user=oc["user_id"], exam=oc.get("exam_id"), topic=oc["topic_id"],
            micro=proj.get("microtopic_id"), source_type="sentence_drill",
            source_entity=oc["source_entity_id"], evaluation=oc["evaluation_id"],
            tier=proj["evidence_tier"], projection=proj["issue_projection_id"], key=k)
        pairs.append({"evidence": ev, "shadow": sh})
        per[proj["issue_projection_id"]] = {"key": k, "tier": proj["evidence_tier"],
                                            "micro": proj.get("microtopic_id")}
    out = _json(
        f"SELECT ewp_complete_mastery_outbox_batch('{oc['id']}','{oc['claim_token']}',"
        f"'{json.dumps(pairs)}'::jsonb)")
    return out, per


def _seed_issue_assert(answer, ch, issue_type, severity="should_fix"):
    """Produce a projection-linked ASSERT evidence row for one issue and return
    its context (evaluation, issue, projection, evidence_key, ...)."""
    sid = _new_submitted_session(answer, ch)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    micro = claim.get("microtopic_id")
    unit_key = _evidence_key(
        evidence_op="assert", user_id=_A, evaluation_id=claim["evaluation_id"],
        issue_projection_id=None, microtopic_id=micro,
        evidence_tier="production", source_type="sentence_drill")
    issues = json.dumps([_issue(issue_type, "quote", severity)])
    _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','{issues}'::jsonb,'{{}}'::jsonb,NULL,false,'shadow','{unit_key}')")
    oc = _json("SELECT ewp_claim_mastery_outbox(900)")
    out, per = _drain_batch(oc)
    eid = claim["evaluation_id"]
    issue = _scalar(
        f"SELECT id FROM writing_issue_events WHERE evaluation_id='{eid}' AND issue_type='{issue_type}'")
    proj = _scalar(
        f"SELECT p.id FROM writing_issue_projections p JOIN writing_issue_events i ON i.id=p.issue_event_id "
        f"WHERE i.evaluation_id='{eid}' AND i.issue_type='{issue_type}' AND p.projection_kind='automatic'")
    return {
        "sid": sid, "eval": eid, "issue": issue, "projection": proj,
        "evidence_key": per[proj]["key"], "tier": per[proj]["tier"], "micro": per[proj]["micro"],
        "topic": oc["topic_id"], "exam": oc.get("exam_id"), "source_entity": oc["source_entity_id"],
        "batch_rows": out["rows"],
    }


def test_per_issue_projection_evidence_written_with_non_null_projection():
    ctx = _seed_issue_assert("per issue base text", "d1" + "0" * 62, "article")
    # unit-level production + one projection-linked row.
    assert ctx["batch_rows"] == 2
    row = _scalar(
        f"SELECT evidence_tier||'/'||(issue_projection_id IS NOT NULL) "
        f"FROM user_topic_mastery_evidence WHERE evidence_key='{ctx['evidence_key']}'")
    # a freshly-surfaced (never-resolved) issue → recognition tier.
    assert row == "recognition/true"
    assert _scalar(
        f"SELECT issue_projection_id FROM user_topic_mastery_evidence "
        f"WHERE evidence_key='{ctx['evidence_key']}'") == ctx["projection"]


def test_per_issue_correction_tier_for_resolved_lineage_and_redrain_idempotent():
    # v1: SVA must_fix. v2: resolved. v3: SVA REGRESSES (present again) → its
    # lineage has a 'resolved' event, so the per-issue tier is 'correction'.
    sid = _new_submitted_session("correction tier base", "d2" + "0" * 62)
    e1 = _claim_complete([_issue("subject_verb_agreement", "they is")])
    _rewrite(sid, "correction tier v2", "d3" + "0" * 62, 2)
    e2 = _claim_complete([_issue("spelling", "teh")])  # SVA resolved
    _rewrite(sid, "correction tier v3", "d4" + "0" * 62, 3)
    claim = _json("SELECT ewp_claim_evaluation_job(900, ARRAY['language_evaluation'])")
    unit_key = _evidence_key(
        evidence_op="assert", user_id=_A, evaluation_id=claim["evaluation_id"],
        issue_projection_id=None, microtopic_id=claim.get("microtopic_id"),
        evidence_tier="production", source_type="sentence_drill")
    issues = json.dumps([_issue("subject_verb_agreement", "they is")])
    _json(
        f"SELECT ewp_complete_language_evaluation('{claim['job_id']}','{claim['claim_token']}',"
        f"'lang-mock-v1','{issues}'::jsonb,'{{}}'::jsonb,NULL,false,'shadow','{unit_key}')")
    oc = _json("SELECT ewp_claim_mastery_outbox(900)")
    projs = oc["issue_projections"]
    assert len(projs) == 1 and projs[0]["evidence_tier"] == "correction"
    out, per = _drain_batch(oc)
    key = per[projs[0]["issue_projection_id"]]["key"]
    assert _scalar(
        f"SELECT evidence_tier FROM user_topic_mastery_evidence WHERE evidence_key='{key}'") == "correction"
    # re-drain (simulate a crash-retry: reprocess the SAME row) inserts nothing new.
    tok2 = "00000000-0000-0000-0000-0000000000cc"
    _psql(
        f"UPDATE writing_mastery_outbox SET status='processing', claim_token='{tok2}', "
        f"locked_at=now() WHERE id='{oc['id']}'")
    oc2 = {**oc, "claim_token": tok2}
    _drain_batch(oc2)
    assert _scalar(
        f"SELECT count(*) FROM user_topic_mastery_evidence WHERE evidence_key='{key}'") == "1"


def _claim_review_correction_for(rev):
    """Claim the review_correction outbox row for `rev`. The claim RPC is
    global-oldest (single-worker semantics); on a shared DB other tests leave
    pending review_correction rows, so park any non-matching claimed row and
    retry until ours surfaces."""
    for _ in range(50):
        raw = _scalar("SELECT ewp_claim_review_correction_outbox(900)")
        if not raw:
            break
        rc = json.loads(raw)
        if rc["review_event_id"] == rev:
            return rc
        _psql(
            f"UPDATE writing_mastery_outbox SET status='failed', claim_token=NULL, "
            f"locked_at=NULL WHERE id='{rc['id']}'")
    raise AssertionError(f"no review_correction outbox row claimed for {rev}")


def _apply_correction(ctx, decision, corrected=None):
    """Seed a review event with `decision`, enqueue + claim + complete the
    correction, and return (enqueue_result, review_event_id)."""
    corr = f",'{corrected}'" if corrected else ",NULL"
    _psql(
        "INSERT INTO writing_issue_review_events(issue_event_id,decision,corrected_issue_type,reviewer_type) "
        f"VALUES ('{ctx['issue']}','{decision}'{corr},'system')")
    rev = _scalar(
        f"SELECT id FROM writing_issue_review_events WHERE issue_event_id='{ctx['issue']}' "
        "ORDER BY event_seq DESC LIMIT 1")
    enq = _json(f"SELECT ewp_enqueue_review_correction('{rev}')")
    if enq["status"] != "enqueued":
        return enq, rev
    rc = _claim_review_correction_for(rev)
    ck = _evidence_key(
        evidence_op=rc["evidence_op"], user_id=rc["user_id"], evaluation_id=rc["evaluation_id"],
        issue_projection_id=rc["issue_projection_id"], microtopic_id=rc.get("microtopic_id"),
        evidence_tier=rc["evidence_tier"], source_type=rc["source_type"],
        review_event_id=rc["review_event_id"])
    ev, sh = _mk_evidence_dict(
        op=rc["evidence_op"], user=rc["user_id"], exam=rc.get("exam_id"), topic=rc["topic_id"],
        micro=rc.get("microtopic_id"), source_type=rc["source_type"],
        source_entity=rc["source_entity_id"], evaluation=rc["evaluation_id"],
        tier=rc["evidence_tier"], projection=rc["issue_projection_id"], key=ck,
        review=rc["review_event_id"], supersedes=rc["supersedes_evidence_key"])
    out = _json(
        f"SELECT ewp_complete_review_correction('{rc['id']}','{rc['claim_token']}',"
        f"'{json.dumps(ev)}'::jsonb,'{json.dumps(sh)}'::jsonb)")
    assert out["status"] == "done"
    return enq, rev


def _in_effective(projection):
    return _scalar(
        f"SELECT count(*) FROM effective_user_topic_mastery_evidence WHERE issue_projection_id='{projection}'")


def test_review_correction_invalidated_retract_folds_out():
    ctx = _seed_issue_assert("retract base text", "d5" + "0" * 62, "article")
    assert _in_effective(ctx["projection"]) == "1"
    enq, _ = _apply_correction(ctx, "invalidated")
    assert enq["evidence_op"] == "retract" and enq["mastery_flag_state"] == "shadow"
    # a retract row exists preserving the predecessor projection...
    assert _scalar(
        f"SELECT count(*) FROM user_topic_mastery_evidence "
        f"WHERE evidence_op='retract' AND issue_projection_id='{ctx['projection']}'") == "1"
    # ...and the effective fold no longer surfaces the issue.
    assert _in_effective(ctx["projection"]) == "0"


def test_review_correction_reclassified_replace_supersedes():
    ctx = _seed_issue_assert("replace base text", "d6" + "0" * 62, "article")
    enq, rev = _apply_correction(ctx, "reclassified", corrected="word_choice")
    assert enq["evidence_op"] == "replace"
    # a review_override projection was created for the cited review event...
    override = _scalar(
        f"SELECT id FROM writing_issue_projections "
        f"WHERE projection_kind='review_override' AND override_review_event_id='{rev}'")
    assert override
    # ...the replace row carries it, the original automatic projection is superseded.
    assert _scalar(
        f"SELECT count(*) FROM user_topic_mastery_evidence "
        f"WHERE evidence_op='replace' AND issue_projection_id='{override}'") == "1"
    assert _in_effective(ctx["projection"]) == "0"      # original folded out
    assert _in_effective(override) == "1"               # replacement effective


def test_review_correction_confirmed_reassert_restores():
    ctx = _seed_issue_assert("reassert base text", "d7" + "0" * 62, "article")
    _apply_correction(ctx, "invalidated")               # retract
    assert _in_effective(ctx["projection"]) == "0"
    enq, _ = _apply_correction(ctx, "confirmed")        # re-assert
    assert enq["evidence_op"] == "assert"
    # the re-assert restores the ORIGINAL automatic projection into the fold.
    assert _in_effective(ctx["projection"]) == "1"
    assert _scalar(
        f"SELECT count(*) FROM user_topic_mastery_evidence "
        f"WHERE evidence_op='assert' AND review_event_id IS NOT NULL "
        f"AND issue_projection_id='{ctx['projection']}'") == "1"


def test_review_correction_pinned_flag_copied_not_reresolved():
    # The correction inherits the assertion's pinned mode (§4.12c/§8.2); the
    # pipeline NEVER reads a current flag, so a correction is emitted even when
    # the current flag would be 'off'. The enqueued row's flag equals the pin.
    ctx = _seed_issue_assert("pinned flag text", "d8" + "0" * 62, "article")
    _psql(
        "INSERT INTO writing_issue_review_events(issue_event_id,decision,reviewer_type) "
        f"VALUES ('{ctx['issue']}','invalidated','system')")
    rev = _scalar(
        f"SELECT id FROM writing_issue_review_events WHERE issue_event_id='{ctx['issue']}' "
        "ORDER BY event_seq DESC LIMIT 1")
    enq = _json(f"SELECT ewp_enqueue_review_correction('{rev}')")
    assert enq["status"] == "enqueued"
    assert _scalar(
        f"SELECT mastery_flag_state FROM writing_mastery_outbox WHERE review_event_id='{rev}'") == "shadow"


def test_review_correction_stale_rejected_by_trigger():
    # Enqueue a retract for an invalidation, then a NEWER confirmed review lands.
    # Completing the (now stale) retract must be rejected by the correction guard.
    ctx = _seed_issue_assert("stale correction text", "d9" + "0" * 62, "article")
    _psql(
        "INSERT INTO writing_issue_review_events(issue_event_id,decision,reviewer_type) "
        f"VALUES ('{ctx['issue']}','invalidated','system')")
    rev1 = _scalar(
        f"SELECT id FROM writing_issue_review_events WHERE issue_event_id='{ctx['issue']}' "
        "ORDER BY event_seq DESC LIMIT 1")
    _json(f"SELECT ewp_enqueue_review_correction('{rev1}')")
    rc = _claim_review_correction_for(rev1)
    # a newer review event supersedes rev1.
    _psql(
        "INSERT INTO writing_issue_review_events(issue_event_id,decision,reviewer_type) "
        f"VALUES ('{ctx['issue']}','confirmed','system')")
    ck = _evidence_key(
        evidence_op=rc["evidence_op"], user_id=rc["user_id"], evaluation_id=rc["evaluation_id"],
        issue_projection_id=rc["issue_projection_id"], microtopic_id=rc.get("microtopic_id"),
        evidence_tier=rc["evidence_tier"], source_type=rc["source_type"],
        review_event_id=rc["review_event_id"])
    ev, sh = _mk_evidence_dict(
        op=rc["evidence_op"], user=rc["user_id"], exam=rc.get("exam_id"), topic=rc["topic_id"],
        micro=rc.get("microtopic_id"), source_type=rc["source_type"],
        source_entity=rc["source_entity_id"], evaluation=rc["evaluation_id"],
        tier=rc["evidence_tier"], projection=rc["issue_projection_id"], key=ck,
        review=rc["review_event_id"], supersedes=rc["supersedes_evidence_key"])
    p = _psql(
        f"SELECT ewp_complete_review_correction('{rc['id']}','{rc['claim_token']}',"
        f"'{json.dumps(ev)}'::jsonb,'{json.dumps(sh)}'::jsonb)", expect_ok=False)
    assert "evidence_correction_invalid" in p.stderr


def test_review_correction_mismatched_op_rejected_by_trigger():
    # A direct correction whose op does not match the review decision is rejected
    # by ewp_check_evidence_correction (op↔decision is locked, §4.12c).
    ctx = _seed_issue_assert("mismatch op text", "da" + "0" * 62, "article")
    _psql(
        "INSERT INTO writing_issue_review_events(issue_event_id,decision,reviewer_type) "
        f"VALUES ('{ctx['issue']}','invalidated','system')")
    rev = _scalar(
        f"SELECT id FROM writing_issue_review_events WHERE issue_event_id='{ctx['issue']}' "
        "ORDER BY event_seq DESC LIMIT 1")
    # invalidated demands 'retract'; forge a 'replace' → trigger rejects.
    ck = _evidence_key(
        evidence_op="replace", user_id=_A, evaluation_id=ctx["eval"],
        issue_projection_id=ctx["projection"], microtopic_id=ctx["micro"],
        evidence_tier=ctx["tier"], source_type="sentence_drill", review_event_id=rev)
    p = _psql(
        "INSERT INTO user_topic_mastery_evidence(user_id,topic_id,microtopic_id,source_type,"
        "source_entity_id,evidence_tier,issue_projection_id,evidence_op,review_event_id,"
        "supersedes_evidence_key,evidence_key,observed_at) VALUES "
        f"('{_A}','{ctx['topic']}',{'NULL' if ctx['micro'] is None else chr(39)+ctx['micro']+chr(39)},"
        f"'sentence_drill','{ctx['source_entity']}','{ctx['tier']}','{ctx['projection']}','replace',"
        f"'{rev}','{ctx['evidence_key']}','{ck}',now())", expect_ok=False)
    assert "evidence_correction_invalid" in p.stderr
