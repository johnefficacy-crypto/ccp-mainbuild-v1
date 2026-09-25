"""QRE-GIR-A part: (1) row with an unknown number of persons — solver enumerates every row length
n = k..60 and every placement of the named persons (backtracking), asserting a unique (n, positions);
(2) data sufficiency with numbered statements — sufficiency of I, II, I+II decided by exhaustive
enumeration of arrangements with the gira_geo geometries."""
import random
from gira_engine import P, A, Clue, solve, verify_unique, generate, length_cue, ordn, ORD, NUMW, cap
from gira_geo import Line, Circle, lst, numtxt
from gira_arr import letters, pnames

NMAX = 60
MICRO_RU = "reas-row-with-unknown-number-of-persons-cb13e578"
MICRO_DS = "reas-data-sufficiency-with-numbered-statements-cb6e8f2a"


# ------------------------------------------------------------------ row with unknown number
class RC:
    """clue over (n, pos): who = tuple of person indices it involves."""
    __slots__ = ("text", "fn", "who", "tag")

    def __init__(self, text, fn, who, tag=""):
        self.text, self.fn, self.who, self.tag = text, fn, tuple(who), tag


def ru_solve(k, clues, cap_=None, nmin=None, nmax=NMAX):
    """All (n, pos) with n in [max(k,nmin)..nmax] satisfying clues; pos[i] in 0..n-1 distinct."""
    order = sorted(range(k), key=lambda i: -sum(1 for c in clues if i in c.who))
    by_last = {i: [] for i in range(k)}
    for c in clues:
        last = max(c.who, key=order.index)
        by_last[last].append(c)
    sols = []
    for n in range(max(k, nmin or k), nmax + 1):
        pos = [None] * k

        def rec(d):
            if cap_ and len(sols) >= cap_:
                return
            if d == k:
                sols.append((n, tuple(pos)))
                return
            i = order[d]
            used = set(pos[j] for j in order[:d])
            for v in range(n):
                if v in used:
                    continue
                pos[i] = v
                if all(c.fn(n, pos) for c in by_last[i]):
                    rec(d + 1)
            pos[i] = None
        rec(0)
        if cap_ and len(sols) >= cap_:
            break
    return sols


def ru_pool(names, n, pos, rng):
    k = len(names)
    out = []
    for i in range(k):
        X = names[i]
        out.append(RC(f"{X} is {ordn(pos[i]+1)} from the left end.", lambda n_, p, i=i, v=pos[i]: p[i] == v, [i], "anchor"))
        out.append(RC(f"{X} is {ordn(n-pos[i])} from the right end.", lambda n_, p, i=i, r=n - pos[i]: n_ - p[i] == r, [i], "anchor"))
        if pos[i] >= 1 and rng.random() < 0.4:
            m = pos[i]
            out.append(RC(f"Only {NUMW.get(m, m)} {'person sits' if m == 1 else 'persons sit'} to the left of {X}.",
                          lambda n_, p, i=i, m=m: p[i] == m, [i], "anchor"))
    for i in range(k):
        for j in range(k):
            if i == j:
                continue
            X, Y = names[i], names[j]
            d = pos[i] - pos[j]
            if d > 0:
                m = d - 1
                if m >= 1:
                    out.append(RC(f"Exactly {NUMW.get(m, m)} {'person sits' if m == 1 else 'persons sit'} between {X} and {Y}, and {X} is to the right of {Y}.",
                                  lambda n_, p, i=i, j=j, d=d: p[i] - p[j] == d, [i, j]))
                    if i < j and rng.random() < 0.5:
                        out.append(RC(f"Exactly {NUMW.get(m, m)} {'person sits' if m == 1 else 'persons sit'} between {X} and {Y}.",
                                      lambda n_, p, i=i, j=j, d=d: abs(p[i] - p[j]) == d, [i, j]))
                if d == 1:
                    out.append(RC(f"{X} sits immediately to the right of {Y}.", lambda n_, p, i=i, j=j: p[i] - p[j] == 1, [i, j]))
                elif d <= 12:
                    out.append(RC(f"{X} is {ordn(d)} to the right of {Y}.", lambda n_, p, i=i, j=j, d=d: p[i] - p[j] == d, [i, j]))
            if i < j and pos[i] == n - 1 - pos[j]:
                out.append(RC(f"As many persons sit to the left of {X} as to the right of {Y}.", lambda n_, p, i=i, j=j: p[i] == n_ - 1 - p[j], [i, j]))
            if rng.random() < 0.25:
                t = pos[j]
                out.append(RC(f"If {X} and {Y} interchange their positions, {X} becomes {ordn(t+1)} from the left end.",
                              lambda n_, p, j=j, t=t: p[j] == t, [i, j]))
    return out


def ru_generate(names, n, rng):
    k = len(names)
    pos = tuple(rng.sample(range(n), k))
    pool = ru_pool(names, n, pos, rng)
    rng.shuffle(pool)
    pool.sort(key=lambda c: c.tag == "anchor")        # relational clues first, anchors last
    chosen = []
    cnt = len(ru_solve(k, chosen, cap_=40))
    for c in pool:
        c2 = len(ru_solve(k, chosen + [c], cap_=40))
        if c2 < cnt or cnt >= 40 and any(i not in {w for cc in chosen for w in cc.who} for i in c.who):
            chosen.append(c)
            cnt = c2
        if cnt == 1:
            break
    if cnt != 1:
        return None
    for c in rng.sample(chosen, len(chosen)):
        t = [x for x in chosen if x is not c]
        if len(ru_solve(k, t, cap_=2)) == 1:
            chosen = t
    sols = ru_solve(k, chosen)
    assert sols == [(n, pos)], sols
    rng.shuffle(chosen)
    return chosen, pos


def ru_intro(names):
    return f"Some persons sit in a single row, all facing north. {lst(names)} are among them; the total number of persons in the row is not given."


def ru_questions(names, n, pos, rng, prefs):
    k = len(names)
    qs = []
    for t in prefs:
        if t == "total":
            wr = [(str(n + 1), "counted one seat extra at an end"), (str(n - 1), "left out one end seat"),
                  (str(n + 2), "counted both anchor persons again")]
            qs.append(dict(q="How many persons sit in the row?", correct=str(n), wrongs=wr,
                           how=f"The unique placement needs exactly {n} seats (leftmost occupied seat is 1, rightmost is {n}).",
                           trap="Total = (position from left) + (position from right) − 1 for the same person.", kind="numerical"))
        elif t == "right":
            i = rng.randrange(k)
            r = n - pos[i]
            wr = [(ordn(pos[i] + 1), "gave the position from the left end"), (ordn(r + 1), "added one extra"), (ordn(r - 1) if r > 1 else ordn(r + 2), "subtracted one extra")]
            qs.append(dict(q=f"What is the position of {names[i]} from the right end of the row?", correct=ordn(r), wrongs=wr,
                           how=f"{names[i]} is {ordn(pos[i]+1)} from the left in a row of {n}; from the right: {n} − {pos[i]+1} + 1 = {r}.",
                           trap="Position from right = n − (position from left) + 1.", kind="numerical"))
        elif t == "btw":
            prs = [(i, j) for i in range(k) for j in range(i + 1, k) if abs(pos[i] - pos[j]) >= 2]
            i, j = rng.choice(prs)
            m = abs(pos[i] - pos[j]) - 1
            wr = [(str(m + 1), "included one of the two named persons"), (str(m + 2), "included both named persons"), (str(m - 1), "counted one short")]
            qs.append(dict(q=f"How many persons sit between {names[i]} and {names[j]}?", correct=str(m), wrongs=wr,
                           how=f"{names[i]} is at seat {pos[i]+1} and {names[j]} at seat {pos[j]+1} (from the left); {m} seats lie between.",
                           trap="Between excludes both named persons.", kind="numerical"))
        elif t == "rightcnt":
            i = rng.randrange(k)
            c = n - 1 - pos[i]
            wr = [(str(pos[i]), "counted to the left instead"), (str(c + 1), "included the person named"), (str(c - 1), "counted one short")]
            if c - 1 < 0:
                wr[2] = (str(c + 2), "counted two extra")
            qs.append(dict(q=f"How many persons sit to the right of {names[i]}?", correct=str(c), wrongs=wr,
                           how=f"{names[i]} is at seat {pos[i]+1} of {n}; {c} persons sit to the right.",
                           trap="Persons to the right = n − (position from left).", kind="numerical"))
        elif t == "leftpos":
            i = rng.randrange(k)
            l_ = pos[i] + 1
            wr = [(ordn(n - pos[i]), "gave the position from the right end"), (ordn(l_ + 1), "added one extra"), (ordn(l_ - 1) if l_ > 1 else ordn(l_ + 2), "subtracted one extra")]
            qs.append(dict(q=f"What is the position of {names[i]} from the left end of the row?", correct=ordn(l_), wrongs=wr,
                           how=f"{names[i]} occupies seat {l_} from the left.", trap="Fix the row length first, then convert end-positions.", kind="numerical"))
    for q in qs:
        texts = [q["correct"]] + [w[0] for w in q["wrongs"]]
        assert len(set(texts)) == 4, texts
    return qs


def ru_fixed(B):
    """Foundation classics, each proven by enumeration over n = 1..60."""
    out = []
    # 1. same person counted from both ends
    L_, R_ = 14, 19
    cl = [RC(f"R is {ordn(L_)} from the left end.", lambda n, p: p[0] == L_ - 1, [0]),
          RC(f"R is {ordn(R_)} from the right end.", lambda n, p: n - p[0] == R_, [0])]
    s = ru_solve(1, cl)
    assert len({x[0] for x in s}) == 1
    n = s[0][0]
    assert n == L_ + R_ - 1
    out.append(("L1", f"In a row of students facing north, R is {ordn(L_)} from the left end and {ordn(R_)} from the right end. How many students are there in the row?",
                str(n), [(str(L_ + R_), "added the two positions without removing R's double count"), (str(n - 1), "subtracted one extra"),
                         (str(R_ - L_ + 1), "subtracted the positions")],
                [f"R is counted in both positions, so total = {L_} + {R_} − 1 = {n}.", f"Enumeration over every row length confirms {n} is the only length consistent with both statements."],
                "Total = left position + right position − 1", "R is included in both counts."))
    # 2. interchange
    a_l, b_r, a_new = 9, 16, 21
    cl = [RC("", lambda n, p: p[0] == a_l - 1, [0]), RC("", lambda n, p: n - p[1] == b_r, [1]), RC("", lambda n, p: p[1] == a_new - 1, [0, 1])]
    s = ru_solve(2, cl)
    assert len(s) == 1
    n = s[0][0]
    assert n == a_new + b_r - 1
    out.append(("L1", f"In a row of girls facing north, Meena is {ordn(a_l)} from the left end and Sheela is {ordn(b_r)} from the right end. If they interchange their positions, "
                      f"Meena becomes {ordn(a_new)} from the left end. How many girls are there in the row?",
                str(n), [(str(a_l + b_r - 1), "used Meena's original position with Sheela's"), (str(n + 1), "did not subtract the common count"),
                         (str(a_new + a_l - 1), "added Meena's two left positions")],
                [f"After interchange Meena takes Sheela's seat, so Sheela's seat is {ordn(a_new)} from the left and {ordn(b_r)} from the right.",
                 f"Total = {a_new} + {b_r} − 1 = {n}."],
                "Total = (new left position) + (Sheela's right position) − 1", "The new position belongs to the other person's original seat."))
    # 3. gap between two persons, non-overlapping
    pL, m, qR = 7, 4, 11
    cl = [RC("", lambda n, p: p[0] == pL - 1, [0]), RC("", lambda n, p: p[1] - p[0] == m + 1, [0, 1]), RC("", lambda n, p: n - p[1] == qR, [1])]
    s = ru_solve(2, cl)
    assert len(s) == 1
    n = s[0][0]
    assert n == pL + m + qR
    out.append(("L2", f"In a row of persons facing north, P is {ordn(pL)} from the left end and Q is {ordn(qR)} from the right end. Exactly {NUMW[m]} persons sit between P and Q, "
                      f"and Q is to the right of P. How many persons are there in the row?",
                str(n), [(str(n - 1), "treated P and Q as counted twice"), (str(pL + qR), "ignored the persons between them"), (str(n + 1), "counted one extra")],
                [f"Seats: P at {pL}, then {m} persons, Q at {pL + m + 1} from the left.", f"Q is {ordn(qR)} from the right, so n = {pL + m + 1} + {qR} − 1 = {n}."],
                "n = P(left) + persons between + Q(right)", "P and Q do not overlap here, so nothing is subtracted."))
    # 4. minimum number (overlap allowed)
    aL, bR, m = 10, 8, 3
    cl = [RC("", lambda n, p: p[0] == aL - 1, [0]), RC("", lambda n, p: n - p[1] == bR, [1]), RC("", lambda n, p: abs(p[0] - p[1]) == m + 1, [0, 1])]
    s = ru_solve(2, cl)
    ns = sorted({x[0] for x in s})
    assert len(ns) == 2
    mn, mx = ns
    out.append(("L2", f"In a row of children facing north, Anu is {ordn(aL)} from the left end and Binu is {ordn(bR)} from the right end. Exactly {NUMW[m]} children sit between them. "
                      f"What is the minimum possible number of children in the row?",
                str(mn), [(str(mx), "assumed Anu must be to the left of Binu"), (str(mn - 1), "subtracted one extra"), (str(aL + bR - 1), "treated Anu and Binu as the same child")],
                [f"Case 1: Binu to the right of Anu → Binu at seat {aL + m + 1} → n = {aL + m + 1} + {bR} − 1 = {mx}.",
                 f"Case 2: Binu to the left of Anu → Binu at seat {aL - m - 1} → n = {aL - m - 1} + {bR} − 1 = {mn}.",
                 f"Enumeration over n = 1…60 finds only n = {mn} and n = {mx}; the minimum is {mn}."],
                "Check both relative orders; minimum comes from the overlapping case", "The two named persons can be on either side of each other."))
    return out


def ru_add(B):
    for lvl, stem, corr, wr, steps, formula, trap in ru_fixed(B):
        assert len(wr) == 3
        B.add(micro=MICRO_RU, level=lvl, tier="foundation", stem=stem, correct=corr, wrongs=wr, steps=steps, formula=formula, trap=trap,
              kind="numerical", ref="Standard ranking / row-length pattern (SSC/IBPS). Original numbers; verified by enumerating row lengths 1–60.")
    units = [("foundation", "L2", 4, (10, 16), ["total"]),
             ("officer", "L3", 5, (14, 22), ["total"]),
             ("officer", "L3", 5, (14, 22), ["right"]),
             ("officer", "L4", 6, (18, 30), ["total", "btw", "right", "rightcnt", "leftpos"]),
             ("officer", "L4", 6, (16, 26), ["total", "btw", "right"])]
    gi = 0
    for ui, (tier, lvl, k, (nlo, nhi), prefs) in enumerate(units):
        for att in range(200):
            rng = random.Random(f"GRA-RU-{ui}#{att}")
            names = letters(rng, k)
            n = rng.randint(nlo, nhi)
            r = ru_generate(names, n, rng)
            if r:
                break
        clues, pos = r
        qs = ru_questions(names, n, pos, rng, prefs)
        group = None
        if len(qs) > 1:
            gi += 1
            group = f"GRA-RU-{gi:02d}"
        stim = ru_intro(names) + "\n\n" + "\n".join(f"- {c.text}" for c in clues)
        placement = ", ".join(f"{names[i]} – seat {pos[i]+1}" for i in sorted(range(k), key=lambda i: pos[i]))
        for q in qs:
            B.add(micro=MICRO_RU, level=lvl, tier=tier, group=group, stem=stim + "\n\n" + q["q"], correct=q["correct"], wrongs=q["wrongs"],
                  steps=[f"The builder enumerates every row length from {k} to {NMAX} and every placement of the {k} named persons; "
                         f"exactly one combination satisfies all {len(clues)} statements: n = {n}.",
                         f"Seats from the left: {placement}.", q["how"]],
                  formula="Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues",
                  trap=q["trap"], kind="case" if group else q["kind"],
                  ref="Standard row-with-unknown-total pattern (IBPS/SBI PO). Original puzzle; unique (n, placement) proven by enumeration in builder.")


# ------------------------------------------------------------------ data sufficiency
DS_OPTS = {
    "I": "Statement I alone is sufficient, but statement II alone is not sufficient.",
    "II": "Statement II alone is sufficient, but statement I alone is not sufficient.",
    "E": "Either statement I alone or statement II alone is sufficient.",
    "B": "Statements I and II together are necessary; neither alone is sufficient.",
    "N": "Statements I and II together are not sufficient.",
}


def ds_cat(s1, s2, s12):
    if s1 and s2:
        return "E"
    if s1:
        return "I"
    if s2:
        return "II"
    return "B" if s12 else "N"


def ds_err(opt, s1, s2, s12):
    return {"I": "statement II alone also answers it" if s1 else "statement I alone leaves more than one answer",
            "II": "statement I alone also answers it" if s2 else "statement II alone leaves more than one answer",
            "E": "one of the statements alone leaves more than one answer",
            "B": "one statement alone is already sufficient" if (s1 or s2) else "even together they leave more than one answer",
            "N": "together (or singly) the statements do fix the answer"}[opt]


def ds_targets(geo, w, rng):
    """(question text, target fn over worlds) readable off the hidden world."""
    n = geo.n
    out = []
    if isinstance(geo, Line):
        for i in (0, n - 1, rng.randrange(n)):
            qt = geo.V["q_at"](i)
            out.append((qt, lambda ww, i=i: ww[P].index(i)))
        if "q_slot" in geo.V:
            x = rng.randrange(n)
            out.append((geo.V["q_slot"](geo.en(x)), lambda ww, x=x: ww[P][x]))
        if geo.attrs:
            x = rng.randrange(n)
            out.append((geo.attrs[0].q_of.format(X=geo.en(x)), lambda ww, x=x: ww[A][x]))
    else:
        x = rng.randrange(n)
        out.append((f"Who sits immediately to the right of {geo.names[x]}?", lambda ww, x=x: ww[P].index(geo.kth(ww, x, 1))))
        y = rng.randrange(n)
        out.append((f"Who sits second to the left of {geo.names[y]}?", lambda ww, y=y: ww[P].index(geo.kth(ww, y, -2))))
        if n % 2 == 0:
            z = rng.randrange(n)
            out.append((f"Who sits opposite {geo.names[z]}?", lambda ww, z=z: ww[P].index((ww[P][z] + n // 2) % n)))
    return out


def ds_make(fac, cat, seed, nb=(0, 1), ns=(1, 2)):
    for att in range(3000):
        rng = random.Random(f"{seed}#{att}")
        geo = fac(rng)
        dom = geo.domains()
        w = geo.rand_world(rng)
        pool = [c for c in geo.pool(w, rng, 0.3) if c.tag != "direct"]
        rng.shuffle(pool)
        nbase = rng.choice(nb)
        base = pool[:nbase]
        k1, k2 = rng.choice(ns), rng.choice(ns)
        S1 = pool[nbase:nbase + k1]
        S2 = pool[nbase + k1:nbase + k1 + k2]
        if len(S2) < k2:
            continue
        qt, tf = rng.choice(ds_targets(geo, w, rng))
        vals = lambda cl: {tf(x) for x in solve(dom, cl, 5_000_000)}
        if len(vals(base)) == 1:
            continue
        v1, v2, v12 = vals(base + S1), vals(base + S2), vals(base + S1 + S2)
        s1, s2, s12 = len(v1) == 1, len(v2) == 1, len(v12) == 1
        if ds_cat(s1, s2, s12) != cat:
            continue
        # neither statement may be redundant-empty: each must narrow the base set
        nb_all = len(solve(dom, base, 5_000_000))
        if any(len(solve(dom, base + [c], 5_000_000)) == nb_all for c in S1 + S2):
            continue
        return geo, w, base, S1, S2, qt, (s1, s2, s12), (len(vals(base)), len(v1), len(v2), len(v12))
    raise RuntimeError("DS generation failed " + seed)


def ds_add(B):
    L_ = lambda kind, n, attrs=(), nm=letters: (lambda rng: Line(kind, nm(rng, n), attrs, rng))
    CI = lambda n: (lambda rng: Circle(letters(rng, n), (), rng, facing="in"))
    units = [("foundation", "L1", L_("row", 5), "I", (0,), (1,)),
             ("foundation", "L2", L_("height", 5), "II", (0, 1), (1, 2)),
             ("foundation", "L2", L_("floor", 5), "E", (0, 1), (1, 2)),
             ("foundation", "L2", L_("day", 5, nm=pnames), "B", (0, 1), (1, 2)),
             ("foundation", "L2", L_("box", 5), "N", (0, 1), (1, 2)),
             ("officer", "L3", L_("row", 6), "B", (1, 2), (1, 2)),
             ("officer", "L3", CI(6), "I", (1, 2), (1, 2)),
             ("officer", "L3", L_("floor", 6, ["car"]), "II", (1, 2), (2,)),
             ("officer", "L3", L_("height", 6), "E", (1, 2), (1, 2)),
             ("officer", "L3", CI(7), "N", (1, 2), (1, 2)),
             ("officer", "L3", L_("box", 6, ["boxcol"]), "B", (1, 2), (2,)),
             ("officer", "L3", L_("time", 6, nm=pnames), "I", (1, 2), (1, 2)),
             ("officer", "L3", L_("day", 6, ["subject"], nm=pnames), "E", (1, 2), (2,)),
             ("officer", "L3", L_("month", 6, nm=pnames) if False else (lambda rng: Line("month", pnames(rng, 6), (), rng, months=["March", "July", "October"], dates=[4, 18])),
              "II", (1, 2), (1, 2)),
             ("officer", "L3", L_("year", 6, nm=pnames), "N", (1, 2), (1, 2))]
    head = ("The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are "
            "sufficient to answer the question, read together with the common information.")
    for ui, (tier, lvl, fac, cat, nb, ns) in enumerate(units):
        geo, w, base, S1, S2, qt, (s1, s2, s12), counts = ds_make(fac, cat, f"GRA-DS-{ui}", nb, ns)
        info = geo.intro() + ((" " + " ".join(c.text for c in base)) if base else "")
        stem = (f"{head}\n\nCommon information: {info}\n\nQuestion: {qt}\n\n"
                f"I. {' '.join(c.text for c in S1)}\n\nII. {' '.join(c.text for c in S2)}")
        rng = random.Random(f"GRA-DS-opt-{ui}")
        others = [k for k in DS_OPTS if k != cat]
        # keep the two long 'alone' options together so the key never stands out by length
        for _ in range(50):
            pick = rng.sample(others, 3)
            texts = [DS_OPTS[cat]] + [DS_OPTS[k] for k in pick]
            if not length_cue(texts, DS_OPTS[cat]):
                break
        wrongs = [(DS_OPTS[k], ds_err(k, s1, s2, s12)) for k in pick]
        b, c1, c2, c12 = counts
        yn = lambda s: "a single answer" if s else "more than one possible answer"
        steps = [f"Common information alone allows {b} different answers.",
                 f"With I alone: {c1} possible answer(s) → {yn(s1)}.",
                 f"With II alone: {c2} possible answer(s) → {yn(s2)}.",
                 f"With I and II together: {c12} possible answer(s) → {yn(s12)}.",
                 "All counts come from exhaustive enumeration of the arrangements in the builder."]
        B.add(micro=MICRO_DS, level=lvl, tier=tier, stem=stem, correct=DS_OPTS[cat], wrongs=wrongs, steps=steps,
              formula="Sufficient ⇔ every arrangement consistent with the data gives the same answer",
              trap="Test each statement alone first (with the common information) before combining them.",
              kind="statement", ref="Standard data-sufficiency pattern (IBPS/SBI PO, RBI Grade B). Original data; sufficiency decided by enumeration in builder.")


def add_all(B):
    ru_add(B)
    ds_add(B)
