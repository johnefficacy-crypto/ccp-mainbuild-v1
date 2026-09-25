import { BANK, TYPES } from "./drillData";
import {
  blanks,
  buildMix,
  dayKey,
  liveStreak,
  listFor,
  loadProgress,
  mmss,
  moduleTotal,
  norm,
  pjCode,
  saveProgress,
  streakAfter,
  STORAGE_KEY,
  twoWrong,
  weakestModule,
  xpAfter,
} from "./drillEngine";

const NOW = new Date(2026, 8, 25, 12);

function memStorage() {
  const m = {};
  return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, m };
}

test("mmss pads and clamps at zero", () => {
  expect(mmss(605)).toBe("10:05");
  expect(mmss(-3)).toBe("00:00");
});

test("xp: +10 correct, +5 hinted, -3 wrong (or 0 without penalty), never below 0", () => {
  expect(xpAfter(20, { ok: true, hinted: false, penalty: true })).toBe(30);
  expect(xpAfter(20, { ok: true, hinted: true, penalty: true })).toBe(25);
  expect(xpAfter(20, { ok: false, hinted: false, penalty: true })).toBe(17);
  expect(xpAfter(20, { ok: false, hinted: false, penalty: false })).toBe(20);
  expect(xpAfter(1, { ok: false, hinted: false, penalty: true })).toBe(0);
});

test("streak: same day keeps, yesterday extends, gap resets; display lapses after a missed day", () => {
  expect(streakAfter(4, dayKey(0, NOW), NOW)).toBe(4);
  expect(streakAfter(4, dayKey(-1, NOW), NOW)).toBe(5);
  expect(streakAfter(4, dayKey(-3, NOW), NOW)).toBe(1);
  expect(liveStreak(4, dayKey(-1, NOW), NOW)).toBe(4);
  expect(liveStreak(4, dayKey(-2, NOW), NOW)).toBe(0);
});

test("daily mix picks distinct question types within bounds", () => {
  const q = buildMix(12);
  expect(q).toHaveLength(12);
  expect(new Set(q.map((x) => `${x.v}:${x.tab}`)).size).toBe(12);
  q.forEach((x) => expect(listFor(x.v, x.tab)[x.i]).toBeDefined());
  expect(buildMix(1)).toHaveLength(4);
  expect(buildMix(99)).toHaveLength(TYPES.length);
});

test("parajumble code maps the given order to P-Q-R-S letters", () => {
  const q = BANK.pj[0];
  expect(pjCode(q, q.given)).toBe("P Q R S");
  expect(pjCode(q, [0, 1, 2, 3])).toBe("Q S P R");
});

test("cloze blanks, hint strikes two wrong options, norm strips punctuation", () => {
  const q = BANK.cloze[0];
  expect(blanks(q)).toEqual([1, 3, 5, 7]);
  const w = twoWrong(["a", "b", "c", "d"], 2);
  expect(w).toHaveLength(2);
  expect(w).not.toContain(2);
  expect(norm("If I were you, I would apologise.")).toBe("if i were you i would apologise");
});

test("module totals count every tab", () => {
  expect(moduleTotal("voc")).toBe(27);
  expect(moduleTotal("pos")).toBe(9);
  expect(moduleTotal("sc")).toBe(9);
  expect(moduleTotal("err")).toBe(6);
});

test("weakest module needs 2+ attempts under 80%", () => {
  expect(weakestModule({ err: { a: 1, c: 0 } })).toBeNull();
  expect(weakestModule({ err: { a: 4, c: 2 }, voc: { a: 4, c: 1 }, pj: { a: 5, c: 5 } }).m.id).toBe("voc");
});

test("progress round-trips through storage and survives junk", () => {
  const st = memStorage();
  saveProgress({ stats: { err: { a: 1, c: 1 } }, xp: 10, streak: 2, lastDay: "2026-9-25", extra: 1 }, st);
  expect(JSON.parse(st.m[STORAGE_KEY])).toEqual({ stats: { err: { a: 1, c: 1 } }, xp: 10, streak: 2, lastDay: "2026-9-25" });
  expect(loadProgress(st).xp).toBe(10);
  st.setItem(STORAGE_KEY, "{not json");
  expect(loadProgress(st)).toEqual({ stats: {}, xp: 0, streak: 0, lastDay: "" });
});
