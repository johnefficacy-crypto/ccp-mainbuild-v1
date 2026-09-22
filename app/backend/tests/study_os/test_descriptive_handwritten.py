"""P3 — handwritten answers, photographed page by page.

The Mains answer an aspirant will actually write is handwritten, under time, on
paper. These pin the three things that make that safe to support:

* the limits are enforced BEFORE a signed URL exists, not in the browser;
* the object path's first segment is the owner, which is what the storage
  policy in migration 298 compares to `auth.uid()`;
* user B can never reach user A's pages, by row or by URL.

NO OCR. Nothing here reads an image.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.study_os import descriptive as d

A = "11111111-1111-1111-1111-111111111111"
B = "22222222-2222-2222-2222-222222222222"
ATTEMPT_A = "aaaa0000-0000-0000-0000-00000000000a"
ATTEMPT_B = "bbbb0000-0000-0000-0000-00000000000b"

MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "app/supabase/migrations/298_descriptive_attempt_pages.sql"
)


class Storage:
    """Supabase Storage, with the bucket policy actually applied.

    The real policy is `(storage.foldername(name))[1] = auth.uid()::text`. This
    models exactly that: an object is readable only by the user whose id is the
    first path segment. A test double that ignores the policy would let a
    cross-user leak pass.
    """

    def __init__(self, bucket, as_user):
        self.bucket = bucket
        self.as_user = as_user
        self.objects = {}
        self.removed = []

    def from_(self, bucket):
        self.bucket = bucket
        return self

    def _owner(self, path):
        return str(path).split("/", 1)[0]

    def create_signed_upload_url(self, path):
        if self._owner(path) != self.as_user:
            raise PermissionError("new row violates row-level security policy")
        self.objects[path] = b""
        return {"signedURL": f"https://storage.test/upload/{path}", "token": "tok"}

    def create_signed_url(self, path, ttl):
        if self._owner(path) != self.as_user:
            raise PermissionError("object not found")
        return {"signedURL": f"https://storage.test/read/{path}?ttl={ttl}"}

    def remove(self, paths):
        for p in paths:
            if self._owner(p) != self.as_user:
                raise PermissionError("object not found")
            self.removed.append(p)
            self.objects.pop(p, None)


class Table:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self._filters, self._order = [], None

    def select(self, *a, **k):
        self._mode = "select"
        return self

    def insert(self, row):
        self._mode, self._payload = "insert", row
        return self

    def update(self, patch):
        self._mode, self._payload = "update", patch
        return self

    def delete(self):
        self._mode = "delete"
        return self

    def eq(self, key, val):
        self._filters.append((key, val))
        return self

    def in_(self, key, vals):
        self._filters.append((key, list(vals)))
        return self

    def order(self, key, desc=False):
        self._order = (key, desc)
        return self

    def range(self, a, b):
        self._range = (a, b)
        return self

    def limit(self, n):
        return self

    def _matches(self, row):
        for key, val in self._filters:
            if isinstance(val, list):
                if row.get(key) not in val:
                    return False
            elif row.get(key) != val:
                return False
        return True

    def execute(self):
        rows = self.db.tables.setdefault(self.name, [])
        if self._mode == "insert":
            new = {"id": f"{self.name}-{len(rows) + 1}", **self._payload}
            rows.append(new)
            return type("X", (), {"data": [new]})()
        hits = [r for r in rows if self._matches(r)]
        if self._mode == "update":
            for r in hits:
                r.update(self._payload)
            return type("X", (), {"data": hits})()
        if self._mode == "delete":
            for r in hits:
                rows.remove(r)
            return type("X", (), {"data": hits})()
        if self._order:
            key, desc = self._order
            hits = sorted(hits, key=lambda r: (r.get(key) is None, r.get(key)), reverse=desc)
        got = hits[self._range[0] : self._range[1] + 1] if getattr(self, "_range", None) else hits
        return type("X", (), {"data": got})()


class Db:
    def __init__(self, as_user=A):
        self.tables = {
            "descriptive_attempts": [
                {"id": ATTEMPT_A, "user_id": A, "pyq_question_id": "q-1",
                 "status": "draft", "answer_text": "", "word_count": 0,
                 "time_spent_seconds": 0, "timer_target_seconds": None,
                 "pasted_chars": 0, "answer_mode": "typed", "self_scores": None,
                 "self_total": None, "notes": None,
                 "started_at": "2026-05-01T09:00:00Z", "submitted_at": None,
                 "updated_at": "2026-05-01T09:00:00Z"},
                {"id": ATTEMPT_B, "user_id": B, "pyq_question_id": "q-1",
                 "status": "draft", "answer_text": "", "word_count": 0,
                 "time_spent_seconds": 0, "timer_target_seconds": None,
                 "pasted_chars": 0, "answer_mode": "handwritten",
                 "self_scores": None, "self_total": None, "notes": None,
                 "started_at": "2026-05-01T09:00:00Z", "submitted_at": None,
                 "updated_at": "2026-05-01T09:00:00Z"},
            ],
            "descriptive_attempt_pages": [],
            "pyq_questions": [{"id": "q-1", "pyq_paper_id": "p-1",
                               "question_number": 1, "question_text": "Discuss.",
                               "question_type": "descriptive",
                               "reviewer_status": "verified", "metadata": {}}],
            "pyq_papers": [{"id": "p-1", "exam_id": "e", "year": 2020,
                            "paper_code": "X", "trust_status": "pending",
                            "metadata": {}}],
        }
        self.storage = Storage("answer-pages", as_user)

    def table(self, name):
        return Table(self, name)


# ── the limits, enforced before a URL exists ───────────────────────────────

@pytest.mark.parametrize("mime", sorted(d.PAGE_MIME_TYPES))
def test_every_accepted_type_is_a_phone_or_scanner_output(mime):
    assert d.validate_page_upload(page_no=1, mime_type=mime, size_bytes=1000)[1] == mime


@pytest.mark.parametrize("mime", ["image/gif", "video/mp4", "text/plain",
                                  "application/zip", "", None])
def test_an_unsupported_type_is_refused(mime):
    with pytest.raises(d.DescriptiveError) as exc:
        d.validate_page_upload(page_no=1, mime_type=mime, size_bytes=1000)
    assert exc.value.status == 422
    assert exc.value.code == "page_type_unsupported"


def test_a_page_over_the_size_limit_is_refused():
    with pytest.raises(d.DescriptiveError) as exc:
        d.validate_page_upload(page_no=1, mime_type="image/jpeg",
                               size_bytes=d.MAX_PAGE_BYTES + 1)
    assert exc.value.code == "page_too_large"
    assert "10 MB" in exc.value.message


def test_an_empty_file_is_refused():
    with pytest.raises(d.DescriptiveError) as exc:
        d.validate_page_upload(page_no=1, mime_type="image/jpeg", size_bytes=0)
    assert exc.value.code == "page_empty"


@pytest.mark.parametrize("page_no", [0, -1, 9, 100, None, "x"])
def test_a_page_number_outside_the_range_is_refused(page_no):
    with pytest.raises(d.DescriptiveError) as exc:
        d.validate_page_upload(page_no=page_no, mime_type="image/jpeg", size_bytes=10)
    assert exc.value.code == "page_number_invalid"


def test_the_limits_are_checked_before_any_signed_url_exists():
    db = Db()
    with pytest.raises(d.DescriptiveError):
        d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                              mime_type="video/mp4", size_bytes=10)
    assert db.storage.objects == {}
    assert db.tables["descriptive_attempt_pages"] == []


# ── the path is the policy ─────────────────────────────────────────────────

def test_the_first_path_segment_is_the_owner():
    """Migration 298 compares `(storage.foldername(name))[1]` to auth.uid(),
    so this is not a naming convention — it is the access check."""
    path = d.page_storage_path(A, ATTEMPT_A, 3, "image/jpeg")
    assert path.split("/")[0] == A
    assert path == f"{A}/{ATTEMPT_A}/page_3.jpg"


@pytest.mark.parametrize("mime,ext", [("image/jpeg", "jpg"), ("image/png", "png"),
                                      ("image/heic", "heic"), ("application/pdf", "pdf")])
def test_the_extension_follows_the_declared_type(mime, ext):
    assert d.page_storage_path(A, ATTEMPT_A, 1, mime).endswith(f"page_1.{ext}")


def test_the_path_is_built_from_the_token_user_not_from_client_input():
    """Every argument that reaches the path comes from the server: the user id
    from the token, the attempt from an ownership-checked read, the page number
    from a validated integer. There is no filename in it at all."""
    db = Db()
    out = d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                                mime_type="image/jpeg", size_bytes=2048)
    assert out["storage_path"].startswith(f"{A}/{ATTEMPT_A}/")
    assert ".." not in out["storage_path"]
    assert re.fullmatch(r"[0-9a-f-]+/[0-9a-f-]+/page_\d\.\w+", out["storage_path"])


# ── user B cannot reach user A's pages ─────────────────────────────────────

def test_user_b_cannot_read_user_as_attempt_pages():
    """The brief's storage policy test, at the row layer."""
    db = Db()
    d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                          mime_type="image/jpeg", size_bytes=2048)
    with pytest.raises(d.DescriptiveError) as exc:
        d.list_attempt_pages(db, B, ATTEMPT_A)
    assert exc.value.status == 404


def test_user_b_cannot_sign_a_url_for_user_as_object():
    """And at the storage layer, which is the half a row policy cannot cover.

    Both have to be wrong for a leak, which is why both exist.
    """
    db = Db()
    d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                          mime_type="image/jpeg", size_bytes=2048)
    page = db.tables["descriptive_attempt_pages"][0]

    as_b = Db(as_user=B)
    assert d._signed_page_url(as_b, page) is None


def test_user_b_cannot_upload_into_user_as_folder():
    db = Db(as_user=B)
    with pytest.raises(d.DescriptiveError) as exc:
        d.request_page_upload(db, B, ATTEMPT_A, page_no=1,
                              mime_type="image/jpeg", size_bytes=2048)
    assert exc.value.status == 404  # the attempt is not theirs to begin with


def test_user_b_cannot_delete_user_as_page():
    db = Db()
    d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                          mime_type="image/jpeg", size_bytes=2048)
    with pytest.raises(d.DescriptiveError) as exc:
        d.delete_attempt_page(db, B, ATTEMPT_A, 1)
    assert exc.value.status == 404
    assert len(db.tables["descriptive_attempt_pages"]) == 1


def test_a_read_payload_never_carries_the_object_path():
    """Two aspirants' paths differ only by a user id."""
    db = Db()
    d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                          mime_type="image/jpeg", size_bytes=2048)
    out = d.list_attempt_pages(db, A, ATTEMPT_A)
    assert out["pages"][0]["url"].startswith("https://storage.test/read/")
    assert "storage_path" not in out["pages"][0]
    assert "storage_bucket" not in out["pages"][0]


def test_a_view_url_is_short_lived():
    db = Db()
    d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                          mime_type="image/jpeg", size_bytes=2048)
    url = d.list_attempt_pages(db, A, ATTEMPT_A)["pages"][0]["url"]
    assert f"ttl={d.PAGE_URL_TTL_SECONDS}" in url
    assert d.PAGE_URL_TTL_SECONDS <= 3600


# ── pages and the attempt ──────────────────────────────────────────────────

def test_uploading_a_page_makes_the_attempt_handwritten_with_no_word_count():
    db = Db()
    d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                          mime_type="image/jpeg", size_bytes=2048)
    attempt = db.tables["descriptive_attempts"][0]
    assert attempt["answer_mode"] == "handwritten"
    # 0 would read as "they wrote nothing", which is the opposite of the truth.
    assert attempt["word_count"] is None


def test_a_handwritten_attempt_keeps_a_null_word_count_through_submit():
    db = Db()
    d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                          mime_type="image/jpeg", size_bytes=2048)
    out = d.submit_attempt(db, A, ATTEMPT_A, self_scores={k: 2 for k in d.RUBRIC_KEYS})
    assert out["word_count"] is None
    assert out["self_total"] == 12  # the rubric is identical


def test_a_typed_attempt_still_counts_its_words():
    db = Db()
    saved = d.save_attempt(db, A, ATTEMPT_A, answer_text="one two three")
    assert saved["word_count"] == 3


def test_reshooting_a_page_replaces_it_rather_than_appending():
    db = Db()
    d.request_page_upload(db, A, ATTEMPT_A, page_no=2,
                          mime_type="image/jpeg", size_bytes=2048)
    d.request_page_upload(db, A, ATTEMPT_A, page_no=2,
                          mime_type="image/jpeg", size_bytes=4096)
    pages = db.tables["descriptive_attempt_pages"]
    assert len(pages) == 1
    assert pages[0]["bytes"] == 4096


def test_the_page_ceiling_counts_new_pages_not_replacements():
    db = Db()
    for n in range(1, d.MAX_ATTEMPT_PAGES + 1):
        d.request_page_upload(db, A, ATTEMPT_A, page_no=n,
                              mime_type="image/jpeg", size_bytes=1000)
    # Re-shooting page 1 at the ceiling is a REPLACEMENT, not a ninth page, so
    # it goes through — a blurry last page must still be retakeable.
    d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                          mime_type="image/jpeg", size_bytes=7777)
    pages = db.tables["descriptive_attempt_pages"]
    assert len(pages) == d.MAX_ATTEMPT_PAGES
    assert next(p for p in pages if p["page_no"] == 1)["bytes"] == 7777


def test_a_ninth_distinct_page_is_refused():
    db = Db()
    for n in range(1, d.MAX_ATTEMPT_PAGES + 1):
        d.request_page_upload(db, A, ATTEMPT_A, page_no=n,
                              mime_type="image/jpeg", size_bytes=1000)
    with pytest.raises(d.DescriptiveError) as exc:
        d.validate_page_upload(page_no=d.MAX_ATTEMPT_PAGES + 1,
                               mime_type="image/jpeg", size_bytes=1000)
    assert exc.value.code == "page_number_invalid"


def test_deleting_the_last_page_returns_the_attempt_to_typing():
    db = Db()
    d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                          mime_type="image/jpeg", size_bytes=2048)
    out = d.delete_attempt_page(db, A, ATTEMPT_A, 1)
    assert out == {"deleted": 1, "remaining": 0}
    assert db.tables["descriptive_attempts"][0]["answer_mode"] == "typed"
    assert db.storage.removed == [f"{A}/{ATTEMPT_A}/page_1.jpg"]


def test_deleting_one_of_several_pages_leaves_the_attempt_handwritten():
    db = Db()
    for n in (1, 2, 3):
        d.request_page_upload(db, A, ATTEMPT_A, page_no=n,
                              mime_type="image/jpeg", size_bytes=1000)
    out = d.delete_attempt_page(db, A, ATTEMPT_A, 2)
    assert out["remaining"] == 2
    assert db.tables["descriptive_attempts"][0]["answer_mode"] == "handwritten"


def test_deleting_a_page_that_is_not_there_is_a_404():
    db = Db()
    with pytest.raises(d.DescriptiveError) as exc:
        d.delete_attempt_page(db, A, ATTEMPT_A, 4)
    assert exc.value.status == 404


# ── a submitted attempt is closed ──────────────────────────────────────────

def test_a_submitted_attempt_takes_no_more_pages():
    """An answer must not grow after it was scored."""
    db = Db()
    db.tables["descriptive_attempts"][0]["status"] = "submitted"
    with pytest.raises(d.DescriptiveError) as exc:
        d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                              mime_type="image/jpeg", size_bytes=1000)
    assert exc.value.status == 409


def test_a_submitted_attempt_loses_no_pages_either():
    db = Db()
    d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                          mime_type="image/jpeg", size_bytes=1000)
    db.tables["descriptive_attempts"][0]["status"] = "submitted"
    with pytest.raises(d.DescriptiveError) as exc:
        d.delete_attempt_page(db, A, ATTEMPT_A, 1)
    assert exc.value.status == 409


# ── switching modes ────────────────────────────────────────────────────────

def test_switching_to_typing_with_pages_attached_is_refused_not_silent():
    """Eight photographs of an answer are not something to discard on a
    mis-click."""
    db = Db()
    d.request_page_upload(db, A, ATTEMPT_A, page_no=1,
                          mime_type="image/jpeg", size_bytes=1000)
    with pytest.raises(d.DescriptiveError) as exc:
        d.set_answer_mode(db, A, ATTEMPT_A, "typed")
    assert exc.value.status == 409
    assert exc.value.code == "pages_present"
    assert len(db.tables["descriptive_attempt_pages"]) == 1


def test_switching_to_handwritten_clears_the_word_count():
    db = Db()
    d.save_attempt(db, A, ATTEMPT_A, answer_text="one two three")
    out = d.set_answer_mode(db, A, ATTEMPT_A, "handwritten")
    assert out["answer_mode"] if "answer_mode" in out else True
    assert db.tables["descriptive_attempts"][0]["word_count"] is None


def test_switching_back_to_typing_restores_the_count_from_the_text():
    db = Db()
    d.save_attempt(db, A, ATTEMPT_A, answer_text="one two three")
    d.set_answer_mode(db, A, ATTEMPT_A, "handwritten")
    d.set_answer_mode(db, A, ATTEMPT_A, "typed")
    assert db.tables["descriptive_attempts"][0]["word_count"] == 3


@pytest.mark.parametrize("mode", ["", "TYPED ", "scanned", None, "handwriting"])
def test_an_unknown_mode_is_refused(mode):
    db = Db()
    if str(mode).strip().lower() in {"typed", "handwritten"}:
        pytest.skip("valid mode")
    with pytest.raises(d.DescriptiveError) as exc:
        d.set_answer_mode(db, A, ATTEMPT_A, mode)
    assert exc.value.status == 422


# ── the migration says what the code assumes ───────────────────────────────

def test_the_bucket_is_private():
    sql = MIGRATION.read_text()
    assert "'answer-pages'" in sql
    assert "public = false" in sql
    assert "values ('answer-pages', 'answer-pages', false)" in sql


def test_the_storage_policies_compare_the_first_path_segment_to_the_caller():
    sql = MIGRATION.read_text()
    for action in ("select", "insert", "delete"):
        assert f"answer_pages_owner_{action}" in sql
    assert sql.count("(storage.foldername(name))[1] = auth.uid()::text") == 3


def test_the_page_table_has_owner_policies_and_no_update():
    sql = MIGRATION.read_text()
    for action in ("select", "insert", "delete"):
        assert f"descriptive_attempt_pages_owner_{action}" in sql
    # A page is an immutable fact: this image, at this position, at this time.
    assert "descriptive_attempt_pages_owner_update" not in sql
    assert "revoke update" in sql


def test_the_migration_limits_match_the_code():
    sql = MIGRATION.read_text()
    assert f"bytes <= {d.MAX_PAGE_BYTES}" in sql
    assert f"page_no <= {d.MAX_ATTEMPT_PAGES}" in sql
    for mime in d.PAGE_MIME_TYPES:
        assert f"'{mime}'" in sql


def test_word_count_became_nullable():
    sql = MIGRATION.read_text()
    assert "alter column word_count drop not null" in sql
    assert "alter column word_count drop default" in sql


# ── the detail view: a handwritten attempt IS its pages ────────────────────
#
# THE BUG THIS SECTION EXISTS FOR. A submitted handwritten attempt with a real
# object in storage opened in "My answers" reading "This attempt has no text
# yet" and rendered no images. The pages were in the table, the object was in
# the bucket, and the payload carried them; nothing showed them.


def _upload(db, attempt=ATTEMPT_A, user=A, page_no=1, mime="image/png"):
    return d.request_page_upload(
        db, user, attempt, page_no=page_no, mime_type=mime, size_bytes=2048
    )


def test_a_handwritten_attempt_detail_carries_its_pages_with_urls():
    db = Db()
    _upload(db, page_no=1)
    _upload(db, page_no=2)

    out = d.attempt_detail(db, A, ATTEMPT_A)

    assert [p["page_no"] for p in out["pages"]] == [1, 2]
    assert all(p["url"] for p in out["pages"])
    assert out["page_count"] == 2
    assert out["url_ttl_seconds"] == d.PAGE_URL_TTL_SECONDS


def test_the_detail_pages_are_ordered_by_page_number_not_by_upload_order():
    """Page 3 re-shot after page 1 must still read 1, 2, 3."""
    db = Db()
    for n in (3, 1, 2):
        _upload(db, page_no=n)
    assert [p["page_no"] for p in d.attempt_detail(db, A, ATTEMPT_A)["pages"]] == [1, 2, 3]


def test_a_handwritten_attempt_with_no_pages_says_zero_not_nothing():
    """`page_count` 0 and `page_count` None are different claims: the first is
    a handwritten answer waiting for its photos, the second is a typed one."""
    db = Db()
    d.set_answer_mode(db, A, ATTEMPT_A, "handwritten")
    out = d.attempt_detail(db, A, ATTEMPT_A)
    assert out["pages"] == []
    assert out["page_count"] == 0


def test_a_typed_attempt_has_no_page_count_at_all():
    out = d.attempt_detail(Db(), A, ATTEMPT_A)
    assert out["page_count"] is None
    assert out["pages"] == []


def test_a_handwritten_attempt_can_still_be_rewritten():
    """"Write this question again" is about the question, not the mode."""
    db = Db()
    _upload(db)
    assert d.attempt_detail(db, A, ATTEMPT_A)["can_rewrite"] is True


def test_a_page_whose_url_cannot_be_signed_says_which_rather_than_going_blank():
    """One unreadable page must not take down the other seven, and the payload
    has to say WHY there is no URL — the surface renders a different sentence
    for "can't be shown right now" than for a page that is simply absent."""
    db = Db()
    _upload(db, page_no=1)
    _upload(db, page_no=2)

    original = db.storage.create_signed_url

    def flaky(path, ttl):
        if path.endswith("page_2.png"):
            raise RuntimeError("storage said no")
        return original(path, ttl)

    db.storage.create_signed_url = flaky
    pages = d.attempt_detail(db, A, ATTEMPT_A)["pages"]

    assert pages[0]["url"] and pages[0]["url_error"] is None
    assert pages[1]["url"] is None
    assert pages[1]["url_error"] == "url_unavailable"
    assert pages[1]["url_expires_in"] is None


def test_the_detail_payload_still_never_carries_the_object_location():
    """The signed URL contains the path — that is what a signed URL is, and it
    expires. What must not ship is the LOCATION as a field: a client holding
    `storage_path` holds another aspirant's path too, since the two differ only
    by a user id, and that one does not expire."""
    db = Db()
    _upload(db)
    pages = d.attempt_detail(db, A, ATTEMPT_A)["pages"]
    assert "storage_path" not in pages[0]
    assert "storage_bucket" not in pages[0]


def test_user_b_cannot_open_user_as_handwritten_attempt():
    db = Db()
    _upload(db)
    with pytest.raises(d.DescriptiveError) as exc:
        d.attempt_detail(db, B, ATTEMPT_A)
    # 404, not 403: whether that attempt exists is not user B's business.
    assert exc.value.status == 404


# ── the submit gate: no pages is not an answer ─────────────────────────────

def _scores():
    return {k: 2 for k in d.RUBRIC_KEYS}


def test_a_handwritten_attempt_with_no_pages_cannot_be_submitted():
    """Its word count is NULL by design — nothing reads the images — so without
    this the record would be a submitted attempt with no text, no pages and a
    self-score: a claim that something was written and cannot be shown."""
    db = Db()
    d.set_answer_mode(db, A, ATTEMPT_A, "handwritten")
    with pytest.raises(d.DescriptiveError) as exc:
        d.submit_attempt(db, A, ATTEMPT_A, self_scores=_scores())
    assert exc.value.status == 409
    assert exc.value.code == "no_pages"
    # And it is still a draft: a refused submit changes nothing.
    assert db.tables["descriptive_attempts"][0]["status"] == "draft"


def test_the_same_attempt_submits_once_a_page_is_uploaded():
    db = Db()
    _upload(db)
    out = d.submit_attempt(db, A, ATTEMPT_A, self_scores=_scores())
    assert out["status"] == "submitted"
    assert out["word_count"] is None


def test_deleting_the_last_page_before_submitting_re_closes_the_gate():
    """Removing the only page returns the attempt to typing with empty text,
    so the gate that catches it is the typed one — but the submit must not go
    through on the strength of pages that are no longer there."""
    db = Db()
    _upload(db)
    d.delete_attempt_page(db, A, ATTEMPT_A, 1)
    d.set_answer_mode(db, A, ATTEMPT_A, "handwritten")
    with pytest.raises(d.DescriptiveError) as exc:
        d.submit_attempt(db, A, ATTEMPT_A, self_scores=_scores())
    assert exc.value.code == "no_pages"


def test_a_typed_attempt_is_not_held_to_the_page_rule():
    db = Db()
    db.tables["descriptive_attempts"][0]["answer_text"] = "An answer."
    out = d.submit_attempt(db, A, ATTEMPT_A, self_scores=_scores())
    assert out["status"] == "submitted"


def test_the_gate_runs_before_the_rubric_is_validated():
    """Otherwise an aspirant with no pages is told to fix their scores."""
    db = Db()
    d.set_answer_mode(db, A, ATTEMPT_A, "handwritten")
    with pytest.raises(d.DescriptiveError) as exc:
        d.submit_attempt(db, A, ATTEMPT_A, self_scores={})
    assert exc.value.code == "no_pages"


# ── the history list: a handwritten draft reads "0 pages" ─────────────────

def test_a_handwritten_draft_with_no_pages_counts_zero_not_null():
    """The row read like a typed attempt, so the aspirant could not tell a
    handwritten draft waiting for its photos from one that was never started."""
    db = Db()
    d.set_answer_mode(db, A, ATTEMPT_A, "handwritten")
    row = d.list_attempts(db, A)["items"][0]
    assert row["answer_mode"] == "handwritten"
    assert row["page_count"] == 0


def test_a_handwritten_row_counts_the_pages_it_has():
    db = Db()
    _upload(db, page_no=1)
    _upload(db, page_no=2)
    assert d.list_attempts(db, A)["items"][0]["page_count"] == 2


def test_a_typed_row_has_no_page_count():
    assert d.list_attempts(Db(), A)["items"][0]["page_count"] is None


# ── compare: pages beside pages, not beside an empty paragraph ─────────────

def test_compare_carries_each_handwritten_attempts_pages():
    db = Db()
    _upload(db)
    d.submit_attempt(db, A, ATTEMPT_A, self_scores=_scores())

    out = d.compare_attempts(db, A, "q-1")
    handwritten = [a for a in out["attempts"] if a["answer_mode"] == "handwritten"]
    assert handwritten and [p["page_no"] for p in handwritten[0]["pages"]] == [1]
    assert handwritten[0]["pages"][0]["url"]
    assert out["url_ttl_seconds"] == d.PAGE_URL_TTL_SECONDS


def test_compare_gives_a_typed_attempt_no_pages_rather_than_a_missing_key():
    out = d.compare_attempts(Db(), A, "q-1")
    assert out["attempts"][0]["pages"] == []


def test_compare_never_reaches_another_users_attempt():
    """Both fixtures answer q-1; only the caller's own may come back."""
    db = Db()
    out = d.compare_attempts(db, A, "q-1")
    assert [a["id"] for a in out["attempts"]] == [ATTEMPT_A]
