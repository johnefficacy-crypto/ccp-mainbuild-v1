import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { HandHeart } from "lucide-react";

// Lightweight accountability-partner onboarding wizard. Matching is not wired to
// a backend yet, so this is a UI shell that captures preferences and confirms a
// waitlist join — the exam-page CTA that routes here must never dead-end. When a
// matching service lands, `submit()` becomes the POST and the confirmation shows
// suggested matches instead of the waitlist copy.

const STAGES = ["Just starting", "Mid preparation", "Revision", "Final stretch"];
const CHECKINS = ["Morning", "Evening", "Flexible"];
const STYLES = ["Gentle nudges", "Strict / no excuses", "Data-driven"];
const AVAILABILITY = ["Weekday evenings", "Weekday mornings", "Weekends", "Anytime"];
const LANGUAGES = ["English", "Hindi", "Bilingual"];

function Field({ label, children }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-widest text-muted-foreground font-semibold">{label}</span>
      {children}
    </label>
  );
}

function Select({ value, onChange, options, testId, placeholder }) {
  return (
    <select
      value={value}
      onChange={onChange}
      data-testid={testId}
      className="rounded-lg border border-clay-200 bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-clay-400"
    >
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}

export default function AccountabilityWizard() {
  const [params] = useSearchParams();
  const [form, setForm] = useState({
    exam: params.get("exam") || "",
    stage: "",
    checkin: "",
    style: "",
    availability: "",
    language: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  if (submitted) {
    return (
      <div className="soft-card rounded-2xl p-6" data-testid="accountability-wizard-done">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="h-8 w-8 grid place-items-center rounded-lg bg-sage-100 text-sage-700">
            <HandHeart className="h-4 w-4" />
          </span>
          <div className="font-heading text-lg font-semibold">You're on the accountability pool</div>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          We'll match you with a partner preparing for{" "}
          <strong className="text-foreground/80">{form.exam || "your exam"}</strong> and notify you when a match is
          ready. Partner matching is rolling out soon — your preferences are saved.
        </p>
        <button
          type="button"
          className="btn btn-ghost mt-4"
          data-testid="accountability-wizard-restart"
          onClick={() => setSubmitted(false)}
        >
          Edit preferences
        </button>
      </div>
    );
  }

  return (
    <div className="soft-card rounded-2xl p-6" data-testid="accountability-wizard">
      <div className="font-heading text-lg font-semibold">Find an accountability partner</div>
      <p className="text-sm text-muted-foreground mt-1">
        Tell us how you like to be held accountable — we'll pair you with someone on the same path and cadence.
      </p>

      <div className="mt-4 grid sm:grid-cols-2 gap-3">
        <Field label="Target exam">
          <input
            type="text"
            value={form.exam}
            onChange={set("exam")}
            data-testid="wizard-exam"
            placeholder="e.g. upsc-cse"
            className="rounded-lg border border-clay-200 bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-clay-400"
          />
        </Field>
        <Field label="Preparation stage">
          <Select value={form.stage} onChange={set("stage")} options={STAGES} testId="wizard-stage" placeholder="Select stage" />
        </Field>
        <Field label="Daily check-in preference">
          <Select value={form.checkin} onChange={set("checkin")} options={CHECKINS} testId="wizard-checkin" placeholder="Select time" />
        </Field>
        <Field label="Accountability style">
          <Select value={form.style} onChange={set("style")} options={STYLES} testId="wizard-style" placeholder="Select style" />
        </Field>
        <Field label="Availability window">
          <Select value={form.availability} onChange={set("availability")} options={AVAILABILITY} testId="wizard-availability" placeholder="Select availability" />
        </Field>
        <Field label="Language preference">
          <Select value={form.language} onChange={set("language")} options={LANGUAGES} testId="wizard-language" placeholder="Select language" />
        </Field>
      </div>

      <button
        type="button"
        className="btn btn-primary mt-4 inline-flex"
        data-testid="accountability-wizard-submit"
        onClick={() => setSubmitted(true)}
      >
        <HandHeart className="h-4 w-4" /> Join accountability pool
      </button>
    </div>
  );
}
