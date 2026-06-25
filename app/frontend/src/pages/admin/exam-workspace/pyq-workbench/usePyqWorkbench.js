import { useCallback, useEffect, useState } from "react";
import { api } from "../../../../lib/api";
import useApiAction from "../../../../lib/hooks/useApiAction";

const CMS_BASE = "/api/admin/exam-intelligence-cms";

export function usePyqWorkbench(examId, cycleId) {
  const [papers, setPapers] = useState([]);
  const [selectedPaperId, setSelectedPaperId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { run: runReviewAction } = useApiAction();
  const { run: runPatchAction } = useApiAction();
  const { run: runProvenanceAction } = useApiAction();
  const { run: runOnboardAction } = useApiAction();

  const fetchPapers = useCallback(async () => {
    if (!examId) return;
    setLoading(true);
    setError(null);
    try {
      // D10 decision: PYQ corpus is always exam-wide. cycle_id is provenance
      // metadata, not a display/scope filter. Never pass exam_cycle_id here.
      const params = new URLSearchParams({ exam_id: examId });
      const res = await api.get(`${CMS_BASE}/pyq-papers?${params}`);
      setPapers(res.items || []);
    } catch (e) {
      setError(e?.message || "Failed to load papers");
    } finally {
      setLoading(false);
    }
  }, [examId]);

  useEffect(() => { fetchPapers(); }, [fetchPapers]);

  const reviewPaper = useCallback(async (paperId, status, reason) => {
    const result = await runReviewAction({
      action: () => api.post(`${CMS_BASE}/pyq-papers/${paperId}/review`, { status, reason }),
      onSuccess: fetchPapers,
    });
    if (!result?.ok && !result?.cancelled) throw result?.error ?? new Error("Review failed");
  }, [runReviewAction, fetchPapers]);

  const patchPaper = useCallback(async (paperId, payload, reason) => {
    const result = await runPatchAction({
      action: () => api.patch(`${CMS_BASE}/pyq-papers/${paperId}`, { payload, reason }),
      onSuccess: fetchPapers,
    });
    if (!result?.ok && !result?.cancelled) throw result?.error ?? new Error("Patch failed");
  }, [runPatchAction, fetchPapers]);

  const saveProvenance = useCallback(async (paperId, payload, reason) => {
    const result = await runProvenanceAction({
      action: () => api.post(`${CMS_BASE}/pyq-papers/${paperId}/set-provenance`, { payload, reason }),
      onSuccess: fetchPapers,
    });
    if (!result?.ok && !result?.cancelled) throw result?.error ?? new Error("Provenance save failed");
  }, [runProvenanceAction, fetchPapers]);

  // Contextual paper onboarding. POSTs the LOCKED /pyq-onboarding contract,
  // refetches the (exam-wide) paper list, and returns the created paper id so
  // the panel can select it. Surfaces backend {error, blocking_fields} by
  // re-throwing the structured error for the modal's api helpers.
  const onboardPaper = useCallback(async (body) => {
    const result = await runOnboardAction({
      action: () => api.post(`${CMS_BASE}/pyq-onboarding`, body),
      onSuccess: fetchPapers,
    });
    if (!result?.ok && !result?.cancelled) throw result?.error ?? new Error("Onboarding failed");
    return result?.data?.paper?.id ?? null;
  }, [runOnboardAction, fetchPapers]);

  const getPaperSignedPdf = useCallback(async (paperId, documentId) => {
    const data = await api.get(`${CMS_BASE}/pyq-papers/${paperId}/signed-pdf?document_id=${encodeURIComponent(documentId)}`);
    return data.signed_url;
  }, []);

  const fetchPaperQuestions = useCallback(async (paperId) => {
    const res = await api.get(`${CMS_BASE}/pyq-questions?pyq_paper_id=${encodeURIComponent(paperId)}&limit=200`);
    return res.items || [];
  }, []);

  const fetchPyqDocuments = useCallback(async () => {
    if (!examId) return [];
    const params = new URLSearchParams({ exam_id: examId, document_kind: "pyq_paper", limit: "200" });
    const res = await api.get(`${CMS_BASE}/documents?${params}`);
    return res.items || res || [];
  }, [examId]);

  const fetchPyqSources = useCallback(async () => {
    if (!examId) return [];
    const params = new URLSearchParams({ exam_id: examId, limit: "200" });
    const res = await api.get(`${CMS_BASE}/pyq-sources?${params}`);
    return res.items || res || [];
  }, [examId]);

  return {
    papers,
    selectedPaperId,
    setSelectedPaperId,
    loading,
    error,
    refetch: fetchPapers,
    reviewPaper,
    patchPaper,
    saveProvenance,
    onboardPaper,
    getPaperSignedPdf,
    fetchPaperQuestions,
    fetchPyqDocuments,
    fetchPyqSources,
  };
}
