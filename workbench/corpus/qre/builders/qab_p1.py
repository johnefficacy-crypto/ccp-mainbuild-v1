"""QRE-QA-B part 1: Algebra (identities, inequalities, linear equations, quadratic root comparison, word-condition systems)."""
from qab_common import *


def solve2(a1, b1, c1, a2, b2, c2):
    """a1 x + b1 y = c1 ; a2 x + b2 y = c2 (Fractions)."""
    d = F(a1 * b2 - a2 * b1)
    assert d != 0
    return F(c1 * b2 - c2 * b1) / d, F(a1 * c2 - a2 * c1) / d


def identities(B):
    M = "qa-algebraic-identities-and-factorisation-e8595f7a"
    # ---- foundation ----
    for lv, (s, p) in [("L1", (9, 20)), ("L1", (13, 40))]:
        k = s * s - 2 * p
        a, b = roots(1, -s, p)
        assert a * a + b * b == k
        q(B, M, lv, "foundation", f"If a + b = {s} and ab = {p}, then a² + b² equals:", k,
          [(s * s + 2 * p, "added 2ab instead of subtracting it"), (s * s - p, "subtracted ab once instead of 2ab"),
           (s * s - 4 * p, "used the (a − b)² identity")],
          ["a² + b² = (a + b)² − 2ab", f"= {s}² − 2 × {p} = {s*s} − {2*p} = {k}"],
          "a² + b² = (a + b)² − 2ab", "(a + b)² already contains 2ab; it must be removed, not added.")
    k0 = 6
    k = k0 * k0 - 2
    q(B, M, "L2", "foundation", f"If x + 1/x = {k0}, then x² + 1/x² equals:", k,
      [(k0 * k0 + 2, "added 2 instead of subtracting"), (k0 * k0, "squared without removing the cross term"),
       (k0 * k0 - 1, "cross term taken as 1 instead of 2")],
      [f"(x + 1/x)² = x² + 1/x² + 2", f"x² + 1/x² = {k0}² − 2 = {k}"],
      "x² + 1/x² = (x + 1/x)² − 2", "The cross term 2·x·(1/x) = 2 must be subtracted.")
    # factorise x² − 5x − 24
    a, b = 8, -3   # (x − 8)(x + 3)
    q(B, M, "L2", "foundation", "The factors of x² − 5x − 24 are:", "(x − 8)(x + 3)",
      [("(x + 8)(x − 3)", "signs of the factors interchanged (gives +5x)"), ("(x − 6)(x + 4)", "product −24 but sum −2, not −5"),
       ("(x − 12)(x + 2)", "product −24 but sum −10, not −5")],
      ["Need two numbers with product −24 and sum −5.", "−8 and +3 work: (−8)(3) = −24, −8 + 3 = −5.",
       "So x² − 5x − 24 = (x − 8)(x + 3)."],
      "x² + (p + q)x + pq = (x + p)(x + q)", "Check both the product and the sum; the sign of the larger number follows the middle term.",
      kind="conceptual")
    m = 997
    k = m * (2000 - m)
    assert k == 1000000 - 9
    q(B, M, "L2", "foundation", f"Using an identity, the value of {m} × {2000-m} is:", k,
      [(1000000 + 9, "added the square of the difference"), (1000000 - 6, "subtracted 2 × 3 instead of 3²"),
       (1000000 - 3, "subtracted 3 instead of 3²")],
      [f"{m} × {2000-m} = (1000 − 3)(1000 + 3)", "= 1000² − 3² = 10,00,000 − 9 = 9,99,991"],
      "(a − b)(a + b) = a² − b²", "The correction term is b², not b or 2b.")
    # ---- officer ----
    k0 = 5
    k = k0 ** 3 - 3 * k0
    q(B, M, "L2", "officer", f"If x + 1/x = {k0}, then x³ + 1/x³ equals:", k,
      [(k0 ** 3 + 3 * k0, "added 3(x + 1/x) instead of subtracting"), (k0 ** 3 - 3, "subtracted 3 instead of 3(x + 1/x)"),
       (k0 ** 3 - k0, "coefficient 3 missed")],
      ["(x + 1/x)³ = x³ + 1/x³ + 3(x + 1/x)", f"x³ + 1/x³ = {k0}³ − 3 × {k0} = {k0**3} − {3*k0} = {k}"],
      "a³ + b³ = (a + b)³ − 3ab(a + b)", "Here ab = x·(1/x) = 1, so the subtracted term is 3(x + 1/x).")
    k0 = 3
    t = k0 * k0 + 2
    k = t * t - 2
    q(B, M, "L3", "officer", f"If x − 1/x = {k0}, then x⁴ + 1/x⁴ equals:", k,
      [((k0 * k0 - 2) ** 2 - 2, "used x² + 1/x² = (x − 1/x)² − 2 (wrong sign)"), (t * t, "did not subtract 2 at the second squaring"),
       (t * t + 2, "added 2 at the second squaring")],
      [f"x² + 1/x² = (x − 1/x)² + 2 = {k0*k0} + 2 = {t}", f"x⁴ + 1/x⁴ = (x² + 1/x²)² − 2 = {t}² − 2 = {k}"],
      "(x − 1/x)² = x² + 1/x² − 2", "With x − 1/x the correction is +2 at the first step and −2 at the second.")
    s, qq = 12, 47
    k = s * s - 2 * qq
    q(B, M, "L2", "officer", f"If a + b + c = {s} and ab + bc + ca = {qq}, then a² + b² + c² equals:", k,
      [(s * s + 2 * qq, "added 2(ab + bc + ca)"), (s * s - qq, "subtracted the pair-sum only once"), (s * s // 3, "assumed a = b = c")],
      ["(a + b + c)² = a² + b² + c² + 2(ab + bc + ca)", f"a² + b² + c² = {s*s} − 2 × {qq} = {k}"],
      "(a + b + c)² = Σa² + 2Σab", "The pair-sum appears twice in the square of a trinomial.")
    s, qq = 10, 31
    k = s * (s * s - 3 * qq)
    q(B, M, "L3", "officer", f"If a + b + c = {s} and ab + bc + ca = {qq}, then a³ + b³ + c³ − 3abc equals:", k,
      [(s * (s * s - 2 * qq), "used a² + b² + c² in place of (Σa² − Σab)"),
       (s * (s * s - qq), "subtracted Σab once from (Σa)²"), (s ** 3 - 3 * qq, "applied the two-variable cube identity")],
      [f"a² + b² + c² = {s}² − 2 × {qq} = {s*s-2*qq}", f"a² + b² + c² − (ab + bc + ca) = {s*s-2*qq} − {qq} = {s*s-3*qq}",
       f"a³ + b³ + c³ − 3abc = (a + b + c)(Σa² − Σab) = {s} × {s*s-3*qq} = {k}"],
      "a³ + b³ + c³ − 3abc = (a + b + c)[(a + b + c)² − 3(ab + bc + ca)]",
      "The second factor is Σa² − Σab, i.e. (Σa)² − 3Σab, not Σa² alone.")
    x, y, z = 17, 11, 5
    num = (x - y) ** 3 + (y - z) ** 3 + (z - x) ** 3
    den = 3 * (x - y) * (y - z) * (z - x)
    k = F(num, den)
    assert k == 1
    q(B, M, "L3", "officer",
      f"If x = {x}, y = {y} and z = {z}, the value of [(x − y)³ + (y − z)³ + (z − x)³] ÷ [3(x − y)(y − z)(z − x)] is:", k,
      [(3, "forgot the factor 3 already present in the denominator"), (0, "assumed the numerator vanishes because the terms sum to 0"),
       (F(1, 3), "divided by 3 twice")],
      ["Let a = x − y, b = y − z, c = z − x; then a + b + c = 0.", "When a + b + c = 0, a³ + b³ + c³ = 3abc.",
       "So the expression = 3abc ÷ 3abc = 1 (no need to substitute)."],
      "a + b + c = 0 ⇒ a³ + b³ + c³ = 3abc", "It is the sum a + b + c that is 0, not the sum of cubes.", fmt=fr)
    for lv, (a, bb) in [("L3", (2, 3)), ("L3", (3, 8))]:
        assert a * a - bb == 1
        k = (2 * a) ** 2 - 2
        xv = a + math.sqrt(bb)
        assert abs(xv ** 2 + xv ** -2 - k) < 1e-9
        q(B, M, lv, "officer", f"If x = {a} + √{bb}, then x² + 1/x² equals:", k,
          [((2 * a) ** 2, "did not subtract 2"), ((2 * a) ** 2 + 2, "added 2 instead of subtracting"),
           (2 * (a * a + bb) - 2, "took x + 1/x as a² + b instead of 2a")],
          [f"1/x = 1/({a} + √{bb}) = {a} − √{bb} (since {a}² − {bb} = 1)", f"x + 1/x = {2*a}",
           f"x² + 1/x² = {2*a}² − 2 = {k}"],
          "Rationalise, then x² + 1/x² = (x + 1/x)² − 2", "Rationalising is possible only because a² − b = 1; check it first.")
    # remainder / factor theorem: p(x) = 2x³ − 5x² + kx − 12, factor (x − 3)
    P = lambda x, kc, c5=-5, c0=-12: 2 * x ** 3 + c5 * x ** 2 + kc * x + c0
    solk = lambda f: [kc for kc in range(-60, 61) if f(kc) == 0]
    kk, = solk(lambda kc: P(3, kc))
    w1, = solk(lambda kc: P(-3, kc))
    w2, = solk(lambda kc: P(3, kc, c0=0))
    w3, = solk(lambda kc: P(3, kc, c5=5))
    q(B, M, "L2", "officer", "If (x − 3) is a factor of 2x³ − 5x² + kx − 12, the value of k is:", kk,
      [(w1, "substituted x = −3 (sign of the factor)"), (w2, "dropped the constant term"),
       (w3, "took −5x² as +5x² in the substitution")],
      ["Factor theorem: p(3) = 0.", "2 × 27 − 5 × 9 + 3k − 12 = 0",
       f"54 − 45 − 12 + 3k = 0 ⇒ 3k = 3 ⇒ k = {kk}"] if kk == 1 else None,
      "Factor theorem: (x − a) is a factor ⇔ p(a) = 0", "Substitute x = +3 for the factor (x − 3).")
    s, p = 8, 12
    k = F(s * s - 2 * p, p)
    q(B, M, "L2", "officer", f"If a + b = {s} and ab = {p}, the value of a/b + b/a is:", k,
      [(F(s * s, p), "used (a + b)² in place of a² + b²"), (F(s * s + 2 * p, p), "added 2ab"), (F(s, p), "added the reciprocals of a and b")],
      ["a/b + b/a = (a² + b²)/ab", f"a² + b² = {s*s} − {2*p} = {s*s-2*p}", f"a/b + b/a = {s*s-2*p}/{p} = {fr(k)}"],
      "a/b + b/a = [(a + b)² − 2ab]/ab", "Convert to a single fraction before substituting.", fmt=fr)
    q(B, M, "L3", "officer", "If a² + b² + c² = ab + bc + ca for real a, b, c (c ≠ 0), then (a + b)/c equals:", 2,
      [(1, "took a + b = c"), (0, "assumed a = −b"), (3, "counted all three variables in the numerator")],
      ["2(a² + b² + c² − ab − bc − ca) = (a − b)² + (b − c)² + (c − a)² = 0",
       "Each square is 0 ⇒ a = b = c.", "(a + b)/c = 2c/c = 2"],
      "Σa² − Σab = ½[(a − b)² + (b − c)² + (c − a)²]", "A sum of real squares is zero only if each square is zero.")


def inequalities(B):
    M = "qa-inequalities-and-relationship-determination-a6a6a638"
    # ---- foundation ----
    lo, a, b, hi = -5, 2, 3, 11          # −5 ≤ 2x + 3 < 11
    xs = [x for x in range(-50, 50) if lo <= a * x + b < hi]
    k = len(xs)
    q(B, M, "L1", "foundation", f"How many integers x satisfy {lo} ≤ {a}x + {b} < {hi}?", k,
      [(len([x for x in range(-50, 50) if lo <= a * x + b <= hi]), "included the upper end point"),
       (len([x for x in range(-50, 50) if lo < a * x + b < hi]), "excluded the lower end point"),
       (hi - lo, "counted the width of the range of 2x + 3"), (k + 2, "counted both end points of x twice")],
      [f"Subtract {b}: {lo-b} ≤ {a}x < {hi-b}", f"Divide by {a}: {F(lo-b,a)} ≤ x < {F(hi-b,a)}",
       f"Integers: {xs[0]} to {xs[-1]} ⇒ {k} integers"],
      "Solve as a linear inequality, then count integers", "Watch the strict (<) end: 4 itself is excluded.")
    k = 9   # 5x − 7 > 3x + 9  ⇒ x > 8
    assert min(x for x in range(-50, 50) if 5 * x - 7 > 3 * x + 9) == k
    q(B, M, "L1", "foundation", "The smallest integer x satisfying 5x − 7 > 3x + 9 is:", k,
      [(8, "treated > as ≥"), (-8, "sign error while transposing"), (16, "did not divide by 2")],
      ["5x − 3x > 9 + 7 ⇒ 2x > 16 ⇒ x > 8", "Smallest integer greater than 8 is 9."],
      "Transpose, then divide by the (positive) coefficient", "Strict inequality: x = 8 does not satisfy it.")
    k = -5   # −3x + 4 ≤ 19 ⇒ x ≥ −5
    assert min(x for x in range(-50, 50) if -3 * x + 4 <= 19) == k
    q(B, M, "L2", "foundation", "The least integer value of x for which −3x + 4 ≤ 19 is:", k,
      [(5, "did not reverse the inequality when dividing by −3"), (-4, "treated ≤ as strict"),
       (-6, "moved 4 to the wrong side (−3x ≤ 23 style slip)")],
      ["−3x ≤ 15", "Dividing by −3 reverses the sign: x ≥ −5", "Least integer = −5"],
      "Dividing by a negative number reverses the inequality", "Forgetting to flip the sign gives x ≤ −5, which has no least value.")
    fr_ = [F(5, 7), F(7, 10), F(9, 13), F(11, 16)]
    k = max(fr_)
    q(B, M, "L2", "foundation", "Which of the following fractions is the largest: 5/7, 7/10, 9/13, 11/16?", k,
      [(F(11, 16), "picked the fraction with the largest numerator"), (F(9, 13), "compared only the gap between numerator and denominator"),
       (F(7, 10), "compared numerators only after rounding"), (min(fr_), "picked the smallest")],
      ["Decimals: 5/7 ≈ 0.714, 7/10 = 0.700, 9/13 ≈ 0.692, 11/16 = 0.6875", "Largest = 5/7"],
      "Compare by cross-multiplication or decimals", "A bigger numerator does not mean a bigger fraction.", fmt=fr)
    xs = [x for x in range(-50, 50) if abs(x - 3) <= 4]
    k = len(xs)
    q(B, M, "L2", "foundation", "How many integers satisfy |x − 3| ≤ 4?", k,
      [(k - 1, "excluded one end point"), (k - 2, "treated ≤ as <"), (5, "counted only the non-negative side of the modulus")],
      ["|x − 3| ≤ 4 ⇔ −4 ≤ x − 3 ≤ 4 ⇔ −1 ≤ x ≤ 7", f"Integers −1 to 7 ⇒ {k}"],
      "|x − a| ≤ b ⇔ a − b ≤ x ≤ a + b", "The count from −1 to 7 inclusive is 9, not 8.")
    # ---- officer ----
    for lv, (a_, b_, c_, strict) in [("L2", (1, -7, 10, True)), ("L3", (1, -1, -12, False))]:
        f = (lambda x: a_ * x * x + b_ * x + c_ < 0) if strict else (lambda x: a_ * x * x + b_ * x + c_ <= 0)
        xs = [x for x in range(-50, 50) if f(x)]
        k = len(xs)
        r1, r2 = roots(a_, b_, c_)
        incl = len([x for x in range(-50, 50) if a_ * x * x + b_ * x + c_ <= 0])
        excl = len([x for x in range(-50, 50) if a_ * x * x + b_ * x + c_ < 0])
        outside = "all integers outside the roots (infinitely many)"
        sign = "<" if strict else "≤"
        q(B, M, lv, "officer", f"The number of integer values of x satisfying {poly(a_, b_, c_)[:-4]} {sign} 0 is:", k,
          [(incl if strict else excl, "mishandled the end points (strict vs non-strict)"),
           (int(r2 - r1), "took the difference of the roots as the count"), (k + 1, "counted an extra end point"),
           (outside, "took the solution outside the roots")],
          [f"Roots: {fr(r1)} and {fr(r2)}", f"Expression {sign} 0 between the roots: {fr(r1)} {sign} x {sign} {fr(r2)}",
           f"Integers: {xs} ⇒ {k}"],
          "For a > 0, ax² + bx + c < 0 between the roots", "Check whether the roots themselves are included.")
    X = (-1, 4); Y = (-2, 3)
    vals = [2 * x - 3 * y for x in X for y in Y]
    k = max(vals)
    q(B, M, "L3", "officer", "If −1 ≤ x ≤ 4 and −2 ≤ y ≤ 3, the maximum value of 2x − 3y is:", k,
      [(2 * 4 - 3 * 3, "used the maximum of y as well"), (min(vals), "gave the minimum value"),
       (2 * 4 + 3 * 3, "ignored the minus sign on 3y"), (2 * 4 - 3 * 0, "took y = 0 as the optimum")],
      ["2x − 3y is increasing in x and decreasing in y.", "Max at x = 4, y = −2: 8 + 6 = 14"],
      "Linear expression: extreme values occur at the corners", "To maximise −3y, take y at its minimum.")
    X = (-2, 3); Y = (-4, 1)
    vals = [x * y for x in X for y in Y]
    k = max(vals)
    q(B, M, "L3", "officer", "If −2 ≤ x ≤ 3 and −4 ≤ y ≤ 1, the greatest possible value of xy is:", k,
      [(3 * 1, "multiplied the two upper limits"), (3 * 4, "multiplied the largest magnitudes with sign ignored (x = 3, y = −4)"),
       (min(vals), "took the most negative product"), (0, "assumed the product is largest at zero")],
      ["Check the four corner products: (−2)(−4) = 8, (−2)(1) = −2, (3)(−4) = −12, (3)(1) = 3", "Greatest = 8"],
      "For a product over intervals test all four corner products", "Two negatives give the largest positive product here.")
    # quantity comparisons
    items = [
        ("L2", "Quantity I: x, where 3x/4 − 5 = x/2 + 1\n\nQuantity II: y, where 2y + 3(y − 4) = 98",
         [24], [22], ["3x/4 − x/2 = 6 ⇒ x/4 = 6 ⇒ x = 24", "5y − 12 = 98 ⇒ y = 22", "24 > 22 ⇒ I > II"]),
        ("L3", "Quantity I: x, where x² − 10x + 24 = 0\n\nQuantity II: 5",
         roots(1, -10, 24), [5], ["x² − 10x + 24 = (x − 4)(x − 6) ⇒ x = 4 or 6", "4 < 5 but 6 > 5", "No single relation holds"]),
        ("L3", "Quantity I: a² + b², where a + b = 10 and ab = 21\n\nQuantity II: a² + b², where a − b = 4 and ab = 21",
         [100 - 42], [16 + 42], ["I: (a + b)² − 2ab = 100 − 42 = 58", "II: (a − b)² + 2ab = 16 + 42 = 58", "I = II"]),
        ("L3", "Quantity I: x, where x² = 64\n\nQuantity II: y, where y = ∛512",
         [-8, 8], [8], ["x = ±8", "y = 8", "−8 < 8 and 8 = 8 ⇒ I ≤ II"]),
        ("L3", "Quantity I: the largest of three consecutive integers whose sum is 72\n\nQuantity II: the smallest of three consecutive even integers whose sum is 78",
         [25], [24], ["Integers 23, 24, 25 ⇒ largest 25", "Even integers 24, 26, 28 ⇒ smallest 24", "25 > 24 ⇒ I > II"]),
        ("L3", "Quantity I: 2x + y, where x + y = 11 and x − y = 3\n\nQuantity II: xy, where x + y = 11 and x − y = 3",
         [18], [28], ["x = 7, y = 4", "I = 2(7) + 4 = 18; II = 7 × 4 = 28", "18 < 28 ⇒ I < II"]),
    ]
    for lv, body, X, Y, st in items:
        key, wr = rel_wrongs(X, Y, QREL)
        wr = [(t, "sign slip in solving" if "sign" in e else ("compared only one root" if "roots" in e else "misread the comparison (strict vs inclusive)")) for t, e in wr]
        q(B, M, lv, "officer", body + "\n\nCompare Quantity I and Quantity II.", key, wr, st,
          "Evaluate each quantity completely, then compare every possible value",
          "When a quantity has two values, the relation must hold for both.", kind="conceptual")
    # verify computed values used above
    assert roots(1, -10, 24) == [4, 6]


def linear(B):
    M = "qa-linear-equations-in-one-and-two-variables-dbd6b335"
    # ---- foundation ----
    x = F(11 + 15 - 8, 3)   # 5(x − 3) − 2(x − 4) = 11 ⇒ 3x − 7 = 11
    assert 5 * (x - 3) - 2 * (x - 4) == 11
    q(B, M, "L1", "foundation", "Solve: 5(x − 3) − 2(x − 4) = 11", x,
      [(F(11 + 15 + 8, 3), "expanded −2(x − 4) as −2x − 8"), (F(11 + 15 - 8, 7), "added the x-coefficients (5 + 2)"),
       (F(11 - 7, 3), "moved −7 to the right with the wrong sign")],
      ["5x − 15 − 2x + 8 = 11", "3x − 7 = 11 ⇒ 3x = 18 ⇒ x = 6"],
      "Expand, collect like terms, isolate x", "(−2)(−4) = +8.", fmt=fr)
    x = F(14 * 12, 7)
    assert x / 3 + x / 4 == 14
    q(B, M, "L1", "foundation", "If x/3 + x/4 = 14, then x equals:", x,
      [(F(14 * 7, 12), "multiplied by 7/12 instead of dividing"), (F(14 * 7, 2), "added numerators and denominators (x/3 + x/4 = 2x/7)"),
       (14 * 7, "took the LCM as 7")],
      ["x/3 + x/4 = 7x/12", "7x/12 = 14 ⇒ x = 14 × 12/7 = 24"],
      "Combine with LCM of denominators", "The combined fraction is 7x/12, not 2x/7.", fmt=fr)
    xx, yy = solve2(2, 3, 23, 1, -1, -1)
    assert (xx, yy) == (4, 5)
    q(B, M, "L2", "foundation", "If 2x + 3y = 23 and x − y = −1, the value of xy is:", xx * yy,
      [(xx + yy, "gave x + y"), ((lambda a: a[0] * a[1])(solve2(2, 3, 23, 1, -1, 1)), "took x − y = +1"),
       (xx * xx + yy * yy, "gave x² + y²")],
      ["From x − y = −1: x = y − 1", "2(y − 1) + 3y = 23 ⇒ 5y = 25 ⇒ y = 5, x = 4", "xy = 20"],
      "Substitution method", "x − y = −1 means y is the larger value.")
    q(B, M, "L1", "foundation", "When 7 is added to a number and the sum is tripled, the result is 60. The number is:", 13,
      [(27, "reversed the operations in the wrong order (60 ÷ 3 + 7)"), (20, "ignored the addition of 7"),
       (F(53, 3), "subtracted 7 before dividing by 3")],
      ["3(x + 7) = 60 ⇒ x + 7 = 20 ⇒ x = 13"],
      "Undo operations in reverse order", "Divide by 3 first, then subtract 7.", fmt=lambda v: n(v))
    q(B, M, "L2", "foundation", "The sum of two numbers is 50 and their difference is 12. The larger number is:", 31,
      [(19, "gave the smaller number"), (38, "added 50 and 12 without halving"), (25, "ignored the difference")],
      ["x + y = 50, x − y = 12", "2x = 62 ⇒ x = 31"],
      "Larger = (sum + difference)/2", "Half of (sum + difference), not sum − difference.")
    # ---- officer ----
    q(B, M, "L2", "officer", "For what value of k do the equations kx + 3y = 5 and 6x + 9y = 11 have no solution?", 2,
      [(18, "inverted the ratio (6 × 9 ÷ 3)"), (F(30, 11), "equated k/6 with 5/11"), (F(66, 5), "equated k/6 with 11/5 (constants inverted)")],
      ["No solution ⇔ a₁/a₂ = b₁/b₂ ≠ c₁/c₂", "k/6 = 3/9 ⇒ k = 2", "Check: 3/9 = 1/3 ≠ 5/11 ✓"],
      "Parallel lines: a₁/a₂ = b₁/b₂ ≠ c₁/c₂", "Also check the constants' ratio differs; otherwise the lines coincide.", fmt=fr)
    ks = [kc for kc in range(-20, 21) if F(kc - 1, 2) == F(kc + 2, 3) == F(3 * kc, 7)]
    assert ks == [7]
    q(B, M, "L3", "officer",
      "For what value of k does the system 2x + 3y = 7 and (k − 1)x + (k + 2)y = 3k have infinitely many solutions?", 7,
      [(1, "used (k + 1) for (k − 1): 3(k + 1) = 2(k + 2)"), (5, "expanded 2(k + 2) as 2k + 2"),
       (-7, "sign slip while transposing (k = −7)")],
      ["Infinite solutions ⇔ 2/(k − 1) = 3/(k + 2) = 7/(3k)", "2(k + 2) = 3(k − 1) ⇒ k = 7",
       "Check 7/(3k) = 7/21 = 1/3 and 2/6 = 1/3 ✓"],
      "Coincident lines: a₁/a₂ = b₁/b₂ = c₁/c₂", "Verify the third ratio as well.", fmt=fr)
    xs = [x for x in range(-50, 51) if x != 1 and (2 * x + 3) == 3 * (x - 1)]
    assert xs == [6]
    q(B, M, "L2", "officer", "Solve for x: (2x + 3)/(x − 1) = 3", 6,
      [(0, "cleared the denominator on one side only (2x + 3 = 3)"), (4, "wrote 3(x − 1) as 3x − 1"),
       (-6, "sign slip while transposing")],
      ["2x + 3 = 3(x − 1) = 3x − 3", "x = 6 (and x ≠ 1 ✓)"],
      "Cross-multiply, excluding values that make a denominator zero", "Distribute 3 over both terms of (x − 1).")
    x = F(2 + 2 + 3) / (F(3, 2) - 1)
    assert F(1, 2) * (3 * x - 4) == F(1, 5) * (5 * x + 10) + 3
    q(B, M, "L2", "officer", "Solve: 0.5(3x − 4) = 0.2(5x + 10) + 3", x,
      [(F(5 - 2) / F(1, 2), "sign slip on the constant −2"), (F(7) / F(5, 2), "added x-terms instead of subtracting"),
       (F(7), "stopped at 0.5x = 7 without dividing by 0.5")],
      ["1.5x − 2 = x + 2 + 3", "0.5x = 7 ⇒ x = 14"],
      "Clear decimals, collect terms", "0.2 × 10 = 2, not 0.2.", fmt=fr)
    u, v = solve2(2, 3, 13, 5, -4, -2)
    assert (u, v) == (2, 3)
    k = 1 / u + 1 / v
    q(B, M, "L3", "officer", "If 2/x + 3/y = 13 and 5/x − 4/y = −2, then x + y equals:", k,
      [(u + v, "reported 1/x + 1/y (forgot to invert)"), (F(1, u + v), "inverted the sum instead of each term"),
       (1 / u * 1 / v, "multiplied instead of adding")],
      ["Let u = 1/x, v = 1/y: 2u + 3v = 13, 5u − 4v = −2", "u = 2, v = 3 ⇒ x = 1/2, y = 1/3", "x + y = 5/6"],
      "Substitute reciprocals to linearise", "Solve for u, v, then invert each.", fmt=fr)
    xx, yy = solve2(47, 31, 63, 31, 47, 15)
    assert (xx, yy) == (2, -1)
    q(B, M, "L3", "officer", "If 47x + 31y = 63 and 31x + 47y = 15, then x² + y² equals:", xx * xx + yy * yy,
      [((xx + yy) ** 2, "took (x + y)²"), ((xx - yy) ** 2, "took (x − y)²"), (xx * xx - yy * yy, "took x² − y²")],
      ["Add: 78(x + y) = 78 ⇒ x + y = 1", "Subtract: 16(x − y) = 48 ⇒ x − y = 3", "x = 2, y = −1 ⇒ x² + y² = 5"],
      "Symmetric coefficients: add and subtract the equations", "y is negative; its square is still +1.")
    q(B, M, "L3", "officer", "The system 3x + ky = 7 and 6x + 10y = 14 has a unique solution when:", "k ≠ 5",
      [("k = 5", "k = 5 gives coincident lines (infinitely many solutions)"), ("k ≠ 2", "compared k with 6/3"),
       ("for no value of k", "assumed proportional constants force dependence")],
      ["Unique solution ⇔ a₁/a₂ ≠ b₁/b₂", "3/6 ≠ k/10 ⇔ k ≠ 5"],
      "Unique ⇔ a₁/a₂ ≠ b₁/b₂", "c₁/c₂ plays no role for uniqueness.", kind="conceptual")
    a_, b_ = 24 // 3, 24 // 4
    q(B, M, "L2", "officer", "The area (in square units) of the triangle formed by the line 3x + 4y = 24 and the coordinate axes is:",
      a_ * b_ // 2, [(a_ * b_, "forgot the factor ½"), (a_ + b_, "added the intercepts"), (10, "used the hypotenuse length")],
      ["x-intercept = 8, y-intercept = 6", "Area = ½ × 8 × 6 = 24"],
      "Area = ½ × |x-intercept| × |y-intercept|", "It is a right triangle with legs equal to the intercepts.")
    a_s = [a for a in range(-20, 21) if 3 * 2 + a * (-1) == 8]
    b_s = [b for b in range(-20, 21) if b * 2 - 2 * (-1) == 12]
    assert a_s == [-2] and b_s == [5]
    q(B, M, "L2", "officer", "If x = 2 and y = −1 satisfy both 3x + ay = 8 and bx − 2y = 12, then a + b equals:", a_s[0] + b_s[0],
      [(2 + 5, "took a = +2 (sign of y ignored)"), (-2 + 7, "took −2y as −2 when y = −1"), (a_s[0] * b_s[0], "multiplied a and b")],
      ["3(2) + a(−1) = 8 ⇒ 6 − a = 8 ⇒ a = −2", "b(2) − 2(−1) = 12 ⇒ 2b + 2 = 12 ⇒ b = 5", "a + b = 3"],
      "Substitute the given solution into each equation", "y is negative: a·y = −a and −2y = +2.")
    inc = 9000 / (F(2, 3) * F(3, 4))
    assert inc == 18000
    q(B, M, "L3", "officer",
      "A person spends 1/3 of his income on rent and 1/4 of the remainder on food. He saves the balance of ₹9,000. His income is:",
      inc, [(9000 / (1 - F(1, 3) - F(1, 4)), "took 1/4 of the total income for food"), (9000 * 3, "ignored the food expense"),
            (9000 / (F(2, 3) * F(1, 4)), "treated the savings as the 1/4 share of the remainder")],
      ["After rent: 2/3 of income", "After food: 3/4 × 2/3 = 1/2 of income", "Income = 9,000 × 2 = ₹18,000"],
      "Remaining share = Π(1 − fraction of remainder)", "'Of the remainder' compounds; do not subtract from the total.",
      fmt=lambda v: R(v))


def quad_compare(B):
    M = "qa-quadratic-equations-root-comparison-x-vs-y-03936368"
    items = [
        ("foundation", "L1", (5, 6), (6, 7)), ("foundation", "L1", (-3, -4), (-1, -2)),
        ("foundation", "L2", (4, 9), (2, 3)), ("foundation", "L2", (3, 5), (4, 6)),
        ("foundation", "L2", (-2, -5), (2, 3)),
        ("officer", "L2", (F(5, 2), 3), (3, F(5, 3))), ("officer", "L3", (F(1, 2), F(2, 3)), (F(1, 3), F(1, 4))),
        ("officer", "L3", (F(-7, 2), -3), (-2, F(-4, 3))), ("officer", "L3", (F(5, 2), F(5, 2)), (2, F(5, 2))),
        ("officer", "L3", (F(1, 3), F(1, 5)), (F(1, 4), F(1, 5))), ("officer", "L3", (F(4, 3), -3), (-2, -3)),
        ("officer", "L3", (F(1, 2), F(1, 5)), (F(1, 5), F(1, 7))),
    ]
    for tier, lv, rx, ry in items:
        ax, bx, cx = quad_from_roots(*rx)
        ay, by, cy = quad_from_roots(*ry)
        X, Y = roots(ax, bx, cx), roots(ay, by, cy)
        assert set(X) == set(map(F, rx)) and set(Y) == set(map(F, ry))
        key, wr = rel_wrongs(X, Y)
        q(B, M, lv, tier, f"I. {poly(ax, bx, cx, 'x')}\n\nII. {poly(ay, by, cy, 'y')}\n\nFind the relation between x and y.", key, wr,
          [f"I: roots x = {', '.join(fr(r) for r in X)}", f"II: roots y = {', '.join(fr(r) for r in Y)}",
           "Compare every x with every y: " + "; ".join(f"{fr(a)} vs {fr(b)}" for a in X for b in Y), f"Relation: {key}"],
          "Roots of ax² + bx + c = 0 by factorisation (sum = −b/a, product = c/a)",
          "A relation holds only if it is true for all four (x, y) pairs.", kind="conceptual")
    # special forms
    specials = [
        ("officer", "L2", "I. x² = 81\n\nII. y² − 18y + 81 = 0", [-9, 9], [9], ["x = ±9", "y = 9 (repeated root)"]),
        ("officer", "L3", "I. x³ = 343\n\nII. y² = 49", [7], [-7, 7], ["x = 7 (only real cube root)", "y = ±7"]),
        ("officer", "L3", "I. x = √1296\n\nII. y² = 1296", [36], [-36, 36], ["x = 36 (principal square root is non-negative)", "y = ±36"]),
    ]
    for tier, lv, body, X, Y, st in specials:
        key, wr = rel_wrongs(X, Y)
        q(B, M, lv, tier, body + "\n\nFind the relation between x and y.", key, wr,
          st + ["Compare every x with every y", f"Relation: {key}"],
          "x² = a gives ±√a; √a denotes the non-negative root; x³ = a has one real root",
          "√ gives only the positive root, while solving x² = a gives two roots.", kind="conceptual")


def word_systems(B):
    M = "qa-simultaneous-equations-from-word-conditions-29e84158"
    # ---- foundation ----
    a_, c_, N, T = 100, 60, 50, 4200
    ad, ch = solve2(1, 1, N, a_, c_, T)
    assert ad.denominator == 1 and ad > 0 and ch > 0
    q(B, M, "L1", "foundation", f"A show sold {N} tickets: adult tickets at ₹{a_} and child tickets at ₹{c_}. Total collection was ₹{inr(T)}. How many child tickets were sold?",
      ch, [(ad, "gave the number of adult tickets"), (F(a_ * N - T, a_), "divided the shortfall by the adult price instead of the price gap"),
           (F(T - c_ * N, a_), "divided the excess over child fares by the adult price")],
      [f"a + c = {N}; {a_}a + {c_}c = {inr(T)}", f"{a_}({N} − c) + {c_}c = {T} ⇒ {a_*N} − {a_-c_}c = {T}",
       f"c = {a_*N - T}/{a_-c_} = {ch}"],
      "Two equations: count and value", "Check which unknown the question asks for.", fmt=lambda v: n(v, 1))
    A, Bv = 110, 115
    pp, nb = solve2(3, 2, A, 2, 3, Bv)
    k = pp + nb
    assert k == F(A + Bv, 5)
    q(B, M, "L2", "foundation", f"3 pens and 2 notebooks cost ₹{A}; 2 pens and 3 notebooks cost ₹{Bv}. The cost of 1 pen and 1 notebook together is:",
      k, [("₹112.50", "halved the combined total instead of dividing by 5"), (Bv - A, "subtracted the two totals"), (nb, "gave the price of a notebook only")],
      ["Add the equations: 5p + 5n = 225", "p + n = 45"],
      "Add equations with swapped coefficients", "Adding gives 5(p + n); divide by 5.", fmt=lambda v: R(v))
    q(B, M, "L1", "foundation", "The sum of the ages of a father and his son is 60 years, and the father is 4 times as old as the son. The father's age is:",
      48, [(12, "gave the son's age"), (40, "took the father as 2/3 of the sum"), (45, "took the ratio as 3 : 1")],
      ["s + 4s = 60 ⇒ s = 12", "Father = 48"], "Ratio split of a sum", "The father is 4 of 5 parts.", unit=" years")
    c5, c2 = solve2(1, 1, 30, 5, 2, 111)
    assert c5 == 17
    q(B, M, "L2", "foundation", "A bag has 30 coins, all of ₹5 and ₹2, worth ₹111 in all. How many ₹5 coins are there?", c5,
      [(c2, "gave the number of ₹2 coins"), (F(111, 7), "divided the value by (5 + 2)"), (F(111 - 60, 5), "divided (111 − 2 × 30) by 5 instead of by 3")],
      ["x + y = 30; 5x + 2y = 111", "5x + 2(30 − x) = 111 ⇒ 3x = 51 ⇒ x = 17"],
      "Count equation + value equation", "Replace one unknown using the count equation.", fmt=lambda v: n(v, 1))
    c, w = solve2(1, 1, 60, 4, -1, 150)
    assert c == 42
    q(B, M, "L2", "foundation", "In a test, each correct answer gets +4 and each wrong answer −1. A candidate attempted all 60 questions and scored 150. The number of correct answers is:",
      c, [(w, "gave the number of wrong answers"), (F(150, 4), "ignored the negative marking"), (F(150, 5), "divided the score by 5 without adding back the 60 penalty marks")],
      ["c + w = 60; 4c − w = 150", "5c = 210 ⇒ c = 42"], "Add the two equations to eliminate w",
      "Negative marking reduces the score by 1 per wrong answer.", fmt=lambda v: n(v, 1))
    # ---- officer ----
    # 5 years ago A = 3B; 10 years hence A = 2B
    Aa, Bb = solve2(1, -3, 5 - 15, 1, -2, 20 - 10)
    assert (Aa, Bb) == (50, 20)
    q(B, M, "L2", "officer", "Five years ago, A was three times as old as B. Ten years from now, A will be twice as old as B. What will A's age be five years from now?",
      Aa + 5, [(Aa, "gave the present age"), (Bb + 5, "gave B's age"), (Aa - 5, "moved five years the wrong way")],
      ["A − 5 = 3(B − 5) ⇒ A − 3B = −10", "A + 10 = 2(B + 10) ⇒ A − 2B = 10", "B = 20, A = 50 ⇒ A in 5 years = 55"],
      "Translate each time-shifted condition into an equation", "Apply the time shift to both people.", unit=" years")
    U, D = 6, 14
    assert 24 / U + 28 / D == 6 and 30 / U + 21 / D == 6.5
    u, v = solve2(24, 28, F(6), 30, 21, F(13, 2))
    assert (1 / u, 1 / v) == (U, D)
    q(B, M, "L3", "officer", "A boat goes 24 km upstream and 28 km downstream in 6 hours. It goes 30 km upstream and 21 km downstream in 6 hours 30 minutes. The speed of the stream (km/h) is:",
      (D - U) // 2, [((D + U) // 2, "gave the speed of the boat in still water"), (D - U, "did not halve the difference"),
                     (U, "gave the upstream speed")],
      ["Let 1/(b − s) = u, 1/(b + s) = v: 24u + 28v = 6; 30u + 21v = 6.5", "u = 1/6, v = 1/14 ⇒ b − s = 6, b + s = 14",
       "Stream = (14 − 6)/2 = 4 km/h"],
      "Stream speed = (downstream − upstream)/2", "Solve for reciprocals of speeds first.", unit=" km/h")
    sols = [10 * a + b for a in range(1, 10) for b in range(10) if 10 * a + b == 4 * (a + b) and 10 * a + b + 18 == 10 * b + a]
    assert sols == [24]
    q(B, M, "L3", "officer", "A two-digit number is 4 times the sum of its digits. If 18 is added to the number, its digits are reversed. The number is:",
      24, [(42, "gave the reversed number"), (36, "used only the reversal condition (b − a = 2) with a different pair"), (12, "used only the 4 × sum condition")],
      ["10a + b = 4(a + b) ⇒ 2a = b", "Adding 18 reverses: 9(b − a) = 18 ⇒ b − a = 2", "a = 2, b = 4 ⇒ 24"],
      "Two-digit number = 10a + b", "Both conditions are needed; 12, 24, 36, 48 all satisfy the first.")
    m_, w_ = solve2(3, 4, 2280, 2, 5, 2220)
    assert m_.denominator == 1
    q(B, M, "L2", "officer", "3 men and 4 women together earn ₹2,280 a day; 2 men and 5 women earn ₹2,220 a day. The daily wage of one man is:",
      m_, [(w_, "gave a woman's wage"), (F(2280, 7), "averaged over 7 persons"), (F(2280 - 2220, 1), "subtracted the totals")],
      ["3m + 4w = 2280; 2m + 5w = 2220", f"Eliminate: m = {m_}, w = {w_}"], "Elimination", "Keep men and women as separate unknowns.",
      fmt=lambda v: R(v))
    x8 = (F(50000) * F(10, 100) - 4400) / (F(10, 100) - F(8, 100))
    assert x8 == 30000
    q(B, M, "L3", "officer", "₹50,000 is split into two parts, lent for one year at 8% and 10% simple interest. Total interest is ₹4,400. The amount lent at 8% is:",
      x8, [(50000 - x8, "gave the part at 10%"), (25000, "split equally"), ((F(5000) - 4400) / F(8, 100), "divided the shortfall by 8% instead of by the 2% rate gap")],
      ["0.08x + 0.10(50,000 − x) = 4,400", "5,000 − 0.02x = 4,400 ⇒ x = 30,000"],
      "Alligation or one-variable equation", "Check which part the question asks for.", fmt=lambda v: R(v))
    rate, fixed = solve2(10, 1, 175, 25, 1, 355)
    k = fixed + 18 * rate
    q(B, M, "L2", "officer", "A taxi charges a fixed amount plus a rate per km. A 10 km trip costs ₹175 and a 25 km trip costs ₹355. What does an 18 km trip cost?",
      k, [(F(175, 10) * 18, "assumed no fixed charge"), (18 * rate, "left out the fixed charge"), (F(175 + 355, 2), "averaged the two fares")],
      ["10r + f = 175, 25r + f = 355 ⇒ r = 12, f = 55", "18 km: 55 + 216 = ₹271"],
      "Linear cost = fixed + rate × distance", "Proportional scaling ignores the fixed charge.", fmt=lambda v: R(v))
    ll, bb = solve2(-2, 3, 6, 1, -1, 4)
    assert (ll + 3) * (bb - 2) == ll * bb and (ll - 2) * (bb + 2) == ll * bb + 4
    q(B, M, "L3", "officer", "If the length of a rectangle is increased by 3 m and the breadth decreased by 2 m, the area is unchanged. If the length is decreased by 2 m and the breadth increased by 2 m, the area increases by 4 m². The perimeter of the rectangle is:",
      2 * (ll + bb), [(ll * bb, "gave the area"), (ll + bb, "forgot to double"), ((lambda t: 2 * (t[0] + t[1]))(solve2(-2, 3, -6, 1, -1, 4)), "wrote the first condition as −2l + 3b = −6 (sign slip)")],
      ["(l + 3)(b − 2) = lb ⇒ −2l + 3b = 6", "(l − 2)(b + 2) = lb + 4 ⇒ 2l − 2b = 8 ⇒ l − b = 4", f"b = {bb}, l = {ll} ⇒ perimeter = {2*(ll+bb)} m"],
      "Expand and cancel lb", "The lb terms cancel, leaving linear equations.", unit=" m")
    k_ = 100
    A_, B_ = solve2(1, -1, 2 * k_, 1, -2, -3 * k_)
    assert (A_, B_) == (700, 500)
    q(B, M, "L3", "officer", "If A gives ₹100 to B, both have equal amounts. If B gives ₹100 to A, A has twice as much as B. Together they have:",
      A_ + B_, [(A_, "gave A's amount"), ((lambda t: t[0] + t[1])(solve2(1, -1, k_, 1, -2, -3 * k_)), "took the gap A − B as ₹100 instead of ₹200"), (A_ + B_ - 200, "subtracted the transfers")],
      ["A − 100 = B + 100 ⇒ A − B = 200", "A + 100 = 2(B − 100) ⇒ A − 2B = −300", "B = 500, A = 700 ⇒ total ₹1,200"],
      "Two transfer conditions → two equations", "Equalising needs a gap of twice the transfer.", fmt=lambda v: R(v))
    nn, dd = solve2(5, -4, -1, 2, -1, 5)
    assert F(nn + 1, dd + 1) == F(4, 5) and F(nn - 5, dd - 5) == F(1, 2)
    q(B, M, "L3", "officer", "If 1 is added to both the numerator and the denominator of a fraction, it becomes 4/5. If 5 is subtracted from both, it becomes 1/2. The fraction is:",
      F(nn, dd), [(F(nn + 1, dd + 1), "reported the transformed fraction (n + 1)/(d + 1)"),
                  (F(nn - 5, dd - 5), "reported the transformed fraction (n − 5)/(d − 5)"),
                  (F(dd, nn), "inverted numerator and denominator")],
      ["(n + 1)/(d + 1) = 4/5 ⇒ 5n − 4d = −1", "(n − 5)/(d − 5) = 1/2 ⇒ 2n − d = 5", f"n = {nn}, d = {dd} ⇒ {nn}/{dd}"],
      "Form one equation per condition", "The fraction is n/d itself, not a transformed version.", fmt=lambda v: f"{v.numerator}/{v.denominator}" if isinstance(v, F) else str(v))
    ab, bc, ca = 50, 65, 55
    tot = F(ab + bc + ca, 2)
    Bn = tot - ca
    q(B, M, "L2", "officer", "Of three numbers A, B and C: A + B = 50, B + C = 65 and C + A = 55. The value of B is:",
      Bn, [(tot - bc, "gave A"), (tot - ab, "gave C"), (tot, "gave the total A + B + C")],
      ["Adding: 2(A + B + C) = 170 ⇒ A + B + C = 85", "B = 85 − (C + A) = 85 − 55 = 30"],
      "Sum of pairwise sums = 2 × total", "Subtract the pair that does NOT contain B.")


def add_all(B):
    identities(B)
    inequalities(B)
    linear(B)
    quad_compare(B)
    word_systems(B)
