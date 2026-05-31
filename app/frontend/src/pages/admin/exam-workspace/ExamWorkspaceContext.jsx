import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../../../lib/api";

const ExamWorkspaceContext = createContext(null);

const REVIEW_BASE = "/api/admin/exam-intelligence";

export function ExamWorkspaceProvider({ children }) {
  const { exam_id, cycle_id } = useParams();

  const [exam, setExam] = useState(null);
  const [cycle, setCycle] = useState(null);
  const [cycles, setCycles] = useState([]);
  const [phases, setPhases] = useState([]);
  const [readiness, setReadiness] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchContext = useCallback(async () => {
    if (!exam_id) return;
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (cycle_id) params.set("cycle_id", cycle_id);
      const qs = params.toString();
      const url = `${REVIEW_BASE}/workspace/${encodeURIComponent(exam_id)}/context${qs ? `?${qs}` : ""}`;
      const d = await api.get(url);
      setExam(d.exam ?? null);
      setCycle(d.cycle ?? null);
      setCycles(d.cycles ?? []);
      setPhases(d.phases ?? []);
      setReadiness(d.readiness ?? null);
    } catch (e) {
      setError(e?.message || "Failed to load workspace context");
    } finally {
      setLoading(false);
    }
  }, [exam_id, cycle_id]);

  useEffect(() => { fetchContext(); }, [fetchContext]);

  return (
    <ExamWorkspaceContext.Provider
      value={{ exam, cycle, cycles, phases, readiness, loading, error, refetch: fetchContext }}
    >
      {children}
    </ExamWorkspaceContext.Provider>
  );
}

export function useExamWorkspace() {
  const ctx = useContext(ExamWorkspaceContext);
  if (ctx === null) {
    throw new Error("useExamWorkspace must be used inside ExamWorkspaceProvider");
  }
  return ctx;
}
