import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronUp, Search } from "lucide-react";
import { api } from "../../lib/api";
import useApiAction from "../../lib/hooks/useApiAction";
import { setAttemptReturnContext } from "../../pages/study/mocks/attemptReturnContext";
import PyqSummaryCharts from "./PyqSummaryCharts";
import PyqPaperPracticeCards from "./PyqPaperPracticeCards";

const DIFFICULTY_OPTIONS = [
  { value: "", label: "Any difficulty" },
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
  { value: "unknown", label: "Unknown" },
];

function FilterSelect({ label, value, onChange, options }) {
  return (
    <label className="flex flex-col gap-1 min-w-0">
      <span className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">{label}</span>
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
  // Pair topic_tags with topic_names by index — the same pairing the topic-filter
  // dropdown uses (q.topic_names[i] belongs to q.topic_tags[i]). Keep only pairs
  // that resolve cleanly so a length mismatch can never render "undefined", and a
  // question with 0 tags simply yields no pills.
  const topicPills = useMemo(() => {
    const tags = q.topic_tags || [];
    const names = q.topic_names || [];
    return tags
      .map((t, i) => ({ id: t?.topic_id, name: names[i] }))
      .filter((p) => p.id && p.name);
  }, [q.topic_tags, q.topic_names]);
  return (
    <div className="rounded-xl border border-clay-100 bg-white p-4 space-y-2" data-testid="pyq-question-card">
      <div className="flex items-start justify-between gap-2">
        {/* Learner chips: Year · Phase · Subject · Topic(s) · Difficulty · Q number.
            Topic (specific syllabus micro-topic) uses pill-amber so it reads
            distinctly from the broad-paper Subject pill (pill-sage).
            Shift/Source/Official are intentionally NOT shown to learners. */}
        <div className="flex items-center gap-2 flex-wrap">
          {q.paper_year ? <span className="pill pill-clay text-[11px]">{q.paper_year}</span> : null}
          {q.phase_name ? <span className="pill pill-dusk text-[11px]">{q.phase_name}</span> : null}
          {q.subject_name ? <span className="pill pill-sage text-[11px]">{q.subject_name}</span> : null}
          {topicPills.map((tp, i) => (
            <span key={`${tp.id}-${i}`} className="pill pill-amber text-[11px]" data-testid="pyq-topic-pill">
              {tp.name}
            </span>
          ))}
          {q.difficulty && q.difficulty !== "unknown" ? (
            <span className="pill pill-dusk text-[11px] capitalize">{q.difficulty}</span>
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

export default function PyqExplorerSection({ examSlug, examName }) {
  const navigate = useNavigate();
  const { run, busy } = useApiAction();

  // Intelligence overview + paper cards (default primary view).
  const [summary, setSummary] = useState(null);

  // Learner filters (Browse section). Source/Trust is intentionally gone.
  const [year, setYear] = useState("");
  const [phase, setPhase] = useState(""); // phase_slug
  const [subject, setSubject] = useState(""); // subject_id
  const [topic, setTopic] = useState(""); // topic_id
  const [difficulty, setDifficulty] = useState("");

  const [browseOpen, setBrowseOpen] = useState(false);
  const [page, setPage] = useState(1);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [practicingPaperId, setPracticingPaperId] = useState(null);
  const [practiceError, setPracticeError] = useState("");

  const [topicOptions, setTopicOptions] = useState([]); // {id, name, subject_id}
  const auxLoaded = useRef(false);

  const debouncedYear = useDebounce(year, 300);

  // ── intelligence summary (totals, distributions, paper cards) ──────────────
  useEffect(() => {
    if (!examSlug) return undefined;
    let cancelled = false;
    api
      .get(`/api/exam-intelligence/exams/${examSlug}/pyq-summary`)
      .then((d) => !cancelled && setSummary(d))
      .catch(() => !cancelled && setSummary(null));
    return () => {
      cancelled = true;
    };
  }, [examSlug]);

  // ── Topic filter options — derived from /pyqs, but strictly opt-in ─────────
  // Fetched only AFTER Browse is opened (never on initial render, so the hub
  // default hits /pyq-summary alone), once per mount, and paginated to
  // completeness so no topic that first appears after page 1 is silently
  // dropped. Fails closed: on any page error we clear the (possibly partial)
  // set and allow a retry on the next open rather than showing a misleading
  // partial topic list.
  useEffect(() => {
    if (!examSlug || !browseOpen || auxLoaded.current) return undefined;
    auxLoaded.current = true;
    let cancelled = false;
    const PAGE_SIZE = 100;
    const MAX_PAGES = 50; // safety cap (≤ 5000 questions) so this can't run away
    (async () => {
      const map = new Map();
      try {
        for (let pg = 1; pg <= MAX_PAGES; pg += 1) {
          // eslint-disable-next-line no-await-in-loop
          const d = await api.get(
            `/api/exam-intelligence/exams/${examSlug}/pyqs?page=${pg}&page_size=${PAGE_SIZE}`
          );
          if (cancelled) return;
          const rows = d?.items || [];
          rows.forEach((q) => {
            const tags = q.topic_tags || [];
            const names = q.topic_names || [];
            tags.forEach((t, i) => {
              const name = names[i];
              if (t?.topic_id && name && !map.has(t.topic_id)) {
                map.set(t.topic_id, { id: t.topic_id, name, subject_id: q.subject_id || null });
              }
            });
          });
          const totalRows = Number.isFinite(d?.total) ? d.total : rows.length;
          if (rows.length < PAGE_SIZE || pg * PAGE_SIZE >= totalRows) break;
        }
        if (!cancelled) setTopicOptions([...map.values()]);
      } catch {
        if (!cancelled) {
          auxLoaded.current = false; // permit a retry next time Browse opens
          setTopicOptions([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [examSlug, browseOpen]);

  const buildUrl = useCallback(() => {
    const p = new URLSearchParams();
    p.set("page", page);
    p.set("page_size", 20);
    if (debouncedYear) p.set("year", debouncedYear);
    if (phase) p.set("phase", phase);
    if (subject) p.set("subject_id", subject);
    if (topic) p.set("topic_id", topic);
    if (difficulty) p.set("difficulty", difficulty);
    return `/api/exam-intelligence/exams/${examSlug}/pyqs?${p.toString()}`;
  }, [examSlug, page, debouncedYear, phase, subject, topic, difficulty]);

  // Browse list fetches only when the (collapsed-by-default) section is open.
  useEffect(() => {
    if (!examSlug || !browseOpen) return undefined;
    let cancelled = false;
    setLoading(true);
    setError("");
    api
      .get(buildUrl())
      .then((d) => !cancelled && setData(d))
      .catch((e) => {
        if (cancelled) return;
        setError(e?.message || "Failed to load PYQs.");
        setData(null);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [buildUrl, examSlug, browseOpen]);

  useEffect(() => {
    setPage(1);
  }, [debouncedYear, phase, subject, topic, difficulty]);

  const examId = summary?.exam_id || data?.exam_id || null;

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
            setAttemptReturnContext(out.attempt_id, {
              return_to: `/app/exam-intelligence/exams/${examSlug}#pyq-explorer`,
              source_label: `Back to ${examName || "exam"} PYQs`,
            });
            navigate(`/app/study/mocks/attempts/${out.attempt_id}`);
            return;
          }
          setPracticeError("This paper isn't available for practice yet.");
        },
        errorMessage: "Couldn't start practice. Please try again.",
      });
      setPracticingPaperId(null);
    },
    [run, busy, navigate, examId, examSlug, examName]
  );

  const yearOptions = useMemo(
    () => [
      { value: "", label: "Any year" },
      ...(summary?.by_year || []).map((r) => ({ value: String(r.year), label: String(r.year) })),
    ],
    [summary]
  );
  const phaseOptions = useMemo(
    () => [
      { value: "", label: "Any phase" },
      ...(summary?.by_phase || [])
        .filter((r) => r.phase_slug)
        .map((r) => ({ value: r.phase_slug, label: r.phase_name || r.phase_slug })),
    ],
    [summary]
  );
  const subjectOptions = useMemo(
    () => [
      { value: "", label: "Any subject" },
      ...(summary?.by_subject || [])
        .filter((r) => r.subject_id)
        .map((r) => ({ value: r.subject_id, label: r.subject_name || "Subject" })),
    ],
    [summary]
  );
  const topicSelectOptions = useMemo(() => {
    const scoped = subject ? topicOptions.filter((t) => t.subject_id === subject) : topicOptions;
    return [{ value: "", label: "Any topic" }, ...scoped.map((t) => ({ value: t.id, label: t.name }))];
  }, [topicOptions, subject]);

  if (!examSlug) return null;

  const items = data?.items || [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / 20) || 1;
  const hasFilters = year || phase || subject || topic || difficulty;

  return (
    <div className="space-y-6" data-testid="pyq-explorer">
      {/* ── A. PYQ Intelligence overview ─────────────────────────────────── */}
      <div>
        <div className="font-heading text-lg font-semibold mb-3">PYQ intelligence</div>
        {summary ? (
          <PyqSummaryCharts summary={summary} />
        ) : (
          <div className="soft-card rounded-2xl p-6 text-sm text-muted-foreground" data-testid="pyq-summary-loading">
            Loading PYQ intelligence…
          </div>
        )}
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

      {/* ── B. Practice by paper (primary) ───────────────────────────────── */}
      <div>
        <div className="font-heading text-lg font-semibold mb-3">Practice by paper</div>
        <PyqPaperPracticeCards
          papers={summary?.papers}
          onPractice={startPaperPractice}
          practicingPaperId={practicingPaperId}
          practiceDisabled={busy}
          sr={busy}
        />
      </div>

      {/* ── C. Browse questions (secondary, collapsible) ─────────────────── */}
      <div>
        <button
          type="button"
          onClick={() => setBrowseOpen((v) => !v)}
          data-testid="pyq-browse-toggle"
          aria-expanded={browseOpen}
          className="w-full flex items-center justify-between soft-card rounded-2xl px-4 py-3"
        >
          <span className="font-heading text-lg font-semibold">Browse questions</span>
          {browseOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>

        {browseOpen && (
          <div className="mt-3 space-y-4" data-testid="pyq-browse">
            <div className="soft-card rounded-2xl p-4 flex flex-wrap gap-3 items-end">
              <FilterSelect label="Year" value={year} onChange={setYear} options={yearOptions} />
              <FilterSelect label="Phase" value={phase} onChange={setPhase} options={phaseOptions} />
              <FilterSelect label="Subject" value={subject} onChange={setSubject} options={subjectOptions} />
              <FilterSelect label="Topic" value={topic} onChange={setTopic} options={topicSelectOptions} />
              <FilterSelect label="Difficulty" value={difficulty} onChange={setDifficulty} options={DIFFICULTY_OPTIONS} />
              {hasFilters && (
                <button
                  type="button"
                  onClick={() => {
                    setYear("");
                    setPhase("");
                    setSubject("");
                    setTopic("");
                    setDifficulty("");
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

            {error ? (
              <div className="rounded-xl border border-destructive/30 p-4 text-sm text-destructive">{error}</div>
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
        )}
      </div>
    </div>
  );
}
