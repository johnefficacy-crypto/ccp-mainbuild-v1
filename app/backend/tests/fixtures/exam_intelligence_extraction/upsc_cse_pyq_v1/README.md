# UPSC CSE PYQ v1 Fixtures

Read docs/engineering/exam-intelligence-extraction-v1-corpus.md first.

This directory holds hand-labeled ground truth for the deterministic PYQ
extractor v1. Labels are produced via the bbox labeler tool (see PR0.5).

Files:
- questions.schema.json — JSON Schema for the fixture format
- questions.json        — labeled questions (empty skeleton until PR1)
- options.json          — deferred to v2
- topic_tags.json       — deferred to v3

Do not hand-edit bbox coordinates. Use the labeler tool.

Do not commit labeled fixtures derived from copyrighted UPSC content unless
the legal review has cleared inclusion. Until cleared, store labels in a
separate private location and reference document_assets.id only.
