"""Part 2: auditors (s.139-144), fraud reporting, special audit, RPT (s.188), s.186."""
from cab_common import *  # noqa


def add_all(B):
    # ------------------------------------------------------------------ s.141
    B.add(M["s141"], "L1",
          "Which of the following can be appointed as the statutory auditor of a company under s.141 of the Companies Act, 2013?",
          "An LLP whose partners practising in India are mostly chartered accountants",
          [("A private limited company whose directors are all chartered accountants", "body corporate other than an LLP is disqualified"),
           ("A chartered accountant who is a full-time employee of another company", "full-time employment elsewhere disqualifies"),
           ("A firm in which a minority of the partners practising in India are chartered accountants", "majority-of-partners condition not met")],
          ["s.141(1): an individual CA or a firm (including LLP) whose majority partners practising in India are CAs may be appointed.",
           "s.141(3)(a) disqualifies a body corporate other than an LLP; s.141(3)(g) disqualifies a person in full-time employment elsewhere."],
          "s.141(1), (3)", "An LLP is a body corporate but is expressly carved out.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.141(1), (3)(a), (3)(g)")

    n, fvv, mv = 12_000, 10, 450
    B.add(M["s141"], "L2",
          f"The wife of CA Neha, the proposed auditor of Bhoomi Seeds Ltd, holds {inr(n)} equity shares of Bhoomi Seeds (face value ₹{fvv}; market price ₹{mv}). Under s.141(3)(d)(i) read with Rule 10 of the Companies (Audit and Auditors) Rules, 2014, CA Neha is:",
          f"Disqualified, because the face value of the relative's holding ({R(n*fvv)}) exceeds ₹1,00,000",
          [("Eligible, because the limit for a relative's holding is ₹5,00,000 of face value", "₹5 lakh indebtedness limit confused with the securities limit"),
           (f"Disqualified, because the market value of the holding ({R(n*mv)}) exceeds ₹1,00,000", "market value used instead of face value"),
           ("Eligible, because holdings of relatives are not considered under s.141", "relative's security holding overlooked")],
          ["Rule 10(1): a relative may hold securities of face value not exceeding ₹1,00,000.",
           f"Face value = {inr(n)} × ₹{fvv} = {R(n*fvv)} > ₹1,00,000 → disqualification (corrective action possible within 60 days if acquired after appointment)."],
          "Relative's holding test: face value ≤ ₹1,00,000", "The limit is on face value, not market value.",
          verify_fact=True, ref="Companies Act 2013 s.141(3)(d)(i); Companies (Audit and Auditors) Rules 2014, Rule 10")

    aud = [("Public companies", 14, True), ("Private companies with paid-up capital ≥ ₹100 crore", 4, True),
           ("Private companies with paid-up capital < ₹100 crore", 6, False), ("One person companies", 3, False),
           ("Small companies", 2, False)]
    counted = sum(c for _, c, f in aud if f)
    assert counted == 18
    B.add(M["s141"], "L3",
          "CA Ravi holds the following audit appointments:\n\n"
          + table(["Category", "Number"], [[a, c] for a, c, _ in aud], ["---", "---:"])
          + "\n\nFor the ceiling of 20 company audits under s.141(3)(g), the number of his appointments that count is:",
          str(counted),
          [(str(counted + 6), "private companies with paid-up capital below ₹100 crore counted"),
           (str(sum(c for _, c, _ in aud)), "all appointments counted including OPCs and small companies"),
           ("14", "all private companies excluded irrespective of paid-up capital")],
          ["s.141(3)(g) ceiling: 20 companies.",
           "Excluded (MCA exemption and s.141 read with notifications): OPCs, dormant companies, small companies and private companies with paid-up share capital below ₹100 crore.",
           f"Counted = 14 + 4 = {counted}."],
          "Count = public + private (PUC ≥ ₹100 crore)", "Private companies are excluded only if paid-up capital < ₹100 crore.",
          verify_fact=True, ref="Companies Act 2013 s.141(3)(g); MCA notification GSR 583(E) dated 13-06-2017")

    # ------------------------------------------------------------------ s.144 / services
    B.add(M["s144"], "L1",
          "Which of the following services can the statutory auditor of a company render to that company, with approval of the Board or Audit Committee, under s.144?",
          "Tax audit and representation before tax authorities",
          [("Internal audit", "prohibited under s.144(b)"),
           ("Design and implementation of any financial information system", "prohibited under s.144(c)"),
           ("Investment advisory services", "prohibited under s.144(e)")],
          ["s.144 prohibits: (a) accounting and book keeping; (b) internal audit; (c) design/implementation of financial information system; (d) actuarial; (e) investment advisory; (f) investment banking; (g) outsourced financial services; (h) management services.",
           "Taxation services are not in the list and may be rendered with Board/Audit Committee approval."],
          "s.144 prohibited list", "Tax work is permitted; internal audit is not.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.144")

    B.add(M["s144"], "L3",
          stmts("Sagar & Associates are statutory auditors of Pinnacle Foods Ltd. Consider:",
                ["Sagar Advisory LLP, in which Sagar & Associates exercises significant influence, can provide actuarial services to Pinnacle Foods.",
                 "Sagar & Associates can provide book-keeping services to a subsidiary of Pinnacle Foods.",
                 "Sagar & Associates can issue certificates required under other laws to Pinnacle Foods with approval of its Audit Committee."]),
          "3 only",
          [("1 and 3 only", "overlooks that indirect rendering through an associated entity is caught"),
           ("2 and 3 only", "overlooks that services to holding/subsidiary are caught"),
           ("1, 2 and 3", "treats s.144 as applying only to direct services to the company")],
          ["Explanation to s.144: services rendered directly or indirectly — through relatives, entities in which the auditor/partner has significant influence, or to the company's holding company or subsidiary — are covered.",
           "Certification services are not prohibited; they need Board/Audit Committee approval."],
          "s.144 and its Explanation", "The prohibition travels through network entities and group companies.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.144 and Explanation")

    B.add(M["svc"], "L1",
          "Under s.144, services (other than those specifically prohibited) may be rendered by the statutory auditor to the company only if approved by:",
          "The Board of Directors or the Audit Committee",
          [("The shareholders by special resolution", "general meeting approval assumed"),
           ("The Central Government", "confuses with removal of auditor"),
           ("The National Financial Reporting Authority", "NFRA oversees quality, not approval of services")],
          ["s.144 opening words: an auditor may provide such other services as are approved by the Board of Directors or the Audit Committee, as the case may be."],
          "s.144", "Approval is internal (Board / Audit Committee), not by members or government.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.144")

    B.add(M["svc"], "L3",
          stmts("Consider the following in relation to services an auditor may render and the auditor's eligibility:",
                ["A person whose subsidiary or associate company is engaged, on the date of appointment, in consulting and specialised services referred to in s.144 is not eligible for appointment as auditor.",
                 "Rendering management services to the audit client is permitted if fees do not exceed the audit fee.",
                 "An auditor may render outsourced financial services to the company if the Audit Committee approves."]),
          "1 only",
          [("1 and 2 only", "invents a fee-based exemption for management services"),
           ("1 and 3 only", "treats Audit Committee approval as curing a prohibited service"),
           ("2 and 3 only", "overlooks s.141(3)(i)")],
          ["s.141(3)(i): disqualification where the person's subsidiary/associate/other entity is engaged in s.144 consulting and specialised services on the date of appointment.",
           "Management services and outsourced financial services are prohibited outright; approval cannot cure them."],
          "s.141(3)(i); s.144(g), (h)", "Board/Audit Committee approval applies only to non-prohibited services.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.141(3)(i); s.144")

    # ------------------------------------------------------------------ fraud reporting
    B.add(M["fraud"], "L1",
          "Under s.143(12) read with Rule 13 of the Companies (Audit and Auditors) Rules, 2014, a statutory auditor must report a suspected fraud against the company by officers or employees to the Central Government where the amount involved is:",
          "₹1 crore or above",
          [("₹50 lakh or above", "invented lower threshold"),
           ("₹5 crore or above", "invented higher threshold"),
           ("Any amount, irrespective of size", "ignores the Board/Audit Committee route for smaller frauds")],
          ["Rule 13(1): fraud involving ₹1 crore or above → report to Central Government (Form ADT-4).",
           "Below ₹1 crore → report to Audit Committee/Board within 2 days; disclosed in the Board's report."],
          "Rule 13 threshold ₹1 crore", "Smaller frauds still get reported — to the Audit Committee/Board.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.143(12); Audit Rules 2014, Rule 13")

    B.add(M["fraud"], "L2",
          stmts("During the audit of Sunlit Retail Ltd (a listed company) the auditor finds a fraud of ₹42 lakh by a store manager. Consider:",
                ["The auditor must report the matter to the Audit Committee within 2 days of his knowledge of the fraud.",
                 "The auditor must also file Form ADT-4 with the Central Government.",
                 "The Board's report must disclose the details of the fraud reported by the auditor, including the nature and amount involved and remedial action taken."]),
          "1 and 3 only",
          [("1, 2 and 3", "files ADT-4 even though the amount is below ₹1 crore"),
           ("2 and 3 only", "routes a below-threshold fraud to the Central Government"),
           ("1 only", "misses the Board's-report disclosure under s.134(3)(ca)")],
          ["Rule 13(3): fraud below ₹1 crore → report to Audit Committee (or Board) within 2 days of knowledge.",
           "s.134(3)(ca): Board's report discloses frauds reported under s.143(12) other than those reported to the Central Government.",
           "ADT-4 is only for ₹1 crore or above."],
          "Rule 13(3); s.134(3)(ca)", "Reporting route depends on the ₹1 crore threshold.",
          kind="statement", verify_fact=True, ref="Audit Rules 2014, Rule 13(3); Companies Act 2013 s.134(3)(ca)")

    # ------------------------------------------------------------------ removal with CG approval
    br = d(2026, 3, 3)
    B.add(M["remcg"], "L1",
          "An auditor of a company may be removed from office before the expiry of his term only by:",
          "Special resolution, after prior Central Government approval",
          [("An ordinary resolution passed after special notice to members", "confuses with removal of a director / non-reappointment"),
           ("A resolution of the Board with approval of the Audit Committee", "Board has no power to remove an auditor"),
           ("A special resolution followed by confirmation of the Tribunal", "confuses with reduction of capital")],
          ["s.140(1): removal before expiry of term requires previous approval of Central Government and a special resolution; the auditor is given a reasonable opportunity of being heard."],
          "s.140(1)", "Prior CG approval comes first, then the special resolution.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.140(1)")

    # ------------------------------------------------------------------ resignation
    B.add(M["resig"], "L2",
          f"The statutory auditor of Anand Dairy Ltd resigned on {ds(d(2026,6,20))}. Under s.140(2), he must file a statement in Form ADT-3 indicating the reasons and other facts relevant to the resignation with:",
          f"The company and the Registrar within 30 days, i.e. by {ds(plus(d(2026,6,20),30))}",
          [(f"The Registrar only, within 15 days, i.e. by {ds(plus(d(2026,6,20),15))}", "wrong recipient and period"),
           (f"The company and the Registrar within 60 days, i.e. by {ds(plus(d(2026,6,20),60))}", "wrong period"),
           ("The Central Government only, within 30 days of resigning", "confuses with fraud reporting")],
          ["s.140(2) read with Rule 8: resigning auditor files ADT-3 with the company and the Registrar (and CAG for s.139(5) companies) within 30 days from the date of resignation."],
          "s.140(2): ADT-3 within 30 days", "Both company and Registrar; not the Central Government.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.140(2); Audit Rules 2014, Rule 8")

    nd = d(2026, 5, 4)
    eff = d(2026, 5, 31)
    B.add(M["resig"], "L2",
          f"Ms Iyer, a director of Kunal Exports Ltd, delivered her resignation letter to the company on {ds(nd)}, stating that it should take effect from {ds(eff)}. Under s.168, her resignation takes effect on, and the company must intimate the Registrar (Form DIR-12) within:",
          f"{ds(eff)}; within 30 days",
          [(f"{ds(nd)}; within 30 days", "ignores the later effective date specified in the notice"),
           (f"{ds(eff)}; within 15 days", "wrong intimation period"),
           ("The date the Board accepts the resignation; within 30 days", "treats Board acceptance as necessary")],
          ["s.168(2): resignation effective from the date the company receives the notice or the date specified by the director, whichever is later.",
           "s.168(1) read with Rule 15: company files DIR-12 within 30 days of receipt of notice; Board acceptance is not required."],
          "Effective date = later of receipt date and specified date", "Resignation needs no acceptance by the Board.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.168; Appointment Rules 2014, Rule 15")

    # ------------------------------------------------------------------ special auditor (CAG / RBI)
    reg = d(2026, 4, 1)
    B.add(M["spaud"], "L2",
          "In the case of a government company, the statutory auditor for a financial year (other than the first auditor) is appointed by:",
          "The Comptroller and Auditor-General of India, within 180 days from the commencement of the financial year",
          [("The Board of Directors, within 30 days from the commencement of the financial year", "non-government first-auditor rule applied"),
           ("The members at the AGM for a term of five years", "s.139(1) rule for non-government companies applied"),
           ("The Comptroller and Auditor-General of India, within 60 days from the commencement of the financial year", "60-day first-auditor period of s.139(7) applied to subsequent auditors")],
          ["s.139(5): CAG appoints the auditor of a government company within 180 days from commencement of the FY.",
           "s.139(7): first auditor of a government company — CAG within 60 days of registration."],
          "s.139(5), (7)", "180 days (subsequent) vs 60 days (first auditor).",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.139(5), (7)")

    B.add(M["spaud"], "L2",
          stmts("Consider the following statements regarding special/test audits:",
                ["The CAG may, by order, cause a test audit of the accounts of a government company to be conducted.",
                 "The Reserve Bank of India may, in the public interest or in the interest of depositors, direct a special audit of a banking company's accounts and may appoint a chartered accountant for that purpose.",
                 "The shareholders of any company may, by ordinary resolution, appoint a special auditor to replace the statutory auditor for a particular quarter."]),
          "1 and 2 only",
          [("1 only", "overlooks RBI's special-audit power under the BR Act"),
           ("1, 2 and 3", "invents a shareholders' power to appoint special auditors"),
           ("2 and 3 only", "overlooks CAG's test audit power")],
          ["s.143(7): CAG may cause test audit of companies covered under s.139(5)/(7).",
           "BR Act 1949 s.30(1B): RBI may order a special audit of a banking company and appoint a CA or direct the existing auditor.",
           "No such shareholders' power exists under the Companies Act, 2013."],
          "s.143(7); BR Act s.30(1B)", "Special audits are ordered by a public authority, not by members.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.143(7); Banking Regulation Act 1949 s.30(1B)")

    # ------------------------------------------------------------------ Tribunal-ordered removal
    B.add(M["tribrem"], "L2",
          "Under s.140(5), where the Tribunal passes a final order that an auditor has acted fraudulently or abetted or colluded in fraud, the auditor:",
          "Cannot be appointed auditor of any company for five years; liable under s.447",
          [("Is barred from auditing only that company, for a period of three years", "limits the bar to one company and a wrong period"),
           ("Is barred for ten years, but only from auditing listed companies", "wrong period and scope"),
           ("Must be removed by special resolution with Central Government approval before the bar applies", "confuses with s.140(1) removal")],
          ["s.140(5) second proviso: auditor (individual or firm) against whom final order is passed is ineligible to be appointed auditor of any company for five years, and liable under s.447."],
          "s.140(5)", "The bar applies to all companies, for five years.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.140(5)")

    rec = d(2026, 7, 8)
    B.add(M["tribrem"], "L3",
          stmts(f"The Central Government applied to the Tribunal on {ds(rec)} alleging that the auditor of Lotus Housing Ltd colluded in a fraud. Consider:",
                ["The Tribunal may act on the application of the Central Government, of any person concerned, or suo motu.",
                 f"If satisfied that a change of auditor is required, the Tribunal shall, within 15 days of receipt of the application (i.e. by {ds(plus(rec,15))}), order that the auditor shall not function as auditor, and the Central Government may appoint another auditor in his place.",
                 "The order can be made only after the auditor's term expires."]),
          "1 and 2 only",
          [("1 only", "misses the 15-day interim order on CG application"),
           ("2 only", "believes only the Central Government can move the Tribunal"),
           ("1, 2 and 3", "believes the order waits for the term to expire")],
          ["s.140(5): Tribunal acts suo motu or on application by CG or any person concerned.",
           "First proviso: on CG application, if satisfied, Tribunal orders within 15 days of receipt that the auditor shall not function; CG may appoint another auditor.",
           "The purpose is to change the auditor during the term."],
          "s.140(5) and first proviso", "The 15-day window runs from receipt of the application.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.140(5)")

    # ------------------------------------------------------------------ RPT
    to, nw = 800e7, 300e7
    txn = 85e7
    B.add(M["rpt"], "L2",
          f"Tarang Electricals Ltd (turnover {cr(to)}, net worth {cr(nw)} as per audited financial statements of the preceding year) proposes to purchase raw materials worth {cr(txn)} during the year from a private company in which its managing director is a director and member. The transaction is not in the ordinary course of business. Under s.188 read with Rule 15, the transaction requires:",
          "Board approval plus members' ordinary resolution (≥ 10% of turnover)",
          [("Board approval only, since it is below 10% of net worth", "net worth base used for a goods-purchase contract"),
           ("Board approval and approval of members by special resolution", "special-resolution requirement of the pre-2015 regime applied"),
           ("No approval, since the counterparty is a private company", "misunderstands related-party definition")],
          [f"Rule 15(3)(i)(a): sale/purchase of goods or materials ≥ 10% of turnover needs members' ordinary resolution.",
           f"10% of turnover = {cr(0.1*to)}; transaction {cr(txn)} ≥ threshold.",
           "A private company in which a director is a director and member is a related party (s.2(76)(v))."],
          "Goods contracts: ≥ 10% of turnover → ordinary resolution", "Property purchases use net worth; goods contracts use turnover.",
          verify_fact=True, ref="Companies Act 2013 s.188(1); s.2(76); Meetings of Board Rules 2014, Rule 15(3)")

    B.add(M["rpt"], "L3",
          stmts("Under s.188 of the Companies Act, 2013, consider:",
                ["A contract with a related party entered into without Board/members' approval may be ratified by the Board or members, as the case may be, within three months from the date on which it was entered into.",
                 "In a general meeting resolution to approve a related party contract, no member of the company shall vote if such member is a related party in the context of that contract.",
                 "Transactions in the ordinary course of business that are on arm's length basis are outside the approval requirements of s.188(1)."]),
          "1, 2 and 3",
          [("1 and 2 only", "overlooks the ordinary course + arm's length exemption"),
           ("2 and 3 only", "overlooks the three-month ratification window"),
           ("1 and 3 only", "overlooks the voting bar on interested members")],
          ["s.188(3): ratification within three months; else voidable at the Board's option.",
           "s.188(1) fourth proviso: related-party members cannot vote on that resolution (exemption for companies where 90% or more members are relatives of promoters or related parties).",
           "Explanation (b)/fifth proviso: ordinary course + arm's length transactions are outside s.188(1)."],
          "s.188(1) provisos; s.188(3)", "All three conditions of s.188 are standard traps.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.188(1), (3)")

    B.add(M["rpt"], "L1",
          "Which of the following is NOT one of the categories of contracts/arrangements listed in s.188(1)?",
          "Borrowing from a scheduled bank in which a director holds 0.5% shares",
          [("Leasing of property of any kind", "listed in s.188(1)(c)"),
           ("Appointment of a related party to any office or place of profit in the company", "listed in s.188(1)(f)"),
           ("Underwriting the subscription of securities of the company", "listed in s.188(1)(g)")],
          ["s.188(1): (a) sale/purchase/supply of goods; (b) selling/buying property; (c) leasing property; (d) availing/rendering services; (e) appointment of agent; (f) office or place of profit; (g) underwriting.",
           "A bank in which a director merely holds 0.5% is not a related party, and borrowing is not a listed category."],
          "s.188(1)(a)–(g)", "Holding < 2% with a director does not make a public company a related party.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.188(1); s.2(76)")

    # ------------------------------------------------------------------ s.186
    pu, fr, sp, rr, crr = 120e7, 90e7, 30e7, 25e7, 10e7
    a = 0.6 * (pu + fr + sp)
    b = fr + sp
    lim = max(a, b)
    assert round(lim) == 144e7
    B.add(M["s186"], "L2",
          "Extract from the latest audited balance sheet of Rudra Steel Ltd (₹ crore):\n\n"
          + table(["Item", "₹ crore"], [["Paid-up share capital", 120], ["Free reserves", 90], ["Securities premium", 30],
                                         ["Revaluation reserve", 25], ["Capital redemption reserve", 10]], ["---", "---:"])
          + "\n\nThe aggregate limit for loans, guarantees, securities and investments that Rudra can make under s.186(2) without a special resolution is:",
          cr(lim),
          [(cr(0.6 * (pu + fr + sp + rr + crr)), "revaluation reserve and CRR wrongly included"),
           (cr(b), "the lower of the two limbs taken"),
           (cr(0.6 * (pu + fr)), "securities premium omitted from the 60% limb")],
          [f"Limb 1: 60% × (120 + 90 + 30) = {cr(a)}.",
           f"Limb 2: 100% × (90 + 30) = {cr(b)}.",
           f"Limit = higher = {cr(lim)}. Revaluation reserve and CRR are neither free reserves nor securities premium."],
          "Limit = max[60% (PUC + FR + SP), 100% (FR + SP)]", "It is 'whichever is more', not less.",
          verify_fact=True, ref="Companies Act 2013 s.186(2); s.2(43)")

    B.add(M["s186"], "L3",
          stmts("Consider the following regarding s.186 of the Companies Act, 2013:",
                ["A special resolution is not required for a loan given by a company to its wholly owned subsidiary even if the s.186(2) limit is exceeded.",
                 "Every loan, guarantee, security or investment under s.186 must be approved by a Board resolution passed at a meeting with the consent of all directors present.",
                 "A company that is in default in repayment of deposits or interest thereon shall not give any loan, guarantee or security or make any acquisition till the default subsists.",
                 "The Board may approve an inter-corporate loan by circular resolution if all directors sign."]),
          "1, 2 and 3 only",
          [("1 and 2 only", "misses the s.186(8) bar on defaulting companies"),
           ("2, 3 and 4 only", "overlooks the WOS exemption and allows circulation"),
           ("1, 2, 3 and 4", "allows circulation for a s.179(3) matter")],
          ["s.186(3) proviso: SR not needed for loans/guarantees/security to WOS or JV, or acquisition of securities of WOS.",
           "s.186(5): Board resolution at a meeting, consent of all directors present (PFI approval where term loan subsists, subject to proviso).",
           "s.186(8): bar while deposit default subsists.",
           "Loans and investments are s.179(3)(d)/(e)/(f) powers exercisable only at Board meetings — not by circulation."],
          "s.186(3), (5), (8); s.179(3)", "'Consent of all directors present' presupposes a meeting.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.186(3), (5), (8); s.179(3)")
