import { describe, it, expect } from 'vitest';
import {
  canvasRectToNormalized,
  pdfNativeToNormalized,
  normalizedToCanvas,
} from './coords';

describe('canvasRectToNormalized', () => {
  it('normalizes a simple rect on a 1000×500 canvas', () => {
    const bbox = canvasRectToNormalized(100, 50, 500, 200, {
      width: 1000,
      height: 500,
    });
    expect(bbox).toEqual([0.1, 0.1, 0.5, 0.4]);
  });

  it('handles reversed drag direction (x2 < x1, y2 < y1)', () => {
    const bbox = canvasRectToNormalized(500, 200, 100, 50, {
      width: 1000,
      height: 500,
    });
    expect(bbox).toEqual([0.1, 0.1, 0.5, 0.4]);
  });

  it('clamps out-of-bounds values to [0, 1]', () => {
    const bbox = canvasRectToNormalized(-50, -10, 1200, 600, {
      width: 1000,
      height: 500,
    });
    expect(bbox).toEqual([0, 0, 1, 1]);
  });

  it('round-trips back through normalizedToCanvas', () => {
    const dims = { width: 800, height: 1100 };
    const original = canvasRectToNormalized(80, 110, 400, 550, dims);
    const pixels = normalizedToCanvas(original, dims);
    expect(pixels[0]).toBeCloseTo(80);
    expect(pixels[1]).toBeCloseTo(110);
    expect(pixels[2]).toBeCloseTo(400);
    expect(pixels[3]).toBeCloseTo(550);
  });
});

describe('pdfNativeToNormalized', () => {
  // A4 page in PDF points
  const A4 = { width: 595, height: 842 };

  it('converts a bbox near the top-left of an A4 page', () => {
    // PDF (50, 750, 200, 800): near top of page (PDF y increases upward)
    const bbox = pdfNativeToNormalized([50, 750, 200, 800], A4);
    expect(bbox[0]).toBeCloseTo(50 / 595);
    expect(bbox[1]).toBeCloseTo((842 - 800) / 842);
    expect(bbox[2]).toBeCloseTo(200 / 595);
    expect(bbox[3]).toBeCloseTo((842 - 750) / 842);
  });

  it('converts a bbox near the bottom-right of an A4 page', () => {
    const bbox = pdfNativeToNormalized([400, 100, 580, 200], A4);
    expect(bbox[0]).toBeCloseTo(400 / 595);
    expect(bbox[1]).toBeCloseTo((842 - 200) / 842);
    expect(bbox[2]).toBeCloseTo(580 / 595);
    expect(bbox[3]).toBeCloseTo((842 - 100) / 842);
  });

  it('produces values strictly within [0, 1]', () => {
    const bbox = pdfNativeToNormalized([10, 10, 585, 832], A4);
    for (const v of bbox) {
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(1);
    }
  });

  it('round-trips for three sample bboxes (xmin < xmax, ymin < ymax preserved)', () => {
    const samples: Array<[number, number, number, number]> = [
      [50, 300, 250, 600],
      [0, 0, 595, 842],
      [100, 200, 300, 400],
    ];
    for (const s of samples) {
      const norm = pdfNativeToNormalized(s, A4);
      expect(norm[0]).toBeLessThanOrEqual(norm[2]); // xmin <= xmax
      expect(norm[1]).toBeLessThanOrEqual(norm[3]); // ymin <= ymax
    }
  });
});
