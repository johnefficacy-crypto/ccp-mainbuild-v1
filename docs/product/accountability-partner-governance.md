# Accountability Partner — Governance & Matching Policy

_Last updated: 2026-06-26 — Design phase, pre-implementation. Reconciled against the live code (PR #772 review)._

Related docs:
- `docs/product/community-platform.md` §Accountability partners (strategy)
- `docs/engineering/community-governance-spec-v1.md` §4.2 (Admin Partner Console)
- `docs/engineering/study-os-comparison-spec.md` (goal-specific compatibility, behavior scores)
- `docs/product/persona-study-policy-contract.md` (persona dimensions — internal use only)

---

## 1. What this doc covers

`docs/product/community-platform.md` defines *what* accountability partnerships are and the minimum-viable matching algorithm. This doc covers:

- Governance model (formation, operation, dissolution)
- Partner-finding hierarchy (user choice vs. recommendation)
- Recommender parameters and scoring policy
- Similar vs. opposite trait matching — the answer and its rationale
- Risk register and mitigations
- Identity and anonymity policy

Schema/admin governance hooks are tracked in `docs/engineering/community-governance-spec-v1.md`. The **current implementation reality** (and where it diverges from this policy) is captured in §8.

---

## 2. Three-moment governance model

Govern the feature across three moments in a pair's lifecycle, not as a single blob.

### 2.1 Formation

| Rule | Rationale / current state |
|---|---|
| Opt-in pool only; minimum activity threshold to enter | Filters bots, day-one ghosts, and abandoned accounts before they waste a committed user's slot. **Not yet implemented.** |
| Mutual consent before a pair exists | **Not enforced today** (§8). Two divergent paths exist: `/community/partner/invite` writes a *pending* `accountability_partner_requests` row but has **no accept/decline route**, so an invite never becomes a pair; `/api/accountability/partners/request` inserts an `accountability_pairs` row at `status='active'` directly, with **no consent step**. The canonical lifecycle must be: **request → recipient accept/decline → one-active-pair guard → atomic pair creation.** |
| One active partner per user, hard enforced | The product contract is *"One person"* (`PartnersScreen.jsx:147`). The schema's `unique(user_a, user_b, status)` (`072_study_os_pairs.sql:13`) blocks duplicate *pair* rows between the same two users, **not** a user holding multiple active pairs. Add a one-active-pair-per-user guard at pair-creation time. |
| Goal-specific exam compatibility (not a universal same-exam filter) | See §4.1. `accountability_pairs.exam_id` is nullable and `pairing_goal` is goal-specific by design. |

### 2.2 Operation

| Rule | Rationale / current state |
|---|---|
| Structured interaction only at launch — check-ins and weekly-review answers; no open DMs | Biggest single abuse-surface reducer; matches current UI scope |
| Partner sees only a sanitized, published projection — never raw profile facts | **Not implemented (§8).** `072_study_os_pairs.sql` governs access to the *pair row* only. Both partner lookups (`community_runtime.py:646`, `social_sessions.py:397`) currently select and return `full_name` and `city`, contradicting §7. A sanitized published-partner DTO is required. |
| Reliability signals derived from the user's own Study OS telemetry, not peer ratings | Prevents retaliation (no rage-quit score-tanking); keeps signals deterministic. Behavior/discipline scoring lives in `study-os-comparison-spec.md`. |
| Check-ins anchored to observable Study OS data where available | Reduces collusion risk; cross-reference `user_events` (hours, mocks) with the self-reported boolean. Today `community_runtime` returns only the caller's check-ins and an empty `thisWeek`, so the UI can retain *seeded* partner metrics after a live fetch (§8). |

### 2.3 Dissolution

| Rule | Rationale / current state |
|---|---|
| Unilateral, no-fault exit; no behavioral penalty | Already: `POST /community/partner/end` (user) and admin `partner_end_pair` |
| Block + rematch-block so a bad pairing never recurs | **Schema and admin write-path exist:** `partner_rematch_blocks` (`105_community_governance.sql:32`, lexicographic unordered pair, `reason >= 8` chars) + `admin_community_governance.py`. The remaining gap is **enforcement in the user matching/invite paths** — the recommender and invite routes do not yet exclude blocked pairs. |
| Dispute path → `moderation_items`, admin-attributed, audited | Trust > Speed; Control > Automation |
| Solo-mode fallback; the active user is never stranded | The "If this partnership ends · Candidates we'd suggest" card (`PartnersScreen.jsx:599`) is the entry point |
| No "your partner missed N days" shame notification to either party | Off-ramp copy stays blameless |

---

## 3. Partner-finding hierarchy

Three entry modes exist (per `community-platform.md:135`):

```
Invite a known person   →  Browse the opt-in pool   →  Auto-match suggestion
       ↑                           ↑                          ↑
   highest                      middle                     fallback
   intent                       intent                     (cold start)
```

**Explicit user choice always supersedes the recommender.** Precedence:

> Accepted invite  >  Browse-selected  >  Auto-match suggestion

Rationale: a self-chosen partner carries intrinsic motivation and consent the algorithm cannot manufacture. The recommender is the cold-start fallback — and at launch, most users will not have a friend on the platform, so the recommender does most of the actual work.

**Friend pairs get the same standard, not an easier one.** Mutual-leniency risk (friends rubber-stamping each other's check-ins) is real. The truth shown in the side-by-side ("Same plan, two columns" — `PartnersScreen.jsx:294`) applies regardless of how the pair formed.

---

## 4. Recommender parameters

Keep the recommender **deterministic and replayable**, mirroring how persona snapshots store `evidence[]`. Never use a black-box ML model for this — the "why" string shown to users must be reproducible by an admin.

### 4.1 Compatibility is goal-specific, not a universal same-exam filter

The pairing goal (`accountability_pairs.pairing_goal`) drives the exam-compatibility rule. This matches the governing contract in `study-os-comparison-spec.md`:

| `pairing_goal` | Exam compatibility | Notes |
|---|---|---|
| `discipline` | **Cross-exam OK** | A time-block / consistency cohort; the comparison is behavioral, not content. `exam_id` may be null. |
| `same_exam` | Same exam required | Content sync. |
| `mock_review` | Same exam strongly preferred | Mock content must line up. |
| `revision` | Same exam | Shared syllabus. |

Other hard filters (apply after goal compatibility):

- Both users opted in to the partner pool
- Neither user is currently in an active pair (one-active-pair guard)
- No `partner_rematch_blocks` row between them (lexicographic unordered pair)

### 4.2 Soft score (weighted)

| Signal | Source | Weight |
|---|---|---|
| Availability window overlap (morning / afternoon / evening) | Onboarding self-assessment / `aspirant_preferences` | **High** |
| Weekly intensity band (target hours, mocks/week) | Commitment declaration + `user_events` rolling average | **High** |
| Prep stage / mock-score band | `preparation_stage` persona dimension; mock score percentile | Medium |
| Reliability band (see §5.2) | Derived from own check-in and task-completion history | Medium |
| Language of check-in notes | Profile language preference | Medium |
| Geography / timezone | Profile city, used only for tiebreaking | Low |

### 4.3 "Why" string rules

The reason string shown on the candidate card must be safe, benign copy. Allowed:

> "Same phase · similar mock cadence · morning person"
> "Both Prelims window · 35–40h/week intensity · overlapping availability"

Not allowed — these surface internal persona labels (`persona-study-policy-contract.md`):

> ❌ "Matched because you're both planner-poor-executors"
> ❌ "Similar study-risk score"
> ❌ "Both have high dropoff risk"

**Persona-derived explanations require a contract update first.** `persona-study-policy-contract.md` currently permits **only** `safe_user_explanation[]` and `safe_user_copy` to reach aspirants. Before any persona signal feeds a match reason, either (a) add and version an approved `safe_match_explanation[]` output in that contract, or (b) restrict candidate reasons to non-persona profile facts (exam, phase, declared availability, declared cadence). Until then, use option (b).

---

## 5. Similar vs. opposite trait matching

Your "smart + lazy" framing collapses two axes that must be treated differently.

### 5.1 Ability and pace — match similar

The UI is a fair peer-comparison ("Same plan, two columns"). That mechanic only works between peers. A large ability gap:

- Demoralizes the weaker user (comparison becomes punishment)
- Is pointless for the stronger user (nothing to learn, emotional labor only)
- Collapses fast (observed in two-week timescale, per `community-platform.md:133`)

Match within a similar mock-score band. For `same_exam` / `mock_review` / `revision` goals also match exam-phase; for `discipline` goals the comparison is behavioral, so phase alignment is optional.

### 5.2 Conscientiousness — match adjacent, not opposite

The idea of pairing a low-conscientiousness user with a high-conscientiousness user to "pull them up" is a trap. Avoid it.

**Why it fails:**

1. **Asymmetric burden.** The disciplined user absorbs the emotional labor of a partner who repeatedly fails to deliver. They are your best users — your retention engine. Burning them to subsidize your least committed cohort is backwards.
2. **Accountability requires symmetry.** When one side chronically underdelivers, the streak breaks and the weekly truth becomes shaming — the exact dynamic your community rules prohibit.
3. **The worst cell: two low-conscientiousness users together.** Mutual collusion — both skip, both excuse each other, the pair becomes a fiction.

**What works instead:**

Match on **adjacent reliability bands**, with a *mild positive asymmetry* — the suggested partner should be marginally more consistent than the user, not orders of magnitude more. A stretch peer, not a savior.

For users who fall below the minimum reliability threshold: do not route them to 1:1 pairing at all. Route them to:
- Study groups (pressure diffused; no single peer to disappoint)
- System nudges and Study OS interventions (persona-driven)
- Mentor sessions (structured, paid, time-bounded)

Do not make your best users their unpaid coaches.

---

## 6. Risk register

| Risk | Mitigation |
|---|---|
| **Ghosting / abandonment** | Auto-pause after N days of mutual silence; prompt to re-pair or go solo; reliability signals visible to admin; replacement candidates always pre-loaded in the UI |
| **Collusion / fake check-ins** | Anchor to Study OS telemetry (hours logged, mocks taken) as a corroborating signal; compare published numbers in the side-by-side; avoid gamification that rewards lying |
| **Harassment / safety** | Structured-only interaction (no DMs at launch); block + report → `moderation_items`; `partner_rematch_blocks` (exists); profanity filter on notes; rate limits on invites |
| **Comparison anxiety** (population includes `deadline_anxious`, `dropoff_risk` persona states) | Similar-level matching; `nudge_style: direct_non_shaming` from the study policy contract; "calm truth" framing in all copy; option to blur the other column |
| **Retaliation via peer scores** | Reliability is a function of the user's own behavior, not a partner-assigned rating — no star-rating-your-partner system |
| **Friendship damage** | Blameless exit; no "your friend missed 5 days" notifications; gentle off-ramp copy at dissolution |
| **Dead pairs clogging the pool** | Auto-pause after mutual silence; regular pool-health admin view (ghost count column in Partner Console spec §4.2) |
| **Bots / fake opt-ins** | Minimum-activity gate to enter pool; lean on existing trust-gating infrastructure |

---

## 7. Identity and anonymity policy

### 7.1 Decision: pseudonymous by default, with mutual progressive reveal

Full anonymity weakens accountability — "I won't let Aman down" is a stronger commitment than "I won't let user_4821 down," and a faceless partner is far easier to ghost.

Forced real names is a safety risk, especially material in this market: women aspirants face documented harassment exposure. Never require real names.

> **Implementation note:** today's code contradicts this section — both partner lookups return `full_name` and `city`. A sanitized published-partner DTO (§8) is a prerequisite for shipping this policy.

### 7.2 Default identity surface

Show at formation and throughout the partnership:

- Persistent display name / handle
- Target exam + preparation phase
- Avatar (color-seeded, no photo required)

Never expose by default: real full name, phone, email, precise location (city), social media handles.

### 7.3 Progressive reveal

| Stage | Shared | How |
|---|---|---|
| Candidate browsing | Handle + exam + phase + match reason | System-shown; no contact |
| Active pair | Above + weekly numbers + check-in notes | Mutual, consent at pair formation |
| Deeper reveal (real name, city) | Only if both parties opt in | Explicit mutual consent toggle, never prompted by the platform |

Friend-invite pairs are already non-anonymous by definition — both parties know each other. No additional restriction needed; consent is implicit in the invite.

### 7.4 Gender preference

Add a same-gender matching preference option and make gender disclosure optional on the profile. In this market, this is a meaningful adoption and safety lever. `profiles` does not currently carry a gender field — this requires a deliberate additive schema change, not a default.

---

## 8. Current implementation reality & gaps

Schema for governance is **already in place**; the gaps are in the user-facing lifecycle, consent, privacy projection, and path reconciliation — not schema creation.

### 8.1 Already implemented
- `partner_rematch_blocks` table + admin write path (`105_community_governance.sql:32`, `admin_community_governance.py`).
- `mentor_verification` sidecar (`105_community_governance.sql:53`).
- Admin partner reads/ends (`admin_community_governance.py`): list pairs, end pair, rematch-block.
- `pairing_goal` enum and nullable `exam_id` (`072_study_os_pairs.sql`) — already supports goal-specific compatibility.

**Lifecycle, consent, and privacy — landed in the partner-consent-lifecycle PR (#776):**
- **Canonical consent-first lifecycle.** `request_partner` now writes a *pending* `accountability_partner_requests` row; the two divergent paths are reconciled (both `/community/partner/invite` and `/api/accountability/partners/request` create pending requests). The `message=` `TypeError` is fixed.
- **Accept/decline route + atomic pair creation.** `respond_partner` is implemented; accept goes through SECURITY DEFINER RPC `accept_partner_request` (`193_partner_consent_lifecycle.sql`).
- **One-active-pair guard** enforced for both users at request time and atomically in the accept RPC.
- **Sanitized published-partner DTO.** `published_partner` strips `full_name`/`city`; applied in `partner_state` and `list_partner_suggestions`.
- **Admin invite triage** now reads pending `accountability_partner_requests` (not paused `accountability_pairs`).

### 8.2 Open gaps (remaining)

| Gap | Detail / where to fix |
|---|---|
| **Partner metrics not returned live** | `community_runtime` returns an empty `thisWeek`; `PartnersScreen.jsx` retains seeded partner metrics after a live fetch. Return the partner's published numbers via the sanitized DTO. |
| **Rematch-block not enforced in matching** | The recommender/invite paths must exclude `partner_rematch_blocks` pairs (schema exists; enforcement does not). |
| **Recommender is a stub** | `community_runtime.py` echoes pending invites with `match: 0`. Build the goal-specific scoring function (§4). |
| **Persona-explanation contract** | Add/version `safe_match_explanation[]` in `persona-study-policy-contract.md`, or restrict reasons to non-persona facts (§4.3). |
| **Gender preference field** | Additive migration on `profiles`; opt-in, not required. |
| **Minimum-activity gate for pool entry** | Eligibility check at the invite/browse endpoints. |
| **Frontend accept/decline wiring** | `PartnersScreen.jsx` does not yet call the new `respond` endpoint. |

---

## 9. Strategic rules (carried from `admin-governance.md §10`)

```
Trust > Speed
Control > Automation
Determinism > Heuristics
```

Accountability partnerships are a trust product. Every governance decision that involves a real person — pairing, dispute, block, dissolution — is admin-audited and human-reviewable. The recommender assists; it does not decide.
