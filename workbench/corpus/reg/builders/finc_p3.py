"""FIN-C part 3: leverage (5), EBIT-EPS (5), capital structure theories (4), dividend (1) — non-case."""
from finc_common import M, table, statements, stmt_opts, inr, R, pct, L, f2, PAT


def add_all(B):
    # ======================= Leverage (5) =======================
    m = M("leverage-operating-financial")
    B.add(m, "L1", "Operating leverage of a firm arises because of the presence of:",
          "Fixed operating costs in its cost structure",
          [("Fixed financial charges such as interest", "that causes financial leverage"),
           ("Variable costs that rise in line with sales", "variable costs do not magnify EBIT"),
           ("Preference dividend payable out of profits", "a fixed financial charge, not operating")],
          ["Fixed operating costs do not change with output, so a given % change in sales causes a larger % change in EBIT.",
           "DOL = Contribution ÷ EBIT; it exceeds 1 only when fixed operating costs exist."],
          "DOL = %ΔEBIT ÷ %ΔSales = C ÷ EBIT", "Interest and preference dividend drive financial, not operating, leverage.",
          kind="conceptual", ref=PAT)

    s, v, fc, i = 50, 30, 12, 3
    c = s - v; ebit = c - fc; ebt = ebit - i
    dol, dfl = c / ebit, ebit / ebt
    dcl = dol * dfl
    assert dcl == 4.0
    tb = table(["Particulars", "₹ lakh"], [["Sales", s], ["Variable cost", v], ["Fixed operating cost", fc], ["Interest", i]])
    B.add(m, "L2", f"Extract for Ananta Foods Ltd:\n\n{tb}\n\nThe degree of combined leverage is:",
          f2(dcl),
          [(f2(dol + dfl), "DOL and DFL added instead of multiplied"),
           (f2(dol * dol), "contribution ÷ EBIT used for DFL as well"),
           (f2(dol / dfl), "DOL divided by DFL")],
          [f"Contribution = {c}; EBIT = {ebit}; EBT = {ebt}",
           f"DOL = {c}/{ebit} = {dol:.2f}; DFL = {ebit}/{ebt} = {dfl:.2f}",
           f"DCL = {dol:.2f} × {dfl:.2f} = {dcl:.2f} (= Contribution ÷ EBT = {c}/{ebt})"],
          "DCL = DOL × DFL = C ÷ EBT", "Leverages multiply; they do not add.", ref=PAT)

    dol, dfl, ds = 2.2, 1.5, 0.12
    B.add(m, "L2", f"A company has a degree of operating leverage of {dol} and a degree of financial leverage of {dfl}. If sales rise by {pct(ds,0)}, EPS will rise by:",
          pct(dol * dfl * ds, 1),
          [(pct((dol + dfl) * ds, 1), "DOL and DFL added"),
           (pct(dol * ds, 1), "only operating leverage applied"),
           (pct(dfl * ds, 1), "only financial leverage applied")],
          [f"DCL = {dol} × {dfl} = {dol*dfl:.1f}", f"%ΔEPS = {dol*dfl:.1f} × {pct(ds,0)} = {pct(dol*dfl*ds,1)}"],
          "%ΔEPS = DCL × %ΔSales", "DFL links %ΔEBIT (not %ΔSales) to %ΔEPS.", ref=PAT)

    units, sp, vcu, fc, debt, r, pdiv, t = 4, 20, 12, 18, 40, 0.10, 3, 0.25  # lakh units, ₹, ₹ lakh
    c = units * (sp - vcu); ebit = c - fc; i = debt * r; ebt = ebit - i
    dfl = ebit / (ebt - pdiv / (1 - t))
    opts = [f2(dfl), f2(ebit / ebt), f2(ebit / (ebt - pdiv)), f2(ebit / (ebt - pdiv * (1 - t)))]
    assert len(set(opts)) == 4 and abs(dfl - 14 / 6) < 1e-12
    tb = table(["Particulars", "Data"], [["Sales", f"{units} lakh units at ₹{sp}"], ["Variable cost", f"₹{vcu} per unit"],
                                         ["Fixed operating cost", L(fc, 0)], ["10% debentures", L(debt, 0)],
                                         ["Preference dividend", L(pdiv, 0)], ["Tax rate", pct(t, 0)]])
    B.add(m, "L3", f"Data for Bhavya Plastics Ltd:\n\n{tb}\n\nThe degree of financial leverage is:",
          opts[0],
          [(opts[1], "preference dividend ignored"),
           (opts[2], "preference dividend deducted without grossing up for tax"),
           (opts[3], "preference dividend multiplied by (1 − t) instead of divided")],
          [f"Contribution = {units} × {sp-vcu} = ₹{c} lakh; EBIT = {c} − {fc} = ₹{ebit} lakh",
           f"Interest = ₹{i:g} lakh; EBT = ₹{ebt:g} lakh; pre-tax equivalent of preference dividend = {pdiv}/0.75 = ₹{pdiv/(1-t):g} lakh",
           f"DFL = {ebit} ÷ ({ebt:g} − {pdiv/(1-t):g}) = {opts[0]}"],
          "DFL = EBIT ÷ [EBIT − I − Dp/(1 − t)]", "Preference dividend is paid from post-tax profit, so gross it up.", ref=PAT)

    dol, dfl, i, pv = 3, 2, 6, 0.40
    ebit = i * dfl / (dfl - 1)
    c = dol * ebit; sales = c / pv; fc = c - ebit
    assert ebit == 12 and fc == 24
    B.add(m, "L3", f"Kanak Metals Ltd has a degree of operating leverage of {dol}, a degree of financial leverage of {dfl}, interest of ₹{i} lakh and a P/V ratio of {pct(pv,0)}. It has no preference capital. Its fixed operating cost is:",
          L(fc, 0),
          [(L(c, 0), "contribution reported as fixed cost"),
           (L(c - i, 0), "interest deducted from contribution instead of EBIT"),
           (L(sales - c, 0), "variable cost (sales − contribution) reported")],
          [f"DFL = EBIT/(EBIT − I) → 2 = EBIT/(EBIT − 6) → EBIT = ₹{ebit:g} lakh",
           f"DOL = C/EBIT → C = 3 × {ebit:g} = ₹{c:g} lakh; sales = {c:g}/0.40 = ₹{sales:g} lakh",
           f"Fixed cost = C − EBIT = {c:g} − {ebit:g} = ₹{fc:g} lakh"],
          "EBIT = I × DFL/(DFL − 1); FC = C − EBIT", "Work back from DFL first to find EBIT.", ref=PAT)

    # ======================= EBIT-EPS (5) =======================
    m = M("ebit-eps-analysis")
    B.add(m, "L1", "The financial break-even point of a firm with debt and preference capital is the level of EBIT at which:",
          "EPS is zero — EBIT just covers interest and pre-tax preference dividend",
          [("EPS is identical under two alternative financing plans being compared", "that is the indifference point"),
           ("Contribution exactly equals the fixed operating costs of the firm", "that is the operating break-even point"),
           ("EBIT just covers interest, with preference dividend left out", "omits the grossed-up preference dividend")],
          ["Financial BEP = I + Dp/(1 − t).", "At this EBIT, nothing is left for equity holders, so EPS = 0."],
          "Financial BEP = I + Dp ÷ (1 − t)", "Do not confuse with the indifference point or the operating BEP.",
          kind="conceptual", ref=PAT)

    t, n_a, n_b, i_b = 0.25, 5, 2, 3
    ind = i_b * n_a / (n_a - n_b)
    ind_gross = i_b / (1 - t) * n_a / (n_a - n_b)
    ind_allint = 5 * n_a / (n_a - n_b)
    assert ind == 5
    B.add(m, "L2", f"A new company needs ₹50 lakh. Plan A: all equity — {n_a} lakh shares of ₹10. Plan B: {n_b} lakh shares of ₹10 plus ₹30 lakh of 10% debentures. Tax rate {pct(t,0)}. The EBIT at which EPS is the same under both plans is:",
          L(ind),
          [(L(ind_gross), "interest grossed up for tax as if it were preference dividend"),
           (L(i_b), "financial break-even point of Plan B reported"),
           (L(ind_allint), "10% interest charged on the entire ₹50 lakh")],
          ["EBIT(1 − t)/5 = (EBIT − 3)(1 − t)/2",
           "2 EBIT = 5 EBIT − 15 → EBIT = ₹5 lakh",
           "Check: EPS = 5 × 0.75/5 = ₹0.75 under both plans"],
          "(EBIT − I₁)(1 − t)/N₁ = (EBIT − I₂)(1 − t)/N₂", "Interest is deducted pre-tax; it is not grossed up.", ref=PAT)

    ebit, t, n, pref_amt, pr = 12, 0.25, 5, 30, 0.12
    pd = pref_amt * pr
    eps = (ebit * (1 - t) - pd) / n
    opts = [f"₹{x:.2f}" for x in (eps, (ebit - pd) * (1 - t) / n, ebit * (1 - t) / n, (ebit * (1 - t) - pd / (1 - t)) / n)]
    assert len(set(opts)) == 4 and abs(eps - 1.08) < 1e-12
    B.add(m, "L2", f"Under a proposed plan, Lakshya Retail Ltd will have {n} lakh equity shares and ₹{pref_amt} lakh of {pct(pr,0)} preference shares, and no debt. Expected EBIT is ₹{ebit} lakh and the tax rate is {pct(t,0)}. EPS under this plan is:",
          opts[0],
          [(opts[1], "preference dividend deducted before tax as if it were interest"),
           (opts[2], "preference dividend ignored"),
           (opts[3], "preference dividend grossed up and deducted from profit after tax")],
          [f"PAT = {ebit} × 0.75 = ₹{ebit*(1-t):.2f} lakh", f"Less preference dividend ₹{pd:.2f} lakh → ₹{ebit*(1-t)-pd:.2f} lakh",
           f"EPS = {ebit*(1-t)-pd:.2f} ÷ {n} = {opts[0]}"],
          "EPS = [(EBIT − I)(1 − t) − Dp] ÷ N", "Preference dividend comes out of PAT, at face amount.", ref=PAT)

    t, i0, n1, n2, pd = 0.30, 1.5, 6, 4, 2.4
    x = pd * n1 / ((1 - t) * (n1 - n2))  # EBIT - i0
    ind = x + i0
    wrong_pre = pd * n1 / (n1 - n2) + i0
    wrong_noi = x
    fbep = i0 + pd / (1 - t)
    opts = [L(v) for v in (ind, wrong_pre, wrong_noi, fbep)]
    assert len(set(opts)) == 4
    B.add(m, "L3", f"Charvi Textiles Ltd has 4 lakh equity shares and ₹15 lakh of 10% debentures. It needs ₹20 lakh more and is choosing between (i) issuing 2 lakh equity shares at ₹10, and (ii) issuing ₹20 lakh of 12% preference shares. Tax rate {pct(t,0)}. The EBIT at which EPS is the same under both options is:",
          opts[0],
          [(opts[1], "preference dividend deducted before tax like interest"),
           (opts[2], "existing debenture interest ignored"),
           (opts[3], "financial break-even point of the preference option reported")],
          ["Equity option: N = 6 lakh; preference option: N = 4 lakh, Dp = ₹2.4 lakh; interest ₹1.5 lakh in both",
           "(EBIT − 1.5)(0.7)/6 = [(EBIT − 1.5)(0.7) − 2.4]/4",
           f"0.7(EBIT − 1.5) × (1/4 − 1/6) = 0.6 → EBIT − 1.5 = {x:.4f} → EBIT = {opts[0]}"],
          "(EBIT − I)(1 − t)/N₁ = [(EBIT − I)(1 − t) − Dp]/N₂", "Existing interest appears in both plans and shifts the point.", ref=PAT)

    ebit, t = 20, 0.25
    plans = {"A": (6, 0, 0), "B": (3, 3.6, 0), "C": (3, 0, 3.3)}
    eps = {k: ((ebit - i) * (1 - t) - p) / n for k, (n, i, p) in plans.items()}
    rank = sorted(eps, key=lambda k: -eps[k])
    second = rank[1]
    n2, i2, p2 = plans[second]
    fb = i2 + p2 / (1 - t)
    assert rank == ["B", "C", "A"]
    tb = table(["Plan", "Equity (₹10 shares)", "Debt", "Preference"],
               [["A", "₹60 lakh", "—", "—"], ["B", "₹30 lakh", "₹30 lakh at 12%", "—"], ["C", "₹30 lakh", "—", "₹30 lakh at 11%"]])
    B.add(m, "L3", f"Suvidha Logistics Ltd, a new company, will raise ₹60 lakh under one of these plans:\n\n{tb}\n\nExpected EBIT is ₹{ebit} lakh; tax rate {pct(t,0)}. Which plan ranks second on EPS, and what is that plan's financial break-even point?",
          f"Plan {second}; {L(fb)}",
          [(f"Plan {second}; {L(p2)}", "preference dividend not grossed up for tax"),
           (f"Plan {second}; {L(p2*(1-t))}", "preference dividend multiplied by (1 − t)"),
           (f"Plan {rank[0]}; {L(plans[rank[0]][1])}", "top-ranked plan and its break-even reported")],
          ["EPS: " + "; ".join(f"{k} = ₹{eps[k]:.2f}" for k in plans),
           f"Ranking: {' > '.join(rank)} → second is Plan {second}",
           f"Financial BEP (Plan {second}) = {p2}/0.75 = ₹{fb:.2f} lakh"],
          "Financial BEP = I + Dp/(1 − t)", "Preference dividend must be grossed up to a pre-tax EBIT equivalent.", ref=PAT)

    # ======================= Capital structure theories (4) =======================
    m = M("capital-structure-theories")
    B.add(m, "L1", "Under the Net Operating Income (NOI) approach, as a firm substitutes debt for equity, which of the following remains constant?",
          "The overall cost of capital (Ko) and the value of the firm",
          [("The cost of equity (Ke) and the value of equity", "Ke rises with leverage under NOI"),
           ("The cost of equity (Ke) and the market price per share", "Ke rises; only V and Ko are constant"),
           ("The equity capitalisation rate and the overall cost of capital", "Ke is not constant under NOI")],
          ["NOI: V = EBIT ÷ Ko with Ko constant, so V is independent of leverage.",
           "Cheaper debt is exactly offset by a rising Ke, so capital structure is irrelevant."],
          "V = EBIT ÷ Ko;  Ke = Ko + (Ko − Kd)D/E", "Under the NI approach, by contrast, Ke and Kd are constant and Ko falls.",
          kind="conceptual", ref=PAT)

    ebit, D, kd, ke = 10, 30, 0.10, 0.15
    E = (ebit - D * kd) / ke; V = E + D; ko = ebit / V
    E2 = ebit / ke; ko2 = ebit / (E2 + D)
    assert abs(ko - 10 / (7 / 0.15 + 30)) < 1e-12
    B.add(m, "L2", f"Rishabh Engineering Ltd has EBIT of ₹{ebit} lakh and ₹{D} lakh of {pct(kd,0)} debt. Its equity capitalisation rate is {pct(ke,0)}. Under the Net Income approach (no taxes), its overall cost of capital is:",
          pct(ko),
          [(pct(ke), "equity capitalisation rate reported as Ko"),
           (pct((ke + kd) / 2), "simple average of Ke and Kd"),
           (pct(ko2), "value of equity computed by capitalising EBIT instead of net income")],
          [f"Net income = {ebit} − {D*kd:g} = ₹{ebit-D*kd:g} lakh; E = {ebit-D*kd:g}/0.15 = ₹{E:.2f} lakh",
           f"V = {E:.2f} + {D} = ₹{V:.2f} lakh", f"Ko = {ebit} ÷ {V:.2f} = {pct(ko)}"],
          "E = (EBIT − I)/Ke;  Ko = EBIT/V", "Equity holders capitalise net income, not EBIT.", ref=PAT)

    ebit, ku, D, kd = 12, 0.12, 40, 0.08
    V = ebit / ku; E = V - D
    ke = ku + (ku - kd) * D / E
    opts = [pct(x) for x in (ke, ku + (ku - kd) * D / V, ku, (ebit - D * kd) / V)]
    assert V == 100 and len(set(opts)) == 4
    B.add(m, "L3", f"Firms U and L are identical except that L has ₹{D} lakh of {pct(kd,0)} debt; U is all-equity. Both earn EBIT of ₹{ebit} lakh and U's cost of equity is {pct(ku,0)}. Assuming Modigliani–Miller conditions without taxes, L's cost of equity is:",
          opts[0],
          [(opts[1], "debt ÷ total value used instead of debt ÷ equity"),
           (opts[2], "cost of equity assumed unchanged by leverage"),
           (opts[3], "net income divided by total firm value")],
          [f"MM (no tax): VL = VU = {ebit}/0.12 = ₹{V:.0f} lakh; EL = {V:.0f} − {D} = ₹{E:.0f} lakh",
           f"KeL = Ku + (Ku − Kd) × D/E = 12% + 4% × {D}/{E:.0f} = {opts[0]}",
           f"Check: (EBIT − I)/E = {ebit-D*kd:.1f}/{E:.0f} = {opts[0]}"],
          "KeL = Ku + (Ku − Kd)(D/E)", "The risk premium scales with D/E, not D/V.", ref=PAT)

    ebit, ku_u, D, kd, ke_l, own = 20, 0.125, 50, 0.10, 0.12, 0.10
    VU = ebit / ku_u; EL = (ebit - D * kd) / ke_l; VL = EL + D
    sell = own * EL; inc_old = own * (ebit - D * kd)
    borrow = own * D; buy = sell + borrow
    inc_new = buy / VU * ebit - borrow * kd
    gain = inc_new - inc_old
    no_int = buy / VU * ebit - inc_old
    no_borrow = sell / VU * ebit - inc_old
    saved = sell - (own * VU - borrow)
    assert VU == 160 and VL == 175 and abs(gain - 0.1875) < 1e-9
    tb = table(["Particulars", "Firm U", "Firm L"], [["EBIT (₹ lakh)", ebit, ebit], ["10% debt (₹ lakh)", "—", D],
                                                    ["Equity capitalisation rate", pct(ku_u, 1), pct(ke_l, 0)]])
    B.add(m, "L3", f"Two firms are identical in every respect except capital structure (ignore taxes):\n\n{tb}\n\nAn investor owns 10% of L's equity. Under MM arbitrage, he sells his L shares, borrows personally at 10% in proportion to his share of L's debt, and invests the entire amount in U's shares. The increase in his annual income is:",
          R(round(gain * 1e5)),
          [(R(round(no_int * 1e5)), "interest on the personal borrowing not deducted"),
           (R(round(saved * 1e5)), "cash saved by buying the same 10% of U reported as income"),
           (R(round(no_borrow * 1e5)), "no personal borrowing (homemade leverage) undertaken")],
          [f"VU = 20/0.125 = ₹{VU:.0f} lakh; EL = (20 − 5)/0.12 = ₹{EL:.0f} lakh; VL = ₹{VL:.0f} lakh → L is overvalued",
           f"Sell 10% of L = ₹{sell:.2f} lakh (income ₹{inc_old:.2f} lakh); borrow ₹{borrow:.0f} lakh; invest ₹{buy:.2f} lakh in U",
           f"New income = {buy:.2f}/{VU:.0f} × 20 − {borrow:.0f} × 10% = ₹{inc_new:.4f} lakh",
           f"Gain = {inc_new:.4f} − {inc_old:.2f} = ₹{gain:.4f} lakh = {R(round(gain*1e5))}"],
          "Arbitrage: replicate L's financial risk with personal leverage in U", "Personal borrowing is what keeps the financial risk identical.", ref=PAT)

    # ======================= Dividend policy (1 non-case) =======================
    m = M("dividend-policy-models")
    B.add(m, "L1", "Under Walter's model, for a growth firm whose return on investment (r) exceeds its cost of equity (k), the optimum dividend payout ratio is:",
          "Zero — all earnings should be retained",
          [("100% — all earnings should be distributed", "optimal for a declining firm (r < k)"),
           ("Irrelevant — every payout gives the same price", "true only for a normal firm (r = k)"),
           ("Equal to the ratio of k to r for the firm", "no such rule in Walter's model")],
          ["Walter: P = [D + (r/k)(E − D)] ÷ k.", "When r > k, each rupee retained adds more than a rupee to price, so price is maximised at D = 0."],
          "P = [D + (r/k)(E − D)] ÷ k", "Match the payout rule to the firm type: growth (0%), normal (irrelevant), declining (100%).",
          kind="conceptual", ref=PAT)
