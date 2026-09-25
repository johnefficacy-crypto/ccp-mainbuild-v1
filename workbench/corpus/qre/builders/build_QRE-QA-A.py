"""QRE-QA-A builder: quantitative aptitude (Percentage, Profit & Loss incl. SI/CI, Ratio & Proportion,
Time & Work, Speed-Time-Distance). 26 microtopics x 15 (5 foundation + 10 officer) = 390 questions.
Every key and distractor is computed in the part modules; asserts guard the keys."""
import os as _os, sys
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from collections import Counter
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401

import qa_a_p1, qa_a_p2, qa_a_p3, qa_a_p4, qa_a_p5, qa_a_cases

B = Batch("QRE-QA-A", "quantitative-aptitude", "QAA",
          list_file=_os.path.join(_REG, "lists", "QA-A.tsv"))

for mod in (qa_a_p1, qa_a_p2, qa_a_p3, qa_a_p4, qa_a_p5, qa_a_cases):
    mod.add_all(B)

# quota checks: exactly 5 foundation + 10 officer per microtopic
cnt = Counter((q["microtopic_slug"], q["exam_tier"]) for q in B.Q)
bad = []
for slug in B.cat:
    f, o = cnt[(slug, "foundation")], cnt[(slug, "officer")]
    if (f, o) != (5, 10):
        bad.append((slug, f, o))
assert not bad, bad
for q in B.Q:
    if q["exam_tier"] == "foundation":
        assert q["rubric_level"] in ("L1", "L2", "L3"), q["id"]
    else:
        assert q["rubric_level"] in ("L2", "L3", "L4"), q["id"]
    if q["stimulus_group"]:
        assert q["rubric_level"] == "L4" and q["question_kind"] == "case", q["id"]
groups = Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"])
assert len(groups) >= 4 and all(3 <= v <= 5 for v in groups.values()), groups
assert len(B.Q) == 390, len(B.Q)
B.write()
print("case sets:", dict(groups))
