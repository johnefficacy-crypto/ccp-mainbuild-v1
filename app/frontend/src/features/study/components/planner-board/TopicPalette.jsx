import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";

/**
 * How regularly a topic has been asked in its own subject-paper (PRED-01).
 * The band is a percentile within that paper, so "Likely" means the same thing
 * for an optional as for General Studies. A topic with no year evidence carries
 * no band and shows none — never a default.
 */
const RECURRENCE_LABEL = {
  near_certain: "Near-certain",
  likely: "Likely",
  occasional: "Occasional",
  rare: "Rare",
};

/**
 * Topics from the exam's locked coverage that are not on the board.
 *
 * Every row is draggable AND carries a day picker plus an Add button, so the
 * whole palette is usable without a pointer. The picker is not a fallback for
 * drag — it is the same operation, spelled out.
 */
export default function TopicPalette({ items, days, onAdd, busy, loading, error }) {
  const [query, setQuery] = useState("");
  const [dayByTopic, setDayByTopic] = useState({});

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (i) =>
        (i.topic || "").toLowerCase().includes(q) ||
        (i.subject || "").toLowerCase().includes(q),
    );
  }, [items, query]);

  return (
    <div className="flex flex-col rounded-xl border border-[#E7DECB] bg-white/60 p-4">
      <h3 className="font-heading text-[16px] leading-tight text-[#2E2218]">
        Topics to add
      </h3>
      <p className="mt-1 text-[11.5px] text-clay-700">
        From your exam&apos;s verified syllabus. Anything already on the board is
        hidden.
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

      {!loading && !error && filtered.length === 0 && (
        <p className="mt-4 text-[12px] text-clay-700">
          {items.length === 0
            ? "Every verified topic is already on your board."
            : "No topic matches that search."}
        </p>
      )}

      <ul className="mt-3 flex max-h-[480px] flex-col gap-2 overflow-y-auto">
        {filtered.map((item) => {
          const selectId = `palette-day-${item.topic_id}`;
          const chosen = dayByTopic[item.topic_id] || days[0]?.date || "";
          return (
            <li
              key={item.topic_id}
              data-testid="palette-topic"
              data-topic-id={item.topic_id}
              draggable={!busy}
              onDragStart={(e) => {
                e.dataTransfer.effectAllowed = "copy";
                e.dataTransfer.setData("text/plain", `topic:${item.topic_id}`);
              }}
              className="rounded-lg border border-[#E7DECB] bg-white px-3 py-2"
            >
              <p className="text-[12.5px] leading-snug text-[#2E2218]">{item.topic}</p>
              <p className="num-mono mt-0.5 text-[10.5px] text-clay-700">
                {item.subject || "Unassigned"} · priority{" "}
                {Math.round(
                  item.comparable_priority ?? item.exam_priority_score ?? 0,
                )}
                {RECURRENCE_LABEL[item.predictability_band] ? (
                  <> · recurrence {RECURRENCE_LABEL[item.predictability_band]}</>
                ) : null}
              </p>
              <div className="mt-2 flex items-center gap-1.5">
                <label htmlFor={selectId} className="sr-only">
                  Day for {item.topic}
                </label>
                <select
                  id={selectId}
                  value={chosen}
                  onChange={(e) =>
                    setDayByTopic((prev) => ({
                      ...prev,
                      [item.topic_id]: e.target.value,
                    }))
                  }
                  className="flex-1 rounded border border-[#E7DECB] bg-white px-1.5 py-1 text-[11px] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E2218]"
                >
                  {days.map((d) => (
                    <option key={d.date} value={d.date}>
                      {d.label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={busy || !chosen}
                  onClick={() => onAdd?.(item, chosen)}
                  className="rounded border border-[#2E2218] px-2 py-1 text-[11px] font-semibold text-[#2E2218] hover:bg-[#F3EADB] disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E2218]"
                >
                  Add
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

TopicPalette.propTypes = {
  items: PropTypes.arrayOf(
    PropTypes.shape({
      topic_id: PropTypes.string.isRequired,
      topic: PropTypes.string,
      subject: PropTypes.string,
      exam_priority_score: PropTypes.number,
      // The standing the server ranked by. Equal to exam_priority_score when
      // the candidate set spans a single source_basis.
      comparable_priority: PropTypes.number,
      predictability_band: PropTypes.oneOf([
        "near_certain",
        "likely",
        "occasional",
        "rare",
        null,
      ]),
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
