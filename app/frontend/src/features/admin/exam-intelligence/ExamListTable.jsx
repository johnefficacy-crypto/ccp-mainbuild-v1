import React from "react";
import { Link } from "react-router-dom";
import { ChevronDown, ChevronRight } from "lucide-react";
import { StatusBadge } from "../../../shared/ui/core";
import { humanizeToken } from "./operatorChrome";
import {
  BUSINESS_PRIORITY_LABELS,
  CADENCE_LABELS,
  EXAM_PURPOSE_LABELS,
  REVIEWER_STATUS_PLANNER_NOTE,
} from "./ExamIntelGlossary";

function examKey(exam) {
  return exam?.id ?? exam?.slug ?? exam?.name ?? "unnamed-exam";
}

function examDisplayName(exam) {
  return exam?.name || exam?.slug || "Unnamed exam";
}

function safeDomId(value) {
  return String(value || "exam")
    .replace(/[^A-Za-z0-9_-]/g, "-")
    .replace(/^-+/, "exam-");
}

function examDomHandle(exam, index) {
  if (exam?.slug) return safeDomId(exam.slug);
  if (exam?.name) return safeDomId(exam.name);
  return `row-${index}`;
}

function formatCount(value) {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n : 0;
}

function formatSyllabusSummary(exam) {
  const verified = formatCount(exam?.syllabus_verified);
  const pending = formatCount(exam?.syllabus_pending);
  const parts = [];
  if (verified) parts.push(`${verified} verified`);
  if (pending) parts.push(`${pending} pending`);
  return parts.length ? parts.join(" · ") : "No syllabus review";
}

function formatTopicCoverage(exam) {
  const reviewedOrLocked = formatCount(exam?.verified_topic_count);
  const total = formatCount(exam?.coverage_total);
  if (!total) return "No topic coverage";
  return `${reviewedOrLocked} of ${total} reviewed or locked`;
}

function readinessLabel(level) {
  if (level === "ready") return "ready";
  if (level === "partial") return "partial";
  if (level === "not_ready") return "not ready";
  if (!level) return "not ready";
  return humanizeToken(level) || "not ready";
}

const READINESS_STATUS = {
  ready: "ready",
  partial: "partial",
  not_ready: "missing",
};


export default function ExamListTable({
  items,
  page = 0,
  pageSize = 25,
  total_count = 0,
  has_next = false,
  offset = 0,
  onPageChange,
}) {
  const rows = React.useMemo(() => (Array.isArray(items) ? items : []), [items]);
  const [expandedKeys, setExpandedKeys] = React.useState(() => new Set());

  React.useEffect(() => {
    const present = new Set(rows.map(examKey));
    setExpandedKeys((current) => {
      let changed = false;
      const next = new Set();
      current.forEach((key) => {
        if (present.has(key)) next.add(key);
        else changed = true;
      });
      return changed ? next : current;
    });
  }, [rows]);

  const toggleExpanded = React.useCallback((key) => {
    setExpandedKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const hasPrev = page > 0;
  const rangeStart = total_count === 0 ? 0 : offset + 1;
  const rangeEnd = Math.max(rangeStart, offset + rows.length);

  if (!rows.length && page === 0) {
    return (
      <div className="soft-card grain relative overflow-hidden rounded-[18px] p-5 text-sm text-clay-700">
        No exams registered yet.
      </div>
    );
  }

  return (
    <div className="soft-card grain relative overflow-hidden rounded-[18px]">
      <table className="tbl" data-testid="exam-intel-exam-table">
        <thead>
          <tr>
            <th>Exam</th>
            <th>Purpose</th>
            <th>Syllabus</th>
            <th title={REVIEWER_STATUS_PLANNER_NOTE}>Topic coverage</th>
            <th>Readiness</th>
            <th className="right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((e, index) => {
            const key = examKey(e);
            const displayName = examDisplayName(e);
            const domHandle = examDomHandle(e, index);
            const detailId = `exam-intel-details-${domHandle}`;
            const isExpanded = expandedKeys.has(key);
            const lane = e.management_mode == null
              ? BUSINESS_PRIORITY_LABELS.null
              : (BUSINESS_PRIORITY_LABELS[e.management_mode] ?? BUSINESS_PRIORITY_LABELS.null);
            const cadence = CADENCE_LABELS[e.cadence] ?? "Unknown";
            const Icon = isExpanded ? ChevronDown : ChevronRight;
            return (
              <React.Fragment key={key}>
                <tr>
                  <td>
                    <div className="flex items-start gap-2">
                      <button
                        type="button"
                        className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[#D9C7A7] text-clay-700 hover:bg-[#F3EADB] focus:outline-none focus:ring-2 focus:ring-indigo-300"
                        aria-label={`${isExpanded ? "Hide" : "Show"} details for ${displayName}`}
                        aria-expanded={isExpanded}
                        aria-controls={detailId}
                        onClick={() => toggleExpanded(key)}
                        data-testid={`exam-intel-disclosure-${domHandle}`}
                      >
                        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                      <div>
                        <div className="font-semibold text-clay-900">{displayName}</div>
                        {e.slug ? (
                          <div className="num-mono text-xs text-clay-600">{e.slug}</div>
                        ) : null}
                      </div>
                    </div>
                  </td>
                  <td className="text-clay-700">
                    {EXAM_PURPOSE_LABELS[e.exam_type]?.label ?? (humanizeToken(e.exam_type) || "—")}
                  </td>
                  <td className="text-clay-700">{formatSyllabusSummary(e)}</td>
                  <td className="text-clay-700" title={REVIEWER_STATUS_PLANNER_NOTE}>
                    {formatTopicCoverage(e)}
                  </td>
                  <td>
                    <StatusBadge
                      status={READINESS_STATUS[e.readiness_level] || "missing"}
                      label={readinessLabel(e.readiness_level)}
                    />
                  </td>
                  <td className="right">
                    <div className="inline-flex items-center justify-end gap-2">
                      <Link
                        to={`/admin/exam-intelligence/console/${e.id}`}
                        className="text-[11px] px-3 py-1 rounded-full border border-indigo-300 text-indigo-700 font-semibold hover:bg-indigo-50"
                        data-testid={`exam-intel-console-${e.slug}`}
                      >
                        Open console
                      </Link>
                      <Link
                        to={`/admin/exam-intelligence/workspace/${e.id}`}
                        className="text-[11px] px-2 py-1 rounded-full text-clay-600 hover:text-clay-900 hover:underline underline-offset-2"
                        data-testid={`exam-intel-workspace-${e.slug}`}
                      >
                        Advanced workspace
                      </Link>
                    </div>
                  </td>
                </tr>
                {isExpanded ? (
                  <tr id={detailId} data-testid={`exam-intel-details-${domHandle}`}>
                    <td colSpan={6} className="bg-[#FFFDF9] px-5 py-4 text-sm text-clay-700">
                      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        <div><dt className="font-semibold text-clay-900">Exam key</dt><dd className="num-mono text-xs">{e.slug || "—"}</dd></div>
                        <div><dt className="font-semibold text-clay-900">Management lane</dt><dd>{lane.label}</dd></div>
                        {lane.helper ? <div><dt className="font-semibold text-clay-900">Lane guidance</dt><dd>{lane.helper}</dd></div> : null}
                        <div><dt className="font-semibold text-clay-900">Cadence</dt><dd>{cadence}</dd></div>
                        <div><dt className="font-semibold text-clay-900">Visibility</dt><dd>{e.is_active ? "Active" : "Inactive"}</dd></div>
                        <div><dt className="font-semibold text-clay-900">Syllabus verified count</dt><dd>{formatCount(e.syllabus_verified)}</dd></div>
                        <div><dt className="font-semibold text-clay-900">Syllabus pending count</dt><dd>{formatCount(e.syllabus_pending)}</dd></div>
                        <div><dt className="font-semibold text-clay-900">Reviewed or locked topic count</dt><dd>{formatCount(e.verified_topic_count)}</dd></div>
                        <div><dt className="font-semibold text-clay-900">Total topic coverage count</dt><dd>{formatCount(e.coverage_total)}</dd></div>
                        <div><dt className="font-semibold text-clay-900">High-yield topics</dt><dd>{formatCount(e.high_yield_topic_count)}</dd></div>
                        <div className="sm:col-span-2 lg:col-span-3"><dt className="font-semibold text-clay-900">Planner note</dt><dd>{REVIEWER_STATUS_PLANNER_NOTE}</dd></div>
                      </dl>
                    </td>
                  </tr>
                ) : null}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>

      <div
        className="flex items-center justify-between px-4 py-2 border-t border-[#E7DECB] text-xs text-clay-700"
        data-testid="exam-intel-pagination"
      >
        <span data-testid="exam-intel-range">
          {total_count === 0
            ? "No results"
            : `${rangeStart}–${rangeEnd} of ${total_count}`}
        </span>
        <span className="flex gap-2">
          <button
            type="button"
            disabled={!hasPrev}
            onClick={() => onPageChange?.(page - 1)}
            className="btn btn-ghost text-xs disabled:opacity-40"
            data-testid="exam-intel-prev"
            aria-label="Previous page"
          >
            ← Prev
          </button>
          <button
            type="button"
            disabled={!has_next}
            onClick={() => onPageChange?.(page + 1)}
            className="btn btn-ghost text-xs disabled:opacity-40"
            data-testid="exam-intel-next"
            aria-label="Next page"
          >
            Next →
          </button>
        </span>
      </div>
    </div>
  );
}
