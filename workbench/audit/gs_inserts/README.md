# GS missing-question staging

Reviewable staging for the UPSC CSE Mains GS gap repair. Nothing here is in
the DB until a human approves it and an operator runs the loader with `--live`.

| file | written by | human edits |
|---|---|---|
| `<year>_<paper>.json` | `scripts/extract_gs_missing.py` | no - regenerate |
| `review.csv` | extractor (merged on re-run) | `approved` Y/N, `edited_text`, `edited_marks`, `reviewer_note` |
| `near_matches.csv` | extractor | read-only; 0.60-0.85 matches are never loadable |
| `tag_review.csv` | `scripts/propose_gs_insert_tags.py` (merged on re-run) | `approved`, `edited_slug`, `essay_type`, `reviewer_note` |
| `provenance.json` | hand-filled | `source_document_id` or `source_url` per 2026 paper |
| `summary.md` | extractor | no |

Order:

1. `python scripts/extract_gs_missing.py` - re-run after any OCR/snapshot change.
2. Review `review.csv`. Rows with `low_confidence=Y` need the text checked
   against the official PDF (`flags` says why). `marks_unread` rows need
   `edited_marks` if the marks should be stored.
3. `python scripts/propose_gs_insert_tags.py [--essay-themes essay_themes.jsonl]`, review `tag_review.csv`.
4. Fill `provenance.json` for every 2026 paper being created.
5. `DATABASE_URL=... python scripts/load_gs_inserts.py` (dry run against the DB), then `--live`,
   then `--live --tags-csv workbench/audit/gs_inserts/tag_review.csv --reviewer-id <profiles.id>`.
