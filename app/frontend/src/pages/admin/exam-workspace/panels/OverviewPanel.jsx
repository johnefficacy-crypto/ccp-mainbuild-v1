/**
 * OverviewPanel — read-only snapshot of all workspace dimensions.
 * Consumed by the "Overview" tab (first tab) in ExamWorkspace.
 */
import React from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import {
  LifecycleLegend,
  EXAM_PURPOSE_LABELS,
  BUSINESS_PRIORITY_LABELS,
} from "../ExamIntelGlossary";

// ── helpers ────────────────────────────────────────────────────────────────────

function Row({ label, value, mono }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="ctx-chip" style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
      <span className="lbl" style={{ minWidth: 130, flexShrink: 0 }}>{label}</span>
      <span className={mono ? "mono" : ""} style={{ fontSize: 12.5, color: "var(--ink)" }}>
        {value}
      </span>
    </div>
  );
}

function Section({ title, children, testId }) {
  return (
    <div
      style={{
        border: "1px solid var(--rule)",
        borderRadius: 6,
        padding: "14px 16px",
        background: "var(--paper)",
      }}
      data-testid={testId}
    >
      <div
        className="lbl"
        style={{ fontSize: 10.5, letterSpacing: "0.06em", marginBottom: 10, textTransform: "uppercase" }}
      >
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {children}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const cls =
    status === "locked" ? "ink" :
    status === "ready" ? "info" :
    status === "partial" ? "pending" : "draft";
  return (
    <span className={"badge " + cls} style={{ fontSize: 10, padding: "1px 7px" }}>
      {status ?? "—"}
    </span>
  );
}

function ReadinessRow({ sec }) {
  if (!sec) return null;
  const pct = sec.score_percent ?? 0;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
      <span style={{ minWidth: 140, color: "var(--ink-mute)" }}>{sec.label}</span>
      <StatusBadge status={sec.status} />
      <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-mute)" }}>{pct}%</span>
      {sec.blockers?.length > 0 && (
        <span className="mono" style={{ fontSize: 10, color: "var(--blocker)" }}>
          • {sec.blockers[0]}
        </span>
      )}
    </div>
  );
}

function MetricGrid({ items }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 20px" }}>
      {items.map(([label, val]) =>
        val !== null && val !== undefined ? (
          <span key={label} style={{ fontSize: 12 }}>
            <span style={{ color: "var(--ink-mute)" }}>{label} </span>
            <span className="mono" style={{ fontWeight: 600 }}>{val}</span>
          </span>
        ) : null,
      )}
    </div>
  );
}

// ── panel ──────────────────────────────────────────────────────────────────────

export default function OverviewPanel() {
  const { exam, cycle, cycles, phases, readiness, organization, family } = useExamWorkspace();

  const mgmtLabel = exam?.management_mode
    ? (BUSINESS_PRIORITY_LABELS[exam.management_mode] ?? exam.management_mode)
    : "Unclassified";

  const typeLabel = exam?.exam_type
    ? (EXAM_PURPOSE_LABELS[exam.exam_type] ?? exam.exam_type)
    : null;

  const overallSec = readiness?.overall;
  const tc = readiness?.topic_coverage;

  // Section map for quick lookup
  const secMap = {};
  (readiness?.sections || []).forEach((s) => { secMap[s.section] = s; });

  return (
    <div
      style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}
      data-testid="overview-panel"
    >
      {/* 1. Exam identity */}
      <Section title="Exam identity" testId="overview-section-identity">
        <Row label="Name" value={exam?.name} />
        <Row label="Slug" value={exam?.slug} mono />
        <Row label="Type" value={typeLabel} />
        <Row label="Management lane" value={mgmtLabel} />
        <Row label="Cadence" value={exam?.cadence ?? "—"} />
        <Row label="Active" value={exam?.is_active === false ? "No" : "Yes"} />
      </Section>

      {/* 2. Organisation & family */}
      <Section title="Organisation & family" testId="overview-section-org">
        {organization ? (
          <>
            <Row label="Organisation" value={organization.name} />
            {organization.type && <Row label="Org type" value={organization.type} />}
            {organization.trust_tier && <Row label="Trust tier" value={organization.trust_tier} />}
          </>
        ) : (
          <span style={{ fontSize: 12, color: "var(--ink-mute)" }}>No organisation linked</span>
        )}
        {family ? (
          <Row label="Family" value={family.name} />
        ) : (
          <Row label="Family" value="—" />
        )}
      </Section>

      {/* 3. Readiness scorecard */}
      {readiness && (
        <Section title="Readiness" testId="overview-section-readiness">
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <StatusBadge status={overallSec?.status} />
            <span className="mono" style={{ fontSize: 13, fontWeight: 700 }}>
              {overallSec?.score_percent ?? 0}%
            </span>
            <span style={{ fontSize: 11.5, color: "var(--ink-mute)" }}>
              {overallSec?.ready_to_activate ? "ready to activate" : "not yet ready"}
            </span>
          </div>
          {["setup", "documents", "syllabus_mapper", "pyq_workbench", "updates", "competition", "review_activate"].map(
            (k) => <ReadinessRow key={k} sec={secMap[k]} />,
          )}
        </Section>
      )}

      {/* 4. Topic coverage */}
      {tc && (
        <Section title="Topic coverage" testId="overview-section-topic-coverage">
          <MetricGrid items={[
            ["Total", tc.total],
            ["Draft", tc.draft],
            ["Pending", tc.pending],
            ["Reviewed", tc.reviewed],
            ["Locked", tc.locked],
            ["High yield", tc.high_yield],
          ]} />
        </Section>
      )}

      {/* 5. PYQ Workbench */}
      {secMap.pyq_workbench && (
        <Section title="PYQ workbench" testId="overview-section-pyq">
          <MetricGrid items={[
            ["Papers", secMap.pyq_workbench.metrics?.papers],
            ["Questions", secMap.pyq_workbench.metrics?.questions_total],
            ["Verified", secMap.pyq_workbench.metrics?.questions_verified],
            ["Locked", secMap.pyq_workbench.metrics?.questions_locked],
            ["Options", secMap.pyq_workbench.metrics?.options_total],
            ["Topic tags", secMap.pyq_workbench.metrics?.topic_tags_total],
          ]} />
        </Section>
      )}

      {/* 6. Updates */}
      {secMap.updates && (
        <Section title="Policy updates" testId="overview-section-updates">
          <MetricGrid items={[
            ["Total", secMap.updates.metrics?.total],
            ["Pending", secMap.updates.metrics?.pending],
            ["Verified", secMap.updates.metrics?.verified],
            ["Rejected", secMap.updates.metrics?.rejected],
            ["Stale", secMap.updates.metrics?.stale],
          ]} />
        </Section>
      )}

      {/* 7. Competition */}
      {secMap.competition && (
        <Section title="Competition" testId="overview-section-competition">
          <MetricGrid items={[
            ["Rows", secMap.competition.counts?.present],
            ["Draft", secMap.competition.metrics?.breakdown?.draft],
            ["Reviewed", secMap.competition.metrics?.breakdown?.reviewed],
            ["Locked", secMap.competition.metrics?.breakdown?.locked],
          ]} />
        </Section>
      )}

      {/* 8. Setup / phases */}
      <Section title="Setup" testId="overview-section-setup">
        <MetricGrid items={[
          ["Phases", phases?.length ?? secMap.setup?.metrics?.phase_count ?? 0],
          ["Cycles", cycles?.length ?? 0],
          ["Active cycle", cycle?.cycle_name ?? "—"],
        ]} />
      </Section>

      {/* 9. Documents */}
      {secMap.documents && (
        <Section title="Documents" testId="overview-section-documents">
          <MetricGrid items={[
            ["Total", secMap.documents.metrics?.total],
            ["Extracted", secMap.documents.metrics?.extracted],
            ["Pending", secMap.documents.metrics?.pending],
            ["Failed", secMap.documents.metrics?.failed],
          ]} />
        </Section>
      )}

      {/* 10. Lifecycle legend */}
      <div style={{ gridColumn: "1 / -1" }}>
        <LifecycleLegend />
      </div>
    </div>
  );
}
