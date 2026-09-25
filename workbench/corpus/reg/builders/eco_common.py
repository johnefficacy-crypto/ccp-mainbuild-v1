"""Shared helpers for the REG-CORPUS-ECO part modules."""
import sys
sys.path.insert(0, '/home/claude/corpus')
from reglib import inr, R, pct  # noqa: F401


def slug(B, key):
    m = [s for s in B.cat if s.startswith("econ-" + key)]
    assert len(m) == 1, f"slug key {key!r} matched {m}"
    return m[0]


def mk(B):
    def q(key, level, stem, correct, wrongs, steps, formula, trap, **kw):
        return B.add(micro=slug(B, key), level=level, stem=stem, correct=correct,
                     wrongs=wrongs, steps=steps, formula=formula, trap=trap, **kw)
    return q


def cr(x, d=0):
    """Rupee crore amount."""
    return ("−" if x < 0 else "") + f"₹{inr(abs(x), d)} crore"


def n(x, d=2):
    """Plain number with fixed decimals, trailing zeros trimmed."""
    s = f"{x:,.{d}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def tbl(header, rows, right=None):
    """Markdown table. right: set of column indexes to right-align (default: all but first)."""
    k = len(header)
    right = set(range(1, k)) if right is None else right
    al = ["---:" if i in right else "---" for i in range(k)]
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(al) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def items(rows, unit="₹ crore"):
    """Two-column item table with amounts formatted Indian style."""
    return tbl(["Item", unit], [(a, (inr(b).replace("-", "−") if isinstance(b, (int, float)) else b)) for a, b in rows])


def stmts(lines):
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(lines))
