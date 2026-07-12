"""Calculation Gym — deterministic, seeded, no-LLM retrieval sub-runtime (GQR-Q8).

The server owns the range, random seed, generation, expected answers, and session
limits (§3.2). A session's ``seed`` and generated items are frozen at creation so
the whole session is reproducible: identical ``(skill, seed, count,
policy_version)`` always regenerates identical items and answers.

This module is pure generation + a thin session persistence layer taking
``supabase``; the learner-runtime API wiring (subject_practice dispatch) is a
later slice and is intentionally NOT touched here.
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from math import gcd
from typing import Any, Callable

logger = logging.getLogger("career_copilot.study_os.calc_gym")

# Bump when the generation rules change; frozen onto every session so a session
# is reproducible against the exact generator that made it.
GENERATOR_VERSION = "cgg_v1"

_SESSIONS = "calc_gym_sessions"
_ITEMS = "calc_gym_session_items"

SKILLS = (
    "tables", "squares", "cubes", "square_roots", "cube_roots",
    "fraction_percent", "ratio_simplify", "approximation", "multiplication_patterns",
)

# Curated fraction → percent pairs (exact terminating percents only, so scoring
# is an exact string match).
_FRACTION_PERCENT = [
    (1, 2, "50%"), (1, 4, "25%"), (3, 4, "75%"), (1, 5, "20%"), (2, 5, "40%"),
    (3, 5, "60%"), (4, 5, "80%"), (1, 10, "10%"), (1, 8, "12.5%"), (3, 8, "37.5%"),
    (1, 20, "5%"), (1, 25, "4%"), (1, 50, "2%"),
]

_MULT_PATTERNS = [5, 9, 11, 25, 99]


def _norm(answer: str) -> str:
    """Canonical form for exact-match scoring: strip, lowercase, drop spaces."""
    return (answer or "").strip().lower().replace(" ", "")


def _one_item(skill: str, rng: random.Random) -> dict[str, Any]:
    """Generate a single frozen item ``{prompt, expected_answer, operands}``."""
    if skill == "tables":
        a, b = rng.randint(2, 20), rng.randint(2, 20)
        return {"prompt": f"{a} × {b}", "expected_answer": str(a * b),
                "operands": {"a": a, "b": b, "op": "mul"}}
    if skill == "squares":
        n = rng.randint(2, 40)
        return {"prompt": f"{n}²", "expected_answer": str(n * n), "operands": {"n": n}}
    if skill == "cubes":
        n = rng.randint(2, 25)
        return {"prompt": f"{n}³", "expected_answer": str(n ** 3), "operands": {"n": n}}
    if skill == "square_roots":
        n = rng.randint(2, 40)
        return {"prompt": f"√{n * n}", "expected_answer": str(n), "operands": {"n": n, "radicand": n * n}}
    if skill == "cube_roots":
        n = rng.randint(2, 20)
        return {"prompt": f"∛{n ** 3}", "expected_answer": str(n), "operands": {"n": n, "radicand": n ** 3}}
    if skill == "fraction_percent":
        num, den, pct = rng.choice(_FRACTION_PERCENT)
        return {"prompt": f"{num}/{den} as %", "expected_answer": pct,
                "operands": {"num": num, "den": den}}
    if skill == "ratio_simplify":
        a, b = rng.randint(1, 12), rng.randint(1, 12)
        k = rng.randint(2, 9)
        g = gcd(a, b)
        return {"prompt": f"{a * k}:{b * k}", "expected_answer": f"{a // g}:{b // g}",
                "operands": {"a": a * k, "b": b * k}}
    if skill == "approximation":
        a, b = rng.randint(80, 999), rng.randint(11, 99)
        approx = round(a * b, -2)
        return {"prompt": f"{a} × {b} (nearest 100)", "expected_answer": str(approx),
                "operands": {"a": a, "b": b, "round_to": 100}}
    if skill == "multiplication_patterns":
        a = rng.randint(12, 99)
        m = rng.choice(_MULT_PATTERNS)
        return {"prompt": f"{a} × {m}", "expected_answer": str(a * m),
                "operands": {"a": a, "b": m, "op": "mul"}}
    raise ValueError(f"unknown calc-gym skill: {skill!r}")


def generate_items(skill: str, count: int, seed: int) -> list[dict[str, Any]]:
    """Deterministically generate ``count`` frozen items for ``skill``.

    Same ``(skill, count, seed)`` → byte-identical items, so a session can be
    replayed/audited from its stored seed alone.
    """
    if skill not in SKILLS:
        raise ValueError(f"unknown calc-gym skill: {skill!r}")
    if count <= 0:
        return []
    rng = random.Random(seed)
    return [{**_one_item(skill, rng), "item_index": i} for i in range(count)]


def _new_seed() -> int:
    # Server-owned seed. SystemRandom so sessions aren't predictable across users;
    # the value is then frozen on the row for reproducibility.
    return random.SystemRandom().getrandbits(63)


def create_session(
    supabase: Any,
    *,
    user_id: str,
    skill: str,
    question_count: int,
    duration_sec: int,
    exam_id: str | None = None,
    seed: int | None = None,
    now: datetime | None = None,
    policy_version: str = GENERATOR_VERSION,
) -> dict[str, Any]:
    """Create a frozen gym session and its items. Returns the session plus the
    learner-facing items (prompt only — expected answers stay server-side)."""
    if skill not in SKILLS:
        raise ValueError(f"unknown calc-gym skill: {skill!r}")
    now = now or datetime.now(timezone.utc)
    seed = _new_seed() if seed is None else seed
    items = generate_items(skill, question_count, seed)

    session_rows = supabase.table(_SESSIONS).insert({
        "user_id": user_id,
        "exam_id": exam_id,
        "skill": skill,
        "question_count": question_count,
        "duration_sec": duration_sec,
        "seed": seed,
        "policy_version": policy_version,
        "status": "in_progress",
        "started_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=duration_sec)).isoformat(),
    }).execute()
    session = (getattr(session_rows, "data", None) or [None])[0]
    if not session:
        raise RuntimeError("calc_gym.create_session: session insert returned no row")
    session_id = session["id"]

    # Atomic cascade (AGENTS.md "PR7-style"): a session must never survive with
    # zero/partial frozen items. If the child insert fails, roll the parent back
    # so no orphan in_progress session remains.
    try:
        item_rows = supabase.table(_ITEMS).insert([
            {
                "session_id": session_id,
                "item_index": it["item_index"],
                "prompt": it["prompt"],
                "expected_answer": it["expected_answer"],
                "operands": it["operands"],
            }
            for it in items
        ]).execute()
        inserted = getattr(item_rows, "data", None) or []
        if len(inserted) != len(items):
            raise RuntimeError(
                f"calc_gym.create_session: froze {len(inserted)}/{len(items)} items"
            )
    except Exception:
        _safe_delete_session(supabase, session_id)
        raise

    return {
        "session_id": session_id,
        "skill": skill,
        "question_count": question_count,
        "duration_sec": duration_sec,
        "expires_at": session["expires_at"],
        "policy_version": policy_version,
        # Learner-facing: prompt + index only, never the frozen expected_answer.
        "items": [{"item_index": it["item_index"], "prompt": it["prompt"]} for it in items],
    }


def _safe_delete_session(supabase: Any, session_id: str) -> None:
    try:
        supabase.table(_SESSIONS).delete().eq("id", session_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("calc_gym rollback delete failed session=%s err=%r", session_id, exc)


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _stored_result(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": session["id"],
        "status": session.get("status"),
        "score_correct": session.get("score_correct"),
        "score_total": session.get("score_total"),
        "total_time_sec": session.get("total_time_sec"),
        "idempotent": True,
    }


def submit_session(
    supabase: Any,
    *,
    session_id: str,
    user_id: str,
    answers: dict[int, dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Score a session against its FROZEN expected answers and finalize it.

    Server-enforced (the row's ``duration_sec`` / ``expires_at`` are authoritative,
    not decorative):
      - **ownership** — the fetch is scoped to ``user_id``; another user's session
        is not found.
      - **state** — only an ``in_progress`` session can be scored; ``submitted``
        returns the stored result idempotently; any other state fails closed.
      - **deadline** — a submission after ``expires_at`` is rejected and the
        session is flipped to ``expired`` (never scored late).
      - **concurrency** — the finalize is a CAS update guarded on
        ``status='in_progress'``; a losing concurrent submit re-reads and returns
        the winner's result rather than double-scoring.

    ``answers`` maps ``item_index -> {"user_answer": str, "time_spent_sec": int}``.
    """
    now = now or datetime.now(timezone.utc)
    sess_rows = (
        supabase.table(_SESSIONS).select("*")
        .eq("id", session_id).eq("user_id", user_id).limit(1).execute()
    )
    session = (getattr(sess_rows, "data", None) or [None])[0]
    if not session:
        # Covers both "no such session" and "not owned by this user".
        raise LookupError(f"calc_gym session {session_id} not found for user")

    status = session.get("status")
    if status == "submitted":
        return _stored_result(session)
    if status != "in_progress":
        raise ValueError(f"calc_gym session {session_id} is not in progress (status={status})")

    expires = _parse_ts(session.get("expires_at"))
    if expires is not None and now > expires:
        # Reject late submission and flip in_progress → expired (CAS-guarded so a
        # concurrent on-time submit that already won is not clobbered).
        supabase.table(_SESSIONS).update({"status": "expired"}) \
            .eq("id", session_id).eq("status", "in_progress").execute()
        raise ValueError(f"calc_gym session {session_id} has expired")

    item_rows = supabase.table(_ITEMS).select("*").eq("session_id", session_id).execute()
    items = getattr(item_rows, "data", None) or []

    # Scoring is read-only against the frozen expected answers, so it is safe to
    # compute before claiming the session with the CAS flip below.
    correct = 0
    total_time = 0
    scored: list[dict[str, Any]] = []
    for it in items:
        submitted = answers.get(it["item_index"]) or answers.get(str(it["item_index"])) or {}
        user_answer = submitted.get("user_answer")
        time_spent = int(submitted.get("time_spent_sec") or 0)
        is_correct = user_answer is not None and _norm(str(user_answer)) == _norm(it["expected_answer"])
        if is_correct:
            correct += 1
        total_time += time_spent
        scored.append({"id": it["id"], "user_answer": user_answer,
                       "is_correct": is_correct, "time_spent": time_spent})

    total = len(items)
    # CAS claim: only the submit that flips in_progress → submitted writes scores.
    claim = supabase.table(_SESSIONS).update({
        "status": "submitted",
        "submitted_at": now.isoformat(),
        "score_correct": correct,
        "score_total": total,
        "total_time_sec": total_time,
    }).eq("id", session_id).eq("status", "in_progress").execute()
    if not (getattr(claim, "data", None) or []):
        # Lost the race (or state changed under us): return the winner's result.
        latest = (
            getattr(
                supabase.table(_SESSIONS).select("*").eq("id", session_id).limit(1).execute(),
                "data", None,
            ) or [session]
        )[0]
        return _stored_result(latest)

    # We own the finalize — persist the per-item results.
    for s in scored:
        supabase.table(_ITEMS).update({
            "user_answer": s["user_answer"],
            "is_correct": s["is_correct"],
            "time_spent_sec": s["time_spent"],
            "answered_at": now.isoformat() if s["user_answer"] is not None else None,
        }).eq("id", s["id"]).execute()

    return {
        "session_id": session_id,
        "status": "submitted",
        "score_correct": correct,
        "score_total": total,
        "total_time_sec": total_time,
        "idempotent": False,
    }
