import React, { useMemo, useRef, useState } from 'react';

const statuses = ['not_visited', 'visited', 'answered', 'marked', 'answered_marked'];

export default function QuestionPalette({ questions = [], statusMap = {}, currentIndex = 0, sectionFilter, onJump, locked = false }) {
  const filtered = useMemo(() => (sectionFilter ? questions.filter((q) => q.section_id === sectionFilter) : questions), [questions, sectionFilter]);
  const [active, setActive] = useState(currentIndex);
  const ref = useRef(null);

  const onKeyDown = (e) => {
    const cols = 10;
    if (e.key === 'Escape') return ref.current?.blur();
    let next = active;
    if (e.key === 'ArrowRight') next += 1;
    if (e.key === 'ArrowLeft') next -= 1;
    if (e.key === 'ArrowDown') next += cols;
    if (e.key === 'ArrowUp') next -= cols;
    next = Math.max(0, Math.min(filtered.length - 1, next));
    if (next !== active) { e.preventDefault(); setActive(next); }
    if (e.key === 'Enter' && filtered[active]) onJump?.(filtered[active].index);
  };

  return <div ref={ref} tabIndex={0} aria-label="Question palette" onKeyDown={onKeyDown} style={{display:'grid',gridTemplateColumns:'repeat(10,minmax(2rem,1fr))',gap:8,outline:'2px solid transparent'}}>
    {filtered.map((q, i) => {
      const s = statuses.includes(statusMap[q.id]) ? statusMap[q.id] : 'not_visited';
      const isCurrent = q.index === currentIndex;
      const disabled = locked && sectionFilter && q.section_id !== sectionFilter;
      return <button key={q.id} aria-label={`Jump to question ${q.index + 1}`} disabled={disabled} onClick={() => onJump?.(q.index)} style={{padding:'0.4rem',borderRadius:6,border:isCurrent?'2px solid var(--shell-focus, #2563eb)':'1px solid var(--shell-border,#64748b)',background:`var(--shell-status-${s})`}}>{q.index + 1}</button>;
    })}
  </div>;
}
