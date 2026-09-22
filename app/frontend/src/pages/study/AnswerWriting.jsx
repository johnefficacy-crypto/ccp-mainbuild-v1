import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../../lib/api";
import { Card, Eyebrow, PageHeader, Tabs } from "../../shared/ui/studyos";
import CatalogPicker from "../../features/study/descriptive/CatalogPicker";
import ContinueCard from "../../features/study/descriptive/ContinueCard";
import Coverage from "../../features/study/descriptive/Coverage";
import MyAnswers from "../../features/study/descriptive/MyAnswers";
import Progress from "../../features/study/descriptive/Progress";
import {
  readLastSubject,
  resolveSubject,
  writeLastSubject,
} from "../../features/study/descriptive/subjectMemory";
import QuestionScreen from "../../features/study/descriptive/QuestionScreen";

/**
 * Answer writing — descriptive PYQ practice, one question at a time.
 *
 * Question-level, not paper-level. A Mains paper is three hours, and ~87% of the
 * corpus carries no marks value, so a paper runtime would be a timer with
 * nothing to time and a score out of an unknown total. One question, written
 * properly and reviewed honestly, is the unit of practice that actually exists.
 *
 * The selection lives in the query string so a paper is deep-linkable — which is
 * what lets other surfaces hand an aspirant straight to a filtered list.
 *
 * "My answers" is a VIEW of this surface, not a destination of its own. The
 * no-new-surface rule (locked 2026-06-21) says a new top-level sidebar entry
 * has to remove two; an answer history belongs beside the questions it is a
 * history of anyway, so it is a tab and the tab lives in the query string with
 * everything else.
 */
export default function AnswerWriting() {
  const [params, setParams] = useSearchParams();

  const [examId, setExamId] = useState("");
  const [catalog, setCatalog] = useState(null);
  const [catalogState, setCatalogState] = useState("loading");
  const [catalogError, setCatalogError] = useState("");

  const [questions, setQuestions] = useState([]);
  const VIEWS = ["write", "answers", "coverage", "progress"];
  const view = VIEWS.includes(params.get("view")) ? params.get("view") : "write";
  // EVERY BROWSING CHOICE RIDES IN THE QUERY STRING — the lens, both filters
  // and the year range as well as the selection. That is what makes a view
  // shareable and the back button meaningful; a lens held in component state
  // would silently reset on every navigation.
  const lens = params.get("lens") === "year" ? "year" : "syllabus";
  const filters = useMemo(
    () => ({
      unattempted: params.get("unattempted") === "1",
      hasMarks: params.get("has_marks") === "1",
      yearFrom: params.get("year_from") || "",
      yearTo: params.get("year_to") || "",
    }),
    [params],
  );
  const [userId, setUserId] = useState("");
  const [excludedMap, setExcludedMap] = useState(0);
  const [listState, setListState] = useState("idle");
  const [activeIndex, setActiveIndex] = useState(null);

  const selection = useMemo(
    () => ({
      subject: params.get("subject"),
      paper_id: params.get("paper_id"),
      // Which paper WITHIN the subject — Paper I, or GS3. Distinct from
      // paper_id, which is one sitting.
      paper_number: params.get("paper_number"),
      theme: params.get("theme"),
      year: params.get("year"),
    }),
    [params],
  );

  const setSelection = useCallback(
    (next) => {
      const merged = { ...selection, ...next };
      const query = {};
      Object.entries(merged).forEach(([k, v]) => {
        if (v) query[k] = String(v);
      });
      setParams(query, { replace: true });
      setActiveIndex(null);
    },
    [selection, setParams],
  );

  // The aspirant's target exam drives the whole surface; nothing here asks them
  // to pick one again.
  useEffect(() => {
    api
      .get("/api/study/target-exam")
      .then((d) => {
        setExamId(d?.selected_exam?.id || "");
        // The subject memory is per user, so a shared machine cannot hand one
        // aspirant another's optional.
        setUserId(d?.user_id || d?.selected_exam?.user_id || "");
      })
      .catch(() => setExamId(""));
  }, []);

  // SUBJECT IS REQUIRED CONTEXT, and it is resolved rather than asked for
  // whenever it can be: from the URL, from the subject a `paper_id` in the URL
  // implies, from the subject last worked in, or because there is only one.
  // Only when none of those answer does the aspirant get a picker — and then
  // the picker is all they get.
  useEffect(() => {
    if (selection.subject || !catalog) return;
    const { subject } = resolveSubject({
      urlSubject: selection.subject,
      paperId: selection.paper_id,
      catalog,
      lastUsed: readLastSubject(userId),
    });
    if (subject) setSelection({ subject });
  }, [catalog, selection.subject, selection.paper_id, userId, setSelection]);

  useEffect(() => {
    if (selection.subject) writeLastSubject(userId, selection.subject);
  }, [selection.subject, userId]);

  // The catalogue is re-read when the subject changes: papers, themes and years
  // are all scoped to it. Showing Anthropology's themes under Political Science
  // was not a display bug — the catalogue was genuinely returning every theme
  // in the corpus and the picker was faithfully rendering them.
  const subjectFilter = selection.subject || "";
  const paperNumberFilter = selection.paper_number || "";

  useEffect(() => {
    if (!examId) return;
    setCatalogState("loading");
    const query = new URLSearchParams({ exam_id: examId });
    if (subjectFilter) query.set("subject", subjectFilter);
    if (paperNumberFilter) query.set("paper_number", paperNumberFilter);
    api
      .get(`/api/study/descriptive/catalog?${query.toString()}`)
      .then((d) => {
        setCatalog(d);
        setCatalogError("");
        setCatalogState("ready");
      })
      .catch(() => {
        setCatalogError("The question catalogue is unavailable right now. Reload the page.");
        setCatalogState("error");
      });
  }, [examId, subjectFilter, paperNumberFilter]);

  // A question list needs a subject AND something within it. "Every question
  // in Political Science" is 1,351 rows and no decision; a paper, a theme or a
  // year is a decision.
  const hasFilter = Boolean(
    selection.subject && (selection.paper_id || selection.theme || selection.year),
  );

  useEffect(() => {
    if (!examId || !hasFilter) {
      setQuestions([]);
      setListState("idle");
      return;
    }
    const query = new URLSearchParams({ exam_id: examId, limit: "100" });
    ["subject", "paper_id", "paper_number", "theme", "year"].forEach((k) => {
      if (selection[k]) query.set(k, selection[k]);
    });
    if (filters.unattempted) query.set("exclude_attempted", "true");
    if (filters.hasMarks) query.set("has_marks", "true");
    if (lens === "year") {
      // A year range is a question about sittings, so it only applies to the
      // lens that shows them.
      if (filters.yearFrom) query.set("year_from", filters.yearFrom);
      if (filters.yearTo) query.set("year_to", filters.yearTo);
    }
    setListState("loading");
    api
      .get(`/api/study/descriptive/questions?${query.toString()}`)
      .then((d) => {
        setQuestions(Array.isArray(d?.items) ? d.items : []);
        setExcludedMap(d?.excluded_map_questions || 0);
        setListState("ready");
      })
      .catch(() => {
        setQuestions([]);
        setListState("error");
      });
  }, [examId, hasFilter, selection, filters, lens]);

  const setParam = useCallback(
    (key, value) => {
      const query = {};
      params.forEach((v, k) => {
        if (k !== key) query[k] = v;
      });
      if (value) query[key] = String(value);
      setParams(query, { replace: false });
      setActiveIndex(null);
    },
    // `replace: false` on purpose for these: a lens or filter change is a step
    // the back button should undo.
    [params, setParams],
  );

  const setFilter = useCallback(
    (name, value) => {
      const key = {
        unattempted: "unattempted",
        hasMarks: "has_marks",
        yearFrom: "year_from",
        yearTo: "year_to",
      }[name];
      setParam(key, value === true ? "1" : value === false ? "" : value);
    },
    [setParam],
  );

  const setView = useCallback(
    (next) => {
      const query = {};
      params.forEach((v, k) => {
        if (k !== "view") query[k] = v;
      });
      if (next !== "write") query.view = next;
      setParams(query, { replace: true });
      setActiveIndex(null);
    },
    [params, setParams],
  );

  // Rewriting jumps back to the writing view on that question. The old answer
  // is NOT carried across — `QuestionScreen` opens a fresh attempt and shows
  // the previous one beside it.
  const rewrite = useCallback(
    (questionId) => {
      if (!questionId) return;
      setParams({ view: "write", question_id: String(questionId) }, { replace: true });
      setActiveIndex(null);
    },
    [setParams],
  );

  const active = activeIndex !== null ? questions[activeIndex] : null;
  const hasNext = activeIndex !== null && activeIndex + 1 < questions.length;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Answer writing · descriptive PYQs"
        title="Write a real Mains answer."
        sub="Past questions from your optional, one at a time. You review your own answer against a rubric — nothing here is machine-scored."
      />

      <Tabs
        value={view}
        onChange={setView}
        options={[
          { value: "write", label: "Write" },
          { value: "answers", label: "My answers" },
          { value: "coverage", label: "Coverage" },
          { value: "progress", label: "Progress" },
        ]}
      />

      {view === "answers" && <MyAnswers onRewrite={rewrite} />}

      {view === "progress" && <Progress />}

      {view === "coverage" && (
        <Coverage
          examId={examId}
          onPickQuestion={(q) => q?.paper_id && setParams(
            { view: "write", paper_id: String(q.paper_id) },
            { replace: true },
          )}
        />
      )}

      {view === "write" && examId && !active && (
        <ContinueCard onResume={rewrite} />
      )}

      {view === "write" && !examId && (
        <Card>
          <p className="text-sm text-clay-700">
            Pick your target exam on the Study Plan first, and this fills with its
            past questions.
          </p>
        </Card>
      )}

      {view === "write" && examId && !active && (
        <Card>
          <CatalogPicker
            catalog={catalog}
            selection={selection}
            onSelect={setSelection}
            loading={catalogState === "loading"}
            error={catalogError}
            lens={lens}
            onLensChange={(next) => setParam("lens", next === "syllabus" ? "" : next)}
            filters={filters}
            onFilterChange={setFilter}
          />
        </Card>
      )}

      {view === "write" && examId && !active && hasFilter && (
        <Card padded={false}>
          <div className="px-7 pt-6 pb-3">
            <Eyebrow>Questions</Eyebrow>
            <h2 className="font-heading mt-1 text-[22px] leading-tight">
              {listState === "loading" ? "Loading…" : `${questions.length} to write`}
            </h2>
            {/* "Unattempted only" lives in the navigator's filter row with
                the other filters. Two controls for one filter is worse than
                one, and this one was below the fold. */}
            {excludedMap > 0 && (
              // Counted, not silently dropped. "Three aren't here" is
              // information; a shorter list with no explanation is not.
              <p className="mt-1 text-[12px] text-clay-700" data-testid="descriptive-map-note">
                {excludedMap} map {excludedMap === 1 ? "question needs" : "questions need"} an
                outline map sheet, so {excludedMap === 1 ? "it isn't" : "they aren't"} shown here.
              </p>
            )}
          </div>
          <div className="hairline mx-7" />
          <ul className="px-7 pb-6 pt-2">
            {listState === "ready" && questions.length === 0 && (
              <li className="py-6 text-sm text-clay-700">
                Nothing left here — every question in this selection is done.
              </li>
            )}
            {listState === "error" && (
              <li role="status" className="py-6 text-sm text-rose-700">
                Couldn&apos;t load these questions. Reload the page.
              </li>
            )}
            {questions.map((q, i) => (
              <li key={q.id} className="border-b border-[#E7DECB] py-3 last:border-0">
                <button
                  type="button"
                  className="w-full text-left"
                  onClick={() => setActiveIndex(i)}
                  data-testid="descriptive-question-row"
                >
                  <span className="text-[13px] leading-snug">{q.text}</span>
                  {/* The breadcrumb's source line, which already reads
                      "2019 · P1 · Q5(b) · 15 marks" and omits whatever is
                      unknown. Never `question_number`: it is block-encoded, so
                      "Q108" is an internal key, and never a "marks not
                      recorded" placeholder — that is a sentence about the
                      database, not about the question. */}
                  <span className="num-mono mt-1 block text-[10.5px] text-clay-700">
                    {[
                      q.breadcrumb?.source,
                      typeof q.word_limit === "number" ? `${q.word_limit} words` : null,
                      q.attempt_count ? `${q.attempt_count} attempted` : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {view === "write" && active && (
        <>
          <button
            type="button"
            className="link-under self-start text-[12px] text-clay-700"
            onClick={() => setActiveIndex(null)}
            data-testid="descriptive-back"
          >
            ← Back to the list
          </button>
          <QuestionScreen
            key={active.id}
            question={active}
            hasNext={hasNext}
            onNext={() => setActiveIndex((i) => (i === null ? null : i + 1))}
          />
        </>
      )}
    </div>
  );
}
