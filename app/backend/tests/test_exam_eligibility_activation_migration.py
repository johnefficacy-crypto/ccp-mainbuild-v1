"""Contract test for migration 251 (stream-aware evaluation activation)."""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / ".." / "supabase" / "migrations" / "251_exam_eligibility_stream_aware_activation.sql"
).read_text().lower()


def test_lifts_fail_closed_verify_guard():
    assert "drop constraint if exists exam_eligibility_rules_verified_supported_check" in MIGRATION
    assert "notify pgrst, 'reload schema';" in MIGRATION
    # It only lifts the guard — must not weaken the qual-combo or rule_type checks.
    assert "rule_type_check" not in MIGRATION
    assert "qual_combo" not in MIGRATION
