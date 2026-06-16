"""Canary-safe mapped mock-question import tests."""
from __future__ import annotations

from app.admin.mock_import import commit_import, dry_run
from tests.persona_questions._stub import SBStub

EXAM_ID = "22222222-2222-2222-2222-222222222222"
SUBJECT_ID = "55555555-5555-5555-5555-555555555553"
OTHER_SUBJECT_ID = "55555555-5555-5555-5555-555555555552"
TOPIC_ID = "66666666-6666-6666-6666-666666666661"
OTHER_TOPIC_ID = "66666666-6666-6666-6666-666666666662"


def _actor() -> dict:
    return {
        "id": "author-1",
        "role": "admin",
        "permissions": ["mock_questions:author"],
        "email": "author@example.com",
    }


def _sb() -> SBStub:
    sb = SBStub()
    sb.db["subjects"] = [
        {"id": SUBJECT_ID, "name": "General Intelligence & Reasoning"},
        {"id": OTHER_SUBJECT_ID, "name": "English Comprehension"},
    ]
    sb.db["topics"] = [
        {"id": TOPIC_ID, "subject_id": SUBJECT_ID, "name": "Series"},
        {"id": OTHER_TOPIC_ID, "subject_id": OTHER_SUBJECT_ID, "name": "Grammar"},
    ]
    return sb


def _mapped_csv(*, subject_id: str = SUBJECT_ID, topic_id: str = TOPIC_ID) -> bytes:
    csv = (
        "question_text,option_1,option_2,option_3,option_4,correct_option,"
        "difficulty,is_conceptual,is_factual,is_current,is_current_based,valid_until,"
        "language,exam_id,subject_id,topic_id,source_kind,source_trust,source_url,external_id\n"
        f"Canary mapped question?,A,B,C,D,1,medium,true,false,false,false,,"
        f"en,{EXAM_ID},{subject_id},{topic_id},authored,verified,,canary-001\n"
    )
    return csv.encode()


def test_mapped_dry_run_ok_and_commit_persists_subject_topic_and_ttl_fields():
    sb = _sb()
    result = dry_run(sb, _actor(), _mapped_csv(), "text/csv")

    assert result["ok_count"] == 1
    assert result["missing_mapping_count"] == 0
    assert result["rows"][0]["status"] == "ok"
    assert result["rows"][0]["preview"]["subject_id"] == SUBJECT_ID
    assert result["rows"][0]["preview"]["topic_id"] == TOPIC_ID

    committed = commit_import(sb, _actor(), result["import_token"])
    assert committed["created"] == 1
    assert committed["skipped"] == 0

    row = sb.db["mock_question_bank"][0]
    assert row["exam_id"] == EXAM_ID
    assert row["subject_id"] == SUBJECT_ID
    assert row["topic_id"] == TOPIC_ID
    assert row["is_current_based"] is False
    assert row["valid_until"] is None
    assert row["reviewer_status"] == "draft"


def test_missing_subject_or_topic_is_missing_mapping_and_not_committed():
    sb = _sb()
    csv = (
        "question_text,option_1,option_2,option_3,option_4,correct_option,subject_id,topic_id\n"
        "Missing mapping question?,A,B,C,D,1,,\n"
    ).encode()

    result = dry_run(sb, _actor(), csv, "text/csv")

    assert result["ok_count"] == 0
    assert result["missing_mapping_count"] == 1
    assert result["rows"][0]["status"] == "missing_mapping"
    assert "subject_id is required" in result["rows"][0]["issues"][0]
    assert "topic_id is required" in result["rows"][0]["issues"][1]

    committed = commit_import(sb, _actor(), result["import_token"])
    assert committed["created"] == 0
    assert committed["skipped"] == 1
    assert sb.db.get("mock_question_bank", []) == []


def test_unresolved_subject_or_topic_is_missing_mapping():
    sb = _sb()
    result = dry_run(
        sb,
        _actor(),
        _mapped_csv(subject_id="missing-subject", topic_id="missing-topic"),
        "text/csv",
    )

    assert result["ok_count"] == 0
    assert result["missing_mapping_count"] == 1
    assert result["rows"][0]["status"] == "missing_mapping"
    assert any("subject_id 'missing-subject' does not resolve" in issue for issue in result["rows"][0]["issues"])
    assert any("topic_id 'missing-topic' does not resolve" in issue for issue in result["rows"][0]["issues"])


def test_topic_must_belong_to_subject():
    sb = _sb()
    result = dry_run(
        sb,
        _actor(),
        _mapped_csv(subject_id=SUBJECT_ID, topic_id=OTHER_TOPIC_ID),
        "text/csv",
    )

    assert result["ok_count"] == 0
    assert result["missing_mapping_count"] == 1
    assert result["rows"][0]["status"] == "missing_mapping"
    assert result["rows"][0]["issues"] == ["topic_id belongs to a different subject_id"]


def test_legacy_unmapped_import_without_mapping_columns_still_commits():
    sb = _sb()
    csv = (
        "question_text,option_1,option_2,option_3,option_4,correct_option,difficulty,language,exam_id\n"
        f"Legacy import question?,A,B,C,D,1,easy,en,{EXAM_ID}\n"
    ).encode()

    result = dry_run(sb, _actor(), csv, "text/csv")
    assert result["ok_count"] == 1
    assert result["missing_mapping_count"] == 0

    committed = commit_import(sb, _actor(), result["import_token"])
    assert committed["created"] == 1
    row = sb.db["mock_question_bank"][0]
    assert row["subject_id"] is None
    assert row["topic_id"] is None
}
