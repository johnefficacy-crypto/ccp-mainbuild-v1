"""Admin mock question service — state machine, CRUD, dedup, bilingual linking.

State machine:
    draft ──submit──▶ in_review
    in_review ──approve──▶ verified ──publish──▶ published
    in_review ──request_changes──▶ needs_changes ──submit──▶ in_review
    published ──archive──▶ archived ──restore──▶ verified
    * ──force──▶ * (publisher only, logged with reason)

Conflict-of-interest: reviewer cannot approve a question where
    created_by = actor_id.  Enforced here, not in the RBAC decorator.

Fingerprint:
    sha256(lower(normalize_ws(question_text)) | sorted(option_texts) | correct_idx)
    Stored in question_fingerprint. Unique constraint in DB catches collisions.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("career_copilot.admin.mock_questions")

# ── State machine ──────────────────────────────────────────────────────────────

VALID_STATUSES = frozenset({
    "draft", "in_review", "needs_changes", "verified", "published", "archived",
})

# Map (from_status, action) → to_status
_TRANSITIONS: dict[tuple[str, str], str] = {
    ("draft",          "submit"):          "in_review",
    ("needs_changes",  "submit"):          "in_review",
    ("in_review",      "approve"):         "verified",
    ("in_review",      "request_changes"): "needs_changes",
    ("verified",       "publish"):         "published",
    ("published",      "archive"):         "archived",
    ("archived",       "restore"):         "verified",
}

# Actions that require specific permission tiers (enforced at API layer, checked here too)
_REVIEWER_ACTIONS  = frozenset({"approve", "request_changes"})
_PUBLISHER_ACTIONS = frozenset({"publish", "archive", "restore", "force"})


def allowed_transitions(status: str) -> list[str]:
    """Return the list of actions available from *status*."""
    return [action for (s, action) in _TRANSITIONS if s == status]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Fingerprint ────────────────────────────────────────────────────────────────

def compute_fingerprint(question_text: str, options: list[dict], correct_option_id: str | None) -> str:
    """Compute the canonical question fingerprint.

    Stable: lower-cased, whitespace-normalised question text
            + sorted option texts (alphabetical)
            + index of the correct option (position after sort)
    """
    norm = " ".join(question_text.lower().split())

    # Sort options by text so reordering doesn't change fingerprint
    sorted_opts = sorted(options, key=lambda o: (o.get("option_text") or "").lower())
    opts_text = "|".join((o.get("option_text") or "").strip() for o in sorted_opts)

    # Correct option index in the sorted list
    correct_idx = ""
    for i, o in enumerate(sorted_opts):
        if o.get("id") == correct_option_id:
            correct_idx = str(i)
            break

    raw = f"{norm}|{opts_text}|{correct_idx}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── Audit log helper ───────────────────────────────────────────────────────────

def _write_log(
    supabase: Any,
    *,
    question_id: str,
    actor_id: str | None,
    action: str,
    from_status: str | None = None,
    to_status: str | None = None,
    notes: str | None = None,
    diff: dict | None = None,
) -> None:
    try:
        supabase.table("mock_question_review_log").insert({
            "question_id": question_id,
            "actor_id": actor_id,
            "from_status": from_status,
            "to_status": to_status,
            "action": action,
            "notes": notes,
            "diff": diff,
            "at": _now_iso(),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("mock_question_review_log write failed: %s", exc)


def _build_diff(old: dict, new_data: dict) -> dict:
    """Return field-level diff for audit log."""
    changed: dict[str, dict] = {}
    for key, new_val in new_data.items():
        old_val = old.get(key)
        if old_val != new_val:
            changed[key] = {"from": old_val, "to": new_val}
    return changed


# ── CRUD ───────────────────────────────────────────────────────────────────────

def _fetch_question(supabase: Any, question_id: str) -> dict | None:
    rows = (
        supabase.table("mock_question_bank")
        .select("*")
        .eq("id", question_id)
        .limit(1)
        .execute()
        .data
    ) or []
    return rows[0] if rows else None


def _fetch_options(supabase: Any, question_id: str) -> list[dict]:
    return (
        supabase.table("mock_question_options")
        .select("*")
        .eq("question_id", question_id)
        .order("option_index")
        .execute()
        .data
    ) or []


def _fetch_sources(supabase: Any, question_id: str) -> list[dict]:
    return (
        supabase.table("mock_question_sources")
        .select("*")
        .eq("question_id", question_id)
        .order("created_at")
        .execute()
        .data
    ) or []


def _fetch_tags(supabase: Any, question_id: str) -> list[dict]:
    return (
        supabase.table("mock_question_topic_tags")
        .select("*, topics(id, name, slug)")
        .eq("question_id", question_id)
        .execute()
        .data
    ) or []


def _fetch_log(supabase: Any, question_id: str) -> list[dict]:
    return (
        supabase.table("mock_question_review_log")
        .select("*")
        .eq("question_id", question_id)
        .order("at", desc=True)
        .limit(100)
        .execute()
        .data
    ) or []


def create_question(supabase: Any, actor: dict, data: dict) -> dict:
    """Create a new draft question.

    ``data`` fields:
        question_text, question_type, difficulty, is_conceptual, is_factual,
        is_current, valid_from, valid_until, event_anchor_date, explanation,
        language, exam_id, subject_id, topic_id, options (list of
        {option_text, is_correct}), exam_family.

    Returns the created question dict (with options).
    Raises ValueError for missing required fields.
    Raises RuntimeError on DB error.
    """
    actor_id = actor.get("id")
    q_text = (data.get("question_text") or "").strip()
    if not q_text:
        raise ValueError("question_text is required")
    options_raw: list[dict] = data.get("options") or []
    if len(options_raw) < 2:
        raise ValueError("at least 2 options required")
    correct_options = [o for o in options_raw if o.get("is_correct")]
    if not correct_options:
        raise ValueError("exactly one correct option required")

    # Insert question (fingerprint resolved via trigger; we'll update after options)
    q_row = {
        "question_text": q_text,
        "question_type": data.get("question_type", "mcq"),
        "difficulty": data.get("difficulty") or "medium",
        "is_conceptual": bool(data.get("is_conceptual", False)),
        "is_factual": bool(data.get("is_factual", False)),
        "is_current": bool(data.get("is_current", False)),
        "valid_from": data.get("valid_from"),
        "valid_until": data.get("valid_until"),
        "event_anchor_date": data.get("event_anchor_date"),
        "explanation": data.get("explanation"),
        "language": data.get("language", "en"),
        "exam_id": data.get("exam_id"),
        "exam_family": data.get("exam_family"),
        "subject_id": data.get("subject_id"),
        "topic_id": data.get("topic_id"),
        "reviewer_status": "draft",
        "created_by": actor_id,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    result = supabase.table("mock_question_bank").insert(q_row).execute()
    rows = (result.data or [])
    if not rows:
        raise RuntimeError("question insert returned no row")
    question = rows[0]
    question_id = question["id"]

    # Insert options
    opt_rows = []
    for idx, opt in enumerate(options_raw):
        opt_rows.append({
            "question_id": question_id,
            "option_text": (opt.get("option_text") or "").strip(),
            "option_index": idx,
            "is_correct": bool(opt.get("is_correct", False)),
        })
    supabase.table("mock_question_options").insert(opt_rows).execute()

    # Determine correct_option_id
    opts = _fetch_options(supabase, question_id)
    correct_opt = next((o for o in opts if o.get("is_correct")), None)
    correct_option_id = correct_opt["id"] if correct_opt else None

    # Compute full fingerprint and update
    fp = compute_fingerprint(q_text, opts, correct_option_id)
    try:
        supabase.table("mock_question_bank").update({
            "correct_option_id": correct_option_id,
            "question_fingerprint": fp,
            "updated_at": _now_iso(),
        }).eq("id", question_id).execute()
    except Exception as exc:
        # Fingerprint collision
        if "mock_question_bank_fp_uniq" in str(exc) or "unique" in str(exc).lower():
            supabase.table("mock_question_bank").delete().eq("id", question_id).execute()
            raise ConflictError(f"question_fingerprint collision: {fp}") from exc
        raise

    question["correct_option_id"] = correct_option_id
    question["question_fingerprint"] = fp

    _write_log(supabase, question_id=question_id, actor_id=actor_id,
               action="create", to_status="draft",
               diff={"question_text": {"to": q_text}, "options_count": {"to": len(opt_rows)}})

    return {**question, "options": opts}


def update_question(supabase: Any, actor: dict, question_id: str, data: dict,
                    override_fingerprint: bool = False) -> dict:
    """Edit an owned draft or needs_changes question.

    Publisher can edit any question in any status (via override_fingerprint path).
    Author can only edit own draft / needs_changes.
    Raises PermissionError, ValueError, ConflictError, LookupError.
    """
    actor_id = actor.get("id")
    perms = set(actor.get("permissions") or [])
    is_publisher = actor.get("role") == "super_admin" or "mock_questions:publish" in perms

    q = _fetch_question(supabase, question_id)
    if q is None:
        raise LookupError(f"question {question_id!r} not found")

    editable_statuses = {"draft", "needs_changes"}
    if not is_publisher and q["reviewer_status"] not in editable_statuses:
        raise PermissionError(f"question in status {q['reviewer_status']!r} is not editable")
    if not is_publisher and q.get("created_by") != actor_id:
        raise PermissionError("you can only edit your own questions")

    updates: dict[str, Any] = {"updated_at": _now_iso()}
    for field in ("question_text", "question_type", "difficulty", "explanation",
                  "language", "exam_id", "exam_family", "subject_id", "topic_id",
                  "is_conceptual", "is_factual", "is_current",
                  "valid_from", "valid_until", "event_anchor_date"):
        if field in data:
            updates[field] = data[field]

    options_raw: list[dict] | None = data.get("options")
    opts = _fetch_options(supabase, question_id)

    if options_raw is not None:
        if len(options_raw) < 2:
            raise ValueError("at least 2 options required")
        correct_opts = [o for o in options_raw if o.get("is_correct")]
        if not correct_opts:
            raise ValueError("exactly one correct option required")

        # Replace options
        supabase.table("mock_question_options").delete().eq("question_id", question_id).execute()
        new_opt_rows = []
        for idx, opt in enumerate(options_raw):
            new_opt_rows.append({
                "question_id": question_id,
                "option_text": (opt.get("option_text") or "").strip(),
                "option_index": idx,
                "is_correct": bool(opt.get("is_correct", False)),
            })
        supabase.table("mock_question_options").insert(new_opt_rows).execute()
        opts = _fetch_options(supabase, question_id)

    # Recompute fingerprint
    q_text = updates.get("question_text") or q["question_text"]
    correct_opt = next((o for o in opts if o.get("is_correct")), None)
    correct_option_id = correct_opt["id"] if correct_opt else q.get("correct_option_id")
    fp = compute_fingerprint(q_text, opts, correct_option_id)

    # Check for fingerprint collision (unless publisher is overriding)
    existing_fp = supabase.table("mock_question_bank").select("id").eq("question_fingerprint", fp).neq("id", question_id).limit(1).execute().data or []
    if existing_fp and not (is_publisher and override_fingerprint):
        raise ConflictError(f"fingerprint collision with question {existing_fp[0]['id']}")

    updates["question_fingerprint"] = fp
    updates["correct_option_id"] = correct_option_id

    old_q = dict(q)
    supabase.table("mock_question_bank").update(updates).eq("id", question_id).execute()

    _write_log(supabase, question_id=question_id, actor_id=actor_id,
               action="edit", from_status=q["reviewer_status"],
               to_status=q["reviewer_status"], diff=_build_diff(old_q, updates))

    updated = _fetch_question(supabase, question_id)
    return {**(updated or {}), "options": opts}


def transition(
    supabase: Any,
    actor: dict,
    question_id: str,
    action: str,
    *,
    notes: str | None = None,
    reason: str | None = None,
    to_status_override: str | None = None,
) -> dict:
    """Apply a state-machine action.

    Raises:
        LookupError    — question not found
        PermissionError — wrong actor for the action
        ValueError     — illegal transition (422 at API layer)
        ConflictError  — self-review attempt (409)
    """
    actor_id = actor.get("id")
    perms = set(actor.get("permissions") or [])
    is_super = actor.get("role") == "super_admin"
    is_publisher = is_super or "mock_questions:publish" in perms
    is_reviewer = is_publisher or "mock_questions:review" in perms

    q = _fetch_question(supabase, question_id)
    if q is None:
        raise LookupError(f"question {question_id!r} not found")

    from_status = q["reviewer_status"]

    if action == "force":
        if not is_publisher:
            _write_log(supabase, question_id=question_id, actor_id=actor_id,
                       action="unauthorized", from_status=from_status,
                       notes="force without publisher permission")
            raise PermissionError("publisher permission required for force")
        if not to_status_override or to_status_override not in VALID_STATUSES:
            raise ValueError(f"force requires a valid to_status; got {to_status_override!r}")
        to_status = to_status_override
    else:
        to_status = _TRANSITIONS.get((from_status, action))
        if to_status is None:
            allowed = allowed_transitions(from_status)
            raise ValueError(
                f"transition {action!r} is not allowed from {from_status!r}. "
                f"Allowed: {allowed}"
            )

        if action in _REVIEWER_ACTIONS and not is_reviewer:
            _write_log(supabase, question_id=question_id, actor_id=actor_id,
                       action="unauthorized", from_status=from_status,
                       notes=f"{action} without reviewer permission")
            raise PermissionError("reviewer permission required")

        if action in _PUBLISHER_ACTIONS and not is_publisher:
            _write_log(supabase, question_id=question_id, actor_id=actor_id,
                       action="unauthorized", from_status=from_status,
                       notes=f"{action} without publisher permission")
            raise PermissionError("publisher permission required")

        # Conflict-of-interest: reviewer cannot approve own question
        if action == "approve" and q.get("created_by") == actor_id:
            raise ConflictError("reviewer cannot approve a question they authored")

    # Build update payload
    updates: dict[str, Any] = {
        "reviewer_status": to_status,
        "updated_at": _now_iso(),
    }
    if action in _REVIEWER_ACTIONS or action == "force":
        updates["last_reviewed_by"] = actor_id
        updates["last_reviewed_at"] = _now_iso()
    if action == "publish" or (action == "force" and to_status == "published"):
        updates["published_at"] = _now_iso()

    supabase.table("mock_question_bank").update(updates).eq("id", question_id).execute()

    _write_log(supabase, question_id=question_id, actor_id=actor_id,
               action=action, from_status=from_status, to_status=to_status,
               notes=notes or reason,
               diff={"reviewer_status": {"from": from_status, "to": to_status}})

    updated = _fetch_question(supabase, question_id)
    return updated or {}


# ── Query ──────────────────────────────────────────────────────────────────────

def list_questions(
    supabase: Any,
    actor: dict,
    *,
    status: str | None = None,
    exam_id: str | None = None,
    subject_id: str | None = None,
    topic_id: str | None = None,
    author_id: str | None = None,
    language: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Return paginated question list filtered by actor visibility.

    Authors see only their own questions. Reviewers/publishers see all.
    """
    actor_id = actor.get("id")
    perms = set(actor.get("permissions") or [])
    is_super = actor.get("role") == "super_admin"
    is_elevated = is_super or "mock_questions:review" in perms or "mock_questions:publish" in perms

    q = supabase.table("mock_question_bank").select(
        "id, question_text, question_type, difficulty, reviewer_status, "
        "language, exam_id, subject_id, topic_id, created_by, created_at, "
        "updated_at, is_conceptual, is_factual, is_current, published_at"
    )

    if not is_elevated:
        q = q.eq("created_by", actor_id)
    elif author_id:
        q = q.eq("created_by", author_id)

    if status:
        q = q.eq("reviewer_status", status)
    if exam_id:
        q = q.eq("exam_id", exam_id)
    if subject_id:
        q = q.eq("subject_id", subject_id)
    if topic_id:
        q = q.eq("topic_id", topic_id)
    if language:
        q = q.eq("language", language)

    offset = (page - 1) * page_size
    rows = q.order("created_at", desc=True).range(offset, offset + page_size - 1).execute().data or []

    return {"items": rows, "page": page, "page_size": page_size}


def get_question_detail(supabase: Any, actor: dict, question_id: str) -> dict:
    """Return full question detail: base row + options + sources + tags + log."""
    actor_id = actor.get("id")
    perms = set(actor.get("permissions") or [])
    is_elevated = (
        actor.get("role") == "super_admin"
        or "mock_questions:review" in perms
        or "mock_questions:publish" in perms
    )

    q = _fetch_question(supabase, question_id)
    if q is None:
        raise LookupError(f"question {question_id!r} not found")
    if not is_elevated and q.get("created_by") != actor_id:
        raise PermissionError("access denied")

    opts    = _fetch_options(supabase, question_id)
    sources = _fetch_sources(supabase, question_id)
    tags    = _fetch_tags(supabase, question_id)
    log     = _fetch_log(supabase, question_id)

    return {**q, "options": opts, "sources": sources, "topic_tags": tags, "review_log": log}


def get_review_queue(supabase: Any, actor: dict, page: int = 1, page_size: int = 50) -> dict:
    """Return questions in `in_review` status, newest first."""
    offset = (page - 1) * page_size
    rows = (
        supabase.table("mock_question_bank")
        .select(
            "id, question_text, difficulty, language, exam_id, subject_id, "
            "topic_id, created_by, created_at, updated_at, reviewer_status"
        )
        .eq("reviewer_status", "in_review")
        .order("updated_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
        .data
    ) or []
    return {"items": rows, "page": page, "page_size": page_size}


# ── Dedup check ────────────────────────────────────────────────────────────────

def dedup_check(supabase: Any, question_id: str, similarity_threshold: float = 0.6) -> dict:
    """Return fingerprint match + top-5 trigram neighbors."""
    q = _fetch_question(supabase, question_id)
    if q is None:
        raise LookupError(f"question {question_id!r} not found")

    fp = q.get("question_fingerprint")
    fingerprint_match: dict | None = None
    if fp:
        matches = (
            supabase.table("mock_question_bank")
            .select("id, question_text, reviewer_status, question_fingerprint")
            .eq("question_fingerprint", fp)
            .neq("id", question_id)
            .limit(1)
            .execute()
            .data
        ) or []
        if matches:
            fingerprint_match = matches[0]

    # Trigram neighbors via RPC (the migration adds pg_trgm; expose via rpc)
    trigram_neighbors: list[dict] = []
    try:
        q_text = q.get("question_text", "")
        rpc_rows = (
            supabase.rpc(
                "fn_mock_question_trigram_neighbors",
                {
                    "p_question_id": question_id,
                    "p_question_text": q_text,
                    "p_threshold": similarity_threshold,
                    "p_limit": 5,
                },
            )
            .execute()
            .data
        ) or []
        trigram_neighbors = rpc_rows
    except Exception as exc:  # noqa: BLE001
        logger.warning("trigram neighbor RPC failed: %s", exc)

    return {
        "question_id": question_id,
        "fingerprint": fp,
        "fingerprint_match": fingerprint_match,
        "trigram_neighbors": trigram_neighbors,
        "similarity_threshold": similarity_threshold,
    }


# ── Bilingual linking ──────────────────────────────────────────────────────────

def link_translation(supabase: Any, actor: dict, question_id: str, data: dict) -> dict:
    """Link two questions as translations within a question group."""
    actor_id = actor.get("id")
    group_id: str | None = data.get("group_id")
    partner_id: str | None = data.get("partner_question_id")

    q = _fetch_question(supabase, question_id)
    if q is None:
        raise LookupError(f"question {question_id!r} not found")

    if not group_id and not partner_id:
        raise ValueError("group_id or partner_question_id required")

    if not group_id and partner_id:
        # Resolve group from partner or create new one
        partner = _fetch_question(supabase, partner_id)
        if partner is None:
            raise LookupError(f"partner question {partner_id!r} not found")
        group_id = partner.get("question_group_id")
        if not group_id:
            # Create a new group
            exam_id = q.get("exam_id") or partner.get("exam_id")
            slug = f"group-{question_id[:8]}-{partner_id[:8]}"
            grp = (
                supabase.table("mock_question_groups")
                .insert({"exam_id": exam_id, "canonical_slug": slug})
                .execute()
                .data
            ) or []
            if grp:
                group_id = grp[0]["id"]
                # Link partner
                supabase.table("mock_question_bank").update({"question_group_id": group_id}).eq("id", partner_id).execute()

    supabase.table("mock_question_bank").update({
        "question_group_id": group_id, "updated_at": _now_iso()
    }).eq("id", question_id).execute()

    _write_log(supabase, question_id=question_id, actor_id=actor_id,
               action="edit", diff={"question_group_id": {"to": group_id}})

    return {"question_id": question_id, "group_id": group_id}


# ── Topic tags ─────────────────────────────────────────────────────────────────

def set_topic_tags(supabase: Any, actor: dict, question_id: str, tags: list[dict]) -> list[dict]:
    """Replace all topic tags for a question.

    Each tag: {topic_id, role}. Role must be one of the allowed values.
    """
    q = _fetch_question(supabase, question_id)
    if q is None:
        raise LookupError(f"question {question_id!r} not found")

    valid_roles = {"primary", "secondary", "prerequisite", "trap", "calculation_layer", "conceptual_layer"}
    for tag in tags:
        if tag.get("role") not in valid_roles:
            raise ValueError(f"invalid tag role {tag.get('role')!r}")

    supabase.table("mock_question_topic_tags").delete().eq("question_id", question_id).execute()
    if tags:
        rows = [{"question_id": question_id, "topic_id": t["topic_id"], "role": t["role"]} for t in tags]
        supabase.table("mock_question_topic_tags").insert(rows).execute()

    return _fetch_tags(supabase, question_id)


# ── Sources ────────────────────────────────────────────────────────────────────

def set_sources(supabase: Any, actor: dict, question_id: str, sources: list[dict]) -> list[dict]:
    """Replace all sources for a question."""
    q = _fetch_question(supabase, question_id)
    if q is None:
        raise LookupError(f"question {question_id!r} not found")

    supabase.table("mock_question_sources").delete().eq("question_id", question_id).execute()
    if sources:
        rows = [
            {
                "question_id": question_id,
                "source_kind":  s.get("source_kind", "authored"),
                "source_trust": s.get("source_trust", "unverified"),
                "source_url":   s.get("source_url"),
                "pyq_paper_id": s.get("pyq_paper_id"),
                "pyq_year":     s.get("pyq_year"),
                "evidence_text": s.get("evidence_text"),
            }
            for s in sources
        ]
        supabase.table("mock_question_sources").insert(rows).execute()

    return _fetch_sources(supabase, question_id)


# ── Custom exceptions ──────────────────────────────────────────────────────────

class ConflictError(Exception):
    """Fingerprint collision or self-review conflict."""


class PermissionError(Exception):
    """Actor lacks the required permission for this action."""
