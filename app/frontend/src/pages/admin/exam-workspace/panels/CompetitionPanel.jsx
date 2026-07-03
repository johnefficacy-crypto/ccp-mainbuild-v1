import React, { useCallback, useEffect, useState } from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { api } from "../../../../lib/api";

// Vertical reservation categories, v1 (resolutions §OD-1). Kept in sync with
// the `reservation_categories` seed in migration 215 — do not add PwBD /
// ex-servicemen / domicile here (separate horizontal dimension, later).
const CATEGORIES = [
  { code: "general", label: "General" },
  { code: "ews", label: "EWS" },
  { code: "obc", label: "OBC" },
  { code: "sc", label: "SC" },
  { code: "st", label: "ST" },
];

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

const emptyCutoffRow = () => ({ marks: "", max_marks: "" });
const emptyCutoffMap = () =>
  Object.fromEntries(CATEGORIES.map((c) => [c.code, emptyCutoffRow()]));
const emptyVacancyMap = () => Object.fromEntries(CATEGORIES.map((c) => [c.code, ""]));

export default function CompetitionPanel() {
  const { exam, cycle, phases } = useExamWorkspace();

  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({
    exam_phase_id: "",
    vacancies: "",
    applicants: "",
    vacancy_by_category: emptyVacancyMap(),
    cutoff_by_category: emptyCutoffMap(),
    difficulty_level: "stable",
    difficulty_basis: "",
    source_url: "",
  });
  const [savingNew, setSavingNew] = useState(false);
  const isPhaseScoped = !!form.exam_phase_id;

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
      // Allowed fields = _COMPETITION_FIELDS (admin_exam_intel_cms.py).
      // metric_kind is server-derived from exam_phase_id (OD-11): a row with
      // exam_phase_id set is phase_cutoff (owns cutoff/difficulty only); a
      // row without it is cycle_summary (owns vacancy/pressure only) — the
      // two field groups are therefore mutually exclusive here, matching the
      // server-side field-ownership check.
      const payload = {
        exam_id: exam?.id || null,
        exam_cycle_id: cycle?.id || null,
      };
      if (form.exam_phase_id) {
        payload.exam_phase_id = form.exam_phase_id;
        const cutoff_by_category = {};
        for (const c of CATEGORIES) {
          const row = form.cutoff_by_category[c.code];
          if (row.marks !== "") {
            cutoff_by_category[c.code] = { marks: Number(row.marks) };
            if (row.max_marks !== "") cutoff_by_category[c.code].max_marks = Number(row.max_marks);
          }
        }
        if (Object.keys(cutoff_by_category).length) payload.cutoff_by_category = cutoff_by_category;
        if (form.difficulty_basis.trim()) {
          payload.difficulty_assessment = { level: form.difficulty_level, basis: form.difficulty_basis.trim() };
        }
      } else {
        if (form.vacancies) payload.vacancy_total = parseInt(form.vacancies, 10);
        if (form.applicants) payload.applicant_count = parseInt(form.applicants.replace(/,/g, ""), 10);
        const vacancy_by_category = {};
        for (const c of CATEGORIES) {
          const v = form.vacancy_by_category[c.code];
          if (v !== "") vacancy_by_category[c.code] = parseInt(v, 10);
        }
        if (Object.keys(vacancy_by_category).length) payload.vacancy_by_category = vacancy_by_category;
      }
      const sourceUrl = form.source_url.trim();
      if (sourceUrl) payload.metadata = { source_url: sourceUrl };
      await api.post(`${CMS_BASE}/exam-competition-metrics`, {
        reason: "Add competition metric via workspace panel",
        payload,
      });
      setAdding(false);
      setForm({
        exam_phase_id: "", vacancies: "", applicants: "",
        vacancy_by_category: emptyVacancyMap(), cutoff_by_category: emptyCutoffMap(),
        difficulty_level: "stable", difficulty_basis: "", source_url: "",
      });
      await load();
    } catch (e) {
      setError(e?.message || "Failed to save metric");
    } finally {
      setSavingNew(false);
    }
  }

  function setCutoffField(code, field, value) {
    setForm((f) => ({
      ...f,
      cutoff_by_category: { ...f.cutoff_by_category, [code]: { ...f.cutoff_by_category[code], [field]: value } },
    }));
  }

  function setVacancyField(code, value) {
    setForm((f) => ({ ...f, vacancy_by_category: { ...f.vacancy_by_category, [code]: value } }));
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
            <div className="field" style={{ gridColumn: "span 2" }}>
              <div className="field-lbl">Phase (leave unset for a cycle-level vacancy row)</div>
              <select
                className="input"
                data-testid="competition-phase-select"
                value={form.exam_phase_id}
                onChange={(e) => setForm((f) => ({ ...f, exam_phase_id: e.target.value }))}
              >
                <option value="">— cycle-level (vacancy / applicants) —</option>
                {(phases || []).map((p) => (
                  <option key={p.id} value={p.id}>{p.phase_name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <div className="field-lbl">Source URL</div>
              <input
                className="input"
                placeholder="official URL"
                value={form.source_url}
                onChange={(e) => setForm((f) => ({ ...f, source_url: e.target.value }))}
              />
            </div>
          </div>

          {!isPhaseScoped && (
            <div className="card-body grid3">
              <div className="field">
                <div className="field-lbl">Vacancies (total)</div>
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
              <div className="field" style={{ gridColumn: "span 3" }}>
                <div className="field-lbl">Vacancy by category</div>
                <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                  {CATEGORIES.map((c) => (
                    <div key={c.code} className="field" style={{ minWidth: 90 }}>
                      <div className="field-lbl">{c.label}</div>
                      <input
                        className="input"
                        data-testid={`vacancy-${c.code}`}
                        placeholder="—"
                        value={form.vacancy_by_category[c.code]}
                        onChange={(e) => setVacancyField(c.code, e.target.value)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {isPhaseScoped && (
            <div className="card-body">
              <div className="field">
                <div className="field-lbl">Cutoff by category (marks / max marks)</div>
                <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                  {CATEGORIES.map((c) => (
                    <div key={c.code} className="field" style={{ minWidth: 140 }}>
                      <div className="field-lbl">{c.label}</div>
                      <input
                        className="input"
                        data-testid={`cutoff-marks-${c.code}`}
                        placeholder="marks"
                        value={form.cutoff_by_category[c.code].marks}
                        onChange={(e) => setCutoffField(c.code, "marks", e.target.value)}
                      />
                      <input
                        className="input"
                        style={{ marginTop: 4 }}
                        placeholder="max marks (optional)"
                        value={form.cutoff_by_category[c.code].max_marks}
                        onChange={(e) => setCutoffField(c.code, "max_marks", e.target.value)}
                      />
                    </div>
                  ))}
                </div>
              </div>
              <div className="field" style={{ marginTop: 10 }}>
                <div className="field-lbl">Difficulty assessment (descriptive only — not planner input)</div>
                <div className="row" style={{ gap: 8 }}>
                  <select
                    className="input"
                    style={{ maxWidth: 140 }}
                    value={form.difficulty_level}
                    onChange={(e) => setForm((f) => ({ ...f, difficulty_level: e.target.value }))}
                  >
                    <option value="harder">harder</option>
                    <option value="stable">stable</option>
                    <option value="easier">easier</option>
                  </select>
                  <input
                    className="input"
                    placeholder="basis (8-500 chars, e.g. \"cutoff rose 4th consecutive year\")"
                    value={form.difficulty_basis}
                    onChange={(e) => setForm((f) => ({ ...f, difficulty_basis: e.target.value }))}
                  />
                </div>
              </div>
            </div>
          )}

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
                // Ratio display is not computed client-side (resolutions
                // §0.3 fixes the inverse applicant_count/vacancy_total bug
                // by deriving selection_rate server-side once a
                // provenance-proven denominator exists — PR 2). Until then
                // this column shows the deprecated legacy value, labelled.
                const cutoffEntries = Object.entries(m.cutoff_by_category || {});
                const difficulty = m.difficulty_assessment || {};
                return (
                  <tr key={m.id}>
                    <td className="row-sub">{m.exam_cycle_id ?? cycle?.cycle_name ?? "—"}</td>
                    <td className="num">{m.vacancy_total?.toLocaleString() ?? "—"}</td>
                    <td className="num">{m.applicant_count?.toLocaleString() ?? "—"}</td>
                    <td className="num" title="Legacy value — pending PR 2 provenance-proven ratio">
                      {m.selection_ratio != null ? `${m.selection_ratio} (legacy)` : "—"}
                    </td>
                    <td>
                      {cutoffEntries.length ? (
                        <span className="badge neutral no-dot">
                          {cutoffEntries.map(([code, v]) => `${code}:${v?.marks ?? "—"}`).join(", ")}
                        </span>
                      ) : "—"}
                    </td>
                    <td>
                      {difficulty.level ? (
                        <span className="badge neutral no-dot">{difficulty.level}</span>
                      ) : "—"}
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
