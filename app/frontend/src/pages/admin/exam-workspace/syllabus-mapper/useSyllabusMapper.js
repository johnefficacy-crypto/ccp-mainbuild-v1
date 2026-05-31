import { useCallback, useState } from "react";
import { api } from "../../../../lib/api";
import { computeProposalKey } from "./proposalKey";

const REVIEW_BASE = "/api/admin/exam-intelligence";

export function useSyllabusMapper(examId) {
  const [syllabusDocumentId, setSyllabusDocumentId] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [proposals, setProposals] = useState([]);
  const [selectedKeys, setSelectedKeys] = useState(new Set());
  const [previewResult, setPreviewResult] = useState(null);
  const [commitResult, setCommitResult] = useState(null);
  const [loading, setLoading] = useState({ propose: false, preview: false, commit: false });
  const [error, setError] = useState({ propose: null, preview: null, commit: null });

  const runPropose = useCallback(async (docId, threshold) => {
    if (!docId || !examId) return;
    setLoading((l) => ({ ...l, propose: true }));
    setError((e) => ({ ...e, propose: null }));
    setProposals([]);
    setSelectedKeys(new Set());
    setPreviewResult(null);
    setCommitResult(null);
    try {
      const body = { syllabus_document_id: docId };
      if (threshold !== undefined) body.threshold = threshold;
      const data = await api.post(`${REVIEW_BASE}/workspace/${examId}/syllabus/propose`, body);
      const withKeys = (data.proposals || []).map((p) => ({
        ...p,
        client_proposal_key: computeProposalKey(p),
      }));
      setProposals(withKeys);
      setCurrentPage(withKeys.length > 0 ? withKeys[0].source_page : 1);
    } catch (e) {
      setError((err) => ({ ...err, propose: e?.message || "Failed to load proposals" }));
    } finally {
      setLoading((l) => ({ ...l, propose: false }));
    }
  }, [examId]);

  const runPreview = useCallback(async (selectedProposals) => {
    setLoading((l) => ({ ...l, preview: true }));
    setError((e) => ({ ...e, preview: null }));
    setPreviewResult(null);
    try {
      const data = await api.post(
        `${REVIEW_BASE}/workspace/${examId}/syllabus/accept/preview`,
        { proposals: selectedProposals },
      );
      setPreviewResult(data);
    } catch (e) {
      setError((err) => ({ ...err, preview: e?.message || "Preview failed" }));
    } finally {
      setLoading((l) => ({ ...l, preview: false }));
    }
  }, [examId]);

  const runCommit = useCallback(async (selectedProposals, reason) => {
    setLoading((l) => ({ ...l, commit: true }));
    setError((e) => ({ ...e, commit: null }));
    setCommitResult(null);
    try {
      const data = await api.post(
        `${REVIEW_BASE}/workspace/${examId}/syllabus/accept/commit`,
        { proposals: selectedProposals, reason },
      );
      setCommitResult(data);
      // Remove committed proposals from state
      const committedKeys = new Set(
        (data.per_row || [])
          .filter((r) => r.result === "committed")
          .map((r) => r.proposal_key),
      );
      setProposals((prev) => prev.filter((p) => !committedKeys.has(p.client_proposal_key)));
      setSelectedKeys((prev) => {
        const next = new Set(prev);
        committedKeys.forEach((k) => next.delete(k));
        return next;
      });
      setPreviewResult(null);
    } catch (e) {
      setError((err) => ({ ...err, commit: e?.message || "Commit failed" }));
    } finally {
      setLoading((l) => ({ ...l, commit: false }));
    }
  }, [examId]);

  const toggleSelection = useCallback((key) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const selectPage = useCallback((page) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      proposals.filter((p) => p.source_page === page).forEach((p) => next.add(p.client_proposal_key));
      return next;
    });
  }, [proposals]);

  const selectByMinConfidence = useCallback((minConf) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      proposals.filter((p) => p.confidence_score >= minConf).forEach((p) => next.add(p.client_proposal_key));
      return next;
    });
  }, [proposals]);

  const totalPages = proposals.length > 0
    ? Math.max(...proposals.map((p) => p.source_page))
    : 1;

  return {
    syllabusDocumentId,
    setSyllabusDocumentId,
    currentPage,
    setCurrentPage,
    proposals,
    selectedKeys,
    toggleSelection,
    selectPage,
    selectByMinConfidence,
    previewResult,
    commitResult,
    loading,
    error,
    totalPages,
    runPropose,
    runPreview,
    runCommit,
  };
}
