"""Part 1: dividends (s.123/124/125/127), CSR (s.135), Schedules."""
from cab_common import *  # noqa


def add_all(B):
    # ------------------------------------------------------------------ s.123
    B.add(M["s123"], "L1",
          "Under section 123 of the Companies Act, 2013, which of the following is NOT a permissible source for declaring dividend?",
          "Balance in the securities premium account",
          [("Profits of the current financial year arrived at after providing for depreciation under Schedule II", "permitted source under s.123(1)(a)"),
           ("Undistributed profits of earlier years arrived at after providing for depreciation", "permitted source under s.123(1)(b)"),
           ("Money provided by the Central or a State Government for payment of dividend in pursuance of a guarantee", "permitted source under s.123(1)(c)")],
          ["s.123(1) permits dividend only out of (a) current-year profits after depreciation, (b) undistributed past profits after depreciation, (c) both, or government money under a guarantee.",
           "Securities premium can be applied only for the purposes listed in s.52(2) — distribution as dividend is not one of them."],
          "s.123(1) sources; s.52(2) applications of securities premium",
          "Securities premium is a capital receipt; it can fund bonus shares but never a cash dividend.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.123(1); s.52(2)")

    pbd, dep, fv, bfl, arr = 9.60e7, 2.10e7, 0.45e7, 1.25e7, 0.30e7
    ans = pbd - dep - fv - bfl - arr
    assert round(ans) == 5.50e7
    B.add(M["s123"], "L3",
          "Pranav Castings Ltd reports the following for FY 2025-26 (all figures after tax):\n\n"
          + table(["Item", "₹ crore"], [
              ["Profit for the year before depreciation", "9.60"],
              ["Depreciation for the year as per Schedule II", "2.10"],
              ["Unrealised fair-value gain on investments included in the profit above", "0.45"],
              ["Loss brought forward from earlier years", "1.25"],
              ["Depreciation of an earlier year not provided in that year", "0.30"]], ["---", "---:"])
          + "\n\nThe maximum amount out of FY 2025-26 profits that can be distributed as dividend under s.123 is:",
          cr(ans),
          [(cr(ans + fv), "unrealised fair-value gain not excluded"),
           (cr(pbd - dep - fv), "brought-forward loss and arrear depreciation not set off"),
           (cr(pbd - fv - bfl - arr), "current-year Schedule II depreciation not deducted")],
          [f"Start: profit before depreciation {cr(pbd)}; deduct Schedule II depreciation {cr(dep)}.",
           f"Exclude unrealised/notional fair-value gain {cr(fv)} (first proviso to s.123(1)).",
           f"Set off carried-over loss {cr(bfl)} and depreciation not provided earlier {cr(arr)} (third proviso).",
           f"Distributable = {cr(ans)}."],
          "Distributable = Profit − Sch II depreciation − unrealised gains − b/f losses − arrear depreciation",
          "All three adjustments are mandatory; transfer to reserves is optional and does not reduce the ceiling.",
          verify_fact=True, ref="Companies Act 2013 s.123(1) and its provisos")

    pu, fr, loss = 40e7, 25e7, 1.5e7
    rates = [0.12, 0.15, 0.09]
    avg = sum(rates) / 3
    prop = 0.14
    cap_draw = (pu + fr) / 10
    floor_bal = 0.15 * pu
    max_div = min(avg * pu, cap_draw - loss, fr - floor_bal - loss)
    assert round(max_div) == 4.8e7
    B.add(M["s123"], "L3",
          f"Hemadri Mills Ltd has incurred a loss of {cr(loss)} in FY 2026-27 and proposes to declare an equity dividend of {pct(prop,0)} out of accumulated profits (free reserves). Latest audited figures: paid-up equity capital {cr(pu)}, free reserves {cr(fr)}. Dividend rates for the three immediately preceding years were 12%, 15% and 9%. Under Rule 3 of the Companies (Declaration and Payment of Dividend) Rules, 2014, the maximum equity dividend that can be declared is:",
          cr(max_div),
          [(cr(prop * pu), "proposed 14% rate not capped at the three-year average"),
           (cr(cap_draw - loss), "only the one-tenth withdrawal cap applied; average-rate cap ignored"),
           (cr(cap_draw), "one-tenth cap used without first setting off the current-year loss")],
          [f"Average of preceding three years' rates = {pct(avg)} → dividend cap {cr(avg*pu)}.",
           f"Withdrawal cap = 1/10 × ({cr(pu)} + {cr(fr)}) = {cr(cap_draw)}; first {cr(loss)} must absorb the current loss → {cr(cap_draw-loss)} available.",
           f"Reserves after withdrawal must stay ≥ 15% of paid-up = {cr(floor_bal)}; not binding here.",
           f"Maximum = lowest of the caps = {cr(max_div)}."],
          "Rule 3: rate ≤ 3-yr average; draw ≤ 1/10 (PUC + FR); loss set off first; residual reserves ≥ 15% PUC",
          "The average-rate cap is on the rate; the one-tenth cap is on the total withdrawal including loss set-off.",
          verify_fact=True, ref="Companies (Declaration and Payment of Dividend) Rules 2014, Rule 3; s.123(1) second proviso")

    pu, fr, loss, avg = 50e7, 10e7, 2e7, 0.10
    cap_draw = (pu + fr) / 10
    floor_draw = fr - 0.15 * pu
    draw = min(cap_draw, floor_draw)
    max_div = min(avg * pu, draw - loss)
    assert round(max_div) == 0.5e7
    B.add(M["s123"], "L3",
          f"Tapti Glass Ltd (paid-up equity {cr(pu)}; free reserves as per latest audited balance sheet {cr(fr)}) has a current-year loss of {cr(loss)}. The average dividend rate of the three preceding years is 10%. Applying all conditions of Rule 3 of the Companies (Declaration and Payment of Dividend) Rules, 2014, the maximum equity dividend it can declare out of free reserves is:",
          cr(max_div),
          [(cr(cap_draw - loss), "15%-of-paid-up residual reserve floor ignored"),
           (cr(avg * pu), "only the average-rate cap applied"),
           (cr(floor_draw), "current-year loss not set off before equity dividend")],
          [f"One-tenth cap on withdrawal = 1/10 × {cr(pu+fr)} = {cr(cap_draw)}.",
           f"Residual reserves must be ≥ 15% × {cr(pu)} = {cr(0.15*pu)} → withdrawal ≤ {cr(fr)} − {cr(0.15*pu)} = {cr(floor_draw)} (binding).",
           f"Out of {cr(draw)} withdrawn, {cr(loss)} first sets off the current loss → {cr(max_div)} for dividend.",
           f"Average-rate cap ({cr(avg*pu)}) is not binding."],
          "Max withdrawal = min[1/10 (PUC+FR), FR − 15% PUC]; dividend = withdrawal − current loss (≤ avg-rate cap)",
          "Candidates stop at the one-tenth cap; the 15% floor is the binding constraint when reserves are thin.",
          verify_fact=True, ref="Companies (Declaration and Payment of Dividend) Rules 2014, Rule 3(2)-(4)")

    r3 = [0.20, 0.25, 0.30]
    B.add(M["s123"], "L2",
          "Sona Tiles Ltd paid dividends of 20%, 25% and 30% in the three immediately preceding financial years. For the current year it has incurred a loss up to the end of the quarter immediately preceding the Board meeting at which an interim dividend is to be declared. The Board wants to declare 32%. The maximum rate of interim dividend permissible is:",
          pct(sum(r3) / 3, 0),
          [("30%", "latest year's rate taken as the cap"),
           ("20%", "lowest of the three rates taken as the cap"),
           ("32%", "assumes interim dividend out of surplus is not capped")],
          ["s.123(3) proviso: where the company has incurred loss during the current FY up to the end of the quarter immediately preceding declaration, interim dividend cannot exceed the average rate of the immediately preceding three FYs.",
           "Average = (20 + 25 + 30) ÷ 3 = 25%."],
          "Interim rate ≤ average of preceding 3 FYs (when loss to preceding quarter-end)",
          "The cap is the simple average, not the latest or lowest rate.",
          verify_fact=True, ref="Companies Act 2013 s.123(3) proviso")

    B.add(M["s123"], "L2",
          stmts("Consider the following statements under the Companies Act, 2013:",
                ["No dividend is payable except in cash, but this does not prohibit capitalisation of profits or reserves for issuing fully paid bonus shares.",
                 "A company may declare dividend out of its revaluation reserve if its articles so permit.",
                 "A company that has failed to repay deposits accepted before or after commencement of the Act, as required by s.73/74, shall not declare dividend on equity shares so long as the failure continues."]),
          "1 and 3 only",
          [("1 only", "misses the s.123(6) bar on dividend while deposit default continues"),
           ("1, 2 and 3", "treats revaluation reserve as distributable"),
           ("2 and 3 only", "believes dividend may be paid in kind")],
          ["Statement 1: s.123(5) — dividend only in cash; proviso preserves bonus capitalisation. Correct.",
           "Statement 2: revaluation gains are excluded from profits and from free reserves (s.2(43)); articles cannot override. Incorrect.",
           "Statement 3: s.123(6) bar. Correct."],
          "s.123(5), s.123(6), s.2(43)", "Articles cannot authorise what the Act prohibits.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.123(5), (6); s.2(43)")

    # ------------------------------------------------------------------ Unpaid Dividend Account s.124(1)
    decl = d(2026, 8, 12)
    due = plus(decl, 30)
    tr = plus(due, 7)
    B.add(M["uda"], "L2",
          f"Kalinga Paper Ltd declared a final dividend at its AGM on {ds(decl)}. Part of the dividend remained unpaid/unclaimed within the statutory payment period. Counting days excluding the day of declaration, the last date by which the unpaid amount must be transferred to the Unpaid Dividend Account is:",
          ds(tr),
          [(ds(due), "treats end of the 30-day payment window as the transfer deadline"),
           (ds(plus(due, 30)), "allows a further 30 days instead of 7"),
           (ds(plus(decl, 7)), "counts 7 days from the date of declaration")],
          [f"Payment window: 30 days from declaration → {ds(due)} (s.127).",
           f"s.124(1): transfer within 7 days from expiry of the 30-day period → {ds(tr)}."],
          "Transfer deadline = Declaration + 30 days + 7 days",
          "The 7 days run from the end of the 30-day window, not from declaration.",
          verify_fact=True, ref="Companies Act 2013 s.124(1)")

    amt, late = 6_00_000, 60
    i12 = interest(amt, 0.12, late)
    B.add(M["uda"], "L2",
          f"Jalpaiguri Teas Ltd transferred {R(amt)} of unpaid dividend to its Unpaid Dividend Account {late} days after the due date for transfer. The interest payable by the company under s.124(2) on the amount for the period of default is (365-day year):",
          R(i12),
          [(R(interest(amt, 0.18, late)), "18% rate of s.127 applied instead of 12%"),
           (R(interest(amt, 0.12, late + 7)), "interest counted from expiry of the 30-day payment window instead of the transfer due date"),
           (R(interest(amt, 0.15, late)), "15% rate (delayed refund of application money) applied")],
          [f"s.124(2): interest @ 12% p.a. from date of default on the amount not transferred.",
           f"Interest = {inr(amt)} × 12% × {late}/365 = {R(i12)}; it accrues to the shareholders in proportion to their unpaid dividend."],
          "Interest = Amount × 12% × days/365", "12% (s.124) vs 18% (s.127) — different defaults, different rates.",
          verify_fact=True, ref="Companies Act 2013 s.124(2)")

    # ------------------------------------------------------------------ s.124 IEPF transfer
    B.add(M["s124"], "L3",
          stmts("Mr Kapoor holds 400 shares of Uttara Chemicals Ltd. The company has declared dividend every year from FY 2017-18. Consider the following situations:",
                ["He did not encash dividends for FY 2017-18 to FY 2023-24 (seven consecutive years); the shares are liable to be transferred to the IEPF.",
                 "He did not encash dividends for FY 2017-18 to FY 2019-20, encashed the FY 2020-21 dividend, and did not encash any dividend thereafter up to FY 2025-26; the shares are liable to be transferred to the IEPF.",
                 "Once shares are transferred to the IEPF, he can claim them back by applying to the IEPF Authority."],
                "Which of the above is/are correct?"),
          "1 and 3 only",
          [("1 only", "believes shares transferred to IEPF can never be reclaimed"),
           ("1, 2 and 3", "counts non-consecutive years towards the seven-year test"),
           ("2 and 3 only", "counts total unclaimed years instead of consecutive years")],
          ["s.124(6): shares in respect of which dividend has not been paid or claimed for seven consecutive years or more are transferred to IEPF.",
           "Situation 2: encashment in FY 2020-21 breaks the run; FY 2021-22 to 2025-26 = 5 consecutive years only.",
           "Proviso to s.124(6) and s.125(3)(a): the claimant may reclaim shares/amounts from the Fund (Form IEPF-5)."],
          "s.124(6) — seven CONSECUTIVE years", "Any intervening encashment restarts the seven-year count.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.124(5), (6); s.125(3)(a); IEPF Rules 2016")

    t0 = d(2019, 10, 16)
    due7 = date(2026, 10, 16)
    B.add(M["s124"], "L2",
          f"Money was transferred to the Unpaid Dividend Account of Rewa Cables Ltd on {ds(t0)} and remains unclaimed. Under s.124(5), the amount (with interest accrued) becomes due for transfer to the Investor Education and Protection Fund after:",
          f"Seven years from the date of transfer, i.e. on {ds(due7)}",
          [(f"Seven years from the date of declaration of the dividend", "counts from declaration instead of transfer to the Unpaid Dividend Account"),
           (f"Three years from the date of transfer, i.e. on {ds(date(2022,10,16))}", "confuses with a three-year limitation period"),
           (f"Ten years from the date of transfer, i.e. on {ds(date(2029,10,16))}", "confuses with the ten-year unclaimed-deposit rule of banking law")],
          ["s.124(5): money in the Unpaid Dividend Account unpaid/unclaimed for 7 years from the date of such transfer is transferred to IEPF with interest accrued.",
           f"7 years from {ds(t0)} = {ds(due7)}."],
          "IEPF due date = Transfer date + 7 years", "The clock starts on transfer to the Unpaid Dividend Account.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.124(5)")

    # ------------------------------------------------------------------ s.125
    B.add(M["s125"], "L1",
          "Which of the following amounts is NOT credited to the Investor Education and Protection Fund constituted under s.125 of the Companies Act, 2013?",
          "Unclaimed balances in savings accounts of banking companies",
          [("Sale proceeds of fractional shares arising from bonus issue or merger remaining unpaid for seven years or more", "listed in s.125(2)"),
           ("Redemption amount of preference shares remaining unpaid or unclaimed for seven years or more", "listed in s.125(2)"),
           ("Application money received for allotment of securities and due for refund", "listed in s.125(2)")],
          ["s.125(2) lists amounts credited to IEPF — unpaid dividend accounts, refundable application money, matured deposits/debentures, fractional-share sale proceeds, unpaid preference redemption amounts, grants, donations etc.",
           "Unclaimed bank deposits go to RBI's Depositor Education and Awareness Fund under the Banking Regulation Act, not to IEPF."],
          "s.125(2) credits", "Do not confuse IEPF (MCA) with DEA Fund (RBI).",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.125(2); BR Act 1949 s.26A")

    B.add(M["s125"], "L2",
          stmts("With reference to utilisation of the Investor Education and Protection Fund under s.125(3), consider:",
                ["Refund in respect of unclaimed dividends, matured deposits, matured debentures and application money due for refund.",
                 "Reimbursement of legal expenses incurred in pursuing class action suits under s.37 and s.245 by members, debenture-holders or depositors as may be sanctioned by the Tribunal.",
                 "Payment of compensation to shareholders for decline in market price of shares of a listed company."]),
          "1 and 2 only",
          [("1 only", "misses class-action reimbursement"),
           ("1, 2 and 3", "treats IEPF as a market-loss compensation fund"),
           ("2 and 3 only", "overlooks refund to claimants as a use")],
          ["s.125(3)(a) refunds to claimants; (b) investor education and protection; (c) distribution of disgorged amounts; (d) reimbursement of class-action legal expenses sanctioned by the Tribunal.",
           "Market-price loss compensation is not a permitted use."],
          "s.125(3) utilisation", "Disgorged amounts may be distributed, but general market losses are not compensated.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.125(3)")

    # ------------------------------------------------------------------ s.127
    amt, late = 48_00_000, 73
    B.add(M["s127"], "L2",
          f"Dhruva Motors Ltd declared a dividend of which {R(amt)} was paid {late} days after the expiry of 30 days from the date of declaration. None of the statutory exceptions applies. The simple interest the company must pay for the period of default under s.127 is (365-day year):",
          R(interest(amt, 0.18, late)),
          [(R(interest(amt, 0.12, late)), "12% rate of s.124(2) applied"),
           (R(interest(amt, 0.18, late + 30)), "interest counted from the date of declaration"),
           (R(interest(amt, 0.15, late)), "15% refund-interest rate applied")],
          ["s.127: dividend not paid within 30 days of declaration → company pays simple interest @ 18% p.a. during the period of default.",
           f"Interest = {inr(amt)} × 18% × {late}/365 = {R(interest(amt,0.18,late))}."],
          "Interest = Amount × 18% × days of default/365",
          "Default begins only after the 30-day window closes.",
          verify_fact=True, ref="Companies Act 2013 s.127")

    B.add(M["s127"], "L3",
          stmts("A company fails to pay a declared dividend within 30 days. Under s.127, no offence is committed where:",
                ["the dividend could not be paid by reason of the operation of any law;",
                 "there is a dispute regarding the right to receive the dividend;",
                 "the dividend has been lawfully adjusted by the company against a sum due to it from the shareholder;",
                 "the company's cash flow was temporarily insufficient."],
                "Which of the above are statutory exceptions?"),
          "1, 2 and 3 only",
          [("1 and 2 only", "misses lawful adjustment against dues"),
           ("1, 2, 3 and 4", "treats liquidity shortage as a defence"),
           ("2, 3 and 4 only", "drops operation of law and adds cash shortage")],
          ["s.127 provisos: (a) operation of law; (b) shareholder's directions that could not be complied with; (c) dispute about right to receive; (d) lawful adjustment; (e) failure not due to default of the company.",
           "Cash shortage is the company's own default — no exception; directors knowingly party face imprisonment up to 2 years and fine ≥ ₹1,000 per day."],
          "s.127 exceptions", "Liquidity problems are precisely what s.127 punishes.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.127 provisos")

    # ------------------------------------------------------------------ CSR
    rows = [("P Ltd", 480, 980, 4.90), ("Q Ltd", 300, 1050, 2.00), ("R Ltd", 520, 400, -1.00), ("S Ltd", 100, 200, 5.00)]
    app = [n for n, nw, to, np_ in rows if nw >= 500 or to >= 1000 or np_ >= 5]
    assert app == ["Q Ltd", "R Ltd", "S Ltd"]
    B.add(M["csr"], "L3",
          "Figures for the immediately preceding financial year (₹ crore):\n\n"
          + table(["Company", "Net worth", "Turnover", "Net profit"], [[n, nw, to, f"{np_:.2f}"] for n, nw, to, np_ in rows], ["---", "---:", "---:", "---:"])
          + "\n\nWhich companies are covered by s.135(1) for the current year?",
          "Q Ltd, R Ltd and S Ltd only",
          [("Q Ltd and S Ltd only", "assumes a loss-making company is outside s.135 even if net worth criterion is met"),
           ("S Ltd only", "applies only the net profit criterion"),
           ("P Ltd, Q Ltd, R Ltd and S Ltd", "treats figures close to the thresholds as meeting them")],
          ["s.135(1): net worth ≥ ₹500 crore OR turnover ≥ ₹1,000 crore OR net profit ≥ ₹5 crore in the immediately preceding FY.",
           "Q: turnover 1,050 ✓; R: net worth 520 ✓ (loss irrelevant for applicability); S: net profit 5.00 ✓ (threshold is 'or more'); P: none met."],
          "Any one of NW ≥ 500 cr / TO ≥ 1,000 cr / NP ≥ 5 cr", "Criteria are alternative; a loss year does not exempt a company meeting another test.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.135(1) (as amended 2021)")

    np3 = [18.40e7, -3.20e7, 22.60e7]
    excess = 4.0e5
    avg = sum(np3) / 3
    ob = 0.02 * avg
    req = ob - excess
    assert round(avg) == 12.60e7 and round(ob) == 25.2e5
    B.add(M["csr"], "L3",
          "Vindhya Pharma Ltd is covered by s.135. Its net profits computed under s.198 for the three immediately preceding financial years were ₹18.40 crore, (₹3.20 crore) loss and ₹22.60 crore. In the preceding year it had spent ₹4.00 lakh in excess of its CSR obligation, which the Board has resolved to set off. The minimum CSR amount it must spend in the current year is:",
          lk(req),
          [(lk(0.02 * (np3[0] + np3[2]) / 2 - excess), "loss year excluded from the three-year average"),
           (lk(ob), "excess spend of the earlier year not set off"),
           (lk(0.02 * np3[2] - excess), "2% of the latest year's profit instead of the three-year average")],
          [f"Average net profit = (18.40 − 3.20 + 22.60) ÷ 3 = {cr(avg)}.",
           f"2% obligation = {lk(ob)}.",
           f"Set off excess spent (allowed up to three succeeding FYs, Rule 7(3)) {lk(excess)} → {lk(req)}."],
          "CSR = 2% × average of 3 preceding years' s.198 net profits − eligible excess set-off",
          "A loss year is included in the average (as a negative); it is not dropped.",
          verify_fact=True, ref="Companies Act 2013 s.135(5); CSR Policy Rules 2014, Rule 7(3)")

    B.add(M["csr"], "L2",
          "Match the unspent CSR situation with the correct treatment under s.135(5)-(6):\n\n"
          + table(["", "Situation", "", "Treatment"], [
              ["A", "Unspent amount not relating to an ongoing project", "i", "Transfer to Unspent CSR Account within 30 days of end of FY"],
              ["B", "Unspent amount relating to an ongoing project", "ii", "Transfer to a Schedule VII fund within six months of end of FY"],
              ["C", "Amount in Unspent CSR Account not spent within three FYs", "iii", "Transfer to a Schedule VII fund within 30 days of completion of the third FY"]]),
          "A-ii, B-i, C-iii",
          [("A-i, B-ii, C-iii", "treatment of ongoing and non-ongoing amounts swapped"),
           ("A-ii, B-iii, C-i", "ongoing-project balance sent straight to Schedule VII fund"),
           ("A-iii, B-i, C-ii", "30-day and six-month windows swapped for Schedule VII transfers")],
          ["s.135(5) second proviso: non-ongoing unspent → Schedule VII fund within six months of FY end.",
           "s.135(6): ongoing project unspent → Unspent CSR Account within 30 days of FY end; spend within three FYs, else Schedule VII fund within 30 days of completion of third FY."],
          "s.135(5)-(6)", "Two different Schedule VII timelines: six months (non-ongoing) and 30 days after the third year (ongoing).",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.135(5), (6)")

    B.add(M["csr"], "L3",
          stmts("Consider the following statements on CSR spending under the Companies Act, 2013 and CSR Policy Rules, 2014:",
                ["Excess amount spent over the CSR obligation may be set off against the requirement up to the immediately succeeding three financial years.",
                 "Surplus arising out of CSR activities can be counted towards the excess available for set-off.",
                 "Administrative overheads of a company's CSR shall not exceed 5% of its total CSR expenditure for the financial year.",
                 "Where the CSR obligation does not exceed ₹50 lakh, a CSR Committee need not be constituted and its functions are discharged by the Board."]),
          "1, 3 and 4 only",
          [("1 and 3 only", "misses the ₹50 lakh committee exemption"),
           ("1, 2, 3 and 4", "includes CSR surplus in excess set-off"),
           ("2, 3 and 4 only", "excess set-off period mistaken")],
          ["Rule 7(3): excess set off up to three succeeding FYs; excess shall not include surplus from CSR activities (Rule 7(3)(i)).",
           "Rule 7(1): administrative overheads ≤ 5% of total CSR expenditure.",
           "s.135(9): CSR obligation up to ₹50 lakh — committee not required."],
          "CSR Rules 7(1), 7(3); s.135(9)", "CSR surplus must be ploughed back — it cannot inflate the set-off.",
          kind="statement", verify_fact=True, ref="CSR Policy Rules 2014, Rule 7; Companies Act 2013 s.135(9)")

    # ------------------------------------------------------------------ Schedules
    B.add(M["sched"], "L1",
          "Match the Schedule of the Companies Act, 2013 with its subject:\n\n"
          + table(["", "Schedule", "", "Subject"], [
              ["A", "Schedule II", "i", "Code for Independent Directors"],
              ["B", "Schedule III", "ii", "Activities that may be included in CSR policies"],
              ["C", "Schedule IV", "iii", "Useful lives to compute depreciation"],
              ["D", "Schedule VII", "iv", "General instructions for preparation of balance sheet and statement of profit and loss"]]),
          "A-iii, B-iv, C-i, D-ii",
          [("A-iv, B-iii, C-i, D-ii", "Schedules II and III swapped"),
           ("A-iii, B-iv, C-ii, D-i", "Schedules IV and VII swapped"),
           ("A-iii, B-i, C-iv, D-ii", "Schedule III confused with the ID code")],
          ["Schedule II — useful lives (depreciation); III — format of financial statements; IV — Code for Independent Directors; VII — CSR activities."],
          "Schedules I–VII", "Schedule V (managerial remuneration) and VI (infrastructure projects) are common distractors.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 Schedules II, III, IV, VII")

    ec = 400e7
    base = 120e5
    lim = base + 0.0001 * (ec - 250e7)
    assert round(lim) == 121.5e5
    B.add(M["sched"], "L3",
          f"Suvarna Engineering Ltd has inadequate profits for FY 2026-27 and proposes to pay its Managing Director remuneration under Section II of Part II of Schedule V. Its effective capital is {cr(ec)}. Only an ordinary resolution (not a special resolution) will be passed. The maximum annual remuneration payable is:",
          lk(lim),
          [(lk(base), "0.01% of effective capital in excess of ₹250 crore omitted"),
           (lk(2 * lim), "doubled limit applied without a special resolution"),
           (lk(base + 0.0001 * ec), "0.01% applied on the entire effective capital")],
          ["Schedule V, Part II, Section II table: effective capital above ₹250 crore → ₹120 lakh plus 0.01% of effective capital in excess of ₹250 crore.",
           f"Excess = {cr(ec-250e7)}; 0.01% = {lk(0.0001*(ec-250e7))}; limit = {lk(lim)}.",
           "The limit may be doubled only if a special resolution is passed."],
          "Limit = ₹120 lakh + 0.01% × (EC − ₹250 crore)", "The 0.01% applies only to the excess over ₹250 crore.",
          verify_fact=True, ref="Companies Act 2013 Schedule V Part II Section II (as amended 2018)")

    cost, life, rv = 50e5, 15, 0.05
    dep = cost * (1 - rv) / life
    B.add(M["sched"], "L2",
          f"For computing profits available for dividend, Ganga Polymers Ltd must provide depreciation as per Schedule II. It bought general plant and machinery (useful life 15 years under Schedule II) for {lk(cost)} and adopts residual value at the Schedule II ceiling of 5% of original cost. Annual straight-line depreciation is:",
          lk(dep),
          [(lk(cost / life), "residual value ignored"),
           (lk(cost * 0.90 / life), "10% residual value of the repealed 1956 Act regime used"),
           (lk(cost * 0.0475), "4.75% SLM rate of the repealed Schedule XIV used")],
          ["Schedule II Part A: residual value ordinarily not more than 5% of original cost.",
           f"Depreciable amount = {lk(cost)} × 95% = {lk(cost*0.95)}; ÷ 15 years = {lk(dep)}."],
          "SLM = (Cost − Residual value) ÷ Useful life",
          "Schedule II works on useful lives, not the old Schedule XIV rates.",
          verify_fact=True, ref="Companies Act 2013 Schedule II Part A & C; s.123(2)")
