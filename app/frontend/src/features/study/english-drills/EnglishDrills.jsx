/**
 * EnglishDrills — verbal-ability practice for SSC / Banking / UPSC CSAT /
 * State PSC / Railways / Defence aspirants (Claude Design "English Practice v2").
 *
 * Views: overview (daily mix + nine modules) → practice set per module/tab, or a
 * timed daily mix that rotates all 17 question types → result sheet.
 *
 * Feedback loop: a wrong answer buzzes, shakes the card and states the rule; a
 * hint costs XP and narrows the question (strikes two options, places a word,
 * tags the verbs…). XP, streak and per-module accuracy persist in localStorage
 * (drillEngine.STORAGE_KEY) — this surface is client-only and makes no API calls.
 */
import React, { useEffect, useRef, useState } from "react";

import { INSTRUCTIONS, MODS, POS_TAGS, TABS, VOC_PROMPT, BANK } from "./drillData";
import {
  SEQ_LETTERS,
  blanks,
  buildMix,
  dayKey,
  liveStreak,
  listFor,
  loadProgress,
  mmss,
  moduleTotal,
  norm,
  pct,
  pjCode,
  saveProgress,
  streakAfter,
  twoWrong,
  typeLabel,
  weakestModule,
  xpAfter,
  XP_HINT,
} from "./drillEngine";
import { playVerdict, shake } from "./drillSound";
import "./englishDrills.css";

const K = {
  ink: "var(--color-text)",
  mut: "var(--color-neutral-700)",
  line: "var(--color-divider)",
  acc: "var(--color-accent)",
  accInk: "var(--color-accent-700)",
  accT: "var(--color-accent-100)",
  ok: "var(--ed-ok)",
  okT: "var(--ed-ok-tint)",
  bad: "var(--ed-bad)",
  badT: "var(--ed-bad-tint)",
  pend: "var(--color-neutral-300)",
  paper: "var(--color-bg)",
};

const DEFAULT_TABS = { voc: "syn", pos: "tag", sc: "build" };

function fresh() {
  return {
    fb: null,
    solved: false,
    counted: false,
    hinted: false,
    elim: [],
    pick: null,
    pjOrder: null,
    pjSel: null,
    dragFrom: null,
    dragOver: null,
    pjChecked: false,
    posTags: {},
    posChecked: false,
    scPicked: [],
    scChecked: false,
    clozeSel: {},
    clozeActive: null,
    clozeElim: {},
  };
}

function initialState() {
  return {
    view: "home",
    tabs: DEFAULT_TABS,
    idx: {},
    ...loadProgress(),
    sound: true,
    posTool: "N",
    quiz: null,
    ...fresh(),
  };
}

function curOf(s) {
  if (s.view === "quiz") {
    const it = s.quiz.queue[s.quiz.pos];
    return { v: it.v, tab: it.tab, i: it.i, L: listFor(it.v, it.tab), quiz: true };
  }
  const v = s.view;
  const tab = s.tabs[v] || "";
  return { v, tab, i: s.idx[`${v}:${tab}`] || 0, L: listFor(v, tab), quiz: false };
}

const mkFb = (type, title, body, rule) => ({ type, title, body, rule });

function scrollTop() {
  try {
    window.scrollTo(0, 0);
  } catch (e) {
    /* jsdom */
  }
}

export default function EnglishDrills({
  mixSize = 12,
  mixMinutes = 10,
  xpPenalty = true,
  sound = true,
  autoAdvance = false,
}) {
  const [state, setState] = useState(initialState);
  const sRef = useRef(state);
  sRef.current = state;
  const cardRef = useRef(null);
  const advRef = useRef(null);
  const [, setTick] = useState(0);

  const update = (patch) => {
    const next = { ...sRef.current, ...patch };
    sRef.current = next;
    setState(next);
    return next;
  };

  const remaining = () => {
    const Q = sRef.current.quiz;
    return Q ? Q.dur - (Date.now() - Q.start) / 1000 : 0;
  };

  // ── navigation ────────────────────────────────────────────────────────
  const go = (id, tab) => {
    clearTimeout(advRef.current);
    const s = sRef.current;
    update({ view: id, tabs: tab ? { ...s.tabs, [id]: tab } : s.tabs, ...fresh() });
    scrollTop();
  };
  const startMix = () => {
    const queue = buildMix(mixSize);
    update({
      view: "quiz",
      quiz: { queue, pos: 0, start: Date.now(), dur: mixMinutes * 60, results: [], xp0: sRef.current.xp, end: null },
      ...fresh(),
    });
    scrollTop();
  };
  const finish = () => {
    clearTimeout(advRef.current);
    update({ view: "result", quiz: { ...sRef.current.quiz, end: Date.now() }, ...fresh() });
    scrollTop();
  };
  const next = () => {
    clearTimeout(advRef.current);
    const s = sRef.current;
    if (s.view === "quiz") {
      if (s.quiz.pos >= s.quiz.queue.length - 1) return finish();
      return update({ quiz: { ...s.quiz, pos: s.quiz.pos + 1 }, ...fresh() });
    }
    const c = curOf(s);
    const key = `${c.v}:${c.tab}`;
    if (c.i >= c.L.length - 1) {
      update({ idx: { ...s.idx, [key]: 0 } });
      return go("home");
    }
    return update({ idx: { ...s.idx, [key]: c.i + 1 }, ...fresh() });
  };
  const prev = () => {
    const s = sRef.current;
    const c = curOf(s);
    if (c.quiz || c.i === 0) return;
    update({ idx: { ...s.idx, [`${c.v}:${c.tab}`]: c.i - 1 }, ...fresh() });
  };

  // Daily-mix clock: re-render each second, auto-finish at zero.
  useEffect(() => {
    if (state.view !== "quiz") return undefined;
    const id = setInterval(() => {
      if (sRef.current.view !== "quiz") return;
      if (remaining() <= 0) finish();
      else setTick((t) => t + 1);
    }, 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.view]);
  useEffect(() => () => clearTimeout(advRef.current), []);

  // ── scoring ───────────────────────────────────────────────────────────
  const react = (ok) => {
    if (sRef.current.sound && sound !== false) playVerdict(ok);
    if (!ok) shake(cardRef.current);
    else if (autoAdvance) {
      clearTimeout(advRef.current);
      advRef.current = setTimeout(next, 1500);
    }
  };
  const record = (ok) => {
    const s = sRef.current;
    if (s.counted) return;
    const c = curOf(s);
    const st = { ...s.stats };
    const cu = st[c.v] || { a: 0, c: 0 };
    st[c.v] = { a: cu.a + 1, c: cu.c + (ok ? 1 : 0) };
    const patch = {
      stats: st,
      xp: xpAfter(s.xp, { ok, hinted: s.hinted, penalty: xpPenalty }),
      streak: streakAfter(s.streak, s.lastDay),
      lastDay: dayKey(0),
      counted: true,
    };
    if (s.view === "quiz") {
      const results = s.quiz.results.slice();
      results[s.quiz.pos] = ok;
      patch.quiz = { ...s.quiz, results };
    }
    saveProgress(update(patch));
  };
  const pickOne = (k, ok, f) => {
    const s = sRef.current;
    if (s.solved || s.elim.includes(k)) return;
    record(ok);
    update({ pick: k, solved: true, fb: f });
    react(ok);
  };

  // ── parajumble ────────────────────────────────────────────────────────
  const q = () => {
    const c = curOf(sRef.current);
    return c.L[c.i] || {};
  };
  const pjMove = (from, to) => {
    const s = sRef.current;
    if (s.solved || from == null || from === to) return update({ dragFrom: null, dragOver: null });
    const arr = (s.pjOrder || q().given).slice();
    const [x] = arr.splice(from, 1);
    arr.splice(to, 0, x);
    return update({ pjOrder: arr, dragFrom: null, dragOver: null, pjChecked: false, pjSel: null, fb: null });
  };
  const pjTap = (pos) => {
    const s = sRef.current;
    if (s.solved) return;
    if (s.pjSel == null) return update({ pjSel: pos });
    if (s.pjSel === pos) return update({ pjSel: null });
    const arr = (s.pjOrder || q().given).slice();
    [arr[s.pjSel], arr[pos]] = [arr[pos], arr[s.pjSel]];
    update({ pjOrder: arr, pjSel: null, pjChecked: false, fb: null });
  };

  // ── hint / check / reveal ─────────────────────────────────────────────
  const hint = () => {
    const s = sRef.current;
    if (s.hinted || s.solved) return;
    const c = curOf(s);
    const qq = c.L[c.i];
    const v = c.v;
    const patch = { hinted: true, xp: Math.max(0, s.xp + XP_HINT) };
    let msg = "";
    if (v === "voc" || v === "imp" || v === "rc") {
      patch.elim = twoWrong(qq.o, qq.a);
      msg = "Two wrong options have been struck out.";
    } else if (v === "pj") msg = `The sequence begins with part ${SEQ_LETTERS[qq.given.indexOf(0)]}.`;
    else if (v === "err") msg = qq.rule;
    else if (v === "ce") msg = `Look closely at: ${qq.tag.toLowerCase()}.`;
    else if (v === "pos" && c.tab === "tag") {
      const tags = { ...s.posTags };
      qq.w.forEach((w, k) => {
        if (w[1] === "V") tags[k] = "V";
      });
      patch.posTags = tags;
      msg = "The verbs have been tagged for you.";
    } else if (v === "pos") {
      const [a, b] = qq.pos.toLowerCase().split(" → ");
      msg = `One ${a} is used where ${/^[aeiou]/.test(b) ? "an " : "a "}${b} is needed.`;
    } else if (v === "sc") {
      const first = norm(qq.ans[0]).split(" ")[0];
      patch.scPicked = [qq.t.findIndex((w) => norm(w) === first)];
      patch.scChecked = false;
      msg = "The first word has been placed for you.";
    } else if (v === "cloze") {
      const ce = {};
      blanks(qq).forEach((k) => {
        ce[k] = twoWrong(qq.parts[k].o, qq.parts[k].a);
      });
      patch.clozeElim = ce;
      msg = "Two wrong options have been removed from every blank.";
    }
    patch.fb = mkFb("hint", "Hint · −2 XP", msg);
    saveProgress(update(patch));
  };

  const check = () => {
    const s = sRef.current;
    const c = curOf(s);
    const v = c.v;
    const qq = c.L[c.i];
    if (v === "pj") {
      const order = s.pjOrder || qq.given;
      const n = order.filter((o, i) => o === i).length;
      const ok = n === order.length;
      record(ok);
      update({
        pjChecked: true,
        pjSel: null,
        solved: ok,
        fb: ok
          ? mkFb("ok", `Correct sequence — ${pjCode(qq, order)}`, qq.note)
          : mkFb("bad", "Not in order", `${n} of ${order.length} parts are in place. Rearrange and check again, or reveal the answer.`),
      });
      react(ok);
    } else if (v === "pos") {
      const left = qq.w.filter((_, k) => !s.posTags[k]).length;
      if (left) {
        update({ fb: mkFb("info", "Tag every word first", `${left}${left === 1 ? " word is" : " words are"} still untagged.`) });
        return;
      }
      const right = qq.w.filter((w, k) => s.posTags[k] === w[1]).length;
      const ok = right === qq.w.length;
      record(ok);
      update({
        posChecked: true,
        solved: true,
        fb: ok
          ? mkFb("ok", `All ${right} words tagged correctly`, "", qq.rule)
          : mkFb("bad", `${right} of ${qq.w.length} correct`, "Corrections are shown under each word.", qq.rule),
      });
      react(ok);
    } else if (v === "sc") {
      if (s.scPicked.length < qq.t.length) {
        update({ fb: mkFb("info", "Use every word", `${qq.t.length - s.scPicked.length} word(s) still in the bank.`) });
        return;
      }
      const built = s.scPicked.map((i) => qq.t[i]).join(" ");
      const ok = qq.ans.some((a) => norm(a) === norm(built));
      record(ok);
      update({
        scChecked: true,
        solved: ok,
        fb: ok
          ? mkFb("ok", "Well built", qq.ans[0], qq.note)
          : mkFb("bad", "Not quite", "Tap placed words to send them back and try again, or reveal the answer."),
      });
      react(ok);
    } else if (v === "cloze") {
      const B = blanks(qq);
      const left = B.filter((k) => s.clozeSel[k] == null).length;
      if (left) {
        update({ fb: mkFb("info", "Fill every blank first", `${left} blank(s) still empty.`) });
        return;
      }
      const wrong = B.filter((k) => s.clozeSel[k] !== qq.parts[k].a);
      const ok = wrong.length === 0;
      record(ok);
      update({
        solved: true,
        fb: ok
          ? mkFb("ok", `All ${B.length} blanks correct`, "", qq.rule)
          : mkFb(
              "bad",
              `${B.length - wrong.length} of ${B.length} correct`,
              `Answers: ${wrong.map((k) => `(${B.indexOf(k) + 1}) ${qq.parts[k].o[qq.parts[k].a]}`).join(" · ")}`,
              qq.rule,
            ),
      });
      react(ok);
    }
  };

  const reveal = () => {
    const s = sRef.current;
    const c = curOf(s);
    const qq = c.L[c.i];
    record(false);
    if (c.v === "pj") {
      const id = qq.parts.map((_, i) => i);
      update({ pjOrder: id, pjChecked: true, solved: true, fb: mkFb("info", `Answer: ${pjCode(qq, id)}`, qq.note) });
    }
    if (c.v === "sc") {
      const used = [];
      norm(qq.ans[0])
        .split(" ")
        .forEach((tok) => {
          const i = qq.t.findIndex((w, j) => !used.includes(j) && norm(w) === tok);
          if (i > -1) used.push(i);
        });
      update({ scPicked: used, scChecked: true, solved: true, fb: mkFb("info", "Answer", qq.ans[0], qq.note) });
    }
  };

  // ── render ────────────────────────────────────────────────────────────
  const s = state;
  const v = s.view;
  let attempts = 0;
  let correct = 0;
  Object.values(s.stats).forEach((x) => {
    attempts += x.a;
    correct += x.c;
  });
  const streakNow = liveStreak(s.streak, s.lastDay);
  const activeNav = v === "quiz" || v === "result" ? "home" : v;
  const inQ = v !== "home" && v !== "result";

  return (
    <div className="ed-root" data-testid="english-drills">
      <header className="ed-header">
        <button type="button" className="ed-brand" onClick={() => go("home")}>
          <span className="ed-brand-name">Verbal drills</span>
          <span className="ed-brand-tag">English</span>
        </button>
        <div className="ed-stats">
          <Stat label="Streak" value={`${streakNow}${streakNow === 1 ? " day" : " days"}`} testId="ed-streak" />
          <Stat label="XP" value={String(s.xp)} testId="ed-xp" />
          <Stat label="Accuracy" value={attempts ? `${Math.round((correct / attempts) * 100)}%` : "—"} testId="ed-accuracy" />
          <button
            type="button"
            className="ed-btn ed-btn--sm"
            aria-pressed={s.sound}
            onClick={() => update({ sound: !s.sound })}
          >
            {s.sound ? "♪ Sound on" : "♪ Sound off"}
          </button>
        </div>
      </header>

      <nav className="ed-strip" aria-label="English modules">
        {[{ id: "home", name: "Overview" }, ...MODS].map((m) => (
          <button
            key={m.id}
            type="button"
            className="ed-strip-item"
            aria-current={activeNav === m.id ? "page" : undefined}
            onClick={() => go(m.id)}
          >
            {m.name}
          </button>
        ))}
      </nav>

      <main className="ed-main">
        <div className="ed-col">
          {v === "home" && (
            <Home s={s} mixSize={mixSize} mixMinutes={mixMinutes} xpPenalty={xpPenalty} go={go} startMix={startMix} />
          )}
          {v === "result" && s.quiz && <Result s={s} go={go} startMix={startMix} />}
          {inQ && (
            <Question
              s={s}
              cardRef={cardRef}
              remaining={remaining()}
              handlers={{ update, go, next, prev, finish, pickOne, pjMove, pjTap, hint, check, reveal }}
            />
          )}
        </div>
      </main>
    </div>
  );
}

function Stat({ label, value, testId }) {
  return (
    <div className="ed-stat">
      <span className="ed-stat-label">{label}</span>
      <span className="ed-stat-value" data-testid={testId}>
        {value}
      </span>
    </div>
  );
}

// ── overview ────────────────────────────────────────────────────────────
function Home({ s, mixSize, mixMinutes, xpPenalty, go, startMix }) {
  const size = Math.max(4, Math.min(17, mixSize));
  const weak = weakestModule(s.stats);
  const today = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long" });
  return (
    <div className="ed-stack" style={{ gap: 32 }}>
      <div>
        <div className="ed-kicker">Verbal ability · SSC · Banking · UPSC CSAT · State PSC · Railways · Defence</div>
        <h1 className="ed-hero-title">The English section, drilled daily.</h1>
        <p className="ed-lede">
          Nine drills modelled on the question patterns examiners actually set — from parajumbles and cloze passages to
          parts of speech. Every wrong answer buzzes, states the rule it broke, and is logged against your weak areas.
        </p>
      </div>

      <div className="ed-mixcard">
        <div className="ed-stack" style={{ gap: 12 }}>
          <div className="ed-kicker ed-kicker--acc">Daily mix · {today}</div>
          <h2 className="ed-mix-title">
            {size} questions, {mixMinutes} minutes, every type.
          </h2>
          <p className="ed-mix-copy">
            Question types rotate at random, so no two mixes are alike. Answer, hear the verdict, read the rule, move on —
            before the clock runs out.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 6 }}>
            <button type="button" className="ed-btn ed-btn--primary ed-btn--lg" onClick={startMix}>
              Start today’s mix →
            </button>
          </div>
        </div>
        <div className="ed-stack">
          <div className="ed-row">
            <span>Questions</span>
            <span className="ed-row-value">{size}</span>
          </div>
          <div className="ed-row">
            <span>Time limit</span>
            <span className="ed-row-value">{mixMinutes} min</span>
          </div>
          <div className="ed-row">
            <span>Correct · with hint</span>
            <span className="ed-row-value">+10 · +5 XP</span>
          </div>
          <div className="ed-row">
            <span>Wrong · hint cost</span>
            <span className="ed-row-value">{xpPenalty ? "−3" : "0"} · −2 XP</span>
          </div>
        </div>
      </div>

      {weak && (
        <div className="ed-weak" data-testid="ed-weakest">
          <span>
            <span className="ed-kicker ed-kicker--bad" style={{ marginRight: 10 }}>
              Weakest area
            </span>
            <em>{weak.m.name}</em> — {weak.p}% accuracy so far
          </span>
          <button type="button" className="ed-btn" onClick={() => go(weak.m.id)}>
            Practise it
          </button>
        </div>
      )}

      <div className="ed-stack" style={{ gap: 16 }}>
        <h3 style={{ fontWeight: 600, fontSize: 26 }}>Practise by module</h3>
        <div className="ed-modgrid">
          {MODS.map((m, k) => {
            const p = pct(s.stats[m.id]);
            const ink = p == null ? K.mut : p >= 80 ? K.ok : p >= 50 ? K.ink : K.bad;
            return (
              <button
                key={m.id}
                type="button"
                className="ed-modcard"
                data-testid={`ed-module-${m.id}`}
                onClick={() => go(m.id)}
              >
                <span className="ed-kicker ed-num" style={{ fontSize: 10.5 }}>
                  {String(k + 1).padStart(2, "0")} · {m.tag}
                </span>
                <span className="ed-modcard-name">{m.name}</span>
                <span className="ed-modcard-desc">{m.desc}</span>
                <span className="ed-modcard-foot">
                  <span>{moduleTotal(m.id)} questions</span>
                  <span style={{ color: ink }}>{p == null ? "Not started" : `${p}% · ${s.stats[m.id].a} done`}</span>
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── daily-mix result ────────────────────────────────────────────────────
function Result({ s, go, startMix }) {
  const Q = s.quiz;
  const R = Q.queue.map((_, k) => Q.results[k]);
  const cor = R.filter((r) => r === true).length;
  const att = R.filter((r) => r === true || r === false).length;
  const firstWrong = Q.queue.find((_, k) => R[k] === false);
  const xpDelta = s.xp - Q.xp0;
  const line =
    cor === Q.queue.length
      ? "A clean sweep. Come back tomorrow to keep the streak alive."
      : cor / Q.queue.length >= 0.6
        ? "Solid. Review the misses below, then drill the weakest type."
        : "Plenty to work on — practise the types you missed before the next mix.";
  const cells = [
    ["Accuracy", att ? `${Math.round((cor / att) * 100)}%` : "—"],
    ["XP earned", `${xpDelta >= 0 ? "+" : ""}${xpDelta}`],
    ["Time taken", mmss(Math.min(Q.dur, ((Q.end || Date.now()) - Q.start) / 1000))],
    ["Skipped", String(Q.queue.length - att)],
  ];
  return (
    <div className="ed-stack" style={{ gap: 26 }} data-testid="ed-result">
      <div>
        <div className="ed-kicker ed-kicker--acc">Daily mix · result</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginTop: 8, flexWrap: "wrap" }}>
          <span className="ed-res-big">{cor}</span>
          <span style={{ fontFamily: "var(--font-heading)", fontSize: 28 }}>of {Q.queue.length} correct</span>
        </div>
        <p style={{ margin: "12px 0 0", fontSize: 16, maxWidth: "60ch" }}>{line}</p>
      </div>
      <div className="ed-res-grid">
        {cells.map(([label, value]) => (
          <div key={label} className="ed-stack" style={{ padding: "14px 0", gap: 2 }}>
            <span className="ed-stat-label">{label}</span>
            <span className="ed-figure" style={{ fontSize: 28 }}>
              {value}
            </span>
          </div>
        ))}
      </div>
      <div className="ed-stack">
        {Q.queue.map((it, k) => (
          <div key={k} className="ed-res-row">
            <span className="ed-num" style={{ fontSize: 12, color: K.mut }}>
              {String(k + 1).padStart(2, "0")}
            </span>
            <span style={{ fontSize: 15 }}>{typeLabel(it.v, it.tab)}</span>
            <span
              className="ed-figure"
              style={{ fontSize: 16, color: R[k] === true ? K.ok : R[k] === false ? K.bad : K.mut }}
            >
              {R[k] === true ? "✓ Correct" : R[k] === false ? "✗ Wrong" : "— Skipped"}
            </span>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        <button type="button" className="ed-btn ed-btn--primary ed-btn--lg" onClick={startMix}>
          New mix
        </button>
        {firstWrong && (
          <button type="button" className="ed-btn ed-btn--lg" onClick={() => go(firstWrong.v, firstWrong.tab || undefined)}>
            Practise {typeLabel(firstWrong.v, firstWrong.tab).toLowerCase()}
          </button>
        )}
        <button type="button" className="ed-btn ed-btn--ghost ed-btn--lg" style={{ padding: "11px 16px" }} onClick={() => go("home")}>
          Back to overview
        </button>
      </div>
    </div>
  );
}

// ── question screen ─────────────────────────────────────────────────────
function Question({ s, cardRef, remaining, handlers }) {
  const { update, next, prev, finish, hint, check, reveal } = handlers;
  const c = curOf(s);
  const q = c.L[c.i] || {};
  const tkey = `${c.v}:${c.tab}`;
  const mod = MODS.find((m) => m.id === c.v);
  const tabs = c.quiz ? [] : TABS[c.v] || [];
  const last = c.quiz ? s.quiz.pos >= s.quiz.queue.length - 1 : c.i >= c.L.length - 1;
  const instr = INSTRUCTIONS[tkey];

  return (
    <div data-testid="ed-question">
      {c.quiz ? (
        <div className="ed-stack" style={{ gap: 14, marginBottom: 20 }}>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-end", gap: 12 }}>
            <div>
              <div className="ed-kicker ed-kicker--acc ed-num">
                Daily mix · question {s.quiz.pos + 1} of {s.quiz.queue.length}
              </div>
              <h2 style={{ fontWeight: 600, fontSize: 32, margin: "6px 0 0", lineHeight: 1.1 }}>{typeLabel(c.v, c.tab)}</h2>
              <p style={{ margin: "6px 0 0", fontSize: 15, color: "var(--color-neutral-800)" }}>{instr}</p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <span
                className="ed-figure"
                data-testid="ed-timer"
                role="timer"
                aria-label="Time left"
                style={{ fontSize: 38, lineHeight: 1, color: remaining < 60 ? K.bad : K.ink }}
              >
                {mmss(remaining)}
              </span>
              <button type="button" className="ed-btn ed-btn--sm" onClick={finish}>
                End
              </button>
            </div>
          </div>
          <div className="ed-dots" aria-hidden="true">
            {s.quiz.queue.map((_, k) => (
              <span
                key={k}
                className="ed-dot"
                style={{
                  background:
                    k === s.quiz.pos ? K.ink : s.quiz.results[k] === true ? K.ok : s.quiz.results[k] === false ? K.bad : K.pend,
                }}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="ed-stack" style={{ gap: 16, marginBottom: 20 }}>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-end", gap: 12 }}>
            <div style={{ minWidth: 0 }}>
              <div className="ed-kicker">{mod.tag}</div>
              <h2 style={{ fontWeight: 600, fontSize: 36, margin: "6px 0 0", lineHeight: 1.1 }}>{mod.name}</h2>
              <p style={{ margin: "6px 0 0", fontSize: 15, color: "var(--color-neutral-800)", maxWidth: "62ch" }}>{instr}</p>
            </div>
            <div className="ed-figure" style={{ fontSize: 20 }} data-testid="ed-counter">
              {c.i + 1} / {c.L.length}
            </div>
          </div>
          {tabs.length > 0 && (
            <div className="ed-tabs" role="group" aria-label={`${mod.name} type`}>
              {tabs.map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  className="ed-tab"
                  aria-pressed={c.tab === id}
                  onClick={() => update({ tabs: { ...s.tabs, [c.v]: id }, ...fresh() })}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
          <div className="ed-progress">
            <div style={{ width: `${((c.i + 1) / c.L.length) * 100}%` }} />
          </div>
        </div>
      )}

      <div ref={cardRef} className="ed-card" data-testid="ed-card">
        <QuestionBody c={c} q={q} s={s} handlers={handlers} />
      </div>

      <Feedback fb={s.fb} />

      <div className="ed-actions">
        <div style={{ display: "flex", gap: 10 }}>
          {!c.quiz && (
            <button
              type="button"
              className="ed-btn"
              style={{ opacity: c.i === 0 ? 0.35 : 1 }}
              aria-disabled={c.i === 0}
              onClick={prev}
            >
              ← Previous
            </button>
          )}
          {!s.hinted && !s.solved && (
            <button type="button" className="ed-btn ed-btn--ghost" style={{ padding: "10px 14px" }} onClick={hint}>
              Hint · −2 XP
            </button>
          )}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          {(c.v === "pj" || c.v === "sc") && s.counted && !s.solved && (
            <button type="button" className="ed-btn" onClick={reveal}>
              Reveal answer
            </button>
          )}
          {(c.v === "pj" || c.v === "sc" || c.v === "cloze" || (c.v === "pos" && c.tab === "tag")) && !s.solved && (
            <button type="button" className="ed-btn ed-btn--primary" style={{ padding: "10px 22px" }} onClick={check}>
              Check
            </button>
          )}
          <button
            type="button"
            className="ed-btn"
            style={{
              padding: "10px 20px",
              borderColor: s.solved ? K.ink : K.line,
              background: s.solved ? K.ink : "transparent",
              color: s.solved ? K.paper : K.ink,
            }}
            onClick={next}
          >
            {s.solved || s.counted ? (last ? (c.quiz ? "See result" : "Finish set") : "Next →") : "Skip"}
          </button>
        </div>
      </div>
    </div>
  );
}

const FB_PALETTE = {
  ok: [K.okT, K.ok, "✓"],
  bad: [K.badT, K.bad, "✗"],
  info: ["transparent", K.accInk, "i"],
  hint: [K.accT, K.accInk, "?"],
};

function Feedback({ fb }) {
  return (
    <div role="status" aria-live="polite">
      {fb && (
        <div className="ed-fb" data-testid="ed-feedback" style={{ background: FB_PALETTE[fb.type][0], borderColor: FB_PALETTE[fb.type][1] }}>
          <span className="ed-fb-icon" aria-hidden="true" style={{ borderColor: FB_PALETTE[fb.type][1], color: FB_PALETTE[fb.type][1] }}>
            {FB_PALETTE[fb.type][2]}
          </span>
          <div className="ed-stack" style={{ gap: 5, minWidth: 0 }}>
            <div className="ed-fb-title" style={{ color: FB_PALETTE[fb.type][1] }}>
              {fb.title}
            </div>
            {fb.body && <div style={{ fontSize: 15, lineHeight: 1.6, textWrap: "pretty" }}>{fb.body}</div>}
            {fb.rule && (
              <div style={{ fontSize: 14, lineHeight: 1.55, color: "var(--color-neutral-800)" }} data-testid="ed-rule">
                <span className="ed-stat-label" style={{ marginRight: 6, color: "inherit" }}>
                  Rule
                </span>
                <em>{fb.rule}</em>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── per-type bodies ─────────────────────────────────────────────────────
function optStyle(s, k, right) {
  const gone = s.elim.includes(k) && !s.solved;
  const base = { border: K.line, bg: K.paper, keyLine: K.line, keyInk: K.mut, opacity: gone ? 0.35 : 1, strike: gone ? "line-through" : "none", gone };
  if (!s.solved) return base;
  if (k === right) return { ...base, border: K.ok, bg: K.okT, keyLine: K.ok, keyInk: K.ok };
  if (k === s.pick) return { ...base, border: K.bad, bg: K.badT, keyLine: K.bad, keyInk: K.bad };
  return { ...base, opacity: 0.6 };
}

function QuestionBody({ c, q, s, handlers }) {
  switch (c.v) {
    case "pj":
      return <Parajumble q={q} s={s} handlers={handlers} />;
    case "err":
      return <ErrorSpot q={q} s={s} pickOne={handlers.pickOne} />;
    case "imp":
    case "voc":
      return (
        <>
          {c.v === "imp" ? (
            <div style={{ fontSize: "clamp(20px,3vw,25px)", lineHeight: 1.6, marginBottom: 24, textWrap: "pretty" }}>
              {q.pre}
              <span style={{ borderBottom: `2px solid ${K.acc}`, fontWeight: 600, padding: "0 2px" }}>{q.hl}</span>
              {q.post}
            </div>
          ) : (
            <div style={{ marginBottom: 24 }}>
              <div className="ed-kicker">{VOC_PROMPT[c.tab]}</div>
              <div
                style={{
                  fontFamily: "var(--font-heading)",
                  fontSize: "clamp(34px,5.6vw,54px)",
                  lineHeight: 1.08,
                  marginTop: 8,
                  textWrap: "balance",
                }}
                data-testid="ed-voc-word"
              >
                {q.w}
              </div>
            </div>
          )}
          <McqOptions c={c} q={q} s={s} pickOne={handlers.pickOne} grid />
        </>
      );
    case "rc": {
      const P = BANK.rcP[q.p];
      return (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(290px,1fr))", gap: 28 }}>
          <div className="ed-stack" style={{ gap: 8, maxHeight: 460, overflow: "auto", paddingRight: 6 }}>
            <span className="ed-kicker">Passage</span>
            <h3 style={{ fontWeight: 600, fontSize: 24 }}>{P.title}</h3>
            <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.7, textAlign: "justify", hyphens: "auto" }}>{P.text}</p>
          </div>
          <div className="ed-stack" style={{ gap: 14 }}>
            <span className="ed-kicker">Question {BANK.rc.filter((r) => r.p === q.p).indexOf(q) + 1}</span>
            <p style={{ margin: 0, fontSize: 19, lineHeight: 1.45 }}>{q.q}</p>
            <McqOptions c={c} q={q} s={s} pickOne={handlers.pickOne} />
          </div>
        </div>
      );
    }
    case "cloze":
      return <Cloze q={q} s={s} update={handlers.update} />;
    case "ce":
      return <CommonError q={q} s={s} pickOne={handlers.pickOne} />;
    case "pos":
      return c.tab === "mis" ? (
        <Misused q={q} s={s} pickOne={handlers.pickOne} />
      ) : (
        <PosTagger q={q} s={s} update={handlers.update} />
      );
    case "sc":
      return <Construct q={q} s={s} update={handlers.update} />;
    default:
      return null;
  }
}

function McqOptions({ c, q, s, pickOne, grid }) {
  const onPick = (k) => {
    const ok = k === q.a;
    const ans = q.o[q.a];
    let f;
    if (c.v === "voc") f = mkFb(ok ? "ok" : "bad", ok ? `Correct — ${ans}` : `The answer is ${ans}`, q.m, `e.g. ${q.x}`);
    else if (c.v === "imp")
      f = mkFb(ok ? "ok" : "bad", ok ? "Correct" : `The answer is “${ans}”`, q.pre + (q.a === 3 ? q.hl : ans) + q.post, q.rule);
    else f = mkFb(ok ? "ok" : "bad", ok ? "Correct" : `The answer is “${ans}”`, q.m);
    pickOne(k, ok, f);
  };
  const big = !!grid;
  return (
    <div
      style={
        grid
          ? { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 10 }
          : { display: "flex", flexDirection: "column", gap: 8 }
      }
    >
      {q.o.map((t, k) => {
        const o = optStyle(s, k, q.a);
        return (
          <button
            key={k}
            type="button"
            className="ed-opt"
            data-testid={`ed-opt-${k}`}
            aria-disabled={o.gone || s.solved}
            onClick={() => onPick(k)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: big ? "13px 15px" : "11px 14px",
              borderColor: o.border,
              background: o.bg,
              opacity: o.opacity,
              textDecoration: o.strike,
              fontSize: big ? 16 : 15.5,
              lineHeight: 1.4,
            }}
          >
            <span
              className="ed-key"
              style={{ width: big ? 26 : 24, height: big ? 26 : 24, fontSize: big ? 15 : 14, borderColor: o.keyLine, color: o.keyInk }}
            >
              {"ABCD"[k]}
            </span>
            <span>{t}</span>
          </button>
        );
      })}
    </div>
  );
}

function Parajumble({ q, s, handlers }) {
  const { update, pjMove, pjTap } = handlers;
  const order = s.pjOrder || q.given;
  return (
    <div className="ed-stack" style={{ gap: 16 }}>
      <div className="ed-kicker">{q.kind} · drag, or tap two rows to swap</div>
      <div className="ed-stack" style={{ gap: 8 }} data-testid="ed-pj-list">
        {order.map((o, pos) => {
          let border = K.line;
          let bg = K.paper;
          let badgeLine = K.acc;
          let badgeInk = K.accInk;
          if (s.pjChecked) {
            const okp = o === pos;
            border = okp ? K.ok : K.bad;
            bg = okp ? K.okT : K.badT;
            badgeLine = border;
            badgeInk = border;
          } else if (s.pjSel === pos || (s.dragOver === pos && s.dragFrom !== pos)) {
            border = K.acc;
            bg = K.accT;
          }
          const label = SEQ_LETTERS[q.given.indexOf(o)];
          return (
            <div
              key={o}
              role="button"
              tabIndex={0}
              draggable={!s.solved}
              aria-pressed={s.pjSel === pos}
              aria-label={`Part ${label}, position ${pos + 1}: ${q.parts[o]}`}
              data-testid={`ed-pj-row-${pos}`}
              className="ed-pj-row"
              style={{ borderColor: border, background: bg, opacity: s.dragFrom === pos ? 0.45 : 1 }}
              onDragStart={(e) => {
                try {
                  e.dataTransfer.effectAllowed = "move";
                  e.dataTransfer.setData("text/plain", String(pos));
                } catch (_) {
                  /* some browsers reject setData */
                }
                update({ dragFrom: pos });
              }}
              onDragOver={(e) => {
                e.preventDefault();
                if (s.dragOver !== pos) update({ dragOver: pos });
              }}
              onDrop={(e) => {
                e.preventDefault();
                pjMove(s.dragFrom, pos);
              }}
              onDragEnd={() => update({ dragFrom: null, dragOver: null })}
              onClick={() => pjTap(pos)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  pjTap(pos);
                }
              }}
            >
              <span className="ed-num" style={{ fontSize: 12, color: "var(--color-neutral-600)", width: 12 }}>
                {pos + 1}
              </span>
              <span className="ed-pj-badge" style={{ borderColor: badgeLine, color: badgeInk }}>
                {label}
              </span>
              <span style={{ flex: 1, minWidth: 0, fontSize: 18, lineHeight: 1.5, textWrap: "pretty" }}>{q.parts[o]}</span>
              <span aria-hidden="true" style={{ color: "var(--color-neutral-400)", fontSize: 18, letterSpacing: -2 }}>
                ⋮⋮
              </span>
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, fontSize: 13, color: K.mut }}>
        <span>Your sequence</span>
        <span
          data-testid="ed-pj-code"
          style={{ fontFamily: "var(--font-heading)", fontSize: 24, fontWeight: 600, color: K.ink, letterSpacing: "0.14em" }}
        >
          {pjCode(q, order)}
        </span>
      </div>
    </div>
  );
}

function ErrorSpot({ q, s, pickOne }) {
  return (
    <div className="ed-stack" style={{ gap: 20 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {[...q.parts, "No error"].map((t, k) => {
          let border = K.line;
          let bg = K.paper;
          let labelInk = K.mut;
          if (s.solved) {
            if (k === q.e) {
              border = K.ok;
              bg = K.okT;
              labelInk = K.ok;
            } else if (k === s.pick) {
              border = K.bad;
              bg = K.badT;
              labelInk = K.bad;
            }
          }
          const onPick = () => {
            const ok = k === q.e;
            pickOne(
              k,
              ok,
              mkFb(
                ok ? "ok" : "bad",
                ok ? "Correct" : "Not quite",
                q.e === 4
                  ? "The sentence is correct as written."
                  : `Error in part (${"ABCD"[q.e]}): “${q.parts[q.e]}” should be “${q.fix}”.`,
                q.rule,
              ),
            );
          };
          return (
            <button
              key={k}
              type="button"
              className="ed-opt"
              data-testid={`ed-err-${k}`}
              onClick={onPick}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                gap: 4,
                padding: "12px 14px",
                borderColor: border,
                background: bg,
              }}
            >
              <span style={{ fontSize: 11, letterSpacing: "0.1em", color: labelInk }}>({"ABCDE"[k]})</span>
              <span style={{ fontSize: 20, lineHeight: 1.35 }}>{t}</span>
            </button>
          );
        })}
      </div>
      {s.solved && q.e !== 4 && (
        <div className="ed-stack" style={{ gap: 4, paddingTop: 16, borderTop: `1px solid ${K.line}` }}>
          <span className="ed-kicker ed-kicker--ok">Corrected</span>
          <span style={{ fontSize: 19, fontStyle: "italic" }}>{q.full}</span>
        </div>
      )}
    </div>
  );
}

function Cloze({ q, s, update }) {
  const B = blanks(q);
  const active = s.clozeActive != null ? s.clozeActive : B.find((k) => s.clozeSel[k] == null) ?? B[0];
  const P = q.parts[active];
  return (
    <div className="ed-stack" style={{ gap: 22 }}>
      <h3 style={{ fontWeight: 600, fontSize: 24 }}>{q.title}</h3>
      <p style={{ margin: 0, fontSize: "clamp(17px,2.4vw,20px)", lineHeight: 2, textAlign: "justify", hyphens: "auto" }}>
        {q.parts.map((p, k) => {
          if (typeof p === "string") return <span key={k}>{p}</span>;
          const sel = s.clozeSel[k];
          const okb = sel === p.a;
          let line = "var(--color-neutral-500)";
          let bg = "transparent";
          let ink = K.ink;
          if (s.solved) {
            line = okb ? K.ok : K.bad;
            bg = okb ? K.okT : K.badT;
            ink = okb ? K.ok : K.bad;
          } else if (k === active) {
            line = K.acc;
            bg = K.accT;
          }
          const n = B.indexOf(k) + 1;
          return (
            <span
              key={k}
              role="button"
              tabIndex={s.solved ? -1 : 0}
              aria-label={`Blank ${n}${sel != null ? `: ${p.o[sel]}` : ""}`}
              data-testid={`ed-blank-${n}`}
              onClick={() => {
                if (!s.solved) update({ clozeActive: k });
              }}
              onKeyDown={(e) => {
                if ((e.key === "Enter" || e.key === " ") && !s.solved) {
                  e.preventDefault();
                  update({ clozeActive: k });
                }
              }}
              style={{
                borderBottom: `2px solid ${line}`,
                background: bg,
                padding: "1px 6px",
                cursor: s.solved ? "default" : "pointer",
                color: ink,
                borderRadius: 2,
              }}
            >
              <span style={{ fontSize: 12, verticalAlign: "super", marginRight: 3 }}>({n})</span>
              {sel != null ? p.o[sel] : "    "}
            </span>
          );
        })}
      </p>
      {!s.solved && (
        <div className="ed-stack" style={{ gap: 10, paddingTop: 16, borderTop: `1px solid ${K.line}` }}>
          <span className="ed-kicker ed-kicker--acc">Blank {B.indexOf(active) + 1} — choose a word</span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {P.o.map((t, oi) => {
              const on = s.clozeSel[active] === oi;
              const gone = (s.clozeElim[active] || []).includes(oi);
              return (
                <button
                  key={oi}
                  type="button"
                  className="ed-opt"
                  aria-pressed={on}
                  aria-disabled={gone}
                  onClick={() => {
                    if (s.solved || gone) return;
                    const sel = { ...s.clozeSel, [active]: oi };
                    const nxt = B.find((k) => sel[k] == null);
                    update({ clozeSel: sel, clozeActive: nxt != null ? nxt : active, fb: null });
                  }}
                  style={{
                    padding: "9px 16px",
                    borderColor: on ? K.acc : K.line,
                    background: on ? K.accT : K.paper,
                    opacity: gone ? 0.35 : 1,
                    textDecoration: gone ? "line-through" : "none",
                    fontSize: 16,
                  }}
                >
                  {t}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function CommonError({ q, s, pickOne }) {
  const right = q.fix ? 1 : 0;
  return (
    <div className="ed-stack" style={{ gap: 22 }}>
      <span
        style={{
          alignSelf: "flex-start",
          padding: "3px 10px",
          borderRadius: "var(--radius-sm)",
          border: `1px solid ${K.line}`,
        }}
        className="ed-kicker"
      >
        {s.solved || s.hinted ? q.tag : "Usage"}
      </span>
      <div style={{ fontFamily: "var(--font-heading)", fontSize: "clamp(28px,4.4vw,40px)", lineHeight: 1.2, textWrap: "pretty" }}>
        “{q.s}”
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        {["Correct as written", "Contains an error"].map((t, k) => {
          const o = optStyle(s, k, right);
          return (
            <button
              key={k}
              type="button"
              className="ed-opt"
              data-testid={`ed-ce-${k}`}
              onClick={() => {
                const ok = k === right;
                pickOne(
                  k,
                  ok,
                  mkFb(ok ? "ok" : "bad", ok ? "Right call" : "Not quite", q.fix ? "This is a common error." : "This sentence is correct.", q.rule),
                );
              }}
              style={{
                flex: "1 1 200px",
                padding: "14px 18px",
                borderColor: o.border,
                background: o.bg,
                textAlign: "center",
                fontFamily: "var(--font-heading)",
                fontSize: 19,
                fontWeight: 600,
              }}
            >
              {t}
            </button>
          );
        })}
      </div>
      {s.solved && q.fix && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))", gap: 10 }}>
          <div className="ed-stack" style={{ padding: "14px 16px", borderRadius: "var(--radius-md)", border: `1px solid ${K.bad}`, gap: 4 }}>
            <span className="ed-kicker ed-kicker--bad">✗ Avoid</span>
            <span style={{ fontSize: 17, textDecoration: "line-through", textDecorationColor: K.bad }}>{q.s}</span>
          </div>
          <div className="ed-stack" style={{ padding: "14px 16px", borderRadius: "var(--radius-md)", border: `1px solid ${K.ok}`, gap: 4 }}>
            <span className="ed-kicker ed-kicker--ok">✓ Use</span>
            <span style={{ fontSize: 17 }}>{q.fix}</span>
          </div>
        </div>
      )}
    </div>
  );
}

const hue = (h, l, ch) => `oklch(${l} ${ch} ${h})`;

function PosTagger({ q, s, update }) {
  return (
    <div className="ed-stack" style={{ gap: 22 }}>
      <div className="ed-stack" style={{ gap: 8 }}>
        <span className="ed-kicker">1 · Pick a tag</span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }} role="group" aria-label="Part-of-speech tags">
          {Object.entries(POS_TAGS).map(([code, T]) => {
            const on = s.posTool === code;
            return (
              <button
                key={code}
                type="button"
                aria-pressed={on}
                data-testid={`ed-tool-${code}`}
                onClick={() => update({ posTool: code })}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 7,
                  padding: "6px 12px",
                  borderRadius: 999,
                  border: `1px solid ${on ? hue(T.h, 0.55, 0.12) : K.line}`,
                  background: on ? hue(T.h, 0.95, 0.035) : "transparent",
                  cursor: "pointer",
                  color: K.ink,
                  fontSize: 13.5,
                }}
              >
                <span style={{ width: 9, height: 9, borderRadius: "50%", border: `2px solid ${hue(T.h, 0.58, 0.13)}` }} />
                <span>{T.name}</span>
              </button>
            );
          })}
        </div>
      </div>
      <div className="ed-stack" style={{ gap: 8 }}>
        <span className="ed-kicker">2 · Tap each word</span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {q.w.map(([t, tag], k) => {
            const as = s.posTags[k];
            const T = as && POS_TAGS[as];
            const bg = T ? hue(T.h, 0.95, 0.035) : K.paper;
            let border = T ? hue(T.h, 0.6, 0.11) : K.line;
            let lbl = T ? T.short : "·";
            let ink = T ? hue(T.h, 0.42, 0.12) : K.mut;
            if (s.posChecked) {
              if (as === tag) border = K.ok;
              else {
                border = K.bad;
                ink = K.bad;
                lbl = `${T ? T.short : "—"} → ${POS_TAGS[tag].short}`;
              }
            }
            return (
              <button
                key={k}
                type="button"
                data-testid={`ed-word-${k}`}
                onClick={() => {
                  if (s.posChecked) return;
                  const tags = { ...s.posTags };
                  if (tags[k] === s.posTool) delete tags[k];
                  else tags[k] = s.posTool;
                  update({ posTags: tags, fb: null });
                }}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 2,
                  padding: "8px 12px",
                  borderRadius: "var(--radius-md)",
                  border: `1px solid ${border}`,
                  background: bg,
                  cursor: "pointer",
                  color: K.ink,
                  minWidth: 58,
                }}
              >
                <span style={{ fontSize: 21, lineHeight: 1.3 }}>{t}</span>
                <span style={{ fontSize: 10.5, letterSpacing: "0.08em", fontWeight: 600, color: ink }}>{lbl}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Misused({ q, s, pickOne }) {
  return (
    <div className="ed-stack" style={{ gap: 20 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
        {q.w.map((t, k) => {
          let border = "transparent";
          let bg = "transparent";
          if (s.solved) {
            if (k === q.e) {
              border = K.ok;
              bg = K.okT;
            } else if (k === s.pick) {
              border = K.bad;
              bg = K.badT;
            }
          }
          return (
            <button
              key={k}
              type="button"
              className="ed-opt"
              data-testid={`ed-mis-${k}`}
              onClick={() => {
                const ok = k === q.e;
                pickOne(
                  k,
                  ok,
                  mkFb(ok ? "ok" : "bad", ok ? "Correct" : "Not quite", `“${q.w[q.e].replace(/[.,]/g, "")}” should be “${q.fix}”.`, q.rule),
                );
              }}
              style={{
                padding: "2px 8px",
                borderColor: border,
                background: bg,
                fontFamily: "var(--font-heading)",
                fontSize: "clamp(28px,4.4vw,40px)",
                lineHeight: 1.25,
              }}
            >
              {t}
            </button>
          );
        })}
      </div>
      {s.solved && (
        <div className="ed-stack" style={{ gap: 4, paddingTop: 16, borderTop: `1px solid ${K.line}` }}>
          <span className="ed-kicker ed-kicker--ok">Corrected · {q.pos}</span>
          <span style={{ fontSize: 19, fontStyle: "italic" }}>{q.full}</span>
        </div>
      )}
    </div>
  );
}

function Construct({ q, s, update }) {
  const okBuilt = s.scChecked && s.solved;
  return (
    <div className="ed-stack" style={{ gap: 20 }}>
      <div className="ed-stack" style={{ gap: 6 }}>
        <span className="ed-kicker">{q.task}</span>
        {q.source && (
          <span style={{ fontFamily: "var(--font-heading)", fontSize: "clamp(26px,4vw,34px)", lineHeight: 1.25 }}>{q.source}</span>
        )}
      </div>
      <div
        data-testid="ed-sc-strip"
        style={{
          minHeight: 70,
          padding: 12,
          borderRadius: "var(--radius-md)",
          border: `1px dashed ${s.scChecked ? (okBuilt ? K.ok : K.bad) : "var(--color-neutral-400)"}`,
          background: s.scChecked ? (okBuilt ? K.okT : K.badT) : "transparent",
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
          alignItems: "center",
        }}
      >
        {s.scPicked.length === 0 && (
          <span style={{ color: "var(--color-neutral-600)", fontSize: 14, fontStyle: "italic", padding: "0 6px" }}>
            Tap words below to build the sentence
          </span>
        )}
        {s.scPicked.map((ti, k) => (
          <button
            key={`${ti}-${k}`}
            type="button"
            onClick={() => {
              if (s.solved) return;
              const p = s.scPicked.slice();
              p.splice(k, 1);
              update({ scPicked: p, scChecked: false, fb: null });
            }}
            style={{
              padding: "7px 13px",
              borderRadius: "var(--radius-md)",
              border: `1px solid ${K.acc}`,
              background: "transparent",
              color: K.ink,
              cursor: "pointer",
              fontSize: 18,
            }}
          >
            {q.t[ti]}
          </button>
        ))}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {q.t.map((w, ti) => {
          const used = s.scPicked.includes(ti);
          return (
            <button
              key={ti}
              type="button"
              data-testid={`ed-bank-${ti}`}
              aria-disabled={used}
              onClick={() => {
                if (s.solved || used) return;
                update({ scPicked: [...s.scPicked, ti], scChecked: false, fb: null });
              }}
              style={{
                padding: "7px 13px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--color-neutral-300)",
                background: K.paper,
                color: K.ink,
                cursor: used ? "default" : "pointer",
                opacity: used ? 0.2 : 1,
                fontSize: 18,
                boxShadow: "var(--shadow-sm)",
              }}
            >
              {w}
            </button>
          );
        })}
      </div>
    </div>
  );
}
