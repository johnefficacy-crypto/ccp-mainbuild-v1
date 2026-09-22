/**
 * The subject an aspirant last worked in.
 *
 * Subject is REQUIRED CONTEXT on this surface — without it a paper label reads
 * "2025 · P1" and means six different papers — so the one thing that must not
 * happen is asking for it again every visit. It is remembered per user, so a
 * shared machine does not hand one aspirant another's optional.
 *
 * localStorage, wrapped: it is disabled in private windows and by some
 * corporate policies, and a surface that throws there is worse than one that
 * asks for the subject again. Every read and write fails to a no-op.
 */

const KEY = "ccp.answerWriting.subject";

function storage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function scopedKey(userId) {
  return userId ? `${KEY}.${userId}` : KEY;
}

export function readLastSubject(userId) {
  try {
    return storage()?.getItem(scopedKey(userId)) || null;
  } catch {
    return null;
  }
}

export function writeLastSubject(userId, subject) {
  if (!subject) return;
  try {
    storage()?.setItem(scopedKey(userId), String(subject));
  } catch {
    /* storage disabled — the subject is asked for again next visit */
  }
}

export function clearLastSubject(userId) {
  try {
    storage()?.removeItem(scopedKey(userId));
  } catch {
    /* storage disabled */
  }
}

/**
 * The subject to open on, and why — so the surface can say which it used.
 *
 * Order: the URL (a shared link is an explicit request), then the subject a
 * `paper_id` in the URL implies, then the last-used subject, then the only
 * subject there is. Failing all four the aspirant picks, and NOTHING is shown
 * until they do: a picker is a question, a wall of 140 papers is not.
 */
export function resolveSubject({ urlSubject, paperId, catalog, lastUsed }) {
  if (urlSubject) return { subject: urlSubject, source: "url" };

  if (paperId) {
    const paper = (catalog?.papers || []).find((p) => p.id === paperId);
    if (paper?.subject) return { subject: paper.subject, source: "paper" };
  }

  const subjects = catalog?.subjects || [];
  const known = new Set(subjects.map((s) => s.subject));
  // A remembered subject the corpus no longer has is not a subject. Honouring
  // it would gate the surface on something that can never be picked.
  if (lastUsed && known.has(lastUsed)) return { subject: lastUsed, source: "remembered" };

  if (subjects.length === 1) return { subject: subjects[0].subject, source: "only" };

  return { subject: null, source: "none" };
}
