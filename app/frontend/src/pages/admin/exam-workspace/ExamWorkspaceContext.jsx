import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "../../../lib/api";

const ExamWorkspaceContext = createContext(null);

const REVIEW_BASE = "/api/admin/exam-intelligence";

// D04: contract versions this client knows how to interpret
const SUPPORTED_CONTRACT_VERSIONS = [1];

export function ExamWorkspaceProvider({ children }) {
  const { exam_id } = useParams();
  const [searchParams] = useSearchParams();
  const cycleId = searchParams.get("cycle") || null;

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

  // Management data — cycle-aware authority for verdict, action queue, identity
  const [mgmt, setMgmt] = useState(null);
  const [mgmtLoading, setMgmtLoading] = useState(false);
  const [mgmtError, setMgmtError] = useState("");
  const [mgmtVersionError, setMgmtVersionError] = useState(false);
  // D04: ref tracks version error so fetchReadiness can check it even when the
  // two fetches race and readiness resolves after mgmt clears it.
  const mgmtVersionErrorRef = useRef(false);

  const fetchContext = useCallback(async () => {
    if (!exam_id) return;
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (cycleId) params.set("cycle_id", cycleId);
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
  }, [exam_id, cycleId]);

  const fetchReadiness = useCallback(async () => {
    if (!exam_id) return;
    setReadinessLoading(true);
    setReadinessError("");
    try {
      const params = new URLSearchParams();
      if (cycleId) params.set("cycle_id", cycleId);
      const qs = params.toString();
      const url = `${REVIEW_BASE}/workspace/${encodeURIComponent(exam_id)}/readiness${qs ? `?${qs}` : ""}`;
      const d = await api.get(url);
      // D04: if mgmt resolved with an unsupported version while this fetch was
      // in-flight, discard the result rather than restoring suppressed readiness.
      if (mgmtVersionErrorRef.current) return;
      setReadiness(d);
    } catch (e) {
      setReadinessError(e?.message || "Failed to load readiness");
    } finally {
      setReadinessLoading(false);
    }
  }, [exam_id, cycleId]);

  const fetchMgmt = useCallback(async () => {
    if (!exam_id) return;
    setMgmtLoading(true);
    setMgmtError("");
    setMgmtVersionError(false);
    mgmtVersionErrorRef.current = false;
    try {
      const params = new URLSearchParams();
      if (cycleId) params.set("cycle_id", cycleId);
      const qs = params.toString();
      const url = `${REVIEW_BASE}/management/exams/${encodeURIComponent(exam_id)}${qs ? `?${qs}` : ""}`;
      const d = await api.get(url);
      if (!SUPPORTED_CONTRACT_VERSIONS.includes(d?.contract_version)) {
        // D04: fail-closed — null out mgmt AND legacy readiness to suppress all semantic consumers.
        // Also set the ref so a concurrent fetchReadiness that resolves after this point discards its result.
        mgmtVersionErrorRef.current = true;
        setMgmtVersionError(true);
        setMgmtError("unsupported_contract_version");
        setMgmt(null);
        setReadiness(null);
      } else {
        setMgmt(d);
      }
    } catch (e) {
      setMgmtError(e?.message || "Failed to load management data");
    } finally {
      setMgmtLoading(false);
    }
  }, [exam_id, cycleId]);

  useEffect(() => { fetchContext(); }, [fetchContext]);
  useEffect(() => { fetchReadiness(); }, [fetchReadiness]);
  useEffect(() => { fetchMgmt(); }, [fetchMgmt]);

  return (
    <ExamWorkspaceContext.Provider
      value={{
        exam, cycle, cycles, phases, organization, family, loading, error, refetch: fetchContext,
        readiness, readiness_loading, readiness_error, refetchReadiness: fetchReadiness,
        mgmt, mgmtLoading, mgmtError, mgmtVersionError, refetchMgmt: fetchMgmt,
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
