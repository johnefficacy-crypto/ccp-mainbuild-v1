/**
 * Pure helpers for the English verbal drills: question lookup, scoring, streak
 * and local persistence. No React here, so every rule is unit-testable.
 */
import { BANK, MODS, TYPES } from "./drillData";

export const STORAGE_KEY = "ccp-english-v2";
export const SEQ_LETTERS = "PQRSTU";

export const XP_CORRECT = 10;
export const XP_CORRECT_HINTED = 5;
export const XP_WRONG = -3;
export const XP_HINT = -2;

/** Local-calendar day key, offset by `off` days (e.g. -1 = yesterday). */
export function dayKey(off = 0, now = new Date()) {
  const d = new Date(now);
  d.setDate(d.getDate() + off);
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
}

export function mmss(sec) {
  const s = Math.max(0, Math.round(sec));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

/** Question list for a module + tab. */
export function listFor(v, tab) {
  if (v === "voc") return BANK.voc[tab] || [];
  if (v === "pos") return tab === "mis" ? BANK.posMis : BANK.posTag;
  if (v === "sc") return BANK.sc[tab] || [];
  return BANK[v] || [];
}

export function moduleTotal(id) {
  if (id === "voc") return Object.values(BANK.voc).reduce((n, l) => n + l.length, 0);
  if (id === "pos") return BANK.posTag.length + BANK.posMis.length;
  if (id === "sc") return Object.values(BANK.sc).reduce((n, l) => n + l.length, 0);
  return (BANK[id] || []).length;
}

export function typeLabel(v, tab) {
  const t = TYPES.find(([tv, tt]) => tv === v && tt === (tab || ""));
  return t ? t[2] : "";
}

/** Sequence code for a parajumble order, e.g. "Q S P R". */
export function pjCode(q, order) {
  return order.map((o) => SEQ_LETTERS[q.given.indexOf(o)]).join(" ");
}

export function norm(x) {
  return x.toLowerCase().replace(/[^a-z ]/g, " ").replace(/\s+/g, " ").trim();
}

/** Indices of the blank (non-string) parts of a cloze passage. */
export function blanks(q) {
  return q.parts.map((p, k) => (typeof p === "string" ? -1 : k)).filter((k) => k > -1);
}

/** Two random wrong-option indices to strike out for a hint. */
export function twoWrong(options, answer, rand = Math.random) {
  return options
    .map((_, k) => k)
    .filter((k) => k !== answer)
    .sort(() => rand() - 0.5)
    .slice(0, 2);
}

export function shuffle(arr, rand = Math.random) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rand() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** A rotating daily-mix queue: `size` distinct question types, one random item each. */
export function buildMix(size, rand = Math.random) {
  const n = Math.max(4, Math.min(TYPES.length, size));
  return shuffle(TYPES, rand)
    .slice(0, n)
    .map(([v, tab]) => ({ v, tab, i: Math.floor(rand() * listFor(v, tab).length) }));
}

export function xpAfter(xp, { ok, hinted, penalty }) {
  const delta = ok ? (hinted ? XP_CORRECT_HINTED : XP_CORRECT) : penalty ? XP_WRONG : 0;
  return Math.max(0, xp + delta);
}

/** Streak after answering today: same day keeps it, yesterday extends it, else resets to 1. */
export function streakAfter(streak, lastDay, now = new Date()) {
  if (lastDay === dayKey(0, now)) return streak;
  if (lastDay === dayKey(-1, now)) return streak + 1;
  return 1;
}

/** Streak to display: lapses to 0 once a full day is missed. */
export function liveStreak(streak, lastDay, now = new Date()) {
  return lastDay === dayKey(0, now) || lastDay === dayKey(-1, now) ? streak : 0;
}

export function pct(st) {
  return st && st.a ? Math.round((st.c / st.a) * 100) : null;
}

/** Weakest module: at least 2 attempts and under 80% accuracy, lowest first. */
export function weakestModule(stats) {
  return (
    MODS.map((m) => ({ m, p: pct(stats[m.id]), st: stats[m.id] }))
      .filter((x) => x.st && x.st.a >= 2 && x.p < 80)
      .sort((x, y) => x.p - y.p)[0] || null
  );
}

export function loadProgress(storage = safeStorage()) {
  try {
    const sv = JSON.parse(storage?.getItem(STORAGE_KEY) || "{}");
    return { stats: sv.stats || {}, xp: sv.xp || 0, streak: sv.streak || 0, lastDay: sv.lastDay || "" };
  } catch (e) {
    return { stats: {}, xp: 0, streak: 0, lastDay: "" };
  }
}

export function saveProgress({ stats, xp, streak, lastDay }, storage = safeStorage()) {
  try {
    storage?.setItem(STORAGE_KEY, JSON.stringify({ stats, xp, streak, lastDay }));
  } catch (e) {
    /* storage full or blocked — progress stays in memory for this visit */
  }
}

function safeStorage() {
  try {
    return window.localStorage;
  } catch (e) {
    return null;
  }
}
