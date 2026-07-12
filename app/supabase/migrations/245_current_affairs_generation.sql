-- 245_current_affairs_generation.sql
-- GQR-G3 — Current-affairs LLM generation (SHADOW / no authority).
--
-- Adds the generation-audit table, the question-candidate staging table, and a
-- lease+fencing job queue with claim/complete/fail/sweep RPCs, mirroring the EWP
-- writing_evaluation_jobs pattern (migrations 205/207/209). Everything here is
-- shadow: candidates land in staging with a deterministic validation verdict + a
-- full generation audit; NOTHING promotes, publishes, or writes mock_question_bank.
-- Promotion into the objective bank is GQR-G4/G5, behind the operator human gate.
--
-- Service-role only: RLS enabled with no client allow-policy; per-RPC EXECUTE and
-- table CRUD granted to service_role only (SECURITY DEFINER, search_path=public).

begin;

-- ── 1. generation audit (append-only) ──────────────────────────────────────
create table if not exists public.current_affairs_generation_runs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references public.current_affairs_documents(id) on delete set null,
  event_id uuid references public.current_affairs_events(id) on delete set null,
  candidate_id uuid,
  action text not null
    check (action in ('extraction', 'mcq_generation', 'verification')),
  status text not null default 'succeeded',
  provider text,
  model text,
  prompt_version text,
  adapter_version text,
  input_hash text,
  output_hash text,
  input_tokens integer,
  output_tokens integer,
  total_tokens integer,
  estimated_cost_usd numeric,
  latency_ms integer,
  error text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_cagr_document on public.current_affairs_generation_runs(document_id);
create index if not exists idx_cagr_event on public.current_affairs_generation_runs(event_id);
create index if not exists idx_cagr_action on public.current_affairs_generation_runs(action);

-- Append-only: forbid update/delete (audit integrity, mirrors EWP evaluator runs).
create or replace function public.ca_forbid_generation_run_mutation()
returns trigger language plpgsql as $$
begin
  raise exception 'current_affairs_generation_runs is append-only';
end $$;
drop trigger if exists trg_ca_generation_runs_immutable on public.current_affairs_generation_runs;
create trigger trg_ca_generation_runs_immutable
  before update or delete on public.current_affairs_generation_runs
  for each row execute function public.ca_forbid_generation_run_mutation();

-- ── 2. question candidates (staging; never the objective bank) ──────────────
create table if not exists public.current_affairs_question_candidates (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.current_affairs_events(id) on delete cascade,
  question_payload jsonb not null,
  question_fingerprint text,
  generator_run_id uuid references public.current_affairs_generation_runs(id) on delete set null,
  verifier_run_id uuid references public.current_affairs_generation_runs(id) on delete set null,
  validation_result jsonb not null default '{}'::jsonb,
  verifier_verdict jsonb not null default '{}'::jsonb,
  status text not null default 'generated'
    check (status in ('generated', 'validation_failed', 'review_ready', 'approved', 'rejected', 'promoted')),
  reviewed_by uuid,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_caqc_event on public.current_affairs_question_candidates(event_id);
create index if not exists idx_caqc_status on public.current_affairs_question_candidates(status);
-- Dedup guard: a question fingerprint is unique across candidates (non-null only).
create unique index if not exists uq_caqc_fingerprint
  on public.current_affairs_question_candidates(question_fingerprint)
  where question_fingerprint is not null;

-- ── 3. generation job queue (lease + fencing) ──────────────────────────────
create table if not exists public.current_affairs_generation_jobs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.current_affairs_documents(id) on delete cascade,
  job_kind text not null default 'ca_generation' check (job_kind in ('ca_generation')),
  generation integer not null default 1 check (generation > 0),
  status text not null default 'pending' check (status in ('pending', 'running', 'done', 'failed')),
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 3 check (max_attempts > 0),
  scheduled_for timestamptz,
  locked_at timestamptz,
  claim_token uuid,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (document_id, job_kind, generation),
  check (attempts <= max_attempts),
  constraint ca_generation_jobs_running_lease_ck check (
    status <> 'running' or (locked_at is not null and claim_token is not null)
  )
);
-- One in-flight job per document (single-in-flight, mirrors EWP active index).
create unique index if not exists uq_ca_generation_jobs_active
  on public.current_affairs_generation_jobs(document_id, job_kind)
  where status in ('pending', 'running');
create index if not exists idx_ca_generation_jobs_claimable
  on public.current_affairs_generation_jobs(status, scheduled_for);

-- ── 4. RLS: enable, no client allow-policy (service-role only) ──────────────
do $$
declare t text;
begin
  foreach t in array array[
    'current_affairs_generation_runs',
    'current_affairs_question_candidates',
    'current_affairs_generation_jobs'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from public', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('revoke all on public.%I from authenticated', t);
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
  end loop;
end $$;

-- ── 5. Enqueue (producer) ──────────────────────────────────────────────────
-- Insert a pending generation job for a snapshotted document. The active partial
-- index makes this single-in-flight; a duplicate returns the existing job id.
create or replace function public.ca_enqueue_generation_job(p_document_id uuid)
returns uuid
language plpgsql security definer set search_path = public as $$
declare v_id uuid;
begin
  select id into v_id from public.current_affairs_generation_jobs
  where document_id = p_document_id and job_kind = 'ca_generation'
    and status in ('pending', 'running')
  limit 1;
  if v_id is not null then
    return v_id;
  end if;
  insert into public.current_affairs_generation_jobs(document_id, job_kind, generation, status)
  values (p_document_id, 'ca_generation', 1, 'pending')
  returning id into v_id;
  return v_id;
end $$;

-- ── 6. Claim (FOR UPDATE SKIP LOCKED + lease + fencing token) ───────────────
create or replace function public.ca_claim_generation_job(
  p_lease_seconds integer default 900,
  p_job_kinds text[] default array['ca_generation']
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_job public.current_affairs_generation_jobs%rowtype;
  v_token uuid := gen_random_uuid();
  v_doc public.current_affairs_documents%rowtype;
  v_src public.current_affairs_sources%rowtype;
  v_fps text[];
begin
  select * into v_job from public.current_affairs_generation_jobs j
  where j.status = 'pending'
    and j.job_kind = any(p_job_kinds)
    and (j.scheduled_for is null or j.scheduled_for <= now())
  order by j.created_at
  for update skip locked
  limit 1;
  if not found then
    return null;
  end if;

  update public.current_affairs_generation_jobs
  set status = 'running', locked_at = now(), claim_token = v_token,
      attempts = attempts + 1, updated_at = now()
  where id = v_job.id;

  select * into v_doc from public.current_affairs_documents where id = v_job.document_id;
  select * into v_src from public.current_affairs_sources where id = v_doc.source_id;

  -- Existing candidate fingerprints so the deterministic validator can flag a
  -- duplicate before it reaches the unique index (bounded).
  select coalesce(array_agg(question_fingerprint), array[]::text[]) into v_fps
  from (
    select question_fingerprint from public.current_affairs_question_candidates
    where question_fingerprint is not null
    order by created_at desc limit 5000
  ) f;

  return jsonb_build_object(
    'job_id', v_job.id,
    'claim_token', v_token,
    'job_kind', v_job.job_kind,
    'generation', v_job.generation,
    'attempts', v_job.attempts + 1,
    'max_attempts', v_job.max_attempts,
    'document', jsonb_build_object(
      'id', v_doc.id,
      'source_id', v_doc.source_id,
      'title', v_doc.title,
      'raw_text', v_doc.raw_text,
      'document_type', v_doc.document_type,
      'category', coalesce(v_src.default_category, null),
      'published_at', v_doc.published_at,
      'fetched_at', v_doc.fetched_at
    ),
    'source_authority_level', v_src.authority_level,
    'existing_fingerprints', to_jsonb(v_fps)
  );
end $$;

-- ── 6b. Generation-run insert helper (append-only audit row) ───────────────
create or replace function public._ca_insert_generation_run(
  p_document_id uuid,
  p_event_id uuid,
  p_candidate_id uuid,
  p_action text,
  p_run jsonb,
  p_adapter_version text
) returns uuid
language plpgsql security definer set search_path = public as $$
declare v_id uuid;
begin
  insert into public.current_affairs_generation_runs(
    document_id, event_id, candidate_id, action, status, provider, model,
    prompt_version, adapter_version, input_hash, output_hash, input_tokens,
    output_tokens, total_tokens, estimated_cost_usd, latency_ms, error)
  values (
    p_document_id, p_event_id, p_candidate_id,
    coalesce(p_run->>'action', p_action),
    coalesce(p_run->>'status', 'succeeded'),
    p_run->>'provider', p_run->>'model', p_run->>'prompt_version', p_adapter_version,
    p_run->>'input_hash', p_run->>'output_hash',
    nullif(p_run->>'input_tokens', '')::int, nullif(p_run->>'output_tokens', '')::int,
    nullif(p_run->>'total_tokens', '')::int, nullif(p_run->>'estimated_cost_usd', '')::numeric,
    nullif(p_run->>'latency_ms', '')::int, p_run->>'error')
  returning id into v_id;
  return v_id;
end $$;

-- ── 7. Complete (fencing re-check + replay guard + atomic persist + ack) ────
create or replace function public.ca_complete_generation(
  p_job_id uuid,
  p_claim_token uuid,
  p_document_id uuid,
  p_events jsonb,
  p_generation_runs jsonb default '[]'::jsonb,
  p_adapter_version text default null
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_job public.current_affairs_generation_jobs%rowtype;
  v_event jsonb;
  v_claim jsonb;
  v_ev jsonb;
  v_cand jsonb;
  v_run jsonb;
  v_event_id uuid;
  v_claim_id uuid;
  v_cand_id uuid;
  v_gen_run_id uuid;
  v_ver_run_id uuid;
  v_claim_map jsonb := '{}'::jsonb;   -- temp_id -> claim uuid
  v_linked uuid[];
  v_tid text;
  v_events_written int := 0;
  v_candidates_written int := 0;
begin
  select * into v_job from public.current_affairs_generation_jobs
  where id = p_job_id for update;
  if not found then
    raise exception 'ca_job_not_found: %', p_job_id;
  end if;
  -- Replay guard FIRST (idempotent ack): a successful completion clears claim_token
  -- and marks the job 'done', so a retry with the original token would otherwise trip
  -- the fencing branch below. An already-acked job is a side-effect-free no-op.
  if v_job.status = 'done' then
    return jsonb_build_object('status', 'replayed', 'job_id', p_job_id);
  end if;
  -- Fencing re-check (§8.3): only the current lease holder may complete a live job.
  if v_job.status <> 'running' or v_job.claim_token is distinct from p_claim_token then
    raise exception 'ca_job_fencing_failed: job=% status=%', p_job_id, v_job.status;
  end if;

  for v_event in select * from jsonb_array_elements(coalesce(p_events, '[]'::jsonb)) loop
    -- Event: reuse an existing fingerprint (idempotent), else insert.
    v_event_id := null;
    if v_event->>'event_fingerprint' is not null then
      select id into v_event_id from public.current_affairs_events
      where event_fingerprint = v_event->>'event_fingerprint';
    end if;
    if v_event_id is null then
      insert into public.current_affairs_events(
        canonical_title, event_date, category, event_fingerprint,
        editorial_importance, relevance_from, relevance_until, status)
      values (
        v_event->>'canonical_title',
        nullif(v_event->>'event_date', '')::date,
        v_event->>'category',
        v_event->>'event_fingerprint',
        coalesce(v_event->>'editorial_importance', 'normal'),
        nullif(v_event->>'relevance_from', '')::date,
        nullif(v_event->>'relevance_until', '')::date,
        'active')
      returning id into v_event_id;
    end if;
    v_events_written := v_events_written + 1;

    -- Claims (reviewer_status='pending' — SHADOW; never verified here) + evidence.
    for v_claim in select * from jsonb_array_elements(coalesce(v_event->'claims', '[]'::jsonb)) loop
      insert into public.current_affairs_claims(
        event_id, claim_text, claim_fingerprint, factual_status, reviewer_status)
      values (
        v_event_id, v_claim->>'claim_text', v_claim->>'claim_fingerprint',
        coalesce(v_claim->>'factual_status', 'current'), 'pending')
      returning id into v_claim_id;
      v_claim_map := v_claim_map || jsonb_build_object(v_claim->>'temp_id', v_claim_id::text);

      for v_ev in select * from jsonb_array_elements(coalesce(v_claim->'evidence', '[]'::jsonb)) loop
        insert into public.current_affairs_claim_evidence(
          claim_id, document_id, evidence_text, start_offset, end_offset, evidence_role)
        values (
          v_claim_id,
          nullif(v_ev->>'document_id', '')::uuid,
          v_ev->>'evidence_text',
          nullif(v_ev->>'start_offset', '')::int,
          nullif(v_ev->>'end_offset', '')::int,
          coalesce(v_ev->>'evidence_role', 'supporting'))
        on conflict (claim_id, document_id, start_offset, end_offset) do nothing;
      end loop;
    end loop;

    -- Candidates: resolve temp claim ids → uuids; dedup on fingerprint; persist the
    -- Stage-B (generator) + Stage-C (verifier) audit rows with candidate lineage in
    -- the SAME transaction, so every candidate is fully traceable (§6).
    for v_cand in select * from jsonb_array_elements(coalesce(v_event->'candidates', '[]'::jsonb)) loop
      v_linked := array[]::uuid[];
      for v_tid in select jsonb_array_elements_text(coalesce(v_cand->'linked_temp_claim_ids', '[]'::jsonb)) loop
        if v_claim_map ? v_tid then
          v_linked := v_linked || (v_claim_map->>v_tid)::uuid;
        end if;
      end loop;

      v_cand_id := null;
      -- Conflict target MUST carry the partial index predicate (uq_caqc_fingerprint is
      -- partial WHERE question_fingerprint IS NOT NULL), else Postgres cannot infer it.
      insert into public.current_affairs_question_candidates(
        event_id, question_payload, question_fingerprint,
        validation_result, verifier_verdict, status)
      values (
        v_event_id,
        (v_cand->'question_payload')
          || jsonb_build_object('resolved_claim_ids', to_jsonb(v_linked)),
        v_cand->>'question_fingerprint',
        coalesce(v_cand->'validation_result', '{}'::jsonb),
        coalesce(v_cand->'verifier_verdict', '{}'::jsonb),
        coalesce(v_cand->>'status', 'generated'))
      on conflict (question_fingerprint) where question_fingerprint is not null do nothing
      returning id into v_cand_id;

      if v_cand_id is not null then
        v_gen_run_id := null;
        v_ver_run_id := null;
        if v_cand->'generator_run' is not null and v_cand->'generator_run' <> 'null'::jsonb then
          v_gen_run_id := public._ca_insert_generation_run(
            p_document_id, v_event_id, v_cand_id, 'mcq_generation',
            v_cand->'generator_run', p_adapter_version);
        end if;
        if v_cand->'verifier_run' is not null and v_cand->'verifier_run' <> 'null'::jsonb then
          v_ver_run_id := public._ca_insert_generation_run(
            p_document_id, v_event_id, v_cand_id, 'verification',
            v_cand->'verifier_run', p_adapter_version);
        end if;
        update public.current_affairs_question_candidates
        set generator_run_id = v_gen_run_id, verifier_run_id = v_ver_run_id, updated_at = now()
        where id = v_cand_id;
        v_candidates_written := v_candidates_written + 1;
      end if;
    end loop;
  end loop;

  -- Document-level generation audit (Stage-A extraction runs; candidate-scoped
  -- generator/verifier runs are persisted inline above with lineage).
  for v_run in select * from jsonb_array_elements(coalesce(p_generation_runs, '[]'::jsonb)) loop
    perform public._ca_insert_generation_run(
      p_document_id, null, null, coalesce(v_run->>'action', 'extraction'),
      v_run, p_adapter_version);
  end loop;

  -- Atomic ack.
  update public.current_affairs_generation_jobs
  set status = 'done', locked_at = null, claim_token = null, updated_at = now()
  where id = p_job_id;

  return jsonb_build_object(
    'status', 'completed', 'job_id', p_job_id,
    'events_written', v_events_written, 'candidates_written', v_candidates_written);
end $$;

-- ── 8. Fail (retry/backoff, terminal at max_attempts) ──────────────────────
create or replace function public.ca_fail_generation_job(
  p_job_id uuid,
  p_claim_token uuid,
  p_error text,
  p_backoff_seconds integer default 60
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_job public.current_affairs_generation_jobs%rowtype;
begin
  select * into v_job from public.current_affairs_generation_jobs where id = p_job_id for update;
  if not found then
    raise exception 'ca_job_not_found: %', p_job_id;
  end if;
  if v_job.status <> 'running' or v_job.claim_token is distinct from p_claim_token then
    raise exception 'ca_job_fencing_failed: job=% status=%', p_job_id, v_job.status;
  end if;

  if v_job.attempts < v_job.max_attempts then
    update public.current_affairs_generation_jobs set
      status = 'pending', locked_at = null, claim_token = null, last_error = p_error,
      scheduled_for = now() + make_interval(secs => p_backoff_seconds), updated_at = now()
    where id = p_job_id;
    return jsonb_build_object('status', 'requeued', 'attempts', v_job.attempts);
  end if;

  update public.current_affairs_generation_jobs set
    status = 'failed', locked_at = null, claim_token = null, last_error = p_error, updated_at = now()
  where id = p_job_id;
  return jsonb_build_object('status', 'failed', 'attempts', v_job.attempts);
end $$;

-- ── 9. Sweep stale leases (crashed/hung worker) ────────────────────────────
create or replace function public.ca_sweep_stale_generation_jobs(p_lease_seconds integer default 900)
returns integer
language plpgsql security definer set search_path = public as $$
declare
  v_id uuid;
  v_count int := 0;
  v_job public.current_affairs_generation_jobs%rowtype;
begin
  for v_id in
    select id from public.current_affairs_generation_jobs
    where status = 'running' and locked_at is not null
      and locked_at < now() - make_interval(secs => p_lease_seconds)
  loop
    select * into v_job from public.current_affairs_generation_jobs where id = v_id for update;
    -- Re-validate under lock (a completing worker may have fenced this out).
    if v_job.status = 'running' and v_job.locked_at is not null
       and v_job.locked_at < now() - make_interval(secs => p_lease_seconds) then
      if v_job.attempts >= v_job.max_attempts then
        update public.current_affairs_generation_jobs set
          status = 'failed', locked_at = null, claim_token = null,
          last_error = 'lease_expired_exhausted', updated_at = now()
        where id = v_id;
      else
        update public.current_affairs_generation_jobs set
          status = 'pending', locked_at = null, claim_token = null,
          last_error = 'lease_expired', updated_at = now()
        where id = v_id;
      end if;
      v_count := v_count + 1;
    end if;
  end loop;
  return v_count;
end $$;

-- ── 10. Grants: service_role only (SECURITY DEFINER RPCs) ──────────────────
-- Internal helper: owner-only (called within the SECURITY DEFINER complete RPC);
-- never externally callable.
revoke all on function public._ca_insert_generation_run(uuid, uuid, uuid, text, jsonb, text) from public, anon, authenticated;

revoke all on function public.ca_enqueue_generation_job(uuid) from public, anon, authenticated;
revoke all on function public.ca_claim_generation_job(integer, text[]) from public, anon, authenticated;
revoke all on function public.ca_complete_generation(uuid, uuid, uuid, jsonb, jsonb, text) from public, anon, authenticated;
revoke all on function public.ca_fail_generation_job(uuid, uuid, text, integer) from public, anon, authenticated;
revoke all on function public.ca_sweep_stale_generation_jobs(integer) from public, anon, authenticated;

grant execute on function public.ca_enqueue_generation_job(uuid) to service_role;
grant execute on function public.ca_claim_generation_job(integer, text[]) to service_role;
grant execute on function public.ca_complete_generation(uuid, uuid, uuid, jsonb, jsonb, text) to service_role;
grant execute on function public.ca_fail_generation_job(uuid, uuid, text, integer) to service_role;
grant execute on function public.ca_sweep_stale_generation_jobs(integer) to service_role;

commit;

notify pgrst, 'reload schema';
