"""FIN-B part 4: inflation, real rates, public finance, WPI, PPP & SCBA, income-tax procedure, MF schemes & TER
+ case sets C7 (highway PPP), C8 (inflation targeting), C9 (NRI mutual fund investor)."""
from finb_common import (M, statements, stmt_opts, ar_opts, ar_stem, table, f2, inr, R, pct, lakh, crore)


def ann(r, n):
    return (1 - (1 + r) ** -n) / r


def add_all(B):
    # =============================== Inflation control measures ===============================
    mic = M("inflation-control-measures")
    B.add(mic, "L1", "Which of the following is a supply-side measure to control food inflation?",
          "Stock limits on traders and open-market sale of buffer stocks",
          [("Raising the policy repo rate to curb aggregate demand", "monetary (demand-side) measure"),
           ("Increasing the cash reserve ratio to drain bank liquidity", "monetary measure that drains liquidity"),
           ("Cutting the fiscal deficit by curbing government spending", "fiscal (demand-side) measure")],
          ["Supply-side tools raise or release supply: buffer-stock sales, stock limits, import-duty cuts, export curbs, Price Stabilisation Fund."],
          "Demand-side (monetary/fiscal) vs supply-side tools", "Rate and reserve changes work through demand.", kind="conceptual")

    st = ["The inflation target is set by the Central Government in consultation with the RBI, once in every five years.",
          "The target is deemed to be missed if average inflation stays above the upper tolerance level or below the lower tolerance level for any three consecutive quarters.",
          "On such failure, the RBI must report to the Central Government the reasons, the remedial actions proposed and the estimated time to achieve the target.",
          "Decisions of the Monetary Policy Committee must be unanimous."]
    c, w = stmt_opts([True, True, True, False], ["s.45ZA — Government sets target in consultation with RBI every 5 years",
                                                "failure = 3 consecutive quarters outside the band",
                                                "s.45ZN report on failure", "MPC decides by majority; Governor has a casting vote"], flips=[1, 2, 3])
    B.add(mic, "L3", "Regarding India's flexible inflation-targeting framework under the RBI Act, 1934, consider:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["s.45ZA: target set by GoI in consultation with RBI, once every 5 years.", "Failure: average CPI inflation outside band for 3 consecutive quarters (notified framework).",
                 "s.45ZN: report reasons, remedial actions, time frame.", "s.45ZL: majority vote; Governor's casting vote on a tie."],
          "RBI Act ss.45ZA, 45ZL, 45ZN", "MPC is not a consensus body.", kind="statement", verify_fact=True, ref="RBI Act, 1934 — ss.45ZA, 45ZL, 45ZN; Monetary Policy Framework notification")

    # =============================== Inflation estimates & consequences ===============================
    mie = M("inflation-estimates")
    c0, c1, may = 190.4, 199.3, 198.1
    inf = c1 / c0 - 1
    B.add(mie, "L2", f"The all-India CPI (combined) was {c0} in June last year, {may} in May this year and {c1} in June this year. Year-on-year CPI inflation for June this year is:",
          pct(inf),
          [(pct((c1 - c0) / c1), "change divided by the current index instead of the base"),
           (pct(c1 / may - 1), "month-on-month change reported as inflation"),
           (f"{c1-c0:.2f}%", "index-point change read as a percentage")],
          [f"Inflation = ({c1} − {c0}) ÷ {c0} = {pct(inf)}."],
          "π = (I_t − I_{t−12}) ÷ I_{t−12}", "Divide by the year-ago index.")

    j0, u0, j1, u1 = 180.0, 186.0, 189.0, 190.0
    jun, jul, mom1, mom0 = j1 / j0 - 1, u1 / u0 - 1, u1 / j1 - 1, u0 / j0 - 1
    B.add(mie, "L3", "CPI index values:\n\n" + table(["", "June", "July"], [["Last year", j0, u0], ["This year", j1, u1]])
          + "\n\nWhat is year-on-year inflation for July this year, and why is it so different from June's?",
          f"{pct(jul)}; base effect from last July's {pct(mom0)} monthly jump",
          [(f"{pct(jun+mom1)}; June's inflation plus this July's monthly rise", "adds m-o-m change to last month's y-o-y rate"),
           (f"{pct(jul)}; prices actually fell month-on-month in July this year", f"prices actually rose {pct(mom1)} m-o-m; no deflation"),
           (f"{pct(mom1)}; this month's momentum is the headline inflation rate", "month-on-month momentum reported as y-o-y inflation")],
          [f"June y-o-y = {j1}/{j0} − 1 = {pct(jun)}.", f"July y-o-y = {u1}/{u0} − 1 = {pct(jul)}.",
           f"This July's momentum was {pct(mom1)} against {pct(mom0)} last July — the high base pulls y-o-y down."],
          "y-o-y change ≈ current momentum − momentum a year ago (base effect)", "Headline can fall even while prices rise.")

    # =============================== Nominal vs real ===============================
    mnr = M("nominal-vs-real")
    i_, p_ = 0.092, 0.055
    real = (1 + i_) / (1 + p_) - 1
    B.add(mnr, "L2", f"A bond yields {pct(i_,1)} nominal while expected inflation is {pct(p_,1)}. The real rate using the exact Fisher relation is:",
          pct(real, 3),
          [(pct(i_ - p_, 3), "linear approximation (i − π)"),
           (pct((i_ - p_) / (1 + i_), 3), "difference divided by (1 + nominal) instead of (1 + inflation)"),
           (pct((1 + i_) * (1 + p_) - 1, 3), "inflation compounded in instead of removed")],
          [f"1 + r = (1 + {i_}) ÷ (1 + {p_}) = {(1+i_)/(1+p_):.5f} → r = {pct(real,3)}."],
          "(1 + i) = (1 + r)(1 + π)", "The approximation overstates r when rates are high.")

    fd, tx, inf2 = 0.075, 0.30, 0.054
    ptn = fd * (1 - tx); ptr = (1 + ptn) / (1 + inf2) - 1
    B.add(mnr, "L3", f"A depositor in the 30% tax bracket earns {pct(fd,1)} on a fixed deposit when inflation is {pct(inf2,1)}. Her post-tax real return (exact) is:",
          pct(ptr, 2),
          [(pct((1 + fd) / (1 + inf2) - 1, 2), "tax ignored (pre-tax real return)"),
           (pct(((1 + fd) / (1 + inf2) - 1) * (1 - tx), 2), "tax applied to the real return instead of the nominal interest"),
           (pct(ptn, 2), "inflation ignored (post-tax nominal return)")],
          [f"Post-tax nominal = {pct(fd,1)} × 0.70 = {pct(ptn,2)}.", f"Real = 1.0525 ÷ 1.054 − 1 = {pct(ptr,2)}."],
          "r_post-tax = (1 + i(1 − t)) ÷ (1 + π) − 1", "Tax falls on nominal interest — real return can turn negative.")

    # =============================== Non-tax revenue ===============================
    mnt = M("non-tax-sources-of-revenue")
    st = ["Dividends from public sector enterprises and the surplus transferred by the RBI.",
          "Proceeds from disinvestment of government equity in PSUs.",
          "Interest received on loans given by the Centre to State Governments."]
    c, w = stmt_opts([True, False, True], ["dividends/profits are non-tax revenue", "disinvestment is a non-debt capital receipt", "interest receipts are non-tax revenue"])
    B.add(mnt, "L2", "Which of the following are non-tax revenue receipts of the Union Government?\n\n" + statements(st) + "\n\nSelect the correct answer.",
          c, w, ["Non-tax revenue: interest receipts, dividends & profits (incl. RBI surplus), fees/user charges, external grants, receipts of services.",
                 "Disinvestment and recovery of loans are capital receipts (non-debt)."],
          "Revenue receipts = Tax + Non-tax", "Disinvestment reduces assets — capital, not revenue.", kind="statement")

    items = [("GST (Centre's share)", 900000, "tax"), ("Interest receipts", 40000, "ntr"), ("Dividends and profits (incl. RBI surplus)", 280000, "ntr"),
             ("Fees, user charges and other services", 25000, "ntr"), ("External grants", 1000, "ntr"), ("Disinvestment receipts", 50000, "cap"),
             ("Recovery of loans and advances", 25000, "cap")]
    ntr = sum(v for _, v, k in items if k == "ntr")
    B.add(mnt, "L3", "Budget extract of a fictional Union Government (₹ crore):\n\n" + table(["Receipt", "Amount"], [[n, inr(v)] for n, v, _ in items])
          + "\n\nNon-tax revenue is:",
          f"₹{inr(ntr)} crore",
          [(f"₹{inr(ntr+50000)} crore", "disinvestment receipts included"),
           (f"₹{inr(ntr+25000)} crore", "recovery of loans included"),
           (f"₹{inr(ntr-1000)} crore", "external grants excluded")],
          [f"Non-tax revenue = 40,000 + 2,80,000 + 25,000 + 1,000 = ₹{inr(ntr)} crore.", "Disinvestment and loan recoveries are non-debt capital receipts; GST is tax."],
          "NTR = Interest + Dividends/profits + Fees/services + Grants", "External grants sit in non-tax revenue.")

    # =============================== WPI ===============================
    mw = M("wpi-components")
    B.add(mw, "L1", "In the Wholesale Price Index (base 2011-12), which major group carries the largest weight?",
          "Manufactured products",
          [("Primary articles", "second-largest group (about 23%)"), ("Fuel and power", "smallest major group (about 13%)"),
           ("Services", "WPI does not cover services")],
          ["Weights (2011-12): Primary articles ≈ 22.6%, Fuel & power ≈ 13.2%, Manufactured products ≈ 64.2%."],
          "WPI groups: Primary / Fuel & power / Manufactured", "No services in WPI.", kind="conceptual", verify_fact=True, ref="Office of the Economic Adviser, DPIIT — WPI (2011-12 series)")

    wts = [("Primary articles", 22.62, 0.060), ("Fuel and power", 13.15, -0.020), ("Manufactured products", 64.23, 0.030)]
    head = sum(wg * r for _, wg, r in wts) / 100
    B.add(mw, "L3", "Year-on-year inflation in the WPI major groups this month is given below. Treat the weights as the effective weights.\n\n"
          + table(["Major group", "Weight (%)", "Group inflation (y-o-y)"], [[n, wg, pct(r, 1)] for n, wg, r in wts]) + "\n\nHeadline WPI inflation is approximately:",
          pct(head),
          [(pct(sum(r for _, _, r in wts) / 3), "simple average of group inflation rates"),
           (pct(sum(wg * abs(r) for _, wg, r in wts) / 100), "negative fuel inflation treated as positive"),
           (pct((22.62 * 0.06 + 64.23 * 0.03) / (22.62 + 64.23)), "fuel group dropped and weights re-based")],
          ["Headline ≈ Σ weight × group inflation:"] + [f"{n}: {wg}% × {pct(r,1)} = {wg*r:.4f}" for n, wg, r in wts] + [f"Total = {pct(head)}."],
          "π ≈ Σ wᵢ πᵢ", "Negative contributions must keep their sign.")

    # =============================== PPP models ===============================
    mpp = M("ppp-models")
    B.add(mpp, "L1", "Under the Hybrid Annuity Model (HAM) for national highways, the authority pays what share of the bid project cost to the concessionaire during construction?",
          "40%", [("60%", "the developer's share, recovered later through annuities"), ("20%", "confuses with VGF from the Centre"),
                  ("100%", "describes EPC, where the authority funds the whole project")],
          ["HAM: 40% of bid project cost paid during construction (in milestone-linked instalments); 60% arranged by developer, repaid through semi-annual annuities with interest.",
           "Toll/traffic risk stays with the authority."],
          "HAM = 40 (authority, construction) : 60 (developer, annuities)", "Traffic risk is not with the developer in HAM.", kind="conceptual", verify_fact=True, ref="MoRTH/NHAI Model Concession Agreement — HAM")

    tpc, de = 1500, 0.30
    vgf = 0.20 * tpc + 0.20 * tpc; eq = (tpc - vgf) * de
    B.add(mpp, "L3", f"A state road project under BOT (toll) has a total project cost of ₹{inr(tpc)} crore. It qualifies for the maximum Viability Gap Funding from the Centre, and the project sponsoring authority tops it up to the maximum it is allowed. The concessionaire funds the balance at a debt-equity ratio of 70:30. The concessionaire's equity is:",
          f"₹{eq:g} crore",
          [(f"₹{(tpc-0.20*tpc)*de:g} crore", "sponsoring authority's additional 20% ignored"),
           (f"₹{tpc*de:g} crore", "equity computed on total project cost; VGF ignored"),
           (f"₹{(tpc-vgf)*0.70:g} crore", "debt share reported as equity")],
          [f"VGF = 20% (Centre) + 20% (sponsoring authority) = ₹{vgf:g} crore.", f"Balance = {inr(tpc)} − {vgf:g} = ₹{tpc-vgf:g} crore; equity 30% = ₹{eq:g} crore."],
          "VGF ≤ 20% (GoI) + ≤ 20% (Sponsoring authority)", "The sponsoring authority can match the central VGF.", verify_fact=True, ref="Scheme for Financial Support to PPPs in Infrastructure (VGF scheme)")

    # =============================== Social cost-benefit ===============================
    msc = M("private-vs-social-cost-benefit")
    B.add(msc, "L1", "In social cost-benefit analysis, a 'shadow price' of an input is:",
          "Its social opportunity cost, net of taxes, subsidies and other distortions",
          [("Its prevailing market price, including all indirect taxes levied on it", "market price is what SCBA corrects"),
           ("The price at which the input trades in the informal (black) market", "informal price is not an efficiency price"),
           ("The administered price that the government has fixed for the input", "administered prices are themselves distortions")],
          ["Shadow (accounting) prices reflect true social value/opportunity cost.", "E.g., shadow wage of unskilled labour below market wage where there is unemployment."],
          "Shadow price = social opportunity cost", "Taxes are transfers, not resource costs.", kind="conceptual")

    inv, cf, tax, poll, wage, swf, rp, rs, n = 100, 18, 5, 7, 10, 0.6, 0.12, 0.10, 10
    npv_p = cf * ann(rp, n) - inv
    scf = cf + tax - poll + wage * (1 - swf)
    npv_s = scf * ann(rs, n) - inv
    assert (cf - poll + wage * (1 - swf)) * ann(rs, n) - inv < 0
    B.add(msc, "L3", f"A plant costing ₹{inv} crore yields private post-tax cash flows of ₹{cf} crore a year for {n} years (private NPV at {pct(rp,0)} = ₹{npv_p:.2f} crore). For social appraisal: taxes of ₹{tax} crore a year are transfers; pollution imposes an external cost of ₹{poll} crore a year; the annual wage bill of ₹{wage} crore is for otherwise-unemployed labour with a shadow-wage factor of {swf}. The social discount rate is {pct(rs,0)}. The social NPV is:",
          f"₹{npv_s:.2f} crore",
          [(f"−₹{abs((cf-poll+wage*(1-swf))*ann(rs,n)-inv):.2f} crore", "taxes not added back"),
           (f"₹{(cf+tax+wage*(1-swf))*ann(rs,n)-inv:.2f} crore", "pollution externality ignored"),
           (f"₹{scf*ann(rp,n)-inv:.2f} crore", "private discount rate used for social flows")],
          [f"Social annual flow = {cf} + {tax} (tax) − {poll} (pollution) + {wage}×(1 − {swf}) (labour saving) = ₹{scf:g} crore.",
           f"Annuity factor (10%, 10 yrs) = {ann(rs,n):.4f}.", f"Social NPV = {scf:g} × {ann(rs,n):.4f} − {inv} = ₹{npv_s:.2f} crore."],
          "Social flow = Private flow + Transfers − Externalities + Shadow-price adjustments", "Tax is a cost to the firm but not to society.")

    # =============================== Income tax — assessment & rectification ===============================
    mia = M("income-tax-assessment")
    B.add(mia, "L2", "Under the Income-tax Act, 1961, an individual files the return for AY 2025-26 on 28 July 2025. The last date for service of a scrutiny notice under section 143(2) is:",
          "30 June 2026",
          [("31 December 2026", "9-month limit for processing under s.143(1) applied"),
           ("31 March 2026", "end of the financial year of filing taken as the limit"),
           ("31 July 2026", "12 months from filing assumed")],
          ["s.143(2): notice within 3 months from the end of the FY in which the return is furnished.", "Return furnished in FY 2025-26 → by 30 June 2026."],
          "s.143(2): FY of filing + 3 months", "Processing (143(1)) and scrutiny notice (143(2)) have different limits.",
          verify_fact=True, ref="Income-tax Act, 1961 — s.143(2) proviso (applicable to AY 2025-26)")

    B.add(mia, "L3", "Under the Income-tax Act, 1961, an assessment order for AY 2022-23 under section 143(3) was passed on 15 December 2023. The assessee files a rectification application under section 154, which the Assessing Officer receives on 10 August 2026. The last date to rectify the order at all, and the date by which the AO must dispose of this application, are respectively:",
          "31 March 2028; 28 February 2027",
          [("15 December 2027; 28 February 2027", "4 years counted from the order date instead of end of its FY"),
           ("31 March 2028; 10 February 2027", "6 months counted from the date of receipt instead of end of that month"),
           ("31 March 2027; 28 February 2027", "3-year limit assumed")],
          ["s.154(7): no amendment after 4 years from the end of the FY in which the order was passed → FY 2023-24 ends 31 Mar 2024 → 31 Mar 2028.",
           "s.154(8): on an assessee's application, order within 6 months from the end of the month of receipt → end-Aug 2026 + 6 months = 28 Feb 2027."],
          "s.154(7) 4 years from end of FY; s.154(8) 6 months from end of month", "Both limits run from period-ends, not event dates.",
          verify_fact=True, ref="Income-tax Act, 1961 — s.154(7), 154(8)")

    # =============================== Income tax — penalties & PAN ===============================
    mip = M("income-tax-penalties-and-pan")
    B.add(mip, "L1", "Under the Income-tax Act, 1961 (law as applicable for AY 2025-26), the penalty under section 272B for failure to comply with the PAN provisions of section 139A is:",
          "₹10,000", [("₹5,000", "confuses with the late-filing fee under s.234F"), ("₹1,000", "confuses with the PAN–Aadhaar late-linking fee under s.234H"),
                      ("₹1,00,000", "no such amount for PAN default")],
          ["s.272B(1): failure to comply with s.139A → penalty of ₹10,000.", "Also applies to quoting/intimating a false PAN (s.272B(2))."],
          "s.272B = ₹10,000", "Fees (234F/234H) are not penalties.", kind="conceptual", verify_fact=True, ref="Income-tax Act, 1961 — s.272B")

    ret, asd, rate = 12_00_000, 20_00_000, 0.30 * 1.04
    under = asd - ret; taxu = under * rate; pen = 2.0 * taxu
    B.add(mip, "L3", f"Under the Income-tax Act, 1961 (AY 2025-26), an assessee (all income taxable at the maximum marginal rate of 30% plus 4% cess, no surcharge) returned {R(ret)}. The assessed income is {R(asd)}; the entire difference arose from fabricated purchase invoices. The penalty under section 270A is:",
          R(pen),
          [(R(0.5 * taxu), "50% rate for under-reporting used; fabrication is misreporting"),
           (R(2.0 * under), "200% applied to under-reported income instead of tax thereon"),
           (R(2.0 * under * 0.30), "cess ignored in the tax on under-reported income")],
          [f"Under-reported income = {inr(asd)} − {inr(ret)} = {inr(under)}.", f"Tax thereon = {inr(under)} × 31.2% = {R(taxu)}.",
           f"Misreporting (fabricated evidence) → 200% × {inr(taxu)} = {R(pen)}."],
          "s.270A: 50% (under-reporting) / 200% (misreporting) of tax on under-reported income", "Penalty base is tax, not income.",
          verify_fact=True, ref="Income-tax Act, 1961 — s.270A(7), (8), (9)")

    # =============================== Scheme types & FoF ===============================
    msf = M("scheme-types-and-fund-of-funds")
    B.add(msf, "L2", "Match the SEBI equity scheme category (List I) with its mandatory portfolio condition (List II):\n\n"
          + table(["List I", "List II"], [["A. Large Cap Fund", "1. At least 65% in mid-cap stocks"], ["B. Mid Cap Fund", "2. Maximum of 30 stocks"],
                                          ["C. Multi Cap Fund", "3. At least 80% in large-cap stocks"], ["D. Focused Fund", "4. At least 75% in equity, with at least 25% each in large, mid and small caps"]], ["---", "---"]),
          "A-3, B-1, C-4, D-2",
          [("A-1, B-3, C-4, D-2", "large-cap and mid-cap thresholds swapped"), ("A-3, B-1, C-2, D-4", "multi cap and focused conditions swapped"),
           ("A-3, B-4, C-1, D-2", "mid cap and multi cap swapped")],
          ["Large cap ≥ 80% large caps (top 100).", "Mid cap ≥ 65% mid caps (101–250).", "Multi cap ≥ 75% equity, ≥ 25% each in large/mid/small.", "Focused: ≤ 30 stocks."],
          "SEBI scheme categorisation (2017, multi cap revised 2020)", "Flexi cap has no market-cap minimums; multi cap does.", kind="conceptual",
          verify_fact=True, ref="SEBI circulars on categorisation of MF schemes (Oct 2017; Sep 2020)")

    # =============================== TER & ETFs ===============================
    mte = M("total-expense-ratio")
    slabs = [(500, 0.0225), (250, 0.0200), (1250, 0.0175)]
    aum, rem, cost = 1200, 1200, 0
    for sz, r in slabs:
        take = min(rem, sz); cost += take * r; rem -= take
    ter = cost / aum
    B.add(mte, "L2", "An open-ended active equity scheme is subject to the following TER slabs (given):\n\n"
          + table(["Daily net assets slab", "Max TER on that slab"], [["First ₹500 crore", "2.25%"], ["Next ₹250 crore", "2.00%"], ["Next ₹1,250 crore", "1.75%"]])
          + f"\n\nIf average daily net assets are ₹{inr(aum)} crore, the maximum overall TER is:",
          pct(ter, 4),
          [("2.25%", "top slab applied to the whole AUM"), ("1.75%", "only the slab in which the AUM ends is applied"),
           ("2.00%", "simple average of the three slab rates")],
          [f"Expenses allowed = 500×2.25% + 250×2.00% + 450×1.75% = ₹{cost:.3f} crore.", f"TER = {cost:.3f} ÷ {aum} = {pct(ter,4)}."],
          "Slab-wise TER = Σ slab × rate ÷ AUM", "Slabs work like income-tax brackets.")

    # =============================== CASE C7: Highway PPP ===============================
    bpc = 2400
    auth = 0.40 * bpc; dev = bpc - auth; eq7 = dev * 0.25
    vgf7 = 0.40 * bpc
    ndcf7, units7 = 420, 35
    case7 = (f"**Case — Sahyadri Ghat Highway.** A highway with a bid project cost of ₹{inr(bpc)} crore is being structured. Option 1 is the Hybrid Annuity Model; the developer would fund its share at a debt-equity ratio of 75:25. "
             "Option 2 is BOT (toll) with Viability Gap Funding, the sponsoring authority being willing to top up central VGF to the maximum allowed. "
             f"Traffic studies show the economic IRR (time savings, lower vehicle operating costs, fewer accidents) is well above the social discount rate, but the financial IRR at feasible tolls is below lenders' hurdle. "
             f"After completion, the SPV is to be sold to a listed InvIT expected to generate net distributable cash flows of ₹{ndcf7} crore a year on {units7} crore units.")
    B.add(mpp, "L4", case7 + "\n\nUnder Option 1, how much equity must the developer bring in?",
          f"₹{eq7:g} crore",
          [(f"₹{bpc*0.25:g} crore", "equity computed on total project cost"),
           (f"₹{auth*0.25:g} crore", "developer's share taken as 40% instead of 60%"),
           (f"₹{inr(dev)} crore", "developer's total funding reported as equity")],
          [f"Authority pays 40% = ₹{auth:g} crore during construction.", f"Developer share = 60% = ₹{dev:g} crore; equity 25% = ₹{eq7:g} crore."],
          "Developer equity = 60% × BPC × Equity share", "Only the developer's 60% needs private financing.",
          kind="case", group="C7-GHAT-HIGHWAY", verify_fact=True, ref="HAM Model Concession Agreement")
    B.add(mpp, "L4", case7 + "\n\nUnder Option 2, what is the maximum total VGF (central plus sponsoring authority)?",
          f"₹{vgf7:g} crore",
          [(f"₹{0.20*bpc:g} crore", "only central VGF counted"),
           (f"₹{inr(0.60*bpc)} crore", "HAM-style 60% share confused with VGF"),
           (f"₹{0.30*bpc:g} crore", "30% cap of the social-sector pilot applied")],
          [f"Central VGF ≤ 20% = ₹{0.2*bpc:g} crore; sponsoring authority ≤ 20% = ₹{0.2*bpc:g} crore.", f"Total ≤ ₹{vgf7:g} crore."],
          "VGF ≤ 20% + 20% of TPC", "Enhanced 30%+30% applies only to specified social-infrastructure pilots.",
          kind="case", group="C7-GHAT-HIGHWAY", verify_fact=True, ref="VGF Scheme (DEA) as revised")
    B.add(msc, "L4", case7 + "\n\nIn cost-benefit terms, what justifies public support (VGF or HAM) for this project?",
          "Social returns beat the social discount rate but financial returns miss the hurdle",
          [("The project is financially viable, so support merely boosts developer returns", "contradicts the given financial IRR below hurdle"),
           ("Social NPV is negative, so the support compensates society for the loss", "direction reversed: social returns are high"),
           ("Support only covers construction risk, which cost-benefit analysis ignores", "construction risk allocation is a separate PPP issue")],
          ["SCBA values time savings, VOC savings and safety (non-cash) benefits.", "EIRR > social discount rate but FIRR < hurdle → 'viability gap' justifies public funding."],
          "Fund when Social NPV > 0 but Private NPV < 0", "The gap is financial, not economic.", kind="case", group="C7-GHAT-HIGHWAY")
    B.add(M("invits-and-reits"), "L4", case7 + "\n\nAfter the InvIT acquires the SPV, what is the minimum distribution per unit required each year?",
          f"₹{0.9*ndcf7/units7:.2f}",
          [(f"₹{ndcf7/units7:.2f}", "100% of NDCF assumed"),
           (f"₹{0.8*ndcf7/units7:.2f}", "80% asset-test figure used"),
           (f"₹{0.9*ndcf7/units7/2:.2f}", "annual requirement halved as if only one half-year counted")],
          [f"≥ 90% of NDCF = {0.9*ndcf7:g} crore.", f"Per unit = {0.9*ndcf7:g} ÷ {units7} = ₹{0.9*ndcf7/units7:.2f}."],
          "Min DPU = 90% × NDCF ÷ Units", "The base is NDCF.", kind="case", group="C7-GHAT-HIGHWAY", verify_fact=True, ref="SEBI (InvIT) Regulations, 2014 — Reg 18 (distribution of NDCF)")

    # =============================== CASE C8: Inflation targeting ===============================
    qi = [6.3, 6.6, 6.2, 5.8]; repo8 = 6.50
    real8 = (1 + repo8 / 100) / (1 + qi[3] / 100) - 1
    case8 = ("**Case — Inflation review.** The notified target is 4% CPI inflation with a tolerance band of ±2 percentage points. Quarterly average y-o-y CPI inflation over the last four quarters was: "
             f"Q1 {qi[0]}%, Q2 {qi[1]}%, Q3 {qi[2]}%, Q4 {qi[3]}%. The policy repo rate throughout Q4 was {repo8:.2f}%. In Q4, WPI inflation was only 1.9% "
             "while CPI inflation was 5.8%, with food and services prices rising fastest.")
    B.add(mic, "L4", case8 + "\n\nWhat is the position under the RBI Act, 1934?",
          "Failure after Q3 (3 quarters above 6%); RBI must report to the Government",
          [("No failure — the Act requires four consecutive quarters above 6%", "wrong number of quarters"),
           ("Failure occurred, and the Monetary Policy Committee must be reconstituted", "the Act prescribes a report, not reconstitution"),
           ("No failure — Q4 returned within the band, so the condition is reset", "failure was already complete at Q3")],
          ["Upper tolerance = 6%. Q1–Q3 all above 6% → three consecutive quarters → failure.", "s.45ZN: RBI reports to GoI reasons, remedial actions, estimated time."],
          "Failure = 3 consecutive quarters outside 2–6%", "A later quarter inside the band does not undo the failure.",
          kind="case", group="C8-INFLATION-REVIEW", verify_fact=True, ref="RBI Act s.45ZN; Monetary Policy Framework notification")
    B.add(mnr, "L4", case8 + "\n\nWhat was the ex-post real policy rate in Q4 (exact Fisher relation)?",
          pct(real8, 2),
          [(pct((repo8 - qi[3]) / 100, 2), "linear approximation"),
           (pct((1 + repo8 / 100) / (1 + qi[2] / 100) - 1, 2), "Q3 inflation used"),
           (pct((1 + repo8 / 100) / 1.04 - 1, 2), "target inflation (4%) used for an ex-post measure")],
          [f"r = 1.065 ÷ 1.058 − 1 = {pct(real8,2)}."],
          "r = (1 + i)/(1 + π) − 1", "Ex-post uses realised inflation of the same period.",
          kind="case", group="C8-INFLATION-REVIEW")
    B.add(mie, "L4", case8 + "\n\nWhich best explains the gap between CPI and WPI inflation in Q4?",
          "CPI includes services and weights food heavily; WPI is mostly manufactures",
          [("WPI covers services whereas CPI covers goods only, so WPI lags behind", "reversed: WPI has no services"),
           ("CPI is measured at wholesale prices while WPI is measured at retail prices", "the two are named for the price level they track"),
           ("WPI uses a more recent base year, which automatically lowers measured inflation", "base-year vintage does not mechanically lower inflation")],
          ["WPI ≈ 64% manufactured products, no services.", "CPI has large food (~46% in 2012 series) and services weights — both rising fastest here."],
          "Coverage and weights drive CPI–WPI divergence", "Divergence is common when food/services inflation is high.",
          kind="case", group="C8-INFLATION-REVIEW")

    # =============================== CASE C9: NRI MF investor ===============================
    fof_own, und = 0.009, 0.016
    cap_fof = 0.0225
    nav, inav, mkt = 58.40, 58.62, 59.10
    prem = mkt / inav - 1
    case9 = ("**Case — Rohan, an NRI investor.** Rohan invests from his NRE account on a repatriation basis. "
             f"(i) He considers a domestic fund of funds investing mainly in active equity-oriented schemes, whose TER cap (including the weighted TER of underlying schemes) is {pct(cap_fof)}; "
             f"the underlying schemes' weighted average TER is {pct(und,1)} and the FoF charges {pct(fof_own,1)} itself. "
             f"(ii) He wants to buy a gold ETF for about ₹20 lakh; last NAV ₹{nav}, current iNAV ₹{inav}, market price ₹{mkt}. (iii) He may later sell both and move the money abroad.")
    B.add(msf, "L4", case9 + "\n\nIs the FoF's expense structure compliant, and what is the maximum TER it may charge at its own level?",
          f"Not compliant; own-level TER must not exceed {pct(cap_fof-und,2)}",
          [(f"Compliant; the {pct(fof_own,1)} own TER is below the {pct(cap_fof)} cap", "underlying schemes' TER not added"),
           (f"Not compliant; own-level TER must not exceed {pct(0.01-0,2)}", "1% cap for FoFs investing in liquid/index/ETFs applied"),
           (f"Compliant; own TER can go up to {pct(cap_fof,2)} over and above underlying TER", "cap treated as additional to underlying TER")],
          [f"Total = {pct(fof_own,1)} + {pct(und,1)} = {pct(fof_own+und,1)} > {pct(cap_fof)} → breach.", f"Max own TER = {pct(cap_fof)} − {pct(und,1)} = {pct(cap_fof-und,2)}."],
          "FoF total TER (own + underlying) ≤ cap", "The FoF cap is inclusive of underlying scheme TER.",
          kind="case", group="C9-ROHAN-NRI", verify_fact=True, ref="SEBI (Mutual Funds) Regulations, 1996 — Reg 52(6)(a) (FoF TER)")
    B.add(mte, "L4", case9 + "\n\nWhat premium is Rohan paying, and how must he buy the ETF units?",
          f"{pct(prem,2)} over iNAV; buy on the exchange — direct AMC deals need over ₹25 crore",
          [(f"{pct(mkt/nav-1,2)} over iNAV; buy on the exchange — direct AMC deals need over ₹25 crore", "premium measured against last NAV, not iNAV"),
           (f"{pct(prem,2)} over iNAV; he can subscribe directly with the AMC at the day's NAV", "ignores the ₹25 crore threshold for direct AMC transactions"),
           (f"{pct(1-inav/mkt,2)} over iNAV; buy on the exchange — direct AMC deals need over ₹25 crore", "premium computed on market price as base")],
          [f"Premium = {mkt}/{inav} − 1 = {pct(prem,2)}.", "Investors other than market makers can transact directly with the AMC only for amounts above ₹25 crore."],
          "Premium = Market price ÷ iNAV − 1", "iNAV is the real-time reference, not previous NAV.",
          kind="case", group="C9-ROHAN-NRI", verify_fact=True, ref="SEBI circular on ETFs — direct transactions with AMC (May 2022)")
    B.add(M("nri-and-oci"), "L4", case9 + "\n\nWhen Rohan redeems/sells both investments, how can the proceeds be taken abroad?",
          "Credited to NRE and freely repatriable, as it was a repatriable NRE investment",
          [("Credited to NRO and repatriable only up to USD 1 million per financial year", "treats a repatriation-basis investment as non-repatriable"),
           ("Not repatriable at all; the proceeds must remain in India for three years", "no such lock-in"),
           ("Repatriable only after obtaining prior RBI approval for each remittance", "no approval needed for repatriable-basis proceeds")],
          ["Investment from NRE on repatriation basis → sale proceeds (net of tax) credited to NRE → freely repatriable."],
          "Source of funds decides repatriability", "The USD 1 million facility is for NRO balances.", kind="case", group="C9-ROHAN-NRI",
          verify_fact=True, ref="FEMA (Non-debt Instruments) Rules, 2019; FEMA (Deposit) Regulations, 2016")
