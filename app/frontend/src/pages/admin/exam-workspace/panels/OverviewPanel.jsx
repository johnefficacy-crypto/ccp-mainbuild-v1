/**
 * OverviewPanel — exam workspace overview (non-duplicating fields + readiness).
 *
 * SmartHeader in ExamWorkspace.jsx already renders:
 *   exam name, family, slug, exam_type, active status (readiness badge).
 *
 * This panel shows only the fields SmartHeader does NOT show:
 *   cadence, management_mode, is_active (raw boolean, separate from readiness badge)
 *   plus the full per-section readiness summary.
 *
 * UX-EI-3 / D1: Duplicate exam identity fields (name, slug, type, family) are
 * intentionally absent here to avoid operator confusion with the SmartHeader.
 */
import React from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";

function ReadinessSection({ readiness }) {
  if (!readiness) {
    return (
      <div className="card-body">
        <div className="skel" style={{ height: 20, marginBottom: 6 }} />
        <div className="skel" style={{ height: 20 }} />
      </div>
    );
  }

  const sections = readiness.sections || [];
  const overall = readiness.overall || {};

  return (
    <div data-testid="overview-readiness-sections">
      <div className="card-head">
        <h3 className="oc-title">Readiness summary</h3>
        <span className="anno">
          {overall.score_percent ?? 0}% ready · {overall.status ?? "unknown"}
        </span>
      </div>
      <div>
        {sections.map((s) => {
          const ok = s.status === "ready" || s.status === "locked";
          return (
            <div
              key={s.section}
              className="check-row"
              data-testid={`overview-section-${s.section}`}
              style={{ cursor: "default" }}
            >
              <span
                className={ok ? "sdot ok" : s.status === "empty" ? "sdot bad" : "sdot warn"}
                aria-hidden="true"
                style={{ marginTop: 2, flexShrink: 0 }}
              />
              <div>
                <div className="row" style={{ gap: 6 }}>
                  <span className="ctxt" style={{ fontWeight: 500 }}>
                    {s.label}
                  </span>
                  <span
                    className={
                      ok
                        ? "badge info"
                        : s.status === "empty"
                        ? "badge neutral"
                        : "badge pending"
                    }
                    style={{ fontSize: 10, padding: "1px 6px" }}
                  >
                    {s.status}
                  </span>
                </div>
                {(s.blockers?.length || 0) > 0 && (
                  <ul
                    style={{
                      margin: "4px 0 0",
                      padding: 0,
                      listStyle: "none",
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 4,
                    }}
                    aria-label={`Blockers for ${s.label}`}
                  >
                    {s.blockers.map((b, i) => (
                      <li key={i} className="err-row" style={{ padding: "2px 6px", fontSize: 11 }}>
                        <span aria-hidden="true">⛔ </span>
                        {b}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function OverviewPanel() {
  const { exam, readiness } = useExamWorkspace();

  return (
    <div className="stack">
      <div className="scrn-head">
        <div>
          <div className="scrn-tag">Overview · exam metadata &amp; readiness</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>
            Exam overview
          </h2>
        </div>
      </div>

      {/* Exam configuration — fields NOT shown in SmartHeader.
          SmartHeader already shows: name, family, slug, exam_type, active badge.
          We show here: cadence, management_mode, is_active (raw). */}
      <div className="card" data-testid="overview-config-card">
        <div className="card-head">
          <h3 className="oc-title">Exam configuration</h3>
        </div>
        <div className="card-body grid2">
          <div className="field">
            <div className="field-lbl">Cadence</div>
            <div className="field-val" data-testid="overview-cadence">
              {exam?.cadence ?? "—"}
            </div>
          </div>
          <div className="field">
            <div className="field-lbl">Management mode</div>
            <div className="field-val" data-testid="overview-management-mode">
              {exam?.management_mode ?? "—"}
            </div>
          </div>
          <div className="field">
            <div className="field-lbl">Active</div>
            <div className="field-val" data-testid="overview-is-active">
              {exam == null
                ? "—"
                : exam.is_active
                ? "Yes"
                : "No"}
            </div>
          </div>
        </div>
      </div>

      {/* Readiness — per-section summary. Full review/lock actions are in
          the Review & Activate tab. This is read-only context. */}
      <div className="card" data-testid="overview-readiness-card">
        <ReadinessSection readiness={readiness} />
      </div>
    </div>
  );
}
