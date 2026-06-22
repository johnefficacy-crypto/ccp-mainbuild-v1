"""Tests for console_detail CTA deep-link shapes and evidence-kind selection (I8-B)."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from app.exam_intelligence.console_detail import (
    _deep_link,
    _first_evidence_by_kinds,
    _resolve_pyq_paper_id,
    _build_action_queue,
)

EXAM_ID = "exam-1"
CYCLE_ID = "cycle-1"


class TestDeepLink:
    def test_syllabus_with_row(self):
        label, route = _deep_link("syllabus", EXAM_ID, None, entity_row_id="m1")
        assert "tab=syllabus" in route
        assert "status=pending" in route
        assert "row=m1" in route

    def test_topic_coverage_with_row(self):
        label, route = _deep_link("topic_coverage", EXAM_ID, None, entity_row_id="c1")
        assert "tab=syllabus" in route
        assert "status=pending_review" in route
        assert "row=c1" in route

    def test_pyq_with_paper_and_row(self):
        label, route = _deep_link("pyq", EXAM_ID, CYCLE_ID, entity_row_id="q1", paper_id="p1")
        assert f"cycle={CYCLE_ID}" in route
        assert "tab=pyq" in route
        assert "paper=p1" in route
        assert "status=pending" in route
        assert "row=q1" in route

    def test_pyq_without_paper(self):
        label, route = _deep_link("pyq", EXAM_ID, None, entity_row_id="q1")
        assert "paper=" not in route
        assert "row=q1" in route

    def test_updates_with_row(self):
        label, route = _deep_link("updates", EXAM_ID, None, entity_row_id="u1")
        assert "tab=updates" in route
        assert "status=pending" in route
        assert "row=u1" in route

    def test_documents_with_doc_id_and_status(self):
        label, route = _deep_link("documents", EXAM_ID, CYCLE_ID, entity_row_id="d1", doc_status="failed")
        assert f"cycle={CYCLE_ID}" in route
        assert "tab=documents" in route
        assert "document=d1" in route
        assert "status=failed" in route

    def test_documents_without_doc_id(self):
        label, route = _deep_link("documents", EXAM_ID, None)
        assert "document=" not in route
        assert "status=" not in route

    def test_setup_no_row(self):
        label, route = _deep_link("setup", EXAM_ID, None, entity_row_id="x")
        assert "tab=setup" in route
        assert "row=" not in route

    def test_mock_readiness_goes_to_review(self):
        label, route = _deep_link("mock_readiness", EXAM_ID, None)
        assert "tab=review" in route


class TestFirstEvidenceByKinds:
    def test_returns_first_matching(self):
        refs = [
            {"kind": "exam_topic_coverage", "row_id": "c1"},
            {"kind": "pyq_question", "row_id": "q1"},
        ]
        result = _first_evidence_by_kinds(refs, {"pyq_question"})
        assert result == {"kind": "pyq_question", "row_id": "q1"}

    def test_returns_none_when_no_match(self):
        refs = [{"kind": "exam_topic_coverage", "row_id": "c1"}]
        assert _first_evidence_by_kinds(refs, {"pyq_question"}) is None

    def test_returns_none_on_empty(self):
        assert _first_evidence_by_kinds([], {"syllabus_topic_mention"}) is None

    def test_multi_kind_match(self):
        refs = [
            {"kind": "pyq_option", "row_id": "o1"},
        ]
        result = _first_evidence_by_kinds(refs, {"pyq_question", "pyq_question_topic_tag", "pyq_option"})
        assert result["row_id"] == "o1"


class TestResolvePyqPaperId:
    def test_resolves_paper_id_from_question(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "q1", "pyq_paper_id": "paper-1"}
        ]
        paper_id, question_id = _resolve_pyq_paper_id(sb, "pyq_question", "q1")
        assert paper_id == "paper-1"
        assert question_id == "q1"

    def test_returns_none_tuple_when_not_found(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        paper_id, question_id = _resolve_pyq_paper_id(sb, "pyq_question", "unknown")
        assert paper_id is None
        assert question_id is None

    def test_resolves_tag_to_question_to_paper(self):
        """pyq_question_topic_tag → question_id → pyq_paper_id."""
        sb = MagicMock()
        call_count = 0

        def table_side_effect(name):
            nonlocal call_count
            call_count += 1
            m = MagicMock()
            if name == "pyq_question_topic_tags":
                m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                    {"id": "tag-1", "question_id": "q1"}
                ]
            elif name == "pyq_questions":
                m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                    {"id": "q1", "pyq_paper_id": "paper-1"}
                ]
            return m

        sb.table.side_effect = table_side_effect
        paper_id, question_id = _resolve_pyq_paper_id(sb, "pyq_question_topic_tag", "tag-1")
        assert paper_id == "paper-1"
        assert question_id == "q1"

    def test_resolves_option_to_question_to_paper(self):
        """pyq_option → question_id → pyq_paper_id."""
        sb = MagicMock()

        def table_side_effect(name):
            m = MagicMock()
            if name == "pyq_options":
                m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                    {"id": "opt-1", "question_id": "q2"}
                ]
            elif name == "pyq_questions":
                m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                    {"id": "q2", "pyq_paper_id": "paper-2"}
                ]
            return m

        sb.table.side_effect = table_side_effect
        paper_id, question_id = _resolve_pyq_paper_id(sb, "pyq_option", "opt-1")
        assert paper_id == "paper-2"
        assert question_id == "q2"

    def test_tag_not_found_returns_none_tuple(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        paper_id, question_id = _resolve_pyq_paper_id(sb, "pyq_question_topic_tag", "missing")
        assert paper_id is None
        assert question_id is None

    def test_unknown_kind_returns_none_tuple(self):
        sb = MagicMock()
        paper_id, question_id = _resolve_pyq_paper_id(sb, "unknown_kind", "x")
        assert paper_id is None
        assert question_id is None


class TestBuildActionQueue:
    def _make_sb(self, paper_id="paper-1"):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "q1", "pyq_paper_id": paper_id}
        ]
        return sb

    def test_pyq_cta_includes_paper_id(self):
        sb = self._make_sb()
        checks = [{
            "area": "pyq", "state": "needs_action",
            "evidence_refs": [{"kind": "pyq_question", "row_id": "q1"}],
        }]
        items = _build_action_queue(sb, checks, EXAM_ID, CYCLE_ID)
        assert len(items) == 1
        assert "paper=paper-1" in items[0]["cta_route"]
        assert "row=q1" in items[0]["cta_route"]

    def test_syllabus_cta_includes_mention_row(self):
        sb = MagicMock()
        checks = [{
            "area": "syllabus", "state": "needs_action",
            "evidence_refs": [{"kind": "syllabus_topic_mention", "row_id": "m1"}],
        }]
        items = _build_action_queue(sb, checks, EXAM_ID, None)
        assert "row=m1" in items[0]["cta_route"]
        assert "status=pending" in items[0]["cta_route"]

    def test_topic_coverage_cta_includes_coverage_row(self):
        sb = MagicMock()
        checks = [{
            "area": "topic_coverage", "state": "blocked",
            "evidence_refs": [{"kind": "exam_topic_coverage", "row_id": "c1"}],
        }]
        items = _build_action_queue(sb, checks, EXAM_ID, None)
        assert "row=c1" in items[0]["cta_route"]
        assert "status=pending_review" in items[0]["cta_route"]

    def test_updates_cta_includes_update_row(self):
        sb = MagicMock()
        checks = [{
            "area": "updates", "state": "needs_action",
            "evidence_refs": [{"kind": "exam_policy_updates", "row_id": "u1"}],
        }]
        items = _build_action_queue(sb, checks, EXAM_ID, None)
        assert "row=u1" in items[0]["cta_route"]

    def test_documents_cta_includes_doc_id(self):
        sb = MagicMock()
        checks = [{
            "area": "documents", "state": "needs_action",
            "evidence_refs": [{"kind": "document_assets", "row_id": "d1", "extraction_status": "failed"}],
        }]
        items = _build_action_queue(sb, checks, EXAM_ID, CYCLE_ID)
        assert "document=d1" in items[0]["cta_route"]
        assert "status=failed" in items[0]["cta_route"]

    def test_publish_area_skipped(self):
        sb = MagicMock()
        checks = [{"area": "publish", "state": "blocked", "evidence_refs": []}]
        items = _build_action_queue(sb, checks, EXAM_ID, None)
        assert len(items) == 0

    def test_done_state_skipped(self):
        sb = MagicMock()
        checks = [{"area": "syllabus", "state": "done", "evidence_refs": []}]
        items = _build_action_queue(sb, checks, EXAM_ID, None)
        assert len(items) == 0

    def test_pyq_exception_fallback_omits_entity_row_id(self):
        """DB error in _resolve_pyq_paper_id must not leak a tag/option row_id as a question row."""
        sb = MagicMock()
        sb.table.side_effect = RuntimeError("DB error")
        checks = [{
            "area": "pyq", "state": "needs_action",
            "evidence_refs": [{"kind": "pyq_question_topic_tag", "row_id": "tag-99"}],
        }]
        items = _build_action_queue(sb, checks, EXAM_ID, CYCLE_ID)
        assert len(items) == 1
        assert "row=" not in items[0]["cta_route"]
