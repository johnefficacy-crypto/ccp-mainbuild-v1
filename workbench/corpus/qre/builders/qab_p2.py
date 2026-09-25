"""QRE-QA-B part 2: Number System (clocks & calendars, LCM/HCF, series, wrong-term series, P&C, remainders, consecutive numbers)."""
from qab_common import *
import datetime, calendar
from math import comb, perm, factorial, gcd

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def sn(x):
    """series term formatting: no digit grouping, so commas only separate terms"""
    return n(x).replace(",", "")


def mixed(x):
    x = F(x)
    w, r = divmod(x.numerator, x.denominator)
    return str(w) if r == 0 else (f"{w} {r}/{x.denominator}" if w else f"{r}/{x.denominator}")


def angle(h, m):
    a = abs(F(30 * (h % 12)) - F(11, 2) * m)
    return min(a, 360 - a)


def lcmm(*a):
    r = 1
    for x in a:
        r = r * x // gcd(r, x)
    return r


def clocks(B):
    M = "clocks-and-calendars"
    dg = lambda v: n(v) + "°"
    # ---- foundation ----
    for lv, (h, m) in [("L1", (3, 40)), ("L1", (7, 20))]:
        k = angle(h, m)
        q(B, M, lv, "foundation", f"What is the smaller angle between the hands of a clock at {h}:{m:02d}?", k,
          [(360 - k, "gave the reflex angle"), (abs(30 * h - 6 * m) if abs(30 * h - 6 * m) <= 180 else 360 - abs(30 * h - 6 * m), "kept the hour hand fixed at the hour mark"),
           (abs(30 * h - 5 * m), "moved the minute hand 5° per minute"), (k + 10, "added the hour-hand shift instead of subtracting")],
          [f"θ = |30H − 5.5M| = |30×{h} − 5.5×{m}| = |{30*h} − {n(F(11,2)*m)}| = {n(abs(30*h - F(11,2)*m))}°",
           f"Smaller angle = {n(k)}°"],
          "θ = |30H − 11M/2|", "The hour hand also moves 0.5° per minute.", fmt=dg)
    d1 = datetime.date(2023, 8, 15)
    d2 = datetime.date(2024, 8, 15)
    k = DAYS[d2.weekday()]
    assert DAYS[d1.weekday()] == "Tuesday"
    q(B, M, "L2", "foundation", "15 August 2023 was a Tuesday. On which day of the week did 15 August 2024 fall?", k,
      [(DAYS[(d1.weekday() + 1) % 7], "ignored the leap day of February 2024"), (DAYS[(d1.weekday() + 3) % 7], "added one odd day too many"),
       (DAYS[(d1.weekday() - 2) % 7], "counted the odd days backwards")],
      ["From 15-08-2023 to 15-08-2024 = 366 days (29 Feb 2024 lies in between)", "366 = 52 weeks + 2 odd days", "Tuesday + 2 = Thursday"],
      "Odd days = days mod 7", "A leap-year February inside the interval adds a second odd day.", kind="numerical")
    q(B, M, "L1", "foundation", "A clock gains 5 minutes every hour. It is set right at 8:00 a.m. What time will it show at 8:00 p.m. the same day (actual time)?",
      "9:00 p.m.", [("7:00 p.m.", "subtracted the gain"), ("8:05 p.m.", "counted the gain for only one hour"), ("8:12 p.m.", "gain of 1 minute per hour taken")],
      ["12 hours elapse", "Gain = 12 × 5 = 60 minutes", "Clock shows 8:00 p.m. + 1 h = 9:00 p.m."],
      "Total gain = rate × elapsed time", "A gaining clock runs ahead of the true time.", kind="numerical")
    # verify: coincidences occur every 720/11 minutes
    assert int(24 * 60 / F(720, 11)) == 22
    q(B, M, "L2", "foundation", "How many times do the hour and minute hands of a clock coincide in a day (24 hours)?", 22,
      [(24, "assumed once every hour"), (44, "counted right-angle positions instead"), (11, "counted for 12 hours only")],
      ["Hands coincide every 720/11 = 65 5/11 minutes", "In 12 h: 11 times (the 11–1 o'clock coincidence is at 12)", "In 24 h: 22 times"],
      "Coincidence interval = 720/11 min", "Between 11 and 1 there is only one coincidence (at 12).")
    # ---- officer ----
    h = 4
    k = F(60 * h, 11)      # 30h = 5.5 m ⇒ m = 60h/11
    assert F(30 * h) == F(11, 2) * k
    q(B, M, "L2", "officer", "At what time between 4 and 5 o'clock are the hands of a clock together?", f"{mixed(k)} min past 4",
      [(f"{5*h} min past 4", "ignored the movement of the hour hand (4 × 5 divisions)"), (f"{mixed(F(30*h, 11))} min past 4", "divided 30H by 11 instead of 5.5"),
       (f"{mixed(2 * k)} min past 4", "doubled the result (used 120H/11)")],
      [f"Hour hand at 30 × 4 = 120°; minute hand gains 5.5° per minute", f"m = 120 ÷ 5.5 = {mixed(k)} minutes"],
      "m = 60H/11 (coincidence)", "The minute hand must make up 120° at a relative speed of 5.5°/min.", kind="numerical")
    k = F(30 * 2 + 90, F(11, 2))
    assert angle(2, k) == 90
    q(B, M, "L3", "officer", "At what time, for the first time after 2 o'clock, are the hands of a clock at right angles?", f"{mixed(k)} min past 2",
      [(f"{mixed(F(90 - 60, F(11, 2)))} min past 2", "used (90 − 60) instead of (60 + 90)"), (f"{mixed(F(150, 6))} min past 2", "ignored the hour hand's motion"),
       (f"{mixed(F(60 + 120, F(11,2)))} min past 2", "used a 120° gap instead of 90°")],
      ["At 2:00 the gap is 60° (minute hand behind).", "Right angle first when the minute hand is 90° ahead: gain 60 + 90 = 150°",
       f"m = 150 ÷ 5.5 = {mixed(k)} minutes"],
      "Relative speed 5.5°/min", "The minute hand must first cover the 60° gap and then go 90° beyond.", kind="numerical")
    tm = (11 * 60 + 60) - (4 * 60 + 25)
    k = f"{tm // 60}:{tm % 60:02d}"
    q(B, M, "L2", "officer", "The reflection of a wall clock in a vertical mirror shows 4:25. The actual time is:", k,
      [("8:35", "subtracted from 13:00 (12:60) instead of 11:60"), ("7:25", "reflected only the hour hand"), ("4:35", "reflected only the minute hand")],
      ["Actual time = 11:60 − mirror time", "11:60 − 4:25 = 7:35"],
      "Mirror time + actual time = 12:00", "Use 11:60, not 12:60, for subtraction.", kind="numerical")
    k = 720 // 10
    q(B, M, "L3", "officer", "A clock loses 10 minutes every 24 hours. It is set right at noon on a Monday. After how many days will it next show the correct time?",
      f"{k} days", [(f"{1440//10} days", "required a loss of 24 hours instead of 12"), (f"{360//10} days", "required a loss of 6 hours"),
                    (f"{720} days", "took 1 minute lost per day")],
      ["An analogue clock shows the right time again after losing 12 h = 720 min", "720 ÷ 10 = 72 days"],
      "Days = 720 ÷ daily loss (min)", "A 12-hour dial repeats after 12 hours, not 24.", kind="numerical")
    def same_cal(y):
        z = y + 1
        while not (calendar.isleap(z) == calendar.isleap(y) and datetime.date(z, 1, 1).weekday() == datetime.date(y, 1, 1).weekday()):
            z += 1
        return z
    k = same_cal(2023)
    assert k == 2034
    q(B, M, "L3", "officer", "The calendar of 2023 will be repeated next in the year:", k,
      [(2029, "counted 6 years forward without adjusting for leap years"), (2028, "stopped at the next leap year"),
       (2051, "used the 28-year cycle")],
      ["Accumulate odd days from 2023: 1 (2023), 2 (2024 leap), 1, 1, 1, 2 (2028), 1, 1, 1, 2 (2032), 1 (2033)",
       "Total reaches 14 ≡ 0 (mod 7) after 2033, and 2034 is a non-leap year like 2023", "So 2034"],
      "Same calendar ⇔ same 1 January weekday and same leap status", "The leap status must also match.", fmt=str)
    k = DAYS[datetime.date(1950, 1, 26).weekday()]
    q(B, M, "L3", "officer", "On which day of the week did 26 January 1950 fall? (Use the odd-days method.)", k,
      [(DAYS[(datetime.date(1950, 1, 26).weekday() + 1) % 7], "counted 1900 as a leap year"),
       (DAYS[(datetime.date(1950, 1, 26).weekday() - 1) % 7], "took 26 January as 25 odd days instead of 26"),
       (DAYS[(datetime.date(1950, 1, 26).weekday() + 2) % 7], "treated 1949 as having 13 leap years")],
      ["1600 years: 0 odd days; 300 years: 1 odd day (1700, 1800 and 1900 are not leap years)",
       "49 years (1901–1949): 12 leap + 37 ordinary ⇒ 24 + 37 = 61 ≡ 5 odd days",
       "26 January: 26 ≡ 5 odd days", "Total = 0 + 1 + 5 + 5 = 11 ≡ 4 ⇒ Thursday"],
      "Odd days: 0 = Sunday, 1 = Monday, …", "Century years are leap only if divisible by 400.", fmt=str)
    # 1 March Monday non-leap ⇒ 1 Jan
    d0 = [y for y in range(2001, 2100) if not calendar.isleap(y) and datetime.date(y, 3, 1).weekday() == 0][0]
    k = DAYS[datetime.date(d0, 1, 1).weekday()]
    q(B, M, "L2", "officer", "In a non-leap year, 1 March falls on a Monday. On which day did 1 January of that year fall?", k,
      [(DAYS[(0 - 4) % 7], "assumed a leap year (60 days)"), (DAYS[(0 - 5) % 7], "division slip: took 59 ≡ 5 odd days"),
       (DAYS[(0 - 2) % 7], "took January + February as 58 days")],
      ["Days from 1 Jan to 1 Mar = 31 + 28 = 59", "59 ≡ 3 odd days", "Monday − 3 = Friday"],
      "Move back by odd days", "Count backwards when the known date is later.", fmt=str)
    k = angle(10, 15)
    q(B, M, "L3", "officer", "The smaller angle between the hands of a clock at 10:15 is:", k,
      [(360 - k, "gave the reflex angle"), (150, "kept the hour hand fixed at 10"), (F(315, 2), "moved the hour hand backwards")],
      ["θ = |30 × 10 − 5.5 × 15| = |300 − 82.5| = 217.5°", "Smaller angle = 360 − 217.5 = 142.5°"],
      "θ = |30H − 5.5M|; take 360 − θ if θ > 180", "The formula may return the reflex angle.", fmt=dg)
    q(B, M, "L2", "officer", "How many times in a day (24 hours) are the hands of a clock at right angles?", 44,
      [(48, "assumed twice every hour"), (22, "counted for 12 hours only"), (24, "assumed once every hour")],
      ["In 12 hours the hands are at right angles 22 times (twice every hour except 2–4 and 8–10, where one position is shared)",
       "In 24 hours: 44"], "Right angles in 12 h = 22", "Around 3 and 9 o'clock the counts overlap.")
    k = 60 // (2 + 3)
    q(B, M, "L3", "officer", "Two clocks are set right at noon. One gains 2 minutes an hour and the other loses 3 minutes an hour. After how many hours will they differ by exactly one hour?",
      k, [(60 // (3 - 2), "subtracted the rates"), (60 // 2, "used only the gaining clock"), (60 // 3, "used only the losing clock")],
      ["Relative drift = 2 + 3 = 5 min/h", "60 ÷ 5 = 12 hours"], "Time = required gap ÷ relative drift",
      "Gain and loss move in opposite directions, so the rates add.", unit=" hours")


def lcmhcf(B):
    M = "qa-lcm-hcf-and-divisibility-bad12219"
    a = (72, 108, 180)
    k = gcd(gcd(*a[:2]), a[2])
    q(B, M, "L1", "foundation", "The HCF of 72, 108 and 180 is:", k,
      [(lcmm(*a), "found the LCM"), (k // 2, "stopped at a common factor that is not the highest"), (k // 3, "took the HCF of 72 and 180 as 12")],
      ["72 = 2³·3², 108 = 2²·3³, 180 = 2²·3²·5", "HCF = 2²·3² = 36"], "HCF = product of lowest powers of common primes",
      "Every common factor is not the highest common factor.")
    a = (12, 18, 30)
    k = lcmm(*a)
    q(B, M, "L1", "foundation", "The LCM of 12, 18 and 30 is:", k,
      [(gcd(gcd(*a[:2]), a[2]), "found the HCF"), (2 * k, "took an extra factor 2"), (lcmm(12, 18), "left out 30 (LCM of 12 and 18 only)")],
      ["12 = 2²·3, 18 = 2·3², 30 = 2·3·5", "LCM = 2²·3²·5 = 180"], "LCM = product of highest powers", "Use highest powers, not the product.")
    k = lcmm(6, 8, 12)
    q(B, M, "L2", "foundation", "Three bells toll at intervals of 6, 8 and 12 minutes. They toll together at 9:00 a.m. When will they next toll together?",
      f"9:{k:02d} a.m.", [(f"9:{2*k:02d} a.m.", "took twice the LCM"), ("9:12 a.m.", "took the largest interval"), ("9:26 a.m.", "added the intervals")],
      ["LCM(6, 8, 12) = 24", "9:00 + 24 min = 9:24 a.m."], "Next common time = LCM of intervals", "The largest interval is not a common multiple of all.",
      kind="numerical")
    k = 2160 // 12
    q(B, M, "L1", "foundation", "The product of two numbers is 2,160 and their HCF is 12. Their LCM is:", k,
      [(2160 * 12, "multiplied the product by the HCF"), (2160 // 24, "divided by twice the HCF"), (2160 - 12, "subtracted the HCF")],
      ["HCF × LCM = product", "LCM = 2160 ÷ 12 = 180"], "HCF × LCM = a × b", "Divide the product by the HCF.")
    L = lcmm(12, 15, 20)
    k = L + 7
    assert all(k % d == 7 for d in (12, 15, 20))
    q(B, M, "L2", "foundation", "The least number which, when divided by 12, 15 and 20, leaves remainder 7 in each case is:", k,
      [(L, "forgot to add the remainder"), (L - 7, "subtracted the remainder"), (2 * L + 7, "used twice the LCM")],
      ["LCM(12, 15, 20) = 60", "Required number = 60 + 7 = 67"], "N = LCM + common remainder", "The remainder is added to the LCM.")
    # ---- officer ----
    H = 83
    a1, a2 = H * 17 + 9, H * 23 + 11
    k = gcd(a1 - 9, a2 - 11)
    assert k == H and a1 % k == 9 and a2 % k == 11
    q(B, M, "L3", "officer", f"The greatest number that divides {a1} and {a2} leaving remainders 9 and 11 respectively is:", k,
      [(gcd(a1, a2), "took the HCF of the numbers themselves"), (17, "gave the quotient of (1420 − 9) ÷ 83 instead of the divisor"),
       (2 * H, "doubled the HCF (does not divide 1411)")],
      [f"{a1} − 9 = {a1-9} and {a2} − 11 = {a2-11}", f"HCF({a1-9}, {a2-11}) = {k}"],
      "Divisor = HCF(a − r₁, b − r₂)", "Remainders differ, so the difference rule does not apply.")
    H, r = 67, 13
    nums = (H * 20 + r, H * 31 + r, H * 45 + r)
    k = gcd(gcd(nums[1] - nums[0], nums[2] - nums[1]), nums[2] - nums[0])
    assert k == H and len({x % k for x in nums}) == 1
    q(B, M, "L3", "officer", f"The greatest number that divides {nums[0]}, {nums[1]} and {nums[2]} leaving the same remainder in each case is:", k,
      [(gcd(gcd(nums[0], nums[1]), nums[2]), "took the HCF of the numbers"), (r, "gave the common remainder instead of the divisor"),
       (nums[1] - nums[0], "took one difference as the answer")],
      [f"Differences: {nums[1]-nums[0]}, {nums[2]-nums[1]}, {nums[2]-nums[0]}", f"HCF of the differences = {k}"],
      "Same remainder ⇒ divisor = HCF of pairwise differences", "The common remainder cancels in the differences.")
    L = lcmm(6, 9, 15, 18)
    k = next(x for x in range(1, 10000) if all(x % d == 4 for d in (6, 9, 15, 18)) and x % 7 == 0)
    q(B, M, "L3", "officer", "The least number which leaves remainder 4 when divided by 6, 9, 15 and 18, and is exactly divisible by 7, is:", k,
      [(L + 4, "ignored divisibility by 7"), (7 * L + 4, "multiplied the LCM by 7"), (next(x for x in range(L, 10000, L) if x % 7 == 0), "forgot to add the remainder")],
      [f"LCM(6, 9, 15, 18) = {L}", f"Numbers of the form {L}k + 4: 94, 184, 274, 364, …", "First divisible by 7: 364"],
      "N = LCM·k + r, choose k for the extra divisibility", "Check each candidate for divisibility by 7.")
    L = lcmm(12, 15, 18)
    k = 9999 - 9999 % L
    q(B, M, "L2", "officer", "The largest 4-digit number exactly divisible by 12, 15 and 18 is:", k,
      [(9999 - 9999 % 90, "used LCM 90 (dropped a factor 2)"), (k - L, "subtracted one extra LCM"), (9999 - 9999 % 60, "used LCM(12, 15) = 60 and ignored 18")],
      [f"LCM = {L}", f"9999 ÷ {L} leaves {9999 % L}", f"9999 − {9999 % L} = {k}"], "Largest n-digit multiple = 9999 − (9999 mod LCM)",
      "The LCM of 12, 15, 18 is 180, not 90.")
    L = lcmm(8, 12, 20)
    k = next(x for x in range(10000, 20000) if all(x % d == 3 for d in (8, 12, 20)))
    q(B, M, "L3", "officer", "The smallest 5-digit number which leaves remainder 3 when divided by 8, 12 and 20 is:", k,
      [(k - 3, "forgot to add the remainder"), (10003, "added the remainder to 10000"), (k + L, "overshot by one LCM")],
      [f"LCM = {L}", f"Smallest 5-digit multiple of {L} = {k-3}", f"Add 3: {k}"], "N = smallest multiple of LCM ≥ 10000, plus remainder",
      "10000 itself is not a multiple of 120.")
    ds = [d for d in range(10) if int(f"5{d}72463") % 11 == 0]
    assert len(ds) == 1
    d = ds[0]
    q(B, M, "L2", "officer", "What digit must replace * so that the number 5*72463 is divisible by 11?", d,
      [(11 - d if 11 - d < 10 else d + 1, "took the complement of the difference"), ((d + 2) % 10, "added the alternate-digit sums the wrong way"),
       ((d + 5) % 10, "tested divisibility by 3 instead")],
      ["Alternate sums from the right: (3 + 4 + 7 + 5) and (6 + 2 + *)", f"19 − (8 + *) must be 0 or a multiple of 11 ⇒ * = {d}"],
      "Divisible by 11 ⇔ difference of alternate digit sums ≡ 0 (mod 11)", "Start from the units digit when forming alternate sums.")
    k = F(lcmm(2, 4, 5), gcd(gcd(3, 9), 6))
    q(B, M, "L2", "officer", "The LCM of 2/3, 4/9 and 5/6 is:", k,
      [(F(lcmm(2, 4, 5), lcmm(3, 9, 6)), "divided by the LCM of denominators"), (F(1, lcmm(3, 9, 6)), "took HCF of numerators over LCM of denominators"),
       (F(2 * lcmm(2, 4, 5), 3), "doubled the numerator LCM")],
      ["LCM of fractions = LCM(numerators)/HCF(denominators)", "= LCM(2, 4, 5)/HCF(3, 9, 6) = 20/3"],
      "LCM = LCM(num)/HCF(den); HCF = HCF(num)/LCM(den)", "The two formulas are easily swapped.", fmt=fr)
    k = 16 * 480 // 96
    q(B, M, "L2", "officer", "The HCF of two numbers is 16 and their LCM is 480. If one number is 96, the other is:", k,
      [(480 // 16, "divided LCM by HCF"), (480 // 96, "divided LCM by the given number"), (2 * k, "took LCM × HCF ÷ 48")],
      ["Other = HCF × LCM ÷ given = 16 × 480 ÷ 96 = 80"], "a × b = HCF × LCM", "Check: HCF(96, 80) = 16 ✓")
    pairs = [(a, 216 - a) for a in range(1, 109) if gcd(a, 216 - a) == 27]
    k = len(pairs)
    q(B, M, "L3", "officer", "How many pairs of positive integers have sum 216 and HCF 27?", k,
      [(4, "did not require the multipliers to be co-prime"), (8, "counted ordered pairs of all splits of 8"), (1, "found only one pair")],
      ["Numbers 27a and 27b with a + b = 8 and HCF(a, b) = 1", "Co-prime splits of 8: (1, 7), (3, 5)", f"Pairs: {pairs}"],
      "Numbers = H·a, H·b with (a, b) co-prime", "(2, 6) and (4, 4) would raise the HCF above 27.")
    L = lcmm(4, 6, 10)
    k = len([x for x in range(101, 600) if x % L == 0])
    q(B, M, "L2", "officer", "How many numbers between 100 and 600 are divisible by 4, 6 and 10?", k,
      [(len([x for x in range(101, 600) if x % 30 == 0]), "used LCM 30"), (len([x for x in range(101, 600) if x % 240 == 0]), "used the product 240"),
       (k + 1, "included 600")],
      [f"LCM(4, 6, 10) = {L}", f"Multiples between 100 and 600: 120, 180, …, 540 ⇒ {k}"], "Count multiples of the LCM",
      "'Between' excludes 600.")


def series_diff(B):
    M = "qa-number-series-arithmetic-and-difference-patterns-130693e5"
    def mk(start, diffs):
        s = [start]
        for d in diffs:
            s.append(s[-1] + d)
        return s
    items = [
        ("foundation", "L1", 7, [5, 5, 5, 5, 5], "constant difference 5"),
        ("foundation", "L1", 3, [2, 4, 6, 8, 10], "differences 2, 4, 6, 8, …"),
        ("foundation", "L1", 120, [-9, -9, -9, -9], "constant difference −9"),
        ("foundation", "L2", 4, [5, 7, 9, 11, 13], "differences are consecutive odd numbers"),
        ("foundation", "L2", 2, [4, 6, 8, 10, 12], "n(n + 1): differences 4, 6, 8, …"),
        ("officer", "L2", 11, [2, 4, 8, 16, 32], "differences double: 2, 4, 8, 16, …"),
        ("officer", "L3", 5, [1, 8, 27, 64, 125], "differences are cubes 1³, 2³, 3³, …"),
        ("officer", "L3", 8, [4, 9, 16, 25, 36], "differences are squares 2², 3², 4², …"),
        ("officer", "L3", 17, [2, 3, 5, 7, 11, 13], "differences are consecutive primes"),
        ("officer", "L3", 6, [4, 8, 14, 22, 32], "second differences 4, 6, 8, 10 (increasing by 2)"),
        ("officer", "L2", 250, [10, 20, 30, 40, 50], "differences 10, 20, 30, …"),
        ("officer", "L3", 20, [3, -4, 5, -6, 7], "differences alternate in sign: +3, −4, +5, −6, …"),
        ("officer", "L3", 2, [1, 4, 9, 16, 25], "differences are squares 1², 2², 3², …"),
        ("officer", "L3", 4, [1, 3, 6, 10, 15], "differences are triangular numbers 1, 3, 6, 10, …"),
    ]
    for tier, lv, st, diffs, rule in items:
        s = mk(st, diffs)
        shown, key = s[:-1], s[-1]
        nd = diffs[-1]
        cands = [(shown[-1] + diffs[-2], "assumed the last difference repeats"),
                 (key + (nd + (nd - diffs[-2])), "computed one term too far"),
                 (key + 1 if nd > 0 else key - 1, "arithmetic slip in the next difference"),
                 (key - 2, "arithmetic slip in the last difference"), (key + 2, "arithmetic slip in the last difference")]
        q(B, M, lv, tier, f"Find the next term: {', '.join(sn(x) for x in shown)}, ?", key, cands,
          [f"Differences: {', '.join(n(d) for d in diffs[:-1])}", f"Pattern: {rule}", f"Next difference = {n(nd)} ⇒ {n(shown[-1])} + ({n(nd)}) = {n(key)}"],
          "Take successive differences until a pattern appears", "Check the pattern on every difference, not just the last two.")
    # missing middle term
    s = mk(9, [6, 9, 12, 15, 18])
    key = s[2]
    shown = [n(x) for x in s]
    shown[2] = "?"
    q(B, M, "L3", "officer", f"Find the missing term: {', '.join(shown)}", key,
      [(s[1] + 8, "assumed the differences rise by 2"), (s[1] + 12, "used the difference of the following gap"), (F(s[1] + s[3], 2), "took the average of the neighbours")],
      [f"Differences around the gap must be 9 and 12 (sequence of differences 6, 9, 12, 15, 18)", f"? = 15 + 9 = {key}; check 24 + 12 = 36 ✓"],
      "Second differences constant (3)", "Verify the value against both neighbours.")


def series_mult(B):
    M = "qa-number-series-multiplicative-and-mixed-patterns-340f34bd"
    def gen(start, fns, k):
        s = [start]
        for i in range(k):
            s.append(fns(i, s[-1]))
        return s
    items = [
        ("foundation", "L1", 3, lambda i, x: x * 2, "each term × 2", [(lambda s: s[-2] + s[-3], "added the previous two terms"), (lambda s: s[-2] + 48, "used a constant difference")]),
        ("foundation", "L1", 2, lambda i, x: 2 * x + 1, "× 2 + 1", [(lambda s: 2 * s[-2], "missed the +1"), (lambda s: 2 * s[-2] + 3, "used + 3")]),
        ("foundation", "L2", 1, lambda i, x: x * (i + 2), "× 2, × 3, × 4, … (factorials)", [(lambda s: s[-2] * 5, "repeated the last multiplier"), (lambda s: s[-2] * 7, "skipped a multiplier")]),
        ("foundation", "L2", 5, lambda i, x: x * (i + 2), "× 2, × 3, × 4, × 5, …", [(lambda s: s[-2] * 5, "repeated the last multiplier"), (lambda s: s[-2] + 600, "treated it as additive")]),
        ("foundation", "L1", 729, lambda i, x: F(x, 3), "each term ÷ 3", [(lambda s: F(s[-2], 9), "divided by 9"), (lambda s: s[-2] - 6, "used a difference of −6")]),
        ("officer", "L3", 7, lambda i, x: x * (i + 2) + (i + 1), "× 2 + 1, × 3 + 2, × 4 + 3, …", [(lambda s: s[-2] * 6 + 4, "kept the previous addend"), (lambda s: s[-2] * 5 + 5, "kept the previous multiplier")]),
        ("officer", "L3", 4, lambda i, x: x * (i + 1) + (i + 1), "× 1 + 1, × 2 + 2, × 3 + 3, …", [(lambda s: s[-2] * 5 + 4, "addend lagged by one"), (lambda s: s[-2] * 4 + 5, "multiplier lagged by one")]),
        ("officer", "L3", 6, lambda i, x: x * F(i + 1, 2), "× 0.5, × 1, × 1.5, × 2, …", [(lambda s: s[-2] * 2, "repeated the last multiplier"), (lambda s: s[-2] * 3, "jumped the multiplier by 1")]),
        ("officer", "L3", 3, lambda i, x: x * (i + 1) - (i + 1), "× 1 − 1, × 2 − 2, × 3 − 3, …", [(lambda s: s[-2] * 5, "missed the subtraction"), (lambda s: s[-2] * 5 - 4, "subtracted the previous step's number")]),
        ("officer", "L3", 16, lambda i, x: x * F(3, 2), "each term × 1.5", [(lambda s: s[-2] + 27 + 13.5, "added the growing difference incorrectly"), (lambda s: s[-2] * 2 - 40, "used × 2 − constant")]),
        ("officer", "L3", 10, lambda i, x: 2 * x - 2 * (i + 1), "× 2 − 2, × 2 − 4, × 2 − 6, …", [(lambda s: 2 * s[-2] - 6, "kept the previous subtraction"), (lambda s: 2 * s[-2], "missed the subtraction")]),
        ("officer", "L3", 3360, lambda i, x: F(x, 5 - i), "÷ 5, ÷ 4, ÷ 3, ÷ 2, ÷ 1", [(lambda s: F(s[-2], 2), "repeated ÷ 2"), (lambda s: 14, "continued with ÷ 2 twice")]),
    ]
    nterms = {3360: 5}
    for tier, lv, st, fn, rule, extra in items:
        s = gen(st, fn, nterms.get(st, 5))
        shown, key = s[:-1], s[-1]
        cands = [(f(s), e) for f, e in extra] + [(key + 1, "arithmetic slip"), (key - 1, "arithmetic slip")]
        q(B, M, lv, tier, f"Find the next term: {', '.join(sn(x) for x in shown)}, ?", key, cands,
          [f"Rule: {rule}", "Check: " + ", ".join(f"{n(shown[i])} → {n(s[i+1])}" for i in range(len(shown))) , f"Next term = {n(key)}"],
          "Test ratios and 'multiply then add' rules when differences grow fast", "Verify the rule on every step, including the first.")
    # interleaved / alternating
    s = [4]
    for i in range(5):
        s.append(s[-1] * 2 if i % 2 == 0 else s[-1] + 3)
    assert s[-1] == 50
    shown, key = s[:-1], s[-1]
    q(B, M, "L2", "officer", f"Find the next term: {', '.join(sn(x) for x in shown)}, ?", key,
      [(shown[-1] + 3, "applied +3 again"), (shown[-1] * 2 + 3, "applied both operations"), (shown[-1] + 11, "repeated the earlier jump of +11")],
      ["Operations alternate: × 2, + 3, × 2, + 3, …", f"Next: {shown[-1]} × 2 = {key}"], "Alternating operations", "Track which operation comes next.")
    odd = [3, 6, 12, 24]; even = [10, 20, 40]
    s = [x for pair in zip(odd, even + [None]) for x in pair if x is not None]
    shown, key = s[:-1], s[-1]
    q(B, M, "L3", "officer", f"Find the next term: {', '.join(sn(x) for x in shown)}, ?", key,
      [(80, "continued the even-position series"), (21, "read the odd positions as +3, +6, +9"), (shown[-1] - 28, "used alternating differences")],
      ["Two interleaved series: 3, 6, 12, … and 10, 20, 40, …", "Next term belongs to the first series: 12 × 2 = 24"],
      "Split into odd and even positions", "Check which sub-series the missing position belongs to.")
    s = [m ** 3 - m for m in range(1, 8)]
    shown, key = s[:-1], s[-1]
    q(B, M, "L3", "officer", f"Find the next term: {', '.join(sn(x) for x in shown)}, ?", key,
      [(7 ** 3, "used n³"), (7 ** 3 - 1, "used n³ − 1"), (shown[-1] + 60 + 30, "used second differences incorrectly")],
      ["Terms = n³ − n: 0, 6, 24, 60, 120, 210", "Next (n = 7): 343 − 7 = 336"], "Terms of the form n³ − n", "Spot the cubes hidden inside each term.")


def wrong_term(B):
    M = "qa-wrong-term-series-af3f2c81"
    items = [
        ("foundation", "L1", [5, 12, 19, 26, 33, 40, 47], 3, 2, "constant difference 7"),
        ("foundation", "L1", [m * m for m in range(2, 9)], 4, 1, "squares 2², 3², …"),
        ("foundation", "L2", [3 * 2 ** i for i in range(7)], 5, -8, "each term × 2"),
        ("foundation", "L2", [m * m + 1 for m in range(1, 8)], 2, 1, "n² + 1"),
        ("foundation", "L2", [2, 5, 11, 20, 32, 47, 65], 4, 2, "differences 3, 6, 9, 12, …"),
        ("officer", "L3", [5, 6, 14, 41, 105, 230, 446], 3, 2, "differences are cubes 1³, 2³, 3³, …"),
        ("officer", "L3", [4, 9, 19, 39, 79, 159, 319], 4, -2, "× 2 + 1"),
        ("officer", "L3", [4, 5, 12, 39, 160, 805, 4836], 3, 3, "× 1 + 1, × 2 + 2, × 3 + 3, …"),
        ("officer", "L3", [17, 19, 22, 27, 34, 45, 58], 2, 1, "differences are consecutive primes 2, 3, 5, 7, 11, 13"),
        ("officer", "L3", [6, 10, 18, 32, 54, 86, 130], 4, 2, "second differences 4, 6, 8, 10, 12"),
        ("officer", "L3", [7200, 1440, 360, 120, 60, 60], 2, 20, "÷ 5, ÷ 4, ÷ 3, ÷ 2, ÷ 1"),
        ("officer", "L3", [m ** 3 - 1 for m in range(2, 9)], 5, 2, "n³ − 1"),
        ("officer", "L3", [16, 24, 36, 54, 81, F(243, 2), F(729, 4)], 3, 2, "each term × 1.5"),
    ]
    ask_fix = {10, 11, 12}  # indices (0-based within officer list positions) asking for the correct value
    for idx, (tier, lv, s, pos, delta, rule) in enumerate(items):
        shown = list(s)
        shown[pos] = s[pos] + delta
        others = [i for i in range(len(s)) if i != pos]
        near = sorted(others, key=lambda i: abs(i - pos))[:3]
        if idx in ask_fix:
            key = s[pos]
            cands = [(shown[pos], "the wrong term itself"), (s[pos] + 2 * delta, "corrected in the wrong direction"),
                     (s[pos] - delta if s[pos] - delta != shown[pos] else s[pos] + 3 * delta, "over-corrected"), (s[pos] + 1, "arithmetic slip")]
            q(B, M, lv, tier, f"In the series {', '.join(sn(x) for x in shown)}, one term is wrong. What should replace it?", key, cands,
              [f"Pattern: {rule}", f"The term {n(shown[pos])} breaks the pattern", f"Correct value = {n(s[pos])}"],
              "Identify the rule from the majority of terms", "Confirm the replacement also fits the next step.")
        else:
            key = shown[pos]
            cands = [(shown[i], "this term fits the pattern") for i in near]
            q(B, M, lv, tier, f"Find the wrong term in the series: {', '.join(sn(x) for x in shown)}", key, cands,
              [f"Pattern: {rule}", f"Expected term in position {pos+1}: {n(s[pos])}", f"Given {n(shown[pos])} ⇒ wrong term"],
              "Test the rule on each consecutive pair", "A wrong term disturbs two differences; the common neighbour of both is the culprit.")
    # extra officer item: interleaved
    s = [2, 15, 4, 12, 8, 9, 16, 6]
    shown = list(s); shown[5] = 10
    q(B, M, "L3", "officer", f"Find the wrong term in the series: {', '.join(sn(x) for x in shown)}", 10,
      [(8, "this term fits the pattern (odd positions × 2)"), (16, "this term fits the pattern"), (12, "this term fits the pattern (even positions − 3)")],
      ["Odd positions: 2, 4, 8, 16 (× 2)", "Even positions: 15, 12, 9, 6 (− 3)", "10 should be 9"],
      "Split interleaved series", "Treat alternate positions as separate series.")
    s = [3, 7, 15, 31, 63, 127, 255]
    shown = list(s); shown[3] = 32
    q(B, M, "L3", "officer", f"In the series {', '.join(sn(x) for x in shown)}, one term is wrong. What should replace it?", 31,
      [(32, "the wrong term itself"), (33, "corrected in the wrong direction"), (30, "over-corrected")],
      ["Rule: × 2 + 1", "15 × 2 + 1 = 31, and 31 × 2 + 1 = 63 ✓"], "× 2 + 1 (2ⁿ − 1)", "Check the correction against the next term too.")


def pnc(B):
    M = "permutations-and-combinations"
    q(B, M, "L1", "foundation", "In how many ways can the letters of the word MANGO be arranged?", factorial(5),
      [(factorial(4), "fixed one letter"), (factorial(5) // 2, "divided by 2 as if a letter repeated"), (25, "used 5²")],
      ["All 5 letters distinct ⇒ 5! = 120"], "n distinct objects: n!", "No letter repeats in MANGO.")
    q(B, M, "L1", "foundation", "In a meeting of 12 people, each shakes hands with every other exactly once. The number of handshakes is:", comb(12, 2),
      [(perm(12, 2), "counted ordered pairs"), (144, "used 12²"), (comb(13, 2), "used 13 people")],
      ["Handshakes = C(12, 2) = 12 × 11 / 2 = 66"], "nC2", "A handshake between A and B is the same as between B and A.")
    q(B, M, "L1", "foundation", "In how many ways can a committee of 3 be chosen from 8 people?", comb(8, 3),
      [(perm(8, 3), "used permutations"), (8 * 3, "multiplied 8 × 3"), (8 ** 3, "used 8³")],
      ["C(8, 3) = 8 × 7 × 6 / 6 = 56"], "nCr = n!/(r!(n − r)!)", "Order does not matter in a committee.")
    k = factorial(6) // (2 * 2)
    assert k == len(set(itertools.permutations("LETTER")))
    q(B, M, "L2", "foundation", "In how many distinct ways can the letters of the word LETTER be arranged?", k,
      [(factorial(6), "ignored repeated letters"), (factorial(6) // 2, "adjusted for only one repeated letter"), (factorial(6) // 8, "divided by 2! three times")],
      ["LETTER: L, E×2, T×2, R", "6!/(2! × 2!) = 720/4 = 180"], "n!/(p! q! …)", "Both E and T repeat.")
    q(B, M, "L2", "foundation", "The number of diagonals of a decagon (10 sides) is:", 10 * 7 // 2,
      [(comb(10, 2), "counted all line segments including sides"), (10 * 7, "forgot to halve"), (comb(10, 2) - 5, "subtracted half the sides")],
      ["Diagonals = n(n − 3)/2 = 10 × 7 / 2 = 35"], "n(n − 3)/2", "Sides are also segments joining two vertices; exclude them.")
    # ---- officer ----
    word = "ARRANGE"
    tot = set(itertools.permutations(word))
    k = sum(1 for p in tot if "RR" in "".join(p))
    assert k == factorial(6) // 2
    q(B, M, "L3", "officer", "In how many arrangements of the letters of ARRANGE do the two R's come together?", k,
      [(factorial(6), "did not divide for the two A's"), (len(tot), "counted all arrangements"), (k // 2, "divided by 2 again for the R block")],
      ["Treat RR as one unit: units A, A, RR, N, G, E (6 units, A repeated)", "6!/2! = 360"],
      "Glue method: block counted as one unit", "The two A's still repeat.")
    men, women = 6, 4
    k = sum(comb(women, w) * comb(men, 5 - w) for w in range(2, 5))
    assert k == sum(1 for c in itertools.combinations(range(10), 5) if sum(1 for i in c if i < 4) >= 2)
    q(B, M, "L3", "officer", "A committee of 5 is to be formed from 6 men and 4 women with at least 2 women. In how many ways can this be done?", k,
      [(comb(4, 2) * comb(6, 3), "counted exactly 2 women only"), (comb(10, 5) - comb(6, 5), "counted at least 1 woman"),
       (comb(4, 2) * comb(8, 3), "chose 2 women then any 3 of the rest (overcounting)")],
      ["2W 3M: 6 × 20 = 120", "3W 2M: 4 × 15 = 60", "4W 1M: 1 × 6 = 6", "Total = 186"],
      "Split 'at least' into exact cases", "Choosing 2 women first and then 3 from the rest double-counts.")
    k = sum(1 for p in itertools.permutations("012345", 4) if p[0] != "0" and p[-1] in "05")
    q(B, M, "L3", "officer", "How many 4-digit numbers divisible by 5 can be formed from the digits 0, 1, 2, 3, 4, 5 without repetition?", k,
      [(2 * perm(5, 3), "treated 0 like any other leading digit"), (perm(5, 3), "counted only numbers ending in 0"),
       (sum(1 for p in itertools.permutations("012345", 4) if p[0] != "0"), "counted all 4-digit numbers")],
      ["Ending in 0: 5 × 4 × 3 = 60", "Ending in 5: first digit from 4 non-zero (excluding 5) × 4 × 3 = 48", "Total = 108"],
      "Case split on the last digit", "When the last digit is 5, the first digit cannot be 0.")
    people = range(7)
    def circ():
        c = 0
        for p in itertools.permutations(range(1, 7)):
            ring = (0,) + p
            adj = any({ring[i], ring[(i + 1) % 7]} == {0, 1} for i in range(7))
            c += not adj
        return c
    k = circ()
    q(B, M, "L3", "officer", "In how many ways can 7 people sit around a round table if two particular people must not sit next to each other?", k,
      [(factorial(6), "ignored the restriction"), (2 * factorial(5), "counted arrangements where they sit together"),
       (factorial(7) - 2 * factorial(6), "used linear arrangements")],
      ["Total circular = 6! = 720", "Together: 5! × 2 = 240", "Not together = 720 − 240 = 480"],
      "Circular: (n − 1)!", "Use (n − 1)! for both total and 'together' cases.")
    k = factorial(4) * factorial(5)
    q(B, M, "L3", "officer", "In how many ways can the letters of EQUATION be arranged so that all the vowels come together?", k,
      [(factorial(4), "did not arrange the vowels inside the block"), (factorial(5) * factorial(3), "used 3! for the outer arrangement"),
       (factorial(8), "ignored the condition")],
      ["Vowels E, U, A, I, O (5) form one block; consonants Q, T, N", "Units: block + 3 consonants = 4 ⇒ 4!", "Inside the block: 5!", "Total = 24 × 120 = 2880"],
      "Block × internal arrangements", "Count the block as one unit among the consonants.")
    k = comb(5, 2) * comb(7, 2)
    q(B, M, "L3", "officer", "How many rectangles (of all sizes) are there in a grid of 4 rows × 6 columns of unit squares?", k,
      [(4 * 6, "counted only unit squares"), (comb(5, 2) + comb(7, 2), "added the line choices"), (comb(11, 4), "chose 4 of all 11 lines")],
      ["A rectangle needs 2 of the 5 horizontal lines and 2 of the 7 vertical lines", "C(5, 2) × C(7, 2) = 10 × 21 = 210"],
      "Rectangles = C(m + 1, 2) × C(n + 1, 2)", "Choose lines, not squares.")
    k = comb(8, 3)
    q(B, M, "L2", "officer", "Moving only right or up one unit at a time, how many shortest paths lead from (0, 0) to (5, 3)?", k,
      [(5 * 3, "multiplied the coordinates"), (perm(8, 3), "used permutations"), (comb(8, 2), "chose 2 instead of 3")],
      ["Any path = 5 R and 3 U in some order", "C(8, 3) = 56"], "Lattice paths = C(a + b, a)", "The path is a word of R's and U's.")
    k = comb(12, 3) - comb(6, 3)
    q(B, M, "L2", "officer", "Out of 12 points in a plane, exactly 6 are collinear and no other three are collinear. How many triangles can be formed?", k,
      [(comb(12, 3), "did not remove collinear triples"), (comb(12, 3) - comb(6, 2), "subtracted C(6, 2)"), (comb(6, 3) + comb(6, 2) * 6, "missed triangles using two of the collinear points")],
      ["All triples: C(12, 3) = 220", "Collinear triples: C(6, 3) = 20", "Triangles = 200"],
      "C(n, 3) − C(k, 3)", "Only triples entirely within the collinear set fail.")
    k = factorial(6) * comb(7, 4) * factorial(4)
    q(B, M, "L3", "officer", "In how many ways can 6 boys and 4 girls stand in a row so that no two girls are adjacent?", k,
      [(factorial(6) * comb(7, 4), "did not arrange the girls"), (factorial(6) * comb(5, 4) * factorial(4), "used only the 5 interior gaps"),
       (factorial(6) * factorial(4), "did not choose gaps")],
      ["Arrange boys: 6! = 720; they create 7 gaps", "Choose 4 gaps and arrange girls: C(7, 4) × 4! = 840", "Total = 720 × 840 = 6,04,800"],
      "Gap method", "The two end gaps are also available.")
    k = (3 + 1) * (4 + 1) * (2 + 1) - 1
    q(B, M, "L3", "officer", "From 3 identical apples, 4 identical bananas and 2 identical mangoes, in how many ways can at least one fruit be selected?", k,
      [(k + 1, "included the empty selection"), (2 ** 9 - 1, "treated the fruits as distinct"), (3 * 4 * 2 - 1, "used counts instead of (count + 1)")],
      ["Choices: apples 0–3 (4 ways), bananas 0–4 (5), mangoes 0–2 (3)", "Total = 4 × 5 × 3 = 60, minus the empty selection = 59"],
      "(p + 1)(q + 1)(r + 1) − 1", "Identical items: choose how many, not which.")


def remainders(B):
    M = "qa-remainders-and-factors-0faad1db"
    nd = lambda x: sum(1 for d in range(1, x + 1) if x % d == 0)
    k = nd(360)
    q(B, M, "L1", "foundation", "The number of factors (divisors) of 360 is:", k,
      [(3 * 2 * 1, "multiplied the exponents without adding 1"), (k - 2, "excluded 1 and the number itself"), (4 * 3, "missed the prime factor 5")],
      ["360 = 2³ × 3² × 5", "Number of factors = (3 + 1)(2 + 1)(1 + 1) = 24"], "(a + 1)(b + 1)(c + 1)…", "Add 1 to every exponent.")
    k = pow(2, 10, 7)
    q(B, M, "L1", "foundation", "The remainder when 2¹⁰ is divided by 7 is:", k,
      [(1, "assumed 2¹⁰ ≡ 1 because 2³ ≡ 1 (misapplied cycle)"), (4, "took 2¹⁰ ≡ 2² (wrong cycle position)"), (3, "divided 10 by 7")],
      ["2³ = 8 ≡ 1 (mod 7)", "2¹⁰ = (2³)³ × 2 ≡ 1 × 2 = 2"], "Use a power that is ≡ 1", "10 = 3 × 3 + 1, so one factor of 2 remains.")
    k = 29 % 8
    q(B, M, "L2", "foundation", "A number leaves remainder 29 when divided by 56. What remainder does it leave when divided by 8?", k,
      [(29, "kept the same remainder"), (56 % 29 % 8 if 56 % 29 % 8 != k else 3, "divided 56 by 29"), (1, "divided 29 by 7")],
      ["N = 56q + 29; 56 is a multiple of 8", "Remainder = 29 mod 8 = 5"], "If d | D, remainder mod d = (remainder mod D) mod d",
      "Only works because 8 divides 56.")
    tz = lambda m: sum(m // 5 ** i for i in range(1, 6))
    k = tz(100)
    q(B, M, "L2", "foundation", "How many zeros are there at the end of 100! ?", k,
      [(100 // 5, "counted only multiples of 5"), (100 // 4, "counted multiples of 4"), (100 // 10, "counted multiples of 10 only")],
      ["Zeros = ⌊100/5⌋ + ⌊100/25⌋ = 20 + 4 = 24"], "Σ⌊n/5ᵏ⌋", "Multiples of 25 contribute an extra 5.")
    k = (7 * 11 * 13 * 17) % 5
    q(B, M, "L1", "foundation", "The remainder when 7 × 11 × 13 × 17 is divided by 5 is:", k,
      [((7 + 11 + 13 + 17) % 5, "added instead of multiplied"), ((2 * 1 * 3 * 2) , "multiplied remainders without reducing"), (1, "assumed product of odd numbers ≡ 1")],
      ["Remainders: 7→2, 11→1, 13→3, 17→2", "2 × 1 × 3 × 2 = 12 ≡ 2 (mod 5)"], "Remainder of product = product of remainders (mod d)",
      "Reduce the final product too.")
    # ---- officer ----
    N = 540
    sig = sum(d for d in range(1, N + 1) if N % d == 0)
    q(B, M, "L3", "officer", "The sum of all the factors of 540 is:", sig,
      [(sig - N, "excluded the number itself"), (nd(N), "gave the number of factors"), ((1 + 2 + 4) * (1 + 3 + 9 + 27), "missed the prime 5")],
      ["540 = 2² × 3³ × 5", "Sum = (1 + 2 + 4)(1 + 3 + 9 + 27)(1 + 5) = 7 × 40 × 6 = 1680"], "σ(n) = Π(1 + p + … + pᵃ)",
      "Include every prime factor in the product.")
    N = 1080
    k = sum(1 for d in range(1, N + 1) if N % d == 0 and d % 2)
    q(B, M, "L3", "officer", "How many odd factors does 1080 have?", k,
      [(nd(N), "gave the total number of factors"), (nd(N) - k, "gave the number of even factors"), (k * 2, "included one power of 2")],
      ["1080 = 2³ × 3³ × 5", "Odd factors ignore the 2's: (3 + 1)(1 + 1) = 8"], "Odd factors = product over odd primes of (a + 1)",
      "Drop the power of 2 entirely.")
    k = pow(3, 100, 7)
    q(B, M, "L3", "officer", "The remainder when 3¹⁰⁰ is divided by 7 is:", k,
      [(pow(3, 100 % 3, 7) if pow(3, 100 % 3, 7) != k else 5, "assumed a cycle of length 3"), (pow(3, 2, 7), "reduced the exponent as 100 ≡ 2 (mod 6) — division slip"), (1, "assumed 3¹⁰⁰ ≡ 1")],
      ["3⁶ ≡ 1 (mod 7) (Fermat)", "100 = 6 × 16 + 4 ⇒ 3¹⁰⁰ ≡ 3⁴ = 81 ≡ 4"], "aᵖ⁻¹ ≡ 1 (mod p)", "The cycle of 3 mod 7 has length 6.")
    hp = lambda nn, p: sum(nn // p ** i for i in range(1, 10))
    k = hp(500, 7)
    q(B, M, "L3", "officer", "The highest power of 7 that divides 500! is:", k,
      [(500 // 7, "counted only multiples of 7"), (500 // 7 + 500 // 49, "missed multiples of 343"), (k + 1, "added an extra 1 for 7 itself")],
      ["⌊500/7⌋ + ⌊500/49⌋ + ⌊500/343⌋ = 71 + 10 + 1 = 82"], "Legendre: Σ⌊n/pᵏ⌋", "Keep dividing until the power exceeds n.")
    k = pow(2, 31, 5)
    q(B, M, "L2", "officer", "The remainder when 2³¹ is divided by 5 is:", k,
      [(pow(2, 1, 5), "took 31 ≡ 1 in the exponent"), (1, "assumed 2³¹ ≡ 1 because 2⁴ ≡ 1"), (4, "used 2² ≡ −1 with an odd count of pairs")],
      ["2⁴ ≡ 1 (mod 5)", "31 = 4 × 7 + 3 ⇒ 2³¹ ≡ 2³ = 8 ≡ 3"], "Cyclicity of remainders", "Reduce the exponent mod the cycle length.")
    k = (3 * 3) % 5
    q(B, M, "L2", "officer", "When a number N is divided by 5 the remainder is 3. What is the remainder when N² is divided by 5?", k,
      [(3, "kept the same remainder"), (9, "did not reduce 3² mod 5"), (1, "assumed squares leave remainder 1")],
      ["N = 5q + 3 ⇒ N² ≡ 3² = 9 ≡ 4 (mod 5)"], "(a mod m)² mod m", "Reduce 9 modulo 5.")
    k = sum(factorial(i) for i in range(1, 51)) % 12
    q(B, M, "L3", "officer", "The remainder when 1! + 2! + 3! + … + 50! is divided by 12 is:", k,
      [((1 + 2) % 12, "assumed 3! onwards is divisible by 12"), (0, "assumed every term is divisible by 12"), (1 + 2 + 6 + 24, "added 4! without reducing")],
      ["From 4! = 24 onward every term is divisible by 12", "1 + 2 + 6 = 9 ⇒ remainder 9"], "Terms ≥ k! vanish mod m when m | k!",
      "3! = 6 is not divisible by 12.")
    N = 2 ** 4 * 3 ** 3 * 5 ** 2
    k = sum(1 for d in range(1, N + 1) if N % d == 0 and math.isqrt(d) ** 2 == d)
    q(B, M, "L3", "officer", f"How many factors of 2⁴ × 3³ × 5² are perfect squares?", k,
      [(5 * 4 * 3, "gave the total number of factors"), (2 * 1 * 1, "did not count exponent 0"), (3 * 3 * 2, "rounded 3/2 up for the prime 3")],
      ["Square factor needs even exponents", "2: {0, 2, 4} (3 ways); 3: {0, 2} (2 ways); 5: {0, 2} (2 ways)", "3 × 2 × 2 = 12"],
      "Count even exponents for each prime", "Exponent 0 is even and must be counted.")
    k = 6
    assert math.isqrt(1350 * k) ** 2 == 1350 * k and all(math.isqrt(1350 * j) ** 2 != 1350 * j for j in range(1, k))
    q(B, M, "L2", "officer", "The smallest number by which 1350 must be multiplied to make it a perfect square is:", k,
      [(2, "fixed only the power of 2"), (3, "fixed only the power of 3"), (15, "multiplied by 3 × 5 (misread 5² as 5¹)")],
      ["1350 = 2 × 3³ × 5²", "Make exponents even: need 2¹ × 3¹ = 6"], "Pair up prime exponents", "5² is already a square.")
    Nq = [x for x in range(1, 500) if x % 7 == 4 and (x // 7) % 5 == 3]
    k = Nq[0] % 35
    assert all(x % 35 == k for x in Nq)
    q(B, M, "L3", "officer", "A number when divided by 7 leaves remainder 4, and the quotient so obtained when divided by 5 leaves remainder 3. What is the remainder when the number is divided by 35?", k,
      [(4 + 3, "added the two remainders"), (4 * 3, "multiplied the remainders"), (7 * 3, "forgot to add the first remainder")],
      ["N = 7q + 4, q = 5k + 3", "N = 7(5k + 3) + 4 = 35k + 25", "Remainder = 25"], "Successive division: r = d₁r₂ + r₁", "Multiply the second remainder by the first divisor, then add.")


def consecutive(B):
    M = "qa-sets-of-consecutive-and-patterned-numbers-57029c73"
    mid = 96 // 3
    q(B, M, "L1", "foundation", "The sum of three consecutive even numbers is 96. The largest of them is:", mid + 2,
      [(mid, "gave the middle number"), (mid - 2, "gave the smallest"), (mid + 4, "stepped by 4")],
      ["Middle = 96/3 = 32", "Numbers: 30, 32, 34 ⇒ largest 34"], "Middle = sum ÷ count", "Consecutive even numbers differ by 2.")
    q(B, M, "L1", "foundation", "The average of five consecutive odd numbers is 27. The smallest of them is:", 27 - 4,
      [(27 - 2, "stepped back only once"), (27 - 6, "stepped back three times"), (27 - 8, "stepped back 4 × 2 from the wrong term")],
      ["Average = middle term = 27", "Smallest = 27 − 2 × 2 = 23"], "Middle term = average (odd count)", "Two steps of 2 below the middle.")
    q(B, M, "L1", "foundation", "The sum of the first 20 odd natural numbers is:", 20 ** 2,
      [(20 * 21, "used n(n + 1)"), (20 * 21 // 2, "used the natural-number formula"), (21 ** 2, "used (n + 1)²")],
      ["Sum of first n odd numbers = n²", "20² = 400"], "1 + 3 + … + (2n − 1) = n²", "Not n(n + 1) — that is for even numbers.")
    q(B, M, "L1", "foundation", "The sum of the first 25 natural numbers is:", 25 * 26 // 2,
      [(25 ** 2, "used n²"), (25 * 24 // 2, "used n(n − 1)/2"), (25 * 26, "forgot to halve")],
      ["n(n + 1)/2 = 25 × 26 / 2 = 325"], "Σn = n(n + 1)/2", "Halve the product.")
    k = len([x for x in range(101, 300) if x % 7 == 0])
    q(B, M, "L2", "foundation", "How many multiples of 7 lie between 100 and 300?", k,
      [(k + 1, "counted one extra end term"), (k - 1, "dropped an end term"), (300 // 7, "counted all multiples of 7 up to 300 (forgot to remove those below 100)")],
      ["First = 105, last = 294", "Count = (294 − 105)/7 + 1 = 28"], "Count = (last − first)/d + 1", "Remember the +1 for inclusive counting.")
    # ---- officer ----
    ms = [x for x in range(10, 100) if x % 6 == 0]
    k = sum(ms)
    q(B, M, "L2", "officer", "The sum of all two-digit multiples of 6 is:", k,
      [(k + 6, "included 6"), (k - 96, "excluded 96"), (len(ms) * 96, "multiplied the count by the last term")],
      [f"Terms: 12, 18, …, 96 ⇒ {len(ms)} terms", f"Sum = {len(ms)} × (12 + 96)/2 = {k}"], "AP sum = n(a + l)/2", "6 is a one-digit number.")
    k = [m for m in range(1, 100, 2) if m * (m + 2) == 323][0] + 2
    q(B, M, "L2", "officer", "The product of two consecutive odd numbers is 323. The larger number is:", k,
      [(k - 2, "gave the smaller number"), (k + 2, "stepped one odd number too far"), (18, "took √323 rounded")],
      ["√323 ≈ 17.97 ⇒ numbers are 17 and 19", "17 × 19 = 323 ✓ ⇒ larger 19"], "n(n + 2) = P", "Consecutive odd numbers differ by 2.")
    k = 15 * 16 * 31 // 6
    q(B, M, "L2", "officer", "The value of 1² + 2² + 3² + … + 15² is:", k,
      [(15 * 16 * 31 // 3, "divided by 3 instead of 6"), ((15 * 16 // 2) ** 2, "used the sum-of-cubes formula"), (14 * 15 * 29 // 6, "summed only up to 14")],
      ["Σn² = n(n + 1)(2n + 1)/6", "= 15 × 16 × 31 / 6 = 1240"], "Σn² = n(n + 1)(2n + 1)/6", "(Σn)² is the sum of cubes, not squares.")
    k = 115 + 25
    assert sum(range(21, 26)) == 115 and sum(range(26, 31)) == k
    q(B, M, "L3", "officer", "The sum of five consecutive integers is 115. What is the sum of the next five consecutive integers?", k,
      [(115 + 5, "added 1 per term instead of 5"), (2 * 115, "doubled the sum"), (115 + 10, "added 2 per term")],
      ["Each of the next five integers is 5 more than its counterpart", "Sum increases by 5 × 5 = 25 ⇒ 140"], "Shift each term by the block length",
      "Each term moves 5 places, not 1.")
    k = F(sum(range(2, 101, 2)), 50)
    q(B, M, "L2", "officer", "The average of the first 50 even natural numbers is:", k,
      [(50, "took the count as the average"), (F(sum(range(2, 101, 2)), 49), "divided by 49"), (F(51, 2), "used the natural-number average")],
      ["Sum = n(n + 1) = 50 × 51 = 2550", "Average = 2550/50 = 51"], "Average of first n even numbers = n + 1", "It is n + 1, not n.")
    tr = [m for m in range(1, 100) if m * m + (m + 1) ** 2 + (m + 2) ** 2 == 434]
    k = 3 * tr[0] + 3
    q(B, M, "L3", "officer", "The sum of the squares of three consecutive natural numbers is 434. The sum of the numbers is:", k,
      [(k - 3, "used 10, 11, 12"), (k + 3, "used 12, 13, 14"), (tr[0] + 1, "gave the middle number")],
      ["3m² + 2 = 434 where m is the middle ⇒ m² = 144 ⇒ m = 12", "Numbers 11, 12, 13 ⇒ sum 36"], "(m − 1)² + m² + (m + 1)² = 3m² + 2",
      "Solve for the middle number first.")
    k = len([x for x in range(1, 501) if x % 3 == 0 or x % 5 == 0])
    q(B, M, "L3", "officer", "How many integers from 1 to 500 are divisible by 3 or 5?", k,
      [(500 // 3 + 500 // 5, "did not subtract multiples of 15"), (500 // 15, "counted only multiples of 15"), (500 // 3 + 500 // 5 - 2 * (500 // 15), "subtracted the overlap twice")],
      ["⌊500/3⌋ = 166, ⌊500/5⌋ = 100, ⌊500/15⌋ = 33", "166 + 100 − 33 = 233"], "|A ∪ B| = |A| + |B| − |A ∩ B|",
      "Multiples of 15 are counted in both groups.")
    k = sum(i ** 3 for i in range(1, 11))
    q(B, M, "L2", "officer", "The value of 1³ + 2³ + … + 10³ is:", k,
      [(sum(i * i for i in range(1, 11)), "used the sum of squares"), (sum(i ** 3 for i in range(1, 10)), "summed only up to 9"), (55, "gave Σn")],
      ["Σn³ = [n(n + 1)/2]² = 55² = 3025"], "Σn³ = (Σn)²", "Square the triangular number.")
    ways = sum(1 for a in range(1, 46) for L in range(2, 46) if L * a + L * (L - 1) // 2 == 45)
    q(B, M, "L3", "officer", "In how many ways can 45 be written as a sum of two or more consecutive positive integers?", ways,
      [(ways + 1, "counted 45 itself as a sum"), (3, "counted only runs of odd length"), (2, "found only 22 + 23 and 14 + 15 + 16")],
      ["Number of ways (length ≥ 1) = number of odd divisors of 45 = 6 (1, 3, 5, 9, 15, 45)", "Exclude the single-term 45 ⇒ 5",
       "They are 22+23, 14+15+16, 7+…+11, 5+…+10, 1+…+9"], "Ways = (number of odd divisors) − 1", "The trivial one-term sum must be excluded.")
    k = sum(i if i % 2 else -i for i in range(1, 101))
    q(B, M, "L2", "officer", "The value of 1 − 2 + 3 − 4 + … + 99 − 100 is:", k,
      [(-k, "sign of each pair reversed"), (-100, "took 100 pairs"), (0, "assumed the terms cancel")],
      ["Pair terms: (1 − 2) + (3 − 4) + … = 50 pairs of −1", "Sum = −50"], "Group into pairs", "There are 50 pairs, each −1.")


def add_all(B):
    clocks(B)
    lcmhcf(B)
    series_diff(B)
    series_mult(B)
    wrong_term(B)
    pnc(B)
    remainders(B)
    consecutive(B)
