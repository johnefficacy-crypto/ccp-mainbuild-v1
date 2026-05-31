import { useCallback, useRef, useState } from "react";
import { api } from "../../../../../lib/api";

// NOTE: GET /api/admin/exam-intelligence-cms/topics/{id} does not exist.
// We fetch the list (limit=200) and find by id client-side.
const CMS_BASE = "/api/admin/exam-intelligence-cms";

export function useTopicEdit() {
  const [open, setOpen] = useState(false);
  const [topic, setTopic] = useState(null);
  const [siblings, setSiblings] = useState([]); // for parent_topic_id picker
  const [aliases, setAliases] = useState([]);
  const [dirtyFields, setDirtyFields] = useState(new Set());
  const [reason, setReasonState] = useState("");
  const [loading, setLoading] = useState({
    fetch: false,
    save: false,
    alias_add: false,
    alias_delete: false,
  });
  const [error, setError] = useState({
    fetch: null,
    save: null,
    alias_add: null,
    alias_delete: null,
  });
  // Guard against stale fetches when topic changes quickly
  const openTopicIdRef = useRef(null);

  const openForTopic = useCallback(async (topicId) => {
    openTopicIdRef.current = topicId;
    setOpen(true);
    setTopic(null);
    setSiblings([]);
    setAliases([]);
    setDirtyFields(new Set());
    setReasonState("");
    setError({ fetch: null, save: null, alias_add: null, alias_delete: null });
    setLoading((l) => ({ ...l, fetch: true }));
    try {
      const [topicsRes, aliasesRes] = await Promise.all([
        api.get(`${CMS_BASE}/topics?limit=200`),
        api.get(`${CMS_BASE}/topic-aliases?topic_id=${topicId}&limit=50`),
      ]);
      if (openTopicIdRef.current !== topicId) return; // stale fetch
      const found = (topicsRes.items || []).find((t) => t.id === topicId);
      if (!found) throw new Error(`Topic ${topicId} not found in list`);
      setTopic(found);
      // Siblings = same subject, excluding self; used by parent_topic_id picker
      setSiblings(
        (topicsRes.items || []).filter(
          (t) => t.subject_id === found.subject_id && t.id !== topicId,
        ),
      );
      setAliases(aliasesRes.items || []);
    } catch (e) {
      if (openTopicIdRef.current === topicId) {
        setError((err) => ({ ...err, fetch: e?.message || "Failed to load topic" }));
      }
    } finally {
      if (openTopicIdRef.current === topicId) {
        setLoading((l) => ({ ...l, fetch: false }));
      }
    }
  }, []);

  const setField = useCallback((name, value) => {
    setTopic((prev) => (prev ? { ...prev, [name]: value } : prev));
    setDirtyFields((prev) => new Set([...prev, name]));
  }, []);

  const setReason = useCallback((str) => {
    setReasonState(str);
  }, []);

  const save = useCallback(async (onSuccess) => {
    if (!topic || dirtyFields.size === 0) return;
    setLoading((l) => ({ ...l, save: true }));
    setError((e) => ({ ...e, save: null }));
    try {
      const payload = {};
      for (const key of dirtyFields) {
        payload[key] = topic[key];
      }
      const result = await api.patch(`${CMS_BASE}/topics/${topic.id}`, {
        reason: reason.trim(),
        payload,
      });
      setTopic(result.row);
      setDirtyFields(new Set());
      onSuccess?.({ row: result.row });
    } catch (e) {
      setError((err) => ({ ...err, save: e?.message || "Save failed" }));
    } finally {
      setLoading((l) => ({ ...l, save: false }));
    }
  }, [topic, dirtyFields, reason]);

  const addAlias = useCallback(async (text) => {
    if (!topic || !text.trim()) return;
    setLoading((l) => ({ ...l, alias_add: true }));
    setError((e) => ({ ...e, alias_add: null }));
    try {
      const result = await api.post(`${CMS_BASE}/topic-aliases`, {
        reason: reason.trim(),
        payload: { topic_id: topic.id, alias: text.trim() },
      });
      setAliases((prev) => [result.row, ...prev]);
    } catch (e) {
      setError((err) => ({ ...err, alias_add: e?.message || "Failed to add alias" }));
    } finally {
      setLoading((l) => ({ ...l, alias_add: false }));
    }
  }, [topic, reason]);

  const deleteAlias = useCallback(async (id) => {
    setLoading((l) => ({ ...l, alias_delete: true }));
    setError((e) => ({ ...e, alias_delete: null }));
    try {
      await api.delete(
        `${CMS_BASE}/topic-aliases/${id}?reason=${encodeURIComponent(reason.trim())}`,
      );
      setAliases((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      setError((err) => ({ ...err, alias_delete: e?.message || "Failed to delete alias" }));
    } finally {
      setLoading((l) => ({ ...l, alias_delete: false }));
    }
  }, [reason]);

  const close = useCallback(() => {
    openTopicIdRef.current = null;
    setOpen(false);
    setTopic(null);
    setSiblings([]);
    setAliases([]);
    setDirtyFields(new Set());
    setReasonState("");
    setError({ fetch: null, save: null, alias_add: null, alias_delete: null });
  }, []);

  const isDirty = dirtyFields.size > 0;
  const reasonValid = reason.trim().length >= 8;
  const canSave = isDirty && reasonValid && !loading.save;
  const canAliasWrite = reasonValid;

  return {
    open,
    topic,
    siblings,
    aliases,
    dirtyFields,
    reason,
    loading,
    error,
    isDirty,
    canSave,
    canAliasWrite,
    openForTopic,
    setField,
    setReason,
    save,
    addAlias,
    deleteAlias,
    close,
  };
}
