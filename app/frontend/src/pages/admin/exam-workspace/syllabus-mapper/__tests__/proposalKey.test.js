/**
 * Cross-side pin test: proposalKey.js must produce identical SHA-256 output
 * to Python's compute_proposal_key() for the same input.
 *
 * The known hash was verified against the Python implementation:
 *   hashlib.sha256("doc-abc|topic-xyz|3|arithmetic|".encode()).hexdigest()
 *   => ca3c545edec5edc98340bfdf484ffad0f1d86f74c14ea9d5d97cd778b6d73313
 */
import { computeProposalKey } from "../proposalKey";

const KNOWN = {
  proposal: {
    syllabus_document_id: "doc-abc",
    topic_id: "topic-xyz",
    source_page: 3,
    normalized_text: "arithmetic",
    exam_phase_id: null,
  },
  expected: "ca3c545edec5edc98340bfdf484ffad0f1d86f74c14ea9d5d97cd778b6d73313",
};

test("cross-side pin: known input → known sha256 hex", () => {
  expect(computeProposalKey(KNOWN.proposal)).toBe(KNOWN.expected);
});

test("deterministic: same input → same output", () => {
  const p = { syllabus_document_id: "d", topic_id: "t", source_page: 1, normalized_text: "foo", exam_phase_id: null };
  expect(computeProposalKey(p)).toBe(computeProposalKey(p));
});

test("different source_page → different key", () => {
  const base = { syllabus_document_id: "d", topic_id: "t", source_page: 1, normalized_text: "foo", exam_phase_id: null };
  expect(computeProposalKey(base)).not.toBe(computeProposalKey({ ...base, source_page: 2 }));
});

test("different topic_id → different key", () => {
  const base = { syllabus_document_id: "d", topic_id: "t1", source_page: 1, normalized_text: "foo", exam_phase_id: null };
  expect(computeProposalKey(base)).not.toBe(computeProposalKey({ ...base, topic_id: "t2" }));
});

test("exam_phase_id null vs set → different key", () => {
  const base = { syllabus_document_id: "d", topic_id: "t", source_page: 1, normalized_text: "foo", exam_phase_id: null };
  expect(computeProposalKey(base)).not.toBe(computeProposalKey({ ...base, exam_phase_id: "ph-1" }));
});
