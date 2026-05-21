# Promotion-block diagnosis — `requires_domicile` / post-scoped fields

_Pre-flight artifact for the promotion-block PR. Static (code) verification is
complete; the **live-DB section is PENDING** — it needs queries run against
Supabase (this container has no DB/API access)._

## Method

Verified every pre-flight claim against the code on `main`. Live introspection
on the reference stuck item (`cec98cb3-acad-4501-a34c-8ef4abc6cb5d`) is required
to (1) confirm cause (A), (2) determine whether the item has unnamed posts
(relevance of BUG 4), and (3) fill the live-evidence section + reproduction.

## Claim verification (all CONFIRMED)

| Claim | Verdict | Evidence |
|---|---|---|
| `FieldReviewGroup.jsx` excludes `requires_domicile` (post-scoped) | ✅ | `POST_SCOPED_FIELDS = new Set(["requires_domicile"])` line 6; `required = requiredFields.filter(f => !POST_SCOPED_FIELDS.has(f))` line 250 |
| `PostEligibilityReviewGroup.jsx` is the ONLY UI rendering `requires_domicile` verify/correct | ✅ | verify/correct calls at lines 58, 90; grep of `workflow/` shows no other component issuing `requires_domicile` actions |
| `AdminFixPanel.jsx` gates posts on `(item.raw_extracted_item \|\| item.normalized_item \|\| {}).posts` + `Array.isArray(posts) && posts.length` | ✅ | lines 138, 293 |
| Frontend post `entity_key` fallback is `post-${index}` when `post_name` missing | ✅ | `PostEligibilityReviewGroup.jsx:46` `(post?.post_name || "").trim() || \`post-${postIndex}\`` |
| Backend `promotion_gate.py` matches evidence by `entity_type='post'` AND `entity_key == post.post_name` | ✅ | `_post_identity_key` returns `post_name.strip().lower()` (line 103); matched at lines 182-188 |
| Backend `list_scrape_queue()` flattens evidence to `{field_name: reviewer_status}`, dropping entity scope | ✅ | `admin_scrape.py:1137-1139` dict-comprehension keyed on `field_name` only |

Supporting facts:
- Gate accepts BOTH statuses: `_VERIFIED_STATUSES = {"verified", "corrected"}` (`promotion_gate.py:47`).
- `POST_SCOPED_FIELDS` in the gate is exactly `{"requires_domicile"}` (line 40) — so the hardcoded set is correct; `total_vacancies`, `age_*` are recruitment-level, NOT post-scoped.
- `admin_scrape.py` already imports from the gate (`HIGH_RISK_FIELDS`, `evaluate_promotion_gate`, line 41).
- The verify/correct entity resolver that throws the 422 is `_resolve_entity_path` (`admin_scrape.py:303-323`) → 422 at `patch_scrape_queue_extracted_field` line 553. It matches `entity_key` only against `post_name`; `post-N` → `None` → 422.

## Which cause is firing? (ranked, pending live confirmation)

- **(C) — flattening hides per-post scope → `unverified_fields` wrong. CONFIRMED, RANK #1 (structural).**
  `evidence_by_queue[qid] = {fr.field_name: fr.reviewer_status}` collides all
  posts' `requires_domicile` rows into ONE key (last-write-wins). Then
  `missing = [f for f in _HIGH_RISK_FIELDS if reviewed.get(f) not in {"verified","corrected"}]`
  (line 1230) and `promotable = len(missing)==0 …` (line 1233). For a
  multi-post item, verifying every post cannot reliably clear
  `requires_domicile` from `unverified_fields`, so `AdminFixPanel`'s
  `blockedFromPromote` (`blockers = item.unverified_fields`, line 140) keeps the
  Promote button disabled even though the real gate (`evaluate_promotion_gate`,
  per-post correct) would pass. **This is the primary blocker for any multi-post
  `requires_domicile` item.** → BUG 1.

- **(D) — UI accepts only `"verified"`, not `"corrected"`. CONFIRMED, RANK #2.**
  The per-post checkbox calls `onFieldAction("requires_domicile", "correct", …)`
  (`PostEligibilityReviewGroup.jsx:58`), writing `reviewer_status="corrected"`.
  But `verified = statusKey === "verified"` (line 50) → the Verify button stays
  enabled and shows no done-state for a corrected post, and the same
  exact-match exists in `FieldReviewGroup.jsx:109,265,275` for
  recruitment-level fields. The gate accepts `corrected`, so this is a UI/gate
  mismatch. → BUG 3.

- **(B) — `post-N` entity_key written for unnamed posts → 422 on Correct. CONFIRMED in code; FIRES ONLY IF the item has posts with no `post_name`.** → BUG 4. Live query (a) needed to know if `cec98cb3` has unnamed posts.

- **(A) — `raw_extracted_item` missing → no button rendered. NEEDS LIVE.**
  `list_scrape_queue` does not set `raw_extracted_item`; the frontend overlay
  (`OperationsConsole.selectedQueueItem`) derives it as
  `raw_extracted_item ?? queueDetail.raw_extracted_item ?? queueDetail.extracted_data`,
  so `posts` resolve from `extracted_data.posts` **iff that array exists**. If
  `cec98cb3.extracted_data->'posts'` is empty/missing, the post table never
  renders and `requires_domicile` cannot be reviewed at all. Query (a) decides
  this.

## Blast-radius conflicts found (need a decision before fixing)

1. **BUG 4 backend fix location.** The 422 resolver is `_resolve_entity_path`
   in `admin_scrape.py`, but the allowed `admin_scrape.py` scope is
   "list_scrape_queue evidence shaping only", and the task names
   `promotion_gate.py / canonical.py` for the resolver — neither of which holds
   this resolver. Fixing the actual 422 requires editing `_resolve_entity_path`
   (outside "evidence shaping"). **Flagged; not edited pending approval.**

2. **BUG 3 cross-file.** The same exact-match-on-`"verified"` bug exists in
   `FieldReviewGroup.jsx` (lines 109, 265, 275) for recruitment-level fields,
   but `FieldReviewGroup.jsx` is NOT in the blast radius. BUG 3 says "fix all in
   this PR." **Flagged; in-scope fix is `PostEligibilityReviewGroup.jsx` only
   unless the radius is widened.**

(Non-field `"verified"` callsites — `AdminProgressBar`, `AdminFixPanel`
recruitment publish buttons, `OfficialSourceQuickResolver` source status,
`adminWorkflowContract`, `CurrentActionCard` — key off `publish_status`/source
`is_verified`, a different vocabulary, and must NOT be changed.)

## Live verification — TO RUN (results pending)

```sql
-- (a) Does the stuck item have posts, and is raw extraction present?
select id,
       extracted_data->'posts' as extracted_posts,
       jsonb_array_length(coalesce(extracted_data->'posts','[]'::jsonb)) as n_posts,
       raw_payload is not null as has_raw,
       raw_payload->'extracted_item' is not null as has_raw_extracted_item
from scrape_queue
where id = 'cec98cb3-acad-4501-a34c-8ef4abc6cb5d';

-- (b) requires_domicile evidence rows (scope + status per row)
select field_name, entity_type, entity_key, reviewer_status
from extracted_field_evidence
where scrape_queue_id = 'cec98cb3-acad-4501-a34c-8ef4abc6cb5d'
  and field_name = 'requires_domicile'
order by entity_key;
```

```text
(c) GET /api/admin/scrape/queue?include_detail=true&item_id=cec98cb3-acad-4501-a34c-8ef4abc6cb5d
    → confirm presence/shape of: raw_extracted_item, normalized_item, posts,
      unverified_fields, field_evidence_details (entity_type/entity_key per row).
```

**LIVE RESULTS: _pending — to be pasted in and folded into the ranking above._**

## Reproduction (pending live + fix)

1. Open admin scrape review for `cec98cb3-…`.
2. Verify all flat fields AND check `requires_domicile` for every post.
3. Wait for refresh.
4. Promote button enabled + promotion-preview ready → PASS.

## Implementation status (this PR)

- **BUG 1 — FIXED.** `list_scrape_queue` now builds `field_evidence_status_scoped`
  (`[field]["<entity_type>:<entity_key>"] = status`) alongside the flat
  `field_evidence_status` (kept for back-compat), and computes
  `unverified_fields`/`promotable` per-post for `POST_SCOPED_FIELDS`, mirroring
  `evaluate_promotion_gate` (recruitment-level fields unchanged; no-posts payload
  falls back to the recruitment-level rule). The table path now also selects
  `entity_type, entity_key` (still excludes heavy columns).
- **BUG 3 — PARTIALLY FIXED (per authorization).** `PostEligibilityReviewGroup`
  now accepts `{"verified","corrected"}` (`ACCEPTED_STATUSES`): a corrected post
  disables the Verify button and shows a ✓. **NOT fixed (out of blast radius,
  not authorized):** `FieldReviewGroup.jsx` exact-match `=== "verified"` at
  lines 109, 265, 275 (recruitment-level fields) — a corrected recruitment-level
  field still looks unreviewed in that flat list. Recommended for a follow-up PR.
- **BUG 4 — FIXED (resolver edit authorized).** `_resolve_entity_path` resolves
  `post-<index>` to `posts[index]` when no `post_name` matches; out-of-range
  index stays `None` → 422. `PostEligibilityReviewGroup` emits a dev
  `console.warn` when it falls back to a positional key.
- **BUG 2 — DEFERRED.** Conditional on live query (a): only if
  `cec98cb3.extracted_data->'posts'` is empty/missing does the post table fail
  to render. Static analysis says `posts` resolve via the
  `extracted_data` fallback, so cause (A) is unlikely — confirm with (a) before
  any AdminFixPanel change.

### Tests added
- Backend `tests/test_admin_scrape_endpoints.py`: all-posts-verified clears
  `requires_domicile`; partial keeps it; corrected counts as resolved; scoped
  map present + flat back-compat; `_resolve_entity_path` name-match / `post-N`
  fallback / out-of-range; `patch_*` patches `posts[N]` and 422s on
  out-of-range. Plus the slim-select test updated to the status+scope columns.
- Frontend `__tests__/PostEligibilityReviewGroup.test.jsx`: verified/corrected →
  disabled+✓; rejected/unverified → enabled+no-✓; unnamed post warns + emits
  `post-0`; named post no-warn + uses `post_name`.

## Out of scope (confirmed, not fixed here)

- `/api/admin/recruitments` 500 from `min_age` schema drift (separate PR). May
  also block the button via the promote-to-existing dropdown — note for QA.
- N+1 in `/api/admin/recruitments` (separate PR).
- OperationsConsole 6-endpoint cascade (separate PR).
- `POST_SCOPED_FIELDS` config externalization (kept sourced from the gate here).
