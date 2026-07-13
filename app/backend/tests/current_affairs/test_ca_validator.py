"""Stage-D deterministic validator tests (GQR-G3)."""
from __future__ import annotations

from app.current_affairs.generation.validator import validate_candidate


def _payload(**over):
    base = {
        "stem": "Which body issued the June 2026 circular on digital lending?",
        "options": [
            {"id": "a", "text": "Reserve Bank of India"},
            {"id": "b", "text": "SEBI"},
            {"id": "c", "text": "IRDAI"},
            {"id": "d", "text": "PFRDA"},
        ],
        "correct_option_id": "a",
        "explanation": "The circular was issued by the RBI per the cited claim.",
        "difficulty": "medium",
        "linked_claim_ids": ["c0"],
        "question_fingerprint": "fp-1",
    }
    base.update(over)
    return base


_CTX = dict(
    claims_by_id={"c0": {"id": "c0", "factual_status": "current"}},
    evidence_by_claim={"c0": [{"document_id": "doc-1", "evidence_text": "RBI issued..."}]},
    source_authority_by_document={"doc-1": "primary_official"},
    event={"event_date": "2026-06-01", "relevance_from": "2026-06-01", "relevance_until": "2026-09-01"},
)


def test_valid_candidate_passes():
    r = validate_candidate(_payload(), **_CTX)
    assert r.ok, r.failures


def test_wrong_option_count_fails():
    p = _payload(options=[{"id": "a", "text": "x"}, {"id": "b", "text": "y"}])
    r = validate_candidate(p, **_CTX)
    assert not r.ok and "must_have_exactly_four_options" in r.failures


def test_duplicate_options_fail():
    p = _payload(options=[
        {"id": "a", "text": "RBI"}, {"id": "b", "text": "rbi"},
        {"id": "c", "text": "SEBI"}, {"id": "d", "text": "IRDAI"},
    ])
    r = validate_candidate(p, **_CTX)
    assert not r.ok and "duplicate_options" in r.failures


def test_meta_option_fails():
    p = _payload(options=[
        {"id": "a", "text": "RBI"}, {"id": "b", "text": "SEBI"},
        {"id": "c", "text": "IRDAI"}, {"id": "d", "text": "All of the above"},
    ])
    r = validate_candidate(p, **_CTX)
    assert "meta_option_not_allowed" in r.failures


def test_correct_option_not_present_fails():
    r = validate_candidate(_payload(correct_option_id="z"), **_CTX)
    assert "correct_option_id_invalid" in r.failures


def test_empty_explanation_fails():
    r = validate_candidate(_payload(explanation="  "), **_CTX)
    assert "empty_explanation" in r.failures


def test_unqualified_time_reference_fails():
    r = validate_candidate(_payload(stem="Who is the RBI governor currently?"), **_CTX)
    assert "unqualified_time_reference" in r.failures


def test_answer_leaked_in_stem_fails():
    # The stem names the correct option verbatim → the answer is given away.
    p = _payload(stem="The Reserve Bank of India issued which June 2026 circular authority?")
    r = validate_candidate(p, **_CTX)
    assert "answer_leaked_in_stem" in r.failures


def test_no_linked_claim_fails():
    r = validate_candidate(_payload(linked_claim_ids=[]), **_CTX)
    assert "no_linked_claim" in r.failures


def test_superseded_claim_fails():
    ctx = {**_CTX, "claims_by_id": {"c0": {"id": "c0", "factual_status": "superseded"}}}
    r = validate_candidate(_payload(), **ctx)
    assert "superseded_or_noncurrent_claim" in r.failures


def test_sole_discovery_only_evidence_fails():
    ctx = {**_CTX, "source_authority_by_document": {"doc-1": "discovery_only"}}
    r = validate_candidate(_payload(), **ctx)
    assert "sole_evidence_discovery_only" in r.failures


def test_mixed_authority_with_official_passes_adr0007():
    ctx = {
        **_CTX,
        "evidence_by_claim": {"c0": [
            {"document_id": "doc-1"}, {"document_id": "doc-2"},
        ]},
        "source_authority_by_document": {"doc-1": "discovery_only", "doc-2": "primary_official"},
    }
    r = validate_candidate(_payload(), **ctx)
    assert r.ok, r.failures


def test_duplicate_fingerprint_fails():
    r = validate_candidate(_payload(), **_CTX, existing_fingerprints=frozenset({"fp-1"}))
    assert "duplicate_question_fingerprint" in r.failures


def test_inverted_relevance_window_fails():
    ctx = {**_CTX, "event": {"event_date": "2026-06-01", "relevance_from": "2026-09-01", "relevance_until": "2026-06-01"}}
    r = validate_candidate(_payload(), **ctx)
    assert "relevance_window_inverted" in r.failures
