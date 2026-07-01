"""EWP-2B mastery evidence derivation (architecture §4.12, §8.2, §10.1).

Pure module: no DB access, no network, no heavy imports. It is the single
backend owner of the writing **evidence-key layout** (§4.12b) and of the
unit-level tier decision that turns one evaluation into at most one mastery
evidence row.

The same ``evidence_key`` is used by both ``user_topic_mastery_evidence``
(§4.12) and ``writing_mastery_shadow`` (§10.1a) for a given logical evidence
unit. Because ``evidence_op`` and ``review_event_id`` are part of the key, an
``assert`` and its later ``retract``/``replace`` produce distinct keys and are
not rejected by ``unique (evidence_key)``. The derived ``evidence_key`` is also
reused as the outbox ``idempotency_key`` so the whole assert chain is
idempotent end to end.

``EVIDENCE_KEY_LAYOUT_VERSION = "wev-1"`` records the current field order and
coalesce sentinels. It is intentionally NOT part of the hashed payload (the
payload must match the SQL definition in §4.12b byte-for-byte); it exists only
so that any future change to the layout is auditable in code review.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

# Layout audit tag — docstring/reference only, NEVER hashed (see module docstring).
EVIDENCE_KEY_LAYOUT_VERSION = "wev-1"

#: Ordered evidence tiers. Lexical ordering is NOT meaningful — never compare
#: tiers with ``<``/``>`` on the string; use the SQL ``tier_rank`` helper (§4.12a).
EVIDENCE_TIERS = ("recognition", "correction", "production", "retention")

#: Source types for writing evidence (§4.12a). These are a subset of the
#: ``source_type`` CHECK enum shared by ``user_topic_mastery_evidence`` (§4.12)
#: and ``writing_mastery_shadow`` (§10.1a):
#: ('objective_mock','descriptive_mock','sentence_drill','paragraph_drill',
#:  'human_review','mentor_review').
SOURCE_TYPE_SENTENCE = "sentence_drill"
SOURCE_TYPE_PARAGRAPH = "paragraph_drill"
#: Fallback source type only (unknown/legacy exercise types).
SOURCE_TYPE_WRITING = "descriptive_mock"

#: ``writing_prompts.exercise_type`` values that map to sentence-level drills.
_SENTENCE_EXERCISES = frozenset({
    "sentence_construction",
    "sentence_correction",
    "sentence_rewrite",
    "sentence_reconstruction",
    "vocabulary_in_context",
})
#: ``writing_prompts.exercise_type`` values that map to paragraph-level drills.
_PARAGRAPH_EXERCISES = frozenset({
    "paragraph_writing",
    "summary_writing",
    "precis_practice",
    "essay_practice",
    "letter_practice",
})


def source_type_for_exercise(exercise_type: str) -> str:
    """Map a ``writing_prompts.exercise_type`` to an evidence ``source_type``.

    Sentence-level exercises → ``sentence_drill``; paragraph-level exercises →
    ``paragraph_drill``; anything else → ``descriptive_mock`` (fallback only).
    """
    if exercise_type in _SENTENCE_EXERCISES:
        return SOURCE_TYPE_SENTENCE
    if exercise_type in _PARAGRAPH_EXERCISES:
        return SOURCE_TYPE_PARAGRAPH
    return SOURCE_TYPE_WRITING

# Terminal-success statuses under which a unit yields production/correction
# evidence. Any other status yields no evidence yet (deriver returns None).
_TERMINAL_SUCCESS = frozenset({"completed", "terminal_partial"})


def compute_evidence_key(
    *,
    evidence_op: str,
    user_id: str,
    evaluation_id: str,
    issue_projection_id: str | None,
    microtopic_id: str | None,
    evidence_tier: str,
    source_type: str,
    review_event_id: str | None,
) -> str:
    """Return the lowercase 64-char SHA-256 hex ``evidence_key`` (§4.12b).

    This is the single owner of the writing evidence-key layout. Both
    ``user_topic_mastery_evidence`` and ``writing_mastery_shadow`` key their
    rows with the value returned here for a given logical evidence unit.

    The hashed payload is the UTF-8 bytes of these fields joined by a single
    NUL byte (``\\x00``) in exactly this order (matching the SQL in §4.12b):

      1. ``evidence_op``
      2. ``user_id``
      3. ``evaluation_id``
      4. ``coalesce(issue_projection_id, 'no_projection')``
      5. ``coalesce(microtopic_id, 'no_microtopic')``
      6. ``evidence_tier``
      7. ``source_type``
      8. ``coalesce(review_event_id, 'no_review')``

    See ``EVIDENCE_KEY_LAYOUT_VERSION`` for the audit tag of this layout.
    """
    fields = [
        evidence_op,
        user_id,
        evaluation_id,
        issue_projection_id if issue_projection_id is not None else "no_projection",
        microtopic_id if microtopic_id is not None else "no_microtopic",
        evidence_tier,
        source_type,
        review_event_id if review_event_id is not None else "no_review",
    ]
    return hashlib.sha256(b"\x00".join(f.encode("utf-8") for f in fields)).hexdigest()


@dataclass
class EvidenceRow:
    """One derived mastery evidence unit.

    Fields are the union of columns the mastery worker inserts into
    ``user_topic_mastery_evidence`` (§4.12) and ``writing_mastery_shadow``
    (§10.1a). ``observed_at`` / ``processed_at`` are DB-defaulted and therefore
    omitted from the emitted dicts.
    """

    user_id: str
    topic_id: str
    microtopic_id: Optional[str]
    exam_id: Optional[str]
    source_type: str
    source_entity_id: str
    evaluation_id: str
    issue_projection_id: Optional[str]
    evidence_tier: str
    score: Optional[float]
    confidence: Optional[float]
    evidence_key: str
    evidence_op: str = "assert"

    def to_evidence_dict(self) -> dict:
        """Column dict for ``user_topic_mastery_evidence`` (§4.12).

        Includes ``evidence_op``. Omits ``observed_at`` (DB default).
        """
        return {
            "user_id": self.user_id,
            "topic_id": self.topic_id,
            "microtopic_id": self.microtopic_id,
            "exam_id": self.exam_id,
            "source_type": self.source_type,
            "source_entity_id": self.source_entity_id,
            "evaluation_id": self.evaluation_id,
            "issue_projection_id": self.issue_projection_id,
            "evidence_tier": self.evidence_tier,
            "score": self.score,
            "confidence": self.confidence,
            "evidence_key": self.evidence_key,
            "evidence_op": self.evidence_op,
        }

    def to_shadow_dict(self) -> dict:
        """Column dict for ``writing_mastery_shadow`` (§10.1a).

        Includes ``delta_json`` (default ``{}``). Omits ``processed_at``
        (DB default). The shadow table has no ``evidence_op`` column; the op is
        already folded into ``evidence_key``.
        """
        return {
            "user_id": self.user_id,
            "topic_id": self.topic_id,
            "microtopic_id": self.microtopic_id,
            "exam_id": self.exam_id,
            "source_type": self.source_type,
            "source_entity_id": self.source_entity_id,
            "evaluation_id": self.evaluation_id,
            "issue_projection_id": self.issue_projection_id,
            "evidence_tier": self.evidence_tier,
            "score": self.score,
            "confidence": self.confidence,
            "evidence_key": self.evidence_key,
            "delta_json": {},
        }


def derive_unit_evidence(
    *,
    user_id: str,
    evaluation_id: str,
    topic_id: str,
    microtopic_id: str | None,
    exam_id: str | None,
    source_entity_id: str,
    exercise_type: str,
    has_unresolved_must_fix: bool,
    resolved_issue_count: int,
    overall_status: str,
) -> EvidenceRow | None:
    """Derive ONE unit-level evidence row for an evaluation (pure decision).

    This emits at most one unit-level production/correction evidence row per
    evaluation. Per-issue microtopic evidence (one row per resolved issue
    projection) is intentionally deferred — hence ``issue_projection_id=None``
    and unit-level ``microtopic_id`` here.

    The ``source_type`` is derived from ``exercise_type`` via
    ``source_type_for_exercise`` (sentence_drill / paragraph_drill / fallback
    descriptive_mock). Because ``source_type`` is a hashed field, the derived
    ``evidence_key`` folds in the exercise-derived source type (§4.12b).

    Tier logic:
      * ``overall_status`` not in the terminal-success set
        (``"completed"``/``"terminal_partial"``) → return ``None`` (non-terminal;
        no evidence yet, the unit may still change).
      * else if ``has_unresolved_must_fix`` → return ``None``. A blocking answer
        earns NO positive constructed-response evidence. ``"recognition"`` is
        objective-choice evidence in the locked model and is never emitted by
        this writing path.
      * else if ``resolved_issue_count > 0`` → tier ``"correction"``.
      * else → tier ``"production"``.

    The row is an ``assert`` (``evidence_op="assert"``, ``review_event_id=None``,
    ``issue_projection_id=None``). ``score``/``confidence`` are ``None`` for now.
    The returned row's ``evidence_key`` is used by the caller/RPC as the outbox
    idempotency key.
    """
    if overall_status not in _TERMINAL_SUCCESS:
        return None

    if has_unresolved_must_fix:
        return None

    if resolved_issue_count > 0:
        evidence_tier = "correction"
    else:
        evidence_tier = "production"

    source_type = source_type_for_exercise(exercise_type)

    evidence_key = compute_evidence_key(
        evidence_op="assert",
        user_id=user_id,
        evaluation_id=evaluation_id,
        issue_projection_id=None,
        microtopic_id=microtopic_id,
        evidence_tier=evidence_tier,
        source_type=source_type,
        review_event_id=None,
    )

    return EvidenceRow(
        user_id=user_id,
        topic_id=topic_id,
        microtopic_id=microtopic_id,
        exam_id=exam_id,
        source_type=source_type,
        source_entity_id=source_entity_id,
        evaluation_id=evaluation_id,
        issue_projection_id=None,
        evidence_tier=evidence_tier,
        score=None,
        confidence=None,
        evidence_key=evidence_key,
        evidence_op="assert",
    )


def derive_issue_evidence(
    *,
    user_id: str,
    evaluation_id: str,
    topic_id: str,
    exam_id: str | None,
    source_entity_id: str,
    exercise_type: str,
    issue_projection_id: str,
    issue_microtopic_id: str | None,
    evidence_tier: str,
) -> EvidenceRow:
    """Derive ONE projection-linked evidence row for a single issue (§4.12/§10.1).

    Unlike the unit-level row, this carries the ``issue_projection_id`` (and the
    issue's OWN microtopic), so the row can participate in the schema correction
    chain (§4.12c): a later ``retract``/``replace``/re-assert supersedes it.

    ``evidence_tier`` is supplied by the drain claim. Per §4.12a a POSITIVE tier
    must be DEMONSTRATED: the drain emits a projection-linked row ONLY for a
    lineage the aspirant actually RESOLVED this evaluation, always with tier
    ``correction`` ("aspirant corrected a supplied incorrect sentence"). An
    active/unresolved error earns NO positive evidence and therefore produces no
    projection-linked row here (``recognition`` is objective-choice evidence in
    the locked model and is never emitted by the writing path). The row is an
    ``assert`` (``review_event_id=None``); the derived key folds in
    ``issue_projection_id`` and the issue microtopic so each issue produces a
    distinct evidence_key (§4.12b).
    """
    source_type = source_type_for_exercise(exercise_type)
    evidence_key = compute_evidence_key(
        evidence_op="assert",
        user_id=user_id,
        evaluation_id=evaluation_id,
        issue_projection_id=issue_projection_id,
        microtopic_id=issue_microtopic_id,
        evidence_tier=evidence_tier,
        source_type=source_type,
        review_event_id=None,
    )
    return EvidenceRow(
        user_id=user_id,
        topic_id=topic_id,
        microtopic_id=issue_microtopic_id,
        exam_id=exam_id,
        source_type=source_type,
        source_entity_id=source_entity_id,
        evaluation_id=evaluation_id,
        issue_projection_id=issue_projection_id,
        evidence_tier=evidence_tier,
        score=None,
        confidence=None,
        evidence_key=evidence_key,
        evidence_op="assert",
    )


def derive_review_correction_evidence(
    *,
    evidence_op: str,
    user_id: str,
    evaluation_id: str,
    topic_id: str,
    microtopic_id: str | None,
    exam_id: str | None,
    source_type: str,
    source_entity_id: str,
    evidence_tier: str,
    issue_projection_id: str,
    review_event_id: str,
    supersedes_evidence_key: str,
) -> EvidenceRow:
    """Derive the correction evidence row for a review decision (§4.12c).

    ``evidence_op`` is fixed by the decision (``retract``/``replace``/re-assert
    ``assert``); the identity fields (tier/microtopic/topic/source) are copied
    from the superseded tail. Because ``evidence_op`` and ``review_event_id`` are
    part of the §4.12b key, the correction row keys distinctly from the original
    assertion and from other corrections of the same issue.
    """
    evidence_key = compute_evidence_key(
        evidence_op=evidence_op,
        user_id=user_id,
        evaluation_id=evaluation_id,
        issue_projection_id=issue_projection_id,
        microtopic_id=microtopic_id,
        evidence_tier=evidence_tier,
        source_type=source_type,
        review_event_id=review_event_id,
    )
    return EvidenceRow(
        user_id=user_id,
        topic_id=topic_id,
        microtopic_id=microtopic_id,
        exam_id=exam_id,
        source_type=source_type,
        source_entity_id=source_entity_id,
        evaluation_id=evaluation_id,
        issue_projection_id=issue_projection_id,
        evidence_tier=evidence_tier,
        score=None,
        confidence=None,
        evidence_key=evidence_key,
        evidence_op=evidence_op,
    )
