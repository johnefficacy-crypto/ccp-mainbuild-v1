"""GIR-B part 2: Blood relations (coded, direct description, family-tree puzzles, gender ambiguity).
All keys come from the kinship engine in girb_kin.py; every question asserts determinacy (or the
intended indeterminacy) across all gender-consistent worlds."""
from girb_common import *
from girb_kin import Kin, Contradiction, build_chain, confusers, cap

M_CODE = "reas-coded-blood-relation-c6693c9c"
M_DIR = "reas-direct-relation-from-a-description-e0847737"
M_TREE = "reas-family-tree-puzzle-with-generations-78d7886d"
M_AMB = "reas-relation-with-gender-ambiguity-0d4e3334"
CBD = "Cannot be determined"
GENDERED = ["father", "mother", "son", "daughter", "brother", "sister", "husband", "wife"]


def rel_opts(key, extra=()):
    c = [(cap(t), e) for t, e in confusers(key)] + list(extra)
    return c + [(CBD, "assumed the data are insufficient")]


def chain_sentence(people, ops):
    return " ".join(f"{people[i]} is the {r} of {people[i+1]}." for i, r in enumerate(ops))


def explain_chain(people, ops):
    return [f"{people[i]} is the {r} of {people[i+1]}." for i, r in enumerate(ops)]


def find_chain(seed, n_ops, pool, cond, people=None, tries=20000, avoid=()):
    rng = random.Random(seed)
    people = people or list("ABCDEFG")[: n_ops + 1]
    for _ in range(tries):
        ops = [rng.choice(pool) for _ in range(n_ops)]
        if tuple(ops) in avoid:
            continue
        try:
            k = build_chain(people, ops)
        except Contradiction:
            continue
        r = cond(k, people)
        if r:
            return ops, k, r
    raise RuntimeError("no chain found for " + seed)


def det(first_to_last=True, qual=True, allowed=None):
    def c(k, pp):
        x, y = (pp[0], pp[-1]) if first_to_last else (pp[-1], pp[0])
        s = k.rel_set(x, y, qual)
        if len(s) == 1 and None not in s:
            t = next(iter(s))
            if allowed is None or t.replace("paternal ", "").replace("maternal ", "") in allowed:
                return (x, y, t)
        return None
    return c


INTERESTING = {"grandfather", "grandmother", "uncle", "aunt", "nephew", "niece", "father-in-law", "mother-in-law", "son-in-law",
               "daughter-in-law", "brother-in-law", "sister-in-law", "grandson", "granddaughter", "cousin", "great-grandfather",
               "great-grandmother", "great-grandson", "great-granddaughter"}
SIMPLE = {"father", "mother", "son", "daughter", "brother", "sister", "husband", "wife", "grandfather", "grandmother", "grandson", "granddaughter",
          "uncle", "aunt", "nephew", "niece"}


def coded(B):
    syms = ["#", "@", "$", "%", "&", "*"]
    used = set()

    def code_block(codes):
        return "\n".join(f"- 'P {s} Q' means P is the {r} of Q" for s, r in codes.items())

    specs = [("foundation", "L1", 2, True, SIMPLE), ("foundation", "L2", 2, True, SIMPLE), ("foundation", "L2", 3, True, SIMPLE),
             ("foundation", "L2", 3, False, SIMPLE), ("foundation", "L2", 3, True, SIMPLE),
             ("officer", "L3", 3, True, INTERESTING), ("officer", "L3", 4, True, INTERESTING), ("officer", "L3", 4, False, INTERESTING),
             ("officer", "L3", 4, True, INTERESTING), ("officer", "L3", 4, False, INTERESTING), ("officer", "L3", 4, True, INTERESTING)]
    for i, (tier, lvl, n, f2l, allowed) in enumerate(specs):
        rng = random.Random(f"GRB-code-{i}")
        rels = rng.sample(GENDERED, 6)
        codes = dict(zip(syms, rels))
        inv = {r: s for s, r in codes.items()}
        pp = list("PQRSTU")[: n + 1] if i % 2 else list("JKLMNO")[: n + 1]
        ops, k, (x, y, key) = find_chain(f"GRB-code-{i}", n, rels, det(f2l, True, allowed), people=pp, avoid=used)
        used.add(tuple(ops))
        expr = " ".join(pp[j] + " " + inv[ops[j]] for j in range(n)) + " " + pp[n]
        stem = f"In a certain code language:\n{code_block(codes)}\n\nIf '{expr}' is true, how is {x} related to {y}?"
        q(B, M_CODE, lvl, tier, stem, cap(key), rel_opts(key),
          ["Decode: " + " ".join(explain_chain(pp, ops)), f"Build the tree and read {x} → {y}: {key}."],
          "Decode symbol by symbol, then draw the family tree", "Fix each person's gender from the code words before naming the relation.", kind="conceptual")
    # which expression shows ...
    for i in range(4):
        rng = random.Random(f"GRB-codex-{i}")
        rels = rng.sample(GENDERED, 6)
        codes = dict(zip(syms, rels))
        inv = {r: s for s, r in codes.items()}
        pp = list("WXYZ")
        res = {}
        for ops in itertools.product(rels, repeat=3):
            try:
                k = build_chain(pp, list(ops))
            except Contradiction:
                continue
            res[ops] = frozenset(k.rel_set("W", "Z", True))
        targets = sorted({next(iter(s)) for s in res.values() if len(s) == 1 and None not in s and
                          next(iter(s)).replace("paternal ", "").replace("maternal ", "") in INTERESTING})
        target = targets[rng.randrange(len(targets))]
        keys = [o for o, s in res.items() if s == frozenset([target])]
        kops = keys[rng.randrange(len(keys))]
        # distractors: close expressions (share 2 of 3 ops) with a different outcome
        close = [o for o, s in res.items() if s != frozenset([target]) and sum(a == b for a, b in zip(o, kops)) == 2]
        rng.shuffle(close)
        pick = close[:3]
        assert len(pick) == 3
        ex = lambda o: " ".join(pp[j] + " " + inv[o[j]] for j in range(3)) + " " + pp[3]
        wr = []
        for o in pick:
            s = res[o]
            desc = ", ".join(sorted(x or "no standard term" for x in s))
            wr.append((ex(o), f"gives W as {desc} of Z"))
        stem = f"In a certain code language:\n{code_block(codes)}\n\nWhich expression shows that W is the {target} of Z?"
        q(B, M_CODE, "L3", "officer", stem, ex(kops), wr,
          ["Decode the correct option: " + " ".join(explain_chain(pp, list(kops))), f"W is the {target} of Z in every consistent tree.",
           "Each other option yields a different (or undetermined) relation."],
          "Decode every option; only one fixes the required relation", "Check both gender and side (paternal/maternal) of the relation.", kind="conceptual")


def direct(B):
    specs = [("foundation", "L1", 2, True, SIMPLE), ("foundation", "L1", 2, False, SIMPLE), ("foundation", "L2", 3, True, SIMPLE),
             ("foundation", "L2", 3, False, SIMPLE), ("foundation", "L2", 3, True, SIMPLE),
             ("officer", "L3", 4, True, INTERESTING), ("officer", "L3", 4, False, INTERESTING), ("officer", "L3", 4, True, INTERESTING),
             ("officer", "L3", 5, True, INTERESTING), ("officer", "L3", 5, False, INTERESTING)]
    used = set()
    for i, (tier, lvl, n, f2l, allowed) in enumerate(specs):
        pp = list("ABCDEF")[: n + 1] if i % 2 == 0 else list("PQRSTU")[: n + 1]
        ops, k, (x, y, key) = find_chain(f"GRB-dir-{i}", n, GENDERED, det(f2l, True, allowed), people=pp, avoid=used)
        used.add(tuple(ops))
        stem = chain_sentence(pp, ops) + f" How is {x} related to {y}?"
        q(B, M_DIR, lvl, tier, stem, cap(key), rel_opts(key), explain_chain(pp, ops) + [f"Therefore {x} is the {key} of {y}."],
          "Draw the tree statement by statement", "Genders come only from the relation words; do not assume from letters.", kind="conceptual")
    # pointing / introduction puzzles (engine-verified; 'only son/daughter' inference encoded explicitly)
    pz = []
    k = Kin(); k.apply("Mo", "mother", "Suresh"); k.person("Suresh", "m"); k.apply("Boy", "son", "Suresh")
    pz.append(("Pointing to a photograph of a boy, Suresh said, \"He is the son of the only son of my mother.\" How is the boy related to Suresh?",
               k, "Boy", "Suresh", ["The only son of Suresh's mother is Suresh himself (Suresh is male).", "So the boy is Suresh's son."]))
    k2 = Kin(); k2.apply("Mo", "mother", "Kavita"); k2.person("Kavita", "f"); k2.apply("Gf", "father", "Mo"); k2.apply("Man", "son", "Gf"); k2.sibling("Man", "Mo")
    pz.append(("Pointing to a man, Kavita said, \"He is the only son of my mother's father.\" How is the man related to Kavita?",
               k2, "Man", "Kavita", ["Kavita's mother's father is her maternal grandfather.", "His only son is her mother's brother → maternal uncle."]))
    k = Kin(); k.person("Arjun", "m"); k.apply("Arjun", "father", "Son"); k.apply("Arjun", "brother", "Mo"); k.apply("Mo", "mother", "Lady"); k.person("Lady", "f")
    pz.append(("Pointing to a lady, Arjun said, \"Her mother's brother is the father of my son.\" How is the lady related to Arjun?",
               k, "Lady", "Arjun", ["The father of Arjun's son is Arjun himself.", "Arjun is the brother of the lady's mother → she is his niece."]))
    k = Kin(); k.person("Mohan", "m"); k.apply("W", "son", "Mohan"); k.apply("Woman", "wife", "W")
    pz.append(("Showing a woman in a photograph, Mohan said, \"Her father-in-law is the only son of my father.\" How is the woman related to Mohan?",
               k, "Woman", "Mohan", ["The only son of Mohan's father is Mohan.", "Mohan is the woman's father-in-law → she is his daughter-in-law."]))
    k = Kin(); k.apply("A", "sister", "B"); k.apply("C", "mother", "B"); k.apply("D", "father", "C"); k.apply("E", "mother", "D")
    pz.append(("A is the sister of B. C is the mother of B. D is the father of C. E is the mother of D. How is A related to D?",
               k, "A", "D", ["A and B are children of C.", "D is C's father → D is A's maternal grandfather.", "So A is D's granddaughter."]))
    for stem, k, x, y, steps in pz:
        s = k.rel_set(x, y, True)
        assert len(s) == 1 and None not in s, (stem, s)
        key = next(iter(s))
        q(B, M_DIR, "L3", "officer", stem, cap(key), rel_opts(key), steps + [f"Answer: {key}."],
          "Resolve 'only son/daughter of …' phrases first", "\"The only son of my father\" (said by a man) is the speaker himself.", kind="conceptual")


def ambiguity(B):
    NEUT = GENDERED + ["child", "sibling", "parent"]
    used = set()

    def amb(first_to_last):
        def c(k, pp):
            x, y = (pp[0], pp[-1]) if first_to_last else (pp[-1], pp[0])
            s = k.rel_set(x, y, True)
            if len(s) == 2 and None not in s:
                a, b = sorted(s)
                if a.replace("maternal ", "").replace("paternal ", "") in SIMPLE | INTERESTING:
                    return (x, y, s)
            return None
        return c

    def trap(first_to_last):
        def c(k, pp):
            if len(k.worlds()) < 2:
                return None
            x, y = (pp[0], pp[-1]) if first_to_last else (pp[-1], pp[0])
            s = k.rel_set(x, y, True)
            if len(s) == 1 and None not in s:
                return (x, y, next(iter(s)))
            return None
        return c

    specs = [("foundation", "L2", 2, "amb", False), ("foundation", "L2", 2, "trap", True), ("foundation", "L2", 3, "amb", True),
             ("foundation", "L2", 3, "trap", False), ("foundation", "L2", 3, "amb", False),
             ("officer", "L3", 3, "amb", True), ("officer", "L3", 4, "trap", True), ("officer", "L3", 4, "amb", False),
             ("officer", "L3", 4, "trap", False), ("officer", "L3", 4, "amb", True), ("officer", "L3", 4, "trap", True),
             ("officer", "L3", 4, "amb", False), ("officer", "L3", 5, "trap", False), ("officer", "L3", 5, "amb", True)]
    for i, (tier, lvl, n, mode, f2l) in enumerate(specs):
        pp = list("KLMNOP")[: n + 1] if i % 2 else list("DEFGHI")[: n + 1]
        cond = amb(f2l) if mode == "amb" else trap(f2l)
        ops, k, res = find_chain(f"GRB-amb-{i}", n, NEUT, cond, people=pp, avoid=used)
        used.add(tuple(ops))
        x, y = res[0], res[1]
        stem = chain_sentence(pp, ops) + f" How is {x} related to {y}?"
        unk = sorted(p for p in k.g if k.g[p] is None)
        if mode == "amb":
            s = sorted(res[2])
            wr = [(cap(t), f"assumed a gender/side that the data do not fix") for t in s]
            base = s[0]
            wr += [(cap(t), e) for t, e in confusers(base) if t not in s]
            steps = explain_chain(pp, ops) + [f"Gender not fixed for: {', '.join(unk)}.",
                                               f"Possible relations: {' or '.join(s)} → cannot be determined."]
            q(B, M_AMB, lvl, tier, stem, CBD, wr, steps, "Enumerate both genders of every unfixed person",
              "Do not assume a gender from a name or letter.", kind="conceptual")
        else:
            key = res[2]
            steps = explain_chain(pp, ops) + [f"Gender not fixed for: {', '.join(unk)} — but the asked relation is the same in every case.",
                                               f"Answer: {key}."]
            q(B, M_AMB, lvl, tier, stem, cap(key), [(CBD, "assumed an unfixed gender matters")] + rel_opts(key)[:-1], steps,
              "Check whether the unknown gender actually affects the asked relation", "An unknown gender elsewhere in the chain need not make the answer indeterminate.",
              kind="conceptual")
    # one extra officer item: which single extra fact fixes the relation (searched + verified)
    pp = list("WXYZ")

    def fixer(k, pp):
        s2 = k.rel_set("W", "Z", True)
        if len(s2) < 2 or None in s2:
            return None
        facts = {}
        for who in sorted(p for p in k.g if k.g[p] is None):
            vals = []
            for g in "mf":
                k.g[who] = g
                try:
                    vals.append(k.rel_set("W", "Z", True) if k.worlds() else {None})
                finally:
                    k.g[who] = None
            facts[who] = all(len(v) == 1 and None not in v for v in vals)
        fixing = [w for w, ok in facts.items() if ok]
        return (s2, fixing[0]) if len(fixing) == 1 else None
    ops, k, (s2, good) = find_chain("GRB-amb-fix", 3, NEUT, fixer, people=pp, avoid=used)
    others = [w for w in pp if w != good]
    stem = chain_sentence(pp, ops) + " Which one additional fact is enough to fix how W is related to Z?"
    q(B, M_AMB, "L3", "officer", stem, f"The gender of {good}",
      [(f"The gender of {others[0]}", "that gender is already fixed or irrelevant"), (f"The gender of {others[1]}", "that gender is already fixed or irrelevant"),
       (f"The gender of {others[2]}", "that gender is already fixed or irrelevant")],
      explain_chain(pp, ops) + [f"W is the {' / '.join(sorted(s2))} of Z depending on genders.", f"Only {good}'s gender changes the answer; fixing it settles the relation."],
      "Test each unknown gender for its effect", "Genders already given by words like brother/sister need no extra fact.", kind="conceptual")


# ---------------- family-tree puzzles (brute force over name → slot) ----------------
def tpl(kind):
    k = Kin()
    if kind == "T2":
        k.spouse("G1", "G2"); k.person("G1", "m"); k.person("G2", "f")
        k.parent("G1", "S", "m"); k.person("S", "m"); k.parent("G1", "D"); k.person("D", "f")
        k.spouse("S", "SW"); k.person("SW", "f"); k.parent("S", "C"); k.person("C", "m")
    elif kind == "T3":
        k.spouse("G1", "G2"); k.person("G1", "m"); k.person("G2", "f")
        for c, g in (("S1", "m"), ("S2", "m"), ("D", "f")):
            k.parent("G1", c); k.person(c, g)
        k.spouse("S1", "W1"); k.person("W1", "f"); k.parent("S1", "C1"); k.person("C1", "f")
    elif kind == "T1":
        k.spouse("G1", "G2"); k.person("G1", "m"); k.person("G2", "f")
        k.parent("G1", "S"); k.person("S", "m"); k.parent("G1", "D"); k.person("D", "f")
        k.spouse("S", "SW"); k.person("SW", "f"); k.spouse("D", "DH"); k.person("DH", "m")
        k.parent("S", "C1"); k.person("C1", "m"); k.parent("S", "C2"); k.person("C2", "f")
        k.parent("D", "C3"); k.person("C3", "m")
    elif kind == "T4":
        k.spouse("G1", "G2"); k.person("G1", "m"); k.person("G2", "f")
        for a, w in (("A1", "W1"), ("A2", "W2")):
            k.parent("G1", a); k.person(a, "m"); k.spouse(a, w); k.person(w, "f")
        k.parent("A1", "C1"); k.person("C1", "m"); k.parent("A1", "C2"); k.person("C2", "f")
        k.parent("A2", "C3"); k.person("C3", "f")
    assert len(k.worlds()) == 1
    return k


def solve_tree(kind, names, clues):
    k = tpl(kind)
    G = k.worlds()[0]
    slots = sorted(k.g)
    assert len(slots) == len(names)
    R = {(a, b): (k.rel(a, b, G, False) if a != b else None) for a in slots for b in slots}
    sols = []
    for perm in itertools.permutations(slots):
        m = dict(zip(names, perm))
        ok = True
        for c in clues:
            t = c[0]
            if t == "rel":
                ok = R[(m[c[1]], m[c[3]])] == c[2]
            elif t == "g":
                ok = G[m[c[1]]] == c[2]
            elif t == "nochild":
                ok = not k.children(m[c[1]])
            elif t == "unmarried":
                ok = k.spouse_of(m[c[1]]) is None
            elif t == "married":
                ok = k.spouse_of(m[c[1]]) is not None
            if not ok:
                break
        if ok:
            sols.append(m)
    return k, G, sols


def clue_text(c):
    t = c[0]
    if t == "rel":
        return f"{c[1]} is the {c[2]} of {c[3]}."
    if t == "g":
        return f"{c[1]} is {'male' if c[2] == 'm' else 'female'}."
    if t == "nochild":
        return f"{c[1]} has no children."
    if t == "unmarried":
        return f"{c[1]} is unmarried."
    if t == "married":
        return f"{c[1]} is married."


def tree_intro(n, gens, couples, clues):
    return (f"A family has {n} members spread over {gens} generations, with {couples} married couple{'s' if couples > 1 else ''}. "
            "Every child's parents are both family members (full siblings share both parents).\n\n" + "\n".join(f"- {clue_text(c)}" for c in clues))


def family_tree(B):
    # foundation standalone
    F = [
        ("T2", list("ABCDEF"), [("rel", "A", "husband", "F"), ("rel", "B", "son", "F"), ("rel", "E", "daughter-in-law", "A"),
                                ("rel", "C", "son", "E"), ("rel", "D", "sister", "B")], ("rel", "D", "C"), 3, 2),
        ("T2", list("PQRSTU"), [("rel", "P", "grandfather", "U"), ("rel", "Q", "wife", "R"), ("rel", "R", "father", "U"),
                                ("rel", "S", "sister", "R"), ("rel", "T", "wife", "P")], ("rel", "T", "Q"), 3, 2),
        ("T3", list("JKLMNOP"), [("rel", "J", "wife", "K"), ("rel", "L", "son", "J"), ("rel", "M", "daughter", "L"), ("rel", "N", "wife", "L"),
                                 ("rel", "O", "brother", "L"), ("rel", "P", "daughter", "K")], ("rel", "O", "M"), 3, 2),
        ("T3", list("ABCDEFG"), [("rel", "G", "granddaughter", "A"), ("rel", "B", "mother", "G"), ("rel", "C", "husband", "B"),
                                 ("rel", "D", "sister", "C"), ("rel", "E", "brother", "D"), ("rel", "F", "wife", "A")], ("rel", "B", "F"), 3, 2),
        ("T2", list("KLMNOP"), [("rel", "K", "grandson", "L"), ("rel", "M", "mother", "K"), ("rel", "N", "sister-in-law", "M"),
                                ("rel", "O", "son", "L"), ("rel", "P", "husband", "L")], ("rel", "N", "K"), 3, 2),
    ]
    for kind, names, clues, (qt, x, y), gens, couples in F:
        k, G, sols = solve_tree(kind, names, clues)
        assert len(sols) == 1, (kind, clues, len(sols))
        m = sols[0]
        key = k.rel(m[x], m[y], G, True)
        assert key
        stem = tree_intro(len(names), gens, couples, clues) + f"\n\nHow is {x} related to {y}?"
        q(B, M_TREE, "L2", "foundation", stem, cap(key), rel_opts(key),
          ["Placing members: " + ", ".join(f"{nm}" + ("(M)" if G[m[nm]] == "m" else "(F)") for nm in names) + " — the clues admit exactly one tree (checked by enumeration).",
           f"{x} → {y}: {key}."],
          "Fix couples and generations first, then read the relation", "Paternal vs maternal depends on which parent links the two.", kind="conceptual")
    # officer case sets
    SETS = [
        ("T1", list("JKLMNOPQR"), [("rel", "J", "grandmother", "O"), ("rel", "M", "son-in-law", "J"), ("rel", "K", "daughter-in-law", "L"),
                                   ("rel", "P", "brother", "O"), ("rel", "N", "wife", "M"), ("rel", "Q", "husband", "K"), ("rel", "R", "grandson", "L"),
                                   ("rel", "R", "cousin", "P")]),
        ("T4", list("ABCDEFGHI"), [("rel", "A", "father-in-law", "E"), ("rel", "B", "wife", "A"), ("rel", "C", "brother", "D"), ("rel", "E", "mother", "F"),
                                   ("rel", "G", "sister", "F"), ("rel", "H", "wife", "C"), ("rel", "I", "cousin", "G"), ("g", "F", "m"),
                                   ("rel", "I", "granddaughter", "B")]),
    ]
    for si, (kind, names, clues) in enumerate(SETS):
        k, G, sols = solve_tree(kind, names, clues)
        assert len(sols) == 1, (kind, len(sols))
        m = sols[0]
        inv = {v: nm for nm, v in m.items()}
        head = tree_intro(len(names), 3, 3, clues)
        grp = f"GRB-TREE-SET{si+1}"
        qs = []
        pairs = [("R", "P"), ("L", "R"), ("Q", "N"), ("O", "M")] if si == 0 else [("F", "I"), ("D", "G"), ("H", "G"), ("I", "A")]
        for x, y in pairs:
            key = k.rel(m[x], m[y], G, True)
            assert key, (x, y)
            qs.append((f"How is {x} related to {y}?", cap(key), rel_opts(key), [f"{x} → {y}: {key}."]))
        child = inv["C3"]
        mo = [nm for nm in names if k.rel(m[nm], m[child], G, False) == "mother"]
        assert len(mo) == 1
        fem = [nm for nm in names if G[m[nm]] == "f" and nm != mo[0] and nm != child]
        qs.append((f"Who is the mother of {child}?", mo[0], [(nm, "a female member but not the mother") for nm in fem],
                   [f"{child}'s parents: {', '.join(inv[p] for p in k.parents('C3'))}; the female parent is {mo[0]}."]))
        tree_desc = "; ".join(f"{nm}={'M' if G[m[nm]]=='m' else 'F'}" for nm in names)
        for st, key, cands, steps in qs:
            q(B, M_TREE, "L4", "officer", head + "\n\n" + st, key, cands,
              ["Enumerating all name-to-position assignments leaves exactly one family tree.", f"Genders: {tree_desc}."] + steps,
              "Anchor on unique roles (only son-in-law, grandmother) first", "Cousins share grandparents, not parents.", kind="case", group=grp)


def add_all(B):
    coded(B); direct(B); ambiguity(B); family_tree(B)
