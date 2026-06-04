import React, { useEffect, useState } from "react";
import { RotateCcw, Plus, FileText } from "lucide-react";
import { api, getApiErrorMessage } from "../../../lib/api";
import { parseImportFile } from "../../../lib/bulkImportFile";
import CmsRefField from "../../../features/admin/shared/CmsRefField";
import { DateField } from "../../../shared/ui/heavy";
import ExamIntelDocuments from "./ExamIntelDocuments";

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
      { key: "source_id", label: "source_id (source_registry uuid, optional)" },
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
      { key: "exam_id", label: "exam_id", required: true, type: "ref", ref: REF_EXAM },
      { key: "topic_id", label: "topic_id", required: true, type: "ref", ref: refTopic({}) },
      { key: "exam_cycle_id", label: "exam_cycle_id", type: "ref", ref: refCycle({ exam_id: "exam_id" }) },
      { key: "exam_phase_id", label: "exam_phase_id", type: "ref", ref: refPhase({ exam_id: "exam_id", exam_cycle_id: "exam_cycle_id" }) },
      { key: "section_id", label: "section_id (cascades from phase)", type: "ref", ref: refSection({ exam_phase_id: "exam_phase_id" }) },
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
      { key: "exam_cycle_id", label: "exam_cycle_id", type: "ref", ref: refCycle({ exam_id: "exam_id" }) },
      { key: "source_id", label: "source_id (source_registry uuid, optional)" },
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
const EDITABLE_ENTITIES = new Set(["exam-families", "exams", "exam-cycles", "exam-phases"]);
// Only these two have a DELETE (soft-delete → is_active=false) route.
const DEACTIVATABLE_ENTITIES = new Set(["exam-families", "exams"]);

// Per-entity columns that are nullable in Postgres AND surfaced in cfg.fields,
// so clearing them on edit may legitimately submit null. Any other field
// cleared to empty is blocked (the column is NOT NULL — e.g. slug/name/exam_id/
// year/cycle_name/phase_name/phase_slug, or a defaulted enum/bool like
// status/is_active/phase_order). Source: docs/schema/supabase-current.md.
const NULLABLE_ON_EDIT = {
  "exam-families": new Set(["description"]),
  exams: new Set(["exam_family_id", "exam_type", "description"]),
  "exam-cycles": new Set([
    "notification_date", "application_start", "application_end",
    "exam_start", "exam_end", "source_url",
  ]),
  "exam-phases": new Set([
    "exam_cycle_id", "mode", "duration_mins", "total_questions", "total_marks",
  ]),
};

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
        value={values[f.key] ?? ""}
        onChange={(e) => set(e.target.value)}
        className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
        data-testid={testId}
      >
        <option value="">(skip)</option>
        {f.options.map((o) => (
          <option key={o} value={o}>{o}</option>
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
  // Edit state. ``editingRow`` is the original row (also the diff baseline);
  // ``editValues`` is the prefilled, mutable form bag.
  const [editingRow, setEditingRow] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [editReason, setEditReason] = useState("");
  const [editBusy, setEditBusy] = useState(false);
  const [editError, setEditError] = useState(null);

  const isDocuments = entity === "documents";
  const cfg = ENTITY_CONFIG[entity];
  const isEditable = EDITABLE_ENTITIES.has(entity);
  const isDeactivatable = DEACTIVATABLE_ENTITIES.has(entity);
  // Per-entity bulk caps — source of truth is the backend. UI copy only; the
  // backend enforces. Submit is never blocked client-side.
  const bulkCap = { "pyq-questions": 2000, "pyq-options": 4000, "pyq-question-topic-tags": 2000 }[entity] || 500;

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
    if (editReason.trim().length < 8) {
      setEditError("Reason must be ≥8 chars.");
      return;
    }
    const nullable = NULLABLE_ON_EDIT[entity] || new Set();
    // Diff against the original row: only keys the admin actually changed are
    // submitted. uiOnly (cascade-only) and readonly (server-derived) fields are
    // never sent.
    const patch = {};
    for (const f of cfg.fields) {
      if (f.uiOnly || f.type === "readonly") continue;
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
    setEditBusy(true);
    try {
      const r = await api.patch(`/api/admin/exam-intelligence-cms/${entity}/${editingRow.id}`, {
        reason: editReason.trim(),
        payload: patch,
      });
      setStatus({ ok: true, message: `Updated. audit_id=${r.audit_id}` });
      cancelEdit();
      load();
    } catch (ex) {
      setEditError(getApiErrorMessage(ex));
    } finally {
      setEditBusy(false);
    }
  }

  async function deactivateRow(row) {
    // Soft-delete only (backend flips is_active=false; child rows keep their
    // FK). UI never says "Delete".
    if (!isDeactivatable) return;
    const label = (row.name || row.slug || row.id || "").toString();
    if (!window.confirm(`Deactivate ${cfg.label} "${label}"? It will be hidden (is_active=false), not deleted.`)) {
      return;
    }
    const reasonText = window.prompt("Reason for deactivating (≥8 chars, recorded in audit):") || "";
    if (reasonText.trim().length < 8) {
      setStatus({ ok: false, message: "Deactivate reason must be ≥8 chars." });
      return;
    }
    try {
      const r = await api.del(
        `/api/admin/exam-intelligence-cms/${entity}/${row.id}?reason=${encodeURIComponent(reasonText.trim())}`,
      );
      setStatus({ ok: true, message: `Deactivated. audit_id=${r.audit_id}` });
      if (editingRow && editingRow.id === row.id) cancelEdit();
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
    setEditingRow(null);
    setEditValues({});
    setEditReason("");
    setEditError(null);
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
                {renderFieldControl(f, formValues, setFormValues, "cms-", entity)}
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
            {cfg.fields.map((f) => (
              <label key={f.key} className="block">
                <span className="block text-xs text-muted-foreground mb-1">
                  {f.label}{f.required ? <span className="text-red-700"> *</span> : null}
                </span>
                {renderFieldControl(f, editValues, setEditValues, "cms-edit-", entity)}
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
            <button type="submit" className="btn small" data-testid="cms-edit-submit" disabled={editBusy}>
              {editBusy ? "Saving…" : "Save changes"}
            </button>
            <button type="button" className="btn small" onClick={cancelEdit} data-testid="cms-edit-cancel">
              Cancel
            </button>
          </div>
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
              {isEditable ? <th className="text-left p-2">actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {!items?.items?.length ? (
              <tr><td colSpan={cfg.columns.length + 1 + (isEditable ? 1 : 0)} className="p-3 text-muted-foreground text-center">
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
                {isEditable ? (
                  <td className="p-2 whitespace-nowrap">
                    <button
                      type="button"
                      className="btn small"
                      onClick={() => startEdit(r)}
                      data-testid={`cms-edit-${r.id}`}
                    >
                      Edit
                    </button>
                    {isDeactivatable && r.is_active !== false ? (
                      <button
                        type="button"
                        className="btn small ml-1"
                        onClick={() => deactivateRow(r)}
                        data-testid={`cms-deactivate-${r.id}`}
                      >
                        Deactivate
                      </button>
                    ) : null}
                  </td>
                ) : null}
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
