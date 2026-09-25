"""REG-CORPUS-ACT-IPI builder: financial-sector-acts — Insurance Act 1938 (22), IRDA Act 1999 (20),
PFRDA Act 2013 (24), IFSCA Act 2019 (24). Total 90.
Every date / amount / count in keys and distractors is computed below; asserts guard hand-checked keys.
Statutory positions as of mid-2026, incl. the Sabka Bima Sabki Raksha (Amendment of Insurance Laws) Act, 2025
(in force 05-02-2026) where relied on. Figures that are not statutory are given in the stem as data.
"""
import sys, os as _os
from datetime import date, timedelta
from collections import Counter

_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _REG)
from reglib import Batch, inr, R, pct, lakh, crore, make_slug  # noqa: F401

B = Batch("REG-CORPUS-ACT-IPI", "financial-sector-acts", "ACTI",
          list_file=_os.path.join(_REG, 'lists', 'fsa.REG-CORPUS-ACT-IPI.tsv'))

NAMES = {
    "INS_REG": "Insurance Act — registration, capital and foreign insurer restrictions",
    "INS_INV": "Insurance Act — investments, loans and commission controls",
    "INS_AN": "Insurance Act — assignment and nomination under ss.38–39",
    "INS_45": "Insurance Act — s.45 indisputability and s.64VB premium in advance",
    "INS_PEN": "Insurance Act — surveyors, penalties and appeals",
    "IR_EST": "IRDA Act — establishment, composition and tenure",
    "IR_FN": "IRDA Act — duties, powers and functions under s.14",
    "IR_FUND": "IRDA Act — funds, accounts and reports",
    "IR_CG": "IRDA Act — Central Government control and advisory committee",
    "PF_CON": "PFRDA Act — constitution, composition and tenure",
    "PF_FN": "PFRDA Act — scope and functions of the Authority",
    "PF_NPS": "PFRDA Act — National Pension System and intermediaries",
    "PF_PEN": "PFRDA Act — penalties, adjudication and offences",
    "PF_APP": "PFRDA Act — appeals, funds and oversight",
    "IF_APP": "IFSCA Act — application, definitions and SEZ linkage",
    "IF_COMP": "IFSCA Act — composition, tenure and meetings",
    "IF_POW": "IFSCA Act — functions and powers under First Schedule Acts",
    "IF_FIN": "IFSCA Act — finance, foreign currency and accountability",
    "IF_CG": "IFSCA Act — Central Government powers and overriding provisions",
}
M = {k: make_slug(v, "fsa") for k, v in NAMES.items()}
for k, s in M.items():
    assert s in B.cat, (k, s)

INS = "Insurance Act, 1938"
IRA = "Insurance Regulatory and Development Authority Act, 1999"
PFA = "Pension Fund Regulatory and Development Authority Act, 2013"
IFA = "International Financial Services Centres Authority Act, 2019"
AMD25 = " (as amended by the Sabka Bima Sabki Raksha (Amendment of Insurance Laws) Act, 2025, in force 05-02-2026)"


def add(key, level, stem, correct, wrongs, steps, formula, trap, kind="conceptual", group=None, ref=""):
    return B.add(micro=M[key], level=level, stem=stem, correct=correct, wrongs=wrongs, steps=steps,
                 formula=formula, trap=trap, kind=kind, group=group, verify_fact=True, ref=ref)


def fd(d):
    return f"{d.day} {d.strftime('%B %Y')}"


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:          # 29 Feb
        return d.replace(year=d.year + n, day=28)


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return d.replace(year=d.year + y, month=m + 1)


AR = ["Both A and R are true, and R is the correct explanation of A",
      "Both A and R are true, but R is not the correct explanation of A",
      "A is true, but R is false",
      "A is false, but R is true"]
AR_ERR = {0: "treats R as explaining A", 1: "denies the causal link R supplies", 2: "wrongly rejects R",
          3: "wrongly rejects A"}


def ar(correct_idx):
    return AR[correct_idx], [(AR[i], AR_ERR[i]) for i in range(4) if i != correct_idx]


def perm(mapping):
    return ", ".join(f"{k}-{v}" for k, v in mapping.items())


# =====================================================================================
# INSURANCE ACT, 1938  (22)  L1 4 · L2 7 · L3 7 · L4 4
# =====================================================================================

# ---- L1 ----
add("INS_REG", "L1",
    "A trading company wishes to take out a fire policy on its warehouse at Nhava Sheva with an insurer whose "
    "principal place of business is in Singapore and which is not registered in India. Under the Insurance Act, 1938, this is:",
    "Permitted only with the prior permission of the Authority (IRDAI)",
    [("Permitted with the prior approval of the Reserve Bank of India", "other regulator's power (FEMA angle) substituted for IRDAI"),
     ("Permitted freely if the premium is paid in foreign currency", "treats the bar as a currency rule rather than an insurer-location rule"),
     ("Prohibited absolutely, with no power to permit it", "misses the permission window in s.2CB")],
    ["s.2CB: no person shall take out or renew a policy on property in India with an insurer whose principal place of business is outside India,",
     "save with the prior permission of the Authority."],
    "Insurance Act s.2CB", "The gatekeeper is IRDAI, not RBI; and the bar is not absolute.",
    ref=f"{INS}, s.2CB")

add("INS_45", "L1",
    "Under s.64VB of the Insurance Act, 1938, an insurer may assume a risk in India:",
    "Only once the premium is received, guaranteed or deposited in advance as prescribed",
    [("On acceptance of the proposal, with the premium payable within the grace period", "confuses renewal grace period with first assumption of risk"),
     ("On issue of the policy document, whether or not the premium has been paid", "treats the policy document, not premium, as the trigger"),
     ("When the agent collects the signed proposal, premium following within 30 days", "invents a post-collection payment window")],
    ["s.64VB(1): no risk shall be assumed unless and until the premium payable is received,",
     "or is guaranteed to be paid, or is deposited in advance in the prescribed manner."],
    "Insurance Act s.64VB(1)", "Grace periods apply to renewal premiums of an existing policy, not to the assumption of a fresh risk.",
    ref=f"{INS}, s.64VB")

add("INS_INV", "L1",
    "Which of the following is specifically prohibited by s.27E of the Insurance Act, 1938?",
    "Investing the funds of policyholders outside India, directly or indirectly",
    [("Granting loans to the insurer's own directors", "neighbouring section — loans to directors are dealt with in s.29"),
     ("Allowing a rebate of commission to a prospective policyholder", "that is the s.41 rebate prohibition"),
     ("Paying commission to a person who is not an agent or intermediary", "that is the s.40 commission prohibition")],
    ["s.27E: no insurer shall directly or indirectly invest outside India the funds of the policyholders.",
     "Loans to directors (s.29), commission (s.40) and rebates (s.41) are separate provisions."],
    "Insurance Act s.27E", "Match the prohibition to its section — 27E is the 'outside India' bar.",
    ref=f"{INS}, s.27E")

add("INS_PEN", "L1",
    "A person aggrieved by an order of IRDAI under the Insurance Act, 1938 may appeal to:",
    "The Securities Appellate Tribunal, within 45 days of receipt of the order",
    [("The Securities Appellate Tribunal, within 30 days of receipt of the order", "wrong limitation period"),
     ("The National Company Law Appellate Tribunal, within 45 days", "wrong forum — NCLAT hears Companies Act/IBC appeals"),
     ("The Central Government, within 60 days of the order", "wrong forum; 60 days is the SAT→Supreme Court window")],
    ["s.110 (substituted in 2015): appeal against an order of the Authority lies to the Securities Appellate Tribunal,",
     "to be filed within forty-five days from the date of receipt of the order (SAT may condone delay for sufficient cause)."],
    "Insurance Act s.110", "Insurance, pension and securities appeals all go to SAT; 45 days is the common window.",
    ref=f"{INS}, s.110 (Insurance Laws (Amendment) Act, 2015)")

# ---- L2 ----
pu, sp_, prel = 102e7, 6e7, 5e7
req = 100e7
eff = pu - prel
assert eff == 97e7
add("INS_REG", "L2",
    f"Suraksha Jeevan Ltd applies to IRDAI for registration to carry on life insurance business. Its balance sheet shows:\n\n"
    f"| Item | ₹ crore |\n|---|---:|\n| Paid-up equity share capital | {pu/1e7:.0f} |\n| Securities premium | {sp_/1e7:.0f} |\n"
    f"| Preliminary expenses incurred in formation and registration | {prel/1e7:.0f} |\n\n"
    "Under s.6 of the Insurance Act, 1938, the company's position against the minimum capital requirement is:",
    f"Shortfall of {crore(req-eff,0)}",
    [(f"Complies, with a surplus of {crore(pu+sp_-prel-req,0)}", "securities premium counted as paid-up equity capital"),
     (f"Complies, with a surplus of {crore(pu-req,0)}", "preliminary expenses not excluded"),
     (f"Shortfall of {crore(200e7-eff,0)}", "₹200 crore reinsurer threshold applied to a life insurer")],
    [f"s.6(1): life insurer needs paid-up equity capital of ₹100 crore, excluding sums paid towards preliminary expenses.",
     f"Qualifying capital = {pu/1e7:.0f} − {prel/1e7:.0f} = ₹{eff/1e7:.0f} crore (securities premium is not paid-up equity capital).",
     f"Shortfall = 100 − {eff/1e7:.0f} = ₹{(req-eff)/1e7:.0f} crore."],
    "Qualifying capital = Paid-up equity − Preliminary expenses ≥ ₹100 crore (life/general)",
    "Neither securities premium nor funds used for preliminary expenses count; ₹200 crore is only for exclusive reinsurers.",
    kind="numerical", ref=f"{INS}, s.6(1)")

add("INS_AN", "L2",
    "Harish, who holds a life policy on his own life, nominates his 11-year-old daughter as the nominee. Under s.39 of the Insurance Act, 1938:",
    "He may appoint a person to receive the policy money if it becomes payable during her minority",
    [("The nomination is void because a minor cannot be a nominee", "wrongly treats minority as a bar to nomination"),
     ("A court guardianship certificate must be filed before the nomination is registered", "invents a court formality"),
     ("The insurer must hold the claim amount in deposit until she attains majority", "invents a mandatory deposit")],
    ["s.39(2): where the nominee is a minor, the policyholder may appoint any person to receive the money during the minority of the nominee.",
     "The nomination itself is valid."],
    "Insurance Act s.39(2)", "A minor can be a nominee; the Act provides an 'appointee' mechanism.",
    ref=f"{INS}, s.39")

iss, rsk, rev = date(2021, 8, 12), date(2021, 8, 20), date(2023, 3, 5)
latest = max(iss, rsk, rev)
assert latest == rev
add("INS_45", "L2",
    f"A life policy was issued on {fd(iss)} with risk commencing on {fd(rsk)}. It lapsed for non-payment and was revived on {fd(rev)}. "
    "No rider was added. Under s.45 of the Insurance Act, 1938, the policy cannot be called in question on any ground after:",
    fd(add_years(rev, 3)),
    [(fd(add_years(iss, 3)), "reckoned from date of issue, ignoring revival"),
     (fd(add_years(rsk, 3)), "reckoned from commencement of risk, ignoring revival"),
     (fd(add_years(rev, 2)), "pre-2015 two-year period applied")],
    ["s.45(1): three years from the date of the policy — date of issue, commencement of risk, revival or rider, whichever is later.",
     f"Latest of the dates = revival on {fd(rev)}.",
     f"Indisputability therefore starts after {fd(add_years(rev, 3))}."],
    "Reference date = max(issue, risk commencement, revival, rider); bar = reference date + 3 years",
    "Revival re-starts the three-year clock; the old two-year rule was replaced in 2015.",
    kind="numerical", ref=f"{INS}, s.45(1) (2015 substitution)")

prem, n_paid = 48600, 3
refund = prem * n_paid
assert refund == 145800
add("INS_45", "L2",
    f"Within two years of issue, an insurer repudiates a life policy on the ground of suppression of a material fact; fraud is "
    f"neither alleged nor proved. The policyholder had paid {n_paid} annual premiums of {R(prem)} each. Under s.45(4) of the Insurance Act, 1938, the insurer must:",
    f"Pay {R(refund)}, within 90 days of the repudiation",
    [(f"Pay {R(refund)}, within 30 days of the repudiation", "wrong time limit"),
     ("Pay nothing, since premiums stand forfeited on repudiation", "fraud-type forfeiture applied to a non-fraud repudiation"),
     (f"Pay {R(prem*(n_paid-1))}, within 90 days of the repudiation", "refunds only premiums of completed policy years")],
    ["s.45(4): within three years, a policy may be repudiated for misstatement/suppression of material fact, with written grounds.",
     "Where repudiation is not on the ground of fraud, premiums collected up to the date of repudiation must be paid within ninety days.",
     f"Refund = {n_paid} × {R(prem)} = {R(refund)}."],
    "Refund = Σ premiums collected till date of repudiation (non-fraud); time limit 90 days",
    "Only fraud-based repudiation escapes the refund; the window is 90 days.",
    kind="numerical", ref=f"{INS}, s.45(4)")

add("INS_INV", "L2",
    "Pragati General Insurance Ltd pays a car dealership's sales executive ₹1,500 for every motor policy he refers. He is neither "
    "an insurance agent nor an insurance intermediary. The arrangement is:",
    "In breach of s.40, as only agents or intermediaries may be so paid",
    [("Valid if within the commission limits specified by IRDAI under s.40", "commission limits apply only to agents/intermediaries"),
     ("Valid, because s.40 governs only rebates allowed to policyholders", "confuses s.40 with the s.41 rebate bar"),
     ("Valid if the payment is disclosed in the policy schedule", "invents a disclosure cure")],
    ["s.40(1): no person shall pay or contract to pay any remuneration or reward, by commission or otherwise, for soliciting or procuring insurance business in India",
     "to any person except an insurance agent or an intermediary/insurance intermediary.",
     "The executive is neither, so the payment is prohibited regardless of amount."],
    "Insurance Act s.40(1)", "Limits under s.40 regulate how much agents get; they do not open the door to unregistered referrers.",
    ref=f"{INS}, s.40")

thr = 50000
claimed, assessed, settled = 74500, 61200, 58000
add("INS_PEN", "L2",
    f"Assume regulations under s.64UM(2) of the Insurance Act, 1938 specify {R(thr)} as the threshold claim value. A motor "
    f"own-damage claim of {R(claimed)} is reported. A licensed surveyor assesses the loss at {R(assessed)}; the insurer settles at {R(settled)}. Which is correct?",
    "Report mandatory; the insurer may still settle at a different amount",
    [("The settlement is invalid; the insurer must pay exactly the surveyor-assessed amount", "ignores the proviso preserving the insurer's right to settle at a different amount"),
     (f"No report was needed because the settled amount of {R(settled)} is what matters", "applies the threshold to the settlement, not the claim"),
     ("The insurer must pay the full claimed amount once a surveyor has been appointed", "confuses appointment of surveyor with admission of the claim")],
    [f"s.64UM(2): a claim equal to or exceeding the specified amount ({R(thr)}) shall not be admitted/settled without a licensed surveyor's report (unless the Authority directs otherwise).",
     f"Claim {R(claimed)} ≥ {R(thr)} ⇒ report mandatory.",
     "Proviso: the insurer's right to settle at an amount different from the surveyor's assessment is not abridged."],
    "Report needed if claim ≥ threshold (regulations); settlement amount remains the insurer's call",
    "The threshold is tested on the claim; the surveyor assesses, the insurer decides.",
    ref=f"{INS}, s.64UM(2) and proviso (threshold given as data)")

notice, comm = date(2026, 1, 4), date(2026, 1, 29)
dl_ins, dl_app = notice + timedelta(30), comm + timedelta(30)
assert (dl_ins, dl_app) == (date(2026, 2, 3), date(2026, 2, 28))
add("INS_AN", "L2",
    f"Notice of an assignment of a life policy is received by the insurer on {fd(notice)}. The insurer believes the assignment is for "
    f"trading in policies, records its reasons and communicates its refusal on {fd(comm)}. Under s.38 of the Insurance Act, 1938:",
    f"The insurer had to communicate by {fd(dl_ins)}; the assignee may approach IRDAI by {fd(dl_app)}",
    [(f"The insurer had to communicate by {fd(notice+timedelta(45))}; the assignee may approach IRDAI by {fd(dl_app)}", "45-day appeal window used for the insurer's decision"),
     (f"The insurer had to communicate by {fd(dl_ins)}; the assignee may appeal to SAT by {fd(comm+timedelta(45))}", "wrong forum — s.110 SAT route used for an s.38 grievance"),
     (f"The insurer had to communicate by {fd(dl_ins)}; the assignee may approach IRDAI by {fd(dl_ins+timedelta(30))}", "appeal period counted from the insurer's deadline, not receipt of communication")],
    ["s.38(3)-(4): the insurer may decline to act on an assignment (e.g. not bona fide / trading in policies), recording reasons and communicating within 30 days of the notice.",
     f"{fd(notice)} + 30 days = {fd(dl_ins)}.",
     f"s.38(5): aggrieved person may prefer a claim to the Authority within 30 days of receipt of the communication: {fd(comm)} + 30 = {fd(dl_app)}."],
    "Insurer: notice + 30 days; grievance to IRDAI: communication + 30 days",
    "The first-level remedy against refusal to register an assignment is IRDAI, not SAT.",
    kind="numerical", ref=f"{INS}, s.38(3)-(5)")

# ---- L3 ----
add("INS_AN", "L3",
    "Consider the following statements under ss.38–39 of the Insurance Act, 1938:\n\n"
    "1. An assignment of a life policy to a bank as security for a housing loan automatically cancels an existing nomination.\n"
    "2. An assignment of the policy to the insurer itself against a policy loan within the surrender value also cancels the nomination.\n"
    "3. Where the nominees are the policyholder's parents, spouse or children, they are beneficially entitled to the amount unless it is proved that the holder could not have conferred such title.\n\n"
    "Which of the statements is/are correct?",
    "1 and 3 only",
    [("1 and 2 only", "treats a loan assignment to the insurer as cancelling nomination"),
     ("2 and 3 only", "misses the automatic cancellation on a third-party assignment"),
     ("1, 2 and 3", "misses the insurer-loan exception")],
    ["s.39: a transfer/assignment under s.38 automatically cancels a nomination (statement 1 true).",
     "Exception: assignment to the insurer bearing the risk, against a loan within surrender value, does not cancel the nomination; it affects the nominee only to the insurer's interest (statement 2 false).",
     "s.39(7): parents, spouse, children (or any of them) as nominees are beneficial nominees (statement 3 true)."],
    "Insurance Act s.39 (assignment cancels nomination; insurer-loan exception; beneficial nominees)",
    "The insurer-loan exception is the classic trap.",
    kind="statement", ref=f"{INS}, ss.38, 39")

c, w = ar(0)
add("INS_45", "L3",
    "**Assertion (A):** Six years after issue, an insurer may reduce the sum assured of a life policy on proof that the insured's age was understated in the proposal.\n\n"
    "**Reason (R):** Section 45 allows the insurer to call for proof of age at any time, and adjusting the policy terms on subsequent proof of incorrect age is not calling the policy in question.",
    c, w,
    ["s.45(1) bars questioning a policy on any ground after three years.",
     "s.45(5): nothing prevents calling for proof of age at any time; adjusting terms on proof of mis-stated age is not deemed calling the policy in question.",
     "So A is true and R is exactly why."],
    "Insurance Act s.45(5)", "Age adjustment is outside the three-year bar — it is not 'calling in question'.",
    kind="assertion-reason", ref=f"{INS}, s.45(5)")

add("INS_45", "L3",
    "Consider the following statements under s.64VB of the Insurance Act, 1938:\n\n"
    "1. Where the premium is sent by cheque by post, the risk may be assumed from the date on which the cheque is posted.\n"
    "2. A refund of premium on cancellation of a policy may be credited to the agent's account for onward payment to the insured.\n"
    "3. Premium collected by an agent must be deposited with, or despatched by post to, the insurer within 24 hours of collection, excluding bank and postal holidays.\n\n"
    "Which of the statements is/are correct?",
    "1 and 3 only",
    [("1 and 2 only", "accepts routing of refunds through the agent"),
     ("2 and 3 only", "rejects the posting-date rule for cheques"),
     ("3 only", "rejects the posting-date rule and needlessly doubts statement 1")],
    ["s.64VB(3): premium tendered by postal money order or cheque sent by post — risk may be assumed from the date the money order is booked or the cheque posted.",
     "s.64VB(4): agent-collected premium to be deposited/despatched within 24 hours, excluding bank and postal holidays.",
     "s.64VB(5): refunds are payable directly to the insured (crossed/order cheque or postal money order), not via the agent."],
    "Insurance Act s.64VB(3)-(5)", "Refunds go straight to the insured — never through the intermediary.",
    kind="statement", ref=f"{INS}, s.64VB")

pen_day, cap_new, cap_old = 1e5, 10e7, 1e7
dP, dQ = 64, 1090
pP, pQ = min(pen_day * dP, cap_new), min(pen_day * dQ, cap_new)
tot = pP + pQ
assert tot == 10.64e7
add("INS_PEN", "L3",
    f"Two insurers default in furnishing returns required by the Insurance Act, 1938: Insurer P for {dP} days and Insurer Q for {inr(dQ)} days "
    "(a long-pending filing). Applying s.102 as it stands after the 2025 amendment, the maximum aggregate penalty that can be imposed on the two is:",
    crore(tot),
    [(crore(min(pen_day*dP, cap_old) + min(pen_day*dQ, cap_old)), "pre-2025 ceiling of ₹1 crore applied"),
     (crore(pen_day * (dP + dQ)), "daily penalty applied without the ceiling"),
     (crore(cap_new), "ceiling applied once to the aggregate instead of per defaulter")],
    ["s.102 (2025): up to ₹1 lakh for each day the failure continues, subject to a maximum of ₹10 crore.",
     f"P: {dP} × ₹1 lakh = {crore(pP)} (below cap).",
     f"Q: {inr(dQ)} × ₹1 lakh = {crore(pen_day*dQ)} → capped at {crore(pQ)}.",
     f"Aggregate = {crore(tot)}."],
    "Penalty per defaulter = min(₹1 lakh × days, ₹10 crore)", "The ceiling is per defaulter; the old ₹1 crore ceiling no longer applies.",
    kind="numerical", ref=f"{INS}, s.102" + AMD25)

mp = {"A": 3, "B": 1, "C": 4, "D": 2}
add("INS_REG", "L3",
    "Match the section of the Insurance Act, 1938 with its subject:\n\n"
    "| Section | Subject |\n|---|---|\n| A. s.2CB | 1. Requirement of a certificate of registration to begin insurance business |\n"
    "| B. s.3 | 2. No risk to be assumed unless premium is received in advance |\n"
    "| C. s.27E | 3. Property in India not to be insured with a foreign insurer without permission |\n"
    "| D. s.64VB | 4. Prohibition on investing policyholders' funds outside India |",
    perm(mp),
    [(perm({"A": 1, "B": 3, "C": 4, "D": 2}), "swaps registration and foreign-insurer provisions"),
     (perm({"A": 3, "B": 1, "C": 2, "D": 4}), "swaps investment and premium provisions"),
     (perm({"A": 4, "B": 1, "C": 3, "D": 2}), "swaps the two 'outside India' provisions")],
    ["s.2CB — foreign insurer for Indian property only with permission.", "s.3 — certificate of registration.",
     "s.27E — no investment of policyholders' funds outside India.", "s.64VB — premium in advance."],
    "Section ↔ subject mapping", "s.2CB and s.27E both involve 'outside India' — one is about the insurer, the other about investments.",
    kind="match", ref=f"{INS}, ss.2CB, 3, 27E, 64VB")

add("INS_INV", "L3",
    "Consider the following statements under the Insurance Act, 1938 as it stands in 2026:\n\n"
    "1. The Authority may specify limits on commission, remuneration or reward payable to insurance agents and insurance intermediaries.\n"
    "2. No person shall offer, as an inducement to take out or renew a policy, a rebate of the whole or part of the commission or premium.\n"
    "3. An agent who accepts commission on a policy taken out on his own life is deemed to have allowed a prohibited rebate.\n\n"
    "Which of the statements is/are correct?",
    "1 and 2 only",
    [("2 and 3 only", "denies the Authority's power over commission limits"),
     ("1 and 3 only", "treats own-policy commission as a rebate and drops the rebate bar"),
     ("1, 2 and 3", "misses the own-policy carve-out in s.41")],
    ["s.40 (as amended 2025): the Authority may specify limits on commission/remuneration/reward to agents and intermediaries.",
     "s.41(1): prohibition of rebates as an inducement.",
     "s.41 proviso/explanation: an agent's commission on a policy taken out by himself (own life, and after 2025 own health or property) is not a rebate."],
    "Insurance Act ss.40, 41", "The self-policy carve-out keeps an agent's own commission outside the rebate bar.",
    kind="statement", ref=f"{INS}, ss.40, 41" + AMD25)

claims = [("A", 48000, False), ("B", 50000, False), ("C", 120000, False), ("D", 85000, True)]
need = [k for k, v, d in claims if v >= thr and not d]
assert need == ["B", "C"]
rows = "\n".join(f"| {k} | {R(v)} | {'Yes' if d else 'No'} |" for k, v, d in claims)
add("INS_PEN", "L3",
    f"Assume the threshold specified by regulations under s.64UM(2) of the Insurance Act, 1938 is {R(thr)}. Four general insurance claims arising in India are pending:\n\n"
    f"| Claim | Amount claimed | Authority has directed otherwise for this claim? |\n|---|---:|---|\n{rows}\n\n"
    "For which claims is a report from a licensed surveyor and loss assessor a pre-condition to admission?",
    "B and C only",
    [("C only", "reads 'equal to or exceeding' as 'exceeding'"),
     ("B, C and D", "ignores the 'unless otherwise directed by the Authority' carve-out"),
     ("A, B and C", "applies the requirement irrespective of the threshold")],
    [f"Report needed where claim ≥ {R(thr)} unless the Authority directs otherwise.",
     f"A {R(48000)} < threshold; B = threshold (equal to ⇒ covered); C above; D above but Authority has directed otherwise.",
     "Hence B and C."],
    "Surveyor report if claim ≥ threshold and no contrary direction of the Authority",
    "‘Equal to or exceeding’ catches the boundary claim B.",
    kind="statement", ref=f"{INS}, s.64UM(2) (threshold given as data)")

# ---- L4 case: Meera's policy (4) ----
G1 = "ACTI-CASE-INS-MEERA"
pd_iss = date(2022, 2, 18)
pd_rev = date(2024, 9, 10)
prem_m = 36500
case_ins = (
    "**Case.** Meera took a life policy on her own life. Proposal signed 2 February 2022; policy issued and risk commenced "
    f"{fd(pd_iss)}; annual premium {R(prem_m)} due every 18 February. She paid the 2022 and 2023 premiums, let the policy lapse, "
    f"and revived it on {fd(pd_rev)} by paying the 2024 premium in arrears; she then paid the 2025 and 2026 premiums on time. "
    "She had nominated her husband Arjun and her mother in equal shares. On 1 July 2025 she executed an absolute assignment of the "
    "policy in favour of Kaveri Finance Ltd (a third-party NBFC) as security for a business loan; the insurer registered it. "
    "Meera died on 20 March 2026. While processing the claim, the insurer found that she had not disclosed her diabetes in the "
    "revival declaration; fraud is not alleged.\n\n")
add("INS_45", "L4", case_ins + "Up to which date may the insurer call the policy in question under s.45?",
    fd(add_years(pd_rev, 3)),
    [(fd(add_years(pd_iss, 3)), "reckoned from issue, ignoring revival"),
     (fd(add_years(pd_rev, 2)), "pre-2015 two-year period"),
     (fd(add_years(date(2022, 2, 2), 3)), "reckoned from the proposal date")],
    [f"Reference date = later of issue ({fd(pd_iss)}) and revival ({fd(pd_rev)}) = {fd(pd_rev)}.",
     f"Three years ⇒ {fd(add_years(pd_rev, 3))}."],
    "Reference date = latest of issue / risk / revival / rider; + 3 years",
    "Revival resets the clock; the proposal date is never the reference.",
    kind="case", group=G1, ref=f"{INS}, s.45(1)")

rep = date(2026, 5, 15)
n_prem = 5
ref_amt = prem_m * n_prem
due = rep + timedelta(90)
assert (ref_amt, due) == (182500, date(2026, 8, 13))
add("INS_45", "L4", case_ins + f"If the insurer repudiates on {fd(rep)} for the non-disclosure, it must pay:",
    f"{R(ref_amt)} by {fd(due)}",
    [(f"{R(ref_amt)} by {fd(rep+timedelta(30))}", "30-day window instead of 90"),
     (f"{R(prem_m*4)} by {fd(due)}", "omits the arrear premium paid at revival"),
     (f"{R(prem_m*2)} by {fd(due)}", "counts only premiums paid after revival on due dates")],
    ["Non-fraud repudiation within three years ⇒ premiums collected till repudiation are payable within 90 days (s.45(4)).",
     f"Premiums collected: 2022, 2023, 2024 (arrear at revival), 2025, 2026 = {n_prem} × {R(prem_m)} = {R(ref_amt)}.",
     f"{fd(rep)} + 90 days = {fd(due)}."],
    "Refund = Σ premiums collected; due within 90 days of repudiation",
    "The arrear premium paid on revival is still a premium collected.",
    kind="case", group=G1, ref=f"{INS}, s.45(4)")

add("INS_AN", "L4", case_ins + "Assuming the claim is admitted, who is entitled to receive the policy money?",
    "Kaveri Finance Ltd, as the assignment cancelled the nomination",
    [("Arjun and her mother equally, as beneficial nominees", "ignores automatic cancellation on assignment"),
     ("Arjun and her mother, subject only to a lien of Kaveri Finance", "treats an absolute assignment as a mere charge"),
     ("Meera's legal heirs, since both nomination and assignment lapse on death", "invents lapse of assignment on death")],
    ["s.39: an assignment under s.38 automatically cancels a nomination (the insurer-loan exception does not apply — Kaveri is a third party).",
     "Absolute assignment vests all rights in the assignee; the claim is payable to Kaveri Finance."],
    "Insurance Act ss.38–39", "Beneficial-nominee status cannot survive a cancelled nomination.",
    kind="case", group=G1, ref=f"{INS}, ss.38, 39")

sa, loan, intr = 1000000, 60000, 4800
each = (sa - loan - intr) / 2
assert each == 467600
add("INS_AN", "L4", case_ins + f"Suppose instead there was no assignment to Kaveri Finance, but Meera had assigned the policy to the insurer itself against a policy loan of {R(loan)} "
    f"(within surrender value), with {R(intr)} interest outstanding at death. The death claim is {R(sa)}. Each nominee receives:",
    R(each),
    [(R(sa / 2), "loan and interest ignored — nominee rights treated as unaffected"),
     (R((sa - loan) / 2), "only loan principal deducted"),
     (R((sa - loan - intr)), "whole amount to one nominee — equal shares ignored")],
    ["Assignment to the insurer against a loan within surrender value does not cancel the nomination; it affects nominees only to the insurer's interest.",
     f"Net = {R(sa)} − {R(loan)} − {R(intr)} = {R(sa-loan-intr)}; spouse and mother are beneficial nominees in equal shares.",
     f"Each = {R(each)}."],
    "Nominee share = (Claim − insurer's loan interest) ÷ number of equal-share nominees",
    "The insurer-loan exception keeps the nomination alive but carves out the insurer's dues.",
    kind="case", group=G1, ref=f"{INS}, s.39")

# =====================================================================================
# IRDA ACT, 1999  (20)  L1 4 · L2 6 · L3 6 · L4 4
# =====================================================================================
add("IR_EST", "L1",
    "Under s.4 of the Insurance Regulatory and Development Authority Act, 1999, IRDAI consists of:",
    "A Chairperson, not more than five whole-time members and not more than four part-time members",
    [("A Chairperson and not more than six members, of whom at least three are whole-time", "PFRDA Act composition"),
     ("A Chairperson, four regulator nominees, two Finance Ministry officials and two other members", "IFSCA Act composition"),
     ("A Chairperson, not more than four whole-time members and not more than five part-time members", "whole-time and part-time ceilings swapped")],
    ["s.4: Chairperson; not more than five whole-time members; not more than four part-time members — appointed by the Central Government."],
    "IRDA Act s.4: 1 + ≤5 WTM + ≤4 PTM", "Keep the three regulators' compositions apart: IRDAI 1+5+4, PFRDA 1+6(≥3 WTM), IFSCA 1+4+2+2.",
    ref=f"{IRA}, s.4")

add("IR_FN", "L1",
    "Which category of dispute does s.14(2) of the IRDA Act, 1999 expressly empower IRDAI to adjudicate?",
    "Disputes between insurers and intermediaries or insurance intermediaries",
    [("Disputes between insurers and policyholders over claim quantum", "those go to the Insurance Ombudsman / consumer fora"),
     ("Disputes between intermediaries and subscribers", "PFRDA Act s.14 wording"),
     ("Disputes between two claimants over the validity of a nomination", "civil-court matter")],
    ["s.14(2)(m): adjudication of disputes between insurers and intermediaries or insurance intermediaries."],
    "IRDA Act s.14(2)(m)", "IRDAI does not adjudicate policyholder claim disputes under s.14.",
    ref=f"{IRA}, s.14(2)(m)")

add("IR_CG", "L1",
    "Under s.19 of the IRDA Act, 1999, the Central Government may supersede IRDAI for a period not exceeding:",
    "Six months",
    [("One year", "invented longer period"), ("Three months", "invented shorter period"),
     ("Until reconstitution, with no outer limit", "ignores the statutory cap")],
    ["s.19(1): supersession by notification for such period, not exceeding six months, as may be specified."],
    "IRDA Act s.19", "Six months is common to IRDAI, PFRDA and IFSCA supersession provisions.",
    ref=f"{IRA}, s.19")

add("IR_FUND", "L1",
    "After the 2025 amendments to the IRDA Act, 1999, sums realised by way of penalties by IRDAI are credited to:",
    "The Policyholders' Education and Protection Fund",
    [("The Insurance Regulatory and Development Authority Fund", "confuses the operating fund with the penalty fund"),
     ("The Subscriber Education and Protection Fund", "PFRDA Act s.41 fund"),
     ("The Consolidated Fund of India directly", "IFSCA Act s.13(6) treatment of penalties")],
    ["s.16A (inserted 2025): the Authority constitutes a Policyholders' Education and Protection Fund, credited inter alia with sums realised by way of penalties."],
    "IRDA Act s.16A", "Each regulator's penalty destination differs: IRDAI → PEPF, PFRDA → SEPF, IFSCA → CFI.",
    ref=f"{IRA}, s.16A" + AMD25)

dob, appt = date(1965, 3, 14), date(2026, 6, 1)
end = min(add_years(appt, 5), add_years(dob, 65))
assert end == date(2030, 3, 14)
add("IR_EST", "L2",
    f"A whole-time member of IRDAI, born on {fd(dob)}, enters office on {fd(appt)}. Under s.5 of the IRDA Act, 1999 as amended in 2025, she holds office until:",
    fd(end),
    [(fd(add_years(dob, 62)), "pre-2025 age limit of 62 for whole-time members"),
     (fd(add_years(appt, 5)), "five-year term applied, age limit ignored"),
     (fd(add_years(appt, 3)), "IFSCA Act three-year term")],
    ["s.5 (2025): Chairperson and whole-time members — five years or until age 65, whichever is earlier.",
     f"5 years → {fd(add_years(appt, 5))}; age 65 → {fd(add_years(dob, 65))}.",
     f"Earlier = {fd(end)}."],
    "Tenure end = min(entry + 5 years, 65th birthday)", "The 62-year WTM cap was removed in 2025 for IRDAI (it survives in the PFRDA and IFSCA Acts).",
    kind="numerical", ref=f"{IRA}, s.5" + AMD25)

cease = date(2026, 9, 30)
cool = add_years(cease, 2)
opts = [("Director on the board of a private general insurer from 1 August 2028", date(2028, 8, 1), True, None),
        ("Secretary in a State Government department from 1 November 2028", date(2028, 11, 1), False, "cooling-off already over"),
        ("Professor at a private university from 1 December 2026", date(2026, 12, 1), False, "not government or insurance-sector employment"),
        ("Director on the board of a private general insurer from 1 October 2028", date(2028, 10, 1), False, "cooling-off already over")]
assert opts[0][1] < cool and opts[1][1] > cool and opts[3][1] > cool
add("IR_EST", "L2",
    f"The Chairperson of IRDAI ceases to hold office on {fd(cease)}. Which of the following proposed engagements requires the previous approval of the Central Government?",
    opts[0][0], [(o[0], o[3]) for o in opts[1:]],
    ["s.8: Chairperson and whole-time members shall not, for two years from ceasing to hold office, accept employment under the Central or a State Government or in any company in the insurance sector without previous approval.",
     f"Cooling-off runs to {fd(cool)}.",
     "Only the insurer directorship from 1 August 2028 falls inside the window."],
    "Cooling-off = 2 years from cessation; covers Government and insurance-sector employment",
    "Check both the date and the nature of the engagement.",
    ref=f"{IRA}, s.8")

add("IR_FN", "L2",
    "Which of the following is NOT among the powers and functions of IRDAI listed in s.14(2) of the IRDA Act, 1999?",
    "Regulating pension funds under the National Pension System",
    [("Specifying the code of conduct for surveyors and loss assessors", "is s.14(2)(d)"),
     ("Regulating the investment of funds by insurance companies", "is s.14(2)(k)"),
     ("Regulating maintenance of margin of solvency", "is s.14(2)(l)")],
    ["s.14(2) includes registration, policyholder protection, surveyors' code (d), investments (k), solvency margin (l), dispute adjudication (m), etc.",
     "NPS pension funds are regulated by PFRDA under the PFRDA Act, 2013."],
    "IRDA Act s.14(2)", "Annuity at NPS exit is bought from a life insurer, but the pension fund itself is PFRDA's domain.",
    ref=f"{IRA}, s.14(2)")

add("IR_CG", "L2",
    "The Central Government issues a written direction to IRDAI naming the software vendor IRDAI must use for its internal staff-leave system, "
    "and itself describes the matter as administrative. Under s.18 of the IRDA Act, 1999:",
    "Not binding under s.18, which excludes technical and administrative matters",
    [("IRDAI is bound, as every written direction of the Central Government binds it", "ignores the technical/administrative carve-out"),
     ("IRDAI is bound once the direction is laid before both Houses of Parliament", "invents a laying requirement"),
     ("IRDAI is bound after being given an opportunity to express its views", "applies the policy-direction procedure to a non-policy matter")],
    ["s.18(1): IRDAI is bound by directions on questions of policy, other than those relating to technical and administrative matters.",
     "The Government itself treats this as administrative, so the s.18 binding force does not attach."],
    "IRDA Act s.18", "Policy directions bind; technical/administrative ones are carved out.",
    ref=f"{IRA}, s.18")

sur, rf_open = 480, 1050
exp3 = [380, 410, 420]
cap = sum(exp3)
tr = min(0.25 * sur, cap - rf_open)
cfi = sur - tr
assert (tr, cfi) == (120, 360)
add("IR_FUND", "L2",
    f"Under s.16 of the IRDA Act, 1999 (as amended in 2025), 25% of the annual surplus of the IRDA Fund goes to a Reserve Fund, the Reserve Fund being "
    "capped at the total annual expenditure of the preceding three financial years; the balance surplus goes to the Consolidated Fund of India. For a year:\n\n"
    f"| Item | ₹ crore |\n|---|---:|\n| Annual surplus | {sur} |\n| Reserve Fund balance at start | {inr(rf_open)} |\n"
    f"| Expenditure of preceding 3 years | {exp3[0]}, {exp3[1]}, {exp3[2]} |\n\nThe transfers are:",
    f"₹{tr:.0f} crore to Reserve Fund; ₹{cfi:.0f} crore to Consolidated Fund of India",
    [(f"₹{cap-rf_open:.0f} crore to Reserve Fund; ₹{sur-(cap-rf_open):.0f} crore to Consolidated Fund of India", "fills the headroom instead of transferring 25%"),
     (f"₹{cfi:.0f} crore to Reserve Fund; ₹{tr:.0f} crore to Consolidated Fund of India", "shares reversed"),
     (f"₹{tr:.0f} crore to Reserve Fund; ₹{sur:.0f} crore to Consolidated Fund of India", "surplus not reduced by the reserve transfer")],
    [f"25% of {sur} = {0.25*sur:.0f}; headroom = {cap} − {rf_open} = {cap-rf_open}.",
     f"Transfer = min({0.25*sur:.0f}, {cap-rf_open}) = {tr:.0f}.",
     f"Balance to CFI = {sur} − {tr:.0f} = {cfi:.0f}."],
    "Reserve transfer = min(25% × surplus, cap − opening reserve); CFI = surplus − transfer",
    "The cap only bites when headroom is below 25% of surplus.",
    kind="numerical", ref=f"{IRA}, s.16(3)-(4)" + AMD25)

add("IR_FN", "L2",
    "A general insurer contravenes a regulation made by IRDAI under the IRDA Act, 1999 itself (not under the Insurance Act). After the 2025 amendments, IRDAI's power to impose a monetary penalty for this:",
    "Flows from s.14(2)(n), applying the s.102 Insurance Act penalty",
    [("Does not exist; penalties lie only for breaches of the Insurance Act", "pre-2025 gap assumed to persist"),
     ("Must be exercised by the Central Government on IRDAI's recommendation", "wrong authority"),
     ("Lies with the Securities Appellate Tribunal on a reference by IRDAI", "confuses appellate forum with penalising authority")],
    ["s.14(2)(n) (2025): imposing such penalty as specified in s.102 of the Insurance Act for any violation of the IRDA Act or rules/regulations made under it."],
    "IRDA Act s.14(2)(n) read with Insurance Act s.102", "SAT hears appeals; it does not impose first-instance penalties.",
    ref=f"{IRA}, s.14(2)(n)" + AMD25)

# ---- L3 ----
add("IR_EST", "L3",
    "Consider the following statements about IRDAI members under the IRDA Act, 1999 (as amended in 2025):\n\n"
    "1. A part-time member holds office for a term not exceeding five years.\n"
    "2. A member may be removed on the ground that he has abused his position, without being given an opportunity of being heard.\n"
    "3. Both the Chairperson and whole-time members may hold office until the age of 65, subject to the five-year term.\n\n"
    "Which of the statements is/are correct?",
    "1 and 3 only",
    [("1 and 2 only", "overlooks the hearing requirement for removal on abuse/financial-interest grounds"),
     ("3 only", "doubts the five-year cap for part-time members"),
     ("1, 2 and 3", "overlooks the hearing requirement")],
    ["s.5: part-time member — term not exceeding five years (1 true).",
     "s.6: removal for acquiring prejudicial financial interest or abuse of position only after reasonable opportunity of being heard (2 false).",
     "s.5 (2025): Chairperson and WTMs — five years or 65, whichever earlier (3 true)."],
    "IRDA Act ss.5, 6", "Natural justice is built into the last two removal grounds.",
    kind="statement", ref=f"{IRA}, ss.5, 6" + AMD25)

mp = {"A": 2, "B": 4, "C": 1, "D": 3}
add("IR_FN", "L3",
    "Match the matter with the provision that governs it:\n\n"
    "| Matter | Provision |\n|---|---|\n| A. IRDAI adjudicates a dispute between an insurer and a broker | 1. IRDA Act, s.19 |\n"
    "| B. A policyholder changes the nominee under her policy | 2. IRDA Act, s.14(2)(m) |\n"
    "| C. The Central Government supersedes IRDAI | 3. Insurance Act, s.110 |\n"
    "| D. A broker appeals against IRDAI's penalty order | 4. Insurance Act, s.39 |",
    perm(mp),
    [(perm({"A": 2, "B": 4, "C": 3, "D": 1}), "swaps supersession with the appeal provision"),
     (perm({"A": 4, "B": 2, "C": 1, "D": 3}), "swaps dispute adjudication with nomination"),
     (perm({"A": 3, "B": 4, "C": 1, "D": 2}), "treats adjudication as an appeal")],
    ["Dispute insurer–intermediary: IRDA Act s.14(2)(m).", "Nomination: Insurance Act s.39.",
     "Supersession: IRDA Act s.19.", "Appeal to SAT: Insurance Act s.110."],
    "IRDA Act (institutional) vs Insurance Act (operational) provisions",
    "The IRDA Act sets up and empowers the regulator; policy-level rights and SAT appeals sit in the Insurance Act.",
    kind="match", ref=f"{IRA}, ss.14, 19; {INS}, ss.39, 110")

add("IR_CG", "L3",
    "The Central Government is considering superseding IRDAI for persistent default in complying with its directions. Consider:\n\n"
    "1. The notification cannot specify a supersession period exceeding six months.\n"
    "2. During supersession, IRDAI's powers are exercised by such person or persons as the Central Government directs.\n"
    "3. Members who vacate office on supersession are disqualified from reappointment on reconstitution.\n"
    "4. A copy of the notification and a full report of the action are to be laid before each House of Parliament.\n\n"
    "Which of the statements are correct?",
    "1, 2 and 4 only",
    [("1, 2 and 3 only", "invents disqualification of superseded members"),
     ("1 and 2 only", "misses parliamentary laying"),
     ("2, 3 and 4 only", "denies the six-month ceiling")],
    ["s.19: supersession up to six months; members vacate; powers exercised by person(s) the Central Government directs.",
     "Before expiry the Authority is reconstituted; members who vacated are not disqualified from reappointment.",
     "Notification and full report are laid before each House of Parliament."],
    "IRDA Act s.19", "Supersession is temporary and does not blacklist former members.",
    kind="statement", ref=f"{IRA}, s.19")

add("IR_FUND", "L3",
    "Consider the following statements about the IRDA Fund under s.16 of the IRDA Act, 1999 (as amended in 2025):\n\n"
    "1. The Fund is credited with Government grants and the fees and charges received by the Authority.\n"
    "2. The Fund may be applied to capital expenditure in accordance with an annual capital expenditure plan approved by the Authority.\n"
    "3. Penalties realised by the Authority are credited to the Fund and applied towards staff salaries.\n\n"
    "Which of the statements is/are correct?",
    "1 and 2 only",
    [("1, 2 and 3", "routes penalties into the operating fund"),
     ("1 and 3 only", "misses the 2025 capital-expenditure head; routes penalties to the Fund"),
     ("2 and 3 only", "misses the fees-and-charges credit")],
    ["s.16(1): grants, fees and charges and other approved sums credited.",
     "s.16(2)(c) (2025): capital expenditure per approved annual plan.",
     "Penalties go to the Policyholders' Education and Protection Fund (s.16A), not to s.16."],
    "IRDA Act ss.16, 16A", "Keep penalty money away from the regulator's own salary fund.",
    kind="statement", ref=f"{IRA}, ss.16, 16A" + AMD25)

c, w = ar(3)
add("IR_FN", "L3",
    "**Assertion (A):** IRDAI's power under s.14(2)(i) of the IRDA Act, 1999 to control and regulate rates, advantages, terms and conditions extends to life insurance premium rates.\n\n"
    "**Reason (R):** Section 14(2)(i) speaks of rates, advantages, terms and conditions that may be offered by insurers in respect of general insurance business.",
    c, w,
    ["s.14(2)(i) is confined to general insurance business — so A is false.",
     "R correctly states the scope of the clause."],
    "IRDA Act s.14(2)(i)", "Rate control under clause (i) is a general-insurance power.",
    kind="assertion-reason", ref=f"{IRA}, s.14(2)(i)")

exo = 1 + 5 + 4
mx = 25 + exo
assert mx == 35
add("IR_CG", "L3",
    "IRDAI is at its full statutory strength. It constitutes the Insurance Advisory Committee under s.25 of the IRDA Act, 1999 with the maximum permissible "
    "number of other members. The total membership of the Committee, counting ex officio members, is:",
    str(mx),
    [("25", "treats the 25 ceiling as including ex officio members"),
     (str(25 + 1 + 5), "counts only the Chairperson and whole-time members as ex officio"),
     (str(25 + 1 + 6), "uses PFRDA's 1 + 6 authority strength")],
    ["s.25: not more than 25 members excluding ex officio members.",
     f"Chairperson and members of IRDAI are ex officio: 1 + 5 + 4 = {exo}.",
     f"Maximum total = 25 + {exo} = {mx}."],
    "Max IAC = 25 + (Chairperson + ≤5 WTM + ≤4 PTM)", "All members of the Authority — including part-time — sit ex officio.",
    kind="numerical", ref=f"{IRA}, ss.4, 25")

# ---- L4 case: Authority's year-end (4) ----
G2 = "ACTI-CASE-IRDA-YEAREND"
fees, oth, sal, oexp, capex, pens = 1340, 60, 310, 240, 90, 75
rf0, e3 = 1020, [330, 360, 390]
surplus = fees + oth - (sal + oexp + capex)
assert surplus == 760
case_ir = (
    "**Case.** For FY 2026-27 IRDAI's accounts (illustrative figures, ₹ crore) show: fees and charges received "
    f"{inr(fees)}; other receipts approved by the Central Government {oth}; salaries and allowances {sal}; other revenue expenses {oexp}; "
    f"capital expenditure under the approved annual capex plan {capex}; penalties realised during the year {pens}. The Reserve Fund stood at "
    f"{inr(rf0)} at the start of the year; annual expenditure in the three preceding years was {e3[0]}, {e3[1]} and {e3[2]}. Under s.16 as amended "
    "in 2025, 25% of the annual surplus goes to the Reserve Fund (capped at the preceding three years' total annual expenditure) and the remaining surplus "
    "to the Consolidated Fund of India.\n\n")
add("IR_FUND", "L4", case_ir + "The annual surplus of the IRDA Fund for the year is:",
    f"₹{surplus} crore",
    [(f"₹{surplus+pens} crore", "penalties treated as Fund receipts"),
     (f"₹{surplus+capex} crore", "capital expenditure not charged to the Fund"),
     (f"₹{surplus+pens+capex} crore", "both errors — penalties included and capex excluded")],
    [f"Credits: fees {fees} + other {oth} = {fees+oth} (penalties go to s.16A PEPF).",
     f"Applications: {sal} + {oexp} + {capex} = {sal+oexp+capex}.",
     f"Surplus = {fees+oth} − {sal+oexp+capex} = {surplus}."],
    "Surplus = (grants + fees + other approved receipts) − (salaries + other expenses + approved capex)",
    "Penalties never enter the s.16 Fund after 2025.",
    kind="case", group=G2, ref=f"{IRA}, ss.16, 16A" + AMD25)

cap2 = sum(e3)
tr2 = min(0.25 * surplus, cap2 - rf0)
assert (cap2, tr2) == (1080, 60)
add("IR_FUND", "L4", case_ir + "The amounts transferred to the Reserve Fund and to the Consolidated Fund of India are:",
    f"₹{tr2:.0f} crore and ₹{surplus-tr2:.0f} crore",
    [(f"₹{0.25*surplus:.0f} crore and ₹{surplus-0.25*surplus:.0f} crore", "cap ignored"),
     (f"₹{tr2:.0f} crore and ₹{surplus-tr2+pens:.0f} crore", "penalties also remitted to CFI"),
     (f"₹{0.25*(surplus+pens):.0f} crore and ₹{surplus+pens-0.25*(surplus+pens):.0f} crore", "penalties in surplus and cap ignored")],
    [f"25% × {surplus} = {0.25*surplus:.0f}; cap = {cap2}; headroom = {cap2} − {rf0} = {cap2-rf0}.",
     f"Transfer = min({0.25*surplus:.0f}, {cap2-rf0}) = {tr2:.0f}; CFI = {surplus} − {tr2:.0f} = {surplus-tr2:.0f}."],
    "Reserve = min(25% × surplus, cap − opening reserve)", "Here the cap binds — only the headroom can go to the Reserve Fund.",
    kind="case", group=G2, ref=f"{IRA}, s.16(3)-(4)" + AMD25)

bd = 30
add("IR_FN", "L4", case_ir + f"During the year a broker failed for {bd} days to furnish a return required under IRDAI regulations. The maximum penalty and its destination are:",
    f"{lakh(bd*1e5,0)}, credited to the Policyholders' Education and Protection Fund",
    [(f"{lakh(bd*1e5,0)}, credited to the IRDA Fund", "penalty routed to the operating fund"),
     (f"{lakh(bd*1e5,0)}, credited to the Consolidated Fund of India", "IFSCA-style routing"),
     ("₹1 crore, credited to the Policyholders' Education and Protection Fund", "old ceiling read as a fixed penalty")],
    ["s.14(2)(n) IRDA Act applies s.102 Insurance Act: up to ₹1 lakh per day (max ₹10 crore).",
     f"{bd} × ₹1 lakh = {lakh(bd*1e5,0)} (below cap).",
     "Penalties realised → PEPF under s.16A."],
    "Penalty = min(₹1 lakh × days, ₹10 crore); destination s.16A PEPF",
    "Daily penalty × days, not the ceiling.",
    kind="case", group=G2, ref=f"{IRA}, ss.14(2)(n), 16A; {INS}, s.102" + AMD25)

fy_end = date(2027, 3, 31)
rep_dl = add_months(fy_end.replace(day=1), 9 + 1) - timedelta(1)   # 31 Dec 2027
assert rep_dl == date(2027, 12, 31)
add("IR_FUND", "L4", case_ir + "The annual report of IRDAI's activities for FY 2026-27 and the audit of its accounts are governed as follows:",
    f"Report to the Central Government by {fd(rep_dl)}; accounts audited by the CAG",
    [(f"Report to the Central Government by {fd(fy_end+timedelta(90))}; accounts audited by the CAG", "IFSCA's 90-day timeline"),
     (f"Report to the Central Government by {fd(rep_dl)}; accounts audited by a CA firm the Government appoints", "wrong auditor"),
     (f"Report to the Central Government by 30 September 2027; accounts audited by the CAG", "six-month timeline invented")],
    ["s.20(2): report within nine months after the close of each financial year → 31 December 2027.",
     "s.17: accounts audited by the Comptroller and Auditor-General; report laid before Parliament."],
    "IRDAI report: FY end + 9 months; CAG audit", "IRDAI 9 months vs IFSCA 90 days — a favourite contrast.",
    kind="case", group=G2, ref=f"{IRA}, ss.17, 20")

# =====================================================================================
# PFRDA ACT, 2013  (24)  L1 5 · L2 7 · L3 7 · L4 5
# =====================================================================================
add("PF_CON", "L1",
    "Under s.4 of the PFRDA Act, 2013, the Authority consists of:",
    "A Chairperson and not more than six members, of whom at least three are whole-time members",
    [("A Chairperson, not more than five whole-time and not more than four part-time members", "IRDA Act composition"),
     ("A Chairperson, one nominee each of RBI, SEBI, IRDAI and PFRDA and four others", "IFSCA-style composition"),
     ("A Chairperson and not more than six members, of whom at least three are part-time members", "whole-time/part-time reversed")],
    ["s.4: Chairperson and not more than six members, of whom at least three shall be whole-time, appointed by the Central Government;",
     "with at least one person from each of economics, finance and law."],
    "PFRDA Act s.4", "‘At least three whole-time’ — not ‘at least three part-time’.",
    ref=f"{PFA}, s.4")

add("PF_NPS", "L1",
    "Section 25 of the PFRDA Act, 2013 provides that a pension fund:",
    "Shall not, directly or indirectly, invest the funds of subscribers outside India",
    [("May invest up to 26% of subscribers' funds outside India", "confuses the s.24 foreign-shareholding cap with an investment limit"),
     ("May invest outside India with the approval of the Reserve Bank", "invents an RBI approval route"),
     ("Shall invest at least 26% of subscribers' funds in Government securities", "invented mandate")],
    ["s.25: no pension fund shall directly or indirectly invest outside India the funds of subscribers.",
     "Parallel: Insurance Act s.27E for policyholders' funds."],
    "PFRDA Act s.25", "26% is about foreign ownership of the pension fund (s.24), not where it invests.",
    ref=f"{PFA}, s.25")

add("PF_APP", "L1",
    "An appeal against an order of PFRDA or its adjudicating officer lies to:",
    "The Securities Appellate Tribunal, within 45 days of receipt of the order",
    [("The Securities Appellate Tribunal, within 60 days of receipt of the order", "Supreme Court appeal window used"),
     ("The Pension Ombudsman, within 30 days of the order", "invented forum"),
     ("The High Court having jurisdiction, within 45 days", "wrong forum")],
    ["s.36: appeal to SAT within forty-five days from receipt of the order; SAT may condone delay for sufficient cause and should endeavour to dispose within six months."],
    "PFRDA Act s.36", "Same forum and window as insurance appeals.",
    ref=f"{PFA}, s.36")

add("PF_FN", "L1",
    "Which of the following falls OUTSIDE the application of the PFRDA Act, 2013 under s.12?",
    "Schemes under the Employees' Provident Funds and Miscellaneous Provisions Act, 1952",
    [("The NPS applicable to Central Government employees appointed on or after 1 January 2004", "NPS is the Act's core coverage"),
     ("A pension scheme not regulated by any other enactment", "expressly covered by s.12"),
     ("NPS extended by a State Government to its employees by notification", "covered on notification")],
    ["s.12: the Act applies to the NPS and to any other pension scheme not regulated by any other enactment.",
     "It does not apply to schemes under the EPF & MP Act, 1952 (and other listed provident-fund enactments)."],
    "PFRDA Act s.12", "EPFO-administered schemes have their own statute.",
    ref=f"{PFA}, s.12")

add("PF_NPS", "L1",
    "Under s.23 of the PFRDA Act, 2013, among the pension funds registered by the Authority:",
    "At least one shall be a Government company",
    [("At least one shall be a subsidiary of a scheduled bank", "invented ownership condition"),
     ("None may have any foreign shareholding", "contradicts s.24"),
     ("At least one shall be a life insurance company", "confuses annuity service providers with pension funds")],
    ["s.23: the Authority may register pension funds; at least one of them shall be a Government company."],
    "PFRDA Act s.23", "Life insurers supply annuities at exit — they are not the statutory 'Government company' pension fund.",
    ref=f"{PFA}, s.23")

# ---- L2 ----
dob, appt = date(1965, 7, 20), date(2025, 10, 1)
end = min(add_years(appt, 5), add_years(dob, 62))
assert end == date(2027, 7, 20)
add("PF_CON", "L2",
    f"A whole-time member of PFRDA, born on {fd(dob)}, enters office on {fd(appt)}. Under s.5 of the PFRDA Act, 2013, he holds office until:",
    fd(end),
    [(fd(add_years(dob, 65)), "65-year limit (Chairperson / amended IRDA rule) applied to a WTM"),
     (fd(add_years(appt, 5)), "five-year term applied, age limit ignored"),
     (fd(add_years(appt, 3)), "IFSCA's three-year term")],
    ["s.5: Chairperson and whole-time members — five years; no Chairperson beyond 65, no whole-time member beyond 62.",
     f"5 years → {fd(add_years(appt,5))}; age 62 → {fd(add_years(dob,62))}.",
     f"Earlier = {fd(end)}."],
    "WTM tenure end = min(entry + 5 years, 62nd birthday)", "PFRDA still has the 62 cap for WTMs.",
    kind="numerical", ref=f"{PFA}, s.5")

own, emp, gains = 784000, 784000, 512000
capw = 0.25 * own
assert capw == 196000
add("PF_NPS", "L2",
    f"An NPS subscriber's account shows own contributions {R(own)}, employer contributions {R(emp)} and accumulated returns {R(gains)}. "
    "Under s.20(2)(b) of the PFRDA Act, 2013, the ceiling on partial withdrawal (before any regulatory conditions) is:",
    R(capw),
    [(R(0.25 * (own + emp)), "employer contributions included in the base"),
     (R(0.25 * (own + emp + gains)), "25% of total corpus"),
     (R(0.25 * (own + gains)), "returns added to own contributions")],
    ["s.20(2)(b): withdrawal permitted up to 25% of the contribution made by the subscriber, subject to regulations.",
     f"25% × {R(own)} = {R(capw)}."],
    "Partial withdrawal cap = 25% × subscriber's own contributions",
    "Neither employer contributions nor returns form part of the base.",
    kind="numerical", ref=f"{PFA}, s.20(2)(b)")

pc, fco, fsub, find_ = 300e7, 0.42, 0.15, 0.06
ins_lim = 0.74
agg = fco + fsub + find_
head = (ins_lim - agg) * pc
assert round(agg, 2) == 0.63 and round(head / 1e7, 2) == 33
add("PF_NPS", "L2",
    f"A pension fund has paid-up capital of {crore(pc,0)}. Foreign holdings: a foreign company 42%, that company's subsidiary 15%, and an individual resident "
    "abroad 6%. For this question take the limit permitted for Indian insurance companies as 74%. Under s.24 of the PFRDA Act, 2013, the further equity "
    "that can be held by foreign investors in aggregate is:",
    crore(head, 0),
    [("Nil — the 26% cap is already breached", "ignores the 'insurance limit, whichever is higher' limb"),
     (crore((ins_lim - fco - find_) * pc, 0), "subsidiary's holding excluded from the aggregate"),
     (crore((ins_lim - fco - fsub) * pc, 0), "non-resident individual's holding excluded")],
    ["s.24: aggregate foreign holding (foreign company, its subsidiaries/nominees, foreign individuals/AOPs) ≤ 26% or the insurance-sector limit, whichever is higher.",
     f"Limit = max(26%, 74%) = 74%; aggregate = 42 + 15 + 6 = 63%.",
     f"Headroom = 11% × {crore(pc,0)} = {crore(head,0)}."],
    "Foreign cap = max(26%, insurance-sector limit); headroom = cap − aggregate foreign holding",
    "Aggregate includes subsidiaries and non-resident individuals.",
    kind="numerical", ref=f"{PFA}, s.24 (insurance limit given as data)")

days, prof = 140, 32e5
pen = min(days * 1e5, 1e7)
assert pen == 1e7
add("PF_PEN", "L2",
    f"An entity acted as a point of presence without a certificate of registration for {days} days, earning profits of {lakh(prof,0)} from the activity. "
    "The maximum penalty under s.28(1) of the PFRDA Act, 2013 is:",
    crore(pen),
    [(crore(days * 1e5), "daily penalty without the ceiling"),
     (crore(max(1e7, 5 * prof)), "residual s.28 formula (₹1 crore or 5× profits, higher) applied"),
     (lakh(days * 1e4, 0), "₹10,000 per day assumed")],
    ["s.28(1): failure to obtain registration — ₹1 lakh per day of continuing failure or ₹1 crore, whichever is less.",
     f"{days} × ₹1 lakh = {crore(days*1e5)} > ₹1 crore ⇒ {crore(pen)}."],
    "s.28(1) penalty = min(₹1 lakh × days, ₹1 crore)", "‘Whichever is less’ here; ‘whichever is higher’ is the residual formula.",
    kind="numerical", ref=f"{PFA}, s.28(1)")

sat = date(2026, 3, 12)
d1, d2 = sat + timedelta(60), sat + timedelta(120)
assert (d1, d2) == (date(2026, 5, 11), date(2026, 7, 10))
add("PF_APP", "L2",
    f"An order of the Securities Appellate Tribunal in a PFRDA matter is communicated to the aggrieved intermediary on {fd(sat)}. Under s.38 of the PFRDA Act, 2013, "
    "the appeal to the Supreme Court must ordinarily be filed by, and the outer limit with condonation is:",
    f"{fd(d1)}; extendable to {fd(d2)}",
    [(f"{fd(sat+timedelta(45))}; extendable to {fd(sat+timedelta(90))}", "SAT's 45-day window applied"),
     (f"{fd(d1)}; extendable to {fd(sat+timedelta(90))}", "condonation limited to 30 days"),
     (f"{fd(sat+timedelta(90))}; no further extension", "90 days, no condonation")],
    ["s.38: appeal to the Supreme Court within 60 days from communication of the SAT decision.",
     "The Court may allow a further period not exceeding 60 days for sufficient cause.",
     f"{fd(sat)} + 60 = {fd(d1)}; + 120 = {fd(d2)}."],
    "SC appeal: communication + 60 days (+ up to 60 days)", "45 days is SAT; 60 + 60 is Supreme Court.",
    kind="numerical", ref=f"{PFA}, s.38")

add("PF_FN", "L2",
    "A point of presence and an NPS subscriber dispute whether the PoP delayed transmission of the subscriber's contributions. Under s.14 of the PFRDA Act, 2013:",
    "PFRDA may adjudicate it as an intermediary–subscriber dispute",
    [("Only a civil court can decide it, as it is a contractual dispute", "ignores s.14 adjudication and the s.37 civil-court bar"),
     ("The Securities Appellate Tribunal decides it at first instance", "SAT is appellate only"),
     ("The Insurance Ombudsman decides it, since annuities are involved", "wrong forum")],
    ["s.14(2): functions include adjudication of disputes between intermediaries and between intermediaries and subscribers."],
    "PFRDA Act s.14(2)", "Contrast IRDAI, which adjudicates insurer–intermediary disputes, not customer disputes.",
    ref=f"{PFA}, s.14(2)")

add("PF_PEN", "L2",
    "Penalties realised under the PFRDA Act, 2013 are credited to:",
    "The Subscriber Education and Protection Fund",
    [("The Consolidated Fund of India", "IFSCA/SEBI-style treatment"),
     ("The general fund of PFRDA for its establishment expenses", "operating fund confused"),
     ("The Policyholders' Education and Protection Fund", "IRDA Act s.16A fund")],
    ["s.29: all sums realised by way of penalties are credited to the Subscriber Education and Protection Fund under s.41(1)."],
    "PFRDA Act ss.29, 41", "Penalty money is for subscriber protection, not the regulator's budget.",
    ref=f"{PFA}, ss.29, 41")

# ---- L3 ----
add("PF_NPS", "L3",
    "Consider the following features of the NPS under s.20(2) of the PFRDA Act, 2013:\n\n"
    "1. A subscriber has the option of investing up to 100% of funds in Government securities.\n"
    "2. A subscriber seeking minimum assured returns has the option to invest in schemes providing such returns.\n"
    "3. The Central Government provides an implicit guarantee of benefits to all subscribers.\n\n"
    "Which of the statements is/are correct?",
    "1 and 2 only",
    [("1, 2 and 3", "accepts an implicit Government guarantee"),
     ("2 and 3 only", "denies the 100% G-sec option"),
     ("1 only", "denies the minimum-assured-returns option")],
    ["s.20(2): choice of pension funds and schemes, including up to 100% in Government securities and minimum-assured-return schemes.",
     "No implicit or explicit assurance of benefits except market-based guarantee mechanisms."],
    "PFRDA Act s.20(2)", "NPS is defined-contribution; guarantees exist only if purchased as market-based products.",
    kind="statement", ref=f"{PFA}, s.20(2)")

mp = {"A": 3, "B": 1, "C": 4, "D": 2}
add("PF_NPS", "L3",
    "Match the provision of the PFRDA Act, 2013 with its content:\n\n"
    "| Section | Content |\n|---|---|\n| A. s.21 | 1. Receiving contributions and instructions, transmitting them to the trustee bank or CRA, and paying out benefits |\n"
    "| B. s.22 | 2. Foreign shareholding in a pension fund capped at 26% or the insurance-sector limit, whichever higher |\n"
    "| C. s.25 | 3. Central recordkeeping agency: recordkeeping, accounting and switching |\n"
    "| D. s.24 | 4. Prohibition on investing subscribers' funds outside India |",
    perm(mp),
    [(perm({"A": 1, "B": 3, "C": 4, "D": 2}), "swaps the CRA and PoP roles"),
     (perm({"A": 3, "B": 1, "C": 2, "D": 4}), "swaps the two foreign-investment provisions"),
     (perm({"A": 3, "B": 4, "C": 1, "D": 2}), "treats the PoP section as the investment bar")],
    ["s.21 CRA; s.22 point of presence; s.24 foreign investment cap; s.25 no investment outside India."],
    "PFRDA Act ss.21–25", "s.24 (who owns the fund) vs s.25 (where the fund invests).",
    kind="match", ref=f"{PFA}, ss.21, 22, 24, 25")

p1, p2 = 27e5, 12e5
m1, m2 = max(1e7, 5 * p1), max(1e7, 5 * p2)
assert (m1, m2) == (1.35e7, 1e7)
add("PF_PEN", "L3",
    f"Two registered intermediaries contravene the regulations in ways for which no separate penalty is provided in the PFRDA Act, 2013. Intermediary X made "
    f"profits of {lakh(p1,0)} from its contravention; Intermediary Y made {lakh(p2,0)}. The maximum aggregate penalty that may be imposed under the residual limb of s.28 is:",
    crore(m1 + m2),
    [(crore(min(1e7, 5 * p1) + min(1e7, 5 * p2)), "'whichever is less' applied instead of 'higher'"),
     (crore(2e7), "₹1 crore ceiling applied to each, profit limb ignored"),
     (crore(5 * (p1 + p2)), "only the 5× profit limb applied")],
    ["Residual s.28: penalty may extend to ₹1 crore or five times the profits made/losses avoided, whichever is higher.",
     f"X: max(₹1 crore, 5 × {lakh(p1,0)} = {crore(5*p1)}) = {crore(m1)}.",
     f"Y: max(₹1 crore, {crore(5*p2)}) = {crore(m2)}. Total = {crore(m1+m2)}."],
    "Residual penalty ceiling = max(₹1 crore, 5 × gain)", "The profit limb raises the ceiling only when 5× gain exceeds ₹1 crore.",
    kind="numerical", ref=f"{PFA}, s.28")

add("PF_PEN", "L3",
    "Consider the following statements under the PFRDA Act, 2013:\n\n"
    "1. No court shall take cognizance of an offence under the Act except on a complaint made by the Authority.\n"
    "2. No court inferior to a Court of Session shall try an offence punishable under the Act.\n"
    "3. Failure to pay a penalty imposed under the Act is punishable with imprisonment of up to three years only.\n\n"
    "Which of the statements is/are correct?",
    "1 and 2 only",
    [("1, 2 and 3", "accepts an understated imprisonment term"),
     ("2 and 3 only", "denies the Authority-complaint requirement"),
     ("1 only", "denies the Court of Session requirement")],
    ["s.35(1): cognizance only on the Authority's complaint; s.35(2): Court of Session and above.",
     "s.32(2): failure to pay penalty — imprisonment not less than one month, extendable to ten years, or fine up to ₹25 crore, or both."],
    "PFRDA Act ss.32, 35", "Non-payment of penalty carries a one-month minimum and a ten-year maximum.",
    kind="statement", ref=f"{PFA}, ss.32, 35")

ex_pf = 1 + 6
assert 25 + ex_pf == 32
add("PF_APP", "L3",
    "PFRDA is at its maximum statutory strength and constitutes the Pension Advisory Committee under s.45 of the PFRDA Act, 2013 with the maximum number of other members. "
    "The total membership, counting ex officio members, is:",
    str(25 + ex_pf),
    [("25", "ex officio members counted within the 25"),
     (str(25 + 10), "IRDAI's 1 + 5 + 4 strength used"),
     (str(25 + 1 + 3), "only the Chairperson and the minimum three whole-time members counted")],
    ["s.45: not more than 25 members excluding ex officio members.",
     f"Chairperson and members of the Authority are ex officio: 1 + 6 = {ex_pf}.",
     f"Maximum = 25 + {ex_pf} = {25+ex_pf}."],
    "Max PAC = 25 + (1 + ≤6 members)", "Use PFRDA's own strength (1 + 6), not IRDAI's.",
    kind="numerical", ref=f"{PFA}, ss.4, 45")

add("PF_CON", "L3",
    "Consider the following statements under the PFRDA Act, 2013:\n\n"
    "1. For two years after ceasing office, the Chairperson and whole-time members may not, without Central Government approval, accept employment under the Central or a State Government or in any regulated entity in the pension sector.\n"
    "2. A part-time member holds office for a term not exceeding five years.\n"
    "3. The members must include at least one person with knowledge or experience in each of economics, finance and law.\n\n"
    "Which of the statements is/are correct?",
    "1, 2 and 3",
    [("1 and 2 only", "denies the discipline-mix requirement"),
     ("2 and 3 only", "denies the cooling-off restriction"),
     ("1 and 3 only", "denies the five-year cap on part-time members")],
    ["s.7: two-year restriction on future employment (Government / pension-sector regulated entity).",
     "s.5: part-time member term not exceeding five years.",
     "s.4: at least one person from each of economics, finance and law."],
    "PFRDA Act ss.4, 5, 7", "All three are statutory; the trap is to assume one is from another Act.",
    kind="statement", ref=f"{PFA}, ss.4, 5, 7")

c, w = ar(0)
add("PF_FN", "L3",
    "**Assertion (A):** A State Government may bring its employees within the National Pension System.\n\n"
    "**Reason (R):** Section 12 of the PFRDA Act, 2013 enables a State Government to make the NPS applicable to its employees by notification.",
    c, w,
    ["s.12 lets the Central and State Governments notify NPS for their employees.", "That enabling power is exactly why A holds."],
    "PFRDA Act s.12", "State participation is by notification, not by an amendment of the Act.",
    kind="assertion-reason", ref=f"{PFA}, s.12")

# ---- L4 case: Suvidha (5) ----
G3 = "ACTI-CASE-PFRDA-SUVIDHA"
st, stop = date(2026, 1, 10), date(2026, 4, 18)
ndays = (stop - st).days
assert ndays == 98
prof_s = 21e5
recv = date(2026, 6, 22)
case_pf = (
    f"**Case.** Suvidha Pension Services Ltd began accepting NPS contributions from subscribers and transmitting them to the CRA as a point of presence on "
    f"{fd(st)} without a certificate of registration from PFRDA. It stopped on {fd(stop)} when PFRDA intervened (the failure continued up to the day before). "
    f"It earned {lakh(prof_s,0)} from the activity. After an inquiry, a penalty order was passed and received by Suvidha on {fd(recv)}. "
    "Suvidha's foreign parent holds 30% of its equity; Suvidha now also wants registration as a pension fund. "
    "For this case take the limit permitted for Indian insurance companies as 74%.\n\n")
pen_s = min(ndays * 1e5, 1e7)
add("PF_PEN", "L4", case_pf + "The maximum penalty for Suvidha's failure to obtain registration is:",
    lakh(pen_s, 0),
    [("₹1 crore", "ceiling read as a fixed penalty"),
     (crore(max(1e7, 5 * prof_s)), "residual '₹1 crore or 5× profit, higher' limb applied"),
     (lakh((ndays + 1) * 1e5, 0), "stopping day counted as a day of failure")],
    [f"Days of continuing failure = {fd(st)} to the day before {fd(stop)} = {ndays}.",
     f"s.28(1): min({ndays} × ₹1 lakh, ₹1 crore) = {lakh(pen_s,0)}."],
    "s.28(1) = min(₹1 lakh × days, ₹1 crore)", "Here the day-count stays under the ₹1 crore ceiling.",
    kind="case", group=G3, ref=f"{PFA}, ss.27, 28(1)")

sat_dl = recv + timedelta(45)
assert sat_dl == date(2026, 8, 6)
add("PF_APP", "L4", case_pf + "The last date for Suvidha to appeal without seeking condonation of delay is:",
    f"{fd(sat_dl)}, before the Securities Appellate Tribunal",
    [(f"{fd(recv+timedelta(30))}, before the Securities Appellate Tribunal", "30-day window"),
     (f"{fd(recv+timedelta(60))}, before the Supreme Court", "skips SAT; uses the SC window"),
     (f"{fd(recv+timedelta(45))}, before the Central Government", "wrong forum")],
    [f"s.36: SAT, within 45 days of receipt of order: {fd(recv)} + 45 = {fd(sat_dl)}."],
    "SAT appeal = receipt + 45 days", "First appeal is to SAT, not the Supreme Court.",
    kind="case", group=G3, ref=f"{PFA}, s.36")

add("PF_PEN", "L4", case_pf + "In deciding the quantum of Suvidha's penalty, which of the following is NOT a factor the PFRDA Act, 2013 requires to be considered?",
    "The paid-up capital and net worth of Suvidha",
    [("The amount of disproportionate gain or unfair advantage made by Suvidha", "is a statutory factor"),
     ("The amount of loss caused to subscribers", "is a statutory factor"),
     ("The repetitive nature of the default", "is a statutory factor")],
    ["The Act lists: quantifiable disproportionate gain/unfair advantage, loss caused to subscribers, and repetitive nature of default.",
     "Size or net worth of the defaulter is not a listed factor."],
    "PFRDA Act — factors for adjudging penalty", "Capacity to pay is not a statutory factor.",
    kind="case", group=G3, ref=f"{PFA}, s.30")

sc_comm = date(2026, 12, 14)
sc_dl = sc_comm + timedelta(60)
assert sc_dl == date(2027, 2, 12)
add("PF_APP", "L4", case_pf + f"SAT dismisses Suvidha's appeal; the decision is communicated on {fd(sc_comm)}. Suvidha's further remedy is:",
    f"Appeal to the Supreme Court by {fd(sc_dl)}, extendable by up to 60 days",
    [(f"Appeal to the Supreme Court by {fd(sc_comm+timedelta(45))}, extendable by up to 45 days", "SAT's 45-day window transplanted"),
     (f"Appeal to the High Court by {fd(sc_dl)}, extendable by up to 60 days", "wrong forum"),
     (f"Review before PFRDA by {fd(sc_comm+timedelta(30))}, with no further appeal", "invented review route")],
    [f"s.38: Supreme Court within 60 days of communication = {fd(sc_dl)}; Court may allow a further ≤ 60 days."],
    "SC appeal = communication + 60 (+60)", "The route is Authority → SAT → Supreme Court.",
    kind="case", group=G3, ref=f"{PFA}, s.38")

lim = max(0.26, 0.74)
add("PF_NPS", "L4", case_pf + "Regarding Suvidha's 30% foreign shareholding and its proposed registration as a pension fund:",
    f"Permissible, since the cap is the higher of 26% and the insurance-sector limit, i.e. {pct(lim,0)}",
    [("Not permissible, since foreign holding in a pension fund is capped at 26%", "ignores the 'whichever is higher' limb"),
     ("Permissible only after the foreign parent sells down to 26% within six months", "invents a divestment timeline"),
     ("Irrelevant, since the s.24 cap applies only to CRAs and PoPs", "misapplies s.24 — it governs pension funds")],
    ["s.24: aggregate foreign holding in a pension fund ≤ 26% or the percentage approved for insurance companies, whichever is higher.",
     f"max(26%, 74%) = {pct(lim,0)} > 30% ⇒ permissible (subject to other eligibility norms under s.26)."],
    "Cap = max(26%, insurance-sector limit)", "26% is only the floor of the formula.",
    kind="case", group=G3, ref=f"{PFA}, s.24 (insurance limit given as data)")

# =====================================================================================
# IFSCA ACT, 2019  (24)  L1 5 · L2 7 · L3 7 · L4 5
# =====================================================================================
add("IF_APP", "L1",
    "The International Financial Services Centres Authority Act, 2019 applies to International Financial Services Centres set up under:",
    "Section 18 of the Special Economic Zones Act, 2005",
    [("Section 45W of the Reserve Bank of India Act, 1934", "RBI Act directions power confused with IFSC set-up"),
     ("Section 11 of the SEBI Act, 1992", "SEBI's general powers section"),
     ("Section 47 of the Foreign Exchange Management Act, 1999", "FEMA rule-making power confused")],
    ["s.2: the Act applies to IFSCs set up under s.18 of the SEZ Act, 2005; s.3 defines IFSC the same way."],
    "IFSCA Act ss.2, 3", "The SEZ Act is the legal anchor of every IFSC.",
    ref=f"{IFA}, s.2")

add("IF_COMP", "L1",
    "Which of the following does NOT nominate a member to the International Financial Services Centres Authority?",
    "Insolvency and Bankruptcy Board of India",
    [("Reserve Bank of India", "nominates under s.5(1)(b)(i)"),
     ("Pension Fund Regulatory and Development Authority", "nominates under s.5(1)(b)(iv)"),
     ("Insurance Regulatory and Development Authority of India", "nominates under s.5(1)(b)(iii)")],
    ["s.5(1)(b): one member each nominated ex officio by RBI, SEBI, IRDAI and PFRDA."],
    "IFSCA Act s.5(1)(b)", "Only the four financial-sector regulators in the First Schedule nominate.",
    ref=f"{IFA}, s.5")

add("IF_FIN", "L1",
    "Under s.20 of the IFSCA Act, 2019, every transaction of financial services in an IFSC shall be in:",
    "Foreign currency specified by regulations, consulting the Central Government",
    [("Indian rupees or any freely convertible currency, at the parties' option", "treats INR as a default option"),
     ("Any currency agreed between the parties, subject only to FEMA", "ignores the regulatory specification"),
     ("Such foreign currency as the Reserve Bank may notify under FEMA", "wrong specifying authority")],
    ["s.20: transactions of financial services in an IFSC shall be in such foreign currency as may be specified by regulations (of the Authority) in consultation with the Central Government."],
    "IFSCA Act s.20", "The Authority specifies — in consultation with the Government, not RBI.",
    ref=f"{IFA}, s.20")

add("IF_POW", "L1",
    "Within an IFSC, the powers of the Reserve Bank of India under the Banking Regulation Act, 1949 in respect of an IFSC Banking Unit are exercised by:",
    "The International Financial Services Centres Authority",
    [("The Reserve Bank of India, concurrently with IFSCA", "assumes concurrent jurisdiction"),
     ("The Reserve Bank of India, with IFSCA's concurrence", "reverses the transfer of powers"),
     ("The Central Government through the Development Commissioner of the SEZ", "confuses SEZ administration with financial regulation")],
    ["s.13(1): all powers exercisable by an appropriate regulator under the Acts in the First Schedule shall, in the IFSCs, be exercised by the Authority.",
     "The Banking Regulation Act is among RBI's First Schedule Acts."],
    "IFSCA Act s.13(1)", "In the IFSC, IFSCA is the unified regulator — not a co-regulator.",
    ref=f"{IFA}, s.13(1), First Schedule")

add("IF_CG", "L1",
    "Under s.26 of the IFSCA Act, 2019, in respect of its wealth, income, profits or gains, the Authority:",
    "Is not liable to pay income-tax or any other tax",
    [("Is liable to income-tax at the concessional IFSC unit rate", "applies IFSC-unit tax incentives to the regulator"),
     ("Is exempt only for its first ten years of operation", "confuses with the IFSC unit tax holiday"),
     ("Is liable to tax only on income from penalties", "invented partial liability")],
    ["s.26: notwithstanding any tax law, the Authority is not liable to pay income-tax or any other tax in respect of its wealth, income, profits or gains."],
    "IFSCA Act s.26", "Tax holidays for IFSC units are a different regime from the regulator's own exemption.",
    ref=f"{IFA}, s.26")

# ---- L2 ----
comp = {"Chairperson": 1, "regulator nominees": 4, "Finance Ministry officials": 2, "Selection Committee members": 2}
exoff = comp["regulator nominees"] + comp["Finance Ministry officials"]
assert sum(comp.values()) == 9 and exoff == 6
add("IF_COMP", "L2",
    "When IFSCA is fully constituted under s.5 of the IFSCA Act, 2019, the number of members who are ex officio is:",
    str(exoff),
    [(str(comp["regulator nominees"]), "counts only regulator nominees"),
     (str(sum(comp.values()) - 1), "treats all members other than the Chairperson as ex officio"),
     (str(comp["Finance Ministry officials"]), "counts only Finance Ministry officials")],
    ["s.5(1): Chairperson; one member each from RBI, SEBI, IRDAI, PFRDA (ex officio); two Finance Ministry officials (ex officio); two members on Selection Committee recommendation.",
     f"Ex officio = 4 + 2 = {exoff} of {sum(comp.values())}."],
    "IFSCA = 1 + 4 (ex officio) + 2 (ex officio) + 2", "The Chairperson and the two Selection-Committee members are not ex officio.",
    kind="numerical", ref=f"{IFA}, s.5")

dob, appt = date(1966, 2, 3), date(2026, 5, 1)
end = min(add_years(appt, 3), add_years(dob, 62))
assert end == date(2028, 2, 3)
add("IF_COMP", "L2",
    f"A whole-time member of IFSCA appointed on Selection Committee recommendation, born on {fd(dob)}, enters office on {fd(appt)}. Under s.6 of the IFSCA Act, 2019 she holds office until:",
    fd(end),
    [(fd(add_years(appt, 3)), "three-year term applied, age limit ignored"),
     (fd(add_years(dob, 65)), "Chairperson's 65-year limit applied"),
     (fd(add_years(appt, 5)), "IRDAI/PFRDA five-year term")],
    ["s.6(1): term three years, eligible for reappointment; no Chairperson beyond 65, no whole-time member beyond 62.",
     f"3 years → {fd(add_years(appt,3))}; age 62 → {fd(add_years(dob,62))}.", f"Earlier = {fd(end)}."],
    "Tenure end = min(entry + 3 years, 62nd birthday)", "IFSCA's term is three years, not five.",
    kind="numerical", ref=f"{IFA}, s.6(1)")

fy = date(2026, 3, 31)
rdl = fy + timedelta(90)
assert rdl == date(2026, 6, 29)
add("IF_FIN", "L2",
    "Under s.19 of the IFSCA Act, 2019, the Authority's annual report on its activities, policies and programmes for FY 2025-26 must reach the Central Government by:",
    fd(rdl),
    [(fd(date(2026, 6, 30)), "three calendar months used instead of ninety days"),
     (fd(date(2026, 12, 31)), "IRDAI's nine-month period"),
     (fd(date(2026, 9, 30)), "six-month period invented")],
    [f"s.19(2): within ninety days after the end of each financial year: {fd(fy)} + 90 days = {fd(rdl)}.",
     "The report is laid before each House of Parliament."],
    "IFSCA annual report = FY end + 90 days", "Ninety days ≠ three months: April 30 + May 31 + June 29 = 90.",
    kind="numerical", ref=f"{IFA}, s.19")

add("IF_COMP", "L2",
    "Under s.5(2) of the IFSCA Act, 2019, which member(s) must necessarily be whole-time?",
    "The Chairperson only",
    [("The Chairperson and the two Finance Ministry officials", "treats ex officio officials as whole-time"),
     ("The Chairperson and the two Selection Committee members", "these two may be whole-time or part-time"),
     ("The four regulator nominees", "ex officio nominees are not whole-time members")],
    ["s.5(2): the Chairperson shall be a whole-time member; the two clause (d) members may be whole-time or part-time as the Central Government deems fit."],
    "IFSCA Act s.5(2)", "Only the Chairperson's whole-time status is mandated.",
    ref=f"{IFA}, s.5(2)")

add("IF_APP", "L2",
    "Which of the following is NOT a 'financial product' as defined in s.3 of the IFSCA Act, 2019?",
    "A contract to exchange one currency for another to be settled immediately",
    [("A contract of insurance written by an IFSC insurance office", "expressly included"),
     ("A credit arrangement such as a syndicated loan", "expressly included"),
     ("A foreign currency forward contract to be settled after three months", "included — only immediate-settlement exchanges are excluded")],
    ["s.3: financial product includes securities, contracts of insurance, deposits, credit arrangements, and foreign currency contracts other than contracts to exchange one currency for another that are to be settled immediately, plus notified products."],
    "IFSCA Act s.3 — 'financial product'", "Spot currency exchange is carved out; forwards are in.",
    ref=f"{IFA}, s.3")

add("IF_CG", "L2",
    "The Central Government proposes to exclude IFSC units from a provision of a Central Act. Under s.31 of the IFSCA Act, 2019, the proposed notification must:",
    "Be laid in draft before each House for 30 days, which may disapprove or modify it",
    [("Be laid in draft before each House for 7 days, after which it takes effect", "wrong laying period"),
     ("Be issued straight away; laying before Parliament is not required", "ignores the draft-laying safeguard"),
     ("Await an amending Act of Parliament", "ignores the delegated power in s.31")],
    ["s.31(1): the Central Government may declare that a Central Act shall not apply, or apply with modifications, to IFSC products/services/institutions.",
     "s.31(2): draft laid before each House for thirty days (one or more sessions); Houses may disapprove or modify."],
    "IFSCA Act s.31", "Draft-laying for 30 days is the parliamentary check.",
    ref=f"{IFA}, s.31")

add("IF_POW", "L2",
    "IFSCA investigates a broker-dealer in the IFSC for a violation of provisions it administers under the Securities Contracts (Regulation) Act, 1956. Under s.13(4) of the IFSCA Act, 2019, the investigation and penalty proceedings follow:",
    "The respective First Schedule Act's procedure, applied by IFSCA",
    [("The procedure in the Code of Criminal Procedure alone", "ignores the borrowed statutory procedure"),
     ("SEBI's investigation, followed by adjudication by IFSCA", "splits powers between SEBI and IFSCA"),
     ("A fresh procedure that IFSCA must first frame by regulations", "ignores s.13(4)'s incorporation of existing procedure")],
    ["s.13(4): provisions of the respective Acts on filing, inspection, investigation, prosecution and penalty apply to IFSC products, services and institutions.",
     "The powers are exercised by IFSCA under s.13(1)."],
    "IFSCA Act s.13(1), (4)", "IFSCA borrows both the powers and the procedure of the parent Acts.",
    ref=f"{IFA}, s.13(4)")

# ---- L3 ----
mp = {"A": 2, "B": 3, "C": 1, "D": 4}
add("IF_POW", "L3",
    "Match the Act with the appropriate regulator against which it is listed in the First Schedule to the IFSCA Act, 2019 (as enacted):\n\n"
    "| Act | Appropriate regulator |\n|---|---|\n| A. Depositories Act, 1996 | 1. Reserve Bank of India |\n"
    "| B. General Insurance Business (Nationalisation) Act, 1972 | 2. SEBI |\n"
    "| C. Payment and Settlement Systems Act, 2007 | 3. IRDAI |\n"
    "| D. PFRDA Act, 2013 | 4. PFRDA |",
    perm(mp),
    [(perm({"A": 1, "B": 3, "C": 2, "D": 4}), "treats depositories as RBI's and payment systems as SEBI's"),
     (perm({"A": 2, "B": 4, "C": 1, "D": 3}), "swaps IRDAI and PFRDA"),
     (perm({"A": 2, "B": 1, "C": 3, "D": 4}), "treats GIBNA as RBI's")],
    ["First Schedule: RBI — RBI Act, BR Act, FEMA, PSS Act etc.; SEBI — SCRA, SEBI Act, Depositories Act;",
     "IRDAI — Insurance Act, GIBNA 1972, IRDA Act; PFRDA — PFRDA Act."],
    "IFSCA Act First Schedule", "Depositories are SEBI's; payment systems are RBI's.",
    kind="match", ref=f"{IFA}, First Schedule")

add("IF_COMP", "L3",
    "Consider the following statements on meetings of IFSCA under s.8 of the IFSCA Act, 2019:\n\n"
    "1. Questions are decided by a majority of votes of members present and voting, the presiding member having a casting vote in a tie.\n"
    "2. The quorum is fixed by the Act at one-half of the total members.\n"
    "3. A member with a direct or indirect interest in a matter must disclose it and not take part in deliberations on it.\n\n"
    "Which of the statements is/are correct?",
    "1 and 3 only",
    [("1, 2 and 3", "accepts a statutory quorum figure"),
     ("2 and 3 only", "denies majority-of-present-and-voting rule"),
     ("1 and 2 only", "denies the conflict-of-interest rule")],
    ["s.8(1): times, places, procedure and quorum as specified by regulations — the Act fixes no quorum.",
     "s.8(3): majority of members present and voting; casting vote in a tie.", "s.8(4): disclosure and abstention."],
    "IFSCA Act s.8", "Quorum is left to regulations.",
    kind="statement", ref=f"{IFA}, s.8")

notice_d = date(2026, 6, 1)
eff_d = add_months(notice_d, 3)
assert eff_d == date(2026, 9, 1)
add("IF_COMP", "L3",
    f"On {fd(notice_d)}, a part-time member of IFSCA appointed on Selection Committee recommendation, and the SEBI-nominated ex officio member, both give written notice to the Central Government that they wish to demit office. "
    "Under s.6(3)-(4) of the IFSCA Act, 2019, which is correct?",
    f"Her resignation needs three months' notice (to {fd(eff_d)}); only she faces the two-year restriction",
    [(f"Both need notice of at least one month (to {fd(add_months(notice_d,1))}); the two-year restriction applies to both",
      "one-month notice; restriction extended to ex officio members"),
     (f"Both need notice of at least three months (to {fd(eff_d)}); the two-year restriction applies to both", "restriction extended to ex officio members"),
     (f"The part-time member's resignation needs notice of at least three months (to {fd(eff_d)}); the employment restriction on her lasts one year",
      "one-year cooling-off instead of two")],
    ["s.6(3)(a): a member may resign by written notice of not less than three months.",
     "s.6(4): no member other than an ex officio member shall, for two years after ceasing office, accept Government employment or appointment in any IFSC financial institution without prior approval."],
    "Resignation ≥ 3 months' notice; cooling-off 2 years (non-ex officio only)", "Ex officio nominees are outside the cooling-off rule.",
    ref=f"{IFA}, s.6(3)-(4)")

add("IF_CG", "L3",
    "Consider the following statements on supersession of IFSCA under s.22 of the IFSCA Act, 2019:\n\n"
    "1. The period of supersession cannot exceed six months.\n"
    "2. The Authority must be given a reasonable opportunity to make representations before the notification is issued.\n"
    "3. The Chairperson continues in office during supersession, while the other members vacate.\n\n"
    "Which of the statements is/are correct?",
    "1 and 2 only",
    [("1, 2 and 3", "accepts continuance of the Chairperson"),
     ("1 and 3 only", "denies the pre-notification opportunity"),
     ("2 only", "denies the six-month ceiling")],
    ["s.22: supersession for up to six months after giving the Authority a reasonable opportunity to make representations.",
     "On supersession the Chairperson and all Members vacate office; powers are exercised by the Central Government until reconstitution."],
    "IFSCA Act s.22", "Everyone vacates — including the Chairperson.",
    kind="statement", ref=f"{IFA}, s.22")

add("IF_FIN", "L3",
    "Consider the following statements on the Performance Review Committee under s.17 of the IFSCA Act, 2019:\n\n"
    "1. It is to consist of at least two members.\n"
    "2. It reviews the Authority's functioning at least once in every financial year.\n"
    "3. It is constituted by the Central Government from among officials of the Ministry of Finance.\n\n"
    "Which of the statements is/are correct?",
    "1 and 2 only",
    [("1, 2 and 3", "treats the PRC as a Government-constituted body"),
     ("2 and 3 only", "denies the minimum-size requirement"),
     ("1 and 3 only", "denies the annual review")],
    ["s.17: the Authority constitutes a PRC of at least two members, reviewing at least once every financial year whether it acts in accordance with law, promotes transparency and good governance, and manages risks."],
    "IFSCA Act s.17", "The PRC is an internal accountability committee of the Authority.",
    kind="statement", ref=f"{IFA}, s.17")

add("IF_FIN", "L3",
    "Consider the following statements under the IFSCA Act, 2019:\n\n"
    "1. Fees and charges received by the Authority are credited to the International Financial Services Centres Authority Fund.\n"
    "2. Penalties collected by the Authority under s.13 are credited to that Fund to meet its expenses.\n"
    "3. The Fund is applied to salaries and allowances of members, officers and employees and to other expenses of the Authority.\n\n"
    "Which of the statements is/are correct?",
    "1 and 3 only",
    [("1, 2 and 3", "routes penalties into the Authority's Fund"),
     ("2 and 3 only", "denies crediting of fees"),
     ("1 and 2 only", "denies the Fund's application to salaries and expenses")],
    ["s.15: Fund credited with grants, fees and charges and other approved sums; applied to salaries and other expenses.",
     "s.13(6): penalties are credited to the Consolidated Fund of India in rupees."],
    "IFSCA Act ss.13(6), 15", "IFSCA penalties go to the CFI.",
    kind="statement", ref=f"{IFA}, ss.13, 15")

c, w = ar(3)
add("IF_APP", "L3",
    "**Assertion (A):** The IFSCA Act, 2019 applies only to the IFSC at GIFT City, Gandhinagar, since that IFSC is named in the Act.\n\n"
    "**Reason (R):** The Act applies to International Financial Services Centres set up under s.18 of the Special Economic Zones Act, 2005.",
    c, w,
    ["s.2 extends the Act to every IFSC set up under s.18 SEZ Act — no IFSC is named, so A is false.", "R states s.2 correctly."],
    "IFSCA Act s.2", "Application is by legal category, not by location.",
    kind="assertion-reason", ref=f"{IFA}, s.2")

# ---- L4 case: Aurora (5) ----
G4 = "ACTI-CASE-IFSCA-AURORA"
pen_inr = 2.4e7
r_ord, r_me, r_pay = 86.40, 87.10, 86.90
ordd, payd = date(2026, 8, 14), date(2026, 9, 9)
usd = pen_inr / r_ord
assert round(usd, 2) == 277777.78
case_if = (
    "**Case.** Aurora Capital (IFSC) Pvt Ltd is a broker-dealer unit in an IFSC set up under s.18 of the SEZ Act, 2005. After an inspection, IFSCA "
    f"finds violations of provisions it administers under the Securities Contracts (Regulation) Act, 1956 and, by order dated {fd(ordd)}, imposes a penalty of "
    f"₹{inr(pen_inr)} as specified in that Act. RBI reference rates (₹ per USD): {fd(ordd)} — {r_ord:.2f}; 31 August 2026 — {r_me:.2f}; "
    f"{fd(payd)} (date of payment) — {r_pay:.2f}. Aurora has also been accepting client margin in Indian rupees, and proposes a new category of service that "
    "no regulator had earlier permitted in any IFSC. A former part-time IFSCA member (Selection Committee appointee) who ceased office on 30 November 2025 is to join Aurora's board.\n\n")


def usd_s(x):
    return f"USD {x:,.2f}"


add("IF_POW", "L4", case_if + "Which authority exercised the relevant powers of SEBI under the SCRA against Aurora, and on what basis?",
    "IFSCA, as s.13(1) vests SEBI's SCRA powers in it within IFSCs",
    [("SEBI, as SCRA powers were never transferred to IFSCA", "denies the First Schedule transfer"),
     ("IFSCA, but only after SEBI referred the matter to it", "invents a referral pre-condition"),
     ("SEBI and IFSCA jointly, under a memorandum of understanding", "assumes concurrent jurisdiction")],
    ["SCRA, 1956 is listed against SEBI in the First Schedule.",
     "s.13(1): such powers are exercised by IFSCA in IFSCs."],
    "IFSCA Act s.13(1)", "Unified regulator: IFSCA alone in the IFSC.",
    kind="case", group=G4, ref=f"{IFA}, s.13(1), First Schedule")

add("IF_POW", "L4", case_if + "How much must Aurora pay, and where does it go?",
    f"{usd_s(usd)}, credited to the Consolidated Fund of India in rupees",
    [(f"{usd_s(pen_inr/r_pay)}, credited to the Consolidated Fund of India in rupees", "payment-date rate used"),
     (f"{usd_s(pen_inr/r_me)}, credited to the Consolidated Fund of India in rupees", "month-end rate used"),
     (f"{usd_s(usd)}, credited to the IFSCA Fund", "penalty credited to the Authority's own Fund")],
    ["s.13(5): penalty collected in foreign currency equivalent at the RBI reference rate on the date of the order.",
     f"₹{inr(pen_inr)} ÷ {r_ord:.2f} = {usd_s(usd)}.",
     "s.13(6): sums credited to the Consolidated Fund of India in Indian rupees."],
    "USD due = ₹ penalty ÷ RBI reference rate on order date",
    "The order date, not the payment date, fixes the rate; money goes to the CFI.",
    kind="case", group=G4, ref=f"{IFA}, s.13(5)-(6)")

add("IF_FIN", "L4", case_if + "Aurora's acceptance of client margin in Indian rupees is to be tested against:",
    "s.20 — only foreign currency specified by IFSCA regulations is permitted",
    [("FEMA alone, since the IFSCA Act is silent on currency", "ignores s.20"),
     ("s.20 — rupee dealings are allowed if RBI has notified the currency list", "wrong specifying authority"),
     ("No restriction, since the IFSC is Indian territory where the rupee is legal tender", "ignores the foreign-currency mandate")],
    ["s.20: every transaction of financial services in an IFSC shall be in such foreign currency as specified by regulations in consultation with the Central Government."],
    "IFSCA Act s.20", "IFSC = foreign-currency jurisdiction by statute.",
    kind="case", group=G4, ref=f"{IFA}, s.20")

add("IF_POW", "L4", case_if + "For Aurora's proposed new category of service, the correct route is:",
    "IFSCA recommends; Government notifies; IFSCA then regulates",
    [("IFSCA permits it by its own regulations under s.12(1)", "treats the general duty as a power to create categories"),
     ("SEBI must first permit it in the domestic market", "invented precedence"),
     ("The First Schedule must be amended by Parliament", "Schedule lists regulators/Acts and is amended by notification")],
    ["s.12(2)(b)-(c): regulate products/services notified by the Central Government; recommend new ones for notification."],
    "IFSCA Act s.12(2)(b)-(c)", "New category = recommendation + notification.",
    kind="case", group=G4, ref=f"{IFA}, s.12(2)")

ceased, join1 = date(2025, 11, 30), date(2026, 10, 1)
cool_end = add_years(ceased, 2)
assert join1 < cool_end
add("IF_COMP", "L4", case_if + "The former part-time member is to join Aurora's board on 1 October 2026. Under s.6(4):",
    f"Central Government approval needed; the bar runs till {fd(cool_end)}",
    [("No approval is needed, since the restriction applies only to whole-time members", "restricts s.6(4) to WTMs"),
     (f"No approval is needed, since the one-year restriction ended on {fd(add_years(ceased,1))}", "one-year cooling-off"),
     ("Approval is needed from IFSCA, not from the Central Government", "wrong approving authority")],
    ["s.6(4): any member other than an ex officio member, for two years after ceasing office, needs prior Central Government approval for appointment in any IFSC financial institution.",
     f"{fd(ceased)} + 2 years = {fd(cool_end)} > 1 October 2026."],
    "Cooling-off = cessation + 2 years; approval by Central Government", "Part-time non-ex officio members are covered too.",
    kind="case", group=G4, ref=f"{IFA}, s.6(4)")

# =====================================================================================
QUOTA = {"Insurance Act": 22, "IRDA Act": 20, "PFRDA Act": 24, "IFSCA Act": 24}
per_act = Counter(B.cat[q["microtopic_slug"]]["name"].split(" — ")[0] for q in B.Q)
print("per act", dict(per_act))
assert dict(per_act) == QUOTA, per_act
groups = Counter(q["stimulus_group"] for q in B.Q if q["stimulus_group"])
assert all(3 <= v <= 5 for v in groups.values()), groups
assert all(q["rubric_level"] == "L4" for q in B.Q if q["stimulus_group"])
missing = set(B.cat) - {q["microtopic_slug"] for q in B.Q}
assert not missing, missing
assert len(B.Q) == 90
print("case sets", dict(groups))
B.write()
