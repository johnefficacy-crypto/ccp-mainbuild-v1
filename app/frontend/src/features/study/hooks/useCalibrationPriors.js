import { useState, useEffect, useCallback, useRef } from "react";
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
  const [checkFailed, setCheckFailed] = useState(false); // transient read failure
  const [status, setStatus] = useState("none"); // "completed" | "skipped" | "none"
  const [needsUpdate, setNeedsUpdate] = useState(false);
  const [requiredSubjects, setRequiredSubjects] = useState([]);
  const [items, setItems] = useState([]);
  const [attemptsUsed, setAttemptsUsed] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Stale-response guard. A slow GET for exam A can resolve after the user has
  // switched to exam B; applying A's payload would clobber B's gate state and
  // could wrongly unlock B. We capture a monotonically increasing generation id
  // and the requesting exam id at call time, and on resolution ignore the
  // response unless BOTH still match the latest request — and unless any
  // `exam_id` echoed by the server matches the exam we asked about.
  const requestGenRef = useRef(0);
  const examIdRef = useRef(examId);
  examIdRef.current = examId;

  const fetch = useCallback(async () => {
    if (!examId) {
      setLoading(false);
      return;
    }
    const gen = ++requestGenRef.current;
    const reqExamId = examId;
    const isStale = (d) =>
      gen !== requestGenRef.current ||
      reqExamId !== examIdRef.current ||
      (d && d.exam_id != null && d.exam_id !== reqExamId);
    setLoading(true);
    setError(null);
    try {
      const d = await api.get("/api/study/self-assessment");
      // Drop a response that no longer belongs to the current exam request.
      if (isStale(d)) return;
      setCalibrated(Boolean(d?.calibrated));
      // Fail-closed flag: the server sets this on a transient read error instead
      // of returning a bogus `calibrated`. The page must surface a retry state,
      // not the interstitial (no subjects) and not the plan controls.
      setCheckFailed(Boolean(d?.calibration_check_failed));
      setStatus(typeof d?.status === "string" ? d.status : "none");
      setNeedsUpdate(Boolean(d?.needs_update));
      setRequiredSubjects(Array.isArray(d?.required_subjects) ? d.required_subjects : []);
      setItems(Array.isArray(d?.items) ? d.items : []);
      setAttemptsUsed(
        typeof d?.attempts_used === "number" ? d.attempts_used : null,
      );
    } catch (e) {
      // Ignore errors from a superseded request too — otherwise a stale failure
      // would surface an error / flip calibrated for the exam now in view.
      if (isStale(null)) return;
      // Surface the error and allow retry; resolve calibrated to false so the
      // UI isn't wedged on a spinner, but do not silently treat the user as
      // uncalibrated forever — `error` is set and `retry` is exposed.
      setError(e?.message || "Couldn't load your calibration. Try again.");
      setCheckFailed(false);
      setCalibrated((prev) => (prev === null ? false : prev));
    } finally {
      // Only the latest request owns the loading flag; a superseded request
      // resolving late must not clear a spinner the current request still needs.
      if (gen === requestGenRef.current && reqExamId === examIdRef.current) {
        setLoading(false);
      }
    }
  }, [examId]);

  // Reset all gate state whenever the exam changes so a previous exam's
  // required_subjects / items / calibrated flag cannot leak across exams.
  // Bumping the generation here invalidates any GET still in flight for the
  // prior exam so it can never apply after the reset (belt-and-suspenders with
  // the per-request guard in `fetch`).
  useEffect(() => {
    requestGenRef.current += 1;
    setCalibrated(null);
    setCheckFailed(false);
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
    checkFailed,
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
