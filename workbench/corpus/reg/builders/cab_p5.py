"""Part 5: L4 case sets."""
from cab_common import *  # noqa
import math


def add_all(B):
    # ================================================================== CASE 1 — dividend chain
    g = "CAB-CASE-1"
    pbd, dep, fvg, bfl = 14.20e7, 3.60e7, 0.85e7, 2.15e7
    shares = 4.5e7
    divp = pbd - dep - fvg - bfl
    assert round(divp) == 7.60e7
    decl = d(2026, 9, 18)
    stem = (
        "**Case — Vardhan Polymers Ltd** (listed; equity shares of ₹10 each, 4.5 crore shares fully paid)\n\n"
        + table(["FY 2025-26 (after tax)", "₹ crore"], [
            ["Profit before depreciation", "14.20"],
            ["Depreciation as per Schedule II", "3.60"],
            ["Unrealised fair-value gain on mutual fund units included in profit (net of tax)", "0.85"],
            ["Loss brought forward from FY 2024-25", "2.15"]], ["---", "---:"])
        + f"\n\nThe Board decides to transfer 10% of the distributable profit to general reserve and to distribute the rest as final dividend. "
          f"The dividend is declared at the AGM on {ds(decl)}. A portion of the dividend remains unpaid after the statutory period; one batch of dividend warrants was dispatched late.\n\n")
    B.add(M["s123"], "L4", stem + "The profit available for dividend for FY 2025-26 under s.123(1) is:",
          cr(divp),
          [(cr(divp + fvg), "unrealised fair-value gain not excluded"),
           (cr(divp + bfl), "brought-forward loss not set off"),
           (cr(pbd - fvg - bfl), "Schedule II depreciation not deducted")],
          [f"14.20 − 3.60 (depreciation) − 0.85 (unrealised gain) − 2.15 (b/f loss) = {cr(divp)}."],
          "Distributable = Profit − depreciation − unrealised gains − b/f losses",
          "Fair-value gains are excluded even if credited to P&L.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.123(1) provisos")

    dps = divp * 0.9 / shares
    B.add(M["s123"], "L4", stem + "The maximum dividend per equity share consistent with the Board's decision is:",
          f"₹{dps:.2f}",
          [(f"₹{divp/shares:.2f}", "10% transfer to reserve ignored"),
           (f"₹{(divp+bfl)*0.9/shares:.2f}", "brought-forward loss not set off before the 10% transfer"),
           (f"₹{(divp*0.9)/(shares*10)*100:.2f}", "amount per ₹100 of capital reported as per-share amount")],
          [f"Distributable {cr(divp)}; less 10% to general reserve = {cr(divp*0.9)}.",
           f"Per share = {inr(divp*0.9)} ÷ {inr(shares)} = ₹{dps:.2f} ({pct(dps/10,1)} of face value)."],
          "DPS = (Distributable − transfer to reserve) ÷ Number of shares",
          "Transfer to reserves is voluntary but, once decided, reduces the distributable amount.",
          kind="case", group=g, verify_fact=False, ref="Arithmetic on s.123 base; transfer to reserve per s.123(1) second proviso (voluntary)")

    dep5 = plus(decl, 5)
    due30 = plus(decl, 30)
    tr = plus(due30, 7)
    B.add(M["uda"], "L4", stem + "Counting days excluding the day of declaration, the latest dates for (i) depositing the dividend amount in a separate bank account and (ii) transferring the unpaid amount to the Unpaid Dividend Account are:",
          f"(i) {ds(dep5)}; (ii) {ds(tr)}",
          [(f"(i) {ds(plus(decl,7))}; (ii) {ds(tr)}", "7 days used for the separate-account deposit"),
           (f"(i) {ds(dep5)}; (ii) {ds(due30)}", "transfer deadline taken as the end of the 30-day payment period"),
           (f"(i) {ds(dep5)}; (ii) {ds(plus(decl,7))}", "7 days counted from declaration")],
          ["s.123(4): deposit in a scheduled bank in a separate account within 5 days of declaration.",
           f"s.127: pay within 30 days → {ds(due30)}; s.124(1): transfer unpaid within 7 days thereafter → {ds(tr)}."],
          "Deposit: D + 5; Payment: D + 30; Unpaid transfer: D + 37",
          "Three different clocks run from the date of declaration.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.123(4), s.124(1), s.127")

    un, late = 22e5, 20
    B.add(M["uda"], "L4", stem + f"The company transferred the unpaid amount of {R(un)} to the Unpaid Dividend Account {late} days after the due date. The interest payable under s.124(2) is (365-day year):",
          R(interest(un, 0.12, late)),
          [(R(interest(un, 0.18, late)), "s.127 rate of 18% applied"),
           (R(interest(un, 0.12, late + 7)), "interest counted from end of the 30-day payment period"),
           (R(un * 0.12 * late / 360), "360-day year used")],
          [f"Interest = {inr(un)} × 12% × {late}/365 = {R(interest(un,0.12,late))}; accrues to the shareholders."],
          "Interest = Amount × 12% × days/365", "s.124(2) rate is 12%.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.124(2)")

    bat, dl = 35e5, 16
    B.add(M["s127"], "L4", stem + f"A batch of warrants for {R(bat)} was posted {dl} days after the 30-day period expired, for no reason covered by the statutory exceptions. Which of the following is correct?",
          f"18% interest of {R(interest(bat,0.18,dl))}; directors knowingly party face imprisonment and fine",
          [(f"The company pays interest of {R(interest(bat,0.12,dl))} @ 12% p.a.; no personal liability arises for directors", "s.124(2) rate applied; personal liability ignored"),
           (f"The company pays interest of {R(interest(bat,0.18,dl+30))} @ 18% p.a. counted from declaration", "default period counted from declaration"),
           ("No interest is payable as the dividend was ultimately paid", "treats late payment as curing the default")],
          [f"s.127: interest @ 18% p.a. for the period of default = {inr(bat)} × 18% × {dl}/365 = {R(interest(bat,0.18,dl))}.",
           "Directors knowingly party: imprisonment up to 2 years and fine ≥ ₹1,000 per day of continuing default."],
          "Interest = Amount × 18% × days of default/365", "Late payment does not cure a s.127 default.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.127")

    # ================================================================== CASE 2 — s.186 + RPT
    g = "CAB-CASE-2"
    pu, fr, sp, rr = 80e7, 150e7, 20e7, 30e7
    exist, loan, guar = 132e7, 25e7, 18e7
    to, nw = 620e7, 250e7
    a = 0.6 * (pu + fr + sp)
    b = fr + sp
    lim = max(a, b)
    assert round(lim) == 170e7
    stem = (
        "**Case — Kaveri Cements Ltd** (listed; not an infrastructure, banking, insurance, housing-finance or NBFC company)\n\n"
        "Latest audited balance sheet (₹ crore): paid-up share capital 80; free reserves 150; securities premium 20; revaluation reserve 30. "
        "Turnover 620; net worth 250.\n\n"
        f"Existing aggregate of loans, guarantees, securities and investments covered by s.186(2): ₹132 crore. The Board now proposes (a) an inter-corporate loan of ₹25 crore for 7 years to an unrelated company and (b) a guarantee of ₹18 crore for a bank loan of another unrelated company.\n\n"
        "Separately, the following contracts are proposed with Sharma Traders, a firm in which the managing director's brother is a partner; none of them is both in the ordinary course of business and at arm's length:\n\n"
        + table(["Contract (during the year)", "Value"], [
            ["Purchase of packing material", "₹58 crore"], ["Lease of a warehouse (annual rent)", "₹7 crore"],
            ["Sale of surplus land", "₹27 crore"], ["Appointment of MD's son as General Manager", "₹3 lakh per month"]], ["---", "---:"])
        + "\n\nIndicative G-sec yields: 1-year 6.60%, 3-year 6.90%, 5-year 7.05%, 10-year 7.20%.\n\n")
    B.add(M["s186"], "L4", stem + "The s.186(2) limit for Kaveri and the headroom available before a special resolution is needed are, respectively:",
          f"{cr(lim,0)} and {cr(lim-exist,0)}",
          [(f"{cr(a,0)} and {cr(a-exist,0)}", "'whichever is less' applied — 60% limb taken"),
           (f"{cr(0.6*(pu+fr+sp+rr),0)} and {cr(0.6*(pu+fr+sp+rr)-exist,0)}", "revaluation reserve included in the 60% limb"),
           (f"{cr(0.6*(pu+fr),0)} and {cr(0.6*(pu+fr)-exist,0)}", "60% limb alone, with securities premium omitted")],
          [f"60% × (80 + 150 + 20) = {cr(a,0)}; 100% × (150 + 20) = {cr(b,0)}; limit = higher = {cr(lim,0)}.",
           f"Headroom = {cr(lim,0)} − {cr(exist,0)} = {cr(lim-exist,0)}."],
          "Limit = max[60% (PUC + FR + SP), 100% (FR + SP)]",
          "With large reserves the 100% limb can exceed the 60% limb.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.186(2)")

    tot_after = exist + loan + guar
    B.add(M["s186"], "L4", stem + "With respect to proposals (a) and (b), which of the following is correct?",
          f"Special resolution needed (aggregate {cr(tot_after,0)} > {cr(lim,0)}); Board approval only at a meeting",
          [(f"Only a unanimous Board resolution is needed, since each proposal individually is below the limit", "tests each proposal separately instead of the aggregate"),
           (f"Only the loan counts; guarantees are outside s.186, so aggregate {cr(exist+loan,0)} is within the limit", "guarantees wrongly excluded"),
           ("A special resolution is required, and the Board may pass its resolution by circulation", "allows circulation for a s.179(3) matter")],
          [f"Aggregate = 132 + 25 + 18 = {cr(tot_after,0)} > {cr(lim,0)} → prior SR (s.186(3)).",
           "s.186(5): Board resolution at a meeting with consent of all directors present."],
          "Existing + proposed > limit → SR", "The test is cumulative, including guarantees and securities.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.186(2), (3), (5)")

    B.add(M["s186"], "L4", stem + "The minimum rate of interest at which the 7-year loan in proposal (a) may be given is:",
          "7.05%",
          [("7.20%", "10-year G-sec taken as closest to a 7-year tenor"),
           ("6.94%", "simple average of the four yields used"),
           ("6.60%", "1-year yield applied regardless of tenor")],
          ["s.186(7): no loan at a rate lower than the prevailing yield of 1, 3, 5 or 10-year G-sec closest to the tenor of the loan.",
           "7 years: distance to 5-year = 2; to 10-year = 3 → 5-year yield 7.05%."],
          "Floor = yield of G-sec with tenor closest to loan tenor", "Pick the closest tenor, not the next higher one.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.186(7)")

    need = []
    items = [("purchase", 58e7, to), ("lease", 7e7, to), ("land", 27e7, nw)]
    for nm, v, base in items:
        if v >= 0.10 * base:
            need.append(nm)
    op = 3e5 > 2.5e5
    assert need == ["land"] and op
    B.add(M["rpt"], "L4", stem + "Which of the contracts with Sharma Traders / related parties require prior approval of members by ordinary resolution under s.188 read with Rule 15?",
          "Sale of surplus land and appointment of the MD's son only",
          [("Purchase of packing material and sale of surplus land only", "goods purchase tested against net worth (₹58 cr ≥ 10% of ₹250 cr)"),
           ("Sale of surplus land only", "office-of-profit threshold overlooked"),
           ("All four contracts", "treats every related-party contract as needing members' approval")],
          [f"Goods purchase: ₹58 cr < 10% of turnover ({cr(0.1*to,0)}) → Board only.",
           f"Lease: ₹7 cr < 10% of turnover → Board only.",
           f"Sale of property: ₹27 cr ≥ 10% of net worth ({cr(0.1*nw,0)}) → OR.",
           "Office of profit: monthly remuneration ₹3 lakh > ₹2.5 lakh → OR. (MD's brother and son are relatives under s.2(77) and Rule 4 of the Specification of Definitions Rules; a firm with a relative as partner is a related party; the son holds an office of profit under s.188(1)(f).)"],
          "Goods/lease/services: 10% of turnover; property: 10% of net worth; office of profit: > ₹2.5 lakh p.m.",
          "Each category has its own base; property sale uses net worth.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.188(1)(f), s.2(76), s.2(77); Specification of Definitions Rules 2014, Rule 4; Meetings of Board Rules 2014, Rule 15(3)")

    # ================================================================== CASE 3 — auditor
    g = "CAB-CASE-3"
    know = d(2026, 8, 12)
    fwd = plus(know, 2)
    reply = d(2026, 9, 20)
    to_cg = plus(reply, 15)
    brd = d(2027, 3, 3)
    cg_app = d(2027, 5, 10)
    stem = (
        "**Case — Meridian Textiles Ltd** (unlisted public company)\n\n"
        "At the AGM, Meridian proposes to appoint CA Rohan Mehta (a sole practitioner) as statutory auditor. Facts about him: his wife holds Meridian shares of face value ₹90,000; he owes Meridian ₹4.20 lakh for goods bought on credit; his father has given a guarantee of ₹1.80 lakh to Meridian for dues of one of Meridian's dealers.\n\n"
        f"The incumbent auditors, Kulkarni & Co, are asked by management to also take up internal audit, tax audit, design of a new ERP-based accounting system and certification of export-incentive claims.\n\n"
        f"During the current audit, Kulkarni & Co came to know on {ds(know)} of a vendor fraud of ₹1.40 crore committed by the purchase head. The Audit Committee's reply was received on {ds(reply)}.\n\n"
        f"Separately, the Board, on {ds(brd)}, resolved to seek removal of Kulkarni & Co before expiry of its term; Central Government approval was received on {ds(cg_app)}.\n\n")
    B.add(M["s141"], "L4", stem + "Is CA Rohan Mehta eligible for appointment?",
          "No — his father's guarantee of ₹1.80 lakh for a third person's indebtedness to Meridian exceeds the ₹1 lakh limit",
          [("No — his wife's shareholding disqualifies him, as a relative cannot hold any security of the company", "ignores the ₹1 lakh face-value allowance for relatives"),
           ("No — his debt of ₹4.20 lakh to Meridian disqualifies him", "₹5 lakh indebtedness threshold overlooked"),
           ("Yes — none of the facts crosses a prescribed limit", "misses the guarantee limit applying to relatives")],
          ["s.141(3)(d)(i) + Rule 10: relative may hold securities of face value up to ₹1,00,000 → ₹90,000 is fine.",
           "s.141(3)(d)(ii): indebtedness above ₹5 lakh disqualifies → ₹4.20 lakh is fine.",
           "s.141(3)(d)(iii): guarantee by the person or his relative/partner for a third person's indebtedness above ₹1 lakh disqualifies → ₹1.80 lakh by father disqualifies."],
          "Rule 10 limits: relative's securities ₹1 lakh (FV); indebtedness ₹5 lakh; guarantee ₹1 lakh",
          "The guarantee limit catches relatives too.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.141(3)(d); Audit Rules 2014, Rule 10")

    B.add(M["s144"], "L4", stem + "Which of the additional assignments can Kulkarni & Co accept, subject to Board/Audit Committee approval?",
          "Tax audit and certification of export-incentive claims only",
          [("Tax audit, certification and internal audit only", "internal audit treated as permissible"),
           ("Tax audit, certification and ERP accounting-system design only", "financial information system design treated as permissible"),
           ("All four assignments, since the company is unlisted", "assumes s.144 applies only to listed companies")],
          ["s.144(b) internal audit and s.144(c) design/implementation of any financial information system are prohibited.",
           "Tax audit and certification are not prohibited; they need Board/Audit Committee approval.",
           "s.144 applies to all companies."],
          "s.144 prohibited list", "Listing status is irrelevant to s.144.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.144")

    B.add(M["fraud"], "L4", stem + "Under s.143(12) and Rule 13, the latest dates by which Kulkarni & Co must (i) forward its report to the Audit Committee and (ii) forward the report with the Committee's reply to the Central Government are:",
          f"(i) {ds(fwd)}; (ii) {ds(to_cg)}",
          [(f"(i) {ds(plus(know,15))}; (ii) {ds(to_cg)}", "15 days used for reporting to the Audit Committee"),
           (f"(i) {ds(fwd)}; (ii) {ds(plus(fwd,45))}", "report to CG timed from the 45-day reply window despite reply being received"),
           (f"(i) {ds(fwd)}; (ii) {ds(plus(reply,30))}", "30 days used after receipt of the reply")],
          ["Rule 13(1): ₹1.40 crore ≥ ₹1 crore → report to Board/Audit Committee immediately, not later than 2 days of knowledge, seeking reply within 45 days.",
           f"(i) {ds(know)} + 2 = {ds(fwd)}.",
           f"On receipt of reply, forward report with reply/observations to CG within 15 days → {ds(reply)} + 15 = {ds(to_cg)} (Form ADT-4)."],
          "2 days → 45 days (reply) → 15 days (to CG)", "If no reply comes within 45 days, the auditor forwards the report to CG anyway.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.143(12); Audit Rules 2014, Rule 13")

    app_by = plus(brd, 30)
    gm_by = plus(cg_app, 60)
    B.add(M["remcg"], "L4", stem + "For the removal of Kulkarni & Co, the latest dates for (i) filing the application with the Central Government and (ii) holding the general meeting to pass the special resolution are:",
          f"(i) {ds(app_by)}; (ii) {ds(gm_by)}",
          [(f"(i) {ds(plus(brd,60))}; (ii) {ds(gm_by)}", "60 days used for the CG application"),
           (f"(i) {ds(app_by)}; (ii) {ds(plus(cg_app,30))}", "30 days used for the general meeting"),
           (f"(i) {ds(app_by)}; (ii) the next AGM", "treats the resolution as AGM business")],
          ["Rule 7(2) Audit Rules: application to CG (Form ADT-2, prescribed by Rule 7(1)) within 30 days of the Board resolution.",
           "Rule 7(3): general meeting for the special resolution within 60 days of receipt of CG approval.",
           "The auditor must be given a reasonable opportunity of being heard (s.140(1) proviso)."],
          "Board resolution + 30 days (ADT-2); CG approval + 60 days (SR)", "30 then 60 — do not swap.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.140(1); Audit Rules 2014, Rule 7(2), (3)")

    B.add(M["tribrem"], "L4", stem + "If, instead, the Tribunal on an application under s.140(5) passes a final order that Kulkarni & Co colluded in the vendor fraud, the consequence is:",
          "Auditor must be changed; the firm is barred from any company's audit for five years",
          [("Kulkarni & Co is barred only from Meridian's audit for five years", "bar limited to one company"),
           ("Meridian must pass a special resolution with CG approval before the auditor is changed", "s.140(1) procedure grafted onto a Tribunal order"),
           ("Kulkarni & Co is barred from all audits for ten years", "wrong period")],
          ["s.140(5): Tribunal may direct the company to change its auditor.",
           "Second proviso: auditor (individual or firm) ineligible for appointment in any company for five years; liable under s.447."],
          "s.140(5)", "The Tribunal route bypasses the s.140(1) special resolution.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.140(5)")

    # ================================================================== CASE 4 — private placement
    g = "CAB-CASE-4"
    earlier, indiv, qib, esop = 45, 150, 40, 30
    counted = earlier + indiv
    left = 200 - counted
    rcv = d(2026, 5, 5)
    allot_by = plus(rcv, 60)
    ref_by = plus(allot_by, 15)
    refd = d(2026, 8, 18)
    days = (refd - allot_by).days
    amt = 2.4e7
    stem = (
        "**Case — Sunrise Agro Ltd** (unlisted public company)\n\n"
        f"In June 2026 (FY 2026-27) Sunrise made a private placement of equity shares to {earlier} identified individuals. "
        f"It now makes a second private placement of equity shares in the same financial year to {indiv} identified individuals, {qib} qualified institutional buyers and {esop} employees under its ESOP scheme under s.62(1)(b).\n\n"
        f"For a separate tranche, application money was received on {ds(rcv)}. Allotment could not be made and application money of {cr(amt)} was refunded only on {ds(refd)}.\n\n")
    B.add(M["pp"], "L4", stem + "How many more identified individuals (other than QIBs and ESOP employees) can Sunrise include in equity private placements during FY 2026-27?",
          str(left),
          [(f"None — the ceiling is already exceeded by {counted + esop - 200}", "ESOP employees counted in the 200 ceiling"),
           (f"None — the ceiling is already exceeded by {counted + esop + qib - 200}", "QIBs and ESOP employees counted"),
           (str(200 - indiv), "earlier offer in the same FY ignored")],
          [f"Ceiling: 200 persons in aggregate per FY per kind of security, excluding QIBs and ESOP employees.",
           f"Counted = {earlier} + {indiv} = {counted}; remaining = {left}."],
          "Remaining = 200 − (all non-QIB, non-ESOP offerees in the FY)", "The 200 is an aggregate for the whole FY.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.42(2); PAS Rules 2014, Rule 14(2)(b)")

    B.add(M["pp"], "L4", stem + "For the separate tranche, by when should Sunrise have (i) allotted the securities and, failing that, (ii) repaid the application money?",
          f"(i) {ds(allot_by)}; (ii) {ds(ref_by)}",
          [(f"(i) {ds(plus(rcv,30))}; (ii) {ds(plus(rcv,45))}", "30-day allotment window used"),
           (f"(i) {ds(allot_by)}; (ii) {ds(plus(allot_by,30))}", "30-day refund window used"),
           (f"(i) {ds(plus(rcv,90))}; (ii) {ds(plus(rcv,105))}", "90-day allotment window used")],
          ["s.42(6): allot within 60 days from receipt of application money; else repay within 15 days from expiry of the 60 days.",
           f"{ds(rcv)} + 60 = {ds(allot_by)}; + 15 = {ds(ref_by)}."],
          "Allot ≤ receipt + 60 days; refund ≤ + 15 days", "The 15 days run from the 60th day.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.42(6)")

    B.add(M["pp"], "L4", stem + "The interest payable on the delayed refund of the separate tranche under s.42(6) is (365-day year):",
          R(interest(amt, 0.12, days)),
          [(R(interest(amt, 0.12, (refd - ref_by).days)), "interest counted from the end of the 15-day refund window"),
           (R(interest(amt, 0.15, days)), "15% rate of s.39/Rule 11 applied"),
           (R(interest(amt, 0.18, days)), "18% rate of s.127 applied")],
          [f"s.42(6): if not repaid within the 15 days, liable to repay with interest @ 12% p.a. from the expiry of the 60th day.",
           f"Days from {ds(allot_by)} to {ds(refd)} = {days}; interest = {inr(amt)} × 12% × {days}/365 = {R(interest(amt,0.12,days))}."],
          "Interest = Amount × 12% × days from the 60th day/365",
          "Interest runs from the 60th day, not from the end of the refund window.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.42(6)")

    B.add(M["pp"], "L4", stem + stmts("Consider the following regarding the second placement:",
                                         ["The return of allotment in Form PAS-3 must be filed within 15 days of allotment.",
                                          "The money received must be kept in a separate bank account and cannot be utilised until allotment is made and the return of allotment is filed.",
                                          "Since the company is unlisted, the allotted shares may be issued in physical form."]),
          "1 and 2 only",
          [("1, 2 and 3", "ignores the demat mandate for unlisted public companies"),
           ("2 only", "30-day general PAS-3 period applied"),
           ("1 and 3 only", "allows use of money before allotment/filing")],
          ["s.42(8) + Rule 14: PAS-3 within 15 days of allotment.",
           "s.42(6): separate bank account; proviso to s.42(4): no utilisation until allotment is made and the return of allotment is filed.",
           "s.29 + Rule 9A: unlisted public companies issue securities only in demat."],
          "s.42(4), (6), (8); s.29 / Rule 9A", "Unlisted public companies are within the demat mandate.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.42(4) proviso, s.42(6), (8), s.29; PAS Rules 2014, Rules 9A, 14")

    # ================================================================== CASE 5 — preference redemption
    g = "CAB-CASE-5"
    pref, prem_rate = 6e7, 0.05
    fresh = 2.5e7
    gr, pl, spb = 5e7, 1.8e7, 0.9e7
    crr = pref - fresh
    prem = pref * prem_rate
    stem = (
        "**Case — Orion Chemicals Ltd** (unlisted; not a company of any class prescribed under s.52(3) or s.55(2))\n\n"
        "Orion has 60 lakh 8% redeemable preference shares of ₹10 each, fully paid (₹6.00 crore), due for redemption at a premium of 5%. "
        "To part-finance the redemption it issues 25 lakh equity shares of ₹10 each at par (₹2.50 crore). "
        "Balances before redemption (₹ crore): general reserve 5.00; surplus in P&L 1.80; securities premium 0.90.\n\n")
    B.add(M["pref"], "L4", stem + "The amount to be transferred to the Capital Redemption Reserve is:",
          cr(crr),
          [(cr(pref), "fresh-issue proceeds not deducted"),
           (cr(crr + prem), "premium on redemption added to the CRR"),
           (cr(fresh), "fresh-issue amount transferred instead of the shortfall")],
          ["s.55(2)(c): where redemption is out of profits, a sum equal to the nominal amount of shares redeemed out of profits is transferred to CRR.",
           f"Nominal redeemed out of profits = {cr(pref)} − {cr(fresh)} (fresh issue) = {cr(crr)}."],
          "CRR = Nominal value redeemed − Proceeds of fresh issue (at par)", "Premium on redemption never goes to CRR.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.55(2)")

    B.add(M["s52"], "L4", stem + "Orion provides the premium on redemption out of securities premium. The premium payable and the balance left in securities premium are:",
          f"{cr(prem)} and {cr(spb-prem)}",
          [(f"{cr(pref*0.08)} and {cr(spb-pref*0.08)}", "8% dividend rate confused with 5% premium"),
           (f"{cr(prem)} and {cr(spb)}", "premium charged to P&L while claiming securities premium use"),
           (f"{cr(fresh*prem_rate)} and {cr(spb-fresh*prem_rate)}", "premium computed on the fresh issue instead of shares redeemed")],
          [f"Premium = 5% × {cr(pref)} = {cr(prem)}.",
           f"s.52(2)(d)/s.55(2)(d)(ii): provided out of securities premium (or profits) before redemption → balance {cr(spb)} − {cr(prem)} = {cr(spb-prem)}."],
          "Premium = Nominal × premium rate", "The premium is on shares redeemed, not on the fresh issue.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.52(2)(d); s.55(2)(d)")

    min_fresh = pref - pl
    B.add(M["pref"], "L4", stem + "If Orion wanted to keep its general reserve intact and use only the P&L surplus for the CRR transfer, the minimum number of equity shares of ₹10 at par it would need to issue is:",
          f"{inr(min_fresh/10)} shares",
          [(f"{inr((pref+prem-pl)/10)} shares", "premium on redemption added to the fresh-issue requirement"),
           (f"{inr(pl/10)} shares", "P&L surplus mistaken for fresh-issue requirement"),
           (f"{inr((pref-pl-spb)/10)} shares", "securities premium treated as usable for the nominal amount")],
          [f"Nominal ₹6.00 crore must be covered by fresh-issue proceeds + CRR transfer from profits.",
           f"CRR from P&L ≤ {cr(pl)} → fresh issue ≥ {cr(min_fresh)} → {inr(min_fresh/10)} shares of ₹10."],
          "Fresh issue ≥ Nominal − profits used for CRR", "Securities premium cannot replace capital for the nominal amount.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.55(2)(a), (c)")

    B.add(M["pref"], "L4", stem + stmts("After redemption, consider:",
                                           ["The Capital Redemption Reserve may be applied in paying up unissued shares of the company to be issued as fully paid bonus shares.",
                                            "The Capital Redemption Reserve may be used to pay a dividend to equity shareholders if profits are inadequate.",
                                            "Only fully paid preference shares can be redeemed."]),
          "1 and 3 only",
          [("1, 2 and 3", "CRR treated as distributable"),
           ("1 only", "believes partly paid shares may also be redeemed"),
           ("2 and 3 only", "overlooks bonus use of CRR")],
          ["s.55(2) proviso / s.63(1)(iii): CRR may be applied for fully paid bonus shares.",
           "Otherwise the provisions on reduction of share capital apply as if the CRR were paid-up share capital — it is not distributable.",
           "s.55(2)(b): no shares shall be redeemed unless they are fully paid."],
          "s.55(2), s.63(1)", "CRR behaves like capital — bonus yes, dividend no.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.55; s.63(1)")

    # ================================================================== CASE 6 — governance / meetings
    g = "CAB-CASE-6"
    sanc, vac = 14, 4
    strength = sanc - vac
    inter = 7
    mem = 4200
    pres, prox, corp = 11, 6, 2
    stem = (
        "**Case — Deccan Logistics Ltd** (listed)\n\n"
        f"Articles fix the Board at {sanc}; {vac} offices are vacant, so {strength} directors are in office. For an agenda item on a contract with a promoter-group company, {inter} directors are interested.\n\n"
        f"On the date of the AGM the company has {inr(mem)} members. At the scheduled time, {pres} members are present in person, {prox} members are represented by proxies (not otherwise present), and {corp} body-corporate members are represented by authorised representatives under s.113.\n\n"
        f"The company also circulated a draft Board resolution (not a s.179(3) matter) to all {strength} directors, of whom 2 are interested in the matter.\n\n")
    qg = max(math.ceil(strength / 3), 2)
    B.add(M["bq"], "L4", stem + "The quorum for (i) ordinary business at the Board meeting and (ii) the promoter-group contract item is:",
          f"(i) {qg} directors; (ii) the non-interested directors present, not less than 2",
          [(f"(i) {math.ceil(sanc/3)} directors; (ii) the non-interested directors present, not less than 2", "vacant offices included in total strength"),
           (f"(i) {qg} directors; (ii) {qg} directors, counting interested directors", "s.174(3) interested-director rule ignored"),
           (f"(i) {qg} directors; (ii) all {strength-inter} non-interested directors", "requires all non-interested directors")],
          [f"(i) Strength {strength} → {strength}/3 = {strength/3:.2f} → {qg}.",
           f"(ii) Interested {inter} ≥ 2/3 × {strength} = {2*strength/3:.2f} → quorum = non-interested directors present, not less than two."],
          "s.174(1), (3)", "Two-thirds trigger is computed on total strength excluding vacancies.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.174(1), (3)")

    counted = pres + corp
    B.add(M["gq"], "L4", stem + "Regarding the AGM quorum, which is correct?",
          f"Quorum 15; only {counted} counted (proxies excluded), so quorum is not present",
          [(f"Quorum required is 15; {pres+prox+corp} are counted including proxies, so quorum is present", "proxies counted"),
           (f"Quorum required is 30; {counted} are counted, so quorum is not present", "wrong slab (> 5,000 members)"),
           (f"Quorum required is 5; {pres} members in person suffice", "slab for up to 1,000 members applied")],
          [f"{inr(mem)} members → slab > 1,000 and ≤ 5,000 → 15 personally present.",
           f"Counted: {pres} in person + {corp} s.113 representatives = {counted}; proxies excluded → no quorum; meeting adjourns under s.103(2)."],
          "s.103(1)(a)(ii): 15 personally present", "Authorised representatives count; proxies do not.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.103, s.113")

    ent = strength - 2
    maj = ent // 2 + 1
    third = math.ceil(strength / 3)
    B.add(M["circ"], "L4", stem + "For the circular resolution, the minimum number of approvals needed and the minimum number of directors who can require it to be decided at a meeting are:",
          f"{maj} approvals; {third} directors",
          [(f"{strength//2+1} approvals; {third} directors", "majority computed on all directors including interested"),
           (f"{maj} approvals; {strength//3} directors", "one-third rounded down"),
           (f"{ent} approvals; {third} directors", "unanimity of entitled directors required")],
          [f"Entitled to vote = {strength} − 2 = {ent}; majority = {maj}.",
           f"Not less than one-third of total directors: {strength}/3 = {strength/3:.2f} → {third}."],
          "s.175(1) and proviso", "Approval base excludes interested directors; meeting-demand base does not.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.175(1)")

    B.add(M["src"], "L4", stem + "Deccan Logistics must constitute a Stakeholders Relationship Committee. Under s.178(5)-(6), which is correct?",
          "Chaired by a non-executive director; chair or authorised member attends GMs",
          [("The chairperson must be the managing director, since grievances concern operations", "executive chair assumed"),
           ("The committee is needed only if debenture-holders exceed 1,000", "trigger limited to debenture-holders"),
           ("The committee replaces the Audit Committee for listed companies", "confuses committee roles")],
          ["s.178(5): chairperson — a non-executive director; other members as the Board decides.",
           f"{inr(mem)} members > 1,000 → committee required.",
           "s.178(7): chairperson of each committee or authorised member attends general meetings."],
          "s.178(5)-(7)", "SRC chair: non-executive (not necessarily independent) under the Act.",
          kind="case", group=g, verify_fact=True, ref="Companies Act 2013 s.178(5)-(7)")
