---
audit_type: f3_extraction_archive_race_validation
status: PASS
validation_date: 2026-07-02
candidate_main_sha: 920024c48cba7613bc456ffa65d8b805114f9b63
deployed_sha: 920024c48cba7613bc456ffa65d8b805114f9b63
environment: staging
outcome: OPERATOR_PASS
---

# F3 Extraction Archive-Race Validation — 2026-07-02

## Verdict

**PASS — a document archived during active extraction did not leave its processing job stranded in `running`.**

F3 is operator-validated on staging at deployed SHA
`920024c48cba7613bc456ffa65d8b805114f9b63`.

## Deployment preconditions

| Check | Result | Evidence |
|---|---|---|
| Render status | PASS | `live` |
| Candidate SHA | PASS | `920024c48cba7613bc456ffa65d8b805114f9b63` |
| Deployed SHA | PASS | `920024c48cba7613bc456ffa65d8b805114f9b63` |
| Candidate == deployed | PASS | Exact match |
| Render instance count | PASS | `1` |
| `FF_MOCK_MASTERY_WRITES` | PASS | `shadow` |
| `FF_MOCK_MASTERY_LIVE_USER_IDS` | PASS | Populated with verified named user IDs |
| `ENABLE_SCHEDULER` | PASS | `true` |
| `DISABLE_SCHEDULER` | PASS | Not applied |

## Test fixture

| Item | Value |
|---|---|
| Document ID | `96e1c1cd-c461-49a3-9785-773d783f4f06` |
| Text-extract job ID | `c57170f9-c0aa-4af6-bbb5-b0596efefdf7` |
| Document kind | `note_pdf` |
| PDF page count | `120` |
| PDF size | `382213` bytes |
| Initial document status | `uploaded` |
| Initial job status | `queued` |

The PDF was a disposable staging-only fixture generated specifically for this
validation.

## Procedure

1. Uploaded the disposable PDF through the signed personal-library upload flow.
2. Confirmed a queued `text_extract` processing job existed.
3. Started `POST /api/library/items/{document_id}/process-text`.
4. Polled the staging database through owner-authorized Supabase REST access.
5. Confirmed the job transitioned to `running`.
6. Confirmed the document transitioned to `processing`.
7. Updated the owned document status to `archived` while extraction remained active.
8. Waited for extraction finalization.
9. Read the final job, document, API response, and document-page count.

No service-role credential was used. The archive mutation used the authenticated
document owner's update permission under the personal-library RLS policy.

## Raw result

| Evidence | Result |
|---|---|
| Job observed during race | `running` |
| Document observed during race | `processing` |
| Archive rows updated | `1` |
| Extraction HTTP result | `400` |
| Extraction error code | `document_archived` |
| Final job status | `failed` |
| Final job error code | `document_archived` |
| Final document status | `archived` |
| Final page count | `0` |
| Job started at | `2026-07-02T13:27:36.710067+00:00` |
| Job finished at | `2026-07-02T13:27:42.559845+00:00` |

## Contract assertions

| Assertion | Result |
|---|---|
| Archive occurred after extraction claim | PASS |
| Finalization detected archived document | PASS |
| Processing job did not remain `running` | PASS |
| Job terminalized with `error_code=document_archived` | PASS |
| Archived document was not overwritten by runner | PASS |
| No extracted pages were committed | PASS |

## Fixture disposition

The document remains soft-archived on staging. Its failed processing job is
terminal and requires no manual reset.

## Release disposition

- F3 code fix: **PRESENT**
- F3 staging validation: **OPERATOR PASS**
- F3 release gate: **CLEAR**
- P5 PR #800 staging validation and 36-file boundary approval: **STILL PENDING**
- T0 / P8 window start: **NOT SET**

F3 clearance alone does not start the 14-day shadow window. P5 and T0
conditions 5–7 must still hold simultaneously before `window_start` is
recorded.
