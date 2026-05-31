import { useCallback, useState } from "react";
import { api, apiFetch } from "../../../../../lib/api";

const CMS_BASE = "/api/admin/exam-intelligence-cms";

const INITIAL = {
  step: "upload",
  selected_paper_id: null,
  csv_text: null,
  csv_filename: null,
  preflight: null,
  override_errors: false,
  reason: "",
  commit_result: null,
  loading: { upload: false, preflight: false, commit: false },
  error: { upload: null, preflight: null, commit: null },
};

export function useBulkImport(initialPaperId = null) {
  const [state, setState] = useState({ ...INITIAL, selected_paper_id: initialPaperId });

  const set = (patch) => setState((s) => ({ ...s, ...patch }));
  const setLoading = (key, val) =>
    setState((s) => ({ ...s, loading: { ...s.loading, [key]: val } }));
  const setError = (key, val) =>
    setState((s) => ({ ...s, error: { ...s.error, [key]: val } }));

  const selectPaper = useCallback((paperId) => {
    set({ selected_paper_id: paperId });
  }, []);

  const selectFile = useCallback((file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      set({ csv_text: e.target.result, csv_filename: file.name });
    };
    reader.readAsText(file);
  }, []);

  const runPreflight = useCallback(async (paperId, csvText) => {
    setLoading("preflight", true);
    setError("preflight", null);
    try {
      const res = await apiFetch(
        `${CMS_BASE}/pyq-papers/${encodeURIComponent(paperId)}/bulk-import/preflight`,
        {
          method: "POST",
          headers: { "Content-Type": "text/csv" },
          body: csvText,
        },
      );
      setState((s) => ({ ...s, preflight: res, step: "preview", loading: { ...s.loading, preflight: false } }));
    } catch (e) {
      setLoading("preflight", false);
      setError("preflight", e?.message || "Preflight failed");
    }
  }, []);

  const setOverride = useCallback((val) => set({ override_errors: val }), []);
  const setReason = useCallback((val) => set({ reason: val }), []);

  const runCommit = useCallback(async (paperId, importToken, overrideErrors, reason) => {
    setLoading("commit", true);
    setError("commit", null);
    try {
      const res = await api.post(
        `${CMS_BASE}/pyq-papers/${encodeURIComponent(paperId)}/bulk-import/commit`,
        { import_token: importToken, override_errors: overrideErrors, reason },
      );
      setState((s) => ({ ...s, commit_result: res, step: "result", loading: { ...s.loading, commit: false } }));
    } catch (e) {
      setLoading("commit", false);
      setError("commit", e?.message || "Commit failed");
    }
  }, []);

  const reset = useCallback((initialPaper = null) => {
    setState({ ...INITIAL, selected_paper_id: initialPaper });
  }, []);

  const goToStep = useCallback((step) => set({ step }), []);

  return { state, selectPaper, selectFile, runPreflight, setOverride, setReason, runCommit, reset, goToStep };
}
