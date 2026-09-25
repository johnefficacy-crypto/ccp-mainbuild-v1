"""ECO part 4 — Public finance: deficits, budget classification, fiscal policy (40 Q: L1 8, L2 12, L3 12, L4 8)."""
from eco_common import mk, cr, n, tbl, items, stmts, inr, R, pct

BUD = "Union Budget documents — 'Budget at a Glance' deficit definitions; FRBM Act 2003 (as amended)."
CONST = "Constitution of India, Arts. 110, 112–117, 266–267; Union Budget practice from 2017-18."


def add_all(B):
    q = mk(B)

    # ======================= L1 =======================
    q("fiscal-deficit", "L1", "The fiscal deficit of the Union government is best described as:",
      "Total expenditure minus revenue and non-debt capital receipts (total borrowing)",
      [("Revenue expenditure minus revenue receipts of the government", "that is the revenue deficit"),
       ("Fiscal deficit minus interest payments", "that is the primary deficit"),
       ("Total expenditure minus total receipts, borrowings included, in the year", "old 'budget deficit' concept, which is near zero by construction")],
      ["Non-debt receipts = revenue receipts + recoveries of loans + other (e.g. disinvestment) receipts.", "The gap is filled by borrowings and other liabilities."],
      "FD = TE − (RR + Recoveries of loans + Other non-debt capital receipts)", "FD equals borrowings and other liabilities.",
      kind="conceptual", verify_fact=True, ref=BUD)

    q("fiscal-deficit", "L1", "Primary deficit is obtained as:",
      "Fiscal deficit minus interest payments",
      [("Fiscal deficit minus interest receipts", "interest receipts are revenue receipts already inside FD"),
       ("Revenue deficit minus grants for creation of capital assets", "that is the effective revenue deficit"),
       ("Fiscal deficit minus revenue deficit", "that shows borrowing used for capital purposes")],
      ["Removing interest on past debt shows the current fiscal stance.", "PD = FD − Interest payments."],
      "PD = FD − IP", "Use gross interest PAYMENTS.", kind="conceptual", verify_fact=True, ref=BUD)

    q("indian-fiscal-year", "L1", "Which statement about India's Union budget calendar is correct?",
      "The financial year runs from 1 April to 31 March and, since 2017-18, the Union Budget is normally presented on 1 February",
      [("The financial year runs from 1 January to 31 December and the Budget is presented on 1 February", "calendar year is not India's fiscal year"),
       ("The financial year runs from 1 April to 31 March and the Budget is presented on the last working day of February", "pre-2017 practice"),
       ("The financial year runs from 1 July to 30 June and the Budget is presented in May", "that is a different country's cycle")],
      ["Fiscal year: April–March.", "Advancing the Budget to 1 February lets Parliament pass the Appropriation and Finance Bills before the year starts."],
      "—", "The date changed in 2017; the fiscal year did not.", kind="conceptual", verify_fact=True, ref=CONST)

    q("indian-fiscal-year", "L1", "The 'Annual Financial Statement' laid before Parliament each year is mandated by:",
      "Article 112 of the Constitution",
      [("Article 110 of the Constitution", "defines a Money Bill"),
       ("Article 266 of the Constitution", "Consolidated Fund and Public Account"),
       ("Article 280 of the Constitution", "Finance Commission")],
      ["Art. 112: statement of estimated receipts and expenditure for the year.", "Arts. 113–114: demands for grants and Appropriation Bill."],
      "—", "Art. 112 = AFS; Art. 110 = Money Bill.", kind="conceptual", verify_fact=True, ref=CONST)

    q("non-tax", "L1", "Which of the following is a non-tax revenue receipt of the Union government?",
      "Dividends and profits from PSUs and the central bank",
      [("Proceeds from disinvestment of PSU shares", "non-debt capital receipt"),
       ("Recoveries of loans given to states", "non-debt capital receipt"),
       ("Market borrowings through dated government securities", "debt-creating capital receipt")],
      ["Non-tax revenue = interest receipts, dividends & profits, fees/user charges, external grants etc.", "They neither create liability nor reduce assets."],
      "Revenue receipt: no liability created, no asset reduced", "Disinvestment reduces assets ⇒ capital receipt.", kind="conceptual")

    q("plan-and-non-plan", "L1", "With effect from the Union Budget 2017-18, the plan / non-plan classification of expenditure was:",
      "Discontinued, with the focus shifting to the revenue / capital classification",
      [("Made the primary classification, replacing revenue / capital", "the reverse happened"),
       ("Retained only for central sector schemes", "no such partial retention"),
       ("Replaced by a developmental / non-developmental split in the Budget", "that is an RBI analytical classification, not the Budget's replacement")],
      ["Following the end of Five-Year Plans and expert recommendations, the plan/non-plan split was merged from 2017-18.",
       "Expenditure is presented as revenue vs capital (and by schemes)."],
      "—", "Same year: Railway Budget merged and Budget date advanced.", kind="conceptual", verify_fact=True, ref=CONST)

    q("automatic-stabilisers", "L1", "Which of the following acts as an automatic stabiliser?",
      "A progressive personal income tax",
      [("A discretionary infrastructure stimulus package", "discretionary, needs a new decision"),
       ("A cut in the policy repo rate", "monetary, and discretionary"),
       ("A one-time recapitalisation of public sector banks", "discretionary one-off measure")],
      ["Tax revenue rises faster than income in booms and falls faster in slumps — without any new legislation.", "This dampens swings in disposable income."],
      "Built-in: T = tY with t rising in Y", "'Automatic' means no fresh policy action.", kind="conceptual")

    q("revenue-vs-capital", "L1", "Which of the following is revenue expenditure of the Union government?",
      "Interest payments on public debt",
      [("Capital outlay on defence equipment", "capital expenditure"),
       ("Loans and advances to state governments", "capital expenditure — creates a financial asset"),
       ("Purchase of equity in a public sector enterprise", "capital expenditure — creates a financial asset")],
      ["Revenue expenditure neither creates assets nor reduces liabilities.", "Interest is a current cost of borrowing."],
      "Capital expenditure: creates assets or reduces liabilities", "Interest is revenue expenditure even though debt is capital.", kind="conceptual")

    # ======================= L2 =======================
    TE, RR, rec, oth = 45000, 32000, 800, 1200
    fd = TE - RR - rec - oth
    q("fiscal-deficit", "L2",
      f"Total expenditure {cr(TE)}; revenue receipts {cr(RR)}; recoveries of loans {cr(rec)}; disinvestment receipts {cr(oth)}. Fiscal deficit is:",
      cr(fd),
      [(cr(fd + rec), "recoveries of loans not treated as non-debt receipts"),
       (cr(fd + oth), "disinvestment receipts not deducted"),
       (cr(TE - RR), "only revenue receipts deducted")],
      [f"Non-debt receipts = {inr(RR)} + {rec} + {inr(oth)} = {inr(RR+rec+oth)}", f"FD = {inr(TE)} − {inr(RR+rec+oth)} = {inr(fd)}"],
      "FD = TE − RR − non-debt capital receipts", "Options differ by exactly one misclassified item.", verify_fact=True, ref=BUD)

    FD2, IP, IR = 6400, 3900, 700
    q("fiscal-deficit", "L2",
      f"Fiscal deficit {cr(FD2)}; interest payments {cr(IP)}; interest receipts {cr(IR)}. Primary deficit is:",
      cr(FD2 - IP),
      [(cr(FD2 - (IP - IR)), "net interest (payments − receipts) deducted"),
       (cr(FD2 - IR), "interest receipts deducted instead of payments"),
       (cr(FD2 + IP), "interest added instead of deducted")],
      [f"PD = {inr(FD2)} − {inr(IP)} = {inr(FD2-IP)}"],
      "PD = FD − Interest payments", "Interest receipts are already in revenue receipts.", verify_fact=True, ref=BUD)

    RE3, tax3, nt3, rec3, gca3 = 32000, 22500, 4000, 1000, 1500
    rd3 = RE3 - tax3 - nt3
    q("fiscal-deficit", "L2",
      f"Revenue expenditure {cr(RE3)} (including grants for creation of capital assets {cr(gca3)}); tax revenue (net) {cr(tax3)}; non-tax revenue {cr(nt3)}; recoveries of loans {cr(rec3)}. Revenue deficit is:",
      cr(rd3),
      [(cr(RE3 - tax3), "non-tax revenue ignored"),
       (cr(rd3 - rec3), "recoveries of loans (a capital receipt) deducted"),
       (cr(rd3 - gca3), "grants for capital assets deducted — that is the effective revenue deficit")],
      [f"RD = {inr(RE3)} − ({inr(tax3)} + {inr(nt3)}) = {inr(rd3)}"],
      "RD = RE − RR", "Capital receipts never enter the revenue deficit.", verify_fact=True, ref=BUD)

    RD4, G4, FD4 = 5500, 1800, 9000
    q("fiscal-deficit", "L2",
      f"Revenue deficit {cr(RD4)}; grants for creation of capital assets {cr(G4)}; fiscal deficit {cr(FD4)}. Effective revenue deficit is:",
      cr(RD4 - G4),
      [(cr(RD4 + G4), "grants added instead of deducted"),
       (cr(RD4), "grants adjustment ignored"),
       (cr(FD4 - G4), "grants deducted from fiscal deficit instead of revenue deficit")],
      [f"ERD = {inr(RD4)} − {inr(G4)} = {inr(RD4-G4)}"],
      "ERD = RD − Grants for creation of capital assets", "ERD starts from RD, not FD.", verify_fact=True, ref=BUD)

    q("revenue-vs-capital", "L2", "In the Union Budget, proceeds from strategic disinvestment of a central PSU are classified as:",
      "A non-debt capital receipt",
      [("Non-tax revenue", "disinvestment reduces an asset, so it is not revenue"),
       ("A debt-creating capital receipt", "no liability is created"),
       ("A revenue receipt under 'other receipts'", "'other receipts' is a capital-receipt head")],
      ["Capital receipts either create a liability or reduce an asset.", "Sale of equity reduces the government's assets without creating debt ⇒ non-debt capital receipt."],
      "Receipt test: liability created? asset reduced?", "Non-debt capital receipts reduce the fiscal deficit.", kind="conceptual", verify_fact=True, ref=BUD)

    q("revenue-vs-capital", "L2", "Grants-in-aid given by the Union to states for the creation of capital assets are treated in the Union's accounts as:",
      "Revenue expenditure of the Union (adjusted in ERD)",
      [("Capital expenditure of the Union, as assets are built", "the asset is owned by the state, not the Union"),
       ("A capital receipt of the Union", "it is a payment, not a receipt"),
       ("Excluded from the Union Budget", "grants are budgeted expenditure")],
      ["The Union neither acquires an asset nor reduces a liability.", "Hence revenue expenditure; ERD adjusts for it because the spending builds assets somewhere in the economy."],
      "ERD = RD − Grants for creation of capital assets", "Asset ownership decides the classification.", kind="conceptual", verify_fact=True, ref=BUD)

    q("government-borrowings", "L2", "Treasury bills issued by the Government of India are currently of which maturities?",
      "91 days, 182 days and 364 days",
      [("91 days, 182 days, 273 days and 364 days", "273-day T-bills are not currently issued"),
       ("30 days, 90 days and 180 days", "these are not Indian T-bill tenors"),
       ("1 year, 3 years and 5 years", "those are dated-security style tenors")],
      ["T-bills are zero-coupon, short-term instruments of the Central government.", "Cash Management Bills (under 91 days) are issued separately for temporary mismatches."],
      "—", "364-day, not 365-day.", kind="conceptual", verify_fact=True, ref="RBI / GoI T-bill issuance calendar.")

    c8, t8 = 0.8, 0.2
    k8 = 1 / (1 - c8 * (1 - t8))
    q("automatic-stabilisers", "L2",
      f"MPC is {c8}. Introducing a proportional income tax at {pct(t8)} changes the government-spending multiplier from {n(1/(1-c8))} to:",
      n(k8),
      [(n(1 / (1 - c8)), "tax has no effect on the multiplier"),
       (n((1 - t8) / (1 - c8)), "multiplier scaled by (1 − t) instead of changing the leakage"),
       (n(1 / (1 - c8 + t8)), "tax rate added to MPS")],
      [f"k = 1/[1 − {c8}(1 − {t8})] = 1/{n(1-c8*(1-t8))} = {n(k8)}", "A smaller multiplier means shocks are damped — the stabiliser effect."],
      "k = 1/[1 − c(1 − t)]", "Stabilisers work by reducing the multiplier.")

    gap, c9 = 600, 0.75
    kG9 = 1 / (1 - c9); kT9 = c9 / (1 - c9)
    q("countercyclical", "L2",
      f"Equilibrium income is {cr(gap)} below full-employment income. MPC is {c9} and there are no income-related taxes or imports. The increase in government purchases needed to close the gap is:",
      cr(gap / kG9),
      [(cr(gap), "gap itself taken as the required spending"),
       (cr(gap / kT9), "tax multiplier used — that is the required tax cut"),
       (cr(gap * c9), "gap multiplied by MPC")],
      [f"k = 1/(1 − {c9}) = {n(kG9)}", f"ΔG = {gap}/{n(kG9)} = {inr(gap/kG9)}"],
      "ΔG = Gap ÷ k", "Close the income gap, not the spending gap.")
    q("countercyclical", "L2",
      f"In the same economy (gap {cr(gap)}, MPC {c9}), the lump-sum tax cut that alone would close the gap is:",
      cr(gap / kT9),
      [(cr(gap / kG9), "government-purchase multiplier used"),
       (cr(gap), "gap itself taken as the tax cut"),
       (cr(gap / c9), "gap divided by MPC")],
      [f"Tax multiplier = c/(1 − c) = {n(kT9)}", f"ΔT = {gap}/{n(kT9)} = {inr(gap/kT9)}"],
      "ΔT = Gap ÷ [c/(1 − c)]", "A tax cut must be larger than a spending rise because part of it is saved.")

    FD11, IP11, GDP11 = 16000, 9600, 320000
    q("fiscal-deficit", "L2",
      f"Fiscal deficit {cr(FD11)}; interest payments {cr(IP11)}; GDP {cr(GDP11)}. Fiscal deficit and primary deficit as percentages of GDP are:",
      f"{pct(FD11/GDP11,1)} and {pct((FD11-IP11)/GDP11,1)}",
      [(f"{pct(FD11/GDP11,1)} and {pct(IP11/GDP11,1)}", "interest-to-GDP reported as primary deficit"),
       (f"{pct((FD11-IP11)/GDP11,1)} and {pct(FD11/GDP11,1)}", "the two ratios interchanged"),
       (f"{pct(FD11/GDP11,1)} and {pct((FD11+IP11)/GDP11,1)}", "interest added instead of deducted")],
      [f"FD/GDP = {inr(FD11)}/{inr(GDP11)} = {pct(FD11/GDP11,1)}", f"PD = {inr(FD11-IP11)} ⇒ {pct((FD11-IP11)/GDP11,1)}"],
      "Deficit ratio = Deficit ÷ GDP × 100", "PD/GDP = FD/GDP − IP/GDP.")

    q("monetary-and-fiscal", "L2", "In the IS-LM framework, a combination of expansionary fiscal policy and contractionary monetary policy will:",
      "Raise the interest rate unambiguously, while the effect on output is ambiguous",
      [("Raise both output and the interest rate unambiguously", "ignores the output-reducing effect of monetary tightening"),
       ("Raise output unambiguously, while the interest-rate effect is ambiguous", "both moves push r up"),
       ("Lower both output and the interest rate", "fiscal expansion raises r")],
      ["IS shifts right: Y↑, r↑.", "LM shifts left: Y↓, r↑.", "r rises for sure; Y depends on relative sizes."],
      "IS right + LM left ⇒ r↑, Y?", "Identify which variable both shifts move in the same direction.", kind="conceptual")

    # ======================= L3 =======================
    rows1 = [("Tax revenue (net to Centre)", 20000), ("Non-tax revenue", 3500), ("Recoveries of loans", 400),
             ("Other receipts (disinvestment)", 600), ("Revenue expenditure", 30000), ("  of which: interest payments", 8000),
             ("  of which: grants for creation of capital assets", 2500), ("Capital expenditure", 7500)]
    tx, nt, rl, dis, re, ip, gca, ce = [x[1] for x in rows1]
    fd1 = re + ce - (tx + nt + rl + dis)
    assert fd1 == 13000
    q("fiscal-deficit", "L3",
      "From the following budget data (₹ crore), fiscal deficit is:\n\n" + items(rows1),
      cr(fd1),
      [(cr(fd1 + rl), "recoveries of loans omitted from non-debt receipts"),
       (cr(fd1 + dis), "disinvestment omitted from non-debt receipts"),
       (cr(fd1 + rl + dis), "both non-debt capital receipts omitted (RD + capital expenditure)")],
      [f"Total expenditure = {inr(re)} + {inr(ce)} = {inr(re+ce)}", f"Revenue receipts = {inr(tx)} + {inr(nt)} = {inr(tx+nt)}",
       f"FD = {inr(re+ce)} − {inr(tx+nt)} − {rl} − {dis} = {inr(fd1)}", "'Of which' lines are already inside revenue expenditure."],
      "FD = TE − RR − Recoveries − Other receipts", "Do not add the 'of which' lines again.", verify_fact=True, ref=BUD)

    TE2, IP2, RR2, IR2, ND2 = 50000, 12000, 36000, 1500, 2500
    FD2b = TE2 - RR2 - ND2; PD2 = FD2b - IP2
    ps = lambda x: f"Primary surplus of {cr(-x)}" if x < 0 else f"Primary deficit of {cr(x)}"
    q("fiscal-deficit", "L3",
      "Budget data (₹ crore):\n\n" + items([("Total expenditure", TE2), ("  of which: interest payments", IP2),
                                             ("Revenue receipts", RR2), ("  of which: interest receipts", IR2),
                                             ("Non-debt capital receipts", ND2)]) + "\n\nThe primary balance is:",
      ps(PD2),
      [(ps(FD2b - (IP2 - IR2)), "net interest (payments − receipts) deducted"),
       (ps(FD2b), "fiscal deficit reported as primary deficit"),
       (ps(FD2b - IP2 - IR2), "interest receipts deducted a second time")],
      [f"FD = {inr(TE2)} − {inr(RR2)} − {inr(ND2)} = {inr(FD2b)}", f"PD = {inr(FD2b)} − {inr(IP2)} = {inr(PD2)} ⇒ primary surplus"],
      "PD = FD − Interest payments", "A negative PD is a primary surplus: non-interest spending is fully covered.", verify_fact=True, ref=BUD)

    t3, n3, re3, g3, r3 = 18000, 3000, 27500, 2200, 500
    RD3 = re3 - t3 - n3; ERD3 = RD3 - g3
    pr = lambda a, b: f"RD {cr(a)}; ERD {cr(b)}"
    q("fiscal-deficit", "L3",
      f"Tax revenue {cr(t3)}; non-tax revenue {cr(n3)}; revenue expenditure {cr(re3)} (including grants for creation of capital assets {cr(g3)}); recoveries of loans {cr(r3)}. Revenue deficit and effective revenue deficit are:",
      pr(RD3, ERD3),
      [(pr(RD3 - r3, ERD3 - r3), "recoveries of loans treated as revenue receipts"),
       (pr(RD3, RD3 + g3), "grants added instead of deducted for ERD"),
       (pr(RD3 + n3, ERD3 + n3), "non-tax revenue left out of revenue receipts")],
      [f"RD = {inr(re3)} − {inr(t3+n3)} = {inr(RD3)}", f"ERD = {inr(RD3)} − {inr(g3)} = {inr(ERD3)}"],
      "RD = RE − RR; ERD = RD − GCA", "Each wrong pair carries one misclassification through both figures.", verify_fact=True, ref=BUD)

    q("revenue-vs-capital", "L3",
      "Which of the following are capital receipts of the Union government?\n\n" + stmts([
          "Recovery of loans given to state governments",
          "Dividend received from a public sector bank",
          "Proceeds from sale of shares of a central PSU",
          "Market borrowings through dated government securities"]),
      "1, 3 and 4 only",
      [("1 and 3 only", "borrowings are debt-creating capital receipts"),
       ("1, 2, 3 and 4", "dividend is non-tax revenue"),
       ("3 and 4 only", "loan recoveries reduce an asset ⇒ capital receipt")],
      ["Capital receipts: create a liability (4) or reduce an asset (1, 3).", "Dividend is income on an asset ⇒ revenue receipt (2)."],
      "Receipt test: liability↑ or asset↓ ⇒ capital", "Income FROM an asset is revenue; sale OF an asset is capital.", kind="statement", verify_fact=True, ref=BUD)

    q("revenue-vs-capital", "L3",
      "Match the budget item with its classification in the Union Budget:\n\n" + tbl(["Item", "", "Classification"], [
          ("A. Interest payments", "", "1. Revenue expenditure"),
          ("B. Recovery of loans from states", "", "2. Capital expenditure"),
          ("C. Loans to state governments", "", "3. Non-debt capital receipt"),
          ("D. Spectrum auction proceeds", "", "4. Non-tax revenue")], right=set()) + "\n\nCodes (A-B-C-D):",
      "1-3-2-4",
      [("1-2-3-4", "loans given and loans recovered interchanged"),
       ("1-4-2-3", "loan recovery booked as non-tax revenue and spectrum proceeds as a capital receipt"),
       ("2-3-1-4", "interest payments and loans to states interchanged")],
      ["Interest: revenue expenditure (1).", "Recovery of loans: non-debt capital receipt (3).", "Loans to states: capital expenditure (2).",
       "Spectrum auction proceeds are booked as non-tax revenue (communication services) (4)."],
      "—", "Spectrum sale looks like an asset sale but is booked as non-tax revenue.", kind="conceptual", verify_fact=True, ref=BUD)

    q("fiscal-deficit", "L3",
      "**Assertion (A):** If the primary deficit is zero, the fiscal deficit equals interest payments.\n\n"
      "**Reason (R):** With zero primary deficit, the government borrows only to meet interest on past debt.",
      "Both A and R are true and R is the correct explanation of A",
      [("Both A and R are true but R is not the correct explanation of A", "R is the economic reading of the identity"),
       ("A is true but R is false", "R follows directly"),
       ("A is false because interest receipts must also be deducted", "PD uses gross interest payments")],
      ["PD = FD − IP = 0 ⇒ FD = IP.", "All borrowing finances interest; non-interest spending is covered by non-debt receipts."],
      "PD = FD − IP", "Zero PD ≠ zero borrowing.", kind="assertion-reason", verify_fact=True, ref=BUD)

    shift = 1000
    q("fiscal-deficit", "L3",
      f"The Union reduces grants to states for creation of capital assets by {cr(shift)} and spends the same amount itself on capital projects. Consider:\n\n" + stmts([
          f"Revenue deficit falls by {cr(shift)}.", "Effective revenue deficit is unchanged.", f"Fiscal deficit falls by {cr(shift)}."]) +
      "\n\nWhich are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "total expenditure is unchanged, so FD is unchanged"),
       ("1 and 3 only", "ERD: RD falls by 1,000 but grants for capital assets also fall by 1,000"),
       ("2 only", "revenue expenditure does fall")],
      [f"Revenue expenditure −{shift}, capital expenditure +{shift}: TE unchanged ⇒ FD unchanged.", f"RD −{shift}.",
       f"ERD = RD − GCA = (RD − {shift}) − (GCA − {shift}) ⇒ unchanged."],
      "ERD = RD − GCA; FD depends on TE", "Reclassification moves RD but not FD or ERD.", kind="statement", verify_fact=True, ref=BUD)

    q("government-borrowings", "L3",
      "Consider the following statements about Central government borrowing:\n\n" + stmts([
          "Dated government securities are long-term marketable instruments forming part of internal debt.",
          "Ways and Means Advances from RBI are meant to bridge temporary mismatches between receipts and payments.",
          "External debt consists only of borrowings from multilateral institutions.",
          "Treasury bills form part of the internal debt of the Central government."]) + "\n\nWhich are correct?",
      "1, 2 and 4 only",
      [("1 and 2 only", "T-bills are short-term internal debt"),
       ("1, 2, 3 and 4", "external debt also includes bilateral loans"),
       ("2, 3 and 4 only", "dated securities are the largest internal debt component")],
      ["Internal debt: dated securities, T-bills, etc. (1, 4).", "WMA: temporary accommodation from RBI (2).", "External debt: multilateral and bilateral (3 false)."],
      "—", "'Only' is usually the tell.", kind="statement", verify_fact=True, ref="RBI Act s.17(5) (WMA); GoI Status Paper on Government Debt.")

    rows9 = [("Interest receipts", 1200), ("Dividends and profits (incl. central bank surplus)", 2800), ("Fees for services", 300),
             ("Fines and penalties", 50), ("External grants", 100), ("Disinvestment proceeds", 900), ("Recoveries of loans", 400),
             ("GST (Centre's share)", 5000), ("Customs duty", 700)]
    ntr = 1200 + 2800 + 300 + 50 + 100
    q("non-tax", "L3", "From the following receipts (₹ crore), non-tax revenue is:\n\n" + items(rows9),
      cr(ntr),
      [(cr(ntr + 900), "disinvestment proceeds treated as non-tax revenue"),
       (cr(ntr + 400), "recoveries of loans treated as non-tax revenue"),
       (cr(ntr - 100), "external grants excluded")],
      [f"Non-tax = 1,200 + 2,800 + 300 + 50 + 100 = {inr(ntr)}", "Disinvestment and loan recoveries are capital receipts; GST and customs are tax revenue."],
      "Non-tax revenue: interest, dividends/profits, fees, fines, grants", "External grants are revenue receipts under non-tax revenue.", verify_fact=True, ref=BUD)

    rows10 = [("Market loans (net)", 9000), ("Short-term borrowings (T-bills, net)", 500), ("Securities against small savings", 1800),
              ("State provident funds (net)", 200), ("External debt (net)", 300), ("Draw-down of cash balance", 200)]
    fd10 = sum(x[1] for x in rows10)
    q("fiscal-deficit", "L3", "The financing side of a budget (₹ crore) is given below. The fiscal deficit is:\n\n" + items(rows10),
      cr(fd10),
      [(cr(fd10 - 200), "draw-down of cash balance excluded from financing"),
       (cr(fd10 - 300), "external borrowing excluded"),
       (cr(fd10 - 1800), "small-savings financing excluded")],
      [f"FD = Σ financing items = {inr(fd10)}"],
      "FD = Net borrowing + other liabilities + draw-down of cash", "Every financing source, domestic or external, counts.", verify_fact=True, ref=BUD)

    rows11 = [("Defence capital outlay", 1500), ("Loans to state governments", 800), ("Purchase of equity in a PSU", 400),
              ("Salaries of employees", 2000), ("Interest payments", 3000), ("Grants to states for creation of capital assets", 700),
              ("Subsidies", 1200), ("Construction of national highways", 1100)]
    cap = 1500 + 800 + 400 + 1100
    q("revenue-vs-capital", "L3", "From the following Union expenditure items (₹ crore), capital expenditure is:\n\n" + items(rows11),
      cr(cap),
      [(cr(cap + 700), "grants for capital assets treated as Union capital expenditure"),
       (cr(cap - 800), "loans to states treated as revenue expenditure"),
       (cr(cap - 400), "equity purchase treated as revenue expenditure")],
      [f"Capital = 1,500 + 800 + 400 + 1,100 = {inr(cap)}", "Grants (even for capital assets), salaries, interest and subsidies are revenue expenditure."],
      "Capital expenditure: acquires assets / loans & advances", "Asset ownership test for grants.", verify_fact=True, ref=BUD)

    q("indian-fiscal-year", "L3",
      "Consider the following statements:\n\n" + stmts([
          "Presenting the Union Budget on 1 February allows the Appropriation Bill to be passed before the financial year begins.",
          "A vote on account permits withdrawal from the Consolidated Fund for part of the year pending passage of the full budget.",
          "Being a Money Bill, the Finance Bill can be amended by the Rajya Sabha.",
          "The Railway Budget has been merged with the Union Budget since 2017-18."]) + "\n\nWhich are correct?",
      "1, 2 and 4 only",
      [("1 and 2 only", "misses the 2017-18 merger"),
       ("1, 2, 3 and 4", "Rajya Sabha can only recommend, not amend, a Money Bill"),
       ("2, 3 and 4 only", "rejects the purpose of advancing the Budget date")],
      ["1 Feb presentation ⇒ full budget by 31 March (1).", "Art. 116: vote on account (2).", "Art. 109: Rajya Sabha may only recommend within 14 days (3 false).",
       "Rail budget merged from 2017-18 (4)."],
      "—", "Money Bill: Lok Sabha may accept or reject RS recommendations.", kind="statement", verify_fact=True, ref=CONST)

    # ======================= L4 case H (budget) =======================
    GH = "ECO-BUDGET-CASE-H"
    rowsH = [("Tax revenue (net to Centre)", 24000), ("Non-tax revenue", 4500), ("  of which: interest receipts", 700),
             ("Recoveries of loans", 600), ("Other capital receipts (disinvestment)", 900), ("Revenue expenditure", 36000),
             ("  of which: interest payments", 9500), ("  of which: grants for creation of capital assets", 3200),
             ("Capital expenditure", 8400)]
    txH, ntH, irH, rlH, dsH, reH, ipH, gcH, ceH = [x[1] for x in rowsH]
    rrH = txH + ntH; teH = reH + ceH
    fdH = teH - rrH - rlH - dsH; rdH = reH - rrH; erdH = rdH - gcH; pdH = fdH - ipH
    assert (fdH, rdH, erdH, pdH) == (14400, 7500, 4300, 4900)
    stemH = ("**Case — Union budget of Dakshinara.** Budget estimates for the year (₹ crore). Borrowings and other liabilities are the balancing item.\n\n" +
             items(rowsH) + "\n\n")
    q("fiscal-deficit", "L4", stemH + "**Q.** Fiscal deficit is:",
      cr(fdH),
      [(cr(fdH + rlH), "recoveries of loans omitted"),
       (cr(fdH + dsH), "disinvestment omitted"),
       (cr(fdH + rlH + dsH), "both non-debt capital receipts omitted")],
      [f"TE = {inr(reH)} + {inr(ceH)} = {inr(teH)}", f"RR = {inr(txH)} + {inr(ntH)} = {inr(rrH)}", f"FD = {inr(teH)} − {inr(rrH)} − {rlH} − {dsH} = {inr(fdH)}"],
      "FD = TE − RR − non-debt capital receipts", "Interest receipts are already inside non-tax revenue.", kind="case", group=GH, verify_fact=True, ref=BUD)
    q("fiscal-deficit", "L4", stemH + "**Q.** Revenue deficit is:",
      cr(rdH),
      [(cr(reH - txH), "non-tax revenue left out"),
       (cr(erdH), "effective revenue deficit reported"),
       (cr(rdH - rlH - dsH), "non-debt capital receipts deducted as well")],
      [f"RD = {inr(reH)} − {inr(rrH)} = {inr(rdH)}"],
      "RD = RE − RR", "Capital receipts do not enter RD.", kind="case", group=GH, verify_fact=True, ref=BUD)
    q("fiscal-deficit", "L4", stemH + "**Q.** Effective revenue deficit is:",
      cr(erdH),
      [(cr(rdH + gcH), "grants added instead of deducted"),
       (cr(fdH - gcH), "grants deducted from fiscal deficit"),
       (cr(rdH), "grants adjustment ignored")],
      [f"ERD = {inr(rdH)} − {inr(gcH)} = {inr(erdH)}"],
      "ERD = RD − GCA", "Start from RD.", kind="case", group=GH, verify_fact=True, ref=BUD)
    q("fiscal-deficit", "L4", stemH + "**Q.** Primary deficit is:",
      cr(pdH),
      [(cr(fdH - (ipH - irH)), "net interest deducted"),
       (cr(fdH - ipH - irH), "interest receipts deducted in addition"),
       (cr(fdH + ipH), "interest added")],
      [f"PD = {inr(fdH)} − {inr(ipH)} = {inr(pdH)}"],
      "PD = FD − Interest payments", "Gross interest payments only.", kind="case", group=GH, verify_fact=True, ref=BUD)

    # ======================= L4 case I (stabilisation) =======================
    GI = "ECO-STAB-CASE-I"
    Ystar, Yact, cI, tI, defI = 10000, 9000, 0.8, 0.25, 900
    kI = 1 / (1 - cI * (1 - tI)); gapI = Ystar - Yact
    stemI = ("**Case — Stabilising Meruvia.** Potential output is ₹10,000 crore but actual output is ₹9,000 crore. Households' MPC out of disposable "
             "income is 0.8; the only tax is a proportional income tax at 25%; the economy is closed and investment is autonomous. "
             "The actual budget deficit this year is ₹900 crore.\n\n")
    q("countercyclical", "L4", stemI + "**Q.** The increase in government purchases needed to restore potential output is:",
      cr(gapI / kI),
      [(cr(gapI), "gap taken as the required spending"),
       (cr(gapI * (1 - cI)), "simple multiplier 1/(1 − c) used, ignoring the tax leakage"),
       (cr(gapI / (cI * kI)), "tax-cut multiplier used")],
      [f"k = 1/[1 − 0.8 × 0.75] = {n(kI)}", f"ΔG = {inr(gapI)}/{n(kI)} = {inr(gapI/kI)}"],
      "ΔG = Gap / [1/(1 − c(1 − t))]", "Include the tax leakage in the multiplier.", kind="case", group=GI)
    cyc = tI * gapI
    q("automatic-stabilisers", "L4", stemI + "**Q.** How much of the actual deficit is cyclical, i.e. due to income-tax revenue lost because output is below potential?",
      cr(cyc),
      [(cr(cyc * kI), "revenue loss multiplied again by the multiplier"),
       (cr(gapI * (1 - tI)), "(1 − t) applied instead of t"),
       ("Nil — tax revenue does not depend on income", "ignores the proportional tax")],
      [f"Lost revenue = t × (Y* − Y) = 0.25 × {inr(gapI)} = {inr(cyc)}"],
      "Cyclical deficit = t × output gap", "This revenue shortfall is the automatic stabiliser at work.", kind="case", group=GI)
    q("fiscal-deficit", "L4", stemI + "**Q.** The structural (cyclically adjusted) deficit is:",
      cr(defI - cyc),
      [(cr(defI + cyc), "cyclical part added instead of removed"),
       (cr(defI), "no cyclical adjustment made"),
       (cr(defI - gapI / kI), "required stimulus subtracted instead of cyclical revenue loss")],
      [f"Structural = actual − cyclical = {defI} − {inr(cyc)} = {inr(defI-cyc)}"],
      "Structural deficit = Actual − Cyclical", "Structural deficit is what would remain at potential output.", kind="case", group=GI)
    q("countercyclical", "L4", stemI + "**Q.** If instead a lump-sum tax cut were used, the size of the cut needed to close the gap would be:",
      cr(gapI / (cI * kI)),
      [(cr(gapI / kI), "government-purchase multiplier used"),
       (cr(gapI * (1 - cI) / cI), "simple tax multiplier c/(1 − c) used, ignoring the income tax"),
       (cr(gapI), "gap taken as the tax cut")],
      [f"Lump-sum tax multiplier = c × k = 0.8 × {n(kI)} = {n(cI*kI)}", f"ΔT = {inr(gapI)}/{n(cI*kI)} = {inr(gapI/(cI*kI))}"],
      "k_T = c/[1 − c(1 − t)]", "Tax cut > spending rise for the same effect.", kind="case", group=GI)
