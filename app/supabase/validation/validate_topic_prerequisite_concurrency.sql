-- VERIFY DB — J2-A′ topic prerequisite concurrency + lifecycle race validation
--
-- The unit tests emulate cms_write_topic_prerequisite with the advisory lock as
-- a NO-OP (single-threaded). The lock's real value (serializing concurrent
-- ordering writes so A->B, B->C, C->A cannot jointly form a cycle) and the CAS
-- lifecycle guards can only be proven against real PostgreSQL. Run this against
-- a staging DB with migration 208 applied. This is an OPERATOR / VERIFY DB step;
-- do NOT mark concurrency acceptance complete from unit tests alone.
--
-- Prereqs: three topics A,B,C in one subject; substitute real UUIDs below.
\set A '00000000-0000-0000-0000-00000000000a'
\set B '00000000-0000-0000-0000-00000000000b'
\set C '00000000-0000-0000-0000-00000000000c'

-- ── 1. Three-transaction cycle race ──────────────────────────────────────────
-- Open THREE psql sessions. In each, BEGIN and call the RPC for one edge, then
-- COMMIT all three as close together as possible:
--   S1: begin; select cms_write_topic_prerequisite(null, :'A', :'B', 'requires', 1.0, null, null); -- A depends on B
--   S2: begin; select cms_write_topic_prerequisite(null, :'B', :'C', 'requires', 1.0, null, null); -- B depends on C
--   S3: begin; select cms_write_topic_prerequisite(null, :'C', :'A', 'requires', 1.0, null, null); -- C depends on A (closes cycle)
--   then commit each.
-- EXPECTED: the global advisory lock serializes them; exactly the cycle-closing
-- call raises `cycle: ...`. The graph must NOT contain A->B->C->A afterwards.
-- CHECK (must return 0):
--   with recursive r(n) as (
--     select :'A'::uuid
--     union
--     select tp.prerequisite_topic_id from topic_prerequisites tp
--       join r on tp.topic_id = r.n where tp.relation_type in ('requires','recommended_before'))
--   select count(*) from r where n = :'A' and exists (select 1 from r where n <> :'A');

-- ── 2. Lifecycle CAS race (edit vs review) ───────────────────────────────────
-- Seed one edge E in 'draft'. Concurrently:
--   S1: begin; -- manage PATCH path: expected_status='draft'
--       select cms_write_topic_prerequisite('E', :'A', :'B', 'requires', 0.5, null, null, '{}'::jsonb, 'draft');
--   S2: begin; update topic_prerequisites set reviewer_status='pending_review' where id='E' and reviewer_status='draft';
-- Commit S2 first, then S1.
-- EXPECTED: S1 raises `concurrent_modification` (CAS: row is no longer 'draft').

-- ── 3. Submit/review/delete CAS ──────────────────────────────────────────────
-- The endpoints issue conditional writes:
--   submit: update ... set reviewer_status='pending_review' where id=E and reviewer_status in ('draft','rejected');
--   review: update ... set reviewer_status=<target> where id=E and reviewer_status=<observed current>;
--   delete: delete ... where id=E and reviewer_status in ('draft','rejected');
-- EXPECTED: each returns 0 rows (→ 409 at the API) when a concurrent transition
-- already moved the row out of the expected state. Verify affected-row counts.
