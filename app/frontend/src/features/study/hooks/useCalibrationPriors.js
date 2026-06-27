import { useState, useEffect, useCallback } from "react";
import { api } from "../../../lib/api";

// Authoritative calibration gate state for a single exam.
//
// `calibrated` is server-derived (a gate record + required-set emptiness) — we
// never infer it locally from items.length. `null` means "still loading"; the
// boolean value is only ever set from a GET response. On fetch error we set
// `error` and resolve `calibrated` to `false` so the page is not stuck on a
// spinner, but we surface the error and expose `retry` so the user can recover
// instead of being treated as permanently uncalibrated with no feedback.
export default function useCalibrationPriors(examId) {
  const [calibrated, setCalibrated] = useState(null); // null=loading, true/false
  const [status, setStatus] = useState("none"); // "completed" | "skipped" | "none"
  const [needsUpdate, setNeedsUpdate] = useState(false);
  const [requiredSubjects, setRequiredSubjects] = useState([]);
  const [items, setItems] = useState([]);
  const [attemptsUsed, setAttemptsUsed] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    if (!examId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const d = await api.get("/api/study/self-assessment");
      setCalibrated(Boolean(d?.calibrated));
      setStatus(typeof d?.status === "string" ? d.status : "none");
      setNeedsUpdate(Boolean(d?.needs_update));
      setRequiredSubjects(Array.isArray(d?.required_subjects) ? d.required_subjects : []);
      setItems(Array.isArray(d?.items) ? d.items : []);
      setAttemptsUsed(
        typeof d?.attempts_used === "number" ? d.attempts_used : null,
      );
    } catch (e) {
      // Surface the error and allow retry; resolve calibrated to false so the
      // UI isn't wedged on a spinner, but do not silently treat the user as
      // uncalibrated forever — `error` is set and `retry` is exposed.
      setError(e?.message || "Couldn't load your calibration. Try again.");
      setCalibrated((prev) => (prev === null ? false : prev));
    } finally {
      setLoading(false);
    }
  }, [examId]);

  // Reset all gate state whenever the exam changes so a previous exam's
  // required_subjects / items / calibrated flag cannot leak across exams.
  useEffect(() => {
    setCalibrated(null);
    setStatus("none");
    setNeedsUpdate(false);
    setRequiredSubjects([]);
    setItems([]);
    setAttemptsUsed(null);
    setError(null);
    setLoading(Boolean(examId));
  }, [examId]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const submit = useCallback(
    async (bands, used) => {
      setSaving(true);
      setError(null);
      try {
        const result = await api.put("/api/study/self-assessment", {
          bands,
          attempts_used: used,
        });
        // Refresh authoritative state so `calibrated` reflects whether the full
        // required set is now covered (a partial save may leave it false).
        await fetch();
        return result;
      } catch (e) {
        setError(e?.message || "Couldn't save your answers. Try again.");
        throw e;
      } finally {
        setSaving(false);
      }
    },
    [fetch],
  );

  const skip = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      const result = await api.post("/api/study/self-assessment/skip", {});
      // Skip is now persisted server-side; refetch so calibrated becomes true
      // and survives a reload.
      await fetch();
      return result;
    } catch (e) {
      setError(e?.message || "Couldn't skip right now. Try again.");
      throw e;
    } finally {
      setSaving(false);
    }
  }, [fetch]);

  return {
    calibrated,
    status,
    needsUpdate,
    requiredSubjects,
    items,
    attemptsUsed,
    loading,
    saving,
    error,
    submit,
    skip,
    refetch: fetch,
    retry: fetch,
  };
}
