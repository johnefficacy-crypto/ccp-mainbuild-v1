# Corpus readiness

> **Example output — fixture data, not live counts.** Every number below comes from a committed test fixture. An operator regenerates this file against a real database with `python scripts/corpus_readiness_report.py --live --source demo`.

> **STALE — REG-CORPUS-02 (2026-09-25).** Topic practice, the blueprint base pool and mock-readiness depth now also admit authored `mock_question_bank` rows (`source_kind='authored'`, `exam_id` NULL) for exams with a topic-exam key (SEBI, PFRDA, IFSCA), scoped by `topics.metadata.exams` (`app/backend/app/exam_intelligence/authored_scope.py`). The `projection` read above counts PYQ-projected rows only, so it under-counts practisable topics for those three exams. That PR had no DB access; nothing below was regenerated or hand-edited.

- generated-at: 2026-09-22
- mode: fixture
- source: demo
- script version: 1.0

<details><summary>Exact queries used</summary>

```sql
subjects        select id, name, slug from subjects
exams           select id, slug, name, is_active from exams
topics          select id, subject_id, parent_topic_id, level, is_active from topics
                  where is_active is not false
papers          select id, exam_id, trust_status, source_type, source_url,
                       source_document_id, metadata from pyq_papers
questions       select id, pyq_paper_id, exam_id, reviewer_status, question_type,
                       metadata from pyq_questions
tags            select question_id, topic_id, tag_role, reviewer_status
                  from pyq_question_topic_tags
                  where tag_role = 'primary' and reviewer_status = 'verified'
projection      select id, pyq_question_id, topic_id, microtopic_id
                  from mock_question_bank
coverage        select exam_id, topic_id, reviewer_status, exam_phase_id
                  from exam_topic_coverage
Every read paginates via app/common/pagination.py — a short page is not the
last page. No statement in this script writes, and none calls a review RPC.
The gate verdict in section 3 is READ from pyq_papers.trust_status (--live) or
supplied per paper by the fixture; it is never computed from the columns above.
```

</details>

**Exclusions, applied in every section below.** Retired buckets (`metadata.retired` truthy) are dropped along with everything hanging off them. Thematic optional rows (`metadata.corpus_half='thematic'`) are counted as questions but never as papers — they carry no paper order. Topics with `is_active = false` are dropped, and never supply a subject to a question. Subjects reach their counts through `topics.subject_id`, never through `metadata.exams`: the shared body-agnostic subjects do not carry that key and any exam filter would empty them.

## 1. Corpus per subject × exam

| subject | exam | micro | macro | tagged | verified | descriptive | projected |
|---|---|---:|---:|---:|---:|---:|---:|
| General Intelligence and Reasoning | national-nabard-grade-a | 1 | 1 | 1 | 1 | 0 | 1 |
| General Studies I | upsc-cse | 1 | 1 | 3 | 3 | 3 | 0 |
| Quantitative Aptitude | national-nabard-grade-a | 2 | 1 | 2 | 2 | 0 | 2 |

## 2. Feature readiness per subject

Derived from the counts in section 1, never asserted. The rule for each column, in one line:

- `mcq_practice` — projected > 0
- `topic_mastery` — projected rows carrying microtopic_id AND >=1 locked coverage row
- `answer_writing` — verified descriptive questions AND tags present
- `syllabus_navigation` — macro AND micro layers both present

| subject | mcq_practice | topic_mastery | answer_writing | syllabus_navigation |
|---|---|---|---|---|
| General Intelligence and Reasoning | yes | no | no | yes |
| General Studies I | no | no | yes | yes |
| Quantitative Aptitude | yes | yes | no | yes |

## 3. Blocked corpora

**This section never computes the gate's verdict.** `review_pyq_paper` is the authority, and it is PL/pgSQL (migration `271_review_pyq_paper_question_count_gate.sql`, previously 185/186). It is a review action rather than a predicate — it locks rows, writes an audit row and updates `trust_status` — and it offers no dry-run path, so this report does not call it. Nor does it re-implement the Python re-statement at `admin_exam_intel_cms.py:1266-1298`.

So what follows is the observable provenance fields the gate reads, plus a verdict that was **observed or operator-supplied, never derived here**. Each exam names its own source below. A paper carrying no verdict is reported as "gate verdict unavailable" — never as passing. A gate that moves cannot silently desync this document, because this document transcribes none of its logic.

`scripts/ssc_cgl_readiness.py` is the older single-exam report over this same ground for SSC CGL; it does re-state the gate in Python, and this report deliberately does not.

### ssc-cgl

- 2 questions exist; 2 are not verified, 2 carry no verified primary tag, 2 objective questions are not projected.
- 2 papers in scope. Observed provenance fields: 2 are not `source_type='official'`; 1 has no `source_url`; 2 have no `source_document_id`; 2 are not `trust_status='verified'`; 0 carry no questions.
- Gate verdict, migration `271_review_pyq_paper_question_count_gate.sql` in force: 0 passing, 1 failing, 1 unavailable. Source: `operator:2026-09-22 /rpc/review_pyq_paper error`. Observed or supplied — not computed by this report. Recorded reasons: blocking_fields=source_type,source_url.

## 4. Catalogues with zero questions

- Banking
- Capital Market
- English Language
- Orphan Microtopics

## 5. Topic trees

| subject | macro | micro | micro without a macro layer |
|---|---:|---:|---|
| English Language | 1 | 1 | no |
| General Intelligence and Reasoning | 1 | 1 | no |
| General Studies I | 1 | 1 | no |
| Orphan Microtopics | 0 | 2 | **yes** |
| Quantitative Aptitude | 1 | 2 | no |

