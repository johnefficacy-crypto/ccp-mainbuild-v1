"""PLAN-UI-01 — the seven-day planner board and its three mutations.

The test that matters is first: a user arranges a day, the nightly regeneration
runs, and their placements are still there IN THE RIGHT ORDER. Everything else
in this file exists to keep that one honest.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest

from tests.persona_questions._stub import SBStub
from tests.study_os.test_planner import _seed

from app.study_os import planner_board as board
from app.study_os.planner import apply_plan


def _dates() -> list[str]:
    return board.window_dates()


def _seed_with_plan(**overrides: Any) -> SBStub:
    seed = _seed()
    seed["study_plans"] = [
        {
            "id": "plan-1",
            "user_id": "u-1",
            "status": "active",
            "title": "SSC CGL Study Plan",
            "current_plan_version_id": None,
        }
    ]
    seed["study_tasks"] = []
    seed.update(overrides)
    return SBStub(seed)


def _task(
    task_id: str,
    topic_id: str,
    *,
    day: str,
    source: str = "planner",
    ordinal: int | None = None,
    score: float = 50.0,
    user_id: str = "u-1",
) -> dict[str, Any]:
    return {
        "id": task_id,
        "user_id": user_id,
        "plan_id": "plan-1",
        "topic_id": topic_id,
        "topic": f"Topic {topic_id}",
        "title": f"Topic {topic_id} · Study",
        "subject": "Quantitative Aptitude",
        "subject_id": "s1",
        "task_type": "concept",
        "status": "planned",
        "scheduled_date": day,
        "day_label": "Today",
        "planned_minutes": 25,
        "priority_score": score,
        "source": source,
        "day_ordinal": ordinal,
    }


def _ids_on(sb: SBStub, day: str) -> list[str]:
    rows = [r for r in sb.db["study_tasks"] if r.get("scheduled_date") == day]
    return [r["id"] for r in sorted(rows, key=board._sort_key)]


# ── THE ONE THAT MATTERS ────────────────────────────────────────────────


def test_arranged_day_survives_a_regeneration_in_the_right_order():
    """Arrange today, regenerate, and the arrangement is intact — order included."""
    days = _dates()
    today = days[0]
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [
        _task("a", "t1", day=today, score=90),
        _task("b", "t2", day=today, score=80),
        _task("c", "t3", day=today, score=70),
    ]

    # The user arranges the day: lowest-priority card to the top, then the two
    # others behind it. All three are planner-generated cards before the drag.
    board.move_task(sb, "u-1", "c", scheduled_date=today, position=0)
    board.move_task(sb, "u-1", "a", scheduled_date=today, position=1)
    board.move_task(sb, "u-1", "b", scheduled_date=today, position=2)
    assert _ids_on(sb, today) == ["c", "a", "b"]

    out = apply_plan(sb, "u-1")
    assert out["applied"] is True

    survivors = _ids_on(sb, today)
    assert [t for t in survivors if t in {"a", "b", "c"}] == ["c", "a", "b"], (
        "the regeneration destroyed the user's arrangement"
    )
    for tid in ("a", "b", "c"):
        row = next(r for r in sb.db["study_tasks"] if r["id"] == tid)
        assert row["source"] == "user"
        assert row["day_ordinal"] is not None


def test_a_card_the_user_never_touched_is_still_the_planners_to_replace():
    """The other half of the contract, and what the UI has to communicate.

    Protection follows the user's action, not the day. A card they never
    dragged stays planner-owned and the sweep still replaces it — that is the
    distinction requirement 4 asks the surface to state out loud.
    """
    days = _dates()
    today = days[0]
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [
        _task("moved", "t1", day=today, score=90),
        _task("untouched", "t2", day=today, score=80),
    ]

    board.move_task(sb, "u-1", "moved", scheduled_date=today, position=0)
    apply_plan(sb, "u-1")

    ids = {r["id"] for r in sb.db["study_tasks"]}
    assert "moved" in ids
    assert "untouched" not in ids


def test_moving_a_planner_task_makes_it_a_user_placement():
    """Dragging IS choosing. Without the stamp the 03:00 sweep undoes the move."""
    days = _dates()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [_task("a", "t1", day=days[0], source="planner")]

    card = board.move_task(sb, "u-1", "a", scheduled_date=days[2], position=0)

    assert card["source"] == "user"
    assert card["placed_by_user"] is True
    assert card["scheduled_date"] == days[2]


# ── board read ──────────────────────────────────────────────────────────


def test_board_returns_seven_days_with_today_first():
    sb = _seed_with_plan()
    out = board.get_board(sb, "u-1")
    assert [d["date"] for d in out["days"]] == _dates()
    assert out["days"][0]["label"] == "Today"
    assert out["days"][1]["label"] == "Tomorrow"


def test_board_orders_unarranged_days_by_priority_and_arranged_days_by_ordinal():
    days = _dates()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [
        # day 0: never arranged — priority order, highest first
        _task("p-low", "t3", day=days[0], score=10),
        _task("p-high", "t1", day=days[0], score=99),
        # day 1: arranged — ordinal wins over priority
        _task("o-second", "t2", day=days[1], ordinal=1, score=99),
        _task("o-first", "t4", day=days[1], ordinal=0, score=1),
    ]
    out = board.get_board(sb, "u-1")
    assert [t["id"] for t in out["days"][0]["tasks"]] == ["p-high", "p-low"]
    assert [t["id"] for t in out["days"][1]["tasks"]] == ["o-first", "o-second"]


def test_board_excludes_tasks_outside_the_window():
    days = _dates()
    past = (date.fromisoformat(days[0]) - timedelta(days=1)).isoformat()
    far = (date.fromisoformat(days[0]) + timedelta(days=30)).isoformat()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [
        _task("in", "t1", day=days[3]),
        _task("past", "t2", day=past),
        _task("far", "t3", day=far),
    ]
    out = board.get_board(sb, "u-1")
    rendered = {t["id"] for d in out["days"] for t in d["tasks"]}
    assert rendered == {"in"}


def test_board_without_a_plan_returns_seven_empty_days_not_an_error():
    sb = SBStub(_seed())
    out = board.get_board(sb, "u-1")
    assert out["plan_id"] is None
    assert len(out["days"]) == 7
    assert all(d["tasks"] == [] for d in out["days"])


def test_board_read_failure_raises_rather_than_rendering_an_empty_week():
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [_task("a", "t1", day=_dates()[0])]

    original_table = sb.table

    def _table(name):
        q = original_table(name)
        if name == "study_tasks":
            def _boom():
                raise RuntimeError("study_tasks read failed")
            q.execute = _boom  # type: ignore[assignment]
        return q

    sb.table = _table  # type: ignore[assignment]

    with pytest.raises(board.BoardError) as err:
        board.get_board(sb, "u-1")
    assert err.value.code == "board_read_failed"
    assert err.value.status == 503


def test_card_prefers_the_planners_own_sentence_and_always_has_one():
    """The planner's evidence sentence when it exists; a template when it doesn't.

    A user-created task has no `why_this_task.summary` — only the planner writes
    one — so the card must still say something rather than render an empty line
    for half the board.
    """
    days = _dates()
    sb = _seed_with_plan()
    planner_row = _task("planner-card", "t1", day=days[0], source="planner")
    planner_row["why_this_task"] = {"summary": "Percentage is a verified high-yield topic."}
    user_row = _task("user-card", "t2", day=days[0], source="user")
    user_row["why_this_task"] = {"placed_by": "user"}
    sb.db["study_tasks"] = [planner_row, user_row]

    cards = {c["id"]: c for c in board.get_board(sb, "u-1")["days"][0]["tasks"]}

    assert cards["planner-card"]["why"] == "Percentage is a verified high-yield topic."
    assert cards["user-card"]["why"]
    assert "verified high-yield" not in cards["user-card"]["why"]


# ── palette ─────────────────────────────────────────────────────────────


def test_candidates_keep_scheduled_topics_and_say_which_day():
    """PLAN-UI-02 changed this contract deliberately.

    Scheduled topics used to be dropped from the payload, which left a user
    unable to tell "not in my syllabus" from "already on my board" — the topic
    simply was not there either way. They are now returned carrying the day
    they sit on, and the palette dims them instead of hiding them.
    """
    days = _dates()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [_task("a", "t1", day=days[4])]

    out = board.list_candidates(sb, "u-1")
    by_topic = {i["topic_id"]: i for i in out["items"]}

    assert by_topic["t1"]["scheduled_date"] == days[4]
    assert {"t2", "t3", "t4"} <= set(by_topic)
    assert all(by_topic[t]["scheduled_date"] is None for t in ("t2", "t3", "t4"))
    # draft coverage never reaches a learner surface
    assert "t5" not in by_topic


def test_candidates_report_the_earliest_day_when_a_topic_sits_on_two():
    days = _dates()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [
        _task("late", "t1", day=days[5]),
        _task("early", "t1", day=days[1]),
    ]

    out = board.list_candidates(sb, "u-1")
    by_topic = {i["topic_id"]: i for i in out["items"]}

    assert by_topic["t1"]["scheduled_date"] == days[1]


def test_candidates_exclude_muted_topics_and_sort_by_priority():
    sb = _seed_with_plan()
    sb.db["user_study_plan_preferences"] = [
        {"user_id": "u-1", "focus": "balanced", "muted_topic_ids": ["t2"],
         "pinned_topic_ids": [], "auto_regenerate": True}
    ]
    out = board.list_candidates(sb, "u-1")
    topic_ids = [i["topic_id"] for i in out["items"]]
    scores = [i["exam_priority_score"] for i in out["items"]]

    assert "t2" not in topic_ids
    assert scores == sorted(scores, reverse=True)


# ── create ──────────────────────────────────────────────────────────────


def test_create_places_a_user_task_at_the_requested_position():
    days = _dates()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [
        _task("a", "t1", day=days[0], ordinal=0),
        _task("b", "t2", day=days[0], ordinal=1),
    ]

    card = board.create_user_task(
        sb, "u-1", topic_id="t3", scheduled_date=days[0], position=1
    )

    assert card["source"] == "user"
    assert card["topic_id"] == "t3"
    assert _ids_on(sb, days[0]) == ["a", card["id"], "b"]


def test_create_rejects_a_topic_outside_the_users_locked_coverage():
    sb = _seed_with_plan()
    with pytest.raises(board.BoardError) as err:
        board.create_user_task(
            sb, "u-1", topic_id="t5", scheduled_date=_dates()[0]
        )
    assert err.value.code == "topic_not_available"
    assert err.value.status == 400
    assert sb.db["study_tasks"] == []


def test_create_refuses_a_duplicate_topic_on_the_same_day():
    days = _dates()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [_task("a", "t1", day=days[0])]

    with pytest.raises(board.BoardError) as err:
        board.create_user_task(sb, "u-1", topic_id="t1", scheduled_date=days[0])
    assert err.value.code == "duplicate_topic"
    assert err.value.status == 409
    assert len(sb.db["study_tasks"]) == 1


def test_create_allows_the_same_topic_on_a_different_day():
    days = _dates()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [_task("a", "t1", day=days[0])]

    card = board.create_user_task(sb, "u-1", topic_id="t1", scheduled_date=days[3])
    assert card["scheduled_date"] == days[3]


# ── delete ──────────────────────────────────────────────────────────────


def test_delete_removes_the_task_and_compacts_the_day():
    days = _dates()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [
        _task("a", "t1", day=days[0], ordinal=0),
        _task("b", "t2", day=days[0], ordinal=1),
        _task("c", "t3", day=days[0], ordinal=2),
    ]

    out = board.delete_task(sb, "u-1", "b")

    assert out == {"id": "b", "deleted": True, "scheduled_date": days[0]}
    assert _ids_on(sb, days[0]) == ["a", "c"]
    assert [
        r["day_ordinal"] for r in sorted(sb.db["study_tasks"], key=board._sort_key)
    ] == [0, 1]


# ── ownership ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("mutation", ["move", "delete"])
def test_another_users_task_is_not_found_and_never_mutates(mutation):
    days = _dates()
    sb = _seed_with_plan()
    theirs = _task("theirs", "t1", day=days[0], user_id="u-2", ordinal=0)
    sb.db["study_tasks"] = [theirs]
    before = dict(theirs)

    with pytest.raises(board.BoardError) as err:
        if mutation == "move":
            board.move_task(sb, "u-1", "theirs", scheduled_date=days[1], position=0)
        else:
            board.delete_task(sb, "u-1", "theirs")

    assert err.value.status == 404
    assert sb.db["study_tasks"] == [before]


# ── date validation ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad",
    ["", "not-a-date", "2026-13-45", "13/09/2026", None, 20260913],
)
def test_invalid_dates_are_rejected(bad):
    with pytest.raises(board.BoardError) as err:
        board.validate_board_date(bad)
    assert err.value.code == "invalid_date"


def test_dates_outside_the_seven_day_window_are_rejected_not_clamped():
    days = _dates()
    yesterday = (date.fromisoformat(days[0]) - timedelta(days=1)).isoformat()
    eighth = (date.fromisoformat(days[0]) + timedelta(days=7)).isoformat()
    for bad in (yesterday, eighth):
        with pytest.raises(board.BoardError) as err:
            board.validate_board_date(bad)
        assert err.value.code == "date_out_of_window"


def test_move_to_an_invalid_date_rejects_before_touching_the_row():
    days = _dates()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [_task("a", "t1", day=days[0], ordinal=0)]
    before = dict(sb.db["study_tasks"][0])

    with pytest.raises(board.BoardError):
        board.move_task(sb, "u-1", "a", scheduled_date="2099-01-01", position=0)

    assert sb.db["study_tasks"] == [before]


# ── concurrency ─────────────────────────────────────────────────────────


def test_a_concurrent_double_move_converges_and_never_duplicates():
    """Two moves of the same card land one row, at the last requested slot."""
    days = _dates()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [
        _task("a", "t1", day=days[0], ordinal=0),
        _task("b", "t2", day=days[0], ordinal=1),
        _task("c", "t3", day=days[0], ordinal=2),
    ]

    board.move_task(sb, "u-1", "c", scheduled_date=days[1], position=0)
    board.move_task(sb, "u-1", "c", scheduled_date=days[1], position=0)

    rows = [r for r in sb.db["study_tasks"] if r["id"] == "c"]
    assert len(rows) == 1
    assert rows[0]["scheduled_date"] == days[1]
    assert _ids_on(sb, days[0]) == ["a", "b"]
    assert [r["day_ordinal"] for r in sb.db["study_tasks"] if r["id"] in {"a", "b"}] == [0, 1]


def test_position_beyond_the_day_clamps_to_the_end_rather_than_failing():
    days = _dates()
    sb = _seed_with_plan()
    sb.db["study_tasks"] = [
        _task("a", "t1", day=days[0], ordinal=0),
        _task("b", "t2", day=days[0], ordinal=1),
    ]
    board.move_task(sb, "u-1", "a", scheduled_date=days[0], position=99)
    assert _ids_on(sb, days[0]) == ["b", "a"]


# ── COV-DIM-01: recurrence band on the palette ──────────────────────────


def test_candidates_carry_the_predictability_band():
    """PRED-01's band is percentile-within-subject-paper, so unlike the raw
    priority beside it, it means the same thing for an optional as for GS.
    It is the one comparable signal already on the coverage row."""
    sb = _seed_with_plan()
    for row, band in (("cov-2", "near_certain"), ("cov-3", "occasional")):
        next(c for c in sb.db["exam_topic_coverage"] if c["id"] == row)[
            "predictability_band"
        ] = band

    out = board.list_candidates(sb, "u-1")
    by_topic = {i["topic_id"]: i for i in out["items"]}

    assert by_topic["t2"]["predictability_band"] == "near_certain"
    assert by_topic["t3"]["predictability_band"] == "occasional"


def test_candidate_without_year_evidence_carries_no_band():
    """382 derived rows and all 13 authored ones have no band. An absent band
    is the honest answer — never a default."""
    sb = _seed_with_plan()
    out = board.list_candidates(sb, "u-1")

    assert all(i["predictability_band"] is None for i in out["items"])


def test_candidates_carry_the_rows_real_priority_not_zero():
    """D16: the loader emits `coverage_priority`; this reader asked for
    `exam_priority_score`, a key that has never existed on those rows, so every
    candidate scored 0.0 and the sort fell back to alphabetical."""
    sb = _seed_with_plan()
    out = board.list_candidates(sb, "u-1")
    by_topic = {i["topic_id"]: i for i in out["items"]}

    # Seeded scores: t2=80, t3=60, t4=50 (t1 is on the board).
    assert by_topic["t2"]["exam_priority_score"] == 80.0
    assert by_topic["t3"]["exam_priority_score"] == 60.0
    assert by_topic["t4"]["exam_priority_score"] == 50.0
    assert all(i["exam_priority_score"] > 0 for i in out["items"])


def test_candidates_rank_on_standing_within_source_basis():
    """RANK-SCALE-01: this read is exam-wide, so thirteen authored rows
    (min 60) must not outrank two thousand derived ones (max 36) on the raw
    column alone. The derived top row outranks the authored bottom row."""
    sb = _seed_with_plan()
    cov = {c["id"]: c for c in sb.db["exam_topic_coverage"]}
    # t2 is the best of its (derived) kind; t3 the worst of the authored kind.
    cov["cov-2"].update({"source_basis": "evidence_derived", "exam_priority_score": 30})
    cov["cov-4"].update({"source_basis": "evidence_derived", "exam_priority_score": 5})
    cov["cov-3"].update({"source_basis": "official_syllabus", "exam_priority_score": 60})

    out = board.list_candidates(sb, "u-1")
    order = [i["topic_id"] for i in out["items"]]

    # Raw order would be t3 (60), t2 (30), t4 (5). Standing puts the best
    # derived row level with the only authored one, and t4 stays last.
    assert order.index("t2") < order.index("t4")
    assert out["items"][0]["comparable_priority"] >= out["items"][-1][
        "comparable_priority"
    ]
    # The raw column is untouched beside it (t1 keeps its seeded 88 — nothing
    # is on the board in this fixture, so every locked topic is a candidate).
    assert {i["topic_id"]: i["exam_priority_score"] for i in out["items"]} == {
        "t1": 88.0,
        "t2": 30.0,
        "t3": 60.0,
        "t4": 5.0,
    }


# ── PLAN-UI-02: what the two-pane palette needs ─────────────────────────


def _seed_with_syllabus():
    """Coverage across two subjects, one of them the user's chosen optional,
    with a macro topic that carries no coverage row of its own."""
    sb = _seed_with_plan()
    sb.db["topics"] = [
        {"id": "t1", "name": "Percentage", "subject_id": "s1",
         "parent_topic_id": "macro-1", "level": "microtopic", "is_active": True},
        {"id": "t2", "name": "Ratio", "subject_id": "s1",
         "parent_topic_id": "macro-1", "level": "microtopic", "is_active": True},
        {"id": "t3", "name": "Arithmetic", "subject_id": "s1",
         "parent_topic_id": None, "level": "topic", "is_active": True},
        {"id": "t4", "name": "State theory", "subject_id": "s2",
         "parent_topic_id": "macro-2", "level": "microtopic", "is_active": True},
        # macro-1 has NO coverage row: purely structural, so its name is only
        # reachable by the parent-name read.
        {"id": "macro-1", "name": "Quantitative methods", "subject_id": "s1",
         "parent_topic_id": None, "level": "topic", "is_active": True},
        {"id": "macro-2", "name": "Political theory", "subject_id": "s2",
         "parent_topic_id": None, "level": "topic", "is_active": True},
    ]
    sb.db["subjects"] = [
        {"id": "s1", "name": "Quantitative Aptitude", "slug": "quant"},
        {"id": "s2", "name": "PSIR Paper-1", "slug": "psir-p1"},
    ]
    for row in sb.db["exam_topic_coverage"]:
        row["section_id"] = "sec-1" if row["topic_id"] in ("t1", "t2", "t3") else "sec-2"
    sb.db["exam_topic_coverage"].append(
        {"id": "cov-6", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
         "exam_phase_id": "ph1", "topic_id": "t4", "section_id": "sec-2",
         "exam_priority_score": 40, "is_high_yield": False,
         "confidence_score": 0.6, "reviewer_status": "locked"}
    )
    sb.db["exam_phase_sections"] = [
        {"id": "sec-1", "exam_phase_id": "ph1", "subject_id": "s1",
         "selection_kind": "compulsory", "elective_group": None},
        {"id": "sec-2", "exam_phase_id": "ph1", "subject_id": "s2",
         "selection_kind": "elective", "elective_group": "optional"},
    ]
    return sb


def test_candidates_carry_their_syllabus_position():
    sb = _seed_with_syllabus()
    out = board.list_candidates(sb, "u-1")
    by_topic = {i["topic_id"]: i for i in out["items"]}

    # A microtopic names the macro topic it sits under, even though that macro
    # topic has no coverage row of its own.
    assert by_topic["t1"]["parent_topic_id"] == "macro-1"
    assert by_topic["t1"]["parent_topic"] == "Quantitative methods"
    # A root topic has no parent and files directly under its subject.
    assert by_topic["t3"]["parent_topic_id"] is None
    assert by_topic["t3"]["parent_topic"] is None


def test_candidates_report_whether_the_subject_is_compulsory_or_elective():
    """Read from the section (migration 287), never from a subject slug."""
    sb = _seed_with_syllabus()
    out = board.list_candidates(sb, "u-1")
    by_topic = {i["topic_id"]: i for i in out["items"]}

    assert by_topic["t1"]["selection_kind"] == "compulsory"
    assert by_topic["t4"]["selection_kind"] == "elective"


def test_a_row_with_no_section_reads_as_compulsory():
    """Fail safe: an unclassified subject stays visible rather than hiding
    under a heading the user never opens."""
    sb = _seed_with_syllabus()
    for row in sb.db["exam_topic_coverage"]:
        row["section_id"] = None

    out = board.list_candidates(sb, "u-1")

    assert {i["selection_kind"] for i in out["items"]} == {"compulsory"}


def test_palette_reads_do_not_scale_with_topic_count():
    """Three indexed reads per request, whatever the syllabus size."""
    sb = _seed_with_syllabus()
    reads: dict[str, int] = {"topics": 0, "exam_phase_sections": 0}
    real_table = sb.table

    def _counting_table(name):
        if name in reads:
            reads[name] += 1
        return real_table(name)

    sb.table = _counting_table  # type: ignore[method-assign]
    out = board.list_candidates(sb, "u-1")

    # Four topics, four items. The seed carries TWO coverage rows for t4
    # (cov-4 and cov-6) and this assertion used to read `>= 5`, counting that
    # duplicate as a candidate — the same defect COV-PHASE-01 fixes live, where
    # 1,317 Mains topics each held a second row on a template phase.
    assert len(out["items"]) == 4
    assert len({i["topic_id"] for i in out["items"]}) == 4
    # `topics` is read by two logical callers: the coverage loader for the rows
    # themselves, and the parent-name read the loader could not carry. Each is a
    # paginated walk, so each costs its pages plus the request that proves it
    # reached the end — the guarantee is that neither scales with topic count.
    assert reads["topics"] == 3
    assert reads["exam_phase_sections"] == 1


def test_parent_name_read_failure_leaves_the_palette_usable():
    """An unnamed parent groups under its subject — a smaller loss than a
    failed palette."""

    class _NoTopicNames(SBStub):
        def __init__(self, db, block_after):
            super().__init__(db)
            self._calls = 0
            self._block_after = block_after

        def table(self, name):
            if name == "topics":
                self._calls += 1
                if self._calls > self._block_after:
                    raise RuntimeError("connection refused")
            return super().table(name)

    seeded = _seed_with_syllabus()
    # One paginated read of `topics` is two requests against a stub that
    # ignores .range(): the page, then the one that proves there is no more.
    # Blocking after those two is what leaves the parent-name read failing.
    sb = _NoTopicNames(seeded.db, block_after=2)
    out = board.list_candidates(sb, "u-1")
    by_topic = {i["topic_id"]: i for i in out["items"]}

    assert by_topic["t1"]["parent_topic_id"] == "macro-1"
    assert by_topic["t1"]["parent_topic"] is None
    assert out["read_error"] is False
