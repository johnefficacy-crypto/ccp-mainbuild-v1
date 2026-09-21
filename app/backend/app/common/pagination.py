"""One range-paginated read, for every PostgREST bulk read in the backend.

WHY THIS MODULE EXISTS
----------------------
Nine modules had grown their own copy of this loop, and every copy shared one
rule:

    rows = fetch(offset, offset + _PAGE - 1)
    all_rows.extend(rows)
    if len(rows) < _PAGE:     # <- "that was the last page"
        break

That rule is a no-op whenever the server's ceiling is BELOW ``_PAGE``. The
first request asks for a thousand rows, PostgREST answers with its own
``db-max-rows`` cap, the loop reads a short page as the end of the data and
stops. The read succeeds, reports no error, and returns one page.

It is what made 1,351 questions look like 19 on the answer-writing catalogue:
a subject chip read 19, two papers read 5 each, and the thematic half read "no
themes at all" — every number a plausible-looking slice of a corpus nobody had
finished fetching. Pagination that only terminates correctly when you already
know the server's limit is not pagination.

THE RULE HERE: STOP WHEN A PAGE ADDS NOTHING NEW.
Not when it is short, and not only when it is empty. That ends the walk at the
real end of the data whatever the server's cap is, and it also ends it in one
extra request against a backend that ignores ``range`` and answers every
request with the same rows — an in-memory test double, or a misconfigured
proxy. Waiting for an empty page there never returns.

Rows are deduplicated on ``id`` as a consequence, which is what the caller of a
paginated read wants anyway.

ORDER IS STILL THE CALLER'S JOB. ``fetch(from_n, to_n)`` must build a query
carrying a stable ``.order(...)`` ending on a unique column. Range paging
without a total order is undefined in Postgres: each window is a separate
query, so the server may return rows in a different physical order per page,
and rows repeat across pages while others never appear. Deduplication here
hides the repeats but cannot invent the rows that were never returned.

TWO CONTRACTS, ONE WALK
-----------------------
Callers differ in what they do about an incomplete read, not in how they walk:

* **Graceful** — a failed page degrades to fewer rows on a page nobody
  persists. They read :attr:`PageWalk.rows` and may check
  :attr:`PageWalk.complete`.
* **Fail-closed** — a partial read is worse than no read, because every caller
  can recognise empty and none can recognise partial. They ask the query for
  ``count="exact"`` and use :meth:`PageWalk.verified_rows`, which returns
  ``None`` unless the server's own match count agrees with what arrived.

Both come off the same object, so no module has to re-derive either.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger("career_copilot.common.pagination")

#: Rows requested per page. Asking for more than the server's cap is harmless —
#: the walk terminates on content, not on this number.
PAGE = 1000

#: Hard stop. At PAGE=1000 this is two million rows, far past any real read, so
#: reaching it means the walk is not advancing and something upstream is wrong.
MAX_PAGES = 2_000

#: Max ids per IN() filter, bounded by PostgREST's URL length rather than by
#: any row cap. Every module had its own copy of this number too.
BATCH = 250


def chunks(items: list[Any], size: int = BATCH) -> list[list[Any]]:
    """``items`` split into lists of at most ``size`` — for chunking IN() filters."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def _identity(row: Any, key: str) -> Any:
    """What makes this row the same row on a later page.

    ``id`` when the select carried it. A read that projects a few columns
    without the primary key (``select("question_fingerprint")``) has no id to
    dedupe on, so the whole row stands for itself. That is strictly weaker —
    two genuinely identical rows collapse into one — which is why a read whose
    duplicates are meaningful must select its key.
    """
    if isinstance(row, dict):
        value = row.get(key)
        if value is not None:
            return value
        try:
            return tuple(sorted((str(k), str(v)) for k, v in row.items()))
        except Exception:  # noqa: BLE001 - an unhashable value is still a row
            return repr(row)
    return repr(row)


@dataclass(frozen=True)
class PageWalk:
    """The result of one paginated read.

    ``complete`` is False when a page read failed, which makes ``rows`` a
    PREFIX of the real result rather than the result. ``expected`` is the
    server's exact match count when the query asked for one.
    """

    rows: list[dict[str, Any]]
    complete: bool
    expected: int | None = None
    pages: int = 0

    @property
    def truncated(self) -> bool:
        """The walk stopped without proving it reached the end."""
        return not self.complete or (
            self.expected is not None and len(self.rows) != self.expected
        )

    def verified_rows(
        self, *, table: str | None = None, operation: str | None = None
    ) -> list[dict[str, Any]] | None:
        """``rows`` only if the server's own count agrees; otherwise ``None``.

        For the fail-closed callers. ``None`` covers all three ways a read can
        be short — a page raised, the driver reported no exact count, or fewer
        rows arrived than the server said matched — because a caller that must
        not write on a partial read cannot act on the difference between them.
        """
        if self.complete and self.expected is not None and len(self.rows) == self.expected:
            return self.rows
        logger.error(
            "paginated read is incomplete",
            extra={
                "operation": operation or "read",
                "table": table,
                "rows_collected": len(self.rows),
                "rows_expected": self.expected,
                "pages_read": self.pages,
                "read_failed": not self.complete,
            },
        )
        return None


def _unwrap(page: Any) -> tuple[list[dict[str, Any]], int | None]:
    """(rows, exact count) from either a PostgREST response or a plain list.

    A sequence is checked for FIRST and on its own type. Sniffing for a
    ``count`` attribute instead finds ``list.count``, the built-in method — a
    plain list of rows then reads as a response whose exact count is a bound
    method, and every page raises.
    """
    if page is None:
        return [], None
    if isinstance(page, (list, tuple)):
        return list(page), None
    data = getattr(page, "data", None)
    count = getattr(page, "count", None)
    return list(data or []), count if isinstance(count, (int, float)) else None


def paginate(
    fetch: Callable[[int, int], Any],
    *,
    page_size: int = PAGE,
    max_pages: int = MAX_PAGES,
    key: str = "id",
    table: str | None = None,
    operation: str | None = None,
) -> PageWalk:
    """Walk every row of a range-paginated read.

    ``fetch(from_n, to_n)`` returns the rows for the inclusive ``[from_n,
    to_n]`` window — a plain list, or the PostgREST response itself when the
    caller wants ``count="exact"`` carried through. Returning ``None`` means
    the page read failed: the walk stops and the result is marked incomplete
    rather than raising, so a caller that degrades gracefully still gets what
    arrived. A caller that must NOT degrade uses
    :meth:`PageWalk.verified_rows`.

    Exceptions from ``fetch`` are not caught. A module with its own ``_safe``
    wrapper passes an already-wrapped callable; one without gets the exception
    it would have got before.
    """
    rows: list[dict[str, Any]] = []
    seen: set[Any] = set()
    expected: int | None = None
    offset = 0
    pages = 0

    for _ in range(max_pages):
        page = fetch(offset, offset + page_size - 1)
        if page is None:
            return PageWalk(rows, complete=False, expected=expected, pages=pages)
        pages += 1
        batch, count = _unwrap(page)
        if count is not None:
            expected = int(count)

        added = 0
        for row in batch:
            ident = _identity(row, key)
            if ident in seen:
                continue
            seen.add(ident)
            rows.append(row)
            added += 1

        # The termination rule. NOT `len(batch) < page_size`, which stops on
        # page one whenever the server's cap is below page_size.
        if added == 0:
            return PageWalk(rows, complete=True, expected=expected, pages=pages)

        # Stopping on content costs one extra request at the end of the data:
        # the walk cannot know a page was the last one until a further page
        # adds nothing. A query carrying `count="exact"` HAS that knowledge —
        # the server's own match total — so it stops the moment it has them
        # all. This is an optimisation, never a termination rule of its own: a
        # count the driver never reports simply leaves the extra request.
        if expected is not None and len(rows) >= expected:
            return PageWalk(rows, complete=True, expected=expected, pages=pages)

        offset += len(batch) or page_size

    logger.error(
        "paginated read hit the page ceiling — result is a PREFIX",
        extra={"operation": operation or "read", "table": table,
               "rows_collected": len(rows), "max_pages": max_pages},
    )
    return PageWalk(rows, complete=False, expected=expected, pages=pages)
