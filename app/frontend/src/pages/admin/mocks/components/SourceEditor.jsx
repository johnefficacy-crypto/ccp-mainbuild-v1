import React from "react";
import { Plus, Trash2 } from "lucide-react";

const SOURCE_KINDS = ["authored", "pyq", "official_syllabus", "standard_source", "current_event"];
const SOURCE_TRUSTS = ["unverified", "provisional", "verified"];

const EMPTY_SOURCE = { source_kind: "authored", source_trust: "unverified", source_url: "", evidence_text: "" };

/**
 * SourceEditor — CRUD list of source rows.
 *
 * Props:
 *   value: SourceIn[]
 *   onChange: (newSources) => void
 */
export default function SourceEditor({ value = [], onChange }) {
  const add = () => onChange([...value, { ...EMPTY_SOURCE }]);
  const remove = (i) => onChange(value.filter((_, idx) => idx !== i));
  const update = (i, field, val) => {
    const next = [...value];
    next[i] = { ...next[i], [field]: val };
    onChange(next);
  };

  const inputStyle = {
    background: "#111827", border: "1px solid #374151", borderRadius: 6,
    padding: "6px 10px", color: "#e5e7eb", fontSize: 13, width: "100%", boxSizing: "border-box",
  };
  const selectStyle = { ...inputStyle, cursor: "pointer" };
  const labelStyle  = { fontSize: 11, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4, display: "block" };

  return (
    <div>
      {value.length === 0 && (
        <p style={{ fontSize: 13, color: "#6b7280", margin: "0 0 8px" }}>No sources yet. Add at least one.</p>
      )}
      {value.map((src, i) => (
        <div key={i} style={{ border: "1px solid #374151", borderRadius: 8, padding: 12, marginBottom: 10, position: "relative" }}>
          <button
            onClick={() => remove(i)}
            style={{ position: "absolute", top: 8, right: 8, background: "none", border: "none", cursor: "pointer", color: "#6b7280", padding: 2 }}
          >
            <Trash2 size={14} />
          </button>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 8 }}>
            <div>
              <label style={labelStyle}>Source Kind</label>
              <select value={src.source_kind} onChange={(e) => update(i, "source_kind", e.target.value)} style={selectStyle}>
                {SOURCE_KINDS.map((k) => <option key={k}>{k}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Trust Level</label>
              <select value={src.source_trust} onChange={(e) => update(i, "source_trust", e.target.value)} style={selectStyle}>
                {SOURCE_TRUSTS.map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div style={{ marginBottom: 8 }}>
            <label style={labelStyle}>Source URL</label>
            <input value={src.source_url || ""} onChange={(e) => update(i, "source_url", e.target.value)} placeholder="https://…" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Evidence / Notes</label>
            <input value={src.evidence_text || ""} onChange={(e) => update(i, "evidence_text", e.target.value)} placeholder="Brief description…" style={inputStyle} />
          </div>
        </div>
      ))}
      <button
        onClick={add}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          background: "none", border: "1px dashed #374151", borderRadius: 6,
          padding: "7px 14px", color: "#6b7280", fontSize: 13, cursor: "pointer",
        }}
      >
        <Plus size={14} /> Add source
      </button>
    </div>
  );
}
