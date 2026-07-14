"""Regression for the SSC CGL Tier-1 General Awareness section seed.

The demo seed ``exam_intelligence_demo_ssc_cgl.sql`` authors the fourth,
previously-missing Tier-1 section (General Awareness) so the mock-blueprint
structural envelope reflects the official four-section shape.

These tests parse the seed file directly (no DB) and assert:

  * the real GA subject row is present with the canonical governed identity
    (slug ``general-awareness`` → GA SubjectRuntimePolicy family),
  * the GA ``exam_phase_section`` is authored against that subject, and
  * the four Tier-1 sections sum to the exam_phases envelope: 100 questions,
    200 marks, 100% weightage.

GA is authored for STRUCTURAL completeness only — it is bundle-driven
current-affairs, so the seed intentionally adds NO topics / exam_topic_coverage
/ PYQ for GA. That absence is asserted here so a future accidental coverage row
(which would wrongly turn GA into a topic-mastery subject) trips this test.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SEED = (
    Path(__file__).parents[3]
    / "supabase"
    / "seeds"
    / "exam_intelligence_demo_ssc_cgl.sql"
)

GA_SUBJECT_ID = "55555555-5555-5555-5555-555555555554"
GA_SECTION_ID = "88888888-8888-8888-8888-888888888884"
TIER1_PHASE_ID = "44444444-4444-4444-4444-444444444441"


@pytest.fixture(scope="module")
def seed_sql() -> str:
    assert SEED.exists(), f"Demo seed not found: {SEED}"
    return SEED.read_text()


def test_ga_subject_row_seeded_with_canonical_identity(seed_sql):
    # slug general-awareness + subject_group general_awareness → GA family.
    assert re.search(
        rf"'{GA_SUBJECT_ID}',\s*'general-awareness',\s*"
        rf"'General Awareness',\s*'general_awareness'",
        seed_sql,
    ), "GA subject row missing or not canonically identified"


def test_ga_exam_phase_section_authored_against_ga_subject(seed_sql):
    # ('...884', '<tier1 phase>', '<ga subject>', 'General Awareness', 25,50,25,4)
    assert re.search(
        rf"'{GA_SECTION_ID}',\s*'{TIER1_PHASE_ID}',\s*"
        rf"'{GA_SUBJECT_ID}',\s*'General Awareness',\s*25,\s*50,\s*25,\s*4",
        seed_sql,
    ), "GA exam_phase_section missing or not wired to the GA subject"


def test_tier1_four_sections_sum_to_phase_envelope(seed_sql):
    # Extract every Tier-1 section tuple ('88888888-…-88[1-4]', …, q, marks, w, sort).
    rows = re.findall(
        r"'88888888-8888-8888-8888-8888888888(8[1-4])',\s*"
        r"'[^']*',\s*'[^']*',\s*'[^']*',\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)",
        seed_sql,
    )
    assert len(rows) == 4, f"expected 4 authored Tier-1 sections, found {len(rows)}"
    total_q = sum(int(q) for _sfx, q, _m, _w, _o in rows)
    total_marks = sum(int(m) for _sfx, _q, m, _w, _o in rows)
    total_weight = sum(int(w) for _sfx, _q, _m, w, _o in rows)
    assert total_q == 100
    assert total_marks == 200
    assert total_weight == 100


def test_ga_is_structure_only_no_coverage_or_topics(seed_sql):
    # GA is bundle-driven: the seed must NOT attach topics, locked coverage, or
    # PYQ to the GA subject (any of which would wrongly make GA a topic-mastery
    # subject). The GA subject id therefore appears exactly twice — once as the
    # subject row, once as the exam_phase_section's subject_id. A third
    # occurrence means something was attached to GA.
    assert seed_sql.count(GA_SUBJECT_ID) == 2, (
        "GA subject id should appear exactly twice (subject + section); another "
        "reference likely means coverage/topics/PYQ was attached to GA"
    )
