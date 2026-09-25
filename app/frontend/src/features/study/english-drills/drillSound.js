/**
 * Verdict tones via Web Audio — a rising two-note chime for correct, a low
 * square-wave double buzz for wrong. No audio assets; fails silently where
 * AudioContext is unavailable (tests, old browsers, autoplay blocks).
 */
let ctx = null;

export function playVerdict(ok) {
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    ctx = ctx || new AC();
    const t = ctx.currentTime;
    const beep = (type, f1, f2, st, dur, vol) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = type;
      o.frequency.setValueAtTime(f1, t + st);
      o.frequency.linearRampToValueAtTime(f2, t + st + dur);
      g.gain.setValueAtTime(0.0001, t + st);
      g.gain.exponentialRampToValueAtTime(vol, t + st + 0.01);
      g.gain.exponentialRampToValueAtTime(0.0001, t + st + dur);
      o.connect(g);
      g.connect(ctx.destination);
      o.start(t + st);
      o.stop(t + st + dur + 0.02);
    };
    if (ok) {
      beep("sine", 660, 660, 0, 0.2, 0.16);
      beep("sine", 990, 990, 0.09, 0.28, 0.16);
    } else {
      beep("square", 150, 120, 0, 0.18, 0.12);
      beep("square", 150, 105, 0.22, 0.3, 0.12);
    }
  } catch (e) {
    /* audio is best-effort */
  }
}

/** Horizontal shake on a wrong answer (Web Animations API; skipped under reduced motion). */
export function shake(el) {
  if (!el || !el.animate) return;
  try {
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  } catch (e) {
    /* ignore */
  }
  el.animate(
    [
      { transform: "translateX(0)" },
      { transform: "translateX(-9px)" },
      { transform: "translateX(8px)" },
      { transform: "translateX(-6px)" },
      { transform: "translateX(4px)" },
      { transform: "translateX(0)" },
    ],
    { duration: 420, easing: "ease-out" },
  );
}
