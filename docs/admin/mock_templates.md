# Mock Templates (PR2d)

## Selector schema

- `criteria` mode uses filters and optional `difficulty_mix` that must sum to 1.0 ±0.001.
- `fixed` mode uses exact `question_ids`, and list length must match `question_count`.

## Preview selection contract

`POST /api/admin/mocks/templates/{id}/preview-selection`

Returns per-section availability and explicit gaps:

```json
{
  "sections": [{"name": "Quant", "requested": 35, "available": 28, "gaps": [{"reason": "difficulty_hard", "needed": 7, "available": 2}]}],
  "has_gaps": true
}
```

## Common gap reasons

- `fixed_unpublished`: one or more fixed questions are not currently publishable in bank state.
- `difficulty_hard`: hard bucket supply below requested distribution.
- `topic_percentage`: topic filter mix cannot be satisfied with current bank.
