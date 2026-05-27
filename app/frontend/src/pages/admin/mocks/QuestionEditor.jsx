import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api";
import TagPicker from "./components/TagPicker";
import SourceEditor from "./components/SourceEditor";
import DedupWarning from "./components/DedupWarning";
import StatusBadge from "./components/StatusBadge";
import { ArrowLeft, Plus, Save, Trash2 } from "lucide-react";

// ---------- state machine ----------
const TRANSITIONS = {
  draft:         ["submit"],
  in_review:     ["approve", "request_changes"],
  needs_changes: ["submit"],
  verified:      ["publish", "archive"],
  published:     ["archive"],
  archived:      [],
};

const ACTION_META = {
  submit:          { label: "Submit for Review",  bg: "#2563eb" },
  approve:         { label: "Approve (Verified)", bg: "#16a34a" },
  request_changes: { label: "Request Changes",    bg: "#d97706" },
  publish:         { label: "Publish",            bg: "#7c3aed" },
  archive:         { label: "Archive",            bg: "#4b5563" },
};

const ACTION_ENDPOINT = {
  submit:          "submit",
  approve:         "approve",
  request_changes: "request-changes",
  publish:         "publish",
  archive:         "archive",
};

// ---------- form skeleton ----------
const EMPTY_FORM = {
  question_text: "",
  difficulty: "medium",
  language: "en",
  is_conceptual: false,
  is_factual: false,
  is_current_event: false,
  valid_from: "",
  valid_until: "",
  options: [
    { option_text: "", is_correct: false },
    { option_text: "", is_correct: false },
    { option_text: "", is_correct: false },
    { option_text: "", is_correct: false },
  ],
  tags: [],
  sources: [],
};

// ---------- styles ----------
const S = {
  page:       { padding: 24, color: "#e5e7eb", minHeight: "100vh" },
  header:     { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 },
  breadcrumb: { display: "flex", alignItems: "center", gap: 6, color: "#6b7280", fontSize: 13, marginBottom: 6 },
  title:      { fontSize: 20, fontWeight: 700, color: "#f9fafb", margin: 0 },
  layout:     { display: "grid", gridTemplateColumns: "1fr 300px", gap: 20, alignItems: "start" },
  card:       { background: "#111827", borderRadius: 8, border: "1px solid #1f2937", padding: 18, marginBottom: 14 },
  cardTitle:  { fontSize: 12, fontWeight: 600, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 14, marginTop: 0 },
  label:      { fontSize: 11, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 5, display: "block" },
  input:      { background: "#0f172a", border: "1px solid #374151", borderRadius: 6, padding: "7px 11px", color: "#e5e7eb", fontSize: 14, width: "100%", boxSizing: "border-box" },
  textarea:   { background: "#0f172a", border: "1px solid #374151", borderRadius: 6, padding: "8px 12px", color: "#e5e7eb", fontSize: 14, width: "100%", boxSizing: "border-box", resize: "vertical" },
  select:     { background: "#0f172a", border: "1px solid #374151", borderRadius: 6, padding: "7px 11px", color: "#e5e7eb", fontSize: 14, width: "100%", cursor: "pointer" },
  btn:        { display: "inline-flex", alignItems: "center", gap: 6, border: "none", borderRadius: 6, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer", color: "#fff" },
  iconBtn:    { background: "none", border: "none", cursor: "pointer", color: "#6b7280", padding: 4, display: "flex", alignItems: "center" },
  optionRow:  { display: "flex", alignItems: "center", gap: 8, marginBottom: 8 },
  error:      { background: "#450a0a", border: "1px solid #dc2626", borderRadius: 6, padding: "10px 14px", marginBottom: 14, color: "#fca5a5", fontSize: 13 },
  logEntry:   { paddingBottom: 10, marginBottom: 10 },
  logSep:     { borderBottom: "1px solid #1f2937" },
};

// ---------- component ----------
export default function QuestionEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = id === "new";
  // A route like /admin/mocks/questions/undefined means the caller built the
  // URL from a missing id. Never issue an API call with that — bounce back to
  // the list instead of letting the backend 422/500 on a bad UUID.
  const invalidId = !isNew && (!id || id === "undefined" || id === "null");

  const [form,    setForm]    = useState(EMPTY_FORM);
  const [qStatus, setQStatus] = useState("draft");
  const [reviewLog, setReviewLog] = useState([]);

  const [loading,      setLoading]      = useState(!isNew);
  const [saving,       setSaving]       = useState(false);
  const [error,        setError]        = useState(null);

  const [dedupResult,   setDedupResult]   = useState(null);
  const [dedupDismissed, setDedupDismissed] = useState(false);

  const [showNotesFor,    setShowNotesFor]    = useState(null); // action key
  const [transitionNotes, setTransitionNotes] = useState("");
  const [transitioning,   setTransitioning]   = useState(null);

  const dedupTimer = useRef(null);

  // ── invalid id guard ────────────────────────────────────────────────────────
  useEffect(() => {
    if (invalidId) navigate("/admin/mocks/questions", { replace: true });
  }, [invalidId, navigate]);

  // ── load ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (isNew || invalidId) return;
    setLoading(true);
    api.get(`/api/admin/mocks/questions/${id}`)
      .then((q) => {
        setQStatus(q.reviewer_status || "draft");
        setReviewLog(q.review_log || []);
        setForm({
          question_text:   q.question_text   || "",
          difficulty:      q.difficulty      || "medium",
          language:        q.language        || "en",
          is_conceptual:   !!q.is_conceptual,
          is_factual:      !!q.is_factual,
          is_current_event: !!q.is_current_event,
          valid_from:  q.valid_from  ? q.valid_from.slice(0, 10)  : "",
          valid_until: q.valid_until ? q.valid_until.slice(0, 10) : "",
          options:  (q.options  || []).map((o) => ({ option_text: o.option_text, is_correct: !!o.is_correct })),
          tags:     q.tags    || [],
          sources:  q.sources || [],
        });
      })
      .catch((e) => setError(e?.message || "Failed to load question"))
      .finally(() => setLoading(false));
  }, [id, isNew, invalidId]);

  // ── debounced dedup (edit mode only) ─────────────────────────────────────
  useEffect(() => {
    if (isNew || invalidId || !id || form.question_text.length < 20) return;
    clearTimeout(dedupTimer.current);
    dedupTimer.current = setTimeout(() => {
      api.post(`/api/admin/mocks/questions/${id}/dedup-check`, {})
        .then((res) => { setDedupResult(res); setDedupDismissed(false); })
        .catch(() => {});
    }, 600);
    return () => clearTimeout(dedupTimer.current);
  }, [form.question_text, id, isNew, invalidId]);

  // ── options helpers ───────────────────────────────────────────────────────
  const setCorrect = (idx) =>
    setForm((f) => ({ ...f, options: f.options.map((o, i) => ({ ...o, is_correct: i === idx })) }));

  const updateOption = (idx, text) =>
    setForm((f) => ({ ...f, options: f.options.map((o, i) => i === idx ? { ...o, option_text: text } : o) }));

  const addOption = () => {
    if (form.options.length >= 6) return;
    setForm((f) => ({ ...f, options: [...f.options, { option_text: "", is_correct: false }] }));
  };

  const removeOption = (idx) => {
    if (form.options.length <= 2) return;
    setForm((f) => {
      const next = f.options.filter((_, i) => i !== idx);
      const hasCorrect = next.some((o) => o.is_correct);
      return { ...f, options: hasCorrect ? next : next.map((o, i) => ({ ...o, is_correct: i === 0 })) };
    });
  };

  // ── validate ──────────────────────────────────────────────────────────────
  const validate = () => {
    if (!form.question_text.trim())
      return "Question text is required.";
    const filledOptions = form.options.filter((o) => o.option_text.trim());
    if (filledOptions.length < 2)
      return "At least 2 options are required.";
    if (!form.options.some((o) => o.is_correct))
      return "Select a correct answer.";
    if (!form.is_conceptual && !form.is_factual && !form.is_current_event)
      return "Select at least one cognitive tag.";
    if (form.sources.length === 0)
      return "At least one source is required.";
    if (dedupResult?.fingerprint_match && !dedupDismissed)
      return "Exact duplicate detected — save blocked.";
    return null;
  };

  // ── save ──────────────────────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    const validationError = validate();
    if (validationError) { setError(validationError); return; }

    setSaving(true);
    setError(null);

    const body = {
      question_text:    form.question_text,
      difficulty:       form.difficulty,
      language:         form.language,
      is_conceptual:    form.is_conceptual,
      is_factual:       form.is_factual,
      is_current_event: form.is_current_event,
      valid_from:       form.valid_from  || null,
      valid_until:      form.valid_until || null,
      options:          form.options.filter((o) => o.option_text.trim()),
      tags:             form.tags.map(({ topic_id, role }) => ({ topic_id, role })),
      sources:          form.sources,
    };

    try {
      if (isNew) {
        const created = await api.post("/api/admin/mocks/questions", body);
        navigate(`/admin/mocks/questions/${created.id}`, { replace: true });
      } else {
        await api.patch(`/api/admin/mocks/questions/${id}`, body);
        // Refresh log after save
        const q = await api.get(`/api/admin/mocks/questions/${id}`);
        setReviewLog(q.review_log || []);
        setDedupResult(null);
        setDedupDismissed(false);
      }
    } catch (e) {
      setError(e?.message || "Save failed");
    } finally {
      setSaving(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form, id, isNew, navigate, dedupResult, dedupDismissed]);

  // ── transitions ───────────────────────────────────────────────────────────
  const handleTransition = useCallback(async (action, notes) => {
    setTransitioning(action);
    setError(null);
    try {
      await api.post(`/api/admin/mocks/questions/${id}/${ACTION_ENDPOINT[action]}`, { notes: notes || "" });
      const q = await api.get(`/api/admin/mocks/questions/${id}`);
      setQStatus(q.reviewer_status);
      setReviewLog(q.review_log || []);
      setShowNotesFor(null);
      setTransitionNotes("");
    } catch (e) {
      setError(e?.message || `Action "${action}" failed`);
    } finally {
      setTransitioning(null);
    }
  }, [id]);

  // ── render ────────────────────────────────────────────────────────────────
  if (invalidId) {
    return (
      <div style={S.page}>
        <div style={S.error}>Invalid question id — returning to the question bank…</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ ...S.page, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ color: "#6b7280" }}>Loading…</span>
      </div>
    );
  }

  const isSaveBlocked = saving || (dedupResult?.fingerprint_match && !dedupDismissed);
  const currentTransitions = TRANSITIONS[qStatus] || [];

  return (
    <div style={S.page}>
      {/* ── header ── */}
      <div style={S.header}>
        <div>
          <div style={S.breadcrumb}>
            <Link to="/admin/mocks/questions" style={{ color: "#6b7280", textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>
              <ArrowLeft size={13} /> Question Bank
            </Link>
          </div>
          <h1 style={S.title}>{isNew ? "New Question" : "Edit Question"}</h1>
        </div>
        <button
          onClick={handleSave}
          disabled={isSaveBlocked}
          style={{ ...S.btn, background: isSaveBlocked ? "#374151" : "#2563eb", cursor: isSaveBlocked ? "not-allowed" : "pointer" }}
        >
          <Save size={14} />
          {saving ? "Saving…" : "Save"}
        </button>
      </div>

      {/* ── error banner ── */}
      {error && (
        <div style={S.error}>
          {error}
          <button onClick={() => setError(null)} style={{ float: "right", background: "none", border: "none", color: "#fca5a5", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>×</button>
        </div>
      )}

      {/* ── dedup warning ── */}
      {dedupResult && !dedupDismissed && (
        <DedupWarning result={dedupResult} onDismiss={() => setDedupDismissed(true)} />
      )}

      {/* ── notes modal ── */}
      {showNotesFor && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.65)", zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ background: "#1f2937", borderRadius: 10, padding: 24, width: 440, border: "1px solid #374151" }}>
            <h3 style={{ margin: "0 0 14px", color: "#f9fafb", fontSize: 16 }}>
              {ACTION_META[showNotesFor]?.label}
            </h3>
            <label style={S.label}>Notes (optional)</label>
            <textarea
              value={transitionNotes}
              onChange={(e) => setTransitionNotes(e.target.value)}
              placeholder="Reason or review notes…"
              style={{ ...S.textarea, marginBottom: 16, minHeight: 72 }}
              autoFocus
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                onClick={() => { setShowNotesFor(null); setTransitionNotes(""); }}
                style={{ ...S.btn, background: "#374151" }}
              >
                Cancel
              </button>
              <button
                onClick={() => handleTransition(showNotesFor, transitionNotes)}
                disabled={!!transitioning}
                style={{ ...S.btn, background: ACTION_META[showNotesFor]?.bg || "#2563eb", opacity: transitioning ? 0.6 : 1 }}
              >
                {transitioning ? "…" : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── two-column layout ── */}
      <div style={S.layout}>

        {/* ════ LEFT: form ════ */}
        <div>

          {/* Question text */}
          <div style={S.card}>
            <p style={S.cardTitle}>Question</p>
            <textarea
              value={form.question_text}
              onChange={(e) => setForm((f) => ({ ...f, question_text: e.target.value }))}
              placeholder="Enter the question text…"
              style={{ ...S.textarea, minHeight: 100 }}
            />
          </div>

          {/* Options */}
          <div style={S.card}>
            <p style={S.cardTitle}>Answer Options</p>
            {form.options.map((opt, i) => (
              <div key={i} style={S.optionRow}>
                <input
                  type="radio"
                  name="correct_option"
                  checked={opt.is_correct}
                  onChange={() => setCorrect(i)}
                  title="Mark as correct answer"
                  style={{ cursor: "pointer", accentColor: "#22c55e", flexShrink: 0, width: 16, height: 16 }}
                />
                <input
                  value={opt.option_text}
                  onChange={(e) => updateOption(i, e.target.value)}
                  placeholder={`Option ${String.fromCharCode(65 + i)}`}
                  style={{ ...S.input, flex: 1 }}
                />
                {form.options.length > 2 && (
                  <button onClick={() => removeOption(i)} style={S.iconBtn} title="Remove option">
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            ))}
            {form.options.length < 6 && (
              <button
                onClick={addOption}
                style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "1px dashed #374151", borderRadius: 6, padding: "6px 12px", color: "#6b7280", fontSize: 13, cursor: "pointer", marginTop: 4 }}
              >
                <Plus size={13} /> Add option
              </button>
            )}
            <p style={{ fontSize: 12, color: "#4b5563", margin: "8px 0 0" }}>
              Click the radio button next to the correct answer.
            </p>
          </div>

          {/* Metadata */}
          <div style={S.card}>
            <p style={S.cardTitle}>Metadata</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
              <div>
                <label style={S.label}>Difficulty</label>
                <select value={form.difficulty} onChange={(e) => setForm((f) => ({ ...f, difficulty: e.target.value }))} style={S.select}>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>
              <div>
                <label style={S.label}>Language</label>
                <select value={form.language} onChange={(e) => setForm((f) => ({ ...f, language: e.target.value }))} style={S.select}>
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                </select>
              </div>
            </div>

            <label style={S.label}>
              Cognitive Tags <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
              {[
                ["is_conceptual",    "Conceptual"],
                ["is_factual",       "Factual"],
                ["is_current_event", "Current Event"],
              ].map(([key, lbl]) => (
                <label key={key} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 13, color: "#d1d5db" }}>
                  <input
                    type="checkbox"
                    checked={form[key]}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.checked }))}
                    style={{ cursor: "pointer", accentColor: "#2563eb" }}
                  />
                  {lbl}
                </label>
              ))}
            </div>

            {form.is_current_event && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 14 }}>
                <div>
                  <label style={S.label}>Valid From</label>
                  <input type="date" value={form.valid_from} onChange={(e) => setForm((f) => ({ ...f, valid_from: e.target.value }))} style={S.input} />
                </div>
                <div>
                  <label style={S.label}>Valid Until</label>
                  <input type="date" value={form.valid_until} onChange={(e) => setForm((f) => ({ ...f, valid_until: e.target.value }))} style={S.input} />
                </div>
              </div>
            )}
          </div>

          {/* Topic Tags */}
          <div style={S.card}>
            <p style={S.cardTitle}>Topic Tags</p>
            <TagPicker value={form.tags} onChange={(tags) => setForm((f) => ({ ...f, tags }))} />
          </div>

          {/* Sources */}
          <div style={S.card}>
            <p style={S.cardTitle}>
              Sources <span style={{ color: "#ef4444" }}>*</span>
            </p>
            <SourceEditor value={form.sources} onChange={(sources) => setForm((f) => ({ ...f, sources }))} />
          </div>
        </div>

        {/* ════ RIGHT RAIL ════ */}
        <div style={{ position: "sticky", top: 24 }}>

          {/* Status + transitions */}
          <div style={S.card}>
            <p style={S.cardTitle}>Workflow</p>
            <div style={{ marginBottom: 14 }}>
              <StatusBadge status={qStatus} />
            </div>

            {isNew ? (
              <p style={{ fontSize: 13, color: "#6b7280", margin: 0 }}>
                Save first to access workflow transitions.
              </p>
            ) : currentTransitions.length === 0 ? (
              <p style={{ fontSize: 13, color: "#6b7280", margin: 0 }}>
                No further transitions available.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {currentTransitions.map((action) => (
                  <button
                    key={action}
                    onClick={() => setShowNotesFor(action)}
                    disabled={!!transitioning}
                    style={{
                      ...S.btn,
                      background: ACTION_META[action]?.bg || "#374151",
                      justifyContent: "center",
                      opacity: transitioning ? 0.6 : 1,
                      cursor: transitioning ? "not-allowed" : "pointer",
                    }}
                  >
                    {transitioning === action ? "…" : ACTION_META[action]?.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Review log */}
          {reviewLog.length > 0 && (
            <div style={S.card}>
              <p style={S.cardTitle}>Review Log</p>
              <div style={{ maxHeight: 380, overflowY: "auto" }}>
                {reviewLog.map((entry, i) => (
                  <div
                    key={i}
                    style={{
                      ...S.logEntry,
                      ...(i < reviewLog.length - 1 ? S.logSep : {}),
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 3 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: "#e5e7eb", textTransform: "capitalize" }}>
                        {(entry.action || "").replace(/_/g, " ")}
                      </span>
                      <span style={{ fontSize: 11, color: "#6b7280", flexShrink: 0, marginLeft: 8 }}>
                        {entry.created_at ? new Date(entry.created_at).toLocaleDateString() : ""}
                      </span>
                    </div>
                    {entry.from_status && (
                      <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 3 }}>
                        {entry.from_status} → {entry.to_status}
                      </div>
                    )}
                    {entry.notes && (
                      <div style={{ fontSize: 12, color: "#9ca3af", fontStyle: "italic", marginBottom: 2 }}>
                        "{entry.notes}"
                      </div>
                    )}
                    {entry.actor_id && (
                      <div style={{ fontSize: 11, color: "#4b5563" }}>
                        {entry.actor_id.slice(0, 8)}…
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
