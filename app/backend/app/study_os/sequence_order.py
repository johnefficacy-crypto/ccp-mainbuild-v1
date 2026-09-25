"""Signed sequence answers for ordering PYQs (parajumbles, Logical Order).

The corpus stores a parajumble as a 4-option MCQ: ``pyq_options`` carries the
correct OPTION ("B A D C"), never the correct ORDER as data. A drag-to-reorder
drill therefore has nothing to grade against unless the order is written down
and reviewed. ``scripts/backfill_sequence_order.py`` derives it offline, puts
every derivation on a review worksheet, and on ``--apply --confirm`` writes the
reviewed record to ``pyq_questions.metadata.correct_order``.

This module is the runtime side of that contract and deliberately does NO
parsing of question text or option text. It only accepts a record that:

  * is ``verified`` and carries a ``digest`` that matches its own content
    (a hand-edited or half-written record is refused, not trusted),
  * names segment labels, a correct order and a per-option order that are all
    permutations of the same label set, with no two options naming one order,
  * agrees with the answer key actually frozen into the attempt: the bank's
    correct option must be the record's ``correct_pyq_option_id`` and its order
    must equal ``order``.

Anything else yields ``None`` and the question renders as a plain MCQ — the
learner never sees an order marked right that the answer key does not back.

Stdlib only: the backfill script loads this file by path so the digest is
computed by exactly one implementation on both sides.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

METADATA_KEY = "correct_order"
RECORD_VERSION = 1
MIN_SEGMENTS = 2


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sequence_digest(
    *,
    pyq_question_id: str,
    order: list[str],
    segments: list[dict],
    lead: str,
    tail: str,
    option_orders: dict[str, list[str]],
    correct_pyq_option_id: str,
) -> str:
    """Digest binding a reviewed order to the question, its segments and its key."""
    body = {
        "pyq_question_id": str(pyq_question_id),
        "order": list(order),
        "segments": [{"label": s["label"], "text": s["text"]} for s in segments],
        "lead": lead or "",
        "tail": tail or "",
        "option_orders": {str(k): list(v) for k, v in option_orders.items()},
        "correct_pyq_option_id": str(correct_pyq_option_id),
    }
    return "sha256:" + hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def record_digest(record: dict, pyq_question_id: str) -> str:
    return sequence_digest(
        pyq_question_id=pyq_question_id,
        order=record.get("order") or [],
        segments=record.get("segments") or [],
        lead=record.get("lead") or "",
        tail=record.get("tail") or "",
        option_orders=record.get("option_orders") or {},
        correct_pyq_option_id=record.get("correct_pyq_option_id") or "",
    )


def _is_permutation(seq: Any, labels: list[str]) -> bool:
    return isinstance(seq, list) and len(seq) == len(labels) and sorted(seq) == sorted(labels)


def validate_record(record: Any, pyq_question_id: str | None) -> bool:
    """True only for a complete, verified, self-consistent, untampered record."""
    if not isinstance(record, dict) or not pyq_question_id:
        return False
    if record.get("version") != RECORD_VERSION or record.get("verified") is not True:
        return False
    segments = record.get("segments")
    order = record.get("order")
    option_orders = record.get("option_orders")
    correct_pyq = record.get("correct_pyq_option_id")
    if not isinstance(segments, list) or len(segments) < MIN_SEGMENTS:
        return False
    if not all(isinstance(s, dict) and isinstance(s.get("label"), str) and isinstance(s.get("text"), str)
               and s["label"] and s["text"].strip() for s in segments):
        return False
    labels = [s["label"] for s in segments]
    if len(set(labels)) != len(labels):
        return False
    if not _is_permutation(order, labels):
        return False
    if not isinstance(option_orders, dict) or not option_orders or not correct_pyq:
        return False
    if not all(_is_permutation(v, labels) for v in option_orders.values()):
        return False
    # Two options naming the same order would make a learner's arrangement
    # ambiguous to submit — refuse rather than guess which one they meant.
    if len({tuple(v) for v in option_orders.values()}) != len(option_orders):
        return False
    if option_orders.get(str(correct_pyq)) != order:
        return False
    return record.get("digest") == record_digest(record, str(pyq_question_id))


def freeze_sequence(
    record: Any,
    *,
    pyq_question_id: str | None,
    options: list[dict],
    correct_option_id: str | None,
) -> dict | None:
    """Sequence block frozen into ``question_snapshot`` — or None (plain MCQ).

    ``options`` are the BANK options being frozen (each carries the projected
    ``pyq_option_id``, migration 307). Per-option orders are re-keyed from pyq
    option ids to bank option ids so the attempt API never needs pyq lineage to
    submit an arrangement as the matching option.
    """
    if not validate_record(record, pyq_question_id):
        return None
    option_orders = record["option_orders"]
    by_bank_id: dict[str, list[str]] = {}
    for o in options or []:
        pyq_opt = o.get("pyq_option_id")
        if not pyq_opt or str(pyq_opt) not in option_orders:
            # An option the reviewed record never saw (re-keyed, re-projected,
            # or pre-307 without lineage): the mapping is no longer the one a
            # human signed, so drop to MCQ.
            return None
        by_bank_id[str(o["id"])] = list(option_orders[str(pyq_opt)])
    if len(by_bank_id) != len(option_orders):
        return None
    correct = next((o for o in options if str(o.get("id")) == str(correct_option_id)), None)
    if correct is None or str(correct.get("pyq_option_id")) != str(record["correct_pyq_option_id"]):
        # The answer key moved after review. The key wins; the order is stale.
        return None
    return {
        "lead": record.get("lead") or "",
        "tail": record.get("tail") or "",
        "segments": [{"label": s["label"], "text": s["text"]} for s in record["segments"]],
        "option_orders": by_bank_id,
        "correct_order": list(record["order"]),
    }


def public_sequence(frozen: Any) -> dict | None:
    """The pre-submit view: segments and per-option orders, never the answer.

    Per-option orders restate option text the learner already sees, so they
    reveal nothing; ``correct_order`` stays in the snapshot until review.
    """
    if not isinstance(frozen, dict) or not frozen.get("segments"):
        return None
    return {
        "lead": frozen.get("lead") or "",
        "tail": frozen.get("tail") or "",
        "segments": frozen.get("segments") or [],
        "option_orders": frozen.get("option_orders") or {},
    }
