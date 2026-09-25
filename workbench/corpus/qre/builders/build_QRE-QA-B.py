"""QRE-QA-B builder: quantitative aptitude batch B (Algebra, DI, Geometry & Mensuration, Number System, Simplification, Trigonometry)."""
import os as _os, sys
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from collections import Counter
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401
import importlib

B = Batch("QRE-QA-B", "quantitative-aptitude", "QAB", list_file=_os.path.join(_REG, "lists", "QA-B.tsv"))
PARTS = [p for p in ("qab_p1", "qab_p2", "qab_p3", "qab_p4", "qab_p5", "qab_p6")
         if _os.path.exists(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), p + ".py"))]
for p in PARTS:
    importlib.import_module(p).add_all(B)

c = Counter((x["microtopic_slug"], x["exam_tier"]) for x in B.Q)
bad = []
for slug in B.cat:
    if c[(slug, "foundation")] != 5 or c[(slug, "officer")] != 10:
        bad.append((slug, c[(slug, "foundation")], c[(slug, "officer")]))
if bad:
    print("QUOTA MISMATCH:")
    for b in bad:
        print("  ", b)
    if "--strict" in sys.argv:
        raise SystemExit(1)
B.write()
