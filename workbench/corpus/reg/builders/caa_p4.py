"""REG-CORPUS-CA-A part 4: standalone questions — dividends, directors, IDs, capital, prospectus, NCLAT, committees, meetings, audit."""
from caa_common import q, ar, inr, R, L, Cr, D, date, timedelta, pct


def add_all(B):
    # ---------- Divisible profits (standalone) ----------
    pu, frz, rates, loss = 50, 30, (12, 10, 8), 4
    avg = sum(rates) / 3
    by_rate = avg / 100 * pu
    drawcap = 0.10 * (pu + frz)
    floor_ok = frz - drawcap >= 0.15 * pu
    ans = min(by_rate, drawcap - loss)
    assert floor_ok and ans == 4
    q(B, "divprof", "L3", f"Surya Textiles Ltd has incurred a loss of ₹{loss} crore in FY 2025-26 and wishes to declare a dividend out of "
      f"accumulated free reserves. Latest audited figures: paid-up equity capital ₹{pu} crore; free reserves ₹{frz} crore. Dividend rates "
      f"in the three preceding years: {rates[0]}%, {rates[1]}% and {rates[2]}%. The maximum dividend it can declare is:",
      Cr(ans),
      [(Cr(by_rate), "only the average-rate cap applied; drawal cap and loss set-off ignored"),
       (Cr(drawcap), "10% drawal cap applied but current-year loss not set off first"),
       (Cr(0.10 * pu - loss), "drawal cap computed on paid-up capital alone")],
      [f"Rate cap: average of preceding three years = {avg:g}% → ₹{by_rate:g} crore.",
       f"Drawal cap: 10% of (paid-up + free reserves) = 10% × {pu+frz} = ₹{drawcap:g} crore.",
       f"Drawal first set off against current-year loss ₹{loss} crore → ₹{drawcap-loss:g} crore left for equity dividend.",
       f"Floor: reserves after drawal ({frz-drawcap:g}) ≥ 15% of paid-up ({0.15*pu:g}) → satisfied.",
       f"Maximum = lower of {by_rate:g} and {drawcap-loss:g} = ₹{ans:g} crore."],
      "Rule 3: rate ≤ 3-yr average; drawal ≤ 10% of (PUC + FR); loss set off first; residual reserves ≥ 15% of PUC",
      "The loss absorbs part of the 10% drawal before shareholders see any of it.",
      kind="numerical", ref="Companies (Declaration and Payment of Dividend) Rules 2014, Rule 3")

    cur, cdep, ploss, pdep, unr = 18, 3, 5, 2, 1.5
    avail = cur - cdep - ploss - pdep - unr
    assert abs(avail - 6.5) < 1e-9
    q(B, "divprof", "L3", f"Before depreciation, Rohini Ltd earned ₹{cur} crore in FY 2025-26, including an unrealised fair-value gain of "
      f"₹{unr} crore. Schedule II depreciation for the year is ₹{cdep} crore. It has carried-forward losses of ₹{ploss} crore and unprovided "
      f"depreciation of ₹{pdep} crore from earlier years. The maximum amount available for dividend out of the current year's profit is:",
      Cr(avail),
      [(Cr(avail + unr), "unrealised fair-value gain not excluded"),
       (Cr(cur - cdep - unr), "previous losses and unprovided depreciation not set off"),
       (Cr(avail - 0.10 * cur), "compulsory 10% transfer to reserves assumed (repealed 1956-era rule)")],
      ["s.123(1)(a): profits after providing depreciation under Schedule II.",
       "Proviso to s.123(1)(a): unrealised gains, notional gains, revaluation and fair-value changes excluded.",
       "Fourth proviso to s.123(1): carried-forward losses and depreciation not provided in earlier years must be set off against current profit.",
       f"{cur} − {cdep} − {unr} − {ploss} − {pdep} = ₹{avail:g} crore; transfer to reserves is optional."],
      "Distributable = current profit − depreciation − unrealised gains − b/f losses − unprovided depreciation",
      "Transfer to reserves is discretionary under the 2013 Act.",
      kind="numerical", ref="Companies Act 2013 s.123(1)(a) proviso and fourth proviso to s.123(1)")

    # ---------- Duties of directors ----------
    q(B, "duties", "L1", "Which of the following is NOT a duty of a director under s.166?",
      "To maximise short-term returns to shareholders even at the cost of employees and the environment",
      [("To act in good faith to promote the objects of the company for the benefit of its members as a whole, and in the best interests of the company, employees, community and environment",
        "listed s.166(2) duty treated as not a duty"),
       ("To exercise duties with due and reasonable care, skill and diligence and independent judgment", "listed s.166(3) duty treated as not a duty"),
       ("Not to assign his office; any assignment is void", "listed s.166(6) duty treated as not a duty")],
      ["s.166 lists: act per articles; good faith for members, company, employees, shareholders, community and environment; due care and independent judgment; "
       "avoid conflicts; no undue gain; no assignment of office."],
      "s.166: stakeholder-oriented duties",
      "s.166(2) is explicitly multi-stakeholder.",
      ref="Companies Act 2013 s.166")

    gain = 12
    q(B, "duties", "L2", f"A director of Pavan Ltd diverted a supply contract to his relative's firm and made an undue gain of ₹{gain} lakh. "
      "Under s.166(5), he is liable to:",
      f"Pay the company an amount equal to the gain, i.e., {L(gain)}",
      [(f"Pay the company twice the gain, i.e., {L(2 * gain)}", "disgorgement doubled"),
       (f"Pay {L(gain)} to the Central Government", "payee misidentified"),
       ("Only removal from office; no repayment is required", "disgorgement overlooked")],
      ["s.166(5): a director who achieves an undue gain is liable to pay an amount equal to that gain to the company (fine under s.166(7) is separate)."],
      "Undue gain → pay equal amount to the company",
      "The money goes back to the company, not the government.",
      kind="numerical", ref="Companies Act 2013 s.166(5)")

    # ---------- ESOP & sweat equity ----------
    q(B, "esop", "L1", "Sweat equity shares issued by an unlisted company are locked in for:",
      "Three years from the date of allotment",
      [("One year from the date of allotment", "minimum ESOP vesting period applied"),
       ("Five years from the date of allotment", "lock-in overstated"),
       ("No lock-in at all", "Rule 8 lock-in overlooked")],
      ["Rule 8(5), Companies (Share Capital and Debentures) Rules 2014: sweat equity shares locked in (non-transferable) for three years from allotment."],
      "Sweat equity lock-in: 3 years",
      "One year is the minimum ESOP vesting period, a different rule.",
      ref="Companies Act 2013 s.54; Rule 8(5), Share Capital and Debentures Rules 2014")

    q(B, "esop", "L2", "Under Rule 12 of the Share Capital and Debentures Rules (ESOPs of unlisted companies), consider:\n\n"
      "1. There must be a minimum period of one year between grant and vesting.\n"
      "2. Independent directors may be granted options with shareholder approval.\n"
      "3. A director holding (with relatives or through a body corporate) more than 10% of the equity is not eligible (subject to the start-up relaxation).\n"
      "4. Options granted are not transferable.\n\n"
      "Select the correct answer:",
      "1, 3 and 4 only",
      [("1, 2, 3 and 4", "independent-director bar overlooked"),
       ("1 and 4 only", "10% promoter-director exclusion overlooked"),
       ("2, 3 and 4 only", "minimum vesting period overlooked")],
      ["Rule 12(6)(a): minimum vesting period one year.",
       "Rule 12(1) Explanation: 'employee' excludes independent directors, promoters/promoter group and >10% director-holders (start-ups relaxed).",
       "Rule 12(8): options not transferable."],
      "Rule 12: 1-year vesting; no IDs; no >10% holders; non-transferable",
      "Independent directors are excluded both by Rule 12 and by s.197(7).",
      kind="statement", ref="Companies Act 2013 s.62(1)(b); Rule 12, Share Capital and Debentures Rules 2014")

    puc = 60
    cap15 = 0.15 * puc
    assert cap15 > 5
    q(B, "esop", "L3", f"Nimbus Ltd (not a start-up) has existing paid-up equity capital of ₹{puc} crore and has never issued sweat equity. "
      "The maximum sweat equity it can issue this year is:",
      f"Shares up to 15% of existing paid-up equity capital, i.e., ₹{cap15:g} crore (higher than the ₹5 crore issue-value limit)",
      [("Shares of issue value ₹5 crore (the lower of the two limits)", "'whichever is higher' read as 'whichever is lower'"),
       (f"Shares up to 25% of paid-up equity capital, i.e., ₹{0.25*puc:g} crore", "overall 25% cap treated as the annual limit"),
       (f"Shares up to 50% of paid-up equity capital, i.e., ₹{0.5*puc:g} crore", "start-up relaxation applied")],
      ["Rule 8(4): in a year, not more than 15% of existing paid-up equity capital or shares of issue value ₹5 crore, whichever is higher.",
       f"15% × {puc} = ₹{cap15:g} crore > ₹5 crore → ₹{cap15:g} crore.",
       "Overall cap at any time: 25% of paid-up equity capital (start-ups: 50% up to 10 years)."],
      "Sweat equity per year ≤ max(15% of PUC, ₹5 cr issue value); total ≤ 25% of PUC",
      "The annual limit is the higher of the two tests.",
      kind="numerical", ref="Rule 8(4), Companies (Share Capital and Debentures) Rules 2014 (as amended 2021)")

    # ---------- Firm eligibility (standalone) ----------
    pubc, small, pvt_lt100, pvt_ge100, opc = 8, 6, 4, 5, 2
    count = pubc + pvt_ge100
    room = 20 - count
    assert room == 7
    q(B, "firm", "L2", f"CA Ishaan is currently auditor of {pubc} public companies, {small} small companies, {pvt_lt100} private companies "
      f"with paid-up capital below ₹100 crore, {pvt_ge100} private companies with paid-up capital of ₹100 crore or more, and {opc} OPCs. "
      "How many more countable audits can he accept under s.141(3)(g)?",
      str(room),
      [("None — he already holds 25 audits", "all audits counted, ignoring exclusions"),
       (str(20 - count - pvt_lt100), "private companies below ₹100 crore counted"),
       (str(20 - count - small), "small companies counted")],
      ["s.141(3)(g): limit of 20 companies, excluding OPCs, dormant companies, small companies and private companies with paid-up capital below ₹100 crore.",
       f"Countable = {pubc} public + {pvt_ge100} large private = {count}; room = 20 − {count} = {room}."],
      "Countable audits = public + private (PUC ≥ ₹100 cr); limit 20",
      "Most small-entity audits fall outside the 20-limit.",
      kind="numerical", ref="Companies Act 2013 s.141(3)(g) (as modified for private companies, 2017)")

    fvh = 1.4
    q(B, "firm", "L3", f"The brother of CA Yamini, auditor of Tulsi Ltd, acquires shares of face value ₹{fvh} lakh in Tulsi's subsidiary. "
      "Which is correct?",
      "The ₹1 lakh limit for a relative's holding is exceeded; corrective action must be taken within 60 days of the acquisition, failing which she is disqualified",
      [("There is no issue; a relative may hold up to ₹5 lakh", "indebtedness limit confused with shareholding limit"),
       ("She is disqualified immediately with no scope for correction", "60-day corrective window overlooked"),
       ("The restriction covers only shares of Tulsi itself, not its subsidiary", "holding/subsidiary/associate coverage overlooked")],
      ["s.141(3)(d)(i): relative holding security or interest in the company, its subsidiary, holding or associate — allowed up to ₹1 lakh face value (Rule 10).",
       f"₹{fvh} lakh > ₹1 lakh; Rule 10 proviso: corrective action within 60 days of acquisition."],
      "Relative's holding ≤ ₹1 lakh face value; correct within 60 days",
      "The group-wide coverage extends to subsidiaries.",
      ref="Companies Act 2013 s.141(3)(d)(i); Rule 10, Companies (Audit and Auditors) Rules 2014")

    # ---------- Schedule III ----------
    q(B, "sch3", "L1", "Division II of Schedule III prescribes the format of financial statements for:",
      "Companies required to comply with Ind AS, other than NBFCs",
      [("Companies following the Companies (Accounting Standards) Rules", "Division I scope assigned to Division II"),
       ("NBFCs required to comply with Ind AS", "Division III scope assigned to Division II"),
       ("All companies, irrespective of the accounting framework", "divisional structure ignored")],
      ["Division I: companies under Accounting Standards; Division II: Ind AS companies (non-NBFC); Division III: Ind AS NBFCs."],
      "Schedule III: Div I (AS), Div II (Ind AS non-NBFC), Div III (Ind AS NBFC)",
      "NBFCs have their own Division III.",
      ref="Companies Act 2013 s.129(1), Schedule III")

    a_txt, r_txt = ar(0, {1: "causal link between A and R missed", 2: "R wrongly judged false", 3: "A wrongly judged false"})
    q(B, "sch3", "L2", "**Assertion (A):** Instalments of a long-term borrowing falling due within twelve months after the reporting date are "
      "classified as current liabilities under Schedule III.\n\n**Reason (R):** A liability is current where the company does not have an "
      "unconditional right to defer its settlement for at least twelve months after the reporting date.",
      a_txt, r_txt,
      ["Schedule III (General Instructions): a liability is current if due within 12 months after the reporting date, or if there is no unconditional right to defer settlement for at least 12 months.",
       "Current maturities of long-term debt therefore move to current liabilities (shown within short-term borrowings after the 2021 amendments) — R explains A."],
      "Current liability tests: operating cycle / held for trading / due ≤ 12 months / no unconditional deferral right",
      "The classification follows settlement timing, not the original tenor of the loan.",
      kind="assertion-reason", ref="Companies Act 2013 Schedule III, General Instructions (Division I and II)")

    ratios = {"Current ratio": (1.50, 1.10), "Debt-equity ratio": (0.80, 0.95),
              "Return on equity (%)": (14.0, 11.0), "Trade receivables turnover (times)": (6.0, 7.8)}
    ch = {k: (v[1] - v[0]) / v[0] for k, v in ratios.items()}
    need = [k for k, c in ch.items() if abs(c) > 0.25]
    assert need == ["Current ratio", "Trade receivables turnover (times)"]
    tbl = "| Ratio | FY 2024-25 | FY 2025-26 |\n|---|---:|---:|\n" + "\n".join(f"| {k} | {v[0]:g} | {v[1]:g} |" for k, v in ratios.items())
    q(B, "sch3", "L3", f"Extract of ratios for Kosi Ltd:\n\n{tbl}\n\nUnder the Schedule III (2021) disclosure requirement, for which ratios "
      "must Kosi explain the change?",
      "Current ratio and trade receivables turnover only",
      [("Current ratio only", "increase in receivables turnover ignored (change measured only for declines)"),
       ("All four ratios", "every change treated as needing explanation"),
       ("Current ratio, return on equity and trade receivables turnover", "ROE change measured in percentage points (3) against a 25% threshold misapplied")],
      [f"Changes: " + "; ".join(f"{k} {c*100:+.2f}%" for k, c in ch.items()) + ".",
       "Explanation required where a ratio changes by more than 25% compared with the preceding year.",
       f"Beyond 25%: {', '.join(need)}."],
      "Change % = (Current − Previous) ÷ Previous; explain if |change| > 25%",
      "Direction does not matter; magnitude above 25% does.",
      kind="numerical", ref="Companies Act 2013 Schedule III (amended 24 March 2021), Additional Regulatory Information — ratios")

    # ---------- Further issue & rights ----------
    q(B, "rights", "L2", "In a rights issue by a public company under s.62(1)(a), the offer must remain open for ____ and the notice must be "
      "dispatched at least ____ before the opening of the issue.",
      "not less than 7 days and not more than 30 days; 3 days",
      [("not less than 15 days and not more than 30 days; 3 days", "pre-2021 value: 15-day minimum as originally enacted, before Rule 12A"),
       ("not less than 7 days and not more than 30 days; 7 days", "dispatch lead time overstated"),
       ("not less than 21 days and not more than 45 days; 3 days", "general-meeting notice period mixed in")],
      ["s.62(1)(a)(i) (amended by Companies (Amendment) Act 2020): not less than 15 days or such lesser number of days as prescribed, not exceeding 30 days.",
       "Rule 12A, Share Capital and Debentures Rules (w.e.f. 1 April 2021): prescribed minimum is 7 days → open 7–30 days.",
       "s.62(2): notice dispatched through registered/speed post, electronic mode or courier at least three days before the issue opens."],
      "Rights: open 7–30 days (r.12A); notice ≥ 3 days before opening",
      "The renunciation right exists unless the articles provide otherwise.",
      ref="Companies Act 2013 s.62(1)(a)(i) (amended 2020), s.62(2); Rule 12A, Share Capital and Debentures Rules 2014 (GSR 113(E), 11 Feb 2021)")

    held, rn, rd, price, fvv = 3850, 2, 7, 60, 10
    ent = held * rn // rd
    assert held * rn % rd == 0
    q(B, "rights", "L3", f"Arun holds {inr(held)} shares of Nova Ltd. Nova makes a rights issue of {rn} shares for every {rd} held at ₹{price} "
      f"per share (face value ₹{fvv}). If he subscribes in full, he pays:",
      R(ent * price),
      [(R(round(held * rn / (rd + rn)) * price), "entitlement computed on the post-issue base (2 in 9)"),
       (R(ent * fvv), "face value used instead of issue price"),
       (R(ent * (price - fvv)), "only the premium element counted")],
      [f"Entitlement = {inr(held)} × {rn}/{rd} = {inr(ent)} shares.",
       f"Payment = {inr(ent)} × ₹{price} = {R(ent*price)}."],
      "Rights entitlement = holding × (rights shares ÷ held shares)",
      "The ratio applies to the existing holding, not the enlarged capital.",
      kind="numerical")

    q(B, "rights", "L3", "Mitra Ltd, an unlisted public company, proposes a preferential allotment of equity shares to a strategic investor "
      "under s.62(1)(c). Consider:\n\n"
      "1. A special resolution is required.\n"
      "2. The price must be determined on the basis of a registered valuer's report.\n"
      "3. The allotment must be completed within twelve months of the special resolution.\n"
      "4. An ordinary resolution suffices if the Board unanimously recommends it.\n\n"
      "Select the correct answer:",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "contradictory statement 4 accepted"),
       ("1 and 2 only", "12-month completion window overlooked"),
       ("2, 3 and 4 only", "special-resolution requirement overlooked")],
      ["s.62(1)(c): to any persons if authorised by special resolution, price by registered valuer's report (subject to Rule 13).",
       "Rule 13(2): allotment completed within 12 months of passing the special resolution; otherwise a fresh resolution is needed."],
      "Preferential issue: SR + valuation report + allot within 12 months",
      "Board unanimity cannot replace the members' special resolution.",
      kind="statement", ref="Companies Act 2013 s.62(1)(c); Rule 13, Share Capital and Debentures Rules 2014")

    # ---------- IEPF (standalone) ----------
    q(B, "iepf", "L1", "Which of the following amounts is credited to the Investor Education and Protection Fund?",
      "Matured deposits and debentures with companies that remain unclaimed for seven years",
      [("Unspent CSR amounts of a company", "CSR unspent amounts go to Schedule VII funds / Unspent CSR Account"),
       ("Penalties collected by the NCLT under the Act", "penalties are not IEPF credits"),
       ("Sitting fees that directors decline to accept", "invented credit")],
      ["s.125(2): unpaid dividend accounts, application money due for refund, matured deposits and debentures, interest accrued, "
       "fractional-share sale proceeds, unpaid redemption amounts of preference shares (7 years), grants and donations, etc."],
      "s.125(2) credits to IEPF",
      "Unspent CSR has its own routing under s.135.",
      ref="Companies Act 2013 s.125(2)")

    q(B, "iepf", "L2", "Consider the uses of the IEPF under s.125(3):\n\n"
      "1. Promotion of investors' education, awareness and protection.\n"
      "2. Distribution of any disgorged amount among eligible and identifiable applicants for shares or debentures.\n"
      "3. Granting concessional loans to small investors to buy shares.\n\n"
      "Which are permitted?",
      "1 and 2 only",
      [("1, 2 and 3", "investor financing treated as a permitted use"),
       ("1 only", "disgorgement distribution overlooked"),
       ("2 and 3 only", "investor education overlooked")],
      ["s.125(3): refunds; investor education/awareness/protection; distribution of disgorged amounts; reimbursement of class-action expenses; incidental purposes.",
       "Lending to investors is not a permitted use."],
      "s.125(3) permitted uses",
      "The Fund protects investors; it does not finance their investments.",
      kind="statement", ref="Companies Act 2013 s.125(3)")

    # ---------- ID eligibility (standalone) ----------
    txn_amt, inc = 4.5, 40
    share = txn_amt / inc
    assert share > 0.10
    q(B, "idelig", "L2", f"Mr Dev, proposed as an independent director of Rishi Ltd, had transactions (other than remuneration as director) "
      f"with Rishi of ₹{txn_amt} lakh in each of the two preceding financial years; his total income in each of those years was ₹{inc} lakh. He is:",
      f"Not eligible — the transactions ({share*100:.2f}% of his total income) exceed 10% of his total income",
      [("Eligible — the ceiling for pecuniary relationships is 25% of total income", "NPO receipts threshold (25%) applied"),
       ("Eligible — pecuniary relationship tests apply only to relatives", "s.149(6)(c) (director himself) overlooked"),
       ("Eligible — only transactions above ₹50 lakh are counted", "relatives' ₹50 lakh limit applied to the director")],
      [f"s.149(6)(c) (as amended 2017): no pecuniary relationship, other than remuneration as director or transactions not exceeding 10% of his total income, during the two preceding FYs or current FY.",
       f"{txn_amt}/{inc} = {share*100:.2f}% > 10% → not independent."],
      "Director's own transactions ≤ 10% of his total income",
      "The 10% test is measured against the director's income, not the company's turnover.",
      kind="numerical", ref="Companies Act 2013 s.149(6)(c) (amended 2017)")

    q(B, "idelig", "L3", "Ms Ira is proposed as an independent director of Sona Ltd in FY 2026-27. Consider:\n\n"
      "1. Her daughter has been a (non-KMP) employee of Sona since 2023; this does not bar her.\n"
      "2. Her husband was CFO of Sona's associate company until FY 2024-25; this bars her.\n"
      "3. Had her husband ceased to be CFO in FY 2023-24, she would be eligible.\n\n"
      "Which are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "three-year look-back miscounted (2023-24 falls within it)"),
       ("2 only", "relative-employee proviso overlooked"),
       ("2 and 3 only", "relative-employee proviso overlooked and look-back miscounted")],
      ["s.149(6)(e)(i): neither she nor a relative held KMP position in company/holding/subsidiary/associate in any of the three FYs preceding 2026-27 (2023-24, 2024-25, 2025-26).",
       "Proviso (2017): for a relative who is an employee (not KMP), the restriction does not apply → 1 correct.",
       "Husband as CFO till 2024-25 → within look-back → 2 correct; 2023-24 also within → 3 wrong."],
      "Look-back = the three FYs immediately preceding the FY of appointment",
      "The relief is for relatives who are ordinary employees, not KMP.",
      kind="statement", ref="Companies Act 2013 s.149(6)(e)(i) and proviso")

    # ---------- ID criteria & tenure ----------
    q(B, "idtenure", "L1", "An independent director may hold office for a term of up to ____ consecutive years and for not more than ____ consecutive terms.",
      "Five; two",
      [("Three; three", "cooling-off period confused with term"),
       ("Five; three", "number of terms overstated"),
       ("Ten; one", "total tenure treated as one term")],
      ["s.149(10): term up to five consecutive years; re-appointment by special resolution.",
       "s.149(11): no more than two consecutive terms; eligible again after three years."],
      "ID: 2 × 5 years, then 3-year cooling-off",
      "Re-appointment for the second term needs a special resolution.",
      ref="Companies Act 2013 s.149(10),(11)")

    end = date(2026, 3, 31)
    back = date(2029, 4, 1)
    q(B, "idtenure", "L2", f"Mr Om completed two consecutive terms as an independent director of Zeal Ltd on {D(end)}. Which is correct?",
      f"He can be re-appointed as an independent director from {D(back)}, and meanwhile cannot be associated with Zeal in any other capacity",
      [(f"He can be re-appointed from {D(date(2031, 4, 1))}", "auditor's five-year cooling-off applied"),
       (f"He can be re-appointed from {D(back)}, and may meanwhile act as a paid consultant to Zeal", "bar on association during cooling-off overlooked"),
       ("He can be re-appointed immediately for a third term by special resolution", "two-term cap treated as relaxable")],
      ["s.149(11): eligible after expiry of three years of ceasing to be an ID.",
       "Explanation: during the three years, not appointed in or associated with the company in any other capacity, directly or indirectly."],
      "ID cooling-off: 3 years, no association in any capacity",
      "The cooling-off is total, not just from the ID role.",
      kind="numerical", ref="Companies Act 2013 s.149(11) and proviso")

    q(B, "idtenure", "L3", "Consider the following about independent directors:\n\n"
      "1. They are not counted in the total number of directors when computing directors liable to retire by rotation.\n"
      "2. Their liability is limited to acts of omission or commission that occurred with their knowledge attributable through Board processes, with their consent or connivance, or where they did not act diligently.\n"
      "3. They may receive stock options if approved by special resolution.\n"
      "4. They must hold at least one meeting in a financial year without the non-independent directors and management.\n\n"
      "Select the correct answer:",
      "1, 2 and 4 only",
      [("1, 2, 3 and 4", "stock-option bar overlooked"),
       ("2 and 4 only", "exclusion from rotation overlooked"),
       ("1, 2 and 3 only", "Schedule IV separate meeting overlooked")],
      ["s.149(13): rotation provisions (s.152(6),(7)) do not apply to IDs.",
       "s.149(12): limited liability of IDs and NEDs.",
       "s.149(9)/s.197(7): no stock options → 3 wrong.",
       "Schedule IV, para VII: at least one separate meeting a year."],
      "s.149(9),(12),(13); Schedule IV",
      "IDs are paid by fees and profit-linked commission, never options.",
      kind="statement", ref="Companies Act 2013 s.149(9),(12),(13); Schedule IV para VII")

    # ---------- Interim dividend ----------
    q(B, "interim", "L2", "Which of the following is a permitted source for an interim dividend under s.123(3)?",
      "Profits generated in the financial year up to the quarter preceding the date of declaration",
      [("General reserve built up in earlier years", "free reserves (final-dividend route under Rule 3) used for interim"),
       ("Securities premium account", "capital receipt treated as distributable"),
       ("Revaluation reserve", "notional gain treated as distributable")],
      ["s.123(3): interim dividend out of surplus in the profit and loss account, profits of the FY for which it is declared, or profits generated in the FY till the quarter preceding the declaration."],
      "Interim sources: P&L surplus | current-FY profits | profits to preceding quarter-end",
      "Reserves other than the P&L surplus are not interim sources.",
      ref="Companies Act 2013 s.123(3)")

    puq, rts = 25, (15, 12, 9)
    avgr = sum(rts) / 3
    mx = avgr / 100 * puq
    assert mx == 3
    q(B, "interim", "L3", f"Vasant Ltd has incurred a loss for the current FY up to the end of the quarter immediately preceding the date on "
      f"which it wishes to declare an interim dividend. Its paid-up equity capital is ₹{puq} crore; dividend rates for the three preceding "
      f"FYs were {rts[0]}%, {rts[1]}% and {rts[2]}%. The maximum interim dividend is:",
      Cr(mx),
      [(Cr(rts[0] / 100 * puq), "highest of the three rates used"),
       (Cr(rts[2] / 100 * puq), "most recent year's rate used"),
       ("Nil — no interim dividend is permitted when there is a loss", "loss proviso read as a prohibition")],
      [f"s.123(3) proviso: rate not higher than the average of the three preceding FYs = ({'+'.join(map(str, rts))})/3 = {avgr:g}%.",
       f"Maximum = {avgr:g}% × ₹{puq} crore = ₹{mx:g} crore."],
      "Loss to preceding quarter → interim rate ≤ 3-year average",
      "A loss caps the rate; it does not prohibit the dividend.",
      kind="numerical", ref="Companies Act 2013 s.123(3) proviso")

    q(B, "interim", "L3", "Consider the following about interim dividends:\n\n"
      "1. It may be declared during the financial year or at any time between the close of the financial year and the AGM.\n"
      "2. It is declared by the Board; no general-meeting approval is required for the declaration.\n"
      "3. It must be deposited in a separate scheduled-bank account within five days of declaration.\n"
      "4. It may be paid out of the securities premium account.\n\n"
      "Select the correct answer:",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "securities premium treated as a dividend source"),
       ("2 and 3 only", "post-year-end declaration window overlooked"),
       ("1 and 2 only", "five-day deposit rule overlooked for interim dividends")],
      ["s.123(3): Board may declare during the FY or between FY-end and AGM → 1, 2 correct.",
       "s.123(4): five-day deposit covers interim dividend → 3 correct.",
       "s.52 permits specific uses of securities premium; dividend is not one → 4 wrong."],
      "s.123(3),(4); s.52",
      "Securities premium can fund bonus shares, not dividends.",
      kind="statement", ref="Companies Act 2013 s.123(3),(4), s.52(2)")

    # ---------- Shares at a discount ----------
    a_txt, r_txt = ar(0, {1: "link between A and R missed", 2: "R wrongly judged false", 3: "A wrongly judged false"})
    q(B, "discount", "L1", "**Assertion (A):** A company may issue sweat equity shares at a discount to their face value.\n\n"
      "**Reason (R):** The prohibition in s.53 on issuing shares at a discount does not extend to shares issued under s.54.",
      a_txt, r_txt,
      ["s.53(1): except as provided in s.54, a company shall not issue shares at a discount.",
       "s.53(2A): also permits issue at a discount to creditors on conversion of debt under an RBI-guided statutory resolution plan or debt restructuring.",
       "R is the very reason A holds."],
      "s.53(1) exception: sweat equity (s.54); s.53(2A): debt conversion under RBI framework",
      "Rights, IPO or ESOP shares below par are not exceptions.",
      kind="assertion-reason", ref="Companies Act 2013 s.53(1),(2A)")

    n_, fvs, iss = 1_00_000, 10, 8
    raised = n_ * iss
    pen = min(raised, 5_00_000)
    assert pen == 5_00_000
    q(B, "discount", "L2", f"Laxmi Ltd issues {inr(n_)} equity shares of ₹{fvs} each at ₹{iss} each to investors (no s.53 exception applies). "
      "The consequence is:",
      f"The issue is void; the company must refund {R(raised)} with interest at 12% p.a. from the date of issue, and the company and officers "
      f"in default are liable to a penalty up to the lower of the amount raised and ₹5 lakh (i.e., {R(pen)})",
      [("The issue is valid; the discount is written off against securities premium", "discount treated as an accounting matter"),
       (f"The issue is void; the company must refund {R(raised)} without interest", "12% interest on refund overlooked"),
       ("The issue is voidable at the option of the allottees; interest at 18% p.a. applies", "void treated as voidable; dividend-default rate used")],
      ["s.53(2): shares issued at a discount are void.",
       f"s.53(3) (substituted by Companies (Amendment) Act 2019): penalty up to the amount raised or ₹5 lakh, whichever is less → lower of {R(raised)} and ₹5,00,000 = {R(pen)}; refund with 12% p.a. interest from date of issue."],
      "s.53: void; refund + 12% p.a.; penalty ≤ min(amount raised, ₹5 lakh)",
      "18% is the s.127 dividend-default rate, not the s.53 refund rate.",
      ref="Companies Act 2013 s.53(2),(3) (substituted by Companies (Amendment) Act 2019, w.e.f. 2 Nov 2018)")

    # ---------- Kinds of share capital ----------
    q(B, "kinds", "L1", "Under s.43, the share capital of a company limited by shares is of:",
      "Two kinds — equity (with voting rights, or with differential rights as to dividend, voting or otherwise) and preference",
      [("Three kinds — equity, preference and deferred (founders') shares", "1956-era private company classes assumed"),
       ("Two kinds — ordinary and redeemable", "terminology confused"),
       ("Four kinds — equity, preference, sweat equity and bonus shares", "modes of issue confused with kinds of capital")],
      ["s.43: equity share capital (with voting rights, or with differential rights) and preference share capital."],
      "s.43: equity (voting / DVR) + preference",
      "Sweat equity and bonus shares are equity shares, not separate kinds.",
      ref="Companies Act 2013 s.43")

    q(B, "kinds", "L2", "Cumulative preference dividend of Anand Ltd has not been paid for FY 2023-24 and FY 2024-25. At the AGM in September "
      "2026, the preference shareholders may vote:",
      "On every resolution placed before the company",
      [("Only on resolutions directly affecting their rights", "normal rule applied despite two years' arrears"),
       ("On every resolution, but only after three years of arrears", "trigger period overstated"),
       ("On no resolution, since preference shares carry no votes", "s.47(2) voting rights overlooked")],
      ["s.47(2): preference shareholders vote on resolutions directly affecting their rights, winding up, or repayment/reduction of capital.",
       "Proviso: where dividend has not been paid for two years or more, they vote on all resolutions."],
      "s.47(2): 2 years' arrears → vote on all resolutions",
      "Two years, not three, unlocks full voting.",
      ref="Companies Act 2013 s.47(2) and proviso")

    eqc, pfc, pfv, hold = 10, 5, 100, 1_00_000
    pref_share = pfc / (eqc + pfc)
    holder_pct = hold * pfv / (pfc * 1e7) * pref_share
    q(B, "kinds", "L3", f"Bharat Ltd has paid-up equity capital of ₹{eqc} crore (₹10 shares) and paid-up preference capital of ₹{pfc} crore "
      f"(₹{pfv} shares), on which dividend is in arrears for three years. On a poll, Ms Nidhi, holding {inr(hold)} preference shares, "
      "controls what share of the total voting power?",
      pct(holder_pct),
      [(pct(hold / (eqc * 1e7 / 10 + pfc * 1e7 / pfv)), "votes counted per share across both classes"),
       (pct(hold * pfv / (pfc * 1e7)), "share of preference capital alone reported"),
       (pct(hold * pfv / (eqc * 1e7)), "preference holding divided by equity capital")],
      [f"s.47(2) proviso: equity : preference voting rights = paid-up equity : paid-up preference = {eqc} : {pfc} → preference class holds {pct(pref_share)}.",
       f"Nidhi's share of preference capital = {inr(hold)} × ₹{pfv} ÷ ₹{pfc} crore = {pct(hold*pfv/(pfc*1e7))}.",
       f"Her voting power = {pct(hold*pfv/(pfc*1e7))} × {pct(pref_share)} = {pct(holder_pct)}."],
      "Class voting split in proportion to paid-up capital; individual share in proportion to paid-up in the class",
      "Votes follow paid-up capital, not the number of shares.",
      kind="numerical", ref="Companies Act 2013 s.47(1),(2) and provisos")

    # ---------- Loans to directors (standalone) ----------
    q(B, "loans", "L2", "Which of the following is prohibited by s.185(1)?",
      "A ₹50 lakh loan by S Ltd to a director of its holding company H Ltd for his personal use",
      [("A loan by a holding company to its wholly owned subsidiary", "s.185(3)(c) exception treated as prohibited"),
       ("A loan to the Managing Director as part of conditions of service extended to all employees", "s.185(3)(a) exception treated as prohibited"),
       ("A loan by a company that lends in the ordinary course of business, at interest not below the RBI bank rate", "s.185(3)(b) exception treated as prohibited")],
      ["s.185(1)(a): no loan to any director of the company or of its holding company, or any partner or relative of such director.",
       "s.185(3): exceptions for MD/WTD service conditions or SR scheme, ordinary-course lenders at ≥ bank rate, holding-to-WOS loans, guarantees for subsidiary bank loans."],
      "s.185(1) bar vs s.185(3) exceptions",
      "Directors of the holding company are within the bar.",
      ref="Companies Act 2013 s.185(1),(3)")

    pc_, bor = 10, 22
    lim_ = min(2 * pc_, 50)
    assert bor > lim_
    q(B, "loans", "L3", f"Kanchan Pvt Ltd has no body corporate as shareholder, paid-up capital of ₹{pc_} crore, bank borrowings of ₹{bor} crore "
      "and no default on those borrowings. It wants to lend to one of its directors. Which is correct?",
      f"s.185 applies — borrowings exceed the lower of twice paid-up capital (₹{2*pc_} crore) and ₹50 crore, so the private-company exemption is lost",
      [("Exempt — borrowings are below ₹50 crore", "'whichever is lower' limb ignored"),
       ("Exempt — all private companies are outside s.185", "conditional exemption treated as absolute"),
       ("Exempt — borrowings are below three times paid-up capital", "invented 3× test")],
      ["Private-company exemption (notification of 5 June 2015): s.185 does not apply to a private company (a) with no body corporate in its share capital, "
       "(b) borrowings from banks/FIs/bodies corporate less than twice paid-up capital or ₹50 crore, whichever is lower, and (c) no subsisting default.",
       f"Lower limit = min(2 × {pc_}, 50) = ₹{lim_} crore; borrowings ₹{bor} crore exceed it → exemption fails."],
      "Exemption needs all three conditions; borrowing limit = min(2 × PUC, ₹50 cr)",
      "Missing any one condition brings s.185 back in full.",
      ref="Companies Act 2013 s.185; MCA notification GSR 464(E) dated 5 June 2015 (private company exemptions)")

    # ---------- Maximum gap between Board meetings ----------
    q(B, "maxgap", "L1", "For a company other than an OPC, small or dormant company, the gap between two consecutive Board meetings must not exceed:",
      "120 days",
      [("90 days", "minimum gap for small companies' half-yearly meetings confused"),
       ("180 days", "half-year period assumed"),
       ("60 days", "invented limit")],
      ["s.173(1): at least four meetings a year with not more than 120 days intervening between two consecutive meetings."],
      "s.173(1): ≤ 120 days",
      "90 days is a minimum gap, and only for OPC/small/dormant companies.",
      ref="Companies Act 2013 s.173(1)")

    lastm = date(2026, 8, 14)
    cands = [date(2026, 11, 20), date(2026, 12, 5), date(2026, 12, 10), date(2026, 12, 20)]
    gaps = [(c - lastm).days - 1 for c in cands]
    viol = [c for c, g_ in zip(cands, gaps) if g_ > 120]
    assert len(viol) == 1 and all(abs(g_ - 120) >= 3 for g_ in gaps)
    q(B, "maxgap", "L2", f"The last Board meeting of Shreya Ltd was held on {D(lastm)}. Which proposed date for the next meeting would breach s.173(1)?",
      D(viol[0]),
      [(D(c), f"{g_} intervening days wrongly treated as exceeding 120") for c, g_ in zip(cands, gaps) if c != viol[0]],
      ["Days intervening (excluding both meeting dates): " + "; ".join(f"{D(c)} → {g_}" for c, g_ in zip(cands, gaps)) + ".",
       f"Only {D(viol[0])} exceeds 120 intervening days."],
      "Intervening days = (next − last) − 1 ≤ 120",
      "Count the days between the meetings, not the calendar months.",
      kind="numerical", ref="Companies Act 2013 s.173(1); SS-1")

    # ---------- Maximum directorships (standalone) ----------
    q(B, "maxdir", "L2", "Consider the following about the limit on directorships under s.165:\n\n"
      "1. Alternate directorships are counted within the overall limit of 20.\n"
      "2. A directorship in a private company that is a subsidiary of a public company is counted within the limit of 10 public companies.\n"
      "3. Directorships in dormant companies are counted within the overall limit of 20.\n\n"
      "Which are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "2017 exclusion of dormant companies overlooked"),
       ("2 only", "alternate directorships wrongly excluded"),
       ("1 and 3 only", "private subsidiaries of public companies wrongly excluded from the public count")],
      ["s.165(1): not more than 20 companies including alternate directorships; dormant companies excluded (2017).",
       "Proviso and Explanation: max 10 public companies, counting private companies that are holding or subsidiary of a public company."],
      "s.165(1): 20 (incl. alternate, excl. dormant); 10 public (incl. private holding/subsidiary of public)",
      "A private subsidiary of a public company is deemed public for this count.",
      kind="statement", ref="Companies Act 2013 s.165(1) (amended 2017)")

    q(B, "maxdir", "L3", "Ms Meera is a whole-time director of a listed company and an independent director on the boards of three other "
      "listed entities. She is offered an independent directorship on a fourth listed entity. Under SEBI (LODR) Regulations:",
      "She cannot accept, because a whole-time director of a listed entity can be an independent director in not more than three listed entities",
      [("She can accept, because the limit is seven listed entities", "general seven-entity cap applied, ignoring WTD restriction"),
       ("She can accept, because only the Companies Act limit of 20 companies applies", "LODR limits ignored"),
       ("She cannot accept, because a whole-time director cannot be an independent director anywhere", "limit exaggerated into a total bar")],
      ["LODR Reg 17A(1): no person to be a director in more than seven listed entities.",
       "Reg 17A(2): a person serving as WTD/MD in any listed entity shall be an independent director in not more than three listed entities."],
      "LODR 17A: ≤ 7 listed directorships; WTD/MD → ID in ≤ 3 listed",
      "The LODR caps sit on top of the s.165 limits.",
      ref="SEBI (LODR) Regulations 2015, Reg 17A; Companies Act 2013 s.165")

    # ---------- Misstatement in prospectus ----------
    q(B, "prospectus", "L1", "A prospectus is not valid if it is issued more than ____ after a copy is delivered to the Registrar.",
      "90 days",
      [("30 days", "invented window"),
       ("60 days", "invented window"),
       ("120 days", "invented window")],
      ["s.26(8): no prospectus shall be valid if issued more than 90 days after the date on which a copy is delivered to the Registrar."],
      "s.26(8): 90 days",
      "Filing must also be on or before the date of publication (s.26(4)).",
      ref="Companies Act 2013 s.26(4),(8)")

    q(B, "prospectus", "L2", "Investors who subscribed on the faith of a misleading prospectus of Sagarmala Ltd sue for compensation under s.35. "
      "Who among the following has a valid defence?",
      "A person who had consented to become a director but withdrew his consent before the issue, the prospectus being issued without his authority or consent",
      [("A director who did not read the prospectus before it was issued", "negligence treated as a defence"),
       ("A promoter who relied on the lead manager's draft", "reliance on intermediaries treated as a defence"),
       ("An expert whose misleading statement was included with his consent, never withdrawn", "expert liability overlooked")],
      ["s.35(1): company, directors, persons named as directors with consent, promoters, persons authorising issue and experts are liable.",
       "s.35(2)(a): no liability for a person who withdrew consent to become director before issue and the prospectus was issued without his authority/consent.",
       "s.35(2)(b): issued without his knowledge/consent and, on becoming aware, he gave reasonable public notice."],
      "s.35(2) defences: withdrawal of consent before issue; issue without knowledge + public notice",
      "Not reading the document is no defence.",
      ref="Companies Act 2013 s.35(1),(2)")

    amt_ = 2
    q(B, "prospectus", "L3", f"A court finds that the directors of Rudraksh Ltd knowingly included an untrue statement in a prospectus; the "
      f"fraud involves ₹{amt_} crore and involves public interest. Under s.34 read with s.447, the punishment is:",
      f"Imprisonment of not less than 3 years up to 10 years, and fine not less than ₹{amt_} crore up to ₹{3*amt_} crore",
      [(f"Imprisonment of 6 months to 10 years, and fine of ₹{amt_} crore to ₹{3*amt_} crore", "public-interest minimum of 3 years overlooked"),
       ("Imprisonment up to 5 years or fine up to ₹50 lakh, or both", "small non-public-interest fraud proviso applied"),
       (f"Imprisonment of not less than 3 years up to 10 years, and fine up to ₹{amt_} crore only", "fine range (up to three times) understated")],
      ["s.34: criminal liability for misstatements in prospectus → punishable under s.447.",
       f"s.447: imprisonment 6 months–10 years and fine from the amount involved up to three times; where public interest is involved, minimum 3 years.",
       f"Fine range = ₹{amt_} crore to 3 × {amt_} = ₹{3*amt_} crore."],
      "s.447: 6 m–10 y (3 y min if public interest); fine 1×–3× amount involved",
      "The ₹50 lakh alternative applies only to small frauds without public interest.",
      kind="numerical", ref="Companies Act 2013 s.34, s.447 (as amended 2019)")

    # ---------- NCLAT chairperson age ----------
    q(B, "nclatage", "L1", "The Chairperson of the NCLAT holds office until attaining the age of:",
      "70 years",
      [("67 years", "age limit for NCLAT Members applied"),
       ("65 years", "retirement age of Supreme Court judges applied"),
       ("62 years", "retirement age of High Court judges applied")],
      ["Chairperson of the Appellate Tribunal: until 70 years (s.413 as enacted; TRA 2021 tenure provisions struck down in Madras Bar Association v. UoI, 2025 INSC 1330 — Chairperson 70 / Members 67 per MBA directions).",
       "Members of the Appellate Tribunal: 67 years."],
      "NCLAT: Chairperson 70; Members 67",
      "The Chairperson is often a retired SC judge, so the limit exceeds 65.",
      ref="Companies Act 2013 s.413 (as enacted); Madras Bar Association v. UoI (MBA-IV/V directions; 2025 INSC 1330)")

    q(B, "nclatage", "L2", "Consider the following about the NCLAT:\n\n"
      "1. The Chairperson must be, or must have been, a Judge of the Supreme Court or the Chief Justice of a High Court.\n"
      "2. The Chairperson ceases to hold office on attaining 70 years.\n"
      "3. A Judicial Member ceases to hold office on attaining 67 years.\n"
      "4. A Technical Member may continue until 70 years.\n\n"
      "Select the correct answer:",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "Chairperson's age limit extended to Technical Members"),
       ("1 and 2 only", "Members' age limit overlooked"),
       ("2, 3 and 4 only", "qualification of Chairperson overlooked")],
      ["s.411(1): Chairperson — is/has been a Judge of the Supreme Court or Chief Justice of a High Court.",
       "Age limits: Chairperson 70; Members (judicial and technical) 67."],
      "NCLAT Chairperson: SC Judge / HC CJ; age 70. Members: 67",
      "All Members share the 67-year limit.",
      kind="statement", ref="Companies Act 2013 s.411(1), s.413 (as enacted); Madras Bar Association v. UoI (MBA-IV/V directions; 2025 INSC 1330)")

    # ---------- NRC (standalone) ----------
    q(B, "nrc", "L2", "Which of the following is NOT a function of the Nomination and Remuneration Committee under s.178?",
      "Approving transactions with related parties",
      [("Identifying persons qualified to become directors and senior management, and recommending their appointment and removal",
        "s.178(2) function treated as not NRC's"),
       ("Formulating criteria for qualifications, positive attributes and independence, and recommending a remuneration policy",
        "s.178(3) function treated as not NRC's"),
       ("Specifying the manner of effective evaluation of the performance of the Board, its committees and individual directors",
        "s.178(2) (amended 2017) function treated as not NRC's")],
      ["s.178(2)–(4): identification, appointment/removal recommendations, evaluation methodology, criteria and remuneration policy.",
       "RPT approval is an Audit Committee function (s.177(4)(iv))."],
      "NRC: people and pay; AC: accounts, audit and RPTs",
      "Related-party approvals sit with the Audit Committee.",
      ref="Companies Act 2013 s.178(2)-(4), s.177(4)(iv)")

    q(B, "nrc", "L3", "Ketaki Ltd, a listed company, proposes an NRC of four non-executive directors: two independent directors and two "
      "non-independent non-executive directors, chaired by an independent director. The composition is:",
      "Valid under the Companies Act but not under SEBI LODR, which requires at least two-thirds independent directors",
      [("Valid under both the Companies Act and SEBI LODR", "LODR two-thirds requirement overlooked"),
       ("Invalid under both, since a majority of independent directors is required", "Act's 'not less than one-half' misread as majority"),
       ("Invalid under the Companies Act but valid under SEBI LODR", "requirements reversed")],
      ["s.178(1): ≥ 3 NEDs, not less than one-half independent → 2 of 4 = one-half → valid.",
       "LODR Reg 19(1): all NEDs, at least two-thirds independent, chairperson independent → 2 of 4 < two-thirds → invalid."],
      "NRC: Act ½ IDs; LODR ⅔ IDs",
      "A listed company must meet the stricter LODR test.",
      ref="Companies Act 2013 s.178(1); SEBI (LODR) Regulations 2015, Reg 19(1)")

    # ---------- Notice for Board meeting ----------
    q(B, "noticebm", "L1", "A Board meeting must ordinarily be called by giving each director notice in writing of not less than:",
      "Seven days",
      [("Twenty-one clear days", "general-meeting notice period applied"),
       ("Three days", "adjourned general-meeting notice applied"),
       ("Fourteen days", "invented period")],
      ["s.173(3): not less than seven days' notice in writing to every director at his registered address, by hand, post or electronic means."],
      "s.173(3): 7 days",
      "21 clear days is for general meetings.",
      ref="Companies Act 2013 s.173(3)")

    q(B, "noticebm", "L2", "The Board of Yash Ltd meets on two days' notice to transact urgent business. No independent director attends. The "
      "decisions taken:",
      "Must be circulated to all directors and become final only on ratification by at least one independent director",
      [("Are void, since shorter notice is not permitted", "shorter-notice proviso overlooked"),
       ("Are final, since urgency justifies shorter notice", "ID-ratification condition overlooked"),
       ("Must be ratified by the members at the next general meeting", "ratifying authority misidentified")],
      ["s.173(3) proviso: shorter notice for urgent business if at least one ID is present; if absent, decisions are circulated to all directors and are final only on ratification by at least one ID."],
      "Short-notice meeting: ID present, or ID ratification afterwards",
      "Ratification is by an independent director, not the members.",
      ref="Companies Act 2013 s.173(3) provisos")

    # ---------- Video conferencing ----------
    q(B, "vc", "L1", "A director who participates in a Board meeting through video conferencing:",
      "Is counted for the purpose of quorum",
      [("Is not counted for quorum but may vote", "VC participation excluded from quorum"),
       ("Is counted for quorum only if the articles specifically allow it", "statutory recognition overlooked"),
       ("Is counted for quorum only in a private company", "invented restriction")],
      ["s.173(2): participation may be in person or through VC/other audio-visual means.",
       "Explanation to s.174(1): participation through VC is counted for quorum."],
      "VC participation counts for quorum (s.174(1) Explanation)",
      "The Act itself recognises VC presence; no article is needed.",
      ref="Companies Act 2013 s.173(2), s.174(1) Explanation")

    q(B, "vc", "L2", "Consider the following about Board meetings through video conferencing (position as of 2026):\n\n"
      "1. Directors participating through VC are counted for quorum.\n"
      "2. Approval of the annual financial statements cannot be transacted at a meeting held through VC.\n"
      "3. The VC facility must be capable of recording and recognising participation and of recording and storing the proceedings with date and time.\n\n"
      "Which are correct?",
      "1 and 3 only",
      [("1, 2 and 3", "Rule 4 restricted-items list, omitted in June 2021, treated as current"),
       ("1 only", "technical requirements of s.173(2) overlooked"),
       ("2 and 3 only", "quorum rule overlooked and omitted restriction applied")],
      ["s.174(1) Explanation: VC participants count for quorum → 1 correct.",
       "Rule 4 of the Meetings of Board Rules (items not to be dealt with via VC: annual accounts, Board's report, prospectus, mergers) was omitted by the 2021 amendment → 2 wrong.",
       "s.173(2): the means must record and recognise participation and record/store proceedings with date and time → 3 correct."],
      "s.173(2); s.174(1); Rule 4 omitted (2021)",
      "The restricted-matters list no longer exists.",
      kind="statement", ref="Companies Act 2013 s.173(2), s.174(1); Companies (Meetings of Board and its Powers) Amendment Rules 2021 (omission of Rule 4)")

    # ---------- Dividend within thirty days (standalone) ----------
    a_amt, a_days, b_amt, b_days, c_amt = 1_50_000, 40, 80_000, 60, 50_000
    ia = a_amt * 0.18 * a_days / 365
    ib = b_amt * 0.18 * b_days / 365
    q(B, "div30", "L3", "Mahi Ltd paid three shareholders after the 30-day window:\n\n"
      "| Shareholder | Dividend (₹) | Days of delay beyond window | Reason |\n|---|---:|---:|---|\n"
      f"| A | {inr(a_amt)} | {a_days} | Administrative oversight |\n"
      f"| B | {inr(b_amt)} | {b_days} | Genuine dispute about entitlement |\n"
      f"| C | {inr(c_amt)} | — | Lawfully adjusted against unpaid calls |\n\n"
      "The total s.127 interest Mahi must pay is (nearest rupee):",
      R(ia),
      [(R(ia + ib), "interest charged on the disputed dividend"),
       (R(a_amt * 0.12 * a_days / 365), "12% rate used"),
       (R(a_amt * 0.18), "a full year's interest charged on A")],
      [f"A: no exception → {inr(a_amt)} × 18% × {a_days}/365 = {R(ia)}.",
       "B: dispute regarding the right to receive → statutory exception; no interest.",
       "C: lawful adjustment against a sum due → exception.",
       f"Total = {R(ia)}."],
      "s.127 interest @ 18% p.a. only where no proviso applies",
      "Screen each shareholder against the exceptions before computing.",
      kind="numerical", ref="Companies Act 2013 s.127 and provisos")

    # ---------- Powers exercisable only at a Board meeting ----------
    q(B, "powers", "L1", "Which of the following powers must be exercised by the Board only by a resolution passed at a meeting (not by circulation)?",
      "Making calls on shareholders in respect of money unpaid on their shares",
      [("Approving registration of transmission of shares", "routine power treated as s.179(3) power"),
       ("Affixing the common seal to a share certificate", "ministerial act treated as s.179(3) power"),
       ("Opening a salary bank account", "operational act treated as s.179(3) power")],
      ["s.179(3): calls; buy-back authorisation; issue of securities; borrowing; investing funds; loans/guarantees/security; financial statements and Board's report; "
       "diversification; amalgamation/merger; takeover; and matters in Rule 8."],
      "s.179(3) list — meeting-only powers",
      "Calls on shares head the statutory list.",
      ref="Companies Act 2013 s.179(3); Rule 8, Meetings of Board Rules 2014")

    q(B, "powers", "L2", "Which of the following s.179(3) powers may the Board delegate to a committee, the managing director, the manager or "
      "a principal officer?",
      "Borrowing money, investing the company's funds, and granting loans or giving guarantees/security",
      [("Making calls, approving the financial statements and authorising buy-back", "non-delegable powers treated as delegable"),
       ("Issuing securities, approving amalgamation and diversifying the business", "non-delegable powers treated as delegable"),
       ("All s.179(3) powers, if the articles so provide", "articles treated as overriding the statutory limit")],
      ["s.179(3) proviso: powers under clauses (d) borrow, (e) invest and (f) grant loans/guarantees/security may be delegated on such conditions as the Board specifies."],
      "Delegable: (d), (e), (f) only",
      "Only the treasury-type powers can be delegated.",
      ref="Companies Act 2013 s.179(3) proviso")

    puc_, frz_, sp_, rev_, tl, tmp, new = 40, 55, 15, 15, 70, 12, 35
    limit = puc_ + frz_ + sp_
    after = tl + new
    assert after <= limit < after + tmp and after > puc_ + frz_
    q(B, "powers", "L3", "Latest audited figures of Pallav Ltd (₹ crore): paid-up capital "
      f"{puc_}; free reserves {frz_}; securities premium {sp_}; revaluation reserve {rev_}. Existing borrowings: term loans {tl} and "
      f"temporary loans (repayable within six months, ordinary course) {tmp}. It proposes a new term loan of ₹{new} crore. Which is correct?",
      f"A Board resolution at a meeting suffices — borrowings excluding temporary loans (₹{after} crore) are within ₹{limit} crore",
      [(f"A special resolution is needed — total borrowings including temporary loans (₹{after + tmp} crore) exceed ₹{limit} crore",
        "temporary loans wrongly included"),
       (f"A special resolution is needed — the limit is paid-up capital plus free reserves (₹{puc_ + frz_} crore)", "securities premium omitted from the limit"),
       (f"A special resolution is needed — any borrowing above 60% of paid-up capital, free reserves and premium (₹{0.6*limit:g} crore) requires it",
        "s.186 loan/investment limit confused with s.180 borrowing limit")],
      [f"s.180(1)(c) limit = paid-up + free reserves + securities premium = {puc_}+{frz_}+{sp_} = ₹{limit} crore (revaluation reserve excluded).",
       f"Temporary loans obtained in the ordinary course are excluded → {tl} + {new} = ₹{after} crore ≤ {limit}.",
       "Borrowing is a s.179(3)(d) power → resolution at a Board meeting."],
      "s.180(1)(c): borrowings (excl. temporary loans) > PUC + FR + SP → special resolution",
      "Temporary loans are carved out of the s.180 count.",
      kind="numerical", ref="Companies Act 2013 s.179(3)(d), s.180(1)(c) and Explanation")

    # ---------- Auditor's powers, duties and report ----------
    q(B, "auditrep", "L2", "Under s.143(1), the auditor shall inquire into which of the following?\n\n"
      "1. Whether loans and advances made on the basis of security have been properly secured.\n"
      "2. Whether personal expenses have been charged to revenue account.\n"
      "3. Whether loans and advances have been shown as deposits.\n"
      "4. Whether the company's dividend policy is optimal.\n\n"
      "Select the correct answer:",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "business-judgment matter added to statutory inquiries"),
       ("1 and 2 only", "loans shown as deposits overlooked"),
       ("2, 3 and 4 only", "security for loans overlooked")],
      ["s.143(1)(a)–(f): loans/advances properly secured; book-entry transactions not prejudicial; securities sold below cost (non-investment companies); "
       "loans shown as deposits; personal expenses charged to revenue; cash actually received for shares allotted for cash."],
      "s.143(1) six inquiries",
      "Auditors test stewardship, not commercial policy.",
      kind="statement", ref="Companies Act 2013 s.143(1)")

    to_, br = 42, 28
    assert to_ < 50 and br >= 25  # exemption needs both → fails
    q(B, "auditrep", "L3", f"Hira Pvt Ltd (not an OPC or small company) had turnover of ₹{to_} crore per its latest audited financial "
      f"statements; its bank borrowings peaked at ₹{br} crore during the year. It has filed all financial statements and annual returns on time. "
      "Is the auditor required to report on the adequacy and operating effectiveness of internal financial controls under s.143(3)(i)?",
      f"Yes — exemption needs turnover < ₹50 crore and borrowings < ₹25 crore; borrowings hit ₹{br} crore",
      [(f"No — turnover of ₹{to_} crore below ₹50 crore alone exempts it, despite the ₹{br} crore borrowings",
        "pre-corrigendum 'or' reading: tests treated as alternatives"),
       ("No — any private company is exempt from IFC reporting if all its filings are made on time", "filing condition treated as the whole test"),
       (f"No — the exemption is lost only if bank borrowings exceed ₹50 crore; here they are ₹{br} crore", "borrowing threshold overstated")],
      ["Private-company exemption (GSR 583(E), 13 June 2017, as corrected by corrigendum dated 13 July 2017): s.143(3)(i) does not apply to an OPC or small company, or to a private company "
       "with turnover < ₹50 crore per latest audited FS AND aggregate borrowings from banks/FIs/bodies corporate < ₹25 crore at any time in the year, "
       "provided it has not defaulted in filing under s.137 or s.92.",
       f"Turnover ₹{to_} crore < ₹50 crore, but borrowings ₹{br} crore ≥ ₹25 crore → exemption fails → IFC reporting applies."],
      "IFC reporting exemption: private co with turnover < ₹50 cr AND borrowings < ₹25 cr (and no filing default)",
      "The corrigendum replaced 'or' with 'and' — both tests must be met.",
      ref="Companies Act 2013 s.143(3)(i); MCA notification GSR 583(E) dated 13 June 2017 as corrected by corrigendum dated 13 July 2017")

    q(B, "auditrep", "L3", "Neha Pvt Ltd is not a holding or subsidiary of a public company. Its paid-up capital plus reserves and surplus is "
      "₹80 lakh, total revenue ₹9 crore, and its borrowings from banks peaked at ₹1.3 crore during the year. CARO 2020:",
      "Applies, because borrowings exceeded ₹1 crore at a point during the year",
      [("Does not apply, because revenue is below ₹10 crore", "conditions for exemption treated as alternatives"),
       ("Does not apply, because capital plus reserves is below ₹1 crore", "conditions for exemption treated as alternatives"),
       ("Applies only if the company is listed", "CARO scope confused with listing")],
      ["CARO 2020 para 1(2)(v): a private company (not holding/subsidiary of a public company) is exempt only if paid-up capital + reserves ≤ ₹1 crore, "
       "borrowings ≤ ₹1 crore at any point in the year, AND total revenue ≤ ₹10 crore.",
       "Borrowings of ₹1.3 crore breach one condition → CARO applies."],
      "CARO private-company exemption: all three conditions (₹1 cr / ₹1 cr / ₹10 cr) together",
      "Unlike the IFC exemption, the CARO exemption is cumulative.",
      ref="Companies (Auditor's Report) Order 2020 para 1(2)(v), issued under s.143(11)")
