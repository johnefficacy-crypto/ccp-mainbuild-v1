/**
 * Writing-prompt Bulk Import — CSV/JSON → {reason, subject_id, rows}.
 *
 * The backend import is ATOMIC all-or-nothing: the first invalid/locked row
 * aborts the whole batch with one 422 and there are no per-row results, so this
 * UI shows a single batch-level error banner on failure and
 * result.{created,updated,unchanged} on success. Rows carry a required
 * external_key and NO subject_id (subject is body-level). CSV parsing handles
 * quoted commas (csv.js), not split(",").
 */
import React, { useState } from "react";
import useApiAction from "../../../lib/hooks/useApiAction";
import { getApiErrorMessage } from "../../../lib/api";
import { contentStudioApi, EXERCISE_TYPES, isValidReason } from "./contentStudioApi";
import { parseCsv } from "./csv";
import { validateRequiredWords, validateInt, isUuid } from "./validation";

export const MAX_BULK_ROWS = 500;

// Backend bulk row shape (migration 215 + content_studio.py strict boundary).
const UUID_FIELDS = ["topic_id", "microtopic_id", "rubric_id", "source_document_id"];
// name -> validateInt bounds (mirror of the Pydantic bounds).
const INT_FIELDS = {
  difficulty_level: { min: 1, max: 10 },
  min_words: { min: 0 },
  max_words: { min: 0 },
  required_sentence_count: { min: 1 },
  max_rewrite_attempts: { min: 0 },
};
const TEXT_FIELDS = ["source_text"];
const ALLOWED_KEYS = new Set([
  "external_key",
  "exercise_type",
  "prompt_text",
  ...UUID_FIELDS,
  ...Object.keys(INT_FIELDS),
  ...TEXT_FIELDS,
  "required_words",
]);
// Known-but-forbidden keys get a specific message instead of "unknown".
const FORBIDDEN_KEYS = new Set(["subject_id", "exam_id", "exam_cycle_id", "exam_phase_id"]);

export function normalizeRow(raw) {
  const row = {};
  const errors = [];

  // Reject unknown / forbidden non-empty columns instead of silently dropping
  // them (a typo like `source_document` or `max_rewrite_attempt` must fail loud).
  Object.keys(raw || {}).forEach((k) => {
    const present = String(raw[k] ?? "").trim() !== "" || Array.isArray(raw[k]);
    if (FORBIDDEN_KEYS.has(k)) {
      if (present) {
        errors.push(
          k === "subject_id"
            ? "rows must not carry subject_id (it is set once for the whole batch)"
            : `${k} is not allowed — prompts are subject-scoped`,
        );
      }
    } else if (!ALLOWED_KEYS.has(k) && present) {
      errors.push(`unknown column "${k}" — remove it or fix the header`);
    }
  });

  const key = (raw.external_key || "").trim();
  if (!key) errors.push("external_key is required");
  else row.external_key = key;

  const et = (raw.exercise_type || "").trim();
  if (!EXERCISE_TYPES.includes(et)) errors.push(`exercise_type must be one of: ${EXERCISE_TYPES.join(", ")}`);
  else row.exercise_type = et;

  if (!(raw.prompt_text || "").trim()) errors.push("prompt_text is required");
  else row.prompt_text = raw.prompt_text;

  const topic = (raw.topic_id || "").trim();
  if (!topic) errors.push("topic_id is required");
  else if (!isUuid(topic)) errors.push("topic_id must be a UUID");
  else row.topic_id = topic;

  UUID_FIELDS.filter((f) => f !== "topic_id").forEach((f) => {
    const v = (raw[f] || "").trim();
    if (!v) return;
    if (!isUuid(v)) errors.push(`${f} must be a UUID`);
    else row[f] = v;
  });

  TEXT_FIELDS.forEach((f) => {
    if ((raw[f] || "").trim()) row[f] = raw[f];
  });

  Object.entries(INT_FIELDS).forEach(([f, bounds]) => {
    const res = validateInt(raw[f], f, bounds);
    if (res.error) errors.push(res.error);
    else if (res.value !== undefined) row[f] = res.value;
  });
  if (row.difficulty_level === undefined) errors.push("difficulty_level is required (1–10)");
  if (row.min_words !== undefined && row.max_words !== undefined && row.max_words < row.min_words) {
    errors.push("max_words must be ≥ min_words");
  }

  const rw = raw.required_words;
  let entries = null;
  if (Array.isArray(rw)) entries = rw.map((w) => String(w));
  else if (typeof rw === "string" && rw.trim()) entries = rw.split(/[|,]/);
  if (entries) {
    const res = validateRequiredWords(entries);
    if (res.error) errors.push(res.error);
    else if (res.words.length > 0) row.required_words = res.words;
  }

  return { row, errors };
}

export default function PromptBulkImport({ perms }) {
  const [subjectId, setSubjectId] = useState("");
  const [reason, setReason] = useState("");
  const [parsed, setParsed] = useState(null); // [{row, errors, index}]
  const [parseError, setParseError] = useState("");
  const [batchError, setBatchError] = useState("");
  const [result, setResult] = useState(null);
  const { run, busy } = useApiAction();

  if (!perms.canAuthor) {
    return (
      <div style={{ padding: "2rem", opacity: 0.7 }} data-testid="bulk-import-no-access">
        Bulk import requires content_studio.author.
      </div>
    );
  }

  const handleFile = async (file) => {
    setParseError("");
    setBatchError("");
    setResult(null);
    setParsed(null);
    try {
      const text = await file.text();
      let raws;
      if (file.name.endsWith(".json")) {
        const data = JSON.parse(text);
        raws = Array.isArray(data) ? data : [data];
      } else if (file.name.endsWith(".csv")) {
        raws = parseCsv(text);
      } else {
        setParseError("Unsupported file type — use .csv or .json.");
        return;
      }
      if (!raws.length) {
        setParseError("No rows found in the file.");
        return;
      }
      if (raws.length > MAX_BULK_ROWS) {
        setParseError(`Too many rows: ${raws.length}. The import API accepts at most ${MAX_BULK_ROWS} rows per batch — split the file.`);
        return;
      }
      const seenKeys = new Set();
      const rows = raws.map((raw, index) => {
        const { row, errors } = normalizeRow(raw);
        if (row.external_key) {
          const k = row.external_key.toLowerCase();
          if (seenKeys.has(k)) errors.push("duplicate external_key within the batch");
          seenKeys.add(k);
        }
        return { row, errors, index };
      });
      setParsed(rows);
    } catch (e) {
      setParseError(`Could not parse file: ${e.message}`);
    }
  };

  const invalid = (parsed || []).filter((r) => r.errors.length > 0);
  const canSubmit =
    parsed && parsed.length > 0 && invalid.length === 0 && subjectId.trim() && isValidReason(reason) && !busy;

  const submit = async () => {
    setBatchError("");
    const res = await run({
      action: () =>
        contentStudioApi.bulkImportPrompts({
          reason: reason.trim(),
          subject_id: subjectId.trim(),
          rows: parsed.map((r) => r.row),
        }),
      successMessage: "Import complete.",
      errorMessage: " ",
    });
    if (res.ok) {
      setResult(res.data?.result || null);
      setParsed(null);
    } else if (res.error) {
      // Atomic batch: one banner, no per-row outcomes to render.
      setBatchError(getApiErrorMessage(res.error));
    }
  };

  return (
    <div style={{ padding: 16, maxWidth: 860 }} data-testid="prompt-bulk-import">
      <p style={{ fontSize: 12, opacity: 0.75, marginBottom: 12 }}>
        Import writing prompts for one subject. Each row needs a stable{" "}
        <code>external_key</code> (idempotency: re-importing an identical row is a
        no-op; a changed pending/needs-correction row is updated and reset to
        pending; changed verified/rejected rows abort the batch). The import is
        atomic — all rows land or none do.
      </p>

      <div style={{ display: "grid", gap: 10, maxWidth: 520, marginBottom: 14 }}>
        <label style={{ fontSize: 12 }}>
          Subject ID (applies to every row)
          <input className="input" value={subjectId} onChange={(e) => setSubjectId(e.target.value)} placeholder="UUID of the English subject" data-testid="bulk-subject" />
        </label>
        <label style={{ fontSize: 12 }}>
          Reason (required, 8–500 chars)
          <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} data-testid="bulk-reason" />
        </label>
        <label style={{ fontSize: 12 }}>
          File (.csv or .json)
          <input
            className="input"
            type="file"
            accept=".csv,.json"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            data-testid="bulk-file"
          />
        </label>
      </div>

      {parseError ? (
        <div style={{ color: "var(--err, #c00)", fontSize: 12, marginBottom: 12 }} role="alert" data-testid="bulk-parse-error">
          {parseError}
        </div>
      ) : null}
      {batchError ? (
        <div className="badge blocker" style={{ display: "block", padding: "0.75rem", marginBottom: 12, fontSize: 12 }} role="alert" data-testid="bulk-batch-error">
          Import rejected (atomic — no rows were written): {batchError}
        </div>
      ) : null}
      {result ? (
        <div style={{ padding: "0.75rem", border: "1px solid var(--rule, #ddd)", borderRadius: 4, fontSize: 13, marginBottom: 12 }} data-testid="bulk-result">
          <strong>Import complete.</strong>{" "}
          {result.created ?? 0} created · {result.updated ?? 0} updated · {result.unchanged ?? 0} unchanged.
          Imported prompts are pending review and inactive.
        </div>
      ) : null}

      {parsed ? (
        <>
          <div style={{ fontSize: 13, marginBottom: 8 }} data-testid="bulk-precheck">
            {parsed.length} rows parsed · {invalid.length} with local validation errors
            {invalid.length > 0 ? " — fix the file and re-upload; the batch would be rejected as a whole." : ""}
          </div>
          <div style={{ overflowX: "auto", marginBottom: 12 }}>
            <table className="data-table" style={{ fontSize: 12 }}>
              <thead>
                <tr>
                  <th>#</th>
                  <th>external_key</th>
                  <th>exercise_type</th>
                  <th>prompt_text</th>
                  <th>Local errors</th>
                </tr>
              </thead>
              <tbody>
                {parsed.map((r) => (
                  <tr key={r.index}>
                    <td>{r.index + 1}</td>
                    <td>{r.row.external_key || "—"}</td>
                    <td>{r.row.exercise_type || "—"}</td>
                    <td>
                      <span style={{ display: "block", maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {r.row.prompt_text || "—"}
                      </span>
                    </td>
                    <td style={{ color: r.errors.length ? "var(--err, #c00)" : undefined }}>
                      {r.errors.join("; ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button type="button" className="btn primary" onClick={submit} disabled={!canSubmit} data-testid="bulk-submit">
            {busy ? "Importing…" : `Import ${parsed.length} rows`}
          </button>
        </>
      ) : null}
    </div>
  );
}
