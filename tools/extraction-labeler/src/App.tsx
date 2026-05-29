/// <reference types="vite/client" />
import { useState, useEffect, useCallback, useRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import PdfViewer from './components/PdfViewer';
import QuestionPanel from './components/QuestionPanel';
import ExportPanel from './components/ExportPanel';
import type { LabeledQuestion, Region, PaperMeta, Bbox } from './types';
import { saveSession, loadSession, clearSession } from './lib/storage';

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).href;

const DEFAULT_PAPER: PaperMeta = { paper_name: '', year: 2023, page_count: 1 };

function makeId(): string {
  return crypto.randomUUID();
}

export default function App() {
  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [documentId, setDocumentId] = useState('');
  const [examId, setExamId] = useState('');
  const [paperMeta, setPaperMeta] = useState<PaperMeta>(DEFAULT_PAPER);
  const [questions, setQuestions] = useState<LabeledQuestion[]>([]);
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null);
  const [selectedRegionIdx, setSelectedRegionIdx] = useState<number | null>(null);
  const autosaveTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Autosave: every 5s and on every state change
  const doSave = useCallback(() => {
    saveSession({ documentId, examId, paperMeta, questions });
  }, [documentId, examId, paperMeta, questions]);

  useEffect(() => {
    doSave();
  }, [doSave]);

  useEffect(() => {
    autosaveTimer.current = setInterval(doSave, 5000);
    return () => {
      if (autosaveTimer.current) clearInterval(autosaveTimer.current);
    };
  }, [doSave]);

  // Restore session on documentId change
  useEffect(() => {
    if (!documentId) return;
    const saved = loadSession(documentId);
    if (saved) {
      setExamId(saved.examId);
      setPaperMeta(saved.paperMeta);
      setQuestions(saved.questions);
    }
  }, [documentId]);

  // Keyboard: 'n' = new question, arrow keys = page nav (when not in text input)
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.target as HTMLElement).tagName === 'INPUT' ||
          (e.target as HTMLElement).tagName === 'TEXTAREA') return;
      if (e.key === 'n') handleAddQuestion();
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') setCurrentPage((p) => Math.min(totalPages, p + 1));
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') setCurrentPage((p) => Math.max(1, p - 1));
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  });

  // Regions for current page + selected question
  const currentPageRegions: Region[] = selectedQuestionId
    ? (questions.find((q) => q.id === selectedQuestionId)?.regions.filter((r) => r.page === currentPage) ?? [])
    : [];

  // --- Handlers ---

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const buffer = await file.arrayBuffer();
    const doc = await pdfjsLib.getDocument({ data: buffer }).promise;
    setPdfDoc(doc);
    setTotalPages(doc.numPages);
    setCurrentPage(1);
    setPaperMeta((m) => ({ ...m, page_count: doc.numPages }));
  }

  function handleAddQuestion() {
    const nextNum = questions.length > 0
      ? Math.max(...questions.map((q) => q.question_number)) + 1
      : 1;
    const q: LabeledQuestion = {
      id: makeId(),
      question_number: nextNum,
      question_text: '',
      regions: [],
    };
    setQuestions((qs) => [...qs, q]);
    setSelectedQuestionId(q.id);
    setSelectedRegionIdx(null);
  }

  function handleUpdateQuestion(id: string, patch: Partial<LabeledQuestion>) {
    setQuestions((qs) => qs.map((q) => (q.id === id ? { ...q, ...patch } : q)));
  }

  function handleDeleteQuestion(id: string) {
    setQuestions((qs) => qs.filter((q) => q.id !== id));
    if (selectedQuestionId === id) {
      setSelectedQuestionId(null);
      setSelectedRegionIdx(null);
    }
  }

  function handleRegionAdd(bbox: Bbox) {
    if (!selectedQuestionId) {
      // Auto-create a question if none selected
      const nextNum = questions.length > 0
        ? Math.max(...questions.map((q) => q.question_number)) + 1
        : 1;
      const q: LabeledQuestion = {
        id: makeId(),
        question_number: nextNum,
        question_text: '',
        regions: [{ page: currentPage, bbox }],
      };
      setQuestions((qs) => [...qs, q]);
      setSelectedQuestionId(q.id);
      setSelectedRegionIdx(0);
      return;
    }
    setQuestions((qs) =>
      qs.map((q) => {
        if (q.id !== selectedQuestionId) return q;
        const newRegions = [...q.regions, { page: currentPage, bbox }];
        setSelectedRegionIdx(newRegions.length - 1);
        return { ...q, regions: newRegions };
      }),
    );
  }

  function handleRegionDelete(idx: number) {
    if (!selectedQuestionId) return;
    setQuestions((qs) =>
      qs.map((q) => {
        if (q.id !== selectedQuestionId) return q;
        const pageRegions = q.regions.filter((r) => r.page === currentPage);
        const regionToDelete = pageRegions[idx];
        return { ...q, regions: q.regions.filter((r) => r !== regionToDelete) };
      }),
    );
    setSelectedRegionIdx(null);
  }

  function handleRegionUpdate(idx: number, bbox: Bbox) {
    if (!selectedQuestionId) return;
    setQuestions((qs) =>
      qs.map((q) => {
        if (q.id !== selectedQuestionId) return q;
        const pageRegions = q.regions.filter((r) => r.page === currentPage);
        const targetRegion = pageRegions[idx];
        return {
          ...q,
          regions: q.regions.map((r) => (r === targetRegion ? { ...r, bbox } : r)),
        };
      }),
    );
  }

  function handleClearSession() {
    clearSession(documentId);
    setQuestions([]);
    setSelectedQuestionId(null);
    setSelectedRegionIdx(null);
  }

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <strong style={{ fontSize: 16 }}>Extraction Labeler</strong>
        <span style={{ fontSize: 12, color: '#6b7280' }}>UPSC CSE PYQ v1 bbox labeler</span>
        <label style={styles.fileBtn}>
          📄 Load PDF
          <input
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
        </label>
      </header>

      <div style={styles.body}>
        <div style={styles.viewer}>
          <PdfViewer
            pdfDoc={pdfDoc}
            currentPage={currentPage}
            totalPages={totalPages}
            regions={currentPageRegions}
            selectedRegionIdx={selectedRegionIdx}
            onPageChange={setCurrentPage}
            onRegionAdd={handleRegionAdd}
            onRegionDelete={handleRegionDelete}
            onRegionUpdate={handleRegionUpdate}
            onRegionSelect={setSelectedRegionIdx}
          />
        </div>

        <div style={styles.sidebar}>
          <QuestionPanel
            questions={questions}
            selectedQuestionId={selectedQuestionId}
            currentPage={currentPage}
            onSelect={(id) => { setSelectedQuestionId(id); setSelectedRegionIdx(null); }}
            onAdd={handleAddQuestion}
            onUpdate={handleUpdateQuestion}
            onDelete={handleDeleteQuestion}
          />
          <ExportPanel
            documentId={documentId}
            examId={examId}
            paperMeta={paperMeta}
            questions={questions}
            onDocumentIdChange={setDocumentId}
            onExamIdChange={setExamId}
            onPaperMetaChange={setPaperMeta}
            onClearSession={handleClearSession}
          />
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: { display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '8px 16px',
    background: '#1e293b',
    color: '#f1f5f9',
    flexShrink: 0,
  },
  fileBtn: {
    marginLeft: 'auto',
    padding: '5px 14px',
    background: '#3b82f6',
    color: '#fff',
    borderRadius: 5,
    cursor: 'pointer',
    fontSize: 13,
  },
  body: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
    gap: 12,
    padding: 12,
  },
  viewer: { flex: 1, overflowY: 'auto' },
  sidebar: { display: 'flex', flexDirection: 'column', gap: 10, overflowY: 'auto', flexShrink: 0 },
};
