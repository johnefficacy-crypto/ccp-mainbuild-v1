"""REG-CORPUS-ACC builder: commerce-accountancy, 180 questions, split into part modules acc_p1..acc_p5.
Every numeric key and distractor is computed in the part modules; asserts guard hand-checked values."""
import sys
import importlib
sys.path.insert(0, '/home/claude/corpus')
sys.path.insert(0, '/home/claude/corpus/builders')
from reglib import Batch, inr, R, pct, lakh, crore  # noqa: F401

PARTS = ["acc_p1", "acc_p2", "acc_p3", "acc_p4", "acc_p5"]
QUOTA = 180

B = Batch("REG-CORPUS-ACC", subject="commerce-accountancy", prefix="ACC")
for name in PARTS:
    try:
        mod = importlib.import_module(name)
    except ModuleNotFoundError as e:
        if e.name == name and "--partial" in sys.argv:
            print(f"(skipping missing part {name})")
            continue
        raise
    n0 = len(B.Q)
    mod.add_all(B)
    print(f"{name}: {len(B.Q) - n0} questions")

# case sets: every group must have 3-5 questions and share the same case text prefix
from collections import Counter
groups = Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"])
for g, n in groups.items():
    assert 3 <= n <= 5, f"case set {g} has {n} questions"
assert len(groups) >= 2 or "--partial" in sys.argv
if "--partial" not in sys.argv:
    assert len(B.Q) == QUOTA, f"have {len(B.Q)} questions, quota {QUOTA}"
B.write()
