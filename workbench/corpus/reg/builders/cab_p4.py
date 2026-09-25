"""Part 4: meetings, directors, OPC, LLP, NCLT, strike-off, committees."""
from cab_common import *  # noqa
import math


def add_all(B):
    # ------------------------------------------------------------------ Board quorum
    sanc, vac = 11, 3
    strength = sanc - vac
    q = max(math.ceil(strength / 3), 2)
    assert q == 3
    B.add(M["bq"], "L2",
          f"The articles of Ishaan Motors Ltd fix the Board at {sanc} directors, but {vac} offices are presently vacant. The quorum for a Board meeting under s.174(1) is:",
          f"{q} directors",
          [(f"{math.ceil(sanc/3)} directors", "vacant offices included in total strength"),
           ("2 directors", "fraction dropped / minimum of two applied instead of one-third"),
           (f"{strength//2 + 1} directors", "majority of directors applied")],
          [f"Total strength excludes vacant places: {sanc} − {vac} = {strength}.",
           f"One-third = {strength/3:.2f} → fraction rounded off as one → {q}; higher of {q} and 2 = {q}."],
          "Quorum = max(⌈strength/3⌉, 2), strength excluding vacancies",
          "Round any fraction UP and exclude vacancies from strength.",
          verify_fact=True, ref="Companies Act 2013 s.174(1) and Explanation")

    tot, inter = 12, 8
    non = tot - inter
    assert inter >= 2 * tot / 3
    B.add(M["bq"], "L3",
          f"Palash Industries Ltd has {tot} directors, all in office. For an agenda item on a contract with a group company, {inter} directors are interested. Under s.174(3), the quorum for that item is:",
          f"The non-interested directors present, being not less than two",
          [(f"{math.ceil(tot/3)} directors, including interested directors", "general quorum applied; interested directors counted"),
           (f"All {non} non-interested directors", "presence of every non-interested director required"),
           ("No quorum is possible; the item must go to the general meeting", "assumes s.174(3) makes the Board incompetent")],
          [f"Interested directors ({inter}) ≥ two-thirds of total strength ({2*tot/3:.0f}).",
           "s.174(3): the number of non-interested directors present, being not less than two, shall be the quorum."],
          "If interested ≥ 2/3 of strength → quorum = non-interested present (min 2)",
          "Interested directors are excluded when the two-thirds trigger is met.",
          verify_fact=True, ref="Companies Act 2013 s.174(3)")

    mtg = d(2026, 9, 14)  # Monday
    B.add(M["bq"], "L1",
          f"A Board meeting of Omkar Ltd called for {mtg.strftime('%A')}, {ds(mtg)} could not be held for want of quorum. The articles are silent. Under s.174(4), the meeting stands adjourned to:",
          f"Same day next week ({ds(plus(mtg,7))}), same time and place, or next non-holiday",
          [(f"The next day ({ds(plus(mtg,1))}) at the same time and place", "adjourns to the next day"),
           ("A date to be fixed by the Chairman within 30 days", "invented discretion"),
           ("The same day in the next week, but the members present will constitute the quorum", "GM adjournment rule of s.103(2)(b) applied to Board")],
          ["s.174(4): unless articles provide otherwise, adjourned to same day next week, same time and place; if national holiday, next succeeding non-holiday."],
          "s.174(4)", "No 'those present shall be quorum' rule for Board meetings.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.174(4)")

    # ------------------------------------------------------------------ GM quorum
    mem = 3500
    B.add(M["gq"], "L2",
          f"Nakshatra Chemicals Ltd, a public company, has {inr(mem)} members on the date of its AGM. Unless the articles provide for a larger number, the quorum under s.103(1) is:",
          "15 members personally present",
          [("5 members personally present", "slab for up to 1,000 members applied"),
           ("30 members personally present", "slab for more than 5,000 members applied"),
           ("15 members present in person or by proxy", "proxies counted towards quorum")],
          ["s.103(1)(a): public company — 5 (≤ 1,000 members), 15 (> 1,000 and ≤ 5,000), 30 (> 5,000), personally present.",
           f"{inr(mem)} members → 15."],
          "s.103(1)(a) slabs", "Proxies are not 'personally present'.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.103(1)")

    B.add(M["gq"], "L3",
          stmts("At the AGM of Prithvi Metals Ltd (a public company) the quorum was not present within half an hour. Consider:",
                ["The meeting stands adjourned to the same day in the next week at the same time and place, or to such other date, time and place as the Board may determine.",
                 "If the meeting had been called by requisitionists under s.100, it would stand cancelled.",
                 "If the adjourned meeting is held on a changed date, the company shall give not less than three days' notice to members individually or by newspaper publication (one English and one vernacular).",
                 "At the adjourned meeting, if quorum is not present within half an hour, the meeting stands dissolved."]),
          "1, 2 and 3 only",
          [("1 and 3 only", "overlooks cancellation of a requisitioned meeting"),
           ("1, 2, 3 and 4", "overlooks that members present form the quorum at the adjourned meeting"),
           ("2, 3 and 4 only", "overlooks the Board's power to fix another date")],
          ["s.103(2)(a): adjourned to same day next week or as Board determines; s.103(2)(b): requisitioned meeting cancelled.",
           "Proviso: changed date → ≥ 3 days' notice individually or by newspaper (English + vernacular).",
           "s.103(3): at the adjourned meeting, members present shall be the quorum."],
          "s.103(2), (3)", "Adjourned GM: members present = quorum (unlike a Board meeting).",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.103(2), (3)")

    # ------------------------------------------------------------------ circulation
    B.add(M["circ"], "L1",
          "Which of the following powers of the Board can be exercised by a resolution passed by circulation?",
          "Approval of a contract for supply of goods in the ordinary course of business",
          [("Approval of the financial statements and the Board's report", "s.179(3)(g) — only at a meeting"),
           ("Authorising buy-back of securities under s.68", "s.179(3)(b) — only at a meeting"),
           ("Making calls on shareholders in respect of money unpaid on their shares", "s.179(3)(a) — only at a meeting")],
          ["s.179(3) and Rule 8 list powers exercisable only by resolution at a Board meeting (calls, buy-back, issue of securities, borrowing, investments, loans, financial statements, diversification, amalgamation, takeover, etc.).",
           "Routine ordinary-course contracts may be approved by circulation under s.175."],
          "s.175; s.179(3)", "Anything in s.179(3) needs a physical/VC meeting.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.175, s.179(3); Meetings of Board Rules 2014, Rule 8")

    tot, inter = 10, 2
    ent = tot - inter
    maj = ent // 2 + 1
    third = math.ceil(tot / 3)
    B.add(M["circ"], "L3",
          f"Drishti Ceramics Ltd has {tot} directors. A draft resolution (not a s.179(3) matter) is circulated to all of them; {inter} directors are interested in the matter. Under s.175, the minimum number of approvals needed for the resolution to be passed, and the minimum number of directors who can require it to be decided at a meeting, are respectively:",
          f"{maj} and {third}",
          [(f"{tot//2 + 1} and {third}", "majority computed on all directors including interested ones"),
           (f"{maj} and {tot//3}", "one-third rounded down"),
           (f"{ent} and {third}", "unanimity of entitled directors required")],
          [f"s.175(1): approved by a majority of directors entitled to vote → {ent} entitled → majority = {maj}.",
           f"Proviso: not less than one-third of total directors ({tot}/3 = {tot/3:.2f}) → {third} directors may require a meeting."],
          "Approval: majority of directors entitled to vote; meeting demand: ≥ 1/3 of total directors",
          "Interested directors are excluded from the approval base but not from the one-third base.",
          verify_fact=True, ref="Companies Act 2013 s.175(1) and proviso")

    # ------------------------------------------------------------------ small shareholders' director
    fv, n, mp = 10, 1500, 900
    B.add(M["ssd"], "L2",
          f"Mr Rao holds {inr(n)} shares of face value ₹{fv} in Kosi Power Ltd, a listed company (market price ₹{mp}). For the purposes of s.151 he is:",
          f"A small shareholder, as the nominal value of his holding ({R(n*fv)}) does not exceed ₹20,000",
          [(f"Not a small shareholder, as the market value of his holding ({R(n*mp)}) exceeds ₹20,000", "market value used instead of nominal value"),
           (f"Not a small shareholder, as the test is market value up to ₹2,00,000 and his holding is worth {R(n*mp)}", "SEBI retail-investor ₹2 lakh concept applied"),
           ("A small shareholder, because he holds fewer than 2,000 shares", "number of shares used as the test")],
          ["Explanation to s.151: 'small shareholder' = holding shares of nominal value of not more than ₹20,000.",
           f"Nominal value = {inr(n)} × ₹{fv} = {R(n*fv)} ≤ ₹20,000."],
          "Small shareholder: nominal value ≤ ₹20,000", "SEBI's ₹2 lakh 'retail' definition is a different concept.",
          verify_fact=True, ref="Companies Act 2013 s.151 Explanation")

    sm = 6_000
    need = min(1000, sm // 10)
    B.add(M["ssd"], "L3",
          stmts(f"Rudraksh Textiles Ltd (listed) has {inr(sm)} small shareholders. Consider, under s.151 and Rule 7 of the Companies (Appointment and Qualification of Directors) Rules, 2014:",
                [f"A small shareholders' director can be elected upon notice of not less than {need} small shareholders.",
                 "The small shareholders' director holds office for a term not exceeding three consecutive years and is not eligible for re-appointment.",
                 "The small shareholders' director is liable to retire by rotation.",
                 "A person cannot hold the position of small shareholders' director in more than two companies at the same time."]),
          "1, 2 and 4 only",
          [("2 and 4 only", f"notice threshold taken as 1,000 without applying 'whichever is lower'"),
           ("1, 2, 3 and 4", "treats the small shareholders' director as a rotational director"),
           ("1 and 2 only", "overlooks the two-company cap")],
          [f"Rule 7(1): notice of not less than 1,000 small shareholders or one-tenth of total small shareholders, whichever is lower → min(1,000, {sm//10}) = {need}.",
           "Rule 7(4): tenure ≤ 3 consecutive years; no re-appointment; not liable to retire by rotation.",
           "Rule 7(5): not more than two companies as small shareholders' director (business not competing)."],
          "Notice ≥ min(1,000, 10% of small shareholders)", "'Whichever is lower' makes 600 enough here.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.151; Appointment Rules 2014, Rule 7")

    # ------------------------------------------------------------------ SRC
    B.add(M["src"], "L2",
          "Aarohi Logistics Ltd had 1,020 shareholders in August 2026, which fell to 980 by 31 March 2027; it has no other security holders. Under s.178(5), for FY 2026-27 the company:",
          "Must constitute an SRC chaired by a non-executive director",
          [("Need not constitute the committee, since holders at year-end are below 1,000", "tests the number only at year-end"),
           ("Must constitute the committee chaired by an independent director", "LODR/audit-committee chair requirement confused"),
           ("Must constitute the committee only if it is listed", "listing is not the trigger under s.178(5)")],
          ["s.178(5): company with more than 1,000 shareholders, debenture-holders, deposit-holders and other security holders at any time during a FY shall constitute an SRC.",
           "Chairperson: a non-executive director."],
          "s.178(5): > 1,000 holders at any time during the FY", "'At any time during the year' — the peak counts.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.178(5)")

    # ------------------------------------------------------------------ OPC / types
    B.add(M["opc"], "L3",
          stmts("Consider the following regarding One Person Companies under Rule 3 of the Companies (Incorporation) Rules, 2014 as amended in 2021:",
                ["An Indian citizen residing abroad (not resident in India) can incorporate an OPC.",
                 "A natural person can incorporate more than one OPC if each has a different nominee.",
                 "An OPC must convert into a public or private company once its paid-up capital exceeds ₹50 lakh.",
                 "A minor cannot become a member or nominee of an OPC."]),
          "1 and 4 only",
          [("1, 3 and 4 only", "applies the ₹50 lakh compulsory-conversion threshold removed in 2021"),
           ("4 only", "applies the pre-2021 residency requirement"),
           ("1, 2 and 4 only", "allows multiple OPCs per person")],
          ["Rule 3(1) (2021): only a natural person who is an Indian citizen, whether resident in India or otherwise, can incorporate an OPC or be its nominee.",
           "Rule 3(4): cannot incorporate more than one OPC or be nominee in more than one.",
           "2021 amendment omitted the paid-up ₹50 lakh / turnover ₹2 crore compulsory-conversion trigger.",
           "Rule 3(5): a minor cannot be member or nominee."],
          "Incorporation Rules, Rule 3 (as amended w.e.f. 1-4-2021)",
          "The 2021 amendment removed both the residency condition and the conversion thresholds.",
          kind="statement", verify_fact=True, ref="Companies (Incorporation) Rules 2014, Rule 3 (amended 2021)")

    B.add(M["opc"], "L1",
          "Which of the following is exempted for a One Person Company under the Companies Act, 2013?",
          "Holding an annual general meeting under s.96",
          [("Filing financial statements with the Registrar", "OPCs must file financial statements"),
           ("Maintaining books of account under s.128", "books must be maintained"),
           ("Getting its accounts audited under s.139", "OPC audit is mandatory")],
          ["s.96(1): every company other than an OPC shall hold an AGM each year.",
           "OPC financial statements need not include a cash-flow statement (s.2(40) proviso); audit and filing remain mandatory."],
          "s.96(1); s.2(40)", "OPC exemption is from AGM and cash-flow statement, not from audit.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.96(1); s.2(40)")

    B.add(M["opc"], "L2",
          "Under s.173(5), an OPC, a small company and a dormant company are deemed to comply with the requirement of Board meetings if:",
          "One meeting in each half of a calendar year, at least 90 days apart",
          [("At least four Board meetings are held in a year with a gap of not more than 120 days", "general s.173(1) rule applied"),
           ("At least one Board meeting is held in each financial year", "applies the rule only to OPCs with one director"),
           ("At least two meetings are held in a year with a gap of not more than 90 days", "gap requirement inverted")],
          ["s.173(5): one meeting in each half of a calendar year, gap between the two meetings not less than 90 days.",
           "s.173(5) proviso: OPC with only one director is not subject to the Board-meeting requirement."],
          "s.173(5)", "'Not less than 90 days' gap — the reverse of the 120-day maximum gap for others.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.173(5)")

    # ------------------------------------------------------------------ vacation / removal
    B.add(M["vac"], "L3",
          stmts("Under s.167, the office of a director becomes vacant where he:",
                ["absents himself from all Board meetings held during a period of twelve months, with or without seeking leave of absence;",
                 "is convicted of an offence and sentenced to imprisonment for not less than six months, even if an appeal is pending;",
                 "fails to attend three consecutive Board meetings with leave of absence;",
                 "acts in contravention of s.184 (disclosure of interest)."],
                "Which of the above are grounds of vacation?"),
          "1, 2 and 4 only",
          [("1 and 4 only", "believes conviction under appeal does not vacate office"),
           ("1, 2, 3 and 4", "applies the repealed 1956 Act three-meetings rule"),
           ("2, 3 and 4 only", "drops the twelve-month absence rule")],
          ["s.167(1)(b): absence from all meetings in 12 months with or without leave.",
           "s.167(1)(e)/(f): conviction with imprisonment ≥ 6 months — office vacated irrespective of appeal.",
           "s.167(1)(c): contravention of s.184.",
           "The 'three consecutive meetings' ground belonged to s.283 of the 1956 Act."],
          "s.167(1)", "The 2013 Act uses a 12-month test, with or without leave.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.167(1)")

    paid, tot_paid, vote_pct = 6e5, 90e7, 0.008
    B.add(M["vac"], "L3",
          f"A member of Tejas Ltd holding {pct(vote_pct,1)} of the total voting power, on whose shares {R(paid)} has been paid up, wishes to move a resolution to remove a director under s.169. Which is correct?",
          "He can give special notice (₹5 lakh paid-up suffices), at least 14 days before the meeting",
          [("He cannot give special notice, since he holds less than 1% of the voting power", "treats the two Rule 23 limbs as cumulative"),
           ("He can give special notice, which must reach the company at least 21 days before the meeting", "21-day AGM notice period applied"),
           ("No special notice is needed; the director can be removed by an ordinary resolution on the Board's recommendation", "skips the special-notice requirement of s.169(2)")],
          ["s.169(2): special notice required for removal of a director.",
           "Rule 23 (Management and Administration Rules): members holding ≥ 1% of total voting power OR shares on which ≥ ₹5,00,000 has been paid up.",
           "s.115: special notice at least 14 days before the meeting (exclusive of the day of notice and the meeting); company gives members ≥ 7 days' notice."],
          "Special notice: ≥ 1% voting power OR ≥ ₹5 lakh paid-up; ≥ 14 days before meeting",
          "The two eligibility limbs are alternatives.",
          verify_fact=True, ref="Companies Act 2013 s.115, s.169; Management and Administration Rules 2014, Rule 23")

    # ------------------------------------------------------------------ LLP
    B.add(M["llp"], "L1",
          "Under the LLP Act, 2008 and the LLP Rules, 2009, the Statement of Account and Solvency of an LLP is signed on behalf of the LLP by:",
          "Its designated partners",
          [("Any two partners, whether designated or not", "ignores designated-partner responsibility"),
           ("The auditor of the LLP", "auditor certifies, does not sign for the LLP"),
           ("A practising company secretary", "confuses with certification of annual return")],
          ["s.34 LLP Act read with Rule 24: Statement of Account and Solvency (Form 8) is signed on behalf of the LLP by its designated partners.",
           "s.8: designated partners are responsible for compliance and filings."],
          "LLP Act s.8, s.34; LLP Rules Rule 24", "Designated partners are the compliance signatories.",
          kind="conceptual", verify_fact=True, ref="LLP Act 2008 s.8, s.34; LLP Rules 2009, Rule 24")

    B.add(M["llp"], "L2",
          stmts("Consider the following regarding designated partners and authority in an LLP:",
                ["Every LLP must have at least two designated partners who are individuals, and at least one of them must be resident in India.",
                 "Where a body corporate is a partner, an individual nominated by it may act as a designated partner.",
                 "Every partner of an LLP is, for the purpose of the business of the LLP, the agent of the LLP but not of other partners."]),
          "1, 2 and 3",
          [("1 and 2 only", "overlooks agency of partners under s.26"),
           ("1 and 3 only", "overlooks nominees of body-corporate partners"),
           ("2 and 3 only", "overlooks the two-designated-partner rule")],
          ["s.7(1): at least two designated partners who are individuals, at least one resident in India; where all partners are bodies corporate, their nominees act as designated partners.",
           "s.26: every partner is the agent of the LLP, but not of other partners."],
          "LLP Act s.7, s.26", "Agency runs to the LLP, not to co-partners.",
          kind="statement", verify_fact=True, ref="LLP Act 2008 s.7, s.26")

    # ------------------------------------------------------------------ woman / resident director
    rows = [("A Ltd", "Listed", 40, 150), ("B Ltd", "Unlisted public", 120, 250), ("C Ltd", "Unlisted public", 80, 290),
            ("D Ltd", "Private", 150, 600)]
    need = [n for n, t, pu, to in rows if t == "Listed" or (t == "Unlisted public" and (pu >= 100 or to >= 300))]
    assert need == ["A Ltd", "B Ltd"]
    B.add(M["wd"], "L3",
          "Latest audited figures (₹ crore):\n\n"
          + table(["Company", "Type", "Paid-up capital", "Turnover"], [list(r) for r in rows], ["---", "---", "---:", "---:"])
          + "\n\nWhich companies must have at least one woman director under the second proviso to s.149(1) read with Rule 3?",
          "A Ltd and B Ltd only",
          [("B Ltd and D Ltd only", "listing test ignored and private company included"),
           ("A Ltd, B Ltd and D Ltd only", "private companies treated as covered by size thresholds"),
           ("A Ltd, B Ltd and C Ltd only", "turnover threshold misread as ₹250 crore")],
          ["Rule 3: every listed company; every other public company with paid-up share capital ≥ ₹100 crore or turnover ≥ ₹300 crore.",
           "A: listed ✓; B: paid-up 120 ✓; C: 80 / 290 ✗; D: private — outside the rule."],
          "Listed OR (public AND (PUC ≥ ₹100 cr OR TO ≥ ₹300 cr))", "Private companies are outside Rule 3 regardless of size.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.149(1) second proviso; Appointment Rules 2014, Rule 3")

    vac_d = d(2026, 5, 1)
    nxt = d(2026, 8, 20)
    three_m = d(2026, 8, 1)
    last = max(nxt, three_m)
    assert last == nxt
    B.add(M["wd"], "L3",
          f"The only woman director of Aditi Pharma Ltd (unlisted public company; paid-up capital ₹150 crore) resigned with effect from {ds(vac_d)}. The next Board meeting is scheduled for {ds(nxt)}. Under the proviso to Rule 3, the vacancy must be filled by the Board not later than:",
          ds(last),
          [(ds(three_m), "'whichever is earlier' applied instead of 'whichever is later'"),
           (ds(plus(vac_d, 180)), "six-month period used"),
           ("The next annual general meeting", "treats it as a casual vacancy to be filled by members")],
          ["Rule 3 proviso: intermittent vacancy of woman director filled by the Board at the earliest but not later than the immediate next Board meeting or three months from the date of vacancy, whichever is later.",
           f"Next meeting {ds(nxt)}; three months → {ds(three_m)}; later = {ds(last)}."],
          "Deadline = later of (next Board meeting, vacancy + 3 months)", "'Whichever is later' gives the Board the longer period.",
          verify_fact=True, ref="Appointment Rules 2014, Rule 3 proviso")

    B.add(M["wd"], "L1",
          "Under s.149(3), every company must have at least one director who has stayed in India for a total period of not less than:",
          "182 days during the financial year",
          [("120 days during the financial year", "OPC/LLP residency figure applied"),
           ("182 days during the calendar year", "calendar year instead of financial year"),
           ("365 days during the preceding two financial years", "invented test")],
          ["s.149(3): at least one director who stays in India for a total period of not less than 182 days during the financial year (proportionate for a newly incorporated company)."],
          "s.149(3)", "Company resident director: 182 days in the FY; LLP designated partner: 120 days.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.149(3)")

    # ------------------------------------------------------------------ strike off
    inc = d(2026, 1, 12)
    B.add(M["strike"], "L3",
          stmts("Consider the grounds on which the Registrar may, under s.248(1), remove the name of a company from the register:",
                ["The company has failed to commence business within one year of its incorporation.",
                 "The company is not carrying on any business for two immediately preceding financial years and has not applied for dormant status under s.455.",
                 f"The subscribers have not paid their subscription and a declaration under s.10A(1) has not been filed within 180 days of incorporation (for a company incorporated on {ds(inc)}, i.e. by {ds(plus(inc,180))}).",
                 "The company has not declared dividend for three consecutive years."]),
          "1, 2 and 3 only",
          [("1 and 2 only", "overlooks the s.10A commencement-declaration ground"),
           ("1, 2, 3 and 4", "treats non-declaration of dividend as a ground"),
           ("2, 3 and 4 only", "drops the one-year non-commencement ground")],
          ["s.248(1)(a): failure to commence business within one year of incorporation.",
           "s.248(1)(b): no business for two preceding FYs and no application for dormant status.",
           "s.248(1)(c): subscribers' non-payment and no s.10A declaration within 180 days.",
           "No dividend-related ground exists."],
          "s.248(1)", "Dividend policy is irrelevant to strike-off.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.248(1); s.10A")

    B.add(M["strike"], "L3",
          stmts("Prabhat Traders Pvt Ltd wants to apply for voluntary strike-off under s.248(2). Consider:",
                ["The application may be made after extinguishing all its liabilities, by a special resolution or with the consent of 75% of members in terms of paid-up share capital.",
                 "The application cannot be made if, at any time in the previous three months, it changed its name or shifted its registered office from one State to another.",
                 "Once struck off, the company can be restored by the Tribunal on an application by a member, creditor or workman made within twenty years of the publication of the notice in the Official Gazette."]),
          "1, 2 and 3",
          [("1 and 2 only", "overlooks restoration under s.252(3)"),
           ("1 and 3 only", "overlooks the s.249 three-month restrictions"),
           ("2 and 3 only", "overlooks the SR / 75% consent route")],
          ["s.248(2): after extinguishing liabilities, SR or consent of 75% of members by paid-up capital.",
           "s.249(1)(a): no application if in previous three months it changed name or shifted registered office between States.",
           "s.252(3): Tribunal may restore on application by company, member, creditor or workman within 20 years of Gazette notice."],
          "s.248(2); s.249(1); s.252(3)", "Appeal against Registrar's order: 3 years (s.252(1)); restoration by Tribunal: 20 years (s.252(3)).",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.248(2), s.249, s.252")

    # ------------------------------------------------------------------ NCLT s.408 / s.409 / s.420
    B.add(M["s408"], "L1",
          "Under s.408 of the Companies Act, 2013, the National Company Law Tribunal is constituted by the Central Government and consists of:",
          "A President and as many Judicial and Technical members as CG deems necessary",
          [("A Chairperson and not more than eleven Judicial and Technical members", "NCLAT composition under s.410 applied"),
           ("A President and exactly two members for each State", "invented fixed composition"),
           ("Judges of the High Courts nominated by the Chief Justice of India", "confuses constitution with qualification")],
          ["s.408: NCLT — a President and such number of Judicial and Technical members as the CG deems necessary.",
           "s.410: NCLAT — a Chairperson and Judicial and Technical members not exceeding eleven."],
          "s.408; s.410", "President heads NCLT; Chairperson heads NCLAT.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.408, s.410")

    B.add(M["s408"], "L3",
          stmts("Consider the following regarding the NCLT:",
                ["Its Principal Bench is at New Delhi, presided over by the President.",
                 "A Bench ordinarily consists of one Judicial member and one Technical member.",
                 "It is bound by the procedure laid down in the Code of Civil Procedure, 1908.",
                 "It is the Adjudicating Authority for insolvency resolution of companies under the Insolvency and Bankruptcy Code, 2016."]),
          "1, 2 and 4 only",
          [("1 and 2 only", "overlooks NCLT's role under the IBC"),
           ("1, 2, 3 and 4", "believes NCLT is bound by the CPC"),
           ("2, 3 and 4 only", "overlooks the Principal Bench")],
          ["s.419(2): Principal Bench at New Delhi, presided over by the President.",
           "s.419(3): a Bench consists of one Judicial and one Technical member.",
           "s.424(1): not bound by CPC; guided by principles of natural justice.",
           "IBC s.5(1) / s.60: NCLT is the Adjudicating Authority for corporate persons."],
          "s.419, s.424; IBC s.60", "Tribunals follow natural justice, not the CPC.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.419(2), (3), s.424(1); IBC 2016 s.60")

    B.add(M["s409"], "L1",
          "Under s.409(1), the President of the NCLT shall be a person who:",
          "Is or has been a Judge of a High Court for five years",
          [("Has been a District Judge for ten years", "judicial-member qualification confused"),
           ("Is or has been a Judge of the Supreme Court", "NCLAT Chairperson qualification confused"),
           ("Has been in practice as a chartered accountant for fifteen years", "technical-member qualification confused")],
          ["s.409(1): President — is or has been a Judge of a High Court for five years."],
          "s.409(1)", "Supreme Court judge is the NCLAT Chairperson qualification (s.411(1)).",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.409(1); s.411(1)")

    B.add(M["s409"], "L2",
          "Which of the following persons is qualified for appointment as a Judicial Member of the NCLT under s.409(2)?",
          "An advocate of a court who has practised for ten years",
          [("An advocate who has practised for five years", "practice period understated"),
           ("A member of the Indian Corporate Law Service with fifteen years' service", "technical-member route confused"),
           ("A District Judge with three years' service in that post", "five-year district judge requirement not met")],
          ["s.409(2): judicial member — (a) is or has been a High Court Judge; (b) has been a District Judge for at least five years; or (c) has been an advocate of a court for at least ten years."],
          "s.409(2)", "District judge: 5 years; advocate: 10 years.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.409(2)")

    od = d(2025, 3, 10)
    B.add(M["rect"], "L2",
          f"The NCLT passed an order on {ds(od)} containing an arithmetical error apparent from the record. No appeal has been filed against it. Under s.420(2), the Tribunal may amend the order to rectify the mistake:",
          f"Within two years of the order, i.e. up to {ds(date(2027,3,10))}",
          [(f"Within 45 days from the date of the order, i.e. up to {ds(plus(od,45))}", "NCLAT appeal period confused"),
           (f"Within one year from the date of the order, i.e. up to {ds(date(2026,3,10))}", "period understated"),
           ("At any time, since clerical mistakes have no limitation", "ignores the statutory two-year limit")],
          ["s.420(2): within two years from the date of the order, the Tribunal may amend any order to rectify a mistake apparent from the record, and shall do so if the mistake is brought to its notice by the parties.",
           "Proviso: no amendment in respect of an order against which an appeal has been preferred."],
          "s.420(2): two years", "Rectification (2 years) ≠ appeal to NCLAT (45 + 45 days).",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.420(2)")

    B.add(M["rect"], "L3",
          "Assertion (A): The NCLT cannot, under s.420(2), amend an order to rectify a mistake apparent from the record if an appeal has been preferred against that order.\n\nReason (R): Under s.421, any person aggrieved by an order of the Tribunal may appeal to the NCLAT within 45 days from the date on which a copy of the order is made available, extendable by a further period not exceeding 45 days.",
          "Both A and R are true, but R is not the correct explanation of A",
          [("Both A and R are true, and R is the correct explanation of A", "treats the appeal period as the reason for the bar"),
           ("A is true, but R is false", "misremembers the NCLAT appeal period"),
           ("A is false, but R is true", "overlooks the proviso to s.420(2)")],
          ["A: proviso to s.420(2) bars amendment of an order under appeal — true.",
           "R: s.421(3) — 45 days, extendable by up to 45 days — true.",
           "The bar in A exists to avoid conflict with the appellate forum, not because of the appeal time limit; R does not explain A."],
          "s.420(2) proviso; s.421(3)", "Two true statements need not be causally linked.",
          kind="assertion-reason", verify_fact=True, ref="Companies Act 2013 s.420(2), s.421(3)")
