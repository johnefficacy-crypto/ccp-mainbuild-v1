"""Shared numeric helpers for REG-CORPUS-FIN-A part modules."""
import math


def bond_price(face, cpn, y, years, freq=1):
    """Price on a coupon date. cpn, y are annual rates; years * freq periods."""
    n = int(round(years * freq))
    c = face * cpn / freq
    r = y / freq
    return sum(c / (1 + r) ** t for t in range(1, n + 1)) + face / (1 + r) ** n


def solve(f, lo, hi, tol=1e-12):
    """Bisection root of monotone f on [lo, hi]."""
    flo = f(lo)
    for _ in range(300):
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def ytm(price, face, cpn, years, freq=1, redemption=None):
    red = face if redemption is None else redemption
    n = int(round(years * freq))
    c = face * cpn / freq

    def f(y):
        r = y / freq
        return sum(c / (1 + r) ** t for t in range(1, n + 1)) + red / (1 + r) ** n - price
    return solve(f, -0.5, 1.0)


def mac_duration(face, cpn, y, years, freq=1):
    n = int(round(years * freq))
    c = face * cpn / freq
    r = y / freq
    cfs = [(t, c + (face if t == n else 0)) for t in range(1, n + 1)]
    p = sum(cf / (1 + r) ** t for t, cf in cfs)
    return sum(t * cf / (1 + r) ** t for t, cf in cfs) / p / freq  # in years


def table(header, rows, align=None):
    """GFM table. header: list, rows: list of lists (already formatted strings)."""
    align = align or ["---"] + ["---:"] * (len(header) - 1)
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def f2(x, d=2):
    return f"{x:,.{d}f}"
