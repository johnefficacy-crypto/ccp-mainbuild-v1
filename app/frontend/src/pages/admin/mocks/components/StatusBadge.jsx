import React from "react";

const STATUS_CONFIG = {
  draft:           { label: "Draft",           bg: "#374151", text: "#9ca3af" },
  in_review:       { label: "In Review",       bg: "#1e3a5f", text: "#60a5fa" },
  needs_changes:   { label: "Needs Changes",   bg: "#451a03", text: "#fb923c" },
  verified:        { label: "Verified",        bg: "#14532d", text: "#4ade80" },
  published:       { label: "Published",       bg: "#166534", text: "#86efac" },
  archived:        { label: "Archived",        bg: "#1f2937", text: "#6b7280" },
};

export default function StatusBadge({ status, size = "sm" }) {
  const cfg = STATUS_CONFIG[status] || { label: status, bg: "#374151", text: "#9ca3af" };
  const pad = size === "lg" ? "6px 14px" : "3px 10px";
  const fontSize = size === "lg" ? "13px" : "11px";
  return (
    <span
      style={{
        display: "inline-block",
        padding: pad,
        borderRadius: 9999,
        background: cfg.bg,
        color: cfg.text,
        fontSize,
        fontWeight: 600,
        letterSpacing: "0.03em",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
      }}
    >
      {cfg.label}
    </span>
  );
}
