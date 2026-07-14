/**
 * ImprovementLab — the learner-facing Improvement Lab surface (GQR-S5).
 *
 * Canonical route: /app/study/improvement-lab. The former /app/study/error-lab
 * route is preserved as a backward-compatible redirect to this page (see
 * appRoutes.jsx). Mounted UNDER StudyShell and inside RouteErrorBoundary (like
 * the EWP-3/EWP-4 routes), NOT via AttemptShellRouter, and ABSENT from the
 * sidebar (no-new-surface rule). Reached from study surfaces / planner tasks.
 *
 * Composition — three independent sections, each with its own data source and
 * its own loading / empty / error state. A failure in one section must not hide
 * the others, so each is wrapped in a local SectionBoundary:
 *
 *   Improvement Lab
 *   ├── My Writing Errors   → GET /api/study/practice/english/error-lab (EWP-4)
 *   ├── Methods & Shortcuts → Quant learner feed (GQR-S6, not yet wired)
 *   └── Approaches & Patterns → Reasoning learner feed (GQR-S6, not yet wired)
 *
 * English preservation: the `ewp_error_lab` read model and its endpoint are
 * unchanged; only the learner-facing framing moved under this parent surface.
 */
import React from "react";

import { PageHeader } from "../../shared/ui/studyos";
import SectionBoundary from "../../features/study/improvement-lab/SectionBoundary";
import MyWritingErrors from "../../features/study/improvement-lab/MyWritingErrors";
import PlannedSection from "../../features/study/improvement-lab/PlannedSection";

export default function ImprovementLab() {
  return (
    <div className="mx-auto max-w-3xl p-4" data-testid="improvement-lab">
      <PageHeader
        eyebrow="Study OS"
        title="Improvement Lab"
        sub="Your recurring errors and the solving strategies that help you improve"
      />

      <SectionBoundary title="My Writing Errors">
        <MyWritingErrors />
      </SectionBoundary>

      <SectionBoundary title="Methods & Shortcuts">
        <PlannedSection
          testId="improvement-lab-quant"
          eyebrow="Quantitative Aptitude"
          title="Methods & Shortcuts"
          sub="Faster methods and shortcuts drawn from your practice"
          description="As you attempt more Quant questions, the methods and shortcuts worth revisiting will appear here."
        />
      </SectionBoundary>

      <SectionBoundary title="Approaches & Patterns">
        <PlannedSection
          testId="improvement-lab-reasoning"
          eyebrow="Reasoning"
          title="Approaches & Patterns"
          sub="Recommended approaches and recurring patterns from your practice"
          description="As you attempt more Reasoning questions, the approaches and patterns worth revisiting will appear here."
        />
      </SectionBoundary>
    </div>
  );
}
