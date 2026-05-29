import React, { useEffect, useState } from "react";
import { History, AlertTriangle } from "lucide-react";
import { api } from "../../../lib/api";
import { Card, Eyebrow, Pill, StatusDot } from "../../../shared/ui/studyos";

const REGEN_TRIGGER_LABEL = {
  missed_days_streak: "Missed days streak",
  backlog_threshold: "Backlog over threshold",
  deadline_compression: "Deadline compression",
  mock_score_drift: "Mock score drift",
};

const REGEN_SEVERITY_TONE = {
  low: "outline",
  medium: "amber",
  high: "rose",
};

// RegenTriggerStrip surfaces backend-computed auto-regen trigger
// conditions. The planner does NOT apply changes from this strip — the
// user still drafts and applies via /api/study/plan/{draft,apply}. The
// strip just makes the conditions visible.
function RegenTriggerStrip({ triggers }) {
  if (!Array.isArray(triggers) || triggers.length === 0) return null;
  return (
    <div
      className="rounded-2xl border border-[#F1DEAF] bg-[#FFF8E8] px-4 py-3 mb-4"
      data-testid="regen-triggers-strip"
      role="region"
      aria-label="Why plan may change"
    >
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle className="h-4 w-4 text-[#6A4A09]" aria-hidden="true" />
        <span className="num-mono text-[10px] uppercase tracking-[0.18em] text-[#6A4A09] font-semibold">
          Why plan may change
        </span>
      </div>
      <ul className="space-y-1.5">
        {triggers.map((t, i) => (
          <li
            key={`${t.code || "regen"}-${i}`}
            className="flex items-start gap-2 text-[12.5px] text-clay-900"
            data-testid={`regen-trigger-${t.code}`}
          >
            <Pill tone={REGEN_SEVERITY_TONE[t.severity] || "outline"}>
              {t.severity || "info"}
            </Pill>
            <span className="leading-snug">
              <span className="font-semibold mr-1">
                {REGEN_TRIGGER_LABEL[t.code] || t.code}:
              </span>
              {t.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export { RegenTriggerStrip };

// Plan change log fed by /api/study/plan/changelog (study_adaptation_events).
// Each row is server-derived — the UI never re-derives event copy.

// Backend emits snake_case enums for these columns; the UI used to render
// them verbatim ("plan_regenerated", "weekly_correction_applied") which
// reads as developer debug. Map to human labels but keep the raw value as
// a fallback so a future enum still renders without code changes.
const EVENT_LABEL = {
  plan_regenerated: "Plan regenerated",
  plan_applied: "Plan applied",
  task_carry_forward: "Task carried forward",
  task_completed: "Task completed",
  task_status_changed: "Task status updated",
  weekly_correction_applied: "Weekly correction applied",
  correction_drafted: "Correction tasks drafted",
  correction_applied: "Correction added to plan",
  preferences_updated: "Plan settings updated",
};

const TRIGGER_LABEL = {
  user: "User action",
  user_action: "User action",
  scheduled: "Scheduled",
  weekly_review: "Report Card",
  auto_regenerate: "Auto-regenerate",
  admin: "Admin",
  engine: "Engine",
};

function humanize(value, dictionary) {
  if (!value) return "";
  return dictionary[value] || String(value).replaceAll("_", " ");
}

// Relative-time formatter. Two callers in different timezones reading the
// same shared screen used to see different locale-formatted strings with no
// timezone label, breaking the "auditable" promise of the panel. Relative
// values ("12 min ago") sidestep that entirely; we keep the ISO timestamp
// in `title` so a hover / screen reader still surfaces the precise instant.
function formatRelative(iso) {
  if (!iso) return { text: "", iso: "" };
  const then = new Date(iso);
  if (Number.isNaN(then.valueOf())) return { text: "", iso: "" };
  const diffMs = Date.now() - then.getTime();
  const sec = Math.round(diffMs / 1000);
  const future = sec < 0;
  const abs = Math.abs(sec);
  let text;
  if (abs < 60) text = `${abs}s`;
  else if (abs < 3600) text = `${Math.round(abs / 60)} min`;
  else if (abs < 86400) text = `${Math.round(abs / 3600)} h`;
  else if (abs < 2592000) text = `${Math.round(abs / 86400)} d`;
  else text = then.toLocaleDateString();
  return {
    text: future ? `in ${text}` : `${text} ago`,
    iso: then.toISOString(),
  };
}

export default function PlanChangeLogCard() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .get("/api/study/plan/changelog")
      .then((d) => {
        if (cancelled) return;
        setItems(Array.isArray(d?.items) ? d.items : []);
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setErr(e?.message || "Could not load change log");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Card padded={false} data-testid="plan-changelog">
      <div className="px-7 pt-6 pb-3 flex items-end justify-between gap-4">
        <div>
          <Eyebrow>Plan change log</Eyebrow>
          <h2 className="font-heading text-[18px] mt-1 flex items-center gap-2">
            <History className="h-4 w-4 text-clay-700" aria-hidden="true" />
            What the planner has done recently
          </h2>
        </div>
        <StatusDot state="live" label="" />
      </div>
      <div className="hairline mx-7" />
      <div className="px-7 py-4">
        {err ? (
          <p className="text-xs text-clay-700">{err}</p>
        ) : loading ? (
          <p className="text-xs text-clay-700">Loading…</p>
        ) : !items.length ? (
          <p className="text-xs text-clay-700">
            No plan mutations recorded yet. Apply a regeneration to see entries here.
          </p>
        ) : (
          <ul className="space-y-2.5">
            {items.map((row) => {
              const summary = row.change_summary || {};
              const rel = formatRelative(row.created_at);
              return (
                <li
                  key={row.id}
                  className="rounded-xl border border-[#E7DECB] bg-white/60 px-3.5 py-2.5"
                >
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2">
                      <Pill tone="ink" title={row.event_type}>
                        {humanize(row.event_type, EVENT_LABEL)}
                      </Pill>
                      {row.trigger_source ? (
                        <span
                          className="text-[10.5px] text-clay-700"
                          title={row.trigger_source}
                        >
                          {humanize(row.trigger_source, TRIGGER_LABEL)}
                        </span>
                      ) : null}
                    </div>
                    <span
                      className="num-mono text-[10.5px] text-clay-700"
                      title={rel.iso || undefined}
                    >
                      {rel.text}
                    </span>
                  </div>
                  {(summary.task_count != null || summary.version_number != null) ? (
                    <div className="mt-1.5 text-[12px] text-clay-800">
                      {summary.version_number != null ? `v${summary.version_number}` : null}
                      {summary.version_number != null && summary.task_count != null ? " · " : ""}
                      {summary.task_count != null ? `${summary.task_count} tasks` : null}
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Card>
  );
}
