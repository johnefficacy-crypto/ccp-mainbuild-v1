"""Schema-contract tests for migration 241 (Lane R exam stream schema).

Following the repo's documented convention (see
test_j3_applied_vs_appeared_migration.py): "The repo has no live-DB migration
harness; existing migration tests assert against the migration SQL text."

These pin the integrity contract demanded by the PR #958 checkpost review:
cross-parent trigger enforcement (INSERT + UPDATE), null-safe uniqueness with
no forgeable sentinel, RESTRICT (not CASCADE) references to the canonical
stream identity, RLS, and updated_at triggers. The behavioural apply
(coexistence, duplicate/cross-parent/UPDATE-move rejection) was additionally
exercised end-to-end on an ephemeral PostgreSQL 16 during development; that run
is not reproducible in CI (no Postgres/driver), so its guarantees are pinned
here structurally against the SQL text.
"""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / ".." / "supabase" / "migrations" / "241_exam_streams_schema.sql"
).read_text().lower()


# ── Canonical tables ───────────────────────────────────────────────────────


def test_creates_exam_streams_with_natural_key():
    assert "create table if not exists public.exam_streams" in MIGRATION
    assert "exam_id uuid not null references public.exams(id) on delete cascade" in MIGRATION
    assert "unique (exam_id, stream_key)" in MIGRATION


def test_creates_exam_cycle_streams_with_availability_and_key():
    assert "create table if not exists public.exam_cycle_streams" in MIGRATION
    assert "check (availability in ('offered', 'not_offered', 'expected'))" in MIGRATION
    assert "unique (exam_cycle_id, stream_id)" in MIGRATION


def test_stream_id_added_to_phase_section_coverage():
    for table in ("exam_phases", "exam_phase_sections", "exam_topic_coverage"):
        assert f"alter table public.{table}" in MIGRATION
    # Every stream_id FK reference uses RESTRICT — never CASCADE (P1: retire via
    # is_active, do not erase historical rows on a hard stream delete).
    assert "add column if not exists stream_id uuid references public.exam_streams(id) on delete restrict" in MIGRATION
    assert "public.exam_streams(id) on delete cascade" not in MIGRATION
    # exam_cycle_streams.stream_id is likewise RESTRICT.
    assert "stream_id uuid not null references public.exam_streams(id) on delete restrict" in MIGRATION


# ── Null-safe uniqueness (no forgeable sentinel) ───────────────────────────


def test_uniqueness_is_null_safe_without_zero_uuid_sentinel():
    # The rejected approach used the all-zero UUID as a NULL stand-in; a
    # service-role insert could forge it. Must use NULLS NOT DISTINCT instead.
    assert "nulls not distinct" in MIGRATION
    assert "00000000-0000-0000-0000-000000000000" not in MIGRATION
    for idx in (
        "exam_phases_exam_cycle_stream_slug_uidx",
        "exam_phases_exam_stream_slug_no_cycle_uidx",
        "exam_phase_sections_phase_stream_subject_label_uidx",
        "exam_topic_coverage_cycle_phase_stream_topic_uidx",
        "exam_topic_coverage_exam_phase_stream_topic_uidx",
    ):
        assert idx in MIGRATION


def test_replaces_030_uniqueness_additively():
    # Old 030 phase/coverage indexes dropped; section inline constraint dropped
    # by definition lookup (name-agnostic across environments).
    assert "drop index if exists public.exam_phases_exam_cycle_slug_uidx" in MIGRATION
    assert "drop index if exists public.exam_phases_exam_slug_no_cycle_uidx" in MIGRATION
    assert "drop index if exists public.exam_topic_coverage_cycle_phase_topic_uidx" in MIGRATION
    assert "pg_get_constraintdef(oid) ilike '%(exam_phase_id, subject_id, section_label)%'" in MIGRATION


# ── Cross-parent integrity triggers (fail-closed, INSERT + UPDATE) ─────────


def test_all_four_child_triggers_present_on_insert_and_update():
    fns = (
        "_exam_cycle_streams_check_parent",
        "_exam_phases_check_stream",
        "_exam_phase_sections_check_stream",
        "_exam_topic_coverage_check_stream",
    )
    for fn in fns:
        assert f"create or replace function public.{fn}()" in MIGRATION
    for trg in (
        "trg_exam_cycle_streams_check_parent",
        "trg_exam_phases_check_stream",
        "trg_exam_phase_sections_check_stream",
        "trg_exam_topic_coverage_check_stream",
    ):
        assert trg in MIGRATION
    # Parent reassignment (UPDATE) must be guarded, not only INSERT.
    assert "before insert or update on public.exam_cycle_streams" in MIGRATION
    assert "before insert or update on public.exam_phases" in MIGRATION
    assert "before insert or update on public.exam_phase_sections" in MIGRATION
    assert "before insert or update on public.exam_topic_coverage" in MIGRATION


def test_bidirectional_parent_side_guards_present():
    # The invariant must survive parent-side changes, not only child writes:
    # cycle-stream DELETE / availability demotion, and exam reassignment on the
    # canonical stream / cycle. Parent reads take FOR SHARE (223 race posture).
    assert "for share" in MIGRATION
    assert "create or replace function public._exam_cycle_streams_guard_delete()" in MIGRATION
    assert "before delete on public.exam_cycle_streams" in MIGRATION
    assert "create or replace function public._exam_streams_guard_exam_move()" in MIGRATION
    assert "before update of exam_id on public.exam_streams" in MIGRATION
    assert "create or replace function public._exam_cycles_guard_exam_move()" in MIGRATION
    assert "before update of exam_id on public.exam_cycles" in MIGRATION
    # Demotion / delete of a depended-on pair is rejected.
    assert "cannot demote availability" in MIGRATION
    assert "cannot delete the (cycle=%, stream=%) pair" in MIGRATION


def test_cross_exam_cycle_and_availability_invariants_enforced():
    # Uses the repo's P0422 integrity errcode (as migration 219).
    assert "using errcode = 'p0422'" in MIGRATION
    assert "belong to different exams" in MIGRATION
    # Availability enforced for phases AND for the effective stream below the
    # phase (stream-scoped section / cycle-scoped coverage).
    assert "availability in ('offered', 'expected')" in MIGRATION
    assert "cycle-bound stream phase requires an offered/expected" in MIGRATION
    assert "stream-scoped section requires an offered/expected" in MIGRATION
    assert "cycle-scoped stream coverage requires an offered/expected" in MIGRATION
    # Coverage validates its OWN cycle scope and resolves section through phase.
    assert "cycle % (exam %) does not belong to coverage exam %" in MIGRATION
    assert "section % (exam %) does not belong to coverage exam %" in MIGRATION
    # Stream-conflict guards.
    assert "conflicts with stream-specific parent phase stream" in MIGRATION
    assert "conflicts with stream-specific phase stream" in MIGRATION
    assert "conflicts with stream-specific section stream" in MIGRATION


def test_committed_behavioral_regression_exists():
    reg = (
        Path(__file__).resolve().parents[1]
        / ".." / "supabase" / "tests" / "regression_241_exam_streams_integrity.sql"
    )
    body = reg.read_text().lower()
    # The behavioral regression actually applies rows and exercises the paths
    # the string test cannot (INSERT/UPDATE/DELETE, parent moves, availability).
    for marker in (
        "cross-exam",
        "not_offered rejected",
        "section-without-phase cross-exam",
        "exam reassign with dependents",
        "delete depended-on pair",
        "phase update move cross-exam",
    ):
        assert marker in body


# ── RLS / triggers / reload ────────────────────────────────────────────────


def test_rls_and_updated_at_and_reload():
    assert "alter table public.exam_streams enable row level security" in MIGRATION
    assert "alter table public.exam_cycle_streams enable row level security" in MIGRATION
    assert "exam_streams_read_authenticated" in MIGRATION
    assert "exam_cycle_streams_read_authenticated" in MIGRATION
    assert "for select to authenticated using (true)" in MIGRATION
    for trg in ("exam_streams_updated_at", "exam_cycle_streams_updated_at"):
        assert trg in MIGRATION
    assert "execute function public.tg_set_updated_at()" in MIGRATION
    assert "notify pgrst, 'reload schema';" in MIGRATION


def test_entity_canonicity_never_recruitment_scoped():
    # Streams belong to exam identity, never to recruitment notifications.
    assert "references public.recruitments" not in MIGRATION
    assert "recruitment_id" not in MIGRATION
