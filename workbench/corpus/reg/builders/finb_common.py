"""Shared helpers for REG-CORPUS-FIN-B part modules."""
import os as _os; _REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, csv, os
sys.path.insert(0, _REG)
from reglib import inr, R, pct, lakh, crore  # noqa: F401

_LIST = _os.path.join(_REG, 'lists', 'finance.B.tsv')
SLUGS = [r['slug'] for r in csv.DictReader(open(_LIST, encoding='utf-8'), delimiter='\t')]


def M(key):
    """Resolve a short key (unique substring) to the full finance.B slug."""
    hits = [s for s in SLUGS if key in s]
    assert len(hits) == 1, f"slug key {key!r} -> {hits}"
    return hits[0]


def statements(items):
    """items: list of statement texts. Returns markdown numbered list."""
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(items))


def combo_text(sel, n):
    sel = sorted(sel)
    if not sel:
        return "None of the statements" if n > 1 else "Neither"
    if len(sel) == n:
        return "All of " + (", ".join(str(i) for i in range(1, n)) + f" and {n}") if n > 2 else "Both 1 and 2"
    if len(sel) == 1:
        return f"{sel[0]} only"
    return ", ".join(str(i) for i in sel[:-1]) + f" and {sel[-1]} only"


def stmt_opts(truth, why, flips=None):
    """truth: list of bools; why: list of reasons (why each statement is true/false).
    Returns (correct_text, wrongs) where each wrong flips exactly one statement's verdict.
    flips: optional list of statement indices (0-based) to flip; default first 3."""
    n = len(truth)
    corr = {i + 1 for i, t in enumerate(truth) if t}
    idx = flips if flips is not None else list(range(n))[:3]
    wrongs = []
    for i in idx:
        s = set(corr) ^ {i + 1}
        err = (f"wrongly accepts statement {i+1}: {why[i]}" if not truth[i]
               else f"wrongly rejects statement {i+1}: {why[i]}")
        wrongs.append((combo_text(s, n), err))
    return combo_text(corr, n), wrongs


AR = ["Both A and R are true, and R is the correct explanation of A",
      "Both A and R are true, but R is not the correct explanation of A",
      "A is true, but R is false",
      "A is false, but R is true"]


def ar_opts(key, errs):
    """key: 0..3 index into AR; errs: dict idx->error label for the other three."""
    wr = [(AR[i], errs[i]) for i in range(4) if i != key]
    assert len(wr) == 3
    return AR[key], wr


def ar_stem(a, r):
    return (f"**Assertion (A):** {a}\n\n**Reason (R):** {r}\n\nChoose the correct option.")


def table(header, rows, align=None):
    align = align or ["---"] + ["---:"] * (len(header) - 1)
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def f2(x, d=2):
    return f"{x:,.{d}f}"


def irr(cfs, lo=-0.99, hi=1.0):
    def npv(r):
        return sum(c / (1 + r) ** t for t, c in enumerate(cfs))
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2
