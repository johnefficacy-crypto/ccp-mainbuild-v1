"""REG-CORPUS-ACT-SEC builder: financial-sector-acts — securities-market statutes (71 Q).
SEBI Act 1992 (25) · Securities Contracts (Regulation) Act 1956 + SCRR (24) · Depositories Act 1996 (22).
Every numeric key and distractor is computed below; asserts guard hand-checked values.
Distractors = named errors (pre-amendment values, neighbouring section, other regulator, wrong timeline).
"""
import sys, os as _os, csv, math
from datetime import date, timedelta
from collections import Counter

_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
from reglib import Batch, inr, R, pct, lakh, crore, make_slug  # noqa: F401

BATCH, PREFIX = "REG-CORPUS-ACT-SEC", "ACTS"
LIST = _os.path.join(_REG, 'lists', f'fsa.{BATCH}.tsv')

SEBI = "Securities and Exchange Board of India Act, 1992"
SCRA = "Securities Contracts (Regulation) Act, 1956"
DA = "Depositories Act, 1996"
MICROS = [
    ("S1", "SEBI Act — establishment, Board composition and functions", SEBI),
    ("S2", "SEBI Act — directions, interim measures, CIS and registration", SEBI),
    ("S3", "SEBI Act — Chapter VIA penalties and adjudication", SEBI),
    ("S4", "SEBI Act — SAT appeals, settlement, recovery and offences", SEBI),
    ("C1", "SCRA — definitions of securities, derivatives, spot delivery and options", SCRA),
    ("C2", "SCRA — recognition, bye-laws and control of stock exchanges", SCRA),
    ("C3", "SCRA — contracts in notified areas and legality of derivatives", SCRA),
    ("C4", "SCRA — listing, delisting appeals and minimum public shareholding", SCRA),
    ("C5", "SCRA — penalties and adjudication under s.23 to s.23H", SCRA),
    ("D1", "Depositories Act — depository, participant and beneficial owner", DA),
    ("D2", "Depositories Act — option to hold, transfer, fungibility and opt-out", DA),
    ("D3", "Depositories Act — rights of depository and BO, pledge and indemnity", DA),
    ("D4", "Depositories Act — penalties, SEBI powers and appeals", DA),
]
_os.makedirs(_os.path.dirname(LIST), exist_ok=True)
with open(LIST, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(["slug", "exams", "name", "act"])
    for _, n, a in MICROS:
        w.writerow([make_slug(n, "fsa"), "ifsca,pfrda,sebi", n, a])
M = {k: make_slug(n, "fsa") for k, n, _ in MICROS}

B = Batch(BATCH, "financial-sector-acts", PREFIX, list_file=LIST)
ACT_OF = {}
LEN_FAIL = []


def add(mk, level, stem, correct, wrongs, steps, formula, trap, kind, ref, group=None):
    L = sorted(len(str(t)) for t in [correct] + [w[0] for w in wrongs])
    c = len(str(correct))
    if L[-1] >= 25 and c == L[-1] and c > 1.15 * L[-2]:
        LEN_FAIL.append((len(B.Q) + 1, c, L))
    qid = B.add(micro=M[mk], level=level, stem=stem, correct=correct, wrongs=wrongs, steps=steps,
                formula=formula, trap=trap, kind=kind, group=group, verify_fact=True, ref=ref)
    ACT_OF[qid] = mk[0]
    return qid


def amt(x):
    """₹ amount in lakh / crore with trimmed decimals."""
    if x >= 1e7:
        s = f"{x/1e7:,.2f}".rstrip("0").rstrip(".")
        return f"₹{s} crore"
    s = f"{x/1e5:,.2f}".rstrip("0").rstrip(".")
    return f"₹{s} lakh"


def d(x): return f"{x.day} {x.strftime('%B %Y')}"


def add_months(x, m):
    y, mo = divmod(x.month - 1 + m, 12)
    y += x.year; mo += 1
    last = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]
    return date(y, mo, min(x.day, last))


LAKH, CRORE = 1e5, 1e7


def daily(days, floor=LAKH, per=LAKH, cap=CRORE):
    """Post-2014 daily-default formula: not < ₹1 lakh; up to ₹1 lakh per day; max ₹1 crore."""
    return floor, min(per * days, cap)


def higher_of(fixed, mult, gain):
    return max(fixed, mult * gain)


ST = "\n\nWhich of the statements given above is/are correct?"
AR = ["Both A and R are true and R is the correct explanation of A",
      "Both A and R are true but R is not the correct explanation of A",
      "A is true but R is false", "A is false but R is true"]

# =====================================================================================
# SEBI ACT, 1992 — 25 Q  (L1 5 · L2 8 · L3 7 · L4 5)
# =====================================================================================
# ---- L1 ----
chair, govt, rbi, others = 1, 2, 1, 5
tot = chair + govt + rbi + others
assert tot == 9
add("S1", "L1",
    "Under section 4(1) of the SEBI Act, 1992, the maximum number of members on the Board of SEBI, **including the Chairman**, is:",
    f"{tot}", [(f"{tot-1}", "Chairman left out of the count"),
               (f"{chair+govt+rbi+3}", "only the minimum three whole-time members counted among the 'other' five"),
               (f"{tot+1}", "two RBI officials counted instead of one")],
    ["s.4(1)(a): a Chairman — 1.",
     "s.4(1)(b): two members from officials of the Ministry dealing with Finance and administration of company law — 2.",
     "s.4(1)(c): one member from officials of the Reserve Bank — 1.",
     "s.4(1)(d): five other members, of whom at least three are whole-time — 5.",
     f"Total = {chair} + {govt} + {rbi} + {others} = {tot}."],
    "Board = Chairman + 2 (Govt) + 1 (RBI) + 5 (others, ≥3 whole-time)",
    "'At least three whole-time' is a floor within the five, not a separate count.", "numerical",
    f"{SEBI}, s.4(1)")

add("S1", "L1",
    "SEBI functioned as a non-statutory body from 1988. It acquired statutory status under the SEBI Act, 1992 with effect from:",
    "30 January 1992",
    [("12 April 1988", "date of the non-statutory set-up by Government resolution"),
     ("4 April 1992", "date of Presidential assent, not the date the Act is deemed in force"),
     ("1 April 1992", "start of the financial year after the ordinance assumed")],
    ["SEBI was constituted by a Government resolution on 12 April 1988 without statutory powers.",
     "The SEBI Ordinance of 30 January 1992 was replaced by the Act, which is deemed to have come into force on 30 January 1992 (s.1(3)).",
     "s.3 establishes the Board as a body corporate with head office at Mumbai."],
    "SEBI Act s.1(3) and s.3", "Assent date (4 April 1992) ≠ commencement date.", "conceptual",
    f"{SEBI}, s.1(3), s.3")

add("S3", "L1",
    "For adjudging a penalty under Chapter VIA, SEBI appoints as adjudicating officer under section 15-I an officer:",
    "Not below the rank of Division Chief",
    [("Not below the rank of Executive Director", "rank ceiling confused with a senior-management approval level"),
     ("Who is a whole-time member of the Board", "confuses AO with the whole-time member passing s.11/11B orders"),
     ("Nominated by the Securities Appellate Tribunal", "appellate forum confused with adjudicating authority")],
    ["s.15-I(1): for adjudging under ss.15A–15HB, the Board may appoint any officer not below the rank of a Division Chief to hold an inquiry.",
     "The person concerned must be given a reasonable opportunity of being heard.",
     "SAT hears appeals from the AO's order; it does not appoint the AO."],
    "s.15-I(1)", "Directions under s.11B are passed by a WTM; money penalties are adjudicated by the AO.", "conceptual",
    f"{SEBI}, s.15-I")

add("S4", "L1",
    "An appeal from a decision or order of the Securities Appellate Tribunal lies to the Supreme Court under section 15Z of the SEBI Act on:",
    "Any question of law arising out of the order",
    [("Any question of fact or law arising out of the order", "widens the scope to facts"),
     ("Questions of law, but only via the High Court first", "inserts a High Court tier that the Act does not provide"),
     ("Any question of fact, with leave of SAT", "reverses the scope and adds a leave condition")],
    ["s.15Z: any person aggrieved by a SAT decision may appeal to the Supreme Court within 60 days of communication, on any question of law arising out of such order.",
     "The Supreme Court may allow a further period not exceeding 60 days on sufficient cause."],
    "s.15Z — law only; 60 + 60 days", "SAT is the last fact-finding forum.", "conceptual",
    f"{SEBI}, s.15Z")

add("S4", "L1",
    "Under section 24(1) of the SEBI Act (as amended), a person who contravenes the Act or its rules/regulations is punishable with imprisonment up to __ or fine up to __, or both:",
    "10 years; ₹25 crore",
    [("1 year; fine (no stated ceiling)", "pre-2002 position before the SEBI (Amendment) Act, 2002"),
     ("10 years; ₹1 crore", "fine ceiling confused with the s.15HB penalty maximum"),
     ("7 years; ₹25 crore", "imprisonment term taken from a different statute")],
    ["The SEBI (Amendment) Act, 2002 raised s.24(1) punishment to imprisonment up to ten years, or fine up to ₹25 crore, or both.",
     "s.24(2): failure to pay an AO penalty or comply with AO/Board directions carries imprisonment of not less than one month up to ten years, or fine up to ₹25 crore, or both."],
    "s.24(1)", "Criminal punishment (court) ≠ adjudicated penalty (AO).", "conceptual",
    f"{SEBI}, s.24 (as amended 2002)")

# ---- L2 ----
days = 37
lo, hi = daily(days)
assert (lo, hi) == (1e5, 37e5)
add("S3", "L2",
    f"A registered portfolio manager fails to furnish documents called for by SEBI; the failure continues for **{days} days**. The range of penalty the adjudicating officer may impose under section 15A is:",
    f"{amt(lo)} to {amt(hi)}",
    [(f"Nil to {amt(hi)}", "pre-2014 formula without a minimum penalty"),
     (f"{amt(lo)} to {amt(CRORE)}", "residual s.15HB range applied although s.15A is specific"),
     (f"{amt(lo)} to {amt(LAKH*(days-1))}", "first day of default excluded from the daily count")],
    ["s.15A (post-2014): penalty not less than ₹1 lakh, extending to ₹1 lakh for each day the failure continues, subject to a maximum of ₹1 crore.",
     f"Upper limit = ₹1 lakh × {days} = {amt(hi)} (below the ₹1 crore cap).",
     f"Range = {amt(lo)} to {amt(hi)}."],
    "Penalty ∈ [₹1 lakh, min(₹1 lakh × days, ₹1 crore)]",
    "The Securities Laws (Amendment) Act, 2014 introduced the ₹1 lakh floor.", "numerical",
    f"{SEBI}, s.15A (as amended 2014)")

gain = 6.4 * CRORE
mx = higher_of(25 * CRORE, 3, gain)
assert mx == 25 * CRORE
add("S3", "L2",
    f"An insider trades on unpublished price sensitive information and makes a profit of {amt(gain)}. The **maximum** penalty that can be adjudged under section 15G is:",
    amt(mx),
    [(amt(3 * gain), "three times profit taken alone, ignoring 'whichever is higher'"),
     (amt(25 * CRORE + 3 * gain), "₹25 crore and three times profit added together"),
     (amt(10 * CRORE), "₹10 lakh minimum misread as ₹10 crore ceiling")],
    ["s.15G: penalty not less than ₹10 lakh, extending to ₹25 crore or three times the profit made, whichever is higher.",
     f"Three times profit = 3 × {amt(gain)} = {amt(3*gain)}.",
     f"Higher of ₹25 crore and {amt(3*gain)} = {amt(mx)}."],
    "Max = max(₹25 crore, 3 × profit)", "Three times profit exceeds ₹25 crore only when profit > ₹8.33 crore.", "numerical",
    f"{SEBI}, s.15G")

add("S2", "L2",
    "A WTM of SEBI finds that a promoter made unlawful gains of ₹14 crore through a manipulative scheme and orders him to disgorge that amount. The power to direct disgorgement is expressly found in:",
    "Section 11B(1)",
    [("Section 15HA", "money penalty for fraudulent practices confused with disgorgement"),
     ("Section 11D", "cease-and-desist power confused with restitution of gains"),
     ("Section 15JB", "settlement power; disgorgement there is only part of a consent term")],
    ["s.11B(1) empowers the Board to issue directions in the interest of investors or the securities market.",
     "The Explanation (Securities Laws (Amendment) Act, 2014, deemed effective from 18 July 2013) clarifies that this includes directing any person to disgorge an amount equivalent to the wrongful gain made or loss averted.",
     "s.15HA is a penalty adjudicated by the AO — separate from disgorgement."],
    "s.11B(1) Explanation", "Disgorgement is remedial, not a penalty.", "conceptual",
    f"{SEBI}, s.11B(1) Explanation (2014)")

add("S2", "L2",
    "Pending investigation into suspicious trades by Orbit Capital Ltd, SEBI wants to act immediately by an interim order. Which of the following is a measure available to SEBI under section 11(4)?",
    "Impound and retain proceeds of a transaction under investigation",
    [("Impose a monetary penalty under s.15HA without an adjudicating officer", "penalty requires AO adjudication under s.15-I"),
     ("Order the winding up of Orbit Capital Ltd", "winding up lies with the NCLT, not SEBI"),
     ("Sentence the directors to civil imprisonment till inquiry ends", "only a court can imprison; recovery arrest is under s.28A after default")],
    ["s.11(4) allows SEBI, by order, pending investigation or inquiry, to suspend trading, restrain persons from accessing the market, suspend office-bearers of an exchange or SRO, impound and retain proceeds or securities of a transaction under investigation, attach bank accounts (for a limited period) and direct intermediaries not to dispose of assets.",
     "Penalties need adjudication; winding up and imprisonment lie with other fora."],
    "s.11(4) interim measures", "Interim protective measures ≠ final penal action.", "conceptual",
    f"{SEBI}, s.11(4)")

corpus = 120 * CRORE
add("S2", "L2",
    f"Greenleaf Agro, not registered with SEBI, pools {amt(corpus)} from the public for a teak-plantation scheme that promises returns from sale of timber. Under section 11AA, the scheme:",
    "Is deemed a CIS, since corpus is ₹100 crore or more",
    [("Is a CIS only if its corpus exceeds ₹500 crore", "wrong deemed-CIS threshold"),
     ("Is a deposit scheme regulated only by the RBI", "other regulator's jurisdiction wrongly invoked"),
     ("Is outside s.11AA because it is not a mutual fund", "confuses CIS with mutual fund schemes")],
    ["s.11AA(2A) (2014): any pooling of funds under a scheme not registered with the Board, involving a corpus of ₹100 crore or more, is deemed to be a collective investment scheme.",
     f"Corpus {amt(corpus)} ≥ ₹100 crore; plantation schemes are not in the s.11AA(3) exclusions.",
     "So it is a deemed CIS and requires registration under s.12(1B)."],
    "Deemed CIS: unregistered pooling with corpus ≥ ₹100 crore", "The deeming test is independent of the s.11AA(2) conditions.",
    "conceptual", f"{SEBI}, s.11AA(2A) (2014)")

add("S2", "L2",
    "Consider the following statements about registration under section 12 of the SEBI Act:\n\n"
    "1. A depository and a depository participant require a certificate of registration under s.12(1A).\n"
    "2. No person may sponsor or carry on a mutual fund without registration under s.12(1B).\n"
    "3. SEBI may cancel a certificate of registration without giving the holder an opportunity of hearing if the default is serious." + ST,
    "1 and 2 only",
    [("1 only", "s.12(1B) coverage of mutual funds missed"),
     ("1, 2 and 3", "s.12(3) hearing requirement ignored"),
     ("2 and 3 only", "depositories wrongly placed outside s.12")],
    ["s.12(1A) covers depositories, participants, custodians, FPIs and credit rating agencies — statement 1 true.",
     "s.12(1B) covers venture capital funds and collective investment schemes including mutual funds — statement 2 true.",
     "s.12(3): suspension/cancellation only after a reasonable opportunity of being heard — statement 3 false."],
    "s.12(1), (1A), (1B), (3)", "Natural justice is written into s.12(3).", "statement",
    f"{SEBI}, s.12")

ord_dt, rec_dt = date(2026, 1, 9), date(2026, 1, 19)
last = rec_dt + timedelta(45)
assert last == date(2026, 3, 5)
add("S4", "L2",
    f"A WTM order against Zeal Traders is dated {d(ord_dt)}; the copy is received by Zeal on {d(rec_dt)}. Without seeking condonation, the last date for filing an appeal before SAT under section 15T is:",
    d(last),
    [(d(ord_dt + timedelta(45)), "45 days counted from the order date instead of receipt"),
     (d(rec_dt + timedelta(30)), "30-day period assumed"),
     (d(rec_dt + timedelta(60)), "60-day Supreme Court appeal period applied")],
    ["s.15T: appeal within 45 days from the date on which a copy of the order is received.",
     f"{d(rec_dt)} + 45 days = {d(last)} (day of receipt excluded).",
     "SAT may entertain a later appeal on sufficient cause."],
    "Last date = Date of receipt + 45 days", "Clock runs from receipt of copy, not order date.", "numerical",
    f"{SEBI}, s.15T")

add("S4", "L2",
    "Arvind fails to pay a penalty of ₹40 lakh imposed by an adjudicating officer. Which of the following is **NOT** a mode of recovery available to the Recovery Officer under section 28A?",
    "Compounding the default on payment of a fee",
    [("Attachment and sale of Arvind's movable property", "listed in s.28A(1)(a)"),
     ("Arrest of Arvind and his detention in prison", "listed in s.28A(1)(d)"),
     ("Appointing a receiver for Arvind's properties", "listed in s.28A(1)(e)")],
    ["s.28A (2014) lets the Recovery Officer draw up a certificate and recover by attachment and sale of movable/immovable property, attachment of bank accounts, arrest and detention, and appointing a receiver.",
     "Compounding of offences is under s.24A (by SAT or the court where proceedings are pending), not a recovery mode."],
    "s.28A recovery modes", "Compounding (s.24A) relates to offences, not recovery of dues.", "conceptual",
    f"{SEBI}, s.28A (2014)")

# ---- L3 ----
add("S1", "L3",
    "Consider the following statements about the Board of SEBI under section 4:\n\n"
    "1. Two members are drawn from officials of the Ministry dealing with Finance and administration of company law.\n"
    "2. One member is drawn from officials of the Reserve Bank of India.\n"
    "3. All five 'other' members must be whole-time members." + ST,
    "1 and 2 only",
    [("1, 2 and 3", "'at least three' whole-time read as 'all five'"),
     ("2 only", "Government nominees wrongly limited to one Ministry"),
     ("2 and 3 only", "Ministry nominees missed and whole-time rule misread")],
    ["s.4(1)(b): two members from the Ministry dealing with Finance and administration of company law — true.",
     "s.4(1)(c): one member from RBI officials — true.",
     "s.4(1)(d): five other members, of whom at least three shall be whole-time — so 'all five' is false."],
    "s.4(1)", "'At least three' leaves room for part-time members.", "statement", f"{SEBI}, s.4(1)")

add("S1", "L3",
    "Consider the following statements about SEBI's functions under section 11(2):\n\n"
    "1. Calling for information from any bank or other authority in respect of transactions in securities under investigation.\n"
    "2. Levying fees or other charges for carrying out the purposes of the section.\n"
    "3. Regulating the acceptance of deposits by banking companies." + ST,
    "1 and 2 only",
    [("1 only", "fee-levy power under s.11(2)(k) missed"),
     ("2 and 3 only", "information power missed; bank deposits wrongly assigned to SEBI"),
     ("1, 2 and 3", "RBI's banking-regulation function attributed to SEBI")],
    ["s.11(2)(ia): calling for information from any bank or other authority for transactions under investigation — true.",
     "s.11(2)(k): levying fees or other charges — true.",
     "Deposit acceptance by banks is regulated by RBI under the BR Act — false for SEBI."],
    "s.11(2)", "Other regulator's power is a classic distractor.", "statement", f"{SEBI}, s.11(2)")

rows = [("P", "15G — insider trading"), ("Q", "15HA — fraudulent/unfair trade practices"),
        ("R", "15C — failure to redress investor grievances"), ("S", "15HB — residual contravention")]
cols = ["1. Not less than ₹10 lakh; up to ₹25 crore or 3× profit, whichever higher",
        "2. Not less than ₹5 lakh; up to ₹25 crore or 3× profit, whichever higher",
        "3. Not less than ₹1 lakh; ₹1 lakh per day of failure, max ₹1 crore",
        "4. Not less than ₹1 lakh; up to ₹1 crore"]
tbl = "| Section | Penalty band |\n|---|---|\n" + "\n".join(f"| {a}. {b} | {c} |" for (a, b), c in zip(rows, cols))
add("S3", "L3",
    f"Match the penalty section with its penalty band:\n\n{tbl}\n\nCodes (P-Q-R-S):",
    "P-1, Q-2, R-3, S-4",
    [("P-2, Q-1, R-3, S-4", "insider-trading and fraud floors (₹10 lakh / ₹5 lakh) swapped"),
     ("P-1, Q-2, R-4, S-3", "daily-default band given to the residual section"),
     ("P-2, Q-1, R-4, S-3", "both pairs swapped")],
    ["s.15G: ₹10 lakh floor; ₹25 crore or 3× profit.", "s.15HA: ₹5 lakh floor; ₹25 crore or 3× profit.",
     "s.15C: ₹1 lakh floor; ₹1 lakh/day; cap ₹1 crore.", "s.15HB: ₹1 lakh to ₹1 crore."],
    "Chapter VIA bands (post-2014)", "Only the floors distinguish 15G from 15HA.", "match",
    f"{SEBI}, ss.15C, 15G, 15HA, 15HB (as amended 2014)")

g_days, f_days = 64, 180
g_hi = daily(g_days)[1]; f_hi = daily(f_days)[1]; hb = CRORE
tot = g_hi + f_hi + hb
assert tot == 2.64 * CRORE
add("S3", "L3",
    f"An AO finds that Pinnacle Registrars Ltd (a) failed to redress investor grievances for **{g_days} days** after SEBI's direction, (b) failed to furnish returns to SEBI for **{f_days} days**, and (c) committed a contravention for which no separate penalty is provided. The **maximum aggregate** penalty that can be adjudged is:",
    amt(tot),
    [(amt(LAKH * (g_days + f_days) + hb), "₹1 crore cap under s.15A ignored for the 180-day failure"),
     (amt(g_hi + f_hi), "residual s.15HB penalty omitted"),
     (amt(CRORE), "single ₹1 crore cap applied across all heads")],
    [f"(a) s.15C: min(₹1 lakh × {g_days}, ₹1 crore) = {amt(g_hi)}.",
     f"(b) s.15A: min(₹1 lakh × {f_days}, ₹1 crore) = {amt(f_hi)}.",
     f"(c) s.15HB: up to {amt(hb)}.",
     f"Aggregate maximum = {amt(g_hi)} + {amt(f_hi)} + {amt(hb)} = {amt(tot)}."],
    "Σ head-wise maxima; each daily head capped at ₹1 crore", "Caps apply per head, not overall.", "numerical",
    f"{SEBI}, ss.15A, 15C, 15HB (as amended 2014)")

gx, gy = 10 * CRORE, 7 * CRORE
mx_x, mx_y = higher_of(25 * CRORE, 3, gx), higher_of(25 * CRORE, 3, gy)
assert (mx_x, mx_y) == (30 * CRORE, 25 * CRORE)
add("S3", "L3",
    f"In a takeover matter, (i) Mr X failed to make disclosures required under the takeover regulations and made gains of {amt(gx)}; (ii) Ms Y engaged in fraudulent trades and made a profit of {amt(gy)}. The sum of the **maximum** penalties adjudicable on X (s.15H) and Y (s.15HA) is:",
    amt(mx_x + mx_y),
    [(amt(3 * gx + 3 * gy), "3× gain applied to both without comparing with ₹25 crore"),
     (amt(50 * CRORE), "₹25 crore taken for both, ignoring 3× gain for X"),
     (amt(mx_x + 5 * gy), "5× multiple (s.15F contract-note rule) used for Y")],
    [f"X, s.15H: higher of ₹25 crore and 3 × {amt(gx)} = {amt(3*gx)} → {amt(mx_x)}.",
     f"Y, s.15HA: higher of ₹25 crore and 3 × {amt(gy)} = {amt(3*gy)} → {amt(mx_y)}.",
     f"Sum = {amt(mx_x + mx_y)}."],
    "Max = max(₹25 crore, 3 × gain) per person", "Compare separately for each person.", "numerical",
    f"{SEBI}, ss.15H, 15HA")

add("S3", "L3",
    "**Assertion (A):** A penalty of ₹3 crore adjudged under section 15HA and paid by the noticee is credited to the General Fund of SEBI.\n\n"
    "**Reason (R):** Under section 15JA, all sums realised by way of penalties under the SEBI Act are credited to the Consolidated Fund of India.",
    AR[3], [(AR[0], "assumes penalties fund SEBI's own budget"), (AR[1], "fails to see that R contradicts A"),
            (AR[2], "reverses the truth values of A and R")],
    ["s.15JA: sums realised by way of penalties are credited to the Consolidated Fund of India.",
     "So A is false and R is true.", "SEBI's General Fund (s.14) receives grants, fees and charges — not penalties."],
    "s.15JA", "Penalties → Consolidated Fund of India; fees → SEBI's fund.", "assertion-reason",
    f"{SEBI}, s.15JA, s.14")

ao, disp = date(2026, 1, 12), date(2026, 3, 20)
lim = min(add_months(ao, 3), disp)
assert lim == disp
add("S3", "L3",
    f"An AO order dated {d(ao)} imposed a penalty that SEBI considers erroneous and not in the interest of the securities market. The noticee's appeal was disposed of by SAT on {d(disp)}. Under the proviso to section 15-I(3), SEBI's revisional power could be exercised only up to:",
    d(lim),
    [(d(add_months(ao, 3)), "three months from the AO order, ignoring 'whichever is earlier'"),
     (d(add_months(disp, 3)), "three months counted from SAT's disposal"),
     (d(add_months(ao, 6)), "six-month window assumed")],
    ["s.15-I(3): the Board may call for records and revise an AO order that is erroneous and not in the interest of the market (after hearing).",
     "The power cannot be exercised after three months from the AO order or the disposal of appeal under s.15T, whichever is earlier.",
     f"Earlier of {d(add_months(ao, 3))} and {d(disp)} = {d(lim)}."],
    "Window ends at min(AO order + 3 months, appeal disposal)", "'Whichever is earlier' shortens the window.", "numerical",
    f"{SEBI}, s.15-I(3) proviso")

# ---- L4 case: Kestrel ----
cn, xb, fd = 36 * LAKH, 2.8 * LAKH, 52
rec_ao, sat_rec, sat_comm = date(2026, 2, 23), date(2026, 3, 30), date(2026, 11, 2)
case = ("**Case — Kestrel Stock Broking Ltd (fictional)**\n\n"
        "SEBI's inspection of Kestrel, a registered stock broker, found:\n\n"
        "| Finding | Detail |\n|---|---|\n"
        f"| (a) Contract notes not issued | Trades in securities of aggregate value {amt(cn)} |\n"
        f"| (b) Brokerage charged above the permitted limit | Excess brokerage {amt(xb)} |\n"
        f"| (c) Information called for by SEBI not furnished | Failure continued {fd} days |\n\n"
        f"An adjudicating officer passed a penalty order; Kestrel received a copy on {d(rec_ao)}. "
        f"Kestrel's appeal reached SAT on {d(sat_rec)}. SAT's final decision was communicated to Kestrel on {d(sat_comm)}.")
G1 = "ACTS-CASE-KESTREL"
a_hi = 5 * cn
assert a_hi == 1.8 * CRORE
add("S3", "L4", case + "\n\nFor finding (a) alone, the **maximum** penalty under section 15F(a) is:",
    amt(a_hi),
    [(amt(CRORE), "₹1 crore daily-default cap applied to contract notes"),
     (amt(3 * cn), "3× multiple of ss.15G/15HA applied"),
     (amt(cn), "value of securities itself taken as ceiling")],
    ["s.15F(a): failure to issue contract notes — penalty not less than ₹1 lakh, extending to five times the value of securities for which contract notes were required.",
     f"5 × {amt(cn)} = {amt(a_hi)}."],
    "Max = 5 × value of securities", "Contract-note penalty is value-linked, not day-linked.", "numerical",
    f"{SEBI}, s.15F(a)", group=G1)

b_hi, c_hi = 5 * xb, daily(fd)[1]
tot = a_hi + b_hi + c_hi
assert round(tot) == round(2.46 * CRORE)
add("S3", "L4", case + "\n\nThe **maximum aggregate** penalty across findings (a), (b) and (c) is:",
    amt(tot),
    [(amt(min(a_hi, CRORE) + b_hi + c_hi), "finding (a) wrongly capped at ₹1 crore"),
     (amt(3 * cn + 3 * xb + c_hi), "3× multiple used for (a) and (b)"),
     (amt(a_hi + xb + c_hi), "excess brokerage itself taken as ceiling for (b)")],
    [f"(a) s.15F(a): 5 × {amt(cn)} = {amt(a_hi)}.",
     f"(b) s.15F(c): up to five times the excess brokerage = 5 × {amt(xb)} = {amt(b_hi)}.",
     f"(c) s.15A: min(₹1 lakh × {fd}, ₹1 crore) = {amt(c_hi)}.",
     f"Total = {amt(tot)}."],
    "Σ [5 × value] + [5 × excess brokerage] + [₹1 lakh × days, ≤ ₹1 crore]", "Each head has its own base.",
    "numerical", f"{SEBI}, ss.15A, 15F(a), 15F(c)", group=G1)

endeav = add_months(sat_rec, 6)
add("S4", "L4", case + "\n\nUnder section 15T, SAT shall endeavour to dispose of Kestrel's appeal finally by:",
    d(endeav),
    [(d(sat_rec + timedelta(45)), "45-day filing period confused with disposal target"),
     (d(add_months(sat_rec, 3)), "three-month target assumed"),
     (d(add_months(sat_rec, 12)), "one-year target assumed")],
    ["s.15T: SAT shall deal with the appeal as expeditiously as possible and endeavour to dispose of it within six months from the date of receipt of the appeal.",
     f"{d(sat_rec)} + 6 months = {d(endeav)}."],
    "Disposal target = Receipt of appeal + 6 months", "It is a directory target, not a bar.", "numerical",
    f"{SEBI}, s.15T", group=G1)

outer = sat_comm + timedelta(120)
add("S4", "L4", case + "\n\nKestrel wishes to challenge SAT's decision in the Supreme Court. If sufficient cause for delay is shown, the **latest** date up to which the appeal can be entertained is:",
    d(outer),
    [(d(sat_comm + timedelta(60)), "further 60-day extension ignored"),
     (d(sat_comm + timedelta(90)), "extension taken as 30 days"),
     (d(sat_comm + timedelta(105)), "45-day SAT period plus 60 days used")],
    ["s.15Z: appeal within 60 days from communication of SAT's decision.",
     "Supreme Court may allow a further period not exceeding 60 days on sufficient cause.",
     f"Outer limit = {d(sat_comm)} + 120 days = {d(outer)}."],
    "Outer limit = Communication + 60 + 60 days", "Condonation is capped at 60 extra days.", "numerical",
    f"{SEBI}, s.15Z", group=G1)

add("S4", "L4", case + "\n\nBefore the AO's order, Kestrel had considered settling. Consider:\n\n"
    "1. Kestrel could have filed an application for settlement of the pending adjudication proceedings under section 15JB.\n"
    "2. A settlement order passed under section 15JB is appealable to SAT under section 15T.\n"
    "3. In fixing the quantum of penalty, the AO must have regard to factors such as disproportionate gain, loss to investors and the repetitive nature of default." + ST,
    "1 and 3 only",
    [("1 and 2 only", "overlooks the bar on appeals against settlement orders"),
     ("1, 2 and 3", "treats settlement orders as appealable"),
     ("3 only", "settlement wrongly thought unavailable for adjudication proceedings")],
    ["s.15JB(1): a person against whom proceedings are initiated or may be initiated may apply for settlement — true.",
     "s.15JB: no appeal lies under s.15T against a settlement order — statement 2 false.",
     "s.15J lists disproportionate gain, loss to investors and repetitive nature of default — true."],
    "ss.15J, 15JB", "Settlement is consensual, hence non-appealable.", "statement",
    f"{SEBI}, ss.15J, 15JB (2014)", group=G1)

# =====================================================================================
# SCRA, 1956 (+ SCRR, 1957) — 24 Q  (L1 5 · L2 7 · L3 7 · L4 5)
# =====================================================================================
# ---- L1 ----
add("C1", "L1",
    "Under section 2(i) of the SCRA, a 'spot delivery contract' is one providing for actual delivery of securities and payment of price:",
    "Same day or the next day (transit time excluded)",
    [("Within the T+1 rolling settlement cycle only", "exchange settlement practice confused with the statutory definition"),
     ("Within seven days of the contract date", "arbitrary seven-day window"),
     ("Within fourteen days of the contract date", "arbitrary fourteen-day window")],
    ["s.2(i): delivery and payment either on the same day as the contract or on the next day.",
     "Where parties are in different places, the actual time taken for dispatch of securities or remittance is excluded."],
    "s.2(i)", "The statutory definition predates exchange settlement cycles.", "conceptual", f"{SCRA}, s.2(i)")

add("C1", "L1",
    "Which of the following is expressly included in the definition of 'option in securities' under section 2(d) of the SCRA?",
    "Teji-mandi", [("Badla", "carry-forward system, not an option"),
                   ("Ready forward", "repo-type contract, not an option"),
                   ("Spot delivery", "separately defined in s.2(i)")],
    ["s.2(d): 'option in securities' is a contract for purchase or sale of a right to buy or sell, or both, securities in future.",
     "It includes a teji, a mandi, a teji mandi, a galli, a put, a call or a put and call."],
    "s.2(d)", "Badla is a carry-forward, not a right without obligation.", "conceptual", f"{SCRA}, s.2(d)")

add("C2", "L1",
    "Under section 11 of the SCRA, when the governing body of a recognised stock exchange is superseded, the supersession may be for a period not exceeding:",
    "Six months", [("Seven days", "s.12 suspension-of-business period"),
                   ("Three months", "understated period"),
                   ("One year", "overstated period")],
    ["s.11: the Central Government (SEBI concurrently) may supersede the governing body for a period not exceeding six months, after giving an opportunity of being heard.",
     "s.12 is the separate emergency suspension of business for up to seven days (extendable)."],
    "s.11", "s.11 (supersede, ≤ 6 months) vs s.12 (suspend, ≤ 7 days).", "conceptual", f"{SCRA}, s.11")

add("C3", "L1",
    "Section 18A of the SCRA makes contracts in derivatives legal and valid, notwithstanding any other law, if they are:",
    "Traded on a recognised stock exchange and settled on its clearing house",
    [("Entered into between any two SEBI-registered brokers off the exchange", "bilateral OTC trades not covered by s.18A"),
     ("Approved in advance by the RBI under the RBI Act", "other regulator's (s.45V RBI Act) route confused"),
     ("Settled within the spot delivery period of s.2(i)", "spot delivery test confused with derivative legality")],
    ["s.18A (1999): derivatives are legal and valid if (a) traded on a recognised stock exchange and (b) settled on the clearing house of the recognised stock exchange, per its rules and bye-laws."],
    "s.18A", "Both limbs — exchange trading and exchange clearing.", "conceptual", f"{SCRA}, s.18A")

add("C4", "L1",
    "Under rule 19A of the SCRR, 1957, every listed company other than a public sector company shall maintain public shareholding of at least:",
    "25%", [("10%", "minimum offer size for large issuers confused with continuous requirement"),
            ("20%", "understated threshold"),
            ("35%", "overstated threshold")],
    ["Rule 19A(1): every listed company (other than a PSU) shall maintain public shareholding of at least 25%.",
     "Rule 19A(2): if it falls below, restore within a maximum of twelve months."],
    "SCRR r.19A(1)", "The continuous MPS is 25%, regardless of the initial offer size.", "conceptual",
    f"{SCRA} read with SCRR, 1957, r.19A")

# ---- L2 ----
add("C1", "L2",
    "Which of the following is **NOT** 'securities' under section 2(h) of the SCRA?",
    "A fixed deposit receipt issued by a bank",
    [("A security receipt issued under the SARFAESI Act", "expressly included in s.2(h)"),
     ("A unit issued under a mutual fund scheme", "expressly included in s.2(h)"),
     ("A contract deriving value from a stock index", "a derivative — expressly included")],
    ["s.2(h) includes shares, bonds, debentures, derivatives, CIS units, SARFAESI security receipts, MF units, securitised debt instruments, Government securities and rights or interest in securities.",
     "A bank FD receipt is a deposit, not a marketable security."],
    "s.2(h)", "Marketability and listing-ability distinguish securities from deposits.", "conceptual", f"{SCRA}, s.2(h)")

add("C2", "L2",
    "Violent speculation triggers an emergency. The Central Government (SEBI concurrently) directs a recognised stock exchange to suspend its business under section 12 of the SCRA. The initial period of suspension cannot exceed:",
    "Seven days, extendable",
    [("Six months, non-extendable", "s.11 supersession period confused"),
     ("Fifteen days, extendable once", "wrong period and extension rule"),
     ("Seven days, not extendable", "extension power missed")],
    ["s.12: in an emergency, the exchange may be directed to suspend business for a period not exceeding seven days.",
     "The period may be extended from time to time in the interest of trade or the public."],
    "s.12", "Suspension ≤ 7 days (extendable) vs supersession ≤ 6 months.", "conceptual", f"{SCRA}, s.12")

dd = 23
lo, hi = daily(dd)
add("C5", "L2",
    f"A stock broker fails to furnish a periodical return to the recognised stock exchange; the failure continues for **{dd} days**. The penalty range under section 23A is:",
    f"{amt(lo)} to {amt(hi)}",
    [(f"{amt(5*LAKH)} to {amt(25*CRORE)}", "s.23E listing-failure band applied"),
     (f"{amt(lo)} to {amt(CRORE)}", "residual s.23H band applied"),
     (f"Nil to {amt(hi)}", "pre-2014 formula with no minimum")],
    ["s.23A (post-2014): not less than ₹1 lakh, up to ₹1 lakh per day of failure, max ₹1 crore.",
     f"Upper = ₹1 lakh × {dd} = {amt(hi)}."],
    "Penalty ∈ [₹1 lakh, min(₹1 lakh × days, ₹1 crore)]", "The specific section excludes the residual one.", "numerical",
    f"{SCRA}, s.23A (as amended 2014)")

add("C5", "L2",
    "Alpine Foods Ltd, a listed company, breaches the conditions of listing. The maximum penalty that can be adjudged under section 23E of the SCRA is:",
    "₹25 crore",
    [("₹1 crore", "residual s.23H ceiling applied"),
     ("₹25 crore or 3× gains, whichever higher", "SEBI Act s.15G/15HA formula imported"),
     ("₹1 lakh per day up to ₹1 crore", "s.23A daily-default formula applied")],
    ["s.23E: failure to comply with listing conditions or delisting conditions or grounds — penalty not less than ₹5 lakh, up to ₹25 crore."],
    "s.23E: ₹5 lakh – ₹25 crore", "No '3× gain' limb in s.23E.", "conceptual", f"{SCRA}, s.23E")

dl = date(2026, 5, 4)
lastd = dl + timedelta(15)
add("C4", "L2",
    f"A recognised stock exchange decides on {d(dl)} to delist the shares of Kiran Textiles Ltd. Without seeking condonation, the last date for an appeal to SAT under section 21A(2) is:",
    d(lastd),
    [(d(dl + timedelta(45)), "45-day SAT appeal period of SEBI Act s.15T used"),
     (d(dl + timedelta(30)), "30-day period assumed"),
     (d(dl + timedelta(60)), "60-day Supreme Court appeal period applied")],
    ["s.21A(2): listed company or aggrieved investor may appeal to SAT within 15 days from the date of the exchange's decision to delist.",
     f"{d(dl)} + 15 days = {d(lastd)}.", "SAT may allow a further period not exceeding one month on sufficient cause."],
    "Last date = Decision date + 15 days", "Delisting appeals have the short 15-day window.", "numerical",
    f"{SCRA}, s.21A(2)")

add("C3", "L2",
    "The Central Government has notified section 13 of the SCRA for Region Z. Two investors in Region Z, neither a member of a recognised stock exchange, agree directly (not through any member) to sell listed shares with delivery and payment 20 days later. The contract is:",
    "Void under section 13",
    [("Valid, because s.18 excludes all contracts between non-members", "s.18 excludes spot delivery contracts, not all contracts"),
     ("Valid, as s.13 applies only to derivatives", "confuses s.13 with s.18A"),
     ("Voidable at the option of the buyer", "void-ab-initio consequence misstated")],
    ["s.13: in a notified area, every contract otherwise than between members of a recognised stock exchange, or through or with such a member, is void.",
     "s.18 exempts spot delivery contracts; delivery after 20 days is not spot delivery (s.2(i)).",
     "Hence the contract is void."],
    "s.13 read with s.18 and s.2(i)", "Check the delivery period before applying the s.18 exclusion.", "conceptual",
    f"{SCRA}, ss.13, 18")

add("C2", "L2",
    "Consider the following statements:\n\n"
    "1. A recognised stock exchange may make bye-laws for the regulation and control of contracts, subject to the previous approval of SEBI.\n"
    "2. SEBI may, on its own motion, make bye-laws on matters in section 9 or amend the bye-laws of a recognised stock exchange.\n"
    "3. Bye-laws of a recognised stock exchange require the approval of Parliament before they take effect." + ST,
    "1 and 2 only",
    [("1 only", "SEBI's s.10 power missed"),
     ("2 and 3 only", "s.9 exchange power missed; Parliament wrongly inserted"),
     ("1, 2 and 3", "subordinate bye-laws treated as needing Parliament's approval")],
    ["s.9: exchange bye-laws subject to previous approval of SEBI — true.",
     "s.10: SEBI may make or amend bye-laws on request or on its own motion — true.",
     "No Parliamentary approval is required for exchange bye-laws — false."],
    "ss.9, 10", "Bye-laws are subordinate instruments approved by SEBI.", "statement", f"{SCRA}, ss.9, 10")

# ---- L3 ----
add("C1", "L3",
    "Consider the following about 'derivative' under section 2(ac) of the SCRA:\n\n"
    "1. Commodity derivatives are excluded from the definition and remain regulated under the Forward Contracts (Regulation) Act.\n"
    "2. It includes a contract which derives its value from the prices, or index of prices, of underlying securities.\n"
    "3. It includes a security derived from a loan, whether secured or unsecured." + ST,
    "2 and 3 only",
    [("1 and 2 only", "pre-2015 position before the FCRA repeal and FMC–SEBI merger"),
     ("2 only", "security-derived-from-loan limb missed"),
     ("1, 2 and 3", "commodity derivatives exclusion wrongly accepted")],
    ["Finance Act, 2015 repealed the FCRA and added commodity derivatives to s.2(ac) — statement 1 false.",
     "s.2(ac)(B): contract deriving value from prices/index of underlying securities — true.",
     "s.2(ac)(A): security derived from debt instrument, share, loan (secured or unsecured), risk instrument or CFD — true."],
    "s.2(ac)", "Pre-amendment law is a favourite distractor.", "statement", f"{SCRA}, s.2(ac) (as amended 2015)")

rows = [("P", "Section 4"), ("Q", "Section 5"), ("R", "Section 11"), ("S", "Section 12")]
cols = ["1. Withdrawal of recognition; prior contracts remain valid", "2. Grant of recognition to a stock exchange",
        "3. Suspension of business in an emergency", "4. Supersession of governing body"]
tbl = "| SCRA | Subject |\n|---|---|\n" + "\n".join(f"| {a}. {b} | {c} |" for (a, b), c in zip(rows, cols))
add("C2", "L3", f"Match the SCRA section with its subject:\n\n{tbl}\n\nCodes (P-Q-R-S):",
    "P-2, Q-1, R-4, S-3",
    [("P-1, Q-2, R-4, S-3", "grant and withdrawal swapped"),
     ("P-2, Q-1, R-3, S-4", "supersession and suspension swapped"),
     ("P-1, Q-2, R-3, S-4", "both pairs swapped")],
    ["s.4 grant of recognition; s.5 withdrawal (contracts before the notification unaffected).",
     "s.11 supersession of governing body (≤ 6 months); s.12 suspension of business (≤ 7 days)."],
    "ss.4, 5, 11, 12", "Adjacent sections pair up as opposites.", "match", f"{SCRA}, ss.4, 5, 11, 12")

fdays = 150
t = 25 * CRORE + daily(fdays)[1]
add("C5", "L3",
    f"Ravi Engineering Ltd, listed, (i) breached listing conditions and (ii) failed to file returns with SEBI for **{fdays} days**. The **maximum aggregate** penalty adjudicable under sections 23E and 23A is:",
    amt(t),
    [(amt(25 * CRORE + LAKH * fdays), "₹1 crore cap under s.23A ignored"),
     (amt(CRORE + daily(fdays)[1]), "s.23E ceiling taken as ₹1 crore (s.23H)"),
     (amt(5 * LAKH + daily(fdays)[1]), "s.23E minimum (₹5 lakh) taken as the ceiling")],
    ["(i) s.23E: up to ₹25 crore.", f"(ii) s.23A: min(₹1 lakh × {fdays}, ₹1 crore) = {amt(daily(fdays)[1])}.",
     f"Total = {amt(t)}."],
    "Σ head-wise maxima", "Daily heads are capped at ₹1 crore.", "numerical", f"{SCRA}, ss.23A, 23E")

add("C2", "L3",
    "**Assertion (A):** A contract entered into on a recognised stock exchange before the date of the notification withdrawing its recognition remains valid.\n\n"
    "**Reason (R):** Before withdrawing recognition, the governing body of the exchange must be given an opportunity of being heard.",
    AR[1], [(AR[0], "hearing requirement wrongly treated as the basis for saving contracts"),
            (AR[2], "hearing requirement of s.5(1) overlooked"),
            (AR[3], "saving clause of s.5 overlooked")],
    ["s.5(1): withdrawal only after an opportunity of being heard — R true.",
     "s.5 saving clause: withdrawal does not affect the validity of contracts entered into before the notification — A true.",
     "The saving of prior contracts flows from the express saving clause, not from the hearing requirement."],
    "s.5", "Two true propositions need not be causally linked.", "assertion-reason", f"{SCRA}, s.5")

add("C3", "L3",
    "Consider the following statements:\n\n"
    "1. Options in securities remain prohibited under section 20 of the SCRA.\n"
    "2. Section 18 excludes spot delivery contracts from the operation of section 13.\n"
    "3. A derivative traded on a recognised stock exchange and settled on its clearing house is legal notwithstanding anything in any other law." + ST,
    "2 and 3 only",
    [("1 and 2 only", "relies on s.20, omitted in 1995"),
     ("1, 2 and 3", "omission of s.20 missed"),
     ("3 only", "s.18 exclusion of spot delivery contracts missed")],
    ["s.20 (prohibition of options) was omitted by the Securities Laws (Amendment) Act, 1995 — statement 1 false.",
     "s.18 excludes spot delivery contracts from ss.13, 14, 15 and 17 — true.",
     "s.18A — true."],
    "ss.18, 18A; s.20 omitted (1995)", "Repealed sections are common distractors.", "statement",
    f"{SCRA}, ss.18, 18A, s.20 (omitted 1995)")

T, PR, DR, SUB = 5_00_00_000, 3_70_00_000, 20_00_000, 5_00_000
PUB = T - PR - DR - SUB
p_ok = PUB / T
assert PUB == 1_05_00_000 and abs(p_ok - 0.21) < 1e-12
tbl = ("| Holder | Equity shares |\n|---|---:|\n"
       f"| Promoter and promoter group | {inr(PR)} |\n| Custodian against GDRs issued overseas | {inr(DR)} |\n"
       f"| A subsidiary of the company | {inr(SUB)} |\n| Other shareholders | {inr(PUB)} |\n| **Total** | **{inr(T)}** |")
add("C4", "L3",
    f"Shareholding of Sumeru Chemicals Ltd:\n\n{tbl}\n\nPublic shareholding for rule 19A of the SCRR is:",
    pct(p_ok),
    [(pct((PUB + DR + SUB) / T), "custodian (GDR) and subsidiary holdings counted as public"),
     (pct((PUB + SUB) / T), "subsidiary holding counted as public"),
     (pct(PUB / (T - DR)), "GDR shares excluded from the denominator as well")],
    ["Rule 2(e): 'public' excludes promoter and promoter group and subsidiaries/associates of the company.",
     "Rule 2(d): public shareholding excludes shares held by a custodian against depository receipts issued overseas.",
     f"Public = {inr(PUB)}; ÷ total {inr(T)} = {pct(p_ok)}."],
    "Public % = Public shares ÷ Total equity shares",
    "Exclusions reduce the numerator; the denominator stays total paid-up equity.", "numerical",
    "SCRR, 1957, r.2(d), r.2(e), r.19A")

add("C4", "L3",
    "Consider the following statements:\n\n"
    "1. A person whose securities are listed on a recognised stock exchange on his application must comply with the conditions of the listing agreement.\n"
    "2. An appeal against an exchange's decision to delist securities lies to the Central Government.\n"
    "3. Securities cannot be delisted unless the company has been given a reasonable opportunity of being heard." + ST,
    "1 and 3 only",
    [("1 and 2 only", "pre-2004 appellate forum; hearing proviso missed"),
     ("1, 2 and 3", "appeal forum misstated"),
     ("3 only", "s.21 listing obligation missed")],
    ["s.21: listed person to comply with listing conditions — true.",
     "s.21A(2): appeal lies to SAT, not the Central Government — false.",
     "s.21A(1) proviso: reasonable opportunity of being heard — true."],
    "ss.21, 21A", "Appeals in securities law go to SAT.", "statement", f"{SCRA}, ss.21, 21A")

# ---- L4 case: Vedant Polymers MPS ----
T, PR, DR, SUB = 8_00_00_000, 6_32_00_000, 24_00_000, 8_00_000
PUB = T - PR - DR - SUB
fall = date(2026, 8, 14)
assert PUB == 1_36_00_000
tbl = ("| Holder | Equity shares |\n|---|---:|\n"
       f"| Promoter and promoter group | {inr(PR)} |\n| Custodian against ADRs/GDRs | {inr(DR)} |\n"
       f"| Wholly owned subsidiary | {inr(SUB)} |\n| Other shareholders | {inr(PUB)} |\n| **Total** | **{inr(T)}** |")
case = ("**Case — Vedant Polymers Ltd (fictional)**\n\n"
        f"Vedant is a listed non-PSU company. On {d(fall)}, after its promoter completed an open offer, shareholding stood as follows:\n\n{tbl}")
G2 = "ACTS-CASE-VEDANT"
pp = PUB / T
assert abs(pp - 0.17) < 1e-12
add("C4", "L4", case + "\n\nVedant's public shareholding for rule 19A of the SCRR is:",
    pct(pp),
    [(pct((PUB + DR) / T), "custodian (DR) shares counted as public"),
     (pct((PUB + DR + SUB) / T), "custodian and subsidiary holdings counted as public"),
     (pct(PUB / (T - DR)), "DR shares removed from the denominator too")],
    ["Exclude promoter group, subsidiary and custodian-against-DR shares.", f"Public = {inr(PUB)} ÷ {inr(T)} = {pct(pp)}."],
    "Public % = Public shares ÷ Total equity", "Only 'other shareholders' count here.", "numerical",
    "SCRR, 1957, r.2(d), r.2(e), r.19A", group=G2)

dl = add_months(fall, 12)
add("C4", "L4", case + "\n\nThe latest date by which Vedant must restore public shareholding to 25% under rule 19A(2) is:",
    d(dl),
    [(d(add_months(fall, 36)), "three-year transition given in 2010 to then-listed companies"),
     (d(add_months(fall, 6)), "six-month period assumed"),
     (d(add_months(fall, 24)), "two-year period assumed")],
    ["Rule 19A(2): where public shareholding falls below 25% at any time, restore within a maximum of twelve months from the date of fall.",
     f"{d(fall)} + 12 months = {d(dl)}."],
    "Deadline = Date of fall + 12 months", "The 2010 three-year window applied only to companies then listed.", "numerical",
    "SCRR, 1957, r.19A(2)", group=G2)

need = 0.25 * T
ofs = need - PUB
assert ofs == 64_00_000
add("C4", "L4", case + "\n\nIf the promoter restores compliance only by an offer for sale (OFS) of existing shares to the public, the minimum number of shares to be sold is:",
    inr(ofs),
    [(inr(need - PUB - DR), "custodian (DR) shares counted as public"),
     (inr(0.25 * (T - DR) - PUB), "25% computed on equity excluding DR shares"),
     (inr(math.ceil(ofs / 0.75)), "fresh-issue formula applied to a transfer of existing shares")],
    [f"Required public = 25% × {inr(T)} = {inr(need)}.", f"Shortfall = {inr(need)} − {inr(PUB)} = {inr(ofs)}.",
     "An OFS moves shares from promoter to public; total equity is unchanged."],
    "OFS shares = 25% × Total − Existing public", "Total equity is constant in an OFS.", "numerical",
    "SCRR, 1957, r.19A", group=G2)

x = math.ceil((need - PUB) / 0.75)
assert (PUB + x) / (T + x) >= 0.25 and (PUB + x - 1) / (T + x - 1) < 0.25
add("C4", "L4", case + "\n\nIf instead Vedant issues **fresh** equity shares entirely to public investors (e.g. by QIP), the minimum number of new shares required is:",
    inr(x),
    [(inr(ofs), "OFS count used; enlarged equity base ignored"),
     (inr(x - 1), "rounded down; public stays just below 25%"),
     (inr(math.ceil((need - PUB) / 0.25)), "shortfall divided by 25% instead of 75%")],
    ["Let x new shares: (PUB + x) ÷ (T + x) = 25%.", f"x = (0.25 × {inr(T)} − {inr(PUB)}) ÷ 0.75 = {inr((need-PUB)/0.75, 2)}.",
     f"Round up to {inr(x)} (whole shares; must reach 25%)."],
    "x = (25% × T − P) ÷ (1 − 25%)", "Fresh issue enlarges the denominator.", "numerical",
    "SCRR, 1957, r.19A", group=G2)

add("C4", "L4", case + "\n\nVedant fails to meet the deadline; the exchange later delists its shares. Consider:\n\n"
    "1. The 25% requirement does not apply to Vedant because the promoter's stake rose through a regulated open offer.\n"
    "2. Failure to comply with listing conditions exposes the company to penalty under section 23E of up to ₹25 crore.\n"
    "3. An aggrieved investor may appeal the delisting to SAT within 15 days, and SAT may allow a further period of up to one month on sufficient cause." + ST,
    "2 and 3 only",
    [("1 and 2 only", "open offer wrongly treated as exempting MPS"),
     ("3 only", "s.23E exposure missed"),
     ("1, 2 and 3", "MPS exemption wrongly accepted")],
    ["Rule 19A(2) applies whenever public shareholding falls below 25% 'at any time' — statement 1 false.",
     "s.23E: ₹5 lakh to ₹25 crore for listing-condition failures — true.",
     "s.21A(2): 15 days + further period not exceeding one month — true."],
    "SCRR r.19A; SCRA ss.21A, 23E", "The MPS obligation is continuous.", "statement",
    f"{SCRA}, ss.21A, 23E; SCRR r.19A", group=G2)

# =====================================================================================
# DEPOSITORIES ACT, 1996 — 22 Q  (L1 4 · L2 7 · L3 7 · L4 4)
# =====================================================================================
# ---- L1 ----
add("D1", "L1",
    "For shares held in dematerialised form, whose name appears as 'registered owner' in the register of members of the issuer?",
    "The depository", [("The depository participant", "participant is only the depository's agent"),
                       ("The beneficial owner", "BO is recorded in the depository's register, not the issuer's"),
                       ("The custodian of securities", "custodian is a different intermediary")],
    ["s.2(1)(j): 'registered owner' means a depository whose name is entered as such in the register of the issuer.",
     "s.2(1)(a): 'beneficial owner' is the person whose name is recorded as such with a depository."],
    "s.2(1)(a), (j)", "Legal title (depository) vs beneficial interest (BO).", "conceptual", f"{DA}, s.2(1)(j)")

add("D1", "L1",
    "Before acting as a depository, a company registered under section 12(1A) of the SEBI Act must also obtain a certificate of commencement of business from:",
    "SEBI", [("Registrar of Companies", "company-law commencement confused"),
             ("Reserve Bank of India", "other regulator"),
             ("Ministry of Finance", "Government confused with the regulator")],
    ["s.3(1): no depository shall act as a depository unless it obtains a certificate of commencement of business from the Board.",
     "s.3(2): the certificate is granted only if the depository has adequate systems and safeguards against manipulation of records and transactions."],
    "s.3", "Registration (SEBI Act s.12(1A)) and commencement (DA s.3) are both with SEBI.", "conceptual", f"{DA}, s.3")

add("D2", "L1",
    "A beneficial owner opts out of a depository for certain shares. After receiving intimation from the depository, the issuer must issue the certificate of securities within:",
    "30 days", [("15 days", "confused with the delisting-appeal window"),
                ("Two months", "Companies Act allotment-certificate timeline"),
                ("45 days", "confused with the SAT appeal period")],
    ["s.14(1): BO informs the depository; depository makes entries and informs the issuer.",
     "s.14(2): issuer, within thirty days of receipt of the information and on fulfilment of conditions/fees, issues the certificate to the BO or transferee."],
    "s.14(2)", "Opting out is a right; the issuer's timeline is 30 days.", "conceptual", f"{DA}, s.14")

add("D1", "L1", "Under section 2(1)(e) of the Depositories Act, a 'depository' is:",
    "A company registered under s.12(1A) SEBI Act",
    [("Any bank licensed by the RBI to hold securities", "other regulator's licensing confused"),
     ("A clearing corporation of a stock exchange", "clearing corporation (SCRA s.8A) confused"),
     ("A trust registered with SEBI as custodian", "custodian confused with depository")],
    ["s.2(1)(e): a company formed and registered under the Companies Act and granted a certificate of registration under s.12(1A) of the SEBI Act."],
    "s.2(1)(e)", "A depository must be a company.", "conceptual", f"{DA}, s.2(1)(e)")

# ---- L2 ----
add("D3", "L2",
    "Zenith Ltd convenes its AGM. 40% of its shares are held through Depository A. Who is entitled to vote in respect of those shares?",
    "The beneficial owners",
    [("Depository A, being the registered owner", "s.10(2) bars the depository from voting"),
     ("The depository participants, as agents", "participant has no ownership rights"),
     ("Depository A, on instructions of the BOs", "depository treated as a voting proxy")],
    ["s.10(1): depository is deemed registered owner only for effecting transfer of ownership.",
     "s.10(2): depository, as registered owner, has no voting or other rights in respect of securities held by it.",
     "s.10(3): BO is entitled to all rights and benefits and subject to all liabilities."],
    "s.10", "Registered owner for transfer only.", "conceptual", f"{DA}, s.10")

add("D3", "L2",
    "Neha wants to pledge 5,000 demat shares with Crest Bank as security for a loan. Under section 12, the correct procedure is:",
    "Previous approval of the depository; intimation to it; entry in its records",
    [("Deliver physical certificates to the bank with a blank transfer deed", "physical pledge in a demat regime"),
     ("Register the pledge with the RoC within 30 days as a charge", "company-charge registration confused"),
     ("Obtain approval of the issuer, which records the pledge", "issuer wrongly given the depository's role")],
    ["s.12(1): BO may, with the previous approval of the depository, create a pledge or hypothecation.",
     "s.12(2): BO gives intimation to the depository, which makes entries in its records.",
     "s.12(3): the entry is evidence of the pledge or hypothecation."],
    "s.12", "The depository's records are the evidence of the pledge.", "conceptual", f"{DA}, s.12")

add("D2", "L2", "Which of the following is a direct consequence of section 9 of the Depositories Act?",
    "Demat securities are fungible; no distinctive numbers per holder",
    [("Each BO's shares must carry distinctive numbers in the depository", "fungibility reversed"),
     ("A depository may hold only listed equity shares", "invented restriction"),
     ("Demat securities cannot be transferred during a lock-in", "unrelated to fungibility")],
    ["s.9(1): all securities held by a depository shall be dematerialised and in a fungible form.",
     "Fungibility means units of the same security are interchangeable; identification by distinctive number ceases."],
    "s.9", "Fungibility = interchangeability.", "conceptual", f"{DA}, s.9")

dd = 27
lo, hi = daily(dd)
add("D4", "L2",
    f"An issuer's registrar delays dematerialisation of securities beyond the specified time; the delay continues for **{dd} days**. The penalty range under section 19D is:",
    f"{amt(lo)} to {amt(hi)}",
    [(f"Nil to {amt(hi)}", "pre-2014 formula without a minimum"),
     (f"{amt(lo)} to {amt(CRORE)}", "residual s.19G band applied"),
     (f"{amt(lo)} to {amt(LAKH*(dd-1))}", "first day of delay excluded")],
    ["s.19D (post-2014): not less than ₹1 lakh, up to ₹1 lakh per day of default, max ₹1 crore.",
     f"Upper = ₹1 lakh × {dd} = {amt(hi)}."],
    "Penalty ∈ [₹1 lakh, min(₹1 lakh × days, ₹1 crore)]", "Specific section over residual.", "numerical",
    f"{DA}, s.19D (as amended 2014)")

add("D2", "L2",
    "Arun, a beneficial owner, sells demat shares to Bina, who also holds through a participant. Under section 7, the depository registers the transfer in Bina's name:",
    "On intimation from the participant",
    [("On lodgement of a transfer deed with the issuer", "physical transfer route under Companies Act s.56"),
     ("Only after the issuer approves the transfer", "issuer wrongly given a veto"),
     ("After SEBI endorses the delivery instruction", "regulator inserted into routine transfer")],
    ["s.7(1): every depository, on receipt of intimation from a participant, registers the transfer in the name of the transferee.",
     "No transfer deed is lodged with the issuer for demat transfers."],
    "s.7", "Demat transfers bypass the issuer.", "conceptual", f"{DA}, s.7")

add("D1", "L2",
    "The register and index of beneficial owners maintained by a depository under section 11 of the Depositories Act is, for the Companies Act, 2013:",
    "Deemed the issuer's register of members",
    [("Only a memorandum record for the issuer", "deeming provision of CA 2013 s.88(3) missed"),
     ("Valid only when certified by the issuer", "invented certification condition"),
     ("The register of charges of the issuer", "confused with pledge records")],
    ["s.11: every depository maintains a register and index of beneficial owners.",
     "Companies Act, 2013 s.88(3): such register and index is deemed to be the corresponding register and index of the company."],
    "DA s.11; CA 2013 s.88(3)", "The depository's BO register substitutes for the issuer's.", "conceptual",
    f"{DA}, s.11; Companies Act, 2013, s.88(3)")

add("D1", "L2", "Under sections 4 and 5, an investor who wishes to hold securities in a depository must:",
    "Agree with a depository via a participant",
    [("Contract directly with the issuer company", "issuer is not a party to the BO–depository agreement"),
     ("Register with SEBI as a beneficial owner", "BOs do not register with SEBI"),
     ("Apply to the RBI for a securities account", "other regulator")],
    ["s.4: depository enters into an agreement with participants as its agents.",
     "s.5: any person, through a participant, may enter into an agreement with a depository for availing its services."],
    "ss.4, 5", "The participant is the investor's access point.", "conceptual", f"{DA}, ss.4, 5")

# ---- L3 ----
add("D2", "L3",
    "Consider the following statements:\n\n"
    "1. Under section 8, every subscriber to securities has the option to receive certificates or to hold the securities with a depository.\n"
    "2. For a public offer, section 29 of the Companies Act, 2013 requires securities to be issued only in dematerialised form.\n"
    "3. Where the subscriber opts for a depository, the issuer intimates the depository, which records the allottee as beneficial owner." + ST,
    "1, 2 and 3",
    [("1 and 3 only", "Companies Act s.29 demat mandate missed"),
     ("2 and 3 only", "s.8 option wrongly thought repealed"),
     ("1 and 2 only", "s.8(2)–(3) recording mechanism missed")],
    ["s.8(1): option to receive certificates or hold with a depository — true.",
     "CA 2013 s.29(1)(a): public offers only in demat form — true (it overrides the physical option for public offers).",
     "s.8(2)–(3): issuer intimates depository; depository enters allottee as BO — true."],
    "DA s.8; CA 2013 s.29", "General option (DA) vs mandate for public offers (CA).", "statement",
    f"{DA}, s.8; Companies Act, 2013, s.29")

rows = [("P", "Section 9"), ("Q", "Section 10"), ("R", "Section 12"), ("S", "Section 16")]
cols = ["1. Pledge or hypothecation of demat securities", "2. Securities in fungible form",
        "3. Depository to indemnify BO for loss from negligence", "4. Rights of depository and beneficial owner"]
tbl = "| DA | Subject |\n|---|---|\n" + "\n".join(f"| {a}. {b} | {c} |" for (a, b), c in zip(rows, cols))
add("D3", "L3", f"Match the Depositories Act section with its subject:\n\n{tbl}\n\nCodes (P-Q-R-S):",
    "P-2, Q-4, R-1, S-3",
    [("P-4, Q-2, R-1, S-3", "fungibility and rights sections swapped"),
     ("P-2, Q-4, R-3, S-1", "pledge and indemnity swapped"),
     ("P-4, Q-2, R-3, S-1", "both pairs swapped")],
    ["s.9 fungibility; s.10 rights of depository and BO; s.12 pledge/hypothecation; s.16 indemnity."],
    "ss.9, 10, 12, 16", "Adjacent-section confusion is the trap.", "match", f"{DA}, ss.9, 10, 12, 16")

rd, gd = 48, 110
t = daily(rd)[1] + daily(gd)[1] + CRORE
assert t == 2.48 * CRORE
add("D4", "L3",
    f"A participant (i) failed to reconcile its records with the depository for **{rd} days**, (ii) failed to redress investor grievances for **{gd} days** after SEBI's direction, and (iii) committed a contravention with no separate penalty. The **maximum aggregate** penalty is:",
    amt(t),
    [(amt(LAKH * (rd + gd) + CRORE), "₹1 crore cap on the 110-day failure ignored"),
     (amt(daily(rd)[1] + daily(gd)[1]), "residual s.19G penalty omitted"),
     (amt(daily(rd)[1] + daily(gd)[1] + 25 * CRORE), "s.20 criminal fine used as the residual ceiling")],
    [f"(i) s.19E: min(₹1 lakh × {rd}, ₹1 crore) = {amt(daily(rd)[1])}.",
     f"(ii) s.19C: min(₹1 lakh × {gd}, ₹1 crore) = {amt(daily(gd)[1])}.",
     "(iii) s.19G: up to ₹1 crore.", f"Total = {amt(t)}."],
    "Σ head-wise maxima", "Adjudicated penalty (s.19G) ≠ criminal fine (s.20).", "numerical",
    f"{DA}, ss.19C, 19E, 19G (as amended 2014)")

add("D4", "L3",
    "**Assertion (A):** For a failure to furnish information to SEBI that lasted a single day, an adjudicating officer under section 19A cannot impose a penalty below ₹1 lakh.\n\n"
    "**Reason (R):** The Securities Laws (Amendment) Act, 2014 prescribed a minimum penalty of ₹1 lakh for such failures.",
    AR[0], [(AR[1], "misses that the floor is the very basis of A"),
            (AR[2], "pre-2014 'up to' formula assumed still in force"),
            (AR[3], "treats the AO as free to go below ₹1 lakh")],
    ["Post-2014 s.19A: not less than ₹1 lakh, up to ₹1 lakh per day, max ₹1 crore.",
     "The floor was introduced by the 2014 amendment — so R is true and explains A."],
    "s.19A (as amended 2014)", "Earlier text had only an upper limit.", "assertion-reason", f"{DA}, s.19A (as amended 2014)")

add("D3", "L3",
    "Consider the following statements:\n\n"
    "1. A depository is deemed to be the registered owner for the purpose of effecting transfer of ownership on behalf of a beneficial owner.\n"
    "2. A depository, as registered owner, may vote on the securities where the BO does not.\n"
    "3. A beneficial owner is subject to all liabilities in respect of securities held by a depository." + ST,
    "1 and 3 only",
    [("1 and 2 only", "depository wrongly given residual voting rights"),
     ("1, 2 and 3", "s.10(2) bar on depository rights missed"),
     ("3 only", "s.10(1) deeming for transfer missed")],
    ["s.10(1) — true.", "s.10(2): no voting or other rights for the depository — false.", "s.10(3) — true."],
    "s.10", "Depository holds bare legal title for transfer.", "statement", f"{DA}, s.10")

add("D4", "L3",
    "Consider the following statements:\n\n"
    "1. SEBI may call upon an issuer, depository, participant or beneficial owner to furnish information relating to securities held in a depository.\n"
    "2. SEBI may issue directions to a depository or participant in the interest of investors or orderly development of the securities market.\n"
    "3. A court may take cognizance of an offence under the Act on a complaint by any investor who suffered loss." + ST,
    "1 and 2 only",
    [("1, 2 and 3", "s.22 bar (complaint by the Board) missed"),
     ("2 and 3 only", "s.18 information power missed"),
     ("1 only", "s.19 direction power missed")],
    ["s.18 — true.", "s.19 — true.", "s.22: no court takes cognizance save on a complaint by the Board — statement 3 false."],
    "ss.18, 19, 22", "Prosecution is SEBI-initiated.", "statement", f"{DA}, ss.18, 19, 22")

rc = date(2026, 6, 15)
sat_last = rc + timedelta(45)
sat_dec = date(2026, 12, 7)
sc_last = sat_dec + timedelta(60)
add("D4", "L3",
    f"A depository receives a copy of a SEBI order under the Depositories Act on {d(rc)}. SAT later decides its appeal and communicates the decision on {d(sat_dec)}. The last dates (without condonation) for appealing to SAT and to the Supreme Court are respectively:",
    f"{d(sat_last)}; {d(sc_last)}",
    [(f"{d(rc + timedelta(30))}; {d(sc_last)}", "30 days assumed for the SAT appeal"),
     (f"{d(sat_last)}; {d(sat_dec + timedelta(90))}", "90 days assumed for the Supreme Court appeal"),
     (f"{d(rc + timedelta(15))}; {d(sat_dec + timedelta(45))}", "SCRA delisting window and SAT period swapped in")],
    ["Appeal to SAT within 45 days of receipt of the order.", f"{d(rc)} + 45 = {d(sat_last)}.",
     "Appeal to Supreme Court within 60 days of communication of SAT's decision (on a question of law).",
     f"{d(sat_dec)} + 60 = {d(sc_last)}."],
    "SAT: receipt + 45 days; SC: communication + 60 days", "Same architecture as the SEBI Act.", "numerical",
    f"{DA}, ss.23A, 23F")

# ---- L4 case: Meera / Arcadia ----
H, UNA, PX, PL, OO, RDAYS = 12_000, 3_000, 640, 5_000, 2_000, 75
opt_rec = date(2026, 7, 6)
case = ("**Case — Meera and Arcadia Securities (fictional)**\n\n"
        f"Meera holds {inr(H)} shares of Zenith Ltd through Arcadia Securities, a participant of Depository D. "
        f"Arcadia's staff negligently executed an unsigned delivery instruction and moved {inr(UNA)} of her shares out; "
        f"the loss is assessed at ₹{PX} per share. Meera now wishes to (i) pledge {inr(PL)} shares to Crest Bank and "
        f"(ii) opt out of the depository for {inr(OO)} shares — Zenith received intimation from Depository D on {d(opt_rec)}. "
        f"SEBI's inspection also found that Arcadia failed to reconcile its records with Depository D for {RDAYS} days.")
G3 = "ACTS-CASE-ARCADIA"
loss = UNA * PX
assert loss == 19_20_000
add("D3", "L4", case + "\n\nWho must indemnify Meera, and for how much?",
    f"Depository D, {R(loss)}, with recourse to Arcadia",
    [(f"Arcadia alone, {R(loss)}; D has no liability", "s.16(1) depository liability missed"),
     (f"Depository D, {R(loss)}, without recourse", "s.16(2) right of recovery missed"),
     (f"Zenith Ltd, {R(H*PX)}, as issuer", "issuer wrongly liable; entire holding valued")],
    ["s.16(1): loss caused to a BO by negligence of the depository or participant — depository indemnifies the BO.",
     "s.16(2): where the loss arose from the participant's negligence, the depository may recover from the participant.",
     f"Loss = {inr(UNA)} × ₹{PX} = {R(loss)}."],
    "s.16; Loss = Shares moved × Assessed value", "Depository is the first port of indemnity.", "case",
    f"{DA}, s.16", group=G3)

add("D3", "L4", case + "\n\nFor the pledge to Crest Bank, which of the following is correct?\n\n"
    "1. Meera needs the previous approval of Depository D.\n"
    "2. Meera must intimate Depository D, which records the pledge.\n"
    "3. The pledge must be approved by Zenith Ltd's board of directors." + ST,
    "1 and 2 only",
    [("1 only", "intimation and recording under s.12(2) missed"),
     ("2 and 3 only", "issuer approval wrongly required; depository approval missed"),
     ("1, 2 and 3", "issuer wrongly inserted into the pledge process")],
    ["s.12(1): previous approval of depository — true.", "s.12(2): intimation; depository records — true.",
     "Issuer has no role — false."],
    "s.12", "Pledge sits entirely within the depository system.", "statement", f"{DA}, s.12", group=G3)

lo, hi = daily(RDAYS)
add("D4", "L4", case + f"\n\nFor Arcadia's {RDAYS}-day failure to reconcile records, the penalty range under section 19E is:",
    f"{amt(lo)} to {amt(hi)}",
    [(f"{amt(lo)} to {amt(CRORE)}", "residual s.19G band applied"),
     (f"{amt(lo)} to {amt(LAKH*(RDAYS-1))}", "first day excluded"),
     (f"{amt(5*LAKH)} to {amt(25*CRORE)}", "SCRA s.23E band imported")],
    ["s.19E (post-2014): not less than ₹1 lakh, up to ₹1 lakh per day of failure, max ₹1 crore.",
     f"Upper = ₹1 lakh × {RDAYS} = {amt(hi)}."],
    "Penalty ∈ [₹1 lakh, min(₹1 lakh × days, ₹1 crore)]", "Specific section over residual.", "numerical",
    f"{DA}, s.19E (as amended 2014)", group=G3)

od = opt_rec + timedelta(30)
add("D2", "L4", case + "\n\nFor the opt-out, the latest date by which Zenith must issue the certificate of securities is:",
    d(od),
    [(d(opt_rec + timedelta(15)), "15-day period assumed"),
     (d(add_months(opt_rec, 2)), "two-month allotment timeline of the Companies Act used"),
     (d(opt_rec + timedelta(45)), "45-day SAT appeal period applied")],
    ["s.14(2): issuer issues the certificate within 30 days of receipt of information from the depository.",
     f"{d(opt_rec)} + 30 days = {d(od)}."],
    "Deadline = Receipt of intimation + 30 days", "Clock runs from issuer's receipt, not BO's request.", "numerical",
    f"{DA}, s.14", group=G3)

# =====================================================================================
# checks + output
# =====================================================================================
if LEN_FAIL:
    for q in LEN_FAIL: print("LENGTH CUE:", q)
    raise SystemExit("length-cue failures")
per_act = Counter(ACT_OF.values())
assert per_act == {"S": 25, "C": 24, "D": 22}, per_act
assert len(B.Q) == 71
groups = Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"])
assert all(3 <= v <= 5 for v in groups.values()), groups
assert all(q["rubric_level"] == "L4" for q in B.Q if q["stimulus_group"])
missing = set(B.cat) - {q["microtopic_slug"] for q in B.Q}
assert not missing, missing
print("per act", dict(per_act), "| case sets", dict(groups))
B.write()
