/**
 * PyqPaperWorkspace — three-pane reviewer workspace for a single PYQ paper.
 *
 * Layout:
 *   Left   (~30%)  Question list with filters + missing-number indicator
 *   Center (~40%)  Selected question editor + options + status actions
 *   Right  (~30%)  Source PDF preview via signed URL
 *
 * Routes: /admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace
 *
 * Props (optional):
 *   paperId  — if provided, use this instead of useParams (embedded mode)
 *   embedded — if true, drop h-screen wrapper (sized by parent)
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, ChevronDown, Copy, ExternalLink, Trash2, Link2 } from "lucide-react";
import { api } from "../../../lib/api";
import { useAuth } from "../../../lib/authContext";
import useApiAction from "../../../lib/hooks/useApiAction";

// ── Constants ────────────────────────────────────────────────────────────────

const CMS_BASE = "/api/admin/exam-intelligence-cms";
const REVIEW_BASE = "/api/admin/exam-intelligence";

const PAGE_SIZE = 50;

const STATUS_COLORS = {
  pending: "bg-amber-100 text-amber-800",
  verified: "bg-emerald-100 text-emerald-800",
  rejected: "bg-rose-100 text-rose-800 opacity-60",
  needs_correction: "bg-orange-100 text-orange-800",
};

const SOURCE_KIND_COLORS = {
  auto_extracted: "bg-indigo-100 text-indigo-700",
  manual: "bg-clay-100 text-clay-700",
  bulk_import: "bg-sky-100 text-sky-700",
};

const QUESTION_TYPES = ["mcq", "numerical", "descriptive", "caselet", "matching", "other"];
const DIFFICULTY_OPTIONS = ["easy", "medium", "hard", "very_hard"];
const REJECT_REASONS = ["incomplete", "duplicate", "out_of_scope", "illegible", "other"];
const OPTION_LABELS = ["A", "B", "C", "D", "E", "F"];
// Mirrors backend _STIMULUS_TYPES (admin_exam_intel_cms.py). Shared passages,
// caselets, tables, charts etc. that back one or more questions.
const STIMULUS_TYPES = ["passage", "caselet", "table", "chart", "image", "diagram", "other"];

// Review-status transitions for a stimulus's CONTENT and for a
// question↔stimulus LINK go through the review-queue router, not CMS_BASE.
const STIMULUS_ITEM_TYPE = "pyq_stimulus";
const LINK_ITEM_TYPE = "pyq_question_stimulus";

const AUDIT_REASON = "workspace reviewer action";

// ── Small helpers ─────────────────────────────────────────────────────────────

function Badge({ label, colorClass, className = "" }) {
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold ${colorClass} ${className}`}>
      {label}
    </span>
  );
}

function confidenceFromField(confidenceByField) {
  if (!confidenceByField || typeof confidenceByField !== "object") return null;
  const vals = Object.values(confidenceByField).filter((v) => typeof v === "number");
  if (!vals.length) return null;
  return Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 100);
}

// ── Left pane ─────────────────────────────────────────────────────────────────

function QuestionList({
  questions,
  selectedId,
  onSelect,
  progress,
  statusFilter,
  setStatusFilter,
  sourceKindFilter,
  setSourceKindFilter,
  onAddMissing,
  offset,
  total,
  pageSize,
  onPageChange,
}) {
  const missingNumbers = progress?.missing || [];

  // Both reviewer_status and source_kind are server-side params — questions
  // arrive pre-filtered. No client-side refiltering needed.
  const filtered = questions;

  const pageStart = offset + 1;
  const pageEnd = offset + questions.length;
  const canPrev = offset > 0;
  const canNext = total !== null
    ? offset + pageSize < total
    : questions.length === pageSize;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Missing indicator */}
      {missingNumbers.length > 0 && (
        <div className="p-2 bg-amber-50 border-b border-amber-200 text-[11px] text-amber-800">
          <span className="font-semibold">Missing:</span>{" "}
          {missingNumbers.slice(0, 20).join(", ")}
          {missingNumbers.length > 20 ? ` +${missingNumbers.length - 20} more` : ""}
          <button
            type="button"
            onClick={() => onAddMissing(missingNumbers[0])}
            className="ml-2 text-amber-700 underline hover:no-underline"
          >
            Add missing
          </button>
        </div>
      )}

      {/* Filters + pagination */}
      <div className="p-2 border-b border-clay-200 space-y-1.5 text-[11px]">
        <div className="flex gap-1.5 flex-wrap">
          <select
            className="rounded border border-clay-200 px-1.5 py-0.5 text-[11px] bg-white"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            {["all", "pending", "verified", "rejected", "needs_correction"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select
            className="rounded border border-clay-200 px-1.5 py-0.5 text-[11px] bg-white"
            value={sourceKindFilter}
            onChange={(e) => setSourceKindFilter(e.target.value)}
          >
            {["all", "auto_extracted", "manual", "bulk_import"].map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center justify-between gap-2">
          <p className="text-clay-500" data-testid="question-list-count">
            {filtered.length} shown
            {total !== null && (
              <span data-testid="question-list-total"> · {total} total</span>
            )}
          </p>
          <div className="flex items-center gap-1" data-testid="pagination-controls">
            <button
              type="button"
              className="btn btn-ghost p-0.5 disabled:opacity-40"
              onClick={() => onPageChange(Math.max(0, offset - pageSize))}
              disabled={!canPrev}
              aria-label="Previous page"
              data-testid="pagination-prev"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <span className="text-[10px] text-clay-500 min-w-[50px] text-center" data-testid="pagination-range">
              {questions.length > 0 ? `${pageStart}–${pageEnd}` : "0"}
            </span>
            <button
              type="button"
              className="btn btn-ghost p-0.5 disabled:opacity-40"
              onClick={() => onPageChange(offset + pageSize)}
              disabled={!canNext}
              aria-label="Next page"
              data-testid="pagination-next"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Question rows */}
      <div className="overflow-y-auto flex-1">
        {filtered.map((q) => {
          const conf = confidenceFromField(q.confidence_by_field);
          const isSelected = q.id === selectedId;
          return (
            <button
              key={q.id}
              type="button"
              onClick={() => onSelect(q)}
              className={`w-full text-left px-3 py-2 border-b border-clay-100 transition-colors ${
                isSelected
                  ? "bg-clay-50 border-l-4 border-l-clay-400"
                  : "hover:bg-[#FFFDF9]"
              } ${q.reviewer_status === "rejected" ? "opacity-50" : ""}`}
              data-testid={`question-list-item-${q.id}`}
            >
              <div className="flex items-center justify-between gap-1 mb-0.5">
                <span className="text-sm font-bold text-clay-800">
                  Q{q.question_number ?? "?"}
                </span>
                <div className="flex items-center gap-1">
                  {conf !== null && (
                    <span className="text-[10px] text-clay-500">{conf}%</span>
                  )}
                  <Badge
                    label={q.reviewer_status}
                    colorClass={STATUS_COLORS[q.reviewer_status] || "bg-gray-100 text-gray-600"}
                  />
                </div>
              </div>
              <p className="text-[11px] text-clay-600 truncate leading-snug">
                {(q.question_text || "").slice(0, 80) || <em>no text</em>}
              </p>
              <div className="flex gap-1 mt-0.5 flex-wrap">
                {q.source_kind && (
                  <Badge
                    label={q.source_kind}
                    colorClass={SOURCE_KIND_COLORS[q.source_kind] || "bg-gray-100 text-sky-700"}
                  />
                )}
              </div>
            </button>
          );
        })}
        {filtered.length === 0 && (
          <p className="p-4 text-[12px] text-muted-foreground">No questions match the filters.</p>
        )}
      </div>
    </div>
  );
}

// ── Options editor ────────────────────────────────────────────────────────────

function OptionsEditor({ questionId, initialOptions, onSaved, canEdit = true }) {
  const [options, setOptions] = useState(initialOptions || []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    setOptions(initialOptions || []);
    setAdding(false);
  }, [questionId, initialOptions]);

  function startAdd() {
    const existing = options.map((o) => o.option_label);
    const nextLabel = OPTION_LABELS.find((l) => !existing.includes(l)) || "E";
    setOptions((prev) => [
      ...prev,
      { option_label: nextLabel, option_text: "", is_correct: false, _new: true },
    ]);
    setAdding(true);
  }

  async function saveOption(opt, idx) {
    if (!opt.option_text.trim()) return;
    setBusy(true);
    setError("");
    try {
      if (opt.id) {
        await api.patch(`${CMS_BASE}/pyq-options/${opt.id}`, {
          reason: AUDIT_REASON,
          payload: {
            option_text: opt.option_text,
            is_correct: opt.is_correct,
            source_label: opt.source_label?.trim() ? opt.source_label.trim() : null,
            display_order:
              opt.display_order !== "" && opt.display_order != null
                ? Number(opt.display_order)
                : null,
          },
        });
      } else {
        const res = await api.post(`${CMS_BASE}/pyq-options`, {
          reason: AUDIT_REASON,
          payload: {
            question_id: questionId,
            option_label: opt.option_label,
            option_text: opt.option_text,
            is_correct: opt.is_correct,
            source_label: opt.source_label?.trim() ? opt.source_label.trim() : null,
            display_order:
              opt.display_order !== "" && opt.display_order != null
                ? Number(opt.display_order)
                : null,
          },
        });
        const saved = res.row || res;
        setOptions((prev) => prev.map((o, i) => (i === idx ? { ...saved } : o)));
      }
      if (onSaved) onSaved();
    } catch (e) {
      setError(e?.message || "Save failed");
    } finally {
      setBusy(false);
    }
  }

  function updateOption(idx, patch) {
    setOptions((prev) => prev.map((o, i) => (i === idx ? { ...o, ...patch } : o)));
  }

  return (
    <div className="space-y-1.5">
      {options.map((opt, idx) => (
        <div key={opt.id || idx} className="flex items-start gap-2" data-testid={`option-row-${opt.option_label}`}>
          <span className="w-6 flex-shrink-0 text-[12px] font-bold text-clay-600 mt-1.5">
            [{opt.option_label}]
          </span>
          <div className="flex-1 space-y-1">
            <input
              className="w-full border border-clay-200 rounded px-2 py-1 text-sm bg-white"
              value={opt.option_text || ""}
              onChange={(e) => updateOption(idx, { option_text: e.target.value })}
              onBlur={() => saveOption(opt, idx)}
              placeholder="Option text…"
              disabled={!canEdit}
            />
            <div className="flex gap-1.5">
              <input
                className="flex-1 border border-clay-200 rounded px-2 py-0.5 text-[11px] bg-white"
                value={opt.source_label ?? ""}
                onChange={(e) => updateOption(idx, { source_label: e.target.value })}
                onBlur={() => saveOption(opt, idx)}
                placeholder="Printed label (source_label)…"
                disabled={!canEdit}
                data-testid={`option-source-label-${opt.option_label}`}
              />
              <input
                type="number"
                className="w-24 border border-clay-200 rounded px-2 py-0.5 text-[11px] bg-white"
                value={opt.display_order ?? ""}
                onChange={(e) => updateOption(idx, { display_order: e.target.value })}
                onBlur={() => saveOption(opt, idx)}
                placeholder="order"
                disabled={!canEdit}
                data-testid={`option-display-order-${opt.option_label}`}
              />
            </div>
          </div>
          <label className="flex items-center gap-1 text-[11px] text-clay-600 mt-1.5">
            <input
              type="checkbox"
              checked={!!opt.is_correct}
              disabled={!canEdit}
              data-testid={`option-correct-${opt.option_label}`}
              onChange={(e) => {
                const updated = { ...opt, is_correct: e.target.checked };
                updateOption(idx, { is_correct: e.target.checked });
                if (updated.id) saveOption(updated, idx);
              }}
            />
            ✓
          </label>
        </div>
      ))}
      {options.length === 0 && !adding && (
        <p className="text-[12px] text-muted-foreground">
          No options yet.{" "}
          {canEdit && (
            <button type="button" className="underline text-clay-700" onClick={startAdd}>
              Add options
            </button>
          )}
        </p>
      )}
      {canEdit && options.length > 0 && options.length < 6 && (
        <button type="button" className="text-[11px] text-clay-600 underline" onClick={startAdd}>
          + Add option
        </button>
      )}
      {error && <p className="text-[11px] text-rose-600">{error}</p>}
      {busy && <p className="text-[11px] text-muted-foreground">Saving…</p>}
    </div>
  );
}

// ── Dup detection panel ───────────────────────────────────────────────────────

function DupPanel({ paperId, questionId, questionText, onDismiss, onLinkDuplicate }) {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (!questionText || questionText.length < 20) {
      setMatches([]);
      return;
    }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({ question_text: questionText });
        if (questionId) params.set("question_id", questionId);
        const res = await api.get(
          `${CMS_BASE}/pyq-papers/${paperId}/dup-check?${params}`,
        );
        setMatches(res.matches || []);
      } catch {
        setMatches([]);
      } finally {
        setLoading(false);
      }
    }, 800);
    return () => clearTimeout(debounceRef.current);
  }, [paperId, questionId, questionText]);

  if (loading) return <p className="text-[11px] text-muted-foreground">Checking for duplicates…</p>;
  if (!matches.length) return null;

  return (
    <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 space-y-2">
      <p className="text-[11px] font-semibold text-amber-800">
        ⚠ {matches.length} possible duplicate{matches.length === 1 ? "" : "s"} detected
      </p>
      {matches.map((m) => (
        <div key={m.id} className="flex items-start gap-2 text-[11px] text-amber-900">
          <span className="flex-1">
            Q{m.question_number ?? "?"} · {m.reviewer_status} · ratio {(m.ratio * 100).toFixed(0)}%
            <br />
            <span className="text-amber-700 truncate block max-w-[280px]">
              {(m.question_text || "").slice(0, 80)}
            </span>
          </span>
          <div className="flex flex-col gap-0.5">
            <button
              type="button"
              className="text-[10px] border border-amber-300 rounded px-1.5 py-0.5 hover:bg-amber-100"
              onClick={() => onLinkDuplicate(m)}
            >
              Link as dup
            </button>
            <button
              type="button"
              className="text-[10px] border border-amber-200 rounded px-1.5 py-0.5 hover:bg-amber-50"
              onClick={() => onDismiss(m.id)}
            >
              Dismiss
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Question ↔ stimulus links (shown inside the question editor) ───────────────

function truncate(text, n = 90) {
  const t = (text || "").trim();
  return t.length > n ? `${t.slice(0, n)}…` : t;
}

function QuestionStimuliLinks({ questionId, stimuli = [], canEdit, canReview, refreshKey, onMutated }) {
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const genRef = useRef(0);
  const { run } = useApiAction();

  const stimulusById = React.useMemo(() => {
    const m = {};
    for (const s of stimuli) m[s.id] = s;
    return m;
  }, [stimuli]);

  const load = useCallback(async () => {
    if (!questionId) { setLinks([]); return; }
    genRef.current += 1;
    const gen = genRef.current;
    setLoading(true);
    setError("");
    try {
      const res = await api.get(
        `${CMS_BASE}/pyq-question-stimuli?question_id=${encodeURIComponent(questionId)}`,
      );
      if (genRef.current !== gen) return;
      setLinks(res.items || []);
    } catch (e) {
      if (genRef.current !== gen) return;
      setError(e?.message || "Could not load linked passages");
    } finally {
      if (genRef.current === gen) setLoading(false);
    }
  }, [questionId]);

  useEffect(() => { load(); }, [load, refreshKey]);

  async function reviewLink(link, nextStatus) {
    await run({
      action: () => api.patch(
        `${REVIEW_BASE}/items/${LINK_ITEM_TYPE}/${link.id}/review`,
        { reviewer_status: nextStatus },
      ),
      onSuccess: () => { if (onMutated) onMutated(); else load(); },
      errorMessage: "Could not update link status",
    });
  }

  async function unlink(link) {
    await run({
      action: () => api.delete(`${CMS_BASE}/pyq-question-stimuli/${link.id}`),
      onSuccess: () => { if (onMutated) onMutated(); else load(); },
      errorMessage: "Could not unlink passage",
    });
  }

  return (
    <div data-testid="question-stimuli-links">
      <p className="text-[11px] font-semibold text-clay-700 mb-1 uppercase tracking-wider">
        Linked passages / stimuli
      </p>
      <p className="text-[10.5px] text-clay-500 mb-1.5">
        Verifying this question also verifies its links. The shared passage content is
        reviewed independently in the Passages panel.
      </p>
      {loading && <p className="text-[11px] text-muted-foreground">Loading linked passages…</p>}
      {error && <p className="text-[11px] text-rose-600" data-testid="question-stimuli-links-error">{error}</p>}
      {!loading && !error && links.length === 0 && (
        <p className="text-[11px] text-muted-foreground" data-testid="question-stimuli-links-empty">
          No passages linked to this question.
        </p>
      )}
      <div className="space-y-1.5">
        {links.map((link) => {
          const stim = stimulusById[link.stimulus_id];
          return (
            <div
              key={link.id}
              className="rounded-lg border border-clay-200 bg-white px-2 py-1.5 text-[11px]"
              data-testid={`question-link-${link.id}`}
            >
              <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                {stim?.stimulus_type && (
                  <Badge label={stim.stimulus_type} colorClass="bg-violet-100 text-violet-700" />
                )}
                <Badge
                  label={link.reviewer_status}
                  colorClass={STATUS_COLORS[link.reviewer_status] || "bg-gray-100 text-gray-600"}
                />
                <span className="text-clay-600 truncate flex-1">
                  {stim ? truncate(stim.content_text, 60) || <em>(no text)</em> : link.stimulus_id}
                </span>
              </div>
              {(canReview || canEdit) && (
                <div className="flex items-center gap-1 flex-wrap">
                  {canReview && (
                    <>
                      <button
                        type="button"
                        className="text-[10px] border border-emerald-300 text-emerald-700 rounded px-1.5 py-0.5 hover:bg-emerald-50"
                        onClick={() => reviewLink(link, "verified")}
                        data-testid={`link-verify-${link.id}`}
                      >
                        Verify
                      </button>
                      <button
                        type="button"
                        className="text-[10px] border border-rose-300 text-rose-600 rounded px-1.5 py-0.5 hover:bg-rose-50"
                        onClick={() => reviewLink(link, "rejected")}
                        data-testid={`link-reject-${link.id}`}
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        className="text-[10px] border border-orange-300 text-orange-700 rounded px-1.5 py-0.5 hover:bg-orange-50"
                        onClick={() => reviewLink(link, "needs_correction")}
                        data-testid={`link-needs-correction-${link.id}`}
                      >
                        Needs correction
                      </button>
                    </>
                  )}
                  {canEdit && (
                    <button
                      type="button"
                      className="text-[10px] text-clay-500 hover:text-rose-600 ml-auto flex items-center gap-0.5"
                      onClick={() => unlink(link)}
                      data-testid={`link-unlink-${link.id}`}
                    >
                      <Trash2 className="h-3 w-3" /> Unlink
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Center pane ───────────────────────────────────────────────────────────────

function QuestionEditor({
  question,
  options,
  paperId,
  sections = [],
  stimuli = [],
  canEdit = true,
  canReview = true,
  linkRefreshKey = 0,
  onMutated,
  onSaved,
  onStatusChange,
  onNavigate,
  onOpenDoc,
}) {
  const [form, setForm] = useState({});
  const [rejectReason, setRejectReason] = useState("incomplete");
  const [correctionNotes, setCorrectionNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [provenanceOpen, setProvenanceOpen] = useState(false);

  useEffect(() => {
    if (!question) return;
    setForm({
      question_number: question.question_number ?? "",
      question_text: question.question_text ?? "",
      question_type: question.question_type ?? "mcq",
      observed_difficulty: question.observed_difficulty ?? "",
      expected_solve_time_sec: question.expected_solve_time_sec ?? "",
      section_id: question.section_id ?? "",
      source_question_ref: question.source_question_ref ?? "",
      display_order: question.display_order ?? "",
      metadata: question.metadata ? JSON.stringify(question.metadata, null, 2) : "{}",
    });
    setError("");
  }, [question]);

  const set = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  async function saveDraft() {
    if (!question) return;
    setBusy(true);
    setError("");
    try {
      let meta;
      try {
        meta = JSON.parse(form.metadata || "{}");
      } catch {
        setError("Invalid JSON in metadata field.");
        setBusy(false);
        return;
      }
      const payload = {
        question_number: form.question_number !== "" ? Number(form.question_number) : null,
        question_text: form.question_text,
        question_type: form.question_type,
        observed_difficulty: form.observed_difficulty || null,
        expected_solve_time_sec:
          form.expected_solve_time_sec !== "" ? Number(form.expected_solve_time_sec) : null,
        // Section assignment + printed-order preservation (migration 223, PR-3).
        // A section not in the paper's phase is rejected server-side (422),
        // surfaced via the catch below.
        section_id: form.section_id || null,
        source_question_ref: form.source_question_ref?.trim() ? form.source_question_ref.trim() : null,
        display_order: form.display_order !== "" && form.display_order != null ? Number(form.display_order) : null,
        metadata: meta,
      };
      await api.patch(`${CMS_BASE}/pyq-questions/${question.id}`, {
        reason: AUDIT_REASON,
        payload,
      });
      if (onSaved) onSaved();
    } catch (e) {
      setError(e?.message || "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function doReview(nextStatus, notes) {
    if (!question) return;
    setBusy(true);
    setError("");
    try {
      await api.patch(
        `${REVIEW_BASE}/items/pyq_question/${question.id}/review`,
        { reviewer_status: nextStatus, reviewer_notes: notes || undefined },
      );
      if (onStatusChange) onStatusChange(question.id, nextStatus);
    } catch (e) {
      setError(e?.message || "Status change failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify() {
    if (!form.question_text?.trim()) {
      setError("question_text is required to verify.");
      return;
    }
    if (!form.question_number) {
      setError("question_number is required to verify.");
      return;
    }
    await saveDraft();
    await doReview("verified");
  }

  async function handleReject() {
    await doReview("rejected", rejectReason);
  }

  async function handleNeedsCorrection() {
    await doReview("needs_correction", correctionNotes || undefined);
  }

  function handleDismissDup(dupId) {
    const meta = (() => {
      try {
        return JSON.parse(form.metadata || "{}");
      } catch {
        return {};
      }
    })();
    const dismissals = meta.dup_dismissals || [];
    if (!dismissals.includes(dupId)) dismissals.push(dupId);
    meta.dup_dismissals = dismissals;
    set("metadata", JSON.stringify(meta, null, 2));
  }

  async function handleLinkDuplicate(dupRow) {
    await doReview(
      "rejected",
      `duplicate_of:${dupRow.id}`,
    );
  }

  if (!question) {
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground h-full">
        Select a question from the list.
      </div>
    );
  }

  const conf = confidenceFromField(question.confidence_by_field);

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4 space-y-4 text-sm">
      {/* Header */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => onNavigate(-1)}
          className="btn btn-ghost p-1"
          title="Previous (K / ↑)"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <h2 className="font-bold text-clay-800 flex-1">
          Q{form.question_number || "?"}
        </h2>
        <button
          type="button"
          onClick={() => onNavigate(1)}
          className="btn btn-ghost p-1"
          title="Next (J / ↓)"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <Badge
          label={question.reviewer_status}
          colorClass={STATUS_COLORS[question.reviewer_status] || "bg-gray-100 text-gray-600"}
        />
      </div>

      {error && (
        <div className="rounded-xl bg-dusk-50 text-dusk-800 text-[11px] px-3 py-2">{error}</div>
      )}

      {/* Editable fields */}
      <div className="space-y-2">
        <WsField label="Question number">
          <input
            type="number"
            className="input-ws"
            value={form.question_number ?? ""}
            onChange={(e) => set("question_number", e.target.value)}
            data-testid="editor-question-number"
          />
        </WsField>
        <WsField label="Question text">
          <textarea
            rows={6}
            className="input-ws"
            value={form.question_text ?? ""}
            onChange={(e) => set("question_text", e.target.value)}
            data-testid="editor-question-text"
          />
        </WsField>
        <div className="flex gap-2">
          <WsField label="Type" className="flex-1">
            <select
              className="input-ws"
              value={form.question_type ?? "mcq"}
              onChange={(e) => set("question_type", e.target.value)}
            >
              {QUESTION_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </WsField>
          <WsField label="Difficulty" className="flex-1">
            <select
              className="input-ws"
              value={form.observed_difficulty ?? ""}
              onChange={(e) => set("observed_difficulty", e.target.value)}
            >
              <option value="">—</option>
              {DIFFICULTY_OPTIONS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </WsField>
        </div>
        <WsField label="Expected solve time (sec)">
          <input
            type="number"
            className="input-ws"
            value={form.expected_solve_time_sec ?? ""}
            onChange={(e) => set("expected_solve_time_sec", e.target.value)}
          />
        </WsField>

        {/* Section assignment + printed-order (migration 223, PR-3) */}
        <WsField label="Section">
          <select
            className="input-ws"
            value={form.section_id ?? ""}
            onChange={(e) => set("section_id", e.target.value)}
            disabled={!canEdit}
            data-testid="editor-question-section"
          >
            <option value="">— none —</option>
            {sections.map((s) => (
              <option key={s.id} value={s.id}>
                {s.section_label}
              </option>
            ))}
          </select>
        </WsField>
        <div className="flex gap-2">
          <WsField label="Source question ref" className="flex-1">
            <input
              className="input-ws"
              value={form.source_question_ref ?? ""}
              onChange={(e) => set("source_question_ref", e.target.value)}
              disabled={!canEdit}
              placeholder="e.g. Q12 / Set-B 7"
              data-testid="editor-source-question-ref"
            />
          </WsField>
          <WsField label="Display order" className="flex-1">
            <input
              type="number"
              className="input-ws"
              value={form.display_order ?? ""}
              onChange={(e) => set("display_order", e.target.value)}
              disabled={!canEdit}
              data-testid="editor-display-order"
            />
          </WsField>
        </div>
      </div>

      {/* Provenance (read-only) */}
      <div>
        <button
          type="button"
          className="text-[11px] text-clay-600 underline"
          onClick={() => setProvenanceOpen((p) => !p)}
        >
          {provenanceOpen ? "Hide" : "Show"} provenance
        </button>
        {provenanceOpen && (
          <div
            className="mt-2 space-y-1 text-[11px] bg-clay-50 rounded-xl p-3 text-clay-700"
            data-testid="provenance-panel"
          >
            <ProvenanceLine label="source_kind" value={question.source_kind} />
            <ProvenanceLine
              label="source_document"
              value={question.source_document_id}
              action={
                question.source_document_id ? (
                  <button
                    type="button"
                    className="underline"
                    onClick={() => onOpenDoc(question.source_document_id, question.source_page)}
                  >
                    Preview
                  </button>
                ) : null
              }
            />
            <ProvenanceLine label="source_page" value={question.source_page} />
            {question.source_regions && (
              <ProvenanceLine
                label="source_regions"
                value={`page ${question.source_page}, bbox ${
                  Array.isArray(question.source_regions) && question.source_regions[0]
                    ? question.source_regions[0].join(", ")
                    : JSON.stringify(question.source_regions)
                }`}
              />
            )}
            <ProvenanceLine label="extraction_run" value={question.extraction_run_id} copyable />
            <ProvenanceLine
              label="confidence"
              value={conf !== null ? `${conf}%` : "—"}
            />
            <ProvenanceLine label="extractor_version" value={question.extractor_version} />
            <ProvenanceLine label="idempotency_key" value={question.idempotency_key} copyable />
            <ProvenanceLine label="content_hash" value={question.content_hash} copyable />
          </div>
        )}
      </div>

      {/* Dup detection */}
      <DupPanel
        paperId={paperId}
        questionId={question.id}
        questionText={form.question_text}
        onDismiss={handleDismissDup}
        onLinkDuplicate={handleLinkDuplicate}
      />

      {/* Options */}
      <div>
        <p className="text-[11px] font-semibold text-clay-700 mb-1.5 uppercase tracking-wider">
          Options
        </p>
        <OptionsEditor
          questionId={question.id}
          initialOptions={options}
          onSaved={onSaved}
          canEdit={canEdit}
        />
      </div>

      {/* Linked passages / stimuli for this question (migration 223, PR-3) */}
      <QuestionStimuliLinks
        questionId={question.id}
        stimuli={stimuli}
        canEdit={canEdit}
        canReview={canReview}
        refreshKey={linkRefreshKey}
        onMutated={onMutated}
      />

      {/* Metadata */}
      <WsField label="Metadata (JSON)">
        <textarea
          rows={4}
          className="input-ws font-mono text-[11px]"
          value={form.metadata ?? "{}"}
          onChange={(e) => set("metadata", e.target.value)}
        />
      </WsField>

      {/* PYQ status lifecycle legend */}
      <div className="border-t border-clay-200 pt-3">
        <p className="text-[10px] text-clay-500 mb-1 font-semibold uppercase tracking-wide">PYQ status lifecycle</p>
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10.5px] text-clay-600">
          <span><span className="inline-block w-2 h-2 rounded-sm bg-amber-300 mr-1 align-middle" />pending — awaiting review</span>
          <span><span className="inline-block w-2 h-2 rounded-sm bg-orange-300 mr-1 align-middle" />needs_correction — sent back for edits</span>
          <span><span className="inline-block w-2 h-2 rounded-sm bg-emerald-400 mr-1 align-middle" />verified — approved for scoring/analysis</span>
          <span><span className="inline-block w-2 h-2 rounded-sm bg-rose-300 mr-1 align-middle" />rejected — excluded permanently</span>
        </div>
      </div>

      {/* Status actions */}
      <div className="border-t border-clay-200 pt-3 space-y-2">
        {/* Reject controls */}
        {question.reviewer_status !== "rejected" && (
          <div className="flex items-center gap-2">
            <select
              className="input-ws text-[11px] flex-1"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            >
              {REJECT_REASONS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
            <button
              type="button"
              className="btn btn-ghost border border-rose-300 text-rose-700 text-[12px] px-3 py-1.5"
              onClick={handleReject}
              disabled={busy}
              data-testid="btn-reject"
            >
              Reject
            </button>
          </div>
        )}

        {/* Needs correction notes */}
        <div className="flex items-center gap-2">
          <input
            className="input-ws text-[11px] flex-1"
            placeholder="Correction notes (optional)…"
            value={correctionNotes}
            onChange={(e) => setCorrectionNotes(e.target.value)}
          />
          <button
            type="button"
            className="btn btn-ghost border border-orange-300 text-orange-700 text-[12px] px-3 py-1.5"
            onClick={handleNeedsCorrection}
            disabled={busy}
            data-testid="btn-needs-correction"
          >
            Needs correction
          </button>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            className="btn btn-ghost text-[12px] px-3 py-1.5 flex-1"
            onClick={saveDraft}
            disabled={busy}
            data-testid="btn-save-draft"
          >
            {busy ? "Saving…" : "Save draft  (S)"}
          </button>
          <button
            type="button"
            className="btn btn-primary text-[12px] px-4 py-1.5"
            onClick={handleVerify}
            disabled={busy}
            data-testid="btn-verify"
          >
            Verify  (V)
          </button>
        </div>
      </div>

      <style>{`
        .input-ws {
          width: 100%;
          padding: 0.45rem 0.8rem;
          border-radius: 0.65rem;
          background: rgba(255,255,255,0.9);
          border: 1px solid #E7DECB;
          font-size: 13px;
        }
      `}</style>
    </div>
  );
}

function WsField({ label, children, className = "" }) {
  return (
    <label className={`block ${className}`}>
      <span className="text-[10px] uppercase tracking-wider text-clay-600">{label}</span>
      <div className="mt-0.5">{children}</div>
    </label>
  );
}

function ProvenanceLine({ label, value, copyable, action }) {
  function copy() {
    if (value) navigator.clipboard.writeText(String(value));
  }
  return (
    <div className="flex items-center gap-1">
      <span className="w-32 flex-shrink-0 font-medium">{label}</span>
      <span className="truncate text-clay-500 max-w-[200px]">
        {value !== null && value !== undefined ? String(value) : "—"}
      </span>
      {copyable && value && (
        <button type="button" onClick={copy} title="Copy">
          <Copy className="h-3 w-3 text-clay-400 hover:text-clay-700" />
        </button>
      )}
      {action}
    </div>
  );
}

// ── Right pane — PDF preview ─────────────────────────────────────────────────

function PdfPreview({ documentId, paperId, sourcePage }) {
  const [signedUrl, setSignedUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(sourcePage || 1);

  useEffect(() => {
    setPage(sourcePage || 1);
  }, [sourcePage]);

  useEffect(() => {
    if (!documentId || !paperId) {
      setSignedUrl(null);
      return;
    }
    setLoading(true);
    setError("");
    api
      .get(
        `${CMS_BASE}/pyq-papers/${paperId}/signed-pdf?document_id=${encodeURIComponent(documentId)}`,
      )
      .then((res) => {
        setSignedUrl(res.signed_url);
      })
      .catch((e) => {
        setError(e?.message || "Cannot load preview.");
        setSignedUrl(null);
      })
      .finally(() => setLoading(false));
  }, [documentId, paperId]);

  if (!documentId) {
    return (
      <div className="flex items-center justify-center h-full text-[12px] text-muted-foreground p-4 text-center">
        Manual entry; no source preview
      </div>
    );
  }
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-[12px] text-muted-foreground">
        Loading preview…
      </div>
    );
  }
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-[12px] text-muted-foreground p-4 text-center">
        <p>{error}</p>
        {signedUrl && (
          <a
            href={signedUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="underline text-clay-700 flex items-center gap-1"
          >
            Open PDF <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>
    );
  }
  if (!signedUrl) return null;

  const urlWithPage = `${signedUrl}#page=${page}`;

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-clay-200 text-[11px]">
        <button
          type="button"
          className="btn btn-ghost p-0.5"
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-clay-600">Page {page}</span>
        <button
          type="button"
          className="btn btn-ghost p-0.5"
          onClick={() => setPage((p) => p + 1)}
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <a
          href={signedUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto text-clay-600 hover:text-clay-900"
          title="Open in new tab"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>
      <iframe
        key={page}
        src={urlWithPage}
        title="Source PDF"
        className="flex-1 w-full border-0"
        data-testid="pdf-preview-iframe"
      />
    </div>
  );
}

// ── Add missing question modal ────────────────────────────────────────────────

function AddMissingModal({ paperId, initialNumber, onClose, onCreated }) {
  const [form, setForm] = useState({
    question_number: initialNumber || "",
    question_text: "",
    question_type: "mcq",
    observed_difficulty: "",
    expected_solve_time_sec: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const set = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  async function handleCreate() {
    if (!form.question_text.trim()) {
      setError("question_text is required.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const payload = {
        pyq_paper_id: paperId,
        question_number: form.question_number ? Number(form.question_number) : null,
        question_text: form.question_text.trim(),
        question_type: form.question_type || "mcq",
        source_kind: "manual",
        observed_difficulty: form.observed_difficulty || null,
        expected_solve_time_sec:
          form.expected_solve_time_sec ? Number(form.expected_solve_time_sec) : null,
      };
      const res = await api.post(`${CMS_BASE}/pyq-questions`, {
        reason: "manual entry via workspace — missing question",
        payload,
      });
      onCreated(res.question);
    } catch (e) {
      setError(e?.message || "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg space-y-4 text-sm">
        <h3 className="font-bold text-clay-800">Add missing question</h3>
        {error && (
          <div className="rounded-xl bg-dusk-50 text-dusk-800 text-[11px] px-3 py-2">{error}</div>
        )}
        <WsField label="Question number">
          <input
            type="number"
            className="input-ws"
            value={form.question_number}
            onChange={(e) => set("question_number", e.target.value)}
          />
        </WsField>
        <WsField label="Question text">
          <textarea
            rows={5}
            className="input-ws"
            value={form.question_text}
            onChange={(e) => set("question_text", e.target.value)}
          />
        </WsField>
        <div className="flex gap-2">
          <WsField label="Type" className="flex-1">
            <select
              className="input-ws"
              value={form.question_type}
              onChange={(e) => set("question_type", e.target.value)}
            >
              {QUESTION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </WsField>
          <WsField label="Difficulty" className="flex-1">
            <select
              className="input-ws"
              value={form.observed_difficulty}
              onChange={(e) => set("observed_difficulty", e.target.value)}
            >
              <option value="">—</option>
              {DIFFICULTY_OPTIONS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </WsField>
        </div>
        <div className="flex justify-end gap-2 pt-2 border-t border-clay-200">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleCreate}
            disabled={busy}
          >
            {busy ? "Creating…" : "Create question"}
          </button>
        </div>
        <style>{`.input-ws{width:100%;padding:.45rem .8rem;border-radius:.65rem;background:rgba(255,255,255,.9);border:1px solid #E7DECB;font-size:13px;}`}</style>
      </div>
    </div>
  );
}

// ── Progress bar ──────────────────────────────────────────────────────────────

function ProgressBar({ progress }) {
  if (!progress) return null;
  const { total_expected, present, by_status = {}, missing = [] } = progress;
  const verified = by_status.verified || 0;
  const rejected = by_status.rejected || 0;
  const pending = by_status.pending || 0;
  const needs_correction = by_status.needs_correction || 0;
  const total = total_expected || present || 1;
  const pct = (n) => `${((n / total) * 100).toFixed(1)}%`;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-3 text-[11px] text-clay-700">
        <span>
          <strong className="text-emerald-700">{verified}</strong> verified
        </span>
        <span>
          <strong className="text-amber-700">{pending}</strong> pending
        </span>
        <span>
          <strong className="text-orange-700">{needs_correction}</strong> needs correction
        </span>
        <span>
          <strong className="text-rose-700">{rejected}</strong> rejected
        </span>
        {missing.length > 0 && (
          <span>
            <strong className="text-clay-500">{missing.length}</strong> missing
          </span>
        )}
        <span className="text-clay-500">/ {total} expected</span>
      </div>
      <div className="flex h-2 rounded-full overflow-hidden bg-clay-100">
        <div className="bg-emerald-400" style={{ width: pct(verified) }} />
        <div className="bg-orange-400" style={{ width: pct(needs_correction) }} />
        <div className="bg-rose-300" style={{ width: pct(rejected) }} />
        <div className="bg-amber-300" style={{ width: pct(pending) }} />
      </div>
    </div>
  );
}

// ── Passages / stimuli panel ──────────────────────────────────────────────────

function StimulusRow({
  stimulus,
  sectionLabel,
  canEdit,
  canReview,
  selectedQuestionId,
  refreshKey,
  onMutated,
}) {
  const [count, setCount] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(stimulus.content_text || "");
  const { run } = useApiAction();

  const loadCount = useCallback(async () => {
    try {
      const res = await api.get(
        `${CMS_BASE}/pyq-question-stimuli?stimulus_id=${encodeURIComponent(stimulus.id)}`,
      );
      setCount(res.total ?? (res.items || []).length);
    } catch {
      setCount(null);
    }
  }, [stimulus.id]);

  useEffect(() => { loadCount(); }, [loadCount, refreshKey]);
  useEffect(() => { setDraft(stimulus.content_text || ""); setEditing(false); }, [stimulus.content_text, stimulus.id]);

  async function review(nextStatus) {
    await run({
      action: () => api.patch(
        `${REVIEW_BASE}/items/${STIMULUS_ITEM_TYPE}/${stimulus.id}/review`,
        { reviewer_status: nextStatus },
      ),
      onSuccess: onMutated,
      errorMessage: "Could not update stimulus status",
    });
  }

  async function saveContent() {
    await run({
      action: () => api.patch(`${CMS_BASE}/pyq-stimuli/${stimulus.id}`, {
        reason: AUDIT_REASON,
        payload: { content_text: draft },
      }),
      onSuccess: () => { setEditing(false); if (onMutated) onMutated(); },
      errorMessage: "Could not save stimulus content",
    });
  }

  async function remove() {
    await run({
      action: () => api.delete(`${CMS_BASE}/pyq-stimuli/${stimulus.id}`),
      onSuccess: onMutated,
      confirm: "Delete this passage/stimulus? Its question links will be removed.",
      errorMessage: "Could not delete stimulus",
    });
  }

  async function linkSelected() {
    if (!selectedQuestionId) return;
    await run({
      action: () => api.post(`${CMS_BASE}/pyq-question-stimuli`, {
        reason: AUDIT_REASON,
        payload: { question_id: selectedQuestionId, stimulus_id: stimulus.id },
      }),
      onSuccess: onMutated,
      errorMessage: "Could not link question to stimulus",
    });
  }

  return (
    <div
      className="rounded-lg border border-clay-200 bg-white px-3 py-2 text-[11px] space-y-1"
      data-testid={`stimulus-row-${stimulus.id}`}
    >
      <div className="flex items-center gap-1.5 flex-wrap">
        <Badge label={stimulus.stimulus_type} colorClass="bg-violet-100 text-violet-700" />
        <Badge
          label={stimulus.reviewer_status}
          colorClass={STATUS_COLORS[stimulus.reviewer_status] || "bg-gray-100 text-gray-600"}
        />
        {sectionLabel && (
          <span className="text-clay-500" data-testid={`stimulus-section-${stimulus.id}`}>
            § {sectionLabel}
          </span>
        )}
        <span className="text-clay-500 ml-auto" data-testid={`stimulus-linkcount-${stimulus.id}`}>
          {count == null ? "…" : `${count} linked`}
        </span>
      </div>

      {editing ? (
        <textarea
          rows={3}
          className="w-full border border-clay-200 rounded px-2 py-1 text-[11px] bg-white"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          data-testid={`stimulus-content-input-${stimulus.id}`}
        />
      ) : (
        <p className="text-clay-700">
          {truncate(stimulus.content_text, 160) || <em className="text-clay-400">(no text)</em>}
        </p>
      )}

      {(canReview || canEdit) && (
        <div className="flex items-center gap-1 flex-wrap pt-0.5">
          {canReview && (
            <>
              <button
                type="button"
                className="text-[10px] border border-emerald-300 text-emerald-700 rounded px-1.5 py-0.5 hover:bg-emerald-50"
                onClick={() => review("verified")}
                data-testid={`stimulus-verify-${stimulus.id}`}
              >
                Verify
              </button>
              <button
                type="button"
                className="text-[10px] border border-rose-300 text-rose-600 rounded px-1.5 py-0.5 hover:bg-rose-50"
                onClick={() => review("rejected")}
                data-testid={`stimulus-reject-${stimulus.id}`}
              >
                Reject
              </button>
              <button
                type="button"
                className="text-[10px] border border-orange-300 text-orange-700 rounded px-1.5 py-0.5 hover:bg-orange-50"
                onClick={() => review("needs_correction")}
                data-testid={`stimulus-needs-correction-${stimulus.id}`}
              >
                Needs correction
              </button>
            </>
          )}
          {canEdit && (
            <>
              {selectedQuestionId && !editing && (
                <button
                  type="button"
                  className="text-[10px] border border-indigo-300 text-indigo-700 rounded px-1.5 py-0.5 hover:bg-indigo-50 flex items-center gap-0.5"
                  onClick={linkSelected}
                  data-testid={`stimulus-link-question-${stimulus.id}`}
                >
                  <Link2 className="h-3 w-3" /> Link question
                </button>
              )}
              {editing ? (
                <>
                  <button
                    type="button"
                    className="text-[10px] border border-clay-300 text-clay-700 rounded px-1.5 py-0.5 hover:bg-clay-50"
                    onClick={saveContent}
                    data-testid={`stimulus-content-save-${stimulus.id}`}
                  >
                    Save content
                  </button>
                  <button
                    type="button"
                    className="text-[10px] text-clay-500 rounded px-1.5 py-0.5"
                    onClick={() => { setEditing(false); setDraft(stimulus.content_text || ""); }}
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="text-[10px] border border-clay-300 text-clay-700 rounded px-1.5 py-0.5 hover:bg-clay-50"
                  onClick={() => setEditing(true)}
                  data-testid={`stimulus-edit-${stimulus.id}`}
                >
                  Edit
                </button>
              )}
              <button
                type="button"
                className="text-[10px] text-clay-500 hover:text-rose-600 ml-auto flex items-center gap-0.5"
                onClick={remove}
                data-testid={`stimulus-delete-${stimulus.id}`}
              >
                <Trash2 className="h-3 w-3" /> Delete
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function StimuliPanel({
  stimuli,
  loading,
  error,
  sectionLabelById,
  sections,
  canEdit,
  canReview,
  selectedQuestionId,
  paperId,
  refreshKey,
  onMutated,
}) {
  const [open, setOpen] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newType, setNewType] = useState("passage");
  const [newContent, setNewContent] = useState("");
  const [newSection, setNewSection] = useState("");
  const [createError, setCreateError] = useState("");
  const { run, busy } = useApiAction();

  async function createStimulus() {
    setCreateError("");
    const payload = { pyq_paper_id: paperId, stimulus_type: newType };
    if (newContent.trim()) payload.content_text = newContent.trim();
    if (newSection) payload.section_id = newSection;
    const res = await run({
      action: () => api.post(`${CMS_BASE}/pyq-stimuli`, { reason: AUDIT_REASON, payload }),
      errorMessage: "Could not create stimulus",
    });
    if (res?.ok) {
      setNewContent("");
      setNewSection("");
      setShowCreate(false);
      if (onMutated) onMutated();
    } else {
      setCreateError(res?.error?.message || "Could not create stimulus");
    }
  }

  return (
    <div
      className="flex-shrink-0 border-t border-clay-200 bg-[#FFFDF9]"
      data-testid="pyq-stimuli-panel"
    >
      <button
        type="button"
        className="w-full flex items-center gap-2 px-4 py-2 text-[12px] font-semibold text-clay-700"
        onClick={() => setOpen((p) => !p)}
        data-testid="pyq-stimuli-panel-toggle"
        aria-expanded={open}
      >
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        Passages / stimuli
        {stimuli.length > 0 && (
          <span className="text-[10px] text-clay-500">({stimuli.length})</span>
        )}
      </button>

      {open && (
        <div className="px-4 pb-3 space-y-2 max-h-[40vh] overflow-y-auto">
          {canEdit && (
            <div>
              {!showCreate ? (
                <button
                  type="button"
                  className="text-[11px] text-indigo-700 underline"
                  onClick={() => setShowCreate(true)}
                  data-testid="stimulus-create-open"
                >
                  + Add passage / stimulus
                </button>
              ) : (
                <div className="rounded-lg border border-clay-200 bg-white p-2 space-y-1.5" data-testid="stimulus-create-form">
                  <div className="flex gap-1.5">
                    <select
                      className="border border-clay-200 rounded px-1.5 py-0.5 text-[11px] bg-white"
                      value={newType}
                      onChange={(e) => setNewType(e.target.value)}
                      data-testid="stimulus-create-type"
                    >
                      {STIMULUS_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                    <select
                      className="border border-clay-200 rounded px-1.5 py-0.5 text-[11px] bg-white flex-1"
                      value={newSection}
                      onChange={(e) => setNewSection(e.target.value)}
                      data-testid="stimulus-create-section"
                    >
                      <option value="">— no section —</option>
                      {sections.map((s) => <option key={s.id} value={s.id}>{s.section_label}</option>)}
                    </select>
                  </div>
                  <textarea
                    rows={3}
                    className="w-full border border-clay-200 rounded px-2 py-1 text-[11px] bg-white"
                    value={newContent}
                    onChange={(e) => setNewContent(e.target.value)}
                    placeholder="Passage / stimulus content…"
                    data-testid="stimulus-create-content"
                  />
                  {createError && <p className="text-[10.5px] text-rose-600" data-testid="stimulus-create-error">{createError}</p>}
                  <div className="flex gap-1.5">
                    <button
                      type="button"
                      className="text-[11px] border border-indigo-300 text-indigo-700 rounded px-2 py-0.5 hover:bg-indigo-50 disabled:opacity-50"
                      onClick={createStimulus}
                      disabled={busy}
                      data-testid="stimulus-create-submit"
                    >
                      Add stimulus
                    </button>
                    <button
                      type="button"
                      className="text-[11px] text-clay-500 px-2 py-0.5"
                      onClick={() => { setShowCreate(false); setCreateError(""); }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {loading && <p className="text-[11px] text-muted-foreground" data-testid="pyq-stimuli-loading">Loading passages/stimuli…</p>}
          {error && <p className="text-[11px] text-rose-600" data-testid="pyq-stimuli-error">{error}</p>}
          {!loading && !error && stimuli.length === 0 && (
            <p className="text-[11px] text-muted-foreground" data-testid="pyq-stimuli-empty">
              No passages/stimuli for this paper.
            </p>
          )}
          {!loading && !error && stimuli.map((s) => (
            <StimulusRow
              key={s.id}
              stimulus={s}
              sectionLabel={s.section_id ? sectionLabelById[s.section_id] : null}
              canEdit={canEdit}
              canReview={canReview}
              selectedQuestionId={selectedQuestionId}
              refreshKey={refreshKey}
              onMutated={onMutated}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function PyqPaperWorkspace({ paperId: paperIdProp, embedded = false, status = null, rowId = null }) {
  const { pyq_paper_id: pyq_paper_id_param } = useParams();
  const pyq_paper_id = paperIdProp || pyq_paper_id_param;
  const navigate = useNavigate();

  const { user } = useAuth();
  const canReview = user?.role === "super_admin"
    || (Array.isArray(user?.permissions) && user.permissions.includes("exam_intelligence.review"));
  const canEdit = user?.role === "super_admin"
    || (Array.isArray(user?.permissions) && user.permissions.includes("exam_intelligence.cms"));

  const [paper, setPaper] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [selectedOptions, setSelectedOptions] = useState([]);

  const [progress, setProgress] = useState(null);

  const [statusFilter, setStatusFilter] = useState(status ?? "all");
  const [sourceKindFilter, setSourceKindFilter] = useState("all");

  const deepLinkApplied = useRef(false);
  const loadGenRef = useRef(0);       // macro: incremented on paper/status-prop change
  const questionsGenRef = useRef(0);  // micro: incremented per loadQuestions call
  const optionsGenRef = useRef(0);    // per loadOptions call
  const progressGenRef = useRef(0);   // per loadProgress call
  const [deepLinkNotFound, setDeepLinkNotFound] = useState(false);

  // Pagination state
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(null);

  const [pdfDocumentId, setPdfDocumentId] = useState(null);
  const [pdfPage, setPdfPage] = useState(null);

  const [showAddMissing, setShowAddMissing] = useState(false);
  const [addMissingNumber, setAddMissingNumber] = useState(null);

  // ── Sections + stimuli (migration 223, PR-3) ─────────────────────────────
  const [sections, setSections] = useState([]);
  const [stimuli, setStimuli] = useState([]);
  const [stimuliLoading, setStimuliLoading] = useState(false);
  const [stimuliError, setStimuliError] = useState("");
  // Bumped on any stimulus/link mutation so link lists + link counts reload.
  const [linkRefreshKey, setLinkRefreshKey] = useState(0);
  const stimuliGenRef = useRef(0);

  const sectionLabelById = React.useMemo(() => {
    const m = {};
    for (const s of sections) m[s.id] = s.section_label;
    return m;
  }, [sections]);

  // ── Data loading ─────────────────────────────────────────────────────────

  const loadPaper = useCallback(async () => {
    if (!pyq_paper_id) return;
    const gen = loadGenRef.current;
    try {
      const res = await api.get(`${CMS_BASE}/pyq-papers/${encodeURIComponent(pyq_paper_id)}`);
      if (loadGenRef.current !== gen) return;
      setPaper(res || null);
    } catch {
      /* best-effort */
    }
  }, [pyq_paper_id]);

  // Returns the fetched items so callers can act on them without waiting for
  // the async state update (setQuestions is enqueued, not synchronous).
  const loadQuestions = useCallback(async () => {
    const gen = loadGenRef.current;
    questionsGenRef.current += 1;          // allocate a fresh token for this call
    const qgen = questionsGenRef.current;
    setLoadError("");
    try {
      const params = new URLSearchParams({
        pyq_paper_id: pyq_paper_id,
        limit: String(PAGE_SIZE),
        offset: String(offset),
      });
      if (statusFilter !== "all") params.set("reviewer_status", statusFilter);
      if (sourceKindFilter !== "all") params.set("source_kind", sourceKindFilter);
      const res = await api.get(`${CMS_BASE}/pyq-questions?${params}`);
      if (loadGenRef.current !== gen || questionsGenRef.current !== qgen) return [];
      const items = res.items || [];
      setQuestions(items);
      setTotal(res.total ?? null);
      return items;
    } catch (e) {
      if (loadGenRef.current !== gen || questionsGenRef.current !== qgen) return [];
      setLoadError(e?.message || "Could not load questions");
      return [];
    }
  }, [pyq_paper_id, offset, statusFilter, sourceKindFilter]);

  const loadProgress = useCallback(async () => {
    const gen = loadGenRef.current;
    progressGenRef.current += 1;
    const pgen = progressGenRef.current;
    try {
      const res = await api.get(
        `${CMS_BASE}/pyq-papers/${encodeURIComponent(pyq_paper_id)}/progress`,
      );
      if (loadGenRef.current !== gen || progressGenRef.current !== pgen) return null;
      setProgress(res);
      return res;
    } catch {
      return null;
    }
  }, [pyq_paper_id]);

  const fetchQuestionById = useCallback(async (id) => {
    try {
      return await api.get(`${CMS_BASE}/pyq-questions/${encodeURIComponent(id)}`);
    } catch {
      return null;
    }
  }, []);

  const loadOptions = useCallback(async (questionId) => {
    if (!questionId) {
      setSelectedOptions([]);
      return;
    }
    optionsGenRef.current += 1;
    const ogen = optionsGenRef.current;
    try {
      const res = await api.get(
        `${CMS_BASE}/pyq-options?question_id=${encodeURIComponent(questionId)}&limit=10`,
      );
      if (optionsGenRef.current !== ogen) return;
      setSelectedOptions(res.items || []);
    } catch {
      if (optionsGenRef.current !== ogen) return;
      setSelectedOptions([]);
    }
  }, []);

  const loadStimuli = useCallback(async () => {
    if (!pyq_paper_id) return;
    stimuliGenRef.current += 1;
    const sgen = stimuliGenRef.current;
    setStimuliLoading(true);
    setStimuliError("");
    try {
      const res = await api.get(
        `${CMS_BASE}/pyq-stimuli?pyq_paper_id=${encodeURIComponent(pyq_paper_id)}&limit=100`,
      );
      if (stimuliGenRef.current !== sgen) return;
      setStimuli(res.items || []);
    } catch (e) {
      if (stimuliGenRef.current !== sgen) return;
      setStimuliError(e?.message || "Could not load passages/stimuli");
    } finally {
      if (stimuliGenRef.current === sgen) setStimuliLoading(false);
    }
  }, [pyq_paper_id]);

  // Any stimulus/link mutation reloads the paper-level stimuli list and bumps
  // the refresh key so per-question link lists + link counts re-fetch.
  const handleStimuliMutated = useCallback(() => {
    loadStimuli();
    setLinkRefreshKey((k) => k + 1);
  }, [loadStimuli]);

  // Load the paper's phase sections once the paper (and its exam_phase_id) is known.
  useEffect(() => {
    const phaseId = paper?.exam_phase_id;
    if (!phaseId) { setSections([]); return undefined; }
    let cancelled = false;
    api
      .get(`${CMS_BASE}/exam-phase-sections?exam_phase_id=${encodeURIComponent(phaseId)}&limit=100`)
      .then((res) => { if (!cancelled) setSections(res.items || []); })
      .catch(() => { if (!cancelled) setSections([]); });
    return () => { cancelled = true; };
  }, [paper?.exam_phase_id]);

  // ── Reset all paper-scoped state when the paper changes ─────────────────
  // Increment load generation so any in-flight responses from the previous
  // paper are discarded when they resolve. Must run before the data-loading
  // effect so the new load starts from a clean slate.
  useEffect(() => {
    loadGenRef.current += 1;
    optionsGenRef.current += 1;   // discard any running loadOptions from the old paper
    progressGenRef.current += 1;  // discard any running loadProgress from the old paper
    stimuliGenRef.current += 1;    // discard any running loadStimuli from the old paper
    setPaper(null);
    setQuestions([]);
    setProgress(null);
    setSelectedQuestion(null);
    setSelectedOptions([]);
    setPdfDocumentId(null);
    setPdfPage(null);
    setOffset(0);
    setTotal(null);
    setSections([]);
    setStimuli([]);
    setStimuliError("");
    deepLinkApplied.current = false;
    setDeepLinkNotFound(false);
  }, [pyq_paper_id]);

  // ── Sync status prop → statusFilter; increment gen to discard in-flight ─
  // Must run before the data-loading effect so data-loading always captures
  // the post-increment generation (avoids discarding the initial load on mount).
  useEffect(() => {
    loadGenRef.current += 1;
    optionsGenRef.current += 1;   // discard any running loadOptions from the old status context
    progressGenRef.current += 1;  // discard any running loadProgress from the old status context
    setStatusFilter(status ?? "all");
    setOffset(0);
    setSelectedQuestion(null);
    setSelectedOptions([]);
    deepLinkApplied.current = false;
    setDeepLinkNotFound(false);
  }, [status]);

  // Reload when paper changes (initial load) or when offset/statusFilter changes
  // (loadQuestions closes over offset + statusFilter; loadPaper/loadProgress are
  // stable unless pyq_paper_id changes, so extra fetches of paper/progress on
  // pagination are intentional — progress reflects live server counts).
  // loadQuestions self-allocates its token; we guard setLoading(false) with a
  // cleanup flag so an older effect cannot clear loading for a newer request.
  useEffect(() => {
    setLoading(true);
    let effectActive = true;
    // loadStimuli runs here (after the reset/status effects above) so the reset
    // effect's stimuliGenRef increment cannot discard this paper's fetch.
    Promise.all([loadPaper(), loadQuestions(), loadProgress(), loadStimuli()]).finally(() => {
      if (effectActive) setLoading(false);
    });
    return () => { effectActive = false; };
  }, [loadPaper, loadQuestions, loadProgress, loadStimuli]);

  // ── Filter handlers — reset offset so results are correct ───────────────

  function handleStatusFilterChange(value) {
    setStatusFilter(value);
    setOffset(0);
  }

  function handleSourceKindFilterChange(value) {
    setSourceKindFilter(value);
    setOffset(0);
  }

  // ── Pagination ───────────────────────────────────────────────────────────

  function handlePageChange(newOffset) {
    optionsGenRef.current += 1;   // discard any running loadOptions from the old page's selection
    setOffset(Math.max(0, newOffset));
    setSelectedQuestion(null);
    setSelectedOptions([]);
  }

  // ── Question selection ───────────────────────────────────────────────────

  function selectQuestion(q) {
    setSelectedQuestion(q);
    loadOptions(q?.id);
    if (q?.source_document_id) {
      setPdfDocumentId(q.source_document_id);
      setPdfPage(q.source_page || 1);
    }
  }

  function navigateQuestion(delta) {
    const idx = questions.findIndex((q) => q.id === selectedQuestion?.id);
    const next = questions[idx + delta];
    if (next) selectQuestion(next);
  }

  // ── Keyboard shortcuts ───────────────────────────────────────────────────

  useEffect(() => {
    function handleKey(e) {
      if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
      }
      const map = {
        j: () => navigateQuestion(1),
        ArrowDown: () => navigateQuestion(1),
        k: () => navigateQuestion(-1),
        ArrowUp: () => navigateQuestion(-1),
      };
      map[e.key]?.();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  });

  // ── Deep-link: reset guard when rowId prop changes ───────────────────────

  useEffect(() => {
    deepLinkApplied.current = false;
    setDeepLinkNotFound(false);
  }, [rowId]);

  // ── Deep-link: auto-select question matching rowId ───────────────────────

  useEffect(() => {
    if (!rowId || loading) return;
    if (deepLinkApplied.current) return;
    let cancelled = false;
    const q = questions.find((q) => q.id === rowId && q.pyq_paper_id === pyq_paper_id);
    if (q) {
      deepLinkApplied.current = true;
      setDeepLinkNotFound(false);
      setSelectedQuestion(q);
      loadOptions(q.id);
      if (q.source_document_id) {
        setPdfDocumentId(q.source_document_id);
        setPdfPage(q.source_page || 1);
      }
    } else {
      // Not on current page — fetch directly by ID (pagination-safe).
      fetchQuestionById(rowId).then((fetched) => {
        if (cancelled) return;
        if (!fetched || fetched.pyq_paper_id !== pyq_paper_id) { setDeepLinkNotFound(true); return; }
        deepLinkApplied.current = true;
        setDeepLinkNotFound(false);
        setSelectedQuestion(fetched);
        loadOptions(fetched.id);
        if (fetched.source_document_id) {
          setPdfDocumentId(fetched.source_document_id);
          setPdfPage(fetched.source_page || 1);
        }
      });
    }
    return () => { cancelled = true; };
  }, [rowId, questions, loading, loadOptions, fetchQuestionById, pyq_paper_id]);

  // ── After-save refresh ───────────────────────────────────────────────────

  async function handleSaved() {
    const [items] = await Promise.all([
      loadQuestions(),
      loadProgress(),
      loadOptions(selectedQuestion?.id),
    ]);
    if (selectedQuestion) {
      const refreshed = items.find((q) => q.id === selectedQuestion.id) || null;
      if (refreshed) setSelectedQuestion(refreshed);
    }
  }

  // Refetch after a review status change and clamp to prev page if now empty.
  async function handleStatusChange(questionId, nextStatus) {
    setQuestions((prev) =>
      prev.map((q) =>
        q.id === questionId ? { ...q, reviewer_status: nextStatus } : q,
      ),
    );
    if (selectedQuestion?.id === questionId) {
      setSelectedQuestion((p) => p && { ...p, reviewer_status: nextStatus });
    }
    const items = await loadQuestions();
    if (items.length === 0 && offset > 0) {
      setOffset(Math.max(0, offset - PAGE_SIZE));
    }
    loadProgress();
  }

  function handleOpenDoc(documentId, page) {
    setPdfDocumentId(documentId);
    setPdfPage(page || 1);
  }

  function handleAddMissing(num) {
    setAddMissingNumber(num);
    setShowAddMissing(true);
  }

  async function handleCreatedQuestion(q) {
    setShowAddMissing(false);
    await loadProgress();
    if (offset === 0) {
      await loadQuestions();
    } else {
      setOffset(0);  // effect triggers loadQuestions(offset=0)
    }
    selectQuestion(q);
  }

  // ── Render ───────────────────────────────────────────────────────────────

  const paperTitle = paper
    ? [
        paper.year,
        paper.paper_code,
        paper.shift,
      ]
        .filter(Boolean)
        .join(" · ")
    : pyq_paper_id;

  if (loading && !paper) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-muted-foreground">
        Loading workspace…
      </div>
    );
  }

  const workspaceLink = paper
    ? paper.exam_cycle_id
      ? `/admin/exam-intelligence/workspace/${paper.exam_id}/${paper.exam_cycle_id}`
      : `/admin/exam-intelligence/workspace/${paper.exam_id}`
    : null;

  return (
    <div
      className={`flex flex-col ${embedded ? "h-full" : "h-screen"} overflow-hidden`}
      data-testid="pyq-workspace-root"
      data-embedded={embedded ? "true" : "false"}
    >
      {/* Top header */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-clay-200 bg-[#FFFDF9] space-y-2">
        {!embedded && workspaceLink && (
          <div className="rounded bg-indigo-50 border border-indigo-200 px-3 py-1.5 text-[12px] text-indigo-800 flex items-center gap-2" data-testid="workspace-banner">
            This paper workspace is now available inside Exam Workspace.{" "}
            <Link
              to={workspaceLink}
              className="underline font-medium hover:no-underline"
              data-testid="workspace-banner-link"
            >
              Open in Exam Workspace →
            </Link>
          </div>
        )}
        {/* E4: dual-entry note — this workspace is reachable both as a standalone route
             (/admin/exam-intelligence/pyq-papers/:id/workspace) and as an embedded tab inside
             Exam Workspace. The standalone route has no exam context in the URL; the embedded
             version inherits exam context from ExamWorkspaceContext. If you reached this page
             directly (not from an exam workspace), exam-scoped actions and context are unavailable. */}
        {!embedded && (
          <p className="text-[11px] text-clay-500" data-testid="pyq-workspace-dual-entry-note">
            Viewing as standalone paper workspace — no exam context. To review this paper with full exam context, open it from the PYQ tab inside Exam Workspace.
          </p>
        )}
        <div className="flex items-center gap-3">
          {!embedded && (
            <button
              type="button"
              className="text-[12px] text-clay-600 hover:text-clay-900 underline"
              onClick={() => navigate("/admin/exam-intelligence")}
            >
              ← Exam intelligence
            </button>
          )}
          <h1 className="font-bold text-clay-900 text-sm">{paperTitle}</h1>
        </div>
        <ProgressBar progress={progress} />
        {loadError && (
          <p className="text-[11px] text-rose-600">{loadError}</p>
        )}
      </div>

      {rowId && deepLinkNotFound && !loading && (
        <div
          className="flex-shrink-0 px-4 py-2 bg-rose-50 border-b border-rose-200 text-[12px] text-rose-700"
          data-testid="pyq-deep-link-not-found"
        >
          Question {rowId} was not found in this paper&rsquo;s question list.
        </div>
      )}

      {/* Three-pane layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left — Question list */}
        <div
          className="w-[30%] flex-shrink-0 border-r border-clay-200 flex flex-col overflow-hidden"
          data-testid="question-list-pane"
        >
          <QuestionList
            questions={questions}
            selectedId={selectedQuestion?.id}
            onSelect={selectQuestion}
            progress={progress}
            statusFilter={statusFilter}
            setStatusFilter={handleStatusFilterChange}
            sourceKindFilter={sourceKindFilter}
            setSourceKindFilter={handleSourceKindFilterChange}
            onAddMissing={handleAddMissing}
            offset={offset}
            total={total}
            pageSize={PAGE_SIZE}
            onPageChange={handlePageChange}
          />
        </div>

        {/* Center — Editor */}
        <div
          className="w-[40%] flex-shrink-0 border-r border-clay-200 flex flex-col overflow-hidden"
          data-testid="question-editor-pane"
        >
          <QuestionEditor
            question={selectedQuestion}
            options={selectedOptions}
            paperId={pyq_paper_id}
            sections={sections}
            stimuli={stimuli}
            canEdit={canEdit}
            canReview={canReview}
            linkRefreshKey={linkRefreshKey}
            onMutated={handleStimuliMutated}
            onSaved={handleSaved}
            onStatusChange={handleStatusChange}
            onNavigate={navigateQuestion}
            onOpenDoc={handleOpenDoc}
          />
        </div>

        {/* Right — PDF preview */}
        <div
          className="flex-1 flex flex-col overflow-hidden"
          data-testid="pdf-preview-pane"
        >
          <PdfPreview
            documentId={pdfDocumentId}
            paperId={pyq_paper_id}
            sourcePage={pdfPage}
          />
        </div>
      </div>

      {/* Passages / stimuli panel (migration 223, PR-3) */}
      <StimuliPanel
        stimuli={stimuli}
        loading={stimuliLoading}
        error={stimuliError}
        sectionLabelById={sectionLabelById}
        sections={sections}
        canEdit={canEdit}
        canReview={canReview}
        selectedQuestionId={selectedQuestion?.id || null}
        paperId={pyq_paper_id}
        refreshKey={linkRefreshKey}
        onMutated={handleStimuliMutated}
      />

      {/* Add missing modal */}
      {showAddMissing && (
        <AddMissingModal
          paperId={pyq_paper_id}
          initialNumber={addMissingNumber}
          onClose={() => setShowAddMissing(false)}
          onCreated={handleCreatedQuestion}
        />
      )}
    </div>
  );
}
