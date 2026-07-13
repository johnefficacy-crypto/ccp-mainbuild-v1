# Operator runbook — EWP prompt-bank expansion (import → verify → activate → surface)

**Audience:** operator with live Supabase + Content Studio access.
**Goal:** land more `sentence_construction` writing prompts on a live DB and confirm they surface on Study Home via a planner-generated task.
**Scope reality (read first):** of the 270 repo-authored seed rows, **only `sentence_construction` (batch `01_sentence_construction.json`, 50 rows) is activatable today.** `sentence_correction` / grammar / `vocabulary_in_context` / `paragraph_writing` may be imported and verified but **cannot be activated** yet — activation is blocked on CODE work (evaluator does not receive `source_text`; no paragraph rubric). See `app/supabase/seeds/writing_prompts/README.md` → "Runtime blockers". Do not attempt to activate those types; the activate RPC will refuse them with `exercise_type_not_runtime_ready`.

All writes go through the audited `content_studio` RPCs — **never raw SQL INSERT** (that bypasses the review lifecycle + audit).

---

## 0. Preconditions (one-time)

**0.1 Router flag.** The Content Studio router is gated by `ADMIN_STUDY_OS_ENABLED`. Confirm it is set truthy on the API service, else every call 404s.

**0.2 Operator permissions** (`raw_app_meta_data.permissions`, per CLAUDE.md role model). The full lifecycle needs, across one or more operators:
- `content_studio.author` — create / bulk-import / edit drafts
- `content_studio.review` — pending → verified
- `content_studio.activate` — verified → live (`is_active=true`) — **separate higher-trust authority**
- `exam_intelligence.manage` — propose an applicability target
- `exam_intelligence.review` — promote the target to `active`

**0.3 Env used below**
```bash
API="https://<your-api-host>"          # no trailing slash
TOKEN="<supabase access token for the operator>"
SUBJECT_ID="<english-language subject UUID on THIS db>"   # see 1.2
export EWP_PG_DSN="postgres://…"       # live/staging DSN, for the preflight only
```

---

## 1. Author + preflight the rows

**1.1 (optional) Add/regenerate rows.** Edit `app/supabase/seeds/writing_prompts/01_sentence_construction.json` (a JSON array of prompt rows; **no** `subject_id`/exam columns — prompts are subject-scoped), each with a unique `external_key`, then:
```bash
cd app/supabase/seeds/writing_prompts
python3 build_seed.py        # regenerates + validates every row; fails loudly
```

**1.2 Resolve the live subject id.** The rows bake deterministic migration-205 IDs (`md5('ewp:subject|topic|microtopic:<slug>')`), which are only correct if 205 created the English taxonomy fresh on this DB.
```bash
psql "$EWP_PG_DSN" -tA -c "SELECT id FROM subjects WHERE slug='english-language';"   # -> SUBJECT_ID
```

**1.3 Mandatory preflight** — proves every baked subject/topic/microtopic id is the live, active, correctly-parented row. If it fails, re-map the IDs to the live values before importing (else the first row fails `invalid_scope`).
```bash
EWP_PG_DSN="$EWP_PG_DSN" python3 preflight_ids.py
```

---

## 2. Import (bulk) → lands `pending` / `is_active=false`

Wrap the row array into the `{reason, subject_id, rows}` envelope and POST. Import is **atomic all-or-nothing** and idempotent per `(subject_id, external_key)`.
```bash
python3 to_api_envelope.py 01_sentence_construction.json \
    --subject-id "$SUBJECT_ID" \
    --reason "Prompt-bank expansion: sentence_construction batch 01" > /tmp/env.json

curl -sS -X POST "$API/api/admin/content-studio/writing-prompts/bulk" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    --data @/tmp/env.json | jq
```
- Success → `{"ok": true, "result": {"created": N, "updated": N, "unchanged": N}}`.
- `422 bulk_locked_row` → a changed row collides with a `verified`/`rejected` row (locked); fix the row or bump its `external_key`. The whole batch aborts on the first bad row (one error, no partial import).
- Every imported row is `reviewer_status='pending'`, `is_active=false`.

---

## 3. Verify (pending → verified) — `content_studio.review`

Review is CAS-guarded: you must send the `reviewer_status` and `updated_at` you actually read.

**3.1 List the pending prompts to get `id` + `updated_at`:**
```bash
curl -sS "$API/api/admin/content-studio/writing-prompts?subject_id=$SUBJECT_ID&exercise_type=sentence_construction&reviewer_status=pending&limit=100" \
    -H "Authorization: Bearer $TOKEN" | jq '.items[] | {id, reviewer_status, updated_at}'
```

**3.2 For each prompt, verify it** (`status: verified`, echoing the CAS tokens):
```bash
curl -sS -X POST "$API/api/admin/content-studio/writing-prompts/$PROMPT_ID/review" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{
      "status": "verified",
      "expected_status": "pending",
      "expected_updated_at": "'"$UPDATED_AT"'",
      "reason": "Expansion review: sentence_construction batch 01"
    }' | jq
```
- `409` → the row changed under you; re-GET and retry with fresh tokens.
- Verified prompts are **locked** for editing (edit requires review → `needs_correction` first). Still `is_active=false`.

---

## 4. Applicability — propose (manage) then activate the target (review)

A prompt only surfaces to learners inside an exam context via an **active** `writing_prompt_target`. Split by the locked J2 authority separation.

**4.1 Propose an inert target** (`exam_intelligence.manage`). Choose exactly ONE scope — `is_global:true` OR one of `exam_family_id`/`exam_id`/`exam_phase_id`:
```bash
curl -sS -X POST "$API/api/admin/content-studio/writing-prompts/$PROMPT_ID/targets" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"reason":"Expansion: make applicable to SSC CGL English","exam_id":"'"$EXAM_ID"'"}' | jq
```
- Lands `applicability_status='pending_review'` (inert). A duplicate `(prompt, scope)` → `409 target_exists`.

**4.2 Read the target's CAS token:**
```bash
curl -sS "$API/api/admin/content-studio/writing-prompts/$PROMPT_ID/targets" \
    -H "Authorization: Bearer $TOKEN" | jq '.items[] | {id, applicability_status, updated_at}'
```

**4.3 Promote to active** (`exam_intelligence.review`):
```bash
curl -sS -X POST "$API/api/admin/content-studio/writing-prompt-targets/$TARGET_ID/review" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"reason":"Expansion: activate applicability","applicability_status":"active","expected_updated_at":"'"$TARGET_UPDATED_AT"'"}' | jq
```
- A **global** target cannot be `excluded` (`422 invalid_scope`). Stale token → `409`.

---

## 5. Activate the prompt (`content_studio.activate`)

**5.0 Re-read the prompt for a FRESH CAS token.** Verification in §3.2 ran `cms_review_writing_prompt`, which set `writing_prompts.updated_at = now()`. The activate RPC hard-checks the *current* `updated_at` against `p_expected_updated_at` under the row lock, so the pre-review `$UPDATED_AT` is now stale and would fail with `409 concurrent_modification`. Re-read the prompt and capture its post-verification token:
```bash
PROMPT_UPDATED_AT=$(curl -sS "$API/api/admin/content-studio/writing-prompts/$PROMPT_ID" \
    -H "Authorization: Bearer $TOKEN" | jq -r '.updated_at')
# sanity-check: should show reviewer_status=verified, is_active=false
curl -sS "$API/api/admin/content-studio/writing-prompts/$PROMPT_ID" \
    -H "Authorization: Bearer $TOKEN" | jq '{id, reviewer_status, is_active, updated_at}'
```

**5.1 Activate.** The activate RPC is the **sole** eligibility authority — it checks every precondition under a row lock and returns a **normal 200** verdict `{eligible, blockers}` (a blocked activation is NOT an error). Use the FRESH `$PROMPT_UPDATED_AT`, never the pre-review `$UPDATED_AT`:
```bash
curl -sS -X POST "$API/api/admin/content-studio/writing-prompts/$PROMPT_ID/activate" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"reason":"Expansion: activate verified sentence_construction prompt","expected_updated_at":"'"$PROMPT_UPDATED_AT"'"}' | jq
```
- `{"eligible": true, ...}` → prompt is now `is_active=true` (live).
- `{"eligible": false, "blockers": [...]}` → resolve the listed blockers and retry. Blocker codes:
  - `prompt_not_verified` → do step 3 first.
  - `no_active_applicability_target` → do step 4 first.
  - `exercise_type_not_runtime_ready` → the type isn't in the server-owned allowlist (`sentence_construction` only today) — expected for correction/grammar/vocab/paragraph; do not force.
  - `semantic_evaluator_not_live` / `rubric_missing` → CODE blockers, not operator-resolvable (see the SP1b runbook / paragraph-rubric work).
- CAS mismatch → `409`; missing prompt → `404`.

---

## 6. Confirm it surfaces on Study Home

A prompt reaches a learner only via a planner-generated `english_writing_session` `study_task` in the prompt's topic/exam scope (planner generation shipped in PR #945). The click resolves the prompt server-side via `POST /api/study/tasks/{id}/launch-writing` (which re-applies the exact verified ∧ active ∧ runtime-ready ∧ applicability gate).

1. As a **learner** whose target exam matches the activated target's scope, regenerate/open the plan so the deterministic planner emits a `sentence_construction` task for that topic.
2. On **Study Home**, confirm the task renders the **"Start sentence practice"** CTA.
3. Click it → a `writing_session` is created (no `409 no_eligible_prompt`) and the activated prompt is served.
4. Capture the `session_id` + prompt id as live evidence.

If launch returns `409 no_eligible_prompt`: the prompt/target/topic scope doesn't line up with the task — re-check that the prompt is verified+active, its target is `active` for the task's exam, and the task's `topic_id` matches the prompt's `topic_id`.

---

## 7. Record + checklist

- Write a dated evidence doc under `docs/audits/ewp/` (prompt ids activated, target scope, session id from the click-through).
- Update `docs/status/career-copilot-checklist.md` prompt-bank rows from `OPERATOR PENDING` to the achieved state (imported / verified / active counts), and mark the PR-A live click-through validated once §6 is captured.

### Error → action quick reference
| Code | Meaning | Action |
|---|---|---|
| `422 invalid_scope` | baked taxonomy id not live, or bad target scope | re-run preflight / send exactly one target scope |
| `422 bulk_locked_row` | changed row hits a verified/rejected row | fix row or bump `external_key` |
| `409` | stale CAS (`expected_status`/`expected_updated_at`) or `target_exists` | re-GET, resend fresh token |
| `403` | missing permission | provision the authority in 0.2 |
| `eligible:false` | activation precondition unmet | resolve the listed `blockers` |
