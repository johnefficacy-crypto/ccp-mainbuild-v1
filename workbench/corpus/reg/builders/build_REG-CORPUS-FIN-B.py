"""REG-CORPUS-FIN-B builder: finance, microtopics from lists/finance.B.tsv only. QUOTA = 170.
Parts: finb_p1 (primary markets & securities law), finb_p2 (derivatives, risk, valuation),
finb_p3 (money markets, banking, payments, NBFC, regulators), finb_p4 (macro, public finance, tax, MF).
Run: python3 build_REG-CORPUS-FIN-B.py
"""
import os as _os; _REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, os, importlib
from collections import Counter
sys.path.insert(0, _REG)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401
from finb_common import SLUGS

QUOTA = 170
PARTS = [p for p in ("finb_p1", "finb_p2", "finb_p3", "finb_p4") if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), p + ".py"))]

B = Batch("REG-CORPUS-FIN-B", subject="finance", prefix="FINB")
for p in PARTS:
    n0 = len(B.Q)
    importlib.import_module(p).add_all(B)
    print(f"{p}: {len(B.Q)-n0} questions")

# --- batch-level checks ---
bad = [q["id"] for q in B.Q if q["microtopic_slug"] not in SLUGS]
assert not bad, f"slugs outside finance.B: {bad}"
cov = Counter(q["microtopic_slug"] for q in B.Q)
missing = [s for s in SLUGS if s not in cov]
lv = Counter(q["rubric_level"] for q in B.Q)
groups = Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"])
print("levels", dict(lv), "| groups", dict(groups), "| verify_fact", sum(q["verify_fact"] for q in B.Q))
print("kinds", dict(Counter(q["question_kind"] for q in B.Q)))
print("missing microtopics:", missing)
for g, n in groups.items():
    assert 3 <= n <= 5, (g, n)
    stems = {q["stem"].split("\n\n")[0] for q in B.Q if q["stimulus_group"] == g}
    assert len(stems) == 1, f"case stem not repeated identically in {g}"
if len(PARTS) == 4:
    assert len(B.Q) == QUOTA, f"count {len(B.Q)} != {QUOTA}"
    assert not missing, missing
    assert len(groups) >= 2
B.write()
