import React, { useReducer } from "react";
import { Link } from "react-router-dom";
import { GraduationCap } from "lucide-react";
import useApiCollection from "../../lib/hooks/useApiCollection";
import {
  BUSINESS_PRIORITY_LABELS,
  CADENCE_LABELS,
  EXAM_PURPOSE_LABELS,
} from "../../features/admin/exam-intelligence/ExamIntelGlossary";
import { AdminSafetyBanner } from "../../shared/ui/core";
import { PageHeader, StatusDot } from "../../shared/ui/studyos";

const INITIAL_FILTERS = {
  search: "",
  examType: "",
  activeState: "active",
  managementMode: "",
  cadence: "",
};

function filtersReducer(state, action) {
  switch (action.type) {
    case "SET_FILTER":
      return { ...state, [action.key]: action.value };
    default:
      return state;
  }
}

function buildParams(filters) {
  const p = { limit: "200" };
  if (filters.search.trim()) p.q = filters.search.trim();
  if (filters.examType) p.exam_type = filters.examType;
  if (filters.activeState) p.active_state = filters.activeState;
  if (filters.managementMode) p.management_mode = filters.managementMode;
  if (filters.cadence) p.cadence = filters.cadence;
  return p;
}

const STATUS_CHIP_CLASS = {
  ready: "bg-green-50 text-green-700",
  needs_action: "bg-amber-50 text-amber-700",
  blocked: "bg-red-50 text-red-700",
};

const STATUS_LABEL = {
  ready: "Ready",
  needs_action: "Needs action",
  blocked: "Blocked",
};

export default function AdminExamIntelligence() {
  const [filters, dispatch] = useReducer(filtersReducer, INITIAL_FILTERS);

  const { items, status, refresh } = useApiCollection(
    "/api/admin/exam-intelligence/management/exams",
    [],
    { params: buildParams(filters) },
  );

  const isLoading = status === "loading";

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
            <Link
              to="/admin/exam-intelligence/new"
              className="btn btn-ghost text-xs"
              data-testid="exam-mgmt-create-exam"
            >
              Create exam
            </Link>
            <StatusDot state="live" label="Live" />
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
            onChange={(e) =>
              dispatch({ type: "SET_FILTER", key: "search", value: e.target.value })
            }
            className="input input-sm w-48"
            data-testid="exam-intel-search"
            aria-label="Search exams"
          />
          <select
            value={filters.examType}
            onChange={(e) =>
              dispatch({ type: "SET_FILTER", key: "examType", value: e.target.value })
            }
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
            onChange={(e) =>
              dispatch({ type: "SET_FILTER", key: "activeState", value: e.target.value })
            }
            className="select select-sm w-28"
            data-testid="exam-intel-active-filter"
            aria-label="Filter by active status"
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="all">All</option>
          </select>
          <select
            value={filters.managementMode}
            onChange={(e) =>
              dispatch({ type: "SET_FILTER", key: "managementMode", value: e.target.value })
            }
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
            onChange={(e) =>
              dispatch({ type: "SET_FILTER", key: "cadence", value: e.target.value })
            }
            className="select select-sm w-36"
            data-testid="exam-intel-cadence-filter"
            aria-label="Filter by cadence"
          >
            <option value="">All cadences</option>
            {Object.entries(CADENCE_LABELS).map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
          <div className="ml-auto flex items-center gap-2">
            {status !== "loading" && (
              <p className="text-xs text-muted-foreground" data-testid="exam-intel-count-label">
                {items.length} exam{items.length === 1 ? "" : "s"}
              </p>
            )}
            <button
              type="button"
              onClick={refresh}
              className="btn btn-ghost text-xs"
              data-testid="exam-intel-refresh"
            >
              {isLoading ? "Loading…" : "Refresh"}
            </button>
          </div>
        </div>

        {status === "error" && (
          <div
            className="rounded-xl bg-dusk-50 text-dusk-800 text-xs px-3 py-2"
            data-testid="exam-intel-error"
          >
            Could not load exams
          </div>
        )}

        {isLoading && (
          <div className="text-xs text-muted-foreground py-4" data-testid="exam-intel-loading">
            Loading…
          </div>
        )}

        {(status === "live" || status === "empty") && (
          <div data-testid="exam-mgmt-table">
            {items.length === 0 ? (
              <p className="text-xs text-muted-foreground py-6 text-center">
                No exams match your filters.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-muted-foreground">
                    <th className="text-left py-2 pr-4 font-medium">Status</th>
                    <th className="text-left py-2 pr-4 font-medium">Exam</th>
                    <th className="text-left py-2 pr-4 font-medium">Current cycle</th>
                    <th className="text-left py-2 pr-4 font-medium">Note</th>
                    <th className="py-2" />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      className="border-b last:border-0"
                      data-testid={`exam-mgmt-row-${item.slug}`}
                    >
                      <td className="py-2 pr-4">
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CHIP_CLASS[item.status] ?? ""}`}
                        >
                          {STATUS_LABEL[item.status] ?? item.status}
                        </span>
                      </td>
                      <td className="py-2 pr-4">
                        <span className="font-medium">{item.name}</span>
                        {item.family_name && (
                          <span className="ml-1.5 text-xs text-muted-foreground">
                            {item.family_name}
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-4 text-xs text-muted-foreground">
                        {item.current_cycle
                          ? [item.current_cycle.name, item.current_cycle.year]
                              .filter(Boolean)
                              .join(" ")
                          : "—"}
                      </td>
                      <td className="py-2 pr-4 text-xs text-muted-foreground max-w-xs truncate">
                        {item.first_blocker_text ?? ""}
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
