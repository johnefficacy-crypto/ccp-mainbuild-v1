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


def eligible_bundle_question_ids(
    supabase: Any, bundle_id: str, *, now: datetime | None = None
) -> list[str]:
    """Ordered membership restricted to STILL-eligible promoted current-event questions.

    Mirrors the ``ca_eligible_bundle_question_ids`` SQL helper the start RPC re-derives
    under lock: a bundle member counts only if it is a reviewed promoted current_event
    inside its validity window. Freezing this set (never the raw membership) is what lets
    the RPC's exact-set integrity check pass — a stale/retired member is dropped here and
    the RPC agrees, rather than the attempt being silently shortened downstream.
    """
    now = now or _now()
    ordered = bundle_question_ids(supabase, bundle_id)
    if not ordered:
        return []
    bank = (
        supabase.table("mock_question_bank")
        .select("id,reviewer_status,source_kind,is_current_based,valid_from,valid_until")
        .in_("id", ordered)
        .execute()
        .data
    ) or []
    ok = {
        str(r["id"]) for r in bank
        if r.get("source_kind") == "current_event"
        and r.get("is_current_based")
        and r.get("reviewer_status") in _SELECTABLE
        and _within_window(r, now)
    }
    return [qid for qid in ordered if qid in ok]


def load_question_provenance(
    supabase: Any, question_ids: list[str], *, now: datetime | None = None
) -> dict[str, dict[str, Any]]:
    """Per-question post-submit provenance envelope (frozen at attempt start).

    Returns ``{question_id: {event_date, source_published_at, source_url, superseded,
    supersession_note}}`` — the §10 feedback set (correct answer + explanation already
    live in the question snapshot). Joins: bank → event (``current_affairs_item_id``);
    question → grounding claims/evidence via ``current_affairs_question_links`` →
    ``current_affairs_claim_evidence`` → ``current_affairs_documents``; supersession from
    ``current_affairs_claims.factual_status``/``superseded_at``.
    """
    now = now or _now()
    qids = [str(q) for q in question_ids]
    if not qids:
        return {}

    def _rows(table, cols, col, vals):
        vals = [v for v in vals if v]
        if not vals:
            return []
        try:
            return (supabase.table(table).select(cols).in_(col, list(dict.fromkeys(vals)))
                    .execute().data) or []
        except Exception:  # pragma: no cover - defensive
            return []

    bank = _rows("mock_question_bank", "id,current_affairs_item_id", "id", qids)
    event_by_q = {str(b["id"]): b.get("current_affairs_item_id") for b in bank}
    events = _rows("current_affairs_events", "id,event_date", "id", list(event_by_q.values()))
    event_date = {str(e["id"]): e.get("event_date") for e in events}

    links = _rows("current_affairs_question_links", "mock_question_id,claim_id", "mock_question_id", qids)
    claims_by_q: dict[str, list[str]] = {}
    for lk in links:
        claims_by_q.setdefault(str(lk.get("mock_question_id")), []).append(str(lk.get("claim_id")))
    all_claims = [c for cs in claims_by_q.values() for c in cs]

    claims = _rows("current_affairs_claims", "id,factual_status,superseded_at", "id", all_claims)
    claim_state = {str(c["id"]): c for c in claims}

    evidence = _rows("current_affairs_claim_evidence", "claim_id,document_id,evidence_role", "claim_id", all_claims)
    doc_for_claim: dict[str, str] = {}
    for ev in evidence:
        cid = str(ev.get("claim_id"))
        if cid not in doc_for_claim or ev.get("evidence_role") == "primary":
            if ev.get("document_id"):
                doc_for_claim[cid] = str(ev["document_id"])
    docs = _rows("current_affairs_documents", "id,published_at,final_url,source_url", "id",
                 list(doc_for_claim.values()))
    doc_by_id = {str(d["id"]): d for d in docs}

    out: dict[str, dict[str, Any]] = {}
    for qid in qids:
        claim_ids = claims_by_q.get(qid, [])
        superseded = any(
            (claim_state.get(cid, {}).get("factual_status") not in (None, "current"))
            or claim_state.get(cid, {}).get("superseded_at")
            for cid in claim_ids
        )
        pub_at = url = None
        for cid in claim_ids:
            doc = doc_by_id.get(doc_for_claim.get(cid, ""))
            if doc:
                pub_at = pub_at or doc.get("published_at")
                url = url or doc.get("final_url") or doc.get("source_url")
        eid = event_by_q.get(qid)
        out[qid] = {
            "event_date": event_date.get(str(eid)) if eid else None,
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
