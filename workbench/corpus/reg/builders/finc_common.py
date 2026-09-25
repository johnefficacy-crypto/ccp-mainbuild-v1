"""Shared helpers for REG-CORPUS-FIN-C part modules (repo-relative imports only)."""
import os as _os, sys, csv
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
from reglib import inr, pct, lakh, crore  # noqa: F401,E402
from reglib import R as _R  # noqa: E402


def R(n, dec=0):
    """₹ amount with a proper leading minus sign for negatives (−₹18,700)."""
    return ("−" if n < 0 else "") + _R(abs(n), dec)

_LIST = _os.path.join(_REG, "lists", "finance.C.tsv")
SLUGS = [r["slug"] for r in csv.DictReader(open(_LIST, encoding="utf-8"), delimiter="\t")]
TAX_SLUGS = ["fin-income-tax-assessment-and-rectification-15ac02be",
             "fin-income-tax-penalties-and-pan-provisions-1532a8d7",
             "fin-direct-vs-indirect-taxes-66414170"]
PAT = "Standard ICAI/ICMAI Financial Management pattern. Original figures and entities; no text reproduced."
TAXREF = "Income-tax Act, 2025 (w.e.f. 1 April 2026) — verify against official text"


def M(key):
    hits = [s for s in SLUGS + TAX_SLUGS if key in s]
    assert len(hits) == 1, f"slug key {key!r} -> {hits}"
    return hits[0]


def table(header, rows, align=None):
    align = align or ["---"] + ["---:"] * (len(header) - 1)
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def statements(items):
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(items))


def combo_text(sel, n):
    sel = sorted(sel)
    if not sel:
        return "None of the statements"
    if len(sel) == n:
        return "All of " + ", ".join(str(i) for i in range(1, n)) + f" and {n}" if n > 2 else "Both 1 and 2"
    if len(sel) == 1:
        return f"{sel[0]} only"
    return ", ".join(str(i) for i in sel[:-1]) + f" and {sel[-1]} only"


def stmt_opts(truth, why, flips=None):
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


def pvf(r, n):
    """Present value factor rounded to 3 decimals (table convention)."""
    return round(1 / (1 + r) ** n, 3)


def pvaf(r, n):
    return round((1 - (1 + r) ** -n) / r, 3)


def irr(cfs, lo=-0.9, hi=1.5):
    def f(r):
        return sum(c / (1 + r) ** t for t, c in enumerate(cfs))
    assert f(lo) * f(hi) < 0
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def L(x, d=2):
    """Amount in ₹ lakh given x in lakh."""
    return ("−" if x < 0 else "") + f"₹{abs(x):,.{d}f} lakh"


def f2(x, d=2):
    return f"{x:,.{d}f}"


def yrs(x, d=2):
    return f"{x:.{d}f} years"
