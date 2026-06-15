-- Mock E2E fixture isolation smoke check.
-- Read-only: SELECT-only assertion, raises an exception on any violation.
--
-- Invariant (PRODUCTION ONLY): the Playwright E2E fixtures
-- (app/supabase/seeds/e2e_fixtures.sql) tag their mock_question_bank rows with
-- source_type = 'e2e_fixture' and mark them 'published' so the E2E fixed-id
-- selector can load them INSIDE the E2E database. They must NEVER appear as
-- selectable rows in the production mock bank, where they could leak into a
-- real (criteria/generated) attempt or inflate mock-readiness depth.
--
-- This asserts there are zero e2e_fixture rows in a selectable reviewer_status
-- ('verified' | 'published' | 'live'). Run it against a PRODUCTION-shaped DB.
-- Do NOT run it against the E2E database — there the fixtures are published by
-- design and this check is expected to fail.
--
-- Manual validation:
--   psql "$PROD_DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -f app/supabase/checks/mock_e2e_fixture_isolation.sql

begin read only;

do $$
declare
  selectable_fixture_count integer;
begin
  select count(*)
    into selectable_fixture_count
    from public.mock_question_bank
   where source_type = 'e2e_fixture'
     and reviewer_status in ('verified', 'published', 'live');

  if selectable_fixture_count <> 0 then
    raise exception
      'E2E fixture leak: % e2e_fixture mock_question_bank row(s) are in a '
      'selectable reviewer_status in this database. Test fixtures must never be '
      'selectable in production — archive/de-publish them.',
      selectable_fixture_count;
  end if;
end $$;

rollback;
