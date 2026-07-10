import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../../../lib/api";
import QuestionRenderer from "./components/questions/QuestionRenderer";
import { errorTypeLabel } from "./errorTypeLabels";
import { getAttemptReturnContext } from "./attemptReturnContext";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "correct", label: "Correct" },
  { id: "wrong", label: "Wrong" },
  { id: "unattempted", label: "Unattempted" },
  { id: "option_trap", label: "Distractor trap" },
];

// Attach the original attempt-order number (1-based) to every question BEFORE
// filtering, so a filtered palette shows the real question number instead of a
// re-based filtered index.
function withOriginalNumbers(all) {
  return (all || []).map((q, i) => ({ ...q, _num: i + 1 }));
}

function applyFilter(all, filter) {
  if (filter === "all") return all;
  if (filter === "correct") return all.filter((q) => q.is_correct === true);
  if (filter === "wrong") return all.filter((q) => q.is_correct === false);
  if (filter === "unattempted") return all.filter((q) => !q.selected_option_id);
  return all.filter((q) => q.error_type === filter);
}

export default function MockReview() {
  const { attemptId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [idx, setIdx] = useState(0);

  const filter = searchParams.get("filter") || "all";
  const setFilter = (next) => {
    setSearchParams(next === "all" ? {} : { filter: next });
  };

  const returnCtx = useMemo(() => getAttemptReturnContext(attemptId), [attemptId]);

  useEffect(() => {
    let cancelled = false;
    api.get(`/api/study/mocks/attempts/${attemptId}/review`).then((d) => {
      if (!cancelled) setData(d);
    });
    return () => {
      cancelled = true;
    };
  }, [attemptId]);

  const numbered = useMemo(() => withOriginalNumbers(data?.questions || []), [data]);
  const questions = useMemo(() => applyFilter(numbered, filter), [numbered, filter]);

  // Clamp the active question whenever the filtered set changes (e.g. a new
  // filter shrinks the list below the current index).
  useEffect(() => {
    setIdx((cur) => (cur >= questions.length ? 0 : cur));
  }, [questions.length, filter]);

  if (!data) return <div>Loading…</div>;

  const current = questions[idx] || null;

  return (
    <div className="p-4 space-y-4" data-testid="review-page">
      {returnCtx ? (
        <Link
          to={returnCtx.return_to}
          data-testid="review-back-source"
          className="inline-flex items-center gap-1 text-sm text-clay-700 hover:underline"
        >
          ← {returnCtx.source_label}
        </Link>
      ) : null}

      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter questions">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            data-testid={`review-filter-${f.id}`}
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={`rounded border px-3 py-1 text-sm ${
              filter === f.id ? "bg-clay-900 text-white" : "bg-white"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="text-sm text-clay-700" data-testid="review-result-count">
        {questions.length} question{questions.length === 1 ? "" : "s"}
      </div>

      <div
        className="flex flex-wrap gap-2"
        role="group"
        aria-label="Question palette"
        data-testid="review-palette"
      >
        {questions.map((q, i) => (
          <button
            key={q.question_id}
            type="button"
            data-testid={`review-palette-item-${i}`}
            aria-current={i === idx}
            aria-label={`Question ${q._num}`}
            onClick={() => setIdx(i)}
            className={`h-8 w-8 rounded text-sm ${
              i === idx ? "ring-2 ring-clay-900" : ""
            } ${
              q.is_correct === true
                ? "bg-green-200"
                : q.is_correct === false
                ? "bg-red-200"
                : "bg-clay-100"
            }`}
          >
            {q._num}
          </button>
        ))}
      </div>

      {current ? (
        <div data-testid="review-question">
          <h3 className="font-heading text-lg">
            Q{current._num} · <span data-testid="review-error-label">{errorTypeLabel(current.error_type)}</span>
          </h3>
          <QuestionRenderer
            mode="review"
            showCorrect
            showExplanation
            question={{
              ...current.question_snapshot,
              selected_option_id: current.selected_option_id,
            }}
          />
          <div className="mt-3 flex justify-between">
            <button
              type="button"
              data-testid="review-prev"
              disabled={idx === 0}
              onClick={() => setIdx((i) => Math.max(0, i - 1))}
              className="rounded border px-3 py-1 disabled:opacity-40"
            >
              ← Prev
            </button>
            <button
              type="button"
              data-testid="review-next"
              disabled={idx >= questions.length - 1}
              onClick={() => setIdx((i) => Math.min(questions.length - 1, i + 1))}
              className="rounded border px-3 py-1 disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        </div>
      ) : (
        <div data-testid="review-empty" className="text-sm text-clay-700">
          No questions match this filter.
        </div>
      )}
    </div>
  );
}
