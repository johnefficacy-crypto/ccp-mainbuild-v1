"""REG-CORPUS-MGT builder: management (200 Q). Parts live in mgt_p1..mgt_p4 (each defines add_all(B))."""
import sys, os
sys.path.insert(0, '/home/claude/corpus')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401
from collections import Counter
import importlib

PARTS = [p for p in ["mgt_p1", "mgt_p2", "mgt_p3", "mgt_p4"]
         if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), p + ".py"))]
QUOTA = 200

B = Batch("REG-CORPUS-MGT", subject="management", prefix="MGT")
for p in PARTS:
    n0 = len(B.Q)
    importlib.import_module(p).add_all(B)
    print(p, len(B.Q) - n0, dict(Counter(q["rubric_level"] for q in B.Q[n0:])))

groups = Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"])
assert all(3 <= v <= 5 for v in groups.values()), groups
assert all(q["rubric_level"] == "L4" for q in B.Q if q["stimulus_group"])
missing = set(B.cat) - {q["microtopic_slug"] for q in B.Q}
print("case sets", dict(groups), "| missing microtopics", len(missing))
for s in sorted(missing): print("  -", s)
if len(PARTS) == 4:
    assert len(B.Q) == QUOTA, len(B.Q)
    assert not missing
B.write()
