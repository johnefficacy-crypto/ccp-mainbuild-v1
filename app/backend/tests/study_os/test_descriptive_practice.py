"""Descriptive answer-writing practice — catalogue, questions, attempts.

The corpus this serves is ~12k verified descriptive PYQ rows whose shape lives
almost entirely in two jsonb columns, so most of what can go wrong here is a
metadata key read wrongly rather than a query written wrongly. The fixtures
below mirror the real shape: marks present on a minority, `word_limit` usually
null, `requires_map_sheet` sometimes a string.
"""
from __future__ import annotations

from typing import Any

import pytest

from tests.persona_questions._stub import SBStub

from app.study_os import descriptive as d

EXAM = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"  # UPSC CSE
USER_A = "user-a"
USER_B = "user-b"


def _seed() -> dict[str, Any]:
    """Two real papers, one thematic paper, one retired bucket."""
    return {
        "pyq_papers": [
            {
                "id": "paper-psir-1",
                "exam_id": EXAM,
                "year": 2024,
                "paper_code": "PSIR-I-2024",
                "trust_status": "verified",
                "metadata": {
                    "paper_kind": "mains_optional",
                    "corpus_half": "papers",
                    "optional_subject": "PSIR",
                    "optional_paper_number": 1,
                    "split_from_bucket_id": "bucket-psir",
                },
            },
            {
                "id": "paper-psir-2",
                "exam_id": EXAM,
                "year": 2023,
                "paper_code": "PSIR-I-2023",
                "trust_status": "verified",
                "metadata": {
                    "paper_kind": "mains_optional",
                    "corpus_half": "papers",
                    "optional_subject": "PSIR",
                    "optional_paper_number": 1,
                },
            },
            {
                "id": "paper-thematic",
                "exam_id": EXAM,
                "year": None,
                "paper_code": "PSIR-THEMATIC",
                "trust_status": "verified",
                "metadata": {
                    "paper_kind": "mains_optional",
                    "corpus_half": "thematic",
                    "optional_subject": "PSIR",
                },
            },
            {
                # The bucket the real papers were split out of. Serving it would
                # double every question it contains.
                "id": "bucket-psir",
                "exam_id": EXAM,
                "year": None,
                "paper_code": "PSIR-BUCKET",
                "trust_status": "verified",
                "metadata": {
                    "paper_kind": "mains_optional",
                    "corpus_half": "papers",
                    "retired": True,
                },
            },
        ],
        "pyq_questions": [
            # paper-psir-1: a stem, its sub-part, a marks-less question, a map one
            {
                "id": "q-stem",
                "pyq_paper_id": "paper-psir-1",
                "question_number": 1,
                "question_text": "Answer the following in about 150 words each:",
                "question_type": "descriptive",
                "reviewer_status": "verified",
                "metadata": {"optional_subject": "PSIR", "optional_paper_number": 1},
            },
            {
                "id": "q-subpart",
                "pyq_paper_id": "paper-psir-1",
                "question_number": 2,
                "question_text": "Examine the relevance of Gandhian thought today.",
                "question_type": "descriptive",
                "reviewer_status": "verified",
                "metadata": {
                    "optional_subject": "PSIR",
                    "optional_paper_number": 1,
                    "parent_question_number": 1,
                    "marks": 10,
                    "marks_source": "official",
                    "word_limit": 150,
                    "verified_against_official": True,
                },
            },
            {
                "id": "q-no-marks",
                "pyq_paper_id": "paper-psir-1",
                "question_number": 3,
                "question_text": "Discuss the idea of constitutional morality.",
                "question_type": "descriptive",
                "reviewer_status": "verified",
                "metadata": {"optional_subject": "PSIR", "optional_paper_number": 1},
            },
            {
                "id": "q-map",
                "pyq_paper_id": "paper-psir-1",
                "question_number": 4,
                "question_text": "On the outline map, mark the following.",
                "question_type": "descriptive",
                "reviewer_status": "verified",
                # A STRING true, as the extractor has emitted.
                "metadata": {"optional_subject": "PSIR", "requires_map_sheet": "true"},
            },
            # paper-psir-2
            {
                "id": "q-2023",
                "pyq_paper_id": "paper-psir-2",
                "question_number": 1,
                "question_text": "Critically evaluate the theory of justice.",
                "question_type": "descriptive",
                "reviewer_status": "verified",
                "metadata": {"optional_subject": "PSIR", "marks": 15},
            },
            # thematic half
            {
                "id": "q-theme-tagged",
                "pyq_paper_id": "paper-thematic",
                "question_number": None,
                "question_text": "Explain the concept of sovereignty.",
                "question_type": "descriptive",
                "reviewer_status": "verified",
                "metadata": {"optional_subject": "PSIR"},
            },
            {
                "id": "q-theme-untagged",
                "pyq_paper_id": "paper-thematic",
                "question_number": None,
                "question_text": "Comment on federal balance.",
                "question_type": "descriptive",
                "reviewer_status": "verified",
                "metadata": {"optional_subject": "PSIR"},
            },
            # the retired bucket's copy — must never surface
            {
                "id": "q-bucket",
                "pyq_paper_id": "bucket-psir",
                "question_number": 1,
                "question_text": "Examine the relevance of Gandhian thought today.",
                "question_type": "descriptive",
                "reviewer_status": "verified",
                "metadata": {"optional_subject": "PSIR"},
            },
            # wrong type / wrong status — neither is descriptive practice
            {
                "id": "q-mcq",
                "pyq_paper_id": "paper-psir-1",
                "question_number": 9,
                "question_text": "Which one of the following?",
                "question_type": "mcq",
                "reviewer_status": "verified",
                "metadata": {},
            },
            {
                "id": "q-pending",
                "pyq_paper_id": "paper-psir-1",
                "question_number": 10,
                "question_text": "Not yet reviewed.",
                "question_type": "descriptive",
                "reviewer_status": "pending",
                "metadata": {},
            },
        ],
        "pyq_question_topic_tags": [
            {
                "question_id": "q-theme-tagged",
                "topic_id": "topic-sovereignty",
                "tag_role": "primary",
                "reviewer_status": "verified",
            },
            # secondary + unverified tags must not become themes
            {
                "question_id": "q-theme-untagged",
                "topic_id": "topic-federalism",
                "tag_role": "secondary",
                "reviewer_status": "verified",
            },
            {
                "question_id": "q-theme-untagged",
                "topic_id": "topic-sovereignty",
                "tag_role": "primary",
                "reviewer_status": "pending",
            },
        ],
        "topics": [
            {"id": "topic-sovereignty", "name": "Sovereignty"},
            {"id": "topic-federalism", "name": "Federalism"},
        ],
        "descriptive_attempts": [],
    }


def _sb() -> SBStub:
    return SBStub(_seed())


# ── the shared word rule ─────────────────────────────────────────────────
#
# The JS half is pinned against the SAME fixtures in
# `features/study/essay/__tests__/wordCountParity.test.js`. Both files read from
# `tests/fixtures/word_count_cases.json` so neither can drift alone.


def _cases() -> list[dict[str, Any]]:
    import json
    import pathlib

    path = (
        pathlib.Path(__file__).resolve().parents[1]
        / "fixtures"
        / "word_count_cases.json"
    )
    return json.loads(path.read_text())["cases"]


def test_word_count_matches_the_shared_fixtures():
    for case in _cases():
        assert d.word_count(case["text"]) == case["expected"], case["name"]


def test_word_count_treats_a_hyphenated_compound_as_one_word():
    assert d.word_count("self-reliance is swaraj") == 3


def test_word_count_treats_every_whitespace_run_as_one_separator():
    assert d.word_count("one\n\ntwo\t\tthree    four") == 4


def test_word_count_counts_devanagari_the_same_way():
    assert d.word_count("संविधान की नैतिकता पर चर्चा") == 5


def test_word_count_of_nothing_is_zero():
    for empty in (None, "", "   ", "\n\t "):
        assert d.word_count(empty) == 0


# ── timer target ─────────────────────────────────────────────────────────


def test_timer_target_is_marks_times_seventy_two():
    assert d.timer_target_for(10) == 720
    assert d.timer_target_for(15) == 1080


def test_timer_target_is_none_without_marks():
    """~87% of the corpus. Absent marks is the common case, not an error."""
    for missing in (None, 0, "", "abc", -5):
        assert d.timer_target_for(missing) is None


# ── catalogue ────────────────────────────────────────────────────────────


def test_catalog_excludes_retired_buckets_and_thematic_from_papers():
    out = d.get_catalog(_sb(), EXAM)
    paper_ids = {p["id"] for p in out["papers"]}

    assert paper_ids == {"paper-psir-1", "paper-psir-2"}
    assert "bucket-psir" not in paper_ids
    assert "paper-thematic" not in paper_ids


def test_thematic_questions_appear_under_themes_grouped_by_verified_primary_tag():
    out = d.get_catalog(_sb(), EXAM)
    by_theme = {t["theme"]: t["question_count"] for t in out["themes"]}

    assert by_theme.get("Sovereignty") == 1
    # A secondary tag and an unverified primary tag are both non-themes, so this
    # question lands in the explicit bucket rather than vanishing.
    assert by_theme.get(d.UNTAGGED_THEME) == 1
    assert "Federalism" not in by_theme


def test_catalog_counts_only_verified_descriptive_questions():
    out = d.get_catalog(_sb(), EXAM)
    # 4 real-paper + 2 thematic. The mcq, the pending row and the bucket copy
    # are all excluded — and so is the map question, which list_questions also
    # refuses to serve. A count that includes questions the surface will not
    # open is a promise it cannot keep.
    assert out["total_questions"] == 6
    assert sum(s["question_count"] for s in out["subjects"]) == 6
    assert {s["subject"] for s in out["subjects"]} == {"PSIR"}
    assert [y["year"] for y in out["years"]] == [2024, 2023]


def test_catalog_read_failure_is_not_an_empty_catalogue():
    sb = _sb()
    original = sb.table

    def _table(name):
        q = original(name)
        if name == "pyq_papers":
            def _boom():
                raise RuntimeError("papers read failed")
            q.execute = _boom  # type: ignore[assignment]
        return q

    sb.table = _table  # type: ignore[assignment]

    with pytest.raises(d.DescriptiveError) as err:
        d.get_catalog(sb, EXAM)
    assert err.value.code == "catalog_read_failed"
    assert err.value.status == 503


# ── questions ────────────────────────────────────────────────────────────


def _ids(out: dict[str, Any]) -> set[str]:
    return {i["id"] for i in out["items"]}


def test_map_questions_are_excluded_and_counted():
    out = d.list_questions(_sb(), USER_A, exam_id=EXAM, paper_id="paper-psir-1")

    assert "q-map" not in _ids(out)
    assert out["excluded_map_questions"] == 1


def test_questions_are_verified_descriptive_only():
    out = d.list_questions(_sb(), USER_A, exam_id=EXAM, paper_id="paper-psir-1")
    assert _ids(out) == {"q-stem", "q-subpart", "q-no-marks"}


def test_a_subpart_carries_its_parent_stem():
    out = d.list_questions(_sb(), USER_A, exam_id=EXAM, paper_id="paper-psir-1")
    subpart = next(i for i in out["items"] if i["id"] == "q-subpart")

    assert subpart["parent_question_number"] == 1
    assert subpart["parent_text"] == "Answer the following in about 150 words each:"
    assert subpart["marks"] == 10
    assert subpart["word_limit"] == 150
    assert subpart["timer_target_seconds"] == 720
    assert subpart["verified_against_official"] is True


def test_a_question_without_marks_has_no_timer_target():
    out = d.list_questions(_sb(), USER_A, exam_id=EXAM, paper_id="paper-psir-1")
    plain = next(i for i in out["items"] if i["id"] == "q-no-marks")

    assert plain["marks"] is None
    assert plain["timer_target_seconds"] is None
    assert plain["word_limit"] is None
    # Absent means unknown, and unknown must not read as verified.
    assert plain["verified_against_official"] is False


def test_questions_are_listed_in_question_number_order():
    out = d.list_questions(_sb(), USER_A, exam_id=EXAM, paper_id="paper-psir-1")
    assert [i["id"] for i in out["items"]] == ["q-stem", "q-subpart", "q-no-marks"]


def test_a_theme_filter_selects_the_thematic_half():
    out = d.list_questions(_sb(), USER_A, exam_id=EXAM, theme="Sovereignty")
    assert _ids(out) == {"q-theme-tagged"}


def test_a_year_filter_selects_the_real_paper_half():
    out = d.list_questions(_sb(), USER_A, exam_id=EXAM, year=2023)
    assert _ids(out) == {"q-2023"}


def test_a_retired_buckets_questions_are_never_served():
    out = d.list_questions(_sb(), USER_A, exam_id=EXAM)
    assert "q-bucket" not in _ids(out)


def test_exclude_attempted_drops_questions_this_user_has_answered():
    sb = _sb()
    sb.db["descriptive_attempts"] = [
        {
            "id": "att-1",
            "user_id": USER_A,
            "pyq_question_id": "q-subpart",
            "status": "submitted",
        }
    ]
    everything = d.list_questions(sb, USER_A, exam_id=EXAM, paper_id="paper-psir-1")
    filtered = d.list_questions(
        sb, USER_A, exam_id=EXAM, paper_id="paper-psir-1", exclude_attempted=True
    )

    assert next(i for i in everything["items"] if i["id"] == "q-subpart")["attempt_count"] == 1
    assert "q-subpart" not in _ids(filtered)


def test_attempt_counts_are_never_another_users():
    sb = _sb()
    sb.db["descriptive_attempts"] = [
        {"id": "att-b", "user_id": USER_B, "pyq_question_id": "q-subpart", "status": "submitted"}
    ]
    out = d.list_questions(sb, USER_A, exam_id=EXAM, paper_id="paper-psir-1")
    assert next(i for i in out["items"] if i["id"] == "q-subpart")["attempt_count"] == 0


# ── attempts: the one-open-draft rule ────────────────────────────────────


def test_opening_an_attempt_twice_returns_the_same_draft():
    sb = _sb()
    first = d.open_attempt(sb, USER_A, "q-subpart")
    second = d.open_attempt(sb, USER_A, "q-subpart")

    assert first["id"] == second["id"]
    assert len(sb.db["descriptive_attempts"]) == 1
    assert first["status"] == "draft"
    assert first["timer_target_seconds"] == 720


def test_a_new_attempt_is_allowed_once_the_previous_one_is_submitted():
    sb = _sb()
    first = d.open_attempt(sb, USER_A, "q-subpart")
    d.save_attempt(sb, USER_A, first["id"], answer_text="An answer.")
    d.submit_attempt(sb, USER_A, first["id"], self_scores=_full_scores(), notes=None)

    second = d.open_attempt(sb, USER_A, "q-subpart")

    assert second["id"] != first["id"]
    assert second["status"] == "draft"
    assert len(sb.db["descriptive_attempts"]) == 2


def test_two_users_each_get_their_own_draft_for_one_question():
    sb = _sb()
    a = d.open_attempt(sb, USER_A, "q-subpart")
    b = d.open_attempt(sb, USER_B, "q-subpart")
    assert a["id"] != b["id"]


def test_a_map_question_cannot_be_attempted():
    sb = _sb()
    with pytest.raises(d.DescriptiveError) as err:
        d.open_attempt(sb, USER_A, "q-map")
    assert err.value.code == "map_question"
    assert sb.db["descriptive_attempts"] == []


def test_an_unverified_question_cannot_be_attempted():
    sb = _sb()
    for bad in ("q-pending", "q-mcq", "does-not-exist"):
        with pytest.raises(d.DescriptiveError) as err:
            d.open_attempt(sb, USER_A, bad)
        assert err.value.status == 404


# ── attempts: ownership ──────────────────────────────────────────────────


def test_user_a_cannot_read_user_bs_attempt():
    sb = _sb()
    b = d.open_attempt(sb, USER_B, "q-subpart")

    with pytest.raises(d.DescriptiveError) as err:
        d._load_owned_attempt(sb, USER_A, b["id"])
    assert err.value.status == 404
    assert err.value.code == "attempt_not_found"


def test_user_a_cannot_patch_user_bs_attempt():
    sb = _sb()
    b = d.open_attempt(sb, USER_B, "q-subpart")

    with pytest.raises(d.DescriptiveError) as err:
        d.save_attempt(sb, USER_A, b["id"], answer_text="Not mine to write.")
    assert err.value.status == 404

    row = next(r for r in sb.db["descriptive_attempts"] if r["id"] == b["id"])
    assert row["answer_text"] == ""


def test_user_a_cannot_submit_user_bs_attempt():
    sb = _sb()
    b = d.open_attempt(sb, USER_B, "q-subpart")

    with pytest.raises(d.DescriptiveError) as err:
        d.submit_attempt(sb, USER_A, b["id"], self_scores=_full_scores(), notes=None)
    assert err.value.status == 404

    row = next(r for r in sb.db["descriptive_attempts"] if r["id"] == b["id"])
    assert row["status"] == "draft"


def test_history_is_scoped_to_the_caller():
    sb = _sb()
    d.open_attempt(sb, USER_B, "q-subpart")
    mine = d.open_attempt(sb, USER_A, "q-no-marks")

    out = d.list_attempts(sb, USER_A)
    assert [i["id"] for i in out["items"]] == [mine["id"]]


# ── attempts: autosave ───────────────────────────────────────────────────


def test_the_server_computes_word_count_on_save():
    sb = _sb()
    attempt = d.open_attempt(sb, USER_A, "q-subpart")

    saved = d.save_attempt(
        sb, USER_A, attempt["id"], answer_text="  one two\n\nthree  ", time_spent_seconds=90
    )
    assert saved["word_count"] == 3
    assert saved["time_spent_seconds"] == 90


def test_a_submitted_attempt_cannot_be_edited():
    sb = _sb()
    attempt = d.open_attempt(sb, USER_A, "q-subpart")
    d.save_attempt(sb, USER_A, attempt["id"], answer_text="Written under time.")
    d.submit_attempt(sb, USER_A, attempt["id"], self_scores=_full_scores(), notes=None)

    with pytest.raises(d.DescriptiveError) as err:
        d.save_attempt(sb, USER_A, attempt["id"], answer_text="Rewritten afterwards.")
    assert err.value.code == "attempt_submitted"
    assert err.value.status == 409

    row = next(r for r in sb.db["descriptive_attempts"] if r["id"] == attempt["id"])
    assert row["answer_text"] == "Written under time."


# ── attempts: submit + rubric validation ─────────────────────────────────


def _full_scores(**over: int) -> dict[str, int]:
    scores = {k: 1 for k in d.RUBRIC_KEYS}
    scores.update(over)
    return scores


def test_submit_stores_the_rubric_and_its_sum():
    sb = _sb()
    attempt = d.open_attempt(sb, USER_A, "q-subpart")
    d.save_attempt(sb, USER_A, attempt["id"], answer_text="Two words")

    out = d.submit_attempt(
        sb,
        USER_A,
        attempt["id"],
        self_scores=_full_scores(structure=2, within_limit=0),
        notes="Ran out of time on the conclusion.",
    )

    assert out["status"] == "submitted"
    assert out["self_total"] == 2 + 1 + 1 + 1 + 1 + 0
    assert out["self_scores"]["structure"] == 2
    assert out["notes"] == "Ran out of time on the conclusion."
    assert out["submitted_at"] is not None
    # Recomputed from the stored text, not trusted from the last autosave.
    assert out["word_count"] == 2


def test_submit_rejects_a_score_above_two():
    sb = _sb()
    attempt = d.open_attempt(sb, USER_A, "q-subpart")
    with pytest.raises(d.DescriptiveError) as err:
        d.submit_attempt(
            sb, USER_A, attempt["id"], self_scores=_full_scores(coverage=3), notes=None
        )
    assert err.value.status == 422
    assert err.value.code == "self_scores_invalid"

    row = next(r for r in sb.db["descriptive_attempts"] if r["id"] == attempt["id"])
    assert row["status"] == "draft"


def test_submit_rejects_a_missing_criterion():
    sb = _sb()
    attempt = d.open_attempt(sb, USER_A, "q-subpart")
    partial = _full_scores()
    partial.pop("conclusion")

    with pytest.raises(d.DescriptiveError) as err:
        d.submit_attempt(sb, USER_A, attempt["id"], self_scores=partial, notes=None)
    assert err.value.code == "self_scores_incomplete"
    assert "conclusion" in err.value.message


@pytest.mark.parametrize(
    "bad",
    [None, [], "good", {"structure": 1}, {}],
)
def test_submit_rejects_a_malformed_rubric(bad):
    sb = _sb()
    attempt = d.open_attempt(sb, USER_A, "q-subpart")
    with pytest.raises(d.DescriptiveError) as err:
        d.submit_attempt(sb, USER_A, attempt["id"], self_scores=bad, notes=None)
    assert err.value.status == 422


def test_submit_rejects_an_unknown_criterion():
    sb = _sb()
    attempt = d.open_attempt(sb, USER_A, "q-subpart")
    with pytest.raises(d.DescriptiveError) as err:
        d.submit_attempt(
            sb,
            USER_A,
            attempt["id"],
            self_scores={**_full_scores(), "handwriting": 2},
            notes=None,
        )
    assert err.value.code == "self_scores_unknown_key"


def test_a_boolean_is_not_a_score():
    """`True` is `1` in Python. It is not a rubric judgement."""
    with pytest.raises(d.DescriptiveError):
        d.validate_self_scores(_full_scores(structure=True))


def test_submitting_twice_is_refused():
    sb = _sb()
    attempt = d.open_attempt(sb, USER_A, "q-subpart")
    d.submit_attempt(sb, USER_A, attempt["id"], self_scores=_full_scores(), notes=None)

    with pytest.raises(d.DescriptiveError) as err:
        d.submit_attempt(sb, USER_A, attempt["id"], self_scores=_full_scores(), notes=None)
    assert err.value.code == "attempt_submitted"


def test_rubric_total_ceiling_matches_the_migrations_check():
    assert d.RUBRIC_MAX_TOTAL == 12
    _, total = d.validate_self_scores({k: 2 for k in d.RUBRIC_KEYS})
    assert total == d.RUBRIC_MAX_TOTAL
