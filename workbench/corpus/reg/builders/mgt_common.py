"""Shared helpers for REG-CORPUS-MGT part modules."""
import sys, math, itertools, random
sys.path.insert(0, '/home/claude/corpus')
from reglib import load_catalogue, inr, R, pct, lakh, crore  # noqa: F401

_CAT = list(load_catalogue("management").keys())


def m(frag):
    """Resolve a unique microtopic slug from a fragment."""
    hits = [s for s in _CAT if frag in s]
    assert len(hits) == 1, f"microtopic fragment '{frag}' matched {hits}"
    return hits[0]


def cq(B, micro, level, stem, correct, wrongs, steps, trap, formula="—", kind="conceptual",
       group=None, verify=False, ref=None):
    return B.add(micro=m(micro), level=level, stem=stem, correct=correct, wrongs=wrongs,
                 steps=steps, formula=formula, trap=trap, kind=kind, group=group,
                 verify_fact=verify, ref=ref)


def nq(B, micro, level, stem, correct, wrongs, steps, formula, trap, group=None, verify=False, ref=None):
    return cq(B, micro, level, stem, correct, wrongs, steps, trap, formula=formula,
              kind="numerical", group=group, verify=verify, ref=ref)


# ---------------------------------------------------------------- statements
def _combo(s, n):
    s = sorted(s)
    if not s:
        return "None of the statements"
    if len(s) == n:
        return ", ".join(map(str, s[:-1])) + f" and {s[-1]}" if n > 2 else f"Both {s[0]} and {s[1]}"
    if len(s) == 1:
        return f"{s[0]} only"
    return ", ".join(map(str, s[:-1])) + f" and {s[-1]} only"


def stmt(B, micro, level, intro, stmts, trap, group=None, verify=False, ref=None,
         ask="Which of the statements given above is/are correct?", avoid_none=True):
    """stmts: list of (text, is_true, note). Distractors = nearest wrong combinations,
    each labelled with the exact misjudged statement(s)."""
    n = len(stmts)
    rng = random.Random("stmt|" + intro[-60:] + "|" + stmts[0][0][:40])
    stmts = list(stmts); rng.shuffle(stmts)          # remove position bias (e.g. statement 1 always true)
    truth = frozenset(i + 1 for i, (_, v, _) in enumerate(stmts) if v)
    stem = intro + "\n\n" + "\n".join(f"{i+1}. {t}" for i, (t, _, _) in enumerate(stmts)) + f"\n\n{ask}"
    allsets = []
    for r in range(0, n + 1):
        for c in itertools.combinations(range(1, n + 1), r):
            fs = frozenset(c)
            if fs == truth or (avoid_none and not fs and truth):
                continue
            allsets.append(fs)
    # candidate distractors: Hamming distance 1 or 2 from the key. Choose a triple in which the key is NOT
    # uniquely the 'centre' of the four options (otherwise test-wise candidates can spot it).
    cand = [s for s in allsets if len(s ^ truth) <= 2]
    if len(cand) < 3:
        cand = allsets
    tot = lambda x, grp: sum(len(x ^ y) for y in grp if y is not x)
    good = []
    for tri in itertools.combinations(cand, 3):
        grp = [truth, *tri]
        kt = tot(truth, grp)
        if any(tot(w, grp) <= kt for w in tri):
            good.append((sum(len(w ^ truth) == 1 for w in tri), tri))
    if good:
        best = max(g_[0] for g_ in good)
        pool = [t for c_, t in good if c_ == best]
        chosen = pool[rng.randrange(len(pool))]
    else:
        chosen = sorted(allsets, key=lambda s: (len(s ^ truth), sorted(s)))[:3]
    wrongs = []
    for s in chosen:
        errs = []
        for k in sorted(s ^ truth):
            note = stmts[k - 1][2]
            errs.append(f"accepts false statement {k} ({note})" if k in s
                        else f"rejects correct statement {k} ({note})")
        wrongs.append((_combo(s, n), "; ".join(errs)))
    steps = [f"Statement {i+1}: {'correct' if v else 'incorrect'} — {note}." for i, (_, v, note) in enumerate(stmts)]
    return cq(B, micro, level, stem, _combo(truth, n), wrongs, steps, trap, kind="statement",
              group=group, verify=verify, ref=ref)


# ---------------------------------------------------------------- assertion-reason
AR = ["Both A and R are true, and R is the correct explanation of A",
      "Both A and R are true, but R is not the correct explanation of A",
      "A is true, but R is false",
      "A is false, but R is true"]
_ARV = [(True, True, True), (True, True, False), (True, False, None), (False, True, None)]


def ar(B, micro, level, A, Rs, key, steps, trap, group=None, verify=False, ref=None):
    ka, kr, ke = _ARV[key]
    stem = (f"**Assertion (A):** {A}\n\n**Reason (R):** {Rs}\n\n"
            "Choose the correct option.")
    wrongs = []
    for i, (a, r, e) in enumerate(_ARV):
        if i == key:
            continue
        err = []
        if a != ka: err.append(f"judges A {'true' if a else 'false'}")
        if r != kr: err.append(f"judges R {'true' if r else 'false'}")
        if a and r and ka and kr and e != ke:
            err.append("assumes R explains A merely because both are true" if e else "misses that R is the very reason for A")
        wrongs.append((AR[i], "; ".join(err)))
    return cq(B, micro, level, stem, AR[key], wrongs, steps, trap, kind="assertion-reason",
              group=group, verify=verify, ref=ref)


# ---------------------------------------------------------------- match the following
def match(B, micro, level, intro, left, right, key, wrongs, steps, trap, h1="List I", h2="List II",
          group=None, verify=False, ref=None):
    """left: items A..; right: items 1..; key: list of right numbers for each left item.
    wrongs: list of (tuple_of_left_indices_to_rotate, error)."""
    L = "ABCDEF"
    perm = list(range(len(right)))
    random.Random("match|" + intro + left[0]).shuffle(perm)      # shuffle List II so the key is not A-1, B-2 ...
    right = [right[j] for j in perm]
    key = [perm.index(k - 1) + 1 for k in key]
    rows = "\n".join(f"| {L[i]}. {left[i]} | {i+1}. {right[i]} |" for i in range(len(left)))
    stem = f"{intro}\n\n| {h1} | {h2} |\n|---|---|\n{rows}\n\nSelect the correct matching."
    assert sorted(key) == list(range(1, len(right) + 1))
    fmt = lambda k: ", ".join(f"{L[i]}-{k[i]}" for i in range(len(k)))
    outs = []
    for rot, err in wrongs:
        k = list(key)
        vals = [k[i] for i in rot]
        vals = vals[1:] + vals[:1]
        for i, v in zip(rot, vals):
            k[i] = v
        outs.append((fmt(k), err))
    return cq(B, micro, level, stem, fmt(key), outs, steps, trap, kind="match",
              group=group, verify=verify, ref=ref)
