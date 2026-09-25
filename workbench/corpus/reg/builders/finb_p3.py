"""FIN-B part 3: money markets, RBI operations, payments, banking, NBFCs, cross-border, regulators
+ case sets C3 (bank treasury day) and C4 (NBFC compliance)."""
import datetime as dt
from finb_common import (M, statements, stmt_opts, ar_opts, ar_stem, table, f2, inr, R, pct, lakh, crore, irr)


def add_all(B):
    # =============================== Treasury bills ===============================
    mt = M("treasury-bills")
    st = ["Treasury bills are issued at a discount and redeemed at face value.",
          "The Government of India currently issues T-bills in tenors of 91, 182 and 364 days.",
          "T-bills carry a fixed coupon payable half-yearly."]
    c, w = stmt_opts([True, True, False], ["T-bills are zero-coupon discount instruments", "the three GoI tenors are 91/182/364 days",
                                          "T-bills pay no coupon; return is the discount"])
    B.add(mt, "L1", "Consider the following statements about Government of India Treasury bills:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["T-bills are short-term discount instruments issued by RBI on behalf of GoI.", "Tenors: 91, 182, 364 days.", "No coupon — statement 3 is false."],
          "Return = Face value − Issue price", "Cash management bills are a separate, shorter instrument.", kind="statement")

    y, d = 0.068, 182
    p = 100 / (1 + y * d / 365)
    B.add(mt, "L2", f"The cut-off yield in a {d}-day T-bill auction is {pct(y,2)}. The cut-off price per ₹100 face value is:",
          f"₹{p:.4f}",
          [(f"₹{100*(1-y*d/365):.4f}", "discount-yield formula (yield applied to face value) used"),
           (f"₹{100/(1+y*d/360):.4f}", "360-day year used"),
           (f"₹{100/(1+y)**(d/365):.4f}", "compound (annual) discounting used instead of simple money-market convention")],
          [f"P = 100 ÷ (1 + y × d/365) = 100 ÷ (1 + {y} × {d}/365) = ₹{p:.4f}."],
          "P = 100 / (1 + y × d/365)", "Indian T-bill yield is on price, Actual/365.")

    pb, ps, dh, dm = 98.35, 98.90, 30, 91
    hpr = (ps - pb) / pb * 365 / dh; ytm = (100 - pb) / pb * 365 / dm
    B.add(mt, "L3", f"A treasury buys a {dm}-day T-bill at ₹{pb} on issue and sells it {dh} days later at ₹{ps}, after yields fall. Its annualised holding-period return is:",
          pct(hpr),
          [(pct(ytm), "yield to maturity at purchase quoted instead of realised return"),
           (pct((ps - pb) / pb * 365 / dm), "annualised over the bill's full tenor instead of the holding period"),
           (pct((ps - pb) / 100 * 365 / dh), "gain divided by face value instead of purchase price")],
          [f"Gain = {ps} − {pb} = ₹{ps-pb:.2f}.", f"HPR = {ps-pb:.2f} ÷ {pb} × 365/{dh} = {pct(hpr)}.", f"(YTM at purchase was {pct(ytm)}; falling yields raised realised return.)"],
          "Annualised HPR = (P_sell − P_buy)/P_buy × 365/days held", "Selling early at a higher price beats the purchase yield.")

    # =============================== NDS-OM & G-sec auctions ===============================
    mn = M("nds-om-and-the-g-sec")
    B.add(mn, "L1", "NDS-OM (Negotiated Dealing System – Order Matching) is best described as:",
          "RBI-owned anonymous screen for secondary G-sec trading, settled via CCIL",
          [("RBI's platform for conducting primary auctions of dated G-secs and T-bills", "primary auctions run on RBI's E-Kuber system"),
           ("A CCIL-owned platform for anonymous tri-party repo in corporate bonds", "confuses with TREPS/corporate repo platforms"),
           ("An exchange debt segment where retail investors trade G-secs via brokers", "exchange G-sec trading is separate from NDS-OM")],
          ["NDS-OM (2005) — owned by RBI, operated by CCIL; anonymous; settlement via CCIL as CCP (T+1 standard)."],
          "Secondary G-sec trading → NDS-OM; primary auctions → E-Kuber", "Owned by RBI, operated by CCIL.", kind="conceptual", verify_fact=True, ref="RBI — NDS-OM framework")

    notified, ncb, inv, compb = 12000, 750, 2, 18000
    cap = 0.05 * notified; ratio = min(1, cap / ncb)
    B.add(mn, "L2", f"RBI notifies a dated G-sec auction of ₹{inr(notified)} crore, reserving the maximum permitted portion for non-competitive bidders. Non-competitive bids total ₹{ncb} crore and competitive bids ₹{inr(compb)} crore. An eligible retail investor who bid ₹{inv} crore non-competitively will be allotted:",
          f"₹{inv*ratio:.2f} crore",
          [(f"₹{inv:.2f} crore", "non-competitive bids assumed always met in full"),
           (f"₹{inv*notified/(compb+ncb):.2f} crore", "overall auction bid-cover used as the pro-rata ratio"),
           (f"₹{inv*(1-ratio):.2f} crore", "pro-rata ratio inverted")],
          [f"Reservation = 5% × {inr(notified)} = ₹{cap:g} crore.", f"Bids {ncb} > {cap:g} → pro-rata {cap:g}/{ncb} = {ratio*100:.0f}%.", f"Allotment = {inv} × {ratio:.2f} = ₹{inv*ratio:.2f} crore."],
          "Non-competitive reservation ≤ 5% of notified amount (dated G-secs)", "Oversubscribed non-competitive portion is allotted pro-rata.",
          verify_fact=True, ref="RBI scheme for non-competitive bidding in G-sec auctions")

    bids = [(7.02, 1500), (7.04, 2000), (7.05, 1800), (7.06, 1600), (7.08, 1200)]
    amt = 6000; cum = 0; accepted = []
    for yv, a in bids:
        if cum + a <= amt:
            accepted.append((yv, a)); cum += a
        else:
            part = amt - cum; accepted.append((yv, part)); cutoff, pr = yv, part / a; break
    way = sum(yv * a for yv, a in accepted) / amt
    assert cutoff == 7.06 and abs(pr - 0.4375) < 1e-9
    B.add(mn, "L3", f"A multiple-price yield-based auction for a ₹{inr(amt)} crore dated security receives these competitive bids (no non-competitive bids):\n\n"
          + table(["Bid yield (%)", "Amount (₹ crore)"], [[f"{yv:.2f}", inr(a)] for yv, a in bids]) + "\n\nThe cut-off yield and the pro-rata allotment at the cut-off are:",
          f"{cutoff:.2f}%; {pr*100:.2f}%",
          [(f"{cutoff:.2f}%; {(1-pr)*100:.2f}%", "pro-rata computed on the rejected part"),
           ("7.05%; 100%", "stopped at the last fully accepted bid, leaving the issue short"),
           (f"{way:.4f}%; {pr*100:.2f}%", "weighted-average accepted yield reported as the cut-off")],
          ["Accept lowest yields first: " + ", ".join(f"{yv:.2f}% → {inr(a)}" for yv, a in accepted) + ".",
           f"Cumulative at 7.05% = 5,300; need 700 more of 1,600 at 7.06% → {pr*100:.2f}%.",
           "In a multiple-price auction each successful bidder pays its own bid price; the cut-off is the highest accepted yield."],
          "Cut-off = highest yield needed to fill the notified amount", "Lowest yield = highest price = accepted first.")

    # =============================== Repo, TREPS, CROMS ===============================
    mr = M("repo-tri-party-repo-and-croms")
    st = ["CROMS is CCIL's anonymous screen-based order-matching platform for market repo in government securities.",
          "TREPS (tri-party repo dealing and settlement) replaced CBLO as CCIL's collateralised money-market product.",
          "In a tri-party repo, the tri-party agent is the lender of funds."]
    c, w = stmt_opts([True, True, False], ["CROMS = CCIL repo order-matching", "TREPS replaced CBLO in 2018",
                                          "the tri-party agent only manages collateral, settlement and valuation; it is not the lender"])
    B.add(mr, "L1", "Consider the following statements:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["CROMS (Clearcorp Repo Order Matching System) — anonymous market repo in G-secs.", "TREPS replaced CBLO (Nov 2018).",
                 "Tri-party agent (CCIL for TREPS) handles collateral selection, valuation, margining, settlement — not lending."],
          "Repo platforms: CROMS (market repo), TREPS (tri-party)", "Agent ≠ counterparty.", kind="statement", verify_fact=True, ref="RBI Repurchase Transactions (Repo) Directions, 2018; CCIL")

    cash, coll, rr, dd = 100e7, 104.2e7, 0.064, 7
    intr = cash * rr * dd / 365
    B.add(mr, "L2", f"A bank borrows {crore(cash)} in the market repo for {dd} days at {pct(rr,2)}, delivering G-secs with a market value of {crore(coll)}. The repo interest payable in the second leg is:",
          R(intr),
          [(R(cash * rr * dd / 360), "360-day year used"),
           (R(coll * rr * dd / 365), "interest computed on collateral value instead of cash borrowed"),
           (R(cash * rr * (dd + 1) / 365), "an extra day counted (inclusive day count)")],
          [f"Interest = {crore(cash)} × {pct(rr,2)} × {dd}/365 = {R(intr)}.", f"Second-leg amount = {R(cash+intr)}."],
          "Repo interest = Cash × Rate × Days/365", "Interest runs on the cash leg, not the collateral.")

    fvc, clean, ai, h = 50e7, 97.60, 1.35, 0.02
    lent = fvc * (clean + ai) / 100 * (1 - h)
    B.add(mr, "L3", f"In a repo, the lender of funds accepts {crore(fvc)} face value of a G-sec quoted at a clean price of ₹{clean} with accrued interest of ₹{ai} per ₹100. A haircut of {pct(h,0)} applies. The cash the lender will advance is:",
          crore(lent, 4),
          [(crore(fvc * clean / 100 * (1 - h), 4), "clean price used; accrued interest ignored"),
           (crore(fvc * (clean + ai) / 100, 4), "haircut not applied"),
           (crore(fvc * (clean + ai) / 100 * (1 + h), 4), "haircut added instead of deducted")],
          [f"Dirty price = {clean} + {ai} = {clean+ai:.2f}.", f"Market value = {crore(fvc)} × {clean+ai:.2f}% = {crore(fvc*(clean+ai)/100,4)}.",
           f"Cash = MV × (1 − {pct(h,0)}) = {crore(lent,4)}."],
          "Cash = FV × Dirty price × (1 − haircut)", "Haircut protects the cash lender, so it reduces cash.")

    # =============================== SDF / VRRR / LAF ===============================
    ms = M("monetary-policy-operations-sdf")
    st = ["The Standing Deposit Facility lets RBI absorb liquidity without providing collateral to banks.",
          "The SDF rate is the floor of the LAF corridor, a role earlier played by the fixed-rate reverse repo.",
          "The MSF rate is set 50 basis points above the policy repo rate."]
    c, w = stmt_opts([True, True, False], ["SDF is uncollateralised (s.17(2A) RBI Act)", "SDF replaced fixed-rate reverse repo as floor (April 2022)",
                                          "MSF is 25 bps above repo; the whole corridor is 50 bps"])
    B.add(ms, "L2", "Consider the following statements on RBI's liquidity adjustment facility:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["SDF: introduced April 2022 under s.17(2A); no collateral.", "SDF = repo − 25 bps is the floor; MSF = repo + 25 bps is the ceiling.",
                 "Corridor width = 50 bps; MSF is 25 bps above repo."],
          "Corridor: SDF (repo − 25) … MSF (repo + 25)", "50 bps is the width, not the MSF spread.", kind="statement", verify_fact=True, ref="RBI Act, 1934 s.17(2A); RBI MPS April 2022")

    sur, repo, sdf, vrrr, nd = 500e7, 0.06, 0.0575, 0.0592, 3
    gain = sur * (vrrr - sdf) * nd / 365
    B.add(ms, "L3", f"Policy repo is {pct(repo,2)} and SDF {pct(sdf,2)} (given). A bank with a {crore(sur)} surplus for {nd} days can either park it in SDF every night or bid in a {nd}-day VRRR auction whose cut-off is {pct(vrrr,2)}. The additional interest from the VRRR over the {nd} days is:",
          R(gain),
          [(R(sur * (repo - sdf) * nd / 365), "repo rate used instead of VRRR cut-off"),
           (R(sur * (vrrr - sdf) / 365), "computed for one day only"),
           (R(sur * (vrrr - sdf) * nd / 360), "360-day year used")],
          [f"Spread = {pct(vrrr,2)} − {pct(sdf,2)} = {(vrrr-sdf)*1e4:.0f} bps.", f"Gain = {crore(sur)} × {vrrr-sdf:.4f} × {nd}/365 = {R(gain)}."],
          "Gain = Amount × (VRRR − SDF) × days/365", "VRRR bids clear between SDF and repo in surplus conditions.")

    # =============================== RBI Act 1934 ===============================
    ma = M("rbi-act-1934")
    B.add(ma, "L1", "Which section of the RBI Act, 1934 gives the Reserve Bank the sole right to issue bank notes in India?",
          "Section 22", [("Section 24", "deals with denominations of notes"), ("Section 26", "deals with legal tender character"),
                         ("Section 42", "deals with cash reserves of scheduled banks")],
          ["s.22: sole right to issue bank notes.", "s.24 denominations (up to ₹10,000); s.26 legal tender; s.42 CRR."],
          "s.22 = note issue monopoly", "Coins and ₹1 notes are issued by the Government.", kind="conceptual", verify_fact=True, ref="RBI Act, 1934 — s.22")

    st = ["Under the minimum reserve system, RBI must hold gold and foreign securities worth at least ₹200 crore, of which gold must be at least ₹115 crore.",
          "One-rupee notes are issued by RBI and carry the Governor's signature.",
          "Coins are issued by the Government of India and put into circulation through RBI."]
    c, w = stmt_opts([True, False, True], ["s.33 minimum reserve: ₹200 crore with ₹115 crore gold", "₹1 notes are Government issues signed by the Finance Secretary",
                                          "Coinage Act, 2011 — GoI issues coins; RBI distributes"])
    B.add(ma, "L3", "Consider the following statements regarding currency management in India:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["Minimum reserve system (since 1956/57): ₹200 crore, gold ≥ ₹115 crore.", "₹1 notes: issued by GoI, signed by Finance Secretary.",
                 "Coins: GoI under Coinage Act 2011, distributed by RBI."],
          "RBI Act s.33 minimum reserves; Coinage Act 2011", "The ₹1 note is the classic exception to RBI's note monopoly.", kind="statement",
          verify_fact=True, ref="RBI Act, 1934 — ss.22, 33; Coinage Act, 2011")

    B.add(ma, "L3", "Match the provisions of the RBI Act, 1934 (List I) with their subject (List II):\n\n"
          + table(["List I", "List II"], [["A. Section 7", "1. Constitution of the Monetary Policy Committee"], ["B. Section 17", "2. Cash reserve of scheduled banks"],
                                          ["C. Section 42", "3. Central Government's power to give directions to RBI"], ["D. Section 45ZB", "4. Business the Bank may transact"]], ["---", "---"]),
          "A-3, B-4, C-2, D-1",
          [("A-4, B-3, C-2, D-1", "s.7 and s.17 swapped"), ("A-3, B-4, C-1, D-2", "CRR and MPC swapped"),
           ("A-3, B-2, C-4, D-1", "s.17 and s.42 swapped")],
          ["s.7: Government directions in public interest.", "s.17: business RBI may transact.", "s.42: CRR.", "s.45ZB: MPC constitution (45ZA: inflation target)."],
          "RBI Act map", "45ZA sets the target; 45ZB creates the MPC.", kind="conceptual", verify_fact=True, ref="RBI Act, 1934 — ss.7, 17, 42, 45ZB")

    # =============================== RBI Retail Direct ===============================
    mrd = M("rbi-retail-direct")
    B.add(mrd, "L1", "Under the RBI Retail Direct scheme, an individual investor invests in government securities by opening a:",
          "Retail Direct Gilt (RDG) account maintained with RBI",
          [("Constituent SGL (gilt) account with a bank or primary dealer", "older indirect route, not Retail Direct"),
           ("Subsidiary General Ledger account with RBI", "SGL accounts are for banks and institutions"),
           ("Demat account with a depository participant", "the exchange/demat route, not Retail Direct")],
          ["Retail Direct (Nov 2021): individuals open an RDG account directly with RBI through the online portal/app."],
          "Retail Direct → RDG account", "No intermediary and no account fee.", kind="conceptual", verify_fact=True, ref="RBI Retail Direct Scheme, 2021")

    st = ["Investors participate in primary auctions of G-secs and T-bills through non-competitive bidding.",
          "Secondary-market purchase and sale is done through NDS-OM.",
          "Only resident individuals may open an account; NRIs are excluded."]
    c, w = stmt_opts([True, True, False], ["primary access is non-competitive", "secondary access via NDS-OM (odd-lot/RFQ)",
                                          "NRIs eligible to invest in G-secs under FEMA can also open RDG accounts"])
    B.add(mrd, "L2", "Consider the following statements about RBI Retail Direct:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["Primary: non-competitive bids.", "Secondary: NDS-OM.", "Eligibility: resident individuals and NRIs eligible under FEMA (with PAN, KYC, savings account in India)."],
          "Retail Direct scheme features", "NRI eligibility is a common trap.", kind="statement", verify_fact=True, ref="RBI Retail Direct Scheme, 2021 — eligibility")

    # =============================== NPCI & payment systems ===============================
    mp = M("npci-systems")
    B.add(mp, "L2", "Match the payment system (List I) with the correct feature (List II):\n\n"
          + table(["List I", "List II"], [["A. RTGS", "1. Operated by NPCI; per-transaction limit of ₹5 lakh"], ["B. NEFT", "2. Operated by RBI; minimum amount ₹2 lakh"],
                                          ["C. IMPS", "3. On-device wallet; per-transaction limit ₹1,000"], ["D. UPI Lite", "4. Operated by RBI; no minimum or maximum amount"]], ["---", "---"]),
          "A-2, B-4, C-1, D-3",
          [("A-4, B-2, C-1, D-3", "RTGS and NEFT swapped"), ("A-2, B-1, C-4, D-3", "NEFT treated as an NPCI system"),
           ("A-2, B-4, C-3, D-1", "IMPS and UPI Lite limits swapped")],
          ["RTGS: RBI, gross real-time, min ₹2 lakh.", "NEFT: RBI, half-hourly DNS batches, no min/max.", "IMPS: NPCI, ₹5 lakh per transaction.",
           "UPI Lite: per-transaction ₹1,000 (wallet ₹5,000)."],
          "RBI owns RTGS/NEFT; NPCI owns UPI/IMPS/NACH/RuPay", "Do not attribute NEFT/RTGS to NPCI.", kind="conceptual",
          verify_fact=True, ref="RBI circulars on RTGS/NEFT; NPCI IMPS/UPI Lite limits (Dec 2024)")

    st = ["NEFT and RTGS are owned and operated by the Reserve Bank of India, not NPCI.",
          "NPCI was set up as a not-for-profit company by banks under the guidance of RBI and IBA, and is authorised under the Payment and Settlement Systems Act, 2007.",
          "NEFT settles each transaction individually on a gross, real-time basis."]
    c, w = stmt_opts([True, True, False], ["RBI runs NEFT/RTGS", "NPCI is a not-for-profit (s.8) company promoted by banks",
                                          "NEFT is deferred net settlement in half-hourly batches; RTGS is gross real-time"])
    B.add(mp, "L3", "Consider the following statements:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["RTGS and NEFT are RBI-operated.", "NPCI: not-for-profit company promoted by banks (2008) under PSS Act authorisation.",
                 "NEFT: DNS in 48 half-hourly batches, 24×7."],
          "Gross (RTGS) vs deferred net (NEFT)", "24×7 availability does not make NEFT real-time gross.", kind="statement", verify_fact=True, ref="PSS Act, 2007; RBI NEFT/RTGS")

    # =============================== Payments Vision ===============================
    mv = M("payments-vision")
    B.add(mv, "L1", "The core theme of RBI's Payments Vision 2025 is expressed through the '4 Es'. They stand for:",
          "E-Payments for Everyone, Everywhere, Everytime",
          [("Efficiency, Equity, Economy, Enforcement", "invented administrative Es"),
           ("Competition, Cost, Convenience, Confidence", "the 4 Cs of Payments Vision 2019-21"),
           ("E-Payments for Education, Employment, Enterprise, Exports", "invented sectoral Es")],
          ["Payments Vision 2025 (June 2022): 'E-Payments for Everyone, Everywhere, Everytime'."],
          "4Es: E-payments for Everyone, Everywhere, Everytime", "Don't mix with the 2019-21 4Cs.", kind="conceptual", verify_fact=True, ref="RBI Payments Vision 2025 (June 2022)")

    st = ["The anchor goals of Payments Vision 2025 are Integrity, Inclusion, Innovation, Institutionalisation and Internationalisation.",
          "The preceding Payments Vision 2019-21 was built around four goalposts: Competition, Cost, Convenience and Confidence.",
          "Payments Vision 2025 was issued by NPCI as the retail payments umbrella organisation."]
    c, w = stmt_opts([True, True, False], ["the five 'I' anchor goals", "the 4 Cs of Vision 2019-21", "the Vision is an RBI document"])
    B.add(mv, "L2", "Consider the following statements:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["Vision 2025 anchor goals: 5 Is.", "Vision 2019-21: 4 Cs.", "Issued by RBI's Department of Payment and Settlement Systems, not NPCI."],
          "Vision 2025: 4 Es + 5 Is", "NPCI implements; RBI sets the vision.", kind="statement", verify_fact=True, ref="RBI Payments Vision 2025; Payment Systems Vision 2019-21")

    # =============================== Unified Lending Interface ===============================
    mu = M("unified-lending-interface")
    st = ["ULI has been developed by the Reserve Bank Innovation Hub.",
          "It was piloted in 2023 as the 'Public Tech Platform for Frictionless Credit'.",
          "ULI is a government-owned lender that disburses small-ticket loans directly to borrowers."]
    c, w = stmt_opts([True, True, False], ["RBIH built ULI", "pilot name was PTPFC (Aug 2023)", "ULI is infrastructure connecting lenders and data providers, not a lender"])
    B.add(mu, "L2", "Consider the following statements about the Unified Lending Interface (ULI):\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["RBIH developed the platform.", "Pilot Aug 2023 as PTPFC; renamed ULI in 2024.", "ULI does not lend; it is a digital public infrastructure layer."],
          "ULI = plug-and-play credit DPI", "It is infrastructure, not a lender.", kind="statement", verify_fact=True, ref="RBI statements on PTPFC (2023) and ULI (2024)")

    a, r = ("ULI can shorten credit appraisal time for small and rural borrowers such as farmers and MSMEs.",
            "ULI gives lenders consent-based access, through standardised APIs, to digital information held by multiple providers, including state land records.")
    c, w = ar_opts(0, {1: "R is the mechanism that produces A", 2: "rejects R; standardised APIs and consent-based data flow are ULI's design",
                       3: "rejects A; faster appraisal is the stated objective"})
    B.add(mu, "L3", ar_stem(a, r), c, w,
          ["ULI's 'plug and play' APIs aggregate data (land records, dairy/milk pooling data, satellite data etc.) with borrower consent.",
           "Less paperwork and quicker verification → faster credit for thin-file borrowers. R explains A."],
          "ULI → data access → faster appraisal", "Consent-based architecture is central.", kind="assertion-reason", verify_fact=True, ref="RBI Governor's statements on ULI (Aug 2024)")

    # =============================== Payments banks & differentiated banks ===============================
    mpb = M("payment-banks-and-differentiated")
    st = ["A payments bank may hold a maximum end-of-day balance of ₹2 lakh per individual customer.",
          "A payments bank may issue debit cards but not credit cards.",
          "A payments bank may extend small-value loans of up to ₹25 lakh to micro enterprises."]
    c, w = stmt_opts([True, True, False], ["deposit cap raised to ₹2 lakh in 2021", "no credit cards (no lending)",
                                          "payments banks cannot lend; ₹25 lakh is the SFB 50%-portfolio yardstick"])
    B.add(mpb, "L2", "Consider the following statements about payments banks:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["Balance cap ₹2 lakh per individual (end of day).", "Debit/ATM cards yes; credit cards no.", "No lending activities."],
          "Payments bank: deposits + payments, no credit", "₹25 lakh relates to small finance banks' portfolio mix.", kind="statement",
          verify_fact=True, ref="RBI Guidelines for Licensing of Payments Banks (2014), as amended 2021")

    dd_, tb_, fd_ = 1200, 840, 310
    need_g = 0.75 * dd_; cap_b = 0.25 * dd_
    B.add(mpb, "L3", f"A payments bank has demand deposit balances of ₹{inr(dd_)} crore. It holds ₹{tb_} crore in T-bills and SLR-eligible G-secs of up to one-year maturity and ₹{fd_} crore in current and time deposits with scheduled commercial banks (CRR is maintained separately). Which assessment is correct?",
          f"Shortfall of ₹{need_g-tb_:g} crore in eligible securities and excess of ₹{fd_-cap_b:g} crore in bank deposits",
          [("Compliant, since eligible securities and bank deposits together exceed 75% of deposits", "the two buckets have separate floor and ceiling"),
           (f"Shortfall of ₹{need_g-tb_:g} crore in eligible securities only", "25% ceiling on bank deposits not checked"),
           (f"Shortfall of ₹{0.75*(dd_-0.04*dd_)-tb_:g} crore in eligible securities and excess of ₹{fd_-cap_b:g} crore in bank deposits", "75% applied to deposits net of a 4% CRR")],
          [f"Minimum in eligible G-secs/T-bills = 75% × {inr(dd_)} = ₹{need_g:g} crore → shortfall {need_g-tb_:g}.",
           f"Maximum in bank deposits = 25% × {inr(dd_)} = ₹{cap_b:g} crore → excess {fd_-cap_b:g}."],
          "≥75% in SLR securities (≤1 yr); ≤25% in bank deposits", "The two limits are tested separately.",
          verify_fact=True, ref="RBI Guidelines for Licensing of Payments Banks (2014) — deployment of funds")

    # =============================== Priority sector lending ===============================
    mps = M("priority-sector-lending")
    anbc = 80000
    B.add(mps, "L2", f"A domestic scheduled commercial bank's ANBC is ₹{inr(anbc)} crore (higher than its CEOBE). Its minimum lending to small and marginal farmers under the PSL directions is:",
          f"₹{inr(0.10*anbc)} crore",
          [(f"₹{inr(0.18*anbc)} crore", "overall agriculture target (18%) taken"),
           (f"₹{inr(0.08*anbc)} crore", "old 8% SMF sub-target used"),
           (f"₹{inr(0.10*0.40*anbc)} crore", "10% applied to the total PSL target instead of ANBC")],
          [f"SMF sub-target = 10% of ANBC or CEOBE, whichever is higher = 10% × {inr(anbc)} = ₹{inr(0.10*anbc)} crore."],
          "SMF = 10% of ANBC/CEOBE", "Sub-targets are on ANBC, not on the 40% PSL amount.", verify_fact=True, ref="RBI Master Directions — Priority Sector Lending (targets for domestic SCBs)")

    tot_t, agr_t = 0.40 * anbc, 0.18 * anbc
    tot_a, agr_a, pslc = 30400, 13600, 500
    B.add(mps, "L3", f"For the same bank (ANBC ₹{inr(anbc)} crore), achievement before PSLCs is: total PSL ₹{inr(tot_a)} crore; agriculture ₹{inr(agr_a)} crore. It buys PSLC-Agriculture of ₹{pslc} crore. The remaining shortfall against the overall target and the agriculture sub-target is:",
          f"Overall ₹{inr(tot_t-tot_a-pslc)} crore; agriculture ₹{inr(agr_t-agr_a-pslc)} crore",
          [(f"Overall ₹{inr(tot_t-tot_a)} crore; agriculture ₹{inr(agr_t-agr_a-pslc)} crore", "PSLC counted only towards the sub-target"),
           (f"Overall ₹{inr(tot_t-tot_a-pslc)} crore; agriculture ₹{inr(agr_t-agr_a)} crore", "PSLC counted only towards the overall target"),
           (f"Overall ₹{inr(tot_t-tot_a-2*pslc)} crore; agriculture ₹{inr(agr_t-agr_a-pslc)} crore", "PSLC value double-counted in the overall target")],
          [f"Targets: total 40% = {inr(tot_t)}; agriculture 18% = {inr(agr_t)}.",
           f"PSLC-A counts toward both: total {inr(tot_a)} + {pslc} = {inr(tot_a+pslc)} → shortfall {inr(tot_t-tot_a-pslc)}; agri {inr(agr_a)} + {pslc} → shortfall {inr(agr_t-agr_a-pslc)}."],
          "Achievement = Own lending + PSLCs bought", "A PSLC-A counts toward the agriculture sub-target and the overall target.",
          verify_fact=True, ref="RBI Master Directions — PSL; PSLC scheme")

    # =============================== KFS & fair lending ===============================
    mk = M("key-fact-statement")
    B.add(mk, "L1", "Under RBI's directions of April 2024, a Key Fact Statement (KFS) must be provided to prospective borrowers for:",
          "All retail and MSME term loans extended by regulated entities",
          [("Only digital loans sourced through lending service providers/apps", "digital lending was the earlier, narrower KFS mandate"),
           ("Only term loans of more than ₹50 lakh sanctioned to any borrower", "no size threshold applies"),
           ("Only housing, vehicle and education loans to individual borrowers", "applies to all retail and MSME term loans")],
          ["KFS mandate extended (effective 1 Oct 2024) to all retail and MSME term loans by all REs.", "KFS shows APR including all fees and third-party charges."],
          "KFS: standardised, APR-based disclosure", "Charges not disclosed in KFS cannot be levied without explicit consent.", kind="conceptual",
          verify_fact=True, ref="RBI circular on Key Facts Statement for Loans & Advances (15 Apr 2024)")

    L0, ra, n, fee, ins = 200000, 0.15, 12, 0.02, 1800
    rm = ra / 12
    emi = L0 * rm * (1 + rm) ** n / ((1 + rm) ** n - 1)
    net = L0 - fee * L0 - ins
    apr = irr([-net] + [emi] * n) * 12
    apr_noins = irr([-(L0 - fee * L0)] + [emi] * n) * 12
    ear = (1 + apr / 12) ** 12 - 1
    B.add(mk, "L3", f"A personal loan of {R(L0)} at 15% p.a. (monthly reducing) is repayable in {n} EMIs. The lender deducts upfront a processing fee of {pct(fee,0)} of the loan and a credit-life insurance premium of {R(ins)} collected for a third-party insurer. The Annual Percentage Rate (APR) to be shown in the KFS (monthly IRR × 12) is closest to:",
          pct(apr),
          [("15%", "contract interest rate shown; upfront charges ignored"),
           (pct(apr_noins), "third-party insurance premium excluded from APR"),
           (pct(ear), "effective annual rate (compounded) shown instead of APR convention")],
          [f"EMI = {R(emi,2)}.", f"Net amount received = {inr(L0)} − {inr(fee*L0)} − {inr(ins)} = {R(net)}.",
           f"Monthly IRR equating {R(net)} to 12 EMIs = {apr/12*100:.4f}% → APR = {pct(apr)}."],
          "APR = IRR(net disbursal, EMIs) × 12", "Third-party pass-through charges are included in APR.",
          verify_fact=True, ref="RBI KFS circular (Apr 2024) — APR computation annex")

    # =============================== NBFC categories ===============================
    mnb = M("nbfc-categories")
    B.add(mnb, "L1", "To be classified as an NBFC–Infrastructure Finance Company (NBFC-IFC), an NBFC must deploy at least what share of its total assets in infrastructure loans?",
          "75%", [("50%", "confuses with NBFC-Factor principal-business test"), ("60%", "confuses with HFC housing-finance test"),
                  ("90%", "confuses with the CIC investment-in-group test")],
          ["NBFC-IFC: ≥ 75% of total assets in infrastructure loans; NOF ₹300 crore; rating A or equivalent; CRAR 15% (Tier I 10%)."],
          "IFC: 75% infra loans", "Each NBFC category has its own principal-business threshold.", kind="conceptual", verify_fact=True, ref="RBI Master Direction — NBFC (Scale Based Regulation), NBFC-IFC criteria")

    own, agg, x_out, lent_x = 42e5, 50e5, 9.8e5, 20000
    head = min(50000 - lent_x, 10e5 - x_out, agg - own)
    assert head == 20000
    B.add(mnb, "L3", f"A lender on NBFC-P2P platforms (net worth certificate of more than ₹50 lakh on record) has outstanding loans of {R(own)} across all platforms, including {R(lent_x)} to borrower X. X owes {R(x_out)} in total across all P2P platforms. The maximum further amount this lender can lend to X is:",
          R(head),
          [(R(50000 - lent_x), "borrower's aggregate ₹10 lakh cap not checked"),
           (R(50000), "existing exposure to X not deducted from the ₹50,000 per-borrower cap"),
           (R(agg - own), "only the lender's ₹50 lakh aggregate cap applied")],
          ["Caps: lender→single borrower ₹50,000 (all platforms); lender aggregate ₹50 lakh; borrower aggregate ₹10 lakh.",
           f"Per-borrower headroom = 50,000 − {inr(lent_x)} = {inr(50000-lent_x)}; borrower headroom = 10,00,000 − {inr(x_out)} = {inr(10e5-x_out)}; lender headroom = {inr(agg-own)}.",
           f"Binding = {R(head)}."],
          "Headroom = min(₹50,000 − existing, ₹10 lakh − borrower dues, ₹50 lakh − lender total)", "Three caps bind simultaneously.",
          verify_fact=True, ref="RBI Master Direction — NBFC-P2P Lending Platform Directions, 2017 (as amended)")

    # =============================== Scale-based regulation ===============================
    msb = M("scale-based-regulation")
    st = ["All deposit-taking NBFCs are placed at least in the Middle Layer, irrespective of asset size.",
          "A non-deposit-taking NBFC (not an HFC, IFC, CIC, IDF or SPD) with assets of ₹800 crore falls in the Base Layer.",
          "NBFC-P2P platforms and Account Aggregators are placed in the Middle Layer."]
    c, w = stmt_opts([True, True, False], ["deposit-takers are ML or above", "non-deposit NBFCs below ₹1,000 crore are Base Layer",
                                          "P2P and AA are Base Layer entities"])
    B.add(msb, "L2", "Under RBI's Scale-Based Regulation of NBFCs, consider:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["Middle Layer: all deposit-taking NBFCs; non-deposit NBFCs ≥ ₹1,000 crore; SPDs, IDFs, CICs, HFCs, IFCs.",
                 "Base Layer: non-deposit NBFCs < ₹1,000 crore, P2P, AA, NOFHC, Type I.", "Hence statement 3 is false."],
          "SBR: Base / Middle / Upper / Top", "₹1,000 crore asset size is the BL–ML cut-off for non-deposit NBFCs.", kind="statement",
          verify_fact=True, ref="RBI SBR framework (Oct 2021); Master Direction — NBFC (SBR) 2023")

    st = ["The top ten eligible NBFCs by asset size are always placed in the Upper Layer.",
          "An NBFC-UL must be listed within three years of its identification as NBFC-UL.",
          "Once identified, an NBFC stays in the Upper Layer permanently, even if it later ceases to meet the parametric criteria.",
          "NBFC-UL must maintain Common Equity Tier 1 capital of at least 9%."]
    c, w = stmt_opts([True, True, False, True], ["top-10 by asset size are always UL", "mandatory listing within 3 years",
                                                "enhanced requirements continue for at least 5 years from last classification, not permanently",
                                                "CET1 ≥ 9% for NBFC-UL"], flips=[0, 2, 3])
    B.add(msb, "L3", "Regarding the Upper Layer (NBFC-UL) under Scale-Based Regulation, consider:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["Top 10 by asset size: always UL.", "Listing within 3 years of identification.", "Stays subject to UL norms for at least 5 years from last classification — not permanently.",
                 "CET1 ≥ 9% of RWA."],
          "NBFC-UL: top-10 rule, listing in 3 yrs, CET1 9%, 5-year stickiness", "‘Permanently’ overstates the 5-year rule.", kind="statement",
          verify_fact=True, ref="RBI SBR framework (Oct 2021); Master Direction — NBFC (SBR) 2023")

    # =============================== Nostro / vostro / loro ===============================
    mno = M("nostro-vostro")
    B.add(mno, "L1", "An Indian bank maintains a US dollar account with a correspondent bank in New York. From the Indian bank's point of view this account is its:",
          "Nostro account",
          [("Vostro account", "vostro is the same account seen from the New York bank's side"),
           ("Loro account", "loro refers to a third bank's account held with the correspondent"),
           ("Mirror account", "the mirror is the Indian bank's internal shadow record of its nostro")],
          ["Nostro = 'our account with you' (in foreign currency abroad).", "Vostro = 'your account with us'; Loro = 'their account with you'."],
          "Nostro / Vostro / Loro", "The same account is nostro for the owner and vostro for the host.", kind="conceptual")

    st = ["Under the Special Rupee Vostro Account (SRVA) mechanism, a partner-country bank's correspondent opens a rupee vostro account with an authorised Indian bank to settle trade in INR.",
          "Surplus rupee balances in SRVAs may be invested in Government of India securities, including T-bills.",
          "Proceeds received through an SRVA must be converted into US dollars before being credited to the Indian exporter."]
    c, w = stmt_opts([True, True, False], ["SRVA (July 2022) enables INR invoicing and settlement", "surplus balances can go into G-secs/T-bills",
                                          "SRVA settlement is entirely in INR; no USD leg"])
    B.add(mno, "L2", "Consider the following statements on INR settlement of international trade:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["SRVA: INR vostro accounts of partner-country banks with Indian AD banks.", "Surplus balances may be invested in G-secs/T-bills.", "Settlement is in INR — no conversion to USD."],
          "SRVA = INR vostro for trade", "The point of SRVA is to bypass a third currency.", kind="statement", verify_fact=True, ref="RBI A.P. (DIR) circular on INR invoicing (July 2022) and later relaxations")

    # =============================== NRI / OCI ===============================
    mnr = M("nri-and-oci")
    st = ["Balances in NRE accounts, including interest, are freely repatriable.",
          "Funds in NRO accounts may be repatriated up to USD 1 million per financial year, subject to applicable taxes.",
          "FCNR(B) deposits may be maintained in Indian rupees."]
    c, w = stmt_opts([True, True, False], ["NRE is repatriable", "NRO: USD 1 million per FY facility", "FCNR(B) deposits are held in permitted foreign currencies"])
    B.add(mnr, "L2", "Consider the following statements about NRI accounts under FEMA:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["NRE: INR account, fully repatriable.", "NRO: repatriation up to USD 1 million per FY (after tax).", "FCNR(B): term deposits in foreign currency (1–5 years)."],
          "NRE (repatriable) / NRO (limited) / FCNR(B) (foreign currency)", "FCNR is foreign-currency by definition.", kind="statement",
          verify_fact=True, ref="FEMA (Deposit) Regulations, 2016; RBI Master Direction on deposits by non-residents")

    shs, own_, agg_ = 48e7, 0.1e7, 4.3e7
    head = min(0.05 * shs - own_, 0.10 * shs - agg_)
    assert abs(head - 0.5e7) < 1
    B.add(mnr, "L3", f"A listed company has {shs/1e7:g} crore equity shares. Its shareholders have NOT raised the NRI/OCI aggregate limit. NRIs/OCIs together already hold {agg_/1e7:g} crore shares on a repatriation basis, including {own_/1e7:g} crore held by Mr Kapoor, an NRI. How many more shares can Mr Kapoor buy on the stock exchange on a repatriation basis?",
          f"{head/1e7:g} crore shares",
          [(f"{(0.05*shs-own_)/1e7:g} crore shares", "aggregate 10% NRI/OCI limit ignored"),
           (f"{0.05*shs/1e7:g} crore shares", "own holding and aggregate limit both ignored"),
           (f"{(head-own_)/1e7:g} crore shares", "own holding deducted twice")],
          [f"Individual limit = 5% × {shs/1e7:g} crore = {0.05*shs/1e7:g} crore → headroom {(0.05*shs-own_)/1e7:g} crore.",
           f"Aggregate limit = 10% = {0.10*shs/1e7:g} crore → headroom {(0.10*shs-agg_)/1e7:g} crore.", f"Binding = {head/1e7:g} crore shares."],
          "Min(5% − own, 10% − NRI/OCI aggregate)", "Aggregate can go to 24% only by special resolution.",
          verify_fact=True, ref="FEMA (Non-debt Instruments) Rules, 2019 — Schedule III")

    # =============================== Mandate boundaries ===============================
    mmb = M("mandate-boundaries")
    B.add(mmb, "L2", "Match the activity (List I) with its regulator (List II):\n\n"
          + table(["List I", "List II"], [["A. Chit funds", "1. SEBI"], ["B. Nidhi companies", "2. IRDAI"], ["C. Unit-linked insurance plans", "3. State Governments"],
                                          ["D. Exchange-traded commodity derivatives", "4. Ministry of Corporate Affairs"]], ["---", "---"]),
          "A-3, B-4, C-2, D-1",
          [("A-4, B-3, C-2, D-1", "chit funds and nidhis swapped"), ("A-3, B-4, C-1, D-2", "ULIPs attributed to SEBI"),
           ("A-1, B-4, C-2, D-3", "chit funds treated as collective investment schemes under SEBI")],
          ["Chit funds: Chit Funds Act 1982, administered by States.", "Nidhis: MCA (Companies Act s.406).", "ULIPs: IRDAI.", "Commodity derivatives: SEBI (post-2015 FMC merger)."],
          "Regulatory map", "Chit funds are excluded from SEBI's CIS definition.", kind="conceptual", verify_fact=True, ref="Chit Funds Act, 1982; Companies Act s.406; SEBI Act s.11AA")

    st = ["Housing finance companies are regulated by the RBI, while NHB continues to supervise them.",
          "The Atal Pension Yojana is administered by PFRDA.",
          "OTC interest-rate derivatives are regulated by SEBI."]
    c, w = stmt_opts([True, True, False], ["HFC regulation moved to RBI in 2019", "APY is administered by PFRDA", "OTC IRDs fall under RBI (RBI Act Chapter IIID)"])
    B.add(mmb, "L3", "Consider the following statements on regulatory jurisdiction:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["HFCs: regulation with RBI since Aug 2019; supervision with NHB.", "APY: PFRDA.", "OTC interest-rate/FX derivatives: RBI; exchange-traded: SEBI."],
          "Who regulates what", "OTC vs exchange-traded decides the regulator.", kind="statement", verify_fact=True, ref="Finance (No.2) Act, 2019; RBI Act ss.45U-45W")

    # =============================== International bodies ===============================
    mib = M("international-bodies")
    B.add(mib, "L1", "The Financial Action Task Force (FATF) sets its global anti-money-laundering and counter-terror-financing standards through its:",
          "40 Recommendations",
          [("38 Objectives and Principles of Securities Regulation", "IOSCO's standard"), ("29 Core Principles for Effective Banking Supervision", "BCBS standard"),
           ("24 Principles for Financial Market Infrastructures", "CPMI-IOSCO standard")],
          ["FATF (1989, G7; secretariat at OECD, Paris) — 40 Recommendations; India a member since 2010."],
          "FATF → 40 Recommendations", "Each standard-setter has its own numbered principles.", kind="conceptual", verify_fact=True, ref="FATF Recommendations")

    B.add(mib, "L2", "Match the body (List I) with its location and primary role (List II):\n\n"
          + table(["List I", "List II"], [["A. IOSCO", "1. Basel; the 'central bank for central banks', hosts BCBS"], ["B. BIS", "2. Madrid; global standard-setter for securities regulation"],
                                          ["C. FATF", "3. Basel; coordinates G20 financial regulatory reform"], ["D. FSB", "4. Paris; AML/CFT standards and mutual evaluations"]], ["---", "---"]),
          "A-2, B-1, C-4, D-3",
          [("A-2, B-3, C-4, D-1", "BIS and FSB roles swapped"), ("A-4, B-1, C-2, D-3", "IOSCO and FATF swapped"),
           ("A-1, B-2, C-4, D-3", "IOSCO and BIS swapped")],
          ["IOSCO: Madrid (1983).", "BIS: Basel (1930), hosts BCBS/CPMI.", "FATF: Paris (OECD).", "FSB: Basel (2009), G20."],
          "IOSCO–Madrid; BIS/FSB–Basel; FATF–Paris", "Two bodies sit in Basel — distinguish by role.", kind="conceptual", verify_fact=True, ref="Official charters of IOSCO, BIS, FATF, FSB")

    # =============================== CASE C3: Bank treasury day ===============================
    fv3, pc3, d3 = 200e7, 98.53, 91
    y3 = (100 - pc3) / pc3 * 365 / d3
    sur3, treps, sdf3, msf3, repo3, sh3 = 300e7, 0.059, 0.0575, 0.0625, 0.06, 150e7
    case3 = ("**Case — Sahyadri Bank's treasury day.** Policy parameters (given): repo 6.00%, SDF 5.75%, MSF 6.25%. "
             f"On Wednesday the bank wins {crore(fv3)} face value of 91-day T-bills at the cut-off price of ₹{pc3}. "
             f"On Thursday it has a {crore(sur3)} overnight surplus: TREPS is lending at 5.90%, and SDF is available. "
             f"On Friday, after all market options, it is short by {crore(sh3)} overnight and uses the MSF.")
    B.add(mt, "L4", case3 + "\n\nWhat is the annualised yield on the T-bills bought on Wednesday?",
          pct(y3, 3),
          [(pct((100 - pc3) / 100 * 365 / d3, 3), "discount divided by face value (discount yield)"),
           (pct((100 - pc3) / pc3 * 360 / d3, 3), "360-day year used"),
           (pct((100 - pc3) / pc3, 3), "yield not annualised")],
          [f"Discount = 100 − {pc3} = {100-pc3:.2f}.", f"Yield = {100-pc3:.2f}/{pc3} × 365/91 = {pct(y3,3)}."],
          "y = (100 − P)/P × 365/d", "The base is price, not face value.", kind="case", group="C3-SAHYADRI-TREASURY")
    g3 = sur3 * (treps - sdf3) / 365
    B.add(mr, "L4", case3 + "\n\nBy lending the Thursday surplus in TREPS instead of SDF, the bank earns additionally:",
          R(g3),
          [(R(sur3 * (treps - sdf3) / 360), "360-day year used"),
           (R(sur3 * (repo3 - treps) / 365), "compared TREPS with repo instead of SDF"),
           (R(sur3 * (treps - sdf3)), "annual spread; overnight tenor ignored")],
          [f"Spread = 5.90% − 5.75% = 15 bps.", f"Extra = {crore(sur3)} × 0.0015 ÷ 365 = {R(g3)}."],
          "Extra = Amount × (TREPS − SDF) × 1/365", "Overnight = one day's interest.", kind="case", group="C3-SAHYADRI-TREASURY")
    c3 = sh3 * msf3 / 365
    B.add(ms, "L4", case3 + "\n\nThe overnight cost of the Friday MSF borrowing (for one day) is:",
          R(c3),
          [(R(sh3 * repo3 / 365), "repo rate used instead of MSF"),
           (R(sh3 * sdf3 / 365), "SDF (floor) rate used"),
           (R(sh3 * msf3 / 360), "360-day year used")],
          [f"MSF rate = repo + 25 bps = 6.25% (given).", f"Cost = {crore(sh3)} × 6.25% ÷ 365 = {R(c3)}."],
          "Cost = Amount × MSF × 1/365", "MSF is the ceiling — the penal, last-resort window.", kind="case", group="C3-SAHYADRI-TREASURY")
    st = ["Placing funds under the SDF does not require RBI to give the bank any collateral.",
          "MSF borrowing is at the bank's discretion and may use SLR securities up to the permitted limit.",
          "TREPS is a bilateral OTC repo with no central counterparty."]
    c, w = stmt_opts([True, True, False], ["SDF is uncollateralised", "MSF can dip into SLR within the RBI-set limit", "TREPS is CCP-cleared, with CCIL as tri-party agent"])
    B.add(ms, "L4", case3 + "\n\nWith reference to the instruments used, consider:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["SDF: no collateral.", "MSF: discretionary; can dip into SLR up to the permitted % of NDTL.", "TREPS: CCIL is tri-party agent and CCP."],
          "LAF instruments", "TREPS is anonymous, CCP-cleared.", kind="case", group="C3-SAHYADRI-TREASURY", verify_fact=True, ref="RBI LAF/MSF/SDF framework; CCIL TREPS")

    # =============================== CASE C4: NBFC compliance ===============================
    ta, infra = 1850, 1295
    need = 0.75 * ta - infra
    emi4, days4, rate4 = 48000, 20, 0.02
    pen = emi4 * rate4 * days4 / 30
    rep = dt.date(2026, 3, 3); rel = dt.date(2026, 4, 18); deadline = rep + dt.timedelta(days=30)
    delay = (rel - deadline).days; comp = delay * 5000
    assert delay == 16
    fmt = lambda d: d.strftime("%d %B %Y").lstrip("0")
    case4 = (f"**Case — Kalpavriksh Finance Ltd.** Kalpavriksh is a non-deposit-taking NBFC with total assets of ₹{inr(ta)} crore, of which ₹{inr(infra)} crore are infrastructure loans. "
             f"It is not in the RBI's Upper Layer list. It also runs a retail loan book. One retail borrower missed an EMI of {R(emi4)} and paid {days4} days late; "
             f"the Board-approved policy prescribes penal charges of {pct(rate4,0)} per month on the overdue instalment. Another borrower fully repaid a secured loan on {fmt(rep)}; "
             f"the original property documents were released on {fmt(rel)} (delay attributable to the NBFC).")
    B.add(msb, "L4", case4 + "\n\nUnder Scale-Based Regulation, Kalpavriksh belongs to the:",
          "Middle Layer",
          [("Base Layer", "₹1,000 crore threshold misapplied (assets exceed it)"),
           ("Upper Layer", "size above ₹1,000 crore wrongly treated as automatic UL"),
           ("Top Layer", "Top Layer is ideally empty and populated only on RBI's judgement")],
          [f"Non-deposit NBFC with assets ₹{inr(ta)} crore ≥ ₹1,000 crore → Middle Layer.", "UL membership needs RBI identification (parametric scoring / top 10)."],
          "Non-deposit ≥ ₹1,000 crore → ML", "UL needs identification, not just size.", kind="case", group="C4-KALPAVRIKSH-NBFC", verify_fact=True, ref="RBI SBR framework")
    B.add(mnb, "L4", case4 + "\n\nKalpavriksh wants NBFC-IFC classification. Keeping total assets unchanged, what minimum amount of other assets must be switched into infrastructure loans?",
          f"₹{need:g} crore",
          [(f"₹{need/0.25:g} crore", "treats the new infra loans as additions that also raise total assets"),
           (f"₹{0.80*ta-infra:g} crore", "80% threshold used"),
           ("Nil — it already qualifies", f"current share is {infra/ta*100:.0f}%, below 75%")],
          [f"Current share = {inr(infra)}/{inr(ta)} = {infra/ta*100:.0f}%.", f"Required = 75% × {inr(ta)} = {0.75*ta:g}; gap = {need:g} crore."],
          "Gap = 75% × Total assets − Infra loans", "Hold total assets fixed when reallocating.", kind="case", group="C4-KALPAVRIKSH-NBFC", verify_fact=True, ref="NBFC-IFC criteria")
    B.add(mk, "L4", case4 + "\n\nHow must the late EMI be dealt with under RBI's fair-lending (penal charges) directions?",
          f"Levy {R(pen)} as penal charges, not added to the rate and not capitalised",
          [(f"Levy {R(pen)} as penal interest by adding it to the loan's interest rate", "penal interest via rate add-on is prohibited since 2024"),
           (f"Capitalise {R(pen)} into the principal and charge interest on it thereafter", "compounding of penal charges is prohibited"),
           (f"Levy {R(emi4*rate4)} as penal charges for the full month, not added to the rate", "charge not pro-rated for the actual days of delay")],
          [f"Penal charge = {inr(emi4)} × 2% × {days4}/30 = {R(pen)}.", "Must be 'penal charges', not penal interest; no capitalisation or further interest on them."],
          "Penal charge = Overdue × Rate × Days/30", "Penal interest and compounding are both out.", kind="case", group="C4-KALPAVRIKSH-NBFC",
          verify_fact=True, ref="RBI circular on Fair Lending Practice — Penal Charges in Loan Accounts (Aug 2023, effective 1 Jan 2024)")
    B.add(mk, "L4", case4 + "\n\nWhat compensation does the NBFC owe the second borrower for the late release of documents?",
          R(comp),
          [(R((rel - rep).days * 5000), "delay counted from repayment date instead of after the 30-day window"),
           (R(delay * 1000), "₹1,000 per day used"),
           (R((delay + 1) * 5000), "inclusive day count adds an extra day")],
          [f"Documents due within 30 days of repayment → by {fmt(deadline)}.", f"Released {fmt(rel)} → delay {delay} days.", f"Compensation = {delay} × ₹5,000 = {R(comp)}."],
          "Compensation = ₹5,000 × days of delay beyond 30 days", "The 30-day window is not compensable.", kind="case", group="C4-KALPAVRIKSH-NBFC",
          verify_fact=True, ref="RBI circular on Responsible Lending Conduct — release of property documents (Sep 2023, effective 1 Dec 2023)")
