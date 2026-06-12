import React, { useEffect, useReducer } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, getApiErrorMessage } from "../../../lib/api";
import { slugify, cycleBoundSlug } from "../../../lib/slugify";

// ── Constants ─────────────────────────────────────────────────────────────────

const CMS = "/api/admin/exam-intelligence-cms";
const REASON = "add cycle wizard create";

const CYCLE_STATUSES = ["expected", "open", "active", "closed", "completed", "cancelled"];
const DATE_FIELDS = [
  ["notification_date", "Notification date"],
  ["application_start", "Application start"],
  ["application_end", "Application end"],
  ["exam_start", "Exam start"],
  ["exam_end", "Exam end"],
];
const STEP_LABELS = ["Cycle", "Phases", "Review & Create"];

// ── Helpers ───────────────────────────────────────────────────────────────────

let _seq = 0;
function newId() { return `n${++_seq}`; }

function emptyNewPhase() {
  return {
    _id: newId(),
    phase_name: "",
    base_slug: "",
    phase_order: "",
    mode: "",
    duration_mins: "",
    total_questions: "",
    total_marks: "",
    createTemplate: false,
  };
}

function effectiveSlug(p) {
  return p.base_slug.trim() || slugify(p.phase_name.trim());
}

// ── State / Reducer ───────────────────────────────────────────────────────────

const initialState = {
  step: 0,
  // Loaded on mount
  existingCycles: [],
  existingPhases: [],
  loading: true,
  loadError: null,
  // Step 0 — cycle
  cycleDraft: {
    cycle_name: "", year: "", status: "",
    notification_date: "", application_start: "", application_end: "",
    exam_start: "", exam_end: "",
  },
  dupYearConfirmed: false,
  // Step 1 — phases
  selectedTemplateIds: [],  // ids of existing template phases chosen for cloning
  newPhases: [],
  // Step 2 — create state
  creating: false,
  createLog: [],
  createdIds: { cycle: null, phases: {} },
};

function reducer(state, action) {
  switch (action.type) {
    case "LOAD_OK": return {
      ...state, loading: false, loadError: null,
      existingCycles: action.cycles, existingPhases: action.phases,
    };
    case "LOAD_ERR": return { ...state, loading: false, loadError: action.error };
    case "GOTO_STEP": return { ...state, step: action.step };
    case "SET_CYCLE_DRAFT": return { ...state, cycleDraft: { ...state.cycleDraft, ...action.patch }, dupYearConfirmed: false };
    case "CONFIRM_DUP_YEAR": return { ...state, dupYearConfirmed: true };
    case "TOGGLE_TEMPLATE": return {
      ...state,
      selectedTemplateIds: state.selectedTemplateIds.includes(action.id)
        ? state.selectedTemplateIds.filter((x) => x !== action.id)
        : [...state.selectedTemplateIds, action.id],
    };
    case "ADD_NEW_PHASE": return { ...state, newPhases: [...state.newPhases, emptyNewPhase()] };
    case "UPDATE_NEW_PHASE": return {
      ...state,
      newPhases: state.newPhases.map((p) => p._id === action._id ? { ...p, ...action.patch } : p),
    };
    case "REMOVE_NEW_PHASE": return { ...state, newPhases: state.newPhases.filter((p) => p._id !== action._id) };
    case "SET_CREATING": return { ...state, creating: action.value };
    case "INIT_CREATE_LOG": return { ...state, createLog: action.log };
    case "UPDATE_LOG_ENTRY": return {
      ...state,
      createLog: state.createLog.map((e) => e.key === action.key ? { ...e, ...action.patch } : e),
    };
    case "SET_CREATED_IDS": return { ...state, createdIds: { ...state.createdIds, ...action.patch } };
    case "SET_PHASE_CREATED": return {
      ...state,
      createdIds: { ...state.createdIds, phases: { ...state.createdIds.phases, [action.key]: action.id } },
    };
    case "RESET": return { ...initialState, existingCycles: state.existingCycles, existingPhases: state.existingPhases, loading: false };
    default: return state;
  }
}

// ── Validation helpers ────────────────────────────────────────────────────────

function getDupYearStatus(cycleDraft, existingCycles) {
  const yr = String(cycleDraft.year || "").trim();
  const nm = cycleDraft.cycle_name.trim();
  if (!yr) return null;
  const exact = existingCycles.find(
    (c) => String(c.year) === yr && c.cycle_name.trim() === nm
  );
  if (exact) return "block";
  const yearOnly = existingCycles.find((c) => String(c.year) === yr);
  if (yearOnly) return "warn";
  return null;
}

// Returns errors array; empty = valid (zero phases is valid)
function validatePhaseStep(state) {
  const { cycleDraft, selectedTemplateIds, newPhases, existingCycles, existingPhases } = state;
  const year = String(cycleDraft.year || "").trim();
  const cycleName = cycleDraft.cycle_name.trim();
  const errs = [];

  // Gather all base slugs in this set
  const templates = existingPhases.filter((p) => !p.exam_cycle_id && selectedTemplateIds.includes(p.id));
  const templateSlugs = templates.map((t) => t.phase_slug);
  const newSlugs = newPhases.map((p) => effectiveSlug(p)).filter(Boolean);

  // New phase name requirement
  for (const p of newPhases) {
    if (!p.phase_name.trim()) { errs.push("Every new phase must have a name"); }
  }
  if (errs.length) return errs;

  // Intra-set uniqueness
  const allBase = [...templateSlugs, ...newSlugs];
  const seen = new Set();
  for (const s of allBase) {
    if (!s) continue;
    if (seen.has(s)) { errs.push(`Duplicate base slug: "${s}"`); }
    seen.add(s);
  }

  // Existing-phase collision (same year, already-posted cycle-bound phases)
  const sameYearCycleIds = new Set(
    existingCycles.filter((c) => String(c.year) === year).map((c) => c.id)
  );
  const existingSameYearSlugs = new Set(
    existingPhases
      .filter((p) => p.exam_cycle_id && sameYearCycleIds.has(p.exam_cycle_id))
      .map((p) => p.phase_slug)
  );
  for (const base of allBase) {
    if (!base) continue;
    const cb = cycleBoundSlug(base, year, cycleName);
    if (existingSameYearSlugs.has(cb)) {
      errs.push(`Phase slug "${cb}" already exists for a ${year} cycle`);
    }
  }
  return errs;
}

// ── Components ────────────────────────────────────────────────────────────────

function StepIndicator({ step }) {
  return (
    <ol className="flex gap-1 text-xs mb-6 flex-wrap" aria-label="Wizard steps">
      {STEP_LABELS.map((label, i) => (
        <li key={i} className={`flex items-center gap-1 ${i < STEP_LABELS.length - 1 ? "after:content-['›'] after:ml-1 after:text-muted-foreground" : ""}`}>
          <span className={`px-2 py-0.5 rounded font-medium ${
            i === step ? "bg-primary text-primary-foreground"
              : i < step ? "bg-green-100 text-green-800"
              : "bg-muted text-muted-foreground"
          }`}>
            {i < step ? "✓ " : ""}{label}
          </span>
        </li>
      ))}
    </ol>
  );
}

function FieldRow({ label, required, children }) {
  return (
    <label className="block">
      <span className="block text-xs text-muted-foreground mb-1">
        {label}{required && <span className="text-destructive ml-0.5">*</span>}
      </span>
      {children}
    </label>
  );
}

const INPUT_CLS = "w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background";
const SELECT_CLS = INPUT_CLS;

// ── Step 0: Cycle ─────────────────────────────────────────────────────────────

function StepCycle({ state, dispatch }) {
  const { cycleDraft, existingCycles, dupYearConfirmed } = state;
  const dupStatus = getDupYearStatus(cycleDraft, existingCycles);
  const isBlocked = dupStatus === "block";
  const isWarn = dupStatus === "warn" && !dupYearConfirmed;
  const canAdvance = !!(cycleDraft.cycle_name.trim() && String(cycleDraft.year).trim())
    && !isBlocked && !isWarn;

  return (
    <div data-testid="add-cycle-step-cycle">
      <h2 className="text-base font-semibold mb-4">Step 1 — New Cycle</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <FieldRow label="Cycle name" required>
          <input className={INPUT_CLS} value={cycleDraft.cycle_name}
            onChange={(e) => dispatch({ type: "SET_CYCLE_DRAFT", patch: { cycle_name: e.target.value } })}
            data-testid="ac-cycle-name" />
        </FieldRow>
        <FieldRow label="Year" required>
          <input className={INPUT_CLS} type="number" min="2000" max="2100" value={cycleDraft.year}
            onChange={(e) => dispatch({ type: "SET_CYCLE_DRAFT", patch: { year: e.target.value } })}
            data-testid="ac-cycle-year" />
        </FieldRow>
        <FieldRow label="Status">
          <select className={SELECT_CLS} value={cycleDraft.status}
            onChange={(e) => dispatch({ type: "SET_CYCLE_DRAFT", patch: { status: e.target.value } })}
            data-testid="ac-cycle-status">
            <option value="">Select…</option>
            {CYCLE_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </FieldRow>
        {DATE_FIELDS.map(([key, label]) => (
          <FieldRow key={key} label={label}>
            <input className={INPUT_CLS} type="date" value={cycleDraft[key]}
              onChange={(e) => dispatch({ type: "SET_CYCLE_DRAFT", patch: { [key]: e.target.value } })}
              data-testid={`ac-cycle-${key}`} />
          </FieldRow>
        ))}
      </div>

      {isBlocked && (
        <div className="mt-3 rounded border border-destructive/50 bg-destructive/5 p-3 text-xs text-destructive"
          data-testid="ac-dup-block">
          A cycle named "{cycleDraft.cycle_name}" for year {cycleDraft.year} already exists on this exam.
          Change the year or cycle name.
        </div>
      )}
      {dupStatus === "warn" && (
        <div className="mt-3 rounded border border-amber-300 bg-amber-50 p-3 text-xs text-amber-800"
          data-testid="ac-dup-warn">
          <p>A cycle for year {cycleDraft.year} already exists on this exam. Are you sure you want to add another?</p>
          {!dupYearConfirmed && (
            <button type="button" className="btn small mt-2" onClick={() => dispatch({ type: "CONFIRM_DUP_YEAR" })}
              data-testid="ac-dup-confirm">
              Yes, proceed with year {cycleDraft.year}
            </button>
          )}
          {dupYearConfirmed && (
            <p className="mt-1 text-green-700 font-medium" data-testid="ac-dup-confirmed">✓ Confirmed</p>
          )}
        </div>
      )}

      {existingCycles.length > 0 && (
        <details className="mt-3 text-xs text-muted-foreground">
          <summary className="cursor-pointer">Existing cycles ({existingCycles.length})</summary>
          <ul className="mt-1 list-disc list-inside">
            {existingCycles.map((c) => (
              <li key={c.id}>{c.cycle_name} ({c.year})</li>
            ))}
          </ul>
        </details>
      )}

      <div className="mt-6 flex justify-end">
        <button type="button" className="btn btn-primary" disabled={!canAdvance}
          onClick={() => dispatch({ type: "GOTO_STEP", step: 1 })}
          data-testid="ac-next-1">
          Next: Phases →
        </button>
      </div>
    </div>
  );
}

// ── Step 1: Phases ────────────────────────────────────────────────────────────

function StepPhases({ state, dispatch }) {
  const { cycleDraft, existingPhases, selectedTemplateIds, newPhases } = state;
  const year = String(cycleDraft.year || "").trim();
  const cycleName = cycleDraft.cycle_name.trim();

  const templates = existingPhases.filter((p) => !p.exam_cycle_id);
  const phaseErrs = validatePhaseStep(state);
  const canAdvance = phaseErrs.length === 0;

  return (
    <div data-testid="add-cycle-step-phases">
      <h2 className="text-base font-semibold mb-1">Step 2 — Phases</h2>
      <p className="text-xs text-muted-foreground mb-4">
        Select templates to clone as cycle-bound phases, and/or add brand-new phases.
        Nothing is written until Step 3.
      </p>

      {/* Template picker */}
      {templates.length > 0 ? (
        <section className="mb-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Clone from templates ({templates.length})
          </h3>
          <ul className="space-y-1" data-testid="ac-template-list">
            {templates.map((t) => {
              const selected = selectedTemplateIds.includes(t.id);
              const cbSlug = year ? cycleBoundSlug(t.phase_slug, year, cycleName) : "";
              return (
                <li key={t.id} className="flex items-center gap-3 rounded border border-border/60 px-3 py-2"
                  data-testid={`ac-template-${t.id}`}>
                  <input type="checkbox" id={`tmpl-${t.id}`} checked={selected}
                    onChange={() => dispatch({ type: "TOGGLE_TEMPLATE", id: t.id })}
                    data-testid={`ac-template-check-${t.id}`} />
                  <label htmlFor={`tmpl-${t.id}`} className="flex-1 text-sm cursor-pointer">
                    {t.phase_name}
                    <span className="ml-2 text-xs text-muted-foreground font-mono">{t.phase_slug}</span>
                    {selected && cbSlug && (
                      <span className="ml-2 text-xs text-green-700" data-testid={`ac-template-cb-slug-${t.id}`}>
                        → {cbSlug}
                      </span>
                    )}
                  </label>
                </li>
              );
            })}
          </ul>
        </section>
      ) : (
        <p className="text-xs text-muted-foreground mb-4" data-testid="ac-no-templates">
          No reusable templates exist for this exam yet.
        </p>
      )}

      {/* New phases */}
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
          New phases
        </h3>
        {newPhases.map((p, idx) => {
          const effSlug = effectiveSlug(p);
          const cbSlug = effSlug ? cycleBoundSlug(effSlug, year, cycleName) : "";
          const tmplSlug = effSlug ? slugify(effSlug) : "";
          const nameEmpty = !p.phase_name.trim();
          return (
            <div key={p._id} className="rounded border border-border/60 p-3 mb-3 space-y-2"
              data-testid={`ac-new-phase-${p._id}`}>
              <div className="flex justify-between items-center">
                <span className="text-xs font-medium text-muted-foreground">New phase {idx + 1}</span>
                <button type="button" className="btn small text-destructive"
                  onClick={() => dispatch({ type: "REMOVE_NEW_PHASE", _id: p._id })}
                  data-testid={`ac-remove-phase-${p._id}`}>✕ Remove</button>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <FieldRow label="Phase name" required>
                  <input className={`${INPUT_CLS}${nameEmpty ? " border-destructive" : ""}`}
                    value={p.phase_name}
                    onChange={(e) => dispatch({ type: "UPDATE_NEW_PHASE", _id: p._id, patch: { phase_name: e.target.value } })}
                    data-testid={`ac-phase-name-${p._id}`} />
                </FieldRow>
                <FieldRow label={`Base slug${!p.base_slug.trim() && p.phase_name.trim() ? " (auto)" : ""}`}>
                  <input className={INPUT_CLS} value={p.base_slug}
                    onChange={(e) => dispatch({ type: "UPDATE_NEW_PHASE", _id: p._id, patch: { base_slug: e.target.value } })}
                    placeholder={p.phase_name.trim() ? slugify(p.phase_name.trim()) : "e.g. prelims"}
                    data-testid={`ac-phase-base-slug-${p._id}`} />
                </FieldRow>
                <FieldRow label="Phase order">
                  <input className={INPUT_CLS} type="number" value={p.phase_order}
                    onChange={(e) => dispatch({ type: "UPDATE_NEW_PHASE", _id: p._id, patch: { phase_order: e.target.value } })}
                    data-testid={`ac-phase-order-${p._id}`} />
                </FieldRow>
                <FieldRow label="Mode">
                  <input className={INPUT_CLS} value={p.mode}
                    onChange={(e) => dispatch({ type: "UPDATE_NEW_PHASE", _id: p._id, patch: { mode: e.target.value } })}
                    data-testid={`ac-phase-mode-${p._id}`} />
                </FieldRow>
              </div>
              {cbSlug && (
                <p className="text-xs text-muted-foreground" data-testid={`ac-phase-cb-slug-${p._id}`}>
                  Cycle-bound slug: <code className="font-mono">{cbSlug}</code>
                </p>
              )}
              <label className="flex items-center gap-2 text-xs cursor-pointer"
                data-testid={`ac-phase-template-toggle-${p._id}`}>
                <input type="checkbox" checked={p.createTemplate}
                  onChange={(e) => dispatch({ type: "UPDATE_NEW_PHASE", _id: p._id, patch: { createTemplate: e.target.checked } })} />
                Also create reusable template{tmplSlug ? ` (slug: ${tmplSlug})` : ""}
              </label>
            </div>
          );
        })}
        <button type="button" className="btn small" onClick={() => dispatch({ type: "ADD_NEW_PHASE" })}
          data-testid="ac-add-phase">+ Add new phase</button>
      </section>

      {phaseErrs.length > 0 && (
        <ul className="mt-3 space-y-0.5" data-testid="ac-phase-errors">
          {phaseErrs.map((e, i) => <li key={i} className="text-xs text-destructive">{e}</li>)}
        </ul>
      )}

      <div className="mt-6 flex justify-between">
        <button type="button" className="btn small" onClick={() => dispatch({ type: "GOTO_STEP", step: 0 })}
          data-testid="ac-back-1">← Back</button>
        <button type="button" className="btn btn-primary" disabled={!canAdvance}
          onClick={() => dispatch({ type: "GOTO_STEP", step: 2 })}
          data-testid="ac-next-2">Review & Create →</button>
      </div>
    </div>
  );
}

// ── Step 2: Review & Create ───────────────────────────────────────────────────

function buildCreateLog(state) {
  const { cycleDraft, selectedTemplateIds, newPhases, existingPhases } = state;
  const year = String(cycleDraft.year || "").trim();
  const cycleName = cycleDraft.cycle_name.trim();
  const log = [{ key: "cycle", label: `Create cycle: ${cycleName} (${year})`, status: "pending" }];

  // New templates first
  for (const p of newPhases.filter((p) => p.createTemplate)) {
    const slug = slugify(effectiveSlug(p));
    log.push({ key: `tmpl-${p._id}`, label: `Template: ${p.phase_name} (${slug})`, status: "pending" });
  }
  // Cloned cycle-bound
  const templates = existingPhases.filter((p) => !p.exam_cycle_id && selectedTemplateIds.includes(p.id));
  for (const t of templates) {
    const cb = cycleBoundSlug(t.phase_slug, year, cycleName);
    log.push({ key: `cb-clone-${t.id}`, label: `Cloned phase: ${t.phase_name} (${cb})`, status: "pending" });
  }
  // New cycle-bound
  for (const p of newPhases) {
    const cb = cycleBoundSlug(effectiveSlug(p), year, cycleName);
    log.push({ key: `cb-new-${p._id}`, label: `New phase: ${p.phase_name} (${cb})`, status: "pending" });
  }
  return log;
}

function StepReview({ state, dispatch, examId }) {
  const { cycleDraft, selectedTemplateIds, newPhases, existingPhases, creating, createLog, createdIds } = state;
  const year = String(cycleDraft.year || "").trim();
  const cycleName = cycleDraft.cycle_name.trim();
  const navigate = useNavigate();

  const templates = existingPhases.filter((p) => !p.exam_cycle_id && selectedTemplateIds.includes(p.id));
  const newTemplatePhasess = newPhases.filter((p) => p.createTemplate);
  const isDone = createLog.length > 0 && createLog.every((e) => e.status === "ok");
  const hasFailed = createLog.some((e) => e.status === "error");
  const hasStarted = createLog.length > 0;

  async function runCreate() {
    const log = buildCreateLog(state);
    dispatch({ type: "INIT_CREATE_LOG", log });
    dispatch({ type: "SET_CREATING", value: true });

    let cycleId_ = createdIds.cycle;

    function mark(key, status, message = "") {
      dispatch({ type: "UPDATE_LOG_ENTRY", key, patch: { status, message } });
    }

    try {
      // ── Cycle ──
      if (!createdIds.cycle) {
        try {
          const r = await api.post(`${CMS}/exam-cycles`, {
            reason: REASON,
            payload: {
              exam_id: examId,
              cycle_name: cycleName,
              year: parseInt(year, 10),
              status: cycleDraft.status || undefined,
              notification_date: cycleDraft.notification_date || undefined,
              application_start: cycleDraft.application_start || undefined,
              application_end: cycleDraft.application_end || undefined,
              exam_start: cycleDraft.exam_start || undefined,
              exam_end: cycleDraft.exam_end || undefined,
            },
          });
          cycleId_ = r.row.id;
          dispatch({ type: "SET_CREATED_IDS", patch: { cycle: r.row.id } });
          mark("cycle", "ok");
        } catch (ex) {
          mark("cycle", "error", getApiErrorMessage(ex));
          dispatch({ type: "SET_CREATING", value: false });
          return;
        }
      } else {
        mark("cycle", "ok");
      }

      // ── New templates first ──
      for (const p of newPhases.filter((ph) => ph.createTemplate)) {
        const key = `tmpl-${p._id}`;
        if (createdIds.phases[key]) { mark(key, "ok"); continue; }
        try {
          const slug = slugify(effectiveSlug(p));
          const r = await api.post(`${CMS}/exam-phases`, {
            reason: REASON,
            payload: {
              exam_id: examId,
              phase_name: p.phase_name.trim(),
              phase_slug: slug,
              exam_cycle_id: null,
              phase_order: p.phase_order ? parseInt(p.phase_order, 10) : undefined,
              mode: p.mode.trim() || undefined,
              duration_mins: p.duration_mins ? parseInt(p.duration_mins, 10) : undefined,
              total_questions: p.total_questions ? parseInt(p.total_questions, 10) : undefined,
              total_marks: p.total_marks ? parseInt(p.total_marks, 10) : undefined,
            },
          });
          dispatch({ type: "SET_PHASE_CREATED", key, id: r.row.id });
          mark(key, "ok");
        } catch (ex) {
          mark(key, "error", getApiErrorMessage(ex));
          dispatch({ type: "SET_CREATING", value: false });
          return;
        }
      }

      // ── Cloned cycle-bound phases ──
      for (const t of templates) {
        const key = `cb-clone-${t.id}`;
        if (createdIds.phases[key]) { mark(key, "ok"); continue; }
        try {
          const cb = cycleBoundSlug(t.phase_slug, year, cycleName);
          const r = await api.post(`${CMS}/exam-phases`, {
            reason: REASON,
            payload: {
              exam_id: examId,
              phase_name: t.phase_name,
              phase_slug: cb,
              exam_cycle_id: cycleId_,
              phase_order: t.phase_order ?? undefined,
              mode: t.mode || undefined,
              duration_mins: t.duration_mins || undefined,
              total_questions: t.total_questions || undefined,
              total_marks: t.total_marks || undefined,
            },
          });
          dispatch({ type: "SET_PHASE_CREATED", key, id: r.row.id });
          mark(key, "ok");
        } catch (ex) {
          mark(key, "error", getApiErrorMessage(ex));
          dispatch({ type: "SET_CREATING", value: false });
          return;
        }
      }

      // ── New cycle-bound phases ──
      for (const p of newPhases) {
        const key = `cb-new-${p._id}`;
        if (createdIds.phases[key]) { mark(key, "ok"); continue; }
        try {
          const cb = cycleBoundSlug(effectiveSlug(p), year, cycleName);
          const r = await api.post(`${CMS}/exam-phases`, {
            reason: REASON,
            payload: {
              exam_id: examId,
              phase_name: p.phase_name.trim(),
              phase_slug: cb,
              exam_cycle_id: cycleId_,
              phase_order: p.phase_order ? parseInt(p.phase_order, 10) : undefined,
              mode: p.mode.trim() || undefined,
              duration_mins: p.duration_mins ? parseInt(p.duration_mins, 10) : undefined,
              total_questions: p.total_questions ? parseInt(p.total_questions, 10) : undefined,
              total_marks: p.total_marks ? parseInt(p.total_marks, 10) : undefined,
            },
          });
          dispatch({ type: "SET_PHASE_CREATED", key, id: r.row.id });
          mark(key, "ok");
        } catch (ex) {
          mark(key, "error", getApiErrorMessage(ex));
          dispatch({ type: "SET_CREATING", value: false });
          return;
        }
      }
    } finally {
      dispatch({ type: "SET_CREATING", value: false });
    }
  }

  return (
    <div data-testid="add-cycle-step-review">
      <h2 className="text-base font-semibold mb-4">Step 3 — Review & Create</h2>

      <div className="space-y-3 mb-6 text-sm">
        <section>
          <h3 className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">
            Cycle: {cycleName} ({year})
          </h3>
          <p className="text-xs">Status: {cycleDraft.status || "—"}{cycleDraft.exam_start ? ` · Exam start: ${cycleDraft.exam_start}` : ""}</p>
        </section>
        {templates.length > 0 && (
          <section>
            <h3 className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">
              Cloned cycle-bound phases
            </h3>
            <ul className="list-disc list-inside text-xs space-y-0.5" data-testid="ac-review-cloned">
              {templates.map((t) => (
                <li key={t.id}>{t.phase_name} · slug: <code>{cycleBoundSlug(t.phase_slug, year, cycleName)}</code></li>
              ))}
            </ul>
          </section>
        )}
        {newPhases.length > 0 && (
          <section>
            <h3 className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">
              New cycle-bound phases
            </h3>
            <ul className="list-disc list-inside text-xs space-y-0.5" data-testid="ac-review-new-cb">
              {newPhases.map((p) => (
                <li key={p._id}>{p.phase_name} · slug: <code>{cycleBoundSlug(effectiveSlug(p), year, cycleName)}</code></li>
              ))}
            </ul>
          </section>
        )}
        {newTemplatePhasess.length > 0 && (
          <section>
            <h3 className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">
              New template phases
            </h3>
            <ul className="list-disc list-inside text-xs space-y-0.5" data-testid="ac-review-new-templates">
              {newTemplatePhasess.map((p) => (
                <li key={p._id}>{p.phase_name} · slug: <code>{slugify(effectiveSlug(p))}</code></li>
              ))}
            </ul>
          </section>
        )}
      </div>

      {hasStarted && (
        <div className="rounded border border-border/60 p-3 mb-4 space-y-1" data-testid="ac-create-log">
          {createLog.map((e) => (
            <div key={e.key} className="text-xs flex gap-2 items-baseline" data-testid={`ac-log-${e.key}`}>
              <span className={`font-mono ${e.status === "ok" ? "text-green-700" : e.status === "error" ? "text-destructive" : "text-muted-foreground"}`}>
                {e.status === "ok" ? "✓" : e.status === "error" ? "✗" : "·"}
              </span>
              <span>{e.label}</span>
              {e.message && <span className="text-destructive">{e.message}</span>}
            </div>
          ))}
        </div>
      )}

      {isDone && (
        <div className="rounded bg-green-50 border border-green-200 p-4 mb-4 text-sm text-green-800"
          data-testid="ac-create-success">
          <p className="font-semibold">✓ Cycle and phases created.</p>
          <p className="mt-1">Cycle ID: <code className="font-mono text-xs">{createdIds.cycle}</code></p>
          <button type="button" className="btn small mt-3"
            onClick={() => navigate(`/admin/exam-intelligence/workspace/${examId}/${createdIds.cycle}`)}>
            Open cycle workspace →
          </button>
        </div>
      )}

      <div className="flex gap-3 items-center">
        {!hasStarted && (
          <button type="button" className="btn small"
            onClick={() => dispatch({ type: "GOTO_STEP", step: 1 })}
            data-testid="ac-back-2">← Back</button>
        )}
        {!isDone && (
          <button type="button" className="btn btn-primary" disabled={creating}
            onClick={runCreate}
            data-testid="ac-create">
            {creating ? "Creating…" : hasFailed ? "Resume creation" : "Create"}
          </button>
        )}
        {isDone && (
          <button type="button" className="btn small" onClick={() => dispatch({ type: "RESET" })}
            data-testid="ac-reset">Add another cycle</button>
        )}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AddCycleWizard() {
  const { exam_id } = useParams();
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    Promise.all([
      api.get(`${CMS}/exam-cycles?exam_id=${exam_id}&limit=200`),
      api.get(`${CMS}/exam-phases?exam_id=${exam_id}&limit=500`),
    ])
      .then(([cyclesResp, phasesResp]) => {
        dispatch({
          type: "LOAD_OK",
          cycles: cyclesResp.items || [],
          phases: phasesResp.items || [],
        });
      })
      .catch((ex) => dispatch({ type: "LOAD_ERR", error: getApiErrorMessage(ex) }));
  }, [exam_id]);

  if (state.loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8" data-testid="add-cycle-wizard">
        <p className="text-sm text-muted-foreground">Loading exam data…</p>
      </div>
    );
  }

  if (state.loadError) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8" data-testid="add-cycle-wizard">
        <p className="text-sm text-destructive" role="alert">Failed to load: {state.loadError}</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8" data-testid="add-cycle-wizard">
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Add cycle</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Exam: <code className="font-mono text-xs">{exam_id}</code>
          {" · "}Nothing is written until Step 3.
        </p>
      </div>
      <StepIndicator step={state.step} />
      {state.step === 0 && <StepCycle state={state} dispatch={dispatch} />}
      {state.step === 1 && <StepPhases state={state} dispatch={dispatch} />}
      {state.step === 2 && <StepReview state={state} dispatch={dispatch} examId={exam_id} />}
    </div>
  );
}
