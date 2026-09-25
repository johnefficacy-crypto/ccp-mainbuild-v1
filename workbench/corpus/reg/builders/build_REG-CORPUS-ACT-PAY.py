"""REG-CORPUS-ACT-PAY — financial-sector-acts: payment, credit-information, factoring and NI Acts. 88 Q.
Acts: PSS Act 2007 (24), CICRA 2005 (22), Factoring Regulation Act 2011 (20), NI Act 1881 (22).
Every numeric / date key and distractor is computed below; asserts guard the keys.
Run: python3 builders/build_REG-CORPUS-ACT-PAY.py
"""
import os as _os, sys, csv
from datetime import date, timedelta

_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
from reglib import Batch, inr, R, pct, lakh, crore, make_slug  # noqa: E402

BATCH = "REG-CORPUS-ACT-PAY"
LIST = _os.path.join(_REG, "lists", f"fsa.{BATCH}.tsv")

PSS = "Payment and Settlement Systems Act, 2007"
CIC = "Credit Information Companies (Regulation) Act, 2005"
FRA = "Factoring Regulation Act, 2011"
NIA = "Negotiable Instruments Act, 1881"

MICROS = [
    ("pss_auth", "PSS Act — authorisation, revocation and appeal (s.4–s.9, s.34)", PSS),
    ("pss_prb", "PSS Act — designated authority and Payments Regulatory Board (s.3)", PSS),
    ("pss_setl", "PSS Act — settlement finality, netting and customer funds (s.23, s.23A)", PSS),
    ("pss_dir", "PSS Act — RBI directions and oversight (s.17)", PSS),
    ("pss_pen", "PSS Act — offences, penalties and EFT dishonour (s.25–s.30)", PSS),
    ("cic_reg", "CICRA — registration and minimum capital of credit information companies", CIC),
    ("cic_mem", "CICRA — credit institutions, membership and specified users", CIC),
    ("cic_priv", "CICRA — privacy principles and unauthorised access", CIC),
    ("cic_corr", "CICRA — correction of credit information and dispute timelines", CIC),
    ("cic_pen", "CICRA — offences and RBI penalties", CIC),
    ("fra_def", "Factoring Act — factoring business, assignor, debtor and receivables", FRA),
    ("fra_reg", "Factoring Act — registration of factors and RBI powers", FRA),
    ("fra_asg", "Factoring Act — assignment, notice and rights of the factor", FRA),
    ("fra_cersai", "Factoring Act — registration of assignments with CERSAI and TReDS", FRA),
    ("fra_pen", "Factoring Act — penalties", FRA),
    ("ni_inst", "NI Act — promissory notes, bills of exchange and cheques", NIA),
    ("ni_hold", "NI Act — holder, holder in due course and negotiation", NIA),
    ("ni_mat", "NI Act — maturity and days of grace", NIA),
    ("ni_cross", "NI Act — crossing of cheques and banker protection", NIA),
    ("ni_138", "NI Act — cheque dishonour under s.138 and complaint timelines", NIA),
    ("ni_comp", "NI Act — interim compensation and appeal deposit (s.143A, s.148)", NIA),
]
_os.makedirs(_os.path.dirname(LIST), exist_ok=True)
with open(LIST, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(["slug", "exams", "name", "act"])
    for _, name, act in MICROS:
        w.writerow([make_slug(name, "fsa"), "ifsca,pfrda,sebi", name, act])
M = {k: make_slug(name, "fsa") for k, name, _ in MICROS}

B = Batch(BATCH, "financial-sector-acts", "ACTP", list_file=LIST)


def add(mk, level, stem, correct, wrongs, steps, formula, trap, kind, ref, group=None):
    return B.add(micro=M[mk], level=level, stem=stem, correct=correct, wrongs=wrongs, steps=steps,
                 formula=formula, trap=trap, kind=kind, group=group, verify_fact=True, ref=ref)


# ---------- date helpers ----------
def D(s): return date.fromisoformat(s)
def fd(x): return f"{x.day} {x.strftime('%B %Y')}"
def plus(x, n): return x + timedelta(days=n)


def addm(x, m):
    y, mo = x.year + (x.month - 1 + m) // 12, (x.month - 1 + m) % 12 + 1
    nxt = date(y + (mo == 12), mo % 12 + 1, 1)
    last = (nxt - timedelta(days=1)).day
    return date(y, mo, min(x.day, last))


def weekday_ok(x): return x.weekday() < 5  # Mon–Fri, so no Sunday/holiday extension issue


def L(x): return lakh(x)          # "₹x.xx lakh"
def C(x): return crore(x)         # "₹x.xx crore"


LAKH, CR = 1e5, 1e7
STMT = ["1 only", "1 and 2 only", "2 and 3 only", "1 and 3 only", "1, 2 and 3"]

# =====================================================================================
#  PAYMENT AND SETTLEMENT SYSTEMS ACT, 2007  (24)
# =====================================================================================
# ---- L1 (5)
add("pss_auth", "L1",
    "Under s.4(1) of the Payment and Settlement Systems Act, 2007, a person other than the Reserve Bank may commence or operate a payment system only:",
    "Under and in accordance with an authorisation issued by the RBI",
    [("After registering the system with the Central Government", "wrong authority — Central Government only hears appeals (s.9)"),
     ("Under a banking licence issued by the RBI under the BR Act", "neighbouring statute — BR Act s.22 licence is not a PSS authorisation"),
     ("After obtaining approval from NPCI as umbrella body", "confuses a system operator with the regulator")],
    ["s.4(1): no person other than the RBI shall commence or operate a payment system except under and in accordance with an RBI authorisation.",
     "Provisos exempt agents of a payee, intra-group payment acceptance and RBI-exempted persons; otherwise authorisation is mandatory."],
    "PSS Act s.4(1)", "NPCI itself is an authorised system provider, not the authorising body.",
    "conceptual", f"{PSS}, s.4")

add("pss_prb", "L1",
    "Following the Payments Regulatory Board Regulations, 2025, the RBI exercises its powers and functions under the PSS Act through which body?",
    "The Payments Regulatory Board under s.3(2)",
    [("The Board for Regulation and Supervision of PSS", "outdated — BPSS was replaced by the PRB in 2025"),
     ("The Board for Financial Supervision of the RBI", "bank-supervision committee, not the PSS regulator"),
     ("The Monetary Policy Committee under the RBI Act", "confuses payment regulation with monetary policy")],
    ["s.3(1): the RBI is the designated authority for regulation and supervision of payment systems.",
     "s.3(2) (as amended by the Finance Act, 2019 and operationalised by the PRB Regulations, 2025): the RBI acts through the Payments Regulatory Board.",
     "The PRB replaced the earlier Board for Regulation and Supervision of Payment and Settlement Systems (BPSS)."],
    "PSS Act s.3(1)–(2)", "BPSS is the pre-2025 answer found in older texts.",
    "conceptual", f"{PSS}, s.3 (as amended by Finance Act 2019; PRB Regulations 2025)")

add("pss_setl", "L1",
    "Under Explanation 1 to s.23 of the PSS Act, a settlement effected under the approved netting procedure becomes final and irrevocable:",
    "When the amount payable is determined, even if not yet paid",
    [("Only when the net amount is actually paid by the participant", "reads finality as payment — the Explanation says 'whether or not actually paid'"),
     ("At the close of the settlement day after RBI's reconciliation", "invents a reconciliation step"),
     ("When the system provider's board ratifies the settlement batch", "invents a board-ratification step")],
    ["Explanation 1 to s.23: settlement is final and irrevocable as soon as the money, securities, foreign exchange or derivatives payable as a result of netting are determined.",
     "This holds whether or not the amount is actually paid."],
    "PSS Act s.23(3) with Explanation 1", "Finality attaches at determination, not at payment.",
    "conceptual", f"{PSS}, s.23")

add("pss_auth", "L1",
    "By virtue of s.34, the Payment and Settlement Systems Act, 2007 does NOT apply to:",
    "Stock exchanges and their clearing corporations",
    [("Card networks operating debit and credit card schemes", "card networks are payment systems needing authorisation"),
     ("Issuers of prepaid payment instruments such as wallets", "PPI issuers are authorised under the Act"),
     ("Cross-border money transfer service scheme operators", "MTSS operators are authorised under the Act")],
    ["s.34: nothing in the Act applies to stock exchanges or clearing corporations of stock exchanges.",
     "Those are regulated by SEBI under securities laws; all other payment systems need RBI authorisation."],
    "PSS Act s.34", "Card schemes, wallets and MTSS are the classic authorised payment systems.",
    "conceptual", f"{PSS}, s.34")

add("pss_dir", "L1",
    "The RBI may issue directions under s.17 of the PSS Act to a payment system or system participant when it is of the opinion that the conduct results or is likely to result in:",
    "Systemic risk being inadequately controlled",
    [("A decline in the system provider's annual profit", "commercial performance is not a s.17 trigger"),
     ("A single customer complaint remaining unresolved", "grievance handling is not the s.17 test"),
     ("A system participant choosing to exit the system", "exit per system rules is not the statutory trigger")],
    ["s.17(a): conduct resulting (or likely to result) in systemic risk being inadequately controlled; or",
     "s.17(b): such action likely to affect the payment system, monetary policy or credit policy.",
     "Directions may require cease-and-desist or remedial acts within the time the RBI specifies."],
    "PSS Act s.17", "The test is systemic risk / policy impact, not individual commercial events.",
    "conceptual", f"{PSS}, s.17")

# ---- L2 (7)
comm = D("2026-03-04"); app_last = plus(comm, 30)
add("pss_auth", "L2",
    f"The RBI's order revoking the authorisation of a payment system operator is communicated to it on {fd(comm)}. Counting 30 days and excluding the day of communication, the operator's statutory appeal lies to:",
    f"The Central Government, on or before {fd(app_last)}",
    [(f"The Central Board of the RBI, on or before {fd(app_last)}", "wrong forum — s.9 appeal lies to the Central Government"),
     (f"The Central Government, on or before {fd(plus(comm, 29))}", "day of communication counted in the 30 days"),
     (f"The Central Government, on or before {fd(addm(comm, 3))}", "confuses 3-month decision target with the filing period")],
    [f"s.9: appeal against refusal (s.7) or revocation (s.8) lies to the Central Government within 30 days of communication.",
     f"{fd(comm)} + 30 days = {fd(app_last)}.",
     "The Central Government endeavours to dispose of the appeal within three months; its decision is final."],
    "PSS Act s.9", "Three months is the Government's disposal target, not the filing window.",
    "numerical", f"{PSS}, s.9")

filed = D("2026-01-12")
add("pss_auth", "L2",
    f"An application for authorisation to operate a payment system is filed with the RBI on {fd(filed)}. Under s.7(4), the RBI shall endeavour to dispose of it by:",
    fd(addm(filed, 6)),
    [(fd(addm(filed, 3)), "confuses with the Central Government's 3-month appeal target"),
     (fd(plus(filed, 30)), "confuses with the 30-day appeal period under s.9"),
     (fd(addm(filed, 12)), "assumes a one-year processing period")],
    ["s.7(4): applications are to be processed as soon as possible, endeavouring to decide within six months of filing.",
     f"{fd(filed)} + 6 months = {fd(addm(filed, 6))}."],
    "PSS Act s.7(4)", "Six months for the RBI; 30 days / 3 months belong to the s.9 appeal.",
    "numerical", f"{PSS}, s.7(4)")

amt = 6.2 * LAKH
cap = max(10 * LAKH, 2 * amt)
assert cap == 12.4 * LAKH
add("pss_pen", "L2",
    f"An authorised operator fails to furnish information called for by the RBI; the amount involved in the default is quantified at {L(amt)}. The maximum penalty the RBI can impose under s.30(1) (ignoring any continuing default) is:",
    L(cap),
    [(L(10 * LAKH), "took the ₹10 lakh limb, ignoring 'whichever is more'"),
     (L(amt), "amount involved taken instead of twice the amount"),
     (L(10 * LAKH + 2 * amt), "added both limbs instead of taking the higher")],
    ["s.26(3) defaults attract penalty under s.30.",
     f"s.30(1): higher of ₹10 lakh and twice the amount involved = max(10, 2 × {amt/LAKH:.1f}) lakh = {L(cap)}."],
    "Penalty ≤ max(₹10 lakh, 2 × amount involved)", "It is the higher of the two limbs, not their sum.",
    "numerical", f"{PSS}, s.26(3), s.30(1)")

days = 45
fine = 1 * CR + 1 * LAKH * (days - 1)
assert fine == 1.44 * CR
add("pss_pen", "L2",
    f"A system participant is convicted under s.26(5) for failing to comply with an RBI direction under s.17; the failure continued for {days} days in all. The maximum fine the court may impose is:",
    C(fine),
    [(C(1 * CR + 1 * LAKH * days), "counted the first day in the daily further fine"),
     (C(1 * CR + 25000 * (days - 1)), "applied the ₹25,000 daily rate of s.30 instead of ₹1 lakh"),
     (C(1 * CR), "ignored the further fine for a continuing failure")],
    ["s.26(5): non-compliance with RBI directions — imprisonment 1 month to 10 years, or fine up to ₹1 crore, or both.",
     "Further fine up to ₹1 lakh for every day after the first during which the failure continues.",
     f"₹1 crore + ₹1 lakh × {days-1} = {C(fine)}."],
    "Max fine = ₹1 crore + ₹1 lakh × (days − 1)", "The daily further fine runs from the second day.",
    "numerical", f"{PSS}, s.26(5)")

add("pss_prb", "L2",
    "Under s.3(3) of the PSS Act as amended, the Payments Regulatory Board consists of:",
    "Governor, DG (PSS), an RBI officer and three Central Government nominees",
    [("Governor, all Deputy Governors and up to three Central Board directors", "outdated BPSS composition"),
     ("Governor, DG (PSS) and three RBI officers named by the Governor", "omits the Central Government nominees"),
     ("Finance Secretary as chair, the Governor and two RBI officers", "wrong chair — the Governor chairs the PRB")],
    ["s.3(3): (a) Governor — Chairperson, ex officio; (b) Deputy Governor in charge of PSS — ex officio;",
     "(c) one RBI officer nominated by the Central Board — ex officio; (d) three persons nominated by the Central Government.",
     "Six members in all."],
    "PSS Act s.3(3)", "Older texts describe the BPSS (Governor + DGs + Central Board directors).",
    "conceptual", f"{PSS}, s.3(3) (as amended by Finance Act 2019)")

ob = {("A", "B"): 64, ("B", "C"): 52, ("C", "A"): 38, ("B", "A"): 27, ("C", "B"): 45, ("A", "C"): 19}
net = {p: sum(v for (f_, t), v in ob.items() if t == p) - sum(v for (f_, t), v in ob.items() if f_ == p) for p in "ABC"}
assert sum(net.values()) == 0 and net["B"] == 30
payB = sum(v for (f_, t), v in ob.items() if f_ == "B")
bilA = ob[("A", "B")] - ob[("B", "A")]
tbl = "| Payer → Payee | Amount (₹ crore) |\n|---|---:|\n" + "\n".join(f"| {a} → {b} | {v} |" for (a, b), v in ob.items())
add("pss_setl", "L2",
    f"Three participants settle through an authorised deferred net settlement system using multilateral netting approved under s.23(1). Obligations for the cycle:\n\n{tbl}\n\nParticipant B's settlement position is:",
    f"Net receiver of ₹{net['B']} crore",
    [(f"Net payer of ₹{net['B']} crore", "sign reversed"),
     (f"Net receiver of ₹{bilA} crore", "bilateral netting with A only"),
     (f"Net payer of ₹{payB} crore", "gross payables taken; no netting")],
    [f"B receives: from A {ob[('A','B')]} + from C {ob[('C','B')]} = {ob[('A','B')]+ob[('C','B')]}",
     f"B pays: to C {ob[('B','C')]} + to A {ob[('B','A')]} = {payB}",
     f"Multilateral net = {ob[('A','B')]+ob[('C','B')]} − {payB} = +{net['B']} (receiver); all nets sum to zero."],
    "Multilateral net = Σ receivable − Σ payable", "Netting under s.2 is a determination by the system provider; finality attaches on determination (s.23).",
    "numerical", f"{PSS}, s.2 (netting), s.23(1)")

eft = 4.5 * LAKH
add("pss_pen", "L2",
    f"An electronic funds transfer of {L(eft)}, initiated to discharge a debt, fails for insufficiency of funds and all conditions of the provisos to s.25(1) are met. The initiator is punishable with:",
    f"Imprisonment up to 2 years, or fine up to {L(2*eft)}, or both",
    [(f"Imprisonment up to 1 year, or fine up to {L(eft)}, or both", "one-year term (pre-2002 NI Act s.138) and fine capped at the amount"),
     ("Imprisonment up to 10 years, or fine up to ₹1 crore, or both", "s.26(1) unauthorised-operation penalty"),
     (f"Imprisonment up to 2 years, or fine up to {L(10*LAKH)}, or both", "s.30 ₹10 lakh limb used as the fine cap")],
    ["s.25(1): EFT dishonour for insufficient funds — imprisonment up to two years, or fine up to twice the amount of the EFT, or both.",
     f"Twice {L(eft)} = {L(2*eft)}."],
    "EFT dishonour fine ≤ 2 × amount", "s.25 mirrors NI Act s.138 (two years / twice the amount).",
    "numerical", f"{PSS}, s.25(1)")

# ---- L3 (7)
add("pss_auth", "L3",
    "Consider the following in the context of s.4 of the PSS Act:\n\n1. A company accepting payments from its holding company or a fellow subsidiary does not need RBI authorisation for that activity.\n2. A person acting as the duly appointed agent of another person to whom the payment is due does not need RBI authorisation.\n3. A payment system operating at the commencement of the Act could continue indefinitely without applying for authorisation.\n\nWhich of the statements is/are correct?",
    "1 and 2 only",
    [("1 only", "misses the agent proviso"),
     ("2 and 3 only", "misses the group-company proviso and accepts an indefinite grace period"),
     ("1, 2 and 3", "ignores the six-month limit for existing systems")],
    ["Statement 1 — correct: proviso for payments accepted from the holding company or group companies.",
     "Statement 2 — correct: proviso for a duly appointed agent of the payee.",
     "Statement 3 — wrong: existing systems could continue only for six months from commencement unless authorisation was refused earlier."],
    "PSS Act s.4 provisos", "The transition window for existing systems was six months, not open-ended.",
    "statement", f"{PSS}, s.4")

add("pss_auth", "L3",
    "Consider the following regarding revocation of authorisation under s.8 of the PSS Act:\n\n1. Ordinarily, no order of revocation can be made without giving the system provider a reasonable opportunity of being heard.\n2. The hearing requirement does not apply where the RBI considers revocation necessary in the interest of the monetary policy of the country.\n3. An order of revocation is appealable to the Securities Appellate Tribunal within 45 days.\n\nWhich of the statements is/are correct?",
    "1 and 2 only",
    [("1 only", "misses the s.8(2) exception"),
     ("1 and 3 only", "wrong appellate forum and period"),
     ("1, 2 and 3", "accepts SAT as the appellate forum")],
    ["s.8(1) proviso: reasonable opportunity of being heard before revocation.",
     "s.8(2): sub-section (1) does not apply where revocation is necessary in the interest of monetary policy or other reasons specified in the order.",
     "s.9: appeal lies to the Central Government within 30 days — not SAT."],
    "PSS Act s.8, s.9", "SAT hears SEBI/IRDAI/PFRDA appeals; PSS appeals go to the Central Government.",
    "statement", f"{PSS}, s.8, s.9")

days = 20
pen = 10 * LAKH + 25000 * (days - 1)
assert pen == 14.75 * LAKH
add("pss_pen", "L3",
    f"A system provider fails to produce returns called for by the RBI. No amount is quantifiable and no court complaint has been filed. The default continues for {days} days in all. The maximum penalty the RBI may impose under s.30 is:",
    L(pen),
    [(L(10 * LAKH + 25000 * days), "counted the first day in the daily penalty"),
     (L(10 * LAKH + 1 * LAKH * (days - 1)), "applied the ₹1 lakh daily rate of s.26(1)/(5)"),
     (L(5 * LAKH + 25000 * (days - 1)), "used the ₹5 lakh s.26(4) fine as the base")],
    ["s.26(3): failure to furnish returns → penalty under s.30.",
     "s.30(1): up to ₹10 lakh (or twice the amount, if quantifiable) plus up to ₹25,000 for every day after the first.",
     f"₹10 lakh + ₹25,000 × {days-1} = {L(pen)}."],
    "Penalty = ₹10 lakh + ₹25,000 × (days − 1)", "Do not borrow the ₹1 lakh/day court-fine rate of s.26(1).",
    "numerical", f"{PSS}, s.26(3), s.30(1)")

mt = [("P", "s.26(1) — operating without authorisation"), ("Q", "s.26(2) — wilful false statement in application"),
      ("R", "s.26(4) — disclosure of information prohibited under s.22"), ("S", "s.25 — dishonour of electronic funds transfer")]
pn = ["Imprisonment 1 month to 10 years, or fine up to ₹1 crore, or both",
      "Imprisonment up to 3 years and fine of ₹10 lakh to ₹50 lakh",
      "Imprisonment up to 6 months, or fine up to ₹5 lakh or twice the damage, whichever is more, or both",
      "Imprisonment up to 2 years, or fine up to twice the amount, or both"]
tbl = "| Contravention | | Punishment |\n|---|---|---|\n" + "\n".join(
    f"| {mt[i][0]}. {mt[i][1]} | | {i+1}. {pn[i]} |" for i in range(4))
add("pss_pen", "L3",
    f"Match the contravention under the PSS Act with its punishment. (Punishments are listed in serial order, not in matching order.)\n\n{tbl}",
    "P-1, Q-2, R-3, S-4",
    [("P-1, Q-3, R-2, S-4", "swaps false-statement and disclosure punishments"),
     ("P-4, Q-2, R-3, S-1", "swaps unauthorised operation with EFT dishonour"),
     ("P-2, Q-1, R-3, S-4", "treats false statement as the gravest offence")],
    ["s.26(1): 1 month–10 years or fine up to ₹1 crore (+₹1 lakh/day continuing).",
     "s.26(2): up to 3 years and fine ₹10–50 lakh.",
     "s.26(4): up to 6 months or fine up to ₹5 lakh or twice the damage, whichever is more.",
     "s.25: up to 2 years or fine up to twice the EFT amount."],
    "PSS Act s.25, s.26", "Only s.26(2) has a minimum fine (₹10 lakh).",
    "match", f"{PSS}, s.25, s.26")

add("pss_dir", "L3",
    "**Assertion (A):** The RBI may direct a system participant (not merely the system provider) to cease and desist from a course of conduct that leaves systemic risk inadequately controlled.\n\n**Reason (R):** Section 17 of the PSS Act empowers the RBI to issue written directions to a payment system or a system participant requiring it, within a specified time, to cease and desist or to perform remedial acts.",
    "Both A and R are true and R is the correct explanation of A",
    [("Both A and R are true but R is not the correct explanation of A", "R is the very provision that grounds A"),
     ("A is true but R is false", "misreads s.17 as limited to system providers"),
     ("A is false but R is true", "assumes directions can issue only to the system provider")],
    ["s.17 addresses 'a payment system or a system participant'.",
     "Directions may require cease-and-desist or remedial action within the time specified; hence R explains A."],
    "PSS Act s.17", "Participants (banks, members) are directly reachable under s.17.",
    "assertion-reason", f"{PSS}, s.17")

coll, oblig = 120, 85
add("pss_setl", "L3",
    f"A central counterparty (CCP) operating an authorised payment system is ordered to be wound up. Participant Zeta had posted collateral of ₹{coll} crore with the CCP; its payment obligations, determined forthwith under s.23(5), are ₹{oblig} crore and have become final. The liquidator of the CCP must:",
    f"Apply ₹{oblig} crore and return ₹{coll-oblig} crore of excess collateral to Zeta",
    [(f"Retain all ₹{coll} crore of collateral for distribution to CCP creditors", "treats participant collateral as the CCP's general estate"),
     (f"Reopen the determination and return all ₹{coll} crore to Zeta", "s.23(6) bars reopening a final determination"),
     (f"Return ₹{oblig} crore to Zeta and retain ₹{coll-oblig} crore", "applies and returns the wrong amounts")],
    ["s.23(5): on insolvency of a CCP, payment obligations and settlement instructions are determined forthwith and are final and irrevocable.",
     "s.23(6): the liquidator shall not reopen any final determination and shall return excess collateral to participants.",
     f"Excess = ₹{coll} crore − ₹{oblig} crore = ₹{coll-oblig} crore."],
    "Excess collateral = Collateral − Final obligations", "Finality protects both the settlement and the participant's surplus collateral.",
    "numerical", f"{PSS}, s.23(5)-(6)")

info = D("2026-05-06"); nsent = D("2026-05-28"); nrec = D("2026-06-01")
coa = plus(nrec, 16); lastc = addm(coa, 1)
assert plus(info, 30) >= nsent and weekday_ok(lastc)
add("pss_pen", "L3",
    f"Beneficiary Kappa is told by its bank on {fd(info)} that an EFT initiated by Lambda to repay a loan was not executed for insufficient funds. Kappa's written demand is sent on {fd(nsent)} and received by Lambda on {fd(nrec)}; Lambda does not pay. Treat the day of receipt as excluded from the 15-day period, the cause of action as arising on the day after that period ends, and the one-month complaint period as ending on the corresponding date of the next month. The complaint must be filed by:",
    f"{fd(lastc)}, and Kappa itself can file it",
    [(f"{fd(lastc)}, but only an authorised RBI officer can file it", "ignores the s.28(1) proviso for s.25 complaints"),
     (f"{fd(addm(plus(nrec, 15), 1))}, and Kappa itself can file it", "cause of action taken on the 15th day itself"),
     (f"{fd(addm(nrec, 1))}, and Kappa itself can file it", "one month counted from receipt of the notice")],
    [f"Notice sent within 30 days of {fd(info)} — valid.",
     f"15 days from receipt {fd(nrec)} end on {fd(plus(nrec, 15))}; cause of action arises on {fd(coa)}.",
     f"One month from {fd(coa)} → {fd(lastc)} (s.25(5) applies NI Act Chapter XVII, incl. s.142).",
     "s.28(1) proviso: a court may take cognizance of a s.25 offence on a complaint by the person aggrieved."],
    "Cause of action = receipt + 15 days + 1; limitation = 1 month", "RBI-officer-only complaint rule has an express carve-out for EFT dishonour.",
    "numerical", f"{PSS}, s.25, s.28; {NIA}, s.142")

# ---- L4 standalone (1)
add("pss_auth", "L4",
    "NovaPay Ltd, an authorised payment system operator, repeatedly ignores RBI directions issued under s.17. The RBI revokes its authorisation by an order that records that immediate revocation is necessary in the interest of the monetary policy of the country, without first hearing NovaPay. The order also contains provisions to safeguard NovaPay's customers. NovaPay argues (i) the order is void for want of hearing, and (ii) it can approach only the High Court. Which assessment is correct?",
    "Both fail: s.8(2) excuses hearing; appeal lies to Central Govt",
    [("Argument (i) succeeds: a hearing can never be dispensed with", "ignores the monetary-policy exception in s.8(2)"),
     ("Both fail, but the appeal lies to the RBI's Central Board", "wrong appellate forum under s.9"),
     ("Argument (ii) succeeds: the Act gives no statutory appeal", "overlooks the s.9 appeal to the Central Government")],
    ["s.8(1): revocation for non-compliance with directions, ordinarily after hearing.",
     "s.8(2): hearing requirement does not apply where revocation is necessary in the interest of monetary policy (reasons stated in the order).",
     "s.8(3): order must safeguard affected persons — satisfied here.",
     "s.9: appeal to the Central Government within 30 days; its decision is final."],
    "PSS Act s.8, s.9", "Writ jurisdiction is not the statutory remedy the question tests.",
    "case", f"{PSS}, s.8, s.9")

# ---- L4 case set (4)
CASE_P = ("**Case — WalletWave Technologies Pvt Ltd.** WalletWave began operating a prepaid wallet payment system on 1 February 2026 "
          "without any authorisation from the RBI and continued for 61 days in all before stopping. It then applied for authorisation, "
          "wilfully overstating its net worth in the application; an authorised RBI officer has filed a complaint in court for this false "
          "statement. The RBI has specified wallets of this class as a 'designated payment system' under s.23A and required 100% of "
          "outstanding customer balances to be held in a separate account with a scheduled commercial bank. That account holds ₹48 crore, "
          "exactly equal to customers' outstanding balances. In a separate matter, the RBI served on WalletWave, on 5 August 2026, a notice "
          "demanding payment of a ₹12 lakh penalty imposed under s.30.")
days = 61
fineC = 1 * CR + 1 * LAKH * (days - 1)
add("pss_pen", "L4", CASE_P + "\n\nFor the unauthorised operation, the maximum fine a court may impose on WalletWave is:",
    C(fineC),
    [(C(1 * CR + 1 * LAKH * days), "counted the first day in the daily further fine"),
     (C(10 * LAKH + 25000 * (days - 1)), "applied RBI's s.30 penalty limits to a court fine"),
     (C(50 * LAKH + 1 * LAKH * (days - 1)), "used the s.26(2) ₹50 lakh upper limit as base")],
    ["Operating without authorisation contravenes s.4 → s.26(1).",
     "Fine up to ₹1 crore plus up to ₹1 lakh per day after the first while the contravention continues.",
     f"₹1 crore + ₹1 lakh × {days-1} = {C(fineC)}."],
    "₹1 crore + ₹1 lakh × (days − 1)", "s.30 limits apply only to RBI-imposed penalties for s.26(2)/(3)/(6).",
    "case", f"{PSS}, s.4, s.26(1)", group="ACTP-CASE-WALLETWAVE")

add("pss_pen", "L4", CASE_P + "\n\nFor the false statement in the application, can the RBI now also impose a monetary penalty on WalletWave under s.30?",
    "No — the pending court complaint bars s.30 proceedings",
    [("Yes — up to ₹10 lakh or twice the amount, whichever is more", "ignores the s.30(6) bar once a complaint is filed"),
     ("Yes — but only after the criminal trial ends in acquittal", "invents a sequential-proceedings rule"),
     ("No — false statements carry only imprisonment, never a fine", "s.26(2) carries a ₹10–50 lakh fine as well")],
    ["s.26(2): wilful false statement in an application — up to 3 years and fine ₹10–50 lakh.",
     "s.30(1) allows RBI penalties for s.26(2) defaults, but s.30(6): where a complaint has been filed in court for a s.26(2) or s.26(4) default, no s.30 proceeding shall be taken."],
    "PSS Act s.26(2), s.30(6)", "The RBI must choose: prosecution or administrative penalty, not both.",
    "case", f"{PSS}, s.26(2), s.30(6)", group="ACTP-CASE-WALLETWAVE")

esc, sec = 48, 20
add("pss_setl", "L4", CASE_P + f"\n\nWalletWave is admitted into insolvency. A secured lender to WalletWave claims ₹{sec} crore and asks to be paid from the ₹{esc} crore separate account. The amount of that account available to the secured lender before customers are paid in full is:",
    "₹0 crore",
    [(f"₹{sec} crore", "applies the IBC waterfall — s.23A(3) overrides the IBC"),
     (f"₹{esc*sec/(esc+sec):.2f} crore", "pro-rata sharing between customers and the lender"),
     (f"₹{esc-sec} crore", "lender paid first; customers get the residue")],
    ["s.23A(2): balances may be used only to discharge customer liabilities/repay customers or other RBI-specified purposes.",
     "s.23A(3): notwithstanding the BR Act, Companies Acts, IBC or any other law, customers have a first and paramount charge; the liquidator cannot use the balance until they are paid in full.",
     f"Account = ₹{esc} crore = customer balances, so nothing is available to the lender."],
    "Customer entitlement ranks first on s.23A balances", "s.23A expressly overrides the Insolvency and Bankruptcy Code.",
    "case", f"{PSS}, s.23A", group="ACTP-CASE-WALLETWAVE")

srv = D("2026-08-05"); due = plus(srv, 30)
add("pss_pen", "L4", CASE_P + "\n\nExcluding the day of service, the last date for WalletWave to pay the ₹12 lakh penalty before recovery through the principal civil court can be sought is:",
    fd(due),
    [(fd(plus(srv, 14)), "applied the 14-day period of CICRA s.25 / Factoring Act s.22"),
     (fd(plus(srv, 29)), "counted the day of service"),
     (fd(plus(srv, 60)), "applied the 60-day period of NI Act s.143A")],
    ["s.30(3): penalty payable within 30 days from service of the RBI's demand notice.",
     f"{fd(srv)} + 30 days = {fd(due)}.",
     "On failure, recovery on direction of the principal civil court on an RBI officer's application; the RBI may also debit the defaulter's current account (s.30(4))."],
    "Payment window = 30 days from service", "CICRA and the Factoring Act use 14 days; the PSS Act uses 30.",
    "case", f"{PSS}, s.30(3)", group="ACTP-CASE-WALLETWAVE")

# =====================================================================================
#  CREDIT INFORMATION COMPANIES (REGULATION) ACT, 2005  (22)
# =====================================================================================
# ---- L1 (4)
add("cic_reg", "L1",
    "Under s.3 of the Credit Information Companies (Regulation) Act, 2005, no company shall commence or carry on the business of credit information without a certificate of registration from:",
    "The Reserve Bank of India",
    [("SEBI, under its credit rating agency regulations", "confuses credit bureaus with credit rating agencies"),
     ("The Ministry of Corporate Affairs", "company incorporation is not bureau registration"),
     ("The Central Government in consultation with RBI", "the Central Government only hears s.7 appeals")],
    ["s.3: certificate of registration from the RBI is mandatory for credit information business.",
     "Registration is granted under s.5(2) after the RBI is satisfied about capital, management and public interest."],
    "CICRA s.3, s.5", "Credit rating agencies (SEBI) and credit information companies (RBI) are different.",
    "conceptual", f"{CIC}, s.3")

add("cic_mem", "L1",
    "Under s.15(2) of CICRA, a credit institution that comes into existence after the commencement of the Act must, unless the RBI extends the time, become a member of:",
    "At least one credit information company within three months",
    [("At least one credit information company within six months", "confuses with the s.4(2) six-month window for existing CICs"),
     ("At least two credit information companies within 30 days", "invents a two-bureau statutory floor"),
     ("The CIC nominated by the RBI within one year", "the institution chooses the CIC; no nomination")],
    ["s.15(1)–(2): every credit institution shall become a member of at least one CIC within three months (of commencement / of coming into existence), extendable by the RBI.",
     "Any requirement to join all CICs arises from RBI directions, not from the section itself."],
    "CICRA s.15(2)", "Six months is the application window for existing CICs under s.4(2).",
    "conceptual", f"{CIC}, s.15")

add("cic_priv", "L1",
    "Under s.20 of CICRA, the obligation to adopt the specified privacy principles for collection, processing, preservation, sharing and use of credit information applies to:",
    "Every CIC, credit institution and specified user",
    [("Credit information companies alone", "omits credit institutions and specified users"),
     ("Banking companies only, not NBFCs or other lenders", "reads 'credit institution' too narrowly"),
     ("The RBI, which then enforces them on CICs", "RBI prescribes, it does not 'adopt' the principles")],
    ["s.20 opens: 'Every credit information company, credit institution and specified user shall adopt the following privacy principles…'.",
     "Breach is punishable under s.23(2) with fine up to ₹1 crore."],
    "CICRA s.20", "The duty follows the data to every holder, not just the bureau.",
    "conceptual", f"{CIC}, s.20")

add("cic_mem", "L1",
    "Which of the following is correctly within the definition of 'specified user' under s.2 of CICRA?",
    "A credit institution, or a person specified by RBI",
    [("Any borrower seeking his own credit report", "borrowers access under s.21; they are not specified users"),
     ("Any registered credit rating agency, by default", "only if RBI specifies it by regulations"),
     ("Any employer checking a job applicant's credit", "no statutory entitlement; would be unauthorised access")],
    ["s.2: 'specified user' = any credit institution, a CIC that is a member under s.15(3), and other persons specified by RBI regulations.",
     "Access by anyone else is unauthorised under s.22 unless authorised by law or a court."],
    "CICRA s.2 (specified user)", "Being interested in someone's credit profile does not make a person a specified user.",
    "conceptual", f"{CIC}, s.2")

# ---- L2 (7)
issued = 24 * CR
add("cic_reg", "L2",
    f"A credit information company has authorised capital of ₹30 crore and issued capital of {C(issued)}. The minimum paid-up capital it must maintain at all times under s.8(3) of CICRA is:",
    C(0.75 * issued),
    [(C(0.75 * 20 * CR), "75% of the statutory minimum issued capital, not actual issued"),
     (C(0.75 * 30 * CR), "75% of authorised capital"),
     (C(issued), "treats issued capital as fully paid-up requirement")],
    ["s.8(1): authorised capital ≥ ₹30 crore (RBI may raise to ₹50 crore); s.8(2): issued capital ≥ ₹20 crore.",
     f"s.8(3): paid-up ≥ 75% of issued capital = 75% × {C(issued)} = {C(0.75*issued)}."],
    "Paid-up ≥ 75% × Issued", "The base is the company's actual issued capital.",
    "numerical", f"{CIC}, s.8")

rej = D("2026-03-20")
add("cic_reg", "L2",
    f"The RBI rejects a company's application for a certificate of registration as a credit information company by an order communicated on {fd(rej)}. Excluding the day of communication, the company may appeal:",
    f"To the Central Government by {fd(plus(rej, 30))}",
    [(f"To the RBI's Deputy Governor by {fd(plus(rej, 30))}", "wrong forum — s.7 appeal lies to the Central Government"),
     (f"To the Central Government by {fd(plus(rej, 14))}", "applied the 14-day penalty-payment period"),
     (f"To the Securities Appellate Tribunal by {fd(plus(rej, 45))}", "SAT/45 days belongs to securities law")],
    ["s.7: a company aggrieved by rejection (s.5) or cancellation (s.6) may appeal within 30 days to the Central Government (or authority it specifies).",
     f"{fd(rej)} + 30 days = {fd(plus(rej, 30))}."],
    "CICRA s.7", "Contrast s.15(5): membership-rejection appeals go to the RBI.",
    "numerical", f"{CIC}, s.7")

mr = D("2026-06-11")
add("cic_mem", "L2",
    f"A credit information company rejects an NBFC's application for membership, after hearing it and recording reasons; the order is communicated on {fd(mr)}. Excluding that day, the NBFC's appeal lies:",
    f"To the RBI, within 30 days, i.e. by {fd(plus(mr, 30))}",
    [(f"To the Central Government, by {fd(plus(mr, 30))}", "confuses with s.7 registration appeals"),
     (f"To the RBI, by {fd(plus(mr, 14))}", "applied the 14-day penalty-payment period"),
     (f"To the CIC's own board, by {fd(plus(mr, 30))}", "no internal appeal in s.15")],
    ["s.15(4): rejection only after hearing, with reasons; copy to RBI.",
     "s.15(5): appeal to the RBI within 30 days of communication (extendable for sufficient cause); s.15(7): RBI's decision is final.",
     f"{fd(mr)} + 30 days = {fd(plus(mr, 30))}."],
    "CICRA s.15(5)", "Membership appeals → RBI; registration appeals → Central Government.",
    "numerical", f"{CIC}, s.15(5)")

rq = D("2026-02-03"); dl = plus(rq, 30)
add("cic_corr", "L2",
    f"A borrower asks a CIC on {fd(rq)} to correct an outdated entry; the lender has certified the correction and no dispute is pending. Excluding the day of request, the CIC must take steps to update the information by:",
    fd(dl),
    [(fd(addm(rq, 1)), "read 'thirty days' as one calendar month"),
     (fd(plus(rq, 14)), "applied a 14-day period"),
     (fd(plus(rq, 45)), "applied a 45-day period")],
    ["s.21(3): the CIC / specified user / credit institution shall take steps to update within thirty days after being requested.",
     f"{fd(rq)} + 30 days = {fd(dl)} (February 2026 has 28 days)."],
    "Update deadline = request + 30 days", "In February, 30 days ≠ one calendar month.",
    "numerical", f"{CIC}, s.21(3)")

extra = 12
f22 = 1 * LAKH + 10000 * extra
add("cic_priv", "L2",
    f"A person obtains unauthorised access to credit information held by a CIC and continues that access on {extra} further days. The maximum fine under s.22(2) of CICRA is:",
    L(f22),
    [(L(1 * LAKH + 5000 * extra), "applied the ₹5,000 daily rate of s.23(4)"),
     (C(1 * CR), "applied the ₹1 crore cap for breach of privacy principles"),
     (L(1 * LAKH), "ignored the further fine for continuing access")],
    ["s.22(2): fine up to ₹1 lakh per offence; if unauthorised access continues, further fine up to ₹10,000 for every day the default continues.",
     f"₹1 lakh + ₹10,000 × {extra} = {L(f22)}."],
    "₹1 lakh + ₹10,000 × continuing days", "The daily rate is ₹10,000 here, ₹5,000 under s.23(4).",
    "numerical", f"{CIC}, s.22(2)")

extra = 40
f234 = 1 * LAKH + 5000 * extra
add("cic_pen", "L2",
    f"A credit institution fails to comply with a requirement of CICRA for which no specific punishment is provided; the default continues for {extra} days after the initial default. The maximum fine under s.23(4) is:",
    L(f234),
    [(L(1 * LAKH + 10000 * extra), "applied the ₹10,000 daily rate of s.22(2)"),
     (L(1 * LAKH + 25000 * extra), "applied the ₹25,000 daily rate of PSS Act s.30"),
     (C(1 * CR), "applied the s.23(2)/(3) ₹1 crore cap")],
    ["s.23(4): residual contraventions — fine up to ₹1 lakh; continuing default, further fine up to ₹5,000 per day.",
     f"₹1 lakh + ₹5,000 × {extra} = {L(f234)}."],
    "₹1 lakh + ₹5,000 × days", "Residual clause applies only where no specific punishment exists.",
    "numerical", f"{CIC}, s.23(4)")

sv = D("2026-09-07")
add("cic_pen", "L2",
    f"The RBI imposes a penalty on a CIC under s.25 of CICRA and serves the demand notice on {fd(sv)}. Excluding the day of service, the penalty must be paid by:",
    fd(plus(sv, 14)),
    [(fd(plus(sv, 30)), "applied the 30-day period of PSS Act s.30(3)"),
     (fd(plus(sv, 7)), "assumed a 7-day period"),
     (fd(plus(sv, 60)), "applied the 60-day period of NI Act s.143A")],
    ["s.25: penalty imposed by the RBI is payable within fourteen days of service of the demand notice.",
     f"{fd(sv)} + 14 days = {fd(plus(sv, 14))}; on default, recovery through the principal civil court."],
    "CICRA s.25 — 14 days", "PSS Act allows 30 days; CICRA and the Factoring Act allow 14.",
    "numerical", f"{CIC}, s.25")

# ---- L3 (7)
apps = [("Alpha", 30, 20, 14.5), ("Beta", 30, 18, 18), ("Gamma", 40, 25, 19), ("Delta", 25, 25, 25)]
def ok8(a, i, p): return a >= 30 and i >= 20 and p >= 0.75 * i
passing = [n for n, a, i, p in apps if ok8(a, i, p)]
assert passing == ["Gamma"]
tbl = "| Applicant | Authorised (₹ cr) | Issued (₹ cr) | Paid-up (₹ cr) |\n|---|---:|---:|---:|\n" + \
      "\n".join(f"| {n} | {a} | {i} | {p} |" for n, a, i, p in apps)
add("cic_reg", "L3",
    f"Four companies seek registration as credit information companies. Assume the RBI has not raised the capital floors in s.8 of CICRA.\n\n{tbl}\n\nWhich applicant(s) satisfy the capital requirements of s.8?",
    "Gamma only",
    [("Gamma and Delta", "Delta fully paid-up but authorised capital below ₹30 crore"),
     ("Alpha and Gamma", "Alpha's paid-up 72.5% < 75% of issued"),
     ("Beta and Gamma", "Beta's issued capital below ₹20 crore despite being fully paid")],
    ["Tests: authorised ≥ ₹30 cr; issued ≥ ₹20 cr; paid-up ≥ 75% of issued.",
     "Alpha: 14.5/20 = 72.5% — fails paid-up test.", "Beta: issued 18 < 20 — fails.",
     "Gamma: 40 / 25 / 19 (76%) — passes.", "Delta: authorised 25 < 30 — fails."],
    "s.8(1)–(3) all three tests", "All three limbs must hold simultaneously.",
    "numerical", f"{CIC}, s.8")

add("cic_mem", "L3",
    "Consider the following under CICRA:\n\n1. Housing finance institutions and companies engaged in credit card business fall within the definition of 'credit institution'.\n2. A credit information company may, at its option, become a member of another credit information company.\n3. A credit information company may reject a membership application without hearing the applicant, provided it records reasons.\n\nWhich of the statements is/are correct?",
    "1 and 2 only",
    [("1 only", "misses the s.15(3) option"),
     ("2 and 3 only", "wrongly excludes HFCs/credit card companies and dispenses with hearing"),
     ("1, 2 and 3", "s.15(4) requires both hearing and recorded reasons")],
    ["s.2: 'credit institution' includes banks, co-operative banks, NBFCs, public financial institutions, housing finance institutions, credit card companies and RBI-specified institutions.",
     "s.15(3): a CIC may at its option become a member of another CIC.",
     "s.15(4): rejection needs reasonable opportunity of hearing AND recorded reasons, with a copy to RBI."],
    "CICRA s.2, s.15", "Hearing and reasons are cumulative requirements.",
    "statement", f"{CIC}, s.2, s.15")

add("cic_priv", "L3",
    "Which of the following matters are covered by the privacy principles listed in s.20 of CICRA?\n\n1. The purpose for which credit information may be used, and restrictions on its use and disclosure.\n2. Preservation of credit information — period of maintenance, and modes of removal or destruction.\n3. Networking of CICs, credit institutions and specified users through electronic mode.\n\nSelect the correct answer.",
    "1, 2 and 3",
    [("1 and 2 only", "omits the networking principle in s.20(e)"),
     ("1 and 3 only", "omits the preservation principle in s.20(d)"),
     ("2 and 3 only", "omits purpose-and-use restrictions in s.20(b)")],
    ["s.20(b): purpose, restriction on use and disclosure.", "s.20(d): preservation — period, removal/destruction, records.",
     "s.20(e): networking through electronic mode.", "All three are listed principles."],
    "CICRA s.20(a)–(f)", "Networking is a privacy principle too, not merely a technical matter.",
    "statement", f"{CIC}, s.20")

add("cic_corr", "L3",
    "**Assertion (A):** A credit information company may decline to carry out a borrower's requested correction even within 30 days, if the lender has not certified it or if a dispute on it is pending before a court.\n\n**Reason (R):** Under the provisos to s.21(3) of CICRA, a CIC corrects credit information only after the concerned credit institution certifies it, and no correction is made while a related dispute is pending before an arbitrator, tribunal or court.",
    "Both A and R are true and R is the correct explanation of A",
    [("Both A and R are true but R is not the correct explanation of A", "R is exactly the basis of A"),
     ("A is false but R is true", "treats the 30-day limit as overriding the provisos"),
     ("A is true but R is false", "overlooks the provisos to s.21(3)")],
    ["s.21(3): update within 30 days of request.",
     "First proviso: CIC/specified user corrects only after certification by the concerned credit institution.",
     "Second proviso: no correction while a dispute is pending; the lender's book entries are used meanwhile."],
    "CICRA s.21(3) provisos", "The 30-day clock does not override the certification and pending-dispute provisos.",
    "assertion-reason", f"{CIC}, s.21(3)")

mt = [("P", "s.22(2) — unauthorised access"), ("Q", "s.23(2) — wilful breach of privacy principles"),
      ("R", "s.23(1) — wilful false statement in a return"), ("S", "s.23(4) — residual contravention")]
pn = ["Fine up to ₹1 lakh + up to ₹10,000 per continuing day",
      "Fine up to ₹1 crore",
      "Imprisonment up to 1 year and fine",
      "Fine up to ₹1 lakh + up to ₹5,000 per continuing day"]
tbl = "| Contravention | | Punishment |\n|---|---|---|\n" + "\n".join(
    f"| {mt[i][0]}. {mt[i][1]} | | {i+1}. {pn[i]} |" for i in range(4))
add("cic_pen", "L3",
    f"Match the contravention under CICRA with its punishment.\n\n{tbl}",
    "P-1, Q-2, R-3, S-4",
    [("P-4, Q-2, R-3, S-1", "swaps the two daily rates"),
     ("P-1, Q-3, R-2, S-4", "swaps privacy breach and false return"),
     ("P-2, Q-1, R-3, S-4", "gives unauthorised access the ₹1 crore cap")],
    ["s.22(2): ₹1 lakh + ₹10,000/day.", "s.23(2): up to ₹1 crore.", "s.23(1): up to 1 year imprisonment and fine.",
     "s.23(4): ₹1 lakh + ₹5,000/day."],
    "CICRA s.22, s.23", "Only s.23(1) carries imprisonment.",
    "match", f"{CIC}, s.22, s.23")

filed = D("2026-01-02"); resolved = D("2026-02-20")
tot = (resolved - filed).days; ci_days = 35
delay_total = max(0, tot - 30); ci_delay = max(0, ci_days - 21); cic_delay = max(0, (tot - ci_days) - 9)
assert delay_total == ci_delay + cic_delay == 19
add("cic_corr", "L3",
    f"Under the RBI's compensation framework for credit information complaints (read with s.21 of CICRA), assume: a complaint must be resolved within 30 calendar days of being lodged with the CIC; the credit institution (CI) gets 21 days of this and the CIC 9 days; compensation is ₹100 per calendar day of delay, borne by whichever entity caused it. A complaint lodged with a CIC on {fd(filed)} is resolved on {fd(resolved)}. The CI took {ci_days} days to respond; the CIC used the rest. Compensation payable by the CI is:",
    R(100 * ci_delay),
    [(R(100 * delay_total), "whole delay charged to the CI"),
     (R(100 * cic_delay), "CIC's share reported instead"),
     (R(100 * ci_days), "all CI days charged, not only delay beyond 21")],
    [f"Total time = {tot} days; overall delay = {tot} − 30 = {delay_total} days.",
     f"CI delay = {ci_days} − 21 = {ci_delay} days → ₹{100*ci_delay}.",
     f"CIC time = {tot} − {ci_days} = {tot-ci_days} days; delay = {tot-ci_days} − 9 = {cic_delay} days → ₹{100*cic_delay}.",
     f"Check: {ci_delay} + {cic_delay} = {delay_total}."],
    "Compensation = ₹100 × days beyond each entity's allotted time", "Split the delay by responsibility.",
    "numerical", f"{CIC}, s.21; RBI circular on compensation for delayed updation/rectification of credit information (2023)")

add("cic_pen", "L3",
    "Consider the following regarding penalties under s.25 of CICRA:\n\n1. Once the RBI imposes a penalty for a contravention, no complaint shall be filed in any court for the same contravention.\n2. Where a complaint has already been filed in court for a contravention, the RBI shall not initiate penalty proceedings for it.\n3. For wilfully furnishing false credit information, the RBI may impose a penalty not exceeding ₹1 crore.\n\nWhich of the statements is/are correct?",
    "1, 2 and 3",
    [("1 and 2 only", "misses that s.25 mirrors the s.23(3) ₹1 crore cap"),
     ("1 and 3 only", "misses the reverse bar where a complaint is pending"),
     ("2 and 3 only", "misses the bar on prosecution after an RBI penalty")],
    ["s.25(1): penalties — ₹1 lakh (s.22(2)), ₹1 crore (s.23(2)/(3)), ₹1 lakh + ₹5,000/day (s.23(4)).",
     "s.25(3): penalty imposed → no court complaint for same contravention.",
     "s.25(6): complaint filed → no RBI penalty proceedings."],
    "CICRA s.25", "The two routes are mutually exclusive in both directions.",
    "statement", f"{CIC}, s.25")

# ---- L4 case set (4)
CASE_C = ("**Case — Trident Home Finance Ltd.** Trident, a housing finance company, commenced lending on 1 April 2026. "
          "Borrower Meera found in January 2027 that Trident had reported her fully repaid loan as overdue. She requested Trident and the CIC "
          "on 20 January 2027 to correct it; no dispute was pending and Trident certified the correction, which was finally updated on "
          "20 February 2027. Separately, a Trident employee, without any authority, pulled Meera's credit report from the CIC to vet her for a "
          "relative's marriage proposal and kept pulling fresh reports on 6 further days. An internal audit also found that Trident had "
          "wilfully furnished false repayment data about another borrower to the CIC.")
st = D("2026-04-01")
add("cic_mem", "L4", CASE_C + "\n\nAbsent any RBI extension, the last date by which Trident had to become a member of a credit information company was:",
    f"{fd(addm(st, 3))} — at least one CIC",
    [(f"{fd(addm(st, 6))} — at least one CIC", "used the six-month window of s.4(2)"),
     (f"{fd(plus(st, 30))} — every CIC", "invents a 30-day, all-CIC statutory rule"),
     ("No date — HFCs are outside the Act as NHB-regulated", "HFCs are expressly credit institutions under s.2")],
    ["s.2: housing finance institutions are credit institutions.",
     "s.15(2): a credit institution coming into existence after commencement must join at least one CIC within three months.",
     f"{fd(st)} + 3 months = {fd(addm(st, 3))}."],
    "CICRA s.2, s.15(2)", "Regulatory home (NHB/RBI) does not take an HFC outside CICRA.",
    "case", f"{CIC}, s.2, s.15(2)", group="ACTP-CASE-TRIDENT")

rq = D("2027-01-20"); upd = D("2027-02-20"); dl = plus(rq, 30)
late = (upd - dl).days
assert late == 1
add("cic_corr", "L4", CASE_C + "\n\nWas Meera's correction updated within the time allowed by s.21(3)?",
    f"No — due by {fd(dl)}; updated {late} day late",
    [("Yes — one calendar month is allowed, so on time", "read 30 days as one calendar month"),
     ("Yes — the clock runs only from Trident's certification date", "the Act runs from the request date"),
     (f"No — due by {fd(plus(rq, 14))}; updated {(upd-plus(rq,14)).days} days late", "applied a 14-day period")],
    ["s.21(3): update within thirty days after being requested.",
     f"{fd(rq)} + 30 days = {fd(dl)}; update on {fd(upd)} → {late} day late."],
    "Deadline = request + 30 days", "20 January to 20 February is 31 days, so one calendar month overshoots the 30-day limit.",
    "case", f"{CIC}, s.21(3)", group="ACTP-CASE-TRIDENT")

extra = 6
add("cic_priv", "L4", CASE_C + "\n\nThe maximum fine the employee faces for the unauthorised access is:",
    L(1 * LAKH + 10000 * extra),
    [(L(1 * LAKH + 5000 * extra), "used the ₹5,000 daily rate of s.23(4)"),
     (C(1 * CR), "treated it as the s.23(2) privacy-principle breach by an institution"),
     (L(1 * LAKH + 10000 * (extra + 1)), "counted the first access day as a continuing day")],
    ["Access for a marriage enquiry is not authorised by the Act, any law or a court → s.22(1) breach.",
     f"s.22(2): ₹1 lakh + ₹10,000 × {extra} continuing days = {L(1*LAKH+10000*extra)}."],
    "₹1 lakh + ₹10,000 × continuing days", "The ₹1 crore limit binds CICs/institutions/specified users under s.23(2), not this offence.",
    "case", f"{CIC}, s.22", group="ACTP-CASE-TRIDENT")

add("cic_pen", "L4", CASE_C + "\n\nFor wilfully furnishing false repayment data to the CIC, which statement is correct?",
    "Fine up to ₹1 crore; or RBI penalty up to ₹1 crore payable in 14 days",
    [("Imprisonment up to one year and fine; RBI cannot impose a penalty", "that is s.23(1) — false statement in a return"),
     ("Fine up to ₹1 lakh plus ₹5,000/day as a residual contravention", "residual s.23(4) applies only if no specific provision"),
     ("Fine up to ₹1 crore; or RBI penalty up to ₹1 crore payable in 30 days", "borrows the PSS Act's 30-day payment period")],
    ["s.23(3): wilfully providing false credit information to a CIC — fine up to ₹1 crore.",
     "s.25(1): RBI may instead impose a penalty up to ₹1 crore; payable within 14 days of the demand notice.",
     "Court and RBI routes are mutually exclusive (s.25(3), (6))."],
    "CICRA s.23(3), s.25", "False data furnished to a bureau (s.23(3)) ≠ false statement in a return (s.23(1)).",
    "case", f"{CIC}, s.23(3), s.25", group="ACTP-CASE-TRIDENT")

# =====================================================================================
#  FACTORING REGULATION ACT, 2011  (20)
# =====================================================================================
# ---- L1 (4)
add("fra_def", "L1",
    "Which of the following is excluded from 'factoring business' as defined in s.2 of the Factoring Regulation Act, 2011?",
    "A bank's ordinary-course loan secured by book debts",
    [("An NBFC acquiring receivables by assignment for collection", "core factoring business"),
     ("A bank buying an assignor's receivables for financing", "banks can be factors; this is factoring"),
     ("A factor buying toll receivables of a highway project", "toll dues are receivables after 2021")],
    ["'Factoring business' = acquisition by assignment of receivables for consideration, for collection or financing.",
     "Excluded: (i) credit facilities by a bank in the ordinary course against security of receivables; (ii) commission-agency for sale of agricultural produce or goods."],
    "FRA s.2 (factoring business)", "Security over receivables is lending; assignment is factoring.",
    "conceptual", f"{FRA}, s.2")

add("fra_reg", "L1",
    "Which of the following must obtain a certificate of registration from the RBI under s.3 of the Factoring Regulation Act before carrying on factoring business?",
    "A non-banking financial company",
    [("A scheduled commercial bank", "banks are exempt under s.5"),
     ("A corporation established under a State Act", "statutory corporations are exempt under s.5"),
     ("A Government company engaged in trade finance", "Government companies are exempt under s.5")],
    ["s.3(1): no factor shall carry on factoring business without an RBI certificate of registration.",
     "s.5: s.3 does not apply to banks, statutory corporations (Central/State Act) or Government companies."],
    "FRA s.3, s.5", "Exempt from s.3 registration ≠ outside RBI oversight.",
    "conceptual", f"{FRA}, s.3, s.5")

add("fra_asg", "L1",
    "Under s.8 of the Factoring Regulation Act, an assignee (factor) may demand payment of an assigned receivable from the debtor only after:",
    "Notice of assignment is given to the debtor as required",
    [("The assignment is registered with the Central Registry", "CERSAI filing is not the s.8 trigger"),
     ("The RBI approves the specific assignment transaction", "no transaction-level RBI approval"),
     ("The debtor gives written consent to the assignment", "the debtor's consent is not required")],
    ["s.8: no demand on the debtor unless notice of assignment is given by the assignor, or by the assignee with express authority from the assignor.",
     "s.11: the debtor has a right to such notice before any demand."],
    "FRA s.8, s.11", "Notice, not consent or registration, activates the factor's right to demand.",
    "conceptual", f"{FRA}, s.8")

add("fra_cersai", "L1",
    "Under s.19(1) of the Factoring Regulation Act, a factor must register the particulars of every assignment of receivables in its favour with:",
    "The Central Registry under s.20 of the SARFAESI Act (CERSAI)",
    [("The Registrar of Companies as a charge on the assignor", "confuses with charge registration under the Companies Act"),
     ("An information utility registered under the IBC", "IU records financial information for insolvency, not assignments"),
     ("The RBI's Department of Regulation", "RBI registers factors, not individual assignments")],
    ["s.19(1): particulars of every assignment are registered with the Central Registry set up under s.20 of SARFAESI Act, 2002.",
     "s.19(3): satisfaction is filed on realisation/settlement; s.20: the register is open to public inspection."],
    "FRA s.19(1)", "The same Central Registry (CERSAI) that records SARFAESI security interests.",
    "conceptual", f"{FRA}, s.19")

# ---- L2 (6)
add("fra_def", "L2",
    "After the Factoring Regulation (Amendment) Act, 2021, which of the following transfers falls within 'assignment' under s.2(a)?",
    "Transfer to a factor of part of a foreign debtor's dues",
    [("Transfer by an assignor of its receivables to its own subsidiary", "assignment must be to a factor"),
     ("Pledge of receivables to a bank as security for a cash credit", "security interest in ordinary banking, not assignment"),
     ("Oral transfer of receivables without any written agreement", "s.7 requires an agreement in writing")],
    ["s.2(a) (as amended): transfer by agreement to a factor of an undivided interest, in whole or in part, in receivables due from a debtor — including where the assignor or debtor is outside India.",
     "s.7(1): assignment is by agreement in writing (subject to FEMA for cross-border cases)."],
    "FRA s.2(a) as amended 2021", "Cross-border receivables and part interests were expressly brought in by 2021.",
    "conceptual", f"{FRA}, s.2(a) (as amended 2021), s.7")

extra = 18
p22 = 5 * LAKH + 10000 * extra
add("fra_pen", "L2",
    f"A registered factor fails to comply with a direction issued by the RBI under s.6(2); the default continues for {extra} days after the initial failure. The maximum penalty the RBI may impose under s.22 is:",
    L(p22),
    [(L(5 * LAKH + 5000 * extra), "applied the CICRA s.23(4) ₹5,000 daily rate"),
     (L(10 * LAKH + 25000 * extra), "applied PSS Act s.30 limits"),
     (L(5 * LAKH), "ignored the continuing-default penalty")],
    ["s.22: up to ₹5 lakh; for a continuing default, additional up to ₹10,000 for every day of default.",
     f"₹5 lakh + ₹10,000 × {extra} = {L(p22)}; payable within 14 days of the RBI's notice."],
    "₹5 lakh + ₹10,000 × days", "Separately, s.6(3) lets the RBI prohibit the factor from factoring.",
    "numerical", f"{FRA}, s.22")

add("fra_cersai", "L2",
    "Under s.20 of the Factoring Regulation Act, the particulars of assignment transactions entered in the Central Register are open to inspection by:",
    "Any person, on payment of the prescribed fee",
    [("Only the factor and assignor, free of charge", "inspection is public, not party-restricted"),
     ("Only regulated entities of the RBI", "no such restriction in s.20"),
     ("Any person, but only with the assignor's consent", "no consent requirement")],
    ["s.20(1): open during business hours for inspection by any person on payment of the prescribed fee.",
     "s.20(2): the electronic register is also open for inspection via electronic media on payment of fee."],
    "FRA s.20", "Public inspection is what gives registration its notice value to later financiers.",
    "conceptual", f"{FRA}, s.20")

inv, post = 18 * LAKH, 7 * LAKH
add("fra_asg", "L2",
    f"A debtor owes {L(inv)} on an invoice assigned to a factor. After receiving a valid notice of assignment, the debtor pays {L(post)} to the assignor and {L(inv-post)} to the factor. The debtor's remaining liability to the factor is:",
    L(post),
    [("Nil — the full invoice amount has been paid", "treats post-notice payment to the assignor as a valid discharge"),
     (L(inv), "ignores the amount actually paid to the factor"),
     (L(inv - post), "reported the amount paid to the factor as still due")],
    ["s.9: after notice, the debtor shall pay the assignee; payment to it discharges the debtor.",
     "s.12(b): no valid discharge unless payment is made to the assignee.",
     f"Discharged: {L(inv-post)}; outstanding: {L(inv)} − {L(inv-post)} = {L(post)}."],
    "Post-notice discharge only by payment to the factor", "Payment to the assignor after notice does not discharge the debtor.",
    "numerical", f"{FRA}, s.9, s.12")

add("fra_asg", "L2",
    "Before any notice of assignment is given, a debtor pays ₹6 lakh on an assigned receivable to the assignor. Under the Factoring Regulation Act, the ₹6 lakh:",
    "Is held by the assignor in trust for the factor",
    [("Must be paid a second time by the debtor to the factor", "no notice → payment to assignor is effective for the debtor"),
     ("Belongs to the assignor; the factor bears the loss", "s.10/s.13 impose a trust in favour of the assignee"),
     ("Must be deposited with the RBI pending settlement", "invents an RBI deposit mechanism")],
    ["s.10: where no notice is given, payment by the debtor to the assignor is held in trust for the assignee and must be paid over forthwith.",
     "s.13: payment to the assignor on an assigned receivable is deemed for the assignee's benefit; the assignor is a trustee."],
    "FRA s.10, s.13", "The factor's claim shifts to the assignor as trustee, not back to the debtor.",
    "conceptual", f"{FRA}, s.10, s.13")

add("fra_cersai", "L2",
    "How did the Factoring Regulation (Amendment) Act, 2021 change the time limit in s.19(1) for a factor to register assignment particulars with the Central Registry?",
    "Replaced the fixed 30-day limit with a time to be prescribed",
    [("Retained the 30-day limit from the date of assignment", "pre-2021 text"),
     ("Reduced the limit to 15 days from the date of invoice", "invented period and trigger"),
     ("Removed the filing duty for all factors except NBFCs", "the duty still applies to every factor")],
    ["Original s.19(1): filing within thirty days of assignment.",
     "Amended s.19(1): within such time from the date of assignment, in such manner and on such fee as may be prescribed.",
     "New s.19(1A): TReDS files on behalf of the factor for TReDS-financed receivables."],
    "FRA s.19(1) as amended 2021", "Older texts still quote '30 days'.",
    "conceptual", f"{FRA}, s.19(1) (as amended 2021)")

# ---- L3 (6)
add("fra_def", "L3",
    "Consider the following under s.2 of the Factoring Regulation Act, 2011 (as amended):\n\n1. A 'factor' may be an NBFC holding a certificate under s.3, a bank, a statutory corporation or a Government company.\n2. An 'assignor' is any person who is the owner of a receivable.\n3. 'Receivables' cover money owed for goods only; dues for services are outside the definition.\n\nWhich of the statements is/are correct?",
    "1 and 2 only",
    [("1 only", "misses the assignor definition"),
     ("2 and 3 only", "reads factor narrowly and excludes services"),
     ("1, 2 and 3", "receivables include dues for services")],
    ["Factor: NBFC with CoR under s.3, bank, statutory corporation, or Government company.",
     "Assignor: any person who is the owner of any receivable.",
     "Receivables: money owed and unpaid for goods OR services, including toll/infrastructure-use dues (2021)."],
    "FRA s.2", "Services receivables were always included; 2021 added toll/infrastructure dues.",
    "statement", f"{FRA}, s.2")

add("fra_reg", "L3",
    "**Assertion (A):** After the 2021 amendment, an NBFC need not have factoring as its principal business to be registered as a factor under the Factoring Regulation Act.\n\n**Reason (R):** The Factoring Regulation (Amendment) Act, 2021 omitted the proviso and Explanation to s.3(2) that confined registration to NBFCs whose principal business was factoring, and left the manner of registration to RBI regulations.",
    "Both A and R are true and R is the correct explanation of A",
    [("Both A and R are true but R is not the correct explanation of A", "R is the amendment that produces A"),
     ("A is false but R is true", "assumes the principal-business test survives in the Act"),
     ("A is true but R is false", "misattributes the change to RBI directions alone")],
    ["Pre-2021, s.3(2) proviso/Explanation limited registration to NBFCs with factoring as principal business.",
     "2021: proviso and Explanation omitted; s.3(4) substituted — registration as specified by RBI regulations (s.31A).",
     "Result: a much wider set of NBFCs can undertake factoring, subject to RBI regulations."],
    "FRA s.3 as amended 2021", "Any residual conditions now come from RBI regulations, not the statute.",
    "assertion-reason", f"{FRA}, s.3 (as amended 2021), s.31A")

add("fra_asg", "L3",
    "Consider the following under s.7 of the Factoring Regulation Act:\n\n1. At the time of assignment, the assignor must disclose to the assignee any defences and rights of set-off available to the debtor.\n2. On execution of the written agreement, any security interest created exclusively to secure the receivable vests in the assignee.\n3. Where the receivable is already security for a bank loan and the assignor notifies this, the assignee pays the consideration to that bank.\n\nWhich of the statements is/are correct?",
    "1, 2 and 3",
    [("1 and 2 only", "misses s.7(3) protection of the prior encumbrancer"),
     ("2 and 3 only", "misses the disclosure duty in s.7(1)"),
     ("1 and 3 only", "misses vesting of security interest in s.7(2)")],
    ["s.7(1): written assignment; assignor discloses debtor's defences and set-off.",
     "s.7(2): rights, remedies and exclusive security interest vest in the assignee, with absolute right to recover.",
     "s.7(3): if encumbered and notified, consideration is paid to the bank/creditor."],
    "FRA s.7", "s.7(3) protects the existing lender against a double-pledge of receivables.",
    "statement", f"{FRA}, s.7")

add("fra_cersai", "L3",
    "Consider the following about receivables financed through a Trade Receivables Discounting System (TReDS):\n\n1. A TReDS is a payment system authorised by the RBI under s.7 of the PSS Act for financing trade receivables.\n2. For TReDS-financed receivables, the particulars of assignment and of satisfaction are filed with the Central Registry by the TReDS on behalf of the factor.\n3. The factor must still separately file the same particulars itself within 30 days.\n\nWhich of the statements is/are correct?",
    "1 and 2 only",
    [("2 only", "misses the s.2(sa) definition"),
     ("1 and 3 only", "revives the pre-2021 30-day duty on the factor"),
     ("1, 2 and 3", "duplicates the filing contrary to s.19(1A)")],
    ["s.2(sa) (2021): TReDS = payment system authorised under s.7 PSS Act for financing trade receivables.",
     "s.19(1A): particulars under s.19(1) and (3) are filed on behalf of the factor by the TReDS.",
     "No parallel 30-day filing by the factor; the fixed 30-day limit itself was removed."],
    "FRA s.2(sa), s.19(1A)", "TReDS links the Factoring Act to the PSS Act.",
    "statement", f"{FRA}, s.2(sa), s.19(1A)")

extra = 32
p21 = 5 * LAKH + 10000 * extra
add("fra_pen", "L3",
    f"A factor defaults in filing assignment particulars under s.19; the default continues for {extra} days. Which option correctly states the maximum penalty on the factor and the payment window?",
    f"{L(p21)}, imposed by the RBI; payable within 14 days of notice",
    [(f"{L(5*LAKH + 5000*extra)}, imposed by the RBI; payable within 14 days of notice", "used ₹5,000/day"),
     (f"{L(p21)}, imposed by CERSAI; payable within 30 days of notice", "wrong authority and PSS 30-day period"),
     (f"{L(p21)}, imposed by the RBI; payable within 30 days of notice", "PSS Act 30-day period borrowed")],
    ["s.21: default in filing under s.19 — company and every officer in default liable to penalty up to ₹5 lakh, plus up to ₹10,000 per day of continuing default.",
     "Imposed by the RBI per s.22(2)–(4); payable within 14 days of the demand notice.",
     f"₹5 lakh + ₹10,000 × {extra} = {L(p21)}."],
    "₹5 lakh + ₹10,000 × days", "CERSAI keeps the register; the RBI penalises.",
    "numerical", f"{FRA}, s.21, s.22")

add("fra_reg", "L3",
    "Consider the following under the Factoring Regulation Act:\n\n1. A Government company doing factoring must obtain a certificate of registration under s.3.\n2. If a factor fails to comply with an RBI direction under s.6(2), the RBI may, after hearing it, prohibit it from undertaking factoring business.\n3. Provisions of Chapter IIIB of the RBI Act applicable to registered NBFCs apply mutatis mutandis to a factor registered under s.3.\n\nWhich of the statements is/are correct?",
    "2 and 3 only",
    [("1 and 2 only", "Government companies are exempt under s.5"),
     ("1, 2 and 3", "ignores the s.5 exemption"),
     ("1 and 3 only", "misses the s.6(3) prohibition power")],
    ["s.5: s.3 does not apply to Government companies — statement 1 wrong.",
     "s.6(3): prohibition after reasonable opportunity of hearing — correct.",
     "s.4: Chapter IIIB of RBI Act applies mutatis mutandis to registered factors — correct."],
    "FRA s.4, s.5, s.6", "Prohibition is in addition to the s.22 monetary penalty.",
    "statement", f"{FRA}, s.4, s.5, s.6")

# ---- L4 case set (4)
CASE_F = ("**Case — Kaveri Castings (a micro enterprise) and Sutlej Factors Ltd (an NBFC).** Kaveri supplied goods worth ₹40 lakh to "
          "Narmada Motors Ltd and on 1 March 2027 assigned the invoice by written agreement to Sutlej, which paid 80% up-front. Narmada had "
          "paid Kaveri an advance of ₹5 lakh against this supply on 1 February 2027. Sutlej's notice of assignment, carrying Kaveri's express "
          "authority, reached Narmada on 10 March 2027. On 20 March 2027 Narmada nevertheless paid ₹8 lakh to Kaveri. The financing was "
          "arranged bilaterally, not through a TReDS.")
inv, adv, post = 40 * LAKH, 5 * LAKH, 8 * LAKH
bal = inv - adv
add("fra_asg", "L4", CASE_F + "\n\nTo obtain a valid discharge, the amount Narmada must now pay to Sutlej is:",
    L(bal),
    [(L(bal - post), "treated the post-notice ₹8 lakh paid to Kaveri as a discharge"),
     (L(inv), "ignored the pre-notice advance disclosed to the assignee"),
     (L(0.8 * inv), "confused the factor's up-front payment with the debtor's liability")],
    ["Pre-notice advance of ₹5 lakh: the debtor intimates it (s.12(a)); it is a set-off the assignor must disclose (s.7(1)).",
     "Post-notice payment of ₹8 lakh to Kaveri does not discharge Narmada (s.9, s.12(b)).",
     f"Due to Sutlej = {L(inv)} − {L(adv)} = {L(bal)}."],
    "Due = Invoice − pre-notice payments", "Only payments made before notice reduce what the debtor owes the factor.",
    "case", f"{FRA}, s.7, s.9, s.12", group="ACTP-CASE-KAVERI")

add("fra_asg", "L4", CASE_F + "\n\nWhat is the legal position of the ₹8 lakh that Kaveri received on 20 March 2027?",
    "Kaveri holds it as trustee for Sutlej, to pay over",
    [("Kaveri may keep it; Sutlej can only sue Narmada", "s.13 deems the assignor a trustee"),
     ("It discharges Narmada; Sutlej must look to Kaveri", "post-notice payment gives no discharge"),
     ("It must be refunded to Narmada as paid by mistake", "no refund rule; the trust runs to the assignee")],
    ["s.13: payment to the assignor on an assigned receivable is deemed for the assignee's benefit; the assignor holds it as trustee and must pay it over.",
     "Narmada is not discharged by that payment (s.12(b)); Sutlej's recovery of the ₹8 lakh is from Kaveri as trustee or Narmada as debtor, without double recovery."],
    "FRA s.12(b), s.13", "A trust over the money does not revive a discharge for the debtor.",
    "case", f"{FRA}, s.12, s.13", group="ACTP-CASE-KAVERI")

br, mo = 0.0675, 3
rate = 3 * br
intr = bal * ((1 + rate / 12) ** mo - 1)
simple = bal * rate * mo / 12
atbank = bal * ((1 + br / 12) ** mo - 1)
assert abs(rate - 0.2025) < 1e-12
add("fra_asg", "L4", CASE_F + f"\n\nNarmada pays the {L(bal)} due exactly {mo} months after the appointed day under the MSMED Act. Taking the RBI bank rate as {br*100:.2f}% (given), the interest for delay is receivable by, and amounts to (nearest rupee):",
    f"Sutlej, {R(intr)}",
    [(f"Kaveri, {R(intr)}", "interest belongs to the assignee under s.14(2)"),
     (f"Sutlej, {R(simple)}", "simple interest; MSMED Act requires monthly compounding"),
     (f"Sutlej, {R(atbank)}", "bank rate used instead of three times the bank rate")],
    ["s.14: where the assignor is a micro/small enterprise, the debtor's liability is subject to ss.15–17 MSMED Act; the assignee is entitled to interest for delay.",
     f"MSMED s.16: compound interest with monthly rests at 3 × bank rate = {rate*100:.2f}% p.a.",
     f"Interest = {inr(bal)} × [(1 + {rate:.4f}/12)^{mo} − 1] = {R(intr)}."],
    "I = P[(1 + 3·BR/12)^n − 1]", "Monthly rests + three times bank rate; payee is the factor.",
    "case", f"{FRA}, s.14; MSMED Act 2006, s.16", group="ACTP-CASE-KAVERI")

extra = 15
add("fra_cersai", "L4", CASE_F + f"\n\nSutlej fails to register the particulars of the assignment with the Central Registry within the prescribed time, and the default continues for {extra} days. Which statement is correct?",
    f"Sutlej and its defaulting officers face up to {L(5*LAKH+10000*extra)} from RBI",
    [("Narmada's TReDS platform should have filed it, so Sutlej is not liable", "not a TReDS deal; s.19(1A) inapplicable"),
     (f"Only Sutlej's officers face up to {L(5*LAKH+10000*extra)} from CERSAI", "company also liable; RBI, not CERSAI, imposes"),
     (f"Sutlej and its defaulting officers face up to {L(5*LAKH+5000*extra)} from RBI", "used ₹5,000/day")],
    ["Bilateral (non-TReDS) deal → Sutlej must file under s.19(1).",
     "s.21: company and every officer in default — up to ₹5 lakh plus up to ₹10,000 per day of continuing default, imposed by the RBI.",
     f"₹5 lakh + ₹10,000 × {extra} = {L(5*LAKH+10000*extra)}."],
    "₹5 lakh + ₹10,000 × days", "The TReDS filing mechanism applies only to TReDS-financed receivables.",
    "case", f"{FRA}, s.19, s.21", group="ACTP-CASE-KAVERI")

# =====================================================================================
#  NEGOTIABLE INSTRUMENTS ACT, 1881  (22)
# =====================================================================================
# ---- L1 (4)
add("ni_inst", "L1",
    "Under s.6 of the Negotiable Instruments Act, 1881, a 'cheque' is:",
    "A bill on a specified banker, payable only on demand",
    [("A promissory note drawn on a banker payable on demand", "a cheque is a bill (order), not a note (promise)"),
     ("A bill drawn on any person payable on demand", "the drawee must be a specified banker"),
     ("A bill drawn on a banker payable at a fixed future date", "a cheque cannot be payable otherwise than on demand")],
    ["s.6: a cheque is a bill of exchange drawn on a specified banker and not expressed to be payable otherwise than on demand.",
     "It includes the electronic image of a truncated cheque and a cheque in electronic form."],
    "NI Act s.6", "Every cheque is a bill; not every bill is a cheque.",
    "conceptual", f"{NIA}, s.6")

add("ni_cross", "L1",
    "A cheque bears across its face the name 'Canara Bank', with or without two parallel transverse lines. Under the NI Act, the cheque is:",
    "Crossed specially to Canara Bank",
    [("Crossed generally", "general crossing has no banker's name"),
     ("Crossed 'account payee only'", "A/c payee is a banking-practice direction, not this"),
     ("Uncrossed, as a bank name alone is no crossing", "s.124 treats the banker's name itself as a special crossing")],
    ["s.124: where a cheque bears across its face the name of a banker, with or without 'not negotiable', it is crossed specially to that banker.",
     "s.123: general crossing = two parallel transverse lines (with or without '& Co.')."],
    "NI Act s.123, s.124", "Lines are optional for a special crossing; the banker's name is essential.",
    "conceptual", f"{NIA}, s.124")

add("ni_hold", "L1",
    "Under s.9 of the NI Act, a 'holder in due course' is one who became the holder:",
    "For value, before maturity, without cause to suspect defect",
    [("For consideration, at any time, even after it became overdue", "an overdue instrument cannot be taken in due course"),
     ("Before maturity, even without consideration, in good faith", "consideration is essential"),
     ("By inheritance from a previous holder in due course", "that is s.53 derivation, not s.9 status")],
    ["s.9: holder for consideration who became possessor (bearer) or payee/endorsee (order) before the amount became payable,",
     "without sufficient cause to believe any defect in the title of the transferor."],
    "NI Act s.9", "Three elements: consideration, before maturity, good faith.",
    "conceptual", f"{NIA}, s.9")

amt = 3.6 * LAKH
add("ni_138", "L1",
    f"A cheque for {L(amt)} is dishonoured and all conditions of s.138 of the NI Act are satisfied. The drawer is punishable with imprisonment up to:",
    f"2 years, or fine up to {L(2*amt)}, or both",
    [(f"1 year, or fine up to {L(2*amt)}, or both", "pre-2002 one-year term"),
     (f"2 years, or fine up to {L(amt)}, or both", "fine capped at the cheque amount"),
     (f"3 years, or fine up to {L(3*amt)}, or both", "invented higher limits")],
    ["s.138: imprisonment up to two years, or fine up to twice the cheque amount, or both.",
     f"Twice {L(amt)} = {L(2*amt)}."],
    "Fine ≤ 2 × cheque amount", "The two-year term dates from the 2002 amendment.",
    "numerical", f"{NIA}, s.138")

# ---- L2 (7)
bd = D("2027-01-31"); nom = addm(bd, 1); mat = plus(nom, 3)
assert nom == D("2027-02-28") and mat == D("2027-03-03")
add("ni_mat", "L2",
    f"A bill of exchange dated {fd(bd)} is payable one month after date. Assuming no public holiday intervenes, it is at maturity on:",
    fd(mat),
    [(fd(nom), "days of grace ignored"),
     (fd(plus(plus(bd, 30), 3)), "one month taken as 30 days"),
     (fd(plus(nom, 2)), "days of grace counted including the nominal due date")],
    ["s.23: payable months after date — due on the corresponding day of the month; if none, the last day of that month.",
     f"February 2027 has no 31st → nominal due date {fd(nom)}.",
     f"s.22: three days of grace → {fd(mat)}."],
    "Maturity = nominal due date + 3 days of grace", "No corresponding date → last day of the month.",
    "numerical", f"{NIA}, s.22, s.23")

sight = D("2026-10-14"); nom = plus(sight, 60); mat = plus(nom, 3)
assert mat == D("2026-12-16") and weekday_ok(mat)
add("ni_mat", "L2",
    f"A bill payable 60 days after sight is presented for sight on {fd(sight)}. Assuming no public holiday intervenes, its date of maturity is:",
    fd(mat),
    [(fd(nom), "days of grace ignored"),
     (fd(plus(plus(sight, 59), 3)), "day of presentment included in the 60 days"),
     (fd(plus(addm(sight, 2), 3)), "60 days treated as two months")],
    ["s.24: exclude the day of presentment for sight.",
     f"{fd(sight)} + 60 days = {fd(nom)}.", f"s.22: + 3 days of grace = {fd(mat)}."],
    "Maturity = sight date + n days + 3", "Days ≠ months: count actual days.",
    "numerical", f"{NIA}, s.22, s.24")

bd = D("2026-06-29"); nom = addm(bd, 3); g = plus(nom, 3); pre = plus(g, -1)
assert g == D("2026-10-02") and pre.weekday() == 3
add("ni_mat", "L2",
    f"A bill dated {fd(bd)} is payable three months after date. The day on which it would fall due, including days of grace, is a public holiday (Gandhi Jayanti). The bill is deemed due on:",
    fd(pre),
    [(fd(g), "public holiday ignored"),
     (fd(plus(g, 1)), "moved to the next succeeding day instead of preceding"),
     (fd(nom), "days of grace ignored")],
    [f"Nominal due date = {fd(nom)}; + 3 days of grace = {fd(g)} (public holiday).",
     f"s.25: when maturity falls on a public holiday, the instrument is deemed due on the next preceding business day → {fd(pre)}."],
    "NI Act s.25 — preceding business day", "Under the NI Act maturity moves backwards, not forwards.",
    "numerical", f"{NIA}, s.22, s.23, s.25")

add("ni_cross", "L2",
    "A cheque crossed generally and marked 'not negotiable' is stolen from the payee. The thief transfers it to Sameer, who takes it for value and in good faith. Under s.130, Sameer:",
    "Gets no better title than the thief, i.e. none",
    [("Gets good title as he took it for value in good faith", "that is the HIDC rule, displaced by s.130"),
     ("Gets good title because 'not negotiable' stops only bearer transfer", "misreads the effect of the words"),
     ("Gets good title only after collecting it through his bank", "collection does not cure title")],
    ["s.130: a person taking a cheque crossed generally or specially and bearing 'not negotiable' shall not have, and shall not be capable of giving, a better title than that of the transferor.",
     "The thief had no title; so Sameer has none."],
    "NI Act s.130", "'Not negotiable' keeps transferability but removes HIDC protection.",
    "conceptual", f"{NIA}, s.130")

memo = D("2027-01-12"); nl = plus(memo, 30)
assert weekday_ok(nl)
add("ni_138", "L2",
    f"The payee receives the bank's return memo for a dishonoured cheque on {fd(memo)}. Excluding the day of receipt, the last date for issuing the demand notice under proviso (b) to s.138 is:",
    fd(nl),
    [(fd(addm(memo, 1)), "30 days read as one calendar month"),
     (fd(plus(memo, 15)), "confused with the drawer's 15-day payment window"),
     (fd(plus(memo, 29)), "counted the day of receipt")],
    ["Proviso (b): notice in writing within thirty days of receipt of information from the bank about the return.",
     f"{fd(memo)} + 30 days = {fd(nl)}."],
    "Notice deadline = memo receipt + 30 days", "30 days (notice) vs 15 days (payment) vs one month (complaint).",
    "numerical", f"{NIA}, s.138 proviso (b)")

amt = 7.5 * LAKH
add("ni_comp", "L2",
    f"In a trial under s.138 for a cheque of {L(amt)}, the accused pleads not guilty in a summary trial. The maximum interim compensation the court may order under s.143A, and the period for payment, are:",
    f"{L(0.2*amt)}, within 60 days, extendable by up to 30 days",
    [(f"{L(0.2*amt)}, within 30 days, extendable by up to 15 days", "wrong payment periods"),
     (f"{L(0.3*amt)}, within 60 days, extendable by up to 30 days", "30% instead of 20%"),
     (f"{L(2*0.2*amt)}, within 60 days, extendable by up to 30 days", "20% of the maximum fine (twice the cheque)")],
    ["s.143A(1)–(2): interim compensation not exceeding 20% of the cheque amount.",
     "s.143A(3): payable within 60 days of the order, extendable by up to 30 days for sufficient cause.",
     f"20% × {L(amt)} = {L(0.2*amt)}."],
    "Interim compensation ≤ 20% × cheque amount", "Base is the cheque amount, not the fine.",
    "numerical", f"{NIA}, s.143A (inserted 2018)")

add("ni_hold", "L2",
    "Prakash obtains a promissory note from its maker by fraud and endorses it for value to Qadir, who takes it in good faith before maturity. Qadir later gifts the note to Rukmini, who knew nothing of the fraud. Rukmini sues the maker. Under s.53 of the NI Act, Rukmini:",
    "Can recover, as she has Qadir's rights as HIDC",
    [("Cannot recover, because she gave no consideration", "s.53 lets a donee succeed to HIDC rights"),
     ("Cannot recover, because the note originated in fraud", "Qadir's HIDC status cleansed the defect"),
     ("Can recover only the amount Qadir had paid Prakash", "no such limitation")],
    ["Qadir is a holder in due course (s.9).",
     "s.53: a holder who derives title from a holder in due course has his rights, unless a party to the fraud.",
     "Rukmini was not a party to the fraud → she has Qadir's rights against the maker."],
    "NI Act s.9, s.53", "Consideration is needed to become a HIDC, not to derive title from one.",
    "conceptual", f"{NIA}, s.53")

# ---- L3 (7)
cd = D("2027-01-05"); pres = D("2027-03-20"); memo = D("2027-03-23")
ns, nr = D("2027-04-12"), D("2027-04-16")
coa = plus(nr, 16); lastc = addm(coa, 1)
assert pres <= addm(cd, 3) and ns <= plus(memo, 30) and weekday_ok(lastc)
add("ni_138", "L3",
    f"A cheque dated {fd(cd)} is presented on {fd(pres)} and returned 'funds insufficient'; the payee receives the return memo on {fd(memo)}. Notice is sent on {fd(ns)} and received by the drawer on {fd(nr)}; no payment follows. Treat the day of receipt as excluded from the 15-day period, the cause of action as arising on the next day, and the one-month limitation as ending on the corresponding date of the next month. The last date for filing the complaint under s.142(1)(b) is:",
    fd(lastc),
    [(fd(addm(plus(nr, 15), 1)), "cause of action taken on the 15th day itself"),
     (fd(addm(nr, 1)), "one month counted from receipt of notice"),
     (fd(addm(memo, 2)), "limitation run as two months from the return memo")],
    [f"Presentation within validity (cheque dated {fd(cd)}); notice within 30 days of {fd(memo)}.",
     f"15 days from {fd(nr)} end on {fd(plus(nr, 15))}; cause of action arises {fd(coa)}.",
     f"One month from {fd(coa)} → {fd(lastc)}."],
    "Limitation = 1 month from cause of action", "Cause of action arises only after the 15-day window fully expires.",
    "numerical", f"{NIA}, s.138, s.142(1)(b)")

cd = D("2027-02-10"); pres = D("2027-05-25")
assert pres > addm(cd, 3) and pres < addm(cd, 6)
add("ni_138", "L3",
    f"A cheque dated {fd(cd)} is presented on {fd(pres)} and returned unpaid for insufficiency of funds. Consider:\n\n1. Proviso (a) to s.138 requires presentation within six months of the date of the cheque or within its period of validity, whichever is earlier.\n2. With the RBI-prescribed validity of three months, this presentation falls outside the validity period.\n3. Since presentation is within six months of the date of the cheque, a s.138 prosecution will lie.\n\nWhich of the statements is/are correct?",
    "1 and 2 only",
    [("1 and 3 only", "ignores 'whichever is earlier'"),
     ("3 only", "reads six months as the operative limit"),
     ("1, 2 and 3", "statements 2 and 3 cannot both hold")],
    ["Proviso (a): within six months or validity period, whichever is earlier.",
     f"Validity is three months (RBI, since 1 April 2012) → expires around {fd(addm(cd, 3))}; {fd(pres)} is beyond it.",
     "Condition (a) fails; s.138 is not attracted."],
    "Earlier of 6 months and validity (3 months)", "The statute's six months is overridden by the shorter validity period.",
    "statement", f"{NIA}, s.138 proviso (a); RBI circular on cheque validity (3 months, w.e.f. 1 April 2012)")

add("ni_138", "L3",
    "**Assertion (A):** Where a cheque was delivered for collection through the payee's account, a s.138 complaint lies in the court within whose jurisdiction the payee's bank branch is situated.\n\n**Reason (R):** Section 142(2)(a) of the NI Act, inserted in 2015, vests jurisdiction in the court where the branch of the bank at which the payee (or holder in due course) maintains the account is situated.",
    "Both A and R are true and R is the correct explanation of A",
    [("Both A and R are true but R is not the correct explanation of A", "R is the jurisdictional rule in A"),
     ("A is false but R is true", "assumes the drawee bank's location governs"),
     ("A is true but R is false", "misattributes the rule to case law alone")],
    ["2015 amendment: s.142(2)(a) — cheque delivered for collection through an account → court where the payee's bank branch is situated.",
     "It superseded the drawee-bank rule of Dashrath Rupsingh Rathod (2014)."],
    "NI Act s.142(2)(a)", "Pre-2015 case law pointed to the drawee bank's location.",
    "assertion-reason", f"{NIA}, s.142(2) (amended 2015)")

mt = [("P", "s.123"), ("Q", "s.126"), ("R", "s.131"), ("S", "s.85(1)")]
pn = ["Two parallel transverse lines — general crossing",
      "Crossed cheque payable only to a banker / the named banker",
      "Protection to the collecting banker receiving payment in good faith for a customer",
      "Protection to the paying banker paying an order cheque bearing the payee's apparent endorsement"]
order = [0, 1, 2, 3]
tbl = "| Section | | Provision |\n|---|---|---|\n" + "\n".join(
    f"| {mt[i][0]}. {mt[i][1]} | | {i+1}. {pn[i]} |" for i in order)
add("ni_cross", "L3",
    f"Match the section of the NI Act with its provision.\n\n{tbl}",
    "P-1, Q-2, R-3, S-4",
    [("P-1, Q-2, R-4, S-3", "swaps collecting and paying banker protections"),
     ("P-2, Q-1, R-3, S-4", "swaps the definition and the payment rule"),
     ("P-1, Q-3, R-2, S-4", "places collecting-banker protection in s.126")],
    ["s.123: general crossing.", "s.126: payment of crossed cheques only to a banker (special — to the named banker).",
     "s.131: collecting banker's protection (good faith, without negligence, for a customer).",
     "s.85(1): paying banker discharged on paying an order cheque whose endorsement purports to be the payee's."],
    "NI Act s.85, s.123, s.126, s.131", "s.131 = collecting banker; s.85 / s.128 = paying banker.",
    "match", f"{NIA}, s.85, s.123, s.126, s.131")

add("ni_comp", "L3",
    "Consider the following regarding interim compensation under s.143A of the NI Act:\n\n1. In a summary or summons trial, it may be ordered where the drawer pleads not guilty to the accusation.\n2. If the drawer is acquitted, the court shall direct the complainant to repay it with interest at the RBI bank rate prevailing at the beginning of the relevant financial year.\n3. Any fine or compensation later awarded under s.138 is reduced by the interim compensation already paid.\n\nWhich of the statements is/are correct?",
    "1, 2 and 3",
    [("1 and 2 only", "misses the set-off in s.143A(6)"),
     ("1 and 3 only", "misses the repayment on acquittal"),
     ("2 and 3 only", "misses the summary/summons-trial trigger")],
    ["s.143A(1)(a): summary/summons trial — accused pleads not guilty; (b) other cases — on framing of charge.",
     "s.143A(4): on acquittal, complainant repays with interest at bank rate (RBI) prevailing at the start of the FY, within 60 (+30) days.",
     "s.143A(6): fine/compensation under s.138 reduced by the interim compensation paid."],
    "NI Act s.143A", "Interim compensation is refundable and creditable.",
    "statement", f"{NIA}, s.143A")

bd = D("2026-11-20"); acc = D("2026-11-22")
nom = plus(bd, 80); mat = plus(nom, 3)
assert weekday_ok(mat) and weekday_ok(nom)
add("ni_mat", "L3",
    f"A bill dated {fd(bd)} and payable 80 days after date is accepted on {fd(acc)}. Assuming no public holiday intervenes, its date of maturity is:",
    fd(mat),
    [(fd(plus(plus(acc, 80), 3)), "counted from acceptance, as if payable after sight"),
     (fd(nom), "days of grace ignored"),
     (fd(plus(plus(bd, 79), 3)), "date of the bill included in the 80 days")],
    ["'After date' → count from the date of the bill, excluding that day (s.24).",
     f"{fd(bd)} + 80 days = {fd(nom)}; + 3 days of grace (s.22) = {fd(mat)}."],
    "Maturity = date of bill + n days + 3", "Acceptance date matters only for after-sight bills.",
    "numerical", f"{NIA}, s.22, s.24")

add("ni_hold", "L3",
    "Consider the following under the NI Act:\n\n1. Every holder of a negotiable instrument is presumed to be a holder in due course until the contrary is proved.\n2. A person who takes a bill after it has become overdue can be a holder in due course if he pays full value.\n3. Every prior party to an instrument is liable to a holder in due course until the instrument is duly satisfied.\n\nWhich of the statements is/are correct?",
    "1 and 3 only",
    [("1 and 2 only", "overdue instrument cannot be taken in due course"),
     ("2 and 3 only", "drops the s.118(g) presumption and accepts overdue HIDC"),
     ("1, 2 and 3", "statement 2 contradicts s.9")],
    ["s.118(g): presumption that the holder is a holder in due course (rebuttable).",
     "s.9: must become holder before the amount became payable — statement 2 wrong.",
     "s.36: every prior party is liable to a holder in due course until duly satisfied."],
    "NI Act s.9, s.36, s.118(g)", "Value alone cannot cure taking an overdue instrument.",
    "statement", f"{NIA}, s.9, s.36, s.118")

# ---- L4 case set (4)
CASE_N = ("**Case — Rohan Mehta and Vaidehi Traders.** To repay a trade debt, Rohan issued a cheque for ₹12 lakh dated 1 March 2027 to "
          "Vaidehi Traders. Vaidehi presented it on 20 May 2027; it was returned 'funds insufficient' and Vaidehi received the return memo on "
          "24 May 2027. Its demand notice was sent on 15 June 2027 and delivered to Rohan on 18 June 2027. Rohan did not pay. For all "
          "periods, exclude the first day; the cause of action arises on the day after the 15-day window ends, and a one-month period ends "
          "on the corresponding date of the next month. In the ensuing summary trial Rohan pleaded not guilty; on 1 October 2027 the "
          "Magistrate ordered maximum interim compensation. Rohan was eventually convicted and ordered to pay compensation of ₹18 lakh; he "
          "has appealed.")
cd, pres, memo, ns, nr = D("2027-03-01"), D("2027-05-20"), D("2027-05-24"), D("2027-06-15"), D("2027-06-18")
assert pres <= addm(cd, 3)
nl = plus(memo, 30)
add("ni_138", "L4", CASE_N + "\n\nWhich statement about the first two conditions of the s.138 proviso is correct?",
    f"Both met: presented within 3-month validity; notice by {fd(nl)}",
    [("Presentation invalid: a cheque must be presented within 30 days", "invents a 30-day presentation limit"),
     (f"Notice late: it had to be sent by {fd(plus(memo, 15))}", "15-day payment window applied to the notice"),
     (f"Notice late: it had to be received by {fd(plus(memo, 15))}", "15 days and 'receipt' both misapplied")],
    [f"(a) Cheque dated {fd(cd)}; presented {fd(pres)} — within three months → valid.",
     f"(b) Notice within 30 days of {fd(memo)}, i.e. by {fd(nl)}; sent {fd(ns)} → valid (the Act requires the notice to be made within 30 days)."],
    "Presentation ≤ validity; notice ≤ memo + 30 days", "15 days is the drawer's window after receiving notice.",
    "case", f"{NIA}, s.138 provisos (a), (b)", group="ACTP-CASE-ROHAN")

coa = plus(nr, 16); lastc = addm(coa, 1)
assert weekday_ok(lastc)
add("ni_138", "L4", CASE_N + "\n\nThe last date for Vaidehi to file the complaint without seeking condonation is:",
    fd(lastc),
    [(fd(addm(plus(nr, 15), 1)), "cause of action taken on the 15th day"),
     (fd(addm(ns, 1)), "one month counted from dispatch of notice"),
     (fd(addm(memo, 2)), "two months from the return memo")],
    [f"15 days from {fd(nr)} end on {fd(plus(nr, 15))}; cause of action {fd(coa)}.",
     f"s.142(1)(b): one month from the cause of action → {fd(lastc)}; later filing needs 'sufficient cause' (proviso)."],
    "Limitation = 1 month from cause of action", "Dispatch date is irrelevant to the payment window, which runs from receipt.",
    "case", f"{NIA}, s.138, s.142(1)(b)", group="ACTP-CASE-ROHAN")

chq = 12 * LAKH; order_d = D("2027-10-01")
ic = 0.2 * chq; pay_by = plus(order_d, 60)
add("ni_comp", "L4", CASE_N + "\n\nThe interim compensation ordered on 1 October 2027, and the date by which Rohan must ordinarily pay it, are:",
    f"{L(ic)}, by {fd(pay_by)}",
    [(f"{L(ic)}, by {fd(plus(order_d, 30))}", "30-day extension period taken as the main period"),
     (f"{L(0.2*2*chq)}, by {fd(pay_by)}", "20% of twice the cheque amount"),
     (f"{L(0.2*18*LAKH)}, by {fd(pay_by)}", "20% of the later trial compensation (that is the s.148 base)")],
    ["s.143A(1)(a): summary trial, plea of not guilty → court may order interim compensation.",
     f"s.143A(2): up to 20% of cheque amount = 20% × {L(chq)} = {L(ic)}.",
     f"s.143A(3): within 60 days of the order → {fd(pay_by)} (extendable by up to 30 days)."],
    "Interim ≤ 20% × cheque; pay within 60 (+30) days", "s.143A base = cheque; s.148 base = fine/compensation awarded.",
    "case", f"{NIA}, s.143A", group="ACTP-CASE-ROHAN")

award = 18 * LAKH
dep = 0.2 * award
add("ni_comp", "L4", CASE_N + "\n\nIn Rohan's appeal against conviction, the minimum deposit the appellate court may order under s.148 is:",
    f"{L(dep)}, in addition to the interim compensation paid",
    [(f"{L(dep - ic)}, after deducting the interim compensation", "s.148 proviso: deposit is in addition to s.143A amount"),
     (f"{L(0.2*chq)}, in addition to the interim compensation paid", "20% of the cheque, not of the award"),
     (f"{L(dep + ic)}, as a single consolidated deposit", "added interim compensation into the deposit")],
    ["s.148(1): appellate court may order the appellant to deposit a minimum of 20% of the fine or compensation awarded by the trial court.",
     f"20% × {L(award)} = {L(dep)}.",
     f"Proviso: this is in addition to interim compensation paid under s.143A ({L(ic)})."],
    "Deposit ≥ 20% × trial-court fine/compensation", "No netting of the s.143A amount against the s.148 deposit.",
    "case", f"{NIA}, s.148", group="ACTP-CASE-ROHAN")

B.write()
