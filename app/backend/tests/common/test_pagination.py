"""The shared paginated read, proven against a server cap it does not know.

THE BUG THIS REPLACES. Nine modules carried the same loop, and every copy
stopped when a page came back shorter than the page size. That rule is a no-op
whenever the server's ceiling is below the page size: the first request asks
for a thousand rows, the server answers with its cap, and the loop reads its
own short page as the end of the data. One page, no error, wrong answer.

So every test here runs at caps the code does not know about — 5, 19 and 137,
none of them a divisor of the page size or of the row counts — and asserts the
walk returns EVERY row.
"""
from __future__ import annotations

import pytest

from app.common.pagination import PAGE, PageWalk, chunks, paginate

CAPS = [5, 19, 137]


class Server:
    """A PostgREST-shaped read: ordered rows, an inclusive range window, and a
    hard row cap applied last — which is what ``db-max-rows`` does."""

    def __init__(self, rows, *, cap, exact_count=False, fail_on_page=None):
        self.rows = rows
        self.cap = cap
        self.exact_count = exact_count
        self.fail_on_page = fail_on_page
        self.calls = 0
        self.windows = []

    def fetch(self, from_n, to_n):
        self.calls += 1
        self.windows.append((from_n, to_n))
        if self.fail_on_page is not None and self.calls == self.fail_on_page:
            return None
        window = self.rows[from_n : to_n + 1][: self.cap]
        if not self.exact_count:
            return window
        return type("Resp", (), {"data": window, "count": len(self.rows)})()


def _rows(n):
    return [{"id": f"r{i:05d}", "n": i} for i in range(n)]


# ── the fix ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cap", CAPS)
@pytest.mark.parametrize("total", [0, 1, 4, 5, 6, 19, 20, 137, 300, 1000, 1001])
def test_every_row_arrives_whatever_the_server_cap_is(cap, total):
    server = Server(_rows(total), cap=cap)
    walk = paginate(server.fetch)

    assert walk.complete is True
    assert [r["n"] for r in walk.rows] == list(range(total))


@pytest.mark.parametrize("cap", CAPS)
def test_the_old_short_page_rule_would_have_stopped_at_the_cap(cap):
    """The regression, stated as the number it used to return.

    `if len(rows) < PAGE: break` reads the server's capped first page as the
    last page. This is the 1,351-questions-look-like-19 mechanism, and the
    assertion below is what the fixed walk must NOT do."""
    server = Server(_rows(1000), cap=cap)
    first_page = server.fetch(0, PAGE - 1)
    assert len(first_page) == cap < PAGE  # the old rule's break condition

    walk = paginate(Server(_rows(1000), cap=cap).fetch)
    assert len(walk.rows) == 1000
    assert len(walk.rows) != len(first_page)


@pytest.mark.parametrize("cap", CAPS)
def test_the_walk_advances_by_what_came_back_not_by_the_page_size(cap):
    """Advancing by PAGE after a capped page skips everything in between."""
    server = Server(_rows(3 * cap), cap=cap)
    paginate(server.fetch)
    starts = [w[0] for w in server.windows]
    assert starts[:4] == [0, cap, 2 * cap, 3 * cap]


# ── termination ────────────────────────────────────────────────────────────

def test_a_backend_that_ignores_range_terminates_in_one_extra_request():
    """An in-memory double, or a misconfigured proxy, answers every window with
    the same rows. Waiting for an EMPTY page there never returns; stopping when
    a page adds nothing new ends it immediately."""
    class Deaf(Server):
        def fetch(self, from_n, to_n):
            self.calls += 1
            return self.rows[: self.cap]

    server = Deaf(_rows(50), cap=10)
    walk = paginate(server.fetch)

    assert server.calls == 2
    assert len(walk.rows) == 10  # all it could ever see
    assert walk.complete is True


def test_an_empty_first_page_is_one_request_and_no_rows():
    server = Server([], cap=19)
    walk = paginate(server.fetch)
    assert walk.rows == [] and walk.complete is True and server.calls == 1


def test_rows_repeated_across_pages_are_deduplicated_on_id():
    """Range paging without a total order lets a row appear on two pages. Dedup
    hides the repeat; it cannot invent the row that was never returned, which
    is why the caller still has to order on a unique key."""
    rows = _rows(10)
    class Overlapping(Server):
        def fetch(self, from_n, to_n):
            self.calls += 1
            start = max(0, from_n - 2)  # each page re-serves two earlier rows
            return self.rows[start : start + self.cap]

    walk = paginate(Overlapping(rows, cap=4).fetch)
    ids = [r["id"] for r in walk.rows]
    assert len(ids) == len(set(ids)) == 10


def test_the_page_ceiling_is_a_prefix_not_a_hang():
    """A walk that never stops advancing is stopped, and says it is a prefix."""
    class Endless:
        def __init__(self):
            self.calls = 0

        def fetch(self, from_n, to_n):
            self.calls += 1
            return [{"id": f"x{self.calls}"}]

    endless = Endless()
    walk = paginate(endless.fetch, max_pages=7)
    assert endless.calls == 7
    assert walk.complete is False and walk.truncated is True
    assert len(walk.rows) == 7


# ── the two caller contracts ───────────────────────────────────────────────

@pytest.mark.parametrize("cap", CAPS)
def test_a_failed_page_gives_a_prefix_marked_incomplete(cap):
    server = Server(_rows(500), cap=cap, fail_on_page=3)
    walk = paginate(server.fetch)

    assert walk.complete is False
    assert walk.truncated is True
    assert 0 < len(walk.rows) < 500       # a prefix, not the result
    assert len(walk.rows) == 2 * cap      # exactly the two pages that landed


@pytest.mark.parametrize("cap", CAPS)
def test_verified_rows_returns_the_rows_when_the_server_count_agrees(cap):
    server = Server(_rows(400), cap=cap, exact_count=True)
    walk = paginate(server.fetch)

    assert walk.expected == 400
    assert walk.truncated is False
    assert walk.verified_rows() is not None
    assert len(walk.verified_rows()) == 400


@pytest.mark.parametrize("cap", CAPS)
def test_verified_rows_returns_none_on_a_failed_page_rather_than_a_partial(cap):
    """A partial read is more dangerous than a failed one: every caller can
    recognise empty, none can recognise partial."""
    server = Server(_rows(400), cap=cap, exact_count=True, fail_on_page=2)
    walk = paginate(server.fetch)

    assert walk.rows  # rows did arrive...
    assert walk.verified_rows() is None  # ...and are still refused


def test_verified_rows_returns_none_when_the_driver_reports_no_count():
    walk = paginate(Server(_rows(30), cap=19).fetch)
    assert walk.complete is True and walk.expected is None
    assert walk.verified_rows() is None


def test_verified_rows_returns_none_when_fewer_rows_arrive_than_the_count():
    class Lying(Server):
        def fetch(self, from_n, to_n):
            self.calls += 1
            window = self.rows[from_n : to_n + 1][: self.cap]
            return type("Resp", (), {"data": window, "count": 999})()

    walk = paginate(Lying(_rows(30), cap=19).fetch)
    assert len(walk.rows) == 30 and walk.expected == 999
    assert walk.truncated is True
    assert walk.verified_rows() is None


# ── identity ───────────────────────────────────────────────────────────────

def test_a_projection_without_an_id_dedupes_on_the_whole_row():
    """`select("question_fingerprint")` has no key to dedupe on, so the row
    stands for itself. Weaker — identical rows collapse — which is why a read
    whose duplicates are meaningful must select its key."""
    rows = [{"fp": "a"}, {"fp": "b"}, {"fp": "c"}]
    walk = paginate(Server(rows, cap=2).fetch, key="id")
    assert [r["fp"] for r in walk.rows] == ["a", "b", "c"]


def test_a_custom_key_is_honoured():
    rows = [{"topic_id": f"t{i}"} for i in range(40)]
    walk = paginate(Server(rows, cap=7).fetch, key="topic_id")
    assert len(walk.rows) == 40


# ── the IN() chunker ───────────────────────────────────────────────────────

def test_chunks_splits_for_the_url_length_ceiling_not_for_a_row_cap():
    assert chunks(list(range(5)), 2) == [[0, 1], [2, 3], [4]]
    assert chunks([], 250) == []
    assert len(chunks(list(range(1000)))) == 4  # default BATCH = 250


def test_page_walk_is_immutable():
    walk = PageWalk([], complete=True)
    with pytest.raises(Exception):
        walk.complete = False


# ── the cost of stopping on content ────────────────────────────────────────

@pytest.mark.parametrize("cap", CAPS)
def test_an_exact_count_stops_the_walk_without_the_extra_request(cap):
    """Stopping on content costs one request at the end of the data: the walk
    cannot know a page was the last until a further page adds nothing. A query
    carrying `count="exact"` already knows, so it stops on the row it needed."""
    total = 3 * cap
    counted = Server(_rows(total), cap=cap, exact_count=True)
    plain = Server(_rows(total), cap=cap)

    assert paginate(counted.fetch).rows == paginate(plain.fetch).rows
    assert counted.calls == 3
    assert plain.calls == 4  # the same walk, one request longer


def test_a_count_that_never_arrives_still_terminates_on_content():
    """The count is an optimisation, never a termination rule of its own."""
    server = Server(_rows(40), cap=7)
    walk = paginate(server.fetch)
    assert walk.expected is None and walk.complete is True and len(walk.rows) == 40
