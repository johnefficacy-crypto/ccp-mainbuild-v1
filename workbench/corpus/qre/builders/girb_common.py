"""Shared helpers for the QRE-GIR-B part modules (general intelligence & reasoning, batch B)."""
import os as _os, sys
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
from reglib import inr  # noqa: F401
import itertools, random, math, string  # noqa: F401

REF = "Standard SSC/IBPS/RBI reasoning pattern. Original items; key verified by the solver in the builder; no text reproduced."
AL = string.ascii_uppercase


def L(i):
    """1-based alphabet position -> letter, with wraparound."""
    return AL[(i - 1) % 26]


def P(c):
    return AL.index(c.upper()) + 1


def fmt(v):
    if isinstance(v, float):
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


def q(B, micro, level, tier, stem, key, cands, steps, formula, trap, kind="numerical", group=None, pre=""):
    """cands: list of (value, error). First three distinct from key and each other are used."""
    kt = fmt(key)
    seen, wr = {kt}, []
    for v, e in cands:
        t = fmt(v)
        if t in seen:
            continue
        seen.add(t)
        wr.append((t, e))
        if len(wr) == 3:
            break
    assert len(wr) == 3, f"not enough distinct distractors for: {stem[:80]} key={kt} got={wr}"
    return B.add(micro=micro, level=level, stem=pre + stem, correct=kt, wrongs=wr, steps=steps,
                 formula=formula, trap=trap, kind=kind, group=group, ref=REF, tier=tier)


def numd(key, errs):
    """numeric distractor candidates with standard fall-backs."""
    return list(errs) + [(key + 1, "arithmetic slip (+1)"), (key - 1, "arithmetic slip (−1)"),
                         (key + 2, "arithmetic slip (+2)"), (key - 2, "arithmetic slip (−2)")]
