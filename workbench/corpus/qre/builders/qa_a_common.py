"""Shared helpers for QRE-QA-A part modules (formatting + slug map)."""
from fractions import Fraction as Fr
import math
import os as _os, sys
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _REG not in sys.path:
    sys.path.insert(0, _REG)
from reglib import inr  # noqa: E402

SLUG = {
    "ies": "qa-income-expenditure-and-savings-20025343",
    "pcmp": "qa-percentage-comparison-what-percent-of-more-than-b5ef5d48",
    "pid": "qa-percentage-increase-and-decrease-85f661e1",
    "pop": "qa-population-strength-and-quantity-change-e737e151",
    "spc": "qa-successive-percentage-change-8a4031e7",
    "comb": "qa-combined-transactions-and-overall-gain-229905cb",
    "cpsp": "qa-cost-price-selling-price-and-margin-fa9cf244",
    "disc": "qa-discount-and-marked-price-feadd5c6",
    "eqpl": "qa-equal-profit-and-loss-conditions-cdaceb4b",
    "sici": "qa-simple-and-compound-interest-ee6f76e4",
    "ages": "qa-ages-present-past-and-future-0a8b95a2",
    "avg": "qa-averages-simple-and-weighted-1f479970",
    "med": "qa-median-and-mode-9fcb6443",
    "mix": "qa-mixtures-and-alligation-921971ac",
    "part": "qa-partnership-and-profit-sharing-055fa70d",
    "prop": "qa-proportional-division-of-quantities-14622c51",
    "sratio": "qa-simple-and-compound-ratio-ae9a2833",
    "avgspd": "qa-average-speed-and-journey-segments-5db28484",
    "boat": "qa-boats-and-streams-652dae37",
    "race": "qa-races-and-circular-tracks-ee936ee3",
    "rel": "qa-relative-speed-and-meeting-problems-4f10cb81",
    "trn": "qa-trains-crossing-platforms-and-each-other-fbf3e1f2",
    "eff": "qa-efficiency-comparison-and-relative-capacity-7ef5386a",
    "indiv": "qa-individual-and-combined-work-rates-f1d3f896",
    "partial": "qa-partial-work-and-remaining-work-problems-3868d723",
    "pipes": "qa-pipes-and-cisterns-567ce8e0",
}

TIER = {"f": "foundation", "o": "officer"}


def _fr(x):
    if isinstance(x, float):
        return Fr(x).limit_denominator(100000)
    return Fr(x)


def _terminating2(f):
    """True if f has at most 2 decimal places exactly."""
    return (f * 100).denominator == 1


def N(x):
    """Plain number: integer with Indian commas, exact <=2dp decimals, mixed fraction for small
    non-terminating denominators (thirds, sevenths...), else 2 dp."""
    if isinstance(x, str):
        return x
    f = _fr(x)
    neg = f < 0
    f = abs(f)
    if f.denominator == 1:
        s = inr(int(f))
    elif _terminating2(f):
        s = inr(float(f), 2)
        if s.endswith("0") and "." in s:
            s = s[:-1]
    elif f.denominator <= 12:
        w = f.numerator // f.denominator
        r = f - w
        s = (f"{inr(w)} " if w else "") + f"{r.numerator}/{r.denominator}"
    else:
        s = inr(float(f), 2)
    return ("−" if neg else "") + s


def D(x, d=2):
    """Always decimal (d places), trailing zeros kept only as needed."""
    f = _fr(x)
    if f.denominator == 1:
        return inr(int(f)) if f >= 0 else "−" + inr(int(-f))
    s = inr(abs(float(f)), d)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return ("−" if f < 0 else "") + s


def P(x):
    """Percentage given as a number of percent (e.g. 12.5 -> '12.5%')."""
    return N(x) + "%"


def Rs(x):
    """Money: integers with commas, otherwise exactly 2 decimals."""
    if isinstance(x, str):
        s = x
        if "." in s and len(s.split(".")[1]) == 1:
            s += "0"
        return "₹" + s
    f = _fr(x)
    if f.denominator == 1:
        return "₹" + (inr(int(f)) if f >= 0 else "−" + inr(int(-f)))
    return "₹" + inr(float(f), 2)


def RsD(x):
    return Rs(x)


def ratio(a, b, *more):
    vals = [_fr(v) for v in (a, b) + more]
    den = 1
    for v in vals:
        den = den * v.denominator // math.gcd(den, v.denominator)
    ints = [int(v * den) for v in vals]
    g = 0
    for i in ints:
        g = math.gcd(g, i)
    return ":".join(str(i // g) for i in ints)


def hm_time(hours_from_midnight):
    """Clock string like '2:24 pm' from hours after midnight."""
    tot = round(float(hours_from_midnight) * 60)
    h, m = divmod(tot, 60)
    suf = "am" if h < 12 else "pm"
    if h == 12 and m == 0:
        return "12:00 noon"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {suf}"


def hmin(hours):
    tot = round(float(hours) * 60)
    h, m = divmod(tot, 60)
    if h and m:
        return f"{h} h {m} min"
    if h:
        return f"{h} h"
    return f"{m} min"


def make_q(B):
    def q(m, lv, t, stem, key, wrongs, steps, formula, trap, kind="numerical", g=None):
        return B.add(micro=SLUG[m], level=lv, tier=TIER[t], stem=stem, correct=key, wrongs=wrongs,
                     steps=steps, formula=formula, trap=trap, kind=kind, group=g,
                     ref="Standard quantitative-aptitude pattern (SSC/IBPS/SBI/RBI style). Original figures; no text reproduced.")
    return q
