/**
 * ExamPublishImpact — Wave 4.6D read-only Publish Impact panel.
 *
 * Console-only (variant="console") surface that frames, for the URL exam:
 *   1. WHAT REACHES ASPIRANTS  — verified/locked only (exam-summary + official updates)
 *   2. WHAT THE PLANNER CONSUMES — the composed planner-input set (no single read)
 *   3. WHAT IS EXCLUDED & WHY   — reviewed-not-locked + pending/needs-review/rejected
 *      coverage / syllabus / PYQ, with reviewer_status + notes as the reason
 *   4. MOCK / TEMPLATE IMPACT   — per-phase verdict from /mock-readiness (4.6D0-BE)
 *   + EVIDENCE TRACE via the existing ExamEvidenceDrawer.
 *
 * Locks: read-only (no mutations — the activate action stays in the mounted
 * ReviewActivatePanel); D-E no percentage (scores render as glossary priority
 * bands / counts / labels); reuses console context (readiness) — never refetches
 * it; never calls recruitment publish_impact or get_plan_impact. Each section
 * fetches independently so one failure/empty doesn't blank the panel.
 */
import React, { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { useExamWorkspace } from "./ExamWorkspaceContext";
import ReviewActivatePanel from "./panels/ReviewActivatePanel";
import { band, REVIEWER_STATUS_LABELS } from "../../../features/admin/exam-intelligence/ExamIntelGlossary";

const CMS_BASE = "/api/admin/exam-intelligence-cms";
const EI_BASE = "/api/admin/exam-intelligence";
const ASPIRANT_BASE = "/api/exam-intelligence";

const EXCLUDED_COVERAGE_STATUSES = ["reviewed", "pending_review", "draft", "rejected"];

function statusLabel(status) {
  if (!status) return "—";
  // Reuse the glossary vocabulary where it defines the token; otherwise show
  // the existing reviewer_status token verbatim — coin no new words.
  return REVIEWER_STATUS_LABELS[status]?.label || status;
}

function priorityLabel(score) {
  if (score === null || score === undefined || score === "") return null;
  // D-E: a 0–100 priority is rendered as a glossary band, never a percentage.
  return band(score).label;
}

// ── Independent read hook (loading | data | error); no env import ──────────
function useRead(url, enabled = true) {
  const [status, setStatus] = useState("idle");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!enabled || !url) {
      setStatus("idle");
      return undefined;
    }
    let cancelled = false;
    setStatus("loading");
    setError("");
    api
      .get(url)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setStatus("data");
      })
      .catch((e) => {
        if (cancelled) return;
        setData(null);
        setError(e?.message || "Failed to load");
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [url, enabled]);

  return { status, data, error };
}

// Papers → questions FE join: PYQ has no exam-scoped excluded-questions read.
function useExcludedPyq(examId) {
  const [status, setStatus] = useState("idle");
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!examId) {
      setStatus("idle");
      return undefined;
    }
    let cancelled = false;
    setStatus("loading");
    setError("");
    (async () => {
      try {
        const p = await api.get(`${CMS_BASE}/pyq-papers?exam_id=${encodeURIComponent(examId)}&limit=200`);
        const papers = p?.items || [];
        const lists = await Promise.all(
          papers.map((pp) =>
            api
              .get(`${CMS_BASE}/pyq-questions?pyq_paper_id=${encodeURIComponent(pp.id)}&reviewer_status=pending&limit=200`)
              .then((q) => (q?.items || []).map((row) => ({ ...row, paper_code: pp.paper_code })))
              .catch(() => []), // one bad paper must not blank the PYQ section
          ),
        );
        if (cancelled) return;
        setRows(lists.flat());
        setStatus("data");
      } catch (e) {
        if (cancelled) return;
        setError(e?.message || "Failed to load PYQ");
        setStatus("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [examId]);

  return { status, rows, error };
}

// Evidence trace (View 8): on-demand drill to GET /api/evidence/{kind}/{id}.
// Deliberately NOT the shared ExamEvidenceDrawer — that renders a ConfidencePill
// percentage, which would break the D-E "no percentage" lock. Shows the trust
// envelope (status / source) only.
function EvidenceTrace({ kind, rowId }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("idle");

  useEffect(() => {
    if (!open || !kind || !rowId) return undefined;
    let cancelled = false;
    setStatus("loading");
    api
      .get(`/api/evidence/${encodeURIComponent(kind)}/${encodeURIComponent(rowId)}`)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setStatus("data");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [open, kind, rowId]);

  const row = data?.row || {};
  return (
    <div style={{ marginTop: 2 }}>
      <button
        type="button"
        className="btn small"
        style={{ fontSize: 9.5, padding: "1px 6px" }}
        data-testid={`evidence-toggle-${rowId}`}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "Hide evidence" : "Evidence"}
      </button>
      {open && status === "loading" && <span className="row-sub" data-testid={`evidence-loading-${rowId}`}> loading…</span>}
      {open && status === "error" && <span className="err-row" data-testid={`evidence-error-${rowId}`}> could not load</span>}
      {open && status === "data" && (
        <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-mute)" }} data-testid={`evidence-trace-${rowId}`}>
          {" "}
          {statusLabel(data?.trust?.status || row.reviewer_status)}
          {row.source_url ? ` · ${row.source_url}` : ""}
          {row.source_basis ? ` · ${row.source_basis}` : ""}
        </span>
      )}
    </div>
  );
}

// ── Presentational helpers ──────────────────────────────────────────────────
function Section({ title, sub, testId, children }) {
  return (
    <section
      data-testid={testId}
      style={{ border: "1px solid var(--rule)", borderRadius: 6, padding: "14px 16px", background: "var(--paper)" }}
    >
      <div className="lbl" style={{ fontSize: 10.5, letterSpacing: "0.06em", textTransform: "uppercase" }}>{title}</div>
      {sub && <div className="row-sub" style={{ marginTop: 2, marginBottom: 8 }}>{sub}</div>}
      <div style={{ marginTop: sub ? 0 : 8 }}>{children}</div>
    </section>
  );
}

function ReadState({ read, empty, children, testId }) {
  if (read.status === "loading" || read.status === "idle") {
    return <div className="row-sub" data-testid={`${testId}-loading`}>Loading…</div>;
  }
  if (read.status === "error") {
    return <div className="err-row" data-testid={`${testId}-error`}>{read.error || "Could not load."}</div>;
  }
  if (empty) {
    return <div className="row-sub" data-testid={`${testId}-empty`}>Nothing here.</div>;
  }
  return children;
}

// ── Panel ───────────────────────────────────────────────────────────────────
export default function ExamPublishImpact({ onGotoTab }) {
  const { exam, readiness } = useExamWorkspace();
  const examId = exam?.id || null;
  const examKey = exam?.slug || exam?.id || null;

  // exam-summary = verified/locked-only aspirant read (locked coverage topics,
  // verified PYQ topic counts, competition_series). Fetched once (not in context).
  const summary = useRead(examKey ? `${ASPIRANT_BASE}/exams/${encodeURIComponent(examKey)}` : null);
  // official + verified policy updates (affects_plan / affects_deadline flags).
  const official = useRead(
    examId ? `${EI_BASE}/policy-updates?exam_id=${encodeURIComponent(examId)}&status=verified&source_type=official&limit=200` : null,
  );
  // locked competition metrics the planner consumes.
  const lockedComp = useRead(
    examId ? `${CMS_BASE}/exam-competition-metrics?exam_id=${encodeURIComponent(examId)}&reviewer_status=locked&limit=200` : null,
  );
  // all coverage rows (partitioned client-side: locked reaches aspirants,
  // the rest are excluded with their reviewer_status/notes reason).
  const coverage = useRead(
    examId ? `${CMS_BASE}/exam-topic-coverage?exam_id=${encodeURIComponent(examId)}&limit=200` : null,
  );
  const syllabus = useRead(
    examId ? `${CMS_BASE}/syllabus-topic-mentions?exam_id=${encodeURIComponent(examId)}&limit=200` : null,
  );
  const pyq = useExcludedPyq(examId);
  // View 7 — mock/template impact.
  const mock = useRead(examId ? `${EI_BASE}/exams/${encodeURIComponent(examId)}/mock-readiness` : null);

  const summaryData = summary.data || {};
  const lockedTopics = summaryData.topics || [];
  const verifiedPyqCounts = summaryData.verified_pyq_counts || {};
  const verifiedPyqTotal = Object.values(verifiedPyqCounts).reduce((n, v) => n + (Number(v) || 0), 0);
  const competitionSeries = summaryData.competition_series || [];
  const officialUpdates = official.data?.items || [];
  const lockedCompRows = lockedComp.data?.items || [];

  const coverageRows = coverage.data?.items || [];
  const excludedCoverage = coverageRows.filter((r) => EXCLUDED_COVERAGE_STATUSES.includes(r.reviewer_status));
  const syllabusRows = syllabus.data?.items || [];
  const excludedSyllabus = syllabusRows.filter((r) => r.reviewer_status && !["verified", "locked"].includes(r.reviewer_status));

  // Context reuse: the topic_coverage snapshot already in console context — no refetch.
  const tcSnapshot = readiness?.topic_coverage || null;

  const mockPhases = mock.data?.phases || [];
  const mockSummary = mock.data?.summary || null;
  const mockThresholds = mock.data?.thresholds || null;

  return (
    <div className="stack" data-testid="exam-publish-impact">
      <div className="scrn-head">
        <div>
          <div className="scrn-tag">Publish impact · read-only</div>
          <h2 className="oc-title disp" style={{ fontSize: 20, marginTop: 3 }} data-testid="publish-impact-exam">
            {exam?.name ?? examId}
          </h2>
        </div>
      </div>

      <div style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))" }}>
        {/* 1 — What reaches aspirants */}
        <Section title="What reaches aspirants" sub="Verified / locked rows only." testId="impact-reaches-aspirants">
          <ReadState read={summary} testId="reaches" empty={!summary.data?.available}>
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 4 }}>
              <li className="row" style={{ justifyContent: "space-between" }}>
                <span>Locked topic coverage</span>
                <span className="mono" data-testid="reaches-locked-topics">{lockedTopics.length}</span>
              </li>
              <li className="row" style={{ justifyContent: "space-between" }}>
                <span>Verified PYQ topic tags</span>
                <span className="mono" data-testid="reaches-verified-pyq">{verifiedPyqTotal}</span>
              </li>
              <li className="row" style={{ justifyContent: "space-between" }}>
                <span>Verified syllabus mentions</span>
                <span className="mono">{summaryData.verified_syllabus_mentions ?? 0}</span>
              </li>
              <li className="row" style={{ justifyContent: "space-between" }}>
                <span>Competition cycles (reviewed/locked)</span>
                <span className="mono">{competitionSeries.length}</span>
              </li>
            </ul>
            {lockedTopics.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <div className="lbl" style={{ fontSize: 9.5 }}>Top locked topics</div>
                {lockedTopics.slice(0, 5).map((t) => (
                  <div key={t.topic_id} className="row" style={{ justifyContent: "space-between", fontSize: 12 }}>
                    <span className="truncate">{t.topic_name || t.topic_slug || t.topic_id}</span>
                    {priorityLabel(t.exam_priority_score) && (
                      <span className="badge ink no-dot" style={{ fontSize: 9 }} data-testid="reaches-priority-band">
                        {priorityLabel(t.exam_priority_score)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </ReadState>
        </Section>

        {/* 2 — What the planner consumes (composed) */}
        <Section
          title="What the Study OS planner consumes"
          sub="Composed planner-input set (no single read): locked coverage + verified PYQ + locked competition + official-update flags."
          testId="impact-planner-consumes"
        >
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 4 }}>
            <li className="row" style={{ justifyContent: "space-between" }}>
              <span>Locked coverage topics</span>
              <span className="mono">{lockedTopics.length}</span>
            </li>
            <li className="row" style={{ justifyContent: "space-between" }}>
              <span>Verified PYQ tags</span>
              <span className="mono">{verifiedPyqTotal}</span>
            </li>
            <li className="row" style={{ justifyContent: "space-between" }}>
              <span>Locked competition metrics</span>
              <ReadState read={lockedComp} testId="planner-comp" empty={false}>
                <span className="mono" data-testid="planner-locked-comp">{lockedCompRows.length}</span>
              </ReadState>
            </li>
            <li>
              <ReadState read={official} testId="planner-official" empty={officialUpdates.length === 0}>
                <div>
                  <div className="lbl" style={{ fontSize: 9.5 }}>Official plan/deadline updates</div>
                  {officialUpdates.slice(0, 6).map((u) => (
                    <div key={u.id} className="row" style={{ gap: 6, fontSize: 12 }} data-testid="planner-official-row">
                      <span className="truncate">{u.title}</span>
                      {u.affects_plan && <span className="badge info no-dot" style={{ fontSize: 8.5 }}>plan</span>}
                      {u.affects_deadline && <span className="badge pending no-dot" style={{ fontSize: 8.5 }}>deadline</span>}
                    </div>
                  ))}
                </div>
              </ReadState>
            </li>
          </ul>
        </Section>

        {/* 3 — What is excluded & why */}
        <Section
          title="What is excluded & why"
          sub="Reviewed-but-not-locked and pending / needs-review / rejected rows never reach the planner."
          testId="impact-excluded"
        >
          {tcSnapshot && (
            <div className="row-sub" style={{ marginBottom: 6 }} data-testid="excluded-tc-snapshot">
              Coverage snapshot · reviewed {tcSnapshot.reviewed ?? 0} · pending {tcSnapshot.pending ?? 0} · draft {tcSnapshot.draft ?? 0} · locked {tcSnapshot.locked ?? 0}
            </div>
          )}
          <div className="lbl" style={{ fontSize: 9.5, marginTop: 4 }}>Topic coverage</div>
          <ReadState read={coverage} testId="excluded-coverage" empty={excludedCoverage.length === 0}>
            {excludedCoverage.slice(0, 8).map((r) => (
              <div key={r.id} style={{ borderBottom: "1px solid var(--rule)", padding: "4px 0" }} data-testid="excluded-coverage-row">
                <div className="row" style={{ justifyContent: "space-between", fontSize: 12 }}>
                  <span className="truncate">{r.topic_id}</span>
                  <span className="badge draft no-dot" style={{ fontSize: 9 }}>{statusLabel(r.reviewer_status)}</span>
                </div>
                {(r.review_notes || r.reviewer_notes) && (
                  <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-mute)" }}>{r.review_notes || r.reviewer_notes}</div>
                )}
                <EvidenceTrace kind="exam_topic_coverage" rowId={r.id} />
              </div>
            ))}
          </ReadState>

          <div className="lbl" style={{ fontSize: 9.5, marginTop: 8 }}>Syllabus mentions</div>
          <ReadState read={syllabus} testId="excluded-syllabus" empty={excludedSyllabus.length === 0}>
            {excludedSyllabus.slice(0, 6).map((r) => (
              <div key={r.id} className="row" style={{ justifyContent: "space-between", fontSize: 12 }} data-testid="excluded-syllabus-row">
                <span className="truncate">{r.topic_id || r.normalized_text || r.id}</span>
                <span className="badge draft no-dot" style={{ fontSize: 9 }}>{statusLabel(r.reviewer_status)}</span>
              </div>
            ))}
          </ReadState>

          <div className="lbl" style={{ fontSize: 9.5, marginTop: 8 }}>PYQ questions (papers → questions)</div>
          <ReadState read={pyq} testId="excluded-pyq" empty={pyq.rows.length === 0}>
            {pyq.rows.slice(0, 6).map((r) => (
              <div key={r.id} className="row" style={{ justifyContent: "space-between", fontSize: 12 }} data-testid="excluded-pyq-row">
                <span className="truncate">{r.paper_code ? `${r.paper_code} · ` : ""}{r.question_number ?? r.id}</span>
                <span className="badge draft no-dot" style={{ fontSize: 9 }}>{statusLabel(r.reviewer_status)}</span>
              </div>
            ))}
          </ReadState>
        </Section>

        {/* 4 — Mock / template impact (View 7) */}
        <Section title="Mock / template impact" sub="Per-phase content readiness for mock generation." testId="impact-mock">
          <ReadState read={mock} testId="mock" empty={mockPhases.length === 0 && !mockSummary}>
            {mockSummary && (
              <div className="row" style={{ gap: 8, marginBottom: 6 }} data-testid="mock-summary">
                <span className="badge info no-dot" style={{ fontSize: 9 }}>ready {mockSummary.ready ?? 0}</span>
                <span className="badge pending no-dot" style={{ fontSize: 9 }}>thin_bank {mockSummary.thin_bank ?? 0}</span>
                <span className="badge blocker no-dot" style={{ fontSize: 9 }}>blocked {mockSummary.blocked ?? 0}</span>
              </div>
            )}
            {mockThresholds && (
              <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-mute)", marginBottom: 6 }}>
                thresholds · min/section {mockThresholds.min_per_section} · min locked coverage {mockThresholds.min_locked_coverage}
              </div>
            )}
            {mockPhases.map((ph) => {
              const verdict = ph.readiness_verdict?.summary || {};
              return (
                <div key={ph.exam_phase_id} className="row" style={{ justifyContent: "space-between", fontSize: 12 }} data-testid="mock-phase-row">
                  <span className="truncate">{ph.phase_name || ph.phase_slug || ph.exam_phase_id}</span>
                  <span className="mono" style={{ fontSize: 9.5 }} data-testid="mock-phase-verdict">
                    ready {verdict.ready ?? 0} · thin_bank {verdict.thin_bank ?? 0} · blocked {verdict.blocked ?? 0}
                  </span>
                </div>
              );
            })}
          </ReadState>
        </Section>
      </div>

      {/* Activate action — mount the EXISTING Review & Activate panel as-is. */}
      <Section title="Review & activate" testId="impact-review-activate">
        <ReviewActivatePanel onGotoTab={onGotoTab} />
      </Section>
    </div>
  );
}
