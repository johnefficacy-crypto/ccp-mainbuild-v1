/**
 * ExamTaskRail — Wave 4.6C blocker-first task rail (console variant only).
 *
 * Reuse-only: reads the SAME readiness already held in ExamWorkspace context
 * (sections + topic_coverage snapshot) and drives the EXISTING active-panel
 * (tab) mechanism via onSelect. It owns no fetch and no parallel store.
 *
 * Eight ordered groups:
 *   Setup · Documents · Syllabus · PYQ · Topic coverage · Updates · Competition · Publish
 * Seven are readiness sections; "Topic coverage" is a derived read-only
 * snapshot from readiness.topic_coverage (NOT a readiness section — it has no
 * status/blockers and no dedicated panel), so it routes the operator to the
 * existing Overview snapshot (or Syllabus Mapper when empty).
 *
 * D-E: no readiness percentage is rendered anywhere here.
 */
import React from "react";

// Section-backed rows: readiness section key → existing tab id.
const RAIL_HEAD = [
  { id: "setup",       title: "Setup",       section: "setup",           tab: "setup" },
  { id: "documents",   title: "Documents",   section: "documents",       tab: "documents" },
  { id: "syllabus",    title: "Syllabus",    section: "syllabus_mapper", tab: "syllabus" },
  { id: "pyq",         title: "PYQ",         section: "pyq_workbench",   tab: "pyq" },
];
const RAIL_TAIL = [
  { id: "updates",     title: "Updates",     section: "updates",         tab: "updates" },
  { id: "competition", title: "Competition", section: "competition",     tab: "competition" },
  { id: "publish",     title: "Publish",     section: "review_activate", tab: "review" },
];

/**
 * Derived state for the topic-coverage snapshot row. Operator-confirmed
 * priority: locked > reviewed > needs-review. Reads only readiness.topic_coverage.
 */
export function deriveTopicCoverageRow(tc) {
  if (!tc || (tc.total ?? 0) === 0) {
    return {
      state: "not_started",
      label: "No coverage rows",
      blocker: "No planner-ready topic coverage exists yet.",
      targetTab: "syllabus",
    };
  }
  if ((tc.locked ?? 0) > 0) {
    return {
      state: "planner_ready",
      label: `${tc.locked} locked topic${tc.locked === 1 ? "" : "s"}`,
      blocker: null,
      targetTab: "overview",
    };
  }
  if ((tc.reviewed ?? 0) > 0) {
    return {
      state: "reviewed_not_locked",
      label: `${tc.reviewed} reviewed · lock preferred`,
      blocker: "Reviewed rows may be usable, but locked coverage is preferred.",
      targetTab: "overview",
    };
  }
  const need = (tc.pending ?? 0) + (tc.draft ?? 0);
  return {
    state: "needs_review",
    label: `${need} row${need === 1 ? "" : "s"} need review`,
    blocker: "Coverage rows exist but are not planner-ready.",
    targetTab: "overview",
  };
}

// Reuse the section-status → badge tone mapping the workspace already uses
// (OverviewPanel/TabStrip). No new status vocabulary is coined here.
function statusTone(status) {
  if (status === "locked") return "resolved";
  if (status === "ready") return "info";
  if (status === "partial") return "pending";
  return "draft"; // empty / unknown
}

function RailRow({ children, testId, active, current, onClick }) {
  return (
    <button
      type="button"
      className={"oc-navlink" + (active ? " active" : "")}
      data-testid={testId}
      data-rail-current={current ? "true" : undefined}
      onClick={onClick}
      style={{
        display: "block",
        width: "100%",
        textAlign: "left",
        borderLeft: current ? "3px solid var(--blocker)" : "3px solid transparent",
      }}
    >
      {children}
    </button>
  );
}

function SectionRow({ row, section, activeTab, currentSectionKey, onSelect }) {
  const status = section?.status ?? "empty";
  const pending = typeof section?.metrics?.pending === "number" ? section.metrics.pending : null;
  const blocker = section?.blockers?.[0] ?? null;
  const isCurrent = !!section && row.section === currentSectionKey;

  return (
    <RailRow
      testId={`rail-row-${row.id}`}
      active={activeTab === row.tab}
      current={isCurrent}
      onClick={() => onSelect(row.tab)}
    >
      <div className="row" style={{ justifyContent: "space-between", gap: 8 }}>
        <span className="truncate">
          {isCurrent && <span className="badge blocker no-dot" style={{ fontSize: 8.5, marginRight: 6 }}>now</span>}
          {row.title}
        </span>
        <span className={"badge " + statusTone(status) + " no-dot"} style={{ fontSize: 9 }} data-testid={`rail-status-${row.id}`}>
          {status}
        </span>
      </div>
      <div className="row" style={{ gap: 8, marginTop: 2 }}>
        {pending != null && pending > 0 && (
          <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-mute)" }} data-testid={`rail-pending-${row.id}`}>
            {pending} pending
          </span>
        )}
        {blocker && (
          <span className="mono" style={{ fontSize: 9.5, color: "var(--blocker)", textTransform: "none", letterSpacing: 0 }} data-testid={`rail-blocker-${row.id}`}>
            • {blocker}
          </span>
        )}
      </div>
    </RailRow>
  );
}

function TopicCoverageRow({ tc, activeTab, onSelect }) {
  const d = deriveTopicCoverageRow(tc);
  const counts = `Locked: ${tc?.locked ?? 0} · Reviewed: ${tc?.reviewed ?? 0} · Pending: ${tc?.pending ?? 0} · High-yield: ${tc?.high_yield ?? 0}`;
  return (
    <RailRow
      testId="rail-row-topic_coverage"
      active={activeTab === d.targetTab && false /* snapshot row never owns the active highlight */}
      current={false}
      onClick={() => onSelect(d.targetTab)}
    >
      <div className="row" style={{ justifyContent: "space-between", gap: 8 }}>
        <span className="truncate">Topic coverage</span>
        <span className="badge ink no-dot" style={{ fontSize: 8.5 }} data-testid="rail-topic-coverage-derived">
          derived
        </span>
      </div>
      <div className="row-sub" style={{ marginTop: 2 }} data-testid="rail-topic-coverage-state">{d.label}</div>
      <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-mute)", marginTop: 2 }}>{counts}</div>
      {d.blocker && (
        <div className="mono" style={{ fontSize: 9.5, color: "var(--blocker)", textTransform: "none", letterSpacing: 0, marginTop: 2 }}>
          • {d.blocker}
        </div>
      )}
    </RailRow>
  );
}

export default function ExamTaskRail({ sections, topicCoverage, activeTab, currentSectionKey, onSelect }) {
  const byKey = {};
  (sections || []).forEach((s) => { byKey[s.section] = s; });

  return (
    <nav
      className="oc-sidebar"
      data-testid="exam-task-rail"
      aria-label="Exam governance task rail"
      style={{ width: 264, flexShrink: 0, borderRight: "1px solid var(--rule)", paddingTop: 8 }}
    >
      <div className="oc-section" style={{ cursor: "default" }}>Tasks</div>
      {RAIL_HEAD.map((row) => (
        <SectionRow
          key={row.id}
          row={row}
          section={byKey[row.section]}
          activeTab={activeTab}
          currentSectionKey={currentSectionKey}
          onSelect={onSelect}
        />
      ))}
      <TopicCoverageRow tc={topicCoverage} activeTab={activeTab} onSelect={onSelect} />
      {RAIL_TAIL.map((row) => (
        <SectionRow
          key={row.id}
          row={row}
          section={byKey[row.section]}
          activeTab={activeTab}
          currentSectionKey={currentSectionKey}
          onSelect={onSelect}
        />
      ))}
    </nav>
  );
}
