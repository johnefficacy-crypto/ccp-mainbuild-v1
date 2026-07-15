# Exam Intelligence operator activation runbook

This is a reusable procedure. It is not a second status checklist; execution status and evidence belong to `docs/operator-validation/registry.json`.

| Order | Operator step | Code-backed surface | Acceptance boundary |
|---:|---|---|---|
| 1 | Confirm permissions and feature flag | `ADMIN_STUDY_OS_ENABLED`, `exam_intelligence.cms`, `exam_intelligence.manage`, `exam_intelligence.review` | Confirm the environment flag and app-metadata grants. CMS, Manage Exam, and review remain separate authorities. |
| 2 | Select or create target exams | `/admin/exam-intelligence`, `/admin/exam-intelligence/new`, `/admin/exam-intelligence/exams/:exam_id` | Record exam identity, family, organization, business priority, cadence, and active state. |
| 3 | Create cycles, phases, and sections | Manage Exam → Setup | Record cycle/phase identifiers and verify audit-backed create/update/template promotion. |
| 4 | Upload official/source PDFs | Manage Exam → Documents | Complete signed upload, storage PUT, complete-upload, extraction, page creation, and document classification. |
| 5 | Link documents to syllabus/PYQ rows | Documents panel | Confirm linking creates provenance but does not silently verify; changed provenance returns trust to pending where required. |
| 6 | Build topic, microtopic, and alias base | Manage Exam → Syllabus Mapper | Confirm canonical taxonomy and aliases; do not use global fallback for empty exam coverage. |
| 7 | Run syllabus mapping | Syllabus Mapper | Review proposals and page text, preview, then commit with reason; committed rows remain reviewable. |
| 8 | Review syllabus mentions | Review queue / Syllabus deep link | Resolve pending and needs-correction mentions before trust consumption. |
| 9 | Create and lock exam topic coverage | CMS/coverage review | Confirm rows begin pending_review and only reviewed/locked rows feed downstream consumers, locked preferred. |
| 10 | Add PYQ sources and papers | Manage Exam → PYQ Workbench | Record valid source type and `source_url` or `source_document_id`. |
| 11 | Verify PYQ source/paper trust | PYQ Workbench | Exercise atomic review and confirm material provenance changes require re-review. |
| 12 | Import PYQ questions/options/stimuli | PYQ Workbench bulk import / paper workspace | Run preflight, duplicate detection, commit-token, and idempotency checks; imported content remains pending. |
| 13 | Review PYQ questions, options, tags, stimuli | Review queue | Review every applicable entity and preserve audit evidence. |
| 14 | Compute, review, and lock score snapshots | PYQ Workbench → Score Snapshots | Exercise compute and lifecycle; only locked snapshots may feed planner signals. |
| 15 | Add policy updates | Manage Exam → Updates / CMS | Only official verified updates may set plan/deadline/eligibility/syllabus/vacancy impact flags. |
| 16 | Add competition and candidate-count facts | Manage Exam → Competition | Attach evidence and complete the reviewed/locked lifecycle before Study OS consumption. |
| 17 | Clear activation blockers | Manage Exam → SmartHeader / Review & Activate | Resolve the backend readiness model's first blocker and record final activation status and next action. |

Evidence must include environment, deployment SHAs, migration head, operator identity, target exam/cycle/phase IDs, outputs for each applicable step, defects found, defects fixed, and final disposition.
