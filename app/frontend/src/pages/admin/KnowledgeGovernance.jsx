import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, ClipboardCheck, GraduationCap, RefreshCcw, ShieldCheck, Sparkles, Users2 } from "lucide-react";
import { api } from "../../lib/api";

// TODO PR3-BE-enh: add per-lane aggregate counts (exams, eligibility rules,
// orgs, verification reports, reverification batches, AI policy entries,
// personas) so the cards below can show real metrics instead of the
// "not available yet" placeholder.

const LANES = [
  {
    label: "Exam truth & planner readiness",
    icon: GraduationCap,
    description: "Master exam catalogue, guided exam setup, add-cycle wizard, workspace, and CMS / PYQ paper management.",
    links: [
      { to: "/admin/exam-intelligence", label: "Exam Intelligence" },
      { to: "/admin/exam-intelligence/new", label: "Guided Exam" },
      { to: "/admin/exam-intelligence/cms", label: "CMS / PYQ" },
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
    metricKey: null,
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
    metricKey: null,
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

export default function AdminKnowledgeGovernance() {
  const [audit, setAudit] = useState([]);

  useEffect(() => {
    api
      .get("/api/admin/overview")
      .then((data) => {
        const rows = (data.recent_audit || []).filter(
          (r) => !r.target || KG_ENTITY_TYPES.has(r.target),
        );
        setAudit(rows);
      })
      .catch(() => {});
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
                {/* TODO PR3-BE-enh: replace this placeholder with a real count once the
                    aggregate endpoint exposes KG-scoped metrics. */}
                <div className="anno" style={{ fontStyle: "italic" }}>counts: not available yet</div>
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
