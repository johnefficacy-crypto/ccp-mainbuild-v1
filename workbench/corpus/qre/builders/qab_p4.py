"""QRE-QA-B part 4: Data Interpretation (tabular, bar/line, pie, caselet, set-based, mixed, data sufficiency).
Charts are given as markdown tables. Every key and distractor is computed from the data below."""
from qab_common import *

from decimal import Decimal, ROUND_HALF_UP
_n_common = n


def n(x, d=2):
    """Half-up rounding at d decimals (avoids float half-even, e.g. 50.625 -> 50.63)."""
    if isinstance(x, (F, float)) and not (isinstance(x, F) and x.denominator == 1):
        xd = Decimal(x.numerator) / Decimal(x.denominator) if isinstance(x, F) else Decimal(repr(x))
        x = float(xd.quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP))
    return _n_common(x, d)


P2 = lambda v: n(v) + "%"          # percentage formatter (2 dp, trailing zeros stripped)


def ratio(a, b):
    a, b = F(a), F(b)
    r = a / b
    return f"{r.numerator} : {r.denominator}"


def dset(B, M, tier, lv, gid, stim, items):
    """items: (question, key, cands, steps, formula, trap, fmt, unit)."""
    for (qt, key, cands, steps, formula, trap, fmt, unit) in items:
        q(B, M, lv, tier, qt, key, cands, steps, formula, trap, fmt=fmt, unit=unit,
          kind="case", group=gid, pre=stim + "\n\n")


# =====================================================================
def tabular(B):
    M = "qa-tabular-data-interpretation-e6e4b3de"
    # ---------- foundation set ----------
    fac = ["P", "Q", "R", "S", "T"]
    y23 = dict(P=45, Q=60, R=38, S=52, T=55)
    y24 = dict(P=54, Q=66, R=57, S=52, T=70)
    stim = ("The table shows the number of units (in thousands) produced by five factories in 2023 and 2024.\n\n"
            + table(["Factory", "2023", "2024"], [[f, y23[f], y24[f]] for f in fac]))
    s23, s24 = sum(y23.values()), sum(y24.values())
    inc = {f: F(y24[f] - y23[f], y23[f]) for f in fac}
    gt20 = sum(1 for f in fac if inc[f] > F(1, 5))
    ge20 = sum(1 for f in fac if inc[f] >= F(1, 5))
    anyinc = sum(1 for f in fac if inc[f] > 0)
    assert (gt20, ge20, anyinc) == (2, 3, 4)
    th = " thousand"
    dset(B, M, "foundation", "L1", "QAB-TAB-F1", stim, [
        ("What was the total production of all five factories in 2024?", s24,
         [(s23, "read the 2023 column"), (s24 - y24["T"], "left out factory T"), (F(s23 + s24, 2), "averaged the two years")],
         [f"2024 total = 54 + 66 + 57 + 52 + 70 = {s24} thousand"], "Column total", "Use the correct year's column.", n, th),
        ("By what percentage did the production of factory R increase from 2023 to 2024?", inc["R"] * 100,
         [(F(19, 57) * 100, "took the 2024 figure as base"), (19, "reported the absolute increase as a percentage"),
          (F(57, 38) * 100, "reported the ratio 2024/2023 as the increase")],
         ["Increase = 57 − 38 = 19", "% increase = 19/38 × 100 = 50%"], "% change = change / old value × 100",
         "The base is the earlier (2023) value.", P2, ""),
        ("What is the ratio of the combined production of P and Q in 2023 to the combined production of S and T in 2024?",
         ratio(y23["P"] + y23["Q"], y24["S"] + y24["T"]),
         [(ratio(y24["S"] + y24["T"], y23["P"] + y23["Q"]), "reversed the ratio"),
          (ratio(y24["P"] + y24["Q"], y24["S"] + y24["T"]), "took P and Q from 2024"),
          (ratio(y23["P"] + y23["Q"], y23["S"] + y23["T"]), "took S and T from 2023")],
         ["P + Q (2023) = 45 + 60 = 105", "S + T (2024) = 52 + 70 = 122", "Ratio = 105 : 122"],
         "Ratio of sums", "Pick each pair from the year the question names.", None, ""),
        ("What was the average production per factory in 2023?", F(s23, 5),
         [(F(s23, 4), "divided by 4 instead of 5"), (F(s24, 5), "used the 2024 column"), (F(s23 - y23["R"], 4), "left out the smallest factory (R) and averaged the other four")],
         [f"2023 total = {s23} thousand", f"Average = {s23}/5 = {n(F(s23,5))} thousand"], "Average = total / number of items",
         "Count all five factories.", n, th),
        ("In how many factories did production in 2024 exceed that of 2023 by more than 20%?", gt20,
         [(ge20, "counted P, whose increase is exactly 20%"), (anyinc, "counted every factory that showed any increase"),
          (5, "counted all factories, including S with no change")],
         ["Increases: P 20%, Q 10%, R 50%, S 0%, T 27.27%", "More than 20%: R and T ⇒ 2"], "% change per row",
         "'More than 20%' excludes exactly 20%.", n, ""),
    ])
    # ---------- officer set 1 ----------
    co = ["A", "B", "C", "D", "E"]
    rev = dict(A=480, B=560, C=400, D=640, E=520)
    ex = dict(A=75, B=80, C=70, D=85, E=65)
    stim = ("The table shows the revenue (₹ crore) of five companies in a year and their expenditure as a percentage of revenue. "
            "Profit = Revenue − Expenditure.\n\n"
            + table(["Company", "Revenue (₹ crore)", "Expenditure (% of revenue)"], [[c, rev[c], f"{ex[c]}%"] for c in co]))
    E = {c: F(rev[c] * ex[c], 100) for c in co}
    Pf = {c: rev[c] - E[c] for c in co}
    assert [Pf[c] for c in co] == [120, 112, 120, 96, 182]
    nD = F(rev["D"] * 9, 8)
    newm = (nD - E["D"]) / nD * 100
    Cr = lambda v: "₹" + n(v) + " crore"
    dset(B, M, "officer", "L4", "QAB-TAB-O1", stim, [
        ("The profit of company E is what percentage more than the profit of company B?", (Pf["E"] - Pf["B"]) / Pf["B"] * 100,
         [((Pf["E"] - Pf["B"]) / Pf["E"] * 100, "used E's profit as the base"),
          (F(35, 20) * 100 - 100, "compared profit margins (35% vs 20%) instead of profits"),
          ((Pf["E"] - Pf["B"]) / rev["B"] * 100, "divided the difference by B's revenue")],
         ["Profit E = 520 × 35% = 182; Profit B = 560 × 20% = 112", "(182 − 112)/112 × 100 = 62.5%"],
         "% more = difference / base × 100", "Margins differ from profits because revenues differ.", P2, ""),
        ("What is the total expenditure of companies A, C and E together?", E["A"] + E["C"] + E["E"],
         [(E["A"] + E["C"] + Pf["E"], "used 35% instead of 65% for E"), (E["A"] + E["D"] + E["E"], "took D in place of C"),
          (Pf["A"] + Pf["C"] + Pf["E"], "added profits instead of expenditures")],
         ["A: 480 × 75% = 360", "C: 400 × 70% = 280", "E: 520 × 65% = 338", "Total = 978"],
         "Expenditure = revenue × expenditure %", "Apply each company's own percentage.", Cr, ""),
        ("Next year the revenue of D rises by 12.5% while its expenditure stays the same in rupees. What is D's new profit as a percentage of its new revenue?",
         newm,
         [(15, "kept the old 15% margin"), ((nD - E["D"]) / rev["D"] * 100, "divided the new profit by the old revenue"),
          (F(15 * 9, 8), "scaled the old margin by 1.125")],
         ["New revenue = 640 × 1.125 = 720", "Expenditure = 640 × 85% = 544", "New profit = 176 ⇒ 176/720 = 24.44%"],
         "Margin = profit / revenue", "Fixed expenditure means the margin rises more than proportionately.", P2, ""),
        ("What is the average profit of the five companies?", F(sum(Pf.values()), 5),
         [(F(sum(Pf.values()) - Pf["E"], 4), "left out company E"), (F(sum(Pf.values()), 4), "divided by 4"),
          (F(sum(rev.values()), 5) * (1 - F(sum(ex.values()), 500)), "multiplied average revenue by average margin")],
         ["Profits: 120, 112, 120, 96, 182 ⇒ total 630", "Average = 630/5 = 126"],
         "Average of computed values", "Average margin × average revenue is not the average profit.", Cr, ""),
        ("What is the ratio of the expenditure of B to that of D?", ratio(E["B"], E["D"]),
         [(ratio(80, 85), "compared the percentages"), (ratio(E["D"], E["B"]), "reversed the ratio"), (ratio(rev["B"], rev["D"]), "compared revenues")],
         ["B: 560 × 80% = 448", "D: 640 × 85% = 544", "448 : 544 = 14 : 17"],
         "Ratio of absolute amounts", "Percentages are of different bases.", None, ""),
    ])
    # ---------- officer set 2 ----------
    st = ["P", "Q", "R", "S", "T"]
    app = dict(P=80, Q=120, R=95, S=150, T=72)
    qp = dict(P=F(25), Q=F(20), R=F(40), S=F(16), T=F(75, 2))
    fp = dict(P=40, Q=35, R=45, S=50, T=30)
    stim = ("The table gives, for five states, the number of candidates who applied for an examination (in thousands), "
            "the percentage of applicants who qualified, and the percentage of qualified candidates who are female.\n\n"
            + table(["State", "Applicants ('000)", "Qualified (%)", "Female among qualified (%)"],
                    [[s, app[s], n(qp[s]) + "%", f"{fp[s]}%"] for s in st]))
    Qd = {s: app[s] * qp[s] / 100 for s in st}
    Fe = {s: Qd[s] * fp[s] / 100 for s in st}
    Ma = {s: Qd[s] - Fe[s] for s in st}
    assert [Qd[s] for s in st] == [20, 24, 38, 24, 27]
    k1 = (Ma["Q"] + Ma["T"]) * 1000
    totF = sum(Fe.values())
    nq = {s: app[s] - Qd[s] for s in st}
    dset(B, M, "officer", "L4", "QAB-TAB-O2", stim, [
        ("How many qualified male candidates are there in states Q and T together?", k1,
         [((Qd["Q"] + Qd["T"]) * (1 - F(fp["Q"] + fp["T"], 200)) * 1000, "averaged the two female percentages"),
          ((Qd["Q"] + Qd["T"]) * 1000, "did not remove the female candidates"), ((Fe["Q"] + Fe["T"]) * 1000, "computed females instead of males")],
         ["Q: qualified 24,000; males 65% = 15,600", "T: qualified 27,000; males 70% = 18,900", "Total = 34,500"],
         "Males = qualified × (100 − female %)", "Different states have different bases; do not average percentages.", n, ""),
        ("The qualified females of state R form what percentage of the qualified females of all five states together?", Fe["R"] / totF * 100,
         [(Qd["R"] / sum(Qd.values()) * 100, "used total qualified candidates"), (Fe["R"] / (totF - Fe["R"]) * 100, "divided by the other four states only"),
          (F(app["R"], sum(app.values())) * 100, "used applicants")],
         ["Females: P 8, Q 8.4, R 17.1, S 12, T 8.1 (thousand) ⇒ total 53.6", "17.1/53.6 × 100 = 31.90%"],
         "Share = part / whole × 100", "Compute females state-wise before summing.", P2, ""),
        ("Had the qualifying percentage in S been 20% (female share unchanged), how many more qualified females would S have had?",
         app["S"] * F(4, 100) * F(fp["S"], 100) * 1000,
         [(app["S"] * F(4, 100) * 1000, "did not apply the female share"), (app["S"] * F(20, 100) * F(1, 2) * 1000, "gave the new number, not the increase"),
          (Fe["S"] * 1000 * F(4, 100), "took a 4% rise on the present number of females")],
         ["Extra qualified = 150,000 × 4% = 6,000", "Extra females = 50% of 6,000 = 3,000"],
         "Change = applicants × change in % × female share", "A 4-percentage-point rise is 4% of applicants, not 4% of qualifiers.", n, ""),
        ("What is the ratio of qualified males in P to qualified males in S?", ratio(Ma["P"], Ma["S"]),
         [(ratio(Fe["P"], Fe["S"]), "compared females"), (ratio(app["P"], app["S"]), "compared applicants"), (ratio(Qd["P"], Qd["S"]), "compared all qualified")],
         ["P males = 20,000 × 60% = 12,000", "S males = 24,000 × 50% = 12,000", "Ratio = 1 : 1"],
         "Ratio of derived values", "Different bases can give equal results.", None, ""),
        ("What is the average number of applicants per state who did NOT qualify?", F(sum(nq.values()), 5) * 1000,
         [(F(sum(app.values()), 5) * 1000, "averaged all applicants"), (F(sum(Qd.values()), 5) * 1000, "averaged the qualified"),
          (F(sum(nq.values()), 4) * 1000, "divided by 4")],
         ["Not qualified: 60, 96, 57, 126, 45 (thousand) ⇒ 384", "Average = 384/5 = 76.8 thousand = 76,800"],
         "Average = total / 5", "Subtract qualifiers state by state.", n, ""),
    ])


# =====================================================================
def barline(B):
    M = "qa-bar-and-line-graph-interpretation-35302e14"
    yrs = [2019, 2020, 2021, 2022, 2023]
    pr = dict(zip(yrs, [120, 150, 135, 180, 210]))
    stim = ("A bar graph shows the number of cars (in thousands) produced by a company in five years. The bar heights are:\n\n"
            + table(["Year"] + yrs, [["Cars ('000)"] + [pr[y] for y in yrs]]))
    g = {y: F(pr[y] - pr[y - 1], pr[y - 1]) for y in yrs[1:]}
    best = max(g, key=g.get)
    assert best == 2022
    th = " thousand"
    dset(B, M, "foundation", "L1", "QAB-BAR-F1", stim, [
        ("What is the percentage increase in production from 2021 to 2022?", g[2022] * 100,
         [(F(45, 180) * 100, "used 2022 as the base"), (45, "gave the absolute increase as a percentage"), (F(30, 150) * 100, "compared 2020 with 2022")],
         ["Increase = 180 − 135 = 45", "45/135 × 100 = 33.33%"], "% change = change / old × 100", "Base is the earlier year.", P2, ""),
        ("What is the average annual production over the five years?", F(sum(pr.values()), 5),
         [(F(sum(pr.values()), 4), "divided by 4"), (F(pr[2019] + pr[2023], 2), "averaged only the first and last years"), (150, "took the middle value (median)")],
         ["Total = 120 + 150 + 135 + 180 + 210 = 795", "Average = 795/5 = 159"], "Average = total / 5", "Include all five bars.", n, th),
        ("What is the ratio of production in 2020 to that in 2023?", ratio(150, 210),
         [(ratio(210, 150), "reversed the ratio"), (ratio(120, 210), "read 2019 instead of 2020"), (ratio(150, 180), "read 2022 instead of 2023")],
         ["150 : 210 = 5 : 7"], "Simplify by HCF", "Read the correct bars.", None, ""),
        ("In which year was the percentage increase over the previous year the highest?", str(best),
         [("2020", "judged by the 2020 jump without computing"), ("2023", "picked the year of highest production"), ("2021", "misread the fall as a rise")],
         ["2020: 25%, 2021: −10%, 2022: 33.33%, 2023: 16.67%", "Highest: 2022"], "Year-on-year % change", "Compute each change on its own base.", None, ""),
        ("Production in 2024 is planned to be 20% more than the average of 2022 and 2023. What is the planned production?",
         F(pr[2022] + pr[2023], 2) * F(6, 5),
         [(pr[2023] * F(6, 5), "applied 20% to 2023 alone"), (F(pr[2022] + pr[2023], 2), "forgot the 20% increase"), (pr[2022] * F(6, 5), "applied 20% to 2022 alone")],
         ["Average = (180 + 210)/2 = 195", "195 × 1.2 = 234"], "Increase of r% ⇒ × (1 + r/100)", "Average first, then increase.", n, th),
    ])
    # ---------- officer set 1: line graph ----------
    Y = [2018, 2019, 2020, 2021, 2022, 2023]
    exp = dict(zip(Y, [250, 300, 280, 350, 400, 480]))
    imp = dict(zip(Y, [200, 240, 320, 300, 350, 400]))
    stim = ("A line graph shows the exports and imports (₹ crore) of a company over six years. The plotted values are:\n\n"
            + table(["Year"] + Y, [["Exports"] + [exp[y] for y in Y], ["Imports"] + [imp[y] for y in Y]]))
    c15i = sum(1 for y in Y if exp[y] - imp[y] > F(15, 100) * imp[y])
    c15e = sum(1 for y in Y if exp[y] - imp[y] > F(15, 100) * exp[y])
    c20 = sum(1 for y in Y if exp[y] - imp[y] > F(20, 100) * imp[y])
    cpos = sum(1 for y in Y if exp[y] > imp[y])
    assert (c15i, c15e, c20, cpos) == (4, 3, 2, 5)
    sur = [exp[y] - imp[y] for y in Y]
    t19, t22 = exp[2019] + imp[2019], exp[2022] + imp[2022]
    e24, i24 = exp[2023] * F(exp[2023], exp[2022]), imp[2023] * F(11, 10)
    Cr = lambda v: "₹" + n(v) + " crore"
    dset(B, M, "officer", "L4", "QAB-LINE-O1", stim, [
        ("In how many years did exports exceed imports by more than 15% of that year's imports?", c15i,
         [(c15e, "measured the excess against exports"), (cpos, "counted every year with a surplus"), (c20, "used a 20% threshold")],
         ["Excess/imports: 25%, 25%, deficit, 16.67%, 14.29%, 20%", "More than 15%: 2018, 2019, 2021, 2023 ⇒ 4"],
         "Excess % = (E − I)/I × 100", "Check the base named in the question and exclude the deficit year.", n, ""),
        ("What is the percentage increase in total trade (exports + imports) from 2019 to 2022?", F(t22 - t19, t19) * 100,
         [(F(exp[2022] - exp[2019], exp[2019]) * 100, "used exports only"), (F(imp[2022] - imp[2019], imp[2019]) * 100, "used imports only"),
          (F(t22 - t19, t22) * 100, "used 2022 as base")],
         ["2019 total = 540; 2022 total = 750", "(750 − 540)/540 × 100 = 38.89%"], "% change of a sum", "Add first, then take the change.", P2, ""),
        ("What is the average trade surplus (exports − imports) per year over the six years?", F(sum(sur), 6),
         [(F(sum(abs(s) for s in sur), 6), "treated the 2020 deficit as a surplus"), (F(sum(sur), 5), "divided by the five surplus years"),
          (F(sum(s for s in sur if s > 0), 5), "dropped 2020 entirely")],
         ["Surpluses: 50, 60, −40, 50, 50, 80 ⇒ 250", "Average = 250/6 = 41.67"], "Average with signed values", "A deficit is a negative surplus.", Cr, ""),
        ("Imports in 2020 are what percentage of exports in 2023?", F(imp[2020], exp[2023]) * 100,
         [(F(exp[2023], imp[2020]) * 100, "inverted the ratio"), (F(imp[2023], exp[2023]) * 100, "read 2023 imports"), (F(imp[2020], exp[2022]) * 100, "read 2022 exports")],
         ["320/480 × 100 = 66.67%"], "A as % of B = A/B × 100", "Keep the 'of' quantity in the denominator.", P2, ""),
        ("If exports in 2024 grow at the same rate as from 2022 to 2023 and imports grow by 10%, what will the trade surplus be in 2024?", e24 - i24,
         [(e24 - imp[2023], "did not increase imports"), (exp[2023] * F(11, 10) - i24, "grew exports by 10% too"), (exp[2023] + 80 - i24, "added the 2022–23 rupee increase (₹80 crore) instead of the rate")],
         ["Export growth 2022→23 = 80/400 = 20%", "2024 exports = 480 × 1.2 = 576", "2024 imports = 400 × 1.1 = 440", "Surplus = 136"],
         "Compound one period at the given rate", "Same rate means same %, not same rupee increase.", Cr, ""),
    ])
    # ---------- officer set 2: multiple bar ----------
    cols = ["A", "B", "C", "D"]
    sci = dict(A=12, B=15, C=9, D=18)
    com = dict(A=8, B=9, C=12, D=10)
    art = dict(A=10, B=6, C=14, D=9)
    stim = ("A multiple-bar graph shows the number of students (in hundreds) in three streams in four colleges:\n\n"
            + table(["College", "Science", "Commerce", "Arts"], [[c, sci[c], com[c], art[c]] for c in cols]))
    tot = {c: sci[c] + com[c] + art[c] for c in cols}
    T = sum(tot.values())
    share = {c: F(sci[c], tot[c]) for c in cols}
    top = max(share, key=share.get)
    assert top == "B" and T == 132
    dset(B, M, "officer", "L4", "QAB-BAR-O2", stim, [
        ("Commerce students of all four colleges form what percentage of all students?", F(sum(com.values()), T) * 100,
         [(F(sum(com.values()), sum(sci.values())) * 100, "divided by Science students"), (F(sum(com.values()), T - sum(com.values())) * 100, "divided by non-Commerce students"),
          (F(sum(com.values()), 4), "averaged Commerce per college")],
         ["Commerce = 8 + 9 + 12 + 10 = 39", "Total = 132", "39/132 × 100 = 29.55%"], "Share = part / total × 100", "Total includes all three streams.", P2, ""),
        ("What is the ratio of Science students in A and C together to Arts students in B and D together?", ratio(sci["A"] + sci["C"], art["B"] + art["D"]),
         [(ratio(art["B"] + art["D"], sci["A"] + sci["C"]), "reversed the ratio"), (ratio(sci["A"] + sci["C"], art["A"] + art["C"]), "took Arts of A and C"),
          (ratio(sci["B"] + sci["D"], art["B"] + art["D"]), "took Science of B and D")],
         ["Science A + C = 21", "Arts B + D = 15", "21 : 15 = 7 : 5"], "Ratio of sums", "Match colleges to streams exactly.", None, ""),
        ("If 40% of Science students and 25% of Commerce students of college D are girls, how many girls are there in these two streams of D?",
         (sci["D"] * F(40, 100) + com["D"] * F(25, 100)) * 100,
         [((sci["D"] + com["D"]) * F(65, 200) * 100, "averaged the percentages"), ((sci["D"] * F(25, 100) + com["D"] * F(40, 100)) * 100, "swapped the percentages"),
          (sci["D"] * F(40, 100) + com["D"] * F(25, 100), "forgot that the data are in hundreds")],
         ["Science girls = 40% of 1,800 = 720", "Commerce girls = 25% of 1,000 = 250", "Total = 970"],
         "Part = % × base, per stream", "Units are hundreds.", n, ""),
        ("What is the average number of Arts students per college?", F(sum(art.values()), 4) * 100,
         [(F(sum(art.values()), 3) * 100, "divided by 3 streams"), (F(sum(art.values()), 4), "ignored the unit (hundreds)"), (F(T, 12) * 100, "averaged all streams")],
         ["Arts total = 10 + 6 + 14 + 9 = 39 hundred", "Average = 3,900/4 = 975"], "Average = total / number of colleges", "Divide by colleges, not streams.", n, ""),
        ("In which college do Science students form the largest share of the college's own total?", "College " + top,
         [("College D", "picked the largest absolute Science number"), ("College C", "picked the largest college"), ("College A", "compared Science with Arts only")],
         ["Shares: A 40%, B 50%, C 25.71%, D 48.65%", "Largest: B"], "Share = stream / college total", "Compare proportions, not absolutes.", None, ""),
    ])


# =====================================================================
def pie(B):
    M = "qa-pie-chart-interpretation-32cf3346"
    tot = 60000
    it = [("Rent", 25), ("Food", 30), ("Education", 15), ("Transport", 10), ("Savings", 12), ("Others", 8)]
    d = dict(it)
    assert sum(d.values()) == 100
    stim = ("A pie chart shows how a family's monthly income of ₹60,000 is distributed. The sector shares are:\n\n"
            + table(["Head", "Share of income"], [[h, f"{p}%"] for h, p in it]))
    Rs = lambda v: R(v) if not isinstance(v, str) else v
    dg = lambda v: n(v) + "°"
    dset(B, M, "foundation", "L1", "QAB-PIE-F1", stim, [
        ("How much does the family spend on food per month?", tot * 30 // 100,
         [(tot * 25 // 100, "read the Rent share"), (tot * 15 // 100, "read the Education share"), (tot * 3 // 100, "slipped a decimal place")],
         ["30% of 60,000 = 18,000"], "Amount = share × total", "Read the right sector.", Rs, ""),
        ("What is the central angle of the Education sector?", F(15 * 360, 100),
         [(15, "used the percentage as degrees"), (F(10 * 360, 100), "used the Transport share"), (F(12 * 360, 100), "used the Savings share")],
         ["Angle = 15% × 360° = 54°"], "Angle = share × 360°", "Convert % to degrees by × 3.6.", dg, ""),
        ("By how much does the monthly Rent exceed the Transport expenditure?", tot * 15 // 100,
         [(tot * 25 // 100, "gave the Rent itself"), (tot * 13 // 100, "subtracted Savings instead of Transport"), (tot * 17 // 100, "subtracted Others instead of Transport")],
         ["Difference in share = 25% − 10% = 15%", "15% of 60,000 = 9,000"], "Difference = (share₁ − share₂) × total", "Subtract shares first.", Rs, ""),
        ("What is the ratio of the combined Education and Transport expenditure to Savings?", ratio(25, 12),
         [(ratio(12, 25), "reversed the ratio"), (ratio(15, 12), "left out Transport"), (ratio(25, 8), "compared with Others")],
         ["Education + Transport = 25%", "Savings = 12%", "Ratio = 25 : 12"], "Shares of the same total compare directly", "The common total cancels.", None, ""),
        ("If the income rises by 20% and the Savings share stays at 12%, what will the monthly savings be?", tot * F(6, 5) * F(12, 100),
         [(tot * F(12, 100), "kept the old income"), (tot * F(32, 100), "added 20 to the percentage"), (tot * F(20, 100), "took 20% of the old income")],
         ["New income = 72,000", "12% of 72,000 = 8,640"], "Amount = share × new total", "The share applies to the new income.", Rs, ""),
    ])
    # ---------- officer set 1 ----------
    N = 3600
    dep = [("HR", F(10), 60), ("Sales", F(25), 30), ("Operations", F(20), 25), ("IT", F(45, 2), 40), ("Finance", F(25, 2), 48), ("Admin", F(10), 50)]
    assert sum(p for _, p, _ in dep) == 100
    stim = (f"A company has {inr(N)} employees. Pie chart 1 gives their distribution across departments; the table gives the percentage of women in each department.\n\n"
            + table(["Department", "Share of employees", "Women in department"], [[h, n(p) + "%", f"{w}%"] for h, p, w in dep]))
    emp = {h: N * p / 100 for h, p, _ in dep}
    wom = {h: emp[h] * w / 100 for h, _, w in dep}
    men = {h: emp[h] - wom[h] for h in emp}
    W = sum(wom.values())
    assert W == 1386
    avgw = F(sum(w for *_, w in dep), 6)
    ops_move = men["Operations"] * F(1, 5)
    wmax = max(wom, key=wom.get)
    assert wmax == "IT"
    dg = lambda v: n(v) + "°"
    dset(B, M, "officer", "L4", "QAB-PIE-O1", stim, [
        ("How many women work in the company?", W,
         [(N * avgw / 100, "averaged the six women percentages"), (W - wom["Admin"], "left out Admin"), (N - W, "counted men instead")],
         ["Women: HR 216, Sales 270, Ops 180, IT 324, Finance 216, Admin 180", "Total = 1,386"],
         "Sum of department-wise values", "Department sizes differ, so percentages cannot be averaged.", n, ""),
        ("What is the ratio of men in Sales to men in IT?", ratio(men["Sales"], men["IT"]),
         [(ratio(wom["Sales"], wom["IT"]), "compared women"), (ratio(emp["Sales"], emp["IT"]), "compared all employees"),
          (ratio(emp["Sales"] * F(60, 100), emp["IT"] * F(70, 100)), "swapped the women percentages of the two departments")],
         ["Sales men = 900 × 70% = 630", "IT men = 810 × 60% = 486", "630 : 486 = 35 : 27"], "Men = employees × (100 − women %)", "Use each department's own percentage.", None, ""),
        ("Women in Finance and HR together form what percentage of all women in the company?", (wom["Finance"] + wom["HR"]) / W * 100,
         [((wom["Finance"] + wom["HR"]) / N * 100, "divided by all employees"), (F(45, 2), "gave the departments' share of employees"),
          ((wom["Finance"] + wom["HR"]) / (emp["Finance"] + emp["HR"]) * 100, "divided by employees of the two departments")],
         ["Finance + HR women = 216 + 216 = 432", "432/1,386 × 100 = 31.17%"], "Share = part / whole × 100", "The whole here is all women.", P2, ""),
        ("If 20% of the men in Operations are transferred to Admin, what is the new ratio of men to women in Admin?",
         ratio(men["Admin"] + ops_move, wom["Admin"]),
         [(ratio(men["Admin"] + emp["Operations"] / 5, wom["Admin"]), "transferred 20% of all Operations staff"),
          (ratio(wom["Admin"], men["Admin"] + ops_move), "reversed the ratio"), (ratio(men["Admin"], wom["Admin"]), "ignored the transfer")],
         ["Operations men = 720 × 75% = 540; 20% = 108", "Admin men = 180 + 108 = 288; women = 180", "288 : 180 = 8 : 5"],
         "Update the count, then form the ratio", "Only men move; the base is Operations men.", None, ""),
        ("What is the central angle of the department that has the largest number of women?", F(45, 2) * F(360, 100),
         [(10 * F(360, 100), "chose HR, which has the highest women percentage"), (25 * F(360, 100), "chose the largest department"),
          (40 * F(360, 100), "used IT's women percentage as the share")],
         ["Largest number of women: IT (324)", "IT share = 22.5% ⇒ 22.5 × 3.6 = 81°"], "Angle = share × 360°", "Highest % is not highest number.", dg, ""),
    ])
    # ---------- officer set 2: two pies, different totals ----------
    heads = ["Raw material", "Salaries", "Marketing", "R&D", "Transport", "Others"]
    s22 = dict(zip(heads, [35, 20, 12, 8, 10, 15]))
    s23 = dict(zip(heads, [32, 22, 14, 10, 9, 13]))
    T22, T23 = 40, 50
    assert sum(s22.values()) == sum(s23.values()) == 100
    stim = ("Two pie charts show a company's expenditure distribution. Total expenditure was ₹40 crore in 2022 and ₹50 crore in 2023.\n\n"
            + table(["Head", "2022 share", "2023 share"], [[h, f"{s22[h]}%", f"{s23[h]}%"] for h in heads]))
    a22 = {h: F(T22 * s22[h], 100) for h in heads}
    a23 = {h: F(T23 * s23[h], 100) for h in heads}
    dec = sum(1 for h in heads if a23[h] < a22[h])
    shfall = sum(1 for h in heads if s23[h] < s22[h])
    assert dec == 0 and shfall == 3
    Cr = lambda v: "₹" + n(v) + " crore"
    dg = lambda v: n(v) + "°"
    dset(B, M, "officer", "L4", "QAB-PIE-O2", stim, [
        ("By what percentage did expenditure on Salaries increase from 2022 to 2023?", (a23["Salaries"] - a22["Salaries"]) / a22["Salaries"] * 100,
         [((a23["Salaries"] - a22["Salaries"]) / a23["Salaries"] * 100, "used 2023 as base"), (F(22 - 20, 20) * 100, "compared the shares only"),
          (F(T23 - T22, T22) * 100, "used the growth of total expenditure")],
         ["2022: 20% of 40 = ₹8 crore; 2023: 22% of 50 = ₹11 crore", "(11 − 8)/8 × 100 = 37.5%"],
         "Convert shares to amounts before comparing", "Totals differ between the two pies.", P2, ""),
        ("For how many heads was the rupee expenditure in 2023 LOWER than in 2022?", dec,
         [(shfall, "counted heads whose share fell"), (1, "counted only Raw material"), (2, "counted Transport and Others")],
         ["2023 amounts: 16, 11, 7, 5, 4.5, 6.5 vs 2022: 14, 8, 4.8, 3.2, 4, 6", "Every head rose in rupees ⇒ 0"],
         "Compare amounts, not shares", "A smaller share of a larger total can still be more money.", n, ""),
        ("By how much did combined Marketing and R&D expenditure rise from 2022 to 2023?",
         a23["Marketing"] + a23["R&D"] - a22["Marketing"] - a22["R&D"],
         [(F(4 * T23, 100), "applied the change in share to the 2023 total"), (a23["Marketing"] + a23["R&D"], "gave the 2023 amount"),
          (F(24 * T22, 100) - a22["Marketing"] - a22["R&D"], "applied 2023 shares to the 2022 total")],
         ["2023: 24% of 50 = 12", "2022: 20% of 40 = 8", "Rise = ₹4 crore"], "Change = amount₂ − amount₁", "Each year has its own total.", Cr, ""),
        ("What is the central angle of Transport in the 2023 pie chart?", F(9 * 360, 100),
         [(F(10 * 360, 100), "used the 2022 share"), (9, "used the percentage as degrees"), (a23["Transport"] / T22 * 360, "divided the 2023 amount by the 2022 total")],
         ["9% × 360° = 32.4°"], "Angle = share × 360°", "Use the 2023 share.", dg, ""),
        ("In 2024 total expenditure rises 10% over 2023 and the R&D share rises to 12%. What is the R&D expenditure in 2024?", F(T23 * 11, 10) * F(12, 100),
         [(T23 * F(12, 100), "did not raise the total"), (F(T23 * 11, 10) * F(10, 100), "kept the R&D share at 10%"),
          (a23["R&D"] * F(112, 100), "raised the 2023 R&D amount by 12%")],
         ["2024 total = 55", "12% of 55 = ₹6.6 crore"], "Amount = new share × new total", "Both the total and the share change.", Cr, ""),
    ])


# =====================================================================
def caselet(B):
    M = "qa-caselet-data-interpretation-372ea92b"
    stim = ("A school has 1,200 students, of whom 55% are boys. 40% of the boys and 60% of the girls take part in sports; "
            "the rest do not take part.")
    boys, girls = 660, 540
    sb, sg = boys * 40 // 100, girls * 60 // 100
    assert boys + girls == 1200 and (sb, sg) == (264, 324)
    dset(B, M, "foundation", "L1", "QAB-CAS-F1", stim, [
        ("How many girls take part in sports?", sg,
         [(sb, "computed boys"), (girls * 40 // 100, "used 40% for girls"), (600 * 60 // 100, "assumed half the students are girls")],
         ["Girls = 45% of 1,200 = 540", "60% of 540 = 324"], "Part = % × base", "Girls are 45%, not 50%.", n, ""),
        ("How many students do not take part in sports?", 1200 - sb - sg,
         [(sb + sg, "gave the participants"), (600, "averaged 40% and 60%"), (boys - sb, "counted non-participating boys only")],
         ["Participants = 264 + 324 = 588", "Non-participants = 1,200 − 588 = 612"], "Complement = total − part", "Percentages apply to different bases.", n, ""),
        ("What percentage of the sports participants are boys?", F(sb, sb + sg) * 100,
         [(55, "gave the share of boys in the school"), (40, "gave the participation rate of boys"), (F(sb, 1200) * 100, "divided by all students")],
         ["Boy participants = 264, total participants = 588", "264/588 × 100 = 44.90%"], "Share = part / whole × 100", "The whole is participants.", P2, ""),
        ("What is the ratio of boys who do not take part to girls who do not take part?", ratio(boys - sb, girls - sg),
         [(ratio(boys, girls), "compared all boys and girls"), (ratio(girls - sg, boys - sb), "reversed the ratio"), (ratio(sb, sg), "compared participants")],
         ["Boys not taking part = 396", "Girls not taking part = 216", "396 : 216 = 11 : 6"], "Ratio of complements", "Use the non-participating groups.", None, ""),
        ("If 30 more girls join sports, what percentage of girls will take part?", F(sg + 30, girls) * 100,
         [(F(sg + 30, girls + 30) * 100, "added 30 to the number of girls as well"), (F(sg + 30, 1200) * 100, "divided by all students"),
          (60 + F(30 * 100, 1200), "divided 30 by all students and added to 60%")],
         ["New participants = 354", "354/540 × 100 = 65.56%"], "Share = part / base × 100", "The number of girls is unchanged.", P2, ""),
    ])
    # ---------- officer set 1 ----------
    stim = ("A company sold 12,000 units of three products X, Y and Z in two cities, Delhi and Pune. Delhi accounted for 60% of the units. "
            "In Delhi, X, Y and Z were sold in the ratio 5 : 4 : 3. In Pune, Y made up 40% of the city's units, and 600 more units of X "
            "than of Z were sold. Selling prices per unit are ₹250 for X, ₹300 for Y and ₹400 for Z in both cities.")
    D = dict(X=3000, Y=2400, Z=1800)
    Pn = dict(X=1740, Y=1920, Z=1140)
    assert sum(D.values()) == 7200 and sum(Pn.values()) == 4800 and Pn["X"] - Pn["Z"] == 600
    pr = dict(X=250, Y=300, Z=400)
    rev = lambda c: sum(c[k] * pr[k] for k in c)
    L = lambda v: lakh(v)
    dset(B, M, "officer", "L4", "QAB-CAS-O1", stim, [
        ("How many units of X were sold in the two cities together?", D["X"] + Pn["X"],
         [(D["X"] + Pn["Z"], "reversed 'X exceeds Z by 600' in Pune"), (D["X"] + Pn["Y"], "took Pune's Y figure"), (D["X"] + 1440, "split Pune's X + Z equally")],
         ["Delhi: 7,200 in 5:4:3 ⇒ X 3,000", "Pune: 4,800; Y = 1,920; X + Z = 2,880; X − Z = 600 ⇒ X = 1,740", "Total X = 4,740"],
         "Sum and difference ⇒ X = (S + D)/2", "Read which product is larger.", n, ""),
        ("Units of Z sold in Pune are what percentage of units of Z sold in Delhi?", F(Pn["Z"], D["Z"]) * 100,
         [(F(D["Z"], Pn["Z"]) * 100, "inverted the ratio"), (F(Pn["X"], D["Z"]) * 100, "used Pune's X"), (F(1440, D["Z"]) * 100, "split Pune's X + Z equally")],
         ["Pune Z = (2,880 − 600)/2 = 1,140", "1,140/1,800 × 100 = 63.33%"], "A as % of B = A/B × 100", "Solve Pune's X and Z first.", P2, ""),
        ("What is the ratio of the total units of Y to the total units of Z?", ratio(D["Y"] + Pn["Y"], D["Z"] + Pn["Z"]),
         [(ratio(D["Y"] + Pn["Y"], D["Z"] + Pn["X"]), "swapped X and Z in Pune"), (ratio(4, 3), "used Delhi's ratio only"),
          (ratio(D["Z"] + Pn["Z"], D["Y"] + Pn["Y"]), "reversed the ratio")],
         ["Y = 2,400 + 1,920 = 4,320", "Z = 1,800 + 1,140 = 2,940", "4,320 : 2,940 = 72 : 49"], "Ratio of totals", "Combine both cities.", None, ""),
        ("What was the total revenue from sales in Pune?", rev(Pn),
         [(rev(dict(X=Pn["Z"], Y=Pn["Y"], Z=Pn["X"])), "swapped X and Z in Pune"), (rev(dict(X=1440, Y=1920, Z=1440)), "split X + Z equally"),
          (rev(D), "computed Delhi's revenue")],
         ["X: 1,740 × 250 = 4,35,000", "Y: 1,920 × 300 = 5,76,000", "Z: 1,140 × 400 = 4,56,000", "Total = ₹14.67 lakh"],
         "Revenue = Σ units × price", "Keep X and Z straight; Z is dearer.", L, ""),
        ("Units of Y sold in Delhi are what percentage more than units of Y sold in Pune?", F(D["Y"] - Pn["Y"], Pn["Y"]) * 100,
         [(F(D["Y"] - Pn["Y"], D["Y"]) * 100, "used Delhi as base"), (F(D["Y"] - Pn["Y"], 4800) * 100, "divided by Pune's total units"),
          ((F(40) - F(100, 3)) / 40 * 100, "compared Y's shares of each city's sales")],
         ["Delhi Y = 2,400; Pune Y = 1,920", "480/1,920 × 100 = 25%"], "% more = difference / smaller × 100", "'More than Pune' ⇒ Pune is the base.", P2, ""),
    ])
    # ---------- officer set 2 ----------
    stim = ("A bank branch gave loans to 800 customers in a year under three schemes: home, vehicle and personal. Home-loan customers were 35% of the total, "
            "and vehicle-loan customers were 80 more than personal-loan customers. The average loan was ₹24 lakh for home, ₹6 lakh for vehicle and "
            "₹2.5 lakh for personal loans. Women made up 15% of home-loan, 25% of vehicle-loan and 40% of personal-loan customers.")
    H, V, Pl = 280, 300, 220
    assert H + V + Pl == 800 and V - Pl == 80
    av = dict(H=F(24), V=F(6), P=F(5, 2))
    wr = dict(H=F(15, 100), V=F(25, 100), P=F(40, 100))
    disb = lambda h, v, p: h * av["H"] + v * av["V"] + p * av["P"]
    tdis = disb(H, V, Pl)
    assert tdis == 9070
    wom = lambda h, v, p: h * wr["H"] + v * wr["V"] + p * wr["P"]
    Cr = lambda v: "₹" + n(F(v, 100)) + " crore"
    newV = (V * F(9, 10)) * 7
    dset(B, M, "officer", "L4", "QAB-CAS-O2", stim, [
        ("What was the total amount disbursed?", tdis,
         [(disb(H, Pl, V), "swapped vehicle and personal customers"), (disb(H, 260, 260), "split the remaining customers equally"),
          (800 * (av["H"] + av["V"] + av["P"]) / 3, "multiplied 800 by the simple average of the three averages")],
         ["Home 280, vehicle 300, personal 220", "280 × 24 + 300 × 6 + 220 × 2.5 = 6,720 + 1,800 + 550 = 9,070 lakh", "= ₹90.70 crore"],
         "Total = Σ count × average", "Averages must be weighted by counts.", Cr, ""),
        ("How many women took loans?", wom(H, V, Pl),
         [(wom(H, Pl, V), "swapped vehicle and personal customers"), (wom(H, 260, 260), "split the remaining customers equally"),
          (800 - wom(H, V, Pl), "counted men")],
         ["Home: 15% of 280 = 42", "Vehicle: 25% of 300 = 75", "Personal: 40% of 220 = 88", "Total = 205"],
         "Σ count × rate", "Solve vehicle and personal counts first.", n, ""),
        ("Personal loans form what percentage of the total amount disbursed?", Pl * av["P"] / tdis * 100,
         [(F(Pl, 800) * 100, "gave the share of customers"), (Pl * av["P"] / (tdis - Pl * av["P"]) * 100, "left personal loans out of the base"),
          (av["P"] / (av["H"] + av["V"] + av["P"]) * 100, "compared average loan sizes")],
         ["Personal = 220 × 2.5 = 550 lakh", "550/9,070 × 100 = 6.06%"], "Share = part / total × 100", "Share of money ≠ share of customers.", P2, ""),
        ("If the average vehicle loan rises to ₹7 lakh and the number of vehicle-loan customers falls by 10%, by what percentage does the vehicle-loan disbursement change?",
         (newV - V * av["V"]) / (V * av["V"]) * 100,
         [(F(100, 6) - 10, "subtracted the two percentage changes"), ((newV - V * av["V"]) / newV * 100, "used the new amount as base"),
          (F(100, 6), "ignored the fall in customers")],
         ["New = 270 × 7 = 1,890 lakh; old = 1,800 lakh", "Change = 90/1,800 × 100 = +5%"], "(1 + a)(1 + b) − 1", "Percentage changes multiply, not add.", P2, ""),
        ("What is the ratio of women home-loan customers to women personal-loan customers?", ratio(H * wr["H"], Pl * wr["P"]),
         [(ratio(15, 40), "compared the percentages"), (ratio(H, Pl), "compared all customers"), (ratio(Pl * wr["P"], H * wr["H"]), "reversed the ratio")],
         ["Women home = 42; women personal = 88", "42 : 88 = 21 : 44"], "Ratio of derived counts", "Apply each rate to its own base.", None, ""),
    ])


# =====================================================================
def setbased(B):
    M = "qa-set-based-data-interpretation-8e13c5a7"
    Tn, A, Bb, AB = 500, 280, 240, 90
    oa, ob = A - AB, Bb - AB
    ne = Tn - (A + Bb - AB)
    assert (oa, ob, ne) == (190, 150, 70)
    stim = "In a survey of 500 people, 280 read newspaper A, 240 read newspaper B and 90 read both."
    dset(B, M, "foundation", "L1", "QAB-SET-F1", stim, [
        ("How many people read only newspaper A?", oa,
         [(A, "did not remove the readers of both"), (AB, "gave the readers of both"), (ob, "gave the readers of only B")],
         ["Only A = 280 − 90 = 190"], "Only A = n(A) − n(A ∩ B)", "Readers of both are inside A.", n, ""),
        ("How many people read neither newspaper?", ne,
         [(Tn - oa - ob, "left out the readers of both"), (AB, "gave the readers of both"), (Tn - A, "subtracted only the readers of A")],
         ["n(A ∪ B) = 280 + 240 − 90 = 430", "Neither = 500 − 430 = 70"], "n(A ∪ B) = n(A) + n(B) − n(A ∩ B)", "Subtract the overlap once.", n, ""),
        ("How many people read exactly one newspaper?", oa + ob,
         [(oa + ob + AB, "included the readers of both"), (A + Bb, "added the totals of A and B"), (A, "gave the readers of A")],
         ["Only A 190 + only B 150 = 340"], "Exactly one = n(A) + n(B) − 2n(A ∩ B)", "Remove the overlap from both sets.", n, ""),
        ("What percentage of the readers of B also read A?", F(AB, Bb) * 100,
         [(F(AB, A) * 100, "used readers of A as base"), (F(AB, Tn) * 100, "used all surveyed people"), (F(ob, Bb) * 100, "gave the share reading only B")],
         ["90/240 × 100 = 37.5%"], "Conditional share = n(A ∩ B)/n(B) × 100", "The base is readers of B.", P2, ""),
        ("What is the ratio of people who read only A to those who read only B?", ratio(oa, ob),
         [(ratio(A, Bb), "used total readers"), (ratio(ob, oa), "reversed the ratio"), (ratio(oa, AB), "compared only A with both")],
         ["190 : 150 = 19 : 15"], "Ratio of regions", "Use the 'only' regions.", None, ""),
    ])
    # ---------- officer set 1: three sets ----------
    a, b, c, d, e, f, g = 220, 180, 150, 60, 80, 50, 40   # only P, only Q, only R, PQ-only, QR-only, PR-only, all
    N = 1000
    nP, nQ, nR = a + d + f + g, b + d + e + g, c + e + f + g
    PQ, QR, PR = d + g, e + g, f + g
    ex2 = d + e + f
    un = a + b + c + d + e + f + g
    h = N - un
    assert (nP, nQ, nR, PQ, QR, ex2, h) == (370, 360, 320, 100, 120, 190, 220)
    stim = (f"A survey of {inr(N)} people asked which of three apps P, Q and R they use. Results: {nP} use P, {nQ} use Q and {nR} use R. "
            f"{PQ} use both P and Q, {QR} use both Q and R, {ex2} use exactly two of the apps and {g} use all three.")
    # derived: f = ex2 - (PQ-g) - (QR-g)
    assert ex2 - (PQ - g) - (QR - g) == f
    S = nP + nQ + nR
    dset(B, M, "officer", "L4", "QAB-SET-O1", stim, [
        ("How many people use only P?", a,
         [(nP - PQ - PR, "subtracted P∩Q and P∩R without adding back the all-three group"), (nP - d - g, "forgot the P-and-R-only region"),
          (nP - PQ - g, "subtracted all-three again instead of the P-and-R-only region")],
         ["P and Q only = 100 − 40 = 60; Q and R only = 120 − 40 = 80", "P and R only = 190 − 60 − 80 = 50",
          "Only P = 370 − 60 − 50 − 40 = 220"], "Region method for three sets", "Separate 'both' totals into 'exactly two' and 'all three'.", n, ""),
        ("How many people use none of the three apps?", h,
         [(N - (S - ex2 - g), "subtracted the all-three group only once"), (N - (S - ex2), "ignored the all-three correction"),
          (N - (S - ex2 - 2 * g) + g, "added the all-three group back")],
         ["n(at least one) = Σn − (exactly two) − 2 × (all three)", "= 1,050 − 190 − 80 = 780", "None = 1,000 − 780 = 220"],
         "n(∪) = Σn − E₂ − 2E₃", "Each all-three user is counted three times in Σn.", n, ""),
        ("How many people use exactly one app?", a + b + c,
         [(un, "gave at least one"), (a + b + c + g, "included the all-three users"), (a + b + c - g, "subtracted all-three once more")],
         ["Only Q = 360 − 60 − 80 − 40 = 180", "Only R = 320 − 80 − 50 − 40 = 150", "Exactly one = 220 + 180 + 150 = 550"],
         "Exactly one = at least one − E₂ − E₃", "Work region by region.", n, ""),
        ("What percentage of R users also use at least one other app?", F(e + f + g, nR) * 100,
         [(F(e + f, nR) * 100, "left out the all-three users"), (F(e + f + g, N) * 100, "divided by all surveyed"), (F(e + f + g, un) * 100, "divided by app users")],
         ["R users with another app = 80 + 50 + 40 = 170", "170/320 × 100 = 53.13%"], "Conditional share", "The base is R users.", P2, ""),
        ("If 30 of the people who use only Q start using R as well, how many people will use exactly two apps?", d + (e + 30) + f,
         [(ex2, "did not update the regions"), (ex2 + 60, "added 30 to two regions"), (ex2 - 30, "subtracted 30 from exactly two")],
         ["Only Q → Q and R only: 80 + 30 = 110", "Exactly two = 60 + 110 + 50 = 220"], "Move people between regions", "They move from 'only Q' into 'Q and R only'.", n, ""),
    ])
    # ---------- officer set 2 ----------
    N = 720
    g = 60
    x2 = (N - g) // 3
    x1 = 2 * x2
    oc, of_, oh = x1 * 5 // 11, x1 * 4 // 11, x1 * 2 // 11
    cf, fh = 90, 70
    ch = x2 - cf - fh
    assert (x1, x2, oc, of_, oh, ch) == (440, 220, 200, 160, 80, 60) and oc + of_ + oh == x1
    nC = oc + cf + ch + g
    nF = of_ + cf + fh + g
    nH = oh + fh + ch + g
    stim = ("Each of 720 students plays at least one of cricket, football and hockey. The number who play exactly one game is twice the number who play exactly two games. "
            "60 students play all three. Those who play only cricket, only football and only hockey are in the ratio 5 : 4 : 2. "
            "90 students play cricket and football but not hockey, and 70 play football and hockey but not cricket.")
    dset(B, M, "officer", "L4", "QAB-SET-O2", stim, [
        ("How many students play cricket?", nC,
         [(nC - g, "left out the all-three group"), (oc + cf, "left out the cricket-hockey-only and all-three groups"), (nC + g, "counted the all-three group twice")],
         ["Exactly one + exactly two + 60 = 720 and exactly one = 2 × exactly two ⇒ exactly two = 220, exactly one = 440",
          "Only C = 440 × 5/11 = 200; C and H only = 220 − 90 − 70 = 60", "Cricket = 200 + 90 + 60 + 60 = 410"],
         "Region method", "Include every region inside the cricket circle.", n, ""),
        ("How many students play exactly two games?", x2,
         [(x2 + g, "included the all-three group"), (x1, "gave exactly one"), (N // 3, "ignored the all-three group when splitting 720")],
         ["3 × (exactly two) + 60 = 720 ⇒ exactly two = 220"], "E₁ + E₂ + E₃ = total", "Remove the all-three group first.", n, ""),
        ("How many students play football but not cricket?", of_ + fh,
         [(of_ + fh + g, "included the all-three group"), (of_, "gave only football"), (nF - oc, "subtracted only-cricket from football")],
         ["Only F = 440 × 4/11 = 160", "F and H only = 70", "Football but not cricket = 230"], "F − (F ∩ C)", "All-three players play cricket.", n, ""),
        ("What is the ratio of hockey players to football players?", ratio(nH, nF),
         [(ratio(oh, of_), "compared only-hockey with only-football"), (ratio(nF, nH), "reversed the ratio"), (ratio(nH - g, nF - g), "excluded the all-three group")],
         ["Hockey = 80 + 70 + 60 + 60 = 270", "Football = 160 + 90 + 70 + 60 = 380", "270 : 380 = 27 : 38"], "Ratio of set totals", "Build totals from all regions.", None, ""),
        ("What percentage of the students play at most one game?", F(x1, N) * 100,
         [(F(x2, N) * 100, "used exactly two"), (F(N - g, N) * 100, "computed at most two"), (F(x1 + g, N) * 100, "added the all-three group")],
         ["Everyone plays at least one ⇒ at most one = exactly one = 440", "440/720 × 100 = 61.11%"], "Share", "'At most one' here equals 'exactly one'.", P2, ""),
    ])


# =====================================================================
def mixed(B):
    M = "qa-mixed-and-combined-di-4edc5bb5"
    N = 1500
    st = [("Science", 30, (3, 2)), ("Commerce", 24, (5, 3)), ("Arts", 20, (2, 3)), ("Engineering", 16, (7, 5)), ("Law", 10, (1, 1))]
    stim = ("A college has 1,500 students. A pie chart gives the share of each stream, and the table beside it gives the ratio of boys to girls in each stream.\n\n"
            + table(["Stream", "Share of students", "Boys : Girls"], [[s, f"{p}%", f"{r[0]} : {r[1]}"] for s, p, r in st]))
    tot = {s: N * p // 100 for s, p, _ in st}
    boy = {s: tot[s] * r[0] // (r[0] + r[1]) for s, _, r in st}
    girl = {s: tot[s] - boy[s] for s in tot}
    assert list(boy.values()) == [270, 225, 120, 140, 75]
    dset(B, M, "foundation", "L2", "QAB-MIX-F1", stim, [
        ("How many girls are there in Arts?", girl["Arts"],
         [(boy["Arts"], "computed boys"), (tot["Arts"] // 2, "assumed an equal split"), (girl["Arts"] - boy["Arts"], "gave the difference")],
         ["Arts = 20% of 1,500 = 300", "Girls = 300 × 3/5 = 180"], "Part = total × share of ratio", "Boys : girls = 2 : 3 ⇒ girls are 3/5.", n, ""),
        ("How many boys are there in the college?", sum(boy.values()),
         [(sum(girl.values()), "computed girls"), (N // 2, "assumed half are boys"), (sum(boy.values()) - boy["Arts"], "left out Arts")],
         ["Boys: 270 + 225 + 120 + 140 + 75 = 830"], "Σ stream-wise boys", "Each stream has its own ratio.", n, ""),
        ("What is the ratio of girls in Science to girls in Commerce?", ratio(girl["Science"], girl["Commerce"]),
         [(ratio(boy["Science"], boy["Commerce"]), "compared boys"), (ratio(tot["Science"], tot["Commerce"]), "compared all students"),
          (ratio(girl["Commerce"], girl["Science"]), "reversed the ratio")],
         ["Science girls = 450 × 2/5 = 180", "Commerce girls = 360 × 3/8 = 135", "180 : 135 = 4 : 3"], "Ratio of derived counts", "Use each stream's ratio.", None, ""),
        ("Boys in Engineering form what percentage of Engineering students?", F(boy["Engineering"], tot["Engineering"]) * 100,
         [(F(7, 5) * 100, "gave boys as a percentage of girls"), (16, "gave the stream's share of the college"), (F(girl["Engineering"], tot["Engineering"]) * 100, "computed girls' share")],
         ["7/(7 + 5) = 7/12 = 58.33%"], "Share = part / (sum of ratio terms)", "Divide by the total, not by girls.", P2, ""),
        ("By how many do boys exceed girls in Commerce and Arts taken together?", boy["Commerce"] + boy["Arts"] - girl["Commerce"] - girl["Arts"],
         [(boy["Commerce"] - girl["Commerce"], "used Commerce only"), (abs(boy["Commerce"] - girl["Commerce"]) + abs(boy["Arts"] - girl["Arts"]), "ignored that Arts has more girls"),
          (girl["Arts"] - boy["Arts"], "used Arts only")],
         ["Boys: 225 + 120 = 345", "Girls: 135 + 180 = 315", "Difference = 30"], "Combine before subtracting", "Arts has more girls than boys.", n, ""),
    ])
    # ---------- officer set 1: tables ----------
    co = ["A", "B", "C", "D"]
    mf = dict(A=250, B=320, C=180, D=400)
    sp = dict(A=80, B=75, C=90, D=70)
    price = dict(A=1200, B=1000, C=1500, D=900)
    stim = ("Table 1 gives the units manufactured (in thousands) by four companies in a year and the percentage of manufactured units sold. "
            "Table 2 gives the selling price per unit.\n\n"
            + table(["Company", "Manufactured ('000)", "Sold (%)"], [[c, mf[c], f"{sp[c]}%"] for c in co]) + "\n\n"
            + table(["Company", "Price per unit (₹)"], [[c, inr(price[c])] for c in co]))
    sold = {c: F(mf[c] * sp[c], 100) * 1000 for c in co}
    rv = {c: sold[c] * price[c] for c in co}
    unsold = sum(mf[c] * 1000 - sold[c] for c in co)
    assert unsold == 268000
    avgsp = F(sum(sp.values()), 4)
    topc = max(rv, key=rv.get)
    assert topc == "D"
    Crr = lambda v: v if isinstance(v, str) else crore(v)
    totrev, totsold = sum(rv.values()), sum(sold.values())
    dset(B, M, "officer", "L4", "QAB-MIX-O1", stim, [
        ("How many manufactured units remained unsold across the four companies?", unsold,
         [(sum(mf.values()) * 1000 * (1 - avgsp / 100), "applied the average sale percentage to the total"), (unsold - (mf["D"] * 1000 - sold["D"]), "left out D"),
          (sum(mf.values()) * 1000 - unsold, "gave the units sold")],
         ["Unsold: A 50, B 80, C 18, D 120 thousand", "Total = 2,68,000"], "Unsold = manufactured × (100 − sold %)", "Rates differ across companies.", n, ""),
        ("Which company earned the highest revenue from sales?", "Company " + topc,
         [("Company C", "picked the highest price"), ("Company B", "picked the highest units sold after D without computing revenue"), ("Company A", "picked the highest sale percentage after C")],
         ["Revenue: A ₹24 crore, B ₹24 crore, C ₹24.3 crore, D ₹25.2 crore", "Highest: D"], "Revenue = units sold × price", "Low price × high volume can win.", None, ""),
        ("Revenue of C is what percentage of the combined revenue of A and B?", rv["C"] / (rv["A"] + rv["B"]) * 100,
         [(F(mf["C"], mf["A"] + mf["B"]) * 100, "compared units manufactured"), (sold["C"] / (sold["A"] + sold["B"]) * 100, "compared units sold"),
          (rv["C"] / totrev * 100, "divided by all four companies")],
         ["C = 1,62,000 × 1,500 = ₹24.3 crore", "A + B = ₹48 crore", "24.3/48 × 100 = 50.63%"], "A as % of B", "Compare revenues, not volumes.", P2, ""),
        ("Had D sold 80% of its units at the same price, how much more revenue would it have earned?", mf["D"] * 1000 * F(10, 100) * price["D"],
         [(rv["D"] * F(10, 100), "took 10% of the current revenue"), (mf["D"] * 100 * F(10, 100) * price["D"], "treated the data as hundreds, not thousands"),
          (mf["D"] * 1000 * F(10, 100) * price["A"], "used A's price")],
         ["Extra units = 10% of 4,00,000 = 40,000", "40,000 × 900 = ₹3.6 crore"], "Extra revenue = extra units × price", "10 percentage points of manufactured units.", Crr, ""),
        ("What is the average price realised per unit sold, taking all four companies together?", totrev / totsold,
         [(F(sum(price.values()), 4), "took the simple average of prices"),
          (F(sum(mf[c] * price[c] for c in co), sum(mf.values())), "weighted prices by units manufactured"), (1100, "took the median price")],
         ["Total revenue = ₹97.5 crore", "Units sold = 8,82,000", "Average = 97,50,00,000/8,82,000 = ₹1,105.44"],
         "Weighted average = total revenue / total units sold", "Weights are units sold.", lambda v: "₹" + n(v), ""),
    ])
    # ---------- officer set 2: pie + table ----------
    days = [("Monday", 10, F(20)), ("Tuesday", 12, F(25)), ("Wednesday", 8, F(25, 2)), ("Thursday", 15, F(20)),
            ("Friday", 20, F(15)), ("Saturday", 20, F(30)), ("Sunday", 15, F(25))]
    N = 2400
    assert sum(p for _, p, _ in days) == 100
    stim = ("2,400 tourists visited a hill station in a week. A pie chart gives the share of tourists on each day and the table gives the percentage of foreign tourists that day.\n\n"
            + table(["Day", "Share of week's tourists", "Foreign tourists (%)"], [[dname, f"{p}%", n(fp) + "%"] for dname, p, fp in days]))
    tt = {dn: N * p // 100 for dn, p, _ in days}
    fo = {dn: tt[dn] * fp / 100 for dn, _, fp in days}
    do = {dn: tt[dn] - fo[dn] for dn in tt}
    Fo = sum(fo.values())
    assert Fo == 522
    wk = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    dset(B, M, "officer", "L4", "QAB-MIX-O2", stim, [
        ("How many foreign tourists visited during the week?", Fo,
         [(round(N * sum(fp for *_, fp in days) / 7 / 100), "averaged the daily foreign percentages"), (Fo - fo["Saturday"], "left out Saturday"),
          (N - Fo, "counted domestic tourists")],
         ["Foreign: 48, 72, 24, 72, 72, 144, 90", "Total = 522"], "Σ day-wise values", "Daily totals differ, so percentages cannot be averaged.", n, ""),
        ("What is the ratio of domestic tourists on Friday to domestic tourists on Sunday?", ratio(do["Friday"], do["Sunday"]),
         [(ratio(fo["Friday"], fo["Sunday"]), "compared foreign tourists"), (ratio(tt["Friday"], tt["Sunday"]), "compared all tourists"),
          (ratio(do["Sunday"], do["Friday"]), "reversed the ratio")],
         ["Friday domestic = 480 × 85% = 408", "Sunday domestic = 360 × 75% = 270", "408 : 270 = 68 : 45"], "Ratio of derived counts", "Domestic = total − foreign.", None, ""),
        ("Foreign tourists on Saturday and Sunday together form what percentage of the week's foreign tourists?", (fo["Saturday"] + fo["Sunday"]) / Fo * 100,
         [(35, "gave the weekend's share of all tourists"), ((fo["Saturday"] + fo["Sunday"]) / N * 100, "divided by all tourists"),
          ((fo["Saturday"] + fo["Sunday"]) / (tt["Saturday"] + tt["Sunday"]) * 100, "divided by weekend tourists")],
         ["Weekend foreign = 144 + 90 = 234", "234/522 × 100 = 44.83%"], "Share", "The whole is the week's foreign tourists.", P2, ""),
        ("What is the average number of foreign tourists per weekday (Monday to Friday)?", sum(fo[x] for x in wk) / 5,
         [(Fo / 7, "averaged over all seven days"), (sum(fo[x] for x in wk) / 7, "divided the weekday total by 7"),
          ((fo["Saturday"] + fo["Sunday"]) / 2, "averaged the weekend days")],
         ["Weekday foreign = 48 + 72 + 24 + 72 + 72 = 288", "288/5 = 57.6"], "Average = total / 5", "Weekdays are five.", n, ""),
        ("If next week's total rises by 25% with the same daily shares and foreign percentages, by how much will foreign tourists on Saturday increase?", fo["Saturday"] / 4,
         [(fo["Saturday"] * F(5, 4), "gave next week's number"), (tt["Saturday"] / 4, "gave the increase in all Saturday tourists"),
          (fo["Saturday"], "gave this week's number")],
         ["Saturday foreign = 30% of 480 = 144", "Increase = 25% of 144 = 36"], "Increase = r% × current", "Everything scales by 25%.", n, ""),
    ])


# =====================================================================
def sufficiency(B):
    M = "qa-data-sufficiency-0fd64dd8"
    DSH = ("Each question has two statements, I and II. Decide whether the data in the statements are sufficient to answer it.\n\n")
    items = []   # (tier, level, question, s1text, s2text, domain, base, s1, s2, target, steps, trap)
    R100 = range(1, 101)
    items.append(("foundation", "L1", "What is the value of the positive integer x?", "x² = 49", "x + 3 = 10",
                  [(x,) for x in R100], lambda t: True, lambda t: t[0] ** 2 == 49, lambda t: t[0] + 3 == 10, lambda t: t[0],
                  ["I: x² = 49 and x > 0 ⇒ x = 7 (sufficient)", "II: x = 7 (sufficient)", "Either statement alone answers it."],
                  "Positivity rules out −7 in statement I."))
    items.append(("foundation", "L2", "What is A's present age?", "A is 5 years older than B.", "B is 20 years old.",
                  [(a, b) for a in range(1, 81) for b in range(1, 81)], lambda t: True, lambda t: t[0] == t[1] + 5, lambda t: t[1] == 20, lambda t: t[0],
                  ["I relates A and B but gives no number", "II gives B only", "Together: A = 25"], "Neither statement alone fixes A."))
    items.append(("foundation", "L2", "Is the integer n (1 ≤ n ≤ 100) even?", "n is divisible by 6.", "n is divisible by 3.",
                  [(x,) for x in R100], lambda t: True, lambda t: t[0] % 6 == 0, lambda t: t[0] % 3 == 0, lambda t: t[0] % 2 == 0,
                  ["I: every multiple of 6 is even ⇒ Yes (sufficient)", "II: 3 is odd, 6 is even ⇒ not sufficient"],
                  "A definite 'Yes' is sufficient, just as a number would be."))
    items.append(("foundation", "L2", "What is the price of one pen (in whole rupees)?", "3 pens and 2 pencils cost ₹40.", "One pencil costs ₹5.",
                  [(p, c) for p in range(1, 41) for c in range(1, 41)], lambda t: True, lambda t: 3 * t[0] + 2 * t[1] == 40, lambda t: t[1] == 5, lambda t: t[0],
                  ["I: 3p + 2c = 40 has several solutions (p = 10, c = 5; p = 12, c = 2; …)", "II gives only the pencil", "Together: 3p = 30 ⇒ p = ₹10"],
                  "One equation in two unknowns is not enough."))
    items.append(("foundation", "L2", "What is the two-digit number?", "The sum of its digits is 9.", "Its digits differ by 3.",
                  [(x,) for x in range(10, 100)], lambda t: True, lambda t: sum(map(int, str(t[0]))) == 9,
                  lambda t: abs(int(str(t[0])[0]) - int(str(t[0])[1])) == 3, lambda t: t[0],
                  ["I: 18, 27, 36, 45, …", "II: 14, 25, 36, 41, 63, …", "Together: 36 or 63 ⇒ still two answers"],
                  "Digits differing by 3 does not say which digit is larger."))
    # officer
    items.append(("officer", "L3", "What is B's present age?", "The ratio of the present ages of A and B is 4 : 5.", "Six years ago the ratio of their ages was 3 : 4.",
                  [(a, b) for a in range(1, 101) for b in range(7, 101)], lambda t: True, lambda t: 5 * t[0] == 4 * t[1],
                  lambda t: t[0] > 6 and 4 * (t[0] - 6) == 3 * (t[1] - 6), lambda t: t[1],
                  ["I: A = 4k, B = 5k (k unknown)", "II: one equation in two unknowns", "Together: (4k − 6)/(5k − 6) = 3/4 ⇒ k = 6 ⇒ B = 30"],
                  "Two ratios at two points in time are needed."))
    items.append(("officer", "L3", "What is the two-digit number N?", "N is a multiple of 7 and its digit sum is 10.", "The number formed by reversing N's digits exceeds N by 54.",
                  [(x,) for x in range(10, 100)], lambda t: True, lambda t: t[0] % 7 == 0 and sum(map(int, str(t[0]))) == 10,
                  lambda t: t[0] % 10 != 0 and int(str(t[0])[::-1]) - t[0] == 54, lambda t: t[0],
                  ["I: 28 or 91", "II: units − tens = 6 ⇒ 17, 28, 39", "Together: 28"], "Check that each statement alone leaves more than one number."))
    items.append(("officer", "L3", "Is x > y? (x, y are integers.)", "x + y = 10", "x − y = 4",
                  [(x, y) for x in range(-20, 21) for y in range(-20, 21)], lambda t: True, lambda t: t[0] + t[1] == 10,
                  lambda t: t[0] - t[1] == 4, lambda t: t[0] > t[1],
                  ["I: (7, 3) gives Yes, (3, 7) gives No ⇒ not sufficient", "II: x − y = 4 > 0 ⇒ Yes (sufficient)"],
                  "Solving for x and y is unnecessary; II already decides the comparison."))
    items.append(("officer", "L3", "What is the remainder when the positive integer N is divided by 12?", "N leaves remainder 1 when divided by 4.", "N leaves remainder 2 when divided by 3.",
                  [(x,) for x in range(1, 501)], lambda t: True, lambda t: t[0] % 4 == 1, lambda t: t[0] % 3 == 2, lambda t: t[0] % 12,
                  ["I: N mod 12 ∈ {1, 5, 9}", "II: N mod 12 ∈ {2, 5, 8, 11}", "Together: N mod 12 = 5"], "Neither remainder alone fixes N mod 12; combined (CRT) they do."))
    items.append(("officer", "L3", "What is the remainder when the positive integer N is divided by 6?", "N leaves remainder 7 when divided by 12.", "N leaves remainder 1 when divided by 3.",
                  [(x,) for x in range(1, 501)], lambda t: True, lambda t: t[0] % 12 == 7, lambda t: t[0] % 3 == 1, lambda t: t[0] % 6,
                  ["I: N = 12k + 7 ⇒ N mod 6 = 1 (sufficient)", "II: N mod 6 is 1 or 4 ⇒ not sufficient"], "Because 6 divides 12, statement I alone fixes the remainder."))
    items.append(("officer", "L3", "A and B together finish a job in 12 days. In how many days can A alone finish it?", "B alone can finish it in 20 days.", "A is 50% more efficient than B.",
                  [(a, b) for a in range(13, 301) for b in range(13, 301)], lambda t: F(1, t[0]) + F(1, t[1]) == F(1, 12), lambda t: t[1] == 20,
                  lambda t: F(1, t[0]) == F(3, 2) * F(1, t[1]), lambda t: t[0],
                  ["I: 1/A = 1/12 − 1/20 = 1/30 ⇒ 30 days", "II: rates 3 : 2 ⇒ A's rate = (3/5)(1/12) = 1/20 ⇒ 20 days", "Each alone suffices."],
                  "The combined-time fact is given in the question; each statement completes it."))
    items.append(("officer", "L3", "What is the simple interest earned in 3 years?", "The principal is ₹8,000 and the rate is 10% per annum.", "The amount after 3 years is ₹10,400.",
                  [(p, r) for p in range(500, 20001, 500) for r in range(1, 21)], lambda t: True, lambda t: t[0] == 8000 and t[1] == 10,
                  lambda t: t[0] + F(t[0] * t[1] * 3, 100) == 10400, lambda t: F(t[0] * t[1] * 3, 100),
                  ["I: SI = 8,000 × 10% × 3 = ₹2,400 (sufficient)", "II: P(1 + 3r/100) = 10,400 has many (P, r) pairs, e.g. 8,000 & 10%, 6,500 & 20%"],
                  "The amount alone does not separate principal from interest."))
    items.append(("officer", "L3", "What is the integer x?", "x² − 5x + 6 = 0", "x is a prime number.",
                  [(x,) for x in range(-50, 51)], lambda t: True, lambda t: t[0] ** 2 - 5 * t[0] + 6 == 0,
                  lambda t: t[0] > 1 and all(t[0] % k for k in range(2, t[0])), lambda t: t[0],
                  ["I: x = 2 or 3", "II: any prime", "Together: 2 and 3 are both prime ⇒ still two values"], "Test whether the extra condition actually removes a root."))
    items.append(("officer", "L3", "What is the average of five consecutive odd integers?", "The largest of them is 19.", "The sum of the smallest and the largest is 30.",
                  [(a,) for a in range(-51, 102, 2)], lambda t: True, lambda t: t[0] + 8 == 19, lambda t: 2 * t[0] + 8 == 30, lambda t: t[0] + 4,
                  ["I: numbers 11 to 19 ⇒ average 15", "II: average = (smallest + largest)/2 = 15", "Each alone suffices."],
                  "For equally spaced numbers, average = (first + last)/2."))
    items.append(("officer", "L3", "What is the ratio of the speeds of A and B (in whole km/h)?", "A covers 180 km in 3 hours.", "B takes 1 hour more than A to cover 180 km.",
                  [(va, vb) for va in range(1, 181) for vb in range(1, 181)], lambda t: True, lambda t: t[0] == 60,
                  lambda t: F(180, t[1]) - F(180, t[0]) == 1, lambda t: F(t[0], t[1]),
                  ["I: A = 60 km/h, B unknown", "II: (60, 45) and (90, 60) both fit ⇒ ratio 4 : 3 or 3 : 2", "Together: B = 180/4 = 45 ⇒ 4 : 3"],
                  "A time difference alone does not fix a ratio."))
    for tier, lv, qn, t1, t2, dom, base, s1, s2, tgt, steps, trap in items:
        key = ds_eval(dom, base, s1, s2, tgt)
        stem = DSH + qn + f"\n\nI. {t1}\nII. {t2}"
        ds_q(B, M, lv, tier, stem, key, steps + [f"Answer: {DS[key]}."], trap)


def add_all(B):
    tabular(B)
    barline(B)
    pie(B)
    caselet(B)
    setbased(B)
    mixed(B)
    sufficiency(B)
