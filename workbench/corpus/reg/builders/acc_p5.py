"""Part 5: ratio analysis, cash conversion cycle, fund flow, working capital, cash flow statements (AS 3 / Ind AS 7)."""
from acc_common import S, R, inr, pct, ar, stmt, match, table


def add_all(B):
    # ================= Liquidity =================
    cr, qr, cl = 2.5, 1.5, 400000
    inv = (cr - qr) * cl
    B.add(micro=S("liquidity-ratios"), level="L2",
          stem=f"A firm's current ratio is {cr} and quick ratio {qr}. Current liabilities are {R(cl)}. With no prepaid expenses, its inventory is:",
          correct=R(inv),
          wrongs=[(R(qr * cl), "quick assets reported as inventory"),
                  (R(cr * cl), "current assets reported as inventory"),
                  (R((cr - qr) / cr * cl), "difference in ratios divided by the current ratio")],
          steps=[f"Current assets = {cr} × {inr(cl)} = {inr(cr*cl)}", f"Quick assets = {qr} × {inr(cl)} = {inr(qr*cl)}",
                 f"Inventory = {inr(cr*cl)} − {inr(qr*cl)} = {inr(inv)}"],
          formula="Inventory = (CR − QR) × CL", trap="The gap between the ratios times CL gives inventory.")

    stmt(B, S("liquidity-ratios"), "L3", "A company's current ratio is 2:1 before each of the following independent transactions. Which of them INCREASE the current ratio?",
         ["Payment of trade payables in cash.", "Purchase of inventory on credit.",
          "Collection of cash from trade receivables.", "Issue of long-term debentures for cash."],
         [1, 4], [([1, 3, 4], "treats a receivable collection (asset swap) as increasing the ratio"),
                  ([1, 2, 4], "treats an equal addition to CA and CL as increasing a ratio above 1"),
                  ([4], "misses that equal reduction of CA and CL raises a ratio above 1")],
         ["Take CA 200, CL 100. (1) Pay 50: 150/50 = 3 ↑.", "(2) Buy 50 on credit: 250/150 = 1.67 ↓.",
          "(3) Collect 50: 200/100 unchanged.", "(4) Debentures 50: 250/100 = 2.5 ↑."],
         "When CR > 1, an equal decrease in CA and CL raises the ratio; an equal increase lowers it.",
         question="Select the correct answer:")

    # ================= Turnover =================
    cs, cash_s, od, cd, days = 3600000, 900000, 280000, 320000, 360
    avg = (od + cd) / 2
    dtr = cs / avg
    dso = days / dtr
    assert (avg, dtr, dso) == (300000, 12, 30)
    B.add(micro=S("turnover-ratios"), level="L3",
          stem=(f"Credit sales for the year are {R(cs)} and cash sales {R(cash_s)}. Trade receivables were {R(od)} at the start and {R(cd)} at the end of "
                f"the year. Using a {days}-day year, the average collection period is:"),
          correct=f"{dso:.0f} days",
          wrongs=[(f"{days*cd/cs:.0f} days", "closing receivables used instead of average"),
                  (f"{days*avg/(cs+cash_s):.0f} days", "total sales including cash sales used"),
                  (f"{days*(od+cd)/cs:.0f} days", "opening and closing receivables added, not averaged")],
          steps=[f"Average receivables = ({inr(od)} + {inr(cd)}) ÷ 2 = {inr(avg)}",
                 f"Turnover = {inr(cs)} ÷ {inr(avg)} = {dtr:.0f} times", f"Collection period = {days} ÷ {dtr:.0f} = {dso:.0f} days"],
          formula="Collection period = Average receivables ÷ Credit sales × 360", trap="Cash sales never create receivables.")

    sales, gp, oi, ci = 2400000, 0.25, 220000, 260000
    cogs = sales * (1 - gp)
    itr = cogs / ((oi + ci) / 2)
    assert itr == 7.5
    B.add(micro=S("turnover-ratios"), level="L2",
          stem=(f"Sales are {R(sales)} with a gross profit of {pct(gp,0)} on sales. Opening inventory is {R(oi)} and closing inventory {R(ci)}. "
                "The inventory turnover ratio is:"),
          correct=f"{itr:.2f} times",
          wrongs=[(f"{sales/((oi+ci)/2):.2f} times", "sales used instead of cost of goods sold"),
                  (f"{(sales - sales*gp/(1+gp))/((oi+ci)/2):.2f} times", "25% treated as mark-up on cost"),
                  (f"{cogs/ci:.2f} times", "closing inventory used instead of average")],
          steps=[f"COGS = {inr(sales)} × 75% = {inr(cogs)}", f"Average inventory = {inr((oi+ci)/2)}", f"ITR = {itr:.2f}"],
          formula="Inventory turnover = COGS ÷ Average inventory", trap="Margin on sales vs mark-up on cost.")

    s_wc, ca_wc, cl_wc = 3000000, 1000000, 400000
    B.add(micro=S("turnover-ratios"), level="L2",
          stem=f"Revenue from operations is {R(s_wc)}, current assets {R(ca_wc)} and current liabilities {R(cl_wc)}. The working capital turnover ratio is:",
          correct=f"{s_wc/(ca_wc-cl_wc):.1f} times",
          wrongs=[(f"{s_wc/ca_wc:.1f} times", "current assets (gross WC) used"),
                  (f"{s_wc/cl_wc:.1f} times", "current liabilities used"),
                  (f"{(ca_wc-cl_wc)/s_wc:.1f} times", "ratio inverted")],
          steps=[f"Net working capital = {inr(ca_wc)} − {inr(cl_wc)} = {inr(ca_wc-cl_wc)}", f"Turnover = {inr(s_wc)} ÷ {inr(ca_wc-cl_wc)} = {s_wc/(ca_wc-cl_wc):.1f}"],
          formula="WC turnover = Revenue ÷ Net working capital", trap="Net, not gross, working capital.")

    # ================= Profitability =================
    pat, tr, intr, eq, deb = 600000, 0.25, 200000, 3000000, 2000000
    pbt = pat / (1 - tr)
    ebit = pbt + intr
    roce = ebit / (eq + deb)
    assert (pbt, ebit, roce) == (800000, 1000000, 0.2)
    B.add(micro=S("profitability-ratios"), level="L3",
          stem=(f"Profit after tax is {R(pat)} (tax rate {pct(tr,0)}); interest on 10% debentures is {R(intr)}. Shareholders' funds are {R(eq)} and "
                f"debentures {R(deb)}. Return on capital employed (pre-tax) is:"),
          correct=pct(roce),
          wrongs=[(pct(pat / (eq + deb)), "PAT used as the return"),
                  (pct(pbt / (eq + deb)), "PBT used — interest not added back"),
                  (pct(ebit / eq), "EBIT divided by shareholders' funds only")],
          steps=[f"PBT = {inr(pat)} ÷ 0.75 = {inr(pbt)}", f"EBIT = {inr(pbt)} + {inr(intr)} = {inr(ebit)}",
                 f"ROCE = {inr(ebit)} ÷ {inr(eq+deb)} = {pct(roce)}"],
          formula="ROCE = EBIT ÷ (Equity + Long-term debt)", trap="Match the return to the capital: EBIT with all long-term funds.")

    s2, gpr, opx, int2, tr2 = 6000000, 0.30, 900000, 120000, 0.25
    pbt2 = s2 * gpr - opx - int2
    npr = pbt2 * (1 - tr2) / s2
    assert round(npr, 4) == 0.0975
    B.add(micro=S("profitability-ratios"), level="L3",
          stem=(f"Sales are {R(s2)}, gross profit ratio {pct(gpr,0)}, operating expenses {R(opx)}, interest {R(int2)} and tax rate {pct(tr2,0)}. "
                "The net profit ratio (after tax) is:"),
          correct=pct(npr),
          wrongs=[(pct(pbt2 / s2), "profit before tax used"),
                  (pct((s2 * gpr - opx) / s2), "operating (EBIT) margin reported"),
                  (pct((s2 * gpr - opx) * (1 - tr2) / s2), "interest ignored; tax applied on EBIT")],
          steps=[f"GP = {inr(s2*gpr)}; PBT = {inr(s2*gpr)} − {inr(opx)} − {inr(int2)} = {inr(pbt2)}",
                 f"PAT = {inr(pbt2*(1-tr2))}; NP ratio = {pct(npr)}"],
          formula="NP ratio = PAT ÷ Sales", trap="Deduct interest before tax.")

    # ================= Leverage =================
    eqf, pref, debs = 2500000, 500000, 2000000
    cg = (pref + debs) / eqf
    B.add(micro=S("leverage-ratios"), level="L3",
          stem=(f"A company has equity share capital and reserves (equity shareholders' funds) of {R(eqf)}, 10% preference share capital of {R(pref)} "
                f"and 12% debentures of {R(debs)}. Its capital gearing ratio is:"),
          correct=f"{cg:.2f}",
          wrongs=[(f"{debs/eqf:.2f}", "preference capital excluded from fixed-cost funds"),
                  (f"{debs/(eqf+pref):.2f}", "preference capital treated as equity"),
                  (f"{(pref+debs)/(eqf+pref+debs):.2f}", "fixed-cost funds divided by total capital")],
          steps=[f"Fixed-cost bearing funds = {inr(pref)} + {inr(debs)} = {inr(pref+debs)}", f"Gearing = {inr(pref+debs)} ÷ {inr(eqf)} = {cg:.2f}"],
          formula="Capital gearing = (Preference capital + Debt) ÷ Equity shareholders' funds",
          trap="Preference capital carries a fixed dividend — it belongs with debt here.")

    # ================= Coverage =================
    pat3, dep3, int3, prin = 1200000, 300000, 240000, 600000
    dscr = (pat3 + dep3 + int3) / (int3 + prin)
    B.add(micro=S("coverage-ratios"), level="L3",
          stem=(f"For a year: profit after tax {R(pat3)}, depreciation {R(dep3)}, interest on term loan {R(int3)}, term-loan principal instalment "
                f"{R(prin)}. The debt service coverage ratio is:"),
          correct=f"{dscr:.2f}",
          wrongs=[(f"{(pat3+int3)/(int3+prin):.2f}", "non-cash depreciation not added back"),
                  (f"{(pat3+dep3)/(int3+prin):.2f}", "interest not added back to earnings"),
                  (f"{(pat3+dep3+int3)/prin:.2f}", "interest omitted from debt service")],
          steps=[f"Earnings for debt service = {inr(pat3)} + {inr(dep3)} + {inr(int3)} = {inr(pat3+dep3+int3)}",
                 f"Debt service = {inr(int3)} + {inr(prin)} = {inr(int3+prin)}", f"DSCR = {dscr:.2f}"],
          formula="DSCR = (PAT + Depreciation + Interest) ÷ (Interest + Principal)", trap="Interest appears in both numerator and denominator.")

    pat4, tr4, int4, dep4 = 750000, 0.25, 250000, 250000
    ebit4 = pat4 / (1 - tr4) + int4
    B.add(micro=S("coverage-ratios"), level="L2",
          stem=f"Profit after tax is {R(pat4)} (tax {pct(tr4,0)}), interest {R(int4)} and depreciation {R(dep4)}. The interest coverage ratio (EBIT basis) is:",
          correct=f"{ebit4/int4:.1f} times",
          wrongs=[(f"{pat4/int4:.1f} times", "PAT used"),
                  (f"{(pat4/(1-tr4))/int4:.1f} times", "PBT used — interest not added back"),
                  (f"{(ebit4+dep4)/int4:.1f} times", "EBITDA used though EBIT basis was asked")],
          steps=[f"PBT = {inr(pat4/(1-tr4))}; EBIT = {inr(ebit4)}", f"ICR = {inr(ebit4)} ÷ {inr(int4)} = {ebit4/int4:.1f}"],
          formula="ICR = EBIT ÷ Interest", trap="Gross up PAT for tax before adding interest.")

    # ================= Market ratios =================
    pat5, pdiv, nsh, mp, dps = 5000000, 500000, 1000000, 90, 1.8
    eps = (pat5 - pdiv) / nsh
    pe = mp / eps
    assert (eps, pe) == (4.5, 20)
    B.add(micro=S("market-ratios"), level="L3",
          stem=(f"PAT is {R(pat5)}; preference dividend {R(pdiv)}; {inr(nsh)} equity shares outstanding; market price ₹{mp}; dividend per equity share ₹{dps}. "
                "The price-earnings ratio is:"),
          correct=f"{pe:.0f} times",
          wrongs=[(f"{mp/(pat5/nsh):.0f} times", "preference dividend not deducted from earnings"),
                  (f"{mp/dps:.0f} times", "price divided by dividend per share"),
                  (f"{eps/mp:.2f} times", "earnings yield (EPS ÷ price) reported")],
          steps=[f"EPS = ({inr(pat5)} − {inr(pdiv)}) ÷ {inr(nsh)} = ₹{eps}", f"P/E = {mp} ÷ {eps} = {pe:.0f}",
                 f"(Dividend yield = {dps} ÷ {mp} = {pct(dps/mp)})"],
          formula="P/E = MPS ÷ EPS; EPS = (PAT − Preference dividend) ÷ Equity shares", trap="EPS belongs to equity shareholders only.")

    ec, res, pc_, nsh6 = 10000000, 24000000, 5000000, 1000000
    bvps = (ec + res) / nsh6
    B.add(micro=S("market-ratios"), level="L2",
          stem=(f"Equity share capital (10 lakh shares of ₹10) is {R(ec)}, reserves and surplus {R(res)}, and preference share capital {R(pc_)}. "
                "Book value per equity share is:"),
          correct=f"₹{bvps:.0f}",
          wrongs=[(f"₹{(ec+res+pc_)/nsh6:.0f}", "preference capital included in equity funds"),
                  (f"₹{res/nsh6:.0f}", "reserves only divided by shares"),
                  (f"₹{ec/nsh6:.0f}", "face value reported")],
          steps=[f"Equity funds = {inr(ec)} + {inr(res)} = {inr(ec+res)}", f"BVPS = {inr(ec+res)} ÷ {inr(nsh6)} = ₹{bvps:.0f}"],
          formula="BVPS = Equity shareholders' funds ÷ Number of equity shares", trap="Exclude preference capital.")

    # ================= Limitations of ratio analysis =================
    B.add(micro=S("limitations-of-ratio"), level="L1",
          stem="Which of the following is a recognised limitation of ratio analysis?",
          correct="Ratios based on historical-cost statements ignore changes in price levels",
          wrongs=[("Ratios cannot be computed from published annual financial statements", "they routinely are"),
                  ("Ratios are unaffected by differences in firms' accounting policies", "the opposite is true"),
                  ("Ratios eliminate the distorting effect of window dressing on statements", "window dressing distorts ratios")],
          steps=["Limitations: historical cost, differing accounting policies, window dressing, lack of standard norms, qualitative factors ignored."],
          formula="Limitations of ratio analysis", trap="Inter-firm comparison is distorted by policy differences.", kind="conceptual")

    # ================= CCC =================
    inv7, cogs7, rec7, cs7, pay7, cp7 = 300000, 1800000, 400000, 2400000, 150000, 1800000
    dio, dso7, dpo = inv7 / cogs7 * 360, rec7 / cs7 * 360, pay7 / cp7 * 360
    ccc = dio + dso7 - dpo
    assert (dio, dso7, dpo, ccc) == (60, 60, 30, 90)
    B.add(micro=S("cash-conversion-cycle"), level="L3",
          stem=("Using average balances and a 360-day year:\n\n" +
                table(["Item", "₹"], [["Average inventory", inr(inv7)], ["Cost of goods sold", inr(cogs7)], ["Average trade receivables", inr(rec7)],
                                      ["Credit sales", inr(cs7)], ["Average trade payables", inr(pay7)], ["Credit purchases", inr(cp7)]]) +
                "\n\nThe cash conversion cycle is:"),
          correct=f"{ccc:.0f} days",
          wrongs=[(f"{dio+dso7+dpo:.0f} days", "payables period added instead of deducted"),
                  (f"{dio+dso7:.0f} days", "operating cycle reported (payables ignored)"),
                  (f"{inv7/cs7*360 + dso7 - dpo:.0f} days", "inventory days computed on sales")],
          steps=[f"DIO = {dio:.0f}; DSO = {dso7:.0f}; DPO = {dpo:.0f}", f"CCC = {dio:.0f} + {dso7:.0f} − {dpo:.0f} = {ccc:.0f} days"],
          formula="CCC = DIO + DSO − DPO", trap="Supplier credit shortens the cash cycle.")

    # ================= Fund flow =================
    inc_pl, tgr, dep8, gw8, pos = 400000, 100000, 120000, 30000, 40000
    ffo = inc_pl + tgr + dep8 + gw8 - pos
    assert ffo == 610000
    B.add(micro=S("fund-flow-sources"), level="L3",
          stem=(f"The credit balance of the statement of profit and loss increased by {R(inc_pl)} after transferring {R(tgr)} to general reserve. "
                f"The year's expenses include depreciation {R(dep8)} and goodwill written off {R(gw8)}; income includes profit on sale of machinery {R(pos)}. "
                "Funds from operations are:"),
          correct=R(ffo),
          wrongs=[(R(ffo - tgr), "transfer to general reserve not added back"),
                  (R(ffo + 2 * pos), "profit on sale of machinery added instead of deducted"),
                  (R(ffo - gw8), "goodwill written off not added back")],
          steps=[f"Net profit = {inr(inc_pl)} + {inr(tgr)} = {inr(inc_pl+tgr)}",
                 f"Add non-fund charges {inr(dep8)} + {inr(gw8)}; less non-operating gain {inr(pos)}", f"FFO = {inr(ffo)}"],
          formula="FFO = Net profit + non-fund/non-operating charges − non-operating income", trap="Appropriations are added back to reach net profit.")

    stmt(B, S("limitations-of-fund"), "L3", "Consider the following statements about the fund flow statement (working-capital concept of funds):",
         ["It does not reveal changes in the cash position, since cash is only one element of working capital.",
          "It can replace the statement of profit and loss as a measure of performance.",
          "It is essentially a rearrangement of data already contained in the financial statements."],
         [1, 3], [([1, 2], "treats fund flow as a substitute for the income statement"),
                  ([2, 3], "treats fund flow as a substitute for the income statement"),
                  ([3], "misses that cash changes are hidden inside working capital")],
         ["1 and 3 are standard limitations.", "2 false — fund flow is supplementary; it cannot measure profitability."],
         "Fund flow complements, never replaces, the income statement.")

    ca_o = {"Inventory": 300000, "Trade receivables": 250000, "Cash": 80000}
    ca_c = {"Inventory": 360000, "Trade receivables": 220000, "Cash": 110000}
    cl_o = {"Trade payables": 190000, "Outstanding expenses": 20000}
    cl_c = {"Trade payables": 240000, "Outstanding expenses": 15000}
    wc_o = sum(ca_o.values()) - sum(cl_o.values())
    wc_c = sum(ca_c.values()) - sum(cl_c.values())
    dwc = wc_c - wc_o
    assert (wc_o, wc_c, dwc) == (420000, 435000, 15000)
    rows = [[k, inr(ca_o[k]), inr(ca_c[k])] for k in ca_o] + [[k, inr(cl_o[k]), inr(cl_c[k])] for k in cl_o]
    dca = sum(ca_c.values()) - sum(ca_o.values())
    dcl = sum(cl_c.values()) - sum(cl_o.values())
    B.add(micro=S("statement-of-changes"), level="L3",
          stem=("Current items of a company (₹):\n\n" + table(["Item", "31-3-2025", "31-3-2026"], rows) +
                "\n\nThe schedule of changes in working capital shows:"),
          correct=f"Increase in working capital of {R(dwc)}",
          wrongs=[(f"Decrease in working capital of {R(dwc)}", "increase in current liabilities treated as increasing working capital"),
                  (f"Increase in working capital of {R(dca)}", "changes in current liabilities ignored"),
                  (f"Increase in working capital of {R(dca + dcl)}", "net increase in current liabilities added to working capital")],
          steps=[f"WC 2025 = {inr(sum(ca_o.values()))} − {inr(sum(cl_o.values()))} = {inr(wc_o)}",
                 f"WC 2026 = {inr(sum(ca_c.values()))} − {inr(sum(cl_c.values()))} = {inr(wc_c)}", f"Increase = {inr(dwc)}"],
          formula="ΔWC = ΔCurrent assets − ΔCurrent liabilities", trap="An increase in a current liability decreases working capital.")

    # ================= Cash flow: classification =================
    B.add(micro=S("as-3-"), level="L1",
          stem="Under AS 3, interest paid by a manufacturing company (not a financial enterprise) is classified as a cash flow from:",
          correct="Financing activities",
          wrongs=[("Operating activities", "the treatment for a financial enterprise"),
                  ("Investing activities", "interest received goes here, not interest paid"),
                  ("Operating or financing, at the company's option", "AS 3 gives no option to non-financial enterprises")],
          steps=["AS 3 para 30–31: for non-financial enterprises, interest paid → financing; interest and dividends received → investing."],
          formula="AS 3 paras 30–31", trap="Financial enterprises classify interest as operating.", kind="conceptual", ref="AS 3 paras 30–33")

    match(B, S("as-3-"), "L2", "Match each item with its treatment in a cash flow statement of a manufacturing company:",
          ["Purchase of a patent for cash", "Conversion of debentures into equity shares", "Cash paid to suppliers of raw materials", "Buy-back of equity shares"],
          ["Operating activity", "Investing activity", "Financing activity", "Not shown (non-cash transaction; disclosed)"],
          [2, 4, 1, 3],
          [([2, 3, 1, 4], "conversion shown as financing although no cash moves"),
           ([1, 4, 2, 3], "patent purchase treated as operating"),
           ([2, 4, 3, 1], "supplier payments and buy-back interchanged")],
          ["Patent → investing.", "Debenture conversion → non-cash, excluded (disclosed).", "Suppliers → operating.", "Buy-back → financing."],
          "Non-cash investing/financing transactions are excluded from the statement.", ref="AS 3 / Ind AS 7 paras 43–44")

    stmt(B, S("operating-investing"), "L3", "Under Ind AS 7 as notified in India, consider:",
         ["For a manufacturing company, interest paid is classified as a financing activity.",
          "For a bank, interest received on loans is classified as an operating activity.",
          "For a manufacturing company, dividends received are classified as an operating activity."],
         [1, 2], [([1, 3], "classifies dividends received as operating for a non-financial entity"),
                  ([2, 3], "applies IFRS options instead of the Indian requirement"),
                  ([1, 2, 3], "classifies dividends received as operating for a non-financial entity")],
         ["Ind AS 7 para 33 (Indian version): for other than financial entities, interest paid → financing; interest and dividends received → investing.",
          "For financial institutions such items are operating."],
         "India removed the IAS 7 choice for non-financial entities.", verify_fact=True, ref="Ind AS 7 paras 33–34 (Indian carve-out)")

    # ================= Cash equivalents =================
    stmt(B, S("cash-and-cash"), "L2", "Which of the following are cash and cash equivalents at the reporting date?",
         ["A treasury bill purchased 20 days ago with 75 days to maturity at purchase.",
          "A 12-month fixed deposit placed 10 months ago (2 months left to maturity).",
          "Listed equity shares held for trading.",
          "Under Ind AS 7, a bank overdraft repayable on demand that forms an integral part of cash management."],
         [1, 4], [([1, 2, 4], "measures the three-month test from the reporting date instead of acquisition"),
                  ([1, 3, 4], "treats equity shares as cash equivalents"),
                  ([1], "excludes the overdraft component under Ind AS 7")],
         ["1: original maturity ≤ 3 months from acquisition — CE.", "2: original maturity 12 months — not CE, whatever the remaining period.",
          "3: equity investments are excluded.", "4: included as a component of cash and cash equivalents (Ind AS 7 para 8)."],
         "The three months run from the date of acquisition.", question="Select the correct answer:", ref="AS 3 para 6; Ind AS 7 paras 7–8")

    # ================= Indirect / direct =================
    pbt9, dep9, loss9, int9, divi9, drs, inv9, crs, taxp = 800000, 150000, 20000, 60000, 30000, 70000, 40000, 25000, 180000
    pre = pbt9 + dep9 + loss9 + int9 - divi9
    cfo = pre - drs + inv9 - crs - taxp
    assert (pre, cfo) == (1000000, 765000)
    B.add(micro=S("ind-as-7-"), level="L3",
          stem=("A manufacturing company reports (Ind AS 7, indirect method):\n\n" +
                table(["Item", "₹"], [["Profit before tax", inr(pbt9)], ["Depreciation", inr(dep9)], ["Loss on sale of equipment", inr(loss9)],
                                      ["Interest expense (paid)", inr(int9)], ["Dividend income (received)", inr(divi9)],
                                      ["Increase in trade receivables", inr(drs)], ["Decrease in inventories", inr(inv9)],
                                      ["Decrease in trade payables", inr(crs)], ["Income tax paid", inr(taxp)]]) +
                "\n\nNet cash from operating activities is:"),
          correct=R(cfo),
          wrongs=[(R(cfo - int9), "interest paid left in operating activities"),
                  (R(pre + drs - inv9 + crs - taxp), "working-capital adjustments with reversed signs"),
                  (R(cfo + divi9), "dividend income left in operating activities")],
          steps=[f"Operating profit before WC changes = {inr(pbt9)} + {inr(dep9)} + {inr(loss9)} + {inr(int9)} − {inr(divi9)} = {inr(pre)}",
                 f"WC: −{inr(drs)} + {inr(inv9)} − {inr(crs)} = {inr(-drs+inv9-crs)}", f"Less tax paid {inr(taxp)} → CFO = {inr(cfo)}"],
          formula="CFO = PBT ± non-cash/non-operating items ± WC changes − tax paid", trap="Interest paid → financing; dividend received → investing.",
          verify_fact=True, ref="Ind AS 7 paras 18–20, 33 (Indian version)")

    sales10, cr_share, od10, cd10, bd = 5000000, 0.80, 600000, 750000, 20000
    coll = sales10 - (cd10 - od10) - bd
    assert coll == 4830000
    B.add(micro=S("direct-vs-indirect"), level="L3",
          stem=(f"Total sales are {R(sales10)}, of which {pct(cr_share,0)} are on credit. Trade receivables rose from {R(od10)} to {R(cd10)} after writing off "
                f"bad debts of {R(bd)}. Under the direct method, cash received from customers is:"),
          correct=R(coll),
          wrongs=[(R(coll + bd), "bad debts written off not deducted"),
                  (R(sales10 + (cd10 - od10) - bd), "increase in receivables added"),
                  (R(sales10 * cr_share - (cd10 - od10) - bd), "cash sales left out")],
          steps=[f"Collections = Sales {inr(sales10)} + opening {inr(od10)} − closing {inr(cd10)} − bad debts {inr(bd)} = {inr(coll)}"],
          formula="Cash from customers = Sales + Opening receivables − Closing receivables − Bad debts written off",
          trap="Written-off debts reduce receivables without any cash inflow.")

    # ---- Case C8: Sharda ratios ----
    g = "ACC-C8-SHARDA"
    esc, oe, tl, cm, tp, ocl = 2000000, 1600000, 2000000, 400000, 800000, 200000
    nca, inv_c, inv_o, trc, cash, pre_ = 4600000, 900000, 700000, 1000000, 400000, 100000
    rev, cogs, opx, intx, taxr = 12000000, 9000000, 1760000, 240000, 0.25
    assert esc + oe + tl + cm + tp + ocl == nca + inv_c + trc + cash + pre_
    ebit = rev - cogs - opx
    clb = cm + tp + ocl
    quick = (inv_c + trc + cash + pre_ - inv_c - pre_) / clb
    debt = tl + cm
    de = debt / (esc + oe)
    ihp = (inv_o + inv_c) / 2 / cogs * 360
    ce = esc + oe + debt
    roce = ebit / ce
    assert (ebit, quick, round(de, 2), ihp, round(roce, 4)) == (1240000, 1.0, 0.67, 32, 0.2067)
    case = ("**Case — Sharda Industries Ltd.** Extracts for FY 2025-26 (₹):\n\n**Balance sheet at 31 March 2026**\n\n" +
            table(["Equity and liabilities", "₹", "Assets", "₹"],
                  [["Equity share capital", inr(esc), "Non-current assets", inr(nca)],
                   ["Other equity", inr(oe), "Inventories", inr(inv_c)],
                   ["Long-term borrowings (10% term loan)", inr(tl), "Trade receivables", inr(trc)],
                   ["Short-term borrowings (current maturities of term loan)", inr(cm), "Cash and cash equivalents", inr(cash)],
                   ["Trade payables", inr(tp), "Prepaid expenses", inr(pre_)],
                   ["Other current liabilities", inr(ocl), "", ""],
                   ["Total", inr(esc+oe+tl+cm+tp+ocl), "Total", inr(nca+inv_c+trc+cash+pre_)]],
                  align=["---", "---:", "---", "---:"]) +
            "\n\n**Statement of profit and loss**\n\n" +
            table(["Item", "₹"], [["Revenue from operations (all credit)", inr(rev)], ["Cost of goods sold", inr(cogs)],
                                  ["Other operating expenses (incl. depreciation)", inr(opx)], ["Finance costs", inr(intx)],
                                  [f"Tax at {pct(taxr,0)}", inr((ebit-intx)*taxr)]]) +
            f"\n\nInventory at 1 April 2025 was {R(inv_o)}. Use a 360-day year; 'debt' means total borrowings.\n\n")
    B.add(micro=S("liquidity-ratios"), level="L4", group=g, stem=case + "Treating inventories and prepaid expenses as non-quick assets, the quick (acid-test) ratio is:",
          correct=f"{quick:.2f}",
          wrongs=[(f"{(trc+cash+pre_)/clb:.2f}", "prepaid expenses treated as quick assets"),
                  (f"{(trc+cash)/(tp+ocl):.2f}", "current maturities of the term loan excluded from current liabilities"),
                  (f"{(inv_c+trc+cash+pre_)/clb:.2f}", "current ratio reported")],
          steps=[f"Quick assets = {inr(trc)} + {inr(cash)} = {inr(trc+cash)}", f"Current liabilities = {inr(cm)} + {inr(tp)} + {inr(ocl)} = {inr(clb)}",
                 f"Quick ratio = {quick:.2f}"],
          formula="Quick ratio = (CA − Inventories − Prepaid) ÷ CL", trap="Current maturities of long-term debt are current liabilities.")
    B.add(micro=S("leverage-ratios"), level="L4", group=g, stem=case + "The debt-equity ratio is:",
          correct=f"{de:.2f}",
          wrongs=[(f"{tl/(esc+oe):.2f}", "current maturities excluded from debt"),
                  (f"{(debt+tp+ocl)/(esc+oe):.2f}", "all outside liabilities treated as debt"),
                  (f"{debt/esc:.2f}", "other equity excluded from equity")],
          steps=[f"Debt = {inr(tl)} + {inr(cm)} = {inr(debt)}", f"Equity = {inr(esc)} + {inr(oe)} = {inr(esc+oe)}", f"D/E = {de:.2f}"],
          formula="D/E = Total borrowings ÷ Shareholders' funds", trap="Reclassification to current does not make the loan any less debt.")
    B.add(micro=S("turnover-ratios"), level="L4", group=g, stem=case + "The inventory holding period is:",
          correct=f"{ihp:.0f} days",
          wrongs=[(f"{inv_c/cogs*360:.0f} days", "closing inventory used instead of average"),
                  (f"{(inv_o+inv_c)/2/rev*360:.0f} days", "revenue used instead of cost of goods sold"),
                  (f"{(inv_o+inv_c)/cogs*360:.0f} days", "opening and closing inventory added, not averaged")],
          steps=[f"Average inventory = ({inr(inv_o)} + {inr(inv_c)}) ÷ 2 = {inr((inv_o+inv_c)/2)}",
                 f"Turnover = {inr(cogs)} ÷ {inr((inv_o+inv_c)/2)} = {cogs/((inv_o+inv_c)/2):.2f}", f"Days = 360 ÷ {cogs/((inv_o+inv_c)/2):.2f} = {ihp:.0f}"],
          formula="Inventory days = Average inventory ÷ COGS × 360", trap="Inventory is at cost, so compare with COGS.")
    B.add(micro=S("profitability-ratios"), level="L4", group=g, stem=case + "Return on capital employed (pre-tax; capital employed = shareholders' funds + total borrowings) is:",
          correct=pct(roce),
          wrongs=[(pct((ebit - intx) * (1 - taxr) / ce), "PAT used as the return"),
                  (pct(ebit / (esc + oe + tl)), "current maturities excluded from capital employed"),
                  (pct(ebit / (nca + inv_c + trc + cash + pre_)), "total assets used as capital employed")],
          steps=[f"EBIT = {inr(rev)} − {inr(cogs)} − {inr(opx)} = {inr(ebit)}", f"Capital employed = {inr(esc+oe)} + {inr(debt)} = {inr(ce)}",
                 f"ROCE = {pct(roce)}"],
          formula="ROCE = EBIT ÷ Capital employed", trap="Keep numerator and denominator on the same (pre-interest) basis.")

    # ---- Case C9: Tirupati cash flow ----
    g = "ACC-C9-TIRUPATI"
    o = dict(esc=1000000, re=400000, deb=500000, tp=220000, pt=60000, ppe=1200000, inv=200000, stock=320000, rec=290000, cash=170000)
    c = dict(esc=1200000, re=530000, deb=300000, tp=260000, pt=80000, ppe=1360000, inv=150000, stock=390000, rec=260000)
    liab = ["esc", "re", "deb", "tp", "pt"]
    assets = ["ppe", "inv", "stock", "rec"]
    assert sum(o[k] for k in liab) == sum(o[k] for k in assets) + o["cash"]
    c["cash"] = sum(c[k] for k in liab) - sum(c[k] for k in assets)
    patx, divp, dep, disp_ca, disp_px, inv_px, taxe, intp = 230000, 100000, 140000, 60000, 45000, 70000, 100000, 40000
    assert o["re"] + patx - divp == c["re"]
    pbt = patx + taxe
    inv_ca = o["inv"] - c["inv"]
    gain = inv_px - inv_ca
    lossm = disp_ca - disp_px
    taxpaid = o["pt"] + taxe - c["pt"]
    wc = -(c["stock"] - o["stock"]) + (o["rec"] - c["rec"]) + (c["tp"] - o["tp"])
    cfo = pbt + dep + lossm - gain + intp + wc - taxpaid
    capex = c["ppe"] - o["ppe"] + dep + disp_ca
    cfi = -capex + disp_px + inv_px
    cff = (c["esc"] - o["esc"]) - (o["deb"] - c["deb"]) - intp - divp
    assert (cfo, capex, cfi, cff) == (425000, 360000, -245000, -140000)
    assert cfo + cfi + cff == c["cash"] - o["cash"]
    names = {"esc": "Equity share capital", "re": "Retained earnings", "deb": "10% Debentures", "tp": "Trade payables",
             "pt": "Provision for tax", "ppe": "Property, plant and equipment (net)", "inv": "Long-term investments",
             "stock": "Inventories", "rec": "Trade receivables", "cash": "Cash and cash equivalents"}
    case = ("**Case — Tirupati Ltd (manufacturer; Ind AS 7 as notified in India).** Balance sheets at 31 March (₹):\n\n" +
            table(["Item", "2025", "2026"], [[names[k], inr(o[k]), inr(c[k])] for k in liab + assets + ["cash"]]) +
            f"\n\nAdditional information for FY 2025-26: profit after tax {R(patx)} (tax expense {R(taxe)}); dividend paid {R(divp)}; depreciation {R(dep)}; "
            f"a machine with carrying amount {R(disp_ca)} was sold for {R(disp_px)}; investments with carrying amount {R(inv_ca)} were sold for {R(inv_px)}; "
            f"debentures were redeemed at par; interest paid on debentures {R(intp)} (included in finance costs); new shares were issued at par for cash.\n\n")
    B.add(micro=S("ind-as-7-"), level="L4", group=g, stem=case + "Net cash from operating activities is:",
          correct=R(cfo),
          wrongs=[(R(cfo - taxe + taxpaid), "tax expense deducted instead of tax paid"),
                  (R(cfo - intp), "interest paid left in operating activities"),
                  (R(cfo - 2 * lossm + 2 * gain), "loss on machine and gain on investments with reversed signs")],
          steps=[f"PBT = {inr(patx)} + {inr(taxe)} = {inr(pbt)}",
                 f"+ depreciation {inr(dep)} + loss on machine {inr(lossm)} − gain on investments {inr(gain)} + interest {inr(intp)} = {inr(pbt+dep+lossm-gain+intp)}",
                 f"WC: inventories −{inr(c['stock']-o['stock'])}, receivables +{inr(o['rec']-c['rec'])}, payables +{inr(c['tp']-o['tp'])} → {inr(wc)}",
                 f"Tax paid = {inr(o['pt'])} + {inr(taxe)} − {inr(c['pt'])} = {inr(taxpaid)}", f"CFO = {inr(cfo)}"],
          formula="Indirect method", trap="Use tax paid (provision account), not tax expense.", verify_fact=True, ref="Ind AS 7 paras 18–20, 33, 35")
    B.add(micro=S("operating-investing"), level="L4", group=g, stem=case + "Cash paid for purchase of property, plant and equipment is:",
          correct=R(capex),
          wrongs=[(R(c["ppe"] - o["ppe"]), "net change in PPE taken as purchases"),
                  (R(c["ppe"] - o["ppe"] + dep), "carrying amount of machine sold not added back"),
                  (R(c["ppe"] - o["ppe"] + dep + disp_px), "sale proceeds used instead of carrying amount of the machine sold")],
          steps=[f"Closing {inr(c['ppe'])} = Opening {inr(o['ppe'])} + Purchases − Depreciation {inr(dep)} − CA of disposal {inr(disp_ca)}",
                 f"Purchases = {inr(capex)}"],
          formula="Purchases = Closing − Opening + Depreciation + CA of disposals", trap="Reconstruct the PPE account.")
    B.add(micro=S("operating-investing"), level="L4", group=g, stem=case + "Net cash used in investing activities is:",
          correct=R(-cfi) + " (outflow)",
          wrongs=[(R(capex - disp_px - inv_ca) + " (outflow)", "investments' sale recorded at carrying amount instead of proceeds"),
                  (R(capex - disp_ca - inv_px) + " (outflow)", "machine's sale recorded at carrying amount instead of proceeds"),
                  (R(capex - disp_px) + " (outflow)", "sale of investments omitted")],
          steps=[f"−{inr(capex)} + {inr(disp_px)} + {inr(inv_px)} = −{inr(-cfi)}"],
          formula="CFI = −Capex + Proceeds from disposals", trap="Actual proceeds, not carrying amounts, are cash flows.")
    B.add(micro=S("ind-as-7-"), level="L4", group=g, stem=case + "Net cash from (used in) financing activities is:",
          correct=f"{R(-cff)} (outflow)",
          wrongs=[(f"{R(-cff - intp)} (outflow)", "interest paid classified as operating"),
                  (f"{R(-cff - divp)} (outflow)", "dividends paid classified as operating"),
                  (f"{R(cff + (o['deb']-c['deb']))} (inflow)", "debenture redemption shown in investing activities")],
          steps=[f"Share issue +{inr(c['esc']-o['esc'])}; redemption −{inr(o['deb']-c['deb'])}; interest −{inr(intp)}; dividend −{inr(divp)}",
                 f"CFF = −{inr(-cff)}; check: {inr(cfo)} − {inr(-cfi)} − {inr(-cff)} = {inr(c['cash']-o['cash'])} = change in cash"],
          formula="CFF = issues − redemptions − interest paid − dividends paid (non-financial entity, Indian Ind AS 7)",
          trap="Both interest and dividends paid are financing here.", verify_fact=True, ref="Ind AS 7 paras 17, 33–34")
