"""Migration 308 — the GIR `Venn diagram` leaf, and the audit that refuses to
retire the `english-language` bare-slug rows.

Same convention as `test_qa_ssc_geometry_migration.py` and
`test_gir_english_item_type_migration.py`: CI has no live-DB migration harness,
so these assert against the migration SQL TEXT, and
`app/supabase/tests/regression_308_venn_and_english_retire_audit.sql` carries
the behaviour — every audit verdict, the delete branch, the cascade hazard and
the composite FK — validated on ephemeral PG16.

The substantive claim pinned here is the one that reverses the duplicate-pair
report: the seven bare-slug rows are migration 205's English Writing Practice
taxonomy, every one of them mapped from an `issue_type` in
`writing_issue_type_microtopic_map`, and therefore not retirable. That is read
out of migration 205 itself rather than asserted, so it fails if 205 is ever
misread rather than passing on a restatement.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unicodedata

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[3]
MIGRATIONS = _ROOT / "app" / "supabase" / "migrations"
MIGRATION_PATH = MIGRATIONS / "308_gir_venn_diagram_and_english_duplicate_audit.sql"
MIGRATION = MIGRATION_PATH.read_text()
SQL = MIGRATION.lower()

#: Executable statements only. The header spends a hundred lines on what this
#: migration does NOT do, including the word `delete` a dozen times.
BODY = "\n".join(
    line for line in SQL.splitlines() if not line.lstrip().startswith("--")
)

EWP_MIGRATION = (MIGRATIONS / "205_english_writing_practice_schema.sql").read_text()

LIVE_CATALOGUE = json.loads(
    (_ROOT / "workbench" / "catalogs" / "topic_catalog_nabard_277.json").read_text()
)
GIR = "general-intelligence-reasoning"
ENGLISH = "english-language"

ANCHOR = "reas-two-statement-syllogism-7f65e035"
NEW_SLUG = "reas-venn-diagram-360f6cdd"
NEW_NAME = "Venn diagram"

#: The rows the duplicate-pair report proposed retiring.
CANDIDATES = (
    "subject-verb-agreement", "tense", "articles", "prepositions",
    "pronoun-reference", "modifiers", "redundancy",
)


def _slug_for(prefix: str, name: str) -> str:
    body = unicodedata.normalize("NFKD", name).lower()
    body = re.sub(r"[^a-z0-9]+", "-", body).strip("-")
    return f"{prefix}-{body}-{hashlib.md5(name.encode()).hexdigest()[:8]}"


# ── 1. part 1: the Venn diagram leaf ──────────────────────────────────────

def test_exactly_one_row_is_inserted():
    assert len(re.findall(r"insert into public\.topics", SQL)) == 1
    assert SQL.count("'microtopic',") == 1
    assert "'topic'," not in BODY          # no new macro


def test_the_slug_follows_the_md5_suffix_convention():
    """`left(md5(name), 8)` with the subject's prefix — recomputed, not trusted."""
    assert NEW_SLUG == _slug_for("reas", NEW_NAME)
    assert f"'{NEW_SLUG}'" in MIGRATION
    assert f"'{NEW_NAME}'" in MIGRATION


def test_the_id_is_deterministic():
    assert "md5('ccp:topic:' || v.slug)::uuid" in MIGRATION
    assert "gen_random_uuid" not in BODY


def test_the_new_slug_does_not_collide_and_the_anchor_exists():
    by_slug = {r["slug"]: r for r in LIVE_CATALOGUE}
    assert NEW_SLUG not in by_slug
    assert ANCHOR in by_slug
    assert by_slug[ANCHOR]["subject"] == GIR


def test_the_subject_has_no_number_set_leaf_today():
    """The gap the five sampled questions fall into: two syllogism leaves and a
    letter/digit counting leaf, nothing about set cardinality."""
    names = {r["text"].lower() for r in LIVE_CATALOGUE if r["subject"] == GIR}
    assert not any("venn" in n for n in names)
    assert not any("set" in n.split() for n in names)
    assert "two-statement syllogism" in names


def test_the_leaf_is_the_anchors_sibling_not_its_child():
    """`a.parent_topic_id`, not `a.id`. A leaf under a leaf breaks migration
    270's level split."""
    insert = MIGRATION.split("INSERT INTO public.topics")[1].split("-- ── part 2")[0]
    assert "a.parent_topic_id," in insert
    assert "a.id," not in insert


def test_the_parent_is_resolved_by_slug_never_hardcoded():
    assert "join public.topics a on a.slug = v.anchor_slug" in SQL
    assert not re.search(r"parent_topic_id\s*=\s*'[0-9a-f]{8}-", BODY)


def test_the_insert_is_guarded_on_the_slug():
    assert "where not exists (\n  select 1 from public.topics t where t.slug = v.slug\n)" in SQL


def test_no_exams_key_is_added():
    assert "'exams'" not in SQL
    assert '"exams"' not in SQL


def test_sibling_metadata_is_inherited():
    assert MIGRATION.count("COALESCE(a.metadata, '{}'::jsonb) ||") == 1
    assert "'added_by_migration', '308'" in MIGRATION


def test_the_evidence_is_recorded_with_its_papers():
    for paper in ("3d903cdf", "55571471", "64b4c673"):
        assert paper in MIGRATION, paper
    assert "5 occurrences" in MIGRATION


def test_the_macro_is_named_as_the_anchors_and_the_lookup_is_given():
    """The QRE macro names are not in this repository (277's header says the
    tree was created outside the migration set), so the migration says which
    anchor's macro the leaf joins and hands over the query to print it."""
    assert "parent.slug, parent.name" in MIGRATION
    assert "WHERE t.slug = 'reas-venn-diagram-360f6cdd'" in MIGRATION


# ── 2. part 2: the audit refuses, and why ─────────────────────────────────

def test_all_seven_reported_rows_are_audited():
    block = MIGRATION.split("candidates  text[] := ARRAY[")[1].split("];")[0]
    named = set(re.findall(r"'([a-z-]+)'", block))
    assert named == set(CANDIDATES), named


def test_every_candidate_is_an_ewp_microtopic_seeded_by_205():
    """Not a restatement: the slugs are read out of 205's own `micros` array."""
    micros = EWP_MIGRATION.split("micros    text[][] := ARRAY[")[1].split("];")[0]
    seeded = {m[1] for m in re.findall(r"ARRAY\['([^']+)','([^']+)','([^']+)'\]", micros)}
    for cand in CANDIDATES:
        assert cand in seeded, f"{cand} is not seeded by migration 205"


def test_every_candidate_is_the_target_of_an_ewp_issue_type_mapping():
    """This is why none of them can be deleted: `writing_issue_type_microtopic_map`
    resolves an issue type to each one, and 209's evaluator and 213's Error Lab
    read model read through that map at runtime."""
    maps = EWP_MIGRATION.split("maps      text[][] := ARRAY[")[1].split("];")[0]
    mapped = {m[1] for m in re.findall(r"ARRAY\['([^']+)','([^']+)'\]", maps)}
    for cand in CANDIDATES:
        assert cand in mapped, f"{cand} is not an EWP issue-type target"


def test_the_map_column_is_not_nullable_and_does_not_cascade():
    """A NOT NULL, NO ACTION FK: deleting a mapped row raises. The migration
    says so and the regression proves it on a live cluster."""
    decl = re.search(
        r"microtopic_id\s+uuid\s+NOT NULL REFERENCES public\.topics\(id\)([^,]*),",
        EWP_MIGRATION)
    assert decl, "205's map column declaration changed"
    assert "on delete" not in decl.group(1).lower()


def test_the_migration_states_the_report_was_wrong_rather_than_quietly_skipping():
    """A skip nobody reads is the same silence the audit exists to break."""
    assert "THAT READING WAS WRONG" in MIGRATION
    assert "ENGLISH WRITING PRACTICE" in MIGRATION
    assert "TWO TREES IN ONE SUBJECT" in MIGRATION
    assert "writing_issue_type_microtopic_map" in MIGRATION


def test_articles_is_addressed_by_name():
    """The report singled it out as the odd half of a 2:2 split; the brief asks
    what happens to it."""
    section = MIGRATION.split("`articles` SPECIFICALLY")[1].split("── shared guards")[0]
    assert "issue type" in section
    assert "nothing to merge" in section


# ── 3. the audit's mechanics ──────────────────────────────────────────────

def test_the_referencing_tables_are_discovered_not_listed():
    """A hardcoded list goes stale the next time a table gains a topic FK.
    There are 53 such columns across the migration set today."""
    assert "pg_constraint" in SQL
    assert "confrelid = 'public.topics'::regclass" in MIGRATION
    assert "c.contype = 'f'" in MIGRATION
    assert "execute format(" in SQL


def test_composite_foreign_keys_are_aligned_not_assumed_first():
    """`conkey[1]` would count a composite FK on its first column — for
    `writing_prompts (subject_id, microtopic_id)` that is the subject, which
    matches nothing, and the row would look unreferenced and be deleted."""
    assert "generate_subscripts(c.confkey, 1)" in MIGRATION
    assert "c.confkey[s.i]" in MIGRATION
    assert "c.conkey[s.i]" in MIGRATION
    assert "fa.attname  = 'id'" in MIGRATION
    assert "conkey[1]" not in MIGRATION


def test_child_topics_are_counted_separately_from_references():
    """`topics.parent_topic_id` cascades, so a parent with children would take
    them with it."""
    assert "where parent_topic_id = v_id" in SQL
    assert "a.attname = 'parent_topic_id'" in MIGRATION
    assert "v_children" in MIGRATION


def test_the_delete_is_guarded_on_both_counts():
    assert "if v_total = 0 and v_children = 0 then" in SQL
    deletes = re.findall(r"delete from public\.topics[^\n;]*", BODY)
    assert deletes == ["delete from public.topics where id = v_id"], deletes


def test_a_referenced_row_is_skipped_loudly_not_silently():
    assert "kept" in SQL
    assert "raise notice" in SQL
    # The skip records which tables held it, for the operator's evidence.
    assert "referenced_by" in SQL
    assert "array_to_string(v_detail" in SQL


def test_the_on_delete_label_is_cast_to_text():
    """`confdeltype` is "char": a CASE that unifies on "char" truncates
    'CASCADE' to 'C' and 'no action' to 'n'. Caught on the cluster."""
    case = MIGRATION.split("CASE fk.del")[1].split("END)")[0]
    for label in ("'no action'::text", "'restrict'::text", "'CASCADE'::text",
                  "'set null'::text", "fk.del::text"):
        assert label in case, label


def test_an_absent_candidate_is_reported_not_an_error():
    assert "'absent'" in SQL
    assert "nothing to retire" in SQL


def test_the_audit_does_not_abort_the_migration():
    """The brief: abort the delete, not the migration. A row that cannot be
    retired is the expected outcome."""
    audit = MIGRATION.split("-- ── part 2: the reference audit")[1].split(
        "-- ── prove nothing unintended changed")[0]
    assert "RAISE EXCEPTION" not in audit


def test_nothing_is_deactivated_as_a_back_door():
    """`is_active = false` on an EWP row would hide it from the Error Lab
    without deleting it — the same damage, quieter."""
    assert not re.search(r"\bset\s+is_active", BODY)
    assert "update public.topics" not in BODY


# ── 4. the closing assertion ──────────────────────────────────────────────

def test_the_migration_proves_nothing_unintended_changed():
    assert "create temp table _topics_before_308" in SQL
    assert "is distinct from" in SQL
    assert "changed % existing topic row(s)" in MIGRATION
    # A removal the audit did not make is an abort, not a NOTICE.
    assert "removed topic row(s) the audit did not retire" in MIGRATION
    assert "inserted % rows; exactly one leaf is expected" in MIGRATION


def test_on_conflict_is_not_used():
    assert "on conflict" not in BODY


def test_the_migration_number_is_not_reused():
    """Only that 308 is this file and nobody else claimed it. Deliberately NOT
    "308 is the highest number in the repo" — that is a claim about the PR that
    shipped it, and 306's test learned the hard way that it breaks on the next
    migration anyone adds."""
    numbers = [p.name for p in MIGRATIONS.glob("308_*.sql")]
    assert numbers == [MIGRATION_PATH.name], numbers


# ── 5. the regression is committed and covers every branch ────────────────

REGRESSION = (
    _ROOT / "app" / "supabase" / "tests"
    / "regression_308_venn_and_english_retire_audit.sql"
)


def test_the_behavioural_regression_is_committed():
    sql = REGRESSION.read_text()
    assert "308_gir_venn_diagram_and_english_duplicate_audit.sql" in sql
    # Twice for idempotency, once against an emptied tree.
    assert sql.count("\\i app/supabase/migrations/308_") == 3
    assert "regression 308: all assertions passed" in sql
    assert "absent-tree apply is a no-op" in sql


@pytest.mark.parametrize("claim", [
    "the audit removed a referenced EWP row",
    "pronoun-reference had no references and was not retired",
    "mastery row(s) were cascaded away",
    "EWP mapping(s) now dangle",
    "the child topic was cascaded away",
    "the composite-FK row was lost",
    "expected exactly 1 retired row",
])
def test_the_regression_exercises_every_branch(claim):
    """Including the DELETE branch: a fixture where nothing is ever deletable
    would pass with the delete broken."""
    assert claim in REGRESSION.read_text()


def test_the_regression_fixture_carries_a_cascading_fk():
    """The hazard is not the FK that raises — it is the seventeen that cascade
    and take a learner's history with them without a word."""
    sql = REGRESSION.read_text()
    assert "REFERENCES public.topics(id) ON DELETE CASCADE" in sql
    assert "user_topic_mastery" in sql


# ── 6. the duplicate-pair report is corrected, not quietly left wrong ─────

REPORT_PATH = (_ROOT / "workbench" / "reports"
               / "ENGLISH-CATALOGUE-DUPLICATE-PAIRS-2026-09-23.md")


def test_the_report_carries_the_correction_at_the_top():
    """A report whose central finding is wrong and whose merge plan is still
    the first thing an operator reads is worse than no report."""
    report = REPORT_PATH.read_text()
    head = report[:report.index("## 1.")]
    assert "CORRECTION" in head
    assert "THE CENTRAL FINDING BELOW IS WRONG" in head
    assert "Do not merge or retire anything" in head
    assert "writing_issue_type_microtopic_map" in head
    assert "two trees in one subject" in head.lower()


def test_the_superseded_merge_plan_says_so_where_it_is():
    """Someone scrolling to §3 for the SQL must hit the supersession first."""
    report = REPORT_PATH.read_text()
    plan = report.split("## 3. Proposed merge plan")[1].split("## 4.")[0]
    assert "SUPERSEDED" in plan
    assert "Do not execute this" in plan


def test_the_correction_names_the_migration_that_establishes_it():
    assert MIGRATION_PATH.name in REPORT_PATH.read_text()


def test_the_original_body_is_left_intact_as_the_record():
    """Evidence records are immutable in this repo; the pre-correction reading
    is what was believed on 2026-09-23 and stays readable."""
    report = REPORT_PATH.read_text()
    for kept in ("### 2.1 Subject-verb agreement", "### 2.4 Prepositions",
                 "### 2.8 Rows that look like pairs and are not",
                 "## 5. Same check on the other two shared catalogues"):
        assert kept in report, kept


def test_the_cascade_count_in_the_correction_matches_the_migration_set():
    """The correction says seventeen FK columns cascade. Recomputed here, so a
    number that drifts fails rather than misleading whoever reads it next."""
    ref = re.compile(
        r"references\s+(?:public\.)?topics\s*\(\s*id\s*\)\s*on\s+delete\s+cascade", re.I)
    columns = set()
    for path in sorted(MIGRATIONS.glob("*.sql")):
        body = "\n".join(l.split("--")[0] for l in path.read_text().splitlines())
        for m in re.finditer(
                r"create\s+table(?:\s+if\s+not\s+exists)?\s+(?:public\.)?(\w+)\s*\((.*?)\n\s*\)\s*;",
                body, re.I | re.S):
            for line in m.group(2).splitlines():
                if ref.search(line):
                    columns.add((m.group(1), line.strip().split()[0].strip('"')))
    assert len(columns) == 17, sorted(columns)
    for table in ("user_topic_mastery", "user_topic_error_patterns",
                  "mock_mastery_shadow", "trap_drill_mastery_shadow",
                  "user_topic_self_assessment"):
        assert any(t == table for t, _ in columns), table
        assert table in REPORT_PATH.read_text()


def test_the_migration_and_the_report_agree_on_the_hazard():
    assert "seventeen FK columns that cascade" in REPORT_PATH.read_text()
    assert "seventeen FK columns that cascade" in MIGRATION
