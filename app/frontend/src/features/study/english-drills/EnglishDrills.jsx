/**
 * EnglishDrills — verbal-ability drills over the verified PYQ corpus.
 *
 * Every question comes from the corpus through the EXISTING topic-practice path;
 * this page adds no endpoint and ships no questions of its own:
 *
 *   scope    GET  /api/study/topics?subject_id=<English>  — the caller's current
 *            exam's LOCKED coverage (load_scoped_coverage), with verified PYQ
 *            count + account mastery per topic. Modules are narrowed to it.
 *   launch   POST /api/study/subjects/<English>/practice/start {topic_pyq} —
 *            server resolves the exam, re-checks the topic is locked for this
 *            subject, and assembles a verified, actively-projected PYQ attempt.
 *   answer   POST /api/study/mocks/attempts/:id/answer   (useAnswerSync: retry
 *            with backoff, idempotent client_seq — the offline path)
 *   check    POST /api/study/mocks/attempts/:id/submit   (server grades; mastery
 *            write-back — the account is the source of truth for progress)
 *   verdict  GET  /api/study/mocks/attempts/:id/review   (correct option,
 *            explanation, reviewed parajumble order)
 *
 * The attempt API never reveals an answer before submit, so verdicts (buzzer,
 * shake, rule) play when the set is checked, question by question.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api } from "../../../lib/api";
import useApiAction from "../../../lib/hooks/useApiAction";
import useApiCollection from "../../../lib/hooks/useApiCollection";
import useAnswerSync, { SYNC } from "../../../pages/study/mocks/useAnswerSync";
import MathRenderer from "../../../pages/study/mocks/components/questions/shared/MathRenderer";
import PyqExplanationPanel from "../../../pages/study/mocks/components/questions/shared/PyqExplanationPanel";
import { formatOptionLabel } from "../../../pages/study/mocks/optionLabels";
import { ENGLISH_SUBJECT_ID, MODULES } from "./drillModules";
import {
  clearAttemptPointer,
  initialArrangement,
  loadAttemptPointer,
  matchArrangement,
  moveItem,
  saveAttemptPointer,
  scopeModules,
  swapItems,
  weakestModule,
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
  paper: "var(--color-bg)",
};

const TOPICS_URL = "/api/study/topics";
const ATTEMPTS = "/api/study/mocks/attempts";

function byDisplayOrder(a, b) {
  const ad = a?.display_order;
  const bd = b?.display_order;
  if (ad == null && bd == null) return 0;
  if (ad == null) return 1;
  if (bd == null) return -1;
  return ad - bd;
}

function orderedOptions(options) {
  return [...(options || [])].sort(byDisplayOrder);
}

function optionLabel(options, id) {
  const ordered = orderedOptions(options);
  const pos = ordered.findIndex((o) => o.id === id);
  return pos === -1 ? "" : formatOptionLabel(ordered[pos], pos);
}

function scrollTop() {
  try {
    window.scrollTo(0, 0);
  } catch (e) {
    /* jsdom */
  }
}

export default function EnglishDrills() {
  const topics = useApiCollection(TOPICS_URL, [], { params: { subject_id: ENGLISH_SUBJECT_ID } });
  const [view, setView] = useState("home");
  const [tabs, setTabs] = useState({});
  const [sound, setSound] = useState(true);

  const scoped = useMemo(() => scopeModules(topics.items), [topics.items]);
  const byModule = useMemo(() => Object.fromEntries(scoped.map((s) => [s.module.id, s])), [scoped]);

  const lockedCount = scoped.reduce((n, s) => n + s.locked.length, 0);
  const verifiedTotal = scoped.reduce((n, s) => n + s.verified, 0);
  const masteries = scoped.flatMap((s) => s.locked.map((t) => t.mastery)).filter((x) => x != null);
  const masteryAvg = masteries.length ? Math.round(masteries.reduce((a, b) => a + b, 0) / masteries.length) : null;

  const go = (id) => {
    setView(id);
    scrollTop();
  };

  return (
    <div className="ed-root" data-testid="english-drills">
      <header className="ed-header">
        <button type="button" className="ed-brand" onClick={() => go("home")}>
          <span className="ed-brand-name">Verbal drills</span>
          <span className="ed-brand-tag">English</span>
        </button>
        <div className="ed-stats">
          <Stat label="Verified PYQs" value={topics.status === "live" ? String(verifiedTotal) : "—"} testId="ed-verified" />
          <Stat label="Mastery" value={masteryAvg == null ? "—" : `${masteryAvg}%`} testId="ed-mastery" />
          <button type="button" className="ed-btn ed-btn--sm" aria-pressed={sound} onClick={() => setSound((x) => !x)}>
            {sound ? "♪ Sound on" : "♪ Sound off"}
          </button>
        </div>
      </header>

      <nav className="ed-strip" aria-label="English modules">
        {[{ id: "home", name: "Overview" }, ...MODULES].map((m) => (
          <button
            key={m.id}
            type="button"
            className="ed-strip-item"
            aria-current={view === m.id ? "page" : undefined}
            onClick={() => go(m.id)}
          >
            {m.name}
          </button>
        ))}
      </nav>

      <main className="ed-main">
        <div className="ed-col">
          {topics.status === "loading" && <Note testId="ed-loading">Loading your exam’s English topics…</Note>}
          {topics.status === "error" && (
            <Note testId="ed-error" tone="bad">
              Couldn’t load your exam’s English topics.{" "}
              <button type="button" className="ed-btn ed-btn--sm" onClick={topics.refresh}>
                Retry
              </button>
            </Note>
          )}
          {topics.status === "empty" && (
            <Note testId="ed-no-scope">
              Your current exam has no locked English Language coverage, so there is nothing to drill here. Change your
              target exam in your profile, or check back when English is added to its syllabus.
            </Note>
          )}
          {topics.status === "live" && view === "home" && (
            <Home scoped={scoped} lockedCount={lockedCount} go={go} />
          )}
          {topics.status === "live" && view !== "home" && (
            <ModuleView
              key={view}
              scope={byModule[view]}
              tab={tabs[view]}
              setTab={(id) => setTabs((t) => ({ ...t, [view]: id }))}
              sound={sound}
              onChecked={topics.refresh}
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

function Note({ children, tone, testId }) {
  return (
    <div
      className="ed-note"
      data-testid={testId}
      role={tone === "bad" ? "alert" : "status"}
      style={{ borderColor: tone === "bad" ? K.bad : K.line }}
    >
      {children}
    </div>
  );
}

// ── overview ────────────────────────────────────────────────────────────
function Home({ scoped, lockedCount, go }) {
  const weak = weakestModule(scoped);
  return (
    <div className="ed-stack" style={{ gap: 32 }}>
      <div>
        <div className="ed-kicker">Verbal ability · past-paper questions from your exam</div>
        <h1 className="ed-hero-title">The English section, drilled daily.</h1>
        <p className="ed-lede">
          Every question here is a verified past-paper question from your current exam. Answer a set, check it, and
          each miss buzzes and shows the correct answer with its explanation. Progress is saved to your account.
        </p>
        <p className="ed-kicker ed-num" style={{ marginTop: 12 }} data-testid="ed-scope-line">
          {lockedCount} English topics are locked for your exam
        </p>
      </div>

      {weak && (
        <div className="ed-weak" data-testid="ed-weakest">
          <span>
            <span className="ed-kicker ed-kicker--bad" style={{ marginRight: 10 }}>
              Weakest area
            </span>
            <em>{weak.module.name}</em> — {weak.mastery}% mastery
          </span>
          <button type="button" className="ed-btn" onClick={() => go(weak.module.id)}>
            Practise it
          </button>
        </div>
      )}

      <div className="ed-stack" style={{ gap: 16 }}>
        <h3 style={{ fontWeight: 600, fontSize: 26 }}>Practise by module</h3>
        <div className="ed-modgrid">
          {scoped.map((s, k) => {
            const m = s.module;
            const foot = !s.locked.length
              ? "Not in your exam"
              : !s.practiceable.length
                ? "No verified questions yet"
                : s.mastery == null
                  ? "Not started"
                  : `${s.mastery}% mastery`;
            const ink = !s.practiceable.length ? K.mut : s.mastery == null ? K.mut : s.mastery >= 75 ? K.ok : s.mastery >= 45 ? K.ink : K.bad;
            return (
              <button key={m.id} type="button" className="ed-modcard" data-testid={`ed-module-${m.id}`} onClick={() => go(m.id)}>
                <span className="ed-kicker ed-num" style={{ fontSize: 10.5 }}>
                  {String(k + 1).padStart(2, "0")} · {m.tag}
                </span>
                <span className="ed-modcard-name">{m.name}</span>
                <span className="ed-modcard-desc">{m.desc}</span>
                <span className="ed-modcard-foot">
                  <span>{s.verified} questions</span>
                  <span style={{ color: ink }}>{foot}</span>
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── one module ──────────────────────────────────────────────────────────
function ModuleView({ scope, tab, setTab, sound, onChecked }) {
  const m = scope.module;
  const names = (list) => list.map((t) => t.label).join(", ");
  const active = scope.locked.find((t) => t.id === tab) || scope.practiceable[0] || scope.locked[0] || null;

  return (
    <div data-testid={`ed-view-${m.id}`}>
      <div className="ed-stack" style={{ gap: 16, marginBottom: 20 }}>
        <div>
          <div className="ed-kicker">{m.tag}</div>
          <h2 style={{ fontWeight: 600, fontSize: 36, margin: "6px 0 0", lineHeight: 1.1 }}>{m.name}</h2>
          <p style={{ margin: "6px 0 0", fontSize: 15, color: "var(--color-neutral-800)", maxWidth: "62ch" }}>{m.desc}</p>
        </div>
        {scope.locked.length > 1 && (
          <div className="ed-tabs" role="group" aria-label={`${m.name} topics`}>
            {scope.locked.map((t) => (
              <button
                key={t.id}
                type="button"
                className="ed-tab"
                aria-pressed={active?.id === t.id}
                data-testid={`ed-tab-${t.id}`}
                onClick={() => setTab(t.id)}
              >
                {t.label} <span className="ed-num" style={{ fontWeight: 400, opacity: 0.7 }}>· {t.verified}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {!scope.locked.length && (
        <Note testId="ed-module-empty">
          None of this module’s topics are in your exam’s locked coverage: {names(m.topics)}. There is nothing to drill
          here for your exam.
        </Note>
      )}
      {active && active.verified === 0 && (
        <Note testId="ed-topic-empty">
          No verified past-paper questions yet for “{active.label}” in your exam.
        </Note>
      )}
      {active && active.verified > 0 && (
        <DrillSet key={active.id} topic={active} module={m} sound={sound} onChecked={onChecked} />
      )}
      {scope.locked.length > 0 && scope.notLocked.length > 0 && (
        <p className="ed-kicker" style={{ marginTop: 18, textTransform: "none", letterSpacing: 0 }} data-testid="ed-not-locked">
          Not in your exam’s coverage: {names(scope.notLocked)}.
        </p>
      )}
    </div>
  );
}

// ── one practice set (a topic-mode PYQ attempt) ─────────────────────────
function DrillSet({ topic, module, sound, onChecked }) {
  const [phase, setPhase] = useState("idle"); // idle | loading | answering | review | empty | error
  const [attempt, setAttempt] = useState(null);
  const [answers, setAnswers] = useState({});
  const [idx, setIdx] = useState(0);
  const [review, setReview] = useState(null);
  const [message, setMessage] = useState("");
  const { run, busy } = useApiAction();
  const attemptId = attempt?.attempt_id || null;

  const postAnswer = useCallback((payload) => api.post(`${ATTEMPTS}/${attemptId}/answer`, payload), [attemptId]);
  const sync = useAnswerSync({ postAnswer, debounceMs: 300 });

  const loadReview = useCallback(async (id) => {
    const r = await api.get(`${ATTEMPTS}/${id}/review`);
    setReview(r);
    setIdx(0);
    setPhase("review");
  }, []);

  const loadAttempt = useCallback(
    async (id) => {
      setPhase("loading");
      const a = await api.get(`${ATTEMPTS}/${id}`);
      if (a?.status && a.status !== "in_progress") {
        setAttempt(a);
        await loadReview(id);
        return;
      }
      setAttempt(a);
      const restored = {};
      (a?.questions || []).forEach((q) => {
        if (q.selected_option_id) restored[q.question_id] = q.selected_option_id;
      });
      setAnswers(restored);
      setIdx(0);
      setPhase("answering");
    },
    [loadReview],
  );

  // Resume: background read of the set this device last had open for the
  // topic. Not a mutation — the server copy decides what renders.
  useEffect(() => {
    const pointer = loadAttemptPointer(topic.id);
    if (!pointer) return;
    loadAttempt(pointer).catch(() => {
      clearAttemptPointer(topic.id);
      setPhase("idle");
    });
  }, [topic.id, loadAttempt]);

  const start = () => {
    setMessage("");
    run({
      action: async () => {
        try {
          return await api.post(`/api/study/subjects/${ENGLISH_SUBJECT_ID}/practice/start`, {
            mode: "topic_pyq",
            topic_id: topic.id,
          });
        } catch (e) {
          // 409 = no verified, projected set for this topic in this exam: an
          // honest empty state, not an error toast.
          if (e?.status === 409) return { empty: true };
          throw e;
        }
      },
      onSuccess: async (out) => {
        if (out?.empty) {
          setPhase("empty");
          return;
        }
        if (!out?.attempt_id) {
          setPhase("error");
          return;
        }
        saveAttemptPointer(topic.id, out.attempt_id);
        try {
          await loadAttempt(out.attempt_id);
        } catch (e) {
          setPhase("error");
        }
      },
      errorMessage: "Couldn’t start this set. Please try again.",
    });
  };

  const choose = (qid, optionId) => {
    setAnswers((a) => ({ ...a, [qid]: optionId }));
    sync.queueSave(qid, { question_id: qid, selected_option_id: optionId, is_marked_for_review: false, time_spent_sec: 0 });
  };

  const check = async () => {
    setMessage("");
    const { failedIds, answeredCount } = await sync.flushAll();
    if (failedIds.length) {
      setMessage(`${failedIds.length} answer(s) didn’t save. Retry before checking.`);
      return;
    }
    await run({
      action: () => api.post(`${ATTEMPTS}/${attemptId}/submit`, { claimed_answered_count: answeredCount || null }),
      onSuccess: async () => {
        await loadReview(attemptId);
        if (onChecked) onChecked();
      },
      errorMessage: "Couldn’t check this set. Your answers are saved — try again.",
    });
  };

  const newSet = () => {
    clearAttemptPointer(topic.id);
    setAttempt(null);
    setReview(null);
    setAnswers({});
    setPhase("idle");
  };

  if (phase === "idle" || phase === "empty" || phase === "error") {
    return (
      <div className="ed-card" data-testid="ed-set-start">
        <div className="ed-kicker ed-kicker--acc">{topic.label}</div>
        <h3 style={{ fontWeight: 600, fontSize: 28, margin: "6px 0 8px" }}>
          {topic.verified} verified past-paper question{topic.verified === 1 ? "" : "s"}
        </h3>
        <p style={{ margin: "0 0 16px", fontSize: 15 }}>
          Newest papers first. Answer as many as you like, then check the set to hear each verdict and read why.
        </p>
        {phase === "empty" && (
          <Note testId="ed-set-empty">
            No verified practice set is ready for “{topic.label}” in your exam yet — its questions are not projected
            for practice.
          </Note>
        )}
        {phase === "error" && <Note tone="bad" testId="ed-set-error">Couldn’t open this set. Please try again.</Note>}
        <button type="button" className="ed-btn ed-btn--primary ed-btn--lg" onClick={start} disabled={busy} style={{ marginTop: 12 }}>
          {busy ? "Starting…" : "Start set →"}
        </button>
      </div>
    );
  }

  if (phase === "loading") return <Note testId="ed-set-loading">Loading set…</Note>;

  if (phase === "review") {
    return <ReviewWalk review={review} idx={idx} setIdx={setIdx} sound={sound} onNewSet={newSet} topic={topic} />;
  }

  const qs = attempt?.questions || [];
  const q = qs[idx];
  const answered = Object.keys(answers).length;
  const pending = sync.pendingCount;
  return (
    <div data-testid="ed-answering">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
        <span className="ed-kicker ed-num" data-testid="ed-counter">
          {topic.label} · question {idx + 1} of {qs.length}
        </span>
        <span className="ed-kicker ed-num" data-testid="ed-sync">
          {answered} answered
          {pending ? " · saving…" : ""}
          {sync.failedCount ? ` · ${sync.failedCount} not saved` : ""}
        </span>
      </div>
      <div className="ed-progress" style={{ marginBottom: 20 }}>
        <div style={{ width: `${((idx + 1) / Math.max(1, qs.length)) * 100}%` }} />
      </div>
      {q && (
        <div className="ed-card" data-testid="ed-card">
          <QuestionBody q={q} selected={answers[q.question_id]} onChoose={(opt) => choose(q.question_id, opt)} sequenceModule={!!module.sequence} />
          {sync.syncStates[q.question_id]?.state === SYNC.FAILED && (
            <Note tone="bad" testId="ed-save-failed">
              This answer didn’t save.{" "}
              <button type="button" className="ed-btn ed-btn--sm" onClick={() => sync.retryNow(q.question_id)}>
                Retry
              </button>
            </Note>
          )}
        </div>
      )}
      {message && <Note tone="bad" testId="ed-message">{message}</Note>}
      <div className="ed-actions">
        <div style={{ display: "flex", gap: 10 }}>
          <button type="button" className="ed-btn" disabled={idx === 0} onClick={() => setIdx((i) => Math.max(0, i - 1))}>
            ← Previous
          </button>
          <button type="button" className="ed-btn" disabled={idx >= qs.length - 1} onClick={() => setIdx((i) => Math.min(qs.length - 1, i + 1))}>
            Next →
          </button>
        </div>
        <button type="button" className="ed-btn ed-btn--primary" style={{ padding: "10px 22px" }} onClick={check} disabled={busy}>
          {busy ? "Checking…" : `Check set (${answered}/${qs.length})`}
        </button>
      </div>
    </div>
  );
}

function Passage({ stimuli }) {
  const text = (stimuli || [])
    .slice()
    .sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0))
    .map((s) => s.content_text)
    .filter(Boolean);
  if (!text.length) return null;
  return (
    <div className="ed-stack" style={{ gap: 8, maxHeight: 420, overflow: "auto", paddingRight: 6, marginBottom: 20 }} data-testid="ed-passage">
      <span className="ed-kicker">Passage</span>
      {text.map((t, i) => (
        <MathRenderer key={i} text={t} className="ed-passage-text" />
      ))}
    </div>
  );
}

function QuestionBody({ q, selected, onChoose, sequenceModule }) {
  return (
    <>
      <Passage stimuli={q.stimuli} />
      {q.sequence ? (
        <SequenceAnswer q={q} selected={selected} onChoose={onChoose} />
      ) : (
        <>
          <div className="ed-stem" data-testid="ed-stem">
            <MathRenderer text={q.question_text} />
          </div>
          {sequenceModule && (
            <p className="ed-kicker" style={{ textTransform: "none", letterSpacing: 0, margin: "0 0 12px" }} data-testid="ed-mcq-fallback">
              This question has no reviewed order yet, so it is answered as a choice.
            </p>
          )}
          <Options options={q.options} selected={selected} onChoose={onChoose} />
        </>
      )}
    </>
  );
}

function Options({ options, selected, onChoose, verdict }) {
  const ordered = orderedOptions(options);
  return (
    <div className="ed-stack" style={{ gap: 8 }}>
      {ordered.map((o, pos) => {
        let border = K.line;
        let bg = K.paper;
        if (verdict) {
          if (o.id === verdict.correct) {
            border = K.ok;
            bg = K.okT;
          } else if (o.id === selected) {
            border = K.bad;
            bg = K.badT;
          }
        } else if (o.id === selected) {
          border = K.acc;
          bg = K.accT;
        }
        return (
          <button
            key={o.id}
            type="button"
            className="ed-opt"
            data-testid={`ed-opt-${pos}`}
            aria-pressed={o.id === selected}
            disabled={!!verdict}
            onClick={() => onChoose && onChoose(o.id)}
            style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 15px", borderColor: border, background: bg, fontSize: 16, lineHeight: 1.4 }}
          >
            <span className="ed-key" style={{ width: 30, height: 26, fontSize: 14, borderColor: border }}>
              {formatOptionLabel(o, pos)}
            </span>
            <MathRenderer text={o.option_text || ""} inline />
          </button>
        );
      })}
    </div>
  );
}

/**
 * Drag-to-reorder over N segments (N from the reviewed record — 4, 5, 6…).
 * "Use this order" submits the OPTION whose reviewed order equals the
 * arrangement; the server grades that option. An arrangement no option names
 * is simply not one of the choices the paper offered.
 */
function SequenceAnswer({ q, selected, onChoose }) {
  const seq = q.sequence;
  const textByLabel = useMemo(() => Object.fromEntries(seq.segments.map((s) => [s.label, s.text])), [seq]);
  const [order, setOrder] = useState(() => (selected && seq.option_orders[selected]) || initialArrangement(seq));
  const [sel, setSel] = useState(null);
  const [drag, setDrag] = useState({ from: null, over: null });
  const [note, setNote] = useState("");

  const commit = () => {
    const opt = matchArrangement(seq.option_orders, order);
    if (!opt) {
      setNote("That order isn’t one of the answer choices on the paper. Rearrange and try again.");
      return;
    }
    setNote("");
    onChoose(opt);
  };
  const touch = (next) => {
    setOrder(next);
    setNote("");
  };
  const chosenLabel = selected ? optionLabel(q.options, selected) : "";
  const chosenIsThis = selected && (seq.option_orders[selected] || []).join() === order.join();

  return (
    <div className="ed-stack" style={{ gap: 16 }}>
      {seq.lead && <MathRenderer text={seq.lead} />}
      <div className="ed-kicker">{seq.segments.length} parts · drag, or tap two rows to swap</div>
      <div className="ed-stack" style={{ gap: 8 }} data-testid="ed-pj-list">
        {order.map((label, pos) => {
          const hot = sel === pos || (drag.over === pos && drag.from !== pos);
          return (
            <div
              key={label}
              role="button"
              tabIndex={0}
              draggable
              aria-pressed={sel === pos}
              aria-label={`Part ${label}, position ${pos + 1}: ${textByLabel[label]}`}
              data-testid={`ed-pj-row-${pos}`}
              className="ed-pj-row"
              style={{ borderColor: hot ? K.acc : K.line, background: hot ? K.accT : K.paper, opacity: drag.from === pos ? 0.45 : 1 }}
              onDragStart={(e) => {
                try {
                  e.dataTransfer.effectAllowed = "move";
                  e.dataTransfer.setData("text/plain", String(pos));
                } catch (_) {
                  /* some browsers reject setData */
                }
                setDrag({ from: pos, over: null });
              }}
              onDragOver={(e) => {
                e.preventDefault();
                if (drag.over !== pos) setDrag((d) => ({ ...d, over: pos }));
              }}
              onDrop={(e) => {
                e.preventDefault();
                touch(moveItem(order, drag.from, pos));
                setDrag({ from: null, over: null });
              }}
              onDragEnd={() => setDrag({ from: null, over: null })}
              onClick={() => {
                if (sel == null) setSel(pos);
                else if (sel === pos) setSel(null);
                else {
                  touch(swapItems(order, sel, pos));
                  setSel(null);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  e.currentTarget.click();
                }
              }}
            >
              <span className="ed-num" style={{ fontSize: 12, color: "var(--color-neutral-600)", width: 14 }}>
                {pos + 1}
              </span>
              <span className="ed-pj-badge">{label}</span>
              <span style={{ flex: 1, minWidth: 0, fontSize: 18, lineHeight: 1.5, textWrap: "pretty" }}>{textByLabel[label]}</span>
              <span aria-hidden="true" style={{ color: "var(--color-neutral-400)", fontSize: 18, letterSpacing: -2 }}>
                ⋮⋮
              </span>
            </div>
          );
        })}
      </div>
      {seq.tail && <MathRenderer text={seq.tail} />}
      <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
        <span style={{ fontSize: 13, color: K.mut }}>Your sequence</span>
        <span data-testid="ed-pj-code" style={{ fontFamily: "var(--font-heading)", fontSize: 24, fontWeight: 600, letterSpacing: "0.14em" }}>
          {order.join(" ")}
        </span>
        <button type="button" className="ed-btn ed-btn--primary" onClick={commit}>
          Use this order
        </button>
        {chosenIsThis && (
          <span className="ed-kicker ed-kicker--acc" data-testid="ed-pj-chosen">
            Answer saved · option {chosenLabel}
          </span>
        )}
      </div>
      {note && (
        <Note testId="ed-pj-note">{note}</Note>
      )}
    </div>
  );
}

// ── verdicts after the set is checked ───────────────────────────────────
function ReviewWalk({ review, idx, setIdx, sound, onNewSet, topic }) {
  const items = review?.questions || [];
  const cardRef = useRef(null);
  const played = useRef(new Set());
  const it = items[idx];
  const snap = it?.question_snapshot || {};
  const verdict = it ? (it.selected_option_id == null ? "skipped" : it.is_correct ? "ok" : "bad") : null;

  useEffect(() => {
    if (!it || played.current.has(it.question_id)) return;
    played.current.add(it.question_id);
    if (verdict === "skipped") return;
    if (sound) playVerdict(verdict === "ok");
    if (verdict === "bad") shake(cardRef.current);
  }, [it, verdict, sound]);

  const correct = items.filter((x) => x.selected_option_id != null && x.is_correct).length;
  const wrong = items.filter((x) => x.selected_option_id != null && !x.is_correct).length;
  const skipped = items.length - correct - wrong;
  const seq = snap.sequence;
  const textByLabel = seq ? Object.fromEntries((seq.segments || []).map((s) => [s.label, s.text])) : {};
  const correctLabel = optionLabel(snap.options, snap.correct_option_id);

  return (
    <div className="ed-stack" style={{ gap: 20 }} data-testid="ed-review">
      <div>
        <div className="ed-kicker ed-kicker--acc">{topic.label} · checked</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginTop: 8, flexWrap: "wrap" }}>
          <span className="ed-res-big" data-testid="ed-score">
            {correct}
          </span>
          <span style={{ fontFamily: "var(--font-heading)", fontSize: 28 }}>of {items.length} correct</span>
        </div>
        <p className="ed-kicker ed-num" style={{ marginTop: 8 }}>
          {wrong} wrong · {skipped} not answered · saved to your account
        </p>
      </div>
      <div className="ed-dots" aria-hidden="true">
        {items.map((x, k) => (
          <span
            key={x.question_id}
            className="ed-dot"
            style={{ background: k === idx ? K.ink : x.selected_option_id == null ? "var(--color-neutral-300)" : x.is_correct ? K.ok : K.bad }}
          />
        ))}
      </div>

      {it && (
        <div ref={cardRef} className="ed-card" data-testid="ed-card">
          <span className="ed-kicker ed-num">
            Question {idx + 1} of {items.length}
          </span>
          <Passage stimuli={snap.stimuli} />
          {seq ? (
            <div className="ed-stack" style={{ gap: 8, margin: "8px 0 16px" }} data-testid="ed-review-order">
              {seq.lead && <MathRenderer text={seq.lead} />}
              <span className="ed-kicker ed-kicker--ok">Correct order · {(seq.correct_order || []).join(" ")}</span>
              {(seq.correct_order || []).map((label, pos) => (
                <div key={label} className="ed-pj-row" style={{ cursor: "default", borderColor: K.ok, background: K.okT }}>
                  <span className="ed-num" style={{ fontSize: 12, width: 14 }}>{pos + 1}</span>
                  <span className="ed-pj-badge" style={{ borderColor: K.ok, color: K.ok }}>{label}</span>
                  <span style={{ flex: 1, fontSize: 17, lineHeight: 1.5 }}>{textByLabel[label]}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="ed-stem">
              <MathRenderer text={snap.question_text} />
            </div>
          )}
          <Options options={snap.options} selected={it.selected_option_id} verdict={{ correct: snap.correct_option_id }} />
        </div>
      )}

      {it && (
        <div role="status" aria-live="polite">
          <div
            className="ed-fb"
            data-testid="ed-feedback"
            style={{
              background: verdict === "ok" ? K.okT : verdict === "bad" ? K.badT : "transparent",
              borderColor: verdict === "ok" ? K.ok : verdict === "bad" ? K.bad : K.line,
            }}
          >
            <span className="ed-fb-icon" aria-hidden="true" style={{ borderColor: verdict === "ok" ? K.ok : verdict === "bad" ? K.bad : K.mut, color: verdict === "ok" ? K.ok : verdict === "bad" ? K.bad : K.mut }}>
              {verdict === "ok" ? "✓" : verdict === "bad" ? "✗" : "–"}
            </span>
            <div className="ed-stack" style={{ gap: 6, minWidth: 0 }}>
              <div className="ed-fb-title" style={{ color: verdict === "ok" ? K.ok : verdict === "bad" ? K.bad : K.mut }}>
                {verdict === "ok" ? "Correct" : verdict === "bad" ? `Not quite — the answer is ${correctLabel}` : `Not answered — the answer is ${correctLabel}`}
              </div>
              {(it.explanation || snap.explanation) && (
                <div style={{ fontSize: 15, lineHeight: 1.6 }} data-testid="ed-explanation">
                  <MathRenderer text={it.explanation || snap.explanation} />
                </div>
              )}
              <PyqExplanationPanel mode="review" explanation={it.pyq_explanation} options={snap.options} />
            </div>
          </div>
        </div>
      )}

      <div className="ed-actions">
        <div style={{ display: "flex", gap: 10 }}>
          <button type="button" className="ed-btn" disabled={idx === 0} onClick={() => setIdx((i) => Math.max(0, i - 1))}>
            ← Previous
          </button>
          <button type="button" className="ed-btn" disabled={idx >= items.length - 1} onClick={() => setIdx((i) => Math.min(items.length - 1, i + 1))}>
            Next →
          </button>
        </div>
        <button type="button" className="ed-btn ed-btn--primary" onClick={onNewSet}>
          New set
        </button>
      </div>
    </div>
  );
}

