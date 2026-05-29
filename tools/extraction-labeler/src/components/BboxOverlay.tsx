import { useRef, useEffect, useCallback, useState } from 'react';
import type { Region, Bbox } from '../types';
import { canvasRectToNormalized, normalizedToCanvas } from '../lib/coords';

interface Props {
  width: number;
  height: number;
  /** Regions for the current page only. */
  regions: Region[];
  selectedRegionIdx: number | null;
  onRegionAdd: (bbox: Bbox) => void;
  onRegionDelete: (idx: number) => void;
  onRegionUpdate: (idx: number, bbox: Bbox) => void;
  onRegionSelect: (idx: number | null) => void;
}

const HANDLE_R = 6; // handle hit radius in pixels
const COLORS = {
  region: 'rgba(59,130,246,0.15)',
  regionStroke: 'rgba(59,130,246,0.8)',
  selected: 'rgba(239,68,68,0.2)',
  selectedStroke: 'rgba(239,68,68,0.9)',
  drawing: 'rgba(16,185,129,0.15)',
  drawingStroke: 'rgba(16,185,129,0.9)',
  handle: '#ef4444',
};

type Handle = 0 | 1 | 2 | 3; // NW NE SE SW

type Drag =
  | { mode: 'idle' }
  | { mode: 'drawing'; sx: number; sy: number; cx: number; cy: number }
  | { mode: 'moving'; idx: number; ox: number; oy: number; origBbox: Bbox }
  | { mode: 'resizing'; idx: number; handle: Handle; ox: number; oy: number; origBbox: Bbox };

function cornerHandles(px: [number, number, number, number]): Array<{ x: number; y: number }> {
  return [
    { x: px[0], y: px[1] }, // NW
    { x: px[2], y: px[1] }, // NE
    { x: px[2], y: px[3] }, // SE
    { x: px[0], y: px[3] }, // SW
  ];
}

function hitHandle(mx: number, my: number, px: [number, number, number, number]): Handle | null {
  const handles = cornerHandles(px);
  for (let i = 0; i < handles.length; i++) {
    const h = handles[i];
    if (Math.hypot(mx - h.x, my - h.y) <= HANDLE_R + 3) return i as Handle;
  }
  return null;
}

function hitRegion(mx: number, my: number, px: [number, number, number, number]): boolean {
  return mx >= px[0] && mx <= px[2] && my >= px[1] && my <= px[3];
}

export default function BboxOverlay({
  width,
  height,
  regions,
  selectedRegionIdx,
  onRegionAdd,
  onRegionDelete,
  onRegionUpdate,
  onRegionSelect,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [drag, setDrag] = useState<Drag>({ mode: 'idle' });
  const dims = { width, height };

  // Draw everything on the canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);

    regions.forEach((r, idx) => {
      const px = normalizedToCanvas(r.bbox, dims) as [number, number, number, number];
      const isSelected = idx === selectedRegionIdx;
      ctx.fillStyle = isSelected ? COLORS.selected : COLORS.region;
      ctx.strokeStyle = isSelected ? COLORS.selectedStroke : COLORS.regionStroke;
      ctx.lineWidth = isSelected ? 2 : 1.5;
      ctx.fillRect(px[0], px[1], px[2] - px[0], px[3] - px[1]);
      ctx.strokeRect(px[0], px[1], px[2] - px[0], px[3] - px[1]);

      if (isSelected) {
        ctx.fillStyle = COLORS.handle;
        cornerHandles(px).forEach((h) => {
          ctx.beginPath();
          ctx.arc(h.x, h.y, HANDLE_R, 0, Math.PI * 2);
          ctx.fill();
        });
      }
    });

    // In-progress drawing rect
    if (drag.mode === 'drawing') {
      const px = [
        Math.min(drag.sx, drag.cx), Math.min(drag.sy, drag.cy),
        Math.max(drag.sx, drag.cx), Math.max(drag.sy, drag.cy),
      ];
      ctx.fillStyle = COLORS.drawing;
      ctx.strokeStyle = COLORS.drawingStroke;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.fillRect(px[0], px[1], px[2] - px[0], px[3] - px[1]);
      ctx.strokeRect(px[0], px[1], px[2] - px[0], px[3] - px[1]);
      ctx.setLineDash([]);
    }
  }, [width, height, regions, selectedRegionIdx, drag, dims]);

  const getPos = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const rect = canvasRef.current!.getBoundingClientRect();
      return {
        x: (e.clientX - rect.left) * (width / rect.width),
        y: (e.clientY - rect.top) * (height / rect.height),
      };
    },
    [width, height],
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      e.preventDefault();
      canvasRef.current?.focus();
      const { x, y } = getPos(e);

      // Check handles on selected region first
      if (selectedRegionIdx !== null) {
        const r = regions[selectedRegionIdx];
        if (r) {
          const px = normalizedToCanvas(r.bbox, dims) as [number, number, number, number];
          const h = hitHandle(x, y, px);
          if (h !== null) {
            setDrag({ mode: 'resizing', idx: selectedRegionIdx, handle: h, ox: x, oy: y, origBbox: [...r.bbox] as Bbox });
            return;
          }
          if (hitRegion(x, y, px)) {
            setDrag({ mode: 'moving', idx: selectedRegionIdx, ox: x, oy: y, origBbox: [...r.bbox] as Bbox });
            return;
          }
        }
      }

      // Hit-test all regions (top to bottom, last wins)
      for (let i = regions.length - 1; i >= 0; i--) {
        const px = normalizedToCanvas(regions[i].bbox, dims) as [number, number, number, number];
        if (hitRegion(x, y, px)) {
          onRegionSelect(i);
          setDrag({ mode: 'moving', idx: i, ox: x, oy: y, origBbox: [...regions[i].bbox] as Bbox });
          return;
        }
      }

      // Start drawing
      onRegionSelect(null);
      setDrag({ mode: 'drawing', sx: x, sy: y, cx: x, cy: y });
    },
    [getPos, regions, selectedRegionIdx, dims, onRegionSelect],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (drag.mode === 'idle') return;
      const { x, y } = getPos(e);

      if (drag.mode === 'drawing') {
        setDrag((d) => d.mode === 'drawing' ? { ...d, cx: x, cy: y } : d);
        return;
      }

      if (drag.mode === 'moving') {
        const dx = (x - drag.ox) / width;
        const dy = (y - drag.oy) / height;
        const ob = drag.origBbox;
        const newBbox: Bbox = [
          Math.max(0, Math.min(1 - (ob[2] - ob[0]), ob[0] + dx)),
          Math.max(0, Math.min(1 - (ob[3] - ob[1]), ob[1] + dy)),
          0, 0,
        ];
        newBbox[2] = newBbox[0] + (ob[2] - ob[0]);
        newBbox[3] = newBbox[1] + (ob[3] - ob[1]);
        onRegionUpdate(drag.idx, newBbox);
        return;
      }

      if (drag.mode === 'resizing') {
        const ob = drag.origBbox;
        const nx = x / width;
        const ny = y / height;
        let [xmin, ymin, xmax, ymax] = ob;
        switch (drag.handle) {
          case 0: xmin = Math.min(nx, xmax - 0.01); ymin = Math.min(ny, ymax - 0.01); break; // NW
          case 1: xmax = Math.max(nx, xmin + 0.01); ymin = Math.min(ny, ymax - 0.01); break; // NE
          case 2: xmax = Math.max(nx, xmin + 0.01); ymax = Math.max(ny, ymin + 0.01); break; // SE
          case 3: xmin = Math.min(nx, xmax - 0.01); ymax = Math.max(ny, ymin + 0.01); break; // SW
        }
        onRegionUpdate(drag.idx, [
          Math.max(0, xmin), Math.max(0, ymin),
          Math.min(1, xmax), Math.min(1, ymax),
        ]);
      }
    },
    [drag, getPos, width, height, onRegionUpdate],
  );

  const handleMouseUp = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (drag.mode === 'drawing') {
        const { x, y } = getPos(e);
        const bbox = canvasRectToNormalized(drag.sx, drag.sy, x, y, dims);
        const minSize = 0.005;
        if (bbox[2] - bbox[0] > minSize && bbox[3] - bbox[1] > minSize) {
          onRegionAdd(bbox);
        }
      }
      setDrag({ mode: 'idle' });
    },
    [drag, getPos, dims, onRegionAdd],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLCanvasElement>) => {
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedRegionIdx !== null) {
        e.preventDefault();
        onRegionDelete(selectedRegionIdx);
      }
    },
    [selectedRegionIdx, onRegionDelete],
  );

  const cursor =
    drag.mode === 'drawing'
      ? 'crosshair'
      : drag.mode === 'moving'
      ? 'grabbing'
      : drag.mode === 'resizing'
      ? 'nwse-resize'
      : 'crosshair';

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{ position: 'absolute', top: 0, left: 0, cursor, outline: 'none' }}
      tabIndex={0}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={() => { if (drag.mode === 'drawing') setDrag({ mode: 'idle' }); }}
      onKeyDown={handleKeyDown}
    />
  );
}
