import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../../lib/api";
import { Card, Eyebrow, PageHeader } from "../../shared/ui/studyos";
import CatalogPicker from "../../features/study/descriptive/CatalogPicker";
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
 */
export default function AnswerWriting() {
  const [params, setParams] = useSearchParams();

  const [examId, setExamId] = useState("");
  const [catalog, setCatalog] = useState(null);
  const [catalogState, setCatalogState] = useState("loading");
  const [catalogError, setCatalogError] = useState("");

  const [questions, setQuestions] = useState([]);
  const [excludedMap, setExcludedMap] = useState(0);
  const [listState, setListState] = useState("idle");
  const [activeIndex, setActiveIndex] = useState(null);

  const selection = useMemo(
    () => ({
      subject: params.get("subject"),
      paper_id: params.get("paper_id"),
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
      .then((d) => setExamId(d?.selected_exam?.id || ""))
      .catch(() => setExamId(""));
  }, []);

  // The catalogue is re-read when the subject changes: papers, themes and years
  // are all scoped to it. Showing Anthropology's themes under Political Science
  // was not a display bug — the catalogue was genuinely returning every theme
  // in the corpus and the picker was faithfully rendering them.
  const subjectFilter = selection.subject || "";

  useEffect(() => {
    if (!examId) return;
    setCatalogState("loading");
    const query = new URLSearchParams({ exam_id: examId });
    if (subjectFilter) query.set("subject", subjectFilter);
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
  }, [examId, subjectFilter]);

  const hasFilter = Boolean(selection.paper_id || selection.theme || selection.subject);

  useEffect(() => {
    if (!examId || !hasFilter) {
      setQuestions([]);
      setListState("idle");
      return;
    }
    const query = new URLSearchParams({ exam_id: examId, limit: "100" });
    ["subject", "paper_id", "theme", "year"].forEach((k) => {
      if (selection[k]) query.set(k, selection[k]);
    });
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
  }, [examId, hasFilter, selection]);

  const active = activeIndex !== null ? questions[activeIndex] : null;
  const hasNext = activeIndex !== null && activeIndex + 1 < questions.length;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Answer writing · descriptive PYQs"
        title="Write a real Mains answer."
        sub="Past questions from your optional, one at a time. You review your own answer against a rubric — nothing here is machine-scored."
      />

      {!examId && (
        <Card>
          <p className="text-sm text-clay-700">
            Pick your target exam on the Study Plan first, and this fills with its
            past questions.
          </p>
        </Card>
      )}

      {examId && !active && (
        <Card>
          <CatalogPicker
            catalog={catalog}
            selection={selection}
            onSelect={setSelection}
            loading={catalogState === "loading"}
            error={catalogError}
          />
        </Card>
      )}

      {examId && !active && hasFilter && (
        <Card padded={false}>
          <div className="px-7 pt-6 pb-3">
            <Eyebrow>Questions</Eyebrow>
            <h2 className="font-heading mt-1 text-[22px] leading-tight">
              {listState === "loading" ? "Loading…" : `${questions.length} to write`}
            </h2>
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
                  <span className="num-mono mt-1 block text-[10.5px] text-clay-700">
                    {[
                      q.question_number ? `Q${q.question_number}` : null,
                      typeof q.marks === "number" ? `${q.marks} marks` : "marks not recorded",
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

      {active && (
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
