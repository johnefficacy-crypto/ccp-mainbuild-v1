-- 124_external_api_usage.sql
-- Per-provider API usage counters for external-search quota guarding.
--
-- SerpApi's free tier is 250 searches/month. The discovery runner reads
-- today's count and the month-sum from this table before each request and
-- short-circuits when the daily or monthly cap is hit (see
-- app/backend/app/scraping/quota.py). Only successful, uncached responses are
-- recorded — cached/errored SerpApi searches are free and must not count.

-- up
create table if not exists public.external_api_usage (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  usage_month text not null,            -- 'YYYY-MM'
  usage_date date not null default current_date,
  count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(provider, usage_month, usage_date)
);

create index if not exists idx_external_api_usage_month
  on public.external_api_usage(provider, usage_month);
