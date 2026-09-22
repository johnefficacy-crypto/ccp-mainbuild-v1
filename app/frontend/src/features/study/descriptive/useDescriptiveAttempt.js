import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../../lib/api";
// THE SHARED WORD RULE. The same function the Essay Spine counts with, and the
// transliteration of `descriptive.word_count` on the server. Pinned against one
// fixture list in `wordCountParity.test.js`. A live counter that disagrees with
// the stored one is worse than none: the aspirant would watch it cross the word
// limit and then be told it hadn't.
import { wordCount } from "../essay/spineSlots";

const BASE = "/api/study/descriptive";

/** How often an untouched-but-dirty draft is pushed to the server. */
export const AUTOSAVE_INTERVAL_MS = 10_000;

/**
 * One attempt at one descriptive question: open it, type, autosave, submit.
 *
 * Autosave is interval + blur, never per keystroke. The write carries the whole
 * answer, so a 2000-word answer at one request per character would be both
 * useless and expensive; ten seconds is short enough that a closed tab costs a
 * sentence, not a page.
 *
 * `answer` is local state and the server's copy is behind it by design. The
 * server owns `word_count` — it is recomputed there on every save — but the
 * editor shows the local count so the number moves while you type. They agree
 * because both sides run the same rule.
 */
export default function useDescriptiveAttempt(questionId) {
  const [attempt, setAttempt] = useState(null);
  const [answer, setAnswer] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | ready | error
  const [saveState, setSaveState] = useState("saved"); // saved | saving | dirty | error
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [timerRunning, setTimerRunning] = useState(false);
  const [pastedChars, setPastedChars] = useState(0);

  // Refs, not state: the autosave interval closes over these once and must see
  // current values without re-subscribing on every keystroke.
  const dirtyRef = useRef(false);
  const answerRef = useRef("");
  const elapsedRef = useRef(0);
  const attemptRef = useRef(null);
  const savingRef = useRef(false);
  const pastedRef = useRef(0);

  /** Characters arriving by paste, summed. Reported, never enforced. */
  const notePaste = useCallback((text) => {
    const chars = String(text || "").length;
    if (!chars) return;
    pastedRef.current += chars;
    setPastedChars(pastedRef.current);
    dirtyRef.current = true;
  }, []);

  const setAnswerText = useCallback((text) => {
    setAnswer(text);
    answerRef.current = text;
    dirtyRef.current = true;
    setSaveState("dirty");
  }, []);

  // ── open ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!questionId) return undefined;
    let cancelled = false;
    setStatus("loading");
    setError("");
    api
      .post(`${BASE}/attempts`, { pyq_question_id: questionId })
      .then((row) => {
        if (cancelled) return;
        setAttempt(row);
        attemptRef.current = row;
        const text = row?.answer_text || "";
        setAnswer(text);
        answerRef.current = text;
        const seconds = row?.time_spent_seconds || 0;
        setElapsed(seconds);
        elapsedRef.current = seconds;
        const pasted = row?.pasted_chars || 0;
        setPastedChars(pasted);
        pastedRef.current = pasted;
        dirtyRef.current = false;
        setSaveState("saved");
        setStatus("ready");
      })
      .catch((e) => {
        if (cancelled) return;
        setError(
          e?.status === 422
            ? "This question needs a map sheet, so it can't be practised here."
            : "Couldn't open this question. Try again shortly.",
        );
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [questionId]);

  // ── the clock ──────────────────────────────────────────────────────────
  //
  // TIME IS TRACKED WHETHER OR NOT THE TIMER IS RUNNING. `timerRunning` drives
  // the advisory countdown UI, which is only offered for a question carrying
  // marks (~13% of the corpus) and only once the aspirant presses Start. Tying
  // the stored elapsed time to it meant `time_spent_seconds` was 0 on almost
  // every attempt: the number was not "time spent" but "time spent with the
  // stopwatch running".
  //
  // It is still not wall-clock time. The interval stops while the tab is
  // hidden, so a question left open overnight records the minutes actually
  // spent on it rather than nine hours. The timer remains advisory and nothing
  // here enforces anything.
  useEffect(() => {
    if (status !== "ready") return undefined;
    const tick = () => {
      // Submitted attempts are closed records; the clock stops with them.
      if (attemptRef.current?.status !== "draft") return;
      if (typeof document !== "undefined" && document.hidden) return;
      elapsedRef.current += 1;
      setElapsed(elapsedRef.current);
      dirtyRef.current = true;
    };
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [status]);

  // ── save ───────────────────────────────────────────────────────────────
  const save = useCallback(async () => {
    const current = attemptRef.current;
    if (!current || current.status !== "draft") return false;
    if (!dirtyRef.current || savingRef.current) return false;
    savingRef.current = true;
    setSaveState("saving");
    try {
      const row = await api.patch(`${BASE}/attempts/${current.id}`, {
        answer_text: answerRef.current,
        // Running totals, both of them. The server keeps the max, so a save
        // that arrives late cannot undo a later one.
        time_spent_seconds: elapsedRef.current,
        pasted_chars: pastedRef.current,
      });
      dirtyRef.current = false;
      setAttempt(row);
      attemptRef.current = row;
      setSaveState("saved");
      return true;
    } catch {
      // Keep `dirty` set: the next interval retries, and nothing the aspirant
      // typed is discarded because one request failed.
      setSaveState("error");
      return false;
    } finally {
      savingRef.current = false;
    }
  }, []);

  useEffect(() => {
    if (status !== "ready") return undefined;
    const id = setInterval(save, AUTOSAVE_INTERVAL_MS);
    return () => clearInterval(id);
  }, [status, save]);

  // ── submit ─────────────────────────────────────────────────────────────
  const submit = useCallback(
    async (selfScores, notes) => {
      const current = attemptRef.current;
      if (!current) return { ok: false };
      // Flush first: submitting recomputes the word count from the STORED text,
      // so an unsaved last paragraph would be missing from the record.
      await save();
      try {
        const row = await api.post(`${BASE}/attempts/${current.id}/submit`, {
          self_scores: selfScores,
          notes: notes || null,
          // The last autosave can be up to ten seconds old, and this is the
          // one moment the elapsed time has to be right.
          time_spent_seconds: elapsedRef.current,
          pasted_chars: pastedRef.current,
        });
        setAttempt(row);
        attemptRef.current = row;
        setTimerRunning(false);
        setSaveState("saved");
        return { ok: true, data: row };
      } catch (e) {
        setError(
          e?.status === 422
            ? "Score all six criteria before saving."
            : "Couldn't save your review. Your answer is still here.",
        );
        return { ok: false, error: e };
      }
    },
    [save],
  );

  const liveWordCount = wordCount(answer);

  return {
    attempt,
    answer,
    setAnswerText,
    status,
    saveState,
    error,
    wordCount: liveWordCount,
    elapsed,
    timerRunning,
    startTimer: () => setTimerRunning(true),
    pauseTimer: () => setTimerRunning(false),
    save,
    submit,
    pastedChars,
    notePaste,
    submitted: attempt?.status === "submitted",
  };
}
