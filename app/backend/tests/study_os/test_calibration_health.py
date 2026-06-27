"""Health-aware calibration gate — fail-closed + legacy-plan grandfather.

Pins the third-review contract for ``app.study_os.calibration``:

  * a required-set / gate / plan READ FAILURE must surface as ``check_failed`` /
    ``CalibrationUnavailable`` (fail closed), NEVER as a silent "nothing to
    calibrate" unlock; and
  * an existing plan recorded only via the legacy free-text ``target_exam``
    slug (with a NULL ``exam_id``) must still grandfather the user.

Uses a purpose-built fake client so a specific table read can be made to raise.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.study_os import calibration

EXAM_ID = "11111111-1111-1111-1111-111111111111"
SLUG = "ssc-cgl"


class _Query:
    def __init__(self, rows, *, fail: bool):
        self._rows = rows
        self._fail = fail

    # the calibration reads chain select/eq/in_/limit then execute
    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._fail:
            raise RuntimeError("simulated read failure")
        return SimpleNamespace(data=list(self._rows))


class FakeSB:
    """Returns every seeded row for a table (filters are ignored — seed only the
    rows relevant to the case). Any table in ``fail`` raises on ``execute()``."""

    def __init__(self, tables: dict[str, list], fail: set[str] | None = None):
        self._tables = tables
        self._fail = fail or set()

    def table(self, name: str):
        return _Query(self._tables.get(name, []), fail=name in self._fail)


def _healthy_tables(**overrides) -> dict[str, list]:
    tables = {
        "exam_topic_coverage": [{"topic_id": "t1"}, {"topic_id": "t2"}],
        "topics": [
            {"id": "t1", "subject_id": "s1"},
            {"id": "t2", "subject_id": "s1"},
        ],
        "user_topic_mastery": [],  # nothing validated → s1 required
        "subjects": [{"id": "s1", "name": "Polity"}],
        "user_exam_calibration": [],
        "exams": [{"slug": SLUG}],
        "study_plans": [],
    }
    tables.update(overrides)
    return tables


# ── resolve_required_subjects health ──────────────────────────────────────


def test_resolve_required_subjects_ok_when_all_reads_succeed():
    sb = FakeSB(_healthy_tables())
    subjects, ok = calibration.resolve_required_subjects(sb, EXAM_ID, "u-1")
    assert ok is True
    assert subjects == [{"subject_id": "s1", "subject_name": "Polity"}]


def test_resolve_required_subjects_empty_is_not_a_failure():
    # No locked coverage → legitimately empty required set, ok=True.
    sb = FakeSB(_healthy_tables(exam_topic_coverage=[]))
    subjects, ok = calibration.resolve_required_subjects(sb, EXAM_ID, "u-1")
    assert ok is True
    assert subjects == []


@pytest.mark.parametrize(
    "failing_table",
    ["exam_topic_coverage", "topics", "user_topic_mastery", "subjects"],
)
def test_resolve_required_subjects_read_failure_reports_unhealthy(failing_table):
    sb = FakeSB(_healthy_tables(), fail={failing_table})
    subjects, ok = calibration.resolve_required_subjects(sb, EXAM_ID, "u-1")
    assert ok is False  # MUST fail closed, not be treated as "nothing to calibrate"
    assert subjects == []


# ── evaluate_calibration / calibration_required fail closed ────────────────


@pytest.mark.parametrize(
    "failing_table",
    ["exam_topic_coverage", "topics", "user_topic_mastery", "subjects", "user_exam_calibration"],
)
def test_evaluate_check_failed_on_any_read_failure(failing_table):
    sb = FakeSB(_healthy_tables(), fail={failing_table})
    result = calibration.evaluate_calibration(sb, "u-1", EXAM_ID)
    assert result["check_failed"] is True
    assert result["required"] is None  # never a silent unlock


def test_gate_read_failure_is_check_failed():
    sb = FakeSB(_healthy_tables(), fail={"user_exam_calibration"})
    result = calibration.evaluate_calibration(sb, "u-1", EXAM_ID)
    assert result["check_failed"] is True


@pytest.mark.parametrize(
    "failing_table",
    ["exam_topic_coverage", "topics", "user_topic_mastery", "subjects", "user_exam_calibration"],
)
def test_calibration_required_raises_when_unhealthy(failing_table):
    sb = FakeSB(_healthy_tables(), fail={failing_table})
    with pytest.raises(calibration.CalibrationUnavailable):
        calibration.calibration_required(sb, "u-1", EXAM_ID)


def test_calibration_required_true_for_fresh_user():
    # required subjects exist, no gate, no plan → must calibrate.
    sb = FakeSB(_healthy_tables())
    assert calibration.calibration_required(sb, "u-1", EXAM_ID) is True


def test_calibration_required_false_when_gate_completed():
    sb = FakeSB(
        _healthy_tables(
            user_exam_calibration=[{"status": "completed", "required_subject_set_hash": "x"}]
        )
    )
    assert calibration.calibration_required(sb, "u-1", EXAM_ID) is False


def test_empty_required_set_auto_calibrated_not_check_failed():
    sb = FakeSB(_healthy_tables(exam_topic_coverage=[]))
    result = calibration.evaluate_calibration(sb, "u-1", EXAM_ID)
    assert result["check_failed"] is False
    assert result["required"] is False


# ── legacy-plan grandfather ────────────────────────────────────────────────


def test_existing_plan_matches_canonical_exam_id_column():
    sb = FakeSB(
        _healthy_tables(study_plans=[{"id": "p1", "exam_id": EXAM_ID, "target_exam": None}])
    )
    exists, ok = calibration.has_existing_plan(sb, "u-1", EXAM_ID)
    assert ok is True
    assert exists is True


def test_existing_plan_matches_legacy_target_exam_slug_with_null_exam_id():
    # The regression the reviewer called out: exam_id NULL, target_exam = slug.
    sb = FakeSB(
        _healthy_tables(study_plans=[{"id": "p1", "exam_id": None, "target_exam": SLUG}])
    )
    exists, ok = calibration.has_existing_plan(sb, "u-1", EXAM_ID)
    assert ok is True
    assert exists is True


def test_legacy_slug_plan_grandfathers_user_out_of_gate():
    sb = FakeSB(
        _healthy_tables(study_plans=[{"id": "p1", "exam_id": None, "target_exam": SLUG}])
    )
    # required subjects exist + no gate, but a legacy plan exists → not required.
    assert calibration.calibration_required(sb, "u-1", EXAM_ID) is False


def test_has_existing_plan_read_failure_reports_unhealthy():
    sb = FakeSB(_healthy_tables(), fail={"study_plans"})
    exists, ok = calibration.has_existing_plan(sb, "u-1", EXAM_ID)
    assert ok is False
    assert exists is False
