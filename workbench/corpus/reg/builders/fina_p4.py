"""FIN-A part 4: direct/indirect taxes, DTAA, GST. Case set C3 (GST exporter)."""
from reglib import inr, R, pct, lakh, crore
from fina_util import table

DTAA = "fin-dtaa-and-tax-administration-bodies-7f30b2fa"
DIT = "fin-direct-vs-indirect-taxes-66414170"
GSTR = "fin-gst-returns-and-tcs-by-e-commerce-operators-3f6313c9"
ITC = "fin-gst-supply-input-tax-credit-zero-rated-exports-9d84554b"

CGST = "CGST Act 2017"


def add_all(B):
    A = B.add

    # ================= DTAA / tax bodies =================
    A(DTAA, "L2",
      "Match the body (List I) with its constitutional/statutory basis or function (List II):\n\n"
      + table(["List I", "List II"],
              [["P. Central Board of Direct Taxes", "1. Article 279A of the Constitution; recommends GST rates and rules to the Union and States"],
               ["Q. GST Council", "2. Central Boards of Revenue Act, 1963; administers income-tax"],
               ["R. Income Tax Appellate Tribunal", "3. Administers customs and central GST"],
               ["S. Central Board of Indirect Taxes and Customs", "4. Second appellate authority on facts in income-tax disputes"]], ["---", "---"]) + "\n\nCodes:",
      "P-2, Q-1, R-4, S-3",
      [("P-3, Q-1, R-4, S-2", "CBDT and CBIC functions swapped"),
       ("P-2, Q-4, R-1, S-3", "GST Council confused with ITAT"),
       ("P-2, Q-1, R-3, S-4", "ITAT and CBIC swapped")],
      ["CBDT and CBIC: Central Boards of Revenue Act 1963.", "GST Council: Art. 279A (101st Amendment, 2016).",
       "ITAT: final fact-finding authority in income-tax appeals."], "—",
      "Two revenue boards under one 1963 Act.", kind="match", verify_fact=True,
      ref="Central Boards of Revenue Act 1963; Constitution Art. 279A; Income-tax Act 1961 s.252")

    fi, ft, tot, itax = 6e5, 1.5e5, 24e5, 514800
    avg = itax / tot
    rel = fi * min(avg, ft / fi)
    A(DTAA, "L3",
      "For FY 2024-25, a resident individual's total income of ₹24,00,000 includes ₹6,00,000 earned in Country Z, with which India has no tax treaty; tax of ₹1,50,000 was paid in Country Z on that income. Indian tax on total income (including surcharge and health & education cess) is ₹5,14,800. Relief under Section 91 of the Income-tax Act, 1961 is:",
      R(rel),
      [(R(ft), "full foreign tax allowed as credit"),
       (R((fi - ft) * avg), "Indian rate applied to foreign income net of foreign tax"),
       (R(fi * itax / 1.04 / tot), "Indian average rate computed excluding health & education cess")],
      [f"Indian average rate = 5,14,800 ÷ 24,00,000 = {pct(avg)}", f"Foreign rate = 1,50,000 ÷ 6,00,000 = {pct(ft/fi)}",
       f"Relief = 6,00,000 × lower rate ({pct(min(avg,ft/fi))}) = {R(rel)}"],
      "s.91 relief = Doubly taxed income × lower of (Indian average rate, foreign rate)",
      "Relief is capped at the Indian average rate, not the tax actually paid abroad.", verify_fact=True,
      ref="Income-tax Act 1961, s.91 (unilateral relief) — applicable for FY 2024-25")

    # ================= DIRECT vs INDIRECT =================
    A(DIT, "L1",
      "Which of the following taxes is administered by the Central Board of Direct Taxes (CBDT)?",
      "Securities Transaction Tax",
      [("Customs duty on imported gold", "administered by CBIC"),
       ("GST compensation cess", "levied under the GST (Compensation to States) Act; CBIC"),
       ("Central excise duty on petrol", "excise on petroleum is an indirect tax under CBIC")],
      ["STT is levied under Chapter VII of the Finance (No.2) Act, 2004 and administered by CBDT.",
       "It is classified among direct taxes in Union Budget documents."], "—",
      "Levy on a transaction does not by itself make a tax 'indirect' in India's classification.", kind="conceptual",
      verify_fact=True, ref="Finance (No.2) Act 2004, Chapter VII (STT); Union Budget receipt classification")

    d0, d1, i0, i1, y0, y1 = 16.6, 19.1, 14.8, 15.9, 300.0, 330.0
    gy = y1 / y0 - 1
    bd, bi = (d1 / d0 - 1) / gy, (i1 / i0 - 1) / gy
    s0, s1 = d0 / (d0 + i0), d1 / (d1 + i1)
    A(DIT, "L3",
      f"Illustrative data (₹ lakh crore): direct taxes rose from {d0} to {d1}, indirect taxes from {i0} to {i1}, and nominal GDP from {y0:.0f} to {y1:.0f}. Which statement is correct?",
      f"Direct-tax buoyancy is {bd:.2f} and indirect-tax buoyancy {bi:.2f}; the share of direct taxes rises from {pct(s0,1)} to {pct(s1,1)}",
      [(f"Direct-tax buoyancy is {1/bd:.2f} and indirect-tax buoyancy {1/bi:.2f}; the share of direct taxes rises from {pct(s0,1)} to {pct(s1,1)}", "buoyancy inverted (GDP growth ÷ tax growth)"),
       (f"Direct-tax buoyancy is {(d1-d0)/(y1-y0):.2f} and indirect-tax buoyancy {(i1-i0)/(y1-y0):.2f}; direct-tax share unchanged", "absolute changes used instead of growth rates"),
       (f"Direct-tax buoyancy is {bd:.2f} and indirect-tax buoyancy {bi:.2f}; the share of direct taxes falls to {pct(1-s1,1)}", "indirect share reported as direct share")],
      [f"GDP growth = {pct(gy,1)}", f"Direct growth = {pct(d1/d0-1)} ⇒ buoyancy {bd:.2f}", f"Indirect growth = {pct(i1/i0-1)} ⇒ buoyancy {bi:.2f}",
       f"Direct share: {pct(s0,1)} → {pct(s1,1)}"],
      "Buoyancy = %ΔTax revenue ÷ %ΔNominal GDP", "Buoyancy > 1 means revenue grows faster than the economy.")

    # ================= GST RETURNS / TCS =================
    A(GSTR, "L2",
      "Match the GST return (List I) with its purpose (List II):\n\n"
      + table(["List I", "List II"],
              [["P. GSTR-1", "1. Statement of tax collected at source by an e-commerce operator"],
               ["Q. GSTR-3B", "2. Statement of outward supplies"],
               ["R. GSTR-8", "3. Annual return of a regular taxpayer"],
               ["S. GSTR-9", "4. Summary return with self-assessed tax payment"]], ["---", "---"]) + "\n\nCodes:",
      "P-2, Q-4, R-1, S-3",
      [("P-4, Q-2, R-1, S-3", "GSTR-1 and GSTR-3B swapped"),
       ("P-2, Q-4, R-3, S-1", "GSTR-8 and GSTR-9 swapped"),
       ("P-2, Q-1, R-4, S-3", "GSTR-3B confused with the TCS statement")],
      ["GSTR-1: outward supplies (11th monthly / 13th quarterly under QRMP).", "GSTR-3B: summary return + payment (20th; 22nd/24th for QRMP).",
       "GSTR-8: ECO TCS statement (10th).", "GSTR-9: annual return (31 December)."], "—",
      "GSTR-8 is filed by the operator, not the seller.", kind="match", verify_fact=True, ref=CGST + " ss.37, 39, 44, 52; CGST Rules 59–62, 67, 80")

    intra, inter, ret, s95, rate = 30e5, 12e5, 3e5, 6e5, 0.005
    net_intra = intra - ret
    tcs_c = net_intra * rate / 2
    tcs_i = inter * rate
    tot = 2 * tcs_c + tcs_i
    A(GSTR, "L3",
      f"An e-commerce operator's platform records the following for one seller in a month (values exclusive of GST): intra-State taxable supplies ₹{inr(intra)}, inter-State taxable supplies ₹{inr(inter)}, intra-State goods returned during the month ₹{inr(ret)}, and restaurant services ₹{inr(s95)} on which the operator itself pays tax under Section 9(5). At the TCS rate of 0.5% (0.25% CGST + 0.25% SGST, or 0.5% IGST), total TCS to be collected is:",
      f"{R(tot)} (CGST {R(tcs_c)} + SGST {R(tcs_c)} + IGST {R(tcs_i)})",
      [(f"{R(tot*2)} (CGST {R(tcs_c*2)} + SGST {R(tcs_c*2)} + IGST {R(tcs_i*2)})", "pre-July 2024 rate of 1% applied"),
       (f"{R((intra+inter)*rate)} (CGST {R(intra*rate/2)} + SGST {R(intra*rate/2)} + IGST {R(tcs_i)})", "returns not deducted from net taxable supplies"),
       (f"{R(tot+s95*rate)} (CGST {R((net_intra+s95)*rate/2)} + SGST {R((net_intra+s95)*rate/2)} + IGST {R(tcs_i)})", "Section 9(5) supplies included in the TCS base")],
      [f"Net intra-State = {inr(intra)} − {inr(ret)} = {inr(net_intra)}; 9(5) supplies excluded",
       f"CGST = SGST = 0.25% × {inr(net_intra)} = {R(tcs_c)}", f"IGST = 0.5% × {inr(inter)} = {R(tcs_i)}", f"Total = {R(tot)}"],
      "TCS = rate × (Taxable supplies − Returns), excluding s.9(5) supplies", "The rate was halved to 0.5% from 10 July 2024.",
      verify_fact=True, ref=CGST + " s.52; Notification No. 15/2024–Central Tax (TCS rate 0.5% w.e.f. 10.07.2024)")

    # ================= GST ITC =================
    A(ITC, "L2",
      "Under Section 17(5) of the CGST Act, input tax credit is AVAILABLE on which of the following, for a manufacturer?",
      "GST paid on a goods carriage (truck) used to transport the manufacturer's goods",
      [("GST paid on a sedan (seating capacity 5) used by directors for business travel", "motor vehicles ≤ 13 persons are blocked unless used for specified businesses"),
       ("GST on outdoor catering for an employees' annual party, not obligatory under any law", "food/outdoor catering blocked unless statutorily obligatory"),
       ("GST on membership of a club for senior managers", "club membership is a blocked credit")],
      ["s.17(5)(a) blocks motor vehicles for ≤13 persons (with exceptions); goods-transport vehicles are outside the block.",
       "s.17(5)(b) blocks food, outdoor catering and club membership (subject to the statutory-obligation exception)."], "—",
      "Blocked-credit list is specific — goods transport vehicles are not in it.", kind="conceptual", verify_fact=True, ref=CGST + " s.17(5)")

    out = {"IGST": 2.0e5, "CGST": 4.0e5, "SGST": 4.0e5}
    itc = {"IGST": 3.0e5, "CGST": 5.5e5, "SGST": 1.0e5}
    ig_bal = itc["IGST"] - out["IGST"]
    sgst_cash = out["SGST"] - ig_bal - itc["SGST"]
    cg_cf = itc["CGST"] - out["CGST"]
    assert sgst_cash == 2.0e5 and cg_cf == 1.5e5
    A(ITC, "L3",
      "A registered person's output tax and input tax credit for a month are (₹ lakh):\n\n"
      + table(["Head", "Output tax", "ITC available"], [[k, f"{out[k]/1e5:.2f}", f"{itc[k]/1e5:.2f}"] for k in out]) +
      "\n\nApplying Sections 49 and 49A and Rule 88A of the CGST framework, the MINIMUM cash payment and the credit carried forward are:",
      f"Cash ₹{sgst_cash/1e5:.2f} lakh (SGST); CGST credit ₹{cg_cf/1e5:.2f} lakh carried forward",
      [(f"Cash ₹{(sum(out.values())-sum(itc.values()))/1e5:.2f} lakh; no credit carried forward", "CGST credit cross-utilised against SGST liability"),
       (f"Cash ₹{(out['SGST']-itc['SGST'])/1e5:.2f} lakh (SGST); CGST credit ₹{(cg_cf+ig_bal)/1e5:.2f} lakh carried forward", "balance IGST credit set off against CGST instead of SGST"),
       (f"Cash ₹{(out['SGST']-itc['SGST'])/1e5:.2f} lakh (SGST); IGST ₹{ig_bal/1e5:.2f} lakh and CGST ₹{cg_cf/1e5:.2f} lakh carried forward", "IGST credit wrongly restricted to IGST liability")],
      ["IGST credit ₹3.00 lakh: first against IGST ₹2.00 lakh; balance ₹1.00 lakh must be used (s.49A) — apply to SGST.",
       "CGST credit ₹5.50 lakh against CGST ₹4.00 lakh; excess ₹1.50 lakh cannot be used for SGST.",
       "SGST: 4.00 − 1.00 (IGST) − 1.00 (SGST credit) = ₹2.00 lakh cash."],
      "IGST → IGST, then CGST/SGST in any order; CGST ↛ SGST", "Direct IGST balance to the head whose own credit is insufficient.",
      verify_fact=True, ref=CGST + " ss.49(5), 49A; CGST Rules r.88A")

    c2, tax, ex, zr = 9e5, 120e5, 30e5, 50e5
    F = tax + ex + zr
    d1 = c2 * ex / F
    A(ITC, "L3",
      f"Common input tax credit (C2) of a manufacturer for a month is ₹{inr(c2)}. Its turnover in the State is: taxable domestic supplies ₹{inr(tax)}, exempt supplies ₹{inr(ex)} and exports under LUT ₹{inr(zr)}. Under Rule 42, the credit attributable to exempt supplies (D1) to be reversed is:",
      R(d1),
      [(R(c2 * (ex + zr) / F), "exports treated as exempt supplies"),
       (R(c2 * ex / tax), "exempt turnover divided by taxable domestic turnover only"),
       (R(c2 * ex / (tax + ex)), "zero-rated turnover excluded from total turnover")],
      [f"Total turnover F = {inr(tax)} + {inr(ex)} + {inr(zr)} = {inr(F)}", f"D1 = C2 × E/F = {inr(c2)} × {inr(ex)}/{inr(F)} = {R(d1)}"],
      "D1 = C2 × (Exempt turnover ÷ Total turnover)", "Zero-rated supplies are not exempt — they stay in F but not in E.",
      verify_fact=True, ref=CGST + " s.17(2); CGST Rules r.42; IGST Act s.16")

    # ================= CASE C3: GST EXPORTER =================
    G = "FINA-CASE-GST"
    rm, isv, cgd, car, cat = 14e5, 2e5, 3e5, 1.5e5, 0.4e5
    dom, zro = 240e5, 150e5
    stim = ("**Case — Sutlej Precision Tools Ltd (fictional), registered in Punjab — data for October**\n\n"
            + table(["Inward supply", "GST paid (₹)"],
                    [["Raw materials (used for both domestic and export production)", inr(rm)],
                     ["Input services — job work, freight, testing", inr(isv)],
                     ["CNC machine (capital goods)", inr(cgd)],
                     ["Sedan car for the Managing Director", inr(car)],
                     ["Outdoor catering for staff canteen (not obligatory under any law)", inr(cat)]], ["---", "---:"]) +
            f"\n\nOutward supplies: domestic taxable ₹{inr(dom)}; exports of goods under LUT (without payment of IGST) ₹{inr(zro)}. No exempt supplies. "
            "Assume all documentary conditions of Section 16 are satisfied and the electronic credit ledger has sufficient balance.")
    elig = rm + isv + cgd
    A(ITC, "L4", stim + "\n\nThe input tax credit Sutlej can avail for October is:",
      R(elig),
      [(R(rm + isv + cgd + car + cat), "blocked credits on car and catering included"),
       (R(rm + isv), "credit on capital goods wrongly excluded"),
       (R(rm + isv + cgd + car), "passenger car (≤13 seats) treated as eligible")],
      [f"Eligible: raw materials {inr(rm)} + input services {inr(isv)} + capital goods {inr(cgd)} = {R(elig)}",
       "Blocked under s.17(5): MD's car, outdoor catering."],
      "Eligible ITC = Total ITC − Blocked credits (s.17(5))", "Capital goods credit is available in full upfront.", group=G,
      verify_fact=True, ref=CGST + " ss.16, 17(5)")

    net_itc = rm + isv
    ref = zro * net_itc / (dom + zro)
    A(ITC, "L4", stim + "\n\nThe maximum refund of unutilised ITC on account of exports under LUT, as per Rule 89(4), is closest to:",
      R(ref),
      [(R(zro * elig / (dom + zro)), "capital-goods credit included in Net ITC"),
       (R(zro * net_itc / dom), "adjusted total turnover taken as domestic turnover only"),
       (R(net_itc), "entire Net ITC claimed as refund")],
      [f"Net ITC (inputs + input services) = {inr(net_itc)}", f"Adjusted total turnover = {inr(dom)} + {inr(zro)} = {inr(dom+zro)}",
       f"Refund = {inr(zro)} × {inr(net_itc)} ÷ {inr(dom+zro)} = {R(ref)}"],
      "Refund = Zero-rated turnover × Net ITC ÷ Adjusted total turnover", "Capital goods credit is excluded from 'Net ITC'.", group=G,
      verify_fact=True, ref=CGST + " s.54(3); CGST Rules r.89(4); IGST Act s.16(3)")

    A(ITC, "L4", stim + "\n\nSutlej is considering exporting on payment of IGST instead of under LUT. Which statement is correct?",
      "IGST route: shipping bill is deemed the refund claim for IGST paid; LUT route: unutilised ITC refund is claimed within two years of relevant date",
      [("Exports are exempt supplies, so under either route the common input tax credit attributable to exports must be reversed under Rule 42", "exports are zero-rated, not exempt; credit is available"),
       ("Exporting under LUT requires the exporter to furnish a bank guarantee equal to the IGST foregone on every export consignment it ships", "a bond (with guarantee) is an alternative for ineligible exporters; LUT needs no bank guarantee"),
       ("Under the IGST-payment route, IGST on exports must be paid only in cash and cannot be discharged from the electronic credit ledger balance", "IGST on exports can be paid from ITC")],
      ["IGST Act s.16(3): export under LUT (refund of unutilised ITC) or on payment of IGST (refund of IGST).",
       "Rule 96: shipping bill deemed refund application for IGST paid on goods exported.", "s.54(1): refund claim within two years of the relevant date."], "—",
      "Zero-rating means credit is preserved — either by refund of ITC or refund of IGST.", group=G, kind="case",
      verify_fact=True, ref="IGST Act s.16; " + CGST + " s.54; CGST Rules r.96")

    ecs, eret = 12e5, 1.2e5
    tcs = (ecs - eret) * 0.005
    A(GSTR, "L4", stim + f"\n\nSutlej also sells spare parts intra-State through an e-commerce operator: taxable value ₹{inr(ecs)} with returns of ₹{inr(eret)} in the month. The TCS collected on Sutlej's supplies and its treatment are:",
      f"{R(tcs)}; in Sutlej's electronic cash ledger once the operator files GSTR-8 and Sutlej accepts it",
      [(f"{R(tcs)}; credited to Sutlej's electronic credit ledger as input tax credit for the month", "TCS is credited to the cash ledger, not the credit ledger"),
       (f"{R((ecs-eret)*0.01)}; available in Sutlej's electronic cash ledger once the operator files GSTR-8", "old 1% TCS rate applied"),
       (f"{R(ecs*0.005)}; available in Sutlej's electronic cash ledger once the operator files GSTR-8", "returns not deducted")],
      [f"Net value = {inr(ecs)} − {inr(eret)} = {inr(ecs-eret)}", f"TCS = 0.5% × {inr(ecs-eret)} = {R(tcs)} (CGST + SGST 0.25% each)",
       "Operator files GSTR-8 by the 10th; supplier claims credit in its electronic cash ledger (s.52(7))."],
      "TCS = 0.5% × Net taxable supplies", "TCS is a cash credit, usable to pay any tax liability.", group=G,
      verify_fact=True, ref=CGST + " s.52; Notification No. 15/2024–Central Tax")
