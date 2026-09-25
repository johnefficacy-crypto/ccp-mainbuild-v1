"""REG-CORPUS-ACT-REC builder: financial-sector-acts — recovery / insolvency / AML Acts (89 Q).
IBC 2016 (25) · SARFAESI 2002 (22) · RDB Act 1993 (20) · PMLA 2002 (22).
Every numeric key and distractor is computed here from stated figures; asserts guard hand-checked values.
Run: python3 build_REG-CORPUS-ACT-REC.py  -> out/REG-CORPUS-ACT-REC.json + _review.md
"""
import sys, os as _os
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
from reglib import Batch, inr, R, pct, lakh, crore, make_slug  # noqa: F401
from collections import Counter
from datetime import date, timedelta

BATCH, PREFIX = "REG-CORPUS-ACT-REC", "ACTR"
LIST = _os.path.join(_REG, 'lists', 'fsa.' + BATCH + '.tsv')

IBC = "Insolvency and Bankruptcy Code, 2016"
SAR = "Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002"
RDB = "Recovery of Debts and Bankruptcy Act, 1993"
PML = "Prevention of Money-laundering Act, 2002"

MT = {  # key -> (name, act)
    "I1": ("IBC — CIRP initiation, default threshold and applicants (s.4, 7, 9, 10)", IBC),
    "I2": ("IBC — moratorium, IRP/RP and CoC decision-making", IBC),
    "I3": ("IBC — CIRP timelines, resolution plan and s.29A ineligibility", IBC),
    "I4": ("IBC — liquidation waterfall under s.53", IBC),
    "I5": ("IBC — pre-packaged insolvency for MSMEs and IBBI", IBC),
    "S1": ("SARFAESI — s.13 demand notice, representation and enforcement measures", SAR),
    "S2": ("SARFAESI — consortium consent (s.13(9)) and CMM/DM assistance (s.14)", SAR),
    "S3": ("SARFAESI — DRT application (s.17) and DRAT pre-deposit (s.18)", SAR),
    "S4": ("SARFAESI — exclusions under s.31 and applicability", SAR),
    "S5": ("SARFAESI — asset reconstruction companies and CERSAI", SAR),
    "D1": ("RDB Act — DRT jurisdiction and pecuniary threshold", RDB),
    "D2": ("RDB Act — original application procedure and limitation", RDB),
    "D3": ("RDB Act — DRAT appeal and pre-deposit", RDB),
    "D4": ("RDB Act — recovery certificate and recovery officer", RDB),
    "P1": ("PMLA — offence of money laundering and punishment (s.3, s.4)", PML),
    "P2": ("PMLA — scheduled offences and proceeds of crime", PML),
    "P3": ("PMLA — reporting entities, record-keeping and FIU-IND", PML),
    "P4": ("PMLA — provisional attachment and Adjudicating Authority", PML),
    "P5": ("PMLA — arrest, bail (s.45), Appellate Tribunal and s.66", PML),
}
SLUG = {k: make_slug(v[0], "fsa") for k, v in MT.items()}
_os.makedirs(_os.path.dirname(LIST), exist_ok=True)
with open(LIST, "w", encoding="utf-8") as f:
    f.write("slug\texams\tname\tact\n")
    for k, (n, a) in MT.items():
        f.write(f"{SLUG[k]}\tifsca,pfrda,sebi\t{n}\t{a}\n")

B = Batch(BATCH, "financial-sector-acts", PREFIX, list_file=LIST)
ACT_OF = {}


def Q(mk, level, stem, correct, wrongs, steps, formula, trap, kind, ref, group=None):
    qid = B.add(micro=SLUG[mk], level=level, stem=stem, correct=correct, wrongs=wrongs, steps=steps,
                formula=formula, trap=trap, kind=kind, group=group, verify_fact=True, ref=ref)
    ACT_OF[qid] = mk[0]


def D(d): return f"{d.day} {d.strftime('%B %Y')}"
def cr(x, d=2): return f"₹{x:,.{d}f} crore"      # x already in crore
def lk(x, d=2): return f"₹{x:,.{d}f} lakh"       # x already in lakh
def P2(x): return f"{x*100:.2f}%"


STMT = ["1 and 2 only", "1 and 3 only", "2 and 3 only", "1, 2 and 3", "1 only", "2 only", "3 only"]
AR = {"A": "Both A and R are true, and R is the correct explanation of A",
      "B": "Both A and R are true, but R is not the correct explanation of A",
      "C": "A is true, but R is false",
      "D": "A is false, but R is true"}

# =====================================================================================
# IBC (25): L1 5 · L2 8 · L3 7 · L4 5
# =====================================================================================
Q("I1", "L1",
  "Under section 4 of the Insolvency and Bankruptcy Code, 2016, read with the Central Government notification of March 2020, "
  "the minimum amount of default for initiating the corporate insolvency resolution process (CIRP) against a corporate debtor is:",
  "₹1 crore",
  [("₹1 lakh", "original s.4 figure, superseded by the 2020 notification"),
   ("₹10 lakh", "minimum default notified for pre-packaged insolvency of MSMEs"),
   ("₹20 lakh", "pecuniary threshold notified for DRT jurisdiction under the RDB Act")],
  ["s.4 fixes the minimum default at ₹1 lakh but lets the Central Government raise it up to ₹1 crore.",
   "The March 2020 notification raised it to ₹1 crore; it applies to applications under ss.7, 9 and 10."],
  "IBC s.4: minimum default ₹1 lakh, notifiable up to ₹1 crore (notified ₹1 crore, 24.03.2020)",
  "₹10 lakh is the separate threshold for PPIRP (Chapter III-A), not for ordinary CIRP.",
  "conceptual", f"{IBC}, s.4 (notification S.O. 1205(E), 24.03.2020)")

# I-2 default amount from a table
tl_over, int_over, lc_dev, future = 42.0, 21.5, 38.0, 60.0
dflt = tl_over + int_over + lc_dev
assert abs(dflt - 101.5) < 1e-9
Q("I1", "L2",
  "Kestrel Bank is a financial creditor of Veltrix Components Ltd. Position on the date of its application under section 7:\n\n"
  "| Item | ₹ lakh |\n|---|---:|\n"
  f"| Term-loan instalments due and unpaid | {tl_over:.2f} |\n"
  f"| Interest due and unpaid on the term loan | {int_over:.2f} |\n"
  f"| Letter of credit devolved and not reimbursed on demand | {lc_dev:.2f} |\n"
  f"| Term-loan instalments falling due over the next 18 months | {future:.2f} |\n\n"
  "Taking the notified minimum default, the amount of default and the maintainability of the application are:",
  f"{lk(dflt)} — the application is maintainable",
  [(f"{lk(dflt + future)} — the application is maintainable", "instalments not yet due counted as default"),
   (f"{lk(tl_over + lc_dev)} — the application is not maintainable", "unpaid interest excluded from default"),
   (f"{lk(tl_over + int_over)} — the application is not maintainable", "devolved LC ignored; only the term loan counted")],
  ["Default = debt that has become due and payable and is not paid (s.3(12)).",
   f"Due and unpaid: {tl_over} + {int_over} + {lc_dev} = ₹{dflt:.2f} lakh; future instalments are not yet due.",
   f"₹{dflt:.2f} lakh ≥ ₹100 lakh (₹1 crore), so the s.7 application is maintainable."],
  "Default (s.3(12)) = amount due and unpaid; compare with ₹1 crore (s.4)",
  "Interest that is due is part of the financial debt in default; unmatured instalments are not.",
  "numerical", f"{IBC}, ss.3(12), 4, 7")

# I-3 demand notice
dn = date(2026, 4, 6)
Q("I1", "L2",
  f"An operational creditor delivers a demand notice under section 8 to Sarnath Pumps Ltd on {D(dn)}. The company neither pays "
  "nor brings to notice any existing dispute. Excluding the day of delivery, the period after whose expiry the creditor may file "
  "an application under section 9 ends on:",
  D(dn + timedelta(10)),
  [(D(dn + timedelta(9)), "day of delivery counted in the 10 days"),
   (D(dn + timedelta(14)), "14-day period for the Adjudicating Authority to admit taken as the notice period"),
   (D(dn + timedelta(30)), "30-day period assumed for the corporate debtor's reply")],
  ["s.8(2): within 10 days of receipt of the demand notice the corporate debtor must show an existing dispute or repay.",
   "s.9(1): the application may be filed after expiry of 10 days from delivery if no payment or notice of dispute is received.",
   f"{D(dn)} + 10 days = {D(dn + timedelta(10))}."],
  "s.8(2)/s.9(1): 10 days from delivery of demand notice",
  "The 14 days in s.9(5) is the Authority's time to decide, not the debtor's reply period.",
  "numerical", f"{IBC}, ss.8, 9")

Q("I1", "L1",
  "For a corporate applicant to initiate CIRP of itself under section 10, the application must be accompanied, among other things, by:",
  "A special resolution of members, or three-fourths of partners",
  [("An ordinary resolution of members passed at a general meeting", "ordinary instead of special resolution"),
   ("Approval of financial creditors holding 66% of the financial debt", "pre-packaged (s.54A) approval confused with s.10"),
   ("Prior written approval of the IBBI for filing the application", "regulator's role confused with filing requirement")],
  ["s.10(3)(c) (2020 amendment): a special resolution of shareholders, or a resolution of at least three-fourths of the total number "
   "of partners, approving the filing.",
   "The IBBI does not approve filings; creditor approval of 66% is a pre-pack requirement."],
  "IBC s.10(3)(c)", "Pre-pack needs creditor approval; ordinary s.10 needs member approval.",
  "conceptual", f"{IBC}, s.10(3)")

# I-5 allottees threshold
allot = 800
need = min(100, allot * 0.10)
assert need == 80
Q("I1", "L2",
  f"Project Aster, a residential real-estate project of Meridian Realty Ltd, has {inr(allot)} allottees. Under the proviso to "
  "section 7(1) (2020 amendment), the minimum number of Aster allottees who must jointly file an application for CIRP is:",
  f"{need:.0f} allottees",
  [("100 allottees", "fixed number applied, ignoring 'whichever is less'"),
   (f"{allot*0.66:.0f} allottees", "66% CoC voting threshold applied to allottees"),
   (f"{allot//2 + 1} allottees", "simple majority of allottees assumed")],
  ["Proviso to s.7(1): at least 100 allottees of the same project or 10% of total allottees of that project, whichever is less.",
   f"10% of {allot} = {allot*0.10:.0f}; lower of 100 and {allot*0.10:.0f} = {need:.0f}."],
  "min(100, 10% of allottees of the same project)", "It is the LOWER of the two figures.",
  "numerical", f"{IBC}, s.7(1) second proviso (IBC (Amendment) Act, 2020)")

# I-7 CoC plan vote
fc7 = {"Bank P": 420, "Bank Q": 310, "NBFC R": 180, "ARC S": 140, "Bank T": 150}
tot7 = sum(fc7.values())
favour7 = fc7["Bank P"] + fc7["NBFC R"] + fc7["Bank T"]
cast7 = tot7 - fc7["ARC S"]
vs7, vc7 = favour7 / tot7, favour7 / cast7
assert abs(vs7 - 0.625) < 1e-9 and vs7 < 0.66 < vc7
Q("I2", "L2",
  "Admitted financial debt of the members of the CoC of Halden Polymers Ltd (₹ crore):\n\n| Creditor | Admitted claim |\n|---|---:|\n"
  + "\n".join(f"| {k} | {v} |" for k, v in fc7.items()) +
  "\n\nOn a resolution plan, Bank P, NBFC R and Bank T vote in favour, Bank Q votes against and ARC S abstains. The outcome is:",
  f"Not approved — {P2(vs7)} of voting share is below 66%",
  [(f"Approved — {P2(vc7)} of votes cast exceeds 66%", "base taken as votes cast, not total voting share"),
   (f"Approved — {P2(vs7)} of voting share exceeds 51%", "ordinary-decision threshold of s.21(8) applied"),
   ("Approved — three of the four creditors voting are in favour", "majority by number instead of by value")],
  [f"Total voting share base = {tot7}; in favour = 420 + 180 + 150 = {favour7}.",
   f"Voting share in favour = {favour7}/{tot7} = {P2(vs7)}.",
   "s.30(4): plan needs not less than 66% of the voting share of financial creditors — abstentions do not reduce the base."],
  "s.30(4): approval ≥ 66% of voting share (s.5(28): share of financial debt)",
  "Abstaining creditors still count in the denominator.",
  "numerical", f"{IBC}, ss.5(28), 21(8), 30(4)")

Q("I2", "L2",
  "Consider the following statements about the moratorium under section 14:\n\n"
  "1. A secured creditor cannot take action under the SARFAESI Act against the corporate debtor's assets during the moratorium.\n"
  "2. The moratorium does not bar a creditor from proceeding against a surety under a contract of guarantee to the corporate debtor.\n"
  "3. A supplier of electricity may terminate supply during the moratorium for non-payment of dues relating to the pre-CIRP period.\n\n"
  "Which of the statements given above is/are correct?",
  "1 and 2 only",
  [("1, 2 and 3", "essential supplies wrongly treated as terminable (s.14(2))"),
   ("1 only", "s.14(3)(b) guarantor carve-out (2019 amendment) missed"),
   ("2 and 3 only", "SARFAESI enforcement wrongly treated as outside s.14(1)(c)")],
  ["s.14(1)(c) bars any action to foreclose, recover or enforce security interest, including under SARFAESI.",
   "s.14(3)(b) (2019 amendment): moratorium does not apply to a surety in a contract of guarantee.",
   "s.14(2): supply of essential goods or services shall not be terminated, suspended or interrupted during the moratorium."],
  "IBC s.14(1)(c), 14(2), 14(3)(b)", "The moratorium protects the corporate debtor, not its guarantors.",
  "statement", f"{IBC}, s.14 (as amended 2019/2020)")

Q("I2", "L3",
  "**Assertion (A):** At its first meeting, the committee of creditors may replace the interim resolution professional with another "
  "resolution professional by a vote of 51% of the voting share.\n\n"
  "**Reason (R):** Under section 21(8), all decisions of the committee of creditors are taken by a vote of not less than 51% of the "
  "voting share of the financial creditors, unless otherwise provided in the Code.",
  AR["D"],
  [(AR["A"], "s.22(2) special majority of 66% overlooked"),
   (AR["B"], "Assertion treated as true"),
   (AR["C"], "s.21(8) default rule wrongly rejected")],
  ["s.21(8): default threshold 51% 'save as otherwise provided'.",
   "s.22(2): the first CoC meeting may resolve to appoint the IRP as RP or replace him — by a vote of not less than 66%.",
   "So A is false (needs 66%), R is a true statement of the default rule."],
  "s.22(2): 66% to replace IRP; s.21(8): 51% default", "The 51% rule is displaced wherever the Code prescribes 66%.",
  "assertion-reason", f"{IBC}, ss.21(8), 22(2)")

# I-10 330-day computation
ext, excl = 90, 25
elapsed = 180 + ext + excl
remain = 330 - elapsed
assert remain == 35
Q("I3", "L3",
  "In the CIRP of Norvane Textiles Ltd, the 180-day period expired without a plan and the Adjudicating Authority granted the one-time "
  f"extension of {ext} days. Earlier, on the resolution professional's application, the Authority had excluded {excl} days during which "
  "a High Court stay halted the process, so the extended period ended "
  f"{elapsed} calendar days after the insolvency commencement date. Under the outer limit in the third proviso to section 12(3), "
  "the maximum further calendar time available for completing the CIRP is:",
  f"{remain} days",
  [(f"{330 - 180 - ext} days", "excluded litigation days kept outside the 330-day limit"),
   (f"{excl} days", "excluded period re-added as fresh time"),
   (f"{ext} days", "a second 90-day extension assumed")],
  ["s.12(1)–(3): 180 days + one extension of up to 90 days.",
   "Third proviso (2019 amendment): CIRP to be completed within 330 days from ICD, INCLUDING any extension and time taken in legal proceedings.",
   f"Calendar days used = 180 + {ext} + {excl} = {elapsed}; remaining = 330 − {elapsed} = {remain} days."],
  "Outer limit 330 days (incl. extension and litigation time)",
  "Exclusions granted for litigation still count against 330 (subject to the AA's discretion in exceptional cases, Essar Steel 2019).",
  "numerical", f"{IBC}, s.12(3) third proviso (IBC (Amendment) Act, 2019)")

Q("I3", "L2",
  "In the CIRP of Palmyra Foods Ltd, the resolution professional seeks to apply for extension beyond 180 days. The CoC resolution "
  "for extension receives 64% of the voting share. The resolution professional:",
  "Cannot apply — the resolution needs at least 66% of the voting share",
  [("Can apply — 51% is enough since extension is an ordinary decision", "s.21(8) default applied instead of s.12(2)"),
   ("Can apply on his own once 180 days lapse, without any CoC resolution", "CoC resolution requirement of s.12(2) ignored"),
   ("Cannot apply — the resolution needs at least 75% of the voting share", "pre-2018 threshold of 75%")],
  ["s.12(2): RP shall file the application for extension only if instructed by a CoC resolution passed by not less than 66% of voting share.",
   "64% < 66%, so no application can be made."],
  "IBC s.12(2): 66%", "75% was the pre-June 2018 threshold.",
  "conceptual", f"{IBC}, s.12(2) (as amended 2018)")

Q("I3", "L3",
  "Consider the following statements on ineligibility under section 29A:\n\n"
  "1. A person in control of a corporate debtor whose account has been an NPA for one year or more becomes eligible if it pays all "
  "overdue amounts with interest and charges on the NPA accounts before submitting the resolution plan.\n"
  "2. A person convicted of an offence punishable with imprisonment of two years or more under an Act in the Twelfth Schedule is "
  "ineligible, but the bar ceases two years after release from imprisonment.\n"
  "3. A scheduled bank that became a related party of the corporate debtor solely by converting its debt into equity is ineligible "
  "under the NPA clause.\n\nWhich of the statements given above is/are correct?",
  "1 and 2 only",
  [("1, 2 and 3", "financial-entity exclusion from 'related party' (Explanation I) missed"),
   ("2 only", "cure proviso to s.29A(c) missed"),
   ("1 and 3 only", "two-year sunset in s.29A(d) proviso missed")],
  ["s.29A(c) proviso: eligible on payment of all overdue amounts with interest and charges before submission of the plan.",
   "s.29A(d): conviction — 2 years+ under Twelfth Schedule Acts or 7 years+ under any law; bar lifts 2 years after release.",
   "Explanation I: a regulated financial entity that is a related party only due to debt conversion is not a 'related party'."],
  "IBC s.29A(c), (d) and Explanation I", "Lenders converting debt are not caught by the NPA bar.",
  "statement", f"{IBC}, s.29A (as amended 2018)")

Q("I3", "L3",
  "Kavra Weaves Pvt Ltd, a micro enterprise registered under the MSMED Act, 2006, is under CIRP. Its promoter Ms. Ira wishes to submit a "
  "resolution plan. Kavra's loan account has been an NPA for 20 months, and Ms. Ira's personal guarantee for Kavra's debt has been "
  "invoked and remains unpaid. She is not a wilful defaulter, has no conviction, and is not otherwise disqualified. She is:",
  "Eligible — s.240A disapplies clauses (c) and (h) of s.29A for MSMEs",
  [("Ineligible — the account has been an NPA for over one year, s.29A(c)", "s.240A MSME exemption missed"),
   ("Eligible only after clearing all overdues on the NPA account first", "general cure proviso applied; MSME exemption missed"),
   ("Ineligible — her invoked guarantee remains unpaid, s.29A(h)", "s.240A MSME exemption missed for clause (h)")],
  ["s.240A(1): clauses (c) and (h) of s.29A do not apply to a resolution applicant in respect of CIRP of an MSME.",
   "Her only disqualifying facts fall under (c) (NPA) and (h) (invoked guarantee), so she is eligible."],
  "IBC s.240A read with s.29A(c), (h)", "The MSME carve-out removes the need to cure the NPA before bidding.",
  "case", f"{IBC}, ss.29A, 240A")

Q("I3", "L1",
  "After admission of an application under section 7, the applicant may withdraw it under section 12A only with the approval of the "
  "committee of creditors by:",
  "90% of the voting share",
  [("66% of the voting share", "plan-approval threshold of s.30(4)"),
   ("75% of the voting share", "pre-2018 threshold for major CoC decisions"),
   ("51% of the voting share", "ordinary-decision threshold of s.21(8)")],
  ["s.12A: withdrawal of an admitted application with approval of 90% voting share of the CoC."],
  "IBC s.12A: 90%", "The highest threshold in the Code applies to withdrawal.",
  "conceptual", f"{IBC}, s.12A")

Q("I4", "L2",
  "In a liquidation under section 53, arrange the following claims in order of priority (highest first):\n\n"
  "(i) Workmen's dues for the 24 months preceding the liquidation commencement date\n"
  "(ii) Amounts due to the Central Government for the 2 years preceding the liquidation commencement date\n"
  "(iii) Financial debts owed to unsecured creditors\n"
  "(iv) Wages and unpaid dues of employees other than workmen for the 12 months preceding the liquidation commencement date",
  "(i), (iv), (iii), (ii)",
  [("(i), (ii), (iv), (iii)", "Crown-debt priority assumed for government dues"),
   ("(iv), (i), (iii), (ii)", "employees placed ahead of workmen"),
   ("(i), (iii), (iv), (ii)", "unsecured financial creditors placed ahead of employees")],
  ["s.53(1)(b): workmen (24 months) pari passu with secured creditors who relinquish security.",
   "s.53(1)(c): other employees (12 months). s.53(1)(d): unsecured financial creditors.",
   "s.53(1)(e): government dues (2 years) pari passu with secured creditors' unpaid balance after enforcement."],
  "IBC s.53(1)(a)–(h)", "Government dues rank BELOW unsecured financial creditors under the IBC.",
  "conceptual", f"{IBC}, s.53")

# I-16 waterfall
real, cirp_c, liq_c = 212.0, 5.5, 4.5
wk, sec, emp, ufc, gov, occ = 9.0, 150.0, 7.0, 48.0, 18.0, 26.0
avail = real - cirp_c - liq_c
after_b = avail - (wk + sec)
after_c = after_b - emp
ufc_get = min(ufc, after_c)
assert abs(ufc_get - 36.0) < 1e-9
d_e_pool = ufc_get * ufc / (ufc + gov)
c_d_pool = min(ufc, after_b * ufc / (emp + ufc))
no_cost = min(ufc, real - (wk + sec) - emp)
Q("I4", "L3",
  "Liquidation of Corvel Metals Ltd — the liquidator has realised ₹212.00 crore. Claims (₹ crore):\n\n| Item | Amount |\n|---|---:|\n"
  f"| CIRP costs | {cirp_c:.2f} |\n| Liquidation costs | {liq_c:.2f} |\n| Workmen's dues (24 months) | {wk:.2f} |\n"
  f"| Secured creditors who relinquished security | {sec:.2f} |\n| Other employees' dues (12 months) | {emp:.2f} |\n"
  f"| Unsecured financial creditors | {ufc:.2f} |\n| Central and State Government dues (2 years) | {gov:.2f} |\n"
  f"| Other operational creditors | {occ:.2f} |\n\nThe amount distributed to unsecured financial creditors is:",
  cr(ufc_get),
  [(cr(d_e_pool), "government dues ranked pari passu with unsecured financial creditors"),
   (cr(c_d_pool), "other employees ranked pari passu with unsecured financial creditors"),
   (cr(no_cost), "CIRP and liquidation costs not deducted first")],
  [f"Available after costs = 212 − 5.5 − 4.5 = {avail:.2f}.",
   f"(b) workmen + relinquishing secured = {wk + sec:.2f} paid in full → {after_b:.2f} left.",
   f"(c) other employees {emp:.2f} → {after_c:.2f} left.",
   f"(d) unsecured financial creditors claim {ufc:.2f}; receive {ufc_get:.2f}. Government dues (e) receive nil."],
  "s.53(1): each class paid in full before the next; pari passu within a class",
  "Government dues sit in (e), below unsecured financial creditors.",
  "numerical", f"{IBC}, s.53(1)")

# I-17 shortfall in class (b)
real17, cost17, wk17, wk_old, sec17 = 90.0, 6.0, 12.0, 3.0, 108.0
av17 = real17 - cost17
wk_get = wk17 * av17 / (wk17 + sec17)
assert abs(wk_get - 8.4) < 1e-9
wk_old_in = (wk17 + wk_old) * av17 / (wk17 + wk_old + sec17)
Q("I4", "L3",
  f"The liquidator of Ostrava Castings Ltd has ₹{real17:.2f} crore. Insolvency resolution and liquidation costs are ₹{cost17:.2f} crore. "
  f"Workmen's dues are ₹{wk17 + wk_old:.2f} crore, of which ₹{wk_old:.2f} crore relates to the period before the 24 months preceding "
  f"liquidation. Secured creditors who relinquished their security claim ₹{sec17:.2f} crore. The amount received by workmen "
  "under section 53(1)(b) is:",
  cr(wk_get),
  [(cr(wk17), "workmen paid in full ahead of secured creditors"),
   (cr(wk_old_in), "workmen's dues beyond 24 months included in class (b)"),
   (cr(wk17 * real17 / (wk17 + sec17)), "costs not deducted before class (b)")],
  [f"Available for (b) = {real17} − {cost17} = {av17:.2f}.",
   f"Class (b) claims = workmen 24-month dues {wk17} + secured {sec17} = {wk17 + sec17:.2f} (pari passu).",
   f"Workmen receive {wk17} × {av17}/{wk17 + sec17:.0f} = {wk_get:.2f}; older dues of {wk_old} fall to (f)."],
  "s.53(1)(b): pari passu sharing = claim × available ÷ class total",
  "Only 24 months of workmen's dues enjoy (b) priority.",
  "numerical", f"{IBC}, s.53(1)(b), (f)")

sc_claim, sc_real = 80.0, 55.0
Q("I4", "L2",
  f"A secured creditor of Tarsus Motors Ltd (in liquidation) with a claim of ₹{sc_claim:.0f} crore opts under section 52 to realise its "
  f"security itself and recovers ₹{sc_real:.0f} crore. The unpaid ₹{sc_claim - sc_real:.0f} crore ranks:",
  "Under s.53(1)(e), pari passu with 2-year government dues",
  [("Under s.53(1)(b), pari passu with 24-month workmen's dues", "treated as a relinquishing secured creditor"),
   ("Under s.53(1)(d), with unsecured financial creditors", "shortfall treated as an unsecured financial debt"),
   ("Under s.53(1)(f), with the remaining debts and dues", "shortfall pushed to the residual class")],
  ["A secured creditor may relinquish (and rank in (b)) or realise its security (s.52).",
   "s.53(1)(e)(ii): debts owed to a secured creditor for any amount unpaid following enforcement of security interest rank "
   "pari passu with government dues."],
  "IBC s.52, s.53(1)(e)(ii)", "Enforcing outside the waterfall costs the creditor its (b) rank for the shortfall.",
  "conceptual", f"{IBC}, ss.52, 53(1)(e)")

Q("I5", "L1",
  "The minimum amount of default notified for initiating the pre-packaged insolvency resolution process (PPIRP) of an MSME corporate "
  "debtor under Chapter III-A is:",
  "₹10 lakh",
  [("₹1 crore", "ordinary CIRP threshold under s.4"),
   ("₹1 lakh", "original s.4 figure for CIRP"),
   ("₹20 lakh", "DRT pecuniary threshold under the RDB Act")],
  ["s.54A(1) lets the Central Government notify the PPIRP threshold up to ₹1 crore.",
   "The April 2021 notification fixed it at ₹10 lakh."],
  "IBC s.54A(1) (notification of 09.04.2021)", "PPIRP uses a lower threshold than CIRP.",
  "conceptual", f"{IBC}, s.54A (IBC (Amendment) Act, 2021; notification 09.04.2021)")

Q("I5", "L3",
  "Consider the following statements about the pre-packaged insolvency resolution process (PPIRP):\n\n"
  "1. It is available only to a corporate debtor classified as a micro, small or medium enterprise.\n"
  "2. The name of the proposed resolution professional must be approved by financial creditors, not being related parties, "
  "representing at least 66% in value of the financial debt.\n"
  "3. The process must be completed within 180 days of the pre-packaged insolvency commencement date.\n\n"
  "Which of the statements given above is/are correct?",
  "1 and 2 only",
  [("1, 2 and 3", "CIRP's 180-day period applied to PPIRP"),
   ("2 and 3 only", "MSME-only eligibility of s.54A(1) missed"),
   ("1 only", "unrelated-FC 66% approval of s.54A(2)(e) missed")],
  ["s.54A(1): PPIRP for corporate debtors classified as MSMEs.",
   "s.54A(2)(e): proposed RP approved by ≥66% in value of unrelated financial creditors.",
   "s.54D(1): PPIRP to be completed within 120 days of the pre-packaged insolvency commencement date."],
  "IBC ss.54A, 54D", "PPIRP runs 120 days; the resolution plan must reach the AA within 90 days.",
  "statement", f"{IBC}, ss.54A, 54D (IBC (Amendment) Act, 2021)")

Q("I5", "L1",
  "Which of the following is NOT a function of the Insolvency and Bankruptcy Board of India under the Code?",
  "Admitting CIRP applications against debtors",
  [("Registering insolvency professional agencies", "s.196 registration function"),
   ("Registering and regulating information utilities", "s.196 registration function"),
   ("Making regulations governing the CIRP process", "s.196/s.240 regulation-making power")],
  ["IBBI (s.188) registers and regulates IPs, IPAs and IUs and frames regulations (s.196, s.240).",
   "Admission of CIRP applications is an adjudicatory function of the NCLT as Adjudicating Authority (ss.7, 9, 10, 60)."],
  "IBC ss.60, 188, 196", "The regulator (IBBI) and the adjudicator (NCLT) are separate.",
  "conceptual", f"{IBC}, ss.60, 188, 196")

# ---- IBC case set (L4 x5) ----
G1 = "ACTR-CASE-IBC-ORVIAN"
fcs = {"Bharat Bank": 540, "Coastal Bank": 330, "Delta Finance (related party)": 210, "Eastern ARC": 180, "Fortune Bank": 120}
voters = {k: v for k, v in fcs.items() if "related" not in k}
tv = sum(voters.values()); ta = sum(fcs.values())
assert tv == 1170 and ta == 1380
case_ibc = ("**Case — Orvian Steel Ltd (fictional; not an MSME)**\n\nOrvian was admitted into CIRP on a financial creditor's application. "
            "Admitted financial debt (₹ crore; all secured):\n\n| Financial creditor | Admitted claim |\n|---|---:|\n"
            + "\n".join(f"| {k} | {v} |" for k, v in fcs.items()) +
            "\n\nDelta Finance is a related party of Orvian (not a regulated lender that converted debt). Operational creditor Gamma Logistics "
            "has an admitted claim of ₹3.20 crore. The liquidation value estimated by the registered valuers is ₹480 crore; liquidation costs would be "
            "₹10 crore and workmen's dues for 24 months are ₹20 crore. Fortune Bank also holds a personal guarantee from Orvian's promoter.")
be = voters["Bharat Bank"] + voters["Eastern ARC"]
s_be = be / tv
cast_be = be / (tv - voters["Fortune Bank"])
rel_be = be / ta
assert s_be < 0.66 < cast_be
Q("I2", "L4", case_ibc + "\n\nAt the first CoC meeting, Bharat Bank and Eastern ARC vote to replace the IRP; Coastal Bank votes against; Fortune Bank "
  "abstains. The voting share in favour and the result are:",
  f"{P2(s_be)} — the IRP is not replaced",
  [(f"{P2(cast_be)} — the IRP is replaced", "abstaining Fortune Bank removed from the base"),
   (f"{P2(rel_be)} — the IRP is replaced", "related party's debt counted in the base; 51% threshold applied"),
   (f"{P2(s_be)} — the IRP is replaced", "51% threshold of s.21(8) applied instead of 66%")],
  ["First proviso to s.21(2): a related-party financial creditor has no right of representation, participation or voting.",
   f"Base = {tv}; in favour = 540 + 180 = {be}; share = {P2(s_be)}.",
   "s.22(2) needs 66% to replace the IRP → fails."],
  "s.21(2) proviso; s.22(2) 66%", "Exclude the related party from the base before computing shares.",
  "case", f"{IBC}, ss.21(2), 22(2)", group=G1)

bc = voters["Bharat Bank"] + voters["Coastal Bank"]
s_bc = bc / tv
rel_bc = (bc + fcs["Delta Finance (related party)"]) / ta
assert 0.66 < s_bc < 0.75
Q("I3", "L4", case_ibc + "\n\nOn the resolution plan, Bharat Bank and Coastal Bank vote in favour, Eastern ARC and Fortune Bank vote against, and "
  "Delta Finance seeks to vote in favour. The result is:",
  f"Approved with {P2(s_bc)} of the voting share",
  [(f"Approved with {P2(rel_bc)} of the voting share", "related party's vote and debt counted"),
   (f"Rejected — {P2(s_bc)} falls short of 75%", "pre-2018 threshold applied"),
   ("Rejected — dissenting creditors hold more than 25%", "blocking minority computed on the old 75% rule")],
  [f"Voting base excludes Delta: {tv}. In favour = 540 + 330 = {bc}.",
   f"Share = {P2(s_bc)} ≥ 66% (s.30(4)) → approved; Delta's vote is disregarded."],
  "s.30(4): ≥66% of voting share", "Dissent of 25.64% cannot block a 66% plan.",
  "case", f"{IBC}, ss.21(2), 30(4)", group=G1)

lv, lc, wkd = 480.0, 10.0, 20.0
dist = lv - lc
eastern_min = voters["Eastern ARC"] * dist / (ta + wkd)
excl_rel = voters["Eastern ARC"] * dist / (tv + wkd)
no_wk = voters["Eastern ARC"] * dist / ta
no_cost = voters["Eastern ARC"] * lv / (ta + wkd)
assert abs(eastern_min - 180 * 470 / 1400) < 1e-9
Q("I3", "L4", case_ibc + "\n\nEastern ARC dissents. Assume all financial creditors would relinquish security and share under section 53(1)(b) "
  "with workmen. Under section 30(2)(b)(ii), the minimum amount the plan must provide to Eastern ARC is closest to:",
  cr(eastern_min),
  [(cr(excl_rel), "related party's claim excluded from the liquidation waterfall"),
   (cr(no_wk), "workmen's dues omitted from class (b)"),
   (cr(no_cost), "liquidation costs not deducted first")],
  [f"Liquidation value available after costs = {lv} − {lc} = {dist}.",
   f"Class (b) = all secured FCs {ta} (related party's claim ranks in liquidation) + workmen {wkd} = {ta + wkd}.",
   f"Eastern ARC = 180 × {dist}/{ta + wkd:.0f} = {eastern_min:.2f}."],
  "Dissenting FC ≥ its s.53(1) liquidation entitlement",
  "Related parties lose CoC votes, not their rank in the liquidation waterfall.",
  "case", f"{IBC}, ss.30(2)(b), 53(1)", group=G1)

occ_c = 3.20
fc_ratio = dist / (ta + wkd)
occ_par = occ_c * fc_ratio
plan_val = 620.0
occ_all = occ_c * (plan_val - lc) / (ta + wkd + occ_c)
Q("I3", "L4", case_ibc + "\n\nThe plan (total value ₹620 crore) offers Gamma Logistics ₹0.40 crore. Under section 30(2)(b)(i), the minimum Gamma must "
  "receive — the higher of its liquidation entitlement and its entitlement if the plan value were distributed under section 53(1) — is:",
  "Nil — so the ₹0.40 crore offered complies",
  [(f"{cr(occ_par)} — pari passu with secured creditors", "operational creditor placed in class (b)"),
   (f"{cr(occ_all)} — pro rata with all creditors", "plan value shared rateably without priority"),
   (f"{cr(occ_c)} — admitted claim in full", "operational creditors assumed to be paid in full")],
  [f"Liquidation: after costs {dist} < class (b) {ta + wkd}; nothing reaches operational creditors (class (f)).",
   f"Plan value on s.53 priority: {plan_val} − {lc} = {plan_val - lc} < {ta + wkd}; again nil for Gamma.",
   "Higher of nil and nil = nil; ₹0.40 crore meets the floor."],
  "s.30(2)(b)(i): OC ≥ max(liquidation value share, plan value share under s.53)",
  "The floor is a waterfall entitlement, not a rateable share.",
  "case", f"{IBC}, s.30(2)(b) (as amended 2019)", group=G1)

Q("I2", "L4", case_ibc + "\n\nDuring the moratorium, Fortune Bank sues Orvian's promoter on his personal guarantee, and Eastern ARC issues a "
  "possession notice under section 13(4) of the SARFAESI Act over Orvian's plant. Which action may proceed?",
  "Only Fortune Bank's suit against the promoter-guarantor",
  [("Only Eastern ARC's possession notice over the plant", "SARFAESI treated as outside s.14(1)(c)"),
   ("Both actions, since neither is a suit against Orvian", "SARFAESI measure not seen as enforcement against CD"),
   ("Neither action, as the moratorium covers the guarantor", "s.14(3)(b) guarantor carve-out missed")],
  ["s.14(1)(c) bars enforcement of security interest over the corporate debtor's assets, including under SARFAESI.",
   "s.14(3)(b): moratorium does not apply to a surety in a contract of guarantee to the corporate debtor."],
  "IBC s.14(1)(c), 14(3)(b)", "Guarantors are outside the corporate debtor's moratorium.",
  "case", f"{IBC}, s.14 (as amended 2019)", group=G1)

# =====================================================================================
# SARFAESI (22): L1 4 · L2 7 · L3 7 · L4 4
# =====================================================================================
Q("S1", "L1",
  "Under section 13(2) of the SARFAESI Act, a secured creditor's notice to a borrower whose account is an NPA requires the borrower to "
  "discharge its liabilities in full within:",
  "60 days from the date of notice",
  [("30 days from the date of notice", "confused with the 30-day DRAT appeal period"),
   ("45 days from the date of notice", "confused with the 45-day DRT application period of s.17"),
   ("90 days from the date of notice", "confused with the 90-day NPA overdue norm")],
  ["s.13(2): borrower to discharge liabilities within 60 days from the date of notice; failing which s.13(4) measures follow."],
  "SARFAESI s.13(2): 60 days", "90 days is the NPA classification norm, not the notice period.",
  "conceptual", f"{SAR}, s.13(2)")

n13 = date(2026, 1, 12)
Q("S1", "L2",
  f"A bank serves a notice under section 13(2) dated and delivered on {D(n13)}. Excluding the date of notice, the 60-day period "
  "given to the borrower ends on:",
  D(n13 + timedelta(60)),
  [(D(n13 + timedelta(59)), "date of notice counted as day one"),
   (D(n13 + timedelta(45)), "45-day s.17 period used"),
   (D(n13 + timedelta(30)), "30-day period used")],
  [f"{D(n13)} + 60 days = {D(n13 + timedelta(60))} (s.9 General Clauses Act excludes the first day).",
   "Only after this period can s.13(4) measures be taken."],
  "s.13(2): notice date + 60 days", "Count from the day after the notice date.",
  "numerical", f"{SAR}, s.13(2)")

rep = date(2026, 2, 20)
Q("S1", "L2",
  f"A borrower's representation under section 13(3A) against a demand notice is received by the secured creditor on {D(rep)}. "
  "The creditor finds it untenable. The last date for communicating reasons for non-acceptance is:",
  D(rep + timedelta(15)),
  [(D(rep + timedelta(7)), "pre-2016 'one week' period"),
   (D(rep + timedelta(30)), "30-day period assumed"),
   (D(rep + timedelta(60)), "60-day notice period re-applied")],
  ["s.13(3A) (as amended 2016): reasons for non-acceptance to be communicated within fifteen days of receipt of the representation.",
   f"{D(rep)} + 15 days = {D(rep + timedelta(15))}."],
  "s.13(3A): 15 days", "The one-week period was replaced in 2016.",
  "numerical", f"{SAR}, s.13(3A) (Enforcement of Security Interest and Recovery of Debts Laws (Amendment) Act, 2016)")

Q("S1", "L2",
  "Which of the following is NOT a measure available to a secured creditor under section 13(4)?",
  "Attaching and selling the borrower's unencumbered assets",
  [("Taking possession of the secured assets, with a right to sell", "s.13(4)(a) measure"),
   ("Taking over the management of the borrower's business", "s.13(4)(b) measure"),
   ("Appointing a manager to manage the secured assets taken over", "s.13(4)(c) measure")],
  ["s.13(4): (a) possession incl. transfer by lease/assignment/sale; (b) take over management; (c) appoint manager; "
   "(d) require persons who acquired secured assets to pay.",
   "SARFAESI acts only on secured assets; unencumbered assets need a DRT/civil decree."],
  "SARFAESI s.13(4)(a)–(d)", "Enforcement is limited to the security interest.",
  "conceptual", f"{SAR}, s.13(4)")

Q("S1", "L3",
  "Consider the following statements:\n\n"
  "1. A notice under section 13(2) can be issued only after the borrower's account has been classified as a non-performing asset.\n"
  "2. The borrower may redeem the secured asset by tendering the dues with costs at any time before publication of the notice for "
  "public auction or tender.\n"
  "3. After receipt of a section 13(2) notice, the borrower cannot transfer the secured asset by sale or lease (other than in the "
  "ordinary course of business) without the secured creditor's prior written consent.\n\n"
  "Which of the statements given above is/are correct?",
  "1, 2 and 3",
  [("1 and 3 only", "s.13(8) redemption right (2016) treated as lost"),
   ("1 and 2 only", "s.13(13) restraint missed"),
   ("2 and 3 only", "NPA pre-condition of s.13(2) missed")],
  ["s.13(2): applies where the account is classified as an NPA.",
   "s.13(8) (2016): redemption until publication of auction/tender notice.",
   "s.13(13): no transfer of secured assets (other than ordinary course) without prior written consent."],
  "SARFAESI s.13(2), (8), (13)", "Post-2016 the redemption window closes at publication of the sale notice.",
  "statement", f"{SAR}, s.13 (as amended 2016)")

# S-6 consortium consent
out6 = {"Bank A": 84, "Bank B": 56, "Bank C": 40, "Bank D": 20}
san6 = {"Bank A": 90, "Bank B": 70, "Bank C": 40, "Bank D": 50}
ac_o = (out6["Bank A"] + out6["Bank C"]) / sum(out6.values())
ac_s = (san6["Bank A"] + san6["Bank C"]) / sum(san6.values())
assert ac_o >= 0.60 > ac_s
Q("S2", "L2",
  "A consortium financed Lumen Glass Ltd (₹ crore):\n\n| Lender | Sanctioned limit | Outstanding on record date |\n|---|---:|---:|\n"
  + "\n".join(f"| {k} | {san6[k]} | {out6[k]} |" for k in out6) +
  "\n\nBanks A and C agree to take measures under section 13(4); Banks B and D oppose. Under section 13(9):",
  f"Measures may be taken — consent holds {P2(ac_o)} of outstanding value",
  [(f"Measures barred — consent holds only {P2(ac_s)} of sanctioned limits", "sanctioned limits used instead of outstanding"),
   ("Measures barred — 75% of outstanding value is required", "pre-2016 threshold"),
   ("Measures barred — a majority in number of lenders is needed", "counting lenders instead of value")],
  [f"s.13(9) (as amended 2016): creditors representing not less than 60% in value of the amount outstanding as on a record date.",
   f"A + C = {out6['Bank A'] + out6['Bank C']} of {sum(out6.values())} = {P2(ac_o)} ≥ 60%."],
  "s.13(9): ≥60% by outstanding value", "Base is amount outstanding, not sanctioned limit.",
  "numerical", f"{SAR}, s.13(9) (as amended 2016)")

out7 = {"P": 110, "Q": 75, "R": 65, "S": 50}
san7 = {"P": 120, "Q": 70, "R": 90, "S": 60}
T7, S7 = sum(out7.values()), sum(san7.values())
ok_out = [k for k in "QRS" if out7["P"] + out7[k] >= 0.6 * T7]
ok_san = [k for k in "QRS" if san7["P"] + san7[k] >= 0.6 * S7]
ok_maj = [k for k in "QRS" if out7["P"] + out7[k] > 0.5 * T7]
ok_75 = [k for k in "QRS" if out7["P"] + out7[k] >= 0.75 * T7]
assert ok_out == ["Q"] and ok_san == ["R"] and ok_maj == ["Q", "R", "S"] and ok_75 == []
Q("S2", "L3",
  "Four lenders jointly financed Ferro Alloys Ltd (₹ crore):\n\n| Lender | Sanctioned limit | Outstanding on record date |\n|---|---:|---:|\n"
  + "\n".join(f"| {k} | {san7[k]} | {out7[k]} |" for k in out7) +
  "\n\nLender P wants to take possession of the secured assets under section 13(4). The consent of which single additional lender "
  "would, together with P, satisfy section 13(9)?",
  "Q only",
  [("R only", "60% tested on sanctioned limits"),
   ("Any one of Q, R or S", "simple majority (over 50%) by value applied"),
   ("None — two more lenders are needed", "pre-2016 75% threshold applied")],
  [f"60% of outstanding {T7} = {0.6*T7:.0f}.",
   f"P + Q = {out7['P'] + out7['Q']} ✓; P + R = {out7['P'] + out7['R']} ✗; P + S = {out7['P'] + out7['S']} ✗."],
  "s.13(9): consent ≥ 60% of outstanding value", "Rank lenders on outstanding, not sanction.",
  "numerical", f"{SAR}, s.13(9) (as amended 2016)")

a14 = date(2026, 3, 2)
Q("S2", "L2",
  f"A secured creditor's complete application under section 14, with the prescribed affidavit, is filed before the District Magistrate "
  f"on {D(a14)}. Using the maximum extension permitted, the outer limit for passing the order is:",
  D(a14 + timedelta(60)),
  [(D(a14 + timedelta(30)), "base 30 days taken as the outer limit"),
   (D(a14 + timedelta(45)), "45-day period of s.17 used"),
   (D(a14 + timedelta(90)), "30 + 60 days added")],
  ["s.14(1) second proviso (2016): CMM/DM to pass order within 30 days of the application.",
   "Third proviso: may extend for reasons recorded, but not beyond 60 days in aggregate.",
   f"{D(a14)} + 60 days = {D(a14 + timedelta(60))}."],
  "s.14: 30 days, aggregate not beyond 60 days", "The extension is capped at a TOTAL of 60 days.",
  "numerical", f"{SAR}, s.14(1) provisos (as amended 2013/2016)")

Q("S2", "L1",
  "To take possession of a secured asset with official assistance under section 14, the secured creditor applies to:",
  "The CMM or DM within whose jurisdiction the secured asset lies",
  [("The DRT having jurisdiction over the borrower's residence", "DRT's s.17 appellate role confused with s.14"),
   ("The High Court of the State where the borrower resides", "writ court confused with s.14 authority"),
   ("The NCLT bench where the borrower's office is registered", "IBC adjudicating authority confused with s.14")],
  ["s.14(1): Chief Metropolitan Magistrate or District Magistrate within whose jurisdiction the secured asset or documents are situated."],
  "SARFAESI s.14(1)", "Jurisdiction follows the ASSET, not the borrower.",
  "conceptual", f"{SAR}, s.14(1)")

Q("S3", "L1",
  "A borrower aggrieved by possession taken under section 13(4) may apply to the Debts Recovery Tribunal under section 17 within:",
  "45 days from the date on which the measure is taken",
  [("30 days from the date on which the measure is taken", "30-day DRAT appeal period of s.18"),
   ("60 days from the date on which the measure is taken", "60-day notice period of s.13(2)"),
   ("45 days from the date of the section 13(2) notice", "period counted from the wrong event")],
  ["s.17(1): application within 45 days from the date on which the s.13(4) measure was taken."],
  "SARFAESI s.17(1): 45 days", "The clock starts from the measure, not from the demand notice.",
  "conceptual", f"{SAR}, s.17(1)")

claim11, det11 = 9.60, 7.20
base11 = min(claim11, det11)
Q("S3", "L2",
  f"Secured creditors claimed ₹{claim11:.2f} crore from Arcadia Prints Ltd; the DRT determined the debt at ₹{det11:.2f} crore. For "
  "Arcadia's appeal under section 18, the lowest pre-deposit the DRAT can require after exercising its power of reduction is:",
  cr(0.25 * base11),
  [(cr(0.25 * claim11), "25% applied to the amount claimed, not the lesser"),
   (cr(0.50 * base11), "50% deposit without reduction"),
   (cr(0.75 * base11), "RDB Act s.21 75% rule applied")],
  [f"s.18(1) proviso: deposit 50% of the debt as claimed or as determined by DRT, whichever is less → 50% × {base11} = {0.5*base11:.2f}.",
   f"Second proviso: DRAT may reduce to not less than 25% → 25% × {base11} = {0.25*base11:.2f}."],
  "s.18: 50% of lower of claimed/determined, reducible to 25%", "Use the LOWER of claimed and determined.",
  "numerical", f"{SAR}, s.18(1) provisos")

pos12 = date(2026, 5, 4)
fil12 = date(2026, 6, 10)
def add_months(d, m):
    y, mo = d.year + (d.month - 1 + m) // 12, (d.month - 1 + m) % 12 + 1
    return date(y, mo, d.day)
Q("S3", "L3",
  f"The bank took possession of Rhea Plastics' factory under section 13(4) on {D(pos12)}. Rhea filed its section 17 application on "
  f"{D(fil12)}. The last date for filing the application, and the outer date by which the DRT should dispose of it using the "
  "maximum extension, are respectively:",
  f"{D(pos12 + timedelta(45))} and {D(add_months(fil12, 4))}",
  [(f"{D(pos12 + timedelta(45))} and {D(fil12 + timedelta(60))}", "extension to four months missed"),
   (f"{D(pos12 + timedelta(30))} and {D(add_months(fil12, 4))}", "30-day period used for filing"),
   (f"{D(pos12 + timedelta(45))} and {D(add_months(fil12, 6))}", "six-month DRAT norm used for disposal")],
  [f"s.17(1): 45 days from the measure → {D(pos12 + timedelta(45))}.",
   "s.17(5)–(6): dispose within 60 days of application; may extend with reasons, total not exceeding four months.",
   f"{D(fil12)} + 4 months = {D(add_months(fil12, 4))}."],
  "s.17(1) 45 days; s.17(5)/(6) 60 days extendable to 4 months", "The disposal clock runs from the date of the application.",
  "numerical", f"{SAR}, s.17(1), (5), (6)")

Q("S3", "L3",
  "**Assertion (A):** A borrower appealing to the DRAT under section 18 of the SARFAESI Act must first deposit 75% of the debt.\n\n"
  "**Reason (R):** Section 18 requires a deposit of 50% of the debt due as claimed by the secured creditors or as determined by the "
  "DRT, whichever is less.",
  AR["D"],
  [(AR["A"], "RDB Act s.21 rate carried over to SARFAESI"),
   (AR["B"], "Assertion treated as true"),
   (AR["C"], "s.18 50% rule rejected")],
  ["75% is the pre-deposit under s.21 of the RDB Act, not SARFAESI.",
   "s.18 prescribes 50% of the lesser of claimed and determined debt (reducible to 25%)."],
  "SARFAESI s.18 vs RDB s.21", "Keep the two pre-deposit regimes apart: 50/25 vs 75/50.",
  "assertion-reason", f"{SAR}, s.18; {RDB}, s.21")

Q("S4", "L1",
  "The SARFAESI Act does NOT apply to a security interest created in:",
  "Agricultural land",
  [("A residential flat", "mortgage of immovable property is covered"),
   ("Plant and machinery", "hypothecation of machinery is covered"),
   ("Book debts", "receivables are covered as financial assets")],
  ["s.31(i): the Act does not apply to any security interest created in agricultural land."],
  "SARFAESI s.31(i)", "Agricultural land is the classic exclusion.",
  "conceptual", f"{SAR}, s.31(i)")

acct = {"X": (50.0, 9.0), "Y": (80.0, 17.6)}
Z_fa = 0.9
pX, pY = acct["X"][1] / acct["X"][0], acct["Y"][1] / acct["Y"][0]
assert pX < 0.20 <= pY
Q("S4", "L3",
  "A bank holds security over three NPA accounts (₹ lakh):\n\n| Account | Principal + interest | Amount now due |\n|---|---:|---:|\n"
  f"| X | {acct['X'][0]:.2f} | {acct['X'][1]:.2f} |\n| Y | {acct['Y'][0]:.2f} | {acct['Y'][1]:.2f} |\n"
  f"| Z | {Z_fa:.2f} | {Z_fa:.2f} |\n\nFor Account Z, the security secures a financial asset of ₹{Z_fa:.2f} lakh. The bank can invoke "
  "the SARFAESI Act for:",
  "Account Y only",
  [("Accounts X and Y only", "20% exclusion of s.31(j) missed"),
   ("Accounts Y and Z only", "₹1 lakh exclusion of s.31(h) missed"),
   ("Accounts X, Y and Z", "both exclusions missed")],
  [f"s.31(j): not applicable where amount due is less than 20% of principal and interest — X: {P2(pX)} (excluded); Y: {P2(pY)} (covered).",
   "s.31(h): not applicable to security interest securing a financial asset not exceeding ₹1 lakh — Z excluded."],
  "SARFAESI s.31(h), (j)", "The 20% test compares amount due with principal + interest.",
  "numerical", f"{SAR}, s.31(h), (j)")

Q("S4", "L3",
  "Consider the following:\n\n1. A pledge of movables under section 172 of the Indian Contract Act, 1872\n"
  "2. A security interest in an aircraft\n3. A mortgage of a commercial building\n\n"
  "To which of the above does section 31 exclude the application of the SARFAESI Act?",
  "1 and 2 only",
  [("1, 2 and 3", "mortgage of building wrongly treated as excluded"),
   ("2 only", "pledge exclusion of s.31(b) missed"),
   ("1 only", "aircraft exclusion of s.31(c) missed")],
  ["s.31(b): pledge of movables under s.172 Contract Act.", "s.31(c): security interest in aircraft.",
   "A mortgage of a commercial building is squarely covered."],
  "SARFAESI s.31(b), (c)", "Hypothecation is covered; pledge is not.",
  "statement", f"{SAR}, s.31")

Q("S5", "L2",
  "After registration of security interests with the Central Registry (CERSAI) was made operational, what is the consequence under "
  "section 26D if a secured creditor has not registered its security interest?",
  "It cannot exercise enforcement rights under Chapter III",
  [("The security interest becomes void against the liquidator", "Companies Act s.77 charge rule confused"),
   ("It may enforce, but pays a fine for each day of default", "penalty provision confused with bar on enforcement"),
   ("It loses priority only against later registered creditors", "s.26C priority rule confused with s.26D bar")],
  ["s.26D (2016): no secured creditor shall be entitled to exercise the rights of enforcement of securities under Chapter III unless "
   "the security interest has been registered with the Central Registry."],
  "SARFAESI s.26D", "Registration is a pre-condition to SARFAESI enforcement.",
  "conceptual", f"{SAR}, s.26D (inserted 2016)")

Q("S5", "L3",
  "Consider the following statements about asset reconstruction companies (ARCs):\n\n"
  "1. An ARC must obtain a certificate of registration from the Reserve Bank of India under section 3 before commencing business.\n"
  "2. An ARC may issue security receipts to qualified buyers to raise funds for acquiring financial assets.\n"
  "3. As a measure of asset reconstruction, an ARC may take over the management of the borrower's business.\n\n"
  "Which of the statements given above is/are correct?",
  "1, 2 and 3",
  [("1 and 2 only", "s.9 management-takeover measure missed"),
   ("2 and 3 only", "RBI registration under s.3 missed"),
   ("1 and 3 only", "security-receipt route of s.7 missed")],
  ["s.3: registration with RBI.", "s.7: issue of security receipts to qualified buyers.",
   "s.9(1)(a): proper management of the borrower's business by change in or takeover of management."],
  "SARFAESI ss.3, 7, 9", "ARCs are RBI-regulated, not SEBI-regulated entities.",
  "statement", f"{SAR}, ss.3, 7, 9")

# ---- SARFAESI case set (L4 x4) ----
G2 = "ACTR-CASE-SAR-RIVANTA"
out_c = {"Kosi Bank": 72, "Lotus Bank": 48, "Mahi Bank": 36, "Narmada Bank": 24}
Tc = sum(out_c.values())
n2 = date(2026, 2, 5); r2 = date(2026, 2, 25)
claim_c, det_c = 180.0, 162.0
case_sar = ("**Case — Rivanta Foods Pvt Ltd (fictional)**\n\nRivanta's account with a four-bank consortium was classified as an NPA. "
            "Outstanding on the record date (₹ crore):\n\n| Lender | Outstanding |\n|---|---:|\n"
            + "\n".join(f"| {k} | {v} |" for k, v in out_c.items()) +
            f"\n\nSecurity: mortgage of the factory, hypothecation of stock, mortgage of a farm (agricultural land) and a pledge of listed "
            f"shares. The lead bank served a section 13(2) notice on {D(n2)}; Rivanta's representation reached it on {D(r2)}. Later the "
            f"consortium's claim of ₹{claim_c:.0f} crore was determined by the DRT at ₹{det_c:.0f} crore on Rivanta's section 17 application.")
km = (out_c["Kosi Bank"] + out_c["Mahi Bank"]) / Tc
assert abs(km - 0.60) < 1e-12
Q("S2", "L4", case_sar + "\n\nKosi Bank and Mahi Bank consent to action under section 13(4); Lotus and Narmada oppose. The consortium:",
  f"May act — consent of {P2(km)} is not less than 60%",
  [(f"Cannot act — consent of {P2(km)} does not exceed 60%", "'not less than' read as 'more than'"),
   (f"Cannot act — {P2(km)} is below the 75% required", "pre-2016 threshold"),
   ("Cannot act — only two of the four lenders consent", "counting by number")],
  [f"Consent = (72 + 36)/{Tc} = {P2(km)}.", "s.13(9): 'not less than 60% in value' — exactly 60% qualifies."],
  "s.13(9): ≥ 60%", "Exactly 60% is sufficient.", "case", f"{SAR}, s.13(9) (as amended 2016)", group=G2)

Q("S4", "L4", case_sar + "\n\nAgainst which of Rivanta's assets can the consortium proceed under the SARFAESI Act?",
  "The factory and the hypothecated stock only",
  [("The factory, the stock and the pledged shares only", "pledge exclusion of s.31(b) missed"),
   ("The factory, the stock and the farm only", "agricultural-land exclusion of s.31(i) missed"),
   ("The factory only", "hypothecated stock wrongly treated as a pledge")],
  ["s.31(b): pledge of movables excluded; s.31(i): agricultural land excluded.",
   "Mortgage (factory) and hypothecation (stock) are security interests covered by the Act."],
  "SARFAESI s.31(b), (i)", "Hypothecation ≠ pledge.", "case", f"{SAR}, s.31", group=G2)

b50 = 0.50 * min(claim_c, det_c)
Q("S3", "L4", case_sar + "\n\nThe DRT dismisses Rivanta's application and Rivanta appeals to the DRAT. The range within which the DRAT may fix the "
  "pre-deposit is:",
  f"{cr(0.25*min(claim_c, det_c))} to {cr(b50)}",
  [(f"{cr(0.25*claim_c)} to {cr(0.5*claim_c)}", "claimed amount used instead of the lesser determined amount"),
   (f"{cr(b50)} to {cr(0.75*det_c)}", "RDB Act 50%–75% band applied"),
   (f"{cr(b50)}, fixed with no power to reduce", "reduction power in s.18 second proviso missed")],
  [f"Lesser of claimed {claim_c:.0f} and determined {det_c:.0f} = {det_c:.0f}.",
   f"Standard deposit 50% = {b50:.2f}; reducible to not less than 25% = {0.25*det_c:.2f}."],
  "s.18: 25%–50% of lesser of claimed/determined", "Base is the LOWER figure.", "case", f"{SAR}, s.18", group=G2)

Q("S1", "L4", case_sar + "\n\nExcluding the first day in each case, the date on which the borrower's 60-day period under section 13(2) ends, and the last "
  "date for the lead bank to communicate reasons for rejecting the representation, are respectively:",
  f"{D(n2 + timedelta(60))} and {D(r2 + timedelta(15))}",
  [(f"{D(n2 + timedelta(60))} and {D(r2 + timedelta(7))}", "pre-2016 one-week reply period"),
   (f"{D(n2 + timedelta(45))} and {D(r2 + timedelta(15))}", "45-day period used for the notice"),
   (f"{D(r2 + timedelta(60))} and {D(r2 + timedelta(15))}", "60 days counted from the representation")],
  [f"s.13(2): {D(n2)} + 60 = {D(n2 + timedelta(60))}.", f"s.13(3A): {D(r2)} + 15 = {D(r2 + timedelta(15))}."],
  "s.13(2) 60 days; s.13(3A) 15 days", "The representation does not restart the 60-day clock.",
  "case", f"{SAR}, s.13(2), (3A) (as amended 2016)", group=G2)

# =====================================================================================
# RDB Act (20): L1 4 · L2 6 · L3 6 · L4 4
# =====================================================================================
Q("D1", "L1",
  "By notification of the Central Government (2018), the minimum amount of debt for which a bank may approach a Debts Recovery "
  "Tribunal under the RDB Act is:",
  "₹20 lakh",
  [("₹10 lakh", "figure in s.1(4) before the notification"),
   ("₹1 crore", "IBC default threshold confused"),
   ("₹1 lakh", "floor below which the threshold cannot be notified")],
  ["s.1(4): Act does not apply where debt is less than ₹10 lakh or such other amount, not less than ₹1 lakh, as notified.",
   "Notification of September 2018 raised it to ₹20 lakh."],
  "RDB s.1(4) (notification 06.09.2018)", "Below ₹20 lakh the bank goes to the civil court.",
  "conceptual", f"{RDB}, s.1(4) (notification S.O. 4312(E), 06.09.2018)")

pr2, in2 = 14.60, 6.10
Q("D1", "L2",
  f"A bank seeks to recover from Saanvi Traders a loan whose principal outstanding is ₹{pr2:.2f} lakh, with accrued interest of "
  f"₹{in2:.2f} lakh. Taking the notified threshold of ₹20 lakh, the proper forum is:",
  f"DRT — the debt of {lk(pr2 + in2)} meets the threshold",
  [(f"Civil court — principal of {lk(pr2)} is below ₹20 lakh", "interest excluded from 'debt'"),
   ("DRT — any debt above ₹10 lakh lies before the DRT", "pre-notification threshold relied on"),
   ("Civil court — the DRT hears claims of ₹1 crore and above", "IBC threshold confused")],
  ["s.2(g): 'debt' means any liability (inclusive of interest) claimed as due.",
   f"Debt = {pr2} + {in2} = {pr2 + in2:.2f} lakh ≥ 20 lakh → DRT."],
  "RDB s.2(g), s.1(4)", "Interest is part of the debt.", "numerical", f"{RDB}, ss.1(4), 2(g)")

Q("D3", "L1",
  "An appeal against an order of the DRT under section 20 lies to the DRAT within:",
  "45 days from receipt of a copy of the order",
  [("30 days from receipt of a copy of the order", "SARFAESI s.18 appeal period"),
   ("60 days from receipt of a copy of the order", "PMLA High Court appeal period"),
   ("45 days from the date of pronouncement", "period counted from the wrong event")],
  ["s.20(3): appeal within 45 days from the date on which a copy of the order is received (delay condonable for sufficient cause)."],
  "RDB s.20(3): 45 days", "Count from receipt of the copy.", "conceptual", f"{RDB}, s.20(3)")

det4, claim4 = 4.80, 5.60
Q("D3", "L2",
  f"A bank claimed ₹{claim4:.2f} crore; the DRT determined the debt at ₹{det4:.2f} crore. For the borrower's appeal, the lowest "
  "pre-deposit the DRAT may accept after exercising its power of reduction under section 21 is:",
  cr(0.50 * det4),
  [(cr(0.75 * det4), "75% deposit without reduction"),
   (cr(0.25 * det4), "SARFAESI 25% floor applied"),
   (cr(0.50 * claim4), "50% applied to the amount claimed")],
  [f"s.21: deposit 75% of the debt as determined by the DRT = {0.75*det4:.2f}.",
   f"Proviso (2016): DRAT may reduce to not less than 50% = {0.5*det4:.2f}."],
  "RDB s.21: 75% of determined debt, reducible to 50%", "The base is the amount determined by the DRT.",
  "numerical", f"{RDB}, s.21 (as amended 2016)")

Q("D2", "L2",
  "Under section 19(24), the DRT is to endeavour to dispose of an original application finally within:",
  "180 days from the date of receipt of the application",
  [("60 days from the date of receipt of the application", "SARFAESI s.17 disposal period"),
   ("330 days from the date of receipt of the application", "IBC outer limit confused"),
   ("6 months from service of summons on the defendant", "DRAT norm and wrong starting point")],
  ["s.19(24): Tribunal to endeavour to dispose of the application within 180 days of receipt."],
  "RDB s.19(24)", "The period is an endeavour, running from receipt.", "conceptual", f"{RDB}, s.19(24)")

sv6 = date(2026, 3, 9)
Q("D2", "L2",
  f"Summons in an original application is served on the defendant on {D(sv6)}. The defendant does not file a written statement within "
  "the normal period. If the Presiding Officer grants the maximum extension, the last date for filing it is:",
  D(sv6 + timedelta(45)),
  [(D(sv6 + timedelta(30)), "normal 30 days without extension"),
   (D(sv6 + timedelta(60)), "30 + 30 days assumed"),
   (D(sv6 + timedelta(90)), "CPC outer 90-day period applied")],
  ["s.19(5) (2016): written statement within 30 days of service of summons.",
   "Proviso: extension in exceptional cases, not exceeding 15 days → 45 days in all.",
   f"{D(sv6)} + 45 days = {D(sv6 + timedelta(45))}."],
  "RDB s.19(5): 30 + 15 days", "The CPC 90/120-day timelines do not govern the DRT.",
  "numerical", f"{RDB}, s.19(5) (as amended 2016)")

Q("D2", "L1",
  "As regards limitation for applications to the Debts Recovery Tribunal, the RDB Act provides that:",
  "The Limitation Act, 1963 applies, as far as may be",
  [("No limitation applies to claims by banks", "special-status assumption"),
   ("Applications lie within 45 days of the default", "appeal period confused with limitation"),
   ("A 12-year period applies to every bank claim", "mortgage-suit period generalised")],
  ["s.24: the provisions of the Limitation Act, 1963 shall, as far as may be, apply to an application made to a Tribunal."],
  "RDB s.24", "Ordinary limitation rules apply.", "conceptual", f"{RDB}, s.24")

Q("D1", "L3",
  "Consider the following statements on where a bank may file an original application under section 19:\n\n"
  "1. Before the DRT within whose jurisdiction the branch maintaining the account in which the debt is outstanding is located.\n"
  "2. Before the DRT within whose jurisdiction the defendant resides or carries on business.\n"
  "3. Only before the DRT within whose jurisdiction the bank's registered office is located.\n\n"
  "Which of the statements given above is/are correct?",
  "1 and 2 only",
  [("2 only", "2016 branch-based venue missed"),
   ("1, 2 and 3", "registered-office venue wrongly added"),
   ("1 and 3 only", "defendant-based venue missed")],
  ["s.19(1)(a) (2016): the branch or office maintaining the account.",
   "s.19(1)(b)–(c): where the defendant resides/works/carries on business, or where the cause of action arises.",
   "There is no rule confining filing to the bank's registered office."],
  "RDB s.19(1)", "The 2016 amendment added the account-branch venue.", "statement", f"{RDB}, s.19(1) (as amended 2016)")

Q("D4", "L3",
  "Consider the following modes of recovery available to a Recovery Officer under section 25 on a recovery certificate:\n\n"
  "1. Attachment and sale of the movable or immovable property of the defendant\n"
  "2. Arrest of the defendant and his detention in prison\n"
  "3. Appointing a receiver for the management of the defendant's properties\n\n"
  "Which of the above is/are available?",
  "1, 2 and 3",
  [("1 and 3 only", "arrest and detention (s.25(b)) missed"),
   ("1 only", "only attachment and sale recognised"),
   ("1 and 2 only", "receiver (s.25(c)) missed")],
  ["s.25: (a) attachment and sale of movable/immovable property; (b) arrest and detention; (c) appointing a receiver.",
   "s.28 adds other modes (e.g. garnishee-type recovery from debtors of the defendant)."],
  "RDB s.25(a)–(c)", "All three are statutory modes.", "statement", f"{RDB}, s.25")

Q("D4", "L2",
  "A defendant aggrieved by an order of the Recovery Officer made in execution of a recovery certificate may appeal:",
  "To the DRT within 30 days of the order",
  [("To the DRAT within 45 days of the order", "s.20 route against DRT orders confused"),
   ("To the High Court within 60 days of the order", "PMLA s.42 route confused"),
   ("To the DRT within 45 days of the order", "s.20 period applied to s.30 appeal")],
  ["s.30(1): appeal against a Recovery Officer's order to the Tribunal (DRT) within 30 days of the order."],
  "RDB s.30", "Recovery Officer → DRT; DRT → DRAT.", "conceptual", f"{RDB}, s.30")

Q("D3", "L3",
  "**Assertion (A):** The DRAT may waive the pre-deposit entirely for a borrower facing genuine financial hardship.\n\n"
  "**Reason (R):** Under section 21, the DRAT may, for reasons recorded in writing, reduce the deposit to not less than 50% of the "
  "debt determined.",
  AR["D"],
  [(AR["A"], "reduction floor read as a waiver power"),
   (AR["B"], "Assertion treated as true"),
   (AR["C"], "2016 reduction proviso rejected")],
  ["Pre-2016 s.21 allowed waiver or reduction; the 2016 amendment removed waiver and set a 50% floor.",
   "So A is false; R correctly states the current proviso."],
  "RDB s.21 proviso (2016)", "No full waiver after 2016.", "assertion-reason", f"{RDB}, s.21 (as amended 2016)")

# D-12 recovery arithmetic (interest given as data)
dec, rate, yrs, costs, sale = 2.40, 0.11, 1.5, 0.04, 3.10
due = dec + dec * rate * yrs + costs
surplus = sale - due
assert abs(due - 2.836) < 1e-9
comp_due = dec * (1 + rate) ** yrs + costs
Q("D4", "L3",
  f"A recovery certificate for ₹{dec:.2f} crore directs simple interest at {rate*100:.0f}% p.a. from 1 April 2025 until realisation, plus "
  f"costs of ₹{costs:.2f} crore. On 30 September 2026 the Recovery Officer sells the defendant's attached property for ₹{sale:.2f} crore "
  "(no other claimants). The surplus refundable to the defendant is:",
  cr(surplus, 3),
  [(cr(sale - comp_due, 3), "interest compounded annually instead of simple"),
   (cr(sale - dec - dec * rate * yrs, 3), "costs omitted"),
   (cr(sale - dec - dec * rate - costs, 3), "interest for only one year")],
  [f"Interest = {dec} × {rate} × {yrs} = {dec*rate*yrs:.3f}.",
   f"Amount due = {dec} + {dec*rate*yrs:.3f} + {costs} = {due:.3f}.",
   f"Surplus = {sale} − {due:.3f} = {surplus:.3f} (refunded to the defendant)."],
  "Due = certificate + simple interest + costs; surplus = sale − due",
  "1 April 2025 to 30 September 2026 is 18 months.", "numerical", f"{RDB}, ss.19(20)/(22), 25, 29")

Q("D2", "L3",
  "Consider the following statements about proceedings before the DRT:\n\n"
  "1. The defendant may set up a counter-claim against the applicant bank, which the DRT decides along with the application.\n"
  "2. The DRT is bound to follow the procedure in the Code of Civil Procedure, 1908 in all respects.\n"
  "3. The DRT may pass an interim order restraining the defendant from transferring or disposing of his assets.\n\n"
  "Which of the statements given above is/are correct?",
  "1 and 3 only",
  [("1, 2 and 3", "s.22(1) freedom from CPC missed"),
   ("3 only", "counter-claim right of s.19(8) missed"),
   ("2 and 3 only", "CPC wrongly made binding; counter-claim missed")],
  ["s.19(8): counter-claim permitted, with effect of a cross-suit.",
   "s.22(1): Tribunal not bound by CPC; guided by principles of natural justice.",
   "s.19(12)–(13): interim orders including restraint on transfer."],
  "RDB ss.19(8), 19(13), 22(1)", "The DRT regulates its own procedure.", "statement", f"{RDB}, ss.19, 22")

Q("D1", "L1",
  "To be appointed Presiding Officer of a Debts Recovery Tribunal, a person must be, or have been, or be qualified to be:",
  "A District Judge",
  [("A Judge of a High Court", "DRAT Chairperson qualification"),
   ("A Judicial Member of the NCLT", "IBC tribunal qualification confused"),
   ("A Magistrate of the first class", "criminal court qualification confused")],
  ["s.5(1): Presiding Officer of a DRT — is, has been, or is qualified to be a District Judge.",
   "s.10: DRAT Chairperson — is, has been, or is qualified to be a High Court Judge."],
  "RDB ss.5, 10", "DRT ~ District Judge; DRAT ~ High Court Judge.", "conceptual", f"{RDB}, ss.5, 10")

op15, cp15 = date(2026, 2, 10), date(2026, 2, 17)
Q("D3", "L2",
  f"The DRT pronounced its final order in Bank of Tarai v. Hemant Castings on {D(op15)}; the defendant received the certified copy on "
  f"{D(cp15)}. Without seeking condonation, the last date for the appeal to the DRAT is:",
  D(cp15 + timedelta(45)),
  [(D(op15 + timedelta(45)), "counted from pronouncement"),
   (D(cp15 + timedelta(30)), "30-day SARFAESI s.18 period applied"),
   (D(cp15 + timedelta(60)), "60-day period assumed")],
  [f"s.20(3): 45 days from receipt of copy → {D(cp15)} + 45 = {D(cp15 + timedelta(45))}."],
  "RDB s.20(3)", "Receipt of copy, not pronouncement, starts the clock.", "numerical", f"{RDB}, s.20(3)")

Q("D1", "L3",
  "Consider the following statements:\n\n"
  "1. The DRT is the Adjudicating Authority under Part III of the IBC for insolvency of individuals and partnership firms.\n"
  "2. An appeal from an order of the DRT acting under Part III of the IBC lies to the DRAT.\n"
  "3. Insolvency proceedings against a personal guarantor of a corporate debtor under CIRP lie before the NCLT, not the DRT.\n\n"
  "Which of the statements given above is/are correct?",
  "1, 2 and 3",
  [("1 and 2 only", "s.60(2) IBC guarantor rule missed"),
   ("1 only", "IBC s.181 appeal route missed"),
   ("2 and 3 only", "IBC s.179 DRT role missed")],
  ["IBC s.179: DRT is the AA for individuals and partnership firms.", "IBC s.181: appeal to DRAT.",
   "IBC s.60(2): proceedings against a personal guarantor of a CD under CIRP go to the NCLT."],
  "IBC ss.60(2), 179, 181", "Guarantor follows the corporate debtor's forum.", "statement",
  f"{RDB}, s.17; {IBC}, ss.60(2), 179, 181")

# ---- RDB case set (L4 x4) ----
G3 = "ACTR-CASE-RDB-NIRVIK"
pr_n, in_n, pen_n = 128.0, 36.0, 4.0   # ₹ lakh
det_n = 1.52   # ₹ crore determined
ord_n, rcv_n = date(2026, 7, 14), date(2026, 7, 21)
case_rdb = ("**Case — Nirvik Engineering Ltd (fictional)**\n\nPrayag Bank's claim against Nirvik (₹ lakh): principal "
            f"{pr_n:.2f}, interest {in_n:.2f}, penal charges {pen_n:.2f}. Nirvik's factory is mortgaged to the bank. Prayag filed an original "
            f"application before the DRT within whose jurisdiction its lending branch maintains Nirvik's account. The DRT determined the debt at "
            f"₹{det_n:.2f} crore by an order pronounced on {D(ord_n)}; Nirvik received the copy on {D(rcv_n)}.")
claim_n = (pr_n + in_n + pen_n) / 100
Q("D3", "L4", case_rdb + "\n\nNirvik wishes to appeal. The standard pre-deposit and the lowest deposit after reduction under section 21 are respectively:",
  f"{cr(0.75*det_n)} and {cr(0.50*det_n)}",
  [(f"{cr(0.75*claim_n)} and {cr(0.50*claim_n)}", "claimed amount used instead of determined debt"),
   (f"{cr(0.50*det_n)} and {cr(0.25*det_n)}", "SARFAESI s.18 band applied"),
   (f"{cr(0.75*det_n)} and nil (full waiver)", "pre-2016 waiver power assumed")],
  [f"Claim = {pr_n + in_n + pen_n:.0f} lakh = ₹{claim_n:.2f} crore; determined = ₹{det_n:.2f} crore.",
   f"75% × {det_n} = {0.75*det_n:.2f}; floor 50% × {det_n} = {0.5*det_n:.2f}."],
  "RDB s.21: 75% of determined, reducible to 50%", "Base is the DRT-determined debt.", "case",
  f"{RDB}, s.21 (as amended 2016)", group=G3)

Q("D3", "L4", case_rdb + "\n\nThe last date for Nirvik's appeal to the DRAT (without condonation) is:",
  D(rcv_n + timedelta(45)),
  [(D(ord_n + timedelta(45)), "counted from pronouncement"),
   (D(rcv_n + timedelta(30)), "SARFAESI 30-day period applied"),
   (D(rcv_n + timedelta(60)), "60-day period assumed")],
  [f"s.20(3): {D(rcv_n)} + 45 days = {D(rcv_n + timedelta(45))}."],
  "RDB s.20(3)", "Count from receipt of the copy.", "case", f"{RDB}, s.20(3)", group=G3)

Q("D1", "L4", case_rdb + "\n\nNirvik objects that (i) the DRT lacks pecuniary jurisdiction and (ii) the application should have been filed where Nirvik's "
  "registered office is. Taking the notified ₹20 lakh threshold, the objections are:",
  "Both untenable — debt exceeds ₹20 lakh; branch venue is valid",
  [("Only (ii) valid — filing must follow the defendant's office", "s.19(1)(a) branch venue (2016) missed"),
   ("Only (i) valid — the DRT hears only claims of ₹1 crore or more", "IBC threshold confused with RDB threshold"),
   ("Both valid — penal charges excluded and venue is improper", "debt narrowed and branch venue missed")],
  [f"Debt (incl. interest, s.2(g)) = ₹{pr_n + in_n + pen_n:.0f} lakh ≫ ₹20 lakh.",
   "s.19(1)(a): application may be filed where the branch maintaining the account is located."],
  "RDB ss.1(4), 2(g), 19(1)", "Venue options are alternative, not exclusive.", "case", f"{RDB}, ss.1(4), 19(1)", group=G3)

Q("D2", "L4", case_rdb + "\n\nWhile the original application is pending, Prayag Bank proposes to take possession of the mortgaged factory under "
  "section 13(4) of the SARFAESI Act. Which is correct?",
  "It may do so, as SARFAESI operates in addition to the RDB Act",
  [("It must first withdraw the original application before the DRT", "election-of-remedies assumed"),
   ("It may do so only with the DRT's prior leave in the pending case", "leave requirement invented"),
   ("It cannot, as a pending application bars all parallel measures", "s.37 SARFAESI missed")],
  ["SARFAESI s.37: its provisions are in addition to, and not in derogation of, the RDB Act.",
   "Parallel recourse was upheld by the Supreme Court (Mardia Chemicals, 2004; later decisions)."],
  "SARFAESI s.37", "The remedies are cumulative.", "case", f"{SAR}, ss.35, 37; {RDB}, s.19", group=G3)

# =====================================================================================
# PMLA (22): L1 4 · L2 7 · L3 7 · L4 4
# =====================================================================================
Q("P1", "L1",
  "The punishment for money laundering under section 4 of the PMLA (other than NDPS-linked cases) is:",
  "Rigorous imprisonment of 3 to 7 years, and fine",
  [("Rigorous imprisonment of 1 to 5 years, and fine", "understated range"),
   ("Rigorous imprisonment of 7 to 10 years, and fine", "NDPS ceiling used as the floor"),
   ("Rigorous imprisonment of 3 to 10 years, and fine", "NDPS ceiling applied to all cases")],
  ["s.4: rigorous imprisonment not less than 3 years, extendable to 7 years, and fine.",
   "Proviso: up to 10 years where proceeds relate to an NDPS offence."],
  "PMLA s.4", "The 10-year ceiling is NDPS-specific.", "conceptual", f"{PML}, s.4")

Q("P1", "L2",
  "Proceeds laundered by Mr. V were derived from an offence under the Narcotic Drugs and Psychotropic Substances Act, 1985 listed in the "
  "Schedule. The maximum term of rigorous imprisonment he faces under section 4 of the PMLA is:",
  "10 years",
  [("7 years", "general ceiling applied; NDPS proviso missed"),
   ("14 years", "confused with other special-statute ceilings"),
   ("Imprisonment for life", "NDPS Act's own punishment confused with PMLA's")],
  ["s.4 proviso: where proceeds of crime relate to an NDPS offence, the maximum is 10 years (minimum still 3 years)."],
  "PMLA s.4 proviso", "Only the ceiling changes.", "conceptual", f"{PML}, s.4 proviso")

Q("P1", "L3",
  "Consider the following statements:\n\n"
  "1. The offence under section 3 covers concealment, possession, acquisition or use of proceeds of crime and projecting or claiming "
  "them as untainted property.\n"
  "2. Money laundering is a continuing activity so long as a person is enjoying the proceeds of crime in any manner.\n"
  "3. The fine under section 4 is capped at ₹5 lakh.\n\nWhich of the statements given above is/are correct?",
  "1 and 2 only",
  [("1, 2 and 3", "pre-2013 ₹5 lakh fine cap assumed"),
   ("1 only", "2019 Explanation on continuing offence missed"),
   ("2 and 3 only", "s.3 activities list missed; old fine cap assumed")],
  ["s.3 and its Explanation (2019): the listed processes/activities; continuing activity while proceeds are enjoyed.",
   "The ₹5 lakh fine cap was removed by the PML (Amendment) Act, 2012; fine is now unlimited."],
  "PMLA ss.3, 4", "No upper limit on fine now.", "statement", f"{PML}, ss.3 (Explanation 2019), 4 (as amended 2012)")

Q("P2", "L1",
  "An offence in Part B of the Schedule to the PMLA becomes a 'scheduled offence' only if the total value involved is:",
  "₹1 crore or more",
  [("₹30 lakh or more", "pre-2015 threshold"),
   ("₹50 lakh or more", "wrong threshold"),
   ("₹10 lakh or more", "CTR cash threshold confused")],
  ["s.2(1)(y)(ii): Part B offences are scheduled offences if the total value involved is ₹1 crore or more (Finance Act, 2015)."],
  "PMLA s.2(1)(y)(ii)", "₹30 lakh was the older figure.", "conceptual", f"{PML}, s.2(1)(y) (as amended by Finance Act, 2015)")

Q("P2", "L2",
  "Fenwick Exports made a false declaration under section 132 of the Customs Act, 1962 (a Part B offence); the total value involved is "
  "₹85 lakh. For PMLA purposes:",
  "It is not a scheduled offence — value is below ₹1 crore",
  [("It is a scheduled offence — value exceeds ₹30 lakh", "pre-2015 threshold"),
   ("It is a scheduled offence — Part B offences need no threshold", "Part A rule applied to Part B"),
   ("It is not a scheduled offence — customs offences are unlisted", "s.132 Customs Act wrongly treated as outside the Schedule")],
  ["Part B contains s.132 Customs Act; it becomes a scheduled offence only if value ≥ ₹1 crore (s.2(1)(y)(ii)).",
   "₹85 lakh < ₹1 crore → not a scheduled offence."],
  "PMLA s.2(1)(y)(ii); Schedule Part B", "Part A has no value threshold; Part B does.", "conceptual", f"{PML}, s.2(1)(y), Schedule Part B")

decl = [38, 29, 41]
tot_d = sum(decl)
assert tot_d == 108
Q("P2", "L3",
  f"Over one year, Orlan Traders made three false declarations under section 132 of the Customs Act, 1962 involving ₹{decl[0]} lakh, "
  f"₹{decl[1]} lakh and ₹{decl[2]} lakh. Treating these as offences whose total value is aggregated, for PMLA purposes the conduct is:",
  f"Scheduled — aggregate {lk(tot_d)} meets the ₹1 crore test",
  [("Not scheduled — no single declaration reaches ₹1 crore", "'total value involved' read per offence"),
   ("Scheduled — two declarations exceed the ₹30 lakh threshold", "pre-2015 threshold per declaration"),
   ("Not scheduled — Part B covers only Part A-linked customs cases", "confused description of Part B")],
  [f"Total value = {' + '.join(map(str, decl))} = {tot_d} lakh = ₹1.08 crore.",
   "s.2(1)(y)(ii) uses 'total value involved in such offences' — ≥ ₹1 crore → scheduled."],
  "PMLA s.2(1)(y)(ii): total value ≥ ₹1 crore", "The test is on the TOTAL value.", "numerical", f"{PML}, s.2(1)(y)(ii)")

Q("P2", "L2",
  "Proceeds of a scheduled offence committed by Mr. K were transferred abroad and cannot be traced. Under section 2(1)(u) of the PMLA:",
  "Property of equivalent value held in India can be proceeds of crime",
  [("Only property directly derived from the offence can be attached", "value-based limb of s.2(1)(u) missed"),
   ("Proceeds taken abroad fall outside the PMLA entirely", "extra-territorial limb (2015) missed"),
   ("Only property acquired after the FIR is registered is covered", "time limit invented")],
  ["s.2(1)(u): property derived directly or indirectly from criminal activity relating to a scheduled offence, or the value of any "
   "such property; if taken or held outside India, property equivalent in value held within the country or abroad."],
  "PMLA s.2(1)(u) (as amended 2015/2019)", "'Value' of the proceeds is covered, not just the tainted asset.",
  "conceptual", f"{PML}, s.2(1)(u) (as amended by Finance Acts 2015, 2019)")

Q("P3", "L1",
  "Under section 12 of the PMLA, a reporting entity must maintain the record of every transaction for a period of:",
  "5 years from the date of the transaction",
  [("10 years from the date of the transaction", "pre-2013 period"),
   ("8 years from the date of the transaction", "Companies Act books-of-account period confused"),
   ("5 years from the date of opening the account", "wrong starting event")],
  ["s.12(3) (as amended 2012): records of transactions maintained for 5 years from the date of transaction."],
  "PMLA s.12(3)", "The 10-year period was reduced to 5 by the 2012 amendment.", "conceptual", f"{PML}, s.12(3) (as amended 2012)")

open9, close9, last9 = date(2012, 6, 1), date(2021, 9, 30), date(2021, 8, 14)
Q("P3", "L2",
  f"Mr. D opened a bank account on {D(open9)}, made his last transaction on {D(last9)} and closed the account on {D(close9)}. Under "
  "section 12(4), the bank must retain his identity (KYC) records at least until:",
  D(date(close9.year + 5, close9.month, close9.day)),
  [(D(date(last9.year + 5, last9.month, last9.day)), "period counted from the last transaction"),
   (D(date(open9.year + 5, open9.month, open9.day)), "period counted from account opening"),
   (D(date(close9.year + 10, close9.month, close9.day)), "pre-2013 10-year period")],
  ["s.12(4): identity records maintained for 5 years after the business relationship has ended or the account has been closed, "
   "whichever is later.", f"{D(close9)} + 5 years."],
  "PMLA s.12(4)", "Transaction records run from the transaction; identity records from closure.",
  "numerical", f"{PML}, s.12(4)")

cash = [("Deposit, 3 Mar (single)", 11.0, None), ("Withdrawal, 9 Mar (single)", 10.0, None),
        ("Deposit, 12 Mar", 4.2, "S"), ("Deposit, 19 Mar", 3.5, "S"), ("Deposit, 27 Mar", 2.8, "S")]
series = sum(a for _, a, g in cash if g == "S")
assert series > 10 and cash[1][1] == 10.0
Q("P3", "L3",
  "Cash transactions in a customer's account at Uday Bank during March 2026 (₹ lakh); the three deposits marked 'S' are integrally "
  "connected:\n\n| Transaction | Amount | Series |\n|---|---:|:---:|\n"
  + "\n".join(f"| {t} | {a:.2f} | {g or '—'} |" for t, a, g in cash) +
  "\n\nUnder the PML (Maintenance of Records) Rules, 2005, which transactions go into the cash transaction report, and by when?",
  "The ₹11 lakh deposit and the 'S' series — by 15 April 2026",
  [("The ₹11 lakh deposit and ₹10 lakh withdrawal — by 15 April 2026", "'more than ₹10 lakh' read as '₹10 lakh or more'; series missed"),
   ("The ₹11 lakh deposit only — within 7 working days", "series aggregation missed; STR timeline applied"),
   ("All five transactions — by 15 April 2026", "every cash transaction treated as reportable")],
  ["Rule 3: cash transactions of more than ₹10 lakh, and integrally connected series individually below ₹10 lakh whose monthly "
   f"aggregate exceeds ₹10 lakh (here {series:.2f}).",
   "₹10.00 lakh is not 'more than' ₹10 lakh.", "Rule 8: CTR by the 15th of the succeeding month (STRs: within 7 working days)."],
  "PML Rules r.3(1)(A)–(B), r.8", "Threshold is 'more than' ₹10 lakh.", "numerical",
  f"{PML}, s.12; PML (Maintenance of Records) Rules, 2005, rr.3, 8")

nfail = 6
Q("P3", "L2",
  f"The Director, FIU-IND finds that a reporting entity committed {nfail} separate failures to comply with its obligations under "
  "Chapter IV. The range of fine that may be imposed under section 13(2)(d) is:",
  f"{R(10000*nfail)} to {R(100000*nfail)}",
  [(f"{R(10000)} to {R(100000)}", "per-failure range not multiplied"),
   (f"{R(10000)} to {R(100000*nfail)}", "minimum not applied per failure"),
   (f"{R(100000*nfail)} to {R(1000000*nfail)}", "limits misread as ₹1 lakh and ₹10 lakh")],
  ["s.13(2)(d): monetary penalty not less than ₹10,000, extendable to ₹1 lakh, for each failure.",
   f"× {nfail} failures → {R(10000*nfail)} to {R(100000*nfail)}."],
  "PMLA s.13(2)(d)", "The range applies to EACH failure.", "numerical", f"{PML}, s.13(2)(d)")

Q("P3", "L1",
  "The Financial Intelligence Unit–India (FIU-IND), the central agency receiving cash and suspicious transaction reports, functions under:",
  "The Department of Revenue, Ministry of Finance",
  [("The Reserve Bank of India", "banking regulator confused with FIU"),
   ("The Directorate of Enforcement", "investigating agency confused with FIU"),
   ("The Securities and Exchange Board of India", "market regulator confused with FIU")],
  ["FIU-IND (set up 2004) reports to the Economic Intelligence Council; administratively under the Department of Revenue, MoF.",
   "The Director, FIU-IND exercises powers under ss.12–13."],
  "PMLA ss.12–13; Govt OM 2004", "ED investigates; FIU-IND receives and analyses reports.", "conceptual", f"{PML}, ss.12, 13")

pa = date(2026, 1, 16)
Q("P4", "L3",
  f"The Deputy Director, ED provisionally attaches property of Mr. H under section 5 on {D(pa)}. The last date for filing the "
  "complaint before the Adjudicating Authority, and the date on which the attachment lapses if not confirmed, are respectively:",
  f"{D(pa + timedelta(30))} and {D(pa + timedelta(180))}",
  [(f"{D(pa + timedelta(30))} and {D(pa + timedelta(150))}", "attachment period taken as 150 days"),
   (f"{D(pa + timedelta(45))} and {D(pa + timedelta(180))}", "45-day appeal period used for complaint"),
   (f"{D(pa + timedelta(30))} and {D(pa + timedelta(365))}", "s.8(3) 365-day period used for provisional attachment")],
  ["s.5(1): provisional attachment valid for up to 180 days from the date of the order.",
   "s.5(5): complaint before the Adjudicating Authority within 30 days of attachment.",
   f"{D(pa)} + 30 = {D(pa + timedelta(30))}; + 180 = {D(pa + timedelta(180))}."],
  "PMLA s.5(1): 180 days; s.5(5): 30 days", "Confirmation under s.8 must come within the 180 days.",
  "numerical", f"{PML}, s.5(1), (5)")

Q("P4", "L3",
  "Consider the following statements on attachment under the PMLA:\n\n"
  "1. Provisional attachment may be ordered by the Director or an officer not below the rank of Deputy Director authorised by him.\n"
  "2. A provisional attachment order ceases to have effect after 180 days unless confirmed earlier by the Adjudicating Authority.\n"
  "3. A person interested in the enjoyment of attached immovable property cannot continue to enjoy it during provisional attachment.\n\n"
  "Which of the statements given above is/are correct?",
  "1 and 2 only",
  [("1, 2 and 3", "s.5(4) enjoyment saving missed"),
   ("2 and 3 only", "officer rank in s.5(1) missed"),
   ("1 only", "180-day lapse rule missed")],
  ["s.5(1): Director or officer not below Deputy Director; up to 180 days.",
   "s.5(4): nothing in the section prevents the person interested from enjoying the immovable property attached."],
  "PMLA s.5(1), (4)", "Attachment is not dispossession.", "statement", f"{PML}, s.5")

aa = date(2026, 8, 3)
Q("P5", "L2",
  f"The Adjudicating Authority confirms an attachment; the aggrieved person receives the order on {D(aa)}. The last date for appeal to "
  "the Appellate Tribunal under section 26 (without condonation) is:",
  D(aa + timedelta(45)),
  [(D(aa + timedelta(30)), "30-day period assumed"),
   (D(aa + timedelta(60)), "s.42 High Court period applied"),
   (D(aa + timedelta(90)), "90-day period assumed")],
  ["s.26(3): appeal within 45 days from receipt of the copy of the order.", f"{D(aa)} + 45 = {D(aa + timedelta(45))}."],
  "PMLA s.26(3)", "45 days to the Tribunal; 60 days onward to the High Court.", "numerical", f"{PML}, s.26(3)")

Q("P5", "L3",
  "Consider the following statements on bail under section 45 of the PMLA:\n\n"
  "1. The Public Prosecutor must be given an opportunity to oppose, and where he opposes, the court must be satisfied that there are "
  "reasonable grounds for believing the accused is not guilty and is not likely to commit an offence while on bail.\n"
  "2. A woman accused may be released on bail if the Special Court so directs, without the twin conditions.\n"
  "3. An accused of money laundering of a sum less than ₹1 crore may be released on bail if the Special Court so directs.\n\n"
  "Which of the statements given above is/are correct?",
  "1, 2 and 3",
  [("1 and 2 only", "sub-₹1 crore proviso missed"),
   ("1 only", "both provisos to s.45(1) missed"),
   ("1 and 3 only", "woman/minor/sick proviso missed")],
  ["s.45(1): twin conditions.", "First proviso: person under 16, woman, sick or infirm may be released if the Special Court directs.",
   "Also: a person accused of laundering less than ₹1 crore, alone or with co-accused, may be released if the Special Court directs."],
  "PMLA s.45(1) and provisos", "The ₹1 crore limit counts the sum laundered alone OR with co-accused.",
  "statement", f"{PML}, s.45 (as amended 2018; upheld in Vijay Madanlal Choudhary, 2022)")

Q("P5", "L2",
  "During a PMLA investigation, the ED finds material indicating evasion of GST by the accused. Under section 66(2), the Director:",
  "Shall share the information with the concerned agency",
  [("Must itself prosecute the GST offence before the Special Court", "ED's jurisdiction over other laws assumed"),
   ("Must keep it confidential as it arose in a PMLA probe", "confidentiality overrides s.66 assumed"),
   ("May act only after the GST offence enters the Schedule", "scheduled-offence rule confused with information sharing")],
  ["s.66(2): where the Director has reason to believe, on the basis of information in his possession, that a provision of any other "
   "law has been contravened, he shall share the information with the concerned agency for necessary action."],
  "PMLA s.66(2)", "Information sharing ≠ prosecution.", "conceptual", f"{PML}, s.66(2)")

Q("P5", "L3",
  "**Assertion (A):** An Assistant Director of the ED, authorised in this behalf, may arrest a person under section 19 if, on the basis "
  "of material in his possession, he has reason to believe (recorded in writing) that the person is guilty of money laundering.\n\n"
  "**Reason (R):** Section 19 confers the power of arrest on the Director, Deputy Director, Assistant Director or any other officer "
  "authorised by the Central Government by general or special order.",
  AR["A"],
  [(AR["B"], "R not recognised as the source of the power in A"),
   (AR["C"], "power of arrest of officers under s.19 denied"),
   (AR["D"], "Assistant Director wrongly excluded")],
  ["s.19(1): Director, Deputy Director, Assistant Director or other authorised officer may arrest on reasons to believe recorded in writing.",
   "The arrested person must be informed of the grounds (in writing — Pankaj Bansal, 2023) and produced before the court within 24 hours.",
   "R is the very source of the power asserted in A."],
  "PMLA s.19", "Grounds of arrest must be communicated.", "assertion-reason", f"{PML}, s.19")

# ---- PMLA case set (L4 x4) ----
G4 = "ACTR-CASE-PMLA-SARVIK"
pa4 = date(2026, 3, 9)
at4 = date(2026, 10, 12)
case_pml = ("**Case — Sarvik Infra Pvt Ltd (fictional)**\n\nThe police registered an FIR for cheating (a Part A scheduled offence) against Sarvik's "
            "managing director Mr. A and CFO Mr. B. The ED alleges that ₹1.40 crore of proceeds was jointly laundered by them, of which ₹72 lakh "
            f"passed through Mr. B's accounts. On {D(pa4)} the Deputy Director provisionally attached Mr. B's flat under section 5. "
            f"The Adjudicating Authority later confirmed the attachment; the Appellate Tribunal dismissed Mr. B's appeal and its order was "
            f"communicated to her on {D(at4)}.")
Q("P4", "L4", case_pml + "\n\nThe last date for the ED's complaint before the Adjudicating Authority, and the date on which the attachment would lapse "
  "without confirmation, are respectively:",
  f"{D(pa4 + timedelta(30))} and {D(pa4 + timedelta(180))}",
  [(f"{D(pa4 + timedelta(30))} and {D(pa4 + timedelta(90))}", "90-day attachment period assumed"),
   (f"{D(pa4 + timedelta(60))} and {D(pa4 + timedelta(180))}", "60 days assumed for the complaint"),
   (f"{D(pa4 + timedelta(45))} and {D(pa4 + timedelta(180))}", "45-day appeal period used for complaint")],
  [f"s.5(5): 30 days → {D(pa4 + timedelta(30))}.", f"s.5(1): 180 days → {D(pa4 + timedelta(180))}."],
  "PMLA s.5(1), (5)", "Both periods run from the attachment order.", "case", f"{PML}, s.5", group=G4)

Q("P5", "L4", case_pml + "\n\nMr. B (aged 52, in good health) seeks bail relying on the ₹1 crore proviso to section 45(1). "
  "His claim:",
  "Fails — ₹1.40 crore was laundered jointly with the co-accused",
  [("Succeeds — only ₹72 lakh passed through his accounts", "'alone or with other co-accused' missed"),
   ("Succeeds — the twin conditions never apply to economic offences", "s.45 scope misread"),
   ("Fails — the ₹1 crore proviso was struck down by the Supreme Court", "s.45 validity (Vijay Madanlal, 2022) misstated")],
  ["s.45(1) proviso: relief where the accused is charged with laundering a sum less than ₹1 crore, 'either alone or with other co-accused'.",
   "Joint sum ₹1.40 crore ≥ ₹1 crore → proviso unavailable; twin conditions apply (no age/gender/sickness proviso applies)."],
  "PMLA s.45(1) proviso", "Aggregate the sum laundered with co-accused.", "case", f"{PML}, s.45", group=G4)

Q("P1", "L4", case_pml + "\n\nIf Mr. B is convicted under section 4, the permissible punishment is:",
  "3 to 7 years' rigorous imprisonment and fine without upper limit",
  [("3 to 10 years' rigorous imprisonment and fine without upper limit", "NDPS proviso applied to a cheating case"),
   ("3 to 7 years' rigorous imprisonment and fine up to ₹5 lakh", "pre-2013 fine cap assumed"),
   ("Up to 7 years' imprisonment, fine only, at the court's discretion", "minimum term and mandatory imprisonment missed")],
  ["s.4: RI 3–7 years and fine (cap removed in 2012); 10-year ceiling only for NDPS-linked proceeds."],
  "PMLA s.4", "Imprisonment is mandatory, with a 3-year minimum.", "case", f"{PML}, s.4 (as amended 2012)", group=G4)

Q("P5", "L4", case_pml + "\n\nMr. B wishes to challenge the Appellate Tribunal's order. The forum and last date (without condonation) are:",
  f"High Court, by {D(at4 + timedelta(60))}",
  [(f"Supreme Court, by {D(at4 + timedelta(60))}", "wrong forum (SARFAESI/IBC habit)"),
   (f"High Court, by {D(at4 + timedelta(45))}", "s.26 45-day period applied to s.42"),
   (f"Special Court, by {D(at4 + timedelta(30))}", "trial court confused with appellate forum")],
  ["s.42: appeal to the High Court within 60 days of communication of the Appellate Tribunal's decision, on any question of law or fact "
   "(extendable by up to 60 more days for sufficient cause).", f"{D(at4)} + 60 = {D(at4 + timedelta(60))}."],
  "PMLA s.42", "PMLA: Tribunal → High Court.", "case", f"{PML}, s.42", group=G4)

# =====================================================================================
QUOTA = {"I": 25, "S": 22, "D": 20, "P": 22}
per_act = Counter(ACT_OF.values())
lv_act = {a: Counter(q["rubric_level"] for q in B.Q if ACT_OF[q["id"]] == a) for a in QUOTA}
groups = Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"])
print("per act", dict(per_act), {a: dict(v) for a, v in lv_act.items()})
print("case sets", dict(groups))
assert dict(per_act) == QUOTA, per_act
assert all(3 <= v <= 5 for v in groups.values())
assert all(q["rubric_level"] == "L4" for q in B.Q if q["stimulus_group"])
missing = set(B.cat) - {q["microtopic_slug"] for q in B.Q}
assert not missing, missing
assert len(B.Q) == 89
B.write()
