import React, { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../../../lib/api";
import { ArrowLeft, Upload, CheckCircle, AlertTriangle, XCircle, ArrowRight } from "lucide-react";

// ---------- styles ----------
const S = {
  page:      { padding: 24, color: "#e5e7eb", minHeight: "100vh", maxWidth: 860, margin: "0 auto" },
  header:    { marginBottom: 24 },
  breadcrumb:{ display: "flex", alignItems: "center", gap: 6, color: "#6b7280", fontSize: 13, marginBottom: 6 },
  title:     { fontSize: 20, fontWeight: 700, color: "#f9fafb", margin: "0 0 4px" },
  subtitle:  { fontSize: 13, color: "#6b7280", margin: 0 },
  card:      { background: "#111827", borderRadius: 8, border: "1px solid #1f2937", padding: 20, marginBottom: 16 },
  cardTitle: { fontSize: 13, fontWeight: 600, color: "#f9fafb", margin: "0 0 14px" },
  label:     { fontSize: 11, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 5, display: "block" },
  input:     { background: "#0f172a", border: "1px solid #374151", borderRadius: 6, padding: "8px 12px", color: "#e5e7eb", fontSize: 14, width: "100%", boxSizing: "border-box" },
  btn:       { display: "inline-flex", alignItems: "center", gap: 6, border: "none", borderRadius: 6, padding: "9px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer", color: "#fff" },
  th:        { textAlign: "left", fontSize: 11, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", padding: "8px 10px", borderBottom: "1px solid #1f2937" },
  td:        { padding: "8px 10px", borderBottom: "1px solid #1f2937", fontSize: 13, color: "#d1d5db", verticalAlign: "top" },
  error:     { background: "#450a0a", border: "1px solid #dc2626", borderRadius: 6, padding: "10px 14px", marginBottom: 14, color: "#fca5a5", fontSize: 13 },
  steps:     { display: "flex", gap: 0, marginBottom: 28 },
};

// Row status pill
const ROW_STATUS = {
  ok:           { bg: "#052e16", color: "#22c55e", label: "OK",        Icon: CheckCircle  },
  duplicate:    { bg: "#1c1004", color: "#f59e0b", label: "Duplicate", Icon: AlertTriangle },
  parse_error:  { bg: "#1a0505", color: "#ef4444", label: "Error",     Icon: XCircle      },
  missing_tags: { bg: "#0c1a2e", color: "#60a5fa", label: "No tags",   Icon: AlertTriangle },
};

function RowPill({ status }) {
  const cfg = ROW_STATUS[status] || ROW_STATUS.ok;
  const { Icon } = cfg;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, background: cfg.bg, color: cfg.color, borderRadius: 4, padding: "2px 8px", fontSize: 12, fontWeight: 600 }}>
      <Icon size={11} />
      {cfg.label}
    </span>
  );
}

function StepIndicator({ current }) {
  const steps = ["Upload", "Preview", "Done"];
  return (
    <div style={S.steps}>
      {steps.map((label, i) => {
        const active = i === current;
        const done   = i < current;
        return (
          <React.Fragment key={label}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{
                width: 26, height: 26, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                background: done ? "#2563eb" : active ? "#1d4ed8" : "#1f2937",
                border: `2px solid ${done || active ? "#2563eb" : "#374151"}`,
                fontSize: 12, fontWeight: 700, color: done || active ? "#fff" : "#6b7280",
              }}>
                {done ? "✓" : i + 1}
              </div>
              <span style={{ fontSize: 13, fontWeight: active ? 600 : 400, color: active ? "#f9fafb" : done ? "#9ca3af" : "#6b7280" }}>
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div style={{ flex: 1, height: 2, background: done ? "#2563eb" : "#1f2937", margin: "0 10px", alignSelf: "center" }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ---------- component ----------
export default function ImportWizard() {
  const navigate = useNavigate();
  const fileRef  = useRef(null);

  const [step,        setStep]        = useState(0); // 0=upload, 1=preview, 2=done
  const [file,        setFile]        = useState(null);
  const [examId,      setExamId]      = useState("");
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState(null);
  const [dryRunData,  setDryRunData]  = useState(null);  // { import_token, total, ok_count, duplicate_count, error_count, rows }
  const [commitResult, setCommitResult] = useState(null); // { created, skipped, failed, question_ids }

  // ── dry run ────────────────────────────────────────────────────────────────
  const handleDryRun = async () => {
    if (!file) { setError("Please select a file."); return; }
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    if (examId.trim()) formData.append("exam_id_override", examId.trim());

    try {
      // api.post may not support FormData; fall back to fetch directly
      const res = await fetch("/api/admin/mocks/questions/import/dry-run", {
        method: "POST",
        body: formData,
        headers: { Authorization: api._authHeader?.() }.Authorization
          ? { Authorization: api._authHeader() }
          : undefined,
        credentials: "include",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setDryRunData(data);
      setStep(1);
    } catch (e) {
      setError(e?.message || "Dry-run failed");
    } finally {
      setLoading(false);
    }
  };

  // ── commit ─────────────────────────────────────────────────────────────────
  const handleCommit = async () => {
    if (!dryRunData?.import_token) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.post("/api/admin/mocks/questions/import/commit", {
        import_token: dryRunData.import_token,
      });
      setCommitResult(result);
      setStep(2);
    } catch (e) {
      setError(e?.message || "Commit failed");
    } finally {
      setLoading(false);
    }
  };

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <div style={S.page}>
      {/* Header */}
      <div style={S.header}>
        <div style={S.breadcrumb}>
          <Link to="/admin/mocks/questions" style={{ color: "#6b7280", textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>
            <ArrowLeft size={13} /> Question Bank
          </Link>
        </div>
        <h1 style={S.title}>Bulk Import</h1>
        <p style={S.subtitle}>Upload a CSV or JSON file to import questions into the bank.</p>
      </div>

      <StepIndicator current={step} />

      {/* Error */}
      {error && (
        <div style={S.error}>
          {error}
          <button onClick={() => setError(null)} style={{ float: "right", background: "none", border: "none", color: "#fca5a5", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>×</button>
        </div>
      )}

      {/* ── Step 0: Upload ── */}
      {step === 0 && (
        <div style={S.card}>
          <h2 style={S.cardTitle}>Select File</h2>

          {/* Drop zone */}
          <div
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const f = e.dataTransfer.files[0];
              if (f) setFile(f);
            }}
            style={{
              border: "2px dashed #374151", borderRadius: 8, padding: 32,
              textAlign: "center", cursor: "pointer", marginBottom: 16,
              background: file ? "#0f2b1a" : "transparent",
              transition: "background 0.15s",
            }}
          >
            <Upload size={28} color={file ? "#22c55e" : "#4b5563"} style={{ marginBottom: 8 }} />
            {file ? (
              <>
                <div style={{ fontWeight: 600, color: "#22c55e", fontSize: 14 }}>{file.name}</div>
                <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>{(file.size / 1024).toFixed(1)} KB</div>
              </>
            ) : (
              <>
                <div style={{ fontWeight: 600, color: "#e5e7eb", fontSize: 14 }}>Click or drop file here</div>
                <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>Accepts .csv or .json</div>
              </>
            )}
          </div>
          <input ref={fileRef} type="file" accept=".csv,.json" style={{ display: "none" }} onChange={(e) => setFile(e.target.files[0] || null)} />

          {/* Exam ID override */}
          <div style={{ marginBottom: 20 }}>
            <label style={S.label}>Exam ID Override (optional)</label>
            <input
              value={examId}
              onChange={(e) => setExamId(e.target.value)}
              placeholder="Leave blank to use per-row exam_id"
              style={S.input}
            />
          </div>

          {/* Format hint */}
          <details style={{ marginBottom: 20 }}>
            <summary style={{ fontSize: 13, color: "#6b7280", cursor: "pointer", userSelect: "none" }}>
              Expected CSV / JSON format
            </summary>
            <div style={{ marginTop: 10, padding: 12, background: "#0f172a", borderRadius: 6, fontSize: 12, color: "#9ca3af", fontFamily: "monospace", lineHeight: 1.6, overflowX: "auto" }}>
              <div style={{ color: "#6b7280", marginBottom: 8 }}># CSV columns:</div>
              question_text, option_a, option_b, option_c, option_d, correct_option, difficulty, language, source_kind, source_url, exam_id
              <br /><br />
              <div style={{ color: "#6b7280", marginBottom: 8 }}># JSON format:</div>
              {"[\n  {\n    \"question_text\": \"…\",\n    \"options\": [{\"text\":\"…\",\"is_correct\":false}, …],\n    \"correct_option\": 0,\n    \"difficulty\": \"medium\",\n    \"language\": \"en\",\n    \"source_kind\": \"authored\",\n    \"source_url\": \"\",\n    \"exam_id\": \"uuid\"\n  }\n]"}
            </div>
          </details>

          <button
            onClick={handleDryRun}
            disabled={!file || loading}
            style={{ ...S.btn, background: (!file || loading) ? "#374151" : "#2563eb", cursor: (!file || loading) ? "not-allowed" : "pointer" }}
          >
            <ArrowRight size={14} />
            {loading ? "Analysing…" : "Preview Import"}
          </button>
        </div>
      )}

      {/* ── Step 1: Preview ── */}
      {step === 1 && dryRunData && (
        <>
          {/* Summary counts */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
            {[
              { label: "Total",      value: dryRunData.total,           color: "#e5e7eb" },
              { label: "OK",         value: dryRunData.ok_count,        color: "#22c55e" },
              { label: "Duplicates", value: dryRunData.duplicate_count, color: "#f59e0b" },
              { label: "Errors",     value: dryRunData.error_count,     color: "#ef4444" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 8, padding: 16, textAlign: "center" }}>
                <div style={{ fontSize: 26, fontWeight: 700, color }}>{value ?? 0}</div>
                <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Row table */}
          <div style={{ background: "#111827", borderRadius: 8, border: "1px solid #1f2937", overflow: "auto", marginBottom: 16 }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ ...S.th, width: 50 }}>#</th>
                  <th style={S.th}>Question</th>
                  <th style={{ ...S.th, width: 110 }}>Status</th>
                  <th style={S.th}>Notes</th>
                </tr>
              </thead>
              <tbody>
                {(dryRunData.rows || []).map((row, i) => (
                  <tr key={i}>
                    <td style={{ ...S.td, color: "#6b7280" }}>{i + 1}</td>
                    <td style={S.td}>
                      <span style={{ display: "block", maxWidth: 420, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {row.question_text || <em style={{ color: "#4b5563" }}>—</em>}
                      </span>
                    </td>
                    <td style={S.td}>
                      <RowPill status={row.status} />
                    </td>
                    <td style={{ ...S.td, color: "#6b7280", fontSize: 12 }}>
                      {row.errors?.join("; ") || row.duplicate_of
                        ? `Duplicate of ${row.duplicate_of}`
                        : row.notes || ""}
                    </td>
                  </tr>
                ))}
                {(dryRunData.rows || []).length === 0 && (
                  <tr>
                    <td colSpan={4} style={{ ...S.td, textAlign: "center", color: "#6b7280" }}>No rows parsed.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button onClick={() => { setStep(0); setDryRunData(null); setFile(null); }} style={{ ...S.btn, background: "#374151" }}>
              ← Start Over
            </button>
            <button
              onClick={handleCommit}
              disabled={loading || dryRunData.ok_count === 0}
              style={{
                ...S.btn,
                background: (loading || dryRunData.ok_count === 0) ? "#374151" : "#16a34a",
                cursor: (loading || dryRunData.ok_count === 0) ? "not-allowed" : "pointer",
              }}
            >
              <CheckCircle size={14} />
              {loading
                ? "Importing…"
                : `Import ${dryRunData.ok_count} Question${dryRunData.ok_count !== 1 ? "s" : ""}`}
            </button>
          </div>
        </>
      )}

      {/* ── Step 2: Done ── */}
      {step === 2 && commitResult && (
        <div style={S.card}>
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <CheckCircle size={48} color="#22c55e" style={{ marginBottom: 16 }} />
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "#f9fafb", margin: "0 0 8px" }}>Import Complete</h2>
            <p style={{ color: "#6b7280", fontSize: 14, margin: "0 0 28px" }}>
              Your questions have been added to the question bank.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 28 }}>
            {[
              { label: "Created", value: commitResult.created, color: "#22c55e" },
              { label: "Skipped", value: commitResult.skipped, color: "#f59e0b" },
              { label: "Failed",  value: commitResult.failed,  color: "#ef4444" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ background: "#0f172a", border: "1px solid #1f2937", borderRadius: 8, padding: 16, textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 700, color }}>{value ?? 0}</div>
                <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
            <button onClick={() => { setStep(0); setFile(null); setDryRunData(null); setCommitResult(null); }} style={{ ...S.btn, background: "#374151" }}>
              Import More
            </button>
            <button onClick={() => navigate("/admin/mocks/questions")} style={{ ...S.btn, background: "#2563eb" }}>
              View Question Bank →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
