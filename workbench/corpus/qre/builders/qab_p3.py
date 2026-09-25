"""QRE-QA-B part 3: Simplification (approximation, BODMAS, fraction-percentage, missing term, roots & powers) and Trigonometry."""
from qab_common import *
import re

S3 = math.sqrt(3)


def ev(expr):
    """Exact evaluation of an arithmetic expression: every number literal becomes a Fraction."""
    return eval(re.sub(r"\d+(\.\d+)?", lambda m: f"F('{m.group()}')", expr), {"F": F})


def approximation(B):
    M = "qa-approximation-with-decimals-and-surds-5e910263"
    # (tier, level, stem, actual, key, [(value, error)])
    items = [
        ("foundation", "L1", "24.98% of 639.97 + 17.02² ≈ ?", 0.2498 * 639.97 + 17.02 ** 2, 449,
         [(160 + 34, "squared 17 as 17 × 2"), (128 + 289, "took 24.98% as 20%"), (160 + 324, "rounded 17.02 up to 18")],
         ["24.98% of 639.97 ≈ 25% of 640 = 160", "17.02² ≈ 17² = 289", "Total ≈ 449"]),
        ("foundation", "L1", "1199.8 ÷ 24.02 × 7.98 ≈ ?", 1199.8 / 24.02 * 7.98, 400,
         [(50, "dropped the × 8"), (480, "rounded 24.02 to 20"), (1200 / 24 / 8, "divided by 8 instead of multiplying")],
         ["1200 ÷ 24 = 50", "50 × 8 = 400"]),
        ("foundation", "L2", "√1023.9 + ∛342.8 ≈ ?", math.sqrt(1023.9) + 342.8 ** (1 / 3), 39,
         [(32 + 49, "squared 7 instead of taking the cube root"), (32 + 19, "took ∛343 as 19"), (36 + 7, "took √1024 as 36")],
         ["√1024 = 32", "∛343 = 7", "Sum ≈ 39"]),
        ("foundation", "L2", "49.97 × 12.03 − 299.9 ≈ ?", 49.97 * 12.03 - 299.9, 300,
         [(900, "added instead of subtracting"), (250, "used 50 × 11"), (360, "used 55 × 12 − 300")],
         ["50 × 12 = 600", "600 − 300 = 300"]),
        ("foundation", "L2", "44.95% of 1200.2 − 15.1% of 399.8 ≈ ?", 0.4495 * 1200.2 - 0.151 * 399.8, 480,
         [(540 + 60, "added the two terms"), (540 - 40, "took 15% of 400 as 40"), (540 - 80, "took 15% of 400 as 80 (used 20%)")],
         ["45% of 1200 = 540", "15% of 400 = 60", "540 − 60 = 480"]),
        ("officer", "L2", "(√784.3 + √1295.8) × 4.98 ≈ ?", (math.sqrt(784.3) + math.sqrt(1295.8)) * 4.98, 320,
         [(28 * 36 // 5 * 1, "multiplied the roots instead of adding"), ((28 + 36) * 4, "rounded 4.98 down to 4"), ((26 + 36) * 5, "took √784 as 26")],
         ["√784 = 28, √1296 = 36", "(28 + 36) × 5 = 320"]),
        ("officer", "L3", "3.99³ + 8.01² − √143.9 ≈ ?", 3.99 ** 3 + 8.01 ** 2 - math.sqrt(143.9), 116,
         [(64 + 64 + 12, "added the square root"), (48 + 64 - 12, "took 4³ as 48"), (64 + 16 - 12, "took 8² as 16")],
         ["4³ = 64, 8² = 64, √144 = 12", "64 + 64 − 12 = 116"]),
        ("officer", "L3", "7/11 of 1649.8 ÷ 2.99 ≈ ?", 7 / 11 * 1649.8 / 2.99, 350,
         [(1050, "did not divide by 3"), (0.7 * 1650 / 3, "approximated 7/11 as 0.7"), (150 * 7 / 3 * 1.2, "took 1650 ÷ 11 as 180")],
         ["1650 ÷ 11 = 150; × 7 = 1050", "1050 ÷ 3 = 350"]),
        ("officer", "L3", "(18.02 × 14.98 + 29.9) ÷ 5.99 ≈ ?", (18.02 * 14.98 + 29.9) / 5.99, 50,
         [(270 / 6 + 30, "divided only the product by 6"), (18 * 15 / 6, "ignored the + 30"), (300 / 5, "rounded 5.99 to 5")],
         ["18 × 15 = 270", "(270 + 30) ÷ 6 = 50"]),
        ("officer", "L3", "√50.1 × √17.9 ≈ ?", math.sqrt(50.1) * math.sqrt(17.9), 30,
         [(7 * 4, "rounded each root down separately (7 and 4)"), (8 * 5, "rounded each root up separately"), (68, "added under the roots and ignored the root")],
         ["√50 × √18 = √900", "= 30"]),
        ("officer", "L3", "65.01% of 480.2 + 34.98% of 719.9 ≈ ?", 0.6501 * 480.2 + 0.3498 * 719.9, 564,
         [(312 + 216, "took 35% of 720 as 30%"), (288 + 252, "took 65% of 480 as 60%"), (0.65 * 720 + 0.35 * 480, "swapped the bases")],
         ["65% of 480 = 312", "35% of 720 = 252", "Sum = 564"]),
        ("officer", "L2", "2399.7 ÷ 39.9 ÷ 2.01 ≈ ?", 2399.7 / 39.9 / 2.01, 30,
         [(120, "multiplied by 2 instead of dividing"), (60, "divided only by 40"), (3, "misplaced a zero (2400 ÷ 400 ÷ 2)")],
         ["2400 ÷ 40 = 60", "60 ÷ 2 = 30"]),
        ("officer", "L3", "12.01² − 7.99² ≈ ?", 12.01 ** 2 - 7.99 ** 2, 80,
         [(16, "took (12 − 8)²"), (208, "added the squares"), (40, "used (12 − 8) × 10")],
         ["a² − b² = (a + b)(a − b)", "(12 + 8)(12 − 8) = 20 × 4 = 80"]),
        ("officer", "L3", "∛3374.6 × 2.98 − 18.1 ≈ ?", 3374.6 ** (1 / 3) * 2.98 - 18.1, 27,
         [(15 * 3 + 18, "added 18"), (14 * 3 - 18, "took ∛3375 as 14"), (15 * 2 - 18, "rounded 2.98 down to 2")],
         ["∛3375 = 15", "15 × 3 − 18 = 27"]),
        ("officer", "L3", "999.99 × 0.1499 + 250.03 × 0.401 ≈ ?", 999.99 * 0.1499 + 250.03 * 0.401, 250,
         [(15 + 100, "shifted the decimal in 1000 × 0.15"), (150 + 10, "shifted the decimal in 250 × 0.4"), (150 + 250 * 0.5, "rounded 0.401 to 0.5")],
         ["1000 × 0.15 = 150", "250 × 0.4 = 100", "Sum = 250"]),
    ]
    for tier, lv, stem, actual, key, cands, steps in items:
        vals = [key] + [c[0] for c in cands]
        closest_ok(key, vals, actual)
        q(B, M, lv, tier, stem, key, cands, steps + [f"(Exact value ≈ {actual:.2f}, closest option {key})"],
          "Round each number to the nearest convenient value, then simplify",
          "Round to values that keep the operations exact (perfect squares, cubes, simple percentages).")


def bodmas(B):
    M = "qa-bodmas-and-order-of-operations-eaf71d19"
    items = [
        ("foundation", "L1", "48 ÷ 6 × 2 + 5 − 3", "48/6*2+5-3",
         [("48/(6*2)+5-3", "multiplied before dividing"), ("48/6*(2+5)-3", "added before multiplying"), ("48/6*2+5+3", "sign slip on −3")]),
        ("foundation", "L1", "25 − 5 × 3 + 12 ÷ 4", "25-5*3+12/4",
         [("(25-5)*3+12/4", "subtracted before multiplying"), ("((25-5)*3+12)/4", "worked strictly left to right"), ("25-5*3-12/4", "sign slip on the last term")]),
        ("foundation", "L2", "7 + 3 × (10 − 4)² ÷ 9", "7+3*(10-4)**2/9",
         [("(7+3)*(10-4)**2/9", "added before multiplying"), ("7+3*(10**2-4**2)/9", "squared each term inside the bracket"), ("7+3*(10-4)/9", "forgot to square the bracket")]),
        ("foundation", "L2", "1/2 of 36 + 4 × 5", "36/2+4*5",
         [("(36+4)/2*5", "applied 'of' to 36 + 4"), ("(36/2+4)*5", "added before multiplying"), ("36/2+4+5", "added 5 instead of multiplying")]),
        ("foundation", "L2", "100 − [20 + {15 − (8 − 3)}]", "100-(20+(15-(8-3)))",
         [("100-20+15-(8-3)", "removed [ ] without changing the signs inside"), ("100-(20+(15+(8-3)))", "sign of (8 − 3) not carried"), ("100-(20+(15-8)-3)", "opened ( ) before { } wrongly")]),
        ("officer", "L3", "72 ÷ 3/4 of 16 + 5 × 2", "72/(3*16/4)+5*2",
         [("72/(3/4)*16+5*2", "divided by 3/4 before applying 'of'"), ("(72/(3*16/4)+5)*2", "added before multiplying"), ("72/3/4*16+5*2", "read 3/4 as ÷ 3 ÷ 4 and then multiplied by 16")]),
        ("officer", "L3", "18 − [5 − {6 + 2(7 − 8 − 5)}]", "18-(5-(6+2*(7-8-5)))",
         [("18-(5-(6+2*(7-(8-5))))", "read 7 − 8 − 5 as 7 − (8 − 5)"), ("18-(5-(6-2*(7-8-5)))", "sign slip on 2(−6)"), ("18+(5-(6+2*(7-8-5)))", "sign slip removing [ ]")]),
        ("officer", "L3", "(3/5 + 1/2) ÷ (2/3 − 1/4) × 5/6", "(F(3,5)+F(1,2))/(F(2,3)-F(1,4))*F(5,6)",
         [("(F(3,5)+F(1,2))/((F(2,3)-F(1,4))*F(5,6))", "multiplied before dividing"), ("(F(3,5)+F(1,2))*(F(2,3)-F(1,4))*F(5,6)", "did not invert the divisor"),
          ("F(4,7)/(F(2,3)-F(1,4))*F(5,6)", "added fractions as (3 + 1)/(5 + 2)")]),
        ("officer", "L2", "5 + 5 × 5 − 5 ÷ 5", "5+5*5-5/5",
         [("((5+5)*5-5)/5", "worked strictly left to right"), ("(5+5)*5-5/5", "added before multiplying"), ("5+5*(5-5)/5", "subtracted before multiplying and dividing")]),
        ("officer", "L3", "8 − 4 ÷ 2 × 3 + 6² ÷ 4 × 2", "8-4/2*3+6**2/4*2",
         [("8-4/(2*3)+6**2/(4*2)", "multiplied before dividing"), ("(8-4)/2*3+6**2/4*2", "subtracted first"), ("8-4/2*3+6**2/(4*2)", "multiplied before dividing in the second term only")]),
        ("officer", "L3", "0.5 × 0.4 + 0.3 ÷ 0.06 − 0.2", "0.5*0.4+0.3/0.06-0.2",
         [("0.5*0.4+0.3/0.06+0.2", "sign slip on 0.2"), ("0.5*0.4+0.3/0.6-0.2", "decimal slip: 0.3 ÷ 0.06 taken as 0.5"), ("0.5*0.4+3/0.06-0.2", "decimal slip: read 0.3 as 3")]),
        ("officer", "L3", "(6² − 4²) ÷ (6 − 4) + 3 × 2³", "(6**2-4**2)/(6-4)+3*2**3",
         [("(6-4)**2/(6-4)+3*2**3", "took 6² − 4² as (6 − 4)²"), ("(6**2-4**2)/(6-4)+3*6", "took 2³ as 6"), ("((6**2-4**2)/(6-4)+3)*2**3", "added before multiplying")]),
        ("officer", "L3", "1 + 1/(1 + 1/(1 + 1/2))", "1+1/(1+1/(1+F(1,2)))",
         [("1+1/(1+F(1,2))", "stopped one level early"), ("1+1/(1+1/(1+1/(1+F(1,2))))", "added an extra level"), ("1+F(1,2)", "treated the continued fraction as 1 + 1/2")]),
        ("officer", "L3", "2/3 ÷ 4/9 of 3/8 + 1/2", "F(2,3)/(F(4,9)*F(3,8))+F(1,2)",
         [("F(2,3)/F(4,9)*F(3,8)+F(1,2)", "divided before applying 'of'"), ("F(2,3)/(F(4,9)*F(3,8)+F(1,2))", "added before dividing"), ("F(2,3)*F(4,9)*F(3,8)+F(1,2)", "multiplied instead of dividing")]),
        ("officer", "L3", "150 ÷ [25 − {5 × (8 − 6)}] + 12 × 2", "150/(25-(5*(8-6)))+12*2",
         [("(150/(25-(5*(8-6)))+12)*2", "added before multiplying"), ("150/(25-(5*(8-6)))+12", "dropped the × 2"), ("150/25-5*(8-6)+12*2", "divided before evaluating the bracket")]),
    ]
    for tier, lv, disp, expr, wrongs in items:
        f = lambda e: eval(e, {"F": F}) if "F(" in e else ev(e)
        key = f(expr)
        cands = [(f(e), err) for e, err in wrongs]
        fm = fr if any(F(v).denominator not in (1, 2, 4, 5, 10, 20, 25, 50, 100) for v in [key] + [c[0] for c in cands]) else n
        q(B, M, lv, tier, f"Simplify: {disp}", key, cands + [(key + 1, "arithmetic slip"), (key - 1, "arithmetic slip")],
          ["Order: brackets → orders (powers, roots, 'of') → division/multiplication left to right → addition/subtraction left to right",
           f"Value = {fm(key)}"],
          "BODMAS / VBODMAS", "Division and multiplication have equal priority and are done left to right; 'of' is done before them.", fmt=fm)


def fracpct(B):
    M = "qa-fraction-and-percentage-equivalents-475121ec"
    P = lambda v: n(v) + "%"
    q(B, M, "L1", "foundation", "3/8 expressed as a percentage is:", F(3, 8) * 100,
      [(F(8, 3) * 100, "inverted the fraction"), (F(3, 8) * 10, "multiplied by 10 instead of 100"), (F(5, 8) * 100, "gave the complement")],
      ["3/8 = 0.375", "0.375 × 100 = 37.5%"], "Fraction × 100 = percentage", "Divide the numerator by the denominator first.", fmt=P)
    q(B, M, "L1", "foundation", "16⅔% of 240 is:", 40,
      [(48, "used 20% (1/5)"), (36, "used 15%"), (60, "used 25% (1/4)")],
      ["16⅔% = 1/6", "240 ÷ 6 = 40"], "16⅔% = 1/6", "Memorise the fractional equivalents of common percentages.")
    q(B, M, "L1", "foundation", "0.125 as a fraction in lowest terms is:", "1/8",
      [("1/80", "misplaced the decimal"), ("5/8", "used 0.625"), ("1/4", "halved instead of quartered")],
      ["0.125 = 125/1000 = 1/8"], "Decimal → fraction over a power of 10, then reduce", "125/1000 reduces by 125.", kind="numerical")
    q(B, M, "L2", "foundation", "83⅓% expressed as a fraction is:", "5/6",
      [("4/5", "used 80%"), ("7/8", "used 87.5%"), ("5/7", "used 71.4%")],
      ["83⅓% = 250/3 %", "= 250/300 = 5/6"], "83⅓% = 5/6", "It is 1 − 1/6.")
    q(B, M, "L2", "foundation", "11 1/9% of 810 is:", 90,
      [(81, "used 10%"), (F(810, 8), "used 12.5%"), (F(810, 11), "used 1/11 (9 1/11%)")],
      ["11 1/9% = 1/9", "810 ÷ 9 = 90"], "11 1/9% = 1/9", "Do not confuse 1/9 with 1/11.")
    # officer
    whole = F(216) / F(3, 8)
    q(B, M, "L2", "officer", "If 37.5% of a number is 216, then 62.5% of the number is:", whole * F(5, 8),
      [(whole, "gave the whole number"), (216 * F(5, 8), "took 62.5% of 216"), (whole * F(60, 100), "used 60% for 62.5%")],
      ["37.5% = 3/8 ⇒ number = 216 × 8/3 = 576", "62.5% = 5/8 ⇒ 576 × 5/8 = 360"], "Use 3/8 and 5/8", "Shortcut: 216 × 5/3 = 360.")
    k = F(350, 7) + F(180, 9) * 2
    q(B, M, "L3", "officer", "14 2/7% of 350 + 22 2/9% of 180 is:", k,
      [(F(350, 7) + F(180, 9), "used 1/9 for 22 2/9%"), (F(350, 14) + F(180, 9) * 2, "used 1/14 for 14 2/7%"), (F(350, 7) + F(180, 4), "used 25% for 22 2/9%")],
      ["14 2/7% = 1/7 ⇒ 50", "22 2/9% = 2/9 ⇒ 40", "Total = 90"], "1/7 = 14 2/7%, 2/9 = 22 2/9%", "22 2/9% is 2/9, not 1/9.")
    k = 2 * F(36 * 125, 100)
    q(B, M, "L2", "officer", "36% of 125 + 125% of 36 is:", k,
      [(k / 2, "computed only one term"), (36 + 125, "added the numbers"), (k * 2, "doubled twice")],
      ["x% of y = y% of x", "36% of 125 = 45; so total = 2 × 45 = 90"], "x% of y = y% of x", "Both terms are equal.")
    k = F(100, 60) * 100
    q(B, M, "L3", "officer", "If a is 60% of b, then b is what percent of a?", k,
      [(140, "added the 40% gap to 100%"), (40, "gave the gap as a percentage"), (160, "added 60 to 100")],
      ["b/a = 1/0.6 = 5/3", "5/3 = 166⅔%"], "b as % of a = 100/0.6", "The base changes, so the percentage is not symmetric.",
      fmt=lambda v: (mixedpct(v) if isinstance(v, F) else n(v) + "%"))
    vals = {"3/7": F(3, 7), "42.5%": F(425, 1000), "0.43": F(43, 100), "7/16": F(7, 16)}
    key = max(vals, key=vals.get)
    q(B, M, "L2", "officer", "Which is the largest: 3/7, 42.5%, 0.43, 7/16?", key,
      [(k_, "misjudged the decimal value") for k_ in vals if k_ != key],
      ["3/7 ≈ 0.4286, 42.5% = 0.425, 0.43, 7/16 = 0.4375", f"Largest = {key}"], "Convert all to decimals", "The values differ only in the third decimal place.",
      kind="conceptual")
    q(B, M, "L2", "officer", "9 1/11% expressed as a fraction is:", "1/11",
      [("1/9", "confused with 11 1/9%"), ("1/12", "confused with 8⅓%"), ("1/10", "rounded to 10%")],
      ["9 1/11% = 100/11 % = 1/11"], "1/11 = 9 1/11%", "Pairs such as 1/9 ↔ 11 1/9% and 1/11 ↔ 9 1/11% are easily swapped.")
    q(B, M, "L3", "officer", "The recurring decimal 0.454545… equals:", "5/11",
      [("9/20", "treated it as the terminating 0.45"), ("4/9", "treated only the 4 as recurring"), ("45/999", "used 999 for a 2-digit period")],
      ["Let x = 0.4545…; 100x = 45.4545…", "99x = 45 ⇒ x = 45/99 = 5/11"], "Pure recurring: period/(99…9)", "A 2-digit period uses 99.")
    k = (F(9, 8) * F(8, 9) - 1) * 100
    assert k == 0
    q(B, M, "L3", "officer", "A quantity is increased by 12.5% and the result is decreased by 11 1/9%. The net change is:", "No change",
      [("1.39% increase", "subtracted the two percentages"), ("1.39% decrease", "subtracted the percentages with the wrong sign"), ("1.25% increase", "used 10% for 11 1/9%")],
      ["12.5% = 1/8 ⇒ × 9/8", "11 1/9% = 1/9 ⇒ × 8/9", "9/8 × 8/9 = 1 ⇒ no change"], "Successive change: multiply the factors",
      "Percentages act on different bases; multiply factors, don't subtract.", kind="numerical")
    k = F(7, 12) * F(9, 4) * 480
    q(B, M, "L2", "officer", "7/12 of 2¼ of 480 is:", k,
      [(F(7, 12) * F(1, 2) * 480, "read 2¼ as 2 × ¼"), (F(7, 12) * 2 * 480, "ignored the ¼"), (F(9, 4) * 480, "ignored the 7/12")],
      ["2¼ = 9/4", "7/12 × 9/4 × 480 = 630"], "Convert mixed numbers to improper fractions", "2¼ means 2 + ¼.")
    q(B, M, "L3", "officer", "The decimal 0.2333… (only 3 recurring) equals:", "7/30",
      [("23/99", "treated both digits as recurring"), ("23/90", "did not subtract the non-recurring part"), ("23/100", "treated it as terminating")],
      ["x = 0.2333…; 100x − 10x = 23.33… − 2.33… = 21", "90x = 21 ⇒ x = 21/90 = 7/30"], "Mixed recurring: (whole − non-recurring)/(9s then 0s)",
      "Subtract the non-recurring part 2 from 23.")


def mixedpct(v):
    v = F(v)
    w, r = divmod(v.numerator, v.denominator)
    return (f"{w}" + (f" {r}/{v.denominator}" if r else "")) + "%"


def missing(B):
    M = "qa-missing-term-simplification-find-47d869c3"
    def solve_lin(f, target):
        a = f(F(1)) - f(F(0)); b = f(F(0))
        return (F(target) - b) / a
    # foundation
    k = solve_lin(lambda x: F(35, 100) * 240 + x, 150)
    q(B, M, "L1", "foundation", "35% of 240 + ? = 150", k,
      [(150 + 84, "added instead of subtracting"), (150 - 60, "took 25% of 240"), (150 - F(84, 10), "took 35% as 0.035")],
      ["35% of 240 = 84", "? = 150 − 84 = 66"], "Isolate the unknown", "Evaluate the percentage exactly.")
    k = solve_lin(lambda x: x * 12, F(1440, 8))
    q(B, M, "L1", "foundation", "? × 12 = 1440 ÷ 8", k,
      [(1440 // 8 * 12, "multiplied by 12 instead of dividing"), (1440 * 8 // 12, "multiplied by 8"), (1440 // 12, "ignored the ÷ 8")],
      ["1440 ÷ 8 = 180", "? = 180 ÷ 12 = 15"], "Evaluate the known side first", "Move the 12 across by division.")
    k = 17 ** 2 - 13 * 15
    q(B, M, "L1", "foundation", "17² − ? = 13 × 15", k,
      [(17 ** 2 + 13 * 15, "added instead of subtracting"), (34 - 13 * 15, "took 17² as 34"), (17 ** 2 - 185, "took 13 × 15 as 185")],
      ["289 − ? = 195", "? = 94"], "Isolate ?", "17² = 289.")
    k = (30 - 14) ** 2
    q(B, M, "L2", "foundation", "√? + 14 = 30", k,
      [(16, "forgot to square"), ((30 + 14) ** 2, "added 14 instead of subtracting"), (30 ** 2 - 14 ** 2, "squared each term")],
      ["√? = 16", "? = 256"], "Square after isolating the root", "Isolate √? before squaring.")
    k = solve_lin(lambda x: F(3, 5) * x, F(480, 4))
    q(B, M, "L2", "foundation", "3/5 of ? = 1/4 of 480", k,
      [(F(3, 5) * 120, "multiplied by 3/5 instead of dividing"), (120, "ignored the 3/5"), (F(480 * 3, 5), "used 3/5 of 480")],
      ["1/4 of 480 = 120", "? = 120 × 5/3 = 200"], "Divide by the fraction", "Dividing by 3/5 means multiplying by 5/3.")
    # officer
    k = solve_lin(lambda x: x / 12 * 7 + F(45, 100) * 480, 342)
    q(B, M, "L2", "officer", "(? ÷ 12) × 7 + 45% of 480 = 342", k,
      [(F(126 * 7, 12), "multiplied by 7/12 instead of 12/7"), (126 * 12, "ignored the × 7"), (F((342 + 216) * 12, 7), "added 216 instead of subtracting")],
      ["45% of 480 = 216", "7?/12 = 342 − 216 = 126", "? = 126 × 12/7 = 216"], "Isolate step by step", "Undo × 7 and ÷ 12 correctly.")
    k = math.isqrt(17 ** 2 - 15 ** 2)
    q(B, M, "L2", "officer", "?² + 15² = 17²", k,
      [(17 ** 2 - 15 ** 2, "did not take the square root"), (17 - 15, "subtracted the bases"), (math.sqrt(17 ** 2 + 15 ** 2), "added the squares")],
      ["?² = 289 − 225 = 64", "? = 8"], "a² = c² − b²", "Take the square root at the end.")
    k = (F(25, 100) * 432 / 6) ** 3
    q(B, M, "L3", "officer", "∛? × 6 = 25% of 432", k,
      [(18, "forgot to cube"), (18 ** 2, "squared instead of cubing"), ((F(432, 4) * 6) ** 1, "multiplied by 6 instead of dividing (and did not cube)")],
      ["25% of 432 = 108", "∛? = 108 ÷ 6 = 18", "? = 18³ = 5832"], "Cube after isolating", "Cubing, not squaring, undoes a cube root.")
    k = solve_lin(lambda x: F("4.5") * x - F("12.6") / F("0.3"), 21)
    q(B, M, "L3", "officer", "4.5 × ? − 12.6 ÷ 0.3 = 21", k,
      [((21 + F("4.2")) / F("4.5"), "decimal slip: 12.6 ÷ 0.3 taken as 4.2"), ((21 + 42) * F("4.5"), "multiplied by 4.5 instead of dividing"), (F(63, 4), "divided by 4 instead of 4.5")],
      ["12.6 ÷ 0.3 = 42", "4.5? = 63 ⇒ ? = 14"], "Evaluate division first (BODMAS)", "12.6 ÷ 0.3 = 126 ÷ 3 = 42.")
    k = 10 - 3
    q(B, M, "L2", "officer", "2^? × 8 = 4⁵", k,
      [(10, "forgot to subtract the exponent of 8"), (5 - 3, "equated 4⁵ with 2⁵"), (13, "added the exponent of 8")],
      ["4⁵ = 2¹⁰, 8 = 2³", "? + 3 = 10 ⇒ ? = 7"], "Same base: add exponents", "Rewrite everything as powers of 2.")
    k = (289 - F(30, 100) * 340) / 850 * 100
    q(B, M, "L3", "officer", "?% of 850 + 30% of 340 = 289", k,
      [(289 - 102, "did not convert to a percentage"), ((289 + 102) / F(850) * 100, "added 102 instead of subtracting"), ((289 - 102) / F(340) * 100, "used 340 as the base")],
      ["30% of 340 = 102", "?% of 850 = 187 ⇒ ? = 187/850 × 100 = 22"], "Percentage = part/base × 100", "Divide by the base 850.")
    k = solve_lin(lambda x: F(5, 8) * F(3, 7) * x, 1350)
    q(B, M, "L3", "officer", "5/8 of 3/7 of ? = 1350", k,
      [(F(1350 * 15, 56), "multiplied by the fractions instead of dividing"), (F(1350 * 8, 5), "ignored 3/7"), (F(1350 * 7, 3), "ignored 5/8")],
      ["5/8 × 3/7 = 15/56", "? = 1350 × 56/15 = 5040"], "Divide by the combined fraction", "Combine the fractions first.")
    k = 30 * F("0.27")
    q(B, M, "L3", "officer", "? ÷ √0.0729 = 30", k,
      [(30 * F("2.7"), "took √0.0729 as 2.7"), (30 * F("0.027"), "took √0.0729 as 0.027"), (30 / F("0.27"), "divided by the root instead of multiplying")],
      ["√0.0729 = 0.27", "? = 30 × 0.27 = 8.1"], "√(0.0729) = 0.27 (4 decimal places → 2)", "Halve the number of decimal places.")
    k = F(7, 4) + F(17, 6) - F(37, 12)
    q(B, M, "L3", "officer", "1¾ + 2⅚ − ? = 3 1/12", k,
      [(F(7, 4) + F(17, 6) + F(37, 12), "added 3 1/12 instead of subtracting"), (F(3, 4) + F(17, 6) - F(37, 12), "dropped the whole number of 1¾"), (F(7, 4) + F(17, 6) - F(7, 2), "read 3 1/12 as 3½")],
      ["1¾ + 2⅚ = 21/12 + 34/12 = 55/12", "? = 55/12 − 37/12 = 18/12 = 3/2"], "Common denominator 12", "Convert mixed numbers carefully.", fmt=fr)
    k = solve_lin(lambda x: F("0.6") * x + F("0.4") * 250, F(62, 100) * 500)
    q(B, M, "L3", "officer", "0.6 × ? + 0.4 × 250 = 62% of 500", k,
      [(210, "forgot to divide by 0.6"), (210 * F("0.6"), "multiplied by 0.6"), ((310 + 100) / F("0.6"), "added 100 instead of subtracting")],
      ["62% of 500 = 310; 0.4 × 250 = 100", "0.6? = 210 ⇒ ? = 350"], "Isolate ?", "Divide by 0.6 at the end.")


def roots(B):
    M = "qa-square-roots-cube-roots-and-powers-f19808cb"
    q(B, M, "L1", "foundation", "√0.0169 = ?", "0.13",
      [("0.013", "took too many decimal places"), ("1.3", "took too few decimal places"), ("0.0013", "kept all four decimal places")],
      ["0.0169 = 169/10000", "√ = 13/100 = 0.13"], "Decimal places halve under a square root", "4 decimal places → 2.")
    q(B, M, "L1", "foundation", "∛0.000343 = ?", "0.07",
      [("0.7", "took one decimal place"), ("0.007", "took three decimal places"), ("0.0007", "took four decimal places")],
      ["0.000343 = 343 × 10⁻⁶", "∛ = 7 × 10⁻² = 0.07"], "Decimal places divide by 3 under a cube root", "6 decimal places → 2.")
    q(B, M, "L1", "foundation", "27^(2/3) = ?", 9,
      [(18, "multiplied 27 by 2/3"), (3, "took only the cube root"), (81, "squared 9 again")],
      ["27^(1/3) = 3", "3² = 9"], "a^(m/n) = (ⁿ√a)^m", "Take the root first, then the power.")
    cyc = [7, 9, 3, 1]
    k = cyc[(45 - 1) % 4]
    assert k == pow(7, 45, 10)
    q(B, M, "L2", "foundation", "The unit digit of 7⁴⁵ is:", k,
      [(cyc[(45) % 4], "shifted the cycle by one"), (cyc[2], "used remainder 3"), (1, "assumed a multiple of 4")],
      ["Unit digits of 7ⁿ cycle 7, 9, 3, 1", "45 = 4 × 11 + 1 ⇒ unit digit 7"], "Cyclicity 4", "Remainder 1 → first element of the cycle.")
    k = math.isqrt(1764)
    q(B, M, "L2", "foundation", "√1764 = ?", k,
      [(48, "picked the other unit-digit candidate (8)"), (38, "took 30s instead of 40s"), (44, "took the root as ending in 4")],
      ["1764 ends in 4 ⇒ root ends in 2 or 8", "40² = 1600 < 1764 < 2025 = 45² ⇒ root is 42"], "Unit digit + bracketing", "42² = 1764 ✓")
    # officer
    v = 225
    for a in (154, 108, 25, 10):
        v = a + math.isqrt(v)
    k = math.isqrt(v)
    q(B, M, "L3", "officer", "√(10 + √(25 + √(108 + √(154 + √225)))) = ?", k,
      [(k * k, "did not take the outermost root"), (6, "stopped one level early"), (5, "took √25 and ignored the rest")],
      ["√225 = 15; 154 + 15 = 169 → 13", "108 + 13 = 121 → 11", "25 + 11 = 36 → 6", "10 + 6 = 16 → 4"], "Work from the innermost root outwards",
      "Take every root, including the outermost.")
    q(B, M, "L2", "officer", "(0.064)^(−1/3) = ?", "2.5",
      [("0.4", "ignored the negative sign in the exponent"), ("−0.4", "treated the negative exponent as a negative value"), ("0.25", "inverted 4 instead of 0.4")],
      ["0.064^(1/3) = 0.4", "Negative exponent ⇒ reciprocal: 1/0.4 = 2.5"], "a^(−m) = 1/a^m", "Negative exponents give reciprocals, not negatives.")
    q(B, M, "L2", "officer", "If 5^(2x − 1) = 625, then x = ?", F(5, 2),
      [(2, "solved 2x = 4"), (3, "solved 2x − 1 = 5"), (F(3, 2), "solved 2x − 1 = 2")],
      ["625 = 5⁴", "2x − 1 = 4 ⇒ x = 5/2"], "Equate exponents on the same base", "Add 1 before dividing by 2.", fmt=fr)
    q(B, M, "L3", "officer", "√12 + √27 − √75 = ?", "0",
      [("2√3", "dropped √27"), ("10√3", "added all three"), ("√−36", "combined under one root")],
      ["√12 = 2√3, √27 = 3√3, √75 = 5√3", "2√3 + 3√3 − 5√3 = 0"], "Simplify each surd to the same radicand", "Surds add only after simplification.", kind="numerical")
    val = (math.sqrt(5) + S3) / (math.sqrt(5) - S3)
    assert abs(val - (4 + math.sqrt(15))) < 1e-9
    q(B, M, "L3", "officer", "(√5 + √3) ÷ (√5 − √3) = ?", "4 + √15",
      [("8 + 2√15", "forgot to divide by (5 − 3)"), ("4 − √15", "sign slip in the numerator"), ("1 + √15/4", "divided by 8 instead of 2")],
      ["Multiply by (√5 + √3)/(√5 + √3)", "Numerator = 5 + 3 + 2√15 = 8 + 2√15; denominator = 5 − 3 = 2", "Result = 4 + √15"],
      "Rationalise with the conjugate", "Denominator becomes a − b = 2.", kind="numerical")
    r = math.isqrt(2000)
    k = 2000 - r * r
    q(B, M, "L2", "officer", "The least number to be subtracted from 2000 to make it a perfect square is:", k,
      [((r + 1) ** 2 - 2000, "found the number to add instead"), (r * r, "gave the perfect square"), (r, "gave the square root")],
      [f"44² = 1936 < 2000 < 2025 = 45²", f"2000 − 1936 = {k}"], "Subtract to the nearest lower square", "Subtracting goes down to 44².")
    k = F("1.2") + F("0.12") + F("0.012")
    q(B, M, "L3", "officer", "√1.44 + √0.0144 + √0.000144 = ?", k,
      [(F("1.2") + F("0.012") + F("0.012"), "took √0.0144 as 0.012"), (F("1.2") + F("0.12") + F("0.0012"), "took √0.000144 as 0.0012"), (F("1.2") + F("0.012") + F("0.0012"), "misplaced the decimal in both small roots")],
      ["√1.44 = 1.2, √0.0144 = 0.12, √0.000144 = 0.012", "Sum = 1.332"], "Halve decimal places", "0.000144 has 6 decimal places → root has 3.", fmt=lambda v: n(v, 4))
    k = 2 ** 10 * F(4) ** -3 * 8 ** 2
    q(B, M, "L2", "officer", "2¹⁰ × 4⁻³ × 8² = ?", k,
      [(2 ** 13, "took 4⁻³ as 2⁻³"), (2 ** 9, "took 8² as 2⁵"), (2 ** 22, "ignored the negative sign of 4⁻³")],
      ["4⁻³ = 2⁻⁶, 8² = 2⁶", "2^(10 − 6 + 6) = 2¹⁰ = 1024"], "Convert to base 2", "(2²)⁻³ = 2⁻⁶.")
    k = (pow(3, 65, 10) * 6 * pow(7, 71, 10)) % 10
    q(B, M, "L3", "officer", "The unit digit of 3⁶⁵ × 6⁵⁹ × 7⁷¹ is:", k,
      [((3 * 6 * 7) % 10, "took 7⁷¹ as ending in 7"), ((9 * 6 * 3) % 10, "took 3⁶⁵ as ending in 9"), ((3 + 6 + 3) % 10, "added the unit digits"), (1, "assumed every cycle ends in 1")],
      ["3⁶⁵: 65 ≡ 1 (mod 4) ⇒ 3", "6ⁿ always ends in 6", "7⁷¹: 71 ≡ 3 (mod 4) ⇒ 3", "3 × 6 × 3 = 54 ⇒ 4"], "Unit-digit cycles of length 4", "Multiply the unit digits, then take the last digit.")
    k = (F(13, 12) ** 2 - 1) * 144
    q(B, M, "L2", "officer", "If √(1 + x/144) = 13/12, then x = ?", k,
      [(1, "took 13 − 12"), (169, "used 13² only"), (144 + 169, "added 144 and 169")],
      ["1 + x/144 = 169/144", "x/144 = 25/144 ⇒ x = 25"], "Square both sides", "Square the fraction fully: 169/144.")


def complementary(B):
    M = "qa-complementary-angles-c7318569"
    dg = lambda v: n(v) + "°"
    q(B, M, "L1", "foundation", "The value of sin 37° ÷ cos 53° is:", 1,
      [(0, "subtracted instead of dividing"), ("tan 37°", "treated it as sin/cos of the same angle"), ("37/53", "divided the angles")],
      ["cos 53° = cos(90° − 37°) = sin 37°", "sin 37° ÷ sin 37° = 1"], "cos(90° − θ) = sin θ", "53° and 37° are complementary.", kind="numerical")
    q(B, M, "L1", "foundation", "The value of tan 25° × tan 65° is:", 1,
      [(0, "assumed complementary tangents cancel to 0"), ("tan 90°", "added the angles"), (2, "added the values")],
      ["tan 65° = cot 25°", "tan 25° × cot 25° = 1"], "tan(90° − θ) = cot θ", "tan θ · cot θ = 1.", kind="numerical")
    q(B, M, "L1", "foundation", "The value of sin² 28° + sin² 62° is:", 1,
      [(2, "treated each square as 1"), (0, "took them as cancelling"), ("2 sin² 28°", "treated the two terms as equal")],
      ["sin 62° = cos 28°", "sin² 28° + cos² 28° = 1"], "sin(90° − θ) = cos θ", "Rewrite one term with the complement.", kind="numerical")
    k = F(90 + 26, 4)
    assert abs(math.sin(math.radians(3 * k)) - math.cos(math.radians(k - 26))) < 1e-12
    q(B, M, "L2", "foundation", "If sin 3A = cos(A − 26°), where 3A is acute, then A = ?", k,
      [(F(90 - 26, 4), "sign slip on 26°"), (F(90 + 26, 2), "took 3A + A as 2A"), (F(90 + 26, 3), "dropped A from the second angle")],
      ["sin 3A = cos(90° − 3A)", "90° − 3A = A − 26° ⇒ 4A = 116° ⇒ A = 29°"], "sin x = cos y ⇒ x + y = 90° (acute)", "Collect A terms carefully.", fmt=dg)
    q(B, M, "L2", "foundation", "The value of cos 48° − sin 42° is:", 0,
      [(1, "assumed complementary pairs give 1"), ("cos 6°", "subtracted the angles"), ("2 cos 48°", "added instead of subtracting")],
      ["sin 42° = cos 48°", "cos 48° − cos 48° = 0"], "sin(90° − θ) = cos θ", "The two terms are equal.", kind="numerical")
    # officer
    q(B, M, "L2", "officer", "The value of tan 10° · tan 20° · tan 45° · tan 70° · tan 80° is:", 1,
      [(0, "assumed the product vanishes"), ("√3", "took tan 45° as √3"), (45, "used the angle 45 instead of tan 45°")],
      ["tan 10° tan 80° = 1, tan 20° tan 70° = 1", "tan 45° = 1 ⇒ product = 1"], "tan θ · tan(90° − θ) = 1", "Pair complementary angles.", kind="numerical")
    k = F(90 + 18, 3)
    q(B, M, "L2", "officer", "If tan 2A = cot(A − 18°), where 2A is acute, then A = ?", k,
      [(F(90 - 18, 3), "sign slip on 18°"), (F(90 + 18, 2), "equated only 2A with 108°"), (F(90 + 18, 1) - 36, "solved A = 108° − 36°")],
      ["cot(A − 18°) = tan(108° − A)", "2A = 108° − A ⇒ A = 36°"], "tan x = cot y ⇒ x + y = 90°", "Both A-terms must be collected.", fmt=dg)
    q(B, M, "L3", "officer", "The value of (sin 35° cos 55° + cos 35° sin 55°) ÷ (cosec² 10° − tan² 80°) is:", 1,
      [(0, "took the denominator as 0"), (2, "evaluated the numerator as 2"), (F(1, 2), "took the denominator as 2")],
      ["cos 55° = sin 35°, sin 55° = cos 35° ⇒ numerator = sin² 35° + cos² 35° = 1", "tan 80° = cot 10° ⇒ denominator = cosec² 10° − cot² 10° = 1", "Value = 1"],
      "Complements + Pythagorean identities", "Convert tan 80° to cot 10° before using cosec² − cot² = 1.", fmt=fr)
    q(B, M, "L3", "officer", "The value of sec 70° sin 20° + cos 20° cosec 70° is:", 2,
      [(1, "evaluated only one product"), (0, "subtracted the products"), ("2 sin 20°", "did not convert sec 70°")],
      ["sec 70° = cosec 20° ⇒ sin 20° cosec 20° = 1", "cosec 70° = sec 20° ⇒ cos 20° sec 20° = 1", "Total = 2"], "sec(90° − θ) = cosec θ", "Each product is 1.", kind="numerical")
    k = F(90 + 20, 5)
    q(B, M, "L3", "officer", "If sec 4A = cosec(A − 20°), where 4A is acute, then A = ?", k,
      [(F(90 - 20, 5), "sign slip on 20°"), (F(90 + 20, 4), "dropped the A on the right"), (F(90 + 20, 3), "took 4A + A as 3A")],
      ["sec 4A = cosec(90° − 4A)", "90° − 4A = A − 20° ⇒ 5A = 110° ⇒ A = 22°"], "sec x = cosec y ⇒ x + y = 90°", "Carry the −20° correctly.", fmt=dg)
    q(B, M, "L2", "officer", "sin(90° − θ) cos θ + cos(90° − θ) sin θ equals:", "1",
      [("0", "took the terms as cancelling"), ("2 sin θ cos θ", "did not convert the complements"), ("cos 2θ", "used the double-angle pattern with a sign slip")],
      ["sin(90° − θ) = cos θ, cos(90° − θ) = sin θ", "cos² θ + sin² θ = 1"], "Complement identities", "Convert before simplifying.", kind="numerical")
    q(B, M, "L3", "officer", "The value of cos 1° × cos 2° × cos 3° × … × cos 180° is:", 0,
      [(1, "paired complements as in a tangent product"), (-1, "used cos 180° = −1 only"), (F(1, 2), "used cos 60° only")],
      ["The product contains cos 90° = 0", "So the whole product is 0"], "A single zero factor makes the product zero", "Look for a zero factor before pairing.", fmt=fr)
    q(B, M, "L3", "officer", "If A + B = 90°, then (tan A tan B + tan A cot B) ÷ (sin A sec B) − sin² B ÷ cos² A equals:", "tan² A",
      [("cot² A", "converted tan A cot B as cot² A"), ("sec² A", "forgot to subtract sin² B/cos² A = 1"), ("1", "took tan A cot B as 1")],
      ["tan B = cot A ⇒ tan A tan B = 1; cot B = tan A ⇒ tan A cot B = tan² A", "sec B = cosec A ⇒ sin A sec B = 1; sin B = cos A ⇒ sin² B/cos² A = 1",
       "Expression = 1 + tan² A − 1 = tan² A"], "Complement substitution + 1 + tan² = sec²", "Replace every B-ratio by its A-complement first.", kind="numerical")
    q(B, M, "L3", "officer", "The value of tan 1° × tan 2° × tan 3° × … × tan 89° is:", 1,
      [(0, "assumed the product vanishes"), (89, "counted the factors"), ("Not defined", "thought tan 90° is included")],
      ["Pair tan θ with tan(90° − θ): each pair is 1", "Middle factor tan 45° = 1 ⇒ product = 1"], "tan θ tan(90° − θ) = 1", "tan 90° is not in the product.", kind="numerical")
    k = 90 - 20 - 40
    q(B, M, "L2", "officer", "If cos(40° + x) = sin 20°, where 40° + x is acute, then x = ?", k,
      [(20 - 40, "equated the angles directly"), (90 + 20 - 40, "added 20° instead of subtracting"), (90 - 40, "ignored the 20°")],
      ["sin 20° = cos 70°", "40° + x = 70° ⇒ x = 30°"], "sin θ = cos(90° − θ)", "Convert first, then equate.", fmt=dg)


def surd(p, q_, unit=""):
    p, q_ = F(p), F(q_)
    parts = []
    if p:
        parts.append(fr(p))
    if q_:
        aq = abs(q_)
        c = ("" if aq.numerator == 1 else str(aq.numerator)) + "√3" + ("" if aq.denominator == 1 else f"/{aq.denominator}")
        if parts:
            parts.append(("− " if q_ < 0 else "+ ") + c)
        else:
            parts.append(("−" if q_ < 0 else "") + c)
    s = " ".join(parts) if parts else "0"
    return s + unit


def heights(B):
    M = "qa-heights-and-distances-7268e06f"
    m = lambda p, q_: surd(p, q_, " m")
    t = math.tan; r = math.radians
    h = 20 * t(r(60)); assert abs(h - 20 * S3) < 1e-9
    q(B, M, "L1", "foundation", "From a point 20 m from the foot of a tower, the angle of elevation of its top is 60°. The height of the tower is:", m(0, 20),
      [(m(0, F(20, 3)), "used tan 30° instead of tan 60°"), (m(40, 0), "used sec 60° (hypotenuse)"), (m(0, 10), "used sin 60° × 20")],
      ["tan 60° = h/20", "h = 20√3 m"], "tan θ = opposite/adjacent", "tan 60° = √3, not 1/√3.", kind="numerical")
    q(B, M, "L1", "foundation", "A 10 m ladder leans against a wall, making 60° with the ground. How high up the wall does it reach?", m(0, 5),
      [(m(5, 0), "used cos 60°"), (m(0, 10), "took the ladder as the base and used tan 60°"), (m(20, 0), "used sec 60°")],
      ["sin 60° = h/10", "h = 10 × √3/2 = 5√3 m"], "sin θ = opposite/hypotenuse", "The ladder is the hypotenuse.", kind="numerical")
    q(B, M, "L1", "foundation", "A kite is flying on a 100 m string making 30° with the ground. The height of the kite is:", m(50, 0),
      [(m(0, 50), "used cos 30°"), (m(0, 100), "used cot 30°"), (m(0, F(100, 3)), "used tan 30°")],
      ["sin 30° = h/100", "h = 50 m"], "sin θ = opposite/hypotenuse", "The string is the hypotenuse.", kind="numerical")
    q(B, M, "L2", "foundation", "The shadow of a pole is √3 times its height. The angle of elevation of the sun is:", "30°",
      [("60°", "took tan θ = √3"), ("45°", "assumed equal shadow and height"), ("90°", "took the shadow as zero")],
      ["tan θ = h/(√3 h) = 1/√3", "θ = 30°"], "tan θ = height/shadow", "A longer shadow means a lower sun.", kind="numerical")
    q(B, M, "L2", "foundation", "From a point 35 m from the base of a tower, the angle of elevation of the top is 45°. The height of the tower is:", "35 m",
      [("35√2 m", "used sec 45°"), (m(0, 35), "used tan 60°"), ("17.5 m", "halved the distance")],
      ["tan 45° = 1 ⇒ h = 35 m"], "tan 45° = 1", "At 45° height equals horizontal distance.", kind="numerical")
    # officer
    H = 60
    d = H / t(r(60)); diff = d * t(r(30))
    assert abs(H - diff - 40) < 1e-9
    q(B, M, "L3", "officer", "From the top of a 60 m tower, the angles of depression of the top and the bottom of a building are 30° and 60°. The height of the building is:", m(40, 0),
      [(m(20, 0), "gave the height difference"), (m(0, 20), "gave the horizontal distance"), (m(60, -20), "subtracted the distance from 60")],
      ["Distance d = 60/tan 60° = 20√3 m", "Drop to building top = d tan 30° = 20 m", "Building = 60 − 20 = 40 m"], "Two right triangles sharing the base",
      "Subtract the drop from the tower height.", kind="numerical")
    h = 40 / (1 / t(r(30)) - 1 / t(r(60)))
    assert abs(h - 20 * S3) < 1e-9
    q(B, M, "L3", "officer", "The angle of elevation of the top of a tower is 30°. On walking 40 m towards it, the angle becomes 60°. The height of the tower is:", m(0, 20),
      [(m(0, 40), "used 40 tan 60°"), (m(20, 0), "halved the walked distance"), (m(40, 0), "took the height equal to the walked distance")],
      ["h cot 30° − h cot 60° = 40", "h(√3 − 1/√3) = 40 ⇒ h × 2/√3 = 40", "h = 20√3 m"], "Difference of cotangents", "The 40 m is the difference of the two horizontal distances.", kind="numerical")
    dd = 75 / t(r(30)) + 75 / t(r(60))
    assert abs(dd - 100 * S3) < 1e-9
    q(B, M, "L3", "officer", "Two men on opposite sides of a 75 m tower observe its top at angles of elevation 30° and 60°. The distance between the men is:", m(0, 100),
      [(m(0, 50), "subtracted the distances (same side)"), (m(100, 0), "dropped the √3"), (m(0, 75), "used only the 30° distance")],
      ["Distances: 75 cot 30° = 75√3, 75 cot 60° = 25√3", "Sum = 100√3 m"], "Opposite sides ⇒ add distances", "On opposite sides the distances add.", kind="numerical")
    h = 20 / (1 / t(r(45)) - 1 / t(r(60)))
    assert abs(h - (30 + 10 * S3)) < 1e-9
    q(B, M, "L3", "officer", "From a point, the angle of elevation of a tower's top is 60°. Moving 20 m directly away, it becomes 45°. The height of the tower is:", m(30, 10),
      [(m(10, 10), "rationalised with the wrong factor (10(√3 + 1))"), (m(0, 20), "used 20 tan 60°"), (m(30, -10), "sign slip in the conjugate")],
      ["h cot 45° − h cot 60° = 20 ⇒ h(1 − 1/√3) = 20", "h = 20√3/(√3 − 1) = 10√3(√3 + 1) = 30 + 10√3 m"], "Difference of cotangents", "Multiply by the conjugate (√3 + 1).", kind="numerical")
    fl = 20 * t(r(60)) - 20
    assert abs(fl - 20 * (S3 - 1)) < 1e-9
    q(B, M, "L3", "officer", "A flagstaff stands on a 20 m building. From a point on the ground, the angles of elevation of the bottom and top of the flagstaff are 45° and 60°. The length of the flagstaff is:", "20(√3 − 1) m",
      [("20√3 m", "gave the total height"), ("20(√3 + 1) m", "added the building height"), ("20 m", "took the flagstaff equal to the building")],
      ["45° ⇒ distance = 20 m", "Total height = 20 tan 60° = 20√3 m", "Flagstaff = 20√3 − 20 = 20(√3 − 1) m"], "Total − building", "Subtract the building height.", kind="numerical")
    hh = 1500 * S3
    dist = hh * (1 / t(r(30)) - 1 / t(r(60)))
    assert abs(dist - 3000) < 1e-6
    q(B, M, "L3", "officer", "An aeroplane flying horizontally at a height of 1500√3 m is seen at an angle of elevation of 60°, and 15 seconds later at 30°. Its speed is:", "720 km/h",
      [("200 km/h", "did not convert m/s to km/h"), ("360 km/h", "used only half the distance"), ("1440 km/h", "used 7.5 seconds")],
      ["Horizontal distance covered = 1500√3 (cot 30° − cot 60°) = 1500√3 × 2/√3 = 3000 m", "Speed = 3000/15 = 200 m/s = 720 km/h"],
      "Speed = distance/time; × 18/5 for km/h", "Convert units at the end.", kind="numerical")
    tot = 10 * t(r(30)) + 10 / math.cos(r(30))
    assert abs(tot - 10 * S3) < 1e-9
    q(B, M, "L3", "officer", "A tree breaks due to a storm; the broken part bends so that its top touches the ground 10 m from the foot, making 30° with the ground. The original height of the tree was:", m(0, 10),
      [(m(0, F(20, 3)), "gave only the broken part"), (m(0, F(10, 3)), "gave only the standing part"), (m(10, 10), "added 10 m to the standing part")],
      ["Standing part = 10 tan 30° = 10/√3", "Broken part = 10/cos 30° = 20/√3", "Height = 30/√3 = 10√3 m"], "Height = standing + broken", "The broken part is the hypotenuse.", kind="numerical")
    dd = 100 / t(r(30)) - 100 / t(r(45))
    assert abs(dd - 100 * (S3 - 1)) < 1e-9
    q(B, M, "L3", "officer", "From the top of a 100 m cliff, the angles of depression of two ships on the same side are 45° and 30°. The distance between the ships is:", "100(√3 − 1) m",
      [("100(√3 + 1) m", "added the distances (opposite sides)"), (m(0, 100), "gave the far ship's distance"), ("100 m", "gave the near ship's distance")],
      ["Distances: 100 cot 45° = 100, 100 cot 30° = 100√3", "Difference = 100(√3 − 1) m"], "Same side ⇒ subtract distances", "Ships on the same side: subtract.", kind="numerical")
    k = math.isqrt(4 * 9)
    q(B, M, "L3", "officer", "The angles of elevation of the top of a tower from two points 4 m and 9 m from its base, on the same straight line, are complementary. The height of the tower is:", f"{k} m",
      [("6.5 m", "averaged the distances"), ("5 m", "took the difference of distances"), ("36 m", "did not take the square root")],
      ["tan θ = h/4 and tan(90° − θ) = cot θ = h/9", "tan θ × cot θ = 1 ⇒ h²/36 = 1 ⇒ h = 6 m"], "h = √(ab)", "Use the product of the two tangents.", kind="numerical")
    k = 45 + 1.6
    q(B, M, "L2", "officer", "An observer 1.6 m tall stands 45 m from a tower. The angle of elevation of the top of the tower from his eyes is 45°. The height of the tower is:", n(k) + " m",
      [("45 m", "ignored the observer's height"), (n(45 - 1.6) + " m", "subtracted the observer's height"), (n(45 * S3 + 1.6) + " m", "used tan 60°")],
      ["Height above eye level = 45 tan 45° = 45 m", "Tower = 45 + 1.6 = 46.6 m"], "Add eye height", "Angles are measured from eye level.", kind="numerical")


def trig_id(B):
    M = "qa-trigonometric-ratios-and-identities-179e3e31"
    q(B, M, "L1", "foundation", "If sin θ = 3/5 (θ acute), then tan θ = ?", F(3, 4),
      [(F(4, 3), "gave cot θ"), (F(4, 5), "gave cos θ"), (F(5, 3), "gave cosec θ")],
      ["cos θ = 4/5 (3-4-5 triangle)", "tan θ = (3/5)/(4/5) = 3/4"], "tan = sin/cos", "Opposite 3, hypotenuse 5, adjacent 4.", fmt=fr)
    q(B, M, "L1", "foundation", "(1 + tan² θ) cos² θ simplifies to:", "1",
      [("sin² θ", "expanded as cos² θ + sin² θ − cos² θ"), ("tan² θ", "cancelled the 1"), ("sec² θ", "did not multiply by cos² θ")],
      ["1 + tan² θ = sec² θ", "sec² θ × cos² θ = 1"], "1 + tan² θ = sec² θ", "sec θ and cos θ are reciprocals.", kind="numerical")
    q(B, M, "L1", "foundation", "The value of sin 60° cos 30° + cos 60° sin 30° is:", 1,
      [(F(1, 2), "took sin 60° cos 30° as 1/4"), (F(3, 4), "left out the second product"), ("√3/2", "evaluated sin 60° only")],
      ["(√3/2)(√3/2) + (1/2)(1/2) = 3/4 + 1/4 = 1"], "Standard values (= sin 90°)", "Square roots multiply to 3, not √3.", fmt=fr)
    q(B, M, "L2", "foundation", "If cos θ = 12/13 (θ acute), then sin θ + cos θ = ?", F(17, 13),
      [(F(7, 13), "subtracted"), (1, "assumed sin θ + cos θ = 1"), (F(13, 17), "inverted the result")],
      ["sin θ = 5/13", "5/13 + 12/13 = 17/13"], "sin² + cos² = 1", "sin² + cos² = 1, not sin + cos.", fmt=fr)
    q(B, M, "L2", "foundation", "The value of tan 45° + sec 60° − cosec 30° is:", 1,
      [(5, "added cosec 30°"), (3, "ignored cosec 30°"), (-1, "took tan 45° as 0")],
      ["tan 45° = 1, sec 60° = 2, cosec 30° = 2", "1 + 2 − 2 = 1"], "Standard values", "sec 60° = 1/cos 60° = 2.")
    # officer
    s_ = F(16 - 1, 16 + 1)
    q(B, M, "L3", "officer", "If sec θ + tan θ = 4, then sin θ = ?", s_,
      [(F(8, 17), "gave cos θ"), (F(15, 8), "gave tan θ"), (F(1, 4), "gave sec θ − tan θ")],
      ["sec θ − tan θ = 1/4 (since sec² − tan² = 1)", "sec θ = 17/8, tan θ = 15/8", "sin θ = tan θ/sec θ = 15/17"], "sec² − tan² = 1",
      "sin θ = (k² − 1)/(k² + 1).", fmt=fr)
    tn = F(4, 5)
    k = (5 * tn - 3) / (5 * tn + 2)
    q(B, M, "L3", "officer", "If 5 tan θ = 4, then (5 sin θ − 3 cos θ) ÷ (5 sin θ + 2 cos θ) = ?", k,
      [((5 * F(5, 4) - 3) / (5 * F(5, 4) + 2), "took tan θ = 5/4"), ((tn - 3) / (tn + 2), "dropped the factor 5"), (F(7, 6), "added 3 in the numerator")],
      ["Divide numerator and denominator by cos θ", "(5 tan θ − 3)/(5 tan θ + 2) = (4 − 3)/(4 + 2) = 1/6"], "Divide by cos θ", "5 tan θ = 4 directly.", fmt=fr)
    q(B, M, "L3", "officer", "sin⁶ θ + cos⁶ θ + 3 sin² θ cos² θ equals:", "1",
      [("0", "sign slip in the cube identity"), ("3", "treated each term as 1"), ("1 − 3 sin² θ cos² θ", "stopped at sin⁶ + cos⁶")],
      ["sin⁶ + cos⁶ = (sin² + cos²)³ − 3 sin² cos²(sin² + cos²) = 1 − 3 sin² cos²", "Adding 3 sin² cos² gives 1"], "a³ + b³ = (a + b)³ − 3ab(a + b)",
      "Use a = sin² θ, b = cos² θ.", kind="numerical")
    q(B, M, "L3", "officer", "If sin θ + cos θ = √2 cos θ, then cot θ = ?", "√2 + 1",
      [("√2 − 1", "gave tan θ"), ("√2", "dropped the −1"), ("1/√2", "took sin θ = cos θ/√2")],
      ["sin θ = (√2 − 1) cos θ ⇒ tan θ = √2 − 1", "cot θ = 1/(√2 − 1) = √2 + 1"], "Rationalise", "cot is the reciprocal of tan.", kind="numerical")
    q(B, M, "L2", "officer", "If tan θ + cot θ = 2, then tan² θ + cot² θ = ?", 2,
      [(4, "squared without subtracting 2"), (0, "subtracted 4"), (6, "added 2")],
      ["(tan θ + cot θ)² = tan² θ + cot² θ + 2", "tan² θ + cot² θ = 4 − 2 = 2"], "x² + 1/x² = (x + 1/x)² − 2", "tan θ · cot θ = 1.")
    q(B, M, "L3", "officer", "(1 − sin θ) ÷ (1 + sin θ) is equal to:", "(sec θ − tan θ)²",
      [("(sec θ + tan θ)²", "sign slip"), ("(cosec θ − cot θ)²", "used the cosec–cot identity"), ("sec² θ − tan² θ", "expanded incorrectly")],
      ["Multiply numerator and denominator by (1 − sin θ): (1 − sin θ)²/cos² θ", "= (1/cos θ − sin θ/cos θ)² = (sec θ − tan θ)²"], "Rationalise with the conjugate",
      "Denominator becomes 1 − sin² θ = cos² θ.", kind="numerical")
    q(B, M, "L2", "officer", "If x = a sec θ and y = b tan θ, then x²/a² − y²/b² = ?", "1",
      [("0", "took sec² = tan²"), ("−1", "sign slip"), ("a² − b²", "did not divide by a² and b²")],
      ["x²/a² = sec² θ, y²/b² = tan² θ", "sec² θ − tan² θ = 1"], "sec² − tan² = 1", "Divide first to isolate the ratios.", kind="numerical")
    q(B, M, "L3", "officer", "The maximum value of 3 sin θ + 4 cos θ is:", 5,
      [(7, "added the coefficients"), (1, "subtracted the coefficients"), (12, "multiplied the coefficients")],
      ["Maximum of a sin θ + b cos θ = √(a² + b²)", "√(9 + 16) = 5"], "√(a² + b²)", "sin θ and cos θ cannot both be 1.")
    q(B, M, "L3", "officer", "The minimum value of 9 tan² θ + 4 cot² θ is:", 12,
      [(13, "added the coefficients"), (0, "took tan θ = 0"), (6, "took √36 without doubling")],
      ["AM ≥ GM: 9 tan² θ + 4 cot² θ ≥ 2√(9 × 4) = 12", "Equality when tan² θ = 2/3"], "a x + b/x ≥ 2√(ab)", "Double the geometric mean.")
    q(B, M, "L3", "officer", "If cosec θ − cot θ = 1/3, then cos θ = ?", F(4, 5),
      [(F(3, 5), "gave sin θ"), (F(4, 3), "gave cot θ"), (F(5, 4), "inverted cos θ")],
      ["cosec θ + cot θ = 3", "cosec θ = 5/3, cot θ = 4/3", "sin θ = 3/5 ⇒ cos θ = cot θ × sin θ = 4/5"], "cosec² − cot² = 1", "Add and subtract the two equations.", fmt=fr)


def add_all(B):
    approximation(B)
    bodmas(B)
    fracpct(B)
    missing(B)
    roots(B)
    complementary(B)
    heights(B)
    trig_id(B)
