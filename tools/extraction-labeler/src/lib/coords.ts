import type { Bbox } from '../types';

export interface PageDimensions {
  width: number;
  height: number;
}

/**
 * Canvas pixel rect (top-left origin) → normalized top-left bbox [0..1].
 * Handles reversed drag direction (x2 < x1 or y2 < y1).
 */
export function canvasRectToNormalized(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  dims: PageDimensions,
): Bbox {
  return [
    clamp(Math.min(x1, x2) / dims.width),
    clamp(Math.min(y1, y2) / dims.height),
    clamp(Math.max(x1, x2) / dims.width),
    clamp(Math.max(y1, y2) / dims.height),
  ];
}

/**
 * PDF-native bbox (bottom-left origin, points) → normalized top-left [0..1].
 * PDF y-axis points upward; we flip to match the top-left convention.
 */
export function pdfNativeToNormalized(
  pdfBbox: [number, number, number, number],
  pageDims: PageDimensions,
): Bbox {
  const [px1, py1, px2, py2] = pdfBbox;
  const xmin = Math.min(px1, px2) / pageDims.width;
  const xmax = Math.max(px1, px2) / pageDims.width;
  // PDF y increases upward; top-left normalized y_min corresponds to the
  // larger PDF y value (higher on the page).
  const ymin = (pageDims.height - Math.max(py1, py2)) / pageDims.height;
  const ymax = (pageDims.height - Math.min(py1, py2)) / pageDims.height;
  return [clamp(xmin), clamp(ymin), clamp(xmax), clamp(ymax)];
}

/** Normalized bbox → canvas pixel coordinates. */
export function normalizedToCanvas(
  bbox: Bbox,
  dims: PageDimensions,
): [number, number, number, number] {
  return [
    bbox[0] * dims.width,
    bbox[1] * dims.height,
    bbox[2] * dims.width,
    bbox[3] * dims.height,
  ];
}

function clamp(v: number): number {
  return Math.max(0, Math.min(1, v));
}
