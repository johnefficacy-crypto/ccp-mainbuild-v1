"""FIN-B part 1: primary markets & securities law (ICDR, IPO, retail limits, green shoe,
underwriting, NCD/NCRPS, REIT/InvIT, SSE, municipal bonds, SCRA, SEBI Act, RA/IA) + case sets C1, C2."""
import datetime as dt
from finb_common import (M, statements, stmt_opts, ar_opts, ar_stem, table, f2, inr, R, pct, lakh, crore)


def add_all(B):
    # =============================== ICDR essentials ===============================
    mi = M("icdr-regulations-essentials")
    st = ["Net tangible assets of at least ₹3 crore in each of the preceding three full years, of which not more than 50% is held in monetary assets",
          "An average operating profit of at least ₹15 crore during the preceding three years, with operating profit in each of those years",
          "A net worth of at least ₹5 crore in each of the preceding three full years"]
    c, w = stmt_opts([True, True, False],
                     ["NTA test is ₹3 crore each year with the 50% monetary-asset cap",
                      "operating-profit test is ₹15 crore average with profit in each year",
                      "the net-worth test is ₹1 crore in each of three years, not ₹5 crore"])
    B.add(mi, "L1", "Under Regulation 6(1) of the SEBI (ICDR) Regulations, 2018, which of the following are among the eligibility conditions for a main-board IPO?\n\n" + statements(st) + "\n\nSelect the correct answer.",
          c, w,
          ["Reg 6(1)(a): NTA ≥ ₹3 crore in each of the preceding 3 full years (restated, consolidated), not more than 50% in monetary assets (cap relaxed if the IPO is entirely an offer for sale).",
           "Reg 6(1)(b): average operating profit ≥ ₹15 crore over the preceding 3 years, with operating profit in each year.",
           "Reg 6(1)(c): net worth ≥ ₹1 crore in each of the preceding 3 years — so statement 3 overstates it."],
          "Reg 6(1): NTA ₹3 cr / Op. profit avg ₹15 cr / Net worth ₹1 cr", "The ₹1 crore net-worth floor is often inflated to ₹5 crore or confused with the ₹3 crore NTA figure.",
          kind="statement", verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Reg 6(1)")

    nta = [3.40, 3.85, 2.90]; op = [14.2, 16.8, 15.6]; nw = [9.5, 12.1, 14.0]
    avg_op = sum(op) / 3; avg_nta = sum(nta) / 3
    assert avg_nta >= 3 and min(nta) < 3 and avg_op >= 15
    tb = table(["Year (restated, consolidated)", "Net tangible assets (₹ cr)", "Operating profit (₹ cr)", "Net worth (₹ cr)"],
               [["FY-3", nta[0], op[0], nw[0]], ["FY-2", nta[1], op[1], nw[1]], ["FY-1", nta[2], op[2], nw[2]]])
    B.add(mi, "L3", f"Suvarna Polymers Ltd plans a main-board IPO. Monetary assets were below 20% of NTA in every year.\n\n{tb}\n\nWhich statement correctly describes its route under the SEBI (ICDR) Regulations, 2018?",
          "Fails 6(1); may issue only under 6(2) with at least 75% of net offer to QIBs",
          [("Qualifies under 6(1), since its average NTA exceeds the ₹3 crore floor", "NTA test averaged; it must be met in each year"),
           ("Fails 6(1), since its average operating profit is below the ₹15 crore floor", f"average operating profit is ₹{avg_op:.2f} crore, which passes"),
           ("Fails 6(1); may issue under 6(2) with at least 50% of net offer to QIBs", "6(2) requires at least 75% to QIBs; 50% is the 6(1) ceiling")],
          [f"NTA: FY-1 = ₹{nta[2]} crore < ₹3 crore → NTA test fails (must hold in EACH of 3 years; average ₹{avg_nta:.2f} crore is irrelevant).",
           f"Operating profit: average = ({' + '.join(map(str, op))}) ÷ 3 = ₹{avg_op:.2f} crore, positive each year → passes.",
           "Failing any limb of 6(1) pushes the issuer to 6(2): book building with ≥75% of net offer to QIBs, ≤15% NII, ≤10% retail."],
          "Reg 6(1) all limbs each year; else Reg 6(2) with QIB ≥ 75%", "Averages are used only for the operating-profit limb.",
          kind="numerical", verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Reg 6(1), 6(2), 32(2)")

    pre, prom_pre, fresh, ofs = 8.0, 6.0, 2.0, 1.0  # crore shares
    post = pre + fresh; prom_post = prom_pre - ofs
    mpc = 0.20 * post
    assert mpc == 2.0 and prom_post == 5.0
    B.add(mi, "L2", f"Before its IPO, Tejas Instruments Ltd has {pre:g} crore equity shares, of which the promoters hold {prom_pre:g} crore. The IPO comprises a fresh issue of {fresh:g} crore shares and an offer for sale of {ofs:g} crore shares by the promoters. Issue proceeds are for working capital (no capital-expenditure object). How many promoter shares must be locked in for 18 months as minimum promoter contribution?",
          f"{mpc:g} crore shares",
          [(f"{0.20*pre:g} crore shares", "20% applied to pre-issue capital instead of post-issue capital"),
           (f"{0.20*prom_post:g} crore shares", "20% of the promoters' own holding instead of post-issue capital"),
           (f"{prom_post:g} crore shares", "entire post-issue promoter holding treated as MPC; the excess has only a 6-month lock-in")],
          [f"Post-issue capital = {pre:g} + {fresh:g} (fresh; OFS does not add shares) = {post:g} crore.",
           f"MPC = 20% × {post:g} = {mpc:g} crore shares — locked in for 18 months from allotment (3 years if the objects are capex).",
           f"Promoters hold {prom_post:g} crore post-issue; the excess {prom_post-mpc:g} crore is locked in for 6 months."],
          "MPC = 20% of post-issue capital", "OFS shares change hands but do not change post-issue capital.",
          verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Reg 14, 16 (as amended 2021)")

    gross, gcp = 1200, 180
    acq = min(0.25 * gross, 0.35 * gross - gcp)
    assert acq == 240
    B.add(mi, "L2", f"An issuer's fresh issue will raise gross proceeds of ₹{gross} crore. It earmarks ₹{gcp} crore for general corporate purposes and wants the largest possible amount for acquisitions whose targets are not yet identified. Under the ICDR limits on objects, the maximum amount it can earmark for unidentified acquisitions is:",
          f"₹{acq:g} crore",
          [(f"₹{0.25*gross:g} crore", "25% individual cap applied; combined 35% cap with GCP ignored"),
           (f"₹{0.35*gross:g} crore", "combined 35% cap taken without deducting GCP"),
           (f"₹{0.35*gross-0.25*gross:g} crore", "difference between the two caps taken as the headroom")],
          [f"Unidentified acquisitions ≤ 25% of gross proceeds = ₹{0.25*gross:g} crore.",
           f"GCP + unidentified acquisitions ≤ 35% = ₹{0.35*gross:g} crore → headroom after GCP = {0.35*gross:g} − {gcp} = ₹{0.35*gross-gcp:g} crore.",
           f"Binding limit = min({0.25*gross:g}, {0.35*gross-gcp:g}) = ₹{acq:g} crore."],
          "Min(25% × Gross, 35% × Gross − GCP)", "Both caps apply simultaneously; GCP itself is capped at 25%.",
          verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Reg 7(2), 7(3) (2022 amendment)")

    # =============================== IPO process & book building ===============================
    mp = M("ipo-process-and-book-building")
    B.add(mp, "L1", "In a book-built IPO under the SEBI (ICDR) Regulations, 2018, the price band must satisfy which condition?",
          "Cap ≤ 120% of floor, and cap ≥ 105% of floor",
          [("Cap ≤ 110% of floor, and cap ≥ 105% of floor", "outdated/incorrect band width"),
           ("Cap ≤ 120% of floor, with no minimum spread", "ignores the minimum 105% spread introduced in 2022"),
           ("Floor ≥ 80% of cap, with no minimum spread", "restates the 120% ceiling loosely and drops the 105% minimum")],
          ["The cap on the price band shall be ≤ 120% of the floor price.", "The cap shall be at least 105% of the floor price (minimum spread)."],
          "Floor × 1.05 ≤ Cap ≤ Floor × 1.20", "Two-sided condition: both a maximum and a minimum spread.",
          kind="conceptual", verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Reg 29 (as amended 2022)")

    days = ["Thursday", "Friday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    B.add(mp, "L2", "A main-board IPO closes for bidding on a Thursday (day T). There are no holidays other than Saturdays and Sundays. Under the mandatory listing timeline for public issues, the shares should be listed on:",
          "Tuesday of the following week (T+3 working days)",
          [("Sunday of the same week (T+3 calendar days)", "counts calendar days instead of working days"),
           ("Monday of the following week (T+2 working days)", "T+2 — the day of credit of shares/unblocking, not listing"),
           ("Friday of the following week (T+6 working days)", "old T+6 timeline")],
          ["T = Thursday (issue close).", "T+1 = Friday (basis of allotment), T+2 = Monday (credit/unblock), T+3 = Tuesday (listing).",
           "T+3 has been mandatory for public issues opening on or after 1 December 2023."],
          "Listing on T+3 working days", "Weekends are skipped; the old T+6 timeline no longer applies.",
          verify_fact=True, ref="SEBI circular on T+3 listing (Aug 2023), mandatory from 1 Dec 2023")

    size = 40_00_000
    bids = [(310, 6_00_000), (308, 9_00_000), (306, 14_00_000), (304, 18_00_000), (302, 11_00_000), (300, 7_00_000)]
    cum, cut = 0, None
    rows = []
    for p, q in bids:
        cum += q; rows.append([p, inr(q), inr(cum)])
        if cut is None and cum >= size: cut = p
    maxdem = max(bids, key=lambda x: x[1])[0]
    wavg = sum(p * q for p, q in bids) / sum(q for p, q in bids)
    assert cut == 304 and maxdem == 304
    # max-demand coincides with cut -> choose alternative named distractors
    tbq = table(["Bid price (₹)", "Shares bid at this price"], [[r[0], r[1]] for r in rows])
    B.add(mp, "L3", f"In a book-built issue of {inr(size)} shares (price band ₹300–₹310), the demand at each price point is:\n\n{tbq}\n\nBids at a price are also willing to buy at any lower price. Assuming the issuer fixes the highest price at which the entire issue is subscribed, the issue price is:",
          f"₹{cut}",
          [(f"₹{wavg:.2f}", "demand-weighted average bid price"),
           ("₹306", "cumulated demand only down to ₹306 (29 lakh) — issue not fully covered"),
           ("₹300", "floor price taken as the discovered price")],
          [f"Cumulate demand from the highest price: " + "; ".join(f"₹{r[0]} → {r[2]}" for r in rows) + ".",
           f"Cumulative demand first reaches {inr(size)} at ₹{cut} ({[r[2] for r in rows if r[0]==cut][0]} ≥ {inr(size)}).",
           f"Hence issue price = ₹{cut}."],
          "Issue price = highest price at which cumulative demand ≥ issue size", "Do not average bids; demand is cumulated downward.")

    st = ["Retail individual investors and eligible employees may bid at the 'cut-off' price.",
          "QIBs and non-institutional investors are not permitted to withdraw or lower the size of their bids at any stage.",
          "Anchor investors bid on the last day of the issue period, after QIB demand is known."]
    c, w = stmt_opts([True, True, False],
                     ["cut-off bidding is allowed only for RIIs and employees",
                      "QIB/NII bids cannot be withdrawn or lowered once placed",
                      "anchor bidding is one working day before the issue opens"])
    B.add(mp, "L2", "With reference to book building under the SEBI (ICDR) Regulations, 2018, consider:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w,
          ["Only RIIs (and employees in the reservation) may tick 'cut-off'; others must quote a price.",
           "QIBs and NIIs cannot withdraw or lower their bids at any stage; RIIs can revise or withdraw until issue close.",
           "Anchor bids are taken one working day before the issue opens."],
          "ICDR book-building rules", "Anchor day precedes the issue; it is not the closing day.",
          kind="statement", verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Schedule XIII; Reg 32")

    # =============================== Retail application limits ===============================
    mr = M("retail-application-limits")
    B.add(mr, "L1", "Under the SEBI (ICDR) Regulations, 2018, a 'retail individual investor' in a main-board issue is an individual who applies or bids for specified securities for a value of:",
          "Not more than ₹2 lakh",
          [("Not more than ₹5 lakh", "confuses with the UPI-mandate limit for individual bids"),
           ("Not more than ₹1 lakh", "outdated pre-2010 limit"),
           ("Not more than ₹10 lakh", "confuses with the small-NII / big-NII dividing line")],
          ["RII: individual bidding ≤ ₹2 lakh (in all bids, at the cap for cut-off bids).", "₹2–10 lakh is small NII; above ₹10 lakh is big NII."],
          "RII ≤ ₹2 lakh", "₹5 lakh is the UPI limit, not the RII limit.",
          kind="conceptual", verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Reg 2(1)(vv)")

    fl, cap, lot = 480, 505, 29
    lots = int(200000 // (cap * lot)); lots_f = int(200000 // (fl * lot)); lots_u = int(500000 // (cap * lot))
    assert lots == 13 and lots_f == 14
    B.add(mr, "L2", f"An IPO has a price band of ₹{fl}–₹{cap} and a bid lot of {lot} shares. A retail individual investor bids at the cut-off price. The maximum number of shares he can bid for while remaining a retail individual investor is:",
          f"{lots*lot} shares ({lots} lots)",
          [(f"{lots_f*lot} shares ({lots_f} lots)", "lots computed at the floor price; cut-off bids are valued at the cap"),
           (f"{int(200000//cap)} shares", "₹2 lakh ÷ cap price without rounding down to whole lots"),
           (f"{lots_u*lot} shares ({lots_u} lots)", "₹5 lakh UPI limit used as the retail ceiling")],
          [f"Cut-off bid is blocked at the cap: one lot = {lot} × ₹{cap} = ₹{inr(lot*cap)}.",
           f"₹2,00,000 ÷ ₹{inr(lot*cap)} = {200000/(lot*cap):.2f} → {lots} whole lots.",
           f"Shares = {lots} × {lot} = {lots*lot}."],
          "Max lots = floor(₹2,00,000 ÷ (Cap × Lot))", "Cut-off bids are valued at the upper end of the band.",
          verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Reg 2(1)(vv); Schedule XIII")

    issue, lot = 1_20_00_000, 50
    ret = int(0.35 * issue); nlots = ret // lot; apps = 7_00_000
    assert nlots == 84000
    B.add(mr, "L3", f"A Regulation 6(1) IPO offers {inr(issue)} shares (no reservations), bid lot {lot}. The retail portion receives {inr(apps)} valid applications, every one of them for at least one lot, and is heavily oversubscribed. Under the ICDR allotment rule for retail investors, the retail allotment will be:",
          f"{inr(nlots)} applicants, chosen by lottery, get one lot each",
          [(f"All {inr(apps)} applicants get a proportionate {ret//apps} shares each", "proportionate allotment ignoring the minimum-bid-lot rule"),
           (f"{inr(issue//lot)} applicants, chosen by lottery, get one lot each", "entire issue treated as the retail portion"),
           (f"{inr(int(0.10*issue)//lot)} applicants, chosen by lottery, get one lot each", "10% retail cap of Reg 6(2) applied to a 6(1) issue")],
          [f"Retail portion = 35% × {inr(issue)} = {inr(ret)} shares.",
           f"Minimum-lot allotments possible = {inr(ret)} ÷ {lot} = {inr(nlots)}.",
           f"Since applicants ({inr(apps)}) exceed {inr(nlots)}, a lottery picks {inr(nlots)} applicants for one lot each."],
          "Retail lots = Retail portion ÷ Minimum bid lot", "Retail allotment is not proportionate when oversubscribed.",
          verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Reg 32(1), Schedule XIV")

    # =============================== Green shoe ===============================
    mg = M("green-shoe")
    st = ["The over-allotment under a green shoe option may not exceed 15% of the issue size.",
          "The stabilising agent borrows the over-allotment shares from promoters or pre-issue shareholders.",
          "The stabilisation period may extend up to 90 days from the date of listing."]
    c, w = stmt_opts([True, True, False], ["GSO cap is 15% of issue size", "SA borrows shares from promoters/pre-issue holders",
                                          "the stabilisation period is up to 30 days from listing/trading"])
    B.add(mg, "L1", "Regarding the green shoe option (price stabilisation mechanism) under the SEBI (ICDR) Regulations, consider:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w,
          ["Over-allotment ≤ 15% of issue size.", "SA (usually a BRLM) borrows shares from promoters/pre-issue shareholders under an agreement.",
           "Stabilisation lasts up to 30 days from the date of commencement of trading."],
          "GSO: 15% / 30 days", "90 days is the anchor lock-in for the second half, not the stabilisation period.",
          kind="statement", verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Reg 57, Schedule XIII")

    iss, bought = 2_00_00_000, 18_00_000
    ova = int(0.15 * iss); fresh_g = ova - bought
    B.add(mg, "L2", f"An IPO of {inr(iss)} shares carries a green shoe option exercised in full at the time of allotment. During stabilisation the price slips below the issue price and the stabilising agent buys {inr(bought)} shares from the market. How many shares must the company issue at the end of the stabilisation period?",
          f"{inr(fresh_g)} shares",
          [(f"{inr(bought)} shares", "market purchases treated as the fresh-issue quantity"),
           (f"{inr(ova)} shares", "market purchases ignored; entire over-allotment issued afresh"),
           ("Nil", "assumes market purchases fully cover the over-allotment")],
          [f"Over-allotment = 15% × {inr(iss)} = {inr(ova)} shares (borrowed from promoters).",
           f"SA returns {inr(bought)} shares bought from the market to the promoters.",
           f"Shortfall {inr(ova)} − {inr(bought)} = {inr(fresh_g)} shares are issued by the company to the promoters."],
          "Fresh issue = Over-allotment − Shares bought in stabilisation", "The company issues only what the SA could not buy back.",
          verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Schedule XIII (green shoe)")

    ip, ap = 250, 238
    fund = ova * ip; spent = bought * ap; to_co = fresh_g * ip; resid = fund - spent - to_co
    assert round(resid) == 21_600_000
    B.add(mg, "L3", f"Continuing: issue price ₹{ip}; the {inr(ova)} over-allotted shares were paid for in full into the GSO bank account; the stabilising agent bought {inr(bought)} shares at an average ₹{ap}; the company allots the remaining shares at the issue price. Ignoring expenses, the amount left in the GSO bank account and its destination is:",
          f"{crore(resid)}, transferred to the Investor Protection Fund of the stock exchange",
          [(f"{crore(fund - spent)}, transferred to the Investor Protection Fund of the stock exchange", "payment to the company for fresh shares not deducted"),
           (f"{crore(resid)}, paid to the issuer company", "wrong destination; issuer receives only the price of the fresh shares"),
           (f"{crore(resid)}, paid to the promoters who lent the shares", "wrong destination; lenders get shares back, not the surplus")],
          [f"Inflow = {inr(ova)} × ₹{ip} = {crore(fund)}.",
           f"Market purchases = {inr(bought)} × ₹{ap} = {crore(spent)}.",
           f"Paid to company for {inr(fresh_g)} shares = {crore(to_co)}.",
           f"Residual = {crore(resid)} → Investor Protection Fund of the exchange."],
          "Residual = OA × Issue price − Buyback cost − Fresh issue remittance", "The stabilisation 'profit' belongs to neither issuer nor promoters.",
          verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Schedule XIII, para on GSO bank account")

    # =============================== Underwriting & devolvement ===============================
    mu = M("underwriting-and-devolvement")
    B.add(mu, "L1", "In the context of a public issue, 'devolvement' on an underwriter means:",
          "The underwriter must take up the unsubscribed part of its commitment",
          [("The underwriter's commission is passed on to its sub-underwriters", "confuses with brokerage/sub-underwriting commission"),
           ("The issue is withdrawn as minimum subscription is not received", "confuses with refund on failure of minimum subscription"),
           ("The underwriter buys shares in the market to support the listing price", "confuses with price stabilisation (green shoe)")],
          ["If an issue is undersubscribed, the shortfall 'devolves' on the underwriters in proportion to their commitments.",
           "They must take up (or procure subscribers for) those securities."],
          "Net liability = Gross commitment − Applications credited", "Devolvement is about shortfall in subscription, not price support.", kind="conceptual")

    g = {"A": 6.0, "B": 4.0}; mk = {"A": 5.0, "B": 2.0}; um = 1.0
    netB = g["B"] - mk["B"] - um * 0.4
    B.add(mu, "L2", "An issue of 10 lakh shares is underwritten by A (60%) and B (40%). Applications received: marked A 5 lakh, marked B 2 lakh, unmarked 1 lakh. There is no firm underwriting. B's net liability is:",
          f"{netB:.2f} lakh shares",
          [(f"{g['B']-mk['B']:.2f} lakh shares", "unmarked applications not credited"),
           (f"{g['B']-mk['B']-um*0.5:.2f} lakh shares", "unmarked applications split equally instead of in underwriting ratio"),
           (f"{g['B']-mk['B']-um*2/7:.4f} lakh shares", "unmarked applications split in ratio of marked applications")],
          ["Gross liability: A 6, B 4 (lakh).", "Unmarked 1 lakh credited 60:40 → A 0.6, B 0.4.",
           f"B: 4 − 0.4 − 2 (marked) = {netB:.2f} lakh."],
          "Net = Gross − Unmarked (in underwriting ratio) − Marked", "Unmarked applications go in the gross underwriting ratio.")

    price, pct_c = 150, 0.05
    shares = 40_00_000; aoa = 0.03
    B.add(mu, "L2", f"A company issues {inr(shares)} equity shares at ₹{price} each; its Articles authorise underwriting commission up to {pct(aoa,0)}. Under the Companies (Prospectus and Allotment of Securities) Rules, 2014, the maximum underwriting commission payable on the full issue is:",
          crore(shares * price * aoa),
          [(crore(shares * price * pct_c), "statutory 5% ceiling applied although the Articles allow less"),
           (crore(shares * price * 0.025), "2.5% ceiling meant for debentures applied to shares"),
           (crore(shares * 10 * aoa), "commission computed on face value ₹10 instead of issue price")],
          ["Rule 13: commission on shares ≤ 5% of the issue price or the rate authorised by the Articles, whichever is less (debentures: 2.5%).",
           f"Applicable rate = min(5%, {pct(aoa,0)}) = {pct(aoa,0)}.",
           f"Commission = {inr(shares)} × ₹{price} × {pct(aoa,0)} = {crore(shares*price*aoa)}."],
          "Max commission = min(5%, AoA rate) × Issue price × Shares", "The lower of the statutory and Articles limits applies.",
          verify_fact=True, ref="Companies Act, 2013 s.40(6); Companies (Prospectus and Allotment of Securities) Rules, 2014 — Rule 13")

    # =============================== NCD / NCRPS face value ===============================
    mn = M("minimum-face-value-ncd")
    B.add(mn, "L1", "After SEBI's 2024 relaxation, the minimum face value at which a listed issuer may issue non-convertible debt securities or NCRPS on a private placement basis, subject to the instrument being plain-vanilla interest/dividend bearing and a merchant banker being appointed, is:",
          "₹10,000",
          [("₹1 lakh", "2022 level, superseded by the 2024 relaxation"),
           ("₹10 lakh", "pre-October 2022 level"),
           ("₹1,000", "confuses with typical face value in public issues of debt")],
          ["Oct 2022: face value reduced from ₹10 lakh to ₹1 lakh.", "July 2024: further reduced to ₹10,000 for plain-vanilla interest/dividend-bearing NCDs/NCRPS, with a merchant banker appointed."],
          "Private placement FV: ₹10 lakh → ₹1 lakh (2022) → ₹10,000 (2024)", "The ₹10,000 figure carries conditions (plain vanilla, merchant banker).",
          kind="conceptual", verify_fact=True, ref="SEBI circular July 2024 on face value of NCS/NCRPS; SEBI (NCS) Regulations, 2021")

    st = ["NCRPS must have a minimum tenure of three years.",
          "NCRPS issued to the public must carry a credit rating of not less than 'AA-' or equivalent.",
          "NCRPS may be issued with no redemption date."]
    c, w = stmt_opts([True, True, False], ["NCRPS minimum tenure is 3 years", "public-issue NCRPS need at least AA- rating",
                                          "NCRPS must be redeemable; perpetual instruments (PNCPS/PDIs) are a separate class under Chapter V"])
    B.add(mn, "L2", "Consider the following statements on non-convertible redeemable preference shares (NCRPS) under the SEBI (NCS) Regulations, 2021:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w,
          ["Minimum tenure of NCRPS is 3 years.", "Public issue of NCRPS requires a rating of at least AA- (or equivalent).",
           "NCRPS must be redeemable. Perpetual instruments (perpetual non-cumulative preference shares, perpetual debt instruments) are a separate class permitted only for banks/NBFCs etc. under Chapter V of the NCS Regulations."],
          "NCRPS: ≥3 yrs tenure, ≥AA- for public issue", "‘Redeemable’ is in the name; PNCPS of banks/NBFCs are a different instrument.",
          kind="statement", verify_fact=True, ref="SEBI (NCS) Regulations, 2021 — NCRPS provisions and Chapter V (PDIs/PNCPS); SEBI circular Feb 2023")

    B.add(mn, "L3", "Match the regime (List I) with the minimum face value for privately placed non-convertible debt securities (List II):\n\n"
          + table(["List I — Regime", "List II — Minimum face value"],
                  [["A. Before October 2022", "1. ₹10,000"], ["B. October 2022 circular", "2. ₹10 lakh"],
                   ["C. July 2024 circular (plain-vanilla, with merchant banker)", "3. ₹1 lakh"]], ["---", "---"]),
          "A-2, B-3, C-1",
          [("A-3, B-2, C-1", "reverses the first two regimes"),
           ("A-2, B-1, C-3", "attributes the 2024 relaxation to 2022"),
           ("A-1, B-3, C-2", "treats the evolution as an increase in face value")],
          ["Pre-Oct 2022: ₹10 lakh.", "Oct 2022: ₹1 lakh.", "July 2024: ₹10,000 (conditions apply)."],
          "₹10 lakh → ₹1 lakh → ₹10,000", "Each step reduced the face value to widen participation.",
          kind="conceptual", verify_fact=True, ref="SEBI circulars Oct 2022 and July 2024 (NCS face value)")

    # =============================== REITs & InvITs ===============================
    mre = M("invits-and-reits")
    B.add(mre, "L1", "Under the SEBI (REIT) Regulations, 2014, at least what proportion of the value of a REIT's assets must be in completed and rent- or income-generating properties?",
          "80%", [("90%", "confuses with the NDCF distribution requirement"), ("75%", "confuses with NBFC-IFC/MFI asset tests"), ("51%", "simple-majority guess; no such rule")],
          ["Reg 18: ≥ 80% of value in completed and rent/income-generating properties.", "Balance ≤ 20% may be in under-construction assets, listed/unlisted debt, G-secs, MF units etc."],
          "≥80% completed income-generating assets", "90% is the distribution rule, not the asset rule.",
          kind="conceptual", verify_fact=True, ref="SEBI (REIT) Regulations, 2014 — Reg 18")

    ndcf, np_, units = 540, 410, 30
    dpu = 0.9 * ndcf / units
    B.add(mre, "L2", f"A listed REIT has net distributable cash flows (NDCF) of ₹{ndcf} crore and accounting net profit of ₹{np_} crore for the half-year, with {units} crore units outstanding. The minimum distribution per unit required by the REIT Regulations is:",
          f"₹{dpu:.2f}",
          [(f"₹{ndcf/units:.2f}", "100% of NDCF distributed"),
           (f"₹{0.9*np_/units:.2f}", "90% applied to accounting profit instead of NDCF"),
           (f"₹{0.8*ndcf/units:.2f}", "80% (asset-test figure) applied to NDCF")],
          [f"Minimum distribution = 90% × ₹{ndcf} crore = ₹{0.9*ndcf:g} crore.", f"Per unit = {0.9*ndcf:g} ÷ {units} = ₹{dpu:.2f}."],
          "Min DPU = 90% × NDCF ÷ Units", "The base is NDCF, not accounting profit.",
          verify_fact=True, ref="SEBI (REIT) Regulations, 2014 — Reg 18 (distribution of NDCF)")

    B.add(mre, "L2", "Match each party in an InvIT/REIT structure (List I) with its role (List II):\n\n"
          + table(["List I", "List II"], [["A. Trustee", "1. Operates and maintains the infrastructure assets of an InvIT"],
                                          ["B. Investment manager", "2. Holds assets in trust for unitholders; must be a SEBI-registered debenture trustee not associated with sponsor/manager"],
                                          ["C. Project manager", "3. Makes investment decisions for the InvIT"],
                                          ["D. Sponsor", "4. Sets up the trust and must hold a minimum unitholding with lock-in"]], ["---", "---"]),
          "A-2, B-3, C-1, D-4",
          [("A-3, B-2, C-1, D-4", "trustee and investment manager roles swapped"),
           ("A-2, B-1, C-3, D-4", "investment manager and project manager swapped"),
           ("A-4, B-3, C-1, D-2", "trustee and sponsor swapped")],
          ["Trustee: SEBI-registered debenture trustee, holds assets for unitholders.", "Investment manager: investment decisions.",
           "Project manager: execution/O&M of projects.", "Sponsor: settles the trust; minimum holding with lock-in."],
          "Four-party structure", "InvITs have a project manager; REITs have a manager and no project manager.",
          kind="conceptual", verify_fact=True, ref="SEBI (InvIT) Regulations, 2014 — Reg 2, 4, 10, 11")

    va, ex = 12000, 3600
    head = 0.49 * va - ex
    B.add(mre, "L3", f"A listed REIT's assets are valued at ₹{inr(va)} crore; consolidated borrowings net of cash are ₹{inr(ex)} crore. It holds a AAA rating and has unitholder approval for borrowing beyond 25%. Assuming the asset value and cash stay unchanged, the maximum further borrowing permitted by the REIT Regulations is:",
          f"₹{inr(head)} crore",
          [(f"₹{inr(0.70*va-ex)} crore", "InvIT 70% ceiling applied to a REIT"),
           (f"₹{inr(0.49*va)} crore", "existing borrowings not deducted from the 49% ceiling"),
           ("Nil — borrowings already exceed the 25% limit", "ignores the rating-plus-approval route up to 49%")],
          [f"Ceiling = 49% × {inr(va)} = ₹{inr(0.49*va)} crore.", f"Headroom = {inr(0.49*va)} − {inr(ex)} = ₹{inr(head)} crore.",
           "Above 25% requires credit rating and unitholder approval, both available here."],
          "Headroom = 49% × Asset value − Existing net borrowings", "25% is a trigger for conditions, not a hard ceiling.",
          verify_fact=True, ref="SEBI (REIT) Regulations, 2014 — Reg 20")

    # =============================== Social Stock Exchange ===============================
    ms = M("social-stock-exchange")
    B.add(ms, "L1", "A Zero Coupon Zero Principal (ZCZP) instrument on a Social Stock Exchange is:",
          "An NPO-issued security paying neither coupon nor principal back",
          [("A zero-coupon bond issued at a discount by a for-profit enterprise", "confuses with deep-discount bonds"),
           ("A Social Impact Fund unit that returns only the principal invested", "confuses SIF units with ZCZP"),
           ("A grant to an NPO that is later converted into its equity capital", "NPOs have no equity; ZCZP is not convertible")],
          ["ZCZP is a securities-law instrument issued by an NPO registered on the SSE segment.", "Subscribers receive no coupon and no principal repayment — economically a donation, but listed/reported."],
          "ZCZP = NPO + no coupon + no principal", "For-profit social enterprises raise through equity/debt, not ZCZP.",
          kind="conceptual", verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Chapter X-A (Social Stock Exchange)")

    st = ["The minimum issue size for a public issue of ZCZP instruments is ₹50 lakh.",
          "The minimum application size for a ZCZP public issue is ₹1,000.",
          "A for-profit social enterprise may issue ZCZP instruments once it is registered on the SSE."]
    c, w = stmt_opts([True, True, False], ["2023 relaxation reduced minimum issue size to ₹50 lakh", "minimum application reduced to ₹1,000 (2025)",
                                          "only not-for-profit organisations can issue ZCZP"])
    B.add(ms, "L2", "Consider the following statements about fund-raising on the Social Stock Exchange:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["Minimum issue size for ZCZP: ₹50 lakh (reduced from ₹1 crore).", "Minimum application: ₹1,000 (₹2 lakh → ₹10,000 in 2023 → ₹1,000 in 2025).",
                 "ZCZP is available only to NPOs; FPSEs use equity/debt routes."],
          "ZCZP: ₹50 lakh issue / ₹1,000 application", "Old values (₹1 crore issue; ₹2 lakh and ₹10,000 application) are common traps.",
          kind="statement", verify_fact=True, ref="SEBI (ICDR) Regulations Chapter X-A, as amended 2023; SEBI Board decision 19 Mar 2025 and circular (ZCZP min application ₹1,000)")

    rev = [(70, 100), (62, 100), (60, 100)]; exp_ = [(66, 90), (63, 92), (72, 96)]; ben = [(68, 100), (65, 100), (66, 100)]
    r_avg = sum(a for a, b in rev) / sum(b for a, b in rev); e_avg = sum(a for a, b in exp_) / sum(b for a, b in exp_)
    b_avg = sum(a for a, b in ben) / sum(b for a, b in ben)
    passes = [n for n, v in (("revenue", r_avg), ("expenditure", e_avg), ("beneficiaries", b_avg)) if v >= 0.67]
    assert passes == ["expenditure"], (r_avg, e_avg, b_avg)
    tbs = table(["Year", "Revenue from eligible population / total (₹ lakh)", "Expenditure on eligible population / total (₹ lakh)", "Eligible beneficiaries / total (%)"],
                [[f"Y{i+1}", f"{rev[i][0]} / {rev[i][1]}", f"{exp_[i][0]} / {exp_[i][1]}", f"{ben[i][0]} / {ben[i][1]}"] for i in range(3)])
    B.add(ms, "L3", f"Seva Pragati Foundation (an NPO) wants to register on the SSE. The '67% test' may be met on any one of three bases, each measured as an average over the preceding three years.\n\n{tbs}\n\nOn which basis/bases does it satisfy the test?",
          "Expenditure basis only",
          [("Revenue basis only", f"Y1 alone (70%) exceeds 67% but the 3-year average is {r_avg*100:.2f}%"),
           ("Beneficiary basis only", f"3-year average of beneficiaries is {b_avg*100:.2f}%, below 67%"),
           ("None — it must satisfy all three bases", "the test needs any ONE basis, not all three")],
          [f"Revenue: {sum(a for a,b in rev)} ÷ {sum(b for a,b in rev)} = {r_avg*100:.2f}% (<67%).",
           f"Expenditure: {sum(a for a,b in exp_)} ÷ {sum(b for a,b in exp_)} = {e_avg*100:.2f}% (≥67%).",
           f"Beneficiaries: {b_avg*100:.2f}% (<67%).", "Meeting any one basis suffices → expenditure basis."],
          "Average over 3 years ≥ 67% on revenue OR expenditure OR beneficiaries", "Average across years, not a single good year; any one basis suffices.",
          verify_fact=True, ref="SEBI (ICDR) Regulations, 2018 — Chapter X-A, eligibility of social enterprises (67% test)")

    # =============================== Municipal & revenue bonds ===============================
    mm = M("municipal-and-revenue-bonds")
    B.add(mm, "L1", "A municipal 'revenue bond' differs from a 'general obligation' bond mainly because it is:",
          "Repaid only from the financed project's own revenues, not general taxes",
          [("Backed by the full faith, credit and taxing power of the municipality", "describes a general obligation bond"),
           ("Guaranteed by the State Government in every case, whatever the project", "state guarantee is optional credit enhancement, not the defining feature"),
           ("Always exempt from income tax in the hands of investors in the bonds", "tax-free status depends on specific notification")],
          ["Revenue bond: repaid from project revenues (tolls, water charges) often via escrow.", "GO bond: backed by general revenues/taxing power."],
          "Revenue bond ↔ project cash flows", "Credit enhancement does not change the repayment source.", kind="conceptual")

    rev_, om, int_, prin = 96.0, 38.0, 22.0, 18.0
    dscr = (rev_ - om) / (int_ + prin)
    B.add(mm, "L2", f"A water-supply revenue bond: annual user-charge collections ₹{rev_:g} crore, O&M expenses ₹{om:g} crore, annual interest ₹{int_:g} crore and scheduled principal ₹{prin:g} crore. The debt service coverage ratio is:",
          f"{dscr:.2f}x",
          [(f"{rev_/(int_+prin):.2f}x", "gross collections used; O&M not deducted"),
           (f"{(rev_-om)/int_:.2f}x", "interest coverage computed; principal ignored"),
           (f"{(rev_-om-int_)/prin:.2f}x", "interest deducted from numerator and denominator reduced to principal")],
          [f"Net revenue available = {rev_:g} − {om:g} = ₹{rev_-om:g} crore.", f"Debt service = {int_:g} + {prin:g} = ₹{int_+prin:g} crore.",
           f"DSCR = {rev_-om:g} ÷ {int_+prin:g} = {dscr:.2f}x."],
          "DSCR = (Revenue − O&M) ÷ (Interest + Principal)", "Principal must be in debt service.")

    st = ["The municipality must not have had negative net worth in any of the three immediately preceding financial years.",
          "The municipality must not have defaulted in repayment of debt securities or loans in the last 365 days.",
          "Municipal debt securities may be issued to the public with a tenor of six months to meet cash-flow mismatches."]
    c, w = stmt_opts([True, True, False], ["negative net worth in any of preceding 3 FYs bars issue", "no default in last 365 days is a condition",
                                          "minimum tenor is 3 years; short-term cash-flow paper is not permitted"])
    B.add(mm, "L3", "With reference to public issues of municipal debt securities under SEBI regulations, consider:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["Eligibility: no negative net worth in any of 3 preceding FYs.", "No default in repayment in last 365 days.",
                 "Minimum tenor of municipal debt securities is 3 years."],
          "SEBI (Issue and Listing of Municipal Debt Securities) conditions", "Muni bonds finance projects; they are not money-market paper.",
          kind="statement", verify_fact=True, ref="SEBI (Issue and Listing of Municipal Debt Securities) Regulations, 2015 — Reg 4, 5")

    # =============================== SCRA 1956 ===============================
    msc = M("securities-contracts-regulation")
    B.add(msc, "L1", "Under Section 18A of the Securities Contracts (Regulation) Act, 1956, contracts in derivatives are legal and valid if they are:",
          "Traded on a recognised exchange and settled via its clearing corporation",
          [("Entered into between two SEBI-registered intermediaries, on or off exchange", "OTC derivatives between intermediaries are not covered by 18A"),
           ("Approved in advance by the Reserve Bank of India for each counterparty", "RBI governs OTC interest-rate/FX derivatives, not 18A validity"),
           ("Registered with a depository within seven days of their execution", "depository registration is not a validity condition")],
          ["Section 18A overrides other laws: derivatives are legal and valid if traded on a recognised stock exchange and settled on its clearing house/recognised clearing corporation."],
          "SCRA s.18A", "Exchange trading plus exchange/clearing-corporation settlement are both required.",
          kind="conceptual", verify_fact=True, ref="SCRA, 1956 — s.18A")

    mc = 3200
    mpo = 400
    assert 1600 < mc <= 4000
    B.add(msc, "L2", f"A company's post-issue market capitalisation at the issue price will be ₹{inr(mc)} crore. Under Rule 19(2)(b) of the Securities Contracts (Regulation) Rules, 1957, the minimum value of shares it must offer to the public in its IPO is:",
          f"₹{mpo} crore",
          [(f"₹{inr(0.25*mc)} crore", "25% slab (for market cap up to ₹1,600 crore) applied"),
           (f"₹{inr(0.10*mc)} crore", "10% slab (for market cap above ₹4,000 crore up to ₹50,000 crore) applied"),
           (f"₹{inr(0.25*1600)} crore plus 10% of the excess over ₹1,600 crore", "invents a marginal-rate formula for the middle slab")],
          ["Slabs (post-issue market cap, as amended March 2026): ≤ ₹1,600 cr → 25%; > ₹1,600–4,000 cr → ₹400 cr; > ₹4,000–50,000 cr → 10%; > ₹50,000 cr–1 lakh cr → ₹1,000 cr and ≥ 8%; > ₹1–5 lakh cr → ₹6,250 cr and ≥ 2.75%; > ₹5 lakh cr → ₹15,000 cr and ≥ 1% (minimum 2.5%).",
           f"₹{inr(mc)} crore falls in the second slab → ₹400 crore (= {400/mc*100:.1f}% here)."],
          "SCRR Rule 19(2)(b) slabs", "The middle slab is a fixed amount, not a percentage.",
          verify_fact=True, ref="SCRR, 1957 — Rule 19(2)(b), as amended by SCR (Amendment) Rules, March 2026")

    B.add(msc, "L3", "Match the provisions of the SCRA, 1956 (List I) with their subject (List II):\n\n"
          + table(["List I", "List II"], [["A. Section 2(h)", "1. Appeal to SAT against refusal of listing"], ["B. Section 3/4", "2. Definition of 'securities'"],
                                          ["C. Section 21A", "3. Recognition of stock exchanges"], ["D. Section 22", "4. Delisting of securities"]], ["---", "---"]),
          "A-2, B-3, C-4, D-1",
          [("A-2, B-3, C-1, D-4", "delisting and appeal swapped"), ("A-3, B-2, C-4, D-1", "definition and recognition swapped"),
           ("A-2, B-4, C-3, D-1", "recognition and delisting swapped")],
          ["2(h): securities.", "3–4: application for and grant of recognition.", "21A: delisting.", "22: appeal against refusal to list (to SAT)."],
          "SCRA map", "21 = listing conditions; 21A = delisting; 22 = appeal.", kind="conceptual", verify_fact=True, ref="SCRA, 1956 — ss.2(h), 3, 4, 21A, 22")

    # =============================== SEBI Act 1992 ===============================
    msa = M("sebi-act-1992")
    B.add(msa, "L1", "Under Section 4 of the SEBI Act, 1992, the Board consists of a Chairman and:",
          "2 MoF officials, 1 RBI member and 5 others (at least 3 whole-time)",
          [("2 RBI members, 1 MoF official and 5 others (at least 3 whole-time)", "RBI and Finance Ministry numbers swapped"),
           ("1 member each from MoF, RBI, IRDAI and PFRDA, and 4 whole-time members", "invents cross-regulator membership"),
           ("2 MoF officials, 1 RBI member and 2 other whole-time members only", "omits the five 'other' members")],
          ["s.4(1): Chairman; 2 members from officials of the Ministry dealing with Finance/Company Law; 1 member from RBI; 5 other members, at least 3 whole-time."],
          "SEBI Board = 1 + 2 + 1 + 5", "At least three of the five others must be whole-time.",
          kind="conceptual", verify_fact=True, ref="SEBI Act, 1992 — s.4")

    prof = 12
    mx = max(25, 3 * prof)
    B.add(msa, "L2", f"An insider made a profit of ₹{prof} crore from trading on UPSI. The maximum monetary penalty an adjudicating officer can impose under Section 15G of the SEBI Act, 1992 is:",
          f"₹{mx} crore",
          [("₹25 crore", "ignores the 'three times the profit, whichever is higher' limb"),
           (f"₹{25+prof} crore", "adds ₹25 crore and the profit instead of taking the higher amount"),
           (f"₹{prof} crore", "limits penalty to disgorgement of the profit")],
          ["s.15G: penalty not less than ₹10 lakh, may extend to ₹25 crore or three times the profit made, whichever is higher.",
           f"3 × {prof} = ₹{3*prof} crore > ₹25 crore → maximum ₹{mx} crore."],
          "Max = higher of ₹25 crore and 3 × profit", "‘Whichever is higher’ — not additive.",
          verify_fact=True, ref="SEBI Act, 1992 — s.15G")

    st = ["An appeal against an order of a SEBI adjudicating officer lies to the Securities Appellate Tribunal within 45 days of receipt of the order.",
          "An appeal against a SAT order lies to the Supreme Court within 60 days, on any question of law arising out of the order.",
          "A SEBI order passed with the consent of the parties is also appealable to SAT."]
    c, w = stmt_opts([True, True, False], ["s.15T: 45 days to SAT", "s.15Z: 60 days to SC on question of law", "s.15T(2): no appeal lies against a consent order"])
    B.add(msa, "L3", "Consider the following statements on appeals under the SEBI Act, 1992:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["s.15T(3): appeal to SAT within 45 days (condonable).", "s.15Z: appeal to Supreme Court within 60 days on a question of law.",
                 "s.15T(2): no appeal lies against an order made with the consent of parties."],
          "SAT 45 days → SC 60 days", "Consent orders are not appealable.", kind="statement", verify_fact=True, ref="SEBI Act, 1992 — ss.15T, 15Z")

    # =============================== RA & IA ===============================
    mra = M("research-analyst-and-investment-adviser")
    a, r = ("An individual registered as an investment adviser cannot also act as a mutual fund distributor to any client.",
            "The IA Regulations require segregation of advisory and distribution activities at client level only for non-individual advisers, while individual IAs are barred from distribution altogether.")
    c, w = ar_opts(0, {1: "treats R as unrelated although it states the very rule producing A",
                       2: "rejects R; the client-level segregation for non-individuals and bar for individuals is the rule",
                       3: "rejects A; individual IAs cannot distribute"})
    B.add(mra, "L1", ar_stem(a, r), c, w,
          ["Individual IAs cannot provide distribution services (to any client).", "Non-individual IAs must segregate at client level: advice and distribution to the same client/family are not allowed; distribution via a separate subsidiary/division.",
           "R explains why A holds."], "IA Regs — Reg 22 (segregation)", "Client-level segregation vs outright bar: know who faces which.",
          kind="assertion-reason", verify_fact=True, ref="SEBI (Investment Advisers) Regulations, 2013 — Reg 22 (as amended 2020)")

    aua = 80_00_000
    fee_aua = 0.025 * aua
    B.add(mra, "L2", f"A registered investment adviser charges an individual client's family on the assets-under-advice mode. The family's AUA across all its accounts is {R(aua)}. The maximum annual fee permitted under the IA Regulations is:",
          R(fee_aua),
          [(R(151000), "fixed-fee mode ceiling applied to an AUA-mode client"),
           (R(0.02 * aua), "2% instead of 2.5% of AUA"),
           (R(0.025 * aua / 2), "half-yearly advance cap confused with annual fee ceiling")],
          ["Fee limits (individual/HUF clients): AUA mode ≤ 2.5% of AUA per annum per family; fixed-fee mode ≤ ₹1,51,000 per annum per family.",
           f"2.5% × {inr(aua)} = {R(fee_aua)}."],
          "AUA mode: 2.5% p.a. per family", "Each mode has its own ceiling; do not mix them.",
          verify_fact=True, ref="SEBI (Investment Advisers) Regulations — Reg 15A; SEBI circular on IA fees (as revised Dec 2024)")

    pub = dt.date(2026, 3, 16)
    start = pub - dt.timedelta(days=30); end = pub + dt.timedelta(days=5)
    fmt = lambda d: d.strftime("%d %B %Y").lstrip("0")
    B.add(mra, "L3", f"A research analyst publishes a research report recommending shares of Kaveri Cables Ltd on {fmt(pub)}. Under the SEBI (Research Analysts) Regulations, 2014, the analyst and associates are barred from dealing in those shares during the window:",
          f"From {fmt(start)} to {fmt(end)}",
          [(f"From {fmt(pub - dt.timedelta(days=5))} to {fmt(pub + dt.timedelta(days=30))}", "30-day and 5-day limbs reversed"),
           (f"From {fmt(pub)} to {fmt(pub + dt.timedelta(days=30))}", "only a post-publication blackout applied"),
           (f"From {fmt(pub - dt.timedelta(days=30))} to {fmt(pub)}", "post-publication 5-day blackout omitted")],
          ["RA and associates shall not deal in the recommended securities 30 days before and 5 days after publication.",
           f"{fmt(pub)} − 30 days = {fmt(start)}; + 5 days = {fmt(end)}."],
          "Blackout: 30 days before, 5 days after", "The longer window is before publication.",
          verify_fact=True, ref="SEBI (Research Analysts) Regulations, 2014 — Reg 16")

    # =============================== CASE C1: IPO ===============================
    iss = 1_50_00_000; qib = 0.50 * iss; anc = 0.60 * qib; net_q = qib - anc; mf = 0.05 * net_q
    nii = 0.15 * iss; snii = nii / 3; ret_ = 0.35 * iss
    ap_, ipx = 250, 252
    case1 = ("**Case — Vardhan Agritech Ltd IPO.** Vardhan satisfies Regulation 6(1) of the ICDR Regulations and offers "
             f"{inr(iss)} equity shares by book building at a price band of ₹240–₹252 (no employee or shareholder reservation). "
             "It uses the maximum anchor allocation. Anchor investors are allotted at ₹250; the issue is later priced at the cap of ₹252. "
             "Allotment to all categories is on the same day; listing follows on T+3.")
    B.add(mi, "L4", case1 + f"\n\nHow many shares are available for allocation to QIBs **other than** anchor investors and **other than** the portion reserved for mutual funds?",
          f"{inr(net_q-mf)} shares",
          [(f"{inr(net_q)} shares", "mutual-fund reservation (5% of net QIB) not carved out"),
           (f"{inr(qib-0.05*qib)} shares", "anchor portion not deducted; MF 5% applied to whole QIB portion"),
           (f"{inr(qib-anc/3*1-0.05*(qib))} shares", "only one-third of the anchor book deducted and MF 5% applied to the whole QIB portion")],
          [f"QIB portion ≤ 50% → {inr(qib)}.", f"Anchor = 60% of QIB = {inr(anc)}.", f"Net QIB = {inr(net_q)}; 5% for MFs = {inr(mf)}.",
           f"Available to all QIBs (other than the MF reservation) = {inr(net_q-mf)}."],
          "Net QIB = QIB − Anchor; MF reserve = 5% of Net QIB", "The 5% MF reservation is on the net QIB portion, after anchors.",
          kind="case", group="C1-VARDHAN-IPO", verify_fact=True, ref="ICDR Reg 32(1), Schedule XIII (anchor, MF reservation)")
    assert net_q - mf == 2850000

    B.add(mi, "L4", case1 + "\n\nWhat is the position regarding the price difference for anchor investors?",
          f"Anchors must pay an additional ₹{ipx-ap_} per share, i.e. {lakh((ipx-ap_)*anc)} in aggregate",
          [(f"Anchors receive a refund of ₹{ipx-ap_} per share, i.e. {lakh((ipx-ap_)*anc)}", "direction reversed"),
           ("No adjustment — anchors keep the allocation price of ₹250", "ignores the pay-in of the difference when issue price is higher"),
           (f"Anchors pay the difference only on the one-third reserved for mutual funds, i.e. {lakh((ipx-ap_)*anc/3)}", "restricts the adjustment to MF anchors")],
          ["If issue price > anchor price, anchors pay the difference by the pay-in date; if lower, no refund.", f"Additional = ₹{ipx-ap_} × {inr(anc)} = {lakh((ipx-ap_)*anc)}."],
          "Top-up = (Issue price − Anchor price) × Anchor shares, if positive", "One-way adjustment: pay up, never refunded.",
          kind="case", group="C1-VARDHAN-IPO", verify_fact=True, ref="ICDR Schedule XIII — anchor investors")

    B.add(mr, "L4", case1 + "\n\nWhat is the minimum allocation available to non-institutional investors applying for more than ₹2 lakh and up to ₹10 lakh?",
          f"{inr(snii)} shares",
          [(f"{inr(nii*2/3)} shares", "two-thirds sub-category (above ₹10 lakh) taken"),
           (f"{inr(nii)} shares", "entire NII portion treated as the small-NII bucket"),
           (f"{inr(ret_/3)} shares", "one-third applied to the retail portion")],
          [f"NII portion ≥ 15% → {inr(nii)}.", f"One-third for bids > ₹2 lakh to ₹10 lakh → {inr(snii)}; two-thirds for > ₹10 lakh → {inr(nii*2/3)}."],
          "sNII = NII ÷ 3", "Unsubscribed portion in one NII sub-category can go to the other.",
          kind="case", group="C1-VARDHAN-IPO", verify_fact=True, ref="ICDR Reg 32(3A) (2022 amendment)")

    B.add(mi, "L4", case1 + "\n\nHow many anchor shares become free of lock-in 30 days after allotment, and when is the balance released?",
          f"Half ({inr(anc/2)}) after 30 days; the other half after 90 days",
          [(f"All {inr(anc)} anchor shares are released after 30 days", "pre-2022 single 30-day lock-in"),
           (f"Half ({inr(anc/2)}) after 30 days; the other half after 18 months", "confuses with promoter MPC lock-in"),
           (f"None after 30 days; all {inr(anc)} are released after 90 days", "applies the longer limb to the full anchor book")],
          [f"Anchor shares = {inr(anc)}.", "50% locked for 30 days, remaining 50% for 90 days from allotment."],
          "Anchor lock-in 50% × 30 days + 50% × 90 days", "The split lock-in came in 2022.",
          kind="case", group="C1-VARDHAN-IPO", verify_fact=True, ref="ICDR Schedule XIII (as amended 2022) — anchor lock-in")

    # =============================== CASE C2: Underwriting ===============================
    ratio = {"P": 0.5, "Q": 0.3, "R": 0.2}; size_ = 50.0
    firm = {"P": 2.0, "Q": 1.0, "R": 0.5}; mkd = {"P": 18.0, "Q": 15.6, "R": 6.0}; unm = 4.0

    def devolve(firm_as_marked=True):
        gross = {k: size_ * v for k, v in ratio.items()}
        u = unm + (0 if firm_as_marked else sum(firm.values()))
        bal = {k: gross[k] - u * ratio[k] - mkd[k] - (firm[k] if firm_as_marked else 0) for k in ratio}
        neg = {k: -v for k, v in bal.items() if v < 0}
        pos = [k for k in bal if bal[k] >= 0]
        for k, s in neg.items():
            tot = sum(ratio[p] for p in pos)
            for p in pos: bal[p] -= s * ratio[p] / tot
            bal[k] = 0
        return bal, neg
    net, sur = devolve(True); net2, sur2 = devolve(False)
    assert abs(sur["Q"] - 2.8) < 1e-9 and abs(net["P"] - 1.0) < 1e-9 and abs(net["R"] - 1.9) < 1e-9
    tu = table(["Underwriter", "Share of issue", "Firm underwriting (lakh)", "Marked applications (lakh)"],
               [[k, pct(ratio[k], 0), firm[k], mkd[k]] for k in ratio])
    case2 = (f"**Case — Meghdoot Motors Ltd.** A public issue of {size_:g} lakh equity shares of ₹10 each at ₹120 is underwritten as below. "
             f"Unmarked applications total {unm:g} lakh shares. Firm underwriting applications are to be treated as **marked** applications "
             "(credited to the respective underwriter), and any surplus of an underwriter is shared by the others in their underwriting ratio. "
             "Underwriting commission is 2% of the issue price on shares underwritten.\n\n" + tu)
    B.add(mu, "L4", case2 + "\n\nWhat is Q's surplus after crediting unmarked, marked and firm applications?",
          f"{sur['Q']:.2f} lakh shares",
          [(f"{sur2['Q']:.2f} lakh shares", "firm applications treated as unmarked"),
           (f"{abs(size_*0.3 - mkd['Q'] - firm['Q']):.2f} lakh shares", "unmarked applications not credited to Q"),
           (f"{mkd['Q'] - size_*0.3:.2f} lakh shares", "only marked applications compared with gross liability")],
          ["Gross: P 25, Q 15, R 10.", "Unmarked 4 in 5:3:2 → P 2.0, Q 1.2, R 0.8.",
           f"Q: 15 − 1.2 − 15.6 (marked) − 1.0 (firm) = −{sur['Q']:.2f} → surplus {sur['Q']:.2f} lakh."],
          "Balance = Gross − Unmarked share − Marked − Firm", "Firm allotment convention changes the answer.",
          kind="case", group="C2-MEGHDOOT-UW")
    B.add(mu, "L4", case2 + "\n\nWhat is P's net liability (excluding its firm underwriting)?",
          f"{net['P']:.2f} lakh shares",
          [(f"{net2['P']:.4f} lakh shares", "firm applications treated as unmarked"),
           (f"{25 - 2.0 - 18 - 2.0:.2f} lakh shares", "Q's surplus not shared out"),
           (f"{25 - 2.0 - 18 - 2.0 - sur['Q']/2:.2f} lakh shares", "Q's surplus split equally between P and R")],
          ["P balance before surplus = 25 − 2.0 − 18 − 2.0 = 3.00.", f"Q's surplus {sur['Q']:.2f} shared P:R = 5:2 → P gets {sur['Q']*5/7:.2f}.",
           f"P net = 3.00 − {sur['Q']*5/7:.2f} = {net['P']:.2f} lakh."],
          "Surplus shared in underwriting ratio among deficit underwriters", "Ratio for surplus sharing excludes the surplus underwriter.",
          kind="case", group="C2-MEGHDOOT-UW")
    B.add(mu, "L4", case2 + "\n\nIn total, how many shares must R take up (net liability plus firm underwriting)?",
          f"{net['R']+firm['R']:.2f} lakh shares",
          [(f"{net['R']:.2f} lakh shares", "firm underwriting not added to total take-up"),
           (f"{net2['R']+firm['R']:.4f} lakh shares", "firm applications treated as unmarked"),
           (f"{10 - 0.8 - 6.0:.2f} lakh shares", "firm underwriting and Q's surplus both ignored")],
          ["R balance = 10 − 0.8 − 6.0 − 0.5 = 2.70.", f"Less share of Q's surplus (2/7 × {sur['Q']:.2f}) = {sur['Q']*2/7:.2f} → net {net['R']:.2f}.",
           f"Total take-up = {net['R']:.2f} + firm 0.5 = {net['R']+firm['R']:.2f} lakh."],
          "Total = Net liability + Firm underwriting", "Firm underwriting is taken up regardless of subscription.",
          kind="case", group="C2-MEGHDOOT-UW")
    comm = 25_00_000 * 120 * 0.02
    B.add(mu, "L4", case2 + "\n\nWhat underwriting commission is payable to P?",
          lakh(comm),
          [(lakh((net['P'] + firm['P']) * 1e5 * 120 * 0.02), "commission only on shares actually taken up"),
           (lakh(25_00_000 * 10 * 0.02), "computed on face value instead of issue price"),
           (lakh(25_00_000 * 120 * 0.05), "statutory 5% ceiling used instead of agreed 2%")],
          ["Commission is on the entire underwriting commitment, whether or not shares devolve.", f"25 lakh × ₹120 × 2% = {lakh(comm)}."],
          "Commission = Shares underwritten × Issue price × Rate", "Commission is earned on the commitment, not the devolvement.",
          kind="case", group="C2-MEGHDOOT-UW")
