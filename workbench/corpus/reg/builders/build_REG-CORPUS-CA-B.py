"""REG-CORPUS-CA-B — Companies Act 2013, microtopic list B (SEBI / PFRDA).
Run: python3 build_REG-CORPUS-CA-B.py -> out/REG-CORPUS-CA-B.json + _review.md"""
import os as _os; _REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, os, csv
sys.path.insert(0, _REG)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reglib import Batch, inr, R, pct, lakh, crore  # noqa
import cab_p1, cab_p2, cab_p3, cab_p4, cab_p5
from collections import Counter

QUOTA = 130
B = Batch("REG-CORPUS-CA-B", subject="companies-act", prefix="CAB")
for m in (cab_p1, cab_p2, cab_p3, cab_p4, cab_p5):
    m.add_all(B)

allowed = {r["slug"] for r in csv.DictReader(open(_os.path.join(_REG, 'lists', 'companies-act.B.tsv')), delimiter='\t')}
used = Counter(q["microtopic_slug"] for q in B.Q)
bad = set(used) - allowed
assert not bad, f"slugs outside list B: {bad}"
missing = allowed - set(used)
lv = Counter(q["rubric_level"] for q in B.Q)
groups = Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"])
print("count", len(B.Q), "levels", dict(lv), "groups", dict(groups), "missing", missing)
print("verify_fact", sum(q["verify_fact"] for q in B.Q))
assert not missing, missing
assert len(B.Q) == QUOTA, len(B.Q)
B.write()
