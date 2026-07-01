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


# ---- tier decisions --------------------------------------------------------

def _derive(**over):
    kw = dict(
        user_id="u",
        evaluation_id="e",
        topic_id="t",
        microtopic_id=None,
        exam_id=None,
        source_entity_id="se",
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


def test_tier_recognition_when_unresolved_must_fix():
    row = _derive(resolved_issue_count=5, has_unresolved_must_fix=True)
    assert row.evidence_tier == "recognition"


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
    )
    assert row.evidence_op == "assert"
    assert row.issue_projection_id is None
    assert row.source_type == "descriptive_mock"
    assert row.score is None and row.confidence is None
    assert row.evidence_key == _PINNED_KEY  # matches the fixed production input


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
