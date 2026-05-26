# Attempt Analytics (PR4a)

## Classifier rule order (first match wins)
1. `correct`
2. `silly_mistake`
3. `calc_error`
4. `option_trap`
5. `concept_gap`
6. `marked_unanswered`
7. `time_pressure_unattempted`
8. `knowledge_gap`

## Time analytics fallback
Primary source is `mock_attempt_events` (`question.visited` transitions). If event rows are unavailable/malformed, the library falls back to `mock_attempt_responses.time_spent_sec` and emits a warning.

## Output contract
Public contract lives in `app/backend/app/study_os/attempt_analytics/schemas.py` and exposes:
- attempt summary
- section/topic breakdowns
- per-response classification
- stuck/rush question sets
- warning metadata
