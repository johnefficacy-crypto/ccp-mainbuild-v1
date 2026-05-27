"""Event type constants for mock attempt telemetry (PR2b).

Application-layer validation — the DB column is unconstrained text so PR3/PR5
can add new event types without a migration.
"""
from __future__ import annotations

# ── Lifecycle — server-emitted ─────────────────────────────────────────────────
ATTEMPT_STARTED        = "attempt.started"
ATTEMPT_RESUMED        = "attempt.resumed"
ATTEMPT_SUBMITTED      = "attempt.submitted"
ATTEMPT_AUTO_SUBMITTED = "attempt.auto_submitted"
ATTEMPT_EXPIRED        = "attempt.expired"

# ── Question interaction — client-emitted, server-corroborated ─────────────────
QUESTION_VISITED  = "question.visited"
QUESTION_ANSWERED = "question.answered"
QUESTION_MARKED   = "question.marked"
QUESTION_UNMARKED = "question.unmarked"
QUESTION_CLEARED  = "question.cleared"

# ── Anti-cheat foundation — client-emitted, record-only ───────────────────────
ATTEMPT_TAB_BLURRED = "attempt.tab_blurred"
ATTEMPT_TAB_FOCUSED = "attempt.tab_focused"
ATTEMPT_COPY        = "attempt.copy"
ATTEMPT_PASTE       = "attempt.paste"

# ── Drift detection — client-emitted ──────────────────────────────────────────
ATTEMPT_HEARTBEAT = "attempt.heartbeat"

# ── Answer-save sync UX (PR-fix-7) — client-emitted, record-only ──────────────
ANSWER_SAVE_FAILED  = "answer.save_failed"
ANSWER_SAVE_RETRIED = "answer.save_retried"

KNOWN_CLIENT_EVENTS: frozenset[str] = frozenset({
    QUESTION_VISITED,
    QUESTION_ANSWERED,
    QUESTION_MARKED,
    QUESTION_UNMARKED,
    QUESTION_CLEARED,
    ATTEMPT_TAB_BLURRED,
    ATTEMPT_TAB_FOCUSED,
    ATTEMPT_COPY,
    ATTEMPT_PASTE,
    ATTEMPT_HEARTBEAT,
    ANSWER_SAVE_FAILED,
    ANSWER_SAVE_RETRIED,
})

KNOWN_SERVER_EVENTS: frozenset[str] = frozenset({
    ATTEMPT_STARTED,
    ATTEMPT_RESUMED,
    ATTEMPT_SUBMITTED,
    ATTEMPT_AUTO_SUBMITTED,
    ATTEMPT_EXPIRED,
    QUESTION_ANSWERED,
})

ALL_KNOWN_EVENTS: frozenset[str] = KNOWN_CLIENT_EVENTS | KNOWN_SERVER_EVENTS
