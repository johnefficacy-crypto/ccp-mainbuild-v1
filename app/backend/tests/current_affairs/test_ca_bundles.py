"""Bundle selection + eligibility + provenance tests (GQR-G5a)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.current_affairs import bundles
from tests.persona_questions._stub import SBStub

_NOW = datetime(2026, 7, 13, tzinfo=timezone.utc)
_FUTURE = (_NOW + timedelta(days=10)).isoformat()
_PAST = (_NOW - timedelta(days=1)).isoformat()


def _bank(qid, *, status="verified", is_current=True, kind="current_event",
          valid_until=_FUTURE, valid_from=None, anchor="2026-07-10"):
    return {"id": qid, "reviewer_status": status, "source_kind": kind,
            "is_current_based": is_current, "valid_until": valid_until,
            "valid_from": valid_from, "event_anchor_date": anchor}


def test_selects_only_in_window_reviewed_current_event():
    db = {"mock_question_bank": [
        _bank("q1"),                                   # eligible
        _bank("q2", valid_until=_PAST),                # expired → excluded
        _bank("q3", status="draft"),                   # unreviewed → excluded
        _bank("q4", is_current=False),                 # not current-based (filtered by eq)
        _bank("q5", valid_from=_FUTURE),               # not yet relevant → excluded
    ]}
    ids = bundles.select_promoted_current_event_ids(SBStub(db), now=_NOW)
    assert ids == ["q1"]


def test_selection_orders_newest_anchor_first():
    db = {"mock_question_bank": [
        _bank("old", anchor="2026-07-01"), _bank("new", anchor="2026-07-12"),
    ]}
    assert bundles.select_promoted_current_event_ids(SBStub(db), now=_NOW) == ["new", "old"]


def _bundle(bid, **over):
    row = {"id": bid, "cadence": "weekly", "status": "published", "reviewer_status": "verified",
           "exam_id": None, "exam_family_id": None,
           "period_start": "2026-07-06", "available_until": _FUTURE, "publish_at": _PAST}
    row.update(over)
    return row


def _exam(exam_id, family_id):
    return {"id": exam_id, "exam_family_id": family_id}


def test_resolve_prefers_exact_exam_over_family_over_global():
    # All three scope tiers are servable; exact-exam must win.
    db = {
        "exams": [_exam("e-1", "fam-1")],
        "current_affairs_bundles": [
            _bundle("global"),
            _bundle("family", exam_family_id="fam-1"),
            _bundle("exact", exam_id="e-1"),
        ],
    }
    assert bundles.resolve_eligible_bundle(SBStub(db), exam_id="e-1", now=_NOW)["id"] == "exact"


def test_resolve_falls_back_to_family_then_global():
    db_fam = {
        "exams": [_exam("e-1", "fam-1")],
        "current_affairs_bundles": [_bundle("global"), _bundle("family", exam_family_id="fam-1")],
    }
    assert bundles.resolve_eligible_bundle(SBStub(db_fam), exam_id="e-1", now=_NOW)["id"] == "family"
    db_glob = {
        "exams": [_exam("e-1", "fam-1")],
        "current_affairs_bundles": [_bundle("global"), _bundle("family", exam_family_id="fam-OTHER")],
    }
    assert bundles.resolve_eligible_bundle(SBStub(db_glob), exam_id="e-1", now=_NOW)["id"] == "global"


def test_resolve_requires_verified_and_open_window():
    db = {"exams": [_exam("e-1", "fam-1")], "current_affairs_bundles": [
        _bundle("unverified", reviewer_status="in_review"),   # not verified → excluded
        _bundle("expired", available_until=_PAST),            # window closed → excluded
        _bundle("unpublished_yet", publish_at=_FUTURE),       # publish_at future → excluded
    ]}
    assert bundles.resolve_eligible_bundle(SBStub(db), exam_id="e-1", now=_NOW) is None


def test_resolve_skips_bundle_for_other_exam():
    db = {"exams": [_exam("e-1", "fam-1")],
          "current_affairs_bundles": [_bundle("other_exam", exam_id="other")]}
    assert bundles.resolve_eligible_bundle(SBStub(db), exam_id="e-1", now=_NOW) is None


def test_bundle_question_ids_ordered():
    db = {"current_affairs_bundle_questions": [
        {"bundle_id": "b1", "mock_question_id": "q2", "display_order": 1},
        {"bundle_id": "b1", "mock_question_id": "q1", "display_order": 0},
    ]}
    assert bundles.bundle_question_ids(SBStub(db), "b1") == ["q1", "q2"]


def _prov(qid):
    """Complete, integrity-passing promoted provenance chain for a bank question id."""
    return {
        "current_affairs_events": [{"id": f"ev-{qid}", "event_date": "2026-07-09",
                                    "status": "active", "relevance_until": None}],
        "current_affairs_question_links": [
            {"mock_question_id": qid, "claim_id": f"c-{qid}", "event_id": f"ev-{qid}"}],
        "current_affairs_claims": [{"id": f"c-{qid}", "event_id": f"ev-{qid}",
                                    "reviewer_status": "verified", "factual_status": "current",
                                    "superseded_at": None}],
        "current_affairs_claim_evidence": [
            {"claim_id": f"c-{qid}", "document_id": f"d-{qid}", "evidence_role": "primary"}],
        "current_affairs_documents": [{"id": f"d-{qid}", "source_id": f"s-{qid}",
                                       "published_at": "2026-07-08T00:00:00Z",
                                       "final_url": f"https://pib.gov.in/{qid}"}],
        "current_affairs_sources": [{"id": f"s-{qid}", "is_active": True,
                                     "authority_level": "primary_official"}],
    }


def _bank_prov(qid, **over):
    b = _bank(qid, **over)
    b["current_affairs_item_id"] = f"ev-{qid}"
    return b


def test_eligible_membership_requires_window_review_and_complete_provenance():
    # Raw membership has 4: one eligible, one expired, one unreviewed, one lacking a
    # promoted-provenance chain — only the fully eligible + provenance-complete one counts.
    db = {
        "current_affairs_bundle_questions": [
            {"bundle_id": "b1", "mock_question_id": q, "display_order": i}
            for i, q in enumerate(["q1", "q2", "q3", "q4"])
        ],
        "mock_question_bank": [
            _bank_prov("q1"), _bank_prov("q2", valid_until=_PAST),
            _bank_prov("q3", status="draft"), _bank_prov("q4"),  # q4 in-window but no provenance
        ],
    }
    # Complete provenance chains for q1/q2/q3 only (q4 intentionally has none).
    for qid in ("q1", "q2", "q3"):
        for tbl, rows in _prov(qid).items():
            db.setdefault(tbl, []).extend(rows)
    assert bundles.eligible_bundle_question_ids(SBStub(db), "b1", now=_NOW) == ["q1"]


def test_eligibility_rejects_provenance_integrity_failures():
    # Existence is not enough: a superseded claim, a demoted event, a mismatched link
    # event, and a discovery-only source each disqualify the member (integrity, not just
    # a row's presence).
    base = {
        "current_affairs_bundle_questions": [
            {"bundle_id": "b1", "mock_question_id": q, "display_order": i}
            for i, q in enumerate(["qc", "qe", "ql", "qs"])
        ],
        "mock_question_bank": [_bank_prov(q) for q in ("qc", "qe", "ql", "qs")],
    }
    for q in ("qc", "qe", "ql", "qs"):
        for tbl, rows in _prov(q).items():
            base.setdefault(tbl, []).extend(rows)
    # qc: claim no longer current
    next(c for c in base["current_affairs_claims"] if c["id"] == "c-qc")["factual_status"] = "superseded"
    # qe: event demoted
    next(e for e in base["current_affairs_events"] if e["id"] == "ev-qe")["status"] = "demoted"
    # ql: link points at a different event than the bank
    next(l for l in base["current_affairs_question_links"] if l["mock_question_id"] == "ql")["event_id"] = "ev-OTHER"
    # qs: source is discovery-only
    next(s for s in base["current_affairs_sources"] if s["id"] == "s-qs")["authority_level"] = "discovery_only"
    assert bundles.eligible_bundle_question_ids(SBStub(base), "b1", now=_NOW) == []


def test_load_question_provenance_builds_auditable_envelope_and_flags_supersession():
    db = {
        "mock_question_bank": [{"id": "q1", "current_affairs_item_id": "ev-1"}],
        "current_affairs_events": [{"id": "ev-1", "event_date": "2026-07-09"}],
        "current_affairs_question_links": [{"mock_question_id": "q1", "claim_id": "c-1"}],
        "current_affairs_claims": [
            {"id": "c-1", "factual_status": "superseded", "superseded_at": _PAST}],
        "current_affairs_claim_evidence": [
            {"claim_id": "c-1", "document_id": "d-1", "evidence_role": "primary",
             "start_offset": 0, "end_offset": 38}],
        "current_affairs_documents": [
            {"id": "d-1", "published_at": "2026-07-08T00:00:00Z", "content_hash": "sha-1",
             "final_url": "https://pib.gov.in/x", "source_url": "https://pib.gov.in/x-raw"}],
    }
    env = bundles.load_question_provenance(SBStub(db), ["q1"], now=_NOW)["q1"]
    assert env["event_id"] == "ev-1" and env["event_date"] == "2026-07-09"
    assert env["claim_ids"] == ["c-1"]
    assert env["source_published_at"] == "2026-07-08T00:00:00Z"
    assert env["source_url"] == "https://pib.gov.in/x"
    ev = env["evidence"][0]
    assert ev["document_id"] == "d-1" and ev["content_hash"] == "sha-1"
    assert ev["start_offset"] == 0 and ev["end_offset"] == 38
    assert env["superseded"] is True and env["supersession_note"]


def test_load_question_provenance_no_supersession_for_current_claim():
    db = {
        "mock_question_bank": [{"id": "q1", "current_affairs_item_id": "ev-1"}],
        "current_affairs_events": [{"id": "ev-1", "event_date": "2026-07-09"}],
        "current_affairs_question_links": [{"mock_question_id": "q1", "claim_id": "c-1"}],
        "current_affairs_claims": [{"id": "c-1", "factual_status": "current", "superseded_at": None}],
        "current_affairs_claim_evidence": [
            {"claim_id": "c-1", "document_id": "d-1", "evidence_role": "primary"}],
        "current_affairs_documents": [{"id": "d-1", "published_at": "2026-07-08T00:00:00Z",
                                       "final_url": "https://rbi.org.in/y", "source_url": None}],
    }
    env = bundles.load_question_provenance(SBStub(db), ["q1"], now=_NOW)["q1"]
    assert env["superseded"] is False and env.get("supersession_note") is None
    assert env["source_url"] == "https://rbi.org.in/y"


def test_load_question_provenance_fails_closed_on_incomplete():
    # A question that resolves to no event / no grounding claim must raise (fail closed),
    # never yield an empty envelope (F3).
    db = {"mock_question_bank": [{"id": "q1", "current_affairs_item_id": None}]}
    import pytest
    with pytest.raises(RuntimeError):
        bundles.load_question_provenance(SBStub(db), ["q1"], now=_NOW)
