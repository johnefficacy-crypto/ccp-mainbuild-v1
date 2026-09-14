/**
 * Shaping the candidate list into the two-pane palette's model.
 *
 * Pure functions over the `/api/study/plan/candidates` payload: no React, no
 * fetching, so the grouping rules are testable on their own and the panel
 * stays a rendering concern.
 *
 * The tree is deliberately TWO levels — subject, then macro topic. Microtopics
 * are the cards, not tree nodes: a third level would mean a user drills three
 * times to reach the thing they came for, and the card is where the actions
 * live anyway.
 */

/** Subjects everybody sits, then the optional this user chose. */
export const GROUPS = [
  { kind: "compulsory", label: "Compulsory papers" },
  { kind: "elective", label: "Your optional" },
];

/** A topic filed directly under its subject, with no macro topic between. */
export const UNGROUPED = "__ungrouped__";

function subjectKey(item) {
  return String(item.subject_id || item.subject || "unassigned");
}

function macroKey(item) {
  return item.parent_topic_id ? String(item.parent_topic_id) : UNGROUPED;
}

/**
 * `[{ kind, label, subjects: [{ id, name, count, macros: [...] }] }]`
 *
 * Subjects and macro topics keep the order the server sent — it ranked the
 * list, and re-sorting alphabetically here would throw that away. Counts are
 * the structural signal: they say how much is behind a node before it opens.
 */
export function buildTree(items) {
  const bySubject = new Map();

  (items || []).forEach((item) => {
    if (!item || !item.topic_id) return;
    const sid = subjectKey(item);
    if (!bySubject.has(sid)) {
      bySubject.set(sid, {
        id: sid,
        name: item.subject || "Unassigned",
        kind: item.selection_kind === "elective" ? "elective" : "compulsory",
        count: 0,
        macroOrder: [],
        macros: new Map(),
      });
    }
    const subject = bySubject.get(sid);
    subject.count += 1;

    const mid = macroKey(item);
    if (!subject.macros.has(mid)) {
      subject.macroOrder.push(mid);
      subject.macros.set(mid, {
        id: mid,
        // A macro topic whose own name could not be resolved files under its
        // subject rather than under a blank heading.
        name: mid === UNGROUPED ? null : item.parent_topic || null,
        count: 0,
      });
    }
    subject.macros.get(mid).count += 1;
  });

  return GROUPS.map((group) => ({
    ...group,
    subjects: [...bySubject.values()]
      .filter((s) => s.kind === group.kind)
      .map((s) => ({
        id: s.id,
        name: s.name,
        count: s.count,
        macros: s.macroOrder
          .map((mid) => s.macros.get(mid))
          .filter((m) => m.id !== UNGROUPED && m.name),
      })),
  })).filter((group) => group.subjects.length > 0);
}

/** The first selectable node, so the right pane is never empty on open. */
export function firstNode(tree) {
  const subject = (tree[0] || {}).subjects?.[0];
  return subject ? { subjectId: subject.id, macroId: null } : null;
}

export function sameNode(a, b) {
  return Boolean(a && b && a.subjectId === b.subjectId && a.macroId === b.macroId);
}

/**
 * Topics under a node. A subject node includes every topic in the subject —
 * the ones under its macro topics too, so selecting the subject is "show me
 * everything here" rather than "show me the leftovers".
 */
export function topicsForNode(items, node) {
  if (!node) return [];
  return (items || []).filter((item) => {
    if (subjectKey(item) !== node.subjectId) return false;
    if (!node.macroId) return true;
    return macroKey(item) === node.macroId;
  });
}

/**
 * Search runs across the WHOLE syllabus, not the selected node — a user who
 * types a topic name does not know which subject it lives under, which is the
 * entire reason they are typing. Substring, case-insensitive, on the topic
 * name only: matching the subject too would return 176 rows for "history".
 */
export function searchTopics(items, query) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return [];
  return (items || []).filter((item) =>
    String(item.topic || "").toLowerCase().includes(q),
  );
}

/** "Quantitative Aptitude › Quantitative methods" for a search hit or a node. */
export function positionOf(item) {
  return [item.subject, item.parent_topic].filter(Boolean).join(" › ");
}
