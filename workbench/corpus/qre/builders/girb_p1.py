"""GIR-B part 1: Series (5 microtopics) + Analogy/Classification (3 microtopics)."""
from girb_common import *

M_NS = "reas-number-series-6232574a"
M_WN = "reas-wrong-number-series-31e436e6"
M_AS = "reas-alphabet-series-b3b70d39"
M_AN = "reas-alphanumeric-and-mixed-series-74351adc"
M_PC = "reas-letter-and-digit-pair-counting-8acc9fe0"
M_NLA = "reas-number-and-letter-analogy-2d75e3a9"
M_ODD = "reas-odd-one-out-from-a-list-f44030fa"
M_WA = "reas-word-and-meaning-analogy-101b7b75"


def gen(first, step, n):
    """step(i, prev) -> next, i = 1-based index of the step."""
    t = [first]
    for i in range(1, n):
        t.append(step(i, t[-1]))
    return t


def number_series(B):
    items = [
        # tier, level, first, step, n_shown, rule, errs(fn of terms, key), trap
        ("foundation", "L1", 3, lambda i, p: 2 * p + 1, 6, "Each term = previous × 2 + 1",
         lambda t, k: [(2 * t[-1], "doubled without adding 1"), (t[-1] + (t[-1] - t[-2]), "repeated the last difference"),
                       (2 * t[-1] + 3, "added 3 instead of 1")], "Differences 4, 8, 16, 32 also double — both views give the same next term."),
        ("foundation", "L1", 5, lambda i, p: p + i * i, 6, "Differences are 1², 2², 3², 4², 5²",
         lambda t, k: [(t[-1] + 16, "repeated the last difference 4²"), (t[-1] + 20, "took differences as multiples of 4"),
                       (t[-1] + 36, "jumped to 6²")], "Look at the differences before guessing a multiplier."),
        ("foundation", "L1", 2, lambda i, p: (i + 1) * (i + 2), 5, "Term n = n × (n + 1)",
         lambda t, k: [(40, "added 10 again"), (36, "took 6² instead of 6 × 7"), (44, "added 14")],
         "Differences 4, 6, 8, 10 rise by 2; next difference is 12."),
        ("foundation", "L2", 4, lambda i, p: [2, 3, 5, 7, 11, 13, 17][i] ** 2, 5, "Squares of consecutive primes 2, 3, 5, 7, 11",
         lambda t, k: [(144, "took 12², a non-prime"), (196, "took 14²"), (225, "took 15²")], "The bases are primes, so 12 and 14 are skipped."),
        ("foundation", "L2", 1, lambda i, p: p * (i + 1), 5, "Multiply by 2, 3, 4, 5, …",
         lambda t, k: [(t[-1] * 5, "repeated ×5"), (t[-1] * 2, "doubled"), (t[-1] * 7, "multiplied by 7")],
         "Multipliers rise by 1 each step (factorials)."),
        ("officer", "L3", 7, lambda i, p: p * i + i, 5, "×1+1, ×2+2, ×3+3, ×4+4, ×5+5",
         lambda t, k: [(t[-1] * 5, "multiplied by 5 but forgot +5"), (t[-1] * 6 + 5, "used ×6"), (t[-1] * 5 + 4, "added 4 instead of 5")],
         "Both the multiplier and the addend rise together."),
        ("officer", "L2", 11, lambda i, p: p + 2 ** i, 5, "Differences double: 2, 4, 8, 16, 32",
         lambda t, k: [(t[-1] + 16, "repeated last difference"), (2 * t[-1], "doubled the term"), (t[-1] + 34, "differences taken as +2 series")],
         "It is the difference that doubles, not the term."),
        ("officer", "L2", 120, lambda i, p: p - (23 - 2 * i), 5, "Differences −21, −19, −17, −15, −13 (also n² − 1 for n = 11 … 6)",
         lambda t, k: [(33, "subtracted 15 again"), (36, "took 6² without −1"), (37, "subtracted 11")],
         "Descending squares minus 1: 121−1, 100−1, 81−1 …"),
        ("officer", "L2", 6, lambda i, p: p + 5 * i, 5, "Differences 5, 10, 15, 20, 25",
         lambda t, k: [(t[-1] + 20, "repeated last difference"), (t[-1] + 30, "skipped a multiple of 5"), (t[-1] + 24, "added 24")],
         "Differences are multiples of 5 in order."),
        ("officer", "L3", 0, lambda i, p: (i + 1) ** 3 - (i + 1), 5, "Term n = n³ − n",
         lambda t, k: [(216, "took 6³ without subtracting 6"), (180, "added 60 again"), (200, "added 80")],
         "0, 6, 24, 60, 120 are 1³−1, 2³−2, 3³−3 …"),
        ("officer", "L3", 5, lambda i, p: p + 4 * i, 5, "Differences 4, 8, 12, 16, 20",
         lambda t, k: [(t[-1] + 16, "repeated last difference"), (t[-1] + 24, "skipped 20"), (t[-1] + 36, "used squares")],
         "Differences rise by a constant 4."),
        ("officer", "L3", 17, lambda i, p: [17, 19, 23, 29, 31, 37, 41, 43][i], 6, "Consecutive prime numbers from 17",
         lambda t, k: [(39, "added 2 assuming odd numbers"), (43, "skipped 41"), (40, "added 3")],
         "39 = 3 × 13 is not prime."),
        ("officer", "L3", 3, lambda i, p: p * (1 + 0.5 * i), 5, "Multiply by 1.5, 2, 2.5, 3, 3.5",
         lambda t, k: [(t[-1] * 4, "multiplied by 4"), (t[-1] * 3, "repeated ×3"), (t[-1] * 3.5 + 0.5, "rounding slip")],
         "Multipliers step up by 0.5."),
    ]
    for tier, lvl, first, step, n, rule, errs, trap in items:
        t = gen(first, step, n + 1)
        shown, key = t[:n], t[n]
        stem = "What comes next in the series?\n\n" + ", ".join(fmt(x) for x in shown) + ", ?"
        q(B, M_NS, lvl, tier, stem, key, numd(key, errs(shown, key)),
          [f"Rule: {rule}.", "Terms: " + ", ".join(fmt(x) for x in shown) + f" → next = {fmt(key)}."], rule, trap)
    # interleaved series
    a = [4, 7, 10, 13]; b = [20, 17, 14, 11]
    s = [x for pr in zip(a, b) for x in pr]
    shown, key = s[:7], s[7]
    assert key == 11
    q(B, M_NS, "L3", "officer", "What comes next in the series?\n\n" + ", ".join(map(str, shown)) + ", ?", key,
      numd(key, [(16, "continued odd-position series"), (12, "subtracted 2"), (10, "subtracted 4")]),
      ["Odd positions: 4, 7, 10, 13 (+3).", "Even positions: 20, 17, 14, ? (−3) → 11."],
      "Two interleaved series", "The next term belongs to the even-position series.")
    # missing middle term n²(n+1)
    t = [n * n * (n + 1) for n in range(1, 7)]
    assert t == [2, 12, 36, 80, 150, 252]
    q(B, M_NS, "L3", "officer", "Find the missing term.\n\n2, 12, 36, 80, ?, 252", 150,
      numd(150, [(144, "took 12²"), (160, "took differences as +10, +24, +44 … +80"), (125, "took 5³")]),
      ["Term n = n² × (n + 1): 1×2, 4×3, 9×4, 16×5.", "5th term = 25 × 6 = 150; check 36 × 7 = 252."],
      "n²(n+1)", "Always verify the candidate against the term after the gap.")


def wrong_series(B):
    items = [
        ("foundation", "L1", gen(3, lambda i, p: 2 * p - 1, 6), 4, 34, "×2 − 1"),
        ("foundation", "L1", [n * n for n in range(1, 8)], 4, 24, "consecutive squares"),
        ("foundation", "L1", gen(7, lambda i, p: 2 * p, 5), 2, 30, "×2"),
        ("foundation", "L2", gen(10, lambda i, p: p + 5 * i, 6), 3, 45, "differences 5, 10, 15, 20, 25"),
        ("foundation", "L2", gen(4, lambda i, p: p + i + 1, 6), 3, 14, "differences 2, 3, 4, 5, 6"),
        ("officer", "L3", gen(2, lambda i, p: p * i + 1, 6), 4, 91, "×1+1, ×2+1, ×3+1, ×4+1, ×5+1"),
        ("officer", "L3", gen(6, lambda i, p: p + i ** 3, 6), 3, 43, "differences 1³, 2³, 3³, 4³, 5³"),
        ("officer", "L3", gen(1, lambda i, p: p + i * i, 7), 4, 32, "differences 1², 2², 3², 4², 5², 6²"),
        ("officer", "L2", gen(5, lambda i, p: 2 * p + 1, 6), 3, 49, "×2 + 1"),
        ("officer", "L3", [120 // n for n in (1, 2, 3, 4, 5, 6)], 3, 32, "120 ÷ 1, ÷ 2, ÷ 3, ÷ 4, ÷ 5, ÷ 6"),
        ("officer", "L2", [n * n - 1 for n in range(2, 9)], 4, 36, "n² − 1 for n = 2 … 8"),
        ("officer", "L3", gen(4, lambda i, p: p * i + i, 6), 4, 162, "×1+1, ×2+2, ×3+3, ×4+4, ×5+5"),
        ("officer", "L3", [n * n + 1 for n in range(1, 8)], 4, 28, "n² + 1"),
        ("officer", "L3", [1, 10, 3, 20, 5, 30, 7], 3, 25, "odd places 1, 3, 5, 7; even places 10, 20, 30"),
        ("officer", "L4", [1, 3, 4, 7, 11, 18, 29], 4, 12, "each term = sum of the previous two"),
    ]
    for tier, lvl, s, wi, wv, rule in items:
        assert s[wi] != wv
        shown = list(s); shown[wi] = wv
        # other option terms: pick three correct terms (not first two, prefer late)
        others = [i for i in range(len(s)) if i != wi and i >= 1][-3:]
        if len(others) < 3:
            others = [i for i in range(len(s)) if i != wi][:3]
        stem = "Find the wrong term in the series.\n\n" + ", ".join(map(str, shown))
        cands = [(shown[i], "fits the rule") for i in others]
        q(B, M_WN, lvl if lvl != "L4" else "L3", tier, stem, wv, cands,
          [f"Rule: {rule}.", "Correct series: " + ", ".join(map(str, s)) + ".",
           f"Term {wi+1} should be {s[wi]}, not {wv}."], rule,
          "Check every term against the rule; a wrong term also breaks the next step, so locate it from both sides.")


def alpha_series(B):
    def tri(key, d, e1, e2, e3):
        return [(d[0], e1), (d[1], e2), (d[2], e3)]
    items = []
    # F1 +3
    s = [L(3 + 3 * i) for i in range(6)]
    items.append(("foundation", "L1", s[:5], s[5], [(L(P(s[4]) + 2), "added 2"), (L(P(s[4]) + 4), "added 4"), (L(P(s[4]) + 1), "added 1")], "+3 each step"))
    s = gen(26, lambda i, p: p - (i + 1), 6)
    items.append(("foundation", "L2", [L(x) for x in s[:5]], L(s[5]), [(L(s[5] + 1), "subtracted 5 again"), (L(s[5] - 1), "subtracted 7"), (L(s[5] + 2), "subtracted 4")], "−2, −3, −4, −5, −6"))
    s = [L(1 + i) + L(26 - i) for i in range(5)]
    items.append(("foundation", "L1", s[:4], s[4], [("EW", "second letter not moved"), ("FV", "first letter +2"), ("EU", "second letter −2")], "first +1, second −1"))
    s = gen(2, lambda i, p: p + i + 1, 6)
    items.append(("foundation", "L2", [L(x) for x in s[:5]], L(s[5]), [(L(s[5] - 1), "added 5 again"), (L(s[5] + 1), "added 7"), (L(s[5] - 2), "added 4")], "+2, +3, +4, +5, +6"))
    s = ["".join(L(1 + 6 * g + 2 * k) for k in range(3)) for g in range(4)]
    items.append(("foundation", "L2", s[:3], s[3], [("STU", "consecutive letters"), ("RTV", "started one letter early"), ("SUV", "last gap +1")], "alternate letters; each group starts 6 after the last"))
    # officer
    s = [L(4 + 2 * g) + L(11 - g) + L(13 + 2 * g) for g in range(4)]
    assert s[:3] == ["DKM", "FJO", "HIQ"]
    items.append(("officer", "L3", s[:3], s[3], [("JGS", "second letter −2"), ("KHS", "first letter +3"), ("JHT", "third letter +3")], "1st +2, 2nd −1, 3rd +2"))
    s = gen(1, lambda i, p: p + i + 1, 6)
    items.append(("officer", "L2", [L(x) for x in s[:5]], L(s[5]), [(L(s[5] - 1), "added 5 again"), (L(s[5] + 1), "added 7"), (L(s[5] - 2), "added 4")], "+2, +3, +4, +5, +6"))
    s = [L(11 + i) + L(16 - i) for i in range(4)]
    assert s[:3] == ["KP", "LO", "MN"]
    items.append(("officer", "L2", s[:3], s[3], [("NO", "second letter moved forward"), ("OM", "first letter +2"), ("ML", "moved both backwards")], "first +1, second −1 (they cross over)"))
    s = gen(25, lambda i, p: p - 2 * i, 5)
    items.append(("officer", "L3", [L(x) for x in s[:4]], L(s[4]), [(L(s[4] + 1), "subtracted 7"), (L(s[4] - 1), "subtracted 9"), (L(s[4] + 2), "subtracted 6 again")], "−2, −4, −6, −8"))
    def grp(g):
        a = 1 + 3 * g; b = 25 - 2 * g
        return L(a) + L(b) + L(a + 1) + L(b + 1) + L(a + 2)
    s = [grp(g) for g in range(4)]
    assert s[:3] == ["AYBZC", "DWEXF", "GUHVI"]
    items.append(("officer", "L3", s[:3], s[3], [("JTKSL", "inner pair reversed"), ("JRKSL", "inner pair started one early"), ("KSLTM", "outer letters started one late")], "outer letters run on in threes; inner pair steps back by 2"))
    s = gen(2, lambda i, p: p + 2 * i + 1, 6)  # 2,5,10,17,26,37 -> B,E,J,Q,Z,K
    assert [L(x) for x in s] == list("BEJQZK")
    items.append(("officer", "L4", [L(x) for x in s[:5]], L(s[5]), [("J", "added 10"), ("L", "added 12"), ("M", "added 13")], "+3, +5, +7, +9, +11 (count past Z back to A)"))
    s = [L(26 - g) + L(1 + g * (g + 3) // 2) for g in range(5)]
    assert s[:4] == ["ZA", "YC", "XF", "WJ"], s
    items.append(("officer", "L3", s[:4], s[4], [("VN", "second letter +4"), ("UO", "first letter −2"), ("VP", "second letter +6")], "1st −1; 2nd +2, +3, +4, +5"))
    s = [L(n * n) for n in range(1, 6)]
    items.append(("officer", "L2", s[:4], s[4], [("X", "took 24"), ("Z", "took 26"), ("W", "took 23")], "positions 1, 4, 9, 16, 25"))
    def mk():
        out = [(13, 14)]
        for k in range(2, 6):
            f = out[-1][1]; out.append((f, f + k))
        return ["".join(L(x) for x in pr) for pr in out]
    s = mk()
    assert s[:4] == ["MN", "NP", "PS", "SW"], s
    items.append(("officer", "L4", s[:4], s[4], [("WA", "added 4 again"), ("XB", "first letter +1"), ("WC", "added 6")], "2nd letter becomes next 1st letter; gap +1, +2, +3, +4, +5"))
    s = [L(3 + 2 * g) + L(27 - (3 + 2 * g)) for g in range(5)]
    assert s[:4] == ["CX", "EV", "GT", "IR"]
    items.append(("officer", "L3", s[:4], s[4], [("KQ", "second letter −1 only"), ("JP", "first letter +1"), ("LP", "first letter +3")], "1st +2; 2nd is its opposite letter (sum of positions 27)"))
    for tier, lvl, shown, key, cands, rule in items:
        lv = "L3" if lvl == "L4" else lvl
        q(B, M_AS, lv, tier, "What comes next in the series?\n\n" + ", ".join(shown) + ", ?", key, cands,
          [f"Pattern: {rule}.", "Series: " + ", ".join(shown) + f" → {key}."], "A=1 … Z=26 (opposite letter: sum 27)",
          "Write letter positions under each term before looking for the gap pattern.", kind="conceptual")


def alnum_series(B):
    items = []
    s = [L(2 * i + 1) + str(2 * i + 1) for i in range(5)]
    items.append(("foundation", "L1", s[:4], s[4], [("H8", "moved by 1"), ("I8", "number +1 only"), ("J9", "letter +3")], "letter +2, number +2"))
    s = [str(2 * (i + 1)) + L(26 - i) for i in range(5)]
    items.append(("foundation", "L1", s[:4], s[4], [("10U", "letter −2"), ("9V", "number +1"), ("12V", "number +4")], "number +2, letter −1"))
    s = [L(i + 1) + str((i + 1) ** 2) for i in range(5)]
    items.append(("foundation", "L1", s[:4], s[4], [("E20", "number +4 each time"), ("F25", "letter skipped"), ("E24", "square minus 1")], "letter +1; number = square of letter position"))
    s = [L(26 - 2 * i) + str(26 - 2 * i) for i in range(4)]
    items.append(("foundation", "L2", s[:3], s[3], [("U21", "moved by 1"), ("T21", "number −1 only"), ("S19", "moved by 3")], "letter −2 and number = its position"))
    s = [str(n * (n + 1) // 2) + L(n * (n + 1) // 2) for n in range(1, 6)]
    items.append(("foundation", "L2", s[:4], s[4], [("15N", "letter one short"), ("14O", "number +4"), ("16P", "added 6")], "number +2, +3, +4, +5; letter at that position"))
    s = [L(3 * i) + str(3 * i) + L(3 * i + 2) for i in range(1, 5)]
    items.append(("officer", "L2", s[:3], s[3], [("L12M", "third letter +1 only"), ("M12N", "first letter +4"), ("L11N", "number +2")], "letters +3; number = first letter's position; third letter = first +2"))
    s = [str(n) + L(n) + str(n ** 3) for n in range(2, 6)]
    items.append(("officer", "L3", s[:3], s[3], [("5E25", "squared instead of cubed"), ("5F125", "letter +2"), ("6E125", "number +2")], "n, n-th letter, n³"))
    ps = gen(1, lambda i, p: p + i + 1, 5)
    s = [L(x) + str(27 - x) for x in ps]
    items.append(("officer", "L3", s[:4], s[4], [("O11", "number −6"), ("P12", "letter +6"), ("N12", "letter +4")], "letter +2, +3, +4, +5; number = 27 − position (opposite letter)"))
    s = [L(2 + 3 * i) + str(3 + 4 * i) for i in range(5)]
    items.append(("officer", "L2", s[:4], s[4], [("N18", "number +3"), ("M19", "letter +2"), ("O19", "letter +4")], "letter +3, number +4"))
    s = [L(25 - 3 * i) + str((i + 1) * (i + 2)) for i in range(5)]
    items.append(("officer", "L3", s[:4], s[4], [("M28", "number +8 again"), ("N30", "letter −2"), ("L30", "letter −4")], "letter −3; number n(n+1)"))
    s = [str(2 * i + 3) + L(4 * i + 4) for i in range(5)]
    items.append(("officer", "L2", s[:4], s[4], [("11S", "letter +3"), ("10T", "number +1"), ("11U", "letter +5")], "number +2, letter +4"))
    s = [L(3 + 4 * i) + L(5 + 4 * i) + str(8 + 8 * i) for i in range(4)]
    assert s[:3] == ["CE8", "GI16", "KM24"]
    items.append(("officer", "L3", s[:3], s[3], [("OQ30", "number +6"), ("NP32", "letters +3"), ("OR32", "second letter +5")], "letters +4 each; number = sum of the two positions"))
    s = [L(26 - 2 * i) + str(2 * i + 1) + L(2 * i + 1) for i in range(5)]
    items.append(("officer", "L2", s[:4], s[4], [("R9H", "third letter +1"), ("S9I", "first letter −1"), ("R8I", "number +1")], "first −2; number = position of third letter (+2)"))
    ps = gen(1, lambda i, p: p + i + 1, 5)
    s = [str(5 * 2 ** i) + L(ps[i]) for i in range(5)]
    items.append(("officer", "L3", s[:4], s[4], [("80N", "letter +4"), ("60O", "number +20"), ("80P", "letter +6")], "number ×2; letter +2, +3, +4, +5"))
    nums = [1, 1, 2, 6, 24, 120]
    s = [str(nums[i]) + L(1 + 3 * i) for i in range(6)]
    items.append(("officer", "L3", s[:5], s[5], [("96P", "multiplied by 4"), ("120O", "letter +2"), ("120Q", "letter +4")], "number ×1, ×2, ×3, ×4, ×5; letter +3"))
    for tier, lvl, shown, key, cands, rule in items:
        q(B, M_AN, lvl, tier, "What comes next in the series?\n\n" + ", ".join(shown) + ", ?", key, cands,
          [f"Pattern: {rule}.", "Series: " + ", ".join(shown) + f" → {key}."], "Split each term into its letter part and number part",
          "Track the letter part and the number part separately; they usually follow different rules.", kind="conceptual")


# ---------------- pair counting & arrangement ----------------
def pairs_both(w):
    return sum(1 for i in range(len(w)) for j in range(i + 1, len(w)) if abs(P(w[j]) - P(w[i])) == j - i)


def pairs_fwd(w):
    return sum(1 for i in range(len(w)) for j in range(i + 1, len(w)) if P(w[j]) - P(w[i]) == j - i)


def dpairs_both(d):
    return sum(1 for i in range(len(d)) for j in range(i + 1, len(d)) if abs(int(d[j]) - int(d[i])) == j - i)


def dpairs_fwd(d):
    return sum(1 for i in range(len(d)) for j in range(i + 1, len(d)) if int(d[j]) - int(d[i]) == j - i)


def pair_list(w, dig=False):
    v = (lambda c: int(c)) if dig else P
    return [w[i] + w[j] for i in range(len(w)) for j in range(i + 1, len(w)) if abs(v(w[j]) - v(w[i])) == j - i]


VOW = set("AEIOU")
SYM = set("@#$%&*©★")


def kind_of(c):
    if c.isdigit():
        return "D"
    if c in SYM:
        return "S"
    return "V" if c in VOW else "C"


def count_pat(arr, pat):
    """pat: tuple of 3 predicates (prev, mid, next) — count positions i where all hold."""
    return sum(1 for i in range(1, len(arr) - 1) if pat[0](arr[i - 1]) and pat[1](arr[i]) and pat[2](arr[i + 1]))


isD = lambda c: kind_of(c) == "D"
isS = lambda c: kind_of(c) == "S"
isC = lambda c: kind_of(c) == "C"
isV = lambda c: kind_of(c) == "V"
isL = lambda c: kind_of(c) in "CV"
anyc = lambda c: True


def pair_counting(B):
    WREF = "Count a pair once whether the letters run forward or backward."
    words = [("foundation", "L2", "MONITOR"), ("foundation", "L2", "BRIGHTEN"), ("officer", "L3", "PHILOSOPHY")]
    for tier, lvl, w in words:
        k, f = pairs_both(w), pairs_fwd(w)
        stem = (f"How many pairs of letters are there in the word '{w}' each of which has as many letters between them in the word "
                f"as in the English alphabet? ({WREF})")
        q(B, M_PC, lvl, tier, stem, k, numd(k, [(f, "counted only forward (alphabetical-order) pairs"), (k + f, "counted backward pairs twice")]),
          ["Compare every pair (i, j): letters between them in the word = j − i − 1; in the alphabet = |difference in positions| − 1.",
           f"Qualifying pairs: {', '.join(pair_list(w))}.", f"Total = {k}."],
          "|pos(x) − pos(y)| = gap in word", "Adjacent letters of the alphabet sitting next to each other (like ON) also count.")
    for tier, lvl, d in [("foundation", "L2", "5728391"), ("officer", "L3", "86421357")]:
        k, f = dpairs_both(d), dpairs_fwd(d)
        stem = (f"How many pairs of digits are there in the number {d} each of which has as many digits between them in the number "
                f"as when the digits are arranged in ascending order (0–9 number line)? (Count forward and backward pairs once each.)")
        q(B, M_PC, lvl, tier, stem, k, numd(k, [(f, "counted only ascending pairs"), (k + f, "double-counted")]),
          ["For digits a (position i) and b (position j): need |a − b| = j − i.", f"Qualifying pairs: {', '.join(pair_list(d, True))}.", f"Total = {k}."],
          "|a − b| = gap in number", "Descending adjacent digits (e.g. 8 then 7 next to each other) qualify too.")
    # arrangement based
    rng = random.Random("GRB-arr")
    pool = list("BCDFGHJKLMNPRSTWXZ") + list("AEIOU") + list("23456789") + list("@#$%&*©★")

    def make_arr(seed, n):
        r = random.Random(seed)
        while True:
            a = [r.choice(pool) for _ in range(n)]
            if sum(isD(c) for c in a) >= 5 and sum(isS(c) for c in a) >= 5 and sum(isV(c) for c in a) >= 3:
                return a

    def arr_qs(arr):
        out = []
        n = len(arr)
        c1 = count_pat(arr, (isD, isS, isC))
        c1b = count_pat(arr, (anyc, isS, isC))
        c1c = count_pat(arr, (isD, isS, anyc))
        out.append(("How many symbols are there in the arrangement each of which is immediately preceded by a digit and immediately followed by a consonant?",
                    c1, [(c1b, "ignored the 'preceded by a digit' condition"), (c1c, "ignored the 'followed by a consonant' condition")],
                    ["Scan each symbol and check its left and right neighbours.", f"Count = {c1}."]))
        c2 = count_pat(arr, (isL, isD, isL))
        c2b = count_pat(arr, (isC, isD, isC))
        out.append(("How many digits are there in the arrangement each of which is immediately preceded by a letter and immediately followed by a letter? (Vowels are letters too.)",
                    c2, [(c2b, "counted only consonant neighbours"), (sum(isD(c) for c in arr), "counted all digits")],
                    ["Check both neighbours of every digit.", f"Count = {c2}."]))
        # element k-th left of m-th from right
        m, k = 9, 5
        idx = n - m - k  # 0-based from left: m-th from right is index n-m; k to the left -> n-m-k
        key = arr[idx]
        alt1 = arr[n - m + k]; alt2 = arr[idx + 1]; alt3 = arr[m - 1 - k] if m - 1 - k >= 0 else arr[0]
        out.append((f"Which element is {k}th to the left of the {m}th element from the right end?", key,
                    [(alt1, "moved right instead of left"), (alt2, "counted the start element as one step"), (alt3, "counted from the left end")],
                    [f"{m}th from right = position {n-m+1} from left ({arr[n-m]}).", f"{k} to its left = position {idx+1} from left = {key}."]))
        # digits removed
        nod = [c for c in arr if not isD(c)]
        p = 10
        key2 = nod[p - 1]
        out.append((f"If all the digits are removed from the arrangement, which element will be {p}th from the left end?", key2,
                    [(arr[p - 1], "did not remove the digits"), (nod[p], "off by one after removal"), (nod[p - 2], "off by one after removal (other side)")],
                    ["Remaining sequence: " + " ".join(nod) + ".", f"{p}th from left = {key2}."]))
        cv = count_pat(arr, (isV, isC, anyc))
        out.append(("How many consonants are there in the arrangement each of which is immediately preceded by a vowel?", cv,
                    [(count_pat(arr, (anyc, isC, isV)), "counted consonants followed by a vowel"), (sum(isV(c) for c in arr), "counted all vowels")],
                    ["Check the left neighbour of each consonant.", f"Count = {cv}."]))
        return out

    # foundation standalone (1 remaining: 5 foundation = 3 so far? words 2 + digits 1 = 3) -> add 2 standalone arrangement Qs
    arrF = make_arr("GRB-F", 20)
    qs = arr_qs(arrF)
    head = "Study the arrangement:\n\n" + " ".join(arrF) + "\n\n"
    for (st, key, cands, steps) in [qs[0], qs[2]]:
        q(B, M_PC, "L2", "foundation", head + st, key, numd(key, cands) if isinstance(key, int) else cands + [(c, "neighbouring element") for c in arrF],
          steps, "Neighbour checks / position arithmetic", "Read left and right carefully; the end element has only one neighbour.")
    # officer case sets (2 sets × 4 Q)
    for si, seed in enumerate(["GRB-O1", "GRB-O2"]):
        arr = make_arr(seed, 26)
        qs = arr_qs(arr)
        head = "Study the following arrangement carefully and answer the questions.\n\n" + " ".join(arr)
        pick = [0, 1, 2, 3] if si == 0 else [4, 1, 2, 3]
        for pi in pick:
            st, key, cands, steps = qs[pi]
            cc = numd(key, cands) if isinstance(key, int) else cands + [(c, "neighbouring element") for c in arr]
            q(B, M_PC, "L4", "officer", head + "\n\n" + st, key, cc, steps, "Neighbour checks / position arithmetic",
              "Mark positions from both ends before moving left/right.", kind="case", group=f"GRB-PC-SET{si+1}")


# ---------------- analogies ----------------
def shift(w, ks):
    ks = ks if isinstance(ks, list) else [ks] * len(w)
    return "".join(L(P(c) + k) for c, k in zip(w, ks))


def opp(w):
    return "".join(L(27 - P(c)) for c in w)


def nl_analogy(B):
    # letter analogies
    def la(tier, lvl, a, b, c, f, cands, rule):
        assert f(a) == b
        key = f(c)
        q(B, M_NLA, lvl, tier, f"{a} : {b} :: {c} : ?", key, cands,
          [f"Rule: {rule}.", f"{a} → {b}; apply to {c} → {key}."], rule, "Check the rule on every letter, not just the first.", kind="conceptual")
    la("foundation", "L1", "BDF", "CEG", "MOQ", lambda w: shift(w, 1), [("NPQ", "last letter unchanged"), ("LNP", "shifted backward"), ("NQR", "second letter +2")], "each letter +1")
    la("foundation", "L1", "ACE", "ZXV", "BDF", opp, [("YWV", "last letter +1"), ("XWU", "first letter −1"), ("YVU", "second letter −1")], "each letter replaced by its opposite (A↔Z)")
    la("foundation", "L1", "PQR", "RQP", "LMN", lambda w: w[::-1], [("MNL", "rotated"), ("NLM", "rotated the other way"), ("LNM", "swapped last two")], "letters written in reverse order")
    la("officer", "L3", "CFI", "DIN", "EHK", lambda w: shift(w, [1, 3, 5]), [("FJP", "second letter +2"), ("FKO", "third letter +4"), ("GKP", "first letter +2")], "+1, +3, +5 on the three letters")
    la("officer", "L2", "DGJ", "WTQ", "FIL", opp, [("UQO", "second letter off by one"), ("VRO", "first letter off by one"), ("URP", "third letter off by one")], "opposite letters (sum of positions 27)")
    la("officer", "L2", "RATE", "TCVG", "BIRD", lambda w: shift(w, 2), [("DKSF", "third letter +1"), ("CJSE", "shifted by 1"), ("DKTE", "last letter +1")], "each letter +2")
    # number analogies with two example pairs (kills add-a-constant ambiguity)
    def na(tier, lvl, ex, x, f, cands, rule, alt_check=True):
        for a, b in ex:
            assert f(a) == b
        if len(ex) >= 2 and alt_check:
            (a1, b1), (a2, b2) = ex[:2]
            assert b1 - a1 != b2 - a2 and b1 * a2 != b2 * a1, "constant rule also fits"
        key = f(x)
        stem = "The numbers in each pair are related by the same rule. Find the missing number.\n\n" + " :: ".join(f"{a} : {b}" for a, b in ex) + f" :: {x} : ?"
        q(B, M_NLA, lvl, tier, stem, key, numd(key, cands), [f"Rule: {rule}.", "Check: " + "; ".join(f"{a} → {b}" for a, b in ex) + f"; so {x} → {key}."],
          rule, "Test the rule on every example pair before applying it.")
    na("foundation", "L1", [(5, 26), (7, 50)], 12, lambda n: n * n + 1, [(144, "squared only"), (143, "n² − 1"), (156, "n(n+1)")], "n² + 1")
    na("foundation", "L2", [(3, 28), (4, 65)], 5, lambda n: n ** 3 + 1, [(125, "cubed only"), (124, "n³ − 1"), (130, "n³ + n")], "n³ + 1")
    na("officer", "L2", [(11, 132), (9, 90)], 13, lambda n: n * (n + 1), [(169, "squared"), (156, "n(n−1)"), (195, "n(n+2)")], "n × (n + 1)")
    na("officer", "L3", [(16, 26), (36, 50)], 64, lambda n: (int(round(n ** 0.5)) + 1) ** 2 + 1, [(81, "next square, forgot +1"), (74, "added 10"), (78, "added 14")], "a² → (a + 1)² + 1")
    na("officer", "L3", [(3, 80), (4, 255)], 5, lambda n: n ** 4 - 1, [(625, "forgot −1"), (620, "n⁴ − 5"), (575, "n⁴ − 50")], "n⁴ − 1")
    # choose the pair
    f = lambda n: n ** 3 + n
    key = (7, f(7))
    wr = [((5, 126), "n³ + 1"), ((4, 60), "n³ − n"), ((8, 576), "n²(n + 1)")]
    for (a, b), e in wr:
        assert f(a) != b
    q(B, M_NLA, "L3", "officer", "Select the pair in which the numbers are related in the same way as 6 : 222 and 2 : 10.",
      f"{key[0]} : {key[1]}", [(f"{a} : {b}", f"follows {e}") for (a, b), e in wr],
      ["6³ + 6 = 222 and 2³ + 2 = 10 → rule n³ + n.", "7³ + 7 = 350 ✓; 5³ + 5 = 130 ≠ 126; 4³ + 4 = 68 ≠ 60; 8³ + 8 = 520 ≠ 576."],
      "n³ + n", "Distractors follow near-miss rules (n³ + 1, n³ − n).")
    # word-to-number (letter positions)
    s = lambda w: sum(P(c) for c in w)
    assert s("DOG") == 26
    q(B, M_NLA, "L2", "officer", "If DOG : 26 and FAN : 21, then CAT : ?", s("CAT"),
      numd(s("CAT"), [(3 * 1 * 20, "multiplied positions"), (s("CAT") + 3, "counted reverse positions for one letter")]),
      ["DOG: 4 + 15 + 7 = 26; FAN: 6 + 1 + 14 = 21 → sum of positions.", f"CAT: 3 + 1 + 20 = {s('CAT')}."],
      "Sum of alphabet positions", "Confirm with both examples; a product rule fails for FAN.")
    dig = lambda w: "".join(str(P(c)) for c in w)
    assert dig("HIDE") == "8945"
    q(B, M_NLA, "L2", "officer", "If HIDE : 8945, then SEED : ?", dig("SEED"),
      [("19545", "last two letters swapped"), ("18554", "S taken as 18"), ("19455", "middle letters misread")],
      ["Each letter is replaced by its alphabet position: H8 I9 D4 E5.", "S19 E5 E5 D4 → 19554."],
      "Letter → alphabet position", "S is the 19th letter.", kind="conceptual")
    # reverse relation pair
    cands = [("MEAT : TEAM", "swaps only first and last letters"), ("SLOW : WOSL", "partial reversal"), ("NAME : EMNA", "partial reversal")]
    for x, _ in cands:
        a, b = x.split(" : ")
        assert a[::-1] != b
    assert "PART"[::-1] == "TRAP"
    q(B, M_NLA, "L2", "officer", "Select the letter-cluster pair related in the same way as FLOW : WOLF.", "PART : TRAP", cands,
      ["WOLF is FLOW written backwards.", "PART reversed = TRAP ✓; MEAT reversed = TAEM, SLOW reversed = WOLS, NAME reversed = EMAN."],
      "Full reversal", "MEAT : TEAM is a meaningful word pair but not a reversal.", kind="conceptual")


def odd_one(B):
    def oo(tier, lvl, opts, prop, key, rule, kind="conceptual"):
        good = [o for o in opts if prop(o)]
        bad = [o for o in opts if not prop(o)]
        assert bad == [key] and len(good) == 3, (opts, bad)
        q(B, M_ODD, lvl, tier, "Find the odd one out.", key, [(g, "shares the common property") for g in good],
          [f"Common property: {rule}.", f"{key} does not have it."], rule, "Test each option against the property; do not stop at the first surprise.", kind=kind)
    sq = lambda x: int(round(int(x) ** 0.5)) ** 2 == int(x)
    cube = lambda x: round(int(x) ** (1 / 3)) ** 3 == int(x)
    prime = lambda x: int(x) > 1 and all(int(x) % d for d in range(2, int(int(x) ** 0.5) + 1))
    gaps = lambda w, g: all(P(w[i + 1]) - P(w[i]) == g for i in range(len(w) - 1))
    oo("foundation", "L1", ["121", "169", "225", "290"], sq, "290", "perfect squares")
    oo("foundation", "L1", ["17", "23", "29", "33"], prime, "33", "prime numbers")
    oo("foundation", "L1", ["ACE", "GIK", "MOQ", "RTU"], lambda w: gaps(w, 2), "RTU", "letters at gaps of +2")
    oo("foundation", "L1", ["28", "35", "49", "58"], lambda x: int(x) % 7 == 0, "58", "multiples of 7")
    oo("foundation", "L2", ["AZ", "BY", "CX", "DV"], lambda w: P(w[0]) + P(w[1]) == 27, "DV", "opposite-letter pairs (positions sum to 27)")
    oo("officer", "L2", ["120", "210", "336", "500"], lambda x: any(n ** 3 - n == int(x) for n in range(2, 12)), "500", "numbers of the form n³ − n (5³−5, 6³−6, 7³−7)")
    oo("officer", "L2", ["1331", "1728", "2197", "2750"], cube, "2750", "perfect cubes (11³, 12³, 13³)")
    oo("officer", "L3", ["243", "315", "162", "426"], lambda x: sum(map(int, x)) == 9, "426", "digit sum equals 9")
    oo("officer", "L3", ["5 : 24", "7 : 48", "9 : 80", "11 : 110"], lambda s: int(s.split(" : ")[0]) ** 2 - 1 == int(s.split(" : ")[1]), "11 : 110", "second = first² − 1")
    oo("officer", "L2", ["DGJ", "KNQ", "PSV", "UXZ"], lambda w: gaps(w, 3), "UXZ", "letters at gaps of +3")
    oo("officer", "L3", ["CEGI", "LNPR", "SUWY", "HJMO"], lambda w: gaps(w, 2), "HJMO", "letters at gaps of +2")
    oo("officer", "L3", ["97", "101", "103", "91"], prime, "91", "prime numbers (91 = 7 × 13)")
    oo("officer", "L2", ["63", "80", "99", "125"], lambda x: sq(int(x) + 1), "125", "one less than a perfect square")
    oo("officer", "L3", ["2 : 9", "3 : 28", "4 : 65", "5 : 124"], lambda s: int(s.split(" : ")[0]) ** 3 + 1 == int(s.split(" : ")[1]), "5 : 124", "second = first³ + 1")
    oo("officer", "L3", ["BY", "DW", "FU", "HT"], lambda w: P(w[0]) + P(w[1]) == 27, "HT", "opposite-letter pairs (positions sum to 27)")


def word_analogy(B):
    items = [
        ("foundation", "L1", "Pen : Write :: Knife : ?", "Cut", [("Sharp", "quality, not function"), ("Steel", "material"), ("Kitchen", "place of use")], "tool : function"),
        ("foundation", "L1", "Bird : Nest :: Bee : ?", "Hive", [("Honey", "product, not dwelling"), ("Flower", "food source"), ("Wax", "material")], "creature : dwelling"),
        ("foundation", "L1", "Doctor : Patient :: Lawyer : ?", "Client", [("Court", "workplace"), ("Judge", "colleague in the process"), ("Case", "the matter, not the person served")], "professional : person served"),
        ("foundation", "L2", "Cow : Calf :: Horse : ?", "Foal", [("Pony", "a small breed of horse"), ("Mare", "adult female horse"), ("Stallion", "adult male horse")], "adult : young one"),
        ("foundation", "L1", "Eye : See :: Ear : ?", "Hear", [("Sound", "stimulus, not function"), ("Noise", "stimulus"), ("Head", "location")], "organ : function"),
        ("officer", "L2", "Ornithology : Birds :: Entomology : ?", "Insects", [("Words", "confuses with etymology"), ("Fossils", "palaeontology"), ("Fungi", "mycology")], "science : object of study"),
        ("officer", "L2", "Numismatics : Coins :: Philately : ?", "Stamps", [("Maps", "cartography"), ("Books", "bibliophily"), ("Paintings", "art history")], "hobby/study : object collected"),
        ("officer", "L3", "Loquacious : Talkative :: Taciturn : ?", "Reserved", [("Garrulous", "antonym of taciturn"), ("Angry", "unrelated mood"), ("Humble", "unrelated trait")], "synonyms"),
        ("officer", "L2", "Myopia : Eye :: Anaemia : ?", "Blood", [("Heart", "organ confused"), ("Bone", "unrelated tissue"), ("Skin", "symptom site (pallor), not the affected system")], "disorder : part affected"),
        ("officer", "L2", "Thermometer : Temperature :: Hygrometer : ?", "Humidity", [("Pressure", "barometer"), ("Altitude", "altimeter"), ("Rainfall", "rain gauge")], "instrument : quantity measured"),
        ("officer", "L2", "Seismograph : Earthquake :: Anemometer : ?", "Wind speed", [("Air pressure", "barometer"), ("Rainfall", "rain gauge"), ("Humidity", "hygrometer")], "instrument : what it records"),
        ("officer", "L2", "Pupa : Butterfly :: Tadpole : ?", "Frog", [("Fish", "look-alike, different animal"), ("Lizard", "reptile"), ("Snake", "reptile")], "immature stage : adult"),
        ("officer", "L3", "Benevolent : Kind :: Parsimonious : ?", "Stingy", [("Generous", "antonym"), ("Wealthy", "unrelated attribute"), ("Lazy", "unrelated trait")], "synonyms"),
        ("officer", "L3", "Sculptor : Chisel :: Surgeon : ?", "Scalpel", [("Hospital", "workplace"), ("Patient", "person served"), ("Operation", "activity, not instrument")], "worker : cutting instrument"),
        ("officer", "L3", "Choose the pair related in the same way as Chapter : Book.", "Stanza : Poem",
         [("Author : Novel", "creator : creation"), ("Page : Ink", "object : material"), ("Library : Book", "place : item kept")], "part : whole"),
    ]
    for tier, lvl, stem, key, cands, rel in items:
        q(B, M_WA, lvl, tier, stem, key, cands, [f"Relationship: {rel}.", f"Answer: {key}."], rel,
          "Name the relationship in words first, then test each option against it.", kind="conceptual")


def add_all(B):
    number_series(B); wrong_series(B); alpha_series(B); alnum_series(B); pair_counting(B)
    nl_analogy(B); odd_one(B); word_analogy(B)
