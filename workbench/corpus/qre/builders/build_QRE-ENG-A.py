"""QRE-ENG-A builder: English - Reading Comprehension, Cloze Test, Fill in the Blanks (17 microtopics x 15 = 255 Q).
All passages and sentences are original. Run: python3 builders/build_QRE-ENG-A.py
"""
import os as _os, sys
from collections import Counter
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401

import enga_p1, enga_p2, enga_p3, enga_p4, enga_p5

B = Batch("QRE-ENG-A", "english-language", "ENA", list_file=_os.path.join(_REG, "lists", "ENG-A.tsv"))
for part in (enga_p1, enga_p2, enga_p3, enga_p4, enga_p5):
    part.add_all(B)

# --- quota checks: 15 per microtopic = 5 foundation + 10 officer ---
cnt = Counter((x["microtopic_slug"], x["exam_tier"]) for x in B.Q)
for slug in B.cat:
    assert cnt[(slug, "foundation")] == 5, (slug, "foundation", cnt[(slug, "foundation")])
    assert cnt[(slug, "officer")] == 10, (slug, "officer", cnt[(slug, "officer")])
assert len(B.Q) == 255, len(B.Q)

# --- tier/level discipline ---
for x in B.Q:
    if x["exam_tier"] == "foundation":
        assert x["rubric_level"] in ("L1", "L2", "L3"), x["id"]
    else:
        assert x["rubric_level"] in ("L2", "L3", "L4"), x["id"]

# --- case-set integrity: identical stimulus, 3-5 per set ---
groups = {}
for x in B.Q:
    if x["stimulus_group"]:
        groups.setdefault(x["stimulus_group"], []).append(x)
for g, xs in groups.items():
    assert 3 <= len(xs) <= 5, g
    stims = {x["stem"].rsplit("\n\n", 1)[0] for x in xs}
    assert len(stims) == 1, f"{g}: stimulus differs"

# --- length-cue guard (correct option must not stand out as the longest) ---
def cue(opts, c):
    L = sorted(opts)
    return L[-1] >= 25 and c == L[-1] and c > 1.15 * L[-2]
bad = []
for x in B.Q:
    ls = [len(o) for o in [x["_correct"]] + [w for w, _ in x["_wrongs"]]]
    if cue(ls, ls[0]):
        bad.append((x["id"], x["_correct"]))
assert not bad, bad

B.write()
