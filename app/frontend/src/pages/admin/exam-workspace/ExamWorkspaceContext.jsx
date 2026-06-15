import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../../../lib/api";

const ExamWorkspaceContext = createContext(null);

const REVIEW_BASE = "/api/admin/exam-intelligence";

export function ExamWorkspaceProvider({ children, variant = "workspace" }) {
  const { exam_id, cycle_id } = useParams();

  const [exam, setExam] = useState(null);
  const [cycle, setCycle] = useState(null);
  const [cycles, setCycles] = useState([]);
  const [phases, setPhases] = useState([]);
  const [organization, setOrganization] = useState(null);
  const [family, setFamily] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Readiness — fetched separately so it never blocks the shell render
  const [readiness, setReadiness] = useState(null);
  const [readiness_loading, setReadinessLoading] = useState(false);
  const [readiness_error, setReadinessError] = useState("");

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
      setOrganization(d.organization ?? null);
      setFamily(d.family ?? null);
    } catch (e) {
      setError(e?.message || "Failed to load workspace context");
    } finally {
      setLoading(false);
    }
  }, [exam_id, cycle_id]);

  const fetchReadiness = useCallback(async () => {
    if (!exam_id) return;
    setReadinessLoading(true);
    setReadinessError("");
    try {
      const params = new URLSearchParams();
      if (cycle_id) params.set("cycle_id", cycle_id);
      const qs = params.toString();
      const url = `${REVIEW_BASE}/workspace/${encodeURIComponent(exam_id)}/readiness${qs ? `?${qs}` : ""}`;
      const d = await api.get(url);
      setReadiness(d);
    } catch (e) {
      setReadinessError(e?.message || "Failed to load readiness");
    } finally {
      setReadinessLoading(false);
    }
  }, [exam_id, cycle_id]);

  useEffect(() => { fetchContext(); }, [fetchContext]);
  useEffect(() => { fetchReadiness(); }, [fetchReadiness]);

  return (
    <ExamWorkspaceContext.Provider
      value={{
        variant,
        exam, cycle, cycles, phases, organization, family, loading, error, refetch: fetchContext,
        readiness, readiness_loading, readiness_error, refetchReadiness: fetchReadiness,
      }}
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
