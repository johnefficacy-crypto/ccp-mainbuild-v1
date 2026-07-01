import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { api, getApiErrorMessage } from "../../../../lib/api";
import { useAuth } from "../../../../lib/authContext";

/**
 * J2-A — Manage Exam operational editor for topics + aliases, scoped to
 * one exam's covered subjects.
 *
 * Governance (docs/status/Manage-Exam-Operational-Editors-Gate-2026-07-01.md §D):
 * - Rendered only when the user holds `exam_intelligence.manage` (or is
 *   super_admin). The surrounding Syllabus tab stays open to review users;
 *   only this editor sub-panel is gated (rule 2).
 * - All writes go to the `manage`-gated endpoints under
 *   /api/admin/exam-intelligence-manage and carry a reason (rule 3).
 * - Fail-closed: writes are blocked until the exam's subjects resolve and a
 *   subject is selected (inherits the J1 scope-safety posture).
 * - Prerequisite editing (J2-A′) is intentionally absent — blocked pending a
 *   prerequisite-semantics gate.
 */
const BASE = "/api/admin/exam-intelligence-manage";
const LEVELS = ["topic", "microtopic", "concept"];

export default function SyllabusTopicEditorPanel({ examId }) {
  const { user } = useAuth();
  const canManage =
    user?.role === "super_admin" ||
    user?.permissions?.includes("exam_intelligence.manage");

  // Scope resolution state machine (idle | resolving | valid | error).
  const [subjectState, setSubjectState] = useState("idle");
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState("");

  const [topics, setTopics] = useState([]);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  const [status, setStatus] = useState(null); // { ok, message }
  const [form, setForm] = useState(null); // create/edit topic form
  const [aliasTopic, setAliasTopic] = useState(null); // topic whose aliases are open

  const writesBlocked = subjectState !== "valid" || !subjectId;

  // Resolve the exam's covered subjects (OD-4). Fail-closed while resolving.
  useEffect(() => {
    if (!canManage || !examId) return;
    let cancelled = false;
    setSubjectState("resolving");
    setSubjects([]);
    setSubjectId("");
    (async () => {
      try {
        const r = await api.get(`${BASE}/exams/${examId}/subjects`);
        if (cancelled) return;
        const items = r?.items || [];
        setSubjects(items);
        setSubjectId(items[0]?.id || "");
        setSubjectState("valid");
      } catch (e) {
        if (!cancelled) {
          setSubjectState("error");
          setStatus({ ok: false, message: getApiErrorMessage(e) });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [canManage, examId]);

  // Debounce the search input (300 ms, gate C.3).
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  const loadTopics = useCallback(async () => {
    if (!examId || !subjectId) { setTopics([]); return; }
    setTopicsLoading(true);
    try {
      const params = new URLSearchParams({ exam_id: examId, subject_id: subjectId, limit: "50" });
      if (debouncedSearch) params.set("q", debouncedSearch);
      const r = await api.get(`${BASE}/topics?${params}`);
      setTopics(r?.items || []);
    } catch (e) {
      setStatus({ ok: false, message: getApiErrorMessage(e) });
    } finally {
      setTopicsLoading(false);
    }
  }, [examId, subjectId, debouncedSearch]);

  useEffect(() => { loadTopics(); }, [loadTopics]);

  async function submitTopic(e) {
    e.preventDefault();
    if (writesBlocked || !form) {
      setStatus({ ok: false, message: "Scope is unresolved — write blocked." });
      return;
    }
    const reason = (form.reason || "").trim();
    if (reason.length < 8) {
      setStatus({ ok: false, message: "A reason of at least 8 characters is required." });
      return;
    }
    const payload = {
      subject_id: subjectId,
      slug: form.slug,
      name: form.name,
      level: form.level || "topic",
      description: form.description || null,
    };
    try {
      if (form.id) {
        // Edit: never resend subject_id/slug identity churn beyond what changed.
        await api.patch(`${BASE}/topics/${form.id}?exam_id=${examId}`, {
          reason, payload: { name: form.name, description: form.description || null, level: form.level },
        });
      } else {
        await api.post(`${BASE}/topics?exam_id=${examId}`, { reason, payload });
      }
      setStatus({ ok: true, message: form.id ? "Topic updated." : "Topic created." });
      setForm(null);
      loadTopics();
    } catch (e) {
      setStatus({ ok: false, message: getApiErrorMessage(e) });
    }
  }

  async function deleteTopic(t) {
    if (writesBlocked) return;
    const reason = window.prompt(`Delete "${t.name}"? Enter a reason (min 8 chars):`, "");
    if (!reason || reason.trim().length < 8) return;
    try {
      await api.del(`${BASE}/topics/${t.id}?exam_id=${examId}&reason=${encodeURIComponent(reason.trim())}`);
      setStatus({ ok: true, message: "Topic deleted." });
      loadTopics();
    } catch (e) {
      setStatus({ ok: false, message: getApiErrorMessage(e) });
    }
  }

  if (!canManage) return null;

  return (
    <div className="border-b border-gray-200 bg-slate-50 px-4 py-3" data-testid="syllabus-topic-editor">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-600">
          Manage topics
        </span>
        <label htmlFor="ste-subject" className="text-sm text-slate-600">Subject</label>
        <select
          id="ste-subject"
          className="text-sm border rounded px-2 py-1"
          value={subjectId}
          onChange={(e) => setSubjectId(e.target.value)}
          disabled={subjectState !== "valid" || subjects.length === 0}
          data-testid="ste-subject-select"
        >
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <input
          type="search"
          className="text-sm border rounded px-2 py-1"
          placeholder="Search topics…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search topics"
          data-testid="ste-search"
        />
        <button
          type="button"
          className="text-sm px-2 py-1 border rounded bg-white disabled:opacity-40 ml-auto"
          onClick={() => setForm({ level: "topic", reason: "" })}
          disabled={writesBlocked}
          data-testid="ste-new-topic"
        >
          + New topic
        </button>
      </div>

      {subjectState === "resolving" && (
        <div className="text-sm text-slate-400 mt-2" data-testid="ste-resolving">Resolving subjects…</div>
      )}
      {subjectState === "error" && (
        <div className="text-sm text-rose-600 mt-2" role="alert" data-testid="ste-scope-error">
          Could not resolve this exam&apos;s subjects. Editing is blocked.
        </div>
      )}
      {subjectState === "valid" && subjects.length === 0 && (
        <div className="text-sm text-slate-500 mt-2" data-testid="ste-empty-subjects">
          No subjects are mapped to this exam yet. Map topic coverage before editing topics.
        </div>
      )}

      {status && (
        <div
          className={`text-sm mt-2 ${status.ok ? "text-emerald-700" : "text-rose-600"}`}
          role="status"
          data-testid="ste-status"
        >
          {status.message}
        </div>
      )}

      {subjectState === "valid" && subjectId && (
        <div className="mt-2">
          {topicsLoading ? (
            <div className="text-sm text-slate-400" data-testid="ste-topics-loading">Loading topics…</div>
          ) : (
            <ul className="text-sm divide-y divide-slate-100 max-h-56 overflow-y-auto bg-white rounded border border-slate-200" data-testid="ste-topic-list">
              {topics.length === 0 && (
                <li className="px-3 py-2 text-slate-400" data-testid="ste-no-topics">No topics.</li>
              )}
              {topics.map((t) => (
                <li key={t.id} className="px-3 py-2 flex items-center gap-2" data-testid={`ste-topic-${t.id}`}>
                  <span className="flex-1">
                    {t.name} <span className="text-slate-400">· {t.level}</span>
                  </span>
                  <button
                    type="button"
                    className="text-xs px-2 py-0.5 border rounded disabled:opacity-40"
                    onClick={() => setForm({ id: t.id, name: t.name, slug: t.slug, level: t.level, description: t.description || "", reason: "" })}
                    disabled={writesBlocked}
                    data-testid={`ste-edit-${t.id}`}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="text-xs px-2 py-0.5 border rounded disabled:opacity-40"
                    onClick={() => setAliasTopic(aliasTopic?.id === t.id ? null : t)}
                    data-testid={`ste-aliases-${t.id}`}
                  >
                    Aliases
                  </button>
                  <button
                    type="button"
                    className="text-xs px-2 py-0.5 border rounded text-rose-600 disabled:opacity-40"
                    onClick={() => deleteTopic(t)}
                    disabled={writesBlocked}
                    data-testid={`ste-delete-${t.id}`}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {form && (
        <form className="mt-3 bg-white border border-slate-200 rounded p-3 space-y-2" onSubmit={submitTopic} data-testid="ste-form">
          <div className="text-xs font-semibold text-slate-600">{form.id ? "Edit topic" : "New topic"}</div>
          <div className="flex gap-2 flex-wrap">
            <input
              className="text-sm border rounded px-2 py-1 flex-1" placeholder="name" required
              value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })}
              aria-label="Topic name" data-testid="ste-form-name"
            />
            <input
              className="text-sm border rounded px-2 py-1" placeholder="slug" required disabled={!!form.id}
              value={form.slug || ""} onChange={(e) => setForm({ ...form, slug: e.target.value })}
              aria-label="Topic slug" data-testid="ste-form-slug"
            />
            <select
              className="text-sm border rounded px-2 py-1" value={form.level || "topic"}
              onChange={(e) => setForm({ ...form, level: e.target.value })} aria-label="Topic level"
              data-testid="ste-form-level"
            >
              {LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
          <textarea
            className="text-sm border rounded px-2 py-1 w-full" placeholder="description (optional)" rows={2}
            value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })}
            aria-label="Topic description" data-testid="ste-form-description"
          />
          <input
            className="text-sm border rounded px-2 py-1 w-full" placeholder="reason (min 8 chars, audited)" required
            value={form.reason || ""} onChange={(e) => setForm({ ...form, reason: e.target.value })}
            aria-label="Reason" data-testid="ste-form-reason"
          />
          <div className="flex gap-2">
            <button type="submit" className="text-sm px-3 py-1 border rounded bg-slate-800 text-white disabled:opacity-40" disabled={writesBlocked} data-testid="ste-form-save">
              Save
            </button>
            <button type="button" className="text-sm px-3 py-1 border rounded" onClick={() => setForm(null)} data-testid="ste-form-cancel">
              Cancel
            </button>
          </div>
        </form>
      )}

      {aliasTopic && (
        <AliasEditor
          examId={examId}
          topic={aliasTopic}
          writesBlocked={writesBlocked}
          onStatus={setStatus}
        />
      )}
    </div>
  );
}

SyllabusTopicEditorPanel.propTypes = {
  examId: PropTypes.string,
};

function AliasEditor({ examId, topic, writesBlocked, onStatus }) {
  const [aliases, setAliases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newAlias, setNewAlias] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ exam_id: examId, topic_id: topic.id, limit: "50" });
      const r = await api.get(`${BASE}/topic-aliases?${params}`);
      setAliases(r?.items || []);
    } catch (e) {
      onStatus({ ok: false, message: getApiErrorMessage(e) });
    } finally {
      setLoading(false);
    }
  }, [examId, topic.id, onStatus]);

  useEffect(() => { load(); }, [load]);

  async function addAlias() {
    if (writesBlocked || !newAlias.trim()) return;
    try {
      await api.post(`${BASE}/topic-aliases?exam_id=${examId}`, {
        reason: `add alias for ${topic.name}`,
        payload: { topic_id: topic.id, alias: newAlias.trim() },
      });
      setNewAlias("");
      load();
    } catch (e) {
      onStatus({ ok: false, message: getApiErrorMessage(e) });
    }
  }

  async function removeAlias(a) {
    if (writesBlocked) return;
    const reason = window.prompt(`Remove alias "${a.alias}"? Reason (min 8 chars):`, "");
    if (!reason || reason.trim().length < 8) return;
    try {
      await api.del(`${BASE}/topic-aliases/${a.id}?exam_id=${examId}&reason=${encodeURIComponent(reason.trim())}`);
      load();
    } catch (e) {
      onStatus({ ok: false, message: getApiErrorMessage(e) });
    }
  }

  return (
    <div className="mt-3 bg-white border border-slate-200 rounded p-3" data-testid="ste-alias-editor">
      <div className="text-xs font-semibold text-slate-600 mb-2">Aliases · {topic.name}</div>
      {loading ? (
        <div className="text-sm text-slate-400">Loading…</div>
      ) : (
        <ul className="text-sm divide-y divide-slate-100 mb-2" data-testid="ste-alias-list">
          {aliases.length === 0 && <li className="py-1 text-slate-400">No aliases.</li>}
          {aliases.map((a) => (
            <li key={a.id} className="py-1 flex items-center gap-2" data-testid={`ste-alias-${a.id}`}>
              <span className="flex-1">{a.alias}</span>
              <button
                type="button"
                className="text-xs px-2 py-0.5 border rounded text-rose-600 disabled:opacity-40"
                onClick={() => removeAlias(a)}
                disabled={writesBlocked}
                data-testid={`ste-alias-remove-${a.id}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <input
          className="text-sm border rounded px-2 py-1 flex-1"
          placeholder="new alias"
          value={newAlias}
          onChange={(e) => setNewAlias(e.target.value)}
          aria-label="New alias"
          data-testid="ste-alias-input"
        />
        <button
          type="button"
          className="text-sm px-3 py-1 border rounded disabled:opacity-40"
          onClick={addAlias}
          disabled={writesBlocked || !newAlias.trim()}
          data-testid="ste-alias-add"
        >
          Add
        </button>
      </div>
    </div>
  );
}

AliasEditor.propTypes = {
  examId: PropTypes.string,
  topic: PropTypes.object.isRequired,
  writesBlocked: PropTypes.bool,
  onStatus: PropTypes.func.isRequired,
};
