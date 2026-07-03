/**
 * ExamWorkspace — Manage Exam shell (I8-B).
 *
 * Design source: ccp-mainbuild-v1 handoff / Exam Intelligence Workspace.html
 * CSS: admin-console.css (.oc design system), imported globally via index.css.
 *
 * Canonical route: /admin/exam-intelligence/exams/:exam_id
 * Legacy compat:   /admin/exam-intelligence/workspace/:exam_id  → redirected
 *
 * URL is the single source of tab state:
 *   ?tab=<id>      active tab (default: setup)
 *   ?cycle=<id>    selected cycle (normalized from backend current_cycle on first load)
 *   ?status=<s>    pre-filter for syllabus/pyq/updates panels
 *   ?document=<id> pre-select document in DocumentsPanel
 *   ?paper=<id>    pre-select paper in PyqWorkbenchPanel
 *   ?row=<id>      pre-select row in syllabus/pyq panels
 *   ?action=<a>    inline action for setup (e.g. add-cycle)
 */
import React, { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ExamWorkspaceProvider, useExamWorkspace } from "./ExamWorkspaceContext";
import SetupPanel from "./panels/SetupPanel";
import DocumentsPanel from "./panels/DocumentsPanel";
import UpdatesPanel from "./panels/UpdatesPanel";
import CompetitionPanel from "./panels/CompetitionPanel";
import ReviewActivatePanel from "./panels/ReviewActivatePanel";
import ExamActionConsole from "../../../features/admin/exam-intelligence/ExamActionConsole";
import {
  BUSINESS_PRIORITY_LABELS,
  CADENCE_LABELS,
  LifecycleLegend,
} from "../../../features/admin/exam-intelligence/ExamIntelGlossary";
import { useAuth } from "../../../lib/authContext";

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

function getMgmtModeLabel(mode) {
  if (mode == null) return (BUSINESS_PRIORITY_LABELS.null || {}).label || "Unclassified";
  return ((BUSINESS_PRIORITY_LABELS[mode] || BUSINESS_PRIORITY_LABELS.null) || {}).label || mode;
}

// ─── Advanced Repair overflow menu ──────────────────────────────────────────

function AdvancedRepairMenu({ examId, cycleId }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);
  const triggerRef = useRef(null);

  // Focus first menu item when menu opens
  useEffect(() => {
    if (!open) return;
    const firstItem = menuRef.current?.querySelector('[role="menuitem"]');
    firstItem?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleOutside(e) {
      if (
        menuRef.current && !menuRef.current.contains(e.target) &&
        triggerRef.current && !triggerRef.current.contains(e.target)
      ) {
        setOpen(false);
      }
    }
    function handleKey(e) {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
        return;
      }
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
        e.preventDefault();
        const items = Array.from(menuRef.current?.querySelectorAll('[role="menuitem"]') || []);
        if (!items.length) return;
        const idx = items.indexOf(document.activeElement);
        let next;
        if (e.key === "ArrowDown") next = items[(idx + 1) % items.length];
        else if (e.key === "ArrowUp") next = items[(idx - 1 + items.length) % items.length];
        else if (e.key === "Home") next = items[0];
        else if (e.key === "End") next = items[items.length - 1];
        next?.focus();
      }
    }
    document.addEventListener("mousedown", handleOutside);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleOutside);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  function closeAndRestoreFocus() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  const repairHref =
    `/admin/exam-intelligence/cms?exam_id=${encodeURIComponent(examId)}` +
    (cycleId ? `&cycle_id=${encodeURIComponent(cycleId)}` : "") +
    "&entity=documents";

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="btn small"
        data-testid="workspace-more-trigger"
      >
        More
      </button>
      {open && (
        <div
          ref={menuRef}
          role="menu"
          aria-label="More actions"
          className="absolute right-0 z-50 mt-1 min-w-[12rem] rounded-md bg-white py-1 shadow-lg ring-1 ring-black/5"
          data-testid="workspace-more-menu"
        >
          <Link
            to={repairHref}
            role="menuitem"
            tabIndex={0}
            className="block px-4 py-2 text-sm hover:bg-gray-50"
            data-testid="workspace-advanced-repair-link"
            onClick={closeAndRestoreFocus}
          >
            Advanced Repair
          </Link>
        </div>
      )}
    </div>
  );
}

// ─── Smart readiness header ──────────────────────────────────────────────────

function SmartHeader({ onGotoTab }) {
  const { exam, cycles, cycle, mgmt, organization, family } = useExamWorkspace();
  const { user } = useAuth();
  const { exam_id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();

  const hasCmsPermission =
    user?.role === "super_admin" ||
    user?.permissions?.includes("exam_intelligence.cms");

  function handleCycleChange(e) {
    const val = e.target.value;
    const tab = searchParams.get("tab") || "setup";
    const next = new URLSearchParams();
    if (val) next.set("cycle", val);
    next.set("tab", tab);
    // Preserve status/action; drop document/paper/row on cycle change
    const status = searchParams.get("status");
    const action = searchParams.get("action");
    if (status) next.set("status", status);
    if (action) next.set("action", action);
    setSearchParams(next);
  }

  const verdict = mgmt?.activation_verdict || {};
  const blockerCount = mgmt?.blocker_count ?? 0;
  const firstBlockerText = mgmt?.first_blocker_text ?? null;
  const actionQueue = Array.isArray(mgmt?.action_queue) ? mgmt.action_queue : [];
  const firstAction = actionQueue[0] ?? null;

  const managementMode = mgmt?.management_mode ?? exam?.management_mode ?? null;
  const cadence = mgmt?.cadence ?? exam?.cadence ?? null;
  const isActive = mgmt?.is_active ?? exam?.is_active ?? null;
  const familyName = mgmt?.family_name ?? family?.name ?? null;
  const orgName = mgmt?.organization_name ?? organization?.name ?? null;

  const cadenceLabel = cadence ? (CADENCE_LABELS[cadence] || cadence) : null;

  const cycleId = searchParams.get("cycle") ?? null;

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
            <span className="lbl">Exam Management</span>
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
          {/* Identity: mode · cadence · active/inactive · family · org · slug */}
          <div className="row-sub" style={{ marginTop: 2, gap: 6, flexWrap: "wrap" }}>
            <span>{getMgmtModeLabel(managementMode)}</span>
            {cadenceLabel && <><span style={{ opacity: 0.4 }}>·</span><span>{cadenceLabel}</span></>}
            <span style={{ opacity: 0.4 }}>·</span>
            <span className={`badge ${isActive ? "info" : "neutral"} no-dot`} style={{ fontSize: 9.5 }}>
              {isActive ? "Active" : "Inactive"}
            </span>
            {familyName && <><span style={{ opacity: 0.4 }}>·</span><span>{familyName}</span></>}
            {orgName && <><span style={{ opacity: 0.4 }}>·</span><span>{orgName}</span></>}
            {exam?.slug && (
              <><span style={{ opacity: 0.4 }}>·</span><span className="mono">{exam.slug}</span></>
            )}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8, flexShrink: 0 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {hasCmsPermission && (
              <AdvancedRepairMenu examId={exam_id} cycleId={cycleId} />
            )}
            <div>
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
        </div>
      </div>

      {/* Activation status strip — backend verdict authority only */}
      {mgmt && verdict.status && (
        <div
          className={`next-action${verdict.status === "ready" ? "" : " warn"}`}
          style={{ margin: "14px 0", gridTemplateColumns: "auto 1fr auto", gap: 16 }}
          data-testid="smart-header-status"
        >
          <div>
            <span className="lbl">Activation status</span>
            <div
              className="oc-title"
              style={{ fontSize: 16, marginTop: 4, color: "var(--paper)" }}
              data-testid="smart-header-verdict"
            >
              {verdict.headline || verdict.status}
            </div>
          </div>
          <div
            style={{
              borderLeft: "1px solid rgba(250,247,242,0.25)",
              paddingLeft: 16,
            }}
          >
            <span className="lbl">Next action</span>
            <div style={{ fontSize: 13.5, marginTop: 4, color: "var(--paper)" }}
                 data-testid="smart-header-next-action">
              {firstBlockerText || firstAction?.why || "All activation gates pass"}
            </div>
            {blockerCount > 0 && (
              <div className="row" style={{ marginTop: 8, gap: 8 }}>
                <span
                  className="badge blocker no-dot"
                  style={{ background: "rgba(250,247,242,0.16)", color: "var(--paper)" }}
                  data-testid="smart-header-blocker-count"
                >
                  {blockerCount} activation blocker{blockerCount === 1 ? "" : "s"}
                </span>
              </div>
            )}
          </div>
          {firstAction?.cta_route ? (
            <Link
              to={firstAction.cta_route}
              className="btn primary"
              style={{
                background: "var(--paper)",
                color: "var(--ink)",
                borderColor: "var(--paper)",
                alignSelf: "center",
              }}
              data-testid="smart-header-cta"
            >
              {firstAction.cta_label || "Go to next action"} →
            </Link>
          ) : null}
        </div>
      )}

      {/* Advisory content readiness and the lifecycle legend moved into the
          collapsed action disclosure (EI-CLEAN-05) so the header stays canonical:
          headline + first blocker + one next action. */}
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
                {readiness.overall?.ready_to_activate
                  ? "ready to activate"
                  : `${readiness.overall?.score_percent ?? 0}%`}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ─── Main shell ───────────────────────────────────────────────────────────────

function WorkspaceShell() {
  const { loading, error, refetch, readiness, mgmt, mgmtLoading, mgmtError, mgmtVersionError, refetchMgmt } = useExamWorkspace();
  const { exam_id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL is the single source of tab state
  const activeTab = TAB_ORDER.some((t) => t.id === searchParams.get("tab"))
    ? searchParams.get("tab")
    : "setup";

  const action = searchParams.get("action") ?? null;
  const status = searchParams.get("status") ?? null;
  const documentId = searchParams.get("document") ?? null;
  const paperId = searchParams.get("paper") ?? null;
  const rowId = searchParams.get("row") ?? null;

  function gotoTab(id) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("tab", id);
      return next;
    });
  }

  // Initial cycle normalization: if no ?cycle= yet and mgmt has a current_cycle,
  // set it via replace navigation so the back button doesn't land here.
  const currentCycleId = mgmt?.current_cycle?.id;
  useEffect(() => {
    if (!currentCycleId) return;
    if (searchParams.get("cycle")) return;
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("cycle", currentCycleId);
        return next;
      },
      { replace: true },
    );
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentCycleId]);

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

  const panelBody = (
    <>
      {activeTab === "setup" && <SetupPanel action={action} />}
      {activeTab === "documents" && (
        <DocumentsPanel onGotoTab={gotoTab} documentId={documentId} docStatus={status} />
      )}
      {activeTab === "syllabus" && (
        <Suspense fallback={<div style={{ padding: 20, color: "var(--ink-mute)" }}>Loading…</div>}>
          <SyllabusMapperPanel status={status} rowId={rowId} />
        </Suspense>
      )}
      {activeTab === "pyq" && (
        <Suspense fallback={<div style={{ padding: 20, color: "var(--ink-mute)" }}>Loading…</div>}>
          <PyqWorkbenchPanel paperId={paperId} rowId={rowId} status={status} />
        </Suspense>
      )}
      {activeTab === "updates" && <UpdatesPanel status={status} rowId={rowId} />}
      {activeTab === "competition" && <CompetitionPanel />}
      {activeTab === "review" && <ReviewActivatePanel onGotoTab={gotoTab} />}
    </>
  );

  // D04: workspace-level compatibility gate — shown on all tabs when the
  // management contract version is unsupported.  Suppresses semantic consumers
  // (SmartHeader verdict strip, action console, readiness tab content) and
  // keeps identity/navigation intact so the operator can still navigate away.
  const compatError = mgmtVersionError && !mgmtLoading;

  return (
    <div className="oc">
      <SmartHeader onGotoTab={gotoTab} />
      {compatError && (
        <div
          data-testid="workspace-compat-error"
          className="card"
          style={{ margin: "12px 16px 0", borderLeft: "3px solid var(--err, #c00)" }}
        >
          <div className="card-body" style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="err-row" style={{ flex: 1, margin: 0 }}>
              This workspace requires a newer client version. Reload the page or contact support.
            </span>
            <button className="btn" onClick={refetchMgmt} style={{ whiteSpace: "nowrap" }}>
              Retry
            </button>
          </div>
        </div>
      )}
      {/* EI-CLEAN-05: the action queue, activation checks, evidence, mock
          advisory and lifecycle legend collapse into one keyboard-accessible
          disclosure so they no longer sit always-expanded above the tabs. The
          native <details> element is inherently keyboard operable. SmartHeader
          above remains the canonical headline + first blocker + next action.
          Management data is passed so ExamActionConsole skips its own fetch. */}
      <details
        className="oc-action-disclosure"
        data-testid="workspace-action-details"
        style={{ margin: "0 22px" }}
      >
        <summary
          className="lbl"
          data-testid="workspace-action-summary"
          style={{ cursor: "pointer", padding: "10px 0", userSelect: "none" }}
        >
          Action queue, activation checks &amp; advisories
        </summary>
        <ExamActionConsole
          examId={exam_id}
          embedded
          data={mgmt}
          dataStatus={mgmtLoading ? "loading" : (mgmtError || compatError) ? "error" : "ready"}
          onRetry={refetchMgmt}
        />
        {readiness && (
          <div className="ctx-strip" style={{ marginTop: 4 }} data-testid="workspace-advisory-readiness">
            <span className="lbl" style={{ marginRight: 8 }}>Advisory content readiness</span>
            <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-mute)" }}>
              {readiness.overall?.score_percent ?? 0}%
            </span>
          </div>
        )}
        <div className="ctx-strip" style={{ marginTop: 4 }}><LifecycleLegend /></div>
      </details>
      <TabStrip active={activeTab} onChange={gotoTab} readiness={readiness} />

      <main className="oc-main" style={{ paddingTop: 18 }}>
        {panelBody}
      </main>
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
