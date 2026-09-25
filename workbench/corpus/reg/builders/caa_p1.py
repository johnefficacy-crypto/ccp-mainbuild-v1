"""REG-CORPUS-CA-A part 1: case sets A (managerial remuneration), B (buy-back/bonus), C (committee applicability)."""
from fractions import Fraction
from caa_common import q, inr, R, L, Cr, pct


def add_all(B):
    # ================= CASE A — Vellora Engineering Ltd (s.197/198, Schedule V) =================
    g = "CAA-CASE-A"
    rev, sub, land, fvg = 21500, 140, 420, 95
    opx, intr, dep, lossdiv, exgr, dmg, tax = 17300, 480, 1050, 210, 60, 75, 700
    np198 = rev + sub - opx - intr - dep - dmg
    book = rev + sub + land + fvg - opx - intr - dep - lossdiv - exgr - dmg
    assert np198 == 2735 and book == 2980
    A = ("**Case — Vellora Engineering Ltd.** Vellora is a listed public company. Its Board has one Managing Director, "
         "two Whole-time Directors and four non-executive directors (two of them independent). The statement of profit "
         "and loss for FY 2025-26, drawn up **before** charging any managerial remuneration, shows (₹ lakh):\n\n"
         "| Item | ₹ lakh |\n|---|---:|\n"
         f"| Revenue from operations | {inr(rev)} |\n"
         f"| Subsidy received from the Central Government | {inr(sub)} |\n"
         f"| Profit on sale of freehold factory land (Vellora does not deal in property) | {inr(land)} |\n"
         f"| Unrealised fair-value gain on investments measured at FVTPL | {inr(fvg)} |\n"
         f"| Operating expenses (usual working charges, including staff bonus) | {inr(opx)} |\n"
         f"| Interest on debentures and secured term loans | {inr(intr)} |\n"
         f"| Depreciation as per Schedule II | {inr(dep)} |\n"
         f"| Loss on sale of a business division (an undertaking) | {inr(lossdiv)} |\n"
         f"| Ex-gratia payment to a former distributor (no legal liability) | {inr(exgr)} |\n"
         f"| Damages paid under a court decree for breach of contract | {inr(dmg)} |\n"
         f"| Provision for income tax | {inr(tax)} |\n")
    ref198 = "Companies Act 2013 s.198(2)-(5) (as amended 2017: fair-value changes excluded)"

    q(B, "divprof", "L4", A + "\nThe net profit of Vellora for the purpose of s.197, computed under s.198, is:",
      L(np198),
      [(L(np198 + land), "capital profit on sale of land credited"),
       (L(np198 - tax), "income tax deducted, though s.198(5) excludes it"),
       (L(np198 - lossdiv - exgr), "capital loss and voluntary ex-gratia payment deducted")],
      [f"Credit: revenue {inr(rev)} + Government subsidy {inr(sub)} (s.198(2) allows bounties/subsidies) = {inr(rev+sub)}.",
       f"No credit: land profit {inr(land)} (capital, s.198(3)) and unrealised fair-value gain {inr(fvg)} (s.198(3)).",
       f"Deduct: working charges {inr(opx)}, interest {inr(intr)}, Schedule II depreciation {inr(dep)}, court-decree damages {inr(dmg)} (legal liability).",
       f"Not deducted: capital loss on sale of undertaking {inr(lossdiv)}, voluntary ex-gratia {inr(exgr)}, income tax {inr(tax)} (s.198(5)).",
       f"Net profit = {inr(rev+sub)} − {inr(opx+intr+dep+dmg)} = ₹{inr(np198)} lakh."],
      "s.198 profit = revenue items credited − s.198(4) deductions; capital/fair-value items and income tax ignored",
      "Book profit before tax is not the s.198 profit; capital profits and losses both stay out.",
      kind="case", group=g, ref=ref198)

    cap = 0.11 * np198
    q(B, "divprof", "L4", A + "\nThe overall ceiling on total managerial remuneration for FY 2025-26 under s.197(1), before any shareholder "
      "authorisation to exceed it, is:",
      L(cap, 2),
      [(L(0.11 * book, 2), "11% applied to book profit before tax instead of s.198 profit"),
       (L(0.10 * np198, 2), "10% sub-limit for executive directors taken as the overall ceiling"),
       (L(0.11 * (np198 - tax), 2), "income tax deducted before applying 11%")],
      [f"s.198 net profit = ₹{inr(np198)} lakh (working in the case).",
       f"Overall ceiling = 11% × {inr(np198)} = ₹{inr(cap, 2)} lakh."],
      "Total managerial remuneration ≤ 11% of s.198 net profit (s.197(1))",
      "The 11% runs on the s.198 figure, not on PBT; 10% is only the executive-director sub-limit.",
      kind="case", group=g, ref="Companies Act 2013 s.197(1), s.198")

    md, wtd, ned = 130, 75, 29
    ex = md + 2 * wtd
    lim_ex, lim_ned, lim_all = 0.10 * np198, 0.01 * np198, 0.11 * np198
    tot = ex + ned
    assert ex > lim_ex and ned > lim_ned and tot > lim_all
    assert ex <= 0.10 * book and ned <= 0.01 * book and tot <= 0.11 * book
    assert md <= 0.05 * np198 and wtd <= 0.05 * np198
    q(B, "divprof", "L4", A + f"\nThe Board proposes for FY 2025-26: MD ₹{md} lakh, each WTD ₹{wtd} lakh, and commission of ₹{ned} lakh "
      "in total to the non-executive directors (sitting fees separate). Without any special resolution, which limits of s.197(1) "
      "would the proposal breach?",
      "The 10% limit for executive directors, the 1% limit for non-executive directors and the 11% overall ceiling",
      [("Only the 10% executive-director limit; NED commission is within the 3% limit",
        "3% NED limit applied though the company has an MD/WTD (1% applies)"),
       ("Only the 1% NED limit; executive pay is tested against 11%", "11% overall ceiling used instead of the 10% executive sub-limit"),
       ("None of the limits", "all limits tested against book profit before tax (₹2,980 lakh)")],
      [f"s.198 profit ₹{inr(np198)} lakh → 10% = {inr(lim_ex,2)}; 1% = {inr(lim_ned,2)}; 11% = {inr(lim_all,2)}.",
       f"Executive directors: {md} + 2 × {wtd} = {ex} > {inr(lim_ex,2)} → breached.",
       f"NEDs: {ned} > {inr(lim_ned,2)} (1% applies because there is an MD/WTD) → breached.",
       f"Total: {tot} > {inr(lim_all,2)} → overall ceiling exceeded."],
      "Sub-limits: MD/WTDs together 10% (more than one), NEDs 1% (3% if no MD/WTD/manager); overall 11%",
      "On book PBT everything would look compliant — that is exactly the error the s.198 computation guards against.",
      kind="case", group=g, ref="Companies Act 2013 s.197(1) provisos")

    q(B, "divprof", "L4", A + "\nVellora pays each independent director a sitting fee of ₹90,000 per Board meeting. Consider:\n\n"
      "1. The sitting fee is within the ceiling prescribed under the Rules.\n"
      "2. Sitting fees are excluded when testing the 11% ceiling of s.197(1).\n"
      "3. The independent directors may, in addition, be granted stock options if the shareholders approve by special resolution.\n\n"
      "Which of the statements is/are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "stock options to independent directors wrongly allowed (s.197(7) bars them)"),
       ("2 only", "sitting-fee ceiling wrongly taken as below ₹90,000"),
       ("1 and 3 only", "sitting fees wrongly counted within the 11% ceiling")],
      ["Rule 4, Companies (Appointment and Remuneration of Managerial Personnel) Rules 2014: sitting fee up to ₹1 lakh per meeting → 1 correct.",
       "s.197(2): the percentages are exclusive of sitting fees under s.197(5) → 2 correct.",
       "s.197(7)/s.149(9): an independent director is not entitled to any stock option → 3 wrong."],
      "Sitting fee ≤ ₹1 lakh per meeting; outside the 11%; IDs get fees, reimbursement and profit-linked commission only",
      "No shareholder resolution can unlock ESOPs for independent directors.",
      kind="case", group=g, ref="Companies Act 2013 s.197(2),(5),(7); Rule 4 of Managerial Personnel Rules 2014")

    pu, sam, sp_, gr, rr, ltl, cc, inv, pre = 30, 5, 20, 25, 25, 40, 15, 22, 1
    ec = pu + sp_ + gr + ltl - inv - pre
    assert ec == 92

    def band(x):
        return 60 if x < 5 else 84 if x < 100 else 120 if x < 250 else 120 + 0.0001 * (x - 250) * 100
    lim = band(ec)
    assert lim == 84 and band(ec + rr) == 120 and band(ec + inv) == 120
    q(B, "divprof", "L4", A + "\nVellora re-appoints its MD in FY 2026-27, a year in which its profits turn out to be inadequate. Figures as at 31 March 2026 (₹ crore):\n\n"
      "| Item | ₹ crore |\n|---|---:|\n"
      f"| Paid-up equity share capital | {pu} |\n| Share application money pending allotment | {sam} |\n"
      f"| Securities premium | {sp_} |\n| General reserve | {gr} |\n| Revaluation reserve | {rr} |\n"
      f"| Long-term term loan (repayable after one year) | {ltl} |\n| Cash-credit (working capital) | {cc} |\n"
      f"| Non-current investments (Vellora is not an investment company) | {inv} |\n| Preliminary expenses not written off | {pre} |\n\n"
      "Under Item (A) of Section II, Part II of Schedule V, the maximum yearly remuneration payable to the MD, where the "
      "shareholders' approval is by ordinary resolution and all other conditions are met, is:",
      L(lim),
      [(L(120), "revaluation reserve added, or investments not deducted, pushing effective capital into the ₹100–250 crore band"),
       (L(2 * lim), "doubling applied, though doubling is available only with a special resolution"),
       (L(60), "effective-capital band below ₹5 crore applied")],
      [f"Effective capital = paid-up {pu} + premium {sp_} + reserves {gr} + long-term loan {ltl} − investments {inv} − preliminary expenses {pre} = ₹{ec} crore.",
       f"Excluded: share application money ({sam}), revaluation reserve ({rr}), working-capital loan ({cc}).",
       f"₹{ec} crore falls in the '₹5 crore to less than ₹100 crore' band → ₹84 lakh a year.",
       "The limit doubles only if the approving resolution is a special resolution."],
      "Schedule V, Part II, Sec. II(A): <₹5 cr → ₹60 L; ₹5–<100 cr → ₹84 L; ₹100–<250 cr → ₹120 L; ≥₹250 cr → ₹120 L + 0.01% of excess",
      "Revaluation reserve and working-capital borrowings never enter effective capital.",
      kind="case", group=g, ref="Companies Act 2013 Schedule V Part II Section II and Explanation I (effective capital), as revised 2016")

    # ================= CASE B — Sarang Polymers Ltd (s.68-70, s.63) =================
    g = "CAA-CASE-B"
    eq, prem, genr, ret, reval, crr, sec, uns = 50, 20, 45, 25, 15, 5, 170, 50
    fv = 10
    shares = eq * 1e7 / fv
    debt = sec + uns
    base = eq + prem + genr + ret
    assert base == 140 and debt == 220
    lim25 = 0.25 * base
    de_cap = base - debt / 2
    mx = min(lim25, de_cap)
    assert mx == 30
    Bs = ("**Case — Sarang Polymers Ltd.** Sarang is an unlisted public company whose articles authorise buy-back. It has never "
          "defaulted on deposits, debentures, preference shares or loans, and has filed all returns. Extract of its latest audited "
          "balance sheet (31 March 2026, ₹ crore):\n\n| Item | ₹ crore |\n|---|---:|\n"
          f"| Equity share capital (₹{fv} each, fully paid) | {eq} |\n| Securities premium | {prem} |\n| General reserve | {genr} |\n"
          f"| Retained earnings | {ret} |\n| Revaluation reserve | {reval} |\n| Capital redemption reserve | {crr} |\n"
          f"| Secured term loans | {sec} |\n| Unsecured loans | {uns} |\n")
    q(B, "buyback", "L4", Bs + "\nWith a special resolution, the maximum amount Sarang can spend on a buy-back of equity shares is:",
      Cr(mx),
      [(Cr(lim25), "25% cap applied but post-buy-back debt-equity test ignored"),
       (Cr(0.10 * base), "10% Board-route cap applied to a special-resolution buy-back"),
       (Cr(min(0.25 * (base + reval + crr), base + reval + crr - debt / 2)), "revaluation reserve and CRR treated as free reserves")],
      [f"Paid-up capital + free reserves (securities premium counts for s.68; revaluation reserve and CRR do not) = {eq}+{prem}+{genr}+{ret} = ₹{base} crore.",
       f"25% cap = ₹{lim25:g} crore.",
       f"Debt-equity after buy-back ≤ 2:1 → {debt} ≤ 2 × ({base} − X) → X ≤ ₹{de_cap:g} crore.",
       f"Binding limit = lower of the two = ₹{mx:g} crore."],
      "Buy-back ≤ 25% of (paid-up + free reserves) AND post-buy-back debt ≤ 2 × (paid-up + free reserves)",
      "The debt-equity test often binds before the 25% cap.",
      kind="case", group=g, ref="Companies Act 2013 s.68(2)(b),(c),(d) and Explanation (free reserves include securities premium)")

    q(B, "buyback", "L4", Bs + "\nIf the buy-back is to be authorised by a Board resolution alone (no special resolution), the maximum amount is:",
      Cr(0.10 * base),
      [(Cr(0.10 * eq), "10% applied to paid-up capital only, ignoring free reserves"),
       (Cr(0.10 * (base + reval)), "revaluation reserve included in free reserves"),
       (Cr(lim25), "25% special-resolution cap used for the Board route")],
      [f"Board route: up to 10% of total paid-up equity capital and free reserves = 10% × {base} = ₹{0.10*base:g} crore.",
       "Revaluation reserve and CRR are not free reserves."],
      "Board-resolution buy-back ≤ 10% of (paid-up equity capital + free reserves)",
      "10% for the Board route; 25% needs a special resolution.",
      kind="case", group=g, ref="Companies Act 2013 s.68(2)(b) proviso")

    n_bb, price = 12_00_000, 240
    consid = n_bb * price / 1e7
    nominal = n_bb * fv / 1e7
    q(B, "buyback", "L4", Bs + f"\nSarang buys back {inr(n_bb)} shares at ₹{price} each, paid out of the general reserve and securities premium. "
      "The amount to be transferred to the capital redemption reserve under s.69 is:",
      Cr(nominal),
      [(Cr(consid), "entire buy-back consideration transferred"),
       (Cr(consid - nominal), "premium element transferred instead of nominal value"),
       ("Nil, because part of the payment comes from securities premium", "s.69 wrongly read as applying only to free reserves")],
      [f"Nominal value of shares bought back = {inr(n_bb)} × ₹{fv} = ₹{nominal:.2f} crore.",
       "s.69: where shares are bought out of free reserves or securities premium, a sum equal to the nominal value goes to CRR."],
      "Transfer to CRR = nominal value of shares bought back (s.69)",
      "It is the nominal value, not the price paid, that is ring-fenced.",
      kind="case", group=g, ref="Companies Act 2013 s.69(1)")

    q(B, "buyback", "L4", Bs + "\nOn the buy-back process, consider:\n\n"
      "1. The buy-back must be completed within one year of the resolution authorising it.\n"
      "2. Shares bought back must be extinguished and physically destroyed within seven days of the last date of completion.\n"
      "3. Sarang cannot make any further issue of equity shares for one year after completion, not even by way of a bonus issue.\n"
      "4. A return of the buy-back must be filed with the Registrar within thirty days of completion.\n\n"
      "Which of the statements are correct?",
      "1, 2 and 4 only",
      [("1, 2, 3 and 4", "six-month bar (with bonus exception) misread as one year without exception"),
       ("1 and 2 only", "return-filing window misremembered"),
       ("2, 3 and 4 only", "completion window misread (and further-issue bar overstated)")],
      ["s.68(4): complete within one year of the special/Board resolution → 1 correct.",
       "s.68(7): extinguish and physically destroy within 7 days of last date of completion → 2 correct.",
       "s.68(8): no further issue of the same kind for 6 months, except bonus, conversion of warrants/ESOP/sweat equity/preference or debentures → 3 wrong.",
       "s.68(10): return with the Registrar (and SEBI for listed) within 30 days of completion → 4 correct."],
      "1 year to complete; 7 days to extinguish; 6-month issue bar; 30-day return",
      "Bonus issues are expressly carved out of the six-month bar.",
      kind="case", group=g, ref="Companies Act 2013 s.68(4),(7),(8),(10)")

    elig = prem + genr + ret + crr
    r = Fraction(elig, eq)
    r_rev = Fraction(elig + reval, eq)
    r_nocrr = Fraction(elig - crr, eq)
    r_nosp = Fraction(elig - prem, eq)

    def fmt(fr):
        fr10 = fr * 10
        assert fr10.denominator == 1
        return f"{fr10.numerator} bonus shares for every 10 held"
    q(B, "bonus", "L4", Bs + "\nInstead of a buy-back, the Board considers a bonus issue of fully paid equity shares out of every reserve that "
      "may lawfully be capitalised. Ignoring any buy-back, the maximum bonus ratio is:",
      fmt(r),
      [(fmt(r_rev), "revaluation reserve capitalised"),
       (fmt(r_nocrr), "capital redemption reserve wrongly excluded"),
       (fmt(r_nosp), "securities premium wrongly excluded")],
      [f"s.63(1): bonus may come from free reserves, securities premium and CRR; not from revaluation reserve.",
       f"Available = premium {prem} + general reserve {genr} + retained earnings {ret} + CRR {crr} = ₹{elig} crore.",
       f"Ratio = {elig} ÷ {eq} = {float(r):.1f} → {fmt(r)}."],
      "Bonus capacity = (free reserves + securities premium + CRR) ÷ paid-up capital",
      "Revaluation reserve is expressly barred for bonus issues.",
      kind="case", group=g, ref="Companies Act 2013 s.63(1) and proviso")

    # ================= CASE C — Tarini Agro Foods Ltd (IDs, AC, NRC, cost audit) =================
    g = "CAA-CASE-C"
    pc, to, oil, bak, borr = 8, 140, 120, 20, 42
    C = ("**Case — Tarini Agro Foods Ltd.** Tarini is an unlisted public company (not a joint venture, wholly owned subsidiary or "
         "dormant company). Per its latest audited financial statements (31 March 2026): paid-up share capital ₹" + f"{pc}"
         + f" crore; turnover ₹{to} crore (refined edible oil ₹{oil} crore, bakery ₹{bak} crore — all products fall in Table B "
         f"(non-regulated sectors) of Rule 3 of the Companies (Cost Records and Audit) Rules, 2014); aggregate outstanding loans, "
         f"debentures and deposits ₹{borr} crore.\n\nBoard (7): **A** — Executive Chairman (promoter); **B** — Managing Director; "
         "**C** — Whole-time Director; **D** and **E** — independent directors; **F** — nominee director of the lending bank; "
         "**G** — non-executive director from the promoter group. D and E can read and understand financial statements.\n")
    q(B, "boardcomp", "L4", C + "\nThe minimum number of independent directors Tarini must have is:",
      "2",
      [("3", "one-third rule for listed companies applied (7 ÷ 3 rounded up)"),
       ("None", "thresholds read cumulatively; paid-up capital below ₹10 crore taken as decisive"),
       ("1", "single-ID requirement assumed")],
      [f"Rule 4, Appointment and Qualification of Directors Rules: public companies with paid-up capital ≥ ₹10 crore, OR turnover ≥ ₹100 crore, OR aggregate loans/debentures/deposits > ₹50 crore need at least two IDs.",
       f"Tarini: turnover ₹{to} crore ≥ ₹100 crore → at least 2 IDs (the tests are alternatives)."],
      "Unlisted public company meeting any one Rule 4 test → minimum 2 IDs",
      "The one-third rule of s.149(4) is for listed companies.",
      kind="case", group=g, ref="Companies Act 2013 s.149(4); Rule 4, Companies (Appointment and Qualification of Directors) Rules 2014")

    q(B, "ac", "L4", C + "\nWhich proposed Audit Committee composition complies with s.177?",
      "D (Chair), E and F",
      [("D (Chair) and E", "fewer than the minimum three directors"),
       ("A (Chair), D and F", "independent directors not in majority"),
       ("D (Chair), F and G", "only one of three members independent")],
      ["s.177(2): minimum three directors, independent directors forming a majority; majority incl. Chair able to read financial statements.",
       "D, E, F → 3 members, 2 IDs (majority), D and E financially literate → compliant.",
       "Tarini must have an AC because it crosses the Rule 6 turnover test (≥ ₹100 crore)."],
      "AC: ≥3 directors; IDs majority; majority incl. Chair financially literate",
      "A nominee director is non-executive but not independent — he cannot supply the ID majority.",
      kind="case", group=g, ref="Companies Act 2013 s.177(1)-(2); Rule 6, Companies (Meetings of Board and its Powers) Rules 2014")

    q(B, "nrc", "L4", C + "\nWhich proposed Nomination and Remuneration Committee complies with s.178(1)?",
      "E (Chair), D and F",
      [("A (Chair), D and E", "chairperson of the company made chair of the NRC"),
       ("D (Chair), F and G", "independent directors less than one-half"),
       ("D (Chair), E and C", "a whole-time (executive) director included; three non-executive directors needed")],
      ["s.178(1): three or more non-executive directors, not less than one-half independent.",
       "Chairperson of the company may be a member but shall not chair the NRC.",
       "E, D, F → all non-executive; 2 of 3 independent → compliant."],
      "NRC: ≥3 NEDs; ≥½ IDs; company chairperson may join but not chair",
      "Two IDs out of three satisfies 'not less than one-half'.",
      kind="case", group=g, ref="Companies Act 2013 s.178(1)")

    q(B, "cost", "L4", C + "\nRegarding cost audit for FY 2026-27, which is correct?",
      "Cost audit applies; the Board must appoint a cost accountant in practice within 180 days of the start of the financial year, and the statutory auditor cannot be appointed",
      [("Only cost records apply; Table B cost audit needs overall turnover of ₹150 crore", "Table B threshold overstated"),
       ("Cost audit applies; the cost auditor is appointed by shareholders at the AGM", "appointing authority confused with s.139 statutory auditor"),
       ("Cost audit applies; the statutory auditor may also be the cost auditor", "s.148(3) bar on statutory auditor ignored")],
      [f"Table B: cost audit if overall turnover ≥ ₹100 crore and turnover of individual product(s) ≥ ₹35 crore.",
       f"Tarini: overall ₹{to} crore; edible oil ₹{oil} crore → cost audit applies.",
       "Rule 6(2): Board appoints on AC recommendation within 180 days of commencement of FY; s.148(3): a cost accountant; the s.139 auditor is barred."],
      "Table B: overall ≥ ₹100 cr and product ≥ ₹35 cr; Table A: ≥ ₹50 cr and ≥ ₹25 cr",
      "Maintenance of records starts at ₹35 crore overall; audit needs the higher Table A/B tests.",
      kind="case", group=g, ref="Companies Act 2013 s.148(3); Companies (Cost Records and Audit) Rules 2014, Rules 3, 4, 6")

    q(B, "idelig", "L4", C + "\nTarini wants to appoint a further independent director in FY 2026-27. Candidates:\n\n"
      "- **P** ceased to be CFO of Tarini's subsidiary during FY 2024-25.\n"
      "- **Q** ceased to be a partner of Tarini's statutory audit firm during FY 2021-22.\n"
      "- **S** holds, together with his relatives, 2.4% of the total voting power of Tarini.\n"
      "- **T** is a director of a non-profit organisation that receives 30% of its receipts from Tarini's promoters.\n\n"
      "Who is eligible?",
      "Q only",
      [("P and Q only", "KMP of a subsidiary within the three preceding FYs overlooked"),
       ("Q and T only", "NPO test (25% of receipts from company/promoters) missed"),
       ("Q and S only", "2% voting-power ceiling missed")],
      ["s.149(6)(e)(i): no KMP of company/holding/subsidiary/associate in any of the 3 FYs preceding the FY of appointment (2023-24 to 2025-26) → P out.",
       "s.149(6)(e)(ii)(A): partner of audit firm in those 3 FYs is barred; Q left in 2021-22 → eligible.",
       "s.149(6)(e)(iii): holds with relatives 2% or more of voting power → S out.",
       "s.149(6)(e)(iv): chief executive/director of NPO getting 25% or more of receipts from company/promoters → T out."],
      "Three-FY look-back for KMP/audit-firm links; 2% voting power; 25% NPO receipts",
      "The look-back counts financial years before the FY of appointment, so 2021-22 is outside it.",
      kind="case", group=g, ref="Companies Act 2013 s.149(6)(e)")
