"""REG-CORPUS-02 P1/P4/P5 — authored corpus through the existing write paths.

Fixtures are verbatim corpus rows (``tests/fixtures/reg_corpus_cst_sample.json``,
copied from ``workbench/corpus/reg/out/REG-CORPUS-CST.json``): one table
numerical (CST-020), one statement question (CST-003) and one 4-question case
set (CST-065..068, ``stimulus_group`` CST-CASE-PROC). ``_to_import_row`` is the
corpus → bulk-import mapping an operator would apply (the microtopic slug →
topic id lookup is the only DB-dependent step and is faked here).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.admin.mock_import import commit_import, dry_run
from app.admin.mock_questions import create_question, update_question
from app.api import admin_mocks as admin_mocks_api
from app.api.admin_mocks import CreateQuestionIn, UpdateQuestionIn
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "reg_corpus_cst_sample.json"
SUBJECT = "c0510000-0000-0000-0000-0000000000aa"
TOPIC_BY_SLUG = {
    "cost-cost-classification-by-behaviour-fixed-variable-semi-variabl-e25ab568": "c0510000-0000-0000-0000-000000000011",
    "cost-cost-accounting-vs-financial-accounting-2f4381c6": "c0510000-0000-0000-0000-000000000012",
    "cost-equivalent-production-fifo-and-weighted-average-bcff4541": "c0510000-0000-0000-0000-000000000013",
    "cost-process-costing-normal-loss-abnormal-loss-abnormal-gain-18c2fe41": "c0510000-0000-0000-0000-000000000014",
}
_CASE_SPLIT = "\n\n**Q.**"


def _corpus() -> dict[str, dict]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {q["id"]: q for q in data["questions"]}


def _to_import_row(q: dict) -> dict:
    """Corpus row → bulk-import JSON row. A case row's shared case text becomes
    its own stimulus copy; the stem keeps only the question part."""
    stem, stimuli = q["stem"], []
    if q.get("stimulus_group") and _CASE_SPLIT in stem:
        case_text, question = stem.split(_CASE_SPLIT, 1)
        stimuli = [{
            "stimulus_type": "table" if "|---" in case_text else "passage",
            "content_text": case_text,
        }]
        stem = "**Q.**" + question
    row = {
        "question_text": stem,
        "correct_option": str(next(i for i, o in enumerate(q["options"]) if o["is_correct"]) + 1),
        "difficulty": q["difficulty"],
        "rubric_level": q["rubric_level"],
        "stimulus_group": q.get("stimulus_group"),
        "common_trap": q["explanation"]["trap"],
        "stimuli": stimuli,
        "structured_explanation": {
            "solution_steps": q["explanation"]["steps"],
            "formula_used": [q["explanation"]["formula_used"]],
            "common_traps": [q["explanation"]["trap"]],
            "option_rationales": {
                str(i): o["error"] for i, o in enumerate(q["options"]) if o.get("error")
            },
        },
        "subject_id": SUBJECT,
        "topic_id": TOPIC_BY_SLUG[q["microtopic_slug"]],
        "external_id": q["id"],
    }
    for i, o in enumerate(q["options"]):
        row[f"option_{i + 1}"] = o["text"]
    return row


def _actor() -> dict:
    return {"id": "author-1", "role": "admin", "permissions": ["mock_questions:author"],
            "email": "author@example.com"}


def _sb() -> SBStub:
    sb = SBStub()
    sb.db["subjects"] = [{"id": SUBJECT, "name": "Costing"}]
    sb.db["topics"] = [{"id": tid, "subject_id": SUBJECT, "name": slug} for slug, tid in TOPIC_BY_SLUG.items()]
    return sb


def _import(sb: SBStub, ids: list[str]) -> dict:
    corpus = _corpus()
    payload = json.dumps([_to_import_row(corpus[i]) for i in ids]).encode("utf-8")
    preview = dry_run(sb, _actor(), payload, "application/json")
    assert preview["ok_count"] == len(ids), preview
    return commit_import(sb, _actor(), preview["import_token"])


# ── P1 provenance ────────────────────────────────────────────────────────────

def test_bulk_import_writes_source_kind_authored_on_the_bank_row():
    sb = _sb()
    res = _import(sb, ["CST-020", "CST-003"])
    assert res["created"] == 2 and res["failed"] == 0
    for row in sb.db["mock_question_bank"]:
        assert row["source_kind"] == "authored"
        assert row["exam_id"] is None
        assert row["reviewer_status"] == "draft"
    # the side table still carries it too
    assert {s["source_kind"] for s in sb.db["mock_question_sources"]} == {"authored"}


def test_bulk_import_keeps_an_explicit_source_kind():
    sb = _sb()
    csv = (
        "question_text,option_1,option_2,correct_option,source_kind\n"
        "Standard-source question?,A,B,1,standard_source\n"
    ).encode()
    preview = dry_run(sb, _actor(), csv, "text/csv")
    commit_import(sb, _actor(), preview["import_token"])
    assert sb.db["mock_question_bank"][0]["source_kind"] == "standard_source"


def test_crud_create_defaults_source_kind_authored():
    sb = SBStub()
    res = create_question(sb, _actor(), {
        "question_text": "Authored?",
        "options": [{"option_text": "A", "is_correct": True}, {"option_text": "B"}],
    })
    assert res["source_kind"] == "authored"
    # no caller-sent kind → no auto source row (unchanged behaviour)
    assert sb.db.get("mock_question_sources", []) == []


def test_crud_create_keeps_explicit_source_kind_and_pyq_lineage_is_not_stamped():
    sb = SBStub()
    res = create_question(sb, _actor(), {
        "question_text": "CA?", "source_kind": "current_event",
        "options": [{"option_text": "A", "is_correct": True}, {"option_text": "B"}],
    })
    assert res["source_kind"] == "current_event"
    res = create_question(sb, _actor(), {
        "question_text": "Has lineage?", "pyq_question_id": "pyqq-1",
        "options": [{"option_text": "A", "is_correct": True}, {"option_text": "B"}],
    })
    assert res.get("source_kind") is None


@pytest.mark.parametrize("bad", ["very_hard", "HARD", "unknown", ""])
def test_difficulty_is_typed_on_create_and_update(bad):
    with pytest.raises(ValidationError):
        CreateQuestionIn(question_text="Q", difficulty=bad,
                         options=[{"option_text": "A", "is_correct": True}, {"option_text": "B"}])
    with pytest.raises(ValidationError):
        UpdateQuestionIn(difficulty=bad)


def test_create_endpoint_rejects_very_hard_with_422():
    sb = SBStub()
    app = FastAPI()
    app.include_router(admin_mocks_api.router)
    app.dependency_overrides[get_current_user] = _actor
    admin_mocks_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/admin/mocks/questions", json={
        "question_text": "Q?", "difficulty": "very_hard",
        "options": [{"option_text": "A", "is_correct": True}, {"option_text": "B"}],
    })
    assert resp.status_code == 422
    assert sb.db.get("mock_question_bank", []) == []


# ── metadata / P4 explanation / P5 stimuli ───────────────────────────────────

def test_import_writes_rubric_level_and_common_trap():
    sb = _sb()
    _import(sb, ["CST-020"])
    row = sb.db["mock_question_bank"][0]
    assert row["metadata"] == {"rubric_level": "L2"}
    assert row["difficulty"] == "medium"
    assert row["common_trap"] == _corpus()["CST-020"]["explanation"]["trap"]
    # the GFM table stays in the stem verbatim for the renderer
    assert "|---|---:|---:|" in row["question_text"]


def test_import_writes_a_pending_structured_explanation_keyed_by_mock_question():
    sb = _sb()
    _import(sb, ["CST-003"])
    q = _corpus()["CST-003"]
    bank = sb.db["mock_question_bank"][0]
    opts = {o["option_index"]: o for o in sb.db["mock_question_options"]}
    [expl] = sb.db["pyq_question_explanations"]
    assert expl["mock_question_id"] == bank["id"]
    assert "question_id" not in expl  # never keyed to a PYQ
    assert expl["reviewer_status"] == "pending"
    assert expl["solution_steps"] == q["explanation"]["steps"]
    assert expl["formula_used"] == [q["explanation"]["formula_used"]]
    assert expl["common_traps"] == [q["explanation"]["trap"]]
    correct_idx = next(i for i, o in enumerate(q["options"]) if o["is_correct"])
    assert expl["final_answer_mock_option_id"] == opts[correct_idx]["id"]
    # one rationale per wrong option, keyed by the persisted option id
    assert set(expl["option_rationales"]) == {
        opts[i]["id"] for i, o in enumerate(q["options"]) if o.get("error")
    }


def test_case_set_rows_each_get_their_own_stimulus_copy():
    sb = _sb()
    res = _import(sb, ["CST-065", "CST-066", "CST-067", "CST-068"])
    assert res["created"] == 4
    bank = sb.db["mock_question_bank"]
    assert {r["metadata"]["stimulus_group"] for r in bank} == {"CST-CASE-PROC"}
    assert {r["metadata"]["rubric_level"] for r in bank} == {"L4"}
    stimuli = sb.db["mock_question_stimuli"]
    assert len(stimuli) == 4
    assert {s["mock_question_id"] for s in stimuli} == {r["id"] for r in bank}  # one each
    assert len({s["id"] for s in stimuli}) == 4  # copies, not a shared row
    assert all(s["pyq_stimulus_id"] is None for s in stimuli)
    assert all(s["stimulus_type"] == "table" for s in stimuli)
    assert all("Sarayu Chemicals" in s["content_text"] for s in stimuli)
    # stems keep only the question part
    assert all(r["question_text"].startswith("**Q.**") for r in bank)
    assert len({r["question_fingerprint"] for r in bank}) == 4


def test_invalid_rubric_level_is_a_parse_error():
    sb = _sb()
    row = _to_import_row(_corpus()["CST-020"]) | {"rubric_level": "L9"}
    preview = dry_run(sb, _actor(), json.dumps([row]).encode(), "application/json")
    assert preview["error_count"] == 1
    assert "rubric_level" in preview["rows"][0]["issues"][0]


def test_crud_create_writes_stimuli_metadata_and_explanation():
    sb = SBStub()
    body = CreateQuestionIn(
        question_text="**Q.** The value of closing WIP is:",
        difficulty="hard", rubric_level="L4", stimulus_group="CST-CASE-PROC",
        common_trap="Normal loss gets no equivalent units.",
        stimuli=[{"stimulus_type": "table", "content_text": "| Item | Units |\n|---|---:|\n| WIP | 1,500 |"}],
        structured_explanation={"solution_steps": ["s1"], "formula_used": ["f"],
                                "common_traps": ["t"], "option_rationales": {"0": "why A is wrong"}},
        options=[{"option_text": "A"}, {"option_text": "B", "is_correct": True}],
    ).model_dump()
    res = create_question(sb, _actor(), body)
    bank = sb.db["mock_question_bank"][0]
    assert bank["metadata"] == {"rubric_level": "L4", "stimulus_group": "CST-CASE-PROC"}
    assert bank["common_trap"] == "Normal loss gets no equivalent units."
    assert res["stimuli_count"] == 1
    assert sb.db["mock_question_stimuli"][0]["mock_question_id"] == bank["id"]
    expl = sb.db["pyq_question_explanations"][0]
    assert res["structured_explanation_id"] == expl["id"]
    opt_a = next(o for o in sb.db["mock_question_options"] if o["option_index"] == 0)
    assert expl["option_rationales"] == {opt_a["id"]: "why A is wrong"}


def test_crud_update_replaces_only_this_rows_stimuli():
    sb = SBStub()
    a = create_question(sb, _actor(), {
        "question_text": "Case Q1", "stimulus_group": "G",
        "stimuli": [{"stimulus_type": "passage", "content_text": "case v1"}],
        "options": [{"option_text": "A", "is_correct": True}, {"option_text": "B"}],
    })
    b = create_question(sb, _actor(), {
        "question_text": "Case Q2", "stimulus_group": "G",
        "stimuli": [{"stimulus_type": "passage", "content_text": "case v1"}],
        "options": [{"option_text": "C", "is_correct": True}, {"option_text": "D"}],
    })
    update_question(sb, _actor(), a["id"], {
        "stimuli": [{"stimulus_type": "passage", "content_text": "case v2"}],
        "rubric_level": "L2",
    })
    by_q = {s["mock_question_id"]: s["content_text"] for s in sb.db["mock_question_stimuli"]}
    assert by_q == {a["id"]: "case v2", b["id"]: "case v1"}
    row_a = next(r for r in sb.db["mock_question_bank"] if r["id"] == a["id"])
    assert row_a["metadata"] == {"stimulus_group": "G", "rubric_level": "L2"}


def test_crud_update_refuses_stimuli_on_projected_pyq():
    sb = SBStub()
    q = create_question(sb, _actor(), {
        "question_text": "Projected?", "pyq_question_id": "pyqq-9",
        "options": [{"option_text": "A", "is_correct": True}, {"option_text": "B"}],
    })
    next(r for r in sb.db["mock_question_bank"] if r["id"] == q["id"])["pyq_question_id"] = "pyqq-9"
    with pytest.raises(ValueError, match="projection"):
        update_question(sb, _actor(), q["id"], {"stimuli": [{"content_text": "x"}]})
