// Source-aware return context for a mock attempt.
//
// The attempt route (/app/study/mocks/attempts/:attemptId) carries no source
// context on its own, so a learner who launched a PYQ practice attempt from an
// exam's PYQ Explorer has no way back to that section. When practice starts we
// stash a small return descriptor keyed by attempt id in sessionStorage; the
// attempt / result / review pages read it to render a "Back to …" link.
//
// sessionStorage (not localStorage) is deliberate: the context is only relevant
// for the current browsing session and should not persist across sessions.

const KEY_PREFIX = "cc.attempt.return.";

/**
 * Persist the return descriptor for an attempt.
 * @param {string} attemptId
 * @param {{ return_to: string, source_label: string }} ctx
 */
export function setAttemptReturnContext(attemptId, ctx) {
  if (!attemptId || !ctx?.return_to) return;
  try {
    window.sessionStorage.setItem(
      `${KEY_PREFIX}${attemptId}`,
      JSON.stringify({ return_to: ctx.return_to, source_label: ctx.source_label || "Back" }),
    );
  } catch {
    // Private-mode / quota — a missing back link is a graceful degradation.
  }
}

/**
 * Read the return descriptor for an attempt, or null when none was stored.
 * @param {string} attemptId
 * @returns {{ return_to: string, source_label: string } | null}
 */
export function getAttemptReturnContext(attemptId) {
  if (!attemptId) return null;
  try {
    const raw = window.sessionStorage.getItem(`${KEY_PREFIX}${attemptId}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.return_to) return null;
    return { return_to: parsed.return_to, source_label: parsed.source_label || "Back" };
  } catch {
    return null;
  }
}
