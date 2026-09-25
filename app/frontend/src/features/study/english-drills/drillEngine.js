/**
 * Pure helpers for the English drills: exam scoping of the declared module
 * map, account-sourced module stats, arrangement → option matching, and the
 * device-local resume pointer. No React, no network.
 */
import { MODULES } from "./drillModules";

/**
 * Narrow every module to the topics locked for the learner's current exam.
 *
 * `items` is GET /api/study/topics?subject_id=… — the caller's SCOPED locked
 * coverage, each row with `verified_pyq_count` (verified PYQs tagged to it for
 * this exam) and `mastery_score` (account-level, written back on submit).
 */
export function scopeModules(items) {
  const byId = new Map((items || []).map((it) => [String(it.topic_id), it]));
  return MODULES.map((m) => {
    const locked = [];
    const notLocked = [];
    m.topics.forEach((t) => {
      const row = byId.get(t.id);
      if (!row) notLocked.push(t);
      else
        locked.push({
          ...t,
          verified: Number(row.verified_pyq_count) || 0,
          mastery: row.mastery_score == null ? null : Number(row.mastery_score),
        });
    });
    const practiceable = locked.filter((t) => t.verified > 0);
    const masteries = locked.map((t) => t.mastery).filter((x) => x != null);
    return {
      module: m,
      locked,
      notLocked,
      practiceable,
      verified: practiceable.reduce((n, t) => n + t.verified, 0),
      mastery: masteries.length ? Math.round(masteries.reduce((a, b) => a + b, 0) / masteries.length) : null,
    };
  });
}

/** Lowest-mastery module that has a mastery reading below 60, or null. */
export function weakestModule(scoped) {
  return (
    scoped
      .filter((s) => s.mastery != null && s.mastery < 60 && s.practiceable.length)
      .sort((a, b) => a.mastery - b.mastery)[0] || null
  );
}

/** Printed segment order — the arrangement a learner starts from. */
export function initialArrangement(sequence) {
  return (sequence?.segments || []).map((s) => s.label);
}

/**
 * The option whose reviewed order equals the learner's arrangement, or null.
 * `optionOrders` comes from the attempt payload (bank option id → labels); no
 * option text is parsed here.
 */
export function matchArrangement(optionOrders, arrangement) {
  const key = (arrangement || []).join("\u0001");
  const hit = Object.entries(optionOrders || {}).find(([, order]) => (order || []).join("\u0001") === key);
  return hit ? hit[0] : null;
}

export function moveItem(arr, from, to) {
  if (from == null || to == null || from === to) return arr;
  const next = arr.slice();
  const [x] = next.splice(from, 1);
  next.splice(to, 0, x);
  return next;
}

export function swapItems(arr, a, b) {
  const next = arr.slice();
  [next[a], next[b]] = [next[b], next[a]];
  return next;
}

// ── device-local resume pointer ────────────────────────────────────────────
// Only the attempt id lives on the device. Answers, grading and mastery are on
// the account (mock_attempt_responses + submit write-back); after a reload or
// on another device the server copy is what renders.
const KEY = (topicId) => `ccp-english-drills:attempt:${topicId}`;

export function loadAttemptPointer(topicId) {
  try {
    return window.localStorage.getItem(KEY(topicId));
  } catch (e) {
    return null;
  }
}

export function saveAttemptPointer(topicId, attemptId) {
  try {
    window.localStorage.setItem(KEY(topicId), attemptId);
  } catch (e) {
    /* storage blocked — resume falls back to starting a new set */
  }
}

export function clearAttemptPointer(topicId) {
  try {
    window.localStorage.removeItem(KEY(topicId));
  } catch (e) {
    /* ignore */
  }
}
