"""FIN-B part 2: derivatives, risk, TVM and valuation + case sets C5 (options trader), C6 (bank risk)."""
import math
from finb_common import (M, statements, stmt_opts, ar_opts, ar_stem, table, f2, inr, R, pct, lakh, crore)


def add_all(B):
    # =============================== Margining ===============================
    mg = M("margining-initial-and-variation")
    st = ["Variation (mark-to-market) margin settles the day's gain or loss on a futures position against the daily settlement price.",
          "Initial margin is collected upfront to cover the potential loss over the margin period of risk at a high confidence level.",
          "Once initial margin is paid, no further margin is payable on a futures position until expiry."]
    c, w = stmt_opts([True, True, False], ["MTM/variation margin is the daily settlement of gains/losses",
                                          "initial margin is a VaR/SPAN-based upfront buffer",
                                          "MTM losses must be paid daily; margins are revised as prices and volatility change"])
    B.add(mg, "L1", "Consider the following statements about margins on exchange-traded futures:\n\n" + statements(st) + "\n\nWhich of the statements is/are correct?",
          c, w, ["Variation margin = daily MTM cash settlement.", "Initial margin (SPAN/VaR + exposure/ELM) is collected upfront.",
                 "Daily MTM losses and revised margin requirements must be met — statement 3 is false."],
          "Initial margin (upfront) + Variation margin (daily MTM)", "Initial margin is not a one-time lifetime deposit.", kind="statement")

    lots, lot, bp, sp = 3, 50, 22400, 22310
    mtm = lots * lot * (sp - bp)
    B.add(mg, "L2", f"A trader is long {lots} lots of ALPHA50 index futures (lot size {lot}) bought today at {inr(bp)}. The day's settlement price is {inr(sp)}. The day's mark-to-market settlement is:",
          f"Pay {R(-mtm)}",
          [(f"Receive {R(-mtm)}", "sign reversed: a long loses when price falls"),
           (f"Pay {R(-mtm/lots)}", "computed for one lot only"),
           (f"Pay {R(-mtm/lot)}", "lot size ignored; index points × lots only")],
          [f"Change = {inr(sp)} − {inr(bp)} = {sp-bp} points.", f"MTM = {lots} × {lot} × ({sp-bp}) = {R(mtm)} → pay {R(-mtm)}."],
          "MTM = Lots × Lot size × (Settlement − Trade price)", "Falling price → long pays.")

    ip0, lot2, im, mm = 1250, 100, 15000, 11000
    path = [1232, 1205, 1226]
    bal, prev, calls, log = im, ip0, [], []
    for d, p in enumerate(path, 1):
        bal += (p - prev) * lot2; prev = p
        call = im - bal if bal < mm else 0
        calls.append(call); log.append((d, p, bal, call)); bal += call
    assert calls == [0, 4500, 0]
    d2 = log[1]
    tbm = table(["Day", "Settlement price (₹)"], [[f"Day {d}", p] for d, p, _, _ in log])
    B.add(mg, "L3", f"On an exchange that uses a maintenance-margin system, a trader buys one futures contract (lot {lot2}) at ₹{ip0}. Initial margin is {R(im)} and maintenance margin {R(mm)}; if the balance falls below maintenance, it must be restored to the initial level.\n\n{tbm}\n\nThe amount the trader must deposit on Day 2 is:",
          R(d2[3]),
          [(R(mm - d2[2]), "topped up only to the maintenance level"),
           (R((ip0 - path[0]) * 0 + (path[0] - path[1]) * lot2), "only Day 2's MTM loss deposited"),
           ("Nil", "compared the pre-Day-2 balance with the maintenance margin")],
          [f"Day 1: loss ({ip0}−{path[0]})×{lot2} = {inr((ip0-path[0])*lot2)} → balance {inr(log[0][2])} (≥ {inr(mm)}, no call).",
           f"Day 2: loss ({path[0]}−{path[1]})×{lot2} = {inr((path[0]-path[1])*lot2)} → balance {inr(d2[2])} < {inr(mm)}.",
           f"Variation margin = {inr(im)} − {inr(d2[2])} = {R(d2[3])} (restore to initial)."],
          "Call = Initial − Balance, when Balance < Maintenance", "Top-up is to the initial margin, not to maintenance.")

    lots3, lot3, px, span, elm = 4, 500, 1840, 0.14, 0.035
    cv = lots3 * lot3 * px
    B.add(mg, "L2", f"A client sells {lots3} lots of a stock future (lot size {lot3}) at ₹{inr(px)}. SPAN margin is {pct(span)} and exposure margin {pct(elm,1)} of contract value. The total upfront initial margin is:",
          R(cv * (span + elm)),
          [(R(cv * span), "exposure margin omitted"),
           (R(cv * span * (1 + elm)), "exposure margin applied to the SPAN amount instead of contract value"),
           (R(lot3 * px * (span + elm)), "computed for one lot")],
          [f"Contract value = {lots3} × {lot3} × {inr(px)} = {R(cv)}.", f"Margin = {pct(span)} + {pct(elm,1)} = {pct(span+elm,1)} → {R(cv*(span+elm))}."],
          "Initial margin = (SPAN% + Exposure%) × Contract value", "Both components are on contract value.")

    # =============================== Open interest ===============================
    mo = M("open-interest-interpretation")
    B.add(mo, "L2", "Match the price–open interest behaviour (List I) with its usual interpretation (List II):\n\n"
          + table(["List I", "List II"], [["A. Price ↑, OI ↑", "1. Short covering"], ["B. Price ↓, OI ↑", "2. Long unwinding"],
                                          ["C. Price ↑, OI ↓", "3. Long build-up"], ["D. Price ↓, OI ↓", "4. Short build-up"]], ["---", "---"]),
          "A-3, B-4, C-1, D-2",
          [("A-3, B-4, C-2, D-1", "short covering and long unwinding swapped"),
           ("A-4, B-3, C-1, D-2", "long and short build-up swapped"),
           ("A-1, B-2, C-3, D-4", "reads OI change as closing when it is opening")],
          ["Rising OI = new positions; falling OI = positions being closed.", "Price direction tells which side is aggressive."],
          "Price × OI matrix", "Falling OI never signals build-up.", kind="conceptual")

    trades = [("A", "B", 10), ("C", "D", 5), ("E", "A", 4), ("B", "C", 3), ("D", "E", 4)]
    pos = {}
    for b, s, q in trades:
        pos[b] = pos.get(b, 0) + q; pos[s] = pos.get(s, 0) - q
    oi = sum(v for v in pos.values() if v > 0)
    vol = sum(q for _, _, q in trades)
    assert oi == 8 and vol == 26
    tbt = table(["Trade", "Buyer", "Seller", "Contracts"], [[i+1, b, s, q] for i, (b, s, q) in enumerate(trades)], ["---", "---", "---", "---:"])
    B.add(mo, "L3", f"A newly listed futures contract has the following trades on its first day (no positions existed before):\n\n{tbt}\n\nOpen interest at the end of the day is:",
          f"{oi} contracts",
          [(f"{vol} contracts", "trading volume taken as open interest"),
           (f"{sum(v for v in pos.values() if v>0) + sum(-v for v in pos.values() if v<0)} contracts", "long and short positions both counted"),
           (f"{trades[0][2]+trades[1][2]} contracts", "only the two trades where both sides opened counted; later openings/closings ignored")],
          ["Net positions: " + ", ".join(f"{k} {v:+d}" for k, v in sorted(pos.items())) + ".", f"OI = sum of long positions = {oi} (= sum of shorts)."],
          "OI = Σ long positions = Σ short positions", "Each contract has one long and one short — count one side only.")

    tpc = [(24000, 9.2, 6.1), (24200, 16.4, 11.3), (24400, 12.7, 18.1)]  # strike, put OI lakh, call OI lakh
    vols = [(24000, 40.0, 22.0), (24200, 55.0, 60.0), (24400, 30.0, 70.0)]
    put, call = sum(p for _, p, _ in tpc), sum(c for _, _, c in tpc)
    pcr = put / call
    tbo = table(["Strike", "Put OI (lakh)", "Call OI (lakh)", "Put volume (lakh)", "Call volume (lakh)"],
                [[k, p, c, vols[i][1], vols[i][2]] for i, (k, p, c) in enumerate(tpc)])
    B.add(mo, "L2", f"Option-chain data for the near-month expiry of an index:\n\n{tbo}\n\nThe OI-based put–call ratio (PCR) is:",
          f"{pcr:.2f}",
          [(f"{call/put:.2f}", "call OI ÷ put OI (ratio inverted)"),
           (f"{sum(v[1] for v in vols)/sum(v[2] for v in vols):.2f}", "volume-based PCR computed instead of OI-based"),
           (f"{tpc[1][1]/tpc[1][2]:.2f}", "only the at-the-money strike used")],
          [f"Total put OI = {put:.1f} lakh; total call OI = {call:.1f} lakh.", f"PCR = {put:.1f} ÷ {call:.1f} = {pcr:.2f}."],
          "PCR (OI) = Σ Put OI ÷ Σ Call OI", "OI and volume PCRs can point in opposite directions.")

    # =============================== Options basics & payoff ===============================
    mop = M("options-basics-and-payoff")
    B.add(mop, "L1", "A share trades at ₹1,520. Which of the following options is in-the-money?",
          "A call with strike ₹1,480",
          [("A put with strike ₹1,480", "moneyness of puts reversed: this put is out-of-the-money"),
           ("A call with strike ₹1,560", "a call is ITM only when strike < spot"),
           ("A put with strike ₹1,520", "this is at-the-money")],
          ["Call ITM when S > K; put ITM when S < K.", "1,520 > 1,480 → the ₹1,480 call is ITM (intrinsic ₹40)."],
          "Call intrinsic = max(S − K, 0); Put intrinsic = max(K − S, 0)", "The same strike is ITM for a call and OTM for a put.", kind="conceptual")

    K, prem, lot, ST = 640, 22, 1000, 596
    pl = (K - ST - prem) * lot
    B.add(mop, "L2", f"An investor buys one lot ({lot} shares) of a put option, strike ₹{K}, premium ₹{prem}. At expiry the share settles at ₹{ST}. His net profit is:",
          R(pl),
          [(R((K - ST) * lot), "premium paid ignored"),
           (R((K - ST + prem) * lot), "premium added instead of deducted"),
           (f"Loss of {R(prem*lot)}", "treated the put as expiring worthless")],
          [f"Payoff = max({K} − {ST}, 0) = ₹{K-ST}.", f"Net = ({K-ST} − {prem}) × {lot} = {R(pl)}."],
          "Long put P&L = max(K − S_T, 0) − Premium", "Break-even is K − premium = ₹618.")

    k1, p1, k2, p2, lotb = 4000, 145, 4200, 62, 50
    debit = p1 - p2; mxp = (k2 - k1 - debit) * lotb; be = k1 + debit
    B.add(mop, "L3", f"A trader buys a {k1} call at ₹{p1} and sells a {k2} call at ₹{p2} on the same index and expiry (lot {lotb}). The maximum profit per lot and the break-even index level are:",
          f"{R(mxp)}; {inr(be)}",
          [(f"{R((k2-k1)*lotb)}; {inr(be)}", "net debit not deducted from maximum profit"),
           (f"{R(mxp)}; {inr(k1+p1)}", "break-even ignores premium received on the short call"),
           (f"{R(mxp)}; {inr(k2-debit)}", "break-even measured down from the upper strike")],
          [f"Net debit = {p1} − {p2} = ₹{debit}.", f"Max profit = ({k2} − {k1} − {debit}) × {lotb} = {R(mxp)} (at or above {k2}).",
           f"Break-even = {k1} + {debit} = {inr(be)}."],
          "Bull call spread: Max profit = (K2 − K1 − Debit) × Lot; BE = K1 + Debit", "Maximum loss = net debit (₹4,150 per lot).")

    S, Kp, C, r, t = 820, 800, 52, 0.08, 0.25
    pvk = Kp / (1 + r) ** t
    P = C - S + pvk
    B.add(mop, "L3", f"A European call on a non-dividend-paying share (spot ₹{S}, strike ₹{Kp}, 3 months to expiry) trades at ₹{C}. The risk-free rate is {pct(r,0)} p.a. compounded annually. By put–call parity, the price of the European put with the same strike and expiry is:",
          f"₹{P:.2f}",
          [(f"₹{C - S + Kp:.2f}", "strike not discounted to present value"),
           (f"₹{C + S - pvk:.2f}", "parity rearranged with wrong signs (P = C + S − PV(K))"),
           (f"₹{C - S/(1+r)**t + Kp:.2f}", "spot discounted instead of strike")],
          [f"PV(K) = {Kp} ÷ 1.08^0.25 = ₹{pvk:.2f}.", f"P = C − S + PV(K) = {C} − {S} + {pvk:.2f} = ₹{P:.2f}."],
          "C + PV(K) = P + S", "Only the strike is discounted; spot is already a present value.")

    Ks, cp, pp, lots_, STs = 1200, 48, 36, 400, 1310
    pls = (abs(STs - Ks) - cp - pp) * lots_
    B.add(mop, "L3", f"An investor buys a straddle: one lot ({lots_} shares) each of the ₹{Ks} call at ₹{cp} and the ₹{Ks} put at ₹{pp}. At expiry the share settles at ₹{STs}. The net profit or loss is:",
          f"Profit of {R(pls)}",
          [(f"Profit of {R((STs-Ks)*lots_)}", "premiums ignored"),
           (f"Profit of {R((STs-Ks-cp)*lots_)}", "only the call premium deducted; put premium forgotten"),
           (f"Loss of {R((cp+pp)*lots_)}", "treated both legs as expiring worthless")],
          [f"Call payoff = {STs} − {Ks} = ₹{STs-Ks}; put expires worthless.", f"Net = ({STs-Ks} − {cp} − {pp}) × {lots_} = {R(pls)}.",
           f"Break-evens: {Ks-cp-pp} and {Ks+cp+pp}."],
          "Long straddle P&L = |S_T − K| − (C + P)", "Both premiums are sunk regardless of direction.")

    Kc, pc, Sc = 500, 38, 527
    B.add(mop, "L2", f"A call option with strike ₹{Kc} trades at a premium of ₹{pc} when the underlying is at ₹{Sc}. Its intrinsic value and time value are:",
          f"Intrinsic ₹{Sc-Kc}; time value ₹{pc-(Sc-Kc)}",
          [(f"Intrinsic ₹{pc}; time value ₹0", "entire premium treated as intrinsic value"),
           (f"Intrinsic ₹{pc-(Sc-Kc)}; time value ₹{Sc-Kc}", "intrinsic and time value swapped"),
           (f"Intrinsic ₹0; time value ₹{pc}", "option treated as out-of-the-money")],
          [f"Intrinsic = max({Sc} − {Kc}, 0) = ₹{Sc-Kc}.", f"Time value = {pc} − {Sc-Kc} = ₹{pc-(Sc-Kc)}."],
          "Premium = Intrinsic value + Time value", "Time value decays to zero at expiry.")

    # =============================== Swaps ===============================
    msw = M("swaps-interest-rate-and-currency")
    B.add(msw, "L1", "In a plain-vanilla fixed-for-floating interest rate swap in a single currency:",
          "The notional principal is not exchanged; only the net interest difference is settled on each payment date",
          [("The notional principal is exchanged at inception and at maturity", "describes a currency swap"),
           ("Both parties pay floating rates linked to different benchmarks", "describes a basis swap"),
           ("The fixed-rate payer pays the full fixed interest and receives the full floating interest in gross", "gross settlement is not the norm; payments are netted")],
          ["Same currency → exchanging principal is pointless; it is notional.", "Periodic payments are netted."],
          "Net payment = Notional × (Fixed − Floating) × Day fraction", "Principal exchange is a currency-swap feature.", kind="conceptual")

    N, fx, fl, days = 50e7, 0.072, 0.0685, 182
    net = N * (fx - fl) * days / 365
    B.add(msw, "L3", f"Bank X pays fixed {pct(fx,2)} and receives floating on a notional ₹50 crore interest rate swap with semi-annual settlement (Actual/365). The floating rate set for the current {days}-day period is {pct(fl,2)}. The net settlement for the period is:",
          f"Bank X pays {R(net)}",
          [(f"Bank X receives {R(net)}", "direction reversed: fixed payer pays when fixed > floating"),
           (f"Bank X pays {R(N*(fx-fl))}", "annual differential; day-count fraction ignored"),
           (f"Bank X pays {R(N*(fx-fl)*days/360)}", "Actual/360 used instead of Actual/365")],
          [f"Differential = {pct(fx,2)} − {pct(fl,2)} = {pct(fx-fl,2)}.", f"Net = 50,00,00,000 × {fx-fl:.4f} × {days}/365 = {R(net)}; fixed payer pays."],
          "Net = N × (Fixed − Floating) × days/365", "Check the day-count convention stated.")

    fa, fla, fb, flb = 8.0, 0.5, 9.5, 1.2
    gain = (fb - fa) - (flb - fla); eff_a = fla - gain / 2
    assert abs(gain - 0.8) < 1e-9
    tbs = table(["", "Fixed-rate market", "Floating-rate market"], [["Company A (AAA)", f"{fa}%", f"MIBOR + {fla}%"], ["Company B (A)", f"{fb}%", f"MIBOR + {flb}%"]])
    B.add(msw, "L3", f"{tbs}\n\nA wants floating-rate funds and B wants fixed-rate funds. They borrow where each has a comparative advantage and swap, sharing the total gain equally (no intermediary). A's effective cost of funds is:",
          f"MIBOR + {eff_a:.2f}%",
          [(f"MIBOR − {abs(fla-gain):.2f}%", "entire gain allotted to A"),
           (f"MIBOR + {fla:.2f}%", "no gain from the swap recognised"),
           (f"MIBOR − {abs(fla-(fb-fa)/2):.2f}%", "half the fixed-rate differential (not the net gain) taken as A's gain")],
          [f"Fixed differential = {fb-fa:.1f}%; floating differential = {flb-fla:.1f}%.", f"Total gain = {fb-fa:.1f} − {flb-fla:.1f} = {gain:.1f}%; each gets {gain/2:.1f}%.",
           f"A's cost = MIBOR + {fla} − {gain/2:.1f} = MIBOR + {eff_a:.2f}%."],
          "Gain = ΔFixed − ΔFloating; share per agreement", "A has absolute advantage in both, comparative advantage in fixed.")

    usd, s0, s1, ri, ru = 10e6, 83.0, 85.0, 0.075, 0.04
    inr_int = usd * s0 * ri
    B.add(msw, "L2", f"Two firms enter a fixed-for-fixed currency swap: principal USD 10 million exchanged at inception at ₹{s0:g}/USD; annual interest {pct(ri,1)} on the INR leg and {pct(ru,0)} on the USD leg. At the end of year 1 the spot rate is ₹{s1:g}/USD. The INR interest payable by the INR-leg payer for year 1 is:",
          f"₹{inr_int/1e7:.4f} crore",
          [(f"₹{usd*s0*ru/1e7:.4f} crore", "USD coupon rate applied to INR principal"),
           (f"₹{usd*s1*ri/1e7:.4f} crore", "INR principal revalued at year-end spot; principal is fixed at inception rate"),
           (f"₹{usd*s0*(ri-ru)/1e7:.4f} crore", "net rate differential; currency-swap coupons are in different currencies and not netted")],
          [f"INR principal = 1 crore USD × {s0:g} = ₹{usd*s0/1e7:g} crore.", f"INR interest = {usd*s0/1e7:g} × {pct(ri,1)} = ₹{inr_int/1e7:.4f} crore."],
          "INR coupon = USD principal × Inception rate × INR rate", "Principal is locked at the inception exchange rate.")

    # =============================== Market, credit & operational risk ===============================
    mrk = M("market-credit-and-operational-risk")
    B.add(mrk, "L1", "Under the Basel definition, operational risk is the risk of loss from inadequate or failed internal processes, people and systems or from external events. This definition:",
          "Includes legal risk but excludes strategic and reputational risk",
          [("Includes legal, strategic and reputational risk in the definition", "strategic/reputational risks are expressly excluded"),
           ("Excludes legal risk but includes strategic and reputational risk", "legal risk is expressly included"),
           ("Covers only credit losses caused by borrower fraud and misconduct", "credit-related fraud boundary is not the defining feature")],
          ["Basel II para on operational risk: includes legal risk; excludes strategic and reputational risk."],
          "Op risk = process, people, systems, external events (+ legal)", "Reputational risk is not in the capital definition.", kind="conceptual",
          verify_fact=True, ref="BCBS, Basel II framework — definition of operational risk")

    drawn, undrawn, ccf, pd_, rec = 8e7, 4e7, 0.5, 0.025, 0.40
    ead = drawn + ccf * undrawn; el = pd_ * (1 - rec) * ead
    B.add(mrk, "L2", f"A corporate borrower has drawn {crore(drawn)} of a {crore(drawn+undrawn)} facility. The credit conversion factor for the undrawn portion is {pct(ccf,0)}, PD is {pct(pd_,1)} and the expected recovery on default is {pct(rec,0)}. Expected loss is:",
          lakh(el),
          [(lakh(pd_ * (1 - rec) * drawn), "undrawn exposure ignored"),
           (lakh(pd_ * rec * ead), "recovery rate used as LGD"),
           (lakh(pd_ * (1 - rec) * (drawn + undrawn)), "undrawn amount taken at 100% instead of CCF")],
          [f"EAD = {crore(drawn)} + {pct(ccf,0)} × {crore(undrawn)} = {crore(ead)}.", f"LGD = 1 − {pct(rec,0)} = {pct(1-rec,0)}.",
           f"EL = {pct(pd_,1)} × {pct(1-rec,0)} × {crore(ead)} = {lakh(el)}."],
          "EL = PD × LGD × EAD", "LGD = 1 − Recovery.")

    port, md, dy = 100e7, 4.2, 0.005
    loss = port * md * dy
    B.add(mrk, "L3", f"A bank's AFS bond portfolio of {crore(port)} has a modified duration of {md} and a Macaulay duration of 4.37. If yields rise uniformly by 50 basis points, the approximate fall in portfolio value (ignoring convexity) is:",
          crore(loss),
          [(crore(port * 4.37 * dy), "Macaulay duration used instead of modified duration"),
           (crore(port * md * 0.05), "50 bps read as 5%"),
           (crore(port * md * dy / 2), "halved the duration effect as if semi-annual")],
          [f"ΔP ≈ −MD × Δy × P = −{md} × 0.005 × {crore(port)} = −{crore(loss)}."],
          "ΔP/P ≈ −Modified duration × Δy", "Modified duration already adjusts Macaulay for yield.")

    v1, v2, rho = 3.0, 4.0, 0.25
    vp = math.sqrt(v1**2 + v2**2 + 2 * rho * v1 * v2)
    B.add(mrk, "L3", f"A trading desk has a 10-day 99% VaR of ₹{v1:g} crore on its equity book and ₹{v2:g} crore on its bond book. The correlation between the books' returns is {rho}. Assuming normal returns, the diversified 10-day 99% VaR of the desk is:",
          f"₹{vp:.2f} crore",
          [(f"₹{v1+v2:.2f} crore", "simple sum — assumes perfect correlation"),
           (f"₹{math.sqrt(v1**2+v2**2):.2f} crore", "correlation ignored (treated as zero)"),
           (f"₹{math.sqrt(v1**2+v2**2+rho*v1*v2):.2f} crore", "cross term not doubled")],
          [f"VaR_p = √({v1:g}² + {v2:g}² + 2×{rho}×{v1:g}×{v2:g}) = √{v1**2+v2**2+2*rho*v1*v2:g} = ₹{vp:.2f} crore."],
          "VaR_p = √(V₁² + V₂² + 2ρV₁V₂)", "Diversification benefit = ₹{:.2f} crore.".format(v1 + v2 - vp))

    # =============================== Risk identification & mitigation ===============================
    mri = M("risk-identification-and-mitigation")
    B.add(mri, "L1", "A fund manager buys an insurance policy covering losses from employee fidelity breaches. In the '4T' risk-response framework, this is an example of:",
          "Transfer", [("Treat (reduce)", "treating means internal controls that lower likelihood/impact"),
                       ("Tolerate (accept)", "accepting means retaining the risk without action"),
                       ("Terminate (avoid)", "terminating means exiting the activity")],
          ["Insurance shifts the financial consequence to a third party → transfer.", "The underlying risk event still can occur."],
          "4T: Tolerate, Treat, Transfer, Terminate", "Insurance does not reduce likelihood — it transfers loss.", kind="conceptual")

    risks = [("Cyber intrusion", 3, 5), ("Settlement failure", 4, 4), ("Staff attrition", 5, 2), ("Regulatory change", 2, 4), ("Vendor outage", 4, 3)]
    top = max(risks, key=lambda x: x[1] * x[2]); lowest = min(risks, key=lambda x: x[1] * x[2])
    assert top[0] == "Settlement failure" and lowest[0] == "Regulatory change"
    B.add(mri, "L3", "An IFSC broker-dealer scores risks on a 5×5 heat map (score = likelihood × impact):\n\n"
          + table(["Risk", "Likelihood (1–5)", "Impact (1–5)"], [[n, l, i] for n, l, i in risks]) + "\n\nWhich risk should head the mitigation priority list?",
          top[0],
          [("Cyber intrusion", "ranked by impact alone (score 15)"), ("Staff attrition", "ranked by likelihood alone (score 10)"),
           ("Regulatory change", "scale read in reverse — lowest score (8) taken as most severe")],
          ["Scores: " + "; ".join(f"{n} {l}×{i} = {l*i}" for n, l, i in risks) + ".", f"Highest = {top[0]} ({top[1]*top[2]})."],
          "Risk score = Likelihood × Impact", "A single high dimension does not make the top risk.")

    B.add(mri, "L2", "Match the function (List I) with its line in the 'three lines' model of risk governance (List II):\n\n"
          + table(["List I", "List II"], [["A. Trading desk owning and managing its own risks", "1. Third line"], ["B. Risk management and compliance functions", "2. First line"],
                                          ["C. Internal audit giving independent assurance to the board", "3. Second line"]], ["---", "---"]),
          "A-2, B-3, C-1",
          [("A-3, B-2, C-1", "business units and oversight functions swapped"), ("A-2, B-1, C-3", "compliance treated as independent assurance"),
           ("A-1, B-3, C-2", "numbering reversed")],
          ["First line: business/risk owners.", "Second line: risk management, compliance (oversight).", "Third line: internal audit (independent assurance)."],
          "Three lines of defence", "External audit and regulators sit outside the three lines.", kind="conceptual")

    rho2, ss, sf, expo, fcv = 0.9, 0.018, 0.015, 30e7, 25e5
    h = rho2 * ss / sf; n = h * expo / fcv
    assert abs(h - 1.08) < 1e-9
    B.add(mri, "L3", f"An aluminium exporter wants to hedge inventory worth {crore(expo)} with futures (contract value {lakh(fcv)}). The standard deviation of daily spot price changes is {pct(ss,1)}, of futures price changes {pct(sf,1)}, and their correlation is {rho2}. Using the minimum-variance hedge ratio, the number of futures contracts to sell is about:",
          f"{round(n)} contracts",
          [(f"{round(expo/fcv)} contracts", "hedge ratio of 1 assumed"),
           (f"{round(rho2*expo/fcv)} contracts", "correlation used as the hedge ratio"),
           (f"{round(rho2*sf/ss*expo/fcv)} contracts", "volatility ratio inverted (σF/σS)")],
          [f"h* = ρ × σS/σF = {rho2} × {ss*100:.1f}/{sf*100:.1f} = {h:.2f}.", f"N = {h:.2f} × {crore(expo)} ÷ {lakh(fcv)} = {n:.1f} ≈ {round(n)}."],
          "h* = ρ σS/σF; N = h* × Exposure ÷ Contract value", "Hedge ratio can exceed 1 when spot is more volatile than futures.")

    # =============================== Risk-free instruments & risk categories ===============================
    mrf = M("risk-free-instruments-and-risk-categories")
    B.add(mrf, "L1", "The SEBI 'Risk-o-meter' for mutual fund schemes has how many risk levels, and what is the highest level called?",
          "Six levels; 'Very High'",
          [("Five levels; 'High'", "pre-2020 five-level riskometer"), ("Six levels; 'Extremely High'", "wrong label for the top level"),
           ("Four levels; 'Very High'", "wrong number of levels")],
          ["Levels: Low, Low to Moderate, Moderate, Moderately High, High, Very High.", "Evaluated monthly; changes disclosed to unitholders."],
          "Riskometer: 6 levels", "‘Very High’ was added in the 2020 revision.", kind="conceptual", verify_fact=True, ref="SEBI circular on product labelling (Oct 2020)")

    B.add(mrf, "L2", "A debt scheme's potential-risk-class (PRC) matrix places it by maximum Macaulay duration and minimum Credit Risk Value (CRV). The scheme may hold papers up to a Macaulay duration of 2.4 years and its minimum CRV is 11. Its PRC cell is:",
          "B-II",
          [("A-II", "CRV of 11 treated as Class A (needs ≥ 12)"), ("B-III", "duration up to 3 years treated as Class III"),
           ("C-II", "CRV of 11 treated as Class C (that is < 10)")],
          ["Credit risk: Class A CRV ≥ 12; Class B CRV ≥ 10; Class C CRV < 10 → CRV 11 = B.",
           "Interest-rate risk: Class I MD ≤ 1 yr; Class II MD ≤ 3 yrs; Class III any → 2.4 yrs = II."],
          "PRC = Credit class (A/B/C) × Duration class (I/II/III)", "Class is set by the scheme's maximum risk, not current portfolio.",
          verify_fact=True, ref="SEBI circular on Potential Risk Class matrix for debt schemes (June 2021)")

    a, r = ("A 91-day Treasury bill is generally used as the proxy for the risk-free rate in India.",
            "A Treasury bill is free of default risk, reinvestment risk and inflation risk.")
    c, w = ar_opts(2, {0: "accepts R; T-bills carry reinvestment and inflation risk",
                       1: "accepts R as true", 3: "rejects A; T-bills are the standard risk-free proxy"})
    B.add(mrf, "L2", ar_stem(a, r), c, w,
          ["A: sovereign short-dated discount paper → default-free; short tenor minimises interest-rate risk → proxy for risk-free.",
           "R: false — on maturity proceeds must be reinvested at unknown rates, and real return is exposed to inflation."],
          "Risk-free ≈ default-free + short tenor", "‘Risk-free’ is in nominal default terms only.", kind="assertion-reason")

    rf, rm = 0.068, 0.13
    stocks = [("P", 0.40, 1.20), ("Q", 0.35, 0.85), ("R", 0.25, 1.50)]
    bp_ = sum(wt * b for _, wt, b in stocks); er = rf + bp_ * (rm - rf)
    bp_eq = sum(b for _, _, b in stocks) / 3
    B.add(mrf, "L3", f"The 364-day T-bill yield is {pct(rf,1)} and the expected market return {pct(rm,0)}.\n\n"
          + table(["Stock", "Weight", "Beta"], [[n, pct(wt, 0), b] for n, wt, b in stocks]) + "\n\nThe CAPM-expected return on the portfolio is:",
          pct(er),
          [(pct(rf + bp_eq * (rm - rf)), "simple average of betas instead of weighted average"),
           (pct(bp_ * rm), "beta applied to the whole market return (risk-free not separated)"),
           (pct(rf + bp_ * rm), "beta multiplied by market return instead of market risk premium")],
          [f"Portfolio beta = " + " + ".join(f"{wt}×{b}" for _, wt, b in stocks) + f" = {bp_:.4f}.",
           f"E(R) = {pct(rf,1)} + {bp_:.4f} × ({pct(rm,0)} − {pct(rf,1)}) = {pct(er)}."],
          "E(Rp) = Rf + βp (Rm − Rf)", "Beta multiplies the premium, not the market return.")

    # =============================== TVM & Rule of 72 ===============================
    mt = M("time-value-of-money")
    B.add(mt, "L1", "Using the Rule of 72, an investment compounding at 9% per annum will double in approximately:",
          "8 years", [("6.5 years", "Rule of 72 divided by 11 (confuses rate)"), ("11.1 years", "100 ÷ 9 — simple-interest doubling"),
                      ("7.7 years", "Rule of 69 variant misapplied (69 ÷ 9)")],
          ["72 ÷ 9 = 8 years.", f"Exact: ln 2 ÷ ln 1.09 = {math.log(2)/math.log(1.09):.2f} years."],
          "Doubling time ≈ 72 ÷ r(%)", "Simple interest would take 100/r years.", kind="conceptual")

    pm, i, n = 10000, 0.01, 120
    fv = pm * ((1 + i) ** n - 1) / i
    B.add(mt, "L2", f"An investor puts {R(pm)} at the end of every month for 10 years into a scheme earning 12% p.a. compounded monthly. The corpus at the end of 10 years is:",
          R(fv),
          [(R(fv * (1 + i)), "annuity-due formula (investments at beginning of month)"),
           (R(120000 * ((1.12) ** 10 - 1) / 0.12), "annual contributions compounded annually"),
           (R(pm * n * (1 + 0.12 * 10 / 2)), "simple interest on average balance")],
          [f"FV = {inr(pm)} × [(1.01)^120 − 1] ÷ 0.01 = {inr(pm)} × {((1.01)**120-1)/0.01:.4f} = {R(fv)}."],
          "FV (ordinary annuity) = PMT × [(1 + i)^n − 1] ÷ i", "End-of-period payments → ordinary annuity.")

    offers = {"X": (0.096, 12), "Y": (0.0975, 2), "Z": (0.097, 4)}
    ear = {k: (1 + r / m) ** m - 1 for k, (r, m) in offers.items()}
    best = max(ear, key=ear.get)
    assert best == "Z"
    B.add(mt, "L3", "A depositor compares three bank offers:\n\n"
          + table(["Offer", "Nominal rate", "Compounding"], [["X", "9.60%", "Monthly"], ["Y", "9.75%", "Half-yearly"], ["Z", "9.70%", "Quarterly"]])
          + "\n\nOn the basis of effective annual yield, the best offer and its yield are:",
          f"Z; {pct(ear['Z'])}",
          [(f"Y; {pct(ear['Y'])}", "highest nominal rate chosen"),
           (f"X; {pct(ear['X'])}", "most frequent compounding assumed to always win"),
           (f"Z; {pct(0.097)}", "nominal rate quoted as the effective yield")],
          ["EAR = (1 + r/m)^m − 1."] + [f"{k}: {pct(v, 3)}" for k, v in ear.items()],
          "EAR = (1 + r/m)^m − 1", "Compare effective, not nominal, rates.")

    P0, ra, yrs = 25e5, 0.09, 15
    rm_, nm = ra / 12, yrs * 12
    emi = P0 * rm_ * (1 + rm_) ** nm / ((1 + rm_) ** nm - 1)
    ea = P0 * ra * (1 + ra) ** yrs / ((1 + ra) ** yrs - 1) / 12
    B.add(mt, "L3", f"A home loan of {R(P0)} at 9% p.a. (monthly reducing balance) is repayable in equal monthly instalments over {yrs} years. The EMI is:",
          R(emi),
          [(R((P0 + P0 * ra * yrs) / nm), "flat-rate interest on original principal"),
           (R(ea), "annual instalment on annual compounding divided by 12"),
           (R(P0 * ra / 12), "interest-only payment; principal not amortised")],
          [f"r = 9%/12 = 0.75%; n = {nm}.", f"EMI = P r (1+r)^n ÷ [(1+r)^n − 1] = {R(emi)}."],
          "EMI = P r (1+r)^n / [(1+r)^n − 1]", "Flat-rate EMIs overstate the true cost.")

    # =============================== Valuation ratios ===============================
    mv = M("valuation-ratios")
    price, eq, res, prefc, fvv = 360, 50e7, 400e7, 30e7, 10
    shares = eq / fvv; bvps = (eq + res) / shares
    B.add(mv, "L2", f"Balance sheet extract (₹ crore): equity share capital (₹{fvv} shares) 50; reserves and surplus 400; 8% preference share capital 30. The share trades at ₹{price}. The price-to-book ratio is:",
          f"{price/bvps:.2f}x",
          [(f"{price/((eq+res+prefc)/shares):.2f}x", "preference capital included in equity book value"),
           (f"{price/(res/shares):.2f}x", "only reserves used as book value"),
           (f"{price/fvv:.2f}x", "face value used as book value")],
          [f"Shares = 50 crore ÷ ₹{fvv} = {shares/1e7:g} crore.", f"BVPS = (50 + 400) ÷ {shares/1e7:g} = ₹{bvps:g}.", f"P/B = {price} ÷ {bvps:g} = {price/bvps:.2f}x."],
          "P/B = Market price ÷ Book value per equity share", "Preference capital is not equity book value.")

    pat, pbt, prefd, sh, pr = 84, 112, 9, 12.5, 138
    eps = (pat - prefd) / sh
    B.add(mv, "L2", f"A company reports PBT ₹{pbt} crore, PAT ₹{pat} crore and preference dividend ₹{prefd} crore, with {sh} crore equity shares. The share price is ₹{pr}. The P/E ratio is:",
          f"{pr/eps:.2f}x",
          [(f"{pr/(pat/sh):.2f}x", "preference dividend not deducted from earnings"),
           (f"{pr/(pbt/sh):.2f}x", "PBT used instead of earnings to equity"),
           (f"{eps/pr*100:.2f}", "earnings yield (E/P, in %) reported instead of P/E")],
          [f"EPS = ({pat} − {prefd}) ÷ {sh} = ₹{eps:.2f}.", f"P/E = {pr} ÷ {eps:.2f} = {pr/eps:.2f}x."],
          "P/E = Price ÷ EPS; EPS = (PAT − Pref. dividend) ÷ Shares", "Earnings belong to equity only after preference dividend.")

    po, roe, ke = 0.40, 0.15, 0.13
    g = roe * (1 - po); tpe = po * (1 + g) / (ke - g)
    assert abs(g - 0.09) < 1e-12
    B.add(mv, "L3", f"A firm pays out {pct(po,0)} of earnings, earns ROE of {pct(roe,0)} on retained earnings, and its equity investors require {pct(ke,0)}. Using the constant-growth model, its justified trailing P/E is:",
          f"{tpe:.2f}x",
          [(f"{po/(ke-g):.2f}x", "leading (forward) P/E computed instead of trailing"),
           (f"{po*(1+roe*po)/(ke-roe*po):.2f}x", "growth taken as ROE × payout instead of ROE × retention"),
           (f"{1/(ke-g):.2f}x", "payout ratio omitted")],
          [f"g = ROE × b = {pct(roe,0)} × {pct(1-po,0)} = {pct(g,0)}.", f"Trailing P/E = payout × (1 + g) ÷ (ke − g) = {po} × {1+g:.2f} ÷ {ke-g:.2f} = {tpe:.2f}x."],
          "Trailing P/E = D0/E0 × (1 + g) ÷ (ke − g)", "Leading P/E drops the (1 + g) factor.")

    cos = [("P", 30, 25), ("Q", 18, 12), ("R", 24, 24), ("S", 12, 6)]
    peg = sorted(cos, key=lambda x: x[1] / x[2])
    by_pe = sorted(cos, key=lambda x: x[1]); by_g = sorted(cos, key=lambda x: -x[2])
    j = lambda l: ", ".join(x[0] for x in l)
    B.add(mv, "L3", "Four listed peers:\n\n" + table(["Company", "P/E (x)", "Expected EPS growth (% p.a.)"], [[n, p, g_] for n, p, g_ in cos])
          + "\n\nRanked from most to least attractive on the PEG ratio, the order is:",
          j(peg),
          [(j(by_pe), "ranked by P/E alone"), (j(by_g), "ranked by growth alone"), (j(list(reversed(peg))), "PEG ranking reversed (highest PEG first)")],
          ["PEG = P/E ÷ growth: " + "; ".join(f"{n} {p}/{g_} = {p/g_:.2f}" for n, p, g_ in cos) + ".", "Lower PEG = cheaper per unit of growth."],
          "PEG = (P/E) ÷ g(%)", "A low P/E stock can have the worst PEG.")

    # =============================== CASE C5: Options trader ===============================
    L, lotc, F0, Kp5, pp5 = 2, 50, 22000, 21800, 120
    q = L * lotc
    pl_up = (22300 - F0) * q - pp5 * q
    maxloss = (F0 - Kp5 + pp5) * q
    be5 = F0 + pp5
    marg = 0.12 + 0.03; upfront = marg * F0 * q + pp5 * q
    case5 = (f"**Case — Meera's protective hedge.** Meera buys {L} lots of ALPHA50 index futures (lot size {lotc}) at {inr(F0)} and, to protect the position, "
             f"buys {L} lots of the same-expiry {inr(Kp5)} put at ₹{pp5}. The exchange charges SPAN margin of 12% and exposure margin of 3% of the futures contract value; "
             "option premium is paid in full upfront. All positions are held to expiry and settled in cash.")
    B.add(mop, "L4", case5 + "\n\nWhat is Meera's net profit or loss if ALPHA50 settles at 22,300 on expiry?",
          f"Profit of {R(pl_up)}",
          [(f"Profit of {R((22300-F0)*q)}", "put premium ignored"),
           (f"Profit of {R((22300-F0)*q + pp5*q)}", "premium added instead of deducted"),
           (f"Profit of {R((22300-F0)*lotc - pp5*lotc)}", "computed for one lot")],
          [f"Futures: (22,300 − {inr(F0)}) × {q} = {R((22300-F0)*q)}.", f"Put expires worthless; premium = {pp5} × {q} = {R(pp5*q)}.",
           f"Net = {R(pl_up)}."],
          "P&L = Futures gain + Put payoff − Premium", "The hedge costs the premium in rising markets.",
          kind="case", group="C5-MEERA-HEDGE")
    B.add(mop, "L4", case5 + "\n\nWhat is the maximum loss Meera can suffer on the combined position?",
          R(maxloss),
          [(R((F0 - Kp5) * q), "premium omitted from maximum loss"),
           (R(pp5 * q), "only premium treated as maximum loss (as for a naked long put)"),
           ("Unlimited", "the long put caps the downside of the long futures")],
          [f"Below {inr(Kp5)}, futures loss beyond {inr(Kp5)} is offset by the put.", f"Max loss = ({inr(F0)} − {inr(Kp5)} + {pp5}) × {q} = {R(maxloss)}."],
          "Max loss = (F0 − K + Premium) × Quantity", "The floor = strike − premium on a per-unit basis.",
          kind="case", group="C5-MEERA-HEDGE")
    B.add(mop, "L4", case5 + "\n\nAt what expiry level of ALPHA50 does Meera break even?",
          inr(be5),
          [(inr(Kp5 + pp5), "break-even measured from the put strike"),
           (inr(F0 - pp5), "premium subtracted instead of added"),
           (inr(Kp5 - pp5), "break-even of a naked long put")],
          [f"Upside needs to recover the premium: {inr(F0)} + {pp5} = {inr(be5)}."],
          "BE = F0 + Put premium", "A protective put shifts break-even up by the premium.",
          kind="case", group="C5-MEERA-HEDGE")
    B.add(mg, "L4", case5 + "\n\nWhat total amount must Meera deploy upfront at initiation?",
          R(upfront),
          [(R(marg * F0 * q), "option premium omitted"),
           (R(0.12 * F0 * q + pp5 * q), "exposure margin omitted"),
           (R(marg * F0 * lotc + pp5 * lotc), "computed for one lot of each")],
          [f"Futures contract value = {inr(F0)} × {q} = {R(F0*q)}; margin 15% = {R(marg*F0*q)}.", f"Premium = {R(pp5*q)}.", f"Total = {R(upfront)}."],
          "Upfront = (SPAN + ELM) × Contract value + Option premium", "Long options need premium, not margin.",
          kind="case", group="C5-MEERA-HEDGE")

    # =============================== CASE C6: Bank risk dashboard ===============================
    Nn, fxr, flr, dd = 200e7, 0.074, 0.069, 181
    netc = Nn * (fxr - flr) * dd / 365
    segs = [("Corporate", 380, 0.022, 0.50), ("MSME", 90, 0.060, 0.60), ("Retail", 450, 0.015, 0.35)]
    elc = sum(e * p * l for _, e, p, l in segs)
    gi = [310, -40, 470]
    bia = 0.15 * sum(x for x in gi if x > 0) / len([x for x in gi if x > 0])
    tb6 = table(["Segment", "EAD (₹ cr)", "PD", "LGD"], [[n, e, pct(p, 1), pct(l, 0)] for n, e, p, l in segs])
    case6 = (f"**Case — Coastal Finance Bank risk dashboard.** (i) The bank receives fixed {pct(fxr,1)} and pays floating on a ₹200 crore interest rate swap, "
             f"semi-annual, Actual/365; the floating rate fixed for the current {dd}-day period is {pct(flr,1)}. (ii) Its loan book is:\n\n{tb6}\n\n"
             f"(iii) Annual gross income for the last three years was ₹{gi[0]} crore, ₹{gi[1]} crore and ₹{gi[2]} crore. The bank uses the Basic Indicator Approach (alpha 15%) for operational risk.")
    B.add(msw, "L4", case6 + "\n\nWhat is the net swap settlement for the current period?",
          f"Bank receives {R(netc)}",
          [(f"Bank pays {R(netc)}", "direction reversed: fixed receiver gains when fixed > floating"),
           (f"Bank receives {R(Nn*(fxr-flr))}", "annual differential without day-count"),
           (f"Bank receives {R(Nn*fxr*dd/365)}", "gross fixed leg reported instead of net")],
          [f"Differential = {pct(fxr,1)} − {pct(flr,1)} = {pct(fxr-flr,1)}.", f"Net = 200 crore × {fxr-flr:.3f} × {dd}/365 = {R(netc)} received."],
          "Net = N × (Fixed − Floating) × d/365", "Identify whether the bank is fixed payer or receiver.",
          kind="case", group="C6-COASTAL-RISK")
    B.add(mrk, "L4", case6 + "\n\nWhat is the expected credit loss of the loan book?",
          f"₹{elc:.2f} crore",
          [(f"₹{sum(e*p for _, e, p, _ in segs):.2f} crore", "LGD ignored (PD × EAD only)"),
           (f"₹{sum(e*p*(1-l) for _, e, p, l in segs):.2f} crore", "recovery rate (1 − LGD) used instead of LGD"),
           (f"₹{sum(e for _, e, _, _ in segs)*sum(p for _, _, p, _ in segs)/3*sum(l for _, _, _, l in segs)/3:.2f} crore", "simple averages of PD and LGD applied to total EAD")],
          ["EL = Σ EAD × PD × LGD:"] + [f"{n}: {e} × {p} × {l} = {e*p*l:.3f}" for n, e, p, l in segs] + [f"Total = ₹{elc:.2f} crore."],
          "EL = Σ PD × LGD × EAD", "Segment-level EL must be computed before summing.",
          kind="case", group="C6-COASTAL-RISK")
    B.add(mrk, "L4", case6 + "\n\nWhat is the operational-risk capital charge under the Basic Indicator Approach?",
          f"₹{bia:.2f} crore",
          [(f"₹{0.15*sum(gi)/3:.2f} crore", "negative year included in the average"),
           (f"₹{0.15*sum(x for x in gi if x>0)/3:.2f} crore", "negative year excluded from numerator but still counted in the denominator"),
           (f"₹{0.15*gi[-1]:.2f} crore", "latest year's gross income only")],
          [f"Positive years: {gi[0]} and {gi[2]} → average = {(gi[0]+gi[2])/2:g}.", f"Charge = 15% × {(gi[0]+gi[2])/2:g} = ₹{bia:.2f} crore."],
          "K_BIA = α × average positive annual gross income (3 yrs)", "Negative/zero years drop out of numerator AND denominator.",
          kind="case", group="C6-COASTAL-RISK", verify_fact=True, ref="BCBS Basel II — Basic Indicator Approach (para 649)")
    worst = max(segs, key=lambda s: s[1] * s[2] * s[3])
    B.add(mri, "L4", case6 + "\n\nThe risk committee wants to cut expected credit loss most effectively by buying credit protection on one segment. Which segment should it target, and why?",
          f"{worst[0]}, because it contributes the largest expected loss (₹{worst[1]*worst[2]*worst[3]:.2f} crore)",
          [("Retail, because it has the largest EAD", "exposure size alone ignores PD and LGD"),
           ("Retail, because it has the lowest LGD and is cheapest to protect", "cheapness of protection is not the EL-reduction criterion"),
           ("MSME, because it has the highest PD", "PD alone does not rank expected loss")],
          ["Segment EL: " + "; ".join(f"{n} ₹{e*p*l:.2f} cr" for n, e, p, l in segs) + ".", f"Largest EL = {worst[0]} → transferring its risk gives the biggest reduction."],
          "Prioritise mitigation by EL contribution", "Rank by PD × LGD × EAD, not by any single component.",
          kind="case", group="C6-COASTAL-RISK")
    assert worst[0] == "Corporate"
