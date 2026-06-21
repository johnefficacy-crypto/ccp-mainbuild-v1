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
import { ChevronLeft, ChevronRight, Copy, ExternalLink } from "lucide-react";
import { api } from "../../../lib/api";

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

  // source_kind is client-side only (not supported by server filter).
  // reviewer_status is handled server-side; questions already filtered.
  const filtered = questions.filter((q) => {
    if (sourceKindFilter !== "all" && (q.source_kind || "manual") !== sourceKindFilter) return false;
    return true;
  });

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

function OptionsEditor({ questionId, initialOptions, onSaved }) {
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
        <div key={opt.id || idx} className="flex items-start gap-2">
          <span className="w-6 flex-shrink-0 text-[12px] font-bold text-clay-600 mt-1.5">
            [{opt.option_label}]
          </span>
          <input
            className="flex-1 border border-clay-200 rounded px-2 py-1 text-sm bg-white"
            value={opt.option_text || ""}
            onChange={(e) => updateOption(idx, { option_text: e.target.value })}
            onBlur={() => saveOption(opt, idx)}
            placeholder="Option text…"
          />
          <label className="flex items-center gap-1 text-[11px] text-clay-600 mt-1.5">
            <input
              type="checkbox"
              checked={!!opt.is_correct}
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
          <button type="button" className="underline text-clay-700" onClick={startAdd}>
            Add options
          </button>
        </p>
      )}
      {options.length > 0 && options.length < 6 && (
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

// ── Center pane ───────────────────────────────────────────────────────────────

function QuestionEditor({
  question,
  options,
  paperId,
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
        />
      </div>

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

// ── Main component ────────────────────────────────────────────────────────────

export default function PyqPaperWorkspace({ paperId: paperIdProp, embedded = false }) {
  const { pyq_paper_id: pyq_paper_id_param } = useParams();
  const pyq_paper_id = paperIdProp || pyq_paper_id_param;
  const navigate = useNavigate();

  const [paper, setPaper] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [selectedOptions, setSelectedOptions] = useState([]);

  const [progress, setProgress] = useState(null);

  const [statusFilter, setStatusFilter] = useState("all");
  const [sourceKindFilter, setSourceKindFilter] = useState("all");

  // Pagination state
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(null);

  const [pdfDocumentId, setPdfDocumentId] = useState(null);
  const [pdfPage, setPdfPage] = useState(null);

  const [showAddMissing, setShowAddMissing] = useState(false);
  const [addMissingNumber, setAddMissingNumber] = useState(null);

  // ── Data loading ─────────────────────────────────────────────────────────

  const loadPaper = useCallback(async () => {
    if (!pyq_paper_id) return;
    try {
      const res = await api.get(`${CMS_BASE}/pyq-papers/${encodeURIComponent(pyq_paper_id)}`);
      setPaper(res || null);
    } catch {
      /* best-effort */
    }
  }, [pyq_paper_id]);

  // Returns the fetched items so callers can act on them without waiting for
  // the async state update (setQuestions is enqueued, not synchronous).
  const loadQuestions = useCallback(async () => {
    setLoadError("");
    try {
      const params = new URLSearchParams({
        pyq_paper_id: pyq_paper_id,
        limit: String(PAGE_SIZE),
        offset: String(offset),
      });
      if (statusFilter !== "all") params.set("reviewer_status", statusFilter);
      const res = await api.get(`${CMS_BASE}/pyq-questions?${params}`);
      const items = res.items || [];
      setQuestions(items);
      setTotal(res.total ?? null);
      return items;
    } catch (e) {
      setLoadError(e?.message || "Could not load questions");
      return [];
    }
  }, [pyq_paper_id, offset, statusFilter]);

  const loadProgress = useCallback(async () => {
    try {
      const res = await api.get(
        `${CMS_BASE}/pyq-papers/${encodeURIComponent(pyq_paper_id)}/progress`,
      );
      setProgress(res);
    } catch {
      /* best-effort */
    }
  }, [pyq_paper_id]);

  const loadOptions = useCallback(async (questionId) => {
    if (!questionId) {
      setSelectedOptions([]);
      return;
    }
    try {
      const res = await api.get(
        `${CMS_BASE}/pyq-options?question_id=${encodeURIComponent(questionId)}&limit=10`,
      );
      setSelectedOptions(res.items || []);
    } catch {
      setSelectedOptions([]);
    }
  }, []);

  // Reload when paper changes (initial load) or when offset/statusFilter changes
  // (loadQuestions closes over offset + statusFilter; loadPaper/loadProgress are
  // stable unless pyq_paper_id changes, so extra fetches of paper/progress on
  // pagination are intentional — progress reflects live server counts).
  useEffect(() => {
    setLoading(true);
    Promise.all([loadPaper(), loadQuestions(), loadProgress()]).finally(() =>
      setLoading(false),
    );
  }, [loadPaper, loadQuestions, loadProgress]);

  // ── Filter handlers — reset offset so results are correct ───────────────

  function handleStatusFilterChange(value) {
    setStatusFilter(value);
    setOffset(0);
  }

  // ── Pagination ───────────────────────────────────────────────────────────

  function handlePageChange(newOffset) {
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
    const visible = questions.filter((q) =>
      sourceKindFilter === "all" || (q.source_kind || "manual") === sourceKindFilter,
    );
    const idx = visible.findIndex((q) => q.id === selectedQuestion?.id);
    const next = visible[idx + delta];
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
            setSourceKindFilter={setSourceKindFilter}
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
