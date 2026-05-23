## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- ALWAYS read graphify-out/GRAPH_REPORT.md before reading any source files, running grep/glob searches, or answering codebase questions. The graph is your primary map of the codebase.
- IF graphify-out/wiki/index.md EXISTS, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## RBAC bootstrap

Auth roles are `user`, `admin`, `super_admin` only. The single source of truth
for a role is `auth.users.raw_app_meta_data.role` (Supabase app_metadata),
read/written exclusively by the FastAPI service-role backend
(`require_admin` / `require_super_admin`). `profiles.admin_role` and
`profiles.is_admin` are deprecated (marked, not dropped). `mentor` is NOT a
role — it is a capability (`profiles.is_mentor`, surfaced as
`capabilities.mentor` on `/api/auth/me`).

To create the first `super_admin` (the user must already exist in Supabase
Auth), run from the repo root:

```
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
  python -m app.backend.scripts.bootstrap_super_admin --email <email>
```

Env prerequisites: `SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_URL`
(`NEXT_PUBLIC_SUPABASE_URL` is also accepted). The script is idempotent
(re-running on an existing super_admin exits 0 with "already super_admin"),
exits 2 on no match, 3 on multiple matches, and writes a
`rbac.bootstrap_super_admin` audit row. It never prints tokens or keys.

**Force-signout SDK limitation:** `supabase-auth` 2.29 exposes only a
JWT-scoped `sign_out(jwt, scope)` — there is no by-user-id admin signout. The
`POST /api/admin/users/{id}/force-signout` endpoint therefore uses a best-effort
`ban_duration` cycle via `update_user_by_id` to invalidate the active session;
existing access tokens remain valid until they expire. If neither path works
the endpoint returns `{"signout_supported": false}`.

## Study OS frontend contract

Each surface has one source of truth. Do not cross-wire them:

- `/app/study/home` (StudyHome.jsx) → `/api/study/mission-control` for the
  active plan, today's tasks, and focus rollup. The weekly report card is a
  separate fetch (`/api/study/report-card*`) because mission-control does
  not include it.
- `/app/study/plan` (StudyPlan.jsx) → `/api/study/plan/draft`,
  `/api/study/plan/apply`, `/api/study/plan/timeline`. Different contract;
  no overlap with mission-control.
- `/app/today` (Today.jsx) → the dashboard hook only. It is intentionally a
  general action/application overview after the PR3 reorg. **Never call
  `/api/study/mission-control` from `/app/today`.**
- `competition_context` reads `reviewer_status in ('locked','reviewed')`
  (locked preferred). UI copy must say "reviewed or locked rows feed the
  planner; locked preferred" — not "locked only".
