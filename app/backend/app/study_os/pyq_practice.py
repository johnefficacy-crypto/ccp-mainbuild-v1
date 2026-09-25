"""PYQ v2 PR-5/6 (slice B) — learner PYQ practice attempt assembly.

Selects VERIFIED, actively-projected PYQ questions from ``mock_question_bank`` by
paper / section / topic and assembles them into an ad-hoc attempt through the
generated-attempt blueprint path (``start_attempt_from_blueprint``, migrations
174/175/178/179). No new attempt schema and no new route: the existing
``/study/mocks/attempts/{id}`` answer / submit / result / review flow serves the
practice attempt unchanged, and PR-5/6 slice A already makes that path render the
projected passage + printed option labels from the frozen snapshot.

Trust / correctness posture:
  * only ``reviewer_status in (verified, published, live)`` bank rows,
  * only rows whose PYQ projection is ``sync_status='active'`` (checked bounded
    to the candidate ids, not the whole table),
  * a practice attempt is single-exam — a set is never assembled across exams
    (topic practice REQUIRES ``exam_id``; any pool that still spans exams is
    rejected),
  * paper / section practice preserves the source PYQ **printed order**
    (``pyq_questions.display_order`` → ``question_number`` → ``source_question_ref``),
  * option/stimulus fidelity is frozen at start via ``_question_snapshot`` and
    the generated loader's fail-closed passage read.
"""
from __future__ import annotations

import logging
import uuid as _uuid
from typing import Any
from datetime import datetime, timedelta, timezone

from app.exam_intelligence.authored_scope import (
    apply_authored_filters,
    authored_rows_for_exam,
)
from app.study_os.generated_mock_attempt import _load_questions
from app.study_os.mock_engine import _question_snapshot
from app.utils.safe import safe_required
from app.common.pagination import paginate

logger = logging.getLogger("career_copilot.study_os.pyq_practice")

_SELECTABLE = ("verified", "published", "live")
# max ids per IN() filter (PostgREST URL-length ceiling) — the repo-wide bound
# (`exam_intelligence._BATCH`, `essay_builder._BATCH`, `reachability._BATCH`,
# `pyq_papers._BATCH`). An unchunked `.in_()` over a whole exam's projected bank
# (1000+ uuids ~ 40 KB of query string) overflows the request; the read then
# fails and every fail-closed caller below reports it as "no availability" —
# which is how `practice_ready_count` read 0 for EVERY paper on a healthy corpus.
_ID_BATCH = 250
# rows per range page (Supabase `db-max-rows` server-side cap). A bare `.limit(n)`
# does not defeat it, so bulk reads paginate instead of trusting one response.
_PAGE = 1000
_ATTEMPT_TTL = timedelta(hours=24)
_DEFAULT_LIMIT = 100
_MAX_LIMIT = 200
# practice is a learning mode — no negative marking.
_MARKS_PER_CORRECT = 1.0
_MARKS_PER_WRONG = 0.0

# mode -> (blueprint source tag, mock_question_bank filter column).
# The topic column is nominal: topic mode does not filter on it directly, because
# the projected level lives in `topic_id` OR `microtopic_id` depending on whether
# the row has been re-synced under migration 270 (see _topic_target_or_filter).
_MODES: dict[str, tuple[str, str]] = {
    "paper": ("pyq_practice_paper", "pyq_paper_id"),
    "section": ("pyq_practice_section", "section_id"),
    "topic": ("pyq_practice_topic", "topic_id"),
}
# modes whose learner experience must follow the source paper's printed order.
_SOURCE_ORDERED_MODES = frozenset({"paper", "section"})


class PracticeInputError(ValueError):
    """Bad practice request — mapped to HTTP 422 by the endpoint."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_uuid(value: str, field: str) -> None:
    try:
        _uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise PracticeInputError(f"{field} must be a valid UUID") from None


def _chunks(items: list, n: int) -> list[list]:
    return [items[i : i + n] for i in range(0, len(items), n)]


def _read_paged(build, *, op: str) -> list[dict] | None:
    """Range-paginate one PostgREST read. ``None`` on read failure — never a
    partial page set, so a caller can distinguish "empty" from "could not read".

    ``build(from_n, to_n)`` must return the query for the inclusive row slice and
    MUST carry a stable ``.order(...)`` so successive pages partition the result.
    """
    walk = paginate(
        lambda a, b: safe_required(
            lambda: build(a, b).execute(), op=op, log=logger, allow_empty=True
        ),
        page_size=_PAGE,
        operation=op,
    )
    return walk.rows if walk.complete else None


def _active_projection_ids(sb, candidate_ids: list[str]) -> frozenset[str]:
    """The subset of ``candidate_ids`` whose PYQ projection is currently active.

    Bounded to the candidate ids (``.in_``) rather than scanning every active
    projection in the table — this is a learner-facing per-click path. Raises on
    read failure (fail-closed): a practice set must never be assembled from a bank
    whose active-projection guard could not be evaluated.

    The id list is chunked at ``_ID_BATCH``. "Bounded to the candidate ids" bounds
    the SCAN, not the URL: the per-click launch path passes ~100 ids, but
    ``practice_ready_counts_by_paper`` / ``practiceable_topic_ids`` pass an entire
    exam's projected bank, which overflows a single request line.
    """
    if not candidate_ids:
        return frozenset()
    found: set[str] = set()
    for chunk in _chunks(list(candidate_ids), _ID_BATCH):
        rows = safe_required(
            lambda c=chunk: sb.table("pyq_mock_question_projections")
            .select("mock_question_id")
            .eq("sync_status", "active")
            .in_("mock_question_id", c)
            .execute(),
            op="pyq_practice.active_projections",
            log=logger,
            allow_empty=True,
        )
        if rows is None:
            # Fail the WHOLE probe on any chunk failure. A partial union would
            # silently under-report availability instead of surfacing the fault.
            raise RuntimeError("pyq_practice: could not read active PYQ projections")
        found.update(r["mock_question_id"] for r in rows)
    return frozenset(found)


def _printed_order_meta(sb, pyq_question_ids: list[str]) -> dict[str, dict]:
    """Source-order metadata per ``pyq_questions.id`` for printed-order sorting.

    PR-4 did not project the question-level printed order into
    ``mock_question_bank`` (only option/section order), so paper/section practice
    joins back to ``pyq_questions`` for ``display_order`` / ``question_number`` /
    ``source_question_ref``. Fail-closed on read error (paper/section practice
    must not silently fall back to arbitrary id order)."""
    if not pyq_question_ids:
        return {}
    meta: dict[str, dict] = {}
    for chunk in _chunks(list(pyq_question_ids), _ID_BATCH):
        rows = safe_required(
            lambda c=chunk: sb.table("pyq_questions")
            .select("id,display_order,question_number,source_question_ref")
            .in_("id", c)
            .execute(),
            op="pyq_practice.printed_order",
            log=logger,
            allow_empty=True,
        )
        if rows is None:
            raise RuntimeError("pyq_practice: could not read source PYQ printed order")
        meta.update({r["id"]: r for r in rows})
    return meta


def _num(v) -> tuple[int, float]:
    """Sort helper: numeric-first, NULLs/non-numeric last, deterministically."""
    if isinstance(v, bool):  # bool is an int subclass — treat as non-numeric
        return (1, 0.0)
    if isinstance(v, (int, float)):
        return (0, float(v))
    try:
        return (0, float(v))
    except (TypeError, ValueError):
        return (1, 0.0)


def _topic_target_or_filter(target_id: str) -> str:
    """PostgREST OR group for a single topic-mode target, level-agnostic.

    ``mock_question_bank`` carries the projected level in TWO shapes that coexist
    indefinitely (migration 270 re-splits a row only when it is re-synced):

      * pre-270  — the primary tag's topic id is flattened into ``topic_id``
                   whatever its level; ``microtopic_id`` is NULL.
      * post-270 — a microtopic tag writes ``microtopic_id`` = the tag and
                   ``topic_id`` = the tag's PARENT; a top-level tag still writes
                   ``topic_id`` = the tag with ``microtopic_id`` NULL.

    So a locked microtopic target matches ``topic_id`` on unsynced rows and
    ``microtopic_id`` on re-synced ones. This group is deliberately a SUPERSET —
    it cannot express "``topic_id`` = target AND ``microtopic_id`` IS NULL"
    without a nested ``and()`` group — and ``_row_matches_topic_target`` narrows
    it in Python, the same filter-then-re-check posture this module already uses
    for ``valid_until``.
    """
    return f"topic_id.eq.{target_id},microtopic_id.eq.{target_id}"


def _row_matches_topic_target(row: dict, target_id: str) -> bool:
    """Exact-level topic match for one bank row, correct under BOTH row shapes.

    A row that carries a ``microtopic_id`` is a post-270 split row: it belongs to
    that microtopic and to no other level, so it matches only when the target IS
    that microtopic. A row without one is self-describing at whatever level its
    ``topic_id`` names (post-270 top-level, or either level pre-270), so it
    matches its own id.

    Level is PRESERVED, not widened: a top-level target keeps matching its own
    rows and does NOT sweep in its children's. That is the pre-270 behaviour —
    `exam_topic_coverage` locks a topic AT one level, `subjects.py` buckets and
    scores mastery per locked id, and the runtime policy launches practice
    against exactly one locked id — so a top-level lock has never served its
    children's questions, and post-270 (where those children's rows now carry
    the parent in ``topic_id``) is where a naive ``topic_id = target`` would
    start silently doing so.
    """
    return _row_level_id(row) == str(target_id)


def _row_level_id(row: dict) -> str | None:
    """The single coverage-lock id a bank row belongs to, under either shape.

    ``microtopic_id`` when the row carries one (post-270 split row), else its
    ``topic_id``. Never both — a row is practised at exactly one level.
    """
    microtopic_id = row.get("microtopic_id")
    if microtopic_id:
        return str(microtopic_id)
    topic_id = row.get("topic_id")
    return str(topic_id) if topic_id else None


# Authored rows (REG-CORPUS-02) join TOPIC mode only: they carry no paper or
# section, so paper/section practice and the per-paper ready counts stay PYQ-only.
# MCQ only — the practice freeze aborts on any row without options/correct option.
_AUTHORED_SELECT = (
    "id,pyq_question_id,pyq_paper_id,section_id,topic_id,microtopic_id,"
    "exam_id,reviewer_status,valid_until,pyq_year,source_kind,metadata"
)


def _authored_bank_query(sb, now_iso: str):
    q = (
        sb.table("mock_question_bank")
        .select(_AUTHORED_SELECT)
        .in_("reviewer_status", list(_SELECTABLE))
        .eq("question_type", "mcq")
    )
    return apply_authored_filters(q).or_(f"valid_until.is.null,valid_until.gt.{now_iso}")


def _authored_unexpired(rows: list[dict], now_iso: str) -> list[dict]:
    return [r for r in rows if not r.get("valid_until") or str(r["valid_until"]) > now_iso]


def _authored_rows_for_targets(
    sb, *, exam_id: str | None, target_ids: list[str], now_iso: str
) -> list[dict]:
    """Authored rows eligible for ``exam_id`` whose practised level is one of
    ``target_ids``. Empty (and no bank read) for an exam with no topic-exam key."""
    ids = [str(t) for t in dict.fromkeys(target_ids) if t]
    if not ids:
        return []

    def _fetch() -> list[dict]:
        found: dict[str, dict] = {}
        # A target sits in `topic_id` or `microtopic_id` (see
        # _topic_target_or_filter); read each column per chunk and union by id.
        for chunk in _chunks(ids, _ID_BATCH):
            for col in ("topic_id", "microtopic_id"):
                rows = safe_required(
                    lambda c=chunk, k=col: _authored_bank_query(sb, now_iso).in_(k, c).execute(),
                    op="pyq_practice.authored_rows",
                    log=logger,
                    allow_empty=True,
                )
                if rows is None:
                    raise RuntimeError("pyq_practice: could not read authored rows")
                found.update({r["id"]: r for r in rows if r.get("id")})
        return list(found.values())

    wanted = set(ids)
    return [
        r
        for r in _authored_unexpired(authored_rows_for_exam(sb, exam_id, _fetch), now_iso)
        if (_row_level_id(r) or "") in wanted
    ]


def _topic_order_key(r: dict) -> tuple:
    """Topic-mode order: PYQ rows first, newest year then id (the pre-authored
    order, unchanged); then authored rows with each case set kept contiguous
    (``metadata.stimulus_group``), then id."""
    if r.get("pyq_question_id"):
        return (0, -(r.get("pyq_year") or 0), "", str(r.get("id")))
    meta = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
    group = meta.get("stimulus_group")
    return (1, 0, str(group) if group else str(r.get("id")), str(r.get("id")))


def select_practice_rows(
    sb, *, mode: str, exam_id: str | None, target_id: str, limit: int
) -> list[dict]:
    """Resolve the projected-PYQ bank rows for a practice request.

    Returns bank rows (not just ids), ordered by the source printed order for
    paper/section modes and newest-year-first for topic mode, capped to ``limit``.
    """
    if mode not in _MODES:
        raise PracticeInputError(f"unknown practice mode: {mode!r}")
    _, filter_col = _MODES[mode]
    now_iso = _now_iso()
    q = (
        sb.table("mock_question_bank")
        .select(
            "id,pyq_question_id,pyq_paper_id,section_id,topic_id,microtopic_id,"
            "exam_id,reviewer_status,valid_until,pyq_year"
        )
        .in_("reviewer_status", list(_SELECTABLE))
    )
    if mode == "topic":
        # Level-aware: match the target against EITHER level column, then narrow
        # to the exact level in Python (see _row_matches_topic_target).
        # `start_pyq_practice` already UUID-validates target_id, but this function
        # is callable on its own and the value is interpolated into a PostgREST
        # filter STRING rather than passed as an encoded parameter — so re-assert
        # it here, where the interpolation happens.
        _require_uuid(target_id, "target_id")
        q = q.or_(_topic_target_or_filter(target_id))
    else:
        q = q.eq(filter_col, target_id)
    q = q.not_.is_("pyq_question_id", "null")
    if exam_id:
        q = q.eq("exam_id", exam_id)
    q = q.or_(f"valid_until.is.null,valid_until.gt.{now_iso}")
    res = safe_required(
        lambda: q.execute(),
        op="pyq_practice.select_rows",
        log=logger,
        allow_empty=True,
    )
    if res is None:
        raise RuntimeError("pyq_practice: could not read the practice question pool")

    candidates = [
        r for r in res
        if r.get("pyq_question_id")
        and (not r.get("valid_until") or str(r["valid_until"]) > now_iso)
        and (mode != "topic" or _row_matches_topic_target(r, target_id))
    ]
    pool: list[dict] = []
    if candidates:
        active = _active_projection_ids(sb, [r["id"] for r in candidates])
        pool = [r for r in candidates if r["id"] in active]

    if mode == "topic":
        # REG-CORPUS-02: multi-exam authored rows join the topic pool when the
        # exam has a topic-exam key and the target topic carries it. An unkeyed
        # exam (every non-regulatory exam) adds nothing and reads no bank rows.
        pool = pool + _authored_rows_for_targets(
            sb, exam_id=exam_id, target_ids=[target_id], now_iso=now_iso
        )
    if not pool:
        return []

    if mode in _SOURCE_ORDERED_MODES:
        meta = _printed_order_meta(sb, [r["pyq_question_id"] for r in pool if r.get("pyq_question_id")])

        def _key(r: dict) -> tuple:
            m = meta.get(r.get("pyq_question_id"), {})
            do = m.get("display_order")
            qn = m.get("question_number")
            sr = m.get("source_question_ref")
            return (
                do is None, _num(do),
                qn is None, _num(qn),
                str(sr) if sr is not None else "",
                str(r.get("id")),
            )
        pool.sort(key=_key)
    else:  # topic: newest PYQ year first, then id; authored rows after PYQ
        pool.sort(key=_topic_order_key)
    return pool[:limit]


def _snapshot_ready(q: dict | None) -> bool:
    """A bank row is launch-ready iff its frozen MCQ snapshot carries options AND
    a ``correct_option_id`` — the SAME predicate ``_build_practice_payload`` aborts
    the whole attempt on. Reusing the real ``_question_snapshot`` builder keeps the
    availability probe from drifting away from the freeze contract."""
    if q is None:
        return False
    snap = _question_snapshot(q, marks_per_correct=_MARKS_PER_CORRECT, marks_per_wrong=_MARKS_PER_WRONG)
    return bool(snap.get("options") and snap.get("correct_option_id"))


def practice_ready_counts_by_paper(
    sb, exam_id: str, *, paper_ids: "list[str] | frozenset[str] | None" = None
) -> dict[str, int]:
    """Per-paper count of practice-launch-ready projected PYQ rows for an exam.

    Mirrors the launch predicate END-TO-END so the learner PYQ summary's
    ``practice_ready_count`` reflects what ``start_pyq_practice`` would actually
    assemble: ``reviewer_status in (verified, published, live)`` + ``pyq_question_id``
    present + unexpired + ``sync_status='active'`` projection **and** the same
    ``_snapshot_ready`` freeze gate the launch aborts on (options + a
    ``correct_option_id`` in the frozen snapshot) — so a paper is never advertised
    ready if it would 500 at freeze.

    ``paper_ids`` constrains the count to a caller-supplied verified paper set, so
    a stale/active projected bank row on a pending/unverified paper cannot inflate
    a verified-only summary. Best-effort: returns ``{}`` on any read failure so the
    learner surface degrades to zero rather than erroring."""
    if not exam_id:
        return {}
    allowed = None if paper_ids is None else frozenset(paper_ids)
    if allowed is not None and not allowed:
        return {}
    now_iso = _now_iso()

    def _bank_page(from_n: int, to_n: int):
        q = (
            sb.table("mock_question_bank")
            .select("id,pyq_paper_id,valid_until")
            .eq("exam_id", exam_id)
            .in_("reviewer_status", list(_SELECTABLE))
            .not_.is_("pyq_question_id", "null")
            .or_(f"valid_until.is.null,valid_until.gt.{now_iso}")
        )
        if allowed is not None:
            q = q.in_("pyq_paper_id", list(allowed))
        # Stable key so successive pages partition the exam's bank deterministically.
        return q.order("id").range(from_n, to_n)

    try:
        # Range-paginated rather than one `.limit(50000)`: a bare limit does not
        # defeat Supabase's `db-max-rows` cap, so a >1000-row exam was silently
        # truncated to an arbitrary page and undercounted.
        res = _read_paged(_bank_page, op="pyq_practice.ready_by_paper")
    except Exception:  # noqa: BLE001 — fail-closed to empty
        logger.warning("practice_ready_counts_by_paper: bank read failed", exc_info=True)
        return {}
    if res is None:
        logger.warning("practice_ready_counts_by_paper: bank read failed (no data)")
        return {}
    candidates = [
        r
        for r in (res or [])
        if r.get("id") and r.get("pyq_paper_id") and (allowed is None or r["pyq_paper_id"] in allowed)
    ]
    if not candidates:
        return {}
    try:
        active = _active_projection_ids(sb, [r["id"] for r in candidates])
    except Exception:  # noqa: BLE001 — unresolved projection guard => no availability
        logger.warning("practice_ready_counts_by_paper: active-projection probe failed", exc_info=True)
        return {}
    active_ids = [r["id"] for r in candidates if r["id"] in active]
    if not active_ids:
        return {}
    # Apply the SAME freeze-readiness gate the launch enforces, so a bad snapshot
    # (missing options / correct_option_id) is not counted as practice-ready.
    try:
        loaded = _load_questions(sb, active_ids)
    except Exception:  # noqa: BLE001 — fail-closed: unresolved freeze => not ready
        logger.warning("practice_ready_counts_by_paper: candidate load failed", exc_info=True)
        return {}
    counts: dict[str, int] = {}
    for qid in active_ids:
        row = loaded.get(qid)
        if row and _snapshot_ready(row):
            pid = row.get("pyq_paper_id")
            if pid and (allowed is None or pid in allowed):
                counts[pid] = counts.get(pid, 0) + 1
    return counts


def practiceable_topic_ids(
    sb, *, exam_id: str | None, topic_ids: list[str], limit: int = _DEFAULT_LIMIT
) -> set[str]:
    """Topic ids (subset of ``topic_ids``) whose topic-mode practice would actually
    START — not just avoid the empty-pool 409, but survive the freeze.

    Batched availability probe for the subjects readiness surface. It mirrors the
    topic-mode selection EXACTLY (verified/published/live + actively-projected +
    unexpired ``mock_question_bank`` rows for ``exam_id``, newest PYQ year first,
    capped at ``limit``) AND then applies the same per-row freeze readiness
    (`_snapshot_ready`) that ``_build_practice_payload`` enforces. A topic is
    returned only when EVERY selected row is snapshot-ready — because the launch
    aborts (500) if any selected row lacks options/``correct_option_id``, a topic
    with a malformed row must not advertise a ``topic_pyq`` mode (it would fail the
    click instead of showing the calm "no verified practice set yet" state).
    Fail-closed: any read/load error yields no availability, never a false positive."""
    ids = [str(t) for t in dict.fromkeys(topic_ids) if t]
    if not ids or not exam_id:
        return set()
    now_iso = _now_iso()
    # Range-paginated for the same reason as `practice_ready_counts_by_paper`:
    # `.limit(50000)` does not defeat the server-side `db-max-rows` cap.
    res = _read_paged(
        lambda f, t: sb.table("mock_question_bank")
        .select("id,topic_id,microtopic_id,valid_until,pyq_year")
        .in_("reviewer_status", list(_SELECTABLE))
        .eq("exam_id", exam_id)
        .not_.is_("pyq_question_id", "null")
        .or_(f"valid_until.is.null,valid_until.gt.{now_iso}")
        .order("id")
        .range(f, t),
        op="pyq_practice.practiceable_topics",
    )
    if res is None:
        return set()
    candidates = [r for r in res if (not r.get("valid_until") or str(r["valid_until"]) > now_iso)]
    active: frozenset[str] = frozenset()
    if candidates:
        try:
            active = _active_projection_ids(sb, [r["id"] for r in candidates])
        except Exception:  # noqa: BLE001 — fail-closed: unresolved projection guard => no availability
            logger.warning("practiceable_topic_ids: active-projection probe failed", exc_info=True)
            return set()
    wanted = set(ids)
    # Narrow to the requested locks HERE rather than in the query. A locked target
    # can sit in `topic_id` or in `microtopic_id` depending on whether its row has
    # been re-synced under migration 270, so a server-side predicate would need
    # both columns listed — and this probe is called with EVERY locked coverage id
    # for the exam (hundreds on UPSC), which would put two id lists of that size
    # into one request URL. The read is already exam-scoped, so the bounded
    # whole-exam read + this filter is the cheaper and more robust shape (the same
    # posture `practice_ready_counts_by_paper` already uses).
    #
    # Level is preserved, not widened: post-270 a child microtopic's row carries
    # its PARENT in topic_id, and a locked parent must not inherit it (see
    # `_row_matches_topic_target`).
    pool = [
        r
        for r in candidates
        if r["id"] in active and (_row_level_id(r) or "") in wanted
    ]
    # REG-CORPUS-02: the same authored rows topic-mode launch would add
    # (select_practice_rows), so readiness never advertises what launch lacks.
    try:
        pool += _authored_rows_for_targets(sb, exam_id=exam_id, target_ids=ids, now_iso=now_iso)
    except Exception:  # noqa: BLE001 — fail-closed: an unreadable authored pool adds nothing
        logger.warning("practiceable_topic_ids: authored pool read failed", exc_info=True)
    if not pool:
        return set()

    # Group by topic, then pick the SAME rows the launch would freeze: newest PYQ
    # year first, then id, capped at `limit` (topic-mode ordering in
    # select_practice_rows). Readiness is judged over exactly that selected slice.
    limit = max(1, min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT))
    by_topic: dict[str, list[dict]] = {}
    for r in pool:
        by_topic.setdefault(str(_row_level_id(r)), []).append(r)
    selected_by_topic: dict[str, list[str]] = {}
    selected_ids: list[str] = []
    for tid, rows in by_topic.items():
        rows.sort(key=_topic_order_key)
        chosen = [str(r["id"]) for r in rows[:limit]]
        selected_by_topic[tid] = chosen
        selected_ids.extend(chosen)

    try:
        questions_by_id = _load_questions(sb, selected_ids)
    except Exception:  # noqa: BLE001 — fail-closed: a load/passage failure => no availability
        logger.warning("practiceable_topic_ids: question load failed", exc_info=True)
        return set()
    ready_ids = {qid for qid in selected_ids if _snapshot_ready(questions_by_id.get(qid))}
    return {
        tid
        for tid, chosen in selected_by_topic.items()
        if chosen and all(qid in ready_ids for qid in chosen)
    }


def _resolve_exam_phase(sb, mode: str, target_id: str, rows: list[dict]) -> str | None:
    """Best-effort exam-phase for the blueprint (nullable on the attempt path)."""
    if mode == "section":
        res = safe_required(
            lambda: sb.table("exam_phase_sections").select("exam_phase_id").eq("id", target_id).limit(1).execute(),
            op="pyq_practice.section_phase",
            log=logger,
            allow_empty=True,
        )
        if res:
            return res[0].get("exam_phase_id")
        return None
    section_ids = sorted({r.get("section_id") for r in rows if r.get("section_id")})
    if not section_ids:
        return None
    res = safe_required(
        lambda: sb.table("exam_phase_sections").select("exam_phase_id").in_("id", section_ids).execute(),
        op="pyq_practice.rows_phase",
        log=logger,
        allow_empty=True,
    )
    phases = {r.get("exam_phase_id") for r in (res or []) if r.get("exam_phase_id")}
    return next(iter(phases)) if len(phases) == 1 else None


def _build_practice_payload(
    ids: list[str],
    questions_by_id: dict[str, dict],
    *,
    exam_id: str | None,
    exam_phase_id: str | None,
    source: str,
    mode: str,
    target_id: str,
    duration_sec: int | None = None,
) -> tuple[dict, list[dict], list[str]]:
    """Freeze the attempt payload. Fail-closed (mirrors generated attempts): every
    selected id must resolve to a usable MCQ snapshot and the frozen set must
    equal the selection exactly — a projected set never persists shrunk."""
    response_rows: list[dict] = []
    ordered_ids: list[str] = []
    missing_ids: list[str] = []
    bad_snapshot_ids: list[str] = []
    for qid in ids:
        q = questions_by_id.get(qid)
        if q is None:
            missing_ids.append(qid)
            continue
        snap = _question_snapshot(q, marks_per_correct=_MARKS_PER_CORRECT, marks_per_wrong=_MARKS_PER_WRONG)
        if not snap.get("options") or not snap.get("correct_option_id"):
            bad_snapshot_ids.append(qid)
        response_rows.append({"question_id": qid, "question_snapshot": snap})
        ordered_ids.append(qid)

    if missing_ids:
        raise RuntimeError(
            f"pyq_practice freeze aborted: {len(missing_ids)} selected question(s) "
            f"failed to load a bank row (e.g. {missing_ids[:5]})"
        )
    if bad_snapshot_ids:
        raise RuntimeError(
            f"pyq_practice freeze aborted: {len(bad_snapshot_ids)} MCQ snapshot(s) "
            f"missing options/correct_option_id (e.g. {bad_snapshot_ids[:5]})"
        )
    if len(response_rows) != len(ids):
        raise RuntimeError(
            f"pyq_practice freeze aborted: frozen response count {len(response_rows)} "
            f"!= selected count {len(ids)}"
        )

    template_snapshot = {
        "source": source,
        "exam_id": exam_id,
        "exam_phase_id": exam_phase_id,
        "generated": True,
        "practice": True,
        "practice_mode": mode,
        "practice_target_id": target_id,
        # shape consumed by mock_engine.get_attempt / scoring (same as start_attempt)
        "question_ids": ordered_ids,
        "sections": [
            {
                "section_index": 0,
                "section_id": None,
                "section_label": "Practice",
                "question_ids": ordered_ids,
                "question_count": len(ordered_ids),
                "marks_per_correct": _MARKS_PER_CORRECT,
                "marks_per_wrong": _MARKS_PER_WRONG,
            }
        ],
        "interface_mode": "simple",
        "allow_switching": True,
        # practice is a learning mode: no negative marking, no section locks.
        "negative_marking": False,
        "marks_per_correct": _MARKS_PER_CORRECT,
        "marks_per_wrong": _MARKS_PER_WRONG,
        "total_questions": len(ordered_ids),
        "section_locks_enabled": False,
    }
    # Timed practice (GQR-R10): a server-owned countdown. mock_engine already honors
    # ``duration_sec`` on the frozen template — it drives attempt expiry and the
    # client-facing ``time_remaining_sec``. Absent/zero → untimed (prior behaviour).
    if duration_sec and duration_sec > 0:
        template_snapshot["duration_sec"] = int(duration_sec)
    return template_snapshot, response_rows, ordered_ids


def start_pyq_practice(
    sb,
    *,
    user_id: str,
    mode: str,
    target_id: str,
    exam_id: str | None = None,
    limit: int = _DEFAULT_LIMIT,
    blueprint_id: str | None = None,
    duration_sec: int | None = None,
    seconds_per_question: int | None = None,
) -> dict:
    """Assemble and atomically start a PYQ practice attempt.

    Returns ``{outcome:'ready', attempt_id, blueprint_id, question_count,
    expires_at, source, exam_id}`` on success, or ``{outcome:'empty_pool'}`` when
    no eligible projected PYQ matches (endpoint → 409, zero writes). Raises
    ``PracticeInputError`` (→ 422) for bad input, or RuntimeError if the atomic
    RPC write fails (rolled back).

    ``blueprint_id``: pass a deterministic id to make the launch **idempotent** —
    ``start_attempt_from_blueprint`` reuses the existing in-progress attempt for a
    reused blueprint id (unique-violation path, migration 179) instead of starting
    a duplicate. Task-bound launchers (PR-9) derive it from the study task id so a
    double-click / retry returns the same attempt; once that attempt is submitted,
    the same id correctly starts a fresh attempt. Omit for a one-shot attempt.
    """
    if mode not in _MODES:
        raise PracticeInputError(f"unknown practice mode: {mode!r}")
    if not target_id:
        raise PracticeInputError("target_id is required")
    _require_uuid(target_id, "target_id")
    if exam_id is not None:
        _require_uuid(exam_id, "exam_id")
    # topic ids are shared across exams — a topic practice set is only well-defined
    # inside one exam, so exam_id is mandatory for topic mode.
    if mode == "topic" and not exam_id:
        raise PracticeInputError("exam_id is required for topic practice")

    source, _ = _MODES[mode]
    limit = max(1, min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT))

    rows = select_practice_rows(sb, mode=mode, exam_id=exam_id, target_id=target_id, limit=limit)
    if not rows:
        return {"outcome": "empty_pool", "question_count": 0}

    # Single-exam invariant: never assemble an attempt spanning exams (would
    # contaminate attempt/analytics/mastery metadata under one recorded exam_id).
    pool_exams = {r.get("exam_id") for r in rows if r.get("exam_id")}
    if len(pool_exams) > 1:
        raise PracticeInputError(
            "practice selection spans multiple exams; pass exam_id to disambiguate"
        )
    resolved_exam_id = exam_id or (next(iter(pool_exams)) if pool_exams else None)

    ids = [r["id"] for r in rows]
    # Timed practice (GQR-R10): derive the server-owned countdown from the ACTUAL
    # frozen count × a per-question rate, so the timer matches the assembled set
    # (the projected pool may be smaller than ``limit``). An explicit ``duration_sec``
    # wins if both are passed.
    if duration_sec is None and seconds_per_question and seconds_per_question > 0:
        duration_sec = int(seconds_per_question) * len(ids)
    exam_phase_id = _resolve_exam_phase(sb, mode, target_id, rows)

    # _load_questions fails closed if the projected passage read fails.
    questions_by_id = _load_questions(sb, ids)
    template_snapshot, response_rows, ordered_ids = _build_practice_payload(
        ids,
        questions_by_id,
        exam_id=resolved_exam_id,
        exam_phase_id=exam_phase_id,
        source=source,
        mode=mode,
        target_id=target_id,
        duration_sec=duration_sec,
    )

    blueprint_for_rpc = {
        "source": source,
        "template_snapshot": template_snapshot,
        "section_snapshot": template_snapshot["sections"],
        "selector_snapshot": {"mode": mode, "target_id": target_id, "exam_id": resolved_exam_id},
        "question_ids": ordered_ids,
        "readiness_snapshot": {"question_count": len(ordered_ids)},
    }
    if blueprint_id:
        # Deterministic id → RPC reuses the in-progress attempt on retry (idempotent).
        blueprint_for_rpc["id"] = blueprint_id
    # ``expires_at`` is the ONE effective attempt deadline, enforced consistently by
    # every runtime path (get_attempt, save_answer, submit, auto-submit/sweeper) via
    # ``_time_remaining_sec``. Timed practice (GQR-R10) makes it the countdown window;
    # untimed practice keeps the long abandonment TTL and hides the clock in the read
    # layer. There is no second, display-only deadline.
    ttl = timedelta(seconds=duration_sec) if duration_sec and duration_sec > 0 else _ATTEMPT_TTL
    expires_at = (datetime.now(timezone.utc) + ttl).isoformat()

    rows_out = safe_required(
        lambda: sb.rpc(
            "start_attempt_from_blueprint",
            {
                "p_user": user_id,
                "p_exam": resolved_exam_id,
                "p_exam_phase": exam_phase_id,
                "p_blueprint": blueprint_for_rpc,
                "p_template_snapshot": template_snapshot,
                "p_response_rows": response_rows,
                "p_expires_at": expires_at,
            },
        ).execute(),
        op="pyq_practice.start_attempt_from_blueprint",
        log=logger,
    )
    if not rows_out:
        raise RuntimeError(
            "pyq_practice: start_attempt_from_blueprint returned no row "
            "(atomic write failed; nothing was persisted)"
        )
    row = rows_out[0]
    return {
        "outcome": "ready",
        "attempt_id": row.get("attempt_id"),
        "blueprint_id": row.get("blueprint_id"),
        "question_count": len(ordered_ids),
        "expires_at": expires_at,
        "source": source,
        "exam_id": resolved_exam_id,
    }


# ── Paper-practice eligibility + empty-pool diagnosis (PRACTICE-PAPER-01) ────
#
# UPSC CSE Mains optional papers are entirely question_type='descriptive'. The
# mock engine is MCQ-only, so descriptive questions are never projected into
# pyq_mock_question_projections and `start_pyq_practice` correctly finds nothing.
# The 409 is right; a generic 409 after the learner has already picked a paper is
# not. These helpers let the picker hide what cannot launch, and let the launcher
# say WHY when something slips through.

# pyq_papers.metadata shapes that are never paper-practiceable, whatever their
# projection state.
#   thematic: the topic-wise half of the optional corpus. question_number is NULL
#             by design and there is no paper structure to practise.
#   retired:  superseded rows (e.g. a bucket that has been split). Kept for
#             lineage, never offered.
PAPER_PRACTICE_EXCLUDED_CODES = ("thematic_not_paper", "retired_paper")


def paper_practice_exclusion(paper_metadata: Any) -> str | None:
    """Return a stable code when a paper is structurally ineligible, else None.

    Structural means "not a practiceable paper at all", independent of how many
    projected questions it happens to have. Checked before any projection read so
    a thematic collection is never counted, listed or launched.
    """
    meta = paper_metadata if isinstance(paper_metadata, dict) else {}
    if meta.get("corpus_half") == "thematic":
        return "thematic_not_paper"
    if meta.get("retired") is True:
        return "retired_paper"
    return None


def is_paper_practiceable(paper_metadata: Any) -> bool:
    """True when the paper is not structurally excluded. Projection readiness is
    a separate question, answered by ``practice_ready_counts_by_paper``."""
    return paper_practice_exclusion(paper_metadata) is None


# Diagnosis codes returned alongside the 409 detail.
EMPTY_POOL_DEFAULT_CODE = "no_projected_questions"
EMPTY_POOL_DEFAULT_DETAIL = (
    "No verified, projected PYQ questions match this practice selection."
)
_EMPTY_POOL_DETAIL = {
    "thematic_not_paper": (
        "This is a topic-wise collection, not a paper. "
        "Paper practice isn't available."
    ),
    "descriptive_paper": (
        "Descriptive paper — answer-writing practice not available yet."
    ),
    "retired_paper": (
        "This paper has been superseded and is no longer offered for practice."
    ),
}


def diagnose_empty_pool(sb, *, mode: str, target_id: str) -> tuple[str, str]:
    """Explain an empty practice pool as ``(code, detail)``.

    Only paper mode can be diagnosed structurally — section and topic targets are
    not papers, so they fall through to the generic answer. Every read here is
    best-effort: a probe failure must not turn a clean 409 into a 500, so any
    exception degrades to the generic code.
    """
    if mode != "paper" or not target_id:
        return EMPTY_POOL_DEFAULT_CODE, EMPTY_POOL_DEFAULT_DETAIL
    try:
        res = (
            sb.table("pyq_papers")
            .select("id,metadata")
            .eq("id", target_id)
            .limit(1)
            .execute()
        )
        rows = getattr(res, "data", None) or []
    except Exception:  # noqa: BLE001 — a diagnosis probe must never escalate
        logger.warning("diagnose_empty_pool: paper read failed", exc_info=True)
        return EMPTY_POOL_DEFAULT_CODE, EMPTY_POOL_DEFAULT_DETAIL
    if not rows:
        return EMPTY_POOL_DEFAULT_CODE, EMPTY_POOL_DEFAULT_DETAIL

    structural = paper_practice_exclusion(rows[0].get("metadata"))
    if structural:
        return structural, _EMPTY_POOL_DETAIL[structural]

    # Not structurally excluded: is every VERIFIED question on it descriptive?
    # Only verified questions matter — the launcher would never select the rest,
    # so a pending MCQ does not make this a mixed paper from the learner's side.
    try:
        res = (
            sb.table("pyq_questions")
            .select("question_type")
            .eq("pyq_paper_id", target_id)
            .eq("reviewer_status", "verified")
            .limit(_PAGE)
            .execute()
        )
        qrows = getattr(res, "data", None) or []
    except Exception:  # noqa: BLE001
        logger.warning("diagnose_empty_pool: question read failed", exc_info=True)
        return EMPTY_POOL_DEFAULT_CODE, EMPTY_POOL_DEFAULT_DETAIL

    types = {(r.get("question_type") or "").strip().lower() for r in qrows if isinstance(r, dict)}
    types.discard("")
    if types and types == {"descriptive"}:
        return "descriptive_paper", _EMPTY_POOL_DETAIL["descriptive_paper"]

    return EMPTY_POOL_DEFAULT_CODE, EMPTY_POOL_DEFAULT_DETAIL
