"""Which authored ``mock_question_bank`` rows an exam's learners may be served (REG-CORPUS-02/04).

An authored row (``source_kind='authored'``, no ``pyq_question_id``) is written
once and serves every exam whose syllabus covers its topic. It therefore keeps
``exam_id`` NULL, and exam eligibility comes from the topic, not the row:

    row eligible for exam E  ⇔  row.source_kind = 'authored'
                               AND row.pyq_question_id IS NULL
                               AND row.exam_id IS NULL
                               AND topic(row) is eligible for E

    topic T eligible for E   ⇔  T.metadata HAS 'exams':  key(E) ∈ T.metadata.exams     (keyed)
                                T.metadata has no 'exams': T.subject ∈ BODY_AGNOSTIC_SUBJECTS
                                                           AND E's phase sections include
                                                           T.subject                      (body-agnostic)

``topic(row)`` is the row's PRIMARY topic — the single level id the row is
practised at (``microtopic_id`` when set, else ``topic_id``; see
``pyq_practice._row_level_id``). ``key(E)`` comes from :data:`EXAM_TOPIC_KEYS`,
the ONE place an exam slug is mapped to a topic-exam key. A keyed topic is
never widened by the body-agnostic rule: it serves only the exams it names.
An exam with no key and no body-agnostic section gets NO authored rows — never
all of them — and its pool read is not even issued.

Body-agnostic subjects (REG-CORPUS-04) are the shared Quant / Reasoning /
English / static GK trees: their topics carry no ``metadata.exams`` key by
design (migration 305) because every banking, SSC and regulator exam sits the
same syllabus. Which of them an exam examines comes from two sources:

* its own ``exam_phase_sections`` — used everywhere (topic practice, readiness,
  generated mocks, diagnostics);
* :data:`EXAM_AGNOSTIC_SUBJECTS` (REG-CORPUS-05) — an explicit per-exam list,
  UNIONed in for TOPIC PRACTICE ONLY (``include_configured_subjects``). Most
  live exams have no sections for the shared subjects yet (operator check
  2026-09-26: only SSC CGL and RBI Grade B do), so without it SEBI, IFSCA,
  PFRDA and NABARD learners could not practise Quant or GK at all. Generated
  mocks keep reading sections only: a mock's shape is the exam's authored
  pattern, never this list. No ``exam_phase_sections`` rows are implied.

Tier (REG-CORPUS-04). An authored row may carry ``metadata.exam_tier``
(``foundation`` | ``officer``). :data:`EXAM_TIERS` maps an exam slug to its
tier in one place. Tier never affects eligibility; topic practice asks for
same-tier rows by default (``same_tier_only``) and may include the other tier.
A row with no tier, or an exam with no tier, is never tier-filtered.

No new table and no junction: ``topics.metadata.exams`` is already the
catalogue's exam tag (``workbench/catalogs/topic_catalog_regulatory.json``).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterable

logger = logging.getLogger("career_copilot.exam_intelligence.authored_scope")

#: exam slug -> the key carried in ``topics.metadata.exams``. Explicit, never
#: derived from the slug's shape: a new exam is opted in by adding a line here.
EXAM_TOPIC_KEYS: dict[str, str] = {
    "sebi-grade-a": "sebi",
    "pfrda-grade-a": "pfrda",
    "ifsca-grade-a": "ifsca",
}

#: Subjects whose topics are shared across exam bodies and carry no
#: ``metadata.exams`` key. Only these can be served through the body-agnostic
#: rule; an unkeyed topic of any other subject stays invisible to every exam.
BODY_AGNOSTIC_SUBJECTS: frozenset[str] = frozenset({
    "quantitative-aptitude",
    "general-intelligence-reasoning",
    "english-language",
    "general-knowledge",
})

EXAM_TIER_VALUES = ("foundation", "officer")

#: exam slug -> authored-content tier. Explicit, like EXAM_TOPIC_KEYS: an exam
#: missing here is never tier-filtered. Keyed by LIVE ``exams.slug`` values
#: (operator-verified 2026-09-26, REG-CORPUS-05); a slug that does not exist
#: live is dead config, so none is listed speculatively.
EXAM_TIERS: dict[str, str] = {
    # foundation — SSC, IBPS/SBI Clerk, RRB, RBI Assistant
    "national-ssc-combined-graduate-level-cgl": "foundation",
    "national-ssc-combined-higher-secondary-level-chsl": "foundation",
    "national-ssc-multi-tasking-staff-mts-havaldar": "foundation",
    "national-ssc-cpo-delhi-police-capf-sub-inspector": "foundation",
    "national-ssc-gd-constable": "foundation",
    "national-ibps-clerk": "foundation",
    "national-sbi-clerk-junior-associate": "foundation",
    "national-ibps-rrb-office-assistant": "foundation",
    "national-rrb-group-d-level-1": "foundation",
    "national-rbi-assistant": "foundation",
    "rrb-ntpc": "foundation",
    # officer — IBPS/SBI PO, RRB officers, RBI, regulators, NABARD, LIC
    "ibps-po": "officer",
    "sbi-po": "officer",
    "national-ibps-rrb-officer-scale-i-ii-iii": "officer",
    "rbi-grade-b": "officer",
    "sebi-grade-a": "officer",
    "ifsca-grade-a": "officer",
    "pfrda-grade-a": "officer",
    "national-nabard-grade-a": "officer",
    "national-lic-aao-ado": "officer",
}

#: The shared QRE + static GK subjects (a subset of BODY_AGNOSTIC_SUBJECTS).
QRE_GK_SUBJECTS: frozenset[str] = frozenset({
    "english-language",
    "general-intelligence-reasoning",
    "quantitative-aptitude",
    "general-knowledge",
})

#: exam slug -> body-agnostic subject slugs its learners may PRACTISE by topic,
#: in addition to whatever its exam_phase_sections examine. Topic practice only
#: (see module docstring). Explicit so it can be diffed against EXAM_TIERS by
#: tests/study_os/test_authored_scope_config.py; upsc-cse is deliberately absent
#: and no sandbox exam may appear.
EXAM_AGNOSTIC_SUBJECTS: dict[str, frozenset[str]] = {
    "national-ssc-combined-graduate-level-cgl": QRE_GK_SUBJECTS,
    "national-ssc-combined-higher-secondary-level-chsl": QRE_GK_SUBJECTS,
    "national-ssc-multi-tasking-staff-mts-havaldar": QRE_GK_SUBJECTS,
    "national-ssc-cpo-delhi-police-capf-sub-inspector": QRE_GK_SUBJECTS,
    "national-ssc-gd-constable": QRE_GK_SUBJECTS,
    "national-ibps-clerk": QRE_GK_SUBJECTS,
    "national-sbi-clerk-junior-associate": QRE_GK_SUBJECTS,
    "national-ibps-rrb-office-assistant": QRE_GK_SUBJECTS,
    "national-rrb-group-d-level-1": QRE_GK_SUBJECTS,
    "national-rbi-assistant": QRE_GK_SUBJECTS,
    "rrb-ntpc": QRE_GK_SUBJECTS,
    "ibps-po": QRE_GK_SUBJECTS,
    "sbi-po": QRE_GK_SUBJECTS,
    "national-ibps-rrb-officer-scale-i-ii-iii": QRE_GK_SUBJECTS,
    "rbi-grade-b": QRE_GK_SUBJECTS,
    "sebi-grade-a": QRE_GK_SUBJECTS,
    "ifsca-grade-a": QRE_GK_SUBJECTS,
    "pfrda-grade-a": QRE_GK_SUBJECTS,
    "national-nabard-grade-a": QRE_GK_SUBJECTS,
    "national-lic-aao-ado": QRE_GK_SUBJECTS,
}

_SANDBOX_MARK = "sandbox"

AUTHORED_SOURCE_KIND = "authored"

_ID_BATCH = 250  # repo-wide IN() bound (PostgREST URL length)


@dataclass(frozen=True)
class ExamAuthoredScope:
    """What an exam may be served from the authored bank."""

    key: str | None
    agnostic_subject_ids: frozenset[str]
    tier: str | None

    @property
    def empty(self) -> bool:
        return self.key is None and not self.agnostic_subject_ids


def _norm_slug(slug: str | None) -> str:
    return str(slug or "").strip().lower()


def topic_key_for_exam_slug(slug: str | None) -> str | None:
    """The topic-exam key for an exam slug, or ``None`` when it has none."""
    if not slug:
        return None
    return EXAM_TOPIC_KEYS.get(_norm_slug(slug))


def exam_tier_for_slug(slug: str | None) -> str | None:
    """The authored-content tier for an exam slug, or ``None``."""
    if not slug:
        return None
    return EXAM_TIERS.get(_norm_slug(slug))


def _exam_slug(sb: Any, exam_id: str | None) -> str | None:
    if not exam_id:
        return None
    try:
        rows = sb.table("exams").select("id,slug").eq("id", exam_id).limit(1).execute().data or []
    except Exception:  # noqa: BLE001 — authored inclusion is additive; never break the PYQ pool
        logger.warning("authored_scope: exam slug read failed exam=%s", exam_id, exc_info=True)
        return None
    return rows[0].get("slug") if rows else None


def configured_agnostic_subjects(slug: str | None) -> frozenset[str]:
    """Body-agnostic subject slugs :data:`EXAM_AGNOSTIC_SUBJECTS` grants the
    exam for topic practice. Never any for a sandbox exam, and never a subject
    outside BODY_AGNOSTIC_SUBJECTS."""
    s = _norm_slug(slug)
    if not s or _SANDBOX_MARK in s:
        return frozenset()
    return frozenset(EXAM_AGNOSTIC_SUBJECTS.get(s, frozenset())) & BODY_AGNOSTIC_SUBJECTS


def agnostic_config_drift() -> dict[str, list[str]]:
    """Exams in one config map but not the other (REG-CORPUS-05 drift guard)."""
    tiers, agnostic = set(EXAM_TIERS), set(EXAM_AGNOSTIC_SUBJECTS)
    return {
        "agnostic_without_tier": sorted(agnostic - tiers),
        "tier_without_agnostic": sorted(tiers - agnostic),
    }


def log_agnostic_config_drift(log: logging.Logger = logger) -> list[str]:
    """Startup check: warn for every exam granted body-agnostic eligibility by
    config but given no tier (its learners would get both tiers unfiltered).
    Returns the offending slugs."""
    drift = agnostic_config_drift()
    for slug in drift["agnostic_without_tier"]:
        log.warning("authored_scope: exam %s has body-agnostic eligibility but no EXAM_TIERS entry", slug)
    for slug in drift["tier_without_agnostic"]:
        log.warning("authored_scope: exam %s has a tier but no EXAM_AGNOSTIC_SUBJECTS entry", slug)
    return drift["agnostic_without_tier"]


_WARNED_UNTIERED: set[str] = set()


def resolve_exam_topic_key(sb: Any, exam_id: str | None) -> str | None:
    """Read the exam's slug and map it. ``None`` on no exam, unknown slug, or a
    failed read — the caller then serves no keyed authored rows (fail closed)."""
    return topic_key_for_exam_slug(_exam_slug(sb, exam_id))


def _chunked_in(sb: Any, table: str, cols: str, col: str, ids: list[str]) -> list[dict]:
    out: list[dict] = []
    for i in range(0, len(ids), _ID_BATCH):
        out.extend(sb.table(table).select(cols).in_(col, ids[i : i + _ID_BATCH]).execute().data or [])
    return out


def configured_subject_ids(sb: Any, slug: str | None) -> frozenset[str]:
    """Subject ids for :func:`configured_agnostic_subjects`. Fail closed: a
    failed read grants nothing."""
    slugs = sorted(configured_agnostic_subjects(slug))
    if not slugs:
        return frozenset()
    try:
        rows = sb.table("subjects").select("id,slug").in_("slug", slugs).execute().data or []
    except Exception:  # noqa: BLE001
        logger.warning("authored_scope: configured subjects read failed exam=%s", slug, exc_info=True)
        return frozenset()
    return frozenset(str(r["id"]) for r in rows if r.get("id") and _norm_slug(r.get("slug")) in slugs)


def agnostic_subject_ids_for_exam(sb: Any, exam_id: str | None) -> frozenset[str]:
    """Body-agnostic subjects the exam's phase sections examine.

    Fail closed: any failed read yields the empty set (no body-agnostic rows);
    the keyed path is unaffected."""
    if not exam_id:
        return frozenset()
    try:
        phases = sb.table("exam_phases").select("id").eq("exam_id", exam_id).execute().data or []
        phase_ids = sorted({str(p["id"]) for p in phases if p.get("id")})
        if not phase_ids:
            return frozenset()
        sections = _chunked_in(sb, "exam_phase_sections", "exam_phase_id,subject_id", "exam_phase_id", phase_ids)
        subject_ids = sorted({str(s["subject_id"]) for s in sections if s.get("subject_id")})
        if not subject_ids:
            return frozenset()
        subjects = _chunked_in(sb, "subjects", "id,slug", "id", subject_ids)
    except Exception:  # noqa: BLE001
        logger.warning("authored_scope: section subjects read failed exam=%s", exam_id, exc_info=True)
        return frozenset()
    return frozenset(
        str(s["id"]) for s in subjects
        if s.get("id") and _norm_slug(s.get("slug")) in BODY_AGNOSTIC_SUBJECTS
    )


def resolve_exam_scope(
    sb: Any, exam_id: str | None, *, include_configured_subjects: bool = False
) -> ExamAuthoredScope:
    """Key, body-agnostic subjects and tier for ``exam_id``. Empty on no exam
    or a failed slug read.

    Body-agnostic subjects are the exam's phase-section subjects, UNIONed with
    :data:`EXAM_AGNOSTIC_SUBJECTS` when ``include_configured_subjects`` (topic
    practice only)."""
    slug = _exam_slug(sb, exam_id)
    if not slug:
        return ExamAuthoredScope(None, frozenset(), None)
    agnostic = agnostic_subject_ids_for_exam(sb, exam_id)
    if include_configured_subjects:
        agnostic = agnostic | configured_subject_ids(sb, slug)
    tier = exam_tier_for_slug(slug)
    if agnostic and tier is None and _norm_slug(slug) not in _WARNED_UNTIERED:
        _WARNED_UNTIERED.add(_norm_slug(slug))
        logger.warning("authored_scope: exam %s serves body-agnostic rows but has no tier", slug)
    return ExamAuthoredScope(key=topic_key_for_exam_slug(slug), agnostic_subject_ids=agnostic, tier=tier)


def topic_carries_key(topic_metadata: Any, key: str) -> bool:
    """True when ``metadata.exams`` is a list containing ``key``."""
    if not key or not isinstance(topic_metadata, dict):
        return False
    exams = topic_metadata.get("exams")
    return isinstance(exams, list) and key in exams


def topic_is_eligible(topic: dict, scope: ExamAuthoredScope) -> bool:
    """The topic half of the eligibility rule (module docstring)."""
    meta = topic.get("metadata")
    if isinstance(meta, dict) and "exams" in meta:
        return bool(scope.key) and topic_carries_key(meta, scope.key)
    return str(topic.get("subject_id") or "") in scope.agnostic_subject_ids


def eligible_topic_ids(
    sb: Any,
    key: "str | ExamAuthoredScope | None",
    topic_ids: Iterable[str],
) -> set[str]:
    """The subset of ``topic_ids`` eligible under ``key`` (a bare topic-exam
    key, keyed rule only) or a full :class:`ExamAuthoredScope`.

    Fail closed: a failed topics read yields no eligible topics (and so no
    authored rows), never an unfiltered set.
    """
    scope = key if isinstance(key, ExamAuthoredScope) else ExamAuthoredScope(key, frozenset(), None)
    ids = sorted({str(t) for t in topic_ids if t})
    if scope.empty or not ids:
        return set()
    try:
        rows = _chunked_in(sb, "topics", "id,metadata,subject_id", "id", ids)
    except Exception:  # noqa: BLE001
        logger.warning("authored_scope: topics read failed", exc_info=True)
        return set()
    return {str(r["id"]) for r in rows if r.get("id") and topic_is_eligible(r, scope)}


def row_topic_id(row: dict) -> str | None:
    """A bank row's primary (practised-level) topic: ``microtopic_id`` else ``topic_id``."""
    tid = row.get("microtopic_id") or row.get("topic_id")
    return str(tid) if tid else None


def row_exam_tier(row: dict) -> str | None:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    tier = meta.get("exam_tier")
    return tier if tier in EXAM_TIER_VALUES else None


def apply_authored_filters(q: Any) -> Any:
    """Narrow a ``mock_question_bank`` query to multi-exam authored rows."""
    return (
        q.eq("source_kind", AUTHORED_SOURCE_KIND)
        .is_("pyq_question_id", None)
        .is_("exam_id", None)
    )


def authored_rows_for_exam(
    sb: Any,
    exam_id: str | None,
    fetch: Callable[[], list[dict]],
    *,
    same_tier_only: bool = False,
    include_configured_subjects: bool = False,
) -> list[dict]:
    """Authored rows eligible for ``exam_id``, from a caller-built read.

    ``fetch()`` runs the caller's pool read (its own status / type / validity
    filters plus :func:`apply_authored_filters`) and must select ``topic_id``
    and ``microtopic_id`` (and ``metadata`` when ``same_tier_only``). It is not
    called at all when the exam has no key and no body-agnostic section. Rows
    are re-checked here against the authored predicate so a stub or a partial
    filter can never widen the result.

    ``same_tier_only`` drops rows whose ``metadata.exam_tier`` differs from the
    exam's tier; untiered rows, and every row for an untiered exam, are kept.

    ``include_configured_subjects`` adds :data:`EXAM_AGNOSTIC_SUBJECTS` to the
    exam's section subjects — topic practice passes True; generated mocks and
    diagnostics do not.
    """
    scope = resolve_exam_scope(sb, exam_id, include_configured_subjects=include_configured_subjects)
    if scope.empty:
        return []
    try:
        rows = fetch() or []
    except Exception:  # noqa: BLE001 — fail closed to "no authored rows"
        logger.warning("authored_scope: authored pool read failed exam=%s", exam_id, exc_info=True)
        return []
    rows = [
        r for r in rows
        if r.get("source_kind") == AUTHORED_SOURCE_KIND
        and not r.get("pyq_question_id")
        and not r.get("exam_id")
    ]
    if same_tier_only and scope.tier:
        rows = [r for r in rows if row_exam_tier(r) in (None, scope.tier)]
    if not rows:
        return []
    allowed = eligible_topic_ids(sb, scope, (row_topic_id(r) for r in rows))
    return [r for r in rows if row_topic_id(r) in allowed]
