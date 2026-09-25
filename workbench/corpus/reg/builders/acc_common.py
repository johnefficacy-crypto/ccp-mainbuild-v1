"""Shared helpers for the REG-CORPUS-ACC part modules."""
import os as _os; _REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, _REG)
from reglib import inr, R, pct, lakh, crore  # noqa: F401

AR_OPTS = {
    "both_explains": "Both A and R are true, and R is the correct explanation of A",
    "both_not": "Both A and R are true, but R is not the correct explanation of A",
    "a_only": "A is true, but R is false",
    "r_only": "A is false, but R is true",
}
AR_ERR = {
    "both_explains": "treats R as the reason for A when it is not the operative reason",
    "both_not": "misses the causal link between R and A",
    "a_only": "wrongly rejects a correct reason R",
    "r_only": "wrongly rejects a correct assertion A",
}


def ar(B, micro, level, a, r, key, steps, trap, ref=None, verify_fact=False, errs=None, group=None, pre=""):
    """Assertion-reason question. key in AR_OPTS. errs may override error labels."""
    errs = errs or {}
    stem = pre + (f"**Assertion (A):** {a}\n\n**Reason (R):** {r}\n\nChoose the correct option:")
    wrongs = [(AR_OPTS[k], errs.get(k, AR_ERR[k])) for k in AR_OPTS if k != key]
    return B.add(micro=micro, level=level, stem=stem, correct=AR_OPTS[key], wrongs=wrongs,
                 steps=steps, formula="Assertion-reason analysis", trap=trap,
                 kind="assertion-reason", verify_fact=verify_fact, ref=ref, group=group)


def combo(ids):
    ids = sorted(ids)
    if len(ids) == 1:
        return f"{ids[0]} only"
    if len(ids) == 2:
        return f"{ids[0]} and {ids[1]} only"
    if len(ids) == 3 and ids == [1, 2, 3]:
        return "1, 2 and 3"
    return ", ".join(str(i) for i in ids[:-1]) + f" and {ids[-1]}" + ("" if len(ids) == 4 else " only")


def stmt(B, micro, level, intro, statements, true_ids, wrong_sets, steps, trap,
         ref=None, verify_fact=False, question="Which of the statements given above is/are correct?", group=None):
    """statements: list of texts numbered 1..n. true_ids: list of correct ids.
    wrong_sets: list of (ids_list_or_text, error)."""
    body = "\n".join(f"{i+1}. {s}" for i, s in enumerate(statements))
    stem = f"{intro}\n\n{body}\n\n{question}"
    corr = combo(true_ids) if isinstance(true_ids, list) else true_ids
    wrongs = [((combo(w) if isinstance(w, list) else w), e) for w, e in wrong_sets]
    return B.add(micro=micro, level=level, stem=stem, correct=corr, wrongs=wrongs, steps=steps,
                 formula="Statement analysis", trap=trap, kind="statement",
                 verify_fact=verify_fact, ref=ref, group=group)


def match(B, micro, level, intro, left, right, key, wrong_keys, steps, trap,
          ref=None, verify_fact=False, lh="List I", rh="List II", group=None):
    """left: list of texts labelled A.. ; right: list of texts labelled 1..; key: e.g. [2,1,4,3]
    wrong_keys: list of (perm, error)."""
    n = max(len(left), len(right))
    rows = [f"| | {lh} | | {rh} |", "|---|---|---|---|"]
    for i in range(n):
        l = left[i] if i < len(left) else ""
        r = right[i] if i < len(right) else ""
        rows.append(f"| {'ABCDEF'[i] if i < len(left) else ''} | {l} | {i+1 if i < len(right) else ''} | {r} |")

    def fmt(p):
        return ", ".join(f"{'ABCDEF'[i]}-{v}" for i, v in enumerate(p))
    stem = f"{intro}\n\n" + "\n".join(rows) + "\n\nSelect the correct match:"
    return B.add(micro=micro, level=level, stem=stem, correct=fmt(key),
                 wrongs=[(fmt(p), e) for p, e in wrong_keys], steps=steps,
                 formula="Matching", trap=trap, kind="match", verify_fact=verify_fact, ref=ref, group=group)


def table(headers, rows, align=None):
    align = align or (["---"] + ["---:"] * (len(headers) - 1))
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(align) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def close(a, b, tol=0.51):
    return abs(a - b) <= tol


import csv as _csv
_SLUGS = [r["slug"] for r in _csv.DictReader(open(_os.path.join(_REG, 'lists', 'commerce-accountancy.tsv'), encoding='utf-8'), delimiter='\t')]


def S(prefix):
    """Resolve a microtopic slug from its leading words, e.g. S('as-2-') -> full slug."""
    m = [s for s in _SLUGS if s.startswith('comm-' + prefix)]
    assert len(m) == 1, f"slug prefix {prefix!r} matched {m}"
    return m[0]
