import { useCallback, useEffect, useRef, useState } from "react";

/**
 * useAnswerSync — gives every answer save a visible, recoverable sync state so a
 * dropped POST can never leave the UI showing an answer the server never got.
 *
 * State per question (see docs/mock_engine/attempt_save_semantics.md):
 *   unsaved  → user changed, debounce running
 *   saving   → POST in flight
 *   saved    → server ack
 *   retrying → failed once, backoff timer running
 *   failed   → retries exhausted (or a 4xx) — user action required
 *
 * Retries use exponential backoff (1s, 2s, 4s; max 3) and reuse the same
 * client_seq so the server's idempotency guard collapses the duplicate write.
 * 4xx (except 408 client-timeout) are real errors and surface immediately as
 * failed without retrying.
 */
export const SYNC = Object.freeze({
  UNSAVED: "unsaved",
  SAVING: "saving",
  SAVED: "saved",
  RETRYING: "retrying",
  FAILED: "failed",
});

const BACKOFFS_MS = [1000, 2000, 4000];
const MAX_RETRIES = BACKOFFS_MS.length;

function isRetryable(status) {
  // null/0 = network error, 408 = our own client-side timeout, 5xx = server.
  // Genuine 4xx (422 expired attempt, 423 section locked, …) are not retried.
  if (status == null || status === 0) return true;
  if (status === 408) return true;
  return status >= 500;
}

export default function useAnswerSync({ postAnswer, onEvent, debounceMs = 600 }) {
  const [syncStates, setSyncStates] = useState({});

  const debounceTimers = useRef({}); // questionId -> timeout id
  const retryTimers = useRef({}); // questionId -> timeout id
  const payloads = useRef({}); // questionId -> latest payload (with client_seq once fired)
  const seqRef = useRef(0);
  const aliveRef = useRef(true);
  // Synchronous mirror of syncStates for reads inside async callbacks.
  const syncStatesRef = useRef({});
  // Resolvers for flush() callers waiting on a terminal state (saved|failed).
  const flushResolvers = useRef({}); // qid -> resolve[]

  useEffect(() => {
    aliveRef.current = true;
    const debounces = debounceTimers.current;
    const retries = retryTimers.current;
    const resolvers = flushResolvers.current;
    return () => {
      aliveRef.current = false;
      Object.values(debounces).forEach((t) => clearTimeout(t));
      Object.values(retries).forEach((t) => clearTimeout(t));
      // Unblock any callers still awaiting flush() so they don't hang.
      Object.values(resolvers).forEach((arr) => arr.forEach((r) => r()));
    };
  }, []);

  const setEntry = useCallback((qid, patch) => {
    syncStatesRef.current = {
      ...syncStatesRef.current,
      [qid]: { ...syncStatesRef.current[qid], ...patch },
    };
    setSyncStates((prev) => ({ ...prev, [qid]: { ...prev[qid], ...patch } }));
    if (patch.state === SYNC.SAVED || patch.state === SYNC.FAILED) {
      const arr = flushResolvers.current[qid];
      if (arr?.length) {
        delete flushResolvers.current[qid];
        arr.forEach((r) => r());
      }
    }
  }, []);

  // Strictly monotonic counter — always a small integer well within Postgres int4
  // max (2,147,483,647). Never seeded from Date.now() or any timestamp source.
  // Retries replay the same frozen seq so the server's idempotency guard fires.
  const nextSeq = useCallback(() => {
    seqRef.current = seqRef.current + 1;
    return seqRef.current;
  }, []);

  const clearRetry = (qid) => {
    if (retryTimers.current[qid]) {
      clearTimeout(retryTimers.current[qid]);
      delete retryTimers.current[qid];
    }
  };

  const doSave = useCallback(
    async (qid, payload, retryCount) => {
      if (!aliveRef.current) return;
      setEntry(qid, { state: SYNC.SAVING, attempt: retryCount, error: null });
      try {
        await postAnswer(payload);
        if (!aliveRef.current) return;
        setEntry(qid, { state: SYNC.SAVED, savedAt: Date.now(), attempt: 0, error: null });
      } catch (e) {
        if (!aliveRef.current) return;
        const status = e?.status;
        if (!isRetryable(status)) {
          setEntry(qid, { state: SYNC.FAILED, error: e, attempt: retryCount });
          onEvent?.("answer.save_failed", {
            question_id: qid,
            status: status ?? null,
            reason: "client_error",
            attempt: retryCount,
          });
          return;
        }
        if (retryCount >= MAX_RETRIES) {
          setEntry(qid, { state: SYNC.FAILED, error: e, attempt: retryCount });
          onEvent?.("answer.save_failed", {
            question_id: qid,
            status: status ?? null,
            reason: "retries_exhausted",
            attempt: retryCount,
          });
          return;
        }
        const nextAttempt = retryCount + 1;
        const delay = BACKOFFS_MS[retryCount];
        setEntry(qid, { state: SYNC.RETRYING, attempt: nextAttempt, error: e });
        onEvent?.("answer.save_retried", {
          question_id: qid,
          status: status ?? null,
          attempt: nextAttempt,
          delay_ms: delay,
        });
        retryTimers.current[qid] = setTimeout(() => {
          delete retryTimers.current[qid];
          doSave(qid, payload, nextAttempt);
        }, delay);
      }
    },
    [postAnswer, onEvent, setEntry],
  );

  /**
   * Debounced save. `payload` carries everything but client_seq; the seq is
   * minted when the debounce fires (one logical save) and frozen onto the
   * payload so any retry replays the exact same write.
   */
  const queueSave = useCallback(
    (qid, payload) => {
      clearRetry(qid); // a fresh user change supersedes any pending retry
      payloads.current[qid] = { ...payload };
      setEntry(qid, { state: SYNC.UNSAVED, error: null, attempt: 0 });
      if (debounceTimers.current[qid]) clearTimeout(debounceTimers.current[qid]);
      debounceTimers.current[qid] = setTimeout(() => {
        delete debounceTimers.current[qid];
        const fired = { ...payloads.current[qid], client_seq: nextSeq() };
        payloads.current[qid] = fired;
        doSave(qid, fired, 0);
      }, debounceMs);
    },
    [doSave, nextSeq, debounceMs, setEntry],
  );

  // Force a question's pending save to fire now and wait until it reaches a
  // terminal state (saved or failed). Handles three cases:
  //   • debounce still running → cleared and fired immediately
  //   • save in-flight or retrying → just wait for terminal
  //   • already terminal or never touched → no-op
  // Needed before a section change: saves that fire after enter-section are
  // rejected as out-of-section (422 → non-retryable failed).
  const flush = useCallback(
    async (qid) => {
      if (!qid) return;

      if (debounceTimers.current[qid]) {
        clearTimeout(debounceTimers.current[qid]);
        delete debounceTimers.current[qid];
        const fired = { ...payloads.current[qid], client_seq: nextSeq() };
        payloads.current[qid] = fired;
        // Don't await — we wait via the resolver below so retries are covered.
        doSave(qid, fired, 0);
      }

      await new Promise((resolve) => {
        // Check state inside the Promise constructor to avoid a race between
        // the doSave call above and registering the resolver.
        const state = syncStatesRef.current[qid]?.state;
        if (!state || state === SYNC.SAVED || state === SYNC.FAILED) {
          resolve();
          return;
        }
        if (!flushResolvers.current[qid]) flushResolvers.current[qid] = [];
        flushResolvers.current[qid].push(resolve);
      });
    },
    [doSave, nextSeq],
  );

  // Flush multiple questions in parallel — used before a section transition to
  // drain every pending debounce in the current section at once.
  const flushMany = useCallback(
    async (qids) => {
      await Promise.all(qids.map((qid) => flush(qid)));
    },
    [flush],
  );

  // Flush EVERY touched question and wait for all to reach a terminal state.
  // Used before /submit so a debounced/in-flight save on any earlier question
  // (not just the current one) lands before the attempt is finalized — the
  // backend scores from persisted `mock_attempt_responses`, so a submit must
  // never race an unresolved save. Reads the synchronous refs (not React state)
  // so callers get an up-to-date picture after the awaited flush:
  //   { failedIds, answeredCount } — answeredCount counts questions whose save
  //   reached SAVED with a non-null selected_option_id.
  const flushAll = useCallback(async () => {
    const ids = Object.keys(syncStatesRef.current);
    await Promise.all(ids.map((qid) => flush(qid)));
    const snap = syncStatesRef.current;
    const failedIds = Object.entries(snap)
      .filter(([, e]) => e?.state === SYNC.FAILED)
      .map(([qid]) => qid);
    const answeredCount = Object.entries(snap).filter(
      ([qid, e]) => e?.state === SYNC.SAVED && payloads.current[qid]?.selected_option_id != null,
    ).length;
    return { failedIds, answeredCount };
  }, [flush]);

  // Manual retry from the failed banner — replays the same client_seq.
  const retryNow = useCallback(
    (qid) => {
      const payload = payloads.current[qid];
      if (!payload) return;
      clearRetry(qid);
      doSave(qid, payload, 0);
    },
    [doSave],
  );

  const retryAllFailed = useCallback(() => {
    Object.entries(syncStates).forEach(([qid, e]) => {
      if (e?.state === SYNC.FAILED) retryNow(qid);
    });
  }, [syncStates, retryNow]);

  const entries = Object.entries(syncStates);
  const failedIds = entries.filter(([, e]) => e?.state === SYNC.FAILED).map(([qid]) => qid);
  const pendingCount = entries.filter(
    ([, e]) => e?.state === SYNC.UNSAVED || e?.state === SYNC.SAVING || e?.state === SYNC.RETRYING,
  ).length;
  const failedCount = failedIds.length;

  return {
    syncStates,
    queueSave,
    flush,
    flushMany,
    flushAll,
    retryNow,
    retryAllFailed,
    failedIds,
    pendingCount,
    failedCount,
    hasUnsynced: pendingCount > 0 || failedCount > 0,
  };
}
