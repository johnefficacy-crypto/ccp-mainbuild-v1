"""REG-CORPUS-FIN-C builder: finance · corporate finance / financial management (lists/finance.C.tsv, 70 Q)
+ Income-tax Act, 2025 (5 Q, existing finance slugs). QUOTA = 75.
Parts: finc_p1 (cost of capital, WACC/MCC, CAPM), finc_p2 (capital budgeting incl. risk & rationing),
finc_p3 (leverage, EBIT-EPS, capital structure, dividend), finc_p4 (L4 case sets C1-C4), finc_p5 (Income-tax Act, 2025).
Run: python3 build_REG-CORPUS-FIN-C.py
"""
import os as _os, sys, importlib
from collections import Counter
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401,E402
from finc_common import SLUGS, TAX_SLUGS  # noqa: E402

QUOTA = 75
PARTS = ["finc_p1", "finc_p2", "finc_p3", "finc_p4", "finc_p5"]

B = Batch("REG-CORPUS-FIN-C", subject="finance", prefix="FINC")
for p in PARTS:
    n0 = len(B.Q)
    importlib.import_module(p).add_all(B)
    print(f"{p}: {len(B.Q)-n0} questions")

# --- batch-level checks ---
bad = [q["id"] for q in B.Q if q["microtopic_slug"] not in SLUGS + TAX_SLUGS]
assert not bad, f"slugs outside allowed set: {bad}"
p1 = [q for q in B.Q if q["microtopic_slug"] in SLUGS]
p2 = [q for q in B.Q if q["microtopic_slug"] in TAX_SLUGS]
assert len(p1) == 70 and len(p2) == 5, (len(p1), len(p2))
cov = Counter(q["microtopic_slug"] for q in p1)
assert all(cov[s] >= 5 for s in SLUGS), {s: cov[s] for s in SLUGS}
for q in p2:
    assert q["verify_fact"] and q["stem"].startswith("Under the Income-tax Act, 2025, "), q["id"]
    assert "section" not in q["stem"].lower(), q["id"]
lv = Counter(q["rubric_level"] for q in B.Q)
groups = Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"])
assert len(groups) >= 3
for g, n in groups.items():
    assert 3 <= n <= 5, (g, n)
    stems = {q["stem"].rsplit("\n\n", 1)[0] for q in B.Q if q["stimulus_group"] == g}
    assert len(stems) == 1, f"case stem not repeated identically in {g}"
assert len(B.Q) == QUOTA, f"count {len(B.Q)} != {QUOTA}"

# length-cue guard: correct option must not be the uniquely longest by >15% (when >= 25 chars)
cue = []
for q in B.Q:
    ls = sorted([len(q["_correct"])] + [len(t) for t, _ in q["_wrongs"]])
    c = len(q["_correct"])
    if ls[-1] >= 25 and c == ls[-1] and c > 1.15 * ls[-2]:
        cue.append(q["id"])
assert not cue, f"length cue: {cue}"

print("levels", dict(lv), "| groups", dict(groups), "| verify_fact", sum(q["verify_fact"] for q in B.Q))
print("kinds", dict(Counter(q["question_kind"] for q in B.Q)))
for s in SLUGS + TAX_SLUGS:
    n = sum(1 for q in B.Q if q["microtopic_slug"] == s)
    if n:
        print(f"  {n:2d}  {s}")
B.write()
