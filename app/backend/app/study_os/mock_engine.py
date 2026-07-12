"""Mock Engine — server-authoritative attempt loop (PR1).

Handles: start → answer (idempotent upsert) → submit → result.

Scoring always reads from question_snapshot frozen at attempt start, never
from live mock_question_bank rows — so post-submit edits cannot alter scores.

After submit, a compatibility row is written to mock_tests so the existing
Mocks.jsx analytics list keeps working unchanged.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.study_os.attempt_events import record_server_event
from app.study_os.attempt_analytics import service as attempt_analytics
from app.study_os.attempt_event_types import (
    ATTEMPT_AUTO_SUBMITTED,
    ATTEMPT_STARTED,
    ATTEMPT_SUBMITTED,
    QUESTION_ANSWERED,
)
from app.utils.safe import safe_required

logger = logging.getLogger("career_copilot.study_os.mock_engine")

# E2E Playwright fixtures seed mock_question_bank rows tagged with this
# source_type (app/supabase/seeds/e2e_fixtures.sql). They are 'published' so the
# fixed-id E2E selector can load them inside the E2E DB, but they must NEVER be
# eligible for production POOL selection — otherwise a test fixture could leak
# into a real generated/criteria-built attempt. The fixed-id path
# (_load_questions_for_template) loads explicit ids and is intentionally NOT
# filtered, so E2E keeps working.
_E2E_FIXTURE_SOURCE_TYPE = "e2e_fixture"



# ── helpers ────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _safe(call, default=None):
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("mock_engine supabase call failed: %s", exc)
        return default


def _to_decimal_marks(value: int | float | Decimal) -> Decimal:
    """Normalize mark values without inheriting binary-float artifacts."""
    decimal_value = Decimal(str(value))
    if not decimal_value.is_finite():
        raise ValueError(f"total_marks must be finite, got {value!r}")
    return decimal_value


def _to_integral_marks(value: int | float | Decimal) -> int:
    """Return ``value`` as an int only when it is mathematically integral."""
    decimal_value = _to_decimal_marks(value)
    if decimal_value != decimal_value.to_integral_value():
        raise ValueError(f"total_marks must be integral, got {value!r}")
    return int(decimal_value)


def _require(call, op: str):
    try:
        result = call()
        items = getattr(result, "data", result) or []
        if not items:
            raise RuntimeError(f"{op}: no rows returned")
        return items
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{op} failed: {exc}") from exc


# ── question loading ───────────────────────────────────────────────────────────

def _load_questions_for_template(supabase: Any, template: dict) -> list[dict]:
    """Load questions + options for a template, ordered by template config.

    PR2 selector hardening: only published questions that haven't expired are
    eligible for new attempts.  Existing frozen ``question_snapshot`` rows are
    unaffected — scoring always reads from the snapshot, never from this path.
    """
    question_ids: list[str] = (template.get("config") or {}).get("question_ids") or []
    if not question_ids:
        return []

    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    _SELECTABLE = ["verified", "published", "live"]
    q_exec = supabase.table("mock_question_bank") \
        .select("*") \
        .in_("id", question_ids) \
        .in_("reviewer_status", _SELECTABLE) \
        .or_(f"valid_until.is.null,valid_until.gt.{now_iso}") \
        .execute()
    questions = {r["id"]: r for r in (q_exec.data or [])}

    # Active-lineage guard (belt-and-suspenders): exclude PYQ-derived questions
    # whose projection has gone stale or blocked since template creation.
    pyq_ids = [qid for qid, q in questions.items() if q.get("pyq_question_id")]
    if pyq_ids:
        try:
            proj_rows = (
                supabase.table("pyq_mock_question_projections")
                .select("mock_question_id")
                .eq("sync_status", "active")
                .execute()
                .data
            ) or []
            active_mock_ids = {p["mock_question_id"] for p in proj_rows}
            questions = {
                qid: q for qid, q in questions.items()
                if not q.get("pyq_question_id") or qid in active_mock_ids
            }
        except Exception:
            # Fail-closed: exclude all PYQ-derived questions if the guard query fails.
            questions = {
                qid: q for qid, q in questions.items()
                if not q.get("pyq_question_id")
            }

    # Fail-closed: if the template config lists specific question IDs, all of them
    # must survive status/expiry/lineage filtering — a shortened fixed attempt is wrong.
    missing = set(question_ids) - questions.keys()
    if missing:
        raise LookupError(
            f"{len(missing)} question(s) in fixed-template config are "
            f"unavailable (stale, blocked, expired, or not in bank): "
            f"{sorted(missing)}"
        )

    opt_exec = supabase.table("mock_question_options") \
        .select("*") \
        .in_("question_id", question_ids) \
        .order("option_index") \
        .execute()
    opts_by_q: dict[str, list[dict]] = {}
    for o in (opt_exec.data or []):
        opts_by_q.setdefault(o["question_id"], []).append(o)

    # Fail closed: if any selected question is PYQ-derived, the passage read must
    # succeed — a transient failure must not silently freeze a comprehension PYQ
    # as a standalone question (passage gone) into the immutable snapshot.
    require_stimuli = any(q.get("pyq_question_id") for q in questions.values())
    stim_by_q = _load_stimuli_for_questions(supabase, question_ids, required=require_stimuli)

    out = []
    for qid in question_ids:
        q = questions.get(qid)
        if not q:
            continue
        out.append({**q, "options": opts_by_q.get(qid, []), "stimuli": stim_by_q.get(qid, [])})
    return out


def _load_stimuli_for_questions(
    supabase: Any, question_ids: list[str], *, required: bool = False
) -> dict[str, list[dict]]:
    """Load the projected shared-passage/stimulus snapshots (migration 229's
    ``mock_question_stimuli``) for the given ``mock_question_bank`` ids.

    Ordered by ``display_order`` so a question with multiple passages renders
    them in printed order. Returns ``{mock_question_id: [stimulus, ...]}`` — empty
    for authored questions and any projected question with no verified stimuli.

    ``required``: when True (the selected set contains a PYQ-derived question),
    a read FAILURE fails closed with LookupError rather than returning an empty
    map — a projected comprehension PYQ must never start (and freeze) without its
    passage. An empty *successful* read is always fine (authored / no-stimulus).
    """
    if not question_ids:
        return {}
    try:
        res = (
            supabase.table("mock_question_stimuli")
            .select("*")
            .in_("mock_question_id", question_ids)
            .order("display_order")
            .execute()
        )
        rows = getattr(res, "data", None) or []
    except Exception as exc:  # noqa: BLE001 - distinguish read failure from empty
        if required:
            raise LookupError(
                "cannot load projected passage snapshots (mock_question_stimuli): "
                f"{exc!r}; refusing to start a projected-PYQ attempt without its passage"
            ) from exc
        logger.warning("db_op_failed op=mock_engine.load_stimuli err=%r", exc)
        return {}
    by_q: dict[str, list[dict]] = {}
    for s in rows:
        by_q.setdefault(s["mock_question_id"], []).append(s)
    return by_q


def _ordered_options(q: dict) -> list[dict]:
    """Options in projected PRINTED order.

    Migration 229 stores the printed ``display_order`` separately from
    ``option_index`` (which the projection derives from the answer-key label
    order), so the learner-facing order must follow ``display_order``, not
    ``option_index``. Sort by ``display_order`` ascending with NULLs last, then
    ``option_index``, then ``id`` as a stable tiebreak. Authored rows (all
    ``display_order`` NULL) keep their existing ``option_index`` order.
    """
    def _key(o: dict) -> tuple:
        do = o.get("display_order")
        oi = o.get("option_index")
        return (
            do is None,
            do if isinstance(do, (int, float)) else 0,
            oi if isinstance(oi, (int, float)) else 0,
            str(o.get("id") or ""),
        )
    return sorted((q.get("options") or []), key=_key)


def _question_snapshot(q: dict, *, marks_per_correct: float = 1.0, marks_per_wrong: float = 0.25) -> dict:
    """Frozen copy of a question + its options, stored in mock_attempt_responses.

    PR2: marks are template-bound (not question-bound), so they are passed in
    from the template config rather than read from the question row.
    Existing snapshots already have marks frozen; this only affects new attempts.

    Migration 183 provenance fields (pyq_year, pyq_question_id, pyq_paper_id,
    exam_id, subject_id, source_kind) are frozen here so mastery write-back and
    diagnostic tooling can re-derive PYQ lineage from the frozen attempt record
    without reading the live bank.
    """
    return {
        "id": q["id"],
        "question_text": q["question_text"],
        "question_type": q["question_type"],
        "marks": marks_per_correct,
        "negative_marks": marks_per_wrong,
        "correct_option_id": q.get("correct_option_id"),
        "explanation": q.get("explanation"),
        # Mastery write-back (PR5) derives deltas straight from the frozen
        # snapshot, so the topic/difficulty/source signals it weights on must be
        # captured here at attempt start — never read back from the live bank.
        "topic_id": q.get("topic_id"),
        "microtopic_id": q.get("microtopic_id"),
        "difficulty": q.get("difficulty") or "medium",
        "source_type": q.get("source_type") or "authored",
        "expected_time_sec": q.get("expected_time_sec"),
        # PYQ provenance — set for projected questions, null for authored.
        "exam_id": q.get("exam_id"),
        "subject_id": q.get("subject_id"),
        "source_kind": q.get("source_kind"),
        "pyq_year": q.get("pyq_year"),
        "pyq_question_id": q.get("pyq_question_id"),
        "pyq_paper_id": q.get("pyq_paper_id"),
        # PR-5/6 render fidelity: the projection (migration 229) carries the
        # source section and the shared passage/stimulus snapshot into the bank;
        # freeze them here so the attempt-taking, review, and result paths can
        # render the passage and printed option labels straight from the frozen
        # snapshot — never re-reading the live bank. Null/empty for authored rows.
        "section_id": q.get("section_id"),
        "stimuli": [
            {
                "id": s.get("id"),
                "pyq_stimulus_id": s.get("pyq_stimulus_id"),
                "stimulus_type": s.get("stimulus_type"),
                "content_text": s.get("content_text"),
                "language": s.get("language"),
                "display_order": s.get("display_order"),
            }
            for s in (q.get("stimuli") or [])
        ],
        # Frozen in projected printed order (display_order), so the learner sees
        # the PYQ's original option order, not the answer-key label order.
        "options": [
            {
                "id": o["id"],
                "option_text": o["option_text"],
                "option_index": o["option_index"],
                # Printed source label (e.g. "(a)") + printed order, projected by
                # migration 229. Null for authored options.
                "source_label": o.get("source_label"),
                "display_order": o.get("display_order"),
            }
            for o in _ordered_options(q)
        ],
    }


def _criteria_difficulty_targets(mix: dict, total: int) -> dict[str, int]:
    """Apportion ``total`` questions across difficulty buckets by ``mix`` fractions.

    Largest-remainder rounding so the per-bucket targets sum to exactly ``total``
    (plain rounding can over- or under-shoot once fractions are summed).
    """
    if not mix or total <= 0:
        return {}
    raw = {d: float(f or 0) * total for d, f in mix.items()}
    floors = {d: int(v) for d, v in raw.items()}
    remainder = total - sum(floors.values())
    for d in sorted(raw, key=lambda d: raw[d] - floors[d], reverse=True)[:max(remainder, 0)]:
        floors[d] += 1
    return floors


def _select_criteria_question_ids(
    supabase: Any,
    selector: dict,
    question_count: int,
    *,
    active_pyq_mock_ids: frozenset[str] | None = None,
    exclude_ids: frozenset[str] | None = None,
) -> list[str]:
    """Resolve a ``criteria`` section selector to concrete published question ids.

    Honours the bank filters the admin UI can configure (exam_family, subject_id,
    topic_ids) and, when present, the ``difficulty_mix`` distribution. Only
    published, non-expired questions are eligible, and time-bound current-affairs
    items (``is_current`` / ``is_current_based``) are excluded — the same base
    predicate as the generated selector's ``_exam_base_pool``, so a promoted
    ``current_event`` question can never leak into a template-path mock with a
    decaying answer. If a difficulty bucket is short, the deficit is backfilled
    from the rest of the eligible pool so a thin bucket can't silently shrink the
    section below ``question_count``.

    ``active_pyq_mock_ids``: when supplied, PYQ-derived rows (pyq_question_id IS
    NOT NULL) that are NOT in the set are excluded from the pool before
    allocation/backfill.  This prevents stale/blocked projections from being
    selected and then silently dropped by the caller's lineage guard, which would
    produce a shortened attempt without error.

    ``exclude_ids``: question IDs already allocated to prior sections in the same
    template.  Excluded from the pool before selection so the same question cannot
    appear in more than one section of the same attempt (which would violate the
    unique constraint on mock_attempt_responses(attempt_id, question_id)).
    """
    if question_count <= 0:
        return []
    filters = selector.get("filters") or {}
    _SELECTABLE = ["verified", "published", "live"]
    # Exclude E2E fixtures by construction: the criteria pool builds real
    # (generated) attempts, so a fixture row must never be drawn into one even if
    # it is published in this DB. Use is.null OR neq so NULL-provenance rows
    # (e.g. legacy authored questions) are RETAINED — a plain neq would drop them
    # because NULL <> 'e2e_fixture' is NULL in Postgres.
    q = (
        supabase.table("mock_question_bank")
        .select("*")
        .in_("reviewer_status", _SELECTABLE)
        .or_(f"source_type.is.null,source_type.neq.{_E2E_FIXTURE_SOURCE_TYPE}")
    )
    if filters.get("exam_family"):
        q = q.eq("exam_family", filters["exam_family"])
    if filters.get("subject_id"):
        q = q.eq("subject_id", filters["subject_id"])
    if filters.get("topic_ids"):
        q = q.in_("topic_id", list(filters["topic_ids"]))
    now_iso = _now_iso()
    q = q.or_(f"valid_until.is.null,valid_until.gt.{now_iso}")
    rows = _safe(lambda: q.execute(), default=None)
    pool = [
        r for r in (getattr(rows, "data", None) or [])
        if (not r.get("valid_until") or str(r["valid_until"]) > now_iso)
        # Time-bound current-affairs items are segmented OUT of the template pool,
        # mirroring mock_blueprint_selection._exam_base_pool term-for-term: a
        # promoted current_event question (is_current / is_current_based) must
        # never leak into a template-path mock with a decaying answer (GQR-G0).
        and not (bool(r.get("is_current")) or bool(r.get("is_current_based")))
    ]
    # Active-lineage guard applied inside the pool (before allocation/backfill)
    # so that stale PYQ rows cannot be drawn and then silently dropped later.
    if active_pyq_mock_ids is not None:
        pool = [
            r for r in pool
            if not r.get("pyq_question_id") or r["id"] in active_pyq_mock_ids
        ]
    # Cross-section deduplication: remove IDs already allocated to prior sections
    # so the same question cannot appear twice in the same attempt snapshot.
    if exclude_ids:
        pool = [r for r in pool if r["id"] not in exclude_ids]
    # Deterministic ordering so the same template config yields the same set.
    pool.sort(key=lambda r: str(r.get("id")))

    mix = filters.get("difficulty_mix") or {}
    if not mix:
        return [r["id"] for r in pool[:question_count]]

    buckets: dict[str, list[dict]] = {}
    for r in pool:
        buckets.setdefault(r.get("difficulty") or "medium", []).append(r)
    chosen: list[str] = []
    used: set[str] = set()
    for diff, target in _criteria_difficulty_targets(mix, question_count).items():
        for r in buckets.get(diff, [])[:target]:
            chosen.append(r["id"])
            used.add(r["id"])
    if len(chosen) < question_count:
        for r in pool:
            if r["id"] in used:
                continue
            chosen.append(r["id"])
            if len(chosen) >= question_count:
                break
    return chosen[:question_count]


def select_questions_for_template(supabase: Any, template_id: str, user_id: str) -> list[dict]:
    """PR2d selector hook; supports section ``fixed`` and ``criteria`` selectors.

    Fail-closed for fixed sections: if any question in a fixed-mode selector is
    unavailable (wrong status, expired, or lineage-blocked), raises LookupError
    rather than returning a shortened set.  A shortened fixed attempt would give
    a misleadingly different experience and must never start.

    Criteria sections apply active-lineage filtering inside the pool (before
    allocation/backfill) so a stale/blocked PYQ row is never selected and
    cannot cause silent underfill.
    """
    sections = _safe(lambda: supabase.table("mock_template_sections").select("*").eq("template_id", template_id).order("section_index").execute(), default=None)
    sec_rows = getattr(sections, "data", None) or []
    if not sec_rows:
        return []
    ordered: list[str] = []
    fixed_required: set[str] = set()  # IDs that must survive all filters
    # Each entry is (requested_count, frozenset_of_selected_ids) for criteria sections.
    # Used post-filter to fail-closed when a section ends up genuinely underfilled.
    criteria_requirements: list[tuple[int, frozenset[str]]] = []

    # ── Pass 1: collect and validate all fixed IDs upfront ────────────────────
    # Reserved before any criteria allocation so criteria sections can exclude
    # them regardless of their position (criteria→fixed, fixed→fixed, intra-fixed
    # duplicates all produce LookupError here rather than a DB constraint failure).
    all_fixed_ids: set[str] = set()
    for sec in sec_rows:
        selector = sec.get("selector") or {}
        if selector.get("mode") == "fixed":
            ids = list(selector.get("question_ids") or [])
            id_set = set(ids)
            if len(ids) != len(id_set):
                seen: dict[str, int] = {}
                for _i in ids:
                    seen[_i] = seen.get(_i, 0) + 1
                dupes = sorted(k for k, v in seen.items() if v > 1)
                raise LookupError(
                    f"fixed section '{sec.get('name') or sec.get('id', '?')}' "
                    f"contains duplicate question IDs: {dupes}"
                )
            overlap = id_set & all_fixed_ids
            if overlap:
                raise LookupError(
                    f"fixed sections have overlapping question IDs: {sorted(overlap)}"
                )
            all_fixed_ids.update(id_set)

    # Fetch active PYQ mock IDs once; passed to criteria selector so that stale
    # projections are excluded from the pool before allocation, not silently
    # dropped after — which would shorten the section without error.
    try:
        _proj = (
            supabase.table("pyq_mock_question_projections")
            .select("mock_question_id")
            .eq("sync_status", "active")
            .execute()
            .data
        ) or []
        _active_pyq_mock_ids: frozenset[str] = frozenset(p["mock_question_id"] for p in _proj)
    except Exception:
        # Fail-closed: if projection table is inaccessible, treat all PYQ rows
        # as inactive so they cannot enter the criteria pool.
        _active_pyq_mock_ids = frozenset()

    # ── Pass 2: allocate per section ──────────────────────────────────────────
    # Criteria sections exclude all fixed IDs (all_fixed_ids) plus any IDs
    # already allocated by prior criteria sections (criteria_selected), so no
    # question ID can appear in more than one section regardless of order.
    criteria_selected: set[str] = set()

    for sec in sec_rows:
        selector = sec.get("selector") or {}
        mode = selector.get("mode")
        if mode == "fixed":
            ids = list(selector.get("question_ids") or [])
            ordered.extend(ids)
            fixed_required.update(ids)
        elif mode == "criteria":
            requested = int(sec.get("question_count") or 0)
            section_ids = _select_criteria_question_ids(
                supabase, selector, requested,
                active_pyq_mock_ids=_active_pyq_mock_ids,
                exclude_ids=frozenset(all_fixed_ids | criteria_selected),
            )
            ordered.extend(section_ids)
            criteria_selected.update(section_ids)
            if requested > 0:
                criteria_requirements.append((requested, frozenset(section_ids)))
    if not ordered:
        # Even with an empty pool, validate criteria section requirements so that
        # a zero-eligible pool raises LookupError rather than returning [] and
        # falling through to the legacy _load_questions_for_template() fallback.
        for requested_count, section_id_set in criteria_requirements:
            if len(section_id_set) < requested_count:
                raise LookupError(
                    f"criteria section requires {requested_count} question(s) but only "
                    f"{len(section_id_set)} are available after status/expiry/lineage filtering; "
                    f"unavailable IDs: []"
                )
        return []

    from datetime import datetime, timezone
    _now_iso = datetime.now(timezone.utc).isoformat()
    _SELECTABLE = ["verified", "published", "live"]
    q_rows = _safe(
        lambda: supabase.table("mock_question_bank")
        .select("*")
        .in_("id", ordered)
        .in_("reviewer_status", _SELECTABLE)
        .or_(f"valid_until.is.null,valid_until.gt.{_now_iso}")
        .execute(),
        default=None,
    )
    by_id = {r["id"]: r for r in (getattr(q_rows, "data", None) or [])}

    # Active-lineage guard: exclude PYQ-derived questions with non-active projections.
    pyq_ids = [qid for qid, q in by_id.items() if q.get("pyq_question_id")]
    if pyq_ids:
        try:
            proj_rows = (
                supabase.table("pyq_mock_question_projections")
                .select("mock_question_id")
                .eq("sync_status", "active")
                .execute()
                .data
            ) or []
            active_mock_ids = {p["mock_question_id"] for p in proj_rows}
            by_id = {
                qid: q for qid, q in by_id.items()
                if not q.get("pyq_question_id") or qid in active_mock_ids
            }
        except Exception:
            # Fail-closed: exclude all PYQ-derived questions if guard query fails.
            by_id = {qid: q for qid, q in by_id.items() if not q.get("pyq_question_id")}

    # Fail-closed: abort if any fixed-section question is unavailable after filtering.
    if fixed_required:
        missing = fixed_required - by_id.keys()
        if missing:
            raise LookupError(
                f"{len(missing)} question(s) in fixed-template section(s) are "
                f"unavailable (stale, blocked, expired, or not in bank): "
                f"{sorted(missing)}"
            )

    # Fail-closed: abort if any criteria section ends up genuinely underfilled.
    # Pre-allocation lineage filtering removes stale PYQ rows, but if the eligible
    # pool is genuinely thin the section count will be below the configured target.
    # Starting a shortened attempt would give a misleading experience; fail instead.
    for requested_count, section_id_set in criteria_requirements:
        surviving = [qid for qid in section_id_set if qid in by_id]
        if len(surviving) < requested_count:
            unavailable = sorted(section_id_set - by_id.keys())
            raise LookupError(
                f"criteria section requires {requested_count} question(s) but only "
                f"{len(surviving)} are available after status/expiry/lineage filtering; "
                f"unavailable IDs: {unavailable}"
            )

    # Attach options (ordered by option_index) — without these the frozen
    # snapshot has no options and the attempt renders no answer choices.
    opt_rows = _safe(
        lambda: supabase.table("mock_question_options")
        .select("*")
        .in_("question_id", ordered)
        .order("option_index")
        .execute(),
        default=None,
    )
    opts_by_q: dict[str, list[dict]] = {}
    for o in (getattr(opt_rows, "data", None) or []):
        opts_by_q.setdefault(o["question_id"], []).append(o)
    return [{**by_id[qid], "options": opts_by_q.get(qid, [])} for qid in ordered if qid in by_id]


# ── public API ─────────────────────────────────────────────────────────────────

def start_attempt(supabase: Any, user_id: str, template_slug: str) -> dict:
    """Create a new in_progress attempt.

    Raises:
        LookupError — template not found or has no questions.
        ConflictError — active attempt already exists.
        RuntimeError — DB insert failed.
    """
    tmpl_rows = _safe(
        lambda: supabase.table("mock_templates")
        .select("*")
        .eq("slug", template_slug)
        .eq("status", "active")
        .limit(1)
        .execute(),
        default=None,
    )
    templates = getattr(tmpl_rows, "data", None) or []
    if not templates:
        raise LookupError(f"template '{template_slug}' not found")
    template = templates[0]

    existing = _safe(
        lambda: supabase.table("mock_attempts")
        .select("id,status,expires_at,started_at")
        .eq("user_id", user_id)
        .eq("template_id", template["id"])
        .eq("status", "in_progress")
        .limit(1)
        .execute(),
        default=None,
    )
    if (getattr(existing, "data", None) or []):
        raise ConflictError("active attempt already exists for this template")

    questions = select_questions_for_template(supabase, template["id"], user_id)
    if not questions:
        questions = _load_questions_for_template(supabase, template)
    if not questions:
        raise LookupError("template has no available questions")

    now = _now()
    expires_at = now + timedelta(seconds=int(template.get("duration_sec") or 3600))

    template_snapshot = {
        "id": template["id"],
        "slug": template["slug"],
        "name": template["name"],
        "total_questions": template.get("total_questions"),
        "duration_sec": template.get("duration_sec"),
        "negative_marking": template.get("negative_marking"),
        "marks_per_correct": float(template.get("marks_per_correct") or 1),
        "marks_per_wrong": float(template.get("marks_per_wrong") or 0.25),
        "question_ids": [q["id"] for q in questions],
        "interface_mode": (template.get("config") or {}).get("interface_mode", "simple"),
        "sections": (template.get("config") or {}).get("sections") or [],
        "allow_switching": bool((template.get("config") or {}).get("allow_switching", True)),
    }

    attempt_rows = _require(
        lambda: supabase.table("mock_attempts").insert({
            "user_id": user_id,
            "template_id": template["id"],
            "template_snapshot": template_snapshot,
            "status": "in_progress",
            "started_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "current_section_index": 0,
            "section_locks_enabled": not bool((template.get("config") or {}).get("allow_switching", True)),
        }).execute(),
        op="mock_attempts.insert",
    )
    attempt = attempt_rows[0]
    attempt_id = attempt["id"]

    tmpl_marks     = float(template.get("marks_per_correct") or 1)
    tmpl_neg_marks = float(template.get("marks_per_wrong") or 0.25)
    response_rows = [
        {
            "attempt_id": attempt_id,
            "question_id": q["id"],
            "question_snapshot": _question_snapshot(
                q,
                marks_per_correct=tmpl_marks,
                marks_per_wrong=tmpl_neg_marks,
            ),
            "is_visited": False,
            "is_marked_for_review": False,
            "client_seq": 0,
        }
        for q in questions
    ]
    _require(
        lambda: supabase.table("mock_attempt_responses").insert(response_rows).execute(),
        op="mock_attempt_responses.insert_initial",
    )

    record_server_event(
        supabase, attempt_id, user_id, ATTEMPT_STARTED,
        payload={"template_slug": template_slug},
        occurred_at=now.isoformat(),
    )

    return {
        "attempt_id": attempt_id,
        "expires_at": expires_at.isoformat(),
        "current_section_index": 0,
        "section_locks_enabled": not bool((template.get("config") or {}).get("allow_switching", True)),
        "questions": [_serialise_question_for_attempt(q) for q in questions],
    }


def get_attempt(supabase: Any, user_id: str, attempt_id: str) -> dict:
    """Return current attempt state with saved responses and time_remaining_sec."""
    attempt = _fetch_attempt(supabase, user_id, attempt_id)

    resp_rows = _safe(
        lambda: supabase.table("mock_attempt_responses")
        .select("*")
        .eq("attempt_id", attempt_id)
        .execute(),
        default=None,
    )
    responses = getattr(resp_rows, "data", None) or []

    snapshot = attempt.get("template_snapshot") or {}
    question_ids: list[str] = snapshot.get("question_ids") or []

    resp_by_q = {r["question_id"]: r for r in responses}

    questions_out = []
    for qid in question_ids:
        r = resp_by_q.get(qid)
        snap = (r or {}).get("question_snapshot") or {}
        questions_out.append({
            "question_id": qid,
            "question_text": snap.get("question_text"),
            "question_type": snap.get("question_type"),
            "marks": snap.get("marks"),
            "negative_marks": snap.get("negative_marks"),
            "options": snap.get("options") or [],
            # PR-5/6: shared passage/stimulus + source section, frozen at start,
            # so a projected PYQ renders its passage while the learner attempts it.
            "stimuli": snap.get("stimuli") or [],
            "section_id": snap.get("section_id"),
            "selected_option_id": (r or {}).get("selected_option_id"),
            "is_marked_for_review": bool((r or {}).get("is_marked_for_review")),
            "is_visited": bool((r or {}).get("is_visited")),
            "time_spent_sec": int((r or {}).get("time_spent_sec") or 0),
            "section_index": _question_section_index(snapshot, qid),
        })

    time_remaining = _practice_aware_time_remaining_sec(attempt, snapshot)

    return {
        "attempt_id": attempt_id,
        "status": attempt["status"],
        "expires_at": attempt["expires_at"],
        "time_remaining_sec": time_remaining,
        "questions": questions_out,
        "current_section_index": int(attempt.get("current_section_index") or 0),
        "section_locks_enabled": bool(attempt.get("section_locks_enabled")),
        "template_interface_mode": snapshot.get("interface_mode") or "simple",
        "template_config": {"interface_mode": snapshot.get("interface_mode"), "allow_switching": snapshot.get("allow_switching")},
        "sections": _get_section_states(supabase, attempt_id),
    }




def _question_section_index(snapshot: dict, question_id: str) -> int | None:
    qids = snapshot.get("question_ids") or []
    sections = snapshot.get("sections") or []
    for sec in sections:
        idx = int(sec.get("section_index") or 0)
        for qid in sec.get("question_ids") or []:
            if qid == question_id:
                return idx
    if question_id in qids:
        return 0
    return None


def _get_section_states(supabase: Any, attempt_id: str) -> list[dict]:
    rows = _safe(lambda: supabase.table("mock_attempt_section_state").select("*").eq("attempt_id", attempt_id).order("section_index").execute(), default=None)
    return getattr(rows, "data", None) or []


def enter_section(supabase: Any, user_id: str, attempt_id: str, section_index: int) -> dict:
    attempt = _fetch_attempt(supabase, user_id, attempt_id)
    current = int(attempt.get("current_section_index") or 0)
    locked = bool(attempt.get("section_locks_enabled"))
    if locked and section_index < current:
        raise ValueError("backward section movement is not allowed")
    now = _now_iso()
    _safe(lambda: supabase.table("mock_attempts").update({"current_section_index": section_index}).eq("id", attempt_id).execute(), default=None)
    _safe(lambda: supabase.table("mock_attempt_section_state").upsert({"attempt_id": attempt_id, "section_index": section_index, "entered_at": now}).execute(), default=None)  # safe-write-ok: navigation state; non-critical, not used for scoring
    return {"ok": True, "current_section_index": section_index}

def save_answer(
    supabase: Any,
    user_id: str,
    attempt_id: str,
    question_id: str,
    selected_option_id: str | None,
    is_marked_for_review: bool,
    client_seq: int,
    time_spent_sec: int,
) -> dict:
    """Idempotent upsert for a single answer.

    Rejected (raises ValueError) when:
      - attempt is not in_progress
      - attempt has expired
      - incoming client_seq ≤ stored client_seq (stale/duplicate)
    """
    attempt = _fetch_attempt(supabase, user_id, attempt_id)
    if attempt["status"] != "in_progress":
        raise ValueError("attempt is not in progress")
    if _time_remaining_sec(attempt) <= 0:
        raise ValueError("attempt has expired")
    snapshot = attempt.get("template_snapshot") or {}
    if bool(attempt.get("section_locks_enabled")):
        expected = _question_section_index(snapshot, question_id)
        if expected is not None and expected != int(attempt.get("current_section_index") or 0):
            raise ValueError("question is outside current section")

    existing = _safe(
        lambda: supabase.table("mock_attempt_responses")
        .select("id,client_seq")
        .eq("attempt_id", attempt_id)
        .eq("question_id", question_id)
        .limit(1)
        .execute(),
        default=None,
    )
    existing_rows = getattr(existing, "data", None) or []
    if existing_rows:
        stored_seq = int(existing_rows[0].get("client_seq") or 0)
        if client_seq <= stored_seq:
            # A client retry after a partial-failure write replays the same
            # client_seq. The row was already written (and the QUESTION_ANSWERED
            # event already emitted) on the first call, so we acknowledge without
            # re-processing — no duplicate row, no duplicate side effect.
            return {"ok": True, "idempotent": True, "status": "already_recorded"}

    payload = {
        "selected_option_id": selected_option_id,
        "is_marked_for_review": is_marked_for_review,
        "is_visited": True,
        "time_spent_sec": time_spent_sec,
        "client_seq": client_seq,
        "updated_at": _now_iso(),
    }

    try:
        result = (
            supabase.table("mock_attempt_responses")
            .update(payload)
            .eq("attempt_id", attempt_id)
            .eq("question_id", question_id)
            .execute()
        )
    except Exception as exc:
        raise AnswerPersistenceError(
            f"DB write rejected for attempt={attempt_id} question={question_id}: {exc}"
        ) from exc
    updated_rows = getattr(result, "data", None) or []
    if not updated_rows:
        raise AnswerPersistenceError(
            f"answer update affected 0 rows: attempt={attempt_id} question={question_id}"
        )

    # INVARIANT: events are telemetry, not source of truth.
    # mock_attempt_responses.selected_option_id is the only authority for scoring.
    # Never record QUESTION_ANSWERED before the response row update is confirmed.
    # See docs/mock_engine/attempt_save_semantics.md.
    record_server_event(
        supabase, attempt_id, user_id, QUESTION_ANSWERED,
        payload={
            "question_id": question_id,
            "selected_option_id": selected_option_id,
            "is_marked_for_review": is_marked_for_review,
            "time_spent_sec": time_spent_sec,
        },
    )

    return {"ok": True, "idempotent": False}


def _finalize_submission(
    supabase: Any,
    attempt: dict,
    user_id: str,
    *,
    submitted_at: str,
    event_type: str,
) -> tuple[dict, list[dict], list[dict]]:
    """Score an in-progress attempt and flip it to ``submitted``.

    Shared by the user-initiated ``submit_attempt`` and the sweeper's
    ``auto_submit_attempt``. Handles only the deterministic, snapshot-based work
    (scoring, status flip, lifecycle event, Mocks.jsx compat row). Derivation is
    NOT run here — callers decide whether to run it inline or schedule a job.
    """
    attempt_id = attempt["id"]
    resp_rows = _safe(
        lambda: supabase.table("mock_attempt_responses")
        .select("*")
        .eq("attempt_id", attempt_id)
        .execute(),
        default=None,
    )
    responses = getattr(resp_rows, "data", None) or []

    snapshot = attempt.get("template_snapshot") or {}
    neg_marking = bool(snapshot.get("negative_marking", True))

    total_correct = 0
    total_wrong = 0
    total_unattempted = 0
    score_raw = 0.0
    updates = []

    for r in responses:
        snap = r.get("question_snapshot") or {}
        correct_opt = snap.get("correct_option_id")
        selected = r.get("selected_option_id")
        marks = float(snap.get("marks") or 1)
        neg = float(snap.get("negative_marks") or 0)

        if not selected:
            total_unattempted += 1
            is_correct = None
            awarded = 0.0
        elif selected == correct_opt:
            total_correct += 1
            is_correct = True
            awarded = marks
            score_raw += marks
        else:
            total_wrong += 1
            is_correct = False
            if neg_marking:
                awarded = -neg
                score_raw -= neg
            else:
                awarded = 0.0

        updates.append({
            "id": r["id"],
            "is_correct": is_correct,
            "marks_awarded": awarded,
        })

    # Per-response score writes are correctness-critical: a silent failure here
    # would flip the attempt to ``submitted`` (below) while individual responses
    # keep null/stale marks. Use safe_required and raise on failure so the
    # attempt is left ``in_progress`` (the safe state) and the caller can retry —
    # re-scoring is idempotent because marks come from the frozen snapshot and
    # these are overwrites, not increments.
    for upd in updates:
        written = safe_required(
            lambda u=upd: supabase.table("mock_attempt_responses")
            .update({"is_correct": u["is_correct"], "marks_awarded": u["marks_awarded"]})
            .eq("id", u["id"])
            .execute(),
            op="mock_engine.finalize_response_score",
            log=logger,
        )
        if written is None:
            raise SubmissionPersistenceError(
                f"response score write failed: attempt={attempt_id} response={upd['id']}"
            )

    total_q = len(responses)
    max_score = sum(
        (_to_decimal_marks((r.get("question_snapshot") or {}).get("marks") or 1)
         for r in responses),
        Decimal("0"),
    )
    max_score_float = float(max_score)
    pct = round(score_raw / max_score_float * 100, 2) if max_score_float > 0 else 0.0

    # Attempt finalization is correctness-critical: this flip + aggregate scores
    # is the headline result the client reads back. A silent failure must not be
    # reported as a successful submission. Raising here (before the submitted
    # event and the mock_tests compat row below) leaves the attempt
    # ``in_progress`` so a retry re-runs cleanly.
    finalized = safe_required(
        lambda: supabase.table("mock_attempts")
        .update({
            "status": "submitted",
            "submitted_at": submitted_at,
            "score_raw": round(score_raw, 2),
            "score_percentage": pct,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "total_unattempted": total_unattempted,
        })
        .eq("id", attempt_id)
        .execute(),
        op="mock_engine.finalize_attempt",
        log=logger,
    )
    if finalized is None:
        raise AttemptFinalizationError(
            f"attempt finalization write failed: attempt={attempt_id}"
        )

    # Server-authoritative event — written immediately after the status flip.
    record_server_event(
        supabase, attempt_id, user_id, event_type,
        payload={
            "score_raw": round(score_raw, 2),
            "score_percentage": pct,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "total_unattempted": total_unattempted,
        },
        occurred_at=submitted_at,
    )

    # Compatibility row for existing Mocks.jsx analytics
    _emit_mock_tests_row(supabase, user_id, attempt, score_raw, max_score,
                         total_correct, total_wrong, total_q, submitted_at)

    updated_attempt = {
        **attempt,
        "status": "submitted",
        "submitted_at": submitted_at,
        "score_raw": round(score_raw, 2),
        "score_percentage": pct,
        "total_correct": total_correct,
        "total_wrong": total_wrong,
        "total_unattempted": total_unattempted,
    }
    return updated_attempt, responses, updates


def _repair_submitted_side_effects(supabase: Any, attempt_id: str) -> None:
    """Idempotently reconcile post-finalize side effects for a submitted attempt.

    Covers the ambiguous case where the ``mock_attempts`` finalization UPDATE
    committed on the server but the client call raised before the submitted
    event, the ``mock_tests`` compat row, or analytics derivation ran — so the
    resubmit fast path would otherwise skip them forever. Self-healing and
    best-effort: when a side effect is missing it schedules the existing retry
    job (the sweeper drains it and both jobs are idempotent). Never raises — a
    repair failure must not break an otherwise-successful resubmit. The
    ATTEMPT_SUBMITTED event is telemetry only (not source of truth) and is
    intentionally not re-emitted here to avoid duplicate events.
    """
    compat = _safe(
        lambda: supabase.table("mock_tests")
        .select("id")
        .eq("mock_attempt_id", attempt_id)
        .limit(1)
        .execute(),
        default=None,
    )
    if not getattr(compat, "data", None):
        schedule_job(supabase, JOB_MOCK_TESTS_RETRY, attempt_id)

    summary = _safe(
        lambda: supabase.table("mock_attempt_summary")
        .select("attempt_id")
        .eq("attempt_id", attempt_id)
        .limit(1)
        .execute(),
        default=None,
    )
    if not getattr(summary, "data", None):
        schedule_job(supabase, JOB_ANALYTICS_RETRY, attempt_id)


def submit_attempt(
    supabase: Any,
    user_id: str,
    attempt_id: str,
    claimed_answered_count: int | None = None,
) -> dict:
    """Score and finalise the attempt. Idempotent — second call returns same result."""
    attempt = _fetch_attempt(supabase, user_id, attempt_id)

    if attempt["status"] == "submitted":
        # Reconcile the ambiguous "finalization UPDATE committed but the client
        # raised before the side effects ran" case: a retry would otherwise take
        # this fast path and never (re)create the mock_tests compat row or
        # analytics, leaving a submitted attempt missing from history/analytics.
        _repair_submitted_side_effects(supabase, attempt_id)
        return _build_result(supabase, attempt)

    if attempt["status"] != "in_progress":
        raise ValueError("attempt is not in progress")

    if claimed_answered_count is not None:
        resp_rows = _safe(
            lambda: supabase.table("mock_attempt_responses")
            .select("selected_option_id")
            .eq("attempt_id", attempt_id)
            .execute(),
            default=None,
        )
        db_answered = sum(
            1 for r in (getattr(resp_rows, "data", None) or [])
            if r.get("selected_option_id") is not None
        )
        if claimed_answered_count > db_answered:
            raise SubmitConsistencyError(
                f"client claims {claimed_answered_count} answered, "
                f"DB has {db_answered}; refusing to submit"
            )

    now_iso = _now_iso()
    updated_attempt, responses, updates = _finalize_submission(
        supabase, attempt, user_id, submitted_at=now_iso, event_type=ATTEMPT_SUBMITTED,
    )

    try:
        attempt_analytics.compute_and_persist(supabase, attempt_id)
        _complete_job(supabase, JOB_ANALYTICS_RETRY, attempt_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("derivation failed attempt=%s", attempt_id, exc_info=exc)
        schedule_job(supabase, JOB_ANALYTICS_RETRY, attempt_id, last_error=str(exc))

    return _build_result(supabase, updated_attempt, responses=responses, updates=updates)


def auto_submit_attempt(supabase: Any, attempt_id: str) -> dict:
    """Submit an expired in-progress attempt on the user's behalf (sweeper path).

    Idempotent: a no-op once the attempt has left ``in_progress``. Stamps
    ``submitted_at`` with the attempt's ``expires_at`` (the moment the window
    actually closed, not the sweeper's wall clock) and emits
    ``attempt.auto_submitted``. Derivation is scheduled as an ``analytics_retry``
    job rather than run synchronously, so one slow derivation cannot stall the
    sweep batch.
    """
    attempt = _fetch_attempt_by_id(supabase, attempt_id)
    if attempt is None or attempt.get("status") != "in_progress":
        return {"ok": True, "skipped": True}

    submitted_at = attempt.get("expires_at") or _now_iso()
    _finalize_submission(
        supabase, attempt, attempt["user_id"],
        submitted_at=submitted_at, event_type=ATTEMPT_AUTO_SUBMITTED,
    )
    schedule_job(supabase, JOB_ANALYTICS_RETRY, attempt_id)
    # D2 (revised): do NOT eagerly enqueue mastery_retry here. The
    # JOB_ANALYTICS_RETRY handler (D4) is the single resolution point for mastery
    # mode, calling get_or_resolve_pinned_mastery_flag after analytics succeeds.
    # Eager enqueue here would resolve the flag from the current env before
    # analytics runs, racing with any FF or allowlist change between auto-submit
    # and the analytics job, and could create a conflicting live+shadow pair for
    # the same attempt.
    return {"ok": True, "skipped": False, "submitted_at": submitted_at}


def get_result(supabase: Any, user_id: str, attempt_id: str) -> dict:
    attempt = _fetch_attempt(supabase, user_id, attempt_id)
    if attempt["status"] != "submitted":
        raise ValueError("attempt not yet submitted")
    return _build_result(supabase, attempt)


# ── internal helpers ───────────────────────────────────────────────────────────

def _fetch_attempt(supabase: Any, user_id: str, attempt_id: str) -> dict:
    rows = _safe(
        lambda: supabase.table("mock_attempts")
        .select("*")
        .eq("id", attempt_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute(),
        default=None,
    )
    items = getattr(rows, "data", None) or []
    if not items:
        raise LookupError("attempt not found")
    return items[0]


def _fetch_attempt_by_id(supabase: Any, attempt_id: str) -> dict | None:
    """Fetch an attempt without an owner filter — for system/sweeper paths."""
    rows = _safe(
        lambda: supabase.table("mock_attempts")
        .select("*")
        .eq("id", attempt_id)
        .limit(1)
        .execute(),
        default=None,
    )
    return (getattr(rows, "data", None) or [None])[0]


def _time_remaining_sec(attempt: dict) -> int:
    expires_str = attempt.get("expires_at")
    if not expires_str:
        return 0
    try:
        expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
        delta = (expires - _now()).total_seconds()
        return max(0, int(delta))
    except Exception:  # noqa: BLE001
        return 0


def _practice_aware_time_remaining_sec(attempt: dict, snapshot: dict) -> int | None:
    """Countdown surfaced to the attempt shell.

    The countdown reads the SAME ``expires_at`` deadline that save/submit/auto-submit
    enforce — never a second, display-only clock. The only special case is UNTIMED
    practice: its ``expires_at`` is the long abandonment TTL, which must not read as a
    learner clock, so it surfaces ``None`` (the shell renders ``--`` and never
    auto-submits). Timed practice and real/generated mocks fall through to the shared
    ``expires_at`` remaining.
    """
    if snapshot.get("practice") and int(snapshot.get("duration_sec") or 0) <= 0:
        return None
    return _time_remaining_sec(attempt)


def _serialise_question_for_attempt(q: dict, *, marks_per_correct: float = 1.0, marks_per_wrong: float = 0.25) -> dict:
    """Serialise a question for the attempt GET response.

    PR2: marks come from the frozen question_snapshot (which was written at
    attempt-start with template-level marks), not from the live question row.
    Callers should prefer reading from question_snapshot; this helper is used
    when re-hydrating from the snapshot dict directly.
    """
    return {
        "question_id": q["id"],
        "question_text": q["question_text"],
        "question_type": q["question_type"],
        "marks": float(q.get("marks") or marks_per_correct),
        "negative_marks": float(q.get("negative_marks") or marks_per_wrong),
        "stimuli": q.get("stimuli") or [],
        "section_id": q.get("section_id"),
        "options": [
            {
                "id": o["id"],
                "option_text": o["option_text"],
                "option_index": o["option_index"],
                "source_label": o.get("source_label"),
                "display_order": o.get("display_order"),
            }
            for o in _ordered_options(q)
        ],
    }


def _build_result(
    supabase: Any,
    attempt: dict,
    responses: list[dict] | None = None,
    updates: list[dict] | None = None,
) -> dict:
    if responses is None:
        resp_rows = _safe(
            lambda: supabase.table("mock_attempt_responses")
            .select("*")
            .eq("attempt_id", attempt["id"])
            .execute(),
            default=None,
        )
        responses = getattr(resp_rows, "data", None) or []

    upd_by_id = {u["id"]: u for u in (updates or [])}

    per_question = []
    for r in responses:
        snap = r.get("question_snapshot") or {}
        upd = upd_by_id.get(r["id"], {})
        is_correct = upd.get("is_correct", r.get("is_correct"))
        marks_awarded = upd.get("marks_awarded", r.get("marks_awarded"))
        correct_opt = snap.get("correct_option_id")
        per_question.append({
            "question_id": r["question_id"],
            "question_text": snap.get("question_text"),
            "selected_option_id": r.get("selected_option_id"),
            "correct_option_id": correct_opt,
            "is_correct": is_correct,
            "marks_awarded": marks_awarded,
            "options": snap.get("options") or [],
            "stimuli": snap.get("stimuli") or [],
            "section_id": snap.get("section_id"),
            "explanation": snap.get("explanation"),
            # Per-question client dwell, so the result Time tab can render a real
            # dwell distribution instead of an empty placeholder chart.
            "time_spent_sec": int((r or {}).get("time_spent_sec") or 0),
        })

    summary_rows = _safe(lambda: supabase.table("mock_attempt_summary").select("*").eq("attempt_id", attempt["id"]).limit(1).execute(), default=None)
    summary = (getattr(summary_rows, "data", None) or [None])[0]
    section_rows = _safe(lambda: supabase.table("mock_attempt_section_breakdown").select("*").eq("attempt_id", attempt["id"]).order("section_index").execute(), default=None)
    # score_raw/score_percentage originate as Decimal and are persisted via
    # model_dump(mode="json"), i.e. as JSON strings. Coerce back to a number so
    # the result contract is numeric regardless of which source (summary vs
    # attempt row) supplies the value.
    def _as_number(v):
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return v
        return v

    # Timing analytics (PR #942 item 6). The durable source is the per-response
    # `time_spent_sec` (client dwell, persisted by save_answer); prefer a stored
    # summary total when present. `time_remaining_sec` is derived from the frozen
    # template duration; `avg_time_per_q_sec` is dwell / question count.
    question_count = len(per_question)
    dwell_total = sum(int((r or {}).get("time_spent_sec") or 0) for r in responses)
    summary_time = (summary or {}).get("time_used_sec")
    try:
        time_used_sec = int(summary_time) if summary_time is not None else dwell_total
    except (TypeError, ValueError):
        time_used_sec = dwell_total
    snap = attempt.get("template_snapshot") or {}
    duration_sec = int(snap.get("duration_sec") or 0)
    time_remaining_sec = max(0, duration_sec - time_used_sec) if duration_sec else None
    avg_time_per_q_sec = round(time_used_sec / question_count, 1) if question_count else 0

    return {
        "attempt_id": attempt["id"],
        "status": attempt.get("status"),
        "submitted_at": attempt.get("submitted_at"),
        "score_raw": _as_number((summary or {}).get("score_raw", attempt.get("score_raw"))),
        "score_percentage": _as_number((summary or {}).get("score_percentage", attempt.get("score_percentage"))),
        "total_correct": (summary or {}).get("total_correct", attempt.get("total_correct")),
        "total_wrong": (summary or {}).get("total_wrong", attempt.get("total_wrong")),
        "total_unattempted": (summary or {}).get("total_unattempted", attempt.get("total_unattempted")),
        "time_used_sec": time_used_sec,
        "time_remaining_sec": time_remaining_sec,
        "avg_time_per_q_sec": avg_time_per_q_sec,
        "section_breakdown": getattr(section_rows, "data", None) or [],
        "per_question": per_question,
    }




def get_analytics(supabase: Any, user_id: str, attempt_id: str) -> dict:
    attempt = _fetch_attempt(supabase, user_id, attempt_id)
    if attempt.get("status") != "submitted":
        raise ValueError("attempt not yet submitted")
    topics = _safe(lambda: supabase.table("mock_attempt_topic_breakdown").select("*").eq("attempt_id", attempt_id).execute(), default=None)
    classes = _safe(lambda: supabase.table("mock_attempt_response_classification").select("*").eq("attempt_id", attempt_id).execute(), default=None)
    summary_rows = _safe(lambda: supabase.table("mock_attempt_summary").select("analytics_quality").eq("attempt_id", attempt_id).limit(1).execute(), default=None)
    topic_breakdown = getattr(topics, "data", None) or []
    # Attach a learner-friendly `topic_name` so the result Topic heatmap labels
    # rows with real names instead of raw topic UUIDs. Fail-open: on a read miss
    # the row keeps whatever name is absent and the UI falls back gracefully.
    topic_ids = [t.get("topic_id") for t in topic_breakdown if t.get("topic_id")]
    if topic_ids:
        name_rows = _safe(
            lambda: supabase.table("topics").select("id, name").in_("id", topic_ids).execute(),
            default=None,
        )
        names = {r.get("id"): r.get("name") for r in (getattr(name_rows, "data", None) or [])}
        for t in topic_breakdown:
            t["topic_name"] = names.get(t.get("topic_id"))
    return {
        "attempt_id": attempt_id,
        "topic_breakdown": topic_breakdown,
        "response_classification": getattr(classes, "data", None) or [],
        "analytics_quality": ((getattr(summary_rows, "data", None) or [{}])[0]).get("analytics_quality") or {},
    }


def get_review(supabase: Any, user_id: str, attempt_id: str) -> dict:
    attempt = _fetch_attempt(supabase, user_id, attempt_id)
    if attempt.get("status") != "submitted":
        raise ValueError("attempt not yet submitted")
    resp_rows = _safe(lambda: supabase.table("mock_attempt_responses").select("*").eq("attempt_id", attempt_id).execute(), default=None)
    cls_rows = _safe(lambda: supabase.table("mock_attempt_response_classification").select("question_id,error_type").eq("attempt_id", attempt_id).execute(), default=None)
    cls = {r.get("question_id"): r.get("error_type") for r in (getattr(cls_rows, "data", None) or [])}

    # Response-row order from PostgREST is not guaranteed. Drive the review
    # order — and the immutable 1-based `attempt_order` the UI numbers by — from
    # the attempt order frozen at start in `template_snapshot.question_ids`
    # (the same source `get_attempt` iterates). Any response row missing from
    # the snapshot is appended in row order as a defensive fallback.
    by_qid = {r.get("question_id"): r for r in (getattr(resp_rows, "data", None) or []) if r.get("question_id")}
    snapshot = attempt.get("template_snapshot") or {}
    ordered_ids = [qid for qid in (snapshot.get("question_ids") or []) if qid in by_qid]
    seen = set(ordered_ids)
    for r in (getattr(resp_rows, "data", None) or []):
        qid = r.get("question_id")
        if qid and qid not in seen:
            ordered_ids.append(qid)
            seen.add(qid)

    questions = []
    for i, qid in enumerate(ordered_ids):
        r = by_qid[qid]
        snap = r.get("question_snapshot") or {}
        questions.append({
            "question_id": qid,
            "attempt_order": i + 1,
            "question_snapshot": snap,
            "selected_option_id": r.get("selected_option_id"),
            "is_correct": r.get("is_correct"),
            "error_type": cls.get(qid),
            "explanation": snap.get("explanation"),
            "time_spent_sec": int(r.get("time_spent_sec") or 0),
        })
    return {"attempt_id": attempt_id, "questions": questions}

def _emit_mock_tests_row(
    supabase: Any,
    user_id: str,
    attempt: dict,
    score_raw: float,
    max_score: float,
    total_correct: int,
    total_wrong: int,
    total_q: int,
    submitted_at: str,
) -> None:
    """Write a mock_tests row compatible with the existing Mocks.jsx schema."""
    snap = attempt.get("template_snapshot") or {}
    duration_sec = int(snap.get("duration_sec") or 0)
    duration_mins = round(duration_sec / 60) if duration_sec else None

    try:
        total_marks = _to_integral_marks(max_score)
        supabase.table("mock_tests").insert({
            "user_id": user_id,
            "test_name": snap.get("name") or "Mock",
            "title": snap.get("name") or "Mock",
            "exam_name": snap.get("exam_family") or snap.get("slug") or "",
            "scored_marks": round(score_raw, 2),
            "total_marks": total_marks,
            "duration_mins": duration_mins,
            "correct_answers": total_correct,
            "wrong_answers": total_wrong,
            "questions_attempted": total_correct + total_wrong,
            "review_state": "unreviewed",
            "attempted_at": submitted_at,
            "source_type": "platform_attempt",
            "trust_level": "platform_verified",
            "mock_attempt_id": attempt["id"],
            "analysis_payload": {"mock_attempt_id": attempt["id"]},
        }).execute()
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "mock_tests insert failed attempt=%s, scheduling retry: %s",
            attempt.get("id"), exc,
        )
        schedule_job(supabase, JOB_MOCK_TESTS_RETRY, attempt["id"], last_error=str(exc))


def _retry_emit_mock_tests_row(supabase: Any, attempt_id: str) -> None:
    """Idempotent re-emit of a mock_tests compat row. Called by the sweeper."""
    existing = _safe(
        lambda: supabase.table("mock_tests")
        .select("id")
        .eq("mock_attempt_id", attempt_id)
        .limit(1)
        .execute(),
        default=None,
    )
    if getattr(existing, "data", None):
        return  # already present — idempotent no-op

    attempt = _fetch_attempt_by_id(supabase, attempt_id)
    if attempt is None:
        raise RuntimeError(f"attempt {attempt_id} not found for mock_tests_retry")

    resp_rows = _safe(
        lambda: supabase.table("mock_attempt_responses")
        .select("question_snapshot")
        .eq("attempt_id", attempt_id)
        .execute(),
        default=None,
    )
    responses = getattr(resp_rows, "data", None) or []
    max_score = sum(
        (_to_decimal_marks((r.get("question_snapshot") or {}).get("marks") or 1)
         for r in responses),
        Decimal("0"),
    )

    snap = attempt.get("template_snapshot") or {}
    duration_sec = int(snap.get("duration_sec") or 0)
    duration_mins = round(duration_sec / 60) if duration_sec else None
    score_raw = float(attempt.get("score_raw") or 0)
    total_correct = int(attempt.get("total_correct") or 0)
    total_wrong = int(attempt.get("total_wrong") or 0)
    submitted_at = attempt.get("submitted_at") or _now_iso()

    total_marks = _to_integral_marks(max_score)

    # Propagate exceptions so the sweeper's retry/backoff loop handles them.
    supabase.table("mock_tests").insert({
        "user_id": attempt["user_id"],
        "test_name": snap.get("name") or "Mock",
        "title": snap.get("name") or "Mock",
        "exam_name": snap.get("exam_family") or snap.get("slug") or "",
        "scored_marks": round(score_raw, 2),
        "total_marks": total_marks,
        "duration_mins": duration_mins,
        "correct_answers": total_correct,
        "wrong_answers": total_wrong,
        "questions_attempted": total_correct + total_wrong,
        "review_state": "unreviewed",
        "attempted_at": submitted_at,
        "source_type": "platform_attempt",
        "trust_level": "platform_verified",
        "mock_attempt_id": attempt_id,
        "analysis_payload": {"mock_attempt_id": attempt_id},
    }).execute()


class ConflictError(Exception):
    pass


class AnswerPersistenceError(RuntimeError):
    pass


class SubmissionPersistenceError(RuntimeError):
    """A per-response score write failed during finalization.

    Raised before the attempt is flipped to ``submitted``, so the attempt is
    left ``in_progress`` and the submission is safely re-runnable.
    """


class AttemptFinalizationError(RuntimeError):
    """The attempt status/score finalization write failed.

    Raised before the submitted event and mock_tests compat row are emitted, so
    the attempt is left ``in_progress`` and the submission is safely re-runnable.
    """


class SubmitConsistencyError(RuntimeError):
    pass


# ── consolidated background jobs (PR-fix-3) ─────────────────────────────────────
#
# A single sweeper drains ``mock_attempt_jobs`` and dispatches by ``job_kind``.
# Running two cron loops over the same DB would compete on locks and split
# observability, so auto-submit and derivation retry share one loop. A new job
# kind (e.g. ``mastery_retry``) only needs a branch in ``_run_job``.

JOB_AUTO_SUBMIT = "auto_submit"
JOB_ANALYTICS_RETRY = "analytics_retry"
JOB_MASTERY_RETRY = "mastery_retry"
JOB_MOCK_TESTS_RETRY = "mock_tests_retry"
_JOB_LEASE_SECONDS = 60

_ACTIVE_JOB_STATUSES = ["pending", "running"]


def get_or_resolve_pinned_mastery_flag(sb: Any, attempt_id: str, user_id: str) -> str:
    """Return the single pinned mastery mode for this attempt.

    - If one mastery_retry job exists (non-cancelled/non-permanently-failed) → return its mode
    - If both 'live' and 'shadow' jobs exist → log loudly, return 'shadow' (fail closed)
    - If no mastery job exists → resolve from env + allowlist

    This prevents the race where the global FF or allowlist changes between the
    synchronous submit and a later analytics_retry / correction-recovery run,
    causing the same attempt to accumulate BOTH a live and a shadow mastery job.
    """
    rows = (
        sb.table("mock_attempt_jobs")
        .select("mastery_flag_state")
        .eq("attempt_id", attempt_id)
        .eq("job_kind", JOB_MASTERY_RETRY)
        .not_.in_("status", ["cancelled", "failed_permanent"])
        .execute()
        .data
        or []
    )
    modes = {r["mastery_flag_state"] for r in rows if r.get("mastery_flag_state")}
    if len(modes) == 1:
        return modes.pop()
    if len(modes) > 1:
        logger.error(
            "MASTERY_MODE_CONFLICT: attempt %s has both %s mastery jobs — failing closed to shadow",
            attempt_id,
            modes,
        )
        return "shadow"
    # No existing job — resolve from environment
    from app.study_os.mastery_writer import get_mastery_write_flag, resolve_effective_mastery_flag  # noqa: PLC0415
    return resolve_effective_mastery_flag(get_mastery_write_flag(), user_id)


def _backoff_seconds(attempts: int) -> int:
    return min(2 ** max(attempts, 1), 300)


def schedule_job(
    supabase: Any,
    job_kind: str,
    attempt_id: str,
    *,
    scheduled_for: str | None = None,
    last_error: str | None = None,
) -> None:
    """Enqueue (or reschedule) an active job for an attempt.

    Idempotent against the partial unique index on (job_kind, attempt_id) for
    pending/running rows: if an active job already exists it is reset to pending
    with a fresh schedule rather than duplicated.
    """
    existing = _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .select("id,attempts")
        .eq("job_kind", job_kind)
        .eq("attempt_id", attempt_id)
        .in_("status", _ACTIVE_JOB_STATUSES)
        .limit(1)
        .execute(),
        default=None,
    )
    item = (getattr(existing, "data", None) or [None])[0]
    now_iso = scheduled_for or _now_iso()
    if item:
        patch = {"status": "pending", "scheduled_for": now_iso, "updated_at": _now_iso()}
        if last_error is not None:
            patch["last_error"] = last_error[:500]
        _safe(lambda: supabase.table("mock_attempt_jobs").update(patch).eq("id", item["id"]).execute(), default=None)
    else:
        payload = {
            "job_kind": job_kind,
            "attempt_id": attempt_id,
            "scheduled_for": now_iso,
            "attempts": 0,
            "status": "pending",
            "last_error": last_error[:500] if last_error else None,
        }
        _safe(lambda: supabase.table("mock_attempt_jobs").insert(payload).execute(), default=None)  # safe-write-ok: fire-and-forget job scheduling; sweeper re-enqueues missed auto-submit jobs




def _validate_mastery_retry_flag(flag_state: str | None) -> None:
    if flag_state not in {"shadow", "live"}:
        raise ValueError("mastery retry flag_state must be shadow or live")


def _mastery_lease_until() -> str:
    return (_now() + timedelta(seconds=_JOB_LEASE_SECONDS)).isoformat()


def _mastery_retry_done(supabase: Any, attempt_id: str, flag_state: str) -> bool:
    _validate_mastery_retry_flag(flag_state)
    rows = (
        supabase.table("mock_attempt_jobs")
        .select("id")
        .eq("job_kind", JOB_MASTERY_RETRY)
        .eq("attempt_id", attempt_id)
        .eq("mastery_flag_state", flag_state)
        .eq("status", "done")
        .limit(1)
        .execute()
        .data
        or []
    )
    return bool(rows)


def mastery_retry_done(supabase: Any, attempt_id: str, flag_state: str) -> bool:
    return _mastery_retry_done(supabase, attempt_id, flag_state)


def claim_mastery_retry_required(supabase: Any, attempt_id: str, flag_state: str) -> str | None:
    _validate_mastery_retry_flag(flag_state)
    rows = (
        supabase.rpc(
            "claim_mock_mastery_retry",
            {
                "p_attempt_id": attempt_id,
                "p_flag_state": flag_state,
                "p_lease_until": _mastery_lease_until(),
            },
        )
        .execute()
        .data
        or []
    )
    if not rows:
        return None
    row = rows[0]
    return row.get("id") if row.get("claimed") else None


def enqueue_mastery_retry_required(
    supabase: Any,
    attempt_id: str,
    flag_state: str,
    *,
    last_error: str | None = None,
    scheduled_for: str | None = None,
) -> None:
    _validate_mastery_retry_flag(flag_state)
    rows = (
        supabase.table("mock_attempt_jobs")
        .select("id,attempts,mastery_flag_state")
        .eq("job_kind", JOB_MASTERY_RETRY)
        .eq("attempt_id", attempt_id)
        .eq("mastery_flag_state", flag_state)
        .in_("status", _ACTIVE_JOB_STATUSES)
        .limit(1)
        .execute()
        .data
        or []
    )
    now_iso = scheduled_for or _now_iso()
    if rows:
        patch = {"status": "pending", "scheduled_for": now_iso, "updated_at": _now_iso()}
        if last_error is not None:
            patch["last_error"] = last_error[:500]
        supabase.table("mock_attempt_jobs").update(patch).eq("id", rows[0]["id"]).execute()
        return
    payload = {
        "job_kind": JOB_MASTERY_RETRY,
        "attempt_id": attempt_id,
        "mastery_flag_state": flag_state,
        "scheduled_for": now_iso,
        "attempts": 0,
        "status": "pending",
        "last_error": last_error[:500] if last_error else None,
    }
    supabase.table("mock_attempt_jobs").insert(payload).execute()


def mark_mastery_retry_pending_required(supabase: Any, job_id: str, last_error: str) -> None:
    supabase.table("mock_attempt_jobs").update({
        "status": "pending",
        "scheduled_for": _now_iso(),
        "last_error": last_error[:500],
        "updated_at": _now_iso(),
    }).eq("id", job_id).execute()


def complete_mastery_retry_required(supabase: Any, job_id: str) -> None:
    supabase.rpc("complete_mock_mastery_retry", {"p_job_id": job_id}).execute()


def _complete_job(supabase: Any, job_kind: str, attempt_id: str) -> None:
    """Mark any active job for (job_kind, attempt) done — keeps the row for audit."""
    _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .update({"status": "done", "last_error": None, "updated_at": _now_iso()})
        .eq("job_kind", job_kind)
        .eq("attempt_id", attempt_id)
        .in_("status", _ACTIVE_JOB_STATUSES)
        .execute(),
        default=None,
    )


def _mark_running(supabase: Any, job: dict, now: datetime) -> int:
    """Claim a job: bump attempts (bounds crash loops) and flag it running."""
    attempts = int(job.get("attempts") or 0) + 1
    _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .update({"status": "running", "attempts": attempts, "scheduled_for": (now + timedelta(seconds=_JOB_LEASE_SECONDS)).isoformat(), "updated_at": now.isoformat()})
        .eq("id", job["id"])
        .execute(),
        default=None,
    )
    return attempts


def _reschedule_job(supabase: Any, job: dict, attempts: int, last_error: str, now: datetime) -> None:
    next_at = (now + timedelta(seconds=_backoff_seconds(attempts))).isoformat()
    _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .update({"status": "pending", "scheduled_for": next_at, "last_error": last_error[:500], "updated_at": now.isoformat()})
        .eq("id", job["id"])
        .execute(),
        default=None,
    )


def _fail_job(supabase: Any, job: dict, last_error: str, now: datetime) -> None:
    _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .update({"status": "failed", "last_error": last_error[:500], "updated_at": now.isoformat()})
        .eq("id", job["id"])
        .execute(),
        default=None,
    )


def _run_job(supabase: Any, job: dict) -> None:
    """Dispatch a single job by kind. Raises on failure so the sweeper retries."""
    kind = job.get("job_kind")
    attempt_id = job.get("attempt_id")
    if kind == JOB_AUTO_SUBMIT:
        auto_submit_attempt(supabase, attempt_id)
    elif kind == JOB_ANALYTICS_RETRY:
        attempt_analytics.compute_and_persist(supabase, attempt_id)
        # D4: after analytics succeeds, hand off to mastery if FF is not off.
        # Use get_or_resolve_pinned_mastery_flag so the mode is pinned to any
        # existing mastery_retry job rather than re-resolved from the current env.
        # This prevents a FF or allowlist change between submit and analytics_retry
        # from producing conflicting live+shadow jobs for the same attempt.
        _attempt = _fetch_attempt_by_id(supabase, attempt_id)
        _attempt_user_id = (_attempt or {}).get("user_id", "")
        _analytics_retry_flag = get_or_resolve_pinned_mastery_flag(supabase, attempt_id, _attempt_user_id)
        if _analytics_retry_flag != "off":
            enqueue_mastery_retry_required(supabase, attempt_id, _analytics_retry_flag)
    elif kind == JOB_MOCK_TESTS_RETRY:
        _retry_emit_mock_tests_row(supabase, attempt_id)
        _recover_corrections_after_mock_tests(supabase, attempt_id)
    elif kind == JOB_MASTERY_RETRY:
        from app.study_os.mastery_writer import MasteryWriter

        flag_state = job.get("mastery_flag_state")
        _validate_mastery_retry_flag(flag_state)
        MasteryWriter(supabase, flag_state).process_attempt_sync(attempt_id)
    else:
        raise RuntimeError(f"unknown job_kind {kind!r}")


def _recover_corrections_after_mock_tests(supabase: Any, attempt_id: str) -> None:
    """Recovery hook (decision doc §4b): once the mock_tests compat row is
    (re-)emitted, re-run correction drafting so a transient missing-row miss in
    MasteryWriter is recovered rather than silently lost.

    Failures INTENTIONALLY propagate: this runs inside ``_run_job`` (after
    ``_retry_emit_mock_tests_row``), so an exception here flows up to
    ``run_sweeper``, which reschedules the JOB_MOCK_TESTS_RETRY job with backoff
    and preserves ``last_error``. The job is therefore marked done only after
    BOTH the compat-row recovery AND the correction recovery succeed — a failed
    correction can no longer be swallowed and mismarked as success.

    Serial-retry safe: ``_retry_emit_mock_tests_row`` is idempotent (reuses the
    existing compat row, never recreates it) and ``redraft_corrections`` is
    serial-retry idempotent (best-effort read-before-insert dedup), so retrying
    the whole job inserts the correction exactly once across serial retries. It
    only drafts at FF=live and adds NO new mock_tests creation path.

    Pinned-mode: we call ``get_or_resolve_pinned_mastery_flag`` instead of
    ``get_mastery_write_flag()`` directly.  That function returns the mode from
    any existing non-cancelled mastery_retry job for this attempt; if the
    operator changes the global FF between submission and this recovery path, the
    original per-attempt pinned flag is honoured.  If conflicting modes are
    detected (MASTERY_MODE_CONFLICT), it returns "shadow" (fail closed), so
    no live correction drafts are written.
    """
    from app.study_os.mastery_writer import MasteryWriter  # noqa: PLC0415

    # Use get_or_resolve_pinned_mastery_flag to pin the mode to any existing
    # mastery_retry job rather than re-resolving from the current env. This
    # prevents corrections being silently skipped when the operator flips the
    # global FF back to shadow after a live run. If conflicting modes are
    # detected (MASTERY_MODE_CONFLICT), the function returns "shadow" (fail
    # closed), so we skip live correction drafts rather than risk a double-write.
    _attempt = _fetch_attempt_by_id(supabase, attempt_id)
    _attempt_user_id = (_attempt or {}).get("user_id", "")
    _effective_flag = get_or_resolve_pinned_mastery_flag(supabase, attempt_id, _attempt_user_id)
    MasteryWriter(supabase, _effective_flag).redraft_corrections(attempt_id)


def run_sweeper(
    supabase: Any,
    *,
    now: datetime | None = None,
    batch: int = 50,
    max_attempts: int = 5,
) -> dict:
    """Single background loop for the mock engine.

    Phase A enqueues auto-submit jobs for attempts whose window closed more than
    60s ago. Phase B claims due jobs and dispatches them by kind. A crash between
    claim and completion leaves the job ``running`` with ``scheduled_for`` in the
    past, so the next cycle reclaims it; both job kinds are idempotent, so
    reprocessing is safe and no orphan rows are produced.
    """
    now = now or _now()
    counts = {"enqueued": 0, "auto_submitted": 0, "derivations": 0, "failed": 0, "errors": 0}

    # Phase A — detect expired in-progress attempts, enqueue auto-submit jobs.
    threshold = (now - timedelta(seconds=60)).isoformat()
    expired = _safe(
        lambda: supabase.table("mock_attempts")
        .select("id")
        .eq("status", "in_progress")
        .lt("expires_at", threshold)
        .limit(batch)
        .execute(),
        default=None,
    )
    for row in (getattr(expired, "data", None) or []):
        schedule_job(supabase, JOB_AUTO_SUBMIT, row["id"], scheduled_for=now.isoformat())
        counts["enqueued"] += 1

    # Phase B — claim and run due jobs.
    due = _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .select("*")
        .in_("status", _ACTIVE_JOB_STATUSES)
        .lte("scheduled_for", now.isoformat())
        .order("scheduled_for", desc=False)
        .limit(batch)
        .execute(),
        default=None,
    )
    for job in (getattr(due, "data", None) or []):
        if int(job.get("attempts") or 0) >= max_attempts:
            _fail_job(supabase, job, "max_attempts_exceeded", now)
            counts["failed"] += 1
            continue
        attempts = _mark_running(supabase, job, now)
        kind = job.get("job_kind")
        try:
            _run_job(supabase, job)
            if kind == JOB_MASTERY_RETRY:
                complete_mastery_retry_required(supabase, job["id"])
            else:
                _complete_job(supabase, kind, job.get("attempt_id"))
            if kind == JOB_AUTO_SUBMIT:
                counts["auto_submitted"] += 1
            elif kind == JOB_ANALYTICS_RETRY:
                counts["derivations"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("sweeper job failed kind=%s attempt=%s: %s", kind, job.get("attempt_id"), exc)
            _reschedule_job(supabase, job, attempts, str(exc), now)
            counts["errors"] += 1

    return counts
