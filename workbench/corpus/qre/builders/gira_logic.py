"""QRE-GIR-A part: inequalities (4 microtopics) and syllogisms (5 microtopics).

Inequalities: every statement set is solved by (a) a closure check (screening during generation) and
(b) EXHAUSTIVE enumeration of integer models (each letter takes a value 0..n-1, which realises every
weak order) for every question actually written; the builder asserts both agree on every conclusion.

Syllogisms: set models over Venn regions. A model = the set of non-empty regions (bitmask), every term
non-empty (standard exam assumption). All models are enumerated; a definite conclusion follows iff true
in every model; a possibility conclusion follows iff true in at least one model (possibility contents that
are already definite are never generated, to stay clear of the contested convention). Either-or pairs are
only keyed when the two conclusions are mutually exclusive, jointly exhaustive and neither is definite."""
import itertools
import random
from gira_engine import length_cue, cap

# ================================================================== inequalities
MI_DIRECT = "reas-direct-coded-inequality-4e115de6"
MI_EITHER = "reas-either-or-conclusions-in-inequality-0a9ae6c4"
MI_MULTI = "reas-multi-chain-inequality-with-linked-variables-26ae9265"
MI_SYMBOL = "reas-symbol-substitution-inequality-92327ea2"

OPS = [">", "≥", "=", "≤", "<"]
FLIP = {">": "<", "<": ">", "≥": "≤", "≤": "≥", "=": "="}
NEG = {">": "≤", "≤": ">", "<": "≥", "≥": "<"}
TEST = {">": lambda d: d > 0, "≥": lambda d: d >= 0, "=": lambda d: d == 0, "≤": lambda d: d <= 0, "<": lambda d: d < 0}
LETTERSETS = ["PQRSTUVW", "ABCDEFGH", "JKLMNPQR", "DEFGHJKL", "MNPQRSTU", "BCDEFGHJ", "KLMNPQRS", "STUVWXYZ"]


def edges(stmts):
    """(u, v, strict) meaning u >= v (strict: u > v)."""
    out = []
    for x, op, y in stmts:
        if op in (">", "≥"):
            out.append((x, y, op == ">"))
        elif op in ("<", "≤"):
            out.append((y, x, op == "<"))
        else:
            out += [(x, y, False), (y, x, False)]
    return out


def consistent(stmts):
    E = edges(stmts)
    adj = {}
    for u, v, s in E:
        adj.setdefault(u, []).append(v)
    for u, v, s in E:
        if not s:
            continue
        seen, st = {v}, [v]           # does v reach u?
        while st:
            a = st.pop()
            if a == u:
                return False
            for b in adj.get(a, []):
                if b not in seen:
                    seen.add(b)
                    st.append(b)
    return True


def c_follows(stmts, x, op, y):
    """closure-based: op-relation definitely true."""
    if op == "=":
        return c_follows(stmts, x, "≥", y) and c_follows(stmts, x, "≤", y)
    return not consistent(stmts + [(x, NEG[op], y)])


def c_possible(stmts, x, op, y):
    return consistent(stmts + [(x, op, y)])


def enum_models(stmts, pairs):
    """Exhaustive enumeration of integer models; returns set of sign-vectors over `pairs`."""
    vs = sorted({v for s in stmts for v in (s[0], s[2])} | {v for p in pairs for v in p})
    n = len(vs)
    # order: BFS over constraint graph for pruning
    adj = {v: set() for v in vs}
    for x, _, y in stmts:
        adj[x].add(y)
        adj[y].add(x)
    order, seen = [], set()
    for s in vs:
        if s in seen:
            continue
        q = [s]
        seen.add(s)
        while q:
            a = q.pop(0)
            order.append(a)
            for b in sorted(adj[a]):
                if b not in seen:
                    seen.add(b)
                    q.append(b)
    pos = {v: i for i, v in enumerate(order)}
    chk = {v: [] for v in order}
    for x, op, y in stmts:
        last = x if pos[x] > pos[y] else y
        chk[last].append((x, op, y))
    val = {}
    res = set()

    def rec(d):
        if d == n:
            res.add(tuple((val[a] > val[b]) - (val[a] < val[b]) for a, b in pairs))
            return
        v = order[d]
        for k in range(n):
            val[v] = k
            if all(TEST[op](val[x] - val[y]) for x, op, y in chk[v]):
                rec(d + 1)
        del val[v]
    rec(0)
    assert res, "inconsistent statements"
    return res


class IneqCheck:
    """Verifies conclusions by enumeration and cross-checks against closure."""

    def __init__(self, stmts, concl):
        self.stmts = stmts
        pairs = sorted({(c[0], c[2]) for c in concl})
        self.pairs = pairs
        self.M = enum_models(stmts, pairs)

    def status(self, c):
        x, op, y = c
        k = self.pairs.index((x, y))
        vals = [TEST[op](m[k]) for m in self.M]
        e = all(vals)
        assert e == c_follows(self.stmts, x, op, y), f"closure/enumeration disagree on {c}"
        return e, any(vals)

    def either(self, c1, c2):
        """exclusive + exhaustive over all models, neither definite."""
        k1, k2 = self.pairs.index((c1[0], c1[2])), self.pairs.index((c2[0], c2[2]))
        a = [TEST[c1[1]](m[k1]) for m in self.M]
        b = [TEST[c2[1]](m[k2]) for m in self.M]
        return (not all(a)) and (not all(b)) and all(x != y for x, y in zip(a, b))


def ctext(c):
    return f"{c[0]} {c[1]} {c[2]}"


def chain_text(letters_, ops_):
    s = letters_[0]
    for o, l in zip(ops_, letters_[1:]):
        s += f" {o} {l}"
    return s


def chain_stmts(letters_, ops_):
    return [(a, o, b) for a, o, b in zip(letters_, ops_, letters_[1:])]


STD2 = {"I": "Only I follows", "II": "Only II follows", "E": "Either I or II follows",
        "N": "Neither I nor II follows", "B": "Both I and II follow"}


def cat2(f1, f2, eo):
    if f1 and f2:
        return "B"
    if f1:
        return "I"
    if f2:
        return "II"
    return "E" if eo else "N"


def err2(k, f1, f2, eo):
    return {"I": "conclusion II also follows" if f1 else "conclusion I does not follow definitely",
            "II": "conclusion I also follows" if f2 else "conclusion II does not follow definitely",
            "E": "missed that the pair is not complementary / one of them is definite",
            "N": "missed the either-or pair" if eo else "overlooked a conclusion that does follow",
            "B": "treated an uncertain conclusion as definite"}[k]


def combo_text(fl, eo_pair):
    """fl: list of bools for I, II, III ; eo_pair: None or (i, j) indices forming an either-or pair."""
    R = ["I", "II", "III"]
    if eo_pair:
        i, j = eo_pair
        rest = [R[k] for k in range(3) if k not in eo_pair and fl[k]]
        if rest:
            return f"Only {rest[0]} and either {R[i]} or {R[j]} follow"
        return f"Either {R[i]} or {R[j]} follows"
    t = [R[k] for k in range(3) if fl[k]]
    if not t:
        return "None follows"
    if len(t) == 3:
        return "All I, II and III follow"
    if len(t) == 1:
        return f"Only {t[0]} follows"
    return f"Only {t[0]} and {t[1]} follow"


ALL3 = ([(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)])


def combo_wrongs(fl, eo, rng, k=3):
    corr = combo_text(fl, eo)
    cands = []
    for f in ALL3:
        t = combo_text(list(f), None)
        if t != corr:
            diff = [["I", "II", "III"][i] for i in range(3) if bool(f[i]) != bool(fl[i]) or (eo and i in eo)]
            cands.append((t, "misjudged conclusion(s) " + ", ".join(diff)))
    for pr in [(0, 1), (0, 2), (1, 2)]:
        for third in (0, 1):
            f = [0, 0, 0]
            rem = [x for x in range(3) if x not in pr][0]
            f[rem] = third
            t = combo_text(f, pr)
            if t != corr:
                cands.append((t, "paired conclusions that are not a valid either-or pair" if pr != eo else "misjudged the third conclusion"))
    seen, out = {corr}, []
    rng.shuffle(cands)
    for _ in range(200):
        pick = rng.sample(cands, k)
        texts = [corr] + [p[0] for p in pick]
        if len(set(texts)) == 4 and not length_cue(texts, corr):
            return corr, pick
    raise RuntimeError("no combo wrongs")


def pick_std(corr_key, table, errf, rng):
    others = [k for k in table if k != corr_key]
    for _ in range(100):
        pick = rng.sample(others, 3)
        texts = [table[corr_key]] + [table[k] for k in pick]
        if not length_cue(texts, table[corr_key]):
            return [(table[k], errf(k)) for k in pick]
    raise RuntimeError("length cue")


# ------------------------------------------------ random statement builders
def rand_chain(rng, lets, strict_bias=0.5, eq=0.15):
    ops_ = []
    up = rng.random() < 0.5
    for _ in range(len(lets) - 1):
        r = rng.random()
        if r < eq:
            ops_.append("=")
            continue
        dirn = up if rng.random() < 0.72 else not up
        if dirn:
            ops_.append(">" if rng.random() < strict_bias else "≥")
        else:
            ops_.append("<" if rng.random() < strict_bias else "≤")
    return ops_


def rand_concl(rng, vars_, stmts, avoid=()):
    for _ in range(100):
        x, y = rng.sample(vars_, 2)
        op = rng.choice([">", "<", "≥", "≤", "=", ">", "<"])
        c = (x, op, y)
        adjacent = any({s[0], s[2]} == {x, y} for s in stmts)
        if c not in avoid and not adjacent:
            return c
    return None


def eo_partner(rng, c, stmts):
    """complementary relation over same pair (exclusive + exhaustive or partitioning a known >= )."""
    x, op, y = c
    opts = {">": ["="], "<": ["="], "=": [">", "<"], "≥": ["<"], "≤": [">"]}[op]
    return (x, rng.choice(opts), y)


def two_concl_item(rng, stmts, vars_, want, allow_eo=True, tries=400):
    for _ in range(tries):
        c1 = rand_concl(rng, vars_, stmts)
        if c1 is None:
            continue
        if want == "E" or (allow_eo and rng.random() < 0.3):
            c2 = eo_partner(rng, c1, stmts)
            if rng.random() < 0.5:
                c1, c2 = c2, c1
        else:
            c2 = rand_concl(rng, vars_, stmts, avoid=(c1,))
        if c2 is None or c2 == c1:
            continue
        f1, f2 = c_follows(stmts, *c1), c_follows(stmts, *c2)
        chk = IneqCheck(stmts, [c1, c2])
        e1, p1 = chk.status(c1)
        e2, p2 = chk.status(c2)
        eo = (c1[0], c1[2]) == (c2[0], c2[2]) and chk.either(c1, c2)
        # skip contested cases: same pair, jointly exhaustive but overlapping, neither definite
        if (c1[0], c1[2]) == (c2[0], c2[2]) and not e1 and not e2 and not eo:
            k = chk.pairs.index((c1[0], c1[2]))
            if all(TEST[c1[1]](m[k]) or TEST[c2[1]](m[k]) for m in chk.M):
                continue
        cat = cat2(e1, e2, eo)
        if cat == want:
            return c1, c2, (e1, e2, eo), chk
    return None


def three_concl_item(rng, stmts, vars_, want_eo, want_count=None, tries=600):
    for _ in range(tries):
        cs = []
        if want_eo:
            c1 = rand_concl(rng, vars_, stmts)
            if c1 is None:
                continue
            c2 = eo_partner(rng, c1, stmts)
            c3 = rand_concl(rng, vars_, stmts, avoid=(c1, c2))
            if c3 is None:
                continue
            cs = [c1, c2, c3]
            rng.shuffle(cs)
        else:
            for _k in range(3):
                c = rand_concl(rng, vars_, stmts, avoid=tuple(cs))
                if c is None:
                    break
                cs.append(c)
            if len(cs) < 3:
                continue
        chk = IneqCheck(stmts, cs)
        st = [chk.status(c)[0] for c in cs]
        eo = None
        bad = False
        for i, j in [(0, 1), (0, 2), (1, 2)]:
            if (cs[i][0], cs[i][2]) == (cs[j][0], cs[j][2]):
                if chk.either(cs[i], cs[j]):
                    eo = (i, j)
                elif not st[i] and not st[j]:
                    k = chk.pairs.index((cs[i][0], cs[i][2]))
                    if all(TEST[cs[i][1]](m[k]) or TEST[cs[j][1]](m[k]) for m in chk.M):
                        bad = True
        if bad or bool(eo) != want_eo:
            continue
        if want_count is not None and sum(st) != want_count:
            continue
        return cs, st, eo, chk
    return None


def ineq_steps_two(stmts_txt, stmts, cs, st, eo):
    out = [f"Combine the statements: {stmts_txt}."]
    R = ["I", "II", "III"]
    for i, c in enumerate(cs):
        x, op, y = c
        rels = [o for o in (">", "=", "<") if c_possible(stmts, x, o, y)]
        rtxt = {(">",): f"{x} > {y}", ("=",): f"{x} = {y}", ("<",): f"{x} < {y}", (">", "="): f"{x} ≥ {y}",
                ("=", "<"): f"{x} ≤ {y}", (">", "<"): f"{x} ≠ {y}", (">", "=", "<"): f"no definite relation between {x} and {y}"}[tuple(rels)]
        rtxt = rtxt if rtxt.startswith("no ") else "derived relation is " + rtxt
        out.append(f"Conclusion {R[i]} ({ctext(c)}): {rtxt} → {'follows' if st[i] else 'does not follow definitely'}.")
    if eo:
        i, j = eo
        out.append(f"Conclusions {R[i]} and {R[j]} involve the same pair, are mutually exclusive and together cover every possibility → either {R[i]} or {R[j]} follows.")
    out.append("Checked by enumerating every ordering of the letters consistent with the statements.")
    return out


def pack_letters(rng, n):
    s = rng.choice(LETTERSETS)
    L = list(s[:n])
    rng.shuffle(L)
    return L


def build_stmts(rng, n, nchains):
    """nchains linked chains over n letters (each subsequent chain shares one letter)."""
    lets = pack_letters(rng, n)
    if nchains == 1:
        ops_ = rand_chain(rng, lets)
        return lets, [(lets, ops_)]
    sizes = []
    rem = n
    # split: chain i introduces new letters; chain>0 starts/contains one old letter
    base = n // nchains + 1
    chains = []
    first = lets[:base]
    chains.append((first, rand_chain(rng, first)))
    used = list(first)
    rest = lets[base:]
    per = max(1, len(rest) // (nchains - 1))
    for ci in range(1, nchains):
        new = rest[(ci - 1) * per: ci * per] if ci < nchains - 1 else rest[(ci - 1) * per:]
        link = rng.choice(used)
        seq = list(new)
        seq.insert(rng.randrange(len(seq) + 1), link)
        chains.append((seq, rand_chain(rng, seq)))
        used += new
    return lets, chains


def stmts_of(chains):
    s = []
    for L, o in chains:
        s += chain_stmts(L, o)
    return s


def stmts_text(chains, sep="; "):
    return sep.join(chain_text(L, o) for L, o in chains)


def add_two(B, micro, tier, level, seed, n, nchains, want, allow_eo=True, intro=None, fmt=None, group=None):
    for att in range(300):
        rng = random.Random(f"{seed}#{att}")
        lets, chains = build_stmts(rng, n, nchains)
        stmts = stmts_of(chains)
        if not consistent(stmts):
            continue
        r = two_concl_item(rng, stmts, lets, want, allow_eo)
        if r:
            break
    else:
        raise RuntimeError(seed)
    c1, c2, (e1, e2, eo), chk = r
    stx = (fmt or stmts_text)(chains)
    head = intro or "In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow."
    stem = f"{head}\n\nStatements: {stx}\n\nConclusions:\nI. {ctext(c1)}\nII. {ctext(c2)}"
    wr = pick_std(want, STD2, lambda k: err2(k, e1, e2, eo), rng)
    steps = ineq_steps_two(stmts_text(chains), stmts, [c1, c2], [e1, e2], (0, 1) if eo else None)
    B.add(micro=micro, level=level, tier=tier, stem=stem, correct=STD2[want], wrongs=wr, steps=steps,
          formula="A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain",
          trap="Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.",
          kind="statement", group=group,
          ref="Standard inequality pattern (IBPS/SBI PO & Clerk). Original statements; conclusions verified by exhaustive enumeration in builder.")


def add_three(B, micro, tier, level, seed, n, nchains, want_eo, count=None, fmt=None, intro=None):
    for att in range(300):
        rng = random.Random(f"{seed}#{att}")
        lets, chains = build_stmts(rng, n, nchains)
        stmts = stmts_of(chains)
        if not consistent(stmts):
            continue
        r = three_concl_item(rng, stmts, lets, want_eo, count)
        if r:
            break
    else:
        raise RuntimeError(seed)
    cs, st, eo, chk = r
    corr, wr = combo_wrongs(st if not eo else [s for s in st], eo, rng)
    head = intro or "In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow."
    stem = (f"{head}\n\nStatements: {(fmt or stmts_text)(chains)}\n\nConclusions:\n" +
            "\n".join(f"{r_}. {ctext(c)}" for r_, c in zip(["I", "II", "III"], cs)))
    B.add(micro=micro, level=level, tier=tier, stem=stem, correct=corr, wrongs=wr,
          steps=ineq_steps_two(stmts_text(chains), stmts, cs, st, eo),
          formula="Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite",
          trap="An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.",
          kind="statement", ref="Standard inequality pattern (IBPS/SBI PO, RBI Grade B). Original statements; verified by exhaustive enumeration in builder.")


def add_expr_true(B, micro, tier, level, seed, n, negate=False):
    """Given target conclusion, which expression makes it definitely true (or definitely false)."""
    for att in range(500):
        rng = random.Random(f"{seed}#{att}")
        lets = pack_letters(rng, n)
        x, y = rng.sample(lets, 2)
        op = rng.choice([">", "<", "≥", "≤"])
        target = (x, op, y)
        exprs, good = [], None
        seen = set()
        for _ in range(80):
            L = list(lets)
            rng.shuffle(L)
            o = rand_chain(rng, L, eq=0.2)
            txt = chain_text(L, o)
            if txt in seen:
                continue
            st = chain_stmts(L, o)
            if not consistent(st):
                continue
            seen.add(txt)
            chk = IneqCheck(st, [target])
            e, p = chk.status(target)
            val = (not p) if negate else e
            exprs.append((txt, val, st, e, p))
        goods = [e for e in exprs if e[1]]
        bads = [e for e in exprs if not e[1]]
        if len(goods) < 1 or len(bads) < 3:
            continue
        g = goods[0]
        bd = bads[:3]
        texts = [g[0]] + [b[0] for b in bd]
        if length_cue(texts, g[0]) or len(set(texts)) != 4:
            continue
        break
    else:
        raise RuntimeError(seed)
    want = "definitely false" if negate else "definitely true"
    wr = [(b[0], "here the relation is " + ("possible" if negate else ("possible but not certain" if b[4] else "impossible"))) for b in bd]
    stem = f"In which of the following expressions is the expression '{ctext(target)}' {want}?"
    B.add(micro=micro, level=level, tier=tier, stem=stem, correct=g[0], wrongs=wr,
          steps=[f"Trace {x} and {y} along each expression; the path between them must have every sign pointing the same way.",
                 f"In '{g[0]}', the path from {x} to {y} makes '{ctext(target)}' {want}.",
                 "In each other expression the path contains an opposite sign or a weak sign, so the relation is either uncertain or the opposite of what is required.",
                 "Verified by enumerating every ordering consistent with each expression."],
          formula="Relation between two letters is definite only if every sign on the path between them points the same way",
          trap="A single opposite sign anywhere between the two letters destroys the relation; ≥ with > still gives >.",
          kind="conceptual", ref="Standard inequality pattern (SBI/IBPS PO). Original expressions; verified by exhaustive enumeration in builder.")


def add_fill_symbol(B, micro, tier, level, seed, n):
    """Which symbol replaces '?' so that two target relations are definitely true."""
    for att in range(800):
        rng = random.Random(f"{seed}#{att}")
        lets = pack_letters(rng, n)
        o = rand_chain(rng, lets, eq=0.15)
        qi = rng.randrange(len(o))
        x, y = rng.sample(lets, 2)
        i1, i2 = sorted([lets.index(x), lets.index(y)])
        if not (i1 <= qi < i2):
            continue
        tops = [">", "<", "≥", "≤"]
        target_op = rng.choice(tops)
        t1 = (lets[i1], target_op, lets[i2])
        # second target
        cand = [(a, b) for a in range(n) for b in range(a + 1, n) if a <= qi < b and (a, b) != (i1, i2)]
        if not cand:
            continue
        a, b = rng.choice(cand)
        t2 = (lets[a], rng.choice(tops + ["="]), lets[b])
        res = {}
        for s in OPS:
            oo = list(o)
            oo[qi] = s
            st = chain_stmts(lets, oo)
            if not consistent(st):
                res[s] = False
                continue
            chk = IneqCheck(st, [t1, t2])
            res[s] = chk.status(t1)[0] and chk.status(t2)[0]
        goods = [s for s in OPS if res[s]]
        if len(goods) != 1:
            continue
        g = goods[0]
        wrongs = [s for s in OPS if s != g]
        rng.shuffle(wrongs)
        wr = [(s, "makes at least one of the two relations uncertain or false") for s in wrongs[:3]]
        break
    else:
        raise RuntimeError(seed)
    oo = list(o)
    oo[qi] = "?"
    expr = chain_text(lets, oo)
    stem = (f"Which of the following symbols should replace the question mark (?) in the expression '{expr}' so that both "
            f"'{ctext(t1)}' and '{ctext(t2)}' are definitely true?")
    B.add(micro=micro, level=level, tier=tier, stem=stem, correct=g, wrongs=wr,
          steps=[f"Try each symbol in place of ? and trace {t1[0]}–{t1[2]} and {t2[0]}–{t2[2]}.",
                 f"Only '{g}' makes both relations definite: " + chain_text(lets, [g if s == "?" else s for s in oo]) + ".",
                 "Every other symbol either reverses a sign on one of the paths or weakens a required strict sign.",
                 "Each of the five symbols was tested by exhaustive enumeration of orderings in the builder."],
          formula="Both target paths pass through '?'; the symbol must point the same way as the rest of each path and supply strictness if required",
          trap="Check both targets; a symbol that satisfies one can break the other.", kind="conceptual",
          ref="Standard inequality pattern (IBPS PO/Clerk). Original expression; each symbol tested by enumeration in builder.")


def add_fill_seq(B, micro, tier, level, seed, n=5):
    """Fill blanks 'A _ B _ C _ D _ E' with symbol sequence making target(s) definitely true."""
    for att in range(800):
        rng = random.Random(f"{seed}#{att}")
        lets = pack_letters(rng, n)
        seqs = list(itertools.product(OPS, repeat=n - 1))
        x, y = lets[0], lets[-1]
        m = rng.randrange(1, n - 1)
        t1 = (x, rng.choice([">", "<"]), y)
        t2 = (lets[m], rng.choice(["≥", "≤", ">", "<"]), y)
        good_seq = [s for s in seqs if consistent(chain_stmts(lets, s)) and c_follows(chain_stmts(lets, s), *t1) and c_follows(chain_stmts(lets, s), *t2)]
        bad_seq = [s for s in seqs if consistent(chain_stmts(lets, s)) and s not in good_seq]
        if not good_seq or len(bad_seq) < 3:
            continue
        g = rng.choice(good_seq)
        near = sorted(bad_seq, key=lambda s: (sum(a != b for a, b in zip(s, g)), rng.random()))
        bd = [s for s in near if sum(a != b for a, b in zip(s, g)) >= 1][:3]
        # enumeration proof for all four
        ok = True
        for s in [g] + bd:
            chk = IneqCheck(chain_stmts(lets, s), [t1, t2])
            v = chk.status(t1)[0] and chk.status(t2)[0]
            if v != (s == g):
                ok = False
        if ok:
            break
    else:
        raise RuntimeError(seed)
    blank = " _ ".join(lets)
    fmt = lambda s: ", ".join(s)
    stem = (f"Which of the following sets of symbols, placed in the blanks from left to right, will make the expressions "
            f"'{ctext(t1)}' and '{ctext(t2)}' definitely true?\n\n{blank}")
    B.add(micro=micro, level=level, tier=tier, stem=stem, correct=fmt(g),
          wrongs=[(fmt(s), "one sign on a required path points the wrong way or is not strict") for s in bd],
          steps=[f"With '{fmt(g)}' the expression reads {chain_text(lets, g)}.",
                 f"Both paths ({t1[0]} to {t1[2]}, {t2[0]} to {t2[2]}) have all signs in one direction with the needed strictness.",
                 "Each of the other sets leaves at least one target uncertain or false.",
                 "All four options checked by exhaustive enumeration in the builder."],
          formula="Target '>' needs all signs on the path in the same direction with at least one strict sign",
          trap="A set can satisfy the end-to-end relation yet fail the middle-letter relation.", kind="conceptual",
          ref="Standard inequality pattern (SBI PO). Original expression; options verified by enumeration in builder.")


# ---------------------------------------------- symbol substitution
SYMS = ["@", "#", "$", "%", "&", "*", "©", "★"]
MEAN = {">": "neither smaller than nor equal to", "<": "neither greater than nor equal to", "=": "neither smaller than nor greater than",
        "≥": "not smaller than", "≤": "not greater than"}
MEAN2 = {">": "greater than", "<": "smaller than", "=": "equal to", "≥": "either greater than or equal to", "≤": "either smaller than or equal to"}


def make_code(rng, style):
    s = rng.sample(SYMS, 5)
    code = dict(zip(OPS, s))
    lines = []
    mean = MEAN if style == 1 else MEAN2
    for op in rng.sample(OPS, 5):
        lines.append(f"'P {code[op]} Q' means 'P is {mean[op]} Q'.")
    return code, " ".join(lines)


def enc(code, c):
    return f"{c[0]} {code[c[1]]} {c[2]}"


def enc_chain(code, L, o):
    return chain_text(L, [code[x] for x in o])


def add_symbol(B, micro, tier, level, seed, n, nchains, want, code=None, codetxt=None, group=None, three=False, want_eo=False, rng0=None):
    rngc = random.Random(seed + "-code")
    if code is None:
        code, codetxt = make_code(rngc, rngc.choice([1, 2]))
    for att in range(300):
        rng = random.Random(f"{seed}#{att}")
        lets, chains = build_stmts(rng, n, nchains)
        stmts = stmts_of(chains)
        if not consistent(stmts):
            continue
        r = three_concl_item(rng, stmts, lets, want_eo) if three else two_concl_item(rng, stmts, lets, want)
        if r:
            break
    else:
        raise RuntimeError(seed)
    fmtc = lambda ch: "; ".join(enc_chain(code, L, o) for L, o in ch)
    head = f"In the following question, the symbols are used with the meanings given below.\n\n{codetxt}"
    if three:
        cs, st, eo, chk = r
        corr, wr = combo_wrongs(st, eo, rng)
        concl = cs
        steps = ineq_steps_two(stmts_text(chains), stmts, cs, st, eo)
    else:
        c1, c2, (e1, e2, eo), chk = r
        corr = STD2[want]
        wr = pick_std(want, STD2, lambda k: err2(k, e1, e2, eo), rng)
        concl = [c1, c2]
        steps = ineq_steps_two(stmts_text(chains), stmts, concl, [e1, e2], (0, 1) if eo else None)
    decode = ", ".join(f"{code[o]} → {o}" for o in OPS)
    steps = [f"Decode the symbols: {decode}."] + steps
    stem = (f"{head}\n\nAssuming the statements to be true, decide which of the conclusions definitely follow.\n\n"
            f"Statements: {fmtc(chains)}\n\nConclusions:\n" +
            "\n".join(f"{r_}. {enc(code, c)}" for r_, c in zip(["I", "II", "III"], concl)))
    B.add(micro=micro, level=level, tier=tier, stem=stem, correct=corr, wrongs=wr, steps=steps,
          formula="Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule",
          trap="'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.", kind="case" if group else "statement", group=group,
          ref="Standard coded-inequality pattern (IBPS/SBI PO & Clerk). Original code and statements; conclusions verified by enumeration in builder.")


def ineq_add(B):
    # ---- Direct inequality
    M = MI_DIRECT
    for i, (lv, n, want) in enumerate([("L1", 4, "I"), ("L1", 4, "B"), ("L2", 5, "II"), ("L2", 5, "N"), ("L2", 5, "E")]):
        add_two(B, M, "foundation", lv, f"GRA-IQD-F{i}", n, 1, want)
    for i, (n, nc, want) in enumerate([(6, 2, "N"), (6, 2, "I"), (7, 2, "B"), (7, 2, "II")]):
        add_two(B, M, "officer", "L3", f"GRA-IQD-O{i}", n, nc, want)
    for i in range(3):
        add_expr_true(B, M, "officer", "L3", f"GRA-IQD-X{i}", 5 + (i % 2), negate=(i == 2))
    for i in range(3):
        add_three(B, M, "officer", "L3", f"GRA-IQD-T{i}", 7, 2, False, count=[1, 2, 0][i])
    # ---- Either-or
    M = MI_EITHER
    for i, (n, want) in enumerate([(4, "E"), (5, "E"), (5, "I"), (5, "N"), (5, "E")]):
        add_two(B, M, "foundation", "L2", f"GRA-IQE-F{i}", n, 1, want)
    for i in range(6):
        add_three(B, M, "officer", "L3", f"GRA-IQE-T{i}", 7 if i % 2 else 6, 2, True)
    for i, want in enumerate(["N", "E", "B", "II"]):
        add_two(B, M, "officer", "L3", f"GRA-IQE-O{i}", 7, 2, want)
    # ---- Multi-chain
    M = MI_MULTI
    for i, want in enumerate(["I", "N", "B"]):
        add_two(B, M, "foundation", "L2", f"GRA-IQM-F{i}", 6, 2, want)
    for i in range(2):
        add_fill_symbol(B, M, "foundation", "L2", f"GRA-IQM-S{i}", 5)
    for i, want in enumerate(["E", "II", "N", "I"]):
        add_two(B, M, "officer", "L3", f"GRA-IQM-O{i}", 8, 3, want)
    for i in range(3):
        add_fill_seq(B, M, "officer", "L3", f"GRA-IQM-Q{i}", 5)
    for i in range(3):
        add_three(B, M, "officer", "L3", f"GRA-IQM-T{i}", 8, 3, i == 1, count=None)
    # ---- Symbol substitution
    M = MI_SYMBOL
    for i, (n, want) in enumerate([(4, "I"), (4, "N"), (5, "B"), (5, "E"), (5, "II")]):
        add_symbol(B, M, "foundation", "L2", f"GRA-IQS-F{i}", n, 1, want)
    for i in range(2):
        add_symbol(B, M, "officer", "L3", f"GRA-IQS-T{i}", 7, 2, None, three=True, want_eo=(i == 0))
    # case sets: shared code, several statement sets
    for gi, wants in enumerate([["E", "I", "N", "B", "II"], ["II", "E", "N"]]):
        rngc = random.Random(f"GRA-IQS-C{gi}-code")
        code, codetxt = make_code(rngc, 1)
        g = f"GRA-SYM-{gi+1:02d}"
        for qi, want in enumerate(wants):
            add_symbol(B, M, "officer", "L4", f"GRA-IQS-C{gi}-{qi}", 6 + (qi % 2), 2, want, code=code, codetxt=codetxt, group=g)


# ================================================================== syllogisms
MS_TWO = "reas-two-statement-syllogism-7f65e035"
MS_THREE = "reas-three-or-more-statement-syllogism-e8800438"
MS_ONLY = "reas-only-and-only-a-few-statements-d42e0ef7"
MS_POSS = "reas-possibility-conclusions-b7cd9da3"
MS_EO = "reas-either-or-and-complementary-pairs-52508ad3"

NOUNS = [("pens", "pen"), ("books", "book"), ("chairs", "chair"), ("tables", "table"), ("doctors", "doctor"), ("teachers", "teacher"),
         ("rivers", "river"), ("lakes", "lake"), ("rings", "ring"), ("coins", "coin"), ("birds", "bird"), ("kites", "kite"),
         ("phones", "phone"), ("laptops", "laptop"), ("roses", "rose"), ("lilies", "lily"), ("buses", "bus"), ("trains", "train"),
         ("singers", "singer"), ("dancers", "dancer"), ("bottles", "bottle"), ("jars", "jar"), ("apples", "apple"), ("mangoes", "mango"),
         ("stones", "stone"), ("bricks", "brick"), ("clouds", "cloud"), ("stars", "star"), ("files", "file"), ("folders", "folder"),
         ("lions", "lion"), ("tigers", "tiger"), ("shirts", "shirt"), ("jackets", "jacket"), ("walls", "wall"), ("doors", "door"),
         ("cups", "cup"), ("plates", "plate"), ("pilots", "pilot"), ("engineers", "engineer")]


def art(w):
    return ("an " if w[0] in "aeiou" else "a ") + w


class Term:
    def __init__(self, pl, sg):
        self.pl, self.sg = pl, sg


# proposition types over (X, Y) term indices:
#  A all, E no, I some, O some-not, F only-a-few, Y only (Only X are Y == all Y are X)
def ptext(t, x, y, T, poss=False):
    X, Y = T[x], T[y]
    if poss:
        return {"A": f"All {X.pl} being {Y.pl} is a possibility.",
                "I": f"Some {X.pl} being {Y.pl} is a possibility.",
                "O": f"Some {X.pl} not being {Y.pl} is a possibility.",
                "E": f"No {X.sg} being {art(Y.sg)} is a possibility.",
                "RA": f"All {Y.pl} being {X.pl} is a possibility."}[t]
    return {"A": f"All {X.pl} are {Y.pl}.", "E": f"No {X.sg} is {art(Y.sg)}.", "I": f"Some {X.pl} are {Y.pl}.",
            "O": f"Some {X.pl} are not {Y.pl}.", "F": f"Only a few {X.pl} are {Y.pl}.", "Y": f"Only {X.pl} are {Y.pl}."}[t]


class Syl:
    def __init__(self, k):
        self.k = k
        self.regions = list(range(1, 1 << k))     # region r: set of terms whose bit is set

    def rmask(self, pred):
        m = 0
        for idx, r in enumerate(self.regions):
            if pred(r):
                m |= 1 << idx
        return m

    def masks(self, x, y):
        bx, by = 1 << x, 1 << y
        return (self.rmask(lambda r: r & bx and r & by), self.rmask(lambda r: r & bx and not r & by),
                self.rmask(lambda r: r & by and not r & bx))

    def fn(self, t, x, y):
        xy, xny, ynx = self.masks(x, y)
        return {"A": lambda M: not (M & xny), "E": lambda M: not (M & xy), "I": lambda M: bool(M & xy),
                "O": lambda M: bool(M & xny), "F": lambda M: bool(M & xy) and bool(M & xny),
                "Y": lambda M: not (M & ynx), "RA": lambda M: not (M & ynx)}[t]

    def universal_empty(self, stmts):
        """regions forced empty by universal statements (A, E, Y): sound restriction."""
        forb = 0
        for t, x, y in stmts:
            xy, xny, ynx = self.masks(x, y)
            forb |= {"A": xny, "E": xy, "Y": ynx}.get(t, 0)
        return forb

    def models(self, stmts):
        forb = self.universal_empty(stmts)
        allowed = [i for i in range(len(self.regions)) if not (forb >> i) & 1]
        assert len(allowed) <= 18, f"too many free regions ({len(allowed)})"
        fns = [self.fn(t, x, y) for t, x, y in stmts]
        terms = [self.rmask(lambda r, b=1 << j: r & b) for j in range(self.k)]
        out = []
        m = len(allowed)
        for s in range(1 << m):
            M = 0
            for j in range(m):
                if (s >> j) & 1:
                    M |= 1 << allowed[j]
            if all(M & tm for tm in terms) and all(f(M) for f in fns):
                out.append(M)
        assert out, "statements inconsistent"
        return out


def syl_status(S, models, c):
    """c = (type, x, y, poss). returns follows(bool), definite-true(bool), possible(bool)."""
    t, x, y, poss = c
    f = S.fn(t, x, y)
    vals = [f(M) for M in models]
    d, p = all(vals), any(vals)
    return (p if poss else d), d, p


def syl_either(S, models, c1, c2):
    f1, f2 = S.fn(c1[0], c1[1], c1[2]), S.fn(c2[0], c2[1], c2[2])
    a = [f1(M) for M in models]
    b = [f2(M) for M in models]
    return (not all(a)) and (not all(b)) and all(u != v for u, v in zip(a, b))


COMP = {"I": "E", "E": "I", "A": "O", "O": "A"}


def rand_terms(rng, k):
    return [Term(*p) for p in rng.sample(NOUNS, k)]


def rand_stmts(rng, k, nst, types, chain=True):
    """statements linking terms 0-1, 1-2, ... (with random orientation)."""
    out = []
    order = list(range(k))
    rng.shuffle(order)
    links = [(order[i], order[i + 1]) for i in range(k - 1)]
    if nst > k - 1:
        extra = [(a, b) for a in range(k) for b in range(a + 1, k) if (a, b) not in links and (b, a) not in links]
        links += rng.sample(extra, nst - (k - 1))
    for a, b in links[:nst]:
        if rng.random() < 0.5:
            a, b = b, a
        out.append((rng.choice(types), a, b))
    rng.shuffle(out)
    return out


def rand_sconc(rng, k, stmts, types, poss_rate=0.0, avoid=()):
    for _ in range(100):
        x, y = rng.sample(range(k), 2)
        poss = rng.random() < poss_rate
        t = rng.choice(["A", "I", "O", "E", "RA"] if poss else types)
        c = (t, x, y, poss)
        if c in avoid:
            continue
        if not poss and any((s[1], s[2]) == (x, y) and s[0] == t for s in stmts):
            continue           # not a verbatim copy of a statement
        return c
    return None


def cstr(c, T):
    t, x, y, poss = c
    return ptext(t, x, y, T, poss)


def syl_valid_concl(S, models, c):
    """reject possibility contents that are already definite (contested convention) and
    'Only a few'/'Only' conclusions whose truth hinges on nothing (kept simple)."""
    fl, d, p = syl_status(S, models, c)
    if c[3] and d:
        return False
    return True


def syl_steps(stmts, T, cs, st, eo, S, models):
    R = ["I", "II", "III"]
    out = ["Draw the least-overlap (Venn) case for the statements: " + " ".join(ptext(t, x, y, T) for t, x, y in stmts)]
    for i, c in enumerate(cs):
        fl, d, p = syl_status(S, models, c)
        if c[3]:
            why = "possible in at least one valid diagram and not contradicted by any statement" if p else "contradicted by the statements in every valid diagram"
        else:
            why = "true in every valid diagram" if d else ("possible but not certain (a diagram exists where it fails)" if p else "false in every valid diagram")
        out.append(f"Conclusion {R[i]}: {cstr(c, T)} → {why} → {'follows' if st[i] else 'does not follow'}.")
    if eo:
        i, j = eo
        out.append(f"{R[i]} and {R[j]} form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either {R[i]} or {R[j]} follows.")
    out.append(f"Verified by enumerating all {len(models)} admissible Venn-region models in the builder.")
    return out


SYL_REF = "Standard syllogism pattern (IBPS/SBI PO & Clerk, SSC). Original statements; conclusions verified by Venn-region model enumeration in builder."


def syl_two(B, micro, tier, level, seed, k, nst, stypes, ctypes, want, poss_rate=0.0, want_eo=None, force_types=None):
    for att in range(4000):
        rng = random.Random(f"{seed}#{att}")
        T = rand_terms(rng, k)
        stmts = rand_stmts(rng, k, nst, stypes)
        if force_types and not all(any(s[0] == ft for s in stmts) for ft in force_types):
            continue
        S = Syl(k)
        try:
            models = S.models(stmts)
        except AssertionError:
            continue
        c1 = rand_sconc(rng, k, stmts, ctypes, poss_rate)
        if c1 is None:
            continue
        if want == "E" or (want_eo and rng.random() < 0.7) or (want_eo is None and rng.random() < 0.15 and c1[0] in COMP and not c1[3]):
            if c1[0] not in COMP or c1[3]:
                continue
            c2 = (COMP[c1[0]], c1[1], c1[2], False)
            if rng.random() < 0.5:
                c1, c2 = c2, c1
        else:
            c2 = rand_sconc(rng, k, stmts, ctypes, poss_rate, avoid=(c1,))
        if c2 is None or c2 == c1 or cstr(c1, T) == cstr(c2, T):
            continue
        if not (syl_valid_concl(S, models, c1) and syl_valid_concl(S, models, c2)):
            continue
        f1, f2 = syl_status(S, models, c1)[0], syl_status(S, models, c2)[0]
        same = (c1[1], c1[2]) == (c2[1], c2[2]) and not c1[3] and not c2[3]
        eo = same and syl_either(S, models, c1, c2)
        if same and not eo and not f1 and not f2 and COMP.get(c1[0]) == c2[0]:
            continue
        if want_eo is not None and bool(eo) != want_eo and want != "E":
            continue
        if cat2(f1, f2, eo) == want:
            break
    else:
        raise RuntimeError(seed)
    head = "In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow."
    stem = (f"{head}\n\nStatements:\n" + "\n".join(ptext(t, x, y, T) for t, x, y in stmts) +
            f"\n\nConclusions:\nI. {cstr(c1, T)}\nII. {cstr(c2, T)}")
    wr = pick_std(want, STD2, lambda kk: err2(kk, f1, f2, eo), rng)
    B.add(micro=micro, level=level, tier=tier, stem=stem, correct=STD2[want], wrongs=wr,
          steps=syl_steps(stmts, T, [c1, c2], [f1, f2], (0, 1) if eo else None, S, models),
          formula="Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite",
          trap="Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.",
          kind="statement", ref=SYL_REF)


def syl_three(B, micro, tier, level, seed, k, nst, stypes, ctypes, want_eo, poss_rate=0.0, count=None, force_types=None):
    for att in range(6000):
        rng = random.Random(f"{seed}#{att}")
        T = rand_terms(rng, k)
        stmts = rand_stmts(rng, k, nst, stypes)
        if force_types and not all(any(s[0] == ft for s in stmts) for ft in force_types):
            continue
        S = Syl(k)
        try:
            models = S.models(stmts)
        except AssertionError:
            continue
        cs = []
        if want_eo:
            c1 = rand_sconc(rng, k, stmts, [t for t in ctypes if t in COMP], 0)
            if c1 is None:
                continue
            cs = [c1, (COMP[c1[0]], c1[1], c1[2], False)]
            c3 = rand_sconc(rng, k, stmts, ctypes, poss_rate, avoid=tuple(cs))
            if c3 is None:
                continue
            cs.append(c3)
            rng.shuffle(cs)
        else:
            for _ in range(3):
                c = rand_sconc(rng, k, stmts, ctypes, poss_rate, avoid=tuple(cs))
                if c is None:
                    break
                cs.append(c)
            if len(cs) < 3:
                continue
        if len({cstr(c, T) for c in cs}) < 3 or not all(syl_valid_concl(S, models, c) for c in cs):
            continue
        st = [syl_status(S, models, c)[0] for c in cs]
        eo, bad = None, False
        for i, j in [(0, 1), (0, 2), (1, 2)]:
            a, b = cs[i], cs[j]
            if (a[1], a[2]) == (b[1], b[2]) and not a[3] and not b[3] and COMP.get(a[0]) == b[0]:
                if syl_either(S, models, a, b):
                    eo = (i, j)
                elif not st[i] and not st[j]:
                    bad = True
        if bad or bool(eo) != want_eo:
            continue
        if count is not None and sum(st) != count:
            continue
        break
    else:
        raise RuntimeError(seed)
    corr, wr = combo_wrongs(st, eo, rng)
    head = "In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow."
    stem = (f"{head}\n\nStatements:\n" + "\n".join(ptext(t, x, y, T) for t, x, y in stmts) + "\n\nConclusions:\n" +
            "\n".join(f"{r}. {cstr(c, T)}" for r, c in zip(["I", "II", "III"], cs)))
    B.add(micro=micro, level=level, tier=tier, stem=stem, correct=corr, wrongs=wr,
          steps=syl_steps(stmts, T, cs, st, eo, S, models),
          formula="Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite",
          trap="Check each conclusion separately before looking for a complementary pair.", kind="statement", ref=SYL_REF)


def syl_which(B, micro, tier, level, seed, k, nst, stypes, ctypes, poss=False, force_types=None):
    """Which of the following conclusions follows? exactly one of four."""
    for att in range(6000):
        rng = random.Random(f"{seed}#{att}")
        T = rand_terms(rng, k)
        stmts = rand_stmts(rng, k, nst, stypes)
        if force_types and not all(any(s[0] == ft for s in stmts) for ft in force_types):
            continue
        S = Syl(k)
        try:
            models = S.models(stmts)
        except AssertionError:
            continue
        good, bad = [], []
        for _ in range(60):
            c = rand_sconc(rng, k, stmts, ctypes, 0.5 if poss else 0.0)
            if c is None or not syl_valid_concl(S, models, c):
                continue
            (good if syl_status(S, models, c)[0] else bad).append(c)
        if poss and not any(c[3] for c in good):
            continue
        good = [c for c in good if c[3]] if poss else good
        if not good or len({cstr(c, T) for c in bad}) < 3:
            continue
        g = good[0]
        bd, seen = [], {cstr(g, T)}
        for c in bad:
            if cstr(c, T) not in seen:
                seen.add(cstr(c, T))
                bd.append(c)
            if len(bd) == 3:
                break
        texts = [cstr(g, T)] + [cstr(c, T) for c in bd]
        if length_cue(texts, texts[0]):
            continue
        break
    else:
        raise RuntimeError(seed)
    stem = ("Statements:\n" + "\n".join(ptext(t, x, y, T) for t, x, y in stmts) +
            "\n\nTaking the statements to be true, which of the following conclusions logically follows?")
    wr = []
    for c in bd:
        fl, d, p = syl_status(S, models, c)
        wr.append((cstr(c, T), "ruled out by the statements" if not p else "possible but not certain"))
    B.add(micro=micro, level=level, tier=tier, stem=stem, correct=cstr(g, T), wrongs=wr,
          steps=syl_steps(stmts, T, [], [], None, S, models)[:1] +
          [f"'{cstr(g, T)}' holds " + ("in at least one valid diagram and is not ruled out." if g[3] else "in every valid diagram."),
           "Each other option fails in at least one valid diagram (or is ruled out altogether).",
           f"Verified by enumerating all {len(models)} admissible Venn-region models in the builder."],
          formula="A definite conclusion must hold in every admissible diagram",
          trap="Converting 'All A are B' gives only 'Some B are A', never 'All B are A'.", kind="conceptual", ref=SYL_REF)


def syl_needed(B, micro, tier, level, seed, stypes):
    """Given statement 1 and a conclusion, which second statement makes the conclusion follow."""
    for att in range(6000):
        rng = random.Random(f"{seed}#{att}")
        T = rand_terms(rng, 3)
        S = Syl(3)
        a, b, c = 0, 1, 2
        s1 = (rng.choice(stypes), a, b) if rng.random() < 0.5 else (rng.choice(stypes), b, a)
        concl = (rng.choice(["A", "I", "O", "E"]), a, c, False) if rng.random() < 0.5 else (rng.choice(["I", "O", "E"]), c, a, False)
        cands = [(t, b, c) for t in stypes] + [(t, c, b) for t in stypes]
        res = []
        for s2 in cands:
            try:
                models = S.models([s1, s2])
            except AssertionError:
                continue
            res.append((s2, syl_status(S, models, concl)[0]))
        goods = [r for r in res if r[1]]
        bads = [r for r in res if not r[1]]
        if len(goods) != 1 or len(bads) < 3:
            continue
        g = goods[0][0]
        bd = rng.sample([r[0] for r in bads], 3)
        texts = [ptext(*g, T)] + [ptext(*x, T) for x in bd]
        if length_cue(texts, texts[0]):
            continue
        break
    else:
        raise RuntimeError(seed)
    models = S.models([s1, g])
    stem = (f"Statement I: {ptext(*s1, T)}\nConclusion: {cstr(concl, T)}\n\n"
            "Which of the following, taken as Statement II along with Statement I, makes the conclusion follow definitely?")
    B.add(micro=micro, level=level, tier=tier, stem=stem, correct=ptext(*g, T),
          wrongs=[(ptext(*x, T), "with this statement the conclusion is at best possible, not definite") for x in bd],
          steps=[f"Only with '{ptext(*g, T)}' does '{cstr(concl, T)}' hold in every admissible diagram ({len(models)} models enumerated).",
                 "For each other candidate, enumeration finds a valid diagram in which the conclusion fails.",
                 "All candidate second statements were tested exhaustively in the builder (each one listed pair of the middle term)."],
          formula="The middle term must be distributed at least once; a particular premise yields only a particular conclusion",
          trap="'Some' premises chained through the middle term never give a definite conclusion.", kind="conceptual", ref=SYL_REF)


def syl_add(B):
    B4 = ["A", "I", "E", "O"]
    B3 = ["A", "I", "E"]
    C4 = ["A", "I", "E", "O"]
    # ---- two-statement
    M = MS_TWO
    for i, (lv, want) in enumerate([("L1", "I"), ("L1", "B"), ("L2", "N"), ("L2", "E"), ("L2", "II")]):
        syl_two(B, M, "foundation", lv, f"GRA-SY2-F{i}", 3, 2, B3, C4, want, want_eo=(want == "E"))
    for i, cnt in enumerate([1, 2, 0, 2, 1]):
        syl_three(B, M, "officer", "L3", f"GRA-SY2-T{i}", 3, 2, B4, C4, want_eo=(i == 3), count=None if i == 3 else cnt)
    for i in range(3):
        syl_needed(B, M, "officer", "L3", f"GRA-SY2-N{i}", B4)
    for i in range(2):
        syl_which(B, M, "officer", "L2", f"GRA-SY2-W{i}", 3, 2, B4, C4 + ["RA"] if False else C4)
    # ---- three or more statements
    M = MS_THREE
    for i, want in enumerate(["I", "N", "B", "II", "E"]):
        syl_two(B, M, "foundation", "L2", f"GRA-SY3-F{i}", 4, 3, B3, C4, want, want_eo=(want == "E"))
    for i, want in enumerate(["B", "N", "I"]):
        syl_two(B, M, "officer", "L3", f"GRA-SY3-O{i}", 5, 4, B4, C4, want, want_eo=False)
    for i in range(2):
        syl_three(B, M, "officer", "L3", f"GRA-SY3-P{i}", 5, 4, B4, C4, want_eo=(i == 1), count=None if i else 2)
    for i in range(3):
        syl_three(B, M, "officer", "L3", f"GRA-SY3-T{i}", 4, 3, B4, C4, want_eo=(i == 0), count=None if i == 0 else [1, 2, 0][i])
    for i in range(2):
        syl_which(B, M, "officer", "L3", f"GRA-SY3-W{i}", 4 + i, 3 + i, B4, C4)
    # ---- only / only a few
    M = MS_ONLY
    OT = ["A", "I", "E", "F", "Y"]
    for i, want in enumerate(["I", "N", "B", "II", "E"]):
        syl_two(B, M, "foundation", "L2", f"GRA-SYO-F{i}", 3, 2, ["F", "A", "I", "E"], C4 + ["F"], want, want_eo=(want == "E"), force_types=["F"])
    for i, want in enumerate(["II", "B", "N", "I"]):
        syl_two(B, M, "officer", "L3", f"GRA-SYO-O{i}", 3 + (i % 2), 2 + (i % 2), OT, C4 + ["F", "Y"], want, want_eo=False, force_types=["Y"] if i % 2 == 0 else ["F"])
    for i in range(4):
        syl_three(B, M, "officer", "L3", f"GRA-SYO-T{i}", 4, 3, OT, C4 + ["F", "Y"], want_eo=(i == 2), count=None if i == 2 else [1, 2, None, 0][i],
                  force_types=["F", "Y"] if i < 2 else ["Y"])
    for i in range(2):
        syl_which(B, M, "officer", "L3", f"GRA-SYO-W{i}", 4, 3, OT, C4 + ["F"], force_types=["Y", "F"] if i == 0 else ["F"])
    # ---- possibility
    M = MS_POSS
    for i, want in enumerate(["I", "B", "N", "II", "B"]):
        syl_two(B, M, "foundation", "L2", f"GRA-SYP-F{i}", 3, 2, B3 + ["O"], C4, want, poss_rate=0.6, want_eo=False)
    for i, want in enumerate(["II", "N", "B", "I"]):
        syl_two(B, M, "officer", "L3", f"GRA-SYP-O{i}", 4, 3, B4 + ["F"], C4, want, poss_rate=0.7, want_eo=False)
    for i in range(4):
        syl_three(B, M, "officer", "L3", f"GRA-SYP-T{i}", 4, 3, B4 + ["Y"], C4, want_eo=False, poss_rate=0.6, count=[2, 1, 3, 0][i])
    for i in range(2):
        syl_which(B, M, "officer", "L3", f"GRA-SYP-W{i}", 4, 3, B4, C4, poss=True)
    # ---- either-or / complementary pairs
    M = MS_EO
    for i, want in enumerate(["E", "E", "I", "E", "II"]):
        syl_two(B, M, "foundation", "L2", f"GRA-SYE-F{i}", 3, 2, B3 + ["O"], C4, want, want_eo=True if want == "E" else None)
    for i in range(6):
        syl_three(B, M, "officer", "L3", f"GRA-SYE-T{i}", 4 if i % 2 else 3, 3 if i % 2 else 2, B4 + (["F"] if i >= 3 else []), C4, want_eo=True)
    for i, want in enumerate(["N", "E", "B", "I"]):
        syl_two(B, M, "officer", "L3", f"GRA-SYE-O{i}", 4, 3, B4, C4, want, want_eo=(want == "E") if want in ("E", "N") else None)


def add_all(B):
    ineq_add(B)
    syl_add(B)
