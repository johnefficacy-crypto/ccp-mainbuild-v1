// Essay Idea Canvas — shared constants mirroring the real backend contract
// (app/backend/app/api/essay_builder.py). block_type / lens values here MUST
// match the Literal enums the API validates against; a mismatch is a 422.

// The six mind-map branches (lens values). Order + labels are what the aspirant
// reads on the canvas; the snake_case key is what the API stores.
export const LENSES = [
  { key: "economic_efficiency", label: "Economic Efficiency", hue: 75 },
  { key: "global_comparative", label: "Global & Comparative", hue: 200 },
  { key: "governance_implementation", label: "Governance & Implementation", hue: 300 },
  { key: "personal_onground", label: "Personal & On-ground", hue: 20 },
  { key: "social_equity_access", label: "Social Equity & Access", hue: 150 },
  { key: "historical_precedent", label: "Historical Precedent", hue: 250 },
];

export const LENS_KEYS = LENSES.map((l) => l.key);
export const LENS_LABEL = Object.fromEntries(LENSES.map((l) => [l.key, l.label]));

// Anchor point (canvas coords) for each branch region — a sensible default spot
// for a block that has no persisted position yet, and the visual home of the
// branch label. Laid out around a central theme node (mirrors the mockup's
// spatial branch concept; exact pixels are not required, clear separation is).
export const LENS_ANCHOR = {
  economic_efficiency: { x: 520, y: 120 },
  global_comparative: { x: 820, y: 300 },
  governance_implementation: { x: 820, y: 560 },
  personal_onground: { x: 520, y: 740 },
  social_equity_access: { x: 200, y: 560 },
  historical_precedent: { x: 200, y: 300 },
};

// The five helper-rail resource types. Each "add" creates a block of this
// block_type in the active lens.
export const RESOURCE_TYPES = [
  { type: "vocab_term", label: "Vocab term" },
  { type: "quote", label: "Quote" },
  { type: "book_reference", label: "Book reference" },
  { type: "example", label: "Example" },
  { type: "stat_to_verify", label: "Stat to verify" },
];

// Per-branch "+ add idea" creates a free-text structural block in that lens.
// argument_for reads naturally as "a point arguing through this lens".
export const BRANCH_IDEA_BLOCK_TYPE = "argument_for";

// Where a helper block first lands (near the active branch, offset so a stack
// of new blocks doesn't perfectly overlap). Callers add jitter.
export const NEW_BLOCK_OFFSET = 24;
