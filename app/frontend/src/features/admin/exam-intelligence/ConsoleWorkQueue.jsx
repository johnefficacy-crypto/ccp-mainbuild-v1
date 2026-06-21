import React, { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../../lib/api";
import { StatusBadge } from "../../../shared/ui/core";
import { humanizeToken } from "./operatorChrome";
import {
  BUSINESS_PRIORITY_LABELS,
  CADENCE_LABELS,
  EXAM_PURPOSE_LABELS,
} from "./ExamIntelGlossary";

/**
 * ConsoleWorkQueue — Wave 4.6H-FE.
 *
 * The Exam Governance Console work-queue list. Its data layer is the truthful
 * work-queue endpoints from PR #703:
 *   GET /api/admin/exam-intelligence/console/exams    (rows + server workflow/sort/paging)
 *   GET /api/admin/exam-intelligence/console/summary  (base-scoped counts)
 *
 * The backend owns status, flags, blocker text, sort, and all counts. This
 * component NEVER computes status/flags/sort, and NEVER derives catalogue
 * counts from the current page. It does not touch /exams (that stays
 * ExamListShell's generic contract) and renders no readiness/confidence %.
 */

const PAGE_SIZE = 25;

const STATUS_META = {
  blocked: { tone: "pill-rose", label: "Blocked" },
  needs_action: { tone: "pill-amber", label: "Needs action" },
  ready: { tone: "pill-sage", label: "Ready" },
};

// Server flag value → human label. (Subset returned per row.)
const FLAG_LABELS = {
  pending_review: "Pending review",
  missing_pyq: "Missing PYQ",
  missing_coverage: "Missing locked coverage",
  stale_review_queue: "Stale review",
};

// Counted workflow chips — these are the ONLY workflows the summary counts.
const SUMMARY_CHIPS = [
  { value: "", label: "All", countKey: "total_count" },
  { value: "blocked", label: "Blocked", countKey: "blocked" },
  { value: "needs_action", label: "Needs action", countKey: "needs_action" },
  { value: "ready", label: "Ready", countKey: "ready" },
  { value: "pending_review", label: "Pending review", countKey: "pending_review" },
  { value: "stale_review_queue", label: "Stale review", countKey: "stale_review_queue" },
];

// Uncounted workflows — server-filterable but NOT in the summary (no number).
const UNCOUNTED_WORKFLOWS = [
  { value: "missing_pyq", label: "Missing PYQ" },
  { value: "missing_coverage", label: "Missing coverage" },
];

const SORTS = [
  { value: "blockers_first", label: "Blockers first" },
  { value: "management_lane", label: "Management lane" },
  { value: "name", label: "Name" },
];

const INITIAL = {
  search: "",
  examType: "",
  activeState: "active",
  managementMode: "",
  cadence: "",
  examFamilyId: "",
  workflow: "",
  sort: "blockers_first",
  page: 0,
};

function reducer(state, action) {
  switch (action.type) {
    case "SET_FILTER":
      // Any base filter, workflow, or sort change resets pagination.
      return { ...state, [action.key]: action.value, page: 0 };
    case "SET_PAGE":
      return { ...state, page: action.page };
    case "CLEAR_WORKFLOW":
      return { ...state, workflow: "", page: 0 };
    case "RESET":
      return { ...INITIAL };
    default:
      return state;
  }
}

function laneLabel(mode) {
  if (mode == null) return BUSINESS_PRIORITY_LABELS.null.label;
  return (BUSINESS_PRIORITY_LABELS[mode] ?? BUSINESS_PRIORITY_LABELS.null).label;
}

function baseParams(f) {
  const qs = new URLSearchParams();
  if (f.search.trim()) qs.set("q", f.search.trim());
  if (f.examType) qs.set("exam_type", f.examType);
  if (f.activeState) qs.set("active_state", f.activeState);
  if (f.managementMode) qs.set("management_mode", f.managementMode);
  if (f.cadence) qs.set("cadence", f.cadence);
  if (f.examFamilyId) qs.set("exam_family_id", f.examFamilyId);
  return qs;
}

function isDefaultFilters(f) {
  return (
    !f.search.trim() && !f.examType && f.activeState === "active" &&
    !f.managementMode && !f.cadence && !f.examFamilyId
  );
}

export default function ConsoleWorkQueue() {
  const [filters, dispatch] = useReducer(reducer, INITIAL);
  const { page, workflow, sort } = filters;
  const setFilter = (key, value) => dispatch({ type: "SET_FILTER", key, value });

  // Families for the family filter (background; never blocks the list).
  const [families, setFamilies] = useState([]);
  useEffect(() => {
    api
      .get("/api/admin/exam-intelligence-cms/exam-families?is_active=true&limit=200")
      .then((d) => setFamilies(d?.items || []))
      .catch(() => {});
  }, []);

  // ── List state (workflow + sort + paging go here) ──
  const [list, setList] = useState({
    items: [], count: 0, total_count: 0, has_next: false, offset: 0,
  });
  const [listStatus, setListStatus] = useState("idle"); // idle|loading|data|empty|error
  const [listError, setListError] = useState("");
  const listSeq = useRef(0);

  const loadList = useCallback(async (f) => {
    const qs = baseParams(f);
    qs.set("limit", String(PAGE_SIZE));
    qs.set("offset", String(f.page * PAGE_SIZE));
    if (f.workflow) qs.set("workflow", f.workflow);
    if (f.sort) qs.set("sort", f.sort);
    const seq = ++listSeq.current;
    setListStatus("loading");
    setListError("");
    try {
      const d = await api.get(`/api/admin/exam-intelligence/console/exams?${qs}`);
      if (seq !== listSeq.current) return;
      const items = d?.items || [];
      setList({
        items,
        count: d?.count ?? items.length,
        total_count: d?.total_count ?? items.length,
        has_next: d?.has_next ?? false,
        offset: d?.offset ?? 0,
      });
      setListStatus(items.length ? "data" : "empty");
    } catch (e) {
      if (seq !== listSeq.current) return;
      setListError(e?.message || "Could not load the work queue");
      setListStatus("error");
    }
  }, []);

  useEffect(() => {
    loadList(filters);
  }, [filters, loadList]);

  // ── Summary state (base filters ONLY; never workflow/sort/page) ──
  const [summary, setSummary] = useState(null);
  const [summaryStatus, setSummaryStatus] = useState("idle"); // idle|loading|data|error
  const summarySeq = useRef(0);

  // Stable key over base filters only, so workflow/sort/page changes do not
  // refetch the summary (counts must stay at the base-filtered scope).
  // Intentionally keyed on BASE filters only — workflow/sort/page must not
  // trigger a summary refetch (counts stay at the base-filtered scope).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const baseKey = useMemo(() => baseParams(filters).toString(), [
    filters.search, filters.examType, filters.activeState,
    filters.managementMode, filters.cadence, filters.examFamilyId,
  ]);

  const loadSummary = useCallback(async (key) => {
    const seq = ++summarySeq.current;
    setSummaryStatus("loading");
    try {
      const d = await api.get(`/api/admin/exam-intelligence/console/summary${key ? `?${key}` : ""}`);
      if (seq !== summarySeq.current) return;
      setSummary(d);
      setSummaryStatus("data");
    } catch {
      if (seq !== summarySeq.current) return;
      setSummary(null);
      setSummaryStatus("error");
    }
  }, []);

  useEffect(() => {
    loadSummary(baseKey);
  }, [baseKey, loadSummary]);

  const hasPrev = page > 0;
  const rangeStart = list.total_count === 0 ? 0 : list.offset + 1;
  const rangeEnd = Math.max(rangeStart, list.offset + list.items.length);

  return (
    <div className="oc-main" style={{ padding: 22 }} data-testid="console-work-queue">
      <div className="lbl" style={{ marginBottom: 4 }}>Exam Governance Console</div>
      <h1 className="oc-title disp" style={{ fontSize: 24, marginBottom: 4 }}>Work queue</h1>
      <p className="anno" style={{ marginBottom: 12 }}>
        Select an exam to manage its blockers, activation checks, and action queue.
      </p>

      {/* ── Summary strip: base-scoped counts that double as workflow chips ── */}
      <div
        className="row"
        style={{ flexWrap: "wrap", gap: 8, marginBottom: 12 }}
        role="group"
        aria-label="Work-queue summary filters"
        data-testid="console-summary-strip"
      >
        {SUMMARY_CHIPS.map((chip) => {
          const active = workflow === chip.value;
          const count = summaryStatus === "data" ? summary?.[chip.countKey] : null;
          return (
            <button
              key={chip.value || "all"}
              type="button"
              className="btn ghost filter-chip"
              aria-pressed={active}
              onClick={() => setFilter("workflow", chip.value)}
              data-testid={`console-chip-${chip.value || "all"}`}
            >
              {chip.label}
              {count != null ? <span className="mono" style={{ marginLeft: 6 }}>{count}</span> : null}
            </button>
          );
        })}
        {summaryStatus === "error" ? (
          <span className="anno" data-testid="console-summary-error">
            Summary unavailable.{" "}
            <button type="button" className="btn btn-ghost" onClick={() => loadSummary(baseKey)}
                    data-testid="console-summary-retry">Retry</button>
          </span>
        ) : null}
      </div>

      {/* ── Base filters ── */}
      <div className="row" style={{ flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
        <input
          type="search" className="input" style={{ width: 200 }}
          placeholder="Search name or key…" value={filters.search}
          onChange={(e) => setFilter("search", e.target.value)}
          data-testid="console-search" aria-label="Search exams"
        />
        <select className="select" value={filters.examType}
                onChange={(e) => setFilter("examType", e.target.value)}
                data-testid="console-filter-type" aria-label="Filter by exam purpose">
          <option value="">All purposes</option>
          {Object.entries(EXAM_PURPOSE_LABELS).map(([k, { label }]) => (
            <option key={k} value={k}>{label}</option>
          ))}
        </select>
        <select className="select" value={filters.activeState}
                onChange={(e) => setFilter("activeState", e.target.value)}
                data-testid="console-filter-active" aria-label="Filter by active status">
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="all">All</option>
        </select>
        {families.length > 0 && (
          <select className="select" value={filters.examFamilyId}
                  onChange={(e) => setFilter("examFamilyId", e.target.value)}
                  data-testid="console-filter-family" aria-label="Filter by exam family">
            <option value="">All families</option>
            {families.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
          </select>
        )}
        <select className="select" value={filters.managementMode}
                onChange={(e) => setFilter("managementMode", e.target.value)}
                data-testid="console-filter-lane" aria-label="Filter by management lane">
          <option value="">All (non-archive)</option>
          {Object.entries(BUSINESS_PRIORITY_LABELS).filter(([k]) => k !== "null")
            .map(([k, { label }]) => <option key={k} value={k}>{label}</option>)}
          <option value="__null__">{BUSINESS_PRIORITY_LABELS.null.label}</option>
        </select>
        <select className="select" value={filters.cadence}
                onChange={(e) => setFilter("cadence", e.target.value)}
                data-testid="console-filter-cadence" aria-label="Filter by cadence">
          <option value="">All cadences</option>
          {Object.entries(CADENCE_LABELS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
        </select>
      </div>

      {/* ── Workflow controls (uncounted) + sort ── */}
      <div className="row" style={{ flexWrap: "wrap", gap: 8, marginBottom: 12, alignItems: "center" }}>
        <span className="lbl">Workflow:</span>
        {UNCOUNTED_WORKFLOWS.map((w) => {
          const active = workflow === w.value;
          return (
            <button key={w.value} type="button"
                    className="btn ghost filter-chip"
                    aria-pressed={active}
                    onClick={() => setFilter("workflow", w.value)}
                    data-testid={`console-chip-${w.value}`}>
              {w.label}
            </button>
          );
        })}
        <label className="lbl" htmlFor="console-sort" style={{ marginLeft: "auto" }}>Sort</label>
        <select id="console-sort" className="select" value={sort}
                onChange={(e) => setFilter("sort", e.target.value)}
                data-testid="console-sort" aria-label="Sort work queue">
          {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      {/* ── List states ── */}
      {listStatus === "loading" && (
        <div className="row-sub" data-testid="console-loading">Loading work queue…</div>
      )}

      {listStatus === "error" && (
        <div className="err-row" data-testid="console-error">
          {listError || "Could not load the work queue."}{" "}
          <button className="btn" onClick={() => loadList(filters)} data-testid="console-retry">Retry</button>
        </div>
      )}

      {listStatus === "empty" && (
        <div className="empty" data-testid="console-empty">
          <div className="empty-title">No exams match the selected search, filters or workflow.</div>
          <div className="row" style={{ gap: 8, justifyContent: "center", marginTop: 8 }}>
            {workflow ? (
              <button type="button" className="btn" onClick={() => dispatch({ type: "CLEAR_WORKFLOW" })}
                      data-testid="console-empty-clear-workflow">Clear workflow</button>
            ) : null}
            {!isDefaultFilters(filters) || workflow ? (
              <button type="button" className="btn btn-ghost" onClick={() => dispatch({ type: "RESET" })}
                      data-testid="console-empty-clear-all">Clear all filters</button>
            ) : null}
          </div>
        </div>
      )}

      {listStatus === "data" && (
        <div className="card" style={{ overflow: "hidden" }}>
          <table className="tbl" style={{ width: "100%" }} data-testid="console-table">
            <thead>
              <tr>
                <th>Exam</th>
                <th>Organization</th>
                <th>Purpose / lane</th>
                <th>Status</th>
                <th>Blocking issue</th>
                <th>Locked coverage</th>
                <th title="Verified = verified paper + verified question + verified topic tag">PYQ (verified / total)</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {list.items.map((e) => {
                const meta = STATUS_META[e.status] || { tone: "pill-dusk", label: humanizeToken(e.status) };
                return (
                  <tr key={e.id} data-testid={`console-row-${e.id}`}>
                    <td>
                      <div className="row-ttl">{e.name ?? e.slug ?? e.id}</div>
                      {e.slug ? <div className="mono anno">{e.slug}</div> : null}
                    </td>
                    <td className="anno" data-testid={`console-org-${e.id}`}>{e.organization_name || "—"}</td>
                    <td className="anno">
                      {EXAM_PURPOSE_LABELS[e.exam_type]?.label ?? (humanizeToken(e.exam_type) || "—")}
                      <div><span className="badge neutral no-dot">{laneLabel(e.management_mode)}</span>
                        {e.cadence ? <span className="anno" style={{ marginLeft: 6 }}>{CADENCE_LABELS[e.cadence] ?? humanizeToken(e.cadence)}</span> : null}
                      </div>
                    </td>
                    <td data-testid={`console-status-${e.id}`}>
                      <StatusBadge tone={meta.tone} label={meta.label} status={e.status} />
                      {Array.isArray(e.flags) && e.flags.length ? (
                        <div className="row" style={{ flexWrap: "wrap", gap: 4, marginTop: 4 }}>
                          {e.flags.map((fl) => (
                            <span key={fl} className="pill pill-outline" data-testid={`console-flag-${e.id}-${fl}`}>
                              {FLAG_LABELS[fl] ?? humanizeToken(fl)}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </td>
                    <td data-testid={`console-blocker-${e.id}`}>
                      {e.first_blocker_text ? (
                        <>
                          <span>{e.first_blocker_text}</span>
                          {e.blocker_count > 1 ? (
                            <span className="anno" style={{ marginLeft: 6 }}>(+{e.blocker_count - 1} more)</span>
                          ) : null}
                        </>
                      ) : (
                        <span className="anno">No hard blocker</span>
                      )}
                    </td>
                    <td className="mono" data-testid={`console-coverage-${e.id}`}>
                      {e.locked_coverage_count ?? 0}
                      <span className="anno"> locked</span>
                    </td>
                    <td className="mono" data-testid={`console-pyq-${e.id}`}
                        title="Verified = verified paper + verified question + verified topic tag">
                      {e.verified_pyq_count ?? 0}
                      <span className="anno"> / {e.total_pyq_count ?? 0}</span>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <Link to={`/admin/exam-intelligence/exams/${encodeURIComponent(e.id)}`}
                            className="btn" data-testid={`console-manage-${e.id}`}>Manage exam</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className="row" style={{ justifyContent: "space-between", alignItems: "center", padding: "8px 12px", borderTop: "1px solid var(--rule)" }}
               data-testid="console-pagination">
            <span className="anno" data-testid="console-range">
              {list.total_count === 0 ? "No results" : `${rangeStart}–${rangeEnd} of ${list.total_count}`}
            </span>
            <span className="row" style={{ gap: 8 }}>
              <button type="button" className="btn btn-ghost" disabled={!hasPrev}
                      onClick={() => dispatch({ type: "SET_PAGE", page: page - 1 })}
                      data-testid="console-prev" aria-label="Previous page">← Prev</button>
              <button type="button" className="btn btn-ghost" disabled={!list.has_next}
                      onClick={() => dispatch({ type: "SET_PAGE", page: page + 1 })}
                      data-testid="console-next" aria-label="Next page">Next →</button>
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
