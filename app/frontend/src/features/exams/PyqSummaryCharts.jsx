import React from "react";

// Compact learner-facing distribution bars for the PYQ Intelligence overview.
// Driven entirely by GET /api/exam-intelligence/exams/{slug}/pyq-summary. Uses
// lightweight CSS bars (no chart runtime) so it renders cheaply and legibly.

function Bar({ label, value, max, tone = "sage" }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  const bg = tone === "clay" ? "bg-clay-400" : tone === "dusk" ? "bg-dusk-400" : "bg-sage-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-28 shrink-0 text-xs text-muted-foreground truncate" title={label}>
        {label}
      </div>
      <div className="flex-1 h-3 rounded bg-clay-100 overflow-hidden">
        <div className={`h-full ${bg}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="w-10 shrink-0 text-right text-xs font-medium tabular-nums">{value}</div>
    </div>
  );
}

function Block({ title, rows, tone, testId }) {
  if (!rows || rows.length === 0) return null;
  const max = rows.reduce((m, r) => Math.max(m, r.value), 0);
  return (
    <div className="soft-card rounded-2xl p-4" data-testid={testId}>
      <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground font-semibold">{title}</div>
      <div className="mt-3 space-y-1.5">
        {rows.map((r) => (
          <Bar key={r.key} label={r.label} value={r.value} max={max} tone={tone} />
        ))}
      </div>
    </div>
  );
}

const DIFF_LABEL = { easy: "Easy", medium: "Medium", hard: "Hard", unknown: "Unknown" };

export default function PyqSummaryCharts({ summary }) {
  if (!summary) return null;
  const byYear = (summary.by_year || []).map((r) => ({ key: String(r.year), label: String(r.year), value: r.questions }));
  const byPhase = (summary.by_phase || []).map((r) => ({
    key: r.phase_slug || r.phase_name || "phase",
    label: r.phase_name || r.phase_slug || "Phase",
    value: r.questions,
  }));
  const bySubject = (summary.by_subject || []).map((r) => ({
    key: r.subject_id || r.subject_name || "subj",
    label: r.subject_name || "Untagged",
    value: r.questions,
  }));
  const byDifficulty = (summary.by_difficulty || []).map((r) => ({
    key: r.difficulty,
    label: DIFF_LABEL[r.difficulty] || r.difficulty,
    value: r.questions,
  }));

  const totals = summary.totals || {};

  return (
    <div className="space-y-4" data-testid="pyq-summary-charts">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <div className="rounded-xl bg-clay-50/70 border border-clay-100 p-3">
          <div className="text-[10px] uppercase tracking-wider text-clay-700">Verified papers</div>
          <div className="font-heading text-2xl font-semibold mt-1">{(totals.papers || 0).toLocaleString("en-IN")}</div>
        </div>
        <div className="rounded-xl bg-clay-50/70 border border-clay-100 p-3">
          <div className="text-[10px] uppercase tracking-wider text-clay-700">Verified questions</div>
          <div className="font-heading text-2xl font-semibold mt-1">{(totals.questions || 0).toLocaleString("en-IN")}</div>
        </div>
        <div className="rounded-xl bg-clay-50/70 border border-clay-100 p-3">
          <div className="text-[10px] uppercase tracking-wider text-clay-700">Practice-ready</div>
          <div className="font-heading text-2xl font-semibold mt-1" data-testid="summary-practice-ready">
            {(totals.projected_practice_ready || 0).toLocaleString("en-IN")}
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-3">
        <Block title="By year" rows={byYear} tone="sage" testId="summary-by-year" />
        <Block title="By phase" rows={byPhase} tone="dusk" testId="summary-by-phase" />
        <Block title="By subject · high-yield" rows={bySubject} tone="clay" testId="summary-by-subject" />
        <Block title="By difficulty" rows={byDifficulty} tone="sage" testId="summary-by-difficulty" />
      </div>
    </div>
  );
}
