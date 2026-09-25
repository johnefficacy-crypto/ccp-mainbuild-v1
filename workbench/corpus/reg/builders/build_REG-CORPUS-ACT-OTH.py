"""REG-CORPUS-ACT-OTH — financial-sector-acts: FEMA 1999 (25), Competition Act 2002 (22), LLP Act 2008 (20) = 67 Q.
Every numeric key and distractor is computed here from stated figures; asserts guard hand-checked values.
Distractors are named errors (pre-amendment values, neighbouring sections, wrong base, wrong timeline).
Run: python3 builders/build_REG-CORPUS-ACT-OTH.py  -> out/REG-CORPUS-ACT-OTH.json + _review.md
"""
import os as _os
import sys
import csv
from datetime import date, timedelta

_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
from reglib import Batch, inr, R, pct, lakh, crore, make_slug  # noqa: F401,E402

BATCH, PREFIX = "REG-CORPUS-ACT-OTH", "ACTO"
LIST = _os.path.join(_REG, 'lists', 'fsa.' + BATCH + '.tsv')

FEMA = "Foreign Exchange Management Act, 1999"
COMP = "Competition Act, 2002"
LLPA = "Limited Liability Partnership Act, 2008"

MICRO = [
    ("FEMA — residential status under s.2(v)", FEMA),
    ("FEMA — current and capital account transactions (s.5, s.6) and LRS", FEMA),
    ("FEMA — authorised persons and RBI directions (s.10 to s.12)", FEMA),
    ("FEMA — penalties, enforcement and compounding (s.13 to s.15)", FEMA),
    ("FEMA — adjudication and appeals", FEMA),
    ("FEMA — civil character and contrast with FERA", FEMA),
    ("Competition Act — anti-competitive agreements (s.3)", COMP),
    ("Competition Act — abuse of dominant position (s.4)", COMP),
    ("Competition Act — combinations and merger control (s.5, s.6)", COMP),
    ("Competition Act — CCI composition and inquiry process", COMP),
    ("Competition Act — penalties and lesser penalty (s.27, s.46)", COMP),
    ("Competition Act — settlement, commitment and appeals", COMP),
    ("LLP Act — partners, designated partners and mutual rights", LLPA),
    ("LLP Act — incorporation, legal status and liability", LLPA),
    ("LLP Act — conversion into LLP", LLPA),
    ("LLP Act — small LLP, filings and decriminalisation", LLPA),
    ("LLP Act — winding up and dissolution", LLPA),
]
_os.makedirs(_os.path.dirname(LIST), exist_ok=True)
with open(LIST, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(["slug", "exams", "name", "act"])
    for name, act in MICRO:
        w.writerow([make_slug(name, "fsa"), "ifsca,pfrda,sebi", name, act])

S = {k: make_slug(n, "fsa") for k, (n, _) in zip(
    ["F_RES", "F_CAP", "F_AP", "F_PEN", "F_ADJ", "F_CIV",
     "C_AGR", "C_DOM", "C_CMB", "C_CCI", "C_PEN", "C_SET",
     "L_PAR", "L_INC", "L_CNV", "L_SML", "L_WND"], MICRO)}

B = Batch(BATCH, "financial-sector-acts", PREFIX, list_file=LIST)


def add(micro, level, stem, correct, wrongs, steps, formula, trap, kind, ref, group=None):
    return B.add(micro=S[micro], level=level, stem=stem, correct=correct, wrongs=wrongs, steps=steps,
                 formula=formula, trap=trap, kind=kind, group=group, verify_fact=True, ref=ref)


def D(d):  # 5 Aug 2026
    return f"{d.day} {d.strftime('%b %Y')}"


def span(a, b):  # inclusive day count
    return (b - a).days + 1


def cr(x):  # x in crore
    return f"₹{x:,.2f} crore"


ST3 = "1 and 2 only|2 and 3 only|1 and 3 only|1, 2 and 3".split("|")
AR = ["Both A and R are true, and R is the correct explanation of A",
      "Both A and R are true, but R is not the correct explanation of A",
      "A is true, but R is false",
      "A is false, but R is true"]

# =====================================================================================
# FEMA, 1999 — 25 questions
# =====================================================================================

# ---- L1 (5)
add("F_RES", "L1",
    "Under s.2(v) of FEMA, the basic day-count test that makes an individual a \"person resident in India\" "
    "for FY 2026-27 is that he resided in India for:",
    "More than 182 days during FY 2025-26",
    [("182 days or more during FY 2026-27", "income-tax style current-year test imported"),
     ("More than 182 days during FY 2026-27", "current FY used instead of the preceding FY"),
     ("Not less than 120 days during FY 2025-26", "LLP designated-partner residency test (120 days) imported")],
    ["s.2(v)(i): a person residing in India for more than 182 days during the course of the preceding financial year.",
     "The test looks back to the preceding FY (FY 2025-26 for FY 2026-27), and 182 days exactly is not enough.",
     "Even if the count is met, the purpose-based exclusions in s.2(v)(i)(A)/(B) can override it."],
    "Resident (individual) = > 182 days in preceding FY, subject to purpose exclusions",
    "Two traps: 'preceding' FY, and 'more than' 182 days.", "conceptual", f"{FEMA}, s.2(v)")

add("F_CIV", "L1",
    "A contravention of a provision of FEMA (other than the special regime for assets held abroad) is, by its basic design:",
    "A civil wrong visited with a monetary penalty imposed on adjudication",
    [("A criminal offence punishable with imprisonment and fine on prosecution", "FERA, 1973 approach"),
     ("A cognizable, non-bailable offence investigated by the police", "confused with PMLA-type offences"),
     ("An offence with a statutory presumption of culpable mental state", "FERA s.59 presumption carried over")],
    ["FEMA replaced FERA from 1 June 2000 and converted foreign-exchange violations into civil contraventions.",
     "s.13 provides monetary penalty after adjudication under s.16; imprisonment arises only as civil imprisonment "
     "for non-payment of penalty (s.14).",
     "FERA treated violations as criminal offences and presumed culpable mental state."],
    "FEMA: contravention → adjudication → penalty (civil)",
    "Civil imprisonment under s.14 is a recovery tool, not punishment for the contravention.", "conceptual",
    f"{FEMA}, s.13, s.14, s.16; FERA 1973, s.59")

add("F_CAP", "L1",
    "After the Finance Act, 2015 amendment to s.6 of FEMA (effective 2019), capital account transactions "
    "involving debt instruments are regulated by:",
    "The RBI, in consultation with the Central Government",
    [("The Central Government, in consultation with the RBI", "that is the rule for non-debt instruments (s.6(2A))"),
     ("SEBI, in consultation with the RBI", "securities regulator confused with FEMA authority"),
     ("The Central Government alone, without consulting the RBI", "consultation requirement dropped")],
    ["s.6(2): RBI, in consultation with the Central Government, specifies permissible capital account transactions "
     "involving debt instruments (FEM (Debt Instruments) Regulations, 2019).",
     "s.6(2A): the Central Government, in consultation with RBI, prescribes transactions NOT involving debt "
     "instruments (FEM (Non-debt Instruments) Rules, 2019)."],
    "Debt → RBI (consulting GoI); non-debt → GoI (consulting RBI)",
    "The two limbs are mirror images; candidates swap them.", "conceptual", f"{FEMA}, s.6(2), s.6(2A) (Finance Act 2015)")

add("F_AP", "L1",
    "Authorisation to act as an authorised dealer, money changer or off-shore banking unit under s.10 of FEMA is granted by:",
    "The Reserve Bank of India, on an application made to it",
    [("The Central Government, on the RBI's recommendation", "Central Government's s.6(2A)/s.5 role confused"),
     ("The Directorate of Enforcement, on an application made to it", "enforcement agency confused with regulator"),
     ("FEDAI, as the self-regulatory body of dealers", "industry body mistaken for statutory authority")],
    ["s.10(1): the Reserve Bank may, on an application made to it, authorise any person to be an authorised dealer, "
     "money changer, off-shore banking unit or any other authorised person.",
     "RBI can also revoke the authorisation under s.10(3)."],
    "s.10: RBI authorises and revokes", "The Directorate of Enforcement investigates; it does not license.",
    "conceptual", f"{FEMA}, s.10(1)")

add("F_ADJ", "L1",
    "An appeal against an order of the Appellate Tribunal under FEMA lies to the High Court:",
    "Within 60 days, on a question of law",
    [("Within 45 days, on questions of fact and law", "Appellate Tribunal's own 45-day limit applied"),
     ("Within 60 days, on questions of fact and law", "s.35 limited to questions of law"),
     ("Within 90 days, on a question of law", "90-day period of s.14 (penalty payment) confused")],
    ["s.35: any person aggrieved by a decision of the Appellate Tribunal may appeal to the High Court within 60 days "
     "on any question of law arising out of such order.",
     "The High Court may allow a further period not exceeding 60 days for sufficient cause."],
    "Tribunal → High Court: 60 days, law only", "Appeals to the Tribunal are 45 days; to the High Court 60 days.",
    "conceptual", f"{FEMA}, s.35")

# ---- L2 (8)
s1a, s1b = date(2025, 5, 12), date(2025, 9, 20)
s2a, s2b = date(2026, 2, 8), date(2026, 3, 31)
s3a, s3b = date(2026, 4, 1), date(2026, 6, 30)
d1, d2, d3 = span(s1a, s1b), span(s2a, s2b), span(s3a, s3b)
tot = d1 + d2
assert (d1, d2, tot) == (132, 52, 184)
add("F_RES", "L2",
    "Mr. Varun Iyer, an Indian citizen working in India, was physically in India during the following periods:\n\n"
    "| Spell | Arrived | Left |\n|---|---|---|\n"
    f"| 1 | {D(s1a)} | {D(s1b)} |\n| 2 | {D(s2a)} | stayed on (in India on {D(s2b)}) |\n"
    f"| 3 | (continuing) | {D(s3b)} |\n\n"
    "Count both the day of arrival and the day of departure as days in India. For deciding whether the "
    "day-count limb of s.2(v) is met for FY 2026-27, the correct count and result are:",
    f"{tot} days — day-count limb satisfied",
    [(f"{tot-2} days — day-count limb not satisfied", "arrival days excluded despite the counting rule given"),
     (f"{tot} days — not satisfied, as the stay was not continuous", "continuity wrongly required"),
     (f"{d3} days — not satisfied, counted in FY 2026-27", "current FY counted instead of preceding FY")],
    [f"Relevant year = preceding FY 2025-26 (1 Apr 2025 – 31 Mar 2026).",
     f"Spell 1: {D(s1a)} – {D(s1b)} = {d1} days; Spell 2 up to {D(s2b)} = {d2} days.",
     f"Total = {tot} days > 182 → the day-count limb is satisfied (spells need not be continuous).",
     f"Days from 1 Apr 2026 ({d3}) belong to FY 2026-27 and are irrelevant for that year's status."],
    "Days in preceding FY > 182", "Aggregate all spells within the preceding FY only.", "numerical",
    f"{FEMA}, s.2(v)(i)")

add("F_RES", "L2",
    "Ms. Neha Rao lived in India throughout FY 2025-26. On 10 Aug 2026 she leaves India to take up employment "
    "with a company in Dubai. Her status under FEMA on 11 Aug 2026 is:",
    "Person resident outside India, from the time she left India for employment",
    [("Person resident in India for all of FY 2026-27, as she stayed over 182 days in FY 2025-26",
      "day count applied without the employment exclusion"),
     ("Person resident in India until 31 Mar 2027; non-resident from 1 Apr 2027", "status wrongly fixed for the whole FY"),
     ("Person resident in India until she completes 182 days outside India", "non-residence wrongly made to need 182 days abroad")],
    ["s.2(v)(i)(A): a person who has gone out of India for or on taking up employment outside India is excluded "
     "from 'person resident in India', even if he stayed more than 182 days in the preceding FY.",
     "The exclusion operates from the time she goes out for employment."],
    "Resident test = day count − purpose exclusions", "Purpose (employment abroad) overrides the day count.",
    "conceptual", f"{FEMA}, s.2(v)(i)(A)")

add("F_CAP", "L2",
    "Which one of the following, undertaken by a person resident in India, is a current account transaction under FEMA?",
    "Remittance for medical treatment abroad of the remitter's spouse",
    [("Purchase of a residential flat in London for personal use", "creates an asset outside India → capital account"),
     ("Raising an external commercial borrowing from an overseas lender", "creates a liability outside India → capital"),
     ("Guaranteeing a loan taken by a non-resident from a foreign bank", "contingent liability outside India → capital")],
    ["s.2(e): a capital account transaction alters assets or liabilities, including contingent liabilities, outside "
     "India of persons resident in India (or in India of non-residents).",
     "s.2(j): current account transactions include expenses for foreign travel, education and medical care of "
     "parents, spouse and children.",
     "Flat abroad, ECB and a guarantee all alter assets/liabilities → capital account."],
    "Alters foreign assets/liabilities (incl. contingent) → capital; else current",
    "A guarantee is a contingent liability, so it is capital account.", "conceptual", f"{FEMA}, s.2(e), s.2(j)")

lrs = 250000
edu, inv, gift, prior = 80000, 100000, 45000, 30000
head = lrs - (edu + inv + gift)
assert head == 25000
USD = lambda x: f"USD {inr(x)}"
add("F_CAP", "L2",
    f"Assume the Liberalised Remittance Scheme (LRS) ceiling is {USD(lrs)} per resident individual per financial year, "
    "covering both permissible current and capital account purposes. Mrs. Kavya Menon's remittances:\n\n"
    "| Date | Purpose | Amount |\n|---|---|---:|\n"
    f"| 20 Feb 2026 | Gift to a relative abroad | {USD(prior)} |\n"
    f"| 15 May 2026 | Tuition and living expenses of daughter studying abroad | {USD(edu)} |\n"
    f"| 02 Jul 2026 | Purchase of listed shares abroad | {USD(inv)} |\n"
    f"| 18 Sep 2026 | Gift to a nephew abroad | {USD(gift)} |\n\n"
    "No amount beyond the ceiling was claimed on the basis of a university's estimate. The unused LRS headroom "
    "for the rest of FY 2026-27 is:",
    USD(head),
    [(USD(lrs - inv - gift), "education remittance treated as outside LRS"),
     (USD(lrs - edu - inv), "gift treated as outside LRS"),
     ("Nil — the ceiling is already exceeded", "Feb 2026 remittance (FY 2025-26) wrongly counted")],
    [f"Only FY 2026-27 remittances count: {inr(edu)} + {inr(inv)} + {inr(gift)} = {inr(edu+inv+gift)}.",
     f"Headroom = {inr(lrs)} − {inr(edu+inv+gift)} = {USD(head)}.",
     "Studies abroad, gifts and portfolio investment are all within the single LRS ceiling."],
    "Headroom = Ceiling − FY remittances under LRS", "LRS is per financial year, not calendar year.", "numerical",
    f"{FEMA}, s.5 and s.6; LRS (ceiling given in stem)")

days = 12
p11 = 10000 + 2000 * days
assert p11 == 34000
add("F_AP", "L2",
    f"An authorised dealer bank contravenes a direction issued by the RBI under s.11 of FEMA, and the contravention "
    f"continues for {days} further days after it began. The maximum penalty the RBI can impose on the bank is:",
    R(p11),
    [(R(200000 + 5000 * days), "s.13 non-quantifiable penalty rates applied"),
     (R(10000 + 5000 * days), "s.13 daily rate of ₹5,000 used"),
     (R(10000), "continuing-contravention penalty ignored")],
    ["s.11(3): RBI may impose a penalty up to ₹10,000 and, for a continuing contravention, an additional penalty up "
     "to ₹2,000 for every day the contravention continues.",
     f"Maximum = 10,000 + 2,000 × {days} = {inr(p11)}."],
    "Max = ₹10,000 + ₹2,000 × continuing days", "s.11 (authorised person vs RBI direction) ≠ s.13 (general penalty).",
    "numerical", f"{FEMA}, s.11(3)")

sumv = 4800000
add("F_PEN", "L2",
    f"In a contravention of FEMA the sum involved is quantifiable at {R(sumv)}. The maximum penalty under s.13(1) is:",
    R(3 * sumv),
    [(R(2 * sumv), "twice the sum involved"),
     (R(200000), "₹2 lakh cap for non-quantifiable sums applied"),
     (R(4 * sumv), "sum involved added to thrice the sum")],
    ["s.13(1): penalty up to thrice the sum involved where the amount is quantifiable, or up to ₹2 lakh where not quantifiable.",
     f"Maximum = 3 × {inr(sumv)} = {inr(3*sumv)}."],
    "Max penalty = 3 × sum involved (quantifiable)", "₹2 lakh applies only when the sum cannot be quantified.",
    "numerical", f"{FEMA}, s.13(1)")

app = date(2026, 3, 1)
c180 = app + timedelta(days=180)
assert c180 == date(2026, 8, 28)
add("F_PEN", "L2",
    f"Sagar Textiles Pvt Ltd applies on {D(app)} to compound a contravention of FEMA. Under s.15, the compounding "
    "authority is required to compound it on or before (date = application date + statutory period):",
    D(c180),
    [(D(app + timedelta(days=365)), "one-year adjudication period of s.16(6) applied"),
     (D(app + timedelta(days=90)), "90-day penalty-payment period of s.14 applied"),
     (D(app + timedelta(days=45)), "45-day appeal period applied")],
    ["s.15(1): any contravention may, on an application, be compounded within 180 days from the date of receipt of "
     "the application by the Directorate of Enforcement or RBI officers as empowered.",
     f"{D(app)} + 180 days = {D(c180)}."],
    "Compounding deadline = application date + 180 days", "One year is the adjudication endeavour, not compounding.",
    "numerical", f"{FEMA}, s.15")

rec = date(2026, 6, 10)
a45 = rec + timedelta(days=45)
add("F_ADJ", "L2",
    f"An Additional Director of Enforcement, acting as adjudicating authority, imposes a penalty on Meru Gems Ltd. "
    f"The company receives a copy of the order on {D(rec)}. Its appeal (without seeking condonation) must be filed:",
    f"Before the Appellate Tribunal by {D(a45)}",
    [(f"Before the Special Director (Appeals) by {D(a45)}", "s.17 forum is only for Assistant/Deputy Director orders"),
     (f"Before the Appellate Tribunal by {D(rec + timedelta(days=60))}", "60-day High Court period used"),
     (f"Before the High Court by {D(rec + timedelta(days=60))}", "Tribunal stage skipped")],
    ["s.17: Special Director (Appeals) hears appeals only against orders of Assistant or Deputy Directors.",
     "Orders of other adjudicating authorities go to the Appellate Tribunal under s.19.",
     f"s.19(2): within 45 days from receipt of the order → {D(rec)} + 45 = {D(a45)}."],
    "Other AA orders → Appellate Tribunal, 45 days", "Forum depends on the rank of the adjudicating officer.",
    "numerical", f"{FEMA}, s.17, s.19")

# ---- L3 (7)
t1, t2, t3 = (date(2025, 4, 1), date(2025, 6, 30)), (date(2025, 10, 1), date(2025, 11, 30)), (date(2026, 2, 1), date(2026, 3, 2))
dd = [span(*t) for t in (t1, t2, t3)]
assert sum(dd) == 182
add("F_RES", "L3",
    "Mr. Sameer Khan, an Indian citizen who normally works abroad, visited India on a holiday basis in three spells "
    "during FY 2025-26 (both arrival and departure days counted):\n\n"
    "| Spell | From | To | Days |\n|---|---|---|---:|\n"
    + "\n".join(f"| {i+1} | {D(t[0])} | {D(t[1])} | {n} |" for i, (t, n) in enumerate(zip((t1, t2, t3), dd)))
    + "\n\nOver the previous four years he spent more than 365 days in India. His status under FEMA for FY 2026-27 is:",
    f"Not resident — {sum(dd)} days is not more than 182 days",
    [(f"Resident — {sum(dd)} days meets the 182-day threshold", "'more than 182' read as '182 or more'"),
     ("Resident — 60 days in the year plus 365 days in four years suffices", "income-tax alternative test imported"),
     ("Undetermined until FY 2026-27 ends, as the current FY is tested", "current-year test assumed")],
    [f"Days in FY 2025-26 = {' + '.join(map(str, dd))} = {sum(dd)}.",
     "s.2(v)(i) requires MORE THAN 182 days in the preceding FY; 182 fails.",
     "FEMA has no 60-day/365-day alternative (that is an Income-tax Act concept)."],
    "Resident only if days in preceding FY > 182", "Exactly 182 is the classic boundary trap.", "numerical",
    f"{FEMA}, s.2(v)(i)")

add("F_CAP", "L3",
    "Consider the following statements under FEMA:\n\n"
    "1. A person resident in India may continue to hold a house in London that he acquired while he was resident outside India.\n"
    "2. A person resident outside India may hold immovable property in India inherited from a person resident in India.\n"
    "3. Current account transactions need prior permission unless exempted, whereas capital account transactions are "
    "free unless restricted.\n\nWhich of the statements is/are correct?",
    "1 and 2 only",
    [("2 and 3 only", "s.6(4) protection for assets acquired while non-resident overlooked"),
     ("1 and 3 only", "s.6(5) inheritance protection overlooked; s.5/s.6 scheme reversed"),
     ("1, 2 and 3", "s.5/s.6 scheme reversed")],
    ["s.6(4): a resident may hold, own, transfer or invest in foreign currency, foreign security or immovable property "
     "outside India acquired when he was resident outside India, or inherited from a non-resident — statement 1 true.",
     "s.6(5): a non-resident may hold property in India acquired when resident in India or inherited from a resident — statement 2 true.",
     "s.5 makes current account dealings free subject to reasonable restrictions by the Central Government; capital "
     "account dealings are allowed only as specified under s.6 — statement 3 is reversed."],
    "Current: free unless restricted; Capital: permitted only as specified",
    "The s.6(4)/(5) grandfathering is status-based, not approval-based.", "statement",
    f"{FEMA}, s.5, s.6(4), s.6(5)")

tot_d = 40
p13c = 200000 + 5000 * (tot_d - 1)
assert p13c == 395000
add("F_PEN", "L3",
    f"A resident firm fails to file a mandatory FEMA report; the sum involved is not quantifiable. The default "
    f"continues for a total of {tot_d} days (including the first day). The maximum penalty under s.13(1) is:",
    R(p13c),
    [(R(200000 + 5000 * tot_d), "first day also counted for the daily penalty"),
     (R(10000 + 2000 * (tot_d - 1)), "s.11 authorised-person rates applied"),
     (R(200000), "continuing penalty ignored")],
    ["s.13(1): up to ₹2 lakh where the amount is not quantifiable.",
     "Continuing contravention: further penalty up to ₹5,000 for every day AFTER THE FIRST DAY.",
     f"Max = 2,00,000 + 5,000 × ({tot_d} − 1) = {inr(p13c)}."],
    "Max = ₹2,00,000 + ₹5,000 × (days − 1)", "The daily add-on starts after the first day.", "numerical",
    f"{FEMA}, s.13(1)")

add("F_PEN", "L3",
    "Penalties imposed under s.13 of FEMA remain unpaid. Notice of demand was served on each person on the same day.\n\n"
    "| Person | Penalty demanded | Days since notice served |\n|---|---:|---:|\n"
    "| 1. Mr. Ajay | ₹1.5 crore | 100 |\n| 2. Ms. Bela | ₹60 lakh | 60 |\n| 3. Mr. Chirag | ₹60 lakh | 120 |\n\n"
    "Which of the following are correct under s.14?\n\n"
    "1. Mr. Ajay is liable to civil imprisonment, with detention up to three years.\n"
    "2. Ms. Bela is liable to civil imprisonment, with detention up to six months.\n"
    "3. Mr. Chirag is liable to civil imprisonment, with detention up to six months.",
    "1 and 3 only",
    [("1, 2 and 3", "90-day payment window of s.14 ignored for Ms. Bela"),
     ("3 only", "₹1 crore threshold misread as barring detention for larger demands"),
     ("1 only", "six-month tier for demands up to ₹1 crore overlooked")],
    ["s.14: civil imprisonment arises only if the penalty is not paid within 90 days of service of the notice.",
     "Detention: three years where the demand exceeds ₹1 crore; six months in other cases.",
     "Ajay (₹1.5 crore, 100 days) → 3 years; Bela (60 days) → not yet liable; Chirag (₹60 lakh, 120 days) → 6 months."],
    "s.14: unpaid > 90 days → detention 3 yrs (> ₹1 crore) / 6 months (others)",
    "Liability is triggered by the 90-day default, not by the order itself.", "statement", f"{FEMA}, s.14")

add("F_ADJ", "L3",
    "Match the order under FEMA (Column A) with the forum to which the first appeal lies (Column B):\n\n"
    "| Column A — order passed by | Column B — appeal forum |\n|---|---|\n"
    "| P. Deputy Director of Enforcement as adjudicating authority | 1. High Court |\n"
    "| Q. Joint Director of Enforcement as adjudicating authority | 2. Special Director (Appeals) |\n"
    "| R. Special Director (Appeals) | 3. Appellate Tribunal |\n"
    "| S. Appellate Tribunal (question of law) | 4. Appellate Tribunal |",
    "P-2, Q-3, R-4, S-1",
    [("P-3, Q-2, R-4, S-1", "Special Director forum assigned to the wrong rank"),
     ("P-2, Q-2, R-3, S-1", "all Enforcement orders sent to Special Director (Appeals)"),
     ("P-2, Q-3, R-1, S-4", "Special Director's orders sent straight to High Court")],
    ["s.17: orders of Assistant/Deputy Directors → Special Director (Appeals).",
     "s.19: orders of other adjudicating authorities and of the Special Director (Appeals) → Appellate Tribunal.",
     "s.35: Appellate Tribunal orders → High Court on questions of law."],
    "AD/DD → SD(A) → AT → HC; higher AA → AT → HC", "Rank of the adjudicating officer decides the first forum.",
    "match", f"{FEMA}, s.17, s.19, s.35")

add("F_CIV", "L3",
    "Consider the following statements contrasting FEMA, 1999 with FERA, 1973:\n\n"
    "1. FEMA's preamble speaks of facilitating external trade and payments, whereas FERA aimed at conserving foreign exchange resources.\n"
    "2. FERA raised a presumption of culpable mental state against the accused; FEMA contains no such presumption.\n"
    "3. FEMA barred courts from taking cognizance of offences under the repealed FERA after two years from FEMA's commencement.\n\n"
    "Which of the statements is/are correct?",
    "1, 2 and 3",
    [("1 and 2 only", "two-year sunset for FERA cognizance (s.49(3)) overlooked"),
     ("2 and 3 only", "preamble contrast overlooked"),
     ("1 and 3 only", "FERA s.59 presumption overlooked")],
    ["Preamble: FEMA — facilitate external trade and payments and orderly development of the forex market; FERA — conservation of forex.",
     "FERA s.59 presumed culpable mental state; FEMA contraventions are civil with no such presumption.",
     "FEMA s.49(3): no cognizance of FERA offences after two years from 1 June 2000."],
    "FERA: criminal, conservation; FEMA: civil, facilitation", "All three are standard contrast points.",
    "statement", f"{FEMA}, Preamble, s.49(3); FERA 1973, s.59")

add("F_AP", "L3",
    "**Assertion (A):** The RBI may revoke an authorised person's authorisation in the public interest without first "
    "giving it an opportunity to make a representation.\n\n"
    "**Reason (R):** Under s.10(3) of FEMA, the requirement of a reasonable opportunity of making a representation "
    "applies only to revocation on the ground of failure to comply with conditions or contravention of the Act.",
    AR[0], [(AR[1], "link between proviso and assertion missed"),
            (AR[2], "proviso wrongly read as covering all grounds"),
            (AR[3], "public-interest revocation wrongly assumed to need a hearing")],
    ["s.10(3)(a): revocation in the public interest; s.10(3)(b): failure to comply with conditions or contravention.",
     "Proviso: no revocation on a ground in clause (b) without reasonable opportunity of representation.",
     "Hence public-interest revocation (clause (a)) needs no prior representation — R explains A."],
    "s.10(3) proviso attaches to clause (b) only", "Hearing requirement is ground-specific.", "assertion-reason",
    f"{FEMA}, s.10(3)")

# ---- L4 case set (5)
inv_usd, real_usd, fx = 500000, 180000, 84
unreal = inv_usd - real_usd
sum_inr = unreal * fx
assert sum_inr == 26880000
dep = date(2026, 6, 5)
ord_rec = date(2026, 7, 14)
CASE_F = ("**Case — Kaveri Tradelinks Pvt Ltd and Mr. Rohan Mehra (fictional)**\n\n"
          "Kaveri Tradelinks Pvt Ltd, a company incorporated in India, exported goods invoiced at "
          f"{USD(inv_usd)}. Only {USD(real_usd)} was realised; the balance {USD(unreal)} was not realised or repatriated "
          f"within the permitted period, and no extension was obtained. Take the reference rate as ₹{fx} per USD. "
          "A complaint was filed and a Deputy Director of Enforcement was appointed adjudicating authority.\n\n"
          "Mr. Rohan Mehra, Kaveri's export head, lived in India throughout FY 2025-26. On "
          f"{D(dep)} he left India to take up employment with a Singapore firm. He owns a flat in Pune that he bought in 2019.")
GF = "ACTO-CASE-FEMA"

add("F_RES", "L4", CASE_F + "\n\nOn 1 Jul 2026, Mr. Rohan Mehra is:",
    "A person resident outside India, having gone abroad for employment",
    [("A person resident in India for FY 2026-27, having stayed over 182 days in FY 2025-26",
      "day count applied without the employment exclusion"),
     ("A person resident in India until he completes 182 days in Singapore", "non-residence wrongly made to need 182 days abroad"),
     ("A person resident outside India only from 1 Apr 2027", "status wrongly fixed for the whole FY")],
    ["s.2(v)(i)(A)(a): a person who has gone out of India for or on taking up employment outside India is not a "
     "person resident in India, whatever his day count in the preceding FY.",
     f"From {D(dep)} Rohan is a person resident outside India."],
    "Employment abroad → excluded from 'resident'", "Purpose trumps the 182-day count.", "case",
    f"{FEMA}, s.2(v)(i)(A)", group=GF)

add("F_PEN", "L4", CASE_F + "\n\nThe maximum penalty that can be imposed on Kaveri under s.13(1) is:",
    R(3 * sum_inr),
    [(R(3 * inv_usd * fx), "thrice the full invoice value, including the realised part"),
     (R(4 * sum_inr), "sum involved added to thrice the sum"),
     (R(200000), "₹2 lakh non-quantifiable cap applied")],
    [f"Sum involved = unrealised {USD(unreal)} × ₹{fx} = {inr(sum_inr)}.",
     f"s.13(1): up to thrice the sum involved = 3 × {inr(sum_inr)} = {inr(3*sum_inr)}."],
    "Max = 3 × unrealised export value in ₹", "Only the unrealised amount is the 'sum involved'.", "case",
    f"{FEMA}, s.8, s.13(1)", group=GF)

add("F_ADJ", "L4", CASE_F + f"\n\nThe Deputy Director imposes a penalty and Kaveri receives the order on {D(ord_rec)}. "
    "Its first appeal (without seeking condonation) lies:",
    f"To the Special Director (Appeals), by {D(ord_rec + timedelta(days=45))}",
    [(f"To the Appellate Tribunal, by {D(ord_rec + timedelta(days=45))}", "s.17 forum for Deputy Director orders skipped"),
     (f"To the Special Director (Appeals), by {D(ord_rec + timedelta(days=60))}", "60-day period used"),
     (f"To the High Court, by {D(ord_rec + timedelta(days=60))}", "first-appeal stages skipped")],
    ["s.17: orders of an Assistant or Deputy Director of Enforcement are appealable to the Special Director (Appeals).",
     f"s.17(2): within 45 days of receipt → {D(ord_rec)} + 45 = {D(ord_rec + timedelta(days=45))}."],
    "Deputy Director order → SD(A) within 45 days", "Only orders of higher-ranked AAs go straight to the Tribunal.",
    "case", f"{FEMA}, s.17", group=GF)

add("F_PEN", "L4", CASE_F + "\n\nBefore adjudication, Kaveri considers compounding. Consider:\n\n"
    "1. The contravention may be compounded by officers of the Directorate of Enforcement or of the RBI empowered for the purpose.\n"
    "2. Once compounded, no proceeding or further proceeding shall be initiated or continued for that contravention.\n"
    "3. Compounding is available only after the adjudicating authority has passed its order.\n\n"
    "Which of the statements is/are correct?",
    "1 and 2 only",
    [("1, 2 and 3", "compounding wrongly limited to post-adjudication"),
     ("2 and 3 only", "compounding authorities overlooked; stage misstated"),
     ("1 and 3 only", "bar on further proceedings overlooked")],
    ["s.15(1): contraventions may be compounded by the Director of Enforcement / officers of the Directorate and "
     "RBI officers as empowered by the Central Government.",
     "s.15(2): once compounded, no proceeding or further proceeding shall be initiated or continued.",
     "Compounding can be sought before adjudication — statement 3 false."],
    "Compounding: ED/RBI, within 180 days, bars further proceedings", "Compounding is an alternative to adjudication.",
    "case", f"{FEMA}, s.15", group=GF)

add("F_CAP", "L4", CASE_F + "\n\nNow a non-resident, Rohan wishes to keep the Pune flat. Under FEMA:",
    "He may keep it, as he acquired it while resident",
    [("He must sell it within one year of becoming a non-resident", "fictitious disposal timeline"),
     ("He may hold it only with prior RBI permission", "s.6(5) grandfathering overlooked"),
     ("He may hold it only if it had been inherited", "only the inheritance limb of s.6(5) recalled")],
    ["s.6(5): a person resident outside India may hold, own, transfer or invest in immovable property situated in "
     "India if it was acquired, held or owned when he was resident in India, or inherited from a person resident in India.",
     "Rohan bought the flat in 2019 while resident → he may continue to hold it."],
    "s.6(5): acquired while resident / inherited from resident → may hold", "Both limbs of s.6(5) protect him.",
    "case", f"{FEMA}, s.6(5)", group=GF)

# =====================================================================================
# COMPETITION ACT, 2002 — 22 questions
# =====================================================================================

# ---- L1 (4)
add("C_AGR", "L1",
    "Under s.3(3) of the Competition Act, a horizontal agreement between competitors that directly fixes sale prices is:",
    "Presumed to have an appreciable adverse effect on competition",
    [("Examined on the s.19(3) factors with no presumption", "rule-of-reason treatment of vertical agreements applied"),
     ("Exempt if the parties' combined market share is below 25%", "foreign de minimis concept imported"),
     ("Void only if one of the parties is found dominant", "s.4 dominance requirement imported into s.3")],
    ["s.3(3): agreements between enterprises engaged in identical or similar trade that fix prices, limit output, "
     "share markets or rig bids shall be presumed to have an AAEC.",
     "Vertical agreements under s.3(4) are assessed under the rule of reason on s.19(3) factors."],
    "Horizontal (s.3(3)) → presumption; vertical (s.3(4)) → rule of reason",
    "No market-share safe harbour exists for s.3(3) cartels.", "conceptual", f"{COMP}, s.3(3)")

add("C_CCI", "L1",
    "Under s.8 of the Competition Act (as amended in 2007), the Competition Commission of India consists of a Chairperson and:",
    "Not less than two and not more than six other Members",
    [("Not less than two and not more than ten other Members", "original 2002 text before the 2007 amendment"),
     ("Exactly six other Members", "range misread as fixed strength"),
     ("Not less than four and not more than ten other Members", "invented range mixing old ceiling")],
    ["s.8(1) as amended by the Competition (Amendment) Act, 2007: Chairperson and not less than 2 and not more than 6 other Members.",
     "The original 2002 text allowed up to 10 other Members."],
    "CCI = Chairperson + 2 to 6 Members", "Distractor uses the pre-2007 ceiling of ten.", "conceptual",
    f"{COMP}, s.8(1) (2007 amendment)")

add("C_SET", "L1",
    "An enterprise aggrieved by a penalty order of the CCI under s.27 files its appeal before:",
    "The National Company Law Appellate Tribunal (NCLAT)",
    [("The Competition Appellate Tribunal (COMPAT) at Delhi", "COMPAT abolished by Finance Act 2017"),
     ("The High Court having territorial jurisdiction", "writ route confused with statutory appeal"),
     ("The Securities Appellate Tribunal (SAT) at Mumbai", "securities-market tribunal confused")],
    ["The Finance Act, 2017 merged COMPAT into NCLAT; s.53A now designates NCLAT as Appellate Tribunal.",
     "Further appeal from NCLAT lies to the Supreme Court (s.53T)."],
    "CCI → NCLAT → Supreme Court", "COMPAT no longer exists.", "conceptual", f"{COMP}, s.53A, s.53B")

add("C_DOM", "L1",
    "Under s.4 of the Competition Act, holding a dominant position in a relevant market:",
    "Is not prohibited by itself; only its abuse is prohibited",
    [("Is prohibited once market share exceeds 50%", "fixed market-share test assumed"),
     ("Requires prior approval of the CCI to be maintained", "combination pre-approval concept confused"),
     ("Is prohibited if the enterprise is a government company", "public-sector status misread as a violation")],
    ["s.4(1): no enterprise or group shall abuse its dominant position.",
     "Dominance is assessed on s.19(4) factors — not a single market-share number — and is not unlawful per se."],
    "s.4: abuse, not dominance, is prohibited", "The Act uses no numerical dominance threshold.", "conceptual",
    f"{COMP}, s.4, s.19(4)")

# ---- L2 (7)
T = {"FY 2022-23": 1840, "FY 2023-24": 2150, "FY 2024-25": 2410}
avgT = sum(T.values()) / 3
pen = 0.10 * avgT
assert round(pen, 2) == 213.33
tblT = "| Financial year | Turnover (₹ crore) |\n|---|---:|\n" + "\n".join(f"| {k} | {inr(v)} |" for k, v in T.items())
add("C_PEN", "L2",
    f"Suryodaya Pharma Ltd is found to have abused its dominant position (s.4). Its turnover:\n\n{tblT}\n\n"
    "The order is passed in FY 2025-26. The maximum penalty under s.27(b) is:",
    cr(pen),
    [(cr(0.10 * T["FY 2024-25"]), "10% of the latest year's turnover only"),
     (cr(0.10 * sum(T.values())), "10% of aggregate, not average, turnover"),
     (cr(0.10 * (T["FY 2023-24"] + T["FY 2024-25"]) / 2), "average of only two preceding years")],
    [f"Average turnover of the three preceding FYs = ({' + '.join(inr(v) for v in T.values())}) ÷ 3 = {avgT:,.2f}.",
     f"Maximum penalty = 10% × {avgT:,.2f} = {cr(pen)}."],
    "Max penalty = 10% × average turnover of 3 preceding FYs", "Average, not aggregate or latest year.",
    "numerical", f"{COMP}, s.27(b)")

add("C_AGR", "L2",
    "Which one of the following agreements is presumed to cause an appreciable adverse effect on competition under s.3(3)?",
    "Three road contractors agreeing who will quote lowest in a tender",
    [("A manufacturer fixing the minimum resale price for its dealers", "resale price maintenance is vertical (s.3(4))"),
     ("A supplier appointing one exclusive distributor for a state", "exclusive distribution is vertical (s.3(4))"),
     ("A printer maker requiring buyers to purchase its cartridges", "tie-in arrangement is vertical (s.3(4))")],
    ["s.3(3)(d): agreements that directly or indirectly result in bid rigging or collusive bidding are presumed to have AAEC.",
     "RPM, exclusive distribution and tie-ins are s.3(4) vertical agreements judged on the rule of reason."],
    "Competitors + bid rigging → s.3(3) presumption", "Vertical restraints have no presumption.", "conceptual",
    f"{COMP}, s.3(3)(d), s.3(4)")

dv = 2400
add("C_CMB", "L2",
    f"GlobalSoft Inc. agrees to acquire StartX Technologies Pvt Ltd for ₹{inr(dv)} crore. StartX's assets and turnover "
    "in India are within the de minimis (small-target) exemption, and the parties do not cross the asset/turnover "
    "thresholds in s.5(a)–(c). StartX has substantial business operations in India. Under the Act as amended in 2023:",
    "Notice is required: deal value exceeds ₹2,000 crore with Indian operations",
    [("No notice needed, since the de minimis target exemption applies", "small-target exemption applied to deal-value route"),
     ("No notice needed, since the asset/turnover thresholds are not met", "deal-value threshold s.5(d) overlooked"),
     ("Notice is due within 30 days after the deal is completed", "post-completion filing; also old 30-day window")],
    ["2023 amendment inserted s.5(d): a transaction whose value exceeds ₹2,000 crore is a combination where the "
     "target has substantial business operations in India.",
     "The small-target exemption does not take such a deal outside s.5(d).",
     "s.6(2): notice must be given before the combination comes into effect."],
    "Deal value > ₹2,000 crore + SBO in India → notifiable", "Deal-value test catches low-asset, high-price targets.",
    "conceptual", f"{COMP}, s.5(d), s.6(2) (2023 amendment)")

nd = date(2026, 2, 2)
bd = date(2026, 1, 18)
add("C_CMB", "L2",
    f"Notice of a combination is filed with the CCI on {D(nd)} (board approval was on {D(bd)}). The CCI neither "
    "passes an order nor stops the clock. The standstill period and the date it runs to (notice date + period) are:",
    f"150 days — up to {D(nd + timedelta(days=150))}",
    [(f"210 days — up to {D(nd + timedelta(days=210))}", "pre-2023 outer limit of 210 days"),
     (f"30 days — up to {D(nd + timedelta(days=30))}", "prima facie opinion window treated as standstill"),
     (f"150 days — up to {D(bd + timedelta(days=150))}", "period counted from board approval")],
    ["s.6(2A) as amended in 2023: no combination shall come into effect until 150 days have passed from the date of "
     "notice or the CCI passes an order, whichever is earlier (earlier 210 days).",
     "s.31(11): if no order is passed within that period, the combination is deemed approved.",
     f"{D(nd)} + 150 days = {D(nd + timedelta(days=150))}."],
    "Standstill = 150 days from notice (2023)", "Trigger is the notice date, not board approval.", "numerical",
    f"{COMP}, s.6(2A), s.31(11) (2023 amendment)")

add("C_DOM", "L2",
    "A dominant cement producer engages in each practice below. Which one is NOT an abuse under s.4(2)?",
    "Matching a rival's lower price in one region to meet competition",
    [("Selling below cost to drive a new entrant out of the region", "predatory pricing — s.4(2)(a)(ii)"),
     ("Refusing a rival access to its rail siding and depot", "denial of market access — s.4(2)(c)"),
     ("Making purchase of cement conditional on buying its RMC", "supplementary obligation — s.4(2)(d)")],
    ["s.4(2)(a): unfair or discriminatory condition or price, including predatory price, is abuse.",
     "Proviso: a discriminatory condition or price adopted to meet the competition is not covered.",
     "Denial of market access (c) and supplementary obligations (d) are abuses."],
    "Meeting-competition proviso to s.4(2)(a)", "Price discrimination to meet competition is protected.",
    "conceptual", f"{COMP}, s.4(2)")

add("C_SET", "L2",
    "Under the 2023 amendments, a commitment under s.48B can be offered:",
    "In a s.4 abuse case, after the s.26(1) order but before the DG report",
    [("In a s.3(3) cartel case, after the s.26(1) order but before the DG report", "cartels excluded from commitment"),
     ("In a s.4 abuse case, after the DG report is received", "settlement stage (s.48A) confused with commitment"),
     ("In any case, after the final s.27 order, while the appeal is pending", "post-order stage; no such route")],
    ["s.48B: commitment for alleged s.3(4) or s.4 contraventions, after the s.26(1) order and before the DG's investigation report.",
     "s.48A: settlement — after the DG report and before the final order.",
     "Neither route is available for s.3(3) horizontal agreements (cartels)."],
    "Commitment: s.26(1) → [commit] → DG report → [settle] → final order", "Settlement follows, commitment precedes, the DG report.",
    "conceptual", f"{COMP}, s.48A, s.48B (2023 amendment)")

imp = 84
add("C_SET", "L2",
    f"The CCI imposes a penalty of ₹{imp} crore on Vayu Airlines Ltd under s.27. To have its appeal entertained by "
    "the NCLAT, Vayu must first deposit:",
    cr(0.25 * imp),
    [(cr(0.10 * imp), "10% pre-deposit borrowed from other statutes"),
     (cr(0.50 * imp), "50% pre-deposit assumed"),
     (cr(imp), "full penalty assumed payable before appeal")],
    ["s.53B(1) proviso (2023 amendment): no appeal against a penalty order shall be entertained unless the appellant "
     "deposits 25% of the penalty imposed.",
     f"25% × {imp} = {cr(0.25*imp)}."],
    "Pre-deposit = 25% of penalty", "The 2023 amendment introduced a mandatory 25% pre-deposit.", "numerical",
    f"{COMP}, s.53B (2023 amendment)")

# ---- L3 (7)
P3 = [60, 75, 90]; T3 = [1200, 1350, 1500]
tp, tt = 3 * sum(P3), 0.10 * sum(T3)
assert all(3 * p > 0.1 * t for p, t in zip(P3, T3)) and (tp, tt) == (675, 405)
yrs = ["FY 2022-23", "FY 2023-24", "FY 2024-25"]
tblC = "| Year of cartel | Profit (₹ crore) | Turnover (₹ crore) |\n|---|---:|---:|\n" + \
       "\n".join(f"| {y} | {p} | {inr(t)} |" for y, p, t in zip(yrs, P3, T3))
add("C_PEN", "L3",
    f"Kosi Tyres Ltd participated in a cartel for three years:\n\n{tblC}\n\nThe maximum penalty on Kosi under the "
    "cartel proviso to s.27(b) is:",
    cr(tp),
    [(cr(tt), "lower of the two limbs chosen"),
     (cr(0.10 * sum(T3) / 3), "non-cartel 10% of average turnover applied"),
     (cr(3 * P3[-1]), "three times only the latest year's profit")],
    [f"Limb 1: 3 × profit for each year = 3 × ({' + '.join(map(str, P3))}) = {tp}.",
     f"Limb 2: 10% of turnover for each year = 10% × {inr(sum(T3))} = {tt:.0f}.",
     f"Whichever is higher → {cr(tp)}."],
    "Cartel: max(3 × profit, 10% × turnover) for each year of continuance",
    "The cartel proviso counts each year of continuance, not an average.", "numerical", f"{COMP}, s.27(b) proviso")

base = {"Alpha": 300, "Beta": 240, "Gamma": 180}
band = [1.0, 0.5, 0.3]
minpay = sum(b * (1 - r) for b, r in zip(base.values(), band))
assert minpay == 246
add("C_PEN", "L3",
    "Three members of a cartel apply under s.46 in the order Alpha, Beta, Gamma, each making full, true and vital "
    "disclosure. Assume the lesser-penalty regulations allow reductions of up to 100%, up to 50% and up to 30% "
    "for the first, second and third applicants respectively. Penalties before reduction (₹ crore):\n\n"
    "| Applicant | Penalty before reduction |\n|---|---:|\n" + "\n".join(f"| {k} | {v} |" for k, v in base.items()) +
    "\n\nThe minimum aggregate penalty payable by the three, if each gets its full band, is:",
    cr(minpay),
    [(cr(base["Alpha"] * 0 + base["Beta"] * 0.7 + base["Gamma"] * 0.5), "second and third bands swapped"),
     (cr(base["Alpha"] * 0.5 + base["Beta"] * 0.5 + base["Gamma"] * 0.7), "first applicant given only 50%"),
     (cr(base["Beta"] * 0.5 + base["Gamma"] * 0.5), "Gamma given the 50% band as well")],
    ["Alpha (first): 300 × (1 − 100%) = 0.",
     "Beta (second): 240 × (1 − 50%) = 120.",
     "Gamma (third): 180 × (1 − 30%) = 126.",
     f"Total = {cr(minpay)}."],
    "Payable = Penalty × (1 − band by priority)", "Bands depend on order of application, not penalty size.",
    "numerical", f"{COMP}, s.46; lesser-penalty bands given in stem")

add("C_AGR", "L3",
    "Consider the following statements on s.3 of the Competition Act:\n\n"
    "1. After the 2023 amendment, an enterprise not engaged in identical or similar trade that participates in "
    "furthering a horizontal agreement is presumed to be a party to it.\n"
    "2. A joint venture agreement that increases efficiency in production or supply is outside the s.3(3) presumption.\n"
    "3. Vertical agreements under s.3(4), such as exclusive supply, are presumed to cause an appreciable adverse effect.\n\n"
    "Which of the statements is/are correct?",
    "1 and 2 only",
    [("1, 2 and 3", "vertical agreements wrongly given the presumption"),
     ("2 and 3 only", "2023 hub-and-spoke provision overlooked"),
     ("1 and 3 only", "efficiency JV proviso overlooked")],
    ["2023 amendment to s.3(3): a non-competitor participating in furtherance of a horizontal agreement is presumed "
     "to be part of it (hub-and-spoke).",
     "Proviso to s.3(3): efficiency-enhancing joint ventures are excluded from the presumption.",
     "s.3(4) vertical agreements are contraventions only if they cause AAEC — no presumption."],
    "s.3(3) presumption (+hub-and-spoke, −efficiency JV); s.3(4) rule of reason",
    "Only horizontal agreements carry the presumption.", "statement", f"{COMP}, s.3(3), s.3(4) (2023 amendment)")

add("C_DOM", "L3",
    "Match the statutory factor (Column A) with the provision under which the CCI considers it (Column B):\n\n"
    "| Column A — factor | Column B — provision |\n|---|---|\n"
    "| P. Dependence of consumers on the enterprise | 1. s.19(3) — appreciable adverse effect |\n"
    "| Q. Accrual of benefits to consumers | 2. s.19(4) — dominant position |\n"
    "| R. Transport costs and local specification requirements | 3. s.19(6) — relevant geographic market |\n"
    "| S. Physical characteristics or end-use of goods | 4. s.19(7) — relevant product market |",
    "P-2, Q-1, R-3, S-4",
    [("P-1, Q-2, R-3, S-4", "AAEC and dominance factors swapped"),
     ("P-2, Q-1, R-4, S-3", "geographic and product market factors swapped"),
     ("P-2, Q-4, R-3, S-1", "consumer benefit read as product-market factor")],
    ["s.19(4): dominance factors include market share, size and resources, dependence of consumers, entry barriers.",
     "s.19(3): AAEC factors include barriers to entry, foreclosure, accrual of benefits to consumers.",
     "s.19(6): geographic market — regulatory barriers, local specification, transport costs.",
     "s.19(7): product market — physical characteristics, end-use, price, consumer preferences."],
    "s.19(3) AAEC · s.19(4) dominance · s.19(6) geographic · s.19(7) product",
    "Consumer dependence signals dominance; consumer benefit is a pro-competitive AAEC factor.", "match",
    f"{COMP}, s.19(3), (4), (6), (7)")

# thresholds given in stem (data)
TH_A, DM_A, DM_T = 2500, 450, 1250
deals = {"D1": (3000, 400, 1000, 900, False), "D2": (2800, 600, 1400, 1100, False), "D3": (1500, 300, 800, 2300, True)}


def notifiable(k):
    comb, ta, tt_, val, sbo = deals[k]
    dm = ta <= DM_A or tt_ <= DM_T
    return (comb > TH_A and not dm) or (val > 2000 and sbo)


ans = [k for k in deals if notifiable(k)]
assert ans == ["D2", "D3"]
add("C_CMB", "L3",
    f"Assume: (i) the parties' combined assets in India exceed ₹{inr(TH_A)} crore is the relevant s.5 asset test; "
    f"(ii) the small-target exemption applies where the target has Indian assets not above ₹{DM_A} crore OR Indian "
    f"turnover not above ₹{inr(DM_T)} crore. Three proposed acquisitions (₹ crore):\n\n"
    "| Deal | Combined Indian assets | Target Indian assets | Target Indian turnover | Deal value | Target has substantial Indian operations |\n"
    "|---|---:|---:|---:|---:|---|\n" +
    "\n".join(f"| {k} | {inr(v[0])} | {v[1]} | {inr(v[2])} | {inr(v[3])} | {'Yes' if v[4] else 'No'} |" for k, v in deals.items()) +
    "\n\nWhich deals must be notified to the CCI?",
    "D2 and D3 only",
    [("D1, D2 and D3", "small-target exemption ignored for D1"),
     ("D2 only", "deal-value threshold (s.5(d)) ignored for D3"),
     ("D1 and D3 only", "exemption applied to the wrong target")],
    ["D1: combined assets 3,000 > 2,500, but target assets 400 ≤ 450 → small-target exemption; deal value 900 → not notifiable.",
     "D2: combined assets 2,800 > 2,500; target 600 > 450 and 1,400 > 1,250 → no exemption → notifiable.",
     "D3: below asset test, but deal value 2,300 > 2,000 with substantial Indian operations → notifiable under s.5(d)."],
    "Asset/turnover test − small-target exemption; OR deal value > ₹2,000 crore + SBO",
    "The exemption is satisfied if EITHER target limb is within the limit.", "numerical",
    f"{COMP}, s.5, s.5(d) (2023 amendment); asset and de minimis limits given as data")

add("C_SET", "L3",
    "**Assertion (A):** A party to a bid-rigging cartel cannot apply for settlement under s.48A.\n\n"
    "**Reason (R):** Settlement and commitment are available only for alleged contraventions of s.3(4) and s.4; "
    "cartel members may instead seek lesser penalty under s.46.",
    AR[0], [(AR[1], "link between scope of s.48A and the assertion missed"),
            (AR[2], "s.46 route or scope limit denied"),
            (AR[3], "cartels wrongly assumed eligible for settlement")],
    ["s.48A/s.48B (2023) apply to proceedings under s.3(4) (vertical) and s.4 (abuse) only.",
     "Bid rigging is an s.3(3) horizontal agreement → excluded; the leniency route is s.46.",
     "R directly explains A."],
    "Settlement/commitment: s.3(4), s.4 only; cartels → s.46", "Cartels get leniency, not settlement.",
    "assertion-reason", f"{COMP}, s.46, s.48A, s.48B (2023 amendment)")

add("C_CCI", "L3",
    "Arrange the stages of a CCI inquiry into an alleged s.4 contravention in the correct order:\n\n"
    "P. Director General investigates and submits a report\n"
    "Q. CCI forms a prima facie opinion and directs investigation under s.26(1)\n"
    "R. Information is filed under s.19(1)\n"
    "S. CCI passes a final order under s.27 after hearing the parties",
    "R → Q → P → S",
    [("R → P → Q → S", "DG investigation placed before the prima facie order"),
     ("Q → R → P → S", "prima facie opinion placed before information"),
     ("R → Q → S → P", "final order placed before the DG report")],
    ["s.19(1): inquiry begins on information, reference or suo motu.",
     "s.26(1): if a prima facie case exists, CCI directs the DG to investigate.",
     "DG report → objections/hearing → final order under s.27."],
    "Information → s.26(1) → DG report → s.27 order", "The DG acts only on the CCI's s.26(1) direction.",
    "conceptual", f"{COMP}, s.19, s.26, s.27")

# ---- L4 case set (4)
Pc = [20, 22, 25]; Tc = [900, 1000, 1100]
lim1, lim2 = 3 * sum(Pc), 0.10 * sum(Tc)
assert (lim1, lim2) == (201, 300)
beta_base = 150
pen_ch = lim2
CASE_C = ("**Case — Western RMC Suppliers Forum (fictional)**\n\n"
          "Aravali RMC Ltd, Bhima Infra Ltd and Chambal Concrete Ltd supply ready-mix concrete. Through meetings of "
          "their trade association, the Western RMC Suppliers Forum, they decided in advance who would quote lowest "
          "in municipal tenders from FY 2022-23 to FY 2024-25 (three years). Aravali approached the CCI first under "
          "s.46 with full disclosure; Bhima approached second. Chambal did not apply. Chambal's figures (₹ crore):\n\n"
          "| Year | Profit | Turnover |\n|---|---:|---:|\n" +
          "\n".join(f"| {y} | {p} | {inr(t)} |" for y, p, t in zip(yrs, Pc, Tc)) +
          "\n\nAssume the lesser-penalty regulations allow up to 100% reduction for the first applicant and up to 50% "
          "for the second.")
GC = "ACTO-CASE-COMP"

add("C_AGR", "L4", CASE_C + "\n\nThe arrangement is best characterised as:",
    "A horizontal s.3(3) agreement, presumed to cause AAEC",
    [("A vertical s.3(4) agreement judged on the rule of reason", "competitors' pact treated as vertical"),
     ("Outside s.3, as decisions of an association are not agreements", "association practices wrongly excluded"),
     ("An abuse of collective dominance under s.4 only", "s.4 applied instead of s.3(3)")],
    ["s.3(3) covers agreements and decisions of associations of enterprises engaged in identical or similar trade, including cartels.",
     "s.3(3)(d): bid rigging/collusive bidding is presumed to have AAEC."],
    "Competitors + association + bid rigging → s.3(3)(d)", "Association decisions are expressly covered.",
    "case", f"{COMP}, s.3(3)(d)", group=GC)

add("C_PEN", "L4", CASE_C + "\n\nThe maximum penalty that can be imposed on Chambal is:",
    cr(max(lim1, lim2)),
    [(cr(lim1), "lower of the two limbs chosen"),
     (cr(0.10 * sum(Tc) / 3), "non-cartel 10% of average turnover applied"),
     (cr(0.10 * Tc[-1]), "10% of only the latest year's turnover")],
    [f"3 × profit for each year = 3 × {sum(Pc)} = {lim1}.",
     f"10% of turnover for each year = 10% × {inr(sum(Tc))} = {lim2:.0f}.",
     f"Higher of the two = {cr(max(lim1, lim2))}."],
    "Cartel: higher of 3 × profit or 10% × turnover, each year", "Here the turnover limb is higher.",
    "case", f"{COMP}, s.27(b) proviso", group=GC)

add("C_SET", "L4", CASE_C + f"\n\nThe CCI computes Bhima's penalty before reduction at ₹{beta_base} crore. Bhima also asks to "
    "settle under s.48A. The correct position is:",
    f"Minimum payable {cr(beta_base*0.5)}; settlement is not available",
    [(f"Minimum payable {cr(beta_base*0.5)}; settlement allowed after DG report", "cartels wrongly made eligible for s.48A"),
     (f"Minimum payable {cr(0)}; full immunity as it also disclosed", "first-applicant band given to second applicant"),
     (f"Minimum payable {cr(beta_base*0.7)}; settlement is not available", "third-applicant 30% band applied")],
    [f"Second applicant: up to 50% reduction → 150 × 50% = {cr(beta_base*0.5)}.",
     "s.48A settlement is confined to s.3(4) and s.4 proceedings; bid rigging falls under s.3(3)."],
    "Payable = base × (1 − band); cartel → no settlement", "Leniency is the only concession route for cartelists.",
    "case", f"{COMP}, s.46, s.48A", group=GC)

add("C_SET", "L4", CASE_C + f"\n\nThe CCI imposes {cr(pen_ch)} on Chambal. Chambal's appeal lies:",
    f"To NCLAT within 60 days, after depositing {cr(0.25*pen_ch)}",
    [(f"To NCLAT within 60 days, after depositing {cr(0.10*pen_ch)}", "10% pre-deposit assumed"),
     (f"To NCLAT within 30 days, after depositing {cr(0.25*pen_ch)}", "wrong appeal period"),
     (f"To the Supreme Court within 60 days, after depositing {cr(0.25*pen_ch)}", "NCLAT stage skipped")],
    ["s.53B: appeal to NCLAT within 60 days of receipt of the CCI's order.",
     f"2023 proviso: 25% of penalty must be deposited → 25% × {pen_ch:.0f} = {cr(0.25*pen_ch)}.",
     "Supreme Court appeal (s.53T) lies only against NCLAT's order."],
    "NCLAT, 60 days, 25% pre-deposit", "Supreme Court is the second appellate forum.", "case",
    f"{COMP}, s.53B, s.53T (2023 amendment)", group=GC)

# =====================================================================================
# LLP ACT, 2008 — 20 questions
# =====================================================================================

# ---- L1 (4)
add("L_PAR", "L1",
    "For incorporation of a limited liability partnership, the LLP Act, 2008 requires:",
    "At least two partners, with no maximum limit",
    [("At least two partners, with a maximum of fifty", "partnership-firm cap under Companies Act rules imported"),
     ("At least seven partners, with no maximum limit", "public-company minimum imported"),
     ("At least one partner, as with a one person company", "OPC concept imported")],
    ["s.6(1): every LLP shall have at least two partners.", "The Act prescribes no maximum."],
    "Minimum 2 partners; no ceiling", "The 50-person cap applies to partnership firms, not LLPs.", "conceptual",
    f"{LLPA}, s.6")

add("L_INC", "L1",
    "Which statement about the legal status of an LLP is correct?",
    "It is a body corporate with perpetual succession, outside the Partnership Act, 1932",
    [("It is a firm under the Partnership Act, 1932 with limited liability added", "s.4 exclusion overlooked"),
     ("It is a company limited by guarantee under the Companies Act, 2013", "LLP confused with guarantee company"),
     ("It is a body corporate, but a change in partners dissolves it", "perpetual succession denied")],
    ["s.3: an LLP is a body corporate, a legal entity separate from its partners, with perpetual succession; change "
     "in partners does not affect its existence.",
     "s.4: the Indian Partnership Act, 1932 does not apply to an LLP."],
    "LLP = body corporate + separate entity + perpetual succession", "It is neither a firm nor a company.",
    "conceptual", f"{LLPA}, s.3, s.4")

add("L_WND", "L1",
    "Under the LLP Act, an LLP may be wound up compulsorily by:",
    "The National Company Law Tribunal",
    [("The National Company Law Appellate Tribunal", "appellate forum confused with original forum"),
     ("The Registrar of Companies", "Registrar's strike-off power confused with winding up"),
     ("The High Court having jurisdiction", "pre-NCLT forum")],
    ["s.63: winding up may be voluntary or by the Tribunal.", "Tribunal = NCLT (s.2(1)(x) read with Companies Act, 2013)."],
    "Compulsory winding up → NCLT", "NCLAT hears appeals; High Courts no longer wind up LLPs.", "conceptual",
    f"{LLPA}, s.63, s.64")

add("L_CNV", "L1",
    "Conversion of an unlisted public company into an LLP is governed by:",
    "Section 57 read with the Fourth Schedule",
    [("Section 56 read with the Third Schedule", "private company conversion route"),
     ("Section 55 read with the Second Schedule", "partnership firm conversion route"),
     ("Section 57, which also covers listed companies", "listed companies wrongly included")],
    ["s.55/Second Schedule: firm → LLP.", "s.56/Third Schedule: private company → LLP.",
     "s.57/Fourth Schedule: unlisted public company → LLP."],
    "Firm 55/II · Pvt Co 56/III · Unlisted Public Co 57/IV", "Listed companies cannot use s.57.",
    "conceptual", f"{LLPA}, s.55 to s.57")

# ---- L2 (6)
add("L_PAR", "L2",
    "Sunrise Advisory LLP has exactly two designated partners, both individuals. In FY 2025-26, Ms. Asha (an Indian "
    "citizen working mainly from Dubai) stayed in India for 130 days; Mr. Brian (a foreign national) stayed 90 days. "
    "Under s.7, as amended by the LLP (Amendment) Act, 2021, the resident designated partner requirement for FY 2025-26 is:",
    "Met — Asha stayed in India for at least 120 days in the FY",
    [("Not met — a resident must stay 182 days in the preceding year", "pre-2021 182-day test applied"),
     ("Not met — both designated partners must be resident in India", "requirement is at least one resident"),
     ("Met — residency is irrelevant for designated partners", "residency requirement denied")],
    ["s.7(1): at least two designated partners who are individuals, at least one of whom shall be resident in India.",
     "Explanation (2021 amendment): 'resident in India' = stayed in India not less than 120 days during the financial year "
     "(earlier: 182 days during the immediately preceding one year).",
     "Asha's 130 days ≥ 120 → requirement met."],
    "≥1 designated partner resident: ≥120 days in the FY", "The 182-day test is pre-amendment.", "conceptual",
    f"{LLPA}, s.7 Explanation (LLP (Amendment) Act 2021)")

add("L_INC", "L2",
    "In the course of Crest Engineering LLP's business, partner Dev negligently certifies a defective design, causing "
    "loss to a client. Partner Esha had no involvement. Under ss.27 and 28, the client can recover from:",
    "The LLP and Dev; Esha is not personally liable",
    [("The LLP only; no partner is ever personally liable", "partner's own wrongful act (s.28(2)) ignored"),
     ("The LLP, Dev and Esha jointly, as in a firm", "unlimited joint liability of a firm imported"),
     ("Dev only; the LLP is not liable for a partner's act", "s.27(2) vicarious liability of the LLP ignored")],
    ["s.27(2): an LLP is liable if a partner is liable for a wrongful act or omission in the course of its business.",
     "s.28(2): a partner is personally liable for his own wrongful act or omission, but not for another partner's."],
    "LLP + wrongdoer liable; innocent partners protected", "Liability protection is lost only for one's own wrong.",
    "conceptual", f"{LLPA}, s.27, s.28")

due11 = date(2026, 5, 30)
fil11 = date(2026, 8, 15)
late = (fil11 - due11).days
assert late == 77
add("L_SML", "L2",
    f"Nimbus Tech LLP files its annual return (Form 11) for FY 2025-26 on {D(fil11)}. Assume an additional fee of "
    "₹100 per day of delay. The additional fee payable is:",
    R(100 * late),
    [(R(100 * (fil11 - date(2026, 3, 31)).days), "delay counted from the end of the FY"),
     (R(100 * (fil11 - date(2026, 6, 30)).days), "due date taken as 30 June"),
     (R(100 * (late + 1)), "due date itself counted as a day of delay")],
    ["s.35: annual return within 60 days of the close of the FY → due 30 May 2026.",
     f"Delay = {D(due11)} to {D(fil11)} = {late} days; fee = {late} × 100 = {inr(100*late)}."],
    "Annual return due = FY end + 60 days (30 May)", "Form 11 (60 days) ≠ Form 8 (30 Oct).", "numerical",
    f"{LLPA}, s.35; additional fee rate given in stem")

add("L_CNV", "L2",
    "Rathi & Co., a registered firm of four partners, wants to convert into an LLP. At conversion, partner Om wishes "
    "to retire and an investor, Priya, wishes to join. Under s.55 and the Second Schedule:",
    "It cannot convert unless all its partners become partners",
    [("It can convert, as long as the LLP has at least two partners", "minimum-partner rule mistaken for conversion condition"),
     ("It can convert if Om consents in writing to his exit", "consent does not cure the condition"),
     ("It can convert if the Registrar of Firms grants approval", "fictitious approval route")],
    ["Second Schedule: a firm may convert if all its partners become the partners of the LLP and no one else.",
     "Om's exit and Priya's entry must happen before or after conversion, not as part of it."],
    "Conversion: same partners in, no one else", "Partner changes break the identity condition.", "conceptual",
    f"{LLPA}, s.55, Second Schedule")

bL, bP, nP = 150000, 120000, 3
capL, capP = 100000, 50000
tot_pen = min(bL / 2, capL) + nP * min(bP / 2, capP)
assert tot_pen == 225000
add("L_SML", "L2",
    "Assume that the penalty payable by a small LLP (and its partners) is one-half of the penalty otherwise specified, "
    f"subject to a maximum of {R(capL)} for the LLP and {R(capP)} for each partner. For a default by Tara Small LLP, "
    f"the specified penalties work out to {R(bL)} on the LLP and {R(bP)} on each of its {nP} partners. The total penalty payable is:",
    R(tot_pen),
    [(R(bL / 2 + nP * bP / 2), "per-person caps ignored"),
     (R(bL + nP * bP), "small-LLP concession ignored"),
     (R(bL / 2 + capP), "partner cap applied to all partners together")],
    [f"LLP: half of {inr(bL)} = {inr(bL/2)} (below cap).",
     f"Each partner: half of {inr(bP)} = {inr(bP/2)} → capped at {inr(capP)}.",
     f"Total = {inr(bL/2)} + {nP} × {inr(capP)} = {inr(tot_pen)}."],
    "Payable = Σ min(½ × specified, cap)", "Caps apply per person.", "numerical",
    f"{LLPA}, lesser-penalty provision for small LLPs (LLP (Amendment) Act 2021); rule given in stem")

add("L_WND", "L2",
    "Nayan Advisory LLP has not filed its statement of account and solvency or annual return for FY 2021-22, 2022-23 "
    "and 2023-24. For four months in 2025 it had only one partner. Its partners have now resolved that the LLP be "
    "wound up by the Tribunal. Which ground under s.64 is available now?",
    "The LLP's own decision to be wound up by the Tribunal",
    [("Default in filing returns for consecutive financial years", "three years < five consecutive FYs required"),
     ("Partners reduced below two", "four months < more than six months required"),
     ("None, as only creditors may petition", "LLP's own decision ground overlooked")],
    ["s.64(a): the LLP decides that it be wound up by the Tribunal — available.",
     "s.64(b): partners below two for more than six months — not met (4 months).",
     "s.64(e): default in filing for any five consecutive FYs — not met (3 years)."],
    "s.64: own decision / <2 partners >6 months / 5-year filing default / just & equitable…",
    "Check the duration limbs before choosing a ground.", "conceptual", f"{LLPA}, s.64")

# ---- L3 (6)
death = date(2026, 1, 1)
six = date(2026, 6, 30)
debts = [(date(2026, 3, 15), 400000), (date(2026, 6, 20), 600000), (date(2026, 7, 10), 500000), (date(2026, 11, 2), 700000)]
per = sum(a for d, a in debts if d > six)
assert per == 1200000
add("L_PAR", "L3",
    f"Sheetal and Rakesh were the only partners of Vista Interiors LLP. Rakesh died on {D(death)}. Sheetal, knowing "
    "she was the sole partner, carried on the business throughout 2026 without admitting anyone. LLP obligations "
    "incurred in 2026:\n\n| Date | Obligation |\n|---|---:|\n" +
    "\n".join(f"| {D(d)} | {R(a)} |" for d, a in debts) +
    f"\n\nTreat the six-month period as ending on {D(six)}. Sheetal's personal liability under s.6(2) is for:",
    R(per),
    [(R(sum(a for _, a in debts)), "all obligations since the partner's death"),
     (R(sum(a for d, a in debts if d > date(2026, 9, 15))), "six months counted from the first obligation"),
     ("Nil, since the LLP is a separate legal entity", "s.6(2) exception ignored")],
    ["s.6(2): if an LLP carries on business with fewer than two partners for more than six months, the sole partner "
     "who knows it is personally liable for obligations incurred during the period after those six months.",
     f"Obligations after {D(six)}: {' + '.join(inr(a) for d, a in debts if d > six)} = {inr(per)}."],
    "Personal liability = obligations after the 6-month grace", "The first six months stay protected.",
    "numerical", f"{LLPA}, s.6(2)")

SL_C, SL_T = 5, 50
E = {"E1": (4, 60), "E2": (3, 45), "E3": (6, 20), "E4": (5, 50)}
q_ok = [k for k, (c, t) in E.items() if c <= SL_C and t <= SL_T]
assert q_ok == ["E2", "E4"]
add("L_SML", "L3",
    f"Assume the prescribed limits for a small LLP are contribution not exceeding ₹{SL_C} crore AND turnover (preceding "
    f"FY) not exceeding ₹{SL_T} crore. Data (₹ crore):\n\n| LLP | Contribution | Turnover |\n|---|---:|---:|\n" +
    "\n".join(f"| {k} | {c} | {t} |" for k, (c, t) in E.items()) + "\n\nWhich are small LLPs?",
    " and ".join(q_ok) + " only",
    [("E1, E2, E3 and E4", "either limit treated as sufficient"),
     ("E2 only", "'not exceeding' read as 'less than'"),
     ("E1, E2 and E4 only", "turnover limit ignored")],
    ["The definition (s.2(1)(ta), 2021) is conjunctive: both contribution and turnover limits must be met.",
     "E1 fails turnover; E3 fails contribution; E4 equals both limits — 'not exceeding' includes equality."],
    "Small LLP = contribution ≤ limit AND turnover ≤ limit", "Equality qualifies; both tests must pass.",
    "numerical", f"{LLPA}, s.2(1)(ta) (LLP (Amendment) Act 2021); limits given in stem")

add("L_SML", "L3",
    "Consider the following statements on the LLP (Amendment) Act, 2021:\n\n"
    "1. Carrying on business with intent to defraud creditors remains a criminal offence under the Act.\n"
    "2. The amendment introduced the concept of a small LLP, eligible for lower penalties.\n"
    "3. An appeal against a penalty order of the adjudicating officer lies to the NCLT.\n\n"
    "Which of the statements is/are correct?",
    "1 and 2 only",
    [("1, 2 and 3", "appellate authority misidentified as NCLT"),
     ("2 and 3 only", "fraud wrongly assumed decriminalised"),
     ("1 and 3 only", "small LLP concept overlooked")],
    ["Decriminalisation (2021) moved many defaults to penalties adjudged by an adjudicating officer (s.76A), but "
     "fraud under s.30 stays a criminal offence.",
     "Small LLP concept (s.2(1)(ta)) was introduced with lesser penalties.",
     "Appeal against the adjudicating officer's order lies to the Regional Director, not the NCLT."],
    "2021: decriminalise procedural defaults; keep fraud criminal; AO → RD appeal",
    "Adjudication appeals go to the Regional Director.", "statement",
    f"{LLPA}, s.30, s.76A, s.2(1)(ta) (LLP (Amendment) Act 2021)")

add("L_INC", "L3",
    "**Assertion (A):** A supplier of Orbit LLP cannot sue Orbit's partners personally for an unpaid contractual "
    "debt of the LLP, absent fraud.\n\n"
    "**Reason (R):** Under s.27(3), an obligation of an LLP, whether arising in contract or otherwise, is solely "
    "the obligation of the LLP.",
    AR[0], [(AR[1], "s.27(3) not linked to the assertion"),
            (AR[2], "s.27(3) misread"),
            (AR[3], "partners wrongly assumed liable as in a firm")],
    ["s.27(3): obligations of the LLP are solely its obligations; s.27(4): liabilities are met out of its property.",
     "s.28(1): a partner is not personally liable solely by reason of being a partner.",
     "Exception: s.30 unlimited liability where business is carried on with intent to defraud."],
    "s.27(3) + s.28(1): LLP alone owes its debts (fraud excepted)", "Fraud (s.30) is the key exception.",
    "assertion-reason", f"{LLPA}, s.27(3), s.28, s.30")

add("L_CNV", "L3",
    "Three private companies want to convert into LLPs under s.56 and the Third Schedule:\n\n"
    "| Company | Charge on assets | Shareholders joining LLP |\n|---|---|---|\n"
    "| Alpha Pvt Ltd | Bank charge fully satisfied and closed | All five, no one else |\n"
    "| Beta Pvt Ltd | Working capital charge subsisting | All three, no one else |\n"
    "| Gamma Pvt Ltd | No charge ever created | Three of four; the fourth exits |\n\n"
    "Which can convert?",
    "Alpha only",
    [("Alpha and Beta only", "subsisting security interest ignored"),
     ("Alpha and Gamma only", "all-shareholders condition ignored"),
     ("Alpha, Beta and Gamma", "both conditions ignored")],
    ["Third Schedule: conversion allowed only if there is no security interest subsisting or in force, and all "
     "shareholders become partners and no one else.",
     "Beta fails the security-interest test; Gamma fails the identity test."],
    "Pvt Co → LLP: no subsisting charge + identical membership", "Both conditions are cumulative.",
    "statement", f"{LLPA}, s.56, Third Schedule")

capA, capB, prof, rem = 3000000, 1000000, 1200000, 200000
shareA = prof / 2
assert shareA == 600000
add("L_PAR", "L3",
    f"Kiran and Leela are partners of Monsoon Crafts LLP with no LLP agreement. Kiran contributed {R(capA)} and Leela "
    f"{R(capB)}. Leela managed the business and claims {R(rem)} as remuneration. Profit for the year before any "
    f"remuneration is {R(prof)}. Under the First Schedule, Kiran's share of profit is:",
    R(shareA),
    [(R(prof * capA / (capA + capB)), "profit shared in capital ratio"),
     (R((prof - rem) / 2), "remuneration allowed before sharing"),
     (R((prof - rem) * capA / (capA + capB)), "capital ratio and remuneration both applied")],
    ["s.23(4): where there is no LLP agreement, the First Schedule governs mutual rights.",
     "First Schedule: partners share capital, profits and losses equally; no partner is entitled to remuneration.",
     f"Kiran's share = {inr(prof)} ÷ 2 = {inr(shareA)}."],
    "No agreement → equal sharing, no remuneration", "Contribution ratio is irrelevant under the default rules.",
    "numerical", f"{LLPA}, s.23(4), First Schedule")

# ---- L4 case set (4)
kd = [(date(2025, 4, 1), date(2025, 5, 10)), (date(2025, 12, 20), date(2026, 1, 15)), (date(2026, 3, 1), date(2026, 3, 28))]
kdays = sum(span(*t) for t in kd)
assert kdays == 95
due8 = date(2026, 10, 30)
fil8 = date(2027, 1, 5)
late8 = (fil8 - due8).days
assert late8 == 67
nt = date(2027, 1, 10)
ceas = nt + timedelta(days=30)
fdl = ceas + timedelta(days=30)
CASE_L = ("**Case — Arohi Design LLP (fictional)**\n\n"
          "Arohi Design Studio, a registered firm of three partners (Ira, Kabir and Meher), converted into Arohi Design "
          "LLP, registered on 1 Jul 2025. All three partners became partners of the LLP and no one else; Ira and Kabir "
          "are the designated partners. There is no clause in the LLP agreement on cessation. Ira lived in India "
          "throughout FY 2025-26. Kabir, posted to London, was in India only on these days (both ends counted):\n\n"
          "| Spell | From | To |\n|---|---|---|\n" +
          "\n".join(f"| {i+1} | {D(a)} | {D(b)} |" for i, (a, b) in enumerate(kd)) +
          "\n\nAssume an additional fee of ₹100 per day of delay for late filings.")
GL = "ACTO-CASE-LLP"

add("L_CNV", "L4", CASE_L + "\n\nConsider the following consequences of the conversion:\n\n"
    "1. All property and liabilities of the firm vested in the LLP, and the firm is deemed dissolved.\n"
    "2. For 12 months from registration, the LLP's official correspondence must state that it was converted from "
    "the firm, with the firm's name and registration number.\n"
    "3. Contracts made by the firm before conversion ended automatically on conversion.\n\n"
    "Which of the statements is/are correct?",
    "1 and 2 only",
    [("1, 2 and 3", "continuity of pending contracts overlooked"),
     ("2 and 3 only", "vesting and deemed dissolution overlooked"),
     ("1 and 3 only", "12-month correspondence disclosure overlooked")],
    ["Second Schedule: on registration, the firm's undertaking, property, rights and liabilities vest in the LLP and "
     "the firm is deemed dissolved.",
     "Every official correspondence for 12 months must disclose the conversion, firm name and registration number.",
     "Contracts and proceedings of the firm continue by or against the LLP — they do not lapse."],
    "Conversion = vesting + deemed dissolution + continuity + 12-month disclosure",
    "Conversion transfers, it does not terminate, contracts.", "case", f"{LLPA}, s.55, Second Schedule", group=GL)

add("L_PAR", "L4", CASE_L + "\n\nFor FY 2025-26, Arohi's compliance with the resident designated partner requirement is:",
    f"Compliant — Ira is resident, so Kabir's {kdays} days do not matter",
    [(f"Non-compliant — Kabir's {kdays} days fall short of 120 days", "requirement read as all designated partners"),
     ("Non-compliant — Ira must also have 182 days in the preceding year", "pre-2021 182-day test applied"),
     (f"Compliant — Kabir's {kdays} days exceed the 90-day minimum", "fictitious 90-day test")],
    [f"Kabir's days = {' + '.join(str(span(*t)) for t in kd)} = {kdays} (< 120, so not resident).",
     "s.7(1) needs only one designated partner resident in India (≥120 days in the FY). Ira qualifies.",
     "The LLP is compliant."],
    "≥1 resident designated partner (≥120 days in FY)", "Only one resident designated partner is needed.",
    "case", f"{LLPA}, s.7 (LLP (Amendment) Act 2021)", group=GL)

add("L_SML", "L4", CASE_L + f"\n\nArohi files its statement of account and solvency (Form 8) for FY 2025-26 on {D(fil8)}. "
    "The additional fee is:",
    R(100 * late8),
    [(R(100 * (fil8 - date(2026, 5, 30)).days), "annual return due date (30 May) applied"),
     (R(100 * (fil8 - date(2026, 9, 30)).days), "due date taken as six months from FY end"),
     (R(100 * (fil8 - date(2026, 11, 29)).days), "due date taken as eight months from FY end")],
    ["Statement of account and solvency is due within 30 days from the end of six months of the FY → 30 Oct 2026.",
     f"Delay = {D(due8)} to {D(fil8)} = {late8} days → {late8} × 100 = {inr(100*late8)}."],
    "Form 8 due 30 Oct; fee = days late × rate", "Six months is the preparation period; filing gets 30 more days.",
    "case", f"{LLPA}, s.34; LLP Rules, 2009 r.24; fee rate given in stem", group=GL)

add("L_PAR", "L4", CASE_L + f"\n\nMeher gives written notice of resignation to the other partners on {D(nt)}. Treat cessation "
    "as effective on expiry of the minimum notice period. The cessation date and the last date for the LLP to file "
    "the notice of change with the Registrar are:",
    f"{D(ceas)} and {D(fdl)}",
    [(f"{D(nt)} and {D(nt + timedelta(days=30))}", "cessation treated as immediate"),
     (f"{D(ceas)} and {D(ceas + timedelta(days=60))}", "60-day annual-return period used for filing"),
     (f"{D(ceas)} and {D(ceas + timedelta(days=15))}", "15-day filing period assumed")],
    ["s.24(1): absent agreement, a partner ceases by giving not less than 30 days' notice → "
     f"{D(nt)} + 30 = {D(ceas)}.",
     f"s.25(2): the LLP must file notice with the Registrar within 30 days of cessation → {D(fdl)}."],
    "Cessation = notice + 30 days; filing = cessation + 30 days", "Two separate 30-day clocks run back to back.",
    "case", f"{LLPA}, s.24, s.25", group=GL)

# =====================================================================================
QUOTA = {FEMA: 25, COMP: 22, LLPA: 20}
act_of = {make_slug(n, "fsa"): a for n, a in MICRO}
from collections import Counter  # noqa: E402
per_act = Counter(act_of[q["microtopic_slug"]] for q in B.Q)
assert dict(per_act) == QUOTA, per_act
assert {q["microtopic_slug"] for q in B.Q} == set(act_of), "every microtopic must be used"
assert len(B.Q) == 67
B.write()
