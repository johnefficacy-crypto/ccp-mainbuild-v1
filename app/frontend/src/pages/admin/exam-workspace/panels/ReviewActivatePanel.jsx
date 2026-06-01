import React from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";

const TAB_FOR_SECTION = {
  setup: "setup",
  documents: "documents",
  syllabus_mapper: "syllabus",
  pyq_workbench: "pyq",
  updates: "updates",
  competition: "competition",
};

function StatusDot({ status }) {
  const cls =
    status === "ready" || status === "locked"
      ? "sdot ok"
      : status === "empty"
      ? "sdot bad"
      : "sdot warn";
  return <span className={cls} style={{ marginTop: 4 }} />;
}

function StatusBadge({ status }) {
  const map = {
    empty:   { cls: "badge neutral",  text: "empty" },
    partial: { cls: "badge pending",  text: "in progress" },
    ready:   { cls: "badge info",     text: "ready" },
    locked:  { cls: "badge resolved", text: "locked" },
  };
  const b = map[status] || map.empty;
  return (
    <span className={b.cls} style={{ fontSize: 10, padding: "1px 6px" }}>
      {b.text}
    </span>
  );
}

export default function ReviewActivatePanel({ onGotoTab }) {
  const { readiness, readiness_loading } = useExamWorkspace();

  if (readiness_loading || !readiness) {
    return (
      <div className="stack">
        <div className="scrn-head">
          <div className="scrn-tag">Terminal · lock &amp; activate</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>
            Review &amp; Activate
          </h2>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="skel" style={{ height: 48, marginBottom: 10 }} />
            <div className="skel" style={{ height: 20, marginBottom: 6 }} />
            <div className="skel" style={{ height: 20 }} />
          </div>
        </div>
      </div>
    );
  }

  const sections = (readiness.sections || []).filter(
    (s) => s.section !== "review_activate",
  );
  const overall = readiness.overall || {};
  const ready = overall.ready_to_activate;
  const scorePercent = overall.score_percent ?? 0;

  const totalBlockers = sections.reduce((n, s) => n + (s.blockers?.length || 0), 0);
  const blockedSections = sections.filter((s) => (s.blockers?.length || 0) > 0);
  const clearCount = sections.filter(
    (s) => s.status === "ready" || s.status === "locked",
  ).length;

  return (
    <div className="stack">
      <div className="scrn-head">
        <div>
          <div className="scrn-tag">Terminal · lock &amp; activate</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>
            Review &amp; Activate
          </h2>
        </div>
        <span className="badge pending no-dot">{scorePercent}% ready</span>
      </div>

      {/* Activation callout */}
      <div className={"next-action" + (ready ? "" : " warn")}>
        <div>
          <span className="lbl">{ready ? "Ready" : "Activation blocked"}</span>
          <div
            className="oc-title"
            style={{ fontSize: 16, marginTop: 4, color: "var(--paper)" }}
          >
            {ready
              ? "All sections verified — this exam can go live."
              : `${totalBlockers} blocker${totalBlockers === 1 ? "" : "s"} across ${blockedSections.length} section${blockedSections.length === 1 ? "" : "s"} must clear first.`}
          </div>
        </div>
        <button
          className="btn primary"
          disabled={!ready}
          title={ready ? "" : "Resolve blockers to enable"}
        >
          {ready ? "Lock & activate exam" : "🔒 Activate (disabled)"}
        </button>
      </div>

      {/* Section checklist */}
      <div className="card">
        <div className="card-head">
          <h3 className="oc-title">Section readiness checklist</h3>
          <span className="row-sub">
            {clearCount} / {sections.length} clear
          </span>
        </div>
        <div>
          {sections.map((s) => {
            const ok = s.status === "ready" || s.status === "locked";
            const tabTarget = TAB_FOR_SECTION[s.section];
            return (
              <div
                key={s.section}
                className="check-row"
                style={{ cursor: "default" }}
              >
                <StatusDot status={s.status} />
                <div>
                  <div className="row" style={{ gap: 8 }}>
                    <span className="ctxt" style={{ fontWeight: 500 }}>
                      {s.label}
                    </span>
                    <StatusBadge status={s.status} />
                    {s.weight > 0 && (
                      <span className="csub">weight {s.weight}</span>
                    )}
                  </div>
                  <div className="csub" style={{ marginTop: 3 }}>{s.note}</div>
                  {(s.blockers?.length || 0) > 0 && (
                    <div className="row" style={{ gap: 6, marginTop: 6 }}>
                      {s.blockers.map((b, i) => (
                        <span key={i} className="err-row" style={{ padding: "3px 7px" }}>
                          ⛔ {b}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div style={{ textAlign: "right" }}>
                  {!ok && tabTarget ? (
                    <button
                      className="btn small"
                      onClick={() => onGotoTab(tabTarget)}
                    >
                      Resolve →
                    </button>
                  ) : ok ? (
                    <span className="seal" style={{ fontSize: 11 }}>verified</span>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
