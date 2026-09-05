"""Exam / topic resolvers (defensive).

Reads from ``exams`` are admin-mutable but change rarely. We hold a
10-minute in-process TTL cache so dashboard fan-out doesn't repeat the
same one-row lookup across every request. Admin writers must call
:func:`invalidate_exam_lookup_cache` after they mutate the table.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable

from cachetools import TTLCache

logger = logging.getLogger("career_copilot.exam_intelligence.lookup")


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("exam_intelligence read failed: %s", exc)
        return default


_PAGE = 1000   # rows per pagination page (matches the exam_intelligence package)


def _paginate(build_query: Callable[[int, int], Any]) -> tuple[list[dict[str, Any]], bool]:
    """Fetch every row for *build_query* via deterministic range pagination.

    ``build_query(from_n, to_n)`` returns the rows for the inclusive
    ``[from_n, to_n]`` slice and MUST carry a stable ``.order(...)`` key so the
    server-side row cap (Supabase ``db-max-rows``) can never silently truncate
    the result.

    Returns ``(rows, complete)``. ``complete`` is False when a page read failed
    and the walk stopped early, so the rows are a PREFIX of the real result,
    not the result. Callers still degrade gracefully (same contract as
    ``_safe``) but must not persist an incomplete read — a cached prefix is a
    silently-missing row for the whole cache lifetime, which reads to an
    operator as "the endpoint dropped my exam" with no error anywhere.
    """
    all_rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        rows = _safe(lambda o=offset: build_query(o, o + _PAGE - 1), default=None)
        if rows is None:
            return all_rows, False
        all_rows.extend(rows)
        if len(rows) < _PAGE:
            return all_rows, True
        offset += _PAGE


_EXAM_COLS = (
    "id, slug, name, exam_type, default_difficulty_level, "
    "exam_family_id, is_active"
)

# 10-minute TTL across all three lookup functions. Keys are tagged with
# a short prefix so a single cache holds slug, id, and list lookups.
_EXAM_CACHE: TTLCache = TTLCache(maxsize=512, ttl=600)


def invalidate_exam_lookup_cache() -> None:
    """Drop the in-process exam-lookup cache.

    Call this from admin write paths after an ``exams`` row is created,
    edited, or soft-deleted so the next dashboard read picks up the
    change immediately.
    """
    _EXAM_CACHE.clear()


def resolve_exam_by_slug(supabase: Any, slug: str) -> dict[str, Any] | None:
    if not slug:
        return None
    key = ("slug", slug)
    cached = _EXAM_CACHE.get(key)
    if cached is not None:
        return None if cached == _MISSING else cached
    rows = _safe(
        lambda: (
            supabase.table("exams")
            .select(_EXAM_COLS)
            .eq("slug", slug)
            .limit(1)
            .execute()
            .data
        ),
        default=[],
    ) or []
    value = rows[0] if rows else _MISSING
    _EXAM_CACHE[key] = value
    return None if value is _MISSING else value


def resolve_exam_by_id(supabase: Any, exam_id: str) -> dict[str, Any] | None:
    if not exam_id:
        return None
    key = ("id", exam_id)
    cached = _EXAM_CACHE.get(key)
    if cached is not None:
        return None if cached == _MISSING else cached
    rows = _safe(
        lambda: (
            supabase.table("exams")
            .select(_EXAM_COLS)
            .eq("id", exam_id)
            .limit(1)
            .execute()
            .data
        ),
        default=[],
    ) or []
    value = rows[0] if rows else _MISSING
    _EXAM_CACHE[key] = value
    return None if value is _MISSING else value


def list_active_exams(supabase: Any, limit: int | None = None) -> list[dict[str, Any]]:
    """Return **every** active exam, ordered by name.

    Previously capped at ``limit`` rows via a single ``.limit()`` call with no
    pagination, so any active exam sorting alphabetically past the cap (default
    100) was silently dropped from every caller — including the catalogue
    search, which then could not find real exams like UPSC CSE. The read now
    range-paginates the full set, so the returned list is complete.

    Inclusion rule: ``exams.is_active = true`` is the ONLY gate. Verified
    content is irrelevant — an exam with zero verified papers, zero verified
    questions, and nothing practice-ready is listed if it is active, and an
    exam with a fully published bank is absent if it is not. The
    ``"verified_only": true`` flag on the API response is a router-wide
    contract marker, not a filter on this read.

    Staleness: the result is cached for ``_EXAM_CACHE``'s TTL. An ``is_active``
    correction applied OUT OF BAND (direct SQL in Supabase rather than through
    the CMS write paths, which call :func:`invalidate_exam_lookup_cache`) is
    invisible here until the TTL lapses — per worker process. If a corrected
    exam is still missing, that window is the first thing to rule out.

    ``limit`` is retained only for source compatibility with existing callers
    (they passed it as an arbitrary safety cap, never as a deliberate page
    size) and is **ignored** — the function always returns the complete active
    set. A bounded/paged view, if ever needed, is a separate, deliberate change
    to this contract. Because the result no longer varies by ``limit``, the
    cache key is a single constant.
    """
    key = ("active",)
    cached = _EXAM_CACHE.get(key)
    if cached is not None:
        return list(cached)
    rows, complete = _paginate(
        lambda from_n, to_n: (
            supabase.table("exams")
            .select(_EXAM_COLS)
            .eq("is_active", True)
            .order("name")
            .range(from_n, to_n)
            .execute()
            .data
        )
    )
    # Only a COMPLETE read may be cached. Caching a prefix would pin a
    # catalogue that is missing real exams for the full TTL, and the caller
    # cannot tell that from a genuinely smaller catalogue.
    if complete:
        _EXAM_CACHE[key] = rows
    return list(rows)


_SEPARATORS = re.compile(r"[-_]+")
_WHITESPACE = re.compile(r"\s+")

# Fields the catalogue search indexes. The deployed ``name`` frequently omits
# the acronym learners type ("Civil Services Examination"), while the ``slug``
# carries it (``upsc-cse``); ``exam_type`` gives family-ish matches.
_SEARCH_FIELDS = ("name", "slug", "exam_type")


def _normalize_search_text(value: Any) -> str:
    """Lowercase, flatten ``-``/``_`` to spaces, collapse runs of whitespace."""
    text = _SEPARATORS.sub(" ", str(value or "").lower())
    return _WHITESPACE.sub(" ", text).strip()


def exam_search_haystack(exam: dict[str, Any] | None) -> str:
    """Searchable text for one exam row.

    Mirrors ``examSearchHaystack`` in
    ``app/frontend/src/pages/exam-intelligence/ExamIntelligenceCatalogue.jsx``
    so the server-side ``?q=`` filter and the catalogue's in-page filter agree
    on what matches. Both the separated and the collapsed form are indexed, so
    "upsc cse" and "upsccse" both hit ``upsc-cse``.
    """
    row = exam if isinstance(exam, dict) else {}
    joined = " ".join(
        t for t in (_normalize_search_text(row.get(f)) for f in _SEARCH_FIELDS) if t
    )
    return f"{joined} {joined.replace(' ', '')}"


def exam_matches_query(exam: dict[str, Any] | None, query: str | None) -> bool:
    """Whether *exam* matches the free-text *query*.

    The QUERY is normalized the same way the haystack is, so a learner (or an
    API caller) can paste a slug verbatim — ``?q=upsc-cse`` — and still match a
    haystack that stores it separator-flattened. An empty/whitespace query
    matches everything: "no filter", never "nothing found".
    """
    needle = _normalize_search_text(query)
    if not needle:
        return True
    haystack = exam_search_haystack(exam)
    return needle in haystack or needle.replace(" ", "") in haystack


def filter_exams_by_query(
    exams: list[dict[str, Any]], query: str | None
) -> list[dict[str, Any]]:
    """Filter an exam list by *query*, preserving the caller's ordering."""
    if not _normalize_search_text(query):
        return list(exams)
    return [e for e in exams if exam_matches_query(e, query)]


# Sentinel for negative-cache so a 404 lookup doesn't keep re-hitting
# Supabase within the TTL window. Use a module-private object so it can
# never collide with a real row dict.
_MISSING: dict[str, Any] = {"__missing__": True}
