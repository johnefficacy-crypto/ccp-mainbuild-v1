#!/usr/bin/env python3
"""Propose microtopic tags for the regulatory PYQ corpus (SEBI / PFRDA / IFSCA).

Three pieces, run in order:

1. **Candidate builder** — narrows the topic catalogue to the microtopics a
   question could plausibly carry, before the model is asked anything. Filters
   are conjunctive: ``level='microtopic'``, the row's subject equals the
   question's *resolved* subject, and the row's ``metadata.exams`` contains the
   question's regulatory body. Subject resolution goes through an alias map
   file, never string equality — the corpus prints "Economy" where the
   catalogue says ``economics``, and "Company Act" where it says
   ``companies-act``.
2. **Proposer** — prompts a model with each question's stem, options and its
   candidate microtopics, and parses one JSON object back. Every field is
   validated; a malformed response aborts the run rather than defaulting.
3. **Writer** — emits a JSONL record per question and a SQL file of upserts
   into ``pyq_question_topic_tags``.

Nothing here touches a database, ever. A model provider is reached only when
``--live`` asks for it: the client is injected through a single
``Callable[[str], str]`` seam, ``--dry-run`` replays a fixture of canned
responses through the real parser, and a run with neither flag still makes no
network call. ``--live`` reads its key from ``ANTHROPIC_API_KEY`` (never an
argument or a literal), retries rate limits and transient errors with
exponential backoff honouring ``Retry-After``, and aborts the whole run if a
batch is still failing — questions are never silently dropped from the output.

Governance
----------
Every emitted row is ``reviewer_status='pending'``, ``tagging_source='ai'``,
``source_kind='auto_extracted'``. This module cannot emit ``'verified'``:
``_tag_values`` refuses any other status and the SQL emitter asserts it again
before a statement is built. AI proposals enter the review lifecycle; they do
not bypass it (CLAUDE.md -> verified-only reads).

The upsert deliberately does **not** touch ``reviewer_status``,
``reviewed_by`` or ``reviewed_at``, and its ``DO UPDATE`` is guarded on the
stored row still being ``pending``. Re-running after a reviewer has verified or
rejected a proposal must not reset their verdict.

Input contracts
---------------
All three inputs are read from files; none is fetched.

``--questions`` JSONL, one object per line::

    {"id": "<uuid>", "question_text": "...", "subject": "Economy",
     "body": "sebi", "options": [{"label": "a", "text": "..."}, ...]}

``--catalogue`` JSONL, one object per line::

    {"id": "<uuid>", "slug": "money-market-instruments", "name": "...",
     "level": "microtopic", "subject": "economics", "description": "...",
     "metadata": {"exams": ["sebi", "pfrda"]}}

``--alias-map`` JSON object, printed subject -> catalogue subject slug::

    {"Economy": "economics", "Company Act": "companies-act"}

Unknown keys are tolerated on every input (an export gaining a column must not
break the run); missing or wrong-typed *required* keys abort it by name and
line number.

Usage::

    python scripts/propose_pyq_topic_tags.py \\
        --questions questions.jsonl --catalogue catalogue.jsonl \\
        --alias-map subject_aliases.json \\
        --batch-size 10 \\
        --dry-run --fixture responses.json \\
        --out-jsonl proposals.jsonl --out-sql proposals.sql

Live, against the provider::

    export ANTHROPIC_API_KEY=...
    python scripts/propose_pyq_topic_tags.py \\
        --questions questions.jsonl --catalogue catalogue.jsonl \\
        --alias-map subject_aliases.json \\
        --batch-size 10 --live --model claude-opus-5 \\
        --out-jsonl proposals.jsonl --out-sql proposals.sql
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from typing import Any, Callable, Iterable, Sequence

# ── constants ────────────────────────────────────────────────────────────────

TABLE = "pyq_question_topic_tags"

# Locked by governance. A proposal is a proposal until a human says otherwise.
REVIEWER_STATUS = "pending"
TAGGING_SOURCE = "ai"
SOURCE_KIND = "auto_extracted"
TAG_ROLE = "primary"

# Stamped on every row and mixed into the idempotency key, so re-running a
# newer proposer version writes new rows rather than silently overwriting the
# older version's proposals under the same key.
EXTRACTOR_VERSION = "pyq-topic-proposer-v1"

MICROTOPIC = "microtopic"
KNOWN_BODIES = ("sebi", "pfrda", "ifsca")

STATUS_MAPPED = "MAPPED"
STATUS_UNMAPPED = "UNMAPPED"

RATIONALE_WORD_CAP = 20

# A batch whose every mapped proposal carries the identical confidence is the
# failure this cap exists to catch: the model emitting a fixed 0.9 rather than
# estimating. Below this many mapped proposals, identical values are plausible
# by chance and are not treated as degenerate.
MIN_BATCH_FOR_VARIANCE_CHECK = 4

# ── live provider defaults ───────────────────────────────────────────────────
#
# Anthropic is the repo's established provider: it is the only one of the three
# pinned SDKs (anthropic, openai, google-genai) that any module actually
# imports, and app/study_os/writing_practice/semantic_evaluator.py is the
# pattern this adapter follows — deferred import, key resolved from the
# environment by the SDK, and a getattr-based transient classifier so neither
# this module nor its tests hard-depend on the package being installed.
API_KEY_ENV = "ANTHROPIC_API_KEY"
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TIMEOUT_S = 120.0
DEFAULT_MAX_RETRIES = 4
DEFAULT_BACKOFF_BASE_S = 1.0
# Ceiling on one backoff sleep, including a Retry-After the provider asks for.
MAX_BACKOFF_S = 60.0


class ProposerError(RuntimeError):
    """Any failure that must abort the run rather than degrade it."""


# ── input loading ────────────────────────────────────────────────────────────


def _read_jsonl(path: str) -> list[tuple[int, dict]]:
    """Read a JSONL file as (line_number, object) pairs.

    Blank lines are skipped; anything else that is not a JSON object is an
    error naming the line, because a half-read export is indistinguishable from
    a short one once the rows are in memory.
    """
    rows: list[tuple[int, dict]] = []
    with open(path, encoding="utf-8-sig") as fh:
        for lineno, raw in enumerate(fh, start=1):
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ProposerError(f"{path}:{lineno}: not valid JSON — {exc}") from exc
            if not isinstance(obj, dict):
                raise ProposerError(
                    f"{path}:{lineno}: expected a JSON object, got {type(obj).__name__}"
                )
            rows.append((lineno, obj))
    if not rows:
        raise ProposerError(f"{path}: no rows")
    return rows


def _require(obj: dict, key: str, where: str, types: tuple[type, ...]) -> Any:
    if key not in obj:
        raise ProposerError(f"{where}: missing required key {key!r}")
    val = obj[key]
    if not isinstance(val, types) or isinstance(val, bool):
        names = "/".join(t.__name__ for t in types)
        raise ProposerError(
            f"{where}: {key!r} is {type(val).__name__}, expected {names}"
        )
    return val


def normalise_subject(raw: str) -> str:
    """Fold a printed subject to a comparable form.

    Case, surrounding whitespace, internal runs of whitespace and trailing
    punctuation all vary across the corpus ("Economy", "economy ", "ECONOMY.").
    None of that is a different subject, so none of it should produce a
    different alias-map lookup.
    """
    return re.sub(r"\s+", " ", raw.strip().strip(".,;:").casefold())


def load_alias_map(path: str) -> dict[str, str]:
    """Load the printed-subject -> catalogue-subject-slug map.

    Keys are normalised on load so the file can be written the way a human
    reads it ("Company Act") and still match a corpus that prints
    "company act ".
    """
    with open(path, encoding="utf-8-sig") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ProposerError(f"{path}: expected a JSON object of alias -> subject slug")
    out: dict[str, str] = {}
    for alias, slug in raw.items():
        if not isinstance(slug, str) or not slug.strip():
            raise ProposerError(f"{path}: alias {alias!r} maps to {slug!r}, expected a slug")
        key = normalise_subject(alias)
        if key in out and out[key] != slug:
            raise ProposerError(
                f"{path}: alias {alias!r} normalises to {key!r} which already maps "
                f"to {out[key]!r} — two aliases cannot claim one subject differently"
            )
        out[key] = slug
    return out


def load_catalogue(path: str) -> list[dict]:
    """Load catalogue rows, validating the fields the filter depends on."""
    rows: list[dict] = []
    seen_slugs: dict[str, str] = {}
    for lineno, obj in _read_jsonl(path):
        where = f"{path}:{lineno}"
        row = {
            "id": _require(obj, "id", where, (str,)),
            "slug": _require(obj, "slug", where, (str,)),
            "name": _require(obj, "name", where, (str,)),
            "level": _require(obj, "level", where, (str,)),
            "subject": _require(obj, "subject", where, (str,)),
            "description": obj.get("description") or "",
        }
        if not isinstance(row["description"], str):
            raise ProposerError(f"{where}: 'description' is not a string")
        meta = obj.get("metadata") or {}
        if not isinstance(meta, dict):
            raise ProposerError(f"{where}: 'metadata' is not an object")
        exams = meta.get("exams") or []
        if not isinstance(exams, list) or any(not isinstance(e, str) for e in exams):
            raise ProposerError(f"{where}: metadata.exams is not a list of strings")
        row["exams"] = [e.strip().casefold() for e in exams]
        # A slug is the writer's only handle on a topic_id, so two rows sharing
        # one slug would make the resolution ambiguous rather than merely
        # redundant. Caught at load, before a proposal can depend on it.
        if row["slug"] in seen_slugs and seen_slugs[row["slug"]] != row["id"]:
            raise ProposerError(
                f"{where}: slug {row['slug']!r} already used by topic "
                f"{seen_slugs[row['slug']]}"
            )
        seen_slugs[row["slug"]] = row["id"]
        rows.append(row)
    return rows


def load_questions(path: str, alias_map: dict[str, str]) -> list[dict]:
    """Load questions and resolve each one's subject through the alias map.

    Every unresolved subject is collected and reported together: an operator
    extending the alias map wants the whole list, not one name per run.
    """
    rows: list[dict] = []
    unresolved: dict[str, list[str]] = {}
    for lineno, obj in _read_jsonl(path):
        where = f"{path}:{lineno}"
        raw_subject = _require(obj, "subject", where, (str,))
        body = _require(obj, "body", where, (str,)).strip().casefold()
        if body not in KNOWN_BODIES:
            raise ProposerError(
                f"{where}: body {body!r} is not one of {'/'.join(KNOWN_BODIES)}"
            )
        options = obj.get("options") or []
        if not isinstance(options, list):
            raise ProposerError(f"{where}: 'options' is not a list")
        parsed_options = []
        for i, opt in enumerate(options):
            if not isinstance(opt, dict):
                raise ProposerError(f"{where}: options[{i}] is not an object")
            parsed_options.append({
                "label": str(opt.get("label") or "").strip(),
                "text": str(opt.get("text") or "").strip(),
            })

        key = normalise_subject(raw_subject)
        resolved = alias_map.get(key)
        if resolved is None:
            unresolved.setdefault(raw_subject, []).append(where)
            continue

        rows.append({
            "id": _require(obj, "id", where, (str,)),
            "question_text": _require(obj, "question_text", where, (str,)),
            "raw_subject": raw_subject,
            "subject": resolved,
            "body": body,
            "options": parsed_options,
        })

    if unresolved:
        listed = "; ".join(
            f"{name!r} ({len(where)} question(s), first at {where[0]})"
            for name, where in sorted(unresolved.items())
        )
        raise ProposerError(
            "these printed subjects have no entry in the alias map, so their "
            f"candidate sets would be silently empty: {listed}"
        )

    ids = [r["id"] for r in rows]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ProposerError(f"{path}: duplicated question id(s) {dupes}")
    return rows


# ── 1. candidate builder ─────────────────────────────────────────────────────


def build_candidates(question: dict, catalogue: Sequence[dict]) -> list[dict]:
    """The microtopics this question is allowed to be tagged with.

    Three conjunctive filters, in the order that discards the most first:

    ``level='microtopic'``  a topic- or concept-level row is the wrong
                            granularity for a question tag.
    subject                 compared against the question's *resolved* subject,
                            which came from the alias map — never against the
                            printed one.
    body                    the row's ``metadata.exams`` must name this
                            question's regulator. A SEBI question cannot be
                            tagged with a PFRDA-only microtopic however well the
                            text matches.

    The model never sees a topic this returns nothing for, which is what keeps
    a proposal inside the catalogue instead of inventing a slug.
    """
    subject = question["subject"]
    body = question["body"]
    return [
        row for row in catalogue
        if row["level"] == MICROTOPIC
        and row["subject"] == subject
        and body in row["exams"]
    ]


# ── 2. proposer ──────────────────────────────────────────────────────────────

OUTPUT_CONTRACT = """\
Return ONE JSON object and nothing else — no prose, no code fence:

{"proposals": [
  {"question_id": "<id exactly as given>",
   "status": "MAPPED" | "UNMAPPED",
   "topic_slug": "<slug from that question's candidate list>" | null,
   "confidence": <number 0.0-1.0>,
   "rationale": "<at most 20 words>",
   "reason": "<why no candidate fits; UNMAPPED only, else null>"}
]}

Rules:
- One entry per question given, same ids, no extras.
- topic_slug MUST be copied from that question's own candidate list. Never
  invent one, and never borrow another question's candidate.
- If no candidate genuinely fits, answer UNMAPPED with a reason. UNMAPPED is a
  correct answer, not a failure — a forced wrong tag costs a reviewer more
  than an honest miss.
- confidence is your real estimate that a subject expert would accept this tag:
  0.9-1.0 the stem names the microtopic outright; 0.7-0.89 clearly within it;
  0.5-0.69 plausible, competing candidate exists; below 0.5 a guess worth
  reviewing. For UNMAPPED it is your confidence that nothing fits.
  Do not emit the same number for every question.
"""


def build_prompt(batch: Sequence[dict], candidates: dict[str, list[dict]]) -> str:
    """Render one batch of questions with their candidate microtopics."""
    parts = [
        "You tag Indian regulatory exam questions (SEBI / PFRDA / IFSCA) with "
        "one microtopic from a fixed catalogue.",
        "",
        OUTPUT_CONTRACT,
        "",
        "QUESTIONS",
        "",
    ]
    for q in batch:
        parts.append(f"--- question_id: {q['id']}")
        parts.append(f"subject: {q['subject']}   body: {q['body']}")
        parts.append(f"stem: {q['question_text']}")
        for opt in q["options"]:
            parts.append(f"  ({opt['label']}) {opt['text']}")
        cands = candidates.get(q["id"], [])
        if cands:
            parts.append("candidate microtopics:")
            for row in cands:
                desc = f" — {row['description']}" if row["description"] else ""
                parts.append(f"  - {row['slug']}: {row['name']}{desc}")
        else:
            # Still shown to the model so the batch shape stays uniform, and so
            # an empty candidate set produces a recorded UNMAPPED rather than a
            # silently absent question.
            parts.append("candidate microtopics: (none — answer UNMAPPED)")
        parts.append("")
    return "\n".join(parts)


def batched(rows: Sequence[dict], size: int) -> Iterable[list[dict]]:
    """Split rows into batches of at most ``size``, preserving order."""
    if size < 1:
        raise ProposerError(f"batch size must be at least 1, got {size}")
    for i in range(0, len(rows), size):
        yield list(rows[i:i + size])


def _strip_fence(text: str) -> str:
    """Drop a ```json fence if the model wrapped its object in one."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def parse_response(
    text: str, batch: Sequence[dict], candidates: dict[str, list[dict]]
) -> list[dict]:
    """Parse and fully validate one batch response.

    Every branch here raises. Nothing is defaulted, coerced or dropped: a
    response this function cannot vouch for entirely is a response that would
    put an unreviewable row in front of an operator, and the run is worth less
    than that.
    """
    try:
        obj = json.loads(_strip_fence(text))
    except json.JSONDecodeError as exc:
        raise ProposerError(f"model response is not valid JSON — {exc}") from exc
    if not isinstance(obj, dict):
        raise ProposerError(
            f"model response is a {type(obj).__name__}, expected a JSON object"
        )
    if "proposals" not in obj:
        raise ProposerError("model response has no 'proposals' key")
    raw = obj["proposals"]
    if not isinstance(raw, list):
        raise ProposerError(f"'proposals' is {type(raw).__name__}, expected a list")

    expected = [q["id"] for q in batch]
    got = [p.get("question_id") if isinstance(p, dict) else None for p in raw]
    if sorted(map(str, got)) != sorted(expected):
        missing = sorted(set(expected) - {str(g) for g in got})
        extra = sorted({str(g) for g in got} - set(expected))
        raise ProposerError(
            "model response does not cover the batch exactly — "
            f"missing {missing}, unexpected {extra}"
        )

    by_id = {q["id"]: q for q in batch}
    out: list[dict] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ProposerError(f"proposals[{i}] is not an object")
        qid = str(item["question_id"])
        where = f"proposals[{i}] (question {qid})"

        status = item.get("status")
        if status not in (STATUS_MAPPED, STATUS_UNMAPPED):
            raise ProposerError(
                f"{where}: status {status!r} is not {STATUS_MAPPED}/{STATUS_UNMAPPED}"
            )

        conf = item.get("confidence")
        if isinstance(conf, bool) or not isinstance(conf, (int, float)):
            raise ProposerError(
                f"{where}: confidence is {conf!r}, expected a number in 0.0-1.0"
            )
        conf = float(conf)
        if not 0.0 <= conf <= 1.0:
            raise ProposerError(f"{where}: confidence {conf} is outside 0.0-1.0")

        rationale = item.get("rationale") or ""
        if not isinstance(rationale, str):
            raise ProposerError(f"{where}: rationale is not a string")
        rationale = rationale.strip()
        words = len(rationale.split())
        if words > RATIONALE_WORD_CAP:
            raise ProposerError(
                f"{where}: rationale is {words} words, capped at {RATIONALE_WORD_CAP}"
            )

        slug = item.get("topic_slug")
        reason = item.get("reason") or ""
        if not isinstance(reason, str):
            raise ProposerError(f"{where}: reason is not a string")

        if status == STATUS_MAPPED:
            if not isinstance(slug, str) or not slug.strip():
                raise ProposerError(f"{where}: MAPPED with topic_slug {slug!r}")
            slug = slug.strip()
            allowed = {row["slug"] for row in candidates.get(qid, [])}
            if slug not in allowed:
                # The single most damaging failure mode: a slug that looks
                # right, resolves to nothing, and would otherwise reach the
                # writer. Rejected against this question's own candidates.
                raise ProposerError(
                    f"{where}: topic_slug {slug!r} is not among this question's "
                    f"{len(allowed)} candidate microtopic(s)"
                )
        else:
            if slug not in (None, "", "null"):
                raise ProposerError(
                    f"{where}: UNMAPPED must not carry a topic_slug, got {slug!r}"
                )
            slug = None
            if not reason.strip():
                raise ProposerError(f"{where}: UNMAPPED requires a non-empty reason")

        q = by_id[qid]
        out.append({
            "question_id": qid,
            "status": status,
            "topic_slug": slug,
            "confidence": conf,
            "rationale": rationale,
            "reason": reason.strip(),
            "subject": q["subject"],
            "body": q["body"],
            "candidate_count": len(candidates.get(qid, [])),
        })

    _reject_degenerate_confidence(out)
    return out


def _reject_degenerate_confidence(proposals: Sequence[dict]) -> None:
    """A batch of mapped proposals that all share one confidence is not an estimate.

    The contract asks for a real 0-1 judgement. A model that answers 0.9 to
    everything satisfies every per-field check while carrying no information a
    reviewer can triage on, so the batch is rejected rather than written.
    """
    mapped = [p["confidence"] for p in proposals if p["status"] == STATUS_MAPPED]
    if len(mapped) >= MIN_BATCH_FOR_VARIANCE_CHECK and len(set(mapped)) == 1:
        raise ProposerError(
            f"every one of {len(mapped)} mapped proposals in this batch carries "
            f"confidence {mapped[0]} — that is a constant, not an estimate"
        )


def propose(
    questions: Sequence[dict],
    catalogue: Sequence[dict],
    *,
    client: Callable[[str], str],
    batch_size: int,
) -> list[dict]:
    """Run the proposer over every question, one batch at a time."""
    candidates = {q["id"]: build_candidates(q, catalogue) for q in questions}
    out: list[dict] = []
    for batch in batched(questions, batch_size):
        response = client(build_prompt(batch, candidates))
        out.extend(parse_response(response, batch, candidates))
    return out


def fixture_client(path: str) -> Callable[[str], str]:
    """A client that replays canned responses in batch order.

    Drives ``--dry-run`` with no network. The fixture is a JSON list of the raw
    strings a model would have returned, so the real parser and every one of its
    checks run exactly as they would live.
    """
    with open(path, encoding="utf-8-sig") as fh:
        responses = json.load(fh)
    if not isinstance(responses, list) or not all(isinstance(r, str) for r in responses):
        raise ProposerError(f"{path}: expected a JSON list of raw response strings")
    calls = {"n": 0}

    def _client(_prompt: str) -> str:
        i = calls["n"]
        if i >= len(responses):
            raise ProposerError(
                f"{path}: fixture has {len(responses)} response(s) but the run "
                f"asked for batch {i + 1} — check --batch-size"
            )
        calls["n"] += 1
        return responses[i]

    return _client


def no_client(_prompt: str) -> str:
    raise ProposerError(
        "no model client configured. This script does not open a network "
        "connection on its own: run with --dry-run --fixture <file>, --live to "
        "call the provider, or supply a client programmatically."
    )


def _is_transient(exc: BaseException) -> bool:
    """Retryable: rate limit, timeout, connection failure, or a 5xx.

    Mirrors ``semantic_evaluator._is_transient``. Types are looked up with
    ``getattr`` so a missing or older SDK degrades to "not retryable" instead of
    raising during error handling.
    """
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    try:
        import anthropic
    except ImportError:
        return False
    transient_types = tuple(
        t for t in (
            getattr(anthropic, "RateLimitError", None),
            getattr(anthropic, "APITimeoutError", None),
            getattr(anthropic, "APIConnectionError", None),
            getattr(anthropic, "InternalServerError", None),
        ) if t is not None
    )
    if transient_types and isinstance(exc, transient_types):
        return True
    status_exc = getattr(anthropic, "APIStatusError", None)
    if status_exc is not None and isinstance(exc, status_exc):
        return int(getattr(exc, "status_code", 0) or 0) >= 500
    return False


def _retry_after_s(exc: BaseException) -> float | None:
    """The provider's own Retry-After, in seconds, when it sent one.

    A 429 usually carries the wait it wants; honouring it beats guessing.
    """
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if headers is None:
        return None
    try:
        raw = headers.get("retry-after")
    except Exception:  # noqa: BLE001 - a header mapping that does not behave
        return None
    if raw is None:
        return None
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None  # HTTP-date form; fall back to exponential backoff
    return value if value >= 0 else None


def _backoff_s(attempt: int, base_s: float, exc: BaseException) -> float:
    """Seconds to wait before retry ``attempt`` (1-based)."""
    asked = _retry_after_s(exc)
    if asked is not None:
        return min(asked, MAX_BACKOFF_S)
    return min(base_s * (2 ** (attempt - 1)), MAX_BACKOFF_S)


def _response_text(response: Any) -> str:
    """Concatenate the text blocks of a Messages response.

    Refusals and ``max_tokens`` truncation are named here rather than left to
    surface downstream as a confusing parse failure — a truncated batch is a
    provider-side abort, not a malformed model reply.
    """
    stop_reason = getattr(response, "stop_reason", None)
    if stop_reason == "refusal":
        raise ProposerError(
            "the provider declined this batch (stop_reason='refusal'); nothing "
            "was proposed for it"
        )
    if stop_reason == "max_tokens":
        raise ProposerError(
            f"the response hit max_tokens ({DEFAULT_MAX_TOKENS}) and is truncated; "
            f"re-run with a smaller --batch-size"
        )
    parts = [
        getattr(block, "text", "")
        for block in (getattr(response, "content", None) or [])
        if getattr(block, "type", None) == "text"
    ]
    text = "".join(parts).strip()
    if not text:
        raise ProposerError("the provider returned a response with no text content")
    return text


def anthropic_client(
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base_s: float = DEFAULT_BACKOFF_BASE_S,
    client_factory: Callable[[], Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[str], str]:
    """A live client callable over the Anthropic Messages API.

    Satisfies the same ``Callable[[str], str]`` seam ``propose`` takes, so the
    parser, writer and ``--dry-run`` path are untouched by this being live.

    The key is read from ``ANTHROPIC_API_KEY`` in the environment and is never
    passed as a literal; its absence is raised **here**, at construction, so a
    misconfigured run fails before a single batch is sent rather than partway
    through the corpus.

    Retries are this function's own: the SDK's built-in retry is switched off
    (``max_retries=0``) so one backoff policy governs, and it is observable in
    tests through the injected ``sleep``. A batch that is still failing after
    ``max_retries`` raises ``ProposerError``, which aborts the run — a dropped
    batch would silently leave those questions untagged with an exit code of 0.
    """
    if not (os.environ.get(API_KEY_ENV) or "").strip():
        raise ProposerError(
            f"{API_KEY_ENV} is not set. Export the key before running --live; "
            f"this script never accepts one as an argument or a literal."
        )

    def _build():
        if client_factory is not None:
            return client_factory()
        import anthropic  # deferred: --dry-run must not need the SDK installed

        # Key comes from ANTHROPIC_API_KEY via the SDK's own environment
        # resolution — checked above so the failure is ours and is early.
        # max_retries=0: the retry loop below is the single authority.
        return anthropic.Anthropic(timeout=timeout_s, max_retries=0)

    try:
        client = _build()
    except ProposerError:
        raise
    except ImportError as exc:
        raise ProposerError(
            f"the anthropic SDK is not installed ({exc}); install it or run "
            f"with --dry-run --fixture <file>"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - bad config must not reach a batch
        raise ProposerError(f"could not build the provider client: {exc}") from exc

    def _client(prompt: str) -> str:
        attempt = 0
        while True:
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return _response_text(response)
            except ProposerError:
                raise  # refusal / truncation / empty: not retryable, abort now
            except Exception as exc:  # noqa: BLE001 - classify, then retry or abort
                if _is_transient(exc) and attempt < max_retries:
                    attempt += 1
                    sleep(_backoff_s(attempt, backoff_base_s, exc))
                    continue
                kind = "transient" if _is_transient(exc) else "non-retryable"
                raise ProposerError(
                    f"model call failed after {attempt} retr"
                    f"{'y' if attempt == 1 else 'ies'} "
                    f"({kind} {exc.__class__.__name__}: {str(exc)[:200]}). "
                    f"Aborting: the questions in this batch would otherwise be "
                    f"dropped from the output without any tag."
                ) from exc

    return _client


# ── 3. writer ────────────────────────────────────────────────────────────────


def idempotency_key(question_id: str, topic_id: str, tag_role: str = TAG_ROLE) -> str:
    """Stable identity for one proposed tag.

    Deterministic in the inputs alone, so a second run over the same corpus
    produces the same key and the INSERT upserts instead of duplicating. The
    extractor version is mixed in so a future proposer's rows are new rows
    rather than a silent overwrite of this one's.
    """
    payload = "\x00".join([EXTRACTOR_VERSION, question_id, topic_id, tag_role])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_topic_ids(proposals: Sequence[dict], catalogue: Sequence[dict]) -> dict[str, str]:
    """Map every proposed slug to a topic_id, or abort naming all that fail.

    Reported together rather than one per run: an unresolved slug usually means
    the catalogue export and the proposal file are from different points in
    time, and the operator needs the whole set to judge that.
    """
    by_slug = {row["slug"]: row["id"] for row in catalogue}
    resolved: dict[str, str] = {}
    missing: dict[str, list[str]] = {}
    for p in proposals:
        slug = p["topic_slug"]
        if slug is None:
            continue
        if slug in by_slug:
            resolved[slug] = by_slug[slug]
        else:
            missing.setdefault(slug, []).append(p["question_id"])
    if missing:
        listed = "; ".join(
            f"{slug!r} (proposed for {len(qs)} question(s), first {qs[0]})"
            for slug, qs in sorted(missing.items())
        )
        raise ProposerError(
            f"these topic slugs do not resolve against the catalogue export: {listed}"
        )
    return resolved


def _tag_values(proposal: dict, topic_id: str) -> dict:
    """The column values for one row, with the governance constants pinned."""
    if REVIEWER_STATUS != "pending":
        raise ProposerError(
            f"refusing to write reviewer_status={REVIEWER_STATUS!r}: this "
            "module emits proposals for review, never verified rows"
        )
    return {
        "question_id": proposal["question_id"],
        "topic_id": topic_id,
        "tag_role": TAG_ROLE,
        "tag_weight": 1,
        "tagging_source": TAGGING_SOURCE,
        "source_kind": SOURCE_KIND,
        "reviewer_status": REVIEWER_STATUS,
        "confidence_score": round(float(proposal["confidence"]), 3),
        "extractor_version": EXTRACTOR_VERSION,
        "idempotency_key": idempotency_key(proposal["question_id"], topic_id),
        "confidence_by_field": {"topic_id": round(float(proposal["confidence"]), 3)},
        "metadata": {
            "rationale": proposal["rationale"],
            "candidate_count": proposal["candidate_count"],
            "proposer": EXTRACTOR_VERSION,
        },
    }


def write_jsonl(proposals: Sequence[dict], path: str) -> int:
    """Write one record per question, mapped and unmapped alike.

    UNMAPPED records are kept: they are the audit trail for a question the
    corpus could not tag, and dropping them would make an unmapped question
    indistinguishable from one that was never run.
    """
    with open(path, "w", encoding="utf-8") as fh:
        for p in proposals:
            fh.write(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n")
    return len(proposals)


def _sql_str(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _sql_json(value: Any) -> str:
    return _sql_str(json.dumps(value, ensure_ascii=False, sort_keys=True)) + "::jsonb"


def build_sql(proposals: Sequence[dict], topic_ids: dict[str, str]) -> str:
    """Render the upsert statements.

    ``ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL`` matches
    the *partial* unique index from migration 149 — without the predicate
    Postgres cannot infer that index and the statement errors.

    ``DO UPDATE`` refreshes only what a re-run can legitimately change, and is
    guarded on the stored row still being ``pending``. It never writes
    ``reviewer_status``, ``reviewed_by`` or ``reviewed_at``: a reviewer's
    verdict outranks a fresh proposal, and a re-run must not quietly reset it.

    Operator note — the table carries a SECOND unique constraint,
    ``unique(question_id, topic_id, tag_role)`` from migration 032. If a
    manually authored tag already claims the same (question, topic, primary)
    triple with a NULL ``idempotency_key``, this INSERT does not match the
    ``idempotency_key`` conflict target and raises a unique violation, aborting
    the transaction. That is the intended direction: an AI proposal must not
    silently displace a human's tag. The operator resolves it by reviewing the
    existing tag, not by widening the conflict target here.
    """
    mapped = [p for p in proposals if p["status"] == STATUS_MAPPED]
    lines = [
        "-- Proposed PYQ microtopic tags. Generated; do not edit by hand.",
        f"-- extractor_version: {EXTRACTOR_VERSION}",
        f"-- rows: {len(mapped)} mapped of {len(proposals)} question(s)",
        f"-- Every row is reviewer_status='{REVIEWER_STATUS}', "
        f"tagging_source='{TAGGING_SOURCE}', source_kind='{SOURCE_KIND}'.",
        "-- Re-running is an upsert on idempotency_key; rows a reviewer has",
        "-- already acted on are left untouched by the DO UPDATE guard.",
        "",
        "begin;",
        "",
    ]
    for p in mapped:
        v = _tag_values(p, topic_ids[p["topic_slug"]])
        if v["reviewer_status"] != "pending":
            raise ProposerError("refusing to emit a non-pending reviewer_status")
        lines.append(
            f"insert into public.{TABLE} (\n"
            "  question_id, topic_id, tag_role, tag_weight, tagging_source,\n"
            "  source_kind, reviewer_status, confidence_score, extractor_version,\n"
            "  idempotency_key, confidence_by_field, metadata\n"
            ") values (\n"
            f"  {_sql_str(v['question_id'])}::uuid,\n"
            f"  {_sql_str(v['topic_id'])}::uuid,\n"
            f"  {_sql_str(v['tag_role'])},\n"
            f"  {v['tag_weight']},\n"
            f"  {_sql_str(v['tagging_source'])},\n"
            f"  {_sql_str(v['source_kind'])},\n"
            f"  {_sql_str(v['reviewer_status'])},\n"
            f"  {v['confidence_score']},\n"
            f"  {_sql_str(v['extractor_version'])},\n"
            f"  {_sql_str(v['idempotency_key'])},\n"
            f"  {_sql_json(v['confidence_by_field'])},\n"
            f"  {_sql_json(v['metadata'])}\n"
            ")\n"
            "on conflict (idempotency_key) where idempotency_key is not null\n"
            "do update set\n"
            "  tag_weight = excluded.tag_weight,\n"
            "  confidence_score = excluded.confidence_score,\n"
            "  confidence_by_field = excluded.confidence_by_field,\n"
            "  metadata = excluded.metadata,\n"
            "  extractor_version = excluded.extractor_version\n"
            f"where public.{TABLE}.reviewer_status = 'pending';"
        )
        lines.append("")
    lines.append("commit;")
    return "\n".join(lines) + "\n"


def write_sql(proposals: Sequence[dict], catalogue: Sequence[dict], path: str) -> int:
    topic_ids = resolve_topic_ids(proposals, catalogue)
    sql = build_sql(proposals, topic_ids)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(sql)
    return sum(1 for p in proposals if p["status"] == STATUS_MAPPED)


# ── cli ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--questions", required=True, help="Exported questions JSONL")
    ap.add_argument("--catalogue", required=True, help="Exported topic catalogue JSONL")
    ap.add_argument("--alias-map", required=True,
                    help="JSON object: printed subject -> catalogue subject slug")
    ap.add_argument("--batch-size", type=int, default=10,
                    help="Questions per model prompt (default 10)")
    ap.add_argument("--out-jsonl", required=True, help="Write the proposal JSONL here")
    ap.add_argument("--out-sql", required=True, help="Write the upsert SQL here")
    ap.add_argument("--dry-run", action="store_true",
                    help="Replay --fixture instead of calling a model. No network, "
                         "no database; the parser and writer run for real.")
    ap.add_argument("--fixture", help="JSON list of raw model responses, for --dry-run")
    ap.add_argument("--live", action="store_true",
                    help=f"Call the provider for real. Requires {API_KEY_ENV} in the "
                         f"environment. Without this and without --dry-run the run "
                         f"still makes no network call.")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help=f"Model id for --live (default {DEFAULT_MODEL})")
    ap.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES,
                    help=f"Retries per batch on rate limits and transient errors "
                         f"(default {DEFAULT_MAX_RETRIES}). A batch still failing "
                         f"after these aborts the run.")
    ap.add_argument("--report", action="store_true", help="Parse summary to stderr")
    args = ap.parse_args(argv)

    if args.dry_run and not args.fixture:
        print("--dry-run requires --fixture", file=sys.stderr)
        return 2
    if args.fixture and not args.dry_run:
        print("--fixture is only meaningful with --dry-run", file=sys.stderr)
        return 2
    if args.live and args.dry_run:
        print("--live and --dry-run are mutually exclusive", file=sys.stderr)
        return 2
    if args.max_retries < 0:
        print("--max-retries cannot be negative", file=sys.stderr)
        return 2

    try:
        alias_map = load_alias_map(args.alias_map)
        catalogue = load_catalogue(args.catalogue)
        questions = load_questions(args.questions, alias_map)
        if args.dry_run:
            client = fixture_client(args.fixture)
        elif args.live:
            # Built before the first batch: a missing key fails here, not
            # halfway through the corpus.
            client = anthropic_client(model=args.model, max_retries=args.max_retries)
        else:
            client = no_client
        proposals = propose(
            questions, catalogue, client=client, batch_size=args.batch_size
        )
        written = write_jsonl(proposals, args.out_jsonl)
        rows = write_sql(proposals, catalogue, args.out_sql)
    except ProposerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.report:
        unmapped = [p for p in proposals if p["status"] == STATUS_UNMAPPED]
        empty = [p for p in proposals if p["candidate_count"] == 0]
        print(f"{len(questions)} question(s), {len(catalogue)} catalogue row(s)",
              file=sys.stderr)
        print(f"  {rows} mapped, {len(unmapped)} unmapped, "
              f"{len(empty)} with no candidates", file=sys.stderr)
        if args.dry_run:
            mode = " (dry run, fixture-driven)"
        elif args.live:
            mode = f" (live, model {args.model})"
        else:
            mode = ""
        print(f"  batch size {args.batch_size}{mode}", file=sys.stderr)

    print(f"wrote {written} proposal(s) to {args.out_jsonl} and {rows} upsert(s) "
          f"to {args.out_sql}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
