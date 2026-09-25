"""QRE-GK-B builder: static GK batch B (Geography, General Science, Indian Economy). 27 microtopics x (5 foundation + 10 officer)."""
import os as _os, sys
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from collections import Counter
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401
import importlib
from gkb_common import G

B = Batch("QRE-GK-B", "general-knowledge", "GKB", list_file=_os.path.join(_REG, "lists", "GK-B.tsv"))
g = G(B)
for p in ("gkb_p1", "gkb_p2", "gkb_p3"):
    if _os.path.exists(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), p + ".py")):
        importlib.import_module(p).add_all(g)

c = Counter((x["microtopic_slug"], x["exam_tier"]) for x in B.Q)
bad = [(s, c[(s, "foundation")], c[(s, "officer")]) for s in B.cat
       if c[(s, "foundation")] != 5 or c[(s, "officer")] != 10]
if bad:
    print("QUOTA MISMATCH:")
    for b in bad:
        print("  ", b)

# length-cue guard (same rule as the brief's check), reported by id before shuffling
cue = []
for q in B.Q:
    L = sorted([len(q["_correct"])] + [len(t) for t, _ in q["_wrongs"]])
    cl = len(q["_correct"])
    if L[-1] >= 25 and cl == L[-1] and cl > 1.15 * L[-2]:
        cue.append(q["id"])
if cue:
    print("LENGTH CUE:", cue)
assert all(q["verify_fact"] for q in B.Q)
if "--strict" in sys.argv and (bad or cue):
    raise SystemExit(1)
B.write()
