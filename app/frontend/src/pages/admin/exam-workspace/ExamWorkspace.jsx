/**
 * ExamWorkspace — Exam Intelligence admin workspace shell.
 *
 * Design source: ccp-mainbuild-v1 handoff / Exam Intelligence Workspace.html
 * CSS: admin-console.css (.oc design system), imported globally via index.css.
 *
 * Routes:
 *   /admin/exam-intelligence/workspace/:exam_id
 *   /admin/exam-intelligence/workspace/:exam_id/:cycle_id
 */
import React, { lazy, Suspense, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ExamWorkspaceProvider, useExamWorkspace } from "./ExamWorkspaceContext";
import SetupPanel from "./panels/SetupPanel";
import DocumentsPanel from "./panels/DocumentsPanel";
import UpdatesPanel from "./panels/UpdatesPanel";
import CompetitionPanel from "./panels/CompetitionPanel";
import ReviewActivatePanel from "./panels/ReviewActivatePanel";

const SyllabusMapperPanel = lazy(() => import("./syllabus-mapper/SyllabusMapperPanel"));
const PyqWorkbenchPanel = lazy(() => import("./pyq-workbench/PyqWorkbenchPanel"));

// ─── Tab definitions ────────────────────────────────────────────────────────

const TAB_ORDER = [
  { id: "setup",      label: "Setup",             kind: "open" },
  { id: "documents",  label: "Documents",          kind: "open" },
  { id: "syllabus",   label: "Syllabus Mapper",    kind: "readiness", section: "syllabus_mapper" },
  { id: "pyq",        label: "PYQ Workbench",      kind: "readiness", section: "pyq_workbench" },
  { id: "updates",    label: "Updates",            kind: "readiness", section: "updates" },
  { id: "competition",label: "Competition",        kind: "readiness", section: "competition" },
  { id: "review",     label: "Review & Activate",  kind: "terminal",  section: "review_activate" },
];

function sectionByKey(readiness, sectionKey) {
  return readiness?.sections?.find((s) => s.section === sectionKey) || null;
}

function totalBlockers(readiness) {
  return (readiness?.sections || [])
    .filter((s) => s.section !== "review_activate")
    .reduce((n, s) => n + (s.blockers?.length || 0), 0);
}

// ─── Trust legend ────────────────────────────────────────────────────────────

function TrustLegend() {
  const items = [
    ["draft",    "draft",    "created, not reviewed"],
    ["pending",  "pending",  "in review queue"],
    ["blocker",  "needs fix","sent back to enrichment"],
    ["info",     "reviewed", "reviewed, not yet live"],
    ["ink",      "locked",   "live to aspirants"],
  ];
  return (
    <div className="ctx-strip" style={{ marginTop: 4 }}>
      <span className="lbl" style={{ marginRight: 2 }}>Trust legend</span>
      {items.map(([cls, text, desc]) => (
        <span className="ctx-chip" key={text} title={desc}>
          <span className={"badge " + cls} style={{ fontSize: 9.5, padding: "1px 6px" }}>
            {text}
          </span>
          <span style={{ color: "var(--ink-mute)", fontSize: 10.5 }}>{desc}</span>
        </span>
      ))}
    </div>
  );
}

// ─── Smart readiness header ──────────────────────────────────────────────────

function SmartHeader({ onGotoTab }) {
  const { exam, cycles, cycle, readiness } = useExamWorkspace();
  const { exam_id } = useParams();
  const navigate = useNavigate();

  function handleCycleChange(e) {
    const val = e.target.value;
    if (val) {
      navigate(`/admin/exam-intelligence/workspace/${exam_id}/${val}`);
    } else {
      navigate(`/admin/exam-intelligence/workspace/${exam_id}`);
    }
  }

  const blockers = totalBlockers(readiness);
  const scorePercent = readiness?.overall?.score_percent ?? 0;
  const overallStatus = readiness?.overall?.status ?? "empty";

  // Current stage = first non-ready/locked section
  const currentSec = (readiness?.sections || []).find(
    (s) => s.section !== "review_activate" && !(s.status === "ready" || s.status === "locked"),
  );
  const stageLabel = currentSec ? currentSec.label : "Ready to activate";

  // Next action = highest-weight blocked section
  const nextSec = [...(readiness?.sections || [])]
    .filter((s) => (s.blockers?.length || 0) > 0)
    .sort((a, b) => (b.weight || 0) - (a.weight || 0))[0];
  const nextLine = nextSec
    ? `${nextSec.blockers[0]} — open ${nextSec.label}`
    : "All sections clear — review & activate";

  const tabForSection = {
    setup: "setup", documents: "documents",
    syllabus_mapper: "syllabus", pyq_workbench: "pyq",
    updates: "updates", competition: "competition",
    review_activate: "review",
  };
  const nextTabId = nextSec ? (tabForSection[nextSec.section] ?? "review") : "review";

  return (
    <div
      style={{
        borderBottom: "1px solid var(--rule)",
        background: "var(--paper)",
        padding: "16px 22px 0",
      }}
    >
      {/* Title row */}
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div className="min-w-0">
          <div className="row" style={{ gap: 8 }}>
            <span className="lbl">Exam Intelligence · Workspace</span>
            {exam?.exam_type && (
              <span className="badge ink no-dot" style={{ fontSize: 9.5 }}>
                {exam.exam_type}
              </span>
            )}
          </div>
          <h1
            className="oc-title disp"
            style={{ fontSize: 26, marginTop: 4 }}
            data-testid="exam-name"
          >
            {exam?.name ?? exam_id}
          </h1>
          {exam?.slug && (
            <div className="row-sub" style={{ marginTop: 2 }}>
              {exam.family_name ?? exam.family ?? ""}{exam.family_name || exam.family ? " · " : ""}
              <span className="mono">{exam.slug}</span>
            </div>
          )}
        </div>

        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <div className="lbl" style={{ marginBottom: 4 }}>Cycle</div>
          <select
            className="input"
            style={{ minWidth: 180 }}
            value={cycle?.id ?? ""}
            onChange={handleCycleChange}
            data-testid="cycle-picker"
          >
            <option value="">All cycles</option>
            {cycles.map((c) => (
              <option key={c.id} value={c.id}>
                {c.cycle_name ?? c.name ?? c.id}
                {c.status === "active" ? " · active" : ""}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Readiness strip */}
      {readiness && (
        <div
          className="next-action warn"
          style={{ margin: "14px 0", gridTemplateColumns: "auto 1fr auto", gap: 16 }}
        >
          <div>
            <span className="lbl">Current stage</span>
            <div
              className="oc-title"
              style={{ fontSize: 16, marginTop: 4, color: "var(--paper)" }}
            >
              {stageLabel}
            </div>
            <div
              className="mono"
              style={{ fontSize: 10.5, color: "rgba(250,247,242,0.7)", marginTop: 2 }}
            >
              {scorePercent}% ready · {overallStatus}
            </div>
          </div>
          <div
            style={{
              borderLeft: "1px solid rgba(250,247,242,0.25)",
              paddingLeft: 16,
            }}
          >
            <span className="lbl">Next action</span>
            <div style={{ fontSize: 13.5, marginTop: 4, color: "var(--paper)" }}>
              {nextLine}
            </div>
            <div className="row" style={{ marginTop: 8, gap: 8 }}>
              <span
                className="badge blocker no-dot"
                style={{ background: "rgba(250,247,242,0.16)", color: "var(--paper)" }}
              >
                {blockers} activation blocker{blockers === 1 ? "" : "s"}
              </span>
            </div>
          </div>
          <button
            className="btn primary"
            style={{
              background: "var(--paper)",
              color: "var(--ink)",
              borderColor: "var(--paper)",
              alignSelf: "center",
            }}
            onClick={() => onGotoTab(nextTabId)}
          >
            Go to next action →
          </button>
        </div>
      )}

      <TrustLegend />
      <div style={{ height: 14 }} />
    </div>
  );
}

// ─── 7-tab strip ─────────────────────────────────────────────────────────────

function TabStrip({ active, onChange, readiness }) {
  return (
    <div className="modebar" role="tablist" style={{ paddingTop: 2 }} data-testid="tab-strip">
      {TAB_ORDER.map((t) => {
        const sec = t.section ? sectionByKey(readiness, t.section) : null;
        const isActive = active === t.id;
        const hasBlocker = sec && (sec.blockers?.length || 0) > 0;

        return (
          <button
            key={t.id}
            role="tab"
            aria-selected={isActive}
            className={"modepill" + (isActive ? " active" : "")}
            onClick={() => onChange(t.id)}
            data-testid={`tab-${t.id}`}
            style={{
              flexDirection: "column",
              alignItems: "flex-start",
              gap: 2,
              paddingTop: 9,
              paddingBottom: 9,
            }}
          >
            <span className="row" style={{ gap: 6 }}>
              {t.kind === "terminal" && <span style={{ fontSize: 11 }}>🔒</span>}
              {t.label}
              {t.kind === "open" && (
                <span
                  className="count"
                  style={{
                    background: "transparent",
                    color: "var(--ink-mute)",
                    padding: 0,
                    fontSize: 9,
                  }}
                >
                  always open
                </span>
              )}
              {sec && (sec.status === "ready" || sec.status === "locked") && t.kind === "readiness" && (
                <span
                  className={"badge " + (sec.status === "locked" ? "resolved" : "info")}
                  style={{ fontSize: 10, padding: "1px 6px" }}
                >
                  {sec.status}
                </span>
              )}
            </span>
            {t.kind === "readiness" && hasBlocker && (
              <span
                className="mono"
                style={{
                  fontSize: 9.5,
                  color: "var(--blocker)",
                  textTransform: "none",
                  letterSpacing: 0,
                }}
              >
                • {sec.blockers[0]}
              </span>
            )}
            {t.kind === "terminal" && readiness && (
              <span
                className="mono"
                style={{
                  fontSize: 9.5,
                  color: "var(--ink-mute)",
                  textTransform: "none",
                  letterSpacing: 0,
                }}
              >
                {readiness.overall?.ready_to_activate ? "ready to activate" : `${readiness.overall?.score_percent ?? 0}%`}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ─── Advanced raw table editor drawer ────────────────────────────────────────

function AdvancedDrawer() {
  const [open, setOpen] = useState(false);
  const [entity, setEntity] = useState("syllabus_topic_mentions");

  return (
    <div
      style={{
        borderTop: "1px solid var(--rule)",
        marginTop: 22,
        background: "var(--paper-sunk)",
      }}
    >
      <button
        className="oc-section-toggle"
        style={{ padding: "12px 22px", fontSize: 11 }}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>
          ⚙ Advanced — raw table editor{" "}
          <span style={{ color: "var(--ink-mute)", textTransform: "none", letterSpacing: 0 }}>
            · bulk import &amp; edge fixes
          </span>
        </span>
        <span
          className="nav-chevron"
          style={{ transform: open ? "rotate(180deg)" : "none" }}
        >
          ▾
        </span>
      </button>
      {open && (
        <div style={{ padding: "0 22px 22px" }}>
          <div
            className="banner"
            style={{
              padding: "8px 12px",
              borderRadius: 4,
              border: "1px dashed var(--rule)",
              background: "var(--paper)",
              fontSize: 11.5,
              color: "var(--ink-mute)",
              marginBottom: 10,
            }}
          >
            Secondary path. Direct row edits skip the guided workflow above — use only for bulk
            import or edge fixes. Rows still land at{" "}
            <span className="mono">pending</span>.
          </div>
          <div className="ctx-strip" style={{ marginBottom: 10 }}>
            <span className="ctx-kind">Entity</span>
            <select
              className="input"
              style={{ maxWidth: 280 }}
              value={entity}
              onChange={(e) => setEntity(e.target.value)}
            >
              <option value="syllabus_topic_mentions">syllabus_topic_mentions</option>
              <option value="pyq_questions">pyq_questions</option>
              <option value="exam_competition_metrics">exam_competition_metrics</option>
            </select>
            <span
              className="row-sub"
              style={{ fontSize: 11, color: "var(--ink-mute)", marginLeft: 4 }}
            >
              Navigate to the dedicated panel above to manage rows.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main shell ───────────────────────────────────────────────────────────────

function WorkspaceShell() {
  const { loading, error, refetch, readiness } = useExamWorkspace();
  const [activeTab, setActiveTab] = useState("setup");

  function gotoTab(id) { setActiveTab(id); }

  if (loading) {
    return (
      <div className="oc" data-testid="workspace-loading">
        <div style={{ padding: "2rem" }}>
          <div className="skel" style={{ height: 32, width: "40%", marginBottom: 12 }} />
          <div className="skel" style={{ height: 16, width: "25%", marginBottom: 20 }} />
          <div className="skel" style={{ height: 44, marginBottom: 8 }} />
          <div className="skel" style={{ height: 280 }} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="oc" data-testid="workspace-error">
        <div style={{ padding: "2rem" }}>
          <div className="err-row" style={{ marginBottom: 12 }}>{error}</div>
          <button className="btn primary" onClick={refetch}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="oc">
      <SmartHeader onGotoTab={gotoTab} />
      <TabStrip active={activeTab} onChange={setActiveTab} readiness={readiness} />

      <main className="oc-main" style={{ paddingTop: 18 }}>
        {activeTab === "setup" && <SetupPanel />}
        {activeTab === "documents" && <DocumentsPanel onGotoTab={gotoTab} />}
        {activeTab === "syllabus" && (
          <Suspense fallback={<div style={{ padding: 20, color: "var(--ink-mute)" }}>Loading…</div>}>
            <SyllabusMapperPanel />
          </Suspense>
        )}
        {activeTab === "pyq" && (
          <Suspense fallback={<div style={{ padding: 20, color: "var(--ink-mute)" }}>Loading…</div>}>
            <PyqWorkbenchPanel />
          </Suspense>
        )}
        {activeTab === "updates" && <UpdatesPanel />}
        {activeTab === "competition" && <CompetitionPanel />}
        {activeTab === "review" && <ReviewActivatePanel onGotoTab={gotoTab} />}
      </main>

      <AdvancedDrawer />

    </div>
  );
}

export default function ExamWorkspace() {
  return (
    <ExamWorkspaceProvider>
      <WorkspaceShell />
    </ExamWorkspaceProvider>
  );
}
