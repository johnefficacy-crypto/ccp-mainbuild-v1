"""Shared helpers for the QRE-GK-B part modules (static GK: General Science, Geography, Indian Economy).

G wraps a reglib Batch:
  G.m(key, ref)            -> set current microtopic (key = slug prefix) and its default source ref
  G.f(level, stem, correct, wrongs, steps, trap, ...)   -> foundation direct question
  G.o(level, stem, correct, wrongs, steps, trap, ...)   -> officer direct question
  G.st(tier, level, intro, [(text, bool), ...], steps, trap, ask="correct")  -> statement combination
  G.mt(tier, level, intro, h1, h2, [(left, right) x4], steps, trap)          -> match-the-following
  G.ar(tier, level, A, R, a_true, r_true, explains, steps, trap)             -> assertion-reason
wrongs are "text|named error" strings (or (text, error) tuples).
Every question carries verify_fact=True and a source ref.
"""
import itertools
import random

AR_OPTS = [
    "Both A and R are true and R is the correct explanation of A",
    "Both A and R are true but R is not the correct explanation of A",
    "A is true but R is false",
    "A is false but R is true",
]
AR_ERR = ["over-credits R as the explanation", "misses the causal link / wrongly links R to A",
          "wrongly rejects R", "wrongly rejects A"]


def _combo_label(s, n):
    s = sorted(s)
    if n == 2:
        return {(1,): "1 only", (2,): "2 only", (1, 2): "Both 1 and 2", (): "Neither 1 nor 2"}[tuple(s)]
    if len(s) == n:
        return ", ".join(str(i) for i in s[:-1]) + f" and {s[-1]}"
    if len(s) == 1:
        return f"{s[0]} only"
    if not s:
        return "None of them"
    return ", ".join(str(i) for i in s[:-1]) + f" and {s[-1]} only"


class G:
    def __init__(self, B):
        self.B = B
        self.slugs = list(B.cat)
        self.micro = None
        self.ref = None

    def m(self, key, ref):
        hits = [s for s in self.slugs if s.startswith(key)]
        assert len(hits) == 1, (key, hits)
        self.micro, self.ref = hits[0], ref

    @staticmethod
    def _w(wrongs):
        out = []
        for w in wrongs:
            if isinstance(w, tuple):
                out.append(w)
            else:
                t, _, e = w.partition("|")
                out.append((t.strip(), (e or "plausible but incorrect alternative").strip()))
        return out

    def _add(self, tier, level, stem, correct, wrongs, steps, trap, kind, ref, formula):
        if isinstance(steps, str):
            steps = [steps]
        return self.B.add(micro=self.micro, level=level, stem=stem, correct=correct, wrongs=self._w(wrongs),
                          steps=steps, formula=formula or "Static GK fact", trap=trap, kind=kind,
                          verify_fact=True, ref=ref or self.ref, tier=tier)

    def f(self, level, stem, correct, wrongs, steps, trap, kind="conceptual", ref=None, formula=None):
        return self._add("foundation", level, stem, correct, wrongs, steps, trap, kind, ref, formula)

    def o(self, level, stem, correct, wrongs, steps, trap, kind="conceptual", ref=None, formula=None):
        return self._add("officer", level, stem, correct, wrongs, steps, trap, kind, ref, formula)

    def st(self, tier, level, intro, stmts, steps, trap, ask="correct", ref=None):
        n = len(stmts)
        falses = [i for i, (_, t) in enumerate(stmts) if not t]
        if n == 3 and len(falses) == 1:
            # rotate the lone false statement through positions 1..3 so keys do not cluster on one combination
            self._stc = getattr(self, "_stc", 0) + 1
            fs = stmts[falses[0]]
            rest = [x for i, x in enumerate(stmts) if i != falses[0]]
            stmts = rest[:]
            stmts.insert(self._stc % 3, fs)
        truth = {i + 1 for i, (_, t) in enumerate(stmts) if (t if ask == "correct" else not t)}
        body = "\n".join(f"{i+1}. {t}" for i, (t, _) in enumerate(stmts))
        q = "Which of the statements given above is/are correct?" if ask == "correct" else \
            "Which of the statements given above is/are NOT correct?"
        stem = f"{intro}\n\n{body}\n\n{q}"
        correct = _combo_label(truth, n)
        allsets = [set(c) for k in range(0 if n == 2 else 1, n + 1) for c in itertools.combinations(range(1, n + 1), k)]
        cands = [s for s in allsets if s != truth]
        rnd = random.Random(f"{self.micro}-{len(self.B.Q)}")
        near = [s for s in cands if len(s ^ truth) == 1]
        far = [s for s in cands if len(s ^ truth) > 1]
        rnd.shuffle(near); rnd.shuffle(far)
        pick = (near + far)[:3]
        wrongs = []
        for s in pick:
            extra, miss = sorted(s - truth), sorted(truth - s)
            err = "; ".join(([f"wrongly accepts statement {', '.join(map(str, extra))}"] if extra else []) +
                            ([f"misses statement {', '.join(map(str, miss))}"] if miss else []))
            wrongs.append((_combo_label(s, n), err))
        return self._add(tier, level, stem, correct, wrongs, steps, trap, "statement", ref, None)

    def mt(self, tier, level, intro, h1, h2, pairs, steps, trap, ref=None):
        assert len(pairs) == 4 and len({r for _, r in pairs}) == 4
        rnd = random.Random(f"mt-{self.micro}-{len(self.B.Q)}")
        rights = [r for _, r in pairs]
        order = rights[:]
        while order == rights:
            rnd.shuffle(order)
        code = [order.index(r) + 1 for r in rights]          # A->code[0] ...
        rows = "\n".join(f"| {'ABCD'[i]}. {pairs[i][0]} | {i+1}. {order[i]} |" for i in range(4))
        stem = f"{intro}\n\n| List I ({h1}) | List II ({h2}) |\n|---|---|\n{rows}\n\nSelect the correct code:"
        fmt = lambda c: ", ".join(f"{'ABCD'[i]}-{c[i]}" for i in range(4))
        swaps = list(itertools.combinations(range(4), 2))
        rnd.shuffle(swaps)
        wrongs = []
        for a, b in swaps[:3]:
            c = code[:]
            c[a], c[b] = c[b], c[a]
            wrongs.append((fmt(c), f"swaps {pairs[a][0]} and {pairs[b][0]}"))
        return self._add(tier, level, stem, fmt(code), wrongs, steps, trap, "match", ref, None)

    def ar(self, tier, level, A, R, a_true, r_true, explains, steps, trap, ref=None):
        if a_true and r_true:
            k = 0 if explains else 1
        elif a_true:
            k = 2
        elif r_true:
            k = 3
        else:
            raise AssertionError("both-false AR not used")
        stem = f"Consider the following:\n\nAssertion (A): {A}\n\nReason (R): {R}\n\nChoose the correct option:"
        wrongs = [(AR_OPTS[i], AR_ERR[i]) for i in range(4) if i != k]
        return self._add(tier, level, stem, AR_OPTS[k], wrongs, steps, trap, "assertion-reason", ref, None)
