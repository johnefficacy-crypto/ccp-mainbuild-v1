import React from "react";
import { Link } from "react-router-dom";
import { StatusBadge } from "../../../shared/ui/core";

const READINESS_STATUS = {
  ready: "ready",
  partial: "partial",
  not_ready: "missing",
};

export default function ExamListTable({ items, onSelect }) {
  const rows = Array.isArray(items) ? items : [];
  if (!rows.length) {
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
            <th>Slug</th>
            <th>Name</th>
            <th>Type</th>
            <th className="right">Syllabus ✓</th>
            <th className="right">Syllabus ⏳</th>
            <th className="right">Verified topics</th>
            <th className="right">High-yield</th>
            <th>Readiness</th>
            <th className="right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((e) => (
            <tr key={e.id}>
              <td className="num-mono">{e.slug}</td>
              <td>{e.name}</td>
              <td className="text-clay-700">{e.exam_type}</td>
              <td className="right num-mono text-sage-700">{e.syllabus_verified ?? 0}</td>
              <td className="right num-mono text-dusk-700">{e.syllabus_pending ?? 0}</td>
              <td className="right num-mono">
                {e.verified_topic_count ?? 0}
                <span className="text-clay-700"> / {e.coverage_total ?? 0}</span>
              </td>
              <td className="right num-mono">{e.high_yield_topic_count ?? 0}</td>
              <td>
                <StatusBadge
                  status={READINESS_STATUS[e.readiness_level] || "missing"}
                  label={(e.readiness_level || "not_ready").replaceAll("_", " ")}
                />
              </td>
              <td className="right">
                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => onSelect && onSelect(e)}
                    className="text-[11px] px-3 py-1 rounded-full bg-[#2E2218] text-[#F3EADB] font-semibold"
                    data-testid={`exam-intel-review-${e.slug}`}
                  >
                    Pending review →
                  </button>
                  <Link
                    to={`/admin/exam-intelligence/workspace/${e.id}`}
                    className="text-[11px] px-3 py-1 rounded-full border border-indigo-300 text-indigo-700 font-semibold hover:bg-indigo-50"
                    data-testid={`exam-intel-workspace-${e.slug}`}
                  >
                    Open workspace
                  </Link>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
