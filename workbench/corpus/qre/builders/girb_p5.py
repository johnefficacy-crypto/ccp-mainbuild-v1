"""GIR-B part 5: Direction & distance (coordinates) and Order & ranking (brute-force solvers)."""
from girb_common import *

M_DREL = "reas-direction-of-one-point-relative-to-another-783ac0e9"
M_PATH = "reas-path-tracing-and-final-position-11904573"
M_PYT = "reas-shortest-distance-by-pythagoras-3a8e0d2c"
M_TWO = "reas-two-person-path-problems-c50164bd"
M_AGE = "reas-age-and-height-ordering-9e5c27d9"
M_ATTR = "reas-comparison-and-ordering-by-attribute-d24d90e3"
M_POS = "reas-position-from-either-end-8ab86a4c"
M_TOT = "reas-total-count-deduction-from-positions-8130a2b3"

DIRS = ["North", "East", "South", "West"]
VEC = {"North": (0, 1), "East": (1, 0), "South": (0, -1), "West": (-1, 0)}
DCONV = "(North-East, South-West etc. denote the quadrant between the two main directions.)"


def dir_name(dx, dy):
    if dx == 0 and dy == 0:
        return "Same point"
    ns = "North" if dy > 0 else ("South" if dy < 0 else "")
    ew = "East" if dx > 0 else ("West" if dx < 0 else "")
    return f"{ns}-{ew}" if ns and ew else (ns or ew)


ALL8 = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"]


def dir_cands(key):
    i = ALL8.index(key)
    return [(ALL8[(i + 4) % 8], "opposite direction (reversed the reference point)"), (ALL8[(i + 2) % 8], "turned the wrong way once"),
            (ALL8[(i + 6) % 8], "turned the wrong way once (other side)"), (ALL8[(i + 1) % 8], "neighbouring direction"), (ALL8[(i - 1) % 8], "neighbouring direction")]


def walk(start_face, legs):
    """legs: list of (turn, dist) with turn in {None,'left','right','back'} applied before walking."""
    f = DIRS.index(start_face)
    x = y = 0
    pts = [(0, 0)]
    for t, d in legs:
        if t == "right":
            f = (f + 1) % 4
        elif t == "left":
            f = (f - 1) % 4
        elif t == "back":
            f = (f + 2) % 4
        dx, dy = VEC[DIRS[f]]
        x += dx * d; y += dy * d
        pts.append((x, y))
    return x, y, DIRS[f], pts


def describe(name, start_face, legs, unit="m"):
    parts = []
    for i, (t, d) in enumerate(legs):
        if i == 0:
            parts.append(f"{name} starts from point S and walks {d} {unit} towards the {start_face}")
        else:
            tt = {"left": "turns left", "right": "turns right", "back": "turns back"}[t]
            parts.append(f"then {tt} and walks {d} {unit}")
    return ", ".join(parts) + "."


def dist_txt(d2, unit="m"):
    r = math.isqrt(d2)
    return f"{r} {unit}" if r * r == d2 else f"√{d2} {unit}"


def random_legs(rng, n, lo=2, hi=12):
    legs = [(None, rng.randint(lo, hi))]
    for _ in range(n - 1):
        legs.append((rng.choice(["left", "right"]), rng.randint(lo, hi)))
    return legs


def pick_walk(seed, n, cond, lo=2, hi=12):
    rng = random.Random(seed)
    for _ in range(50000):
        face = rng.choice(DIRS)
        legs = random_legs(rng, n, lo, hi)
        x, y, f, pts = walk(face, legs)
        if len(set(pts)) == len(pts) and cond(x, y, f, legs):
            return face, legs, x, y, f
    raise RuntimeError(seed)


NAMES = ["Ravi", "Meena", "Arjun", "Sana", "Kiran", "Farhan", "Neha", "Vikram", "Asha", "Deepak", "Lata", "Manoj", "Pooja", "Imran", "Divya", "Rohit"]


def direction_relative(B):
    # foundation: two/three-point descriptions
    F = [(("P", "Q", 0, 6), ("R", "Q", 8, 0), "P", "R"),
         (("A", "B", -5, 0), ("C", "B", 0, -7), "C", "A"),
         (("M", "N", 0, -4), ("O", "N", 0, 9), "M", "O"),
         (("X", "Y", 3, 0), ("Z", "Y", 0, 3), "Z", "X"),
         (("K", "L", -6, 0), ("J", "L", 0, 5), "L", "J")]
    for (a, ra, ax, ay), (b, rb, bx, by), p, r in F:
        pos = {ra: (0, 0), a: (ax, ay)}
        pos[b] = (pos[rb][0] + bx, pos[rb][1] + by)
        def rel(u, v, dx, dy):
            d = dir_name(dx, dy); dd = abs(dx) + abs(dy)
            return f"{u} is {dd} m {d.lower()} of {v}"
        stem = f"{rel(a, ra, ax, ay)}. {rel(b, rb, bx, by)}. In which direction is {p} with respect to {r}? {DCONV}"
        key = dir_name(pos[p][0] - pos[r][0], pos[p][1] - pos[r][1])
        q(B, M_DREL, "L1", "foundation", stem, key, dir_cands(key),
          [f"Place {ra} at (0, 0): {a} = {pos[a]}, {b} = {pos[b]}.", f"{p} − {r} = ({pos[p][0]-pos[r][0]}, {pos[p][1]-pos[r][1]}) → {key}."],
          "Coordinates: x = east, y = north", "Read 'P with respect to R' as: stand at R, look towards P.", kind="conceptual")
    # officer standalone: walks, shadows, rotations
    for i in range(3):
        face, legs, x, y, f = pick_walk(f"GRB-drel-{i}", 4 + (i % 2), lambda x, y, f, l: x != 0 and y != 0)
        nm = NAMES[i]
        key = dir_name(-x, -y)
        stem = describe(nm, face, legs) + f" In which direction is the starting point S from {nm}'s final position? {DCONV}"
        q(B, M_DREL, "L3", "officer", stem, key, dir_cands(key),
          [f"Final position relative to S: ({x}, {y}).", f"S relative to final = ({-x}, {-y}) → {key}."],
          "Track (x, y) after each leg", "The question asks for S from the end point, not the end point from S.", kind="conceptual")
    # shadow problems (morning: sun in east → shadow west; evening: shadow east)
    sh = [("morning", "right", "A", "B", "facing each other"), ("evening", "left", "P", "Q", "standing back to back"),
          ("morning", "left", "Kiran", None, None)]
    for tod, side, a, b, pose in sh:
        shadow = "West" if tod == "morning" else "East"
        # a's facing such that shadow is on a's side
        for fa in DIRS:
            fi = DIRS.index(fa)
            sd = DIRS[(fi + 1) % 4] if side == "right" else DIRS[(fi - 1) % 4]
            if sd == shadow:
                break
        if b:
            fb = DIRS[(fi + 2) % 4] if pose == "facing each other" else fa
            if pose == "back to back":
                fb = DIRS[(fi + 2) % 4]
            fb = DIRS[(fi + 2) % 4]
            key = fb
            stem = (f"One {tod}, soon after sunrise," if tod == "morning" else f"One evening, shortly before sunset,") + \
                   f" {a} and {b} were {pose}. {a}'s shadow fell exactly to {a}'s {side}. Which direction was {b} facing?"
            steps = [f"The sun is in the {'East' if tod == 'morning' else 'West'}, so shadows fall to the {shadow}.",
                     f"{shadow} is on {a}'s {side} → {a} faces {fa}.", f"{b} {'faces ' + a if pose == 'facing each other' else 'has back to ' + a} → faces {fb}."]
        else:
            key = fa
            stem = f"One morning after sunrise, {a} was walking and noticed that the shadow fell exactly to the {side}. In which direction was {a} walking?"
            steps = ["Morning sun in the East → shadow to the West.", f"West is on the {side} → walking {fa}."]
        cands = [(d, "shadow direction or side confused") for d in DIRS if d != key]
        q(B, M_DREL, "L3", "officer", stem, key, cands, steps, "Morning shadow → West; evening shadow → East",
          "Facing each other or back to back, the two people face opposite directions.", kind="conceptual")
    # officer case set: network of points
    pos = {"A": (0, 0)}
    rels = [("B", "A", 10, 0), ("C", "B", 0, 6), ("D", "C", -4, 0), ("E", "D", 0, -12), ("F", "E", -6, 0)]
    for p, r, dx, dy in rels:
        pos[p] = (pos[r][0] + dx, pos[r][1] + dy)
    text = " ".join(f"Point {p} is {abs(dx)+abs(dy)} m {dir_name(dx, dy).lower()} of point {r}." for p, r, dx, dy in rels)
    head = "Study the information and answer the questions.\n\n" + text + f" {DCONV}"
    qs = []
    for u, v in [("F", "B"), ("D", "A")]:
        dx, dy = pos[u][0] - pos[v][0], pos[u][1] - pos[v][1]
        key = dir_name(dx, dy)
        qs.append((f"In which direction is point {u} with respect to point {v}?", key, dir_cands(key), [f"{u} = {pos[u]}, {v} = {pos[v]} → ({dx}, {dy}) → {key}."]))
    d2 = (pos["E"][0] - pos["A"][0]) ** 2 + (pos["E"][1] - pos["A"][1]) ** 2
    qs.append(("What is the shortest distance between points A and E?", dist_txt(d2),
               [(f"{abs(pos['E'][0])+abs(pos['E'][1])} m", "added the legs instead of using Pythagoras"), (dist_txt(d2 + 20), "arithmetic slip in squaring"),
                (f"{10 + 6 + 4 + 12} m", "added the whole path")], [f"A = (0, 0), E = {pos['E']} → √({pos['E'][0]}² + {pos['E'][1]}²) = {dist_txt(d2)}."]))
    cands = [p for p in pos if p != "A"]
    exact = [p for p in cands if pos[p][0] == pos["A"][0] or pos[p][1] == pos["A"][1]]
    # which point lies exactly south of C?
    south_c = [p for p in pos if pos[p][0] == pos["C"][0] and pos[p][1] < pos["C"][1]]
    assert south_c == ["B"]
    qs.append(("Which point lies exactly south of point C?", "B", [("E", "E is south-west of C"), ("A", "A is south-west of C"), ("F", "F is south-west of C")],
               [f"C = {pos['C']}; B = {pos['B']} has the same x and smaller y."]))
    for st, key, cands_, steps in qs:
        q(B, M_DREL, "L4", "officer", head + "\n\n" + st, key, cands_, ["Place A at (0, 0): " + ", ".join(f"{k}={v}" for k, v in pos.items()) + "."] + steps,
          "Coordinates", "Plot every point before answering.", kind="case", group="GRB-DIR-SET1")


def path_tracing(B):
    specs = [("foundation", "L1", 3, "face"), ("foundation", "L1", 3, "face"), ("foundation", "L2", 4, "face"), ("foundation", "L2", 3, "pos"),
             ("foundation", "L2", 4, "pos")] + [("officer", "L3", 5, "face"), ("officer", "L3", 5, "pos"), ("officer", "L3", 6, "pos"),
                                                ("officer", "L3", 5, "pos"), ("officer", "L3", 6, "face")]
    for i, (tier, lvl, n, mode) in enumerate(specs):
        face, legs, x, y, f = pick_walk(f"GRB-path-{i}", n, lambda x, y, f, l: (x == 0) != (y == 0) if mode == "pos" else True)
        nm = NAMES[(i + 4) % len(NAMES)]
        if mode == "face":
            key = f
            stem = describe(nm, face, legs) + f" Which direction is {nm} facing now?"
            cands = [(DIRS[(DIRS.index(f) + 2) % 4], "reversed a turn"), (DIRS[(DIRS.index(f) + 1) % 4], "one turn misread"), (DIRS[(DIRS.index(f) + 3) % 4], "one turn misread (other side)")]
            steps = ["Track facing after each turn: start " + face + "; " + ", ".join(t for t, _ in legs[1:]) + f" → {f}."]
        else:
            d = abs(x) + abs(y)
            key = f"{d} m {dir_name(x, y)}"
            opp_ = dir_name(-x, -y)
            total = sum(dd for _, dd in legs)
            cands = [(f"{d} m {opp_}", "direction reversed"), (f"{total} m {dir_name(x, y)}", "added the whole path"),
                     (f"{d + 2} m {dir_name(x, y)}", "arithmetic slip"), (f"{abs(d - 2)} m {dir_name(x, y)}", "arithmetic slip")]
            stem = describe(nm, face, legs) + f" How far and in which direction is {nm} now from the starting point S?"
            steps = [f"Net displacement: ({x}, {y}).", f"Distance {d} m towards the {dir_name(x, y)}."]
        q(B, M_PATH, lvl, tier, stem, key, cands, steps, "Right turn = clockwise 90°, left = anticlockwise 90°",
          "Left and right are relative to the current facing, not to the map.", kind="conceptual")
    # rotation-by-degrees items (officer extra) — replace nothing; counts: 5 foundation + 5 officer so far
    rot = [("North", [(135, "clockwise"), (270, "anticlockwise")]), ("West", [(90, "clockwise"), (225, "anticlockwise"), (45, "clockwise")]),
           ("South", [(45, "anticlockwise"), (180, "clockwise"), (90, "anticlockwise")]), ("East", [(315, "clockwise"), (90, "anticlockwise")]),
           ("North-East", [(90, "anticlockwise"), (135, "anticlockwise")])]
    for face, turns in rot:
        a = ALL8.index(face) * 45
        for deg, sense in turns:
            a = (a + (deg if sense == "clockwise" else -deg)) % 360
        key = ALL8[a // 45]
        stem = f"A man is facing {face}. He turns " + ", then ".join(f"{d}° {s}" for d, s in turns) + ". Which direction is he facing now?"
        # distractor: all turns taken clockwise
        a2 = ALL8.index(face) * 45 + sum(d for d, _ in turns)
        cands = [(ALL8[(a2 % 360) // 45], "treated every turn as clockwise")] + dir_cands(key)
        q(B, M_PATH, "L3", "officer", stem, key, cands,
          [f"Start at {ALL8.index(face)*45}° (North = 0°, clockwise positive).", f"Net angle = {a}° → {key}."],
          "Net rotation = Σ clockwise − Σ anticlockwise (mod 360°)", "Anticlockwise turns subtract.", kind="conceptual")


TRIPLES = [(3, 4), (6, 8), (5, 12), (8, 15), (9, 12), (12, 16), (7, 24), (15, 20)]


def pythagoras(B):
    specs = [("foundation", "L1", 3), ("foundation", "L2", 3), ("foundation", "L2", 4), ("foundation", "L2", 4), ("foundation", "L2", 3),
             ("officer", "L3", 5), ("officer", "L3", 5), ("officer", "L3", 6), ("officer", "L3", 5), ("officer", "L3", 6),
             ("officer", "L3", 5), ("officer", "L3", 6)]
    def trip(x, y, f, l):
        a, b = sorted((abs(x), abs(y)))
        return (a, b) in TRIPLES
    for i, (tier, lvl, n) in enumerate(specs):
        face, legs, x, y, f = pick_walk(f"GRB-pyt-{i}", n, trip, 2, 20)
        d = math.isqrt(x * x + y * y)
        nm = NAMES[(i + 7) % len(NAMES)]
        total = sum(dd for _, dd in legs)
        stem = describe(nm, face, legs) + f" What is the shortest distance between {nm}'s final position and S?"
        q(B, M_PYT, lvl, tier, stem, f"{d} m",
          [(f"{abs(x)+abs(y)} m", "added the net east-west and north-south distances"), (f"{total} m", "added the whole path"),
           (f"{abs(abs(x)-abs(y))} m", "subtracted instead of using Pythagoras"), (f"{d + 1} m", "arithmetic slip")],
          [f"Net displacement: {abs(x)} m {'East' if x > 0 else 'West'}, {abs(y)} m {'North' if y > 0 else 'South'}.", f"√({abs(x)}² + {abs(y)}²) = {d} m."],
          "Shortest distance = √(Δx² + Δy²)", "Net out opposite legs first, then apply Pythagoras.")
    # non-integer answers (surd form)
    for i in range(3):
        face, legs, x, y, f = pick_walk(f"GRB-pyts-{i}", 4, lambda x, y, f, l: x != 0 and y != 0 and math.isqrt(x * x + y * y) ** 2 != x * x + y * y)
        d2 = x * x + y * y
        nm = NAMES[(i + 11) % len(NAMES)]
        stem = describe(nm, face, legs) + f" What is the shortest distance between {nm}'s final position and S?"
        q(B, M_PYT, "L3", "officer", stem, f"√{d2} m",
          [(f"{abs(x)+abs(y)} m", "added the net distances"), (dist_txt(abs(x * x - y * y)) if x * x != y * y else "0 m", "subtracted the squares"),
           (dist_txt(d2 + 2 * abs(x * y)), "used (a + b)² instead of a² + b²"), (f"{sum(dd for _, dd in legs)} m", "added the whole path"),
           (dist_txt(d2 + 1), "arithmetic slip")],
          [f"Net displacement: ({x}, {y}).", f"√({abs(x)}² + {abs(y)}²) = √{d2} m."], "Shortest distance = √(Δx² + Δy²)", "Leave the answer in surd form when it is not a perfect square.")


def two_person(B):
    rng = random.Random("GRB-two")
    made = {"foundation": 0, "officer": 0}
    i = 0
    while made["foundation"] < 5 or made["officer"] < 10:
        i += 1
        tier = "foundation" if made["foundation"] < 5 else "officer"
        n = 2 if tier == "foundation" else rng.choice([3, 3, 4])
        fa, la, xa, ya, _ = pick_walk(f"GRB-twoA-{i}", n, lambda *a: True, 2, 12)
        fb, lb, xb, yb, _ = pick_walk(f"GRB-twoB-{i}", n, lambda *a: True, 2, 12)
        dx, dy = xa - xb, ya - yb
        d2 = dx * dx + dy * dy
        if d2 == 0:
            continue
        if tier == "foundation" and (math.isqrt(d2) ** 2 != d2 or (dx != 0 and dy != 0 and (sorted((abs(dx), abs(dy))) not in [list(t) for t in TRIPLES]))):
            continue
        a, b = NAMES[i % 16], NAMES[(i + 5) % 16]
        mode = "dist" if (made[tier] % 2 == 0) else "dir"
        if mode == "dir" and (dx == 0 or dy == 0) and tier == "officer":
            pass
        sa = describe(a, fa, la).replace("point S", "the same point S")
        sb = describe(b, fb, lb).replace("point S", "the same point S")
        if mode == "dist":
            key = dist_txt(d2)
            cands = [(f"{abs(dx)+abs(dy)} m", "added the gaps instead of Pythagoras"), (dist_txt(xa * xa + ya * ya + xb * xb + yb * yb), "added squared distances from S"),
                     (dist_txt(d2 + 4), "arithmetic slip"), (f"{abs(dx)+abs(dy)+2} m", "arithmetic slip")]
            st = f"What is the shortest distance between {a} and {b} now?"
            steps = [f"{a} ends at ({xa}, {ya}); {b} ends at ({xb}, {yb}).", f"Gap: ({dx}, {dy}) → {key}."]
            formula = "√(Δx² + Δy²)"
        else:
            key = dir_name(dx, dy)
            cands = dir_cands(key)
            st = f"In which direction is {a} with respect to {b} now? {DCONV}"
            steps = [f"{a} ends at ({xa}, {ya}); {b} ends at ({xb}, {yb}).", f"{a} − {b} = ({dx}, {dy}) → {key}."]
            formula = "Direction of A from B = sign of (xA − xB, yA − yB)"
        stem = sa + " " + sb + " " + st
        lvl = "L2" if tier == "foundation" else "L3"
        q(B, M_TWO, lvl, tier, stem, key, cands, steps, formula, "Work out both end points from the same origin before comparing.", kind="conceptual")
        made[tier] += 1


# ---------------- ordering puzzles ----------------
def solve_order(names, clues):
    """order = tuple from highest to lowest (tallest/oldest/heaviest first)."""
    sols = []
    for perm in itertools.permutations(names):
        r = {n: i for i, n in enumerate(perm)}  # 0 = highest
        if all(c(r, len(names)) for c in clues):
            sols.append(perm)
    return sols


def gt(a, b):
    return lambda r, n: r[a] < r[b]


def rank_is(a, k):
    return lambda r, n: r[a] == k - 1


def not_rank(a, k):
    return lambda r, n: r[a] != k - 1


def above_count(a, k):
    return lambda r, n: r[a] == k


def below_count(a, k):
    return lambda r, n: n - 1 - r[a] == k


def order_puzzles(B):
    ORD = {"height": ("taller", "shorter", "tallest", "shortest"), "age": ("older", "younger", "oldest", "youngest"),
           "weight": ("heavier", "lighter", "heaviest", "lightest"), "marks": ("scored more than", "scored less than", "highest scorer", "lowest scorer")}

    def ordq(micro, tier, lvl, names, clue_txt, clues, attr, asks, group=None, intro=None):
        sols = solve_order(names, clues)
        assert len(sols) >= 1, clue_txt
        more, less, top, bot = ORD[attr]
        head = (intro or f"Among {len(names)} persons {', '.join(names[:-1])} and {names[-1]}, no two have the same {attr}.") + "\n\n" + "\n".join(f"- {c}" for c in clue_txt)
        for st, fn, cfn in asks:
            vals = {fn(s) for s in sols}
            assert len(vals) == 1, (st, vals, len(sols))
            key = vals.pop()
            cands = cfn(sols[0], key)
            if isinstance(key, int):
                cands = numd(key, cands)
            order_s = " > ".join(sols[0]) if len(sols) == 1 else f"{len(sols)} possible orders; the answer is the same in all"
            q(B, micro, lvl, tier, head + "\n\n" + st, key, cands,
              [f"Arrangement (greatest to least): {order_s}.", f"Answer: {key}."], "Chain the comparisons into one order",
              "Combine every clue before answering; 'only two are taller' fixes an exact rank.", kind="case" if group else "conceptual", group=group)

    def by_rank(k):
        return lambda s: s[k - 1]

    def others(s, key):
        return [(x, "misplaced in the order") for x in s if x != key]

    # ----- age & height : foundation
    F = [(list("ABCDE"), ["A is taller than B.", "C is taller than A.", "D is shorter than B.", "E is taller than C."],
          [gt("A", "B"), gt("C", "A"), gt("B", "D"), gt("E", "C")], "height", [("Who is the second tallest?", by_rank(2), others)]),
         (list("PQRST"), ["P is older than Q but younger than R.", "S is younger than Q.", "T is older than R."],
          [gt("P", "Q"), gt("R", "P"), gt("Q", "S"), gt("T", "R")], "age", [("Who is the youngest?", by_rank(5), others)]),
         (list("MNOPQ"), ["M is taller than N but shorter than O.", "P is shorter than N.", "Q is taller than O."],
          [gt("M", "N"), gt("O", "M"), gt("N", "P"), gt("Q", "O")], "height", [("Who is exactly in the middle when arranged by height?", by_rank(3), others)]),
         (list("JKLMN"), ["J is older than K.", "L is younger than K but older than M.", "N is older than J."],
          [gt("J", "K"), gt("K", "L"), gt("L", "M"), gt("N", "J")], "age",
          [("How many persons are younger than K?", lambda s: 4 - s.index("K"), lambda s, k: [(k + 1, "counted K"), (4 - k, "counted older persons"), (k - 1, "missed one")])]),
         (list("ABCDE"), ["A is taller than B and C.", "D is taller than A.", "E is shorter than C.", "B is taller than C."],
          [gt("A", "B"), gt("A", "C"), gt("D", "A"), gt("C", "E"), gt("B", "C")], "height", [("Who is the shortest?", by_rank(5), others)])]
    for names, ct, cl, attr, asks in F:
        ordq(M_AGE, "foundation", "L1" if len(ct) <= 3 else "L2", names, ct, cl, attr, asks)
    # ----- officer set 1 (height, 6 persons)
    names = list("ABCDEF")
    ct = ["Only two persons are taller than F.", "B is taller than D but is not the tallest.", "E is shorter than F but taller than D.",
          "C is taller than A.", "A is taller than B.", "B is taller than E."]
    cl = [above_count("F", 2), gt("B", "D"), not_rank("B", 1), gt("F", "E"), gt("E", "D"), gt("C", "A"), gt("A", "B"), gt("B", "E")]
    assert len(solve_order(names, cl)) == 1, solve_order(names, cl)
    ordq(M_AGE, "officer", "L4", names, ct, cl, "height",
         [("Who is the tallest?", by_rank(1), others), ("Who is the shortest?", by_rank(6), others),
          ("How many persons are taller than E?", lambda s: s.index("E"), lambda s, k: [(k + 1, "counted E"), (k - 1, "missed one"), (5 - k, "counted shorter persons")]),
          ("Who is third from the shortest end?", lambda s: s[3], others)], group="GRB-AGE-SET1")
    # ----- officer set 2 (age, 6 persons)
    names = list("PQRSTU")
    ct = ["Exactly one person is older than R.", "T is younger than Q but older than S.", "U is older than T.", "P is the youngest.",
          "Q is younger than U.", "S is not younger than P."]
    cl = [above_count("R", 1), gt("Q", "T"), gt("T", "S"), gt("U", "T"), rank_is("P", 6), gt("U", "Q"), gt("S", "P")]
    sols = solve_order(names, cl)
    ordq(M_AGE, "officer", "L4", names, ct, cl, "age",
         [("Who is the oldest?", by_rank(1), others), ("Who is the second youngest?", by_rank(5), others),
          ("Who is exactly two places older than S in the order of age?", lambda s: s[s.index("S") - 2], others)], group="GRB-AGE-SET2")
    # ----- officer standalone: which is definitely true
    names = list("VWXYZ")
    ct = ["V is taller than W.", "X is shorter than W but taller than Y.", "Z is shorter than V."]
    cl = [gt("V", "W"), gt("W", "X"), gt("X", "Y"), gt("V", "Z")]
    sols = solve_order(names, cl)
    stmts = [("V is the tallest.", lambda s: s[0] == "V"), ("Z is shorter than X.", lambda s: s.index("Z") > s.index("X")),
             ("Y is the shortest.", lambda s: s[-1] == "Y"), ("W is the second tallest.", lambda s: s[1] == "W")]
    truth = {t: all(f(s) for s in sols) for t, f in stmts}
    assert list(truth.values()).count(True) == 1, truth
    key = [t for t, v in truth.items() if v][0]
    head = f"Among five persons V, W, X, Y and Z, no two have the same height.\n\n" + "\n".join(f"- {c}" for c in ct) + "\n\nWhich of the following is definitely true?"
    q(B, M_AGE, "L3", "officer", head, key, [(t, "possible but not certain") for t, v in truth.items() if not v],
      [f"{len(sols)} orders are possible, e.g. " + "; ".join(" > ".join(s) for s in sols[:3]) + ".", f"Only '{key}' holds in all of them."],
      "A statement is definitely true only if it holds in every possible order", "Z's position is not fixed relative to W, X, Y.")
    names = list("GHIJK")
    ct = ["G is older than H but younger than I.", "J is younger than H.", "K is older than J but younger than G."]
    cl = [gt("G", "H"), gt("I", "G"), gt("H", "J"), gt("K", "J"), gt("G", "K")]
    sols = solve_order(names, cl)
    stmts = [("J is the youngest.", lambda s: s[-1] == "J"), ("K is older than H.", lambda s: s.index("K") < s.index("H")),
             ("H is the second youngest.", lambda s: s[3] == "H"), ("G is the oldest.", lambda s: s[0] == "G")]
    truth = {t: all(f(s) for s in sols) for t, f in stmts}
    assert list(truth.values()).count(True) == 1, truth
    key = [t for t, v in truth.items() if v][0]
    head = f"Among five persons G, H, I, J and K, no two are of the same age.\n\n" + "\n".join(f"- {c}" for c in ct) + "\n\nWhich of the following is definitely true?"
    q(B, M_AGE, "L3", "officer", head, key, [(t, "possible but not certain" if any(f(s) for s in sols) else "false") for (t, f) in stmts if t != key],
      [f"Possible orders: " + "; ".join(" > ".join(s) for s in sols) + ".", f"Only '{key}' holds in all of them."],
      "Definitely true = true in every case", "H and K can be in either order.")
    # one more officer standalone (age with count clue)
    names = list("ABCDEF")
    ct = ["C is older than exactly two persons.", "A is older than C.", "F is younger than D but older than C.", "B is the youngest.", "E is younger than C."]
    cl = [below_count("C", 2), gt("A", "C"), gt("D", "F"), gt("F", "C"), rank_is("B", 6), gt("C", "E")]
    sols = solve_order(names, cl)
    ordq(M_AGE, "officer", "L3", names, ct, cl, "age", [("Who is the second youngest?", by_rank(5), others)])

    # ----- comparison by attribute (weights / marks) -----
    F2 = [(list("PQRST"), ["P is heavier than Q.", "R is lighter than Q but heavier than T.", "S is heavier than P."],
           [gt("P", "Q"), gt("Q", "R"), gt("R", "T"), gt("S", "P")], "weight", [("Who is the third heaviest?", by_rank(3), others)]),
          (list("ABCDE"), ["A scored more than B.", "C scored less than D but more than A.", "E scored less than B."],
           [gt("A", "B"), gt("D", "C"), gt("C", "A"), gt("B", "E")], "marks", [("Who scored the second highest marks?", by_rank(2), others)]),
          (list("KLMNO"), ["K is heavier than L and M.", "N is heavier than K.", "M is heavier than L.", "O is lighter than L."],
           [gt("K", "L"), gt("K", "M"), gt("N", "K"), gt("M", "L"), gt("L", "O")], "weight", [("Who is the lightest?", by_rank(5), others)]),
          (list("UVWXY"), ["V scored more than only two students.", "W scored more than V.", "X scored less than Y.", "U scored the highest."],
           [below_count("V", 2), gt("W", "V"), gt("Y", "X"), rank_is("U", 1)], "marks", [("Who scored the lowest marks?", by_rank(5), others)]),
          (list("FGHIJ"), ["F is heavier than G but lighter than H.", "I is lighter than G.", "J is heavier than H."],
           [gt("F", "G"), gt("H", "F"), gt("G", "I"), gt("J", "H")], "weight",
           [("How many persons are heavier than G?", lambda s: s.index("G"), lambda s, k: [(k + 1, "counted G"), (k - 1, "missed one"), (4 - k, "counted lighter persons")])])]
    for names, ct, cl, attr, asks in F2:
        ordq(M_ATTR, "foundation", "L2", names, ct, cl, attr, asks,
             intro=f"Five persons {', '.join(names[:-1])} and {names[-1]} are compared by {attr}; no two are equal.")
    # officer set: marks with numbers
    names = list("PQRST")
    ct = ["R scored more than only T.", "P scored more than Q.", "The student who scored the third highest marks scored 64.",
          "S scored 12 marks more than the third highest scorer.", "S did not score the highest marks."]
    cl = [rank_is("R", 4), rank_is("T", 5), gt("P", "Q"), lambda r, n: r["S"] < 2, not_rank("S", 1)]
    sols = solve_order(names, cl)
    assert len(sols) == 1, sols
    s0 = sols[0]
    grp = "GRB-ATTR-SET1"
    head = "Five students P, Q, R, S and T scored different marks in a test.\n\n" + "\n".join(f"- {c}" for c in ct)
    thirds = s0[2]
    sq = [("Who scored 64 marks?", thirds, others(s0, thirds), [f"Order: {' > '.join(s0)}.", f"Third highest = {thirds}."]),
          ("What are S's marks?", 76, [(52, "subtracted 12"), (64, "took S as third"), (74, "added 10")], ["S = 64 + 12 = 76."]),
          ("Who scored the highest marks?", s0[0], others(s0, s0[0]), [f"Order: {' > '.join(s0)}."]),
          ("How many students scored less than 64?", 2, [(3, "counted the third scorer"), (1, "counted only T"), (4, "counted everyone else")], [f"Below the third scorer: {s0[3]}, {s0[4]} → 2."])]
    assert s0[1] == "S"
    for st, key, cands, steps in sq:
        q(B, M_ATTR, "L4", "officer", head + "\n\n" + st, key, cands, steps, "Fix ranks first, then attach the numbers",
          "'More than only T' means exactly one person is below.", kind="case", group=grp)
    # officer set 2: weights 6 persons
    names = list("ABCDEF")
    ct = ["B is heavier than only three boxes.", "D is heavier than B but lighter than F.", "A is lighter than E.", "C is the lightest.",
          "E is lighter than B."]
    cl = [below_count("B", 3), gt("D", "B"), gt("F", "D"), gt("E", "A"), rank_is("C", 6), gt("B", "E")]
    sols = solve_order(names, cl)
    ordq(M_ATTR, "officer", "L4", names, ct, cl, "weight",
         [("Who is the heaviest?", by_rank(1), others), ("Who is the second lightest?", by_rank(5), others),
          ("Which box is exactly midway between D and E in the order of weight?", lambda s: s[(s.index("D") + s.index("E")) // 2] if abs(s.index("E") - s.index("D")) == 2 else None, others)],
         group="GRB-ATTR-SET2", intro="Six boxes A, B, C, D, E and F have different weights.")
    # officer standalone (3)
    stand = [
        (list("PQRST"), ["Q earns more than R but less than S.", "P earns less than R.", "T earns more than S."],
         [gt("Q", "R"), gt("S", "Q"), gt("R", "P"), gt("T", "S")], "Who earns the second lowest salary?", by_rank(4),
         "Five colleagues P, Q, R, S and T earn different salaries."),
        (list("JKLMN"), ["L is heavier than M but lighter than J.", "K is lighter than N.", "N is lighter than M."],
         [gt("L", "M"), gt("J", "L"), gt("N", "K"), gt("M", "N")], "Who is the lightest?", by_rank(5),
         "Five parcels J, K, L, M and N have different weights."),
        (list("ABCDEF"), ["Only one car is faster than D.", "B is slower than E but faster than F.", "A is faster than D.", "C is slower than F.", "E is slower than D."],
         [above_count("D", 1), gt("E", "B"), gt("B", "F"), gt("A", "D"), gt("F", "C"), gt("D", "E")], "Which car is the fourth fastest?", by_rank(4),
         "Six cars A, B, C, D, E and F in a race have different speeds (listed fastest first)."),
    ]
    for names, ct, cl, st, fn, intro in stand:
        ordq(M_ATTR, "officer", "L3", names, ct, cl, "weight", [(st, fn, others)], intro=intro)


# ---------------- position from either end / total count ----------------
def row_check(n, pos_left):
    """return (pos_left, pos_right) consistency helper."""
    return pos_left, n - pos_left + 1


def positions(B):
    items = []
    # foundation
    for (l, r, nm) in [(12, 17, "Ravi"), (9, 23, "Asha"), (15, 15, "Imran")]:
        n = l + r - 1
        row = [None] * n; row[l - 1] = nm
        assert row[::-1].index(nm) + 1 == r
        items.append(("foundation", "L1", f"In a row of children, {nm} is {l}th from the left end and {r}th from the right end. How many children are there in the row?",
                      n, [(l + r, "did not subtract 1"), (l + r - 2, "subtracted 2"), (abs(l - r), "took the difference")],
                      [f"Total = {l} + {r} − 1 = {n}."]))
    n, l = 40, 13
    items.append(("foundation", "L1", f"In a row of {n} students, Pooja is {l}th from the left. What is her position from the right?", n - l + 1,
                  [(n - l, "did not add 1"), (n - l + 2, "added 2"), (l, "repeated the left position")], [f"Right position = {n} − {l} + 1 = {n-l+1}."]))
    t, b = 7, 26
    items.append(("foundation", "L2", f"In a class, Kiran's rank is {t}th from the top and {b}th from the bottom. How many students are there in the class?", t + b - 1,
                  [(t + b, "did not subtract 1"), (b - t, "took the difference"), (t + b - 2, "subtracted 2")], [f"Total = {t} + {b} − 1 = {t+b-1}."]))
    # officer
    t, b, fail, absent = 9, 38, 5, 3
    total = t + b - 1 + fail + absent
    items.append(("officer", "L3", f"In an examination, Riya ranked {t}th from the top and {b}th from the bottom among the students who passed. {fail} students failed and {absent} were absent. How many students were enrolled?",
                  total, [(t + b - 1, "ignored failed and absent students"), (t + b - 1 + fail, "ignored absent students"), (t + b + fail + absent, "did not subtract 1")],
                  [f"Passed = {t} + {b} − 1 = {t+b-1}.", f"Enrolled = {t+b-1} + {fail} + {absent} = {total}."]))
    # interchange
    a_l, b_r, a_new = 10, 18, 15
    n = a_new + b_r - 1
    row = list(range(n)); row = [None] * n; row[a_l - 1] = "A"; row[n - b_r] = "B"
    i, j = row.index("A"), row.index("B"); row[i], row[j] = row[j], row[i]
    assert row.index("A") + 1 == a_new
    items.append(("officer", "L3", f"In a row, A is {a_l}th from the left and B is {b_r}th from the right. When they interchange positions, A becomes {a_new}th from the left. How many persons are in the row?",
                  n, [(a_l + b_r - 1, "used A's old position"), (a_new + b_r, "did not subtract 1"), (a_new + a_l + b_r - 1, "added all positions")],
                  [f"After the swap A occupies B's old seat: {a_new}th from left and {b_r}th from right.", f"Total = {a_new} + {b_r} − 1 = {n}."]))
    # interchange 2: new position of B
    n, a_l, b_l = 45, 12, 30
    row = [None] * n; row[a_l - 1] = "A"; row[b_l - 1] = "B"
    i, j = row.index("A"), row.index("B"); row[i], row[j] = row[j], row[i]
    new_b_r = n - row.index("B")
    items.append(("officer", "L3", f"In a row of {n} persons, A is {a_l}th from the left and B is {b_l}th from the left. If A and B interchange positions, what will be B's position from the right end?",
                  new_b_r, [(n - b_l + 1, "B's old position from the right"), (new_b_r - 1, "did not add 1"), (a_l, "B's new position from the left")],
                  [f"B moves to position {a_l} from left.", f"From right: {n} − {a_l} + 1 = {new_b_r}."]))
    # persons between
    n, a_l, b_r = 50, 14, 20
    b_l = n - b_r + 1
    between = b_l - a_l - 1
    items.append(("officer", "L3", f"In a row of {n} persons, P is {a_l}th from the left and Q is {b_r}th from the right. How many persons are there between P and Q?",
                  between, [(between + 1, "counted one of them"), (n - a_l - b_r, "subtracted positions directly"), (between + 2, "counted both")],
                  [f"Q from left = {n} − {b_r} + 1 = {b_l}.", f"Between = {b_l} − {a_l} − 1 = {between}."]))
    # middle person
    n = 41
    mid = (n + 1) // 2
    items.append(("officer", "L2", f"In a row of {n} girls, Divya is exactly in the middle. What is her position from the left end?", mid,
                  [(n // 2, "took half without rounding up"), (mid + 1, "counted one extra"), (n - mid, "subtracted from total")], [f"Middle of {n} = ({n} + 1) ÷ 2 = {mid}."]))
    # shift
    n, l, move = 36, 11, 7
    items.append(("officer", "L3", f"In a row of {n} students, Manoj is {l}th from the left. If he moves {move} places to the right, what will be his position from the right end?",
                  n - (l + move) + 1, [(n - (l + move), "did not add 1"), (n - l + 1, "ignored the move"), (n - (l - move) + 1, "moved left instead")],
                  [f"New left position = {l} + {move} = {l+move}.", f"From right = {n} − {l+move} + 1 = {n-l-move+1}."]))
    # 1-in-3 etc: rank among boys & girls
    tb, bb, girls = 11, 16, 12
    items.append(("officer", "L3", f"In a class, Rohit is {tb}th from the top and {bb}th from the bottom among the boys. There are {girls} girls in the class. How many students are in the class?",
                  tb + bb - 1 + girls, [(tb + bb - 1, "forgot the girls"), (tb + bb + girls, "did not subtract 1"), (tb + bb - 1 + girls - 1, "subtracted twice")],
                  [f"Boys = {tb} + {bb} − 1 = {tb+bb-1}.", f"Class = {tb+bb-1} + {girls} = {tb+bb-1+girls}."]))
    # position after removing
    n, l = 30, 18
    items.append(("officer", "L3", f"In a row of {n} chairs numbered from the left, the first 5 chairs from the left are removed. What is the position from the right end of the chair that was originally {l}th from the left?",
                  n - l + 1, [(n - 5 - (l - 5) + 1 - 1, "did not add 1"), (l - 5, "new position from the left"), (n - l + 1 - 5, "subtracted the removed chairs from the right count")],
                  ["Removing chairs on the left does not change positions counted from the right.", f"From right = {n} − {l} + 1 = {n-l+1}."]))
    items.append(("officer", "L3", "In a row of boys, Farhan is 7th from the left and Vikram is 12th from the right. If they interchange positions, Farhan becomes 22nd from the left. What is Vikram's new position from the right?",
                  33 - 7 + 1, [(12, "Vikram's old position from right"), (22, "Farhan's new position"), (33 - 7, "did not add 1")],
                  ["Total = 22 + 12 − 1 = 33.", "Vikram now sits in Farhan's old seat: 7th from left → 33 − 7 + 1 = 27th from right."]))
    assert 22 + 12 - 1 == 33
    n, a, k = 21, 5, 3
    b_pos, c_pos = a + k, (n + 1) // 2
    items.append(("officer", "L3", f"In a row of {n} persons, A is {a}th from the left and B is {k} places to the right of A. C is exactly in the middle of the row. How many persons are there between B and C?",
                  c_pos - b_pos - 1, [(c_pos - b_pos, "did not subtract 1"), (c_pos - a - 1, "measured from A"), (c_pos - b_pos + 1, "counted both")],
                  [f"B = {b_pos}th, C = {c_pos}th from the left.", f"Between = {c_pos} − {b_pos} − 1 = {c_pos-b_pos-1}."]))
    for tier, lvl, stem, key, cands, steps in items:
        q(B, M_POS, lvl, tier, stem, key, numd(key, cands), steps, "Total = Left + Right − 1", "Always subtract 1: the person is counted from both ends.")


def totals(B):
    def possible(a_front, b_back, gap, lo=1, hi=80):
        out = set()
        for n in range(lo, hi):
            pa = a_front
            pb = n - b_back + 1
            if not (1 <= pa <= n and 1 <= pb <= n) or pa == pb:
                continue
            if abs(pa - pb) - 1 == gap:
                out.add(n)
        return sorted(out)
    items = []
    # foundation
    s = possible(8, 10, 3)
    items.append(("foundation", "L2", "In a queue, A is 8th from the front and B is 10th from the back. There are 3 persons between A and B, and A is ahead of B. How many persons are in the queue?",
                  8 + 3 + 10, [(8 + 10 + 3 - 1, "subtracted 1 as if counting one person twice"), (8 + 10, "ignored those in between"), (8 + 10 + 3 + 1, "added 1")],
                  ["A ahead of B, no overlap: 8 + 3 + 10 = 21.", f"(Check by enumeration: totals possible = {s}; with A ahead of B only 21.)"]))
    assert 21 in s
    items.append(("foundation", "L1", "In a row, there are 6 persons to the left of Neha and 9 persons to her right. How many persons are in the row?", 16,
                  [(15, "forgot Neha"), (17, "counted Neha twice"), (14, "subtracted 1")], ["6 + 1 + 9 = 16."]))
    items.append(("foundation", "L2", "In a row of trees, one tree is 7th from either end. How many trees are there in the row?", 13,
                  [(14, "did not subtract 1"), (12, "subtracted 2"), (7, "took one side only")], ["7 + 7 − 1 = 13."]))
    items.append(("foundation", "L2", "Students stand in a line. Asha is 12th from the front; there are 5 students between Asha and Lata, and Lata is the last in the line. How many students are in the line?",
                  12 + 5 + 1, [(12 + 5, "forgot Lata"), (12 + 5 + 2, "counted Asha twice"), (12 + 6 + 1, "miscounted the gap")], ["Positions: Asha 12th, then 5 students, then Lata → 12 + 5 + 1 = 18."]))
    items.append(("foundation", "L2", "In a row of 25 people, Raju is 10th from the left. Sonu is 4 places to the right of Raju. What is Sonu's position from the right end?", 25 - 14 + 1,
                  [(25 - 14, "did not add 1"), (14, "Sonu's position from left"), (25 - 6 + 1, "moved left")], ["Sonu from left = 14 → from right = 25 − 14 + 1 = 12."]))
    # officer: minimum / possible values
    s = possible(10, 8, 3)
    mn = min(s)
    items.append(("officer", "L3", "In a queue, P is 10th from the front and Q is 8th from the back. There are exactly 3 persons between P and Q. What is the minimum possible number of persons in the queue?",
                  mn, [(max(s), "assumed P is ahead of Q"), (10 + 8 - 1, "treated them as the same person"), (10 + 8 + 3 - 1, "subtracted 1 from the larger case")],
                  [f"Enumerating queue lengths: possible totals = {s}.", f"Q ahead of P (overlap) gives the minimum {mn}."]))
    s2 = possible(15, 12, 4)
    items.append(("officer", "L3", "In a row, R is 15th from the left and S is 12th from the right. There are 4 persons between R and S. How many different totals are possible for the number of persons in the row?",
                  len(s2), [(1, "considered only one arrangement"), (3, "added a case where they coincide"), (4, "double-counted")],
                  [f"Possible totals by enumeration: {s2}.", f"Count = {len(s2)}."]))
    items.append(("officer", "L3", "In a row, R is 15th from the left and S is 12th from the right. There are 4 persons between R and S. What is the maximum possible number of persons in the row?",
                  max(s2), [(min(s2), "took the overlap case"), (15 + 12 - 1, "treated R and S as one person"), (15 + 12 + 4 - 1, "subtracted 1 wrongly")],
                  [f"Possible totals: {s2}.", f"Maximum = {max(s2)} (R left of S, no overlap)."]))
    # interchange leading to total
    items.append(("officer", "L3", "In a row, M is 9th from the left and N is 16th from the right. After they interchange positions, M becomes 20th from the left. How many persons are in the row?",
                  20 + 16 - 1, [(9 + 16 - 1, "used M's old position"), (20 + 16, "did not subtract 1"), (20 + 9, "added M's positions")],
                  ["M takes N's seat: 20th from left, 16th from right.", "Total = 20 + 16 − 1 = 35."]))
    # every third
    n = 40
    items.append(("officer", "L3", f"There are {n} persons in a row. Starting from the left, every third person wears a cap (3rd, 6th, 9th, …). Starting from the right, every fourth person wears a badge. How many persons wear both a cap and a badge?",
                  sum(1 for p in range(1, n + 1) if p % 3 == 0 and (n - p + 1) % 4 == 0),
                  [(n // 12, "assumed both counts start from the same end"), (n // 3, "counted caps only"), (n // 4, "counted badges only")],
                  ["Cap: position p divisible by 3. Badge: (41 − p) divisible by 4.", "Enumerate p = 1 … 40 and count both conditions."]))
    # minimum number of persons in a queue with overlapping descriptions
    # "A is 5th from front, B is 6th from back, B is just behind A"
    s3 = [n for n in range(2, 40) if (n - 6 + 1) - 5 == 1]
    assert s3 == [11]
    items.append(("officer", "L3", "In a queue, A is 5th from the front and B is 6th from the back. B stands immediately behind A. How many persons are in the queue?", 10,
                  [(11, "added 1 for B twice"), (12, "counted both A and B again"), (9, "subtracted 2")],
                  ["B is 6th from front (just behind A at 5th) and 6th from back.", "Total = 6 + 6 − 1 = 11 → wait: B at 6th from front and 6th from back gives 11."]))
    # fix: compute cleanly
    items[-1] = ("officer", "L3", "In a queue, A is 5th from the front and B is 6th from the back. B stands immediately behind A. How many persons are in the queue?", 11,
                 [(10, "subtracted 1 twice"), (12, "did not subtract 1"), (13, "counted A and B separately on top")],
                 ["B is immediately behind A, so B is 6th from the front.", "B is also 6th from the back → total = 6 + 6 − 1 = 11 (enumeration confirms)."])
    # people between in circular? no — mixed ends
    s4 = possible(18, 18, 6)
    items.append(("officer", "L3", "In a line of children, Kavya is 18th from the front and Tara is 18th from the back. There are 6 children between them. What is the minimum number of children in the line?",
                  min(s4), [(max(s4), "assumed Kavya is ahead of Tara"), (35, "treated them as the same person"), (min(s4) + 1, "off by one")],
                  [f"Possible totals: {s4}.", f"Minimum = {min(s4)} (Tara ahead of Kavya)."]))
    # count of persons behind
    items.append(("officer", "L3", "In a row of 60 persons, X is 23rd from the left. Y is 11 places to the right of X. How many persons are to the right of Y?",
                  60 - 34, [(60 - 34 + 1, "counted Y"), (60 - 23, "ignored Y's move"), (34, "Y's position from left")],
                  ["Y is at 23 + 11 = 34 from left.", "Persons to the right of Y = 60 − 34 = 26."]))
    n, af, bb = 40, 12, 20
    bf = n - bb + 1
    items.append(("officer", "L2", f"In a queue of {n} persons, A is {af}th from the front and B is {bb}th from the back. How many persons stand between A and B?",
                  bf - af - 1, [(bf - af, "did not subtract 1"), (n - af - bb, "subtracted positions directly"), (bf - af + 1, "counted both")],
                  [f"B from the front = {n} − {bb} + 1 = {bf}.", f"Between = {bf} − {af} − 1 = {bf-af-1}."]))
    sols = []
    for n in range(2, 30):
        for so in range(1, n + 1):
            mo = so + 1
            if mo <= n and mo - 1 == 4 and n - so == 3:
                sols.append(n)
    assert sols == [7]
    items.append(("officer", "L3", "In a queue, there are 4 persons ahead of Mohan and 3 persons behind Sohan. Mohan stands immediately behind Sohan. How many persons are in the queue?",
                  7, [(9, "added the two counts plus both persons"), (8, "counted one of them twice"), (6, "subtracted an extra person")],
                  ["Mohan is 5th from the front, so Sohan is 4th.", "3 persons behind Sohan → total = 4 + 3 = 7 (enumeration confirms)."]))
    for tier, lvl, stem, key, cands, steps in items:
        q(B, M_TOT, lvl, tier, stem, key, numd(key, cands), steps, "Enumerate the possible arrangements; total = left + right − 1",
          "When the order of two people is not stated, check both arrangements.")


def add_all(B):
    direction_relative(B); path_tracing(B); pythagoras(B); two_person(B); order_puzzles(B); positions(B); totals(B)
