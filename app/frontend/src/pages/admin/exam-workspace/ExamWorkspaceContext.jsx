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

  // Readiness — gated on management contract validation (D04)
  const [readiness, setReadiness] = useState(null);
  const [readiness_loading, setReadinessLoading] = useState(false);
  const [readiness_error, setReadinessError] = useState("");

  // Management data — cycle-aware authority for verdict, action queue, identity
  const [mgmt, setMgmt] = useState(null);
  const [mgmtLoading, setMgmtLoading] = useState(false);
  const [mgmtError, setMgmtError] = useState("");
  const [mgmtVersionError, setMgmtVersionError] = useState(false);

  // D04: generation counter — incremented on every fetchMgmt call so that
  // stale in-flight responses (from rapid cycle changes) are discarded.
  // fetchReadiness checks this before committing to guarantee it belongs to
  // the same request generation as the management validation that allowed it.
  const mgmtGenRef = useRef(0);

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

  // D04: fetchReadiness is NOT triggered independently. It is called by fetchMgmt
  // only after the management contract has been validated for the same generation.
  // This eliminates the race where legacy readiness could be committed before or
  // after an unsupported-version management response clears it.
  const fetchReadiness = useCallback(async (expectedGen) => {
    if (!exam_id) return;
    setReadinessLoading(true);
    setReadinessError("");
    try {
      const params = new URLSearchParams();
      if (cycleId) params.set("cycle_id", cycleId);
      const qs = params.toString();
      const url = `${REVIEW_BASE}/workspace/${encodeURIComponent(exam_id)}/readiness${qs ? `?${qs}` : ""}`;
      const d = await api.get(url);
      // D04: discard if a newer mgmt request has superseded this generation.
      if (mgmtGenRef.current !== expectedGen) return;
      setReadiness(d);
    } catch (e) {
      if (mgmtGenRef.current !== expectedGen) return;
      setReadinessError(e?.message || "Failed to load readiness");
    } finally {
      if (mgmtGenRef.current === expectedGen) setReadinessLoading(false);
    }
  }, [exam_id, cycleId]);

  const fetchMgmt = useCallback(async () => {
    if (!exam_id) return;
    // D04: increment generation so any concurrent readiness fetch from a prior
    // call is invalidated.
    const gen = ++mgmtGenRef.current;
    setMgmtLoading(true);
    setMgmtError("");
    setMgmtVersionError(false);
    // D04: clear both stale readiness AND stale mgmt so semantic consumers
    // (SmartHeader, action console) do not render the previous cycle's verdict
    // until the new response validates and commits.
    setReadiness(null);
    setMgmt(null);
    try {
      const params = new URLSearchParams();
      if (cycleId) params.set("cycle_id", cycleId);
      const qs = params.toString();
      const url = `${REVIEW_BASE}/management/exams/${encodeURIComponent(exam_id)}${qs ? `?${qs}` : ""}`;
      const d = await api.get(url);
      // D04: stale response — a newer fetchMgmt has already started; discard.
      if (mgmtGenRef.current !== gen) return;
      if (!SUPPORTED_CONTRACT_VERSIONS.includes(d?.contract_version)) {
        // D04: fail-closed — suppress all semantic consumers for unsupported versions.
        setMgmtVersionError(true);
        setMgmtError("unsupported_contract_version");
        setMgmt(null);
        // readiness already cleared at start; do not fetch it.
      } else {
        setMgmt(d);
        // D04: only fetch readiness once management contract is validated and for
        // the same generation.  Not awaited — loading state managed independently.
        fetchReadiness(gen);
      }
    } catch (e) {
      if (mgmtGenRef.current !== gen) return;
      setMgmtError(e?.message || "Failed to load management data");
    } finally {
      if (mgmtGenRef.current === gen) setMgmtLoading(false);
    }
  }, [exam_id, cycleId, fetchReadiness]);

  useEffect(() => { fetchContext(); }, [fetchContext]);
  // fetchReadiness is triggered by fetchMgmt — no independent effect.
  useEffect(() => { fetchMgmt(); }, [fetchMgmt]);

  // D04/P1: refetchReadiness routes through fetchMgmt so every readiness refresh
  // is preceded by a fresh management-contract validation.  Direct readiness
  // calls (e.g. from ReviewActivatePanel after a row lock) would bypass the
  // version guard and contradict the sequencing invariant.
  const refetchReadiness = useCallback(() => fetchMgmt(), [fetchMgmt]);

  return (
    <ExamWorkspaceContext.Provider
      value={{
        exam, cycle, cycles, phases, organization, family, loading, error, refetch: fetchContext,
        readiness, readiness_loading, readiness_error, refetchReadiness,
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
