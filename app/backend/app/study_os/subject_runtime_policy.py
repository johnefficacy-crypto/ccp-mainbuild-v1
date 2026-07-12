"""Study OS — server-owned Subject Runtime Policy registry (GQR-1).

The subject surface historically hard-coded exactly two runtimes: English writing
and PYQ topic practice. ``subjects.py`` appended ``english_writing`` when writing
was available and ``topic_pyq`` when projected PYQ topics existed; ``subject_practice.py``
dispatched launches through an ``if mode ==`` ladder; ``planner.py`` stamped
``pyq_practice`` for a fixed set of task types. Nothing else was expressible, so GA
current-affairs and specialised Quant/Reasoning modes fit neither branch.

This module is the single **server-owned** source of truth for subject runtime
config — code-governed, not a table (mirroring ``planner._LAUNCH_STAMP_TASK_TYPES``).
It is deliberately import-light (no writing/pyq/mock imports) so it can be consulted
from ``subjects.py`` (hub descriptors), ``subject_practice.py`` (launch dispatch) and
``planner.py`` (launch stamping) without an import cycle. Handlers that need those
heavy modules stay where they are and register themselves against these mode keys.

GQR-1 ships **no behavioural change** for existing subjects: the two wired runtime
modes below (``english_writing`` / ``topic_pyq``) reproduce the prior hub output and
launch behaviour exactly. The declared per-family ``supported_modes`` carry the
contract vocabulary (docs/architecture/subject-practice-framework.md §2.2) as the seam
the GA / Quant / Reasoning verticals light up next.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# ── Runtime launch modes actually wired in v1 ──────────────────────────────
# These strings are part of the browser/runtime contract: the hub emits them as
# ``launch_mode`` and the launch endpoint dispatches on them. They MUST stay
# byte-stable — regression tests pin them.
MODE_ENGLISH_WRITING = "english_writing"
MODE_TOPIC_PYQ = "topic_pyq"

# Subject families (contract §2.2 vocabulary).
FAMILY_ENGLISH = "english"
FAMILY_QUANT = "quant"
FAMILY_REASONING = "reasoning"
FAMILY_GENERAL_AWARENESS = "general_awareness"

# Planner launch-type stamp (kept in sync with planner.LAUNCH_PYQ_PRACTICE; a
# local literal avoids a cross-module import cycle, same rationale as planner's).
LAUNCH_PYQ_PRACTICE = "pyq_practice"


@dataclass(frozen=True)
class SubjectRuntimePolicy:
    """Declared runtime policy for one subject family (contract §2.2).

    ``supported_modes`` is the ordered, hub-exposed mode vocabulary for the family.
    In v1 only the two wired adapters (see ``WIRED_RUNTIME_MODES``) are runnable; the
    remaining declared modes are the seam the GA/Quant/Reasoning PRs implement. The
    behavioural flags are consumed by the planner/attempt layers as those land — GA
    is always ``mastery_enabled=False`` / ``correction_enabled=False`` per the domain
    rule that current-affairs performance must never write ``user_topic_mastery``.
    """

    subject_family: str
    supported_modes: tuple[str, ...]
    attempt_kind: str
    mastery_enabled: bool
    correction_enabled: bool
    retry_policy: str  # none | ephemeral_ca | normal_srs
    # Server-side seams (contract §2.2). Populated by the owning vertical PR; a
    # ``None`` resolver means the family has no runnable inventory/planner path yet.
    inventory_resolver: Callable[..., Any] | None = None
    planner_resolver: Callable[..., Any] | None = None


# Initial policies — verbatim from contract §2.2. Ordered; the hub renders
# ``supported_modes`` in declaration order.
SUBJECT_RUNTIME_POLICIES: dict[str, SubjectRuntimePolicy] = {
    FAMILY_ENGLISH: SubjectRuntimePolicy(
        subject_family=FAMILY_ENGLISH,
        supported_modes=("objective_practice", "english_writing_session"),
        attempt_kind="learning_session",
        mastery_enabled=True,
        correction_enabled=True,
        retry_policy="normal_srs",
    ),
    FAMILY_QUANT: SubjectRuntimePolicy(
        subject_family=FAMILY_QUANT,
        supported_modes=("topic_practice", "timed_practice", "heuristic_drill", "calculation_gym"),
        attempt_kind="mock_attempt",
        mastery_enabled=True,
        correction_enabled=True,
        retry_policy="normal_srs",
    ),
    FAMILY_REASONING: SubjectRuntimePolicy(
        subject_family=FAMILY_REASONING,
        supported_modes=("topic_practice", "timed_practice", "reasoning_set"),
        attempt_kind="mock_attempt",
        mastery_enabled=True,
        correction_enabled=True,
        retry_policy="normal_srs",
    ),
    FAMILY_GENERAL_AWARENESS: SubjectRuntimePolicy(
        subject_family=FAMILY_GENERAL_AWARENESS,
        # GA v1 excludes permanent mastery/SRS; current-affairs retries are ephemeral.
        supported_modes=("weekly_current_affairs", "monthly_current_affairs"),
        attempt_kind="current_affairs_attempt",
        mastery_enabled=False,
        correction_enabled=False,
        retry_policy="ephemeral_ca",
    ),
}


# ── Wired runtime-mode adapters (v1) ───────────────────────────────────────
@dataclass(frozen=True)
class RuntimeModeAdapter:
    """A runtime mode that is actually runnable in v1.

    Couples the hub descriptor (what ``subjects.py`` emits) with the dispatch key
    the launch endpoint routes on. Replaces the two inline ``if`` branches in
    ``subjects._subject_practice`` and the ``if mode ==`` ladder in
    ``subject_practice.start_subject_practice`` with one registry both consult.
    """

    mode: str
    label: str
    subject_family: str
    # Extra static descriptor fields merged into the hub mode entry (e.g. the
    # companion client_route modes rendered alongside a server_launch mode).
    companion_modes: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def hub_mode(self, *, target_topic_id: str | None = None) -> dict[str, Any]:
        """The primary ``server_launch`` hub descriptor for this mode."""
        return {
            "type": self.mode,
            "label": self.label,
            "target_topic_id": target_topic_id,
            "route_type": "server_launch",
            "launch_mode": self.mode,
        }


WIRED_RUNTIME_MODES: dict[str, RuntimeModeAdapter] = {
    MODE_ENGLISH_WRITING: RuntimeModeAdapter(
        mode=MODE_ENGLISH_WRITING,
        label="Sentence practice",
        subject_family=FAMILY_ENGLISH,
        companion_modes=(
            {
                "type": "error_lab", "label": "Error Lab", "target_topic_id": None,
                "route_type": "client_route", "route": "/app/study/error-lab",
            },
        ),
    ),
    MODE_TOPIC_PYQ: RuntimeModeAdapter(
        mode=MODE_TOPIC_PYQ,
        label="Topic PYQ practice",
        subject_family=FAMILY_QUANT,  # generic PYQ topic runtime; not family-gated in v1
        companion_modes=(
            {
                "type": "mock_section", "label": "Mock section practice",
                "target_topic_id": None, "route_type": "client_route",
                "route": "/app/study/mocks",
            },
        ),
    ),
}


def is_wired_mode(mode: str) -> bool:
    """True iff ``mode`` has a runnable v1 launch adapter."""
    return mode in WIRED_RUNTIME_MODES


# ── Planner launch resolution (generalises _LAUNCH_STAMP_TASK_TYPES) ────────
# task_type values whose plan tasks resolve to a PYQ topic-practice launch. Kept
# as the single source the planner consults; adding a subject runtime here is a
# registry edit, not an if-ladder edit.
_PLANNER_PYQ_TASK_TYPES: frozenset[str] = frozenset({"retrieval_practice", "revision"})


def resolve_planner_launch(
    task_type: str, *, topic_id: str | None, exam_id: str | None
) -> dict[str, Any] | None:
    """Resolve a runnable launch stamp for a planner task, or ``None``.

    Generalises the inline ``_LAUNCH_STAMP_TASK_TYPES`` stamping in ``planner.py``.
    v1 behaviour is preserved exactly: ``retrieval_practice`` / ``revision`` tasks on
    a real topic+exam resolve to a typed PYQ topic-practice launch; every other
    task_type (or a task missing topic/exam) resolves to ``None`` (left unstamped).
    Returns the launch column payload the planner merges onto the task.
    """
    if task_type in _PLANNER_PYQ_TASK_TYPES and topic_id and exam_id:
        return {
            "launch_type": LAUNCH_PYQ_PRACTICE,
            "launch_entity_id": topic_id,
            "launch_context": {"mode": "topic", "target_id": topic_id, "exam_id": exam_id},
        }
    return None
