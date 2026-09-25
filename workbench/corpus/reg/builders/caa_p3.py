"""REG-CORPUS-CA-A part 3: standalone questions — meetings, appeals, auditors, incorporation, capital (microtopics A–D)."""
from caa_common import q, ar, inr, R, L, Cr, D, date, timedelta, add_months


def add_all(B):
    # ---------- Adjournment when quorum absent ----------
    q(B, "adj", "L1", "In a public company, if a quorum is not present within half an hour of the time appointed for a general meeting "
      "(not called on requisition of members), the meeting:",
      "Stands adjourned to the same day in the next week at the same time and place, or to another date, time and place fixed by the Board",
      [("Stands dissolved and must be called afresh with 21 clear days' notice", "requisition-meeting cancellation rule applied to all meetings"),
       ("Proceeds immediately, the members present being deemed the quorum", "adjourned-meeting rule applied to the original meeting"),
       ("Stands adjourned to the same day in the next month", "period of adjournment misstated")],
      ["s.103(2)(a): meeting stands adjourned to the same day next week, same time and place, or other date/time/place determined by the Board.",
       "Only at the adjourned meeting do the members present constitute the quorum (s.103(3))."],
      "s.103(2): no quorum in 30 minutes → adjourned one week (or as Board fixes)",
      "'Members present are the quorum' applies only at the adjourned meeting.",
      ref="Companies Act 2013 s.103(2)")

    q(B, "adj", "L2", "Kamal Chemicals Ltd, a public company, has 3,200 members. Its AGM fails for want of quorum and the Board fixes the "
      "adjourned meeting on a date other than the same day of the next week. Which is correct?",
      "Quorum is 15 members personally present; at least 3 days' notice of the adjourned meeting must be given individually or by newspaper advertisement",
      [("Quorum is 5 members; at least 3 days' notice", "quorum band for up to 1,000 members applied"),
       ("Quorum is 15 members; a fresh 21 clear days' notice is needed", "adjourned meeting treated as a new meeting"),
       ("Quorum is 30 members; at least 3 days' notice", "quorum band for more than 5,000 members applied")],
      ["s.103(1)(a)(ii): public company with more than 1,000 but up to 5,000 members → 15 members personally present.",
       "s.103(2) proviso: if adjourned to a different date/time/place, at least 3 days' notice to members individually or by advertisement in "
       "newspapers (one English, one vernacular) circulating where the registered office is situated."],
      "Quorum 5 / 15 / 30 (≤1,000 / ≤5,000 / >5,000 members); 3 days' notice for a re-fixed adjourned meeting",
      "Only a change from the default 'same day next week' triggers the 3-day notice.",
      kind="numerical", ref="Companies Act 2013 s.103(1)(a), s.103(2) proviso")

    q(B, "adj", "L3", "Vinayak Steel Ltd, a public company with 6,000 members, calls its AGM. Consider:\n\n"
      "1. The quorum is 30 members personally present.\n"
      "2. If the meeting is adjourned for want of quorum and, at the adjourned meeting, a quorum is again not present within half an hour, the 4 members present shall be the quorum.\n"
      "3. Had the meeting been called on the requisition of members under s.100 and quorum been absent, it would stand cancelled.\n\n"
      "Which of the statements are correct?",
      "1, 2 and 3",
      [("1 and 2 only", "cancellation of requisitioned meetings overlooked"),
       ("1 only", "adjourned-meeting quorum rule overlooked"),
       ("2 and 3 only", "quorum band for more than 5,000 members misapplied")],
      ["s.103(1)(a)(iii): more than 5,000 members → 30 members.",
       "s.103(3): at the adjourned meeting, if quorum absent within half an hour, members present shall be the quorum.",
       "s.103(2)(b): a meeting called on requisition under s.100 stands cancelled."],
      "s.103(1)–(3)",
      "There is no minimum number at the adjourned meeting — whoever is present is the quorum.",
      kind="statement", ref="Companies Act 2013 s.103(1)(a)(iii), (2)(b), (3)")

    # ---------- Age limits ----------
    q(B, "age", "L1", "Under s.196(3), a company shall not appoint or continue the employment of a person as managing director, whole-time "
      "director or manager who is below the age of ____ or has attained the age of ____ (the latter subject to a special resolution exception).",
      "21 years; 70 years",
      [("18 years; 70 years", "age of majority used for the lower limit"),
       ("21 years; 75 years", "SEBI LODR non-executive director age (75) used"),
       ("25 years; 65 years", "retirement-style limits assumed")],
      ["s.196(3)(a): below 21 or attained 70 years — barred; appointment of a person above 70 is possible by special resolution with justification in the explanatory statement."],
      "MD/WTD/manager: 21 ≤ age < 70 (70+ by special resolution)",
      "75 is the SEBI LODR trigger for non-executive directors, not the Companies Act MD limit.",
      ref="Companies Act 2013 s.196(3)(a)")

    q(B, "age", "L2", "Mr Venkat, aged 71, is proposed as a Whole-time Director of Nilgiri Tea Ltd, a public company. Which is correct?",
      "He may be appointed by a special resolution, with the explanatory statement to the notice indicating the justification for appointing him",
      [("He cannot be appointed at all, having attained 70", "special-resolution exception overlooked"),
       ("An ordinary resolution with Board recommendation suffices", "resolution type understated"),
       ("He can be appointed only with Central Government approval in every case, in addition to a special resolution", "CG approval wrongly made mandatory")],
      ["s.196(3)(a) proviso: a person who has attained 70 may be appointed by special resolution; the explanatory statement must indicate the justification."],
      "Age 70+ → special resolution + justification in explanatory statement",
      "The bar at 70 is not absolute.",
      ref="Companies Act 2013 s.196(3)(a) proviso")

    # ---------- Alternate director ----------
    q(B, "alt", "L2", "Consider the following about alternate directors under s.161(2):\n\n"
      "1. The Board may appoint one only if authorised by the articles or by a resolution passed in general meeting.\n"
      "2. The original director must be absent from India for a period of not less than three months.\n"
      "3. A person who is already a director of the same company may be appointed as the alternate.\n\n"
      "Which are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "bar on existing directors acting as alternate overlooked"),
       ("2 only", "authorisation requirement overlooked"),
       ("1 and 3 only", "three-month absence condition overlooked")],
      ["s.161(2): Board may appoint (if authorised by articles or GM resolution) an alternate for a director absent from India for not less than three months.",
       "No person holding an alternate directorship for any other director, or holding a directorship in the same company, can be appointed."],
      "Alternate: authorisation + ≥3 months' absence from India + not already a director/alternate in the company",
      "Absence from meetings is not enough — absence from India is the trigger.",
      kind="statement", ref="Companies Act 2013 s.161(2)")

    leave, ret_ = date(2026, 8, 1), date(2026, 10, 15)
    q(B, "alt", "L3", f"Ms Kavya, an independent director of Orbit Ltd, leaves India on {D(leave)} for five months. The Board (authorised by "
      f"the articles) appoints Mr Jatin as her alternate. Ms Kavya returns to India early, on {D(ret_)}. Which is correct?",
      f"Jatin must himself satisfy the independence criteria of s.149(6), and he vacates office when Kavya returns on {D(ret_)}",
      [("Jatin continues until the originally planned five-month absence ends", "vacation on return of original director overlooked"),
       ("Jatin need not be independent, since he only substitutes for Kavya", "ID-qualification proviso for alternates overlooked"),
       ("Jatin holds office until the next AGM, like an additional director", "additional-director tenure confused with alternate")],
      ["s.161(2) proviso: an alternate for an independent director must be qualified to be appointed as an independent director.",
       "The alternate holds office no longer than permissible to the original director and vacates when the original director returns to India."],
      "Alternate vacates on return of original director; alternate for an ID must be ID-qualified",
      "Early return ends the alternate's tenure immediately.",
      ref="Companies Act 2013 s.161(2) and provisos")

    # ---------- Appeal to Supreme Court ----------
    q(B, "sc", "L1", "Under s.423, an appeal against an order of the NCLAT lies to the Supreme Court:",
      "Within 60 days from receipt of the order, on any question of law arising out of it",
      [("Within 45 days, on questions of fact and law", "NCLAT appeal window and scope applied"),
       ("Within 90 days, on any question of law", "window overstated"),
       ("Within 30 days, on any question", "IBC-type window and unrestricted scope assumed")],
      ["s.423: any person aggrieved may appeal to the Supreme Court within 60 days from receipt of the order, on any question of law.",
       "The Supreme Court may allow a further period not exceeding 60 days on sufficient cause."],
      "s.423: 60 days + up to 60 days; questions of law only",
      "Facts are settled at the NCLAT; only law goes up.",
      ref="Companies Act 2013 s.423")

    rec = date(2026, 3, 3)
    last = rec + timedelta(days=60)
    ext = rec + timedelta(days=120)
    q(B, "sc", "L2", f"A certified copy of an NCLAT order is received by Mehul on {D(rec)}. If the Supreme Court is satisfied that he had "
      "sufficient cause for delay, the latest date up to which it may entertain his appeal is:",
      D(ext),
      [(D(last), "extension period ignored"),
       (D(rec + timedelta(days=105)), "NCLAT's 45-day extension applied to the Supreme Court"),
       (D(rec + timedelta(days=180)), "extension taken as 120 days")],
      [f"Normal window: 60 days from receipt → {D(last)}.",
       f"Further period (sufficient cause): not exceeding 60 days → {D(ext)}."],
      "SC appeal: 60 + 60 days from receipt of NCLAT order",
      "The extension equals the original window (60), unlike NCLAT's 45 + 45.",
      kind="numerical", ref="Companies Act 2013 s.423 proviso")

    # ---------- Appeal window to NCLAT ----------
    q(B, "nclat_appeal", "L1", "An appeal to the NCLAT against an order of the NCLT under the Companies Act must be filed within:",
      "45 days from the date the copy of the order is made available, extendable by up to 45 days for sufficient cause",
      [("30 days, extendable by 15 days", "IBC s.61 window applied to Companies Act appeals"),
       ("60 days, extendable by 60 days", "Supreme Court window (s.423) applied"),
       ("90 days, with no extension", "window and extension both misstated")],
      ["s.421(3): 45 days from the date on which a copy of the order is made available; NCLAT may entertain within a further period not exceeding 45 days if satisfied of sufficient cause."],
      "s.421(3): 45 + 45 days",
      "IBC appeals (30 + 15) run on a different clock.",
      ref="Companies Act 2013 s.421(3)")

    q(B, "nclat_appeal", "L2", "Consider the following about appeals from the NCLT:\n\n"
      "1. No appeal lies to the NCLAT from an order of the NCLT made with the consent of the parties.\n"
      "2. After hearing the parties, the NCLAT may confirm, modify or set aside the order and sends a copy of its order to the NCLT and the parties.\n"
      "3. Only the company that was a party before the NCLT may appeal; other aggrieved persons cannot.\n\n"
      "Which are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "'any person aggrieved' misread as only the company"),
       ("2 only", "consent-order bar overlooked"),
       ("1 and 3 only", "NCLAT's powers on appeal overlooked")],
      ["s.421(1): any person aggrieved by an NCLT order may appeal → 3 wrong.",
       "s.421(2): no appeal from an order made with the consent of parties → 1 correct.",
       "s.421(4): NCLAT passes orders confirming, modifying or setting aside, and sends copies → 2 correct."],
      "s.421(1)–(4)",
      "Consent orders are final by design.",
      kind="statement", ref="Companies Act 2013 s.421(1),(2),(4)")

    avail, filed = date(2026, 1, 12), date(2026, 3, 20)
    n = (filed - avail).days
    assert 45 < n <= 90 and n > 60
    q(B, "nclat_appeal", "L3", f"The copy of an NCLT order was made available to Rudra Ltd on {D(avail)}. Rudra files its appeal before the "
      f"NCLAT on {D(filed)}. The appeal is:",
      f"Filed on day {n}: beyond 45 days but within the further 45 days, so the NCLAT may entertain it if satisfied that there was sufficient cause",
      [(f"Filed on day {n}: time-barred, as the NCLAT has no power to condone delay", "condonation power of s.421(3) proviso overlooked"),
       (f"Filed on day {n}: within time, as 90 days is available as of right", "extension treated as automatic"),
       (f"Filed on day {n}: time-barred, as the outer limit including extension is 60 days", "Supreme Court's 60-day window confused with NCLAT's outer limit")],
      [f"Days from {D(avail)} to {D(filed)} = {n}.",
       "Normal limit 45 days; further period up to 45 days (outer limit 90) only on sufficient cause."],
      "s.421(3): 45 days as of right; 46–90 days only on sufficient cause",
      "The extra 45 days is discretionary, not a right.",
      kind="numerical", ref="Companies Act 2013 s.421(3) and proviso")

    # ---------- Appointment consultation process ----------
    q(B, "consult", "L2", "Before recommending an auditor, the Audit Committee (or the Board, where no committee is required) must, under the "
      "Audit and Auditors Rules, take into consideration:\n\n"
      "1. The qualifications and experience of the individual or firm.\n"
      "2. Whether those qualifications and experience are commensurate with the size and requirements of the company.\n"
      "3. Any order or pending proceeding relating to professional matters of conduct against the proposed auditor before ICAI or any competent authority or court.\n"
      "4. Whether the proposed auditor has quoted the lowest fee.\n\n"
      "Select the correct answer:",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "lowest-fee criterion invented"),
       ("1 and 2 only", "pending disciplinary proceedings criterion overlooked"),
       ("1 and 4 only", "commensurability and disciplinary criteria overlooked")],
      ["Rule 3(2), Companies (Audit and Auditors) Rules 2014: qualifications and experience; commensurability with size and requirements; "
       "pending orders/proceedings on professional conduct.",
       "Lowest fee is not a statutory criterion; s.139(1) also requires the auditor's written consent and eligibility certificate."],
      "Rule 3: qualifications, commensurability, disciplinary history",
      "Price is not a statutory selection criterion.",
      kind="statement", ref="Companies Act 2013 s.139(1),(11); Rule 3, Companies (Audit and Auditors) Rules 2014")

    # ---------- Registered valuer ----------
    q(B, "valuer", "L1", "Where the Companies Act requires a valuation of shares, property or net worth, the registered valuer is appointed by:",
      "The Audit Committee or, in its absence, the Board of Directors",
      [("The members in general meeting", "appointing authority confused with statutory auditor"),
       ("The Board of Directors in all cases", "Audit Committee's primary role overlooked"),
       ("The Insolvency and Bankruptcy Board of India", "registering authority confused with appointing authority")],
      ["s.247(1): valuation by a registered valuer appointed by the Audit Committee or, in its absence, by the Board.",
       "IBBI is the authority that registers valuers under the Registered Valuers Rules 2017."],
      "s.247(1): AC → else Board",
      "IBBI registers valuers; it does not appoint them for a company.",
      ref="Companies Act 2013 s.247(1)")

    q(B, "valuer", "L3", "Mr Naresh, a registered valuer, is engaged in May 2026 to value the shares of Pioneer Ltd, an unlisted company, for a "
      "preferential allotment. Consider:\n\n"
      "1. He cannot undertake the valuation if he was interested in the shares at any time during the three years before his appointment.\n"
      "2. He must not become interested in the shares for three years after the valuation.\n"
      "3. For a preferential issue under s.62(1)(c), the price must be determined on the basis of a registered valuer's report.\n"
      "4. If the Audit Committee cannot meet, the Managing Director alone may appoint him.\n\n"
      "Select the correct answer:",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "MD treated as an appointing authority"),
       ("1 and 3 only", "post-valuation three-year restriction overlooked"),
       ("3 and 4 only", "s.247 interest restrictions overlooked")],
      ["s.247(2)(c): no valuation of an asset in which the valuer has direct/indirect interest, or becomes interested, during 3 years before appointment or 3 years after valuation.",
       "s.62(1)(c): price determined by the valuation report of a registered valuer (unlisted company).",
       "s.247(1): appointment by AC, else Board — not by the MD alone."],
      "s.247: 3 years before + 3 years after; AC/Board appoints",
      "The interest bar runs both backwards and forwards.",
      kind="statement", ref="Companies Act 2013 s.247(1),(2); s.62(1)(c)")

    # ---------- DIN ----------
    q(B, "din", "L1", "Under ss.153–155, a Director Identification Number is:",
      "Allotted once to an individual by the Central Government and used for all his directorships",
      [("Allotted separately for each company in which the individual is a director", "one-DIN rule of s.155 ignored"),
       ("Allotted by the company that first appoints the individual", "allotting authority misstated"),
       ("Required to be surrendered and re-obtained every five years", "invented renewal requirement")],
      ["s.153: application to the Central Government; s.154: allotment within one month.",
       "s.155: no individual who has been allotted a DIN shall apply for or obtain another."],
      "One individual, one DIN (s.155)",
      "The DIN travels with the person, not the company.",
      ref="Companies Act 2013 ss.153-155")

    ap = date(2026, 8, 5)
    q(B, "din", "L2", f"Rewa Ltd appoints Ms Tara as a director on {D(ap)}. The last date for filing the return of particulars of the "
      "appointment with the Registrar is:",
      D(ap + timedelta(days=30)),
      [(D(ap + timedelta(days=15)), "15-day window assumed"),
       (D(ap + timedelta(days=60)), "60-day window assumed"),
       (D(ap + timedelta(days=90)), "90-day window assumed")],
      ["s.170(2): return with particulars of appointment/change of directors and KMP within 30 days.",
       f"{D(ap)} + 30 days = {D(ap + timedelta(days=30))}."],
      "s.170(2): 30 days",
      "The consent filing under s.152(5) runs on the same 30-day clock.",
      kind="numerical", ref="Companies Act 2013 s.170(2)")

    # ---------- Auditor rotation ----------
    q(B, "rotation", "L2", "Which of the following companies are covered by the auditor-rotation requirement of s.139(2)?\n\n"
      "(a) An unlisted public company with paid-up capital of ₹8 crore and no borrowings.\n"
      "(b) A private company with paid-up capital of ₹60 crore.\n"
      "(c) A private company with paid-up capital of ₹20 crore and bank borrowings of ₹55 crore.\n"
      "(d) A small company.",
      "(b) and (c) only",
      [("(b) only", "public-borrowings criterion (≥ ₹50 crore) overlooked"),
       ("(a), (b) and (c)", "₹10 crore unlisted public threshold misapplied"),
       ("(b), (c) and (d)", "exclusion of small companies overlooked")],
      ["Rule 5: listed companies; unlisted public companies with paid-up capital ≥ ₹10 crore; private companies with paid-up capital ≥ ₹50 crore; "
       "all companies with public borrowings from FIs, banks or public deposits ≥ ₹50 crore.",
       "OPCs and small companies are excluded.",
       "(a) ₹8 crore → out; (b) ₹60 crore private → in; (c) borrowings ₹55 crore → in; (d) small → out."],
      "Rule 5 class: listed / unlisted public ≥ ₹10 cr / private ≥ ₹50 cr / borrowings ≥ ₹50 cr",
      "The borrowings test catches companies below the capital thresholds.",
      kind="statement", ref="Companies Act 2013 s.139(2); Rule 5, Companies (Audit and Auditors) Rules 2014")

    start, term, cool = 2022, 5, 5
    q(B, "rotation", "L3", f"CA Harish, an individual, was appointed statutory auditor of Lotus Ltd (listed) at the {start} AGM until the "
      f"conclusion of the {start + term} AGM. The earliest AGM at which he can again be appointed auditor of Lotus is the:",
      f"{start + term + cool} AGM",
      [(f"{start + term} AGM, for a second five-year term", "two-term allowance for firms applied to an individual"),
       (f"{start + term + 3} AGM", "three-year cooling-off assumed"),
       (f"{start + 2 * term + cool} AGM", "second term assumed before cooling-off")],
      [f"Individual auditor: only one term of five consecutive years ({start}–{start + term}).",
       f"Cooling-off: five years from completion of the term → {start + term + cool} AGM."],
      "Individual: 1 term of 5 years + 5-year cooling-off; firm: 2 terms + 5 years",
      "Individuals do not get a second consecutive term.",
      kind="numerical", ref="Companies Act 2013 s.139(2)(a) and proviso")

    # ---------- Audit Committee ----------
    q(B, "ac", "L2", "Under Rule 6 of the Meetings of Board Rules, which of these unlisted public companies must constitute an Audit Committee "
      "(figures per latest audited financial statements)?\n\n"
      "| Company | Paid-up capital | Turnover | Outstanding loans, debentures and deposits |\n|---|---:|---:|---:|\n"
      "| P | ₹6 crore | ₹120 crore | ₹10 crore |\n| Q | ₹9 crore | ₹80 crore | ₹50 crore |\n| R | ₹10 crore | ₹30 crore | nil |",
      "P and R only",
      [("P, Q and R", "borrowing test read as '₹50 crore or more' instead of 'exceeding ₹50 crore'"),
       ("R only", "only the paid-up capital test applied"),
       ("P only", "₹10 crore paid-up test read as 'exceeding'")],
      ["Rule 6: paid-up capital ≥ ₹10 crore; OR turnover ≥ ₹100 crore; OR aggregate outstanding loans/borrowings/debentures/deposits exceeding ₹50 crore.",
       "P: turnover ₹120 crore → yes. Q: ₹50 crore does not exceed ₹50 crore; other tests fail → no. R: paid-up ₹10 crore → yes."],
      "Rule 6: ≥ ₹10 cr capital | ≥ ₹100 cr turnover | > ₹50 cr borrowings",
      "'Not less than' for capital and turnover, but 'exceeding' for borrowings.",
      kind="numerical", ref="Companies Act 2013 s.177(1); Rule 6, Companies (Meetings of Board and its Powers) Rules 2014")

    q(B, "ac", "L3", "Which of the following are functions of the Audit Committee under s.177(4)?\n\n"
      "1. Recommending the appointment, remuneration and terms of appointment of auditors.\n"
      "2. Approval or any subsequent modification of transactions with related parties.\n"
      "3. Scrutiny of inter-corporate loans and investments.\n"
      "4. Making the final appointment of the statutory auditor.\n\n"
      "Select the correct answer:",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "recommending confused with appointing"),
       ("1 and 2 only", "scrutiny of inter-corporate loans omitted"),
       ("2, 3 and 4 only", "recommendation role replaced by appointment")],
      ["s.177(4): recommend auditors; review independence; examine financial statements; approve/modify RPTs; scrutinise inter-corporate loans and investments; "
       "valuation; evaluate internal financial controls; monitor end use of public-offer funds.",
       "The statutory auditor is appointed by the members (s.139(1))."],
      "s.177(4) terms of reference",
      "The AC recommends; the AGM appoints.",
      kind="statement", ref="Companies Act 2013 s.177(4)")

    txn = 80
    q(B, "ac", "L3", f"A director of Harit Ltd enters into a ₹{txn} lakh transaction (not covered by s.188) on behalf of the company "
      "without the Audit Committee's approval. The Committee does not ratify it within three months. The transaction is:",
      "Voidable at the option of the Audit Committee",
      [("Void ab initio", "voidable treated as void"),
       ("Valid, because transactions below ₹1 crore need no Audit Committee approval", "ratification proviso misread as an exemption"),
       ("Valid if ratified by the Board at any later date", "Board substituted for the Audit Committee; time limit ignored")],
      [f"s.177(4)(iv) proviso: a transaction not exceeding ₹1 crore entered by a director/officer without AC approval and not ratified by the AC within three months is voidable at the AC's option.",
       f"₹{txn} lakh ≤ ₹1 crore; no ratification in 3 months → voidable; the director concerned indemnifies the company for loss if the counterparty is related to him."],
      "s.177(4)(iv): ≤ ₹1 crore, unratified in 3 months → voidable at AC's option",
      "Voidable, not void — the AC chooses.",
      ref="Companies Act 2013 s.177(4)(iv) provisos")

    # ---------- Beneficial owner ----------
    q(B, "bo", "L2", "Under s.89, a person whose name is entered in the register of members but who does not hold the beneficial interest must "
      "file a declaration with the company within ____ , and the company must file a return with the Registrar within ____ of receiving it.",
      "30 days; 30 days",
      [("30 days; 60 days", "company's filing window overstated"),
       ("15 days; 30 days", "holder's window understated"),
       ("90 days; 30 days", "significant beneficial owner transition period confused with s.89")],
      ["s.89(1): registered holder declares within 30 days (MGT-4); s.89(2): beneficial owner declares within 30 days (MGT-5).",
       "s.89(6): company files return with Registrar within 30 days of receipt (MGT-6)."],
      "s.89: 30 days / 30 days",
      "s.89 (nominee holdings) and s.90 (significant beneficial owners) are separate regimes.",
      ref="Companies Act 2013 s.89(1),(2),(6)")

    h_stake, alpha_in_t, h_direct = 60, 20, 3
    k_stake, beta_in_t = 40, 30
    assert k_stake * beta_in_t / 100 >= 10 and h_direct < 10
    q(B, "bo", "L3", "Target Ltd's register shows:\n\n"
      f"| Member | Holding in Target |\n|---|---:|\n| Alpha Pvt Ltd | {alpha_in_t}% |\n| Beta Pvt Ltd | {beta_in_t}% |\n| Mr H (directly) | {h_direct}% |\n\n"
      f"Mr H holds {h_stake}% of Alpha. Mr K holds {k_stake}% of Beta (no one holds a majority of Beta). Neither exercises significant "
      "influence or control otherwise. Who is a significant beneficial owner (SBO) of Target?",
      "Mr H only",
      [("Both Mr H and Mr K", f"proportionate look-through used ({k_stake}% × {beta_in_t}% = {k_stake*beta_in_t/100:g}%) without the majority-stake test"),
       ("Neither, since each holds less than 10% directly", "indirect holdings ignored"),
       ("Mr K only", "majority-stake test reversed")],
      ["SBO Rules: an individual holding, directly or indirectly (with direct holdings), not less than 10% of shares/voting/dividend rights, or exercising significant influence or control.",
       "Indirect holding through a company member arises only where the individual holds a majority stake in that member (or its ultimate holding company).",
       f"H holds a majority ({h_stake}%) of Alpha → Alpha's {alpha_in_t}% attributed; with direct {h_direct}% he crosses 10% → SBO.",
       f"K's {k_stake}% of Beta is not a majority → no indirect holding → not an SBO."],
      "SBO: ≥ 10% (direct + indirect); indirect via company member only with majority stake",
      "The rules use a majority-stake gate, not arithmetic multiplication.",
      ref="Companies Act 2013 s.90; Companies (Significant Beneficial Owners) Rules 2018, Rule 2(1)(h) and Explanations")

    q(B, "bo", "L3", "15% of the shares of Sagar Ltd are registered in the name of Mr Vikram as trustee of the Asha Family Trust, a "
      "discretionary trust settled by Mrs Asha for the benefit of her children. Assuming no other rights, who is treated as holding "
      "the right indirectly for SBO purposes?",
      "Mr Vikram, the trustee",
      [("Mrs Asha, the settlor", "revocable-trust rule (author/settlor) applied to a discretionary trust"),
       ("The children, as beneficiaries", "specific-trust rule (beneficiary) applied"),
       ("No one, because a trust cannot have a significant beneficial owner", "trust look-through ignored")],
      ["SBO Rules, Explanation (member is a trust through trustee): trustee — discretionary or charitable trust; beneficiary — specific trust; author/settlor — revocable trust.",
       "Discretionary trust → trustee (Mr Vikram), holding 15% ≥ 10%."],
      "Trust member: discretionary/charitable → trustee; specific → beneficiary; revocable → settlor",
      "The type of trust decides which third person qualifies.",
      ref="Companies (Significant Beneficial Owners) Rules 2018, Rule 2(1)(h) Explanation III(iv)")

    # ---------- Board composition ----------
    q(B, "boardcomp", "L1", "The minimum number of directors for a public company, a private company and a One Person Company, and the "
      "maximum without a special resolution, are respectively:",
      "3, 2, 1; maximum 15",
      [("3, 2, 1; maximum 12", "Companies Act 1956-era ceiling assumed"),
       ("7, 2, 1; maximum 15", "minimum members of a public company confused with minimum directors"),
       ("2, 2, 1; maximum 15", "public-company minimum understated")],
      ["s.149(1)(a): minimum 3 (public), 2 (private), 1 (OPC); maximum 15.",
       "More than 15 may be appointed after passing a special resolution."],
      "s.149(1): 3 / 2 / 1; max 15 (more by SR)",
      "Seven is the minimum number of members, not directors, of a public company.",
      ref="Companies Act 2013 s.149(1)")

    nb = 11
    import math
    ids = math.ceil(nb / 3)
    q(B, "boardcomp", "L2", f"The Board of Pranav Ltd, a listed public company, has {nb} directors. Under the Companies Act, 2013 (ignore SEBI "
      "LODR), the minimum number of independent directors is:",
      str(ids),
      [(str(nb // 3), "fraction in one-third dropped instead of rounded up"),
       ("2", "Rule 4 minimum for unlisted public companies applied"),
       (str(math.ceil(nb / 2)), "one-half requirement of SEBI LODR (executive chairperson) applied")],
      [f"s.149(4): at least one-third of total directors; {nb}/3 = {nb/3:.2f}.",
       f"Explanation: any fraction is rounded off as one → {ids}."],
      "IDs ≥ ⌈Board ÷ 3⌉ for listed public companies",
      "Fractions round up, not down.",
      kind="numerical", ref="Companies Act 2013 s.149(4) and Explanation")

    q(B, "boardcomp", "L3", "Aarav Ltd, an unlisted public company, has paid-up capital of ₹60 crore and turnover of ₹320 crore. Consider:\n\n"
      "1. Increasing its Board to 17 directors requires a special resolution.\n"
      "2. It must have at least one woman director.\n"
      "3. It must have at least one director who stayed in India for at least 182 days in the previous calendar year.\n\n"
      "Which are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "resident-director test still read as 'previous calendar year' (amended to 'financial year')"),
       ("1 only", "woman-director turnover threshold (₹300 crore) missed"),
       ("2 and 3 only", "special resolution for more than 15 directors overlooked")],
      ["s.149(1) proviso: more than 15 directors after special resolution → 1 correct.",
       "Rule 3: public companies with paid-up capital ≥ ₹100 crore or turnover ≥ ₹300 crore need a woman director → ₹320 crore → 2 correct.",
       "s.149(3) (as amended 2017): at least one director who stays in India ≥ 182 days during the financial year → 3 wrong."],
      "s.149(1), (3); Rule 3 woman director",
      "The resident-director test now runs on the financial year.",
      kind="statement", ref="Companies Act 2013 s.149(1), s.149(3) (amended 2017); Rule 3, Appointment and Qualification of Directors Rules 2014")

    # ---------- Board meetings: frequency, first meeting ----------
    q(B, "bmfreq", "L1", "The first meeting of the Board of a newly incorporated company must be held within:",
      "30 days of the date of incorporation",
      [("60 days of the date of incorporation", "window doubled"),
       ("90 days of the date of incorporation", "first-auditor EGM window confused"),
       ("180 days of the date of incorporation", "commencement-of-business declaration window confused")],
      ["s.173(1): first Board meeting within 30 days of incorporation; thereafter at least four meetings a year."],
      "s.173(1): 30 days",
      "180 days is the s.10A declaration window, not the first Board meeting.",
      ref="Companies Act 2013 s.173(1)")

    sched = {"a": (date(2026, 3, 10), date(2026, 9, 20)), "b": (date(2026, 6, 15), date(2026, 8, 5)),
             "c": (date(2026, 2, 10), date(2026, 5, 25))}
    gaps = {k: (v[1] - v[0]).days for k, v in sched.items()}
    assert gaps["a"] >= 90 and gaps["b"] < 90
    q(B, "bmfreq", "L3", "Neel Traders Ltd is a small company. Which schedule of Board meetings for calendar year 2026 complies with s.173(5)?",
      f"{D(sched['a'][0])} and {D(sched['a'][1])}",
      [(f"{D(sched['b'][0])} and {D(sched['b'][1])}", f"one meeting in each half, but gap only {gaps['b']} days (< 90)"),
       (f"{D(sched['c'][0])} and {D(sched['c'][1])}", "both meetings in the first half of the calendar year"),
       ("A single meeting on 30 June 2026", "one meeting a year treated as sufficient")],
      ["s.173(5): OPC, small company and dormant company — at least one meeting in each half of the calendar year, with a gap of not less than 90 days between the two.",
       f"(a) March and September; gap {gaps['a']} days → compliant."],
      "Small company: one meeting per half-year, ≥ 90 days apart",
      "For small companies 90 days is a minimum gap, the opposite of the 120-day maximum for others.",
      ref="Companies Act 2013 s.173(5)")

    # ---------- Bonus shares ----------
    q(B, "bonus", "L2", "Which of the following are conditions for a bonus issue under s.63?\n\n"
      "1. It is authorised by the articles.\n"
      "2. It has been recommended by the Board and authorised in general meeting.\n"
      "3. Partly paid-up shares outstanding on the date of allotment are made fully paid-up.\n"
      "4. It may be issued in lieu of the dividend for the year.\n\n"
      "Select the correct answer:",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "bonus in lieu of dividend wrongly permitted"),
       ("1 and 2 only", "partly-paid condition overlooked"),
       ("2, 3 and 4 only", "articles authorisation overlooked")],
      ["s.63(2): articles authorise; GM approval on Board recommendation; no default in deposits/debt securities; no default in statutory employee dues; partly paid shares made fully paid.",
       "s.63(5): bonus shares shall not be issued in lieu of dividend."],
      "s.63(2) conditions; s.63(5) no bonus in lieu of dividend",
      "Bonus capitalises reserves — it cannot substitute for a cash dividend.",
      kind="statement", ref="Companies Act 2013 s.63(2),(5)")

    sp, gr, rv, crr, pl, unr, cap = 18, 30, 25, 6, 12, 4, 40
    avail = sp + gr + crr + (pl - unr)
    assert avail == 62
    q(B, "bonus", "L3", "Extract of Deccan Motors Ltd's latest audited balance sheet (₹ crore):\n\n"
      "| Item | ₹ crore |\n|---|---:|\n"
      f"| Equity share capital (fully paid) | {cap} |\n| Securities premium | {sp} |\n| General reserve | {gr} |\n"
      f"| Revaluation reserve | {rv} |\n| Capital redemption reserve | {crr} |\n"
      f"| Surplus in profit and loss (includes unrealised fair-value gains of ₹{unr} crore) | {pl} |\n\n"
      "The maximum amount that can be capitalised for a bonus issue is:",
      Cr(avail),
      [(Cr(avail + rv), "revaluation reserve capitalised"),
       (Cr(avail + unr), "unrealised fair-value gains treated as free reserves"),
       (Cr(avail - crr), "capital redemption reserve wrongly excluded")],
      ["s.63(1): free reserves, securities premium, CRR; not revaluation reserve.",
       f"s.2(43): free reserves exclude unrealised/notional gains → P&L surplus usable = {pl} − {unr} = {pl-unr}.",
       f"Total = {sp} + {gr} + {crr} + {pl-unr} = ₹{avail} crore."],
      "Bonus pool = securities premium + CRR + free reserves (net of unrealised gains)",
      "Fair-value gains sitting in retained earnings are not free reserves.",
      kind="numerical", ref="Companies Act 2013 s.2(43), s.63(1)")

    # ---------- Buy-back (standalone) ----------
    eqc, fr, fv, price = 20, 180, 10, 80
    nshares = eqc * 1e7 / fv
    amt_cap = 0.25 * (eqc + fr) * 1e7
    by_amt = amt_cap / price
    by_cnt = 0.25 * nshares
    ans = min(by_amt, by_cnt)
    assert ans == by_cnt == 50_00_000
    q(B, "buyback", "L3", f"Ganga Ltd has paid-up equity capital of ₹{eqc} crore (shares of ₹{fv}), free reserves including securities "
      f"premium of ₹{fr} crore, and no debt. It proposes a buy-back at ₹{price} per share under a special resolution. The maximum "
      "number of equity shares it can buy back in the year is:",
      inr(ans),
      [(inr(by_amt), "only the 25%-of-capital-and-free-reserves amount cap applied"),
       (inr(0.10 * (eqc + fr) * 1e7 / price), "10% Board-route cap applied"),
       (inr(0.25 * eqc * 1e7 / price), "25% of equity capital in rupees divided by the buy-back price")],
      [f"Amount cap: 25% × ({eqc}+{fr}) crore = ₹{amt_cap/1e7:g} crore → ÷ ₹{price} = {inr(by_amt)} shares.",
       f"Share cap: 25% of {inr(nshares)} equity shares = {inr(by_cnt)} shares (s.68(2)(c) proviso).",
       f"Binding = lower = {inr(ans)} shares."],
      "Buy-back of equity shares ≤ min(25% of paid-up + free reserves in value, 25% of equity shares in number)",
      "At a low buy-back price, the 25%-of-shares count binds before the value cap.",
      kind="numerical", ref="Companies Act 2013 s.68(2)(c) and proviso")

    # ---------- CAG appointment ----------
    q(B, "cag", "L1", "In a Government company, the Comptroller and Auditor-General appoints the auditor (other than the first auditor) "
      "within ____ from the commencement of the financial year.",
      "180 days",
      [("60 days", "first-auditor window of s.139(7) applied"),
       ("30 days", "casual-vacancy window applied"),
       ("90 days", "invented window")],
      ["s.139(5): CAG appoints within 180 days from commencement of the FY; the auditor holds office till the conclusion of the AGM."],
      "s.139(5): 180 days",
      "60 days is for the first auditor of a Government company.",
      ref="Companies Act 2013 s.139(5)")

    q(B, "cag", "L2", "Match the appointment windows for the **first auditor of a Government company**:\n\n"
      "| Step | Authority |\n|---|---|\n| I | CAG |\n| II | Board (if CAG fails) |\n| III | Members at an EGM (if Board fails) |\n\n"
      "The windows for I, II and III are respectively:",
      "60 days from registration; next 30 days; next 60 days",
      [("30 days; next 60 days; next 90 days", "non-Government first-auditor windows (s.139(6)) mixed in"),
       ("60 days; next 60 days; next 30 days", "Board and members' windows swapped"),
       ("180 days; next 30 days; next 60 days", "subsequent-auditor window (s.139(5)) used for CAG")],
      ["s.139(7): CAG within 60 days of registration; if not, Board within next 30 days; if Board fails, it informs members who appoint within 60 days at an EGM."],
      "s.139(7): 60 → 30 → 60",
      "The non-Government sequence is Board 30 days, then members 90 days.",
      kind="match", ref="Companies Act 2013 s.139(7)")

    reg = date(2026, 5, 10)
    cag_end = reg + timedelta(days=60)
    board_end = cag_end + timedelta(days=30)
    mem_end = board_end + timedelta(days=60)
    q(B, "cag", "L3", f"Bhavya Power Corporation Ltd, a Government company, is registered on {D(reg)}. The CAG does not appoint the first "
      "auditor. The latest date by which the Board must make the appointment is:",
      D(board_end),
      [(D(reg + timedelta(days=30)), "non-Government 30-day Board window applied from registration"),
       (D(cag_end), "end of CAG's own window taken"),
       (D(mem_end), "members' EGM deadline taken")],
      [f"CAG window: 60 days from registration → {D(cag_end)}.",
       f"Board: within next 30 days → {D(board_end)}.",
       f"(Members at EGM: within next 60 days → {D(mem_end)}.)"],
      "s.139(7): CAG 60 days → Board next 30 days → members next 60 days",
      "The Board's clock starts only after the CAG's 60 days expire.",
      kind="numerical", ref="Companies Act 2013 s.139(7)")

    # ---------- Casual vacancy (standalone) ----------
    q(B, "casual", "L2", "A casual vacancy arises in the office of auditor of a company whose accounts are audited by an auditor appointed by the "
      "CAG. It is filled:",
      "By the CAG within 30 days; if the CAG does not, by the Board within the next 30 days",
      [("By the Board within 30 days, with approval of members within three months", "rule for non-CAG companies applied"),
       ("By the CAG within 60 days", "window overstated"),
       ("By members at a general meeting within three months", "members made the primary authority")],
      ["s.139(8)(ii): CAG fills within 30 days; failing which the Board fills within the next 30 days."],
      "s.139(8)(ii): CAG 30 → Board 30",
      "Members' approval is a feature of resignation vacancies in non-CAG companies.",
      ref="Companies Act 2013 s.139(8)(ii)")

    # ---------- CRC / incorporation ----------
    q(B, "crc", "L1", "A name reserved for a proposed new company (e.g., through SPICe+ Part A) remains reserved for:",
      "20 days from the date of approval",
      [("60 days from the date of approval", "change-of-name reservation period applied"),
       ("30 days from the date of application", "period and starting point misstated"),
       ("90 days from the date of approval", "invented period")],
      ["s.4(5)(i) with Rule 9, Companies (Incorporation) Rules: 20 days from approval for a new company; 60 days for change of name of an existing company."],
      "Name reservation: 20 days (new) / 60 days (change of name)",
      "The longer 60-day period is only for existing companies changing their name.",
      ref="Companies Act 2013 s.4(5)(i); Rule 9, Companies (Incorporation) Rules 2014")

    q(B, "crc", "L2", "Consider the following about incorporation:\n\n"
      "1. The certificate of incorporation issued by the Registrar is conclusive evidence that all requirements of the Act as to registration have been complied with.\n"
      "2. A company having share capital cannot commence business unless a director files, within 180 days of incorporation, a declaration that every subscriber has paid for the shares agreed to be taken.\n"
      "3. A company must have a registered office within 90 days of incorporation.\n\n"
      "Which are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "registered-office window (30 days) overstated"),
       ("2 only", "conclusive-evidence rule of s.7(2) overlooked"),
       ("1 and 3 only", "s.10A declaration overlooked")],
      ["s.7(2): certificate of incorporation is conclusive evidence of compliance with registration requirements → 1 correct.",
       "s.10A: declaration within 180 days of incorporation before commencing business or borrowing → 2 correct.",
       "s.12(1): registered office within 30 days of incorporation → 3 wrong."],
      "s.7(2), s.10A (180 days), s.12(1) (30 days)",
      "Registered office: 30 days; business-commencement declaration: 180 days.",
      kind="statement", ref="Companies Act 2013 s.7(2), s.10A, s.12(1)")

    # ---------- NCLAT constitution & powers ----------
    q(B, "nclat", "L1", "Under s.410, the NCLAT consists of a Chairperson and Judicial and Technical Members numbering, in all, not more than:",
      "Eleven",
      [("Seven", "number understated"),
       ("Fifteen", "maximum Board size confused"),
       ("Sixty-two", "original maximum membership of the NCLT confused")],
      ["s.410: Chairperson and such number of Judicial and Technical Members, not exceeding eleven, as the Central Government deems fit."],
      "s.410: members ≤ 11",
      "The NCLT's strength is set separately under s.408.",
      ref="Companies Act 2013 s.410")

    q(B, "nclat", "L2", "Consider the following about the NCLAT:\n\n"
      "1. It is not bound by the procedure laid down in the Code of Civil Procedure but is guided by the principles of natural justice.\n"
      "2. It has the same powers as a civil court for summoning witnesses, discovery of documents and receiving evidence on affidavits.\n"
      "3. It has the same power to punish for contempt as a High Court.\n"
      "4. It is strictly bound by the Indian Evidence Act and CPC procedure.\n\n"
      "Select the correct answer:",
      "1, 2 and 3 only",
      [("1, 2, 3 and 4", "contradictory statement 4 accepted"),
       ("2 and 3 only", "natural-justice procedure clause overlooked"),
       ("1 and 2 only", "contempt power of s.425 overlooked")],
      ["s.424(1): not bound by CPC; guided by natural justice.",
       "s.424(2): civil-court powers for specified matters; orders enforceable as decrees.",
       "s.425: same jurisdiction, powers and authority in respect of contempt as a High Court."],
      "s.424–425",
      "Civil-court powers do not mean civil-court procedure.",
      kind="statement", ref="Companies Act 2013 ss.424, 425")

    # ---------- Cost audit ----------
    q(B, "cost", "L2", "Sanjeevani Pharma Ltd operates in a regulated sector (Table A). In the preceding financial year its overall turnover was "
      "₹60 crore; its largest individual product turnover was ₹22 crore. For the current year:",
      "It must maintain cost records, but cost audit is not required",
      [("It must maintain cost records and get them audited", "individual-product test (₹25 crore) overlooked"),
       ("Neither cost records nor cost audit applies", "₹35 crore record-maintenance threshold missed"),
       ("Cost audit applies, but cost records need not be maintained", "audit wrongly separated from records")],
      ["Rule 3: cost records if overall turnover ≥ ₹35 crore → ₹60 crore → yes.",
       "Rule 4 (Table A): audit if overall turnover ≥ ₹50 crore AND individual product ≥ ₹25 crore → ₹22 crore fails → no audit."],
      "Records ≥ ₹35 cr; audit Table A ≥ ₹50 cr & product ≥ ₹25 cr",
      "Both limbs of the audit test must be met.",
      kind="numerical", ref="Companies (Cost Records and Audit) Rules 2014, Rules 3 and 4")

    q(B, "cost", "L3", "Consider the cost-audit timelines:\n\n"
      "1. The cost auditor submits the report to the Board within 180 days from the closure of the financial year.\n"
      "2. The company files the cost audit report with the Central Government within 60 days of receiving it.\n"
      "3. The remuneration of the cost auditor is ratified by the shareholders.\n"
      "4. The company intimates the appointment to the Central Government within 30 days of the Board meeting or 180 days of commencement of the financial year, whichever is earlier.\n\n"
      "Select the correct answer:",
      "1, 3 and 4 only",
      [("1, 2, 3 and 4", "CRA-4 window taken as 60 days"),
       ("1 and 3 only", "CRA-2 intimation window overlooked"),
       ("2, 3 and 4 only", "180-day report window overlooked")],
      ["Rule 6(5): report to Board within 180 days of FY closure (CRA-3).",
       "Rule 6(6): company files with CG within 30 days of receipt (CRA-4) → 2 wrong.",
       "Rule 14: remuneration ratified by shareholders.",
       "Rule 6(2): CRA-2 within 30 days of Board meeting or 180 days of FY start, whichever earlier."],
      "Cost audit: CRA-2 (30/180 days) → CRA-3 (180 days after FY) → CRA-4 (30 days)",
      "CRA-4 is due 30 days after receipt, not 60.",
      kind="statement", ref="Companies (Cost Records and Audit) Rules 2014, Rules 6 and 14")

    # ---------- Delivery timeline for securities ----------
    q(B, "delivery", "L1", "On allotment of shares, a company must deliver the share certificates (unless the shares are in a depository) within:",
      "Two months from the date of allotment",
      [("One month from the date of allotment", "transfer-lodgement window applied"),
       ("Six months from the date of allotment", "debenture window applied"),
       ("Fifteen days from the date of allotment", "invented window")],
      ["s.56(4)(b): within two months from allotment of shares."],
      "s.56(4): subscribers 2 m; shares 2 m; transfer 1 m; debentures 6 m",
      "Debentures get six months; shares only two.",
      ref="Companies Act 2013 s.56(4)(b)")

    lodged = date(2026, 1, 5)
    q(B, "delivery", "L2", f"A duly stamped and executed instrument of transfer of physical shares of Rupal Ltd (unlisted) is lodged with the "
      f"company on {D(lodged)}. The certificates must be delivered by:",
      D(add_months(lodged, 1)),
      [(D(add_months(lodged, 2)), "allotment window (two months) applied"),
       (D(add_months(lodged, 6)), "debenture window applied"),
       (D(lodged + timedelta(days=15)), "invented 15-day window")],
      ["s.56(4)(c): within one month from receipt of the instrument of transfer or intimation of transmission.",
       f"{D(lodged)} + 1 month = {D(add_months(lodged, 1))}."],
      "Transfer/transmission: one month from receipt",
      "Transfers get the shortest window.",
      kind="numerical", ref="Companies Act 2013 s.56(4)(c)")

    inc2 = date(2026, 4, 1)
    ev = [("Subscribers to the memorandum (incorporated " + D(inc2) + ")", 2),
          ("Allotment of shares", 2), ("Instrument of transfer received", 1), ("Allotment of debentures", 6)]
    q(B, "delivery", "L3", "Match each event with the period within which certificates must be delivered under s.56(4):\n\n"
      "| Event | Period |\n|---|---|\n"
      "| I. Subscribers to the memorandum | a. One month |\n| II. Allotment of shares | b. Two months |\n"
      "| III. Instrument of transfer received | c. Six months |\n| IV. Allotment of debentures | |",
      "I-b, II-b, III-a, IV-c",
      [("I-a, II-b, III-a, IV-c", "subscribers given the transfer window"),
       ("I-b, II-c, III-a, IV-b", "shares and debentures windows swapped"),
       ("I-b, II-b, III-b, IV-c", "transfer given the allotment window")],
      ["s.56(4)(a) subscribers: 2 months from incorporation; (b) shares: 2 months from allotment; (c) transfer/transmission: 1 month; (d) debentures: 6 months."],
      "2 / 2 / 1 / 6 months",
      "Two events share the two-month window.",
      kind="match", ref="Companies Act 2013 s.56(4)")

    # ---------- Deposit within five days (standalone) ----------
    q(B, "dep5", "L1", "The amount of a dividend, including an interim dividend, must be deposited in a separate account in a scheduled bank within:",
      "Five days from the date of declaration",
      [("Seven days from the date of declaration", "Unpaid Dividend Account transfer window applied"),
       ("Thirty days from the date of declaration", "payment window applied"),
       ("Fifteen days from the date of declaration", "invented window")],
      ["s.123(4): within five days from the date of declaration."],
      "s.123(4): 5 days",
      "The same five-day rule covers interim dividends.",
      ref="Companies Act 2013 s.123(4)")

    # ---------- Disqualifications ----------
    q(B, "disq", "L2", "Mr Arjun was convicted of an offence and sentenced to imprisonment for eight years. Under s.164(1)(d):",
      "He is not eligible for appointment as a director in any company at any time",
      [("He becomes eligible five years after expiry of the sentence", "rule for sentences of 6 months to below 7 years applied"),
       ("He is barred only from the company in relation to which the offence was committed", "company-specific bar assumed"),
       ("He becomes eligible seven years after expiry of the sentence", "invented cooling period")],
      ["s.164(1)(d): sentence ≥ 6 months → disqualified until 5 years from expiry of the sentence.",
       "Proviso: sentence of seven years or more → not eligible for appointment in any company."],
      "Sentence ≥ 7 years → permanent bar",
      "Seven years or more converts the five-year bar into a permanent one.",
      ref="Companies Act 2013 s.164(1)(d) and proviso")

    q(B, "disq", "L3", "Four persons are proposed as directors of Meru Ltd in September 2026:\n\n"
      "- **P**: sentenced to eight months' imprisonment for an offence; sentence expired in September 2023.\n"
      "- **Q**: has not paid a call on shares of Meru for four months from the last date fixed.\n"
      "- **R**: convicted in 2022 of an offence dealing with related party transactions under s.188.\n"
      "- **S**: has applied to be adjudicated insolvent; the application is pending.\n\n"
      "Who can be appointed?",
      "Q only",
      [("Q and R only", "five-year window for s.188 convictions overlooked"),
       ("P and Q only", "five years from expiry of sentence not yet elapsed for P"),
       ("P, Q and R", "both five-year windows overlooked")],
      ["P: s.164(1)(d) — 5 years from expiry (Sept 2023) not elapsed → disqualified.",
       "Q: s.164(1)(f) — calls unpaid for six months → only four months → not disqualified.",
       "R: s.164(1)(g) — s.188 conviction at any time during the last five years → disqualified.",
       "S: s.164(1)(c) — pending insolvency application → disqualified."],
      "s.164(1)(c),(d),(f),(g)",
      "Unpaid calls disqualify only after six months.",
      kind="statement", ref="Companies Act 2013 s.164(1)")
