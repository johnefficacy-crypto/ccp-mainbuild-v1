"""`list_active_exams` must return the COMPLETE active-exam set.

Regression for the catalogue-search truncation bug: the read was capped at a
single ``.limit(100)`` with no pagination, so any active exam sorting
alphabetically past the 100th row (e.g. UPSC CSE) was silently dropped before
the frontend search box ever saw it. The fix range-paginates the full set.

``CappingSB`` models Supabase's server-side ``db-max-rows`` cap AND honours
``.range()``, so it reproduces the truncation a single unordered/limited read
would suffer and proves the paginated read defeats it.
"""
from __future__ import annotations

from app.exam_intelligence import lookup
from app.exam_intelligence.lookup import list_active_exams
from tests.exam_intelligence._capping_stub import CappingSB


def _exam(i: int, *, is_active: bool = True) -> dict:
    # Zero-padded names give a deterministic alphabetical .order("name").
    return {
        "id": f"e{i:05d}",
        "slug": f"exam-{i:05d}",
        "name": f"Exam {i:05d}",
        "exam_type": "test",
        "default_difficulty_level": None,
        "exam_family_id": None,
        "is_active": is_active,
    }


def _catalogue(n_active: int) -> list[dict]:
    return [_exam(i) for i in range(n_active)]


def test_returns_active_exam_sorting_past_old_100_cap():
    """A known exam sorting alphabetically past position 100 — and past a full
    server page — is present, where the old ``.limit(100)`` would have dropped
    it. The corpus exceeds one page, exercising the pagination loop itself."""
    lookup.invalidate_exam_lookup_cache()
    cap = lookup._PAGE
    rows = _catalogue(cap + 100)  # > one server page → forces a 2nd range() page
    # Target exam whose NAME sorts last (well past the old 100 cap); its slug is
    # what the catalogue search matches "UPSC" against.
    target = _exam(0)
    target.update({"id": "e-upsc", "slug": "upsc-cse", "name": "ZZZ UPSC Civil Services"})
    rows.append(target)
    # An inactive exam must never leak in.
    inactive = _exam(1, is_active=False)
    inactive.update({"id": "e-inactive", "slug": "sandbox-inactive", "name": "AAA Inactive Sandbox"})
    rows.append(inactive)

    sb = CappingSB({"exams": rows}, server_cap=cap)
    out = list_active_exams(sb)

    slugs = {r["slug"] for r in out}
    assert "upsc-cse" in slugs                     # present despite sorting past 100 / past one page
    assert "sandbox-inactive" not in slugs         # is_active=False still excluded
    assert len(out) == cap + 100 + 1               # every active exam, no truncation
    # Deterministic name order preserved end-to-end.
    names = [r["name"] for r in out]
    assert names == sorted(names)


def test_ignores_limit_argument_and_returns_full_set():
    """Callers still pass ``limit`` (endpoint=100/200, evaluator=500) as a
    legacy safety cap; it must no longer truncate — the full set comes back
    regardless of the value passed."""
    cap = lookup._PAGE
    rows = _catalogue(150)  # > any legacy limit the callers pass
    sb = CappingSB({"exams": rows}, server_cap=cap)

    lookup.invalidate_exam_lookup_cache()
    assert len(list_active_exams(sb, limit=100)) == 150
    lookup.invalidate_exam_lookup_cache()
    assert len(list_active_exams(sb, limit=500)) == 150
    lookup.invalidate_exam_lookup_cache()
    assert len(list_active_exams(sb)) == 150


def test_cache_returns_identical_complete_set_and_refetches_full_after_invalidation():
    """Within the TTL window two calls return identical, complete results; after
    invalidation the re-fetch is still the full set, never a stale truncation."""
    cap = lookup._PAGE
    rows = _catalogue(130)
    sb = CappingSB({"exams": rows}, server_cap=cap)

    lookup.invalidate_exam_lookup_cache()
    first = list_active_exams(sb)
    second = list_active_exams(sb)          # served from cache
    assert first == second
    assert len(first) == 130

    lookup.invalidate_exam_lookup_cache()
    third = list_active_exams(sb)           # fresh fetch after invalidation
    assert third == first                   # complete again, not truncated
    assert len(third) == 130

    # A returned list is a copy — mutating it must not corrupt the cache.
    first.clear()
    assert len(list_active_exams(sb)) == 130
