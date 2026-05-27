import MasteryDeltaIndicator from "./MasteryDeltaIndicator";

// Items keep the original {id, at, title, description} contract. Optional
// per-item fields are additive: `clickable` + an `onSelect(item)` callback make
// the title actionable, and a numeric `mastery_delta` renders the PR6a
// MasteryDeltaIndicator inline.
export default function PlanImpactTimeline({ items = [], onSelect }) {
  return (
    <ol className="space-y-3">
      {items.map((item) => {
        const clickable = typeof onSelect === "function" && item.clickable;
        const hasDelta = typeof item.mastery_delta === "number";
        return (
          <li key={item.id} className="relative border-l border-slate-300 pl-4">
            <span className="absolute -left-1.5 top-1 h-3 w-3 rounded-full bg-blue-600" />
            <p className="text-xs text-slate-500">{item.at}</p>
            {clickable ? (
              <button
                type="button"
                onClick={() => onSelect(item)}
                className="text-left text-sm font-medium text-blue-700 hover:underline"
              >
                {item.title}
              </button>
            ) : (
              <p className="text-sm font-medium">{item.title}</p>
            )}
            {item.description ? (
              <p className="text-sm text-slate-600">{item.description}</p>
            ) : null}
            {hasDelta ? (
              <div className="mt-1">
                <MasteryDeltaIndicator delta={item.mastery_delta} />
              </div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
