import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { api } from "../../../../lib/api";
import { useAuth } from "../../../../lib/authContext";
import useApiAction from "../../../../lib/hooks/useApiAction";
import TopicEditorForm, { TOPIC_LEVELS } from "../../studyos/editors/TopicEditorForm";
import TopicAliasEditor from "../../studyos/editors/TopicAliasEditor";
import TopicPrerequisiteEditor from "./TopicPrerequisiteEditor";

/**
 * J2-A / J2-A′ — Manage Exam operational editor for topics + aliases +
 * prerequisites, scoped to one exam's covered subjects.
 *
 * Governance (Manage-Exam gate §D; Topic-Prerequisite-Semantics gate §F):
 * - Mounts for canManage || canReview (rule 2 / prereq blocker 2). Topic and
 *   alias mutation controls are manage-only; the prerequisite editor exposes
 *   manage controls to managers and review controls to reviewers.
 * - All mutations run through `useApiAction`. Fail-closed on scope resolution.
 * - Reuses shared components under `pages/admin/studyos/editors/` (OD-3).
 */
const BASE = "/api/admin/exam-intelligence-manage";
const PAGE_SIZE = 50;

export default function SyllabusTopicEditorPanel({ examId }) {
  const { user } = useAuth();
  const canManage =
    user?.role === "super_admin" ||
    user?.permissions?.includes("exam_intelligence.manage");
  const canReview =
    user?.role === "super_admin" ||
    user?.permissions?.includes("exam_intelligence.review");

  const [subjectState, setSubjectState] = useState("idle"); // idle|resolving|valid|error
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState("");

  const [topics, setTopics] = useState([]);
  const [total, setTotal] = useState(null);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [topicsError, setTopicsError] = useState(false);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState("");
  const [page, setPage] = useState(1); // 1-based

  const [form, setForm] = useState(null);
  const [aliasTopic, setAliasTopic] = useState(null);
  const [prereqTopic, setPrereqTopic] = useState(null);

  const topicAction = useApiAction();
  // Fail-closed on a failed topic fetch too: an incomplete/errored list must
  // not let the operator create/edit against stale data (writes blocked).
  const writesBlocked = subjectState !== "valid" || !subjectId || topicsError || topicAction.busy;

  // Resolve the exam's covered subjects (OD-4). Fail-closed while resolving.
  useEffect(() => {
    if ((!canManage && !canReview) || !examId) return;
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
      } catch {
        if (!cancelled) setSubjectState("error");
      }
    })();
    return () => { cancelled = true; };
  }, [canManage, canReview, examId]);

  // Debounce search (300 ms, gate C.3).
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  // Reset to page 1 whenever the query shape changes (gate C.3).
  useEffect(() => { setPage(1); }, [subjectId, debouncedSearch, levelFilter]);

  const loadTopics = useCallback(async () => {
    if (!examId || !subjectId) { setTopics([]); setTotal(null); return; }
    setTopicsLoading(true);
    setTopicsError(false);
    try {
      const params = new URLSearchParams({
        exam_id: examId,
        subject_id: subjectId,
        limit: String(PAGE_SIZE),
        offset: String((page - 1) * PAGE_SIZE),
      });
      if (debouncedSearch) params.set("q", debouncedSearch);
      if (levelFilter) params.set("level", levelFilter);
      const r = await api.get(`${BASE}/topics?${params}`);
      setTopics(r?.items || []);
      setTotal(typeof r?.total === "number" ? r.total : null);
    } catch {
      setTopics([]);
      setTotal(null);
      setTopicsError(true);
    } finally {
      setTopicsLoading(false);
    }
  }, [examId, subjectId, debouncedSearch, levelFilter, page]);

  useEffect(() => { loadTopics(); }, [loadTopics]);

  const hasNext = total != null ? page * PAGE_SIZE < total : topics.length === PAGE_SIZE;

  function saveTopic(fields) {
    if (writesBlocked) return;
    if ((fields.reason || "").trim().length < 8) {
      topicAction.run({ action: () => Promise.reject(new Error("A reason of at least 8 characters is required.")),
        errorMessage: "A reason of at least 8 characters is required." });
      return;
    }
    const reason = fields.reason.trim();
    const isEdit = Boolean(fields.id);
    const action = isEdit
      ? () => api.patch(`${BASE}/topics/${fields.id}?exam_id=${examId}`, {
          reason, payload: { name: fields.name, description: fields.description || null, level: fields.level } })
      : () => api.post(`${BASE}/topics?exam_id=${examId}`, {
          reason, payload: { subject_id: subjectId, slug: fields.slug, name: fields.name,
            level: fields.level || "topic", description: fields.description || null } });
    topicAction.run({
      action,
      successMessage: isEdit ? "Topic updated." : "Topic created.",
      errorMessage: "Could not save the topic.",
      onSuccess: () => { setForm(null); loadTopics(); },
    });
  }

  function deleteTopic(t) {
    if (writesBlocked) return;
    const reason = window.prompt(`Delete "${t.name}"? Enter a reason (min 8 chars):`, "");
    if (!reason || reason.trim().length < 8) return;
    topicAction.run({
      action: () => api.del(`${BASE}/topics/${t.id}?exam_id=${examId}&reason=${encodeURIComponent(reason.trim())}`),
      successMessage: "Topic deleted.",
      errorMessage: "Could not delete the topic.",
      onSuccess: loadTopics,
    });
  }

  if (!canManage && !canReview) return null;

  return (
    <div className="border-b border-gray-200 bg-slate-50 px-4 py-3" data-testid="syllabus-topic-editor">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-600">Manage topics</span>
        <label htmlFor="ste-subject" className="text-sm text-slate-600">Subject</label>
        <select
          id="ste-subject" className="text-sm border rounded px-2 py-1" value={subjectId}
          onChange={(e) => setSubjectId(e.target.value)}
          disabled={subjectState !== "valid" || subjects.length === 0}
          data-testid="ste-subject-select"
        >
          {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <label htmlFor="ste-level" className="text-sm text-slate-600">Level</label>
        <select
          id="ste-level" className="text-sm border rounded px-2 py-1" value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)} data-testid="ste-level-filter"
        >
          <option value="">(all levels)</option>
          {TOPIC_LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <input
          type="search" className="text-sm border rounded px-2 py-1" placeholder="Search topics…"
          value={search} onChange={(e) => setSearch(e.target.value)}
          aria-label="Search topics" data-testid="ste-search"
        />
        {canManage && (
          <button
            type="button" className="text-sm px-2 py-1 border rounded bg-white disabled:opacity-40 ml-auto"
            onClick={() => setForm({ level: "topic" })} disabled={writesBlocked} data-testid="ste-new-topic"
          >
            + New topic
          </button>
        )}
      </div>

      {subjectState === "resolving" && <div className="text-sm text-slate-400 mt-2" data-testid="ste-resolving">Resolving subjects…</div>}
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

      {subjectState === "valid" && subjectId && (
        <div className="mt-2">
          {topicsLoading ? (
            <div className="text-sm text-slate-400" data-testid="ste-topics-loading">Loading topics…</div>
          ) : (
            <>
              <ul className="text-sm divide-y divide-slate-100 max-h-56 overflow-y-auto bg-white rounded border border-slate-200" data-testid="ste-topic-list">
                {topics.length === 0 && <li className="px-3 py-2 text-slate-400" data-testid="ste-no-topics">No topics.</li>}
                {topics.map((t) => (
                  <li key={t.id} className="px-3 py-2 flex items-center gap-2" data-testid={`ste-topic-${t.id}`}>
                    <span className="flex-1">{t.name} <span className="text-slate-400">· {t.level}</span></span>
                    {canManage && (
                      <>
                        <button type="button" className="text-xs px-2 py-0.5 border rounded disabled:opacity-40"
                          onClick={() => setForm({ id: t.id, name: t.name, slug: t.slug, level: t.level, description: t.description || "" })}
                          disabled={writesBlocked} data-testid={`ste-edit-${t.id}`}>Edit</button>
                        <button type="button" className="text-xs px-2 py-0.5 border rounded"
                          onClick={() => setAliasTopic(aliasTopic?.id === t.id ? null : t)}
                          data-testid={`ste-aliases-${t.id}`}>Aliases</button>
                      </>
                    )}
                    <button type="button" className="text-xs px-2 py-0.5 border rounded"
                      onClick={() => setPrereqTopic(prereqTopic?.id === t.id ? null : t)}
                      data-testid={`ste-prereqs-${t.id}`}>Prereqs</button>
                    {canManage && (
                      <button type="button" className="text-xs px-2 py-0.5 border rounded text-rose-600 disabled:opacity-40"
                        onClick={() => deleteTopic(t)} disabled={writesBlocked} data-testid={`ste-delete-${t.id}`}>Delete</button>
                    )}
                  </li>
                ))}
              </ul>
              <div className="flex items-center gap-2 mt-2 text-sm" data-testid="ste-pagination">
                <button type="button" className="px-2 py-0.5 border rounded disabled:opacity-40"
                  onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}
                  data-testid="ste-prev">Previous</button>
                <span className="text-slate-500" data-testid="ste-page-indicator">
                  {total != null
                    ? `Showing ${(page - 1) * PAGE_SIZE + (topics.length ? 1 : 0)}–${(page - 1) * PAGE_SIZE + topics.length} of ${total}`
                    : `Page ${page}`}
                </span>
                <button type="button" className="px-2 py-0.5 border rounded disabled:opacity-40"
                  onClick={() => setPage((p) => p + 1)} disabled={!hasNext}
                  data-testid="ste-next">Next</button>
              </div>
            </>
          )}
        </div>
      )}

      {form && (
        <TopicEditorForm
          key={form.id || "new"}
          initial={form}
          busy={topicAction.busy}
          onSubmit={saveTopic}
          onCancel={() => setForm(null)}
        />
      )}

      {aliasTopic && canManage && (
        <AliasEditorContainer examId={examId} topic={aliasTopic} disabled={writesBlocked} />
      )}

      {prereqTopic && (
        <TopicPrerequisiteEditor
          examId={examId}
          topic={prereqTopic}
          candidateTopics={topics}
          canManage={canManage}
          canReview={canReview}
        />
      )}
    </div>
  );
}

SyllabusTopicEditorPanel.propTypes = { examId: PropTypes.string };

/** Data container that wires the shared TopicAliasEditor to the manage endpoints. */
function AliasEditorContainer({ examId, topic, disabled }) {
  const [aliases, setAliases] = useState([]);
  const [loading, setLoading] = useState(false);
  const aliasAction = useApiAction();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ exam_id: examId, topic_id: topic.id, limit: "50" });
      const r = await api.get(`${BASE}/topic-aliases?${params}`);
      setAliases(r?.items || []);
    } catch {
      setAliases([]);
    } finally {
      setLoading(false);
    }
  }, [examId, topic.id]);

  useEffect(() => { load(); }, [load]);

  function addAlias(alias) {
    aliasAction.run({
      action: () => api.post(`${BASE}/topic-aliases?exam_id=${examId}`, {
        reason: `add alias for ${topic.name}`, payload: { topic_id: topic.id, alias } }),
      successMessage: "Alias added.",
      errorMessage: "Could not add alias.",
      onSuccess: load,
    });
  }

  function removeAlias(a) {
    const reason = window.prompt(`Remove alias "${a.alias}"? Reason (min 8 chars):`, "");
    if (!reason || reason.trim().length < 8) return;
    aliasAction.run({
      action: () => api.del(`${BASE}/topic-aliases/${a.id}?exam_id=${examId}&reason=${encodeURIComponent(reason.trim())}`),
      successMessage: "Alias removed.",
      errorMessage: "Could not remove alias.",
      onSuccess: load,
    });
  }

  return (
    <TopicAliasEditor
      topicName={topic.name}
      aliases={aliases}
      loading={loading}
      disabled={disabled || aliasAction.busy}
      onAdd={addAlias}
      onRemove={removeAlias}
    />
  );
}

AliasEditorContainer.propTypes = {
  examId: PropTypes.string,
  topic: PropTypes.object.isRequired,
  disabled: PropTypes.bool,
};
