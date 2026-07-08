-- 233_pyq_stimuli_media_assets.sql
-- PYQ v2 PR-11 (advanced question types & media), slice 1: first-class media
-- storage for stimuli.
--
-- Migration 223 shipped shared text stimuli (passage/caselet/table) but
-- explicitly deferred "first-class media storage (FK to document_assets,
-- locators, alt-text)" to PR-11. This migration lands exactly that on
-- public.pyq_stimuli:
--   * document_asset_id — FK to the stored image/chart/diagram asset,
--   * asset_locator     — jsonb page/region locator (page_number, bbox, …),
--   * alt_text          — accessibility contract (WCAG) for the media.
--
-- Governance (mirrors the 223 posture):
--   * Asset integrity: a linked document_asset must be a live
--     admin_exam_intelligence asset (not archived) — mirrors migration 186's
--     provenance validation for pyq_papers.source_document_id.
--   * Fail-closed accessibility: a media stimulus (image/chart/diagram) cannot
--     be reviewer_status='verified' without alt_text and actual content
--     (content_text or a linked asset). Enforced on INSERT and UPDATE.
--   * Re-review on media edit: the existing verified-content downgrade
--     (migration 223) is extended so editing alt_text / document_asset_id /
--     asset_locator on a verified stimulus forces it back to needs_correction.
--
-- Additive + idempotent: every column is nullable/defaulted; no importer or
-- projection contract is changed here (those are later PR-11 slices).

alter table public.pyq_stimuli
  add column if not exists document_asset_id uuid references public.document_assets(id) on delete set null,
  add column if not exists asset_locator jsonb not null default '{}'::jsonb,
  add column if not exists alt_text text;

create index if not exists idx_pyq_stimuli_document_asset
  on public.pyq_stimuli(document_asset_id)
  where document_asset_id is not null;

-- ── Media integrity + fail-closed accessibility ────────────────────────────
create or replace function public.pyq_stimuli_media_guard()
returns trigger
language plpgsql
as $fn$
declare
  v_scope text;
  v_status text;
  v_kind text;
  v_is_media boolean := new.stimulus_type in ('image', 'chart', 'diagram');
begin
  -- 1. A linked asset must be a live admin_exam_intelligence IMAGE document.
  --    image/chart/diagram media are stored as image binaries, so the asset's
  --    document_kind must be 'image'; a non-media kind (pyq_paper, syllabus,
  --    answer_key, text_file, other, …) is rejected. Bad statuses (failed /
  --    archived) are rejected too — matches the provenance posture used for
  --    pyq_papers.source_document_id (migrations 186/187).
  if new.document_asset_id is not null then
    select scope, status, document_kind into v_scope, v_status, v_kind
      from public.document_assets where id = new.document_asset_id for share;
    if v_scope is null then
      raise exception 'pyq_stimuli.document_asset_id % not found', new.document_asset_id;
    end if;
    if v_scope <> 'admin_exam_intelligence' then
      raise exception 'pyq_stimuli.document_asset_id % has scope % (expected admin_exam_intelligence)',
        new.document_asset_id, v_scope;
    end if;
    if v_status in ('failed', 'archived') then
      raise exception 'pyq_stimuli.document_asset_id % has unusable status %', new.document_asset_id, v_status;
    end if;
    if v_kind <> 'image' then
      raise exception 'pyq_stimuli.document_asset_id % has document_kind % (media stimuli require an image asset)',
        new.document_asset_id, v_kind;
    end if;
  end if;

  -- 2. Fail-closed accessibility + renderability: a media stimulus cannot be
  --    verified without alt-text AND a linked image asset. content_text is NOT
  --    a substitute — the media renderer (QuestionStimuli) shows the asset or
  --    the alt-text fallback for image/chart/diagram and never renders
  --    content_text, so a content_text-only "verified" media stimulus would
  --    reach attempts with its actual content omitted (checkpost PR #910, P2).
  if new.reviewer_status = 'verified' and v_is_media then
    if new.alt_text is null or btrim(new.alt_text) = '' then
      raise exception 'media_stimulus_requires_alt_text: % stimulus % cannot be verified without alt_text',
        new.stimulus_type, new.id;
    end if;
    if new.document_asset_id is null then
      raise exception 'media_stimulus_requires_asset: % stimulus % cannot be verified without a linked image asset (content_text is not rendered for media)',
        new.stimulus_type, new.id;
    end if;
  end if;

  return new;
end;
$fn$;

drop trigger if exists trg_pyq_stimuli_media_guard on public.pyq_stimuli;
create trigger trg_pyq_stimuli_media_guard
  before insert or update on public.pyq_stimuli
  for each row execute function public.pyq_stimuli_media_guard();

-- ── Extend the 223 verified-content downgrade to cover the media fields ─────
create or replace function public.pyq_downgrade_stimulus_review_on_content_edit()
returns trigger
language plpgsql
as $fn$
begin
  if old.reviewer_status = 'verified'
     and new.reviewer_status is not distinct from old.reviewer_status
     and (
       new.content_text is distinct from old.content_text
       or new.stimulus_type is distinct from old.stimulus_type
       or new.language is distinct from old.language
       or new.metadata is distinct from old.metadata
       or new.alt_text is distinct from old.alt_text
       or new.document_asset_id is distinct from old.document_asset_id
       or new.asset_locator is distinct from old.asset_locator
     )
  then
    new.reviewer_status := 'needs_correction';
    new.reviewed_by := null;
    new.reviewed_at := null;
  end if;

  return new;
end;
$fn$;

drop trigger if exists trg_pyq_stimuli_downgrade_on_content_edit on public.pyq_stimuli;
create trigger trg_pyq_stimuli_downgrade_on_content_edit
  before update of content_text, stimulus_type, language, metadata,
    alt_text, document_asset_id, asset_locator on public.pyq_stimuli
  for each row execute function public.pyq_downgrade_stimulus_review_on_content_edit();

notify pgrst, 'reload schema';
