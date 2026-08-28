/**
 * Essay Spine slot taxonomy.
 *
 * The Spine screen sequences an aspirant's brainstormed content into an essay
 * structure. Slot order is the order the essay reads: introduction -> body ->
 * conclusion.
 *
 * The design mockup (`repoadditions/docs/design/essay-idea-and-spine-builder/
 * Main.dc.html`) models the middle of the essay as one generic "body" bucket.
 * The real schema does not: migration 265 gives `argument_for` and
 * `argument_against` as two distinct block types, and that split is the point —
 * an essay that only argues one side is the failure mode this screen should
 * make visible. So "body" is rendered as separate, separately-labelled slots
 * rather than one merged bucket.
 *
 * Labels here are aspirant-facing. The raw enum values never reach the screen.
 */

export const SPINE_SLOTS = [
  {
    blockType: "hook",
    label: "Hook",
    section: "Introduction",
    helper: "The opening that earns the reader's attention.",
    placeholder: "e.g. Rising fuel queues made subsidy reform a kitchen-table issue, not a budget line.",
    targetWords: 50,
  },
  {
    blockType: "thesis",
    label: "Thesis",
    section: "Introduction",
    helper: "The claim the rest of the essay has to earn.",
    placeholder: "e.g. Cash transfers outperform product subsidies on efficiency — but only where financial access is assured.",
    targetWords: 50,
  },
  {
    blockType: "argument_for",
    label: "Supporting argument",
    section: "Body",
    helper: "A reason the thesis holds. Add one per paragraph you plan to write.",
    placeholder: "e.g. Direct transfer removes the intermediaries where leakage happens.",
    targetWords: 175,
  },
  {
    blockType: "argument_against",
    label: "Counter-consideration",
    section: "Body",
    helper: "Where the thesis is weakest. An essay that never concedes anything reads as a pamphlet.",
    placeholder: "e.g. A fixed cash amount loses real value as prices rise.",
    targetWords: 175,
  },
  {
    blockType: "counter_narrative",
    label: "Counter-narrative",
    section: "Body",
    helper: "The opposing story told on its own terms, before you answer it.",
    placeholder: "e.g. Product subsidy guarantees the good itself; cash guarantees only the money.",
    targetWords: 175,
  },
  {
    blockType: "closing_thought",
    label: "Closing thought",
    section: "Conclusion",
    helper: "What the reader should be left holding.",
    placeholder: "e.g. The verdict is not cash versus product — it is cash plus last-mile banking.",
    targetWords: 100,
  },
];

/** Ordered section names, derived so the slot list stays the single source. */
export const SPINE_SECTIONS = SPINE_SLOTS.reduce(
  (acc, slot) => (acc.includes(slot.section) ? acc : [...acc, slot.section]),
  [],
);

export const SPINE_BLOCK_TYPES = SPINE_SLOTS.map((s) => s.blockType);

/** Rough planned length the six slots add up to, for the progress readout. */
export const SPINE_TARGET_WORDS_LOW = 1000;
export const SPINE_TARGET_WORDS_HIGH = 1200;

/**
 * A Spine block is one the aspirant wrote for the essay structure, not one
 * living on the Idea Canvas. Canvas blocks carry a `lens` (which mind-map
 * branch they hang off); Spine blocks have `lens === null`.
 */
export function isSpineBlock(block) {
  return !!block && (block.lens === null || block.lens === undefined);
}

/** Blocks for one slot, oldest first so the reading order is stable. */
export function blocksForSlot(blocks, blockType) {
  return (blocks || [])
    .filter((b) => isSpineBlock(b) && b.block_type === blockType)
    .sort((a, b) => String(a.created_at || "").localeCompare(String(b.created_at || "")));
}

/**
 * Brainstorm blocks the aspirant has promoted off the canvas (lens cleared)
 * whose type is not one of the six Spine slots — quotes, examples, vocabulary
 * and so on. The Spine shows them as available material; it never creates them.
 */
export function promotedBlocks(blocks) {
  return (blocks || []).filter(
    (b) => isSpineBlock(b) && !SPINE_BLOCK_TYPES.includes(b.block_type),
  );
}

export function wordCount(text) {
  const trimmed = String(text || "").trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

/** Words actually written across every Spine slot. */
export function plannedWordCount(blocks) {
  return (blocks || [])
    .filter((b) => isSpineBlock(b) && SPINE_BLOCK_TYPES.includes(b.block_type))
    .reduce((sum, b) => sum + wordCount(b.block_text), 0);
}

/** Distinct theme ids the aspirant already has any block under. */
export function themeIdsFromBlocks(blocks) {
  const seen = [];
  (blocks || []).forEach((b) => {
    if (b?.theme_id && !seen.includes(b.theme_id)) seen.push(b.theme_id);
  });
  return seen;
}
