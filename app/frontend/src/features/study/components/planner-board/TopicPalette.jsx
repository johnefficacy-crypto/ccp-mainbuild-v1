import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";

import PaletteCard from "./PaletteCard";
import {
  buildTree,
  firstNode,
  sameNode,
  searchTopics,
  topicsForNode,
} from "./syllabusTree";

/**
 * Two panes: the syllabus on the left, the topics of the selected node on the
 * right.
 *
 * The flat list this replaces was unusable at 683 in-scope topics — no way to
 * see which subject you were in, no way to tell a microtopic's place in the
 * syllabus, and a search box that did nothing. The tree answers "where am I",
 * the cards answer "what can I add", and search cuts across both because
 * someone who types a topic name does not know which subject it lives under.
 *
 * What is deliberately NOT here: a priority number. The server ranks the cards
 * by `comparable_priority`, but that is a percentile within a source_basis —
 * three topics can hold 100 at once — so showing it would invite reading it as
 * a score out of 100. The order carries it; the number would mislead.
 */
export default function TopicPalette({ items, days, onAdd, busy, loading, error }) {
  const [query, setQuery] = useState("");
  const [node, setNode] = useState(null);
  const [dayByTopic, setDayByTopic] = useState({});

  const tree = useMemo(() => buildTree(items), [items]);
  const searching = query.trim().length > 0;

  // Settle on a node once the list arrives, and recover if the selected one
  // disappears (the user's optional changed, or a topic was placed).
  useEffect(() => {
    setNode((current) => {
      const stillThere =
        current &&
        tree.some((g) =>
          g.subjects.some(
            (s) =>
              s.id === current.subjectId &&
              (!current.macroId || s.macros.some((m) => m.id === current.macroId)),
          ),
        );
      return stillThere ? current : firstNode(tree);
    });
  }, [tree]);

  const visible = useMemo(
    () => (searching ? searchTopics(items, query) : topicsForNode(items, node)),
    [items, query, searching, node],
  );

  const selectedSubject = useMemo(() => {
    for (const group of tree) {
      const match = group.subjects.find((s) => s.id === node?.subjectId);
      if (match) return match;
    }
    return null;
  }, [tree, node]);

  const breadcrumb = searching
    ? `Matching “${query.trim()}” across your syllabus`
    : [
        selectedSubject?.name,
        node?.macroId
          ? (selectedSubject?.macros.find((m) => m.id === node.macroId) || {}).name
          : null,
      ]
        .filter(Boolean)
        .join(" › ");

  const chosenFor = (topicId) => dayByTopic[topicId] || days[0]?.date || "";

  return (
    <div className="flex flex-col rounded-xl border border-[#E7DECB] bg-white/60 p-4">
      <h3 className="font-heading text-[16px] leading-tight text-[#2E2218]">
        Topics to add
      </h3>
      <p className="mt-1 text-[11.5px] text-clay-700">
        Your exam&apos;s verified syllabus. Topics already on the board stay
        listed, marked with their day.
      </p>

      <label htmlFor="palette-search" className="mt-3 block text-[11px] text-clay-700">
        Search topics
      </label>
      <input
        id="palette-search"
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Percentage, Polity…"
        className="mt-1 w-full rounded-lg border border-[#E7DECB] bg-white px-2.5 py-1.5 text-[12.5px] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E2218]"
      />

      {loading && <p className="mt-4 text-[12px] text-clay-700">Loading topics…</p>}
      {error && (
        <p role="status" className="mt-4 text-[12px] text-rose-700">
          {error}
        </p>
      )}

      {!loading && !error && (
        <div className="mt-3 grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          {/* ── the syllabus ─────────────────────────────────────────── */}
          <nav
            aria-label="Syllabus"
            data-testid="palette-tree"
            aria-hidden={searching ? "true" : undefined}
            className={
              "max-h-[420px] overflow-y-auto pr-1 " + (searching ? "opacity-40" : "")
            }
          >
            {tree.length === 0 && (
              <p className="text-[12px] text-clay-700">
                Every verified topic is already on your board.
              </p>
            )}
            {tree.map((group) => (
              <div key={group.kind} className="mb-3 last:mb-0">
                <p className="text-[11px] text-clay-700">{group.label}</p>
                <ul className="mt-1">
                  {group.subjects.map((subject) => {
                    const on = !searching && sameNode(node, {
                      subjectId: subject.id,
                      macroId: null,
                    });
                    return (
                      <li key={subject.id}>
                        <button
                          type="button"
                          data-testid="tree-subject"
                          aria-current={on ? "true" : undefined}
                          disabled={searching}
                          onClick={() =>
                            setNode({ subjectId: subject.id, macroId: null })
                          }
                          className={
                            "flex w-full items-baseline justify-between gap-2 rounded px-1.5 py-1 text-left text-[12px] hover:bg-[#F3EADB] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E2218] " +
                            (on ? "bg-[#F3EADB] font-semibold text-[#2E2218]" : "text-[#2E2218]")
                          }
                        >
                          <span className="truncate">{subject.name}</span>
                          <span className="num-mono shrink-0 text-[10.5px] text-clay-700">
                            {subject.count}
                          </span>
                        </button>
                        {subject.macros.length > 0 && (
                          <ul className="ml-2 border-l border-[#E7DECB] pl-1.5">
                            {subject.macros.map((macro) => {
                              const macroOn = !searching && sameNode(node, {
                                subjectId: subject.id,
                                macroId: macro.id,
                              });
                              return (
                                <li key={macro.id}>
                                  <button
                                    type="button"
                                    data-testid="tree-macro"
                                    aria-current={macroOn ? "true" : undefined}
                                    disabled={searching}
                                    onClick={() =>
                                      setNode({
                                        subjectId: subject.id,
                                        macroId: macro.id,
                                      })
                                    }
                                    className={
                                      "flex w-full items-baseline justify-between gap-2 rounded px-1.5 py-1 text-left text-[11.5px] hover:bg-[#F3EADB] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E2218] " +
                                      (macroOn
                                        ? "bg-[#F3EADB] font-semibold text-[#2E2218]"
                                        : "text-clay-700")
                                    }
                                  >
                                    <span className="truncate">{macro.name}</span>
                                    <span className="num-mono shrink-0 text-[10.5px]">
                                      {macro.count}
                                    </span>
                                  </button>
                                </li>
                              );
                            })}
                          </ul>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </nav>

          {/* ── the topics ───────────────────────────────────────────── */}
          <div className="min-w-0">
            {breadcrumb && (
              <p
                data-testid="palette-breadcrumb"
                className="truncate text-[11px] text-clay-700"
              >
                {breadcrumb}
              </p>
            )}
            {visible.length === 0 ? (
              <p className="mt-2 text-[12px] text-clay-700">
                {searching
                  ? "No topic matches that search."
                  : "Nothing left to add here."}
              </p>
            ) : (
              <ul className="mt-2 flex max-h-[420px] flex-col gap-2 overflow-y-auto">
                {visible.map((item) => (
                  <PaletteCard
                    key={item.topic_id}
                    item={item}
                    days={days}
                    chosenDay={chosenFor(item.topic_id)}
                    onDayChange={(topicId, date) =>
                      setDayByTopic((prev) => ({ ...prev, [topicId]: date }))
                    }
                    onAdd={onAdd}
                    busy={busy}
                    showPosition={searching}
                  />
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

TopicPalette.propTypes = {
  items: PropTypes.arrayOf(
    PropTypes.shape({
      topic_id: PropTypes.string.isRequired,
      topic: PropTypes.string,
      subject: PropTypes.string,
      subject_id: PropTypes.string,
      parent_topic_id: PropTypes.string,
      parent_topic: PropTypes.string,
      selection_kind: PropTypes.oneOf(["compulsory", "elective"]),
      scheduled_date: PropTypes.string,
      predictability_band: PropTypes.string,
    }),
  ).isRequired,
  days: PropTypes.arrayOf(
    PropTypes.shape({ date: PropTypes.string, label: PropTypes.string }),
  ).isRequired,
  onAdd: PropTypes.func,
  busy: PropTypes.bool,
  loading: PropTypes.bool,
  error: PropTypes.string,
};
