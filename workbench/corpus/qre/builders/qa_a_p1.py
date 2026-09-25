"""QRE-QA-A part 1: Percentage (5 microtopics)."""
from fractions import Fraction as Fr
from qa_a_common import N, D, P, Rs, RsD, ratio, make_q


def add_all(B):
    q = make_q(B)

    # ===================== Income, expenditure and savings =====================
    inc, sp = 48000, Fr(72)
    sav = inc * (100 - sp) / 100
    assert sav == 13440
    q("ies", "L1", "f", f"Meena earns {Rs(inc)} a month and spends {P(sp)} of it. Her monthly savings are:",
      Rs(sav),
      [(Rs(inc * sp / 100), "expenditure reported instead of savings"),
       (Rs(Fr(28, 100) * inc * sp / 100), "28% applied to expenditure instead of income"),
       (Rs(inc * Fr(38, 100)), "subtraction slip: 100 − 72 taken as 38")],
      [f"Savings share = 100% − {P(sp)} = 28%", f"Savings = 28% of {N(inc)} = {Rs(sav)}"],
      "Savings = Income − Expenditure", "The savings rate is the complement of the spending rate, applied to income.")

    s, r = 9000, 15
    inc = Fr(s * 100, r)
    assert inc == 60000
    q("ies", "L1", "f", f"A clerk saves {Rs(s)} a month, which is {r}% of his income. His monthly expenditure is:",
      Rs(inc - s),
      [(Rs(inc), "income reported instead of expenditure"),
       (Rs(Fr(r, 100) * s), "15% taken of savings"),
       (Rs(inc + s), "savings added to income")],
      [f"Income = {N(s)} × 100/{r} = {Rs(inc)}", f"Expenditure = {N(inc)} − {N(s)} = {Rs(inc - s)}"],
      "Income = Savings ÷ savings rate", "Find income first; expenditure is income minus savings.")

    I, E = Fr(100), Fr(75)
    nI, nE = I * Fr(120, 100), E * Fr(110, 100)
    ch = ((nI - nE) - (I - E)) / (I - E) * 100
    assert ch == 50
    q("ies", "L2", "f", "A person saves 25% of his income. His income rises by 20% and his expenditure by 10%. By what percentage do his savings increase?",
      P(ch),
      [(P(10), "difference of the two rates (20 − 10)"), (P(30), "sum of the two rates"),
       (P(15), "average of the two rates")],
      ["Take income 100, expenditure 75, savings 25", f"New income 120, new expenditure {N(nE)}, new savings {N(nI - nE)}",
       f"Increase = {N(nI - nE - 25)}/25 × 100 = {P(ch)}"],
      "Savings = Income − Expenditure; % change on old savings", "Savings react more than income because expenditure is a large fixed-share block.")

    # incomes 5:4, expenditures 3:2, each saves 8000
    x = 4000
    y = 2 * x - 4000
    assert 5 * x - 3 * y == 8000 and 4 * x - 2 * y == 8000
    q("ies", "L2", "f", "The incomes of A and B are in the ratio 5 : 4 and their expenditures in the ratio 3 : 2. If each saves ₹8,000, A's income is:",
      Rs(5 * x),
      [(Rs(4 * x), "B's income reported"), (Rs(3 * y), "A's expenditure reported"),
       (Rs(8000 * 5), "savings multiplied by A's ratio term")],
      ["Let incomes 5x, 4x and expenditures 3y, 2y", "5x − 3y = 8000 and 4x − 2y = 8000",
       f"Solving: x = {N(x)}, y = {N(y)}", f"A's income = 5x = {Rs(5 * x)}"],
      "Income − Expenditure = Savings for each person", "Two different multipliers are needed for the two ratios.")

    sv = 12600
    share = Fr(70, 100) * Fr(60, 100)
    inc = sv / share
    assert inc == 30000
    q("ies", "L2", "f", f"Ravi spends 30% of his income on rent and 40% of the remainder on food. He saves the rest, which is {Rs(sv)}. His income is:",
      Rs(inc),
      [(Rs(Fr(sv) / Fr(30, 100)), "40% taken on income, not on the remainder"),
       (Rs(Fr(sv) / Fr(70, 100)), "food expense ignored"),
       (Rs(Fr(sv) / Fr(40, 100)), "savings equated to 40%")],
      ["After rent: 70% of income", "Food = 40% of 70% = 28%; savings = 70% − 28% = 42%",
       f"Income = {N(sv)} ÷ 0.42 = {Rs(inc)}"],
      "Chain the shares: 0.70 × 0.60 = 0.42", "'Of the remainder' means the base shrinks after each spend.")

    # officer
    E = Fr(200, 3)
    assert 125 - Fr(115, 100) * E == Fr(145, 100) * (100 - E)
    wrongE = Fr(125) / Fr(26, 10)
    q("ies", "L3", "o", "Arun's income rises by 25% and his expenditure by 15%; as a result his savings rise by 45%. What percentage of his original income did he save?",
      P(100 - E),
      [(P(E), "expenditure share reported"),
       (P(100 - wrongE), "savings growth applied to expenditure (125 − 1.15E = 1.45E)"),
       (P(20), "the 20-point gap in growth rates read as the savings share")],
      ["Income 100, expenditure E, savings 100 − E", "125 − 1.15E = 1.45(100 − E)", "0.30E = 20 ⇒ E = 66 2/3",
       f"Savings share = {P(100 - E)}"],
      "New income − new expenditure = new savings", "Set up the equation in savings, not in expenditure.")

    I, S = Fr(100), Fr(20)
    E = I - S
    nE = I * Fr(130, 100) - S * Fr(110, 100)
    ch = (nE - E) / E * 100
    assert ch == 35
    q("ies", "L3", "o", "A family saves 20% of its income. Income increases by 30% and savings increase by 10%. Expenditure increases by:",
      P(ch),
      [(P(20), "difference of rates 30 − 10"), (P(40), "sum of rates"),
       (P(28), "expenditure increase measured on income instead of old expenditure")],
      ["Income 100, savings 20, expenditure 80", "New income 130, new savings 22, new expenditure 108",
       f"Increase = 28/80 × 100 = {P(ch)}"],
      "% change = change ÷ old expenditure × 100", "Base for the expenditure change is 80, not 100.")

    # A income 25% more than B; A exp 20% more than B's; A saves 40% more than B
    E = Fr(75)
    assert 125 - Fr(12, 10) * E == Fr(14, 10) * (100 - E)
    Asav = 125 - Fr(12, 10) * E
    q("ies", "L3", "o", "A's income is 25% more than B's and A's expenditure is 20% more than B's. A saves 40% more than B. What percentage of his income does A save?",
      P(Asav / 125 * 100),
      [(P(100 - E), "B's savings rate reported"), (P(Asav), "A's savings measured on B's income"),
       (P(100 - Asav / 125 * 100), "A's expenditure share reported")],
      ["B: income 100, expenditure E; A: income 125, expenditure 1.2E", "125 − 1.2E = 1.4(100 − E) ⇒ E = 75",
       f"A saves 125 − 90 = 35, i.e. 35/125 = {P(Asav / 125 * 100)}"],
      "Savings = Income − Expenditure for each person", "Measure A's savings rate on A's own income.")

    inc = 75000
    a = inc * Fr(80, 100)
    b = a * Fr(75, 100)
    c = b * Fr(90, 100)
    assert c == 40500
    q("ies", "L2", "o", f"From a monthly income of {Rs(inc)}, Kavya spends 20% on housing, 25% of the remainder on education and 10% of what is then left on travel. She saves the balance. Her savings are:",
      Rs(c),
      [(Rs(inc * Fr(45, 100)), "all three rates deducted from income (55%)"), (Rs(b), "travel step missed"),
       (Rs(b - inc * Fr(10, 100)), "travel taken as 10% of income")],
      [f"After housing: {N(a)}", f"After education: 75% of {N(a)} = {N(b)}", f"After travel: 90% of {N(b)} = {Rs(c)}"],
      "Remainder = Income × 0.80 × 0.75 × 0.90", "Each later rate applies to the shrinking remainder.")

    # statement
    I1, E1 = 100, 50
    dS = Fr(10, 100) * I1 - Fr(15, 100) * E1
    assert dS > 0  # II false
    q("ies", "L3", "o",
      "Consider the following for a person with positive savings:\n\nI. If income and expenditure both rise by the same percentage, savings rise by that percentage.\nII. If expenditure rises by a larger percentage than income, savings must fall.\nIII. If savings rise by a larger percentage than income, expenditure must rise by a smaller percentage than income.\n\nWhich of these are correct?",
      "I and III only",
      [("I only", "misses that III follows from S = I − E"), ("I and II only", "II fails: income 100, expenditure 50, +10% and +15% still raise savings"),
       ("I, II and III", "accepts II without testing")],
      ["I: S' = kI − kE = kS, true", "II: I = 100, E = 50; income +10% (+10), expenditure +15% (+7.5) ⇒ savings rise by 2.5, so false",
       "III: ΔE = ΔI − ΔS < aI − aS = aE, so expenditure grows by less than a%, true"],
      "ΔS = ΔI − ΔE", "A bigger percentage on a smaller base can still be a smaller absolute rise.", kind="statement")

    I, E = Fr(100), Fr(85)
    nI, nE = 120, E * Fr(125, 100)
    r = (nI - nE) / nI * 100
    q("ies", "L3", "o", "Suresh saves 15% of his income. Next year his income rises by 20% and his expenditure by 25%. What percentage of the new income does he save?",
      P(D(r)),
      [(P(nI - nE), "new savings measured on old income"), (P(10), "15 + 20 − 25 applied to rates"),
       (P(D((nI - (E + 25)) / nI * 100)), "25 points added to expenditure instead of 25%")],
      ["Income 100, expenditure 85", f"New income 120, new expenditure 85 × 1.25 = {N(nE)}",
       f"New savings = {N(nI - nE)}; share = {N(nI - nE)}/120 = {D(r)}%"],
      "Savings rate = Savings ÷ Income", "Percent changes cannot be added to a share directly.")

    # E:S from growth
    # 1.2E + 1.1S = 1.16(E+S) -> E/S = 3/2
    assert Fr(116 - 110, 120 - 116) == Fr(3, 2)
    q("ies", "L3", "o", "A person's expenditure rises by 20% and his savings by 10%, so that his income rises by 16%. The ratio of his original expenditure to savings is:",
      "3:2",
      [("2:3", "ratio inverted"), ("2:1", "ratio of the two growth rates taken"), ("3:5", "expenditure to income reported")],
      ["1.20E + 1.10S = 1.16(E + S)", "0.04E = 0.06S", "E : S = 3 : 2"],
      "Weighted growth: income growth is the average of E and S growth weighted by their size",
      "Alligation: E share ↔ (16 − 10), S share ↔ (20 − 16).")

    I, E = 100, 60
    nE = Fr(115) - (I - E)
    ch = (nE - E) / E * 100
    assert ch == 25
    q("ies", "L3", "o", "Neha spends 60% of her income. Her income rises by 15%. If her savings in rupees are to stay the same, by what percentage can her expenditure rise?",
      P(ch),
      [(P(15), "same percentage as income"), (P(9), "15% of 60 read as a percentage"),
       (P(Fr(15, 40) * 100), "increase in income divided by savings")],
      ["Income 100, expenditure 60, savings 40", "New income 115, savings still 40 ⇒ expenditure 75",
       f"Rise = 15/60 = {P(ch)}"],
      "New expenditure = New income − Unchanged savings", "The whole ₹15 income gain goes to expenditure, whose base is 60.")

    E = Fr(70) * Fr(125, 100)
    r = (120 - E) / 120 * 100
    q("ies", "L3", "o", "An employee saves 30% of his salary. His salary rises by 20%, while prices of everything he buys rise by 25% and he keeps buying the same quantities. His new savings as a percentage of new salary are:",
      P(D(r)),
      [(P(120 - E), "new savings measured on old salary"), (P(25), "30 + 20 − 25 applied to rates"),
       (P(35), "30 + (25 − 20) applied")],
      ["Salary 100, spending 70", f"New spending = 70 × 1.25 = {N(E)}; new salary 120",
       f"New savings = {N(120 - E)} ⇒ {N(120 - E)}/120 = {D(r)}%"],
      "Same quantities ⇒ spending scales with prices", "Divide by the new salary, not the old one.")

    AI, AE = 80, Fr(80) * Fr(75, 100)
    r = (AI - AE) / AI * 100
    assert r == 25
    q("ies", "L2", "o", "A's income is 20% less than B's and A's expenditure is 25% less than B's. If B saves 20% of his income, what percentage of his income does A save?",
      P(r),
      [(P(20), "B's rate reported"), (P(15), "rates netted: 20 − 5"), (P(75), "A's expenditure share reported")],
      ["B: income 100, expenditure 80", "A: income 80, expenditure 60", f"A saves 20/80 = {P(r)}"],
      "Savings rate = (Income − Expenditure) ÷ Income", "A's base is his own income of 80.")

    # ===================== Percentage comparison =====================
    q("pcmp", "L1", "f", "A's salary is 25% more than B's. By what percentage is B's salary less than A's?",
      P(20),
      [(P(25), "same percentage assumed both ways"), (P(Fr(100, 3)), "25/75 used"), (P(80), "B as a percentage of A")],
      ["A = 125 when B = 100", "Difference 25 on base 125 = 20%"],
      "Less-than % = r/(100 + r) × 100", "The base switches to A's salary.")

    q("pcmp", "L1", "f", "150 m is what percentage of 1.2 km?",
      P(Fr(150, 1200) * 100),
      [(P(8), "1200 ÷ 150 read as a percentage"), (P(Fr(150, 12000) * 100), "1.2 km taken as 12,000 m"),
       (P(125), "unit conversion skipped: 150/1.2")],
      ["1.2 km = 1,200 m", "150/1,200 × 100 = 12.5%"],
      "% = part ÷ whole × 100 (same units)", "Convert units before dividing.")

    n = Fr(147 * 100, 35)
    q("pcmp", "L1", "f", "If 35% of a number is 147, then 60% of the number is:",
      N(n * Fr(60, 100)),
      [(N(n), "the number itself"), (N(Fr(147 * 60, 100)), "60% taken of 147"),
       (N(Fr(147) * Fr(125, 100)), "25 points added as 25% of 147")],
      [f"Number = 147 × 100/35 = {N(n)}", f"60% of {N(n)} = {N(n * Fr(60, 100))}"],
      "x% of N ⇒ N = value × 100/x", "Or directly 147 × 60/35.")

    C = Fr(140) * Fr(70, 100)
    q("pcmp", "L2", "f", "A is 40% more than B, and C is 30% less than A. Compared with B, C is:",
      "2% less",
      [("10% more", "percentages netted (40 − 30)"), ("2% more", "sign of the change reversed"), ("10% less", "30 − 40 with base ignored")],
      ["B = 100 ⇒ A = 140", f"C = 70% of 140 = {N(C)}", "C is 2 less than 100, i.e. 2% less"],
      "Chain the multipliers: 1.4 × 0.7 = 0.98", "Percentages on different bases cannot be subtracted.")
    assert C == 98

    q("pcmp", "L2", "f", "If 20% of A equals 30% of B, then A is how much percent more than B?",
      P(50),
      [(P(10), "difference of percentages"), (P(Fr(100, 3)), "B less than A reported"), (P(150), "A as a percentage of B")],
      ["0.2A = 0.3B ⇒ A = 1.5B", "A exceeds B by 50%"],
      "A/B = 30/20", "'More than' needs (A − B)/B.")

    Ar = Fr(120, 100) * Fr(75, 100)
    more = (1 - Ar) / Ar * 100
    q("pcmp", "L3", "o", "A's income is 20% more than B's, and B's income is 25% less than C's. By what percentage is C's income more than A's?",
      P(more),
      [(P(10), "A less than C reported (base C)"), (P(5), "rates netted: 25 − 20"), (P(1 / Ar * 100), "C as a percentage of A")],
      ["C = 100 ⇒ B = 75 ⇒ A = 90", f"C exceeds A by 10 on base 90 = {P(more)}"],
      "More-than % uses the smaller quantity as base", "10% less the other way is 11 1/9% more.")

    n = Fr(1020) / Fr(85, 100)
    assert n == 1200
    q("pcmp", "L3", "o", "A number exceeds 15% of itself by 1,020. What is 35% of the number?",
      N(n * Fr(35, 100)),
      [(N(Fr(1020) * Fr(35, 100)), "excess treated as the number"), (N(Fr(1020) / Fr(15, 100) * Fr(35, 100)), "1,020 taken as 15% of the number"),
       (N(Fr(1020) * Fr(115, 100) * Fr(35, 100)), "number taken as 1.15 × 1,020")],
      ["N − 0.15N = 1,020 ⇒ 0.85N = 1,020 ⇒ N = 1,200", "35% of 1,200 = 420"],
      "N(1 − 0.15) = excess", "The excess is 85% of the number.")

    r = Fr(130, 145) * 100
    q("pcmp", "L3", "o", "Two numbers are respectively 30% and 45% more than a third number. The first number is what percentage of the second?",
      P(D(r)),
      [(P(85), "100 − (45 − 30)"), (P(D(Fr(145, 130) * 100)), "second as a percentage of first"), (P(D(Fr(15, 130) * 100)), "gap measured on first number")],
      ["Third = 100 ⇒ numbers 130 and 145", f"130/145 × 100 = {D(r)}%"],
      "Ratio of (100 + a) to (100 + b)", "Compare the two numbers, not their markups.")

    fE, fM, fb = 35, 42, 12
    both = 100 - (fE + fM - fb)
    assert both == 35
    q("pcmp", "L3", "o", "In an examination, 65% of candidates passed in English, 58% passed in Mathematics and 12% failed in both. What percentage passed in both?",
      P(both),
      [(P(65 + 58 - 100), "failed-in-both group ignored"), (P(100 - fb), "everyone except the both-fail group"),
       (P(100 - fE - fb), "only English failures and both-failures removed")],
      ["Failed English 35%, failed Maths 42%", "Failed at least one = 35 + 42 − 12 = 65%", "Passed both = 100 − 65 = 35%"],
      "n(A ∪ B) = n(A) + n(B) − n(A ∩ B)", "Work with failure sets and use inclusion–exclusion.")

    Bm = Fr(336) / Fr(70, 100)
    Cm = Bm / Fr(120, 100)
    assert Cm == 400
    q("pcmp", "L3", "o", "A scored 30% fewer marks than B, and B scored 20% more than C. If A scored 336, C scored:",
      N(Cm),
      [(N(Bm), "B's score reported"), (N(Bm * Fr(80, 100)), "'20% more' reversed as 20% less of B"),
       (N(Fr(336) / Fr(120, 100)), "30% step skipped")],
      ["B = 336/0.7 = 480", "C = 480/1.2 = 400"],
      "Undo each change by division", "C = B/1.2, not 0.8B.")

    q("pcmp", "L3", "o",
      "The price of an item rises from ₹80 to ₹100. Consider:\n\nI. The increase is 25%.\nII. To return to ₹80, the new price must fall by 20%.\nIII. The old price is 75% of the new price.\n\nWhich are correct?",
      "I and II only",
      [("I and III only", "III: 80/100 = 80%, not 75%"), ("I, II and III", "III accepted by symmetry"), ("II only", "I wrongly rejected")],
      ["Increase = 20/80 = 25% (I true)", "Decrease = 20/100 = 20% (II true)", "80/100 = 80% (III false)"],
      "Change % = change ÷ original", "Rise and fall percentages differ because the base differs.", kind="statement")

    q("pcmp", "L2", "o", "If A is 3/5 of B, then B is how much percent more than A?",
      P(Fr(2, 3) * 100),
      [(P(40), "A less than B reported"), (P(60), "A as a percentage of B"), (P(Fr(5, 3) * 100), "B as a percentage of A")],
      ["A = 3, B = 5", "B exceeds A by 2 on base 3 = 66 2/3%"],
      "(B − A)/A × 100", "Base is A.")

    N_ = Fr(2090) / (Fr(88, 100) * Fr(95, 100) * Fr(10, 100))
    assert N_ == 25000
    q("pcmp", "L3", "o", "In a two-candidate election, 12% of voters did not vote and 5% of the votes cast were invalid. The winner got 55% of the valid votes and won by 2,090 votes. The total number of voters was:",
      N(N_),
      [(N(Fr(2090) / (Fr(88, 100) * Fr(10, 100))), "invalid votes ignored"),
       (N(Fr(2090) / (Fr(95, 100) * Fr(10, 100))), "non-voters ignored"),
       (N(Fr(2090) / (Fr(88, 100) * Fr(95, 100) * Fr(5, 100))), "margin taken as 5% instead of 10% of valid votes")],
      ["Votes cast = 0.88N; valid = 0.95 × 0.88N = 0.836N", "Margin = (55 − 45)% of valid = 0.0836N",
       "0.0836N = 2,090 ⇒ N = 25,000"],
      "Margin = (winner% − loser%) × valid votes", "Two layers of shrinkage before the margin.")

    pen = Fr(60, 100) * Fr(125, 100)
    more = (1 - pen) / pen * 100
    q("pcmp", "L3", "o", "A pen costs 60% of a notebook, and a notebook costs 25% more than a file. By what percentage is the file costlier than the pen?",
      P(more),
      [(P(25), "pen cheaper than file reported"), (P(15), "rates netted: 40 − 25"), (P(pen * 100), "pen as a percentage of file")],
      ["File = 100 ⇒ notebook 125 ⇒ pen 75", f"File exceeds pen by 25 on base 75 = {P(more)}"],
      "Chain: pen = 0.6 × 1.25 × file", "The base for 'costlier than the pen' is the pen.")

    # ===================== Percentage increase and decrease =====================
    q("pid", "L1", "f", "The price of a gas cylinder rises from ₹240 to ₹282. The percentage increase is:",
      P(Fr(42, 240) * 100),
      [(P(D(Fr(42, 282) * 100)), "increase divided by new price"), (P(42), "absolute rise read as a percentage"),
       (P(Fr(42, 2400) * 100), "decimal slip")],
      ["Rise = 282 − 240 = 42", "42/240 × 100 = 17.5%"],
      "% increase = rise ÷ original × 100", "Base is the original price.")

    q("pid", "L1", "f", "The price of sugar falls by 20%. By what percentage must a household increase consumption to keep its expenditure unchanged?",
      P(25),
      [(P(20), "same percentage assumed"), (P(Fr(50, 3)), "20/120 used"), (P(80), "new price ratio reported")],
      ["Price 100 → 80", "Consumption must rise 100/80 = 1.25 ⇒ 25%"],
      "Required % = r/(100 − r) × 100", "Expenditure = price × quantity must stay constant.")

    c = (1 - Fr(110, 125)) * 100
    assert c == 12
    q("pid", "L2", "f", "The price of rice rises by 25%. A family reduces consumption so that its expenditure on rice rises by only 10%. The percentage reduction in consumption is:",
      P(c),
      [(P(15), "rates subtracted: 25 − 10"), (P(20), "full compensation for 25% rise"), (P(Fr(88, 10)), "new consumption ratio 0.88 misread as 8.8%")],
      ["New expenditure/Old = 1.10 = 1.25 × q", "q = 1.10/1.25 = 0.88", "Reduction = 12%"],
      "Expenditure = Price × Quantity", "Divide the multipliers, do not subtract percentages.")

    save = Fr(800) * Fr(20, 100)
    newp = save / 4
    old = newp / Fr(80, 100)
    assert old == 50
    q("pid", "L1", "f", "A 20% reduction in the price of apples lets a buyer get 4 kg more for ₹800. The original price per kg was:",
      Rs(old),
      [(Rs(newp), "reduced price reported"), (Rs(Fr(800, 4)), "₹800 divided by 4 kg"), (Rs(save), "money saved reported")],
      ["Saving = 20% of 800 = ₹160, which buys 4 kg", "Reduced price = ₹40/kg", "Original = 40/0.8 = ₹50/kg"],
      "Saving ÷ extra quantity = reduced price", "The ₹160 buys the extra kg at the reduced price.")

    n = Fr(945) / Fr(135, 100)
    ans = n * Fr(65, 100)
    assert n == 700
    q("pid", "L2", "f", "A number increased by 35% becomes 945. If the same number had instead been decreased by 35%, the result would be:",
      N(ans),
      [(N(Fr(945) * Fr(65, 100)), "35% deducted from 945 instead of the original"), (N(n * Fr(35, 100)), "35% of the original reported"),
       (N(Fr(945) * Fr(30, 100)), "70% of 945 subtracted")],
      ["Original = 945/1.35 = 700", "Decreased value = 0.65 × 700 = 455"],
      "Original = New ÷ (1 + r)", "Recover the original first.")

    c = (1 - Fr(117, 130)) * 100
    assert c == 10
    q("pid", "L3", "o", "Petrol prices rise by 30%. A motorist wants to limit the rise in his fuel bill to 17%. By what percentage must he cut consumption?",
      P(c),
      [(P(13), "rates subtracted"), (P(D(Fr(30, 130) * 100)), "full compensation for price rise"),
       (P(D(Fr(13, 117) * 100)), "gap divided by 117 instead of 130")],
      ["1.17 = 1.30 × q", "q = 0.90", "Cut = 10%"],
      "q = (1 + e)/(1 + p)", "Divide new expenditure multiplier by price multiplier.")

    newp = Fr(1344) * Fr(125, 1000) / 3
    old = newp / Fr(875, 1000)
    assert old == 64
    q("pid", "L3", "o", "A 12.5% fall in the price of dal enables a buyer to purchase 3 kg more for ₹1,344. The original price per kg was:",
      Rs(old),
      [(Rs(newp), "reduced price reported"), (Rs(Fr(1344, 3)), "total divided by extra quantity"),
       (Rs(newp * Fr(875, 1000)), "reduction applied twice")],
      ["Saving = 12.5% of 1,344 = ₹168 buys 3 kg ⇒ reduced price ₹56", "Original = 56 ÷ 0.875 = ₹64"],
      "Reduced price = saving ÷ extra kg", "Scale back up to get the original.")

    x = (1 / (Fr(8, 10) * Fr(12, 10)) - 1) * 100
    q("pid", "L3", "o", "An employee's pay is cut by 20% and later raised by 20%. By what percentage must it now be raised to restore the original pay?",
      P(x),
      [(P(4), "net loss 4% taken as needed rise"), (P(20), "raise equal to cut assumed"), ("0%", "believes cut and raise cancel")],
      ["100 → 80 → 96", "Needed rise = 4/96 = 4 1/6%"],
      "Required % = loss/remaining × 100", "The base is 96, not 100.")
    assert x == Fr(25, 6)

    rv = Fr(75, 100) * Fr(160, 100)
    assert rv == Fr(12, 10)
    q("pid", "L3", "o", "A museum cuts its ticket price by 25% and the number of visitors rises by 60%. The effect on ticket revenue is:",
      "20% increase",
      [("35% increase", "percentages added"), ("20% decrease", "sign reversed"), ("15% increase", "cross term 15% taken as net effect")],
      ["Revenue multiplier = 0.75 × 1.60 = 1.20", "Increase = 20%"],
      "Revenue = Price × Volume", "Net % = a + b + ab/100 = 60 − 25 − 15.")

    d = Fr(10, 110) * 100
    q("pid", "L3", "o", "Water expands by 10% in volume on freezing. By what percentage does ice shrink on melting back to water?",
      P(d),
      [(P(10), "same percentage assumed"), (P(11), "rough reciprocal"), (P(9), "decimal truncated")],
      ["Water 100 → ice 110", "Shrink 10 on base 110 = 9 1/11%"],
      "r/(100 + r) × 100", "Base is the ice volume.")

    e = (Fr(5, 3) - Fr(3, 5)) / Fr(5, 3) * 100
    assert e == 64
    q("pid", "L3", "o", "A student multiplied a number by 3/5 instead of 5/3. The percentage error in the result is:",
      P(e),
      [(P(36), "ratio of results taken as the error"), (P(D((Fr(5, 3) - Fr(3, 5)) / Fr(3, 5) * 100)), "error measured on the wrong result"),
       (P(40), "(5 − 3)/5 used")],
      ["Correct = 5N/3, obtained = 3N/5", "Error = 16N/15", "% error = (16/15)/(5/3) × 100 = 64%"],
      "% error = |correct − obtained| ÷ correct × 100", "Measure against the correct value.")

    save = Fr(120, 6)
    newp = save / 5
    old = newp * Fr(6, 5)
    assert old == Fr(24, 5)
    q("pid", "L3", "o", "Because of a 16 2/3% fall in the price of mangoes, a buyer gets 5 more mangoes for ₹120. The original price per mango was:",
      RsD(old),
      [(RsD(newp), "reduced price reported"), (RsD(Fr(120, 5)), "₹120 ÷ 5"), (RsD(newp * Fr(5, 6)), "reduction applied twice")],
      ["Saving = 1/6 of 120 = ₹20 buys 5 mangoes ⇒ reduced price ₹4", "Original = 4 × 6/5 = ₹4.80"],
      "Reduced price = saving ÷ extra count", "16 2/3% = 1/6.")

    # boys/girls
    assert Fr(30 - 24, 24 - 20) == Fr(3, 2)
    q("pid", "L3", "o", "In a school, the number of boys increases by 20% and the number of girls by 30%, so that total strength rises by 24%. The original ratio of boys to girls was:",
      "3:2",
      [("2:3", "alligation sides swapped"), ("3:5", "boys to total reported"), ("2:5", "girls to total reported")],
      ["20b + 30g = 24(b + g)", "6g = 4b ⇒ b : g = 3 : 2"],
      "Alligation on percentage growth", "The group nearer the average growth is larger.")

    pr = Fr(54, 48) / Fr(90, 100)
    assert pr == Fr(5, 4)
    q("pid", "L3", "o", "A shop's revenue rose from ₹4.8 lakh to ₹5.4 lakh while units sold fell by 10%. The percentage change in average price per unit is:",
      "25% increase",
      [("22.5% increase", "12.5% + 10% added"), ("12.5% increase", "revenue change taken as price change"), ("2.5% increase", "12.5% − 10%")],
      ["Revenue multiplier = 5.4/4.8 = 1.125", "Price multiplier = 1.125/0.9 = 1.25"],
      "Price = Revenue ÷ Volume", "Divide multipliers.")

    X, Y = Fr(140) * Fr(120, 100), Fr(150)
    assert (X - Y) / Y * 100 == 12
    q("pid", "L3", "o", "X earns 40% more than Y. Y gets a 50% raise and X a 20% raise. Now:",
      "X earns 12% more than Y",
      [("X earns 10% more than Y", "raises netted: 40 − 30"), ("Y earns 12% more than X", "direction reversed"),
       ("X earns 10.71% more than Y", "gap measured on X's new salary")],
      ["Y = 100 → 150; X = 140 → 168", "X exceeds Y by 18 on 150 = 12%"],
      "Apply each raise to its own base", "Compare on Y's new salary.")

    # ===================== Population / strength / quantity change =====================
    P0 = 50000
    q("pop", "L1", "f", f"A town's population of {N(P0)} grows at 8% per annum. Its population after 2 years will be:",
      N(P0 * Fr(108, 100) ** 2),
      [(N(P0 * Fr(116, 100)), "simple growth of 16%"), (N(P0 * Fr(108, 100)), "only one year applied"),
       (N(P0 * Fr(92, 100) ** 2), "decline instead of growth")],
      ["50,000 × 1.08 = 54,000", "54,000 × 1.08 = 58,320"],
      "P(1 + r)^n", "Growth compounds on the new base.")

    v = 72900
    q("pop", "L1", "f", f"A machine loses 10% of its value every year. After 3 years it is worth {Rs(v)}. Its original value was:",
      Rs(Fr(v) / Fr(9, 10) ** 3),
      [(Rs(D(Fr(v) / Fr(7, 10))), "simple 30% depreciation"), (Rs(D(Fr(v) * Fr(11, 10) ** 3)), "10% added back each year"),
       (Rs(Fr(v) / Fr(9, 10) ** 2), "only two years undone")],
      ["Original × 0.9³ = 72,900", "Original = 72,900/0.729 = 1,00,000"],
      "V = V0(1 − r)^n", "Adding 10% back is not the inverse of losing 10%.")

    q("pop", "L2", "f", "A village of 20,000 people grows by 10% in the first year and declines by 10% in the second. The population after 2 years is:",
      N(20000 * Fr(11, 10) * Fr(9, 10)),
      [("20,000", "assumes +10% and −10% cancel"), ("20,200", "net 1% taken as gain"), ("19,000", "decline applied to original twice")],
      ["20,000 × 1.1 = 22,000", "22,000 × 0.9 = 19,800"],
      "Successive multipliers 1.1 × 0.9 = 0.99", "Equal up and down moves give a net fall.")

    q("pop", "L2", "f", "A school's enrolment rose by 15% to 1,610. The earlier enrolment was:",
      N(Fr(1610) / Fr(115, 100)),
      [(N(Fr(1610) * Fr(85, 100)), "15% deducted from the new figure"), (N(Fr(1610) * Fr(115, 100)), "multiplied instead of divided"),
       (N(1610 - 15), "15 subtracted")],
      ["Earlier × 1.15 = 1,610", "Earlier = 1,400"],
      "Old = New ÷ (1 + r)", "15% of 1,610 is not 15% of the old value.")

    m, f_ = 6600, 5400
    new = m * Fr(11, 10) + f_ * Fr(12, 10)
    q("pop", "L2", "f", "A village has 12,000 people, 55% of them male. Next year males increase by 10% and females by 20%. The new population is:",
      N(new),
      [(N(12000 * Fr(115, 100)), "average 15% applied to total"), (N(m * Fr(12, 10) + f_ * Fr(11, 10)), "rates swapped between males and females"),
       (N(12000 + m * Fr(1, 10)), "female growth left out")],
      ["Males 6,600 → 7,260; females 5,400 → 6,480", "Total = 13,740"],
      "Grow each group separately", "Weights are 55:45, not 50:50.")

    P0 = 250000
    q("pop", "L3", "o", "A city of 2,50,000 grows 5% in year 1 and 8% in year 2, then declines 4% in year 3. The population at the end of year 3 is:",
      N(P0 * Fr(105, 100) * Fr(108, 100) * Fr(96, 100)),
      [(N(P0 * Fr(109, 100)), "rates added: 5 + 8 − 4"), (N(P0 * Fr(105, 100) * Fr(108, 100) * Fr(104, 100)), "decline treated as growth"),
       (N(P0 * Fr(105, 100) * Fr(108, 100)), "year 3 ignored")],
      ["2,50,000 × 1.05 = 2,62,500", "× 1.08 = 2,83,500", "× 0.96 = 2,72,160"],
      "P × Π(1 ± r_i)", "Each year's change acts on the previous year's figure.")

    def mig(p, g, out, n, before=False):
        for _ in range(n):
            p = (p - out) * g if before else p * g - out
        return p
    q("pop", "L3", "o", "A town of 50,000 grows by 10% a year, but 2,000 people move out at the end of each year. The population after 2 years is:",
      N(mig(50000, Fr(11, 10), 2000, 2)),
      [(N(mig(50000, Fr(11, 10), 2000, 2, True)), "migration deducted before growth"), (N(50000 * Fr(12, 10) - 4000), "simple 20% growth then 4,000 removed"),
       (N(50000 * Fr(121, 100) - 4000), "compound growth, then all migration removed at the end")],
      ["Year 1: 55,000 − 2,000 = 53,000", "Year 2: 58,300 − 2,000 = 56,300"],
      "P_next = P × 1.1 − 2,000", "Year-2 growth applies after year-1 migration.")

    q("pop", "L3", "o", "A bacterial culture grows by 25% every hour. After 2 hours it has 22,500 cells. The initial count was:",
      N(Fr(22500) / Fr(125, 100) ** 2),
      [(N(Fr(22500) / Fr(150, 100)), "simple 50% growth"), (N(Fr(22500) * Fr(75, 100)), "25% removed once"),
       (N(D(Fr(22500) * Fr(75, 100) ** 2)), "25% removed twice")],
      ["Initial × 1.25² = 22,500", "Initial = 22,500/1.5625 = 14,400"],
      "N0 = N ÷ (1 + r)^t", "Reverse growth by dividing, not by subtracting 25%.")

    v0 = 500000
    v3 = v0 * Fr(8, 10) ** 2 * Fr(9, 10)
    q("pop", "L3", "o", "A machine bought for ₹5,00,000 depreciates 20% a year for two years and 10% in the third year (reducing balance). The total loss in value over 3 years is:",
      Rs(v0 - v3),
      [(Rs(Fr(v0) * Fr(50, 100)), "rates added: 20 + 20 + 10"), (Rs(v0 - (v0 * Fr(64, 100) - v0 * Fr(10, 100))), "third-year 10% taken on original cost"),
       (Rs(v3), "value after 3 years reported, not the loss")],
      ["5,00,000 × 0.8 × 0.8 = 3,20,000", "× 0.9 = 2,88,000", "Loss = 2,12,000"],
      "Loss = V0 − V0 × Π(1 − r)", "Reducing balance: each rate applies to the written-down value.")

    b = Fr(1800, 3)
    q("pop", "L3", "o", "In a college, the number of boys rises by 20% and the number of girls falls by 10%, leaving total strength of 1,800 unchanged. The number of boys now is:",
      N(b * Fr(12, 10)),
      [(N(b), "original number of boys"), (N(2 * b * Fr(9, 10)), "girls now reported"), (N(2 * b), "original girls reported")],
      ["0.2B = 0.1G ⇒ G = 2B", "B = 600, G = 1,200", "Boys now = 720"],
      "Gains and losses must balance when the total is unchanged", "Ratio from 20B = 10G.")

    base = Fr(237600) / (Fr(11, 10) * Fr(12, 10) * Fr(9, 10))
    assert base == 200000
    q("pop", "L3", "o", "Over three years a district's population rose 10%, then 20%, then fell 10%, reaching 2,37,600. The population at the start was:",
      N(base),
      [(N(Fr(237600) / Fr(12, 10)), "net +20% (rates added)"), (N(D(Fr(237600) / (Fr(11, 10) * Fr(12, 10) * Fr(11, 10)))), "the 10% fall treated as a rise"),
       (N(Fr(237600) / Fr(11, 10)), "only the first year undone")],
      ["Multiplier = 1.1 × 1.2 × 0.9 = 1.188", "Start = 2,37,600/1.188 = 2,00,000"],
      "P0 = P3 ÷ Π(1 ± r)", "Undo all three years together.")

    A2, B2 = 100000 * Fr(121, 100), 150000 * Fr(81, 100)
    assert B2 - A2 == 500
    q("pop", "L3", "o", "City A (1,00,000) grows 10% a year; city B (1,50,000) shrinks 10% a year. After 2 years:",
      "B exceeds A by 500",
      [("A exceeds B by 500", "direction reversed"), ("Both are equal", "simple (non-compound) change used"),
       ("B exceeds A by 1,500", "A grown simply, B shrunk with compounding")],
      ["A = 1,00,000 × 1.21 = 1,21,000", "B = 1,50,000 × 0.81 = 1,21,500"],
      "Compound both", "Simple change gives 1,20,000 each — a trap.")

    def tank(v, weeks, before=False):
        for _ in range(weeks):
            v = (v + 5) * Fr(8, 10) if before else v * Fr(8, 10) + 5
        return v
    q("pop", "L3", "o", "A tank holds 100 L. Each week 20% of the water present evaporates, and 5 L is added at the end of the week. Water in the tank after 2 weeks is:",
      N(tank(100, 2)) + " L",
      [(N(tank(100, 2, True)) + " L", "water added before evaporation"), ("70 L", "20% of 100 lost each week (simple)"),
       ("64 L", "weekly additions ignored")],
      ["Week 1: 80 + 5 = 85", "Week 2: 68 + 5 = 73"],
      "V_next = 0.8V + 5", "Evaporation acts on the current level.")

    q("pop", "L3", "o", "A town of 80,000 has a birth rate of 3.5% and a death rate of 1.5% per year. Its population after 2 years is:",
      N(80000 * Fr(102, 100) ** 2),
      [(N(80000 * Fr(104, 100)), "net 2% not compounded"), (N(D(80000 * Fr(1035, 1000) ** 2)), "death rate ignored"),
       (N(80000 * Fr(105, 100) ** 2), "birth and death rates added")],
      ["Net growth = 3.5 − 1.5 = 2%", "80,000 × 1.02² = 83,232"],
      "Net rate = birth − death", "Deaths reduce the growth rate.")

    n = next(k for k in range(1, 20) if Fr(88, 100) ** k < Fr(1, 2))
    assert n == 6
    q("pop", "L3", "o", "A car loses 12% of its value every year. After how many complete years will its value first fall below half the purchase price?",
      f"{n} years",
      [("5 years", "stopped at 52.8% of cost, still above half"), ("4 years", "simple 12% a year: 50/12"), ("7 years", "one year too many")],
      ["0.88⁵ = 0.528 (above half)", "0.88⁶ = 0.464 (below half)"],
      "Find least n with 0.88^n < 0.5", "Test values; compounding slows the fall.")

    # ===================== Successive percentage change =====================
    q("spc", "L1", "f", "Two successive discounts of 20% and 10% are equivalent to a single discount of:",
      P(28),
      [(P(30), "discounts added"), (P(32), "cross term added instead of subtracted"), (P(2), "cross term taken as answer")],
      ["0.8 × 0.9 = 0.72", "Single discount = 28%"],
      "a + b − ab/100", "The second discount applies to a reduced price.")

    q("spc", "L1", "f", "A price is increased by 10% and then again by 10%. The net increase is:",
      P(21),
      [(P(20), "increases added"), (P(1), "only the cross term"), (P(22), "cross term doubled")],
      ["1.1 × 1.1 = 1.21", "Net = 21%"],
      "a + b + ab/100", "Second increase applies on 110.")

    q("spc", "L2", "f", "The length of a rectangle is increased by 20% and its breadth decreased by 10%. The area changes by:",
      "8% increase",
      [("10% increase", "percentages netted"), ("12% increase", "cross term added"), ("2% increase", "cross term alone")],
      ["1.2 × 0.9 = 1.08", "Area up 8%"],
      "a + b + ab/100 with b negative", "20 − 10 − 2 = 8.")

    q("spc", "L2", "f", "A salary is increased by 25% and then decreased by 20%. The net effect is:",
      "No change",
      [("5% increase", "percentages netted"), ("5% decrease", "sign error"), ("1% decrease", "equal-rate rule misapplied")],
      ["1.25 × 0.8 = 1.00", "No net change"],
      "Multiply the factors", "25% up and 20% down are exact inverses.")

    o = Fr(810) / (Fr(12, 10) * Fr(75, 100))
    assert o == 900
    q("spc", "L2", "f", "A price is raised by 20% and then reduced by 25%, ending at ₹810. The original price was:",
      Rs(o),
      [(Rs(D(Fr(810) / Fr(95, 100))), "net −5% (rates added)"), (Rs(Fr(810) * Fr(9, 10)), "net factor multiplied instead of divided"),
       (Rs(Fr(810) / Fr(75, 100)), "20% rise ignored")],
      ["Net factor = 1.2 × 0.75 = 0.9", "Original = 810/0.9 = ₹900"],
      "Original = Final ÷ Π factors", "Net change is −10%, not −5%.")

    mp = 8000
    q("spc", "L3", "o", "A television marked ₹8,000 is sold after successive discounts of 10%, 20% and 25%. The selling price is:",
      Rs(mp * Fr(9, 10) * Fr(8, 10) * Fr(75, 100)),
      [(Rs(mp * Fr(45, 100)), "discounts added (55%)"), (Rs(mp * Fr(72, 100)), "third discount missed"),
       (Rs(mp * Fr(60, 100)), "first discount missed")],
      ["8,000 × 0.9 = 7,200", "× 0.8 = 5,760", "× 0.75 = 4,320"],
      "SP = MP × Π(1 − d)", "Each discount is on the already-reduced price.")

    v = Fr(121, 100) * Fr(8, 10)
    q("spc", "L3", "o", "The radius of a cylinder is increased by 10% and its height reduced by 20%. Its volume:",
      "decreases by 3.2%",
      [("increases by 1%", "21 − 20 netted"), ("increases by 3.2%", "sign reversed"), ("decreases by 10%", "radius change used once")],
      ["V ∝ r²h", "1.1² × 0.8 = 0.968", "Decrease 3.2%"],
      "Radius enters squared", "Square the radius factor first.")
    assert v == Fr(968, 1000)

    q("spc", "L3", "o", "A price is first increased by x% and then decreased by x%, causing a net loss of 4%. The value of x is:",
      "20",
      [("2", "√4 without the ×10"), ("4", "net loss taken as x"), ("25", "100 ÷ 4")],
      ["Net change = −x²/100", "x²/100 = 4 ⇒ x = 20"],
      "Equal up/down ⇒ loss = x²/100 %", "The loss is always x²/100 %.")

    r = Fr(12, 10) * Fr(8, 10) * Fr(9, 10) * Fr(11, 10)
    q("spc", "L3", "o", "A firm raises price by 20% and sales volume falls 20%. Later it cuts price by 10% and volume rises 10%. The net change in revenue from the start is:",
      P(D((1 - r) * 100)) + " decrease",
      [("No change", "all percentages cancel"), ("4% decrease", "first stage only"), ("1% decrease", "second stage only")],
      ["Stage 1: 1.2 × 0.8 = 0.96", "Stage 2: 0.9 × 1.1 = 0.99", "Net: 0.9504 ⇒ 4.96% decrease"],
      "Revenue factor = Π(price) × Π(volume)", "Both stages lose revenue.")

    q("spc", "L3", "o", "A wage is cut by 10%, then raised by 10%, then cut again by 10%. The overall change is:",
      "10.9% decrease",
      [("10% decrease", "percentages added"), ("8.91% decrease", "factor 0.891 misread"), ("11% decrease", "first two steps −1%, then −10% added")],
      ["0.9 × 1.1 × 0.9 = 0.891", "Decrease 10.9%"],
      "Multiply all factors", "Additive shortcuts fail across three steps.")

    q("spc", "L3", "o", "Three successive increases of 10%, 20% and 30% are equivalent to a single increase of:",
      P(D((Fr(11, 10) * Fr(12, 10) * Fr(13, 10) - 1) * 100)),
      [(P(60), "rates added"), (P(62), "first two compounded, third added"), (P(56), "first increase missed")],
      ["1.1 × 1.2 = 1.32", "1.32 × 1.3 = 1.716 ⇒ 71.6%"],
      "Π(1 + r) − 1", "Three-way compounding adds more than the pairwise cross terms.")

    n = Fr(2700) / Fr(9, 100)
    assert n == 30000
    q("spc", "L3", "o", "A number is increased by 30% and the result decreased by 30%. The final value is 2,700 less than the original. The original number is:",
      N(n),
      [(N(Fr(2700) / Fr(1, 100)), "net loss taken as 1%"), (N(D(Fr(2700) / Fr(21, 100))), "0.3 × 0.7 used as loss"),
       (N(D(Fr(2700) / Fr(91, 100))), "divided by final factor 0.91")],
      ["1.3 × 0.7 = 0.91 ⇒ loss 9%", "0.09N = 2,700 ⇒ N = 30,000"],
      "Loss = x²/100 %", "The 9% loss is on the original.")

    x = (1 - 1 / (Fr(125, 100) * Fr(12, 10))) * 100
    q("spc", "L3", "o", "A box's length is increased by 25% and breadth by 20%. By what percentage must its height be reduced to keep the volume unchanged?",
      P(x),
      [(P(45), "rates added"), (P(50), "combined 50% increase taken as the cut"), (P(30), "net of 45 and cross term misapplied")],
      ["1.25 × 1.2 = 1.5", "Height factor = 1/1.5 = 2/3", "Reduction = 33 1/3%"],
      "Required cut = (F − 1)/F", "Cut = 50/150, not 50%.")

    r = Fr(121, 100) * Fr(79, 100)
    q("spc", "L3", "o", "A price rises by 10% each year for two years and then falls by 21%. Compared with the start, the price is now:",
      P(D((1 - r) * 100)) + " lower",
      [("unchanged", "21% rise and 21% fall assumed to cancel"), (P(D((1 - r) * 100)) + " higher", "sign reversed"), ("1% lower", "21 − 20 netted")],
      ["1.1² = 1.21", "1.21 × 0.79 = 0.9559", "4.41% lower"],
      "Multiply factors", "Equal percentage up and down leaves a net fall.")

    d = (1 - Fr(68, 100) / Fr(85, 100)) * 100
    assert d == 20
    q("spc", "L3", "o", "Two successive discounts of 15% and d% equal a single discount of 32%. Then d is:",
      P(d),
      [(P(17), "32 − 15 subtracted"), (P(47), "discounts added"), (P(D(Fr(17, 68) * 100)), "gap divided by final price")],
      ["0.85 × (1 − d) = 0.68", "1 − d = 0.8 ⇒ d = 20%"],
      "Π(1 − d) = 1 − D", "Second discount acts on 85, so 17/85.")
