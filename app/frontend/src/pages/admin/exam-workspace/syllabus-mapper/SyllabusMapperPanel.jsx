import React, { useCallback, useEffect, useState } from "react";
import { api } from "../../../../lib/api";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import AcceptPreviewModal from "./AcceptPreviewModal";
import DocumentSelector from "./DocumentSelector";
import PageViewer from "./PageViewer";
import ProposalActionBar from "./ProposalActionBar";
import ProposalRunner from "./ProposalRunner";
import SyllabusTopicEditorPanel from "./SyllabusTopicEditorPanel";
import TopicTreePanel from "./TopicTreePanel";
import TopicEditDrawer from "./topic-edit/TopicEditDrawer";
import { useTopicEdit } from "./topic-edit/useTopicEdit";
import { useSyllabusMapper } from "./useSyllabusMapper";

export default function SyllabusMapperPanel({ status = null, rowId = null }) {
  const { exam } = useExamWorkspace();
  const examId = exam?.id;
  const [showModal, setShowModal] = useState(false);

  // Deep-link state: when status or rowId is provided, fetch and show the pending review list
  const [pendingItems, setPendingItems] = useState([]);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [pendingError, setPendingError] = useState("");
  const [rowNotFound, setRowNotFound] = useState(false);

  const showPendingList = status || rowId;

  const loadPending = useCallback(async () => {
    if (!examId || !showPendingList) return;
    setPendingLoading(true);
    setPendingError("");
    try {
      if (status === "pending_review") {
        const qs = new URLSearchParams({ exam_id: examId, status: "pending_review", limit: "50" });
        const d = await api.get(`/api/admin/exam-intelligence/topic-coverage?${qs}`);
        setPendingItems(d?.items || []);
      } else {
        const qs = new URLSearchParams({ kind: "syllabus_topic_mention", status: "pending", limit: "50" });
        const d = await api.get(`/api/admin/exam-intelligence/exams/${examId}/items?${qs}`);
        setPendingItems(d?.items || []);
      }
    } catch (e) {
      setPendingError(e?.message || "Failed to load pending items");
    } finally {
      setPendingLoading(false);
    }
  }, [examId, status, showPendingList]);

  useEffect(() => { loadPending(); }, [loadPending]);

  useEffect(() => {
    if (!rowId || pendingLoading || pendingError) return;
    setRowNotFound(!pendingItems.some((item) => item.id === rowId));
  }, [rowId, pendingItems, pendingLoading, pendingError]);
  const [pageText, setPageText] = useState("");

  const mapper = useSyllabusMapper(examId);
  const topicEdit = useTopicEdit();

  // Fetch page text when page changes
  useEffect(() => {
    if (!mapper.syllabusDocumentId || !mapper.currentPage) { setPageText(""); return; }
    api
      .get(`/api/admin/exam-intelligence/workspace/${examId}/documents/${mapper.syllabusDocumentId}/pages/${mapper.currentPage}`)
      .then((d) => setPageText(d?.text_content || ""))
      .catch(() => setPageText(""));
  }, [examId, mapper.syllabusDocumentId, mapper.currentPage]);

  const currentPageProposals = mapper.proposals.filter((p) => p.source_page === mapper.currentPage);
  const selectedProposals = mapper.proposals.filter((p) => mapper.selectedKeys.has(p.client_proposal_key));

  function handleAcceptSelected() {
    mapper.runPreview(selectedProposals).then(() => setShowModal(true));
  }

  function handleCommit(reason) {
    mapper.runCommit(selectedProposals, reason).then(() => setShowModal(false));
  }

  return (
    <div className="flex flex-col h-full" data-testid="syllabus-mapper-panel">
      {/* J2-A: canonical topic/alias editor (manage-gated; renders null otherwise) */}
      <SyllabusTopicEditorPanel examId={examId} />
      {/* Deep-link: show pending review list when status/rowId is in the URL */}
      {showPendingList && (
        <div className="border-b border-gray-200 bg-amber-50 px-4 py-3" data-testid="syllabus-pending-list">
          <div className="text-xs font-medium text-amber-800 mb-2">
            {status === "pending_review" ? "Pending topic coverage rows" : "Pending syllabus mentions"}
          </div>
          {pendingLoading && <div className="text-sm text-gray-400">Loading…</div>}
          {pendingError && <div className="text-sm text-rose-600" data-testid="syllabus-pending-error">{pendingError}</div>}
          {rowNotFound && !pendingLoading && (
            <div className="text-sm text-rose-600" data-testid="syllabus-row-not-found">
              Row {rowId} was not found in pending items for this exam.
            </div>
          )}
          {!pendingLoading && pendingItems.length > 0 && (
            <ul className="text-sm divide-y divide-gray-100 max-h-40 overflow-y-auto" data-testid="syllabus-pending-items">
              {pendingItems.map((item) => (
                <li
                  key={item.id}
                  data-testid={`syllabus-pending-item-${item.id}`}
                  style={item.id === rowId ? { background: "#fef9c3", outline: "1px solid #ca8a04", padding: "4px 6px", borderRadius: 2 } : { padding: "4px 6px" }}
                >
                  {item.raw_text || item.topic_id || item.id}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {/* Top bar */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-gray-200 bg-white flex-wrap">
        <DocumentSelector
          examId={examId}
          value={mapper.syllabusDocumentId}
          onChange={(id) => { mapper.setSyllabusDocumentId(id); if (id) mapper.runPropose(id); }}
        />

        <ProposalRunner
          docId={mapper.syllabusDocumentId}
          loading={mapper.loading.propose}
          error={mapper.error.propose}
          onRun={mapper.runPropose}
          proposalCount={mapper.proposals.length}
        />

        {/* Page navigation */}
        {mapper.proposals.length > 0 && (
          <div className="flex items-center gap-1 ml-auto">
            <button
              type="button"
              onClick={() => mapper.setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={mapper.currentPage <= 1}
              className="px-2 py-1 text-sm border rounded disabled:opacity-40"
              aria-label="Previous page"
            >
              ‹
            </button>
            <span className="text-sm px-2" data-testid="page-indicator">
              Page {mapper.currentPage} / {mapper.totalPages}
            </span>
            <button
              type="button"
              onClick={() => mapper.setCurrentPage((p) => Math.min(mapper.totalPages, p + 1))}
              disabled={mapper.currentPage >= mapper.totalPages}
              className="px-2 py-1 text-sm border rounded disabled:opacity-40"
              aria-label="Next page"
            >
              ›
            </button>
          </div>
        )}
      </div>

      {/* Split pane */}
      <div className="flex flex-1 min-h-0">
        <div className="flex-1 border-r border-gray-200">
          <PageViewer
            pageText={pageText}
            pageProposals={currentPageProposals}
            selectedKeys={mapper.selectedKeys}
            onToggle={mapper.toggleSelection}
          />
        </div>
        <div className="w-72 shrink-0">
          <TopicTreePanel
            proposals={mapper.proposals}
            selectedKeys={mapper.selectedKeys}
            onToggle={mapper.toggleSelection}
            onEditTopic={topicEdit.openForTopic}
            currentPage={mapper.currentPage}
          />
        </div>
      </div>

      {/* Action bar */}
      <ProposalActionBar
        proposals={mapper.proposals}
        selectedKeys={mapper.selectedKeys}
        currentPage={mapper.currentPage}
        onAcceptSelected={handleAcceptSelected}
        onSelectPage={mapper.selectPage}
        onSelectByMinConfidence={mapper.selectByMinConfidence}
        disabled={mapper.loading.propose || mapper.loading.preview || mapper.loading.commit}
      />

      {/* Preview / commit modal */}
      {showModal && (
        <AcceptPreviewModal
          previewResult={mapper.previewResult}
          loading={mapper.loading.commit}
          onCommit={handleCommit}
          onClose={() => setShowModal(false)}
        />
      )}

      {/* Topic edit drawer — re-propose on alias change so matching updates */}
      <TopicEditDrawer
        hook={topicEdit}
        onSaved={() => {
          if (mapper.syllabusDocumentId) mapper.runPropose(mapper.syllabusDocumentId);
        }}
      />
    </div>
  );
}
