"""Helpers for QRE-GK-A static-GK authoring. Keys for statement / match / chronology / A-R items
are DERIVED from truth flags (not typed by hand), so each key is correct by construction."""
import itertools, random

GEN = "Static fact (durable); verify against reference"
AR_OPTS = {
    "a": "Both A and R are true, and R is the correct explanation of A",
    "b": "Both A and R are true, but R is not the correct explanation of A",
    "c": "A is true, but R is false",
    "d": "A is false, but R is true",
}
AR_ERR = {"a": "treats R as the explanation of A", "b": "misses the causal link between R and A",
          "c": "wrongly rejects R", "d": "wrongly rejects A"}


def _combo(s):
    s = sorted(s)
    if len(s) == 1: return f"{s[0]} only"
    if len(s) == 2: return f"{s[0]} and {s[1]} only"
    return ", ".join(map(str, s[:-1])) + f" and {s[-1]}"


class H:
    def __init__(self, B, ref):
        self.B, self.ref, self.m = B, ref, None

    def slug(self, key):
        hits = [s for s in self.B.cat if s.startswith(key)]
        assert len(hits) == 1, (key, hits)
        return hits[0]

    def topic(self, key, ref):
        self.m, self.ref = self.slug(key), ref

    def _add(self, lv, stem, c, w, steps, trap, kind, tier, ref, formula=GEN):
        return self.B.add(micro=self.m, level=lv, stem=stem, correct=c, wrongs=w, steps=steps,
                          formula=formula, trap=trap, kind=kind, verify_fact=True,
                          ref=ref or self.ref, tier=tier)

    # ---- foundation direct MCQ ----
    def F(self, stem, c, w, why, trap, lv="L1", ref=None):
        w = [x if isinstance(x, tuple) else (x, "plausible confusion with a related fact") for x in w]
        steps = why if isinstance(why, list) else [why]
        return self._add(lv, stem, c, w, steps, trap, "conceptual", "foundation", ref)

    # ---- officer: statement combinations ----
    def S(self, intro, st, trap, ask="correct", lv="L3", ref=None, pairs=False):
        n = len(st)
        truth = {i + 1 for i, (_, t, _) in enumerate(st) if t}
        key = truth if ask == "correct" else set(range(1, n + 1)) - truth
        body = "\n".join(f"{i+1}. {s}" for i, (s, _, _) in enumerate(st))
        noun = "pairs" if pairs else "statements"
        if pairs:
            q = "Which of the pairs given above is/are correctly matched?" if ask == "correct" else \
                "Which of the pairs given above is/are NOT correctly matched?"
        else:
            q = f"Which of the statements given above is/are {'correct' if ask=='correct' else 'NOT correct'}?"
        stem = f"{intro}\n\n{body}\n\n{q}"
        if n == 2:
            lab = {frozenset({1}): "1 only", frozenset({2}): "2 only",
                   frozenset({1, 2}): "Both 1 and 2", frozenset(): "Neither 1 nor 2"}
            c = lab[frozenset(key)]
            w = [(v, "mis-judges one statement") for k, v in lab.items() if k != frozenset(key)]
        else:
            assert key, "empty key not allowed for 3+ statements"
            subs = [set(x) for r in range(1, n + 1) for x in itertools.combinations(range(1, n + 1), r)]
            if n == 4: subs = [s for s in subs if len(s) <= 3 or s == {1, 2, 3, 4}]
            others = [s for s in subs if s != key]
            rnd = random.Random(stem)
            near = [s for s in others if len(s ^ key) == 1]; far = [s for s in others if len(s ^ key) > 1]
            rnd.shuffle(near); rnd.shuffle(far)
            pick = (near[:2] + far)[:3] if len(near) >= 2 else (near + far)[:3]
            c = _combo(key)
            def err(s):
                extra, miss = s - key, key - s
                parts = []
                if extra: parts.append("accepts " + ", ".join(map(str, sorted(extra))))
                if miss: parts.append("rejects " + ", ".join(map(str, sorted(miss))))
                return "; ".join(parts) + f" ({'incorrect' if ask=='correct' else 'correct'} {noun} misjudged)"
            w = [(_combo(s), err(s)) for s in pick]
        steps = [f"{noun[:-1].capitalize()} {i+1} is {'correct' if t else 'incorrect'}: {note}"
                 for i, (_, t, note) in enumerate(st)]
        steps.append(f"Hence the answer is: {c}.")
        return self._add(lv, stem, c, w, steps, trap, "statement", "officer", ref)

    # ---- officer: how many statements correct ----
    def N(self, intro, st, trap, lv="L3", ref=None, pairs=False):
        n = len(st); k = sum(1 for _, t, _ in st if t)
        assert 1 <= k <= n
        body = "\n".join(f"{i+1}. {s}" for i, (s, _, _) in enumerate(st))
        q = "How many of the pairs given above are correctly matched?" if pairs else \
            "How many of the statements given above are correct?"
        names = {1: "Only one", 2: "Only two", 3: "Only three" if n == 4 else "All three", 4: "All four"}
        opts = [names[i] for i in range(1, n + 1)]
        if n == 3: opts.append("None")
        c = names[k]
        w = [(o, "miscounts the correct " + ("pairs" if pairs else "statements")) for o in opts if o != c][:3]
        noun = "Pair" if pairs else "Statement"
        steps = [f"{noun} {i+1} is {'correct' if t else 'incorrect'}: {note}" for i, (_, t, note) in enumerate(st)]
        steps.append(f"{k} of {n} are correct — {c}.")
        return self._add(lv, f"{intro}\n\n{body}\n\n{q}", c, w, steps, trap, "statement", "officer", ref)

    # ---- officer: match the following ----
    def M(self, h1, h2, pairs, trap, lv="L3", ref=None, notes=None, lead=None):
        assert len(pairs) == 4
        rnd = random.Random("|".join(a for a, _ in pairs))
        order = list(range(4))
        while order == [0, 1, 2, 3]:
            rnd.shuffle(order)
        right = [pairs[i][1] for i in order]          # List II in shuffled order
        code = [right.index(pairs[i][1]) + 1 for i in range(4)]
        fmt = lambda p: ", ".join(f"{'ABCD'[i]}-{p[i]}" for i in range(4))
        perms = [list(p) for p in itertools.permutations(range(1, 5)) if list(p) != code]
        close = [p for p in perms if sum(a == b for a, b in zip(p, code)) in (1, 2)]
        rnd.shuffle(close)
        w = [(fmt(p), "mismatches " + ", ".join("ABCD"[i] for i in range(4) if p[i] != code[i])) for p in close[:3]]
        rows = "\n".join(f"| {'ABCD'[i]}. {pairs[i][0]} | {j+1}. {right[j]} |" for i, j in zip(range(4), range(4)))
        stem = (lead + "\n\n" if lead else "") + f"Match List I ({h1}) with List II ({h2}):\n\n| List I | List II |\n|---|---|\n{rows}\n\nSelect the correct answer using the codes below:"
        steps = [f"{pairs[i][0]} → {pairs[i][1]}" + (f" ({notes[i]})" if notes and notes[i] else "") for i in range(4)]
        steps.append(f"Code: {fmt(code)}.")
        return self._add(lv, stem, fmt(code), w, steps, trap, "match", "officer", ref)

    # ---- officer: chronology ----
    def C(self, intro, ev, trap, lv="L3", ref=None):
        """ev: list of (event, sort_key, shown_date) — any order."""
        assert len({k for _, k, _ in ev}) == len(ev)
        rnd = random.Random("|".join(e for e, _, _ in ev))
        shown = list(ev)
        chrono = sorted(ev, key=lambda x: x[1])
        while [e for e, _, _ in shown] == [e for e, _, _ in chrono]:
            rnd.shuffle(shown)
        code = [shown.index(e) + 1 for e in chrono]
        fmt = lambda p: " – ".join(map(str, p))
        perms = [list(p) for p in itertools.permutations(range(1, len(ev) + 1)) if list(p) != code]
        close = [p for p in perms if sum(a == b for a, b in zip(p, code)) in (1, 2)]
        rnd.shuffle(close)
        w = [(fmt(p), "misplaces " + ", ".join(str(code[i]) for i in range(len(p)) if p[i] != code[i]) + " in the sequence") for p in close[:3]]
        body = "\n".join(f"{i+1}. {e}" for i, (e, _, _) in enumerate(shown))
        stem = f"{intro}\n\n{body}\n\nSelect the correct chronological order (earliest first):"
        steps = [f"{e} — {d}" for e, _, d in chrono] + [f"Order: {fmt(code)}."]
        return self._add(lv, stem, fmt(code), w, steps, trap, "statement", "officer", ref)

    # ---- officer: assertion-reason ----
    def A(self, a, r, at, rt, expl, why, trap, lv="L3", ref=None):
        assert at or rt, "both-false A-R not used"
        k = "a" if (at and rt and expl) else "b" if (at and rt) else "c" if at else "d"
        stem = (f"Consider the following:\n\nAssertion (A): {a}\n\nReason (R): {r}\n\n"
                "Choose the correct option:")
        w = [(AR_OPTS[x], AR_ERR[x]) for x in "abcd" if x != k]
        steps = why if isinstance(why, list) else [why]
        steps = steps + [f"A is {'true' if at else 'false'}; R is {'true' if rt else 'false'}"
                         + (f"; R {'does' if expl else 'does not'} explain A." if at and rt else ".")]
        return self._add(lv, stem, AR_OPTS[k], w, steps, trap, "assertion-reason", "officer", ref)

    # ---- officer: numerical (business terms) ----
    def Q(self, stem, c, w, steps, formula, trap, lv="L3", ref=None, tier="officer"):
        return self._add(lv, stem, c, w, steps, trap, "numerical", tier, ref, formula=formula)
