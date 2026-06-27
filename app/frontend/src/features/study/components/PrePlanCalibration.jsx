import React, { useMemo, useState } from "react";

const BANDS = [
  {
    value: "strong",
    label: "Strong",
    selectedCls: "border-sage-600 bg-sage-50 text-sage-800",
    hoverCls: "hover:border-sage-400 hover:bg-sage-50/50",
  },
  {
    value: "decent",
    label: "Decent",
    selectedCls: "border-amber-500 bg-amber-50 text-amber-800",
    hoverCls: "hover:border-amber-400 hover:bg-amber-50/50",
  },
  {
    value: "weak",
    label: "Weak",
    selectedCls: "border-rose-500 bg-rose-50 text-rose-800",
    hoverCls: "hover:border-rose-400 hover:bg-rose-50/50",
  },
  {
    value: "new",
    label: "Never studied",
    selectedCls: "border-clay-400 bg-clay-50 text-clay-700",
    hoverCls: "hover:border-clay-300 hover:bg-clay-50/50",
  },
];

const ATTEMPTS_OPTIONS = [
  { value: 0, label: "First attempt" },
  { value: 1, label: "1 attempt" },
  { value: 2, label: "2+ attempts" },
];

// Build the initial band selections from any previously-saved `items`,
// matching on subject_id so an editing user sees their saved answers pressed.
function buildInitialSelections(requiredSubjects, items) {
  const byId = new Map(
    (Array.isArray(items) ? items : [])
      .filter((it) => it && it.subject_id && it.band)
      .map((it) => [String(it.subject_id), it.band]),
  );
  const out = {};
  for (const s of Array.isArray(requiredSubjects) ? requiredSubjects : []) {
    const saved = byId.get(String(s.subject_id));
    if (saved) out[s.subject_id] = saved;
  }
  return out;
}

export default function PrePlanCalibration({
  requiredSubjects,
  items,
  attemptsUsed,
  onSubmit,
  onSkip,
  saving,
  error,
}) {
  const rows = useMemo(
    () => (Array.isArray(requiredSubjects) ? requiredSubjects : []),
    [requiredSubjects],
  );

  // Seed selections from saved items once; re-seed if the subject/item identity
  // changes (e.g. exam switch or a fresh fetch supplying new prefill data).
  const seededSelections = useMemo(
    () => buildInitialSelections(rows, items),
    [rows, items],
  );
  const seedKey = useMemo(
    () =>
      JSON.stringify(
        rows.map((s) => [s.subject_id, seededSelections[s.subject_id] || ""]),
      ),
    [rows, seededSelections],
  );

  const [selections, setSelections] = useState(seededSelections);
  const [seenSeed, setSeenSeed] = useState(seedKey);
  const [attempts, setAttempts] = useState(
    typeof attemptsUsed === "number" ? attemptsUsed : 0,
  );
  const [seenAttempts, setSeenAttempts] = useState(attemptsUsed);

  // Re-prefill when the seed changes (render-phase reconcile — no effect).
  if (seedKey !== seenSeed) {
    setSelections(seededSelections);
    setSeenSeed(seedKey);
  }
  if (attemptsUsed !== seenAttempts) {
    setAttempts(typeof attemptsUsed === "number" ? attemptsUsed : 0);
    setSeenAttempts(attemptsUsed);
  }

  const answeredCount = rows.reduce(
    (n, s) => n + (selections[s.subject_id] ? 1 : 0),
    0,
  );
  const total = rows.length;
  const complete = total > 0 && answeredCount === total;
  const isSaving = Boolean(saving);
  const canSave = complete && !isSaving;

  function handleBandSelect(subjectId, bandValue) {
    setSelections((prev) => ({ ...prev, [subjectId]: bandValue }));
  }

  function handleSave() {
    if (!canSave) return;
    const bands_payload = rows.map((s) => ({
      subject_id: s.subject_id,
      band: selections[s.subject_id],
    }));
    onSubmit(bands_payload, attempts);
  }

  return (
    <div
      className="rounded-2xl border border-[#E7DECB] bg-white p-6 space-y-5"
      data-testid="preplan-calibration"
    >
      {/* Header */}
      <div>
        <div className="text-[11px] uppercase tracking-[0.18em] text-clay-700 mb-1">
          Study plan setup
        </div>
        <h2 className="font-heading text-[20px] leading-tight text-clay-900">
          Calibrate your starting point
        </h2>
        <p className="text-[13px] text-clay-700 mt-1.5">
          Tell us how prepared you feel for each subject. This helps us personalize your first
          study plan. You can update it anytime.
        </p>
        <p className="text-[12px] text-clay-500 mt-2 border border-[#E7DECB] rounded-lg px-3 py-2 bg-[#FBF8F2]">
          This is self-reported and will be refined as you take practice tests.
        </p>
      </div>

      {/* Error banner */}
      {error ? (
        <div
          className="rounded-xl border border-rose-300 bg-rose-50 px-3 py-2"
          role="alert"
          data-testid="calibration-error"
        >
          <p className="text-[12.5px] text-rose-800">{error}</p>
        </div>
      ) : null}

      {/* Subject grid */}
      {rows.length > 0 ? (
        <div className="grid sm:grid-cols-2 gap-3">
          {rows.map((s) => {
            const selected = selections[s.subject_id];
            return (
              <div
                key={s.subject_id}
                className="rounded-xl border border-[#E7DECB] bg-white/70 p-3.5"
              >
                <div className="font-medium text-[14px] text-clay-900 mb-2.5">
                  {s.subject_name}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {BANDS.map((band) => {
                    const isSelected = selected === band.value;
                    return (
                      <button
                        key={band.value}
                        type="button"
                        onClick={() => handleBandSelect(s.subject_id, band.value)}
                        className={`text-[11.5px] px-2.5 py-1 rounded-full border font-medium transition-all outline-none focus-visible:ring-2 focus-visible:ring-clay-900 focus-visible:ring-offset-1 ${
                          isSelected
                            ? band.selectedCls + " font-semibold"
                            : "border-[#E7DECB] text-clay-700 bg-white " + band.hoverCls
                        }`}
                        aria-pressed={isSelected}
                      >
                        {band.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-clay-700">Loading subjects…</p>
      )}

      {/* Attempts question */}
      <div className="rounded-xl border border-[#E7DECB] bg-[#FBF8F2] p-4">
        <div className="text-[13px] font-medium text-clay-900 mb-2.5">
          How many times have you attempted this exam?
        </div>
        <div className="flex flex-wrap gap-2">
          {ATTEMPTS_OPTIONS.map((opt) => {
            const isSelected = attempts === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setAttempts(opt.value)}
                className={`text-[12px] px-3.5 py-1.5 rounded-full border font-medium transition-all outline-none focus-visible:ring-2 focus-visible:ring-clay-900 focus-visible:ring-offset-1 ${
                  isSelected
                    ? "border-[#2E2218] bg-[#2E2218] text-[#F3EADB]"
                    : "border-[#E7DECB] text-clay-700 bg-white hover:border-clay-400 hover:bg-clay-50/50"
                }`}
                aria-pressed={isSelected}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Completeness helper */}
      {total > 0 && !complete ? (
        <p className="text-[12px] text-clay-700" data-testid="calibration-helper">
          Answer all {total} subjects to continue ({answeredCount}/{total} done).
        </p>
      ) : null}

      {/* Actions */}
      <div className="flex items-center justify-between pt-1">
        <button
          type="button"
          onClick={onSkip}
          disabled={isSaving}
          className="text-[12.5px] text-clay-700 hover:text-clay-900 underline underline-offset-2 transition disabled:opacity-50"
        >
          Skip for now
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={!canSave}
          className="btn btn-primary"
          data-testid="calibration-save-btn"
        >
          {isSaving ? "Saving…" : "Save & continue"}
        </button>
      </div>
    </div>
  );
}
