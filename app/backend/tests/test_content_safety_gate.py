"""Content safety gate — reviewer_status invariants and mock-expansion gate.

Rules enforced (applied to both in-memory row sets and seed SQL):

  1. community_resources: any row with usable_for_mock_generation=True must
     also have reviewer_status='verified'.

  2. mock_question_bank: no row may carry reviewer_status='live' until the
     mock-expansion gate is met (≥ 200 verified Quant questions).

  3. Mock-expansion gate (documented in pilot_content_ssc_cgl_banking.sql):
     usable_for_mock_generation must remain False on all community_resources
     rows while the count of mock_question_bank rows with
       subject_id = QUANT_SUBJECT_ID and reviewer_status = 'verified'
     is below 200.

These tests are standalone (no live DB) and parse the pilot seed SQL file
to assert the invariants hold on committed seed data.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# ── constants ─────────────────────────────────────────────────────────────────

QUANT_SUBJECT_ID = "55555555-5555-5555-5555-555555555551"
MOCK_EXPANSION_GATE = 200

SEEDS_DIR = Path(__file__).parents[2] / "supabase" / "seeds"
PILOT_SEED = SEEDS_DIR / "pilot_content_ssc_cgl_banking.sql"


# ── in-memory validator (pure-Python, no DB) ──────────────────────────────────


def check_community_resources(rows: list[dict]) -> list[str]:
    """Return violation messages for community_resources rows that break the
    safety rule: usable_for_mock_generation=True requires reviewer_status='verified'.
    """
    violations = []
    for row in rows:
        if row.get("usable_for_mock_generation") and row.get("reviewer_status") != "verified":
            violations.append(
                f"community_resources id={row.get('id')!r}: "
                f"usable_for_mock_generation=True but reviewer_status={row.get('reviewer_status')!r}"
            )
    return violations


def check_mock_question_bank(rows: list[dict], verified_quant_count: int) -> list[str]:
    """Return violation messages for mock_question_bank rows that carry
    reviewer_status='live' before the 200-verified-Quant gate is met.
    """
    violations = []
    gate_open = verified_quant_count >= MOCK_EXPANSION_GATE
    for row in rows:
        if row.get("reviewer_status") == "live" and not gate_open:
            violations.append(
                f"mock_question_bank id={row.get('id')!r}: "
                f"reviewer_status='live' but verified_quant_count={verified_quant_count} "
                f"< {MOCK_EXPANSION_GATE} (gate not met)"
            )
    return violations


def count_verified_quant(rows: list[dict]) -> int:
    return sum(
        1 for r in rows
        if r.get("reviewer_status") == "verified"
        and r.get("subject_id") == QUANT_SUBJECT_ID
    )


# ── unit tests: validator logic ───────────────────────────────────────────────


def test_community_resources_passes_when_verified():
    rows = [{"id": "cr-1", "usable_for_mock_generation": True, "reviewer_status": "verified"}]
    assert check_community_resources(rows) == []


def test_community_resources_fails_when_mock_gen_without_verified():
    rows = [{"id": "cr-2", "usable_for_mock_generation": True, "reviewer_status": "pending"}]
    violations = check_community_resources(rows)
    assert len(violations) == 1
    assert "cr-2" in violations[0]
    assert "usable_for_mock_generation=True" in violations[0]


def test_community_resources_safe_when_mock_gen_false():
    rows = [{"id": "cr-3", "usable_for_mock_generation": False, "reviewer_status": "pending"}]
    assert check_community_resources(rows) == []


def test_mock_qb_live_blocked_before_gate():
    rows = [{"id": "q-1", "reviewer_status": "live", "subject_id": QUANT_SUBJECT_ID}]
    violations = check_mock_question_bank(rows, verified_quant_count=50)
    assert len(violations) == 1
    assert "q-1" in violations[0]
    assert "gate not met" in violations[0]


def test_mock_qb_live_allowed_after_gate():
    rows = [{"id": "q-2", "reviewer_status": "live", "subject_id": QUANT_SUBJECT_ID}]
    violations = check_mock_question_bank(rows, verified_quant_count=200)
    assert violations == []


def test_mock_qb_verified_never_blocked():
    rows = [{"id": "q-3", "reviewer_status": "verified", "subject_id": QUANT_SUBJECT_ID}]
    assert check_mock_question_bank(rows, verified_quant_count=10) == []


def test_count_verified_quant_counts_correct_subject():
    rows = [
        {"reviewer_status": "verified", "subject_id": QUANT_SUBJECT_ID},
        {"reviewer_status": "verified", "subject_id": "other-subject"},
        {"reviewer_status": "draft",    "subject_id": QUANT_SUBJECT_ID},
    ]
    assert count_verified_quant(rows) == 1


# ── seed SQL static checks ────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def pilot_seed_sql() -> str:
    assert PILOT_SEED.exists(), f"Pilot seed not found: {PILOT_SEED}"
    return PILOT_SEED.read_text()


def _extract_insert_values(sql: str, table: str) -> list[str]:
    """Return a list of raw VALUES strings for INSERT INTO <table> blocks."""
    pattern = re.compile(
        rf"insert\s+into\s+public\.{re.escape(table)}\s*\([^)]+\)\s*values\s*(.+?)on\s+conflict",
        re.IGNORECASE | re.DOTALL,
    )
    return [m.group(1) for m in pattern.finditer(sql)]


def test_pilot_seed_no_usable_for_mock_generation_true(pilot_seed_sql):
    """No community_resources row in the pilot seed sets usable_for_mock_generation=true."""
    blocks = _extract_insert_values(pilot_seed_sql, "community_resources")
    assert blocks, "Expected at least one community_resources INSERT in the pilot seed"
    for block in blocks:
        assert "usable_for_mock_generation=true" not in block.lower(), (
            "Pilot seed sets usable_for_mock_generation=true on a community_resources row "
            "before the 200-verified-Quant gate is met. Set it to false until the gate opens."
        )


def test_pilot_seed_no_mock_qb_live_status(pilot_seed_sql):
    """No mock_question_bank row in the pilot seed carries reviewer_status='live'."""
    blocks = _extract_insert_values(pilot_seed_sql, "mock_question_bank")
    assert blocks, "Expected at least one mock_question_bank INSERT in the pilot seed"
    for block in blocks:
        # Match 'live' as a quoted SQL value, not as a substring of another word.
        assert not re.search(r"'live'", block, re.IGNORECASE), (
            "Pilot seed contains a mock_question_bank row with reviewer_status='live'. "
            "The mock-expansion gate requires ≥ 200 verified Quant questions first."
        )


def test_pilot_seed_quant_question_count_below_gate(pilot_seed_sql):
    """Pilot seed has fewer than 200 verified Quant questions — gate is correctly closed."""
    blocks = _extract_insert_values(pilot_seed_sql, "mock_question_bank")
    verified_quant_rows = 0
    for block in blocks:
        # Count tuples referencing the Quant subject UUID with 'verified' status.
        tuples = re.findall(r"\(([^()]+)\)", block, re.DOTALL)
        for tpl in tuples:
            has_quant = QUANT_SUBJECT_ID in tpl
            has_verified = "'verified'" in tpl
            if has_quant and has_verified:
                verified_quant_rows += 1

    assert verified_quant_rows < MOCK_EXPANSION_GATE, (
        f"Pilot seed has {verified_quant_rows} verified Quant questions, which meets or "
        f"exceeds the {MOCK_EXPANSION_GATE}-question gate. If this is intentional, also "
        "set usable_for_mock_generation=true on the relevant community_resources rows "
        "and update this assertion to reflect the new threshold."
    )
    # Also assert we seeded at least some Quant questions (sanity check).
    assert verified_quant_rows > 0, (
        "No verified Quant questions found in the pilot seed — check UUID references."
    )
