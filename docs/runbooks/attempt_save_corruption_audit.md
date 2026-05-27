# Mock Attempt Save Corruption Audit

Run these when investigating user reports of "wrong score on submitted mock":

## 1. Check for client_seq overflow corruption

```sql
SELECT COUNT(*) FROM mock_attempt_responses WHERE client_seq > 2147483647;
-- Expect: 0. Non-zero means silent corruption.
```

## 2. Check for events sequence_no overflow

```sql
SELECT COUNT(*) FROM mock_attempt_events WHERE sequence_no > 2147483647;
-- Expect: 0.
```

## 3. Identify submitted attempts with suspiciously low answer counts

```sql
SELECT ma.user_id, ma.id, ma.submitted_at,
       ma.total_correct + ma.total_wrong AS db_attempted,
       jsonb_array_length(ma.template_snapshot->'questions') AS total_questions,
       COUNT(mar.id) FILTER (WHERE mar.selected_option_id IS NOT NULL) AS answered
FROM mock_attempts ma
LEFT JOIN mock_attempt_responses mar ON mar.attempt_id = ma.id
WHERE ma.status = 'submitted' AND ma.submitted_at > now() - interval '30 days'
GROUP BY ma.id
HAVING COUNT(mar.id) FILTER (WHERE mar.selected_option_id IS NOT NULL)
       < jsonb_array_length(ma.template_snapshot->'questions') * 0.5
ORDER BY ma.submitted_at DESC;
-- Non-empty: those users got incorrect scores. Decide outreach.
```

## 4. Identify in-progress attempts that may be heading toward bad submit

```sql
SELECT ma.id, ma.user_id, ma.started_at,
       jsonb_array_length(ma.template_snapshot->'questions') AS total,
       COUNT(mar.id) FILTER (WHERE mar.selected_option_id IS NOT NULL) AS answered
FROM mock_attempts ma
LEFT JOIN mock_attempt_responses mar ON mar.attempt_id = ma.id
WHERE ma.status = 'in_progress' AND ma.started_at > now() - interval '7 days'
GROUP BY ma.id
ORDER BY ma.started_at DESC;
-- Active attempts with answered=0 after meaningful elapsed time are at risk.
```

## Background

This audit was run on 2026-05-27 following the PR-fix-10a investigation.
At that time:

- Query 1 returned 0 (no client_seq overflow in any response row).
- Query 2 returned 0 (no sequence_no overflow in any event row).
- Query 3 returned 0 rows (no submitted attempts with <50% answered in last 30 days).
- No backfill or data recovery was required.

The root cause was `useAnswerSync.js` seeding `client_seq` from `Date.now()`
(a 13-digit millisecond timestamp), which exceeds the Postgres `int4` maximum
(2,147,483,647). Supabase rejected the UPDATE with error 22003. The backend
wrapped the update in `_safe(...)`, swallowing the error and returning 200 OK
while recording the `QUESTION_ANSWERED` event as if the write succeeded.
PR-fix-10a closes the surface: monotonic counter in the frontend, strict write
in the backend, 503 on failure, submit consistency check.
