"""GIR-B part 6: Input-Output (arithmetic machines, sign interchange, shifting machines, step counting).
Every machine is simulated step by step; every sign item is evaluated exactly with Fractions under BODMAS."""
from girb_common import *
from fractions import Fraction

M_AOM = "reas-arithmetic-operation-machine-258cf421"
M_SGN = "reas-mathematical-operations-sign-interchange-3d6288ea"
M_SHF = "reas-shifting-and-rearrangement-machine-9b0cb8fb"
M_STP = "reas-step-count-and-intermediate-step-questions-790ddbf0"

ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
SCONV = ("Convention: a step moves exactly the elements named by the rule; a step in which nothing would change is not "
         "counted, and the machine stops as soon as the arrangement is complete.")
WORDS = ["amber", "bold", "cider", "drum", "eagle", "frost", "grape", "house", "inch", "jolly", "kite", "lemon", "mango",
         "nest", "olive", "plum", "quilt", "river", "stone", "tiger", "urban", "vivid", "wheat", "yarn", "zebra"]


def S(state):
    return " ".join(str(x) for x in state)


# ---------------------------------------------------------------- arithmetic helpers
def dsum(n):
    return sum(int(c) for c in str(abs(n)))


def pipeline(inp, ops):
    """ops: list of (description, fn(list)->list). Returns list of states [input, step1, ...]."""
    st = [list(inp)]
    for _, f in ops:
        st.append(f(st[-1]))
    return st


OPS = {
    "oddeven": ("each odd number is increased by 5 and each even number is divided by 2",
                lambda L: [x + 5 if x % 2 else x // 2 for x in L]),
    "dsum": ("each number is replaced by the sum of its digits", lambda L: [dsum(x) for x in L]),
    "posmul": ("each number is multiplied by its position from the left (1st, 2nd, ...)",
               lambda L: [x * (i + 1) for i, x in enumerate(L)]),
    "desc": ("the numbers are arranged in descending order", lambda L: sorted(L, reverse=True)),
    "asc": ("the numbers are arranged in ascending order", lambda L: sorted(L)),
    "pairsum": ("each pair of adjacent numbers is replaced by their sum (so the list becomes one shorter)",
                lambda L: [L[i] + L[i + 1] for i in range(len(L) - 1)]),
    "sq_minus": ("each number is replaced by (number − 3)", lambda L: [x - 3 for x in L]),
    "rev": ("the order of the numbers is reversed", lambda L: L[::-1]),
    "digswap": ("the digits of each two-digit number are interchanged (a single-digit number stays as it is)",
                lambda L: [int(str(x)[::-1]) if x >= 10 else x for x in L]),
    "plus_idx": ("each number is increased by its position from the right (rightmost = 1)",
                 lambda L: [x + (len(L) - i) for i, x in enumerate(L)]),
}


def ops_text(keys):
    return " ".join(f"Step {ROMAN[i+1]}: {OPS[k][0]}." for i, k in enumerate(keys))


# ---------------------------------------------------------------- row-rule grid
def row_rule(a, b):
    if a % 2 == 0 and b % 2 == 1:
        return a + b
    if a % 2 == 1 and b % 2 == 1:
        return a * b
    if a % 2 == 1 and b % 2 == 0:
        return abs(a - b)
    return (a + b) // 2


ROW_RULES = ("Numbers in a row are processed from left to right: the first two numbers give a result, which then works with "
             "the third number, and so on. Rules: (i) an even number followed by an odd number — add them; (ii) an odd number "
             "followed by an odd number — multiply them; (iii) an odd number followed by an even number — take the difference "
             "(larger minus smaller); (iv) an even number followed by an even number — take half of their sum.")


def row_eval(row):
    r = row[0]
    trail = [r]
    for x in row[1:]:
        r = row_rule(r, x)
        trail.append(r)
    return r, trail


def row_wrong(row):
    """plausible error: always add."""
    return sum(row)


# ---------------------------------------------------------------- sign expressions
PREC = {"+": 1, "−": 1, "×": 2, "÷": 2}


def ev(tokens):
    """tokens: [n, op, n, op, n...] with ops in + − × ÷ ; exact BODMAS. Returns Fraction or None (div by 0)."""
    nums = [Fraction(tokens[0])]
    ops = []
    for i in range(1, len(tokens), 2):
        op, n = tokens[i], Fraction(tokens[i + 1])
        if op in "×÷":
            if op == "÷" and n == 0:
                return None
            nums[-1] = nums[-1] * n if op == "×" else nums[-1] / n
        else:
            ops.append(op); nums.append(n)
    r = nums[0]
    for op, n in zip(ops, nums[1:]):
        r = r + n if op == "+" else r - n
    return r


def ev_ltr(tokens):
    r = Fraction(tokens[0])
    for i in range(1, len(tokens), 2):
        op, n = tokens[i], Fraction(tokens[i + 1])
        if op == "÷" and n == 0:
            return None
        r = {"+": r + n, "−": r - n, "×": r * n, "÷": r / n if n else None}[op]
    return r


def tstr(tokens):
    return " ".join(str(t) for t in tokens)


def subst(tokens, m):
    return [m.get(t, t) if isinstance(t, str) else t for t in tokens]


def swap_ops(tokens, a, b):
    return [(b if t == a else a if t == b else t) if isinstance(t, str) else t for t in tokens]


def is_int(f):
    return f is not None and f.denominator == 1


# ---------------------------------------------------------------- shifting machines
def insertion_machine(inp, order, side="left"):
    """Each step places the next element of `order` at the next slot of a block growing from `side`.
    No-change steps are skipped (not counted). Returns list of states [input, step1, ...]."""
    st = list(inp)
    states = [list(st)]
    final_n = len(order)
    for k, el in enumerate(order):
        new = list(st)
        new.remove(el)
        if side == "left":
            new.insert(k, el)
        else:
            new.insert(len(new) - k, el)
        if new != st:
            states.append(new)
            st = new
    return states


def wordnum_machine(inp, wkey_rev=False, nkey_rev=False, words_left=True):
    """Each step: next word (alphabetical, or reverse) goes to the left block, and the next number
    (ascending, or descending) goes to the right block — or the sides swapped when words_left=False.
    Steps with no change are skipped. Returns states."""
    words = sorted([x for x in inp if isinstance(x, str)], reverse=wkey_rev)
    nums = sorted([x for x in inp if isinstance(x, int)], reverse=nkey_rev)
    st = list(inp)
    states = [list(st)]
    for k in range(max(len(words), len(nums))):
        new = list(st)
        n = len(new)
        if k < len(words):
            w = words[k]; new.remove(w)
            if words_left:
                new.insert(k, w)
            else:
                new.insert(len(new) - k, w)
        if k < len(nums):
            m = nums[k]; new.remove(m)
            if words_left:
                new.insert(len(new) - k, m)
            else:
                new.insert(k, m)
        assert len(new) == n
        if new != st:
            states.append(new)
            st = new
    return states


def swap_machine(inp, order):
    """Each step: the next element of `order` swaps places with the element at the next slot from the left."""
    st = list(inp)
    states = [list(st)]
    for k, el in enumerate(order):
        new = list(st)
        i = new.index(el)
        new[i], new[k] = new[k], new[i]
        if new != st:
            states.append(new)
            st = new
    return states


def full_steps(states):
    """True if every step changed and the last state is the first 'complete' one."""
    return all(states[i] != states[i + 1] for i in range(len(states) - 1))


def arr_cands(states, k, extra):
    """distractors for 'what is Step k': neighbouring steps + extra alternative-rule states."""
    c = []
    if k - 1 >= 0:
        c.append((S(states[k - 1]), "stopped one step early (this is the previous step)"))
    if k + 1 < len(states):
        c.append((S(states[k + 1]), "went one step too far (this is the next step)"))
    c += extra
    return c


def rng_inputs(seed, nw, nn, lo=11, hi=98):
    rng = random.Random(seed)
    words = rng.sample(WORDS, nw)
    nums = rng.sample(range(lo, hi), nn)
    items = words + nums
    rng.shuffle(items)
    return items


# ====================================================================== ARITHMETIC OPERATION MACHINE
def arithmetic_machine(B):
    F = "Apply the stated operation to every number, one step at a time"
    T = "Apply each step to the output of the previous step, not to the original input."
    # foundation: 5 single pipelines
    cfgs = [
        (101, ["oddeven", "dsum"], 5, "final", "L1"),
        (102, ["oddeven", "asc", "posmul"], 5, "sum", "L2"),
        (103, ["dsum", "desc", "pairsum"], 5, "final", "L2"),
        (104, ["digswap", "sq_minus"], 4, "sum", "L1"),
        (105, ["rev", "plus_idx", "dsum"], 5, "max", "L2"),
    ]
    for seed, keys, n, ask, lvl in cfgs:
        rng = random.Random(seed)
        inp = rng.sample(range(12, 96), n)
        st = pipeline(inp, [OPS[k] for k in keys])
        last = len(keys)
        stem = f"A number machine works as follows. {ops_text(keys)}\nInput: {S(inp)}\n"
        if ask == "final":
            key = S(st[last])
            stem += f"What is Step {ROMAN[last]} (the final output)?"
            # alternative: skip first step
            alt = pipeline(inp, [OPS[k] for k in keys[1:]])[-1]
            cands = [(S(st[last - 1]), "stopped one step early"), (S(alt), f"skipped Step I"),
                     (S(st[last][::-1]), "wrote the output in reverse order")]
            if keys[-1] == "pairsum":
                cands.append((S(pipeline(inp, [OPS["dsum"], OPS["asc"], OPS["pairsum"]])[-1]), "arranged in ascending instead of descending order"))
            q(B, M_AOM, lvl, "foundation", stem, key, cands,
              [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(1, last + 1)], F, T, kind="conceptual")
        elif ask == "sum":
            key = sum(st[last])
            stem += f"What is the sum of the numbers in Step {ROMAN[last]}?"
            alt = pipeline(inp, [OPS[k] for k in keys[1:]])[-1]
            cands = [(sum(st[last - 1]), "summed the previous step"), (sum(alt), "skipped Step I"), (sum(inp), "summed the input")]
            q(B, M_AOM, lvl, "foundation", stem, key, numd(key, cands),
              [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(1, last + 1)] + [f"Sum = {key}."], F, T)
        else:
            key = max(st[last])
            stem += f"What is the largest number in Step {ROMAN[last]}?"
            cands = [(max(st[last - 1]), "read the previous step"), (min(st[last]), "picked the smallest"), (max(inp), "read the input")]
            q(B, M_AOM, lvl, "foundation", stem, key, numd(key, cands),
              [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(1, last + 1)] + [f"Largest = {key}."], F, T)

    # officer set 1: row-rule grid (4 questions, L4)
    rng = random.Random(110)
    while True:
        rows = [[rng.randint(3, 20) for _ in range(3)] for _ in range(4)]
        res = [row_eval(r) for r in rows]
        vals = [r[0] for r in res]
        rules_used = {(a % 2, b % 2) for row, (_, tr) in zip(rows, res) for a, b in zip(tr[:-1], row[1:])}
        if len(set(vals)) == 4 and all(v < 400 for v in vals) and len(rules_used) == 4:
            break
    grid = "\n".join(f"Row {i+1}: {S(r)}" for i, r in enumerate(rows))
    stim = ROW_RULES + "\n\n" + grid
    pre = stim + "\n\n"

    def trail_txt(i):
        r, t = res[i]
        return f"Row {i+1}: " + " → ".join(str(x) for x in t)
    # Q1 result of row 2
    key = vals[1]
    q(B, M_AOM, "L4", "officer", "What is the result of Row 2?", key,
      numd(key, [(row_wrong(rows[1]), "added all numbers irrespective of the rules"), (ev_ltr([rows[1][0], "×", rows[1][1], "+", rows[1][2]]), "applied rules to the wrong pair"), (vals[0], "result of Row 1")]),
      [trail_txt(1)], "Apply the parity rule pair by pair, left to right", "Recheck the parity of the running result before each step.",
      kind="case", group="GRB-IO-AOM-SET1", pre=pre)
    key = vals[0] + vals[2]
    q(B, M_AOM, "L4", "officer", "What is the sum of the results of Row 1 and Row 3?", key,
      numd(key, [(vals[0] + vals[3], "used Row 4 instead of Row 3"), (row_wrong(rows[0]) + row_wrong(rows[2]), "added all numbers"), (vals[1] + vals[2], "used Row 2 instead of Row 1")]),
      [trail_txt(0), trail_txt(2), f"Sum = {vals[0]} + {vals[2]} = {key}."], "Row results", "Keep track of which row is asked.",
      kind="case", group="GRB-IO-AOM-SET1", pre=pre)
    key = vals[3] - vals[1] if vals[3] > vals[1] else vals[1] - vals[3]
    q(B, M_AOM, "L4", "officer", "What is the difference between the results of Row 4 and Row 2 (larger minus smaller)?", key,
      numd(key, [(abs(row_wrong(rows[3]) - row_wrong(rows[1])), "added all numbers in each row"), (vals[3] + vals[1], "added instead of subtracting"), (abs(vals[3] - vals[0]), "used Row 1 instead of Row 2")]),
      [trail_txt(3), trail_txt(1), f"Difference = {key}."], "Row results", "Parity of the intermediate result decides the next rule.",
      kind="case", group="GRB-IO-AOM-SET1", pre=pre)
    hi = max(range(4), key=lambda i: vals[i]); lo_ = min(range(4), key=lambda i: vals[i])
    names = [f"Row {i+1}" for i in range(4)]
    q(B, M_AOM, "L4", "officer", "Which row gives the largest result?", names[hi],
      [(names[lo_], "picked the smallest result")] + [(names[i], "arithmetic slip in applying the parity rules") for i in range(4) if i != hi],
      [trail_txt(i) for i in range(4)] + [f"Largest = {names[hi]} ({vals[hi]})."], "Row results", "Compare the final results, not the raw numbers.",
      kind="case", group="GRB-IO-AOM-SET1", pre=pre)

    # officer set 2: pipeline machine (3 questions, L4)
    keys = ["oddeven", "desc", "posmul", "dsum"]
    rng = random.Random(111)
    inp = rng.sample(range(13, 97), 6)
    st = pipeline(inp, [OPS[k] for k in keys])
    stim = f"A number machine processes a row of numbers. {ops_text(keys)}\nInput: {S(inp)}"
    pre = stim + "\n\n"
    stp = [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(1, 5)]
    key = st[3][2]
    q(B, M_AOM, "L4", "officer", "Which number is third from the left in Step III?", key,
      numd(key, [(st[3][3], "counted fourth from the left"), (st[2][2], "read Step II"), (st[3][-3], "counted third from the right")]),
      stp[:3], F, T, kind="case", group="GRB-IO-AOM-SET2", pre=pre)
    key = sum(st[4])
    alt = pipeline(inp, [OPS[k] for k in ["oddeven", "asc", "posmul", "dsum"]])[-1]
    q(B, M_AOM, "L4", "officer", "What is the sum of all numbers in Step IV?", key,
      numd(key, [(sum(alt), "arranged ascending in Step II"), (sum(dsum(x) for x in st[2]), "skipped Step III"), (sum(st[3]), "summed Step III")]),
      stp + [f"Sum = {key}."], F, T, kind="case", group="GRB-IO-AOM-SET2", pre=pre)
    cnt = sum(1 for x in st[4] if x % 2 == 0)
    q(B, M_AOM, "L4", "officer", "How many even numbers are there in Step IV?", cnt,
      numd(cnt, [(sum(1 for x in st[3] if x % 2 == 0), "counted in Step III"), (6 - cnt, "counted odd numbers"), (sum(1 for x in alt if x % 2 == 0), "arranged ascending in Step II")]),
      stp + [f"Even numbers in Step IV: {cnt}."], F, T, kind="case", group="GRB-IO-AOM-SET2", pre=pre)

    # officer standalone 3 (L3)
    for seed, keys, ask in [(120, ["digswap", "oddeven", "asc", "pairsum"], "second"),
                            (121, ["plus_idx", "oddeven", "dsum", "posmul"], "sum"),
                            (122, ["oddeven", "digswap", "desc", "pairsum"], "diff")]:
        rng = random.Random(seed)
        inp = rng.sample(range(12, 98), 5)
        st = pipeline(inp, [OPS[k] for k in keys])
        stem = f"A number machine works as follows. {ops_text(keys)}\nInput: {S(inp)}\n"
        stp = [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(1, 5)]
        wrong_first = pipeline(inp, [OPS[k] for k in keys[1:]])[-1] if keys[-1] != "pairsum" else pipeline(inp, [OPS[k] for k in keys[1:]])[-1]
        if ask == "second":
            key = st[4][1]
            cands = [(st[4][-2], "counted second from the right"), (st[3][1], "read Step III"), (wrong_first[1] if len(wrong_first) > 1 else key + 3, "skipped Step I")]
            stem += "Which number is second from the left in Step IV?"
        elif ask == "sum":
            key = sum(st[4])
            cands = [(sum(st[3]), "summed Step III"), (sum(wrong_first), "skipped Step I"), (sum(x * (i + 1) for i, x in enumerate(st[2])), "skipped Step III")]
            stem += "What is the sum of the numbers in Step IV?"
        else:
            key = max(st[4]) - min(st[4])
            cands = [(max(st[3]) - min(st[3]), "used Step III"), (max(wrong_first) - min(wrong_first), "skipped Step I"), (max(st[4]) + min(st[4]), "added instead of subtracting")]
            stem += "What is the difference between the largest and the smallest number in Step IV?"
        q(B, M_AOM, "L3", "officer", stem, key, numd(key, cands), stp + [f"Answer = {key}."], F, T)


# ====================================================================== SIGN INTERCHANGE
def gen_expr(rng, nops, lo=2, hi=30):
    ops = [rng.choice("+−×÷") for _ in range(nops)]
    toks = [rng.randint(lo, hi)]
    for o in ops:
        toks += [o, rng.randint(lo, hi)]
    return toks


def sign_interchange(B):
    F = "Substitute the symbols first, then apply BODMAS (÷ and × before + and −, left to right)"
    T = "Do not evaluate strictly left to right; BODMAS applies after substitution."
    ALLO = ["+", "−", "×", "÷"]
    # foundation 5: direct substitution
    rng = random.Random(201)
    made = 0
    perms = [p for p in itertools.permutations(ALLO) if all(a != b for a, b in zip(ALLO, p))]
    while made < 5:
        m = dict(zip(ALLO, rng.choice(perms)))
        toks = gen_expr(rng, 3 if made < 3 else 4, 2, 40)
        t2 = subst(toks, m)
        v = ev(t2); vl = ev_ltr(t2); vo = ev(toks)
        if not (is_int(v) and 0 <= v <= 200 and is_int(vl) and vl != v and (vo is None or vo != v)):
            continue
        if len(set(t for t in toks if isinstance(t, str))) < 3:
            continue
        mtxt = ", ".join(f"'{a}' means '{m[a]}'" for a in ALLO)
        cands = [(int(vl), "evaluated left to right, ignoring BODMAS")]
        if is_int(vo):
            cands.append((int(vo), "did not substitute the symbols"))
        inv = {v2: k for k, v2 in m.items()}
        vi = ev(subst(toks, inv))
        if is_int(vi):
            cands.append((int(vi), "applied the substitution in reverse"))
        q(B, M_SGN, "L1" if made < 3 else "L2", "foundation", f"If {mtxt}, then what is the value of {tstr(toks)} ?",
          int(v), numd(int(v), cands), [f"After substitution: {tstr(t2)}", f"BODMAS gives {int(v)}."], F, T)
        made += 1

    # officer: which interchange makes the equation correct (4, L3)
    pairs = list(itertools.combinations(ALLO, 2))
    made = 0
    rng = random.Random(202)
    while made < 4:
        toks = gen_expr(rng, 4, 2, 24)
        used = set(t for t in toks if isinstance(t, str))
        if len(used) < 4:
            continue
        good = []
        for a, b in pairs:
            v = ev(swap_ops(toks, a, b))
            good.append(((a, b), v))
        # choose target pair
        cand_pairs = [p for p, v in good if is_int(v) and 0 < v < 300]
        if not cand_pairs:
            continue
        tp = rng.choice(cand_pairs)
        target = dict(good)[tp]
        if ev(toks) == target:
            continue
        others = [p for p, v in good if p != tp and v != target]
        if len(others) < 3:
            continue
        # also the other swaps must not accidentally make it true (checked by v != target)
        wr = rng.sample(others, 3)
        txt = lambda p: f"'{p[0]}' and '{p[1]}'"
        stem = (f"Which of the following interchanges of signs would make the given equation correct?\n"
                f"{tstr(toks)} = {int(target)}")
        steps = [f"Interchanging {txt(tp)}: {tstr(swap_ops(toks, *tp))} = {int(target)} ✓"]
        for p in wr:
            vv = dict(good)[p]
            steps.append(f"Interchanging {txt(p)} gives {('undefined' if vv is None else fmt(float(vv)) if vv.denominator != 1 else int(vv))} ≠ {int(target)}")
        assert sum(1 for p in [tp] + wr if dict(good)[p] == target) == 1
        q(B, M_SGN, "L3", "officer", stem, txt(tp), [(txt(p), "this interchange does not balance the equation") for p in wr],
          steps, "Try each option; evaluate with BODMAS", "Interchange every occurrence of both signs.", kind="conceptual")
        made += 1

    # officer: which equation is correct under a substitution (3, L3)
    made = 0
    rng = random.Random(203)
    while made < 3:
        m = dict(zip(ALLO, rng.choice(perms)))
        eqs = []
        tries = 0
        while len(eqs) < 4 and tries < 2000:
            tries += 1
            toks = gen_expr(rng, 3, 2, 20)
            v = ev(subst(toks, m))
            if not is_int(v) or v < 0 or v > 150:
                continue
            eqs.append((toks, int(v)))
        if len(eqs) < 4:
            continue
        # one correct, three with a wrong RHS (a named error value)
        correct_eq = eqs[0]
        wrong_eqs = []
        for toks, v in eqs[1:]:
            vl = ev_ltr(subst(toks, m))
            vo = ev(toks)
            alt = int(vl) if is_int(vl) and vl != v else (int(vo) if is_int(vo) and vo != v else v + 2)
            if alt < 0:
                alt = v + 3
            wrong_eqs.append((toks, alt, v))
        mtxt = ", ".join(f"'{a}' means '{m[a]}'" for a in ALLO)
        assert ev(subst(correct_eq[0], m)) == correct_eq[1]
        assert all(ev(subst(t, m)) != a for t, a, _ in wrong_eqs)
        stem = f"If {mtxt}, which of the following equations is correct?"
        steps = [f"{tstr(correct_eq[0])} → {tstr(subst(correct_eq[0], m))} = {correct_eq[1]} ✓"] + \
                [f"{tstr(t)} → {tstr(subst(t, m))} = {v}, not {a}" for t, a, v in wrong_eqs]
        q(B, M_SGN, "L3", "officer", stem, f"{tstr(correct_eq[0])} = {correct_eq[1]}",
          [(f"{tstr(t)} = {a}", "true only if evaluated left to right or without substitution") for t, a, v in wrong_eqs],
          steps, F, T, kind="conceptual")
        made += 1

    # officer: letter-coded operators, longer expressions with brackets-free BODMAS (3, L3/L4-lite)
    made = 0
    rng = random.Random(204)
    codes = ["P", "Q", "R", "S"]
    while made < 3:
        m = dict(zip(codes, rng.sample(ALLO, 4)))
        toks = [rng.randint(2, 30)]
        for _ in range(5):
            toks += [rng.choice(codes), rng.randint(2, 30)]
        t2 = subst(toks, m)
        v = ev(t2); vl = ev_ltr(t2)
        if not (is_int(v) and 0 <= v <= 300 and is_int(vl) and vl != v):
            continue
        if len(set(t for t in toks if isinstance(t, str))) < 4:
            continue
        mtxt = ", ".join(f"'{c}' means '{m[c]}'" for c in codes)
        # wrong mapping: swap the meanings of two codes
        m2 = dict(m); m2["P"], m2["Q"] = m["Q"], m["P"]
        v2 = ev(subst(toks, m2))
        cands = [(int(vl), "evaluated left to right")]
        if is_int(v2):
            cands.append((int(v2), "interchanged the meanings of P and Q"))
        q(B, M_SGN, "L3", "officer", f"If {mtxt}, then what is the value of {tstr(toks)} ?", int(v),
          numd(int(v), cands), [f"Decoded: {tstr(t2)}", f"BODMAS gives {int(v)}."], F, T)
        made += 1


# ====================================================================== SHIFTING / REARRANGEMENT MACHINE
def shifting_machine(B):
    F = "Simulate the machine one step at a time"
    T = "Each step builds on the previous step's arrangement, not on the input."
    # foundation 5: numbers only, smallest-to-left insertion
    RULE_F = ("A machine rearranges a line of numbers. In each step, the smallest number not yet arranged moves to the "
              "leftmost position among the unarranged numbers, and the others shift right. ")
    made, seed = 0, 300
    asks = ["step2", "pos3", "step3", "last", "between"]
    while made < 5:
        seed += 1
        rng = random.Random(seed)
        inp = rng.sample(range(11, 99), 6)
        order = sorted(inp)
        st = insertion_machine(inp, order, "left")
        if len(st) != 6 or not full_steps(st):
            continue
        desc_st = insertion_machine(inp, sorted(inp, reverse=True), "left")
        ask = asks[made]
        stem = RULE_F + SCONV + f"\nInput: {S(inp)}\n"
        stp = [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(1, len(st))]
        if ask in ("step2", "step3"):
            k = 2 if ask == "step2" else 3
            stem += f"What is Step {ROMAN[k]}?"
            q(B, M_SHF, "L2", "foundation", stem, S(st[k]), arr_cands(st, k, [(S(desc_st[k]), "moved the largest number instead")]),
              stp[:k], F, T, kind="conceptual")
        elif ask == "pos3":
            el = st[3][4]
            stem += f"In Step III, which number is fifth from the left?"
            q(B, M_SHF, "L1", "foundation", stem, el,
              [(st[3][1], "counted fifth from the right"), (st[2][4], "read Step II"), (inp[4], "read the input")] + [(x, "miscounted position") for x in st[3] if x != el],
              stp[:3], F, T, kind="conceptual")
        elif ask == "last":
            stem += "How many steps are needed to complete the arrangement?"
            key = len(st) - 1
            q(B, M_SHF, "L2", "foundation", stem, key, numd(key, [(len(inp), "counted one step per number"), (key - 1, "missed the last step")]),
              stp, F, T)
        else:
            s4 = st[4]
            a, b = s4[1], s4[3]
            stem += f"In Step IV, which number lies exactly midway between {a} and {b}?"
            key = s4[2]
            q(B, M_SHF, "L2", "foundation", stem, key,
              [(s4[4], "counted one place too far"), (s4[0], "counted from the wrong side")] + [(x, "miscounted position") for x in s4 if x not in (a, b, key)],
              stp[:4], F, T, kind="conceptual")
        made += 1

    # officer case sets: word + number machine (2 sets × 4 = 8, L4)
    RULE_W = ("A word and number arrangement machine rearranges a line of words and two-digit numbers. In each step, the "
              "word that comes next in alphabetical order is placed at the left end, just after the words already arranged "
              "there; and the next number in ascending order is placed at the right end, just before the numbers already "
              "arranged there (so the smallest number finally stands at the extreme right). ")
    RULE_W2 = ("A word and number arrangement machine rearranges a line of words and two-digit numbers. In each step, the "
               "next number in descending order is placed at the left end, just after the numbers already arranged there; "
               "and the next word in reverse alphabetical order (Z to A) is placed at the right end, just before the words "
               "already arranged there. ")
    for si, (rule, kw) in enumerate([(RULE_W, dict()), (RULE_W2, dict(wkey_rev=True, nkey_rev=True, words_left=False))]):
        seed = 330 + si * 50
        while True:
            seed += 1
            inp = rng_inputs(seed, 4, 4)
            st = wordnum_machine(inp, **kw)
            if len(st) == 5 and full_steps(st):
                break
        alt = wordnum_machine(inp, **({"wkey_rev": not kw.get("wkey_rev", False), "nkey_rev": not kw.get("nkey_rev", False), "words_left": kw.get("words_left", True)}))
        grp = f"GRB-IO-SHF-SET{si+1}"
        stim = rule + SCONV + f"\n\nInput: {S(inp)}"
        pre = stim + "\n\n"
        stp = [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(1, len(st))]
        # Q1 step II
        q(B, M_SHF, "L4", "officer", "What is Step II?", S(st[2]),
          arr_cands(st, 2, [(S(alt[2]), "used the opposite sorting order")]), stp[:2], F, T, kind="case", group=grp, pre=pre)
        # Q2 element 3rd from right in step III
        e = st[3][-3]
        q(B, M_SHF, "L4", "officer", "Which element is third from the right end in Step III?", e,
          [(st[3][2], "counted third from the left"), (st[2][-3], "read Step II"), (st[3][-4], "counted fourth from the right")] + [(x, "miscounted") for x in st[3] if x != e],
          stp[:3], F, T, kind="case", group=grp, pre=pre)
        # Q3 which step is the last
        key = f"Step {ROMAN[len(st)-1]}"
        q(B, M_SHF, "L4", "officer", "Which step is the last step of the arrangement?", key,
          [(f"Step {ROMAN[len(st)]}", "added an extra step"), (f"Step {ROMAN[len(st)-2]}", "stopped one step early"), ("Step VIII", "counted one step per element")],
          stp, F, T, kind="case", group=grp, pre=pre)
        # Q4 how many elements between two items in last step
        fin = st[-1]
        a, b = fin[1], fin[5]
        key = 3
        # count elements between a and b in step II
        s2 = st[2]
        k2 = abs(s2.index(a) - s2.index(b)) - 1
        qtxt = f"In Step II, how many elements are there between '{a}' and '{b}'?"
        q(B, M_SHF, "L4", "officer", qtxt, k2,
          numd(k2, [(abs(fin.index(a) - fin.index(b)) - 1, "counted in the final step"), (abs(inp.index(a) - inp.index(b)) - 1, "counted in the input"), (k2 + 2, "included both elements")]),
          stp[:2] + [f"In Step II, '{a}' is at position {s2.index(a)+1} and '{b}' at {s2.index(b)+1}; between = {k2}."], F, T, kind="case", group=grp, pre=pre)

    # officer standalone 2 (L3): swap machine
    RULE_S = ("A machine rearranges a line of numbers. In each step, the largest number not yet arranged interchanges "
              "places with the number standing in the leftmost unarranged position (positions are filled from the left). ")
    seed = 400
    done = 0
    while done < 2:
        seed += 1
        rng = random.Random(seed)
        inp = rng.sample(range(11, 99), 7)
        st = swap_machine(inp, sorted(inp, reverse=True))
        if len(st) < 6 or not full_steps(st):
            continue
        ins = insertion_machine(inp, sorted(inp, reverse=True), "left")
        stem = RULE_S + SCONV + f"\nInput: {S(inp)}\n"
        stp = [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(1, len(st))]
        if done == 0:
            stem += "What is Step III?"
            k = 3
            ext = [(S(ins[k]), "shifted the others right instead of interchanging")] if len(ins) > k else []
            q(B, M_SHF, "L3", "officer", stem, S(st[k]), arr_cands(st, k, ext), stp[:k], F, "Interchange, not shift: only two numbers change places per step.", kind="conceptual")
        else:
            key = len(st) - 1
            stem += "How many steps does the machine take to complete the arrangement?"
            q(B, M_SHF, "L3", "officer", stem, key,
              numd(key, [(len(ins) - 1, "used shifting instead of interchanging"), (len(inp), "counted one step per number"), (len(inp) - 1, "assumed every position needs a step")]),
              stp, F, "A number already in its place needs no step.")
        done += 1


# ====================================================================== STEP COUNT & INTERMEDIATE STEPS
def step_count(B):
    F = "Simulate the machine; skip steps that would change nothing"
    T = "Elements already in their final place do not need a step."
    RULE = ("A machine arranges a line of numbers in ascending order from the left. In each step, the smallest number not yet "
            "arranged moves to the leftmost unarranged position and the others shift right. ")
    # foundation 5: count steps for inputs with some pre-arranged elements
    made, seed = 0, 500
    while made < 5:
        seed += 1
        rng = random.Random(seed)
        n = 6 if made < 3 else 7
        inp = rng.sample(range(11, 99), n)
        st = insertion_machine(inp, sorted(inp), "left")
        steps = len(st) - 1
        if not (2 <= steps <= n - 2):
            continue
        naive = n
        stem = RULE + SCONV + f"\nInput: {S(inp)}\nHow many steps are required to complete the arrangement?"
        q(B, M_STP, "L2" if made < 4 else "L3", "foundation", stem, steps,
          numd(steps, [(naive, "counted one step per number"), (naive - 1, "assumed only the last number needs no step"), (steps + 1, "counted a no-change step")]),
          [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(1, len(st))] + [f"Arrangement complete after {steps} steps."], F, T)
        made += 1

    # officer: 2 case sets of 3 (L4) — given a Step, work forward
    RULE_W = ("A word and number arrangement machine works on a line of words and numbers. In each step, the next word in "
              "alphabetical order is placed at the left end just after the words already arranged, and the next number in "
              "descending order is placed at the right end just before the numbers already arranged there (so the largest "
              "number finally stands at the extreme right). ")
    for si in range(2):
        seed = 550 + si * 40
        while True:
            seed += 1
            inp = rng_inputs(seed, 4 + si, 4 + si, 11, 99)
            st = wordnum_machine(inp, nkey_rev=True)
            if len(st) == 5 + si and full_steps(st):
                break
        grp = f"GRB-IO-STP-SET{si+1}"
        given = 2
        stim = RULE_W + SCONV + f"\n\nStep II of an input is: {S(st[given])}"
        pre = stim + "\n\n"
        last = len(st) - 1
        stp = [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(given + 1, len(st))]
        # Q1 how many more steps
        key = last - given
        q(B, M_STP, "L4", "officer", "How many more steps are needed after Step II to complete the arrangement?", key,
          numd(key, [(last, "counted total steps instead of remaining steps"), (key + 1, "counted Step II again"), (len(st[given]) - 2 * given, "subtracted arranged elements from the total")]),
          stp + [f"Last step = Step {ROMAN[last]}; remaining = {key}."], F, T, kind="case", group=grp, pre=pre)
        # Q2 which is Step IV
        k = 4
        q(B, M_STP, "L4", "officer", f"What is Step {ROMAN[k]}?", S(st[k]),
          arr_cands(st, k, [(S(wordnum_machine(st[given], nkey_rev=False)[-1]), "arranged numbers in ascending order"),
                            (S(wordnum_machine(st[given], wkey_rev=True, nkey_rev=True)[min(2, len(wordnum_machine(st[given], wkey_rev=True, nkey_rev=True)) - 1)]), "arranged words in reverse alphabetical order"),
                            (S(st[given]), "copied the given Step II")]),
          stp[:k - given], F, T, kind="case", group=grp, pre=pre)
        # Q3 in which step does element X first reach its final position?
        fin = st[-1]
        cand_el = [x for x in fin if st[given].index(x) != fin.index(x)]
        x = cand_el[-1]
        reach = next(i for i in range(given, len(st)) if all(st[j].index(x) == fin.index(x) for j in range(i, len(st))))
        key = f"Step {ROMAN[reach]}"
        opts = [f"Step {ROMAN[i]}" for i in range(given + 1, len(st)) if i != reach] + [f"Step {ROMAN[len(st)]}", "Step II"]
        q(B, M_STP, "L4", "officer", f"In which step does '{x}' first reach the position it occupies in the final arrangement (and stay there)?", key,
          [(o, "misread the step in which it settles") for o in opts],
          stp + [f"'{x}' settles at position {fin.index(x)+1} from {key} onwards."], F, "An element can pass through its final position and move again; check it stays.",
          kind="case", group=grp, pre=pre)

    # officer standalone 4 (L3)
    # (a) given Step III of numbers-only machine, what is the last step number
    RULE_D = ("A machine arranges numbers in descending order from the left. In each step, the largest number not yet "
              "arranged moves to the leftmost unarranged position and the others shift right. ")
    done, seed = 0, 600
    while done < 4:
        seed += 1
        rng = random.Random(seed)
        inp = rng.sample(range(11, 99), 8)
        st = insertion_machine(inp, sorted(inp, reverse=True), "left")
        if len(st) < 7 or not full_steps(st):
            continue
        last = len(st) - 1
        if done == 0:
            stem = RULE_D + SCONV + f"\nStep III of an input is: {S(st[3])}\nWhich step is the last step?"
            key = f"Step {ROMAN[last]}"
            q(B, M_STP, "L3", "officer", stem, key,
              [(f"Step {ROMAN[last+1]}", "counted a no-change step"), (f"Step {ROMAN[last-1]}", "stopped one step early"), ("Step VIII", "counted one step per number")] +
              [(f"Step {ROMAN[last-2]}", "stopped two steps early")],
              [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(4, len(st))], F, T, kind="conceptual")
        elif done == 1:
            stem = RULE_D + SCONV + f"\nStep II of an input is: {S(st[2])}\nWhat is Step V?"
            q(B, M_STP, "L3", "officer", stem, S(st[5]),
              arr_cands(st, 5, [(S(insertion_machine(st[2], sorted(inp), "left")[min(3, len(insertion_machine(st[2], sorted(inp), 'left')) - 1)]), "arranged in ascending order")]),
              [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(3, 6)], F, T, kind="conceptual")
        elif done == 2:
            stem = RULE_D + SCONV + f"\nInput: {S(inp)}\nIn which step does the arrangement '{S(st[4])}' appear?"
            key = "Step IV"
            q(B, M_STP, "L3", "officer", stem, key, [("Step III", "one step early"), ("Step V", "one step late"), ("Step VI", "counted a no-change step"), ("Step II", "miscounted")],
              [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(1, 5)], F, T, kind="conceptual")
        else:
            stem = RULE_D + SCONV + f"\nInput: {S(inp)}\nWhat is the sum of the numbers in the 2nd and 7th positions from the left in Step III?"
            key = st[3][1] + st[3][6]
            q(B, M_STP, "L3", "officer", stem, key,
              numd(key, [(st[2][1] + st[2][6], "read Step II"), (st[4][1] + st[4][6], "read Step IV"), (st[3][2] + st[3][5], "counted from the wrong end")]),
              [f"Step {ROMAN[i]}: {S(st[i])}" for i in range(1, 4)] + [f"{st[3][1]} + {st[3][6]} = {key}."], F, T)
        done += 1


def add_all(B):
    arithmetic_machine(B); sign_interchange(B); shifting_machine(B); step_count(B)
