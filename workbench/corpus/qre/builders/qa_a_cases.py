"""QRE-QA-A case sets (L4, officer): shop sales-mix DI, trains caselet, ferry caselet,
partnership + profit caselet, dairy mixture caselet, marks frequency-table (median/mode)."""
from fractions import Fraction as Fr
from collections import Counter
from qa_a_common import N, D, P, Rs, ratio, hm_time, hmin, make_q


def add_all(B):
    q0 = make_q(B)

    def case(g, stim):
        def q(m, stem, key, wrongs, steps, formula, trap):
            return q0(m, "L4", "o", stim + "\n\n" + stem, key, wrongs, steps, formula, trap, kind="case", g=g)
        return q

    # ===================== Set 1: shop sales-mix =====================
    items = {  # units, CP, MP, discount %
        "Kettle": (120, 800, 1200, 20),
        "Toaster": (80, 1500, 2000, 10),
        "Mixer": (60, 2400, 3200, 15),
        "Iron": (150, 500, 750, 12),
    }
    rows = "\n".join(f"| {k} | {u} | {Rs(c)} | {Rs(m)} | {d}% |" for k, (u, c, m, d) in items.items())
    stim = ("An appliance shop's sales for one month are shown below. Every unit of an item was sold at the same discount on its marked price.\n\n"
            "| Item | Units sold | Cost price per unit | Marked price per unit | Discount |\n|---|---|---|---|---|\n" + rows)
    q = case("QAA-SHOP", stim)
    sp = {k: Fr(m * (100 - d), 100) for k, (u, c, m, d) in items.items()}
    rev = {k: sp[k] * items[k][0] for k in items}
    cost = {k: items[k][1] * items[k][0] for k in items}
    mrev = {k: items[k][2] * items[k][0] for k in items}

    x = (rev["Toaster"] - rev["Kettle"]) / rev["Kettle"] * 100
    assert x == 25
    q("pcmp", "Revenue from toasters is what percent more than revenue from kettles?",
      P(x), [(P((rev["Toaster"] - rev["Kettle"]) / rev["Toaster"] * 100), "toaster revenue used as base"),
             (P(rev["Toaster"] / rev["Kettle"] * 100), "ratio reported as 'more than'"),
             (P(D((mrev["Toaster"] - mrev["Kettle"]) / mrev["Kettle"] * 100)), "marked-price values compared")],
      ["Kettle SP = 960 ⇒ revenue 1,15,200", "Toaster SP = 1,800 ⇒ revenue 1,44,000", "(1,44,000 − 1,15,200)/1,15,200 = 25%"],
      "% more = difference ÷ base × 100", "Base is the kettle revenue.")

    TC, TR, TM = sum(cost.values()), sum(rev.values()), sum(mrev.values())
    op = (TR - TC) / TC * 100
    mean_p = sum((sp[k] - items[k][1]) / items[k][1] * 100 for k in items) / 4
    q("comb", "The shop's overall profit percentage on the month's sales of all four items is closest to:",
      P(D(op)), [(P(D(mean_p)), "simple average of item-wise profit %"), (P(D((TR - TC) / TR * 100)), "profit taken on selling price"),
                 (P(D((TM - TC) / TC * 100)), "overall mark-up reported")],
      ["Total CP = 4,35,000; total SP = 5,21,400", "Profit = 86,400", "86,400/4,35,000 = 19.86%"],
      "Overall % = total profit ÷ total cost", "Item percentages must be weighted by cost.")

    k = "Mixer"
    pm = (sp[k] - items[k][1]) / sp[k] * 100
    q("cpsp", "The profit on each mixer, expressed as a percentage of its selling price, is:",
      P(D(pm)), [(P(D((sp[k] - items[k][1]) / items[k][1] * 100)), "profit taken on cost"), (P(15), "discount rate reported"),
                 (P(D(Fr(items[k][2] - items[k][1], items[k][1]) * 100)), "mark-up reported")],
      ["SP = 3,200 × 0.85 = 2,720", "Profit = 320", "320/2,720 = 11.76%"], "Margin on SP = profit ÷ SP", "Margin and mark-up use different bases.")

    need = items[k][1] * Fr(120, 100)
    dmax = (items[k][2] - need) / items[k][2] * 100
    assert dmax == 10
    q("disc", "Next month the shop wants a 20% profit on mixers without changing the marked price. The maximum discount it can allow is:",
      P(dmax), [(P(D((items[k][2] - need) / items[k][1] * 100)), "discount amount taken on cost"),
                (P(D((items[k][2] - need) / need * 100)), "discount amount taken on the new SP"), (P(20), "profit rate reported")],
      ["Required SP = 2,400 × 1.2 = 2,880", "Discount = 320 on MP 3,200", "= 10%"], "Discount % on marked price", "Discount is always on MP.")

    # ===================== Set 2: trains =====================
    XY, vP, vQ, vR = 360, 60, 75, 100
    LP, LQ, LR = 240, 210, 300
    stim = (f"Stations X and Y are {XY} km apart on a double-track line. Train P ({LP} m long) leaves X at 6:00 am for Y at {vP} km/h. "
            f"Train Q ({LQ} m long) leaves Y at 7:30 am for X at {vQ} km/h. Train R ({LR} m long) leaves X at 8:00 am for Y at {vR} km/h on the track used by P, "
            "and overtakes P on a loop line without either train slowing. All speeds are constant and there are no halts.")
    q = case("QAA-TRAINS", stim)
    gap = XY - vP * Fr(3, 2)
    tm = Fr(3, 2) + gap / (vP + vQ)
    assert tm == Fr(7, 2)
    q("rel", "At what time do the engines of P and Q pass each other?",
      hm_time(6 + tm), [(hm_time(6 + Fr(XY, vP + vQ)), "both assumed to start at 6:00 am"), (hm_time(Fr(15, 2) + Fr(XY, vP + vQ)), "P's head start ignored"),
                        (hm_time(6 + gap / (vP + vQ)), "meeting time counted from 6:00 am")],
      ["By 7:30 am P has run 90 km; gap 270 km", "Closing speed 135 km/h ⇒ 2 h", "Meet at 9:30 am"], "Head start, then closing speed", "Count the 2 h from 7:30 am.")

    rel = Fr((vP + vQ) * 5, 18)
    t = (LP + LQ) / rel
    q("trn", "How long do P and Q take to cross each other completely?",
      f"{N(t)} s", [(f"{N((LP + LQ) / Fr((vQ - vP) * 5, 18))} s", "same-direction relative speed used"), (f"{N(LP / rel)} s", "only P's length used"),
                    (f"{D(Fr(LP + LQ, vP + vQ))} s", "km/h not converted to m/s")],
      ["Relative speed = 135 km/h = 37.5 m/s", "Distance = 240 + 210 = 450 m", "Time = 12 s"], "Opposite: add speeds; add lengths", "Convert with 5/18.")

    gapR = vP * 2
    tc = Fr(gapR, vR - vP)
    assert 8 + tc < 6 + Fr(XY, vP)
    q("rel", "At what time does R's engine draw level with P's engine?",
      hm_time(8 + tc), [(hm_time(8 + Fr(gapR, vR + vP)), "speeds added"), (hm_time(8 + Fr(gapR, vP)), "head start divided by P's speed"),
                        (hm_time(6 + tc), "catch-up time counted from 6:00 am")],
      ["At 8:00 am P is 120 km ahead", "Gain = 40 km/h ⇒ 3 h", "11:00 am (P has not yet reached Y)"], "Head start ÷ relative speed", "Count from R's departure.")

    rel2 = Fr((vR - vP) * 5, 18)
    t2 = (LP + LR) / rel2
    q("trn", "How long does R take to overtake P completely (from R's engine reaching P's rear to R's rear clearing P's engine)?",
      f"{D(t2)} s", [(f"{D((LP + LR) / Fr((vR + vP) * 5, 18))} s", "opposite-direction relative speed"), (f"{D(LR / rel2)} s", "only R's length used"),
                     (f"{D(LP / rel2)} s", "only P's length used")],
      ["Relative speed = 40 km/h = 100/9 m/s", "Distance = 300 + 240 = 540 m", "Time = 48.6 s"], "Same direction: subtract speeds; add lengths", "Both lengths must clear.")

    # ===================== Set 3: ferry =====================
    b, s, AB = 18, 6, 48
    halt = Fr(1, 3)
    stim = (f"A ferry has a still-water speed of {b} km/h. It runs from jetty A downstream to jetty B, {AB} km away, and returns to A. "
            f"On the return it halts for 20 minutes at jetty C, midway between B and A. On a normal day the river flows at {s} km/h.")
    q = case("QAA-FERRY", stim)
    down, up = Fr(AB, b + s), Fr(AB, b - s)
    tot = down + up + halt
    q("boat", "On a normal day, the total time for the round trip, including the halt, is:",
      hmin(tot), [(hmin(down + up), "halt ignored"), (hmin(Fr(2 * AB, b) + halt), "still-water speed used both ways"),
                  (hmin(2 * down + halt), "return timed at downstream speed")],
      ["Down: 48/24 = 2 h; up: 48/12 = 4 h", "Total = 6 h + 20 min"], "Time = d/(b + s) + d/(b − s) + halt", "The upstream leg takes twice as long.")

    avg = Fr(2 * AB) / tot
    q("avgspd", "On a normal day, the ferry's average speed for the whole round trip, including the halt, is closest to:",
      f"{D(avg)} km/h", [(f"{D(Fr(2 * AB) / (down + up))} km/h", "halt excluded"), (f"{D(Fr(b + s + b - s, 2))} km/h", "mean of downstream and upstream speeds"),
                         (f"{D(Fr(2 * AB) / (down + up + 1))} km/h", "halt taken as 1 hour")],
      ["Distance 96 km; time 6 1/3 h", "Average = 96 ÷ 19/3 = 15.16 km/h"], "Total distance ÷ total time", "Include the halt.")

    s2 = next(x for x in range(1, 18) if Fr(AB, b + x) + Fr(AB, b - x) == Fr(48, 5))
    q("boat", "On a flood day the ferry makes the round trip, without the halt, in 9 hours 36 minutes. The stream speed that day is:",
      f"{s2} km/h", [(f"{b - 10} km/h", "average speed subtracted from still-water speed"), (f"{s} km/h", "normal-day stream speed"),
                     ("10 km/h", "round-trip average speed reported")],
      ["48/(18 + s) + 48/(18 − s) = 9.6", "1,728/(324 − s²) = 9.6 ⇒ s² = 144", "s = 12 km/h"], "Round-trip equation", "Average speed ≠ boat − stream.")

    left = Fr(17, 3) - down - halt
    ground = AB / left
    ground_nohalt = AB / (Fr(17, 3) - down)
    q("avgspd", "On a normal day the operator wants the round trip, including the halt, completed in 5 hours 40 minutes by speeding up only on the return leg. The still-water speed needed on the return is:",
      f"{D(ground + s)} km/h", [(f"{D(ground)} km/h", "required ground speed reported"), (f"{D(ground_nohalt + s)} km/h", "halt ignored"),
                                (f"{D(ground - s)} km/h", "stream subtracted instead of added")],
      ["Downstream 2 h + halt 1/3 h", "Return must take 5 2/3 − 2 1/3 = 3 1/3 h ⇒ ground speed 14.4 km/h", "Still-water speed = 14.4 + 6 = 20.4 km/h"],
      "Remaining distance ÷ remaining time, then add stream", "Upstream ground speed = b − s.")

    # ===================== Set 4: partnership + profit =====================
    cm = {"Asha": 120000 * 12, "Bilal": 90000 * 4 + 60000 * 8, "Chitra": 160000 * 9}
    profit = 310000
    fee = profit // 10
    pool = profit - fee
    tot_cm = sum(cm.values())
    share = {k: Fr(pool * v, tot_cm) for k, v in cm.items()}
    assert all(v.denominator == 1 for v in share.values())
    stim = ("Asha, Bilal and Chitra run a catering business for one year. Asha invests ₹1,20,000 at the start. Bilal invests ₹90,000 at the start and "
            "withdraws ₹30,000 at the end of the 4th month. Chitra joins at the end of the 3rd month with ₹1,60,000. Asha, the working partner, first takes 10% of the "
            "annual profit as a management fee; the rest is shared in the ratio of capital-months. The annual profit is ₹3,10,000.")
    q = case("QAA-PARTNER", stim)
    q("sratio", "The ratio in which the profit after the fee is shared (Asha : Bilal : Chitra) is:",
      ratio(*cm.values()), [(ratio(120000, 90000, 160000), "opening capitals only"), (ratio(120000 * 12, 90000 * 12, 160000 * 9), "Bilal's withdrawal ignored"),
                            (ratio(120000 * 12, 90000 * 4 + 60000 * 8, 160000 * 12), "Chitra counted for 12 months")],
      ["Asha 1,20,000 × 12 = 14,40,000", "Bilal 90,000 × 4 + 60,000 × 8 = 8,40,000", "Chitra 1,60,000 × 9 = 14,40,000 ⇒ 12 : 7 : 12"],
      "Compound ratio: capital × months", "Split Bilal's year at the withdrawal.")

    q("part", "Bilal's share of the profit is:",
      Rs(share["Bilal"]), [(Rs(Fr(profit * cm["Bilal"], tot_cm)), "fee not deducted"), (Rs(Fr(pool, 3)), "equal split"),
                           (Rs(Fr(pool * 3, 11)), "withdrawal ignored (4 : 3 : 4)")],
      ["Pool = 3,10,000 − 31,000 = 2,79,000", "Bilal = 2,79,000 × 7/31 = ₹63,000"], "Share = pool × own ratio ÷ total", "Deduct the fee first.")

    asha = share["Asha"] + fee
    q("part", "Asha's total receipt from the business for the year is:",
      Rs(asha), [(Rs(share["Asha"]), "fee omitted"), (Rs(Fr(profit * cm["Asha"], tot_cm)), "whole profit shared, no fee"),
                 (Rs(Fr(profit * cm["Asha"], tot_cm) + fee), "fee added without deducting it from the pool")],
      ["Asha's share = 2,79,000 × 12/31 = 1,08,000", "Plus fee 31,000 = ₹1,39,000"], "Working partner: fee + share", "The fee comes out of the profit before sharing.")

    ex = (asha - share["Chitra"]) / share["Chitra"] * 100
    q("part", "By what percentage does Asha's total receipt exceed Chitra's?",
      P(D(ex)), [(P(D((asha - share["Chitra"]) / asha * 100)), "Asha's receipt used as base"), (P(0), "fee overlooked (equal capital-months)"),
                 (P(10), "fee rate reported")],
      ["Asha 1,39,000; Chitra 1,08,000", "Excess 31,000/1,08,000 = 28.70%"], "% more = difference ÷ base", "Base is Chitra's receipt.")

    parts = [Fr(1, 3), Fr(1, 4), Fr(1, 6)]
    eldest = share["Chitra"] * parts[0] / sum(parts)
    assert eldest == 48000
    q("prop", "Chitra divides her share among her three children in the ratio 1/3 : 1/4 : 1/6. The largest portion is:",
      Rs(eldest), [(Rs(share["Chitra"] / 3), "1/3 of the total taken directly"), (Rs(share["Chitra"] * parts[2] / sum(parts)), "smallest portion"),
                   (Rs(share["Chitra"] / 9), "one ratio part")],
      ["1/3 : 1/4 : 1/6 = 4 : 3 : 2 (× 12)", "1,08,000 ÷ 9 = 12,000 per part", "Largest = 4 × 12,000 = ₹48,000"], "Clear fractions with the LCM", "Fractional ratios must be converted to whole numbers.")

    # ===================== Set 5: dairy mixtures =====================
    tanks = {"X": (60, 5, 1), "Y": (80, 3, 1)}
    stim = ("A dairy has three tanks. Tank X holds 60 litres of milk and water in the ratio 5 : 1; tank Y holds 80 litres in the ratio 3 : 1; "
            "tank Z holds 40 litres of pure milk. Milk costs the dairy ₹48 per litre; water costs nothing.")
    q = case("QAA-DAIRY", stim)
    milk = {k: Fr(v * a, a + b_) for k, (v, a, b_) in tanks.items()}
    water = {k: tanks[k][0] - milk[k] for k in tanks}
    mX, mY = milk["X"], milk["Y"]
    q("mix", "If tanks X and Y are emptied into one container, the ratio of milk to water in it is:",
      ratio(mX + mY, water["X"] + water["Y"]), [(ratio(5 + 3, 1 + 1), "ratio terms added"), (ratio(Fr(5, 6) + Fr(3, 4), Fr(1, 6) + Fr(1, 4)), "unweighted mean of concentrations"),
                                                (ratio(water["X"] + water["Y"], mX + mY), "ratio inverted")],
      ["X: 50 milk, 10 water; Y: 60 milk, 20 water", "Total 110 : 30 = 11 : 3"], "Add actual quantities", "Ratio terms cannot be added across different volumes.")

    z = next(Fr(z, 2) for z in range(0, 81) if (mY + Fr(z, 2)) / (80 + Fr(z, 2)) == Fr(4, 5))
    assert z == 20
    q("mix", "How many litres from tank Z must be added to the whole of tank Y so that milk makes up 80% of the mixture?",
      f"{N(z)} litres", [(f"{N(Fr(4, 5) * 80 - mY)} litres", "extra milk for 80 L only, volume increase ignored"),
                         (f"{N((Fr(4, 5) * 80 - mY) / Fr(1, 4))} litres", "shortfall divided by water fraction"), ("5 litres", "alligation ratio 1 part read as litres")],
      ["Alligation: Y 75%, Z 100%, target 80% ⇒ Y : Z = 20 : 5 = 4 : 1", "Z = 80/4 = 20 L", "Check: 80/100 = 80%"], "Alligation", "Adding milk also raises the volume.")

    tot_v = 60 + 80 + 40
    tot_m = mX + mY + 40
    avgc = tot_m * 48 / tot_v
    per = [Fr(mX * 48, 60), Fr(mY * 48, 80), Fr(48)]
    q("avg", "If all three tanks are mixed, the average cost per litre of the mixture is:",
      Rs(avgc), [(Rs(sum(per) / 3), "simple average of the tanks' costs per litre"), (Rs(48), "price of pure milk"),
                 (Rs(per[1]), "tank Y's cost per litre")],
      ["Milk = 50 + 60 + 40 = 150 L in 180 L", "Cost = 150 × 48 = 7,200", "Average = 7,200/180 = ₹40 per litre"], "Weighted average = total cost ÷ total volume", "Tanks differ in volume.")

    rem = mY * (1 - Fr(16, 80)) ** 2
    q("mix", "From tank Y, 16 litres are drawn off and replaced with water; this is done twice. The milk left in tank Y is:",
      f"{N(rem)} litres", [(f"{N(mY - 2 * 16 * Fr(3, 4))} litres", "same milk removed each time (linear)"), (f"{N(mY * Fr(4, 5))} litres", "only one operation"),
                           (f"{N(80 * Fr(16, 25))} litres", "factor applied to total liquid")],
      ["Each draw keeps 64/80 = 4/5 of the milk", "60 × (4/5)² = 38.4 L"], "Milk left = M(1 − r/V)ⁿ", "The second draw removes less milk.")

    # ===================== Set 6: marks frequency table (median / mode) =====================
    freq = {3: 2, 4: 3, 5: 7, 6: 4, 7: 4, 8: 3, 9: 2}
    assert sum(freq.values()) == 25
    stim = ("Marks (out of 10) scored by 25 candidates in a mock test:\n\n| Marks | " + " | ".join(str(k) for k in freq) + " |\n|" + "---|" * (len(freq) + 1) +
            "\n| Candidates | " + " | ".join(str(v) for v in freq.values()) + " |")
    q = case("QAA-MARKS", stim)

    def med(fr):
        xs = sorted(x for k, v in fr.items() for x in [k] * v)
        n = len(xs)
        return Fr(xs[n // 2]) if n % 2 else Fr(xs[n // 2 - 1] + xs[n // 2], 2)

    def modes(fr):
        m = max(fr.values())
        return sorted(k for k, v in fr.items() if v == m)

    mean = Fr(sum(k * v for k, v in freq.items()), 25)
    xs = sorted(x for k, v in freq.items() for x in [k] * v)
    assert med(freq) == 6 and modes(freq) == [5]
    q("med", "The median mark is:",
      N(med(freq)), [(N(modes(freq)[0]), "mode reported"), (D(mean), "mean reported"), (N(Fr(xs[11] + xs[12], 2)), "even count assumed (12th and 13th averaged)")],
      ["Cumulative: 2, 5, 12, 16, …", "Median = 13th value = 6"], "Median = ((n + 1)/2)th value", "Use cumulative frequencies.")

    f2 = dict(freq); f2[7] += 3
    m2, mo2 = med(f2), modes(f2)
    assert m2 == 6 and mo2 == [5, 7]
    q("med", "Three more candidates, each scoring 7, are added. The new median and mode are:",
      "Median 6; modes 5 and 7", [("Median 6.5; mode 7", "median taken between 6 and 7; old mode dropped"), ("Median 6; mode 7 only", "tie with 5 missed"),
                                   ("Median 7; modes 5 and 7", "median shifted to the added value")],
      ["n = 28 ⇒ median = mean of 14th and 15th values", "Cumulative: 2, 5, 12, 16 ⇒ both are 6 ⇒ median 6", "5 and 7 now both occur 7 times ⇒ bimodal"],
      "Median for even n; mode = most frequent value(s)", "A tie gives two modes.")

    kmin = next(k for k in range(0, 40) if med({**freq, 8: freq[8] + k}) >= 7)
    assert kmin == 8 and med({**freq, 8: freq[8] + 7}) == Fr(13, 2)
    q("med", "What is the least number of additional candidates, each scoring 8, needed to make the median 7 or more?",
      str(kmin), [("7", "median of 6.5 accepted"), ("9", "even total assumed necessary"), ("4", "difference of cumulative counts (16 − 12)")],
      ["With k added, n = 25 + k; 16 candidates score 6 or less", "Need the middle position(s) beyond 16", "k = 7 ⇒ n = 32, median = (6 + 7)/2 = 6.5; k = 8 ⇒ n = 33, median = 17th = 7"],
      "Median position (n + 1)/2", "An even total averages two middle values.")
