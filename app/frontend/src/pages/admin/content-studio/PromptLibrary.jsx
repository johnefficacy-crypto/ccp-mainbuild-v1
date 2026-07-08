/**
 * Writing-prompt Library — browse/create/edit canonical (subject-scoped) prompts.
 *
 * One fetch owner: useApiCollection holds items/status; filters are sanitized
 * before they reach the hook (no empty-string typed params → no 422s).
 * Activate/Deactivate (EWP-SP2) is gated on the SEPARATE content_studio.activate
 * authority (perms.canActivate) and offered only on verified prompts; eligibility
 * is decided by the server RPC, never here.
 */
import React, { useMemo, useState } from "react";
import useApiCollection from "../../../lib/hooks/useApiCollection";
import { ErrorState, EmptyState } from "../../../shared/ui/core";
import { EXERCISE_TYPES, REVIEWER_STATUSES } from "./contentStudioApi";
import PromptEditor from "./PromptEditor";
import PromptActivationDialog from "./PromptActivation";

const PAGE_SIZE = 50;

function cleanParams(filters, offset) {
  const params = { limit: PAGE_SIZE, offset };
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== "" && v !== null && v !== undefined) params[k] = v;
  });
  return params;
}

export default function PromptLibrary({ perms, onAssign }) {
  const [filters, setFilters] = useState({
    q: "",
    subject_id: "",
    exercise_type: "",
    reviewer_status: "",
    difficulty_level: "",
  });
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState(null); // null closed | {} create | prompt edit
  const [activating, setActivating] = useState(null); // null | { prompt, mode }

  const params = useMemo(() => cleanParams(filters, offset), [filters, offset]);
  const { items, status, total, refresh } = useApiCollection(
    "/api/admin/content-studio/writing-prompts",
    [],
    { params },
  );

  const canAssign = perms.canProposeAssignment || perms.canReviewAssignment;
  // Prefer the server total; only fall back to the full-page heuristic when the
  // backend didn't send one.
  const hasNext =
    total !== null ? offset + PAGE_SIZE < total : status === "live" && items.length === PAGE_SIZE;

  const setFilter = (key, value) => {
    setOffset(0);
    setFilters((f) => ({ ...f, [key]: value }));
  };

  return (
    <div style={{ padding: 16 }} data-testid="prompt-library">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end", marginBottom: 12 }}>
        <label style={{ fontSize: 12 }}>
          Search
          <input
            className="input"
            type="text"
            value={filters.q}
            placeholder="Prompt text…"
            onChange={(e) => setFilter("q", e.target.value)}
            data-testid="prompt-filter-q"
          />
        </label>
        <label style={{ fontSize: 12 }}>
          Subject ID
          <input
            className="input"
            type="text"
            value={filters.subject_id}
            placeholder="UUID (English)"
            onChange={(e) => setFilter("subject_id", e.target.value.trim())}
            data-testid="prompt-filter-subject"
          />
        </label>
        <label style={{ fontSize: 12 }}>
          Exercise type
          <select
            className="input"
            value={filters.exercise_type}
            onChange={(e) => setFilter("exercise_type", e.target.value)}
            data-testid="prompt-filter-exercise-type"
          >
            <option value="">All types</option>
            {EXERCISE_TYPES.map((t) => (
              <option key={t} value={t}>{t.replaceAll("_", " ")}</option>
            ))}
          </select>
        </label>
        <label style={{ fontSize: 12 }}>
          Reviewer status
          <select
            className="input"
            value={filters.reviewer_status}
            onChange={(e) => setFilter("reviewer_status", e.target.value)}
            data-testid="prompt-filter-status"
          >
            <option value="">All statuses</option>
            {REVIEWER_STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <label style={{ fontSize: 12 }}>
          Difficulty
          <select
            className="input"
            value={filters.difficulty_level}
            onChange={(e) => setFilter("difficulty_level", e.target.value)}
            data-testid="prompt-filter-difficulty"
          >
            <option value="">All</option>
            {Array.from({ length: 10 }, (_, i) => i + 1).map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </label>
        {perms.canAuthor ? (
          <button
            type="button"
            className="btn primary"
            style={{ marginLeft: "auto" }}
            onClick={() => setEditing({})}
            data-testid="prompt-new"
          >
            + New prompt
          </button>
        ) : null}
      </div>

      {status === "loading" ? <div style={{ padding: "2rem", opacity: 0.7 }}>Loading prompts…</div> : null}
      {status === "error" ? <ErrorState message="Could not load writing prompts." onRetry={refresh} /> : null}
      {status === "empty" ? <EmptyState title="No prompts found" description="Adjust the filters, create a prompt, or bulk import." /> : null}

      {status === "live" ? (
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" data-testid="prompt-table">
            <thead>
              <tr>
                <th>Prompt</th>
                <th>Exercise type</th>
                <th style={{ textAlign: "right" }}>Difficulty</th>
                <th>Reviewer status</th>
                <th>Active</th>
                <th>Updated</th>
                <th style={{ width: 60 }} />
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id} data-testid={`prompt-row-${p.id}`}>
                  <td>
                    <span style={{ display: "block", maxWidth: 420, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 13 }}>
                      {p.prompt_text}
                    </span>
                  </td>
                  <td style={{ fontSize: 12 }}>{(p.exercise_type || "").replaceAll("_", " ")}</td>
                  <td style={{ textAlign: "right", fontSize: 12 }}>{p.difficulty_level}/10</td>
                  <td><span className="badge info">{p.reviewer_status}</span></td>
                  <td style={{ fontSize: 12 }}>{p.is_active ? "active" : "inactive (gated)"}</td>
                  <td style={{ fontSize: 12, opacity: 0.7 }}>
                    {p.updated_at ? new Date(p.updated_at).toLocaleDateString() : "—"}
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      {perms.canAuthor ? (
                        p.reviewer_status === "verified" ? (
                          <span style={{ fontSize: 11, opacity: 0.6 }} title="Verified prompts are locked; request needs_correction via review first.">
                            locked
                          </span>
                        ) : p.reviewer_status === "rejected" ? (
                          <span style={{ fontSize: 11, opacity: 0.6 }} title="Rejected is terminal — a rejected prompt cannot be edited or re-reviewed.">
                            rejected (terminal)
                          </span>
                        ) : (
                          <button
                            type="button"
                            className="btn small"
                            onClick={() => setEditing(p)}
                            data-testid={`prompt-edit-${p.id}`}
                          >
                            Edit
                          </button>
                        )
                      ) : null}
                      {canAssign && onAssign ? (
                        <button
                          type="button"
                          className="btn small"
                          onClick={() => onAssign(p.id)}
                          title="Manage exam applicability for this prompt"
                          data-testid={`prompt-assign-${p.id}`}
                        >
                          Assign
                        </button>
                      ) : null}
                      {/* Activation authority (content_studio.activate) — offered
                          only on verified prompts; the server RPC decides eligibility. */}
                      {perms.canActivate && p.is_active ? (
                        <button
                          type="button"
                          className="btn small"
                          onClick={() => setActivating({ prompt: p, mode: "deactivate" })}
                          data-testid={`prompt-deactivate-${p.id}`}
                        >
                          Deactivate
                        </button>
                      ) : perms.canActivate && p.reviewer_status === "verified" ? (
                        <button
                          type="button"
                          className="btn small"
                          onClick={() => setActivating({ prompt: p, mode: "activate" })}
                          data-testid={`prompt-activate-${p.id}`}
                        >
                          Activate
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 8, marginTop: 12 }}>
        {total !== null && (status === "live" || status === "empty") ? (
          <span style={{ fontSize: 12, opacity: 0.7, marginRight: "auto" }} data-testid="prompt-pagination-summary">
            {total === 0 ? "0" : `${offset + 1}–${offset + items.length}`} of {total}
          </span>
        ) : null}
        {offset > 0 ? (
          <button type="button" className="btn small" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} data-testid="prompt-prev">
            ← Prev
          </button>
        ) : null}
        {hasNext ? (
          <button type="button" className="btn small" onClick={() => setOffset(offset + PAGE_SIZE)} data-testid="prompt-next">
            Next →
          </button>
        ) : null}
      </div>

      {editing !== null ? (
        <PromptEditor
          prompt={editing.id ? editing : null}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            refresh();
          }}
        />
      ) : null}

      {activating !== null ? (
        <PromptActivationDialog
          prompt={activating.prompt}
          mode={activating.mode}
          onClose={() => setActivating(null)}
          onDone={() => {
            setActivating(null);
            refresh();
          }}
        />
      ) : null}
    </div>
  );
}
