import { useState, useEffect, useCallback } from "react";
import { api } from "../../../lib/api";

export default function useCalibrationPriors(examId) {
  const [calibrated, setCalibrated] = useState(null); // null=loading, true/false
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error] = useState(null);

  const fetch = useCallback(async () => {
    if (!examId) { setLoading(false); return; }
    setLoading(true);
    try {
      const d = await api.get("/api/study/self-assessment");
      setCalibrated(Boolean(d?.calibrated));
      setItems(Array.isArray(d?.items) ? d.items : []);
    } catch {
      setCalibrated(false);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [examId]);

  useEffect(() => { fetch(); }, [fetch]);

  const submit = useCallback(async (bands, attemptsUsed) => {
    await api.put("/api/study/self-assessment", { bands, attempts_used: attemptsUsed });
    setCalibrated(true);
  }, []);

  const skip = useCallback(() => {
    setCalibrated(true); // treat skip as done for this session
  }, []);

  return { calibrated, items, loading, error, submit, skip, refetch: fetch };
}
