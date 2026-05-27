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

  useEffect(() => {
    aliveRef.current = true;
    const debounces = debounceTimers.current;
    const retries = retryTimers.current;
    return () => {
      aliveRef.current = false;
      Object.values(debounces).forEach((t) => clearTimeout(t));
      Object.values(retries).forEach((t) => clearTimeout(t));
    };
  }, []);

  const setEntry = useCallback((qid, patch) => {
    setSyncStates((prev) => ({ ...prev, [qid]: { ...prev[qid], ...patch } }));
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
    retryNow,
    retryAllFailed,
    failedIds,
    pendingCount,
    failedCount,
    hasUnsynced: pendingCount > 0 || failedCount > 0,
  };
}
