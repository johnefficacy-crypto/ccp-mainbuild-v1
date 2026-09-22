import PropTypes from "prop-types";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../../../lib/api";
import { Card, Eyebrow, Pill, StudyEmptyState } from "../../../shared/ui/studyos";
import AnswerStructurePanel from "./AnswerStructurePanel";
import AttemptPages, { pageCountLabel } from "./AttemptPages";

/**
 * My answers — every attempt this aspirant has written.
 *
 * THE POINT OF THE SURFACE IS THAT NOTHING IS REPLACED. A submitted attempt is
 * kept forever; writing the same question again adds a second attempt beside
 * the first. That is the only evidence of improvement this product has, so the
 * history never collapses two attempts into "the latest one" and the compare
 * view reads oldest-first, because a progression runs forwards.
 *
 * Rewriting starts a BLANK attempt with the old answer shown alongside. It is
 * never prefilled: editing last month's answer in place would destroy the
 * record of what they could do last month.
 */

const DATE = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  year: "numeric",
});

function formatDate(value) {
  if (!value) return null;
  const at = new Date(value);
  return Number.isNaN(at.getTime()) ? null : DATE.format(at);
}

function formatMinutes(seconds) {
  const total = Number(seconds);
  if (!Number.isFinite(total) || total <= 0) return null;
  const mins = Math.round(total / 60);
  return mins < 1 ? "under a minute" : `${mins} min`;
}

/** The facts of one attempt, in the order an aspirant scans them. */
export function attemptMeta(row) {
  const out = [];
  const when = formatDate(row.submitted_at || row.started_at);
  if (when) out.push(when);
  // A handwritten attempt has no word count — nothing has read the pages — so
  // it reads its page count instead, where a typed attempt reads its words.
  // "0 pages" is said out loud: a handwritten draft waiting for its photos is
  // a different thing from a typed one, and the row should say which.
  if (row.answer_mode === "handwritten") {
    if (Number.isFinite(row.page_count)) out.push(pageCountLabel(row.page_count));
  } else if (Number.isFinite(row.word_count)) {
    out.push(`${row.word_count} words`);
  }
  const spent = formatMinutes(row.time_spent_seconds);
  if (spent) out.push(spent);
  if (Number.isFinite(row.self_total)) out.push(`${row.self_total}/12 self-score`);
  // Only once the aspirant has ticked the answer structure; an unticked
  // attempt is not "0% covered".
  if (Number.isFinite(row.points_covered_pct)) {
    out.push(`${row.points_covered_pct}% points covered`);
  }
  return out;
}

function Badges({ row }) {
  return (
    <span className="ml-2 inline-flex flex-wrap gap-1 align-middle">
      <Pill tone={row.answer_mode === "handwritten" ? "amber" : "outline"}>
        {row.answer_mode === "handwritten" ? "Handwritten" : "Text"}
      </Pill>
      {row.status === "draft" ? <Pill tone="outline">Draft</Pill> : null}
      {/* Tri-state on purpose: null means this attempt predates paste
          tracking, and claiming "clean" for it would assert something nobody
          measured. Unknown therefore shows no badge at all. */}
      {row.has_pasted_text === true ? <Pill tone="rose">Contains pasted text</Pill> : null}
    </span>
  );
}

Badges.propTypes = { row: PropTypes.object.isRequired };

function FilterSelect({ label, value, onChange, options, testId }) {
  if (!options.length) return null;
  return (
    <label className="flex flex-col gap-1 text-[11px] text-clay-700">
      {label}
      <select
        className="rounded-md border border-[#D9C7A7] bg-[#FFFDF9] px-2 py-1.5 text-[12px]"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid={testId}
      >
        <option value="">All</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label} ({o.count})
          </option>
        ))}
      </select>
    </label>
  );
}

FilterSelect.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  options: PropTypes.array.isRequired,
  testId: PropTypes.string,
};

const EMPTY_FILTERS = {
  subject: "",
  paper_id: "",
  theme: "",
  status: "",
  since: "",
  until: "",
};

export default function MyAnswers({ onRewrite }) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading");
  const [openId, setOpenId] = useState(null);
  const [compareFor, setCompareFor] = useState(null);

  const query = useMemo(() => {
    const q = new URLSearchParams({ limit: "50" });
    Object.entries(filters).forEach(([k, v]) => {
      if (v) q.set(k, v);
    });
    return q.toString();
  }, [filters]);

  useEffect(() => {
    let live = true;
    setState("loading");
    api
      .get(`/api/study/descriptive/attempts?${query}`)
      .then((d) => {
        if (!live) return;
        setData(d);
        setState("ready");
      })
      .catch(() => {
        if (!live) return;
        setState("error");
      });
    return () => {
      live = false;
    };
  }, [query]);

  const setFilter = useCallback((key, value) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setOpenId(null);
  }, []);

  const facets = data?.facets || {};
  const items = data?.items || [];
  const anyFilter = Object.values(filters).some(Boolean);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <Eyebrow>Filter</Eyebrow>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <FilterSelect
            label="Subject"
            value={filters.subject}
            onChange={(v) => setFilter("subject", v)}
            options={(facets.subjects || []).map((f) => ({ ...f, label: f.value }))}
            testId="my-answers-filter-subject"
          />
          <FilterSelect
            label="Paper"
            value={filters.paper_id}
            onChange={(v) => setFilter("paper_id", v)}
            options={(facets.papers || []).map((p) => ({
              value: p.paper_id,
              label: p.label,
              count: p.count,
            }))}
            testId="my-answers-filter-paper"
          />
          <FilterSelect
            label="Theme"
            value={filters.theme}
            onChange={(v) => setFilter("theme", v)}
            options={(facets.themes || []).map((f) => ({ ...f, label: f.value }))}
            testId="my-answers-filter-theme"
          />
          <FilterSelect
            label="Status"
            value={filters.status}
            onChange={(v) => setFilter("status", v)}
            options={(facets.statuses || []).map((f) => ({
              ...f,
              label: f.value === "draft" ? "Draft" : "Submitted",
            }))}
            testId="my-answers-filter-status"
          />
          <label className="flex flex-col gap-1 text-[11px] text-clay-700">
            From
            <input
              type="date"
              className="rounded-md border border-[#D9C7A7] bg-[#FFFDF9] px-2 py-1.5 text-[12px]"
              value={filters.since}
              onChange={(e) => setFilter("since", e.target.value)}
              data-testid="my-answers-filter-since"
            />
          </label>
          <label className="flex flex-col gap-1 text-[11px] text-clay-700">
            To
            <input
              type="date"
              className="rounded-md border border-[#D9C7A7] bg-[#FFFDF9] px-2 py-1.5 text-[12px]"
              value={filters.until}
              onChange={(e) => setFilter("until", e.target.value)}
              data-testid="my-answers-filter-until"
            />
          </label>
          {anyFilter ? (
            <button
              type="button"
              className="link-under text-[12px] text-clay-700"
              onClick={() => setFilters(EMPTY_FILTERS)}
              data-testid="my-answers-clear-filters"
            >
              Clear filters
            </button>
          ) : null}
        </div>
        {/* Requirement 4, stated where it matters rather than in a help page:
            the aspirant needs to know the old answer survives BEFORE they
            press Rewrite, not afterwards. */}
        <p className="mt-4 text-[12px] text-clay-700" data-testid="my-answers-retention-note">
          Every answer you submit is kept. Writing a question again adds a new
          attempt beside the old one — you can only have one draft open per
          question at a time.
        </p>
      </Card>

      {state === "error" && (
        <Card>
          <p role="status" className="text-sm text-rose-700">
            Couldn&apos;t load your answers. Reload the page.
          </p>
        </Card>
      )}

      {state === "ready" && items.length === 0 && (
        <StudyEmptyState
          icon="✎"
          title={anyFilter ? "Nothing matches those filters." : "No answers yet."}
          body={
            anyFilter
              ? "Clear a filter to see more of your history."
              : "Write your first answer and it will appear here, with every later attempt beside it."
          }
        />
      )}

      {items.length > 0 && (
        <Card padded={false}>
          <div className="px-7 pt-6 pb-3">
            <Eyebrow>Your answers</Eyebrow>
            <h2 className="font-heading mt-1 text-[22px] leading-tight">
              {state === "loading" ? "Loading…" : `${data?.total ?? items.length} written`}
            </h2>
          </div>
          <div className="hairline mx-7" />
          <ul className="px-7 pb-6 pt-2">
            {items.map((row) => (
              <li key={row.id} className="border-b border-[#E7DECB] py-3 last:border-0">
                <button
                  type="button"
                  className="w-full text-left"
                  onClick={() => setOpenId(openId === row.id ? null : row.id)}
                  data-testid="my-answers-row"
                >
                  <span className="text-[13px] leading-snug">
                    {row.question?.excerpt}
                    <Badges row={row} />
                  </span>
                  <span className="num-mono mt-1 block text-[10.5px] text-clay-700">
                    {[row.question?.breadcrumb?.source, ...attemptMeta(row)]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </button>
                {openId === row.id && (
                  <AttemptDetail
                    attemptId={row.id}
                    questionId={row.question?.id}
                    onRewrite={onRewrite}
                    onCompare={() => setCompareFor(row.question?.id)}
                  />
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {compareFor && (
        <CompareAttempts questionId={compareFor} onClose={() => setCompareFor(null)} />
      )}
    </div>
  );
}

MyAnswers.propTypes = { onRewrite: PropTypes.func };

/** One attempt, read-only. There is no editor here, by construction. */
export function AttemptDetail({ attemptId, questionId, onRewrite, onCompare }) {
  const [detail, setDetail] = useState(null);
  const [state, setState] = useState("loading");
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    let live = true;
    setState("loading");
    setComparing(false);
    api
      .get(`/api/study/descriptive/attempts/${attemptId}`)
      .then((d) => {
        if (!live) return;
        setDetail(d);
        setState("ready");
      })
      .catch(() => live && setState("error"));
    return () => {
      live = false;
    };
  }, [attemptId]);

  if (state === "loading") {
    return <p className="mt-3 text-[12px] text-clay-700">Loading your answer…</p>;
  }
  if (state === "error") {
    return (
      <p role="status" className="mt-3 text-[12px] text-rose-700">
        Couldn&apos;t load that answer.
      </p>
    );
  }

  const attempt = detail?.attempt || {};
  const handwritten = attempt.answer_mode === "handwritten";
  const submitted = attempt.status === "submitted";
  return (
    <div className="mt-3 rounded-lg border border-[#E7DECB] bg-[#FBF8F2] p-4">
      <div className={comparing ? "grid gap-4 lg:grid-cols-2" : ""}>
      <div>
      {/* A HANDWRITTEN ATTEMPT IS ITS PAGES. It has no text and never will —
          nothing reads these images — so "no text yet" was a sentence about a
          typed attempt shown over a real answer sitting in storage. */}
      {handwritten ? (
        <AttemptPages
          attemptId={attemptId}
          pages={detail?.pages || []}
          ttlSeconds={detail?.url_ttl_seconds}
          emptyLabel={`${pageCountLabel(0)} — this answer is waiting for its photos.`}
        />
      ) : (
        <p
          className="whitespace-pre-wrap text-[13px] leading-relaxed text-clay-900"
          data-testid="my-answers-detail-text"
        >
          {attempt.answer_text || "This attempt has no text yet."}
        </p>
      )}
      </div>
      {comparing && submitted && <AnswerStructurePanel attemptId={attemptId} />}
      </div>
      <div className="mt-3 flex flex-wrap gap-3">
        {detail?.can_rewrite && (
          <button
            type="button"
            className="link-under text-[12px] text-clay-700"
            onClick={() => onRewrite && onRewrite(questionId)}
            data-testid="my-answers-rewrite"
          >
            Write this question again
          </button>
        )}
        {submitted && (
          <button
            type="button"
            className="link-under text-[12px] text-clay-700"
            aria-expanded={comparing}
            onClick={() => setComparing((v) => !v)}
            data-testid="my-answers-compare-structure"
          >
            {comparing ? "Hide answer structure" : "Compare with answer structure"}
          </button>
        )}
        <button
          type="button"
          className="link-under text-[12px] text-clay-700"
          onClick={onCompare}
          data-testid="my-answers-compare"
        >
          Compare my attempts
        </button>
      </div>
      <p className="mt-2 text-[11px] text-clay-700">
        Rewriting starts a blank answer. This one stays exactly as it is, beside it.
      </p>
    </div>
  );
}

AttemptDetail.propTypes = {
  attemptId: PropTypes.string.isRequired,
  questionId: PropTypes.string,
  onRewrite: PropTypes.func,
  onCompare: PropTypes.func,
};

/** Every attempt at one question, side by side, oldest first. */
export function CompareAttempts({ questionId, onClose }) {
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading");

  useEffect(() => {
    let live = true;
    setState("loading");
    api
      .get(`/api/study/descriptive/questions/${questionId}/attempts`)
      .then((d) => {
        if (!live) return;
        setData(d);
        setState("ready");
      })
      .catch(() => live && setState("error"));
    return () => {
      live = false;
    };
  }, [questionId]);

  const attempts = data?.attempts || [];
  const delta =
    Number.isFinite(data?.self_total_first) && Number.isFinite(data?.self_total_last)
      ? data.self_total_last - data.self_total_first
      : null;

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <Eyebrow>Compare</Eyebrow>
          <h3 className="font-heading mt-1 text-[18px] leading-tight">
            {attempts.length} {attempts.length === 1 ? "attempt" : "attempts"} at this question
          </h3>
        </div>
        <button
          type="button"
          className="link-under text-[12px] text-clay-700"
          onClick={onClose}
          data-testid="my-answers-compare-close"
        >
          Close
        </button>
      </div>

      {state === "error" && (
        <p role="status" className="mt-3 text-[12px] text-rose-700">
          Couldn&apos;t load these attempts.
        </p>
      )}

      {/* Only stated when there are two scored attempts to compare. One
          attempt has nothing to improve on, and saying "+0" would read as a
          judgement rather than an absence. */}
      {delta !== null && data.submitted_count > 1 && (
        <p className="mt-2 text-[12px] text-clay-700" data-testid="my-answers-compare-delta">
          Self-score went from {data.self_total_first}/12 to {data.self_total_last}/12
          {delta === 0 ? " — unchanged." : delta > 0 ? ` — up ${delta}.` : ` — down ${-delta}.`}
        </p>
      )}

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {attempts.map((a, i) => (
          <div
            key={a.id}
            className="rounded-lg border border-[#E7DECB] bg-[#FBF8F2] p-4"
            data-testid="my-answers-compare-column"
          >
            <p className="num-mono text-[10.5px] text-clay-700">
              {[`Attempt ${i + 1}`, ...attemptMeta(a)].filter(Boolean).join(" · ")}
            </p>
            {/* Side by side means side by side whatever was written: a
                handwritten column shows its pages, not an empty paragraph
                that reads as "nothing here". */}
            {a.answer_mode === "handwritten" ? (
              <div className="mt-2">
                <AttemptPages
                  attemptId={a.id}
                  pages={a.pages || []}
                  ttlSeconds={data?.url_ttl_seconds}
                  emptyLabel={`${pageCountLabel(0)} in this attempt.`}
                />
              </div>
            ) : (
              <p className="mt-2 whitespace-pre-wrap text-[12.5px] leading-relaxed">
                {a.answer_text || "No text in this attempt."}
              </p>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

CompareAttempts.propTypes = {
  questionId: PropTypes.string.isRequired,
  onClose: PropTypes.func,
};
