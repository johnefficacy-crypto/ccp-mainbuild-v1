import { useCallback, useEffect, useState } from "react";
import { api } from "../../../../lib/api";
import useApiAction from "../../../../lib/hooks/useApiAction";

const CMS_BASE = "/api/admin/exam-intelligence-cms";
const DOC_BASE = `${CMS_BASE}/documents`;

// document_assets.status values that are terminal (no more polling needed).
function isTerminalDocStatus(s) {
  return s === "processed" || s === "failed" || s === "archived";
}
// document_processing_jobs.status values that are terminal.
function isTerminalJobStatus(s) {
  return s === "succeeded" || s === "failed" || s === "skipped";
}

export function usePyqWorkbench(examId, cycleId) {
  const [papers, setPapers] = useState([]);
  const [selectedPaperId, setSelectedPaperId] = useState(null);
  const [loading, setLoading] = useState(false);
  // `loaded` flips true only after the first fetch settles, so the empty state
  // never flashes on the initial pre-fetch render (loading inits false, papers
  // inits []). Without it the empty CTA appears, vanishes during the fetch, and
  // reappears — a flash for operators and a race for synchronous test queries.
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(null);

  const { run: runReviewAction } = useApiAction();
  const { run: runPatchAction } = useApiAction();
  const { run: runProvenanceAction } = useApiAction();
  const { run: runOnboardAction } = useApiAction();
  const { run: runSourceReviewAction } = useApiAction();
  const { run: runUploadAction } = useApiAction();

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
      setLoaded(true);
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

  // ── Inline PYQ document upload (OD-5 follow-up) ────────────────────────────
  // Runs the same upload sequence DocumentsPanel uses, scoped to this exam and
  // document_kind=pyq_paper, then polls extraction status until terminal.
  // Resolves with { id, status, extraction, ok } so the modal can link the new
  // document_id during onboarding.
  //
  // GOVERNANCE: the two state-changing POSTs (upload-url creates a
  // document_assets row; complete-upload flips status→processing and enqueues
  // extraction) run INSIDE useApiAction, as required for user-triggered
  // mutations (busy/error semantics). The binary PUT bypasses api.post because
  // the body is raw bytes, not JSON (AGENTS.md pattern #4), and the status poll
  // is a background read — both are exempt from the mutation rule.
  const uploadPyqDocument = useCallback(async (file, { onProgress } = {}) => {
    if (!examId) throw new Error("No exam selected");
    if (!file) throw new Error("Choose a PDF file.");
    if (file.type !== "application/pdf") throw new Error("Only PDF files are accepted.");

    const report = (phase, extra = {}) => { onProgress?.({ phase, ...extra }); };

    const outcome = await runUploadAction({
      errorMessage: "PDF upload failed.",
      action: async () => {
        // Step 1 — mint signed URL + create document_assets row (mutation)
        report("requesting-url");
        const signed = await api.post(`${DOC_BASE}/upload-url`, {
          exam_id: examId,
          exam_cycle_id: cycleId || null,
          exam_phase_id: null,
          document_kind: "pyq_paper",
          filename: file.name,
          mime_type: file.type,
          size_bytes: file.size,
          exam_identity: null,
          structural_format: null,
          source_kind: null,
        });

        // Step 2 — PUT bytes directly to storage (raw binary, not JSON; PUT
        // intentionally uses fetch, not api.post — AGENTS.md pattern #4).
        report("uploading");
        const put = await fetch(signed.upload_url, {
          method: "PUT",
          headers: { "content-type": file.type },
          body: file,
        });
        if (!put.ok) throw new Error(`Storage upload failed (${put.status})`);

        // Step 3 — complete upload: status → processing, enqueue extraction (mutation)
        report("completing");
        await api.post(`${DOC_BASE}/complete-upload`, { document_id: signed.document_id });

        // Step 4 — poll extraction status until terminal (background read).
        report("extracting", { documentId: signed.document_id });
        const documentId = signed.document_id;
        const POLL_MS = 3000;
        const MAX_POLLS = 100; // ~5 min ceiling so a stuck job never loops forever
        for (let i = 0; i < MAX_POLLS; i += 1) {
          // eslint-disable-next-line no-await-in-loop
          const r = await api.get(`${DOC_BASE}/${documentId}`).catch(() => null);
          const docStatus = r?.document?.status;
          const jobStatus = r?.extraction?.status;
          if (isTerminalDocStatus(docStatus) || isTerminalJobStatus(jobStatus)) {
            const ok = docStatus !== "failed" && jobStatus !== "failed";
            report(ok ? "ready" : "failed", { documentId, status: docStatus, extraction: r?.extraction || {} });
            return { id: documentId, status: docStatus, extraction: r?.extraction || {}, ok };
          }
          report("extracting", { documentId, status: docStatus, extraction: r?.extraction || {} });
          // eslint-disable-next-line no-await-in-loop
          await new Promise((resolve) => setTimeout(resolve, POLL_MS));
        }
        // Polling ceiling hit — the row exists and is linkable; surface as processing.
        report("ready", { documentId, status: "processing" });
        return { id: documentId, status: "processing", extraction: {}, ok: true };
      },
    });

    if (!outcome?.ok && !outcome?.cancelled) throw outcome?.error ?? new Error("Upload failed");
    return outcome?.data ?? null;
  }, [examId, cycleId, runUploadAction]);

  // ── PYQ source trust lifecycle (OD-2 / Finding 7 follow-up) ────────────────
  // POSTs the source review (verify / reject / re-queue) against the backend
  // contract, then refetches the paper list so any downstream summary reflects
  // the new trust_status. Mutation goes through useApiAction (governance).
  const reviewPyqSource = useCallback(async (sourceId, status, reason) => {
    const result = await runSourceReviewAction({
      action: () => api.post(`${CMS_BASE}/pyq-sources/${sourceId}/review`, { status, reason }),
      onSuccess: fetchPapers,
    });
    if (!result?.ok && !result?.cancelled) throw result?.error ?? new Error("Source review failed");
    return result?.data ?? null;
  }, [runSourceReviewAction, fetchPapers]);

  return {
    papers,
    selectedPaperId,
    setSelectedPaperId,
    loading,
    loaded,
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
    uploadPyqDocument,
    reviewPyqSource,
  };
}
