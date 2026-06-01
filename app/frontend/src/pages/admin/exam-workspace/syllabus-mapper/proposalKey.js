/**
 * Deterministic proposal key — must match Python compute_proposal_key() exactly.
 *
 * sha256(syllabus_document_id|topic_id|source_page|normalized_text|exam_phase_id)
 *
 * Cross-side pin test: see __tests__/proposalKey.test.js
 */
import { sha256 } from "js-sha256";

export function computeProposalKey(proposal) {
  const parts = [
    proposal.syllabus_document_id ?? "",
    proposal.topic_id ?? "",
    String(proposal.source_page ?? 0),
    proposal.normalized_text ?? "",
    proposal.exam_phase_id ?? "",
  ].join("|");
  return sha256(parts);
}
