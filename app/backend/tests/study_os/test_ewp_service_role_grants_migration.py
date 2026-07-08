"""Migration 234 contract: EWP tables granted to service_role.

Text-assertion style (matches the repo's migration contracts, e.g.
test_writing_rpcs_migration.py). The behavioural validation is the
writing-practice e2e flow (launch_writing SELECTs writing_sessions via
service_role) plus the operator/integration apply pass.

Guards against the regression where an EWP table the service_role backend
touches is created but never granted table-level privileges (migration 173's
blanket grant only covered tables existing at that time).
"""
from __future__ import annotations

from pathlib import Path

_SQL = (
    Path(__file__).parents[3]
    / "supabase/migrations/234_ewp_service_role_table_grants.sql"
).read_text()
# Collapse alignment whitespace so grant lines match regardless of padding.
_NORM = " ".join(_SQL.lower().split())

# Every EWP table the service_role backend (get_supabase_admin) accesses
# directly, created in migration 205 (writing_* + exam_descriptive_requirements
# + user_topic_mastery_evidence) or 214 (writing_prompt_targets).
EWP_TABLES = [
    "writing_prompts",
    "writing_rubrics",
    "exam_descriptive_requirements",
    "writing_prompt_targets",
    "writing_sessions",
    "writing_session_units",
    "writing_unit_versions",
    "writing_evaluations",
    "writing_evaluation_jobs",
    "writing_session_checks",
    "writing_issue_events",
    "writing_issue_resolution_events",
    "writing_issue_projections",
    "writing_issue_review_events",
    "writing_issue_type_microtopic_map",
    "writing_mastery_shadow",
    "writing_mastery_outbox",
    "user_topic_mastery_evidence",
]


def test_is_migration_234():
    assert _SQL.startswith("-- 234_ewp_service_role_table_grants.sql")


def test_grants_full_crud_to_service_role_on_every_ewp_table():
    for table in EWP_TABLES:
        assert (
            f"grant select, insert, update, delete on public.{table} to service_role;"
            in _NORM
        ), f"missing service_role grant for public.{table}"


def test_writing_sessions_is_covered():
    # writing_sessions is the table that surfaced the 42501 permission-denied
    # error in launch_writing() and must be granted.
    assert "public.writing_sessions to service_role" in _NORM


def test_reloads_postgrest_schema_cache():
    assert "notify pgrst, 'reload schema';" in _NORM
