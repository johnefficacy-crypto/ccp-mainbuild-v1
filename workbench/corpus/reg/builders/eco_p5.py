"""ECO part 5 — Monetary policy, inflation, Phillips curve, external sector, institutions, cycles (42 Q: L1 9, L2 12, L3 13, L4 8)."""
from eco_common import mk, cr, n, tbl, items, stmts, inr, R, pct

RBIACT = "RBI Act 1934 ss. 45ZA–45ZN (inflation target, MPC); Monetary Policy Committee and Monetary Policy Process Regulations, 2016."
LAF = "RBI LAF corridor: SDF (floor) = repo − 25 bps; MSF (ceiling) = repo + 25 bps (since April 2022)."
FEMA = "FEMA (Non-debt Instruments) Rules, 2019; Consolidated FDI Policy (DPIIT)."


def add_all(B):
    q = mk(B)
    usd = lambda x: f"US${n(abs(x),1)} bn"
    bal = lambda x, pos="surplus", neg="deficit": f"{pos.capitalize() if x >= 0 else neg.capitalize()} of {usd(x)}"

    # ======================= L1 =======================
    q("bank-for-international", "L1", "Which of the following correctly describes the Bank for International Settlements (BIS)?",
      "Based in Basel, it acts as a bank for central banks and hosts the Basel Committee",
      [("Headquartered in Washington DC, it lends to member governments for balance-of-payments support", "describes the IMF"),
       ("Headquartered in Madrid, it sets principles for securities regulation", "describes IOSCO"),
       ("A World Bank Group member that provides political-risk insurance to investors", "describes MIGA")],
      ["BIS (1930) is owned by central banks and provides banking services to them.", "It hosts the BCBS, whose Basel III standards govern bank capital."],
      "—", "Basel = BIS/BCBS; Madrid = IOSCO; Washington = IMF/WBG.", kind="conceptual", verify_fact=True, ref="BIS Statutes; BIS annual report.")

    q("iosco", "L1", "IOSCO is best described as:",
      "The global body of securities regulators, based in Madrid, setting regulatory principles",
      [("The Basel-based committee that sets capital standards for banks", "that is the BCBS"),
       ("The Paris-based inter-governmental body that sets anti-money-laundering standards", "that is FATF"),
       ("The association of insurance supervisors that issues Insurance Core Principles", "that is IAIS")],
      ["IOSCO (1983) brings together securities regulators such as SEBI.", "It also runs the Multilateral MoU on enforcement cooperation."],
      "—", "Match each standard-setter with its sector.", kind="conceptual", verify_fact=True, ref="IOSCO By-laws; Objectives and Principles of Securities Regulation.")

    q("world-bank", "L1", "India is NOT a member of which World Bank Group institution?",
      "International Centre for Settlement of Investment Disputes (ICSID)",
      [("International Bank for Reconstruction and Development (IBRD)", "India is a founding member"),
       ("International Development Association (IDA)", "India is a member (and former major borrower)"),
       ("Multilateral Investment Guarantee Agency (MIGA)", "India joined MIGA in the 1990s")],
      ["WBG has five institutions: IBRD, IDA, IFC, MIGA, ICSID.", "India has not signed the ICSID Convention."],
      "—", "Five institutions, India in four.", kind="conceptual", verify_fact=True, ref="World Bank Group member-country listings (ICSID Contracting States).")

    q("international-monetary", "L1", "Which currency is NOT part of the IMF's SDR valuation basket?",
      "Swiss franc",
      [("Chinese renminbi", "included since October 2016"),
       ("Japanese yen", "included"),
       ("Pound sterling", "included")],
      ["The SDR basket: US dollar, euro, Chinese renminbi, Japanese yen, pound sterling."],
      "—", "Five currencies; renminbi is the newest.", kind="conceptual", verify_fact=True, ref="IMF SDR valuation (2022 review).")

    q("currency-depreciation", "L1", "The term 'devaluation' properly refers to:",
      "Official cut in external value under a fixed or pegged regime",
      [("A market-driven fall in the external value of a floating currency", "that is depreciation"),
       ("A fall in the domestic purchasing power of money due to inflation", "internal, not external, value"),
       ("A reduction in the face value of the currency notes in issue", "redenomination")],
      ["Devaluation is a policy act of the authorities; depreciation is a market outcome."],
      "—", "Floating → depreciation; pegged → devaluation.", kind="conceptual")

    q("leading-and-lagging", "L1", "Which of the following is usually classified as a LEADING economic indicator?",
      "New orders index of the manufacturing PMI",
      [("Unemployment rate", "typically a lagging indicator"),
       ("Average duration of unemployment", "lagging indicator"),
       ("Outstanding bank credit to the industry sector", "tends to lag the cycle")],
      ["Leading indicators turn before the economy: new orders, building permits, stock prices, yield-curve slope.", "Lagging: unemployment, credit outstanding, CPI for services."],
      "—", "Orders precede output; hiring follows it.", kind="conceptual")

    q("unemployment-types", "L1", "A software engineer who has resigned and is spending a few weeks searching for a better-matched job is:",
      "Frictionally unemployed",
      [("Structurally unemployed", "structural unemployment arises from a skill/location mismatch with available jobs"),
       ("Cyclically unemployed", "cyclical unemployment arises from deficient aggregate demand"),
       ("Disguisedly unemployed", "disguised unemployment has zero marginal product while apparently employed")],
      ["Frictional unemployment reflects search and matching time.", "It persists even at full employment."],
      "Natural rate = Frictional + Structural", "Voluntary job search ⇒ frictional.", kind="conceptual")

    q("stagflation", "L1", "Stagflation refers to a situation of:",
      "High inflation with stagnant output and high unemployment",
      [("Falling prices with rising output", "benign deflation"),
       ("High inflation with booming output and low unemployment", "overheating / demand-pull"),
       ("Falling prices with falling output", "deflationary recession")],
      ["Typically caused by adverse supply shocks (e.g. oil).", "Poses a policy dilemma: fighting inflation deepens the slump."],
      "—", "Contradicts a stable short-run Phillips trade-off.", kind="conceptual")

    q("direct-vs-indirect", "L1", "Which of the following is a DIRECT (quantity-based, non-market) monetary policy instrument?",
      "Cash Reserve Ratio",
      [("Open market operations", "indirect — works through market prices/liquidity"),
       ("Repo auctions under the LAF", "indirect, market-based"),
       ("Marginal Standing Facility", "indirect, rate-based standing facility")],
      ["Direct instruments prescribe quantities/ratios: CRR, SLR, directed credit.", "Indirect instruments act through interest rates and liquidity: repo, reverse repo/SDF, OMO, MSF."],
      "—", "Reserve requirements are direct; operations and facilities are indirect.", kind="conceptual", verify_fact=True, ref="RBI monetary policy framework (instruments).")

    # ======================= L2 =======================
    mx, mm, sv, sec, pri = 450, 680, 170, 110, -45
    tdf = mx - mm
    q("trade-deficit", "L2",
      f"A country's BoP shows merchandise exports {usd(mx)}, merchandise imports {usd(mm)}, net services {usd(sv)} surplus, net primary income {usd(pri)} deficit and net secondary income {usd(sec)} surplus. Its (merchandise) trade deficit is:",
      usd(tdf),
      [(usd(tdf + sv), "net services included — that is the goods-and-services balance"),
       (bal(tdf + sv + pri + sec), "current-account balance reported"),
       (usd(tdf + pri), "primary income deficit added to the trade gap")],
      [f"Trade balance = {mx} − {mm} = {tdf}", f"(Current account = {tdf} + {sv} − 45 + {sec} = {tdf+sv+pri+sec})"],
      "Trade balance = Merchandise X − Merchandise M", "A large trade deficit can coexist with a current-account surplus.")

    g2, s2, p2, sc2, gdp = -260, 150, -40, 100, 3500
    ca2 = g2 + s2 + p2 + sc2
    q("current-account-deficit", "L2",
      f"Goods balance {usd(g2)} (deficit); services {usd(s2)} surplus; primary income {usd(p2)} deficit; secondary income {usd(sc2)} surplus; GDP {usd(gdp)}. The current-account deficit as a share of GDP is:",
      pct(-ca2 / gdp),
      [(pct(-(g2 + s2) / gdp), "only goods and services counted"),
       (pct(-(g2 + s2 + sc2) / gdp), "primary income omitted"),
       (pct(-g2 / gdp), "trade deficit reported")],
      [f"CA = −260 + 150 − 40 + 100 = {ca2}", f"CAD/GDP = {-ca2}/{inr(gdp)} = {pct(-ca2/gdp)}"],
      "CA = Goods + Services + Primary income + Secondary income", "Remittances (secondary income) cushion India's CAD.")

    pin, pus, mkt = 2400, 40, 84
    ppp = pin / pus
    q("purchasing-power-parity", "L2",
      f"A representative basket costs ₹{inr(pin)} in India and ${pus} in the US. The market exchange rate is ₹{mkt} per dollar. The PPP exchange rate and the implication are:",
      f"₹{n(ppp)} per $; the rupee is undervalued at the market rate relative to PPP",
      [(f"₹{n(ppp)} per $; the rupee is overvalued at the market rate relative to PPP", "direction of misalignment reversed"),
       (f"₹{n(mkt/ppp)} per $; the rupee is undervalued", "ratio of market rate to PPP reported as the PPP rate"),
       (f"₹{mkt} per $; PPP holds at the market rate", "market rate assumed to equal PPP")],
      [f"PPP = {inr(pin)}/{pus} = ₹{n(ppp)} per $", f"Market ₹{mkt} > PPP ₹{n(ppp)}: a dollar buys more in India than PPP implies ⇒ rupee undervalued."],
      "Absolute PPP: E = P_domestic / P_foreign", "More rupees per dollar than PPP ⇒ rupee cheap (undervalued).")

    s0, pi_in, pi_us = 80, 0.06, 0.02
    ef = s0 * (1 + pi_in) / (1 + pi_us)
    q("purchasing-power-parity", "L2",
      f"The spot rate is ₹{s0}/$. Expected inflation is {pct(pi_in)} in India and {pct(pi_us)} in the US. By relative PPP, the expected rate one year ahead is:",
      f"₹{n(ef)}/$",
      [(f"₹{n(s0*(1+pi_in-pi_us))}/$", "linear approximation (inflation differential) used"),
       (f"₹{n(s0*(1+pi_us)/(1+pi_in))}/$", "inflation ratio inverted — rupee shown appreciating"),
       (f"₹{n(s0*(1+pi_in))}/$", "US inflation ignored")],
      [f"E₁ = {s0} × 1.06/1.02 = {n(ef)}"],
      "E₁ = E₀ × (1 + π_d)/(1 + π_f)", "Higher-inflation currency depreciates.")

    e0, e1 = 80, 84
    q("currency-depreciation", "L2", f"The exchange rate moves from ₹{e0}/$ to ₹{e1}/$ in a market-determined regime. The change in the rupee's value is:",
      f"Rupee depreciated by {pct(1-e0/e1)}",
      [(f"Rupee depreciated by {pct(e1/e0-1)}", "dollar's appreciation reported as rupee's depreciation"),
       (f"Rupee appreciated by {pct(e1/e0-1)}", "direction reversed"),
       (f"Rupee devalued by {pct(e1/e0-1)}", "devaluation terminology misapplied to a market-determined rate")],
      [f"Rupee value in $: 1/80 → 1/84", f"% change = (1/84 − 1/80)/(1/80) = −{pct(1-e0/e1)}", f"(Dollar appreciated by {pct(e1/e0-1)}.)"],
      "%Δ(home currency) = E₀/E₁ − 1 (E in home per foreign)", "The two percentages differ because the base differs.")

    q("inflation-targeting", "L2", "Under the RBI Act, the Monetary Policy Committee consists of:",
      "Six: Governor (casting vote), a Deputy Governor, one RBI officer and three Centre appointees",
      [("Six members, all appointed by the Central Government, with decisions requiring unanimity", "three are RBI members; decisions by majority"),
       ("Five members — three from RBI and two external — with the Finance Secretary holding a veto", "wrong size; no government veto"),
       ("Seven members including the Finance Secretary as a voting member", "government officials are not members")],
      ["s.45ZB: six members; quorum four including the Governor (or DG in his absence).", "Majority vote; Governor has a second/casting vote in a tie."],
      "—", "No government nominee votes; external members are appointed by the Centre.", kind="conceptual", verify_fact=True, ref=RBIACT)

    i0, i1 = 150, 160.5
    inf = i1 / i0 - 1
    q("inflation-targeting", "L2",
      f"A central bank targets 4% CPI inflation with a tolerance band of ±2 percentage points. The CPI was {n(i0,1)} a year ago and is {n(i1,1)} now. Year-on-year inflation and its position relative to the band are:",
      f"{pct(inf,1)} — above the upper tolerance level",
      [(f"{n(i1-i0,1)}% — above the upper tolerance level", "index-point change read as per cent"),
       (f"{pct((i1-i0)/i1)} — above the upper tolerance level", "current index used as base"),
       (f"{pct(inf,1)} — within the band", "band misread as ±3 points")],
      [f"Inflation = {n(i1,1)}/{n(i0,1)} − 1 = {pct(inf,1)}", "Upper tolerance = 4 + 2 = 6% ⇒ breached."],
      "π = CPIₜ/CPIₜ₋₁₂ − 1", "Points ≠ per cent.")

    pe, beta, u, us = 4, 0.5, 5, 6
    pi_ = pe - beta * (u - us)
    q("phillips-curve", "L2",
      f"The expectations-augmented Phillips curve is π = πᵉ − {beta}(u − u*). With πᵉ = {pe}%, u = {u}% and u* = {us}%, inflation is:",
      f"{n(pi_)}%",
      [(f"{n(pe + beta*(u-us))}%", "sign of the unemployment gap reversed"),
       (f"{pe}%", "unemployment gap ignored"),
       (f"{n(pe - (u-us))}%", "slope coefficient ignored")],
      [f"π = {pe} − {beta}×({u} − {us}) = {n(pi_)}%"],
      "π = πᵉ − β(u − u*)", "Unemployment below natural ⇒ inflation above expected.")

    q("cost-push", "L2", "A sharp rise in international crude oil prices, other things equal, will in the short run:",
      "Shift aggregate supply leftward, raising prices and reducing output",
      [("Shift aggregate demand rightward, raising both prices and output", "that is demand-pull inflation"),
       ("Shift long-run aggregate supply rightward, lowering prices", "direction and curve wrong"),
       ("Shift aggregate demand leftward, lowering prices and output", "a demand shock, not a cost shock")],
      ["Higher input costs ⇒ firms supply less at each price level.", "Result: higher P, lower Y — cost-push inflation."],
      "SRAS ↑ costs ⇒ SRAS shifts left", "Output direction separates cost-push from demand-pull.", kind="conceptual")

    q("foreign-direct-investment", "L2", "Under India's FDI policy, the difference between the automatic route and the government route is that:",
      "Automatic route needs no prior approval; government route needs prior ministry approval",
      [("Automatic-route investment needs prior RBI approval, government-route does not", "RBI approval is not a precondition under the automatic route"),
       ("The government route applies only to portfolio investment", "routes are for FDI"),
       ("Proposals under the government route are cleared by the Foreign Investment Promotion Board", "FIPB was abolished in 2017")],
      ["Automatic route: invest, then report.", "Government route: prior approval via the Foreign Investment Facilitation Portal / administrative ministry."],
      "—", "FIPB no longer exists.", kind="conceptual", verify_fact=True, ref=FEMA)

    q("business-cycle", "L2", "The correct sequence of phases in a typical business cycle, beginning from the lowest point, is:",
      "Trough → Expansion → Peak → Contraction → Trough",
      [("Trough → Peak → Recovery → Recession → Trough", "peak placed before recovery"),
       ("Trough → Recession → Recovery → Peak → Trough", "recession placed immediately after the trough"),
       ("Peak → Recovery → Trough → Contraction → Peak", "phases jumbled")],
      ["From the trough activity recovers and expands to a peak, then contracts to the next trough."],
      "—", "Turning points: peak and trough; phases: expansion and contraction.", kind="conceptual")

    q("objectives-and-functions", "L2", "Following the 2016 amendment, the Preamble of the RBI Act describes the primary objective of monetary policy as:",
      "Maintaining price stability while keeping in mind the objective of growth",
      [("Achieving full employment while keeping inflation below the target", "full employment is not the stated primary objective"),
       ("Maintaining a fixed exchange rate against the US dollar", "India does not target a fixed rate"),
       ("Ensuring the fiscal deficit stays within the FRBM target", "fiscal target is the government's, not monetary policy's")],
      ["The Preamble was amended to reflect flexible inflation targeting.", "Price stability is primary; growth is kept in mind."],
      "—", "'Flexible' inflation targeting — growth matters but is secondary.", kind="conceptual", verify_fact=True, ref=RBIACT)

    # ======================= L3 =======================
    rowsC = [("Merchandise exports", 430), ("Merchandise imports", 690), ("Services exports", 340), ("Services imports", 180),
             ("Primary income receipts", 40), ("Primary income payments", 85), ("Personal transfers (remittances), net", 120),
             ("Other secondary income, net", -5), ("FDI, net inflow", 30), ("Portfolio investment, net", 20),
             ("Capital transfers, net (capital account)", 1), ("External commercial borrowings, net", 15)]
    v = dict(rowsC)
    ca = 430 - 690 + 340 - 180 + 40 - 85 + 120 - 5
    assert ca == -30
    q("current-account-deficit", "L3", "From the following BoP entries (US$ bn), the current-account balance is:\n\n" + items(rowsC, unit="US$ bn"),
      bal(ca),
      [(bal(ca - 120), "remittances treated as a capital-account item"),
       (bal(ca + 30), "FDI inflow included in the current account"),
       (bal(ca + 1), "capital transfers included in the current account")],
      ["Goods −260; services +160; primary income −45; secondary income +115", f"CA = {ca}", "FDI, portfolio, ECB: financial account; capital transfers: capital account."],
      "CA = G + S + Primary + Secondary income", "Close options differ by one misclassified line.", verify_fact=True, ref="IMF BPM6 classification.")

    fin = 30 + 20 + 15 - 20; eo = -2; kap = 1
    ov = ca + kap + fin + eo
    q("balance-of-payments", "L3",
      f"Continuing the same economy: current account {usd(ca)} deficit; capital account {usd(kap)} surplus; financial account excluding reserves: FDI +30, portfolio +20, ECB +15, other investment −20; errors and omissions −2 (US$ bn). The overall balance and the movement in foreign-exchange reserves are:",
      f"Surplus of {usd(ov)}; reserves rise by {usd(ov)}",
      [(f"Surplus of {usd(ov-eo)}; reserves rise by {usd(ov-eo)}", "errors and omissions ignored"),
       (f"Surplus of {usd(ov-kap)}; reserves rise by {usd(ov-kap)}", "capital account omitted"),
       (f"Deficit of {usd(ov)}; reserves fall by {usd(ov)}", "sign of the overall balance reversed")],
      [f"Financial account (excl. reserves) = 30 + 20 + 15 − 20 = {fin}", f"Overall = −30 + 1 + {fin} − 2 = {ov}", "An overall surplus is absorbed as a rise in reserves (shown with a negative sign in RBI's BoP tables)."],
      "Overall balance = CA + KA + FA(excl. reserves) + E&O = ΔReserves", "Increase in reserves is a debit (use of funds).")

    q("why-the-balance", "L3",
      "**Assertion (A):** The balance of payments always balances in the accounting sense.\n\n"
      "**Reason (R):** Every transaction is recorded by double entry, so any net imbalance on current, capital and financial (non-reserve) accounts is matched by changes in official reserves and by errors and omissions.",
      "Both A and R are true and R is the correct explanation of A",
      [("Both A and R are true but R is not the correct explanation of A", "double entry is exactly why it balances"),
       ("A is false because a country can run a persistent BoP deficit", "confuses accounting balance with overall-balance disequilibrium"),
       ("A is true but R is false", "R is the standard explanation")],
      ["Credits = debits by construction.", "'Deficit' refers to the overall balance before reserve changes."],
      "CA + KA + FA + E&O = 0", "Accounting balance ≠ economic equilibrium.", kind="assertion-reason")

    q("exchange-rate-regimes", "L3",
      "Consider the following statements:\n\n" + stmts([
          "Under a clean float, a BoP disequilibrium is corrected by the exchange rate without any change in official reserves.",
          "Under a fixed exchange rate, a BoP deficit obliges the central bank to sell foreign-exchange reserves.",
          "India's rupee is formally pegged to the US dollar.",
          "Under a currency board, domestic base money must be backed by foreign-exchange reserves at a fixed rate."]) + "\n\nWhich are correct?",
      "1, 2 and 4 only",
      [("1 and 2 only", "misses the currency-board rule"),
       ("1, 2, 3 and 4", "India has a market-determined rate with RBI intervention to curb volatility, not a peg"),
       ("2, 3 and 4 only", "rejects the clean-float mechanism")],
      ["Clean float: no intervention ⇒ ΔReserves = 0 (1).", "Fixed: defend parity with reserves (2).", "India: managed float (3 false).", "Currency board: full reserve backing (4)."],
      "—", "Managed float ≠ peg.", kind="statement", verify_fact=True, ref="RBI exchange-rate policy statements; IMF AREAER classification.")

    q("international-monetary", "L3",
      "Consider the following statements about the IMF:\n\n" + stmts([
          "A member's quota largely determines its voting power and its access to IMF financing.",
          "General SDR allocations are distributed to members in proportion to their quotas.",
          "The SDR is a currency that circulates for retail payments among IMF members.",
          "The Rapid Financing Instrument provides quick financial assistance for urgent balance-of-payments needs."]) + "\n\nWhich are correct?",
      "1, 2 and 4 only",
      [("1 and 2 only", "RFI is an emergency financing window"),
       ("1, 2, 3 and 4", "the SDR is a reserve asset / unit of account, not a circulating currency"),
       ("2, 3 and 4 only", "quota–voting link rejected")],
      ["Quota ⇒ votes, access, SDR allocations (1, 2).", "SDR: international reserve asset and unit of account (3 false).", "RFI: rapid, low-conditionality emergency support (4)."],
      "—", "SDR is a claim on freely usable currencies, not money in circulation.", kind="statement", verify_fact=True, ref="IMF Articles of Agreement; IMF lending facilities factsheets.")

    qi = [6.4, 6.8, 5.9, 6.2, 6.5, 6.1]
    run, fail = 0, None
    for i, x in enumerate(qi):
        run = run + 1 if x > 6 else 0
        if run == 3 and fail is None:
            fail = i + 1
    assert fail == 6
    q("inflation-targeting", "L3",
      "The inflation target is 4% CPI with an upper tolerance level of 6% and a lower level of 2%. Average CPI inflation by quarter was:\n\n" +
      tbl(["Quarter", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6"], [["Avg. CPI inflation (%)"] + [n(x, 1) for x in qi]]) +
      "\n\nUnder the notified framework, the central bank is first deemed to have failed to meet the target at the end of:",
      f"Q{fail}",
      [("Q4", "three breaches counted although they were not consecutive"),
       ("Q2", "two consecutive breaches treated as failure"),
       ("No failure — inflation returned below 6% in Q3", "a later run of three consecutive breaches overlooked")],
      ["Failure = average inflation above the upper tolerance (or below the lower) for any three CONSECUTIVE quarters.",
       "Q1–Q2 breach, Q3 does not; Q4, Q5, Q6 all > 6% ⇒ failure at end-Q6.", "RBI must then report reasons, remedial action and time-frame to the Government (s.45ZN)."],
      "Failure ⇔ 3 consecutive quarterly averages outside 2–6%", "Consecutive is the operative word.", verify_fact=True, ref=RBIACT)

    q("monetary-policy-transmission", "L3",
      "Consider the following statements on monetary policy transmission in India:\n\n" + stmts([
          "Linking new floating-rate retail and MSME loans to an external benchmark has speeded up transmission to lending rates.",
          "Administered interest rates on small-savings schemes that do not track market rates can impede transmission to bank deposit rates.",
          "A higher share of fixed-rate legacy loans in bank books speeds up transmission to average lending rates.",
          "Keeping the weighted average call rate close to the policy repo rate through liquidity management supports transmission."]) + "\n\nWhich are correct?",
      "1, 2 and 4 only",
      [("1 and 2 only", "liquidity alignment of the operating target is central to transmission"),
       ("1, 2, 3 and 4", "fixed-rate stock slows transmission"),
       ("2, 3 and 4 only", "rejects the EBLR effect")],
      ["EBLR (from Oct 2019) passes policy changes to new floating loans quickly (1).", "Sticky small-savings rates compete with bank deposits (2).",
       "Fixed-rate loans reprice only at maturity (3 false).", "WACR is the operating target; aligning it with repo is the first leg (4)."],
      "Policy rate → WACR → money-market rates → deposit/lending rates", "Operating target first, then bank rates.", kind="statement", verify_fact=True,
      ref="RBI circular on External Benchmark Based Lending (Sept 2019); RBI monetary policy framework.")

    pi0, bb, us8, u8 = 4, 0.5, 6, 4
    path = []
    p = pi0
    for _ in range(3):
        p = p - bb * (u8 - us8); path.append(p)
    q("phillips-curve", "L3",
      f"Expectations are adaptive (πᵉₜ = πₜ₋₁) and πₜ = πᵉₜ − {bb}(uₜ − u*), with u* = {us8}%. Inflation last year was {pi0}%. If the government holds unemployment at {u8}% for the next three years, inflation in year 3 will be:",
      f"{n(path[-1])}%",
      [(f"{n(pi0 - bb*(u8-us8))}%", "expectations held fixed at the initial 4% (static short-run curve)"),
       (f"{n(path[1])}%", "only two years of acceleration counted"),
       (f"{n(pi0 + 3*(us8-u8))}%", "slope coefficient 0.5 ignored")],
      [f"Year 1: 4 + 0.5×2 = {n(path[0])}%", f"Year 2: {n(path[0])} + 1 = {n(path[1])}%", f"Year 3: {n(path[1])} + 1 = {n(path[2])}%"],
      "Accelerationist: Δπ = −β(u − u*)", "Holding u below u* needs ever-rising inflation — the long-run Phillips curve is vertical.")

    pe9, b9, us9, v9, tgt = 4, 0.5, 6, 2, 4
    u9 = us9 + (pe9 + v9 - tgt) / b9
    q("supply-shocks", "L3",
      f"Inflation follows π = πᵉ − {b9}(u − u*) + v, where v is a supply shock. With πᵉ = {pe9}%, u* = {us9}% and an adverse supply shock v = {v9} points, the unemployment rate needed to hold inflation at the {tgt}% target this year is:",
      f"{n(u9)}%",
      [(f"{n(us9 + v9)}%", "shock not scaled by the slope (β ignored)"),
       (f"{n(us9)}%", "natural rate reported — shock ignored"),
       (f"{n(us9 + v9*b9)}%", "shock multiplied rather than divided by β")],
      [f"{tgt} = {pe9} − 0.5(u − 6) + 2 ⇒ 0.5(u − 6) = 2 ⇒ u = {n(u9)}%"],
      "u = u* + (πᵉ + v − π_target)/β", "A flat Phillips curve makes supply shocks costly to offset.")

    q("demand-pull", "L3",
      "Which of the following are sources of demand-pull inflation?\n\n" + stmts([
          "A large increase in government spending financed by money creation",
          "Wage increases that outpace productivity growth",
          "A crop failure that raises food prices",
          "A surge in export demand when the economy is near full capacity"]),
      "1 and 4 only",
      [("1, 2 and 4 only", "wage-push is cost-push"),
       ("1, 3 and 4 only", "crop failure is a supply shock"),
       ("2 and 3 only", "these are the cost-push/supply sources, reversed")],
      ["Demand-pull: AD outruns capacity (1, 4).", "Cost-push/supply: wage-push (2), crop failure (3)."],
      "AD↑ ⇒ demand-pull; SRAS↓ ⇒ cost-push", "Ask which curve shifts.", kind="statement")

    lf, fr, st, cy = 50, 1.5, 2.0, 1.0
    q("unemployment-types", "L3",
      f"Labour force is {lf} crore. Of the unemployed, {fr} crore are frictionally, {st} crore structurally and {cy} crore cyclically unemployed. The natural rate of unemployment and the actual rate are:",
      f"Natural {pct((fr+st)/lf)}; actual {pct((fr+st+cy)/lf)}",
      [(f"Natural {pct((fr+st+cy)/lf)}; actual {pct((fr+st+cy)/lf)}", "cyclical unemployment included in the natural rate"),
       (f"Natural {pct(fr/lf)}; actual {pct((fr+st+cy)/lf)}", "structural unemployment excluded from the natural rate"),
       (f"Natural {pct((fr+st)/lf)}; actual {pct(cy/lf)}", "only cyclical unemployment counted as actual")],
      [f"Natural = (1.5 + 2.0)/50 = {pct((fr+st)/lf)}", f"Actual = 4.5/50 = {pct((fr+st+cy)/lf)}"],
      "Natural rate = (Frictional + Structural)/Labour force", "Cyclical unemployment is the gap above the natural rate.")

    q("foreign-direct-investment", "L3",
      "Consider the following statements under India's foreign-investment rules:\n\n" + stmts([
          "Investment by a foreign investor of 10% or more of the post-issue paid-up equity of a listed Indian company (fully diluted basis) is classified as FDI.",
          "Once classified as FDI, an investment continues to be FDI even if the holding later falls below 10%.",
          "Greenfield FDI involves setting up a new entity, while brownfield FDI involves acquisition of or investment in an existing entity.",
          "All FDI in India requires prior approval of the Reserve Bank of India."]) + "\n\nWhich are correct?",
      "1, 2 and 3 only",
      [("1 and 3 only", "misses the 'once FDI, always FDI' rule"),
       ("1, 2, 3 and 4", "most sectors are under the automatic route"),
       ("2, 3 and 4 only", "rejects the 10% threshold")],
      ["10% threshold separates FDI from FPI in listed companies (1).", "An FDI holding stays FDI even if diluted below 10% (2).",
       "Greenfield vs brownfield (3).", "Automatic route needs no prior approval (4 false)."],
      "—", "'All' in statement 4 is the giveaway.", kind="statement", verify_fact=True, ref=FEMA)

    q("stagflation", "L3",
      "**Assertion (A):** Stagflation cannot be explained by movement along a stable, downward-sloping short-run Phillips curve.\n\n"
      "**Reason (R):** Stagflation involves inflation and unemployment rising together, which is consistent with an adverse supply shock shifting the short-run Phillips curve upward.",
      "Both A and R are true and R is the correct explanation of A",
      [("Both A and R are true but R is not the correct explanation of A", "R is precisely why a stable curve fails"),
       ("A is false because a steep Phillips curve can produce stagflation", "slope does not make both variables rise"),
       ("A is true but R is false", "supply shocks shift the curve upward")],
      ["Along a stable curve, π and u move inversely.", "Simultaneous rise ⇒ the curve itself shifted (supply shock / expectations)."],
      "π = πᵉ − β(u − u*) + v", "1970s oil shocks broke the simple Phillips curve.", kind="assertion-reason")

    # ======================= L4 case J (BoP) =======================
    GJ = "ECO-BOP-CASE-J"
    rowsJ = [("Merchandise exports", 210), ("Merchandise imports", 290), ("Services exports", 95), ("Services imports", 60),
             ("Primary income, net", -18), ("Secondary income, net (mainly remittances)", 38), ("Capital account, net", 0.5),
             ("FDI, net", 12), ("Portfolio investment, net", -6), ("Loans incl. ECB, net", 9), ("Banking capital, net", 4),
             ("Other financial flows, net", -1.5), ("Errors and omissions", -1)]
    J = dict(rowsJ); gdpJ = 1250
    tb = 210 - 290; gs = tb + 95 - 60; caJ = gs - 18 + 38
    faJ = 12 - 6 + 9 + 4 - 1.5
    ovJ = caJ + 0.5 + faJ - 1
    assert (tb, gs, caJ, faJ, ovJ) == (-80, -45, -25, 17.5, -8)
    stemJ = (f"**Case — Oristan's balance of payments.** Annual data (US$ bn); GDP is US${inr(gdpJ)} bn.\n\n" +
             tbl(["Item", "US$ bn"], [(a, n(b, 1)) for a, b in rowsJ]) + "\n\n")
    q("trade-deficit", "L4", stemJ + "**Q.** Oristan's merchandise trade balance is:",
      bal(tb),
      [(bal(gs), "services included — goods-and-services balance"),
       (bal(caJ), "current-account balance reported"),
       (bal(210 - 290 - 60), "services imports lumped with merchandise imports")],
      [f"210 − 290 = {tb}"],
      "Trade balance = Merchandise X − M", "Keep goods and services separate.", kind="case", group=GJ)
    q("current-account-deficit", "L4", stemJ + "**Q.** Oristan's current-account deficit as a percentage of GDP is:",
      pct(-caJ / gdpJ),
      [(pct(-gs / gdpJ), "only goods and services counted"),
       (pct(-(gs - 18) / gdpJ), "secondary income (remittances) omitted"),
       (pct(-(gs + 38) / gdpJ), "primary income omitted")],
      [f"CA = −80 + 35 − 18 + 38 = {caJ}", f"CAD/GDP = 25/{inr(gdpJ)} = {pct(-caJ/gdpJ)}"],
      "CA = Goods + Services + Primary + Secondary", "Remittances substantially shrink the CAD.", kind="case", group=GJ)
    q("balance-of-payments", "L4", stemJ + "**Q.** The net financial-account inflow excluding reserve changes is:",
      usd(faJ),
      [(usd(12 + 6 + 9 + 4 - 1.5), "portfolio outflow treated as an inflow"),
       (usd(faJ + 0.5), "capital account added into the financial account"),
       (usd(faJ - 1), "errors and omissions netted into the financial account")],
      [f"12 − 6 + 9 + 4 − 1.5 = {n(faJ,1)}"],
      "FA = FDI + FPI + Loans + Banking + Other", "Capital account (capital transfers) is separate from the financial account.", kind="case", group=GJ)
    q("why-the-balance", "L4", stemJ + "**Q.** The change in Oristan's foreign-exchange reserves that makes the BoP balance is:",
      f"Reserves fall by {usd(ovJ)}",
      [(f"Reserves fall by {usd(ovJ + 1)}", "errors and omissions ignored"),
       (f"Reserves rise by {usd(ovJ)}", "sign reversed"),
       (f"Reserves fall by {usd(ovJ - 0.5)}", "capital account ignored")],
      [f"Overall = −25 + 0.5 + 17.5 − 1 = {n(ovJ,1)}", "Overall deficit is financed by drawing down reserves by $8 bn."],
      "ΔReserves = −(CA + KA + FA + E&O)", "Reserve change is the balancing item.", kind="case", group=GJ)

    # ======================= L4 case K (monetary policy) =======================
    GK = "ECO-MPOL-CASE-K"
    prev = [140.0, 142.0, 145.0, 146.0]
    cur = [149.8, 152.4, 155.3, 154.8]
    yoy = [c / p - 1 for c, p in zip(cur, prev)]
    repo0, hike, pexp = 6.00, 0.50, 0.05
    stemK = ("**Case — Reserve Bank of Deccania.** The notified target is 4% CPI inflation with a tolerance band of ±2 percentage points; failure is "
             "defined as average inflation outside the band for three consecutive quarters. The policy repo rate is 6.00%; the standing deposit facility "
             "(SDF) rate is 25 bps below repo and the marginal standing facility (MSF) rate 25 bps above repo. Quarterly average CPI:\n\n" +
             tbl(["Quarter", "Q1", "Q2", "Q3", "Q4"], [["Previous year"] + [n(x, 1) for x in prev], ["Current year"] + [n(x, 1) for x in cur]]) + "\n\n")
    q("inflation-targeting", "L4", stemK + "**Q.** Year-on-year CPI inflation in Q3 of the current year is:",
      pct(yoy[2]),
      [(pct(cur[2] / cur[1] - 1), "quarter-on-quarter change computed"),
       (f"{n(cur[2]-prev[2],1)}%", "index-point change read as per cent"),
       (pct((cur[2] - prev[2]) / cur[2]), "current index used as base")],
      [f"{n(cur[2],1)}/{n(prev[2],1)} − 1 = {pct(yoy[2])}"],
      "y-o-y π = CPIₜ/CPIₜ₋₄ − 1", "Compare with the same quarter a year ago.", kind="case", group=GK)
    assert all(x > 0.06 for x in yoy[:3])
    q("inflation-targeting", "L4", stemK + "**Q.** By the end of Q3, has the central bank failed to meet the target under the stated framework?",
      "Yes — above 6% in Q1, Q2 and Q3, i.e. three consecutive quarters",
      [("No — failure requires four consecutive quarters outside the band", "threshold misremembered"),
       ("No — failure is judged only on the annual average inflation", "framework uses quarterly averages"),
       ("Yes — because inflation exceeded the 4% target in any single quarter", "target vs tolerance band confused")],
      [f"Q1 {pct(yoy[0])}, Q2 {pct(yoy[1])}, Q3 {pct(yoy[2])} — all above 6%.", "Three consecutive quarters ⇒ failure; the central bank must report reasons and remedial actions."],
      "Failure ⇔ 3 consecutive quarters outside [2%, 6%]", "Band, not point target, triggers failure.", kind="case", group=GK, verify_fact=True, ref=RBIACT)
    r1 = repo0 + hike
    q("direct-vs-indirect", "L4", stemK + f"**Q.** The MPC raises the repo rate by {int(hike*100)} bps. The new SDF and MSF rates are:",
      f"SDF {n(r1-0.25)}%, MSF {n(r1+0.25)}%",
      [(f"SDF {n(repo0)}%, MSF {n(r1+0.5)}%", "corridor widened instead of shifted"),
       (f"SDF {n(repo0-0.25)}%, MSF {n(repo0+0.25)}%", "corridor left at the old repo rate"),
       (f"SDF {n(r1)}%, MSF {n(r1+0.5)}%", "SDF set equal to repo and MSF 50 bps above")],
      [f"New repo = {n(repo0)} + {n(hike)} = {n(r1)}%", f"SDF = {n(r1)} − 0.25 = {n(r1-0.25)}%; MSF = {n(r1)} + 0.25 = {n(r1+0.25)}%"],
      "Corridor moves with repo; width unchanged", "SDF is the floor, MSF the ceiling.", kind="case", group=GK, verify_fact=True, ref=LAF)
    rr = (1 + r1 / 100) / (1 + pexp) - 1
    q("monetary-policy-transmission", "L4", stemK + f"**Q.** After the hike, if expected inflation over the next year is {pct(pexp)}, the ex-ante real policy rate (exact Fisher relation) is:",
      pct(rr),
      [(pct(r1 / 100 - pexp), "linear approximation instead of exact Fisher relation"),
       (pct(r1 / 100 - yoy[3]), "backward-looking Q4 inflation used instead of expected inflation"),
       (pct((1 + r1 / 100) * (1 + pexp) - 1), "compounded instead of deflated — nominal-like rate")],
      [f"(1 + {n(r1/100,3)})/(1 + {pexp}) − 1 = {pct(rr)}"],
      "1 + r = (1 + i)/(1 + πᵉ)", "Real rates drive spending decisions; use expected inflation.", kind="case", group=GK)
