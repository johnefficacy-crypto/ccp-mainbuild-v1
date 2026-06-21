import React, { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { GraduationCap } from "lucide-react";
import { api } from "../../lib/api";
import {
  BUSINESS_PRIORITY_LABELS,
  CADENCE_LABELS,
  EXAM_PURPOSE_LABELS,
  getBusinessPriorityLabel,
} from "../../features/admin/exam-intelligence/ExamIntelGlossary";
import { AdminSafetyBanner } from "../../shared/ui/core";
import { PageHeader, StatusDot } from "../../shared/ui/studyos";

const PAGE_SIZE = 25;

const INITIAL_FILTERS = {
  search: "",
  examType: "",
  activeState: "active",
  familyId: "",
  managementMode: "",
  cadence: "",
  workflow: "",
  sort: "blockers_first",
};

function filtersReducer(state, action) {
  switch (action.type) {
    case "SET_FILTER":
      return { ...state, [action.key]: action.value };
    default:
      return state;
  }
}

function buildParams(filters, offset) {
  const p = { limit: String(PAGE_SIZE), offset: String(offset) };
  if (filters.search.trim()) p.q = filters.search.trim();
  if (filters.examType) p.exam_type = filters.examType;
  if (filters.activeState) p.active_state = filters.activeState;
  if (filters.familyId) p.exam_family_id = filters.familyId;
  if (filters.managementMode) p.management_mode = filters.managementMode;
  if (filters.cadence) p.cadence = filters.cadence;
  if (filters.workflow) p.workflow = filters.workflow;
  if (filters.sort) p.sort = filters.sort;
  return p;
}

const STATUS_META = {
  ready:        { label: "Ready",        cls: "bg-green-50 text-green-700" },
  needs_action: { label: "Needs action", cls: "bg-amber-50 text-amber-700" },
  blocked:      { label: "Blocked",      cls: "bg-red-50 text-red-700" },
};

function StatusChip({ status }) {
  const meta = STATUS_META[status];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        meta ? meta.cls : "bg-gray-100 text-gray-600"
      }`}
    >
      {meta ? meta.label : (status ?? "—")}
    </span>
  );
}

const WORKFLOW_OPTIONS = [
  { value: "",                   label: "All workflows" },
  { value: "blocked",            label: "Blocked" },
  { value: "needs_action",       label: "Needs action" },
  { value: "ready",              label: "Ready" },
  { value: "pending_review",     label: "Pending review" },
  { value: "stale_review_queue", label: "Stale review queue" },
  { value: "missing_pyq",        label: "Missing PYQ" },
  { value: "missing_coverage",   label: "Missing coverage" },
];

const SORT_OPTIONS = [
  { value: "blockers_first",   label: "Blockers first" },
  { value: "management_lane",  label: "Management lane" },
  { value: "name",             label: "Name A–Z" },
];

function MoreMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="btn btn-ghost text-xs"
        data-testid="exam-mgmt-more-trigger"
      >
        More
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-1 min-w-[10rem] rounded-md bg-white py-1 shadow-lg ring-1 ring-black/5"
          data-testid="exam-mgmt-more-menu"
        >
          <Link
            to="/admin/exam-intelligence/new"
            role="menuitem"
            className="block px-4 py-2 text-sm hover:bg-gray-50"
            data-testid="exam-mgmt-create-exam"
            onClick={() => setOpen(false)}
          >
            Create exam
          </Link>
        </div>
      )}
    </div>
  );
}

function ReadinessDots({ r }) {
  if (!r) return <span className="text-muted-foreground">—</span>;
  return (
    <>
      <span className={r.setup === "ready" ? "text-green-600" : "text-amber-600"}>S</span>
      <span className={r.topic_coverage === "ready" ? "text-green-600" : "text-amber-600"}>T</span>
      <span className={r.pyq === "ready" ? "text-green-600" : "text-amber-600"}>P</span>
      {(r.pending_review_count ?? 0) > 0 && (
        <span className="ml-1 text-amber-600">+{r.pending_review_count}⌛</span>
      )}
    </>
  );
}

function ExamRow({ item }) {
  const cycle = item.current_cycle;
  return (
    <tr
      className="border-b last:border-0 align-top"
      data-testid={`exam-mgmt-row-${item.slug}`}
    >
      <td className="py-2 pr-3">
        <StatusChip status={item.status} />
        {item.blocker_count > 0 && (
          <span
            className="ml-1 text-xs text-red-600"
            data-testid={`exam-mgmt-blockers-${item.slug}`}
          >
            ×{item.blocker_count}
          </span>
        )}
      </td>
      <td className="py-2 pr-3">
        <span className="font-medium" data-testid={`exam-mgmt-name-${item.slug}`}>
          {item.name}
        </span>
        {item.family_name && (
          <div
            className="text-xs text-muted-foreground"
            data-testid={`exam-mgmt-family-${item.slug}`}
          >
            {item.family_name}
          </div>
        )}
      </td>
      <td
        className="py-2 pr-3 text-xs text-muted-foreground"
        data-testid={`exam-mgmt-org-${item.slug}`}
      >
        {item.organization_name ?? "—"}
      </td>
      <td className="py-2 pr-3 text-xs text-muted-foreground">
        <div data-testid={`exam-mgmt-mode-${item.slug}`}>
          {getBusinessPriorityLabel(item.management_mode)}
        </div>
        <div data-testid={`exam-mgmt-cadence-${item.slug}`}>
          {CADENCE_LABELS[item.cadence] ?? item.cadence ?? "—"}
        </div>
      </td>
      <td
        className="py-2 pr-3 text-xs"
        data-testid={`exam-mgmt-active-${item.slug}`}
      >
        {item.is_active ? "Active" : "Inactive"}
      </td>
      <td
        className="py-2 pr-3 text-xs text-muted-foreground"
        data-testid={`exam-mgmt-cycle-${item.slug}`}
      >
        {cycle ? (
          <>
            <div className="font-medium text-foreground">
              {[cycle.name, cycle.year].filter(Boolean).join(" ")}
              {cycle.status && (
                <span className="ml-1 font-normal text-muted-foreground">
                  ({cycle.status})
                </span>
              )}
            </div>
            {(cycle.phases ?? []).map((ph) => (
              <div key={ph.id} className="mt-0.5" data-testid={`exam-mgmt-phase-${ph.id}`}>
                <span>{ph.label}</span>
                {ph.status && <span className="ml-1">({ph.status})</span>}
                {(ph.start_date || ph.end_date) && (
                  <span className="ml-1 text-muted-foreground">
                    {ph.start_date ?? "?"} – {ph.end_date ?? "?"}
                  </span>
                )}
              </div>
            ))}
          </>
        ) : (
          "—"
        )}
      </td>
      <td className="py-2 pr-3 text-xs text-muted-foreground max-w-xs truncate">
        {item.first_blocker_text ?? ""}
      </td>
      <td className="py-2 pr-3 text-xs" data-testid={`exam-mgmt-readiness-${item.slug}`}>
        <ReadinessDots r={item.readiness_summary} />
      </td>
      <td className="py-2 text-right">
        <Link
          to={`/admin/exam-intelligence/exams/${item.id}`}
          className="btn btn-ghost text-xs"
          data-testid={`exam-mgmt-manage-${item.slug}`}
        >
          Manage exam
        </Link>
      </td>
    </tr>
  );
}

export default function AdminExamIntelligence() {
  const [filters, dispatch] = useReducer(filtersReducer, INITIAL_FILTERS);
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState("loading");
  const [data, setData] = useState({
    items: [],
    totalCount: 0,
    familyOptions: [],
    hasNext: false,
    offset: 0,
  });
  const seqRef = useRef(0);

  const fetchPage = useCallback(async (currentFilters, currentOffset) => {
    const seq = ++seqRef.current;
    setStatus("loading");
    try {
      const params = buildParams(currentFilters, currentOffset);
      const qs = new URLSearchParams(params).toString();
      const res = await api.get(
        `/api/admin/exam-intelligence/management/exams?${qs}`,
      );
      if (seq !== seqRef.current) return;
      if (!res || !Array.isArray(res.items)) {
        setStatus("error");
        return;
      }
      setData({
        items: res.items,
        totalCount: res.total_count ?? 0,
        familyOptions: res.family_options ?? [],
        hasNext: res.has_next ?? false,
        offset: currentOffset,
      });
      setStatus(res.items.length === 0 ? "empty" : "live");
    } catch {
      if (seq !== seqRef.current) return;
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    fetchPage(filters, offset);
  }, [fetchPage, filters, offset]);

  function setFilter(key, value) {
    dispatch({ type: "SET_FILTER", key, value });
    setOffset(0);
  }

  const hasPrev = data.offset > 0;
  const rangeStart = data.totalCount === 0 ? 0 : data.offset + 1;
  const rangeEnd = data.offset + data.items.length;

  return (
    <div className="space-y-6" data-testid="admin-exam-intelligence-page">
      <PageHeader
        eyebrow={
          <span className="inline-flex items-center gap-2">
            <GraduationCap className="h-3.5 w-3.5" /> Exam intelligence · internal
          </span>
        }
        title="Exam Management"
        sub="Review status, cycle health, and coverage readiness for every active exam."
        right={
          <span className="inline-flex items-center gap-2 flex-wrap justify-end">
            <StatusDot state="live" label="Live" />
            <MoreMenu />
          </span>
        }
      />

      <AdminSafetyBanner
        title="Lifecycle-gated contract"
        testId="admin-exam-intel-safety"
        tone="clay"
        collapsible
        defaultOpen={false}
      >
        User-facing exam intelligence reads only rows at the right lifecycle
        stage:{" "}
        <span className="font-mono">reviewed</span> or{" "}
        <span className="font-mono">locked</span> for coverage rows;{" "}
        <span className="font-mono">verified</span> for PYQ questions.
        Pending and rejected rows never reach the aspirant. No AI is used to
        generate, interpret, or auto-approve these rows.
      </AdminSafetyBanner>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="search"
            placeholder="Search name or slug…"
            value={filters.search}
            onChange={(e) => setFilter("search", e.target.value)}
            className="input input-sm w-48"
            data-testid="exam-intel-search"
            aria-label="Search exams"
          />
          <select
            value={filters.examType}
            onChange={(e) => setFilter("examType", e.target.value)}
            className="select select-sm w-44"
            data-testid="exam-intel-type-filter"
            aria-label="Filter by exam purpose"
          >
            <option value="">All purposes</option>
            {Object.entries(EXAM_PURPOSE_LABELS).map(([k, { label }]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
          <select
            value={filters.activeState}
            onChange={(e) => setFilter("activeState", e.target.value)}
            className="select select-sm w-28"
            data-testid="exam-intel-active-filter"
            aria-label="Filter by active status"
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="all">All</option>
          </select>
          <select
            value={filters.familyId}
            onChange={(e) => setFilter("familyId", e.target.value)}
            className="select select-sm w-44"
            data-testid="exam-intel-family-filter"
            aria-label="Filter by exam family"
          >
            <option value="">All families</option>
            {data.familyOptions.map((f) => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>
          <select
            value={filters.managementMode}
            onChange={(e) => setFilter("managementMode", e.target.value)}
            className="select select-sm w-44"
            data-testid="exam-intel-lane-filter"
            aria-label="Filter by business priority"
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
            value={filters.cadence}
            onChange={(e) => setFilter("cadence", e.target.value)}
            className="select select-sm w-36"
            data-testid="exam-intel-cadence-filter"
            aria-label="Filter by cadence"
          >
            <option value="">All cadences</option>
            {Object.entries(CADENCE_LABELS).map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
          <select
            value={filters.workflow}
            onChange={(e) => setFilter("workflow", e.target.value)}
            className="select select-sm w-44"
            data-testid="exam-intel-workflow-filter"
            aria-label="Filter by workflow status"
          >
            {WORKFLOW_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <select
            value={filters.sort}
            onChange={(e) => setFilter("sort", e.target.value)}
            className="select select-sm w-44"
            data-testid="exam-intel-sort"
            aria-label="Sort exams"
          >
            {SORT_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {status === "error" && (
          <div
            className="rounded-xl bg-dusk-50 text-dusk-800 text-xs px-3 py-2"
            data-testid="exam-intel-error"
          >
            Could not load exams
          </div>
        )}

        {status === "loading" && (
          <div
            className="text-xs text-muted-foreground py-4"
            data-testid="exam-intel-loading"
          >
            Loading…
          </div>
        )}

        {(status === "live" || status === "empty") && (
          <div data-testid="exam-mgmt-table">
            <div className="flex items-center justify-between mb-2">
              <p
                className="text-xs text-muted-foreground"
                data-testid="exam-intel-count-label"
              >
                {data.totalCount === 0
                  ? "No exams"
                  : `${rangeStart}–${rangeEnd} of ${data.totalCount} exam${data.totalCount === 1 ? "" : "s"}`}
              </p>
              <div className="flex gap-1">
                <button
                  type="button"
                  disabled={!hasPrev}
                  onClick={() => setOffset(Math.max(0, data.offset - PAGE_SIZE))}
                  className="btn btn-ghost text-xs"
                  data-testid="exam-intel-prev"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={!data.hasNext}
                  onClick={() => setOffset(data.offset + PAGE_SIZE)}
                  className="btn btn-ghost text-xs"
                  data-testid="exam-intel-next"
                >
                  Next
                </button>
              </div>
            </div>

            {data.items.length === 0 ? (
              <p className="text-xs text-muted-foreground py-6 text-center">
                No exams match your filters.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-muted-foreground">
                    <th className="text-left py-2 pr-3 font-medium">Status</th>
                    <th className="text-left py-2 pr-3 font-medium">Exam / Family</th>
                    <th className="text-left py-2 pr-3 font-medium">Organisation</th>
                    <th className="text-left py-2 pr-3 font-medium">Lane / Cadence</th>
                    <th className="text-left py-2 pr-3 font-medium">Active</th>
                    <th className="text-left py-2 pr-3 font-medium">Current cycle</th>
                    <th className="text-left py-2 pr-3 font-medium">First blocker</th>
                    <th className="text-left py-2 pr-3 font-medium">Readiness</th>
                    <th className="py-2" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <ExamRow key={item.id} item={item} />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
