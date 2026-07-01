"""Unit tests for the pure EWP-2B evidence deriver (§4.12, §8.2, §10.1).

The module is imported by full path to avoid pulling in unrelated package
``__init__`` dependencies. It has no heavy imports of its own.
"""
import importlib.util
import os
import sys

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "app",
    "study_os",
    "writing_practice",
    "evidence_deriver.py",
)
_spec = importlib.util.spec_from_file_location("evidence_deriver", _MODULE_PATH)
ed = importlib.util.module_from_spec(_spec)
sys.modules["evidence_deriver"] = ed  # dataclass type resolution needs this
_spec.loader.exec_module(ed)


# Pinned digest for a fixed input — any layout change breaks this (§4.12b).
_PINNED_KEY = "d46006c93127bc6097078a8bfbc584251c41017a57c03fe29ab0b8cab1398691"

_FIXED_KW = dict(
    evidence_op="assert",
    user_id="user-1",
    evaluation_id="eval-1",
    issue_projection_id=None,
    microtopic_id=None,
    evidence_tier="production",
    source_type="descriptive_mock",
    review_event_id=None,
)


def test_pinned_evidence_key():
    assert ed.compute_evidence_key(**_FIXED_KW) == _PINNED_KEY


def test_key_is_lowercase_64_hex():
    key = ed.compute_evidence_key(**_FIXED_KW)
    assert len(key) == 64
    assert key == key.lower()
    int(key, 16)  # valid hex


def test_key_deterministic():
    assert ed.compute_evidence_key(**_FIXED_KW) == ed.compute_evidence_key(**_FIXED_KW)


def test_key_changes_when_any_field_changes():
    base = ed.compute_evidence_key(**_FIXED_KW)
    for field_name, new_val in [
        ("evidence_op", "retract"),
        ("user_id", "user-2"),
        ("evaluation_id", "eval-2"),
        ("issue_projection_id", "proj-1"),
        ("microtopic_id", "mt-1"),
        ("evidence_tier", "correction"),
        ("source_type", "other"),
        ("review_event_id", "rev-1"),
    ]:
        kw = dict(_FIXED_KW)
        kw[field_name] = new_val
        assert ed.compute_evidence_key(**kw) != base, field_name


def test_none_field_coalescing():
    # Explicit sentinels must produce the same key as None for each nullable field.
    with_nones = ed.compute_evidence_key(**_FIXED_KW)
    with_sentinels = ed.compute_evidence_key(
        evidence_op="assert",
        user_id="user-1",
        evaluation_id="eval-1",
        issue_projection_id="no_projection",
        microtopic_id="no_microtopic",
        evidence_tier="production",
        source_type="descriptive_mock",
        review_event_id="no_review",
    )
    assert with_nones == with_sentinels


def test_layout_version_constant():
    assert ed.EVIDENCE_KEY_LAYOUT_VERSION == "wev-1"
    assert ed.EVIDENCE_TIERS == ("recognition", "correction", "production", "retention")
    assert ed.SOURCE_TYPE_WRITING == "descriptive_mock"
    assert ed.SOURCE_TYPE_SENTENCE == "sentence_drill"
    assert ed.SOURCE_TYPE_PARAGRAPH == "paragraph_drill"


# ---- source_type_for_exercise ---------------------------------------------

def test_source_type_sentence_exercises():
    for et in (
        "sentence_construction",
        "sentence_correction",
        "sentence_rewrite",
        "sentence_reconstruction",
        "vocabulary_in_context",
    ):
        assert ed.source_type_for_exercise(et) == "sentence_drill", et


def test_source_type_paragraph_exercises():
    for et in (
        "paragraph_writing",
        "summary_writing",
        "precis_practice",
        "essay_practice",
        "letter_practice",
    ):
        assert ed.source_type_for_exercise(et) == "paragraph_drill", et


def test_source_type_unknown_falls_back():
    for et in ("", "objective_mock", "mystery"):
        assert ed.source_type_for_exercise(et) == "descriptive_mock", et


# ---- tier decisions --------------------------------------------------------

# Pinned digest for a fixed derive-unit input (sentence_drill, production tier).
# Changing source_type (via exercise_type) changes this hash (§4.12b).
_PINNED_DERIVE_KEY = "a70db94d7777a621a55abfb7f6a24cad8be5cf63d4f5f46edc27da87d13a6220"


def _derive(**over):
    kw = dict(
        user_id="u",
        evaluation_id="e",
        topic_id="t",
        microtopic_id=None,
        exam_id=None,
        source_entity_id="se",
        exercise_type="sentence_construction",
        has_unresolved_must_fix=False,
        resolved_issue_count=0,
        overall_status="completed",
    )
    kw.update(over)
    return ed.derive_unit_evidence(**kw)


def test_tier_correction():
    row = _derive(resolved_issue_count=2, has_unresolved_must_fix=False)
    assert row.evidence_tier == "correction"


def test_tier_production():
    row = _derive(resolved_issue_count=0, has_unresolved_must_fix=False)
    assert row.evidence_tier == "production"


def test_unresolved_must_fix_yields_no_evidence():
    # A blocking answer earns NO positive evidence — no recognition row.
    assert _derive(resolved_issue_count=5, has_unresolved_must_fix=True) is None
    assert _derive(resolved_issue_count=0, has_unresolved_must_fix=True) is None


def test_recognition_never_emitted_by_writing_path():
    # "recognition" survives only in the tuple; the writing deriver never emits it.
    for rc in (0, 3):
        for mf in (True, False):
            row = _derive(resolved_issue_count=rc, has_unresolved_must_fix=mf)
            if row is not None:
                assert row.evidence_tier != "recognition"


def test_source_type_derived_from_exercise():
    assert _derive(exercise_type="sentence_correction").source_type == "sentence_drill"
    assert _derive(exercise_type="paragraph_writing").source_type == "paragraph_drill"
    assert _derive(exercise_type="mystery").source_type == "descriptive_mock"


def test_non_terminal_status_returns_none():
    for status in ("in_progress", "pending", "failed", ""):
        assert _derive(overall_status=status) is None


def test_terminal_partial_yields_evidence():
    row = _derive(overall_status="terminal_partial")
    assert row is not None


def test_derived_row_fields_and_key():
    row = _derive(
        user_id="user-1",
        evaluation_id="eval-1",
        microtopic_id=None,
        resolved_issue_count=0,
        has_unresolved_must_fix=False,
        exercise_type="sentence_construction",
    )
    assert row.evidence_op == "assert"
    assert row.issue_projection_id is None
    assert row.source_type == "sentence_drill"
    assert row.score is None and row.confidence is None
    assert row.evidence_key == _PINNED_DERIVE_KEY  # pinned sentence_drill production input


def test_derived_key_stable_and_changes_with_exercise_type():
    pinned = dict(user_id="user-1", evaluation_id="eval-1")
    base = _derive(exercise_type="sentence_construction", **pinned).evidence_key
    assert base == _PINNED_DERIVE_KEY
    # stable across calls
    assert base == _derive(exercise_type="sentence_construction", **pinned).evidence_key
    # Different derived source_type => different key.
    assert _derive(exercise_type="paragraph_writing", **pinned).evidence_key != base
    assert _derive(exercise_type="mystery", **pinned).evidence_key != base


def test_to_dicts():
    row = _derive()
    ev = row.to_evidence_dict()
    sh = row.to_shadow_dict()
    assert "evidence_op" in ev
    assert "observed_at" not in ev
    assert "evidence_op" not in sh
    assert "processed_at" not in sh
    assert sh["delta_json"] == {}
    assert ev["evidence_key"] == sh["evidence_key"]
