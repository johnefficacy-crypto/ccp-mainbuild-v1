"""FIN-C part 4: L4 case sets.
C1 project appraisal (4) · C2 financing decision (4) · C3 dividend decision (4) · C4 MM with taxes + CAPM (3)."""
from finc_common import M, table, inr, R, pct, L, f2, yrs, pvf, PAT


def add_all(B):
    # ============ C1: Ashvik Components — full project appraisal ============
    cost, inst, sal_est, sal_act, life, wc, t, k = 48, 2, 5, 8, 5, 6, 0.25, 0.12
    units = [20000, 24000, 28000, 28000, 22000]; sp, vc, fcc = 400, 250, 12
    basis = cost + inst
    dep = (basis - sal_est) / life
    f = [pvf(k, i + 1) for i in range(life)]
    def cfat_series(dep_, tx=t):
        return [((u * (sp - vc) / 1e5 - fcc - dep_) * (1 - tx) + dep_) for u in units]
    cf = cfat_series(dep)
    term = sal_act - t * (sal_act - sal_est) + wc
    assert abs(cf[1] - 20.25) < 1e-9 and abs(term - 13.25) < 1e-9
    outlay = basis + wc
    flows = cf[:-1] + [cf[-1] + term]
    npv = sum(c * x for c, x in zip(flows, f)) - outlay
    npv_nowc = sum(c * x for c, x in zip(cf[:-1] + [cf[-1] + term - wc], f)) - basis
    npv_noterm = sum(c * x for c, x in zip(cf, f)) - outlay
    dep_x = (cost - sal_est) / life
    cf_x = cfat_series(dep_x)
    term_x = sal_act - t * (sal_act - (sal_est + 0)) + wc
    npv_x = sum(c * x for c, x in zip(cf_x[:-1] + [cf_x[-1] + term_x], f)) - (cost + wc)
    C1 = ("**Case — Ashvik Components Ltd.** The company is appraising a new precision-parts line. Data:\n\n" +
          table(["Item", "Data"], [["Machine cost / installation", f"{L(cost,0)} / {L(inst,0)} (installation is capitalised)"],
                                   ["Life; depreciation", f"{life} years; straight-line on capitalised cost less estimated salvage of {L(sal_est,0)}"],
                                   ["Actual sale value at end of year 5", f"{L(sal_act,0)}; profit over book value taxed at {pct(t,0)}"],
                                   ["Working capital", f"{L(wc,0)} at start, fully released at end of year 5"],
                                   ["Selling price / variable cost", f"₹{sp} / ₹{vc} per unit"],
                                   ["Incremental fixed cash cost", f"{L(fcc,0)} a year"],
                                   ["Tax rate; cost of capital", f"{pct(t,0)}; {pct(k,0)}"]]) + "\n\n" +
          table(["Year", "1", "2", "3", "4", "5"], [["Units sold"] + [inr(u) for u in units], ["PVF at 12%"] + f]))
    g = "FINC-C1-ashvik"
    B.add(M("npv-irr-pi-and-mirr"), "L4", C1 + "\n\nThe cash flow after tax from operations in year 2 is:",
          L(cf[1]),
          [(L(cf_x[1]), "installation cost left out of the depreciable base"),
           (L((units[1] * (sp - vc) / 1e5 - fcc) * (1 - t)), "tax charged on EBDT; depreciation tax shield ignored"),
           (L((units[1] * (sp - vc) / 1e5 - fcc - dep) * (1 - t)), "profit after tax; depreciation not added back")],
          [f"Depreciation = ({cost} + {inst} − {sal_est}) ÷ {life} = ₹{dep:g} lakh",
           f"Year 2: contribution = 24,000 × ₹150 = ₹36 lakh; EBDT = 36 − 12 = ₹24 lakh",
           f"CFAT = (24 − {dep:g}) × 0.75 + {dep:g} = ₹{cf[1]:.2f} lakh"],
          "CFAT = (EBDT − Dep)(1 − t) + Dep", "Installation is capitalised and depreciated.", group=g, kind="case", ref=PAT)

    B.add(M("npv-irr-pi-and-mirr"), "L4", C1 + "\n\nThe terminal (non-operating) cash inflow at the end of year 5 is:",
          L(term),
          [(L(sal_act + wc), "tax on profit on sale ignored"),
           (L(sal_act * (1 - t) + wc), "tax charged on the entire sale value instead of the profit over book value"),
           (L(sal_act - t * (sal_act - sal_est)), "release of working capital omitted")],
          [f"Book value at end = estimated salvage = ₹{sal_est} lakh; profit on sale = {sal_act} − {sal_est} = ₹{sal_act-sal_est} lakh",
           f"Tax = {pct(t,0)} × {sal_act-sal_est} = ₹{t*(sal_act-sal_est):.2f} lakh → net salvage = ₹{sal_act-t*(sal_act-sal_est):.2f} lakh",
           f"Terminal inflow = {sal_act-t*(sal_act-sal_est):.2f} + WC {wc} = ₹{term:.2f} lakh"],
          "Terminal CF = Sale value − t(Sale value − BV) + WC", "Only the gain over book value is taxed.", group=g, kind="case", ref=PAT)

    B.add(M("npv-irr-pi-and-mirr"), "L4", C1 + "\n\nThe NPV of the project is:",
          L(npv),
          [(L(npv_nowc), "working capital ignored at both ends"),
           (L(npv_noterm), "terminal inflow (net salvage + working capital) omitted"),
           (L(npv_x), "installation cost ignored in both the outlay and the depreciable base")],
          ["CFAT (₹ lakh): " + ", ".join(f"{c:.2f}" for c in cf) + f"; add terminal ₹{term:.2f} lakh in year 5",
           f"PV of inflows = {' + '.join(f'{c:.2f}×{x}' for c, x in zip(flows, f))} = ₹{npv+outlay:.3f} lakh",
           f"Outlay = {basis} + {wc} = ₹{outlay} lakh; NPV = ₹{npv:.3f} lakh"],
          "NPV = Σ CFt × PVFt − (Capital cost + WC)", "The outlay includes installation and working capital.", group=g, kind="case", ref=PAT)

    pv = [c * x for c, x in zip(flows, f)]
    cum, yr = 0, 0
    while cum + pv[yr] < outlay:
        cum += pv[yr]; yr += 1
    dpb = yr + (outlay - cum) / pv[yr]
    cu, y2 = 0, 0
    while cu + flows[y2] < outlay:
        cu += flows[y2]; y2 += 1
    spb = y2 + (outlay - cu) / flows[y2]
    cum3, y3 = 0, 0
    while cum3 + pv[y3] < basis:
        cum3 += pv[y3]; y3 += 1
    dpb_nowc = y3 + (basis - cum3) / pv[y3]
    wrong = yr + (outlay - cum) / flows[yr]
    opts = [yrs(x) for x in (dpb, spb, dpb_nowc, wrong)]
    assert len(set(opts)) == 4
    B.add(M("payback-and-discounted"), "L4", C1 + "\n\nThe discounted payback period of the project is:",
          opts[0],
          [(opts[1], "simple (undiscounted) payback"),
           (opts[2], "working capital excluded from the amount to be recovered"),
           (opts[3], "final fraction computed on the undiscounted year-4 cash flow")],
          ["Discounted inflows (₹ lakh): " + ", ".join(f"{x:.3f}" for x in pv),
           f"Cumulative after {yr} years = ₹{cum:.3f} lakh; balance = {outlay} − {cum:.3f} = ₹{outlay-cum:.3f} lakh",
           f"DPB = {yr} + {outlay-cum:.3f}/{pv[yr]:.3f} = {opts[0]}"],
          "DPB = Years before recovery + Unrecovered PV ÷ PV of next year's inflow",
          "Working capital is part of the investment to be recovered.", group=g, kind="case", ref=PAT)

    # ============ C2: Kavera Foods — financing an expansion ============
    sh0, res, deb0, r0 = 20, 50, 100, 0.10
    need, price, fl, d0, gr = 150, 25, 1, 2.0, 0.07
    rB, t = 0.12, 0.25
    sales, vr, fco = 400, 0.60, 70
    cont = sales * (1 - vr); ebit = cont - fco
    newsh = need / price
    iA, iB = deb0 * r0, deb0 * r0 + need * rB
    nA, nB = sh0 + newsh, sh0
    dcl_B = cont / (ebit - iB); dcl_A = cont / (ebit - iA)
    dol, dflB = cont / ebit, ebit / (ebit - iB)
    assert ebit == 90 and newsh == 6
    C2 = ("**Case — Kavera Foods Ltd.** Present capital: 20 lakh equity shares of ₹10 each, reserves ₹50 lakh and ₹100 lakh of 10% debentures. "
          f"An expansion costing ₹{need} lakh is planned. After expansion: sales ₹{sales} lakh, variable cost {pct(vr,0)} of sales, fixed operating cost ₹{fco} lakh. Two financing plans are considered:\n\n" +
          table(["Plan", "Instrument"], [["A", f"Equity shares issued at ₹{price} (6 lakh shares); flotation cost ₹{fl} per share"],
                                         ["B", f"{pct(rB,0)} debentures of ₹{need} lakh"]]) +
          f"\n\nTax rate {pct(t,0)}. The dividend just paid is ₹{d0:.2f} per share, expected to grow at {pct(gr,0)} a year; the current share price is ₹{price}.")
    g = "FINC-C2-kavera"
    B.add(M("leverage-operating-financial"), "L4", C2 + "\n\nThe degree of combined leverage after expansion under Plan B is:",
          f2(dcl_B),
          [(f2(dcl_A), "Plan A's combined leverage (only existing interest)"),
           (f2(dol + dflB), "DOL and DFL added instead of multiplied"),
           (f2(cont / (ebit - need * rB)), "only the new debenture interest deducted")],
          [f"Contribution = {sales} × 40% = ₹{cont:g} lakh; EBIT = {cont:g} − {fco} = ₹{ebit:g} lakh",
           f"Interest under Plan B = 10 + 18 = ₹{iB:g} lakh; EBT = ₹{ebit-iB:g} lakh",
           f"DCL = {cont:g} ÷ {ebit-iB:g} = {dcl_B:.2f} (DOL {dol:.2f} × DFL {dflB:.2f})"],
          "DCL = Contribution ÷ EBT", "Existing debenture interest continues under both plans.", group=g, kind="case", ref=PAT)

    ind = (nA * iB - nB * iA) / (nA - nB)
    ind_noold = (nA * need * rB) / (nA - nB)
    npar = sh0 + need / 10
    ind_par = (npar * iB - nB * iA) / (npar - nB)
    ind_oneside = (nA * need * rB - nB * iA) / (nA - nB)
    opts = [L(x) for x in (ind, ind_noold, ind_par, ind_oneside)]
    assert abs(ind - 88) < 1e-9 and len(set(opts)) == 4
    B.add(M("ebit-eps-analysis"), "L4", C2 + "\n\nThe EBIT at which EPS is the same under Plans A and B is:",
          opts[0],
          [(opts[1], "existing debenture interest ignored in both plans"),
           (opts[2], "new shares assumed issued at par (15 lakh shares)"),
           (opts[3], "existing interest deducted only under Plan A")],
          [f"Plan A: N = {nA:g} lakh, I = ₹{iA:g} lakh; Plan B: N = {nB:g} lakh, I = ₹{iB:g} lakh",
           f"(EBIT − {iA:g})(0.75)/{nA:g} = (EBIT − {iB:g})(0.75)/{nB:g}",
           f"{nB:g}·EBIT − {nB*iA:g} = {nA:g}·EBIT − {nA*iB:g} → EBIT = ₹{ind:g} lakh"],
          "(EBIT − I_A)/N_A = (EBIT − I_B)/N_B", "Expected EBIT (₹90 lakh) is just above the point, so Plan B gives the higher EPS.",
          group=g, kind="case", ref=PAT)

    d1 = d0 * (1 + gr)
    ke_new = d1 / (price - fl) + gr
    ke_re = d1 / price + gr
    opts = [pct(x) for x in (ke_new, ke_re, d0 / (price - fl) + gr, d1 / (price + fl) + gr)]
    assert len(set(opts)) == 4
    B.add(M("cost-of-capital-debt-preference"), "L4", C2 + "\n\nThe cost of the new equity under Plan A is:",
          opts[0],
          [(opts[1], "flotation cost ignored"),
           (opts[2], "D0 used instead of D1"),
           (opts[3], "flotation cost added to the price instead of deducted")],
          [f"D1 = {d0:.2f} × 1.07 = ₹{d1:.2f}; net proceeds = {price} − {fl} = ₹{price-fl}",
           f"Ke = {d1:.2f}/{price-fl} + 7% = {opts[0]}"],
          "Ke(new) = D1 ÷ (P0 − f) + g", "Flotation cost reduces the net proceeds per share.", group=g, kind="case", ref=PAT)

    ke_B = 0.165
    E_bv = sh0 * 10 + res
    w = (E_bv * ke_B + deb0 * r0 * (1 - t) + need * rB * (1 - t)) / (E_bv + deb0 + need)
    w_pre = (E_bv * ke_B + deb0 * r0 + need * rB) / (E_bv + deb0 + need)
    w_one = (E_bv * ke_B + (deb0 + need) * rB * (1 - t)) / (E_bv + deb0 + need)
    w_oldke = (E_bv * ke_re + deb0 * r0 * (1 - t) + need * rB * (1 - t)) / (E_bv + deb0 + need)
    opts = [pct(x) for x in (w, w_pre, w_one, w_oldke)]
    assert abs(w - 0.1245) < 1e-12 and len(set(opts)) == 4
    B.add(M("weighted-average-and-marginal"), "L4", C2 + f"\n\nIf Plan B is adopted, the cost of equity is expected to rise to {pct(ke_B,1)}. Using book-value weights, the WACC after expansion is:",
          opts[0],
          [(opts[1], "pre-tax cost of debentures used"),
           (opts[2], "all debentures costed at the new 12% coupon"),
           (opts[3], "pre-expansion cost of equity (from the dividend-growth model) used")],
          [f"Equity (capital + reserves) = ₹{E_bv} lakh at {pct(ke_B,1)}; old debentures ₹{deb0} lakh at 10% × 0.75 = 7.5%; new ₹{need} lakh at 12% × 0.75 = 9%",
           f"WACC = ({E_bv} × 16.5% + {deb0} × 7.5% + {need} × 9%) ÷ {E_bv+deb0+need} = {opts[0]}"],
          "WACC = Σ (BVᵢ × post-tax kᵢ) ÷ Σ BVᵢ", "Each debt tranche keeps its own coupon.", group=g, kind="case", ref=PAT)

    # ============ C3: Meridian Tools — dividend decision ============
    eps, r, k, n_sh, payout, p0, inv = 12, 0.18, 0.14, 5, 0.40, 100, 90
    D = eps * payout
    walter = lambda d: (d + r / k * (eps - d)) / k
    C3 = (f"**Case — Meridian Tools Ltd.** EPS ₹{eps}; return on investment {pct(r,0)}; cost of equity {pct(k,0)}; {n_sh} lakh equity shares; "
          f"present payout ratio {pct(payout,0)}; current market price ₹{p0}. The company plans capital investment of ₹{inv} lakh next year and expects net income of ₹{eps*n_sh} lakh.")
    g = "FINC-C3-meridian"
    pw = walter(D)
    opts = [f"₹{x:.2f}" for x in (pw, (D + k / r * (eps - D)) / k, (D + r / k * (eps - D)) / r, eps / k)]
    assert len(set(opts)) == 4
    B.add(M("dividend-policy-models"), "L4", C3 + "\n\nUnder Walter's model, the price per share at the present payout ratio is:",
          opts[0],
          [(opts[1], "r and k interchanged in the retention term"),
           (opts[2], "capitalised at r instead of k"),
           (opts[3], "EPS ÷ k — treats payout as irrelevant")],
          [f"D = {eps} × {payout} = ₹{D:.2f}; retained = ₹{eps-D:.2f}",
           f"P = [{D:.2f} + (0.18/0.14) × {eps-D:.2f}] ÷ 0.14 = {opts[0]}"],
          "P = [D + (r/k)(E − D)] ÷ k", "r/k multiplies the retained part only.", group=g, kind="case", ref=PAT)

    B.add(M("dividend-policy-models"), "L4", C3 + "\n\nUnder Walter's model, the optimum payout ratio and the corresponding price per share are:",
          f"0%; ₹{walter(0):.2f}",
          [(f"100%; ₹{walter(eps):.2f}", "declining-firm rule applied although r > k"),
           (f"40%; ₹{pw:.2f}", "present payout assumed optimal"),
           (f"0%; ₹{eps/k:.2f}", "correct payout but price computed as EPS ÷ k")],
          ["r (18%) > k (14%) → growth firm → retain everything",
           f"P = [0 + (0.18/0.14) × {eps}] ÷ 0.14 = ₹{walter(0):.2f}"],
          "Walter: r > k ⇒ D/P = 0", "Price rises steadily as payout falls when r > k.", group=g, kind="case", ref=PAT)

    b = 1 - payout
    gg = b * r
    pg = eps * (1 - b) / (k - gg)
    g_wrong = payout * r
    opts = [f"₹{x:.2f}" for x in (pg, eps * (1 - b) / (k - g_wrong), eps * (1 - b) * (1 + gg) / (k - gg), eps * (1 - b) / (k - b * k))]
    assert abs(pg - 150) < 1e-9 and len(set(opts)) == 4
    B.add(M("dividend-policy-models"), "L4", C3 + "\n\nTreating ₹12 as next year's EPS, the price per share under Gordon's model at the present payout ratio is:",
          opts[0],
          [(opts[1], "growth computed as payout × r instead of retention × r"),
           (opts[2], "dividend grown once more although EPS is already next year's"),
           (opts[3], "growth computed as retention × k instead of retention × r")],
          [f"b = {b:.1f}; g = b × r = {b:.1f} × 18% = {pct(gg,1)}",
           f"P = E(1 − b) ÷ (k − br) = {eps*(1-b):.2f} ÷ ({pct(k,0)} − {pct(gg,1)}) = {opts[0]}"],
          "P = E₁(1 − b) ÷ (k − br)", "g must be below k; here the spread is only 3.2%.", group=g, kind="case", ref=PAT)

    ni = eps * n_sh
    p1 = p0 * (1 + k) - D
    fin = inv - (ni - D * n_sh)
    m_new = fin / p1 * 1e5
    p1n = p0 * (1 + k)
    alt = [(inv - ni) / p1n * 1e5, inv / p1 * 1e5, fin / p0 * 1e5]
    opts = [f"{inr(round(x))} shares" for x in [m_new] + alt]
    assert abs(p1 - 109.2) < 1e-9 and len(set(opts)) == 4
    B.add(M("dividend-policy-models"), "L4", C3 + f"\n\nThe company decides to pay a dividend of ₹{D:.2f} per share at the end of the year. Under the Modigliani–Miller model, the number of new shares it must issue at year-end to finance the investment is closest to:",
          opts[0],
          [(opts[1], "no-dividend case (P₁ = ₹114, only ₹30 lakh to raise)"),
           (opts[2], "entire investment treated as externally financed"),
           (opts[3], "new shares priced at the current price instead of P₁")],
          [f"P₁ = P₀(1 + k) − D₁ = 100 × 1.14 − {D:.2f} = ₹{p1:.2f}",
           f"Retained earnings = {ni} − {D:.2f} × {n_sh} = ₹{ni-D*n_sh:g} lakh; funds to raise = {inv} − {ni-D*n_sh:g} = ₹{fin:g} lakh",
           f"New shares = {fin:g} lakh ÷ {p1:.2f} = {opts[0]}"],
          "P₁ = P₀(1 + ke) − D₁;  m = (I − (E − nD₁)) ÷ P₁", "The ex-dividend price P₁, not P₀, is the issue price.", group=g, kind="case", ref=PAT)

    # ============ C4: Rudra Logistics — MM with taxes and CAPM ============
    ebit, ku, t, D, kd, bu, rf, rm = 30, 0.15, 0.25, 60, 0.07, 1.0, 0.07, 0.15
    VU = ebit * (1 - t) / ku
    VL = VU + t * D
    E = VL - D
    C4 = (f"**Case — Rudra Logistics Ltd** is all-equity financed. EBIT is ₹{ebit} lakh a year in perpetuity, all earnings are distributed, and its cost of equity is {pct(ku,0)} "
          f"(unlevered beta {bu:.1f}; risk-free rate {pct(rf,0)}; expected market return {pct(rm,0)}). The corporate tax rate is {pct(t,0)}. It plans to issue ₹{D} lakh of perpetual debt at the risk-free rate of {pct(kd,0)} and use the proceeds to buy back shares. Assume Modigliani–Miller (1963) conditions with corporate taxes.")
    g = "FINC-C4-rudra"
    assert VU == 150 and VL == 165
    B.add(M("capital-structure-theories"), "L4", C4 + "\n\nThe value of the firm after the recapitalisation is:",
          L(VL, 0),
          [(L(ebit / ku, 0), "taxes ignored (MM without taxes)"),
           (L(VU, 0), "tax shield on debt ignored"),
           (L(VU + D, 0), "full amount of debt added instead of the tax shield t × D")],
          [f"VU = {ebit} × (1 − 0.25) ÷ 0.15 = ₹{VU:g} lakh", f"VL = VU + tD = {VU:g} + 0.25 × {D} = ₹{VL:g} lakh"],
          "VL = VU + tD", "Only the present value of the interest tax shield is added.", group=g, kind="case", ref=PAT)

    ke = ku + (ku - kd) * (1 - t) * D / E
    opts = [pct(x) for x in (ke, ku + (ku - kd) * D / E, ku + (ku - kd) * (1 - t) * D / VL, ku + (ku - kd) * (1 - t) * D / (VU - D))]
    chk = ((ebit - D * kd) * (1 - t)) / E
    assert abs(ke - chk) < 1e-12 and len(set(opts)) == 4
    B.add(M("capital-structure-theories"), "L4", C4 + "\n\nThe cost of equity after the recapitalisation is:",
          opts[0],
          [(opts[1], "(1 − t) factor omitted — MM no-tax formula"),
           (opts[2], "debt ÷ firm value used instead of debt ÷ equity"),
           (opts[3], "equity taken as VU − D, ignoring the tax-shield gain")],
          [f"E = VL − D = {VL:g} − {D} = ₹{E:g} lakh",
           f"KeL = 15% + (15% − 7%) × 0.75 × {D}/{E:g} = {opts[0]}",
           f"Check: net income = (30 − 4.2) × 0.75 = ₹{(ebit-D*kd)*(1-t):.2f} lakh; ÷ {E:g} = {pct(chk)}"],
          "KeL = Ku + (Ku − Kd)(1 − t)(D/E)", "Equity is VL − D, which already includes the tax shield.", group=g, kind="case", ref=PAT)

    bl = bu * (1 + (1 - t) * D / E)
    opts = [f2(x) for x in (bl, bu * (1 + D / E), bu * (1 + (1 - t) * D / VL), bu)]
    assert abs(rf + bl * (rm - rf) - ke) < 1e-12 and len(set(opts)) == 4
    B.add(M("capm-beta"), "L4", C4 + "\n\nThe equity beta after recapitalisation, consistent with CAPM and the cost of equity found above, is:",
          opts[0],
          [(opts[1], "(1 − t) omitted in relevering"),
           (opts[2], "debt ÷ firm value used instead of debt ÷ equity"),
           (opts[3], "beta assumed unchanged by financial leverage")],
          [f"βL = βU[1 + (1 − t)D/E] = 1.0 × [1 + 0.75 × {D}/{E:g}] = {opts[0]}",
           f"CAPM check: 7% + {bl:.4f} × 8% = {pct(rf+bl*(rm-rf))} = KeL"],
          "βL = βU[1 + (1 − t)D/E]", "With risk-free debt, Hamada's relevering matches MM's cost of equity.", group=g, kind="case", ref=PAT)
