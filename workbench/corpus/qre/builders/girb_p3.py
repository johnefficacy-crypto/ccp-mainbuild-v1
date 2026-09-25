"""GIR-B part 3: Coding-Decoding (6 microtopics). Every code is produced by applying the rule in code;
inference-type items (symbol / message coding) are solved by exhaustive or signature-based deduction
and the asked element is asserted to be uniquely determined."""
from girb_common import *
from collections import Counter

M_COND = "reas-conditional-coding-with-rules-0b7eaac9"
M_SHIFT = "reas-letter-shifting-and-alphabet-position-e476a433"
M_SYM = "reas-letter-to-symbol-coding-35896380"
M_NUM = "reas-number-and-digit-coding-722eaafb"
M_WF = "reas-word-formation-from-given-letters-3a6e82a0"
M_MSG = "reas-word-substitution-message-coding-fe3dbcfc"
VOW = set("AEIOU")


# ---------------- conditional coding ----------------
def cond_code(word, table, conds, skip=None, only=None):
    base = [table[c] for c in word]
    for i, (name, test, act, _) in enumerate(conds):
        if skip is not None and i == skip:
            continue
        if only is not None and i != only:
            continue
        if test(word):
            return "".join(act(word, list(base), table)), i
    return "".join(base), None


def conditional(B):
    def mk_table(seed, letters, codes):
        r = random.Random(seed)
        cs = list(codes); r.shuffle(cs)
        return dict(zip(letters, cs))

    def swap_ends(w, b, t):
        b[0], b[-1] = b[-1], b[0]; return b

    def both_last(w, b, t):
        b[0] = b[-1]; return b

    def fixed(sym1, sym2):
        def f(w, b, t):
            b[0] = sym1; b[-1] = sym2; return b
        return f

    def second_last_swap(w, b, t):
        b[1], b[-2] = b[-2], b[1]; return b

    def all_vowels(sym):
        def f(w, b, t):
            return [sym if c in VOW else x for c, x in zip(w, b)]
        return f

    FC = [("i", lambda w: w[0] in VOW and w[-1] not in VOW, swap_ends, "If the first letter is a vowel and the last letter is a consonant, their codes are interchanged."),
          ("ii", lambda w: w[0] not in VOW and w[-1] not in VOW, both_last, "If both the first and the last letters are consonants, the first letter takes the code of the last letter.")]
    OC = [("i", lambda w: w[0] in VOW and w[-1] in VOW, fixed("★", "★"), "If both the first and the last letters are vowels, both are coded as ★."),
          ("ii", lambda w: w[0] not in VOW and w[-1] in VOW, swap_ends, "If the first letter is a consonant and the last letter is a vowel, their codes are interchanged."),
          ("iii", lambda w: w[1] in VOW and w[-2] in VOW, second_last_swap, "If the second and the second-last letters are both vowels, their codes are interchanged."),
          ("iv", lambda w: w[0] not in VOW and w[-1] not in VOW, fixed("©", "δ"), "If both the first and the last letters are consonants, the first is coded as © and the last as δ.")]

    def run(tier, lvl, table, conds, words, group, seed):
        tab_md = "| Letter | " + " | ".join(table) + " |\n|" + "---|" * (len(table) + 1) + "\n| Code | " + " | ".join(table.values()) + " |"
        rules = "\n".join(f"({c[0]}) {c[3]}" for c in conds)
        head = (f"Letters are coded as follows:\n\n{tab_md}\n\nConditions (apply only the first condition that holds, in the order given; "
                f"if none holds, code each letter directly):\n{rules}")
        for w in words:
            key, used = cond_code(w, table, conds)
            cands = []
            plain, _ = cond_code(w, table, [])
            if used is not None:
                cands.append((plain, "applied no condition"))
            for j in range(len(conds)):
                if j != used:
                    alt = "".join(conds[j][2](w, [table[c] for c in w], table))
                    cands.append((alt, f"applied condition ({conds[j][0]}) wrongly"))
            if used is not None:
                nxt, _ = cond_code(w, table, conds, skip=used)
                cands.append((nxt, "skipped the first applicable condition"))
            b = [table[c] for c in w]
            b2 = list(b); b2[1], b2[2] = b2[2], b2[1]
            cands.append(("".join(b2), "letters 2 and 3 coded in swapped order"))
            b3 = list(key); b3[-1], b3[-2] = b3[-2], b3[-1]
            cands.append(("".join(b3), "last two codes swapped"))
            stem = f"What is the code for '{w}'?"
            ctext = f"condition ({conds[used][0]})" if used is not None else "no condition"
            q(B, M_COND, lvl, tier, head + "\n\n" + stem, key, cands,
              [f"Direct codes: {' '.join(b)}.", f"'{w}': first {w[0]} ({'vowel' if w[0] in VOW else 'consonant'}), last {w[-1]} ({'vowel' if w[-1] in VOW else 'consonant'}) → {ctext} applies.",
               f"Code = {key}."], "Check conditions in order; apply only the first that holds",
              "Test the conditions strictly in the listed order — a later condition may also fit.", kind="case" if group else "conceptual", group=group)

    tF = mk_table("GRB-condF", list("AEKMPRTUW"), list("518247396"))
    wordsF = ["AKMRT", "PEMKA", "TAKEM", "UPRMW", "MAPEU"]
    for w in wordsF:
        assert all(c in tF for c in w)
    run("foundation", "L2", tF, FC, wordsF, None, "F")
    t1 = mk_table("GRB-condO1", list("ABDEGHIJLNOU"), list("7@3#9$1%48&2"))
    w1 = ["ABHJE", "DUHLA", "GIDOL", "NBHJD", "EGHLN"]
    t2 = mk_table("GRB-condO2", list("CEFIKMOPRSTU"), list("4*8©2%6#9$1&"))
    w2 = ["OKMSE", "FIPRT", "TOKEM", "SKMPU", "UCMKR"]
    for tab, ws in ((t1, w1), (t2, w2)):
        for w in ws:
            assert all(c in tab for c in w), w
    # ensure variety of conditions triggered
    for tab, ws in ((t1, w1), (t2, w2)):
        used = {cond_code(w, tab, OC)[1] for w in ws}
        assert len(used) == 5, used
    run("officer", "L4", t1, OC, w1, "GRB-COND-SET1", "O1")
    run("officer", "L4", t2, OC, w2, "GRB-COND-SET2", "O2")


# ---------------- letter shifting ----------------
def sh(w, k):
    return "".join(L(P(c) + k) for c in w)


def opp(w):
    return "".join(L(27 - P(c)) for c in w)


def shifting(B):
    R_ = {
        "+1": lambda w: sh(w, 1), "-1": lambda w: sh(w, -1), "+2": lambda w: sh(w, 2), "-2": lambda w: sh(w, -2), "+3": lambda w: sh(w, 3),
        "alt+1-1": lambda w: "".join(L(P(c) + (1 if i % 2 == 0 else -1)) for i, c in enumerate(w)),
        "alt-1+1": lambda w: "".join(L(P(c) + (-1 if i % 2 == 0 else 1)) for i, c in enumerate(w)),
        "rev": lambda w: w[::-1], "rev+1": lambda w: sh(w[::-1], 1), "rev-1": lambda w: sh(w[::-1], -1), "rev+2": lambda w: sh(w[::-1], 2),
        "opp": opp, "opp+1": lambda w: sh(opp(w), 1), "pos+i": lambda w: "".join(L(P(c) + i + 1) for i, c in enumerate(w)),
        "pos-i": lambda w: "".join(L(P(c) - i - 1) for i, c in enumerate(w)),
        "v+1c-1": lambda w: "".join(L(P(c) + (1 if c in VOW else -1)) for c in w),
        "v-1c+1": lambda w: "".join(L(P(c) + (-1 if c in VOW else 1)) for c in w),
        "halves": lambda w: w[: len(w) // 2][::-1] + w[len(w) // 2:][::-1],
        "halves+1": lambda w: sh(w[: len(w) // 2][::-1] + w[len(w) // 2:][::-1], 1),
    }
    DESC = {"+1": "each letter moved one place forward", "-1": "each letter moved one place back", "+2": "each letter moved two places forward",
            "-2": "each letter moved two places back", "+3": "each letter moved three places forward",
            "alt+1-1": "letters alternately +1 and −1", "alt-1+1": "letters alternately −1 and +1", "rev": "word written in reverse",
            "rev+1": "word reversed, then each letter +1", "rev-1": "word reversed, then each letter −1", "rev+2": "word reversed, then each letter +2",
            "opp": "each letter replaced by its opposite (A↔Z)", "opp+1": "opposite letter, then +1",
            "pos+i": "letter at position n moved n places forward", "pos-i": "letter at position n moved n places back",
            "v+1c-1": "vowels +1, consonants −1", "v-1c+1": "vowels −1, consonants +1",
            "halves": "each half of the word reversed", "halves+1": "each half reversed, then each letter +1"}
    NEAR = {"rev": ["rev+1", "halves", "rev-1"], "+1": ["+2", "-1", "rev+1"], "-1": ["+1", "-2", "rev-1"], "+2": ["+1", "+3", "rev+2"], "-2": ["-1", "+2", "rev-1"],
            "+3": ["+2", "rev+2", "+1"], "alt+1-1": ["alt-1+1", "+1", "-1"], "alt-1+1": ["alt+1-1", "-1", "+1"],
            "rev+1": ["rev-1", "+1", "rev"], "rev-1": ["rev+1", "-1", "rev"], "rev+2": ["rev+1", "+2", "rev"],
            "opp": ["opp+1", "rev", "-1"], "opp+1": ["opp", "rev+1", "+1"], "pos+i": ["pos-i", "+1", "rev+1"], "pos-i": ["pos+i", "-1", "rev-1"],
            "v+1c-1": ["v-1c+1", "+1", "-1"], "v-1c+1": ["v+1c-1", "-1", "+1"], "halves": ["rev", "halves+1", "rev+1"],
            "halves+1": ["halves", "rev+1", "+1"]}
    items = [("foundation", "L1", "+1", "MANGO", "APPLE", "enc"), ("foundation", "L1", "-1", "TABLE", "CHAIR", "enc"),
             ("foundation", "L1", "rev", "PLANT", "STONE", "enc"), ("foundation", "L2", "+2", "RIVER", "CLOUD", "enc"),
             ("foundation", "L2", "opp", "GOLD", "IRON", "enc"),
             ("officer", "L2", "alt+1-1", "GARDEN", "MARKET", "enc"), ("officer", "L3", "rev+1", "SILVER", "BRIDGE", "enc"),
             ("officer", "L3", "pos+i", "WINTER", "CANDLE", "enc"), ("officer", "L3", "v+1c-1", "FOREST", "PENCIL", "enc"),
             ("officer", "L3", "opp+1", "BASKET", "TEMPLE", "enc"), ("officer", "L3", "halves", "MIRROR", "POCKET", "enc"),
             ("officer", "L3", "rev-1", "ORANGE", "PLANET", "dec"), ("officer", "L3", "pos-i", "SUMMER", "FLOWER", "dec"),
             ("officer", "L3", "halves+1", "CASTLE", "SPIDER", "dec"), ("officer", "L3", "alt-1+1", "ROCKET", "GUITAR", "dec")]
    for tier, lvl, r, ex, tgt, mode in items:
        f = R_[r]
        exc = f(ex)
        # the example must not also be explained by a near rule
        for n in NEAR[r]:
            assert R_[n](ex) != exc, (r, n, ex)
        if mode == "enc":
            key = f(tgt)
            stem = f"In a certain code language, '{ex}' is written as '{exc}'. How is '{tgt}' written in that code?"
            cands = [(R_[n](tgt), f"applied '{DESC[n]}' instead") for n in NEAR[r]]
            steps = [f"{ex} → {exc}: {DESC[r]}.", f"{tgt} → {key}."]
        else:
            code = f(tgt)
            key = tgt
            # distractors: words whose code differs (one letter changed / near-anagram)
            alts = [tgt[:-1] + L(P(tgt[-1]) + 1), tgt[1:] + tgt[0], tgt[0] + tgt[2] + tgt[1] + tgt[3:]]
            for a in alts:
                assert f(a) != code
            stem = f"In a certain code language, '{ex}' is written as '{exc}'. Which word is written as '{code}' in that code?"
            cands = [(alts[0], "decoded the last letter one place off"), (alts[1], "rotated instead of reversing"), (alts[2], "two letters decoded in swapped order")]
            steps = [f"{ex} → {exc}: {DESC[r]}.", f"Reverse the operation on '{code}' → {key}."]
        q(B, M_SHIFT, lvl, tier, stem, key, cands, steps, "Compare letter positions of the word and its code",
          "Test the rule on every letter of the example; a rule that fits only the first letter is wrong.", kind="conceptual")


# ---------------- letter to symbol ----------------
def symbol(B):
    # foundation: order-preserving, deduce from examples
    F = [
        ({"CAT": "#@$", "TAP": "$@%"}, "PACT", "positional"),
        ({"DOG": "&*!", "GOLD": "!*+&"}, "LOG", "positional"),
        ({"RAIN": "©@%β", "NAIL": "β@%δ"}, "LAIR", "positional"),
        ({"SEAT": "$#@&", "TEAM": "&#@*"}, "MEAT", "positional"),
        ({"MILK": "@#$%", "KILN": "%#$&"}, "LINK", "positional"),
    ]
    for ex, tgt, _ in F:
        mp = {}
        for w, c in ex.items():
            assert len(w) == len(c)
            for a, b in zip(w, c):
                assert mp.get(a, b) == b
                mp[a] = b
        assert len(set(mp.values())) == len(mp)
        assert all(ch in mp for ch in tgt)
        key = "".join(mp[ch] for ch in tgt)
        k2 = list(key); k2[0], k2[1] = k2[1], k2[0]
        k3 = key[::-1]
        k4 = list(key); k4[-1], k4[-2] = k4[-2], k4[-1]
        stem = "In a certain code, " + " and ".join(f"'{w}' is written as '{c}'" for w, c in ex.items()) + f". How is '{tgt}' written in that code?"
        q(B, M_SYM, "L1" if len(tgt) <= 3 else "L2", "foundation", stem, key,
          [("".join(k2), "first two symbols swapped"), (k3, "wrote the code in reverse"), ("".join(k4), "last two symbols swapped")],
          ["Letter-to-symbol pairs: " + ", ".join(f"{a}={b}" for a, b in mp.items()) + ".", f"{tgt} → {key}."],
          "Read the letter-symbol pairs position by position", "Keep the order of the new word, not of the examples.", kind="conceptual")
    # officer: order NOT preserved; solve by enumerating bijections
    symsets = ["@#$%&*©", "★@#$%&β", "π@#$%&*", "@#$%&©δ", "#$%&*★β"]
    specs = []
    rng = random.Random("GRB-sym")
    letters_pool = ["PRSTEAN", "LMOCIDE", "BRAKEST", "GLOWMAN", "FIRSTEP"]
    made = 0
    si = 0
    while made < 10:
        letters = list(letters_pool[si % 5]); syms = list(symsets[si % 5]); si += 1
        truth = dict(zip(letters, rng.sample(syms, len(syms))))
        # pick 3-4 random letter groups (words as groups of letters)
        for _ in range(200):
            groups = ["".join(rng.sample(letters, rng.choice([3, 4]))) for _ in range(4)]
            if len(set(groups)) < 4:
                continue
            ul = sorted({c for g in groups for c in g})
            us = [truth[c] for c in ul]
            sols = []
            for perm in itertools.permutations(us):
                m = dict(zip(ul, perm))
                if all({m[c] for c in g} == {truth[c] for c in g} for g in groups):
                    sols.append(m)
            det_letters = [c for c in ul if len({s[c] for s in sols}) == 1]
            undet = [c for c in ul if c not in det_letters]
            if 1 <= len(det_letters) <= 4 and undet:
                letters, syms = ul, us
                break
        else:
            continue
        codes = {g: "".join(rng.sample([truth[c] for c in g], len(g))) for g in groups}
        head = ("In a certain code, each letter is replaced by a symbol, but the symbols are NOT written in the same order as the letters.\n\n" +
                "\n".join(f"- '{g}' is coded as '{codes[g]}'" for g in groups))
        # ask: symbol for determined letter
        c = det_letters[0]
        key = truth[c]
        others = [s for s in syms if s != key]
        rng.shuffle(others)
        stem = head + f"\n\nWhich symbol stands for the letter {c}?"
        # prefer distractors from the same groups as c
        pref = [truth[x] for g in groups if c in g for x in g if x != c]
        cand = [(s, "a symbol shared with a group containing the letter") for s in dict.fromkeys(pref)] + [(s, "symbol of another letter") for s in others]
        q(B, M_SYM, "L3", "officer", stem, key, cand,
          [f"Letter {c} appears in: {', '.join(g for g in groups if c in g)}; it is absent from: {', '.join(g for g in groups if c not in g) or 'none'}.",
           f"The only symbol with exactly the same pattern of appearances is {key}.", f"Exhaustive check of all letter→symbol assignments confirms {c} = {key}."],
          "Match each letter to the symbol with the same appearance pattern", "Intersect the codes of the groups that contain the letter and remove symbols from groups that do not.")
        made += 1
        if made >= 10:
            break
        # second question on the same data: which letter is coded as a determined symbol (different letter) or undetermined answer
        if len(det_letters) >= 2:
            c2 = det_letters[1]
            key2 = c2
            stem2 = head + f"\n\nWhich letter is coded as '{truth[c2]}'?"
            cand2 = [(x, "letter whose symbol is not fixed by the data" if x in undet else "letter coded by another symbol") for x in letters if x != c2]
            q(B, M_SYM, "L3", "officer", stem2, key2, cand2,
              [f"Symbol {truth[c2]} appears exactly in the codes of the groups containing {c2}.", f"Exhaustive check confirms {truth[c2]} = {c2}."],
              "Appearance-pattern matching", "A letter appearing in the same groups as another cannot be pinned down.")
            made += 1
        else:
            u = undet[0]
            poss = sorted({s[u] for s in sols})
            stem3 = head + f"\n\nWhich of the following is true about the symbol for the letter {u}?"
            keyt = "It cannot be determined uniquely"
            cand3 = [(f"It is {s}", "picked one of several possible symbols") for s in poss] + [(f"It is {s}", "symbol of another letter") for s in syms if s not in poss]
            q(B, M_SYM, "L3", "officer", stem3, keyt, cand3,
              [f"Letter {u} shares its appearance pattern with another letter, so its symbol could be any of {', '.join(poss)}.", "Hence it cannot be determined."],
              "Appearance-pattern matching", "Two letters appearing in exactly the same groups cannot be separated.")
            made += 1


# ---------------- number & digit coding ----------------
def numcode(B):
    def dig(n, f):
        return "".join(str(f(int(d), i)) for i, d in enumerate(str(n)))
    items = []
    # foundation
    a, b = "4739", dig("4739", lambda d, i: (d + 1) % 10)
    key = dig("5628", lambda d, i: (d + 1) % 10)
    items.append(("foundation", "L1", f"In a code, {a} is written as {b} (after 9 comes 0). How is 5628 written?", key,
                  [(dig("5628", lambda d, i: (d - 1) % 10), "subtracted 1"), (dig("5628", lambda d, i: (d + 2) % 10), "added 2"), (key[::-1], "reversed the result")],
                  ["Each digit +1 (9 → 0).", f"5628 → {key}."]))
    s = lambda w: sum(P(c) for c in w)
    items.append(("foundation", "L1", f"If CAT = {s('CAT')} and DOG = {s('DOG')}, then BAT = ?", s("BAT"),
                  [(s("BAT") + 1, "took B as 3"), (2 * 1 * 20, "multiplied positions"), (s("BAT") - 2, "dropped B")],
                  ["Code = sum of alphabet positions.", f"B(2) + A(1) + T(20) = {s('BAT')}."]))
    pos = lambda w: "".join(str(P(c)) for c in w)
    items.append(("foundation", "L1", f"If BAG is coded as {pos('BAG')}, how is FACE coded?", pos("FACE"),
                  [("6153", "last two letters swapped"), ("6135" + "0", "added a zero"), ("7135", "F taken as 7")],
                  ["Each letter → its alphabet position: B2 A1 G7.", f"F6 A1 C3 E5 → {pos('FACE')}."]))
    rz = lambda w: "".join(str(27 - P(c)) for c in w)
    items.append(("foundation", "L2", f"If A = 26, B = 25, …, Z = 1, what is the code for 'SKY' written as the three numbers side by side?", rz("SKY"),
                  [(pos("SKY"), "used forward positions"), ("8162", "Y taken as 2... misplaced"), ("81625", "K taken as 15")],
                  ["Reverse position = 27 − forward position.", f"S → 8, K → 16, Y → 2 → {rz('SKY')}."]))
    rev = lambda n: str(n)[::-1]
    items.append(("foundation", "L2", "In a code, 2468 is written as 8642 and 1357 as 7531. How is 9304 written?", rev(9304),
                  [("9403", "reversed only the middle"), ("0493", "swapped pairs"), ("4039", "rotated")],
                  ["The digits are written in reverse order.", "9304 → 4039."]))
    # fix the foundation SKY distractors to be computed sensibly
    items[3] = (items[3][0], items[3][1], items[3][2], rz("SKY"),
                [(pos("SKY"), "used forward positions (A = 1)"), (rz("SKY")[:-1] + "3", "Y taken as 3"), ("816" + "1", "Y taken as 1")], items[3][5])
    items[2] = (items[2][0], items[2][1], items[2][2], pos("FACE"), [("6153", "last two letters swapped"), ("7135", "F taken as 7"), ("6125", "C taken as 2")], items[2][5])
    items[4] = (items[4][0], items[4][1], items[4][2], rev(9304), [("9403", "reversed only the last three digits"), ("3049", "moved the first digit to the end"), ("0493", "swapped adjacent pairs")], items[4][5])
    # officer
    n = "5827461"
    t = dig(n, lambda d, i: d + 1 if d % 2 else d - 1)
    assert len(t) == len(n)
    ev = sum(1 for d in t if int(d) % 2 == 0)
    items.append(("officer", "L3", f"In the number {n}, 1 is added to each odd digit and 1 is subtracted from each even digit. How many even digits will the new number have?",
                  ev, [(sum(1 for d in n if int(d) % 2 == 0), "counted even digits of the original number"), (len(n), "assumed all digits become even")],
                  [f"New number: {t}.", "Adding/subtracting 1 flips parity, so the new even digits are the old odd digits.", f"Even digits: {ev}."]))
    nn = "639418275"
    t2 = "".join(sorted(nn))
    mid = t2[len(t2) // 2]
    diff_pos = sum(1 for a, b in zip(nn, t2) if a == b)
    items.append(("officer", "L3", f"If the digits of {nn} are arranged in ascending order, how many digits will remain at the same position?",
                  diff_pos, [(diff_pos + 1, "counted the middle digit twice"), (len(nn) - diff_pos, "counted digits that moved"), (diff_pos + 2, "counted a near-miss")],
                  [f"Ascending: {t2}.", "Positions unchanged: " + (", ".join(f"{a} (position {i+1})" for i, (a, b) in enumerate(zip(nn, t2)) if a == b) or "none") + f" → {diff_pos}."]))
    # word → number via rule verified on two examples
    f1 = lambda w: sum(P(c) for c in w) * len(w)
    assert f1("ACE") == 27 and f1("BD") == 12
    items.append(("officer", "L3", f"In a code, ACE = {f1('ACE')} and BD = {f1('BD')}. What is the code for FIG?", f1("FIG"),
                  [(sum(P(c) for c in "FIG"), "sum of positions only"), (f1("FIG") + 3, "multiplied by 4"), (6 * 9 * 7, "product of positions")],
                  ["ACE: (1 + 3 + 5) × 3 = 27; BD: (2 + 4) × 2 = 12 → sum of positions × number of letters.", f"FIG: (6 + 9 + 7) × 3 = {f1('FIG')}."]))
    items[-1] = (items[-1][0], items[-1][1], items[-1][2], f1("FIG"),
                 [(sum(P(c) for c in "FIG"), "sum of positions only"), (sum(P(c) for c in "FIG") * 4, "multiplied by 4"), (6 * 9 * 7, "product of positions")], items[-1][5])
    f2 = lambda w: "".join(str(P(c) * 2) for c in w)
    items.append(("officer", "L2", f"If BAD is written as {f2('BAD')} and CAB as {f2('CAB')}, how is DEAF written?", f2("DEAF"),
                  [("".join(str(P(c) + 2) for c in "DEAF"), "added 2 instead of doubling"), ("".join(str(P(c)) for c in "DEAF"), "used plain positions"),
                   ("".join(str(P(c) * 2) for c in "DEFA"), "last two letters swapped")],
                  ["Each letter → 2 × its position: B4 A2 D8.", f"D8 E10 A2 F12 → {f2('DEAF')}."]))
    f3 = lambda n: "".join(str(9 - int(d)) for d in n)
    items.append(("officer", "L2", f"In a code, 2718 is written as {f3('2718')} and 4350 as {f3('4350')}. How is 6093 written?", f3("6093"),
                  [(f3("6093")[::-1], "reversed after coding"), ("".join(str((int(d) + 1) % 10) for d in "6093"), "added 1"), ("".join(str(10 - int(d)) if d != "0" else "0" for d in "6093"), "used 10 − d")],
                  ["Each digit d → 9 − d.", f"6093 → {f3('6093')}."]))
    f4 = lambda n: n[1] + n[0] + n[3] + n[2] + n[5] + n[4]
    items.append(("officer", "L2", f"In a code, 385146 is written as {f4('385146')} and 902713 as {f4('902713')}. How is 657281 written?", f4("657281"),
                  [("657281"[::-1], "reversed the whole number"), ("567281", "swapped only the first pair"), ("758621", "rotated pairs")],
                  ["Each adjacent pair of digits is swapped.", f"65 72 81 → 56 27 18 → {f4('657281')}."]))
    s3 = lambda w: sum(P(c) for c in w) - len(w)
    assert s3("HAT") == 26
    items.append(("officer", "L3", f"If HAT = {s3('HAT')} and PEN = {s3('PEN')}, then BOX = ?", s3("BOX"),
                  [(sum(P(c) for c in "BOX"), "forgot to subtract the number of letters"), (s3("BOX") - 3, "subtracted twice"), (s3("BOX") + 1, "took O as 16")],
                  [f"HAT: 8 + 1 + 20 = 29, minus 3 letters = 26; PEN: 16 + 5 + 14 = 35 − 3 = 32 → sum − number of letters.", f"BOX: 2 + 15 + 24 = 41 − 3 = {s3('BOX')}."]))
    assert s3("PEN") == 32
    mul = lambda w: math.prod(P(c) for c in w)
    items.append(("officer", "L3", f"If ACE = {mul('ACE')} and BAD = {mul('BAD')}, then CAB = ?", mul("CAB"),
                  [(sum(P(c) for c in "CAB"), "added positions"), (mul("CAB") * 2, "doubled"), (mul("CAB") + 3, "added the letter count")],
                  ["ACE: 1 × 3 × 5 = 15; BAD: 2 × 1 × 4 = 8 → product of positions.", f"CAB: 3 × 1 × 2 = {mul('CAB')}."]))
    # sum rule check: ACE sum=9 != 15, so product rule unique
    assert sum(P(c) for c in "ACE") != mul("ACE")
    nb = "73916"
    t5 = "".join(str(int(d) ** 2 % 10) for d in nb)
    items.append(("officer", "L3", f"In a code, each digit of a number is replaced by the unit digit of its square. Using this code, {nb} becomes:", t5,
                  [("".join(str(int(d) ** 2) for d in nb), "wrote the full squares"),
                   ("".join(str(int(d) * 2 % 10) for d in nb), "doubled instead of squaring"), (t5[::-1], "reversed the result")],
                  [f"Unit digits of squares: " + ", ".join(f"{d}²→{int(d)**2 % 10}" for d in nb) + ".", f"Code = {t5}."]))
    wc = {"ROSE": "6821", "CHAIR": "73456", "PREACH": "961473"}
    mp = {}
    for w, c in wc.items():
        for a, d in zip(w, c):
            assert mp.get(a, d) == d
            mp[a] = d
    assert len(set(mp.values())) == len(mp)
    k6 = "".join(mp[c] for c in "SEARCH")
    items.append(("officer", "L3", "In a code, " + ", ".join(f"{w} is written as {c}" for w, c in wc.items()) + ". How is SEARCH written?", k6,
                  [(k6[:4] + k6[5] + k6[4], "C and H codes swapped"), (k6[0] + k6[2] + k6[1] + k6[3:], "E and A codes swapped"), (k6[:3] + k6[4] + k6[3] + k6[5], "R and C codes swapped")],
                  ["Letter → digit pairs from the examples: " + ", ".join(f"{a}={d}" for a, d in mp.items()) + ".", f"S E A R C H → {k6}."]))
    for tier, lvl, stem, key, cands, steps in items:
        q(B, M_NUM, lvl, tier, stem, key, numd(key, cands) if isinstance(key, int) else cands, steps,
          "Find the rule from the example(s), then apply it", "Confirm the rule on every example before applying it.")


# ---------------- word formation ----------------
def formable(w, base):
    cb, cw = Counter(base), Counter(w)
    return all(cb[c] >= n for c, n in cw.items())


def wordform(B):
    BASES = {
        "ADMINISTRATION": ["STATION", "RATION", "DOMINANT", "TRANSIT", "MANTRA", "NATION", "TRADITION", "DIARIST", "MINISTER", "DOCTRINE", "SANITARY", "ANIMATE"],
        "RESPONSIBILITY": ["SENSIBILITY", "PROBE", "BISTRO", "SPINY", "POLITE", "PISTOL", "POSITION", "PRESTIGE", "ROBUST", "TENSILE"],
        "INTERNATIONAL": ["RATIONAL", "NATIONAL", "LATTER", "INTERN", "TOTAL", "RENTAL", "ORIENTAL", "RETAIN", "LANTERN", "TERMINAL", "ENTRANCE", "ALTERNATE"],
        "CONSTITUTION": ["COUNTS", "STOIC", "TUITION", "NOTION", "COTTON", "INSTINCT", "UNCTION", "SUCTION", "CONTEST", "CUSTOM", "COUNSEL"],
        "DEMONSTRATION": ["MONSTER", "STATION", "MODERATION", "DORMANT", "MENTOR", "ROTATION", "DOMINANT", "TRANSMIT", "ANIMATED", "MEDITATE", "STANDARD"],
    }
    info = {b: ([w for w in ws if formable(w, b)], [w for w in ws if not formable(w, b)]) for b, ws in BASES.items()}
    for b, (can, cannot) in info.items():
        assert len(can) >= 3 and len(cannot) >= 3, (b, can, cannot)

    def why(w, b):
        cb, cw = Counter(b), Counter(w)
        miss = [f"{c} needed {n}, available {cb[c]}" for c, n in cw.items() if cb[c] < n]
        return "; ".join(miss)
    bl = list(BASES)
    plan = [("foundation", "L1", "cannot", 0), ("foundation", "L1", "cannot", 1), ("foundation", "L2", "can", 2), ("foundation", "L2", "cannot", 3),
            ("officer", "L3", "can", 4),
            ("officer", "L2", "cannot", 2), ("officer", "L3", "can", 0), ("officer", "L3", "count", 1), ("officer", "L3", "count", 3),
            ("officer", "L3", "cannot", 4), ("officer", "L3", "can", 1), ("officer", "L3", "count", 4)]
    for n, (tier, lvl, mode, bi) in enumerate(plan):
        b = bl[bi]
        can, cannot = info[b]
        r = random.Random(f"GRB-wf-{n}")
        if mode == "cannot":
            key = r.choice(cannot)
            others = r.sample(can, 3)
            stem = f"Which of the following words CANNOT be formed using the letters of the word '{b}' (each letter used only as often as it appears)?"
            q(B, M_WF, lvl, tier, stem, key, [(w, "can be formed") for w in others],
              [f"{key}: {why(key, b)} → cannot be formed.", "Each other option's letters are all available in the required numbers."],
              "Compare letter counts with the given word", "Check repeated letters: a letter used twice must appear twice in the given word.", kind="conceptual")
        elif mode == "can":
            key = r.choice(can)
            others = r.sample(cannot, 3)
            stem = f"Which of the following words CAN be formed using the letters of the word '{b}' (each letter used only as often as it appears)?"
            q(B, M_WF, lvl, tier, stem, key, [(w, f"cannot be formed ({why(w, b)})") for w in others],
              [f"{key}: all letters available.", "Others fail: " + "; ".join(f"{w} ({why(w, b)})" for w in others) + "."],
              "Compare letter counts with the given word", "Check every letter, including repeats.", kind="conceptual")
        else:
            pool = r.sample(can, 3) + r.sample(cannot, 2)
            r.shuffle(pool)
            k = sum(formable(w, b) for w in pool)
            stem = f"How many of the following words can be formed using the letters of '{b}' (each letter used only as often as it appears)?\n\n" + ", ".join(pool)
            q(B, M_WF, lvl, tier, stem, k, numd(k, [(5, "ignored letter counts"), (k - 1, "rejected a word with a repeated letter wrongly")]),
              ["Check each: " + "; ".join(f"{w} {'✓' if formable(w, b) else '✗ (' + why(w, b) + ')'}" for w in pool) + ".", f"Count = {k}."],
              "Letter-count comparison", "A word may look formable until you count a repeated letter.")
    # anagram items: exactly one option uses exactly the same letters
    AN = [("foundation", "L1", "LISTEN", "SILENT", ["SILENCE", "LENTIL", "LISTED"]),
          ("officer", "L2", "MASTER", "STREAM", ["STEAMS", "MATTER", "SMARTER"]),
          ("officer", "L3", "TRIANGLE", "INTEGRAL", ["TRAILING", "RATTLING", "ENTAILS"])]
    for tier, lvl, base, key, others in AN:
        assert sorted(key) == sorted(base)
        for o in others:
            assert sorted(o) != sorted(base), o
        q(B, M_WF, lvl, tier, f"Which of the following words uses exactly the letters of '{base}', each exactly once?", key,
          [(o, "one or more letters differ") for o in others],
          [f"Sorted letters of {base}: {''.join(sorted(base))}.", f"{key} sorts to the same string; the others differ."],
          "Anagram check by sorting letters", "Similar-looking words often add or drop one letter.", kind="conceptual")


# ---------------- message (word substitution) coding ----------------
def signatures(sents, codes):
    words = sorted({w for s in sents for w in s})
    cds = sorted({c for s in codes for c in s})
    sw = {w: tuple(w in s for s in sents) for w in words}
    sc = {c: tuple(c in s for s in codes) for c in cds}
    return sw, sc


def message(B):
    V = ["sun", "rises", "early", "birds", "sing", "sweetly", "rain", "falls", "gently", "farmers", "work", "hard", "children", "play", "outside",
         "river", "flows", "fast", "wind", "blows", "cold", "stars", "shine", "bright", "trees", "grow", "tall"]
    C = ["ka", "lo", "mi", "pu", "zo", "te", "ri", "ba", "ne", "su", "fo", "gi", "ju", "xa", "we", "hy", "qo", "ve"]
    made = {"foundation": 0, "officer": 0}
    target = {"foundation": 5, "officer": 10}
    seed = 0
    while made["foundation"] < 5 or made["officer"] < 10:
        seed += 1
        r = random.Random(f"GRB-msg-{seed}")
        tier = "foundation" if made["foundation"] < 5 else "officer"
        nw, ns, ln = (5, 3, 3) if tier == "foundation" else (8, 4, 4)
        words = r.sample(V, nw)
        codes = r.sample(C, nw)
        truth = dict(zip(words, codes))
        sents = []
        for _ in range(ns):
            sents.append(r.sample(words, ln))
        if any(sorted(a) == sorted(b) for a, b in itertools.combinations(sents, 2)):
            continue
        csents = [[truth[w] for w in s] for s in sents]
        for cs in csents:
            r.shuffle(cs)
        sw, sc = signatures(sents, csents)
        allw = sorted(sw)
        uniq = [w for w in allw if sum(1 for x in allw if sw[x] == sw[w]) == 1]
        amb = [w for w in allw if w not in uniq and any(sw[w]) ]
        if not uniq or not amb:
            continue
        # verify signature logic by brute force on small cases
        allc = sorted(sc)
        if len(allw) <= 8:
            sols = []
            for perm in itertools.permutations(allc):
                m = dict(zip(allw, perm))
                if all(sorted(m[w] for w in s) == sorted(cs) for s, cs in zip(sents, csents)):
                    sols.append(m)
            for w in uniq:
                assert len({s[w] for s in sols}) == 1
            for w in amb:
                assert len({s[w] for s in sols}) > 1
        head = "In a certain code language:\n\n" + "\n".join(f"- '{' '.join(s)}' is written as '{' '.join(cs)}'" for s, cs in zip(sents, csents))
        head += "\n\n(The code words are not necessarily in the same order as the words.)"
        w = r.choice(uniq)
        key = truth[w]
        pref = [truth[x] for s in sents if w in s for x in s if x != w]
        cands = [(c, "code of a word appearing alongside it") for c in dict.fromkeys(pref)] + [(c, "code of another word") for c in allc if c != key]
        lvl = "L2" if tier == "foundation" else "L3"
        q(B, M_MSG, lvl, tier, head + f"\n\nWhat is the code for '{w}'?", key, cands,
          [f"'{w}' appears in sentence(s) {', '.join(str(i+1) for i, s in enumerate(sents) if w in s)} only.",
           f"The only code appearing in exactly those coded sentences is '{key}'."],
          "Match each word to the code with the same pattern of appearance", "Codes common to two sentences belong to words common to both.", kind="conceptual")
        made[tier] += 1
        if tier == "officer" and made["officer"] < 10:
            # second question on same data: an undeterminable word
            a = r.choice(amb)
            poss = sorted({c for c in allc if sc[c] == sw[a]})
            keyt = "Cannot be determined"
            cands2 = [(c, "one of the possible codes, not certain") for c in poss] + [(c, "code of another word") for c in allc if c not in poss]
            q(B, M_MSG, "L3", "officer", head + f"\n\nWhat is the code for '{a}'?", keyt, cands2,
              [f"'{a}' appears in the same sentences as another word, so its code could be {' or '.join(poss)}.", "Hence it cannot be determined."],
              "Words with identical appearance patterns cannot be separated", "Do not guess between two codes with the same pattern.", kind="conceptual")
            made["officer"] += 1


def add_all(B):
    conditional(B); shifting(B); symbol(B); numcode(B); wordform(B); message(B)
