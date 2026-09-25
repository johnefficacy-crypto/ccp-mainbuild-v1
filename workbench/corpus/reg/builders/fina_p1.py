"""FIN-A part 1: fixed income, derivatives, currency risk, active/passive. Case sets C1 (bond book), C4 (derivatives desk), C8 (exporter FX)."""
import math, statistics
from reglib import inr, R, pct, lakh, crore
from fina_util import bond_price, ytm, mac_duration, solve, table, f2

BY = "fin-bond-yield-and-pricing-d8b6d50e"
CL = "fin-callable-and-puttable-securities-f888d9aa"
DC = "fin-day-count-conventions-468761e5"
FF = "fin-fixed-vs-floating-rate-securities-3be5a34d"
FP = "fin-forward-pricing-and-cost-of-carry-3de99e51"
CB = "fin-contango-and-backwardation-591fb9ff"
FU = "fin-forwards-vs-futures-234bb6d4"
HG = "fin-hedging-vs-arbitrage-vs-speculation-29034d21"
CDS = "fin-credit-default-swaps-7725a2ef"
CR = "fin-currency-risk-and-settlement-risk-b4c402da"
AP = "fin-active-vs-passive-investment-strategies-9a451e96"


def add_all(B):
    A = B.add

    # ================= BOND YIELD AND PRICING =================
    A(BY, "L1",
      "Other things remaining the same, which of the following bonds will show the LARGEST percentage price change for a 50 bp rise in market yield?",
      "A 15-year zero-coupon bond",
      [("A 15-year bond paying a 9% annual coupon", "higher coupon shortens duration — less sensitive than the zero"),
       ("A 5-year zero-coupon bond", "zero-coupon, but shorter maturity means lower duration"),
       ("A 15-year floating-rate note reset every six months", "FRN duration is roughly the time to next reset")],
      ["Price sensitivity is measured by (modified) duration.",
       "For a given maturity, a zero-coupon bond has the highest duration (equal to its maturity).",
       "Longer maturity raises duration; a 15-year zero therefore beats a 15-year coupon bond and a 5-year zero.",
       "An FRN re-prices to near par at each reset, so its duration is only about 0.5 years."],
      "%ΔP ≈ −Modified duration × Δy",
      "Maturity alone does not decide sensitivity — coupon size and reset features matter.", kind="conceptual")

    F, c, y, n = 1000, 0.075, 0.082, 5
    p = bond_price(F, c, y, n)
    p_semi = bond_price(F, c, y, n, 2)
    p_mix = sum(F * c / (1 + y) ** t for t in range(1, n + 1)) + F / (1 + c) ** n
    p_cur = F * c / y  # perpetuity treatment
    assert 970 < p < 975
    A(BY, "L2",
      f"A bond of face value ₹{inr(F)} carries a {pct(c)} coupon payable annually and has {n} years to maturity. It is redeemable at par. If the market yield on comparable bonds is {pct(y)}, the bond's price is closest to:",
      R(p, 2),
      [(R(p_semi, 2), "semi-annual compounding applied to an annual-coupon bond"),
       (R(p_mix, 2), "redemption value discounted at the coupon rate instead of the yield"),
       (R(p_cur, 2), "coupon capitalised as a perpetuity (C ÷ y), maturity ignored")],
      [f"Annual coupon = {inr(F)} × {pct(c)} = ₹{F*c:.2f}",
       f"PV of coupons = {F*c:.2f} × annuity factor (8.2%, 5 yrs) = ₹{sum(F*c/(1+y)**t for t in range(1,n+1)):.2f}",
       f"PV of redemption = {inr(F)} ÷ 1.082⁵ = ₹{F/(1+y)**n:.2f}",
       f"Price = ₹{p:.2f} (below par since yield > coupon)"],
      "P = Σ C/(1+y)ᵗ + F/(1+y)ⁿ",
      "All cash flows — including redemption — are discounted at the market yield, with the bond's own payment frequency.")

    P0, F, c = 96.40, 100, 0.0715
    cy = F * c / P0
    A(BY, "L2",
      f"A ₹{F} face value bond with a {pct(c)} annual coupon is quoted at ₹{P0:.2f}. Its current yield is:",
      pct(cy),
      [(pct(c), "coupon rate taken as current yield"),
       (pct(P0 * c / F / 100 * 100 / 100 if False else (F * c / F) * (P0 / F)), "coupon rate scaled by price/face instead of face/price"),
       (pct((F * c + (F - P0)) / P0), "full pull-to-par gain added in one year")],
      [f"Annual coupon = ₹{F*c:.2f}",
       f"Current yield = {F*c:.2f} ÷ {P0:.2f} = {pct(cy)}"],
      "Current yield = Annual coupon ÷ Market price",
      "Current yield ignores the capital gain to maturity — it is not YTM.")

    F, c, P0, n = 1000, 0.08, 945, 6
    C = F * c
    approx = (C + (F - P0) / n) / ((F + P0) / 2)
    exact = ytm(P0, F, c, n)
    A(BY, "L3",
      f"A {n}-year, {pct(c)} annual-coupon bond (face ₹{inr(F)}, redeemable at par) trades at ₹{inr(P0)}. Using the standard approximation formula, its yield to maturity is closest to:",
      pct(approx),
      [(pct((C + (F - P0) / n) / P0), "denominator taken as market price instead of average of face and price"),
       (pct((C - (F - P0) / n) / ((F + P0) / 2)), "discount amortisation subtracted instead of added"),
       (pct((C + (F - P0) / n) / F), "denominator taken as face value")],
      [f"Annual coupon = ₹{inr(C)}; discount amortised per year = ({inr(F)} − {inr(P0)}) ÷ {n} = ₹{(F-P0)/n:.2f}",
       f"Average investment = ({inr(F)} + {inr(P0)}) ÷ 2 = ₹{(F+P0)/2:.1f}",
       f"Approx. YTM = {C+(F-P0)/n:.2f} ÷ {(F+P0)/2:.1f} = {pct(approx)}",
       f"(Exact IRR check: {pct(exact)} — the approximation is close.)"],
      "YTM ≈ [C + (F − P)/n] ÷ [(F + P)/2]",
      "A discount bond's YTM exceeds its coupon; the gain to par is added, not subtracted.")

    F, c, y, n = 1000, 0.08, 0.10, 4
    D = mac_duration(F, c, y, n)
    pv = [(t, (F * c + (F if t == n else 0)) / (1 + y) ** t) for t in range(1, n + 1)]
    Pn = sum(v for _, v in pv)
    und = sum(t * (F * c + (F if t == n else 0)) for t in range(1, n + 1)) / sum(F * c + (F if t == n else 0) for t in range(1, n + 1))
    rows = [[str(t), inr(F * c + (F if t == n else 0)), f"{1/(1+y)**t:.4f}", f"{v:.2f}"] for t, v in pv]
    assert abs(D - 3.5616) < 0.01
    A(BY, "L3",
      f"A 4-year bond of face ₹{inr(F)} pays an {pct(c)} coupon annually; market yield is {pct(y)}.\n\n"
      + table(["Year", "Cash flow (₹)", "PV factor @10%", "PV (₹)"], rows) +
      "\n\nThe bond's Macaulay duration is closest to:",
      f"{D:.2f} years",
      [(f"{D/(1+y):.2f} years", "modified duration reported instead of Macaulay"),
       (f"{und:.2f} years", "cash flows weighted without discounting"),
       (f"{n:.2f} years", "duration taken equal to maturity (true only for a zero-coupon bond)")],
      [f"Price = Σ PV = ₹{Pn:.2f}",
       "Σ t × PV = " + " + ".join(f"{t}×{v:.2f}" for t, v in pv) + f" = {sum(t*v for t,v in pv):.2f}",
       f"Macaulay duration = {sum(t*v for t,v in pv):.2f} ÷ {Pn:.2f} = {D:.2f} years"],
      "D = Σ [t × PV(CFₜ)] ÷ Price",
      "Weights must be present values; modified duration = D/(1+y) is a different measure.")

    MD, CX, dy = 6.20, 52.0, 0.0075
    ch = -MD * dy + 0.5 * CX * dy ** 2
    A(BY, "L3",
      f"A bond has modified duration of {MD} and convexity of {CX:.0f}. If its yield rises by {dy*1e4:.0f} basis points, the estimated percentage change in price (duration + convexity) is:",
      f"{ch*100:.3f}%",
      [(f"{-MD*dy*100:.3f}%", "convexity adjustment ignored"),
       (f"{(-MD*dy - 0.5*CX*dy**2)*100:.3f}%", "convexity adjustment subtracted (sign reversed)"),
       (f"{(-MD*dy + CX*dy**2)*100:.3f}%", "½ factor omitted from convexity term")],
      [f"Duration effect = −{MD} × {dy} = {-MD*dy*100:.3f}%",
       f"Convexity effect = ½ × {CX:.0f} × {dy}² = +{0.5*CX*dy**2*100:.3f}%",
       f"Total ≈ {ch*100:.3f}%"],
      "%ΔP ≈ −MD·Δy + ½·Convexity·(Δy)²",
      "Positive convexity always adds to price, whether yields rise or fall.")

    F, y, n = 100, 0.072, 6
    pz = F / (1 + y / 2) ** (2 * n)
    A(BY, "L2",
      f"A zero-coupon STRIP of face ₹{F} matures in {n} years. Using the market convention of semi-annual compounding, at a yield of {pct(y)} p.a. its price is:",
      R(pz, 2),
      [(R(F / (1 + y) ** n, 2), "annual compounding used"),
       (R(F / (1 + y * n), 2), "simple interest discounting"),
       (R(F / (1 + y / 2) ** n, 2), "half-yearly rate applied for only 6 periods")],
      [f"Periods = {n} × 2 = {2*n}; periodic rate = {pct(y/2)}",
       f"Price = 100 ÷ (1.036)¹² = ₹{pz:.2f}"],
      "P = F ÷ (1 + y/2)^(2n)",
      "Match the number of periods to the compounding frequency.")

    A(BY, "L1",
      "Consider the following statements about yield to maturity (YTM):\n\n"
      "1. YTM is the internal rate of return of the bond's promised cash flows at the current market price.\n"
      "2. The investor realises the YTM only if all coupons are reinvested at the YTM and the bond is held to maturity without default.\n"
      "3. For a bond trading at a premium, YTM is higher than the current yield.\n\nWhich of the statements given above is/are correct?",
      "1 and 2 only",
      [("1 only", "misses the reinvestment/hold-to-maturity assumption"),
       ("1, 2 and 3", "premium bond: YTM < current yield < coupon"),
       ("2 and 3 only", "statement 3 is wrong; statement 1 is the definition")],
      ["Statement 1: definition of YTM — correct.",
       "Statement 2: realised yield equals YTM only under those assumptions — correct.",
       "Statement 3: premium bond ⇒ coupon > current yield > YTM, so it is wrong."],
      "Premium: coupon > CY > YTM; Discount: coupon < CY < YTM",
      "The ordering of coupon, current yield and YTM flips between premium and discount bonds.", kind="statement")

    F, c, n, rr = 1000, 0.08, 3, 0.06
    fv = sum(F * c * (1 + rr) ** (n - t) for t in range(1, n + 1)) + F
    rcy = (fv / F) ** (1 / n) - 1
    A(BY, "L3",
      f"An investor buys a {n}-year, {pct(c)} annual-coupon bond at par (₹{inr(F)}) and holds it to maturity. Each coupon can be reinvested only at {pct(rr)} p.a. The investor's realised compound yield is closest to:",
      pct(rcy),
      [(pct(c), "YTM taken as realised yield — reinvestment shortfall ignored"),
       (pct(((F * c * n + F) / F) ** (1 / n) - 1), "interest-on-interest ignored (coupons not reinvested)"),
       (pct((c + rr) / 2), "simple average of coupon rate and reinvestment rate")],
      [f"FV of coupons at 6%: 80×1.06² + 80×1.06 + 80 = ₹{fv-F:.2f}",
       f"Terminal value = {fv-F:.2f} + {inr(F)} = ₹{fv:.2f}",
       f"Realised yield = ({fv:.2f} ÷ {inr(F)})^(1/3) − 1 = {pct(rcy)}"],
      "RCY = (Terminal value ÷ Price)^(1/n) − 1",
      "Reinvestment below YTM drags the realised return below YTM even for a par bond.")

    # ================= CALLABLE / PUTTABLE =================
    A(CL, "L1",
      "Which of the following correctly describes a callable bond relative to an otherwise identical option-free bond?",
      "Its price is the option-free price minus the issuer's call value, and it shows negative convexity at low yields",
      [("Its price equals the option-free price plus the call option value, since the investor holds the option", "call option belongs to the issuer, not the investor"),
       ("Its price rises faster than the option-free bond when yields fall, because the call caps the investor's losses", "price compression near call price — gains are capped, not enhanced"),
       ("It must offer a lower yield than the option-free bond because the investor can redeem it before maturity", "describes a puttable bond; callable bonds offer a higher yield")],
      ["The issuer holds the right to redeem early, so the investor is short a call.",
       "Callable price = Straight bond − Call value.",
       "As yields fall the price is capped near the call price → negative convexity."],
      "P(callable) = P(straight) − C; P(puttable) = P(straight) + Put",
      "Who holds the option decides the sign.", kind="conceptual")

    ps, cv, pv_ = 1042.60, 18.35, 11.20
    both = ps - cv + pv_
    A(CL, "L2",
      f"An option-free bond is valued at ₹{ps:,.2f}. An otherwise identical bond carries both an issuer call option (valued at ₹{cv:.2f}) and an investor put option (valued at ₹{pv_:.2f}). Ignoring interaction between the options, the value of the bond with both options is:",
      R(both, 2),
      [(R(ps + cv - pv_, 2), "signs of both options reversed"),
       (R(ps - cv - pv_, 2), "put option also treated as reducing value"),
       (R(ps + cv + pv_, 2), "both options added to straight value")],
      [f"Investor is short the call: −{cv:.2f}",
       f"Investor is long the put: +{pv_:.2f}",
       f"Value = {ps:,.2f} − {cv:.2f} + {pv_:.2f} = ₹{both:,.2f}"],
      "V = Straight − Call + Put",
      "The call benefits the issuer; the put benefits the holder.")

    F, c, P0, n, kc, nc = 100, 0.09, 108.00, 10, 103.0, 4
    y_m = ytm(P0, F, c, n)
    y_c = ytm(P0, F, c, nc, redemption=kc)
    y_c_face = ytm(P0, F, c, nc)
    ap = (F * c + (kc - P0) / nc) / ((kc + P0) / 2)
    assert y_c < y_m
    A(CL, "L3",
      f"A {n}-year, {pct(c)} annual-coupon bond (face ₹{F}) trades at ₹{P0:.2f}. It is callable at ₹{kc:.0f} at the end of year {nc}. Its yield to call (exact IRR basis) is closest to:",
      pct(y_c),
      [(pct(y_m), "yield to maturity reported (call feature ignored)"),
       (pct(y_c_face), "redemption at face ₹100 instead of the call price ₹103"),
       (pct(ap - 0.0012), "approximation with call premium omitted from amortisation")],
      [f"Cash flows to call: ₹9 for years 1–{nc} plus ₹{kc:.0f} at year {nc}",
       f"Solve 108 = Σ 9/(1+y)ᵗ + 103/(1+y)⁴ → y = {pct(y_c)}",
       f"YTM over 10 years = {pct(y_m)}; yield-to-worst = lower of the two = YTC"],
      "P = Σ C/(1+y)ᵗ + Call price/(1+y)ᵏ",
      "For a premium callable bond the YTC is usually the yield-to-worst.")
    # patch last distractor to a clean named error (approx YTC with face amortisation)
    last = B.Q[-1]
    last["_wrongs"][2] = (pct((F * c + (F - P0) / nc) / ((F + P0) / 2)), "approximation formula using face ₹100 instead of call price")
    assert len(set([last["_correct"]] + [w[0] for w in last["_wrongs"]])) == 4

    A(CL, "L2",
      "**Assertion (A):** When market yields fall sharply, the price of a puttable bond rises roughly in line with an otherwise identical option-free bond.\n\n"
      "**Reason (R):** The put option gains value mainly when yields rise, putting a floor under the bond's price.\n\nChoose the correct option:",
      "Both A and R are true, and R correctly explains A",
      [("Both A and R are true, but R does not explain A", "R is precisely why the put is nearly worthless at low yields"),
       ("Only A is true; R is a false statement of fact", "R correctly states when the put is valuable"),
       ("Only R is true; A is a false statement of fact", "confuses puttable with callable (price compression is a callable feature)")],
      ["At low yields the put is deep out-of-the-money and adds little value, so the puttable bond behaves like a straight bond.",
       "At high yields the put floors the price near the put price.",
       "Hence R explains A."],
      "P(puttable) = P(straight) + Put value",
      "Price compression at low yields belongs to callable, not puttable bonds.", kind="assertion-reason")

    # ================= DAY COUNT =================
    A(DC, "L2",
      "Match the instrument (List I) with the day-count convention generally applied in the Indian market (List II):\n\n"
      + table(["List I — Instrument", "List II — Convention"],
              [["P. Government of India dated securities", "1. Actual/364 (discount basis)"],
               ["Q. Treasury bills", "2. 30/360"],
               ["R. Commercial paper and certificates of deposit", "3. Actual/365"],
               ["S. Listed corporate bonds (SEBI framework)", "4. Actual/Actual"]], ["---", "---"]) +
      "\n\nCodes:",
      "P-2, Q-1, R-3, S-4",
      [("P-4, Q-1, R-3, S-2", "G-sec and corporate bond conventions swapped"),
       ("P-2, Q-3, R-1, S-4", "T-bill and money-market (CP/CD) conventions swapped"),
       ("P-3, Q-1, R-2, S-4", "G-secs taken as Actual/365")],
      ["G-secs: 30/360 for accrued interest.",
       "T-bills: yield on Actual/364 discount basis.",
       "CP/CD and money market: Actual/365.",
       "Corporate bonds: Actual/Actual under SEBI's day-count circular (366 in leap years)."],
      "Convention matters for accrued interest and yield computation",
      "Only G-secs use 30/360; money-market paper uses actual days.", kind="match", verify_fact=True,
      ref="FIMMDA/RBI market conventions for G-secs & T-bills; SEBI circular on day count convention for debt securities (2013)")

    face, c = 100, 0.0718
    d30 = (10 - 7) * 30 + (3 - 14)
    dact = 17 + 31 + 30 + 3
    ai = face * c * d30 / 360
    assert d30 == 79 and dact == 81
    A(DC, "L2",
      f"A GoI dated security with a {pct(c)} coupon pays interest half-yearly on 14 January and 14 July. A trade settles on 3 October. Using the 30/360 convention, the accrued interest per ₹100 face value is:",
      f"₹{ai:.4f}",
      [(f"₹{face*c*dact/365:.4f}", "actual days (81) on Actual/365 basis"),
       (f"₹{face*c*dact/360:.4f}", "actual days (81) on a 360-day year"),
       (f"₹{face*c*d30/365:.4f}", "30/360 day count but divided by 365")],
      ["30/360 days from 14 Jul to 3 Oct = (10 − 7) × 30 + (3 − 14) = 79 days",
       f"Accrued = 100 × 7.18% × 79/360 = ₹{ai:.4f}"],
      "AI = Face × Coupon × Days(30/360) ÷ 360",
      "Count days the 30/360 way and divide by 360 — never mix conventions.",
      verify_fact=True, ref="30/360 convention for GoI dated securities (FIMMDA / RBI)")

    P91, days = 98.2750, 91
    yt = (100 - P91) / P91 * 364 / days
    A(DC, "L2",
      f"A {days}-day Treasury bill is allotted at a price of ₹{P91:.4f} per ₹100. Its annualised yield is:",
      f"{yt*100:.4f}%",
      [(f"{(100-P91)/P91*365/days*100:.4f}%", "Actual/365 used instead of 364"),
       (f"{(100-P91)/100*364/days*100:.4f}%", "discount on face value (discount rate) instead of yield on price"),
       (f"{(100-P91)/P91*360/days*100:.4f}%", "360-day year used")],
      [f"Discount = 100 − {P91:.4f} = {100-P91:.4f}",
       f"Yield = {100-P91:.4f} ÷ {P91:.4f} × 364/91 = {yt*100:.4f}%"],
      "T-bill yield = (100 − P)/P × 364/d",
      "Divide by price (not face) and annualise on 364 days.",
      verify_fact=True, ref="RBI T-bill yield convention (364-day year)")

    fv, cp, c = 5e7, 99.25, 0.0695
    d30 = (11 - 8) * 30 + (28 - 15)
    ai = c * 100 * d30 / 360
    inv = fv / 100 * (cp + ai)
    assert d30 == 103
    A(DC, "L3",
      f"A bank buys ₹5 crore face value of a {pct(c)} GoI security (coupon dates 15 February and 15 August) at a clean price of ₹{cp:.2f}, for settlement on 28 November. Under market conventions, the consideration payable is:",
      R(inv, 0),
      [(R(fv / 100 * cp, 0), "clean price paid — accrued interest omitted"),
       (R(fv / 100 * (cp + c * 100 * 105 / 365), 0), "accrued on actual days (105) / 365"),
       (R(fv / 100 * (cp - ai), 0), "accrued interest deducted from clean price")],
      [f"30/360 days 15 Aug → 28 Nov = 3×30 + (28 − 15) = {d30}",
       f"Accrued per ₹100 = 6.95 × {d30}/360 = ₹{ai:.4f}",
       f"Dirty price = {cp:.2f} + {ai:.4f} = {cp+ai:.4f}",
       f"Consideration = ₹5 crore × {cp+ai:.4f}% = {R(inv)}"],
      "Dirty price = Clean price + Accrued interest",
      "Settlement is on the dirty (full) price.",
      verify_fact=True, ref="30/360 convention for GoI dated securities")

    # ================= FIXED vs FLOATING =================
    A(FF, "L1",
      "Immediately after a coupon reset date, a plain floating-rate note whose quoted spread equals the market-required spread will typically:",
      "Trade close to par, with an interest-rate duration roughly equal to the time to the next reset",
      [("Trade at a premium, with duration equal to its residual maturity", "treats FRN like a fixed-coupon bond"),
       ("Trade at a discount, because floating coupons are uncertain", "coupon uncertainty does not cause a discount if spread = required spread"),
       ("Trade at par, but with duration greater than a fixed-rate bond of the same maturity", "floating resets shorten duration, not lengthen it")],
      ["At each reset the coupon moves to the market rate, so PV returns to about par.",
       "Rate risk exists only until the next reset, so duration ≈ time to reset.",
       "Credit-spread changes (not benchmark changes) can still move the price."],
      "FRN price ≈ par at reset if quoted margin = required margin",
      "FRNs carry low interest-rate risk but still carry spread (credit) risk.", kind="conceptual")

    yl = [0.0692, 0.0685, 0.0699]
    spread, face = 0.0122, 1e8
    base = sum(yl) / 3
    cpn = base + spread
    half = face * cpn / 2
    A(FF, "L2",
      "A floating rate bond's coupon for each half-year is set as: base rate = simple average of the cut-off yields of the last three auctions of 182-day T-bills, plus a fixed spread of 1.22%. The last three auction cut-offs were 6.92%, 6.85% and 6.99%. The coupon amount for the half-year on a holding of ₹10 crore face value is:",
      R(half, 0),
      [(R(face * cpn, 0), "annual coupon rate applied to a half-year"),
       (R(face * (yl[-1] + spread) / 2, 0), "only the latest auction yield taken as base"),
       (R(face * base / 2, 0), "fixed spread omitted")],
      [f"Base = (6.92 + 6.85 + 6.99) ÷ 3 = {base*100:.4f}%",
       f"Coupon rate = {base*100:.4f} + 1.22 = {cpn*100:.4f}% p.a.",
       f"Half-year coupon = ₹10 crore × {cpn*100:.4f}% ÷ 2 = {R(half)}"],
      "Coupon = Base (benchmark average) + Spread; periodic = annual ÷ 2",
      "Rate is annual; pay-out is half-yearly.")

    col, fl, inv_, M, sp = 0.08, 60, 40, 0.062, 0.005
    ic = (col * 100 - fl * (M + sp)) / inv_
    A(FF, "L3",
      f"An issuer carves a ₹100 crore, {pct(col)} fixed-rate bond pool into two tranches: ₹{fl} crore of floaters paying MIBOR + {sp*100:.2f}% and ₹{inv_} crore of inverse floaters that absorb the balance of the pool's interest. If MIBOR is {pct(M)}, the coupon on the inverse floater is:",
      pct(ic),
      [(pct((col * 100 - fl * M) / inv_), "floater spread ignored"),
       (pct((col * 100 - fl * (M + sp)) / fl), "residual interest divided by floater size"),
       (pct(col - M + col), "rule-of-thumb 2×fixed − MIBOR (weights ignored)")],
      [f"Pool interest = 8% × 100 = ₹8.00 crore",
       f"Floater interest = 60 × ({M*100:.1f} + 0.50)% = ₹{fl*(M+sp):.2f} crore",
       f"Inverse floater gets ₹{col*100 - fl*(M+sp):.2f} crore on ₹40 crore = {pct(ic)}"],
      "Inverse coupon = (Pool interest − Floater interest) ÷ Inverse tranche",
      "Inverse floaters have leverage: coupon falls 1.5 pp for every 1 pp rise in MIBOR here.")

    # ================= FORWARD PRICING =================
    A(FP, "L1",
      "Consider the following statements on the cost-of-carry model for financial futures:\n\n"
      "1. The fair futures price equals spot price plus carrying cost minus carry return (such as dividends) to expiry.\n"
      "2. If the market futures price exceeds the fair price, an arbitrageur buys spot and sells futures.\n"
      "3. Higher expected dividends during the life of a stock futures contract raise its fair price.\n\nWhich of the statements given above is/are correct?",
      "1 and 2 only",
      [("1 only", "statement 2 describes cash-and-carry arbitrage correctly"),
       ("2 and 3 only", "dividends are carry return — they reduce the fair price"),
       ("1, 2 and 3", "statement 3 reverses the effect of dividends")],
      ["Fair F = S + cost of carry − carry return — correct.",
       "Futures overpriced → buy spot, sell futures (cash-and-carry) — correct.",
       "Dividends reduce the fair futures price — statement 3 wrong."],
      "F = S + Carry cost − Carry return",
      "Income on the underlying is a deduction from carry.", kind="statement")

    S, r, T, D, td = 2450, 0.07, 0.25, 30, 2 / 12
    pvD = D * math.exp(-r * td)
    Fv = (S - pvD) * math.exp(r * T)
    A(FP, "L2",
      f"A stock trades at ₹{inr(S)}. A dividend of ₹{D} is expected in 2 months. The continuously compounded risk-free rate is {pct(r)}. The fair price of a 3-month forward on the stock is:",
      R(Fv, 2),
      [(R(S * math.exp(r * T), 2), "dividend ignored"),
       (R((S - D) * math.exp(r * T), 2), "dividend deducted without discounting"),
       (R((S + pvD) * math.exp(r * T), 2), "PV of dividend added instead of deducted")],
      [f"PV of dividend = 30 × e^(−0.07×2/12) = ₹{pvD:.4f}",
       f"F = ({inr(S)} − {pvD:.4f}) × e^(0.07×0.25) = ₹{Fv:.2f}"],
      "F = (S − PV(D)) × e^(rT)",
      "Deduct the present value of income, then carry forward.")

    S, r, q, T = 24500, 0.068, 0.014, 0.25
    Fi = S * math.exp((r - q) * T)
    A(FP, "L2",
      f"An equity index stands at {inr(S)}. The risk-free rate is {pct(r, 1)} and the index dividend yield is {pct(q, 1)} p.a., both continuously compounded. The theoretical price of a 3-month index future is:",
      f"{Fi:,.2f}",
      [(f"{S*math.exp(r*T):,.2f}", "dividend yield ignored"),
       (f"{S*math.exp((r+q)*T):,.2f}", "dividend yield added to the financing rate"),
       (f"{S*math.exp((r-q)):,.2f}", "annual carry applied to a 3-month contract")],
      [f"Net carry = {pct(r,1)} − {pct(q,1)} = {pct(r-q,1)}",
       f"F = {inr(S)} × e^({r-q:.3f}×0.25) = {Fi:,.2f}"],
      "F = S × e^((r − q)T)", "Scale carry by time to expiry.")

    S, r, T, Fm, ntc = 1860, 0.072, 2 / 12, 1895, 0
    fair = S * math.exp(r * T)
    prof = Fm - fair
    A(FP, "L3",
      f"A non-dividend-paying share trades at ₹{inr(S)}; its 2-month futures trades at ₹{inr(Fm)}. The continuously compounded risk-free rate is {pct(r)}. Ignoring transaction costs, the arbitrage strategy and profit per share at expiry are:",
      f"Buy spot, sell futures; profit ₹{prof:.2f}",
      [(f"Sell spot, buy futures; profit ₹{prof:.2f}", "direction reversed — futures is overpriced, not underpriced"),
       (f"Buy spot, sell futures; profit ₹{Fm-S:.2f}", "financing cost of holding spot ignored"),
       (f"Buy spot, sell futures; profit ₹{(Fm-fair)*math.exp(-r*T):.2f}", "profit discounted to today, not at expiry")],
      [f"Fair F = {inr(S)} × e^(0.072×2/12) = ₹{fair:.2f}",
       f"Market F {inr(Fm)} > fair ⇒ futures overpriced ⇒ cash-and-carry",
       f"Profit at expiry = {inr(Fm)} − {fair:.2f} = ₹{prof:.2f}"],
      "Arbitrage profit (cash-and-carry) = F(market) − S·e^(rT)",
      "Borrowing cost to carry the stock must be deducted.")

    S, ri, ru, T = 83.40, 0.07, 0.045, 0.5
    Fx = S * (1 + ri * T) / (1 + ru * T)
    A(FP, "L3",
      f"USD/INR spot is ₹{S:.2f}. Six-month interest rates (simple, p.a.) are {pct(ri)} in India and {pct(ru, 1)} in the USA. The 6-month forward rate implied by covered interest parity is:",
      f"₹{Fx:.4f}",
      [(f"₹{S*(1+ru*T)/(1+ri*T):.4f}", "interest ratio inverted — dollar shown at a forward discount"),
       (f"₹{S*(1+(ri-ru)):.4f}", "annual interest differential applied without scaling for six months"),
       (f"₹{S*(1+ri)/(1+ru):.4f}", "annual rates used without time adjustment")],
      [f"F = 83.40 × (1 + 0.07×0.5) ÷ (1 + 0.045×0.5)",
       f"= 83.40 × {1+ri*T:.4f} ÷ {1+ru*T:.4f} = ₹{Fx:.4f}",
       "Higher-interest currency (INR) trades at a forward discount, so USD is at a premium."],
      "F = S × (1 + r_d·T) ÷ (1 + r_f·T)",
      "Domestic (INR) rate goes in the numerator when quoting INR per USD.")

    K, F1, r, T = 1520, 1575, 0.07, 0.5
    val = (F1 - K) * math.exp(-r * T)
    A(FP, "L3",
      f"Three months ago a trader entered a long forward to buy a stock at ₹{inr(K)} with 6 months remaining now. Today's forward price for the same maturity is ₹{inr(F1)}. With a continuously compounded risk-free rate of {pct(r)}, the value of the trader's position today is:",
      R(val, 2),
      [(R(F1 - K, 2), "difference not discounted to today"),
       ("−" + R(val, 2), "sign reversed — long gains when forward price rises"),
       (R((F1 - K) * math.exp(-r * 0.75), 2), "discounted over the original 9-month life instead of remaining 6 months")],
      [f"Gain per share at maturity = {inr(F1)} − {inr(K)} = ₹{F1-K}",
       f"Value today = {F1-K} × e^(−0.07×0.5) = ₹{val:.2f}"],
      "f = (F₀ − K) e^(−rT)", "Discount only over the remaining life.")

    # ================= CONTANGO / BACKWARDATION =================
    A(CB, "L1",
      "A commodity futures market in which futures prices for more distant delivery months are progressively LOWER than the spot price is said to be in:",
      "Backwardation",
      [("Contango", "contango is futures above spot"),
       ("Normal carry (full carry) market", "full carry implies futures above spot by cost of carry"),
       ("Negative basis convergence", "not a standard market-structure term")],
      ["Contango: F > S, rising with maturity (typical when carry costs dominate).",
       "Backwardation: F < S, usually when convenience yield or supply tightness is high."],
      "Basis = Spot − Futures; positive basis ⇒ backwardation",
      "Remember the direction: contango = futures above spot.", kind="conceptual")

    S, r, u, T, Fm = 840, 0.068, 0.015, 0.5, 856
    cy = r + u - math.log(Fm / S) / T
    A(CB, "L2",
      f"Metal M trades spot at ₹{S}/kg; its 6-month futures is ₹{Fm}/kg. The risk-free rate is {pct(r,1)} and storage cost is {pct(u,1)} of value p.a., both continuous. The implied convenience yield is closest to:",
      pct(cy),
      [(pct(math.log(Fm / S) / T), "implied carry rate reported as convenience yield"),
       (pct(r - math.log(Fm / S) / T), "storage cost ignored"),
       (pct((r + u) - (Fm / S - 1)), "6-month simple change not annualised")],
      [f"ln(F/S)/T = ln({Fm}/{S}) ÷ 0.5 = {pct(math.log(Fm/S)/T)}",
       f"y = r + u − ln(F/S)/T = 6.8% + 1.5% − {pct(math.log(Fm/S)/T)} = {pct(cy)}"],
      "F = S·e^((r + u − y)T)",
      "A market can be in contango yet below full carry — the gap is the convenience yield.")

    A(CB, "L3",
      "Consider the following statements:\n\n"
      "1. In a backwardated market, a long futures position rolled forward each month tends to earn a positive roll yield, other things equal.\n"
      "2. A convenience yield higher than the sum of financing and storage costs is consistent with backwardation.\n"
      "3. For a stock index future, contango cannot arise if the dividend yield exceeds the risk-free rate.\n\nWhich of the statements given above is/are correct?",
      "1, 2 and 3",
      [("1 and 2 only", "statement 3 follows from F = S·e^((r−q)T): q > r ⇒ F < S"),
       ("2 only", "statement 1: roll yield is positive when longs roll into cheaper deferred contracts that converge up"),
       ("1 and 3 only", "statement 2 is the textbook condition for backwardation")],
      ["1: Deferred futures below spot drift up to spot as expiry nears → positive roll yield for longs.",
       "2: y > r + u ⇒ F < S ⇒ backwardation.",
       "3: q > r ⇒ r − q < 0 ⇒ F < S, so no contango."],
      "F = S·e^((r + u − y)T); index: F = S·e^((r − q)T)",
      "Treat the dividend yield of an index like a convenience yield.", kind="statement")

    # ================= FORWARDS vs FUTURES =================
    A(FU, "L1",
      "Match the feature (List I) with the contract to which it applies (List II):\n\n"
      + table(["List I — Feature", "List II"],
              [["P. Daily mark-to-market through a clearing corporation", "1. Forward contract"],
               ["Q. Terms tailored to the counterparties' needs", "2. Futures contract"],
               ["R. Novation by a central counterparty", "3. Both"],
               ["S. Obligation to transact at a pre-agreed price on a future date", ""]], ["---", "---"]) + "\n\nCodes:",
      "P-2, Q-1, R-2, S-3",
      [("P-2, Q-1, R-3, S-3", "novation assumed for OTC forwards as well"),
       ("P-3, Q-1, R-2, S-2", "MTM assumed for forwards; forward also binds to a price"),
       ("P-2, Q-3, R-2, S-3", "futures are standardised, not customised")],
      ["Futures: exchange-traded, standardised, daily MTM, CCP novation.",
       "Forwards: OTC, customised, settled at maturity, bilateral counterparty risk.",
       "Both are obligations at a pre-agreed price."],
      "—", "Customisation vs standardisation is the core distinction.", kind="match")

    S0, IM, MM, lots, lot = 1500.0, 60000, 45000, 2, 250
    path = [1488.0, 1466.0, 1462.0, 1479.0]
    bal = IM; call_day, call_amt = None, None
    log = []
    prev = S0
    for d, pz in enumerate(path, 1):
        bal += (pz - prev) * lots * lot
        prev = pz
        if bal < MM and call_day is None:
            call_day, call_amt = d, IM - bal
            log.append(f"Day {d}: price {pz} → balance ₹{inr(bal)} < maintenance ₹{inr(MM)}; call = ₹{inr(IM-bal)}")
            bal = IM
        else:
            log.append(f"Day {d}: price {pz} → balance ₹{inr(bal)}")
    assert call_day == 2
    A(FU, "L3",
      f"A trader buys {lots} lots of a stock future (lot size {lot}) at ₹{S0:.2f}. Initial margin is ₹{inr(IM)} and maintenance margin ₹{inr(MM)} for the position. Daily settlement prices are:\n\n"
      + table(["Day", "1", "2", "3", "4"], [["Settlement price (₹)"] + [f"{x:.2f}" for x in path]]) +
      "\n\nThe first margin call arises on which day, and for how much (the account must be restored to the initial margin)?",
      f"Day {call_day}; ₹{inr(call_amt)}",
      [(f"Day {call_day}; ₹{inr(MM - (IM + (path[1]-S0)*lots*lot))}", "top-up only to maintenance margin"),
       (f"Day 3; ₹{inr(IM - (IM + (path[2]-S0)*lots*lot))}", "breach tested against initial margin only at a larger cumulative loss; day-2 breach missed"),
       (f"Day {call_day}; ₹{inr(IM-MM)}", "fixed gap between initial and maintenance margin taken as the call")],
      log + ["Variation margin restores the account to the initial margin, not merely to maintenance."],
      "Margin a/c = IM + Σ daily MTM; call when < maintenance, restore to IM",
      "The top-up is to the initial margin level.")
    q = B.Q[-1]
    # guard: ensure 3rd/4th distractor distinct from key
    if q["_wrongs"][2][0] == q["_correct"]:
        q["_wrongs"][2] = (f"Day 1; ₹{inr(IM-(IM+(path[0]-S0)*lots*lot))}", "call triggered on first adverse move")
    assert len(set([q["_correct"]] + [w[0] for w in q["_wrongs"]])) == 4

    A(FU, "L2",
      "**Assertion (A):** If the risk-free interest rate is constant and known, the theoretical forward and futures prices for the same underlying and maturity are equal.\n\n"
      "**Reason (R):** Daily settlement of futures creates reinvestment gains or losses whose value depends on the correlation between the underlying price and interest rates.\n\nChoose the correct option:",
      "Both A and R are true, but R does not explain A",
      [("Both A and R are true, and R correctly explains A", "R explains why the prices DIFFER when rates are stochastic, not why they are equal"),
       ("Only A is true; R is a false statement of fact", "R is a correct statement of the source of forward–futures divergence"),
       ("Only R is true; A is a false statement of fact", "A is the standard no-arbitrage result with deterministic rates")],
      ["With deterministic rates, MTM flows can be reinvested at known rates → F(forward) = F(futures).",
       "R describes the divergence mechanism when rates are random and correlated with the underlying.",
       "Both true, but R is not the reason for A."],
      "—", "An R that explains the exception does not explain the rule.", kind="assertion-reason")

    # ================= HEDGING / ARBITRAGE / SPECULATION =================
    A(HG, "L1",
      "Classify the following market participants correctly:\n\n"
      "(i) An oil refiner buys crude oil futures to lock in input cost for next quarter.\n"
      "(ii) A trader with no exposure buys index futures expecting a rally after a policy announcement.\n"
      "(iii) A desk buys shares in the cash market and simultaneously sells the same stock's futures that are priced above fair value.",
      "(i) Hedger, (ii) Speculator, (iii) Arbitrageur",
      [("(i) Speculator, (ii) Hedger, (iii) Arbitrageur", "confuses offsetting an existing exposure with taking a view"),
       ("(i) Hedger, (ii) Arbitrageur, (iii) Speculator", "arbitrage requires offsetting positions for locked-in profit"),
       ("(i) Arbitrageur, (ii) Speculator, (iii) Hedger", "refiner is protecting a business exposure")],
      ["Hedger offsets an existing or anticipated exposure.",
       "Speculator takes an open position to profit from an expected price move.",
       "Arbitrageur locks in a riskless profit from mispricing (cash-and-carry)."],
      "—", "Look for (a) pre-existing exposure, (b) offsetting legs.", kind="conceptual")

    V, beta, Fp, lot = 12e7, 1.3, 24800, 75
    N = beta * V / (Fp * lot)
    A(HG, "L2",
      f"A fund manager wants to fully hedge an equity portfolio worth {crore(V,0)} with a beta of {beta} using index futures priced at {inr(Fp)} (lot size {lot}). The number of contracts to SELL is closest to:",
      f"{round(N)} contracts",
      [(f"{round(V/(Fp*lot))} contracts", "beta ignored"),
       (f"{round(V/beta/(Fp*lot))} contracts", "portfolio value divided by beta"),
       (f"{round(beta*V/Fp/100)} contracts", "futures value computed on a lot of 100 instead of the contract lot size")],
      [f"Futures contract value = {inr(Fp)} × {lot} = ₹{inr(Fp*lot)}",
       f"N = {beta} × {inr(V)} ÷ {inr(Fp*lot)} = {N:.2f} ≈ {round(N)}"],
      "N = β × V_P ÷ (F × lot)", "Scale by beta, and by the contract (not index) value.")

    rho, sS, sF, Q, size, Fp2 = 0.85, 0.024, 0.029, 5e5, 5000, 1
    h = rho * sS / sF
    nc = h * Q / size
    A(HG, "L3",
      f"A cotton-yarn exporter will buy {inr(Q)} kg of cotton in 3 months and hedges with cotton futures (contract size {inr(size)} kg). Monthly changes have σ(spot) = {pct(sS,1)}, σ(futures) = {pct(sF,1)} and correlation {rho}. The minimum-variance hedge requires, closest to:",
      f"Buying {round(nc)} contracts",
      [(f"Buying {round(Q/size)} contracts", "naïve 1:1 hedge ratio"),
       (f"Buying {round(rho*sF/sS*Q/size)} contracts", "volatilities inverted in hedge ratio"),
       (f"Selling {round(nc)} contracts", "direction reversed — a future purchase is hedged with a long position")],
      [f"h* = ρ × σS/σF = 0.85 × 2.4/2.9 = {h:.4f}",
       f"Contracts = {h:.4f} × {inr(Q)} ÷ {inr(size)} = {nc:.2f} ≈ {round(nc)}",
       "Anticipated purchase ⇒ long hedge."],
      "h* = ρ·σS/σF; N* = h* × Q_A ÷ Q_F",
      "A buyer of the physical hedges by buying futures.")

    V, b0, b1, Fp, lot = 8e7, 1.25, 0.80, 24000, 75
    N = (b1 - b0) * V / (Fp * lot)
    A(HG, "L3",
      f"A portfolio worth {crore(V,0)} has a beta of {b0}. The manager wants to reduce beta to {b1} for one month using index futures at {inr(Fp)} (lot {lot}). The required action is:",
      f"Sell {round(-N)} contracts",
      [(f"Buy {round(-N)} contracts", "direction reversed — reducing beta requires short futures"),
       (f"Sell {round(b0*V/(Fp*lot))} contracts", "full hedge to beta zero computed"),
       (f"Sell {round(b1*V/(Fp*lot))} contracts", "target beta used instead of the change in beta")],
      [f"N = (β* − β) × V ÷ (F × lot) = ({b1} − {b0}) × {inr(V)} ÷ {inr(Fp*lot)} = {N:.2f}",
       f"Negative ⇒ sell ≈ {round(-N)} contracts"],
      "N = (β* − β) × V ÷ Futures contract value", "Use the change in beta, not the target beta.")

    # ================= CDS =================
    A(CDS, "L1",
      "In a single-name credit default swap, upon a credit event of the reference entity under physical settlement, the protection buyer:",
      "Delivers the reference entity's deliverable obligations and receives their par value from the seller",
      [("Receives only the recovery value of the defaulted reference obligation from the protection seller", "seller pays par, buyer keeps the loss protection; recovery is what the buyer gives up"),
       ("Pays the CDS premium for the entire remaining tenor to the seller as a single lump sum", "premium stops after the credit event, apart from accrued premium"),
       ("Receives the full notional value from the seller while also retaining the reference obligations", "that would be over-compensation; cash settlement pays only par − recovery")],
      ["Physical settlement: buyer delivers the bonds/loans, seller pays par.",
       "Cash settlement: seller pays notional × (1 − recovery rate).",
       "Premium payments cease after the credit event (accrued premium to the event date is settled)."],
      "Payoff to buyer = Notional × (1 − R)", "The seller absorbs the loss given default.", kind="conceptual")

    N, s = 50e7, 0.018
    qp = N * s / 4
    A(CDS, "L2",
      f"A bank buys protection on notional {crore(N,0)} through a 5-year CDS at a spread of {s*1e4:.0f} bp p.a., payable quarterly. Ignoring the day-count adjustment, each quarterly premium payment is:",
      R(qp),
      [(R(N * s), "annual premium paid each quarter"),
       (R(N * s / 12), "monthly premium computed"),
       (R(N * 0.0018 / 4), "180 bp read as 0.18%")],
      [f"Annual premium = {crore(N,0)} × 1.80% = {R(N*s)}",
       f"Quarterly = {R(N*s)} ÷ 4 = {R(qp)}"],
      "Premium = Notional × Spread × (period fraction)", "1 bp = 0.01%.")

    N, s, Rr, months = 25e7, 0.024, 0.35, 2
    payoff = N * (1 - Rr)
    accrued = N * s * months / 12
    net = payoff - accrued
    A(CDS, "L2",
      f"A fund bought CDS protection on {crore(N,0)} notional at {s*1e4:.0f} bp p.a. (paid quarterly in arrears). A credit event occurs {months} months after the last premium date; the auction sets recovery at {pct(Rr,0)}. Under cash settlement, the net amount the fund receives (after paying accrued premium) is:",
      R(net),
      [(R(payoff), "accrued premium ignored"),
       (R(N * Rr - accrued), "recovery amount paid instead of loss (1 − R)"),
       (R(payoff - N * s / 4), "full quarter's premium deducted instead of 2 months' accrual")],
      [f"Protection payment = {crore(N,0)} × (1 − 0.35) = {R(payoff)}",
       f"Accrued premium = {crore(N,0)} × 2.40% × 2/12 = {R(accrued)}",
       f"Net = {R(payoff)} − {R(accrued)} = {R(net)}"],
      "Net = N(1 − R) − Accrued premium", "Premium accrues only to the credit-event date.")

    s, Rr = 0.030, 0.40
    lam = s / (1 - Rr)
    pd1 = 1 - math.exp(-lam)
    A(CDS, "L3",
      f"The 5-year CDS spread on a corporate is {s*1e4:.0f} bp and the expected recovery rate is {pct(Rr,0)}. Using the credit-triangle approximation (constant hazard rate), the implied probability of default within the next one year is closest to:",
      pct(pd1),
      [(pct(s), "spread read directly as default probability"),
       (pct(1 - math.exp(-s / Rr)), "spread divided by recovery rate instead of loss rate"),
       (pct(lam), "hazard rate reported as 1-year PD (no e^(−λ) conversion)")],
      [f"λ ≈ s ÷ (1 − R) = 0.030 ÷ 0.60 = {lam:.4f}",
       f"1-year PD = 1 − e^(−{lam:.4f}) = {pct(pd1)}"],
      "λ ≈ s/(1 − R); PD(t) = 1 − e^(−λt)",
      "The spread compensates for expected LOSS, not default alone.")

    # ================= CURRENCY RISK (standalone) =================
    A(CR, "L1",
      "The risk that a bank pays out one currency in a foreign-exchange trade but fails to receive the counter-currency because the counterparty fails in between (often due to time-zone differences) is called:",
      "Settlement (Herstatt) risk, mitigated by payment-versus-payment settlement",
      [("Translation risk, mitigated by forward cover on foreign-currency balances", "translation risk relates to restating foreign-currency financial statements"),
       ("Replacement-cost (pre-settlement) risk, mitigated by daily mark-to-market", "replacement risk arises before settlement date, not during it"),
       ("Economic exposure, mitigated by operational hedging such as relocating plants", "economic exposure concerns long-term competitiveness")],
      ["Principal risk at the settlement stage of FX trades is Herstatt risk (after Bankhaus Herstatt, 1974).",
       "PvP arrangements (e.g., CLS; CCIL's guaranteed settlement for USD/INR) ensure both legs settle together."],
      "—", "Pre-settlement (replacement) risk ≠ settlement (principal) risk.", kind="conceptual")

    A(CR, "L2",
      "Match the exposure (List I) with its example (List II):\n\n"
      + table(["List I — Exposure", "List II — Example"],
              [["P. Transaction exposure", "1. A rupee appreciation erodes an exporter's long-run price competitiveness against Vietnamese rivals"],
               ["Q. Translation exposure", "2. A USD 5 million import payable due in 90 days"],
               ["R. Economic exposure", "3. Restating a UK subsidiary's GBP balance sheet into INR for consolidation"],
               ["S. Settlement risk", "4. Counterparty failure after the bank has paid EUR but before receiving INR"]], ["---", "---"]) + "\n\nCodes:",
      "P-2, Q-3, R-1, S-4",
      [("P-3, Q-2, R-1, S-4", "transaction and translation exposures swapped"),
       ("P-2, Q-1, R-3, S-4", "translation and economic exposures swapped"),
       ("P-4, Q-3, R-1, S-2", "settlement risk confused with a contracted payable")],
      ["Transaction: contracted foreign-currency cash flows.",
       "Translation: accounting restatement of foreign operations.",
       "Economic: effect on future cash flows / competitive position.",
       "Settlement: principal risk at the time of exchange of currencies."],
      "—", "Contracted cash flow = transaction; accounting restatement = translation.", kind="match")

    # ================= ACTIVE vs PASSIVE =================
    A(AP, "L1",
      "Which of the following is MOST characteristic of a passive (index) investment strategy?",
      "Replicating benchmark constituents and weights to minimise tracking error at low cost",
      [("Maximising the information ratio through active security selection and timing", "information ratio is an active-management metric"),
       ("Frequent tactical shifts between asset classes based on valuation signals", "tactical allocation is active management"),
       ("Holding a concentrated portfolio of the fund manager's high-conviction stocks", "concentration is the opposite of index replication")],
      ["Passive funds (index funds, ETFs) seek benchmark returns, not outperformance.",
       "Success is measured by low tracking error and low expense ratio."],
      "—", "Active funds are judged by alpha/IR; passive by tracking error.", kind="conceptual")

    fr = [0.1240, 0.0815, -0.0310]
    ir = [0.1295, 0.0862, -0.0262]
    td = [a - b for a, b in zip(fr, ir)]
    avg_td = sum(td) / 3
    A(AP, "L2",
      "An index fund reports these annual returns against its benchmark:\n\n"
      + table(["Year", "Fund return", "Index (TRI) return"], [[str(i + 1), pct(a), pct(b)] for i, (a, b) in enumerate(zip(fr, ir))]) +
      "\n\nThe average annual tracking difference is:",
      f"{avg_td*100:.2f}%",
      [(f"{abs(avg_td)*100:.2f}%", "sign dropped — fund underperformed, so difference is negative"),
       (f"{statistics.stdev(td)*100:.2f}%", "tracking error (std. deviation) reported instead of tracking difference"),
       (f"{(td[0]+td[1]-td[2])/3*100:.2f}%", "sign of year-3 difference reversed because both returns were negative")],
      ["Differences: " + ", ".join(f"{d*100:+.2f}%" for d in td),
       f"Average = {avg_td*100:.2f}%"],
      "Tracking difference = Fund return − Benchmark return",
      "Tracking difference (level) ≠ tracking error (volatility).")

    m_f = [0.021, -0.008, 0.015, 0.032, -0.012, 0.006]
    m_b = [0.019, -0.011, 0.018, 0.027, -0.010, 0.004]
    d = [a - b for a, b in zip(m_f, m_b)]
    te_m = statistics.stdev(d)
    te_a = te_m * math.sqrt(12)
    A(AP, "L3",
      "Monthly returns of an active fund and its benchmark are:\n\n"
      + table(["Month", "Fund", "Benchmark"], [[str(i + 1), pct(a, 1), pct(b, 1)] for i, (a, b) in enumerate(zip(m_f, m_b))]) +
      "\n\nUsing the sample standard deviation of monthly active returns and √12 annualisation, the annualised tracking error is closest to:",
      pct(te_a),
      [(pct(te_m), "monthly tracking error not annualised"),
       (pct(te_m * 12), "annualised by multiplying by 12 instead of √12"),
       (pct(statistics.pstdev(d) * math.sqrt(12) * 0.9 if False else statistics.stdev(m_f) * math.sqrt(12) - statistics.stdev(m_b) * math.sqrt(12)), "difference of the two volatilities taken instead of volatility of the difference")],
      ["Active returns: " + ", ".join(f"{x*100:+.1f}%" for x in d),
       f"Sample σ (monthly) = {pct(te_m)}",
       f"Annualised TE = {pct(te_m)} × √12 = {pct(te_a)}"],
      "TE = σ(R_p − R_b) × √12",
      "TE is the volatility of the difference, not the difference in volatilities.")

    funds = {"Fund P": (0.162, 0.041), "Fund Q": (0.148, 0.018)}
    rb = 0.135
    irs = {k: (r - rb) / te for k, (r, te) in funds.items()}
    best = max(irs, key=irs.get)
    assert best == "Fund Q"
    A(AP, "L3",
      f"Two actively managed large-cap funds share a benchmark that returned {pct(rb,1)}.\n\n"
      + table(["Fund", "Return", "Tracking error"], [[k, pct(r, 1), pct(te, 1)] for k, (r, te) in funds.items()]) +
      "\n\nOn the basis of the information ratio, which statement is correct?",
      f"Fund Q is superior: IR {irs['Fund Q']:.2f} vs {irs['Fund P']:.2f}",
      [(f"Fund Q is superior: IR {funds['Fund Q'][0]/funds['Fund Q'][1]:.2f} vs {funds['Fund P'][0]/funds['Fund P'][1]:.2f}", "total return (not active return) divided by tracking error"),
       (f"Fund P is superior: higher active return of {pct(funds['Fund P'][0]-rb,1)}", "ranks on alpha, ignoring active risk"),
       (f"Both are equal: IR {(sum(r for r,_ in funds.values())/2-rb)/(sum(t for _,t in funds.values())/2):.2f}", "averaged the two funds' figures")],
      [f"IR(P) = ({pct(funds['Fund P'][0],1)} − {pct(rb,1)}) ÷ {pct(funds['Fund P'][1],1)} = {irs['Fund P']:.2f}",
       f"IR(Q) = ({pct(funds['Fund Q'][0],1)} − {pct(rb,1)}) ÷ {pct(funds['Fund Q'][1],1)} = {irs['Fund Q']:.2f}"],
      "IR = (R_p − R_b) ÷ TE", "More alpha is not better if it costs disproportionate active risk.")

    # ================= CASE C1: BOND BOOK =================
    G = "FINA-CASE-BOND"
    Xc, Xy, Xn, Xf = 0.0726, 0.0690, 6, 20e7
    Yc, Yn, Yp, Yk, Ykn, Yf = 0.084, 8, 106.50, 102.0, 3, 10e7
    Zf, Zd = 10e7, 0.48
    Yd = 2.90
    Xp = bond_price(100, Xc, Xy, Xn, 2)
    Xmac = mac_duration(100, Xc, Xy, Xn, 2)
    Xmd = Xmac / (1 + Xy / 2)
    stim = ("**Case — Sahyadri Retirement Trust (fictional)**\n\n"
            "On 22 August 2026, immediately after coupon payments, the Trust's debt book is:\n\n"
            + table(["Bond", "Terms", "Face held", "Market data"],
                    [["X — GoI dated security", f"{pct(Xc)} coupon, half-yearly (22 Feb/22 Aug), matures 22 Aug 2032, 30/360", crore(Xf, 0), f"YTM {pct(Xy)} (semi-annual)"],
                     ["Y — AAA corporate", f"{pct(Yc)} annual coupon, matures 22 Aug 2034; callable at ₹{Yk:.0f} on 22 Aug 2029", crore(Yf, 0), f"Price ₹{Yp:.2f}; effective duration {Yd}"],
                     ["Z — Floating rate note", "Coupon reset half-yearly to benchmark + fixed spread; next reset 22 Feb 2027", crore(Zf, 0), f"Price ₹100.00; effective duration {Zd}"]],
                    ["---", "---", "---:", "---"]))
    A(BY, "L4", stim + "\n\nThe price of Bond X per ₹100 face value on 22 August 2026 is closest to:",
      R(Xp, 2),
      [(R(bond_price(100, Xc, Xy, Xn, 1), 2), "annual compounding/coupons used for a half-yearly G-sec"),
       (R(bond_price(100, Xc, Xy, 5.5, 2), 2), "one half-year period dropped (11 periods)"),
       (R(bond_price(100, Xc, Xy + 0.0036, Xn, 2), 2), "yield read as 7.26% coupon-based spread (discounted at 7.26%)")],
      [f"12 half-years; coupon ₹{Xc*100/2:.2f}; periodic yield {pct(Xy/2,3)}",
       f"Price = Σ 3.63/(1.0345)ᵗ + 100/(1.0345)¹² = ₹{Xp:.2f}"],
      "P = Σ (C/2)/(1 + y/2)ᵗ + F/(1 + y/2)²ⁿ",
      "G-secs pay half-yearly; use 2n periods at y/2.", group=G)
    q = B.Q[-1]
    q["_wrongs"][2] = (R(bond_price(100, Xc, Xc, Xn, 2), 2), "discounted at the coupon rate (par value) instead of YTM")

    y_m = ytm(Yp, 100, Yc, Yn)
    y_c = ytm(Yp, 100, Yc, Ykn, redemption=Yk)
    ytw = min(y_m, y_c)
    A(CL, "L4", stim + "\n\nThe yield-to-worst on Bond Y is closest to:",
      pct(ytw),
      [(pct(y_m), "yield to maturity taken — call feature ignored"),
       (pct(ytm(Yp, 100, Yc, Ykn)), "yield to call computed with redemption at ₹100 instead of ₹102"),
       (pct((y_m + y_c) / 2), "simple average of YTM and YTC")],
      [f"YTM (8 yrs, redeem 100) = {pct(y_m)}",
       f"YTC (3 yrs, redeem 102) = {pct(y_c)}",
       f"Yield-to-worst = lower = {pct(ytw)}"],
      "YTW = min(YTM, YTC over all call dates)",
      "A premium callable bond is likely to be called — its worst yield is to the call.", group=G)
    assert ytw == y_c

    d30 = (11 - 8) * 30 + (9 - 22)
    ai = Xf * Xc * d30 / 360
    A(DC, "L4", stim + f"\n\nOn 9 November 2026 the Trust sells its entire holding of Bond X. The accrued interest it will receive is:",
      R(ai),
      [(R(Xf * Xc * 79 / 365), "actual days (79) on Actual/365"),
       (R(Xf * Xc * d30 / 365), "30/360 days divided by 365"),
       (R(Xf * Xc / 2 * d30 / 360), "annual coupon halved and then day-fraction applied again")],
      [f"30/360 days 22 Aug → 9 Nov = 3×30 + (9 − 22) = {d30}",
       f"Accrued = {crore(Xf,0)} × {pct(Xc)} × {d30}/360 = {R(ai)}"],
      "AI = Face × Coupon × Days/360", "Half-yearly payment frequency does not change the 30/360 accrual formula.", group=G)
    assert d30 == 77

    mv = {"X": Xf * Xp / 100, "Y": Yf * Yp / 100, "Z": Zf}
    dur = {"X": Xmd, "Y": Yd, "Z": Zd}
    tot = sum(mv.values())
    pdur = sum(mv[k] * dur[k] for k in mv) / tot
    fdur = sum(Xf * 0 + {"X": Xf, "Y": Yf, "Z": Zf}[k] * dur[k] for k in mv) / (Xf + Yf + Zf)
    A(FF, "L4", stim + "\n\nUsing Bond X's modified duration and the effective durations given for Y and Z, the market-value-weighted duration of the book is closest to:",
      f"{pdur:.2f}",
      [(f"{fdur:.2f}", "weights based on face value instead of market value"),
       (f"{(Xmac*mv['X'] + Yd*mv['Y'] + Zd*mv['Z'])/tot:.2f}", "Macaulay duration of X used instead of modified"),
       (f"{(Xmd*mv['X'] + Yd*mv['Y'] + Yn*mv['Z'])/tot:.2f}", "FRN assigned a duration equal to its residual maturity")],
      [f"X: Macaulay {Xmac:.3f} yrs → modified {Xmac:.3f}/1.0345 = {Xmd:.3f}",
       f"Market values: X {crore(mv['X'])}, Y {crore(mv['Y'])}, Z {crore(mv['Z'])}; total {crore(tot)}",
       f"Weighted duration = {pdur:.3f}"],
      "D_p = Σ wᵢ Dᵢ, wᵢ = MVᵢ/ΣMV",
      "An FRN contributes only its time-to-reset duration.", group=G)

    dy = 0.0040
    loss = -pdur * dy * tot
    A(BY, "L4", stim + f"\n\nIf all yields rise in parallel by {dy*1e4:.0f} bp, the estimated change in the book's market value (duration only) is closest to:",
      f"−{lakh(-loss)}",
      [(f"−{lakh(pdur*dy*(Xf+Yf+Zf))}", "applied to face value instead of market value"),
       (f"−{lakh(Xmd*dy*tot)}", "Bond X's duration applied to the whole book"),
       (f"−{lakh(pdur*0.004/2*tot)}", "semi-annual yield change (20 bp) used")],
      [f"Portfolio duration = {pdur:.3f}; market value = {crore(tot)}",
       f"ΔV ≈ −{pdur:.3f} × 0.0040 × {inr(tot)} = −{lakh(-loss)}"],
      "ΔV ≈ −D_mod × Δy × V", "Use market value, not face.", group=G)

    # ================= CASE C4: DERIVATIVES DESK =================
    G = "FINA-CASE-DERIV"
    S, r, q, T, Fm = 24500, 0.068, 0.014, 0.25, 24950
    Vp, bp, lot = 15e7, 1.15, 65
    fair = S * math.exp((r - q) * T)
    stim = ("**Case — Meru Capital's derivatives desk (fictional)**\n\n"
            + table(["Item", "Data"],
                    [["Equity index spot", inr(S)],
                     ["3-month index futures (market)", inr(Fm)],
                     ["Risk-free rate (continuous)", pct(r, 1)],
                     ["Index dividend yield (continuous)", pct(q, 1)],
                     ["Index futures lot size", str(lot)],
                     ["Client equity portfolio", f"{crore(Vp,0)}, beta {bp}"]], ["---", "---:"]) +
            "\n\nThe desk may borrow and lend at the risk-free rate; ignore transaction costs and taxes.")
    A(FP, "L4", stim + "\n\nBased on cost of carry, the index futures is:",
      f"Overpriced by {Fm-fair:.2f} points — sell futures, buy the index basket",
      [(f"Overpriced by {Fm-S*math.exp(r*T):.2f} points — sell futures, buy the index basket", "dividend yield ignored in fair value"),
       (f"Underpriced by {Fm-fair:.2f} points — buy futures, short the basket", "direction reversed"),
       (f"Overpriced by {Fm-S:.2f} points — sell futures, buy the index basket", "basis (F − S) treated as mispricing; carry ignored")],
      [f"Fair F = {inr(S)} × e^((0.068 − 0.014)×0.25) = {fair:.2f}",
       f"Market F − fair F = {Fm-fair:.2f} > 0 ⇒ overpriced ⇒ cash-and-carry"],
      "F* = S·e^((r − q)T)", "Mispricing is measured against fair value, not against spot.", group=G)

    N = bp * Vp / (Fm * lot)
    A(HG, "L4", stim + "\n\nTo hedge the client's portfolio fully against market risk using the 3-month futures at the market price, the desk should sell approximately:",
      f"{round(N)} contracts",
      [(f"{round(bp*Vp/(S*lot))} contracts", "spot index used instead of futures price (acceptable only as approximation)"),
       (f"{round(Vp/(Fm*lot))} contracts", "beta ignored"),
       (f"{round(bp*Vp/(Fm*lot)/lot*10)} contracts", "divided by lot size twice")],
      [f"Contract value = {inr(Fm)} × {lot} = ₹{inr(Fm*lot)}",
       f"N = 1.15 × {inr(Vp)} ÷ {inr(Fm*lot)} = {N:.2f} ≈ {round(N)}"],
      "N = β × V ÷ (F × lot)", "Hedge on the futures contract value.", group=G)
    qq = B.Q[-1]
    if round(bp * Vp / (S * lot)) == round(N):
        qq["_wrongs"][0] = (f"{round(bp*Vp/(S*lot*0.5))} contracts", "half-lot confusion")
    assert len(set([qq["_correct"]] + [w[0] for w in qq["_wrongs"]])) == 4

    Nn = round(N)
    S1, F1 = 23800, 24120
    port_chg = Vp * bp * (S1 / S - 1)
    fut_gain = Nn * lot * (Fm - F1)
    net = port_chg + fut_gain
    A(HG, "L4", stim + f"\n\nThe desk sells {Nn} contracts. One month later the index is {inr(S1)} and the futures {inr(F1)}. Assuming the portfolio moves exactly per its beta (ignore dividends), the net gain/loss on the hedged position is closest to:",
      f"{'Gain' if net > 0 else 'Loss'} of {lakh(abs(net))}",
      [(f"Loss of {lakh(abs(port_chg))}", "futures gain ignored (unhedged loss)"),
       (f"{'Gain' if Vp*(S1/S-1)+fut_gain>0 else 'Loss'} of {lakh(abs(Vp*(S1/S-1)+fut_gain))}", "portfolio loss computed without beta"),
       (f"{'Gain' if port_chg + Nn*lot*(S-S1) > 0 else 'Loss'} of {lakh(abs(port_chg + Nn*lot*(S-S1)))}", "futures gain measured on spot change (basis change ignored)")],
      [f"Index return = {S1}/{S} − 1 = {pct(S1/S-1)}; portfolio change = 1.15 × that × {crore(Vp,0)} = {lakh(port_chg)}",
       f"Futures gain = {Nn} × {lot} × ({inr(Fm)} − {inr(F1)}) = {lakh(fut_gain)}",
       f"Net = {lakh(net)} — residual reflects basis narrowing and rounding"],
      "Hedged P&L = β·V·r_index + N·lot·(F₀ − F₁)",
      "Basis risk: futures moved by a different amount from spot.", group=G)

    A(FU, "L4", stim + "\n\nThe client asks whether a 3-month OTC forward with a bank on the index would have been equivalent. Which statement is correct?",
      "The forward settles only at maturity, leaving bank counterparty risk; futures gains and losses settle daily via the clearing corporation",
      [("The forward would require daily variation margin to be paid through the clearing corporation, exactly as the futures contract does", "OTC forwards are not novated/MTM'd by an exchange CCP"),
       ("The forward price would necessarily be higher than the futures price because the bank bears the client's counterparty risk", "with deterministic rates forward ≈ futures price; credit terms are priced separately"),
       ("The forward would eliminate basis risk entirely because it is a standardised contract with exchange-fixed lot sizes and expiry dates", "forwards are customised, not standardised; basis risk depends on maturity match")],
      ["Forwards: bilateral, settled at maturity, counterparty credit risk.",
       "Futures: daily MTM, CCP novation, standardised lots and expiries."],
      "—", "Customisation can reduce basis risk; standardisation is a futures feature.", group=G, kind="case")

    A(CB, "L4", stim + "\n\nWhich description of the index futures market structure on this date is correct?",
      f"Contango, with the observed basis (spot − futures) of {S-Fm:.0f} points; the fair-value basis is {S-fair:.2f} points",
      [(f"Backwardation, since dividend yield reduces the fair price below spot", "r > q so fair F > S — still contango"),
       (f"Contango, with basis of {Fm-S:.0f} points and fair-value basis of {fair-S:.2f} points, both positive", "basis sign convention (spot − futures) reversed"),
       (f"Contango only because the futures is mispriced; at fair value the market would be in backwardation", "fair value is also above spot since r > q")],
      [f"Observed basis = {inr(S)} − {inr(Fm)} = {S-Fm:.0f} (negative ⇒ futures above spot ⇒ contango)",
       f"Fair F = {fair:.2f} > spot since r − q > 0; fair basis = {S-fair:.2f}"],
      "Basis = S − F", "Contango holds even at fair value whenever r > q.", group=G, kind="case")

    # ================= CASE C8: EXPORTER FX =================
    G = "FINA-CASE-FX"
    usd, s0, fwd, ri, ru, T = 2e6, 84.20, 85.10, 0.072, 0.051, 0.5
    K, prem = 84.80, 0.65
    stim = ("**Case — Kaveri Textiles Ltd (fictional)**\n\n"
            f"Kaveri will receive USD {usd/1e6:.0f} million from a US buyer in 6 months. Market data today:\n\n"
            + table(["Item", "Data"],
                    [["Spot USD/INR", f"₹{s0:.2f}"], ["6-month forward USD/INR", f"₹{fwd:.2f}"],
                     ["INR deposit rate (simple p.a.)", pct(ri, 1)], ["USD borrowing rate (simple p.a.)", pct(ru, 1)],
                     ["6-month USD put option (strike ₹84.80)", f"premium ₹{prem:.2f} per USD, paid today"]], ["---", "---:"]))
    borrow = usd / (1 + ru * T)
    mmh = borrow * s0 * (1 + ri * T)
    A(CR, "L4", stim + "\n\nUnder a money-market hedge (borrow USD now, convert at spot, deposit INR), Kaveri's INR proceeds at the end of 6 months are closest to:",
      crore(mmh, 4),
      [(crore(usd * s0 * (1 + ri * T), 4), "borrowed the full USD 2 million instead of its present value"),
       (crore(usd / (1 + ru) * s0 * (1 + ri), 4), "annual rates applied to a 6-month period"),
       (crore(borrow * s0, 4), "INR deposit interest ignored")],
      [f"USD to borrow = 2,000,000 ÷ (1 + 0.051×0.5) = {borrow:,.2f}",
       f"Convert at spot: × 84.20 = ₹{borrow*s0:,.0f}",
       f"Deposit 6 months at 7.2%: × {1+ri*T:.3f} = {crore(mmh,4)}"],
      "MMH proceeds = [FC ÷ (1 + r_f·T)] × S × (1 + r_d·T)",
      "Borrow only the PV of the receivable so that the receivable repays the loan exactly.", group=G, kind="case")

    ST = 84.40
    prem_fv = prem * (1 + ri * T)
    outs = {"Forward": usd * fwd, "Option": usd * (max(K, ST) - prem_fv), "Unhedged": usd * ST}
    def rank(d):
        return " > ".join(f"{k} {crore(v,4)}" for k, v in sorted(d.items(), key=lambda kv: -kv[1]))
    key = rank(outs)
    assert list(sorted(outs, key=lambda k: -outs[k])) == ["Forward", "Unhedged", "Option"]
    w1 = dict(outs, Option=usd * (max(K, ST) + prem_fv))
    w2 = dict(outs, Option=usd * (ST - prem_fv))
    w3 = dict(outs, Option=usd * K)
    A(CR, "L4", stim + f"\n\nIf spot at maturity turns out to be ₹{ST:.2f}, rank the three alternatives by INR received (option premium carried forward at the INR deposit rate):",
      key,
      [(rank(w1), "premium added to (instead of deducted from) the strike"),
       (rank(w2), "put treated as lapsed although spot < strike"),
       (rank(w3), "premium cost ignored — option valued at strike")],
      [f"Forward: 2 mn × 85.10 = {crore(outs['Forward'],4)}",
       f"Put exercised (84.40 < 84.80): 2 mn × (84.80 − 0.65×1.036 = {K-prem_fv:.4f}) = {crore(outs['Option'],4)}",
       f"Unhedged: 2 mn × 84.40 = {crore(outs['Unhedged'],4)}",
       "The small rupee move leaves the option's floor (net of premium) below the unhedged outcome."],
      "Put outcome = max(K, S_T) − Premium × (1 + r·T)",
      "An option's floor is net of its premium cost; a modest move may not recover the premium.", group=G, kind="case")

    A(CR, "L4", stim + "\n\nKaveri's bank books the forward and, on maturity, settles the USD/INR leg through CCIL's guaranteed settlement. Which statement about the risks involved is correct?",
      "CCIL's central-counterparty role curbs interbank settlement risk; until maturity Kaveri still faces replacement-cost (pre-settlement) risk on its bank",
      [("Settlement through CCIL eliminates Kaveri's own transaction exposure to the rupee, so booking the forward with its bank is unnecessary", "CCP settlement removes interbank principal risk, not the exporter's price exposure"),
       ("Herstatt risk is highest for USD/INR trades because both currencies settle in the same time zone, so CCIL cannot mitigate it at all", "Herstatt risk arises from time-zone gaps; PvP/CCP mitigates it"),
       ("Replacement-cost risk exists only for option contracts and not for forwards, so Kaveri has no counterparty risk at all on its bank", "a forward with positive MTM has replacement cost if the counterparty defaults")],
      ["CCIL novates interbank USD/INR trades and settles them on a guaranteed basis — mitigates principal/settlement risk.",
       "The client–bank forward remains a bilateral contract; before maturity the risk is pre-settlement (replacement cost)."],
      "—", "Distinguish interbank settlement risk from the client's counterparty risk.", group=G, kind="case")
