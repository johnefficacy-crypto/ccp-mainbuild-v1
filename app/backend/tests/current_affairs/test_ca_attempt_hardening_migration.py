"""Migration 254 contract (GQR-G5a hardening, checkpost #976 round 2) — text-assertion.

Forward migration over the immutable 253: scope shape + scope gate, fail-closed bundle
degradation with membership/bank locks, ordered exact-set, snapshot verification vs the
bank + content-revision freeze, and provenance-complete eligibility. Behavioural proof is
VERIFY DB (validate_ca_attempt_rpcs.sql).
"""
from __future__ import annotations

from pathlib import Path

_SQL = (
    Path(__file__).parents[3] / "supabase/migrations/255_current_affairs_attempt_start_hardening.sql"
).read_text()
_NORM = " ".join(_SQL.lower().split())


def test_is_forward_migration_over_immutable_253():
    # Must ALTER + CREATE OR REPLACE in place — never recreate the landed 253 tables.
    assert "create table" not in _NORM
    assert "alter table public.current_affairs_bundles" in _NORM
    # guard trigger fn + eligibility helper + start.
    assert _NORM.count("create or replace function") == 3


def test_scope_shape_check_added():
    # R2-F1: exact XOR family XOR global.
    assert "add constraint cab_scope_shape check (exam_id is null or exam_family_id is null)" in _NORM


def test_restrict_fks_prevent_silent_shrink_and_scope_widen():
    # R3-F1: membership FK RESTRICT (bank delete can't shrink a bundle).
    assert ("add constraint current_affairs_bundle_questions_mock_question_id_fkey "
            "foreign key (mock_question_id) references public.mock_question_bank(id) on delete restrict") in _NORM
    # R3-F4: scope FKs RESTRICT (exam/family delete can't widen a published bundle).
    assert "references public.exams(id) on delete restrict" in _NORM
    assert "references public.exam_families(id) on delete restrict" in _NORM
    # R3-F4: attempt.exam_id becomes a real FK.
    assert "current_affairs_attempts_exam_id_fkey" in _NORM


def test_membership_is_locked_while_published():
    # R3-F1: membership mutation forced through draft → republish.
    assert "bundle_membership_locked_when_published" in _NORM
    assert "create trigger ca_bundle_membership_guard" in _NORM


def test_start_binds_membership_revision_and_verifies_content():
    start = _NORM.split("function public.ca_start_current_affairs_attempt")[1]
    # R2-F1 scope gate.
    assert "bundle_scope_mismatch" in start
    assert "exam_family_id into v_family from public.exams" in start
    # R2/R3-F1 locks (membership + bank + options), degradation, ordered set, revision.
    assert "current_affairs_bundle_questions where bundle_id = p_bundle for update" in start
    assert "mock_question_options" in start and "for update" in start
    assert "bundle_degraded" in start
    assert "with ordinality" in start
    assert "membership_revision" in start and "md5(" in start
    # R2/R3-F2 content verified vs bank (text + answer + option id+text) + content revision.
    assert "snapshot_text_mismatch" in start
    assert "snapshot_answer_mismatch" in start
    assert "snapshot_options_mismatch" in start
    assert "content_revision" in start


def test_eligibility_proves_full_provenance_integrity():
    # R3-F3: event-consistency + verified/current claim + active/relevant event + active
    # non-discovery source — not mere existence.
    helper = _NORM.split("function public.ca_eligible_bundle_question_ids")[1]
    assert "ql.event_id = q.current_affairs_item_id" in helper
    assert "cl.event_id = q.current_affairs_item_id" in helper
    assert "cl.reviewer_status = 'verified'" in helper
    assert "cl.factual_status = 'current'" in helper
    assert "ev.status = 'active'" in helper
    assert "s.is_active = true" in helper
    assert "authority_level in ('primary_official', 'official_secondary')" in helper


def test_security_definer_search_path_preserved():
    assert _NORM.count("security definer set search_path = public") >= 3
