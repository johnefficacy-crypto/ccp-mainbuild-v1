import React from "react";
import PropTypes from "prop-types";

/**
 * How regularly a topic has been asked in its own subject-paper (PRED-01).
 * A percentile within that paper, so "Likely" says the same thing about a PSIR
 * topic as about a General Studies one. A topic with no year evidence carries
 * no band, and shows no pill — the absence is the honest statement, and a grey
 * "Unknown" chip would be a claim we cannot make.
 */
const RECURRENCE_LABEL = {
  near_certain: "Near-certain",
  likely: "Likely",
  occasional: "Occasional",
  rare: "Rare",
};

export default function PaletteCard({ item, days, chosenDay, onDayChange, onAdd, busy, showPosition }) {
  const selectId = `palette-day-${item.topic_id}`;
  const band = RECURRENCE_LABEL[item.predictability_band];
  const scheduled = Boolean(item.scheduled_date);
  const dayLabel = scheduled
    ? (days.find((d) => d.date === item.scheduled_date) || {}).label
    : null;

  return (
    <li
      data-testid="palette-topic"
      data-topic-id={item.topic_id}
      data-scheduled={scheduled ? "true" : "false"}
      draggable={!busy && !scheduled}
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "copy";
        e.dataTransfer.setData("text/plain", `topic:${item.topic_id}`);
      }}
      className={
        "rounded-lg border border-[#E7DECB] px-3 py-2 " +
        (scheduled ? "bg-[#FBF7EF] opacity-60" : "bg-white")
      }
    >
      <p className="text-[12.5px] leading-snug text-[#2E2218]">{item.topic}</p>

      {showPosition && (
        <p className="mt-0.5 text-[10.5px] text-clay-700">
          {[item.subject, item.parent_topic].filter(Boolean).join(" › ")}
        </p>
      )}

      {band && (
        <p className="mt-1.5">
          <span
            data-testid="recurrence-pill"
            className="inline-block rounded-full border border-[#E7DECB] bg-[#F3EADB] px-2 py-0.5 text-[10.5px] text-[#2E2218]"
          >
            Asked {band.toLowerCase()}
          </span>
        </p>
      )}

      {scheduled ? (
        <p data-testid="palette-scheduled" className="mt-2 text-[11px] text-clay-700">
          {dayLabel ? `On your board — ${dayLabel}` : "On your board this week"}
        </p>
      ) : (
        <div className="mt-2 flex items-center gap-1.5">
          <label htmlFor={selectId} className="sr-only">
            Day for {item.topic}
          </label>
          <select
            id={selectId}
            value={chosenDay}
            onChange={(e) => onDayChange(item.topic_id, e.target.value)}
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
            disabled={busy || !chosenDay}
            onClick={() => onAdd?.(item, chosenDay)}
            className="rounded border border-[#2E2218] px-2 py-1 text-[11px] font-semibold text-[#2E2218] hover:bg-[#F3EADB] disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E2218]"
          >
            Add
          </button>
        </div>
      )}
    </li>
  );
}

PaletteCard.propTypes = {
  item: PropTypes.shape({
    topic_id: PropTypes.string.isRequired,
    topic: PropTypes.string,
    subject: PropTypes.string,
    parent_topic: PropTypes.string,
    scheduled_date: PropTypes.string,
    predictability_band: PropTypes.oneOf([
      "near_certain",
      "likely",
      "occasional",
      "rare",
      null,
    ]),
  }).isRequired,
  days: PropTypes.arrayOf(
    PropTypes.shape({ date: PropTypes.string, label: PropTypes.string }),
  ).isRequired,
  chosenDay: PropTypes.string,
  onDayChange: PropTypes.func.isRequired,
  onAdd: PropTypes.func,
  busy: PropTypes.bool,
  showPosition: PropTypes.bool,
};
