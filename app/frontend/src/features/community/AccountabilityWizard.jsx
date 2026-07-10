import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { HandHeart } from "lucide-react";

// Lightweight accountability-partner onboarding wizard. Partner matching has no
// backend yet, so this captures preferences DURABLY on this device (localStorage)
// and is explicit that matching is not live — it must not claim server-side
// "joined the pool" state it can't back up. When a matching service lands,
// `submit()` becomes the POST and the confirmation shows suggested matches.

const STORAGE_KEY = "cc.accountability.prefs";

const STAGES = ["Just starting", "Mid preparation", "Revision", "Final stretch"];
const CHECKINS = ["Morning", "Evening", "Flexible"];
const STYLES = ["Gentle nudges", "Strict / no excuses", "Data-driven"];
const AVAILABILITY = ["Weekday evenings", "Weekday mornings", "Weekends", "Anytime"];
const LANGUAGES = ["English", "Hindi", "Bilingual"];

function loadPrefs() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function savePrefs(prefs) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    return true;
  } catch {
    return false; // private mode / quota — degrade to session-only
  }
}

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
  const stored = loadPrefs();
  const [form, setForm] = useState({
    // ?exam= (arriving from an exam page) takes precedence, else last saved.
    exam: params.get("exam") || stored?.exam || "",
    stage: stored?.stage || "",
    checkin: stored?.checkin || "",
    style: stored?.style || "",
    availability: stored?.availability || "",
    language: stored?.language || "",
  });
  const [saved, setSaved] = useState(false);
  const [persisted, setPersisted] = useState(true);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  function submit() {
    setPersisted(savePrefs(form));
    setSaved(true);
  }

  if (saved) {
    return (
      <div className="soft-card rounded-2xl p-6" data-testid="accountability-wizard-done">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="h-8 w-8 grid place-items-center rounded-lg bg-sage-100 text-sage-700">
            <HandHeart className="h-4 w-4" />
          </span>
          <div className="font-heading text-lg font-semibold">Preferences saved</div>
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          {persisted
            ? "Saved on this device."
            : "Captured for this session (couldn't save to this device)."}{" "}
          Accountability partner matching isn't live yet — it's rolling out soon, and we'll use these to pair you with
          someone preparing for <strong className="text-foreground/80">{form.exam || "your exam"}</strong> when it is.
        </p>
        <button
          type="button"
          className="btn btn-ghost mt-4"
          data-testid="accountability-wizard-restart"
          onClick={() => setSaved(false)}
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
        Tell us how you like to be held accountable. Matching is coming soon — your preferences are saved on this device
        so we can pair you with someone on the same path when it's live.
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
        onClick={submit}
      >
        <HandHeart className="h-4 w-4" /> Save my preferences
      </button>
    </div>
  );
}
