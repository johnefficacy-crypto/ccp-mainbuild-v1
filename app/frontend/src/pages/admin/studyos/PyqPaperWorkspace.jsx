import React, { useEffect, useState, useCallback } from "react";
import { ChevronRight, RotateCcw, Plus, Search } from "lucide-react";
import { api, getApiErrorMessage } from "../../../lib/api";

const PYQ_QUESTION_TYPES = ["mcq", "numerical", "descriptive", "caselet", "matching", "other"];
const PYQ_OBSERVED_DIFFICULTY = ["easy", "moderate", "hard"];
const PYQ_OPTION_LABELS = ["A", "B", "C", "D", "E"];

const STATUS_CHIP = {
  verified: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
  needs_correction: "bg-amber-100 text-amber-800",
  pending: "bg-muted text-muted-foreground",
};

// Jaccard word-overlap used for client-side duplicate surfacing.
// Only runs on saved (server) question text — never on live keystrokes.
function _similarity(a, b) {
  if (!a || !b) return 0;
  const words = (s) =>
    new Set(
      s
        .toLowerCase()
        .replace(/[^a-z0-9 ]/g, " ")
        .split(/\s+/)
        .filter((w) => w.length > 3),
    );
  const wa = words(a);
  const wb = words(b);
  if (!wa.size && !wb.size) return 0;
  const inter = [...wa].filter((w) => wb.has(w)).length;
  const union = new Set([...wa, ...wb]).size;
  return union ? inter / union : 0;
}

// ─── QuestionEditor ──────────────────────────────────────────────────────────
// Safety invariants:
//   1. Form resets only when question.id changes (keyed on server identity),
//      so option-only parent re-renders never overwrite unsaved edits.
//   2. questionDirty tracks question_text divergence from the saved server
//      value and is reported upward via onDirtyChange so OptionsEditor can
//      block unsafe option adds without reading internal form state.
//   3. saveDraft() returns boolean; handleVerify short-circuits on failure.
//   4. Dup check runs only after a successful saveDraft, against server text.
function QuestionEditor({ question, allQuestions, onSaved, onStatusChanged, onDirtyChange }) {
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [reviewing, setReviewing] = useState(false);
  const [reviewError, setReviewError] = useState(null);
  const [dups, setDups] = useState(null);

  // Reset form only when the question id changes, not on every re-render.
  // This is the critical invariant: option saves must not overwrite local edits.
  useEffect(() => {
    if (!question) {
      setForm({});
      setDups(null);
      return;
    }
    setForm({
      question_text: question.question_text ?? "",
      question_type: question.question_type ?? "",
      observed_difficulty: question.observed_difficulty ?? "",
      question_number: question.question_number ?? "",
      explanation_text: question.explanation_text ?? "",
      language: question.language ?? "",
    });
    setSaveError(null);
    setReviewError(null);
    setDups(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question?.id]);

  const questionDirty =
    !!question && form.question_text !== (question.question_text ?? "");

  useEffect(() => {
    onDirtyChange?.(questionDirty);
  }, [questionDirty, onDirtyChange]);

  async function saveDraft() {
    if (!question) return false;
    setSaving(true);
    setSaveError(null);
    try {
      const patch = {};
      const q = question;
      if (form.question_text !== (q.question_text ?? "")) patch.question_text = form.question_text;
      if ((form.question_type || null) !== (q.question_type || null)) patch.question_type = form.question_type || null;
      if ((form.observed_difficulty || null) !== (q.observed_difficulty || null)) patch.observed_difficulty = form.observed_difficulty || null;
      const qn = form.question_number !== "" ? Number(form.question_number) : null;
      if (qn !== (q.question_number ?? null)) patch.question_number = qn;
      if ((form.explanation_text || "") !== (q.explanation_text ?? "")) patch.explanation_text = form.explanation_text;
      if ((form.language || "") !== (q.language ?? "")) patch.language = form.language;

      if (!Object.keys(patch).length) return true;

      const r = await api.patch(
        `/api/admin/exam-intelligence-cms/pyq-questions/${q.id}`,
        { reason: "workspace draft save", payload: patch },
      );
      const saved = r.row ?? { ...q, ...patch };
      onSaved(saved);
      // Dup check runs after save using the now-confirmed server text.
      runDupCheck(saved.question_text, saved.id);
      return true;
    } catch (e) {
      setSaveError(getApiErrorMessage(e));
      return false;
    } finally {
      setSaving(false);
    }
  }

  function runDupCheck(savedText, selfId) {
    if (!savedText || savedText.length < 20) { setDups([]); return; }
    const results = (allQuestions || [])
      .filter((q) => q.id !== selfId)
      .map((q) => ({ q, score: _similarity(savedText, q.question_text) }))
      .filter(({ score }) => score >= 0.5)
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);
    setDups(results);
  }

  async function handleVerify() {
    const ok = await saveDraft();
    if (!ok) return;
    setReviewing(true);
    setReviewError(null);
    try {
      await api.patch(
        `/api/admin/exam-intelligence/items/pyq_question/${question.id}/review`,
        { reviewer_status: "verified" },
      );
      onStatusChanged(question.id, "verified");
    } catch (e) {
      setReviewError(getApiErrorMessage(e));
    } finally {
      setReviewing(false);
    }
  }

  async function handleSetStatus(status) {
    setReviewing(true);
    setReviewError(null);
    try {
      await api.patch(
        `/api/admin/exam-intelligence/items/pyq_question/${question.id}/review`,
        { reviewer_status: status },
      );
      onStatusChanged(question.id, status);
    } catch (e) {
      setReviewError(getApiErrorMessage(e));
    } finally {
      setReviewing(false);
    }
  }

  if (!question) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
        Select a question from the list.
      </div>
    );
  }

  const busy = saving || reviewing;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="text-xs font-mono text-muted-foreground">
          Q{question.question_number || "?"} · {question.id?.slice(0, 8)}…
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_CHIP[question.reviewer_status] ?? STATUS_CHIP.pending}`}>
          {question.reviewer_status || "pending"}
        </span>
      </div>

      <label className="block">
        <span className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
          Question text
          {questionDirty && (
            <span className="text-amber-600 font-medium">· unsaved</span>
          )}
        </span>
        <textarea
          value={form.question_text ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, question_text: e.target.value }))}
          rows={5}
          className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background font-mono"
          data-testid="qeditor-question-text"
        />
      </label>

      <div className="grid grid-cols-3 gap-2">
        <label className="block">
          <span className="block text-xs text-muted-foreground mb-1">Type</span>
          <select
            value={form.question_type ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, question_type: e.target.value }))}
            className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
            data-testid="qeditor-question-type"
          >
            <option value="">(skip)</option>
            {PYQ_QUESTION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="block text-xs text-muted-foreground mb-1">Difficulty</span>
          <select
            value={form.observed_difficulty ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, observed_difficulty: e.target.value }))}
            className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
            data-testid="qeditor-difficulty"
          >
            <option value="">(skip)</option>
            {PYQ_OBSERVED_DIFFICULTY.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="block text-xs text-muted-foreground mb-1">Q#</span>
          <input
            type="number"
            value={form.question_number ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, question_number: e.target.value }))}
            className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
            data-testid="qeditor-question-number"
          />
        </label>
      </div>

      <label className="block">
        <span className="block text-xs text-muted-foreground mb-1">Explanation</span>
        <textarea
          value={form.explanation_text ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, explanation_text: e.target.value }))}
          rows={2}
          className="w-full px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
          data-testid="qeditor-explanation"
        />
      </label>

      {saveError && <div className="text-sm text-red-700" role="alert">{saveError}</div>}
      {reviewError && <div className="text-sm text-red-700" role="alert">{reviewError}</div>}

      <div className="flex gap-2 flex-wrap">
        <button type="button" className="btn small" onClick={saveDraft} disabled={busy} data-testid="qeditor-save">
          {saving ? "Saving…" : "Save draft"}
        </button>
        <button type="button" className="btn small" onClick={handleVerify} disabled={busy} data-testid="qeditor-verify">
          {reviewing ? "Working…" : "Verify"}
        </button>
        <button type="button" className="btn small" onClick={() => handleSetStatus("rejected")} disabled={busy} data-testid="qeditor-reject">
          Reject
        </button>
        <button type="button" className="btn small" onClick={() => handleSetStatus("needs_correction")} disabled={busy} data-testid="qeditor-needs-correction">
          Needs correction
        </button>
        <button
          type="button"
          className="btn small ml-auto"
          onClick={() => runDupCheck(question.question_text, question.id)}
          disabled={questionDirty}
          title={questionDirty ? "Save before checking duplicates" : "Check for similar questions in this paper"}
          data-testid="qeditor-check-dups"
        >
          <Search className="h-3 w-3" /> Check dups
        </button>
      </div>

      {dups !== null && (
        <div className="rounded border border-border/60 p-2 space-y-1" data-testid="qeditor-dup-panel">
          <div className="text-xs font-medium text-muted-foreground">
            {dups.length === 0 ? "No similar questions found in this paper." : `${dups.length} similar question(s) found:`}
          </div>
          {dups.map(({ q, score }) => (
            <div key={q.id} className="text-xs bg-amber-50 border border-amber-200 rounded p-2">
              <span className="font-mono text-amber-700">{Math.round(score * 100)}% match</span>
              {" · "}Q{q.question_number || "?"}
              {": "}
              <span className="text-muted-foreground line-clamp-2">{q.question_text?.slice(0, 120)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-1 text-xs text-muted-foreground">
        {questionDirty
          ? "Save draft before adding options or checking duplicates to prevent state rollback."
          : null}
      </div>
    </div>
  );
}

// ─── OptionsEditor ────────────────────────────────────────────────────────────
// Safety invariants:
//   1. onSavedOption only triggers an options-only reload, never loadQuestions().
//   2. Adding a new option is blocked while questionDirty is true.
//   3. is_correct checkbox fires an immediate PATCH on change, not just on blur.
function OptionsEditor({ question, options, questionDirty, onSavedOption }) {
  const [adding, setAdding] = useState(false);
  const [newLabel, setNewLabel] = useState("");
  const [newText, setNewText] = useState("");
  const [newCorrect, setNewCorrect] = useState(false);
  const [savingId, setSavingId] = useState(null);
  const [optionError, setOptionError] = useState(null);

  function startAdd() {
    if (questionDirty) return; // blocked — caller should surface a warning
    const used = new Set((options || []).map((o) => o.option_label));
    const next = PYQ_OPTION_LABELS.find((l) => !used.has(l)) ?? "";
    setNewLabel(next);
    setNewText("");
    setNewCorrect(false);
    setAdding(true);
    setOptionError(null);
  }

  async function submitNewOption() {
    if (!question || !newLabel || !newText.trim()) return;
    setSavingId("new");
    setOptionError(null);
    try {
      await api.post("/api/admin/exam-intelligence-cms/pyq-options", {
        reason: "workspace option add",
        payload: {
          question_id: question.id,
          option_label: newLabel,
          option_text: newText.trim(),
          is_correct: newCorrect,
        },
      });
      setAdding(false);
      setNewLabel("");
      setNewText("");
      setNewCorrect(false);
      // Only reload options — never the question list.
      onSavedOption();
    } catch (e) {
      setOptionError(getApiErrorMessage(e));
    } finally {
      setSavingId(null);
    }
  }

  async function saveOptionText(opt, text) {
    if (text === opt.option_text) return;
    setSavingId(opt.id);
    setOptionError(null);
    try {
      await api.patch(`/api/admin/exam-intelligence-cms/pyq-options/${opt.id}`, {
        reason: "workspace option text edit",
        payload: { option_text: text },
      });
      onSavedOption(); // options-only reload
    } catch (e) {
      setOptionError(getApiErrorMessage(e));
    } finally {
      setSavingId(null);
    }
  }

  async function toggleCorrect(opt) {
    setSavingId(opt.id);
    setOptionError(null);
    try {
      await api.patch(`/api/admin/exam-intelligence-cms/pyq-options/${opt.id}`, {
        reason: "workspace option correct toggle",
        payload: { is_correct: !opt.is_correct },
      });
      onSavedOption(); // options-only reload
    } catch (e) {
      setOptionError(getApiErrorMessage(e));
    } finally {
      setSavingId(null);
    }
  }

  if (!question) return null;

  return (
    <div className="space-y-2" data-testid="options-editor">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">Options</span>
        <button
          type="button"
          className="btn small"
          onClick={startAdd}
          disabled={questionDirty || adding}
          title={questionDirty ? "Save question text before adding options" : "Add option"}
          data-testid="options-add-btn"
        >
          <Plus className="h-3 w-3" /> Add option
        </button>
      </div>

      {questionDirty && (
        <p className="text-xs text-amber-700" role="alert" data-testid="options-dirty-warning">
          Save question text first — adding options now would reset your unsaved edits.
        </p>
      )}

      {(options || []).map((opt) => (
        <div key={opt.id} className="flex items-start gap-2 rounded border border-border/40 p-2">
          <span className="text-xs font-bold w-5 shrink-0 mt-1">{opt.option_label}</span>
          <input
            type="text"
            defaultValue={opt.option_text ?? ""}
            onBlur={(e) => saveOptionText(opt, e.target.value)}
            disabled={savingId === opt.id}
            className="flex-1 px-2 py-1 text-sm border border-border/60 rounded bg-background"
            data-testid={`option-text-${opt.option_label}`}
          />
          <label className="flex items-center gap-1 text-xs shrink-0 mt-1 cursor-pointer">
            <input
              type="checkbox"
              checked={!!opt.is_correct}
              onChange={() => toggleCorrect(opt)}
              disabled={savingId === opt.id}
              data-testid={`option-correct-${opt.option_label}`}
            />
            correct
          </label>
          {savingId === opt.id && (
            <span className="text-xs text-muted-foreground shrink-0 mt-1">saving…</span>
          )}
        </div>
      ))}

      {adding && (
        <div className="rounded border border-sky-300/60 bg-card p-2 space-y-2" data-testid="new-option-form">
          <div className="flex items-center gap-2">
            <select
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              className="w-16 px-2 py-1 text-sm border border-border/60 rounded bg-background"
              data-testid="new-option-label"
            >
              <option value="">(label)</option>
              {PYQ_OPTION_LABELS.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
            <input
              type="text"
              value={newText}
              onChange={(e) => setNewText(e.target.value)}
              placeholder="Option text"
              className="flex-1 px-2 py-1 text-sm border border-border/60 rounded bg-background"
              data-testid="new-option-text"
            />
            <label className="flex items-center gap-1 text-xs shrink-0 cursor-pointer">
              <input
                type="checkbox"
                checked={newCorrect}
                onChange={(e) => setNewCorrect(e.target.checked)}
                data-testid="new-option-correct"
              />
              correct
            </label>
          </div>
          <div className="flex gap-2">
            <button type="button" className="btn small" onClick={submitNewOption} disabled={savingId === "new" || !newLabel || !newText.trim()} data-testid="new-option-submit">
              {savingId === "new" ? "Saving…" : "Save option"}
            </button>
            <button type="button" className="btn small" onClick={() => setAdding(false)} data-testid="new-option-cancel">
              Cancel
            </button>
          </div>
          {optionError && <div className="text-sm text-red-700" role="alert">{optionError}</div>}
        </div>
      )}

      {optionError && !adding && (
        <div className="text-sm text-red-700" role="alert">{optionError}</div>
      )}
    </div>
  );
}

// ─── PyqPaperWorkspace (root) ─────────────────────────────────────────────────
export default function PyqPaperWorkspace() {
  const [exams, setExams] = useState([]);
  const [examId, setExamId] = useState("");
  const [papers, setPapers] = useState([]);
  const [paperId, setPaperId] = useState("");
  const [questions, setQuestions] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [options, setOptions] = useState([]);
  const [loadingQ, setLoadingQ] = useState(false);
  const [loadingOpts, setLoadingOpts] = useState(false);
  const [err, setErr] = useState(null);
  // Lifted from QuestionEditor so OptionsEditor can block adds while dirty.
  const [questionDirty, setQuestionDirty] = useState(false);

  const selectedQuestion = questions.find((q) => q.id === selectedId) ?? null;

  // Load exam list once
  useEffect(() => {
    api
      .get("/api/admin/exam-intelligence-cms/exams?limit=200")
      .then((r) => setExams(r.items || []))
      .catch(() => {});
  }, []);

  // Load papers when exam changes
  useEffect(() => {
    setPapers([]);
    setPaperId("");
    setQuestions([]);
    setSelectedId(null);
    setOptions([]);
    if (!examId) return;
    api
      .get(`/api/admin/exam-intelligence-cms/pyq-papers?exam_id=${examId}&limit=200`)
      .then((r) => setPapers(r.items || []))
      .catch(() => {});
  }, [examId]);

  const loadQuestions = useCallback(async (pid) => {
    if (!pid) return;
    setLoadingQ(true);
    setErr(null);
    try {
      const r = await api.get(
        `/api/admin/exam-intelligence-cms/pyq-questions?pyq_paper_id=${pid}&limit=200`,
      );
      setQuestions(r.items || []);
    } catch (e) {
      setErr(getApiErrorMessage(e));
    } finally {
      setLoadingQ(false);
    }
  }, []);

  // Load options for selected question only (not tied to question list reload).
  const loadOptions = useCallback(async (qid) => {
    if (!qid) { setOptions([]); return; }
    setLoadingOpts(true);
    try {
      const r = await api.get(
        `/api/admin/exam-intelligence-cms/pyq-options?question_id=${qid}&limit=20`,
      );
      setOptions(r.items || []);
    } catch {
      // silently degrade — options are a sub-resource, not critical
    } finally {
      setLoadingOpts(false);
    }
  }, []);

  // Load questions when paper changes
  useEffect(() => {
    setQuestions([]);
    setSelectedId(null);
    setOptions([]);
    if (!paperId) return;
    loadQuestions(paperId);
  }, [paperId, loadQuestions]);

  // Load options when selected question changes; reset dirty state.
  useEffect(() => {
    setQuestionDirty(false);
    loadOptions(selectedId);
  }, [selectedId, loadOptions]);

  function handleQuestionSaved(savedRow) {
    // Update the question in-place in the list without triggering a full reload.
    // This keeps the left-panel list current without blowing away local edits
    // in any other components sharing question data.
    setQuestions((prev) =>
      prev.map((q) => (q.id === savedRow.id ? { ...q, ...savedRow } : q)),
    );
  }

  function handleStatusChanged(qid, status) {
    setQuestions((prev) =>
      prev.map((q) => (q.id === qid ? { ...q, reviewer_status: status } : q)),
    );
  }

  // Options-only refresh: called after any option write.
  // Never calls loadQuestions — that would reset unsaved question_text edits.
  function handleSavedOption() {
    loadOptions(selectedId);
  }

  return (
    <div className="space-y-4" data-testid="pyq-paper-workspace">
      <div>
        <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground font-semibold">
          Study OS · exam intelligence
        </div>
        <h1 className="mt-1 font-heading text-3xl font-semibold tracking-tight">PYQ Paper Workspace</h1>
        <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
          Review and curate PYQ questions and options. Select an exam, then a paper, then a question.
          Save question text before adding options to prevent state rollback.
        </p>
      </div>

      {/* Selectors */}
      <div className="flex gap-3 flex-wrap items-end">
        <label className="block">
          <span className="block text-xs text-muted-foreground mb-1">Exam</span>
          <select
            value={examId}
            onChange={(e) => setExamId(e.target.value)}
            className="px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
            data-testid="workspace-exam-select"
          >
            <option value="">— pick exam —</option>
            {exams.map((e) => (
              <option key={e.id} value={e.id}>{e.name || e.slug}</option>
            ))}
          </select>
        </label>

        {papers.length > 0 && (
          <label className="block">
            <span className="block text-xs text-muted-foreground mb-1">Paper</span>
            <select
              value={paperId}
              onChange={(e) => setPaperId(e.target.value)}
              className="px-2 py-1.5 text-sm border border-border/60 rounded bg-background"
              data-testid="workspace-paper-select"
            >
              <option value="">— pick paper —</option>
              {papers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.paper_code || p.id?.slice(0, 8)} · {p.year}
                </option>
              ))}
            </select>
          </label>
        )}

        {paperId && (
          <button
            type="button"
            className="btn small"
            onClick={() => loadQuestions(paperId)}
            disabled={loadingQ}
            data-testid="workspace-reload-questions"
          >
            <RotateCcw className="h-3 w-3" /> {loadingQ ? "Loading…" : "Reload"}
          </button>
        )}
      </div>

      {err && <div className="text-sm text-red-700" role="alert">{err}</div>}

      {/* Main workspace split */}
      {paperId && (
        <div className="grid grid-cols-[280px_1fr] gap-4 min-h-[400px]">
          {/* Question list */}
          <section className="rounded border border-border/60 bg-card overflow-y-auto max-h-[70vh]" data-testid="question-list">
            {loadingQ ? (
              <div className="p-3 text-xs text-muted-foreground">Loading questions…</div>
            ) : !questions.length ? (
              <div className="p-3 text-xs text-muted-foreground">No questions in this paper.</div>
            ) : (
              questions.map((q) => (
                <button
                  key={q.id}
                  type="button"
                  onClick={() => setSelectedId(q.id)}
                  className={`w-full text-left p-2 border-b border-border/40 text-xs hover:bg-muted/40 transition-colors flex items-start gap-1 ${
                    q.id === selectedId ? "bg-sky-50" : ""
                  }`}
                  data-testid={`question-list-item-${q.id}`}
                >
                  <ChevronRight className={`h-3 w-3 mt-0.5 shrink-0 ${q.id === selectedId ? "text-sky-600" : "text-muted-foreground/50"}`} />
                  <span className="flex-1 space-y-0.5">
                    <span className="flex items-center justify-between gap-1">
                      <span className="font-medium">Q{q.question_number || "?"}</span>
                      <span className={`text-[10px] px-1.5 py-0 rounded-full ${STATUS_CHIP[q.reviewer_status] ?? STATUS_CHIP.pending}`}>
                        {q.reviewer_status || "pending"}
                      </span>
                    </span>
                    <span className="block text-muted-foreground line-clamp-2 leading-snug">
                      {q.question_text?.slice(0, 80) || "—"}
                    </span>
                  </span>
                </button>
              ))
            )}
          </section>

          {/* Editor panel */}
          <section className="space-y-4">
            <div className="rounded border border-border/60 bg-card p-4">
              <QuestionEditor
                question={selectedQuestion}
                allQuestions={questions}
                onSaved={handleQuestionSaved}
                onStatusChanged={handleStatusChanged}
                onDirtyChange={setQuestionDirty}
              />
            </div>

            {selectedQuestion && (
              <div className="rounded border border-border/60 bg-card p-4">
                {loadingOpts ? (
                  <div className="text-xs text-muted-foreground">Loading options…</div>
                ) : (
                  <OptionsEditor
                    question={selectedQuestion}
                    options={options}
                    questionDirty={questionDirty}
                    onSavedOption={handleSavedOption}
                  />
                )}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
