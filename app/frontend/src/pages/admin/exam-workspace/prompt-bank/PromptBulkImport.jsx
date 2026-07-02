/**
 * Bulk import flow for CSV/JSON.
 *
 * Flow:
 * 1. Select file
 * 2. Parse locally
 * 3. Validate rows
 * 4. Show preview with row-level errors
 * 5. Confirm import
 * 6. Display created/rejected summary
 */
import React, { useState } from "react";

const REQUIRED_FIELDS = [
  "external_key",
  "exercise_type",
  "prompt_text",
  "topic_id",
  "difficulty_level",
];

function parseImportFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target.result;
        let data;

        if (file.name.endsWith(".json")) {
          data = JSON.parse(text);
          if (!Array.isArray(data)) data = [data];
        } else if (file.name.endsWith(".csv")) {
          data = parseCSV(text);
        } else {
          reject(new Error("Unsupported file type. Use CSV or JSON."));
          return;
        }

        if (!Array.isArray(data) || data.length === 0) {
          reject(new Error("No rows found."));
          return;
        }

        resolve(data);
      } catch (e) {
        reject(new Error(`Parse error: ${e.message}`));
      }
    };
    reader.onerror = () => reject(new Error("File read failed"));
    reader.readAsText(file);
  });
}

function parseCSV(text) {
  const lines = text.split("\n").filter((l) => l.trim());
  if (lines.length < 2) return [];

  const headers = lines[0].split(",").map((h) => h.trim());
  const rows = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(",").map((v) => v.trim());
    const row = {};
    headers.forEach((h, idx) => {
      row[h] = values[idx] || "";
    });
    rows.push(row);
  }

  return rows;
}

function validateRow(row) {
  const errors = [];

  REQUIRED_FIELDS.forEach((field) => {
    if (!row[field] || String(row[field]).trim() === "") {
      errors.push(`Missing ${field}`);
    }
  });

  if (row.difficulty_level) {
    const d = Number(row.difficulty_level);
    if (isNaN(d) || d < 1 || d > 10) {
      errors.push("Difficulty must be 1–10");
    }
  }

  if (row.max_words && row.min_words) {
    const min = Number(row.min_words);
    const max = Number(row.max_words);
    if (max < min) {
      errors.push("Max words must be >= min words");
    }
  }

  return errors;
}

export default function PromptBulkImport({ examId, onImport, onClose }) {
  const [stage, setStage] = useState("upload"); // upload, preview, summary
  const [validatedRows, setValidatedRows] = useState([]);
  const [parseError, setParseError] = useState("");
  const [importing, setImporting] = useState(false);
  const [summary, setSummary] = useState(null);

  const handleFileSelect = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;

    setParseError("");
    setImporting(true);

    try {
      const parsed = await parseImportFile(f);

      const validated = parsed.map((row) => ({
        row,
        errors: validateRow(row),
      }));
      setValidatedRows(validated);

      setStage("preview");
    } catch (err) {
      setParseError(err.message);
    } finally {
      setImporting(false);
    }
  };

  const handleConfirmImport = async () => {
    const importableRows = validatedRows
      .filter((v) => v.errors.length === 0)
      .map((v) => ({
        ...v.row,
        exam_id: examId,
      }));

    if (importableRows.length === 0) {
      setParseError("No valid rows to import.");
      return;
    }

    setImporting(true);
    try {
      const result = await onImport(importableRows);
      setSummary(result || { created: importableRows.length, failed: 0 });
      setStage("summary");
    } catch (err) {
      setParseError(err.message);
    } finally {
      setImporting(false);
    }
  };

  const validCount = validatedRows.filter((v) => v.errors.length === 0).length;
  const invalidCount = validatedRows.length - validCount;

  if (stage === "upload") {
    return (
      <div
        className="modal-overlay"
        onClick={onClose}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(0,0,0,0.5)",
          zIndex: 101,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          className="modal"
          onClick={(e) => e.stopPropagation()}
          style={{
            width: "min(500px, 90vw)",
            background: "white",
            borderRadius: 6,
            boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
            overflow: "hidden",
          }}
        >
          <div style={{ padding: "2rem", textAlign: "center" }}>
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>
              Bulk Import Prompts
            </h2>
            <p style={{ fontSize: 13, opacity: 0.7, marginBottom: "2rem" }}>
              Upload a CSV or JSON file with prompts. Required fields:{" "}
              <code style={{ fontSize: 11 }}>
                external_key, exercise_type, prompt_text, topic_id, difficulty_level
              </code>
            </p>

            <label
              style={{
                display: "block",
                padding: "2rem 1rem",
                border: "2px dashed var(--rule)",
                borderRadius: 6,
                cursor: "pointer",
                background: "var(--paper-dim, #f5f6f7)",
                marginBottom: "1rem",
                transition: "all 0.2s",
              }}
              onDragOver={(e) => {
                e.preventDefault();
                e.currentTarget.style.background = "var(--info-light, #e3f2fd)";
              }}
              onDragLeave={(e) => {
                e.currentTarget.style.background = "var(--paper-dim, #f5f6f7)";
              }}
              onDrop={(e) => {
                e.preventDefault();
                const f = e.dataTransfer.files[0];
                if (f) {
                  handleFileSelect({ target: { files: [f] } });
                }
              }}
            >
              <input
                type="file"
                accept=".csv,.json"
                onChange={handleFileSelect}
                disabled={importing}
                style={{ display: "none" }}
              />
              <div>
                {importing ? "Parsing…" : "Drop file or click to select"}
              </div>
              <div style={{ fontSize: 11, opacity: 0.6, marginTop: 4 }}>
                CSV or JSON
              </div>
            </label>

            {parseError && (
              <div
                style={{
                  padding: "0.75rem",
                  background: "var(--err-light, #ffebee)",
                  color: "var(--err, #c00)",
                  borderRadius: 4,
                  fontSize: 12,
                  marginBottom: "1rem",
                }}
              >
                {parseError}
              </div>
            )}

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button className="btn" onClick={onClose} disabled={importing}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (stage === "preview") {
    return (
      <div
        className="modal-overlay"
        onClick={onClose}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(0,0,0,0.5)",
          zIndex: 101,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          className="modal"
          onClick={(e) => e.stopPropagation()}
          style={{
            width: "min(700px, 90vw)",
            maxHeight: "85vh",
            background: "white",
            borderRadius: 6,
            boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div style={{ padding: "1.5rem", borderBottom: "1px solid var(--rule)" }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
              Import Preview
            </h2>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: "1.5rem" }}>
            <div
              style={{
                marginBottom: "1rem",
                padding: "0.75rem",
                background: validCount > 0 ? "var(--success-light, #e8f5e9)" : "var(--warn-light, #fff8e1)",
                borderRadius: 4,
                fontSize: 13,
              }}
            >
              <strong>{validCount} valid</strong>, <strong>{invalidCount} invalid</strong>
            </div>

            <div style={{ overflowX: "auto" }}>
              <table className="data-table" style={{ fontSize: 12 }}>
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>External Key</th>
                    <th>Exercise Type</th>
                    <th>Difficulty</th>
                    <th>Errors</th>
                  </tr>
                </thead>
                <tbody>
                  {validatedRows.map((v, idx) => (
                    <tr key={idx}>
                      <td>
                        {v.errors.length === 0 ? (
                          <span className="badge info" style={{ fontSize: 10 }}>
                            ✓
                          </span>
                        ) : (
                          <span className="badge blocker" style={{ fontSize: 10 }}>
                            ✗
                          </span>
                        )}
                      </td>
                      <td>{v.row.external_key || "—"}</td>
                      <td>{v.row.exercise_type || "—"}</td>
                      <td>{v.row.difficulty_level || "—"}</td>
                      <td>
                        {v.errors.length > 0 && (
                          <span style={{ color: "var(--err, #c00)", fontSize: 11 }}>
                            {v.errors.join("; ")}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div
            style={{
              padding: "1rem",
              borderTop: "1px solid var(--rule)",
              display: "flex",
              gap: 8,
              justifyContent: "flex-end",
            }}
          >
            <button className="btn" onClick={() => setStage("upload")} disabled={importing}>
              Back
            </button>
            <button
              className="btn primary"
              onClick={handleConfirmImport}
              disabled={importing || validCount === 0}
            >
              {importing ? "Importing…" : `Import ${validCount} prompts`}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (stage === "summary") {
    return (
      <div
        className="modal-overlay"
        onClick={onClose}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(0,0,0,0.5)",
          zIndex: 101,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          className="modal"
          onClick={(e) => e.stopPropagation()}
          style={{
            width: "min(500px, 90vw)",
            background: "white",
            borderRadius: 6,
            boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
          }}
        >
          <div style={{ padding: "2rem", textAlign: "center" }}>
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>
              ✓ Import Complete
            </h2>
            <div style={{ fontSize: 14, marginBottom: "1.5rem" }}>
              <p style={{ marginBottom: 8 }}>
                <strong>{summary?.created || 0} prompts created</strong>
              </p>
              {summary?.failed > 0 && (
                <p style={{ color: "var(--warn, #f80)" }}>
                  <strong>{summary.failed} prompts failed</strong>
                </p>
              )}
            </div>
            <button
              className="btn primary"
              onClick={onClose}
            >
              Done
            </button>
          </div>
        </div>
      </div>
    );
  }
}
