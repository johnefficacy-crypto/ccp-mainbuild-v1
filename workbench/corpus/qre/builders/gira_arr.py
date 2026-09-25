"""QRE-GIR-A part: puzzles and seating arrangements (13 microtopics). Each unit = one puzzle whose clue set
is generated from a hidden world and then PROVEN unique by exhaustive enumeration (verify_unique)."""
import random
from gira_engine import P, A, C, Clue, generate, verify_unique, length_cue, cap, solve, NUMW
from gira_geo import Geo, Line, RowMix, Circle, Grid, lst

LETTERS = ["ABCDEFGH", "JKLMNPQR", "PQRSTUVW", "BCDEFGHJ", "LMNPQRST", "STUVWXYZ", "EFGHJKLM", "KLMNPQRS", "DEFGHJKL", "MNPQRSTU"]
PNAMES = [["Aman", "Bela", "Chitra", "Dev", "Esha", "Farid", "Gauri", "Harsh"],
          ["Kavya", "Lalit", "Meera", "Nikhil", "Om", "Preeti", "Rahul", "Sana"],
          ["Tara", "Uday", "Vani", "Yash", "Zoya", "Arjun", "Bhumi", "Charu"],
          ["Deepa", "Ekta", "Firoz", "Gopal", "Hina", "Ishaan", "Jaya", "Karan"]]


def letters(rng, n):
    s = rng.choice(LETTERS)
    return list(s[:n])


def pnames(rng, n):
    s = rng.choice(PNAMES)
    return sorted(rng.sample(s, n))


class Match(Geo):
    """Pure category matching: persons x two attributes, no ordering."""

    def p_domain(self):
        return [tuple(range(self.n))]

    def intro(self):
        return " ".join([f"{cap(NUMW[self.n])} friends – {lst(self.names)} – are being described."] + [a.intro_text() for a in self.attrs])

    def neighbours(self, w, x):
        return []

    def describe(self, w):
        return "; ".join(f"{self.names[e]}{self.attr_suffix(w, e)}" for e in range(self.n))

    def rel_clues(self, w, rng, pa):
        out = []
        n = self.n
        for i, at in enumerate(self.attrs):
            s = (A, C)[i]
            for e in range(n):
                v = w[s][e]
                e2 = rng.choice([u for u in range(n) if u != e])
                a, b = (e, e2) if rng.random() < 0.5 else (e2, e)
                out.append(Clue(f"Either {self.en(a)} or {self.en(b)} {at.pred.format(v=at.vals[v])}.",
                                (lambda ww, s=s, a=a, b=b, v=v: ww[s][a] == v or ww[s][b] == v), {s}))
        if len(self.attrs) == 2:
            a0, a1 = self.attrs
            for e in range(n):
                v0, v1 = w[A][e], w[C][e]
                x1, x2 = rng.sample([u for u in range(n) if u != v1], 2)
                r0 = cap(a0.ref.format(v=a0.vals[v0]))
                txt = (f"{r0} is neither from {a1.vals[x1]} nor from {a1.vals[x2]}." if a1.key == "city" else
                       f"{r0} {a1.neg.format(v=a1.vals[x1])} and {a1.neg.format(v=a1.vals[x2])}.")
                out.append(Clue(txt, (lambda ww, v0=v0, x1=x1, x2=x2: ww[C][ww[A].index(v0)] not in (x1, x2)), {A, C}, "neg"))
        return out

    def q_link(self, w, rng):
        if len(self.attrs) < 2:
            return None
        i = rng.randrange(2)
        a0, a1 = self.attrs[i], self.attrs[1 - i]
        s0, s1 = (A, C)[i], (A, C)[1 - i]
        v0 = rng.randrange(self.n)
        e = w[s0].index(v0)
        corr = a1.vals[w[s1][e]]
        wr = [(a1.vals[w[s1][y]], f"belongs to {self.names[y]}") for y in rng.sample(range(self.n), self.n) if y != e][:3]
        return dict(q=a1.q_of.format(X=a0.ref.format(v=a0.vals[v0])), correct=corr, wrongs=wr,
                    how=f"{a0.ref.format(v=a0.vals[v0])} is {self.names[e]}, who {a1.pred.format(v=corr)}.",
                    trap="Chain the two attributes through the person; do not pair attributes directly from one clue.", kind="conceptual")


def make_puzzle(factory, seed, direct_last=True, pa=0.35, max_clues=None, min_clues=0):
    for att in range(80):
        rng = random.Random(f"{seed}#{att}")
        geo = factory(rng)
        w = geo.rand_world(rng)
        pool = geo.pool(w, rng, pa)
        r = generate(geo.domains(), pool, rng, direct_last=direct_last)
        if r is None:
            continue
        clues, sol = r
        if max_clues and len(clues) > max_clues:
            continue
        if len(clues) < min_clues:
            continue
        verify_unique(geo.domains(), clues, w)
        rng.shuffle(clues)
        return geo, w, clues, rng
    raise RuntimeError(f"could not build puzzle {seed}")


QFUN = {
    "rel": lambda g, w, r, c: g.q_rel(w, r) if hasattr(g, "q_rel") else None,
    "attr_rel": lambda g, w, r, c: g.q_rel(w, r, attr_ref=True) if hasattr(g, "q_rel") and g.attrs else None,
    "at": lambda g, w, r, c: g.q_at(w, r) if hasattr(g, "q_at") else None,
    "slot": lambda g, w, r, c: g.q_slot(w, r) if hasattr(g, "q_slot") else None,
    "btw": lambda g, w, r, c: g.q_btw(w, r) if hasattr(g, "q_btw") else None,
    "cnt": lambda g, w, r, c: g.q_cnt(w, r) if hasattr(g, "q_cnt") else None,
    "same": lambda g, w, r, c: g.q_same(w, r) if hasattr(g, "q_same") else None,
    "attr_of": lambda g, w, r, c: g.q_attr_of(w, r),
    "attr_who": lambda g, w, r, c: g.q_attr_who(w, r),
    "stmt": lambda g, w, r, c: g.q_stmt(w, r, c, True),
    "stmt_not": lambda g, w, r, c: g.q_stmt(w, r, c, False),
    "odd_pairs": lambda g, w, r, c: g.q_odd_pairs(w, r),
    "odd_cat": lambda g, w, r, c: g.q_odd_cat(w, r),
    "posrel": lambda g, w, r, c: g.q_posrel(w, r) if hasattr(g, "q_posrel") else None,
    "facecount": lambda g, w, r, c: g.q_facecount(w, r) if hasattr(g, "q_facecount") else None,
    "ends": lambda g, w, r, c: g.q_ends(w, r) if hasattr(g, "q_ends") else None,
    "opp": lambda g, w, r, c: g.q_opp(w, r) if hasattr(g, "q_opp") else None,
    "btwdir": lambda g, w, r, c: g.q_btwdir(w, r) if hasattr(g, "q_btwdir") else None,
    "above": lambda g, w, r, c: g.q_above(w, r) if hasattr(g, "q_above") else None,
    "flat": lambda g, w, r, c: g.q_flat(w, r) if hasattr(g, "q_flat") else None,
    "samefloor": lambda g, w, r, c: g.q_samefloor(w, r) if hasattr(g, "q_samefloor") else None,
    "link": lambda g, w, r, c: g.q_link(w, r) if hasattr(g, "q_link") else None,
}
FALLBACK = ["stmt", "attr_of", "attr_who", "rel", "stmt_not", "btw", "cnt", "at", "slot", "link", "posrel", "above", "samefloor", "flat", "opp"]


def anchor_hint(geo, clues):
    d = geo.domains()
    sc = []
    for c in clues:
        if c.need == {P}:
            k = sum(1 for p in d[P] if c.fn((p, None, None, None)))
            sc.append((k, c.text))
    sc.sort()
    if not sc:
        return None
    t = [f"'{x[1]}'" for x in sc[:2]]
    return "Start from the most restrictive position clue(s): " + " and ".join(t) + "; then place the others by elimination."


def questions_for(geo, w, clues, rng, prefs, k):
    out, seen = [], set()
    for t in list(prefs) + FALLBACK:
        if len(out) >= k:
            break
        if t in seen and t not in ("odd_pairs", "rel"):
            continue
        for _ in range(6):
            q = QFUN[t](geo, w, rng, clues)
            if q is None:
                break
            texts = [q["correct"]] + [x[0] for x in q["wrongs"]]
            if len(q["wrongs"]) != 3 or len(set(texts)) != 4 or length_cue(texts, q["correct"]):
                continue
            key = (q["q"], q["correct"])
            if any(q["q"] == o["q"] for o in out):
                if t != "odd_pairs" or any(key == (o["q"], o["correct"]) for o in out):
                    continue
                q["q"] = q["q"].replace("In each pair below", "Consider the pairs below. In each").replace("Which pair does not", "Which pair does not") if t == "odd_pairs" else q["q"]
                if any(q["q"] == o["q"] for o in out):
                    continue
            out.append(q)
            seen.add(t)
            break
    assert len(out) == k, f"only {len(out)} questions"
    return out


def emit(B, micro, tier, level, geo, w, clues, qs, group=None, topic="arrangement"):
    stim = geo.intro() + "\n\n" + "\n".join(f"- {c.text}" for c in clues)
    hint = anchor_hint(geo, clues)
    for q in qs:
        steps = [f"Exhaustive enumeration over {geo.space_note()} leaves exactly one arrangement that satisfies all "
                 f"{len(clues)} conditions (uniqueness asserted by the builder's solver)."]
        if hint:
            steps.append(hint)
        steps += [f"Solved arrangement — {geo.describe(w)}.", q["how"]]
        B.add(micro=micro, level=level, tier=tier, group=group,
              stem=stim + "\n\n" + q["q"], correct=q["correct"], wrongs=q["wrongs"], steps=steps,
              formula="Unique arrangement by exhaustive case enumeration (itertools brute force)",
              trap=q["trap"], kind="case" if group else q["kind"],
              ref=f"Standard {topic} pattern (SSC/IBPS/SBI/RBI reasoning). Original puzzle; clue set proven unique by solver in builder.")


# ------------------------------------------------------------------ specs
def L(kind, n, attrs=(), nm=letters, **kw):
    return lambda rng: Line(kind, nm(rng, n), attrs, rng, **kw)


def RM(n, attrs=()):
    return lambda rng: RowMix(letters(rng, n), attrs, rng)


def CI(n, facing="in", attrs=(), shape="circle"):
    return lambda rng: Circle(letters(rng, n), attrs, rng, facing=facing, shape=shape)


def GR(floors, attrs=()):
    return lambda rng: Grid(letters(rng, 2 * floors), floors, attrs, rng)


def MA(n, attrs):
    return lambda rng: Match(pnames(rng, n), attrs, rng)


def MO(months, dates, attrs=()):
    n = len(months) * len(dates)
    return lambda rng: Line("month", pnames(rng, n), attrs, rng, months=months, dates=dates)


def YR(n, attrs=(), y0=2016):
    return lambda rng: Line("year", pnames(rng, n), attrs, rng, year0=y0)


# unit = (tier, level, factory, n_questions, prefs, direct_last)
SPECS = {
    "reas-linear-row-single-row-one-direction-3c93ae0f": ("seating arrangement", [
        ("foundation", "L1", L("row", 5), 1, ["at"], False),
        ("foundation", "L1", L("row", 5), 1, ["rel"], False),
        ("foundation", "L2", L("row", 6), 1, ["rel"], True),
        ("foundation", "L2", L("row", 6), 1, ["btw"], True),
        ("foundation", "L2", L("row", 6), 1, ["slot"], True),
        ("officer", "L3", L("row", 7), 1, ["stmt"], True),
        ("officer", "L3", L("row", 6, ["city"]), 1, ["attr_rel"], True),
        ("officer", "L4", L("row", 8, ["fruit"]), 5, ["rel", "attr_of", "btw", "stmt", "attr_who"], True),
        ("officer", "L4", L("row", 7, ["dept"]), 3, ["attr_rel", "cnt", "stmt_not"], True)]),
    "reas-linear-row-facing-both-directions-08c55ceb": ("seating arrangement", [
        ("foundation", "L1", RM(5), 1, ["ends"], False),
        ("foundation", "L2", RM(5), 1, ["rel"], False),
        ("foundation", "L2", RM(6), 1, ["facecount"], True),
        ("foundation", "L2", RM(6), 1, ["rel"], True),
        ("foundation", "L2", RM(6), 1, ["posrel"], True),
        ("officer", "L3", RM(7), 1, ["rel"], True),
        ("officer", "L3", RM(6, ["sport"]), 1, ["stmt"], True),
        ("officer", "L4", RM(8), 5, ["rel", "posrel", "facecount", "stmt", "btw"], True),
        ("officer", "L4", RM(7, ["city"]), 3, ["attr_rel", "attr_who", "stmt_not"], True)]),
    "reas-circular-arrangement-facing-centre-49054cf2": ("circular seating", [
        ("foundation", "L1", CI(5), 1, ["rel"], False),
        ("foundation", "L1", CI(5), 1, ["posrel"], False),
        ("foundation", "L2", CI(6), 1, ["opp"], True),
        ("foundation", "L2", CI(6), 1, ["rel"], True),
        ("foundation", "L2", CI(6), 1, ["btwdir"], True),
        ("officer", "L3", CI(7), 1, ["posrel"], True),
        ("officer", "L3", CI(6, attrs=["car"]), 1, ["attr_rel"], True),
        ("officer", "L4", CI(8, attrs=["fruit"]), 5, ["rel", "attr_of", "opp", "btwdir", "stmt"], True),
        ("officer", "L4", CI(7, attrs=["subject"]), 3, ["attr_rel", "posrel", "stmt_not"], True)]),
    "reas-circular-arrangement-mixed-facing-5596b070": ("circular seating", [
        ("foundation", "L1", CI(5, "mixed"), 1, ["facecount"], False),
        ("foundation", "L2", CI(5, "mixed"), 1, ["rel"], False),
        ("foundation", "L2", CI(6, "mixed"), 1, ["rel"], True),
        ("foundation", "L2", CI(6, "mixed"), 1, ["posrel"], True),
        ("foundation", "L2", CI(6, "mixed"), 1, ["opp"], True),
        ("officer", "L3", CI(7, "mixed"), 1, ["rel"], True),
        ("officer", "L3", CI(6, "mixed", ["city"]), 1, ["stmt"], True),
        ("officer", "L4", CI(8, "mixed"), 5, ["rel", "posrel", "facecount", "btwdir", "stmt"], True),
        ("officer", "L4", CI(7, "mixed", ["sport"]), 3, ["attr_rel", "attr_who", "stmt_not"], True)]),
    "reas-square-and-rectangular-arrangement-18e7b720": ("square/rectangular seating", [
        ("foundation", "L1", CI(4, "in", shape="square"), 1, ["rel"], False),
        ("foundation", "L2", CI(6, "in", shape="rect"), 1, ["rel"], False),
        ("foundation", "L2", CI(6, "in", shape="rect"), 1, ["posrel"], True),
        ("foundation", "L2", CI(8, "in", shape="square"), 1, ["opp"], True),
        ("foundation", "L2", CI(8, "in", shape="square"), 1, ["rel"], True),
        ("officer", "L3", CI(8, "sq", shape="square"), 1, ["rel"], True),
        ("officer", "L3", CI(6, "in", ["fruit"], shape="rect"), 1, ["attr_rel"], True),
        ("officer", "L4", CI(8, "sq", ["dept"], shape="square"), 5, ["rel", "attr_of", "odd_cat", "posrel", "stmt"], True),
        ("officer", "L4", CI(8, "mixed", shape="square"), 3, ["rel", "facecount", "stmt_not"], True)]),
    "reas-floor-puzzle-1df93898": ("floor puzzle", [
        ("foundation", "L1", L("floor", 5), 1, ["at"], False),
        ("foundation", "L1", L("floor", 5), 1, ["slot"], False),
        ("foundation", "L2", L("floor", 6), 1, ["rel"], True),
        ("foundation", "L2", L("floor", 6), 1, ["btw"], True),
        ("foundation", "L2", L("floor", 6), 1, ["cnt"], True),
        ("officer", "L3", L("floor", 7), 1, ["stmt"], True),
        ("officer", "L3", L("floor", 6, ["car"]), 1, ["attr_rel"], True),
        ("officer", "L4", L("floor", 8, ["city"]), 5, ["rel", "attr_of", "btw", "stmt", "slot"], True),
        ("officer", "L4", L("floor", 7, ["sport"]), 3, ["attr_rel", "attr_who", "stmt_not"], True)]),
    "reas-floor-and-flat-double-variable-puzzle-fd87d2ea": ("floor-and-flat puzzle", [
        ("foundation", "L1", GR(2), 1, ["samefloor"], False),
        ("foundation", "L2", GR(3), 1, ["above"], False),
        ("foundation", "L2", GR(3), 1, ["flat"], True),
        ("foundation", "L2", GR(3), 1, ["samefloor"], True),
        ("foundation", "L2", GR(3), 1, ["cnt"], True),
        ("officer", "L3", GR(4), 1, ["above"], True),
        ("officer", "L3", GR(3, ["car"]), 1, ["attr_of"], True),
        ("officer", "L4", GR(4, ["dept"]), 5, ["above", "flat", "attr_of", "samefloor", "stmt"], True),
        ("officer", "L4", GR(3, ["city"]), 3, ["attr_who", "cnt", "stmt_not"], True)]),
    "reas-box-and-stack-puzzle-60988bfb": ("box/stack puzzle", [
        ("foundation", "L1", L("box", 5), 1, ["at"], False),
        ("foundation", "L1", L("box", 5), 1, ["rel"], False),
        ("foundation", "L2", L("box", 6), 1, ["btw"], True),
        ("foundation", "L2", L("box", 6), 1, ["cnt"], True),
        ("foundation", "L2", L("box", 6), 1, ["slot"], True),
        ("officer", "L3", L("box", 7), 1, ["stmt"], True),
        ("officer", "L3", L("box", 6, ["boxcol"]), 1, ["attr_rel"], True),
        ("officer", "L4", L("box", 8, ["boxcol"]), 5, ["rel", "attr_of", "btw", "stmt", "attr_who"], True),
        ("officer", "L4", L("box", 7, ["item"]), 3, ["attr_rel", "cnt", "stmt_not"], True)]),
    "reas-category-and-attribute-matching-puzzle-e5f2f3ac": ("category matching puzzle", [
        ("foundation", "L1", MA(4, ["fruit", "city"]), 1, ["link"], False),
        ("foundation", "L1", MA(4, ["sport", "city"]), 1, ["attr_of"], False),
        ("foundation", "L2", MA(5, ["fruit", "city"]), 1, ["link"], True),
        ("foundation", "L2", MA(5, ["sport", "dept"]), 1, ["attr_who"], True),
        ("foundation", "L2", MA(5, ["subject", "city"]), 1, ["link"], True),
        ("officer", "L3", MA(6, ["fruit", "city"]), 1, ["link"], True),
        ("officer", "L3", YR(6, ["dept"]), 1, ["attr_rel"], True),
        ("officer", "L4", YR(6, ["fruit", "city"]), 5, ["attr_of", "attr_who", "rel", "stmt", "slot"], True),
        ("officer", "L4", YR(5, ["sport", "dept"], 2019), 3, ["attr_rel", "attr_of", "stmt_not"], True)]),
    "reas-clock-time-scheduling-puzzle-6b2a94df": ("clock-time scheduling puzzle", [
        ("foundation", "L1", L("time", 5, nm=pnames), 1, ["at"], False),
        ("foundation", "L2", L("time", 5, nm=pnames), 1, ["rel"], False),
        ("foundation", "L2", L("time", 6, nm=pnames), 1, ["slot"], True),
        ("foundation", "L2", L("time", 6, nm=pnames), 1, ["rel"], True),
        ("foundation", "L2", L("time", 6, nm=pnames), 1, ["btw"], True),
        ("officer", "L3", L("time", 7, nm=pnames), 1, ["rel"], True),
        ("officer", "L3", L("time", 6, ["city"], nm=pnames), 1, ["attr_rel"], True),
        ("officer", "L4", L("time", 8, ["dept"], nm=pnames), 5, ["rel", "slot", "attr_of", "stmt", "cnt"], True),
        ("officer", "L4", L("time", 7, ["city"], nm=pnames), 3, ["attr_who", "rel", "stmt_not"], True)]),
    "reas-day-and-week-scheduling-puzzle-076b2549": ("day/week scheduling puzzle", [
        ("foundation", "L1", L("day", 5, nm=pnames), 1, ["at"], False),
        ("foundation", "L1", L("day", 5, nm=pnames), 1, ["slot"], False),
        ("foundation", "L2", L("day", 6, nm=pnames), 1, ["rel"], True),
        ("foundation", "L2", L("day", 6, nm=pnames), 1, ["btw"], True),
        ("foundation", "L2", L("day", 7, nm=pnames), 1, ["slot"], True),
        ("officer", "L3", L("day", 7, nm=pnames), 1, ["stmt"], True),
        ("officer", "L3", L("day", 6, ["subject"], nm=pnames), 1, ["attr_rel"], True),
        ("officer", "L4", L("day", 7, ["subject"], nm=pnames), 5, ["rel", "attr_of", "slot", "stmt", "cnt"], True),
        ("officer", "L4", L("day", 6, ["sport"], nm=pnames), 3, ["attr_who", "attr_rel", "stmt_not"], True)]),
    "reas-month-and-date-scheduling-puzzle-3404d95a": ("month-and-date scheduling puzzle", [
        ("foundation", "L1", MO(["January", "March", "April", "June", "August"], [10]), 1, ["at"], False),
        ("foundation", "L2", MO(["February", "April", "July", "October", "November"], [16]), 1, ["slot"], False),
        ("foundation", "L2", MO(["April", "July", "November"], [9, 21]), 1, ["rel"], True),
        ("foundation", "L2", MO(["March", "June", "September"], [5, 18]), 1, ["same"], True),
        ("foundation", "L2", MO(["January", "May", "June"], [12, 25]), 1, ["slot"], True),
        ("officer", "L3", MO(["March", "April", "July", "September"], [7, 22]), 1, ["same"], True),
        ("officer", "L3", MO(["February", "May", "August"], [11, 24], ["city"]), 1, ["attr_rel"], True),
        ("officer", "L4", MO(["January", "April", "June", "October"], [8, 19], ["fruit"]), 5, ["slot", "same", "attr_of", "stmt", "btw"], True),
        ("officer", "L4", MO(["March", "June", "November"], [6, 17], ["sport"]), 3, ["attr_rel", "cnt", "stmt_not"], True)]),
    "reas-odd-one-out-within-an-arrangement-8a59afe3": ("odd-one-out in arrangement", [
        ("foundation", "L1", L("row", 5), 1, ["odd_pairs"], False),
        ("foundation", "L2", CI(6), 1, ["odd_pairs"], True),
        ("foundation", "L2", L("floor", 6), 1, ["odd_cat"], True),
        ("foundation", "L2", L("floor", 6), 1, ["odd_pairs"], True),
        ("foundation", "L2", CI(6, shape="rect"), 1, ["odd_cat"], True),
        ("officer", "L3", CI(8, "in", shape="square"), 1, ["odd_cat"], True),
        ("officer", "L3", CI(7, "mixed"), 1, ["odd_pairs"], True),
        ("officer", "L4", CI(8, "in", ["fruit"]), 5, ["odd_pairs", "odd_pairs", "rel", "attr_of", "stmt"], True),
        ("officer", "L4", GR(4), 3, ["odd_cat", "odd_pairs", "above"], True)]),
}


def add_all(B):
    gi = 0
    for mi, (micro, (topic, units)) in enumerate(SPECS.items()):
        for ui, (tier, level, fac, nq, prefs, dl) in enumerate(units):
            seed = f"GRA-{micro}-{ui}"
            geo, w, clues, rng = make_puzzle(fac, seed, direct_last=dl)
            qs = questions_for(geo, w, clues, rng, prefs, nq)
            group = None
            if nq > 1:
                gi += 1
                group = f"GRA-ARR-{gi:02d}"
            emit(B, micro, tier, level, geo, w, clues, qs, group, topic)
