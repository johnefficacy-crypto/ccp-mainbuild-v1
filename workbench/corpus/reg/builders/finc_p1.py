"""FIN-C part 1: cost of capital (7), WACC / MCC (5), CAPM (6) — non-case questions."""
import math
from finc_common import M, table, statements, stmt_opts, inr, R, pct, L, f2, PAT


def add_all(B):
    # ======================= Cost of capital (7) =======================
    m = M("cost-of-capital-debt-preference")
    B.add(m, "L1", "In computing the specific cost of each source of finance, the cost of debentures is taken net of tax while the cost of preference shares is not. The reason is that:",
          "Interest is a tax-deductible expense; preference dividend is an appropriation of profit",
          [("Preference dividend is cumulative, so it is already stated net of corporate tax", "confuses cumulative feature with tax treatment"),
           ("Debentures are secured, so the lender rather than the company bears the tax", "confuses security with tax incidence"),
           ("Preference capital is redeemable, so any tax paid is recovered on its redemption", "invents a tax recovery on redemption")],
          ["Debenture interest is charged against profit before tax, so each ₹1 of interest costs the company ₹(1 − t).",
           "Preference dividend is paid out of profit after tax, so there is no tax saving; Kp is used without (1 − t)."],
          "Kd = I(1 − t) ÷ NP;  Kp = PD ÷ NP", "Applying (1 − t) to preference dividend understates Kp.",
          kind="conceptual", ref=PAT)

    B.add(m, "L1", "A company finances part of its expansion from retained earnings. Ignoring shareholders' personal taxes, the cost of retained earnings is best taken as:",
          "Equal to the cost of equity, with no adjustment for flotation cost",
          [("Nil, since no dividend is contractually payable on retained profits", "treats retained earnings as cost-free"),
           ("Equal to the cost of equity after grossing up for flotation cost", "flotation cost applies only to a fresh issue"),
           ("Equal to the post-tax cost of debt, the cheapest source available", "confuses opportunity cost with cheapest source")],
          ["Retained earnings belong to equity shareholders; their opportunity cost is the return shareholders could earn elsewhere, i.e. Ke.",
           "No issue expenses are incurred on retained profits, so Kr = Ke without a flotation adjustment (Ke for a new issue is higher)."],
          "Kr = Ke = D1 ÷ P0 + g", "Retained earnings are not free; only the flotation cost is saved.",
          kind="conceptual", ref=PAT)

    cpn, mp, fl, t = 10, 94, 0.02, 0.25
    np_ = mp * (1 - fl)
    kd = cpn * (1 - t) / np_
    assert abs(np_ - 92.12) < 1e-9
    B.add(m, "L2", f"Vedant Textiles Ltd issues {cpn}% irredeemable debentures of face value ₹100 at the current market price of ₹{mp}. Flotation cost is {pct(fl,0)} of the issue price and the tax rate is {pct(t,0)}. The post-tax cost of these debentures is:",
          pct(kd),
          [(pct(cpn * (1 - t) / mp), "flotation cost ignored (market price used as net proceeds)"),
           (pct(cpn * (1 - t) / 100), "face value used as net proceeds"),
           (pct(cpn / np_), "pre-tax cost; tax shield on interest ignored")],
          [f"Net proceeds = {mp} × (1 − {fl}) = ₹{np_:.2f}",
           f"Post-tax interest = {cpn} × (1 − {t}) = ₹{cpn*(1-t):.2f}",
           f"Kd = {cpn*(1-t):.2f} ÷ {np_:.2f} = {pct(kd)}"],
          "Kd (irredeemable) = I(1 − t) ÷ NP", "Net proceeds, not face value, form the base.", ref=PAT)

    d0, g, p0, f = 6.0, 0.08, 120, 0.04
    d1 = d0 * (1 + g)
    ke_new = d1 / (p0 * (1 - f)) + g
    ke_re = d1 / p0 + g
    assert abs(ke_new - 0.13625) < 1e-9
    B.add(m, "L2", f"The equity shares of Sarthak Pharma Ltd trade at ₹{p0}. The dividend just paid is ₹{d0:.2f} per share and dividends are expected to grow at {pct(g,0)} a year indefinitely. A fresh issue will involve flotation cost of {pct(f,0)} of the market price. The cost of the new equity is:",
          pct(ke_new, 3),
          [(pct(ke_re, 3), "flotation cost ignored — this is the cost of retained earnings"),
           (pct(d0 / (p0 * (1 - f)) + g, 3), "D0 used instead of D1 = D0(1 + g)"),
           (pct(d0 / p0 + g, 3), "D0 used and flotation ignored")],
          [f"D1 = {d0:.2f} × {1+g} = ₹{d1:.2f}",
           f"Net proceeds = {p0} × (1 − {f}) = ₹{p0*(1-f):.2f}",
           f"Ke (new) = {d1:.2f} ÷ {p0*(1-f):.2f} + {pct(g,0)} = {pct(ke_new,3)}"],
          "Ke = D1 ÷ P0(1 − f) + g", "Gordon's model needs next year's dividend, not the one just paid.", ref=PAT)

    fv, cpn, disc, flo, prem, n, t = 1000, 0.11, 0.02, 0.03, 0.05, 8, 0.30
    NP = fv * (1 - disc - flo); RV = fv * (1 + prem); I = fv * cpn
    kd = (I * (1 - t) + (RV - NP) / n) / ((RV + NP) / 2)
    assert NP == 950 and RV == 1050 and abs(kd - 0.0895) < 1e-9
    tb = table(["Particulars", "Data"], [["Face value", R(fv)], ["Coupon", pct(cpn, 0)], ["Issue price", f"{pct(disc,0)} discount to face value"],
                                         ["Flotation cost", f"{pct(flo,0)} of face value"], ["Redemption", f"At {pct(prem,0)} premium after {n} years"], ["Tax rate", pct(t, 0)]])
    B.add(m, "L3", f"Kaveri Cables Ltd issues redeemable debentures on the following terms:\n\n{tb}\n\nUsing the approximation method, the post-tax cost of the debentures is:",
          pct(kd),
          [(pct((I * (1 - t) + (RV - NP) / n) / NP), "net proceeds used as the denominator instead of the average of RV and NP"),
           (pct((I * (1 - t) + (fv - NP) / n) / ((fv + NP) / 2)), "redemption premium ignored (redeemed at par)"),
           (pct((I + (RV - NP) / n) * (1 - t) / ((RV + NP) / 2)), "tax shield also applied to the amortised discount and premium")],
          [f"NP = {fv} − {pct(disc,0)} discount − {pct(flo,0)} flotation = ₹{NP:.0f}; RV = ₹{RV:.0f}",
           f"Annual post-tax interest = {I:.0f} × (1 − {t}) = ₹{I*(1-t):.0f}; amortisation = ({RV:.0f} − {NP:.0f}) ÷ {n} = ₹{(RV-NP)/n:.2f}",
           f"Kd = ({I*(1-t):.0f} + {(RV-NP)/n:.2f}) ÷ [({RV:.0f} + {NP:.0f}) ÷ 2] = {pct(kd)}"],
          "Kd = [I(1 − t) + (RV − NP)/n] ÷ [(RV + NP)/2]",
          "Both the issue discount and the flotation cost reduce NP; the premium raises RV.", ref=PAT)

    fv, rate, flo, prem, n, t = 100, 0.09, 0.03, 0.10, 10, 0.25
    NP, RV, PD = fv * (1 - flo), fv * (1 + prem), fv * rate
    kp = (PD + (RV - NP) / n) / ((RV + NP) / 2)
    B.add(m, "L3", f"Anvaya Chemicals Ltd issues {pct(rate,0)} preference shares of ₹{fv} each at par. Flotation cost is {pct(flo,0)} of the issue price and the shares are redeemable at a premium of {pct(prem,0)} after {n} years. The company's tax rate is {pct(t,0)}. The cost of preference capital is:",
          pct(kp),
          [(pct((PD + (RV - NP) / n) / NP), "net proceeds used as the denominator"),
           (pct((PD + (fv - NP) / n) / ((fv + NP) / 2)), "redemption premium ignored"),
           (pct((PD * (1 - t) + (RV - NP) / n) / ((RV + NP) / 2)), "tax shield wrongly applied to preference dividend")],
          [f"NP = {fv} × (1 − {flo}) = ₹{NP:.0f}; RV = ₹{RV:.0f}; PD = ₹{PD:.0f}",
           f"Kp = ({PD:.0f} + ({RV:.0f} − {NP:.0f}) ÷ {n}) ÷ [({RV:.0f} + {NP:.0f}) ÷ 2] = {PD+(RV-NP)/n:.2f} ÷ {(RV+NP)/2:.1f} = {pct(kp)}",
           "The tax rate is irrelevant: preference dividend is not tax-deductible."],
          "Kp = [PD + (RV − NP)/n] ÷ [(RV + NP)/2]", "The tax rate in the stem is a lure.", ref=PAT)

    eps, b, roe, p0 = 20, 0.60, 0.15, 150
    g = b * roe; d0 = eps * (1 - b); d1 = d0 * (1 + g)
    ke = d1 / p0 + g
    g_w = (1 - b) * roe
    assert abs(g - 0.09) < 1e-12 and abs(d1 - 8.72) < 1e-9
    B.add(m, "L3", f"Nirmal Agro Ltd has just reported EPS of ₹{eps}. It retains {pct(b,0)} of earnings and earns a return of {pct(roe,0)} on equity, which is expected to continue. The share trades at ₹{p0}. Using the dividend growth model with g = b × r, the cost of equity is:",
          pct(ke),
          [(pct(d0 / p0 + g), "D0 used instead of D1"),
           (pct(eps * b * (1 + g) / p0 + g), "retained portion taken as the dividend (retention confused with payout)"),
           (pct(d0 * (1 + g_w) / p0 + g_w), "growth computed as payout × r instead of retention × r")],
          [f"g = b × r = {b} × {roe} = {pct(g)}",
           f"D0 = {eps} × (1 − {b}) = ₹{d0:.2f}; D1 = {d0:.2f} × {1+g:.2f} = ₹{d1:.2f}",
           f"Ke = {d1:.2f} ÷ {p0} + {pct(g)} = {pct(ke)}"],
          "g = b × r;  Ke = D1 ÷ P0 + g", "Growth comes from the retained portion; the dividend is the paid-out portion.", ref=PAT)

    # ======================= WACC / MCC (5) =======================
    m = M("weighted-average-and-marginal")
    B.add(m, "L1", "A firm plans to raise new capital in a fixed target mix. In constructing its marginal cost of capital schedule, a break point occurs at a total new financing equal to:",
          "The amount of the cheaper tranche of a source ÷ that source's weight",
          [("The amount of the cheaper tranche of a source × that source's weight", "multiplies by the weight instead of dividing"),
           ("The amount of the cheaper tranche of a source ÷ the firm's current WACC", "divides by WACC instead of the weight"),
           ("The total new capital required ÷ the weight of the costliest source", "uses total requirement, not the tranche limit")],
          ["When a source's cheaper tranche is exhausted, its component cost rises, and so does WACC.",
           "Because that source provides only its weight w of every rupee raised, the tranche lasts until total financing = Tranche ÷ w."],
          "Break point = Limit of cheaper funds ÷ Weight of that source", "Dividing by the weight grosses the tranche up to total capital.",
          kind="conceptual", ref=PAT)

    w = [("Equity", 0.60, 0.16), ("Preference", 0.10, 0.11), ("Debt (pre-tax)", 0.30, 0.12)]
    t = 0.30
    wacc = 0.60 * 0.16 + 0.10 * 0.11 + 0.30 * 0.12 * (1 - t)
    assert abs(wacc - 0.1322) < 1e-12
    tb = table(["Source", "Target weight", "Cost"], [[s, pct(a, 0), pct(c, 0)] for s, a, c in w])
    B.add(m, "L2", f"Ishaan Motors Ltd uses the following target capital structure. Its tax rate is {pct(t,0)}.\n\n{tb}\n\nThe weighted average cost of capital is:",
          pct(wacc),
          [(pct(0.096 + 0.011 + 0.036), "pre-tax cost of debt used"),
           (pct(0.096 + 0.011 * (1 - t) + 0.30 * 0.12 * (1 - t)), "tax shield also applied to preference dividend"),
           (pct((0.16 + 0.11 + 0.12 * (1 - t)) / 3), "simple average of component costs; weights ignored")],
          ["Post-tax Kd = 12% × (1 − 0.30) = 8.40%",
           "WACC = 0.60 × 16% + 0.10 × 11% + 0.30 × 8.40% = 9.60% + 1.10% + 2.52%",
           f"= {pct(wacc)}"],
          "WACC = Σ wᵢ kᵢ with Kd post-tax", "Only debt gets the tax shield.", ref=PAT)

    sh, par, mpx, res, deb, dmp, ke, kd = 5, 10, 36, 20, 30, 105, 0.15, 0.084  # lakh shares / ₹ lakh
    E_b, E_m, D_m = sh * par + res, sh * mpx, deb * dmp / 100
    bw = (E_b * ke + deb * kd) / (E_b + deb)
    mw = (E_m * ke + D_m * kd) / (E_m + D_m)
    mw_res = ((E_m + res) * ke + D_m * kd) / (E_m + res + D_m)
    mw_dbook = (E_m * ke + deb * kd) / (E_m + deb)
    assert len({round(x, 4) for x in (bw, mw, mw_res, mw_dbook)}) == 4
    tb = table(["Source", "Book value (₹ lakh)", "Market data", "Cost"],
               [["Equity shares (₹10 each)", sh * par, f"{sh} lakh shares at ₹{mpx}", pct(ke, 0)],
                ["Retained earnings", res, "—", pct(ke, 0)],
                ["12% debentures", deb, f"₹{dmp} per ₹100", pct(kd) + " (post-tax)"]])
    B.add(m, "L2", f"Extract from the books of Tarang Electricals Ltd:\n\n{tb}\n\nThe weighted average cost of capital using market-value weights is:",
          pct(mw),
          [(pct(bw), "book-value weights used"),
           (pct(mw_res), "retained earnings added again to the market value of equity"),
           (pct(mw_dbook), "debentures taken at book value while equity is at market value")],
          [f"Market value of equity = {sh} lakh × ₹{mpx} = ₹{E_m:.0f} lakh (this already includes retained earnings)",
           f"Market value of debentures = {deb} × {dmp}/100 = ₹{D_m:.1f} lakh",
           f"WACC = ({E_m:.0f} × 15% + {D_m:.1f} × 8.4%) ÷ {E_m+D_m:.1f} = {pct(mw)}"],
          "Market WACC = (E_m·Ke + D_m·Kd) ÷ (E_m + D_m)", "Retained earnings are part of equity's market value; do not add them twice.", ref=PAT)

    w_d, w_e = 0.40, 0.60
    re_lim, ke_re, ke_new = 18, 0.15, 0.17
    d_lim, kd1, kd2 = 10, 0.07, 0.084
    bp_re, bp_d = re_lim / w_e, d_lim / w_d
    raise_ = 28
    assert bp_d == 25 and bp_re == 30
    def mcc(x):
        k_d = kd1 if x <= bp_d else kd2
        k_e = ke_re if x <= bp_re else ke_new
        return w_d * k_d + w_e * k_e
    marg = mcc(raise_)
    avg = (bp_d * mcc(1) + (raise_ - bp_d) * marg) / raise_
    B.add(m, "L3", f"Ojas Ceramics Ltd raises new funds in the ratio debt 40 : equity 60. Retained earnings of ₹{re_lim} lakh are available at a cost of {pct(ke_re,0)}; beyond that, new equity costs {pct(ke_new,0)}. The first ₹{d_lim} lakh of debt costs {pct(kd1,0)} post-tax and further debt costs {pct(kd2,1)} post-tax. If the company raises ₹{raise_} lakh in total, the marginal cost of capital on the last rupee raised is:",
          pct(marg),
          [(pct(mcc(1)), "break points ignored; cheapest component costs used throughout"),
           (pct(w_d * kd2 + w_e * ke_new), "tranche limits taken as break points without dividing by weights"),
           (pct(avg), "average cost over the whole ₹28 lakh instead of the marginal cost")],
          [f"Break point (debt) = {d_lim} ÷ {w_d} = ₹{bp_d:.0f} lakh; break point (retained earnings) = {re_lim} ÷ {w_e} = ₹{bp_re:.0f} lakh",
           f"At ₹{raise_} lakh: debt is in the costlier tranche ({pct(kd2,1)}), equity still from retained earnings ({pct(ke_re,0)})",
           f"MCC = 0.40 × {pct(kd2,1)} + 0.60 × {pct(ke_re,0)} = {pct(marg)}"],
          "Break point = Tranche ÷ Weight; MCC = Σ w × marginal component cost",
          "₹28 lakh lies between the ₹25 lakh and ₹30 lakh break points.", ref=PAT)

    n_sh, p0, d1, g = 10, 50, 4, 0.06  # lakh shares
    pref, pmp, deb, dmp, t = 20, 95, 40, 96, 0.25
    ke = d1 / p0 + g; kp = 10 / pmp; kd = 12 * (1 - t) / dmp; kd_pre = 12 / dmp
    E, P, D = n_sh * p0, pref * pmp / 100, deb * dmp / 100
    wm = (E * ke + P * kp + D * kd) / (E + P + D)
    wb = (n_sh * 10 * ke + pref * kp + deb * kd) / (n_sh * 10 + pref + deb)
    w_pre = (E * ke + P * kp + D * kd_pre) / (E + P + D)
    ke_bad = d1 * (1 + g) / p0 + g
    w_ke = (E * ke_bad + P * kp + D * kd) / (E + P + D)
    assert abs(ke - 0.14) < 1e-12
    tb = table(["Source", "Book value (₹ lakh)", "Market price"],
               [["Equity shares of ₹10 each", n_sh * 10, f"₹{p0} per share"],
                ["10% irredeemable preference shares", pref, f"₹{pmp} per ₹100"],
                ["12% irredeemable debentures", deb, f"₹{dmp} per ₹100"]])
    B.add(m, "L3", f"Capital of Lohit Paper Ltd:\n\n{tb}\n\nThe next dividend expected on equity is ₹{d1} per share, growing at {pct(g,0)} a year. The tax rate is {pct(t,0)}. Using market-value weights and market prices for component costs, WACC is:",
          pct(wm),
          [(pct(wb), "book-value weights used"),
           (pct(w_pre), "pre-tax cost of debentures used"),
           (pct(w_ke), "₹4 treated as D0 and grown again")],
          [f"Ke = {d1}/{p0} + 6% = {pct(ke)}; Kp = 10/{pmp} = {pct(kp)}; Kd = 12 × 0.75/{dmp} = {pct(kd)}",
           f"Market values: E = ₹{E:.0f} lakh, P = ₹{P:.0f} lakh, D = ₹{D:.1f} lakh; total ₹{E+P+D:.1f} lakh",
           f"WACC = ({E:.0f} × {pct(ke)} + {P:.0f} × {pct(kp)} + {D:.1f} × {pct(kd)}) ÷ {E+P+D:.1f} = {pct(wm)}"],
          "WACC = Σ (MVᵢ × kᵢ) ÷ Σ MVᵢ", "The stated dividend is already D1.", ref=PAT)

    # ======================= CAPM (6) =======================
    m = M("capm-beta")
    B.add(m, "L1", "In the Capital Asset Pricing Model, the beta of a security measures:",
          "Its systematic risk — sensitivity of its return to market returns",
          [("Its total risk — the standard deviation of its own returns", "total risk, not systematic risk"),
           ("Its unsystematic risk — variation specific to the company", "diversifiable risk is not priced in CAPM"),
           ("Its excess return over that predicted by the market model", "that is alpha, not beta")],
          ["β = Cov(Ri, Rm) ÷ Var(Rm): the co-movement of the security with the market.",
           "Only this non-diversifiable (systematic) risk earns a premium in CAPM."],
          "β = Cov(i, m) ÷ σm²", "Beta is not total risk; a stock can be volatile yet have a low beta.",
          kind="conceptual", ref=PAT)

    st = ["The security market line relates expected return to beta and applies to individual securities as well as portfolios.",
          "The capital market line relates expected return to standard deviation and applies only to efficient portfolios.",
          "A security whose expected return plots above the security market line is overvalued."]
    c, w = stmt_opts([True, True, False],
                     ["SML uses beta and holds for every asset", "CML uses σ and holds only for efficient portfolios",
                      "above the SML the security offers more than its required return, i.e. it is undervalued"])
    B.add(m, "L1", "Consider the following statements:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w,
          ["SML: E(R) = Rf + β(Rm − Rf) — valid for any security or portfolio.",
           "CML: E(Rp) = Rf + [(Rm − Rf)/σm]σp — valid only for efficient (fully diversified) portfolios.",
           "Above the SML → expected return > required return → price too low → undervalued (positive alpha)."],
          "SML vs CML", "Above SML means undervalued, not overvalued.", kind="statement", ref=PAT)

    cov, sm, si, rf, rm = 0.0216, 0.15, 0.20, 0.07, 0.125
    beta = cov / sm ** 2; rho = cov / (si * sm)
    k = rf + beta * (rm - rf)
    assert abs(beta - 0.96) < 1e-12 and abs(rho - 0.72) < 1e-12
    B.add(m, "L2", f"The covariance between the returns of Pranav Steel Ltd and the market index is {cov}. The standard deviation of the market return is {pct(sm,0)} and that of Pranav Steel is {pct(si,0)}. The risk-free rate is {pct(rf,0)} and the expected market return is {pct(rm,1)}. The required return on Pranav Steel is:",
          pct(k),
          [(pct(rf + rho * (rm - rf)), "correlation coefficient used as beta"),
           (pct(beta * rm), "β × Rm; risk-free rate ignored"),
           (pct(rf + si / sm * (rm - rf)), "ratio of standard deviations used as beta, ignoring correlation")],
          [f"β = Cov ÷ σm² = {cov} ÷ {sm**2:.4f} = {beta:.2f}",
           f"Required return = {pct(rf,0)} + {beta:.2f} × ({pct(rm,1)} − {pct(rf,0)}) = {pct(k)}"],
          "β = Cov(i,m)/σm²;  k = Rf + β(Rm − Rf)", "Divide the covariance by market variance, not by σm or σi·σm.", ref=PAT)

    port = [("A", 2000, 200, 1.4), ("B", 5000, 70, 0.8), ("C", 1000, 250, 1.1)]
    rf, rm = 0.06, 0.12
    val = sum(n * p for _, n, p, _ in port)
    bp = sum(n * p * b for _, n, p, b in port) / val
    b_simple = sum(b for *_, b in port) / 3
    b_count = sum(n * b for _, n, _, b in port) / sum(n for _, n, _, _ in port)
    ret = lambda b: rf + b * (rm - rf)
    assert abs(bp - 1.115) < 1e-12
    tb = table(["Stock", "Shares held", "Price (₹)", "Beta"], [[s, inr(n), p, b] for s, n, p, b in port])
    B.add(m, "L2", f"An investor holds the following portfolio:\n\n{tb}\n\nThe risk-free rate is {pct(rf,0)} and the market return {pct(rm,0)}. The required return on the portfolio under CAPM is:",
          pct(ret(bp)),
          [(pct(ret(b_simple)), "simple average of betas"),
           (pct(ret(b_count)), "betas weighted by number of shares instead of market value"),
           (pct(bp * rm), "portfolio beta × Rm; risk-free rate ignored")],
          [f"Market values: A ₹{inr(400000)}, B ₹{inr(350000)}, C ₹{inr(250000)}; total ₹{inr(val)}",
           f"βp = (0.40 × 1.4) + (0.35 × 0.8) + (0.25 × 1.1) = {bp:.3f}",
           f"Required return = 6% + {bp:.3f} × 6% = {pct(ret(bp))}"],
          "βp = Σ wᵢβᵢ (value weights)", "Weights are market values, not share counts.", ref=PAT)

    rf, rm = 0.06, 0.13
    stocks = [("P", 1.2, 0.150), ("Q", 0.8, 0.112), ("R", 1.5, 0.160), ("S", 0.6, 0.108)]
    req = {s: rf + b * (rm - rf) for s, b, _ in stocks}
    alpha = {s: e - req[s] for s, _, e in stocks}
    under = [s for s in alpha if alpha[s] > 0]
    over = [s for s in alpha if alpha[s] < 0]
    norf = [s for s, b, e in stocks if e > b * rm]
    top2 = sorted([s for s, _, _ in stocks], key=lambda s: -dict((x, e) for x, _, e in stocks)[s])[:2]
    J = lambda xs: " and ".join(sorted(xs))
    assert J(under) == "P and S" and len({J(under), J(over), J(norf), J(top2)}) == 4
    tb = table(["Stock", "Beta", "Analyst's expected return"], [[s, b, pct(e, 1)] for s, b, e in stocks])
    B.add(m, "L3", f"The risk-free rate is {pct(rf,0)} and the expected market return {pct(rm,0)}.\n\n{tb}\n\nOn the basis of the security market line, which stocks are undervalued?",
          J(under),
          [(J(over), "sign of alpha reversed — these plot below the SML"),
           (J(norf), "expected return compared with β × Rm, ignoring the risk-free rate"),
           (J(top2), "highest expected returns taken as undervalued without adjusting for beta")],
          ["Required return = 6% + β × 7%: " + "; ".join(f"{s} = {pct(req[s],1)}" for s in req),
           "Alpha = expected − required: " + "; ".join(f"{s} = {alpha[s]*100:+.1f}%" for s in alpha),
           f"Positive alpha (above SML) → undervalued: {J(under)}"],
          "α = E(R) − [Rf + β(Rm − Rf)]", "A high expected return is not a bargain if beta is higher still.", ref=PAT)

    rmk = [10, 6, -2, 14, 12]; rst = [15, 4, 1, 18, 9]
    n = len(rmk); mm, ms = sum(rmk) / n, sum(rst) / n
    cov = sum((a - mm) * (b - ms) for a, b in zip(rmk, rst)) / n
    vm = sum((a - mm) ** 2 for a in rmk) / n; vs = sum((b - ms) ** 2 for b in rst) / n
    beta = cov / vm; rho = cov / math.sqrt(vm * vs); rsd = math.sqrt(vs / vm); rev = cov / vs
    opts = [f2(x) for x in (beta, rho, rsd, rev)]
    assert len(set(opts)) == 4
    tb = table(["Year", "Market return (%)", "Return on Hemant Ltd (%)"], [[i + 1, a, b] for i, (a, b) in enumerate(zip(rmk, rst))])
    B.add(m, "L3", f"Returns over five years:\n\n{tb}\n\nThe beta of Hemant Ltd, estimated from these data, is closest to:",
          f2(beta),
          [(f2(rho), "correlation coefficient reported as beta"),
           (f2(rsd), "ratio of standard deviations (σi/σm), ignoring correlation"),
           (f2(rev), "covariance divided by the variance of the stock instead of the market")],
          [f"Mean market return = {mm:.1f}%; mean stock return = {ms:.1f}%",
           f"Cov(i,m) = Σ(dm × di) ÷ {n} = {cov:.2f}; Var(m) = Σdm² ÷ {n} = {vm:.2f}",
           f"β = {cov:.2f} ÷ {vm:.2f} = {beta:.2f}"],
          "β = Cov(i,m) ÷ Var(m)", "Whether n or n − 1 is used cancels out in the ratio.", ref=PAT)
