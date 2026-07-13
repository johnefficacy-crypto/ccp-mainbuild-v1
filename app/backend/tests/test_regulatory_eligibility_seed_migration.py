"""Schema-contract tests for migration 254 (Lane R R1 eligibility + cycles seed).

Repo convention (cf. test_financial_regulatory_seed_migration.py): no live-DB
migration harness in CI, so these assert against the migration SQL text. The
behavioural apply / idempotency / constraint-conformance was validated on
ephemeral PG16 against the migration-248 constraints (validator + qualification
CHECK + fail-closed verify + NULLS NOT DISTINCT uniqueness):
apply + re-apply → 3 cycles, 28 rules (14 stream-scoped), 8 qualification_combination
all valid, 0 verified.
"""
import json
import re
from pathlib import Path

_PATH = (
    Path(__file__).resolve().parents[1]
    / ".." / "supabase" / "migrations"
    / "254_financial_regulatory_eligibility_and_cycles_seed.sql"
)
MIGRATION = _PATH.read_text()
LOW = MIGRATION.lower()
# Executable SQL only — strip `--` line comments (the header explains the
# verified/CHECK governance in prose, which must not trip the "never verified" test).
CODE = "\n".join(line.split("--", 1)[0] for line in LOW.splitlines())


def test_seeds_the_three_researched_regulator_cycles():
    assert "'sebi grade a 2025'" in LOW
    assert "'pfrda grade a 2025'" in LOW
    assert "'irdai assistant manager 2024'" in LOW
    assert "insert into public.exam_cycles" in LOW


def test_every_seeded_row_is_draft_never_verified():
    # The seed must never mark a row verified — the evaluator reads only
    # verified rows, and Tier-A requires human review first. (Prose in the
    # header explains the CHECK; only executable SQL is checked here.)
    assert "'verified'" not in CODE
    # Both eligibility inserts select the literal 'draft' reviewer_status.
    assert CODE.count("'draft'") >= 2


def test_new_rule_types_are_used_and_stream_scoped():
    for rt in ("discipline", "min_percentage", "certification", "qualification_combination"):
        assert rt in LOW, rt
    # Stream rules join exam_streams by stream_key (per-stream targeting).
    assert "join public.exam_streams s on s.exam_id = e.id and s.stream_key" in LOW


def test_idempotent_on_conflict_guards_present():
    assert "on conflict (exam_id, year, cycle_name) do nothing" in LOW
    assert "on conflict do nothing" in LOW


def _valid_qc(node) -> bool:
    if not isinstance(node, dict):
        return False
    if "op" in node:
        if node["op"] not in ("and", "or"):
            return False
        clauses = node.get("clauses")
        if not isinstance(clauses, list) or not clauses:
            return False
        return all(_valid_qc(c) for c in clauses)
    rt = node.get("rule_type")
    if rt in ("min_percentage", "experience_min_years"):
        return isinstance(node.get("value_num"), (int, float))
    if rt in ("discipline", "certification", "education_min_level", "nationality"):
        return isinstance(node.get("value_text"), str)
    return False


def test_all_qualification_combination_json_is_structurally_valid():
    blobs = [
        b for b in re.findall(r"'(\{.*?\})'::jsonb", MIGRATION)
        if '"op"' in b or '"rule_type"' in b
    ]
    assert len(blobs) == 8, f"expected 8 qualification_combination blobs, found {len(blobs)}"
    for b in blobs:
        assert _valid_qc(json.loads(b)), f"invalid qualification_combination grammar: {b}"
