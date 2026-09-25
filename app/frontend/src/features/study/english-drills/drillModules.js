/**
 * English drills — the ONE declared mapping from drill modules to corpus
 * microtopics. Components never name a microtopic id; they read it from here.
 *
 * Source of the ids: the English Language subject
 * (55555555-5555-5555-5555-555555555552) catalogue — 68 rows in
 * workbench/catalogs/topic_catalog_nabard_277.json plus the three added by
 * migration 306 (md5('ccp:topic:' || slug)::uuid). All 71 are accounted for
 * below: 58 mapped to a module, 13 EXCLUDED with the reason. A test asserts the
 * total and that no id is mapped twice.
 *
 * What a learner sees is always narrowed further at runtime to the topics in
 * their current exam's LOCKED coverage (GET /api/study/topics?subject_id=…,
 * `load_scoped_coverage`); the launch endpoint re-checks that server-side.
 *
 * Deliberately absent:
 *   - Parts of speech (tag words / spot the misused word): zero corpus
 *     questions and not an MCQ shape, so no PYQ can ever feed it. Removed.
 *   - Direct → indirect narration has one question; it is a topic inside
 *     Sentence construction, not a module.
 */
export const ENGLISH_SUBJECT_ID = "55555555-5555-5555-5555-555555555552";

export const MODULES = [
  {
    id: "pj",
    name: "Parajumbles",
    tag: "Reordering",
    desc: "Put jumbled sentences into a logical sequence. Drag to reorder when the question has a reviewed order; otherwise choose the option.",
    // Ordering questions whose reviewed order (metadata.correct_order) renders
    // as a drag-to-reorder list — see scripts/backfill_sequence_order.py, which
    // reads the same two ids.
    sequence: true,
    topics: [
      { id: "8d10db27-adf4-21de-1e30-ac69023ab650", label: "Sentence rearrangement" },
      { id: "b2b889f0-5310-23a4-a50c-daa504f0afe7", label: "Logical order" },
    ],
  },
  {
    id: "err",
    name: "Error Detection",
    tag: "Spotting errors",
    desc: "Find the part of the sentence that carries the error, or pick the sentence that is correct.",
    topics: [
      { id: "10b21db7-8b86-4fa9-a1f6-8cd7d21085da", label: "Segment-marked errors" },
      { id: "9cc0f630-ab4f-4a0a-b5b2-9212f18af346", label: "Correct sentence" },
    ],
  },
  {
    id: "imp",
    name: "Sentence Improvement",
    tag: "Replacement",
    desc: "Replace the underlined phrase with the correct option — or recognise when no improvement is needed.",
    topics: [
      { id: "57e9ec9c-c979-437a-b1e8-90580921f096", label: "Phrase replacement" },
      { id: "d5881d53-754a-4f95-a6a2-38d2bbd55162", label: "No improvement" },
    ],
  },
  {
    id: "cloze",
    name: "Cloze & Fill-ins",
    tag: "Fill in the blanks",
    desc: "Passage cloze, connectors, and one- or two-blank sentence completion.",
    topics: [
      { id: "c91ecdcc-7fc9-4d23-b3b7-9122ce81cf9a", label: "Passage cloze" },
      { id: "4b44f9f1-8d13-4977-be4b-aa5108b10ead", label: "Single-blank cloze" },
      { id: "de6aaf4c-db6e-4c5c-b2bd-fc3d1880cc21", label: "Connector cloze" },
      { id: "fd797be4-4857-4885-a456-52d9ce38df94", label: "Connector completion" },
      { id: "53bf9a36-47c0-4473-b677-29a66d1a7bdb", label: "Double blank" },
      { id: "d9727773-6fbe-6454-fc17-fcca3d466594", label: "Missing part" },
      { id: "cbb196b4-3325-4af1-80f9-a4280d592e9f", label: "Contextual word" },
      { id: "0b53297b-0109-4334-b1ee-e56a18137969", label: "Word pair" },
      { id: "613e6076-97c1-4a2b-b932-8831642cf075", label: "Prepositions & phrasals" },
    ],
  },
  {
    id: "rc",
    name: "Reading Comprehension",
    tag: "Passages",
    desc: "Passage questions on detail, inference, main idea, tone, argument and vocabulary in context.",
    topics: [
      { id: "342ec4bb-5625-4398-9b44-2963d65062a4", label: "Explicit detail" },
      { id: "420312ba-2e38-4e16-a836-7e6764a05535", label: "Inference" },
      { id: "baf763bb-6d36-4a25-b1ba-6419e3b26852", label: "Main idea" },
      { id: "ebdd3a2a-f038-4775-9684-647b6cbbdcbb", label: "Tone & purpose" },
      { id: "abf57bec-5615-4320-a666-ff980779a0c2", label: "Argument" },
      { id: "dbed7599-7bab-45e3-ab53-cb8cbb8a1c55", label: "Vocabulary in context" },
      { id: "bf06f202-6d47-497c-a4e2-5f7f377d0fbb", label: "Passage synonyms & antonyms" },
      { id: "70b4fc2f-cf07-d8ef-fb7e-3025342ba94d", label: "Comprehension (general)" },
    ],
  },
  {
    id: "voc",
    name: "Vocabulary",
    tag: "Words & phrases",
    desc: "Synonyms, antonyms, idioms, one-word substitution, spelling, phrasal verbs and collocations.",
    topics: [
      { id: "bb17b54f-b233-4c9d-9bad-4526b5ce2f87", label: "Synonyms" },
      { id: "b56cb48c-f85b-4158-8e71-f954f48a8c10", label: "Antonyms" },
      { id: "f4ab61e2-cadf-4686-a1c5-50554463f230", label: "Idioms" },
      { id: "e6f14cb6-df7f-4e3a-9aa4-5efbf45b7946", label: "One-word" },
      { id: "22591465-673a-c375-3460-2702125f6fc3", label: "Spelling" },
      { id: "37a65bc7-1c55-43e7-b59a-c25f3bc3232f", label: "Phrasal verbs" },
      { id: "1ea65bf4-15e7-e99a-3687-b3e324f4b5b9", label: "Collocations" },
      { id: "640b124b-d77a-5052-7d60-c5263b23bbd8", label: "Formal vocabulary" },
      { id: "d24db813-295b-cb39-e6b3-327409910c6f", label: "Word choice" },
    ],
  },
  {
    id: "ce",
    name: "Common Errors",
    tag: "Grammar & usage",
    desc: "Agreement, tense, pronouns, articles and prepositions, modifiers, parallelism, redundancy and confused words.",
    topics: [
      { id: "7c71b869-e50a-4ebd-aea1-fe291dbee5ed", label: "Subject–verb agreement" },
      { id: "b9facc82-38d7-f725-7c97-8b5894c157f0", label: "Subject–verb agreement (legacy)" },
      { id: "f146f9b5-b13d-47c0-8aca-c80a6566b4fe", label: "Tense & sequence" },
      { id: "aa680736-24d9-abb2-d7f2-ad3bcb2acb77", label: "Tense (legacy)" },
      { id: "ee103c0c-a9fa-4ae8-98dd-78cdc4378732", label: "Pronoun reference" },
      { id: "c6beb287-3fef-397f-e204-57f8e4053328", label: "Pronoun reference (legacy)" },
      { id: "f9c12eec-a497-4d10-b219-2da6b28a92f7", label: "Prepositions & articles" },
      { id: "5db857e5-5b9d-2f80-0046-1978c199ed85", label: "Prepositions" },
      { id: "b790ab2c-17e8-9025-f313-2c44d24dac8d", label: "Articles" },
      { id: "e5efcb86-127f-460d-83fb-9faa38ee400c", label: "Parallelism" },
      { id: "3ab068c5-397c-4189-913f-0d26569b3899", label: "Word order & modifiers" },
      { id: "aca53761-13fc-65c9-bd3c-9f324e9a589f", label: "Modifiers (legacy)" },
      { id: "e6e0700f-0130-49e0-961d-89cbe5eab3f8", label: "Redundancy & wordiness" },
      { id: "84fae1ba-f1d4-98da-1c09-45c51ceb2e22", label: "Redundancy (legacy)" },
      { id: "0df7dc1f-8059-4012-a9a4-59b8bc8b7181", label: "Confused word pairs" },
      { id: "5bc8efce-f987-86cc-afc9-1d5fc5d03881", label: "Word usage" },
      { id: "c18d927f-2eab-49db-b302-a017cf1f2193", label: "Word interchange" },
      { id: "c777f14a-2058-a3ec-1208-bb4b36e2a19a", label: "Punctuation" },
      { id: "eeed4b11-c9a3-4c0d-9f08-e31d6d8bcdac", label: "Formal register" },
    ],
  },
  {
    id: "sc",
    name: "Sentence Construction",
    tag: "Transform",
    desc: "Active ↔ passive voice, direct ↔ indirect narration, and sentence transformation.",
    topics: [
      { id: "925bca25-49af-bb3b-0e2b-707ca2e0b9fa", label: "Active → passive" },
      // One question in the corpus: folded in here, never a module of its own.
      { id: "a628b8f9-5d2f-8502-5517-cc2b1cf0916a", label: "Direct → indirect" },
      { id: "386a7e56-8043-74cf-4bfb-43aa9a845c9c", label: "Transformation" },
      { id: "4d511b04-901c-8fb4-06a9-a1efe500e4f6", label: "Simple sentences" },
      { id: "5f033e03-98a8-9e1e-f503-3d837e169983", label: "Compound sentences" },
      { id: "5194a509-d374-28d7-24f8-7a49f7a308b8", label: "Complex sentences" },
      { id: "1ecdc0ab-2bc0-7ea9-2d55-064bd36f0cdc", label: "Sentence structure" },
    ],
  },
];

/**
 * English microtopics that feed NO drill, and why. Writing-assessment leaves are
 * judged in a candidate's own prose (English writing practice serves them);
 * the communication leaves are business-communication theory, not verbal
 * ability.
 */
export const EXCLUDED_TOPICS = [
  { id: "f911f68b-418c-d7bb-37e3-00499792e022", label: "Cohesion", reason: "writing assessment" },
  { id: "b2d49393-0e86-3521-fc2d-c5ec26e286e9", label: "Conclusion", reason: "writing assessment" },
  { id: "0e4fdd22-0bfe-ee0a-c0bc-d74b9518afeb", label: "Content Relevance", reason: "writing assessment" },
  { id: "63d9ed95-155f-b31b-acd8-3bb63b0bbb76", label: "Essay Writing", reason: "writing assessment" },
  { id: "8a436650-6e75-79db-904f-e60bd0f7abaf", label: "Format Rules", reason: "writing assessment" },
  { id: "eb5019d6-aa0e-23f3-dabd-d507596cf97a", label: "Letter and Report Writing", reason: "writing assessment" },
  { id: "47d00077-5f85-ba3b-fc49-cf7405914aa2", label: "Précis Writing", reason: "writing assessment" },
  { id: "42954cdb-5339-b7b2-9424-c0569960244b", label: "Topic Sentence", reason: "writing assessment" },
  { id: "50e8c0d4-60b5-7d43-4c12-33a386b0bbe5", label: "Word Limit", reason: "writing assessment" },
  { id: "3f2a57b9-ea87-4d0e-9296-6651b115c149", label: "Written answers to a passage", reason: "descriptive, not MCQ" },
  { id: "fa2ead71-59b9-4417-b71f-1f623d2c02c9", label: "Barriers to communication", reason: "business communication" },
  { id: "3a0004f6-d89a-4f5f-b858-0dca53d6f277", label: "Communication register by relationship", reason: "business communication" },
  { id: "2416c0e0-a68f-45a9-9d66-9b8910ac3e9e", label: "Tools of communication", reason: "business communication" },
];

export const MODULE_BY_ID = Object.fromEntries(MODULES.map((m) => [m.id, m]));
