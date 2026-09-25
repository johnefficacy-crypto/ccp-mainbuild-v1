"""QRE-CORPUS · ENG-B · English language (error spotting, sentence improvement, vocabulary,
idioms, workplace communication). 375 original items: 25 microtopics x (5 foundation + 10 officer).
Error-spotting items keep segment order fixed so that option letters match the (A)(B)(C)(D) marks
in the stem; every other item is key-balanced by reglib-style shuffling.
Run: python3 builders/build_QRE-ENG-B.py
"""
import os as _os, sys, random, importlib
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from reglib import Batch, inr, R, pct, lakh, crore
from collections import Counter

L = "ABCD"


class EBatch(Batch):
    def _finalise(self):
        free = [q for q in self.Q if "_seq" not in q]
        n = len(free)
        pos = ([0, 1, 2, 3] * (n // 4 + 1))[:n]
        random.Random(self.batch + "-keys").shuffle(pos)
        pmap = {q["id"]: p for q, p in zip(free, pos)}
        for q in self.Q:
            if "_seq" in q:
                seq = q.pop("_seq"); q.pop("_wrongs"); q.pop("_correct")
                opts = [{"text": t, "is_correct": c, "error": e} for t, c, e in seq]
                p = [i for i, o in enumerate(opts) if o["is_correct"]][0]
            else:
                p = pmap[q["id"]]
                wrong = list(q.pop("_wrongs")); random.Random(q["id"]).shuffle(wrong)
                c = q.pop("_correct")
                opts = [{"text": t, "is_correct": False, "error": e} for t, e in wrong]
                opts.insert(p, {"text": c, "is_correct": True, "error": None})
            for i, o in enumerate(opts): o["label"] = L[i]
            q["options"] = opts
            q["correct_label"] = L[p]


B = EBatch("QRE-ENG-B", "english-language", "ENB", list_file=_os.path.join(_REG, "lists", "ENG-B.tsv"))

ES_LEAD = ("Read the sentence and find the part that contains a grammatical or usage error. "
           "If there is no error, choose (D) 'No error'.")


def _steps(s):
    return [s] if isinstance(s, str) else list(s)


def mc(micro, tier, level, stem, correct, wrongs, steps, rule, trap, kind="conceptual", group=None, stim=None):
    if stim: stem = stim + "\n\n" + stem
    return B.add(micro=micro, level=level, stem=stem, correct=correct, wrongs=wrongs, steps=_steps(steps),
                 formula=rule, trap=trap, kind=kind, group=group, tier=tier,
                 ref="Original sentence(s); standard usage per Indian competitive-exam conventions (British spelling).")


def es(micro, tier, level, segs, err, fix, rule, why, trap, lead=ES_LEAD, group=None, stim=None, bait=None):
    """Error spotting. segs = 3 parts -> (A)(B)(C) + (D) No error. err = 0..2 or None (No error)."""
    assert len(segs) == 3 and (err is None or err in (0, 1, 2))
    body = " ".join(f"({L[i]}) {s}" for i, s in enumerate(segs)) + " (D) No error"
    stem = lead + "\n\n" + body
    if stim: stem = stim + "\n\n" + stem
    bait = bait or {}
    seq = []
    for i in range(3):
        ok = (err == i)
        seq.append((f"({L[i]}) {segs[i]}", ok, None if ok else bait.get(i, "this part is correct as written")))
    seq.append(("(D) No error", err is None,
                None if err is None else f"misses the error in part ({L[err]})"))
    corr = [t for t, c, e in seq if c][0]
    wr = [(t, e) for t, c, e in seq if not c]
    steps = [why, "Corrected: " + fix] if err is not None else [why, "The sentence is correct as written: " + fix]
    qid = B.add(micro=micro, level=level, stem=stem, correct=corr, wrongs=wr, steps=steps, formula=rule,
                trap=trap, kind="conceptual", group=group, tier=tier,
                ref="Original sentence; segment-marked error-spotting pattern (SSC/IBPS). British spelling.")
    B.Q[-1]["_seq"] = seq
    return qid


SI_LEAD = ("Choose the alternative that best replaces the part in bold. "
           "If no improvement is needed, choose 'No improvement'.")
NI = "No improvement"


def si(micro, tier, level, sentence, correct, wrongs, steps, rule, trap, lead=SI_LEAD, group=None, stim=None):
    return mc(micro, tier, level, lead + "\n\n" + sentence, correct, wrongs, steps, rule, trap, group=group, stim=stim)


PJ_LEAD = "Rearrange the sentences {labs} to form a coherent paragraph."


def pj_stim(sents, lab):
    """sents in correct logical order; lab[i] = label given to sents[i]."""
    assert len(sents) == len(lab) and len(set(lab)) == len(lab)
    labs = sorted(lab)
    show = {lab[i]: sents[i] for i in range(len(sents))}
    return PJ_LEAD.format(labs=", ".join(labs)) + "\n\n" + "\n".join(f"{k}. {show[k]}" for k in labs)


def pj(micro, tier, level, sents, lab, wrongs, cues, trap):
    for w, _ in wrongs:
        assert sorted(w) == sorted(lab) and w != lab, (w, lab)
    stem = pj_stim(sents, lab) + "\n\nWhich is the correct order?"
    return mc(micro, tier, level, stem, lab, wrongs, cues,
              "Opening sentence introduces the topic without back-reference; follow pronoun, connector and time cues.",
              trap)


H = dict(mc=mc, es=es, si=si, pj=pj, pj_stim=pj_stim, NI=NI)

for part in ["engb_p1", "engb_p2", "engb_p3", "engb_p4", "engb_p5", "engb_p6"]:
    importlib.import_module(part).add_all(B, H)

mt = Counter(q["microtopic_slug"] for q in B.Q)
for s in B.cat:
    pass
tiers = Counter((q["microtopic_slug"], q["exam_tier"]) for q in B.Q)
listed = [l.split("\t")[0] for l in open(_os.path.join(_REG, "lists", "ENG-B.tsv"), encoding="utf-8").read().splitlines()[1:] if l.strip()]
for s in listed:
    assert tiers[(s, "foundation")] == 5 and tiers[(s, "officer")] == 10, (s, tiers[(s, "foundation")], tiers[(s, "officer")])
assert set(mt) == set(listed), set(mt) ^ set(listed)
for q in B.Q:
    if q["exam_tier"] == "foundation": assert q["rubric_level"] in ("L1", "L2", "L3"), q["id"]
    else: assert q["rubric_level"] in ("L2", "L3", "L4"), q["id"]
    if q["rubric_level"] == "L4": assert q["stimulus_group"], q["id"]
g = Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"])
assert all(3 <= v <= 5 for v in g.values()), g
assert len(B.Q) == 375, len(B.Q)
B.write()
print("case sets:", dict(g))
