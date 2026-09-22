# RBI-ENG-CHILD-01 — RBI English essay child-prompt load spec

**Type:** operator run. 16 new `pyq_questions` rows plus 4 parent metadata updates.

**Migration dependency:** none. This load can run before or after the
`essay_pyq_tags.format` schema PR (migration `304_essay_pyq_tags_format.sql`).
Only the *tagging* of these rows waits on `format` — creating the rows does not.

The numbering block below is also recorded in migration 304's header so the
schema and this spec cannot drift apart.

---

## 1. Parents (4) — one per paper, all `question_number = 1`

| year | paper_id | parent question_id |
|---|---|---|
| 2022 | `4f15f17d-542b-421e-81d0-b6280ea7c67b` | `36adb921-429e-40fc-b788-0606c25b36e3` |
| 2023 | `b046e6fa-bb3a-46dc-846a-2e791d5f342f` | `a67db400-d253-4ea3-bf62-fef97081c7b8` |
| 2024 | `e0a9e855-085b-4a26-9710-63b295fd40d7` | `5697c38f-02eb-4bc2-bd7a-6bc8f95c02ee` |
| 2025 | `9ca02669-5875-4e97-b2bb-5f04ed49e94b` | `106fcb3e-e237-4429-889f-e4939d785ee1` |

## 2. Child numbering — per paper, 301–304

| prompt_index | question_number | display_order | source_question_ref |
|---|---|---|---|
| 1 | 301 | 301 | `ENG-Q1-P1` |
| 2 | 302 | 302 | `ENG-Q1-P2` |
| 3 | 303 | 303 | `ENG-Q1-P3` |
| 4 | 304 | 304 | `ENG-Q1-P4` |

The same numbers are used on all four papers. Uniqueness is per paper, and these
papers occupy `question_number` 1–15 only — confirmed. The 300-block leaves
16–299 free and clears the 200 already in use elsewhere on RBI (a Phase I paper
reaches `question_number` / `display_order` 200).

## 3. Child field values

```
pyq_paper_id        = parent's paper_id
section_id          = parent's section_id (the English section for that year)
question_number     = 301..304
display_order       = same as question_number
question_text       = the single prompt, verbatim, WITHOUT the container instruction line
question_type       = 'descriptive'
correct_option_id   = null
source_question_ref = ENG-Q1-P{n}
reviewer_status     = pending (CMS-born)
metadata            = { "parent_question_id": "<parent uuid>",
                        "prompt_index": n,
                        "prompt_of": "ENG-Q1",
                        "marks": 40,
                        "word_limit": "<parent's word_limit>",
                        "is_child_prompt": true }
```

## 4. Parent update (4 rows)

`metadata` is a whole-column replace, so read–merge–write:

```
metadata += { "is_container": true,
              "child_count": 4,
              "child_refs": ["ENG-Q1-P1","ENG-Q1-P2","ENG-Q1-P3","ENG-Q1-P4"] }
```

Leave `question_text` as-is — it stays the container instruction. The parent
gets no theme tag; tags go on children only.

## 5. Prompt text source

`workbench/sources/rbi-descriptive-english.json`, essay rows only. Strip:

- the leading instruction — "Write an essay on any one of the following topics…"
- the bullet or letter marker — `•`, `a)`, `A.`

16 prompts total, 4 per year.

## 6. POST route

```
POST /api/admin/exam-intelligence-cms/pyq-questions
body: { reason: "<string>", payload: { ...fields } }
```

Read `.row.id` from the response, **not** `.id`.

## 7. Known failure modes (from the 2022 UPSC Essay load)

- `display_order` is globally unique **per paper**, not per section — hence
  301–304, not 1–4.
- `source_question_ref` is unique per paper — hence the `-P{n}` suffix.
- Identical `question_text` trips a content-hash unique constraint. All 16
  prompts are distinct, but verify before posting.
- JWT expiry mid-batch → rebuild `$headers` after refreshing
  `$env:CCP_ADMIN_JWT`, then retry the whole batch.
  `uq_pyq_questions_idempotency_key` makes re-posting safe when
  `idempotency_key` is set.
- PowerShell 5.1: use `[System.Text.Encoding]::UTF8.GetBytes($payload)` with
  `-Body $bytes` and `Content-Type: application/json; charset=utf-8`.

## 8. Verification after load

```sql
SELECT p.year, count(*) children
FROM pyq_questions q JOIN pyq_papers p ON p.id = q.pyq_paper_id
WHERE q.question_number BETWEEN 301 AND 304
  AND q.pyq_paper_id IN ('4f15f17d-542b-421e-81d0-b6280ea7c67b','b046e6fa-bb3a-46dc-846a-2e791d5f342f',
                         'e0a9e855-085b-4a26-9710-63b295fd40d7','9ca02669-5875-4e97-b2bb-5f04ed49e94b')
GROUP BY 1 ORDER BY 1;
-- expect 4 per year, 16 total

SELECT count(*) FROM pyq_questions
WHERE metadata->>'is_child_prompt' = 'true';
-- expect 16
```

## 9. After the load

The English worksheet's 16 essay rows retarget from `parent_question_id` to the
new child `question_id`s, matched on `prompt_index`. The 8 précis/comprehension
rows keep their existing parent ids.
