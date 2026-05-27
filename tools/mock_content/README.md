# mock-content CLI

Local content authoring/validation CLI for PR2 import schema.

## Install

```bash
cd tools/mock_content
pip install -e .
```

## Commands

- `mock-content validate <file.csv>`
- `mock-content fingerprint <file.csv> [--out output.csv]`
- `mock-content dedupe <file.csv> --against bank_snapshot.csv [--out report.csv]`
- `mock-content normalize <file.csv> [--out clean.csv]`
- `mock-content tag-coverage <file.csv>`
- `mock-content sample-template [--out-dir .]`

## Fingerprint contract

Fingerprint algorithm and versioning are locked in `schema.json` under `fingerprint_version` and `fingerprint`.
Any PR2 trigger changes must bump both sides together.

## Snapshot contract

`dedupe` requires snapshot columns:
- `id`
- `question_fingerprint`
- `question_text`
- `exam_family`

Extra columns are ignored.
