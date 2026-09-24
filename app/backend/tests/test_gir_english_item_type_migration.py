"""Migration 306 — the GIR and English item-type leaves two SSC tagging passes
could not place.

Same convention as `test_qa_ssc_geometry_migration.py`: CI has no live-DB
migration harness, so these assert against the migration SQL TEXT, and
`app/supabase/tests/regression_306_gir_english_item_type_gaps.sql` carries the
behaviour — apply, two applies, additivity, and the tag resolution of the five
questions sitting on `Logical Order` — validated on ephemeral PG16.

What text alone can pin, and is pinned here:

* the migration can only INSERT, and asserts its own additivity;
* the slugs follow `left(md5(name), 8)` with the subject's prefix, recomputed
  here rather than trusted;
* each leaf's anchor is the macro the brief named, and `Logical Order` is not
  one of them — the para jumble deliberately lands elsewhere;
* the catalogue export picks the six up at microtopic level, and an SSC number
  series / voice / para-jumble question, which had no defensible candidate in
  its own subject before, has one after.

The last group runs the real `catalog_rows` and `build_candidates` against the
committed live catalogue dump, so it describes the catalogue that exists rather
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
    _ROOT / "app" / "supabase" / "migrations" / "306_gir_english_ssc_item_type_gaps.sql"
)
MIGRATION = MIGRATION_PATH.read_text()
SQL = MIGRATION.lower()

#: The executable statements alone. The header spends fifty lines on what this
#: migration does NOT do ("nothing here renames, re-parents, deactivates or
#: deletes a row"), so a prohibition checked against the whole file would trip
#: over its own rationale. No `--` appears inside a string literal here.
BODY = "\n".join(
    line for line in SQL.splitlines() if not line.lstrip().startswith("--")
)

#: The live catalogue as exported after 277 — QA 55, GIR 59, English 68 leaves,
#: which is what demo holds today. `logical-order`'s id in this dump matches the
#: one the operator brief quoted, which is how we know the dump is current.
LIVE_CATALOGUE = json.loads(
    (_ROOT / "workbench" / "catalogs" / "topic_catalog_nabard_277.json").read_text()
)
GIR = "general-intelligence-reasoning"
ENGLISH = "english-language"
GIR_SUBJECT_ID = "55555555-5555-5555-5555-555555555553"
ENGLISH_SUBJECT_ID = "55555555-5555-5555-5555-555555555552"

#: anchor slug -> (subject, the new leaves hung off it). The anchors are READ,
#: never written: they carry live tags.
ANCHORS = {
    "reas-alphabet-series-b3b70d39": GIR,
    "reas-arithmetic-operation-machine-258cf421": GIR,
    "eng-tense-and-sequence-of-tenses-7e82f0cb": ENGLISH,
    "eng-word-order-and-modifier-placement-1b73c44c": ENGLISH,
}

#: The row the brief says to leave alone. Five para jumbles are tagged on it.
LOGICAL_ORDER_ID = "b2b889f0-5310-23a4-a50c-daa504f0afe7"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


review = _load("pyq_question_review")
proposer = _load("propose_pyq_topic_tags")


def _slug_for(prefix: str, name: str) -> str:
    body = unicodedata.normalize("NFKD", name).lower()
    body = re.sub(r"[^a-z0-9]+", "-", body).strip("-")
    return f"{prefix}-{body}-{hashlib.md5(name.encode()).hexdigest()[:8]}"


def new_rows() -> list[tuple[str, str, str]]:
    """(anchor_slug, slug, name) for every row inserted, parsed from the SQL.

    Parsed rather than restated, so a seventh row added to the migration and not
    to this file fails the count below instead of passing unnoticed.
    """
    out = []
    for tup in re.findall(r"\(\s*((?:'(?:[^']*)',?\s*(?:--[^\n]*\n\s*)?)+)\)", MIGRATION):
        parts = re.findall(r"'([^']*)'", tup)
        if len(parts) == 4 and parts[0] in ANCHORS:
            out.append((parts[0], parts[1], parts[2]))
    return out


def subject_of(slug: str) -> str:
    return GIR if slug.startswith("reas-") else ENGLISH


# ── 1. additive only ──────────────────────────────────────────────────────

def test_the_migration_only_inserts():
    """The 1,428 existing primary tags point at rows in this table, and both
    subjects are shared by four exam bodies. Nothing may change."""
    for verb in ("update public.topics", "delete from public.topics",
                 "alter table public.topics", "drop table public", "truncate"):
        assert verb not in BODY, f"migration 306 contains {verb!r}"
    assert len(re.findall(r"insert into public\.topics", SQL)) == 1


def test_no_row_is_re_parented_or_renamed():
    """`on conflict do update` would rewrite a live row through the back door."""
    assert "on conflict" not in BODY


def test_the_migration_asserts_its_own_additivity():
    """A header claiming 'additive' is not a check. The transaction snapshots
    every column of every pre-existing row and fails on any difference."""
    assert "create temp table _topics_before_306" in SQL
    assert "is distinct from" in SQL
    assert "raise exception 'migration 306 is additive only" in SQL
    assert "disappeared" in SQL and "changed" in SQL


def test_the_snapshot_covers_every_column_the_readers_use():
    """A snapshot of (id, slug) would pass while a rename went through."""
    for column in ("subject_id", "parent_topic_id", "slug", "name",
                   "level", "is_active", "metadata"):
        assert BODY.count(column) >= 3, column


def test_the_insert_is_guarded_on_the_slug():
    """Idempotency: a second apply must insert nothing rather than raise on the
    (subject_id, parent_topic_id, slug) unique index."""
    assert "where not exists (\n  select 1 from public.topics t where t.slug = v.slug\n)" in SQL


def test_parents_are_resolved_by_slug_never_hardcoded():
    """Migration 269 aborted every clean `supabase db reset` by hardcoding a
    parent id no migration creates. These trees live only on the live database."""
    assert "join public.topics a on a.slug = v.anchor_slug" in SQL
    assert not re.search(r"parent_topic_id\s*=\s*'[0-9a-f]{8}-", SQL)
    # The only uuid in the file is `Logical Order`'s, and only in a comment
    # explaining what is NOT done to it.
    assert LOGICAL_ORDER_ID not in BODY


def test_an_absent_tree_is_a_no_op_not_an_abort():
    """The anchor join, not a lookup that could return NULL and insert an
    orphan, is what makes a fresh database safe."""
    assert "join public.topics a on a.slug" in SQL
    assert "left join" not in BODY


# ── 2. the rows themselves ────────────────────────────────────────────────

def test_six_rows_are_added_all_microtopics():
    rows = new_rows()
    assert len(rows) == 6, [s for _, s, _ in rows]
    assert SQL.count("'microtopic',") == 1   # one INSERT, one level literal
    assert "'topic'," not in BODY            # no new macro


def test_three_go_to_reasoning_and_three_to_english():
    got = sorted(subject_of(slug) for _, slug, _ in new_rows())
    assert got == [ENGLISH] * 3 + [GIR] * 3


def test_every_new_slug_follows_the_md5_suffix_convention():
    """`left(md5(name), 8)` with the subject's prefix — the convention 273 set
    and 277/305 followed. Recomputed so a hand-typed slug cannot drift."""
    for _, slug, name in new_rows():
        prefix = slug.split("-")[0]
        assert slug == _slug_for(prefix, name), f"{slug} is not the slug of {name!r}"


def test_the_slug_prefix_matches_the_anchors_subject():
    for anchor, slug, _ in new_rows():
        assert slug.startswith("reas-" if ANCHORS[anchor] == GIR else "eng-")


def test_ids_are_deterministic_not_random():
    """A worksheet has to be able to name these ids before the migration runs."""
    assert "md5('ccp:topic:' || v.slug)::uuid" in MIGRATION
    assert "gen_random_uuid" not in BODY


def test_names_carry_no_parenthetical_subject_marker():
    """The brief writes "Number series (GIR)" to say which subject's leaf is
    meant. Not one of the 127 live rows in these two subjects carries a
    parenthetical subject tag, so neither do these."""
    live = {r["text"] for r in LIVE_CATALOGUE if r["subject"] in (GIR, ENGLISH)}
    assert not any(re.search(r"\((GIR|English)\)", n) for n in live)
    for _, _, name in new_rows():
        assert not re.search(r"\((GIR|English|Eng)\)$", name), name
    # "(para jumble)" is a gloss on the item type, not a subject marker.
    assert "Sentence rearrangement (para jumble)" in [n for _, _, n in new_rows()]


def test_the_new_slugs_do_not_collide_with_the_live_catalogue():
    live = {r["slug"] for r in LIVE_CATALOGUE}
    for _, slug, _ in new_rows():
        assert slug not in live, f"{slug} already exists live"


def test_the_anchors_exist_in_the_live_catalogue_in_the_right_subject():
    """An anchor that is not there makes that row a silent no-op."""
    by_slug = {r["slug"]: r for r in LIVE_CATALOGUE}
    for anchor, subject in ANCHORS.items():
        assert anchor in by_slug, anchor
        assert by_slug[anchor]["subject"] == subject


def test_no_exams_key_is_added():
    """Both subjects are body-agnostic and the tooling runs --any-body; one
    `exams` key here empties every candidate set (see the SSC runbook)."""
    assert "'exams'" not in SQL
    assert '"exams"' not in SQL
    assert "jsonb_build_object(\n    'ssc_cgl_tier1_area'" in MIGRATION


def test_the_anchors_themselves_carry_no_exams_key():
    """The inherited metadata is the anchor's, so an anchor with a body key
    would smuggle one in. None of these four has one."""
    for r in LIVE_CATALOGUE:
        if r["slug"] in ANCHORS:
            assert not (r.get("metadata") or {}).get("exams")
            assert not r.get("exams")


def test_sibling_metadata_is_inherited_not_replaced():
    assert MIGRATION.count("COALESCE(a.metadata, '{}'::jsonb) ||") == 1
    assert "'added_by_migration', '306'" in MIGRATION


def test_the_provenance_is_the_tagging_passes_not_a_quoted_syllabus():
    """305 had to say the SSC notice was unreachable from the build environment.
    306's evidence is different in kind — two operator passes over 122
    questions — and the rows say so instead of citing a line they cannot see."""
    assert "ssc_cgl_tier1_area" in MIGRATION
    assert "workbench/audit/ssc_cgl/drafts/" in MIGRATION
    assert "122 questions" in MIGRATION


# ── 3. the anchors, one row at a time ─────────────────────────────────────

EXPECTED_ANCHORS = {
    "reas-number-series-6232574a": "reas-alphabet-series-b3b70d39",
    "reas-wrong-number-series-31e436e6": "reas-alphabet-series-b3b70d39",
    "reas-mathematical-operations-sign-interchange-3d6288ea":
        "reas-arithmetic-operation-machine-258cf421",
    "eng-active-and-passive-voice-e6437f9d": "eng-tense-and-sequence-of-tenses-7e82f0cb",
    "eng-direct-and-indirect-narration-1d250c23": "eng-tense-and-sequence-of-tenses-7e82f0cb",
    "eng-sentence-rearrangement-para-jumble-66cc898f":
        "eng-word-order-and-modifier-placement-1b73c44c",
}


def test_each_leaf_hangs_off_the_anchor_it_is_documented_under():
    assert {slug: anchor for anchor, slug, _ in new_rows()} == EXPECTED_ANCHORS


def test_the_para_jumble_is_not_anchored_on_logical_order():
    """The whole point of the row. `Logical Order` is a writing-assessment leaf
    (Cohesion, Topic Sentence, Word Limit); a four-option MCQ does not belong
    in the macro a marker uses to judge a candidate's own prose."""
    anchor = EXPECTED_ANCHORS["eng-sentence-rearrangement-para-jumble-66cc898f"]
    assert anchor != "logical-order"
    assert "logical-order" not in [a for a, _, _ in new_rows()]


def test_logical_order_is_left_alone_entirely():
    """Not retired, not renamed, not re-parented, and its five tags stay put.
    Re-tagging those questions is a reviewed worksheet's job."""
    assert "logical-order" not in BODY
    assert "retire" not in BODY
    # `is_active=false` is how a leaf is hidden from aspirants, and it appears
    # here only as the new rows' own column, in the snapshot, and in the
    # additivity comparison. There is no SET clause at all.
    assert not re.search(r"\bset\s+is_active", BODY)
    assert not re.search(r"\bset\b", BODY.split("end $$;")[0])


def test_the_new_leaves_share_their_anchors_macro():
    """`a.parent_topic_id`, not `a.id`: these are siblings of the anchor, not
    children of it. A leaf under a leaf breaks migration 270's level split."""
    insert = MIGRATION.split("INSERT INTO public.topics")[1]
    assert "a.parent_topic_id," in insert
    assert "a.id," not in insert


def test_no_existing_leaf_is_named_as_an_insert_target():
    """Tag resolution is unchanged because no live slug is written to."""
    inserted = {slug for _, slug, _ in new_rows()}
    live = {r["slug"] for r in LIVE_CATALOGUE}
    assert inserted & live == set()


# ── 4. the catalogue export ───────────────────────────────────────────────

def _as_topic_rows(rows):
    """Catalogue dump rows in the shape `catalog_rows` consumes."""
    ids = {GIR: GIR_SUBJECT_ID, ENGLISH: ENGLISH_SUBJECT_ID,
           "quantitative-aptitude": "55555555-5555-5555-5555-555555555551"}
    return [
        {"id": r["id"], "name": r["text"], "slug": r["slug"], "level": "microtopic",
         "subject_id": ids[r["subject"]], "is_active": True, "metadata": {}}
        for r in rows
    ]


def _new_microtopic_rows(subject: str | None = None):
    """The six new leaves, as the CMS would return them after the migration."""
    ids = {GIR: GIR_SUBJECT_ID, ENGLISH: ENGLISH_SUBJECT_ID}
    return [
        {"id": hashlib.md5(f"ccp:topic:{slug}".encode()).hexdigest(),
         "name": name, "slug": slug, "level": "microtopic",
         "subject_id": ids[subject_of(slug)], "is_active": True,
         "metadata": {"ssc_cgl_tier1_area": "x", "added_by_migration": "306"}}
        for _, slug, name in new_rows()
        if subject is None or subject_of(slug) == subject
    ]


def test_the_catalogue_export_picks_up_all_six_leaves():
    live = [r for r in LIVE_CATALOGUE if r["subject"] in (GIR, ENGLISH)]
    topics = _as_topic_rows(live) + _new_microtopic_rows()
    out = review.catalog_rows(topics, bodies=[], any_body=True)

    slugs = {r["slug"] for r in out}
    assert len(out) == len(live) + 6
    for _, slug, _ in new_rows():
        assert slug in slugs
    assert all(r["level"] == "microtopic" for r in out)


def test_the_export_counts_per_subject_are_what_the_pr_reports():
    """59 -> 62 reasoning, 68 -> 71 English, QA untouched at 64 (55 in this
    post-277 dump plus migration 305's nine)."""
    live = {s: sum(1 for r in LIVE_CATALOGUE if r["subject"] == s)
            for s in (GIR, ENGLISH, "quantitative-aptitude")}
    assert live == {GIR: 59, ENGLISH: 68, "quantitative-aptitude": 55}
    assert live[GIR] + len(_new_microtopic_rows(GIR)) == 62
    assert live[ENGLISH] + len(_new_microtopic_rows(ENGLISH)) == 71


def test_the_new_rows_survive_any_body_without_an_exams_key():
    """The filter that emptied the SSC catalogue: with a body predicate these
    rows vanish, which is why the runbook mandates --any-body."""
    rows = _new_microtopic_rows()
    assert review.catalog_rows(rows, bodies=[], any_body=True) != []
    assert review.catalog_rows(rows, bodies=["ssc"], any_body=False) == []


# ── 5. the unmapped questions now have somewhere to go ────────────────────

NUMBER_SERIES = {
    "id": "q-ssc-numseries",
    "subject": GIR,
    "body": "ssc",
    "text": "Select the number that will come next in the series: 25, 30, 40, 55, 75, ?",
}
WRONG_NUMBER = {
    "id": "q-ssc-wrongnum",
    "subject": GIR,
    "body": "ssc",
    "text": ("Select the wrong number in the given series: "
             "16, 36, 64, 100, 145, 196, 256, 324"),
}
SIGN_INTERCHANGE = {
    "id": "q-ssc-signs",
    "subject": GIR,
    "body": "ssc",
    "text": ("If the signs '+' and 'x' are interchanged, which of the following "
             "equations becomes correct?"),
}
VOICE = {
    "id": "q-ssc-voice",
    "subject": ENGLISH,
    "body": "ssc",
    "text": "Select the passive voice form of the sentence: The gardener waters the plants daily.",
}
PARA_JUMBLE = {
    "id": "q-ssc-jumble",
    "subject": ENGLISH,
    "body": "ssc",
    "text": ("The following sentences, labelled A to D, are to be rearranged in "
             "the correct order to form a meaningful paragraph."),
}


def _candidate_rows(subject: str, include_new: bool):
    rows = [
        {"id": r["id"], "slug": r["slug"], "name": r["text"], "level": "microtopic",
         "subject": subject, "exams": [], "description": ""}
        for r in LIVE_CATALOGUE if r["subject"] == subject
    ]
    if include_new:
        rows += [
            {"id": r["id"], "slug": r["slug"], "name": r["name"], "level": "microtopic",
             "subject": subject, "exams": [], "description": ""}
            for r in _new_microtopic_rows(subject)
        ]
    return rows


def _names(rows):
    return {r["name"].lower() for r in rows}


def test_reasoning_has_no_number_series_leaf_before_the_migration():
    """The state that forced the wrong tag: the subject offers `Alphabet series`
    and `Alphanumeric and mixed series` and nothing numeric."""
    names = _names(_candidate_rows(GIR, False))
    assert any("alphabet series" in n for n in names)
    assert not any("number series" in n for n in names)
    assert not any("sign interchange" in n for n in names)


def test_english_has_no_voice_or_narration_leaf_before_the_migration():
    names = _names(_candidate_rows(ENGLISH, False))
    for term in ("passive", "voice", "narration", "indirect speech", "rearrangement"):
        assert not any(term in n for n in names), term


@pytest.mark.parametrize("question,expected", [
    (NUMBER_SERIES, "number series"),
    (WRONG_NUMBER, "wrong-number series"),
    (SIGN_INTERCHANGE, "mathematical operations — sign interchange"),
    (VOICE, "active and passive voice"),
    (PARA_JUMBLE, "sentence rearrangement (para jumble)"),
])
def test_after_the_migration_each_sampled_item_type_has_its_candidate(question, expected):
    rows = _candidate_rows(question["subject"], True)
    names = _names(proposer.build_candidates(question, rows, any_body=True))
    assert expected in names


def test_the_candidate_set_only_grows():
    """Nothing is removed from what the model could already choose."""
    for subject, question in ((GIR, NUMBER_SERIES), (ENGLISH, VOICE)):
        before = proposer.build_candidates(question, _candidate_rows(subject, False),
                                           any_body=True)
        after = proposer.build_candidates(question, _candidate_rows(subject, True),
                                          any_body=True)
        assert {r["slug"] for r in before} <= {r["slug"] for r in after}


def test_a_reasoning_series_question_is_never_offered_a_qa_leaf():
    """QA already has number-series leaves; the subject filter runs first, so a
    reasoning question could never reach them. That is why 306 adds its own."""
    rows = _candidate_rows(GIR, True) + [
        {"id": r["id"], "slug": r["slug"], "name": r["text"], "level": "microtopic",
         "subject": "quantitative-aptitude", "exams": [], "description": ""}
        for r in LIVE_CATALOGUE if r["subject"] == "quantitative-aptitude"
    ]
    out = proposer.build_candidates(NUMBER_SERIES, rows, any_body=True)
    assert out, "the reasoning question lost every candidate"
    assert all(r["subject"] == GIR for r in out)


def test_the_two_series_leaves_are_distinguishable_not_a_near_duplicate():
    """Finding the next term and finding the intruder are different tasks. The
    names differ by more than a word so a worksheet cannot pick either one."""
    names = _names(_candidate_rows(GIR, True))
    assert "number series" in names and "wrong-number series" in names
    for_intruder = _names(proposer.build_candidates(
        WRONG_NUMBER, _candidate_rows(GIR, True), any_body=True))
    assert "wrong-number series" in for_intruder


# ── 6. the regression exists and is wired to this migration ───────────────

def test_the_behavioural_regression_is_committed():
    path = (_ROOT / "app" / "supabase" / "tests"
            / "regression_306_gir_english_item_type_gaps.sql")
    sql = path.read_text()
    assert "306_gir_english_ssc_item_type_gaps.sql" in sql
    # Applied three times: twice for idempotency, once against an empty tree.
    assert sql.count("\\i app/supabase/migrations/306_") == 3
    assert "tag resolution changed" in sql
    assert "Logical Order was altered" in sql
    assert "absent-tree apply is a no-op" in sql


def test_the_regression_covers_the_row_that_must_not_move():
    """`Logical Order` at its live id, in the writing macro, with its five tags
    — asserted after two applies."""
    sql = (_ROOT / "app" / "supabase" / "tests"
           / "regression_306_gir_english_item_type_gaps.sql").read_text()
    assert LOGICAL_ORDER_ID in sql
    assert "Logical Order lost tags" in sql
    assert "para jumble landed in the writing macro" in sql


# ── 7. the duplicate-pair report ──────────────────────────────────────────

REPORT_PATH = (_ROOT / "workbench" / "reports"
               / "ENGLISH-CATALOGUE-DUPLICATE-PAIRS-2026-09-23.md")

#: Every row the report names, with the id it prints. Asserted against the live
#: dump so a stale id in the report is a test failure rather than an operator
#: running the wrong UPDATE.
REPORTED = {
    "subject-verb-agreement": "b9facc82-38d7-f725-7c97-8b5894c157f0",
    "eng-subject-verb-agreement-07be8ac5": "7c71b869-e50a-4ebd-aea1-fe291dbee5ed",
    "prepositions": "5db857e5-5b9d-2f80-0046-1978c199ed85",
    "articles": "b790ab2c-17e8-9025-f313-2c44d24dac8d",
    "eng-preposition-and-article-errors-000b76d8": "f9c12eec-a497-4d10-b219-2da6b28a92f7",
    "eng-preposition-and-phrasal-completion-5c07ccb9": "613e6076-97c1-4a2b-b932-8831642cf075",
    "pronoun-reference": "c6beb287-3fef-397f-e204-57f8e4053328",
    "eng-pronoun-reference-and-agreement-d6412298": "ee103c0c-a9fa-4ae8-98dd-78cdc4378732",
    "redundancy": "84fae1ba-f1d4-98da-1c09-45c51ceb2e22",
    "eng-redundancy-and-wordiness-1787d0ac": "e6e0700f-0130-49e0-961d-89cbe5eab3f8",
    "tense": "aa680736-24d9-abb2-d7f2-ad3bcb2acb77",
    "eng-tense-and-sequence-of-tenses-7e82f0cb": "f146f9b5-b13d-47c0-8aca-c80a6566b4fe",
    "modifiers": "aca53761-13fc-65c9-bd3c-9f324e9a589f",
    "eng-word-order-and-modifier-placement-1b73c44c": "3ab068c5-397c-4189-913f-0d26569b3899",
    "permutations-and-combinations": "de0e24eb-5c25-4e0f-8eeb-325b8732f9cc",
    "clocks-and-calendars": "484fbb39-85bd-4c88-88b3-9426befa6b49",
}


def test_every_id_in_the_report_is_the_live_id_of_that_slug():
    """The report's SQL is copy-pasted by an operator. A drifted id would
    re-point real tags at the wrong topic."""
    report = REPORT_PATH.read_text()
    by_slug = {r["slug"]: r["id"] for r in LIVE_CATALOGUE}
    for slug, topic_id in REPORTED.items():
        assert by_slug.get(slug) == topic_id, slug
        assert slug in report and topic_id in report, slug


def test_the_report_finds_every_legacy_shaped_slug_subsumed_by_a_modern_one():
    """A pair the report missed is a pair nobody decides about.

    The sweep the report documents: a legacy row (slug without its subject's
    prefix) is a merge candidate when its WHOLE name is contained in some modern
    row's name, ignoring case, plurals and function words. That rule finds the
    four the brief named plus `tense` and `modifiers`; anything a later export
    adds fails here instead of going unnoticed.
    """
    report = REPORT_PATH.read_text()
    prefixes = {GIR: "reas-", ENGLISH: "eng-", "quantitative-aptitude": "qa-"}
    stop = {"and", "or", "of", "the", "a", "in", "to", "with",
            "from", "within", "by", "their", "its"}

    def stems(text):
        words = [w for w in re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
                 if w not in stop]
        return {w[:-1] if len(w) > 4 and w.endswith("s") else w for w in words}

    subsumed = set()
    for subject, prefix in prefixes.items():
        rows = [r for r in LIVE_CATALOGUE if r["subject"] == subject]
        modern = [stems(r["text"]) for r in rows if r["slug"].startswith(prefix)]
        for r in rows:
            if r["slug"].startswith(prefix):
                continue
            legacy = stems(r["text"])
            if legacy and any(legacy <= m for m in modern):
                subsumed.add(r["slug"])

    assert subsumed == {
        "subject-verb-agreement", "pronoun-reference", "redundancy",
        "prepositions", "articles", "tense", "modifiers",
    }, sorted(subsumed)
    for slug in subsumed:
        assert slug in report, slug
    # The two the brief did not name are flagged as such, not folded in silently.
    assert report.count("**not in the brief**") == 2


def test_the_report_keeps_the_writing_leaves_out_of_the_merge():
    """The near-misses. These legacy rows share a word with a modern row and
    nothing else: they are descriptive-writing assessment criteria, not MCQ item
    types. Merging them would be the mistake 306 is built to avoid."""
    report = REPORT_PATH.read_text()
    for name in ("Simple Sentences", "Compound Sentences", "Complex Sentences",
                 "Sentence Transformation", "Sentence Structure", "Word Choice",
                 "Word Limit", "Topic Sentence", "Formal Vocabulary",
                 "Logical Order"):
        assert name in report, name
    assert "Leave all of these alone." in report


def test_the_report_ships_no_schema_change():
    """The brief says report, propose, ship nothing — 306 touches none of the
    rows the report merely reports on.

    This originally also asserted that 306 was the highest-numbered migration in
    the whole repo. That was a claim about the PR that shipped it, written as a
    repo-global invariant, so it was guaranteed to break on the next migration
    anyone added — 307 (EXPL-OPTID-01) was the first to hit it. A PR's scope is
    recorded in git history and cannot be re-derived from the tree afterwards,
    so that half is gone and the half that is still true and still worth
    guarding stays: 306 exists, and it writes no reported row.
    """
    assert MIGRATION_PATH.exists(), MIGRATION_PATH

    # 306 inserts no reported row, and the two reported rows it does name
    # (the modern members of pairs 2.5 and 2.6) appear only as anchors, which
    # are joined on and never written.
    inserted = {slug for _, slug, _ in new_rows()}
    assert inserted & set(REPORTED) == set()
    named = {slug for slug in REPORTED if f"'{slug}'" in BODY}
    assert named == {"eng-tense-and-sequence-of-tenses-7e82f0cb",
                     "eng-word-order-and-modifier-placement-1b73c44c"}
    assert named <= set(ANCHORS)


def test_the_report_states_the_counts_could_not_be_computed():
    """The brief asked for per-exam tag counts. There is no live access and
    `workbench/audit/ssc_cgl/drafts/` is not in the repo, so the report must say
    so and hand over the SQL rather than print a plausible number."""
    report = REPORT_PATH.read_text()
    assert "NOT PRODUCED HERE" in report
    assert "There is no `drafts/` directory in the" in report
    assert not (_ROOT / "workbench" / "audit" / "ssc_cgl" / "drafts").exists()
    # The SQL an operator runs instead.
    assert "pyq_question_topic_tags" in report and "GROUP BY" in report


def test_the_report_retires_rather_than_deletes():
    """CLAUDE.md: retire is not archive, and a deleted topic id breaks every
    worksheet and evidence record that names it."""
    report = REPORT_PATH.read_text()
    assert "UPDATE public.topics SET is_active = false" in report
    assert "DELETE FROM public.topics" not in report.replace(
        "**`is_active = false`, not `DELETE FROM public.topics`.**", "")


def test_the_proposed_merge_guards_the_tag_uniqueness_constraint():
    """A question tagged with both members would abort the whole UPDATE."""
    report = REPORT_PATH.read_text()
    assert "NOT EXISTS" in report
    assert "prepositions" in report
