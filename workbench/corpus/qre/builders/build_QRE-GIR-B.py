"""QRE-CORPUS builder: GIR-B (general intelligence & reasoning, batch B). 540 items, 15 per microtopic.
Run: python3 builders/build_QRE-GIR-B.py"""
import os as _os, sys
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401
from collections import Counter
import girb_p1, girb_p2, girb_p3, girb_p4, girb_p5, girb_p6

B = Batch("QRE-GIR-B", "general-intelligence-reasoning", "GRB", list_file=_os.path.join(_REG, 'lists', 'GIR-B.tsv'))
for mod in (girb_p1, girb_p2, girb_p3, girb_p4, girb_p5, girb_p6):
    mod.add_all(B)

c = Counter((q["microtopic_slug"], q["exam_tier"]) for q in B.Q)
for slug in sorted({q["microtopic_slug"] for q in B.Q}):
    f, o = c[(slug, "foundation")], c[(slug, "officer")]
    if (f, o) != (5, 10):
        print("QUOTA", slug, f, o)
B.write()
