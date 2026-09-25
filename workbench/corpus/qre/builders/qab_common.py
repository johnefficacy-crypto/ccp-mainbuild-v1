"""Shared helpers for the QRE-QA-B part modules (quantitative aptitude, batch B)."""
import os as _os, sys
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
from reglib import inr, R, pct, lakh, crore  # noqa: F401
from fractions import Fraction as F  # noqa: F401
import math, itertools  # noqa: F401

REF = "Standard SSC/IBPS/RBI quantitative-aptitude pattern. Original figures; no text reproduced."


def n(x, d=2):
    """Plain number formatting: exact integers without decimals (Indian grouping), else d decimals, trailing zeros stripped."""
    if isinstance(x, F):
        if x.denominator == 1:
            return inr(int(x))
        x = float(x)
    if isinstance(x, int):
        return inr(x)
    if abs(x - round(x)) < 1e-9:
        return inr(int(round(x)))
    s = f"{x:.{d}f}".rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    if abs(x) >= 1000:
        w, _, fr = s.partition(".")
        s = inr(int(w)) + ("." + fr if fr else "")
    return s


def fr(x):
    """Fraction formatting a/b (or integer)."""
    x = F(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def q(B, micro, level, tier, stem, key, cands, steps, formula, trap, fmt=None, unit="",
      kind="numerical", group=None, pre=""):
    """key and each candidate value are formatted via fmt (+unit) unless given as str.
    cands: list of (value, error). The first three that are distinct from the key and
    from each other are used, so extra candidates act as fall-backs."""
    fmt = fmt or n
    f = (lambda v: v if isinstance(v, str) else fmt(v) + unit)
    kt = f(key)
    seen, wr = {kt}, []
    for v, e in cands:
        t = f(v)
        if t in seen:
            continue
        seen.add(t)
        wr.append((t, e))
        if len(wr) == 3:
            break
    assert len(wr) == 3, f"not enough distinct distractors for: {stem[:80]} key={kt} got={wr}"
    return B.add(micro=micro, level=level, stem=pre + stem, correct=kt, wrongs=wr, steps=steps,
                 formula=formula, trap=trap, kind=kind, group=group, ref=REF, tier=tier)


# ---------- relation labels (quadratic comparison / quantity comparison) ----------
XREL = ["x > y", "x < y", "x ≥ y", "x ≤ y", "x = y or no relation"]
QREL = ["I > II", "I < II", "I ≥ II", "I ≤ II", "I = II or no relation"]


def relation(X, Y, labels=XREL):
    P = [(a, b) for a in X for b in Y]
    if all(a == b for a, b in P):
        return labels[4]
    if all(a > b for a, b in P):
        return labels[0]
    if all(a < b for a, b in P):
        return labels[1]
    if all(a >= b for a, b in P):
        return labels[2]
    if all(a <= b for a, b in P):
        return labels[3]
    return labels[4]


def rel_wrongs(X, Y, labels=XREL):
    key = relation(X, Y, labels)
    c = [(relation([-a for a in X], Y, labels), "sign of the roots of I reversed while factorising"),
         (relation(X, [-b for b in Y], labels), "sign of the roots of II reversed while factorising"),
         (relation([max(X)], [max(Y)], labels), "compared only the larger roots"),
         (relation([min(X)], [min(Y)], labels), "compared only the smaller roots")]
    c += [(l, "did not test every root pair") for l in labels]
    return key, [(t, e) for t, e in c if t != key]


def term(c, v, first=False):
    c = F(c)
    if c == 0:
        return ""
    sgn = "−" if c < 0 else "+"
    a = abs(c)
    cs = fr(a) if (a != 1 or not v) else ""
    body = f"{cs}{v}"
    if first:
        return ("−" if c < 0 else "") + body
    return f" {sgn} {body}"


def poly(a, b, c, v="x"):
    return term(a, v + "²", True) + term(b, v) + term(c, "") + " = 0"


def quad_from_roots(r1, r2):
    r1, r2 = F(r1), F(r2)
    q1, p1, q2, p2 = r1.denominator, r1.numerator, r2.denominator, r2.numerator
    a, b, c = q1 * q2, -(q1 * p2 + q2 * p1), p1 * p2
    g = math.gcd(math.gcd(a, abs(b)), abs(c))
    return a // g, b // g, c // g


def roots(a, b, c):
    D = b * b - 4 * a * c
    s = math.isqrt(D)
    assert s * s == D, "non-rational roots"
    return sorted({F(-b + s, 2 * a), F(-b - s, 2 * a)})


# ---------- data sufficiency ----------
DS = {
    "I": "I alone is sufficient; II alone is not",
    "II": "II alone is sufficient; I alone is not",
    "E": "Either I or II alone is sufficient",
    "B": "Both I and II together are needed",
    "N": "Even I and II together are insufficient",
}
DS_ERR = {
    "I": "overlooked what statement II adds / over-read statement I",
    "II": "overlooked what statement I adds / over-read statement II",
    "E": "treated a partially informative statement as sufficient on its own",
    "B": "missed that one statement already fixes the answer",
    "N": "missed that the statements combine to a unique answer",
}


def ds_eval(domain, base, s1, s2, target):
    """domain: iterable of tuples; base/s1/s2: predicates; target: function -> value.
    Returns DS key by exhaustive enumeration."""
    sols = [t for t in domain if base(t)]
    def uniq(pred):
        vals = {target(t) for t in sols if pred(t)}
        assert vals, "statement set is inconsistent (no solution)"
        return len(vals) == 1
    a, b = uniq(s1), uniq(s2)
    if a and b:
        return "E"
    if a:
        return "I"
    if b:
        return "II"
    return "B" if uniq(lambda t: s1(t) and s2(t)) else "N"


def ds_q(B, micro, level, tier, stem, key, steps, trap, group=None):
    wr = [(DS[k], DS_ERR[k]) for k in DS if k != key]
    # keep the three most tempting: drop the one farthest from the key
    drop = {"I": "N", "II": "N", "E": "N", "B": "E", "N": "E"}[key]
    wr = [w for w in wr if w[0] != DS[drop]]
    return B.add(micro=micro, level=level, stem=stem, correct=DS[key], wrongs=wr, steps=steps,
                 formula="Data sufficiency: test each statement alone, then together", trap=trap,
                 kind="case" if group else "conceptual", group=group, ref=REF, tier=tier)


def table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def closest_ok(key, options, actual):
    """Assert that key is the option closest to the actual value (approximation questions)."""
    best = min(options, key=lambda o: abs(o - actual))
    assert best == key, (key, options, actual)
