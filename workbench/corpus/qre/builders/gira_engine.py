"""QRE-GIR-A shared engine: brute-force solvers (itertools), clue objects, unique-clue-set generator,
option helpers. Every arrangement puzzle in this batch is proven unique by `solve` (exhaustive staged
enumeration over permutations / facings / attribute bijections) before any question is written."""
import itertools

P, F, A, C = 0, 1, 2, 3          # world tuple slots: positions, facings, attribute-1, attribute-2

ORD = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh",
       8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth", 13: "thirteenth",
       14: "fourteenth", 15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
       19: "nineteenth", 20: "twentieth"}
NUMW = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
        8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def ordn(k):
    """1 -> 1st, 2 -> 2nd ..."""
    suf = "th" if 10 <= k % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(k % 10, "th")
    return f"{k}{suf}"


def cap(s):
    return s[:1].upper() + s[1:]


class Clue:
    __slots__ = ("text", "fn", "need", "tag", "refs")

    def __init__(self, text, fn, need, tag="", refs=None):
        self.text, self.fn, self.need, self.tag, self.refs = text.replace(".m..", ".m."), fn, frozenset(need), tag, refs

    def __repr__(self):
        return f"Clue({self.text!r})"


def _w(s, v):
    w = [None, None, None, None]
    w[s] = v
    return tuple(w)


def solve(domains, clues, limit=400000):
    """Exhaustive staged enumeration. domains: {stage: [values]}. Returns the list of ALL worlds
    satisfying every clue, or None if an intermediate cross-product would exceed `limit`."""
    for c in clues:
        assert c.need <= set(domains) and c.need, f"clue needs unknown stage: {c}"
    filt = {}
    for s in domains:
        fs = [c.fn for c in clues if c.need == {s}]
        vals = domains[s]
        if fs:
            vals = [v for v in vals if all(f(_w(s, v)) for f in fs)]
        if not vals:
            return []
        filt[s] = vals
    order = sorted(domains, key=lambda s: len(filt[s]))
    multi = [c for c in clues if len(c.need) > 1]
    cur = [_w(order[0], v) for v in filt[order[0]]]
    done = {order[0]}
    for s in order[1:]:
        if len(cur) * len(filt[s]) > limit:
            return None
        done.add(s)
        fs = [c.fn for c in multi if s in c.need and c.need <= done]
        new = []
        for w in cur:
            for v in filt[s]:
                w2 = w[:s] + (v,) + w[s + 1:]
                if all(f(w2) for f in fs):
                    new.append(w2)
        cur = new
        if not cur:
            return []
    return cur


def generate(domains, pool, rng, limit=300000, direct_last=True):
    """Pick a subset of `pool` (all true in the hidden world) whose solution set is exactly one world,
    then prune redundant clues. Returns (clues, world) or None."""
    ind = [c for c in pool if c.tag != "direct"]
    dr = [c for c in pool if c.tag == "direct"]
    rng.shuffle(ind)
    rng.shuffle(dr)
    order = ind + dr if direct_last else rng.sample(pool, len(pool))
    chosen, filt, state = [], {s: list(v) for s, v in domains.items()}, {"w": None}

    def add(c):
        ws = state["w"]
        if ws is not None:
            nw = [w for w in ws if c.fn(w)]
            if len(nw) < len(ws):
                state["w"] = nw
                chosen.append(c)
                return True
            return False
        if len(c.need) == 1:
            (s,) = c.need
            nv = [v for v in filt[s] if c.fn(_w(s, v))]
            if len(nv) < len(filt[s]):
                filt[s] = nv
                chosen.append(c)
                r = solve(domains, chosen, limit)
                if r is not None:
                    state["w"] = r
                return True
            return False
        r = solve(domains, chosen + [c], limit)
        if r is None:
            return None
        chosen.append(c)
        state["w"] = r
        return True

    pending = order
    while True:
        prog, nxt = False, []
        for c in pending:
            if state["w"] is not None and len(state["w"]) == 1:
                break
            r = add(c)
            if r is None:
                nxt.append(c)
            elif r:
                prog = True
        if state["w"] is not None and len(state["w"]) == 1:
            break
        if not prog or not nxt:
            return None
        pending = nxt
    for c in rng.sample(chosen, len(chosen)):
        t = [x for x in chosen if x is not c]
        r = solve(domains, t, limit)
        if r is not None and len(r) == 1:
            chosen = t
    r = solve(domains, chosen, limit * 20)
    assert r is not None and len(r) == 1
    return chosen, r[0]


def verify_unique(domains, clues, world):
    """Builder-level proof: exhaustive enumeration yields exactly the hidden world."""
    r = solve(domains, clues, 20_000_000)
    assert r is not None, "enumeration too large to verify"
    assert len(r) == 1 and r[0] == world, f"clue set not unique ({len(r)} solutions)"
    return True


def length_cue(opts_texts, correct_text):
    L = sorted(len(t) for t in opts_texts)
    c = len(correct_text)
    return L[-1] >= 25 and c == L[-1] and c > 1.15 * L[-2]


def pick_close(cands, target_len, k, rng):
    """Pick k candidate items (text, ...) whose text length is closest to target_len (ties random)."""
    cands = list(cands)
    rng.shuffle(cands)
    cands.sort(key=lambda x: abs(len(x[0]) - target_len))
    return cands[:k]
