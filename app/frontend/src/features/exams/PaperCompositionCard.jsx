import React, { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChevronDown, ChevronRight, Layers } from "lucide-react";
import PropTypes from "prop-types";

import { api } from "../../lib/api";

/**
 * Paper composition — what ONE paper was made of, by topic.
 *
 * A different question from the reachability trend, off a different column, so
 * it carries its own eligibility: a paper qualifies here when its questions
 * carry verified primary topic tags, whether or not difficulty was ever
 * assessed. As of 2026-09-04 that excludes three of the four CSAT papers and
 * most of Mains, which render the empty state rather than an empty chart.
 *
 * HORIZONTAL BARS, NOT A PIE. A pie with twenty-plus microtopic slices is
 * unreadable, and these are counts of questions — not slices of a designed
 * whole. A paper's topic mix is what happened to be asked, not a budget someone
 * allocated, so nothing here should imply the parts were chosen to sum to one.
 *
 * TAG LEVEL IS STATED, NEVER ASSUMED. `topics` is a two-level tree and tags sit
 * at either level: the nine GS-I papers are tagged to microtopics, whereas 2025
 * CSAT's eighty tags are all top-level topics. A top-level breakdown built from
 * microtopic tags and one built from top-level tags look identical on screen
 * and mean different things, so the card says which it is showing.
 */

const PARENT_COLOR = "#54794E";
const CHILD_COLOR = "#94B28A";
const ROW_HEIGHT = 30;
const MIN_CHART_HEIGHT = 140;

const TAG_LEVEL_COPY = {
  microtopic:
    "Tagged at microtopic level — the finest level of the topic tree. " +
    "Microtopics are grouped under their parent topic below; expand a topic " +
    "to see them.",
  topic:
    "Tagged at top-level topic only, not at microtopic level. This is a " +
    "coarser breakdown than a microtopic-tagged paper's and the two are not " +
    "directly comparable.",
  mixed:
    "Tagged at a mix of top-level topics and microtopics. The two levels are " +
    "not equivalent, so a group built from a top-level tag is not the same " +
    "kind of count as one built from its microtopics.",
};

/**
 * Category axes key on the label string, so two topics that happen to share a
 * name would silently merge into one bar. Disambiguate rather than lose a row.
 */
function uniqueLabels(rows) {
  const seen = new Map();
  return rows.map((row) => {
    const base = row.label;
    const n = (seen.get(base) || 0) + 1;
    seen.set(base, n);
    return n === 1 ? row : { ...row, label: `${base} (${n})` };
  });
}

/**
 * Flatten the group tree into the rows the chart currently shows: every parent,
 * plus the children of the parents the reader has expanded.
 */
function visibleRows(groups, expanded) {
  const rows = [];
  groups.forEach((g) => {
    rows.push({
      key: g.topic_id,
      label: g.topic_name || g.topic_id,
      questions: g.questions,
      depth: 0,
    });
    if (expanded.has(g.topic_id)) {
      (g.children || []).forEach((c) => {
        rows.push({
          key: `${g.topic_id}:${c.topic_id}`,
          label: `› ${c.topic_name || c.topic_id}`,
          questions: c.questions,
          depth: 1,
        });
      });
    }
  });
  return uniqueLabels(rows);
}

function CardShell({ testId, children }) {
  return (
    <div className="soft-card rounded-2xl p-5" data-testid={testId}>
      <div className="flex items-center gap-2">
        <Layers className="h-4 w-4 text-clay-500" />
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground font-semibold">
            Paper composition · by topic
          </div>
          <div className="font-heading text-lg font-semibold mt-0.5">
            What this paper was made of
          </div>
        </div>
      </div>
      {children}
    </div>
  );
}

export default function PaperCompositionCard({ paperId = null, paperLabel = null }) {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(() => new Set());

  useEffect(() => {
    let cancelled = false;
    setExpanded(new Set());
    if (!paperId) {
      setPayload(null);
      return undefined;
    }
    setLoading(true);
    api
      .get(`/api/exam-intelligence/pyq-papers/${paperId}/composition`)
      .then((d) => {
        if (cancelled) return;
        setPayload(d);
        setError("");
      })
      .catch((e) => {
        if (cancelled) return;
        setPayload(null);
        setError(e?.message || "Failed to load the paper composition.");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [paperId]);

  const groups = useMemo(
    () => (Array.isArray(payload?.groups) ? payload.groups : []),
    [payload]
  );
  const rows = useMemo(() => visibleRows(groups, expanded), [groups, expanded]);
  const expandable = useMemo(
    () => groups.filter((g) => (g.children || []).length > 0),
    [groups]
  );

  if (!paperId) return null;

  if (loading) {
    return (
      <CardShell testId="paper-composition-loading">
        <div className="mt-4 text-sm text-muted-foreground" aria-busy="true">
          Loading the topic breakdown…
        </div>
      </CardShell>
    );
  }

  if (error) {
    return (
      <CardShell testId="paper-composition-error">
        <p className="mt-4 text-sm text-muted-foreground" role="alert">
          {error}
        </p>
      </CardShell>
    );
  }

  if (groups.length === 0) {
    return (
      <CardShell testId="paper-composition-empty">
        <p className="mt-4 text-sm text-muted-foreground">
          {paperLabel ? `${paperLabel} has ` : "This paper has "}
          no verified topic tags yet, so there is no breakdown to show. Tagging
          is per paper — a paper elsewhere in this exam may already be tagged.
        </p>
      </CardShell>
    );
  }

  const toggle = (id) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const allExpanded =
    expandable.length > 0 && expandable.every((g) => expanded.has(g.topic_id));

  const chartHeight = Math.max(MIN_CHART_HEIGHT, rows.length * ROW_HEIGHT + 32);
  const maxQuestions = rows.reduce((m, r) => Math.max(m, r.questions), 0);

  return (
    <CardShell testId="paper-composition-card">
      <p
        className="mt-3 text-xs leading-relaxed text-clay-700 bg-clay-50/70 border border-clay-100 rounded-lg px-3 py-2"
        data-testid="paper-composition-tag-level"
      >
        {TAG_LEVEL_COPY[payload.tag_level] || TAG_LEVEL_COPY.topic}
      </p>

      <div className="mt-2 text-xs text-muted-foreground" data-testid="paper-composition-counts">
        {payload.tagged_questions} of {payload.total_questions} verified
        questions carry a primary tag
        {payload.untagged_questions > 0
          ? ` · ${payload.untagged_questions} untagged`
          : ""}
        {payload.multi_tagged_questions > 0
          ? ` · ${payload.multi_tagged_questions} counted once despite multiple primary tags`
          : ""}
        .
      </div>

      <div
        className="mt-4"
        style={{ height: chartHeight }}
        data-testid="paper-composition-chart"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 4, right: 36, bottom: 4, left: 8 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#E8DFD3" horizontal={false} />
            <XAxis
              type="number"
              domain={[0, Math.max(1, maxQuestions)]}
              allowDecimals={false}
              stroke="#7A6A55"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={190}
              stroke="#7A6A55"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              interval={0}
            />
            <Tooltip formatter={(value) => [value, "Questions"]} />
            <Bar dataKey="questions" name="Questions" radius={[0, 3, 3, 0]}>
              {rows.map((r) => (
                <Cell key={r.key} fill={r.depth === 0 ? PARENT_COLOR : CHILD_COLOR} />
              ))}
              <LabelList
                dataKey="questions"
                position="right"
                style={{ fontSize: 11, fill: "#7A6A55" }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {expandable.length > 0 ? (
        <div className="mt-3">
          <div className="flex items-center justify-between">
            <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground font-semibold">
              Topics
            </div>
            <button
              type="button"
              className="text-xs text-clay-700 hover:underline rounded"
              onClick={() =>
                setExpanded(
                  allExpanded ? new Set() : new Set(expandable.map((g) => g.topic_id))
                )
              }
              data-testid="paper-composition-toggle-all"
            >
              {allExpanded ? "Collapse all" : "Expand all"}
            </button>
          </div>
          <ul className="mt-1.5 divide-y divide-clay-100">
            {groups.map((g) => {
              const children = g.children || [];
              const isOpen = expanded.has(g.topic_id);
              const name = g.topic_name || g.topic_id;
              if (children.length === 0) {
                return (
                  <li
                    key={g.topic_id}
                    className="py-1.5 text-xs text-muted-foreground flex items-center justify-between gap-3"
                  >
                    <span className="truncate">{name}</span>
                    <span className="shrink-0">{g.questions}</span>
                  </li>
                );
              }
              return (
                <li key={g.topic_id} className="py-0.5">
                  <button
                    type="button"
                    onClick={() => toggle(g.topic_id)}
                    aria-expanded={isOpen}
                    className="w-full flex items-center justify-between gap-3 py-1 text-xs text-left hover:text-clay-700 rounded"
                    data-testid={`paper-composition-expand-${g.topic_id}`}
                  >
                    <span className="flex items-center gap-1.5 min-w-0">
                      {isOpen ? (
                        <ChevronDown className="h-3.5 w-3.5 shrink-0" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 shrink-0" />
                      )}
                      <span className="truncate font-medium">{name}</span>
                      <span className="text-muted-foreground shrink-0">
                        · {children.length} microtopics
                      </span>
                    </span>
                    <span className="shrink-0 text-muted-foreground">{g.questions}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        Counts verified questions carrying a verified primary topic tag. A
        question is counted once, under one topic.
      </p>
    </CardShell>
  );
}

PaperCompositionCard.propTypes = {
  /** A verified pyq_paper id. Composition is per paper, never per exam. */
  paperId: PropTypes.string,
  /** Display name for the paper, used only in the empty state. */
  paperLabel: PropTypes.string,
};
