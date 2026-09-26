"""FIN-A part 3: capital-market institutions, regulation, macro-fiscal. Case sets C6 (IPO) and C7 (Union budget)."""
import math
from reglib import inr, R, pct, lakh, crore
from fina_util import table, f2

AIF = "fin-aif-categories-and-angel-funds-0084a9f3"
AA = "fin-account-aggregator-framework-54211b31"
ALT = "fin-alternate-sources-of-finance-1d5feb9c"
ANC = "fin-anchor-investors-and-lock-in-9c556998"
BOT = "fin-bot-variants-and-risk-allocation-0ed2c252"
CBDC = "fin-cbdc-stablecoins-and-crypto-policy-9476ef9a"
CPI = "fin-cpi-components-and-trends-4bb0a8ea"
CIR = "fin-circuit-breakers-and-trading-halts-3d39e4dd"
CLR = "fin-clearing-corporations-and-settlement-469ecd05"
CRA = "fin-credit-rating-agencies-and-sovereign-ratings-a4f09f50"
DACT = "fin-depositories-act-1996-10c812ac"
DMAT = "fin-depositories-and-dematerialisation-0a3e7f01"
DPI = "fin-digital-public-infrastructure-and-india-stack-28615c13"
DIL = "fin-dilution-and-further-issue-of-capital-41a71d2a"
FDI = "fin-fdi-caps-and-sectoral-limits-402d73ba"
FEMA = "fin-fema-framework-and-master-directions-abd75bc6"
FRBM = "fin-frbm-act-targets-and-fiscal-rules-dfa55a55"
FSDC = "fin-fsdc-and-regulatory-coordination-4c2d899f"
FC = "fin-finance-commission-and-devolution-criteria-911108f5"
FII = "fin-financial-inclusion-index-and-schemes-f4ae2435"
FIS = "fin-fiscal-policy-instruments-and-stance-20eb50f6"
FFS = "fin-fund-of-funds-for-startups-e2f3469f"

ICDR = "SEBI (Issue of Capital and Disclosure Requirements) Regulations, 2018 — anchor investor provisions (Schedule XIII) and lock-in (Regs 16–17)"


def add_all(B):
    A = B.add

    # ================= AIF =================
    A(AIF, "L1",
      "Under the SEBI (Alternative Investment Funds) Regulations, 2012, an Angel Fund is a sub-category of:",
      "Category I AIF — Venture Capital Fund",
      [("Category II AIF — Private Equity Fund", "Cat II covers PE/debt funds without specific incentives"),
       ("Category III AIF — Hedge Fund", "Cat III funds use complex/leveraged strategies"),
       ("A separate category outside the AIF Regulations, registered as a venture capital undertaking", "angel funds are registered under the AIF Regulations")],
      ["Category I includes venture capital funds (incl. angel funds), SME funds, social venture funds and infrastructure funds.",
       "Angel funds are a sub-category of VCF within Category I."], "—",
      "Cat I = sectors the Government considers socially/economically desirable.", kind="conceptual",
      verify_fact=True, ref="SEBI (AIF) Regulations 2012, Reg 3(4)(a) and Chapter III-A (Angel Funds)")

    A(AIF, "L3",
      "Consider the following statements regarding AIFs:\n\n"
      "1. Category I and II AIFs may not borrow except to meet temporary funding requirements, within limits specified by SEBI.\n"
      "2. Category III AIFs may employ leverage, subject to SEBI's exposure limits.\n"
      "3. The minimum investment by an investor in an AIF (other than accredited investors and employees/directors of the manager) is ₹1 crore.\n"
      "4. Category III AIFs must be close-ended with a minimum tenure of three years.\n\nWhich of the statements given above are correct?",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "Cat III AIFs may be open-ended; the 3-year close-ended rule is for Cat I and II"),
       ("1 and 2 only", "statement 3 correctly states the ₹1 crore minimum"),
       ("2, 3 and 4 only", "statement 4 is wrong; statement 1 is correct")],
      ["Cat I/II: no leverage except temporary funding (short-term borrowing within limits) — correct.",
       "Cat III: leverage permitted within limits — correct.",
       "Minimum ticket ₹1 crore (₹25 lakh for employees/directors; exemption for accredited investors in LVFs) — correct.",
       "Cat III may be open- or close-ended — statement 4 wrong."], "—",
      "Tenure rule (≥3 years close-ended) applies to Cat I and II.", kind="statement", verify_fact=True,
      ref="SEBI (AIF) Regulations 2012, Regs 10, 13, 16–18")

    # ================= ACCOUNT AGGREGATOR =================
    A(AA, "L2",
      "**Assertion (A):** An Account Aggregator cannot read, store or use for its own purposes the financial information it transmits.\n\n"
      "**Reason (R):** Under RBI's NBFC-AA directions, the Account Aggregator acts only as a consent-based conduit between Financial Information Providers and Financial Information Users, with data flowing encrypted.\n\nChoose the correct option:",
      "Both A and R are true, and R correctly explains A",
      [("Both A and R are true, but R does not explain A", "R is the design basis for the 'data-blind' feature in A"),
       ("Only A is true; R is a false statement of fact", "R correctly describes the AA's role"),
       ("Only R is true; A is a false statement of fact", "AAs are prohibited from storing or using customer data")],
      ["AA = consent manager; data is end-to-end encrypted; AA is 'data blind'.",
       "It may not undertake any other business or use the data."], "—",
      "The AA moves data; it does not hold or analyse it.", kind="assertion-reason", verify_fact=True,
      ref="RBI Master Direction — NBFC-Account Aggregator (Reserve Bank) Directions, 2016")

    A(AA, "L3",
      "Consider the following statements about the Account Aggregator (AA) ecosystem:\n\n"
      "1. An AA must be a company registered with the RBI as an NBFC-AA.\n"
      "2. Entities regulated by SEBI, IRDAI and PFRDA can participate as Financial Information Providers or Users.\n"
      "3. A customer's consent artefact specifies the purpose, the data sought, the duration and the frequency of access, and can be revoked.\n"
      "4. An AA may offer credit to customers on the basis of the data it aggregates.\n\nWhich of the statements given above are correct?",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "an AA cannot use the data or undertake lending"),
       ("1 and 3 only", "financial-sector regulators other than RBI have notified their entities as FIPs/FIUs"),
       ("2, 3 and 4 only", "statement 1 is correct; statement 4 is wrong")],
      ["NBFC-AA registration with RBI — correct.",
       "SEBI, IRDAI, PFRDA entities participate — correct.",
       "Consent artefact elements and revocability — correct.",
       "AA cannot lend or use data — statement 4 wrong."], "—",
      "AA = conduit; FIU = lender/user.", kind="statement", verify_fact=True,
      ref="RBI NBFC-AA Directions 2016; SEBI/IRDAI/PFRDA circulars on AA participation")

    # ================= ALTERNATE SOURCES =================
    A(ALT, "L2",
      "Match the financing source (List I) with its key feature (List II):\n\n"
      + table(["List I", "List II"],
              [["P. Venture debt", "1. Asset sold to a financier and taken back on lease, releasing locked-up capital"],
               ["Q. Sale and leaseback", "2. Receivables pooled and sold to an SPV that issues pass-through certificates"],
               ["R. Securitisation", "3. Term loan to a VC-backed startup, often with warrants, complementing equity"],
               ["S. Invoice discounting on TReDS", "4. MSME receivables from large buyers auctioned to financiers on an electronic platform"]], ["---", "---"]) + "\n\nCodes:",
      "P-3, Q-1, R-2, S-4",
      [("P-1, Q-3, R-2, S-4", "venture debt and sale-leaseback swapped"),
       ("P-3, Q-1, R-4, S-2", "securitisation and TReDS swapped"),
       ("P-3, Q-2, R-1, S-4", "sale-leaseback and securitisation swapped")],
      ["Venture debt: debt for equity-backed startups with warrants.", "Sale & leaseback: sell asset, lease back.",
       "Securitisation: SPV issues PTCs against pooled receivables.", "TReDS: MSME invoice discounting platform (RBI-authorised)."],
      "—", "TReDS is buyer-accepted receivables finance for MSMEs.", kind="match")

    disc, dd, net = 0.02, 10, 45
    cost = disc / (1 - disc) * 365 / (net - dd)
    A(ALT, "L3",
      f"A supplier offers credit terms of '{disc*100:.0f}/{dd}, net {net}'. A buyer that forgoes the cash discount and pays on day {net} is effectively using trade credit as a source of finance. Its approximate annualised cost (365-day year, simple) is:",
      pct(cost),
      [(pct(disc * 365 / (net - dd)), "discount divided by invoice value instead of the net amount (1 − d)"),
       (pct(disc / (1 - disc) * 365 / net), "full credit period (45 days) used instead of the extra 35 days"),
       (pct((1 + disc / (1 - disc)) ** (365 / (net - dd)) - 1), "compound (effective) rate reported instead of the simple approximation asked")],
      [f"Cost per period = 2 ÷ 98 = {disc/(1-disc)*100:.4f}%",
       f"Extra days of credit = 45 − 10 = 35", f"Annualised = {disc/(1-disc)*100:.4f}% × 365/35 = {pct(cost)}"],
      "Cost = d/(1 − d) × 365/(N − D)", "Trade credit that looks 'free' is usually expensive once the discount is forgone.")

    # ================= ANCHOR INVESTORS =================
    A(ANC, "L2",
      "In a main-board book-built IPO, shares allotted to anchor investors are subject to which lock-in?",
      "50% of shares for 30 days and 50% for 90 days, from the date of allotment",
      [("100% of the anchor shares for 30 days, from the date of allotment", "pre-2022 anchor lock-in"),
       ("100% of the anchor shares for 90 days, from the date of listing", "lock-in runs from allotment and is staggered"),
       ("50% of shares for 90 days and 50% for 180 days, from the date of allotment", "periods overstated; 6-month lock-in applies to pre-issue non-promoter shareholders")],
      ["SEBI amended ICDR (effective April 2022) to add a 90-day lock-in on 50% of anchor shares.",
       "The other 50% remains locked for 30 days."], "—",
      "Staggered lock-in: 30 days / 90 days.", verify_fact=True, ref=ICDR)

    A(ANC, "L3",
      "Consider the following statements about anchor investors in a main-board IPO:\n\n"
      "1. An anchor investor must apply for at least ₹10 crore.\n"
      "2. Anchor bidding takes place one working day before the issue opens.\n"
      "3. If the final issue price is lower than the anchor allocation price, the difference is refunded to anchor investors.\n"
      "4. Anchor investors must be qualified institutional buyers.\n\nWhich of the statements given above are correct?",
      "1, 2 and 4 only",
      [("1, 2, 3 and 4", "no refund if the issue price is lower — anchors are allotted at the anchor price"),
       ("1 and 2 only", "anchor investors are QIBs — statement 4 is correct"),
       ("2, 3 and 4 only", "statement 1 is correct; statement 3 is wrong")],
      ["Minimum application ₹10 crore — correct.", "Anchor bid/allocation one working day before opening — correct.",
       "If issue price < anchor price: no refund; if higher: anchors pay the difference — statement 3 wrong.",
       "Anchors are QIBs — correct."], "—",
      "The price adjustment works only one way (against the anchor).", kind="statement", verify_fact=True, ref=ICDR)

    # ================= BOT =================
    A(BOT, "L1",
      "Under the Hybrid Annuity Model (HAM) used for national highway projects, which of the following is correct?",
      "Authority pays 40% of bid project cost in construction; developer funds the rest, recovered via annuities; traffic risk stays with authority",
      [("The developer bears full traffic risk and collects toll from road users over the whole concession period to recover its investment", "describes BOT-toll"),
       ("The authority funds 100% of construction in milestone instalments, and the contractor has no financing or traffic-risk role at all", "describes EPC"),
       ("The developer pays an upfront lump sum to the authority for the right to collect tolls on an already built and operational highway", "describes TOT")],
      ["HAM (2016): 40% construction support from the authority; 60% arranged by developer (equity + debt).",
       "Developer receives semi-annual annuities with interest; toll collected by the authority."], "—",
      "HAM mixes EPC (authority funding) and annuity-BOT features.", kind="conceptual", verify_fact=True,
      ref="NHAI/MoRTH Hybrid Annuity Model framework (2016)")

    A(BOT, "L2",
      "Match the PPP/contract model (List I) with the party bearing TRAFFIC (demand) risk (List II):\n\n"
      + table(["List I", "List II"],
              [["P. BOT (Toll)", "1. Private developer"],
               ["Q. BOT (Annuity)", "2. Public authority"],
               ["R. EPC", "3. Private developer who paid an upfront concession fee"],
               ["S. TOT (Toll-Operate-Transfer)", ""]], ["---", "---"]) + "\n\nCodes:",
      "P-1, Q-2, R-2, S-3",
      [("P-1, Q-1, R-2, S-3", "annuity BOT wrongly assigned traffic risk to developer"),
       ("P-2, Q-2, R-1, S-3", "BOT-toll and EPC risk assignment reversed"),
       ("P-1, Q-2, R-1, S-2", "EPC contractor and TOT concessionaire risk reversed")],
      ["BOT-toll: developer collects toll ⇒ bears traffic risk.", "BOT-annuity and EPC: authority bears traffic risk.",
       "TOT: concessionaire pays upfront for toll rights ⇒ bears traffic risk."], "—",
      "Whoever keeps the toll bears traffic risk.", kind="match")

    bpc, cs, de = 1200e7, 0.40, (70, 30)
    dev = bpc * (1 - cs)
    eq = dev * de[1] / 100
    A(BOT, "L3",
      f"A HAM highway project has a bid project cost of {crore(bpc,0)}. The authority provides {pct(cs,0)} of the cost as construction support. The developer funds its share with debt and equity in the ratio {de[0]}:{de[1]}. The developer's equity requirement is:",
      crore(eq, 0),
      [(crore(bpc * de[1] / 100, 0), "debt:equity applied to the full bid project cost"),
       (crore(bpc * cs * de[1] / 100, 0), "developer's share taken as 40% instead of 60%"),
       (crore(dev * de[1] / de[0], 0), "30/70 ratio (equity/debt) applied as a share of funding")],
      [f"Developer's share = 60% × {crore(bpc,0)} = {crore(dev,0)}", f"Equity = 30% × {crore(dev,0)} = {crore(eq,0)}"],
      "Equity = BPC × (1 − construction support) × Equity share", "Apply the financing mix only to the developer-funded part.",
      verify_fact=True, ref="HAM 40:60 funding structure (MoRTH/NHAI)")

    # ================= CBDC =================
    A(CBDC, "L1",
      "The RBI's pilots of the Central Bank Digital Currency (e₹) began in:",
      "November 2022 for wholesale (e₹-W) and December 2022 for retail (e₹-R)",
      [("December 2022 for wholesale (e₹-W) and November 2022 for retail (e₹-R)", "sequence reversed"),
       ("April 2021 for both wholesale and retail segments simultaneously", "predates the Finance Act 2022 enabling amendment"),
       ("November 2023 for retail (e₹-R) only; wholesale not yet piloted", "wholesale pilot came first, in 2022")],
      ["e₹-W pilot: 1 November 2022 (settlement of secondary G-sec trades).", "e₹-R pilot: 1 December 2022."], "—",
      "Wholesale first, retail a month later.", verify_fact=True, ref="RBI press releases, Oct–Nov 2022; RBI Concept Note on CBDC (Oct 2022)")

    A(CBDC, "L3",
      "Consider the following statements:\n\n"
      "1. The Finance Act, 2022 amended the RBI Act, 1934 to include a digital form of bank notes.\n"
      "2. Retail e₹ earns interest for holders in the same manner as a savings deposit.\n"
      "3. The e₹ is a direct liability of the Reserve Bank of India.\n"
      "4. Virtual digital asset service providers are covered as 'reporting entities' under the Prevention of Money-laundering Act, 2002.\n\nWhich of the statements given above are correct?",
      "1, 3 and 4 only",
      [("1, 2, 3 and 4", "the e₹ is non-interest-bearing, like cash"),
       ("1 and 3 only", "PMLA coverage of VDA service providers was notified in March 2023"),
       ("2, 3 and 4 only", "statement 2 is wrong; statement 1 is correct")],
      ["1: Finance Act 2022 amended RBI Act (s.22 etc.) to cover digital currency — correct.",
       "2: e₹ is non-remunerated to avoid disintermediation — wrong.",
       "3: CBDC is RBI's liability, like physical currency — correct.",
       "4: VDA SPs brought under PMLA (March 2023) — correct."], "—",
      "Interest-bearing CBDC would compete with bank deposits.", kind="statement", verify_fact=True,
      ref="Finance Act 2022 (amendments to RBI Act 1934); MoF notification under PMLA, 7 March 2023")

    # ================= CPI =================
    W = {"Food and beverages": 40, "Housing": 12, "Fuel and light": 7, "Clothing and footwear": 7, "Miscellaneous": 34}
    I0 = {"Food and beverages": 190.0, "Housing": 176.0, "Fuel and light": 182.0, "Clothing and footwear": 188.0, "Miscellaneous": 180.0}
    I1 = {"Food and beverages": 205.2, "Housing": 183.0, "Fuel and light": 185.6, "Clothing and footwear": 194.6, "Miscellaneous": 188.1}
    c0 = sum(W[k] * I0[k] for k in W) / 100
    c1 = sum(W[k] * I1[k] for k in W) / 100
    infl = c1 / c0 - 1
    simple = sum((I1[k] / I0[k] - 1) for k in W) / 5
    rows = [[k, str(W[k]), f"{I0[k]:.1f}", f"{I1[k]:.1f}"] for k in W]
    A(CPI, "L2",
      "Group indices and weights of an illustrative consumer price index:\n\n"
      + table(["Group", "Weight", "Index (last year)", "Index (this year)"], rows) +
      "\n\nHeadline year-on-year inflation is closest to:",
      pct(infl),
      [(pct(simple), "simple average of group inflation rates (weights ignored)"),
       (pct(I1["Food and beverages"] / I0["Food and beverages"] - 1), "food inflation reported as headline"),
       (pct(sum(W[k] * (I1[k] / I0[k] - 1) for k in W) / 100 * 0 + (c1 - c0) / 100), "index-point change read as a percentage")],
      [f"Combined index last year = Σ wI/100 = {c0:.2f}", f"This year = {c1:.2f}", f"Inflation = {c1:.2f}/{c0:.2f} − 1 = {pct(infl)}"],
      "CPI = Σ wᵢIᵢ / Σ wᵢ; π = CPI₁/CPI₀ − 1", "Weight group indices, then compute the change.")

    k = "Food and beverages"
    contrib = W[k] * (I1[k] - I0[k]) / 100 / (c1 - c0)
    A(CPI, "L3",
      "Using the same illustrative index:\n\n"
      + table(["Group", "Weight", "Index (last year)", "Index (this year)"], rows) +
      "\n\nThe share of headline inflation contributed by 'Food and beverages' is closest to:",
      pct(contrib, 1),
      [(pct(W[k] / 100, 1), "weight taken as contribution"),
       (pct(W[k] / 100 * (I1[k] / I0[k] - 1) / infl, 1), "weight × group inflation ÷ headline inflation (relative index levels ignored)"),
       (pct((I1[k] / I0[k] - 1) / sum(I1[j] / I0[j] - 1 for j in W), 1), "share in the unweighted sum of group inflation rates")],
      [f"Food: weight × Δindex = 40 × {I1[k]-I0[k]:.1f} / 100 = {W[k]*(I1[k]-I0[k])/100:.3f} points",
       f"Headline change = {c1-c0:.3f} points", f"Contribution = {pct(contrib,1)}"],
      "Contributionᵢ = wᵢ ΔIᵢ ÷ Σ wⱼ ΔIⱼ", "Food's share of inflation can greatly exceed its weight when food prices surge.")

    jan0, feb0, jan1, feb1 = 180.0, 183.6, 190.8, 191.8
    yj, yf = jan1 / jan0 - 1, feb1 / feb0 - 1
    A(CPI, "L3",
      f"An index stood at {jan0} (January last year), {feb0} (February last year), {jan1} (January this year) and {feb1} (February this year). Year-on-year inflation in February this year and the main reason for its change from January are:",
      f"{pct(yf)}; favourable base effect as last February's {pct(feb0/jan0-1)} jump drops out",
      [(f"{pct(yj)}; unchanged, as prices rose again this February", "January's y-o-y rate reported for February"),
       (f"{pct(feb1/jan1-1)}; a sharp slowdown in current month price momentum", "month-on-month change taken as y-o-y inflation"),
       (f"{pct(yf)}; a sharp fall in price levels during February this year", "prices actually rose m-o-m this February")],
      [f"Jan y-o-y = {jan1}/{jan0} − 1 = {pct(yj)}", f"Feb y-o-y = {feb1}/{feb0} − 1 = {pct(yf)}",
       f"This February m-o-m = +{pct(feb1/jan1-1)} (prices rose); last February m-o-m = +{pct(feb0/jan0-1)} (high base)"],
      "π_yoy(t) ≈ Σ last 12 m-o-m changes", "Inflation can fall even as prices keep rising, if the base month was high.")

    # ================= CIRCUIT BREAKERS =================
    A(CIR, "L2",
      "Under SEBI's index-based market-wide circuit breaker, if the benchmark index falls by 10% at 12:15 pm, trading in all equity and equity-derivative segments is halted for:",
      "45 minutes",
      [("15 minutes", "halt applicable if the 10% trigger is hit between 1:00 pm and 2:30 pm"),
       ("1 hour 45 minutes", "halt for a 15% trigger before 1:00 pm"),
       ("The remainder of the day", "applies to a 20% trigger (or 15% after 2:00 pm)")],
      ["10% trigger: before 1 pm → 45 min; 1–2:30 pm → 15 min; after 2:30 pm → no halt.",
       "Trading resumes with a pre-open call auction session."], "—",
      "The halt length depends on the time of the breach.", verify_fact=True,
      ref="SEBI circular on index-based market-wide circuit breakers (2001, as revised 2013)")

    pc = 24380
    lv = {p: round(pc * (1 - p)) for p in (0.10, 0.15, 0.20)}
    A(CIR, "L3",
      f"The benchmark index closed at {inr(pc)} yesterday. Today it falls to {inr(lv[0.10]-40)} at 11:20 am (trading halts, then resumes) and later touches {inr(lv[0.15]-60)} at 1:40 pm. With circuit levels computed on the previous close, the consequence of the 1:40 pm fall is:",
      f"The 15% level ({inr(lv[0.15])}) is breached after 1:00 pm but before 2:00 pm — trading halts for 45 minutes",
      [(f"The 15% level ({inr(lv[0.15])}) is breached before 2:00 pm — trading halts for 1 hour 45 minutes", "1h45m halt applies only to a 15% breach before 1:00 pm"),
       (f"Only the 10% level ({inr(lv[0.10])}) matters as it was already triggered; trading continues", "each successive level triggers its own halt"),
       (f"The 20% level ({inr(round(pc*0.8))}) is breached — trading halts for the rest of the day", "a 20% fall would take the index to the 20% level, not reached")],
      [f"Levels: 10% → {inr(lv[0.10])}; 15% → {inr(lv[0.15])}; 20% → {inr(lv[0.20])}",
       f"{inr(lv[0.15]-60)} is below the 15% level but above the 20% level",
       "15% breach at/after 1:00 pm and before 2:00 pm → 45-minute halt."],
      "Trigger level = Previous close × (1 − x%)", "Match both the depth of fall and the clock time.",
      verify_fact=True, ref="SEBI MWCB framework — halt durations by trigger and time")

    # ================= CLEARING =================
    trades = [("Buy", "Stock P", 12000, 410.0), ("Sell", "Stock P", 9000, 412.5), ("Sell", "Stock Q", 5000, 1250.0), ("Buy", "Stock Q", 2000, 1248.0)]
    funds = sum((-1 if s == "Buy" else 1) * q * p for s, _, q, p in trades)
    gross = sum(q * p for _, _, q, p in trades)
    A(CLR, "L2",
      "A clearing member's trades in the cash segment on one day (all for T+1 settlement) are:\n\n"
      + table(["Side", "Security", "Quantity", "Price (₹)"], [[s, n, inr(q), f"{p:.2f}"] for s, n, q, p in trades]) +
      "\n\nAfter multilateral netting by the clearing corporation, the member's net funds obligation is:",
      f"Net pay-out (receive) of {R(funds)}" if funds > 0 else f"Net pay-in (pay) of {R(-funds)}",
      [(f"Net pay-in (pay) of {R(abs(funds))}" if funds > 0 else f"Net pay-out (receive) of {R(-funds)}", "direction reversed"),
       (f"Gross settlement of {R(gross)}", "gross value of trades — netting ignored"),
       (f"Net pay-out (receive) of {R(abs(12000*410 - 9000*412.5) + 0)}", "netting done only for Stock P, Stock Q ignored")],
      [f"Stock P: pay {inr(12000*410)} − receive {inr(9000*412.5)} = net pay {inr(12000*410-9000*412.5)}",
       f"Stock Q: receive {inr(5000*1250)} − pay {inr(2000*1248)} = net receive {inr(5000*1250-2000*1248)}",
       f"Net funds = {R(abs(funds))} {'receivable' if funds>0 else 'payable'}"],
      "Net funds = Σ sell value − Σ buy value (across securities)", "Novation + netting collapse many obligations into one per member.")

    pos, var, elm, drop = 2e7, 0.125, 0.035, 0.06
    m0 = pos * (var + elm)
    mtm = pos * drop
    tot = m0 * (1 - drop) + mtm  # margins on revalued position + MTM loss
    A(CLR, "L3",
      f"A client buys shares worth {crore(pos,0)}. The clearing corporation's upfront margin comprises VaR margin of {pct(var,1)} and extreme loss margin of {pct(elm,1)} of position value. Before pay-in, the share price falls {pct(drop,0)}; margins are recomputed on the new value and the mark-to-market loss is also collected. Total margin + MTM required at that point is:",
      R(tot),
      [(R(m0), "initial upfront margin only; MTM ignored"),
       (R(m0 + mtm), "margins not revalued on the lower position value"),
       (R(pos * var * (1 - drop) + mtm), "extreme loss margin omitted")],
      [f"Initial margin = {pct(var+elm)} × {crore(pos,0)} = {R(m0)}", f"New value = {R(pos*(1-drop))}; margin = {R(m0*(1-drop))}",
       f"MTM loss = {R(mtm)}; total = {R(tot)}"],
      "Requirement = (VaR + ELM) × Current value + MTM loss", "MTM is collected on top of the VaR/ELM margin.")

    # ================= CRA =================
    A(CRA, "L1",
      "On the long-term rating scales used by S&P/Fitch and Moody's, the LOWEST investment-grade rating is:",
      "BBB− (S&P/Fitch) and Baa3 (Moody's)",
      [("BB+ (S&P/Fitch) and Ba1 (Moody's)", "highest speculative grade"),
       ("A− (S&P/Fitch) and A3 (Moody's)", "upper-medium grade, above the cut-off"),
       ("BBB (S&P/Fitch) and Baa2 (Moody's)", "one notch above the lowest investment grade")],
      ["Investment grade: AAA to BBB− / Aaa to Baa3.", "BB+ / Ba1 and below: speculative ('junk')."], "—",
      "BBB− and Baa3 are the equivalent notches.", kind="conceptual")

    A(CRA, "L3",
      "Consider the following statements:\n\n"
      "1. A credit rating agency registered with SEBI must have a minimum net worth of ₹25 crore.\n"
      "2. A 'D' rating indicates that the instrument is in default or expected to be in default soon.\n"
      "3. A sovereign's local-currency rating is typically equal to or higher than its foreign-currency rating.\n"
      "4. A SEBI-registered CRA may rate securities issued by its promoter if it discloses the relationship.\n\nWhich of the statements given above are correct?",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "rating a promoter's securities is prohibited, not merely disclosed"),
       ("2 and 3 only", "₹25 crore net-worth requirement (2018 amendment) is correct"),
       ("1, 2 and 4 only", "statement 4 is wrong; statement 3 is correct")],
      ["Net worth ₹25 crore (raised from ₹5 crore in 2018) — correct.", "D = default — correct.",
       "Sovereigns can print/borrow in own currency ⇒ LC ≥ FC typically — correct.",
       "CRA Regulations prohibit rating securities of its promoter — statement 4 wrong."], "—",
      "Conflict-of-interest rules bar promoter ratings outright.", kind="statement", verify_fact=True,
      ref="SEBI (Credit Rating Agencies) Regulations 1999 (as amended 2018), Regs 6 and 22")

    # ================= DEPOSITORIES ACT =================
    A(DACT, "L2",
      "Match the section of the Depositories Act, 1996 (List I) with its subject (List II):\n\n"
      + table(["List I", "List II"],
              [["P. Section 9", "1. Depository deemed registered owner; beneficial owner entitled to all rights and benefits"],
               ["Q. Section 10", "2. Securities in depositories to be in fungible form"],
               ["R. Section 14", "3. Depository to indemnify beneficial owner for loss caused by negligence of the depository or participant"],
               ["S. Section 16", "4. Option to opt out of a depository"]], ["---", "---"]) + "\n\nCodes:",
      "P-2, Q-1, R-4, S-3",
      [("P-1, Q-2, R-4, S-3", "sections 9 and 10 swapped"),
       ("P-2, Q-1, R-3, S-4", "sections 14 and 16 swapped"),
       ("P-2, Q-4, R-1, S-3", "section 10 confused with opting out")],
      ["s.9 fungibility; s.10 rights of depositories and beneficial owners; s.14 opting out; s.16 indemnity."], "—",
      "Legal ownership (depository) vs beneficial ownership (investor) — s.10.", kind="match", verify_fact=True,
      ref="Depositories Act 1996, ss.9, 10, 14, 16")

    A(DACT, "L3",
      "Consider the following statements under the Depositories Act, 1996:\n\n"
      "1. A depository is deemed to be the registered owner for effecting transfer of ownership, but has no voting rights in respect of securities held by it.\n"
      "2. The beneficial owner is entitled to all rights and liabilities in respect of securities held by a depository.\n"
      "3. A depository must obtain a certificate of registration from the Reserve Bank of India before commencing business.\n"
      "4. Securities held in a depository are not identified by distinctive numbers.\n\nWhich of the statements given above are correct?",
      "1, 2 and 4 only",
      [("1, 2, 3 and 4", "registration/certificate of commencement is from SEBI, not RBI"),
       ("1 and 2 only", "fungibility means no distinctive numbers — statement 4 is correct"),
       ("2, 3 and 4 only", "statement 3 is wrong; statement 1 is correct")],
      ["s.10(1)–(2): depository is registered owner for transfer; no voting rights — correct.", "s.10(3): beneficial owner has all rights — correct.",
       "Registration and certificate of commencement: SEBI — statement 3 wrong.", "s.9: fungible, no distinctive numbers — correct."], "—",
      "SEBI, not RBI, regulates depositories.", kind="statement", verify_fact=True, ref="Depositories Act 1996, ss.3, 9, 10")

    # ================= DEMAT =================
    A(DMAT, "L2",
      "**Assertion (A):** Shareholders of a listed company holding physical share certificates cannot transfer them to a buyer in physical form, though they can still dematerialise them.\n\n"
      "**Reason (R):** SEBI amended the Listing Regulations so that, from 1 April 2019, requests for transfer of securities of listed companies are processed only in dematerialised form (extended to transmission and transposition from January 2022).\n\nChoose the correct option:",
      "Both A and R are true, and R correctly explains A",
      [("Both A and R are true, but R does not explain A", "R is the rule that produces A"),
       ("Only A is true; R is a false statement of fact", "R correctly states the SEBI amendment"),
       ("Only R is true; A is a false statement of fact", "A follows from R; demat of physical shares remains allowed")],
      ["Reg 40(1) of LODR (amended 2018, effective 1 April 2019): transfers only in demat.",
       "Proviso substituted by LODR (Amendment) Regulations, 24 January 2022: transmission and transposition also only in demat.",
       "Holders of physical certificates may still dematerialise them."], "—",
      "Holding in physical form is not banned — transfer is.", kind="assertion-reason", verify_fact=True,
      ref="SEBI (LODR) Regulations 2015, Reg 40(1) (as amended June 2018; proviso substituted by LODR (Amendment) Regulations, 24 January 2022)")

    # ================= DPI =================
    A(DPI, "L2",
      "Match the India Stack component (List I) with its layer/function (List II):\n\n"
      + table(["List I", "List II"],
              [["P. Aadhaar e-KYC", "1. Consent-based sharing of financial data"],
               ["Q. UPI", "2. Presence-less identity verification"],
               ["R. DigiLocker", "3. Interoperable real-time payments"],
               ["S. Account Aggregator", "4. Issuer-verified digital documents"]], ["---", "---"]) + "\n\nCodes:",
      "P-2, Q-3, R-4, S-1",
      [("P-4, Q-3, R-2, S-1", "Aadhaar e-KYC and DigiLocker swapped"),
       ("P-2, Q-1, R-4, S-3", "UPI and AA swapped"),
       ("P-2, Q-3, R-1, S-4", "DigiLocker and AA swapped")],
      ["Identity layer: Aadhaar/e-KYC; payments layer: UPI; data layer: DigiLocker, AA (DEPA)."], "—",
      "India Stack = identity + payments + data layers.", kind="match")

    # ================= DILUTION =================
    cum, n_old, n_new, sub = 450, 7, 2, 330
    terp = (n_old * cum + n_new * sub) / (n_old + n_new)
    A(DIL, "L3",
      f"A company announces a rights issue of {n_new} shares for every {n_old} held at ₹{sub}. The cum-rights market price is ₹{cum}. The theoretical ex-rights price (TERP) and the value of one rights entitlement (right to buy one new share) are:",
      f"TERP ₹{terp:.2f}; value of a rights entitlement ₹{terp-sub:.2f}",
      [(f"TERP ₹{terp:.2f}; value of a rights entitlement ₹{cum-terp:.2f}", "value per existing share given instead of per rights entitlement"),
       (f"TERP ₹{(n_old*cum+n_new*sub)/n_old:.2f}; value of a rights entitlement ₹{(n_old*cum+n_new*sub)/n_old-sub:.2f}", "divided by old shares only"),
       (f"TERP ₹{(cum+sub)/2:.2f}; value of a rights entitlement ₹{(cum+sub)/2-sub:.2f}", "simple average of market and subscription price")],
      [f"TERP = (7 × {cum} + 2 × {sub}) ÷ 9 = ₹{terp:.2f}", f"Value of entitlement = {terp:.2f} − {sub} = ₹{terp-sub:.2f}",
       f"Value per existing share = {cum} − {terp:.2f} = ₹{cum-terp:.2f} (= {terp-sub:.2f} × 2/7)"],
      "TERP = (N·P_cum + n·S)/(N + n); RE value = TERP − S", "Per entitlement vs per existing share differ by the ratio n/N.")

    hold = 1400
    ent = hold * n_new // n_old
    reval = terp - sub
    x = ent * reval / (sub + reval)
    xs = math.floor(x)
    A(DIL, "L3",
      f"For the same rights issue (TERP ₹{terp:.2f}, subscription ₹{sub}), an investor holding {inr(hold)} shares wants neither to invest new cash nor to let her rights lapse. She sells just enough entitlements (at their theoretical value) to fund subscription of the rest. The maximum number of new shares she can take up is:",
      f"{xs} shares",
      [(f"{ent//2} shares", "sells half the entitlements (value ignored)"),
       (f"{math.floor(ent*(cum-terp)/sub)} shares", "entitlements valued at value per existing share"),
       (f"{math.floor(ent*reval/sub)} shares", "sale proceeds of ALL entitlements divided by subscription price (double counts)")],
      [f"Entitlements = 1,400 × 2/7 = {ent}", f"Sell (E − x), subscribe x: x × {sub} = ({ent} − x) × {reval:.2f}",
       f"x = {ent} × {reval:.2f} ÷ ({sub} + {reval:.2f}) = {x:.2f} → {xs} shares"],
      "x = E × V_RE ÷ (S + V_RE)", "Entitlements sold are not available for subscription.")

    ni, sh, opt, ex, avg = 120e7, 10e7, 50e5, 300, 450
    inc = opt * (1 - ex / avg)
    deps = ni / (sh + inc)
    A(DIL, "L3",
      f"A company's profit attributable to equity holders is {crore(ni,0)} with {crore(sh,0).replace('₹','')} (i.e., 10 crore) weighted average shares. There are {inr(opt)} outstanding employee stock options, exercisable at ₹{ex}, and the average market price during the year was ₹{avg}. Under the treasury stock method (Ind AS 33), diluted EPS is:",
      f"₹{deps:.2f}",
      [(f"₹{ni/(sh+opt):.2f}", "all options added as shares without treasury-stock adjustment"),
       (f"₹{ni/sh:.2f}", "basic EPS; options ignored"),
       (f"₹{ni/(sh+opt*ex/avg):.2f}", "shares 'bought back' added instead of the net incremental shares")],
      [f"Incremental shares = {inr(opt)} × (1 − {ex}/{avg}) = {inr(inc)}", f"Diluted EPS = {crore(ni,0)} ÷ {inr(sh+inc)} = ₹{deps:.2f}"],
      "Incremental shares = Options × (1 − Exercise price ÷ Average market price)", "Only the 'free' shares dilute.")
    B.Q[-1]["stem"] = B.Q[-1]["stem"].replace(f"with {crore(sh,0).replace('₹','')} (i.e., 10 crore) weighted", "with 10 crore weighted")

    # ================= FDI =================
    A(FDI, "L2",
      "Match the sector (List I) with the FDI limit and route (List II) under the consolidated FDI policy:\n\n"
      + table(["List I", "List II"],
              [["P. Private sector banking", "1. 20% — Government route"],
               ["Q. Public sector banking", "2. 74% — up to 49% automatic, beyond via Government route"],
               ["R. Multi-brand retail trading", "3. 74% automatic; beyond 74% Government route"],
               ["S. Defence manufacturing", "4. 51% — Government route"]], ["---", "---"]) + "\n\nCodes:",
      "P-2, Q-1, R-4, S-3",
      [("P-3, Q-1, R-4, S-2", "private banking and defence routes swapped"),
       ("P-2, Q-4, R-1, S-3", "public sector banking and multi-brand retail swapped"),
       ("P-1, Q-2, R-4, S-3", "private and public sector banking swapped")],
      ["Private banks: 74% (49% automatic).", "PSBs: 20% government route.", "Multi-brand retail: 51% government route.",
       "Defence: 74% automatic (2020), beyond via government route."], "—",
      "Banking caps differ sharply between private and public sector banks.", kind="match", verify_fact=True,
      ref="DPIIT Consolidated FDI Policy (as updated); Press Notes on defence (2020)")

    A(FDI, "L3",
      "Consider the following statements on India's FDI policy:\n\n"
      "1. An entity of a country sharing a land border with India can invest only under the Government route.\n"
      "2. FDI is prohibited in lottery business and in gambling and betting.\n"
      "3. FDI up to 100% in telecom services is permitted under the automatic route.\n"
      "4. FDI up to 100% in print media dealing with news and current affairs is permitted under the automatic route.\n\nWhich of the statements given above are correct?",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "news print media is capped at 26% under the Government route"),
       ("1 and 2 only", "telecom was moved to 100% automatic in 2021"),
       ("2, 3 and 4 only", "statement 1 (Press Note 3 of 2020) is correct; statement 4 is wrong")],
      ["Press Note 3 (2020) — land-border countries: Government route — correct.", "Lottery, gambling/betting: prohibited — correct.",
       "Telecom: 100% automatic (Oct 2021) — correct.", "News print media: 26% Government route — statement 4 wrong."], "—",
      "Media caps remain restrictive.", kind="statement", verify_fact=True, ref="DPIIT Consolidated FDI Policy; Press Note 3 (2020); Press Note 4 (2021)")

    # ================= FEMA =================
    A(FEMA, "L1",
      "Under Section 13 of FEMA, 1999, a person contravening its provisions is liable to a penalty of:",
      "Up to thrice the sum involved (or ₹2 lakh if not quantifiable), plus up to ₹5,000 per day if continuing",
      [("Imprisonment of up to seven years in every case, in addition to a monetary fine", "FEMA is civil; imprisonment arises only for non-payment of penalty after notice"),
       ("Up to twice the sum involved, with no additional penalty for continuing contraventions", "multiple and continuing penalty misstated"),
       ("A fixed penalty of ₹10 lakh per contravention, irrespective of the sum involved or its duration", "penalty is linked to the sum involved")],
      ["s.13(1): up to thrice the sum involved (if quantifiable) or up to ₹2 lakh; continuing: up to ₹5,000 per day."], "—",
      "FEMA replaced the criminal approach of FERA with civil penalties.", verify_fact=True, ref="FEMA 1999, s.13")

    A(FEMA, "L3",
      "Consider the following statements:\n\n"
      "1. Current account transactions are freely permitted, subject to reasonable restrictions the Central Government may impose in consultation with the RBI.\n"
      "2. Capital account transactions in debt instruments are regulated by the RBI, while those in non-debt instruments are regulated by the Central Government.\n"
      "3. Under the Liberalised Remittance Scheme, resident individuals may remit up to USD 2,50,000 per financial year for permissible transactions.\n"
      "4. Compounding of contraventions under FEMA is not permitted.\n\nWhich of the statements given above are correct?",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "compounding is available under s.15 FEMA"),
       ("1 and 3 only", "the 2015 amendment to s.6 (effective October 2019) split debt/non-debt powers"),
       ("2, 3 and 4 only", "statement 1 is correct (s.5); statement 4 is wrong")],
      ["s.5 current account — correct.", "s.6 as amended: RBI (debt), Central Govt (non-debt) — correct.",
       "LRS limit USD 2,50,000 per FY — correct.", "s.15 allows compounding — statement 4 wrong."], "—",
      "Non-debt instruments rules are notified by the Central Government (NDI Rules 2019).", kind="statement", verify_fact=True,
      ref="FEMA 1999 ss.5, 6, 15; FEM (Non-debt Instruments) Rules 2019; RBI LRS Master Direction")

    # ================= FRBM =================
    rr, ndcr, rev, cap, intr, gcca, gdp = 30.2, 0.9, 35.6, 10.4, 11.3, 2.9, 330.0
    fd = rev + cap - rr - ndcr
    A(FRBM, "L3",
      "Stylised Union Government accounts (₹ lakh crore): revenue receipts 30.2; non-debt capital receipts 0.9; revenue expenditure 35.6 (of which interest 11.3 and grants for creation of capital assets 2.9); capital expenditure 10.4; nominal GDP 330.0. The fiscal deficit and primary deficit as % of GDP are:",
      f"Fiscal deficit {pct(fd/gdp)}; primary deficit {pct((fd-intr)/gdp)}",
      [(f"Fiscal deficit {pct((rev+cap-rr)/gdp)}; primary deficit {pct((rev+cap-rr-intr)/gdp)}", "non-debt capital receipts not deducted"),
       (f"Fiscal deficit {pct(fd/gdp)}; primary deficit {pct((fd-intr-gcca)/gdp)}", "grants for capital assets also deducted for primary deficit"),
       (f"Fiscal deficit {pct((rev-rr)/gdp)}; primary deficit {pct((rev-rr-intr)/gdp)}", "revenue deficit taken as fiscal deficit")],
      [f"Total expenditure = {rev} + {cap} = {rev+cap:.1f}", f"FD = {rev+cap:.1f} − ({rr} + {ndcr}) = {fd:.1f} → {pct(fd/gdp)}",
       f"PD = FD − interest = {fd-intr:.1f} → {pct((fd-intr)/gdp)}"],
      "FD = Total exp − (Revenue receipts + Non-debt capital receipts); PD = FD − Interest", "Borrowings are the balancing item, not a receipt.")

    d0, i, g, pd = 0.570, 0.075, 0.105, 0.012
    d1 = d0 * (1 + i) / (1 + g) + pd
    A(FRBM, "L3",
      f"A government's debt is {pct(d0,1)} of GDP. The effective interest rate on debt is {pct(i,1)}, nominal GDP growth is {pct(g,1)}, and it runs a primary deficit of {pct(pd,1)} of GDP. Next year's debt-to-GDP ratio is closest to:",
      pct(d1),
      [(pct(d0 * (1 + g) / (1 + i) + pd), "interest and growth factors inverted"),
       (pct(d0 * (1 + i) / (1 + g)), "primary deficit ignored"),
       (pct(d0 + pd), "interest–growth differential ignored")],
      [f"d₁ = {d0} × {1+i:.3f}/{1+g:.3f} + {pd} = {d1:.4f}", "g > i helps reduce the ratio despite the primary deficit."],
      "d₁ = d₀(1 + i)/(1 + g) + pd", "A favourable i − g gap can offset a moderate primary deficit.")

    # ================= FSDC =================
    A(FSDC, "L1",
      "The Financial Stability and Development Council (FSDC) is:",
      "A non-statutory body chaired by the Finance Minister; its sub-committee is chaired by the RBI Governor",
      [("A statutory body under the RBI Act, chaired by the RBI Governor with the FM as a member", "FSDC was set up by executive decision (2010), chaired by the FM"),
       ("A statutory body under the SEBI Act, chaired by the SEBI Chairperson with RBI as a member", "not statutory; not chaired by SEBI"),
       ("A non-statutory body chaired by the Cabinet Secretary, with a sub-committee under the RBI Governor", "chaired by the Finance Minister")],
      ["Set up in December 2010 by government notification.", "Chair: Finance Minister; members include heads of RBI, SEBI, IRDAI, PFRDA, IBBI.",
       "FSDC Sub-Committee chaired by the RBI Governor."], "—",
      "It coordinates; it does not regulate.", verify_fact=True, ref="Government of India resolution constituting FSDC (2010)")

    # ================= FINANCE COMMISSION =================
    crit = {"Income distance": (0.45, 0.092), "Population": (0.15, 0.071), "Area": (0.15, 0.058),
            "Forest and ecology": (0.10, 0.043), "Demographic performance": (0.125, 0.049), "Tax and fiscal effort": (0.025, 0.066)}
    share = sum(w * s for w, s in crit.values())
    A(FC, "L3",
      "A Finance Commission uses the following horizontal-devolution criteria. State X's share in each criterion (computed by the Commission) is given:\n\n"
      + table(["Criterion", "Weight", "State X share"], [[k, pct(w, 1), pct(s, 1)] for k, (w, s) in crit.items()]) +
      "\n\nState X's share in the States' divisible-pool devolution is closest to:",
      pct(share, 3),
      [(pct(sum(s for _, s in crit.values()) / 6, 3), "simple average of criterion shares"),
       (pct(share - 0.025 * 0.066 + 0.25 * 0.066, 3), "tax & fiscal effort weighted at 25% instead of 2.5%"),
       (pct(sum(w * s for k, (w, s) in crit.items() if k != "Income distance") / 0.55, 3), "income distance excluded and weights re-scaled")],
      ["Share = Σ weight × criterion share", " + ".join(f"{w}×{s}" for w, s in crit.values()) + f" = {share:.5f}"],
      "sᵢ = Σₖ wₖ · sᵢₖ", "Weights must be applied; a simple average misrepresents the formula.")

    # ================= FI INDEX =================
    acc, use, qual = 78.0, 55.0, 60.0
    fi = 0.35 * acc + 0.45 * use + 0.20 * qual
    A(FII, "L2",
      f"The RBI's Financial Inclusion Index combines three sub-indices — Access (weight 35%), Usage (45%) and Quality (20%). If the sub-index scores are Access {acc}, Usage {use} and Quality {qual}, the FI-Index is:",
      f"{fi:.2f}",
      [(f"{(acc+use+qual)/3:.2f}", "equal weights"),
       (f"{0.45*acc+0.35*use+0.20*qual:.2f}", "access and usage weights swapped"),
       (f"{0.35*acc+0.20*use+0.45*qual:.2f}", "usage and quality weights swapped")],
      [f"FI = 0.35×{acc} + 0.45×{use} + 0.20×{qual} = {fi:.2f}"],
      "FI-Index = 0.35 A + 0.45 U + 0.20 Q", "Usage carries the highest weight.", verify_fact=True,
      ref="RBI press release on Financial Inclusion Index (August 2021)")

    A(FII, "L3",
      "Consider the following statements:\n\n"
      "1. The RBI's FI-Index ranges from 0 to 100 and is constructed without any base year.\n"
      "2. The FI-Index is published annually, in July, for the financial year ended March.\n"
      "3. Pradhan Mantri Jeevan Jyoti Bima Yojana provides accident insurance cover of ₹2 lakh for an annual premium of ₹20.\n"
      "4. Income-tax payers are not eligible to join the Atal Pension Yojana from 1 October 2022.\n\nWhich of the statements given above are correct?",
      "1, 2 and 4 only",
      [("1, 2, 3 and 4", "₹2 lakh accident cover for ₹20 is PMSBY; PMJJBY is life cover"),
       ("1 and 2 only", "APY exclusion of income-tax payers (from Oct 2022) is correct"),
       ("2, 3 and 4 only", "statement 1 is correct; statement 3 is wrong")],
      ["FI-Index: 0–100, no base year — correct.", "Published annually in July — correct.",
       "PMJJBY = life cover (₹2 lakh, ₹436 p.a.); ₹20 accident cover is PMSBY — statement 3 wrong.",
       "APY: income-tax payers barred from 1 Oct 2022 — correct."], "—",
      "PMJJBY (life) vs PMSBY (accident).", kind="statement", verify_fact=True,
      ref="RBI FI-Index release (2021); MoF notifications on PMJJBY/PMSBY premia (2022) and APY (Aug 2022)")

    # ================= FISCAL POLICY =================
    A(FIS, "L2",
      "**Assertion (A):** Progressive income taxes and unemployment-linked transfers moderate business-cycle fluctuations without any fresh policy decision.\n\n"
      "**Reason (R):** During a downturn, tax collections fall and transfers rise automatically, supporting disposable income.\n\nChoose the correct option:",
      "Both A and R are true, and R correctly explains A",
      [("Both A and R are true, but R does not explain A", "R is the mechanism of automatic stabilisers"),
       ("Only A is true; R is a false statement of fact", "R is correct"),
       ("Only R is true; A is a false statement of fact", "these are automatic (built-in) stabilisers")],
      ["Automatic stabilisers work through the tax-transfer system with no discretionary action.",
       "R describes their counter-cyclical mechanism."], "—",
      "Discretionary vs automatic fiscal policy.", kind="assertion-reason")

    c, t, m, dG = 0.8, 0.25, 0.10, 50000
    k = 1 / (1 - c * (1 - t) + m)
    A(FIS, "L3",
      f"In an open economy the marginal propensity to consume is {c}, the proportional tax rate {t} and the marginal propensity to import {m}. Government raises spending by ₹{inr(dG)} crore. The resulting increase in equilibrium income is:",
      f"₹{inr(dG*k)} crore",
      [(f"₹{inr(dG/(1-c))} crore", "closed-economy multiplier with no taxes (1/(1 − c))"),
       (f"₹{inr(dG/(1-c*(1-t)))} crore", "imports ignored"),
       (f"₹{inr(dG/(1-c+m))} crore", "taxes ignored")],
      [f"k = 1 ÷ [1 − 0.8(1 − 0.25) + 0.10] = 1 ÷ {1-c*(1-t)+m:.2f} = {k:.2f}", f"ΔY = {k:.2f} × {inr(dG)} = ₹{inr(dG*k)} crore"],
      "k = 1 ÷ [1 − c(1 − t) + m]", "Taxes and imports are leakages that shrink the multiplier.")

    # ================= FFS =================
    A(FFS, "L1",
      "Consider the following statements about the Fund of Funds for Startups (FFS):\n\n"
      "1. It is operated by SIDBI.\n"
      "2. It invests directly in DPIIT-recognised startups.\n"
      "3. It contributes to SEBI-registered Alternative Investment Funds, which in turn invest in startups.\n\nWhich of the statements given above is/are correct?",
      "1 and 3 only",
      [("1, 2 and 3", "FFS does not invest directly in startups"),
       ("1 and 2 only", "the fund-of-funds route is via AIFs (daughter funds)"),
       ("3 only", "SIDBI manages the FFS — statement 1 is correct")],
      ["FFS (₹10,000 crore, approved 2016) is managed by SIDBI.", "It commits capital to SEBI-registered AIFs, which invest in startups."], "—",
      "A fund of funds invests in funds, not companies.", kind="statement", verify_fact=True,
      ref="DPIIT Startup India — Fund of Funds for Startups scheme (2016)")

    # ================= CASE C6: IPO =================
    G = "FINA-CASE-IPO"
    pre, prom, fresh, ofs, ip, ap_, pat = 18e7, 15e7, 4e7, 2e7, 326, 320, 540e7
    offer = fresh + ofs
    stim = ("**Case — Narmada Green Energy Ltd (fictional)** — main-board book-built IPO; the issuer satisfies the profitability track-record route (Reg 6(1), ICDR).\n\n"
            + table(["Item", "Data"],
                    [["Pre-issue equity shares", "18 crore (promoters 15 crore)"],
                     ["Fresh issue", "4 crore shares"], ["Offer for sale by promoters", "2 crore shares"],
                     ["Price band / final issue price", f"₹310–{ip} / ₹{ip}"], ["Anchor allocation price", f"₹{ap_}"],
                     ["Profit after tax (latest year)", crore(pat, 0)], ["Employee / shareholder reservation", "Nil"]], ["---", "---"]) +
            "\n\nAssume allocation norms: QIBs not more than 50% of the net offer; anchor investors up to 60% of the QIB portion, one-third of the anchor portion reserved for domestic mutual funds.")
    qib = 0.5 * offer
    anc = 0.6 * qib
    lipf = anc * (0.40 - 1 / 3)
    assert round(anc / 3 / 1e7, 2) == 0.60 and round(lipf / 1e7, 2) == 0.12
    stim150 = stim.replace("one-third of the anchor portion reserved for domestic mutual funds.",
                           "40% of the anchor portion reserved — one-third of the anchor portion (33.33%) for domestic mutual funds and the remaining 6.67% of the anchor portion for life insurers and pension funds (any unsubscribed part of the latter available to mutual funds).")
    assert stim150 != stim
    A(ANC, "L4", stim150 + "\n\nThe maximum number of shares that can be allocated to anchor investors, and the minimum reserved for domestic mutual funds within it, are:",
      f"{anc/1e7:.2f} crore shares; {anc/3/1e7:.2f} crore shares",
      [(f"{0.6*offer/1e7:.2f} crore shares; {0.6*offer/3/1e7:.2f} crore shares", "60% applied to the whole offer instead of the QIB portion"),
       (f"{0.6*0.5*fresh/1e7:.2f} crore shares; {0.6*0.5*fresh/3/1e7:.2f} crore shares", "offer for sale excluded from the offer size"),
       (f"{anc/1e7:.2f} crore shares; {anc/2/1e7:.2f} crore shares", "half (not one-third) reserved for mutual funds")],
      [f"Offer = 4 + 2 = {offer/1e7:.0f} crore shares", f"QIB portion ≤ 50% = {qib/1e7:.1f} crore", f"Anchor ≤ 60% × {qib/1e7:.1f} = {anc/1e7:.2f} crore; MF ≥ one-third = {anc/3/1e7:.2f} crore",
       f"Total reservation 40% of anchor = {0.4*anc/1e7:.2f} crore, of which life insurers/pension funds {lipf/1e7:.2f} crore"],
      "Anchor ≤ 0.6 × QIB portion; reservation = 40% of anchor (⅓ MFs + balance LI/PF)", "The offer includes both fresh issue and OFS.", group=G,
      verify_fact=True, ref=ICDR + "; Reg 32(1); ICDR (Third Amendment) Regulations 2025 — 40% anchor reservation (⅓ MFs, balance life insurers & pension funds)")

    extra = anc * (ip - ap_)
    A(ANC, "L4", stim + "\n\nAnchors are allotted the maximum permissible shares. Which statement about their payment and lock-in is correct?",
      f"They pay an additional {crore(extra)}; 50% locked for 30 days and 50% for 90 days from allotment",
      [(f"They receive a refund of {crore(extra)}; all their shares are locked in for 30 days from allotment", "direction of price adjustment reversed and old lock-in"),
       (f"No adjustment — anchors are allotted at the anchor price; 50% locked for 30 days and 50% for 90 days", "anchors must pay the difference when the issue price is higher"),
       (f"They pay an additional {crore(extra)}; all shares locked in for 90 days from listing", "lock-in is staggered and runs from allotment")],
      [f"Issue price ₹{ip} > anchor price ₹{ap_} ⇒ anchors pay ₹{ip-ap_} × {anc/1e7:.2f} crore = {crore(extra)}",
       "Lock-in: 50% for 30 days, 50% for 90 days from allotment."],
      "Top-up = (Issue price − Anchor price) × Anchor shares", "A lower issue price gives no refund; a higher one requires a top-up.", group=G,
      verify_fact=True, ref=ICDR)

    post = pre + fresh
    ph = (prom - ofs) / post
    A(DIL, "L4", stim + "\n\nThe promoters' post-issue shareholding is closest to:",
      pct(ph),
      [(pct(prom / post), "offer for sale ignored"),
       (pct((prom - ofs) / pre), "fresh issue ignored in post-issue capital"),
       (pct((prom - ofs) / (pre + fresh + ofs)), "OFS shares treated as newly issued")],
      [f"Post-issue shares = 18 + 4 = {post/1e7:.0f} crore (OFS does not add shares)", f"Promoters = 15 − 2 = 13 crore", f"Holding = 13 ÷ 22 = {pct(ph)}"],
      "Post-issue holding = (Pre-issue holding − OFS) ÷ (Pre-issue shares + Fresh issue)", "OFS transfers existing shares; only the fresh issue dilutes.", group=G)

    pe_post = ip / (pat / post)
    A(DIL, "L4", stim + "\n\nOn the latest profit, the P/E multiple at the issue price on a fully diluted post-issue basis is closest to:",
      f"{pe_post:.2f}×",
      [(f"{ip/(pat/pre):.2f}×", "pre-issue share count used"),
       (f"{ip/(pat/(post+ofs)):.2f}×", "OFS shares added to post-issue capital"),
       (f"{ip/(pat/(pre+ofs)):.2f}×", "OFS shares added instead of the fresh issue")],
      [f"Post-issue EPS = {crore(pat,0)} ÷ 22 crore = ₹{pat/post:.2f}", f"P/E = {ip} ÷ {pat/post:.2f} = {pe_post:.2f}×"],
      "Post-issue P/E = Issue price ÷ (PAT ÷ Post-issue shares)", "Investors pay for a larger share base after the fresh issue.", group=G)

    # ================= CASE C7: BUDGET =================
    G = "FINA-CASE-BUDGET"
    tax_net, nontax, rec, dis, revx, intr, gcca, capx, gdp = 28.4, 5.6, 0.3, 0.5, 39.4, 12.8, 3.2, 11.2, 356.0
    gtr, cess, coc, statesh = 42.0, 5.6, 0.5, 0.0785
    rr = tax_net + nontax
    ndcr = rec + dis
    stim = ("**Case — Stylised Union Budget (illustrative figures, ₹ lakh crore)**\n\n"
            + table(["Item", "₹ lakh crore"],
                    [["Tax revenue (net to Centre)", f"{tax_net}"], ["Non-tax revenue", f"{nontax}"],
                     ["Recovery of loans", f"{rec}"], ["Disinvestment receipts", f"{dis}"],
                     ["Revenue expenditure", f"{revx}"], ["  of which interest payments", f"{intr}"],
                     ["  of which grants for creation of capital assets", f"{gcca}"], ["Capital expenditure", f"{capx}"],
                     ["Gross tax revenue", f"{gtr}"], ["  of which cesses and surcharges", f"{cess}"], ["Cost of collection", f"{coc}"],
                     ["Nominal GDP", f"{gdp}"]], ["---", "---:"]) +
            f"\n\nThe Finance Commission award: 41% of the divisible pool to States; State Y's horizontal share {pct(statesh)}.")
    fd = revx + capx - rr - ndcr
    A(FRBM, "L4", stim + "\n\nThe fiscal deficit as a percentage of GDP is:",
      pct(fd / gdp),
      [(pct((revx + capx - rr) / gdp), "non-debt capital receipts not deducted"),
       (pct((revx + capx - rr - ndcr - intr) / gdp), "primary deficit reported"),
       (pct((revx + capx - rr - rec) / gdp), "disinvestment treated as financing, not a receipt")],
      [f"Revenue receipts = {rr:.1f}; non-debt capital receipts = {ndcr:.1f}", f"Total expenditure = {revx+capx:.1f}",
       f"FD = {revx+capx:.1f} − {rr+ndcr:.1f} = {fd:.1f} → {pct(fd/gdp)} of GDP"],
      "FD = Total expenditure − (RR + NDCR)", "Disinvestment and loan recoveries are non-debt capital receipts.", group=G)

    rd = revx - rr
    erd = rd - gcca
    A(FRBM, "L4", stim + "\n\nThe effective revenue deficit and primary deficit (₹ lakh crore) are:",
      f"ERD {erd:.1f}; PD {fd-intr:.1f}",
      [(f"ERD {rd:.1f}; PD {fd-intr:.1f}", "revenue deficit reported as ERD (capital-asset grants not deducted)"),
       (f"ERD {erd:.1f}; PD {fd:.1f}", "interest not deducted — fiscal deficit reported as primary deficit"),
       (f"ERD {erd:.1f}; PD {fd-intr-gcca:.1f}", "grants for capital assets also deducted in computing primary deficit")],
      [f"RD = {revx} − {rr:.1f} = {rd:.1f}", f"ERD = RD − grants for capital assets = {rd:.1f} − {gcca} = {erd:.1f}", f"PD = FD − interest = {fd:.1f} − {intr} = {fd-intr:.1f}"],
      "ERD = RD − Grants for creation of capital assets; PD = FD − Interest", "ERD was introduced by the 2012 FRBM amendment.", group=G)

    pool = gtr - cess - coc
    sy = pool * 0.41 * statesh
    A(FC, "L4", stim + "\n\nState Y's share of central taxes under the award is closest to:",
      f"₹{sy:.4f} lakh crore",
      [(f"₹{gtr*0.41*statesh:.4f} lakh crore", "41% applied to gross tax revenue (cesses/surcharges not excluded)"),
       (f"₹{(gtr-cess)*0.41*statesh:.4f} lakh crore", "cost of collection not deducted"),
       (f"₹{tax_net*0.41*statesh:.4f} lakh crore", "41% applied to Centre's net tax revenue")],
      [f"Divisible pool = {gtr} − {cess} − {coc} = {pool:.1f}", f"States' share = 41% × {pool:.1f} = {0.41*pool:.3f}", f"State Y = {pct(statesh)} × {0.41*pool:.3f} = {sy:.4f}"],
      "Divisible pool = GTR − Cesses & surcharges − Cost of collection", "Cesses and surcharges are outside the divisible pool.", group=G)

    kc, kr, sh = 2.45, 0.99, 1.0
    A(FIS, "L4", stim + f"\n\nThe government reallocates ₹{sh:.1f} lakh crore from revenue expenditure to capital expenditure within the same total. If the capital-expenditure multiplier is {kc} and the revenue-expenditure multiplier {kr}, the effect is:",
      f"Fiscal deficit unchanged; GDP higher by about ₹{(kc-kr)*sh:.2f} lakh crore; ERD falls by ₹{sh:.1f} lakh crore",
      [(f"Fiscal deficit falls by ₹{sh:.1f} lakh crore; GDP higher by about ₹{kc*sh:.2f} lakh crore; ERD unchanged", "reallocation treated as additional capex financed by deficit reduction"),
       (f"Fiscal deficit unchanged; GDP higher by about ₹{kc*sh:.2f} lakh crore; ERD also unchanged", "revenue-expenditure cut's negative effect ignored"),
       (f"Fiscal deficit unchanged; GDP higher by about ₹{(kc-kr)*sh:.2f} lakh crore; ERD rises by ₹{sh:.1f} lakh crore", "direction of ERD change reversed")],
      [f"Total expenditure constant ⇒ FD unchanged", f"ΔGDP ≈ {kc} × {sh} − {kr} × {sh} = {(kc-kr)*sh:.2f}", "Revenue expenditure falls ⇒ RD and ERD fall by the same amount."],
      "ΔY = k_cap·ΔG_cap + k_rev·ΔG_rev", "Composition of spending matters even at an unchanged deficit.", group=G, kind="case")
