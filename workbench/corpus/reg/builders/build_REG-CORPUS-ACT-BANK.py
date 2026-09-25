"""REG-CORPUS-ACT-BANK builder: financial-sector-acts · banking-sector Acts (70 Q).
  RBI Act, 1934 (25) · Banking Regulation Act, 1949 (25) · DICGC Act, 1961 (20).
Writes its own catalogue lists/fsa.REG-CORPUS-ACT-BANK.tsv, then builds out/<BATCH>.json + _review.md.
Every numeric key / distractor is computed below; asserts guard hand-checked values.
Run: python3 build_REG-CORPUS-ACT-BANK.py
"""
import os as _os, sys, csv
from collections import Counter
from datetime import date, timedelta
_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
from reglib import Batch, inr, R, pct, lakh, crore, make_slug  # noqa: E402

BATCH, PREFIX = "REG-CORPUS-ACT-BANK", "ACTB"
LIST = _os.path.join(_REG, "lists", f"fsa.{BATCH}.tsv")
RBI, BRA, DIC = ("Reserve Bank of India Act, 1934", "Banking Regulation Act, 1949",
                 "Deposit Insurance and Credit Guarantee Corporation Act, 1961")

MICROS = [  # (key, name, act)
    ("rbi-gov", "RBI Act — Constitution, Central Board and governance", RBI),
    ("rbi-note", "RBI Act — Note issue and minimum reserve system", RBI),
    ("rbi-crr", "RBI Act — Cash reserve ratio and penal interest under s.42", RBI),
    ("rbi-mpc", "RBI Act — Monetary Policy Committee and inflation targeting", RBI),
    ("rbi-nbfc", "RBI Act — NBFC regulation under Chapter IIIB", RBI),
    ("rbi-biz", "RBI Act — Business of the Bank and lender of last resort", RBI),
    ("br-def", "BR Act — Definitions and permitted business", BRA),
    ("br-cap", "BR Act — Capital, voting rights and reserve fund", BRA),
    ("br-loan", "BR Act — Loans to directors and restrictions on shareholding", BRA),
    ("br-lic", "BR Act — Licensing and statutory liquidity ratio", BRA),
    ("br-dir", "BR Act — RBI directions, removal and supersession powers", BRA),
    ("br-amal", "BR Act — Moratorium, amalgamation and co-operative banks", BRA),
    ("dic-elig", "DICGC Act — Insured banks and excluded deposits", DIC),
    ("dic-cover", "DICGC Act — Deposit insurance cover computation", DIC),
    ("dic-prem", "DICGC Act — Premium payable by insured banks", DIC),
    ("dic-time", "DICGC Act — Payment timelines and the 2021 amendment", DIC),
]
M = {k: make_slug(n, "fsa") for k, n, _ in MICROS}
_os.makedirs(_os.path.dirname(LIST), exist_ok=True)
with open(LIST, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(["slug", "exams", "name", "act"])
    for k, n, a in MICROS:
        w.writerow([M[k], "ifsca,pfrda,sebi", n, a])

B = Batch(BATCH, "financial-sector-acts", PREFIX, list_file=LIST)


# ---------------- helpers ----------------
def table(header, rows, align=None):
    align = align or ["---"] + ["---:"] * (len(header) - 1)
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def stl(items):
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(items))


def combo(sel, n):
    sel = sorted(sel)
    if not sel:
        return "None of the statements"
    if len(sel) == n:
        return ", ".join(str(i) for i in range(1, n)) + f" and {n}"
    if len(sel) == 1:
        return f"{sel[0]} only"
    return ", ".join(str(i) for i in sel[:-1]) + f" and {sel[-1]} only"


def stmt_opts(truth, why, flips=None):
    n = len(truth)
    corr = {i + 1 for i, t in enumerate(truth) if t}
    idx = flips if flips is not None else list(range(n))[:3]
    wrongs = []
    for i in idx:
        s = set(corr) ^ {i + 1}
        err = (f"wrongly accepts statement {i+1}: {why[i]}" if not truth[i]
               else f"wrongly rejects statement {i+1}: {why[i]}")
        wrongs.append((combo(s, n), err))
    return combo(corr, n), wrongs


AR = ["Both A and R are true, and R is the correct explanation of A",
      "Both A and R are true, but R is not the correct explanation of A",
      "A is true, but R is false",
      "A is false, but R is true"]


def ar_opts(key, errs):
    """key = index into AR; errs = dict idx->error for the other three."""
    return AR[key], [(AR[i], errs[i]) for i in range(4) if i != key]


def dfmt(d):
    return f"{d.day} {d.strftime('%B %Y')}"


def add_months(d, m):
    y, mo = divmod(d.month - 1 + m, 12)
    return date(d.year + y, mo + 1, d.day)


CR = 1e7
LK = 1e5


def cr(x, d=2):  # x in rupees
    return crore(x, d)


def ref(act, s):
    return f"{act}, {s} — verify against current official text"


# =====================================================================
# RBI ACT, 1934  (25)
# =====================================================================
# --- governance ---
B.add(M["rbi-gov"], "L1",
      "Under the Reserve Bank of India Act, 1934, the minimum frequency of meetings of the Central Board of the Reserve Bank is:",
      "At least six times a year and at least once in each quarter",
      [("At least four times a year, at least once in each quarter", "confuses with the MPC's minimum of four meetings a year (s.45ZI)"),
       ("At least twelve times a year, i.e. once every month", "invented monthly requirement"),
       ("At least twice a year, once in each half-year", "confuses with half-yearly Monetary Policy Report cycle")],
      ["Section 13 requires the Governor to convene meetings of the Central Board at least six times in each year.",
       "It also requires at least one meeting in each quarter, so the six meetings cannot be bunched."],
      "RBI Act s.13(1)", "Four meetings a year is the MPC floor, not the Central Board's.",
      kind="conceptual", verify_fact=True, ref=ref(RBI, "s.13"))

B.add(M["rbi-gov"], "L1",
      "The Central Government wishes to require the Reserve Bank to follow a particular course of action in the public interest. Under the RBI Act, it may do so:",
      "By directions issued after consultation with the Governor",
      [("By directions issued without any prior consultation", "omits the mandatory consultation with the Governor in s.7(1)"),
       ("Only through an amendment Act passed by Parliament", "ignores the statutory direction power in s.7"),
       ("By directions issued after a resolution of the MPC", "confuses general directions with monetary policy decisions of the MPC")],
      ["Section 7(1): the Central Government may from time to time give such directions to the Bank as it may, after consultation with the Governor, consider necessary in the public interest.",
       "Consultation with the Governor is a precondition; the MPC has no role in s.7 directions."],
      "RBI Act s.7(1)", "The s.7 power has never been a no-consultation power.",
      kind="conceptual", verify_fact=True, ref=ref(RBI, "s.7"))

B.add(M["rbi-gov"], "L3",
      "Match the provisions of the RBI Act, 1934 with their subject matter:\n\n"
      + table(["Section", "Subject"],
              [["P. s.7", "1. Allocation of surplus profits to the Central Government"],
               ["Q. s.8", "2. Composition of the Central Board"],
               ["R. s.13", "3. Directions by the Central Government after consulting the Governor"],
               ["S. s.47", "4. Meetings of the Central Board"]], ["---", "---"]),
      "P-3, Q-2, R-4, S-1",
      [("P-3, Q-4, R-2, S-1", "swaps composition (s.8) and meetings (s.13)"),
       ("P-1, Q-2, R-4, S-3", "swaps Central Government directions (s.7) with surplus transfer (s.47)"),
       ("P-2, Q-3, R-4, S-1", "treats s.7 as the Board-composition section")],
      ["s.7 — Central Government directions after consultation with the Governor.",
       "s.8 — composition of the Central Board (Governor, Deputy Governors, nominated directors).",
       "s.13 — meetings of the Central Board.", "s.47 — surplus profits paid to the Central Government."],
      "Section map of RBI Act Chapter II–IV", "s.7 (directions) and s.47 (surplus) are the two most interchanged.",
      kind="conceptual", verify_fact=True, ref=ref(RBI, "ss.7, 8, 13, 47"))

# --- note issue ---
B.add(M["rbi-note"], "L1",
      "Under section 22 of the RBI Act, 1934, the sole right to issue bank notes in India vests in:",
      "The Reserve Bank of India",
      [("The Central Government, acting through its printing presses", "confuses printing of notes with the legal right of issue"),
       ("The Central Government for denominations up to ₹10,000", "confuses the s.24 denomination ceiling with the right of issue"),
       ("The Reserve Bank jointly with the State Bank of India", "invented joint issue right")],
      ["s.22 gives the Bank the sole right to issue bank notes in India.",
       "One-rupee notes are issued by the Government and are treated as coin, not RBI bank notes."],
      "RBI Act s.22", "Printing and issue are different things; issue is a legal right of the RBI.",
      kind="conceptual", verify_fact=True, ref=ref(RBI, "s.22"))

gold, fx = 110 * CR, 500000 * CR
assert gold + fx >= 200 * CR and gold < 115 * CR
B.add(M["rbi-note"], "L2",
      f"In a hypothetical stress scenario, the Issue Department of the RBI holds gold coin and bullion valued at {cr(gold,0)} "
      f"and foreign securities of {cr(fx,0)}, besides rupee securities. Judged only against section 33, the position is:",
      "Non-compliant, because gold coin and bullion are below ₹115 crore",
      [("Compliant, because gold plus foreign securities exceed ₹200 crore", "checks only the aggregate limb and misses the gold sub-limit"),
       ("Non-compliant, because foreign securities are not 40% of notes", "applies the pre-1956 proportional reserve rule"),
       ("Compliant, because gold holdings are not tested separately", "denies the separate gold floor within the minimum reserve")],
      ["s.33(2) minimum reserve: gold coin, gold bullion and foreign securities together ≥ ₹200 crore.",
       f"Of this, gold coin and bullion alone must be ≥ ₹115 crore; here gold = {cr(gold,0)}.",
       "Aggregate limb is satisfied, but the gold sub-limit is breached, so the position does not satisfy s.33 (unless suspended under s.37)."],
      "Gold + foreign securities ≥ ₹200 crore; gold ≥ ₹115 crore", "Two tests, both must hold.",
      kind="conceptual", verify_fact=True, ref=ref(RBI, "s.33(2), s.37"))

o, w_ = ar_opts(0, {1: "misses that the minimum reserve system is the very reason note issue is not tied to gold",
                    2: "treats the minimum reserve system as repealed",
                    3: "believes note issue is still tied proportionally to gold"})
B.add(M["rbi-note"], "L2",
      "**Assertion (A):** The Reserve Bank can expand the note issue far beyond the value of the gold and foreign securities it holds.\n\n"
      "**Reason (R):** Since the 1956–57 amendments, section 33 requires only a fixed minimum of gold and foreign securities, not a fixed proportion of notes issued.",
      o, w_,
      ["Before 1956 the RBI followed a proportional reserve system (40% of assets in gold/foreign securities).",
       "The minimum reserve system (₹200 crore, of which gold ≥ ₹115 crore) replaced it; the reserve does not rise with note issue.",
       "Hence A is true and R is its correct explanation."],
      "RBI Act s.33 (minimum reserve system)", "The 40% proportional rule is historical.",
      kind="assertion-reason", verify_fact=True, ref=ref(RBI, "s.33"))

c, wr = stmt_opts([True, False, True],
                  ["s.26(2) demonetisation is by Central Government notification on the Central Board's recommendation",
                   "s.24 caps denominations at ₹10,000 and the Central Government specifies them",
                   "s.33(2) is the minimum reserve provision"], flips=[0, 1, 2])
B.add(M["rbi-note"], "L3",
      "Consider the following statements about note issue under the RBI Act, 1934:\n\n" + stl([
          "On the recommendation of the Central Board, the Central Government may by notification declare that a series of bank notes of any denomination shall cease to be legal tender.",
          "The Central Board may, on its own, introduce a bank note of ₹20,000 denomination.",
          "The aggregate value of gold coin, gold bullion and foreign securities held as assets of the Issue Department must not be less than ₹200 crore."]) +
      "\n\nWhich of the statements is/are correct?",
      c, wr,
      ["1: s.26(2) — correct.",
       "2: s.24 — denominations not exceeding ₹10,000, specified by the Central Government on the Board's recommendation — incorrect.",
       "3: s.33(2) — correct."],
      "RBI Act ss.24, 26(2), 33(2)", "Demonetisation and new denominations both need the Central Government.",
      kind="statement", verify_fact=True, ref=ref(RBI, "ss.24, 26(2), 33"))

# --- CRR ---
pc, rs = 3 * LK, 2.5 * LK
assert pc + rs >= 5 * LK and pc < 5 * LK
B.add(M["rbi-crr"], "L2",
      f"A banking company has paid-up capital of {lakh(pc)} and reserves of {lakh(rs)}, and RBI is satisfied that its affairs are not conducted detrimentally to depositors. "
      "For inclusion in the Second Schedule under s.42(6), its capital position is:",
      f"Adequate, as paid-up capital and reserves total {lakh(pc+rs)}",
      [(f"Inadequate, as paid-up capital alone is below {lakh(5*LK)}", "tests paid-up capital alone instead of capital plus reserves"),
       (f"Inadequate, as the test is {lakh(10*LK)} of capital and reserves", "confuses with the higher s.11 figures for banks in Mumbai/Kolkata"),
       ("Irrelevant, as only a licence under s.22 is needed", "confuses licensing under the BR Act with scheduling under the RBI Act")],
      ["s.42(6)(a): paid-up capital and reserves of aggregate value not less than ₹5 lakh, plus RBI's satisfaction about depositors' interests.",
       f"Aggregate = {lakh(pc)} + {lakh(rs)} = {lakh(pc+rs)} ≥ ₹5 lakh."],
      "Paid-up capital + reserves ≥ ₹5 lakh", "The test is on the aggregate, not paid-up capital alone.",
      kind="numerical", verify_fact=True, ref=ref(RBI, "s.42(6)(a)"))

c, wr = stmt_opts([True, True, False],
                  ["the 2006 amendment removed the 3%–20% band", "CRR is on net demand and time liabilities",
                   "interest on eligible CRR balances was discontinued after the 2006 amendment"], flips=[0, 1, 2])
B.add(M["rbi-crr"], "L2",
      "Consider the following statements on the cash reserve ratio under s.42 of the RBI Act:\n\n" + stl([
          "The Act no longer prescribes a statutory floor or ceiling for the CRR; RBI specifies the percentage.",
          "The CRR is maintained as a percentage of the bank's net demand and time liabilities in India.",
          "The Act obliges RBI to pay interest on the CRR balances of scheduled banks."]) +
      "\n\nWhich of the statements is/are correct?",
      c, wr,
      ["1: Correct — the 2006 amendment removed the 3% floor and 20% ceiling.",
       "2: Correct — s.42(1) links CRR to total demand and time liabilities (net of specified items).",
       "3: Incorrect — the provision for interest on CRR balances was omitted; RBI pays no interest on CRR."],
      "RBI Act s.42(1) (as amended 2006)", "The 3%–20% band and interest on CRR are pre-2006 features.",
      kind="statement", verify_fact=True, ref=ref(RBI, "s.42(1), RBI (Amendment) Act 2006"))

br = 0.065
req = 900 * CR
bal = [912, 880, 865, 905, 885, 890, 901]
short = [max(0, req - b * CR) for b in bal]
rate, prev = [], False
for s in short:
    if s > 0:
        rate.append(br + (0.05 if prev else 0.03)); prev = True
    else:
        rate.append(0); prev = False
pen = sum(s * r / 365 for s, r in zip(short, rate))
pen_all3 = sum(s * (br + .03) / 365 for s in short)
pen_all5 = sum(s * (br + .05) / 365 for s in short)
pen_noreset = sum(s * (br + (.03 if i == 1 else .05)) / 365 for i, s in enumerate(short) if s)
assert round(pen) == 232877, pen
B.add(M["rbi-crr"], "L3",
      "Kaveri Bank Ltd, a scheduled bank, must hold a stipulated minimum CRR balance of ₹900 crore with RBI at the close of each day. "
      f"The Bank Rate is {pct(br)}. Its closing balances for seven consecutive days were:\n\n"
      + table(["Day", "1", "2", "3", "4", "5", "6", "7"], [["Balance (₹ crore)"] + bal]) +
      "\n\nApplying the penal-interest scheme of s.42(3) on a daily basis (365-day year), total penal interest for the week is closest to:",
      R(pen),
      [(R(pen_all3), "charges Bank Rate + 3% on every default day, ignoring the step-up for continuing default"),
       (R(pen_noreset), "treats Day 5 as a continuation although Day 4 was compliant"),
       (R(pen_all5), "charges Bank Rate + 5% from the first day of default")],
      [f"Shortfalls (₹ crore): Day 2 = 20, Day 3 = 35, Day 5 = 15, Day 6 = 10; Days 1, 4, 7 compliant.",
       f"First day of a default run: Bank Rate + 3% = {pct(br+.03)}; next succeeding day(s): Bank Rate + 5% = {pct(br+.05)}.",
       "Day 4 is compliant, so Day 5 starts a fresh run at +3%.",
       f"Penal = (20×9.5% + 35×11.5% + 15×9.5% + 10×11.5%) crore ÷ 365 = {R(pen)}"],
      "Penal = Shortfall × (Bank Rate + 3%/5%) × 1/365", "A compliant day breaks the chain; the next default starts at +3%.",
      kind="numerical", verify_fact=True, ref=ref(RBI, "s.42(3); RBI CRR directions (daily minimum)"))

f1r, f1a, f2r, f2a = 2400 * CR, 2352 * CR, 2420 * CR, 2390 * CR
s1_, s2_ = f1r - f1a, f2r - f2a
pf = s1_ * (br + .03) * 14 / 365 + s2_ * (br + .05) * 14 / 365
pf_3 = (s1_ + s2_) * (br + .03) * 14 / 365
pf_5 = (s1_ + s2_) * (br + .05) * 14 / 365
pf_nobr = s1_ * .03 * 14 / 365 + s2_ * .05 * 14 / 365
B.add(M["rbi-crr"], "L3",
      f"Godavari Bank Ltd's average daily CRR balances for two successive fortnights were (Bank Rate {pct(br)}):\n\n"
      + table(["Fortnight", "Required average (₹ crore)", "Actual average (₹ crore)"],
              [["I", inr(f1r / CR), inr(f1a / CR)], ["II", inr(f2r / CR), inr(f2a / CR)]]) +
      "\n\nUsing the average-basis penal interest of s.42(3) (14-day fortnight, 365-day year), total penal interest for the two fortnights is:",
      lakh(pf),
      [(lakh(pf_3), "applies Bank Rate + 3% to Fortnight II as well, missing the step-up for continuing default"),
       (lakh(pf_5), "applies Bank Rate + 5% from the first fortnight of default"),
       (lakh(pf_nobr), "uses 3%/5% flat without adding the Bank Rate")],
      [f"Shortfall I = {inr(s1_/CR)} crore; shortfall II = {inr(s2_/CR)} crore (default continues).",
       f"Fortnight I at Bank Rate + 3% = {pct(br+.03)}; Fortnight II at Bank Rate + 5% = {pct(br+.05)}.",
       f"Penal = 48 cr × 9.5% × 14/365 + 30 cr × 11.5% × 14/365 = {lakh(pf)}"],
      "Penal = Avg shortfall × (Bank Rate + 3% / 5%) × 14/365", "Rates are over the Bank Rate, not flat.",
      kind="numerical", verify_fact=True, ref=ref(RBI, "s.42(3)"))

# --- MPC ---
B.add(M["rbi-mpc"], "L1",
      "Which of the following is NOT a member of the Monetary Policy Committee constituted under s.45ZB of the RBI Act?",
      "Secretary, Department of Economic Affairs",
      [("Deputy Governor in charge of monetary policy", "this Deputy Governor is an ex officio member"),
       ("One RBI officer nominated by the Central Board", "this officer is a member under s.45ZB(2)(c)"),
       ("Governor of the Reserve Bank, as chairperson", "the Governor is the ex officio chairperson")],
      ["s.45ZB: six members — Governor (chair), Deputy Governor in charge of monetary policy, one RBI officer nominated by the Central Board, and three persons appointed by the Central Government.",
       "No Government official sits on the MPC."],
      "MPC = 3 RBI + 3 external", "Government nominees sit on the Central Board, not the MPC.",
      kind="conceptual", verify_fact=True, ref=ref(RBI, "s.45ZB"))

B.add(M["rbi-mpc"], "L2",
      "At a scheduled MPC meeting, the Governor and the Deputy Governor in charge of monetary policy are both abroad. "
      "The RBI officer-member and all three external members attend. Can the meeting transact business?",
      "No; neither the Governor nor the Deputy Governor is present",
      [("Yes; four members are present, which meets the quorum of four", "counts heads but ignores the composition condition of the quorum"),
       ("Yes; the RBI officer-member can preside and complete the quorum", "assumes the officer-member substitutes for the Governor"),
       ("No; the quorum is five of the six members of the Committee", "wrong quorum number")],
      ["s.45ZI: quorum is four members, one of whom must be the Governor and, in his absence, the Deputy Governor who is a member.",
       "Four are present but neither the Governor nor the Deputy Governor is among them — no quorum."],
      "Quorum = 4 incl. Governor (or DG in his absence)", "Quorum has a headcount AND a composition limb.",
      kind="case", verify_fact=True, ref=ref(RBI, "s.45ZI"))

B.add(M["rbi-mpc"], "L2",
      "All six MPC members vote. The Governor, the Deputy Governor and the RBI officer-member vote for a 25 bp cut in the policy repo rate; "
      "the three external members vote for no change. The outcome is:",
      "A 25 bp cut, carried by the Governor's second or casting vote",
      [("No change, as a tied vote preserves the existing rate", "assumes a tie defaults to status quo"),
       ("Referred to the Central Government to break the tie", "invents a Government role in MPC decisions"),
       ("Deferred to the next meeting for a fresh vote on the rate", "invents deferral on equality of votes")],
      ["s.45ZI: questions are decided by majority of members present and voting; each member has one vote.",
       "On equality of votes, the Governor has a second or casting vote; he voted for the cut."],
      "Tie → Governor's casting vote", "No Government role in MPC voting.",
      kind="case", verify_fact=True, ref=ref(RBI, "s.45ZI"))

qs = [6.3, 6.1, 5.9, 6.4, 6.2, 6.05, 5.7]
run, fail_q = 0, None
for i, v in enumerate(qs):
    run = run + 1 if (v > 6 or v < 2) else 0
    if run == 3 and fail_q is None:
        fail_q = i + 1
assert fail_q == 6
avg_q = next(i + 3 for i in range(len(qs) - 2) if sum(qs[i:i+3]) / 3 > 6)
assert avg_q == 3
B.add(M["rbi-mpc"], "L3",
      "The notified inflation target is 4% CPI inflation with an upper tolerance of 6% and a lower tolerance of 2%. Average CPI inflation (%) by quarter:\n\n"
      + table(["Quarter", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"], [["CPI (%)"] + qs]) +
      "\n\nUnder the failure criterion in the framework notified with s.45ZA/45ZN, RBI is first regarded as having failed to meet the target at the end of:",
      "Q6",
      [("Q2", "treats two consecutive quarters above tolerance as failure"),
       ("Q3", "uses the three-quarter average (6.10%) instead of three consecutive quarters each above 6%"),
       ("Q5", "counts Q1, Q2, Q4, Q5 cumulatively ignoring the break at Q3")],
      ["Failure = average inflation above the upper tolerance (or below the lower) for three consecutive quarters.",
       "Q1, Q2 > 6% but Q3 = 5.9% breaks the run.",
       "Q4 = 6.4, Q5 = 6.2, Q6 = 6.05 — three consecutive quarters above 6% → failure at end-Q6; s.45ZN report follows."],
      "3 consecutive quarters outside 2%–6%", "Each quarter must breach; averaging three quarters is not the test.",
      kind="numerical", verify_fact=True, ref=ref(RBI, "ss.45ZA, 45ZN read with the 2016 Central Govt notification on failure factors"))

c, wr = stmt_opts([True, False, True],
                  ["s.45ZL minutes on the fourteenth day", "the MPR is half-yearly under s.45ZM",
                   "external members serve four years and are not eligible for reappointment"], flips=[0, 1, 2])
B.add(M["rbi-mpc"], "L3",
      "Consider the following statements on the monetary policy framework in Chapter IIIF of the RBI Act:\n\n" + stl([
          "RBI publishes the minutes of MPC proceedings on the fourteenth day after every meeting.",
          "RBI publishes a Monetary Policy Report once every quarter.",
          "An external member of the MPC holds office for four years and is not eligible for reappointment."]) +
      "\n\nWhich of the statements is/are correct?",
      c, wr,
      ["1: Correct — minutes (resolution, votes, members' statements) on the 14th day.",
       "2: Incorrect — the Monetary Policy Report is published once in every six months.",
       "3: Correct — four-year term, no reappointment."],
      "RBI Act ss.45ZC, 45ZL, 45ZM", "MPC meets at least four times a year; the MPR is only half-yearly.",
      kind="statement", verify_fact=True, ref=ref(RBI, "ss.45ZC, 45ZL, 45ZM"))

# --- NBFC ---
B.add(M["rbi-nbfc"], "L1",
      "Under s.45-IA of the RBI Act, a non-banking financial company must have net owned fund of ₹25 lakh or such other amount as RBI may specify by notification, subject to a ceiling of:",
      "₹100 crore",
      [("₹2 crore", "pre-2019 ceiling of two hundred lakh rupees"),
       ("₹200 crore", "reads 'two hundred lakh' as two hundred crore"),
       ("₹10 crore", "confuses the RBI-specified minimum for a class of NBFCs with the statutory ceiling")],
      ["s.45-IA(1)(b) originally allowed RBI to specify up to ₹200 lakh (₹2 crore).",
       "The Finance (No. 2) Act, 2019 raised this ceiling to ₹100 crore; RBI's category-wise minimums are set within it."],
      "RBI Act s.45-IA(1)(b) as amended 2019", "₹2 crore is the old ceiling; ₹10 crore is an RBI-set requirement, not the ceiling.",
      kind="conceptual", verify_fact=True, ref=ref(RBI, "s.45-IA(1)(b), Finance (No. 2) Act 2019"))

G = "NBFC-CASE"
ta, fa, gi, fi = 240 * CR, 150 * CR, 36 * CR, 21 * CR
eq, fr, intang, dre = 40 * CR, 22 * CR, 3 * CR, 1 * CR
sub, onbfc, lgrp, unrel = 6 * CR, 3 * CR, 4 * CR, 5 * CR
np_, div = 8.4 * CR, 3 * CR
dep = {"31 Mar": 110 * CR, "30 Jun": 120 * CR, "30 Sep": 128 * CR}
la = 0.15
case = ("**Case — Vardhan Capital Ltd.** Vardhan Capital Ltd is a company that lends to small traders and also accepts public deposits. Extracts (₹ crore):\n\n"
        + table(["Item", "₹ crore"], [
            ["Total assets", inr(ta / CR)], ["Financial assets", inr(fa / CR)],
            ["Gross income", inr(gi / CR)], ["Income from financial assets", inr(fi / CR)],
            ["Paid-up equity capital", inr(eq / CR)], ["Free reserves", inr(fr / CR)],
            ["Intangible assets", inr(intang / CR)], ["Deferred revenue expenditure", inr(dre / CR)],
            ["Equity shares of its subsidiary", inr(sub / CR)], ["Equity shares of another NBFC", inr(onbfc / CR)],
            ["Loan to a group company", inr(lgrp / CR)], ["Shares of an unrelated listed manufacturing company", inr(unrel / CR)],
            ["Net profit as per P&L (current year)", f"{np_/CR:.1f}"], ["Proposed dividend", inr(div / CR)],
            ["Public deposits: 31 Mar / 30 Jun / 30 Sep", f"{inr(dep['31 Mar']/CR)} / {inr(dep['30 Jun']/CR)} / {inr(dep['30 Sep']/CR)}"]]) +
        "\n\nAssume RBI's principal-business test (financial assets > 50% of total assets AND income from financial assets > 50% of gross income) "
        f"and a liquid-asset requirement of {pct(la,0)} of public deposits specified under s.45-IB.")
assert fa / ta > .5 and fi / gi > .5
B.add(M["rbi-nbfc"], "L4", case + "\n\n**Q1.** Does Vardhan Capital require a certificate of registration under s.45-IA?",
      f"Yes; financial assets are {pct(fa/ta,1)} of assets and income {pct(fi/gi,1)}",
      [(f"No; income share of {pct(fi/gi,1)} is below the 60% threshold", "applies an invented 60% income threshold"),
       ("No; accepting deposits makes it a bank under the BR Act", "confuses deposit-taking NBFC with banking under s.5(b) BR Act"),
       (f"Yes, but only because its financial assets exceed {cr(100*CR,0)}", "invents an asset-size trigger for registration")],
      [f"Financial assets ÷ total assets = {inr(fa/CR)} ÷ {inr(ta/CR)} = {pct(fa/ta,1)} > 50%.",
       f"Income from financial assets ÷ gross income = {inr(fi/CR)} ÷ {inr(gi/CR)} = {pct(fi/gi,1)} > 50%.",
       "Both limbs met → principal business is financial → NBFC → CoR required before carrying on business (s.45-IA)."],
      "50-50 principal business test", "Both limbs must exceed 50%; there is no size trigger.",
      kind="case", group=G, verify_fact=True, ref=ref(RBI, "s.45-I(f), s.45-IA; RBI principal-business criteria (given)"))

owned = eq + fr - intang - dre
grp = sub + onbfc + lgrp
nof = owned - max(0, grp - 0.10 * owned)
nof_full = owned - grp
nof_unrel = owned - max(0, grp + unrel - 0.10 * owned)
owned_b = eq + fr
nof_noint = owned_b - max(0, grp - 0.10 * owned_b)
assert abs(nof - 50.8 * CR) < 1
B.add(M["rbi-nbfc"], "L4", case + "\n\n**Q2.** Net owned fund of Vardhan Capital as defined in the Explanation to s.45-IA is:",
      cr(nof),
      [(cr(nof_full), "deducts the whole group/NBFC exposure instead of only the excess over 10% of owned fund"),
       (cr(nof_unrel), "also deducts shares of the unrelated manufacturing company"),
       (cr(nof_noint), "does not deduct intangible assets and deferred revenue expenditure")],
      [f"Owned fund = equity + free reserves − intangibles − DRE = 40 + 22 − 3 − 1 = {cr(owned)}.",
       f"Exposure to subsidiary, group companies and other NBFCs = 6 + 3 + 4 = {cr(grp)}; 10% of owned fund = {cr(0.1*owned)}.",
       f"Deduct only the excess: {cr(grp)} − {cr(0.1*owned)} = {cr(grp-0.1*owned)}.",
       f"NOF = {cr(owned)} − {cr(grp-0.1*owned)} = {cr(nof)}. Unrelated non-NBFC shares are not deducted."],
      "NOF = Owned fund − (Group/NBFC exposure − 10% of owned fund)", "Only the excess over 10% is deducted.",
      kind="case", group=G, verify_fact=True, ref=ref(RBI, "s.45-IA, Explanation"))

rf = 0.20 * np_
B.add(M["rbi-nbfc"], "L4", case + "\n\n**Q3.** The minimum transfer to reserve fund required by s.45-IC for the year is:",
      cr(rf),
      [(cr(0.25 * np_), "applies 25%, the RBI-prescribed statutory reserve rate for banks"),
       (cr(0.20 * (np_ - div)), "computes 20% on profit after the proposed dividend"),
       (cr(0.10 * np_), "applies 10%, an invented lower rate")],
      ["s.45-IC: every NBFC shall create a reserve fund and transfer not less than 20% of net profit, as disclosed in the P&L, before declaring any dividend.",
       f"20% × {np_/CR:.1f} crore = {cr(rf)}."],
      "Transfer ≥ 20% × net profit (before dividend)", "The base is profit before dividend.",
      kind="case", group=G, verify_fact=True, ref=ref(RBI, "s.45-IC"))

lar = la * dep["30 Jun"]
B.add(M["rbi-nbfc"], "L4", case + "\n\n**Q4.** For the quarter October–December, the liquid assets Vardhan Capital must maintain under s.45-IB are:",
      cr(lar),
      [(cr(la * dep["30 Sep"]), "uses deposits at the end of the immediately preceding quarter"),
       (cr(la * dep["31 Mar"]), "uses deposits at the end of the third preceding quarter"),
       (cr(0.25 * dep["30 Jun"]), "applies the 25% statutory ceiling instead of the specified rate")],
      ["s.45-IB: liquid assets as a specified percentage (5% to 25%) of deposits outstanding at the close of business on the last working day of the second preceding quarter.",
       f"For Oct–Dec, the second preceding quarter ends 30 June: {pct(la,0)} × {cr(dep['30 Jun'],0)} = {cr(lar)}."],
      "Liquid assets = % × deposits at end of second preceding quarter", "Second preceding, not immediately preceding.",
      kind="case", group=G, verify_fact=True, ref=ref(RBI, "s.45-IB"))

c, wr = stmt_opts([True, False, True],
                  ["s.45-MB(1) empowers RBI to prohibit acceptance of deposits",
                   "RBI can only file a winding-up petition (s.45-MC); winding up is ordered by the Tribunal",
                   "s.45-MB(2) lets RBI restrain sale or transfer of property"], flips=[0, 1, 2])
B.add(M["rbi-nbfc"], "L4", case + "\n\n**Q5.** RBI later finds that Vardhan Capital has repeatedly delayed repayment of matured deposits. Consider these actions:\n\n" + stl([
          "Prohibit the company from accepting any fresh deposit.",
          "Itself order the winding up of the company without approaching the Tribunal.",
          "Direct the company not to sell, transfer or otherwise alienate its property without RBI's prior permission."]) +
      "\n\nWhich of these are within RBI's powers under Chapter IIIB?",
      c, wr,
      ["1: s.45-MB(1) — RBI may prohibit acceptance of deposits.",
       "2: Not within power — under s.45-MC, RBI may file a winding-up petition; the order is the Tribunal's.",
       "3: s.45-MB(2) — RBI may prohibit alienation of property."],
      "RBI Act ss.45-MB, 45-MC", "RBI petitions for winding up; it cannot order it.",
      kind="case", group=G, verify_fact=True, ref=ref(RBI, "ss.45-MB, 45-MC"))

# --- business / LOLR ---
B.add(M["rbi-biz"], "L1",
      "The provision that lets RBI, on a 'special occasion', purchase or discount bills and make loans notwithstanding the limitations in s.17 — the statutory basis of its emergency lender-of-last-resort role — is:",
      "Section 18",
      [("Section 17(4)", "ordinary secured lending, which is subject to the s.17 limits"),
       ("Section 45-L", "power over NBFCs, not emergency lending"),
       ("Section 42", "cash reserve requirement, not lending")],
      ["s.18 (power of direct discount): in special occasions, for regulating credit in the interests of trade, commerce, industry and agriculture, RBI may lend or discount notwithstanding s.17 limitations.",
       "This is the legal basis for emergency liquidity support."],
      "RBI Act s.18", "s.17 lists routine business; s.18 overrides its limits in emergencies.",
      kind="conceptual", verify_fact=True, ref=ref(RBI, "s.18"))

B.add(M["rbi-biz"], "L2",
      "Which of the following transactions would the Reserve Bank be barred from undertaking by the RBI Act?",
      "Loan to a scheduled bank secured by a mortgage on its office building",
      [("Purchase of Government of India securities in open market operations", "s.17(8) permits purchase and sale of Government securities"),
       ("Accepting interest-free deposits from a State Government", "s.17(1) permits deposits from Central and State Governments"),
       ("Accepting interest-bearing deposits under its Standing Deposit Facility", "permitted by s.17 since the Finance Act, 2018")],
      ["s.19 bars RBI from advancing money on the security of immovable property (other than its own premises).",
       "Government securities, Government deposits and SDF deposits are all permitted business under s.17."],
      "RBI Act s.19 vs s.17", "The SDF is an explicit statutory carve-out from the ban on paying interest.",
      kind="case", verify_fact=True, ref=ref(RBI, "ss.17, 19; Finance Act 2018 (SDF)"))

c, wr = stmt_opts([True, True, False],
                  ["s.20 is obligatory for the Central Government; s.21A is by agreement with States",
                   "the Finance Act 2018 enabled uncollateralised SDF deposits",
                   "s.19 bars unsecured lending outside the s.17/s.18 framework"], flips=[0, 1, 2])
B.add(M["rbi-biz"], "L3",
      "Consider the following statements on the business of the Reserve Bank:\n\n" + stl([
          "RBI is obliged to transact the banking business of the Central Government, while it transacts the business of a State Government by agreement.",
          "RBI may accept deposits from banks and others, repayable with interest and without collateral, under the Standing Deposit Facility.",
          "In its normal course of business, RBI may grant unsecured loans to any company engaged in infrastructure."]) +
      "\n\nWhich of the statements is/are correct?",
      c, wr,
      ["1: Correct — s.20 (Central Government, obligatory) and s.21A (States, by agreement).",
       "2: Correct — s.17 amended by the Finance Act, 2018 to enable the SDF.",
       "3: Incorrect — s.19 prohibits unsecured loans except as permitted."],
      "RBI Act ss.17, 19, 20, 21A", "Central Government business is mandatory; State business is contractual.",
      kind="statement", verify_fact=True, ref=ref(RBI, "ss.17, 19, 20, 21A"))

# =====================================================================
# BANKING REGULATION ACT, 1949 (25)
# =====================================================================
B.add(M["br-def"], "L1",
      "Tarang Textiles Ltd accepts deposits from the public solely to finance its own spinning business. Under the Banking Regulation Act, it is:",
      "Not a banking company; the deposits are not for lending",
      [("A banking company, as it accepts deposits from the public", "ignores the 'for the purpose of lending or investment' element of s.5(b)"),
       ("A banking company only if deposits are withdrawable by cheque", "treats cheque withdrawal as the sole test"),
       ("A banking company unless the Central Government exempts it", "invents an exemption route; the Explanation settles it")],
      ["s.5(b): banking = accepting, for lending or investment, deposits from the public repayable on demand or otherwise and withdrawable by cheque, draft, order or otherwise.",
       "Explanation to s.5(c): a company engaged in manufacture that accepts deposits merely to finance its own business is not deemed to transact banking."],
      "BR Act s.5(b), s.5(c) Explanation", "Purpose of the deposits (lending/investment) is the key element.",
      kind="conceptual", verify_fact=True, ref=ref(BRA, "s.5(b), (c)"))

B.add(M["br-def"], "L1",
      "Sagar Bank Ltd took possession of cotton bales pledged by a defaulting borrower and now proposes to sell them. Under s.8 of the BR Act, the sale is:",
      "Permitted, as it is made in realising security for a loan",
      [("Prohibited, as a bank may never buy, sell or barter goods", "ignores the realisation-of-security exception in s.8"),
       ("Permitted only after prior approval of the Central Government", "invents a Central Government approval"),
       ("Permitted only if the bales are held for over seven years", "confuses with the s.9 immovable-property disposal period")],
      ["s.8 bars a banking company from directly or indirectly buying, selling or bartering goods.",
       "The exception: dealings in connection with the realisation of security given to or held by it."],
      "BR Act s.8", "Seven years is the s.9 rule for immovable property, not goods.",
      kind="conceptual", verify_fact=True, ref=ref(BRA, "s.8"))

acq = date(2019, 3, 15)
dl7, dlx = date(2026, 3, 15), date(2031, 3, 15)
B.add(M["br-def"], "L2",
      f"On {dfmt(acq)}, Malabar Bank Ltd acquired a warehouse in satisfaction of a borrower's debt. It does not need the warehouse for its own use. "
      "If RBI grants the maximum extension permissible under s.9, the latest date by which the bank must dispose of the warehouse is:",
      dfmt(dlx),
      [(dfmt(date(2029, 3, 15)), "takes the basic holding period as five years instead of seven"),
       (dfmt(dl7), "ignores the extension RBI may grant"),
       (dfmt(date(2033, 3, 15)), "takes the maximum extension as seven years")],
      ["s.9: immovable property not required for own use may not be held beyond seven years from acquisition.",
       f"Basic deadline = {dfmt(dl7)}; RBI may extend by up to five years → {dfmt(dlx)}."],
      "Deadline = acquisition + 7 years (+ up to 5 years' extension)", "7 + 5, not 5 + 5.",
      kind="numerical", verify_fact=True, ref=ref(BRA, "s.9"))

c, wr = stmt_opts([False, True, True],
                  ["the Explanation to s.5(c) excludes such a manufacturer",
                   "s.7 restricts the words bank, banker, banking to banking companies (with limited exceptions)",
                   "s.6(2) confines a banking company to the business listed in s.6(1)"], flips=[0, 1, 2])
B.add(M["br-def"], "L3",
      "Consider the following statements under the Banking Regulation Act, 1949:\n\n" + stl([
          "A manufacturing company that accepts public deposits merely to finance its own business is deemed to transact the business of banking.",
          "A company other than a banking company generally may not use the word 'bank', 'banker' or 'banking' as part of its name.",
          "A banking company may not engage in any form of business other than those referred to in s.6(1)."]) +
      "\n\nWhich of the statements is/are correct?",
      c, wr,
      ["1: Incorrect — Explanation to s.5(c).", "2: Correct — s.7.", "3: Correct — s.6(2)."],
      "BR Act ss.5, 6, 7", "Statement 1 inverts the Explanation.",
      kind="statement", verify_fact=True, ref=ref(BRA, "ss.5(c), 6, 7"))

# --- capital / reserve ---
p_ = 146 * CR
B.add(M["br-cap"], "L2",
      f"Deccan Bank Ltd, incorporated in India, reports net profit of {cr(p_,0)} in its profit and loss account and intends to declare a dividend. "
      "The minimum it must transfer to the reserve fund under s.17 of the BR Act is:",
      cr(0.20 * p_),
      [(cr(0.25 * p_), "applies RBI's 25% prudential statutory-reserve stipulation as the statutory minimum"),
       (cr(0.10 * p_), "applies an invented 10% rate"),
       (cr(0.20 * p_ * 0.8), "computes 20% on profit after the transfer itself")],
      ["s.17(1): before declaring dividend, transfer not less than 20% of profit as disclosed in the P&L to the reserve fund.",
       f"20% × {cr(p_,0)} = {cr(0.20*p_)}. (RBI separately asks banks to transfer 25%, but the statutory floor is 20%.)"],
      "Reserve transfer ≥ 20% × profit", "Statute says 20%; the 25% figure is an RBI prudential stipulation.",
      kind="numerical", verify_fact=True, ref=ref(BRA, "s.17(1)"))

au, sb, pu = 600 * CR, 320 * CR, 150 * CR
assert sb >= au / 2 and pu < sb / 2
B.add(M["br-cap"], "L3",
      f"Indus Bank Ltd has authorised capital {cr(au,0)}, subscribed capital {cr(sb,0)} and paid-up capital {cr(pu,0)}, all in equity shares. "
      "Under s.12(1) of the BR Act, the bank:",
      "Breaches only the rule that paid-up capital be at least half of subscribed",
      [("Breaches only the rule that subscribed capital be at least half of authorised", "misreads 320 ≥ 300 as a breach"),
       ("Breaches both rules, as paid-up capital is below half of authorised", "compares paid-up capital with authorised capital"),
       ("Breaches neither rule, as only the s.11 minimum capital is relevant", "ignores s.12(1) capital-structure conditions")],
      [f"s.12(1)(i): subscribed ≥ ½ authorised → {cr(sb,0)} ≥ {cr(au/2,0)} ✓.",
       f"s.12(1)(ii): paid-up ≥ ½ subscribed → {cr(pu,0)} < {cr(sb/2,0)} ✗."],
      "Subscribed ≥ ½ Authorised; Paid-up ≥ ½ Subscribed", "Paid-up is tested against subscribed, not authorised.",
      kind="numerical", verify_fact=True, ref=ref(BRA, "s.12(1)"))

tot, hold = 50 * CR, 16 * CR
vr = 0.26 * tot
B.add(M["br-cap"], "L2",
      f"A private sector banking company has {inr(tot/CR)} crore equity shares (one vote each). An investor, with all required approvals, holds {inr(hold/CR)} crore shares. "
      "The maximum votes the investor can exercise on a poll is:",
      f"{vr/CR:.0f} crore votes",
      [(f"{0.10*tot/CR:.0f} crore votes", "applies the 10% ceiling in the main text, ignoring RBI's raising of the ceiling to 26%"),
       (f"{hold/CR:.0f} crore votes", "no voting-rights ceiling applied"),
       (f"{0.26*hold/CR:.2f} crore votes", "applies 26% to the investor's own holding instead of total voting rights")],
      ["s.12(2): no shareholder may exercise voting rights beyond the ceiling; the Act permits RBI to raise it in phases from 10% to 26%, and RBI has notified 26%.",
       f"26% × {inr(tot/CR)} crore = {vr/CR:.0f} crore votes (holding = 32%)."],
      "Votes = min(holding, 26% × total votes)", "The ceiling is on total voting rights of all shareholders.",
      kind="numerical", verify_fact=True, ref=ref(BRA, "s.12(2) and RBI notification raising ceiling to 26%"))

B.add(M["br-cap"], "L1",
      "Under s.12B of the BR Act, a person needs RBI's prior approval to acquire shares or voting rights that would take his holding in a banking company to:",
      "5% or more of paid-up capital or total voting rights",
      [("10% or more of paid-up capital or voting rights", "confuses with the base voting ceiling in s.12(2)"),
       ("26% or more of paid-up capital or voting rights", "confuses with the raised voting-rights ceiling"),
       ("More than 2% of paid-up capital or voting rights", "invented threshold")],
      ["s.12B (inserted 2012): prior approval of RBI for acquisition resulting in 5% or more of paid-up share capital or total voting rights."],
      "BR Act s.12B", "5% for acquisition approval; 26% is the voting cap.",
      kind="conceptual", verify_fact=True, ref=ref(BRA, "s.12B"))

pin, pgl = 120 * CR, 900 * CR
d11 = 0.20 * pin
B.add(M["br-cap"], "L3",
      f"Harbour Bank plc, incorporated outside India, has branches in India. For the calendar year, its profit as disclosed in the P&L is {cr(pin,0)} on Indian business and {cr(pgl,0)} worldwide. "
      "The amount it must deposit with RBI under s.11(2)(b)(ii) for the year is:",
      cr(d11),
      [(cr(0.20 * pgl), "applies 20% to worldwide profit instead of Indian-branch profit"),
       (cr(0.20 * pin * 0.8), "first deducts an s.17 reserve transfer, which applies to Indian-incorporated banks"),
       (cr(0.25 * pin), "applies 25% instead of 20%")],
      ["s.11(2)(b)(ii): a foreign bank must deposit with RBI, after each calendar year, 20% of its profit for that year on business transacted through its branches in India.",
       f"20% × {cr(pin,0)} = {cr(d11)}."],
      "Deposit = 20% × Indian-branch profit", "Base is Indian-branch profit; s.17 is irrelevant here.",
      kind="numerical", verify_fact=True, ref=ref(BRA, "s.11(2)(b)(ii)"))

# --- loans / holdings ---
B.add(M["br-loan"], "L2",
      "Mr Kapoor is a director of Vasant Bank Ltd. He is also a director of Alpha Pvt Ltd, a partner in Beta & Co., a director of Gamma Power Ltd (a government company) and a guarantor for his nephew's personal borrowings. "
      "Which proposed loan by Vasant Bank is NOT hit by s.20(1)?",
      "Term loan to Gamma Power Ltd",
      [("Working-capital loan to Alpha Pvt Ltd", "company of which the bank's director is a director — prohibited"),
       ("Overdraft to Beta & Co.", "firm in which the director is a partner — prohibited"),
       ("Personal loan to his nephew", "individual for whom the director is guarantor — prohibited")],
      ["s.20(1)(b) bars loans to directors, firms where a director is partner/guarantor, companies where a director is director/manager/employee/guarantor or holds substantial interest, and individuals for whom a director is partner or guarantor.",
       "Subsidiaries, s.8 companies and government companies are excluded from the company limb."],
      "BR Act s.20(1)", "Government companies are carved out of the company limb.",
      kind="case", verify_fact=True, ref=ref(BRA, "s.20(1)"))

cpu, hd, hs = 30 * LK, 1.8 * LK, 1.5 * LK
thr_old, thr_new = min(5 * LK, 0.1 * cpu), min(2 * CR, 0.1 * cpu)
assert thr_old == thr_new == 3 * LK and hd + hs > thr_old and hd < thr_old
B.add(M["br-loan"], "L3",
      f"Ms Rao, a director of Nilgiri Bank Ltd, holds shares of paid-up value {lakh(hd)} in Orchid Foods Pvt Ltd (paid-up capital {lakh(cpu)}); her husband holds shares of paid-up value {lakh(hs)}. "
      "For s.20, does Ms Rao hold a 'substantial interest' in Orchid Foods under s.5(ne)?",
      f"Yes; the family's {lakh(hd+hs)} exceeds 10% of paid-up capital ({lakh(0.1*cpu)})",
      [(f"No; her own {lakh(hd)} is only {pct(hd/cpu,0)} of paid-up capital", "ignores aggregation with spouse's holding"),
       ("No; the holding is below the fixed rupee limb of the definition", "treats the rupee limb as the only test instead of the lower of the two"),
       ("No; substantial interest applies only to listed companies", "invents a listed-company restriction")],
      ["s.5(ne): beneficial interest held singly or with spouse/minor child, whose paid-up amount exceeds the fixed rupee limit or 10% of paid-up capital, whichever is less.",
       f"10% of {lakh(cpu)} = {lakh(0.1*cpu)}, which is below the rupee limit (whether the older ₹5 lakh or the ₹2 crore after the 2025 amendment).",
       f"Aggregate {lakh(hd)} + {lakh(hs)} = {lakh(hd+hs)} > {lakh(0.1*cpu)} → substantial interest; loan to Orchid Foods is barred by s.20."],
      "Substantial interest: holding > lower of (rupee limit, 10% of paid-up)", "Spouse and minor children are aggregated.",
      kind="case", verify_fact=True, ref=ref(BRA, "s.5(ne) (rupee limb amended by Banking Laws (Amendment) Act 2025 — key unaffected), s.20"))

bpc, brs, ipc, ex = 1200 * CR, 8800 * CR, 2000 * CR, 420 * CR
lim = min(0.30 * ipc, 0.30 * (bpc + brs))
assert lim == 600 * CR
B.add(M["br-loan"], "L2",
      f"Coromandel Bank Ltd has paid-up capital {cr(bpc,0)} and reserves {cr(brs,0)}. It already holds, as pledgee, shares of Zenith Ltd with paid-up value {cr(ex,0)}; Zenith's paid-up capital is {cr(ipc,0)}. "
      "The further shares of Zenith it may hold (as pledgee, mortgagee or owner) within s.19(2) are:",
      cr(lim - ex, 0),
      [(cr(0.30 * (bpc + brs) - ex, 0), "uses the higher of the two limits"),
       (cr(lim, 0), "ignores shares already held as pledgee"),
       ("Nil, as the existing holding already exceeds the limit", "measures 30% against the bank's paid-up capital alone (₹360 crore)")],
      [f"Limit = lower of 30% of Zenith's paid-up ({cr(0.3*ipc,0)}) and 30% of the bank's paid-up + reserves ({cr(0.3*(bpc+brs),0)}) = {cr(lim,0)}.",
       f"Headroom = {cr(lim,0)} − {cr(ex,0)} = {cr(lim-ex,0)}. Pledged shares count."],
      "Holding ≤ min(30% × investee paid-up, 30% × own paid-up + reserves)", "Whichever is less; pledged shares count.",
      kind="numerical", verify_fact=True, ref=ref(BRA, "s.19(2)"))

# --- licensing / SLR ---
B.add(M["br-lic"], "L1",
      "RBI cancels the banking licence of Sunrise Bank Ltd under s.22(4). The bank may appeal against the cancellation to:",
      "The Central Government, within 30 days of the decision",
      [("The National Company Law Appellate Tribunal, within 45 days", "wrong forum; NCLAT has no role under s.22"),
       ("The Central Government, within 60 days of the decision", "wrong time limit"),
       ("The Securities Appellate Tribunal, within 45 days", "confuses with appeals against SEBI orders")],
      ["s.22(5): a banking company aggrieved by cancellation of its licence may appeal to the Central Government within 30 days from the date of communication of the decision.",
       "The Central Government's decision is final."],
      "BR Act s.22(5)", "Appeal lies to the Central Government, not a tribunal.",
      kind="conceptual", verify_fact=True, ref=ref(BRA, "s.22(5)"))

br2 = 0.0675
sl = [50 * CR, 80 * CR, 30 * CR]
psl = sl[0] * (br2 + .03) / 365 + (sl[1] + sl[2]) * (br2 + .05) / 365
psl3 = sum(sl) * (br2 + .03) / 365
psl_3rd = (sl[0] + sl[1]) * (br2 + .03) / 365 + sl[2] * (br2 + .05) / 365
psl_nobr = sl[0] * .03 / 365 + (sl[1] + sl[2]) * .05 / 365
B.add(M["br-lic"], "L3",
      f"Krishna Bank Ltd fell short of its SLR requirement on three consecutive days by ₹50 crore, ₹80 crore and ₹30 crore; it was compliant on the days before and after. Bank Rate is {pct(br2)}. "
      "Penal interest payable under s.24 (365-day year) is closest to:",
      R(psl),
      [(R(psl3), "charges Bank Rate + 3% on all three days"),
       (R(psl_3rd), "starts the Bank Rate + 5% rate only from the third day"),
       (R(psl_nobr), "applies 3%/5% flat without adding the Bank Rate")],
      [f"Day 1 (first day of default): Bank Rate + 3% = {pct(br2+.03)} on ₹50 crore.",
       f"Days 2–3 (continuing default): Bank Rate + 5% = {pct(br2+.05)} on ₹80 crore and ₹30 crore.",
       f"Penal = [50×9.75% + (80+30)×11.75%] crore ÷ 365 = {R(psl)}"],
      "Penal = Shortfall × (Bank Rate + 3% first day / 5% succeeding days) ÷ 365", "The 5% rate applies from the next succeeding day.",
      kind="numerical", verify_fact=True, ref=ref(BRA, "s.24(4)"))

B.add(M["br-lic"], "L2",
      "Which statement correctly describes RBI's power over the statutory liquidity ratio under s.24 of the BR Act as it now stands?",
      "RBI may specify SLR up to 40% of NDTL, with no floor",
      [("RBI must keep SLR between 25% and 40% of NDTL", "the 25% floor was removed by the 2007 amendment"),
       ("RBI may specify SLR up to 20% of NDTL", "confuses with the old CRR ceiling under s.42"),
       ("The Central Government fixes SLR; RBI only monitors it", "wrong authority")],
      ["s.24(2A): assets in cash, gold or unencumbered approved securities at a percentage not exceeding 40% of NDTL as RBI specifies.",
       "The Banking Regulation (Amendment) Act, 2007 removed the 25% floor."],
      "BR Act s.24(2A)", "Only the 40% ceiling survives.",
      kind="conceptual", verify_fact=True, ref=ref(BRA, "s.24(2A), BR (Amendment) Act 2007"))

# --- directions / removal ---
B.add(M["br-dir"], "L1",
      "Which of the following is NOT a ground on which RBI may issue directions to banking companies under s.35A of the BR Act?",
      "Maximising the dividend paid to the bank's shareholders",
      [("Public interest", "listed ground"),
       ("Preventing affairs being conducted detrimentally to depositors", "listed ground"),
       ("Securing the proper management of any banking company", "listed ground")],
      ["s.35A(1): directions in the public interest, in the interest of banking policy, to prevent affairs being conducted detrimentally to depositors or the bank, or to secure proper management."],
      "BR Act s.35A(1)", "Shareholder returns are not a statutory ground.",
      kind="conceptual", verify_fact=True, ref=ref(BRA, "s.35A"))

mx, curb = 12, 9
nad = min(5, mx // 3)
assert nad == 4
B.add(M["br-dir"], "L2",
      f"The articles of Pennar Bank Ltd fix the maximum board strength at {mx}; the board presently has {curb} directors. The maximum number of additional directors RBI may appoint under s.36AB is:",
      str(nad),
      [("5", "applies the absolute cap of five, ignoring 'whichever is less'"),
       ("3", "computes one-third of present strength instead of maximum strength"),
       ("6", "takes one-half of maximum strength")],
      ["s.36AB: RBI may appoint additional directors not exceeding five or one-third of the maximum strength fixed by the articles, whichever is less.",
       f"min(5, {mx}/3 = {mx//3}) = {nad}."],
      "Additional directors ≤ min(5, ⅓ × maximum strength)", "Maximum strength under the articles, not current strength.",
      kind="numerical", verify_fact=True, ref=ref(BRA, "s.36AB"))

amt, days = 72 * LK, 18
pmax = max(1 * CR, 2 * amt) + 1 * LK * (days - 1)
p_less = min(1 * CR, 2 * amt) + 1 * LK * (days - 1)
p_all = max(1 * CR, 2 * amt) + 1 * LK * days
p_nocont = max(1 * CR, 2 * amt)
assert pmax == 161 * LK
B.add(M["br-dir"], "L3",
      f"A banking company commits a contravention under s.46(4) of the BR Act involving a quantifiable amount of {lakh(amt,0)}. The contravention continues for {days} days in all. "
      "The maximum penalty RBI may impose under s.47A is:",
      cr(pmax),
      [(cr(p_less), "takes the lower of ₹1 crore and twice the amount"),
       (cr(p_all), "charges the daily penalty for the first day as well"),
       (cr(p_nocont), "omits the continuing-default penalty")],
      ["s.47A(1)(b): up to ₹1 crore or twice the amount involved (if quantifiable), whichever is more.",
       f"max(₹1 crore, 2 × {lakh(amt,0)} = {cr(2*amt)}) = {cr(max(CR,2*amt))}.",
       f"Continuing default: up to ₹1 lakh per day after the first → {days-1} × ₹1 lakh = {lakh(LK*(days-1),0)}.",
       f"Maximum = {cr(pmax)}."],
      "Penalty = max(₹1 cr, 2 × amount) + ₹1 lakh × (days − 1)", "'Whichever is more', and the daily add-on runs after the first day.",
      kind="numerical", verify_fact=True, ref=ref(BRA, "s.47A(1)(b)"))

# --- amalgamation / co-op ---
pres_m, pres_v, fav_m, fav_v = 120, 90 * LK, 70, 58 * LK
maj_n, two3 = fav_m > pres_m / 2, fav_v >= (2 / 3) * pres_v
assert maj_n and not two3
B.add(M["br-amal"], "L3",
      f"At the meeting of shareholders of Tapti Bank Ltd on a voluntary amalgamation scheme under s.44A, {pres_m} shareholders holding {inr(pres_v)} shares are present in person or by proxy. "
      f"{fav_m} shareholders holding {inr(fav_v)} shares vote in favour. The scheme:",
      "Fails, as 58 lakh shares are below two-thirds of shares present",
      [("Passes, as a majority in number of those present is in favour", "applies only the majority-in-number limb"),
       ("Passes, as more than half of the shares present are in favour", "applies simple majority by value"),
       ("Fails, as a majority in number of all shareholders is not present", "invents a majority-of-all-members quorum")],
      [f"s.44A(2): approval needs a majority in number representing two-thirds in value of shareholders present and voting.",
       f"Number: {fav_m} of {pres_m} → majority ✓.",
       f"Value: {inr(fav_v)} ÷ {inr(pres_v)} = {pct(fav_v/pres_v,1)} < 66.67% ✗ → resolution fails."],
      "Majority in number AND ⅔ in value of those present", "Both limbs; the value limb is ⅔, not ½.",
      kind="numerical", verify_fact=True, ref=ref(BRA, "s.44A(2)"))

c, wr = stmt_opts([True, True, True],
                  ["s.3 excludes primary agricultural credit societies",
                   "RBI may supersede a co-operative bank's board in consultation with the State Government (2020 amendment)",
                   "s.22 as applied by s.56 requires co-operative banks to hold an RBI licence"], flips=[0, 1, 2])
B.add(M["br-amal"], "L3",
      "Consider the following statements on co-operative banks and the BR Act, 1949 (as amended in 2020):\n\n" + stl([
          "The Act does not apply to a primary agricultural credit society.",
          "RBI may supersede the board of a co-operative bank, after consultation with the concerned State Government.",
          "A co-operative bank requires a licence from RBI under s.22, as applied to co-operative societies by s.56."]) +
      "\n\nWhich of the statements is/are correct?",
      c, wr,
      ["1: Correct — s.3.", "2: Correct — s.36ACA as applied through s.56 after the BR (Amendment) Act, 2020.",
       "3: Correct — s.22 applies to co-operative banks through Part V (s.56)."],
      "BR Act ss.3, 22, 36ACA, 56", "Co-operative banks are within RBI's banking regulation (Part V), barring PACS.",
      kind="statement", verify_fact=True, ref=ref(BRA, "ss.3, 22, 36ACA, 56; BR (Amendment) Act 2020"))

G2 = "BR-KONARK"
bcase = ("**Case — Konark Bank Ltd.** An RBI inspection of Konark Bank Ltd, a private sector bank, reveals large undisclosed NPAs, governance lapses and a sharp deposit run. "
         "RBI wants to (i) immediately restrict withdrawals, (ii) replace the management, and (iii) resolve the bank through amalgamation with a stronger bank. "
         "On 1 April 2026 RBI superseded the board for six months, and later extended the supersession by four months. "
         "Separately, on RBI's application, the Central Government ordered a moratorium for three months from 5 March 2026.")
B.add(M["br-dir"], "L4", bcase + "\n\n**Q1.** The provision RBI would use to immediately cap withdrawals at a fixed amount per depositor is:",
      "Section 35A — directions to a banking company",
      [("Section 45 — moratorium, which RBI orders itself", "the moratorium is ordered by the Central Government on RBI's application"),
       ("Section 36ACA — supersession of the board", "supersession changes management, not withdrawals"),
       ("Section 22(4) — cancellation of licence", "cancellation ends banking business rather than capping withdrawals")],
      ["s.35A lets RBI issue directions, including restricting acceptance of deposits and withdrawals, to protect depositors.",
       "s.45 moratorium is a Central Government order; s.36ACA addresses management."],
      "BR Act s.35A", "RBI cannot itself impose a s.45 moratorium.",
      kind="case", group=G2, verify_fact=True, ref=ref(BRA, "ss.35A, 45"))

sup_used = 6 + 4
B.add(M["br-dir"], "L4", bcase + "\n\n**Q2.** The maximum further period for which the supersession may be extended is:",
      f"{12 - sup_used} months",
      [(f"{24 - sup_used} months", "assumes a 24-month aggregate limit"),
       ("6 months", "assumes each extension may itself run six months, with no aggregate cap"),
       ("Nil — the first period can never be extended", "denies the power to extend within the aggregate")],
      ["s.36ACA: RBI, in consultation with the Central Government, may supersede the board for up to 12 months; extensions are allowed but the aggregate cannot exceed 12 months.",
       f"Used = 6 + 4 = {sup_used} months → further extension ≤ {12-sup_used} months."],
      "Aggregate supersession ≤ 12 months", "The 12-month cap is cumulative.",
      kind="case", group=G2, verify_fact=True, ref=ref(BRA, "s.36ACA"))

B.add(M["br-amal"], "L4", bcase + "\n\n**Q3.** The moratorium may be extended by the Central Government by at most:",
      "3 more months, as the total cannot exceed six months",
      [("9 more months, as the total cannot exceed twelve months", "confuses with the 12-month supersession cap"),
       ("No extension; a moratorium order cannot be extended at all", "denies extension within the aggregate limit"),
       ("3 more months, but only with Parliament's approval", "invents parliamentary approval")],
      ["s.45(2): the Central Government may order a moratorium on RBI's application; it may be extended from time to time, but the total period cannot exceed six months.",
       "Used 3 months → 3 more months at most."],
      "Moratorium ≤ 6 months in aggregate", "Six months for moratorium; twelve for supersession.",
      kind="case", group=G2, verify_fact=True, ref=ref(BRA, "s.45(2)"))

B.add(M["br-amal"], "L4", bcase + "\n\n**Q4.** A compulsory scheme of amalgamation of Konark Bank prepared by RBI under s.45 comes into force when:",
      "The Central Government sanctions the scheme",
      [("RBI itself sanctions the scheme it has prepared", "confuses with the s.44A voluntary route, where RBI sanctions"),
       ("The NCLT sanctions it after creditor meetings", "applies the Companies Act merger route"),
       ("Two-thirds in value of shareholders approve it", "applies the s.44A shareholder approval")],
      ["s.45: RBI prepares the scheme (during the moratorium or otherwise), invites suggestions, and forwards it to the Central Government.",
       "The Central Government sanctions it, with or without modifications; shareholder approval and NCLT sanction are not needed."],
      "BR Act s.45(4)–(7)", "s.44A voluntary: RBI sanctions; s.45 compulsory: Central Government sanctions.",
      kind="case", group=G2, verify_fact=True, ref=ref(BRA, "ss.44A, 45"))

B.add(M["br-dir"], "L4", bcase + "\n\n**Q5.** RBI removes Konark's managing director and CEO under s.36AA. His statutory remedy is:",
      "Appeal to the Central Government within 30 days of the order",
      [("Appeal to the Securities Appellate Tribunal within 45 days", "wrong forum"),
       ("Petition to the NCLT for oppression and mismanagement", "company-law remedy, not the s.36AA appeal"),
       ("Appeal to the RBI Central Board within 60 days", "wrong forum and time limit")],
      ["s.36AA(3): a person removed may appeal to the Central Government within 30 days of the communication of the order; its decision is final."],
      "BR Act s.36AA", "Same 30-day Central Government appeal pattern as s.22(5).",
      kind="case", group=G2, verify_fact=True, ref=ref(BRA, "s.36AA"))

# =====================================================================
# DICGC ACT, 1961 (20)
# =====================================================================
B.add(M["dic-cover"], "L1",
      "Deposit insurance by DICGC for a depositor of an insured bank currently covers:",
      "Principal and interest up to ₹5 lakh per depositor per bank, same capacity",
      [("Principal only up to ₹5 lakh, with interest paid over and above", "treats interest as outside the ₹5 lakh cap"),
       ("Principal and interest up to ₹1 lakh per depositor per bank", "the limit before 4 February 2020"),
       ("Principal and interest up to ₹5 lakh per depositor across all banks", "aggregates across banks instead of per bank")],
      ["The limit was raised from ₹1 lakh to ₹5 lakh with effect from 4 February 2020.",
       "It covers principal and interest together, per depositor per bank, in the same right and capacity."],
      "Cover = min(principal + interest, ₹5 lakh) per bank per capacity", "Interest sits inside the cap.",
      kind="conceptual", verify_fact=True, ref=ref(DIC, "s.16(1) and DICGC notification (₹5 lakh from 4 Feb 2020)"))

B.add(M["dic-elig"], "L1",
      "Which of the following is NOT covered by DICGC deposit insurance?",
      "A primary agricultural society",
      [("A regional rural bank in Odisha", "RRBs are insured banks"),
       ("A local area bank licensed by RBI", "LABs are insured banks"),
       ("An urban co-operative bank", "eligible co-operative banks are insured")],
      ["All commercial banks (including RRBs, LABs, and branches of foreign banks in India) and eligible co-operative banks are insured.",
       "Primary agricultural credit societies are not insured banks."],
      "DICGC Act s.2(gg), Chapter III", "PACS are outside both the BR Act (s.3) and deposit insurance.",
      kind="conceptual", verify_fact=True, ref=ref(DIC, "ss.2(gg), 13A"))

B.add(M["dic-elig"], "L2",
      "In a failed insured commercial bank, which of the following deposits qualifies for DICGC insurance?",
      "NRI's savings deposit held at a Delhi branch",
      [("Deposit of a State Government department", "State Government deposits are excluded"),
       ("Deposit of a foreign Government's embassy", "foreign Government deposits are excluded"),
       ("Term deposit placed by another bank", "inter-bank deposits are excluded")],
      ["s.2(g) excludes deposits of foreign Governments, Central/State Governments, other banks, and amounts received outside India.",
       "An NRI's deposit received in India is not excluded."],
      "DICGC Act s.2(g)", "Residence of the depositor does not matter; place of receipt does.",
      kind="case", verify_fact=True, ref=ref(DIC, "s.2(g)"))

c, wr = stmt_opts([True, True, False],
                  ["RRBs and LABs are insured", "foreign bank branches in India are insured",
                   "deposits received outside India are excluded by s.2(g)"], flips=[0, 1, 2])
B.add(M["dic-elig"], "L3",
      "Consider the following statements on deposit insurance coverage:\n\n" + stl([
          "Regional rural banks and local area banks are insured banks.",
          "Deposits with branches in India of a bank incorporated abroad are insured.",
          "Deposits received at the London branch of an Indian public sector bank are insured."]) +
      "\n\nWhich of the statements is/are correct?",
      c, wr,
      ["1: Correct.", "2: Correct — foreign banks' Indian branches are insured.",
       "3: Incorrect — amounts due on deposits received outside India are excluded."],
      "DICGC Act s.2(g)", "Ownership of the bank is irrelevant; place of receipt is decisive.",
      kind="statement", verify_fact=True, ref=ref(DIC, "s.2(g)"))

# --- cover computations ---
b1, b2, b3 = 3.4 * LK, 1.7 * LK, 1.9 * LK
agg = b1 + b2 + b3
ins = min(agg, 5 * LK)
B.add(M["dic-cover"], "L2",
      f"Mr Joshi, in his individual capacity, holds at Laxmi Bank a savings account of {lakh(b1)} at its Pune branch, a fixed deposit of {lakh(b2)} at its Nashik branch and a recurring deposit of {lakh(b3)} at its Pune branch (all inclusive of interest). "
      "If the bank is liquidated, DICGC's liability to him is:",
      lakh(ins),
      [(lakh(agg), "no cap applied to the aggregated balance"),
       (lakh(min(b1 + b3, 5 * LK) + min(b2, 5 * LK)), "caps separately branch by branch"),
       (lakh(min(b1, 5 * LK)), "covers only the single largest account")],
      [f"Same bank, same capacity → aggregate across branches: {lakh(b1)} + {lakh(b2)} + {lakh(b3)} = {lakh(agg)}.",
       f"Cover = min({lakh(agg)}, ₹5 lakh) = {lakh(ins)}."],
      "Cover = min(Σ same-capacity balances in the bank, ₹5 lakh)", "Branches are not separate banks.",
      kind="numerical", verify_fact=True, ref=ref(DIC, "s.16(1)"))

rows = [("Savings a/c at Shreyas Bank — Pradeep alone", "Aggregated with his other individual deposits"),
        ("Joint FD at Shreyas Bank — Pradeep and his wife", "Separate capacity; insured separately"),
        ("FD at Unnati Bank — Pradeep alone", "Separate bank; insured separately"),
        ("FD at Shreyas Bank — Pradeep as guardian of his minor son", "Separate capacity; insured separately")]
B.add(M["dic-cover"], "L3",
      "Pradeep already has an individual fixed deposit at Shreyas Bank. Match each additional deposit with its treatment for the ₹5 lakh cover:\n\n"
      + table(["Deposit", "Treatment"],
              [["P. Savings a/c at Shreyas Bank in his sole name", "1. Separate bank; separate ₹5 lakh cover"],
               ["Q. Joint FD at Shreyas Bank with his wife", "2. Aggregated with his existing individual FD"],
               ["R. FD at Unnati Bank in his sole name", "3. Held as guardian of a minor; separate capacity"],
               ["S. FD at Shreyas Bank for his minor son", "4. Different right and capacity (joint holding); separate cover"]], ["---", "---"]),
      "P-2, Q-4, R-1, S-3",
      [("P-1, Q-4, R-2, S-3", "treats an account at another branch/type as a separate bank and aggregates across banks"),
       ("P-2, Q-2, R-1, S-3", "aggregates the joint FD with his individual deposits"),
       ("P-2, Q-4, R-2, S-3", "aggregates deposits across two different banks")],
      ["Same bank, same capacity → aggregated (P).", "Joint account is a different capacity → separate (Q).",
       "Different insured bank → separate (R).", "Deposit held as guardian for a minor → separate capacity (S)."],
      "Aggregate only within the same bank and the same right and capacity", "Different bank or different capacity → separate cover.",
      kind="conceptual", verify_fact=True, ref=ref(DIC, "s.16(1); DICGC 'same right and capacity' rule"))

fdp, fdi, sq = 4.85 * LK, 0.30 * LK, 3.6 * LK
tot2 = min(fdp + fdi, 5 * LK) + min(sq, 5 * LK)
B.add(M["dic-cover"], "L3",
      f"Mrs Dsouza holds a fixed deposit of {lakh(fdp)} with accrued interest of {lakh(fdi)} at Pragati Bank, and a savings balance of {lakh(sq)} at Samruddhi Bank, both in her sole name. "
      "Both banks are liquidated. Her total insured claim on DICGC is:",
      lakh(tot2),
      [(lakh(5 * LK), "applies one ₹5 lakh cap across both banks"),
       (lakh(fdp + sq), "excludes interest from cover"),
       (lakh(fdp + fdi + sq), "does not cap the Pragati Bank balance")],
      [f"Pragati: min({lakh(fdp)} + {lakh(fdi)} = {lakh(fdp+fdi)}, ₹5 lakh) = ₹5.00 lakh.",
       f"Samruddhi: {lakh(sq)} (below cap).", f"Total = {lakh(tot2)}."],
      "Σ over banks of min(principal + interest, ₹5 lakh)", "The cap is per bank; interest counts towards it.",
      kind="numerical", verify_fact=True, ref=ref(DIC, "s.16(1)"))

dpa, rpct = 8 * LK, 0.40
recd = dpa * rpct
pay = min(dpa, 5 * LK) - recd
B.add(M["dic-cover"], "L2",
      f"Under an RBI-sanctioned scheme of amalgamation, depositors of a weak insured bank receive {pct(rpct,0)} of their balances from the transferee bank. "
      f"A depositor had {lakh(dpa,0)} (principal plus interest). DICGC's liability to her is:",
      lakh(pay),
      [(lakh(dpa - recd), "pays the full shortfall without the insured-limit cap"),
       (lakh(5 * LK), "ignores the amount received under the scheme"),
       (lakh(5 * LK * (1 - rpct)), "applies the 60% shortfall to the ₹5 lakh limit")],
      [f"Received under scheme = {pct(rpct,0)} × {lakh(dpa,0)} = {lakh(recd)}.",
       "s.16(2): DICGC pays the lower of (original deposit − amount received) and (insured limit − amount received).",
       f"= min({lakh(dpa-recd)}, {lakh(5*LK-recd)}) = {lakh(pay)}."],
      "Payment = min(Deposit, ₹5 lakh) − Amount received under scheme", "The insured limit caps what the depositor ends up with.",
      kind="numerical", verify_fact=True, ref=ref(DIC, "s.16(2)"))

o, w_ = ar_opts(2, {0: "accepts R, which is false: liability also arises on amalgamation/reconstruction and on RBI restrictions",
                    1: "accepts R, which is false",
                    3: "rejects A, which s.16(2) supports"})
B.add(M["dic-cover"], "L3",
      "**Assertion (A):** When an insured bank is amalgamated under a scheme and a depositor receives less than the insured limit, DICGC makes good the shortfall up to that limit.\n\n"
      "**Reason (R):** DICGC's liability to depositors arises only when an insured bank is wound up.",
      o, w_,
      ["A is true — s.16(2) covers schemes of compromise, arrangement, reconstruction or amalgamation.",
       "R is false — liability also arises under s.16(2) and, since 2021, under s.18A when RBI restricts withdrawals."],
      "DICGC Act ss.16(1), 16(2), 18A", "Liquidation is only one of three triggers.",
      kind="assertion-reason", verify_fact=True, ref=ref(DIC, "ss.16, 18A"))

cd_, dd_ = 20 * LK, 3 * LK
cpay = min(cd_, 5 * LK) + min(dd_, 5 * LK)
B.add(M["dic-cover"], "L2",
      f"At a liquidated insured bank, Nova Tools Pvt Ltd has a current account balance of {lakh(cd_,0)} and its managing director Mr Iyer has an individual savings balance of {lakh(dd_,0)} (both inclusive of interest). "
      "DICGC's total liability for these two accounts is:",
      lakh(cpay),
      [(lakh(5 * LK), "treats the company and its director as one depositor"),
       (lakh(dd_), "assumes deposits of companies are not insured"),
       (lakh(cd_ + dd_), "applies no cap to either account")],
      ["Every depositor — individual, firm or company — is insured up to ₹5 lakh per bank; a company is a separate depositor from its directors.",
       f"Company: min({lakh(cd_,0)}, ₹5 lakh) = ₹5.00 lakh; Mr Iyer: {lakh(dd_)}.", f"Total = {lakh(cpay)}."],
      "Σ per depositor of min(balance, ₹5 lakh)", "Corporate deposits are insured, and separately from directors'.",
      kind="numerical", verify_fact=True, ref=ref(DIC, "s.16(1)"))

# --- premium ---
ad, prate = 860 * CR, 0.12 / 100
hp = ad * prate / 2
B.add(M["dic-prem"], "L2",
      f"An insured bank's assessable deposits at the end of the previous half-year were {cr(ad,0)}. Premium is 12 paise per ₹100 of assessable deposits per annum, payable half-yearly (given). "
      "The premium for the half-year is:",
      lakh(hp),
      [(lakh(2 * hp), "charges the full annual rate for a half-year"),
       (lakh(hp / 2), "treats the premium as payable quarterly"),
       (lakh(hp / 10), "reads 12 paise per ₹100 as 12 paise per ₹1,000")],
      [f"Annual rate = 12/10,000 = {prate*100:.2f}% of assessable deposits.",
       f"Half-year premium = {cr(ad,0)} × 0.12% ÷ 2 = {lakh(hp)}."],
      "Premium = Assessable deposits × rate × ½", "Rate is per annum; the instalment is half-yearly.",
      kind="numerical", verify_fact=True, ref=ref(DIC, "s.15 (premium rate given in stem)"))

td, sg, ib, fg, insd = 2400 * CR, 150 * CR, 90 * CR, 10 * CR, 1100 * CR
ass = td - sg - ib - fg
p2 = ass * prate / 2
B.add(M["dic-prem"], "L3",
      f"Details of Surya Bank Ltd at the end of the previous half-year (₹ crore): total deposits {inr(td/CR)}, of which State Government deposits {inr(sg/CR)}, deposits of other banks {inr(ib/CR)} and a foreign Government's deposit {inr(fg/CR)}. "
      f"The insured portion (balances up to ₹5 lakh per depositor) is {inr(insd/CR)}. At 12 paise per ₹100 per annum (given), the half-yearly premium is:",
      lakh(p2),
      [(lakh(td * prate / 2), "computes premium on total deposits without exclusions"),
       (lakh(insd * prate / 2), "computes premium only on the insured portion"),
       (lakh(ass * prate), "charges the annual rate for a half-year")],
      [f"Assessable deposits = {inr(td/CR)} − {inr(sg/CR)} − {inr(ib/CR)} − {inr(fg/CR)} = {inr(ass/CR)} crore.",
       f"Half-year premium = {inr(ass/CR)} crore × 0.12% ÷ 2 = {lakh(p2)}."],
      "Premium = (Total − excluded deposits) × rate × ½", "Premium is on assessable deposits, not just the insured slice.",
      kind="numerical", verify_fact=True, ref=ref(DIC, "ss.2(g), 15"))

B.add(M["dic-prem"], "L1",
      "The deposit insurance premium payable to DICGC is borne by:",
      "The insured bank, which cannot recover it from depositors",
      [("Depositors, through a deduction from interest credited", "assumes the cost is passed on to depositors"),
       ("The Central Government, through budgetary support", "invented Government funding"),
       ("RBI, as the sole owner of DICGC", "confuses ownership with premium liability")],
      ["The insured bank pays the premium half-yearly on its assessable deposits and bears it itself; it is not charged to depositors."],
      "DICGC Act s.15", "Ownership of DICGC by RBI does not shift the premium burden.",
      kind="conceptual", verify_fact=True, ref=ref(DIC, "s.15"))

# --- timelines ---
B.add(M["dic-time"], "L1",
      "After the DICGC (Amendment) Act, 2021, depositors of an insured bank placed under RBI directions restricting withdrawals receive insured amounts within:",
      "90 days of the directions being imposed",
      [("45 days of the directions being imposed", "the 45-day step is only the bank's submission of depositor details"),
       ("Two months of the liquidator submitting the claim list", "the liquidation-route timeline"),
       ("180 days of the directions being imposed", "invented longer timeline")],
      ["s.18A (2021): 45 days for the bank to submit depositor details, 30 days for DICGC verification, payment in the next 15 days — 90 days in all."],
      "45 + 30 + 15 = 90 days", "90 days is the whole cycle.",
      kind="conceptual", verify_fact=True, ref=ref(DIC, "s.18A (DICGC (Amendment) Act 2021)"))

ld = date(2026, 2, 10)
lst = add_months(ld, 3)
rec = date(2026, 5, 2)
pd_ = add_months(rec, 2)
B.add(M["dic-time"], "L2",
      f"A liquidator assumes charge of a failed insured bank on {dfmt(ld)} and sends the depositor claim list to DICGC on {dfmt(rec)}. "
      "The statutory deadlines for the list and for DICGC's payment are respectively:",
      f"{dfmt(lst)} and {dfmt(pd_)}",
      [(f"{dfmt(lst)} and {dfmt(add_months(ld,5))}", "measures the payment period from the liquidator taking charge"),
       (f"{dfmt(add_months(ld,2))} and {dfmt(add_months(rec,3))}", "swaps the three-month and two-month periods"),
       (f"{dfmt(lst)} and {dfmt(rec + timedelta(days=90))}", "applies the 90-day s.18A timeline to liquidation")],
      [f"Liquidator: list within 3 months of assuming charge → {dfmt(lst)} (sent on {dfmt(rec)}, in time).",
       f"DICGC: pay within 2 months of receiving the list → {dfmt(pd_)}."],
      "List ≤ 3 months; payment ≤ 2 months from receipt", "The two-month clock starts on receipt of the list.",
      kind="numerical", verify_fact=True, ref=ref(DIC, "ss.16(1), 17"))

c, wr = stmt_opts([True, True, False],
                  ["s.18A covers banks under RBI withdrawal restrictions", "45 + 30 + 15 = 90 days",
                   "the ₹5 lakh cover dates from February 2020, not the 2021 Act"], flips=[0, 1, 2])
B.add(M["dic-time"], "L3",
      "Consider the following statements on the DICGC (Amendment) Act, 2021:\n\n" + stl([
          "It enables payment to depositors of a bank under RBI directions restricting withdrawals, without waiting for liquidation.",
          "The bank must submit depositor details within 45 days of the directions, and payment must be made within 90 days of the directions.",
          "It raised the insurance cover from ₹1 lakh to ₹5 lakh per depositor."]) +
      "\n\nWhich of the statements is/are correct?",
      c, wr,
      ["1: Correct — s.18A.", "2: Correct — 45-day submission; payment by day 90.",
       "3: Incorrect — the ₹5 lakh limit took effect on 4 February 2020 under DICGC's notification, before the 2021 Act."],
      "DICGC Act s.18A", "The 2021 Act changed timing, not the cover amount.",
      kind="statement", verify_fact=True, ref=ref(DIC, "s.18A; DICGC notification Feb 2020"))

G3 = "DICGC-SAHAKAR"
rd = date(2026, 1, 20)
d45, d75, d90 = rd + timedelta(days=45), rd + timedelta(days=75), rd + timedelta(days=90)
assert d45 == date(2026, 3, 6) and d90 == date(2026, 4, 20)
dcase = (f"**Case — Sahakar Urban Co-operative Bank.** On {dfmt(rd)}, RBI issued directions under s.35A (read with s.56) of the BR Act to Sahakar Urban Co-operative Bank, an insured bank, "
         "prohibiting all withdrawals. The bank is not in liquidation and no scheme of amalgamation has been notified. Selected accounts:\n\n"
         + table(["Depositor / capacity", "Balance incl. interest (₹ lakh)"], [
             ["Mr Vikram — savings, individual", "1.80"], ["Mr Vikram — FD, individual", "3.45"],
             ["Mr Vikram and Mrs Vikram — joint FD", "2.40"], ["Vikram & Sons (partnership firm) — current a/c", "6.50"],
             ["Ms Leela — FD, individual", "4.20"], ["State Government department — deposit", "40.00"],
             ["District Central Co-operative Bank — term deposit", "25.00"]]))
B.add(M["dic-time"], "L4", dcase + "\n\n**Q1.** The last date by which the bank must furnish depositor details to DICGC is:",
      dfmt(d45),
      [(dfmt(rd + timedelta(days=30)), "takes 30 days, DICGC's verification window, as the bank's deadline"),
       (dfmt(d90), "treats the 90-day payment deadline as the submission deadline"),
       (dfmt(d75), "takes the end of DICGC's 30-day verification window (day 75) as the bank's deadline")],
      [f"s.18A: bank to submit within 45 days of the directions: {dfmt(rd)} + 45 days = {dfmt(d45)}."],
      "Submission = directions date + 45 days", "45 days is the bank's step; 30 and 15 days belong to DICGC.",
      kind="case", group=G3, verify_fact=True, ref=ref(DIC, "s.18A"))

B.add(M["dic-time"], "L4", dcase + "\n\n**Q2.** The latest date by which eligible depositors should receive their insured amounts is:",
      dfmt(d90),
      [(dfmt(d75), "stops at the end of DICGC's verification window"),
       (dfmt(d45 + timedelta(days=90)), "starts the 90 days from the bank's submission date"),
       (dfmt(add_months(d45, 2)), "applies the liquidation rule of two months from receipt of list")],
      ["45 days (bank) + 30 days (DICGC verification) + 15 days (payment) = 90 days from the directions.",
       f"{dfmt(rd)} + 90 days = {dfmt(d90)}."],
      "Payment by directions date + 90 days", "The 90 days run from the directions, not from submission.",
      kind="case", group=G3, verify_fact=True, ref=ref(DIC, "s.18A"))

v_ind = min(1.80 + 3.45, 5.0)
v_all = v_ind + min(2.40, 5) + min(6.50, 5)
v_one = 5.0
v_nocap = 1.80 + 3.45 + 2.40 + 6.50
v_indnocap = (1.80 + 3.45) + 2.40 + 5.0
assert abs(v_all - 12.4) < 1e-9
B.add(M["dic-cover"], "L4", dcase + "\n\n**Q3.** Total insured amount payable in respect of the four accounts linked to the Vikram family (individual, joint and firm) is:",
      f"₹{v_all:.2f} lakh",
      [(f"₹{v_indnocap:.2f} lakh", "does not cap Mr Vikram's aggregated individual deposits"),
       (f"₹{v_one:.2f} lakh", "applies a single ₹5 lakh cap to everything linked to Mr Vikram"),
       (f"₹{v_nocap:.2f} lakh", "pays all balances in full without any cap")],
      [f"Individual: 1.80 + 3.45 = 5.25 → capped at ₹5.00 lakh.",
       "Joint FD (different capacity): ₹2.40 lakh.", "Firm (separate depositor): 6.50 → capped at ₹5.00 lakh.",
       f"Total = 5.00 + 2.40 + 5.00 = ₹{v_all:.2f} lakh."],
      "Σ min(capacity-wise balance, ₹5 lakh)", "Cap each capacity separately; aggregate within a capacity.",
      kind="case", group=G3, verify_fact=True, ref=ref(DIC, "ss.16, 18A"))

bank_tot = v_all + min(4.20, 5)
inc_ex = bank_tot + 5 + 5
inc_nocap = 1.80 + 3.45 + 2.40 + 6.50 + 4.20
only_ind = 5.0 + 4.20
B.add(M["dic-elig"], "L4", dcase + "\n\n**Q4.** DICGC's total liability for all the accounts in the table is:",
      f"₹{bank_tot:.2f} lakh",
      [(f"₹{inc_ex:.2f} lakh", "also insures the State Government and inter-bank deposits up to ₹5 lakh each"),
       (f"₹{inc_nocap:.2f} lakh", "excludes Government/inter-bank deposits but applies no cap"),
       (f"₹{only_ind:.2f} lakh", "covers only individual-capacity deposits, dropping joint and firm accounts")],
      [f"Vikram-linked accounts: ₹{v_all:.2f} lakh (as capped by capacity).", "Ms Leela: ₹4.20 lakh (below cap).",
       "State Government and inter-bank deposits are excluded by s.2(g).",
       f"Total = {v_all:.2f} + 4.20 = ₹{bank_tot:.2f} lakh."],
      "Σ eligible capped amounts; exclude s.2(g) deposits", "Government and inter-bank deposits get nothing, not ₹5 lakh.",
      kind="case", group=G3, verify_fact=True, ref=ref(DIC, "ss.2(g), 16, 18A"))

# =====================================================================
QUOTA = {RBI: 25, BRA: 25, DIC: 20}
act_of = {M[k]: a for k, _, a in MICROS}
cnt = Counter(act_of[q["microtopic_slug"]] for q in B.Q)
assert dict(cnt) == QUOTA, cnt
assert len(B.Q) == 70
assert all(q["verify_fact"] for q in B.Q)
for a in QUOTA:
    lv = Counter(q["rubric_level"] for q in B.Q if act_of[q["microtopic_slug"]] == a)
    print(a, dict(sorted(lv.items())))
print("groups", Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"]))
B.write()
