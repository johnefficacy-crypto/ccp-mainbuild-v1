import { useRef, useEffect, useState } from 'react';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import type { Region, Bbox } from '../types';
import BboxOverlay from './BboxOverlay';

interface Props {
  pdfDoc: PDFDocumentProxy | null;
  currentPage: number;
  totalPages: number;
  regions: Region[];
  selectedRegionIdx: number | null;
  onPageChange: (page: number) => void;
  onRegionAdd: (bbox: Bbox) => void;
  onRegionDelete: (idx: number) => void;
  onRegionUpdate: (idx: number, bbox: Bbox) => void;
  onRegionSelect: (idx: number | null) => void;
}

const SCALE = 1.5;

export default function PdfViewer({
  pdfDoc,
  currentPage,
  totalPages,
  regions,
  selectedRegionIdx,
  onPageChange,
  onRegionAdd,
  onRegionDelete,
  onRegionUpdate,
  onRegionSelect,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [canvasDims, setCanvasDims] = useState({ width: 0, height: 0 });
  const [jumpValue, setJumpValue] = useState('');
  const renderTaskRef = useRef<{ cancel: () => void } | null>(null);

  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;

    let cancelled = false;

    async function render() {
      const page = await pdfDoc!.getPage(currentPage);
      if (cancelled) return;
      const viewport = page.getViewport({ scale: SCALE });
      const canvas = canvasRef.current!;
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      setCanvasDims({ width: viewport.width, height: viewport.height });

      const ctx = canvas.getContext('2d')!;
      const task = page.render({ canvasContext: ctx, viewport });
      renderTaskRef.current = task;
      try {
        await task.promise;
      } catch {
        // Cancelled render — ignore
      }
    }

    // Cancel any in-progress render
    renderTaskRef.current?.cancel();
    render();

    return () => {
      cancelled = true;
      renderTaskRef.current?.cancel();
    };
  }, [pdfDoc, currentPage]);

  function goTo(page: number) {
    const p = Math.max(1, Math.min(totalPages, page));
    onPageChange(p);
  }

  function handleJump(e: React.FormEvent) {
    e.preventDefault();
    const n = parseInt(jumpValue, 10);
    if (!isNaN(n)) goTo(n);
    setJumpValue('');
  }

  if (!pdfDoc) {
    return (
      <div style={styles.placeholder}>
        <p style={{ color: '#6b7280' }}>Load a PDF to begin labeling.</p>
      </div>
    );
  }

  return (
    <div style={styles.wrapper}>
      <div style={styles.nav}>
        <button onClick={() => goTo(currentPage - 1)} disabled={currentPage <= 1}>
          ◀ Prev
        </button>
        <span style={{ margin: '0 8px' }}>
          Page {currentPage} / {totalPages}
        </span>
        <button onClick={() => goTo(currentPage + 1)} disabled={currentPage >= totalPages}>
          Next ▶
        </button>
        <form onSubmit={handleJump} style={{ marginLeft: 12, display: 'inline-flex', gap: 4 }}>
          <input
            type="number"
            min={1}
            max={totalPages}
            value={jumpValue}
            onChange={(e) => setJumpValue(e.target.value)}
            placeholder="Go to…"
            style={{ width: 70, padding: '2px 6px', border: '1px solid #d1d5db', borderRadius: 4 }}
          />
          <button type="submit">Go</button>
        </form>
      </div>

      <div style={{ position: 'relative', display: 'inline-block', lineHeight: 0 }}>
        <canvas ref={canvasRef} style={{ display: 'block', border: '1px solid #d1d5db' }} />
        {canvasDims.width > 0 && (
          <BboxOverlay
            width={canvasDims.width}
            height={canvasDims.height}
            regions={regions}
            selectedRegionIdx={selectedRegionIdx}
            onRegionAdd={onRegionAdd}
            onRegionDelete={onRegionDelete}
            onRegionUpdate={onRegionUpdate}
            onRegionSelect={onRegionSelect}
          />
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: { display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-start' },
  placeholder: {
    width: 595,
    height: 400,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '2px dashed #d1d5db',
    borderRadius: 8,
  },
  nav: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '6px 0',
  },
};
