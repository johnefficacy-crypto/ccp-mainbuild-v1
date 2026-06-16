import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, ClipboardCheck, GraduationCap, ShieldCheck } from "lucide-react";
import { api } from "../../lib/api";

// TODO PR3-BE-enh: add per-lane aggregate counts for "Exam truth & planner
// readiness" and "AI + personalization guardrails" lanes — no kg metrics are
// available from the overview endpoint for those two lanes yet.

const LANES = [
  {
    label: "Exam truth & planner readiness",
    icon: GraduationCap,
    description: "Master exam catalogue, guided exam setup, add-cycle wizard, workspace, and CMS / PYQ paper management.",
    links: [
      { to: "/admin/exam-intelligence/console", label: "Exam Governance Console" },
      { to: "/admin/exam-intelligence", label: "Exam Registry" },
      { to: "/admin/exam-intelligence/new", label: "Create exam" },
    ],
    metricKey: null,
  },
  {
    label: "User eligibility truth",
    icon: ShieldCheck,
    description: "Rules that gate which users can sit which exams. Changes here propagate immediately to aspirant eligibility checks.",
    links: [
      { to: "/admin/exam-eligibility", label: "Exam Eligibility" },
    ],
    metricKey: "eligibility_rules",
  },
  {
    label: "Official-source trust & change propagation",
    icon: ClipboardCheck,
    description: "Organisation registry, per-org verification reports, and batch reverification workflows for official-source changes.",
    links: [
      { to: "/admin/organizations", label: "Organizations" },
      { to: "/admin/verification-reports", label: "Verification Reports" },
      { to: "/admin/reverification-batches", label: "Reverification Batches" },
    ],
    metricKey: "trust_propagation",
  },
  {
    label: "AI + personalization guardrails",
    icon: Bot,
    description: "AI policy controls and persona definitions that constrain and personalise study-plan generation.",
    links: [
      { to: "/admin/ai-policy", label: "AI Governance" },
      { to: "/admin/persona", label: "Persona" },
    ],
    metricKey: null,
  },
];

const KG_ENTITY_TYPES = new Set([
  "exam", "exam_cycle", "eligibility_rule", "organization", "verification_report",
  "reverification_batch", "ai_policy", "persona",
]);

function LaneMetric({ metricKey, kg, kgLoading, kgError }) {
  if (metricKey === null) {
    return (
      <div className="anno" style={{ fontStyle: "italic" }}>counts: not available yet</div>
    );
  }

  if (kgLoading) {
    return <div className="anno" style={{ fontStyle: "italic" }}>loading…</div>;
  }

  if (kgError || !kg) {
    return <div className="anno" style={{ fontStyle: "italic", color: "var(--c-warn, #b45309)" }}>counts unavailable</div>;
  }

  if (metricKey === "eligibility_rules") {
    const r = kg.eligibility_rules ?? {};
    const draft = r.draft ?? 0;
    const verified = r.verified ?? 0;
    const archived = r.archived ?? 0;
    return (
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <span className="anno"><strong>{draft}</strong> draft</span>
        <span className="anno"><strong>{verified}</strong> verified</span>
        <span className="anno"><strong>{archived}</strong> archived</span>
      </div>
    );
  }

  if (metricKey === "trust_propagation") {
    const unacked = kg.unacked_reverification_batches ?? 0;
    const needsAction = kg.reports_need_action ?? 0;
    return (
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <span className="anno"><strong>{unacked}</strong> unacked batch{unacked !== 1 ? "es" : ""}</span>
        <span className="anno"><strong>{needsAction}</strong> report{needsAction !== 1 ? "s" : ""} need action</span>
      </div>
    );
  }

  return <div className="anno" style={{ fontStyle: "italic" }}>counts: not available yet</div>;
}

export default function AdminKnowledgeGovernance() {
  const [audit, setAudit] = useState([]);
  const [kg, setKg] = useState(null);
  const [kgLoading, setKgLoading] = useState(true);
  const [kgError, setKgError] = useState(false);

  useEffect(() => {
    setKgLoading(true);
    api
      .get("/api/admin/overview")
      .then((data) => {
        const rows = (data.recent_audit || []).filter(
          (r) => !r.target || KG_ENTITY_TYPES.has(r.target),
        );
        setAudit(rows);
        setKg(data.kg ?? null);
        setKgError(!data.kg);
      })
      .catch(() => {
        setKgError(true);
      })
      .finally(() => {
        setKgLoading(false);
      });
  }, []);

  return (
    <div className="stack" data-testid="admin-kg-landing">
      <section className="scrn" style={{ padding: 0, border: "none" }}>
        <div className="scrn-head">
          <div>
            <div className="lbl">Admin · Knowledge Governance</div>
            <h2 className="oc-title disp" style={{ fontSize: 22, marginTop: 4 }}>Knowledge Governance</h2>
            <div className="anno" style={{ marginTop: 4 }}>
              Four lanes — exam truth, eligibility truth, official-source trust, and AI guardrails.
            </div>
          </div>
          <span className="scrn-tag">knowledge governance</span>
        </div>
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
        {LANES.map((lane) => {
          const Icon = lane.icon;
          return (
            <div key={lane.label} className="card">
              <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Icon className="nav-glyph" style={{ flexShrink: 0 }} />
                  <strong style={{ fontSize: 13 }}>{lane.label}</strong>
                </div>
                <p className="anno" style={{ margin: 0 }}>{lane.description}</p>
                <LaneMetric
                  metricKey={lane.metricKey}
                  kg={kg}
                  kgLoading={kgLoading && lane.metricKey !== null}
                  kgError={kgError}
                />
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                  {lane.links.map((lk) => (
                    <Link key={lk.to} to={lk.to} className="btn small">
                      {lk.label}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <section className="scrn" style={{ marginTop: 24 }}>
        <div className="scrn-head">
          <div>
            <div className="lbl">Knowledge Governance · recent activity</div>
            <h3 className="oc-title" style={{ fontSize: 16, marginTop: 4 }}>What changed / what to do next</h3>
          </div>
        </div>
        {audit.length === 0 ? (
          <div className="card">
            <div className="card-body">
              <div className="empty">
                <div className="empty-title">No recent KG activity.</div>
                All lanes are quiet. Check back after the next import or rule change.
              </div>
            </div>
          </div>
        ) : (
          <div className="card">
            <ul className="stack" style={{ padding: 0, margin: 0, listStyle: "none" }}>
              {audit.map((row, i) => (
                <li
                  key={i}
                  className="card-body"
                  style={{ display: "flex", gap: 12, alignItems: "flex-start", justifyContent: "space-between" }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{row.action}</div>
                    <div className="anno">{row.target ?? "—"} · {row.actor}</div>
                    {row.notes ? <div className="anno" style={{ marginTop: 2 }}>{row.notes}</div> : null}
                  </div>
                  <div className="anno" style={{ flexShrink: 0, textAlign: "right" }}>
                    {row.at ? new Date(row.at).toLocaleString() : "—"}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
