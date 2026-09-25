"""QRE-CORPUS builder: GIR-A (general intelligence & reasoning, batch A). 360 items, 15 per microtopic
(5 foundation + 10 officer). Puzzles / seating: clue sets proven unique by exhaustive enumeration
(gira_engine.solve); row-with-unknown-total and data sufficiency by enumeration (gira_misc); inequalities by
integer-model enumeration and syllogisms by Venn-region model enumeration (gira_logic).
Run: python3 builders/build_QRE-GIR-A.py"""
import os as _os, sys
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401
from collections import Counter
import gira_arr, gira_misc, gira_logic

B = Batch("QRE-GIR-A", "general-intelligence-reasoning", "GRA", list_file=_os.path.join(_REG, 'lists', 'GIR-A.tsv'))
for mod in (gira_arr, gira_misc, gira_logic):
    mod.add_all(B)

c = Counter((q["microtopic_slug"], q["exam_tier"]) for q in B.Q)
for slug in B.cat:
    f, o = c[(slug, "foundation")], c[(slug, "officer")]
    assert (f, o) == (5, 10), f"QUOTA {slug} {f} {o}"
groups = Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"])
assert all(3 <= v <= 5 for v in groups.values()), groups
assert len(B.Q) == 360, len(B.Q)
B.write()
