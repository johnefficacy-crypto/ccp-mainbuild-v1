/**
 * PhaseForm — shared controlled form for a single exam phase row.
 *
 * Source of truth: GuidedExamWizard.jsx StepPhases per-phase row (more complete —
 * includes slug derivation, mode, template toggle, and duplicate-slug validation
 * absent from SetupPanel's simpler add-phase form).
 *
 * Used by:
 *   - GuidedExamWizard.jsx (Step 4 — Phases, one PhaseForm per phase in list)
 *   - SetupPanel.jsx (inline add-phase form)
 */
import React from "react";
import { slugify, cycleBoundSlug } from "../../../../lib/slugify";
import DateField from "../../../../shared/ui/DateField";

const INPUT_CLS = "input w-full";

// Canonical D05 classified phase kinds — mirrors backend
// app/exam_intelligence/document_policy.py CLASSIFIED_PHASE_KINDS (migration 210
// CHECK). NULL/unset = unclassified; do not add values here without a backend change.
export const PHASE_KIND_OPTIONS = [
  { value: "objective_written", label: "Objective written" },
  { value: "descriptive_written", label: "Descriptive written" },
  { value: "mixed_written", label: "Mixed written" },
  { value: "interview", label: "Interview" },
  { value: "physical_test", label: "Physical test" },
  { value: "medical", label: "Medical" },
  { value: "document_verification", label: "Document verification" },
];

function effectiveSlug(phase_name, base_slug) {
  return (base_slug || "").trim() || slugify((phase_name || "").trim());
}

/**
 * @param {{
 *   values: {
 *     phase_name: string, base_slug: string, phase_order: string|number,
 *     mode: string, createTemplate: boolean,
 *     phase_start: string|null, phase_end: string|null,
 *   },
 *   onChange: (key: string, val: any) => void,
 *   cycleName?: string,
 *   year?: string,
 *   showSlug?: boolean,
 *   showMode?: boolean,
 *   showKind?: boolean,
 *   showTemplate?: boolean,
 *   showDates?: boolean,
 *   isDuplicate?: boolean,
 * }} props
 */
export default function PhaseForm({
  values,
  onChange,
  cycleName = "",
  year = "",
  showSlug = true,
  showMode = true,
  showKind = false,
  showTemplate = true,
  showDates = true,
  isDuplicate = false,
  rowId = null,
}) {
  const {
    phase_name = "",
    base_slug = "",
    phase_order = "",
    mode = "",
    phase_kind = "",
    createTemplate = false,
    phase_start = null,
    phase_end = null,
  } = values;

  const effSlug = effectiveSlug(phase_name, base_slug);
  const cbSlug = effSlug && cycleName && year ? cycleBoundSlug(effSlug, year, cycleName) : "";
  const tmplSlug = effSlug ? slugify(effSlug) : "";
  const nameEmpty = !phase_name.trim();

  return (
    <div data-testid="phase-form">
      <div className="grid gap-2 sm:grid-cols-2">
        <div>
          <label className="text-xs font-medium text-muted-foreground">
            Phase name <span className="text-destructive">*</span>
          </label>
          <input
            className={`${INPUT_CLS}${nameEmpty ? " border-destructive" : ""}`}
            placeholder="Phase name"
            value={phase_name}
            onChange={e => onChange("phase_name", e.target.value)}
            data-testid={rowId ? `phase-name-${rowId}` : "phase-form-name"}
          />
        </div>

        {showSlug && (
          <div>
            <label className="text-xs font-medium text-muted-foreground">
              Base slug{!base_slug.trim() && phase_name.trim() ? " (auto)" : ""}
            </label>
            <input
              className={`${INPUT_CLS}${isDuplicate ? " border-destructive" : ""}`}
              value={base_slug}
              onChange={e => onChange("base_slug", e.target.value)}
              placeholder={phase_name.trim() ? slugify(phase_name.trim()) : "e.g. prelims"}
              data-testid={rowId ? `phase-base-slug-${rowId}` : "phase-form-base-slug"}
            />
            {isDuplicate && (
              <p className="text-xs text-destructive mt-0.5">Duplicate slug "{effSlug}"</p>
            )}
          </div>
        )}

        <div>
          <label className="text-xs font-medium text-muted-foreground">Phase order</label>
          <input
            className={INPUT_CLS}
            type="number"
            value={phase_order}
            onChange={e => onChange("phase_order", e.target.value)}
            data-testid="phase-form-order"
          />
        </div>

        {showMode && (
          <div>
            <label className="text-xs font-medium text-muted-foreground">Mode</label>
            <input
              className={INPUT_CLS}
              value={mode}
              onChange={e => onChange("mode", e.target.value)}
              data-testid="phase-form-mode"
            />
          </div>
        )}

        {showKind && (
          <div>
            <label
              className="text-xs font-medium text-muted-foreground"
              htmlFor={rowId ? `phase-kind-${rowId}` : "phase-form-kind"}
            >
              Phase kind
            </label>
            <select
              id={rowId ? `phase-kind-${rowId}` : "phase-form-kind"}
              className={INPUT_CLS}
              value={phase_kind || ""}
              onChange={e => onChange("phase_kind", e.target.value)}
              data-testid={rowId ? `phase-kind-${rowId}` : "phase-form-kind"}
            >
              <option value="">— unclassified —</option>
              {PHASE_KIND_OPTIONS.map(k => (
                <option key={k.value} value={k.value}>{k.label}</option>
              ))}
            </select>
          </div>
        )}

        {showDates && (
          <>
            <div>
              <DateField
                value={phase_start}
                onChange={v => onChange("phase_start", v)}
                mode="any"
                label="Phase start"
                name="phase_form_start"
                id="phase-form-start"
              />
            </div>
            <div>
              <DateField
                value={phase_end}
                onChange={v => onChange("phase_end", v)}
                mode="any"
                label="Phase end"
                name="phase_form_end"
                id="phase-form-end"
              />
            </div>
          </>
        )}
      </div>

      {showSlug && cbSlug && (
        <p className="text-xs text-muted-foreground mt-1" data-testid={rowId ? `phase-cb-slug-preview-${rowId}` : "phase-form-cb-slug-preview"}>
          Cycle-bound slug: <code className="font-mono">{cbSlug}</code>
        </p>
      )}

      {showTemplate && (
        <label className="flex items-center gap-2 text-xs cursor-pointer mt-2" data-testid={rowId ? `phase-template-toggle-${rowId}` : "phase-form-template-toggle"}>
          <input
            type="checkbox"
            checked={createTemplate}
            onChange={e => onChange("createTemplate", e.target.checked)}
          />
          Also create reusable template{tmplSlug ? ` (slug: ${tmplSlug})` : ""}
        </label>
      )}
    </div>
  );
}
