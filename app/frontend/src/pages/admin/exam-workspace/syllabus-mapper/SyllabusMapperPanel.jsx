import React, { useEffect, useState } from "react";
import { api } from "../../../../lib/api";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import AcceptPreviewModal from "./AcceptPreviewModal";
import DocumentSelector from "./DocumentSelector";
import PageViewer from "./PageViewer";
import ProposalActionBar from "./ProposalActionBar";
import ProposalRunner from "./ProposalRunner";
import TopicTreePanel from "./TopicTreePanel";
import { useSyllabusMapper } from "./useSyllabusMapper";

export default function SyllabusMapperPanel() {
  const { exam } = useExamWorkspace();
  const examId = exam?.id;
  const [showModal, setShowModal] = useState(false);
  const [pageText, setPageText] = useState("");

  const mapper = useSyllabusMapper(examId);

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
    </div>
  );
}
