# Accountability Partner — Governance & Matching Policy

_Last updated: 2026-06-25 — Design phase, pre-implementation_

Related docs:
- `docs/product/community-platform.md` §Accountability partners (strategy)
- `docs/engineering/community-governance-spec-v1.md` §4.2 (Admin Partner Console)
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

Implementation hooks (admin console, schema gaps) are tracked in `docs/engineering/community-governance-spec-v1.md`.

---

## 2. Three-moment governance model

Govern the feature across three moments in a pair's lifecycle, not as a single blob.

### 2.1 Formation

| Rule | Rationale |
|---|---|
| Opt-in pool only; minimum activity threshold to enter | Filters bots, day-one ghosts, and abandoned accounts before they waste a committed user's slot |
| Both sides must consent — invite is a request, not an auto-pair | `accountability_partner_requests.status='pending'` already enforces this; keep it |
| One active partner per user, hard enforced | The product contract is *"One person"* (`PartnersScreen.jsx:147`). The schema's `unique(user_a, user_b, status)` blocks duplicate *pair* rows, not a user holding multiple active pairs. Add a one-active-pair-per-user guard at write time. |
| Same/overlapping target exam required | Hard filter; non-negotiable per `community-platform.md` |

### 2.2 Operation

| Rule | Rationale |
|---|---|
| Structured interaction only at launch — check-ins and weekly-review answers; no open DMs | Biggest single abuse-surface reducer; matches current UI scope |
| "Partner sees what you publish, nothing more" | Literal RLS enforcement; already scoped in `072_study_os_pairs.sql` |
| Reliability signals derived from the user's own Study OS telemetry, not peer ratings | Prevents retaliation (no rage-quit score-tanking); keeps signals deterministic |
| Check-ins anchored to observable Study OS data where available | Reduces collusion risk; cross-reference `user_events` (hours, mocks) with the self-reported boolean |

### 2.3 Dissolution

| Rule | Rationale |
|---|---|
| Unilateral, no-fault exit; no behavioral penalty | Already: `POST /community/partner/end`; keep the exit cheap |
| Block + rematch-block so a bad pairing never recurs | `partner_rematch_blocks` table specced in community-governance-spec-v1 §4.2 |
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

### 4.1 Hard filters (all must pass before scoring)

- Same or overlapping target exam
- Same exam phase (Prelims window vs. Mains window — a Prelims-week user and a Mains-week user have nothing to compare)
- Both users opted in to the partner pool
- Neither user is currently in an active pair
- No `partner_rematch_blocks` row between them

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

Not allowed — these surface internal persona labels (`persona-study-policy-contract.md:161`):

> ❌ "Matched because you're both planner-poor-executors"
> ❌ "Similar study-risk score"
> ❌ "Both have high dropoff risk"

Match on the internal signal; surface a benign, behavioral reason.

---

## 5. Similar vs. opposite trait matching

Your "smart + lazy" framing collapses two axes that must be treated differently.

### 5.1 Ability and pace — match similar

The UI is a fair peer-comparison ("Same plan, two columns"). That mechanic only works between peers. A large ability gap:

- Demoralizes the weaker user (comparison becomes punishment)
- Is pointless for the stronger user (nothing to learn, emotional labor only)
- Collapses fast (observed in two-week timescale, per `community-platform.md:133`)

Match within the same exam-phase and within a similar mock-score band.

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
| **Harassment / safety** | Structured-only interaction (no DMs at launch); block + report → `moderation_items`; rematch-block; profanity filter on notes; rate limits on invites |
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

### 7.2 Default identity surface

Show at formation and throughout the partnership:

- Persistent display name / handle
- Target exam + preparation phase
- Avatar (color-seeded, no photo required)

Never expose by default: real full name, phone, email, precise location, social media handles.

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

## 8. Open implementation gaps

These are not addressed by any existing migration or route:

| Gap | Where to fix |
|---|---|
| One-active-pair-per-user invariant not enforced in schema | Add check/trigger in migration after `072_study_os_pairs.sql` |
| Reliability / ghost score not computed anywhere | New derived column or materialized view; feed `admin_community_governance.py` |
| `partner_rematch_blocks` table not yet created | Schema delta in `community-governance-spec-v1.md` §4.2 |
| Recommender returns echoed pending invites only (`community_runtime.py:661`) | Build the scoring function in `community_runtime.py` or a new `partner_matcher.py` |
| Gender preference field missing from `profiles` | Additive migration; opt-in, not required |
| Minimum-activity gate for pool entry | Eligibility check at `/community/partner/invite` and browse endpoint |

---

## 9. Strategic rules (carried from `admin-governance.md §10`)

```
Trust > Speed
Control > Automation
Determinism > Heuristics
```

Accountability partnerships are a trust product. Every governance decision that involves a real person — pairing, dispute, block, dissolution — is admin-audited and human-reviewable. The recommender assists; it does not decide.
