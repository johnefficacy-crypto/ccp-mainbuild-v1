"""ROADMAP-01 thresholds — the only place these numbers live.

The syllabus roadmap derives a per-topic state at read time from these five
constants. Nothing else hard-codes them: the endpoint returns them in its
payload so the Progress tab legend renders what the backend actually used.

MASTERED_AT deliberately equals report_cards._HIGH_YIELD_MASTERED_THRESHOLD so
"mastered" means the same thing on the roadmap and the weekly report card; a
test guards the pair against drift. report_cards is not changed.
"""
from __future__ import annotations

# Below this score, with enough attempts behind it, a macro topic is weak.
WEAK_BELOW = 50.0

# At or above this score, with enough attempts behind it, a macro topic is mastered.
MASTERED_AT = 75.0

# Attempts needed before a score can call a topic weak or mastered. A single
# attempt lands at a 35.00 floor, which is not a measured weakness.
MIN_ATTEMPTS = 2

# A mastered topic untouched for MORE than this many days is flagged for revision.
REVISE_AFTER_DAYS = 14

# Mastery-history points returned per macro topic (most recent, ascending).
HISTORY_POINTS = 10
