"""REG-CORPUS-FIN-A builder — finance microtopics in lists/finance.A.tsv (170 questions).
Parts: fina_p1 (fixed income/derivatives/FX/active-passive), fina_p2 (banking & money market),
fina_p3 (market institutions, regulation, macro-fiscal), fina_p4 (taxes & GST).
Every numeric key and distractor is computed in the part modules.
Run: python3 builders/build_REG-CORPUS-FIN-A.py
"""
import os as _os; _REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, os, csv
sys.path.insert(0, _REG)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections import Counter
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401
import fina_p1, fina_p2, fina_p3, fina_p4

QUOTA = 170
B = Batch("REG-CORPUS-FIN-A", subject="finance", prefix="FINA")
for part in (fina_p1, fina_p2, fina_p3, fina_p4):
    part.add_all(B)

# ---- batch-level checks ----
with open(_os.path.join(_REG, 'lists', 'finance.A.tsv'), encoding='utf-8') as f:
    scope = {r['slug'] for r in csv.DictReader(f, delimiter='\t')}
used = Counter(q['microtopic_slug'] for q in B.Q)
assert set(used) <= scope, f"out-of-scope slugs: {set(used) - scope}"
missing = scope - set(used)
assert not missing, f"microtopics not covered: {missing}"
assert len(B.Q) == QUOTA, len(B.Q)
lv = Counter(q['rubric_level'] for q in B.Q)
assert lv == {"L1": 34, "L2": 51, "L3": 51, "L4": 34}, lv
groups = Counter(q['stimulus_group'] for q in B.Q if q['stimulus_group'])
assert len(groups) >= 2 and all(3 <= n <= 5 for n in groups.values()), groups
assert all(q['rubric_level'] == 'L4' for q in B.Q if q['stimulus_group'])
for q in B.Q:
    if q['verify_fact']:
        assert q['source_refs'][0]['note'], q['id']

B.write()
print("case sets:", dict(groups))
print("verify_fact:", sum(q['verify_fact'] for q in B.Q))
