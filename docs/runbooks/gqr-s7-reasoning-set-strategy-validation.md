# GQR-S7 Reasoning set-strategy validation

Use this runbook after PR #1005 is merged and before marking GQR-S7 live-validated.
It covers text/table Reasoning sets only; non-verbal Reasoning remains GQR-S9.

## Preconditions

- Migrations through 262 are applied.
- A verified active Reasoning strategy exists.
- A verified canonical PYQ stimulus is projected into at least two admitted mock-bank questions.
- The selected strategy scope matches every question in that shared set.
- An operator can create a reviewed stimulus-strategy link through the current service-role workflow.

## 1. Apply migration 263

Check the live migration ledger and confirm `263_reasoning_stimulus_strategy_authority.sql` is the next unapplied migration. Apply it through the repository's normal deployment workflow.

Confirm `public.reasoning_stimulus_strategies` exists before continuing.

## 2. Validate RLS and privileges

Run the committed read-only validator:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f app/supabase/validation/validate_reasoning_stimulus_strategy_privileges.sql
```

Expected final output:

```text
ALL PASS — reasoning_stimulus_strategies is RLS-enabled and service-role-only
```

This proves RLS is enabled, no direct client policies exist, anon/authenticated have no direct CRUD privileges, and service_role has the intended privileges.

## 3. Choose a canonical grouped set

Select one text/table `pyq_stimuli` row that is retained by at least two projected questions. Confirm:

- the canonical stimulus is verified;
- all selected questions are admitted for mock use;
- all questions belong to canonical Reasoning taxonomy;
- the selected strategy topic/microtopic scope matches every question;
- when questions span different microtopics, the strategy is topic-scoped rather than microtopic-scoped.

Record the stimulus ID, strategy ID, and question IDs.

## 4. Create the governed link

Using the current service-role link workflow:

1. Create the `reasoning_stimulus_strategies` row as pending.
2. Set relevance deliberately.
3. Review it to verified with reviewer attribution and timestamp.
4. Re-read the link and confirm:
   - link status is verified;
   - strategy status is verified;
   - strategy is active.

Do not add learner table policies or expose this table directly to the browser.

## 5. Submit a grouped mock

Using a learner account:

1. Start a regular or generated mock containing at least two questions with the selected canonical stimulus.
2. Confirm the shared text/table stimulus renders during the attempt.
3. Submit the attempt and record its ID.

S7 strategies are review-only; active-attempt strategy rendering is not valid evidence.

## 6. Validate the review API

Call:

```text
GET /api/study/mocks/attempts/<ATTEMPT_ID>/review
```

Confirm the additive `stimulus_solution_strategies` response contains one group for the selected stimulus with:

- `pyq_stimulus_id`;
- grouped `question_ids` in frozen attempt order;
- `first_attempt_order`;
- learner-safe strategy fields.

Confirm governance, applicability, topic, audit, and CAS fields are absent. Existing `questions[].solution_strategies` must remain independent and unchanged.

A question carrying two canonical stimuli must retain two separate groups rather than flattening them.

## 7. Validate browser rendering

Open the submitted review and confirm:

- **Set-solving approach** appears above the question renderer;
- each applicable canonical stimulus has its own panel;
- question-specific **Solution Strategy** still appears in its local panel;
- unrelated questions show no set panel;
- active attempts show no set panel;
- the frozen stimulus content remains unchanged.

Capture the response and screenshots as operator evidence.

## 8. Prove live withdrawal

Move the stimulus link out of verified state, reload the same submitted review, and confirm the set strategy disappears immediately while the core review, frozen stimulus, and question-specific strategies remain available.

Restore the intended final state only after recording the result and receiving the content decision.

## 9. Record evidence

Record:

- environment and deployment SHA;
- live migration maximum and migration 263 result;
- privilege-validator output;
- stimulus, strategy, link, question, and attempt IDs;
- API response excerpt;
- browser screenshots;
- withdrawal result;
- operator identity and timestamp.

Create one immutable evidence record from `docs/operator-validation/EVIDENCE_TEMPLATE.md`, append it to gate `gqr-s7-live-validation` in `docs/operator-validation/registry.json`, update the gate status, and regenerate `docs/operator-validation/INDEX.md`. Do not mirror operator status into the GQR or global checklist.
