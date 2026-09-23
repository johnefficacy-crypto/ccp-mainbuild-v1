"""Migration 305 — the SSC CGL geometry, trigonometry and central-tendency leaves.

Repo convention (see test_financial_regulatory_seed_migration.py): CI has no
live-DB migration harness, so these assert against the migration SQL text, and
`app/supabase/tests/regression_305_qa_ssc_geometry_trigonometry.sql` carries the
behaviour — apply, two applies, additivity and tag resolution — validated on
ephemeral PG16.

What is pinned here that text alone can pin:

* the migration can only INSERT — no verb that could change a live row appears;
* the slugs follow `left(md5(name), 8)`, recomputed here rather than trusted;
* the catalogue export picks the new leaves up and leaves the new macro out;
* an SSC geometry question, which had NO defensible candidate before, has one.

The last two run the real `catalog_rows` and `build_candidates` against the
committed live catalogue dump, so they describe the actual catalogue rather
than a fixture invented to agree with the migration.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import unicodedata

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[3]
MIGRATION_PATH = (
    _ROOT / "app" / "supabase" / "migrations"
    / "305_qa_ssc_geometry_trigonometry_central_tendency.sql"
)
MIGRATION = MIGRATION_PATH.read_text()
SQL = MIGRATION.lower()

#: The executable statements alone. The header explains at length what this
#: migration does NOT do ("not gen_random_uuid()", "never renames"), so a
#: prohibition asserted against the whole file would trip over its own
#: rationale. There is no `--` inside a string literal in this migration.
BODY = "\n".join(
    line for line in SQL.splitlines() if not line.lstrip().startswith("--")
)

#: The live catalogue as exported after migration 277 — QA 55, GIR 59, Eng 68,
#: which is what demo holds today. Microtopic rows only, by `catalog`'s rule.
LIVE_CATALOGUE = json.loads(
    (_ROOT / "workbench" / "catalogs" / "topic_catalog_nabard_277.json").read_text()
)
QA_SUBJECT = "quantitative-aptitude"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


review = _load("pyq_question_review")
proposer = _load("propose_pyq_topic_tags")


def _slug_for(name: str) -> str:
    body = unicodedata.normalize("NFKD", name).lower()
    body = re.sub(r"[^a-z0-9]+", "-", body).strip("-")
    return f"qa-{body}-{hashlib.md5(name.encode()).hexdigest()[:8]}"


def new_rows() -> list[tuple[str, str]]:
    """(slug, name) for every row this migration inserts, read from the SQL.

    Parsed rather than restated, so a row added to the migration and not to the
    diff table fails the count assertion below instead of passing unnoticed.
    """
    out: dict[str, str] = {}

    # The macro is written longhand: one column per line.
    macro = re.search(
        r"'(qa-trigonometry-[0-9a-f]{8})',\s*\n\s*'([^']+)',\s*\n\s*'topic'", MIGRATION
    )
    assert macro, "the Trigonometry macro row is not in the migration"
    out[macro.group(1)] = macro.group(2)

    # The leaves are VALUES tuples: 4-column (anchor, slug, name, area) beside
    # an existing leaf, or 2-column (slug, name) under the new macro.
    for tup in re.findall(r"\(\s*((?:'(?:[^']*)',?\s*)+)\)", MIGRATION):
        parts = re.findall(r"'([^']*)'", tup)
        if len(parts) == 4 and parts[0] in ANCHORS:
            out[parts[1]] = parts[2]
        elif len(parts) == 2 and parts[0].startswith("qa-"):
            out[parts[0]] = parts[1]
    return sorted(out.items())


#: The existing leaves this migration hangs new rows off. They must survive
#: untouched — they are the two most-tagged geometry/average leaves there are.
ANCHORS = (
    "qa-coordinate-and-line-geometry-eb041f58",
    "qa-averages-simple-and-weighted-1f479970",
)


# ── 1. additive only ──────────────────────────────────────────────────────

def test_the_migration_only_inserts():
    """No verb that could change or remove a live row appears at all. The 1,428
    existing primary tags point at rows in this table."""
    for verb in ("update public.topics", "delete from public.topics",
                 "alter table public.topics", "drop table public", "truncate"):
        assert verb not in BODY, f"migration 305 contains {verb!r}"
    assert sql_insert_count() == 3, "expected exactly three INSERT statements"


def sql_insert_count() -> int:
    return len(re.findall(r"insert into public\.topics", SQL))


def test_no_row_is_re_parented_or_renamed():
    """`on conflict do update` would rewrite a live row through the back door."""
    assert "on conflict" not in BODY


def test_the_migration_asserts_its_own_additivity():
    """A comment claiming 'additive' is not a check. The transaction snapshots
    every column of every pre-existing row and fails on any difference."""
    assert "create temp table _topics_before" in SQL
    assert "is distinct from" in SQL
    assert "raise exception 'migration 305 is additive only" in SQL
    # Both failure modes, not just one.
    assert "disappeared" in SQL and "changed" in SQL


def test_every_insert_is_guarded_on_the_slug():
    """Idempotency: a re-run must insert nothing. Every one of the three
    INSERTs carries its own slug guard — two shy of three would make a re-run
    raise on the (subject_id, parent_topic_id, slug) unique index."""
    guards = re.findall(r"select 1 from public\.topics t where t\.slug", BODY)
    assert len(guards) == sql_insert_count() == 3


def test_parents_are_resolved_by_slug_never_hardcoded():
    """Migration 269 aborted every clean `supabase db reset` by hardcoding a
    parent id that no migration creates. These trees live only on demo."""
    assert "join public.topics a on a.slug = v.anchor_slug" in SQL
    for anchor in ANCHORS:
        assert anchor in MIGRATION
    # No literal topic uuid is used as a parent.
    assert not re.search(r"parent_topic_id\s*=\s*'[0-9a-f]{8}-", SQL)


# ── 2. the rows themselves ────────────────────────────────────────────────

def test_ten_rows_are_added_one_macro_and_nine_leaves():
    rows = new_rows()
    assert len(rows) == 10, [s for s, _ in rows]
    assert SQL.count("'microtopic',") == 2   # two INSERTs write microtopics
    assert "'topic',\n" in MIGRATION or "  'topic'," in MIGRATION


def test_every_new_slug_follows_the_md5_suffix_convention():
    """`left(md5(name), 8)`, the convention 273 set and 277 followed —
    recomputed here so a hand-typed slug cannot drift from its name."""
    for slug, name in new_rows():
        assert slug == _slug_for(name), f"{slug} is not the slug of {name!r}"


def test_ids_are_deterministic_not_random():
    """A worksheet has to be able to name these ids before the migration runs."""
    assert "md5('ccp:topic:' || v.slug)::uuid" in MIGRATION
    assert "gen_random_uuid" not in BODY


def test_the_new_slugs_do_not_collide_with_the_live_catalogue():
    live = {r["slug"] for r in LIVE_CATALOGUE}
    for slug, _ in new_rows():
        assert slug not in live, f"{slug} already exists live"


def test_the_anchors_exist_in_the_live_catalogue():
    """An anchor that is not there makes the whole migration a silent no-op."""
    live = {r["slug"] for r in LIVE_CATALOGUE if r["subject"] == QA_SUBJECT}
    for anchor in ANCHORS:
        assert anchor in live


def test_no_exams_key_is_added():
    """These three subjects are body-agnostic and the tooling runs --any-body;
    one `exams` key here empties every candidate set (see the SSC runbook)."""
    assert "'exams'" not in SQL
    assert '"exams"' not in SQL


def test_the_syllabus_area_is_recorded_without_being_passed_off_as_a_quote():
    """The notice is not reachable from the build environment, so the rows
    carry an area NAME and say where it came from rather than a fabricated
    line attributed to SSC."""
    assert "ssc_cgl_tier1_area" in MIGRATION
    assert "operator brief 2026-09-23" in MIGRATION
    assert "not retrievable in build environment" in MIGRATION


def test_sibling_metadata_is_inherited_not_replaced():
    """A new row whose metadata does not match its siblings' shape is a row the
    next reader of the catalogue has to special-case."""
    assert MIGRATION.count("COALESCE(a.metadata, '{}'::jsonb) ||") == 1
    assert MIGRATION.count("COALESCE(m.metadata, '{}'::jsonb) ||") == 1
    assert MIGRATION.count("COALESCE(parent.metadata, '{}'::jsonb) ||") == 1


# ── 3. the level split migration 270 depends on ───────────────────────────

def test_the_new_macro_is_top_level_and_its_leaves_hang_off_it():
    """Migration 270 resolves a tag's level from `parent_topic_id`: a macro with
    a parent, or a leaf without one, would land in the wrong rollup."""
    macro_stmt = MIGRATION.split("── 1. the Trigonometry macro")[1].split("── 2.")[0]
    assert "NULL,\n  'qa-trigonometry-" in macro_stmt
    assert "'topic'," in macro_stmt

    trig_stmt = MIGRATION.split("── 3. microtopics under the new Trigonometry macro")[1]
    assert "m.id," in trig_stmt          # parent = the macro
    assert "'microtopic'," in trig_stmt


def test_existing_tagged_leaves_are_never_named_as_an_insert_target():
    """Tag resolution is unchanged because no live slug is written to. The
    anchors are READ (joined on) and never appear as a new row's slug."""
    inserted = {slug for slug, _ in new_rows()}
    live = {r["slug"] for r in LIVE_CATALOGUE}
    assert inserted & live == set()


# ── 4. the catalogue export ───────────────────────────────────────────────

def _as_topic_rows(rows, *, subject_id="55555555-5555-5555-5555-555555555551"):
    """Catalogue dump rows in the shape `catalog_rows` consumes."""
    return [
        {"id": r["id"], "name": r["text"], "slug": r["slug"], "level": "microtopic",
         "subject_id": subject_id, "is_active": True, "metadata": {}}
        for r in rows
    ]


def _new_microtopic_rows():
    """The nine new leaves, as the CMS would return them."""
    macro = {s for s, _ in new_rows() if s.startswith("qa-trigonometry-")}
    return [
        {"id": hashlib.md5(f"ccp:topic:{slug}".encode()).hexdigest(),
         "name": name, "slug": slug, "level": "microtopic",
         "subject_id": "55555555-5555-5555-5555-555555555551",
         "is_active": True, "metadata": {"ssc_cgl_tier1_area": "x"}}
        for slug, name in new_rows() if slug not in macro
    ]


def _new_macro_row():
    slug, name = next((s, n) for s, n in new_rows() if s.startswith("qa-trigonometry-"))
    return {"id": "m", "name": name, "slug": slug, "level": "topic",
            "subject_id": "55555555-5555-5555-5555-555555555551",
            "is_active": True, "metadata": {}}


def test_the_catalogue_export_picks_up_the_new_leaves():
    qa_live = [r for r in LIVE_CATALOGUE if r["subject"] == QA_SUBJECT]
    topics = _as_topic_rows(qa_live) + _new_microtopic_rows()
    out = review.catalog_rows(topics, bodies=[], any_body=True)

    slugs = {r["slug"] for r in out}
    assert len(out) == len(qa_live) + 9
    for slug, _ in new_rows():
        if not slug.startswith("qa-trigonometry-"):
            assert slug in slugs
    assert all(r["level"] == "microtopic" for r in out)


def test_the_new_macro_is_not_exported_as_a_taggable_row():
    """`catalog` emits leaves only, and `load_topic_catalog` aborts on any other
    level — a macro in the file would reject every worksheet that names it."""
    out = review.catalog_rows([_new_macro_row()], bodies=[], any_body=True)
    assert out == []


def test_the_new_rows_survive_any_body_without_an_exams_key():
    """The filter that emptied the SSC catalogue: with a body predicate these
    rows vanish, which is why the runbook mandates --any-body."""
    rows = _new_microtopic_rows()
    assert review.catalog_rows(rows, bodies=[], any_body=True) != []
    assert review.catalog_rows(rows, bodies=["ssc"], any_body=False) == []


# ── 5. an SSC geometry question now has somewhere to go ───────────────────

GEOMETRY_QUESTION = {
    "id": "q-ssc-geom",
    "subject": QA_SUBJECT,
    "body": "ssc",
    "text": ("In a circle with centre O, AB is a chord and PT is a tangent at P. "
             "If angle OAB = 35 degrees, find angle APT."),
}
TRIG_QUESTION = {
    "id": "q-ssc-trig",
    "subject": QA_SUBJECT,
    "body": "ssc",
    "text": "If sin A = 3/5, find the value of (1 + tan^2 A) / (1 + cot^2 A).",
}


def _candidate_rows(include_new: bool):
    rows = [
        {"id": r["id"], "slug": r["slug"], "name": r["text"], "level": "microtopic",
         "subject": QA_SUBJECT, "exams": [], "description": ""}
        for r in LIVE_CATALOGUE if r["subject"] == QA_SUBJECT
    ]
    if include_new:
        rows += [
            {"id": r["id"], "slug": r["slug"], "name": r["name"], "level": "microtopic",
             "subject": QA_SUBJECT, "exams": [], "description": ""}
            for r in _new_microtopic_rows()
        ]
    return rows


def _names(rows):
    return {r["name"].lower() for r in rows}


@pytest.mark.parametrize("question", [GEOMETRY_QUESTION, TRIG_QUESTION])
def test_before_the_migration_there_is_no_honest_candidate(question):
    """The state that forced the wrong tag: the whole QA catalogue offers the
    model nothing about a theorem or a ratio, only areas and volumes."""
    names = _names(proposer.build_candidates(question, _candidate_rows(False),
                                             any_body=True))
    for term in ("trigono", "tangent", "chord", "congru", "similar",
                 "median", "mode", "heights"):
        assert not any(term in n for n in names), term


def test_after_the_migration_the_geometry_question_has_a_candidate():
    names = _names(proposer.build_candidates(GEOMETRY_QUESTION,
                                             _candidate_rows(True), any_body=True))
    assert any("circle theorems" in n for n in names)
    assert any("congruence and similarity" in n for n in names)


def test_after_the_migration_the_trig_question_has_a_candidate():
    names = _names(proposer.build_candidates(TRIG_QUESTION,
                                             _candidate_rows(True), any_body=True))
    assert any("trigonometric ratios and identities" in n for n in names)
    assert any("complementary angles" in n for n in names)
    assert any("heights and distances" in n for n in names)


def test_the_candidate_set_grows_by_exactly_the_new_leaves():
    """Nothing is removed from what the model could already choose."""
    before = proposer.build_candidates(GEOMETRY_QUESTION, _candidate_rows(False),
                                       any_body=True)
    after = proposer.build_candidates(GEOMETRY_QUESTION, _candidate_rows(True),
                                      any_body=True)
    assert {r["slug"] for r in before} <= {r["slug"] for r in after}
    assert len(after) - len(before) == 9


def test_median_and_mode_does_not_shadow_averages():
    """Deliberately not named 'Mean, median and mode': a plain-mean question
    would then match two leaves equally and produce a tag_conflict."""
    names = _names(_candidate_rows(True))
    assert "median and mode" in names
    assert "averages — simple and weighted" in names
    assert not any(n.startswith("mean, median") for n in names)


# ── 6. the regression exists and is wired to this migration ───────────────

def test_the_behavioural_regression_is_committed():
    path = _ROOT / "app" / "supabase" / "tests" / "regression_305_qa_ssc_geometry_trigonometry.sql"
    sql = path.read_text()
    assert "305_qa_ssc_geometry_trigonometry_central_tendency.sql" in sql
    # Applied twice, which is what makes it an idempotency test.
    assert sql.count("\\i app/supabase/migrations/305_") == 3
    assert "tag resolution changed" in sql
    assert "absent-tree apply is a no-op" in sql
