"""Kinship engine for GIR-B blood-relation items.

Structure: couples (sets of <=2 spouses). Each person may belong to a parent-couple (pc) and a
marriage-couple (mc). Siblings share a pc (full siblings, the standard exam convention).
Unknown genders are enumerated; a world is valid when both members of every 2-person couple
have different genders. rel(x, y) names what x is to y.
"""
import itertools


class Contradiction(Exception):
    pass


class Kin:
    def __init__(self):
        self.g, self.pc, self.mc, self.cp = {}, {}, {}, {}
        self._n = 0

    def person(self, x, g=None):
        if x not in self.g:
            self.g[x] = None
        if g:
            if self.g[x] and self.g[x] != g:
                raise Contradiction(f"gender clash {x}")
            self.g[x] = g

    def _new(self, members=()):
        self._n += 1
        self.cp[self._n] = set(members)
        for m in members:
            self.mc[m] = self._n
        return self._n

    def _merge(self, a, b):
        if a == b:
            return a
        mem = self.cp[a] | self.cp[b]
        if len(mem) > 2:
            raise Contradiction("couple > 2")
        self.cp[a] = mem
        for d in (self.pc, self.mc):
            for k, v in list(d.items()):
                if v == b:
                    d[k] = a
        del self.cp[b]
        for m in mem:
            self.mc[m] = a
        return a

    def _marr(self, x):
        if x not in self.mc:
            self._new([x])
        return self.mc[x]

    def parent(self, x, y, g=None):
        self.person(x, g); self.person(y)
        c = self._marr(x)
        if y in self.pc:
            c = self._merge(c, self.pc[y])
        self.pc[y] = c
        self._check()

    def sibling(self, x, y, g=None):
        self.person(x, g); self.person(y)
        a, b = self.pc.get(x), self.pc.get(y)
        if a and b:
            self._merge(a, b)
        elif a:
            self.pc[y] = a
        elif b:
            self.pc[x] = b
        else:
            c = self._new(); self.pc[x] = c; self.pc[y] = c
        self._check()

    def spouse(self, x, y, g=None):
        self.person(x, g); self.person(y)
        a, b = self.mc.get(x), self.mc.get(y)
        if a and b:
            self._merge(a, b)
        elif a:
            if len(self.cp[a]) >= 2:
                raise Contradiction("already married")
            self.cp[a].add(y); self.mc[y] = a
        elif b:
            if len(self.cp[b]) >= 2:
                raise Contradiction("already married")
            self.cp[b].add(x); self.mc[x] = b
        else:
            self._new([x, y])
        self._check()

    def _check(self):
        # no person is own ancestor
        for x in self.g:
            seen, fr = set(), [x]
            while fr:
                p = fr.pop()
                for q in self.parents(p):
                    if q == x:
                        raise Contradiction("cycle")
                    if q not in seen:
                        seen.add(q); fr.append(q)
            if x in self.pc and x in self.mc and self.pc[x] == self.mc[x]:
                raise Contradiction("married to parent")
        for x in self.g:
            sp = self.spouse_of(x)
            if sp and (sp in self.siblings(x) or sp in self.parents(x) or x in self.parents(sp)):
                raise Contradiction("spouse is sibling/parent")

    RELS = {"father": ("parent", "m"), "mother": ("parent", "f"), "son": ("child", "m"), "daughter": ("child", "f"),
            "brother": ("sibling", "m"), "sister": ("sibling", "f"), "husband": ("spouse", "m"), "wife": ("spouse", "f"),
            "parent": ("parent", None), "child": ("child", None), "sibling": ("sibling", None), "spouse": ("spouse", None)}

    def apply(self, x, r, y):
        kind, g = self.RELS[r]
        if kind == "parent":
            self.parent(x, y, g)
        elif kind == "child":
            self.person(x, g); self.parent(y, x)
        elif kind == "sibling":
            self.sibling(x, y, g)
        else:
            self.spouse(x, y, g)

    # ---------- queries ----------
    def parents(self, x):
        return sorted(self.cp[self.pc[x]]) if x in self.pc else []

    def spouse_of(self, x):
        if x in self.mc:
            o = self.cp[self.mc[x]] - {x}
            return next(iter(o)) if o else None
        return None

    def children(self, x):
        if x not in self.mc:
            return []
        return sorted(p for p in self.g if self.pc.get(p) == self.mc[x])

    def siblings(self, x):
        if x not in self.pc:
            return []
        return sorted(p for p in self.g if p != x and self.pc.get(p) == self.pc[x])

    def worlds(self):
        unk = [p for p in self.g if self.g[p] is None]
        out = []
        for combo in itertools.product("mf", repeat=len(unk)):
            G = dict(self.g); G.update(zip(unk, combo))
            ok = all(len(c) < 2 or len({G[m] for m in c}) == 2 for c in self.cp.values())
            if ok:
                out.append(G)
        return out

    def rel(self, x, y, G, qual=True):
        g = G[x]
        pick = lambda m, f: m if g == "m" else f
        side = lambda p: ("paternal " if G[p] == "m" else "maternal ") if qual else ""
        if x in self.parents(y):
            return pick("father", "mother")
        if y in self.parents(x):
            return pick("son", "daughter")
        if self.spouse_of(y) == x:
            return pick("husband", "wife")
        if x in self.siblings(y):
            return pick("brother", "sister")
        for p in self.parents(y):
            if x in self.parents(p):
                return side(p) + pick("grandfather", "grandmother")
        for p in self.parents(x):
            if y in self.parents(p):
                return pick("grandson", "granddaughter")
        for p in self.parents(y):
            for gp in self.parents(p):
                if x in self.parents(gp):
                    return pick("great-grandfather", "great-grandmother")
        for p in self.parents(x):
            for gp in self.parents(p):
                if y in self.parents(gp):
                    return pick("great-grandson", "great-granddaughter")
        for p in self.parents(y):
            sibs = self.siblings(p)
            if x in sibs or any(self.spouse_of(s) == x for s in sibs):
                return side(p) + pick("uncle", "aunt")
        for p in self.parents(x):
            sibs = self.siblings(p)
            if y in sibs or any(self.spouse_of(s) == y for s in sibs):
                return pick("nephew", "niece")
        sp = self.spouse_of(y)
        if sp and x in self.parents(sp):
            return pick("father-in-law", "mother-in-law")
        if any(self.spouse_of(c) == x for c in self.children(y)):
            return pick("son-in-law", "daughter-in-law")
        if (sp and x in self.siblings(sp)) or any(self.spouse_of(s) == x for s in self.siblings(y)):
            return pick("brother-in-law", "sister-in-law")
        for p in self.parents(x):
            for q in self.parents(y):
                if p in self.siblings(q):
                    return "cousin"
        return None

    def rel_set(self, x, y, qual=True):
        return {self.rel(x, y, G, qual) for G in self.worlds()}


def build_chain(people, ops):
    """people: [A, B, C, ...]; ops: relation words r_i meaning people[i] r_i people[i+1]."""
    k = Kin()
    for i, r in enumerate(ops):
        k.apply(people[i], r, people[i + 1])
    if not k.worlds():
        raise Contradiction("no valid world")
    return k


FLIP = {}
for m, f in [("father", "mother"), ("son", "daughter"), ("brother", "sister"), ("husband", "wife"),
             ("grandfather", "grandmother"), ("grandson", "granddaughter"), ("uncle", "aunt"), ("nephew", "niece"),
             ("father-in-law", "mother-in-law"), ("son-in-law", "daughter-in-law"), ("brother-in-law", "sister-in-law"),
             ("great-grandfather", "great-grandmother"), ("great-grandson", "great-granddaughter")]:
    FLIP[m] = f; FLIP[f] = m
FLIP["cousin"] = "cousin"

CONF_M = {"father": ["uncle", "grandfather", "brother", "father-in-law"], "grandfather": ["father", "uncle", "great-grandfather", "father-in-law"],
          "uncle": ["father", "brother-in-law", "cousin", "grandfather"], "nephew": ["son", "grandson", "cousin", "brother"],
          "son": ["nephew", "grandson", "brother", "son-in-law"], "brother": ["cousin", "brother-in-law", "son", "nephew"],
          "husband": ["brother-in-law", "father", "son-in-law", "brother"], "father-in-law": ["father", "uncle", "brother-in-law", "grandfather"],
          "son-in-law": ["son", "nephew", "brother-in-law", "grandson"], "brother-in-law": ["brother", "uncle", "cousin", "husband"],
          "grandson": ["son", "nephew", "great-grandson", "son-in-law"], "great-grandfather": ["grandfather", "father", "uncle", "great-grandson"],
          "great-grandson": ["grandson", "son", "nephew", "great-grandfather"]}


def gender_of(term):
    base = term.replace("paternal ", "").replace("maternal ", "")
    if base == "cousin":
        return None
    for m in CONF_M:
        if base == m:
            return "m"
    return "f"


def to_gender(term, g):
    base = term.replace("paternal ", "").replace("maternal ", "")
    pre = term[: len(term) - len(base)]
    if base == "cousin":
        return term
    cur = gender_of(base)
    return pre + (base if cur == g else FLIP[base])


def confusers(term):
    """distractor candidates (term, error) for a key relation term."""
    base = term.replace("paternal ", "").replace("maternal ", "")
    pre = term[: len(term) - len(base)]
    out = []
    if pre:
        other = "maternal " if pre == "paternal " else "paternal "
        out.append((other + base, "wrong side of the family (paternal/maternal swapped)"))
    if base != "cousin":
        out.append((pre + FLIP[base], "gender of the person reversed"))
        g = gender_of(base)
        mbase = base if g == "m" else FLIP[base]
        for c in CONF_M.get(mbase, []):
            out.append((to_gender(c, g), "generation or in-law link misread"))
    else:
        out += [("brother", "treated cousin as sibling"), ("nephew", "generation shifted"), ("uncle", "generation shifted"), ("sister", "treated cousin as sibling")]
    return out


def cap(s):
    return s[0].upper() + s[1:] if s else s
