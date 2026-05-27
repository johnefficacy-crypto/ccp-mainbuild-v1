import { useState } from 'react';
import type { LabeledQuestion, PaperMeta } from '../types';
import { validateFixture } from '../lib/schema';

interface Props {
  documentId: string;
  examId: string;
  paperMeta: PaperMeta;
  questions: LabeledQuestion[];
  onDocumentIdChange: (v: string) => void;
  onExamIdChange: (v: string) => void;
  onPaperMetaChange: (v: PaperMeta) => void;
  onClearSession: () => void;
}

function buildFixture(
  documentId: string,
  examId: string,
  paperMeta: PaperMeta,
  questions: LabeledQuestion[],
) {
  return {
    corpus_id: 'upsc-cse-prelims-pyq-v1' as const,
    document_id: documentId,
    document_kind: 'pyq_paper' as const,
    exam_id: examId,
    paper: {
      paper_name: paperMeta.paper_name,
      year: paperMeta.year,
      page_count: paperMeta.page_count,
    },
    extractor_target: 'questions' as const,
    coord_system: 'top_left_normalized' as const,
    expected_questions: questions.map(({ id: _id, ...rest }) => rest),
  };
}

export default function ExportPanel({
  documentId,
  examId,
  paperMeta,
  questions,
  onDocumentIdChange,
  onExamIdChange,
  onPaperMetaChange,
  onClearSession,
}: Props) {
  const [showErrors, setShowErrors] = useState(false);

  const fixture = buildFixture(documentId, examId, paperMeta, questions);
  const { valid, errors } = validateFixture(fixture);

  function handleExport() {
    if (!valid) {
      setShowErrors(true);
      return;
    }
    const blob = new Blob([JSON.stringify(fixture, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'questions.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleClear() {
    if (window.confirm('Clear this session? All labels will be lost.')) {
      onClearSession();
    }
  }

  return (
    <div style={styles.panel}>
      <strong style={{ fontSize: 14 }}>Fixture metadata</strong>

      <label style={styles.label}>
        document_id (document_assets.id)
        <input
          value={documentId}
          onChange={(e) => onDocumentIdChange(e.target.value)}
          placeholder="UUID from document_assets"
          style={styles.input}
        />
      </label>

      <label style={styles.label}>
        exam_id (UUID)
        <input
          value={examId}
          onChange={(e) => onExamIdChange(e.target.value)}
          placeholder="UPSC CSE exam UUID"
          style={styles.input}
        />
      </label>

      <label style={styles.label}>
        paper_name
        <input
          value={paperMeta.paper_name}
          onChange={(e) => onPaperMetaChange({ ...paperMeta, paper_name: e.target.value })}
          placeholder="General Studies Paper I 2023"
          style={styles.input}
        />
      </label>

      <div style={{ display: 'flex', gap: 8 }}>
        <label style={{ ...styles.label, flex: 1 }}>
          year
          <input
            type="number"
            min={1990}
            max={2100}
            value={paperMeta.year}
            onChange={(e) => onPaperMetaChange({ ...paperMeta, year: parseInt(e.target.value, 10) || 2023 })}
            style={styles.input}
          />
        </label>
        <label style={{ ...styles.label, flex: 1 }}>
          page_count
          <input
            type="number"
            min={1}
            value={paperMeta.page_count}
            onChange={(e) => onPaperMetaChange({ ...paperMeta, page_count: parseInt(e.target.value, 10) || 1 })}
            style={styles.input}
          />
        </label>
      </div>

      <div style={styles.stats}>
        {questions.length} question{questions.length !== 1 ? 's' : ''} ·{' '}
        {questions.reduce((n, q) => n + q.regions.length, 0)} regions
      </div>

      {!valid && showErrors && (
        <div style={styles.errorBox}>
          {errors.map((e, i) => (
            <div key={i} style={{ fontSize: 11 }}>
              {e}
            </div>
          ))}
        </div>
      )}

      {!valid && (
        <div style={styles.warnBadge}>
          {errors.length} validation error{errors.length !== 1 ? 's' : ''}{' '}
          <button
            onClick={() => setShowErrors((v) => !v)}
            style={{ fontSize: 11, background: 'none', border: 'none', cursor: 'pointer', color: '#b45309', textDecoration: 'underline' }}
          >
            {showErrors ? 'hide' : 'show'}
          </button>
        </div>
      )}

      <button
        onClick={handleExport}
        disabled={!valid}
        style={{
          ...styles.exportBtn,
          background: valid ? '#16a34a' : '#9ca3af',
          cursor: valid ? 'pointer' : 'not-allowed',
        }}
      >
        ⬇ Export questions.json
      </button>

      <button onClick={handleClear} style={styles.clearBtn}>
        Clear session
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    padding: 14,
    background: '#fff',
    border: '1px solid #e5e7eb',
    borderRadius: 8,
    width: 280,
  },
  label: {
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
    fontSize: 12,
    color: '#374151',
  },
  input: {
    padding: '5px 8px',
    border: '1px solid #d1d5db',
    borderRadius: 4,
    fontSize: 13,
    width: '100%',
  },
  stats: {
    fontSize: 12,
    color: '#6b7280',
    padding: '4px 0',
  },
  errorBox: {
    background: '#fef2f2',
    border: '1px solid #fca5a5',
    borderRadius: 4,
    padding: '6px 8px',
    color: '#dc2626',
    maxHeight: 120,
    overflowY: 'auto',
  },
  warnBadge: {
    background: '#fffbeb',
    border: '1px solid #fcd34d',
    borderRadius: 4,
    padding: '4px 8px',
    fontSize: 12,
    color: '#b45309',
  },
  exportBtn: {
    padding: '8px 0',
    color: '#fff',
    border: 'none',
    borderRadius: 5,
    fontSize: 14,
    fontWeight: 600,
  },
  clearBtn: {
    padding: '5px 0',
    background: 'none',
    border: '1px solid #e5e7eb',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 12,
    color: '#6b7280',
  },
};
