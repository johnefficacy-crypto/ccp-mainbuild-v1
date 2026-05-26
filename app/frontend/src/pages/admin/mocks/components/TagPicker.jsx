import React, { useEffect, useState } from "react";
import { api } from "../../../../lib/api";
import { X } from "lucide-react";

const ROLE_OPTIONS = [
  { value: "primary",           label: "Primary" },
  { value: "secondary",         label: "Secondary" },
  { value: "prerequisite",      label: "Prerequisite" },
  { value: "trap",              label: "Trap" },
  { value: "calculation_layer", label: "Calculation" },
  { value: "conceptual_layer",  label: "Conceptual" },
];

/**
 * TagPicker — lets author pick topics from the topics table and assign a role.
 *
 * Props:
 *   value: [{ topic_id, role, topics: { name } }]
 *   onChange: (newTags) => void
 */
export default function TagPicker({ value = [], onChange }) {
  const [topics, setTopics] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (search.length < 2) { setTopics([]); return; }
    setLoading(true);
    api.get(`/api/canonical/topics?q=${encodeURIComponent(search)}&limit=10`)
      .then((res) => setTopics(res?.items || res || []))
      .catch(() => setTopics([]))
      .finally(() => setLoading(false));
  }, [search]);

  const addTag = (topic, role = "primary") => {
    if (value.some((t) => t.topic_id === topic.id && t.role === role)) return;
    onChange([...value, { topic_id: topic.id, role, topics: { name: topic.name } }]);
    setSearch("");
    setTopics([]);
  };

  const removeTag = (idx) => onChange(value.filter((_, i) => i !== idx));

  const changeRole = (idx, role) => {
    const next = [...value];
    next[idx] = { ...next[idx], role };
    onChange(next);
  };

  return (
    <div>
      {/* Existing tags */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
        {value.map((t, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 6,
            background: "#1f2937", borderRadius: 6, padding: "4px 10px",
          }}>
            <span style={{ fontSize: 13, color: "#e5e7eb" }}>{t.topics?.name || t.topic_id}</span>
            <select
              value={t.role}
              onChange={(e) => changeRole(i, e.target.value)}
              style={{ fontSize: 11, background: "#374151", color: "#9ca3af", border: "none", borderRadius: 4, padding: "2px 4px" }}
            >
              {ROLE_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
            <button onClick={() => removeTag(i)} style={{ background: "none", border: "none", cursor: "pointer", color: "#6b7280", padding: 0, display: "flex" }}>
              <X size={13} />
            </button>
          </div>
        ))}
      </div>

      {/* Search */}
      <div style={{ position: "relative" }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search topics…"
          style={{
            width: "100%", boxSizing: "border-box",
            background: "#111827", border: "1px solid #374151", borderRadius: 6,
            padding: "8px 12px", color: "#e5e7eb", fontSize: 13,
          }}
        />
        {loading && <span style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", color: "#6b7280", fontSize: 11 }}>…</span>}
        {topics.length > 0 && (
          <ul style={{
            position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0, zIndex: 20,
            background: "#1f2937", border: "1px solid #374151", borderRadius: 6,
            listStyle: "none", margin: 0, padding: 4, maxHeight: 200, overflowY: "auto",
          }}>
            {topics.map((t) => (
              <li key={t.id}>
                <button
                  onClick={() => addTag(t)}
                  style={{
                    width: "100%", textAlign: "left", background: "none", border: "none",
                    cursor: "pointer", color: "#e5e7eb", fontSize: 13, padding: "6px 10px", borderRadius: 4,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#374151")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
                >
                  {t.name}
                  {t.subject_name && <span style={{ color: "#6b7280", marginLeft: 8, fontSize: 11 }}>{t.subject_name}</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
