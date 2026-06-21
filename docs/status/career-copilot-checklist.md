# Career Copilot — Bug / Feature Checklist

| ID        | Area              | Description                                                                 | Status                          |
|-----------|-------------------|-----------------------------------------------------------------------------|---------------------------------|
| BUG-EI-1  | Exam Intelligence | `POST /api/admin/exam-intelligence/workspace/{exam_id}/syllabus/propose` always returns 404 — proposer queried `document_assets` (no `exam_id` column) instead of `syllabus_documents` | CODE-FIXED, VALIDATION PENDING |
