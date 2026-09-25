"""REG-CORPUS-ECO: economics — 220 original MCQs for SEBI / PFRDA / IFSCA Grade A.
Parts (each defines add_all(B)):
  eco_p1  national income accounting
  eco_p2  Keynesian macro, multiplier, IS-LM, money supply & credit multiplier
  eco_p3  micro: demand, elasticity, surplus, tax incidence, market structures
  eco_p4  public finance: deficits, budget classification, fiscal policy
  eco_p5  monetary policy, inflation, Phillips curve, external sector, institutions, cycles
Run: python3 build_REG-CORPUS-ECO.py
"""
import sys, os
sys.path.insert(0, '/home/claude/corpus')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401
import eco_p1, eco_p2, eco_p3, eco_p4, eco_p5

QUOTA = 220
PARTS = [eco_p1, eco_p2, eco_p3, eco_p4, eco_p5]
ONLY = [p for p in PARTS if not sys.argv[1:] or p.__name__ in sys.argv[1:]]

B = Batch("REG-CORPUS-ECO", subject="economics", prefix="ECO")
for p in ONLY:
    before = len(B.Q)
    p.add_all(B)
    print(f"{p.__name__}: {len(B.Q) - before} Q")

if len(ONLY) == len(PARTS):
    assert len(B.Q) == QUOTA, f"quota mismatch: {len(B.Q)} != {QUOTA}"
    covered = {q["microtopic_slug"] for q in B.Q}
    missing = sorted(set(B.cat) - covered)
    assert not missing, f"uncovered microtopics: {missing}"
    groups = {}
    for q in B.Q:
        if q["stimulus_group"]:
            groups.setdefault(q["stimulus_group"], []).append(q)
    for g, qs in groups.items():
        assert 3 <= len(qs) <= 5 and all(x["rubric_level"] == "L4" for x in qs), g
    B.write()
else:
    print("partial run — nothing written; total", len(B.Q))
