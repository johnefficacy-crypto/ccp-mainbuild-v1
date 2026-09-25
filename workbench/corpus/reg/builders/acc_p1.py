"""Part 1: fundamentals, accounting process, concepts, errors, bills, software/XBRL, applicability, convergence."""
from acc_common import S, R, inr, pct, ar, stmt, match, table


def add_all(B):
    # ---------------- Accounting equation ----------------
    A0, L0 = 500000, 180000
    C0 = A0 - L0
    cost, mk = 40000, 0.25
    sale = cost * (1 + mk)
    pay_cr, draw_g, os_sal = 30000, 8000, 6000
    C1 = C0 + (sale - cost) - draw_g - os_sal
    assert C1 == 316000
    B.add(micro=S("accounting-equation"), level="L2",
          stem=(f"Mehar Stores begins with total assets of {R(A0)} and outside liabilities of {R(L0)}. During the week:\n\n"
                f"1. Goods costing {R(cost)} sold on credit at a mark-up of {pct(mk)} on cost.\n"
                f"2. Paid a creditor {R(pay_cr)}.\n3. Proprietor took goods costing {R(draw_g)} for personal use.\n"
                f"4. Salary of {R(os_sal)} became outstanding.\n\nApplying the accounting equation, closing capital is:"),
          correct=R(C1),
          wrongs=[(R(C0 + (sale - cost) - draw_g), "outstanding salary ignored (accrued expense missed)"),
                  (R(C0 + sale - draw_g - os_sal), "entire sale value added to capital instead of the profit element"),
                  (R(C0 + (sale - cost) + draw_g - os_sal), "drawings added to capital (sign reversed)")],
          steps=[f"Opening capital = {inr(A0)} − {inr(L0)} = {inr(C0)}",
                 f"Credit sale: profit {inr(sale)} − {inr(cost)} = {inr(sale-cost)} raises capital",
                 "Paying a creditor reduces assets and liabilities equally — no effect on capital",
                 f"Drawings −{inr(draw_g)}; outstanding salary is an expense −{inr(os_sal)}",
                 f"Closing capital = {inr(C0)} + {inr(sale-cost)} − {inr(draw_g)} − {inr(os_sal)} = {inr(C1)}"],
          formula="Capital = Assets − Liabilities; ΔCapital = Profit − Drawings",
          trap="Only the profit on a sale (not the sale value) changes capital; a creditor payment never does.")

    B.add(micro=S("accounting-equation"), level="L1",
          stem="Which of the following transactions leaves the TOTAL of assets unchanged?",
          correct="Purchase of furniture for cash",
          wrongs=[("Purchase of furniture on credit from a supplier", "credit purchase increases assets and liabilities"),
                  ("Payment of rent in cash", "expense payment reduces assets and capital"),
                  ("Introduction of additional capital in cash", "capital introduced increases assets")],
          steps=["Cash purchase of furniture: one asset (furniture) up, another (cash) down by the same amount.",
                 "Total assets unchanged; only the composition changes."],
          formula="Assets = Liabilities + Capital", trap="Credit purchases expand both sides; cash purchases only swap assets.",
          kind="conceptual")

    # ---------------- Double entry ----------------
    B.add(micro=S("double-entry"), level="L1",
          stem="The proprietor withdraws goods costing ₹12,000 (sale value ₹15,000) for personal use. The correct journal entry is:",
          correct="Drawings A/c Dr ₹12,000 To Purchases A/c ₹12,000",
          wrongs=[("Drawings A/c Dr ₹15,000 To Sales A/c ₹15,000", "recorded at selling price as a sale"),
                  ("Purchases A/c Dr ₹12,000 To Drawings A/c ₹12,000", "debit and credit reversed"),
                  ("Capital A/c Dr ₹12,000 To Stock A/c ₹12,000", "credits stock instead of purchases in a periodic system")],
          steps=["Goods withdrawn reduce goods available for sale — credit Purchases at cost.",
                 "The withdrawal is drawings of the proprietor — debit Drawings."],
          formula="Debit the receiver (proprietor via drawings); credit what goes out (purchases, at cost)",
          trap="Withdrawal is recorded at cost, not sale value; it is not a sale.", kind="conceptual")

    dr, disc = 50000, 0.03
    recv = dr * (1 - disc)
    B.add(micro=S("double-entry"), level="L2",
          stem=(f"Ravi owes the firm {R(dr)}. He settles the account in full by paying cash after being allowed a cash discount of "
                f"{pct(disc)}. The firm's entry is:"),
          correct=f"Cash A/c Dr {R(recv)}; Discount Allowed A/c Dr {R(dr-recv)}; To Ravi {R(dr)}",
          wrongs=[(f"Cash A/c Dr {R(recv)}; To Ravi {R(recv)}", "discount not recorded, leaving a debit balance on Ravi"),
                  (f"Cash A/c Dr {R(dr)}; To Ravi {R(recv)}; To Discount Allowed {R(dr-recv)}", "discount credited as if received"),
                  (f"Cash A/c Dr {R(recv)}; Discount Received A/c Dr {R(dr-recv)}; To Ravi {R(dr)}", "confuses discount allowed with discount received")],
          steps=[f"Cash received = {inr(dr)} × (1 − {pct(disc)}) = {inr(recv)}",
                 f"Discount allowed = {inr(dr-recv)} — a loss (nominal account) debited",
                 f"Ravi (personal account, giver) credited with full {inr(dr)}"],
          formula="Debit what comes in and all losses; credit the giver", trap="Discount allowed is an expense of the firm (debit).")

    # ---------------- Stages of accounting process ----------------
    B.add(micro=S("stages-of-the"), level="L1",
          stem="Transferring entries from the journal to the respective ledger accounts belongs to which stage of the accounting process?",
          correct="Classifying",
          wrongs=[("Recording", "journalising is recording, posting is classifying"),
                  ("Summarising", "summarising is the trial balance / financial statements stage"),
                  ("Interpreting", "interpretation follows analysis of statements")],
          steps=["Identify → Record (journal/subsidiary books) → Classify (ledger posting) → Summarise (trial balance, statements) → Analyse/interpret → Communicate."],
          formula="Accounting cycle sequence", trap="Posting groups like items together — that is classification.", kind="conceptual")

    stmt(B, S("stages-of-the"), "L2", "Consider the following statements about the accounting process:",
         ["A trial balance is prepared from ledger balances and is a step towards summarising.",
          "Agreement of the trial balance proves that the books are free from all errors.",
          "Subsidiary books such as the purchases book are part of the recording stage."],
         [1, 3], [([1, 2], "believes an agreed trial balance proves accuracy"),
                  ([2, 3], "rejects the trial balance's summarising role and accepts the accuracy myth"),
                  ([1, 2, 3], "accepts the accuracy myth")],
         ["Statement 1 is true: TB lists ledger balances before statements are drawn.",
          "Statement 2 is false: errors of omission, principle, compensating and wrong-account errors do not disturb agreement.",
          "Statement 3 is true: special journals are books of original entry."],
         "An agreed trial balance proves only arithmetical accuracy of posting totals.")

    # ---------------- Users and objectives ----------------
    B.add(micro=S("users-and-objectives"), level="L1",
          stem="According to the Conceptual Framework for Financial Reporting under Ind AS, the primary users of general purpose financial reports are:",
          correct="Existing and potential investors, lenders and other creditors",
          wrongs=[("Management and the board of directors of the reporting entity", "management can obtain internal information directly"),
                  ("Tax authorities, sectoral regulators and government agencies", "regulators may use reports but are not the primary users"),
                  ("Employees, trade unions and members of the general public", "secondary users; not the primary user group")],
          steps=["The Framework identifies providers of resources — investors, lenders and other creditors — as primary users.",
                 "They cannot require entities to provide information directly and must rely on general purpose reports."],
          formula="Objective of general purpose financial reporting", trap="Management is an internal user and not the target of GPFR.",
          kind="conceptual", ref="Conceptual Framework for Financial Reporting under Ind AS, Chapter 1")

    match(B, S("users-and-objectives"), "L2", "Match each user of accounting information with its principal information need:",
          ["Trade creditors", "Long-term lenders", "Equity investors", "Income-tax authorities"],
          ["Ability to pay amounts within the short credit period", "Assessment of taxable income",
           "Long-run solvency and interest-servicing capacity", "Return, risk and dividend capacity"],
          [1, 3, 4, 2],
          [([3, 1, 4, 2], "interchanges short-term liquidity with long-term solvency"),
           ([1, 3, 2, 4], "interchanges investors' and tax authorities' needs"),
           ([4, 3, 1, 2], "treats creditors as return-seeking investors")],
          ["Creditors: short-term liquidity.", "Lenders: solvency and coverage.", "Investors: return and risk.", "Tax: taxable income."],
          "Creditors and lenders both assess repayment but over different horizons.")

    # ---------------- Qualitative characteristics ----------------
    B.add(micro=S("qualitative-characteristics"), level="L1",
          stem="Which of the following is a FUNDAMENTAL qualitative characteristic of useful financial information under the Conceptual Framework?",
          correct="Faithful representation",
          wrongs=[("Comparability", "an enhancing characteristic"),
                  ("Timeliness", "an enhancing characteristic"),
                  ("Verifiability", "an enhancing characteristic")],
          steps=["Fundamental: relevance (with materiality) and faithful representation.",
                 "Enhancing: comparability, verifiability, timeliness, understandability."],
          formula="QC hierarchy", trap="Comparability matters a lot but is only enhancing.", kind="conceptual",
          ref="Conceptual Framework for Financial Reporting under Ind AS, Chapter 2")

    stmt(B, S("qualitative-characteristics"), "L2", "Consider the following statements:",
         ["Materiality is an entity-specific aspect of relevance.",
          "Timeliness is a fundamental qualitative characteristic.",
          "A perfectly faithful representation would be complete, neutral and free from error."],
         [1, 3], [([1, 2], "treats timeliness as fundamental"), ([2, 3], "denies materiality's link to relevance"),
                  ([1, 2, 3], "treats timeliness as fundamental")],
         ["Materiality depends on the nature/magnitude of items in the context of the entity — part of relevance.",
          "Timeliness is enhancing, not fundamental.", "Completeness, neutrality and freedom from error define faithful representation."],
         "Enhancing characteristics cannot make irrelevant or unfaithful information useful.")

    # ---------------- Concepts ----------------
    match(B, S("going-concern"), "L2", "Match the accounting practice with the concept that primarily justifies it:",
          ["Closing stock valued at lower of cost and net realisable value", "Outstanding wages of March charged to March's profit and loss",
           "Same depreciation method used year after year", "Fixed assets carried at cost less depreciation, not break-up value"],
          ["Consistency", "Going concern", "Conservatism (prudence)", "Matching"],
          [3, 4, 1, 2],
          [([4, 3, 1, 2], "interchanges prudence and matching"),
           ([3, 4, 2, 1], "interchanges consistency and going concern"),
           ([2, 4, 1, 3], "links NRV write-down to going concern")],
          ["LCNRV anticipates losses but not gains — prudence.", "Accrued wages are matched to the period's revenue.",
           "Consistency requires the same policy across periods.", "Going concern justifies historical cost rather than liquidation value."],
          "The lower-of-cost-and-NRV rule is the textbook conservatism example.")

    ar(B, S("going-concern"), "L3",
       "Insurance premium paid on 1 January 2026 for the year ending 31 December 2026 is partly shown as a prepaid asset in the balance sheet at 31 March 2026.",
       "The matching concept requires costs to be recognised as expenses in the period in which the related benefit is consumed.",
       "both_explains",
       ["Only three months' cover (Jan–Mar) is consumed by 31 March; nine months' premium relates to the next year.",
        "Matching/accrual requires the unexpired portion to be carried forward — so R explains A."],
       "Payment in cash does not decide the period of expense recognition.")

    # ---------------- Accrual vs cash ----------------
    cash_rec, od, cd = 840000, 120000, 95000
    rev = cash_rec - od + cd
    sal_paid, sal_prev, sal_os, sal_adv = 360000, 30000, 36000, 12000
    exp = sal_paid - sal_prev + sal_os - sal_adv
    acc_p, cash_p = rev - exp, cash_rec - sal_paid
    assert (rev, exp, acc_p) == (815000, 354000, 461000)
    B.add(micro=S("accrual-vs-cash"), level="L3",
          stem=("A consultancy (all revenue on credit; salary is its only expense) gives these data for FY 2025-26:\n\n" +
                table(["Item", "₹"], [["Cash collected from clients", inr(cash_rec)], ["Receivables, 1 April 2025", inr(od)],
                                      ["Receivables, 31 March 2026", inr(cd)], ["Salary paid in cash", inr(sal_paid)],
                                      ["— of which relates to FY 2024-25 (outstanding then)", inr(sal_prev)],
                                      ["— of which is advance for April 2026", inr(sal_adv)],
                                      ["Salary outstanding at 31 March 2026", inr(sal_os)]]) +
                "\n\nProfit on the accrual basis is:"),
          correct=R(acc_p),
          wrongs=[(R(cash_p), "cash-basis profit reported"),
                  (R((cash_rec + od - cd) - exp), "receivable adjustment reversed"),
                  (R(rev - (sal_paid - sal_prev + sal_os)), "advance salary for next year not excluded")],
          steps=[f"Revenue = {inr(cash_rec)} − {inr(od)} + {inr(cd)} = {inr(rev)}",
                 f"Salary expense = {inr(sal_paid)} − {inr(sal_prev)} + {inr(sal_os)} − {inr(sal_adv)} = {inr(exp)}",
                 f"Accrual profit = {inr(rev)} − {inr(exp)} = {inr(acc_p)}"],
          formula="Accrual revenue = Cash collected − Opening receivables + Closing receivables",
          trap="Both prior-year arrears and next-year advances in the cash paid must be removed.")

    B.add(micro=S("accrual-vs-cash"), level="L1",
          stem="Under Section 128(1) of the Companies Act, 2013, a company's books of account must be kept on:",
          correct="Accrual basis and according to the double entry system",
          wrongs=[("Cash basis or accrual basis at the option of the board", "assumes an option that the Act does not give companies"),
                  ("Accrual basis, with single entry allowed for small companies", "no single-entry relaxation exists"),
                  ("Cash basis, with accrual adjustments at year-end", "hybrid basis not permitted")],
          steps=["Section 128(1) requires books that give a true and fair view, kept on accrual basis and according to the double entry system."],
          formula="Companies Act, 2013 — s.128(1)", trap="Small or one person companies get no cash-basis exemption.",
          kind="conceptual", verify_fact=True, ref="Companies Act, 2013, s.128(1)")

    # ---------------- Capital vs revenue ----------------
    stmt(B, S("capital-vs-revenue"), "L2", "A manufacturer incurs the following. Which of them are capital expenditure?",
         ["Replacement of a worn-out belt that merely restores the machine's original efficiency.",
          "Legal fees and stamp duty paid on acquiring a factory site.",
          "Cost of training operators to run a newly installed machine.",
          "Wages paid to own employees for installing the new machine."],
         [2, 4], [([1, 2, 4], "treats routine replacement (repairs) as capital"),
                  ([2, 3, 4], "capitalises staff training"),
                  ([2], "misses that installation wages are directly attributable")],
         ["1: maintains, does not enhance — revenue.", "2: directly attributable to acquiring land — capital.",
          "3: training costs are excluded from the cost of PPE — revenue.", "4: installation labour is directly attributable — capital."],
         "Directly attributable costs of bringing an asset to working condition are capitalised; training is not.",
         question="Select the correct answer:")

    lp, td, gst, frt, inst, trial, samp, train, admin, oploss = 1200000, 0.05, 0.18, 35000, 48000, 22000, 7000, 18000, 25000, 30000
    price = lp * (1 - td)
    cost_m = price + frt + inst + (trial - samp)
    assert cost_m == 1238000
    B.add(micro=S("capital-vs-revenue"), level="L3",
          stem=("Tarang Ltd bought a machine. Details:\n\n" +
                table(["Item", "₹"], [["List price", inr(lp)], [f"Trade discount", pct(td) + " of list price"],
                                      ["GST @18% on invoice (full input tax credit available)", inr(price * gst)],
                                      ["Freight inward", inr(frt)], ["Installation", inr(inst)],
                                      ["Cost of trial run", inr(trial)], ["Sale proceeds of samples produced in trial run", inr(samp)],
                                      ["Operator training", inr(train)], ["General administration overhead allocated", inr(admin)],
                                      ["Initial operating loss before demand built up", inr(oploss)]]) +
                "\n\nThe amount to be capitalised is:"),
          correct=R(cost_m),
          wrongs=[(R(cost_m + price * gst), "recoverable GST included in cost"),
                  (R(cost_m + train + admin), "training and administration overheads capitalised"),
                  (R(cost_m + lp * td), "trade discount not deducted")],
          steps=[f"Net price = {inr(lp)} × (1 − {pct(td)}) = {inr(price)}",
                 f"Add freight {inr(frt)}, installation {inr(inst)}, net trial-run cost {inr(trial)} − {inr(samp)} = {inr(trial-samp)}",
                 f"Cost = {inr(cost_m)}; GST with full ITC, training, admin OH and initial losses are excluded"],
          formula="Cost = Purchase price (net of trade discounts, recoverable taxes) + directly attributable costs",
          trap="Recoverable taxes and initial operating losses are never part of asset cost.",
          ref="AS 10 / Ind AS 16 — elements of cost")

    # ---------------- Rectification ----------------
    B.add(micro=S("rectification"), level="L1",
          stem="Purchase of office furniture for ₹40,000 was debited to Purchases Account. This is an error of:",
          correct="Principle",
          wrongs=[("Commission", "commission errors are wrong account of the same class"),
                  ("Omission", "the transaction was recorded"),
                  ("Compensation", "no offsetting error exists")],
          steps=["Capital expenditure recorded as revenue expenditure violates accounting principles.",
                 "Does not affect agreement of the trial balance."],
          formula="Classification of errors", trap="Wrong class of account (capital vs revenue) = error of principle.", kind="conceptual")

    stmt(B, S("rectification"), "L2", "Which of the following errors will NOT affect the agreement of the trial balance?",
         ["Credit sale of ₹7,500 to Asha entirely omitted from the books.",
          "Wages of ₹9,000 paid for installing a machine debited to Wages Account.",
          "Total of the sales book carried forward as ₹1,24,500 instead of ₹1,25,400.",
          "Cash received from Bala ₹3,000 credited to Balu's account."],
         [1, 2, 4], [([1, 2], "misses that a wrong personal account (commission) leaves the TB in agreement"),
                     ([1, 2, 3, 4], "treats a casting/carry-forward error as two-sided"),
                     ([2, 3, 4], "believes total omission disturbs the TB")],
         ["1: complete omission — no debit, no credit.", "2: error of principle — both sides still equal.",
          "3: one-sided (sales credited short by ₹900) — disturbs TB.", "4: wrong account on the correct side — no effect."],
         "Only one-sided errors (casting, carry-forward, single posting) disturb the TB.",
         question="Select the correct answer:")

    rp, gw, rep, dep_r, sr, cs = 240000, 6000, 15000, 0.10, 4000, 3000
    corr_p = rp + gw - rep + rep * dep_r - 2 * sr - cs
    assert corr_p == 221500
    B.add(micro=S("rectification"), level="L3",
          stem=(f"After closing the books, Suraj & Co. (reported net profit {R(rp)}) finds:\n\n"
                f"1. Goods costing {R(gw)} taken by the proprietor were not recorded at all.\n"
                f"2. Repairs to machinery of {R(rep)} were debited to Machinery Account, which was depreciated at {pct(dep_r,0)} for the full year.\n"
                f"3. Returns inward of {R(sr)} were recorded in the purchases returns book.\n"
                f"4. Closing stock was overcast by {R(cs)}.\n\nThe corrected net profit is:"),
          correct=R(corr_p),
          wrongs=[(R(corr_p - rep * dep_r), "depreciation charged on repairs not written back"),
                  (R(corr_p + sr), "returns error treated as a single-sided ₹4,000 effect"),
                  (R(corr_p - 2 * gw), "goods withdrawal treated as reducing profit")],
          steps=[f"(1) Credit purchases {inr(gw)} on recording drawings → profit +{inr(gw)}",
                 f"(2) Charge repairs −{inr(rep)}, write back depreciation +{inr(rep*dep_r)}",
                 f"(3) Purchases returns overstated (profit +{inr(sr)}) and sales returns omitted (profit +{inr(sr)}) → −{inr(2*sr)}",
                 f"(4) Stock overcast → −{inr(cs)}",
                 f"Corrected = {inr(rp)} + {inr(gw)} − {inr(rep)} + {inr(rep*dep_r)} − {inr(2*sr)} − {inr(cs)} = {inr(corr_p)}"],
          formula="Corrected profit = Reported profit ± effect of each error on nominal accounts",
          trap="Recording returns inward as returns outward doubles the error.")

    # ---------------- Case set C1: suspense ----------------
    g = "ACC-C1-KAVERI"
    s_uc, mo_act, mo_post, da, repb, rent, np0 = 5000, 8400, 4800, 1200, 2500, 7000, 186000
    crshort = s_uc + (mo_act - mo_post)
    drshort = 2 * da
    susp = crshort - drshort
    assert susp == 6200
    case = (f"**Case — Kaveri Traders.** The trial balance at 31 March 2026 did not agree and the difference was placed in a suspense account. "
            f"A draft net profit of {R(np0)} was computed. Later the following were found:\n\n"
            f"(a) The sales day book was undercast by {R(s_uc)}.\n"
            f"(b) A credit purchase of {R(mo_act)} from Mohan was correctly entered in the purchases book but posted to Mohan's account as {R(mo_post)}.\n"
            f"(c) Discount allowed of {R(da)} to a customer was posted to the credit side of Discount Account (the customer's account was correctly credited).\n"
            f"(d) Repairs of {R(repb)} were debited to Building Account.\n"
            f"(e) Rent of {R(rent)} paid in cash was omitted from the books altogether.\n\n")
    B.add(micro=S("rectification"), level="L4", group=g,
          stem=case + "The balance originally placed in the suspense account was:",
          correct=f"{R(susp)} credit",
          wrongs=[(f"{R(susp)} debit", "side reversed: debit total was the larger"),
                  (f"{R(crshort - da)} credit", "wrong-side posting treated as a single ₹1,200 effect"),
                  (f"{R(crshort + drshort)} credit", "shortfalls on both sides added instead of netted")],
          steps=[f"Credit side short: (a) {inr(s_uc)} + (b) {inr(mo_act-mo_post)} = {inr(crshort)}",
                 f"Debit side short: (c) posted to wrong side → 2 × {inr(da)} = {inr(drshort)}",
                 f"Net: debits exceed credits by {inr(susp)} → suspense credited {inr(susp)}",
                 "(d) and (e) do not affect the trial balance."],
          formula="Suspense = net one-sided difference", trap="Posting to the wrong side creates double the amount.")
    np1 = np0 + s_uc - drshort - repb - rent
    assert np1 == 179100
    B.add(micro=S("rectification"), level="L4", group=g,
          stem=case + "The corrected net profit is:",
          correct=R(np1),
          wrongs=[(R(np0 + s_uc - da - repb - rent), "discount correction taken as ₹1,200 only"),
                  (R(np0 + s_uc - drshort - rent), "repairs debited to building treated as having no profit effect"),
                  (R(np0 - s_uc - drshort - repb - rent), "sales undercasting treated as reducing profit")],
          steps=[f"(a) +{inr(s_uc)}; (b) no effect (personal account); (c) −{inr(drshort)}; (d) −{inr(repb)}; (e) −{inr(rent)}",
                 f"Corrected = {inr(np0)} + {inr(s_uc)} − {inr(drshort)} − {inr(repb)} − {inr(rent)} = {inr(np1)}"],
          formula="Corrected profit = draft profit ± nominal-account corrections", trap="Errors in personal accounts do not touch profit.")
    stmt(B, S("rectification"), "L4",
         case + "Consider the following statements:",
         ["Error (d) is an error of principle.", "Error (e) disturbs the agreement of the trial balance.",
          "Error (b) is an error of commission."],
         [1, 3], [([1, 2], "believes a complete omission affects the TB"), ([2, 3], "misclassifies (d)"),
                  ([1, 2, 3], "believes a complete omission affects the TB")],
         ["(d) revenue expense capitalised — principle.", "(e) complete omission — no effect on TB.",
          "(b) wrong amount posted in a personal account — commission."],
         "Omission of a whole transaction never disturbs the TB.", group=g)
    B.add(micro=S("rectification"), level="L4", group=g,
          stem=case + "The rectifying entry for error (c) is:",
          correct=f"Discount Allowed A/c Dr {R(drshort)} To Suspense A/c {R(drshort)}",
          wrongs=[(f"Discount Allowed A/c Dr {R(da)} To Suspense A/c {R(da)}", "only the missing debit corrected, wrong credit left"),
                  (f"Suspense A/c Dr {R(drshort)} To Discount Allowed A/c {R(drshort)}", "direction reversed"),
                  (f"Discount Allowed A/c Dr {R(da)} To Customer A/c {R(da)}", "customer credited twice")],
          steps=["Discount account shows a credit of ₹1,200 where a debit of ₹1,200 was needed.",
                 f"Debit discount by {inr(drshort)} to cancel and replace; the other side is suspense."],
          formula="Wrong side posting → rectify with twice the amount", trap="The customer's account was already correct.")

    # ---------------- Bills of exchange ----------------
    B.add(micro=S("bills-of-exchange"), level="L2",
          stem="A bill dated 31 January 2026 is payable one month after date. Assuming no public holiday intervenes, its date of maturity is:",
          correct="3 March 2026",
          wrongs=[("28 February 2026", "days of grace ignored"),
                  ("6 March 2026", "rolled the non-existent 31 February forward to 3 March and then added grace"),
                  ("2 March 2026", "grace days counted inclusive of the nominal due date")],
          steps=["One month after 31 January: February has no 31st, so the nominal due date is the last day, 28 February 2026.",
                 "Add three days of grace: 3 March 2026."],
          formula="Maturity = nominal due date + 3 days of grace (NI Act ss.22–23)",
          trap="If the month has no corresponding day, the last day of the month is taken.",
          kind="numerical", verify_fact=True, ref="Negotiable Instruments Act, 1881, ss.22–23")

    bills = [(6000, 0), (9000, 15), (5000, 40)]
    tot = sum(a for a, _ in bills)
    prod = sum(a * d for a, d in bills)
    avg_days = prod / tot
    assert abs(avg_days - 16.75) < 1e-9
    B.add(micro=S("bills-of-exchange"), level="L3",
          stem=("Anand accepted three bills drawn by Balan:\n\n" +
                table(["Bill", "Amount (₹)", "Due date"], [["1", inr(6000), "10 March 2026"], ["2", inr(9000), "25 March 2026"],
                                                            ["3", inr(5000), "19 April 2026"]]) +
                "\n\nHe wishes to pay all bills on one date without loss of interest to either side. The average due date (rounded to the nearest day) is:"),
          correct="27 March 2026",
          wrongs=[("28 March 2026", "simple average of days used (amounts not weighted)"),
                  ("26 March 2026", "fraction of a day truncated instead of rounded"),
                  ("25 March 2026", "due date of the largest bill taken")],
          steps=["Base date 10 March. Days: 0, 15, 40.",
                 f"Products: 0 + 1,35,000 + 2,00,000 = {inr(prod)}",
                 f"Average = {inr(prod)} ÷ {inr(tot)} = {avg_days:.2f} ≈ 17 days → 27 March 2026"],
          formula="Average due date = Base date + Σ(amount × days) ÷ Σ amount",
          trap="Weight by amount; round a fraction ≥ 0.5 up.")

    fv, disc_p, noting = 20000, 19600, 100
    B.add(micro=S("bills-of-exchange"), level="L2",
          stem=(f"Pooja discounted Kiran's acceptance of {R(fv)} with her bank for {R(disc_p)}. On maturity the bill was dishonoured and "
                f"the bank paid noting charges of {R(noting)}. Pooja's entry on dishonour is:"),
          correct=f"Kiran A/c Dr {R(fv+noting)} To Bank A/c {R(fv+noting)}",
          wrongs=[(f"Kiran A/c Dr {R(disc_p+noting)} To Bank A/c {R(disc_p+noting)}", "discounted proceeds used instead of face value"),
                  (f"Kiran A/c Dr {R(fv+noting)} To Bills Receivable A/c {R(fv+noting)}", "bill treated as still held, though it was discounted"),
                  (f"Kiran A/c Dr {R(fv)} To Bank A/c {R(fv)}", "noting charges not recovered from the acceptor")],
          steps=["The bank recovers full face value plus noting charges from Pooja.",
                 "Pooja charges Kiran the same, since the bill left her books when discounted."],
          formula="Dishonour of discounted bill: Drawee Dr; To Bank (face value + noting)",
          trap="Discount already borne is a finance cost; it is not reduced from the claim.")

    # ---------------- Software and XBRL ----------------
    B.add(micro=S("accounting-software"), level="L1",
          stem="In XBRL reporting, the electronic dictionary that defines the elements (tags) and their relationships used in financial statements is called the:",
          correct="Taxonomy",
          wrongs=[("Instance document", "the instance document carries the reported values"),
                  ("Style sheet", "style sheets only format presentation"),
                  ("General ledger chart of accounts", "an internal ledger structure, not the reporting dictionary")],
          steps=["XBRL = eXtensible Business Reporting Language.",
                 "Taxonomy: the definitions; instance document: the facts tagged with those definitions."],
          formula="XBRL architecture", trap="Values live in the instance document; meanings live in the taxonomy.", kind="conceptual")

    stmt(B, S("accounting-software"), "L2",
         "Under Rule 3 of the Companies (Accounts) Rules, 2014 (as amended), for books of account kept in electronic mode:",
         ["Back-up of books must be kept on servers physically located in India on a daily basis.",
          "Accounting software must have an audit-trail (edit log) feature that cannot be disabled.",
          "Back-up is required only at the end of each quarter."],
         [1, 2], [([1, 3], "retains the superseded periodic back-up idea"), ([2, 3], "denies daily back-up"),
                  ([1, 2, 3], "accepts contradictory statements 1 and 3")],
         ["The 2022 amendment made back-up in India a daily requirement.",
          "Audit trail with edit log that cannot be disabled applies from FY 2023-24.",
          "Statement 3 contradicts the daily back-up requirement."],
         "Periodic back-up was the old rule; it is now daily.", verify_fact=True,
         ref="Companies (Accounts) Rules, 2014 — Rule 3(1) and 3(5) as amended in 2021/2022")

    stmt(B, S("accounting-software"), "L3",
         "Under the Companies (Filing of Documents and Forms in XBRL) Rules, 2015, consider these companies (none is a banking company, insurance company or housing finance company, and none is required to follow Ind AS, unless stated):",
         ["P Ltd, unlisted, paid-up capital ₹3 crore, turnover ₹120 crore, must file financial statements in XBRL.",
          "Q Ltd, unlisted and not required to follow Ind AS, paid-up capital ₹4 crore, turnover ₹80 crore, must file in XBRL.",
          "R Ltd, a non-banking financial company with paid-up capital ₹20 crore, is excluded from XBRL filing."],
         [1, 3], [([1, 2], "applies XBRL to a company below both thresholds"),
                  ([2, 3], "reads the paid-up and turnover thresholds as cumulative"),
                  ([1], "misses the NBFC exclusion")],
         ["Rule 3 classes (any one): listed companies and their Indian subsidiaries; paid-up capital ≥ ₹5 crore; turnover ≥ ₹100 crore; companies required to prepare financial statements under Ind AS.",
          "P: turnover ≥ ₹100 crore → covered. Q: below both thresholds, unlisted and not an Ind AS company → not covered.",
          "Excluded: banking companies, insurance companies, NBFCs and housing finance companies (power companies are not excluded)."],
         "The thresholds are alternatives, not cumulative.", verify_fact=True,
         ref="Companies (Filing of Documents and Forms in XBRL) Rules, 2015, Rule 3 (classes (i)–(iv) and exempted companies)")

    # ---------------- Applicability framework ----------------
    B.add(micro=S("applicability-framework"), level="L2",
          stem=("Under the Companies (Accounting Standards) Rules, 2021, which of the following unlisted companies (none a bank, insurer or "
                "FI, and none part of a larger group) qualifies as a Small and Medium-sized Company (SMC) for the current year? Turnover (excluding other income) is for the immediately preceding accounting year; borrowings are the maximum outstanding at any time in that year."),
          correct="Turnover ₹240 crore; borrowings ₹48 crore",
          wrongs=[("Turnover ₹240 crore; borrowings ₹55 crore", "borrowing limit of ₹50 crore exceeded"),
                  ("Turnover ₹260 crore; borrowings ₹20 crore", "turnover limit of ₹250 crore exceeded"),
                  ("Turnover ₹60 crore; borrowings ₹5 crore, but the company has filed a draft offer document for listing", "a company in the process of listing is not an SMC")],
          steps=["SMC: not listed or in process of listing; not a bank/FI/insurer; turnover (excluding other income) ≤ ₹250 crore in the immediately preceding accounting year; borrowings ≤ ₹50 crore at any time in that year; not a holding/subsidiary of a non-SMC.",
                 "Only the first option satisfies all conditions."],
          formula="SMC criteria (Rule 2(1)(e), 2021 Rules)", trap="Both limits must be met, and 'in process of listing' disqualifies.",
          kind="conceptual", verify_fact=True, ref="Companies (Accounting Standards) Rules, 2021, Rule 2(1)(e)")

    stmt(B, S("applicability-framework"), "L2", "With reference to the Companies (Indian Accounting Standards) Rules, 2015:",
         ["An unlisted company with net worth of ₹280 crore is required to follow Ind AS.",
          "A company that has voluntarily adopted Ind AS may revert to AS if its net worth later falls below the threshold.",
          "Holding, subsidiary, joint venture and associate companies of a company covered by Ind AS must also follow Ind AS."],
         [1, 3], [([1, 2], "believes Ind AS adoption is reversible"), ([2, 3], "misses the ₹250 crore net-worth trigger"),
                  ([1, 2, 3], "believes Ind AS adoption is reversible")],
         ["Unlisted companies with net worth ≥ ₹250 crore are covered.", "Once adopted, Ind AS must be followed thereafter.",
          "Group companies of a covered company are covered."],
         "Ind AS adoption is irreversible.", verify_fact=True, ref="Companies (Ind AS) Rules, 2015, Rule 4")

    B.add(micro=S("applicability-framework"), level="L1",
          stem="Under the Companies (Accounting Standards) Rules, 2021, a Small and Medium-sized Company is exempt from applying which of the following standards in full?",
          correct="AS 17 — Segment Reporting",
          wrongs=[("AS 2 — Valuation of Inventories", "AS 2 applies to all companies"),
                  ("AS 10 — Property, Plant and Equipment", "AS 10 applies to all companies (with no relaxation in full)"),
                  ("AS 9 — Revenue Recognition", "AS 9 applies to all companies")],
          steps=["AS 17 (Segment Reporting) is not applicable to SMCs.",
                 "AS 2, AS 9 and AS 10 apply to all companies."],
          formula="SMC exemptions", trap="Full exemption for SMCs is AS 17; other reliefs (AS 15, AS 19, AS 20, AS 28, AS 29) are partial.",
          kind="conceptual", verify_fact=True, ref="Companies (AS) Rules, 2021 — AS 17 applicability to SMCs")

    # ---------------- Convergence ----------------
    B.add(micro=S("as-vs-ind-as"), level="L1",
          stem="Under Ind AS 40 as notified in India, investment property is measured after initial recognition using:",
          correct="The cost model only, with fair value disclosed",
          wrongs=[("Either the cost model or the fair value model", "IFRS (IAS 40) position; India carved out the fair value model"),
                  ("The fair value model only", "reverse of the Indian carve-out"),
                  ("The revaluation model with surplus to OCI", "revaluation model belongs to Ind AS 16, not Ind AS 40")],
          steps=["Ind AS 40 permits only the cost model; fair value must be disclosed."],
          formula="Ind AS 40 subsequent measurement", trap="A classic Ind AS vs IFRS carve-out.", kind="conceptual",
          verify_fact=True, ref="Ind AS 40, paragraph 30 (Indian carve-out)")

    stmt(B, S("as-vs-ind-as"), "L2", "Consider the following comparisons between AS and Ind AS:",
         ["AS 5 requires separate disclosure of extraordinary items, whereas Ind AS 1 prohibits presenting any item as extraordinary.",
          "Under Ind AS 103 as notified in India, a gain on bargain purchase is recognised in OCI and accumulated in equity as capital reserve (where the reason is clear).",
          "Ind AS 16 does not permit the revaluation model for property, plant and equipment."],
         [1, 2], [([1, 3], "believes Ind AS 16 bans revaluation"), ([2, 3], "denies the extraordinary item difference"),
                  ([1, 2, 3], "believes Ind AS 16 bans revaluation")],
         ["1 true.", "2 true — Indian carve-out from IFRS 3's P&L treatment.", "3 false — Ind AS 16 allows cost or revaluation model."],
         "Revaluation is banned for investment property (Ind AS 40), not for PPE.", verify_fact=True,
         ref="AS 5; Ind AS 1 para 87; Ind AS 103 para 34/36A; Ind AS 16 para 29")

    ar(B, S("as-vs-ind-as"), "L3",
       "Under AS, proposed dividends declared after the reporting date are not recognised as a liability at the reporting date, which now matches Ind AS 10.",
       "The 2016 revision of AS 4 aligned the treatment of proposed dividends with the principle that no present obligation exists at the balance sheet date.",
       "both_explains",
       ["Revised AS 4 (2016) requires dividends proposed/declared after the balance sheet date to be disclosed in notes, not provided.",
        "Ind AS 10 has the same rule because no obligation exists until declared. R explains A."],
       "Pre-2016 AS 4 required a provision for proposed dividend — an outdated rule.",
       verify_fact=True, ref="AS 4 (revised 2016) para 8.5; Ind AS 10 para 12")
