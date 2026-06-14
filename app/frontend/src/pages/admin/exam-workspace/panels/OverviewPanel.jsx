import React from "react";
import {
  BUSINESS_PRIORITY_LABELS,
  EXAM_PURPOSE_LABELS,
} from "../../../../features/admin/exam-intelligence/ExamIntelGlossary";
import { useExamWorkspace } from "../ExamWorkspaceContext";

export default function OverviewPanel() {
  const { exam, cycle, readiness } = useExamWorkspace();
  const mgmtLabel = exam?.management_mode
    ? (BUSINESS_PRIORITY_LABELS[exam.management_mode]?.label ?? exam.management_mode)
    : BUSINESS_PRIORITY_LABELS.null.label;
  const typeLabel = exam?.exam_type
    ? (EXAM_PURPOSE_LABELS[exam.exam_type]?.label ?? exam.exam_type)
    : null;
  const familyLabel = exam?.family_name ?? exam?.family ?? "—";
  const orgLabel = exam?.organization_name ?? exam?.organization ?? exam?.org_name ?? "—";

  return (
    <section className="card" data-testid="overview-panel">
      <div className="card-head">
        <div>
          <div className="eyebrow">Workspace overview</div>
          <h2>{exam?.name ?? "Exam"}</h2>
        </div>
        <span className="pill pill-dusk">{mgmtLabel}</span>
      </div>
      <div className="grid cols-4" style={{ marginTop: 16 }}>
        <div>
          <div className="lbl">Purpose</div>
          <div className="field-val">{typeLabel ?? "—"}</div>
        </div>
        <div>
          <div className="lbl">Family</div>
          <div className="field-val" data-testid="overview-family">{familyLabel}</div>
        </div>
        <div>
          <div className="lbl">Organization</div>
          <div className="field-val" data-testid="overview-org">{orgLabel}</div>
        </div>
        <div>
          <div className="lbl">Cycle</div>
          <div className="field-val">{cycle?.cycle_name ?? cycle?.name ?? "All cycles"}</div>
        </div>
      </div>
      {readiness?.overall && (
        <div className="banner" style={{ marginTop: 16 }}>
          Readiness: {readiness.overall.score_percent ?? 0}% · {readiness.overall.status ?? "empty"}
        </div>
      )}
    </section>
  );
}
