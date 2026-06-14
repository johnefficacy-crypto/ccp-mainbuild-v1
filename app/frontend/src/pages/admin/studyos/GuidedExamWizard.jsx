import React, { useEffect, useReducer } from "react";
import { useNavigate } from "react-router-dom";
import { api, getApiErrorMessage } from "../../../lib/api";
import { slugify, cycleBoundSlug } from "../../../lib/slugify";
import CycleForm from "../../../features/admin/exam-intelligence/forms/CycleForm";
import PhaseForm from "../../../features/admin/exam-intelligence/forms/PhaseForm";

// ── Constants ────────────────────────────────────────────────────────────────

const EXAM_TYPES = ["recruitment", "entrance", "certification", "opportunity", "other"];
const MANAGEMENT_MODES = ["core", "light", "index_only", "archive"];
const CADENCES = ["annual", "recurring", "irregular", "one_off", "unknown"];
const CYCLE_STATUSES = ["expected", "open", "active", "closed", "completed", "cancelled"];
const ORG_TYPES = [
  "state_psc", "central", "banking", "insurance", "railways",
  "defence", "police", "teaching", "university", "board", "other",
];

const STEP_LABELS = ["Organization", "Exam", "Cycle", "Phases", "Review & Create"];

const CMS = "/api/admin/exam-intelligence-cms";
const REASON = "guided exam wizard create";

// ── Helpers ──────────────────────────────────────────────────────────────────

let _phaseSeq = 0;
function newPhaseId() { return `p${++_phaseSeq}`; }

function emptyPhase() {
  return {
    _id: newPhaseId(),
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

// Effective base_slug: explicit trimmed value OR slugify(phase_name)
function effectiveSlug(p) {
  return p.base_slug.trim() || slugify(p.phase_name.trim());
}

// Returns array of human-readable error strings; empty = all valid
function validatePhases(phases) {
  const errs = [];
  const seen = new Set();
  for (const p of phases) {
    if (!p.phase_name.trim()) {
      errs.push("Every phase must have a name");
      continue;
    }
    const slug = effectiveSlug(p);
    if (!slug) {
      errs.push(`Phase "${p.phase_name}" has no usable slug`);
      continue;
    }
    if (seen.has(slug)) {
      errs.push(`Duplicate base slug: "${slug}"`);
    }
    seen.add(slug);
  }
  return errs;
}

// ── State / Reducer ───────────────────────────────────────────────────────────

const initialState = {
  step: 0,
  // Step 0 — org (orgId only used in select mode)
  orgMode: "select",
  orgSearch: "",
  orgId: null,
  orgDraft: { name: "", short_name: "", type: "", state: "", website_url: "" },
  // Step 1 — exam
  examDraft: {
    name: "", exam_type: "", exam_family_id: "",
    management_mode: "light", cadence: "unknown", description: "",
  },
  examId: null,
  // Step 2 — cycle
  cycleDraft: {
    cycle_name: "", year: "", status: "",
    notification_date: "", application_start: "", application_end: "",
    exam_start: "", exam_end: "",
  },
  cycleId: null,
  // Step 3 — phases
  phases: [],
  // Step 4 — create state
  creating: false,
  createLog: [],
  // org id only stored after Step-5 POST (never from Step-1)
  createdIds: { org: null, exam: null, cycle: null, phases: {} },
};

function reducer(state, action) {
  switch (action.type) {
    case "GOTO_STEP": return { ...state, step: action.step };
    case "SET_ORG_MODE": return { ...state, orgMode: action.mode };
    case "SET_ORG_SEARCH": return { ...state, orgSearch: action.value };
    case "SET_ORG_ID": return { ...state, orgId: action.id };
    case "SET_ORG_DRAFT": return { ...state, orgDraft: { ...state.orgDraft, ...action.patch } };
    case "SET_EXAM_DRAFT": return { ...state, examDraft: { ...state.examDraft, ...action.patch } };
    case "SET_CYCLE_DRAFT": return { ...state, cycleDraft: { ...state.cycleDraft, ...action.patch } };
    case "ADD_PHASE": return { ...state, phases: [...state.phases, emptyPhase()] };
    case "UPDATE_PHASE": return {
      ...state,
      phases: state.phases.map((p) => p._id === action._id ? { ...p, ...action.patch } : p),
    };
    case "REMOVE_PHASE": return { ...state, phases: state.phases.filter((p) => p._id !== action._id) };
    case "SET_CREATING": return { ...state, creating: action.value };
    case "INIT_CREATE_LOG": return { ...state, createLog: action.log };
    case "UPDATE_LOG_ENTRY": return {
      ...state,
      createLog: state.createLog.map((e) =>
        e.key === action.key ? { ...e, ...action.patch } : e
      ),
    };
    case "SET_CREATED_IDS": return {
      ...state,
      createdIds: { ...state.createdIds, ...action.patch },
    };
    case "SET_PHASE_CREATED": return {
      ...state,
      createdIds: {
        ...state.createdIds,
        phases: { ...state.createdIds.phases, [action.key]: action.id },
      },
    };
    case "RESET": return { ...initialState, phases: [] };
    default: return state;
  }
}

// ── Components ────────────────────────────────────────────────────────────────

function StepIndicator({ step }) {
  return (
    <ol className="flex gap-1 text-xs mb-6 flex-wrap" aria-label="Wizard steps">
      {STEP_LABELS.map((label, i) => (
        <li key={i} className={`flex items-center gap-1 ${i < STEP_LABELS.length - 1 ? "after:content-['›'] after:ml-1 after:text-muted-foreground" : ""}`}>
          <span
            className={`px-2 py-0.5 rounded font-medium ${
              i === step
                ? "bg-primary text-primary-foreground"
                : i < step
                ? "bg-green-100 text-green-800"
                : "bg-muted text-muted-foreground"
            }`}
          >
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

// ── Step 0: Organization ──────────────────────────────────────────────────────

function StepOrg({ state, dispatch }) {
  const { orgMode, orgSearch, orgId, orgDraft } = state;
  const [allOrgs, setAllOrgs] = React.useState(null);
  const [loadingOrgs, setLoadingOrgs] = React.useState(false);

  useEffect(() => {
    if (orgMode === "select" && allOrgs === null) {
      setLoadingOrgs(true);
      api.get("/api/admin/organizations")
        .then((d) => setAllOrgs(d.items || []))
        .catch(() => setAllOrgs([]))
        .finally(() => setLoadingOrgs(false));
    }
  }, [orgMode, allOrgs]);

  const filtered = React.useMemo(() => {
    if (!allOrgs) return [];
    const q = orgSearch.toLowerCase();
    return q ? allOrgs.filter((o) =>
      o.name?.toLowerCase().includes(q) ||
      o.short_name?.toLowerCase().includes(q) ||
      o.type?.toLowerCase().includes(q)
    ) : allOrgs;
  }, [allOrgs, orgSearch]);

  const canAdvance = orgMode === "select"
    ? !!orgId
    : (!!orgDraft.name.trim() && !!orgDraft.short_name.trim() && !!orgDraft.type);

  return (
    <div data-testid="wizard-step-org">
      <h2 className="text-base font-semibold mb-4">Step 1 — Organization</h2>

      <div className="flex gap-2 mb-4">
        <button
          type="button"
          className={`btn small ${orgMode === "select" ? "btn-primary" : ""}`}
          onClick={() => dispatch({ type: "SET_ORG_MODE", mode: "select" })}
          data-testid="org-mode-select"
        >
          Select existing
        </button>
        <button
          type="button"
          className={`btn small ${orgMode === "create" ? "btn-primary" : ""}`}
          onClick={() => dispatch({ type: "SET_ORG_MODE", mode: "create" })}
          data-testid="org-mode-create"
        >
          Create new
        </button>
      </div>

      {orgMode === "select" && (
        <div className="space-y-3">
          <input
            type="search"
            className={INPUT_CLS}
            placeholder="Search by name, short name, or type…"
            value={orgSearch}
            onChange={(e) => dispatch({ type: "SET_ORG_SEARCH", value: e.target.value })}
            data-testid="org-search-input"
          />
          {loadingOrgs && <p className="text-xs text-muted-foreground">Loading…</p>}
          {!loadingOrgs && allOrgs !== null && (
            <ul className="border border-border/60 rounded max-h-60 overflow-y-auto text-sm" data-testid="org-list">
              {filtered.length === 0 && (
                <li className="p-3 text-muted-foreground">No organizations found.</li>
              )}
              {filtered.map((o) => (
                <li key={o.id}>
                  <button
                    type="button"
                    className={`w-full text-left px-3 py-2 hover:bg-accent text-sm ${orgId === o.id ? "bg-accent font-medium" : ""}`}
                    onClick={() => dispatch({ type: "SET_ORG_ID", id: o.id })}
                    data-testid={`org-select-${o.id}`}
                  >
                    {o.name} · <span className="text-muted-foreground">{o.type}{o.state ? ` / ${o.state}` : ""}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {orgId && (
            <p className="text-xs text-green-700" data-testid="org-selected-id">
              ✓ Selected: {orgId}
            </p>
          )}
        </div>
      )}

      {orgMode === "create" && (
        <div className="space-y-3" data-testid="org-create-form">
          <p className="text-xs text-amber-700 bg-amber-50 rounded px-2 py-1.5">
            Org will be created in Step 5. Nothing is posted yet.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <FieldRow label="Name" required>
              <input className={INPUT_CLS} value={orgDraft.name}
                onChange={(e) => dispatch({ type: "SET_ORG_DRAFT", patch: { name: e.target.value } })}
                data-testid="org-name" />
            </FieldRow>
            <FieldRow label="Short name (acronym)" required>
              <input className={INPUT_CLS} value={orgDraft.short_name}
                onChange={(e) => dispatch({ type: "SET_ORG_DRAFT", patch: { short_name: e.target.value } })}
                data-testid="org-short-name" />
            </FieldRow>
            <FieldRow label="Type" required>
              <select className={SELECT_CLS} value={orgDraft.type}
                onChange={(e) => dispatch({ type: "SET_ORG_DRAFT", patch: { type: e.target.value } })}
                data-testid="org-type">
                <option value="">Select…</option>
                {ORG_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </FieldRow>
            <FieldRow label="State (for state-level orgs)">
              <input className={INPUT_CLS} value={orgDraft.state}
                onChange={(e) => dispatch({ type: "SET_ORG_DRAFT", patch: { state: e.target.value } })}
                data-testid="org-state" />
            </FieldRow>
            <FieldRow label="Website URL">
              <input className={INPUT_CLS} type="url" value={orgDraft.website_url}
                onChange={(e) => dispatch({ type: "SET_ORG_DRAFT", patch: { website_url: e.target.value } })}
                data-testid="org-website" />
            </FieldRow>
          </div>
        </div>
      )}

      <div className="mt-6 flex justify-end">
        <button
          type="button"
          className="btn btn-primary"
          disabled={!canAdvance}
          onClick={() => dispatch({ type: "GOTO_STEP", step: 1 })}
          data-testid="wizard-next-1"
        >
          Next: Exam →
        </button>
      </div>
    </div>
  );
}

// ── Step 1: Exam ──────────────────────────────────────────────────────────────

function StepExam({ state, dispatch }) {
  const { examDraft, orgId, orgMode, orgDraft } = state;
  // Show resolved org label — for create mode show draft name (not yet posted)
  const orgLabel = orgMode === "select" ? (orgId || "—") : (orgDraft.name.trim() || "(new org)");

  function handleNext() {
    const coerced = {
      ...examDraft,
      management_mode: examDraft.management_mode || "light",
      cadence: examDraft.cadence || "unknown",
    };
    if (coerced.management_mode !== examDraft.management_mode || coerced.cadence !== examDraft.cadence) {
      dispatch({ type: "SET_EXAM_DRAFT", patch: coerced });
    }
    dispatch({ type: "GOTO_STEP", step: 2 });
  }

  return (
    <div data-testid="wizard-step-exam">
      <h2 className="text-base font-semibold mb-4">Step 2 — Exam</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <FieldRow label="Name" required>
          <input className={INPUT_CLS} value={examDraft.name}
            onChange={(e) => dispatch({ type: "SET_EXAM_DRAFT", patch: { name: e.target.value } })}
            data-testid="exam-name" />
        </FieldRow>
        <FieldRow label="Conducting organization">
          <input className={INPUT_CLS} value={orgLabel} readOnly data-testid="exam-org-id" />
        </FieldRow>
        <FieldRow label="Exam type">
          <select className={SELECT_CLS} value={examDraft.exam_type}
            onChange={(e) => dispatch({ type: "SET_EXAM_DRAFT", patch: { exam_type: e.target.value } })}
            data-testid="exam-type">
            <option value="">Select…</option>
            {EXAM_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </FieldRow>
        <FieldRow label="Management mode">
          <select className={SELECT_CLS} value={examDraft.management_mode || "light"}
            onChange={(e) => dispatch({ type: "SET_EXAM_DRAFT", patch: { management_mode: e.target.value } })}
            data-testid="exam-management-mode">
            {MANAGEMENT_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </FieldRow>
        <FieldRow label="Cadence">
          <select className={SELECT_CLS} value={examDraft.cadence || "unknown"}
            onChange={(e) => dispatch({ type: "SET_EXAM_DRAFT", patch: { cadence: e.target.value } })}
            data-testid="exam-cadence">
            {CADENCES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </FieldRow>
        <FieldRow label="Exam family ID (optional)">
          <input className={INPUT_CLS} value={examDraft.exam_family_id}
            onChange={(e) => dispatch({ type: "SET_EXAM_DRAFT", patch: { exam_family_id: e.target.value } })}
            placeholder="UUID or leave blank"
            data-testid="exam-family-id" />
        </FieldRow>
        <FieldRow label="Description">
          <textarea className={INPUT_CLS} value={examDraft.description} rows={2}
            onChange={(e) => dispatch({ type: "SET_EXAM_DRAFT", patch: { description: e.target.value } })}
            data-testid="exam-description" />
        </FieldRow>
      </div>
      <div className="mt-6 flex justify-between">
        <button type="button" className="btn small" onClick={() => dispatch({ type: "GOTO_STEP", step: 0 })}
          data-testid="wizard-back-1">← Back</button>
        <button type="button" className="btn btn-primary" disabled={!examDraft.name.trim()} onClick={handleNext}
          data-testid="wizard-next-2">Next: Cycle →</button>
      </div>
    </div>
  );
}

// ── Step 2: Cycle ─────────────────────────────────────────────────────────────

function StepCycle({ state, dispatch }) {
  const { cycleDraft } = state;
  const canAdvance = cycleDraft.cycle_name.trim() && String(cycleDraft.year).trim();

  return (
    <div data-testid="wizard-step-cycle">
      <h2 className="text-base font-semibold mb-4">Step 3 — Exam Cycle</h2>
      <CycleForm
        values={cycleDraft}
        onChange={(key, val) => dispatch({ type: "SET_CYCLE_DRAFT", patch: { [key]: val } })}
        showReason={false}
      />
      <div className="mt-6 flex justify-between">
        <button type="button" className="btn small" onClick={() => dispatch({ type: "GOTO_STEP", step: 1 })}
          data-testid="wizard-back-2">← Back</button>
        <button type="button" className="btn btn-primary" disabled={!canAdvance}
          onClick={() => dispatch({ type: "GOTO_STEP", step: 3 })}
          data-testid="wizard-next-3">Next: Phases →</button>
      </div>
    </div>
  );
}

// ── Step 3: Phases ────────────────────────────────────────────────────────────

function StepPhases({ state, dispatch }) {
  const { phases, cycleDraft } = state;
  const year = String(cycleDraft.year || "").trim();
  const cycleName = cycleDraft.cycle_name.trim();
  const phaseErrs = validatePhases(phases);
  const canAdvance = phaseErrs.length === 0; // zero phases is also valid

  return (
    <div data-testid="wizard-step-phases">
      <h2 className="text-base font-semibold mb-1">Step 4 — Phases</h2>
      <p className="text-xs text-muted-foreground mb-4">
        Define 0 or more phases. Each creates a cycle-bound row (slug suffixed with year).
        Toggle "also template" to additionally create a bare-slug reusable template. Leave
        base slug blank to derive it from the phase name.
      </p>

      {phases.map((p, idx) => {
        const effSlug = effectiveSlug(p);
        const dupeSlug = effSlug
          ? phases.filter((q) => effectiveSlug(q) === effSlug).length > 1
          : false;
        const nameEmpty = !p.phase_name.trim();
        const rowInvalid = nameEmpty || !effSlug || dupeSlug;
        return (
          <div
            key={p._id}
            className={`rounded border p-3 mb-3 space-y-2 ${rowInvalid ? "border-destructive/50" : "border-border/60"}`}
            data-testid={`phase-row-${p._id}`}
          >
            <div className="flex justify-between items-center">
              <span className="text-xs font-medium text-muted-foreground">Phase {idx + 1}</span>
              <button type="button" className="btn small text-destructive"
                onClick={() => dispatch({ type: "REMOVE_PHASE", _id: p._id })}
                data-testid={`phase-remove-${p._id}`}>✕ Remove</button>
            </div>
            <PhaseForm
              values={p}
              onChange={(key, val) => dispatch({ type: "UPDATE_PHASE", _id: p._id, patch: { [key]: val } })}
              cycleName={cycleName}
              year={year}
              showSlug
              showMode
              showTemplate
              showDates={false}
              isDuplicate={dupeSlug}
              rowId={p._id}
            />
          </div>
        );
      })}

      <button type="button" className="btn small" onClick={() => dispatch({ type: "ADD_PHASE" })}
        data-testid="add-phase">+ Add phase</button>

      {phaseErrs.length > 0 && (
        <ul className="mt-3 space-y-0.5" data-testid="phase-errors">
          {phaseErrs.map((e, i) => (
            <li key={i} className="text-xs text-destructive">{e}</li>
          ))}
        </ul>
      )}

      <div className="mt-6 flex justify-between">
        <button type="button" className="btn small" onClick={() => dispatch({ type: "GOTO_STEP", step: 2 })}
          data-testid="wizard-back-3">← Back</button>
        <button type="button" className="btn btn-primary" disabled={!canAdvance}
          onClick={() => dispatch({ type: "GOTO_STEP", step: 4 })}
          data-testid="wizard-next-4">Review & Create →</button>
      </div>
    </div>
  );
}

// ── Step 4: Review & Create ───────────────────────────────────────────────────

function phaseRows(phases, cycleId, year, cycleName) {
  const cbRows = [];
  const tmplRows = [];
  for (const p of phases) {
    const slug = effectiveSlug(p);
    const cbSlug = cycleBoundSlug(slug, year, cycleName);
    cbRows.push({ ...p, _kind: "cycle-bound", phase_slug: cbSlug, exam_cycle_id: cycleId });
    if (p.createTemplate) {
      tmplRows.push({ ...p, _kind: "template", phase_slug: slugify(slug), exam_cycle_id: null });
    }
  }
  return { cbRows, tmplRows };
}

function buildCreateLog(state) {
  const { orgMode, phases, cycleDraft } = state;
  const year = String(cycleDraft.year || "").trim();
  const cycleName = cycleDraft.cycle_name.trim();
  const log = [];
  // Org always included for create mode (posted fresh in Step 5)
  if (orgMode === "create") {
    log.push({ key: "org", label: "Create organization", status: "pending" });
  }
  log.push({ key: "exam", label: "Create exam", status: "pending" });
  log.push({ key: "cycle", label: "Create cycle", status: "pending" });
  const { tmplRows, cbRows } = phaseRows(phases, null, year, cycleName);
  for (const p of tmplRows) {
    log.push({ key: `tmpl-${p._id}`, label: `Template phase: ${p.phase_name} (${p.phase_slug})`, status: "pending" });
  }
  for (const p of cbRows) {
    log.push({ key: `cb-${p._id}`, label: `Cycle-bound phase: ${p.phase_name} (${p.phase_slug})`, status: "pending" });
  }
  return log;
}

function StepReview({ state, dispatch }) {
  const {
    orgMode, orgId, orgDraft, examDraft, cycleDraft, phases,
    creating, createLog, createdIds,
  } = state;
  const year = String(cycleDraft.year || "").trim();
  const cycleName = cycleDraft.cycle_name.trim();
  const navigate = useNavigate();
  const { cbRows, tmplRows } = phaseRows(phases, createdIds.cycle, year, cycleName);

  const isDone = createLog.length > 0 && createLog.every((e) => e.status === "ok");
  const hasFailed = createLog.some((e) => e.status === "error");
  const hasStarted = createLog.length > 0;

  async function runCreate() {
    const log = buildCreateLog(state);
    dispatch({ type: "INIT_CREATE_LOG", log });
    dispatch({ type: "SET_CREATING", value: true });

    // Resolved org id: select → state.orgId; create → will be set after POST
    let orgId_ = orgMode === "select" ? orgId : createdIds.org;
    let examId_ = createdIds.exam;
    let cycleId_ = createdIds.cycle;

    function mark(key, status, message = "") {
      dispatch({ type: "UPDATE_LOG_ENTRY", key, patch: { status, message } });
    }

    try {
      // ── Org (create mode only; skip if already created in a prior resume) ──
      if (orgMode === "create" && !createdIds.org) {
        try {
          const r = await api.post("/api/admin/organizations", {
            name: orgDraft.name.trim(),
            short_name: orgDraft.short_name.trim(),
            type: orgDraft.type,
            state: orgDraft.state.trim() || undefined,
            website_url: orgDraft.website_url.trim() || undefined,
          });
          orgId_ = r.id;
          dispatch({ type: "SET_CREATED_IDS", patch: { org: r.id } });
          mark("org", "ok", r.warnings?.length ? `${r.warnings.length} similar org(s) found` : "");
        } catch (ex) {
          mark("org", "error", getApiErrorMessage(ex));
          dispatch({ type: "SET_CREATING", value: false });
          return;
        }
      } else if (orgMode === "create" && createdIds.org) {
        // Already created in a previous attempt — skip, mark done
        mark("org", "ok");
      }

      // ── Exam ──
      if (!createdIds.exam) {
        const examPayload = {
          name: examDraft.name.trim(),
          conducting_organization_id: orgId_,
          exam_type: examDraft.exam_type || undefined,
          exam_family_id: examDraft.exam_family_id.trim() || undefined,
          management_mode: examDraft.management_mode || "light",
          cadence: examDraft.cadence || "unknown",
          description: examDraft.description.trim() || undefined,
        };
        try {
          const r = await api.post(`${CMS}/exams`, { reason: REASON, payload: examPayload });
          examId_ = r.row.id;
          dispatch({ type: "SET_CREATED_IDS", patch: { exam: r.row.id } });
          mark("exam", "ok");
        } catch (ex) {
          mark("exam", "error", getApiErrorMessage(ex));
          dispatch({ type: "SET_CREATING", value: false });
          return;
        }
      } else {
        mark("exam", "ok");
      }

      // ── Cycle ──
      if (!createdIds.cycle) {
        const cyclePayload = {
          exam_id: examId_,
          cycle_name: cycleDraft.cycle_name.trim(),
          year: parseInt(cycleDraft.year, 10),
          status: cycleDraft.status || undefined,
          // Empty date strings → undefined (omit from payload)
          notification_date: cycleDraft.notification_date || undefined,
          application_start: cycleDraft.application_start || undefined,
          application_end: cycleDraft.application_end || undefined,
          exam_start: cycleDraft.exam_start || undefined,
          exam_end: cycleDraft.exam_end || undefined,
        };
        try {
          const r = await api.post(`${CMS}/exam-cycles`, { reason: REASON, payload: cyclePayload });
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

      // ── Phases — templates first (sorted by phase_order), then cycle-bound ──
      const sortedByOrder = (arr) =>
        [...arr].sort((a, b) => Number(a.phase_order || 0) - Number(b.phase_order || 0));

      for (const p of sortedByOrder(tmplRows)) {
        const key = `tmpl-${p._id}`;
        if (createdIds.phases[key]) { mark(key, "ok"); continue; }
        try {
          const r = await api.post(`${CMS}/exam-phases`, {
            reason: REASON,
            payload: {
              exam_id: examId_,
              phase_name: p.phase_name.trim(),
              phase_slug: p.phase_slug,
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

      for (const p of sortedByOrder(cbRows)) {
        const key = `cb-${p._id}`;
        if (createdIds.phases[key]) { mark(key, "ok"); continue; }
        try {
          const r = await api.post(`${CMS}/exam-phases`, {
            reason: REASON,
            payload: {
              exam_id: examId_,
              phase_name: p.phase_name.trim(),
              phase_slug: p.phase_slug,
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
    <div data-testid="wizard-step-review">
      <h2 className="text-base font-semibold mb-4">Step 5 — Review & Create</h2>

      {/* Summary */}
      <div className="space-y-3 mb-6 text-sm">
        <section>
          <h3 className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">Organization</h3>
          {orgMode === "select"
            ? <p>Using existing org: <code className="font-mono text-xs">{orgId}</code></p>
            : <p>{orgDraft.name} ({orgDraft.type}{orgDraft.state ? ` / ${orgDraft.state}` : ""}){createdIds.org ? <span className="ml-2 text-green-700 text-xs">✓ id: {createdIds.org}</span> : ""}</p>
          }
        </section>
        <section>
          <h3 className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">Exam</h3>
          <p>{examDraft.name} · {examDraft.exam_type || "—"} · {examDraft.management_mode || "light"} · {examDraft.cadence || "unknown"}</p>
        </section>
        <section>
          <h3 className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">Cycle</h3>
          <p>{cycleDraft.cycle_name} ({year})</p>
        </section>
        {tmplRows.length > 0 && (
          <section>
            <h3 className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">Template phases</h3>
            <ul className="list-disc list-inside text-xs space-y-0.5" data-testid="review-template-phases">
              {tmplRows.map((p) => (
                <li key={p._id}>{p.phase_name} · slug: <code>{p.phase_slug}</code> · cycle: none</li>
              ))}
            </ul>
          </section>
        )}
        <section>
          <h3 className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">
            Cycle-bound phases for {cycleDraft.cycle_name || "cycle"} ({year})
          </h3>
          {cbRows.length === 0
            ? <p className="text-xs text-muted-foreground">No phases defined.</p>
            : (
              <ul className="list-disc list-inside text-xs space-y-0.5" data-testid="review-cb-phases">
                {cbRows.map((p) => (
                  <li key={p._id}>{p.phase_name} · slug: <code>{p.phase_slug}</code> · cycle: {cycleDraft.cycle_name} ({year})</li>
                ))}
              </ul>
            )
          }
        </section>
      </div>

      {/* Create log */}
      {hasStarted && (
        <div className="rounded border border-border/60 p-3 mb-4 space-y-1" data-testid="create-log">
          {createLog.map((e) => (
            <div key={e.key} className="text-xs flex gap-2 items-baseline" data-testid={`log-${e.key}`}>
              <span className={`font-mono ${e.status === "ok" ? "text-green-700" : e.status === "error" ? "text-destructive" : "text-muted-foreground"}`}>
                {e.status === "ok" ? "✓" : e.status === "error" ? "✗" : "·"}
              </span>
              <span>{e.label}</span>
              {e.message && <span className={e.status === "error" ? "text-destructive" : "text-amber-700"}>{e.message}</span>}
            </div>
          ))}
        </div>
      )}

      {isDone && (
        <div className="rounded bg-green-50 border border-green-200 p-4 mb-4 text-sm text-green-800" data-testid="create-success">
          <p className="font-semibold">✓ All entities created successfully.</p>
          <p className="mt-1">Exam ID: <code className="font-mono text-xs">{createdIds.exam}</code></p>
          <button type="button" className="btn small mt-3"
            onClick={() => navigate(`/admin/exam-intelligence/workspace/${createdIds.exam}?tab=setup`)}>
            Open exam workspace →
          </button>
          <div className="mt-4 pt-4 border-t border-green-300">
            <p className="font-semibold text-amber-800">⚠ This exam is not planner-ready yet.</p>
            <p className="mt-1 text-xs text-green-700">Complete these steps in the exam workspace before the exam appears in student plans:</p>
            <ul className="mt-2 space-y-1 text-xs text-green-800">
              <li>
                <span className="inline-block w-4">☐</span>
                <button type="button" className="underline hover:no-underline text-left"
                  onClick={() => navigate(`/admin/exam-intelligence/workspace/${createdIds.exam}?tab=setup`)}>
                  Documents
                </button>
                {" "}— upload the official notification and syllabus PDF
              </li>
              <li>
                <span className="inline-block w-4">☐</span>
                <button type="button" className="underline hover:no-underline text-left"
                  onClick={() => navigate(`/admin/exam-intelligence/workspace/${createdIds.exam}?tab=setup`)}>
                  Syllabus Mapper
                </button>
                {" "}— map syllabus topics to the subject taxonomy
              </li>
              <li>
                <span className="inline-block w-4">☐</span>
                <button type="button" className="underline hover:no-underline text-left"
                  onClick={() => navigate(`/admin/exam-intelligence/workspace/${createdIds.exam}?tab=setup`)}>
                  PYQ Workbench
                </button>
                {" "}— import and review previous-year questions
              </li>
              <li>
                <span className="inline-block w-4">☐</span>
                <button type="button" className="underline hover:no-underline text-left"
                  onClick={() => navigate(`/admin/exam-intelligence/workspace/${createdIds.exam}?tab=setup`)}>
                  Updates
                </button>
                {" "}— add at least one published update for this exam
              </li>
              <li>
                <span className="inline-block w-4">☐</span>
                <button type="button" className="underline hover:no-underline text-left"
                  onClick={() => navigate(`/admin/exam-intelligence/workspace/${createdIds.exam}?tab=setup`)}>
                  Competition
                </button>
                {" "}— fill seats, applicants, and selection ratio
              </li>
              <li>
                <span className="inline-block w-4">☐</span>
                <button type="button" className="underline hover:no-underline text-left"
                  onClick={() => navigate(`/admin/exam-intelligence/workspace/${createdIds.exam}?tab=setup`)}>
                  Review &amp; Activate
                </button>
                {" "}— resolve all blockers and activate the exam
              </li>
              <li>
                <span className="inline-block w-4">☐</span>
                <button type="button" className="underline hover:no-underline text-left"
                  onClick={() => navigate("/admin/exam-eligibility")}>
                  Exam Eligibility baseline
                </button>
                {" "}— set qualification and age-limit rules so eligibility checks pass
              </li>
            </ul>
          </div>
        </div>
      )}

      <div className="flex gap-3 items-center">
        {!hasStarted && (
          <button type="button" className="btn small"
            onClick={() => dispatch({ type: "GOTO_STEP", step: 3 })}
            data-testid="wizard-back-4">← Back</button>
        )}
        {!isDone && (
          <button type="button" className="btn btn-primary" disabled={creating}
            onClick={runCreate}
            data-testid="wizard-create">
            {creating ? "Creating…" : hasFailed ? "Resume creation" : "Create all"}
          </button>
        )}
        {isDone && (
          <button type="button" className="btn small" onClick={() => dispatch({ type: "RESET" })}
            data-testid="wizard-reset">Start over</button>
        )}
      </div>
    </div>
  );
}

// ── Main wizard ───────────────────────────────────────────────────────────────

export default function GuidedExamWizard() {
  const [state, dispatch] = useReducer(reducer, initialState);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8" data-testid="guided-exam-wizard">
      <h1 className="text-xl font-semibold mb-2">Guided exam setup</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Create a new exam end-to-end: org → exam → cycle → phases. Nothing is written until Step 5.
      </p>
      <StepIndicator step={state.step} />
      {state.step === 0 && <StepOrg state={state} dispatch={dispatch} />}
      {state.step === 1 && <StepExam state={state} dispatch={dispatch} />}
      {state.step === 2 && <StepCycle state={state} dispatch={dispatch} />}
      {state.step === 3 && <StepPhases state={state} dispatch={dispatch} />}
      {state.step === 4 && <StepReview state={state} dispatch={dispatch} />}
    </div>
  );
}
