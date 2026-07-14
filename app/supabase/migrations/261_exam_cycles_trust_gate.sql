-- 261_exam_cycles_trust_gate.sql
--
-- Enforcement prerequisite 2 of docs/architecture/regulatory-eligibility-authoring-spec.md
-- ("No trust gate on exam_cycles"). Until this lands, exam_cycles has NO review
-- column, the exam_cycles_read_authenticated policy (035) grants every
-- authenticated user read, and study_os/exam_target_window.py + planner +
-- mission-control + plan-timeline consume every non-`cancelled` cycle — so any
-- newly authored cycle row is IMMEDIATELY live to aspirants. This migration adds
-- a draft/reviewed/verified review lifecycle, reviewer attribution, an atomic
-- CAS-based SECURITY DEFINER review RPC, a verified-only authenticated RLS read
-- policy, and a direct-update block trigger so a verified cycle's reviewed
-- content cannot be mutated without demoting it first.
--
-- Two-step promotion: draft -> reviewed -> verified (no draft -> verified jump);
-- reviewed/verified -> draft demotes and clears the reviewer stamp. Promotion to
-- verified requires reviewer separation (the reviewer must differ from the
-- cycle's created_by) and FAILS CLOSED when authorship is absent.
--
-- Legacy safety: exam_cycles had NO prior review column, so every existing cycle
-- was implicitly trusted and is relied on by live aspirant Study OS. This
-- migration GRANDFATHERS every pre-existing cycle to reviewer_status='verified'
-- exactly once (only when the column is first created, so a re-apply is a
-- no-op), with reviewer attribution left NULL to mark them legacy-grandfathered.
-- The column DEFAULT is 'draft', so every FUTURE insert must earn trust through
-- the review RPC. No existing live cycle is hidden by this change — only newly
-- authored cycles are gated. No regulator cycles should be authored before this
-- lands.
--
-- DO NOT apply to production without staging sign-off.
-- DO NOT edit landed migrations.


-- ── A. Review lifecycle columns + one-time legacy grandfather ────────────────
--
-- The column is created and back-filled inside a single guarded block so the
-- grandfather UPDATE runs ONLY on the first apply (when the column does not yet
-- exist). A second apply finds the column present, skips the block, and never
-- re-verifies rows drafted since — the migration stays idempotent (no blanket
-- UPDATE of existing rows on re-apply).
do $$
declare
  v_col_exists boolean;
begin
  select exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name   = 'exam_cycles'
      and column_name  = 'reviewer_status'
  ) into v_col_exists;

  if not v_col_exists then
    alter table public.exam_cycles
      add column reviewer_status text not null default 'draft';
    -- Grandfather every PRE-EXISTING cycle as already-trusted so live aspirant
    -- Study OS is not blacked out. Runs once, only on first apply.
    update public.exam_cycles set reviewer_status = 'verified';
  end if;
end $$;

alter table public.exam_cycles
  drop constraint if exists exam_cycles_reviewer_status_check;
alter table public.exam_cycles
  add constraint exam_cycles_reviewer_status_check
  check (reviewer_status in ('draft', 'reviewed', 'verified'));

-- Reviewer attribution (who advanced the row to its current review state) and
-- authorship (for reviewer separation). Both FK -> auth.users, both NULLable.
alter table public.exam_cycles
  add column if not exists reviewed_by uuid
    references auth.users(id) on delete set null;
alter table public.exam_cycles
  add column if not exists reviewed_at timestamptz;
alter table public.exam_cycles
  add column if not exists created_by uuid
    references auth.users(id) on delete set null;

create index if not exists idx_exam_cycles_reviewer_status
  on public.exam_cycles(reviewer_status);

comment on column public.exam_cycles.reviewer_status is
  'Trust gate (migration 261): draft -> reviewed -> verified. Only verified '
  'cycles are readable by authenticated aspirants (RLS) and consumed by Study OS '
  '(exam_target_window / planner / mission-control / plan-timeline). New rows '
  'default draft; promotion is only possible through review_exam_cycle().';


-- ── B. Verified-only authenticated read policy ───────────────────────────────
--
-- Replaces the permissive 035 exam_cycles_read_authenticated (using true).
-- Authenticated aspirants see only verified cycles; admins keep full read (they
-- also retain the 035 exam_cycles_admin_all FOR ALL policy). The canonical
-- public.is_admin(auth.uid()) predicate reads auth app metadata (migration 195);
-- profiles.is_admin is deprecated and must not be reintroduced.
drop policy if exists exam_cycles_read_authenticated on public.exam_cycles;
drop policy if exists exam_cycles_read_verified on public.exam_cycles;
create policy exam_cycles_read_verified on public.exam_cycles
  for select to authenticated
  using (
    reviewer_status = 'verified'
    or public.is_admin(auth.uid())
  );


-- ── C. Direct-update protection: a reviewed or verified cycle's REVIEWED
--     CONTENT cannot be mutated while retaining an earned review state. Any such
--     edit must demote the row to draft in the same statement. This is the DB
--     backstop for every application write path's demote-on-material-edit rule.
--     Source provenance and metadata are reviewed content too. Operational
--     `status` (expected/open/active/closed/…) and the separate
--     planner_activation_enabled exposure flag are deliberately NOT watched —
--     they are legitimate lifecycle/exposure controls, not reviewed content.
create or replace function public._exam_cycles_block_verified_material_edit()
returns trigger
language plpgsql as $fn$
begin
  if old.reviewer_status in ('reviewed', 'verified')
     and new.reviewer_status is distinct from 'draft'
     and (
          old.exam_id           is distinct from new.exam_id
       or old.year              is distinct from new.year
       or old.cycle_name        is distinct from new.cycle_name
       or old.notification_date is distinct from new.notification_date
       or old.application_start is distinct from new.application_start
       or old.application_end   is distinct from new.application_end
       or old.exam_start        is distinct from new.exam_start
       or old.exam_end          is distinct from new.exam_end
       or old.source_url        is distinct from new.source_url
       or old.metadata          is distinct from new.metadata
     ) then
    raise exception
      'exam_cycles: cannot mutate reviewed content of a reviewed or verified cycle '
      'without demoting it to draft'
      using errcode = 'P0422';
  end if;
  return new;
end;
$fn$;

drop trigger if exists trg_exam_cycles_block_verified_material_edit on public.exam_cycles;
create trigger trg_exam_cycles_block_verified_material_edit
  before update on public.exam_cycles
  for each row execute function public._exam_cycles_block_verified_material_edit();


-- ── D. review_exam_cycle() — atomic SECURITY DEFINER review RPC ───────────────
--
-- Mirrors review_exam_eligibility_rule (migration 257): reason length gate,
-- target-status validation, row lock, CAS on expected reviewer_status, transition
-- matrix, reviewer separation for -> verified, and an audit row in the SAME
-- transaction. Moving to draft clears the reviewer stamp.
--
-- Transitions:
--   draft    -> reviewed
--   reviewed -> verified | draft
--   verified -> reviewed | draft
--
-- reviewed -> verified additionally requires:
--   • created_by present on the cycle (else creator_missing — fail closed)
--   • reviewer actor differs from created_by (else reviewer_is_creator)
create or replace function public.review_exam_cycle(
    p_cycle_id        text,
    p_expected_status text,
    p_target_status   text,
    p_reason          text,
    p_actor_id        text,
    p_actor_email     text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_cycle          exam_cycles%ROWTYPE;
    v_audit_id       uuid;
    v_updated        exam_cycles%ROWTYPE;
    v_reason_trimmed text;
BEGIN
    -- 1. Reason length gate (explicit NULL guard: trim(NULL)/length(NULL) are NULL).
    IF p_reason IS NULL THEN
        RAISE EXCEPTION 'invalid_reason: reason must not be null' USING ERRCODE = 'P0422';
    END IF;
    v_reason_trimmed := trim(p_reason);
    IF length(v_reason_trimmed) < 8 OR length(v_reason_trimmed) > 500 THEN
        RAISE EXCEPTION 'invalid_reason: reason must be 8-500 characters (got %)',
            length(v_reason_trimmed) USING ERRCODE = 'P0422';
    END IF;

    -- 2. Target status must be a known value.
    IF p_target_status NOT IN ('draft', 'reviewed', 'verified') THEN
        RAISE EXCEPTION 'invalid_target_status: % is not a recognised reviewer_status',
            p_target_status USING ERRCODE = 'P0422';
    END IF;

    -- 3. Lock the cycle row.
    SELECT * INTO v_cycle
    FROM public.exam_cycles
    WHERE id = p_cycle_id::uuid
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: exam_cycle % does not exist', p_cycle_id
            USING ERRCODE = 'P0404';
    END IF;

    -- 4. Concurrent-modification guard.
    IF v_cycle.reviewer_status IS DISTINCT FROM p_expected_status THEN
        RAISE EXCEPTION 'concurrent_modification: expected reviewer_status=% but found %. Re-fetch and retry.',
            p_expected_status, v_cycle.reviewer_status USING ERRCODE = 'P0409';
    END IF;

    -- 5. Transition matrix (two-step promotion: draft -> reviewed -> verified).
    IF NOT (
           (v_cycle.reviewer_status = 'draft'    AND p_target_status = 'reviewed')
        OR (v_cycle.reviewer_status = 'reviewed' AND p_target_status IN ('verified', 'draft'))
        OR (v_cycle.reviewer_status = 'verified' AND p_target_status IN ('reviewed', 'draft'))
    ) THEN
        RAISE EXCEPTION 'transition_not_allowed: % -> % is not a permitted transition',
            v_cycle.reviewer_status, p_target_status USING ERRCODE = 'P0422';
    END IF;

    -- 6. Reviewer separation for -> verified. FAILS CLOSED when creator
    --    attribution is absent — a cycle with no created_by cannot prove a second
    --    reviewer, so it is not promotable to verified.
    IF p_target_status = 'verified' THEN
        IF v_cycle.created_by IS NULL THEN
            RAISE EXCEPTION 'creator_missing: cycle has no created_by; cannot establish reviewer separation'
                USING ERRCODE = 'P0422';
        END IF;
        IF v_cycle.created_by::text = p_actor_id THEN
            RAISE EXCEPTION 'reviewer_is_creator: the cycle author cannot verify their own cycle'
                USING ERRCODE = 'P0422';
        END IF;
    END IF;

    -- 7. Audit row in the same transaction.
    INSERT INTO public.admin_audit_logs (
        actor_id, actor_email, action, entity_type, entity_id, new_value, notes
    )
    VALUES (
        p_actor_id::uuid,
        p_actor_email,
        'exam_intel.cms.cycle.review',
        'exam_cycle',
        p_cycle_id,
        jsonb_build_object(
            'from_status', p_expected_status,
            'to_status',   p_target_status,
            'reason',      v_reason_trimmed,
            'reviewed_by', p_actor_email,
            'reviewed_at', now()::text
        ),
        'admin_exam_intel_cms'
    )
    RETURNING id INTO v_audit_id;

    -- 8. Apply the status change + reviewer attribution atomically. Moving to
    --    draft clears the reviewer stamp; reviewed/verified stamp the actor.
    IF p_target_status = 'draft' THEN
        UPDATE public.exam_cycles
        SET    reviewer_status = p_target_status,
               reviewed_by      = NULL,
               reviewed_at      = NULL,
               updated_at       = now()
        WHERE  id = p_cycle_id::uuid
        AND    reviewer_status = p_expected_status
        RETURNING * INTO v_updated;
    ELSE
        UPDATE public.exam_cycles
        SET    reviewer_status = p_target_status,
               reviewed_by      = p_actor_id::uuid,
               reviewed_at      = now(),
               updated_at       = now()
        WHERE  id = p_cycle_id::uuid
        AND    reviewer_status = p_expected_status
        RETURNING * INTO v_updated;
    END IF;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'concurrent_modification: zero rows updated after lock'
            USING ERRCODE = 'P0409';
    END IF;

    RETURN jsonb_build_object(
        'ok', true, 'audit_id', v_audit_id, 'row', to_jsonb(v_updated)
    );
END;
$$;

REVOKE EXECUTE ON FUNCTION public.review_exam_cycle(text, text, text, text, text, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.review_exam_cycle(text, text, text, text, text, text) FROM anon;
REVOKE EXECUTE ON FUNCTION public.review_exam_cycle(text, text, text, text, text, text) FROM authenticated;
GRANT  EXECUTE ON FUNCTION public.review_exam_cycle(text, text, text, text, text, text) TO service_role;


notify pgrst, 'reload schema';
