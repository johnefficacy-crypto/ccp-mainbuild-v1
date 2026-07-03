# Writing-prompt bank seed (Content Studio)

Authored seed for the English writing-prompt bank — **270 prompts** across the
five checklist targets. Source of truth for the counts:
`docs/status/career-copilot-checklist.md` → "Prompt bank seed".

| Batch file | Exercise type | Topic | Count |
|---|---|---|---|
| `01_sentence_construction.json` | `sentence_construction` | sentence-construction | 50 |
| `02_sentence_correction.json` | `sentence_correction` | sentence-construction | 50 |
| `03_grammar.json` | `sentence_correction` | grammar | 100 |
| `04_vocabulary.json` | `vocabulary_in_context` | vocabulary-in-context | 50 |
| `05_paragraph.json` | `paragraph_writing` | paragraph-writing | 20 |
| **Total** | | | **270** |

## This is PENDING content — it needs review to go live

Every prompt is authored as **Content Studio pending content**. The batches are
`{reason, subject_id, rows}` payloads for the audited bulk-import write path
(`POST /api/admin/content-studio/writing-prompts/bulk` →
`cms_bulk_upsert_writing_prompts`, migration 215), so on import each prompt lands
`reviewer_status='pending'` / `is_active=false`. It must pass the reviewer
lifecycle (Content Studio → Review Queue) to reach `verified`, and it stays
inactive until the activation gate is lifted. **We do not seed rows with raw
`INSERT`** — that would bypass the review lifecycle and audit trail that the
verified-only-reads governance depends on.

## IDs are deterministic (no slug resolution needed)

`subject_id` / `topic_id` / `microtopic_id` are the exact UUIDs migration 205
assigns: `md5('ewp:subject:english-language')`, `md5('ewp:topic:<slug>')`,
`md5('ewp:microtopic:<slug>')`. So the emitted UUIDs resolve against any
205-seeded database. `subject_id` is `dae70ac3-f38c-2a75-7e4c-ce7b7aae85fd`
(english-language). Rows carry **no** `subject_id` (it is batch-level) and **no**
exam columns (prompts are subject-scoped).

## Regenerating

`build_seed.py` holds the curated content and emits the JSON. It validates every
row against the backend rules (single-token `required_words` via the migration
215 tokenizer, difficulty 1–10, `max_words ≥ min_words`, unique `external_key`)
and fails loudly on any violation:

```bash
python3 build_seed.py
```

`external_key`s (`ewp-seed-<cat>-NNN`) are stable, so re-importing an unchanged
row is a no-op and a corrected-then-re-imported row updates in place (subject-
scoped idempotency).

## Importing (operator, once RPCs + permissions are provisioned)

Prerequisites (OPERATOR PENDING per the #855 checklist row): migrations 213→215
applied, and a `content_studio.author` operator. Then either upload each JSON in
Content Studio → **Bulk Import**, or POST it directly, e.g.:

```bash
curl -X POST "$API/api/admin/content-studio/writing-prompts/bulk" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data @03_grammar.json
```

Import order does not matter (batches are independent). After import, review in
Content Studio → Review Queue: each row shows the full prompt snapshot; verify
sound prompts, or send weak ones to `needs_correction`.
