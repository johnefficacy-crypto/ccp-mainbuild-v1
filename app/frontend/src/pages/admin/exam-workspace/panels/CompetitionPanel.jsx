import React, { useCallback, useEffect, useState } from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { api } from "../../../../lib/api";

function TrustBadge({ status }) {
  const map = {
    pending:          { cls: "badge pending",  text: "pending" },
    needs_correction: { cls: "badge blocker",  text: "needs fix" },
    draft:            { cls: "badge neutral",  text: "draft" },
    verified:         { cls: "badge info",     text: "verified" },
    locked:           { cls: "badge ink",      text: "locked" },
  };
  const b = map[status] || map.pending;
  return <span className={b.cls}>{b.text}</span>;
}

const EI_BASE = "/api/admin/exam-intelligence";
const CMS_BASE = "/api/admin/exam-intelligence-cms";

export default function CompetitionPanel() {
  const { exam, cycle } = useExamWorkspace();

  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({
    vacancies: "",
    applicants: "",
    cutoff_trend: "rising",
    difficulty_trend: "harder",
    source_url: "",
  });
  const [savingNew, setSavingNew] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams({ status: "all", limit: "100" });
      if (exam?.id) qs.set("exam_id", exam.id);
      if (cycle?.id) qs.set("cycle_id", cycle.id);
      const d = await api.get(`${EI_BASE}/competition-metrics?${qs}`);
      setMetrics(d?.items || []);
    } catch (e) {
      setError(e?.message || "Failed to load metrics");
    } finally {
      setLoading(false);
    }
  }, [exam?.id, cycle?.id]);

  useEffect(() => { load(); }, [load]);

  async function lockMetric(id) {
    setBusyId(id);
    setError("");
    try {
      // Competition review uses the coverage lifecycle
      // (draft|pending_review|reviewed|locked|rejected) — "verified" is not a
      // valid status here and 422s. Only "locked" rows feed competition_context
      // in Study OS, so the promote action locks the row directly.
      await api.patch(`${EI_BASE}/competition-metrics/${encodeURIComponent(id)}/review`, {
        reviewer_status: "locked",
      });
      await load();
    } catch (e) {
      setError(e?.message || "Lock failed");
    } finally {
      setBusyId(null);
    }
  }

  async function saveMetric() {
    setSavingNew(true);
    setError("");
    try {
      // Allowed fields = _COMPETITION_FIELDS (admin_exam_intel_cms.py:1366).
      // Column names are vacancy_total / applicant_count (not vacancies /
      // total_applicants); source_url is not a column, so it rides in
      // metadata. reviewer_status is server-controlled (lands 'draft').
      const payload = {
        exam_id: exam?.id || null,
        exam_cycle_id: cycle?.id || null,
        cutoff_trend: form.cutoff_trend,
        difficulty_trend: form.difficulty_trend,
      };
      if (form.vacancies) payload.vacancy_total = parseInt(form.vacancies, 10);
      if (form.applicants) payload.applicant_count = parseInt(form.applicants.replace(/,/g, ""), 10);
      const sourceUrl = form.source_url.trim();
      if (sourceUrl) payload.metadata = { source_url: sourceUrl };
      await api.post(`${CMS_BASE}/exam-competition-metrics`, {
        reason: "Add competition metric via workspace panel",
        payload,
      });
      setAdding(false);
      setForm({ vacancies: "", applicants: "", cutoff_trend: "rising", difficulty_trend: "harder", source_url: "" });
      await load();
    } catch (e) {
      setError(e?.message || "Failed to save metric");
    } finally {
      setSavingNew(false);
    }
  }

  if (!adding && metrics.length === 0 && !loading) {
    return (
      <div className="stack">
        <div className="scrn-head">
          <div className="scrn-tag">Readiness · competition metrics</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>Competition</h2>
        </div>
        {error && <div className="err-row">{error}</div>}
        <div className="card" style={{ borderStyle: "dashed" }}>
          <div className="empty" style={{ padding: "34px 18px" }}>
            <div className="empty-title">No competition metric for this cycle</div>
            <div style={{ maxWidth: 440, margin: "0 auto 14px" }}>
              Add vacancy, applicant ratio and cutoff trends. The planner only adapts to a locked
              metric — drafts stay internal.
            </div>
            <button className="btn primary" onClick={() => setAdding(true)}>
              Add competition metric
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="scrn-head">
        <div>
          <div className="scrn-tag">Readiness · competition metrics</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }}>Competition</h2>
        </div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn small" onClick={load} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
          {!adding && (
            <button className="btn primary small" onClick={() => setAdding(true)}>
              + Add metric
            </button>
          )}
        </div>
      </div>

      {error && <div className="err-row">{error}</div>}

      {adding && (
        <div className="card">
          <div className="card-head">
            <h4 className="oc-title">New competition metric</h4>
          </div>
          <div className="card-body grid3">
            <div className="field">
              <div className="field-lbl">Vacancies</div>
              <input
                className="input"
                placeholder="e.g. 1056"
                value={form.vacancies}
                onChange={(e) => setForm((f) => ({ ...f, vacancies: e.target.value }))}
              />
            </div>
            <div className="field">
              <div className="field-lbl">Applicants</div>
              <input
                className="input"
                placeholder="e.g. 1,100,000"
                value={form.applicants}
                onChange={(e) => setForm((f) => ({ ...f, applicants: e.target.value }))}
              />
            </div>
            <div className="field">
              <div className="field-lbl">Cutoff trend</div>
              <select
                className="input"
                value={form.cutoff_trend}
                onChange={(e) => setForm((f) => ({ ...f, cutoff_trend: e.target.value }))}
              >
                <option value="rising">rising</option>
                <option value="flat">flat</option>
                <option value="falling">falling</option>
              </select>
            </div>
            <div className="field">
              <div className="field-lbl">Difficulty trend</div>
              <select
                className="input"
                value={form.difficulty_trend}
                onChange={(e) => setForm((f) => ({ ...f, difficulty_trend: e.target.value }))}
              >
                <option value="harder">harder</option>
                <option value="stable">stable</option>
                <option value="easier">easier</option>
              </select>
            </div>
            <div className="field" style={{ gridColumn: "span 2" }}>
              <div className="field-lbl">Source URL</div>
              <input
                className="input"
                placeholder="official URL"
                value={form.source_url}
                onChange={(e) => setForm((f) => ({ ...f, source_url: e.target.value }))}
              />
            </div>
          </div>
          <div className="card-foot" style={{ justifyContent: "flex-start" }}>
            <button className="btn primary small" onClick={saveMetric} disabled={savingNew}>
              {savingNew ? "Saving…" : "Save as draft"}
            </button>
            <button
              className="btn ghost small"
              onClick={() => { setAdding(false); setError(""); }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* D4: Competition metrics are always pre-filtered to this exam (exam_id set in query).
           The "Exam" column is not shown — all rows belong to the current exam context.
           This table is display-only for the exam column; use the Exam selector above to switch exams. */}
      {metrics.length > 0 && (
        <p className="text-[11px] text-clay-500" data-testid="competition-exam-filter-note">
          Showing metrics for this exam only. The exam column is not displayed — all rows are pre-filtered by exam context and cannot be filtered further here.
        </p>
      )}
      {metrics.length > 0 && (
        <div className="card">
          <table className="t">
            <thead>
              <tr>
                <th>Cycle</th>
                <th>Vacancies</th>
                <th>Applicants</th>
                <th>Ratio</th>
                <th>Cutoff</th>
                <th>Difficulty</th>
                <th>Trust</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => {
                const ratio =
                  m.applicant_ratio ??
                  (m.vacancy_total && m.applicant_count
                    ? (m.applicant_count / m.vacancy_total).toFixed(0) + ":1"
                    : "—");
                return (
                  <tr key={m.id}>
                    <td className="row-sub">{m.exam_cycle_id ?? cycle?.cycle_name ?? "—"}</td>
                    <td className="num">{m.vacancy_total?.toLocaleString() ?? "—"}</td>
                    <td className="num">{m.applicant_count?.toLocaleString() ?? "—"}</td>
                    <td className="num">{ratio}</td>
                    <td>
                      <span className="badge neutral no-dot">{m.cutoff_trend ?? "—"}</span>
                    </td>
                    <td>
                      <span className="badge neutral no-dot">{m.difficulty_trend ?? "—"}</span>
                    </td>
                    <td><TrustBadge status={m.reviewer_status ?? "pending"} /></td>
                    <td style={{ textAlign: "right" }}>
                      {m.reviewer_status !== "locked" && (
                        <button
                          className="btn small primary"
                          disabled={busyId === m.id}
                          onClick={() => lockMetric(m.id)}
                        >
                          {busyId === m.id ? "…" : "Lock"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
