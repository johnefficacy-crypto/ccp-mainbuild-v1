import React from "react";
import { Link } from "react-router-dom";
import { StatusBadge } from "../../../shared/ui/core";
import {
  BUSINESS_PRIORITY_LABELS,
  BUSINESS_PRIORITY_LABELS as _BP,
  CADENCE_LABELS,
  EXAM_PURPOSE_LABELS,
  IS_ACTIVE_HELPER,
  REVIEWER_STATUS_PLANNER_NOTE,
} from "./ExamIntelGlossary";

const READINESS_STATUS = {
  ready: "ready",
  partial: "partial",
  not_ready: "missing",
};

function bpLabel(mode) {
  if (mode == null) return _BP.null.label;
  return (_BP[mode] ?? _BP.null).label;
}

function bpHelper(mode) {
  if (mode == null) return _BP.null.helper;
  return (_BP[mode] ?? _BP.null).helper;
}

export default function ExamListTable({
  items,
  page = 0,
  pageSize = 25,
  total_count = 0,
  has_next = false,
  offset = 0,
  onPageChange,
}) {
  const rows = Array.isArray(items) ? items : [];

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
            <th>Exam key</th>
            <th>Name</th>
            <th>Purpose</th>
            <th
              title={Object.values(BUSINESS_PRIORITY_LABELS)
                .filter((v) => v.helper)
                .map((v) => `${v.label}: ${v.helper}`)
                .join("\n")}
            >
              Business priority
            </th>
            <th>Cadence</th>
            <th className="right">Syllabus ✓</th>
            <th className="right">Syllabus ⏳</th>
            <th className="right">Planner-ready topics</th>
            <th className="right">Locked high-yield topics</th>
            <th title={REVIEWER_STATUS_PLANNER_NOTE}>User-facing readiness</th>
            <th className="right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((e) => (
            <tr key={e.id}>
              <td className="num-mono">{e.slug}</td>
              <td>{e.name}</td>
              <td className="text-clay-700">
                {EXAM_PURPOSE_LABELS[e.exam_type]?.label ?? e.exam_type}
              </td>
              <td
                className="text-clay-700"
                data-testid={`exam-intel-lane-${e.slug}`}
                title={bpHelper(e.management_mode) ?? undefined}
              >
                {bpLabel(e.management_mode)}
              </td>
              <td
                className="text-clay-700"
                data-testid={`exam-intel-cadence-${e.slug}`}
              >
                {CADENCE_LABELS[e.cadence] ?? "Unknown"}
              </td>
              <td className="right num-mono text-sage-700">{e.syllabus_verified ?? 0}</td>
              <td className="right num-mono text-dusk-700">{e.syllabus_pending ?? 0}</td>
              <td className="right num-mono">
                {e.verified_topic_count ?? 0}
                <span className="text-clay-700"> / {e.coverage_total ?? 0}</span>
              </td>
              <td className="right num-mono">{e.high_yield_topic_count ?? 0}</td>
              <td title={IS_ACTIVE_HELPER}>
                <StatusBadge
                  status={READINESS_STATUS[e.readiness_level] || "missing"}
                  label={(e.readiness_level || "not_ready").replaceAll("_", " ")}
                />
              </td>
              <td className="right">
                <Link
                  to={`/admin/exam-intelligence/workspace/${e.id}`}
                  className="text-[11px] px-3 py-1 rounded-full border border-indigo-300 text-indigo-700 font-semibold hover:bg-indigo-50"
                  data-testid={`exam-intel-workspace-${e.slug}`}
                >
                  Open workspace
                </Link>
              </td>
            </tr>
          ))}
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
