"""QRE-GIR-A arrangement geometries: ordered lines (row / floors / stack / days / clock slots / dates /
years / heights), row facing both directions, circles (facing centre / outside / mixed; square and
rectangular tables), and floor x flat grids. Each geometry supplies: world domains for the solver,
a pool of clues TRUE in a hidden world (the generator keeps a minimal subset that proves uniqueness),
and question factories that read answers off the unique solved world."""
import itertools
import re
from gira_engine import P, F, A, C, Clue, ORD, NUMW, ordn, cap, pick_close, length_cue

STG = (A, C)


def lst(xs):
    xs = list(xs)
    return ", ".join(xs[:-1]) + " and " + xs[-1] if len(xs) > 1 else xs[0]


def numtxt(m):
    return "None" if m == 0 else cap(NUMW[m])


ATTR_LIB = {
    "fruit": dict(vals=["Apple", "Banana", "Cherry", "Guava", "Mango", "Orange", "Papaya", "Litchi"],
                  ref="the one who likes {v}", pred="likes {v}", neg="does not like {v}",
                  q_of="Which fruit does {X} like?", q_who="Who likes {v}?",
                  intro="Each of them likes a different fruit among {vals}."),
    "city": dict(vals=["Agra", "Bhopal", "Chennai", "Delhi", "Indore", "Jaipur", "Kochi", "Patna"],
                 ref="the one from {v}", pred="is from {v}", neg="is not from {v}",
                 q_of="Which city is {X} from?", q_who="Who is from {v}?",
                 intro="Each of them is from a different city among {vals}."),
    "car": dict(vals=["black", "blue", "green", "grey", "red", "silver", "white", "yellow"],
                ref="the owner of the {v} car", pred="owns the {v} car", neg="does not own the {v} car",
                q_of="What is the colour of the car owned by {X}?", q_who="Who owns the {v} car?",
                intro="Each of them owns a car of a different colour among {vals}."),
    "boxcol": dict(vals=["black", "blue", "green", "orange", "pink", "red", "white", "yellow"],
                   ref="the {v} box", pred="is {v}", neg="is not {v}",
                   q_of="What is the colour of {X}?", q_who="Which box is {v}?",
                   intro="Each box is of a different colour among {vals}."),
    "item": dict(vals=["bags", "books", "clocks", "cups", "lamps", "pens", "shoes", "toys"],
                 ref="the box containing {v}", pred="contains {v}", neg="does not contain {v}",
                 q_of="What does {X} contain?", q_who="Which box contains {v}?",
                 intro="Each box contains a different item among {vals}."),
    "subject": dict(vals=["Botany", "Chemistry", "Civics", "Economics", "Geography", "History", "Physics", "Zoology"],
                    ref="the one who teaches {v}", pred="teaches {v}", neg="does not teach {v}",
                    q_of="Which subject does {X} teach?", q_who="Who teaches {v}?",
                    intro="Each of them teaches a different subject among {vals}."),
    "dept": dict(vals=["Admin", "Audit", "Finance", "HR", "IT", "Legal", "Marketing", "Sales"],
                 ref="the one who works in {v}", pred="works in {v}", neg="does not work in {v}",
                 q_of="In which department does {X} work?", q_who="Who works in {v}?",
                 intro="Each of them works in a different department among {vals}."),
    "sport": dict(vals=["Badminton", "Chess", "Cricket", "Football", "Hockey", "Kabaddi", "Tennis", "Volleyball"],
                  ref="the one who plays {v}", pred="plays {v}", neg="does not play {v}",
                  q_of="Which game does {X} play?", q_who="Who plays {v}?",
                  intro="Each of them plays a different game among {vals}."),
}


class Attr:
    def __init__(self, key, n, rng):
        d = ATTR_LIB[key]
        self.key = key
        self.vals = sorted(rng.sample(d["vals"], n))
        for k in ("ref", "pred", "neg", "q_of", "q_who", "intro"):
            setattr(self, k, d[k])

    def intro_text(self):
        return self.intro.format(vals=lst(self.vals))


class Geo:
    prefix = ""          # e.g. "box "
    unit_pl = "persons"
    rel_need = (P,)
    sym_note = ""

    def __init__(self, names, attr_keys=(), rng=None):
        self.names = list(names)
        self.n = len(names)
        self.attrs = [Attr(k, self.n, rng) for k in attr_keys]
        self._dom = None

    # ---------- worlds
    def p_domain(self):
        return list(itertools.permutations(range(self.n)))

    def f_domain(self):
        return None

    def domains(self):
        if self._dom is None:
            d = {P: self.p_domain()}
            fd = self.f_domain()
            if fd is not None:
                d[F] = fd
            for i, _ in enumerate(self.attrs):
                d[STG[i]] = list(itertools.permutations(range(self.n)))
            self._dom = d
        return self._dom

    def rand_world(self, rng):
        w = [None] * 4
        for s, vals in self.domains().items():
            w[s] = rng.choice(vals)
        return tuple(w)

    def space_note(self):
        d = self.domains()
        parts = [f"{len(d[P]):,} seat/position orders"]
        if F in d:
            parts.append(f"{len(d[F]):,} facing patterns")
        for i, _ in enumerate(self.attrs):
            parts.append(f"{len(d[STG[i]]):,} {self.attrs[i].key} assignments")
        return " × ".join(parts)

    # ---------- references
    def en(self, e):
        return self.prefix + self.names[e]

    def ent(self, w, ref):
        k, v = ref
        return v if k < 0 else w[STG[k]].index(v)

    def need(self, ref):
        return set() if ref[0] < 0 else {STG[ref[0]]}

    def rtext(self, ref):
        k, v = ref
        return self.en(v) if k < 0 else self.attrs[k].ref.format(v=self.attrs[k].vals[v])

    def ref_for(self, w, e, rng, pa):
        if self.attrs and rng.random() < pa:
            k = rng.randrange(len(self.attrs))
            return (k, w[STG[k]][e])
        return (-1, e)

    def bin(self, tmpl, rx, ry, pred, need=None, tag=""):
        text = cap(tmpl(self.rtext(rx), self.rtext(ry)))
        ent = self.ent

        def fn(w):
            a, b = ent(w, rx), ent(w, ry)
            return a != b and pred(w, a, b)
        return Clue(text, fn, set(need or self.rel_need) | self.need(rx) | self.need(ry), tag, (rx, ry))

    def uni(self, tmpl, rx, pred, need=None, tag=""):
        text = cap(tmpl(self.rtext(rx)))
        ent = self.ent

        def fn(w):
            return pred(w, ent(w, rx))
        return Clue(text, fn, set(need or self.rel_need) | self.need(rx), tag)

    # ---------- attribute clues
    def attr_clues(self, w, rng):
        out = []
        for i, at in enumerate(self.attrs):
            s = STG[i]
            for e in range(self.n):
                v = w[s][e]
                out.append(Clue(f"{cap(self.en(e))} {at.pred.format(v=at.vals[v])}.",
                                (lambda ww, s=s, e=e, v=v: ww[s][e] == v), {s}, "direct"))
                for v2 in rng.sample([u for u in range(self.n) if u != v], 2):
                    out.append(Clue(f"{cap(self.en(e))} {at.neg.format(v=at.vals[v2])}.",
                                    (lambda ww, s=s, e=e, v2=v2: ww[s][e] != v2), {s}, "neg"))
        if len(self.attrs) == 2:
            a0, a1 = self.attrs
            for e in range(self.n):
                v0, v1 = w[A][e], w[C][e]
                out.append(Clue(f"{cap(a0.ref.format(v=a0.vals[v0]))} {a1.pred.format(v=a1.vals[v1])}.",
                                (lambda ww, v0=v0, v1=v1: ww[C][ww[A].index(v0)] == v1), {A, C}, "link"))
                v1b = rng.choice([u for u in range(self.n) if u != v1])
                out.append(Clue(f"{cap(a0.ref.format(v=a0.vals[v0]))} {a1.neg.format(v=a1.vals[v1b])}.",
                                (lambda ww, v0=v0, v1b=v1b: ww[C][ww[A].index(v0)] != v1b), {A, C}, "neg"))
        return out

    def pool(self, w, rng, pa=0.35):
        return self.rel_clues(w, rng, pa) + self.attr_clues(w, rng)

    # ---------- solution text
    def attr_suffix(self, w, e):
        if not self.attrs:
            return ""
        return " (" + ", ".join(self.attrs[i].vals[w[STG[i]][e]] for i in range(len(self.attrs))) + ")"

    # ---------- generic question factories
    def q_attr_of(self, w, rng):
        if not self.attrs:
            return None
        i = rng.randrange(len(self.attrs))
        at, s = self.attrs[i], STG[i]
        x = rng.randrange(self.n)
        nb = self.neighbours(w, x)
        corr = at.vals[w[s][x]]
        wr = [(at.vals[w[s][y]], f"attribute of {self.names[y]}, a neighbour of {self.names[x]}") for y in nb]
        wr += [(at.vals[w[s][y]], f"attribute of {self.names[y]}") for y in rng.sample(range(self.n), self.n) if y != x and y not in nb]
        return dict(q=at.q_of.format(X=self.en(x)), correct=corr, wrongs=wr[:3],
                    how=f"{cap(self.en(x))} {at.pred.format(v=corr)} in the solved arrangement.",
                    trap="Read the attribute off the solved arrangement, not off the nearest clue that mentions it.",
                    kind="conceptual")

    def q_attr_who(self, w, rng):
        if not self.attrs:
            return None
        i = rng.randrange(len(self.attrs))
        at, s = self.attrs[i], STG[i]
        v = rng.randrange(self.n)
        x = w[s].index(v)
        nb = self.neighbours(w, x)
        wr = [(self.names[y], "neighbour of the correct person") for y in nb]
        wr += [(self.names[y], "no clue links this person to that attribute") for y in rng.sample(range(self.n), self.n) if y != x and y not in nb]
        return dict(q=at.q_who.format(v=at.vals[v]), correct=self.names[x], wrongs=wr[:3],
                    how=f"{cap(self.en(x))} {at.pred.format(v=at.vals[v])}.",
                    trap="Attribute clues often name the attribute, not the person; resolve them only after positions are fixed.",
                    kind="conceptual")

    def text_shape(self, text):
        t = text
        for a in self.attrs:
            for v in a.vals:
                t = t.replace(v, "#")
        for nm in self.names:
            t = re.sub(r"\b" + re.escape(nm) + r"\b", "@", t)
        return t

    def self_ref(self, c, w):
        return c.refs is not None and self.ent(w, c.refs[0]) == self.ent(w, c.refs[1])

    def q_stmt(self, w, rng, clues, want_true=True):
        used = {c.text for c in clues}
        trues = [c for c in self.pool(w, rng, 0.4) if c.tag != "direct" and c.text not in used and c.fn(w)]
        falses, seen = [], set()
        for _ in range(40):
            w2 = self.rand_world(rng)
            for c in self.pool(w2, rng, 0.4):
                if c.tag != "direct" and not c.fn(w) and c.text not in seen and c.text not in used and not self.self_ref(c, w):
                    seen.add(c.text)
                    falses.append(c)
        if len(trues) < 3 or len(falses) < 3:
            return None
        for _ in range(40):
            if want_true:
                corr, others_pool = rng.choice(trues), falses
                err = "false in the solved arrangement"
            else:
                corr, others_pool = rng.choice(falses), trues
                err = "this statement is true in the solved arrangement"
            cs = self.text_shape(corr.text)
            same = [c for c in others_pool if self.text_shape(c.text) == cs]
            diff = [c for c in others_pool if self.text_shape(c.text) != cs]
            pick = rng.sample(same, 1) if same else []
            shapes = {cs}
            rng.shuffle(diff)
            diff.sort(key=lambda c: abs(len(c.text) - len(corr.text) - 2))
            for c in diff:
                if len(pick) == 3:
                    break
                sh = self.text_shape(c.text)
                if sh not in shapes:
                    shapes.add(sh)
                    pick.append(c)
            for c in diff:
                if len(pick) == 3:
                    break
                if c not in pick:
                    pick.append(c)
            texts = [corr.text] + [c.text for c in pick]
            if len(pick) == 3 and len(set(texts)) == 4 and not length_cue(texts, corr.text):
                break
        others = [(c.text, c) for c in pick]
        assert corr.fn(w) == want_true and all(o[1].fn(w) != want_true for o in others)
        q = "Which of the following statements is true?" if want_true else "Which of the following statements is NOT true?"
        return dict(q=q, correct=corr.text, wrongs=[(o[0], err) for o in others],
                    how=("Only this statement holds in the unique arrangement; each of the others contradicts it."
                         if want_true else "This statement fails in the unique arrangement; the other three hold."),
                    trap="Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.",
                    kind="statement")

    def q_odd_pairs(self, w, rng):
        n = self.n
        offs = {}
        for x in range(n):
            for y in range(n):
                if x != y:
                    o = self.offset(w, x, y)
                    if o is not None:
                        offs.setdefault(o, []).append((x, y))
        cands = [o for o, prs in offs.items() if len({a for a, b in prs}) >= 3 and self.off_ok(o)]
        rng.shuffle(cands)
        for o in cands:
            prs = rng.sample(offs[o], len(offs[o]))
            pick, used = [], set()
            for a, b in prs:
                if a not in used and b not in used:
                    pick.append((a, b))
                    used |= {a, b}
                if len(pick) == 3:
                    break
            if len(pick) < 3:
                continue
            odd = [(x, y) for x in range(n) for y in range(n) if x != y and x not in {a for a, _ in pick}
                   and self.offset(w, x, y) is not None and self.off_mag(self.offset(w, x, y)) != self.off_mag(o)]
            if not odd:
                continue
            ox, oy = rng.choice(odd)
            allp = pick + [(ox, oy)]
            vals = [self.offset(w, a, b) for a, b in allp]
            assert vals.count(o) == 3 and vals[3] != o
            fmt = lambda pr: f"{self.names[pr[0]]} – {self.names[pr[1]]}"
            return dict(q="In each pair below, the second member bears a certain positional relation to the first. "
                          "Three of the four pairs are alike in that relation and so form a group. Which pair does not belong to the group?",
                        correct=fmt((ox, oy)),
                        wrongs=[(fmt(pr), "belongs to the group: " + self.off_text(o)) for pr in pick],
                        how=f"In three pairs the second member is {self.off_text(o)} the first; in {fmt((ox, oy))} it is {self.off_text(vals[3])}.",
                        trap="Measure every pair from the first member's own position (and facing); do not mix up the direction.",
                        kind="conceptual")
        return None

    def q_odd_cat(self, w, rng):
        cats = self.cats(w)
        rng.shuffle(cats)
        for name, pred in cats:
            ins = [e for e in range(self.n) if pred(e)]
            outs = [e for e in range(self.n) if not pred(e)]
            if len(ins) < 3 or not outs:
                continue
            for _ in range(20):
                three = rng.sample(ins, 3)
                odd = rng.choice(outs)
                four = three + [odd]
                ok = True
                for n2, p2 in cats:        # no other category may split the four as 3-1 with a different odd one
                    if n2 == name:
                        continue
                    t = [e for e in four if p2(e)]
                    f = [e for e in four if not p2(e)]
                    if (len(t) == 3 and f[0] != odd) or (len(f) == 3 and t[0] != odd):
                        ok = False
                        break
                if ok:
                    return dict(q="Three of the following four are alike in a certain way based on their positions in the arrangement "
                                  "and so form a group. Which one does not belong to that group?",
                                correct=self.names[odd],
                                wrongs=[(self.names[e], f"belongs to the group ({name})") for e in three],
                                how=f"{', '.join(self.names[e] for e in three)} are all {name}; {self.names[odd]} is not.",
                                trap="Look for the positional property the three share, not for the letters' alphabetical pattern.",
                                kind="conceptual")
        return None

    def ent_opts(self, corr_e, cands, fill_err, exclude=()):
        """cands: [(entity, error)] in priority order; filled with other entities (never the reference person)."""
        seen, wr = {corr_e} | set(exclude), []
        for e, err in cands:
            if e is not None and e not in seen:
                seen.add(e)
                wr.append((self.names[e], err))
        for e in range(self.n):
            if len(wr) >= 3:
                break
            if e not in seen:
                seen.add(e)
                wr.append((self.names[e], fill_err))
        return wr[:3]

    def cats(self, w):
        return []

    def off_ok(self, o):
        return self.off_mag(o) >= 1


# =====================================================================================
#  Ordered line (1-D): row facing north, floors, box stack, days, clock slots, dates, years, heights
# =====================================================================================
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TIMES = {5: [10, 11, 12, 14, 15], 6: [9, 10, 11, 12, 14, 15], 7: [9, 10, 11, 12, 14, 15, 16], 8: [9, 10, 11, 12, 14, 15, 16, 17]}


def tlabel(h):
    return "12 noon" if h == 12 else (f"{h} a.m." if h < 12 else f"{h-12} p.m.")


class Line(Geo):
    def __init__(self, kind, names, attr_keys=(), rng=None, months=None, dates=None, year0=2015):
        super().__init__(names, attr_keys, rng)
        self.kind = kind
        n = self.n
        self.val = list(range(n))
        self.grp = None
        if kind == "box":
            self.prefix, self.unit_pl = "box ", "boxes"
        if kind == "time":
            self.val = TIMES[n]
        if kind == "month":
            self.months, self.dates = months, dates
            self.slots = [(m, d) for m in months for d in dates]
            assert len(self.slots) == n
            self.grp = [i // len(dates) for i in range(n)]
        if kind == "year":
            self.years = [year0 + i for i in range(n)]
            self.val = self.years
        self.V = self._vocab()

    def label(self, i):
        k, n = self.kind, self.n
        return {"row": f"{ordn(i+1)} from the left end", "floor": f"Floor {i+1}", "box": f"{ordn(i+1)} from the bottom",
                "day": DAYS[i] if k == "day" else "", "time": tlabel(self.val[i]) if k == "time" else "",
                "month": f"{self.slots[i][1]} {self.slots[i][0]}" if k == "month" else "",
                "year": str(self.val[i]), "height": f"{ordn(n-i)} tallest"}[k]

    def _vocab(self):
        k, n = self.kind, self.n
        pl = lambda m, sg, pl_: sg if m == 1 else pl_
        V = {}
        if k == "row":
            V.update(
                intro=lambda: f"{cap(NUMW[n])} persons – {lst(self.names)} – sit in a straight row, all facing north.",
                hi1=lambda X, Y: f"{X} sits immediately to the right of {Y}.",
                lo1=lambda X, Y: f"{X} sits immediately to the left of {Y}.",
                hik=lambda X, Y, q: f"{X} sits {ORD[q]} to the right of {Y}.",
                lok=lambda X, Y, q: f"{X} sits {ORD[q]} to the left of {Y}.",
                btw=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'person sits', 'persons sit')} between {X} and {Y}.",
                btwd=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'person sits', 'persons sit')} between {X} and {Y}, and {X} is to the right of {Y}.",
                adj=lambda X, Y: f"{X} sits adjacent to {Y}.",
                nadj=lambda X, Y: f"{X} does not sit adjacent to {Y}.",
                some=lambda X, Y: f"{X} sits somewhere to the right of {Y}.",
                end=lambda X: f"{X} sits at one of the extreme ends.",
                nend=lambda X: f"{X} does not sit at either extreme end.",
                top=lambda X: f"{X} sits at the extreme right end.",
                bot=lambda X: f"{X} sits at the extreme left end.",
                at=lambda X, i: f"{X} sits {ORD[i+1]} from the left end." if i < n / 2 else f"{X} sits {ORD[n-i]} from the right end.",
                asmany=lambda X, Y: f"As many persons sit to the right of {X} as to the left of {Y}.",
                q_hi=lambda X, q: f"Who sits {'immediately' if q == 1 else ORD[q]} to the right of {X}?",
                q_lo=lambda X, q: f"Who sits {'immediately' if q == 1 else ORD[q]} to the left of {X}?",
                q_at=lambda i: ("Who sits at the extreme left end?" if i == 0 else "Who sits at the extreme right end?" if i == n - 1 else
                                f"Who sits {ORD[i+1]} from the left end?" if i < n / 2 else f"Who sits {ORD[n-i]} from the right end?"),
                q_slot=lambda X: f"What is the position of {X} from the left end of the row?",
                q_btw=lambda X, Y: f"How many persons sit between {X} and {Y}?",
                q_cnt=lambda X: f"How many persons sit to the right of {X}?",
                hi_word="to the right of", lo_word="to the left of", sol_head="Left to right")
        elif k == "floor":
            V.update(
                intro=lambda: (f"{cap(NUMW[n])} persons – {lst(self.names)} – live on the {NUMW[n]} floors of a building, one person per floor. "
                               f"The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered {n}."),
                hi1=lambda X, Y: f"{X} lives on the floor immediately above {Y}.",
                lo1=lambda X, Y: f"{X} lives on the floor immediately below {Y}.",
                hik=lambda X, Y, q: f"{X} lives {NUMW[q]} floors above {Y}.",
                lok=lambda X, Y, q: f"{X} lives {NUMW[q]} floors below {Y}.",
                btw=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'person lives', 'persons live')} between {X} and {Y}.",
                btwd=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'person lives', 'persons live')} between {X} and {Y}, and {X} lives above {Y}.",
                adj=lambda X, Y: f"{X} and {Y} live on adjacent floors.",
                nadj=lambda X, Y: f"{X} and {Y} do not live on adjacent floors.",
                some=lambda X, Y: f"{X} lives on a floor somewhere above {Y}.",
                end=lambda X: f"{X} lives either on the topmost floor or on the lowermost floor.",
                nend=lambda X: f"{X} lives neither on the topmost floor nor on the lowermost floor.",
                top=lambda X: f"{X} lives on the topmost floor.",
                bot=lambda X: f"{X} lives on the lowermost floor.",
                at=lambda X, i: f"{X} lives on floor {i+1}.",
                props=[(lambda X: f"{X} lives on an even-numbered floor.", lambda i: (i + 1) % 2 == 0),
                       (lambda X: f"{X} lives on an odd-numbered floor.", lambda i: (i + 1) % 2 == 1)],
                asmany=lambda X, Y: f"The number of persons living above {X} is the same as the number of persons living below {Y}.",
                q_hi=lambda X, q: f"Who lives on the floor immediately above {X}?" if q == 1 else f"Who lives {NUMW[q]} floors above {X}?",
                q_lo=lambda X, q: f"Who lives on the floor immediately below {X}?" if q == 1 else f"Who lives {NUMW[q]} floors below {X}?",
                q_at=lambda i: f"Who lives on floor {i+1}?",
                q_slot=lambda X: f"On which floor does {X} live?",
                q_btw=lambda X, Y: f"How many persons live between {X} and {Y}?",
                q_cnt=lambda X: f"How many persons live above {X}?",
                hi_word="above", lo_word="below", sol_head="Floor 1 (lowest) upwards")
        elif k == "box":
            V.update(
                intro=lambda: (f"{cap(NUMW[n])} boxes – {lst(self.names)} – are placed one above another in a single stack. "
                               f"Position 1 is at the bottom and position {n} is at the top."),
                hi1=lambda X, Y: f"{X} is placed immediately above {Y}.",
                lo1=lambda X, Y: f"{X} is placed immediately below {Y}.",
                btw=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'box is', 'boxes are')} placed between {X} and {Y}.",
                btwd=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'box is', 'boxes are')} placed between {X} and {Y}, and {X} is above {Y}.",
                adj=lambda X, Y: f"{X} and {Y} are placed one directly on the other.",
                nadj=lambda X, Y: f"{X} is not placed adjacent to {Y}.",
                some=lambda X, Y: f"{X} is placed somewhere above {Y}.",
                end=lambda X: f"{X} is placed either at the top or at the bottom.",
                nend=lambda X: f"{X} is placed neither at the top nor at the bottom.",
                top=lambda X: f"{X} is placed at the top.",
                bot=lambda X: f"{X} is placed at the bottom.",
                at=lambda X, i: f"{X} is placed {ORD[i+1]} from the bottom." if i < n / 2 else f"{X} is placed {ORD[n-i]} from the top.",
                props=[(lambda X: f"{X} is placed at an even-numbered position.", lambda i: (i + 1) % 2 == 0),
                       (lambda X: f"{X} is placed at an odd-numbered position.", lambda i: (i + 1) % 2 == 1)],
                asmany=lambda X, Y: f"The number of boxes above {X} is the same as the number of boxes below {Y}.",
                q_hi=lambda X, q: f"Which box is placed immediately above {X}?" if q == 1 else None,
                q_lo=lambda X, q: f"Which box is placed immediately below {X}?" if q == 1 else None,
                q_at=lambda i: ("Which box is placed at the bottom?" if i == 0 else "Which box is placed at the top?" if i == n - 1 else
                                f"Which box is placed {ORD[i+1]} from the bottom?" if i < n / 2 else f"Which box is placed {ORD[n-i]} from the top?"),
                q_slot=lambda X: f"At which position from the bottom is {X} placed?",
                q_btw=lambda X, Y: f"How many boxes are placed between {X} and {Y}?",
                q_cnt=lambda X: f"How many boxes are placed above {X}?",
                hi_word="above", lo_word="below", sol_head="Bottom (position 1) upwards")
        elif k == "day":
            last = DAYS[n - 1]
            V.update(
                intro=lambda: (f"{cap(NUMW[n])} persons – {lst(self.names)} – each give a talk on a different day of the same week, "
                               f"from Monday to {last}, one talk per day."),
                hi1=lambda X, Y: f"{X} gives a talk on the day immediately after {Y}.",
                lo1=lambda X, Y: f"{X} gives a talk on the day immediately before {Y}.",
                hik=lambda X, Y, q: f"{X} gives a talk {NUMW[q]} days after {Y}.",
                lok=lambda X, Y, q: f"{X} gives a talk {NUMW[q]} days before {Y}.",
                btw=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'person gives a talk', 'persons give talks')} between {X} and {Y}.",
                btwd=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'person gives a talk', 'persons give talks')} between {X} and {Y}, with {X} coming after {Y}.",
                adj=lambda X, Y: f"{X} and {Y} give talks on consecutive days.",
                nadj=lambda X, Y: f"{X} and {Y} do not give talks on consecutive days.",
                some=lambda X, Y: f"{X} gives a talk on some day after {Y}.",
                end=lambda X: f"{X} gives a talk either on Monday or on {last}.",
                nend=lambda X: f"{X} gives a talk neither on Monday nor on {last}.",
                top=lambda X: f"{X} gives a talk on {last}.",
                bot=lambda X: f"{X} gives a talk on Monday.",
                at=lambda X, i: f"{X} gives a talk on {DAYS[i]}.",
                props=[(lambda X: f"{X} gives a talk on a day after Wednesday.", lambda i: i > 2),
                       (lambda X: f"{X} gives a talk on a day before Thursday.", lambda i: i < 3)]
                + ([(lambda X: f"{X} gives a talk on a weekend day.", lambda i: i >= 5)] if n >= 6 else []),
                asmany=lambda X, Y: f"As many persons give talks after {X} as before {Y}.",
                q_hi=lambda X, q: f"Who gives a talk on the day immediately after {X}?" if q == 1 else f"Who gives a talk {NUMW[q]} days after {X}?",
                q_lo=lambda X, q: f"Who gives a talk on the day immediately before {X}?" if q == 1 else f"Who gives a talk {NUMW[q]} days before {X}?",
                q_at=lambda i: f"Who gives a talk on {DAYS[i]}?",
                q_slot=lambda X: f"On which day does {X} give a talk?",
                q_btw=lambda X, Y: f"How many persons give talks between {X} and {Y}?",
                q_cnt=lambda X: f"How many persons give talks after {X}?",
                hi_word="after", lo_word="before", sol_head="Monday onwards")
        elif k == "time":
            ts = [tlabel(h) for h in self.val]
            V.update(
                intro=lambda: (f"{cap(NUMW[n])} persons – {lst(self.names)} – meet a counsellor one at a time on the same day. "
                               f"Each meeting lasts one hour and starts at one of these times: {lst(ts)} "
                               f"No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m."),
                hi1=lambda X, Y: f"{X} meets the counsellor in the slot immediately after {Y}.",
                lo1=lambda X, Y: f"{X} meets the counsellor in the slot immediately before {Y}.",
                hik=lambda X, Y, q: f"{X} meets the counsellor exactly {NUMW[q]} hours after {Y}.",
                lok=lambda X, Y, q: f"{X} meets the counsellor exactly {NUMW[q]} hours before {Y}.",
                btw=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'person meets', 'persons meet')} the counsellor between {X} and {Y}.",
                btwd=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'person meets', 'persons meet')} the counsellor between {X} and {Y}, with {X} meeting later than {Y}.",
                adj=lambda X, Y: f"{X} and {Y} have consecutive slots.",
                nadj=lambda X, Y: f"{X} and {Y} do not have consecutive slots.",
                some=lambda X, Y: f"{X} meets the counsellor at some time after {Y}.",
                end=lambda X: f"{X} has either the first or the last slot.",
                nend=lambda X: f"{X} has neither the first nor the last slot.",
                top=lambda X: f"{X} has the last slot of the day.",
                bot=lambda X: f"{X} has the first slot of the day.",
                at=lambda X, i: f"{X} meets the counsellor at {ts[i]}.",
                props=[(lambda X: f"{X} meets the counsellor before noon.", lambda i: self.val[i] < 12),
                       (lambda X: f"{X} meets the counsellor after the lunch break.", lambda i: self.val[i] >= 14)],
                asmany=lambda X, Y: f"As many persons meet the counsellor after {X} as before {Y}.",
                q_hi=lambda X, q: f"Who meets the counsellor in the slot immediately after {X}?" if q == 1 else f"Who meets the counsellor exactly {NUMW[q]} hours after {X}?",
                q_lo=lambda X, q: f"Who meets the counsellor in the slot immediately before {X}?" if q == 1 else f"Who meets the counsellor exactly {NUMW[q]} hours before {X}?",
                q_at=lambda i: f"Who meets the counsellor at {ts[i]}?",
                q_slot=lambda X: f"At what time does {X} meet the counsellor?",
                q_btw=lambda X, Y: f"How many persons meet the counsellor between {X} and {Y}?",
                q_cnt=lambda X: f"How many persons meet the counsellor after {X}?",
                hi_word="after", lo_word="before", sol_head="Earliest to latest")
        elif k == "month":
            ms, ds = self.months, self.dates
            mdays = {"January": 31, "February": 28, "March": 31, "April": 30, "May": 31, "June": 30, "July": 31,
                     "August": 31, "September": 30, "October": 31, "November": 30, "December": 31}
            dtxt = lst([ordn(d) for d in ds]) if len(ds) > 1 else ordn(ds[0])
            props = [(lambda X: f"{X} visits in a month that has 31 days.", lambda i: mdays[self.slots[i][0]] == 31),
                     (lambda X: f"{X} visits in a month that has 30 days.", lambda i: mdays[self.slots[i][0]] == 30)]
            if len(ds) > 1:
                for d in ds:
                    props.append((lambda X, d=d: f"{X} visits on the {ordn(d)} of a month.", lambda i, d=d: self.slots[i][1] == d))
            mid = ms[len(ms) // 2]
            props.append((lambda X, mid=mid: f"{X} visits before {mid}.", lambda i, mid=mid: ms.index(self.slots[i][0]) < ms.index(mid)))
            V.update(
                intro=lambda: (f"{cap(NUMW[n])} persons – {lst(self.names)} – visit a museum on {NUMW[n]} different dates of the same year: "
                               f"the {dtxt} of each of {lst(ms)}. No two persons visit on the same date."),
                hi1=lambda X, Y: f"{X} visits immediately after {Y}.",
                lo1=lambda X, Y: f"{X} visits immediately before {Y}.",
                btw=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'person visits', 'persons visit')} between {X} and {Y}.",
                btwd=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'person visits', 'persons visit')} between {X} and {Y}, with {X} visiting later than {Y}.",
                some=lambda X, Y: f"{X} visits on some date after {Y}.",
                end=lambda X: f"{X} is either the first or the last to visit.",
                nend=lambda X: f"{X} is neither the first nor the last to visit.",
                top=lambda X: f"{X} is the last to visit.",
                bot=lambda X: f"{X} is the first to visit.",
                at=lambda X, i: f"{X} visits on {self.slots[i][1]} {self.slots[i][0]}.",
                props=props,
                same=lambda X, Y: f"{X} and {Y} visit in the same month.",
                nsame=lambda X, Y: f"{X} and {Y} do not visit in the same month.",
                asmany=lambda X, Y: f"As many persons visit after {X} as before {Y}.",
                q_hi=lambda X, q: f"Who visits immediately after {X}?" if q == 1 else None,
                q_lo=lambda X, q: f"Who visits immediately before {X}?" if q == 1 else None,
                q_at=lambda i: f"Who visits on {self.slots[i][1]} {self.slots[i][0]}?",
                q_slot=lambda X: f"On which date does {X} visit?",
                q_btw=lambda X, Y: f"How many persons visit between {X} and {Y}?",
                q_cnt=lambda X: f"How many persons visit after {X}?",
                q_same=lambda X: f"Who visits in the same month as {X}?",
                hi_word="after", lo_word="before", sol_head="Chronological order")
        elif k == "year":
            ys = self.years
            V.update(
                intro=lambda: (f"{cap(NUMW[n])} persons – {lst(self.names)} – joined a company in {NUMW[n]} different years from "
                               f"{ys[0]} to {ys[-1]}, one person per year."),
                hi1=lambda X, Y: f"{X} joined in the year immediately after {Y}.",
                lo1=lambda X, Y: f"{X} joined in the year immediately before {Y}.",
                hik=lambda X, Y, q: f"{X} joined exactly {NUMW[q]} years after {Y}.",
                lok=lambda X, Y, q: f"{X} joined exactly {NUMW[q]} years before {Y}.",
                btw=lambda X, Y, m: f"Only {NUMW[m]} {pl(m, 'person joined', 'persons joined')} between {X} and {Y}.",
                adj=lambda X, Y: f"{X} and {Y} joined in consecutive years.",
                nadj=lambda X, Y: f"{X} and {Y} did not join in consecutive years.",
                some=lambda X, Y: f"{X} joined later than {Y}.",
                end=lambda X: f"{X} joined either in {ys[0]} or in {ys[-1]}.",
                top=lambda X: f"{X} joined in {ys[-1]}.",
                bot=lambda X: f"{X} joined in {ys[0]}.",
                at=lambda X, i: f"{X} joined in {ys[i]}.",
                props=[(lambda X: f"{X} joined in an even-numbered year.", lambda i: ys[i] % 2 == 0),
                       (lambda X: f"{X} joined in an odd-numbered year.", lambda i: ys[i] % 2 == 1)],
                asmany=lambda X, Y: f"As many persons joined after {X} as before {Y}.",
                q_hi=lambda X, q: f"Who joined in the year immediately after {X}?" if q == 1 else f"Who joined exactly {NUMW[q]} years after {X}?",
                q_lo=lambda X, q: f"Who joined in the year immediately before {X}?" if q == 1 else f"Who joined exactly {NUMW[q]} years before {X}?",
                q_at=lambda i: f"Who joined in {ys[i]}?",
                q_slot=lambda X: f"In which year did {X} join?",
                q_btw=lambda X, Y: f"How many persons joined between {X} and {Y}?",
                q_cnt=lambda X: f"How many persons joined after {X}?",
                hi_word="after", lo_word="before", sol_head="Earliest to latest")
        elif k == "height":
            V.update(
                intro=lambda: f"{cap(NUMW[n])} persons – {lst(self.names)} – are all of different heights.",
                btwd=lambda X, Y, m: f"Exactly {NUMW[m]} {pl(m, 'person is', 'persons are')} shorter than {X} but taller than {Y}.",
                some=lambda X, Y: f"{X} is taller than {Y}.",
                top=lambda X: f"{X} is the tallest.",
                bot=lambda X: f"{X} is the shortest.",
                at=lambda X, i: (f"{X} is the tallest." if i == n - 1 else f"{X} is the shortest." if i == 0 else
                                 f"{X} is the {ORD[n-i]} tallest." if n - i <= i + 1 else f"{X} is the {ORD[i+1]} shortest."),
                asmany=lambda X, Y: f"As many persons are taller than {X} as are shorter than {Y}.",
                q_at=lambda i: "Who is the tallest?" if i == n - 1 else ("Who is the shortest?" if i == 0 else f"Who is the {ORD[n-i]} tallest?"),
                hi_word="taller than", lo_word="shorter than", sol_head="Shortest to tallest")
        return V

    def intro(self):
        return " ".join([self.V["intro"]()] + [a.intro_text() for a in self.attrs])

    def neighbours(self, w, x):
        p = w[P]
        return [e for e in range(self.n) if abs(p[e] - p[x]) == 1]

    def describe(self, w):
        p = w[P]
        order = sorted(range(self.n), key=lambda e: p[e])
        return f"{self.V['sol_head']}: " + "; ".join(f"{self.label(p[e])} – {self.names[e]}{self.attr_suffix(w, e)}" for e in order)

    def rel_clues(self, w, rng, pa):
        V, n, p, val = self.V, self.n, w[P], self.val
        out = []
        pairs = [(x, y) for x in range(n) for y in range(n) if x != y]
        rng.shuffle(pairs)
        for x, y in pairs:
            rx, ry = self.ref_for(w, x, rng, pa), self.ref_for(w, y, rng, pa * 0.5)
            d = p[x] - p[y]
            dv = val[p[x]] - val[p[y]]
            if d == 1 and "hi1" in V:
                out.append(self.bin(V["hi1"], rx, ry, lambda w, a, b: w[P][a] - w[P][b] == 1))
            if d == -1 and "lo1" in V:
                out.append(self.bin(V["lo1"], rx, ry, lambda w, a, b: w[P][a] - w[P][b] == -1))
            if "hik" in V and 2 <= abs(dv) <= 5 and (self.kind != "row" or abs(d) <= 4):
                if dv > 0:
                    out.append(self.bin(lambda X, Y, q=dv: V["hik"](X, Y, q), rx, ry,
                                        lambda w, a, b, q=dv: val[w[P][a]] - val[w[P][b]] == q))
                else:
                    out.append(self.bin(lambda X, Y, q=-dv: V["lok"](X, Y, q), rx, ry,
                                        lambda w, a, b, q=dv: val[w[P][a]] - val[w[P][b]] == q))
            m = abs(d) - 1
            if m >= 1 and x < y and "btw" in V and rng.random() < 0.7:
                out.append(self.bin(lambda X, Y, m=m: V["btw"](X, Y, m), rx, ry,
                                    lambda w, a, b, m=m: abs(w[P][a] - w[P][b]) == m + 1))
            if m >= 1 and d > 0 and "btwd" in V and rng.random() < 0.6:
                out.append(self.bin(lambda X, Y, m=m: V["btwd"](X, Y, m), rx, ry,
                                    lambda w, a, b, m=m: w[P][a] - w[P][b] == m + 1))
            if x < y and "adj" in V and abs(d) == 1 and rng.random() < 0.5:
                out.append(self.bin(V["adj"], rx, ry, lambda w, a, b: abs(w[P][a] - w[P][b]) == 1))
            if x < y and "nadj" in V and abs(d) > 1 and rng.random() < 0.25:
                out.append(self.bin(V["nadj"], rx, ry, lambda w, a, b: abs(w[P][a] - w[P][b]) != 1))
            if d > 0 and "some" in V and rng.random() < 0.3:
                out.append(self.bin(V["some"], rx, ry, lambda w, a, b: w[P][a] > w[P][b]))
            if "asmany" in V and n - 1 - p[x] == p[y]:
                out.append(self.bin(V["asmany"], rx, ry, lambda w, a, b: n - 1 - w[P][a] == w[P][b]))
            if self.grp and x < y and rng.random() < 0.6:
                g = self.grp
                if g[p[x]] == g[p[y]]:
                    out.append(self.bin(V["same"], rx, ry, lambda w, a, b: g[w[P][a]] == g[w[P][b]]))
                elif rng.random() < 0.4:
                    out.append(self.bin(V["nsame"], rx, ry, lambda w, a, b: g[w[P][a]] != g[w[P][b]]))
        for x in range(n):
            rx = self.ref_for(w, x, rng, pa)
            s = p[x]
            if s in (0, n - 1):
                if "end" in V:
                    out.append(self.uni(V["end"], rx, lambda w, a: w[P][a] in (0, n - 1)))
                out.append(self.uni(V["top"] if s == n - 1 else V["bot"], rx, lambda w, a, s=s: w[P][a] == s, tag="direct"))
            elif "nend" in V and rng.random() < 0.5:
                out.append(self.uni(V["nend"], rx, lambda w, a: w[P][a] not in (0, n - 1)))
            out.append(self.uni(lambda X, s=s: V["at"](X, s), rx, lambda w, a, s=s: w[P][a] == s, tag="direct"))
            for tf, pr in V.get("props", []):
                if pr(s) and rng.random() < 0.6:
                    out.append(self.uni(tf, rx, lambda w, a, pr=pr: pr(w[P][a])))
        return out

    # ----- questions
    def q_rel(self, w, rng, attr_ref=False):
        V, n, p, val = self.V, self.n, w[P], self.val
        inv = {p[e]: e for e in range(n)}
        vinv = {val[s]: s for s in range(n)}
        for _ in range(40):
            x = rng.randrange(n)
            q = rng.choice([1, 1, 2, 2, 3])
            up = rng.random() < 0.5
            tv = val[p[x]] + (q if up else -q)
            if tv not in vinv:
                continue
            ft = V["q_hi" if up else "q_lo"]
            if ft is None:
                continue
            rx = (-1, x)
            if attr_ref and self.attrs:
                rx = (0, w[A][x])
            qt = ft(self.rtext(rx), q)
            if qt is None:
                continue
            y = inv[vinv[tv]]
            rv = val[p[x]] - (q if up else -q)
            cands = [(inv[vinv[rv]] if rv in vinv else None, f"direction reversed ({V['lo_word' if up else 'hi_word']} instead of {V['hi_word' if up else 'lo_word']})")]
            if self.kind == "time" and q > 1:
                ss = p[x] + (q if up else -q)
                if 0 <= ss < n:
                    cands.insert(0, (inv[ss], "counted slots instead of clock hours (ignored the lunch gap)"))
            for dq, lab in ((1, "counted one place too far"), (-1, "counted one place short")):
                tv2 = val[p[x]] + (q + dq if up else -(q + dq))
                if q + dq >= 1 and tv2 in vinv:
                    cands.append((inv[vinv[tv2]], lab))
            wr = self.ent_opts(y, cands, "not at the required position", exclude=(x,))
            return dict(q=qt, correct=self.names[y], wrongs=wr,
                        how=f"{cap(self.rtext(rx))} is at {self.label(p[x])}; the person asked for is at {self.label(p[y])}, i.e. {self.names[y]}.",
                        trap="Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.",
                        kind="conceptual")
        return None

    def q_at(self, w, rng):
        n, p = self.n, w[P]
        inv = {p[e]: e for e in range(n)}
        i = rng.randrange(n)
        if self.kind == "row" and n % 2 == 1 and rng.random() < 0.5:
            i = n // 2
        cands = [(inv[n - 1 - i], "counted from the opposite end")]
        cands += [(inv[j], "off by one position") for j in (i + 1, i - 1) if 0 <= j < n]
        return dict(q=self.V["q_at"](i), correct=self.names[inv[i]], wrongs=self.ent_opts(inv[i], cands, "not at that position"),
                    how=f"{self.label(i)} is occupied by {self.names[inv[i]]}.",
                    trap="Check which end the count starts from.", kind="conceptual")

    def q_slot(self, w, rng):
        if "q_slot" not in self.V:
            return None
        n, p = self.n, w[P]
        x = rng.randrange(n)
        s = p[x]
        wr, seen = [], {s}
        for j, lab in ((n - 1 - s, "counted from the opposite end"), (s + 1, "off by one position"), (s - 1, "off by one position"),
                       (s + 2, "off by two positions"), (s - 2, "off by two positions")):
            if 0 <= j < n and j not in seen:
                seen.add(j)
                wr.append((self.label(j), lab))
        return dict(q=self.V["q_slot"](self.en(x)), correct=self.label(s), wrongs=wr[:3],
                    how=f"{cap(self.en(x))} is at {self.label(s)}.", trap="Read the position from the correct end.",
                    kind="conceptual")

    def q_btw(self, w, rng):
        if "q_btw" not in self.V:
            return None
        n, p = self.n, w[P]
        prs = [(x, y) for x in range(n) for y in range(x + 1, n) if abs(p[x] - p[y]) >= 2]
        x, y = rng.choice(prs)
        m = abs(p[x] - p[y]) - 1
        wr = [(numtxt(m + 1), "counted one of the two named persons"), (numtxt(m + 2), "counted both named persons")]
        wr.append((numtxt(m - 1), "counted one short") if m >= 2 else (numtxt(m + 3), "counted from the wrong end"))
        return dict(q=self.V["q_btw"](self.en(x), self.en(y)), correct=numtxt(m), wrongs=wr,
                    how=f"{cap(self.en(x))} is at {self.label(p[x])} and {self.en(y)} at {self.label(p[y])}; {m} position(s) lie strictly between them.",
                    trap="'Between' excludes both named persons.", kind="numerical")

    def q_cnt(self, w, rng):
        if "q_cnt" not in self.V:
            return None
        n, p = self.n, w[P]
        x = rng.choice([e for e in range(n) if 0 < p[e] < n - 1] or list(range(n)))
        c = n - 1 - p[x]
        wr, seen = [], {c}
        for v, lab in ((p[x], f"counted {self.V['lo_word']} instead of {self.V['hi_word']}"), (c + 1, "included the person named"),
                       (c - 1, "missed the extreme position"), (c + 2, "counted two extra")):
            if v >= 0 and v not in seen:
                seen.add(v)
                wr.append((numtxt(v), lab))
        return dict(q=self.V["q_cnt"](self.en(x)), correct=numtxt(c), wrongs=wr[:3],
                    how=f"{cap(self.en(x))} is at {self.label(p[x])}; {c} position(s) lie beyond it in that direction.",
                    trap="Count only the persons beyond the one named, in the stated direction.", kind="numerical")

    def q_same(self, w, rng):
        if not self.grp:
            return None
        p, g, n = w[P], self.grp, self.n
        x = rng.randrange(n)
        mates = [e for e in range(n) if e != x and g[p[e]] == g[p[x]]]
        if len(mates) != 1:
            return None
        y = mates[0]
        cands = [(e, "visits in the adjacent slot but a different month") for e in self.neighbours(w, x) if e != y]
        return dict(q=self.V["q_same"](self.en(x)), correct=self.names[y], wrongs=self.ent_opts(y, cands, "visits in a different month", exclude=(x,)),
                    how=f"{cap(self.en(x))} visits on {self.label(p[x])}; the other date of that month belongs to {self.names[y]}.",
                    trap="Consecutive visitors need not share a month.", kind="conceptual")

    def offset(self, w, x, y):
        return w[P][y] - w[P][x]

    def off_mag(self, o):
        return abs(o)

    def off_text(self, o):
        k, word = abs(o), (self.V["hi_word"] if o > 0 else self.V["lo_word"])
        if self.kind == "row":
            return ("immediately " if k == 1 else f"{ORD[k]} ") + word
        return f"{NUMW[k]} place{'s' if k > 1 else ''} {word}"

    def cats(self, w):
        n, p = self.n, w[P]
        cs = [("at an extreme position", lambda e: p[e] in (0, n - 1))]
        if self.kind in ("floor", "box", "year"):
            cs.append(("at even-numbered positions" if self.kind != "floor" else "on even-numbered floors", lambda e: (p[e] + 1) % 2 == 0))
            cs.append(("at odd-numbered positions" if self.kind != "floor" else "on odd-numbered floors", lambda e: (p[e] + 1) % 2 == 1))
        if self.kind == "time":
            cs.append(("scheduled before noon", lambda e: self.val[p[e]] < 12))
            cs.append(("scheduled after the lunch break", lambda e: self.val[p[e]] >= 14))
        if self.kind == "day":
            cs.append(("scheduled after Wednesday", lambda e: p[e] > 2))
            cs.append(("scheduled before Thursday", lambda e: p[e] < 3))
        if self.kind == "row":
            cs.append(("in the left half of the row", lambda e: p[e] < n // 2))
            cs.append(("in the right half of the row", lambda e: p[e] >= (n + 1) // 2))
        return cs


# =====================================================================================
#  Row facing both directions
# =====================================================================================
class RowMix(Geo):
    rel_need = (P, F)

    def f_domain(self):
        n = self.n
        return [f for f in itertools.product((0, 1), repeat=n) if 1 <= sum(f) <= n - 1]

    def rd(self, w, e):
        return 1 if w[F][e] == 0 else -1

    def intro(self):
        return " ".join([f"{cap(NUMW[self.n])} persons – {lst(self.names)} – sit in a straight row. Some of them face north and the others face south."]
                        + [a.intro_text() for a in self.attrs])

    def fw(self, f):
        return "north" if f == 0 else "south"

    def neighbours(self, w, x):
        p = w[P]
        return [e for e in range(self.n) if abs(p[e] - p[x]) == 1]

    def describe(self, w):
        p, f = w[P], w[F]
        order = sorted(range(self.n), key=lambda e: p[e])
        sfx = lambda e: "".join(", " + self.attrs[i].vals[w[STG[i]][e]] for i in range(len(self.attrs)))
        return "West to east: " + "; ".join(f"{self.names[e]} (faces {self.fw(f[e])}{sfx(e)})" for e in order)

    def rel_clues(self, w, rng, pa):
        n, p, f = self.n, w[P], w[F]
        out = []
        rd = self.rd
        pairs = [(x, y) for x in range(n) for y in range(n) if x != y]
        rng.shuffle(pairs)
        for x, y in pairs:
            rx, ry = self.ref_for(w, x, rng, pa), self.ref_for(w, y, rng, pa * 0.5)
            k = (p[x] - p[y]) * rd(w, y)          # x is k-th to the right of y (y's frame) if k>0
            if 1 <= abs(k) <= 3:
                side = "right" if k > 0 else "left"
                kk = abs(k)
                txt = (lambda X, Y, s=side: f"{X} sits immediately to the {s} of {Y}.") if kk == 1 else \
                      (lambda X, Y, s=side, kk=kk: f"{X} sits {ORD[kk]} to the {s} of {Y}.")
                out.append(self.bin(txt, rx, ry, lambda w, a, b, k=k: (w[P][a] - w[P][b]) * rd(w, b) == k))
            m = abs(p[x] - p[y]) - 1
            if x < y and m >= 1 and rng.random() < 0.5:
                out.append(self.bin(lambda X, Y, m=m: f"Only {NUMW[m]} {'person sits' if m == 1 else 'persons sit'} between {X} and {Y}.",
                                    rx, ry, lambda w, a, b, m=m: abs(w[P][a] - w[P][b]) == m + 1, need=(P,)))
            if x < y and abs(p[x] - p[y]) == 1 and rng.random() < 0.4:
                out.append(self.bin(lambda X, Y: f"{X} sits adjacent to {Y}.", rx, ry, lambda w, a, b: abs(w[P][a] - w[P][b]) == 1, need=(P,)))
            if x < y and rng.random() < 0.35:
                same = f[x] == f[y]
                out.append(self.bin((lambda X, Y: f"{X} and {Y} face the same direction.") if same else (lambda X, Y: f"{X} and {Y} face opposite directions."),
                                    rx, ry, (lambda w, a, b: w[F][a] == w[F][b]) if same else (lambda w, a, b: w[F][a] != w[F][b]), need=(F,)))
        for x in range(n):
            rx = self.ref_for(w, x, rng, pa)
            fx = f[x]
            out.append(self.uni(lambda X, fx=fx: f"{X} faces {self.fw(fx)}.", rx, lambda w, a, fx=fx: w[F][a] == fx, need=(F,), tag="face"))
            if p[x] in (0, n - 1):
                out.append(self.uni(lambda X: f"{X} sits at one of the extreme ends.", rx, lambda w, a: w[P][a] in (0, n - 1), need=(P,)))
            else:
                if rng.random() < 0.4:
                    out.append(self.uni(lambda X: f"{X} does not sit at either extreme end.", rx, lambda w, a: w[P][a] not in (0, n - 1), need=(P,)))
                nb = self.neighbours(w, x)
                fs = {f[e] for e in nb}
                if len(fs) == 1:
                    ff = fs.pop()
                    out.append(self.uni(lambda X, ff=ff: f"Both immediate neighbours of {X} face {self.fw(ff)}.", rx,
                                        lambda w, a, ff=ff: 0 < w[P][a] < n - 1 and all(w[F][e] == ff for e in range(n) if abs(w[P][e] - w[P][a]) == 1)))
                else:
                    out.append(self.uni(lambda X: f"The immediate neighbours of {X} face opposite directions.", rx,
                                        lambda w, a: 0 < w[P][a] < n - 1 and len({w[F][e] for e in range(n) if abs(w[P][e] - w[P][a]) == 1}) == 2))
        ends = [e for e in range(n) if p[e] in (0, n - 1)]
        same = f[ends[0]] == f[ends[1]]
        out.append(Clue("The persons at the two extreme ends face the same direction." if same else "The persons at the two extreme ends face opposite directions.",
                        (lambda w: (lambda es: (w[F][es[0]] == w[F][es[1]]) == same)([e for e in range(n) if w[P][e] in (0, n - 1)])), {P, F}))
        cn = n - sum(f)
        out.append(Clue(f"Exactly {NUMW[cn]} {'person faces' if cn == 1 else 'persons face'} north.", (lambda w, cn=cn: n - sum(w[F]) == cn), {F}))
        return out

    def q_rel(self, w, rng, attr_ref=False):
        n, p = self.n, w[P]
        inv = {p[e]: e for e in range(n)}
        xs = rng.sample(range(n), n)
        xs.sort(key=lambda e: -w[F][e])           # prefer south-facing reference persons (the classic trap)
        for x in xs:
            for k in rng.sample([1, 2, 2, 3], 4):
                side = rng.choice([1, -1])
                t = p[x] + side * k * self.rd(w, x)
                if not 0 <= t < n:
                    continue
                y = inv[t]
                sname = "right" if side > 0 else "left"
                rx = (0, w[A][x]) if attr_ref and self.attrs else (-1, x)
                qt = f"Who sits {'immediately' if k == 1 else ORD[k]} to the {sname} of {self.rtext(rx)}?"
                naive = p[x] + side * k                        # as if x faced north
                rev = p[x] - side * k * self.rd(w, x)
                cands = []
                if w[F][x] == 1 and 0 <= naive < n:
                    cands.append((inv[naive], f"treated {self.names[x]} as facing north (viewer's {sname})"))
                if 0 <= rev < n:
                    cands.append((inv[rev], "opposite side taken"))
                for kk in (k + 1, k - 1):
                    tt = p[x] + side * kk * self.rd(w, x)
                    if kk >= 1 and 0 <= tt < n:
                        cands.append((inv[tt], "counted one place off"))
                return dict(q=qt, correct=self.names[y], wrongs=self.ent_opts(y, cands, "not at that position", exclude=(x,)),
                            how=f"{self.names[x]} faces {self.fw(w[F][x])}, so {self.names[x]}'s {sname} is towards the "
                                f"{'east' if side * self.rd(w, x) > 0 else 'west'}; counting {k} place(s) that way gives {self.names[y]}.",
                            trap="Right and left are taken from the reference person's own facing; a south-facing person's right is the viewer's left.",
                            kind="conceptual")
        return None

    def q_posrel(self, w, rng):
        n, p = self.n, w[P]
        for _ in range(40):
            x, y = rng.sample(range(n), 2)
            k = (p[x] - p[y]) * self.rd(w, y)
            if not 1 <= abs(k) <= 4:
                continue
            desc = lambda kk: ("Immediately to the " if abs(kk) == 1 else f"{cap(ORD[abs(kk)])} to the ") + ("right" if kk > 0 else "left")
            corr = desc(k)
            cands = [(desc(-k), "measured from the viewer's side / reversed"), (desc(k + (1 if k > 0 else -1)), "counted one place extra")]
            if abs(k) > 1:
                cands.append((desc(k - (1 if k > 0 else -1)), "counted one place short"))
            cands.append((desc(-(k + (1 if k > 0 else -1))), "reversed and off by one"))
            wr, seen = [], {corr}
            for t, e in cands:
                if t not in seen:
                    seen.add(t)
                    wr.append((t, e))
            return dict(q=f"What is the position of {self.names[x]} with respect to {self.names[y]}?", correct=corr, wrongs=wr[:3],
                        how=f"{self.names[y]} faces {self.fw(w[F][y])}; from {self.names[y]}'s own right-left, {self.names[x]} is {corr.lower()}.",
                        trap="Use the reference person's facing, not the viewer's.", kind="conceptual")
        return None

    def q_facecount(self, w, rng):
        n = self.n
        c = n - sum(w[F])
        wr = [(numtxt(v), lab) for v, lab in ((n - c, "counted south-facing persons"), (c + 1, "off by one"), (c - 1, "off by one"), (c + 2, "off by two"))
              if 0 <= v <= n and v != c]
        seen, out = set(), []
        for t, e in wr:
            if t not in seen:
                seen.add(t)
                out.append((t, e))
        return dict(q="How many persons face north?", correct=numtxt(c), wrongs=out[:3],
                    how=f"North-facing: {', '.join(self.names[e] for e in range(n) if w[F][e] == 0)}.",
                    trap="Fix every person's facing before counting.", kind="numerical")

    def q_ends(self, w, rng):
        n, p = self.n, w[P]
        inv = {p[e]: e for e in range(n)}
        corr = f"{self.names[inv[0]]} and {self.names[inv[n-1]]}"
        wr = [(f"{self.names[inv[1]]} and {self.names[inv[n-1]]}", "one person taken from the second position"),
              (f"{self.names[inv[0]]} and {self.names[inv[n-2]]}", "one person taken from the second position"),
              (f"{self.names[inv[1]]} and {self.names[inv[n-2]]}", "second-from-end persons")]
        return dict(q="Who sit at the two extreme ends of the row?", correct=corr, wrongs=wr,
                    how=f"Extreme ends: {corr}.", trap="Ends are fixed by the solved order, whatever the facings.", kind="conceptual")

    def q_btw(self, w, rng):
        n, p = self.n, w[P]
        prs = [(x, y) for x in range(n) for y in range(x + 1, n) if abs(p[x] - p[y]) >= 2]
        x, y = rng.choice(prs)
        m = abs(p[x] - p[y]) - 1
        wr = [(numtxt(m + 1), "counted one of the two named persons"), (numtxt(m + 2), "counted both named persons"),
              (numtxt(m - 1), "counted one short") if m >= 2 else (numtxt(m + 3), "miscounted")]
        return dict(q=f"How many persons sit between {self.names[x]} and {self.names[y]}?", correct=numtxt(m), wrongs=wr,
                    how=f"{m} person(s) sit strictly between them.", trap="'Between' excludes both named persons.", kind="numerical")

    def offset(self, w, x, y):
        return (w[P][y] - w[P][x]) * self.rd(w, x)

    def off_mag(self, o):
        return abs(o)

    def off_text(self, o):
        k = abs(o)
        return ("immediately" if k == 1 else ORD[k]) + " to the " + ("right" if o > 0 else "left") + " of"

    def cats(self, w):
        n, p, f = self.n, w[P], w[F]
        return [("facing north", lambda e: f[e] == 0), ("facing south", lambda e: f[e] == 1),
                ("seated at an extreme end", lambda e: p[e] in (0, n - 1))]


# =====================================================================================
#  Circle / square / rectangle
# =====================================================================================
class Circle(Geo):
    def __init__(self, names, attr_keys=(), rng=None, facing="in", shape="circle"):
        self.facing, self.shape = facing, shape
        super().__init__(names, attr_keys, rng)
        n = self.n
        if shape == "square":
            assert n in (4, 8)
        if shape == "rect":
            assert n == 6
        self.rel_need = (P, F) if facing == "mixed" else (P,)

    def p_domain(self):
        n = self.n
        allowed = {"circle": {0}, "square": {0, 1} if n == 8 else {0}, "rect": {0, 1, 2}}[self.shape]
        return [p for p in itertools.permutations(range(n)) if p[0] in allowed]

    def f_domain(self):
        if self.facing != "mixed":
            return None
        n = self.n
        return [f for f in itertools.product((0, 1), repeat=n) if 1 <= sum(f) <= n - 1]

    def rand_world(self, rng):
        return super().rand_world(rng)

    def fin(self, w, e):
        """True if e faces the centre."""
        if self.facing == "in":
            return True
        if self.facing == "out":
            return False
        if self.facing == "sq":
            return w[P][e] % 2 == 0
        return w[F][e] == 0

    def rd(self, w, e):
        return -1 if self.fin(w, e) else 1

    def intro(self):
        n = self.n
        who = f"{cap(NUMW[n])} persons – {lst(self.names)} –"
        if self.shape == "circle":
            base = f"{who} sit around a circular table"
        elif self.shape == "square":
            base = (f"{who} sit around a square table, one at each corner" if n == 4 else
                    f"{who} sit around a square table: four sit at the four corners and four sit one at the middle of each side")
        else:
            base = f"{who} sit around a rectangular table: two sit on each of the longer sides and one sits at each of the shorter sides"
        face = {"in": ", all facing the centre.", "out": ", all facing away from the centre.",
                "mixed": ". Some of them face the centre and the others face away from the centre.",
                "sq": ". Those at the corners face the centre and those at the middle of the sides face away from the centre."}[self.facing]
        return " ".join([base + face] + [a.intro_text() for a in self.attrs])

    def neighbours(self, w, x):
        p, n = w[P], self.n
        return [e for e in range(n) if (p[e] - p[x]) % n in (1, n - 1)]

    def describe(self, w):
        p, n = w[P], self.n
        order = sorted(range(n), key=lambda e: p[e])
        def tag(e):
            t = []
            if self.facing in ("mixed", "sq"):
                t.append("faces centre" if self.fin(w, e) else "faces outside")
            if self.shape == "square" and n == 8:
                t.append("corner" if p[e] % 2 == 0 else "middle of side")
            if self.shape == "rect":
                t.append("shorter side" if p[e] in (0, 3) else "longer side")
            return (" [" + ", ".join(t) + "]" if t else "") + self.attr_suffix(w, e)
        return f"Clockwise from {self.names[order[0]]}: " + "; ".join(f"{self.names[e]}{tag(e)}" for e in order)

    def kth(self, w, y, k):
        """seat k places to y's right (k<0: left)."""
        return (w[P][y] + k * self.rd(w, y)) % self.n

    def rel_clues(self, w, rng, pa):
        n, p = self.n, w[P]
        out = []
        rdn = self.rd
        half = n // 2
        pairs = [(x, y) for x in range(n) for y in range(n) if x != y]
        rng.shuffle(pairs)
        for x, y in pairs:
            rx, ry = self.ref_for(w, x, rng, pa), self.ref_for(w, y, rng, pa * 0.5)
            kr = ((p[x] - p[y]) * rdn(w, y)) % n          # x is kr-th to the right of y
            if n % 2 == 0 and kr == half:
                if x < y:
                    out.append(self.bin(lambda X, Y: f"{X} sits opposite {Y}.", rx, ry, lambda w, a, b: (w[P][a] - w[P][b]) % n == half, need=(P,)))
                continue
            k, side = (kr, "right") if kr < n - kr else (n - kr, "left")
            if k <= 3:
                sgn = 1 if side == "right" else -1
                txt = (lambda X, Y, s=side: f"{X} sits immediately to the {s} of {Y}.") if k == 1 else \
                      (lambda X, Y, s=side, k=k: f"{X} sits {ORD[k]} to the {s} of {Y}.")
                out.append(self.bin(txt, rx, ry, lambda w, a, b, k=k, sgn=sgn: w[P][a] == (w[P][b] + sgn * k * rdn(w, b)) % n))
                if k >= 2 and rng.random() < 0.3:
                    m = k - 1
                    out.append(self.bin(lambda X, Y, m=m, s=side: f"Only {NUMW[m]} {'person sits' if m == 1 else 'persons sit'} between {Y} and {X} when counted from the {s} of {Y}.",
                                        rx, ry, lambda w, a, b, k=k, sgn=sgn: w[P][a] == (w[P][b] + sgn * k * rdn(w, b)) % n))
            if x < y:
                adj = (p[x] - p[y]) % n in (1, n - 1)
                if adj and rng.random() < 0.4:
                    out.append(self.bin(lambda X, Y: f"{X} is an immediate neighbour of {Y}.", rx, ry,
                                        lambda w, a, b: (w[P][a] - w[P][b]) % n in (1, n - 1), need=(P,)))
                elif not adj and rng.random() < 0.25:
                    out.append(self.bin(lambda X, Y: f"{X} is not an immediate neighbour of {Y}.", rx, ry,
                                        lambda w, a, b: (w[P][a] - w[P][b]) % n not in (1, n - 1), need=(P,)))
                if self.facing == "mixed" and rng.random() < 0.3:
                    same = w[F][x] == w[F][y]
                    out.append(self.bin((lambda X, Y: f"{X} and {Y} face the same direction.") if same else (lambda X, Y: f"{X} and {Y} face opposite directions."),
                                        rx, ry, (lambda w, a, b: w[F][a] == w[F][b]) if same else (lambda w, a, b: w[F][a] != w[F][b]), need=(F,)))
        for x in range(n):
            rx = self.ref_for(w, x, rng, pa)
            if self.facing == "mixed":
                fi = w[F][x]
                out.append(self.uni((lambda X: f"{X} faces the centre.") if fi == 0 else (lambda X: f"{X} faces away from the centre."),
                                    rx, lambda w, a, fi=fi: w[F][a] == fi, need=(F,), tag="face"))
                nb = self.neighbours(w, x)
                fs = {w[F][e] for e in nb}
                if len(fs) == 1:
                    ff = fs.pop()
                    out.append(self.uni((lambda X: f"Both immediate neighbours of {X} face the centre.") if ff == 0 else
                                        (lambda X: f"Both immediate neighbours of {X} face away from the centre."), rx,
                                        lambda w, a, ff=ff: all(w[F][e] == ff for e in range(n) if (w[P][e] - w[P][a]) % n in (1, n - 1))))
                else:
                    out.append(self.uni(lambda X: f"The immediate neighbours of {X} face opposite directions.", rx,
                                        lambda w, a: len({w[F][e] for e in range(n) if (w[P][e] - w[P][a]) % n in (1, n - 1)}) == 2))
            if self.shape == "square" and n == 8:
                cor = p[x] % 2 == 0
                out.append(self.uni((lambda X: f"{X} sits at one of the corners.") if cor else (lambda X: f"{X} sits at the middle of one of the sides."),
                                    rx, lambda w, a, cor=cor: (w[P][a] % 2 == 0) == cor, need=(P,)))
            if self.shape == "rect":
                sh = p[x] in (0, 3)
                out.append(self.uni((lambda X: f"{X} sits at one of the shorter sides of the table.") if sh else (lambda X: f"{X} sits on one of the longer sides of the table."),
                                    rx, lambda w, a, sh=sh: (w[P][a] in (0, 3)) == sh, need=(P,)))
        if self.facing == "mixed":
            cn = n - sum(w[F])
            out.append(Clue(f"Exactly {NUMW[cn]} {'person faces' if cn == 1 else 'persons face'} the centre.", (lambda w, cn=cn: n - sum(w[F]) == cn), {F}))
        return out

    def q_rel(self, w, rng, attr_ref=False):
        n, p = self.n, w[P]
        inv = {p[e]: e for e in range(n)}
        xs = rng.sample(range(n), n)
        if self.facing in ("mixed", "sq", "out"):
            xs.sort(key=lambda e: self.fin(w, e))       # prefer outward-facing reference (trap)
        for x in xs:
            k = rng.choice([1, 2, 2, 3, 3]) if n >= 7 else rng.choice([1, 2])
            if n % 2 == 0 and k == n // 2:
                continue
            side = rng.choice([1, -1])
            y = inv[self.kth(w, x, side * k)]
            sname = "right" if side > 0 else "left"
            rx = (0, w[A][x]) if attr_ref and self.attrs else (-1, x)
            cands = [(inv[self.kth(w, x, -side * k)], "direction reversed")]
            if not self.fin(w, x):
                cands.insert(0, (inv[(p[x] + side * k * -1) % n], f"treated {self.names[x]} as facing the centre"))
            cands += [(inv[self.kth(w, x, side * (k + 1))], "counted one seat too far")]
            if k > 1:
                cands.append((inv[self.kth(w, x, side * (k - 1))], "counted one seat short"))
            cands = [(e, lab) for e, lab in cands if e != y]
            face = "faces the centre" if self.fin(w, x) else "faces away from the centre"
            return dict(q=f"Who sits {'immediately' if k == 1 else ORD[k]} to the {sname} of {self.rtext(rx)}?",
                        correct=self.names[y], wrongs=self.ent_opts(y, cands, "not at that seat", exclude=(x,)),
                        how=f"{self.names[x]} {face}, so {self.names[x]}'s {sname} runs "
                            f"{'clockwise' if side * self.rd(w, x) > 0 else 'anticlockwise'}; {k} seat(s) that way is {self.names[y]}.",
                        trap="For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.",
                        kind="conceptual")
        return None

    def q_opp(self, w, rng):
        n, p = self.n, w[P]
        if n % 2:
            return None
        inv = {p[e]: e for e in range(n)}
        x = rng.randrange(n)
        y = inv[(p[x] + n // 2) % n]
        cands = [(inv[(p[x] + n // 2 + 1) % n], "seat next to the opposite seat"), (inv[(p[x] + n // 2 - 1) % n], "seat next to the opposite seat")]
        return dict(q=f"Who sits opposite {self.names[x]}?", correct=self.names[y], wrongs=self.ent_opts(y, cands, "not opposite", exclude=(x,)),
                    how=f"The seat {n//2} places away from {self.names[x]} in either direction is {self.names[y]}'s.",
                    trap="Opposite means exactly half-way round the table.", kind="conceptual")

    def q_btwdir(self, w, rng):
        n, p = self.n, w[P]
        for _ in range(30):
            x, y = rng.sample(range(n), 2)
            side = rng.choice([1, -1])
            # steps from x towards x's `side` until y
            steps = next(s for s in range(1, n) if self.kth(w, x, side * s) == p[y])
            m = steps - 1
            other = n - 2 - m
            if m == other or m < 1:
                continue
            sname = "right" if side > 0 else "left"
            wr, seen = [], {numtxt(m)}
            for v, lab in ((other, "counted from the other side"), (m + 1, "counted one named person"), (m - 1, "counted one short"), (m + 2, "counted both named persons")):
                t = numtxt(v)
                if v >= 0 and t not in seen:
                    seen.add(t)
                    wr.append((t, lab))
            return dict(q=f"How many persons sit between {self.names[x]} and {self.names[y]} when counted from the {sname} of {self.names[x]}?",
                        correct=numtxt(m), wrongs=wr[:3],
                        how=f"Moving to {self.names[x]}'s {sname}, {m} person(s) are passed before reaching {self.names[y]}.",
                        trap="The count depends on the side; the other side gives n − 2 − m.", kind="numerical")
        return None

    def q_posrel(self, w, rng):
        n, p = self.n, w[P]
        for _ in range(40):
            x, y = rng.sample(range(n), 2)
            kr = ((p[x] - p[y]) * self.rd(w, y)) % n
            if n % 2 == 0 and kr == n // 2:
                continue
            k, side = (kr, 1) if kr < n - kr else (n - kr, -1)
            desc = lambda kk, s: ("Immediately to the " if kk == 1 else f"{cap(ORD[kk])} to the ") + ("right" if s > 0 else "left")
            truth = lambda kk, s: ((p[x] - p[y]) * self.rd(w, y)) % n == (s * kk) % n
            corr = desc(k, side)
            cands = [(k, -side, "direction reversed"), (k + 1, side, "counted one seat extra"), (k + 1, -side, "reversed and off by one")]
            if k > 1:
                cands.append((k - 1, side, "counted one seat short"))
            wr = [(desc(kk, s), e) for kk, s, e in cands if kk < n and not truth(kk, s)][:3]
            if len(wr) < 3 or len({t for t, _ in wr} | {corr}) < 4:
                continue
            face = "faces the centre" if self.fin(w, y) else "faces away from the centre"
            return dict(q=f"What is the position of {self.names[x]} with respect to {self.names[y]}?", correct=corr, wrongs=wr,
                        how=f"{self.names[y]} {face}; counted from {self.names[y]}'s own right/left, {self.names[x]} is {corr.lower()}.",
                        trap="Positions are always read from the reference person's facing.", kind="conceptual")
        return None

    def q_facecount(self, w, rng):
        if self.facing != "mixed":
            return None
        n = self.n
        c = sum(1 for e in range(n) if self.fin(w, e))
        cands = ((n - c, "counted those facing outside"), (c + 1, "off by one"), (c - 1, "off by one"), (c + 2, "off by two"))
        wr, seen = [], {c}
        for v, lab in cands:
            if 0 <= v <= n and v not in seen:
                seen.add(v)
                wr.append((numtxt(v), lab))
        return dict(q="How many persons face the centre?", correct=numtxt(c), wrongs=wr[:3],
                    how=f"Facing the centre: {', '.join(self.names[e] for e in range(n) if self.fin(w, e))}.",
                    trap="Fix every facing before counting.", kind="numerical")

    def offset(self, w, x, y):
        return ((w[P][y] - w[P][x]) * self.rd(w, x)) % self.n

    def off_mag(self, o):
        return min(o, self.n - o)

    def off_text(self, o):
        n = self.n
        if n % 2 == 0 and o == n // 2:
            return "opposite"
        k, s = (o, "right") if o < n - o else (n - o, "left")
        return ("immediately" if k == 1 else ORD[k]) + f" to the {s} of"

    def cats(self, w):
        n, p = self.n, w[P]
        cs = []
        if self.facing in ("mixed", "sq"):
            cs += [("facing the centre", lambda e: self.fin(w, e)), ("facing away from the centre", lambda e: not self.fin(w, e))]
        if self.shape == "square" and n == 8:
            cs += [("seated at corners", lambda e: p[e] % 2 == 0), ("seated at the middle of sides", lambda e: p[e] % 2 == 1)]
        if self.shape == "rect":
            cs += [("seated on the longer sides", lambda e: p[e] not in (0, 3)), ("seated at the shorter sides", lambda e: p[e] in (0, 3))]
        return cs


# =====================================================================================
#  Floor x flat grid (two flats per floor: Flat A to the west, Flat B to the east)
# =====================================================================================
class Grid(Geo):
    def __init__(self, names, floors, attr_keys=(), rng=None):
        super().__init__(names, attr_keys, rng)
        self.nf = floors
        assert self.n == 2 * floors

    def fl(self, c):
        return c // 2

    def ft(self, c):
        return c % 2

    def label(self, c):
        return f"Flat {'AB'[c % 2]}, floor {c // 2 + 1}"

    def intro(self):
        nf = self.nf
        return " ".join([f"{cap(NUMW[self.n])} persons – {lst(self.names)} – live in a {NUMW[nf]}-storey building, one person per flat. "
                         f"The lowermost floor is floor 1 and the topmost is floor {nf}. Each floor has two flats: Flat A on the west and Flat B on the east; "
                         f"Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B."]
                        + [a.intro_text() for a in self.attrs])

    def neighbours(self, w, x):
        c = w[P][x]
        return [e for e in range(self.n) if e != x and (abs(w[P][e] - c) == 2 or w[P][e] // 2 == c // 2)]

    def describe(self, w):
        p = w[P]
        rows = []
        for f in range(self.nf - 1, -1, -1):
            a = next(e for e in range(self.n) if p[e] == 2 * f)
            b = next(e for e in range(self.n) if p[e] == 2 * f + 1)
            rows.append(f"floor {f+1}: A – {self.names[a]}{self.attr_suffix(w, a)}, B – {self.names[b]}{self.attr_suffix(w, b)}")
        return "Top to bottom — " + "; ".join(rows)

    def rel_clues(self, w, rng, pa):
        n, p, nf = self.n, w[P], self.nf
        out = []
        pairs = [(x, y) for x in range(n) for y in range(n) if x != y]
        rng.shuffle(pairs)
        for x, y in pairs:
            rx, ry = self.ref_for(w, x, rng, pa), self.ref_for(w, y, rng, pa * 0.5)
            cx, cy = p[x], p[y]
            if cx - cy == 2:
                out.append(self.bin(lambda X, Y: f"{X} lives directly above {Y}.", rx, ry, lambda w, a, b: w[P][a] - w[P][b] == 2))
            if cx // 2 == cy // 2 and x < y and rng.random() < 0.6:
                out.append(self.bin(lambda X, Y: f"{X} and {Y} live on the same floor.", rx, ry, lambda w, a, b: w[P][a] // 2 == w[P][b] // 2))
            if cx // 2 == cy // 2 and cx % 2 == 1 and rng.random() < 0.5:
                out.append(self.bin(lambda X, Y: f"{X} lives to the east of {Y} on the same floor.", rx, ry, lambda w, a, b: w[P][a] - w[P][b] == 1 and w[P][a] % 2 == 1))
            dfl = cx // 2 - cy // 2
            if dfl >= 1 and rng.random() < 0.35:
                out.append(self.bin(lambda X, Y: f"{X} lives on a higher floor than {Y}.", rx, ry, lambda w, a, b: w[P][a] // 2 > w[P][b] // 2))
            if dfl >= 2 and x < y and rng.random() < 0.5:
                m = dfl - 1
                out.append(self.bin(lambda X, Y, d=dfl: f"{X} lives {NUMW[d]} floors above {Y}.", rx, ry,
                                    lambda w, a, b, d=dfl: w[P][a] // 2 - w[P][b] // 2 == d))
            if x < y and cx // 2 != cy // 2 and rng.random() < 0.2:
                out.append(self.bin(lambda X, Y: f"{X} and {Y} do not live on the same floor.", rx, ry, lambda w, a, b: w[P][a] // 2 != w[P][b] // 2))
            if x < y and cx % 2 == cy % 2 and cx // 2 != cy // 2 and rng.random() < 0.3:
                out.append(self.bin(lambda X, Y: f"{X} and {Y} live in the same type of flat.", rx, ry, lambda w, a, b: w[P][a] % 2 == w[P][b] % 2))
            if cx % 2 != cy % 2 and abs(cx // 2 - cy // 2) == 1 and x < y and rng.random() < 0.3:
                out.append(self.bin(lambda X, Y: f"{X} and {Y} live on adjacent floors but in different types of flat.", rx, ry,
                                    lambda w, a, b: w[P][a] % 2 != w[P][b] % 2 and abs(w[P][a] // 2 - w[P][b] // 2) == 1))
        for x in range(n):
            rx = self.ref_for(w, x, rng, pa)
            c = p[x]
            ft = "AB"[c % 2]
            out.append(self.uni(lambda X, ft=ft: f"{X} lives in Flat {ft}.", rx, lambda w, a, t=c % 2: w[P][a] % 2 == t))
            ev = (c // 2 + 1) % 2 == 0
            if rng.random() < 0.5:
                out.append(self.uni((lambda X: f"{X} lives on an even-numbered floor.") if ev else (lambda X: f"{X} lives on an odd-numbered floor."),
                                    rx, lambda w, a, ev=ev: ((w[P][a] // 2 + 1) % 2 == 0) == ev))
            if c // 2 == nf - 1:
                out.append(self.uni(lambda X: f"{X} lives on the topmost floor.", rx, lambda w, a: w[P][a] // 2 == nf - 1))
            if c // 2 == 0:
                out.append(self.uni(lambda X: f"{X} lives on the lowermost floor.", rx, lambda w, a: w[P][a] // 2 == 0))
            out.append(self.uni(lambda X, c=c: f"{X} lives in Flat {'AB'[c % 2]} of floor {c // 2 + 1}.", rx, lambda w, a, c=c: w[P][a] == c, tag="direct"))
        return out

    def q_above(self, w, rng):
        n, p = self.n, w[P]
        inv = {p[e]: e for e in range(n)}
        xs = [e for e in range(n) if p[e] + 2 < n]
        x = rng.choice(xs)
        up = rng.random() < 0.6 or p[x] < 2
        t = p[x] + 2 if up else p[x] - 2
        if not 0 <= t < n:
            return None
        y = inv[t]
        word = "above" if up else "below"
        diag = t + (1 if t % 2 == 0 else -1)
        cands = [(inv[diag], f"same floor as the flat {word}, but the other type (diagonal)"),
                 (inv[p[x] + (1 if p[x] % 2 == 0 else -1)], "neighbour on the same floor")]
        t2 = p[x] - 2 if up else p[x] + 2
        if 0 <= t2 < n:
            cands.append((inv[t2], "direction reversed"))
        return dict(q=f"Who lives directly {word} {self.names[x]}?", correct=self.names[y], wrongs=self.ent_opts(y, cands, "not directly " + word, exclude=(x,)),
                    how=f"{self.names[x]} is in {self.label(p[x])}; directly {word} is {self.label(t)} – {self.names[y]}.",
                    trap="'Directly above/below' keeps the same flat type (A over A, B over B).", kind="conceptual")

    def q_flat(self, w, rng):
        n, p = self.n, w[P]
        x = rng.randrange(n)
        c = p[x]
        cands = [c ^ 1, c + 2, c - 2, (c ^ 1) + 2, (c ^ 1) - 2]
        labs = ["right floor, wrong flat type", "one floor too high", "one floor too low", "diagonal flat", "diagonal flat"]
        wr, seen = [], {c}
        for cc, lab in zip(cands, labs):
            if 0 <= cc < n and cc not in seen:
                seen.add(cc)
                wr.append((self.label(cc), lab))
        return dict(q=f"In which flat does {self.names[x]} live?", correct=self.label(c), wrongs=wr[:3],
                    how=f"{self.names[x]} – {self.label(c)}.", trap="Fix both variables — floor and flat type.", kind="conceptual")

    def q_samefloor(self, w, rng):
        n, p = self.n, w[P]
        inv = {p[e]: e for e in range(n)}
        x = rng.randrange(n)
        y = inv[p[x] ^ 1]
        cands = [(inv[p[x] + 2], "lives directly above instead") if p[x] + 2 < n else (None, ""),
                 (inv[p[x] - 2], "lives directly below instead") if p[x] - 2 >= 0 else (None, "")]
        return dict(q=f"Who lives on the same floor as {self.names[x]}?", correct=self.names[y], wrongs=self.ent_opts(y, cands, "lives on another floor", exclude=(x,)),
                    how=f"{self.names[x]} is in {self.label(p[x])}; the other flat on that floor is {self.names[y]}'s.",
                    trap="Same floor ≠ same flat type.", kind="conceptual")

    def q_cnt(self, w, rng):
        n, p, nf = self.n, w[P], self.nf
        x = rng.choice([e for e in range(n) if 0 < p[e] // 2 < nf - 1] or list(range(n)))
        c = 2 * (nf - 1 - p[x] // 2)
        wr, seen = [], {c}
        for v, lab in ((nf - 1 - p[x] // 2, "counted floors, not persons"), (c + 1, "counted the other flat on the same floor"),
                       (2 * (p[x] // 2), "counted below instead of above"), (c + 2, "counted one floor extra")):
            if v >= 0 and v not in seen:
                seen.add(v)
                wr.append((numtxt(v), lab))
        return dict(q=f"How many persons live on floors above the floor of {self.names[x]}?", correct=numtxt(c), wrongs=wr[:3],
                    how=f"{self.names[x]} is on floor {p[x]//2+1}; {nf-1-p[x]//2} floor(s) above × 2 flats = {c}.",
                    trap="Each floor holds two persons.", kind="numerical")

    def offset(self, w, x, y):
        cx, cy = w[P][x], w[P][y]
        return (cy // 2 - cx // 2, (cy % 2) - (cx % 2))

    def off_mag(self, o):
        return o

    def off_ok(self, o):
        return o != (0, 0)

    def off_text(self, o):
        df, dt = o
        v = "on the same floor" if df == 0 else f"{NUMW[abs(df)]} floor{'s' if abs(df) > 1 else ''} {'above' if df > 0 else 'below'}"
        t = "in the same flat type" if dt == 0 else ("to the east (Flat B)" if dt > 0 else "to the west (Flat A)")
        return f"{v}, {t} of"

    def cats(self, w):
        p = w[P]
        return [("in Flat A", lambda e: p[e] % 2 == 0), ("in Flat B", lambda e: p[e] % 2 == 1),
                ("on even-numbered floors", lambda e: (p[e] // 2 + 1) % 2 == 0), ("on odd-numbered floors", lambda e: (p[e] // 2 + 1) % 2 == 1)]
