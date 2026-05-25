import React, { useEffect, useState } from "react";
import { RotateCcw, Plus, FileText } from "lucide-react";
import { api, getApiErrorMessage } from "../../../lib/api";
import { parseImportFile } from "../../../lib/bulkImportFile";
import CmsRefField from "../../../features/admin/shared/CmsRefField";
import ExamIntelDocuments from "./ExamIntelDocuments";

// Reusable ref-picker descriptors. Each points at a CMS list endpoint that
// already exists; child pickers cascade off a sibling form field.
const REF_EXAM = { endpoint: "exams", labelKey: "name", secondaryKey: "slug" };
const REF_FAMILY = { endpoint: "exam-families", labelKey: "name", secondaryKey: "slug" };
const REF_SUBJECT = { endpoint: "subjects", labelKey: "name", secondaryKey: "slug" };
const refCycle = (filters) => ({ endpoint: "exam-cycles", labelKey: "cycle_name", secondaryKey: "year", filters });
const refPhase = (filters) => ({ endpoint: "exam-phases", labelKey: "phase_name", secondaryKey: "phase_slug", filters });
const refTopic = (filters, staticFilters) => ({ endpoint: "topics", labelKey: "name", secondaryKey: "level", filters, staticFilters });
const refDoc = (filters) => ({ endpoint: "syllabus-documents", labelKey: "title", secondaryKey: "document_type", filters });
const refPyqSource = (filters) => ({ endpoint: "pyq-sources", labelKey: "title", secondaryKey: "source_type", filters });
const refPaper = (filters) => ({ endpoint: "pyq-papers", labelKey: "paper_code", secondaryKey: "year", filters });
const refQuestion = (filters) => ({ endpoint: "pyq-questions", labelKey: "question_text", secondaryKey: "question_number", filters });

// Enum values mirror the CHECK constraints on public.exam_topic_coverage
// (migration 030). Keep these in sync with the migration, not invented.
const COVERAGE_DEPTHS = ["unknown", "none", "mentioned", "light", "normal", "deep", "core"];
const COVERAGE_SOURCE_BASES = ["official_syllabus", "pyq_analysis", "admin_review", "hybrid", "manual", "model_generated"];
const COVERAGE_REVIEWER_STATUSES = ["draft", "pending_review", "reviewed", "locked", "rejected"];

// Taxonomy enums mirror the CHECK constraints in migration 029.
const TOPIC_LEVELS = ["topic", "microtopic", "concept"];
const TOPIC_PREREQ_RELATIONS = ["requires", "recommended_before", "supports", "foundation_for"];

// Syllabus mention enum mirrors the CHECK constraint in migration 031.
const MENTION_TYPES = ["explicit", "implied", "parent_topic_only", "derived"];

// PYQ enums mirror the CHECK constraints in migration 032.
const PYQ_SOURCE_TYPES = ["official", "memory_based", "coaching", "community", "aggregator", "unknown"];
const PYQ_TAG_ROLES = ["primary", "secondary", "prerequisite", "trap", "calculation_layer", "conceptual_layer"];
const PYQ_TAGGING_SOURCES = ["manual", "admin", "ai", "rule", "imported"];

const ENTITY_CONFIG = {
  "exam-families": {
    label: "Exam families",
    fields: [
      { key: "slug", label: "slug", required: true },
      { key: "name", label: "name", required: true },
      { key: "description", label: "description" },
      { key: "is_active", label: "is_active", type: "bool" },
    ],
    columns: ["slug", "name", "is_active", "created_at"],
  },
  exams: {
    label: "Exams",
    fields: [
      { key: "slug", label: "slug", required: true },
      { key: "name", label: "name", required: true },
      { key: "exam_family_id", label: "exam_family_id", type: "ref", ref: REF_FAMILY },
      { key: "exam_type", label: "exam_type (recruitment|entrance|certification|opportunity|other)" },
      { key: "description", label: "description" },
      { key: "is_active", label: "is_active", type: "bool" },
    ],
    columns: ["slug", "name", "exam_type", "is_active", "created_at"],
  },
  "exam-cycles": {
    label: "Exam cycles",
    fields: [
      { key: "exam_id", label: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "year", label: "year", required: true, type: "int" },
      { key: "cycle_name", label: "cycle_name", required: true },
      { key: "status", label: "status (expected|open|active|closed|completed|cancelled)" },
      { key: "notification_date", label: "notification_date (YYYY-MM-DD)" },
      { key: "application_start", label: "application_start (YYYY-MM-DD)" },
      { key: "application_end", label: "application_end (YYYY-MM-DD)" },
      { key: "exam_start", label: "exam_start (YYYY-MM-DD)" },
      { key: "exam_end", label: "exam_end (YYYY-MM-DD)" },
      { key: "source_url", label: "source_url" },
    ],
    columns: ["exam_id", "year", "cycle_name", "status"],
  },
  "exam-phases": {
    label: "Exam phases",
    fields: [
      { key: "exam_id", label: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "phase_name", label: "phase_name", required: true },
      { key: "phase_slug", label: "phase_slug", required: true },
      { key: "exam_cycle_id", label: "exam_cycle_id", type: "ref", ref: refCycle({ exam_id: "exam_id" }) },
      { key: "phase_order", label: "phase_order", type: "int" },
      { key: "mode", label: "mode" },
      { key: "duration_mins", label: "duration_mins", type: "int" },
      { key: "total_questions", label: "total_questions", type: "int" },
      { key: "total_marks", label: "total_marks", type: "int" },
      { key: "status", label: "status (expected|active|completed|cancelled)" },
    ],
    columns: ["exam_id", "phase_name", "phase_order", "status"],
  },
  "syllabus-documents": {
    label: "Syllabus documents",
    fields: [
      { key: "exam_id", label: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "document_type", label: "document_type (notification|syllabus_pdf|official_page|pattern_notice|corrigendum|other)", required: true },
      { key: "title", label: "title", required: true },
      { key: "source_url", label: "source_url" },
      { key: "storage_path", label: "storage_path (pick an uploaded document)", type: "ref",
        ref: { endpoint: "documents", valueField: "storage_path", labelKey: "original_filename",
               displayFields: ["original_filename", "created_at"], secondaryKey: "document_kind",
               filters: { exam_id: "exam_id" } } },
      { key: "exam_cycle_id", label: "exam_cycle_id", type: "ref", ref: refCycle({ exam_id: "exam_id" }) },
    ],
    columns: ["title", "document_type", "trust_status", "exam_id"],
  },
  "pyq-papers": {
    label: "PYQ papers",
    fields: [
      { key: "exam_id", label: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "pyq_source_id", label: "pyq_source_id (in this exam)", type: "ref", ref: refPyqSource({ exam_id: "exam_id" }) },
      { key: "year", label: "year", required: true, type: "int" },
      { key: "exam_phase_id", label: "exam_phase_id", type: "ref", ref: refPhase({ exam_id: "exam_id" }) },
      { key: "paper_date", label: "paper_date (YYYY-MM-DD)" },
      { key: "shift", label: "shift" },
      { key: "paper_code", label: "paper_code" },
      { key: "source_url", label: "source_url" },
      { key: "source_type", label: "source_type (official|memory_based|coaching|community|aggregator|unknown)" },
    ],
    columns: ["year", "paper_code", "source_type", "trust_status"],
  },
  "exam-topic-coverage": {
    label: "Exam topic coverage",
    fields: [
      { key: "exam_id", label: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "topic_id", label: "topic_id", required: true },
      { key: "exam_cycle_id", label: "exam_cycle_id", type: "ref", ref: refCycle({ exam_id: "exam_id" }) },
      { key: "exam_phase_id", label: "exam_phase_id", type: "ref", ref: refPhase({ exam_id: "exam_id", exam_cycle_id: "exam_cycle_id" }) },
      { key: "coverage_depth", label: "coverage_depth", type: "enum", options: COVERAGE_DEPTHS },
      { key: "expected_difficulty", label: "expected_difficulty" },
      { key: "exam_priority_score", label: "exam_priority_score (0–100)", type: "number", step: 0.01, min: 0, max: 100 },
      { key: "is_high_yield", label: "is_high_yield", type: "bool" },
      { key: "confidence_score", label: "confidence_score (0–1)", type: "number", step: 0.001, min: 0, max: 1 },
      { key: "source_basis", label: "source_basis", type: "enum", options: COVERAGE_SOURCE_BASES },
      { key: "reviewer_status", label: "reviewer_status (forced to pending_review on create)", type: "enum", options: COVERAGE_REVIEWER_STATUSES },
      { key: "review_notes", label: "review_notes" },
      { key: "metadata", label: "metadata (JSON object)", type: "json" },
    ],
    columns: ["exam_id", "topic_id", "coverage_depth", "exam_priority_score", "is_high_yield", "reviewer_status"],
  },
  "policy-updates": {
    label: "Policy updates",
    fields: [
      { key: "exam_id", label: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "update_type", label: "update_type (notification_change|cycle_change|...)", required: true },
      { key: "title", label: "title", required: true },
      { key: "summary", label: "summary" },
      { key: "source_type", label: "source_type (official|aggregator|research|opportunity|unknown)" },
      { key: "source_url", label: "source_url" },
      { key: "affects_syllabus", label: "affects_syllabus", type: "bool" },
      { key: "affects_plan", label: "affects_plan", type: "bool" },
    ],
    columns: ["title", "update_type", "reviewer_status", "source_type"],
  },
  subjects: {
    label: "Subjects",
    fields: [
      { key: "slug", label: "slug", required: true },
      { key: "name", label: "name", required: true },
      { key: "subject_group", label: "subject_group" },
      { key: "default_difficulty_level", label: "default_difficulty_level" },
      { key: "description", label: "description" },
      { key: "is_active", label: "is_active", type: "bool" },
    ],
    columns: ["slug", "name", "subject_group", "is_active"],
  },
  topics: {
    label: "Topics",
    fields: [
      { key: "subject_id", label: "subject_id", required: true, type: "ref", ref: REF_SUBJECT },
      { key: "level", label: "level", type: "enum", options: TOPIC_LEVELS },
      // Parent picker is scoped to the chosen subject and restricted to
      // level=topic, so a microtopic/concept can only hang off a top-level
      // topic (the UI rule layered over the permissive backend).
      { key: "parent_topic_id", label: "parent_topic_id (a level=topic in this subject)", type: "ref", ref: refTopic({ subject_id: "subject_id" }, { level: "topic" }) },
      { key: "slug", label: "slug", required: true },
      { key: "name", label: "name", required: true },
      { key: "default_difficulty_level", label: "default_difficulty_level" },
      { key: "description", label: "description" },
      { key: "is_active", label: "is_active", type: "bool" },
    ],
    columns: ["subject_id", "slug", "name", "level", "is_active"],
  },
  "topic-aliases": {
    label: "Topic aliases",
    supportsBulk: false,
    fields: [
      { key: "subject_id", label: "subject_id (scope only — not saved)", type: "ref", ref: REF_SUBJECT, uiOnly: true },
      { key: "topic_id", label: "topic_id", required: true, type: "ref", ref: refTopic({ subject_id: "subject_id" }) },
      { key: "alias", label: "alias", required: true },
      { key: "source_context", label: "source_context" },
    ],
    columns: ["topic_id", "alias", "normalized_alias", "created_at"],
  },
  "topic-prerequisites": {
    label: "Topic prerequisites",
    supportsBulk: false,
    fields: [
      { key: "subject_id", label: "subject_id (scope only — not saved)", type: "ref", ref: REF_SUBJECT, uiOnly: true },
      { key: "topic_id", label: "topic_id", required: true, type: "ref", ref: refTopic({ subject_id: "subject_id" }) },
      { key: "prerequisite_topic_id", label: "prerequisite_topic_id", required: true, type: "ref", ref: refTopic({ subject_id: "subject_id" }) },
      { key: "relation_type", label: "relation_type", type: "enum", options: TOPIC_PREREQ_RELATIONS },
      { key: "strength", label: "strength (0–1)", type: "number", step: 0.001, min: 0, max: 1 },
      { key: "source_basis", label: "source_basis" },
    ],
    columns: ["topic_id", "prerequisite_topic_id", "relation_type", "strength"],
  },
  "syllabus-topic-mentions": {
    label: "Syllabus topic mentions",
    notice: "Lands as pending — verify in /admin/exam-intelligence review.",
    fields: [
      { key: "exam_id", label: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "syllabus_document_id", label: "syllabus_document_id (in this exam)", required: true, type: "ref", ref: refDoc({ exam_id: "exam_id" }) },
      { key: "exam_cycle_id", label: "exam_cycle_id", type: "ref", ref: refCycle({ exam_id: "exam_id" }) },
      { key: "exam_phase_id", label: "exam_phase_id", type: "ref", ref: refPhase({ exam_id: "exam_id" }) },
      { key: "subject_id", label: "subject_id (scope only — not saved)", type: "ref", ref: REF_SUBJECT, uiOnly: true },
      { key: "topic_id", label: "topic_id", required: true, type: "ref", ref: refTopic({ subject_id: "subject_id" }) },
      { key: "mention_type", label: "mention_type", type: "enum", options: MENTION_TYPES },
      { key: "raw_text", label: "raw_text" },
      { key: "normalized_text", label: "normalized_text" },
      { key: "confidence_score", label: "confidence_score (0–1)", type: "number", step: 0.001, min: 0, max: 1 },
      { key: "extraction_method", label: "extraction_method" },
      { key: "metadata", label: "metadata (JSON object)", type: "json" },
    ],
    columns: ["topic_id", "mention_type", "reviewer_status", "raw_text"],
  },
  "pyq-sources": {
    label: "PYQ sources",
    notice: "Lands as pending — verify trust before papers from it feed scoring.",
    fields: [
      { key: "exam_id", label: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "source_type", label: "source_type", type: "enum", options: PYQ_SOURCE_TYPES },
      { key: "title", label: "title" },
      { key: "source_url", label: "source_url" },
      { key: "source_id", label: "source_id (source_registry uuid, optional)" },
      { key: "metadata", label: "metadata (JSON object)", type: "json" },
    ],
    columns: ["exam_id", "source_type", "title", "trust_status"],
  },
  "pyq-question-topic-tags": {
    label: "PYQ question topic tags",
    notice: "Lands as pending — verify in /admin/exam-intelligence review.",
    fields: [
      { key: "exam_id", label: "exam_id (scope only — not saved)", type: "ref", ref: REF_EXAM, uiOnly: true },
      { key: "pyq_paper_id", label: "pyq_paper_id (scope only — not saved)", type: "ref", ref: refPaper({ exam_id: "exam_id" }), uiOnly: true },
      { key: "question_id", label: "question_id", required: true, type: "ref", ref: refQuestion({ pyq_paper_id: "pyq_paper_id" }) },
      { key: "subject_id", label: "subject_id (scope only — not saved)", type: "ref", ref: REF_SUBJECT, uiOnly: true },
      { key: "topic_id", label: "topic_id", required: true, type: "ref", ref: refTopic({ subject_id: "subject_id" }) },
      { key: "tag_role", label: "tag_role", type: "enum", options: PYQ_TAG_ROLES },
      { key: "tagging_source", label: "tagging_source", type: "enum", options: PYQ_TAGGING_SOURCES },
      { key: "tag_weight", label: "tag_weight (0–1)", type: "number", step: 0.001, min: 0, max: 1 },
      { key: "confidence_score", label: "confidence_score (0–1)", type: "number", step: 0.001, min: 0, max: 1 },
      { key: "metadata", label: "metadata (JSON object)", type: "json" },
    ],
    columns: ["question_id", "topic_id", "tag_role", "reviewer_status"],
  },
};

const ENTITY_KEYS = Object.keys(ENTITY_CONFIG);

function parseValue(field, raw) {
  if (raw === "" || raw == null) return undefined;
  if (field.type === "bool") return raw === "true";
  if (field.type === "int") {
    const n = parseInt(raw, 10);
    return Number.isFinite(n) ? n : undefined;
  }
  if (field.type === "number") {
    const n = parseFloat(raw);
    return Number.isFinite(n) ? n : undefined;
  }
  if (field.type === "json") {
    // Throws on malformed input; submitCreate catches it and surfaces a
    // field-specific message rather than silently dropping the value.
    const parsed = JSON.parse(raw);
    if (parsed == null || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("must be a JSON object");
    }
    return parsed;
  }
  return raw;
}

export default function AdminExamIntelCms() {
  const [entity, setEntity] = useState("exam-families");
  const [items, setItems] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [status, setStatus] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showBulk, setShowBulk] = useState(false);
  const [bulkRows, setBulkRows] = useState("");
  const [bulkReason, setBulkReason] = useState("");
  const [fileParseError, setFileParseError] = useState("");
  const [bulkResult, setBulkResult] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [reason, setReason] = useState("");

  const isDocuments = entity === "documents";
  const cfg = ENTITY_CONFIG[entity];

  async function load() {
    // The Documents panel manages its own data via the upload/list endpoints.
    if (isDocuments) {
      setItems(null);
      setBusy(false);
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const r = await api.get(`/api/admin/exam-intelligence-cms/${entity}?limit=50`);
      setItems(r);
    } catch (e) {
      setErr(getApiErrorMessage(e));
      setItems(null);
    } finally {
      setBusy(false);
    }
  }

  async function handleBulkFile(e) {
    setFileParseError("");
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    try {
      const text = await file.text();
      const { rows, errors } = parseImportFile(file.name, text);
      if (errors.length && rows.length === 0) {
        setFileParseError(errors.join("; "));
        return;
      }
      setBulkRows(JSON.stringify(rows, null, 2));
      if (errors.length) {
        // Partial parse — surface the per-row errors but still let the
        // admin review and submit the clean rows.
        setFileParseError(`Parsed ${rows.length} rows. Skipped: ${errors.join("; ")}`);
      }
    } catch (ex) {
      setFileParseError(`Could not read file: ${ex.message || ex}`);
    }
  }

  async function submitBulk(e) {
    e.preventDefault();
    setBulkResult(null);
    if (bulkReason.trim().length < 8) {
      setStatus({ ok: false, message: "Bulk reason must be ≥8 chars." });
      return;
    }
    let rows;
    try {
      rows = JSON.parse(bulkRows);
      if (!Array.isArray(rows)) throw new Error("Top-level JSON must be an array");
    } catch (e) {
      setStatus({ ok: false, message: `Could not parse rows JSON: ${e.message}` });
      return;
    }
    try {
      const r = await api.post("/api/admin/exam-intelligence-cms/bulk-import", {
        reason: bulkReason.trim(),
        entity,
        rows,
      });
      setBulkResult(r);
      setStatus({
        ok: r.ok,
        message: `Bulk import: ${r.ok_count}/${r.total} ok, ${r.error_count} errors. audit_id=${r.audit_id}`,
      });
      load();
    } catch (ex) {
      setStatus({ ok: false, message: getApiErrorMessage(ex) });
    }
  }

  async function submitCreate(e) {
    e.preventDefault();
    if (reason.trim().length < 8) {
      setStatus({ ok: false, message: "Reason must be ≥8 chars." });
      return;
    }
    const payload = {};
    for (const f of cfg.fields) {
      // uiOnly fields (e.g. a subject_id scope picker) drive cascade
      // filtering but are not real columns — never submit them.
      if (f.uiOnly) continue;
      let v;
      try {
        v = parseValue(f, formValues[f.key]);
      } catch (err) {
        setStatus({ ok: false, message: `Invalid ${f.key}: ${err.message}` });
        return;
      }
      if (v !== undefined) payload[f.key] = v;
    }
    // UI rule: a microtopic/concept must hang off a parent topic. The
    // parent picker only offers level=topic rows, so this guarantees the
    // "microtopic requires a level=topic parent" contract.
    if (entity === "topics" && ["microtopic", "concept"].includes(payload.level) && !payload.parent_topic_id) {
      setStatus({ ok: false, message: `A ${payload.level} must have a parent topic (level=topic).` });
      return;
    }
    try {
      const r = await api.post(`/api/admin/exam-intelligence-cms/${entity}`, {
        reason: reason.trim(),
        payload,
      });
      setStatus({ ok: true, message: `Created. audit_id=${r.audit_id}` });
      setShowCreate(false);
      setFormValues({});
      setReason("");
      load();
    } catch (ex) {
      setStatus({ ok: false, message: getApiErrorMessage(ex) });
    }
  }

  function insertBulkTemplate() {
    const keys = cfg.fields.filter((f) => !f.uiOnly).map((f) => f.key);
    const skeleton = Object.fromEntries(keys.map((k) => [k, ""]));
    setBulkRows(JSON.stringify([skeleton], null, 2));
  }

  useEffect(() => {
    setItems(null);
    setStatus(null);
    setShowCreate(false);
    setShowBulk(false);
    setBulkRows("");
    setBulkResult(null);
    setFileParseError("");
    setFormValues({});
    setReason("");
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entity]);

  return (
    <div className="space-y-5" data-testid="admin-exam-intel-cms">
      <div>
        <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground font-semibold">
          Study OS · exam intelligence CMS
        </div>
        <h1 className="mt-1 font-heading text-3xl font-semibold tracking-tight">Exam Intelligence CMS</h1>
        <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
          Create exam families, exams, cycles, phases, syllabus documents, PYQ papers/questions, topic
          coverage, and policy updates. Per spec §12 #4: CMS <strong>feeds</strong> the review queue —
          rows with a review_status / trust_status land at <code>pending</code>; promote them via the
          existing review queue, not here.
        </p>
      </div>

      <div className="flex gap-2 items-end flex-wrap">
        <label>
          <span className="block text-xs text-muted-foreground mb-1">Entity</span>
          <select
            value={entity}
            onChange={(e) => setEntity(e.target.value)}
            className="px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
            data-testid="cms-entity-select"
          >
            {ENTITY_KEYS.map((k) => (
              <option key={k} value={k}>{ENTITY_CONFIG[k].label} · {k}</option>
            ))}
            <option value="documents">Documents (PDF upload) · documents</option>
          </select>
        </label>
        {!isDocuments ? (
          <>
            <button type="button" className="btn small" onClick={load} disabled={busy}>
              <RotateCcw className="h-3 w-3" /> {busy ? "Loading…" : "Reload"}
            </button>
            <button
              type="button"
              className="btn small"
              onClick={() => setShowCreate((s) => !s)}
              data-testid="cms-toggle-create"
            >
              <Plus className="h-3 w-3" /> {showCreate ? "Cancel" : "New row"}
            </button>
            {cfg.supportsBulk !== false ? (
              <button
                type="button"
                className="btn small"
                onClick={() => setShowBulk((s) => !s)}
                data-testid="cms-toggle-bulk"
              >
                <Plus className="h-3 w-3" /> {showBulk ? "Cancel bulk" : "Bulk import"}
              </button>
            ) : null}
          </>
        ) : null}
      </div>

      {status ? (
        <div className={`text-sm ${status.ok ? "text-emerald-700" : "text-red-700"}`} role="status" aria-live="polite">
          {status.message}
        </div>
      ) : null}

      {err ? <div className="text-sm text-red-700" role="alert">{err}</div> : null}

      {isDocuments ? <ExamIntelDocuments /> : null}

      {!isDocuments && showBulk && cfg.supportsBulk !== false ? (
        <form onSubmit={submitBulk} className="rounded border border-border/60 bg-card p-4 space-y-2" data-testid="cms-bulk-form">
          <h3 className="text-sm font-semibold">Bulk import {ENTITY_CONFIG[entity].label}</h3>
          <p className="text-xs text-muted-foreground">
            Drop a <strong>.csv</strong> or <strong>.json</strong> file, or paste a JSON array of row
            objects (max 500). Each row goes through the same validation as the single-row create — required
            fields, FK resolution, enum constraints, and forced statuses. Per-row results are returned so you
            can fix and retry only the failed rows. PDF and Markdown are out of scope — those need a separate
            extraction pipeline.
          </p>
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">Upload .csv / .json</span>
            <input
              type="file"
              accept=".csv,.json,text/csv,application/json"
              onChange={handleBulkFile}
              data-testid="cms-bulk-file"
              className="block text-xs"
            />
            {fileParseError ? (
              <div className="mt-1 text-xs text-red-700" role="alert" data-testid="cms-bulk-file-error">
                {fileParseError}
              </div>
            ) : null}
          </label>
          <label className="block">
            <span className="flex items-center justify-between text-xs text-muted-foreground mb-1">
              <span>Rows JSON (array, max 500)</span>
              <button
                type="button"
                className="btn small"
                onClick={insertBulkTemplate}
                data-testid="cms-bulk-template"
              >
                Insert template
              </button>
            </span>
            <textarea
              value={bulkRows}
              onChange={(e) => setBulkRows(e.target.value)}
              rows={8}
              placeholder='[{"slug":"a","name":"A"},{"slug":"b","name":"B"}]'
              className="w-full px-2 py-1.5 text-xs font-mono border border-border/60 rounded bg-background"
              data-testid="cms-bulk-rows"
            />
          </label>
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">Reason (≥8 chars)</span>
            <textarea value={bulkReason} onChange={(e) => setBulkReason(e.target.value)} rows={2} className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background" data-testid="cms-bulk-reason" />
          </label>
          <button type="submit" className="btn small" data-testid="cms-bulk-submit">Import</button>
          {bulkResult ? (
            <details className="text-xs mt-2">
              <summary className="cursor-pointer text-muted-foreground">
                {bulkResult.ok_count}/{bulkResult.total} succeeded — click to see per-row results
              </summary>
              <pre className="mt-2 bg-muted p-2 rounded max-h-60 overflow-auto">
                {JSON.stringify(bulkResult.results, null, 2)}
              </pre>
            </details>
          ) : null}
        </form>
      ) : null}

      {!isDocuments && showCreate ? (
        <form onSubmit={submitCreate} className="rounded border border-border/60 bg-card p-4 space-y-2" data-testid="cms-create-form">
          <h3 className="text-sm font-semibold">New {cfg.label} row</h3>
          {cfg.notice ? (
            <p className="text-xs text-amber-700" data-testid="cms-create-notice">{cfg.notice}</p>
          ) : null}
          <div className="grid gap-2 sm:grid-cols-2">
            {cfg.fields.map((f) => (
              <label key={f.key} className="block">
                <span className="block text-xs text-muted-foreground mb-1">
                  {f.label}{f.required ? <span className="text-red-700"> *</span> : null}
                </span>
                {f.type === "ref" ? (
                  <CmsRefField
                    field={f}
                    value={formValues[f.key] ?? ""}
                    formValues={formValues}
                    onChange={(val) => setFormValues((p) => ({ ...p, [f.key]: val }))}
                    testId={`cms-field-${f.key}`}
                  />
                ) : f.type === "bool" ? (
                  <select
                    value={formValues[f.key] ?? ""}
                    onChange={(e) => setFormValues((p) => ({ ...p, [f.key]: e.target.value }))}
                    className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
                    data-testid={`cms-field-${f.key}`}
                  >
                    <option value="">(skip)</option>
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </select>
                ) : f.type === "enum" ? (
                  <select
                    value={formValues[f.key] ?? ""}
                    onChange={(e) => setFormValues((p) => ({ ...p, [f.key]: e.target.value }))}
                    className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
                    data-testid={`cms-field-${f.key}`}
                  >
                    <option value="">(skip)</option>
                    {f.options.map((o) => (
                      <option key={o} value={o}>{o}</option>
                    ))}
                  </select>
                ) : f.type === "json" ? (
                  <textarea
                    value={formValues[f.key] ?? ""}
                    onChange={(e) => setFormValues((p) => ({ ...p, [f.key]: e.target.value }))}
                    rows={3}
                    placeholder="{}"
                    className="w-full px-2 py-1.5 text-sm font-mono border border-border/60 rounded bg-background"
                    data-testid={`cms-field-${f.key}`}
                  />
                ) : (
                  <input
                    type={f.type === "int" || f.type === "number" ? "number" : "text"}
                    step={f.type === "number" ? f.step : undefined}
                    min={f.min}
                    max={f.max}
                    value={formValues[f.key] ?? ""}
                    onChange={(e) => setFormValues((p) => ({ ...p, [f.key]: e.target.value }))}
                    className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
                    data-testid={`cms-field-${f.key}`}
                  />
                )}
              </label>
            ))}
          </div>
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">Reason (≥8 chars, recorded in audit)</span>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
              data-testid="cms-reason"
            />
          </label>
          <button type="submit" className="btn small" data-testid="cms-create-submit">
            Create
          </button>
        </form>
      ) : null}

      {!isDocuments ? (
      <section className="rounded border border-border/60 bg-card p-0 overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-2"><FileText className="inline h-3 w-3 mr-1" />id</th>
              {cfg.columns.map((c) => (
                <th key={c} className="text-left p-2">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {!items?.items?.length ? (
              <tr><td colSpan={cfg.columns.length + 1} className="p-3 text-muted-foreground text-center">
                {busy ? "Loading…" : "No rows."}
              </td></tr>
            ) : items.items.map((r) => (
              <tr key={r.id} className="border-t border-border/40">
                <td className="p-2 font-mono">{r.id?.slice(0, 8)}…</td>
                {cfg.columns.map((c) => (
                  <td key={c} className="p-2">
                    {r[c] == null ? "—" : typeof r[c] === "boolean" ? String(r[c]) : String(r[c]).slice(0, 60)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {items?.total != null ? (
          <div className="text-xs text-muted-foreground p-2 border-t border-border/40">
            total {items.total}, showing {items.items?.length ?? 0}
          </div>
        ) : null}
      </section>
      ) : null}
    </div>
  );
}
