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
        product = a * b
        # Explicit half-up to nearest 100 (aptitude convention). Python's built-in
        # round(x, -2) uses banker's rounding (ties-to-even), so e.g. 11050 → 11000
        # instead of the expected 11100.
        approx = ((product + 50) // 100) * 100
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
    """Create a frozen gym session and its items ATOMICALLY (single-transaction
    RPC — no orphan/partial session can survive a child-insert failure). Returns
    the session plus the learner-facing items (prompt only — expected answers
    stay server-side)."""
    if skill not in SKILLS:
        raise ValueError(f"unknown calc-gym skill: {skill!r}")
    now = now or datetime.now(timezone.utc)
    seed = _new_seed() if seed is None else seed
    items = generate_items(skill, question_count, seed)

    res = supabase.rpc("create_calc_gym_session", {
        "p_user_id": user_id,
        "p_exam_id": exam_id,
        "p_skill": skill,
        "p_question_count": question_count,
        "p_duration_sec": duration_sec,
        "p_seed": seed,
        "p_policy_version": policy_version,
        "p_items": items,
        "p_now": now.isoformat(),
    }).execute()
    session_id = getattr(res, "data", None)
    if isinstance(session_id, dict):
        session_id = session_id.get("id") or session_id.get("create_calc_gym_session")
    if not session_id:
        raise RuntimeError("calc_gym.create_session: RPC returned no session id")

    return {
        "session_id": session_id,
        "skill": skill,
        "question_count": question_count,
        "duration_sec": duration_sec,
        "expires_at": (now + timedelta(seconds=duration_sec)).isoformat(),
        "policy_version": policy_version,
        # Learner-facing: prompt + index only, never the frozen expected_answer.
        "items": [{"item_index": it["item_index"], "prompt": it["prompt"]} for it in items],
    }


# Map the RPC's structured error codes/messages to typed Python exceptions so
# callers surface the right status regardless of the DB driver's error class.
def _raise_typed(exc: Exception) -> None:
    msg = str(exc)
    if "not_found" in msg:
        raise LookupError(msg) from exc
    if any(tag in msg for tag in ("expired", "not_in_progress", "missing_user")):
        raise ValueError(msg) from exc
    raise exc


def submit_session(
    supabase: Any,
    *,
    session_id: str,
    user_id: str,
    answers: dict[int, dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Score a session and finalize it via the ATOMIC ``submit_calc_gym_session``
    RPC (single transaction: locks the owned session, enforces state + deadline,
    clamps client timing, and writes every item result plus the aggregate — all
    or nothing).

    Server-enforced by the RPC: ownership (another user's session → not found),
    state (``submitted`` → idempotent, any non-``in_progress`` → fail closed),
    deadline (late submit → ``expired``, never scored), and single-writer
    finalize under the row lock. ``answers`` maps ``item_index ->
    {"user_answer": str, "time_spent_sec": int}`` (keys are stringified for JSON).
    """
    now = now or datetime.now(timezone.utc)
    answers_json = {str(k): v for k, v in (answers or {}).items()}
    try:
        res = supabase.rpc("submit_calc_gym_session", {
            "p_session_id": session_id,
            "p_user_id": user_id,
            "p_answers": answers_json,
            "p_now": now.isoformat(),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        _raise_typed(exc)
    return getattr(res, "data", None) or {}
