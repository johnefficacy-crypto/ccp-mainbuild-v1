"""REG-CORPUS-CA-A part 2: case sets D (auditors), E (dividend payment), F (directors)."""
from caa_common import q, inr, R, L, Cr, D, date, timedelta


def add_all(B):
    # ================= CASE D — Aravali Textiles Ltd (auditors) =================
    g = "CAA-CASE-D"
    Dd = ("**Case — Aravali Textiles Ltd.** Aravali is an unlisted public company with paid-up share capital of ₹12 crore; it has "
          "constituted an Audit Committee. Its statutory auditor, the firm **K&M Associates**, was appointed at the AGM of 2016 until "
          "the conclusion of the AGM of 2021, and re-appointed at the 2021 AGM until the conclusion of the AGM of 2026. The next AGM "
          "is due in September 2026.\n")
    first_term_end, second_term_end, cool = 2021, 2026, 5
    earliest = second_term_end + cool
    q(B, "rotation", "L4", Dd + "\nWhich statement about the auditor appointment at the September 2026 AGM is correct?",
      f"K&M cannot be re-appointed; it is eligible again only after a five-year cooling-off (i.e., from the {earliest} AGM), and a firm "
      "having a common partner with K&M at the end of its term is also barred during that period",
      [("K&M can be re-appointed for a third term if members pass a special resolution", "two-term cap treated as relaxable"),
       (f"K&M cannot be re-appointed; it becomes eligible again after three years (the {second_term_end + 3} AGM)",
        "three-year cooling-off of independent directors applied to auditors"),
       ("K&M can be re-appointed because rotation applies only to listed companies", "Rule 5 class (unlisted public, paid-up ≥ ₹10 crore) ignored")],
      ["Rule 5, Audit and Auditors Rules: unlisted public companies with paid-up capital ≥ ₹10 crore are covered by s.139(2).",
       f"An audit firm can serve at most two terms of five consecutive years: 2016–{first_term_end} and {first_term_end}–{second_term_end}.",
       f"Cooling-off: five years from completion of the term → earliest re-appointment at the {earliest} AGM.",
       "s.139(2) proviso: a firm with a common partner at the date of completion of the term is also ineligible for five years."],
      "Firm: max 2 × 5-year terms, then 5-year cooling-off; individual: 1 × 5 years",
      "The three-year cooling-off belongs to independent directors, not auditors.",
      kind="case", group=g, ref="Companies Act 2013 s.139(2) and provisos; Rule 5, Companies (Audit and Auditors) Rules 2014")

    q(B, "consult", "L4", Dd + "\nAravali's Audit Committee recommends the firm Desai Shah LLP, but the Board prefers another firm. The correct "
      "course is:",
      "The Board refers the recommendation back to the Audit Committee citing reasons; if the Committee does not reconsider, the Board "
      "records its reasons for disagreement and sends its own recommendation to the members at the AGM",
      [("The Board appoints its preferred firm directly, since the Board is the appointing authority",
        "Board treated as appointing authority; members appoint at the AGM under s.139(1)"),
       ("The Board must place only the Audit Committee's recommendation before members", "Board's right to send its own recommendation ignored"),
       ("The dispute is referred to the Registrar for a decision", "non-existent external reference invented")],
      ["s.139(11): where an AC is required, auditor appointments are made after taking into account its recommendations.",
       "Rule 3, Audit and Auditors Rules: if the Board disagrees, it refers back to the AC citing reasons.",
       "If the AC does not reconsider, the Board records reasons and sends its own recommendation to the AGM; members decide."],
      "AC recommends → Board (agree: forward; disagree: refer back → own recommendation with reasons) → members appoint",
      "Neither the AC nor the Board appoints; the members do, at the AGM.",
      kind="case", group=g, ref="Companies Act 2013 s.139(1),(11); Rule 3, Companies (Audit and Auditors) Rules 2014")

    part_ca, part_tot, wife_fv, indebt = 3, 5, 80_000, 7_00_000
    q(B, "firm", "L4", Dd + f"\nDesai Shah LLP has {part_tot} partners, {part_ca} of whom are chartered accountants practising in India. "
      f"One partner's wife holds Aravali shares of face value {R(wife_fv)}. Another partner owes Aravali {R(indebt)} under a personal "
      "loan. The LLP audits 18 companies, 6 of them small companies. The LLP is:",
      "Disqualified, because a partner is indebted to the company beyond ₹5 lakh",
      [("Disqualified, because a partner's wife holds shares in the company", "relative's ₹1 lakh face-value allowance ignored"),
       ("Disqualified, because two partners are not chartered accountants", "majority test misread as all partners"),
       ("Eligible for appointment", "indebtedness limit under Rule 10 missed")],
      [f"s.141(1): an LLP qualifies if a majority of partners practising in India are CAs — {part_ca} of {part_tot} → satisfied.",
       f"s.141(3)(d)(i) with Rule 10: a relative may hold securities of face value up to ₹1 lakh → {R(wife_fv)} is allowed.",
       f"s.141(3)(d)(ii) with Rule 10: person, relative or partner indebted to the company above ₹5 lakh → {R(indebt)} disqualifies.",
       "Audit ceiling of 20 companies is not breached (18, with small companies excluded anyway)."],
      "Rule 10: relative's holding ≤ ₹1 lakh face value; indebtedness ≤ ₹5 lakh; guarantee ≤ ₹1 lakh",
      "A disqualification of a partner taints the firm.",
      kind="case", group=g, ref="Companies Act 2013 s.141(1),(3)(d),(g); Rule 10, Companies (Audit and Auditors) Rules 2014")

    q(B, "casual", "L4", Dd + "\nThe firm appointed at the 2026 AGM for five years resigns on 10 February 2027. Which is correct?",
      "The Board fills the vacancy within 30 days; the appointment must be approved by members at a general meeting convened within "
      "three months of the Board's recommendation, and the appointee holds office till the conclusion of the next AGM",
      [("The Board fills the vacancy within 30 days and the appointee serves the balance of the five-year term",
        "tenure of casual-vacancy appointee confused with the original term"),
       ("The Audit Committee fills the vacancy within 60 days; no members' approval is needed", "wrong authority, window and approval"),
       ("Members fill the vacancy at an EGM within 90 days for a fresh five-year term", "first-auditor fallback (s.139(6)) confused with casual vacancy")],
      ["s.139(8)(i): casual vacancy (other than in a CAG-audited company) filled by the Board within 30 days.",
       "If caused by resignation, the appointment is also approved by the company at a general meeting convened within three months of the Board's recommendation.",
       "The appointee holds office till the conclusion of the next AGM."],
      "Casual vacancy: Board within 30 days → (resignation) GM approval within 3 months → office till next AGM",
      "The appointee does not inherit the remaining years of the five-year term.",
      kind="case", group=g, ref="Companies Act 2013 s.139(8)(i)")

    # ================= CASE E — Kaveri Cements Ltd (dividend) =================
    g = "CAA-CASE-E"
    decl = date(2026, 9, 26)
    dps, nsh = 4, 3_00_00_000
    amt = dps * nsh / 1e7
    E = (f"**Case — Kaveri Cements Ltd.** At its AGM on {D(decl)}, Kaveri, a listed company, declared a final dividend of ₹{dps} per "
         f"equity share on {inr(nsh)} equity shares of ₹10 each.\n")
    d5 = decl + timedelta(days=5)
    q(B, "dep5", "L4", E + "\nThe amount Kaveri must deposit in a separate account in a scheduled bank, and the last date for doing so, are:",
      f"{Cr(amt)} by {D(d5)}",
      [(f"{Cr(amt)} by {D(decl + timedelta(days=7))}", "seven-day Unpaid Dividend Account rule applied"),
       (f"{Cr(amt)} by {D(decl + timedelta(days=30))}", "thirty-day payment window applied to the deposit"),
       (f"{Cr(amt)} by {D(decl + timedelta(days=4))}", "day of declaration counted as day one")],
      [f"Amount = ₹{dps} × {inr(nsh)} = ₹{amt:.2f} crore.",
       f"s.123(4): deposit within five days from the date of declaration → {D(decl)} + 5 days = {D(d5)} (the day of declaration is excluded)."],
      "Deposit dividend in a separate scheduled-bank account within 5 days of declaration (s.123(4))",
      "Five days to fund the account, thirty days to pay, seven more days to move unpaid amounts.",
      kind="case", group=g, ref="Companies Act 2013 s.123(4); General Clauses Act 1897 s.9")

    held = 50_000
    div = held * dps
    pay = date(2026, 12, 15)
    win_end = decl + timedelta(days=30)
    ddays = (pay - win_end).days
    all_days = (pay - decl).days
    assert ddays == 50 and all_days == 80
    i_ok = div * 0.18 * ddays / 365
    q(B, "div30", "L4", E + f"\nShareholder X, holding {inr(held)} shares, is paid only on {D(pay)}; none of the statutory exceptions applies. "
      "Counting the default period from the day after the statutory payment window ends up to and including the day of payment, the "
      "interest Kaveri owes X is (nearest rupee):",
      R(i_ok),
      [(R(div * 0.18 * all_days / 365), "interest counted from the date of declaration"),
       (R(div * 0.12 * ddays / 365), "12% rate applied instead of 18%"),
       (R(div * 0.18), "a full year's interest charged")],
      [f"Dividend due = {inr(held)} × ₹{dps} = {R(div)}.",
       f"Window: 30 days from {D(decl)} ends {D(win_end)}; default days = {D(win_end)} → {D(pay)} = {ddays}.",
       f"Interest = {inr(div)} × 18% × {ddays}/365 = {R(i_ok)}."],
      "s.127: simple interest @ 18% p.a. for the period of default",
      "Interest runs only for the default period, not from declaration.",
      kind="case", group=g, ref="Companies Act 2013 s.127")

    q(B, "div30", "L4", E + "\nKaveri misses the 30-day window for several shareholders. Which reason would NOT be a defence under s.127?",
      "The company's bank balance was insufficient on the due date",
      [("The dividend could not be paid by reason of the operation of law", "a listed statutory exception treated as no defence"),
       ("There was a dispute regarding the right to receive the dividend", "a listed statutory exception treated as no defence"),
       ("The dividend was lawfully adjusted against a sum due from the shareholder", "a listed statutory exception treated as no defence")],
      ["s.127 provisos: no offence where (a) operation of law; (b) shareholder's directions could not be complied with and were communicated; "
       "(c) dispute about the right to receive; (d) lawful adjustment against a sum due; (e) failure not due to default on the company's part.",
       "Insufficient funds is the company's own default — no defence. (s.123(4) already requires funding within 5 days.)"],
      "s.127 exceptions: operation of law, shareholder directions, dispute, lawful adjustment, no default of company",
      "Lack of funds is precisely the failure s.123(4) is meant to prevent.",
      kind="case", group=g, ref="Companies Act 2013 s.127 provisos")

    q(B, "iepf", "L4", E + "\nSome of this dividend eventually remains unclaimed for seven years and reaches the Investor Education and "
      "Protection Fund. The Fund may be used for:\n\n"
      "1. Refunds in respect of unclaimed dividends to the rightful claimants.\n"
      "2. Reimbursing legal expenses incurred in class-action suits under ss.37 and 245, as sanctioned by the Tribunal.\n"
      "3. Paying the s.127 interest that Kaveri owes its shareholders for late payment.\n\n"
      "Select the correct answer:",
      "1 and 2 only",
      [("1, 2 and 3", "company's own statutory liability shifted to the Fund"),
       ("1 only", "class-action reimbursement not recognised as a permitted use"),
       ("2 and 3 only", "refund of unclaimed amounts overlooked")],
      ["s.125(3): Fund used for refunds of unclaimed dividends, matured deposits/debentures, application money; investor education, "
       "awareness and protection; distribution of disgorged amounts; reimbursement of class-action legal expenses (ss.37, 245) sanctioned by the Tribunal.",
       "s.127 interest is Kaveri's own liability → not a use of the Fund."],
      "s.125(3) permitted uses",
      "IEPF is not a backstop for a company's own defaults.",
      kind="case", group=g, ref="Companies Act 2013 s.124(5), s.125(3)")

    # ================= CASE F — Sundaram Logistics Ltd (directors) =================
    g = "CAA-CASE-F"
    pub, pvt_sub, alt_pvt, pvt, dorm = 7, 2, 1, 6, 4
    F = ("**Case — Sundaram Logistics Ltd.** Sundaram, a public company that is neither a holding nor a subsidiary company, plans to "
         "appoint **Rohan Mehta** (who already holds a DIN) as an additional director on 10 November 2026. Rohan is currently a director "
         f"of {pub} public companies, {pvt_sub} private companies that are subsidiaries of public companies, {pvt} other private "
         f"companies and {dorm} dormant companies, and an alternate director in {alt_pvt} other private company (not a subsidiary of a "
         "public company). An existing Sundaram director, **Leena Rao**, is also a director of Kanak Traders Pvt Ltd, which has not "
         "filed its financial statements or annual returns for FY 2022-23, 2023-24 and 2024-25.\n")
    pub_after = pub + pvt_sub + 1
    tot_after = pub + pvt_sub + alt_pvt + pvt + 1
    assert pub_after == 10 and tot_after == 17 and tot_after + dorm == 21
    q(B, "maxdir", "L4", F + "\nAfter his appointment at Sundaram, Rohan's position under s.165 is:",
      f"Within limits — {pub_after} public-company directorships and {tot_after} in all",
      [(f"Over the limit — {tot_after + dorm} directorships in all", "dormant-company directorships counted"),
       (f"Within limits — {pub + 1} public-company directorships and {tot_after} in all", "private subsidiaries of public companies left out of the public count"),
       (f"Within limits — {pub_after} public-company directorships and {tot_after - alt_pvt} in all", "alternate directorship left out of the overall count")],
      [f"Overall limit 20 (includes alternate directorships; dormant companies excluded): {pub}+{pvt_sub}+{alt_pvt}+{pvt}+1 = {tot_after}.",
       f"Public limit 10 (private companies that are holding/subsidiary of a public company count): {pub}+{pvt_sub}+1 = {pub_after} → at the ceiling but within it."],
      "s.165(1): ≤ 20 companies incl. alternate (dormant excluded); ≤ 10 public incl. private holding/subsidiary of public",
      "Ten public directorships is permitted; the eleventh is not.",
      kind="case", group=g, ref="Companies Act 2013 s.165(1) and Explanation")

    q(B, "disq", "L4", F + "\nConsider Leena Rao's position:\n\n"
      "1. She is not eligible to be re-appointed in Kanak, or appointed in any other company, for five years from the date on which Kanak failed to file.\n"
      "2. Her office as director becomes vacant in Sundaram and also in Kanak.\n"
      "3. Had Kanak defaulted for only two financial years, s.164(2)(a) would not be attracted.\n\n"
      "Which statements are correct?",
      "1 and 3 only",
      [("1, 2 and 3", "vacation extended to the defaulting company itself"),
       ("1 only", "three-continuous-year trigger overlooked"),
       ("2 and 3 only", "five-year ineligibility overlooked")],
      ["s.164(2)(a): non-filing of financial statements or annual returns for any continuous period of three FYs → director not eligible for re-appointment in that company or appointment in any other company for five years from the date of failure → 1 correct.",
       "s.167(1)(a) proviso: office vacated in all companies other than the company in default → 2 wrong.",
       "Two years does not satisfy the three-continuous-year trigger → 3 correct."],
      "s.164(2): 3 continuous FYs non-filing → 5-year bar; s.167(1)(a): vacate all except defaulting company",
      "The defaulting company keeps the director so that it can cure the default.",
      kind="case", group=g, ref="Companies Act 2013 s.164(2)(a), s.167(1)(a) proviso")

    q(B, "loans", "L4", F + "\nAfter Rohan joins, Sundaram considers:\n\n"
      "(i) a loan of ₹2 crore to Mehta & Sons, a partnership firm in which Rohan's brother is a partner;\n"
      "(ii) a loan to Vistar Pvt Ltd, of which Rohan is a member, for Vistar's principal business;\n"
      "(iii) a housing loan to a Whole-time Director under a scheme approved by members by special resolution.\n\n"
      "Which is prohibited irrespective of any shareholder approval?",
      "(i) only",
      [("(i) and (ii) only", "loan to a private company in which a director is a member treated as absolutely prohibited (pre-2018 view)"),
       ("(i), (ii) and (iii)", "service-scheme exception for MD/WTD overlooked"),
       ("(ii) only", "firm in which a director's relative is partner treated as permissible")],
      ["s.185(1)(b): no loan to a firm in which a director or his relative is a partner → (i) prohibited.",
       "s.185(2): loan to 'any person in whom the director is interested' (incl. a private company of which he is a member) allowed with special resolution and use for principal business → (ii) permissible.",
       "s.185(3)(a): loan to MD/WTD under a scheme approved by members by special resolution → (iii) permissible."],
      "s.185(1) absolute bar (director, director of holding, partner, firm with director/relative as partner); s.185(2) SR route",
      "The relative-partner firm is caught by the absolute bar.",
      kind="case", group=g, ref="Companies Act 2013 s.185 (as substituted w.e.f. 7 May 2018)")

    appt = date(2026, 11, 10)
    q(B, "din", "L4", F + "\nWhich statement about the filings for Rohan's appointment is correct?",
      f"Rohan's consent to act must be filed with the Registrar within 30 days of appointment (by {D(appt + timedelta(days=30))}), and Sundaram "
      "must file the return of particulars of the appointment within 30 days",
      [(f"Consent and return both within 60 days (by {D(appt + timedelta(days=60))})", "filing window doubled"),
       ("Sundaram must obtain a fresh DIN for Rohan for this company", "s.155 one-DIN rule ignored"),
       ("No filing is needed because an additional director holds office only till the next AGM", "additional director treated as outside s.152(5)/s.170(2)")],
      ["s.152(5): a person appointed shall not act unless his consent is filed with the Registrar within 30 days of appointment.",
       "s.170(2): return containing particulars of appointment filed within 30 days.",
       "s.155: an individual holding a DIN shall not obtain another."],
      "Consent (DIR-2) and return (DIR-12) — 30 days each; one DIN for life",
      "An additional director is a director for every filing purpose.",
      kind="case", group=g, ref="Companies Act 2013 s.152(5), s.155, s.161(1), s.170(2)")
