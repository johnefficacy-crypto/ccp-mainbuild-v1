import React, { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { api } from "../../../lib/api";
import { StatusBadge } from "../../../shared/ui/core";
import {
  BUSINESS_PRIORITY_LABELS,
  CADENCE_LABELS,
  EXAM_PURPOSE_LABELS,
  REVIEWER_STATUS_PLANNER_NOTE,
} from "./ExamIntelGlossary";

/**
 * ExamListShell — Wave 4.6G.
 *
 * A reusable, searchable + filterable + paginated exam list driven ONLY by the
 * existing /api/admin/exam-intelligence/exams contract (q, exam_type,
 * active_state, management_mode, cadence, exam_family_id, limit, offset). It is
 * modeled on ExamIntelligence.jsx's api + reducer read so it can expose
 * total_count / has_next / offset for honest pagination (useApiCollection does
 * not surface those).
 *
 * Reuse seams:
 *   - `rowAction(exam) => ReactNode` injects the per-row action cell, so the
 *     same shell can serve the console (Open console / Advanced workspace) and,
 *     later, the Registry.
 *   - `title` / `eyebrow` / `helper` frame the list.
 *
 * Deliberate non-goals (4.6H / 4.6I): NO workflow chips (Needs action /
 * Blocked / Missing PYQ / Stale / Ready), NO aggregate counts, NO sort param,
 * NO readiness percentage. Columns are built ONLY from fields /exams returns.
 */

const PAGE_SIZE = 25;

// readiness_level → StatusBadge status (no percentage, ever).
const READINESS_STATUS = {
  ready: "ready",
  partial: "partial",
  not_ready: "missing",
};

const INITIAL_FILTERS = {
  search: "",
  examType: "",
  activeState: "active",
  managementMode: "",
  cadence: "",
  examFamilyId: "",
  page: 0,
};

function filtersReducer(state, action) {
  switch (action.type) {
    case "SET_FILTER":
      return { ...state, [action.key]: action.value, page: 0 };
    case "SET_PAGE":
      return { ...state, page: action.page };
    case "RESET":
      return { ...INITIAL_FILTERS };
    default:
      return state;
  }
}

function laneLabel(mode) {
  if (mode == null) return BUSINESS_PRIORITY_LABELS.null.label;
  return (BUSINESS_PRIORITY_LABELS[mode] ?? BUSINESS_PRIORITY_LABELS.null).label;
}

function isDefaultFilters(f) {
  return (
    !f.search.trim() &&
    !f.examType &&
    f.activeState === "active" &&
    !f.managementMode &&
    !f.cadence &&
    !f.examFamilyId
  );
}

export default function ExamListShell({
  title = "Exams",
  eyebrow = "Exam Governance Console",
  helper = null,
  rowAction,
}) {
  const [exams, setExams] = useState({
    items: [],
    count: 0,
    total_count: 0,
    has_next: false,
    limit: PAGE_SIZE,
    offset: 0,
  });
  const [status, setStatus] = useState("idle"); // idle | loading | data | empty | error
  const [error, setError] = useState("");

  const [families, setFamilies] = useState([]);
  useEffect(() => {
    // Background read for the family filter; never blocks the list.
    api
      .get("/api/admin/exam-intelligence-cms/exam-families?is_active=true&limit=200")
      .then((d) => setFamilies(d?.items || []))
      .catch(() => {});
  }, []);

  const [filters, dispatch] = useReducer(filtersReducer, INITIAL_FILTERS);
  const { page } = filters;

  const seqRef = useRef(0);

  const loadExams = useCallback(async (f) => {
    const offset = f.page * PAGE_SIZE;
    const qs = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
    if (f.search.trim()) qs.set("q", f.search.trim());
    if (f.examType) qs.set("exam_type", f.examType);
    if (f.activeState) qs.set("active_state", f.activeState);
    if (f.managementMode) qs.set("management_mode", f.managementMode);
    if (f.cadence) qs.set("cadence", f.cadence);
    if (f.examFamilyId) qs.set("exam_family_id", f.examFamilyId);

    const mySeq = ++seqRef.current;
    setStatus("loading");
    setError("");
    try {
      const d = await api.get(`/api/admin/exam-intelligence/exams?${qs}`);
      if (mySeq !== seqRef.current) return;
      const items = d?.items || [];
      setExams({
        items,
        count: d?.count ?? items.length,
        total_count: d?.total_count ?? items.length,
        has_next: d?.has_next ?? false,
        limit: d?.limit ?? PAGE_SIZE,
        offset: d?.offset ?? offset,
      });
      setStatus(items.length ? "data" : "empty");
    } catch (e) {
      if (mySeq !== seqRef.current) return;
      setError(e?.message || "Could not load exams");
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    loadExams(filters);
  }, [filters, loadExams]);

  const setFilter = (key, value) => dispatch({ type: "SET_FILTER", key, value });
  const hasPrev = page > 0;
  const rangeStart = exams.total_count === 0 ? 0 : exams.offset + 1;
  const rangeEnd = Math.max(rangeStart, exams.offset + exams.items.length);

  return (
    <div className="oc-main" style={{ padding: 22 }} data-testid="exam-list-shell">
      <div className="lbl" style={{ marginBottom: 4 }}>{eyebrow}</div>
      <h1 className="oc-title disp" style={{ fontSize: 24, marginBottom: helper ? 4 : 12 }}>
        {title}
      </h1>
      {helper ? <p className="anno" style={{ marginBottom: 12 }}>{helper}</p> : null}

      {/* ── Filter bar: search + the supported /exams filters only ── */}
      <div className="row" style={{ flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
        <label className="lbl" htmlFor="exam-list-search" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
          Search exams
        </label>
        <input
          id="exam-list-search"
          type="search"
          className="input"
          style={{ width: 200 }}
          placeholder="Search name or key…"
          value={filters.search}
          onChange={(e) => setFilter("search", e.target.value)}
          data-testid="exam-list-search"
          aria-label="Search exams"
        />
        <select
          className="select"
          value={filters.examType}
          onChange={(e) => setFilter("examType", e.target.value)}
          data-testid="exam-list-filter-type"
          aria-label="Filter by exam purpose"
        >
          <option value="">All purposes</option>
          {Object.entries(EXAM_PURPOSE_LABELS).map(([k, { label }]) => (
            <option key={k} value={k}>{label}</option>
          ))}
        </select>
        <select
          className="select"
          value={filters.activeState}
          onChange={(e) => setFilter("activeState", e.target.value)}
          data-testid="exam-list-filter-active"
          aria-label="Filter by active status"
        >
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="all">All</option>
        </select>
        {families.length > 0 && (
          <select
            className="select"
            value={filters.examFamilyId}
            onChange={(e) => setFilter("examFamilyId", e.target.value)}
            data-testid="exam-list-filter-family"
            aria-label="Filter by exam family"
          >
            <option value="">All families</option>
            {families.map((f) => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>
        )}
        <select
          className="select"
          value={filters.managementMode}
          onChange={(e) => setFilter("managementMode", e.target.value)}
          data-testid="exam-list-filter-lane"
          aria-label="Filter by management lane"
        >
          <option value="">All (non-archive)</option>
          {Object.entries(BUSINESS_PRIORITY_LABELS)
            .filter(([k]) => k !== "null")
            .map(([k, { label }]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          <option value="__null__">{BUSINESS_PRIORITY_LABELS.null.label}</option>
        </select>
        <select
          className="select"
          value={filters.cadence}
          onChange={(e) => setFilter("cadence", e.target.value)}
          data-testid="exam-list-filter-cadence"
          aria-label="Filter by cadence"
        >
          <option value="">All cadences</option>
          {Object.entries(CADENCE_LABELS).map(([k, label]) => (
            <option key={k} value={k}>{label}</option>
          ))}
        </select>
        {!isDefaultFilters(filters) && (
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => dispatch({ type: "RESET" })}
            data-testid="exam-list-clear"
          >
            Clear filters
          </button>
        )}
        {status !== "idle" && status !== "loading" && (
          <span className="anno" style={{ marginLeft: "auto" }} data-testid="exam-list-count">
            {exams.total_count} exam{exams.total_count === 1 ? "" : "s"}
          </span>
        )}
      </div>

      {status === "loading" && (
        <div className="row-sub" data-testid="exam-list-loading">Loading exams…</div>
      )}

      {status === "error" && (
        <div className="err-row" data-testid="exam-list-error">
          {error || "Could not load exams."}{" "}
          <button className="btn" onClick={() => loadExams(filters)}>Retry</button>
        </div>
      )}

      {status === "empty" && (
        <div className="empty" data-testid="exam-list-empty">
          <div className="empty-title">No exams match these filters.</div>
          {!isDefaultFilters(filters) ? (
            <button
              type="button"
              className="btn"
              onClick={() => dispatch({ type: "RESET" })}
              data-testid="exam-list-empty-clear"
            >
              Clear search &amp; filters
            </button>
          ) : (
            <span className="anno">No exams are registered yet.</span>
          )}
        </div>
      )}

      {status === "data" && (
        <div className="card" style={{ overflow: "hidden" }}>
          <table className="tbl" style={{ width: "100%" }} data-testid="exam-list-table">
            <thead>
              <tr>
                <th>Exam</th>
                <th>Purpose</th>
                <th>Lane</th>
                <th>Cadence</th>
                <th>Planner-ready topics</th>
                <th title={REVIEWER_STATUS_PLANNER_NOTE}>Readiness</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {exams.items.map((exam) => (
                <tr key={exam.id} data-testid={`exam-list-row-${exam.id}`}>
                  <td>
                    <div className="row-ttl">{exam.name ?? exam.slug ?? exam.id}</div>
                    {exam.slug ? (
                      <div className="mono anno" data-testid={`exam-list-slug-${exam.id}`}>{exam.slug}</div>
                    ) : null}
                  </td>
                  <td className="anno">
                    {EXAM_PURPOSE_LABELS[exam.exam_type]?.label ?? exam.exam_type ?? "—"}
                  </td>
                  <td>
                    <span className="badge neutral no-dot">{laneLabel(exam.management_mode)}</span>
                  </td>
                  <td className="anno">{CADENCE_LABELS[exam.cadence] ?? "Unknown"}</td>
                  <td className="mono">
                    {exam.coverage_total == null && exam.verified_topic_count == null ? (
                      "—"
                    ) : (
                      <>
                        {exam.verified_topic_count ?? 0}
                        <span className="anno"> / {exam.coverage_total ?? 0}</span>
                      </>
                    )}
                  </td>
                  <td>
                    <StatusBadge
                      status={READINESS_STATUS[exam.readiness_level] || "missing"}
                      label={(exam.readiness_level || "not_ready").replaceAll("_", " ")}
                    />
                  </td>
                  <td style={{ textAlign: "right" }}>
                    {typeof rowAction === "function" ? rowAction(exam) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div
            className="row"
            style={{ justifyContent: "space-between", alignItems: "center", padding: "8px 12px", borderTop: "1px solid var(--rule)" }}
            data-testid="exam-list-pagination"
          >
            <span className="anno" data-testid="exam-list-range">
              {exams.total_count === 0 ? "No results" : `${rangeStart}–${rangeEnd} of ${exams.total_count}`}
            </span>
            <span className="row" style={{ gap: 8 }}>
              <button
                type="button"
                className="btn btn-ghost"
                disabled={!hasPrev}
                onClick={() => dispatch({ type: "SET_PAGE", page: page - 1 })}
                data-testid="exam-list-prev"
                aria-label="Previous page"
              >
                ← Prev
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                disabled={!exams.has_next}
                onClick={() => dispatch({ type: "SET_PAGE", page: page + 1 })}
                data-testid="exam-list-next"
                aria-label="Next page"
              >
                Next →
              </button>
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
