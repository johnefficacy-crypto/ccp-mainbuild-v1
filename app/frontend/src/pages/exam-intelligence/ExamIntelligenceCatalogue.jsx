import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BarChart3, Search } from "lucide-react";
import { api } from "../../lib/api";

// Top-level Exam Intelligence landing (PR #942 item 13). This is the
// study-intelligence catalogue — NOT the eligibility/recruitment funnel.
// It reads the verified-only active-exam catalogue from
// `/api/exam-intelligence/exams` and links each exam straight to its
// intelligence detail at `/app/exam-intelligence/exams/:slug`. It must not
// reuse EligibleExamsPage (eligibility-summary data, eligibility copy, or the
// recruitment CTA) — Eligibility stays the application funnel.

const DIFFICULTY_LABELS = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
};

// Normalize free text for search: lowercase, flatten `-`/`_` to spaces, and
// collapse runs of whitespace. Applied to BOTH the exam text and the typed
// query, so a learner can paste a slug verbatim (`upsc-cse`) and still match a
// haystack that stores it separator-flattened.
function normalizeSearchText(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// Build the searchable text for an exam. The deployed `name` frequently omits
// the acronym learners type (e.g. "UPSC"), while the `slug` carries it
// (`upsc-cse`). Searching name + slug (with separators flattened to spaces) so
// "UPSC" resolves to upsc-cse, plus exam_type for family-ish matches.
//
// Kept in step with `exam_search_haystack` in
// `app/backend/app/exam_intelligence/lookup.py`, which backs the server-side
// `?q=` filter on `/api/exam-intelligence/exams`. The two must agree: a query
// that matches here must match there.
export function examSearchHaystack(exam) {
  const parts = [exam?.name, exam?.slug, exam?.exam_type]
    .map((v) => normalizeSearchText(v))
    .filter(Boolean);
  // Keep both the separated and collapsed forms so "upsccse" and "upsc cse"
  // both hit `upsc-cse`.
  const joined = parts.join(" ");
  return `${joined} ${joined.replace(/\s+/g, "")}`;
}

// An empty query means "no filter", never "nothing found".
export function examMatchesQuery(exam, query) {
  const needle = normalizeSearchText(query);
  if (!needle) return true;
  const haystack = examSearchHaystack(exam);
  return haystack.includes(needle) || haystack.includes(needle.replace(/\s+/g, ""));
}

function ExamCard({ exam }) {
  const difficulty = DIFFICULTY_LABELS[exam.default_difficulty_level];
  return (
    <Link
      to={`/app/exam-intelligence/exams/${exam.slug}`}
      data-testid={`exam-intel-card-${exam.slug}`}
      className="group soft-card rounded-2xl p-5 flex flex-col gap-3 hover:border-clay-300 transition-colors"
    >
      <div className="flex items-start gap-3">
        <span className="shrink-0 h-9 w-9 grid place-items-center rounded-xl bg-clay-100 text-clay-700">
          <BarChart3 className="h-4.5 w-4.5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <div className="font-heading text-[15px] font-semibold text-clay-900 truncate">
            {exam.name}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {exam.exam_type ? (
              <span className="pill pill-dusk text-[11px] capitalize">
                {String(exam.exam_type).replace(/_/g, " ")}
              </span>
            ) : null}
            {difficulty ? (
              <span className="pill pill-sage text-[11px]">{difficulty}</span>
            ) : null}
          </div>
        </div>
      </div>
      <div className="mt-auto flex items-center gap-1.5 text-[12px] font-semibold text-clay-700 group-hover:text-clay-900">
        Open exam intelligence
        <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
      </div>
    </Link>
  );
}

export default function ExamIntelligenceCatalogue() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    setError(false);
    setData(null);
    api
      .get("/api/exam-intelligence/exams")
      .then((d) => {
        if (cancelled) return;
        if (d?.error) {
          setError(true);
          return;
        }
        setData(d || { items: [] });
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const exams = useMemo(() => (Array.isArray(data?.items) ? data.items : []), [data]);
  const filtered = useMemo(
    () => exams.filter((e) => examMatchesQuery(e, query)),
    [exams, query],
  );

  return (
    <section data-testid="exam-intelligence-page" aria-labelledby="exam-intelligence-heading">
      <div className="flex items-end justify-between flex-wrap gap-3 mb-4">
        <div>
          <h2
            id="exam-intelligence-heading"
            className="font-heading text-2xl font-semibold tracking-tight"
          >
            Exam intelligence
          </h2>
          <p className="text-sm text-muted-foreground mt-1 max-w-[70ch]">
            Verified previous-year trends, paper structure, and practice — per exam. Pick an
            exam to open its PYQ intelligence and start practising from real papers.
          </p>
        </div>
      </div>

      {error ? (
        <div className="soft-card rounded-2xl p-6" data-testid="exam-intelligence-error">
          <p className="text-sm text-clay-800">
            We couldn't load the exam catalogue. Nothing has changed — try again.
          </p>
          <button
            type="button"
            onClick={() => setReloadKey((k) => k + 1)}
            data-testid="exam-intelligence-retry"
            className="btn btn-ghost mt-3 text-sm"
          >
            Retry
          </button>
        </div>
      ) : !data ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="soft-card rounded-2xl h-28 animate-pulse" />
          ))}
        </div>
      ) : exams.length === 0 ? (
        <div
          className="rounded-2xl border border-dashed border-clay-200 bg-clay-50/50 p-8 text-center"
          data-testid="exam-intelligence-empty"
        >
          <BarChart3 className="h-5 w-5 mx-auto text-clay-500" />
          <div className="mt-2 font-heading text-base font-semibold">No exams published yet</div>
          <p className="mt-1 text-xs text-muted-foreground">
            Exam intelligence appears here once exams are verified and published.
          </p>
        </div>
      ) : (
        <>
          <label className="relative block mb-4 max-w-md">
            <span className="sr-only">Search exams</span>
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-clay-500" aria-hidden="true" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search exams…"
              data-testid="exam-intelligence-search"
              className="w-full rounded-lg border border-clay-200 bg-white pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay-400"
            />
          </label>
          {filtered.length === 0 ? (
            <div className="text-sm text-muted-foreground" data-testid="exam-intelligence-no-match">
              No exams match “{query}”.
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="exam-intelligence-grid">
              {filtered.map((exam) => (
                <ExamCard key={exam.id || exam.slug} exam={exam} />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
