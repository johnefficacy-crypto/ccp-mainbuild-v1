"""Study OS — server-owned Subject Runtime Policy registry (GQR-1).

The subject surface historically hard-coded exactly two runtimes: English writing
and PYQ topic practice. ``subjects.py`` appended ``english_writing`` when writing
was available and ``topic_pyq`` when projected PYQ topics existed; ``subject_practice.py``
dispatched launches through an ``if mode ==`` ladder; ``planner.py`` stamped
``pyq_practice`` for a fixed set of task types regardless of subject. Nothing else
was expressible, so GA current-affairs and specialised Quant/Reasoning modes fit
neither branch, and — critically — a General-Awareness retrieval/revision task would
be stamped as a PYQ launch.

This module is the single **server-owned** authority for subject runtime config —
code-governed, not a table (mirroring ``planner._LAUNCH_STAMP_TASK_TYPES``). It is
deliberately import-light (no writing/pyq/mock imports) so it can be consumed from
``subjects.py`` (hub descriptors, via ``policy.inventory_resolver``), ``planner.py``
(launch stamping, via ``policy.planner_resolver``) and ``subject_practice.py`` (launch
dispatch, via ``is_wired_mode``) without an import cycle.

Family resolution is off **canonical governed metadata** — ``subject_group`` first,
then ``slug`` — never the display name. The resolvers ARE the runtime authority:
``_subject_practice`` iterates ``policy.inventory_resolver(ctx)`` with no English/PYQ
branch, and ``planner`` delegates to ``policy.planner_resolver``. Adding a mode to a
vertical (GA/Quant/Reasoning) is a registry edit, not an edit to ``subjects.py`` or
``planner.py``.

Compatibility: English and PYQ output/behaviour for the seeded families
(numerical/verbal/reasoning + ungoverned ``gs``/unknown) is preserved byte-for-byte;
only ``general_awareness`` — which has no seeded subject yet (SSC GA seed is a tracked
prerequisite) — is fenced off from the generic PYQ path, per the domain rule that GA
current-affairs must never behave as enduring subject mastery/PYQ.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

# ── Runtime launch modes actually wired in v1 ──────────────────────────────
# These strings are part of the browser/runtime contract: the hub emits them as
# ``launch_mode`` and the launch endpoint dispatches on them. They MUST stay
# byte-stable — regression tests pin them.
MODE_ENGLISH_WRITING = "english_writing"
MODE_TOPIC_PYQ = "topic_pyq"
MODE_TIMED_PRACTICE = "timed_practice"
MODE_WEEKLY_CURRENT_AFFAIRS = "weekly_current_affairs"

# Reserved identifier for the bundle-driven GA current-affairs "subject". GA is NOT a
# topic-coverage subject — current-affairs is bundle-driven, not topic-driven — so it has
# no real ``subjects`` row and never appears via locked ``exam_topic_coverage``. This
# stable sentinel (a valid UUID for the ``/subjects/{id}/practice/start`` path param) lets
# the hub emit a GA card and the launch gate resolve the GA family WITHOUT a fake locked
# topic. Reachability is gated on a servable weekly bundle, not on coverage.
CURRENT_AFFAIRS_VIRTUAL_SUBJECT_ID = "00000000-0000-0000-0000-0000000000ca"

# Subject families (contract §2.2 vocabulary).
FAMILY_ENGLISH = "english"
FAMILY_QUANT = "quant"
FAMILY_REASONING = "reasoning"
FAMILY_GENERAL_AWARENESS = "general_awareness"

# Planner launch-type stamp (kept in sync with planner.LAUNCH_PYQ_PRACTICE; a
# local literal avoids a cross-module import cycle, same rationale as planner's).
LAUNCH_PYQ_PRACTICE = "pyq_practice"

# task_type values whose plan tasks resolve to a PYQ topic-practice launch.
_PLANNER_PYQ_TASK_TYPES: frozenset[str] = frozenset({"retrieval_practice", "revision"})


# ── Family resolution from canonical governed metadata ─────────────────────
# Governed subject-group -> family (primary key; stable across exams that share the
# SSC/RRB taxonomy). ``gs`` (UPSC General Studies) is intentionally NOT mapped to
# general_awareness — those are PYQ-backed subjects and must keep the generic PYQ
# runtime; only the dedicated SSC General-Awareness group maps to the GA family.
_GROUP_FAMILY: dict[str, str] = {
    "numerical": FAMILY_QUANT,
    "quantitative": FAMILY_QUANT,
    "verbal": FAMILY_ENGLISH,
    "english": FAMILY_ENGLISH,
    "reasoning": FAMILY_REASONING,
    "general-awareness": FAMILY_GENERAL_AWARENESS,
    "general_awareness": FAMILY_GENERAL_AWARENESS,
    "current-affairs": FAMILY_GENERAL_AWARENESS,
}

# Canonical slug -> family (secondary key, used when subject_group is absent/unknown).
_SLUG_FAMILY: dict[str, str] = {
    "quantitative-aptitude": FAMILY_QUANT,
    "quant": FAMILY_QUANT,
    "maths": FAMILY_QUANT,
    "english-language": FAMILY_ENGLISH,
    "english": FAMILY_ENGLISH,
    "general-intelligence-reasoning": FAMILY_REASONING,
    "reasoning": FAMILY_REASONING,
    "general-awareness": FAMILY_GENERAL_AWARENESS,
    "general-awareness-current-affairs": FAMILY_GENERAL_AWARENESS,
    "current-affairs": FAMILY_GENERAL_AWARENESS,
}


def family_for_subject(*, slug: str | None = None, subject_group: str | None = None) -> str | None:
    """Resolve a subject family from canonical governed metadata.

    ``subject_group`` (the governed taxonomy column) is authoritative; ``slug`` is a
    fallback. Returns ``None`` for an ungoverned/unknown subject (e.g. UPSC ``gs``),
    which the caller maps to the generic PYQ-capable policy — never to GA.
    """
    if subject_group:
        fam = _GROUP_FAMILY.get(subject_group.strip().lower())
        if fam:
            return fam
    if slug:
        fam = _SLUG_FAMILY.get(slug.strip().lower())
        if fam:
            return fam
    return None


# ── Inventory context + wired runtime-mode adapters (v1) ───────────────────
@dataclass(frozen=True)
class InventoryContext:
    """Server-resolved eligibility signals for one subject card.

    Passed to a policy's ``inventory_resolver``. Topic ids stay in their original
    type (never str-coerced) so mastery/error lookups match ``subjects.py`` exactly;
    only the emitted ``target_topic_id`` is stringified.
    """

    eng_available: bool = False
    available_topic_ids: tuple[Any, ...] = ()
    mastery: Mapping[Any, float] = field(default_factory=dict)
    error_topics: frozenset[Any] = frozenset()


@dataclass(frozen=True)
class RuntimeModeAdapter:
    """A runtime mode that is actually runnable in v1.

    Couples the hub descriptor (what ``subjects.py`` emits) with the dispatch key the
    launch endpoint routes on. ``topic_pyq`` is deliberately family-agnostic (offered
    to every non-GA family via each policy's wired-mode list) — the adapter carries no
    single owning family, so activating family gating cannot silently drop PYQ for
    English/Reasoning.
    """

    mode: str
    label: str
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

    def hub_entries(self, *, target_topic_id: str | None = None) -> list[dict[str, Any]]:
        """Primary descriptor + its client-route companions (fresh dicts)."""
        return [self.hub_mode(target_topic_id=target_topic_id),
                *[dict(m) for m in self.companion_modes]]


WIRED_RUNTIME_MODES: dict[str, RuntimeModeAdapter] = {
    MODE_ENGLISH_WRITING: RuntimeModeAdapter(
        mode=MODE_ENGLISH_WRITING,
        label="Sentence practice",
        companion_modes=(
            {
                "type": "error_lab", "label": "Improvement Lab", "target_topic_id": None,
                "route_type": "client_route", "route": "/app/study/improvement-lab",
            },
        ),
    ),
    MODE_TOPIC_PYQ: RuntimeModeAdapter(
        mode=MODE_TOPIC_PYQ,
        label="Topic PYQ practice",
        companion_modes=(
            {
                "type": "mock_section", "label": "Mock section practice",
                "target_topic_id": None, "route_type": "client_route",
                "route": "/app/study/mocks",
            },
        ),
    ),
    # GQR-R10: same server-owned topic-PYQ assembly as topic_pyq, but the launch
    # freezes a server-owned countdown (duration_sec) onto the attempt. Reuses the
    # existing objective attempt shell + timer — no new attempt engine, no migration.
    MODE_TIMED_PRACTICE: RuntimeModeAdapter(
        mode=MODE_TIMED_PRACTICE,
        label="Timed practice",
    ),
    # GQR-G5: GA current-affairs. Unlike the topic-PYQ modes this is bundle-driven,
    # not topic-driven — the learner never picks a topic, and there is no
    # ``target_topic_id``. The server resolves the eligible weekly bundle and freezes
    # its still-eligible questions at launch (no_bundle / empty_bundle / bundle_degraded
    # are handled there, not gated in the hub descriptor).
    MODE_WEEKLY_CURRENT_AFFAIRS: RuntimeModeAdapter(
        mode=MODE_WEEKLY_CURRENT_AFFAIRS,
        label="Weekly current affairs",
    ),
}


def is_wired_mode(mode: str) -> bool:
    """True iff ``mode`` has a runnable v1 launch adapter."""
    return mode in WIRED_RUNTIME_MODES


def _weakest_available_topic(ctx: InventoryContext) -> Any:
    """Weakest projected topic first: lowest mastery, then error-flagged, stable
    tiebreak. Identical ordering to the prior ``subjects._subject_practice``."""
    return sorted(
        ctx.available_topic_ids,
        key=lambda t: (
            ctx.mastery.get(t) if ctx.mastery.get(t) is not None else 999.0,
            0 if t in ctx.error_topics else 1,
            str(t),
        ),
    )[0]


def _emit_english_writing(ctx: InventoryContext) -> list[dict[str, Any]]:
    if not ctx.eng_available:
        return []
    return WIRED_RUNTIME_MODES[MODE_ENGLISH_WRITING].hub_entries()


def _emit_topic_pyq(ctx: InventoryContext) -> list[dict[str, Any]]:
    if not ctx.available_topic_ids:
        return []
    chosen = _weakest_available_topic(ctx)
    return WIRED_RUNTIME_MODES[MODE_TOPIC_PYQ].hub_entries(target_topic_id=str(chosen))


def _emit_timed_practice(ctx: InventoryContext) -> list[dict[str, Any]]:
    # Same eligibility + target as topic_pyq (a projected topic pool); differs only by
    # the server-owned timer applied at launch.
    if not ctx.available_topic_ids:
        return []
    chosen = _weakest_available_topic(ctx)
    return WIRED_RUNTIME_MODES[MODE_TIMED_PRACTICE].hub_entries(target_topic_id=str(chosen))


def _emit_weekly_current_affairs(ctx: InventoryContext) -> list[dict[str, Any]]:
    # Bundle-driven, not topic-driven: current-affairs eligibility is a published
    # weekly bundle resolved at launch, never a projected PYQ topic pool. The mode is
    # always offered for a GA subject; the launch handler owns the no_bundle /
    # empty_bundle / bundle_degraded outcomes (a decaying answer must never be gated
    # by stale hub inventory signals — GA is calendar-driven).
    return WIRED_RUNTIME_MODES[MODE_WEEKLY_CURRENT_AFFAIRS].hub_entries()


# Per wired-mode signal resolver. Registering a runtime = adding an entry here + to a
# policy's ``wired_runtime_modes``; no branch is added to ``subjects.py``.
_MODE_EMITTERS: dict[str, Callable[[InventoryContext], list[dict[str, Any]]]] = {
    MODE_ENGLISH_WRITING: _emit_english_writing,
    MODE_TOPIC_PYQ: _emit_topic_pyq,
    MODE_TIMED_PRACTICE: _emit_timed_practice,
    MODE_WEEKLY_CURRENT_AFFAIRS: _emit_weekly_current_affairs,
}


def _make_inventory_resolver(
    wired_modes: tuple[str, ...]
) -> Callable[[InventoryContext], list[dict[str, Any]]]:
    """Build an inventory resolver that emits, in order, the eligible hub entries for
    this family's wired modes given the signal context."""

    def resolver(ctx: InventoryContext) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for mode in wired_modes:
            entries.extend(_MODE_EMITTERS[mode](ctx))
        return entries

    return resolver


# ── Planner launch resolvers ───────────────────────────────────────────────
def _pyq_planner_resolver(
    task_type: str, *, topic_id: Any | None, exam_id: Any | None
) -> dict[str, Any] | None:
    """PYQ topic-practice stamp for retrieval/revision tasks on a real topic+exam.
    Byte-identical to the prior inline planner stamp."""
    if task_type in _PLANNER_PYQ_TASK_TYPES and topic_id and exam_id:
        return {
            "launch_type": LAUNCH_PYQ_PRACTICE,
            "launch_entity_id": topic_id,
            "launch_context": {"mode": "topic", "target_id": topic_id, "exam_id": exam_id},
        }
    return None


def _no_launch_planner_resolver(
    task_type: str, *, topic_id: Any | None, exam_id: Any | None
) -> dict[str, Any] | None:
    """GA is calendar-driven: a General-Awareness retrieval/revision task must NEVER
    be stamped as a PYQ launch (domain rule — GA is current-affairs only)."""
    return None


# ── Policy dataclass + registry ────────────────────────────────────────────
@dataclass(frozen=True)
class SubjectRuntimePolicy:
    """Runtime authority for one subject family (contract §2.2).

    ``supported_modes`` is the ordered, hub-exposed product vocabulary. ``wired_runtime_modes``
    are the v1 runnable adapters (subset actually launchable now). ``inventory_resolver``
    and ``planner_resolver`` are the live callables consumed by ``subjects.py`` and
    ``planner.py`` respectively. The behavioural flags (``mastery_enabled`` etc.) are
    read by the attempt/mastery layers as the vertical PRs land — GA is always
    ``mastery_enabled=False`` / ``correction_enabled=False`` per the domain rule that
    current-affairs performance must never write ``user_topic_mastery``.
    """

    subject_family: str
    supported_modes: tuple[str, ...]
    wired_runtime_modes: tuple[str, ...]
    attempt_kind: str
    mastery_enabled: bool
    correction_enabled: bool
    retry_policy: str  # none | ephemeral_ca | normal_srs
    inventory_resolver: Callable[[InventoryContext], list[dict[str, Any]]]
    planner_resolver: Callable[..., dict[str, Any] | None]


def _policy(
    *, family: str, supported_modes: tuple[str, ...], wired_runtime_modes: tuple[str, ...],
    attempt_kind: str, mastery_enabled: bool, correction_enabled: bool, retry_policy: str,
    planner_resolver: Callable[..., dict[str, Any] | None],
) -> SubjectRuntimePolicy:
    return SubjectRuntimePolicy(
        subject_family=family,
        supported_modes=supported_modes,
        wired_runtime_modes=wired_runtime_modes,
        attempt_kind=attempt_kind,
        mastery_enabled=mastery_enabled,
        correction_enabled=correction_enabled,
        retry_policy=retry_policy,
        inventory_resolver=_make_inventory_resolver(wired_runtime_modes),
        planner_resolver=planner_resolver,
    )


SUBJECT_RUNTIME_POLICIES: dict[str, SubjectRuntimePolicy] = {
    FAMILY_ENGLISH: _policy(
        family=FAMILY_ENGLISH,
        supported_modes=("objective_practice", "english_writing_session"),
        wired_runtime_modes=(MODE_ENGLISH_WRITING, MODE_TOPIC_PYQ),
        attempt_kind="learning_session",
        mastery_enabled=True, correction_enabled=True, retry_policy="normal_srs",
        planner_resolver=_pyq_planner_resolver,
    ),
    FAMILY_QUANT: _policy(
        family=FAMILY_QUANT,
        supported_modes=("topic_practice", "timed_practice", "heuristic_drill", "calculation_gym"),
        wired_runtime_modes=(MODE_TOPIC_PYQ,),
        attempt_kind="mock_attempt",
        mastery_enabled=True, correction_enabled=True, retry_policy="normal_srs",
        planner_resolver=_pyq_planner_resolver,
    ),
    FAMILY_REASONING: _policy(
        family=FAMILY_REASONING,
        supported_modes=("topic_practice", "timed_practice", "reasoning_set"),
        # v1 wired: topic PYQ (topic_practice) + timed_practice over the objective
        # runtime. reasoning_set (shared text/table stimulus sets) is the deferred
        # slice — it needs a stimulus-grouped selector, tracked as GQR-R10 set-runtime.
        wired_runtime_modes=(MODE_TOPIC_PYQ, MODE_TIMED_PRACTICE),
        attempt_kind="mock_attempt",
        mastery_enabled=True, correction_enabled=True, retry_policy="normal_srs",
        planner_resolver=_pyq_planner_resolver,
    ),
    FAMILY_GENERAL_AWARENESS: _policy(
        family=FAMILY_GENERAL_AWARENESS,
        # GA v1 excludes permanent mastery/SRS; current-affairs retries are ephemeral.
        # weekly_current_affairs is wired (GQR-G5 learner runtime); monthly stays a
        # declared-but-unwired product mode. No PYQ stamp ever.
        supported_modes=("weekly_current_affairs", "monthly_current_affairs"),
        wired_runtime_modes=(MODE_WEEKLY_CURRENT_AFFAIRS,),
        attempt_kind="current_affairs_attempt",
        mastery_enabled=False, correction_enabled=False, retry_policy="ephemeral_ca",
        planner_resolver=_no_launch_planner_resolver,
    ),
}

# Fallback for an ungoverned/unknown subject (e.g. UPSC ``gs``): the generic
# PYQ-capable runtime, preserving prior behaviour. NOT registered as a family — it is
# the default when ``family_for_subject`` returns None.
_GENERIC_POLICY = _policy(
    family="generic",
    supported_modes=("objective_practice",),
    wired_runtime_modes=(MODE_ENGLISH_WRITING, MODE_TOPIC_PYQ),
    attempt_kind="mock_attempt",
    mastery_enabled=True, correction_enabled=True, retry_policy="normal_srs",
    planner_resolver=_pyq_planner_resolver,
)


def policy_for_family(family: str | None) -> SubjectRuntimePolicy:
    """Resolve the runtime policy for a family, falling back to the generic
    PYQ-capable policy for an ungoverned/unknown subject."""
    if family is None:
        return _GENERIC_POLICY
    return SUBJECT_RUNTIME_POLICIES.get(family, _GENERIC_POLICY)


def resolve_subject_modes(
    *, slug: str | None, subject_group: str | None, ctx: InventoryContext
) -> list[dict[str, Any]]:
    """Hub practice modes for a subject: resolve family from canonical metadata, then
    let that policy's inventory resolver emit the eligible runtime modes. The single
    entry point ``subjects._subject_practice`` calls — no per-mode branching there."""
    family = family_for_subject(slug=slug, subject_group=subject_group)
    return policy_for_family(family).inventory_resolver(ctx)


def resolve_planner_launch(
    task_type: str, *, subject_slug: str | None = None, subject_group: str | None = None,
    topic_id: Any | None, exam_id: Any | None,
) -> dict[str, Any] | None:
    """Resolve a runnable launch stamp for a planner task, or ``None``.

    Delegates to the family policy's ``planner_resolver`` — so a General-Awareness task
    can never be stamped ``pyq_practice`` — while preserving byte-stable PYQ output for
    existing (numerical/verbal/reasoning + ungoverned) subjects.
    """
    family = family_for_subject(slug=subject_slug, subject_group=subject_group)
    resolver = policy_for_family(family).planner_resolver
    return resolver(task_type, topic_id=topic_id, exam_id=exam_id)
