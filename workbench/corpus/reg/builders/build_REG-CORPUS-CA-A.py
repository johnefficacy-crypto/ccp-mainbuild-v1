"""REG-CORPUS-CA-A — Companies Act 2013 (list A), 130 questions for SEBI / PFRDA.
Part modules caa_p1..caa_p4 each expose add_all(B). One Batch, one write().
Run: python3 /home/claude/corpus/builders/build_REG-CORPUS-CA-A.py
"""
import sys
sys.path.insert(0, '/home/claude/corpus')
sys.path.insert(0, '/home/claude/corpus/builders')
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401
import caa_p1, caa_p2, caa_p3, caa_p4

QUOTA = 130
B = Batch("REG-CORPUS-CA-A", subject="companies-act", prefix="CAA")
caa_p3.add_all(B)
caa_p1.add_all(B)
caa_p4.add_all(B)
caa_p2.add_all(B)

import csv
allowed = {r["slug"] for r in csv.DictReader(open('/home/claude/corpus/lists/companies-act.A.tsv'), delimiter="\t")}
used = {q["microtopic_slug"] for q in B.Q}
assert used <= allowed, used - allowed
missing = allowed - used
assert not missing, missing
print("count", len(B.Q))
assert len(B.Q) == QUOTA, len(B.Q)
B.write()
