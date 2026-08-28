"""Essay Builder API — ownership + verified-only contract.

Covers:
- An aspirant can create / read / update / delete their OWN brainstorm blocks.
- Another aspirant's block is unreachable on every verb: read, patch and
  delete all raise 404 (existence never leaks), and the list is scoped.
- The Idea Canvas additions (new block types + the six lens values) round-trip
  and are validated.
- ``/essay-pyq-tags`` is shared reference data: no ownership scoping, filters
  by theme_id, and enforces verified-only conjunctively across tag, question
  and paper.
"""
from __future__ import annotations

import inspect

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api import essay_builder as eb
from app.core import rate_limit


class Resp:
    def __init__(self, data):
        self.data = data


class Q:
    def __init__(self, store, table):
        self.store = store
        self.table_name = table
        self.filters: dict = {}
        self.in_filters: dict = {}
        self.limit_n: int | None = None
        self.payload: dict | None = None
        self.op = "select"

    def select(self, *a, **k):
        return self

    def eq(self, k, v):
        self.filters[k] = v
        return self

    def in_(self, k, values):
        self.in_filters[k] = list(values)
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def insert(self, payload):
        self.op = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.op = "update"
        self.payload = payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    def _matches(self, row):
        if not all(row.get(k) == v for k, v in self.filters.items()):
            return False
        return all(row.get(k) in vals for k, vals in self.in_filters.items())

    def execute(self):
        rows = self.store.tables.setdefault(self.table_name, [])
        if self.op == "insert":
            row = dict(self.payload)
            self.store.seq += 1
            # Real uuids: the router 404s a non-uuid id before touching the store.
            row.setdefault("id", f"55555555-5555-4555-8555-{self.store.seq:012d}")
            row.setdefault("created_at", "2026-08-28T00:00:00+00:00")
            row.setdefault("updated_at", "2026-08-28T00:00:00+00:00")
            row.setdefault("usage_count", 0)
            row.setdefault("source_note", None)
            row.setdefault("canvas_x", None)
            row.setdefault("canvas_y", None)
            rows.append(row)
            return Resp([row])
        if self.op == "update":
            updated = []
            for r in rows:
                if self._matches(r):
                    r.update(self.payload or {})
                    updated.append(r)
            return Resp(updated)
        if self.op == "delete":
            self.store.tables[self.table_name] = [
                r for r in rows if not self._matches(r)
            ]
            return Resp([])
        out = [r for r in rows if self._matches(r)]
        if self.limit_n is not None:
            out = out[: self.limit_n]
        return Resp(out)


class SB:
    def __init__(self, **seed):
        self.seq = 0
        self.tables: dict[str, list[dict]] = {"essay_brainstorm_blocks": []}
        for k, v in seed.items():
            self.tables[k] = v

    def table(self, name):
        return Q(self, name)


THEME_A = "11111111-1111-4111-8111-111111111111"
THEME_B = "22222222-2222-4222-8222-222222222222"
TOPIC_A = "33333333-3333-4333-8333-333333333333"
BLOCK_A = "44444444-4444-4444-8444-444444444444"


def _user(uid="user-a"):
    return {"id": uid, "is_anonymous": False}


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    rate_limit.reset()
    rate_limit.configure("essay_blocks.write", per_minute=1000, burst=1000)
    yield
    rate_limit.reset()


@pytest.fixture
def sb(monkeypatch):
    fake = SB(
        essay_themes=[{"id": THEME_A}, {"id": THEME_B}],
        topics=[{"id": TOPIC_A}],
        essay_brainstorm_blocks=[
            {
                "id": BLOCK_A,
                "theme_id": THEME_A,
                "block_type": "quote",
                "block_text": "A's private sticky",
                "lens": "economic_efficiency",
                "linked_gs_topic_id": None,
                "canvas_x": None,
                "canvas_y": None,
                "source_note": None,
                "usage_count": 0,
                "created_by": "user-a",
                "created_at": "2026-08-20T00:00:00+00:00",
                "updated_at": "2026-08-20T00:00:00+00:00",
            }
        ],
    )
    monkeypatch.setattr(eb, "get_supabase_admin", lambda: fake)
    return fake


# ── owner CRUD ─────────────────────────────────────────────────────────────


def test_owner_create_read_update_delete_round_trip(sb):
    created = eb.create_block(
        eb.BlockCreate(
            theme_id=THEME_A,
            block_type="vocab_term",
            block_text="Leakage — loss of subsidy value to intermediaries",
            lens="governance_implementation",
        ),
        user=_user("user-a"),
    )
    block_id = created["id"]
    assert created["block_type"] == "vocab_term"
    assert created["lens"] == "governance_implementation"

    fetched = eb.get_block(block_id, user=_user("user-a"))
    assert fetched["block_text"].startswith("Leakage")

    listed = eb.list_blocks(
        theme_id=None, lens=None, block_type=None, limit=200, user=_user("user-a")
    )
    assert block_id in [i["id"] for i in listed["items"]]

    patched = eb.update_block(
        block_id, eb.BlockPatch(block_text="Leakage — edited"), user=_user("user-a")
    )
    assert patched["block_text"] == "Leakage — edited"

    assert eb.delete_block(block_id, user=_user("user-a"))["ok"] is True
    with pytest.raises(HTTPException) as exc:
        eb.get_block(block_id, user=_user("user-a"))
    assert exc.value.status_code == 404


def test_patch_can_clear_lens_without_touching_other_fields(sb):
    out = eb.update_block(BLOCK_A, eb.BlockPatch(lens=None), user=_user("user-a"))
    assert out["lens"] is None
    assert out["block_text"] == "A's private sticky"


def test_patch_explicit_null_on_not_null_column_rejected(sb):
    for column in ("block_type", "block_text"):
        with pytest.raises(HTTPException) as exc:
            eb.update_block(
                BLOCK_A, eb.BlockPatch(**{column: None}), user=_user("user-a")
            )
        assert exc.value.status_code == 422


def test_empty_patch_rejected(sb):
    with pytest.raises(HTTPException) as exc:
        eb.update_block(BLOCK_A, eb.BlockPatch(), user=_user("user-a"))
    assert exc.value.status_code == 422


# ── cross-user isolation ───────────────────────────────────────────────────


def test_cross_user_read_by_id_fails_not_empty(sb):
    with pytest.raises(HTTPException) as exc:
        eb.get_block(BLOCK_A, user=_user("user-b"))
    assert exc.value.status_code == 404


def test_cross_user_list_is_scoped(sb):
    out = eb.list_blocks(
        theme_id=None, lens=None, block_type=None, limit=200, user=_user("user-b")
    )
    assert out["items"] == []


def test_cross_user_update_blocked(sb):
    with pytest.raises(HTTPException) as exc:
        eb.update_block(BLOCK_A, eb.BlockPatch(block_text="hacked"), user=_user("user-b"))
    assert exc.value.status_code == 404
    assert sb.tables["essay_brainstorm_blocks"][0]["block_text"] == "A's private sticky"


def test_cross_user_delete_blocked(sb):
    with pytest.raises(HTTPException) as exc:
        eb.delete_block(BLOCK_A, user=_user("user-b"))
    assert exc.value.status_code == 404
    assert len(sb.tables["essay_brainstorm_blocks"]) == 1


# ── validation ─────────────────────────────────────────────────────────────


def test_unknown_theme_rejected(sb):
    with pytest.raises(HTTPException) as exc:
        eb.create_block(
            eb.BlockCreate(
                theme_id="99999999-9999-4999-8999-999999999999",
                block_type="hook",
                block_text="x",
            ),
            user=_user("user-a"),
        )
    assert exc.value.status_code == 422


def test_unknown_linked_topic_rejected(sb):
    with pytest.raises(HTTPException) as exc:
        eb.create_block(
            eb.BlockCreate(
                theme_id=THEME_A,
                block_type="example",
                block_text="PAHAL (DBTL)",
                linked_gs_topic_id="88888888-8888-4888-8888-888888888888",
            ),
            user=_user("user-a"),
        )
    assert exc.value.status_code == 422


def test_new_idea_canvas_block_types_and_all_six_lenses_accepted(sb):
    for block_type in ("vocab_term", "book_reference", "stat_to_verify"):
        for lens in eb.LENSES:
            out = eb.create_block(
                eb.BlockCreate(
                    theme_id=THEME_A,
                    block_type=block_type,
                    block_text=f"{block_type}/{lens}",
                    lens=lens,
                ),
                user=_user("user-a"),
            )
            assert out["block_type"] == block_type
            assert out["lens"] == lens


def test_spine_block_types_take_no_lens(sb):
    out = eb.create_block(
        eb.BlockCreate(theme_id=THEME_A, block_type="thesis", block_text="Cash > kind"),
        user=_user("user-a"),
    )
    assert out["lens"] is None


def test_unknown_block_type_and_lens_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        eb.BlockCreate(theme_id=THEME_A, block_type="body", block_text="x")
    with pytest.raises(ValidationError):
        eb.BlockCreate(
            theme_id=THEME_A, block_type="hook", block_text="x", lens="econ"
        )


def test_list_rejects_unknown_filter_values(sb):
    with pytest.raises(HTTPException) as exc:
        eb.list_blocks(
            theme_id=None, lens="econ", block_type=None, limit=200, user=_user("user-a")
        )
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException) as exc:
        eb.list_blocks(
            theme_id=None, lens=None, block_type="body", limit=200, user=_user("user-a")
        )
    assert exc.value.status_code == 422


def test_list_filters_combine(sb):
    eb.create_block(
        eb.BlockCreate(
            theme_id=THEME_B,
            block_type="stat_to_verify",
            block_text="[VERIFY] PM-KISAN beneficiary count",
            lens="social_equity_access",
        ),
        user=_user("user-a"),
    )
    out = eb.list_blocks(
        theme_id=THEME_B,
        lens="social_equity_access",
        block_type="stat_to_verify",
        limit=200,
        user=_user("user-a"),
    )
    assert len(out["items"]) == 1
    out_other_theme = eb.list_blocks(
        theme_id=THEME_A,
        lens="social_equity_access",
        block_type="stat_to_verify",
        limit=200,
        user=_user("user-a"),
    )
    assert out_other_theme["items"] == []


# ── canvas position (migration 267) ──────────────────────────────────


def test_create_with_position_round_trips_on_read(sb):
    created = eb.create_block(
        eb.BlockCreate(
            theme_id=THEME_A,
            block_type="example",
            block_text="PAHAL (DBTL)",
            lens="historical_precedent",
            canvas_x=190.5,
            canvas_y=250.25,
        ),
        user=_user("user-a"),
    )
    assert (created["canvas_x"], created["canvas_y"]) == (190.5, 250.25)

    fetched = eb.get_block(created["id"], user=_user("user-a"))
    assert (fetched["canvas_x"], fetched["canvas_y"]) == (190.5, 250.25)

    listed = eb.list_blocks(
        theme_id=THEME_A, lens=None, block_type=None, limit=200, user=_user("user-a")
    )
    row = next(i for i in listed["items"] if i["id"] == created["id"])
    assert (row["canvas_x"], row["canvas_y"]) == (190.5, 250.25)


def test_create_without_position_stays_valid_and_unplaced(sb):
    created = eb.create_block(
        eb.BlockCreate(theme_id=THEME_A, block_type="thesis", block_text="Cash > kind"),
        user=_user("user-a"),
    )
    assert created["canvas_x"] is None
    assert created["canvas_y"] is None
    # Unplaced is a permanent valid state, not a transient one later reads reject.
    assert eb.get_block(created["id"], user=_user("user-a"))["canvas_x"] is None


def test_create_with_negative_and_subpixel_coordinates(sb):
    # Nothing clamps a drag in the mockup, so a sticky can end up at a negative
    # coordinate, and clientX deltas make it sub-pixel.
    created = eb.create_block(
        eb.BlockCreate(
            theme_id=THEME_A,
            block_type="quote",
            block_text="dragged off the left edge",
            canvas_x=-42.75,
            canvas_y=0.5,
        ),
        user=_user("user-a"),
    )
    assert (created["canvas_x"], created["canvas_y"]) == (-42.75, 0.5)


def test_create_with_only_one_axis_rejected(sb):
    for kwargs in ({"canvas_x": 10.0}, {"canvas_y": 10.0}):
        with pytest.raises(HTTPException) as exc:
            eb.create_block(
                eb.BlockCreate(
                    theme_id=THEME_A, block_type="hook", block_text="x", **kwargs
                ),
                user=_user("user-a"),
            )
        assert exc.value.status_code == 422


def test_patch_moves_both_axes_together(sb):
    out = eb.update_block(
        BLOCK_A, eb.BlockPatch(canvas_x=470.0, canvas_y=130.0), user=_user("user-a")
    )
    assert (out["canvas_x"], out["canvas_y"]) == (470.0, 130.0)
    # A drag must not disturb the rest of the block.
    assert out["block_text"] == "A's private sticky"
    assert out["lens"] == "economic_efficiency"


def test_patch_single_axis_rejected(sb):
    for patch in (eb.BlockPatch(canvas_x=1.0), eb.BlockPatch(canvas_y=1.0)):
        with pytest.raises(HTTPException) as exc:
            eb.update_block(BLOCK_A, patch, user=_user("user-a"))
        assert exc.value.status_code == 422
    stored = sb.tables["essay_brainstorm_blocks"][0]
    assert stored["canvas_x"] is None and stored["canvas_y"] is None


def test_patch_mixed_null_and_value_rejected(sb):
    with pytest.raises(HTTPException) as exc:
        eb.update_block(
            BLOCK_A, eb.BlockPatch(canvas_x=5.0, canvas_y=None), user=_user("user-a")
        )
    assert exc.value.status_code == 422


def test_patch_explicit_null_clears_position(sb):
    placed = eb.update_block(
        BLOCK_A, eb.BlockPatch(canvas_x=470.0, canvas_y=130.0), user=_user("user-a")
    )
    assert placed["canvas_x"] == 470.0
    cleared = eb.update_block(
        BLOCK_A, eb.BlockPatch(canvas_x=None, canvas_y=None), user=_user("user-a")
    )
    assert cleared["canvas_x"] is None
    assert cleared["canvas_y"] is None
    # Same explicit-null-clears semantic lens already had; rest untouched.
    assert cleared["block_text"] == "A's private sticky"
    assert cleared["lens"] == "economic_efficiency"


def test_patch_omitting_position_leaves_it_alone(sb):
    eb.update_block(
        BLOCK_A, eb.BlockPatch(canvas_x=12.0, canvas_y=34.0), user=_user("user-a")
    )
    out = eb.update_block(
        BLOCK_A, eb.BlockPatch(block_text="edited"), user=_user("user-a")
    )
    assert out["block_text"] == "edited"
    assert (out["canvas_x"], out["canvas_y"]) == (12.0, 34.0)


def test_non_finite_and_out_of_column_range_coordinates_rejected(sb):
    for x, y in (
        (float("nan"), 1.0),
        (float("inf"), 1.0),
        (1.0, float("-inf")),
        (1e9, 1.0),  # beyond numeric(10,2)
        (1.0, -1e9),
    ):
        with pytest.raises(HTTPException) as exc:
            eb.create_block(
                eb.BlockCreate(
                    theme_id=THEME_A,
                    block_type="hook",
                    block_text="x",
                    canvas_x=x,
                    canvas_y=y,
                ),
                user=_user("user-a"),
            )
        assert exc.value.status_code == 422


def test_coord_coerces_postgrest_numeric_string(sb):
    # PostgREST can hand a numeric back as a string; that wire representation
    # must not leak into the API response.
    sb.tables["essay_brainstorm_blocks"][0]["canvas_x"] = "470.00"
    sb.tables["essay_brainstorm_blocks"][0]["canvas_y"] = "130.00"
    out = eb.get_block(BLOCK_A, user=_user("user-a"))
    assert out["canvas_x"] == 470.0
    assert out["canvas_y"] == 130.0


def test_cross_user_cannot_move_another_aspirants_block(sb):
    with pytest.raises(HTTPException) as exc:
        eb.update_block(
            BLOCK_A, eb.BlockPatch(canvas_x=1.0, canvas_y=2.0), user=_user("user-b")
        )
    assert exc.value.status_code == 404
    stored = sb.tables["essay_brainstorm_blocks"][0]
    assert stored["canvas_x"] is None and stored["canvas_y"] is None


# ── shared essay PYQ tags ──────────────────────────────────────────────────


@pytest.fixture
def tags_sb(monkeypatch):
    fake = SB(
        essay_pyq_tags=[
            {
                "id": "tag-1", "question_id": "q-1", "theme_id": THEME_A,
                "secondary_theme_id": None, "essay_type": "issue_concrete",
                "quote_source_type": None, "reviewer_status": "verified",
                "created_at": "2026-08-01T00:00:00+00:00",
            },
            {
                "id": "tag-2", "question_id": "q-2", "theme_id": THEME_B,
                "secondary_theme_id": None, "essay_type": "quote_abstract",
                "quote_source_type": "indian_thinker", "reviewer_status": "verified",
                "created_at": "2026-08-02T00:00:00+00:00",
            },
            {
                "id": "tag-pending", "question_id": "q-1", "theme_id": THEME_A,
                "secondary_theme_id": None, "essay_type": "issue_concrete",
                "quote_source_type": None, "reviewer_status": "pending",
                "created_at": "2026-08-03T00:00:00+00:00",
            },
            {
                "id": "tag-unverified-question", "question_id": "q-3",
                "theme_id": THEME_A, "secondary_theme_id": None,
                "essay_type": "issue_concrete", "quote_source_type": None,
                "reviewer_status": "verified",
                "created_at": "2026-08-04T00:00:00+00:00",
            },
            {
                "id": "tag-untrusted-paper", "question_id": "q-4",
                "theme_id": THEME_A, "secondary_theme_id": None,
                "essay_type": "issue_concrete", "quote_source_type": None,
                "reviewer_status": "verified",
                "created_at": "2026-08-05T00:00:00+00:00",
            },
        ],
        pyq_questions=[
            {"id": "q-1", "question_text": "Cash transfer vs product subsidy",
             "question_number": 1, "pyq_paper_id": "p-1", "reviewer_status": "verified"},
            {"id": "q-2", "question_text": "Poverty is the worst form of violence",
             "question_number": 2, "pyq_paper_id": "p-1", "reviewer_status": "verified"},
            {"id": "q-3", "question_text": "unreviewed question",
             "question_number": 3, "pyq_paper_id": "p-1", "reviewer_status": "pending"},
            {"id": "q-4", "question_text": "verified q on an untrusted paper",
             "question_number": 4, "pyq_paper_id": "p-2", "reviewer_status": "verified"},
        ],
        pyq_papers=[
            {"id": "p-1", "year": 2024, "trust_status": "verified"},
            {"id": "p-2", "year": 2023, "trust_status": "pending"},
        ],
    )
    monkeypatch.setattr(eb, "get_supabase_admin", lambda: fake)
    return fake


def test_essay_pyq_tags_readable_by_any_authenticated_user(tags_sb):
    a = eb.list_essay_pyq_tags(theme_id=None, limit=200, user=_user("user-a"))
    b = eb.list_essay_pyq_tags(theme_id=None, limit=200, user=_user("user-b"))
    assert a == b
    assert {i["id"] for i in a["items"]} == {"tag-1", "tag-2"}


def test_essay_pyq_tags_filters_by_theme(tags_sb):
    out = eb.list_essay_pyq_tags(theme_id=THEME_B, limit=200, user=_user("user-a"))
    assert [i["id"] for i in out["items"]] == ["tag-2"]
    assert out["items"][0]["year"] == 2024
    assert out["items"][0]["question_text"].startswith("Poverty")


def test_essay_pyq_tags_hides_pending_tags_and_unverified_parents(tags_sb):
    out = eb.list_essay_pyq_tags(theme_id=THEME_A, limit=200, user=_user("user-a"))
    ids = {i["id"] for i in out["items"]}
    assert ids == {"tag-1"}
    assert "tag-pending" not in ids           # tag not verified
    assert "tag-unverified-question" not in ids  # question not verified
    assert "tag-untrusted-paper" not in ids   # paper not trust-verified


def test_essay_pyq_tags_empty_when_nothing_verified(monkeypatch):
    fake = SB(essay_pyq_tags=[], pyq_questions=[], pyq_papers=[])
    monkeypatch.setattr(eb, "get_supabase_admin", lambda: fake)
    out = eb.list_essay_pyq_tags(theme_id=None, limit=200, user=_user("user-a"))
    assert out == {"items": [], "count": 0}


def test_essay_pyq_tags_rejects_non_uuid_theme(tags_sb):
    with pytest.raises(HTTPException) as exc:
        eb.list_essay_pyq_tags(theme_id="not-a-uuid", limit=200, user=_user("user-a"))
    assert exc.value.status_code == 422


# ── essay theme catalogue ─────────────────────────────────────────────────


@pytest.fixture
def themes_sb(monkeypatch):
    fake = SB(
        essay_themes=[
            {
                "id": THEME_A, "theme_code": "ECO", "theme_name": "Economy and development",
                "description": "Growth, welfare and the state's role.", "status": "active",
                "sort_order": 1, "first_seen_year": 2013,
                "metadata": {"internal": "do-not-leak"},
                "created_at": "2026-08-01T00:00:00+00:00",
                "updated_at": "2026-08-01T00:00:00+00:00",
            },
            {
                "id": THEME_B, "theme_code": "GOV", "theme_name": "Governance",
                "description": None, "status": "active", "sort_order": 2,
                "first_seen_year": 2014, "metadata": {},
                "created_at": "2026-08-01T00:00:00+00:00",
                "updated_at": "2026-08-01T00:00:00+00:00",
            },
            {
                "id": "77777777-7777-4777-8777-777777777777", "theme_code": "FUT",
                "theme_name": "Reserved for a future year", "description": None,
                "status": "reserved", "sort_order": 99, "first_seen_year": None,
                "metadata": {}, "created_at": "2026-08-01T00:00:00+00:00",
                "updated_at": "2026-08-01T00:00:00+00:00",
            },
        ],
    )
    monkeypatch.setattr(eb, "get_supabase_admin", lambda: fake)
    return fake


def test_theme_catalogue_returns_active_themes_by_default(themes_sb):
    out = eb.list_essay_themes(include_reserved=False, limit=200, user=_user("user-a"))
    assert {i["theme_code"] for i in out["items"]} == {"ECO", "GOV"}
    assert out["count"] == 2


def test_theme_catalogue_includes_reserved_only_when_asked(themes_sb):
    out = eb.list_essay_themes(include_reserved=True, limit=200, user=_user("user-a"))
    assert {i["theme_code"] for i in out["items"]} == {"ECO", "GOV", "FUT"}
    assert out["count"] == 3


def test_theme_catalogue_exposes_only_the_aspirant_facing_fields(themes_sb):
    out = eb.list_essay_themes(include_reserved=False, limit=200, user=_user("user-a"))
    eco = next(i for i in out["items"] if i["theme_code"] == "ECO")
    assert set(eco.keys()) == {"id", "theme_code", "theme_name", "description", "status"}
    # Authoring-side columns must not leak through a read-only aspirant route.
    for authoring_field in ("sort_order", "metadata", "first_seen_year", "created_at", "updated_at"):
        assert authoring_field not in eco
    assert eco["theme_name"] == "Economy and development"
    assert eco["description"] == "Growth, welfare and the state's role."


def test_theme_catalogue_is_shared_not_ownership_scoped(themes_sb):
    # Same rows for any authenticated aspirant — themes are reference data.
    a = eb.list_essay_themes(include_reserved=False, limit=200, user=_user("user-a"))
    b = eb.list_essay_themes(include_reserved=False, limit=200, user=_user("user-b"))
    assert a == b
    assert a["count"] > 0


def test_theme_catalogue_needs_no_permission_gate():
    import inspect

    from app.core import auth

    dep = inspect.signature(eb.list_essay_themes).parameters["user"].default
    # Plain authentication only. `require_permission(...)` would return a
    # closure, not this function — an aspirant must not be gated out.
    assert getattr(dep, "dependency", None) is auth.get_current_user


def test_theme_catalogue_empty_catalogue_reads_cleanly(monkeypatch):
    fake = SB(essay_themes=[])
    monkeypatch.setattr(eb, "get_supabase_admin", lambda: fake)
    out = eb.list_essay_themes(include_reserved=False, limit=200, user=_user("user-a"))
    assert out == {"items": [], "count": 0}


# ── auth wiring ────────────────────────────────────────────────────────────


def test_routes_require_auth():
    from app.core import auth

    for fn in (eb.list_blocks, eb.get_block, eb.list_essay_pyq_tags):
        dep = inspect.signature(fn).parameters["user"].default
        assert getattr(dep, "dependency", None) is auth.get_current_user
    for fn in (eb.create_block, eb.update_block, eb.delete_block):
        dep = inspect.signature(fn).parameters["user"].default
        assert getattr(dep, "dependency", None) is auth.get_current_user_required_permanent


def test_write_rate_limit_fires(sb):
    rate_limit.configure("essay_blocks.write", per_minute=2, burst=2)
    body = eb.BlockCreate(theme_id=THEME_A, block_type="hook", block_text="x")
    eb.create_block(body, user=_user("rl-user"))
    eb.create_block(body, user=_user("rl-user"))
    with pytest.raises(HTTPException) as exc:
        eb.create_block(body, user=_user("rl-user"))
    assert exc.value.status_code == 429
