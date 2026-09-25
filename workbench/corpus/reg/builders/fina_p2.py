"""FIN-A part 2: banking, money market, bank regulation. Case sets C2 (bank capital) and C5 (working-capital borrower)."""
import math
from reglib import inr, R, pct, lakh, crore
from fina_util import table, f2

NPA = "fin-asset-classification-npa-and-divergence-disclosure-bce36906"
ADV = "fin-bank-advances-cash-credit-overdraft-bill-discounting-5a3cb714"
BRA = "fin-banking-regulation-act-1949-licensing-s-35a-scheduled-banks-bc585c11"
BAS = "fin-basel-norms-and-capital-adequacy-2a0b56cf"
LEV = "fin-capital-and-leverage-norms-d-sibs-c1201623"
BC = "fin-business-correspondents-a0d54848"
CD = "fin-certificates-of-deposit-denomination-and-maturity-49b00cd6"
CP = "fin-commercial-paper-eligibility-and-net-worth-b032568c"
CM = "fin-call-notice-and-term-money-4a0be84f"
CTS = "fin-cheque-truncation-system-df558b7f"
DFI = "fin-development-financial-institutions-nabard-sidbi-nhb-nabfid-e-95bc9803"
EXP = "fin-export-credit-and-trade-finance-7f162ab0"
FB = "fin-fbil-benchmark-rates-fbb2b6a6"

IRAC = "RBI Master Circular — Prudential norms on Income Recognition, Asset Classification and Provisioning (IRACP); Prudential Framework for Resolution of Stressed Assets (7 June 2019)"
BASEL = "RBI Master Circular — Basel III Capital Regulations; RBI D-SIB framework (2014) and leverage ratio guidelines (June 2019)"


def L(x):
    return lakh(x)


def add_all(B):
    A = B.add

    # ================= NPA =================
    A(NPA, "L1",
      "Under RBI's framework for early recognition of stress, a term loan (not a revolving facility) whose principal or interest has remained overdue for 75 days is classified as:",
      "SMA-2",
      [("SMA-1", "SMA-1 covers 31–60 days overdue"),
       ("Sub-standard (NPA)", "NPA only after overdue for more than 90 days"),
       ("SMA-0", "SMA-0 covers up to 30 days overdue")],
      ["SMA-0: 1–30 days; SMA-1: 31–60 days; SMA-2: 61–90 days overdue.",
       "Beyond 90 days the account becomes an NPA (sub-standard)."],
      "Overdue 61–90 days ⇒ SMA-2", "SMA categories are standard assets; NPA begins after 90 days.",
      kind="conceptual", verify_fact=True, ref=IRAC)

    A(NPA, "L2",
      "A secured term loan was classified as NPA on 31 March 2025 and has remained NPA since, with realisable security. As on 30 September 2027 its asset classification is:",
      "Doubtful — D2",
      [("Doubtful — D1", "counts doubtful period from the NPA date instead of after 12 months as sub-standard"),
       ("Doubtful — D3", "counts total NPA age (2.5 years) as the doubtful period and misreads the D3 band"),
       ("Loss asset", "loss classification depends on the security being identified as uncollectible, not on age alone")],
      ["Sub-standard: 31 Mar 2025 → 31 Mar 2026 (12 months).",
       "Doubtful from 31 Mar 2026; by 30 Sep 2027 it has been doubtful for 18 months.",
       "D1 ≤ 1 year; D2 > 1 to 3 years; D3 > 3 years ⇒ D2."],
      "Doubtful age = NPA age − 12 months", "The doubtful clock starts only after 12 months as sub-standard.",
      verify_fact=True, ref=IRAC)

    # provisioning table
    std, ss_sec, ss_uns = 500e7, 40e7, 10e7
    d1_bal, d1_sec = 30e7, 18e7
    d3_bal, d3_sec = 12e7, 5e7
    loss = 4e7
    prov = (std * 0.004 + ss_sec * 0.15 + ss_uns * 0.25 + d1_sec * 0.25 + (d1_bal - d1_sec) * 1.0
            + d3_bal * 1.0 + loss)
    w1 = prov - (d1_sec * 0.25 + (d1_bal - d1_sec)) + d1_bal * 0.25
    w2 = prov - ss_uns * 0.25 + ss_uns * 0.15
    w3 = prov - std * 0.004
    rows = [["Standard assets (general category)", crore(std, 0), "—"],
            ["Sub-standard — secured", crore(ss_sec, 0), "—"],
            ["Sub-standard — unsecured exposure (ab initio)", crore(ss_uns, 0), "—"],
            ["Doubtful D1", crore(d1_bal, 0), crore(d1_sec, 0)],
            ["Doubtful D3", crore(d3_bal, 0), crore(d3_sec, 0)],
            ["Loss assets", crore(loss, 0), "—"]]
    A(NPA, "L3",
      "Shivalik Bank (fictional) has the following advances portfolio:\n\n"
      + table(["Category", "Outstanding", "Realisable security"], rows) +
      "\n\nApplying RBI's minimum provisioning norms (standard 0.40%; sub-standard 15%, unsecured sub-standard 25%; doubtful secured portion D1 25%, D2 40%, D3 100%; unsecured portion of doubtful 100%; loss 100%), total provision required is:",
      crore(prov),
      [(crore(w1), "entire D1 balance provided at 25% (unsecured portion not segregated)"),
       (crore(w2), "unsecured sub-standard exposure provided at 15%"),
       (crore(w3), "standard asset provision omitted")],
      [f"Standard: 0.40% × 500 = ₹{std*0.004/1e7:.2f} cr",
       f"Sub-standard: 15% × 40 + 25% × 10 = ₹{(ss_sec*0.15+ss_uns*0.25)/1e7:.2f} cr",
       f"D1: 25% × 18 + 100% × 12 = ₹{(d1_sec*0.25+(d1_bal-d1_sec))/1e7:.2f} cr",
       f"D3: 100% × 12 = ₹12.00 cr; Loss: ₹4.00 cr",
       f"Total = {crore(prov)}"],
      "Doubtful provision = Secured portion × age rate + Unsecured portion × 100%",
      "Split doubtful assets into secured and unsecured portions.",
      verify_fact=True, ref=IRAC + " — provisioning rates stated in stem")

    pbp, addl_p, inc_g, addl_g = 800e7, 90e7, 1000e7, 120e7
    A(NPA, "L2",
      f"After RBI's annual supervisory assessment of a listed bank: reported profit before provisions and contingencies = {crore(pbp,0)}; additional provisioning assessed by RBI = {crore(addl_p,0)}; published incremental gross NPAs for the year = {crore(inc_g,0)}; additional gross NPAs identified by RBI = {crore(addl_g,0)}. Under RBI's divergence-disclosure norms (thresholds: 10% of reported profit before provisions and contingencies; 15% of published incremental GNPAs), the bank:",
      f"Must disclose: extra provisioning ({pct(addl_p/pbp)}) exceeds 10%, though extra GNPA ({pct(addl_g/inc_g,0)}) is within 15%",
      [("Need not disclose, because both the thresholds must be breached together in a year", "the tests are alternative (and/or), not cumulative"),
       (f"Must disclose, because the extra GNPA ({pct(addl_g/inc_g,0)}) exceeds the 10% threshold for GNPA", "10% threshold misapplied to GNPA divergence (GNPA test is 15%)"),
       ("Need not disclose, as divergence disclosure applies only if net profit turns into a loss", "that is not the trigger; loss-turn is only one of the listed disclosure items")],
      [f"Additional provisioning ÷ profit before provisions = {inr(addl_p/1e7)} ÷ {inr(pbp/1e7)} = {pct(addl_p/pbp)} > 10% ⇒ trigger",
       f"Additional GNPA ÷ incremental GNPA = {pct(addl_g/inc_g,0)} ≤ 15%",
       "Either condition triggers disclosure in notes to accounts."],
      "Disclose if ΔProv > 10% of PBP&C OR ΔGNPA > 15% of incremental GNPA",
      "The two thresholds are alternatives.", verify_fact=True,
      ref="RBI circular on divergence in asset classification and provisioning (April 2019) — thresholds stated in stem")

    # ================= BANK ADVANCES =================
    A(ADV, "L1",
      "Match the credit facility (List I) with its description (List II):\n\n"
      + table(["List I", "List II"],
              [["P. Cash credit", "1. Running account in which a current-account holder may overdraw up to a sanctioned limit, often against collateral such as FDs"],
               ["Q. Overdraft", "2. Revolving limit against hypothecation/pledge of stock and book debts, drawable within drawing power"],
               ["R. Bill discounting", "3. Bank pays the present value of a usance bill and collects the full amount at maturity"],
               ["S. Letter of credit", "4. Bank's undertaking to pay the beneficiary against complying documents"]], ["---", "---"]) + "\n\nCodes:",
      "P-2, Q-1, R-3, S-4",
      [("P-1, Q-2, R-3, S-4", "cash credit and overdraft descriptions swapped"),
       ("P-2, Q-1, R-4, S-3", "bill discounting confused with a documentary credit"),
       ("P-2, Q-3, R-1, S-4", "overdraft confused with bill finance")],
      ["Cash credit: working-capital limit secured by current assets, subject to drawing power.",
       "Overdraft: overdrawing a current account up to a limit.",
       "Bill discounting: bank advances discounted value of a trade bill.",
       "LC: non-fund-based undertaking."], "—", "Drawing power is the hallmark of cash credit.", kind="match")

    bill, days, rate, comm = 5e5, 60, 0.10, 0.0025
    disc = bill * rate * days / 365
    net = bill - disc - bill * comm
    A(ADV, "L2",
      f"A bank discounts a trade bill of {R(bill)} with {days} days to maturity at {pct(rate,0)} p.a. (Actual/365) and charges a collection commission of {pct(comm)} of the bill amount. The net amount credited to the customer is:",
      R(net),
      [(R(bill - bill * rate * days / 360 - bill * comm), "360-day year used"),
       (R(bill - disc), "commission ignored"),
       (R(bill / (1 + rate * days / 365) - bill * comm), "true discount (PV basis) used instead of banker's discount on face")],
      [f"Discount = {R(bill)} × 10% × 60/365 = {R(disc)}",
       f"Commission = {R(bill*comm)}",
       f"Net = {R(bill)} − {R(disc)} − {R(bill*comm)} = {R(net)}"],
      "Banker's discount = Face × r × t", "Banks deduct discount on the face value of the bill.")

    bals = [(8, 1200000), (10, 1850000), (7, 900000), (5, 1600000)]
    r_od = 0.115
    prod = sum(d * b for d, b in bals)
    intr = prod * r_od / 365
    days_t = sum(d for d, _ in bals)
    avg_simple = sum(b for _, b in bals) / 4
    A(ADV, "L3",
      "An overdraft account shows the following debit balances during a 30-day month (interest at 11.5% p.a. on daily products, Actual/365):\n\n"
      + table(["Period (days)", "Debit balance (₹)"], [[str(d), inr(b)] for d, b in bals]) +
      "\n\nThe interest debited for the month is:",
      R(intr),
      [(R(avg_simple * r_od * 30 / 365), "simple average of balances used, ignoring days"),
       (R(max(b for _, b in bals) * r_od * 30 / 365), "interest on the peak balance"),
       (R(prod * r_od / 360), "360-day year used")],
      ["Products = " + " + ".join(f"{d}×{inr(b)}" for d, b in bals) + f" = {inr(prod)}",
       f"Interest = {inr(prod)} × 11.5% ÷ 365 = {R(intr)}"],
      "Interest = Σ(balance × days) × r ÷ 365", "Weight each balance by the days it was outstanding.")

    # ================= BR ACT =================
    A(BRA, "L1",
      "Under Section 35A of the Banking Regulation Act, 1949, the Reserve Bank of India may issue directions to banking companies when it is satisfied that it is necessary:",
      "In public interest or banking policy, to stop affairs being run against depositors' or the bank's interest, or to secure proper management",
      [("Only on a reference from the Central Government under Section 45, after a moratorium has first been declared on the bank concerned", "s.35A is RBI's own power; s.45 deals with moratorium/reconstruction"),
       ("Only to fix the rate of interest payable on deposits of scheduled banks, and for no other purpose whatsoever under the Act", "interest-rate directions are only one application of s.21/s.35A, not the test"),
       ("Only after obtaining the prior approval of the Financial Stability and Development Council, chaired by the Union Finance Minister", "FSDC is a non-statutory coordination body with no such role")],
      ["s.35A(1) lists the grounds: public interest, banking policy, protection of depositors/bank, proper management.",
       "Directions are binding; RBI may modify or cancel them."], "—",
      "s.35A is a broad, self-standing RBI power.", kind="conceptual", verify_fact=True, ref="Banking Regulation Act 1949, s.35A")

    A(BRA, "L2",
      "Consider the following statements:\n\n"
      "1. No company can carry on banking business in India without a licence issued by the RBI under Section 22 of the Banking Regulation Act, 1949.\n"
      "2. For inclusion in the Second Schedule to the RBI Act, 1934, a bank must have paid-up capital and reserves of an aggregate value of not less than ₹5 lakh and satisfy the RBI that its affairs are not conducted detrimentally to depositors.\n"
      "3. Section 24 of the Banking Regulation Act prescribes a statutory floor of 25% of NDTL for SLR.\n\nWhich of the statements given above is/are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "the 25% SLR floor was removed by the 2007 amendment; only a 40% ceiling remains"),
       ("1 only", "statement 2 correctly states the s.42(6) RBI Act criteria"),
       ("2 and 3 only", "statement 1 correctly states the licensing requirement")],
      ["s.22 BR Act: licence from RBI mandatory — correct.",
       "s.42(6)(a) RBI Act: ₹5 lakh paid-up capital + reserves and depositor-interest test — correct.",
       "s.24 now only sets a ceiling (40%); no floor — incorrect."],
      "—", "Old SLR floor of 25% no longer exists.", kind="statement", verify_fact=True,
      ref="BR Act 1949 ss.22, 24 (as amended 2007); RBI Act 1934 s.42(6)")

    A(BRA, "L2",
      "Match the provision of the Banking Regulation Act, 1949 (List I) with its subject (List II):\n\n"
      + table(["List I", "List II"],
              [["P. Section 5(b)", "1. Licensing of banking companies"],
               ["Q. Section 22", "2. Definition of 'banking'"],
               ["R. Section 35A", "3. RBI may apply to the Central Government for a moratorium; scheme of reconstruction or amalgamation"],
               ["S. Section 45", "4. Power of the RBI to give directions"]], ["---", "---"]) + "\n\nCodes:",
      "P-2, Q-1, R-4, S-3",
      [("P-1, Q-2, R-4, S-3", "definition and licensing sections swapped"),
       ("P-2, Q-1, R-3, S-4", "direction power and moratorium section swapped"),
       ("P-2, Q-4, R-1, S-3", "licensing confused with directions")],
      ["s.5(b): banking = accepting deposits of money from the public for lending/investment, repayable on demand or otherwise, withdrawable by cheque, draft or otherwise.",
       "s.22 licensing; s.35A directions; s.45 moratorium and reconstruction/amalgamation."], "—",
      "s.45 (not s.44A) is the compulsory reconstruction route.", kind="match", verify_fact=True,
      ref="Banking Regulation Act 1949, ss.5(b), 22, 35A, 45")

    # ================= BASEL =================
    A(BAS, "L1",
      "Under RBI's Basel III capital regulations, the minimum Common Equity Tier 1 ratio a bank must maintain INCLUDING the capital conservation buffer (and excluding any D-SIB surcharge or countercyclical buffer) is:",
      "8.0% of risk-weighted assets",
      [("5.5% of risk-weighted assets", "CET1 minimum without the conservation buffer"),
       ("7.0% of risk-weighted assets", "BCBS global CET1 + CCB (4.5% + 2.5%)"),
       ("11.5% of risk-weighted assets", "total capital + CCB, not CET1")],
      ["RBI CET1 minimum = 5.5%; CCB = 2.5% (in CET1).",
       "CET1 + CCB = 8.0%; Tier 1 minimum 7%; total capital 9% (+ CCB = 11.5%)."],
      "CET1 + CCB = 5.5% + 2.5%", "RBI's minima are stricter than BCBS (4.5%/6%/8%).",
      verify_fact=True, ref=BASEL)

    A(BAS, "L1",
      "Match the Basel pillar (List I) with its content (List II):\n\n"
      + table(["List I", "List II"],
              [["P. Pillar 1", "1. Disclosure requirements to promote market discipline"],
               ["Q. Pillar 2", "2. Minimum capital for credit, market and operational risk"],
               ["R. Pillar 3", "3. Supervisory review, including the bank's ICAAP"]], ["---", "---"]) + "\n\nCodes:",
      "P-2, Q-3, R-1",
      [("P-2, Q-1, R-3", "supervisory review and disclosure swapped"),
       ("P-3, Q-2, R-1", "minimum capital and supervisory review swapped"),
       ("P-1, Q-3, R-2", "pillar order reversed for 1 and 3")],
      ["Pillar 1: minimum capital requirements.", "Pillar 2: SREP/ICAAP.", "Pillar 3: market discipline via disclosures."],
      "—", "ICAAP belongs to Pillar 2.", kind="match")

    cet1, at1, t2 = 5400e7, 900e7, 1500e7
    rc, rm, ro = 60000e7, 5000e7, 7000e7
    rwa = rc + rm + ro
    crar = (cet1 + at1 + t2) / rwa
    A(BAS, "L2",
      f"A bank reports CET1 capital {crore(cet1,0)}, Additional Tier 1 {crore(at1,0)} and Tier 2 {crore(t2,0)} (all eligible). Risk-weighted assets are: credit {crore(rc,0)}, market {crore(rm,0)} and operational {crore(ro,0)}. Its CRAR is:",
      pct(crar),
      [(pct((cet1 + at1 + t2) / rc), "only credit RWA used as denominator"),
       (pct((cet1 + at1) / rwa), "Tier 1 ratio reported instead of CRAR"),
       (pct((cet1 + at1 + t2) / (rc + rm)), "operational risk RWA omitted")],
      [f"Total capital = {crore(cet1+at1+t2,0)}", f"Total RWA = {crore(rwa,0)}", f"CRAR = {pct(crar)}"],
      "CRAR = (Tier 1 + Tier 2) ÷ (Credit + Market + Operational RWA)", "All three risk categories enter the denominator.")

    exp = [("Claims on the Government of India", 2000, 1.0, 0.0),
           ("Claims on scheduled banks", 800, 1.0, 0.20),
           ("Rated corporate loans", 1500, 1.0, 0.50),
           ("Regulatory retail portfolio", 1000, 1.0, 0.75),
           ("Undrawn committed lines (off-balance sheet)", 600, 0.20, 1.00),
           ("Financial guarantees issued (off-balance sheet)", 400, 1.00, 1.00)]
    rwa_c = sum(a * c * w for _, a, c, w in exp)
    w_noccf = sum(a * w for _, a, c, w in exp)
    w_onbs = sum(a * c * w for n, a, c, w in exp if "off" not in n)
    w_gov = rwa_c + 2000 * 0.0 + 800 * (1.0 - 0.20)
    A(BAS, "L3",
      "Compute credit risk-weighted assets (₹ crore) from the following, using the CCFs and risk weights given:\n\n"
      + table(["Exposure", "Amount (₹ cr)", "CCF", "Risk weight"], [[n, inr(a), pct(c, 0), pct(w, 0)] for n, a, c, w in exp]) + "\n\nCredit RWA is:",
      f"₹{inr(rwa_c)} crore",
      [(f"₹{inr(w_noccf)} crore", "credit conversion factors ignored for off-balance-sheet items"),
       (f"₹{inr(w_onbs)} crore", "off-balance-sheet exposures left out"),
       (f"₹{inr(w_gov)} crore", "claims on banks taken at 100% risk weight")],
      ["On-B/S: 0 + 800×20% + 1500×50% + 1000×75% = " + inr(w_onbs),
       f"Off-B/S: 600×20%×100% + 400×100%×100% = {inr(600*0.2+400)}",
       f"Total = ₹{inr(rwa_c)} crore"],
      "RWA = Exposure × CCF × Risk weight", "Convert off-balance-sheet items to credit equivalents first.")

    t1, t2x, gp, rc2, ro2 = 7200e7, 900e7, 1100e7, 64000e7, 12000e7
    cap = 0.0125 * rc2
    t2e = t2x + min(gp, cap)
    crar2 = (t1 + t2e) / (rc2 + ro2)
    A(BAS, "L3",
      f"A bank has Tier 1 capital of {crore(t1,0)}, Tier 2 instruments of {crore(t2x,0)} and general provisions/floating provisions of {crore(gp,0)} available for Tier 2. Credit RWA are {crore(rc2,0)}; market and operational RWA together are {crore(ro2,0)}. Given that general provisions count in Tier 2 only up to 1.25% of credit RWA, the CRAR is:",
      pct(crar2),
      [(pct((t1 + t2x + gp) / (rc2 + ro2)), "general provisions included without the 1.25% cap"),
       (pct((t1 + t2x + 0.0125 * (rc2 + ro2)) / (rc2 + ro2)), "1.25% cap applied to total RWA instead of credit RWA"),
       (pct((t1 + t2x) / (rc2 + ro2)), "general provisions excluded altogether")],
      [f"Cap = 1.25% × {crore(rc2,0)} = {crore(cap,0)}; eligible = {crore(min(gp,cap),0)}",
       f"Total capital = {crore(t1,0)} + {crore(t2x,0)} + {crore(min(gp,cap),0)} = {crore(t1+t2e,0)}",
       f"CRAR = {crore(t1+t2e,0)} ÷ {crore(rc2+ro2,0)} = {pct(crar2)}"],
      "Eligible GP in Tier 2 = min(GP, 1.25% × credit RWA)", "The cap is on credit RWA only.",
      verify_fact=True, ref=BASEL + " — Tier 2 eligibility of general provisions")

    # ================= LEVERAGE / D-SIB =================
    A(LEV, "L1",
      "Under RBI's leverage ratio framework, the minimum leverage ratio prescribed for Domestic Systemically Important Banks (D-SIBs) and for other scheduled commercial banks respectively is:",
      "4.0% and 3.5%",
      [("3.0% and 3.0%", "BCBS minimum applied to all banks"),
       ("3.5% and 4.0%", "values interchanged"),
       ("4.5% and 4.0%", "CET1 floor of BCBS confused with leverage ratio")],
      ["RBI (June 2019): leverage ratio ≥ 4% for D-SIBs and ≥ 3.5% for other banks.",
       "Leverage ratio = Tier 1 capital ÷ Exposure measure."], "—",
      "India's leverage ratio floor is above the Basel 3% minimum.", verify_fact=True, ref=BASEL)

    t1, onb, der, sft, offb = 12000e7, 280000e7, 6000e7, 4000e7, 20000e7
    em = onb + der + sft + offb
    lr = t1 / em
    A(LEV, "L2",
      f"A bank has Tier 1 capital of {crore(t1,0)}. Its exposure measure comprises on-balance-sheet exposures {crore(onb,0)}, derivative exposures {crore(der,0)}, securities financing transaction exposures {crore(sft,0)} and off-balance-sheet items (after CCFs) {crore(offb,0)}. Its leverage ratio is:",
      pct(lr),
      [(pct(t1 / onb), "only on-balance-sheet exposures used"),
       (pct(t1 / (onb + der + sft)), "off-balance-sheet items omitted"),
       (pct(t1 / (em - offb + offb * 5)), "off-balance-sheet items grossed up to notional (CCF reversed)")],
      [f"Exposure measure = {crore(em,0)}", f"Leverage ratio = {crore(t1,0)} ÷ {crore(em,0)} = {pct(lr)}"],
      "Leverage ratio = Tier 1 ÷ (On-B/S + Derivatives + SFT + Off-B/S after CCF)",
      "Unlike CRAR, exposures are not risk-weighted.")

    A(LEV, "L2",
      "Consider the following statements about RBI's D-SIB framework:\n\n"
      "1. Banks identified as D-SIBs must hold an additional Common Equity Tier 1 surcharge over and above the capital conservation buffer.\n"
      "2. D-SIBs are placed in buckets according to their systemic importance scores, and a higher bucket attracts a higher surcharge.\n"
      "3. The D-SIB surcharge substitutes for the capital conservation buffer, so a D-SIB need not maintain CCB.\n\nWhich of the statements given above is/are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "surcharge is additional to CCB, not a substitute"),
       ("2 only", "statement 1 is correct — surcharge is in CET1"),
       ("1 and 3 only", "statements 1 and 3 contradict each other")],
      ["Surcharge (0.20% to 1.00% of RWA by bucket) is in CET1, over and above CCB.",
       "Bucket placement is by systemic importance score.",
       "Statement 3 is incorrect."], "—", "Buffers stack: minimum + CCB + D-SIB surcharge (+ CCyB).",
      kind="statement", verify_fact=True, ref=BASEL)

    # ================= BUSINESS CORRESPONDENTS =================
    A(BC, "L1",
      "Consider the following statements about the Business Correspondent (BC) model:\n\n"
      "1. The bank remains fully responsible for the acts and omissions of its BCs.\n"
      "2. BCs may undertake cash-in/cash-out transactions on behalf of the bank, while Business Facilitators may not handle cash.\n"
      "3. A BC may levy its own service charges directly on customers without the bank's involvement.\n\nWhich of the statements given above is/are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "BCs cannot charge customers directly; charges are levied by the bank"),
       ("2 only", "statement 1 is a core RBI condition"),
       ("1 and 3 only", "statement 3 is contrary to RBI guidelines")],
      ["The bank is the principal and responsible for its BC agents.",
       "BCs handle cash and small-value transactions; BFs only facilitate (no cash).",
       "Customers pay the bank's (reasonable, disclosed) charges, not BC-levied charges."], "—",
      "BC = agent of the bank; the bank bears the liability.", kind="statement", verify_fact=True,
      ref="RBI circulars on financial inclusion — BC/BF model (2006 onwards)")

    A(BC, "L2",
      "**Assertion (A):** Payments banks and small finance banks can use Business Correspondents to extend their reach.\n\n"
      "**Reason (R):** RBI permits only individuals, and not companies, to act as Business Correspondents.\n\nChoose the correct option:",
      "Only A is true; R is a false statement of fact",
      [("Both A and R are true, and R correctly explains A", "R is false — for-profit companies incl. non-deposit-taking NBFCs may be BCs"),
       ("Both A and R are true, but R does not explain A", "R is false"),
       ("Only R is true; A is a false statement of fact", "A is true; differentiated banks rely heavily on BC/agent networks")],
      ["A: payments/small finance banks may engage BCs — true.",
       "R: RBI permitted for-profit companies as BCs (2010) and later non-deposit-taking NBFCs (2014) — false."],
      "—", "Corporate BCs are allowed.", kind="assertion-reason", verify_fact=True, ref="RBI BC guidelines (2010 revision)")

    # ================= CD =================
    A(CD, "L1",
      "As per RBI directions, certificates of deposit (CDs) issued by scheduled commercial banks have a minimum denomination and maturity of:",
      "₹5 lakh and multiples; maturity 7 days to one year",
      [("₹1 lakh and multiples; maturity 7 days to one year", "old/incorrect denomination"),
       ("₹5 lakh and multiples; maturity 1 year to 3 years", "maturity band for CDs issued by AIFIs, not banks"),
       ("₹25 lakh and multiples; maturity 15 days to one year", "neither denomination nor minimum tenor is correct")],
      ["Banks: 7 days to 1 year; AIFIs: 1 to 3 years.",
       "Minimum ₹5 lakh and multiples of ₹5 lakh; issued in demat form."], "—",
      "Tenor bands differ for banks and AIFIs.", verify_fact=True,
      ref="RBI (Certificate of Deposit) Directions, 2021")

    fv, d, y = 5e7, 182, 0.0725
    price = fv / (1 + y * d / 365)
    A(CD, "L2",
      f"A bank issues a {d}-day CD of face value {crore(fv,0)} at a yield of {pct(y)} (Actual/365, money-market yield). The issue price is:",
      R(price),
      [(R(fv * (1 - y * d / 365)), "discount-rate (bank discount) method applied to face"),
       (R(fv / (1 + y * d / 360)), "360-day year used"),
       (R(fv / (1 + y * d / 364)), "T-bill 364-day convention used")],
      [f"Price = {inr(fv)} ÷ (1 + 0.0725 × 182/365) = {R(price)}"],
      "P = F ÷ (1 + y × d/365)", "CD yields are quoted on price, not face.")

    fv, d0, y0, dh, y1 = 1e7, 364, 0.0760, 91, 0.0715
    p0 = fv / (1 + y0 * d0 / 365)
    p1 = fv / (1 + y1 * (d0 - dh) / 365)
    hpr = (p1 / p0 - 1) * 365 / dh
    A(CD, "L3",
      f"A mutual fund buys a fresh {d0}-day CD (face {crore(fv,0)}) at a yield of {pct(y0,2)} and sells it after {dh} days when the yield for the remaining tenor is {pct(y1,2)}. Both yields are Actual/365 money-market yields. The fund's annualised holding-period return is closest to:",
      pct(hpr),
      [(pct(y0), "purchase yield taken as realised return"),
       (pct(y0 + (y0 - y1)), "yield change added one-for-one to purchase yield (duration ignored)"),
       (pct((fv / (1 + y1 * d0 / 365) / p0 - 1) * 365 / dh), "sale price computed on the full original tenor")],
      [f"Buy price = {R(p0)}", f"Sale price (273 days left) = {R(p1)}",
       f"HPR = ({inr(p1)} ÷ {inr(p0)} − 1) × 365/91 = {pct(hpr)}"],
      "HPR(ann.) = (P₁/P₀ − 1) × 365/d", "A fall in yields gives a capital gain on top of accrual.")

    # ================= CP =================
    A(CP, "L1",
      "Consider the following statements regarding commercial paper (CP) under RBI's 2024 directions on CPs and short-term NCDs:\n\n"
      "1. Eligible issuers include companies, NBFCs and LLPs having a net worth of ₹100 crore or more.\n"
      "2. CP may be issued with a tenor from 7 days up to one year, in minimum denominations of ₹5 lakh and multiples thereof.\n"
      "3. CPs may be underwritten or co-accepted by banks to enhance marketability.\n\nWhich of the statements given above is/are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "underwriting/co-acceptance of CPs is prohibited"),
       ("2 only", "statement 1 correctly states the net-worth criterion"),
       ("2 and 3 only", "statement 3 is prohibited; statement 1 is correct")],
      ["Net worth ≥ ₹100 crore (plus minimum credit rating) — correct.",
       "Tenor 7 days–1 year; ₹5 lakh denomination — correct.",
       "Issuance cannot be underwritten or co-accepted — incorrect."], "—",
      "The old ₹4 crore tangible-net-worth test is no longer the criterion.", kind="statement", verify_fact=True,
      ref="RBI (Commercial Paper and Non-Convertible Debentures of original or initial maturity up to one year) Directions, 2024")

    fv, P, d, costs = 50e7, 98.30, 91, 6e5
    net = fv * P / 100 - costs
    eff = (fv - net) / net * 365 / d
    A(CP, "L2",
      f"A company issues 91-day CP of face value {crore(fv,0)} at a price of ₹{P:.2f} per ₹100. Rating, IPA and stamp-duty costs total {L(costs)}, paid upfront. The effective annualised cost of funds (Actual/365) is closest to:",
      pct(eff),
      [(pct((100 - P) / P * 365 / d), "issue costs ignored"),
       (pct(((100 - P) / 100 + costs / fv) * 365 / d), "discount computed on face value (discount rate) instead of net proceeds"),
       (pct(((fv - net) / net) * 360 / d), "360-day year used")],
      [f"Net proceeds = {crore(fv,0)} × 98.30% − {L(costs)} = {R(net)}",
       f"Cost = ({inr(fv)} − {inr(net)}) ÷ {inr(net)} × 365/91 = {pct(eff)}"],
      "Effective cost = (Face − Net proceeds)/Net proceeds × 365/d", "Base the cost on the money actually received.")

    fv, P = 1e7, 97.95
    y = (100 - P) / P * 365 / 120
    A(CP, "L2",
      f"A 120-day CP is purchased at ₹{P:.2f} per ₹100 of face value. The money-market yield to the investor (Actual/365) is:",
      pct(y),
      [(pct((100 - P) / 100 * 365 / 120), "discount on face (discount rate) instead of yield on price"),
       (pct((100 - P) / P * 364 / 120), "T-bill 364-day basis used"),
       (pct((100 - P) / P), "not annualised")],
      [f"Yield = ({100-P:.2f} ÷ {P:.2f}) × 365/120 = {pct(y)}"],
      "y = (F − P)/P × 365/d", "Annualise on 365 days for CP.")

    # ================= CALL / NOTICE / TERM =================
    A(CM, "L1",
      "In the Indian money market, funds lent for a period of 2 to 14 days are classified as:",
      "Notice money",
      [("Call money", "call money is overnight (one day, or over holidays)"),
       ("Term money", "term money is 15 days to one year"),
       ("Tri-party repo", "TREPS is a collateralised segment defined by instrument, not tenor")],
      ["Call: overnight; notice: 2–14 days; term: 15 days–1 year (uncollateralised interbank)."], "—",
      "Tenor, not collateral, separates call/notice/term.", verify_fact=True, ref="RBI Call, Notice and Term Money Market directions")

    amt, r, d = 75e7, 0.0645, 14
    intr = amt * r * d / 365
    A(CM, "L2",
      f"Bank A lends {crore(amt,0)} to Bank B in the notice money market for {d} days at {pct(r)}. Interest receivable at maturity (Actual/365) is:",
      R(intr),
      [(R(amt * r * d / 360), "360-day year used"),
       (R(amt * r * 15 / 365), "maturity counted inclusively as 15 days"),
       (R(amt * r / 365), "interest for one day (call convention) only")],
      [f"Interest = {inr(amt)} × 6.45% × 14/365 = {R(intr)}"],
      "I = P × r × d/365", "Money-market interest in India is on Actual/365.")

    cf = 4000e7
    A(CM, "L3",
      f"A scheduled commercial bank's capital funds (Tier 1 + Tier 2) at the end of the previous financial year were {crore(cf,0)}. Under RBI's prudential limits for the call/notice money market (borrowing: 100% of capital funds on a fortnightly average, 125% on any day; lending: 25% on a fortnightly average, 50% on any day), the maximum the bank may LEND on any single day is:",
      crore(0.50 * cf, 0),
      [(crore(0.25 * cf, 0), "fortnightly-average lending limit applied to a single day"),
       (crore(1.25 * cf, 0), "daily borrowing limit applied to lending"),
       (crore(1.00 * cf, 0), "average borrowing limit applied to lending")],
      ["Lending: average 25%, peak day 50% of capital funds.", f"50% × {crore(cf,0)} = {crore(0.5*cf,0)}"],
      "Max daily lending = 50% × capital funds", "Distinguish average and single-day limits.",
      verify_fact=True, ref="RBI Master Direction — Money Market Instruments: Call/Notice Money Market Operations (prudential limits)")

    # ================= CTS =================
    A(CTS, "L1",
      "In the Cheque Truncation System (CTS), clearing of a cheque is effected by:",
      "Electronic transmission of the cheque image and MICR data via the clearing house, while the presenting bank retains the physical instrument",
      [("Physical movement of the cheque to the drawee branch for signature verification, followed by electronic net settlement of funds", "physical movement is what truncation eliminates"),
       ("Conversion of the cheque into a UPI collect request that NPCI debits in real time from the drawer's account at the drawee bank", "CTS is an image-based clearing system, not UPI"),
       ("Real-time gross settlement of each cheque individually through RTGS once the drawee bank has verified the physical instrument", "CTS settles on a net basis in clearing sessions")],
      ["Truncation stops the flow of the physical cheque at the presenting bank.",
       "Images + MICR data are sent via the clearing house (NPCI grid).",
       "Physical instrument is retained for the prescribed period."], "—",
      "Image-based clearing ≠ RTGS.", kind="conceptual")

    A(CTS, "L2",
      "Consider the following statements:\n\n"
      "1. Under the Positive Pay System, banks enable the facility for all account holders issuing cheques of ₹50,000 and above, and may make it mandatory for cheques of ₹5 lakh and above.\n"
      "2. Cheques in India are valid for a period of three months from the date of the instrument.\n"
      "3. CTS instruments must conform to the CTS-2010 standard.\n\nWhich of the statements given above is/are correct?",
      "1, 2 and 3",
      [("1 and 2 only", "CTS-2010 standard compliance is required for cheques cleared in CTS"),
       ("2 and 3 only", "statement 1 correctly reflects the PPS thresholds"),
       ("1 and 3 only", "validity was reduced to three months by RBI (2012)")],
      ["PPS (from 1 January 2021): enabled for ≥ ₹50,000; banks may mandate for ≥ ₹5 lakh.",
       "Validity three months (RBI, April 2012).",
       "CTS-2010 standard with security features."], "—", "All three are current RBI rules.",
      kind="statement", verify_fact=True, ref="RBI circulars: Positive Pay System (Sept 2020); cheque validity (Nov 2011); CTS-2010 standards")

    # ================= DFIs =================
    A(DFI, "L1",
      "Match the institution (List I) with its primary mandate (List II):\n\n"
      + table(["List I", "List II"],
              [["P. NABARD", "1. Long-term infrastructure financing and development of bond/derivative markets for infrastructure"],
               ["Q. SIDBI", "2. Agriculture and rural development, incl. refinance and RIDF"],
               ["R. NHB", "3. Promotion and financing of MSMEs"],
               ["S. NaBFID", "4. Housing finance — refinance and supervision of housing finance companies"]], ["---", "---"]) + "\n\nCodes:",
      "P-2, Q-3, R-4, S-1",
      [("P-2, Q-4, R-3, S-1", "SIDBI and NHB mandates swapped"),
       ("P-1, Q-3, R-4, S-2", "NABARD and NaBFID mandates swapped"),
       ("P-3, Q-2, R-4, S-1", "NABARD and SIDBI mandates swapped")],
      ["NABARD (1982): agriculture/rural; RIDF.", "SIDBI (1990): MSMEs.", "NHB (1988): housing finance.", "NaBFID (2021): infrastructure."],
      "—", "NaBFID is the newest AIFI.", kind="match")

    A(DFI, "L2",
      "Consider the following statements:\n\n"
      "1. NABARD, SIDBI, NHB, EXIM Bank and NaBFID are regulated and supervised by the RBI as All India Financial Institutions.\n"
      "2. NaBFID was established under a dedicated Act of Parliament passed in 2021.\n"
      "3. NHB continues to be the regulator of housing finance companies.\n\nWhich of the statements given above is/are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "regulation of HFCs moved from NHB to RBI in August 2019 (NHB retains supervision/grievance functions)"),
       ("2 only", "statement 1 is correct — five AIFIs are under RBI"),
       ("1 and 3 only", "statement 3 is incorrect")],
      ["The five AIFIs are regulated by RBI — correct.",
       "National Bank for Financing Infrastructure and Development Act, 2021 — correct.",
       "Regulatory powers over HFCs were transferred to RBI (Finance (No.2) Act, 2019) — incorrect."], "—",
      "Regulation and supervision of HFCs are split after 2019.", kind="statement", verify_fact=True,
      ref="NaBFID Act 2021; Finance (No.2) Act 2019 amendments to NHB Act; RBI AIFI framework")

    A(DFI, "L1",
      "**Assertion (A):** Rural Infrastructure Development Fund (RIDF) resources are routed through NABARD to State Governments for rural infrastructure projects.\n\n"
      "**Reason (R):** Commercial banks deposit amounts equal to their shortfall in priority-sector lending targets into funds such as RIDF maintained with NABARD.\n\nChoose the correct option:",
      "Both A and R are true, and R correctly explains A",
      [("Both A and R are true, but R does not explain A", "PSL shortfall deposits are the source of RIDF corpus"),
       ("Only A is true; R is a false statement of fact", "R correctly describes PSL-shortfall allocation"),
       ("Only R is true; A is a false statement of fact", "RIDF loans are extended by NABARD to State Governments")],
      ["RIDF (1995–96) is funded by PSL-shortfall deposits of banks.",
       "NABARD lends these to States/State entities for rural infrastructure."], "—",
      "PSL shortfall → RIDF → State Governments.", kind="assertion-reason")

    # ================= EXPORT CREDIT =================
    A(EXP, "L1",
      "Which of the following is a POST-shipment export finance facility?",
      "Negotiation/discounting of export bills drawn under a letter of credit",
      [("Packing credit to purchase raw materials for an export order", "pre-shipment finance"),
       ("Advance against incentives receivable, granted before goods are manufactured", "timing is pre-shipment"),
       ("Running account packing credit", "pre-shipment finance")],
      ["Pre-shipment: packing credit (incl. running account), finance to procure/process goods.",
       "Post-shipment: purchase/discount/negotiation of export bills, advances against bills sent on collection."], "—",
      "The shipment date splits pre- and post-shipment finance.", kind="conceptual")

    usd, days, dr, fee, spot = 500000, 180, 0.065, 0.005, 84.60
    disc = usd * dr * days / 360
    proceeds = (usd - disc - usd * fee) * spot
    A(EXP, "L2",
      f"An exporter forfaits a USD {inr(usd)} avalised bill due in {days} days. The forfaiter charges a discount of {pct(dr,1)} p.a. (Actual/360, straight discount on face) and a commitment/handling fee of {pct(fee,1)} of face. At a spot rate of ₹{spot:.2f}, the exporter's INR proceeds are:",
      R(proceeds),
      [(R((usd - usd * dr * days / 365 - usd * fee) * spot), "Actual/365 used instead of the USD 360-day convention"),
       (R((usd - disc) * spot), "fee ignored"),
       (R((usd - usd * dr - usd * fee) * spot), "full annual discount charged for a 180-day bill")],
      [f"Discount = 500,000 × 6.5% × 180/360 = USD {disc:,.0f}", f"Fee = USD {usd*fee:,.0f}",
       f"Net = USD {usd-disc-usd*fee:,.0f} × {spot} = {R(proceeds)}"],
      "Proceeds = [Face − Face×d×t/360 − Fee] × Spot", "USD money-market discounting uses a 360-day year.")

    sales, adv, dchg, sfee, admin, bd = 24e7, 0.80, 0.12, 0.01, 18e5, 0.005
    dso = 90
    recv = sales * dso / 360
    cost = recv * adv * dchg + sales * sfee
    save = admin + sales * bd
    netc = cost - save
    A(EXP, "L3",
      f"An exporter with annual credit sales of {crore(sales,0)} and a 90-day collection period (360-day year) considers without-recourse export factoring: the factor advances {pct(adv,0)} of receivables at {pct(dchg,0)} p.a. and charges a service fee of {pct(sfee,0)} of sales. Factoring would save sales-ledger costs of {L(admin)} p.a. and eliminate bad debts of {pct(bd,1)} of sales. The NET annual cost of factoring is closest to:",
      L(netc),
      [(L(cost), "savings in admin cost and bad debts ignored"),
       (L(recv * dchg + sales * sfee - save), "interest charged on 100% of receivables instead of the advance"),
       (L(recv * adv * dchg + recv * sfee - save), "service fee applied to receivables instead of annual sales")],
      [f"Average receivables = {crore(sales,0)} × 90/360 = {crore(recv)}",
       f"Interest = {crore(recv)} × 80% × 12% = {L(recv*adv*dchg)}; fee = 1% × {crore(sales,0)} = {L(sales*sfee)}",
       f"Savings = {L(admin)} + {L(sales*bd)} = {L(save)}",
       f"Net cost = {L(cost)} − {L(save)} = {L(netc)}"],
      "Net cost = Interest on advance + Fee − (Admin + Bad-debt savings)", "Compare total factoring cost with costs avoided.")

    # ================= FBIL =================
    A(FB, "L1",
      "Consider the following statements about Financial Benchmarks India Pvt. Ltd. (FBIL):\n\n"
      "1. FBIL is jointly owned by FIMMDA, FEDAI and the Indian Banks' Association.\n"
      "2. FBIL publishes the overnight MIBOR and the USD/INR reference rate.\n"
      "3. FBIL is the statutory regulator of all interest-rate benchmarks in India under the RBI Act.\n\nWhich of the statements given above is/are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "FBIL is an administrator; RBI regulates benchmark administrators"),
       ("2 only", "statement 1 correctly states FBIL's ownership"),
       ("2 and 3 only", "statement 3 is incorrect")],
      ["FBIL (2014) is owned by FIMMDA, FEDAI and IBA.",
       "It administers MIBOR, USD/INR reference rate, T-bill/CD curves, G-sec valuations, MMIFOR etc.",
       "RBI regulates administrators under its Financial Benchmark Administrators Directions; FBIL is not a regulator."], "—",
      "Administrator ≠ regulator.", kind="statement", verify_fact=True,
      ref="RBI Financial Benchmark Administrators (Reserve Bank) Directions; FBIL constitution")

    A(FB, "L2",
      "**Assertion (A):** After the cessation of USD LIBOR, the Mumbai Interbank Forward Outright Rate (MIFOR) benchmark was replaced by a modified MIFOR that uses SOFR as the USD reference rate.\n\n"
      "**Reason (R):** MIFOR is derived from USD/INR forward premia and a USD interest rate, so it needed a new USD reference rate once LIBOR ceased.\n\nChoose the correct option:",
      "Both A and R are true, and R correctly explains A",
      [("Both A and R are true, but R does not explain A", "R is exactly why MIFOR had to be modified"),
       ("Only A is true; R is a false statement of fact", "R correctly describes MIFOR construction"),
       ("Only R is true; A is a false statement of fact", "FBIL did introduce MMIFOR based on SOFR")],
      ["MIFOR = implied INR rate from USD/INR forward premium + USD rate.",
       "LIBOR cessation (June 2023) ⇒ FBIL's Modified MIFOR (MMIFOR) uses SOFR."], "—",
      "Benchmark transition follows the underlying input.", kind="assertion-reason", verify_fact=True,
      ref="FBIL announcements on MMIFOR; RBI LIBOR transition circulars")

    # ================= CASE C2: BANK CAPITAL =================
    G = "FINA-CASE-BANKCAP"
    cet1, at1, t2i, gp = 9800e7, 1400e7, 1600e7, 1500e7
    rcr, rmk, rop = 96000e7, 8000e7, 12000e7
    em = 270000e7
    gadv, gnpa, provs = 110000e7, 4600e7, 3100e7
    surch = 0.004
    stim = ("**Case — Tapti Commercial Bank Ltd (fictional)** — identified by RBI as a D-SIB in bucket 2 (CET1 surcharge 0.40% of RWA). Figures as at 31 March (₹ crore):\n\n"
            + table(["Item", "₹ crore"],
                    [["CET1 capital (after regulatory adjustments)", inr(cet1 / 1e7)],
                     ["Additional Tier 1 instruments", inr(at1 / 1e7)],
                     ["Tier 2 instruments (eligible)", inr(t2i / 1e7)],
                     ["General/floating provisions", inr(gp / 1e7)],
                     ["Credit RWA", inr(rcr / 1e7)], ["Market RWA", inr(rmk / 1e7)], ["Operational RWA", inr(rop / 1e7)],
                     ["Leverage exposure measure", inr(em / 1e7)],
                     ["Gross advances", inr(gadv / 1e7)], ["Gross NPAs", inr(gnpa / 1e7)], ["Specific provisions held on NPAs", inr(provs / 1e7)]], ["---", "---:"]) +
            "\n\nAssume RBI minima: CET1 5.5%, CCB 2.5%, Tier 1 7%, total capital 9%; general provisions eligible in Tier 2 up to 1.25% of credit RWA; leverage ratio 4% for D-SIBs; CCyB nil.")
    rwa = rcr + rmk + rop
    gpe = min(gp, 0.0125 * rcr)
    crar = (cet1 + at1 + t2i + gpe) / rwa
    A(BAS, "L4", stim + "\n\nThe bank's CRAR is closest to:",
      pct(crar),
      [(pct((cet1 + at1 + t2i + gp) / rwa), "general provisions included without the 1.25% cap"),
       (pct((cet1 + at1 + t2i + gpe) / rcr), "only credit RWA in the denominator"),
       (pct((cet1 + at1 + t2i) / rwa), "general provisions excluded altogether")],
      [f"Eligible GP = min({inr(gp/1e7)}, 1.25% × {inr(rcr/1e7)} = {inr(0.0125*rcr/1e7)}) = {inr(gpe/1e7)}",
       f"Total capital = {inr((cet1+at1+t2i+gpe)/1e7)}; RWA = {inr(rwa/1e7)}", f"CRAR = {pct(crar)}"],
      "CRAR = Total capital ÷ Total RWA", "Cap GP at 1.25% of credit RWA.", group=G,
      verify_fact=True, ref=BASEL)

    req = 0.055 + 0.025 + surch
    surplus = cet1 - req * rwa
    A(BAS, "L4", stim + "\n\nThe bank's CET1 surplus over its total CET1 requirement (minimum + CCB + D-SIB surcharge) is closest to:",
      f"₹{inr(surplus/1e7)} crore",
      [(f"₹{inr((cet1 - 0.08*rwa)/1e7)} crore", "D-SIB surcharge omitted"),
       (f"₹{inr((cet1 - 0.055*rwa)/1e7)} crore", "only the 5.5% minimum considered (buffers ignored)"),
       (f"₹{inr((cet1 - req*rcr)/1e7)} crore", "requirement applied on credit RWA only")],
      [f"Requirement = (5.5 + 2.5 + 0.40)% = {pct(req)} of {inr(rwa/1e7)} = {inr(req*rwa/1e7)}",
       f"Surplus = {inr(cet1/1e7)} − {inr(req*rwa/1e7)} = {inr(surplus/1e7)}"],
      "CET1 requirement = (Min + CCB + D-SIB) × RWA", "The surcharge sits on top of CCB.", group=G,
      verify_fact=True, ref=BASEL)

    lr = (cet1 + at1) / em
    A(LEV, "L4", stim + "\n\nWith respect to the leverage ratio, the bank:",
      f"Meets the requirement: leverage ratio {pct(lr)} against 4%",
      [(f"Falls short: leverage ratio {pct(cet1/em)} against 4%", "CET1 used instead of Tier 1 capital"),
       (f"Meets the requirement: leverage ratio {pct((cet1+at1+t2i+gpe)/em)} against 3.5%", "total capital used, and non-D-SIB floor applied"),
       (f"Meets the requirement: leverage ratio {pct((cet1+at1)/rwa)} against 4%", "RWA used instead of exposure measure")],
      [f"Tier 1 = {inr((cet1+at1)/1e7)}; exposure = {inr(em/1e7)}", f"Leverage ratio = {pct(lr)} ≥ 4% (D-SIB floor)"],
      "Leverage ratio = Tier 1 ÷ Exposure measure", "Numerator is Tier 1, denominator is unweighted exposure.", group=G,
      verify_fact=True, ref=BASEL)
    assert lr >= 0.04 and cet1 / em < 0.04

    nnpa = (gnpa - provs) / (gadv - provs)
    A(NPA, "L4", stim + "\n\nThe bank's net NPA ratio is closest to:",
      pct(nnpa),
      [(pct((gnpa - provs) / gadv), "net NPAs divided by gross advances instead of net advances"),
       (pct(gnpa / gadv), "gross NPA ratio reported"),
       (pct((gnpa - provs) / (gadv - gnpa)), "gross NPAs (instead of provisions) deducted from advances in the denominator")],
      [f"Net NPA = {inr(gnpa/1e7)} − {inr(provs/1e7)} = {inr((gnpa-provs)/1e7)}",
       f"Net advances = {inr(gadv/1e7)} − {inr(provs/1e7)} = {inr((gadv-provs)/1e7)}",
       f"Net NPA ratio = {pct(nnpa)}"],
      "Net NPA % = (GNPA − Provisions) ÷ (Gross advances − Provisions)", "Deduct provisions from both numerator and denominator.", group=G)

    tgt = 0.75
    need = tgt * gnpa - provs
    A(NPA, "L4", stim + f"\n\nThe board sets an internal target provision coverage ratio (specific provisions ÷ GNPA, excluding technical write-offs) of {pct(tgt,0)}. The additional provision required, and its effect on CET1 (ignoring tax), are closest to:",
      f"₹{inr(need/1e7)} crore; CET1 ratio falls to {pct((cet1-need)/rwa)}",
      [(f"₹{inr((tgt*(gnpa-provs))/1e7)} crore; CET1 ratio falls to {pct((cet1-tgt*(gnpa-provs))/rwa)}", "target applied to net NPAs"),
       (f"₹{inr(need/1e7)} crore; CET1 ratio unchanged at {pct(cet1/rwa)}", "provisions charged to P&L do reduce CET1"),
       (f"₹{inr((tgt*gnpa)/1e7)} crore; CET1 ratio falls to {pct((cet1-tgt*gnpa)/rwa)}", "existing provisions not netted off")],
      [f"Present PCR = {inr(provs/1e7)} ÷ {inr(gnpa/1e7)} = {pct(provs/gnpa)}",
       f"Required provisions = 75% × {inr(gnpa/1e7)} = {inr(tgt*gnpa/1e7)}; additional = {inr(need/1e7)}",
       f"CET1 = {inr((cet1-need)/1e7)} ÷ {inr(rwa/1e7)} = {pct((cet1-need)/rwa)}"],
      "PCR = Provisions ÷ GNPA", "New provisions flow through profit and reduce CET1.", group=G)

    # ================= CASE C5: WORKING CAPITAL BORROWER =================
    G = "FINA-CASE-WC"
    rm, wip, fg, rec, rec_old, oca = 180e5, 60e5, 110e5, 220e5, 30e5, 30e5
    cred, ocl, core = 140e5, 40e5, 100e5
    ca = rm + wip + fg + rec + oca
    stim = ("**Case — Vindhya Auto Components Ltd (fictional)** — projected current assets and liabilities for next year (₹ lakh):\n\n"
            + table(["Current assets", "₹ lakh", "Current liabilities (other than bank borrowings)", "₹ lakh"],
                    [["Raw materials", inr(rm / 1e5), "Sundry creditors (for goods)", inr(cred / 1e5)],
                     ["Work-in-progress", inr(wip / 1e5), "Other current liabilities", inr(ocl / 1e5)],
                     ["Finished goods", inr(fg / 1e5), "", ""],
                     [f"Receivables (of which over 90 days: {inr(rec_old/1e5)})", inr(rec / 1e5), "", ""],
                     ["Other current assets", inr(oca / 1e5), "", ""],
                     ["**Total**", inr(ca / 1e5), "**Total**", inr((cred + ocl) / 1e5)]], ["---", "---:", "---", "---:"]) +
            f"\n\nCore current assets are estimated at ₹{inr(core/1e5)} lakh. The bank's cash-credit rate is 10.25% p.a.; it lends against stocks at 25% margin (after deducting creditors for goods) and against receivables up to 90 days at 40% margin.")
    m1 = 0.75 * (ca - cred - ocl)
    m2 = 0.75 * ca - (cred + ocl)
    m3 = 0.75 * (ca - core) - (cred + ocl)
    A(ADV, "L4", stim + "\n\nThe Maximum Permissible Bank Finance under the second method of lending (Tandon Committee) is:",
      L(m2),
      [(L(m1), "first method: 75% of working-capital gap"),
       (L(m3), "third method: core current assets excluded"),
       (L(0.75 * (ca - rec_old) - (cred + ocl)), "overdue receivables excluded from current assets (a DP adjustment, not MPBF)")],
      [f"Total CA = {L(ca)}; OCL = {L(cred+ocl)}",
       f"Method II: 75% × {L(ca)} − {L(cred+ocl)} = {L(m2)}"],
      "MPBF (II) = 0.75 × CA − OCL", "Borrower funds 25% of total current assets from long-term sources.", group=G)

    stock = rm + wip + fg
    dp = (stock - cred) * 0.75 + (rec - rec_old) * 0.60
    A(ADV, "L4", stim + "\n\nOn these figures, the drawing power available under the cash-credit limit (before comparing with the sanctioned limit) is:",
      L(dp),
      [(L(stock * 0.75 + (rec - rec_old) * 0.60), "creditors for goods not deducted from stock"),
       (L((stock - cred) * 0.75 + rec * 0.60), "receivables over 90 days included"),
       (L((stock - cred + rec - rec_old) * 0.75), "25% stock margin applied to receivables too")],
      [f"Stock = {L(stock)}; less creditors {L(cred)} = {L(stock-cred)}; × 75% = {L((stock-cred)*0.75)}",
       f"Eligible receivables = {L(rec-rec_old)} × 60% = {L((rec-rec_old)*0.6)}",
       f"DP = {L(dp)}"],
      "DP = (Stock − Creditors)(1 − m₁) + Eligible debtors(1 − m₂)", "Unpaid stock is financed by creditors, not the bank.", group=G)

    fv, P, d, costs, cc = 10e7, 98.25, 91, 1.5e5, 0.1025
    net = fv * P / 100 - costs
    eff = (fv - net) / net * 365 / d
    sav = net * (cc - eff) * d / 365
    A(CP, "L4", stim + f"\n\nThe company (net worth and rating eligible) plans to replace part of its cash credit with a 91-day CP of face {crore(fv,0)} issued at ₹{P:.2f}, with issue expenses of {L(costs)}. Compared with cash credit on the same net amount for 91 days, the CP route:",
      f"Saves about {L(sav)}; effective CP cost {pct(eff)}",
      [(f"Saves about {L(net*(cc-(100-P)/P*365/d)*d/365)}; effective CP cost {pct((100-P)/P*365/d)}", "issue expenses ignored"),
       (f"Saves about {L(fv*(cc-eff))}; effective CP cost {pct(eff)}", "saving computed for a full year on face value"),
       (f"Costs about {L(sav)} more; effective CP cost {pct(eff)}", "comparison direction reversed")],
      [f"Net proceeds = {R(net)}", f"Effective cost = {pct(eff)}",
       f"Saving = {R(net)} × ({pct(cc)} − {pct(eff)}) × 91/365 = {L(sav)}"],
      "Saving = Net funds × (r_CC − r_CP) × d/365", "Compare on the same amount and period.", group=G)
    assert eff < cc

    fob, marg, pcr, pdays = 4e7, 0.10, 0.085, 75
    pc = fob * (1 - marg)
    intr = pc * pcr * pdays / 365
    A(EXP, "L4", stim + f"\n\nVindhya also receives a confirmed export order (FOB {crore(fob,0)}). The bank sanctions packing credit with a {pct(marg,0)} margin at {pct(pcr,1)} p.a.; the advance is liquidated by export proceeds after {pdays} days. Interest on the packing credit is:",
      R(intr),
      [(R(fob * pcr * pdays / 365), "margin ignored — interest on full FOB value"),
       (R(pc * pcr * pdays / 360), "360-day year used"),
       (R(fob * marg * pcr * pdays / 365), "interest computed on the margin instead of the advance")],
      [f"Packing credit = {crore(fob,0)} × 90% = {crore(pc)}", f"Interest = {inr(pc)} × 8.5% × 75/365 = {R(intr)}"],
      "Interest = FOB × (1 − margin) × r × d/365", "The margin is the exporter's own stake.", group=G)
