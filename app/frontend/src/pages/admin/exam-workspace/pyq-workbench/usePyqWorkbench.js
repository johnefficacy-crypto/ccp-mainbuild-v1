import { useCallback, useEffect, useState } from "react";
import { api } from "../../../../lib/api";

const CMS_BASE = "/api/admin/exam-intelligence-cms";

export function usePyqWorkbench(examId, cycleId) {
  const [papers, setPapers] = useState([]);
  const [selectedPaperId, setSelectedPaperId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPapers = useCallback(async () => {
    if (!examId) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ exam_id: examId });
      if (cycleId) params.set("exam_cycle_id", cycleId);
      const res = await api.get(`${CMS_BASE}/pyq-papers?${params}`);
      setPapers(res.items || []);
    } catch (e) {
      setError(e?.message || "Failed to load papers");
    } finally {
      setLoading(false);
    }
  }, [examId, cycleId]);

  useEffect(() => { fetchPapers(); }, [fetchPapers]);

  const reviewPaper = useCallback(async (paperId, status, reason) => {
    await api.post(`${CMS_BASE}/pyq-papers/${paperId}/review`, { status, reason });
    await fetchPapers();
  }, [fetchPapers]);

  const patchPaper = useCallback(async (paperId, payload, reason) => {
    await api.patch(`${CMS_BASE}/pyq-papers/${paperId}`, { payload, reason });
    await fetchPapers();
  }, [fetchPapers]);

  const getPaperSignedPdf = useCallback(async (paperId, documentId) => {
    const data = await api.get(`${CMS_BASE}/pyq-papers/${paperId}/signed-pdf?document_id=${encodeURIComponent(documentId)}`);
    return data.signed_url;
  }, []);

  return { papers, selectedPaperId, setSelectedPaperId, loading, error, refetch: fetchPapers, reviewPaper, patchPaper, getPaperSignedPdf };
}
