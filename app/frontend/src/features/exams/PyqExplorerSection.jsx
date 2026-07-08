import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronUp, Search } from "lucide-react";
import { api } from "../../lib/api";
import useApiAction from "../../lib/hooks/useApiAction";

const DIFFICULTY_OPTIONS = [
  { value: "", label: "Any difficulty" },
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
  { value: "unknown", label: "Unknown" },
];

const SOURCE_OPTIONS = [
  { value: "", label: "Any source" },
  { value: "official", label: "Official" },
  { value: "memory_based", label: "Memory-based" },
  { value: "coaching", label: "Coaching" },
  { value: "community", label: "Community" },
  { value: "aggregator", label: "Aggregator" },
];

function FilterSelect({ label, value, onChange, options }) {
  return (
    <label className="flex flex-col gap-1 min-w-0">
      <span className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-clay-200 bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-clay-400"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function QuestionCard({ q, onPractice, practicing, practiceDisabled }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="rounded-xl border border-clay-100 bg-white p-4 space-y-2"
      data-testid="pyq-question-card"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          {q.paper_year ? (
            <span className="pill pill-clay text-[11px]">{q.paper_year}</span>
          ) : null}
          {q.shift ? (
            <span className="pill pill-clay text-[11px]">Shift {q.shift}</span>
          ) : null}
          {q.difficulty && q.difficulty !== "unknown" ? (
            <span className="pill pill-dusk text-[11px] capitalize">{q.difficulty}</span>
          ) : null}
          {q.source_type ? (
            <span className="pill pill-sage text-[11px]">{q.source_type}</span>
          ) : null}
          {q.question_number != null ? (
            <span className="text-[11px] text-muted-foreground">Q{q.question_number}</span>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="shrink-0 text-clay-600 hover:text-clay-900"
          aria-label={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      <p className="text-sm leading-relaxed">{q.question_text || "—"}</p>

      {q.paper_id ? (
        <div className="pt-0.5">
          <button
            type="button"
            onClick={() => onPractice(q.paper_id)}
            disabled={practiceDisabled}
            className="btn btn-ghost text-xs disabled:opacity-40"
            data-testid="pyq-practice-paper-btn"
            title="Start a practice attempt over this paper's verified questions"
          >
            {practicing ? "Starting…" : "Practice this paper"}
          </button>
        </div>
      ) : null}

      {expanded && (
        <div className="mt-2 space-y-1.5">
          {q.options.length > 0 && (
            <ul className="space-y-1">
              {q.options.map((opt) => (
                <li
                  key={opt.id}
                  className={`flex items-start gap-2 text-sm rounded-lg px-3 py-1.5 ${
                    opt.is_correct
                      ? "bg-sage-50 border border-sage-200 text-sage-900"
                      : "bg-clay-50/60 border border-clay-100"
                  }`}
                >
                  <span className="font-semibold shrink-0">{opt.label}.</span>
                  <span>{opt.text}</span>
                  {opt.is_correct && (
                    <span className="ml-auto shrink-0 text-[10px] uppercase tracking-wide text-sage-700 font-semibold">
                      Correct
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
          {q.explanation ? (
            <div className="rounded-lg bg-clay-50 border border-clay-100 px-3 py-2 text-xs text-muted-foreground">
              <span className="font-semibold text-clay-800">Explanation: </span>
              {q.explanation}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export default function PyqExplorerSection({ examSlug }) {
  const navigate = useNavigate();
  const { run, busy } = useApiAction();
  const [year, setYear] = useState("");
  const [phase, setPhase] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [page, setPage] = useState(1);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Practice launcher (PYQ v2 PR-5/6 slice C): start a practice attempt over a
  // paper's verified, projected questions and hand off to the existing attempt
  // shell. Not every listed paper is projected to the mock bank yet, so a 409
  // (empty pool) is an expected, gracefully-handled state.
  const [practicingPaperId, setPracticingPaperId] = useState(null);
  const [practiceError, setPracticeError] = useState("");

  // Available years derived from first load (no filter)
  const [availableYears, setAvailableYears] = useState([]);
  const yearsLoaded = useRef(false);

  const debouncedYear = useDebounce(year, 300);

  const buildUrl = useCallback(
    (overrides = {}) => {
      const p = new URLSearchParams();
      const cfg = { page, page_size: 20, ...overrides };
      p.set("page", cfg.page ?? page);
      p.set("page_size", cfg.page_size ?? 20);
      if (debouncedYear) p.set("year", debouncedYear);
      if (phase) p.set("phase", phase);
      if (difficulty) p.set("difficulty", difficulty);
      if (sourceType) p.set("source_type", sourceType);
      return `/api/exam-intelligence/exams/${examSlug}/pyqs?${p.toString()}`;
    },
    [examSlug, page, debouncedYear, phase, difficulty, sourceType]
  );

  useEffect(() => {
    if (!examSlug || yearsLoaded.current) return;
    yearsLoaded.current = true;
    api
      .get(`/api/exam-intelligence/exams/${examSlug}/pyqs?page=1&page_size=100`)
      .then((d) => {
        const years = [...new Set((d?.items || []).map((q) => q.paper_year).filter(Boolean))].sort(
          (a, b) => b - a
        );
        setAvailableYears(years);
      })
      .catch(() => {});
  }, [examSlug]);

  useEffect(() => {
    if (!examSlug) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    api
      .get(buildUrl())
      .then((d) => {
        if (cancelled) return;
        setData(d);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.message || "Failed to load PYQs.");
        setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [buildUrl, examSlug]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [debouncedYear, phase, difficulty, sourceType]);

  const examId = data?.exam_id || null;

  // Route the mutation through the shared useApiAction runner (frontend
  // governance). The expected 409 (paper not yet projected) is caught inside the
  // action and surfaced as an inline notice — returned as a handled result so
  // useApiAction's generic error toast does not also fire; any unexpected error
  // is rethrown onto the standard action error path.
  const startPaperPractice = useCallback(
    async (paperId) => {
      if (!paperId || busy) return;
      setPracticingPaperId(paperId);
      setPracticeError("");
      await run({
        action: async () => {
          try {
            return await api.post("/api/study/mocks/practice/start", {
              mode: "paper",
              target_id: paperId,
              ...(examId ? { exam_id: examId } : {}),
            });
          } catch (e) {
            if (e?.status === 409) return { emptyPool: true };
            throw e;
          }
        },
        onSuccess: (out) => {
          if (out?.emptyPool) {
            setPracticeError(
              "This paper isn't available for practice yet — its questions need to be verified and projected to the mock bank first."
            );
            return;
          }
          if (out?.attempt_id) {
            navigate(`/app/study/mocks/attempts/${out.attempt_id}`);
            return;
          }
          setPracticeError("This paper isn't available for practice yet.");
        },
        errorMessage: "Couldn't start practice. Please try again.",
      });
      setPracticingPaperId(null);
    },
    [run, busy, navigate, examId]
  );

  if (!examSlug) return null;

  const items = data?.items || [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / 20) || 1;

  const yearOptions = [
    { value: "", label: "Any year" },
    ...availableYears.map((y) => ({ value: String(y), label: String(y) })),
  ];

  return (
    <div className="space-y-4" data-testid="pyq-explorer">
      {/* Filters */}
      <div className="soft-card rounded-2xl p-4 flex flex-wrap gap-3 items-end">
        <FilterSelect label="Year" value={year} onChange={setYear} options={yearOptions} />
        <FilterSelect label="Difficulty" value={difficulty} onChange={setDifficulty} options={DIFFICULTY_OPTIONS} />
        <FilterSelect label="Source / Trust" value={sourceType} onChange={setSourceType} options={SOURCE_OPTIONS} />
        {(year || phase || difficulty || sourceType) && (
          <button
            type="button"
            onClick={() => {
              setYear("");
              setPhase("");
              setDifficulty("");
              setSourceType("");
            }}
            className="btn btn-ghost text-xs self-end"
          >
            Clear filters
          </button>
        )}
        <div className="ml-auto self-end text-xs text-muted-foreground">
          {loading ? "Loading…" : `${total.toLocaleString()} verified question${total !== 1 ? "s" : ""}`}
        </div>
      </div>

      {practiceError ? (
        <div
          className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2.5 text-sm text-amber-800"
          data-testid="pyq-practice-error"
          role="status"
        >
          {practiceError}
        </div>
      ) : null}

      {/* Results */}
      {error ? (
        <div className="rounded-xl border border-destructive/30 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-clay-100 bg-clay-50/60 h-20 animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div
          className="rounded-2xl border border-dashed border-clay-200 bg-clay-50/50 p-8 text-center"
          data-testid="pyq-explorer-empty"
        >
          <Search className="h-5 w-5 mx-auto text-clay-500" />
          <div className="mt-2 font-heading text-base font-semibold">No questions found</div>
          <p className="mt-1 text-xs text-muted-foreground">
            Try removing some filters, or check back once more questions are verified.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((q) => (
            <QuestionCard
              key={q.id}
              q={q}
              onPractice={startPaperPractice}
              practicing={busy && practicingPaperId === q.paper_id}
              practiceDisabled={busy}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && !loading && !error && (
        <div className="flex items-center justify-between gap-3 pt-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="btn btn-ghost text-sm disabled:opacity-40"
          >
            ← Previous
          </button>
          <span className="text-xs text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="btn btn-ghost text-sm disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
