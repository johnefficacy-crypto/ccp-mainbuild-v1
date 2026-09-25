"""QRE-QA-A part 5: Time and Work (efficiency, combined rates, partial work, pipes and cisterns)."""
from fractions import Fraction as Fr
from qa_a_common import N, D, Rs, ratio, make_q


def days(x):
    return f"{N(x)} days"


def hrs(x):
    return f"{N(x)} h"


def mins(x):
    return f"{N(x)} min"


def together(*ts):
    return 1 / sum(Fr(1, 1) / t for t in ts)


def add_all(B):
    q = make_q(B)

    # ===================== Individual and combined work rates =====================
    k = together(12, 24)
    assert k == 8
    q("indiv", "L1", "f", "A can finish a job in 12 days and B in 24 days. Working together they finish it in:",
      days(k), [(days(18), "average of the two times"), (days(36), "times added"), (days(6), "half the faster time")],
      ["One day's work = 1/12 + 1/24 = 3/24 = 1/8", "Together = 8 days"], "T = ab/(a + b)", "Add rates, not days.")

    k = together(10, 15, 30)
    assert k == 5
    q("indiv", "L1", "f", "A, B and C can do a work in 10, 15 and 30 days respectively. Together they will finish it in:",
      days(k), [(days(together(10, 15)), "C left out"), (days(Fr(55, 3)), "average of the times"), (days(55), "times added")],
      ["1/10 + 1/15 + 1/30 = 6/30 = 1/5", "Together = 5 days"], "Sum of daily rates", "Every worker's rate counts.")

    b = 1 / (Fr(1, 12) - Fr(1, 20))
    assert b == 30
    q("indiv", "L2", "f", "A and B together finish a task in 12 days. A alone takes 20 days. B alone will take:",
      days(b), [(days(together(12, 20)), "rates added instead of subtracted"), (days(8), "days subtracted"), (days(16), "average of 12 and 20")],
      ["B's rate = 1/12 − 1/20 = 2/60 = 1/30", "B alone = 30 days"], "1/B = 1/(A+B) − 1/A", "Subtract rates, not days.")

    a = Fr(14 * 3, 2)
    q("indiv", "L2", "f", "A is twice as efficient as B. Together they finish a job in 14 days. A alone would finish it in:",
      days(a), [(days(42), "B's time"), (days(28), "14 × 2"), (days(7), "14 ÷ 2")],
      ["Rates 2 : 1 ⇒ 3 units/day", "Work = 3 × 14 = 42 units", "A alone = 42/2 = 21 days"], "Work = combined rate × time", "Twice as efficient ⇒ half the time of B.")

    men = Fr(6 * 15, 10)
    q("indiv", "L2", "f", "6 workers finish a job in 15 days. How many workers are needed to finish it in 10 days?",
      N(men), [(N(Fr(6 * 10, 15)), "direct proportion used"), ("11", "one extra worker per day saved"), ("10", "days read as workers")],
      ["Work = 6 × 15 = 90 worker-days", "90 ÷ 10 = 9 workers"], "M₁D₁ = M₂D₂", "Fewer days ⇒ more workers (inverse).")

    ab, bc, ca = 15, 20, 12
    s = (Fr(1, ab) + Fr(1, bc) + Fr(1, ca)) / 2
    assert 1 / s == 10
    q("indiv", "L3", "o", "A and B can do a work in 15 days, B and C in 20 days, and C and A in 12 days. All three together will do it in:",
      days(1 / s), [(days(1 / (2 * s)), "sum of pairs not halved"), (days(Fr(47, 3)), "average of the pair times"), (days(Fr(47, 2)), "pair times added and halved")],
      ["2(A + B + C) = 1/15 + 1/20 + 1/12 = 12/60 = 1/5", "A + B + C = 1/10 ⇒ 10 days"], "Add the pair rates and halve", "Each worker appears in two pairs.")

    A = 1 / (s - Fr(1, bc))
    Bt = 1 / (s - Fr(1, ca))
    Ct = 1 / (s - Fr(1, ab))
    assert (A, Bt, Ct) == (20, 60, 30)
    q("indiv", "L3", "o", "A and B can do a work in 15 days, B and C in 20 days, and C and A in 12 days. A alone will do it in:",
      days(A), [(days(Ct), "C's time (A + B subtracted)"), (days(Bt), "B's time (C + A subtracted)"), (days(1 / s), "all three together")],
      ["A + B + C = 1/10", "A = 1/10 − (B + C) = 1/10 − 1/20 = 1/20", "A alone = 20 days"], "Individual = total − opposite pair", "Subtract the pair that excludes A.")

    man, wom = 3, 2  # 12 men = 18 women ⇒ man : woman = 3 : 2
    W = 12 * man * 14
    t = Fr(W, 8 * man + 16 * wom)
    assert t == 9 and 18 * wom * 14 == W
    q("indiv", "L3", "o", "12 men or 18 women can finish a job in 14 days. In how many days will 8 men and 16 women finish it?",
      days(t), [(days(Fr(W, 24 * man)), "women counted as men"), (days(Fr(W, 24 * wom)), "men counted as women"), (days(Fr(14 * 30, 24)), "heads of both groups added")],
      ["12 men = 18 women ⇒ 1 man = 1.5 women; take man = 3, woman = 2 units", "Work = 12 × 3 × 14 = 504", "8 × 3 + 16 × 2 = 56 per day ⇒ 9 days"], "Convert to a common unit", "Men and women have different efficiencies.")

    T = next(T for T in range(6, 60) if Fr(T - 5, 20) + Fr(T, 30) == 1)
    q("indiv", "L3", "o", "A can do a work in 20 days and B in 30 days. They start together, but A leaves 5 days before the work is finished. The work lasts:",
      days(T), [(days(together(20, 30)), "A's leaving ignored"), (days(together(20, 30) + 5), "5 days added to the together time"), (days(T - 5), "A's working days reported")],
      ["B works T days, A works T − 5", "(T − 5)/20 + T/30 = 1 ⇒ 5T = 75", "T = 15 days"], "Σ(days × rate) = 1", "A misses the last 5 days, B does not.")

    ta, tb = Fr(5) * 3, Fr(10) * Fr(5, 2)
    k = together(ta, tb)
    q("indiv", "L3", "o", "A does 1/3 of a job in 5 days and B does 2/5 of it in 10 days. Working together, they finish the whole job in:",
      days(k), [(days(together(5, 10)), "partial-job days used as full-job days"), (days(Fr(ta + tb, 2)), "average of full times"), (days(ta + tb), "full times added")],
      ["A alone = 15 days; B alone = 25 days", "Together = 15 × 25/40 = 75/8 = 9 3/8 days"], "Scale partial days to full job first", "5 days is only a third of A's time.")

    m = next(Fr(m) for m in range(1, 40) if 8 * (4 * m + 6) == 10 * (3 * m + 7))
    W = 8 * (4 * m + 6)
    assert m == 11 and W == 400
    Wi = 8 * (4 + 6 * 11)  # women = 11 men (inverted)
    q("indiv", "L3", "o", "4 men and 6 women finish a job in 8 days; 3 men and 7 women finish it in 10 days. In how many days will 10 women finish it?",
      days(Fr(W, 10)), [(days(Fr(W, 10 * m)), "10 men instead of 10 women"), (days(8), "men and women taken as equally efficient"), (days(Fr(Wi, 10 * 11)), "man–woman ratio inverted")],
      ["8(4m + 6w) = 10(3m + 7w) ⇒ 2m = 22w ⇒ m = 11w", "Work = 8(44 + 6) = 400 woman-days", "10 women ⇒ 40 days"], "Equate total work", "Solve the efficiency ratio first.")

    k = 30
    a, b = 2 * k, 3 * k
    assert Fr(b - a) == 30 and together(a, b) == 36
    q("indiv", "L3", "o", "A is 50% more efficient than B, and B takes 30 days longer than A to finish a job alone. Working together they finish it in:",
      days(together(a, b)), [(days(Fr(a + b, 2)), "average of individual times"), (days(18), "together time halved"), (days(30), "time difference reported")],
      ["Efficiency 3 : 2 ⇒ time 2 : 3 = 2k, 3k", "k = 30 ⇒ A 60, B 90", "Together = 60 × 90/150 = 36 days"], "Time ∝ 1/efficiency", "Convert efficiency to time first.")

    done = 2 * (Fr(1, 10) + Fr(1, 12) + Fr(1, 15))
    rest = (1 - done) / (Fr(1, 10) + Fr(1, 12))
    q("indiv", "L2", "o", "A, B and C can do a work in 10, 12 and 15 days. They start together; after 2 days C leaves and A and B finish the rest. The whole work takes:",
      days(2 + rest), [(days(rest), "only the days after C left"), (days(together(10, 12, 15)), "C assumed to stay"), (days(together(10, 12)), "C's work ignored")],
      ["2 days' work = 2(6 + 5 + 4)/60 = 1/2", "Rest 1/2 at 11/60 per day = 30/11 days", "Total = 2 + 2 8/11 = 4 8/11 days"], "Work done + remaining work", "Add the first 2 days.")

    shares = [Fr(3, 6), Fr(3, 8)]
    c = 1 - sum(shares)
    wage = 3200
    assert c * wage == 400
    q("indiv", "L3", "o", "A can do a job in 6 days and B in 8 days. With C's help they finish it in 3 days and are paid ₹3,200 in all. C's share is:",
      Rs(c * wage), [(Rs(Fr(wage, 3)), "equal three-way split"), (Rs(shares[1] * wage), "B's share"), (Rs(shares[0] * wage), "A's share")],
      ["In 3 days A does 1/2, B does 3/8", "C does 1 − 1/2 − 3/8 = 1/8", "C gets 3,200/8 = ₹400"], "Wages ∝ work done", "Share by work, not by days.")

    b = 1 / ((1 - Fr(15, 24)) / 9)
    assert b == 24
    q("indiv", "L3", "o", "A can do a job in 24 days. A works alone for 6 days; then B joins and the two finish the rest in 9 more days. B alone would do the job in:",
      days(b), [(days(1 / (Fr(1, 9) - Fr(1, 24))), "whole job taken as done together in 9 days"), (days(9 / (1 - Fr(6, 24))), "A's work in the last 9 days ignored"),
                (days(9 / (Fr(6, 24))), "A's share and B's share swapped")],
      ["A works 6 + 9 = 15 days ⇒ 15/24 = 5/8", "B does 3/8 in 9 days", "B alone = 24 days"], "Count each worker's total days", "A keeps working after B joins.")

    # ===================== Efficiency comparison and relative capacity =====================
    q("eff", "L1", "f", "A is thrice as efficient as B. B alone finishes a job in 24 days. A alone will finish it in:",
      days(8), [(days(72), "multiplied instead of divided"), (days(6), "together time"), (days(12), "twice as efficient assumed")],
      ["Time ∝ 1/efficiency", "A = 24/3 = 8 days"], "Time ∝ 1/efficiency", "More efficient ⇒ less time.")

    q("eff", "L1", "f", "A is 25% more efficient than B. B alone does a job in 20 days. A alone will do it in:",
      days(Fr(20, Fr(5, 4))), [(days(15), "25% taken off the time"), (days(25), "25% added to the time"), (days(20), "efficiency ignored")],
      ["Efficiency 5 : 4 ⇒ time 4 : 5", "A = 20 × 4/5 = 16 days"], "Time ∝ 1/efficiency", "25% more efficiency is 20% less time.")

    W = 8 * 15
    q("eff", "L2", "f", "The efficiencies of A and B are in the ratio 5 : 3. Together they finish a job in 15 days. B alone will take:",
      days(Fr(W, 3)), [(days(Fr(W, 5)), "A's time"), (days(25), "15 × 5/3"), (days(9), "15 × 3/5")],
      ["Work = (5 + 3) × 15 = 120 units", "B alone = 120/3 = 40 days"], "Work = rate × time", "Use the combined rate.")

    b = next(b for b in range(11, 60) if b == 2 * (b - 10))
    q("eff", "L2", "f", "A takes 10 days less than B to do a job, and A is twice as efficient as B. B alone will take:",
      days(b), [(days(b - 10), "A's time"), (days(30), "difference × 3"), (days(together(b, b - 10)), "together time")],
      ["B = 2A and B − A = 10", "A = 10, B = 20 days"], "Time ∝ 1/efficiency", "Twice as efficient ⇒ half the time.")

    q("eff", "L2", "f", "3 men or 5 women can finish a job in 15 days. How long will 6 women take?",
      days(Fr(5 * 15, 6)), [(days(18), "direct proportion"), (days(Fr(3 * 15, 6)), "women treated as men"), (days(25), "5 × 15/3")],
      ["Work = 5 × 15 = 75 woman-days", "6 women ⇒ 75/6 = 12.5 days"], "Convert to woman-days", "Use the women's rate.")

    W = 12 * 35
    q("eff", "L3", "o", "A is 40% more efficient than B. Together they finish a job in 35 days. A alone will finish it in:",
      days(Fr(W, 7)), [(days(Fr(W, 5)), "B's time"), (days(49), "35 × 1.4"), (days(70), "together time doubled")],
      ["A : B = 7 : 5", "Work = 12 × 35 = 420 units", "A alone = 420/7 = 60 days"], "Efficiency ratio → units", "A's share is 7/12 of the rate.")

    t = Fr(12, Fr(26, 10))
    q("eff", "L3", "o", "A finishes a job in 12 days. B is 60% more efficient than A. Working together they finish it in:",
      days(t), [(days(Fr(12, Fr(16, 10))), "B's time"), (days(6), "equal efficiency assumed"), (days(Fr(12, Fr(24, 10))), "40% used instead of 60%")],
      ["Rates 1 : 1.6 ⇒ combined 2.6 A-units", "Time = 12/2.6 = 60/13 = 4 8/13 days"], "Combined rate in A-units", "B's rate is 1.6 × A's.")

    mu, wu, bu = 6, 4, 3  # 2 men = 3 women = 4 boys
    W = 10 * mu * 18
    g = 4 * mu + 6 * wu + 8 * bu
    assert Fr(W, g) == 15
    q("eff", "L3", "o", "2 men do as much work as 3 women or 4 boys. 10 men finish a job in 18 days. In how many days will 4 men, 6 women and 8 boys finish it?",
      days(Fr(W, g)), [(days(Fr(10 * 18, 18)), "all 18 persons taken as men"), (days(Fr(W, 4 * mu + 6 * wu + 8 * wu)), "boys valued as women"),
                      (days(Fr(W, 4 * mu + 6 * mu + 8 * bu)), "women valued as men")],
      ["Man = 6, woman = 4, boy = 3 units", "Work = 10 × 6 × 18 = 1,080", "Group rate = 24 + 24 + 24 = 72 ⇒ 15 days"], "LCM of 2, 3, 4 gives unit rates", "Equal work ⇒ inverse efficiency ratio.")

    W = 36
    level, dday = 0, 0
    while level < W:
        dday += 1
        level += 2 if dday % 2 == 1 else 1
    assert dday == 24
    q("eff", "L3", "o", "A is twice as efficient as B, and together they finish a job in 12 days. If they work on alternate days starting with A, the job is finished in:",
      days(dday), [(days(12), "together time"), (days(18), "A's time alone"), (days(27), "average of individual times")],
      ["A 18 days, B 36 days; work = 36 units, A 2/day, B 1/day", "Every 2 days: 3 units ⇒ 12 cycles = 24 days"], "Cycle method", "Check whether the last cycle is partial.")

    p = next(p for p in range(1, 60) if 3 * p - p == 40)
    q("eff", "L3", "o", "P is three times as efficient as Q and finishes a job 40 days earlier than Q. Together they finish it in:",
      days(together(p, 3 * p)), [(days(3 * p), "Q's time"), (days(p), "P's time"), (days(40), "difference reported")],
      ["Q = 3P and Q − P = 40 ⇒ P = 20, Q = 60", "Together = 20 × 60/80 = 15 days"], "Time ∝ 1/efficiency", "Find the individual times first.")

    m, w = 8, 5  # 5 men = 8 women
    W = 16 * w * 25
    g = 10 * m + 4 * w
    assert Fr(W, g) == 20
    q("eff", "L3", "o", "5 men can do as much work as 8 women. 16 women finish a job in 25 days. In how many days will 10 men and 4 women finish it?",
      days(Fr(W, g)), [(days(Fr(16 * 25, 14)), "men and women taken as equal"), (days(Fr(W, 10 * m)), "4 women omitted"), (days(Fr(W, 10 * m + 4 * m)), "women counted as men")],
      ["Man = 8, woman = 5 units", "Work = 16 × 5 × 25 = 2,000", "Rate = 80 + 20 = 100 ⇒ 20 days"], "Common efficiency unit", "5 men = 8 women ⇒ man : woman = 8 : 5.")

    r1 = Fr(300, 5)
    r2 = r1 * Fr(8, 10)
    assert Fr(1080) / (r1 + r2) == 10
    q("eff", "L3", "o", "Machine M1 makes 300 units in 5 hours. Machine M2 is 20% less efficient than M1. Working together, how long will they take to make 1,080 units?",
      hrs(Fr(1080) / (r1 + r2)), [(hrs(Fr(1080) / (r1 + r1 * Fr(12, 10))), "M2 taken as 20% more efficient"), (hrs(Fr(1080) / r1), "M1 alone"), (hrs(Fr(1080) / r2), "M2 alone")],
      ["M1 = 60/h, M2 = 48/h", "Together 108/h ⇒ 10 h"], "Units ÷ combined rate", "20% less efficient ⇒ 0.8 × rate.")

    a = Fr(1, 20)
    b = a * Fr(5, 4)
    t = Fr(7, 10) / (a + b)
    q("eff", "L3", "o", "A does 30% of a job in 6 days. B is 25% more efficient than A. Working together, in how many days will they finish the remaining 70%?",
      days(t), [(days(1 / (a + b)), "whole job instead of 70%"), (days(Fr(7, 10) / (a + Fr(1, 15))), "25% less time taken as 25% more efficiency"),
               (days(Fr(7, 10) / b), "B alone")],
      ["A alone = 20 days; B = 1.25/20 = 1/16 per day", "Together = 1/20 + 1/16 = 9/80", "0.7 ÷ 9/80 = 56/9 = 6 2/9 days"], "Remaining ÷ combined rate", "25% more efficient ⇒ time × 4/5.")

    W = 12 * 20
    q("eff", "L2", "o", "The efficiencies of A, B and C are in the ratio 3 : 4 : 5. Together they finish a job in 20 days. C alone will take:",
      days(Fr(W, 5)), [(days(Fr(W, 3)), "A's time"), (days(Fr(W, 4)), "B's time"), (days(Fr(100, 3)), "20 × 5/3")],
      ["Work = 12 × 20 = 240 units", "C alone = 240/5 = 48 days"], "Units from efficiency ratio", "Multiply the combined rate by the time.")

    ab = Fr(1, 12)
    bb = (1 - 10 * ab) / 5
    aa = ab - bb
    assert 10 * aa + 15 * bb == 1 and 1 / bb == 30
    q("eff", "L3", "o", "If A works for 10 days and leaves, B finishes the rest in 15 days. If A works for 12 days and leaves, B finishes the rest in 12 days. B alone would finish the job in:",
      days(1 / bb), [(days(1 / aa), "A's time"), (days(12), "together time"), (days(25), "average of 20 and 30")],
      ["12A + 12B = 1 ⇒ A + B = 1/12", "10A + 15B = 1 ⇒ 10/12 + 5B = 1 ⇒ B = 1/30", "B alone = 30 days"], "Two equations in rates", "Second scenario gives the combined rate.")

    # ===================== Partial work and remaining work =====================
    b = 9 / (1 - Fr(8, 20))
    q("partial", "L1", "f", "A can do a work in 20 days. A works for 8 days and then B finishes the rest in 9 days. B alone would do the work in:",
      days(b), [(days(9 / Fr(8, 20)), "work done used instead of work left"), (days(12), "20 − 8"), (days(27), "9 × 3")],
      ["A does 8/20 = 2/5", "B does 3/5 in 9 days ⇒ 15 days"], "Remaining work ÷ time", "B did 3/5, not the whole.")

    left = 1 - 4 * (Fr(1, 15) + Fr(1, 10))
    q("partial", "L1", "f", "A can do a work in 15 days and B in 10 days. They work together for 4 days. What fraction of the work is left?",
      N(left), [(N(1 - left), "work done reported"), (N(Fr(1, 6)), "one day's joint work"), (N(1 - Fr(4, 15)), "only A's work subtracted")],
      ["One day = 1/15 + 1/10 = 1/6", "4 days = 2/3 ⇒ left 1/3"], "Left = 1 − days × rate", "Include both workers.")

    rest = 1 - 6 * (Fr(1, 18) + Fr(1, 24))
    q("partial", "L2", "f", "A and B can do a work in 18 and 24 days. They work together for 6 days and then A leaves. B finishes the rest in:",
      days(rest * 24), [(days(rest * 18), "A finishes instead of B"), (days(18), "24 − 6"), (days((1 - rest) * 24), "work done used")],
      ["6 days = 6 × 7/72 = 7/12", "Left 5/12 × 24 = 10 days"], "Remaining × individual time", "B finishes, so use 24.")

    a = 14 / (1 - Fr(5, 12))
    q("partial", "L2", "f", "A and B together can finish a job in 12 days. They work together for 5 days; B then leaves and A finishes the rest in 14 days. A alone would do the job in:",
      days(a), [(days(14 / Fr(5, 12)), "work done used"), (days(19), "5 + 14"), (days(17), "12 + 5")],
      ["5 days = 5/12", "A does 7/12 in 14 days ⇒ 24 days"], "Remaining fraction ÷ time", "A did the remaining 7/12.")

    q("partial", "L2", "f", "A can finish 3/5 of a job in 12 days. In how many more days will A finish the rest?",
      days(Fr(12, 3) * 2), [(days(20), "whole job time"), (days(18), "12 × 3/2"), (days(Fr(24, 5)), "12 × 2/5")],
      ["1/5 of the job = 4 days", "Rest 2/5 = 8 days"], "Unitary method", "Scale by the remaining fraction.")

    units = {"A": 3, "B": 2, "C": 1}
    W, day, lvl = 60, 0, 0
    while lvl < W:
        day += 1
        lvl += units["A"] + (units["B"] + units["C"] if day % 3 == 0 else 0)
    assert day == 15 and lvl == W
    q("partial", "L3", "o", "A, B and C can do a work in 20, 30 and 60 days. A works every day and is helped by B and C together on every third day. The work is finished in:",
      days(day), [(days(20), "A alone"), (days(10), "all three every day"), (days(14), "help counted on alternate days")],
      ["Units 60: A 3, B 2, C 1 per day", "3-day block = 3 + 3 + (3 + 2 + 1) = 12", "60/12 = 5 blocks = 15 days"], "Block method", "Help comes only on day 3, 6, 9…")
    # 12-day check for the alternate-day distractor
    lv2, d2 = 0, 0
    while lv2 < W:
        d2 += 1
        lv2 += 3 + (3 if d2 % 2 == 0 else 0)
    assert d2 == 14

    def alt(first, second, W):
        lvl, d, t = 0, 0, Fr(0)
        while True:
            r = first if d % 2 == 0 else second
            if lvl + r >= W:
                return t + Fr(W - lvl, r)
            lvl += r
            t += 1
            d += 1
    tA = alt(3, 2, 36)
    tB = alt(2, 3, 36)
    assert tA == Fr(43, 3) and tB == Fr(29, 2)
    q("partial", "L3", "o", "A can do a work in 12 days and B in 18 days. They work on alternate days, A starting. The work is finished in:",
      days(tA), [(days(tB), "B assumed to start"), (days(15), "last partial day rounded up"), (days(together(12, 18)), "together every day")],
      ["Units 36: A 3, B 2", "7 two-day cycles = 35 in 14 days", "Day 15: A needs 1/3 day ⇒ 14 1/3 days"], "Cycle method, then partial day", "The last day need not be full.")

    x = next(x for x in range(1, 10) if x * (Fr(1, 10) + Fr(1, 15)) + Fr(5, 15) == 1)
    q("partial", "L3", "o", "A and B can do a work in 10 and 15 days. They start together; A leaves after some days and B finishes the remaining work in 5 days. A left after:",
      days(x), [(days(5), "B's closing days copied"), (days(together(10, 15)), "together time"), (days(Fr(10, 3)), "B's 5 days counted as A's")],
      ["x/6 + 5/15 = 1", "x/6 = 2/3 ⇒ x = 4"], "Joint phase + solo phase = 1", "B's last 5 days do 1/3.")

    b = 20 / (1 - Fr(18, 30))
    a = 1 / (Fr(1, 30) - 1 / b)
    assert b == 50 and a == 75
    q("partial", "L3", "o", "A and B together can do a work in 30 days. After working together for 18 days, A leaves and B finishes the rest in 20 days. A alone would do the work in:",
      days(a), [(days(b), "B's time"), (days(60), "twice the together time"), (days(38), "18 + 20")],
      ["18 days = 3/5 done", "B does 2/5 in 20 ⇒ B = 50 days", "A = 1/30 − 1/50 = 1/75 ⇒ 75 days"], "Find B, then subtract", "A's rate = joint − B's.")

    rem = Fr(20 * 20, 15)
    q("partial", "L3", "o", "20 workers can finish a project in 30 days. After 10 days, 5 workers leave. The remaining workers will finish the rest in:",
      days(rem), [(days(20), "departure ignored"), (days(10 + rem), "total duration reported"), (days(15), "direct proportion 20 × 15/20")],
      ["Left = 20 × 20 = 400 worker-days", "15 workers ⇒ 400/15 = 26 2/3 days"], "Remaining worker-days", "Only 20 days' work was left.")

    new = Fr(12 * 12, 16)
    q("partial", "L3", "o", "12 workers planned to finish a job in 16 days. After 4 days, 4 more workers join. How many days earlier than planned is the job finished?",
      days(12 - new), [(days(4), "joining workers read as days"), (days(new), "remaining days reported"), (days(12), "planned remaining days")],
      ["Left = 12 × 12 = 144 worker-days", "16 workers ⇒ 9 days", "Saved = 12 − 9 = 3 days"], "Remaining worker-days", "Compare with the 12 planned days.")

    A, Bt = Fr(16) * Fr(3, 2), Fr(12) * Fr(4, 3)
    rest = (1 - Fr(4) / Bt) / (1 / A + 1 / Bt)
    Aw, Bw = Fr(16), Fr(12)
    wrong = 4 + (1 - Fr(4) / Bw) / (1 / Aw + 1 / Bw)
    q("partial", "L3", "o", "A can do 2/3 of a job in 16 days and B can do 3/4 of it in 12 days. B works alone for 4 days, then A and B finish the job together. The total time is:",
      days(4 + rest), [(days(rest), "only the joint phase"), (days(together(A, Bt)), "together from the start"), (days(wrong), "partial-job days used as full-job days")],
      ["A = 24, B = 16 days", "B's 4 days = 1/4", "3/4 ÷ (1/24 + 1/16) = 3/4 × 48/5 = 7.2", "Total = 11.2 days"], "Scale partial days first", "2/3 in 16 days ⇒ 24 days for all.")

    b = 21 / (1 - Fr(5, 40))
    q("partial", "L3", "o", "A can do a work in 40 days. A works for 5 days and B finishes the rest in 21 days. Working together from the start, A and B would finish it in:",
      days(together(40, b)), [(days(26), "5 + 21"), (days(b), "B's time"), (days(Fr(40 + b, 2)), "average of individual times")],
      ["A does 1/8", "B does 7/8 in 21 ⇒ B = 24 days", "Together = 40 × 24/64 = 15 days"], "Find B from the remaining work", "Then combine rates.")

    AB, BC = Fr(1, 12), Fr(1, 16)
    C = (1 - 5 * AB - 2 * BC) / 11
    Bb = BC - C
    assert 1 / C == 24 and 1 / Bb == 48
    q("partial", "L3", "o", "A and B can do a work in 12 days, and B and C in 16 days. A works for 5 days, then B for 7 days, and C finishes the rest in 13 days. C alone would do the work in:",
      days(1 / C), [(days(1 / Bb), "B's time"), (days(16), "B and C together"), (days(13), "C's closing days")],
      ["5A + 7B + 13C = 5(A + B) + 2(B + C) + 11C", "= 5/12 + 1/8 + 11C = 1 ⇒ C = 1/24", "C alone = 24 days"], "Regroup into known pairs", "Split 7B as 5B + 2B.")

    x = 21 - Fr(20 * 25 - 20 * 21, 5)
    q("partial", "L2", "o", "20 workers can finish a job in 25 days. After how many days should 5 more workers join so that the job finishes in 21 days?",
      days(x), [(days(16), "days the new workers work"), (days(4), "25 − 21"), (days(10), "half of 21 rounded")],
      ["Work = 500 worker-days; 20 × 21 = 420", "Extra 80 by 5 workers = 16 days", "Join after 21 − 16 = 5 days"], "Total worker-days fixed", "The extra workers stay till the end.")

    # ===================== Pipes and cisterns =====================
    q("pipes", "L1", "f", "Pipes A and B can fill a tank in 12 hours and 15 hours. Both together fill it in:",
      hrs(together(12, 15)), [(hrs(Fr(27, 2)), "average of the times"), (hrs(27), "times added"), (hrs(3), "difference of the times")],
      ["1/12 + 1/15 = 9/60 = 3/20", "Time = 20/3 = 6 2/3 h"], "T = ab/(a + b)", "Add rates.")

    q("pipes", "L1", "f", "Pipe A fills a tank in 10 hours; outlet B empties the full tank in 15 hours. With both open, the empty tank is filled in:",
      hrs(1 / (Fr(1, 10) - Fr(1, 15))), [(hrs(together(10, 15)), "outlet treated as inlet"), (hrs(5), "difference of times"), (hrs(Fr(25, 2)), "average of the times")],
      ["Net = 1/10 − 1/15 = 1/30", "Time = 30 h"], "Net rate = fill − empty", "Subtract the outlet.")

    t = 1 / (Fr(1, 20) + Fr(1, 30) - Fr(1, 60))
    q("pipes", "L2", "f", "Pipes A and B fill a tank in 20 and 30 hours; pipe C empties it in 60 hours. With all three open, the tank fills in:",
      hrs(t), [(hrs(together(20, 30, 60)), "C treated as an inlet"), (hrs(together(20, 30)), "C ignored"), (hrs(1 / (Fr(1, 20) - Fr(1, 60))), "B ignored")],
      ["Net = 1/20 + 1/30 − 1/60 = 4/60", "Time = 15 h"], "Net rate", "Only C is subtracted.")

    leak = 1 / (Fr(1, 8) - Fr(1, 12))
    q("pipes", "L2", "f", "A tap fills a tank in 8 hours, but because of a leak it takes 12 hours. The leak alone would empty the full tank in:",
      hrs(leak), [(hrs(4), "difference of times"), (hrs(20), "times added"), (hrs(together(8, 12)), "rates added")],
      ["Leak rate = 1/8 − 1/12 = 1/24", "Leak empties in 24 h"], "Leak = normal − actual rate", "Subtract rates, not times.")

    rest = (1 - 2 * (Fr(1, 6) + Fr(1, 12))) * 6
    assert rest == 3
    q("pipes", "L2", "f", "Pipe A fills a tank in 6 hours and pipe B in 12 hours. Both are opened; after 2 hours B is closed. A fills the rest in:",
      hrs(rest), [(hrs((1 - 2 * (Fr(1, 6) + Fr(1, 12))) * 12), "B left running instead of A"), (hrs(4), "6 − 2"), (hrs(10), "12 − 2")],
      ["2 h together = 2 × 1/4 = 1/2", "A fills 1/2 in 3 h"], "Remaining ÷ A's rate", "Half was already full.")

    t = 1 / (Fr(1, 20) + Fr(1, 30) - Fr(1, 15))
    q("pipes", "L3", "o", "Two pipes fill a cistern in 20 and 30 minutes; an outlet empties the full cistern in 15 minutes. With all three open on an empty cistern, it fills in:",
      mins(t), [(mins(together(20, 30)), "outlet ignored"), (mins(together(20, 30, 15)), "outlet treated as inlet"), (mins(15), "outlet's time reported")],
      ["Net = 3/60 + 2/60 − 4/60 = 1/60", "Time = 60 min"], "Net rate", "A small net rate means a long time.")

    x = next(Fr(x, 2) for x in range(1, 40) if Fr(12, 16) + Fr(x, 2) / 24 == 1)
    xs = next(Fr(x, 2) for x in range(1, 40) if Fr(12, 24) + Fr(x, 2) / 16 == 1)
    q("pipes", "L3", "o", "Pipes A and B fill a tank in 16 h and 24 h. Both are opened together; B is closed after some time and the tank is full in 12 h from the start. B was open for:",
      hrs(x), [(hrs(xs), "roles of A and B swapped"), (hrs(together(16, 24)), "together time"), (hrs(4), "16 − 12")],
      ["A works 12 h ⇒ 3/4", "B fills 1/4 ⇒ 24/4 = 6 h"], "Σ(time × rate) = 1", "A runs the full 12 h.")

    rA, rB, rC = Fr(1, 12), Fr(1, 15), Fr(1, 20)
    rest = (1 - 2 * (rA + rB + rC)) / (rA + rB)
    alone = (1 - 2 * (rA + rB + rC)) / rA
    from qa_a_common import hm_time
    q("pipes", "L3", "o", "Pipes A, B and C can fill a tank in 12, 15 and 20 hours. All three are opened at 9:00 am on an empty tank; C is closed at 11:00 am. The tank is full at:",
      hm_time(11 + rest), [(hm_time(9 + 1 / (rA + rB + rC)), "C kept open throughout"), (hm_time(9 + rest), "remaining time counted from 9 am"), (hm_time(11 + alone), "B's contribution ignored after 11 am")],
      ["2 h × 1/5 = 2/5 full", "Rest 3/5 at 9/60 per h = 4 h", "11 am + 4 h = 3:00 pm"], "Phase-wise filling", "Count from 11 am.")

    lvl, h = 0, 0
    while True:
        if h % 2 == 0:
            if lvl + 3 >= 12:
                t = h + Fr(12 - lvl, 3)
                break
            lvl += 3
        else:
            lvl -= 2
        h += 1
    assert t == 19
    q("pipes", "L3", "o", "Pipe A fills a tank in 4 hours; pipe B empties the full tank in 6 hours. Starting with an empty tank, they are opened alternately for 1 hour each, A first. The tank is full after:",
      hrs(t), [(hrs(1 / (Fr(1, 4) - Fr(1, 6))), "both open together"), (hrs(24), "net 1 unit per 2 h for all 12 units"), (hrs(18), "last A-hour not counted")],
      ["Units 12: A +3, B −2", "Net +1 per 2 h; after 18 h level = 9", "19th hour A adds 3 ⇒ full at 19 h"], "Cycle method with a final check", "The tank fills during an A-hour before the cycle ends.")

    c = 1 / (Fr(1, 36) + Fr(1, 45) - Fr(1, 30))
    q("pipes", "L3", "o", "Pipes A and B fill a tank in 36 and 45 minutes. With outlet C also open, the tank fills in 30 minutes. C alone empties the full tank in:",
      mins(c), [(mins(together(36, 45)), "A and B together"), (mins(81), "36 + 45"), (mins(together(20, 30)), "C treated as an inlet")],
      ["A + B = 1/36 + 1/45 = 1/20", "C = 1/20 − 1/30 = 1/60", "C empties in 60 min"], "Outlet = inlets − net", "Net filling is slower, so C drains.")

    W = 4 * 36
    q("pipes", "L3", "o", "Pipe A fills water three times as fast as pipe B. Together they fill a tank in 36 minutes. B alone will fill it in:",
      mins(W), [(mins(Fr(W, 3)), "A's time"), (mins(108), "36 × 3"), (mins(72), "36 × 2")],
      ["Rates 3 : 1 ⇒ 4 units/min; work = 144", "B alone = 144 min"], "Units from rate ratio", "B has 1/4 of the combined rate.")

    Cap = next(C for C in range(100, 5000, 10) if (Fr(C, 20) - 15) * 30 == C)
    assert Cap == 900
    q("pipes", "L3", "o", "An inlet fills a tank in 20 minutes. A leak drains water at 15 litres per minute, so with the leak the tank takes 30 minutes to fill. The capacity of the tank is:",
      f"{N(Cap)} litres", [(f"{N(15 * 30)} litres", "leak × filling time"), (f"{N(15 * 40)} litres", "leak × 40 (20 + 20)"), (f"{N(2 * Cap)} litres", "doubled")],
      ["Net rate = C/20 − 15", "(C/20 − 15) × 30 = C ⇒ 1.5C − 450 = C", "C = 900 L"], "Net rate × time = capacity", "Leak is in litres, rate in tanks.")

    rest = (1 - Fr(5, 20)) / (Fr(1, 20) + Fr(1, 30))
    q("pipes", "L3", "o", "Pipes A and B can fill a tank in 20 and 30 minutes. Only A is opened; after 5 minutes B is also opened. The tank is full after a total of:",
      mins(5 + rest), [(mins(together(20, 30)), "both open from the start"), (mins(rest), "time after B opened"), (mins(5 + together(20, 30)), "full joint time added to 5")],
      ["A alone 5 min = 1/4", "3/4 at 1/12 per min = 9 min", "Total 14 min"], "Phase-wise filling", "Add the first 5 minutes.")

    b = 1 / (Fr(2, 3) / 4 - Fr(1, 10) + Fr(1, 15))
    assert b == Fr(15, 2)
    q("pipes", "L3", "o", "A tank has inlets P and Q and an outlet R. P fills it in 10 h and R empties it in 15 h. When the tank is 1/3 full, all three are opened and the tank fills in 4 more hours. Q alone would fill it in:",
      hrs(b), [(hrs(1 / (Fr(1, 4) - Fr(1, 10) + Fr(1, 15))), "tank taken as empty at start"), (hrs(6), "Q's rate taken as the net rate 1/6"), (hrs(15), "outlet ignored")],
      ["Net rate = (2/3)/4 = 1/6", "Q = 1/6 − 1/10 + 1/15 = 2/15", "Q alone = 7.5 h"], "Net = P + Q − R", "Only 2/3 remained.")

    x = next(x for x in range(1, 50) if Fr(1, x) + Fr(1, x + 5) == Fr(1, 6))
    q("pipes", "L2", "o", "Two pipes together fill a tank in 6 hours. One pipe alone would take 5 hours less than the other. The slower pipe alone fills it in:",
      hrs(x + 5), [(hrs(x), "faster pipe's time"), (hrs(12), "together time doubled"), (hrs(11), "6 + 5")],
      ["1/x + 1/(x + 5) = 1/6", "x = 10 ⇒ slower = 15 h"], "Quadratic from combined rate", "Answer the slower pipe.")
