import React, { useEffect, useMemo, useRef, useState } from "react";
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

// Attach the original attempt-order number to every question BEFORE filtering,
// so a filtered palette shows the real question number instead of a re-based
// filtered index. The number comes from the backend's immutable `attempt_order`
// (frozen from `template_snapshot.question_ids`); the row index is only a
// last-resort fallback for older payloads without the field.
function withOriginalNumbers(all) {
  return (all || []).map((q, i) => ({ ...q, _num: q.attempt_order ?? i + 1 }));
}

function applyFilter(all, filter) {
  if (filter === "all") return all;
  if (filter === "correct") return all.filter((q) => q.is_correct === true);
  if (filter === "wrong") return all.filter((q) => q.is_correct === false);
  if (filter === "unattempted") return all.filter((q) => !q.selected_option_id && q.numeric_answer == null);
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

  // ── keyboard navigation (bound once; latest state via ref) ─────────────────
  const navRef = useRef({});
  navRef.current = { idx, count: questions.length };
  useEffect(() => {
    function onKey(e) {
      const t = e.target;
      const tag = (t?.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select" || t?.isContentEditable) return;
      const { count } = navRef.current;
      if (e.key === "Escape") {
        if (document.activeElement && typeof document.activeElement.blur === "function") {
          document.activeElement.blur();
        }
        return;
      }
      if (e.key === "ArrowRight" || e.key === "j" || e.key === "J") {
        e.preventDefault();
        setIdx((i) => Math.min(count - 1, i + 1));
        return;
      }
      if (e.key === "ArrowLeft" || e.key === "k" || e.key === "K") {
        e.preventDefault();
        setIdx((i) => Math.max(0, i - 1));
        return;
      }
      if (/^[1-9]$/.test(e.key)) {
        const target = Number(e.key) - 1;
        if (target < count) {
          e.preventDefault();
          setIdx(target);
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!data) return <div>Loading…</div>;

  const current = questions[idx] || null;

  return (
    <div className="p-4 pb-20 space-y-4" data-testid="review-page">
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
              // Integer/numerical: the learner's typed value overrides the
              // snapshot's numeric_answer spec; expose the correct value +
              // tolerance under explicit keys for the review renderer.
              numeric_answer: current.numeric_answer,
              correct_numeric_answer: current.question_snapshot?.numeric_answer?.value ?? null,
              numeric_tolerance: current.question_snapshot?.numeric_answer?.tolerance ?? null,
            }}
          />
        </div>
      ) : (
        <div data-testid="review-empty" className="text-sm text-clay-700">
          No questions match this filter.
        </div>
      )}

      {/* Sticky footer action bar — stays put regardless of stem length. */}
      <div
        data-testid="review-footer"
        className="fixed bottom-0 left-0 right-0 lg:left-64 z-30 flex items-center justify-between gap-3 border-t border-border bg-[#FBF6EF]/95 backdrop-blur px-4 py-3"
      >
        <button
          type="button"
          data-testid="review-prev"
          disabled={idx === 0 || !current}
          onClick={() => setIdx((i) => Math.max(0, i - 1))}
          className="rounded border px-3 py-1 disabled:opacity-40"
        >
          ← Prev
        </button>
        {current ? (
          <span className="text-xs text-muted-foreground">
            Question {current._num}
          </span>
        ) : null}
        <div className="flex items-center gap-2">
          {returnCtx ? (
            <Link
              to={returnCtx.return_to}
              data-testid="review-footer-back"
              className="rounded border px-3 py-1 text-sm hover:bg-clay-100"
            >
              {returnCtx.source_label}
            </Link>
          ) : null}
          <button
            type="button"
            data-testid="review-next"
            disabled={idx >= questions.length - 1 || !current}
            onClick={() => setIdx((i) => Math.min(questions.length - 1, i + 1))}
            className="rounded border px-3 py-1 disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}
