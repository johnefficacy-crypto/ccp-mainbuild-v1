import React, { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, Info } from "lucide-react";
import PropTypes from "prop-types";

import { api } from "../../lib/api";
import {
  BAND_COLOR,
  BAND_LABEL,
  PROVENANCE_LINE,
  PROVENANCE_SOURCE,
  REACHABILITY_BANDS,
  SHARED_MEASURE_LINE,
  Y_AXIS_LABEL,
  Y_AXIS_MAX,
  Y_AXIS_TICKS,
  reachabilityCopyFor,
} from "./reachabilityConfig";

/**
 * Reachability trend — how reachable each paper's questions were from standard
 * preparation, per band, per year.
 *
 * This is NOT a difficulty curve. No candidate response data exists for this
 * corpus; every question was read and classified against a fixed rubric. The
 * measure line, the band copy and the provenance note all exist to keep that
 * distinction in front of the reader, so none of them is optional and none is
 * behind a disclosure.
 *
 * Counts come from the reachability endpoint, which decides eligibility per
 * paper by computing it: every verified question must carry a non-NULL
 * observed_difficulty and the paper must hold more than one distinct band. An
 * exam whose corpus is entirely NULL (never assessed) or uniformly 'medium'
 * (the August 2026 bulk-import default) returns no papers and renders the empty
 * state, because charting either would be a chart of an import artefact dressed
 * as a finding. Only the per-exam editorial is local — see reachabilityConfig.
 *
 * Bands render as the stored `pyq_questions.observed_difficulty` enum —
 * Easy/Medium/Hard — with no display mapping layer. The Hard copy says
 * "not reachable", never "difficult".
 */

/**
 * Direct end-label for one series. The categorical palette clears the CVD
 * separation floor but not by a wide margin, so identity carries on the label
 * as well as the hue — never on color alone.
 */
function EndLabel({ x, y, value, index, total, band }) {
  if (index !== total - 1) return null;
  return (
    <text
      x={x + 8}
      y={y}
      dy={4}
      fontSize={11}
      fontWeight={600}
      fill={BAND_COLOR[band]}
      data-testid={`reachability-end-label-${band}`}
    >
      {BAND_LABEL[band]} {value}
    </text>
  );
}

function BandInfo({ band, copy }) {
  const [open, setOpen] = useState(false);
  const label = BAND_LABEL[band];
  return (
    <div className="flex items-start gap-2">
      <span
        aria-hidden="true"
        className="mt-1 h-2.5 w-2.5 rounded-full shrink-0"
        style={{ backgroundColor: BAND_COLOR[band] }}
      />
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold">{label}</span>
          <button
            type="button"
            aria-label={`What ${label} means`}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="text-muted-foreground hover:text-clay-700 rounded"
            data-testid={`reachability-info-${band}`}
          >
            <Info className="h-3.5 w-3.5" />
          </button>
        </div>
        {open ? (
          <p
            className="mt-1 text-[11px] leading-relaxed text-muted-foreground"
            data-testid={`reachability-info-copy-${band}`}
          >
            {copy}
          </p>
        ) : null}
      </div>
    </div>
  );
}

BandInfo.propTypes = {
  band: PropTypes.oneOf(REACHABILITY_BANDS).isRequired,
  copy: PropTypes.string.isRequired,
};

function CardShell({ testId, subtitle, children }) {
  return (
    <div className="soft-card rounded-2xl p-5" data-testid={testId}>
      <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground font-semibold">
        {subtitle}
      </div>
      <div className="font-heading text-lg font-semibold mt-0.5">
        Reachability trend
      </div>
      {children}
    </div>
  );
}

/**
 * The empty state names WHICH exclusion applied. "Not assessed" and "assessed
 * but uniform" are different facts about the corpus, and collapsing them into
 * "no data" hides that the second one has rows an operator might mistake for
 * results.
 */
function emptyReason(excluded) {
  const notAssessed = excluded?.not_assessed || 0;
  const uniform = excluded?.uniform || 0;
  if (uniform > 0 && notAssessed === 0) {
    return (
      "Its papers carry a single difficulty value across every question — the " +
      "bulk-import default, not a judgement — so there is nothing to plot."
    );
  }
  if (uniform > 0) {
    return (
      "Its papers have either not been read against the reachability rubric, " +
      "or carry a single bulk-imported difficulty value across every " +
      "question, so there is nothing to plot."
    );
  }
  return (
    "Its papers have not yet been read against the reachability rubric, so " +
    "there is nothing to plot."
  );
}

export default function ReachabilityTrendCard({ examSlug = null, phaseId = null }) {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (!examSlug) {
      setPayload(null);
      return undefined;
    }
    setLoading(true);
    const qs = phaseId ? `?phase_id=${encodeURIComponent(phaseId)}` : "";
    api
      .get(`/api/exam-intelligence/exams/${examSlug}/reachability${qs}`)
      .then((d) => {
        if (cancelled) return;
        setPayload(d);
        setError("");
      })
      .catch((e) => {
        if (cancelled) return;
        setPayload(null);
        setError(e?.message || "Failed to load the reachability trend.");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [examSlug, phaseId]);

  const copy = useMemo(() => reachabilityCopyFor(examSlug), [examSlug]);
  const rows = useMemo(() => {
    const papers = payload?.papers;
    return Array.isArray(papers) ? papers : [];
  }, [payload]);

  if (!examSlug) return null;

  if (loading) {
    return (
      <CardShell
        testId="reachability-trend-loading"
        subtitle="Question reachability · by paper"
      >
        <div className="mt-4 text-sm text-muted-foreground" aria-busy="true">
          Loading the reachability trend…
        </div>
      </CardShell>
    );
  }

  if (error) {
    return (
      <CardShell
        testId="reachability-trend-error"
        subtitle="Question reachability · by paper"
      >
        <p className="mt-4 text-sm text-muted-foreground" role="alert">
          {error}
        </p>
      </CardShell>
    );
  }

  // No assessed papers for this exam. The corpus almost certainly HAS rows for
  // it — bulk-defaulted to 'medium' at import, or never assessed at all — and
  // charting those would be a chart of the import default dressed as a finding.
  if (rows.length === 0) {
    return (
      <CardShell
        testId="reachability-trend-empty"
        subtitle="Question reachability · by paper"
      >
        <div className="mt-4 flex items-start gap-3">
          <BarChart3 className="h-5 w-5 text-clay-500 shrink-0" />
          <p className="text-sm text-muted-foreground">
            Difficulty assessment is pending for this exam.{" "}
            {emptyReason(payload?.excluded)} {SHARED_MEASURE_LINE}
          </p>
        </div>
      </CardShell>
    );
  }

  const lastIndex = rows.length - 1;
  const xDomainStart = rows[0].year;
  const xDomainEnd = rows[lastIndex].year;
  // The prose is editorial, written against a corpus of a known size. If the
  // endpoint now returns a different number of papers, say so rather than
  // letting stale sentences sit silently under fresh counts.
  const proseStale =
    copy.analysis &&
    copy.analysisPaperCount != null &&
    copy.analysisPaperCount !== rows.length;

  return (
    <div className="soft-card rounded-2xl p-5" data-testid="reachability-trend-card">
      <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground font-semibold">
        Question reachability · {copy.seriesLabel} · {rows.length} assessed papers
      </div>
      <div className="font-heading text-lg font-semibold mt-0.5">
        Reachability trend
      </div>

      <div className="mt-4 grid lg:grid-cols-[minmax(0,1fr)_15rem] gap-4">
        <div className="h-72" data-testid="reachability-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ top: 8, right: 78, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E8DFD3" vertical={false} />
              {/* Numeric, not categorical. The series can skip a year whenever
                  a paper is unassessed, and a category axis would draw a
                  two-year gap the same width as a one-year step, overstating
                  how fast the trend moved. A number axis puts each paper at its
                  true distance. */}
              <XAxis
                dataKey="year"
                type="number"
                domain={[xDomainStart, xDomainEnd]}
                ticks={rows.map((r) => r.year)}
                allowDecimals={false}
                stroke="#7A6A55"
                fontSize={11}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[0, Y_AXIS_MAX]}
                // Without explicit ticks the 0-65 domain ends on an uneven
                // 40 → 65 step, which reads as a broken scale.
                ticks={Y_AXIS_TICKS}
                stroke="#7A6A55"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                label={{
                  value: Y_AXIS_LABEL,
                  angle: -90,
                  position: "insideLeft",
                  style: { fontSize: 11, fill: "#7A6A55" },
                }}
              />
              <Tooltip
                formatter={(value, key) => [value, BAND_LABEL[key] || key]}
                labelFormatter={(y) => `${y} paper`}
              />
              <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              {REACHABILITY_BANDS.map((band) => (
                <Line
                  key={band}
                  type="monotone"
                  dataKey={band}
                  name={BAND_LABEL[band]}
                  stroke={BAND_COLOR[band]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                >
                  <LabelList
                    dataKey={band}
                    content={(props) => (
                      <EndLabel {...props} total={lastIndex + 1} band={band} />
                    )}
                  />
                </Line>
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="space-y-3">
          <p
            className="text-xs leading-relaxed text-muted-foreground"
            data-testid="reachability-measure-line"
          >
            {SHARED_MEASURE_LINE}
          </p>
          <div className="space-y-2.5 pt-1">
            {REACHABILITY_BANDS.map((band) => (
              <BandInfo key={band} band={band} copy={copy.bandCopy[band]} />
            ))}
          </div>
        </div>
      </div>

      {copy.analysis ? (
        <div
          className="mt-5 space-y-3 text-sm leading-relaxed text-muted-foreground"
          data-testid="reachability-analysis"
        >
          {copy.analysis.map((para) => (
            <p key={para.slice(0, 40)}>{para}</p>
          ))}
          {proseStale ? (
            <p
              className="text-[11px] text-clay-700"
              data-testid="reachability-analysis-stale"
            >
              Written against {copy.analysisPaperCount} papers; {rows.length} are
              now assessed. The figures quoted above have not been revisited.
            </p>
          ) : null}
        </div>
      ) : null}

      {copy.caveat ? (
        <p
          className="mt-4 text-xs leading-relaxed text-clay-700 bg-clay-50/70 border border-clay-100 rounded-lg px-3 py-2"
          data-testid="reachability-caveat"
        >
          {copy.caveat}
        </p>
      ) : null}

      <p
        className="mt-3 text-[11px] leading-relaxed text-muted-foreground"
        data-testid="reachability-provenance"
      >
        {PROVENANCE_LINE}{" "}
        <span className="font-mono text-[10px]">{PROVENANCE_SOURCE}</span>
      </p>
    </div>
  );
}

ReachabilityTrendCard.propTypes = {
  /** Exam slug. Resolved server-side; counts are never held in the frontend. */
  examSlug: PropTypes.string,
  /**
   * Optional narrowing filter. Read the phase-scoping note in
   * reachabilityConfig.js first — `exam_phases` has no unique constraint and
   * UPSC's nine assessed papers span two phase ids, so passing one here splits
   * a continuous series.
   */
  phaseId: PropTypes.string,
};
