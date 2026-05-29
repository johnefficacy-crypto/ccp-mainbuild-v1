import React from "react";
import MathRenderer from "./MathRenderer";

export default function OptionList({ options = [], selected = [], onSelect, multiple = false, disabled = false }) {
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
      if (options[target]) onSelect(options[target].id);
    }
  };

  return (
    <div>
      {options.map((o, i) => {
        const active = selected.includes(o.id);
        return (
          <button key={o.id} type="button" onClick={() => onSelect(o.id)} onKeyDown={(e) => onKey(e, i, o.id)} disabled={disabled} dir="auto">
            <strong>{o.option_index || String.fromCharCode(65 + i)}.</strong> <MathRenderer text={o.option_text || ""} />
            {multiple && active ? " ✓" : ""}
          </button>
        );
      })}
    </div>
  );
}
