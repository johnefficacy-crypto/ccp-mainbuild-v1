import React from "react";
import PropTypes from "prop-types";

import MathRenderer from "../../../pages/study/mocks/components/questions/shared/MathRenderer";

/**
 * A single strategy card in a personalized Improvement Lab feed (GQR-S6).
 *
 * Renders the shared learner Solution-Strategy DTO plus the bounded practice
 * evidence the feed aggregates (times seen / missed / correct). Subject-agnostic:
 * the same DTO covers Quant (Methods & Shortcuts) and Reasoning (Approaches &
 * Patterns). Read-only; no governance fields are ever present in the payload.
 */

const DETAIL_ROWS = [
  ["standard_method", "Standard method"],
  ["faster_method", "Faster method"],
  ["key_observation", "Key observation"],
  ["common_traps", "Watch out for"],
];

// `formula_latex` is raw LaTeX; MathRenderer keys off `$…$`/`$$…$$`, so wrap a
// bare formula. An already-delimited string passes through untouched.
function asMath(latex) {
  const s = (latex || "").trim();
  if (!s) return "";
  return /\$[^$]+\$/.test(s) ? s : `$$${s}$$`;
}

function fmtDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleDateString();
}

export default function StrategyFeedCard({ strategy: s }) {
  const seen = s.times_seen ?? 0;
  const missed = s.wrong_count ?? 0;
  const correct = s.correct_count ?? 0;
  const lastSeen = fmtDate(s.last_seen_at);

  return (
    <div
      className="mt-3 rounded border border-slate-200 bg-white p-3"
      data-testid={`strategy-feed-card-${s.id}`}
    >
      <div className="flex flex-wrap items-baseline gap-x-2">
        <span className="font-medium text-slate-900">{s.name}</span>
        {s.strategy_type ? (
          <span className="text-xs text-slate-500">· {String(s.strategy_type).replaceAll("_", " ")}</span>
        ) : null}
      </div>

      <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-600" data-testid={`strategy-feed-evidence-${s.id}`}>
        <span>Seen {seen}</span>
        <span className={missed > 0 ? "font-medium text-red-600" : ""}>Missed {missed}</span>
        <span>Correct {correct}</span>
        {lastSeen ? <span className="text-slate-400">Last seen {lastSeen}</span> : null}
      </div>

      {s.formula_latex ? (
        <div className="mt-2" data-testid={`strategy-feed-formula-${s.id}`}>
          <MathRenderer text={asMath(s.formula_latex)} />
        </div>
      ) : null}

      {DETAIL_ROWS.map(([key, label]) =>
        s[key] ? (
          <div key={key} className="mt-2" data-testid={`strategy-feed-${s.id}-${key}`}>
            <div className="text-xs font-semibold text-slate-500">{label}</div>
            <p className="whitespace-pre-wrap text-sm text-slate-800">{s[key]}</p>
          </div>
        ) : null,
      )}
    </div>
  );
}

StrategyFeedCard.propTypes = {
  strategy: PropTypes.shape({
    id: PropTypes.string,
    name: PropTypes.string,
    strategy_type: PropTypes.string,
    formula_latex: PropTypes.string,
    standard_method: PropTypes.string,
    faster_method: PropTypes.string,
    key_observation: PropTypes.string,
    common_traps: PropTypes.string,
    times_seen: PropTypes.number,
    wrong_count: PropTypes.number,
    correct_count: PropTypes.number,
    last_seen_at: PropTypes.string,
  }).isRequired,
};
