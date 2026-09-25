"""FIN-C part 2: capital budgeting — payback (4), NPV/IRR/PI/MIRR (6), NPV vs IRR & rationing (6),
risk (6) — non-case questions."""
import math
from itertools import combinations
from finc_common import M, table, statements, stmt_opts, inr, R, pct, L, f2, yrs, pvf, pvaf, irr, PAT


def add_all(B):
    # ======================= Payback (4) =======================
    m = M("payback-and-discounted")
    st = ["The simple payback period ignores the time value of money.",
          "For a conventional project with a positive discount rate, the discounted payback period is longer than the simple payback period.",
          "The discounted payback period, unlike the simple payback period, takes into account cash flows arising after the payback year."]
    c, w = stmt_opts([True, True, False],
                     ["payback adds undiscounted flows", "discounted flows are smaller, so recovery takes longer",
                      "both methods ignore post-payback cash flows"])
    B.add(m, "L1", "Consider the following statements about payback methods:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w,
          ["Simple payback accumulates undiscounted cash flows → no time value.",
           "Each discounted inflow is smaller than its undiscounted value, so cumulative recovery is slower.",
           "Both methods stop at the recovery point; later cash flows are ignored — the key weakness shared by both."],
          "Payback = years to recover outlay", "Discounting fixes time value, not the post-payback blind spot.",
          kind="statement", ref=PAT)

    out, cfs = 12, [3, 4, 3.5, 3, 2.5]
    cum, yr = 0, 0
    while cum + cfs[yr] < out:
        cum += cfs[yr]; yr += 1
    pb = yr + (out - cum) / cfs[yr]
    assert abs(pb - 3.5) < 1e-12
    tb = table(["Year", "1", "2", "3", "4", "5"], [["Cash inflow (₹ lakh)"] + cfs])
    B.add(m, "L2", f"A project costing ₹{out} lakh is expected to generate:\n\n{tb}\n\nIts payback period is:",
          yrs(pb),
          [(yrs(out / (sum(cfs) / len(cfs))), "outlay divided by average annual inflow"),
           (yrs(yr + (out - cum) / cfs[yr - 1]), "balance divided by the previous year's inflow"),
           (yrs(yr + 1), "whole years only; no interpolation")],
          [f"Cumulative inflows: {', '.join(f'{sum(cfs[:i+1]):g}' for i in range(len(cfs)))}",
           f"After {yr} years ₹{cum:g} lakh is recovered; balance ₹{out-cum:g} lakh",
           f"Payback = {yr} + {out-cum:g}/{cfs[yr]:g} = {pb:.2f} years"],
          "Payback = Years before recovery + Unrecovered balance ÷ Inflow of recovery year",
          "Averaging uneven flows misstates payback.", ref=PAT)

    cost, life, ebdt, t = 10, 5, 3.6, 0.30
    dep = cost / life
    cfat = (ebdt - dep) * (1 - t) + dep
    pb = cost / cfat
    B.add(m, "L2", f"A machine costing ₹{cost} lakh has a life of {life} years with no salvage and is depreciated on a straight-line basis. It will add ₹{ebdt} lakh a year to earnings before depreciation and tax. The tax rate is {pct(t,0)}. The payback period on cash flow after tax is:",
          yrs(pb),
          [(yrs(cost / ebdt), "pre-tax cash flow used"),
           (yrs(cost / (ebdt * (1 - t))), "tax charged on earnings before depreciation; tax shield ignored"),
           (yrs(cost / ((ebdt - dep) * (1 - t))), "profit after tax used; depreciation not added back")],
          [f"Depreciation = {cost}/{life} = ₹{dep:g} lakh",
           f"CFAT = ({ebdt} − {dep:g}) × (1 − {t}) + {dep:g} = ₹{cfat:.2f} lakh",
           f"Payback = {cost} ÷ {cfat:.2f} = {pb:.2f} years"],
          "CFAT = (EBDT − Dep)(1 − t) + Dep", "Depreciation is non-cash but saves tax.", ref=PAT)

    out, cfs, k = 8, [2.5, 3, 3.5, 2], 0.10
    f = [pvf(k, i + 1) for i in range(4)]
    pv = [c * x for c, x in zip(cfs, f)]
    cum = 0; yr = 0
    while cum + pv[yr] < out:
        cum += pv[yr]; yr += 1
    dpb = yr + (out - cum) / pv[yr]
    cu = 0; y2 = 0
    while cu + cfs[y2] < out:
        cu += cfs[y2]; y2 += 1
    spb = y2 + (out - cu) / cfs[y2]
    wrong_interp = yr + (out - cum) / cfs[yr]
    assert yr == 3
    tb = table(["Year", "1", "2", "3", "4"], [["Cash inflow (₹ lakh)"] + cfs, ["PV factor at 10%"] + f])
    B.add(m, "L3", f"A project requires an outlay of ₹{out} lakh.\n\n{tb}\n\nIts discounted payback period is:",
          yrs(dpb),
          [(yrs(spb), "simple (undiscounted) payback"),
           (yrs(wrong_interp), "fraction of final year computed on the undiscounted inflow"),
           (yrs(yr + 1), "whole years only; no interpolation")],
          [f"PVs: {', '.join(f'{x:.4f}' for x in pv)}",
           f"Cumulative PV after {yr} years = {cum:.4f}; balance = {out-cum:.4f}",
           f"Discounted payback = {yr} + {out-cum:.4f}/{pv[yr]:.4f} = {dpb:.2f} years"],
          "DPB = Years before recovery + Unrecovered PV ÷ PV of recovery-year inflow",
          "Interpolate on the discounted inflow of the recovery year.", ref=PAT)

    # ======================= NPV / IRR / PI / MIRR (6) =======================
    m = M("npv-irr-pi-and-mirr")
    B.add(m, "L1", "The modified internal rate of return (MIRR) differs from the conventional IRR chiefly because MIRR assumes that intermediate cash inflows are reinvested at:",
          "The firm's cost of capital (or a specified reinvestment rate)",
          [("The project's own IRR, as in the conventional method", "that is the IRR reinvestment assumption"),
           ("The risk-free rate, so that reinvestment risk is removed", "not the standard MIRR assumption"),
           ("A zero rate, so that only nominal inflows are summed", "confuses MIRR with undiscounted payback logic")],
          ["MIRR compounds inflows to a terminal value at the cost of capital (or a stated rate).",
           "It then finds the rate equating PV of outflows with that terminal value — giving a single, realistic rate."],
          "MIRR = (TV of inflows at k ÷ PV of outflows)^(1/n) − 1", "IRR implicitly assumes reinvestment at the IRR itself.",
          kind="conceptual", ref=PAT)

    out, cfs, k = 20, [6, 7, 8, 5], 0.12
    f = [pvf(k, i + 1) for i in range(4)]
    npv = sum(c * x for c, x in zip(cfs, f)) - out
    avg_npv = sum(cfs) / 4 * pvaf(k, 4) - out
    early = cfs[0] + sum(c * x for c, x in zip(cfs[1:], f[:3])) - out
    assert npv < 0 < early
    tb = table(["Year", "1", "2", "3", "4"], [["Cash inflow (₹ lakh)"] + cfs, ["PV factor at 12%"] + f])
    B.add(m, "L2", f"Suryoday Packaging Ltd evaluates a project costing ₹{out} lakh.\n\n{tb}\n\nThe NPV of the project is:",
          R(round(npv * 1e5)),
          [(R(round(avg_npv * 1e5)), "average inflow multiplied by the 4-year annuity factor"),
           (R(round(early * 1e5)), "year-1 inflow left undiscounted; factors shifted one year"),
           (R(round(-npv * 1e5)), "sign reversed (outlay minus PV of inflows)")],
          [f"PV of inflows = {' + '.join(f'{c}×{x}' for c, x in zip(cfs, f))} = ₹{npv+out:.3f} lakh",
           f"NPV = {npv+out:.3f} − {out} = {L(npv, 3)} = {R(round(npv*1e5))}"],
          "NPV = Σ CFt × PVFt − Outlay", "Undiscounted inflows (₹26 lakh) comfortably exceed cost, but the NPV is negative.", ref=PAT)

    lo, hi, n_lo, n_hi = 0.14, 0.18, 12400, -8600
    ir = lo + n_lo / (n_lo - n_hi) * (hi - lo)
    assert abs(ir - (0.14 + 0.04 * 12400 / 21000)) < 1e-12
    B.add(m, "L2", f"A project's NPV is ₹{inr(n_lo)} at a discount rate of {pct(lo,0)} and −₹{inr(-n_hi)} at {pct(hi,0)}. By linear interpolation, its IRR is:",
          pct(ir),
          [(pct(lo + (-n_hi) / (n_lo - n_hi) * (hi - lo)), "NPV at the higher rate placed in the numerator"),
           (pct(lo + n_lo / (n_lo - n_hi) / 100), "fraction added as percentage points without multiplying by the 4% rate gap"),
           (pct(lo + (hi - lo) * (-n_hi) / n_lo), "ratio of the two NPVs used as the fraction")],
          [f"Total NPV swing = {inr(n_lo)} + {inr(-n_hi)} = {inr(n_lo-n_hi)}",
           f"IRR = 14% + ({inr(n_lo)} ÷ {inr(n_lo-n_hi)}) × 4% = {pct(ir)}"],
          "IRR = L + [NPV_L ÷ (NPV_L − NPV_H)] × (H − L)", "The NPV at the lower rate drives the fraction.", ref=PAT)

    cost, wc, life, sal, ebdt, t, k = 30, 4, 5, 3, 10, 0.30, 0.12
    dep = (cost - sal) / life
    cfat = (ebdt - dep) * (1 - t) + dep
    A, f5 = pvaf(k, 5), pvf(k, 5)
    npv = cfat * A + (sal + wc) * f5 - (cost + wc)
    npv_nowc = cfat * A + sal * f5 - cost
    npv_wcnorel = cfat * A + sal * f5 - (cost + wc)
    dep2 = cost / life
    npv_fulldep = ((ebdt - dep2) * (1 - t) + dep2) * A + (sal + wc) * f5 - (cost + wc)
    assert abs(cfat - 8.62) < 1e-9
    tb = table(["Particulars", "Data"], [["Cost of plant", L(cost)], ["Working capital (year 0, released year 5)", L(wc)],
                                         ["Life / estimated and actual salvage", f"{life} years / {L(sal)}"],
                                         ["Depreciation", "Straight-line on (cost − salvage)"],
                                         ["Annual earnings before depreciation and tax", L(ebdt)], ["Tax rate", pct(t, 0)],
                                         ["Cost of capital; PVAF(12%, 5); PVF(12%, yr 5)", f"{pct(k,0)}; {A}; {f5}"]])
    B.add(m, "L3", f"Dhruv Castings Ltd is appraising a new plant:\n\n{tb}\n\nThe NPV of the project is:",
          L(npv),
          [(L(npv_nowc), "working capital omitted from both the outlay and the terminal inflow"),
           (L(npv_wcnorel), "working capital invested but its release in year 5 omitted"),
           (L(npv_fulldep), "depreciation charged on full cost although salvage is recovered")],
          [f"Depreciation = ({cost} − {sal})/{life} = ₹{dep} lakh; CFAT = ({ebdt} − {dep}) × 0.7 + {dep} = ₹{cfat:.2f} lakh",
           f"PV of CFAT = {cfat:.2f} × {A} = ₹{cfat*A:.3f} lakh",
           f"Terminal inflow = salvage {sal} (equals book value, no tax) + WC {wc} = ₹{sal+wc} lakh; PV = ₹{(sal+wc)*f5:.3f} lakh",
           f"NPV = {cfat*A:.3f} + {(sal+wc)*f5:.3f} − {cost+wc} = ₹{npv:.3f} lakh"],
          "NPV = PV(CFAT) + PV(salvage + WC) − (Cost + WC)", "Working capital is an outflow at the start and an inflow at the end.", ref=PAT)

    cost, life, ebdt4, sale, wc, t = 20, 4, 7, 2.5, 1.5, 0.30
    dep = cost / life
    op = (ebdt4 - dep) * (1 - t) + dep
    net_sale = sale - t * (sale - 0)
    tcf = op + net_sale + wc
    assert abs(tcf - 9.65) < 1e-9
    B.add(m, "L3", f"A machine costing ₹{cost} lakh is fully depreciated on a straight-line basis over {life} years (nil book value at the end). In year {life}, it generates earnings before depreciation and tax of ₹{ebdt4} lakh, is sold for ₹{sale} lakh, and working capital of ₹{wc} lakh is released. Tax is {pct(t,0)}, and any profit on sale of the asset is taxed at the same rate. The total cash flow in year {life} is:",
          L(tcf),
          [(L(op + sale + wc), "sale proceeds taken gross; tax on profit on sale ignored"),
           (L(op + net_sale), "release of working capital omitted"),
           (L(op + net_sale + wc * (1 - t)), "tax wrongly charged on the working capital released")],
          [f"Operating CFAT = ({ebdt4} − {dep:g}) × 0.7 + {dep:g} = ₹{op:.2f} lakh",
           f"Profit on sale = {sale} − 0 (book value) = ₹{sale}; tax = ₹{t*sale:.2f}; net salvage = ₹{net_sale:.2f} lakh",
           f"Year-{life} cash flow = {op:.2f} + {net_sale:.2f} + {wc} = ₹{tcf:.2f} lakh"],
          "Terminal CF = Operating CFAT + Salvage − Tax on (Salvage − BV) + WC released",
          "Release of working capital is not taxable.", ref=PAT)

    out, cfs, k = 10, [4, 5, 4], 0.10
    tv = sum(c * (1 + k) ** (3 - i - 1) for i, c in enumerate(cfs))
    mirr = (tv / out) ** (1 / 3) - 1
    tv2 = tv * (1 + k)
    irr_ = irr([-out] + cfs)
    opts = [pct(x) for x in (mirr, (tv2 / out) ** (1 / 3) - 1, irr_, (tv / out - 1) / 3)]
    assert abs(tv - 14.34) < 1e-9 and len(set(opts)) == 4
    B.add(m, "L3", f"A project costs ₹{out} lakh and yields ₹{cfs[0]} lakh, ₹{cfs[1]} lakh and ₹{cfs[2]} lakh at the end of years 1, 2 and 3. The cost of capital is {pct(k,0)}. The project's MIRR is:",
          opts[0],
          [(opts[1], "every inflow compounded one year too many (terminal value × 1.10)"),
           (opts[2], "conventional IRR (reinvestment at IRR) reported"),
           (opts[3], "simple average return on terminal value; no compounding")],
          [f"Terminal value at 10% = 4 × 1.21 + 5 × 1.10 + 4 = ₹{tv:.2f} lakh",
           f"MIRR = ({tv:.2f} ÷ {out})^(1/3) − 1 = {opts[0]}",
           f"Compare IRR = {opts[2]}: MIRR is lower because inflows earn only 10% on reinvestment."],
          "MIRR = (TV ÷ PV of outlay)^(1/n) − 1", "The final inflow is not compounded.", ref=PAT)

    # ======================= NPV vs IRR conflict & rationing (6) =======================
    m = M("npv-vs-irr-conflict")
    B.add(m, "L1", "When NPV and IRR rank two mutually exclusive projects differently, the NPV ranking is generally preferred because NPV:",
          "Measures absolute wealth added, assuming reinvestment at the cost of capital",
          [("Is always numerically higher than the IRR computed for the same project", "compares a ₹ amount with a %"),
           ("Is the only method that properly recognises the time value of money", "IRR also discounts cash flows"),
           ("Can be computed for uneven cash flows, whereas the IRR cannot be computed", "IRR can be computed for uneven flows")],
          ["NPV measures the ₹ increase in shareholder wealth — the objective of the firm.",
           "Its implicit reinvestment rate (cost of capital) is more realistic than the IRR's own-rate assumption."],
          "Mutually exclusive → choose higher NPV", "IRR is a relative measure and ignores scale.",
          kind="conceptual", ref=PAT)

    A_, B_ = [-20, 4, 24], [-20, 16, 9]
    diff = [a - b for a, b in zip(A_, B_)]
    fisher = diff[2] / -diff[1] - 1
    ia, ib = irr(A_), irr(B_)
    assert abs(fisher - 0.25) < 1e-12
    opts = [pct(fisher), pct((ia + ib) / 2), pct(max(ia, ib)), pct(min(ia, ib))]
    assert len(set(opts)) == 4
    tb = table(["Year", "0", "1", "2"], [["Project A (₹ lakh)"] + A_, ["Project B (₹ lakh)"] + B_])
    B.add(m, "L2", f"Two mutually exclusive projects have the following cash flows:\n\n{tb}\n\nThe crossover (Fisher's) rate at which both projects have the same NPV is:",
          opts[0],
          [(opts[1], "simple average of the two IRRs"),
           (opts[2], "IRR of the higher-IRR project taken as the crossover rate"),
           (opts[3], "IRR of the lower-IRR project taken as the crossover rate")],
          [f"Incremental flows (A − B): year 1 = {diff[1]}, year 2 = +{diff[2]}",
           f"Set {diff[1]}/(1 + r) + {diff[2]}/(1 + r)² = 0 → 1 + r = {diff[2]}/{-diff[1]} → r = {opts[0]}",
           f"For reference: IRR(A) = {pct(ia)}, IRR(B) = {pct(ib)}."],
          "Crossover rate = IRR of incremental cash flows", "The Fisher rate is not derived from the two IRRs.", ref=PAT)

    budget = 50
    pr = [("P", 20, 6.0), ("Q", 15, 6.0), ("R", 25, 7.0), ("S", 10, 2.5)]
    def greedy(key):
        left, tot = budget, 0
        for n, o, v in sorted(pr, key=key):
            take = min(1, left / o); tot += take * v; left -= take * o
            if left <= 0: break
        return tot
    by_pi = greedy(lambda x: -x[2] / x[1]); by_npv = greedy(lambda x: -x[2]); by_out = greedy(lambda x: x[1])
    best_ind = max(sum(v for _, _, v in c) for r in range(1, 5) for c in combinations(pr, r) if sum(o for _, o, _ in c) <= budget)
    opts = [L(x) for x in (by_pi, by_npv, best_ind, by_out)]
    assert abs(by_pi - 16.2) < 1e-9 and len(set(opts)) == 4
    tb = table(["Project", "Outlay (₹ lakh)", "NPV (₹ lakh)"], [[n, o, f"{v:.1f}"] for n, o, v in pr])
    B.add(m, "L2", f"Capital available this year is limited to ₹{budget} lakh. All projects are divisible and independent.\n\n{tb}\n\nThe maximum total NPV achievable is:",
          opts[0],
          [(opts[1], "projects ranked by absolute NPV"),
           (opts[2], "projects treated as indivisible"),
           (opts[3], "projects ranked by smallest outlay")],
          ["PI = 1 + NPV/Outlay: P 1.30, Q 1.40, R 1.28, S 1.25 → rank Q, P, R, S",
           "Q (₹15 lakh) + P (₹20 lakh) = ₹35 lakh; balance ₹15 lakh → 15/25 of R",
           f"NPV = 6.0 + 6.0 + 0.6 × 7.0 = ₹{by_pi:.2f} lakh"],
          "Divisible rationing: rank by PI (NPV per ₹ of outlay)", "With divisibility, fractional projects fill the budget exactly.", ref=PAT)

    budget = 50
    pr = [("A", 35, 12.6), ("B", 20, 6.8), ("C", 30, 9.9), ("D", 15, 3.9), ("E", 10, 3.0)]
    combos = [c for r in range(1, 6) for c in combinations(pr, r) if sum(o for _, o, _ in c) <= budget]
    best = max(combos, key=lambda c: sum(v for *_, v in c))
    def greedy_ind(key):
        left, pick = budget, []
        for p in sorted(pr, key=key):
            if p[1] <= left: pick.append(p); left -= p[1]
        return pick
    lab = lambda c: " and ".join(n for n, *_ in sorted(c)) if len(c) < 3 else ", ".join(n for n, *_ in sorted(c)[:-1]) + " and " + sorted(c)[-1][0]
    txt = lambda c: f"{lab(c)} — NPV {L(sum(v for *_, v in c))}"
    g_pi, g_npv, g_out = greedy_ind(lambda p: -p[2] / p[1]), greedy_ind(lambda p: -p[2]), greedy_ind(lambda p: p[1])
    opts = [txt(best), txt(g_pi), txt(g_npv), txt(g_out)]
    assert lab(best) == "B and C" and len(set(opts)) == 4
    tb = table(["Project", "Outlay (₹ lakh)", "NPV (₹ lakh)", "PI"], [[n, o, f"{v:.1f}", f"{1+v/o:.2f}"] for n, o, v in pr])
    B.add(m, "L3", f"Kshitij Infra Ltd has ₹{budget} lakh for capital projects this year. The projects are independent and indivisible; unused funds earn nothing extra.\n\n{tb}\n\nWhich selection maximises NPV?",
          opts[0],
          [(opts[1], "PI ranking applied greedily to indivisible projects, leaving ₹5 lakh idle"),
           (opts[2], "projects picked in order of absolute NPV"),
           (opts[3], "cheapest projects picked first")],
          ["With indivisible projects PI ranking can leave funds idle; test feasible combinations.",
           "A + E = 45 → 15.6; A + D = 50 → 16.5; B + C = 50 → 16.7; B + D + E = 45 → 13.7; C + D = 45 → 13.8",
           f"Best feasible combination: {txt(best)}"],
          "Indivisible rationing: maximise total NPV over feasible combinations",
          "The highest-PI project (A) is not in the optimal set.", ref=PAT)

    k = 0.12
    pA, cA, pB, cB, n = 10, 4.2, 25, 9.3, 4
    A = pvaf(k, n)
    nA, nB = cA * A - pA, cB * A - pB
    iA, iB = irr([-pA] + [cA] * n), irr([-pB] + [cB] * n)
    iInc = irr([-(pB - pA)] + [cB - cA] * n)
    assert nB > nA and iA > iB and iInc > k
    c_txt = f"B, since the incremental IRR of about {pct(iInc,1)} exceeds 12%"
    B.add(m, "L3", f"Two mutually exclusive projects each have a {n}-year life. Cost of capital is {pct(k,0)} (PVAF = {A}).\n\n" +
          table(["Project", "Outlay (₹ lakh)", "Annual inflow (₹ lakh)"], [["A", pA, cA], ["B", pB, cB]]) +
          "\n\nWhich project should be chosen, and why?",
          c_txt,
          [(f"A, since its IRR of about {pct(iA,1)} exceeds B's IRR", "ranks by IRR, ignoring scale"),
           (f"A, since its PI of {1+nA/pA:.2f} is higher than B's PI of {1+nB/pB:.2f}", "PI ranking used for mutually exclusive projects without a budget limit"),
           ("Either, since both have a positive NPV and an IRR above 12%", "treats mutually exclusive projects as independent accept/reject decisions")],
          [f"NPV A = {cA} × {A} − {pA} = ₹{nA:.3f} lakh; NPV B = {cB} × {A} − {pB} = ₹{nB:.3f} lakh",
           f"IRR A ≈ {pct(iA,1)}; IRR B ≈ {pct(iB,1)} — a scale conflict",
           f"Incremental (B − A): outlay ₹15 lakh, inflow ₹{cB-cA:.1f} lakh → IRR ≈ {pct(iInc,1)} > 12%, so the extra investment adds value → choose B"],
          "Incremental IRR > k ⇒ choose larger project (consistent with NPV)",
          "Mutually exclusive: only one can be taken, so passing the hurdle is not enough.", ref=PAT)

    st = ["For two conventional mutually exclusive projects whose NPV profiles cross, the NPV and IRR rankings conflict only when the cost of capital is below the crossover rate.",
          "A project can have more than one IRR when its cash-flow stream changes sign more than once.",
          "Under single-period capital rationing with indivisible projects, ranking by profitability index always maximises total NPV."]
    c, w = stmt_opts([True, True, False],
                     ["above the crossover rate both methods favour the same project",
                      "multiple sign changes can give multiple IRRs (Descartes' rule)",
                      "indivisibility can leave funds idle, so combinations must be tested"])
    B.add(m, "L3", "Consider the following statements:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w,
          ["Above the Fisher rate, the project with higher IRR also has higher NPV; below it, rankings flip.",
           "Non-conventional flows (e.g. −, +, −) can yield two or more IRRs.",
           "PI ranking is exact only for divisible projects; with indivisible projects evaluate feasible combinations."],
          "Conflict zone: k < crossover rate", "Statement 3 is true only for divisible projects.", kind="statement", ref=PAT)

    # ======================= Capital budgeting under risk (6) =======================
    m = M("capital-budgeting-under-risk")
    B.add(m, "L1", "Under the certainty-equivalent approach, the certainty-equivalent cash flows of a project are discounted at the:",
          "Risk-free rate of return",
          [("Risk-adjusted discount rate", "double-counts risk"),
           ("Weighted average cost of capital", "WACC embeds a risk premium"),
           ("Project's internal rate of return", "IRR is an output, not a discount rate")],
          ["Risk is removed from the numerator by multiplying each cash flow by its CE coefficient (αt ≤ 1).",
           "Discounting at a risk-adjusted rate as well would penalise risk twice, so the risk-free rate is used."],
          "NPV = Σ αt CFt ÷ (1 + Rf)^t − I₀", "Adjust risk in either the numerator or the denominator, never both.",
          kind="conceptual", ref=PAT)

    out, cf, n, rf, rp, wacc = 10, 4, 4, 0.08, 0.06, 0.12
    npv = lambda r: cf * pvaf(r, n) - out
    B.add(m, "L2", f"A project costs ₹{out} lakh and yields ₹{cf} lakh a year for {n} years. The risk-free rate is {pct(rf,0)}, the firm's WACC is {pct(wacc,0)}, and management adds a risk premium of {pct(rp,0)} over the risk-free rate for projects of this class. PVAF (4 years): 6% = {pvaf(0.06,4)}, 8% = {pvaf(0.08,4)}, 12% = {pvaf(0.12,4)}, 14% = {pvaf(0.14,4)}. The NPV using the risk-adjusted discount rate is:",
          L(npv(rf + rp), 3),
          [(L(npv(rf), 3), "risk-free rate used; premium ignored"),
           (L(npv(wacc), 3), "WACC used instead of the risk-adjusted rate"),
           (L(npv(rp), 3), "risk premium alone used as the discount rate")],
          [f"RADR = {pct(rf,0)} + {pct(rp,0)} = 14%",
           f"NPV = {cf} × {pvaf(0.14,4)} − {out} = ₹{npv(0.14):.3f} lakh"],
          "RADR = Rf + Risk premium", "The premium is added to Rf, not to WACC and not used alone.", ref=PAT)

    out, cfs, al, rf, wa = 6, [3, 3, 2.5], [0.9, 0.8, 0.7], 0.06, 0.11
    f6 = [pvf(rf, i + 1) for i in range(3)]; f11 = [pvf(wa, i + 1) for i in range(3)]
    ce = sum(c * a * f for c, a, f in zip(cfs, al, f6)) - out
    no_ce = sum(c * f for c, f in zip(cfs, f6)) - out
    ce_w = sum(c * a * f for c, a, f in zip(cfs, al, f11)) - out
    rev = sum(c * a * f for c, a, f in zip(cfs, al[::-1], f6)) - out
    opts = [R(round(x * 1e5)) for x in (ce, no_ce, ce_w, rev)]
    assert len(set(opts)) == 4
    tb = table(["Year", "1", "2", "3"], [["Expected cash flow (₹ lakh)"] + cfs, ["Certainty-equivalent coefficient"] + al,
                                        ["PVF at 6% (risk-free)"] + f6, ["PVF at 11% (WACC)"] + f11])
    B.add(m, "L2", f"A project costs ₹{out} lakh.\n\n{tb}\n\nThe NPV under the certainty-equivalent approach is:",
          opts[0],
          [(opts[1], "CE coefficients ignored"),
           (opts[2], "CE flows discounted at WACC (risk counted twice)"),
           (opts[3], "coefficients applied in reverse year order")],
          ["CE cash flows = 2.70, 2.40, 1.75 (₹ lakh)",
           f"PV at 6% = 2.70×0.943 + 2.40×0.890 + 1.75×0.840 = ₹{ce+out:.4f} lakh",
           f"NPV = {ce+out:.4f} − {out} = {opts[0]}"],
          "NPV = Σ αt CFt × PVF(Rf, t) − I₀", "Once flows are made certain, discount at the risk-free rate.", ref=PAT)

    out, n, k = 12, 3, 0.10
    dist = [(4, 0.3), (5, 0.5), (8, 0.2)]
    A = pvaf(k, n)
    ecf = sum(c * p for c, p in dist)
    enpv = ecf * A - out
    simple = sum(c for c, _ in dist) / 3 * A - out
    mode = 5 * A - out
    undisc = ecf * n - out
    assert abs(ecf - 5.3) < 1e-9
    tb = table(["Annual cash inflow (₹ lakh)", "Probability"], [[c, p] for c, p in dist])
    B.add(m, "L2", f"A project costs ₹{out} lakh and has a life of {n} years. The annual cash inflow (same in each year) follows this distribution:\n\n{tb}\n\nAt a discount rate of {pct(k,0)} (PVAF = {A}), the expected NPV is:",
          L(enpv, 3),
          [(L(simple, 3), "simple average of outcomes; probabilities ignored"),
           (L(mode, 3), "most likely outcome used instead of the expected value"),
           (L(undisc, 3), "expected inflows not discounted")],
          [f"Expected annual inflow = 4×0.3 + 5×0.5 + 8×0.2 = ₹{ecf:.2f} lakh",
           f"ENPV = {ecf:.2f} × {A} − {out} = ₹{enpv:.3f} lakh"],
          "ENPV = Σ E(CFt) × PVFt − I₀", "Weight by probabilities before discounting.", ref=PAT)

    out, q, sp, vc, fc, n, k = 20, 10000, 500, 300, 8, 5, 0.10
    A = pvaf(k, n)
    cf = (q * (sp - vc)) / 1e5 - fc
    npv = cf * A - out
    rev_pv, vc_pv, cont_pv = q * sp / 1e5 * A, q * vc / 1e5 * A, q * (sp - vc) / 1e5 * A
    s_p, s_v, s_q = npv / rev_pv, npv / vc_pv, npv / cont_pv
    s_undisc = npv / (q * sp / 1e5)
    assert abs(cf - 12) < 1e-9
    B.add(m, "L3", f"Jivika Appliances Ltd: outlay ₹{out} lakh; annual sales {inr(q)} units at ₹{sp}; variable cost ₹{vc} per unit; fixed cash cost ₹{fc} lakh a year; life {n} years; cost of capital {pct(k,0)} (PVAF = {A}); ignore tax. Using sensitivity analysis, which variable is the most sensitive, and by how much can it change adversely before NPV becomes zero?",
          f"Selling price: a fall of {pct(s_p)}",
          [(f"Sales volume: a fall of {pct(s_q)}", "volume sensitivity (less sensitive than price)"),
           (f"Variable cost: a rise of {pct(s_v)}", "variable-cost sensitivity (less sensitive than price)"),
           (f"Selling price: a fall of {pct(s_undisc)}", "NPV compared with one year's undiscounted revenue")],
          [f"Annual CF = {inr(q)} × {sp-vc} − {fc} lakh = ₹{cf:.0f} lakh; NPV = {cf:.0f} × {A} − {out} = ₹{npv:.3f} lakh",
           f"Price: NPV ÷ PV of revenue = {npv:.3f} ÷ {rev_pv:.2f} = {pct(s_p)}",
           f"Variable cost: {npv:.3f} ÷ {vc_pv:.2f} = {pct(s_v)}; volume: {npv:.3f} ÷ {cont_pv:.2f} = {pct(s_q)}",
           "Smallest tolerable change → selling price is most sensitive."],
          "Sensitivity = NPV ÷ PV of the cash-flow element affected", "Volume affects contribution, not revenue, so it is less sensitive than price.", ref=PAT)

    X = [(2, 0.2), (5, 0.5), (9, 0.3)]; Y = [(4, 0.3), (6, 0.4), (8, 0.3)]
    def stats(d):
        e = sum(v * p for v, p in d); sd = math.sqrt(sum(p * (v - e) ** 2 for v, p in d)); return e, sd
    ex, sx = stats(X); ey, sy = stats(Y)
    vals = [v for v, _ in X]; mu = sum(vals) / 3; sd_u = math.sqrt(sum((v - mu) ** 2 for v in vals) / 3)
    opts = [f2(sx / ex), f2(sx ** 2 / ex), f2(ex / sx), f2(sd_u / mu)]
    assert len(set(opts)) == 4 and sy / ey < sx / ex
    tb = table(["NPV of X (₹ lakh)", "Probability", "NPV of Y (₹ lakh)", "Probability "], [[a, p, b, q_] for (a, p), (b, q_) in zip(X, Y)])
    B.add(m, "L3", f"Two projects have the following NPV distributions:\n\n{tb}\n\nThe coefficient of variation of project X is closest to (Y's is {sy/ey:.2f}):",
          opts[0],
          [(opts[1], "variance divided by expected NPV"),
           (opts[2], "expected NPV divided by standard deviation (inverted)"),
           (opts[3], "unweighted mean and standard deviation; probabilities ignored")],
          [f"E(NPV X) = 0.4 + 2.5 + 2.7 = ₹{ex:.2f} lakh",
           f"σ = √[0.2(2 − 5.6)² + 0.5(5 − 5.6)² + 0.3(9 − 5.6)²] = √{sx**2:.2f} = {sx:.3f}",
           f"CV = {sx:.3f} ÷ {ex:.2f} = {opts[0]} — higher than Y's {sy/ey:.2f}, so X is riskier per unit of expected NPV"],
          "CV = σ ÷ E(NPV)", "Use probability weights for both the mean and the variance.", ref=PAT)
