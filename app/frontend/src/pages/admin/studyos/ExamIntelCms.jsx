import React, { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { RotateCcw, Plus, FileText } from "lucide-react";
import { api, getApiErrorMessage } from "../../../lib/api";
import useApiAction from "../../../lib/hooks/useApiAction";
import { parseImportFile } from "../../../lib/bulkImportFile";
import { useAuth } from "../../../lib/authContext";
import AdminSafetyBanner from "../../../shared/ui/AdminSafetyBanner";
import CmsRefField from "../../../features/admin/shared/CmsRefField";
import { DateField } from "../../../shared/ui/heavy";
import ExamIntelDocuments from "./ExamIntelDocuments";
import {
  COVERAGE_DEPTH_LABELS,
  COVERAGE_DEPTH_GROUP_LABEL,
  COVERAGE_DEPTH_HELPER,
  PRIORITY_BANDS_GROUP_LABEL,
  PRIORITY_BANDS_HELPER,
  band,
  BUSINESS_PRIORITY_LABELS,
  REVIEWER_STATUS_LABELS,
  IS_HIGH_YIELD_LABEL,
  IS_HIGH_YIELD_HELPER,
  IS_ACTIVE_LABEL,
  IS_ACTIVE_HELPER,
  LifecycleLegend,
} from "../../../features/admin/exam-intelligence/ExamIntelGlossary";
import { humanizeToken } from "../../../features/admin/exam-intelligence/operatorChrome";

/**
 * Operator-safe cell value for CMS table columns.
 *
 * Applies humanizeToken (which truncates UUID-shaped strings to first 8 chars +
 * "…") so that raw UUIDs never appear verbatim in the table.  Non-UUID values
 * (slugs, names, statuses) are passed through unchanged, capped at 60 chars,
 * so existing display copy is preserved without unintended capitalisation.
 *
 * - null/undefined → "—"
 * - boolean        → "true" / "false"
 * - UUID string    → humanizeToken(value)  e.g. "550e8400…"
 * - Other string   → value.slice(0, 60)
 */
function renderCellValue(value) {
  if (value == null) return "—";
  if (typeof value === "boolean") return String(value);
  const s = String(value);
  const humanized = humanizeToken(s);
  // humanizeToken truncates UUID-shaped values to "${first8}…".
  // For non-UUID strings it would capitalise and replace underscores — we do
  // NOT want that for slug/name/status columns. Use humanized only when it
  // ends with "…", which is the UUID-truncation signal.
  if (humanized.endsWith("…")) return humanized;
  return s.slice(0, 60);
}

function OrgRefSelect({ value, onChange, testId }) {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    api.get("/api/admin/organizations?limit=200")
      .then((d) => { if (active) setOrgs(Array.isArray(d?.items) ? d.items : []); })
      .catch(() => {})
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  return (
    <select
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
      data-testid={testId}
    >
      <option value="">(none)</option>
      {loading && <option disabled>Loading…</option>}
      {orgs.map((o) => (
        <option key={o.id} value={o.id}>
          {o.name}{o.state ? ` — ${o.state}` : ""}{o.type ? ` (${o.type})` : ""}
        </option>
      ))}
    </select>
  );
}

/**
 * Source registry picker with official-only default and toggle.
 * Fetches /source-registry?include_discovery=false by default.
 * Toggle "Show discovery/aggregator sources" switches to include_discovery=true.
 */
function SourceRegistryRefField({ value, onChange, testId }) {
  const [includeDiscovery, setIncludeDiscovery] = useState(false);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const result = api.get(`/api/admin/exam-intelligence-cms/source-registry?include_discovery=${includeDiscovery}&limit=200`);
    if (result && typeof result.then === "function") {
      result
        .then((d) => { if (active) setSources(Array.isArray(d?.items) ? d.items : []); })
        .catch(() => {})
        .finally(() => { if (active) setLoading(false); });
    } else {
      setLoading(false);
    }
    return () => { active = false; };
  }, [includeDiscovery]);

  return (
    <div>
      <select
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
        data-testid={testId}
      >
        <option value="">(none)</option>
        {loading && <option disabled>Loading…</option>}
        {sources.map((s) => (
          <option key={s.id} value={s.id}>
            {s.source_name}{s.source_type ? ` (${s.source_type})` : ""}
          </option>
        ))}
      </select>
      <label style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 4, fontSize: 11, color: "var(--ink-mute)" }}>
        <input
          type="checkbox"
          checked={includeDiscovery}
          onChange={(e) => setIncludeDiscovery(e.target.checked)}
          data-testid={testId ? `${testId}-toggle` : undefined}
        />
        Show discovery/aggregator sources
      </label>
    </div>
  );
}

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
const refSection = (filters) => ({ endpoint: "exam-phase-sections", labelKey: "section_label", secondaryKey: "subject_id", filters });

// exams.cadence CHECK constraint (migration 172, widened by migration 237 to
// add 'biannual' for exams that run twice a year).
const EXAM_CADENCES = ["annual", "biannual", "recurring", "irregular", "one_off", "unknown"];
const EXAM_TYPES = ["recruitment", "entrance", "certification", "opportunity", "other"];
const EXAM_MGMT_MODES = ["core", "light", "index_only", "archive"];

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
const PYQ_QUESTION_TYPES = ["mcq", "numerical", "descriptive", "caselet", "matching", "other"];
// observed_difficulty + option_label have no DB CHECK (migration 032) — these
// are UI conveniences, not enforced enums.
const PYQ_OBSERVED_DIFFICULTY = ["easy", "moderate", "hard"];
const PYQ_OPTION_LABELS = ["A", "B", "C", "D", "E"];
const COMPETITION_SOURCE_BASES = ["manual", "official", "reviewed_analysis", "derived", "model_generated"];
// exam_policy_updates.claim_status CHECK (migration 056).
const POLICY_CLAIM_STATUSES = ["unverified", "official_confirmed", "superseded"];

// Entities whose list endpoint accepts exam_id as a query param.
// Source of truth: admin_exam_intel_cms.py GET route signatures (verified).
const ENTITY_EXAM_SCOPE = new Set([
  "exam-cycles",
  "exam-phases",
  "syllabus-documents",
  "pyq-papers",
  "exam-topic-coverage",
  "policy-updates",
  "exam-competition-metrics",
  "pyq-sources",
  "syllabus-topic-mentions",
]);

// Entities whose list endpoint also accepts exam_cycle_id (the DB column name).
// Only two endpoints support this in the current backend.
const ENTITY_CYCLE_SCOPE = new Set([
  "exam-phases",
  "pyq-papers",
]);

// M4: entities whose list endpoint accepts exam_family_id as a query param.
// subjects has no direct exam_family_id column — the backend resolves it via
// the exam_topic_coverage -> topics -> subject_id path (see
// admin_exam_intel_cms._subject_ids_for_exam_family). This is separate from
// ENTITY_EXAM_SCOPE (which drives off the URL exam_id/cycle_id scope params);
// the family filter below is an independent, entity-local control.
const ENTITY_FAMILY_SCOPE = new Set(["subjects"]);

// J1: per-entity status filter config — options derived from DB CHECK constraints.
// See migrations 030/031/032/056; coverage uses COVERAGE_REVIEWER_STATUSES (migration 030).
const ENTITY_STATUS_CONFIG = {
  "syllabus-topic-mentions": { param: "reviewer_status", label: "Reviewer status", options: ["pending", "verified", "rejected", "needs_correction"] },
  "exam-topic-coverage":     { param: "reviewer_status", label: "Reviewer status", options: COVERAGE_REVIEWER_STATUSES },
  "policy-updates":          { param: "reviewer_status", label: "Reviewer status", options: ["pending", "verified", "rejected", "needs_correction"] },
  "pyq-questions":           { param: "reviewer_status", label: "Reviewer status", options: ["pending", "verified", "rejected", "needs_correction"] },
  "syllabus-documents":      { param: "trust_status",    label: "Trust status",    options: ["pending", "verified", "rejected", "superseded"] },
  "pyq-papers":              { param: "trust_status",    label: "Trust status",    options: ["pending", "verified", "rejected"] },
  "pyq-sources":             { param: "trust_status",    label: "Trust status",    options: ["pending", "verified", "rejected"] },
};

// Additional per-entity filters beyond search/status/family. Options may be
// plain strings (value === label) or {value, label} pairs. Each param must
// have matching query-param support on the corresponding GET list endpoint
// in admin_exam_intel_cms.py.
const ACTIVE_OPTIONS = [{ value: "true", label: "Active" }, { value: "false", label: "Retired" }];
const ENTITY_EXTRA_FILTERS = {
  exams: [
    { param: "is_active", label: "Active", options: ACTIVE_OPTIONS },
    { param: "exam_type", label: "Exam type", options: EXAM_TYPES },
    { param: "management_mode", label: "Business priority", options: EXAM_MGMT_MODES },
    { param: "cadence", label: "Cadence", options: EXAM_CADENCES },
  ],
  "exam-families": [
    { param: "is_active", label: "Active", options: ACTIVE_OPTIONS },
  ],
  subjects: [
    { param: "is_active", label: "Active", options: ACTIVE_OPTIONS },
  ],
  topics: [
    { param: "is_active", label: "Active", options: ACTIVE_OPTIONS },
    { param: "level", label: "Level", options: TOPIC_LEVELS },
  ],
};

// J1: entities that support backend text-search, keyed to the param name.
// Only these 4 entities expose a `q` param; all others ignore unknown params.
const ENTITY_SEARCH_PARAM = {
  "syllabus-topic-mentions": "q",
  "exam-phase-sections":     "q",
  "subjects":                "q",
  "topics":                  "q",
};

// J1: entities whose list endpoint has no `offset` support.
// (pyq-options now supports offset via .range() — backend amended in PR #820.)
const ENTITY_NO_OFFSET = new Set();

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
      { key: "name", label: "name", required: true },
      { key: "conducting_organization_id", label: "conducting_organization_id (org)", type: "org-ref" },
      { key: "exam_family_id", label: "exam_family_id", type: "ref", ref: REF_FAMILY },
      { key: "exam_type", label: "exam_type (recruitment|entrance|certification|opportunity|other)" },
      { key: "management_mode", label: "Business priority", rawName: "management_mode", type: "enum", options: ["core", "light", "index_only", "archive"], defaultValue: "light",
        optionLabels: { core: BUSINESS_PRIORITY_LABELS.core.label, light: BUSINESS_PRIORITY_LABELS.light.label, index_only: BUSINESS_PRIORITY_LABELS.index_only.label, archive: BUSINESS_PRIORITY_LABELS.archive.label } },
      { key: "cadence", label: "cadence", type: "enum", options: EXAM_CADENCES, defaultValue: "unknown",
        optionLabels: { biannual: "biannual (twice a year)" } },
      { key: "description", label: "description" },
      { key: "is_active", label: IS_ACTIVE_LABEL, rawName: "is_active", type: "bool", helperText: IS_ACTIVE_HELPER },
    ],
    columns: ["slug", "name", "exam_type", "management_mode", "is_active", "created_at"],
  },
  "exam-cycles": {
    label: "Exam cycles",
    fields: [
      { key: "exam_id", label: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "year", label: "year", required: true, type: "int" },
      { key: "cycle_name", label: "cycle_name", required: true },
      { key: "status", label: "status (expected|open|active|closed|completed|cancelled)" },
      { key: "notification_date", label: "notification_date (dd-mm-yyyy)", type: "date", mode: "any" },
      { key: "application_start", label: "application_start (dd-mm-yyyy)", type: "date", mode: "future" },
      { key: "application_end", label: "application_end (dd-mm-yyyy)", type: "date", mode: "future" },
      { key: "exam_start", label: "exam_start (dd-mm-yyyy)", type: "date", mode: "future" },
      { key: "exam_end", label: "exam_end (dd-mm-yyyy)", type: "date", mode: "future" },
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
      { key: "phase_start", label: "phase_start (dd-mm-yyyy)", type: "date", mode: "any" },
      { key: "phase_end",   label: "phase_end (dd-mm-yyyy)",   type: "date", mode: "any" },
    ],
    columns: ["exam_id", "phase_name", "phase_order", "status", "phase_start"],
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
      { key: "source_id", label: "source_id (source_registry)", type: "source-registry-ref" },
      { key: "published_at", label: "published_at (dd-mm-yyyy)", type: "date", mode: "any" },
      { key: "fetched_at", label: "fetched_at (dd-mm-yyyy)", type: "date", mode: "any" },
      { key: "content_hash", label: "content_hash (auto-computed by extraction)", type: "readonly" },
      { key: "metadata", label: "metadata (JSON object)", type: "json" },
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
      { key: "paper_date", label: "paper_date (dd-mm-yyyy)", type: "date", mode: "past" },
      { key: "shift", label: "shift" },
      { key: "paper_code", label: "paper_code" },
      { key: "source_url", label: "source_url" },
      { key: "source_type", label: "source_type (official|memory_based|coaching|community|aggregator|unknown)" },
      { key: "exam_cycle_id", label: "exam_cycle_id", type: "ref", ref: refCycle({ exam_id: "exam_id" }) },
      { key: "content_hash", label: "content_hash (auto-computed by extraction)", type: "readonly" },
      { key: "metadata", label: "metadata (JSON object)", type: "json" },
    ],
    columns: ["year", "paper_code", "source_type", "trust_status"],
  },
  "exam-topic-coverage": {
    label: "Exam topic coverage",
    fields: [
      { key: "exam_id", label: "Exam", rawName: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "topic_id", label: "Topic", rawName: "topic_id", required: true, type: "ref", ref: refTopic({}) },
      { key: "exam_cycle_id", label: "exam_cycle_id", type: "ref", ref: refCycle({ exam_id: "exam_id" }) },
      { key: "exam_phase_id", label: "exam_phase_id", type: "ref", ref: refPhase({ exam_id: "exam_id", exam_cycle_id: "exam_cycle_id" }) },
      { key: "section_id", label: "section_id (cascades from phase)", type: "ref", ref: refSection({ exam_phase_id: "exam_phase_id" }) },
      { key: "coverage_depth", label: COVERAGE_DEPTH_GROUP_LABEL, rawName: "coverage_depth", type: "enum", options: COVERAGE_DEPTHS,
        optionLabels: COVERAGE_DEPTH_LABELS, helperText: COVERAGE_DEPTH_HELPER },
      { key: "expected_difficulty", label: "expected_difficulty" },
      { key: "exam_priority_score", label: PRIORITY_BANDS_GROUP_LABEL, rawName: "exam_priority_score", type: "number", step: 0.01, min: 0, max: 100,
        showBand: true, helperText: PRIORITY_BANDS_HELPER },
      { key: "is_high_yield", label: IS_HIGH_YIELD_LABEL, rawName: "is_high_yield", type: "bool", helperText: IS_HIGH_YIELD_HELPER },
      { key: "confidence_score", label: "confidence_score (0–1)", type: "number", step: 0.001, min: 0, max: 1 },
      { key: "source_basis", label: "source_basis", type: "enum", options: COVERAGE_SOURCE_BASES },
      { key: "reviewer_status", label: "Review status", rawName: "reviewer_status", type: "enum", options: COVERAGE_REVIEWER_STATUSES,
        optionLabels: Object.fromEntries(Object.entries(REVIEWER_STATUS_LABELS).map(([k, v]) => [k, v.label])) },
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
      { key: "exam_cycle_id", label: "exam_cycle_id", type: "ref", ref: refCycle({ exam_id: "exam_id" }) },
      { key: "source_id", label: "source_id (source_registry)", type: "source-registry-ref" },
      { key: "claim_status", label: "claim_status", type: "enum", options: POLICY_CLAIM_STATUSES },
      // affects_* may only be true on official sources (DB CHECK + backend guard).
      { key: "affects_plan", label: "affects_plan", type: "bool" },
      { key: "affects_deadline", label: "affects_deadline", type: "bool" },
      { key: "affects_eligibility", label: "affects_eligibility", type: "bool" },
      { key: "affects_documents", label: "affects_documents", type: "bool" },
      { key: "affects_syllabus", label: "affects_syllabus", type: "bool" },
      { key: "affects_vacancy", label: "affects_vacancy", type: "bool" },
      { key: "change_summary", label: "change_summary (JSON object)", type: "json" },
      { key: "evidence", label: "evidence (JSON object)", type: "json" },
      { key: "published_at", label: "published_at (dd-mm-yyyy)", type: "date", mode: "any" },
      { key: "effective_from", label: "effective_from (dd-mm-yyyy)", type: "date", mode: "any" },
    ],
    columns: ["title", "update_type", "reviewer_status", "source_type"],
  },
  subjects: {
    label: "Subjects",
    // M4: subject_id (the row's own UUID) is included in the table columns so operators can
    // reference it when setting up topic scoping fields. renderCellValue truncates UUIDs via
    // humanizeToken — raw UUIDs never appear verbatim. The "Exam family" filter (rendered
    // whenever ENTITY_FAMILY_SCOPE has this entity) scopes the list to subjects reachable
    // from the selected family's exams via exam_topic_coverage -> topics -> subject_id
    // (subjects has no direct exam_family_id column — see
    // admin_exam_intel_cms._subject_ids_for_exam_family).
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
      { key: "source_id", label: "source_id (source_registry)", type: "source-registry-ref" },
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
  "pyq-questions": {
    label: "PYQ questions",
    notice: "Lands as pending — verify in /admin/exam-intelligence review.",
    fields: [
      { key: "exam_id", label: "exam_id (scope only — not saved)", type: "ref", ref: REF_EXAM, uiOnly: true },
      { key: "pyq_paper_id", label: "pyq_paper_id", required: true, type: "ref", ref: refPaper({ exam_id: "exam_id" }) },
      { key: "question_number", label: "question_number", type: "int" },
      { key: "question_text", label: "question_text", required: true },
      { key: "question_type", label: "question_type", type: "enum", options: PYQ_QUESTION_TYPES },
      { key: "observed_difficulty", label: "observed_difficulty", type: "enum", options: PYQ_OBSERVED_DIFFICULTY },
      { key: "expected_solve_time_sec", label: "expected_solve_time_sec", type: "int" },
      { key: "explanation_text", label: "explanation_text", type: "textarea" },
      { key: "language", label: "language" },
      { key: "normalized_question_hash", label: "normalized_question_hash (auto-computed from text)", type: "readonly" },
      { key: "metadata", label: "metadata (JSON object)", type: "json" },
    ],
    columns: ["pyq_paper_id", "question_number", "question_type", "reviewer_status"],
  },
  "pyq-options": {
    label: "PYQ options",
    fields: [
      { key: "exam_id", label: "exam_id (scope only — not saved)", type: "ref", ref: REF_EXAM, uiOnly: true },
      { key: "pyq_paper_id", label: "pyq_paper_id (scope only — not saved)", type: "ref", ref: refPaper({ exam_id: "exam_id" }), uiOnly: true },
      { key: "question_id", label: "question_id", required: true, type: "ref", ref: refQuestion({ pyq_paper_id: "pyq_paper_id" }) },
      { key: "option_label", label: "option_label", type: "enum", options: PYQ_OPTION_LABELS },
      { key: "option_text", label: "option_text" },
      { key: "is_correct", label: "is_correct", type: "bool" },
      { key: "metadata", label: "metadata (JSON object)", type: "json" },
    ],
    columns: ["question_id", "option_label", "is_correct"],
  },
  "exam-phase-sections": {
    label: "Exam phase sections",
    fields: [
      { key: "exam_id", label: "exam_id (scope only — not saved)", type: "ref", ref: REF_EXAM, uiOnly: true },
      { key: "exam_phase_id", label: "exam_phase_id", required: true, type: "ref", ref: refPhase({ exam_id: "exam_id" }) },
      { key: "subject_id", label: "subject_id", required: true, type: "ref", ref: REF_SUBJECT },
      { key: "section_label", label: "section_label", required: true },
      { key: "question_count", label: "question_count", type: "int" },
      { key: "marks", label: "marks", type: "number", step: 0.5, min: 0 },
      { key: "duration_mins", label: "duration_mins", type: "int" },
      { key: "negative_marking", label: "negative_marking" },
      { key: "difficulty_level", label: "difficulty_level" },
      { key: "weightage_percent", label: "weightage_percent", type: "number", step: 0.1, min: 0, max: 100 },
      { key: "sort_order", label: "sort_order", type: "int" },
      { key: "metadata", label: "metadata (JSON object)", type: "json" },
    ],
    columns: ["exam_phase_id", "section_label", "subject_id", "question_count", "marks"],
  },
  "exam-competition-metrics": {
    label: "Exam competition metrics",
    notice: "Lands as draft — promote in /admin/exam-intelligence review.",
    fields: [
      { key: "exam_id", label: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "exam_cycle_id", label: "exam_cycle_id", type: "ref", ref: refCycle({ exam_id: "exam_id" }) },
      { key: "exam_phase_id", label: "exam_phase_id", type: "ref", ref: refPhase({ exam_id: "exam_id" }) },
      { key: "vacancy_total", label: "vacancy_total", type: "int" },
      { key: "applicant_count", label: "applicant_count", type: "int" },
      { key: "selection_ratio", label: "selection_ratio (0–1)", type: "number", step: 0.000001, min: 0, max: 1 },
      { key: "competition_pressure_score", label: "competition_pressure_score (0–100)", type: "number", step: 0.01, min: 0, max: 100 },
      { key: "source_basis", label: "source_basis", type: "enum", options: COMPETITION_SOURCE_BASES },
      { key: "confidence_score", label: "confidence_score (0–1)", type: "number", step: 0.001, min: 0, max: 1 },
      { key: "evidence_count", label: "evidence_count", type: "int" },
      { key: "metadata", label: "metadata (JSON object)", type: "json" },
    ],
    columns: ["exam_id", "vacancy_total", "applicant_count", "reviewer_status", "created_at"],
  },
};

const ENTITY_KEYS = Object.keys(ENTITY_CONFIG);

// Entities that expose a full PATCH route in admin_exam_intel_cms.py and so
// can be edited from the UI. Everything else stays create-only (lifecycle
// rows go through the review queue, not here).
const EDITABLE_ENTITIES = new Set([
  "exam-families", "exams", "exam-cycles", "exam-phases",
  // Taxonomy — non-reviewable, backend update routes exist (admin_exam_intel_cms.py:1557,1673,2195).
  "subjects", "topics",
  // pyq-sources has a PATCH route but trust_status is pipeline-owned; edit form excludes it.
  "pyq-sources",
]);
// Only these two have a DELETE (soft-delete → is_active=false) route.
const DEACTIVATABLE_ENTITIES = new Set(["exam-families", "exams"]);

// Per-entity columns that are nullable in Postgres AND surfaced in cfg.fields,
// so clearing them on edit may legitimately submit null. Any other field
// cleared to empty is blocked (the column is NOT NULL — e.g. slug/name/exam_id/
// year/cycle_name/phase_name/phase_slug, or a defaulted enum/bool like
// status/is_active/phase_order). Source: docs/schema/supabase-current.md.
const NULLABLE_ON_EDIT = {
  "exam-families": new Set(["description"]),
  exams: new Set(["exam_family_id", "exam_type", "management_mode", "cadence", "description"]),
  "exam-cycles": new Set([
    "notification_date", "application_start", "application_end",
    "exam_start", "exam_end", "source_url",
  ]),
  "exam-phases": new Set([
    "exam_cycle_id", "mode", "duration_mins", "total_questions", "total_marks",
  ]),
  // Taxonomy nullable columns (migration 029).
  subjects: new Set(["subject_group", "default_difficulty_level", "description"]),
  topics: new Set(["parent_topic_id", "default_difficulty_level", "description"]),
  // pyq_sources nullable columns (migration 032); exam_id is required.
  "pyq-sources": new Set(["source_id", "source_type", "source_url", "title", "metadata"]),
};

// Fields present in ENTITY_CONFIG but excluded from the edit form because
// the backend owns them (pipeline-managed) and direct mutation is unsafe.
// These fields are still shown in the create form (backend overrides them
// on insert); the edit path skips them entirely.
const EDIT_EXCLUDED_FIELDS = {
  // slug is the bulk-import upsert key for subjects (upsert_on="slug" in
  // _IMPORT_CONFIG). Editing it would turn a re-import into a duplicate insert
  // instead of an idempotent update, and breaks any slug-keyed references.
  subjects: new Set(["slug"]),
  // slug is part of the compound upsert key for topics
  // (upsert_on="subject_id,parent_topic_id,slug"). Same risk as subjects.
  // level/subject_id/parent_topic_id stay editable for legitimate re-parenting.
  topics: new Set(["slug"]),
  // trust_status is pipeline-owned (forced to 'pending' on create, promoted
  // only by the trust pipeline — not via CMS edit).
  // source_id is the external dedup key — same risk class as slug.
  // exam_id stays editable for re-filing a mis-imported source to the right exam.
  "pyq-sources": new Set(["trust_status", "source_id"]),
};

// Fields excluded from the *bulk* edit field picker on top of
// EDIT_EXCLUDED_FIELDS above. name/cycle_name/phase_name/slug are
// identity-ish columns — setting the same value across a whole selected
// batch is never the intent of a bulk edit, and for the unique/compound-key
// ones (slug, cycle_name, phase_name) it would just fail past the first row.
// Mirrors the backend's _BULK_EDIT_CONFIG allowed-field sets exactly.
const BULK_EDIT_EXCLUDED_FIELDS = {
  "exam-families": new Set(["slug", "name"]),
  exams: new Set(["name"]),
  "exam-cycles": new Set(["exam_id", "cycle_name"]),
  "exam-phases": new Set(["exam_id", "phase_name", "phase_slug"]),
  subjects: new Set(["slug", "name"]),
  topics: new Set(["slug", "name"]),
};

function bulkEditableFields(entityKey, cfg) {
  const editExcluded = EDIT_EXCLUDED_FIELDS[entityKey] || new Set();
  const bulkExcluded = BULK_EDIT_EXCLUDED_FIELDS[entityKey] || new Set();
  return cfg.fields.filter(
    (f) => !f.uiOnly && f.type !== "readonly" && !editExcluded.has(f.key) && !bulkExcluded.has(f.key),
  );
}

// Helper copy shown under specific date fields. exam_start is the Study OS
// timeline anchor (see StudyPlan/timeline), so flag it in both create + edit.
const DATE_FIELD_HELP = {
  "exam-cycles": {
    exam_start:
      "Study OS timeline uses exam_start as the current cycle anchor. Keep it future-facing for active cycles.",
  },
};

// Single rendering path for one form control, shared by the create and edit
// forms so they never drift. ``idPrefix`` keeps their test ids distinct
// ("cms-" for create, "cms-edit-" for edit). ``values`` is the whole form bag
// so ref pickers can cascade off sibling fields.
function renderFieldControl(f, values, setValues, idPrefix, entityKey) {
  const testId = `${idPrefix}field-${f.key}`;
  const set = (val) => setValues((p) => ({ ...p, [f.key]: val }));
  if (f.type === "org-ref") {
    return <OrgRefSelect value={values[f.key] ?? ""} onChange={(val) => set(val)} testId={testId} />;
  }
  if (f.type === "source-registry-ref") {
    return <SourceRegistryRefField value={values[f.key] ?? ""} onChange={(val) => set(val)} testId={testId} />;
  }
  if (f.type === "ref") {
    return (
      <CmsRefField
        field={f}
        value={values[f.key] ?? ""}
        formValues={values}
        onChange={(val) => set(val)}
        testId={testId}
      />
    );
  }
  if (f.type === "bool") {
    return (
      <select
        value={values[f.key] ?? ""}
        onChange={(e) => set(e.target.value)}
        className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
        data-testid={testId}
      >
        <option value="">(skip)</option>
        <option value="true">true</option>
        <option value="false">false</option>
      </select>
    );
  }
  if (f.type === "enum") {
    return (
      <select
        value={values[f.key] ?? f.defaultValue ?? ""}
        onChange={(e) => set(e.target.value)}
        className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
        data-testid={testId}
      >
        <option value="">(skip)</option>
        {f.options.map((o) => (
          <option key={o} value={o}>{f.optionLabels?.[o] ?? o}</option>
        ))}
      </select>
    );
  }
  if (f.type === "date") {
    return (
      <div data-testid={testId}>
        <DateField
          value={values[f.key] ?? null}
          onChange={(iso) => set(iso)}
          mode={f.mode || "any"}
          name={f.key}
          id={`${idPrefix}date-${f.key}`}
          helpText={DATE_FIELD_HELP[entityKey]?.[f.key]}
        />
      </div>
    );
  }
  if (f.type === "json") {
    return (
      <textarea
        value={values[f.key] ?? ""}
        onChange={(e) => set(e.target.value)}
        rows={3}
        placeholder="{}"
        className="w-full px-2 py-1.5 text-sm font-mono border border-border/60 rounded bg-background"
        data-testid={testId}
      />
    );
  }
  if (f.type === "textarea") {
    return (
      <textarea
        value={values[f.key] ?? ""}
        onChange={(e) => set(e.target.value)}
        rows={3}
        className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
        data-testid={testId}
      />
    );
  }
  if (f.type === "readonly") {
    // Auto-computed columns (e.g. content hashes). Shown for visibility but
    // never submitted — the backend derives them.
    return (
      <input
        type="text"
        readOnly
        disabled
        value=""
        placeholder="auto-computed"
        className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-muted text-muted-foreground"
        data-testid={testId}
      />
    );
  }
  return (
    <input
      type={f.type === "int" || f.type === "number" ? "number" : "text"}
      step={f.type === "number" ? f.step : undefined}
      min={f.min}
      max={f.max}
      value={values[f.key] ?? ""}
      onChange={(e) => set(e.target.value)}
      className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
      data-testid={testId}
    />
  );
}

// Renders sub-text beneath a relabeled field: raw column name in monospace,
// optional static helper, and dynamic priority band for numeric score fields.
function renderFieldAnnotation(f, values) {
  return (
    <>
      {f.rawName && (
        <span className="text-xs font-mono text-muted-foreground">{f.rawName}</span>
      )}
      {f.helperText && (
        <p className="text-xs text-muted-foreground mt-0.5">{f.helperText}</p>
      )}
      {f.showBand && values[f.key] !== undefined && values[f.key] !== "" && (
        <p className="text-xs text-muted-foreground mt-0.5">
          Band: <strong>{band(values[f.key]).label}</strong>
        </p>
      )}
    </>
  );
}

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
  const { user, status: authStatus } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const scopeExamId = searchParams.get("exam_id") ?? null;
  const scopeCycleId = searchParams.get("cycle_id") ?? null;

  const hasCmsPermission =
    user?.role === "super_admin" ||
    user?.permissions?.includes("exam_intelligence.cms");

  const isAuthorized = hasCmsPermission;

  const [entity, setEntity] = useState(() => {
    const e = searchParams.get("entity");
    return e && (ENTITY_KEYS.includes(e) || e === "documents") ? e : "exam-families";
  });
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
  // Edit state. ``editingRow`` is the original row (also the diff baseline);
  // ``editValues`` is the prefilled, mutable form bag.
  const [editingRow, setEditingRow] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [editReason, setEditReason] = useState("");
  const [editError, setEditError] = useState(null);
  // Retire dialog
  const [retireTarget, setRetireTarget] = useState(null); // { row, label } | null
  const [retireReason, setRetireReason] = useState("");
  const [retireError, setRetireError] = useState(null);

  const loadGenRef = useRef(0);

  const { run: runCreate, busy: busyCreate } = useApiAction();
  const { run: runBulk, busy: busyBulk } = useApiAction();
  const { run: runEdit, busy: busyEdit } = useApiAction();
  const { run: runRetire, busy: busyRetire } = useApiAction();

  // J1: search / filter / pagination state
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  // M4: exam-family filter, entity-local (only ENTITY_FAMILY_SCOPE entities use it).
  const [familyFilter, setFamilyFilter] = useState("");
  const [examFamilies, setExamFamilies] = useState([]);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [scopeExamName, setScopeExamName] = useState(null);
  const [scopeCycleName, setScopeCycleName] = useState(null);
  // "idle" = no scope param; "resolving" = lookup in flight; "valid" = found; "error" = not found
  const [examScopeState, setExamScopeState] = useState("idle");
  const [cycleScopeState, setCycleScopeState] = useState("idle");
  // resolvedExamId/resolvedCycleId track WHICH ID was successfully resolved.
  // writesBlocked also checks these match current URL params to close the
  // initial-render gap and the valid-A → resolving-B scope-change gap.
  const [resolvedExamId, setResolvedExamId] = useState(null);
  const [resolvedCycleId, setResolvedCycleId] = useState(null);
  // Additional per-entity filters (exam_type, management_mode, cadence,
  // is_active, level, ...) keyed by query param — see ENTITY_EXTRA_FILTERS.
  const [extraFilters, setExtraFilters] = useState({});
  // exams-only organization filter. Fetched lazily (same list the org-ref
  // picker already uses) rather than folded into ENTITY_EXTRA_FILTERS since
  // it needs its own async option list instead of a static enum.
  const [orgOptions, setOrgOptions] = useState([]);
  const searchTimerRef = useRef(null);
  const PAGE_SIZE = 50;

  // Bulk select / bulk action state (row checkboxes, "select all matching
  // filter", and the bulk edit / bulk retire panels below the table).
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [selectAllBusy, setSelectAllBusy] = useState(false);
  const [showBulkEdit, setShowBulkEdit] = useState(false);
  const [bulkEditField, setBulkEditField] = useState("");
  const [bulkEditValues, setBulkEditValues] = useState({});
  const [bulkEditReason, setBulkEditReason] = useState("");
  const [bulkEditError, setBulkEditError] = useState(null);
  const [bulkActionResult, setBulkActionResult] = useState(null);
  const [bulkRetireOpen, setBulkRetireOpen] = useState(false);
  const [bulkRetireReason, setBulkRetireReason] = useState("");
  const [bulkRetireError, setBulkRetireError] = useState(null);
  const { run: runBulkUpdate, busy: busyBulkUpdate } = useApiAction();
  const { run: runBulkDeactivate, busy: busyBulkDeactivate } = useApiAction();

  const isDocuments = entity === "documents";
  const cfg = ENTITY_CONFIG[entity];
  const isEditable = EDITABLE_ENTITIES.has(entity);
  const isDeactivatable = DEACTIVATABLE_ENTITIES.has(entity);
  // Same entity set the backend's /bulk-update and /bulk-deactivate accept —
  // see _BULK_EDIT_CONFIG / _BULK_DEACTIVATABLE_TABLES in admin_exam_intel_cms.py.
  const supportsBulkSelect = isEditable;
  // Per-entity bulk caps — source of truth is the backend. UI copy only; the
  // backend enforces. Submit is never blocked client-side.
  const bulkCap = { "pyq-questions": 2000, "pyq-options": 4000, "pyq-question-topic-tags": 2000 }[entity] || 500;
  // Fail-closed: block when no scope, scope is resolving, scope errored, OR
  // resolved identity does not yet match the current URL param (covers first
  // render and valid-A → resolving-B transitions).
  const scopeResolutionFailed =
    (scopeExamId && examScopeState === "error") ||
    (scopeCycleId && scopeExamId && cycleScopeState === "error");
  const writesBlocked =
    (scopeExamId && (examScopeState !== "valid" || resolvedExamId !== scopeExamId)) ||
    (scopeExamId && scopeCycleId && (cycleScopeState !== "valid" || resolvedCycleId !== scopeCycleId));

  async function load({ searchVal, filterVal, pageVal, familyVal, extraVal } = {}) {
    const gen = ++loadGenRef.current;
    if (!isAuthorized) return;
    // The Documents panel manages its own data via the upload/list endpoints.
    if (isDocuments) {
      setItems(null);
      setBusy(false);
      return;
    }
    setBusy(true);
    setErr(null);
    // F5: clear rows immediately so stale rows are not actionable during transitions
    setItems(null);
    // A fresh load always invalidates any in-flight row selection — the ids
    // it referred to may no longer be on the loaded page/result set.
    setSelectedIds(new Set());
    const effectiveSearch = searchVal !== undefined ? searchVal : search;
    const effectiveFilter = filterVal !== undefined ? filterVal : statusFilter;
    const effectivePage = pageVal !== undefined ? pageVal : page;
    const effectiveFamily = familyVal !== undefined ? familyVal : familyFilter;
    const effectiveExtra = extraVal !== undefined ? extraVal : extraFilters;
    const noOffset = ENTITY_NO_OFFSET.has(entity);
    const offset = noOffset ? 0 : (effectivePage - 1) * PAGE_SIZE;
    try {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
      // F3: only send offset for entities whose backend supports it
      if (!noOffset) params.set("offset", String(offset));
      if (scopeExamId && ENTITY_EXAM_SCOPE.has(entity)) {
        params.set("exam_id", scopeExamId);
      }
      // Per B.3: cycle_id without exam_id is ignored
      if (scopeExamId && scopeCycleId && ENTITY_CYCLE_SCOPE.has(entity)) {
        params.set("exam_cycle_id", scopeCycleId);
      }
      // F2: send search only for entities with documented backend support, using correct param
      const searchParam = ENTITY_SEARCH_PARAM[entity];
      if (effectiveSearch && searchParam) {
        params.set(searchParam, effectiveSearch);
      }
      const statusCfg = ENTITY_STATUS_CONFIG[entity];
      if (effectiveFilter && statusCfg) {
        params.set(statusCfg.param, effectiveFilter);
      }
      // M4: exam-family filter, independent of the URL exam/cycle scope.
      if (effectiveFamily && ENTITY_FAMILY_SCOPE.has(entity)) {
        params.set("exam_family_id", effectiveFamily);
      }
      // Extra per-entity filters (exam_type, management_mode, cadence, is_active, level, ...).
      for (const fc of ENTITY_EXTRA_FILTERS[entity] || []) {
        const v = effectiveExtra[fc.param];
        if (v !== undefined && v !== "") params.set(fc.param, v);
      }
      // exams-only organization filter.
      if (entity === "exams" && effectiveExtra.conducting_organization_id) {
        params.set("conducting_organization_id", effectiveExtra.conducting_organization_id);
      }
      const r = await api.get(`/api/admin/exam-intelligence-cms/${entity}?${params}`);
      if (gen !== loadGenRef.current) return;
      setItems(r);
      // F6: track hasMore: full page without total → may have more; short page → done
      const items = r?.items || [];
      if (r?.total != null) {
        setTotalCount(r.total);
        setHasMore(offset + items.length < r.total);
      } else {
        setTotalCount(null);
        setHasMore(!noOffset && items.length === PAGE_SIZE);
      }
    } catch (e) {
      if (gen !== loadGenRef.current) return;
      setErr(getApiErrorMessage(e));
      setItems(null);
    } finally {
      if (gen === loadGenRef.current) setBusy(false);
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
    if (writesBlocked) { setStatus({ ok: false, message: "Write blocked: scope is unresolved or invalid." }); return; }
    setBulkResult(null);
    if (bulkReason.trim().length < 8) {
      setStatus({ ok: false, message: "Bulk reason must be ≥8 chars." });
      return;
    }
    let rows;
    try {
      rows = JSON.parse(bulkRows);
      if (!Array.isArray(rows)) throw new Error("Top-level JSON must be an array");
    } catch (ex) {
      setStatus({ ok: false, message: `Could not parse rows JSON: ${ex.message}` });
      return;
    }
    await runBulk({
      action: () =>
        api.post("/api/admin/exam-intelligence-cms/bulk-import", {
          reason: bulkReason.trim(),
          entity,
          rows,
        }),
      onSuccess: (r) => {
        setBulkResult(r);
        setStatus({
          ok: r.ok,
          message: `Bulk import: ${r.ok_count}/${r.total} ok, ${r.error_count} errors. audit_id=${r.audit_id}`,
        });
        load();
      },
      errorMessage: "Bulk import failed.",
    });
  }

  async function submitCreate(e) {
    e.preventDefault();
    if (writesBlocked) { setStatus({ ok: false, message: "Write blocked: scope is unresolved or invalid." }); return; }
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
    await runCreate({
      action: () =>
        api.post(`/api/admin/exam-intelligence-cms/${entity}`, {
          reason: reason.trim(),
          payload,
        }),
      onSuccess: (r) => {
        setStatus({ ok: true, message: `Created. audit_id=${r.audit_id}` });
        setShowCreate(false);
        setFormValues({});
        setReason("");
        load();
      },
      errorMessage: "Create failed.",
    });
  }

  function startEdit(row) {
    // Prefill every field in the form's shape from the row. Dates stay as the
    // backend's date-only string (DateField speaks YYYY-MM-DD and never calls
    // new Date(), so no timezone drift). Bools become the select's string.
    const next = {};
    for (const f of cfg.fields) {
      const cur = row[f.key];
      if (f.type === "bool") {
        next[f.key] = cur === true ? "true" : cur === false ? "false" : "";
      } else if (f.type === "date") {
        next[f.key] = cur ?? null;
      } else if (f.type === "json") {
        next[f.key] = cur != null ? JSON.stringify(cur, null, 2) : "";
      } else {
        next[f.key] = cur == null ? "" : String(cur);
      }
    }
    setShowCreate(false);
    setEditingRow(row);
    setEditValues(next);
    setEditReason("");
    setEditError(null);
  }

  function cancelEdit() {
    setEditingRow(null);
    setEditValues({});
    setEditReason("");
    setEditError(null);
  }

  async function submitEdit(e) {
    e.preventDefault();
    if (!editingRow) return;
    if (writesBlocked) { setEditError("Write blocked: scope is unresolved or invalid."); return; }
    if (editReason.trim().length < 8) {
      setEditError("Reason must be ≥8 chars.");
      return;
    }
    const nullable = NULLABLE_ON_EDIT[entity] || new Set();
    // Diff against the original row: only keys the admin actually changed are
    // submitted. uiOnly (cascade-only) and readonly (server-derived) fields are
    // never sent.
    const editExcluded = EDIT_EXCLUDED_FIELDS[entity] || new Set();
    const patch = {};
    for (const f of cfg.fields) {
      if (f.uiOnly || f.type === "readonly" || editExcluded.has(f.key)) continue;
      let parsed;
      try {
        parsed = parseValue(f, editValues[f.key]);
      } catch (err) {
        setEditError(`Invalid ${f.key}: ${err.message}`);
        return;
      }
      const orig = editingRow[f.key] == null ? undefined : editingRow[f.key];
      const changed = parsed === undefined ? orig !== undefined : parsed !== orig;
      if (!changed) continue;
      if (parsed === undefined) {
        // Cleared a field. Only allowed when the column is nullable.
        if (!nullable.has(f.key)) {
          setEditError(`${f.key} cannot be empty.`);
          return;
        }
        patch[f.key] = null;
      } else {
        patch[f.key] = parsed;
      }
    }
    if (Object.keys(patch).length === 0) {
      setEditError("No changes to save.");
      return;
    }
    await runEdit({
      action: () =>
        api.patch(`/api/admin/exam-intelligence-cms/${entity}/${editingRow.id}`, {
          reason: editReason.trim(),
          payload: patch,
        }),
      onSuccess: (r) => {
        setStatus({ ok: true, message: `Updated. audit_id=${r.audit_id}` });
        cancelEdit();
        load();
      },
      errorMessage: "Save failed.",
    });
  }

  function deactivateRow(row) {
    // Soft-delete only (backend flips is_active=false; child rows keep their
    // FK). Opens the accessible retire dialog instead of window.confirm/prompt.
    if (!isDeactivatable) return;
    const label = (row.name || row.slug || row.id || "").toString();
    setRetireTarget({ row, label });
    setRetireReason("");
    setRetireError(null);
  }

  async function confirmRetire() {
    if (!retireTarget) return;
    if (writesBlocked) { setRetireError("Write blocked: scope is unresolved or invalid."); return; }
    if (retireReason.trim().length < 8) {
      setRetireError("Retire reason must be ≥8 chars.");
      return;
    }
    const { row } = retireTarget;
    await runRetire({
      action: () =>
        api.del(
          `/api/admin/exam-intelligence-cms/${entity}/${row.id}?reason=${encodeURIComponent(retireReason.trim())}`,
        ),
      onSuccess: (r) => {
        setStatus({ ok: true, message: `Retired. audit_id=${r.audit_id}` });
        setRetireTarget(null);
        if (editingRow && editingRow.id === row.id) cancelEdit();
        load();
      },
      errorMessage: "Retire failed.",
    });
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
    const prefill = {};
    if (scopeExamId && cfg?.fields.some((f) => !f.uiOnly && f.key === "exam_id")) {
      prefill.exam_id = scopeExamId;
    }
    // B.3: cycle_id without exam_id is ignored — do not prefill cycle into create form either
    if (scopeExamId && scopeCycleId && cfg?.fields.some((f) => !f.uiOnly && f.key === "exam_cycle_id")) {
      prefill.exam_cycle_id = scopeCycleId;
    }
    setFormValues(prefill);
    setReason("");
    setEditingRow(null);
    setEditValues({});
    setEditReason("");
    setEditError(null);
    // J1: reset search/filter/page when entity or scope changes; clear pending debounce
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    setSearch("");
    setStatusFilter("");
    setFamilyFilter("");
    setExtraFilters({});
    setSelectedIds(new Set());
    setShowBulkEdit(false);
    setBulkEditField("");
    setBulkEditValues({});
    setBulkEditReason("");
    setBulkEditError(null);
    setBulkActionResult(null);
    setBulkRetireOpen(false);
    setBulkRetireReason("");
    setBulkRetireError(null);
    setPage(1);
    setTotalCount(null);
    setHasMore(false);
    load({ searchVal: "", filterVal: "", pageVal: 1, familyVal: "", extraVal: {} });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entity, isAuthorized, scopeExamId, scopeCycleId]);

  // J1: resolve human-readable scope names; track resolution state and resolved identity
  useEffect(() => {
    if (!isAuthorized || !scopeExamId) {
      setScopeExamName(null); setExamScopeState("idle"); setResolvedExamId(null); return;
    }
    let cancelled = false;
    // Reset synchronously so writesBlocked=true on this render and on scope change
    setScopeExamName(null);
    setExamScopeState("resolving");
    setResolvedExamId(null);
    (async () => {
      let offset = 0;
      try {
        while (!cancelled) {
          const r = await api.get(`/api/admin/exam-intelligence-cms/exams?limit=200&offset=${offset}`);
          if (cancelled) return;
          const items = r?.items || [];
          const exam = items.find((e) => e.id === scopeExamId);
          if (exam) { setScopeExamName(exam.name); setExamScopeState("valid"); setResolvedExamId(scopeExamId); return; }
          if (items.length < 200) break;
          offset += 200;
        }
        if (!cancelled) { setScopeExamName("(exam not found)"); setExamScopeState("error"); }
      } catch { if (!cancelled) { setScopeExamName("(exam not found)"); setExamScopeState("error"); } }
    })();
    return () => { cancelled = true; };
  }, [isAuthorized, scopeExamId]);

  useEffect(() => {
    if (!isAuthorized || !scopeCycleId) {
      setScopeCycleName(null); setCycleScopeState("idle"); setResolvedCycleId(null); return;
    }
    let cancelled = false;
    setScopeCycleName(null);
    setCycleScopeState("resolving");
    setResolvedCycleId(null);
    (async () => {
      const examParam = scopeExamId ? `&exam_id=${encodeURIComponent(scopeExamId)}` : "";
      let offset = 0;
      try {
        while (!cancelled) {
          const r = await api.get(`/api/admin/exam-intelligence-cms/exam-cycles?limit=200&offset=${offset}${examParam}`);
          if (cancelled) return;
          const items = r?.items || [];
          const cycle = items.find((c) => c.id === scopeCycleId);
          if (cycle) { setScopeCycleName(cycle.cycle_name ?? cycle.year ?? "(cycle not found)"); setCycleScopeState("valid"); setResolvedCycleId(scopeCycleId); return; }
          if (items.length < 200) break;
          offset += 200;
        }
        if (!cancelled) { setScopeCycleName("(cycle not found)"); setCycleScopeState("error"); }
      } catch { if (!cancelled) { setScopeCycleName("(cycle not found)"); setCycleScopeState("error"); } }
    })();
    return () => { cancelled = true; };
  }, [isAuthorized, scopeCycleId, scopeExamId]);

  // M4: populate the exam-family picker once an ENTITY_FAMILY_SCOPE entity is
  // selected (currently only subjects). Small, admin-only list — one page.
  // async/await + try/catch (not raw .then chaining) so a mocked/unmocked
  // api.get that resolves to a non-promise in tests can't throw here.
  useEffect(() => {
    if (!isAuthorized || !ENTITY_FAMILY_SCOPE.has(entity) || examFamilies.length > 0) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get("/api/admin/exam-intelligence-cms/exam-families?limit=200");
        if (!cancelled) setExamFamilies(r?.items || []);
      } catch {
        if (!cancelled) setExamFamilies([]);
      }
    })();
    return () => { cancelled = true; };
  }, [isAuthorized, entity, examFamilies.length]);

  // Organization filter options for the exams entity — same list the
  // conducting_organization_id ref picker (OrgRefSelect) already fetches.
  useEffect(() => {
    if (!isAuthorized || entity !== "exams" || orgOptions.length > 0) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get("/api/admin/organizations?limit=200");
        if (!cancelled) setOrgOptions(Array.isArray(r?.items) ? r.items : []);
      } catch {
        if (!cancelled) setOrgOptions([]);
      }
    })();
    return () => { cancelled = true; };
  }, [isAuthorized, entity, orgOptions.length]);

  function handleSearchChange(e) {
    const val = e.target.value;
    setSearch(val);
    setPage(1);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      load({ searchVal: val, filterVal: statusFilter, pageVal: 1 });
    }, 300);
  }

  function handleExtraFilterChange(param, value) {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    const next = { ...extraFilters, [param]: value };
    setExtraFilters(next);
    setPage(1);
    load({ searchVal: search, filterVal: statusFilter, pageVal: 1, familyVal: familyFilter, extraVal: next });
  }

  function toggleRowSelected(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function togglePageSelected() {
    const pageIds = (items?.items || []).map((r) => r.id);
    setSelectedIds((prev) => {
      const allSelected = pageIds.length > 0 && pageIds.every((id) => prev.has(id));
      const next = new Set(prev);
      if (allSelected) {
        pageIds.forEach((id) => next.delete(id));
      } else {
        pageIds.forEach((id) => next.add(id));
      }
      return next;
    });
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  // Gathers every row id matching the current filters (not just the loaded
  // page) by walking the same list endpoint with the same query params,
  // capped at the backend's per-bulk-call limit so one click can't fan out
  // an unbounded request.
  async function selectAllMatchingFilter() {
    const cap = 500;
    setSelectAllBusy(true);
    setBulkActionResult(null);
    try {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
      if (scopeExamId && ENTITY_EXAM_SCOPE.has(entity)) params.set("exam_id", scopeExamId);
      if (scopeExamId && scopeCycleId && ENTITY_CYCLE_SCOPE.has(entity)) params.set("exam_cycle_id", scopeCycleId);
      const searchParam = ENTITY_SEARCH_PARAM[entity];
      if (search && searchParam) params.set(searchParam, search);
      const statusCfg = ENTITY_STATUS_CONFIG[entity];
      if (statusFilter && statusCfg) params.set(statusCfg.param, statusFilter);
      if (familyFilter && ENTITY_FAMILY_SCOPE.has(entity)) params.set("exam_family_id", familyFilter);
      for (const fc of ENTITY_EXTRA_FILTERS[entity] || []) {
        const v = extraFilters[fc.param];
        if (v !== undefined && v !== "") params.set(fc.param, v);
      }
      if (entity === "exams" && extraFilters.conducting_organization_id) {
        params.set("conducting_organization_id", extraFilters.conducting_organization_id);
      }
      const ids = new Set();
      let offset = 0;
      while (ids.size < cap) {
        params.set("offset", String(offset));
        const r = await api.get(`/api/admin/exam-intelligence-cms/${entity}?${params}`);
        const pageItems = r?.items || [];
        for (const row of pageItems) {
          if (ids.size >= cap) break;
          ids.add(row.id);
        }
        if (pageItems.length < PAGE_SIZE) break;
        offset += PAGE_SIZE;
      }
      setSelectedIds(ids);
      setStatus({ ok: true, message: `Selected ${ids.size} row(s) matching the current filter${ids.size >= cap ? ` (capped at ${cap})` : ""}.` });
    } catch (e) {
      setStatus({ ok: false, message: getApiErrorMessage(e) });
    } finally {
      setSelectAllBusy(false);
    }
  }

  function openBulkEdit() {
    setShowBulkEdit((s) => !s);
    setBulkEditField("");
    setBulkEditValues({});
    setBulkEditReason("");
    setBulkEditError(null);
    setBulkActionResult(null);
  }

  async function submitBulkEdit(e) {
    e.preventDefault();
    if (writesBlocked) { setBulkEditError("Write blocked: scope is unresolved or invalid."); return; }
    if (!bulkEditField) { setBulkEditError("Choose a field to set."); return; }
    if (bulkEditReason.trim().length < 8) { setBulkEditError("Reason must be ≥8 chars."); return; }
    const field = cfg.fields.find((f) => f.key === bulkEditField);
    let value;
    try {
      value = parseValue(field, bulkEditValues[field.key]);
    } catch (err) {
      setBulkEditError(`Invalid ${field.key}: ${err.message}`);
      return;
    }
    if (value === undefined) { setBulkEditError(`${field.key} cannot be blank for a bulk set.`); return; }
    await runBulkUpdate({
      action: () =>
        api.post("/api/admin/exam-intelligence-cms/bulk-update", {
          reason: bulkEditReason.trim(),
          entity,
          ids: Array.from(selectedIds),
          patch: { [field.key]: value },
        }),
      onSuccess: (r) => {
        setBulkActionResult(r);
        setStatus({ ok: r.ok, message: `Bulk update: ${r.ok_count}/${r.total} ok, ${r.error_count} errors. audit_id=${r.audit_id}` });
        setShowBulkEdit(false);
        setBulkEditField("");
        setBulkEditValues({});
        setBulkEditReason("");
        clearSelection();
        load();
      },
      errorMessage: "Bulk update failed.",
    });
  }

  async function confirmBulkRetire() {
    if (writesBlocked) { setBulkRetireError("Write blocked: scope is unresolved or invalid."); return; }
    if (bulkRetireReason.trim().length < 8) { setBulkRetireError("Retire reason must be ≥8 chars."); return; }
    await runBulkDeactivate({
      action: () =>
        api.post("/api/admin/exam-intelligence-cms/bulk-deactivate", {
          reason: bulkRetireReason.trim(),
          entity,
          ids: Array.from(selectedIds),
        }),
      onSuccess: (r) => {
        setBulkActionResult(r);
        setStatus({ ok: r.ok, message: `Bulk retire: ${r.ok_count}/${r.total} ok, ${r.error_count} errors. audit_id=${r.audit_id}` });
        setBulkRetireOpen(false);
        setBulkRetireReason("");
        clearSelection();
        load();
      },
      errorMessage: "Bulk retire failed.",
    });
  }

  function handleStatusChange(e) {
    const val = e.target.value;
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    setStatusFilter(val);
    setPage(1);
    load({ searchVal: search, filterVal: val, pageVal: 1 });
  }

  function handleFamilyChange(e) {
    const val = e.target.value;
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    setFamilyFilter(val);
    setPage(1);
    load({ searchVal: search, filterVal: statusFilter, pageVal: 1, familyVal: val });
  }

  function handlePageChange(newPage) {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    setPage(newPage);
    load({ searchVal: search, filterVal: statusFilter, pageVal: newPage });
  }

  function clearScope() {
    const next = new URLSearchParams(searchParams);
    next.delete("exam_id");
    next.delete("cycle_id");
    setSearchParams(next);
  }

  if (authStatus === "checking") {
    return <div data-testid="advanced-repair-checking" style={{ padding: "2rem" }}>Checking permissions…</div>;
  }
  if (!isAuthorized) {
    return (
      <div data-testid="advanced-repair-denied" style={{ padding: "2rem" }}>
        <h2>Access denied</h2>
        <p>
          Advanced Repair requires the <code>exam_intelligence.cms</code> permission.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5" data-testid="admin-exam-intel-cms">
      <div>
        <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground font-semibold">
          Study OS · exam intelligence CMS
        </div>
        <h1 className="mt-1 font-heading text-3xl font-semibold tracking-tight">Advanced Import / Repair</h1>
        <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
          Create exam families, exams, cycles, phases, syllabus documents, PYQ papers/questions, topic
          coverage, and policy updates. Per spec §12 #4: CMS <strong>feeds</strong> the review queue —
          rows with a review_status / trust_status land at <code>pending</code>; promote them via the
          existing review queue, not here.
        </p>
        {/* E5: CMS = direct entity form for repair/power-users only; use the guided wizard at Exam Management → More → Create exam for normal exam creation. */}
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mt-2 max-w-2xl" data-testid="cms-wizard-distinction-note">
          For new exam creation, prefer the guided wizard (Exam Management &rarr; More &rarr; Create exam); this CMS form is for direct entity repair by power-users only.
        </p>
      </div>

      <AdminSafetyBanner
        title="Advanced Repair — exceptional use only"
        testId="advanced-repair-safety-banner"
        collapsible={false}
      >
        Use this surface only for exceptional repair, deduplication, migration recovery, or
        broken-reference correction. Normal operational work belongs in Manage Exam. Raw changes can
        affect linked exam data and remain subject to the existing review and locking lifecycle.
      </AdminSafetyBanner>
      {scopeExamId && (
        <div
          className="rounded border border-border/60 bg-muted/40 px-3 py-2 text-xs text-muted-foreground"
          data-testid="advanced-repair-scope-summary"
        >
          <span className="flex items-center gap-3 flex-wrap">
            <span>
              <strong>Scope:</strong>{" "}
              <span data-testid="scope-exam-name">{scopeExamName ?? "Loading…"}</span>
              {scopeCycleId && (
                <> · <span data-testid="scope-cycle-name">{scopeCycleName ?? "Loading…"}</span></>
              )}
              {!ENTITY_EXAM_SCOPE.has(entity) && (
                <span className="ml-2 text-amber-700" data-testid="scope-not-scoped-note">
                  — This entity is not scoped by exam.
                </span>
              )}
            </span>
            <button
              type="button"
              className="btn small"
              onClick={clearScope}
              data-testid="scope-clear-btn"
            >
              Clear scope
            </button>
          </span>
        </div>
      )}

      {scopeResolutionFailed && (
        <div
          className="rounded border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-800"
          role="alert"
          data-testid="scope-resolution-error"
        >
          <strong>Scope error:</strong> The scoped exam or cycle could not be resolved. All write
          actions are disabled until the scope is cleared or corrected.
          <button
            type="button"
            className="ml-3 underline"
            onClick={clearScope}
            data-testid="scope-error-clear-btn"
          >
            Clear scope
          </button>
        </div>
      )}

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
              disabled={writesBlocked}
              data-testid="cms-toggle-create"
            >
              <Plus className="h-3 w-3" /> {showCreate ? "Cancel" : "New row"}
            </button>
            {cfg.supportsBulk !== false ? (
              <button
                type="button"
                className="btn small"
                onClick={() => setShowBulk((s) => !s)}
                disabled={writesBlocked}
                data-testid="cms-toggle-bulk"
              >
                <Plus className="h-3 w-3" /> {showBulk ? "Cancel bulk" : "Bulk import"}
              </button>
            ) : null}
          </>
        ) : null}
      </div>

      {/* J1: search + status filter; search only for entities with documented backend support */}
      {!isDocuments && (ENTITY_SEARCH_PARAM[entity] || ENTITY_STATUS_CONFIG[entity] || ENTITY_FAMILY_SCOPE.has(entity) || ENTITY_EXTRA_FILTERS[entity] || entity === "exams") && (
        <div className="flex gap-2 items-end flex-wrap">
          {ENTITY_SEARCH_PARAM[entity] && (
            <label>
              <span className="block text-xs text-muted-foreground mb-1">Search</span>
              <input
                type="search"
                value={search}
                onChange={handleSearchChange}
                placeholder={`Search ${cfg?.label ?? entity}…`}
                className="px-2 py-1.5 text-sm border border-border/60 rounded bg-background w-48"
                data-testid="cms-search-input"
              />
            </label>
          )}
          {ENTITY_STATUS_CONFIG[entity] && (
            <label>
              <span className="block text-xs text-muted-foreground mb-1">
                {ENTITY_STATUS_CONFIG[entity].label}
              </span>
              <select
                value={statusFilter}
                onChange={handleStatusChange}
                className="px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
                data-testid="cms-status-filter"
              >
                <option value="">All statuses</option>
                {ENTITY_STATUS_CONFIG[entity].options.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
          )}
          {/* M4: exam-family filter — subjects has no direct exam_family_id column;
              the backend resolves membership via exam_topic_coverage -> topics ->
              subject_id for every exam in the selected family. */}
          {ENTITY_FAMILY_SCOPE.has(entity) && (
            <label>
              <span className="block text-xs text-muted-foreground mb-1">Exam family</span>
              <select
                value={familyFilter}
                onChange={handleFamilyChange}
                className="px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
                data-testid="cms-family-filter"
              >
                <option value="">All families (unscoped)</option>
                {examFamilies.map((f) => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
            </label>
          )}
          {(ENTITY_EXTRA_FILTERS[entity] || []).map((fc) => (
            <label key={fc.param}>
              <span className="block text-xs text-muted-foreground mb-1">{fc.label}</span>
              <select
                value={extraFilters[fc.param] ?? ""}
                onChange={(e) => handleExtraFilterChange(fc.param, e.target.value)}
                className="px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
                data-testid={`cms-filter-${fc.param}`}
              >
                <option value="">All</option>
                {fc.options.map((o) => {
                  const value = typeof o === "string" ? o : o.value;
                  const label = typeof o === "string" ? o : o.label;
                  return <option key={value} value={value}>{label}</option>;
                })}
              </select>
            </label>
          ))}
          {entity === "exams" && (
            <label>
              <span className="block text-xs text-muted-foreground mb-1">Organization</span>
              <select
                value={extraFilters.conducting_organization_id ?? ""}
                onChange={(e) => handleExtraFilterChange("conducting_organization_id", e.target.value)}
                className="px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
                data-testid="cms-filter-conducting_organization_id"
              >
                <option value="">All organizations</option>
                {orgOptions.map((o) => (
                  <option key={o.id} value={o.id}>{o.name}</option>
                ))}
              </select>
            </label>
          )}
        </div>
      )}

      {entity === "exam-topic-coverage" && (
        <div className="rounded border border-border/60 bg-card p-4" data-testid="cms-lifecycle-legend">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Review status</h2>
          <LifecycleLegend />
        </div>
      )}

      {/* M4: subjects entity note — subject_id UUIDs are truncated to first-8 chars in the table
           (via humanizeToken / renderCellValue). Exam-family filtering is not implemented for this
           entity; use subject_group or slug filters instead. */}
      {entity === "subjects" && (
        <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-1.5" data-testid="subjects-display-note">
          <strong>subject_id</strong> values are truncated for display (first 8 chars). Exam-family filtering is not available for subjects — filter by <code>subject_group</code> or <code>slug</code> instead.
        </p>
      )}

      {status ? (
        <div className={`text-sm ${status.ok ? "text-emerald-700" : "text-red-700"}`} role="status" aria-live="polite">
          {status.message}
        </div>
      ) : null}

      {err ? <div className="text-sm text-red-700" role="alert">{err}</div> : null}

      {isDocuments ? <ExamIntelDocuments scopeExamId={scopeExamId} scopeCycleId={scopeCycleId} writesBlocked={writesBlocked} /> : null}

      {!isDocuments && showBulk && cfg.supportsBulk !== false ? (
        <form onSubmit={submitBulk} className="rounded border border-border/60 bg-card p-4 space-y-2" data-testid="cms-bulk-form">
          <h3 className="text-sm font-semibold">Bulk import {ENTITY_CONFIG[entity].label}</h3>
          <p className="text-xs text-muted-foreground">
            Drop a <strong>.csv</strong> or <strong>.json</strong> file, or paste a JSON array of row
            objects (max {bulkCap}). Each row goes through the same validation as the single-row create — required
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
              <span>Rows JSON (array, max {bulkCap})</span>
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
          <button type="submit" className="btn small" disabled={busyBulk} data-testid="cms-bulk-submit">
            {busyBulk ? "Importing…" : "Import"}
          </button>
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
                {renderFieldControl(f, formValues, setFormValues, "cms-", entity)}
                {renderFieldAnnotation(f, formValues)}
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
          <button type="submit" className="btn small" disabled={busyCreate} data-testid="cms-create-submit">
            {busyCreate ? "Creating…" : "Create"}
          </button>
        </form>
      ) : null}

      {!isDocuments && isEditable && editingRow ? (
        <form onSubmit={submitEdit} className="rounded border border-sky-300/60 bg-card p-4 space-y-2" data-testid="cms-edit-form">
          <h3 className="text-sm font-semibold">
            Edit {cfg.label} row · <span className="font-mono">{String(editingRow.id).slice(0, 8)}…</span>
          </h3>
          <p className="text-xs text-muted-foreground">
            Only the fields you change are saved. Concurrency is last-write-wins — there is no
            row-version check, so the most recent save wins if two admins edit the same row.
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {cfg.fields.filter((f) => !EDIT_EXCLUDED_FIELDS[entity]?.has(f.key)).map((f) => (
              <label key={f.key} className="block">
                <span className="block text-xs text-muted-foreground mb-1">
                  {f.label}{f.required ? <span className="text-red-700"> *</span> : null}
                </span>
                {renderFieldControl(f, editValues, setEditValues, "cms-edit-", entity)}
                {renderFieldAnnotation(f, editValues)}
              </label>
            ))}
          </div>
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">Reason (≥8 chars, recorded in audit)</span>
            <textarea
              value={editReason}
              onChange={(e) => setEditReason(e.target.value)}
              rows={2}
              className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
              data-testid="cms-edit-reason"
            />
          </label>
          {editError ? (
            <div className="text-sm text-red-700" role="alert" data-testid="cms-edit-error">{editError}</div>
          ) : null}
          <div className="flex gap-2">
            <button type="submit" className="btn small" data-testid="cms-edit-submit" disabled={busyEdit}>
              {busyEdit ? "Saving…" : "Save changes"}
            </button>
            <button type="button" className="btn small" onClick={cancelEdit} data-testid="cms-edit-cancel">
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      {!isDocuments && supportsBulkSelect ? (
        <section className="rounded border border-border/60 bg-card p-3 space-y-2" data-testid="cms-bulk-toolbar">
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span className="font-semibold" data-testid="cms-bulk-selected-count">{selectedIds.size} selected</span>
            <button
              type="button"
              className="btn small"
              onClick={selectAllMatchingFilter}
              disabled={selectAllBusy || busy}
              data-testid="cms-bulk-select-all-filtered"
            >
              {selectAllBusy ? "Selecting…" : "Select all matching filter"}
            </button>
            <button
              type="button"
              className="btn small"
              onClick={clearSelection}
              disabled={selectedIds.size === 0}
              data-testid="cms-bulk-clear-selection"
            >
              Clear selection
            </button>
            <button
              type="button"
              className="btn small"
              onClick={openBulkEdit}
              disabled={selectedIds.size === 0 || writesBlocked}
              data-testid="cms-bulk-edit-toggle"
            >
              {showBulkEdit ? "Cancel bulk edit" : "Bulk edit selected"}
            </button>
            {isDeactivatable ? (
              <button
                type="button"
                className="btn small"
                onClick={() => { setBulkRetireOpen(true); setBulkRetireReason(""); setBulkRetireError(null); }}
                disabled={selectedIds.size === 0 || writesBlocked}
                data-testid="cms-bulk-retire-toggle"
              >
                Retire selected
              </button>
            ) : null}
          </div>
          {showBulkEdit ? (
            <form onSubmit={submitBulkEdit} className="rounded border border-sky-300/60 bg-background p-3 space-y-2" data-testid="cms-bulk-edit-form">
              <p className="text-xs text-muted-foreground">
                Set one field to one value across all {selectedIds.size} selected {cfg.label} row(s).
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                <label className="block">
                  <span className="block text-xs text-muted-foreground mb-1">Field</span>
                  <select
                    value={bulkEditField}
                    onChange={(e) => { setBulkEditField(e.target.value); setBulkEditValues({}); }}
                    className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
                    data-testid="cms-bulk-edit-field-select"
                  >
                    <option value="">Choose a field…</option>
                    {bulkEditableFields(entity, cfg).map((f) => (
                      <option key={f.key} value={f.key}>{f.label}</option>
                    ))}
                  </select>
                </label>
                {bulkEditField ? (() => {
                  const field = cfg.fields.find((f) => f.key === bulkEditField);
                  return (
                    <label className="block">
                      <span className="block text-xs text-muted-foreground mb-1">New value</span>
                      {renderFieldControl(field, bulkEditValues, setBulkEditValues, "cms-bulk-edit-", entity)}
                      {renderFieldAnnotation(field, bulkEditValues)}
                    </label>
                  );
                })() : null}
              </div>
              <label className="block">
                <span className="block text-xs text-muted-foreground mb-1">Reason (≥8 chars, recorded in audit)</span>
                <textarea
                  value={bulkEditReason}
                  onChange={(e) => setBulkEditReason(e.target.value)}
                  rows={2}
                  className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
                  data-testid="cms-bulk-edit-reason"
                />
              </label>
              {bulkEditError ? (
                <div className="text-sm text-red-700" role="alert" data-testid="cms-bulk-edit-error">{bulkEditError}</div>
              ) : null}
              <button type="submit" className="btn small" disabled={busyBulkUpdate} data-testid="cms-bulk-edit-submit">
                {busyBulkUpdate ? "Applying…" : `Apply to ${selectedIds.size} selected`}
              </button>
            </form>
          ) : null}
          {bulkActionResult ? (
            <details className="text-xs">
              <summary className="cursor-pointer text-muted-foreground">
                {bulkActionResult.ok_count}/{bulkActionResult.total} succeeded — click to see per-row results
              </summary>
              <pre className="mt-2 bg-muted p-2 rounded max-h-60 overflow-auto">
                {JSON.stringify(bulkActionResult.results, null, 2)}
              </pre>
            </details>
          ) : null}
        </section>
      ) : null}

      {!isDocuments ? (
      <section className="rounded border border-border/60 bg-card p-0 overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-muted/50">
            <tr>
              {supportsBulkSelect ? (
                <th className="text-left p-2">
                  <input
                    type="checkbox"
                    aria-label="Select all rows on this page"
                    checked={(items?.items || []).length > 0 && (items.items || []).every((r) => selectedIds.has(r.id))}
                    onChange={togglePageSelected}
                    data-testid="cms-select-page"
                  />
                </th>
              ) : null}
              <th className="text-left p-2"><FileText className="inline h-3 w-3 mr-1" />id</th>
              {cfg.columns.map((c) => (
                <th key={c} className="text-left p-2">{c}</th>
              ))}
              {isEditable ? <th className="text-left p-2">actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {!items?.items?.length ? (
              <tr><td colSpan={cfg.columns.length + 1 + (isEditable ? 1 : 0) + (supportsBulkSelect ? 1 : 0)} className="p-3 text-muted-foreground text-center">
                {busy ? "Loading…" : "No rows."}
              </td></tr>
            ) : items.items.map((r) => (
              <tr key={r.id} className="border-t border-border/40">
                {supportsBulkSelect ? (
                  <td className="p-2">
                    <input
                      type="checkbox"
                      aria-label={`Select row ${r.id}`}
                      checked={selectedIds.has(r.id)}
                      onChange={() => toggleRowSelected(r.id)}
                      data-testid={`cms-select-row-${r.id}`}
                    />
                  </td>
                ) : null}
                <td className="p-2 font-mono">{renderCellValue(r.id)}</td>
                {cfg.columns.map((c) => (
                  <td key={c} className="p-2">
                    {r[c] == null
                    ? (entity === "exams" && c === "management_mode"
                      ? <span className="text-muted-foreground italic">{BUSINESS_PRIORITY_LABELS.null.label}</span>
                      : "—")
                    : renderCellValue(r[c])}
                  </td>
                ))}
                {isEditable ? (
                  <td className="p-2 whitespace-nowrap">
                    <button
                      type="button"
                      className="btn small"
                      onClick={() => startEdit(r)}
                      disabled={writesBlocked || busy}
                      data-testid={`cms-edit-${r.id}`}
                    >
                      Edit
                    </button>
                    {isDeactivatable && r.is_active !== false ? (
                      <button
                        type="button"
                        className="btn small ml-1"
                        onClick={() => deactivateRow(r)}
                        disabled={writesBlocked || busy}
                        data-testid={`cms-retire-${r.id}`}
                      >
                        Retire
                      </button>
                    ) : null}
                    {entity === "exams" && !writesBlocked ? (
                      <a
                        href={`/admin/exam-intelligence/exams/${r.id}/add-cycle`}
                        className="btn small ml-1"
                        data-testid={`ac-entry-${r.id}`}
                      >
                        Add cycle
                      </a>
                    ) : null}
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
        {items !== null && !ENTITY_NO_OFFSET.has(entity) ? (
          <div className="flex items-center gap-3 text-xs text-muted-foreground p-2 border-t border-border/40" data-testid="cms-pagination-footer">
            <button
              type="button"
              className="btn small"
              onClick={() => handlePageChange(page - 1)}
              disabled={page <= 1 || busy}
              data-testid="cms-page-prev-btn"
            >
              Previous
            </button>
            <span data-testid="cms-page-indicator">
              {totalCount != null
                ? `Page ${page} of ${Math.max(1, Math.ceil(totalCount / PAGE_SIZE))} (${totalCount} total)`
                : `Page ${page}`}
            </span>
            <button
              type="button"
              className="btn small"
              onClick={() => handlePageChange(page + 1)}
              disabled={totalCount != null ? page >= Math.ceil(totalCount / PAGE_SIZE) : !hasMore || busy}
              data-testid="cms-page-next-btn"
            >
              Next
            </button>
          </div>
        ) : null}
      </section>
      ) : null}

      {retireTarget ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="retire-dialog-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          data-testid="cms-retire-dialog"
        >
          <div className="bg-background rounded-lg border border-border shadow-lg w-full max-w-md p-6 space-y-4">
            <h2 id="retire-dialog-title" className="font-semibold text-base">
              Retire {cfg.label} &ldquo;{retireTarget.label}&rdquo;?
            </h2>
            <p className="text-sm text-muted-foreground">
              Retiring sets <code>is_active=false</code> and hides this row from aspirants. Active
              identity rows linked to this entry will no longer appear in exam listings. This action
              is recorded in the audit log and is reversible only by an admin edit.
            </p>
            <label className="block">
              <span className="block text-xs text-muted-foreground mb-1">
                Reason for retiring (≥8 chars, recorded in audit)
              </span>
              <textarea
                value={retireReason}
                onChange={(e) => setRetireReason(e.target.value)}
                rows={3}
                autoFocus
                className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
                data-testid="cms-retire-reason"
              />
            </label>
            {retireError ? (
              <div className="text-sm text-red-700" role="alert" data-testid="cms-retire-error">
                {retireError}
              </div>
            ) : null}
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                className="btn small"
                onClick={() => setRetireTarget(null)}
                disabled={busyRetire}
                data-testid="cms-retire-cancel"
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn small"
                onClick={confirmRetire}
                disabled={busyRetire}
                data-testid="cms-retire"
              >
                {busyRetire ? "Retiring…" : "Confirm retire"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {bulkRetireOpen ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="bulk-retire-dialog-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          data-testid="cms-bulk-retire-dialog"
        >
          <div className="bg-background rounded-lg border border-border shadow-lg w-full max-w-md p-6 space-y-4">
            <h2 id="bulk-retire-dialog-title" className="font-semibold text-base">
              Retire {selectedIds.size} {cfg.label} row(s)?
            </h2>
            <p className="text-sm text-muted-foreground">
              Retiring sets <code>is_active=false</code> on every selected row and hides them from
              aspirants. This action is recorded in the audit log and is reversible only by an
              admin edit.
            </p>
            <label className="block">
              <span className="block text-xs text-muted-foreground mb-1">
                Reason for retiring (≥8 chars, recorded in audit)
              </span>
              <textarea
                value={bulkRetireReason}
                onChange={(e) => setBulkRetireReason(e.target.value)}
                rows={3}
                autoFocus
                className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
                data-testid="cms-bulk-retire-reason"
              />
            </label>
            {bulkRetireError ? (
              <div className="text-sm text-red-700" role="alert" data-testid="cms-bulk-retire-error">
                {bulkRetireError}
              </div>
            ) : null}
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                className="btn small"
                onClick={() => setBulkRetireOpen(false)}
                disabled={busyBulkDeactivate}
                data-testid="cms-bulk-retire-cancel"
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn small"
                onClick={confirmBulkRetire}
                disabled={busyBulkDeactivate}
                data-testid="cms-bulk-retire-confirm"
              >
                {busyBulkDeactivate ? "Retiring…" : "Confirm retire"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
