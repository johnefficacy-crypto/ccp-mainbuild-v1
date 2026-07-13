"""Current-affairs bundles (GQR-G5a) — server-owned selection + eligibility.

A bundle is the exam/calendar unit a weekly current-affairs attempt is frozen from.
Selection draws ONLY promoted current-event questions (``source_kind='current_event'``,
``is_current_based=true``, reviewed, inside their relevance window) — the GQR-G0 +
``_exam_base_pool`` fixes keep those same questions out of permanent mocks.

Scope precedence (mirrors the writing_practice applicability band exam > family > global):
a learner's eligible bundle is resolved exact-exam first, then exam-family, then global
(both scope columns null). Only ``status='published'`` AND ``reviewer_status='verified'``
bundles inside their publish/availability window are servable.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("career_copilot.current_affairs.bundles")

# Bank reviewer_status values that are learner-visible (RLS read gate parity).
_SELECTABLE = ("verified", "published", "live")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _within_window(row: dict[str, Any], now: datetime) -> bool:
    """Relevance window: valid_from <= now (if set) AND valid_until > now (if set)."""
    vf, vu = row.get("valid_from"), row.get("valid_until")
    today = now.date().isoformat()
    now_iso = now.isoformat()
    if vf and str(vf) > today and str(vf) > now_iso:
        return False
    if vu and str(vu) <= now_iso and str(vu) <= today:
        return False
    return True


def _resolve_exam_family(supabase: Any, exam_id: str | None) -> str | None:
    """The learner's exam family (``exams.exam_family_id``) — the canonical family link."""
    if not exam_id:
        return None
    try:
        rows = (
            supabase.table("exams").select("exam_family_id")
            .eq("id", exam_id).limit(1).execute().data
        ) or []
    except Exception:  # pragma: no cover - defensive
        return None
    return str(rows[0]["exam_family_id"]) if rows and rows[0].get("exam_family_id") else None


def select_promoted_current_event_ids(
    supabase: Any, *, limit: int = 100, now: datetime | None = None
) -> list[str]:
    """Eligible promoted current-event question ids, newest-relevant first.

    Filters are applied defensively in Python (window) after the categorical eq
    filters so the result never leaks an expired or unreviewed current-event item.
    """
    now = now or _now()
    rows = (
        supabase.table("mock_question_bank")
        .select("id,reviewer_status,source_kind,is_current_based,valid_from,valid_until,event_anchor_date")
        .eq("source_kind", "current_event")
        .eq("is_current_based", True)
        .limit(max(1, limit) * 4)
        .execute()
        .data
    ) or []
    eligible = [
        r for r in rows
        if r.get("reviewer_status") in _SELECTABLE and _within_window(r, now)
    ]
    eligible.sort(key=lambda r: str(r.get("event_anchor_date") or ""), reverse=True)
    return [str(r["id"]) for r in eligible[:limit]]


def bundle_question_ids(supabase: Any, bundle_id: str) -> list[str]:
    """Ordered mock_question_ids of a bundle's raw membership (display_order)."""
    rows = (
        supabase.table("current_affairs_bundle_questions")
        .select("mock_question_id,display_order")
        .eq("bundle_id", bundle_id)
        .order("display_order")
        .execute()
        .data
    ) or []
    return [str(r["mock_question_id"]) for r in rows if r.get("mock_question_id")]


def _rows(supabase: Any, table: str, cols: str, col: str, vals: list) -> list[dict[str, Any]]:
    """Authority read — NEVER swallows failures (fail closed on any DB fault)."""
    vals = [v for v in vals if v]
    if not vals:
        return []
    return (
        supabase.table(table).select(cols).in_(col, list(dict.fromkeys(vals)))
        .execute().data
    ) or []


def _provenance_complete_ids(supabase: Any, qids: list[str], *, now: datetime) -> set[str]:
    """Ids whose promoted provenance passes full INTEGRITY (not mere existence): the
    grounding link/claim events agree with the bank event, the claim is verified+current,
    the event is active + still relevant, and the evidence resolves to an active,
    non-``discovery_only`` source (ADR-0007). Mirrors ``ca_eligible_bundle_question_ids``.
    """
    if not qids:
        return set()
    today = now.date().isoformat()
    bank = _rows(supabase, "mock_question_bank", "id,current_affairs_item_id", "id", qids)
    event_of = {str(b["id"]): str(b["current_affairs_item_id"])
                for b in bank if b.get("current_affairs_item_id")}
    if not event_of:
        return set()
    events = _rows(supabase, "current_affairs_events", "id,status,relevance_until", "id",
                   list(event_of.values()))
    event_ok = {
        str(e["id"]) for e in events
        if e.get("status") == "active"
        and (not e.get("relevance_until") or str(e["relevance_until"]) >= today)
    }
    # links: only claims whose link event agrees with the bank event.
    links = _rows(supabase, "current_affairs_question_links", "mock_question_id,claim_id,event_id",
                  "mock_question_id", list(event_of))
    claims_by_q: dict[str, set[str]] = {}
    for lk in links:
        q, cid = str(lk.get("mock_question_id")), lk.get("claim_id")
        if cid and str(lk.get("event_id")) == event_of.get(q):
            claims_by_q.setdefault(q, set()).add(str(cid))
    all_claims = [c for cs in claims_by_q.values() for c in cs]
    if not all_claims:
        return set()
    claims = _rows(supabase, "current_affairs_claims", "id,event_id,reviewer_status,factual_status",
                   "id", all_claims)
    claim_event = {
        str(c["id"]): str(c.get("event_id")) for c in claims
        if c.get("reviewer_status") == "verified" and c.get("factual_status") == "current"
    }
    evidence = _rows(supabase, "current_affairs_claim_evidence", "claim_id,document_id",
                     "claim_id", list(claim_event))
    docs = _rows(supabase, "current_affairs_documents", "id,source_id", "id",
                 [str(e["document_id"]) for e in evidence if e.get("document_id")])
    src_of_doc = {str(d["id"]): str(d.get("source_id")) for d in docs}
    sources = _rows(supabase, "current_affairs_sources", "id,is_active,authority_level", "id",
                    list(set(src_of_doc.values())))
    src_ok = {str(s["id"]) for s in sources
              if s.get("is_active") and s.get("authority_level") in ("primary_official", "official_secondary")}
    grounded = {
        str(e["claim_id"]) for e in evidence
        if str(e.get("claim_id")) in claim_event
        and src_of_doc.get(str(e.get("document_id"))) in src_ok
        and claim_event[str(e["claim_id"])] in event_ok
    }
    return {q for q, cs in claims_by_q.items()
            if event_of.get(q) in event_ok and (cs & grounded)}


def eligible_bundle_question_ids(
    supabase: Any, bundle_id: str, *, now: datetime | None = None
) -> list[str]:
    """Ordered membership restricted to STILL-eligible promoted current-event questions.

    Mirrors the ``ca_eligible_bundle_question_ids`` SQL helper the start RPC re-derives
    under lock: a member counts only if it is a reviewed promoted current_event inside its
    validity window AND carries complete promoted provenance (event + grounding claim +
    evidence + source document). The start path compares this against the raw membership
    and fails closed on any difference (bundle degraded), so a stale/incomplete member is
    never silently dropped into a shortened attempt.
    """
    now = now or _now()
    ordered = bundle_question_ids(supabase, bundle_id)
    if not ordered:
        return []
    bank = (
        supabase.table("mock_question_bank")
        .select("id,reviewer_status,source_kind,is_current_based,valid_from,valid_until,current_affairs_item_id")
        .in_("id", ordered)
        .execute()
        .data
    ) or []
    base_ok = {
        str(r["id"]) for r in bank
        if r.get("source_kind") == "current_event"
        and r.get("is_current_based")
        and r.get("reviewer_status") in _SELECTABLE
        and _within_window(r, now)
        and r.get("current_affairs_item_id")
    }
    complete = _provenance_complete_ids(supabase, list(base_ok), now=now)
    ok = base_ok & complete
    return [qid for qid in ordered if qid in ok]


def load_question_provenance(
    supabase: Any, question_ids: list[str], *, now: datetime | None = None
) -> dict[str, dict[str, Any]]:
    """Per-question provenance envelope frozen at attempt start (revealed post-submit).

    Carries the §10 learner-facing fields (event date, source publication date, source
    link, supersession warning) PLUS auditable identifiers (event id, claim ids, evidence
    document ids + content hash + spans) so the frozen attempt is provenance-traceable.
    Fails CLOSED: every authority read propagates its error, and a question that resolves
    to no event or no grounding claim raises (a promoted current-event question must have
    both — eligibility already requires it, so this guards a mid-freeze race).
    """
    qids = [str(q) for q in question_ids]
    if not qids:
        return {}

    bank = _rows(supabase, "mock_question_bank", "id,current_affairs_item_id", "id", qids)
    event_by_q = {str(b["id"]): b.get("current_affairs_item_id") for b in bank}
    events = _rows(supabase, "current_affairs_events", "id,event_date", "id",
                   list(event_by_q.values()))
    event_date = {str(e["id"]): e.get("event_date") for e in events}

    links = _rows(supabase, "current_affairs_question_links", "mock_question_id,claim_id",
                  "mock_question_id", qids)
    claims_by_q: dict[str, list[str]] = {}
    for lk in links:
        if lk.get("claim_id"):
            claims_by_q.setdefault(str(lk.get("mock_question_id")), []).append(str(lk.get("claim_id")))
    all_claims = [c for cs in claims_by_q.values() for c in cs]

    claims = _rows(supabase, "current_affairs_claims", "id,factual_status,superseded_at", "id", all_claims)
    claim_state = {str(c["id"]): c for c in claims}

    evidence = _rows(supabase, "current_affairs_claim_evidence",
                     "claim_id,document_id,evidence_role,start_offset,end_offset", "claim_id", all_claims)
    ev_by_claim: dict[str, dict[str, Any]] = {}
    for ev in evidence:
        cid = str(ev.get("claim_id"))
        if cid not in ev_by_claim or ev.get("evidence_role") == "primary":
            ev_by_claim[cid] = ev
    docs = _rows(supabase, "current_affairs_documents", "id,published_at,final_url,source_url,content_hash",
                 "id", [str(e.get("document_id")) for e in evidence if e.get("document_id")])
    doc_by_id = {str(d["id"]): d for d in docs}

    out: dict[str, dict[str, Any]] = {}
    for qid in qids:
        eid = event_by_q.get(qid)
        claim_ids = claims_by_q.get(qid, [])
        if not eid or not claim_ids:
            raise RuntimeError(f"current-affairs provenance incomplete for {qid}")
        superseded = any(
            (claim_state.get(cid, {}).get("factual_status") not in (None, "current"))
            or claim_state.get(cid, {}).get("superseded_at")
            for cid in claim_ids
        )
        pub_at = url = None
        audit_evidence: list[dict[str, Any]] = []
        for cid in claim_ids:
            ev = ev_by_claim.get(cid)
            doc = doc_by_id.get(str(ev.get("document_id"))) if ev else None
            if not ev or not doc:
                # Fail closed: a linked claim with no resolvable evidence/document must not
                # be frozen with a partial envelope (F3).
                raise RuntimeError(f"current-affairs provenance incomplete for {qid}: claim {cid}")
            pub_at = pub_at or doc.get("published_at")
            url = url or doc.get("final_url") or doc.get("source_url")
            audit_evidence.append({
                "claim_id": cid, "document_id": str(ev.get("document_id")),
                "content_hash": doc.get("content_hash"),
                "start_offset": ev.get("start_offset"), "end_offset": ev.get("end_offset"),
            })
        out[qid] = {
            "event_id": str(eid),
            "event_date": event_date.get(str(eid)),
            "claim_ids": claim_ids,
            "evidence": audit_evidence,
            "source_published_at": pub_at,
            "source_url": url,
            "superseded": bool(superseded),
            "supersession_note": (
                "A more recent claim may supersede this item — verify against the latest source."
                if superseded else None
            ),
        }
    return out


def resolve_eligible_bundle(
    supabase: Any, *, exam_id: str | None, cadence: str = "weekly", now: datetime | None = None
) -> dict[str, Any] | None:
    """The learner's currently-eligible published+verified bundle for a cadence.

    Scope precedence: exact-exam (``exam_id`` match) > exam-family (``exam_family_id``
    match) > global (both null). Within a scope tier the most-recent period wins. Only
    ``status='published'`` AND ``reviewer_status='verified'`` bundles inside their
    publish/availability window are eligible.
    """
    now = now or _now()
    now_iso = now.isoformat()
    family_id = _resolve_exam_family(supabase, exam_id)
    rows = (
        supabase.table("current_affairs_bundles")
        .select("*")
        .eq("cadence", cadence)
        .eq("status", "published")
        .order("period_start", desc=True)
        .limit(100)
        .execute()
        .data
    ) or []

    def _servable(b: dict[str, Any]) -> bool:
        if b.get("reviewer_status") != "verified":
            return False
        avail = b.get("available_until")
        if avail and str(avail) <= now_iso:
            return False
        pub = b.get("publish_at")
        if pub and str(pub) > now_iso:
            return False
        return True

    servable = [b for b in rows if _servable(b)]
    # Tier the candidates; each tier is already period-desc ordered from the query.
    exact = [b for b in servable if exam_id and str(b.get("exam_id") or "") == str(exam_id)]
    family = [
        b for b in servable
        if not b.get("exam_id") and family_id and str(b.get("exam_family_id") or "") == str(family_id)
    ]
    glob = [b for b in servable if not b.get("exam_id") and not b.get("exam_family_id")]
    for tier in (exact, family, glob):
        if tier:
            return tier[0]
    return None
