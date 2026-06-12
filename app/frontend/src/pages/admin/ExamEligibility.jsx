import React, { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, GraduationCap, Plus, ShieldCheck, X } from "lucide-react";
import { api } from "../../lib/api";
import { LoadingSkeleton } from "../../shared/ui/core";
import useApiAction from "../../lib/hooks/useApiAction";

const SCOPES = ["all", "general", "obc", "sc", "st", "ews", "pwd", "ex_serviceman", "women"];
const RULE_TYPES = ["age_min", "age_max", "education_min_level", "nationality", "gender", "attempts_max"];
const NUMERIC_TYPES = new Set(["age_min", "age_max", "attempts_max"]);
const TEXT_TYPES = new Set(["education_min_level", "nationality", "gender"]);
const STATUSES = ["draft", "verified", "archived"];

function StatusPill({ status }) {
  const tone =
    status === "verified" ? "pill-sage"
    : status === "draft" ? "pill-amber"
    : "pill-dusk";
  return <span className={`pill ${tone}`} data-testid={`status-${status}`}>{status}</span>;
}

function emptyRuleForm(examId) {
  return {
    exam_id: examId,
    scope: "all",
    rule_type: "age_max",
    value_num: "",
    value_text: "",
    source_url: "",
    source_notes: "",
    reviewer_status: "draft",
    is_knockout: true,
  };
}

function ConfirmDialog({ type, rule, onClose, onConfirm }) {
  const [reason, setReason] = useState("");
  const [sourceUrl, setSourceUrl] = useState(rule?.source_url || "");
  const [sourceUnavailable, setSourceUnavailable] = useState(false);
  const [localError, setLocalError] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    setLocalError("");
    const trimmed = reason.trim();
    if (trimmed.length < 8) {
      setLocalError("Reason must be at least 8 characters.");
      return;
    }
    if (trimmed.length > 500) {
      setLocalError("Reason must be 500 characters or fewer.");
      return;
    }
    if (type === "verify" && !sourceUnavailable && !sourceUrl.trim()) {
      setLocalError("Provide a source URL or check 'Source unavailable'.");
      return;
    }
    onConfirm({
      reason: trimmed,
      sourceUrl: sourceUnavailable ? null : sourceUrl.trim() || null,
    });
  }

  const isVerify = type === "verify";
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      data-testid="confirm-dialog"
    >
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md space-y-4">
        <h2 className="font-heading text-lg font-semibold">
          {isVerify ? "Verify rule" : "Archive rule"}
        </h2>
        <p className="text-sm text-muted-foreground">
          {isVerify
            ? "Verified rules immediately feed the user-facing eligibility summary. Confirm this rule is correct."
            : "Archiving removes this rule from the live eligibility summary. The row is retained for audit."}
        </p>
        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block text-sm">
            <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
              Reason{" "}
              <span className="font-normal normal-case tracking-normal">(8–500 chars)</span>
            </div>
            <textarea
              data-testid="dialog-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-clay-300 bg-white text-sm"
              placeholder={
                isVerify
                  ? "Confirmed against official notification…"
                  : "Superseded by updated regulation…"
              }
            />
          </label>
          {isVerify && (
            <>
              <label className="block text-sm">
                <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                  Source URL
                </div>
                <input
                  type="url"
                  data-testid="dialog-source-url"
                  value={sourceUrl}
                  disabled={sourceUnavailable}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  placeholder="https://upsc.gov.in/…"
                  className="w-full px-3 py-2 rounded-lg border border-clay-300 bg-white text-sm disabled:opacity-40"
                />
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
                <input
                  type="checkbox"
                  data-testid="dialog-source-unavailable"
                  checked={sourceUnavailable}
                  onChange={(e) => setSourceUnavailable(e.target.checked)}
                  className="h-4 w-4 rounded"
                />
                Source unavailable — waive URL requirement
              </label>
            </>
          )}
          {localError && (
            <div className="text-sm text-destructive" data-testid="dialog-error">
              {localError}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="btn btn-ghost">
              Cancel
            </button>
            <button
              type="submit"
              data-testid="dialog-confirm"
              className={`btn ${isVerify ? "btn-primary" : "btn-destructive"}`}
            >
              {isVerify ? "Confirm verify" : "Confirm archive"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function AuditTimeline({ ruleId }) {
  const [status, setStatus] = useState("loading");
  const [items, setItems] = useState([]);

  useEffect(() => {
    setStatus("loading");
    api
      .get(`/api/admin/audit?entity_type=exam_eligibility_rule&entity_id=${ruleId}`)
      .then((d) => {
        setItems(Array.isArray(d?.items) ? d.items : []);
        setStatus("done");
      })
      .catch(() => setStatus("error"));
  }, [ruleId]);

  if (status === "loading") {
    return <div className="py-2 text-xs text-muted-foreground">Loading history…</div>;
  }
  if (status === "error" || items.length === 0) {
    return (
      <div className="py-2 text-xs text-muted-foreground italic" data-testid="audit-empty">
        No recorded history
      </div>
    );
  }

  return (
    <ol className="text-xs space-y-1 border-l-2 border-clay-200 pl-3 mt-1" data-testid="audit-list">
      {items.map((entry) => (
        <li key={entry.id}>
          <span className="font-mono text-muted-foreground mr-2">
            {new Date(entry.created_at).toLocaleDateString()}
          </span>
          <span className="font-semibold">{entry.action}</span>
          {entry.actor_email && (
            <span className="text-muted-foreground ml-1">by {entry.actor_email}</span>
          )}
          {entry.notes && (
            <span className="text-muted-foreground ml-1">— {entry.notes}</span>
          )}
        </li>
      ))}
    </ol>
  );
}

export default function AdminExamEligibility() {
  const [exams, setExams] = useState(null);
  const [selectedExamId, setSelectedExamId] = useState("");
  const [rules, setRules] = useState([]);
  const [exam, setExam] = useState(null);
  const [form, setForm] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const [confirmDialog, setConfirmDialog] = useState(null);
  const [expandedRuleId, setExpandedRuleId] = useState(null);

  const { run: runSave, busy: saveBusy } = useApiAction();
  const { run: runVerify } = useApiAction();
  const { run: runArchive } = useApiAction();

  useEffect(() => {
    refreshExams();
  }, []);

  useEffect(() => {
    if (selectedExamId) refreshRules(selectedExamId);
  }, [selectedExamId]);

  async function refreshExams() {
    setError("");
    try {
      const d = await api.get("/api/admin/exam-eligibility/exams");
      setExams(Array.isArray(d?.items) ? d.items : []);
    } catch (e) {
      setError(e?.message || "Failed to load exams");
      setExams([]);
    }
  }

  async function refreshRules(examId) {
    setError("");
    try {
      const d = await api.get(`/api/admin/exam-eligibility/exams/${examId}/rules`);
      setExam(d?.exam || null);
      setRules(Array.isArray(d?.rules) ? d.rules : []);
    } catch (e) {
      setError(e?.message || "Failed to load rules");
      setRules([]);
      setExam(null);
    }
  }

  function openNewRule() {
    setEditingId(null);
    setForm(emptyRuleForm(selectedExamId));
  }

  function openEditRule(rule) {
    setEditingId(rule.id);
    setForm({
      ...rule,
      value_num: rule.value_num == null ? "" : String(rule.value_num),
      value_text: rule.value_text || "",
      source_url: rule.source_url || "",
      source_notes: rule.source_notes || "",
    });
  }

  function closeForm() {
    setEditingId(null);
    setForm(null);
  }

  async function submitForm(e) {
    e.preventDefault();
    setError("");
    const payload = {
      scope: form.scope,
      rule_type: form.rule_type,
      is_knockout: !!form.is_knockout,
      reviewer_status: form.reviewer_status,
      source_url: form.source_url || null,
      source_notes: form.source_notes || null,
    };
    if (NUMERIC_TYPES.has(form.rule_type)) {
      const raw = String(form.value_num ?? "").trim();
      const n = Number(raw);
      if (!raw || !Number.isFinite(n)) {
        setError(`${form.rule_type} requires a numeric value`);
        return;
      }
      payload.value_num = n;
    } else if (TEXT_TYPES.has(form.rule_type)) {
      if (!form.value_text) {
        setError(`${form.rule_type} requires a text value`);
        return;
      }
      payload.value_text = form.value_text;
    }

    const endpoint = editingId
      ? `/api/admin/exam-eligibility/rules/${editingId}`
      : `/api/admin/exam-eligibility/exams/${selectedExamId}/rules`;
    const method = editingId ? "put" : "post";

    const { ok, error: apiError } = await runSave({
      action: () => api[method](endpoint, payload),
      onSuccess: async () => {
        closeForm();
        await refreshRules(selectedExamId);
        await refreshExams();
      },
      errorMessage: editingId ? "Save failed" : "Create failed",
    });
    if (!ok) {
      const detail = apiError?.detail;
      if (detail && typeof detail === "object" && detail.code === "RULE_ALREADY_EXISTS") {
        setError("A rule with this scope and type already exists. Edit the existing row.");
      } else if (typeof detail === "string") {
        setError(detail);
      }
    }
  }

  async function handleDialogConfirm({ reason, sourceUrl }) {
    const { type, rule } = confirmDialog;
    setConfirmDialog(null);
    setError("");

    if (type === "verify") {
      const { ok, error: apiError } = await runVerify({
        action: () =>
          api.put(`/api/admin/exam-eligibility/rules/${rule.id}`, {
            reviewer_status: "verified",
            source_url: sourceUrl || null,
            waiver_reason: reason,
          }),
        onSuccess: async () => {
          await refreshRules(selectedExamId);
          await refreshExams();
        },
        successMessage: "Rule verified.",
        errorMessage: "Verify failed.",
      });
      if (!ok) {
        const detail = apiError?.detail;
        if (typeof detail === "string") setError(detail);
      }
    } else {
      const qs = new URLSearchParams({ waiver_reason: reason }).toString();
      const { ok, error: apiError } = await runArchive({
        action: () =>
          api.del(`/api/admin/exam-eligibility/rules/${rule.id}?${qs}`),
        onSuccess: async () => {
          await refreshRules(selectedExamId);
          await refreshExams();
        },
        successMessage: "Rule archived.",
        errorMessage: "Archive failed.",
      });
      if (!ok) {
        const detail = apiError?.detail;
        if (typeof detail === "string") setError(detail);
      }
    }
  }

  if (exams === null) {
    return (
      <div className="space-y-4" data-testid="admin-exam-eligibility">
        <LoadingSkeleton variant="cards" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-exam-eligibility">
      {confirmDialog && (
        <ConfirmDialog
          type={confirmDialog.type}
          rule={confirmDialog.rule}
          onClose={() => setConfirmDialog(null)}
          onConfirm={handleDialogConfirm}
        />
      )}

      <div>
        <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground font-semibold">
          Knowledge governance
        </div>
        <h1 className="mt-1 font-heading text-3xl font-semibold tracking-tight">
          Exam eligibility rules
        </h1>
        <p className="text-muted-foreground mt-1">
          The baseline rules that decide which exams a user is shown as eligible for.
          Only <strong>verified</strong> rows feed the user-facing summary.
        </p>
      </div>

      {error && (
        <div
          role="status"
          className="rounded-xl bg-destructive/10 border border-destructive/30 text-destructive text-sm px-3 py-2"
          data-testid="admin-exam-eligibility-error"
        >
          {error}
        </div>
      )}

      <div className="grid md:grid-cols-[260px_1fr] gap-4">
        {/* Left: exam list */}
        <div className="soft-card rounded-2xl p-3" data-testid="exam-list">
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground px-2 pt-1 pb-3">
            Exams ({exams.length})
          </div>
          <div className="space-y-1">
            {exams.map((e) => (
              <button
                key={e.id}
                type="button"
                onClick={() => setSelectedExamId(e.id)}
                data-testid={`exam-row-${e.slug}`}
                className={`w-full text-left rounded-xl px-3 py-2 text-sm ${
                  selectedExamId === e.id ? "bg-clay-100 text-clay-900" : "hover:bg-white/60"
                }`}
              >
                <div className="font-semibold flex items-center gap-2">
                  <GraduationCap className="h-3.5 w-3.5 text-clay-700" />
                  {e.name}
                </div>
                <div className="text-[11px] text-muted-foreground mt-1">
                  {e.rule_counts.verified} verified · {e.rule_counts.draft} draft
                  {e.rule_counts.archived ? ` · ${e.rule_counts.archived} archived` : ""}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Right: rules panel */}
        <div className="soft-card rounded-2xl p-4" data-testid="rules-panel">
          {!selectedExamId ? (
            <div className="text-sm text-muted-foreground p-6 text-center">
              Select an exam on the left to view and edit its eligibility rules.
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between gap-3 mb-4">
                <div>
                  <div className="font-heading text-xl font-semibold">{exam?.name}</div>
                  <div className="text-[11px] text-muted-foreground font-mono">{exam?.slug}</div>
                </div>
                <button
                  type="button"
                  onClick={openNewRule}
                  className="btn btn-primary"
                  data-testid="new-rule-btn"
                >
                  <Plus className="h-3.5 w-3.5" /> New rule
                </button>
              </div>

              {form && (
                <form
                  onSubmit={submitForm}
                  className="rounded-xl border border-clay-300 bg-white/70 p-4 mb-4 space-y-3"
                  data-testid="rule-form"
                >
                  <div className="grid sm:grid-cols-2 gap-3">
                    <label className="text-sm">
                      <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                        Scope
                      </div>
                      <select
                        data-testid="rule-form-scope"
                        value={form.scope}
                        onChange={(e) => setForm({ ...form, scope: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-clay-300 bg-white text-sm"
                      >
                        {SCOPES.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </label>
                    <label className="text-sm">
                      <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                        Rule type
                      </div>
                      <select
                        data-testid="rule-form-type"
                        value={form.rule_type}
                        onChange={(e) =>
                          setForm({ ...form, rule_type: e.target.value, value_num: "", value_text: "" })
                        }
                        className="w-full px-3 py-2 rounded-lg border border-clay-300 bg-white text-sm"
                      >
                        {RULE_TYPES.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </label>
                    {NUMERIC_TYPES.has(form.rule_type) ? (
                      <label className="text-sm sm:col-span-2">
                        <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                          Numeric value
                        </div>
                        <input
                          type="number"
                          data-testid="rule-form-value-num"
                          value={form.value_num}
                          onChange={(e) => setForm({ ...form, value_num: e.target.value })}
                          className="w-full px-3 py-2 rounded-lg border border-clay-300 bg-white text-sm"
                        />
                      </label>
                    ) : (
                      <label className="text-sm sm:col-span-2">
                        <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                          Text value
                        </div>
                        <input
                          type="text"
                          data-testid="rule-form-value-text"
                          value={form.value_text}
                          onChange={(e) => setForm({ ...form, value_text: e.target.value })}
                          placeholder="e.g. graduation"
                          className="w-full px-3 py-2 rounded-lg border border-clay-300 bg-white text-sm"
                        />
                      </label>
                    )}
                    <label className="text-sm">
                      <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                        Reviewer status
                      </div>
                      <select
                        data-testid="rule-form-status"
                        value={form.reviewer_status}
                        onChange={(e) => setForm({ ...form, reviewer_status: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-clay-300 bg-white text-sm"
                      >
                        {STATUSES.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </label>
                    <label className="text-sm">
                      <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                        Source URL
                      </div>
                      <input
                        type="url"
                        data-testid="rule-form-source-url"
                        value={form.source_url}
                        onChange={(e) => setForm({ ...form, source_url: e.target.value })}
                        placeholder="https://upsc.gov.in/..."
                        className="w-full px-3 py-2 rounded-lg border border-clay-300 bg-white text-sm"
                      />
                    </label>
                    <label className="text-sm sm:col-span-2">
                      <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                        Source notes
                      </div>
                      <textarea
                        data-testid="rule-form-source-notes"
                        value={form.source_notes}
                        onChange={(e) => setForm({ ...form, source_notes: e.target.value })}
                        rows={2}
                        className="w-full px-3 py-2 rounded-lg border border-clay-300 bg-white text-sm"
                      />
                    </label>
                  </div>
                  <div className="flex items-center justify-end gap-2">
                    <button type="button" onClick={closeForm} className="btn btn-ghost">
                      Cancel
                    </button>
                    <button
                      type="submit"
                      data-testid="rule-form-submit"
                      className="btn btn-primary"
                      disabled={saveBusy}
                    >
                      {editingId ? "Save changes" : "Create rule"}
                    </button>
                  </div>
                </form>
              )}

              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="rules-table">
                  <thead className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    <tr className="border-b border-clay-200">
                      <th className="text-left py-2 pr-3">Scope</th>
                      <th className="text-left py-2 pr-3">Rule type</th>
                      <th className="text-left py-2 pr-3">Value</th>
                      <th className="text-left py-2 pr-3">Status</th>
                      <th className="text-left py-2 pr-3">Source</th>
                      <th className="text-left py-2 pr-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rules.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-6 text-center text-muted-foreground">
                          No rules yet. Click <strong>New rule</strong> to add one.
                        </td>
                      </tr>
                    )}
                    {rules.map((r) => (
                      <React.Fragment key={r.id}>
                        <tr
                          className="border-b border-clay-100/60 hover:bg-white/40"
                          data-testid={`rule-row-${r.id}`}
                        >
                          <td className="py-2 pr-3 font-mono text-xs">{r.scope}</td>
                          <td className="py-2 pr-3 font-mono text-xs">{r.rule_type}</td>
                          <td className="py-2 pr-3">
                            {r.value_num != null ? r.value_num : r.value_text}
                          </td>
                          <td className="py-2 pr-3">
                            <StatusPill status={r.reviewer_status} />
                          </td>
                          <td className="py-2 pr-3 text-xs">
                            {r.source_url ? (
                              <a
                                href={r.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="link-under"
                              >
                                source
                              </a>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </td>
                          <td className="py-2 pr-3">
                            <div className="flex items-center gap-2 flex-wrap">
                              <button
                                type="button"
                                onClick={() => openEditRule(r)}
                                className="text-xs link-under"
                              >
                                edit
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  setExpandedRuleId(expandedRuleId === r.id ? null : r.id)
                                }
                                className="text-xs link-under text-muted-foreground"
                                data-testid={`history-${r.id}`}
                                aria-expanded={expandedRuleId === r.id}
                              >
                                {expandedRuleId === r.id ? (
                                  <ChevronDown className="inline h-3 w-3" />
                                ) : (
                                  <ChevronRight className="inline h-3 w-3" />
                                )}{" "}
                                history
                              </button>
                              {r.reviewer_status !== "verified" && (
                                <button
                                  type="button"
                                  onClick={() => setConfirmDialog({ type: "verify", rule: r })}
                                  className="text-xs link-under text-sage-700"
                                  data-testid={`verify-${r.id}`}
                                >
                                  <ShieldCheck className="inline h-3 w-3" /> verify
                                </button>
                              )}
                              {r.reviewer_status !== "archived" && (
                                <button
                                  type="button"
                                  onClick={() => setConfirmDialog({ type: "archive", rule: r })}
                                  aria-label={`Archive rule ${r.scope} ${r.rule_type}`}
                                  className="text-xs link-under text-destructive"
                                  data-testid={`archive-${r.id}`}
                                >
                                  <X className="inline h-3 w-3" /> archive
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                        {expandedRuleId === r.id && (
                          <tr data-testid={`audit-row-${r.id}`}>
                            <td colSpan={6} className="px-3 pb-3 bg-white/30">
                              <AuditTimeline ruleId={r.id} />
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
