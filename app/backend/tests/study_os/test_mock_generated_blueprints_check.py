"""A-PR0 generated-mock blueprint schema foundation — check-file contract.

Pure file-content assertions (no DB) so the check runs in CI without Supabase
credentials. It guards the presence and scope of the read-only smoke check
``app/supabase/checks/mock_generated_blueprints_schema.sql``, which asserts
the live schema produced by migrations 174 + 175.

Mirrors the #682 pattern (``test_descriptive_answer_schema.py`` +
``mock_descriptive_answer_schema.sql``): a text-based test pinned to a
read-only ``checks/*.sql`` companion. Behavioral insert/RLS coverage stays as
manual BEGIN/ROLLBACK notes — there is no live-DB harness in this repo.
"""
from pathlib import Path

_CHECKS = Path(__file__).resolve().parents[4] / "app" / "supabase" / "checks"
_CHECK = _CHECKS / "mock_generated_blueprints_schema.sql"


def _check_sql() -> str:
    return _CHECK.read_text().lower()


def test_check_file_exists_and_is_read_only():
    assert _CHECK.exists(), "checks/mock_generated_blueprints_schema.sql is missing"
    sql = _check_sql()
    # Read-only smoke-check envelope, matching the established checks/ format.
    assert "begin read only;" in sql
    assert "do $$" in sql
    assert "rollback;" in sql
    # SELECT-only: no mutating statements in the check file.
    for mutating in ("insert into", "update ", "delete from", "alter table", "create table"):
        assert mutating not in sql, f"check file must be read-only; found {mutating!r}"


def test_check_asserts_table_and_columns():
    sql = _check_sql()
    assert "to_regclass('public.mock_generated_blueprints')" in sql
    for column in (
        "id",
        "user_id",
        "exam_id",
        "exam_phase_id",
        "source",
        "status",
        "template_snapshot",
        "section_snapshot",
        "selector_snapshot",
        "question_ids",
        "readiness_snapshot",
        "expires_at",
        "created_at",
        "started_at",
        "updated_at",
    ):
        assert f"column_name = '{column}'" in sql, f"check missing column assertion: {column}"
    # uuid[] is reported as data_type ARRAY / udt_name _uuid.
    assert "udt_name = '_uuid'" in sql


def test_check_asserts_source_and_status_constraints():
    sql = _check_sql()
    assert "exam_realistic" in sql and "personalized" in sql
    # migration 231 extended the source set — the smoke-check must prove them too.
    for src in ("pyq_practice_paper", "pyq_practice_section", "pyq_practice_topic"):
        assert src in sql
    for status in ("draft", "started", "expired", "cancelled"):
        assert status in sql


def test_check_asserts_foreign_keys():
    sql = _check_sql()
    assert "'public.profiles'::regclass" in sql
    assert "'public.exams'::regclass" in sql
    assert "'public.exam_phases'::regclass" in sql


def test_check_asserts_indexes_by_exact_migration_names():
    sql = _check_sql()
    for index in (
        "idx_mock_generated_blueprints_user_status",
        "idx_mock_generated_blueprints_expires_at",
        "idx_mock_generated_blueprints_exam_phase",
        "uq_mock_generated_blueprints_id_user",
        "uq_mock_attempts_active_blueprint",
    ):
        assert index in sql, f"check missing index assertion: {index}"


def test_check_asserts_trigger_and_rls():
    sql = _check_sql()
    assert "mock_generated_blueprints_updated_at" in sql
    assert "relrowsecurity is true" in sql
    assert "mock_generated_blueprints_owner_select" in sql
    assert "mock_generated_blueprints_service_role_all" in sql


def test_check_asserts_mock_attempts_wiring():
    sql = _check_sql()
    # template_id became nullable; generated_blueprint_id added.
    assert "column_name = 'template_id' and is_nullable = 'yes'" in sql
    assert "column_name = 'generated_blueprint_id'" in sql
    # XOR + composite owner FK, by exact migration names.
    assert "mock_attempts_one_source_chk" in sql
    assert "mock_attempts_generated_blueprint_owner_fkey" in sql
