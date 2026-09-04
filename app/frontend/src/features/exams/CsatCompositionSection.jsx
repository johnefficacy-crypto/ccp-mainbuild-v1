import React, { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3 } from "lucide-react";
import PropTypes from "prop-types";

import { api } from "../../lib/api";
import {
  DEFAULT_SUBJECT_ID,
  OVERALL_VISIBLE_TOPICS,
  PROVENANCE_LINE,
  QUANT_VISIBLE_TOPICS,
  TRUNCATED_SUBJECTS,
  csatAnalysis,
  paperLabel,
  subjectColor,
  subjectSplitRows,
  taggedPapers,
  topicRows,
  untaggedPapers,
} from "./csatCompositionConfig";

/**
 * CSAT composition — what each CSAT paper was made of, by topic.
 *
 * A DIFFERENT CHART FROM THE REACHABILITY TREND, not a second view of it. That
 * trend measures how reachable a question was from standard preparation, on a
 * rubric written for UPSC GS-I; it does not carry over to a percentages
 * question, and CSAT's stored observed_difficulty was assigned by keyword rule
 * rather than judged against any rubric. So CSAT is excluded from that chart,
 * and this section presents no difficulty at all: no band, no scale, no
 * derived label anywhere in it. A test asserts that absence, because a
 * difficulty word appearing here would quietly re-attach a rubric this corpus
 * was never read against.
 *
 * HORIZONTAL BARS, NEVER A PIE. Forty-odd topics is forty-odd slices, which is
 * unreadable, and the finding here is a RANKING — which topics recur and how
 * often — not a set of proportions of a designed whole. These papers were not
 * budgeted to sum to one; the counts are what happened to be asked.
 *
 * PER-YEAR COUNTS ARE THE FINDING, NOT DECORATION. The topic bars stack by
 * paper rather than showing one total, because a topic that ran 16, 8, 16, 8
 * and one that ran 12, 12, 12, 12 aggregate identically and only one of them is
 * a paper alternating between two shapes. The strip under each bar restates
 * those per-year counts as text, so the alternation survives without hover.
 */

const ROW_HEIGHT = 30;
const MIN_CHART_HEIGHT = 150;

function chartHeight(rowCount) {
  return Math.max(MIN_CHART_HEIGHT, rowCount * ROW_HEIGHT + 40);
}

function SectionShell({ testId, children }) {
  return (
    <div className="soft-card rounded-2xl p-5" data-testid={testId}>
      <div className="flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-clay-500" />
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground font-semibold">
            CSAT composition · by topic
          </div>
          <div className="font-heading text-lg font-semibold mt-0.5">
            What each CSAT paper was made of
          </div>
        </div>
      </div>
      {/* Provenance renders with the section, unconditionally — in the loading,
          error, empty and populated states alike. */}
      <p
        className="mt-3 text-xs leading-relaxed text-clay-700 bg-clay-50/70 border border-clay-100 rounded-lg px-3 py-2"
        data-testid="csat-composition-provenance"
      >
        {PROVENANCE_LINE}
      </p>
      {children}
    </div>
  );
}

/**
 * One horizontal bar per row, stacked by paper. `series` is the paper columns;
 * `colorFor` decides a row's colour when the stack is a single series.
 */
function StackedBars({ rows, series, colorOf, testId, height }) {
  // A legend for a single unnamed series is noise; the axis already labels it.
  const showLegend = series.length > 1;
  const max = rows.reduce((m, r) => Math.max(m, r.total), 0);
  return (
    <div className="mt-3" style={{ height }} data-testid={testId}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 4, right: 44, bottom: 4, left: 8 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E8DFD3" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, Math.max(1, max)]}
            allowDecimals={false}
            stroke="#7A6A55"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={210}
            stroke="#7A6A55"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            interval={0}
          />
          <Tooltip formatter={(value, key) => [value, key]} />
          {showLegend ? <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} /> : null}
          {series.map((s, i) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.name}
              stackId="composition"
              fill={s.color}
              radius={i === series.length - 1 ? [0, 3, 3, 0] : undefined}
            >
              {colorOf
                ? rows.map((r) => <Cell key={r.key} fill={colorOf(r)} />)
                : null}
              {i === series.length - 1 ? (
                <LabelList
                  dataKey="total"
                  position="right"
                  style={{ fontSize: 11, fill: "#7A6A55" }}
                />
              ) : null}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * The subject-split strip. Restates each paper's bar as text for the same
 * reason the topic strip does: the counts are the finding, and they should not
 * live only in chart geometry.
 */
function SplitStrip({ rows, subjects }) {
  return (
    <ul className="mt-2 divide-y divide-clay-100" data-testid="csat-subject-split-strip">
      {rows.map((r) => (
        <li
          key={r.key}
          className="py-1.5 flex items-baseline justify-between gap-3 text-xs"
          data-testid={`csat-subject-split-row-${r.key}`}
        >
          <span className="font-medium">{r.label}</span>
          <span className="shrink-0 text-muted-foreground tabular-nums">
            {subjects.map((s) => `${s.name} ${r[s.subject_id] || 0}`).join(" · ")}
            <span className="ml-2 font-semibold text-clay-700">{r.total}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

/**
 * The per-year strip. Restates each bar's per-paper counts as text so the
 * year-on-year movement is readable without hovering, and so it survives into
 * a screen reader rather than living only in chart geometry.
 */
function TopicStrip({ rows, testIdPrefix }) {
  return (
    <ul className="mt-2 divide-y divide-clay-100" data-testid={`${testIdPrefix}-strip`}>
      {rows.map((r) => (
        <li
          key={r.key}
          className="py-1.5 flex items-baseline justify-between gap-3 text-xs"
          data-testid={`${testIdPrefix}-row-${r.key}`}
        >
          <span className="min-w-0 flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className="h-2 w-2 rounded-full shrink-0"
              style={{ backgroundColor: subjectColor(r.subjectId) }}
            />
            <span className="truncate">{r.label}</span>
          </span>
          <span className="shrink-0 text-muted-foreground tabular-nums">
            {r.perPaper.map((c) => `${c.label} ${c.count}`).join(" · ")}
            <span className="ml-2 font-semibold text-clay-700">{r.total}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

function ShowAll({ shown, total, expanded, onToggle, testId }) {
  if (total <= shown && !expanded) return null;
  return (
    <button
      type="button"
      onClick={onToggle}
      className="mt-2 text-xs text-clay-700 hover:underline rounded"
      data-testid={testId}
    >
      {expanded ? `Show top ${shown}` : `Show all ${total}`}
    </button>
  );
}

export default function CsatCompositionSection({ examSlug = null }) {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeSubject, setActiveSubject] = useState(null);
  const [subjectExpanded, setSubjectExpanded] = useState(false);
  const [overallExpanded, setOverallExpanded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setActiveSubject(null);
    setSubjectExpanded(false);
    setOverallExpanded(false);
    if (!examSlug) {
      setPayload(null);
      return undefined;
    }
    setLoading(true);
    api
      .get(`/api/exam-intelligence/exams/${examSlug}/csat-composition`)
      .then((d) => {
        if (cancelled) return;
        setPayload(d);
        setError("");
      })
      .catch((e) => {
        if (cancelled) return;
        setPayload(null);
        setError(e?.message || "Failed to load the CSAT composition.");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [examSlug]);

  const papers = useMemo(
    () => (Array.isArray(payload?.papers) ? payload.papers : []),
    [payload]
  );
  const subjects = useMemo(
    () => (Array.isArray(payload?.subjects) ? payload.subjects : []),
    [payload]
  );
  const drawable = useMemo(() => taggedPapers(papers), [papers]);
  const pending = useMemo(() => untaggedPapers(papers), [papers]);

  const subjectId =
    activeSubject ||
    (subjects.some((s) => s.subject_id === DEFAULT_SUBJECT_ID)
      ? DEFAULT_SUBJECT_ID
      : subjects[0]?.subject_id) ||
    null;

  const splitRows = useMemo(
    () => subjectSplitRows(papers, subjects),
    [papers, subjects]
  );
  const subjectTopics = useMemo(
    () => topicRows(payload?.topics, subjectId, papers),
    [payload, subjectId, papers]
  );
  const overallTopics = useMemo(
    () => topicRows(payload?.topics, null, papers),
    [payload, papers]
  );
  const analysis = useMemo(() => csatAnalysis(payload), [payload]);

  if (!examSlug) return null;

  if (loading) {
    return (
      <SectionShell testId="csat-composition-loading">
        <div className="mt-4 text-sm text-muted-foreground" aria-busy="true">
          Loading the CSAT topic breakdown…
        </div>
      </SectionShell>
    );
  }

  if (error) {
    return (
      <SectionShell testId="csat-composition-error">
        <p className="mt-4 text-sm text-muted-foreground" role="alert">
          {error}
        </p>
      </SectionShell>
    );
  }

  // No CSAT paper qualifies for this exam at all — not a chart with nothing in
  // it, not an empty state, but no section. An exam without a CSAT series
  // should not carry a heading claiming one.
  if (papers.length === 0) return null;

  const paperSeries = drawable.map((p) => ({
    key: p.paper_id,
    name: paperLabel(p),
    color: null,
  }));
  const subjectSeries = subjects.map((s) => ({
    key: s.subject_id,
    name: s.name || s.subject_id,
    color: subjectColor(s.subject_id),
  }));

  // Only the long subject truncates. Reasoning and English are short enough to
  // show whole, and a "show all" control over a list that is already whole is
  // a control that does nothing.
  const truncates = TRUNCATED_SUBJECTS.has(subjectId);
  const shownSubjectTopics =
    truncates && !subjectExpanded
      ? subjectTopics.slice(0, QUANT_VISIBLE_TOPICS)
      : subjectTopics;
  const shownOverall = overallExpanded
    ? overallTopics
    : overallTopics.slice(0, OVERALL_VISIBLE_TOPICS);

  return (
    <SectionShell testId="csat-composition-section">
      <div className="mt-2 text-xs text-muted-foreground" data-testid="csat-composition-counts">
        {drawable.length} papers · {drawable.reduce((n, p) => n + p.tagged_questions, 0)}{" "}
        questions carrying a primary topic tag · {overallTopics.length} distinct
        topics.
      </div>

      {pending.length > 0 ? (
        <p
          className="mt-2 text-xs text-muted-foreground"
          data-testid="csat-composition-untagged-papers"
        >
          {pending.map((p) => paperLabel(p)).join(", ")}{" "}
          {pending.length === 1 ? "carries" : "carry"} no primary topic tags yet,
          so {pending.length === 1 ? "it is" : "they are"} not broken down here.
          Tagging is per paper.
        </p>
      ) : null}

      {drawable.length === 0 ? null : (
        <>
          {/* View 1 — subject split, one bar per paper. */}
          <div className="mt-5">
            <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground font-semibold">
              Subject split, by paper
            </div>
            <StackedBars
              rows={splitRows}
              series={subjectSeries}
              testId="csat-subject-split-chart"
              height={chartHeight(splitRows.length)}
            />
            <SplitStrip rows={splitRows} subjects={subjects} />
          </div>

          {/* View 2 — topics WITHIN one subject, per-year counts kept visible. */}
          <div className="mt-6">
            <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground font-semibold">
              Topics within a subject
            </div>
            <div
              className="mt-2 flex flex-wrap gap-1.5"
              role="tablist"
              aria-label="Subject"
            >
              {subjects.map((s) => {
                const selected = s.subject_id === subjectId;
                return (
                  <button
                    key={s.subject_id}
                    type="button"
                    role="tab"
                    aria-selected={selected}
                    onClick={() => {
                      setActiveSubject(s.subject_id);
                      setSubjectExpanded(false);
                    }}
                    className={`rounded-full border px-3 py-1 text-xs ${
                      selected
                        ? "border-clay-300 bg-clay-100 font-semibold text-clay-800"
                        : "border-clay-200 text-muted-foreground hover:text-clay-700"
                    }`}
                    data-testid={`csat-subject-tab-${s.subject_id}`}
                  >
                    {s.name || s.subject_id}
                  </button>
                );
              })}
            </div>
            <StackedBars
              rows={shownSubjectTopics}
              series={paperSeries.map((s, i) => ({
                ...s,
                color: `rgba(84, 121, 78, ${0.35 + i * 0.2})`,
              }))}
              testId="csat-subject-topics-chart"
              height={chartHeight(shownSubjectTopics.length)}
            />
            <TopicStrip rows={shownSubjectTopics} testIdPrefix="csat-subject-topic" />
            {truncates ? (
              <ShowAll
                shown={QUANT_VISIBLE_TOPICS}
                total={subjectTopics.length}
                expanded={subjectExpanded}
                onToggle={() => setSubjectExpanded((v) => !v)}
                testId="csat-subject-topics-show-all"
              />
            ) : null}
          </div>

          {/* View 3 — the ranking across every subject and every paper. */}
          <div className="mt-6">
            <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground font-semibold">
              Most-tested topics overall
            </div>
            <StackedBars
              rows={shownOverall}
              series={[{ key: "total", name: "Questions", color: null }]}
              colorOf={(r) => subjectColor(r.subjectId)}
              testId="csat-overall-topics-chart"
              height={chartHeight(shownOverall.length)}
            />
            <TopicStrip rows={shownOverall} testIdPrefix="csat-overall-topic" />
            <ShowAll
              shown={OVERALL_VISIBLE_TOPICS}
              total={overallTopics.length}
              expanded={overallExpanded}
              onToggle={() => setOverallExpanded((v) => !v)}
              testId="csat-overall-topics-show-all"
            />
          </div>
        </>
      )}

      {analysis.length > 0 ? (
        <div
          className="mt-6 space-y-3 text-sm leading-relaxed text-muted-foreground"
          data-testid="csat-composition-analysis"
        >
          {analysis.map((para) => (
            <p key={para.slice(0, 48)}>{para}</p>
          ))}
        </div>
      ) : null}
    </SectionShell>
  );
}

CsatCompositionSection.propTypes = {
  /**
   * Exam slug. The series is resolved server-side by the subject of each
   * question's primary tag — never by exam_phase_id, because the four CSAT
   * papers sit on three different phases.
   */
  examSlug: PropTypes.string,
};

StackedBars.propTypes = {
  rows: PropTypes.arrayOf(PropTypes.object).isRequired,
  series: PropTypes.arrayOf(PropTypes.object).isRequired,
  colorOf: PropTypes.func,
  testId: PropTypes.string.isRequired,
  height: PropTypes.number.isRequired,
};

SplitStrip.propTypes = {
  rows: PropTypes.arrayOf(PropTypes.object).isRequired,
  subjects: PropTypes.arrayOf(PropTypes.object).isRequired,
};

TopicStrip.propTypes = {
  rows: PropTypes.arrayOf(PropTypes.object).isRequired,
  testIdPrefix: PropTypes.string.isRequired,
};

ShowAll.propTypes = {
  shown: PropTypes.number.isRequired,
  total: PropTypes.number.isRequired,
  expanded: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  testId: PropTypes.string.isRequired,
};
