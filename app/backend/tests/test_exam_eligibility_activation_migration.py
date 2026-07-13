"""Contract test for migration 253 (stream-aware evaluation activation)."""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / ".." / "supabase" / "migrations" / "253_exam_eligibility_stream_aware_activation.sql"
).read_text().lower()


def test_lifts_fail_closed_verify_guard():
    assert "drop constraint if exists exam_eligibility_rules_verified_supported_check" in MIGRATION
    assert "notify pgrst, 'reload schema';" in MIGRATION


def test_baseline_combo_excludes_experience_and_availability_is_domained():
    # Baseline combos must not admit cycle-only experience_min_years.
    assert "is_valid_baseline_qualification_combination" in MIGRATION
    assert "experience_min_years intentionally excluded" in MIGRATION
    assert "public.is_valid_baseline_qualification_combination(value_json)" in MIGRATION
    # stream_availability is domained at the DB (fail closed on typos).
    assert "exam_eligibility_rules_stream_availability_domain_check" in MIGRATION
    assert "value_text in ('offered','not_offered','expected')" in MIGRATION
