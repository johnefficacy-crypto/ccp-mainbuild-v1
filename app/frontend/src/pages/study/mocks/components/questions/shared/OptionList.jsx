import React from "react";
import MathRenderer from "./MathRenderer";
import { resolveOptionLabel } from "../../../optionLabels";

// Projected printed order: display_order asc (NULLs last). Array#sort is stable,
// so equal/absent display_order preserves the incoming (option_index) order.
function byDisplayOrder(a, b) {
  const ad = a?.display_order, bd = b?.display_order;
  if (ad == null && bd == null) return 0;
  if (ad == null) return 1;
  if (bd == null) return -1;
  return ad - bd;
}

export default function OptionList({ options = [], selected = [], onSelect, multiple = false, disabled = false }) {
  const ordered = [...options].sort(byDisplayOrder);
  const onKey = (e, idx, id) => {
    const parent = e.currentTarget.parentElement;
    if (e.key === "ArrowDown" || e.key === "ArrowRight") parent?.children[idx + 1]?.focus();
    if (e.key === "ArrowUp" || e.key === "ArrowLeft") parent?.children[idx - 1]?.focus();
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      onSelect(id);
    }
    if (/^[1-6]$/.test(e.key)) {
      const target = Number(e.key) - 1;
      parent?.children[target]?.focus();
      if (ordered[target]) onSelect(ordered[target].id);
    }
  };

  return (
    <div>
      {ordered.map((o, i) => {
        const active = selected.includes(o.id);
        // Shared label helper: prefers the projected printed label (e.g. "(a)"),
        // then an A/B/C-style index, then a positional letter — never a raw
        // 0-based/numeric index. Append a "." only to a bare alphanumeric label.
        const base = resolveOptionLabel(o, i);
        const label = /^[A-Za-z0-9]+$/.test(base) ? `${base}.` : base;
        return (
          <button key={o.id} type="button" onClick={() => onSelect(o.id)} onKeyDown={(e) => onKey(e, i, o.id)} disabled={disabled} dir="auto">
            <strong>{label}</strong> <MathRenderer text={o.option_text || ""} />
            {multiple && active ? " ✓" : ""}
          </button>
        );
      })}
    </div>
  );
}
