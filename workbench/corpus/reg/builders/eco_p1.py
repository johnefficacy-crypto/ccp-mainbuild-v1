"""ECO part 1 — National income accounting (48 Q: L1 9, L2 14, L3 13, L4 12)."""
from eco_common import mk, cr, n, tbl, items, stmts, inr, R, pct

SNA = "SNA 2008 / MoSPI national accounts (base 2022-23 series, released Feb 2026)."


def add_all(B):
    q = mk(B)

    # ======================= L1 =======================
    q("gdp-gnp", "L1",
      "The difference between Gross National Product and Gross Domestic Product of an economy (both at market prices) is equal to:",
      "Net factor income from abroad",
      [("Net indirect taxes", "confuses market-price vs factor-cost gap with domestic vs national gap"),
       ("Consumption of fixed capital", "confuses gross vs net gap"),
       ("Net current transfers from abroad", "treats remittances/transfers as factor income")],
      ["Domestic → national: add factor incomes earned by residents abroad and deduct factor incomes earned by non-residents here.",
       "GNP_MP − GDP_MP = Net factor income from abroad (NFIA).",
       "Net indirect taxes separate MP from FC; depreciation separates gross from net."],
      "GNP = GDP + NFIA", "Three different 'bridges' — NFIA, depreciation, net indirect taxes — each links a different pair of aggregates.",
      kind="conceptual")

    q("factor-cost", "L1",
      "GDP at market prices exceeds GDP at factor cost by:",
      "Indirect taxes minus subsidies",
      [("Indirect taxes only", "subsidies ignored"),
       ("Indirect taxes plus subsidies", "subsidies added instead of deducted"),
       ("Direct taxes minus transfer payments", "direct taxes do not enter the MP–FC bridge")],
      ["Market prices include indirect taxes and are lowered by subsidies.",
       "MP − FC = Indirect taxes − Subsidies = Net indirect taxes (NIT)."],
      "GDP_MP = GDP_FC + NIT", "Subsidies reduce market price below factor cost, so they are subtracted from indirect taxes.",
      kind="conceptual")

    q("gva-at-basic", "L1",
      "In India's national accounts (SNA 2008 based), GVA at basic prices is obtained from GVA at factor cost by:",
      "Adding production taxes and deducting production subsidies",
      [("Adding product taxes and deducting product subsidies", "product taxes bridge GVA at basic prices to GDP, not FC to basic prices"),
       ("Adding all indirect taxes and deducting all subsidies", "this jumps straight from factor cost to market prices"),
       ("Deducting consumption of fixed capital", "gross vs net confusion")],
      ["Production taxes/subsidies (e.g. land revenue, stamp duty, some input subsidies) are paid irrespective of output quantity.",
       "GVA_basic = GVA_FC + production taxes − production subsidies.",
       "GDP = ΣGVA_basic + product taxes − product subsidies."],
      "GVA_BP = GVA_FC + (Production taxes − Production subsidies)", "Two tax layers: production taxes (FC→basic) and product taxes (basic→GDP).",
      kind="conceptual", verify_fact=True, ref=SNA)

    q("measurement-methods", "L1",
      "While estimating national income by the income method, which of the following is excluded?",
      "Old-age pension paid by the government",
      [("Mixed income of self-employed persons", "mixed income is a factor income and is included"),
       ("Employers' contribution to social security schemes", "part of compensation of employees"),
       ("Imputed rent of owner-occupied houses", "imputed factor income is included")],
      ["Only factor incomes earned for current productive services enter the income method.",
       "Old-age pension is a transfer payment — no current productive service is rendered.",
       "Mixed income, employer contributions and imputed rent are factor incomes."],
      "NDP_FC = Compensation of employees + Operating surplus + Mixed income", "Transfer payments are unilateral — they add to personal income, not national income.",
      kind="conceptual")

    q("limitations", "L1",
      "Which of the following is a recognised limitation of GDP as a measure of economic welfare?",
      "Unpaid household work by family members is excluded",
      [("Imputed rent of owner-occupied dwellings is excluded", "imputed rent IS included, so this is not a limitation"),
       ("Exports are counted but imports are ignored entirely", "imports are deducted in the expenditure method"),
       ("Government final consumption spending is excluded", "GFCE is a component of GDP")],
      ["Non-market household services are outside the production boundary for services.",
       "Their exclusion under-states welfare and distorts cross-country comparison.",
       "Imputed rent and GFCE are included; imports are netted out."],
      "—", "Owner-occupied housing is the famous exception that IS imputed.",
      kind="conceptual")

    ni, popn = 4_20_000, 3.5   # crore rupees, crore persons
    pci = ni * 1e7 / (popn * 1e7)
    assert pci == 120000
    q("per-capita", "L1",
      f"A country's national income (NNP at factor cost) is {cr(ni)} and its population is {n(popn)} crore. Per capita income is:",
      R(pci),
      [(R(ni * 1e7 / (popn * 1e5)), "population read in lakh instead of crore"),
       (R(ni * 1e7 / (popn * 1e8)), "decimal slip: population read as 35 crore"),
       (R(pci / 12), "reported as monthly rather than annual")],
      [f"₹{inr(ni)} crore ÷ {n(popn)} crore persons = ₹{inr(pci)} per person per year."],
      "Per capita income = National income ÷ Population", "Keep units consistent: crore ÷ crore cancels to rupees.")

    nom, real = 2_52_000, 2_10_000
    defl = nom / real * 100
    q("real-vs-nominal", "L1",
      f"Nominal GDP is {cr(nom)} and real GDP (at base-year prices) is {cr(real)}. The GDP deflator is:",
      n(defl, 1),
      [(n(real / nom * 100, 2), "ratio inverted (real ÷ nominal)"),
       (n(defl - 100, 1), "inflation since base year reported as the index"),
       (n(nom / real, 2), "not multiplied by 100")],
      [f"Deflator = {inr(nom)} ÷ {inr(real)} × 100 = {n(defl,1)}"],
      "GDP deflator = Nominal GDP ÷ Real GDP × 100", "The index is 120, the price rise since base is 20%.")

    q("personal-income", "L1",
      "Which of the following is included in personal income but NOT in national income?",
      "Current transfers to households from government",
      [("Undistributed profits retained by companies", "in national income but deducted to reach personal income"),
       ("Corporation tax paid by private companies", "in national income but deducted to reach personal income"),
       ("Wages paid by the government to its employees", "a factor income in both")],
      ["Personal income = income actually received by households, including transfers.",
       "Transfers are not payments for productive services, so they are outside national income.",
       "Corporate tax and retained profits are in national income but never reach households."],
      "PI = NI − Corporate tax − Undistributed profits − Social security contributions (net) + Transfers", "Direction matters: transfers are added, corporate retentions are removed.",
      kind="conceptual")

    q("nnp-at-factor", "L1",
      "In standard macro-economic usage, 'national income' refers to:",
      "Net National Product at factor cost",
      [("Gross Domestic Product at market prices", "headline output measure, not national income"),
       ("Net Domestic Product at factor cost", "that is domestic income; NFIA missing"),
       ("Gross National Product at market prices", "gross and at market prices")],
      ["National income = factor incomes earned by normal residents, net of depreciation.",
       "That is NNP at factor cost = NDP_FC + NFIA."],
      "NI = NNP_FC = NDP_FC + NFIA", "Domestic income (NDP_FC) and national income (NNP_FC) differ by NFIA.",
      kind="conceptual")

    # ======================= L2 =======================
    gdp, fia, fpa = 2_40_000, 6_500, 9_800
    nfia = fia - fpa
    q("gdp-gnp", "L2",
      f"For an economy: GDP at market prices {cr(gdp)}; factor income received from abroad {cr(fia)}; factor income paid to abroad {cr(fpa)}. GNP at market prices is:",
      cr(gdp + nfia),
      [(cr(gdp - nfia), "NFIA sign reversed"),
       (cr(gdp + fia), "only receipts from abroad added"),
       (cr(gdp - fpa), "only payments to abroad deducted")],
      [f"NFIA = {inr(fia)} − {inr(fpa)} = {inr(nfia)}",
       f"GNP_MP = {inr(gdp)} + ({inr(nfia)}) = {inr(gdp+nfia)}"],
      "GNP_MP = GDP_MP + NFIA", "A net outflow of factor income makes GNP smaller than GDP.")

    g, d, it, sb = 5_000, 450, 620, 170
    ndpfc = g - d - (it - sb)
    assert ndpfc == 4100
    q("factor-cost", "L2",
      f"GDP at market prices {cr(g)}; consumption of fixed capital {cr(d)}; indirect taxes {cr(it)}; subsidies {cr(sb)}. NDP at factor cost is:",
      cr(ndpfc),
      [(cr(g - d - it - sb), "subsidies deducted instead of added back"),
       (cr(g - d - it), "subsidies ignored"),
       (cr(g - d), "net indirect taxes not removed (this is NDP_MP)")],
      [f"NIT = {it} − {sb} = {it-sb}", f"NDP_FC = {inr(g)} − {d} − {it-sb} = {inr(ndpfc)}"],
      "NDP_FC = GDP_MP − CFC − (IT − Subsidies)", "Subsidies are added back when moving from MP to FC.")

    sales, dstk, rm, power, wages, cfc, nit = 800, 50, 350, 40, 180, 30, 25
    nva = sales + dstk - rm - power - cfc - nit
    assert nva == 405
    q("measurement-methods", "L2",
      "A manufacturing firm reports (₹ lakh):\n\n" + tbl(["Item", "₹ lakh"], [
          ("Sales", sales), ("Change in stock (closing − opening)", f"+{dstk}"), ("Purchase of raw materials", rm),
          ("Power and fuel purchased", power), ("Wages and salaries", wages), ("Consumption of fixed capital", cfc),
          ("Net indirect taxes", nit)]) +
      "\n\nIts net value added at factor cost is:",
      f"₹{nva} lakh",
      [(f"₹{nva - wages} lakh", "wages deducted as if intermediate consumption"),
       (f"₹{nva - dstk} lakh", "change in stock ignored"),
       (f"₹{nva + nit} lakh", "net indirect taxes not deducted (NVA at MP)")],
      [f"Value of output = {sales} + {dstk} = {sales+dstk}",
       f"GVA_MP = {sales+dstk} − ({rm}+{power}) = {sales+dstk-rm-power}",
       f"NVA_FC = {sales+dstk-rm-power} − {cfc} − {nit} = {nva}"],
      "NVA_FC = Sales + ΔStock − Intermediate consumption − CFC − NIT", "Wages are a factor payment out of value added, not a deduction from it.")

    gbp, ptx, psb = 1_80_000, 21_000, 6_500
    q("gva-at-basic", "L2",
      f"GVA at basic prices is {cr(gbp)}; product taxes {cr(ptx)}; product subsidies {cr(psb)}. GDP is:",
      cr(gbp + ptx - psb),
      [(cr(gbp + ptx + psb), "product subsidies added"),
       (cr(gbp + ptx), "product subsidies ignored"),
       (cr(gbp - psb), "product taxes ignored")],
      [f"GDP = {inr(gbp)} + {inr(ptx)} − {inr(psb)} = {inr(gbp+ptx-psb)}"],
      "GDP = GVA_BP + Product taxes − Product subsidies", "Product taxes (GST, customs etc.) are the bridge from basic prices to GDP.",
      verify_fact=True, ref=SNA)

    gn, gp = 0.114, 0.042
    rg = (1 + gn) / (1 + gp) - 1
    q("real-vs-nominal", "L2",
      f"Nominal GDP grows by {pct(gn,1)} and the GDP deflator rises by {pct(gp,1)} in the same year. The exact growth of real GDP is:",
      pct(rg),
      [(pct(gn - gp), "approximation (subtraction) instead of exact deflation"),
       (pct(gn + gp), "inflation added instead of removed"),
       (pct((1 + gn) * (1 + gp) - 1), "compounded instead of deflated")],
      [f"Real growth = (1 + {gn}) ÷ (1 + {gp}) − 1 = {pct(rg)}"],
      "(1 + g_real) = (1 + g_nominal) ÷ (1 + π_deflator)", "Subtraction is only an approximation; the exact answer is slightly lower.")

    gi, gpop = 0.09, 0.015
    gpc = (1 + gi) / (1 + gpop) - 1
    q("per-capita", "L2",
      f"Real national income rises by {pct(gi,1)} and population by {pct(gpop,1)} in a year. The exact growth in real per capita income is:",
      pct(gpc),
      [(pct(gi - gpop), "approximation by subtraction"),
       (pct((1 + gi) * (1 + gpop) - 1), "population growth compounded instead of divided out"),
       (pct(gi), "population growth ignored")],
      [f"(1.09 ÷ 1.015) − 1 = {pct(gpc)}"],
      "(1 + g_pci) = (1 + g_income) ÷ (1 + g_population)", "Per capita growth is a ratio, not a difference.")

    pi_, dpt, misc, ctax = 45_000, 5_200, 600, 3_000
    pdi = pi_ - dpt - misc
    q("personal-income", "L2",
      f"Personal income {cr(pi_)}; direct personal taxes {cr(dpt)}; miscellaneous receipts of government administrative departments (fees, fines) {cr(misc)}; corporation tax {cr(ctax)}. Personal disposable income is:",
      cr(pdi),
      [(cr(pdi - ctax), "corporation tax deducted again (already removed before personal income)"),
       (cr(pi_ - dpt), "fees and fines not deducted"),
       (cr(pi_ - misc), "direct personal taxes not deducted")],
      [f"PDI = {inr(pi_)} − {inr(dpt)} − {misc} = {inr(pdi)}"],
      "PDI = PI − Direct personal taxes − Misc. receipts of govt. admin. departments", "Corporation tax is deducted at the private-income → personal-income stage, not here.")

    C, I, G, X, M, sh = 600, 180, 140, 90, 110, 40
    gdpe = C + I + G + X - M
    q("measurement-methods", "L2",
      f"Private final consumption {cr(C)}; gross investment {cr(I)}; government final consumption {cr(G)}; exports {cr(X)}; imports {cr(M)}; purchase of second-hand houses {cr(sh)}. GDP at market prices is:",
      cr(gdpe),
      [(cr(gdpe + sh), "second-hand transactions counted as current production"),
       (cr(C + I + G + X + M), "imports added instead of deducted"),
       (cr(C + I + G + X), "imports ignored")],
      [f"GDP = {C} + {I} + {G} + ({X} − {M}) = {gdpe}", "Second-hand purchases are transfers of existing assets — excluded."],
      "GDP_MP = C + I + G + (X − M)", "Only the brokerage on a second-hand sale is current output, not the sale value.")

    ce_in, ce_out, inv_r, inv_p, rem = 120, 80, 300, 520, 900
    nf = ce_in - ce_out + inv_r - inv_p
    q("gdp-gnp", "L2",
      "From the following (₹ crore), net factor income from abroad is:\n\n" + items([
          ("Compensation of residents working abroad (short-term)", ce_in),
          ("Compensation of non-residents working in the country", ce_out),
          ("Investment income received from abroad", inv_r),
          ("Investment income paid to abroad", inv_p),
          ("Remittances received from emigrant workers (personal transfers)", rem)]),
      cr(nf),
      [(cr(nf + rem), "personal transfers treated as factor income"),
       (cr(-nf), "sign reversed"),
       (cr(inv_r - inv_p), "compensation of employees ignored")],
      [f"NFIA = ({ce_in} − {ce_out}) + ({inv_r} − {inv_p}) = {nf}",
       "Remittances are secondary income (current transfers), not factor income."],
      "NFIA = Net compensation of employees + Net property & entrepreneurial income", "Workers' remittances move NDI/GNDI, not GNP.")

    rent, intr, prof, roy, divd = 300, 250, 900, 60, 400
    os_ = rent + intr + prof + roy
    q("measurement-methods", "L2",
      f"Rent {cr(rent)}; interest {cr(intr)}; royalty {cr(roy)}; profits {cr(prof)} (of which dividends {cr(divd)}, corporation tax 200 and undistributed profits 300). Operating surplus is:",
      cr(os_),
      [(cr(os_ + divd), "dividends added again although already inside profits"),
       (cr(os_ - roy), "royalty omitted from property income"),
       (cr(rent + intr + roy + divd), "only distributed profits counted")],
      [f"OS = Rent + Interest + Royalty + Profits = {rent}+{intr}+{roy}+{prof} = {os_}",
       "Profit = dividends + corporation tax + undistributed profit, so dividends are already counted."],
      "Operating surplus = Rent + Royalty + Interest + Profit", "Components of profit must not be added separately.")

    q("measurement-methods", "L2",
      "Which of the following purchases is a FINAL good in national income accounting?",
      "A tractor bought by a farmer",
      [("Fertiliser bought by a farmer", "used up in the year's production — intermediate"),
       ("Flour bought by a bakery", "raw material — intermediate"),
       ("Electricity bought by a steel plant", "input used up — intermediate")],
      ["Final goods are bought for final consumption or for investment (capital formation).",
       "A tractor is a fixed asset used over many years — gross fixed capital formation.",
       "Inputs used up within the year are intermediate consumption."],
      "Final = consumption or capital formation; Intermediate = used up in production within the period", "Durability and use, not the buyer's identity, decide the classification.",
      kind="conceptual")

    nomv, realv = 3_15_000, 2_80_000
    dv = nomv / realv * 100
    q("real-vs-nominal", "L2",
      f"GDP at current prices {cr(nomv)}; GDP at constant (base-year) prices {cr(realv)}. The implicit price deflator and the price rise since the base year are respectively:",
      f"{n(dv,1)} and {n(dv-100,1)}%",
      [(f"{n(realv/nomv*100,2)} and {n(100-realv/nomv*100,2)}%", "ratio inverted"),
       (f"{n(dv-100,1)} and {n(dv,1)}%", "index and rate interchanged"),
       (f"{n(dv,1)} and {n((nomv-realv)/nomv*100,2)}%", "price rise measured on current-price base")],
      [f"Deflator = {inr(nomv)} ÷ {inr(realv)} × 100 = {n(dv,1)}", f"Price rise = {n(dv,1)} − 100 = {n(dv-100,1)}%"],
      "Deflator = Nominal ÷ Real × 100", "Base for price rise is the base-year index (100).")

    nnpmp, nnpfc, sub = 8_400, 7_600, 350
    itx = nnpmp - nnpfc + sub
    q("factor-cost", "L2",
      f"NNP at market prices {cr(nnpmp)}; NNP at factor cost {cr(nnpfc)}; subsidies {cr(sub)}. Indirect taxes are:",
      cr(itx),
      [(cr(nnpmp - nnpfc), "net indirect taxes reported as gross indirect taxes"),
       (cr(nnpmp - nnpfc - sub), "subsidies deducted instead of added"),
       ("Cannot be determined without consumption of fixed capital", "depreciation is irrelevant — both aggregates are net")],
      [f"NIT = {inr(nnpmp)} − {inr(nnpfc)} = {nnpmp-nnpfc}", f"Indirect taxes = NIT + Subsidies = {nnpmp-nnpfc} + {sub} = {itx}"],
      "IT = (NNP_MP − NNP_FC) + Subsidies", "The MP–FC gap is NET indirect taxes.")

    ndp, nfia2, cfc2, nit2 = 9_000, -250, 700, 900
    nnpmp2 = ndp + nfia2 + nit2
    q("gdp-gnp", "L2",
      f"NDP at factor cost {cr(ndp)}; net factor income from abroad {cr(nfia2)}; consumption of fixed capital {cr(cfc2)}; net indirect taxes {cr(nit2)}. NNP at market prices is:",
      cr(nnpmp2),
      [(cr(ndp - nfia2 + nit2), "NFIA sign reversed"),
       (cr(nnpmp2 + cfc2), "depreciation added (this is GNP_MP)"),
       (cr(ndp + nfia2), "net indirect taxes omitted (this is NNP_FC)")],
      [f"NNP_MP = NDP_FC + NFIA + NIT = {inr(ndp)} − 250 + {nit2} = {inr(nnpmp2)}"],
      "NNP_MP = NDP_FC + NFIA + NIT", "Move one bridge at a time: domestic→national, FC→MP.")

    # ======================= L3 =======================
    coe, esc, rnt, it3, roy3, pr3, mi3, nfa3, pen, cg, dv3 = 5_400, 350, 600, 450, 80, 1_300, 2_100, -150, 200, 120, 500
    ni3 = coe + esc + rnt + it3 + roy3 + pr3 + mi3 + nfa3
    assert ni3 == 10130
    q("nnp-at-factor", "L3",
      "Compute national income (NNP at factor cost) by the income method (₹ crore):\n\n" + items([
          ("Compensation of employees (excluding employers' social security contribution)", coe),
          ("Employers' contribution to social security schemes", esc), ("Rent", rnt), ("Interest", it3),
          ("Royalty", roy3), ("Profits", pr3), ("Dividends (paid out of profits)", dv3),
          ("Mixed income of self-employed", mi3), ("Net factor income from abroad", nfa3),
          ("Old-age pensions paid by government", pen), ("Capital gains on sale of shares", cg)]),
      cr(ni3),
      [(cr(ni3 + dv3), "dividends double-counted (already in profits)"),
       (cr(ni3 - esc), "employers' social security contribution omitted from compensation"),
       (cr(ni3 - nfa3), "NFIA not applied (this is NDP_FC)")],
      [f"Compensation of employees = {inr(coe)} + {esc} = {inr(coe+esc)}",
       f"Operating surplus = {rnt}+{it3}+{roy3}+{inr(pr3)} = {inr(rnt+it3+roy3+pr3)}",
       f"NDP_FC = {inr(coe+esc)} + {inr(rnt+it3+roy3+pr3)} + {inr(mi3)} = {inr(ni3-nfa3)}",
       f"NNP_FC = {inr(ni3-nfa3)} + ({nfa3}) = {inr(ni3)}",
       "Excluded: dividends (inside profits), pensions (transfer), capital gains (not current production)."],
      "NNP_FC = COE + OS + MI + NFIA", "Every excluded line in the table is there to catch one specific habit.")

    pf, gf, gdcf, nx, cf4, it4, sb4, nf4, shr, land, ndi = 7_000, 1_500, 2_200, -300, 600, 900, 150, 80, 400, 250, 300
    gdp4 = pf + gf + gdcf + nx
    ni4 = gdp4 - cf4 - (it4 - sb4) + nf4
    assert ni4 == 9130
    q("nnp-at-factor", "L3",
      "Compute national income by the expenditure method (₹ crore):\n\n" + items([
          ("Private final consumption expenditure", pf), ("Government final consumption expenditure", gf),
          ("Gross domestic capital formation", gdcf), ("Net exports", nx), ("Consumption of fixed capital", cf4),
          ("Indirect taxes", it4), ("Subsidies", sb4), ("Net factor income from abroad", nf4),
          ("Purchase of shares by households", shr), ("Purchase of land by firms", land),
          ("Interest on national debt", ndi)]),
      cr(ni4),
      [(cr(ni4 + shr), "purchase of shares treated as investment"),
       (cr(gdp4 - cf4 - (it4 + sb4) + nf4), "subsidies deducted instead of added back"),
       (cr(ni4 - 2 * nf4), "NFIA subtracted instead of added")],
      [f"GDP_MP = {inr(pf)} + {inr(gf)} + {inr(gdcf)} + ({nx}) = {inr(gdp4)}",
       f"NNP_FC = {inr(gdp4)} − {cf4} − ({it4} − {sb4}) + {nf4} = {inr(ni4)}",
       "Shares and land are financial/existing-asset transactions; interest on national debt is a transfer."],
      "NNP_FC = (C + G + I + NX) − CFC − NIT + NFIA", "Financial investment is not capital formation.")

    sec = [("Primary", 4_000, 1_500), ("Secondary", 6_500, 3_800), ("Tertiary", 5_200, 1_700)]
    gva5 = sum(o - ic for _, o, ic in sec)
    cf5, nit5, nf5 = 900, 700, -60
    ni5 = gva5 - cf5 - nit5 + nf5
    assert gva5 == 8700 and ni5 == 7040
    q("measurement-methods", "L3",
      "Using the value-added (product) method, find national income (₹ crore):\n\n" +
      tbl(["Sector", "Value of output", "Intermediate consumption"], [(s, inr(o), inr(ic)) for s, o, ic in sec]) +
      f"\n\nConsumption of fixed capital {inr(cf5)}; net indirect taxes {nit5}; net factor income from abroad {nf5}.",
      cr(ni5),
      [(cr(gva5 - cf5 + nf5), "net indirect taxes not deducted (NNP_MP)"),
       (cr(gva5 - cf5 - nit5 - nf5), "NFIA sign reversed"),
       (cr(gva5 - cf5 - nit5), "NFIA ignored (domestic income)")],
      [f"GVA_MP = (4,000−1,500) + (6,500−3,800) + (5,200−1,700) = {inr(gva5)}",
       f"NNP_FC = {inr(gva5)} − {cf5} − {nit5} + ({nf5}) = {inr(ni5)}"],
      "NNP_FC = ΣGVA_MP − CFC − NIT + NFIA", "Close options differ by a single bridge item.")

    gfc, prt, prs, pdt, pds = 20_000, 600, 250, 2_300, 900
    gvab = gfc + prt - prs
    q("gva-at-basic", "L3",
      "From the following (₹ crore), GVA at basic prices is:\n\n" + items([
          ("GVA at factor cost", gfc), ("Production taxes", prt), ("Production subsidies", prs),
          ("Product taxes", pdt), ("Product subsidies", pds)]),
      cr(gvab),
      [(cr(gvab + pdt - pds), "went all the way to GDP"),
       (cr(gfc + pdt - pds), "product taxes used instead of production taxes"),
       (cr(gfc + prt + prs), "production subsidies added")],
      [f"GVA_BP = {inr(gfc)} + {prt} − {prs} = {inr(gvab)}",
       f"(GDP would be {inr(gvab)} + {inr(pdt)} − {pds} = {inr(gvab+pdt-pds)}.)"],
      "GVA_BP = GVA_FC + production taxes − production subsidies", "Product taxes belong to the next step (GDP).",
      verify_fact=True, ref=SNA)

    y1n, y2n, d2 = 200, 231, 105
    rg6 = (y2n / (d2 / 100)) / y1n - 1
    assert abs(rg6 - 0.10) < 1e-9
    q("real-vs-nominal", "L3",
      "An economy's data (₹ thousand crore):\n\n" + tbl(["Year", "Nominal GDP", "GDP deflator"],
          [("Year 1 (base)", y1n, 100), ("Year 2", y2n, d2)]) + "\n\nReal GDP growth in Year 2 is:",
      pct(rg6),
      [(pct(y2n / y1n - 1), "nominal growth reported"),
       (pct(y2n / y1n - 1 - (d2 / 100 - 1)), "approximation: nominal growth minus inflation"),
       (pct(y2n * d2 / 100 / y1n - 1), "nominal GDP multiplied (not divided) by the deflator")],
      [f"Real GDP Year 2 = {y2n} ÷ 1.05 = {n(y2n/1.05)}", f"Growth = {n(y2n/1.05)} ÷ {y1n} − 1 = {pct(rg6)}"],
      "Real = Nominal ÷ (Deflator/100)", "Deflate first, then compute growth.")

    q("measurement-methods", "L3",
      "Which of the following are included in the GDP of India?\n\n" + stmts([
          "Imputed rent of owner-occupied dwellings",
          "Value of own-account production of goods retained for self-consumption (e.g. farm produce kept by a farm household)",
          "Services of homemakers within their own household",
          "Commission earned by a dealer on the sale of a second-hand car"]),
      "1, 2 and 4 only",
      [("1 and 2 only", "brokerage on second-hand sale wrongly excluded"),
       ("1, 2, 3 and 4", "unpaid household services wrongly included"),
       ("2 and 4 only", "imputed rent wrongly excluded")],
      ["Own-account production of goods and owner-occupied housing services are inside the SNA production boundary.",
       "Unpaid household services are outside it.",
       "The dealer's commission is a current productive service (the car itself is not counted)."],
      "SNA production boundary", "Goods for own use: IN; services for own use: OUT (except owner-occupied housing).",
      kind="statement", verify_fact=True, ref=SNA)

    coe7, os7, mi7 = 3_000, 1_800, 1_200
    pf7, gf7, gfcf7, nx7, cf7, nit7 = 4_500, 900, 1_100, -250, 400, 450
    gdp7 = coe7 + os7 + mi7 + cf7 + nit7
    ds7 = gdp7 - (pf7 + gf7 + gfcf7 + nx7)
    assert ds7 == 600
    q("measurement-methods", "L3",
      "For an economy the income-side data give: compensation of employees 3,000; operating surplus 1,800; mixed income 1,200. "
      "The expenditure-side data give: private final consumption 4,500; government final consumption 900; gross fixed capital formation 1,100; "
      "change in stocks ?; net exports (−)250. Consumption of fixed capital is 400 and net indirect taxes 450 (all ₹ crore). "
      "The change in stocks consistent with both methods is:",
      cr(ds7),
      [(cr(ds7 - nit7), "NDP_FC compared with GDP_MP after adding only depreciation (NIT forgotten)"),
       (cr(ds7 - cf7), "depreciation forgotten on the income side"),
       (cr(gdp7 - (pf7 + gf7 + gfcf7 - nx7)), "net exports sign reversed")],
      [f"Income side NDP_FC = 3,000 + 1,800 + 1,200 = 6,000", f"GDP_MP = 6,000 + 400 + 450 = {inr(gdp7)}",
       f"Change in stocks = {inr(gdp7)} − (4,500 + 900 + 1,100 − 250) = {ds7}"],
      "GDP_MP (income) = NDP_FC + CFC + NIT = C + G + GFCF + ΔS + NX", "Bring both sides to the same valuation before equating.")

    n1, p1, d1_ = 1_00_000, 10, 100
    n2, p2, d2_ = 1_32_000, 11, 120
    r1 = n1 / (d1_ / 100) / p1
    r2 = n2 / (d2_ / 100) / p2
    assert abs(r1 - r2) < 1e-6
    q("per-capita", "L3",
      "Data for a country:\n\n" + tbl(["", "Year 1", "Year 2"], [
          ("National income at current prices (₹ crore)", inr(n1), inr(n2)),
          ("Population (crore)", p1, p2), ("Price index (Year 1 = 100)", d1_, d2_)]) +
      "\n\nThe change in real per capita income from Year 1 to Year 2 is:",
      "0% (unchanged)",
      [(pct((n2 / p2) / (n1 / p1) - 1), "nominal per capita growth — prices not removed"),
       (pct((n2 / 1.2) / n1 - 1), "real national income growth — population not removed"),
       (pct(n2 / n1 - 1), "nominal national income growth")],
      [f"Real PCI Year 1 = {inr(n1)} ÷ 1.00 ÷ 10 = {inr(r1)}", f"Real PCI Year 2 = {inr(n2)} ÷ 1.20 ÷ 11 = {inr(r2)}",
       "No change."],
      "Real PCI = Nominal NI ÷ (P/100) ÷ Population", "Both deflations (prices and population) are required.")

    q("gdp-gnp", "L3",
      "Match the aggregate with its derivation:\n\n" + tbl(["Aggregate", "", "Derivation"], [
          ("A. GNP at market prices", "", "1. GVA at factor cost + production taxes − production subsidies"),
          ("B. NDP at factor cost", "", "2. Personal income − direct personal taxes − misc. receipts of govt. departments"),
          ("C. GVA at basic prices", "", "3. GDP at market prices + NFIA"),
          ("D. Personal disposable income", "", "4. GDP at market prices − CFC − net indirect taxes")], right=set()) +
      "\n\nCodes (A-B-C-D):",
      "3-4-1-2",
      [("3-1-4-2", "NDP_FC and GVA_BP interchanged"),
       ("4-3-1-2", "GNP_MP and NDP_FC interchanged"),
       ("3-4-2-1", "GVA_BP and PDI interchanged")],
      ["GNP_MP = GDP_MP + NFIA (3)", "NDP_FC = GDP_MP − CFC − NIT (4)", "GVA_BP = GVA_FC + production taxes − subsidies (1)",
       "PDI = PI − direct personal taxes − misc. receipts (2)"],
      "—", "Each bridge is used once.", kind="conceptual", verify_fact=True, ref=SNA)

    gnpfc, cf8, nit8, nf8 = 50_000, 4_000, 3_500, -1_200
    ndpmp8 = gnpfc - nf8 + nit8 - cf8
    q("gdp-gnp", "L3",
      f"GNP at factor cost {cr(gnpfc)}; consumption of fixed capital {cr(cf8)}; net indirect taxes {cr(nit8)}; net factor income from abroad {cr(nf8)}. NDP at market prices is:",
      cr(ndpmp8),
      [(cr(gnpfc + nf8 + nit8 - cf8), "NFIA added instead of removed (national → domestic)"),
       (cr(gnpfc - nf8 - nit8 - cf8), "NIT subtracted when moving FC → MP"),
       (cr(gnpfc - nf8 + nit8), "depreciation not deducted (GDP_MP)")],
      [f"GDP_FC = GNP_FC − NFIA = {inr(gnpfc)} + {inr(-nf8)} = {inr(gnpfc-nf8)}",
       f"GDP_MP = {inr(gnpfc-nf8)} + {inr(nit8)} = {inr(gnpfc-nf8+nit8)}",
       f"NDP_MP = {inr(gnpfc-nf8+nit8)} − {inr(cf8)} = {inr(ndpmp8)}"],
      "NDP_MP = GNP_FC − NFIA + NIT − CFC", "Going national → domestic, remove NFIA: a negative NFIA is added back.")

    q("gdp-gnp", "L3",
      "**Assertion (A):** For India, GNP is typically smaller than GDP.\n\n"
      "**Reason (R):** India's net factor income from abroad is negative because investment income paid to non-residents exceeds such income received, "
      "while inward workers' remittances are recorded as current transfers rather than factor income.",
      "Both A and R are true and R is the correct explanation of A",
      [("Both A and R are true but R is not the correct explanation of A", "misses that NFIA is exactly the GDP–GNP gap"),
       ("A is false because large inward remittances make India's GNP exceed GDP", "treats remittances as factor income"),
       ("A is true but R is false", "misclassifies remittances")],
      ["GNP − GDP = NFIA.", "India's primary income account (investment income) is in deficit, so NFIA < 0.",
       "Remittances are secondary income — they raise national disposable income, not GNP."],
      "GNP = GDP + NFIA", "Remittances ≠ factor income from abroad.",
      kind="assertion-reason", verify_fact=True, ref="RBI BoP data (primary income deficit); BPM6 classification of personal transfers.")

    q("limitations", "L3",
      "Consider the following statements about GDP as a welfare indicator:\n\n" + stmts([
          "Expenditure on cleaning up pollution caused by production raises GDP even though welfare may not rise.",
          "Depletion of natural resources such as groundwater is not deducted in arriving at conventional GDP.",
          "GDP automatically adjusts for changes in income distribution across households.",
          "A rise in the share of non-monetised transactions tends to understate measured GDP."]) +
      "\n\nWhich of the statements are correct?",
      "1, 2 and 4 only",
      [("1 and 2 only", "misses the non-monetised sector limitation"),
       ("1, 2, 3 and 4", "GDP says nothing about distribution"),
       ("2, 3 and 4 only", "misses defensive expenditure")],
      ["Defensive expenditure counts as output (1 true).", "Natural capital depletion is not netted out (2 true).",
       "GDP is an aggregate; distribution is invisible (3 false).", "Non-monetised output is under-recorded (4 true)."],
      "—", "Watch for the 'automatically adjusts' wording — GDP never does.", kind="statement")

    pdi9, dpt9, fee9, ct9, up9, ntr9, gtr9, ndi9, gpi9, sne9 = 20_000, 2_500, 300, 1_500, 1_000, 700, 1_200, 600, 800, 400
    pi9 = pdi9 + dpt9 + fee9
    prv9 = pi9 + ct9 + up9
    ni9 = prv9 - gtr9 - ntr9 - ndi9 + gpi9 + sne9
    assert ni9 == 24000
    q("personal-income", "L3",
      "Work backwards to national income (NNP at factor cost) from the following (₹ crore):\n\n" + items([
          ("Personal disposable income", pdi9), ("Direct personal taxes", dpt9),
          ("Miscellaneous receipts of government administrative departments", fee9), ("Corporation tax", ct9),
          ("Undistributed profits of companies", up9), ("Net current transfers from rest of the world", ntr9),
          ("Current transfers from government", gtr9), ("Interest on national debt", ndi9),
          ("Income from property & entrepreneurship accruing to government administrative departments", gpi9),
          ("Savings of non-departmental enterprises", sne9)]),
      cr(ni9),
      [(cr(ni9 + ndi9), "interest on national debt not removed (it is a transfer)"),
       (cr(ni9 - gpi9), "government property income not added back"),
       (cr(ni9 - fee9), "fees and fines not added back to reach personal income")],
      [f"PI = {inr(pdi9)} + {inr(dpt9)} + {fee9} = {inr(pi9)}",
       f"Private income = PI + corporation tax + undistributed profits = {inr(prv9)}",
       f"NNP_FC = Private income − transfers ({inr(gtr9)} + {ntr9}) − national-debt interest ({ndi9}) + govt property income ({gpi9}) + savings of NDEs ({sne9}) = {inr(ni9)}"],
      "Private income = NDP_FC − govt property income − NDE savings + NFIA + national-debt interest + current transfers",
      "Reverse every step: what was added going down is subtracted going up.")

    # ======================= L4 case A =======================
    GA = "ECO-NI-CASE-A"
    rowsA = [("Private final consumption expenditure", 9_200), ("Government final consumption expenditure", 2_100),
             ("Gross domestic fixed capital formation", 3_000), ("Change in stocks", 250), ("Exports", 1_800),
             ("Imports", 2_150), ("Consumption of fixed capital", 1_100), ("Indirect taxes", 1_400),
             ("Subsidies", 250), ("Net factor income from abroad", -120), ("Old-age pensions paid by government", 260),
             ("Purchase of second-hand machinery", 90), ("Net current transfers from abroad", 400),
             ("Capital gains on property", 75)]
    v = dict(rowsA)
    gdpA = v["Private final consumption expenditure"] + v["Government final consumption expenditure"] + \
        v["Gross domestic fixed capital formation"] + v["Change in stocks"] + v["Exports"] - v["Imports"]
    nitA = v["Indirect taxes"] - v["Subsidies"]
    cfcA, nfA = v["Consumption of fixed capital"], v["Net factor income from abroad"]
    ndpfcA = gdpA - cfcA - nitA
    nnpfcA = ndpfcA + nfA
    gnpmpA = gdpA + nfA
    gnpfcA = gnpmpA - nitA
    gndiA = gnpmpA + v["Net current transfers from abroad"]
    assert gdpA == 14200 and ndpfcA == 11950 and nnpfcA == 11830
    stemA = ("**Case — Republic of Varunia.** The national accounts office has compiled the following data for the year (₹ crore). "
             "Not every line belongs in every aggregate.\n\n" + items(rowsA) + "\n\n")
    q("factor-cost", "L4", stemA + "**Q.** Domestic income (NDP at factor cost) of Varunia is:",
      cr(ndpfcA),
      [(cr(nnpfcA), "NFIA applied — that is national, not domestic, income"),
       (cr(gdpA - cfcA - v["Indirect taxes"]), "subsidies ignored"),
       (cr(ndpfcA + v["Old-age pensions paid by government"]), "transfer payments included")],
      [f"GDP_MP = 9,200 + 2,100 + 3,000 + 250 + 1,800 − 2,150 = {inr(gdpA)}",
       f"NIT = 1,400 − 250 = {nitA}", f"NDP_FC = {inr(gdpA)} − {inr(cfcA)} − {inr(nitA)} = {inr(ndpfcA)}"],
      "NDP_FC = GDP_MP − CFC − NIT", "Domestic = no NFIA.", kind="case", group=GA)
    q("nnp-at-factor", "L4", stemA + "**Q.** National income (NNP at factor cost) of Varunia is:",
      cr(nnpfcA),
      [(cr(ndpfcA - nfA), "NFIA sign reversed"),
       (cr(nnpfcA + v["Net current transfers from abroad"]), "net current transfers from abroad treated as factor income"),
       (cr(gdpA - cfcA - v["Indirect taxes"] - v["Subsidies"] + nfA), "subsidies deducted instead of added back")],
      [f"NNP_FC = NDP_FC + NFIA = {inr(ndpfcA)} + ({nfA}) = {inr(nnpfcA)}"],
      "NNP_FC = NDP_FC + NFIA", "Current transfers are not factor income.", kind="case", group=GA)
    q("factor-cost", "L4", stemA + "**Q.** GNP at factor cost of Varunia is:",
      cr(gnpfcA),
      [(cr(gnpmpA), "net indirect taxes not removed (GNP_MP)"),
       (cr(gnpmpA - v["Indirect taxes"]), "gross indirect taxes removed; subsidies ignored"),
       (cr(gdpA - nitA - nfA), "NFIA sign reversed")],
      [f"GNP_MP = {inr(gdpA)} + ({nfA}) = {inr(gnpmpA)}", f"GNP_FC = {inr(gnpmpA)} − {inr(nitA)} = {inr(gnpfcA)}"],
      "GNP_FC = GDP_MP + NFIA − NIT", "Gross aggregates keep depreciation.", kind="case", group=GA)
    q("gdp-gnp", "L4", stemA + "**Q.** Gross National Disposable Income (GNP at market prices plus net current transfers from abroad) of Varunia is:",
      cr(gndiA),
      [(cr(gnpmpA), "current transfers omitted"),
       (cr(gndiA + v["Old-age pensions paid by government"]), "domestic government pensions added (they are internal transfers that net out)"),
       (cr(gdpA + v["Net current transfers from abroad"]), "NFIA omitted")],
      [f"GNDI = GNP_MP + net current transfers from abroad = {inr(gnpmpA)} + 400 = {inr(gndiA)}",
       "Domestic transfers (pensions) redistribute income within the economy and do not change the national total."],
      "GNDI = GDP_MP + NFIA + Net current transfers from abroad", "Only transfers from the rest of the world change disposable income of the nation.",
      kind="case", group=GA)

    # ======================= L4 case B =======================
    GB = "ECO-NI-CASE-B"
    f_s, f_d = 500, 20
    m_buy, m_sb, m_sh, m_d, m_t = 500, 600, 200, 30, 40
    b_buy, b_imp, b_dom, b_exp, b_stk, b_d, b_t = 600, 50, 900, 250, 50, 40, 90
    va_f = f_s
    va_m = (m_sb + m_sh) - m_buy
    va_b = (b_dom + b_exp + b_stk) - (b_buy + b_imp)
    gdpB = va_f + va_m + va_b
    fe = m_sh + b_dom + b_exp + b_stk - b_imp
    assert gdpB == fe == 1350
    ndpfcB = gdpB - (f_d + m_d + b_d) - (m_t + b_t)
    stemB = ("**Case — Kalinga Valley wheat chain.** A closed-off valley economy has three producers (₹ lakh):\n\n"
             "- **Farmer:** uses own seed; sells wheat 500 to the miller; depreciation on tractor 20.\n"
             "- **Miller:** buys wheat 500; sells flour 600 to the baker and 200 directly to households; depreciation 30; net indirect taxes 40.\n"
             "- **Baker:** buys flour 600 and imported yeast 50; sells bread 900 to households and exports bread 250; "
             "unsold bread added to stock 50; depreciation 40; net indirect taxes 90.\n\n"
             "Assume there are no other producers and NFIA is zero.\n\n")
    q("measurement-methods", "L4", stemB + "**Q.** GDP at market prices of the valley is:",
      f"₹{inr(gdpB)} lakh",
      [(f"₹{inr(f_s + m_sb + m_sh + b_dom + b_exp + b_stk)} lakh", "value of output summed — intermediate consumption not deducted"),
       (f"₹{inr(gdpB + b_imp)} lakh", "imported yeast not deducted as intermediate consumption"),
       (f"₹{inr(gdpB - b_stk)} lakh", "addition to stock ignored")],
      [f"Farmer VA = {va_f}", f"Miller VA = (600 + 200) − 500 = {va_m}", f"Baker VA = (900 + 250 + 50) − (600 + 50) = {va_b}",
       f"GDP_MP = {inr(gdpB)}; check by final expenditure: 200 + 900 + 250 + 50 − 50 = {inr(fe)}"],
      "GDP = Σ(Value of output − Intermediate consumption)", "Imported inputs are intermediate consumption too.", kind="case", group=GB)
    q("factor-cost", "L4", stemB + "**Q.** NDP at factor cost of the valley is:",
      f"₹{inr(ndpfcB)} lakh",
      [(f"₹{inr(gdpB - (f_d + m_d + b_d))} lakh", "net indirect taxes not deducted (NDP_MP)"),
       (f"₹{inr(gdpB - (m_t + b_t))} lakh", "depreciation not deducted (GDP_FC)"),
       (f"₹{inr(gdpB - (f_d + m_d + b_d) + m_t + b_t)} lakh", "net indirect taxes added instead of deducted")],
      [f"Depreciation = 20 + 30 + 40 = {f_d+m_d+b_d}", f"NIT = 40 + 90 = {m_t+b_t}", f"NDP_FC = {inr(gdpB)} − 90 − 130 = {inr(ndpfcB)}"],
      "NDP_FC = GDP_MP − CFC − NIT", "Two deductions, both required.", kind="case", group=GB)
    nvab = va_b - b_d - b_t
    q("nnp-at-factor", "L4", stemB + "**Q.** The baker's net value added at factor cost is:",
      f"₹{nvab} lakh",
      [(f"₹{nvab + b_imp} lakh", "imported yeast treated as a factor payment rather than intermediate input"),
       (f"₹{nvab - b_stk} lakh", "unsold stock excluded from output"),
       (f"₹{va_b} lakh", "gross value added at market prices reported")],
      [f"Output = 900 + 250 + 50 = 1,200", f"GVA_MP = 1,200 − 650 = {va_b}", f"NVA_FC = {va_b} − 40 − 90 = {nvab}"],
      "NVA_FC = Output − IC − CFC − NIT", "Change in stock is part of output.", kind="case", group=GB)
    q("measurement-methods", "L4", stemB + "**Q.** In the valley's accounts, the miller's sale of flour worth ₹200 lakh directly to households is treated as:",
      "Private final consumption expenditure, counted once in GDP",
      [("Intermediate consumption, because flour is normally an input", "classification depends on use, not on the product"),
       ("Excluded to avoid double counting with the baker's bread", "double counting arises only for flour used by the baker"),
       ("Investment, because flour can be stored", "no fixed asset or inventory of the producer is created")],
      ["Households use this flour for final consumption.", "Only the ₹600 lakh flour used by the baker is intermediate."],
      "Final vs intermediate by end use", "Same product, different treatment depending on the buyer's use.",
      kind="case", group=GB)

    # ======================= L4 case C =======================
    GC = "ECO-NI-CASE-C"
    rowsC = [("NDP at factor cost", 18_000),
             ("Income from property & entrepreneurship accruing to government administrative departments", 700),
             ("Savings of non-departmental enterprises", 300), ("Net factor income from abroad", -200),
             ("Interest on national debt", 500), ("Current transfers from government", 900),
             ("Net current transfers from rest of the world", 600), ("Corporation tax", 800),
             ("Undistributed profits of companies", 1_100), ("Direct personal taxes", 1_300),
             ("Miscellaneous receipts of government administrative departments", 150),
             ("Consumption of fixed capital", 1_000), ("Net indirect taxes", 1_200)]
    c = [x[1] for x in rowsC]
    ndp, gpi, sne, nfC, ndi, gtr, rtr, ctx, upr, dpt, fee, cfcC, nitC = c
    idp = ndp - gpi - sne
    prvC = idp + nfC + ndi + gtr + rtr
    piC = prvC - ctx - upr
    pdiC = piC - dpt - fee
    niC = ndp + nfC
    assert (prvC, piC, pdiC) == (18800, 16900, 15450)
    stemC = "**Case — Sindhuvar household-income accounts.** Data for the year (₹ crore):\n\n" + items(rowsC) + "\n\n"
    q("personal-income", "L4", stemC + "**Q.** Private income of Sindhuvar is:",
      cr(prvC),
      [(cr(prvC - ndi), "interest on national debt excluded (it is part of private income)"),
       (cr(prvC - 2 * nfC), "NFIA sign reversed"),
       (cr(prvC + gpi), "government property income not deducted")],
      [f"Income from domestic product accruing to private sector = 18,000 − 700 − 300 = {inr(idp)}",
       f"Private income = {inr(idp)} + (−200) + 500 + 900 + 600 = {inr(prvC)}"],
      "Private income = NDP_FC − govt property income − NDE savings + NFIA + national-debt interest + current transfers",
      "National-debt interest is excluded from national income but included in private income.", kind="case", group=GC)
    q("personal-income", "L4", stemC + "**Q.** Personal income of Sindhuvar is:",
      cr(piC),
      [(cr(piC + ctx), "corporation tax not deducted"),
       (cr(piC + upr), "undistributed profits not deducted"),
       (cr(piC - dpt), "direct personal taxes deducted at this stage (that belongs to PDI)")],
      [f"PI = Private income − corporation tax − undistributed profits = {inr(prvC)} − 800 − 1,100 = {inr(piC)}"],
      "PI = Private income − Corporation tax − Corporate savings", "Personal taxes come off only in the next step.", kind="case", group=GC)
    q("personal-income", "L4", stemC + "**Q.** Personal disposable income of Sindhuvar is:",
      cr(pdiC),
      [(cr(pdiC + fee), "fees and fines not deducted"),
       (cr(pdiC - cfcC), "consumption of fixed capital deducted"),
       (cr(pdiC - nitC), "net indirect taxes deducted")],
      [f"PDI = {inr(piC)} − 1,300 − 150 = {inr(pdiC)}", "CFC and NIT are irrelevant: NDP_FC is already net and at factor cost."],
      "PDI = PI − Direct personal taxes − Misc. receipts", "Red-herring lines (CFC, NIT) are already out of NDP_FC.", kind="case", group=GC)
    q("personal-income", "L4", stemC + "**Q.** Consider:\n\n" + stmts([
          f"National income of Sindhuvar is ₹{inr(niC)} crore.",
          "Private income here exceeds national income mainly because it includes transfer incomes and national-debt interest.",
          "Personal income includes undistributed profits of companies."]) + "\n\nWhich of the statements are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "undistributed profits are deducted in reaching personal income"),
       ("2 and 3 only", "national income figure wrongly rejected"),
       ("1 only", "misses why private income exceeds national income")],
      [f"NNP_FC = 18,000 − 200 = {inr(niC)} (1 true)",
       f"Private income {inr(prvC)} > NI {inr(niC)}: transfers (1,500) and national-debt interest (500) outweigh govt property income and NDE savings (1,000) (2 true)",
       "Undistributed profits are removed at the PI stage (3 false)"],
      "NI = NDP_FC + NFIA", "Private income can exceed national income.", kind="case", group=GC)
