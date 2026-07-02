-- ===========================================================================
-- 213_english_writing_practice_error_lab_read_model.sql
-- ---------------------------------------------------------------------------
-- EWP-4 Error Lab server-side read model.
--
-- Replaces the API-layer session→unit→version→evaluation→issue ID fan-out (the
-- former Python _released_evaluation_ids/_current_state_issue_events helpers)
-- with a single owner-scoped, SECURITY DEFINER read function. Doing the walk,
-- the effective-review-decision fold (§4.10a), the reclassification remap
-- (§4.10a/§4.11a), and the canonical-topic join in SQL keeps the read a single
-- round-trip (no progressive `IN (...)` URL building) and applies the exact
-- verified-only gating the rest of EWP relies on:
--
--   (a) owner-scoped to p_user (service-role bypasses RLS; this is the primary
--       authorization, RLS is defence-in-depth),
--   (b) feedback-released only — learning is always released; exam gates on
--       feedback_released_at <= now() (§13 rule 13),
--   (c) current-state only — affects_current_state = true (stale non-latest
--       findings excluded, §4.8),
--   (d) effective-invalidation excluded AND effective-reclassification applied:
--       the latest review event by (created_at DESC, event_seq DESC) wins
--       (§4.10a; event_seq is the monotonic tiebreak, NOT id). An effectively
--       `invalidated` issue is a withdrawn false positive and never leaks; an
--       effectively `reclassified` issue renders the CORRECTED issue_type and
--       its remapped ACTIVE canonical microtopic (same map + English-subject
--       guard the evaluator uses in migration 209),
--   (e) joined to canonical public.topics for microtopic_name + microtopic_slug
--       so the API returns human labels, never bare UUIDs.
--
-- Read-only: no writes, no AI writes. Mirrors the ewp_private SECURITY DEFINER
-- pattern of 205/209 (private schema, service_role EXECUTE only).
--
-- MIGRATION NUMBER: max on main at authoring time is 212; this is 213. The live
-- schema_migrations table could not be queried from the authoring container —
-- reconcile the number at apply time (VERIFY DB) and renumber if 213 is taken.
-- ===========================================================================

CREATE SCHEMA IF NOT EXISTS ewp_private;  -- created in 205; defensive for isolation.

-- ---------------------------------------------------------------------------
-- ewp_private.ewp_error_lab(p_user) — the current-state Error Lab read model.
--
-- SECURITY DEFINER (repo pattern, cf. ewp_private.ewp_issue_effectively_invalidated
-- in 205): it reads writing_issue_review_events, which is RLS-on with NO
-- authenticated policy, so a SECURITY INVOKER function would see zero review
-- rows and wrongly render withdrawn/stale classifications. As DEFINER it reads
-- the review history correctly. It lives in ewp_private (NOT in PostgREST's
-- exposed-schema list) so it can never be probed as a REST RPC oracle for
-- another user's issues; execution is service_role-only.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ewp_private.ewp_error_lab(p_user uuid)
RETURNS TABLE (
  id               uuid,
  issue_type       text,
  severity         text,
  quoted_text      text,
  explanation      text,
  suggested_text   text,
  span_start_utf16 int,
  span_end_utf16   int,
  microtopic_id    uuid,
  microtopic_name  text,
  microtopic_slug  text,
  created_at       timestamptz
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  WITH eff AS (
    -- Effective review decision per issue: latest by (created_at DESC,
    -- event_seq DESC). event_seq is the authoritative tiebreak (§4.10a).
    SELECT DISTINCT ON (r.issue_event_id)
           r.issue_event_id,
           r.decision,
           r.corrected_issue_type
    FROM public.writing_issue_review_events r
    ORDER BY r.issue_event_id, r.created_at DESC, r.event_seq DESC
  ),
  base AS (
    SELECT
      ie.id,
      ie.created_at,
      ie.severity,
      ie.quoted_text,
      ie.explanation,
      ie.suggested_text,
      ie.span_start_utf16,
      ie.span_end_utf16,
      ie.issue_type       AS orig_issue_type,
      ie.microtopic_id    AS orig_microtopic_id,
      eff.decision        AS eff_decision,
      -- Effective issue type: corrected type on an effective reclassify, else
      -- the original.
      CASE WHEN eff.decision = 'reclassified' THEN eff.corrected_issue_type
           ELSE ie.issue_type END AS eff_issue_type
    FROM public.writing_issue_events ie
    JOIN public.writing_evaluations   e ON e.id = ie.evaluation_id
    JOIN public.writing_unit_versions v ON v.id = e.unit_version_id
    JOIN public.writing_session_units u ON u.id = v.unit_id
    JOIN public.writing_sessions      s ON s.id = u.session_id
    LEFT JOIN eff ON eff.issue_event_id = ie.id
    WHERE s.user_id = p_user
      AND ie.affects_current_state = TRUE
      AND (
        s.mode = 'learning'
        OR (s.feedback_released_at IS NOT NULL AND s.feedback_released_at <= now())
      )
      -- Effective invalidation excluded (default 'confirmed' when no events).
      AND COALESCE(eff.decision, 'confirmed') <> 'invalidated'
  ),
  resolved AS (
    SELECT
      b.*,
      -- On an effective reclassify, remap the microtopic from the CORRECTED
      -- issue type via the active map — VALIDATED as a live English microtopic
      -- exactly as the evaluator does (§5.3/§4.15, migration 209 lines 364-378):
      -- level='microtopic', active, inside the english-language subject tree; a
      -- map row that fails those guards yields NULL (topic-level) rather than a
      -- foreign/inactive id. Otherwise keep the issue's original microtopic.
      CASE WHEN b.eff_decision = 'reclassified' THEN (
        SELECT m.microtopic_id
        FROM public.writing_issue_type_microtopic_map m
        JOIN public.topics   t   ON t.id = m.microtopic_id
        JOIN public.subjects sub ON sub.id = t.subject_id
        WHERE m.issue_type = b.eff_issue_type
          AND m.is_active = TRUE
          AND t.level = 'microtopic'
          AND t.is_active = TRUE
          AND sub.slug = 'english-language'
        LIMIT 1
      )
      ELSE b.orig_microtopic_id END AS resolved_microtopic_id
    FROM base b
  )
  SELECT
    r.id,
    r.eff_issue_type            AS issue_type,
    r.severity,
    r.quoted_text,
    r.explanation,
    r.suggested_text,
    r.span_start_utf16,
    r.span_end_utf16,
    r.resolved_microtopic_id    AS microtopic_id,
    t.name                      AS microtopic_name,
    t.slug                      AS microtopic_slug,
    r.created_at
  FROM resolved r
  LEFT JOIN public.topics t ON t.id = r.resolved_microtopic_id
$$;

REVOKE ALL ON FUNCTION ewp_private.ewp_error_lab(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION ewp_private.ewp_error_lab(uuid) TO service_role;

-- ---------------------------------------------------------------------------
-- public.ewp_error_lab(p_user) — thin REST-callable wrapper.
--
-- ewp_private is deliberately NOT in PostgREST's exposed-schema list, so the
-- service-role API client cannot invoke ewp_private.ewp_error_lab via
-- supabase.rpc(...) directly. This public wrapper is the REST entry point: it
-- is service_role-only (REVOKE from PUBLIC/anon/authenticated) and simply
-- delegates to the private read model, so the gating/fold logic has exactly one
-- home. SECURITY DEFINER so it may call into ewp_private.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.ewp_error_lab(p_user uuid)
RETURNS TABLE (
  id               uuid,
  issue_type       text,
  severity         text,
  quoted_text      text,
  explanation      text,
  suggested_text   text,
  span_start_utf16 int,
  span_end_utf16   int,
  microtopic_id    uuid,
  microtopic_name  text,
  microtopic_slug  text,
  created_at       timestamptz
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT * FROM ewp_private.ewp_error_lab(p_user)
$$;

REVOKE ALL ON FUNCTION public.ewp_error_lab(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ewp_error_lab(uuid) TO service_role;
