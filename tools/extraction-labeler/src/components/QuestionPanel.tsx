import { useCallback } from 'react';
import type { LabeledQuestion } from '../types';
import { hashQuestionText } from '../lib/hash';

interface Props {
  questions: LabeledQuestion[];
  selectedQuestionId: string | null;
  currentPage: number;
  onSelect: (id: string) => void;
  onAdd: () => void;
  onUpdate: (id: string, patch: Partial<LabeledQuestion>) => void;
  onDelete: (id: string) => void;
}

export default function QuestionPanel({
  questions,
  selectedQuestionId,
  currentPage,
  onSelect,
  onAdd,
  onUpdate,
  onDelete,
}: Props) {
  const handleTextBlur = useCallback(
    async (q: LabeledQuestion, text: string) => {
      const hash = text.trim() ? await hashQuestionText(text) : undefined;
      onUpdate(q.id, { question_text: text, normalized_question_hash: hash });
    },
    [onUpdate],
  );

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <strong>Questions ({questions.length})</strong>
        <button onClick={onAdd} style={styles.addBtn} title="New question (n)">
          + New
        </button>
      </div>

      <div style={styles.list}>
        {questions.length === 0 && (
          <p style={{ color: '#6b7280', fontSize: 13, padding: '8px 0' }}>
            No questions yet. Draw a bbox then click "+ New".
          </p>
        )}
        {questions.map((q) => {
          const isSelected = q.id === selectedQuestionId;
          const pageList = [...new Set(q.regions.map((r) => r.page))].sort((a, b) => a - b);
          return (
            <div
              key={q.id}
              onClick={() => onSelect(q.id)}
              style={{
                ...styles.item,
                background: isSelected ? '#eff6ff' : '#fff',
                borderColor: isSelected ? '#3b82f6' : '#e5e7eb',
              }}
            >
              <div style={styles.itemHeader}>
                <label style={{ fontSize: 12, color: '#6b7280' }}>Q#</label>
                <input
                  type="number"
                  min={1}
                  value={q.question_number}
                  onChange={(e) =>
                    onUpdate(q.id, { question_number: parseInt(e.target.value, 10) || 1 })
                  }
                  onClick={(e) => e.stopPropagation()}
                  style={styles.numInput}
                />
                <span style={{ marginLeft: 'auto', fontSize: 11, color: '#9ca3af' }}>
                  {q.regions.length} region{q.regions.length !== 1 ? 's' : ''} · p.{pageList.join(',')}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(q.id); }}
                  style={styles.deleteBtn}
                  title="Delete question"
                >
                  ✕
                </button>
              </div>

              <textarea
                value={q.question_text}
                onChange={(e) => onUpdate(q.id, { question_text: e.target.value })}
                onBlur={(e) => handleTextBlur(q, e.target.value)}
                onClick={(e) => e.stopPropagation()}
                placeholder="Question text…"
                rows={3}
                style={styles.textarea}
              />

              {q.normalized_question_hash && (
                <div style={{ fontSize: 10, color: '#9ca3af', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                  {q.normalized_question_hash.slice(0, 16)}…
                </div>
              )}

              {q.regions.some((r) => r.page === currentPage) && (
                <div style={{ fontSize: 11, color: '#059669', marginTop: 2 }}>
                  ● on current page
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    display: 'flex',
    flexDirection: 'column',
    width: 280,
    height: '100%',
    background: '#fff',
    border: '1px solid #e5e7eb',
    borderRadius: 8,
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 12px',
    borderBottom: '1px solid #e5e7eb',
    background: '#f9fafb',
  },
  addBtn: {
    padding: '3px 10px',
    background: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 13,
  },
  list: {
    flex: 1,
    overflowY: 'auto',
    padding: 8,
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  item: {
    padding: 8,
    border: '1px solid #e5e7eb',
    borderRadius: 6,
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  itemHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  numInput: {
    width: 50,
    padding: '2px 4px',
    border: '1px solid #d1d5db',
    borderRadius: 4,
    fontSize: 13,
  },
  textarea: {
    width: '100%',
    resize: 'vertical',
    padding: '4px 6px',
    border: '1px solid #d1d5db',
    borderRadius: 4,
    fontSize: 12,
    fontFamily: 'system-ui, sans-serif',
  },
  deleteBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#ef4444',
    fontSize: 12,
    padding: '0 2px',
  },
};
