"""QRE-GK-A builder — static GK (History, Polity, IR, Misc). 28 microtopics x 15 (5 foundation + 10 officer)."""
import os as _os, sys
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from collections import Counter
from reglib import Batch, inr, R, pct, lakh, crore
import gka_p1, gka_p2, gka_p3, gka_p4

B = Batch("QRE-GK-A", "general-knowledge", "GKA", list_file=_os.path.join(_REG, "lists", "GK-A.tsv"))
for part in (gka_p1, gka_p2, gka_p3, gka_p4):
    part.add_all(B)

per = Counter((q["microtopic_slug"], q["exam_tier"]) for q in B.Q)
for s in B.cat:
    assert per[(s, "foundation")] == 5 and per[(s, "officer")] == 10, (s, per[(s, "foundation")], per[(s, "officer")])
assert all(q["verify_fact"] for q in B.Q)
assert len(B.Q) == 420, len(B.Q)
B.write()
