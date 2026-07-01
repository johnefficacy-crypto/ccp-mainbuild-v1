"""Behavioural integration test for the EWP-1 migration.

Applies migration 205 to a real Postgres and exercises the contracts that
substring inspection cannot prove: append-only immutability against
service-role on EVERY history table, the effective-evidence view isolation
(across users A and B, and across authenticated/anon/service roles), the
session-snapshot guard, review-override coexistence + integrity, blank-version
integrity, cross-user supersession rejection, and the taxonomy seed.

Runs in CI (the backend job provides a Postgres service and sets
``EWP_PG_DSN``); locally set ``EWP_PG_DSN`` to a disposable Postgres superuser
DB. Skips only when no database is configured, so it never blocks environments
without one.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_DSN = os.environ.get("EWP_PG_DSN")
_PSQL = shutil.which("psql")
_MIGRATION = (
    Path(__file__).parents[3]
    / "supabase/migrations/205_english_writing_practice_schema.sql"
)

pytestmark = pytest.mark.skipif(
    not (_DSN and _PSQL),
    reason="set EWP_PG_DSN to a disposable Postgres superuser DB (and have psql) to run",
)

_HEXA = "a" * 64  # a valid content-hash / evidence-key shaped value
_KEY_A = "1" * 64
_KEY_B = "2" * 64

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

# Grant tables to the runtime roles (as production does), then restore the
# migration's deliberate REVOKE on the fold view so we test the real posture.
_GRANTS = """
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO authenticated, service_role, anon;
REVOKE ALL ON public.effective_user_topic_mastery_evidence FROM authenticated, anon;
GRANT SELECT ON public.effective_user_topic_mastery_evidence TO service_role;
"""

_FIXTURES = f"""
INSERT INTO exams(id) VALUES ('00000000-0000-0000-0000-0000000000e1') ON CONFLICT DO NOTHING;
INSERT INTO profiles(id) VALUES ('00000000-0000-0000-0000-0000000000aa'),
                                ('00000000-0000-0000-0000-0000000000bb') ON CONFLICT DO NOTHING;
INSERT INTO writing_prompts(id,exam_id,subject_id,topic_id,exercise_type,prompt_text,difficulty_level)
  SELECT '00000000-0000-0000-0000-0000000000d1','00000000-0000-0000-0000-0000000000e1',
         (SELECT id FROM subjects WHERE slug='english-language'),
         (SELECT id FROM topics WHERE slug='grammar'),'sentence_construction','p',1
  WHERE NOT EXISTS (SELECT 1 FROM writing_prompts WHERE id='00000000-0000-0000-0000-0000000000d1');
INSERT INTO writing_sessions(id,user_id,prompt_id,mode,projection_revision,feedback_release_policy)
  SELECT '00000000-0000-0000-0000-0000000000d2','00000000-0000-0000-0000-0000000000aa',
         '00000000-0000-0000-0000-0000000000d1','learning',1,'immediate'
  WHERE NOT EXISTS (SELECT 1 FROM writing_sessions WHERE id='00000000-0000-0000-0000-0000000000d2');
INSERT INTO writing_session_units(id,session_id,unit_number)
  SELECT '00000000-0000-0000-0000-0000000000d3','00000000-0000-0000-0000-0000000000d2',1
  WHERE NOT EXISTS (SELECT 1 FROM writing_session_units WHERE id='00000000-0000-0000-0000-0000000000d3');
INSERT INTO writing_unit_versions(id,unit_id,version_number,answer_text,content_hash)
  SELECT '00000000-0000-0000-0000-0000000000d4','00000000-0000-0000-0000-0000000000d3',1,'h','{_HEXA}'
  WHERE NOT EXISTS (SELECT 1 FROM writing_unit_versions WHERE id='00000000-0000-0000-0000-0000000000d4');
INSERT INTO writing_evaluations(id,unit_version_id)
  SELECT '00000000-0000-0000-0000-0000000000d5','00000000-0000-0000-0000-0000000000d4'
  WHERE NOT EXISTS (SELECT 1 FROM writing_evaluations WHERE id='00000000-0000-0000-0000-0000000000d5');
-- effective evidence for BOTH users, so a leaking view would return >0 for authenticated.
INSERT INTO user_topic_mastery_evidence(user_id,topic_id,source_type,source_entity_id,evidence_tier,evidence_key,observed_at)
  SELECT '00000000-0000-0000-0000-0000000000aa',(SELECT id FROM topics WHERE slug='grammar'),
         'sentence_drill','00000000-0000-0000-0000-0000000000d4','production','{_KEY_A}',now()
  WHERE NOT EXISTS (SELECT 1 FROM user_topic_mastery_evidence WHERE evidence_key='{_KEY_A}');
INSERT INTO user_topic_mastery_evidence(user_id,topic_id,source_type,source_entity_id,evidence_tier,evidence_key,observed_at)
  SELECT '00000000-0000-0000-0000-0000000000bb',(SELECT id FROM topics WHERE slug='grammar'),
         'sentence_drill','00000000-0000-0000-0000-0000000000d4','production','{_KEY_B}',now()
  WHERE NOT EXISTS (SELECT 1 FROM user_topic_mastery_evidence WHERE evidence_key='{_KEY_B}');
-- One row in every append-only history table so the immutability parametrization
-- exercises the per-row trigger (a 0-row UPDATE/DELETE would trivially succeed).
INSERT INTO writing_issue_events(id,evaluation_id,issue_type,lineage_id,severity)
  SELECT '00000000-0000-0000-0000-00000000ee01','00000000-0000-0000-0000-0000000000d5','article',
         '00000000-0000-0000-0000-0000000000aa','must_fix'
  WHERE NOT EXISTS (SELECT 1 FROM writing_issue_events WHERE id='00000000-0000-0000-0000-00000000ee01');
INSERT INTO writing_issue_resolution_events(issue_event_id,resolving_version_id,resolving_evaluation_id,outcome,evaluator_version)
  SELECT '00000000-0000-0000-0000-00000000ee01','00000000-0000-0000-0000-0000000000d4','00000000-0000-0000-0000-0000000000d5','resolved','v1'
  WHERE NOT EXISTS (SELECT 1 FROM writing_issue_resolution_events WHERE issue_event_id='00000000-0000-0000-0000-00000000ee01');
INSERT INTO writing_issue_projections(issue_event_id,projection_revision,projection_kind,canonical_error_type)
  SELECT '00000000-0000-0000-0000-00000000ee01',1,'automatic','careless'
  WHERE NOT EXISTS (SELECT 1 FROM writing_issue_projections WHERE issue_event_id='00000000-0000-0000-0000-00000000ee01' AND projection_kind='automatic');
INSERT INTO writing_issue_review_events(id,issue_event_id,decision,reviewer_type)
  SELECT '00000000-0000-0000-0000-00000000ee02','00000000-0000-0000-0000-00000000ee01','confirmed','human'
  WHERE NOT EXISTS (SELECT 1 FROM writing_issue_review_events WHERE id='00000000-0000-0000-0000-00000000ee02');
INSERT INTO writing_mastery_shadow(user_id,topic_id,source_type,source_entity_id,evaluation_id,evidence_tier,evidence_key)
  SELECT '00000000-0000-0000-0000-0000000000aa',(SELECT id FROM topics WHERE slug='grammar'),'sentence_drill',
         '00000000-0000-0000-0000-0000000000d4','00000000-0000-0000-0000-0000000000d5','production','{'9'*64}'
  WHERE NOT EXISTS (SELECT 1 FROM writing_mastery_shadow WHERE evidence_key='{'9'*64}');
"""

_IMMUTABLE_TABLES = [
    "writing_unit_versions",
    "writing_issue_events",
    "writing_issue_resolution_events",
    "writing_issue_projections",
    "writing_issue_review_events",
    "user_topic_mastery_evidence",
    "writing_mastery_shadow",
]


def _psql(sql: str, *, expect_ok: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-c", sql],
        capture_output=True, text=True,
    )
    if expect_ok:
        assert proc.returncode == 0, f"unexpected failure:\n{proc.stderr}"
    else:
        assert proc.returncode != 0, f"expected failure but succeeded:\n{proc.stdout}"
    return proc


def _psql_file(path: Path) -> None:
    proc = subprocess.run(
        [_PSQL, _DSN, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-f", str(path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"failed applying {path.name}:\n{proc.stderr}"


def _scalar(sql: str) -> str:
    proc = subprocess.run(
        [_PSQL, _DSN, "-t", "-A", "-X", "-c", sql],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _count_in_txn(role: str, body: str) -> list[str]:
    """Run `body` (ending in a SELECT count) under `role`; return digit lines."""
    out = _scalar(f"BEGIN; SET LOCAL ROLE {role}; {body} COMMIT;")
    return [ln for ln in out.splitlines() if ln.strip().lstrip("-").isdigit()]


@pytest.fixture(scope="module", autouse=True)
def _apply():
    _psql(_BOOTSTRAP)
    _psql_file(_MIGRATION)
    _psql_file(_MIGRATION)  # idempotent re-apply
    _psql(_GRANTS)
    _psql(_FIXTURES)
    yield


def test_seed_counts():
    assert _scalar("SELECT count(*) FROM topics WHERE level='topic'") == "8"
    assert _scalar("SELECT count(*) FROM topics WHERE level='microtopic'") == "28"
    assert _scalar("SELECT count(*) FROM writing_issue_type_microtopic_map") == "19"
    assert _scalar("""
      SELECT count(*) FROM writing_issue_type_microtopic_map m JOIN topics t ON t.id=m.microtopic_id
      WHERE t.level<>'microtopic' OR t.is_active=false
        OR t.subject_id<>(SELECT id FROM subjects WHERE slug='english-language')
    """) == "0"


@pytest.mark.parametrize("table", _IMMUTABLE_TABLES)
def test_every_immutable_table_rejects_update_and_delete(table):
    # UPDATE/DELETE on an append-only table must fail regardless of contents.
    _psql(f"UPDATE public.{table} SET id=id", expect_ok=False)
    _psql(f"DELETE FROM public.{table} WHERE true", expect_ok=False)


def test_effective_view_isolation():
    # service_role (backend, BYPASSRLS) sees both users' effective rows.
    assert _count_in_txn(
        "service_role",
        "SELECT count(*) FROM public.effective_user_topic_mastery_evidence;",
    ) == ["2"]
    # authenticated has NO privilege on the production view → permission denied.
    _psql("SET ROLE authenticated; SELECT * FROM public.effective_user_topic_mastery_evidence;", expect_ok=False)
    # anon likewise.
    _psql("SET ROLE anon; SELECT * FROM public.effective_user_topic_mastery_evidence;", expect_ok=False)
    # Even under an explicit test-only grant, security_invoker + zero base policy
    # means authenticated sees NEITHER user's rows.
    _psql("GRANT SELECT ON public.effective_user_topic_mastery_evidence TO authenticated;")
    try:
        digits = _count_in_txn(
            "authenticated",
            "SET LOCAL ewp.uid='00000000-0000-0000-0000-0000000000aa'; "
            "SELECT count(*) FROM public.effective_user_topic_mastery_evidence;",
        )
        assert digits == ["0"], digits
    finally:
        _psql("REVOKE ALL ON public.effective_user_topic_mastery_evidence FROM authenticated;")


def test_session_snapshot_guard():
    _psql("UPDATE writing_sessions SET projection_revision=2 WHERE id='00000000-0000-0000-0000-0000000000d2'", expect_ok=False)
    _psql("UPDATE writing_sessions SET status='completed' WHERE id='00000000-0000-0000-0000-0000000000d2'", expect_ok=True)


def test_value_domains_rejected():
    _psql("INSERT INTO writing_unit_versions(unit_id,version_number,answer_text,content_hash) "
          "VALUES ('00000000-0000-0000-0000-0000000000d3',9,'x','NOTHEX')", expect_ok=False)
    _psql("INSERT INTO writing_session_units(session_id,unit_number) "
          "VALUES ('00000000-0000-0000-0000-0000000000d2',0)", expect_ok=False)
    _psql("INSERT INTO user_topic_mastery_evidence(user_id,topic_id,source_type,source_entity_id,evidence_tier,evidence_key,observed_at) "
          "VALUES ('00000000-0000-0000-0000-0000000000aa',(SELECT id FROM topics WHERE slug='grammar'),'sentence_drill','00000000-0000-0000-0000-0000000000d4','production','not-hex',now())", expect_ok=False)


def test_blank_version_integrity():
    # blank must be empty text + empty-string SHA-256.
    _psql("INSERT INTO writing_unit_versions(unit_id,version_number,answer_text,submission_kind,content_hash) "
          f"VALUES ('00000000-0000-0000-0000-0000000000d3',20,'nonempty','blank','{_HEXA}')", expect_ok=False)
    _psql("INSERT INTO writing_unit_versions(unit_id,version_number,answer_text,submission_kind,content_hash,server_word_count) "
          "VALUES ('00000000-0000-0000-0000-0000000000d3',21,'','blank',"
          "'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',0)", expect_ok=True)


def test_running_job_requires_lease():
    _psql("INSERT INTO writing_evaluation_jobs(evaluation_id,job_kind,status) "
          "VALUES ('00000000-0000-0000-0000-0000000000d5','language_evaluation','running')", expect_ok=False)


def test_cascade_into_immutable_blocks_profile_delete():
    _psql("DELETE FROM profiles WHERE id='00000000-0000-0000-0000-0000000000bb'", expect_ok=False)


def test_review_override_coexists_and_is_integrity_checked():
    # a plain issue + automatic projection
    _psql("""
      INSERT INTO writing_issue_events(id,evaluation_id,issue_type,lineage_id,severity)
        SELECT '00000000-0000-0000-0000-0000000000f0','00000000-0000-0000-0000-0000000000d5','article',
               '00000000-0000-0000-0000-0000000000c0','must_fix'
        WHERE NOT EXISTS (SELECT 1 FROM writing_issue_events WHERE id='00000000-0000-0000-0000-0000000000f0');
      INSERT INTO writing_issue_projections(issue_event_id,projection_revision,projection_kind,canonical_error_type)
        SELECT '00000000-0000-0000-0000-0000000000f0',1,'automatic','careless'
        WHERE NOT EXISTS (SELECT 1 FROM writing_issue_projections
                          WHERE issue_event_id='00000000-0000-0000-0000-0000000000f0' AND projection_kind='automatic');
      INSERT INTO writing_issue_review_events(id,issue_event_id,decision,corrected_issue_type,reviewer_type)
        SELECT '00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000f0','reclassified','tense','human'
        WHERE NOT EXISTS (SELECT 1 FROM writing_issue_review_events WHERE id='00000000-0000-0000-0000-0000000000f1');
    """)
    # override at the SAME revision coexists with the automatic row
    _psql("INSERT INTO writing_issue_projections(issue_event_id,projection_revision,projection_kind,override_review_event_id,canonical_error_type) "
          "VALUES ('00000000-0000-0000-0000-0000000000f0',1,'review_override','00000000-0000-0000-0000-0000000000f1','concept_gap')", expect_ok=True)
    # a second automatic at the same revision is rejected (partial unique)
    _psql("INSERT INTO writing_issue_projections(issue_event_id,projection_revision,projection_kind,canonical_error_type) "
          "VALUES ('00000000-0000-0000-0000-0000000000f0',1,'automatic','memory_gap')", expect_ok=False)
    # reclassified requires corrected_issue_type
    _psql("INSERT INTO writing_issue_review_events(issue_event_id,decision,reviewer_type) "
          "VALUES ('00000000-0000-0000-0000-0000000000f0','reclassified','human')", expect_ok=False)


def test_effective_review_created_at_id_tiebreak():
    # invalidated then confirmed in the SAME transaction (equal created_at):
    # effective decision must be confirmed (id tiebreak), so NOT invalidated.
    _psql("""
      INSERT INTO writing_issue_events(id,evaluation_id,issue_type,lineage_id,severity)
        SELECT '00000000-0000-0000-0000-0000000000f8','00000000-0000-0000-0000-0000000000d5','tense',
               '00000000-0000-0000-0000-0000000000c8','must_fix'
        WHERE NOT EXISTS (SELECT 1 FROM writing_issue_events WHERE id='00000000-0000-0000-0000-0000000000f8');
      BEGIN;
        INSERT INTO writing_issue_review_events(issue_event_id,decision,reviewer_type)
          VALUES ('00000000-0000-0000-0000-0000000000f8','invalidated','system');
        INSERT INTO writing_issue_review_events(issue_event_id,decision,reviewer_type)
          VALUES ('00000000-0000-0000-0000-0000000000f8','confirmed','human');
      COMMIT;
    """)
    assert _scalar("SELECT ewp_private.ewp_issue_effectively_invalidated('00000000-0000-0000-0000-0000000000f8')") == "f"


def test_cross_user_supersession_rejected():
    # user bb attempts to supersede user aa's evidence_key -> composite FK fails.
    _psql("INSERT INTO writing_issue_review_events(id,issue_event_id,decision,reviewer_type) "
          "SELECT '00000000-0000-0000-0000-0000000000fb','00000000-0000-0000-0000-0000000000f0','invalidated','system' "
          "WHERE NOT EXISTS (SELECT 1 FROM writing_issue_review_events WHERE id='00000000-0000-0000-0000-0000000000fb')")
    _psql("INSERT INTO user_topic_mastery_evidence(user_id,topic_id,source_type,source_entity_id,evidence_tier,evidence_key,evidence_op,review_event_id,supersedes_evidence_key,observed_at) "
          f"VALUES ('00000000-0000-0000-0000-0000000000bb',(SELECT id FROM topics WHERE slug='grammar'),'sentence_drill','00000000-0000-0000-0000-0000000000d4','production','{'3'*64}','retract','00000000-0000-0000-0000-0000000000fb','{_KEY_A}',now())",
          expect_ok=False)


def test_exercise_type_domain_enforced():
    _psql("INSERT INTO writing_prompts(exam_id,subject_id,topic_id,exercise_type,prompt_text,difficulty_level) "
          "SELECT '00000000-0000-0000-0000-0000000000e1',(SELECT id FROM subjects WHERE slug='english-language'),"
          "(SELECT id FROM topics WHERE slug='grammar'),'typo_type','p',1", expect_ok=False)


def test_blank_version_word_count_must_be_zero_not_null():
    # NULL server_word_count for a blank version is now rejected (deterministic 0).
    _psql("INSERT INTO writing_unit_versions(unit_id,version_number,answer_text,submission_kind,content_hash) "
          "VALUES ('00000000-0000-0000-0000-0000000000d3',30,'','blank',"
          "'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')", expect_ok=False)


def test_authenticated_owner_cannot_read_effectively_invalidated_issue():
    # THE path the earlier suite missed: the effective-review helper must work
    # under the AUTHENTICATED role (SECURITY DEFINER reading a zero-policy table),
    # or invalidated raw issue rows leak (locked rule 22). Seed one confirmed
    # issue and one invalidated, then read as the owner.
    _psql("""
      INSERT INTO writing_issue_events(id,evaluation_id,issue_type,lineage_id,severity)
        SELECT '00000000-0000-0000-0000-00000000c001','00000000-0000-0000-0000-0000000000d5','article',
               '00000000-0000-0000-0000-0000000000a1','must_fix'
        WHERE NOT EXISTS (SELECT 1 FROM writing_issue_events WHERE id='00000000-0000-0000-0000-00000000c001');
      INSERT INTO writing_issue_events(id,evaluation_id,issue_type,lineage_id,severity)
        SELECT '00000000-0000-0000-0000-00000000c002','00000000-0000-0000-0000-0000000000d5','tense',
               '00000000-0000-0000-0000-0000000000a2','must_fix'
        WHERE NOT EXISTS (SELECT 1 FROM writing_issue_events WHERE id='00000000-0000-0000-0000-00000000c002');
      INSERT INTO writing_issue_review_events(issue_event_id,decision,reviewer_type)
        SELECT '00000000-0000-0000-0000-00000000c002','invalidated','system'
        WHERE NOT EXISTS (SELECT 1 FROM writing_issue_review_events
                          WHERE issue_event_id='00000000-0000-0000-0000-00000000c002' AND decision='invalidated');
    """)
    out = _scalar(
        "BEGIN; SET LOCAL ROLE authenticated; SET LOCAL ewp.uid='00000000-0000-0000-0000-0000000000aa'; "
        "SELECT id::text FROM public.writing_issue_events ORDER BY id; COMMIT;"
    )
    seen = set(out.split())
    assert "00000000-0000-0000-0000-00000000c001" in seen, "confirmed issue must stay visible"
    assert "00000000-0000-0000-0000-00000000c002" not in seen, "invalidated issue must be hidden from owner"


def test_helper_not_a_public_rpc_oracle():
    # The helper was moved out of `public` into `ewp_private` so PostgREST does
    # not expose it as an RPC. Neither authenticated nor anon can call the old
    # public function (it no longer exists), so no user can probe another user's
    # issue invalidation state through the API surface.
    _psql("SET ROLE authenticated; SELECT public.ewp_issue_effectively_invalidated('00000000-0000-0000-0000-00000000c002')",
          expect_ok=False)
    _psql("SET ROLE anon; SELECT public.ewp_issue_effectively_invalidated('00000000-0000-0000-0000-00000000c002')",
          expect_ok=False)
    # sanity: the private helper exists and is service_role-callable
    assert _scalar(
        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE p.proname='ewp_issue_effectively_invalidated' AND n.nspname='ewp_private'"
    ) == "1"
    assert _scalar(
        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE p.proname='ewp_issue_effectively_invalidated' AND n.nspname='public'"
    ) == "0"


def test_wrapped_role_rls_owner_only():
    # A non-owner authenticated user and anon see none of user aa's sessions.
    for role, setuid in [("authenticated", "SET LOCAL ewp.uid='00000000-0000-0000-0000-0000000000cc'; "), ("anon", "")]:
        out = _scalar(f"BEGIN; SET LOCAL ROLE {role}; {setuid}SELECT count(*) FROM public.writing_sessions; COMMIT;")
        digits = [ln for ln in out.splitlines() if ln.strip().isdigit()]
        assert digits == ["0"], (role, out)


# --- Correction-chain tests: each uses an ISOLATED issue so the history-sensitive
#     latest-review / previous-effective-decision checks are deterministic. ---

def _seed_issue(n, *, extra_proj_rev=None):
    """Isolated issue + automatic projection + predecessor assert for user aa.
    Returns (issue_id, proj_id, pred_key). Optionally seeds a second automatic
    projection at extra_proj_rev (returned proj id is derivable)."""
    issue = f"1eee0000-0000-4000-8000-{n:012x}"
    proj = f"2eee0000-0000-4000-8000-{n:012x}"
    pred = f"{n:02x}" * 32
    _psql(f"""
      INSERT INTO writing_issue_events(id,evaluation_id,issue_type,lineage_id,severity)
        SELECT '{issue}','00000000-0000-0000-0000-0000000000d5','article','{issue}','must_fix'
        WHERE NOT EXISTS (SELECT 1 FROM writing_issue_events WHERE id='{issue}');
      INSERT INTO writing_issue_projections(id,issue_event_id,projection_revision,projection_kind,canonical_error_type)
        SELECT '{proj}','{issue}',1,'automatic','careless'
        WHERE NOT EXISTS (SELECT 1 FROM writing_issue_projections WHERE id='{proj}');
      INSERT INTO user_topic_mastery_evidence(user_id,topic_id,source_type,source_entity_id,evidence_tier,issue_projection_id,evidence_key,observed_at)
        SELECT '00000000-0000-0000-0000-0000000000aa',(SELECT id FROM topics WHERE slug='grammar'),'sentence_drill',
               '00000000-0000-0000-0000-0000000000d4','production','{proj}','{pred}',now()
        WHERE NOT EXISTS (SELECT 1 FROM user_topic_mastery_evidence WHERE evidence_key='{pred}');
    """)
    if extra_proj_rev is not None:
        proj2 = f"2fff0000-0000-4000-8000-{n:012x}"
        _psql(f"INSERT INTO writing_issue_projections(id,issue_event_id,projection_revision,projection_kind,canonical_error_type) "
              f"SELECT '{proj2}','{issue}',{extra_proj_rev},'automatic','concept_gap' "
              f"WHERE NOT EXISTS (SELECT 1 FROM writing_issue_projections WHERE id='{proj2}')")
    return issue, proj, pred


def _review(issue, k, decision):
    rid = f"3eee0000-0000-4000-8000-{k:012x}"
    _psql(f"INSERT INTO writing_issue_review_events(id,issue_event_id,decision,reviewer_type) "
          f"SELECT '{rid}','{issue}','{decision}','system' "
          f"WHERE NOT EXISTS (SELECT 1 FROM writing_issue_review_events WHERE id='{rid}')")
    return rid


def _corr(pred, proj, rid, op, key, *, expect_ok):
    _psql("INSERT INTO user_topic_mastery_evidence(user_id,topic_id,source_type,source_entity_id,evidence_tier,"
          "issue_projection_id,evidence_key,evidence_op,review_event_id,supersedes_evidence_key,observed_at) "
          f"VALUES ('00000000-0000-0000-0000-0000000000aa',(SELECT id FROM topics WHERE slug='grammar'),'sentence_drill',"
          f"'00000000-0000-0000-0000-0000000000d4','production',{'NULL' if proj is None else repr(proj)},'{key}','{op}',"
          f"'{rid}','{pred}',now())", expect_ok=expect_ok)


def test_correction_cross_issue_rejected():
    issue_a, proj_a, pred_a = _seed_issue(0x10)
    issue_b, _, _ = _seed_issue(0x11)
    rev_b = _review(issue_b, 0x110, "invalidated")   # review on the WRONG issue
    _corr(pred_a, proj_a, rev_b, "retract", "d1" * 32, expect_ok=False)


def test_review_decision_to_evidence_op_mapping():
    issue, proj, pred = _seed_issue(0x12)
    rev_inv = _review(issue, 0x120, "invalidated")   # latest, changes from active
    _corr(pred, proj, rev_inv, "assert", "e1" * 32, expect_ok=False)   # invalidated->assert
    # confirmed->retract needs a confirmed as latest; use a fresh issue
    issue2, proj2, pred2 = _seed_issue(0x13)
    rev_conf = _review(issue2, 0x130, "confirmed")   # confirmed but effective was already active → redundant OR mismatch
    # confirmed with no prior review == unchanged (active) → redundant reject
    _corr(pred2, proj2, rev_conf, "assert", "e2" * 32, expect_ok=False)
    # invalidated->retract with the exact predecessor projection → accepted
    _corr(pred, proj, rev_inv, "retract", "e3" * 32, expect_ok=True)


def test_correction_of_non_issue_evidence_rejected():
    # KEY_A is a plain assert with issue_projection_id NULL → cannot be corrected.
    issue, _, _ = _seed_issue(0x14)
    rev = _review(issue, 0x140, "invalidated")
    _corr(_KEY_A, "2eee0000-0000-4000-8000-000000000014", rev, "retract", "77" * 32, expect_ok=False)


def test_correction_stale_and_redundant_rejected():
    issue, proj, pred = _seed_issue(0x15)
    rev1 = _review(issue, 0x150, "invalidated")   # seq1
    rev2 = _review(issue, 0x151, "confirmed")     # seq2 (latest)
    # citing rev1 (stale — rev2 is later) → rejected
    _corr(pred, proj, rev1, "retract", "a1" * 32, expect_ok=False)
    # redundant: a second confirmed while effective is already confirmed → rejected
    rev3 = _review(issue, 0x152, "confirmed")
    _corr(pred, proj, rev3, "assert", "a2" * 32, expect_ok=False)


def test_correction_exact_projection_identity():
    # issue with a second automatic projection at a different revision.
    issue, proj_root, pred = _seed_issue(0x16, extra_proj_rev=2)
    proj_other = "2fff0000-0000-4000-8000-000000000016"
    rev_inv = _review(issue, 0x160, "invalidated")
    # retract must preserve the predecessor's EXACT projection (proj_root), not proj_other
    _corr(pred, proj_other, rev_inv, "retract", "b1" * 32, expect_ok=False)
    _corr(pred, proj_root, rev_inv, "retract", "b2" * 32, expect_ok=True)   # tail = b2 now
    # re-assert must restore the EXACT root projection, not the other revision
    rev_conf = _review(issue, 0x161, "confirmed")
    _corr("b2" * 32, proj_other, rev_conf, "assert", "b3" * 32, expect_ok=False)
    _corr("b2" * 32, proj_root, rev_conf, "assert", "b4" * 32, expect_ok=True)
