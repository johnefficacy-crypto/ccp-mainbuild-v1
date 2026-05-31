import { useCallback, useEffect, useRef } from 'react';
import type { LabeledQuestion } from '../types';
import { hashQuestionText } from '../lib/hash';
import { detectLeadingOrdinal, stripLeadingOrdinal, cleanWhitespace } from '../lib/ordinal';

const MIN_TEXTAREA_PX = 6 * 24;   // 144 px — 6 rows
const MAX_TEXTAREA_PX = 16 * 24;  // 384 px — 16 rows, then scroll

function autoResize(el: HTMLTextAreaElement) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, MAX_TEXTAREA_PX) + 'px';
}

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
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const selected = questions.find((q) => q.id === selectedQuestionId) ?? null;

  // Resize to fit existing content when a different question is selected.
  useEffect(() => {
    if (textareaRef.current) autoResize(textareaRef.current);
  }, [selectedQuestionId]);

  const handleTextBlur = useCallback(
    async (q: LabeledQuestion, text: string) => {
      const hash = text.trim() ? await hashQuestionText(text) : undefined;
      const detected = detectLeadingOrdinal(text);
      const patch: Partial<LabeledQuestion> = { question_text: text, normalized_question_hash: hash };
      if (detected !== null) patch.question_number = detected;
      onUpdate(q.id, patch);
    },
    [onUpdate],
  );

  const recomputeHash = useCallback(
    async (id: string, text: string) => {
      const hash = text.trim() ? await hashQuestionText(text) : undefined;
      onUpdate(id, { question_text: text, normalized_question_hash: hash });
    },
    [onUpdate],
  );

  // Derived values for the active editor
  const detectedOrdinal = selected ? detectLeadingOrdinal(selected.question_text) : null;
  const ordinalMismatch =
    detectedOrdinal !== null && selected !== null && detectedOrdinal !== selected.question_number;
  const hasExtraSpaces =
    selected !== null && cleanWhitespace(selected.question_text) !== selected.question_text;
  const hasLeadingOrdinal = selected !== null && detectLeadingOrdinal(selected.question_text) !== null;

  return (
    <div style={styles.panel}>
      {/* ── Header ── */}
      <div style={styles.header}>
        <strong>Questions ({questions.length})</strong>
        <button onClick={onAdd} style={styles.addBtn} title="New question (n)">
          + New
        </button>
      </div>

      {/* ── Compact list ── */}
      <div style={styles.list}>
        {questions.length === 0 && (
          <p style={{ color: '#6b7280', fontSize: 13, margin: 0, padding: '4px 0' }}>
            No questions yet. Draw a bbox or click "+ New".
          </p>
        )}
        {questions.map((q) => {
          const isSelected = q.id === selectedQuestionId;
          const pageList = [...new Set(q.regions.map((r) => r.page))].sort((a, b) => a - b);
          const onThisPage = q.regions.some((r) => r.page === currentPage);
          const isOos = q.out_of_scope_v1 === true;
          return (
            <div
              key={q.id}
              onClick={() => onSelect(q.id)}
              style={{
                ...styles.listItem,
                background: isSelected ? '#eff6ff' : '#fff',
                borderColor: isSelected ? '#3b82f6' : '#e5e7eb',
                opacity: isOos ? 0.6 : 1,
              }}
            >
              <span style={{ fontWeight: 600, fontSize: 13, color: isSelected ? '#1d4ed8' : '#374151', flexShrink: 0 }}>
                {isOos ? '⊘ ' : ''}Q{q.question_number}
              </span>
              <span style={styles.listPreview}>
                {q.question_text
                  ? q.question_text.slice(0, 45) + (q.question_text.length > 45 ? '…' : '')
                  : <em style={{ color: '#9ca3af' }}>no text</em>}
              </span>
              <span style={{ fontSize: 11, color: onThisPage ? '#059669' : '#9ca3af', flexShrink: 0 }}>
                {q.regions.length}r{pageList.length ? ` p.${pageList.join(',')}` : ''}
              </span>
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(q.id); }}
                style={styles.deleteBtn}
                title="Delete question"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>

      {/* ── Active editor ── */}
      {selected ? (
        <div style={styles.editor}>
          <div style={styles.editorHeader}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#374151' }}>
              Editing Q{selected.question_number}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto' }}>
              <label style={{ fontSize: 12, color: '#6b7280' }}>Q#</label>
              <input
                type="number"
                min={1}
                value={selected.question_number}
                onChange={(e) =>
                  onUpdate(selected.id, { question_number: parseInt(e.target.value, 10) || 1 })
                }
                style={styles.numInput}
              />
              <span style={{ fontSize: 11, color: '#9ca3af', flexShrink: 0 }}>
                {selected.regions.length} region{selected.regions.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>

          {/* Amber warning when detected ordinal differs from stored question_number */}
          {ordinalMismatch && (
            <div style={styles.ordinalWarning}>
              <span style={{ fontSize: 11, color: '#92400e' }}>
                Detected Q# {detectedOrdinal} differs from stored {selected.question_number}.
              </span>
              <button
                style={styles.acceptBtn}
                onClick={() => onUpdate(selected.id, { question_number: detectedOrdinal as number })}
              >
                Accept {detectedOrdinal}
              </button>
            </div>
          )}

          <textarea
            ref={textareaRef}
            value={selected.question_text}
            onChange={(e) => {
              onUpdate(selected.id, { question_text: e.target.value });
              autoResize(e.target);
            }}
            onBlur={(e) => handleTextBlur(selected, e.target.value)}
            placeholder="Paste or type question text…"
            style={styles.activeTextarea}
          />

          {/* Action row: strip ordinal and clean spaces buttons */}
          {(hasLeadingOrdinal || hasExtraSpaces) && (
            <div style={{ display: 'flex', gap: 6 }}>
              {hasLeadingOrdinal && (
                <button
                  style={styles.actionBtn}
                  onClick={() => {
                    const stripped = stripLeadingOrdinal(selected.question_text);
                    recomputeHash(selected.id, stripped);
                  }}
                >
                  Strip N.
                </button>
              )}
              {hasExtraSpaces && (
                <button
                  style={styles.actionBtn}
                  onClick={() => {
                    const cleaned = cleanWhitespace(selected.question_text);
                    recomputeHash(selected.id, cleaned);
                  }}
                >
                  Clean spaces
                </button>
              )}
            </div>
          )}

          {selected.normalized_question_hash && (
            <div style={{ fontSize: 10, color: '#9ca3af', fontFamily: 'monospace', wordBreak: 'break-all' }}>
              {selected.normalized_question_hash.slice(0, 16)}…
            </div>
          )}

          {/* Out-of-scope checkbox */}
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#374151', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={selected.out_of_scope_v1 === true}
              onChange={(e) => onUpdate(selected.id, { out_of_scope_v1: e.target.checked })}
            />
            Out of scope (table / figure / matching)
          </label>

          {/* Guidance text */}
          <div style={{ fontSize: 11, fontStyle: 'italic', color: '#9ca3af' }}>
            Stem only — no leading number, no (a)(b)(c)(d). Matching/table/figure → mark out-of-scope.
          </div>
        </div>
      ) : (
        <div style={styles.editorEmpty}>
          {questions.length > 0
            ? 'Select a question above to edit its text.'
            : 'Draw a bbox on the PDF or click "+ New".'}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    display: 'flex',
    flexDirection: 'column',
    width: 300,
    background: '#fff',
    border: '1px solid #e5e7eb',
    borderRadius: 8,
    overflow: 'clip',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 12px',
    borderBottom: '1px solid #e5e7eb',
    background: '#f9fafb',
    flexShrink: 0,
    position: 'sticky',
    top: 0,
    zIndex: 1,
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
    overflowY: 'auto',
    padding: '6px 8px',
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
    maxHeight: 220,
    flexShrink: 0,
    borderBottom: '1px solid #f3f4f6',
  },
  listItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '5px 7px',
    border: '1px solid #e5e7eb',
    borderRadius: 5,
    cursor: 'pointer',
    minWidth: 0,
  },
  listPreview: {
    flex: 1,
    fontSize: 12,
    color: '#6b7280',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    minWidth: 0,
  },
  deleteBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#ef4444',
    fontSize: 12,
    padding: '0 2px',
    flexShrink: 0,
  },
  editor: {
    display: 'flex',
    flexDirection: 'column',
    gap: 7,
    padding: '10px 12px 12px',
    background: '#f8fafc',
    borderTop: '1px solid #e5e7eb',
  },
  editorHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexShrink: 0,
  },
  numInput: {
    width: 52,
    padding: '2px 4px',
    border: '1px solid #d1d5db',
    borderRadius: 4,
    fontSize: 13,
  },
  activeTextarea: {
    width: '100%',
    minHeight: MIN_TEXTAREA_PX,
    maxHeight: MAX_TEXTAREA_PX,
    overflowY: 'auto',
    resize: 'none',
    padding: '7px 9px',
    border: '1.5px solid #3b82f6',
    borderRadius: 5,
    fontSize: 13,
    fontFamily: 'system-ui, -apple-system, sans-serif',
    lineHeight: 1.6,
    boxSizing: 'border-box',
    color: '#1e293b',
    background: '#fff',
  },
  editorEmpty: {
    padding: '16px 12px',
    fontSize: 13,
    color: '#9ca3af',
    textAlign: 'center',
    fontStyle: 'italic',
    borderTop: '1px solid #e5e7eb',
  },
  ordinalWarning: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: '#fffbeb',
    border: '1px solid #fcd34d',
    borderRadius: 4,
    padding: '5px 8px',
  },
  acceptBtn: {
    padding: '2px 8px',
    background: '#f59e0b',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
    marginLeft: 'auto',
    flexShrink: 0,
  },
  actionBtn: {
    padding: '3px 10px',
    background: '#f3f4f6',
    color: '#374151',
    border: '1px solid #d1d5db',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
  },
};
