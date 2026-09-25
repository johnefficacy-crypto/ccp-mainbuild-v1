"""Which authored ``mock_question_bank`` rows an exam's learners may be served (REG-CORPUS-02).

An authored row (``source_kind='authored'``, no ``pyq_question_id``) is written
once and serves every exam whose syllabus covers its topic. It therefore keeps
``exam_id`` NULL, and exam eligibility comes from the topic, not the row:

    row eligible for exam E  ⇔  row.source_kind = 'authored'
                               AND row.pyq_question_id IS NULL
                               AND row.exam_id IS NULL
                               AND key(E) ∈ topic(row).metadata.exams

``topic(row)`` is the row's PRIMARY topic — the single level id the row is
practised at (``microtopic_id`` when set, else ``topic_id``; see
``pyq_practice._row_level_id``). ``key(E)`` comes from :data:`EXAM_TOPIC_KEYS`,
the ONE place an exam slug is mapped to a topic-exam key. An exam with no entry
gets NO authored rows — never all of them — so every existing exam's pools are
unchanged until a key is registered for it here.

No new table and no junction: ``topics.metadata.exams`` is already the
catalogue's exam tag (``workbench/catalogs/topic_catalog_regulatory.json``).
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Iterable

logger = logging.getLogger("career_copilot.exam_intelligence.authored_scope")

#: exam slug -> the key carried in ``topics.metadata.exams``. Explicit, never
#: derived from the slug's shape: a new exam is opted in by adding a line here.
EXAM_TOPIC_KEYS: dict[str, str] = {
    "sebi-grade-a": "sebi",
    "pfrda-grade-a": "pfrda",
    "ifsca-grade-a": "ifsca",
}

AUTHORED_SOURCE_KIND = "authored"

_ID_BATCH = 250  # repo-wide IN() bound (PostgREST URL length)


def topic_key_for_exam_slug(slug: str | None) -> str | None:
    """The topic-exam key for an exam slug, or ``None`` when it has none."""
    if not slug:
        return None
    return EXAM_TOPIC_KEYS.get(str(slug).strip().lower())


def resolve_exam_topic_key(sb: Any, exam_id: str | None) -> str | None:
    """Read the exam's slug and map it. ``None`` on no exam, unknown slug, or a
    failed read — the caller then serves no authored rows (fail closed)."""
    if not exam_id:
        return None
    try:
        rows = sb.table("exams").select("id,slug").eq("id", exam_id).limit(1).execute().data or []
    except Exception:  # noqa: BLE001 — authored inclusion is additive; never break the PYQ pool
        logger.warning("authored_scope: exam slug read failed exam=%s", exam_id, exc_info=True)
        return None
    if not rows:
        return None
    return topic_key_for_exam_slug(rows[0].get("slug"))


def topic_carries_key(topic_metadata: Any, key: str) -> bool:
    """True when ``metadata.exams`` is a list containing ``key``."""
    if not key or not isinstance(topic_metadata, dict):
        return False
    exams = topic_metadata.get("exams")
    return isinstance(exams, list) and key in exams


def eligible_topic_ids(sb: Any, key: str | None, topic_ids: Iterable[str]) -> set[str]:
    """The subset of ``topic_ids`` whose ``metadata.exams`` contains ``key``.

    Fail closed: a failed topics read yields no eligible topics (and so no
    authored rows), never an unfiltered set.
    """
    ids = sorted({str(t) for t in topic_ids if t})
    if not key or not ids:
        return set()
    out: set[str] = set()
    for i in range(0, len(ids), _ID_BATCH):
        chunk = ids[i : i + _ID_BATCH]
        try:
            rows = sb.table("topics").select("id,metadata").in_("id", chunk).execute().data or []
        except Exception:  # noqa: BLE001
            logger.warning("authored_scope: topics read failed", exc_info=True)
            return set()
        out.update(str(r["id"]) for r in rows if r.get("id") and topic_carries_key(r.get("metadata"), key))
    return out


def row_topic_id(row: dict) -> str | None:
    """A bank row's primary (practised-level) topic: ``microtopic_id`` else ``topic_id``."""
    tid = row.get("microtopic_id") or row.get("topic_id")
    return str(tid) if tid else None


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
) -> list[dict]:
    """Authored rows eligible for ``exam_id``, from a caller-built read.

    ``fetch()`` runs the caller's pool read (its own status / type / validity
    filters plus :func:`apply_authored_filters`) and must select ``topic_id``
    and ``microtopic_id``. It is not called at all when the exam has no key, so
    an unkeyed exam costs one slug read and nothing else. Rows are re-checked
    here against the authored predicate so a stub or a partial filter can never
    widen the result.
    """
    key = resolve_exam_topic_key(sb, exam_id)
    if key is None:
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
    if not rows:
        return []
    allowed = eligible_topic_ids(sb, key, (row_topic_id(r) for r in rows))
    return [r for r in rows if row_topic_id(r) in allowed]
