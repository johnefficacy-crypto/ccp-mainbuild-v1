# REG-CORPUS-FIN-A — finance — SME review sheet (170 Q)

Levels {'L1': 34, 'L2': 51, 'L3': 51, 'L4': 34} · key positions {'B': 43, 'D': 42, 'C': 42, 'A': 43} · microtopics covered 50/111
Status `ai_drafted` / `draft`. ⚠ = verify_fact (statute / rate / threshold — check against current official text).


---

## FINA-001 · L1 · easy · Bond yield and pricing

Other things remaining the same, which of the following bonds will show the LARGEST percentage price change for a 50 bp rise in market yield?

- **A.** A 5-year zero-coupon bond  _(error: zero-coupon, but shorter maturity means lower duration)_
- **B.** A 15-year zero-coupon bond ✅
- **C.** A 15-year bond paying a 9% annual coupon  _(error: higher coupon shortens duration — less sensitive than the zero)_
- **D.** A 15-year floating-rate note reset every six months  _(error: FRN duration is roughly the time to next reset)_

**Working**

1. Price sensitivity is measured by (modified) duration.
2. For a given maturity, a zero-coupon bond has the highest duration (equal to its maturity).
3. Longer maturity raises duration; a 15-year zero therefore beats a 15-year coupon bond and a 5-year zero.
4. An FRN re-prices to near par at each reset, so its duration is only about 0.5 years.

**Formula:** %ΔP ≈ −Modified duration × Δy  
**Trap:** Maturity alone does not decide sensitivity — coupon size and reset features matter.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-002 · L2 · medium · Bond yield and pricing

A bond of face value ₹1,000 carries a 7.50% coupon payable annually and has 5 years to maturity. It is redeemable at par. If the market yield on comparable bonds is 8.20%, the bond's price is closest to:

- **A.** ₹914.63  _(error: coupon capitalised as a perpetuity (C ÷ y), maturity ignored)_
- **B.** ₹971.75  _(error: semi-annual compounding applied to an annual-coupon bond)_
- **C.** ₹994.44  _(error: redemption value discounted at the coupon rate instead of the yield)_
- **D.** ₹972.20 ✅

**Working**

1. Annual coupon = 1,000 × 7.50% = ₹75.00
2. PV of coupons = 75.00 × annuity factor (8.2%, 5 yrs) = ₹297.88
3. PV of redemption = 1,000 ÷ 1.082⁵ = ₹674.32
4. Price = ₹972.20 (below par since yield > coupon)

**Formula:** P = Σ C/(1+y)ᵗ + F/(1+y)ⁿ  
**Trap:** All cash flows — including redemption — are discounted at the market yield, with the bond's own payment frequency.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-003 · L2 · medium · Bond yield and pricing

A ₹100 face value bond with a 7.15% annual coupon is quoted at ₹96.40. Its current yield is:

- **A.** 6.89%  _(error: coupon rate scaled by price/face instead of face/price)_
- **B.** 11.15%  _(error: full pull-to-par gain added in one year)_
- **C.** 7.42% ✅
- **D.** 7.15%  _(error: coupon rate taken as current yield)_

**Working**

1. Annual coupon = ₹7.15
2. Current yield = 7.15 ÷ 96.40 = 7.42%

**Formula:** Current yield = Annual coupon ÷ Market price  
**Trap:** Current yield ignores the capital gain to maturity — it is not YTM.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-004 · L3 · hard · Bond yield and pricing

A 6-year, 8% annual-coupon bond (face ₹1,000, redeemable at par) trades at ₹945. Using the standard approximation formula, its yield to maturity is closest to:

- **A.** 7.28%  _(error: discount amortisation subtracted instead of added)_
- **B.** 8.92%  _(error: denominator taken as face value)_
- **C.** 9.17% ✅
- **D.** 9.44%  _(error: denominator taken as market price instead of average of face and price)_

**Working**

1. Annual coupon = ₹80; discount amortised per year = (1,000 − 945) ÷ 6 = ₹9.17
2. Average investment = (1,000 + 945) ÷ 2 = ₹972.5
3. Approx. YTM = 89.17 ÷ 972.5 = 9.17%
4. (Exact IRR check: 9.23% — the approximation is close.)

**Formula:** YTM ≈ [C + (F − P)/n] ÷ [(F + P)/2]  
**Trap:** A discount bond's YTM exceeds its coupon; the gain to par is added, not subtracted.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-005 · L3 · hard · Bond yield and pricing

A 4-year bond of face ₹1,000 pays an 8% coupon annually; market yield is 10%.

| Year | Cash flow (₹) | PV factor @10% | PV (₹) |
|---|---:|---:|---:|
| 1 | 80 | 0.9091 | 72.73 |
| 2 | 80 | 0.8264 | 66.12 |
| 3 | 80 | 0.7513 | 60.11 |
| 4 | 1,080 | 0.6830 | 737.65 |

The bond's Macaulay duration is closest to:

- **A.** 4.00 years  _(error: duration taken equal to maturity (true only for a zero-coupon bond))_
- **B.** 3.24 years  _(error: modified duration reported instead of Macaulay)_
- **C.** 3.64 years  _(error: cash flows weighted without discounting)_
- **D.** 3.56 years ✅

**Working**

1. Price = Σ PV = ₹936.60
2. Σ t × PV = 1×72.73 + 2×66.12 + 3×60.11 + 4×737.65 = 3335.89
3. Macaulay duration = 3335.89 ÷ 936.60 = 3.56 years

**Formula:** D = Σ [t × PV(CFₜ)] ÷ Price  
**Trap:** Weights must be present values; modified duration = D/(1+y) is a different measure.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-006 · L3 · hard · Bond yield and pricing

A bond has modified duration of 6.2 and convexity of 52. If its yield rises by 75 basis points, the estimated percentage change in price (duration + convexity) is:

- **A.** -4.357%  _(error: ½ factor omitted from convexity term)_
- **B.** -4.504% ✅
- **C.** -4.796%  _(error: convexity adjustment subtracted (sign reversed))_
- **D.** -4.650%  _(error: convexity adjustment ignored)_

**Working**

1. Duration effect = −6.2 × 0.0075 = -4.650%
2. Convexity effect = ½ × 52 × 0.0075² = +0.146%
3. Total ≈ -4.504%

**Formula:** %ΔP ≈ −MD·Δy + ½·Convexity·(Δy)²  
**Trap:** Positive convexity always adds to price, whether yields rise or fall.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-007 · L2 · medium · Bond yield and pricing

A zero-coupon STRIP of face ₹100 matures in 6 years. Using the market convention of semi-annual compounding, at a yield of 7.20% p.a. its price is:

- **A.** ₹69.83  _(error: simple interest discounting)_
- **B.** ₹65.42 ✅
- **C.** ₹80.88  _(error: half-yearly rate applied for only 6 periods)_
- **D.** ₹65.89  _(error: annual compounding used)_

**Working**

1. Periods = 6 × 2 = 12; periodic rate = 3.60%
2. Price = 100 ÷ (1.036)¹² = ₹65.42

**Formula:** P = F ÷ (1 + y/2)^(2n)  
**Trap:** Match the number of periods to the compounding frequency.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-008 · L1 · easy · Bond yield and pricing

Consider the following statements about yield to maturity (YTM):

1. YTM is the internal rate of return of the bond's promised cash flows at the current market price.
2. The investor realises the YTM only if all coupons are reinvested at the YTM and the bond is held to maturity without default.
3. For a bond trading at a premium, YTM is higher than the current yield.

Which of the statements given above is/are correct?

- **A.** 1 only  _(error: misses the reinvestment/hold-to-maturity assumption)_
- **B.** 2 and 3 only  _(error: statement 3 is wrong; statement 1 is the definition)_
- **C.** 1, 2 and 3  _(error: premium bond: YTM < current yield < coupon)_
- **D.** 1 and 2 only ✅

**Working**

1. Statement 1: definition of YTM — correct.
2. Statement 2: realised yield equals YTM only under those assumptions — correct.
3. Statement 3: premium bond ⇒ coupon > current yield > YTM, so it is wrong.

**Formula:** Premium: coupon > CY > YTM; Discount: coupon < CY < YTM  
**Trap:** The ordering of coupon, current yield and YTM flips between premium and discount bonds.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-009 · L3 · hard · Bond yield and pricing

An investor buys a 3-year, 8% annual-coupon bond at par (₹1,000) and holds it to maturity. Each coupon can be reinvested only at 6% p.a. The investor's realised compound yield is closest to:

- **A.** 7%  _(error: simple average of coupon rate and reinvestment rate)_
- **B.** 7.86% ✅
- **C.** 8%  _(error: YTM taken as realised yield — reinvestment shortfall ignored)_
- **D.** 7.43%  _(error: interest-on-interest ignored (coupons not reinvested))_

**Working**

1. FV of coupons at 6%: 80×1.06² + 80×1.06 + 80 = ₹254.69
2. Terminal value = 254.69 + 1,000 = ₹1254.69
3. Realised yield = (1254.69 ÷ 1,000)^(1/3) − 1 = 7.86%

**Formula:** RCY = (Terminal value ÷ Price)^(1/n) − 1  
**Trap:** Reinvestment below YTM drags the realised return below YTM even for a par bond.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-010 · L1 · easy · Callable and puttable securities

Which of the following correctly describes a callable bond relative to an otherwise identical option-free bond?

- **A.** Its price is the option-free price minus the issuer's call value, and it shows negative convexity at low yields ✅
- **B.** Its price rises faster than the option-free bond when yields fall, because the call caps the investor's losses  _(error: price compression near call price — gains are capped, not enhanced)_
- **C.** Its price equals the option-free price plus the call option value, since the investor holds the option  _(error: call option belongs to the issuer, not the investor)_
- **D.** It must offer a lower yield than the option-free bond because the investor can redeem it before maturity  _(error: describes a puttable bond; callable bonds offer a higher yield)_

**Working**

1. The issuer holds the right to redeem early, so the investor is short a call.
2. Callable price = Straight bond − Call value.
3. As yields fall the price is capped near the call price → negative convexity.

**Formula:** P(callable) = P(straight) − C; P(puttable) = P(straight) + Put  
**Trap:** Who holds the option decides the sign.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-011 · L2 · medium · Callable and puttable securities

An option-free bond is valued at ₹1,042.60. An otherwise identical bond carries both an issuer call option (valued at ₹18.35) and an investor put option (valued at ₹11.20). Ignoring interaction between the options, the value of the bond with both options is:

- **A.** ₹1,072.15  _(error: both options added to straight value)_
- **B.** ₹1,013.05  _(error: put option also treated as reducing value)_
- **C.** ₹1,049.75  _(error: signs of both options reversed)_
- **D.** ₹1,035.45 ✅

**Working**

1. Investor is short the call: −18.35
2. Investor is long the put: +11.20
3. Value = 1,042.60 − 18.35 + 11.20 = ₹1,035.45

**Formula:** V = Straight − Call + Put  
**Trap:** The call benefits the issuer; the put benefits the holder.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-012 · L3 · hard · Callable and puttable securities

A 10-year, 9% annual-coupon bond (face ₹100) trades at ₹108.00. It is callable at ₹103 at the end of year 4. Its yield to call (exact IRR basis) is closest to:

- **A.** 7.30% ✅
- **B.** 7.82%  _(error: yield to maturity reported (call feature ignored))_
- **C.** 6.66%  _(error: redemption at face ₹100 instead of the call price ₹103)_
- **D.** 6.73%  _(error: approximation formula using face ₹100 instead of call price)_

**Working**

1. Cash flows to call: ₹9 for years 1–4 plus ₹103 at year 4
2. Solve 108 = Σ 9/(1+y)ᵗ + 103/(1+y)⁴ → y = 7.30%
3. YTM over 10 years = 7.82%; yield-to-worst = lower of the two = YTC

**Formula:** P = Σ C/(1+y)ᵗ + Call price/(1+y)ᵏ  
**Trap:** For a premium callable bond the YTC is usually the yield-to-worst.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-013 · L2 · medium · Callable and puttable securities

**Assertion (A):** When market yields fall sharply, the price of a puttable bond rises roughly in line with an otherwise identical option-free bond.

**Reason (R):** The put option gains value mainly when yields rise, putting a floor under the bond's price.

Choose the correct option:

- **A.** Both A and R are true, and R correctly explains A ✅
- **B.** Only R is true; A is a false statement of fact  _(error: confuses puttable with callable (price compression is a callable feature))_
- **C.** Both A and R are true, but R does not explain A  _(error: R is precisely why the put is nearly worthless at low yields)_
- **D.** Only A is true; R is a false statement of fact  _(error: R correctly states when the put is valuable)_

**Working**

1. At low yields the put is deep out-of-the-money and adds little value, so the puttable bond behaves like a straight bond.
2. At high yields the put floors the price near the put price.
3. Hence R explains A.

**Formula:** P(puttable) = P(straight) + Put value  
**Trap:** Price compression at low yields belongs to callable, not puttable bonds.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-014 · L2 · medium · Day-count conventions ⚠

Match the instrument (List I) with the day-count convention generally applied in the Indian market (List II):

| List I — Instrument | List II — Convention |
|---|---|
| P. Government of India dated securities | 1. Actual/364 (discount basis) |
| Q. Treasury bills | 2. 30/360 |
| R. Commercial paper and certificates of deposit | 3. Actual/365 |
| S. Listed corporate bonds (SEBI framework) | 4. Actual/Actual |

Codes:

- **A.** P-3, Q-1, R-2, S-4  _(error: G-secs taken as Actual/365)_
- **B.** P-4, Q-1, R-3, S-2  _(error: G-sec and corporate bond conventions swapped)_
- **C.** P-2, Q-1, R-3, S-4 ✅
- **D.** P-2, Q-3, R-1, S-4  _(error: T-bill and money-market (CP/CD) conventions swapped)_

**Working**

1. G-secs: 30/360 for accrued interest.
2. T-bills: yield on Actual/364 discount basis.
3. CP/CD and money market: Actual/365.
4. Corporate bonds: Actual/Actual under SEBI's day-count circular (366 in leap years).

**Formula:** Convention matters for accrued interest and yield computation  
**Trap:** Only G-secs use 30/360; money-market paper uses actual days.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-015 · L2 · medium · Day-count conventions ⚠

A GoI dated security with a 7.18% coupon pays interest half-yearly on 14 January and 14 July. A trade settles on 3 October. Using the 30/360 convention, the accrued interest per ₹100 face value is:

- **A.** ₹1.5756 ✅
- **B.** ₹1.6155  _(error: actual days (81) on a 360-day year)_
- **C.** ₹1.5934  _(error: actual days (81) on Actual/365 basis)_
- **D.** ₹1.5540  _(error: 30/360 day count but divided by 365)_

**Working**

1. 30/360 days from 14 Jul to 3 Oct = (10 − 7) × 30 + (3 − 14) = 79 days
2. Accrued = 100 × 7.18% × 79/360 = ₹1.5756

**Formula:** AI = Face × Coupon × Days(30/360) ÷ 360  
**Trap:** Count days the 30/360 way and divide by 360 — never mix conventions.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-016 · L2 · medium · Day-count conventions ⚠

A 91-day Treasury bill is allotted at a price of ₹98.2750 per ₹100. Its annualised yield is:

- **A.** 7.0404%  _(error: Actual/365 used instead of 364)_
- **B.** 7.0211% ✅
- **C.** 6.9000%  _(error: discount on face value (discount rate) instead of yield on price)_
- **D.** 6.9440%  _(error: 360-day year used)_

**Working**

1. Discount = 100 − 98.2750 = 1.7250
2. Yield = 1.7250 ÷ 98.2750 × 364/91 = 7.0211%

**Formula:** T-bill yield = (100 − P)/P × 364/d  
**Trap:** Divide by price (not face) and annualise on 364 days.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-017 · L3 · hard · Day-count conventions ⚠

A bank buys ₹5 crore face value of a 6.95% GoI security (coupon dates 15 February and 15 August) at a clean price of ₹99.25, for settlement on 28 November. Under market conventions, the consideration payable is:

- **A.** ₹4,86,30,764  _(error: accrued interest deducted from clean price)_
- **B.** ₹4,96,25,000  _(error: clean price paid — accrued interest omitted)_
- **C.** ₹5,06,24,658  _(error: accrued on actual days (105) / 365)_
- **D.** ₹5,06,19,236 ✅

**Working**

1. 30/360 days 15 Aug → 28 Nov = 3×30 + (28 − 15) = 103
2. Accrued per ₹100 = 6.95 × 103/360 = ₹1.9885
3. Dirty price = 99.25 + 1.9885 = 101.2385
4. Consideration = ₹5 crore × 101.2385% = ₹5,06,19,236

**Formula:** Dirty price = Clean price + Accrued interest  
**Trap:** Settlement is on the dirty (full) price.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-018 · L1 · easy · Fixed vs floating rate securities

Immediately after a coupon reset date, a plain floating-rate note whose quoted spread equals the market-required spread will typically:

- **A.** Trade at a discount, because floating coupons are uncertain  _(error: coupon uncertainty does not cause a discount if spread = required spread)_
- **B.** Trade at a premium, with duration equal to its residual maturity  _(error: treats FRN like a fixed-coupon bond)_
- **C.** Trade at par, but with duration greater than a fixed-rate bond of the same maturity  _(error: floating resets shorten duration, not lengthen it)_
- **D.** Trade close to par, with an interest-rate duration roughly equal to the time to the next reset ✅

**Working**

1. At each reset the coupon moves to the market rate, so PV returns to about par.
2. Rate risk exists only until the next reset, so duration ≈ time to reset.
3. Credit-spread changes (not benchmark changes) can still move the price.

**Formula:** FRN price ≈ par at reset if quoted margin = required margin  
**Trap:** FRNs carry low interest-rate risk but still carry spread (credit) risk.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-019 · L2 · medium · Fixed vs floating rate securities

A floating rate bond's coupon for each half-year is set as: base rate = simple average of the cut-off yields of the last three auctions of 182-day T-bills, plus a fixed spread of 1.22%. The last three auction cut-offs were 6.92%, 6.85% and 6.99%. The coupon amount for the half-year on a holding of ₹10 crore face value is:

- **A.** ₹81,40,000  _(error: annual coupon rate applied to a half-year)_
- **B.** ₹34,60,000  _(error: fixed spread omitted)_
- **C.** ₹41,05,000  _(error: only the latest auction yield taken as base)_
- **D.** ₹40,70,000 ✅

**Working**

1. Base = (6.92 + 6.85 + 6.99) ÷ 3 = 6.9200%
2. Coupon rate = 6.9200 + 1.22 = 8.1400% p.a.
3. Half-year coupon = ₹10 crore × 8.1400% ÷ 2 = ₹40,70,000

**Formula:** Coupon = Base (benchmark average) + Spread; periodic = annual ÷ 2  
**Trap:** Rate is annual; pay-out is half-yearly.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-020 · L3 · hard · Fixed vs floating rate securities

An issuer carves a ₹100 crore, 8% fixed-rate bond pool into two tranches: ₹60 crore of floaters paying MIBOR + 0.50% and ₹40 crore of inverse floaters that absorb the balance of the pool's interest. If MIBOR is 6.20%, the coupon on the inverse floater is:

- **A.** 9.80%  _(error: rule-of-thumb 2×fixed − MIBOR (weights ignored))_
- **B.** 10.70%  _(error: floater spread ignored)_
- **C.** 9.95% ✅
- **D.** 6.63%  _(error: residual interest divided by floater size)_

**Working**

1. Pool interest = 8% × 100 = ₹8.00 crore
2. Floater interest = 60 × (6.2 + 0.50)% = ₹4.02 crore
3. Inverse floater gets ₹3.98 crore on ₹40 crore = 9.95%

**Formula:** Inverse coupon = (Pool interest − Floater interest) ÷ Inverse tranche  
**Trap:** Inverse floaters have leverage: coupon falls 1.5 pp for every 1 pp rise in MIBOR here.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-021 · L1 · easy · Forward pricing and cost of carry

Consider the following statements on the cost-of-carry model for financial futures:

1. The fair futures price equals spot price plus carrying cost minus carry return (such as dividends) to expiry.
2. If the market futures price exceeds the fair price, an arbitrageur buys spot and sells futures.
3. Higher expected dividends during the life of a stock futures contract raise its fair price.

Which of the statements given above is/are correct?

- **A.** 1 and 2 only ✅
- **B.** 2 and 3 only  _(error: dividends are carry return — they reduce the fair price)_
- **C.** 1, 2 and 3  _(error: statement 3 reverses the effect of dividends)_
- **D.** 1 only  _(error: statement 2 describes cash-and-carry arbitrage correctly)_

**Working**

1. Fair F = S + cost of carry − carry return — correct.
2. Futures overpriced → buy spot, sell futures (cash-and-carry) — correct.
3. Dividends reduce the fair futures price — statement 3 wrong.

**Formula:** F = S + Carry cost − Carry return  
**Trap:** Income on the underlying is a deduction from carry.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-022 · L2 · medium · Forward pricing and cost of carry

A stock trades at ₹2,450. A dividend of ₹30 is expected in 2 months. The continuously compounded risk-free rate is 7%. The fair price of a 3-month forward on the stock is:

- **A.** ₹2,463.08 ✅
- **B.** ₹2,523.43  _(error: PV of dividend added instead of deducted)_
- **C.** ₹2,462.72  _(error: dividend deducted without discounting)_
- **D.** ₹2,493.25  _(error: dividend ignored)_

**Working**

1. PV of dividend = 30 × e^(−0.07×2/12) = ₹29.6520
2. F = (2,450 − 29.6520) × e^(0.07×0.25) = ₹2463.08

**Formula:** F = (S − PV(D)) × e^(rT)  
**Trap:** Deduct the present value of income, then carry forward.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-023 · L2 · medium · Forward pricing and cost of carry

An equity index stands at 24,500. The risk-free rate is 6.8% and the index dividend yield is 1.4% p.a., both continuously compounded. The theoretical price of a 3-month index future is:

- **A.** 24,920.06  _(error: dividend yield ignored)_
- **B.** 25,859.37  _(error: annual carry applied to a 3-month contract)_
- **C.** 25,007.43  _(error: dividend yield added to the financing rate)_
- **D.** 24,832.99 ✅

**Working**

1. Net carry = 6.8% − 1.4% = 5.4%
2. F = 24,500 × e^(0.054×0.25) = 24,832.99

**Formula:** F = S × e^((r − q)T)  
**Trap:** Scale carry by time to expiry.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-024 · L3 · hard · Forward pricing and cost of carry

A non-dividend-paying share trades at ₹1,860; its 2-month futures trades at ₹1,895. The continuously compounded risk-free rate is 7.20%. Ignoring transaction costs, the arbitrage strategy and profit per share at expiry are:

- **A.** Buy spot, sell futures; profit ₹35.00  _(error: financing cost of holding spot ignored)_
- **B.** Buy spot, sell futures; profit ₹12.40  _(error: profit discounted to today, not at expiry)_
- **C.** Buy spot, sell futures; profit ₹12.55 ✅
- **D.** Sell spot, buy futures; profit ₹12.55  _(error: direction reversed — futures is overpriced, not underpriced)_

**Working**

1. Fair F = 1,860 × e^(0.072×2/12) = ₹1882.45
2. Market F 1,895 > fair ⇒ futures overpriced ⇒ cash-and-carry
3. Profit at expiry = 1,895 − 1882.45 = ₹12.55

**Formula:** Arbitrage profit (cash-and-carry) = F(market) − S·e^(rT)  
**Trap:** Borrowing cost to carry the stock must be deducted.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-025 · L3 · hard · Forward pricing and cost of carry

USD/INR spot is ₹83.40. Six-month interest rates (simple, p.a.) are 7% in India and 4.5% in the USA. The 6-month forward rate implied by covered interest parity is:

- **A.** ₹85.4850  _(error: annual interest differential applied without scaling for six months)_
- **B.** ₹84.4196 ✅
- **C.** ₹82.3928  _(error: interest ratio inverted — dollar shown at a forward discount)_
- **D.** ₹85.3952  _(error: annual rates used without time adjustment)_

**Working**

1. F = 83.40 × (1 + 0.07×0.5) ÷ (1 + 0.045×0.5)
2. = 83.40 × 1.0350 ÷ 1.0225 = ₹84.4196
3. Higher-interest currency (INR) trades at a forward discount, so USD is at a premium.

**Formula:** F = S × (1 + r_d·T) ÷ (1 + r_f·T)  
**Trap:** Domestic (INR) rate goes in the numerator when quoting INR per USD.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-026 · L3 · hard · Forward pricing and cost of carry

Three months ago a trader entered a long forward to buy a stock at ₹1,520 with 6 months remaining now. Today's forward price for the same maturity is ₹1,575. With a continuously compounded risk-free rate of 7%, the value of the trader's position today is:

- **A.** −₹53.11  _(error: sign reversed — long gains when forward price rises)_
- **B.** ₹53.11 ✅
- **C.** ₹55.00  _(error: difference not discounted to today)_
- **D.** ₹52.19  _(error: discounted over the original 9-month life instead of remaining 6 months)_

**Working**

1. Gain per share at maturity = 1,575 − 1,520 = ₹55
2. Value today = 55 × e^(−0.07×0.5) = ₹53.11

**Formula:** f = (F₀ − K) e^(−rT)  
**Trap:** Discount only over the remaining life.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-027 · L1 · easy · Contango and backwardation

A commodity futures market in which futures prices for more distant delivery months are progressively LOWER than the spot price is said to be in:

- **A.** Negative basis convergence  _(error: not a standard market-structure term)_
- **B.** Backwardation ✅
- **C.** Contango  _(error: contango is futures above spot)_
- **D.** Normal carry (full carry) market  _(error: full carry implies futures above spot by cost of carry)_

**Working**

1. Contango: F > S, rising with maturity (typical when carry costs dominate).
2. Backwardation: F < S, usually when convenience yield or supply tightness is high.

**Formula:** Basis = Spot − Futures; positive basis ⇒ backwardation  
**Trap:** Remember the direction: contango = futures above spot.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-028 · L2 · medium · Contango and backwardation

Metal M trades spot at ₹840/kg; its 6-month futures is ₹856/kg. The risk-free rate is 6.8% and storage cost is 1.5% of value p.a., both continuous. The implied convenience yield is closest to:

- **A.** 4.53% ✅
- **B.** 3.03%  _(error: storage cost ignored)_
- **C.** 3.77%  _(error: implied carry rate reported as convenience yield)_
- **D.** 6.40%  _(error: 6-month simple change not annualised)_

**Working**

1. ln(F/S)/T = ln(856/840) ÷ 0.5 = 3.77%
2. y = r + u − ln(F/S)/T = 6.8% + 1.5% − 3.77% = 4.53%

**Formula:** F = S·e^((r + u − y)T)  
**Trap:** A market can be in contango yet below full carry — the gap is the convenience yield.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-029 · L3 · hard · Contango and backwardation

Consider the following statements:

1. In a backwardated market, a long futures position rolled forward each month tends to earn a positive roll yield, other things equal.
2. A convenience yield higher than the sum of financing and storage costs is consistent with backwardation.
3. For a stock index future, contango cannot arise if the dividend yield exceeds the risk-free rate.

Which of the statements given above is/are correct?

- **A.** 1 and 3 only  _(error: statement 2 is the textbook condition for backwardation)_
- **B.** 1 and 2 only  _(error: statement 3 follows from F = S·e^((r−q)T): q > r ⇒ F < S)_
- **C.** 2 only  _(error: statement 1: roll yield is positive when longs roll into cheaper deferred contracts that converge up)_
- **D.** 1, 2 and 3 ✅

**Working**

1. 1: Deferred futures below spot drift up to spot as expiry nears → positive roll yield for longs.
2. 2: y > r + u ⇒ F < S ⇒ backwardation.
3. 3: q > r ⇒ r − q < 0 ⇒ F < S, so no contango.

**Formula:** F = S·e^((r + u − y)T); index: F = S·e^((r − q)T)  
**Trap:** Treat the dividend yield of an index like a convenience yield.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-030 · L1 · easy · Forwards vs futures

Match the feature (List I) with the contract to which it applies (List II):

| List I — Feature | List II |
|---|---|
| P. Daily mark-to-market through a clearing corporation | 1. Forward contract |
| Q. Terms tailored to the counterparties' needs | 2. Futures contract |
| R. Novation by a central counterparty | 3. Both |
| S. Obligation to transact at a pre-agreed price on a future date |  |

Codes:

- **A.** P-2, Q-1, R-2, S-3 ✅
- **B.** P-2, Q-3, R-2, S-3  _(error: futures are standardised, not customised)_
- **C.** P-3, Q-1, R-2, S-2  _(error: MTM assumed for forwards; forward also binds to a price)_
- **D.** P-2, Q-1, R-3, S-3  _(error: novation assumed for OTC forwards as well)_

**Working**

1. Futures: exchange-traded, standardised, daily MTM, CCP novation.
2. Forwards: OTC, customised, settled at maturity, bilateral counterparty risk.
3. Both are obligations at a pre-agreed price.

**Formula:** —  
**Trap:** Customisation vs standardisation is the core distinction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-031 · L3 · hard · Forwards vs futures

A trader buys 2 lots of a stock future (lot size 250) at ₹1500.00. Initial margin is ₹60,000 and maintenance margin ₹45,000 for the position. Daily settlement prices are:

| Day | 1 | 2 | 3 | 4 |
|---|---:|---:|---:|---:|
| Settlement price (₹) | 1488.00 | 1466.00 | 1462.00 | 1479.00 |

The first margin call arises on which day, and for how much (the account must be restored to the initial margin)?

- **A.** Day 3; ₹19,000  _(error: breach tested against initial margin only at a larger cumulative loss; day-2 breach missed)_
- **B.** Day 2; ₹17,000 ✅
- **C.** Day 2; ₹2,000  _(error: top-up only to maintenance margin)_
- **D.** Day 2; ₹15,000  _(error: fixed gap between initial and maintenance margin taken as the call)_

**Working**

1. Day 1: price 1488.0 → balance ₹54,000
2. Day 2: price 1466.0 → balance ₹43,000 < maintenance ₹45,000; call = ₹17,000
3. Day 3: price 1462.0 → balance ₹58,000
4. Day 4: price 1479.0 → balance ₹66,500
5. Variation margin restores the account to the initial margin, not merely to maintenance.

**Formula:** Margin a/c = IM + Σ daily MTM; call when < maintenance, restore to IM  
**Trap:** The top-up is to the initial margin level.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-032 · L2 · medium · Forwards vs futures

**Assertion (A):** If the risk-free interest rate is constant and known, the theoretical forward and futures prices for the same underlying and maturity are equal.

**Reason (R):** Daily settlement of futures creates reinvestment gains or losses whose value depends on the correlation between the underlying price and interest rates.

Choose the correct option:

- **A.** Both A and R are true, but R does not explain A ✅
- **B.** Only A is true; R is a false statement of fact  _(error: R is a correct statement of the source of forward–futures divergence)_
- **C.** Both A and R are true, and R correctly explains A  _(error: R explains why the prices DIFFER when rates are stochastic, not why they are equal)_
- **D.** Only R is true; A is a false statement of fact  _(error: A is the standard no-arbitrage result with deterministic rates)_

**Working**

1. With deterministic rates, MTM flows can be reinvested at known rates → F(forward) = F(futures).
2. R describes the divergence mechanism when rates are random and correlated with the underlying.
3. Both true, but R is not the reason for A.

**Formula:** —  
**Trap:** An R that explains the exception does not explain the rule.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-033 · L1 · easy · Hedging vs arbitrage vs speculation

Classify the following market participants correctly:

(i) An oil refiner buys crude oil futures to lock in input cost for next quarter.
(ii) A trader with no exposure buys index futures expecting a rally after a policy announcement.
(iii) A desk buys shares in the cash market and simultaneously sells the same stock's futures that are priced above fair value.

- **A.** (i) Hedger, (ii) Speculator, (iii) Arbitrageur ✅
- **B.** (i) Arbitrageur, (ii) Speculator, (iii) Hedger  _(error: refiner is protecting a business exposure)_
- **C.** (i) Speculator, (ii) Hedger, (iii) Arbitrageur  _(error: confuses offsetting an existing exposure with taking a view)_
- **D.** (i) Hedger, (ii) Arbitrageur, (iii) Speculator  _(error: arbitrage requires offsetting positions for locked-in profit)_

**Working**

1. Hedger offsets an existing or anticipated exposure.
2. Speculator takes an open position to profit from an expected price move.
3. Arbitrageur locks in a riskless profit from mispricing (cash-and-carry).

**Formula:** —  
**Trap:** Look for (a) pre-existing exposure, (b) offsetting legs.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-034 · L2 · medium · Hedging vs arbitrage vs speculation

A fund manager wants to fully hedge an equity portfolio worth ₹12 crore with a beta of 1.3 using index futures priced at 24,800 (lot size 75). The number of contracts to SELL is closest to:

- **A.** 50 contracts  _(error: portfolio value divided by beta)_
- **B.** 63 contracts  _(error: futures value computed on a lot of 100 instead of the contract lot size)_
- **C.** 65 contracts  _(error: beta ignored)_
- **D.** 84 contracts ✅

**Working**

1. Futures contract value = 24,800 × 75 = ₹18,60,000
2. N = 1.3 × 12,00,00,000 ÷ 18,60,000 = 83.87 ≈ 84

**Formula:** N = β × V_P ÷ (F × lot)  
**Trap:** Scale by beta, and by the contract (not index) value.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-035 · L3 · hard · Hedging vs arbitrage vs speculation

A cotton-yarn exporter will buy 5,00,000 kg of cotton in 3 months and hedges with cotton futures (contract size 5,000 kg). Monthly changes have σ(spot) = 2.4%, σ(futures) = 2.9% and correlation 0.85. The minimum-variance hedge requires, closest to:

- **A.** Buying 100 contracts  _(error: naïve 1:1 hedge ratio)_
- **B.** Buying 70 contracts ✅
- **C.** Selling 70 contracts  _(error: direction reversed — a future purchase is hedged with a long position)_
- **D.** Buying 103 contracts  _(error: volatilities inverted in hedge ratio)_

**Working**

1. h* = ρ × σS/σF = 0.85 × 2.4/2.9 = 0.7034
2. Contracts = 0.7034 × 5,00,000 ÷ 5,000 = 70.34 ≈ 70
3. Anticipated purchase ⇒ long hedge.

**Formula:** h* = ρ·σS/σF; N* = h* × Q_A ÷ Q_F  
**Trap:** A buyer of the physical hedges by buying futures.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-036 · L3 · hard · Hedging vs arbitrage vs speculation

A portfolio worth ₹8 crore has a beta of 1.25. The manager wants to reduce beta to 0.8 for one month using index futures at 24,000 (lot 75). The required action is:

- **A.** Sell 20 contracts ✅
- **B.** Sell 56 contracts  _(error: full hedge to beta zero computed)_
- **C.** Sell 36 contracts  _(error: target beta used instead of the change in beta)_
- **D.** Buy 20 contracts  _(error: direction reversed — reducing beta requires short futures)_

**Working**

1. N = (β* − β) × V ÷ (F × lot) = (0.8 − 1.25) × 8,00,00,000 ÷ 18,00,000 = -20.00
2. Negative ⇒ sell ≈ 20 contracts

**Formula:** N = (β* − β) × V ÷ Futures contract value  
**Trap:** Use the change in beta, not the target beta.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-037 · L1 · easy · Credit default swaps

In a single-name credit default swap, upon a credit event of the reference entity under physical settlement, the protection buyer:

- **A.** Receives only the recovery value of the defaulted reference obligation from the protection seller  _(error: seller pays par, buyer keeps the loss protection; recovery is what the buyer gives up)_
- **B.** Receives the full notional value from the seller while also retaining the reference obligations  _(error: that would be over-compensation; cash settlement pays only par − recovery)_
- **C.** Delivers the reference entity's deliverable obligations and receives their par value from the seller ✅
- **D.** Pays the CDS premium for the entire remaining tenor to the seller as a single lump sum  _(error: premium stops after the credit event, apart from accrued premium)_

**Working**

1. Physical settlement: buyer delivers the bonds/loans, seller pays par.
2. Cash settlement: seller pays notional × (1 − recovery rate).
3. Premium payments cease after the credit event (accrued premium to the event date is settled).

**Formula:** Payoff to buyer = Notional × (1 − R)  
**Trap:** The seller absorbs the loss given default.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-038 · L2 · medium · Credit default swaps

A bank buys protection on notional ₹50 crore through a 5-year CDS at a spread of 180 bp p.a., payable quarterly. Ignoring the day-count adjustment, each quarterly premium payment is:

- **A.** ₹90,00,000  _(error: annual premium paid each quarter)_
- **B.** ₹2,25,000  _(error: 180 bp read as 0.18%)_
- **C.** ₹7,50,000  _(error: monthly premium computed)_
- **D.** ₹22,50,000 ✅

**Working**

1. Annual premium = ₹50 crore × 1.80% = ₹90,00,000
2. Quarterly = ₹90,00,000 ÷ 4 = ₹22,50,000

**Formula:** Premium = Notional × Spread × (period fraction)  
**Trap:** 1 bp = 0.01%.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-039 · L2 · medium · Credit default swaps

A fund bought CDS protection on ₹25 crore notional at 240 bp p.a. (paid quarterly in arrears). A credit event occurs 2 months after the last premium date; the auction sets recovery at 35%. Under cash settlement, the net amount the fund receives (after paying accrued premium) is:

- **A.** ₹16,25,00,000  _(error: accrued premium ignored)_
- **B.** ₹16,10,00,000  _(error: full quarter's premium deducted instead of 2 months' accrual)_
- **C.** ₹16,15,00,000 ✅
- **D.** ₹8,65,00,000  _(error: recovery amount paid instead of loss (1 − R))_

**Working**

1. Protection payment = ₹25 crore × (1 − 0.35) = ₹16,25,00,000
2. Accrued premium = ₹25 crore × 2.40% × 2/12 = ₹10,00,000
3. Net = ₹16,25,00,000 − ₹10,00,000 = ₹16,15,00,000

**Formula:** Net = N(1 − R) − Accrued premium  
**Trap:** Premium accrues only to the credit-event date.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-040 · L3 · hard · Credit default swaps

The 5-year CDS spread on a corporate is 300 bp and the expected recovery rate is 40%. Using the credit-triangle approximation (constant hazard rate), the implied probability of default within the next one year is closest to:

- **A.** 3%  _(error: spread read directly as default probability)_
- **B.** 7.23%  _(error: spread divided by recovery rate instead of loss rate)_
- **C.** 5%  _(error: hazard rate reported as 1-year PD (no e^(−λ) conversion))_
- **D.** 4.88% ✅

**Working**

1. λ ≈ s ÷ (1 − R) = 0.030 ÷ 0.60 = 0.0500
2. 1-year PD = 1 − e^(−0.0500) = 4.88%

**Formula:** λ ≈ s/(1 − R); PD(t) = 1 − e^(−λt)  
**Trap:** The spread compensates for expected LOSS, not default alone.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-041 · L1 · easy · Currency risk and settlement risk

The risk that a bank pays out one currency in a foreign-exchange trade but fails to receive the counter-currency because the counterparty fails in between (often due to time-zone differences) is called:

- **A.** Replacement-cost (pre-settlement) risk, mitigated by daily mark-to-market  _(error: replacement risk arises before settlement date, not during it)_
- **B.** Economic exposure, mitigated by operational hedging such as relocating plants  _(error: economic exposure concerns long-term competitiveness)_
- **C.** Settlement (Herstatt) risk, mitigated by payment-versus-payment settlement ✅
- **D.** Translation risk, mitigated by forward cover on foreign-currency balances  _(error: translation risk relates to restating foreign-currency financial statements)_

**Working**

1. Principal risk at the settlement stage of FX trades is Herstatt risk (after Bankhaus Herstatt, 1974).
2. PvP arrangements (e.g., CLS; CCIL's guaranteed settlement for USD/INR) ensure both legs settle together.

**Formula:** —  
**Trap:** Pre-settlement (replacement) risk ≠ settlement (principal) risk.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-042 · L2 · medium · Currency risk and settlement risk

Match the exposure (List I) with its example (List II):

| List I — Exposure | List II — Example |
|---|---|
| P. Transaction exposure | 1. A rupee appreciation erodes an exporter's long-run price competitiveness against Vietnamese rivals |
| Q. Translation exposure | 2. A USD 5 million import payable due in 90 days |
| R. Economic exposure | 3. Restating a UK subsidiary's GBP balance sheet into INR for consolidation |
| S. Settlement risk | 4. Counterparty failure after the bank has paid EUR but before receiving INR |

Codes:

- **A.** P-4, Q-3, R-1, S-2  _(error: settlement risk confused with a contracted payable)_
- **B.** P-3, Q-2, R-1, S-4  _(error: transaction and translation exposures swapped)_
- **C.** P-2, Q-1, R-3, S-4  _(error: translation and economic exposures swapped)_
- **D.** P-2, Q-3, R-1, S-4 ✅

**Working**

1. Transaction: contracted foreign-currency cash flows.
2. Translation: accounting restatement of foreign operations.
3. Economic: effect on future cash flows / competitive position.
4. Settlement: principal risk at the time of exchange of currencies.

**Formula:** —  
**Trap:** Contracted cash flow = transaction; accounting restatement = translation.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-043 · L1 · easy · Active vs passive investment strategies

Which of the following is MOST characteristic of a passive (index) investment strategy?

- **A.** Frequent tactical shifts between asset classes based on valuation signals  _(error: tactical allocation is active management)_
- **B.** Replicating benchmark constituents and weights to minimise tracking error at low cost ✅
- **C.** Maximising the information ratio through active security selection and timing  _(error: information ratio is an active-management metric)_
- **D.** Holding a concentrated portfolio of the fund manager's high-conviction stocks  _(error: concentration is the opposite of index replication)_

**Working**

1. Passive funds (index funds, ETFs) seek benchmark returns, not outperformance.
2. Success is measured by low tracking error and low expense ratio.

**Formula:** —  
**Trap:** Active funds are judged by alpha/IR; passive by tracking error.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-044 · L2 · medium · Active vs passive investment strategies

An index fund reports these annual returns against its benchmark:

| Year | Fund return | Index (TRI) return |
|---|---:|---:|
| 1 | 12.40% | 12.95% |
| 2 | 8.15% | 8.62% |
| 3 | -3.10% | -2.62% |

The average annual tracking difference is:

- **A.** -0.50% ✅
- **B.** -0.18%  _(error: sign of year-3 difference reversed because both returns were negative)_
- **C.** 0.50%  _(error: sign dropped — fund underperformed, so difference is negative)_
- **D.** 0.04%  _(error: tracking error (std. deviation) reported instead of tracking difference)_

**Working**

1. Differences: -0.55%, -0.47%, -0.48%
2. Average = -0.50%

**Formula:** Tracking difference = Fund return − Benchmark return  
**Trap:** Tracking difference (level) ≠ tracking error (volatility).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-045 · L3 · hard · Active vs passive investment strategies

Monthly returns of an active fund and its benchmark are:

| Month | Fund | Benchmark |
|---|---:|---:|
| 1 | 2.1% | 1.9% |
| 2 | -0.8% | -1.1% |
| 3 | 1.5% | 1.8% |
| 4 | 3.2% | 2.7% |
| 5 | -1.2% | -1.0% |
| 6 | 0.6% | 0.4% |

Using the sample standard deviation of monthly active returns and √12 annualisation, the annualised tracking error is closest to:

- **A.** 0.35%  _(error: difference of the two volatilities taken instead of volatility of the difference)_
- **B.** 1.06% ✅
- **C.** 3.67%  _(error: annualised by multiplying by 12 instead of √12)_
- **D.** 0.31%  _(error: monthly tracking error not annualised)_

**Working**

1. Active returns: +0.2%, +0.3%, -0.3%, +0.5%, -0.2%, +0.2%
2. Sample σ (monthly) = 0.31%
3. Annualised TE = 0.31% × √12 = 1.06%

**Formula:** TE = σ(R_p − R_b) × √12  
**Trap:** TE is the volatility of the difference, not the difference in volatilities.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-046 · L3 · hard · Active vs passive investment strategies

Two actively managed large-cap funds share a benchmark that returned 13.5%.

| Fund | Return | Tracking error |
|---|---:|---:|
| Fund P | 16.2% | 4.1% |
| Fund Q | 14.8% | 1.8% |

On the basis of the information ratio, which statement is correct?

- **A.** Fund Q is superior: IR 0.72 vs 0.66 ✅
- **B.** Both are equal: IR 0.68  _(error: averaged the two funds' figures)_
- **C.** Fund Q is superior: IR 8.22 vs 3.95  _(error: total return (not active return) divided by tracking error)_
- **D.** Fund P is superior: higher active return of 2.7%  _(error: ranks on alpha, ignoring active risk)_

**Working**

1. IR(P) = (16.2% − 13.5%) ÷ 4.1% = 0.66
2. IR(Q) = (14.8% − 13.5%) ÷ 1.8% = 0.72

**Formula:** IR = (R_p − R_b) ÷ TE  
**Trap:** More alpha is not better if it costs disproportionate active risk.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-047 · L4 · hard · Bond yield and pricing

**Case — Sahyadri Retirement Trust (fictional)**

On 22 August 2026, immediately after coupon payments, the Trust's debt book is:

| Bond | Terms | Face held | Market data |
|---|---|---:|---|
| X — GoI dated security | 7.26% coupon, half-yearly (22 Feb/22 Aug), matures 22 Aug 2032, 30/360 | ₹20 crore | YTM 6.90% (semi-annual) |
| Y — AAA corporate | 8.40% annual coupon, matures 22 Aug 2034; callable at ₹102 on 22 Aug 2029 | ₹10 crore | Price ₹106.50; effective duration 2.9 |
| Z — Floating rate note | Coupon reset half-yearly to benchmark + fixed spread; next reset 22 Feb 2027 | ₹10 crore | Price ₹100.00; effective duration 0.48 |

The price of Bond X per ₹100 face value on 22 August 2026 is closest to:

- **A.** ₹101.72  _(error: annual compounding/coupons used for a half-yearly G-sec)_
- **B.** ₹101.62  _(error: one half-year period dropped (11 periods))_
- **C.** ₹101.74 ✅
- **D.** ₹100.00  _(error: discounted at the coupon rate (par value) instead of YTM)_

**Working**

1. 12 half-years; coupon ₹3.63; periodic yield 3.450%
2. Price = Σ 3.63/(1.0345)ᵗ + 100/(1.0345)¹² = ₹101.74

**Formula:** P = Σ (C/2)/(1 + y/2)ᵗ + F/(1 + y/2)²ⁿ  
**Trap:** G-secs pay half-yearly; use 2n periods at y/2.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-048 · L4 · hard · Callable and puttable securities

**Case — Sahyadri Retirement Trust (fictional)**

On 22 August 2026, immediately after coupon payments, the Trust's debt book is:

| Bond | Terms | Face held | Market data |
|---|---|---:|---|
| X — GoI dated security | 7.26% coupon, half-yearly (22 Feb/22 Aug), matures 22 Aug 2032, 30/360 | ₹20 crore | YTM 6.90% (semi-annual) |
| Y — AAA corporate | 8.40% annual coupon, matures 22 Aug 2034; callable at ₹102 on 22 Aug 2029 | ₹10 crore | Price ₹106.50; effective duration 2.9 |
| Z — Floating rate note | Coupon reset half-yearly to benchmark + fixed spread; next reset 22 Feb 2027 | ₹10 crore | Price ₹100.00; effective duration 0.48 |

The yield-to-worst on Bond Y is closest to:

- **A.** 6.57% ✅
- **B.** 7.30%  _(error: yield to maturity taken — call feature ignored)_
- **C.** 5.97%  _(error: yield to call computed with redemption at ₹100 instead of ₹102)_
- **D.** 6.93%  _(error: simple average of YTM and YTC)_

**Working**

1. YTM (8 yrs, redeem 100) = 7.30%
2. YTC (3 yrs, redeem 102) = 6.57%
3. Yield-to-worst = lower = 6.57%

**Formula:** YTW = min(YTM, YTC over all call dates)  
**Trap:** A premium callable bond is likely to be called — its worst yield is to the call.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-049 · L4 · hard · Day-count conventions

**Case — Sahyadri Retirement Trust (fictional)**

On 22 August 2026, immediately after coupon payments, the Trust's debt book is:

| Bond | Terms | Face held | Market data |
|---|---|---:|---|
| X — GoI dated security | 7.26% coupon, half-yearly (22 Feb/22 Aug), matures 22 Aug 2032, 30/360 | ₹20 crore | YTM 6.90% (semi-annual) |
| Y — AAA corporate | 8.40% annual coupon, matures 22 Aug 2034; callable at ₹102 on 22 Aug 2029 | ₹10 crore | Price ₹106.50; effective duration 2.9 |
| Z — Floating rate note | Coupon reset half-yearly to benchmark + fixed spread; next reset 22 Feb 2027 | ₹10 crore | Price ₹100.00; effective duration 0.48 |

On 9 November 2026 the Trust sells its entire holding of Bond X. The accrued interest it will receive is:

- **A.** ₹31,05,667 ✅
- **B.** ₹15,52,833  _(error: annual coupon halved and then day-fraction applied again)_
- **C.** ₹31,42,685  _(error: actual days (79) on Actual/365)_
- **D.** ₹30,63,123  _(error: 30/360 days divided by 365)_

**Working**

1. 30/360 days 22 Aug → 9 Nov = 3×30 + (9 − 22) = 77
2. Accrued = ₹20 crore × 7.26% × 77/360 = ₹31,05,667

**Formula:** AI = Face × Coupon × Days/360  
**Trap:** Half-yearly payment frequency does not change the 30/360 accrual formula.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-050 · L4 · hard · Fixed vs floating rate securities

**Case — Sahyadri Retirement Trust (fictional)**

On 22 August 2026, immediately after coupon payments, the Trust's debt book is:

| Bond | Terms | Face held | Market data |
|---|---|---:|---|
| X — GoI dated security | 7.26% coupon, half-yearly (22 Feb/22 Aug), matures 22 Aug 2032, 30/360 | ₹20 crore | YTM 6.90% (semi-annual) |
| Y — AAA corporate | 8.40% annual coupon, matures 22 Aug 2034; callable at ₹102 on 22 Aug 2029 | ₹10 crore | Price ₹106.50; effective duration 2.9 |
| Z — Floating rate note | Coupon reset half-yearly to benchmark + fixed spread; next reset 22 Feb 2027 | ₹10 crore | Price ₹100.00; effective duration 0.48 |

Using Bond X's modified duration and the effective durations given for Y and Z, the market-value-weighted duration of the book is closest to:

- **A.** 3.25  _(error: weights based on face value instead of market value)_
- **B.** 5.09  _(error: FRN assigned a duration equal to its residual maturity)_
- **C.** 3.26 ✅
- **D.** 3.34  _(error: Macaulay duration of X used instead of modified)_

**Working**

1. X: Macaulay 4.979 yrs → modified 4.979/1.0345 = 4.813
2. Market values: X ₹20.35 crore, Y ₹10.65 crore, Z ₹10.00 crore; total ₹41.00 crore
3. Weighted duration = 3.259

**Formula:** D_p = Σ wᵢ Dᵢ, wᵢ = MVᵢ/ΣMV  
**Trap:** An FRN contributes only its time-to-reset duration.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-051 · L4 · hard · Bond yield and pricing

**Case — Sahyadri Retirement Trust (fictional)**

On 22 August 2026, immediately after coupon payments, the Trust's debt book is:

| Bond | Terms | Face held | Market data |
|---|---|---:|---|
| X — GoI dated security | 7.26% coupon, half-yearly (22 Feb/22 Aug), matures 22 Aug 2032, 30/360 | ₹20 crore | YTM 6.90% (semi-annual) |
| Y — AAA corporate | 8.40% annual coupon, matures 22 Aug 2034; callable at ₹102 on 22 Aug 2029 | ₹10 crore | Price ₹106.50; effective duration 2.9 |
| Z — Floating rate note | Coupon reset half-yearly to benchmark + fixed spread; next reset 22 Feb 2027 | ₹10 crore | Price ₹100.00; effective duration 0.48 |

If all yields rise in parallel by 40 bp, the estimated change in the book's market value (duration only) is closest to:

- **A.** −₹78.94 lakh  _(error: Bond X's duration applied to the whole book)_
- **B.** −₹52.15 lakh  _(error: applied to face value instead of market value)_
- **C.** −₹26.73 lakh  _(error: semi-annual yield change (20 bp) used)_
- **D.** −₹53.45 lakh ✅

**Working**

1. Portfolio duration = 3.259; market value = ₹41.00 crore
2. ΔV ≈ −3.259 × 0.0040 × 40,99,89,060 = −₹53.45 lakh

**Formula:** ΔV ≈ −D_mod × Δy × V  
**Trap:** Use market value, not face.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-052 · L4 · hard · Forward pricing and cost of carry

**Case — Meru Capital's derivatives desk (fictional)**

| Item | Data |
|---|---:|
| Equity index spot | 24,500 |
| 3-month index futures (market) | 24,950 |
| Risk-free rate (continuous) | 6.8% |
| Index dividend yield (continuous) | 1.4% |
| Index futures lot size | 65 |
| Client equity portfolio | ₹15 crore, beta 1.15 |

The desk may borrow and lend at the risk-free rate; ignore transaction costs and taxes.

Based on cost of carry, the index futures is:

- **A.** Overpriced by 450.00 points — sell futures, buy the index basket  _(error: basis (F − S) treated as mispricing; carry ignored)_
- **B.** Underpriced by 117.01 points — buy futures, short the basket  _(error: direction reversed)_
- **C.** Overpriced by 117.01 points — sell futures, buy the index basket ✅
- **D.** Overpriced by 29.94 points — sell futures, buy the index basket  _(error: dividend yield ignored in fair value)_

**Working**

1. Fair F = 24,500 × e^((0.068 − 0.014)×0.25) = 24832.99
2. Market F − fair F = 117.01 > 0 ⇒ overpriced ⇒ cash-and-carry

**Formula:** F* = S·e^((r − q)T)  
**Trap:** Mispricing is measured against fair value, not against spot.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-053 · L4 · hard · Hedging vs arbitrage vs speculation

**Case — Meru Capital's derivatives desk (fictional)**

| Item | Data |
|---|---:|
| Equity index spot | 24,500 |
| 3-month index futures (market) | 24,950 |
| Risk-free rate (continuous) | 6.8% |
| Index dividend yield (continuous) | 1.4% |
| Index futures lot size | 65 |
| Client equity portfolio | ₹15 crore, beta 1.15 |

The desk may borrow and lend at the risk-free rate; ignore transaction costs and taxes.

To hedge the client's portfolio fully against market risk using the 3-month futures at the market price, the desk should sell approximately:

- **A.** 108 contracts  _(error: spot index used instead of futures price (acceptable only as approximation))_
- **B.** 106 contracts ✅
- **C.** 16 contracts  _(error: divided by lot size twice)_
- **D.** 92 contracts  _(error: beta ignored)_

**Working**

1. Contract value = 24,950 × 65 = ₹16,21,750
2. N = 1.15 × 15,00,00,000 ÷ 16,21,750 = 106.37 ≈ 106

**Formula:** N = β × V ÷ (F × lot)  
**Trap:** Hedge on the futures contract value.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-054 · L4 · hard · Hedging vs arbitrage vs speculation

**Case — Meru Capital's derivatives desk (fictional)**

| Item | Data |
|---|---:|
| Equity index spot | 24,500 |
| 3-month index futures (market) | 24,950 |
| Risk-free rate (continuous) | 6.8% |
| Index dividend yield (continuous) | 1.4% |
| Index futures lot size | 65 |
| Client equity portfolio | ₹15 crore, beta 1.15 |

The desk may borrow and lend at the risk-free rate; ignore transaction costs and taxes.

The desk sells 106 contracts. One month later the index is 23,800 and the futures 24,120. Assuming the portfolio moves exactly per its beta (ignore dividends), the net gain/loss on the hedged position is closest to:

- **A.** Gain of ₹14.33 lakh  _(error: portfolio loss computed without beta)_
- **B.** Loss of ₹49.29 lakh  _(error: futures gain ignored (unhedged loss))_
- **C.** Gain of ₹7.90 lakh ✅
- **D.** Loss of ₹1.06 lakh  _(error: futures gain measured on spot change (basis change ignored))_

**Working**

1. Index return = 23800/24500 − 1 = -2.86%; portfolio change = 1.15 × that × ₹15 crore = ₹-49.29 lakh
2. Futures gain = 106 × 65 × (24,950 − 24,120) = ₹57.19 lakh
3. Net = ₹7.90 lakh — residual reflects basis narrowing and rounding

**Formula:** Hedged P&L = β·V·r_index + N·lot·(F₀ − F₁)  
**Trap:** Basis risk: futures moved by a different amount from spot.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-055 · L4 · hard · Forwards vs futures

**Case — Meru Capital's derivatives desk (fictional)**

| Item | Data |
|---|---:|
| Equity index spot | 24,500 |
| 3-month index futures (market) | 24,950 |
| Risk-free rate (continuous) | 6.8% |
| Index dividend yield (continuous) | 1.4% |
| Index futures lot size | 65 |
| Client equity portfolio | ₹15 crore, beta 1.15 |

The desk may borrow and lend at the risk-free rate; ignore transaction costs and taxes.

The client asks whether a 3-month OTC forward with a bank on the index would have been equivalent. Which statement is correct?

- **A.** The forward would eliminate basis risk entirely because it is a standardised contract with exchange-fixed lot sizes and expiry dates  _(error: forwards are customised, not standardised; basis risk depends on maturity match)_
- **B.** The forward would require daily variation margin to be paid through the clearing corporation, exactly as the futures contract does  _(error: OTC forwards are not novated/MTM'd by an exchange CCP)_
- **C.** The forward settles only at maturity, leaving bank counterparty risk; futures gains and losses settle daily via the clearing corporation ✅
- **D.** The forward price would necessarily be higher than the futures price because the bank bears the client's counterparty risk  _(error: with deterministic rates forward ≈ futures price; credit terms are priced separately)_

**Working**

1. Forwards: bilateral, settled at maturity, counterparty credit risk.
2. Futures: daily MTM, CCP novation, standardised lots and expiries.

**Formula:** —  
**Trap:** Customisation can reduce basis risk; standardisation is a futures feature.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-056 · L4 · hard · Contango and backwardation

**Case — Meru Capital's derivatives desk (fictional)**

| Item | Data |
|---|---:|
| Equity index spot | 24,500 |
| 3-month index futures (market) | 24,950 |
| Risk-free rate (continuous) | 6.8% |
| Index dividend yield (continuous) | 1.4% |
| Index futures lot size | 65 |
| Client equity portfolio | ₹15 crore, beta 1.15 |

The desk may borrow and lend at the risk-free rate; ignore transaction costs and taxes.

Which description of the index futures market structure on this date is correct?

- **A.** Contango only because the futures is mispriced; at fair value the market would be in backwardation  _(error: fair value is also above spot since r > q)_
- **B.** Backwardation, since dividend yield reduces the fair price below spot  _(error: r > q so fair F > S — still contango)_
- **C.** Contango, with the observed basis (spot − futures) of -450 points; the fair-value basis is -332.99 points ✅
- **D.** Contango, with basis of 450 points and fair-value basis of 332.99 points, both positive  _(error: basis sign convention (spot − futures) reversed)_

**Working**

1. Observed basis = 24,500 − 24,950 = -450 (negative ⇒ futures above spot ⇒ contango)
2. Fair F = 24832.99 > spot since r − q > 0; fair basis = -332.99

**Formula:** Basis = S − F  
**Trap:** Contango holds even at fair value whenever r > q.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-057 · L4 · hard · Currency risk and settlement risk

**Case — Kaveri Textiles Ltd (fictional)**

Kaveri will receive USD 2 million from a US buyer in 6 months. Market data today:

| Item | Data |
|---|---:|
| Spot USD/INR | ₹84.20 |
| 6-month forward USD/INR | ₹85.10 |
| INR deposit rate (simple p.a.) | 7.2% |
| USD borrowing rate (simple p.a.) | 5.1% |
| 6-month USD put option (strike ₹84.80) | premium ₹0.65 per USD, paid today |

Under a money-market hedge (borrow USD now, convert at spot, deposit INR), Kaveri's INR proceeds at the end of 6 months are closest to:

- **A.** ₹16.4213 crore  _(error: INR deposit interest ignored)_
- **B.** ₹17.4462 crore  _(error: borrowed the full USD 2 million instead of its present value)_
- **C.** ₹17.1765 crore  _(error: annual rates applied to a 6-month period)_
- **D.** ₹17.0124 crore ✅

**Working**

1. USD to borrow = 2,000,000 ÷ (1 + 0.051×0.5) = 1,950,268.16
2. Convert at spot: × 84.20 = ₹164,212,579
3. Deposit 6 months at 7.2%: × 1.036 = ₹17.0124 crore

**Formula:** MMH proceeds = [FC ÷ (1 + r_f·T)] × S × (1 + r_d·T)  
**Trap:** Borrow only the PV of the receivable so that the receivable repays the loan exactly.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-058 · L4 · hard · Currency risk and settlement risk

**Case — Kaveri Textiles Ltd (fictional)**

Kaveri will receive USD 2 million from a US buyer in 6 months. Market data today:

| Item | Data |
|---|---:|
| Spot USD/INR | ₹84.20 |
| 6-month forward USD/INR | ₹85.10 |
| INR deposit rate (simple p.a.) | 7.2% |
| USD borrowing rate (simple p.a.) | 5.1% |
| 6-month USD put option (strike ₹84.80) | premium ₹0.65 per USD, paid today |

If spot at maturity turns out to be ₹84.40, rank the three alternatives by INR received (option premium carried forward at the INR deposit rate):

- **A.** Option ₹17.0947 crore > Forward ₹17.0200 crore > Unhedged ₹16.8800 crore  _(error: premium added to (instead of deducted from) the strike)_
- **B.** Forward ₹17.0200 crore > Option ₹16.9600 crore > Unhedged ₹16.8800 crore  _(error: premium cost ignored — option valued at strike)_
- **C.** Forward ₹17.0200 crore > Unhedged ₹16.8800 crore > Option ₹16.8253 crore ✅
- **D.** Forward ₹17.0200 crore > Unhedged ₹16.8800 crore > Option ₹16.7453 crore  _(error: put treated as lapsed although spot < strike)_

**Working**

1. Forward: 2 mn × 85.10 = ₹17.0200 crore
2. Put exercised (84.40 < 84.80): 2 mn × (84.80 − 0.65×1.036 = 84.1266) = ₹16.8253 crore
3. Unhedged: 2 mn × 84.40 = ₹16.8800 crore
4. The small rupee move leaves the option's floor (net of premium) below the unhedged outcome.

**Formula:** Put outcome = max(K, S_T) − Premium × (1 + r·T)  
**Trap:** An option's floor is net of its premium cost; a modest move may not recover the premium.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-059 · L4 · hard · Currency risk and settlement risk

**Case — Kaveri Textiles Ltd (fictional)**

Kaveri will receive USD 2 million from a US buyer in 6 months. Market data today:

| Item | Data |
|---|---:|
| Spot USD/INR | ₹84.20 |
| 6-month forward USD/INR | ₹85.10 |
| INR deposit rate (simple p.a.) | 7.2% |
| USD borrowing rate (simple p.a.) | 5.1% |
| 6-month USD put option (strike ₹84.80) | premium ₹0.65 per USD, paid today |

Kaveri's bank books the forward and, on maturity, settles the USD/INR leg through CCIL's guaranteed settlement. Which statement about the risks involved is correct?

- **A.** CCIL's central-counterparty role curbs interbank settlement risk; until maturity Kaveri still faces replacement-cost (pre-settlement) risk on its bank ✅
- **B.** Settlement through CCIL eliminates Kaveri's own transaction exposure to the rupee, so booking the forward with its bank is unnecessary  _(error: CCP settlement removes interbank principal risk, not the exporter's price exposure)_
- **C.** Herstatt risk is highest for USD/INR trades because both currencies settle in the same time zone, so CCIL cannot mitigate it at all  _(error: Herstatt risk arises from time-zone gaps; PvP/CCP mitigates it)_
- **D.** Replacement-cost risk exists only for option contracts and not for forwards, so Kaveri has no counterparty risk at all on its bank  _(error: a forward with positive MTM has replacement cost if the counterparty defaults)_

**Working**

1. CCIL novates interbank USD/INR trades and settles them on a guaranteed basis — mitigates principal/settlement risk.
2. The client–bank forward remains a bilateral contract; before maturity the risk is pre-settlement (replacement cost).

**Formula:** —  
**Trap:** Distinguish interbank settlement risk from the client's counterparty risk.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-060 · L1 · easy · Asset classification, NPA and divergence disclosure ⚠

Under RBI's framework for early recognition of stress, a term loan (not a revolving facility) whose principal or interest has remained overdue for 75 days is classified as:

- **A.** SMA-0  _(error: SMA-0 covers up to 30 days overdue)_
- **B.** SMA-1  _(error: SMA-1 covers 31–60 days overdue)_
- **C.** Sub-standard (NPA)  _(error: NPA only after overdue for more than 90 days)_
- **D.** SMA-2 ✅

**Working**

1. SMA-0: 1–30 days; SMA-1: 31–60 days; SMA-2: 61–90 days overdue.
2. Beyond 90 days the account becomes an NPA (sub-standard).

**Formula:** Overdue 61–90 days ⇒ SMA-2  
**Trap:** SMA categories are standard assets; NPA begins after 90 days.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-061 · L2 · medium · Asset classification, NPA and divergence disclosure ⚠

A secured term loan was classified as NPA on 31 March 2025 and has remained NPA since, with realisable security. As on 30 September 2027 its asset classification is:

- **A.** Loss asset  _(error: loss classification depends on the security being identified as uncollectible, not on age alone)_
- **B.** Doubtful — D1  _(error: counts doubtful period from the NPA date instead of after 12 months as sub-standard)_
- **C.** Doubtful — D2 ✅
- **D.** Doubtful — D3  _(error: counts total NPA age (2.5 years) as the doubtful period and misreads the D3 band)_

**Working**

1. Sub-standard: 31 Mar 2025 → 31 Mar 2026 (12 months).
2. Doubtful from 31 Mar 2026; by 30 Sep 2027 it has been doubtful for 18 months.
3. D1 ≤ 1 year; D2 > 1 to 3 years; D3 > 3 years ⇒ D2.

**Formula:** Doubtful age = NPA age − 12 months  
**Trap:** The doubtful clock starts only after 12 months as sub-standard.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-062 · L3 · hard · Asset classification, NPA and divergence disclosure ⚠

Shivalik Bank (fictional) has the following advances portfolio:

| Category | Outstanding | Realisable security |
|---|---:|---:|
| Standard assets (general category) | ₹500 crore | — |
| Sub-standard — secured | ₹40 crore | — |
| Sub-standard — unsecured exposure (ab initio) | ₹10 crore | — |
| Doubtful D1 | ₹30 crore | ₹18 crore |
| Doubtful D3 | ₹12 crore | ₹5 crore |
| Loss assets | ₹4 crore | — |

Applying RBI's minimum provisioning norms (standard 0.40%; sub-standard 15%, unsecured sub-standard 25%; doubtful secured portion D1 25%, D2 40%, D3 100%; unsecured portion of doubtful 100%; loss 100%), total provision required is:

- **A.** ₹42.00 crore  _(error: unsecured sub-standard exposure provided at 15%)_
- **B.** ₹41.00 crore  _(error: standard asset provision omitted)_
- **C.** ₹34.00 crore  _(error: entire D1 balance provided at 25% (unsecured portion not segregated))_
- **D.** ₹43.00 crore ✅

**Working**

1. Standard: 0.40% × 500 = ₹2.00 cr
2. Sub-standard: 15% × 40 + 25% × 10 = ₹8.50 cr
3. D1: 25% × 18 + 100% × 12 = ₹16.50 cr
4. D3: 100% × 12 = ₹12.00 cr; Loss: ₹4.00 cr
5. Total = ₹43.00 crore

**Formula:** Doubtful provision = Secured portion × age rate + Unsecured portion × 100%  
**Trap:** Split doubtful assets into secured and unsecured portions.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-063 · L2 · medium · Asset classification, NPA and divergence disclosure ⚠

After RBI's annual supervisory assessment of a listed bank: reported profit before provisions and contingencies = ₹800 crore; additional provisioning assessed by RBI = ₹90 crore; published incremental gross NPAs for the year = ₹1,000 crore; additional gross NPAs identified by RBI = ₹120 crore. Under RBI's divergence-disclosure norms (thresholds: 10% of reported profit before provisions and contingencies; 15% of published incremental GNPAs), the bank:

- **A.** Need not disclose, because both the thresholds must be breached together in a year  _(error: the tests are alternative (and/or), not cumulative)_
- **B.** Must disclose: extra provisioning (11.25%) exceeds 10%, though extra GNPA (12%) is within 15% ✅
- **C.** Need not disclose, as divergence disclosure applies only if net profit turns into a loss  _(error: that is not the trigger; loss-turn is only one of the listed disclosure items)_
- **D.** Must disclose, because the extra GNPA (12%) exceeds the 10% threshold for GNPA  _(error: 10% threshold misapplied to GNPA divergence (GNPA test is 15%))_

**Working**

1. Additional provisioning ÷ profit before provisions = 90 ÷ 800 = 11.25% > 10% ⇒ trigger
2. Additional GNPA ÷ incremental GNPA = 12% ≤ 15%
3. Either condition triggers disclosure in notes to accounts.

**Formula:** Disclose if ΔProv > 10% of PBP&C OR ΔGNPA > 15% of incremental GNPA  
**Trap:** The two thresholds are alternatives.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-064 · L1 · easy · Bank advances — cash credit, overdraft, bill discounting

Match the credit facility (List I) with its description (List II):

| List I | List II |
|---|---|
| P. Cash credit | 1. Running account in which a current-account holder may overdraw up to a sanctioned limit, often against collateral such as FDs |
| Q. Overdraft | 2. Revolving limit against hypothecation/pledge of stock and book debts, drawable within drawing power |
| R. Bill discounting | 3. Bank pays the present value of a usance bill and collects the full amount at maturity |
| S. Letter of credit | 4. Bank's undertaking to pay the beneficiary against complying documents |

Codes:

- **A.** P-2, Q-1, R-4, S-3  _(error: bill discounting confused with a documentary credit)_
- **B.** P-2, Q-3, R-1, S-4  _(error: overdraft confused with bill finance)_
- **C.** P-1, Q-2, R-3, S-4  _(error: cash credit and overdraft descriptions swapped)_
- **D.** P-2, Q-1, R-3, S-4 ✅

**Working**

1. Cash credit: working-capital limit secured by current assets, subject to drawing power.
2. Overdraft: overdrawing a current account up to a limit.
3. Bill discounting: bank advances discounted value of a trade bill.
4. LC: non-fund-based undertaking.

**Formula:** —  
**Trap:** Drawing power is the hallmark of cash credit.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-065 · L2 · medium · Bank advances — cash credit, overdraft, bill discounting

A bank discounts a trade bill of ₹5,00,000 with 60 days to maturity at 10% p.a. (Actual/365) and charges a collection commission of 0.25% of the bill amount. The net amount credited to the customer is:

- **A.** ₹4,91,781  _(error: commission ignored)_
- **B.** ₹4,90,417  _(error: 360-day year used)_
- **C.** ₹4,90,531 ✅
- **D.** ₹4,90,664  _(error: true discount (PV basis) used instead of banker's discount on face)_

**Working**

1. Discount = ₹5,00,000 × 10% × 60/365 = ₹8,219
2. Commission = ₹1,250
3. Net = ₹5,00,000 − ₹8,219 − ₹1,250 = ₹4,90,531

**Formula:** Banker's discount = Face × r × t  
**Trap:** Banks deduct discount on the face value of the bill.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-066 · L3 · hard · Bank advances — cash credit, overdraft, bill discounting

An overdraft account shows the following debit balances during a 30-day month (interest at 11.5% p.a. on daily products, Actual/365):

| Period (days) | Debit balance (₹) |
|---|---:|
| 8 | 12,00,000 |
| 10 | 18,50,000 |
| 7 | 9,00,000 |
| 5 | 16,00,000 |

The interest debited for the month is:

- **A.** ₹13,115  _(error: simple average of balances used, ignoring days)_
- **B.** ₹13,544  _(error: 360-day year used)_
- **C.** ₹13,359 ✅
- **D.** ₹17,486  _(error: interest on the peak balance)_

**Working**

1. Products = 8×12,00,000 + 10×18,50,000 + 7×9,00,000 + 5×16,00,000 = 4,24,00,000
2. Interest = 4,24,00,000 × 11.5% ÷ 365 = ₹13,359

**Formula:** Interest = Σ(balance × days) × r ÷ 365  
**Trap:** Weight each balance by the days it was outstanding.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-067 · L1 · easy · Banking Regulation Act 1949 — licensing, s.35A, scheduled banks ⚠

Under Section 35A of the Banking Regulation Act, 1949, the Reserve Bank of India may issue directions to banking companies when it is satisfied that it is necessary:

- **A.** Only on a reference from the Central Government under Section 45, after a moratorium has first been declared on the bank concerned  _(error: s.35A is RBI's own power; s.45 deals with moratorium/reconstruction)_
- **B.** In public interest or banking policy, to stop affairs being run against depositors' or the bank's interest, or to secure proper management ✅
- **C.** Only after obtaining the prior approval of the Financial Stability and Development Council, chaired by the Union Finance Minister  _(error: FSDC is a non-statutory coordination body with no such role)_
- **D.** Only to fix the rate of interest payable on deposits of scheduled banks, and for no other purpose whatsoever under the Act  _(error: interest-rate directions are only one application of s.21/s.35A, not the test)_

**Working**

1. s.35A(1) lists the grounds: public interest, banking policy, protection of depositors/bank, proper management.
2. Directions are binding; RBI may modify or cancel them.

**Formula:** —  
**Trap:** s.35A is a broad, self-standing RBI power.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-068 · L2 · medium · Banking Regulation Act 1949 — licensing, s.35A, scheduled banks ⚠

Consider the following statements:

1. No company can carry on banking business in India without a licence issued by the RBI under Section 22 of the Banking Regulation Act, 1949.
2. For inclusion in the Second Schedule to the RBI Act, 1934, a bank must have paid-up capital and reserves of an aggregate value of not less than ₹5 lakh and satisfy the RBI that its affairs are not conducted detrimentally to depositors.
3. Section 24 of the Banking Regulation Act prescribes a statutory floor of 25% of NDTL for SLR.

Which of the statements given above is/are correct?

- **A.** 1 only  _(error: statement 2 correctly states the s.42(6) RBI Act criteria)_
- **B.** 2 and 3 only  _(error: statement 1 correctly states the licensing requirement)_
- **C.** 1 and 2 only ✅
- **D.** 1, 2 and 3  _(error: the 25% SLR floor was removed by the 2007 amendment; only a 40% ceiling remains)_

**Working**

1. s.22 BR Act: licence from RBI mandatory — correct.
2. s.42(6)(a) RBI Act: ₹5 lakh paid-up capital + reserves and depositor-interest test — correct.
3. s.24 now only sets a ceiling (40%); no floor — incorrect.

**Formula:** —  
**Trap:** Old SLR floor of 25% no longer exists.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-069 · L2 · medium · Banking Regulation Act 1949 — licensing, s.35A, scheduled banks ⚠

Match the provision of the Banking Regulation Act, 1949 (List I) with its subject (List II):

| List I | List II |
|---|---|
| P. Section 5(b) | 1. Licensing of banking companies |
| Q. Section 22 | 2. Definition of 'banking' |
| R. Section 35A | 3. RBI may apply to the Central Government for a moratorium; scheme of reconstruction or amalgamation |
| S. Section 45 | 4. Power of the RBI to give directions |

Codes:

- **A.** P-2, Q-1, R-3, S-4  _(error: direction power and moratorium section swapped)_
- **B.** P-1, Q-2, R-4, S-3  _(error: definition and licensing sections swapped)_
- **C.** P-2, Q-4, R-1, S-3  _(error: licensing confused with directions)_
- **D.** P-2, Q-1, R-4, S-3 ✅

**Working**

1. s.5(b): banking = accepting deposits of money from the public for lending/investment, repayable on demand or otherwise, withdrawable by cheque, draft or otherwise.
2. s.22 licensing; s.35A directions; s.45 moratorium and reconstruction/amalgamation.

**Formula:** —  
**Trap:** s.45 (not s.44A) is the compulsory reconstruction route.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-070 · L1 · easy · Basel norms and capital adequacy ⚠

Under RBI's Basel III capital regulations, the minimum Common Equity Tier 1 ratio a bank must maintain INCLUDING the capital conservation buffer (and excluding any D-SIB surcharge or countercyclical buffer) is:

- **A.** 5.5% of risk-weighted assets  _(error: CET1 minimum without the conservation buffer)_
- **B.** 8.0% of risk-weighted assets ✅
- **C.** 11.5% of risk-weighted assets  _(error: total capital + CCB, not CET1)_
- **D.** 7.0% of risk-weighted assets  _(error: BCBS global CET1 + CCB (4.5% + 2.5%))_

**Working**

1. RBI CET1 minimum = 5.5%; CCB = 2.5% (in CET1).
2. CET1 + CCB = 8.0%; Tier 1 minimum 7%; total capital 9% (+ CCB = 11.5%).

**Formula:** CET1 + CCB = 5.5% + 2.5%  
**Trap:** RBI's minima are stricter than BCBS (4.5%/6%/8%).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-071 · L1 · easy · Basel norms and capital adequacy

Match the Basel pillar (List I) with its content (List II):

| List I | List II |
|---|---|
| P. Pillar 1 | 1. Disclosure requirements to promote market discipline |
| Q. Pillar 2 | 2. Minimum capital for credit, market and operational risk |
| R. Pillar 3 | 3. Supervisory review, including the bank's ICAAP |

Codes:

- **A.** P-2, Q-3, R-1 ✅
- **B.** P-1, Q-3, R-2  _(error: pillar order reversed for 1 and 3)_
- **C.** P-3, Q-2, R-1  _(error: minimum capital and supervisory review swapped)_
- **D.** P-2, Q-1, R-3  _(error: supervisory review and disclosure swapped)_

**Working**

1. Pillar 1: minimum capital requirements.
2. Pillar 2: SREP/ICAAP.
3. Pillar 3: market discipline via disclosures.

**Formula:** —  
**Trap:** ICAAP belongs to Pillar 2.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-072 · L2 · medium · Basel norms and capital adequacy

A bank reports CET1 capital ₹5,400 crore, Additional Tier 1 ₹900 crore and Tier 2 ₹1,500 crore (all eligible). Risk-weighted assets are: credit ₹60,000 crore, market ₹5,000 crore and operational ₹7,000 crore. Its CRAR is:

- **A.** 12%  _(error: operational risk RWA omitted)_
- **B.** 10.83% ✅
- **C.** 8.75%  _(error: Tier 1 ratio reported instead of CRAR)_
- **D.** 13%  _(error: only credit RWA used as denominator)_

**Working**

1. Total capital = ₹7,800 crore
2. Total RWA = ₹72,000 crore
3. CRAR = 10.83%

**Formula:** CRAR = (Tier 1 + Tier 2) ÷ (Credit + Market + Operational RWA)  
**Trap:** All three risk categories enter the denominator.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-073 · L3 · hard · Basel norms and capital adequacy

Compute credit risk-weighted assets (₹ crore) from the following, using the CCFs and risk weights given:

| Exposure | Amount (₹ cr) | CCF | Risk weight |
|---|---:|---:|---:|
| Claims on the Government of India | 2,000 | 100% | 0% |
| Claims on scheduled banks | 800 | 100% | 20% |
| Rated corporate loans | 1,500 | 100% | 50% |
| Regulatory retail portfolio | 1,000 | 100% | 75% |
| Undrawn committed lines (off-balance sheet) | 600 | 20% | 100% |
| Financial guarantees issued (off-balance sheet) | 400 | 100% | 100% |

Credit RWA is:

- **A.** ₹2,660 crore  _(error: credit conversion factors ignored for off-balance-sheet items)_
- **B.** ₹2,820 crore  _(error: claims on banks taken at 100% risk weight)_
- **C.** ₹2,180 crore ✅
- **D.** ₹1,660 crore  _(error: off-balance-sheet exposures left out)_

**Working**

1. On-B/S: 0 + 800×20% + 1500×50% + 1000×75% = 1,660
2. Off-B/S: 600×20%×100% + 400×100%×100% = 520
3. Total = ₹2,180 crore

**Formula:** RWA = Exposure × CCF × Risk weight  
**Trap:** Convert off-balance-sheet items to credit equivalents first.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-074 · L3 · hard · Basel norms and capital adequacy ⚠

A bank has Tier 1 capital of ₹7,200 crore, Tier 2 instruments of ₹900 crore and general provisions/floating provisions of ₹1,100 crore available for Tier 2. Credit RWA are ₹64,000 crore; market and operational RWA together are ₹12,000 crore. Given that general provisions count in Tier 2 only up to 1.25% of credit RWA, the CRAR is:

- **A.** 12.11%  _(error: general provisions included without the 1.25% cap)_
- **B.** 11.91%  _(error: 1.25% cap applied to total RWA instead of credit RWA)_
- **C.** 11.71% ✅
- **D.** 10.66%  _(error: general provisions excluded altogether)_

**Working**

1. Cap = 1.25% × ₹64,000 crore = ₹800 crore; eligible = ₹800 crore
2. Total capital = ₹7,200 crore + ₹900 crore + ₹800 crore = ₹8,900 crore
3. CRAR = ₹8,900 crore ÷ ₹76,000 crore = 11.71%

**Formula:** Eligible GP in Tier 2 = min(GP, 1.25% × credit RWA)  
**Trap:** The cap is on credit RWA only.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-075 · L1 · easy · Capital and leverage norms; D-SIBs ⚠

Under RBI's leverage ratio framework, the minimum leverage ratio prescribed for Domestic Systemically Important Banks (D-SIBs) and for other scheduled commercial banks respectively is:

- **A.** 4.0% and 3.5% ✅
- **B.** 4.5% and 4.0%  _(error: CET1 floor of BCBS confused with leverage ratio)_
- **C.** 3.0% and 3.0%  _(error: BCBS minimum applied to all banks)_
- **D.** 3.5% and 4.0%  _(error: values interchanged)_

**Working**

1. RBI (June 2019): leverage ratio ≥ 4% for D-SIBs and ≥ 3.5% for other banks.
2. Leverage ratio = Tier 1 capital ÷ Exposure measure.

**Formula:** —  
**Trap:** India's leverage ratio floor is above the Basel 3% minimum.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-076 · L2 · medium · Capital and leverage norms; D-SIBs

A bank has Tier 1 capital of ₹12,000 crore. Its exposure measure comprises on-balance-sheet exposures ₹280,000 crore, derivative exposures ₹6,000 crore, securities financing transaction exposures ₹4,000 crore and off-balance-sheet items (after CCFs) ₹20,000 crore. Its leverage ratio is:

- **A.** 3.08%  _(error: off-balance-sheet items grossed up to notional (CCF reversed))_
- **B.** 4.29%  _(error: only on-balance-sheet exposures used)_
- **C.** 3.87% ✅
- **D.** 4.14%  _(error: off-balance-sheet items omitted)_

**Working**

1. Exposure measure = ₹310,000 crore
2. Leverage ratio = ₹12,000 crore ÷ ₹310,000 crore = 3.87%

**Formula:** Leverage ratio = Tier 1 ÷ (On-B/S + Derivatives + SFT + Off-B/S after CCF)  
**Trap:** Unlike CRAR, exposures are not risk-weighted.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-077 · L2 · medium · Capital and leverage norms; D-SIBs ⚠

Consider the following statements about RBI's D-SIB framework:

1. Banks identified as D-SIBs must hold an additional Common Equity Tier 1 surcharge over and above the capital conservation buffer.
2. D-SIBs are placed in buckets according to their systemic importance scores, and a higher bucket attracts a higher surcharge.
3. The D-SIB surcharge substitutes for the capital conservation buffer, so a D-SIB need not maintain CCB.

Which of the statements given above is/are correct?

- **A.** 2 only  _(error: statement 1 is correct — surcharge is in CET1)_
- **B.** 1, 2 and 3  _(error: surcharge is additional to CCB, not a substitute)_
- **C.** 1 and 2 only ✅
- **D.** 1 and 3 only  _(error: statements 1 and 3 contradict each other)_

**Working**

1. Surcharge (0.20% to 1.00% of RWA by bucket) is in CET1, over and above CCB.
2. Bucket placement is by systemic importance score.
3. Statement 3 is incorrect.

**Formula:** —  
**Trap:** Buffers stack: minimum + CCB + D-SIB surcharge (+ CCyB).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-078 · L1 · easy · Business correspondents ⚠

Consider the following statements about the Business Correspondent (BC) model:

1. The bank remains fully responsible for the acts and omissions of its BCs.
2. BCs may undertake cash-in/cash-out transactions on behalf of the bank, while Business Facilitators may not handle cash.
3. A BC may levy its own service charges directly on customers without the bank's involvement.

Which of the statements given above is/are correct?

- **A.** 2 only  _(error: statement 1 is a core RBI condition)_
- **B.** 1 and 2 only ✅
- **C.** 1 and 3 only  _(error: statement 3 is contrary to RBI guidelines)_
- **D.** 1, 2 and 3  _(error: BCs cannot charge customers directly; charges are levied by the bank)_

**Working**

1. The bank is the principal and responsible for its BC agents.
2. BCs handle cash and small-value transactions; BFs only facilitate (no cash).
3. Customers pay the bank's (reasonable, disclosed) charges, not BC-levied charges.

**Formula:** —  
**Trap:** BC = agent of the bank; the bank bears the liability.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-079 · L2 · medium · Business correspondents ⚠

**Assertion (A):** Payments banks and small finance banks can use Business Correspondents to extend their reach.

**Reason (R):** RBI permits only individuals, and not companies, to act as Business Correspondents.

Choose the correct option:

- **A.** Both A and R are true, and R correctly explains A  _(error: R is false — for-profit companies incl. non-deposit-taking NBFCs may be BCs)_
- **B.** Only A is true; R is a false statement of fact ✅
- **C.** Only R is true; A is a false statement of fact  _(error: A is true; differentiated banks rely heavily on BC/agent networks)_
- **D.** Both A and R are true, but R does not explain A  _(error: R is false)_

**Working**

1. A: payments/small finance banks may engage BCs — true.
2. R: RBI permitted for-profit companies as BCs (2010) and later non-deposit-taking NBFCs (2014) — false.

**Formula:** —  
**Trap:** Corporate BCs are allowed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-080 · L1 · easy · Certificates of deposit — denomination and maturity ⚠

As per RBI directions, certificates of deposit (CDs) issued by scheduled commercial banks have a minimum denomination and maturity of:

- **A.** ₹5 lakh and multiples; maturity 1 year to 3 years  _(error: maturity band for CDs issued by AIFIs, not banks)_
- **B.** ₹1 lakh and multiples; maturity 7 days to one year  _(error: old/incorrect denomination)_
- **C.** ₹25 lakh and multiples; maturity 15 days to one year  _(error: neither denomination nor minimum tenor is correct)_
- **D.** ₹5 lakh and multiples; maturity 7 days to one year ✅

**Working**

1. Banks: 7 days to 1 year; AIFIs: 1 to 3 years.
2. Minimum ₹5 lakh and multiples of ₹5 lakh; issued in demat form.

**Formula:** —  
**Trap:** Tenor bands differ for banks and AIFIs.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-081 · L2 · medium · Certificates of deposit — denomination and maturity

A bank issues a 182-day CD of face value ₹5 crore at a yield of 7.25% (Actual/365, money-market yield). The issue price is:

- **A.** ₹4,82,50,905  _(error: T-bill 364-day convention used)_
- **B.** ₹4,82,32,157  _(error: 360-day year used)_
- **C.** ₹4,82,55,530 ✅
- **D.** ₹4,81,92,466  _(error: discount-rate (bank discount) method applied to face)_

**Working**

1. Price = 5,00,00,000 ÷ (1 + 0.0725 × 182/365) = ₹4,82,55,530

**Formula:** P = F ÷ (1 + y × d/365)  
**Trap:** CD yields are quoted on price, not face.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-082 · L3 · hard · Certificates of deposit — denomination and maturity

A mutual fund buys a fresh 364-day CD (face ₹1 crore) at a yield of 7.60% and sells it after 91 days when the yield for the remaining tenor is 7.15%. Both yields are Actual/365 money-market yields. The fund's annualised holding-period return is closest to:

- **A.** 7.60%  _(error: purchase yield taken as realised return)_
- **B.** 8.05%  _(error: yield change added one-for-one to purchase yield (duration ignored))_
- **C.** 8.50% ✅
- **D.** 1.68%  _(error: sale price computed on the full original tenor)_

**Working**

1. Buy price = ₹92,95,479
2. Sale price (273 days left) = ₹94,92,366
3. HPR = (94,92,366 ÷ 92,95,479 − 1) × 365/91 = 8.50%

**Formula:** HPR(ann.) = (P₁/P₀ − 1) × 365/d  
**Trap:** A fall in yields gives a capital gain on top of accrual.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-083 · L1 · easy · Commercial paper — eligibility and net worth ⚠

Consider the following statements regarding commercial paper (CP) under RBI's 2024 directions on CPs and short-term NCDs:

1. Eligible issuers include companies, NBFCs and LLPs having a net worth of ₹100 crore or more.
2. CP may be issued with a tenor from 7 days up to one year, in minimum denominations of ₹5 lakh and multiples thereof.
3. CPs may be underwritten or co-accepted by banks to enhance marketability.

Which of the statements given above is/are correct?

- **A.** 1 and 2 only ✅
- **B.** 2 and 3 only  _(error: statement 3 is prohibited; statement 1 is correct)_
- **C.** 2 only  _(error: statement 1 correctly states the net-worth criterion)_
- **D.** 1, 2 and 3  _(error: underwriting/co-acceptance of CPs is prohibited)_

**Working**

1. Net worth ≥ ₹100 crore (plus minimum credit rating) — correct.
2. Tenor 7 days–1 year; ₹5 lakh denomination — correct.
3. Issuance cannot be underwritten or co-accepted — incorrect.

**Formula:** —  
**Trap:** The old ₹4 crore tangible-net-worth test is no longer the criterion.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-084 · L2 · medium · Commercial paper — eligibility and net worth

A company issues 91-day CP of face value ₹50 crore at a price of ₹98.30 per ₹100. Rating, IPA and stamp-duty costs total ₹6.00 lakh, paid upfront. The effective annualised cost of funds (Actual/365) is closest to:

- **A.** 7.33%  _(error: 360-day year used)_
- **B.** 7.44% ✅
- **C.** 7.30%  _(error: discount computed on face value (discount rate) instead of net proceeds)_
- **D.** 6.94%  _(error: issue costs ignored)_

**Working**

1. Net proceeds = ₹50 crore × 98.30% − ₹6.00 lakh = ₹49,09,00,000
2. Cost = (50,00,00,000 − 49,09,00,000) ÷ 49,09,00,000 × 365/91 = 7.44%

**Formula:** Effective cost = (Face − Net proceeds)/Net proceeds × 365/d  
**Trap:** Base the cost on the money actually received.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-085 · L2 · medium · Commercial paper — eligibility and net worth

A 120-day CP is purchased at ₹97.95 per ₹100 of face value. The money-market yield to the investor (Actual/365) is:

- **A.** 6.35%  _(error: T-bill 364-day basis used)_
- **B.** 6.24%  _(error: discount on face (discount rate) instead of yield on price)_
- **C.** 6.37% ✅
- **D.** 2.09%  _(error: not annualised)_

**Working**

1. Yield = (2.05 ÷ 97.95) × 365/120 = 6.37%

**Formula:** y = (F − P)/P × 365/d  
**Trap:** Annualise on 365 days for CP.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-086 · L1 · easy · Call, notice and term money ⚠

In the Indian money market, funds lent for a period of 2 to 14 days are classified as:

- **A.** Term money  _(error: term money is 15 days to one year)_
- **B.** Call money  _(error: call money is overnight (one day, or over holidays))_
- **C.** Notice money ✅
- **D.** Tri-party repo  _(error: TREPS is a collateralised segment defined by instrument, not tenor)_

**Working**

1. Call: overnight; notice: 2–14 days; term: 15 days–1 year (uncollateralised interbank).

**Formula:** —  
**Trap:** Tenor, not collateral, separates call/notice/term.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-087 · L2 · medium · Call, notice and term money

Bank A lends ₹75 crore to Bank B in the notice money market for 14 days at 6.45%. Interest receivable at maturity (Actual/365) is:

- **A.** ₹18,81,250  _(error: 360-day year used)_
- **B.** ₹1,32,534  _(error: interest for one day (call convention) only)_
- **C.** ₹19,88,014  _(error: maturity counted inclusively as 15 days)_
- **D.** ₹18,55,479 ✅

**Working**

1. Interest = 75,00,00,000 × 6.45% × 14/365 = ₹18,55,479

**Formula:** I = P × r × d/365  
**Trap:** Money-market interest in India is on Actual/365.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-088 · L3 · hard · Call, notice and term money ⚠

A scheduled commercial bank's capital funds (Tier 1 + Tier 2) at the end of the previous financial year were ₹4,000 crore. Under RBI's current directions, each bank sets its own Board-approved limits for call/notice money operations (borrowing within RBI's prudential inter-bank liability limits). This bank's Board-approved limits are: borrowing 100% of capital funds on a fortnightly average and 125% on any day; lending 25% on a fortnightly average and 50% on any day. The maximum the bank may LEND on any single day is:

- **A.** ₹2,000 crore ✅
- **B.** ₹4,000 crore  _(error: average borrowing limit applied to lending)_
- **C.** ₹1,000 crore  _(error: fortnightly-average lending limit applied to a single day)_
- **D.** ₹5,000 crore  _(error: daily borrowing limit applied to lending)_

**Working**

1. Since the 2021 Directions (as amended 8 June 2023), RBI no longer prescribes percentage caps; banks fix Board-approved limits (borrowing within inter-bank liability limits).
2. Board-approved lending limits here: average 25%, any single day 50% of capital funds.
3. 50% × ₹4,000 crore = ₹2,000 crore

**Formula:** Max single-day lending = Board-approved peak lending % × capital funds  
**Trap:** Distinguish average and single-day limits; the percentages are now the bank's own Board-approved limits, not RBI caps.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-089 · L1 · easy · Cheque Truncation System

In the Cheque Truncation System (CTS), clearing of a cheque is effected by:

- **A.** Conversion of the cheque into a UPI collect request that NPCI debits in real time from the drawer's account at the drawee bank  _(error: CTS is an image-based clearing system, not UPI)_
- **B.** Electronic transmission of the cheque image and MICR data via the clearing house, while the presenting bank retains the physical instrument ✅
- **C.** Physical movement of the cheque to the drawee branch for signature verification, followed by electronic net settlement of funds  _(error: physical movement is what truncation eliminates)_
- **D.** Real-time gross settlement of each cheque individually through RTGS once the drawee bank has verified the physical instrument  _(error: CTS settles on a net basis in clearing sessions)_

**Working**

1. Truncation stops the flow of the physical cheque at the presenting bank.
2. Images + MICR data are sent via the clearing house (NPCI grid).
3. Physical instrument is retained for the prescribed period.

**Formula:** —  
**Trap:** Image-based clearing ≠ RTGS.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-090 · L2 · medium · Cheque Truncation System ⚠

Consider the following statements:

1. Under the Positive Pay System, banks enable the facility for all account holders issuing cheques of ₹50,000 and above, and may make it mandatory for cheques of ₹5 lakh and above.
2. Cheques in India are valid for a period of three months from the date of the instrument.
3. CTS instruments must conform to the CTS-2010 standard.

Which of the statements given above is/are correct?

- **A.** 1 and 2 only  _(error: CTS-2010 standard compliance is required for cheques cleared in CTS)_
- **B.** 1, 2 and 3 ✅
- **C.** 2 and 3 only  _(error: statement 1 correctly reflects the PPS thresholds)_
- **D.** 1 and 3 only  _(error: validity was reduced to three months by RBI (2012))_

**Working**

1. PPS (from 1 January 2021): enabled for ≥ ₹50,000; banks may mandate for ≥ ₹5 lakh.
2. Validity three months (RBI, April 2012).
3. CTS-2010 standard with security features.

**Formula:** —  
**Trap:** All three are current RBI rules.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-091 · L1 · easy · Development financial institutions — NABARD, SIDBI, NHB, NaBFID, EXIM

Match the institution (List I) with its primary mandate (List II):

| List I | List II |
|---|---|
| P. NABARD | 1. Long-term infrastructure financing and development of bond/derivative markets for infrastructure |
| Q. SIDBI | 2. Agriculture and rural development, incl. refinance and RIDF |
| R. NHB | 3. Promotion and financing of MSMEs |
| S. NaBFID | 4. Housing finance — refinance and supervision of housing finance companies |

Codes:

- **A.** P-2, Q-4, R-3, S-1  _(error: SIDBI and NHB mandates swapped)_
- **B.** P-2, Q-3, R-4, S-1 ✅
- **C.** P-1, Q-3, R-4, S-2  _(error: NABARD and NaBFID mandates swapped)_
- **D.** P-3, Q-2, R-4, S-1  _(error: NABARD and SIDBI mandates swapped)_

**Working**

1. NABARD (1982): agriculture/rural; RIDF.
2. SIDBI (1990): MSMEs.
3. NHB (1988): housing finance.
4. NaBFID (2021): infrastructure.

**Formula:** —  
**Trap:** NaBFID is the newest AIFI.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-092 · L2 · medium · Development financial institutions — NABARD, SIDBI, NHB, NaBFID, EXIM ⚠

Consider the following statements:

1. NABARD, SIDBI, NHB, EXIM Bank and NaBFID are regulated and supervised by the RBI as All India Financial Institutions.
2. NaBFID was established under a dedicated Act of Parliament passed in 2021.
3. NHB continues to be the regulator of housing finance companies.

Which of the statements given above is/are correct?

- **A.** 2 only  _(error: statement 1 is correct — five AIFIs are under RBI)_
- **B.** 1, 2 and 3  _(error: regulation of HFCs moved from NHB to RBI in August 2019 (NHB retains supervision/grievance functions))_
- **C.** 1 and 2 only ✅
- **D.** 1 and 3 only  _(error: statement 3 is incorrect)_

**Working**

1. The five AIFIs are regulated by RBI — correct.
2. National Bank for Financing Infrastructure and Development Act, 2021 — correct.
3. Regulatory powers over HFCs were transferred to RBI (Finance (No.2) Act, 2019) — incorrect.

**Formula:** —  
**Trap:** Regulation and supervision of HFCs are split after 2019.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-093 · L1 · easy · Development financial institutions — NABARD, SIDBI, NHB, NaBFID, EXIM

**Assertion (A):** Rural Infrastructure Development Fund (RIDF) resources are routed through NABARD to State Governments for rural infrastructure projects.

**Reason (R):** Commercial banks deposit amounts equal to their shortfall in priority-sector lending targets into funds such as RIDF maintained with NABARD.

Choose the correct option:

- **A.** Both A and R are true, and R correctly explains A ✅
- **B.** Only R is true; A is a false statement of fact  _(error: RIDF loans are extended by NABARD to State Governments)_
- **C.** Only A is true; R is a false statement of fact  _(error: R correctly describes PSL-shortfall allocation)_
- **D.** Both A and R are true, but R does not explain A  _(error: PSL shortfall deposits are the source of RIDF corpus)_

**Working**

1. RIDF (1995–96) is funded by PSL-shortfall deposits of banks.
2. NABARD lends these to States/State entities for rural infrastructure.

**Formula:** —  
**Trap:** PSL shortfall → RIDF → State Governments.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-094 · L1 · easy · Export credit and trade finance

Which of the following is a POST-shipment export finance facility?

- **A.** Advance against incentives receivable, granted before goods are manufactured  _(error: timing is pre-shipment)_
- **B.** Packing credit to purchase raw materials for an export order  _(error: pre-shipment finance)_
- **C.** Negotiation/discounting of export bills drawn under a letter of credit ✅
- **D.** Running account packing credit  _(error: pre-shipment finance)_

**Working**

1. Pre-shipment: packing credit (incl. running account), finance to procure/process goods.
2. Post-shipment: purchase/discount/negotiation of export bills, advances against bills sent on collection.

**Formula:** —  
**Trap:** The shipment date splits pre- and post-shipment finance.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-095 · L2 · medium · Export credit and trade finance

An exporter forfaits a USD 5,00,000 avalised bill due in 180 days. The forfaiter charges a discount of 6.5% p.a. (Actual/360, straight discount on face) and a commitment/handling fee of 0.5% of face. At a spot rate of ₹84.60, the exporter's INR proceeds are:

- **A.** ₹4,07,13,750 ✅
- **B.** ₹4,09,25,250  _(error: fee ignored)_
- **C.** ₹3,93,39,000  _(error: full annual discount charged for a 180-day bill)_
- **D.** ₹4,07,32,582  _(error: Actual/365 used instead of the USD 360-day convention)_

**Working**

1. Discount = 500,000 × 6.5% × 180/360 = USD 16,250
2. Fee = USD 2,500
3. Net = USD 481,250 × 84.6 = ₹4,07,13,750

**Formula:** Proceeds = [Face − Face×d×t/360 − Fee] × Spot  
**Trap:** USD money-market discounting uses a 360-day year.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-096 · L3 · hard · Export credit and trade finance

An exporter with annual credit sales of ₹24 crore and a 90-day collection period (360-day year) considers without-recourse export factoring: the factor advances 80% of receivables at 12% p.a. and charges a service fee of 1% of sales. Factoring would save sales-ledger costs of ₹18.00 lakh p.a. and eliminate bad debts of 0.5% of sales. The NET annual cost of factoring is closest to:

- **A.** ₹51.60 lakh ✅
- **B.** ₹81.60 lakh  _(error: savings in admin cost and bad debts ignored)_
- **C.** ₹66.00 lakh  _(error: interest charged on 100% of receivables instead of the advance)_
- **D.** ₹33.60 lakh  _(error: service fee applied to receivables instead of annual sales)_

**Working**

1. Average receivables = ₹24 crore × 90/360 = ₹6.00 crore
2. Interest = ₹6.00 crore × 80% × 12% = ₹57.60 lakh; fee = 1% × ₹24 crore = ₹24.00 lakh
3. Savings = ₹18.00 lakh + ₹12.00 lakh = ₹30.00 lakh
4. Net cost = ₹81.60 lakh − ₹30.00 lakh = ₹51.60 lakh

**Formula:** Net cost = Interest on advance + Fee − (Admin + Bad-debt savings)  
**Trap:** Compare total factoring cost with costs avoided.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-097 · L1 · easy · FBIL benchmark rates ⚠

Consider the following statements about Financial Benchmarks India Pvt. Ltd. (FBIL):

1. FBIL is jointly owned by FIMMDA, FEDAI and the Indian Banks' Association.
2. FBIL publishes the overnight MIBOR and the USD/INR reference rate.
3. FBIL is the statutory regulator of all interest-rate benchmarks in India under the RBI Act.

Which of the statements given above is/are correct?

- **A.** 1, 2 and 3  _(error: FBIL is an administrator; RBI regulates benchmark administrators)_
- **B.** 1 and 2 only ✅
- **C.** 2 only  _(error: statement 1 correctly states FBIL's ownership)_
- **D.** 2 and 3 only  _(error: statement 3 is incorrect)_

**Working**

1. FBIL (2014) is owned by FIMMDA, FEDAI and IBA.
2. It administers MIBOR, USD/INR reference rate, T-bill/CD curves, G-sec valuations, MMIFOR etc.
3. RBI regulates administrators under its Financial Benchmark Administrators Directions; FBIL is not a regulator.

**Formula:** —  
**Trap:** Administrator ≠ regulator.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-098 · L2 · medium · FBIL benchmark rates ⚠

**Assertion (A):** After the cessation of USD LIBOR, the Mumbai Interbank Forward Outright Rate (MIFOR) benchmark was replaced by a modified MIFOR that uses SOFR as the USD reference rate.

**Reason (R):** MIFOR is derived from USD/INR forward premia and a USD interest rate, so it needed a new USD reference rate once LIBOR ceased.

Choose the correct option:

- **A.** Both A and R are true, but R does not explain A  _(error: R is exactly why MIFOR had to be modified)_
- **B.** Both A and R are true, and R correctly explains A ✅
- **C.** Only R is true; A is a false statement of fact  _(error: FBIL did introduce MMIFOR based on SOFR)_
- **D.** Only A is true; R is a false statement of fact  _(error: R correctly describes MIFOR construction)_

**Working**

1. MIFOR = implied INR rate from USD/INR forward premium + USD rate.
2. LIBOR cessation (June 2023) ⇒ FBIL's Modified MIFOR (MMIFOR) uses SOFR.

**Formula:** —  
**Trap:** Benchmark transition follows the underlying input.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-099 · L4 · hard · Basel norms and capital adequacy ⚠

**Case — Tapti Commercial Bank Ltd (fictional)** — identified by RBI as a D-SIB in bucket 2 (CET1 surcharge 0.40% of RWA). Figures as at 31 March (₹ crore):

| Item | ₹ crore |
|---|---:|
| CET1 capital (after regulatory adjustments) | 9,800 |
| Additional Tier 1 instruments | 1,400 |
| Tier 2 instruments (eligible) | 1,600 |
| General/floating provisions | 1,500 |
| Credit RWA | 96,000 |
| Market RWA | 8,000 |
| Operational RWA | 12,000 |
| Leverage exposure measure | 2,70,000 |
| Gross advances | 1,10,000 |
| Gross NPAs | 4,600 |
| Specific provisions held on NPAs | 3,100 |

Assume RBI minima: CET1 5.5%, CCB 2.5%, Tier 1 7%, total capital 9%; general provisions eligible in Tier 2 up to 1.25% of credit RWA; leverage ratio 4% for D-SIBs; CCyB nil.

The bank's CRAR is closest to:

- **A.** 11.03%  _(error: general provisions excluded altogether)_
- **B.** 12.07% ✅
- **C.** 14.58%  _(error: only credit RWA in the denominator)_
- **D.** 12.33%  _(error: general provisions included without the 1.25% cap)_

**Working**

1. Eligible GP = min(1,500, 1.25% × 96,000 = 1,200) = 1,200
2. Total capital = 14,000; RWA = 1,16,000
3. CRAR = 12.07%

**Formula:** CRAR = Total capital ÷ Total RWA  
**Trap:** Cap GP at 1.25% of credit RWA.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-100 · L4 · hard · Basel norms and capital adequacy ⚠

**Case — Tapti Commercial Bank Ltd (fictional)** — identified by RBI as a D-SIB in bucket 2 (CET1 surcharge 0.40% of RWA). Figures as at 31 March (₹ crore):

| Item | ₹ crore |
|---|---:|
| CET1 capital (after regulatory adjustments) | 9,800 |
| Additional Tier 1 instruments | 1,400 |
| Tier 2 instruments (eligible) | 1,600 |
| General/floating provisions | 1,500 |
| Credit RWA | 96,000 |
| Market RWA | 8,000 |
| Operational RWA | 12,000 |
| Leverage exposure measure | 2,70,000 |
| Gross advances | 1,10,000 |
| Gross NPAs | 4,600 |
| Specific provisions held on NPAs | 3,100 |

Assume RBI minima: CET1 5.5%, CCB 2.5%, Tier 1 7%, total capital 9%; general provisions eligible in Tier 2 up to 1.25% of credit RWA; leverage ratio 4% for D-SIBs; CCyB nil.

The bank's CET1 surplus over its total CET1 requirement (minimum + CCB + D-SIB surcharge) is closest to:

- **A.** ₹1,736 crore  _(error: requirement applied on credit RWA only)_
- **B.** ₹56 crore ✅
- **C.** ₹520 crore  _(error: D-SIB surcharge omitted)_
- **D.** ₹3,420 crore  _(error: only the 5.5% minimum considered (buffers ignored))_

**Working**

1. Requirement = (5.5 + 2.5 + 0.40)% = 8.40% of 1,16,000 = 9,744
2. Surplus = 9,800 − 9,744 = 56

**Formula:** CET1 requirement = (Min + CCB + D-SIB) × RWA  
**Trap:** The surcharge sits on top of CCB.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-101 · L4 · hard · Capital and leverage norms; D-SIBs ⚠

**Case — Tapti Commercial Bank Ltd (fictional)** — identified by RBI as a D-SIB in bucket 2 (CET1 surcharge 0.40% of RWA). Figures as at 31 March (₹ crore):

| Item | ₹ crore |
|---|---:|
| CET1 capital (after regulatory adjustments) | 9,800 |
| Additional Tier 1 instruments | 1,400 |
| Tier 2 instruments (eligible) | 1,600 |
| General/floating provisions | 1,500 |
| Credit RWA | 96,000 |
| Market RWA | 8,000 |
| Operational RWA | 12,000 |
| Leverage exposure measure | 2,70,000 |
| Gross advances | 1,10,000 |
| Gross NPAs | 4,600 |
| Specific provisions held on NPAs | 3,100 |

Assume RBI minima: CET1 5.5%, CCB 2.5%, Tier 1 7%, total capital 9%; general provisions eligible in Tier 2 up to 1.25% of credit RWA; leverage ratio 4% for D-SIBs; CCyB nil.

With respect to the leverage ratio, the bank:

- **A.** Meets the requirement: leverage ratio 5.19% against 3.5%  _(error: total capital used, and non-D-SIB floor applied)_
- **B.** Meets the requirement: leverage ratio 4.15% against 4% ✅
- **C.** Falls short: leverage ratio 3.63% against 4%  _(error: CET1 used instead of Tier 1 capital)_
- **D.** Meets the requirement: leverage ratio 9.66% against 4%  _(error: RWA used instead of exposure measure)_

**Working**

1. Tier 1 = 11,200; exposure = 2,70,000
2. Leverage ratio = 4.15% ≥ 4% (D-SIB floor)

**Formula:** Leverage ratio = Tier 1 ÷ Exposure measure  
**Trap:** Numerator is Tier 1, denominator is unweighted exposure.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-102 · L4 · hard · Asset classification, NPA and divergence disclosure

**Case — Tapti Commercial Bank Ltd (fictional)** — identified by RBI as a D-SIB in bucket 2 (CET1 surcharge 0.40% of RWA). Figures as at 31 March (₹ crore):

| Item | ₹ crore |
|---|---:|
| CET1 capital (after regulatory adjustments) | 9,800 |
| Additional Tier 1 instruments | 1,400 |
| Tier 2 instruments (eligible) | 1,600 |
| General/floating provisions | 1,500 |
| Credit RWA | 96,000 |
| Market RWA | 8,000 |
| Operational RWA | 12,000 |
| Leverage exposure measure | 2,70,000 |
| Gross advances | 1,10,000 |
| Gross NPAs | 4,600 |
| Specific provisions held on NPAs | 3,100 |

Assume RBI minima: CET1 5.5%, CCB 2.5%, Tier 1 7%, total capital 9%; general provisions eligible in Tier 2 up to 1.25% of credit RWA; leverage ratio 4% for D-SIBs; CCyB nil.

The bank's net NPA ratio is closest to:

- **A.** 1.40% ✅
- **B.** 4.18%  _(error: gross NPA ratio reported)_
- **C.** 1.36%  _(error: net NPAs divided by gross advances instead of net advances)_
- **D.** 1.42%  _(error: gross NPAs (instead of provisions) deducted from advances in the denominator)_

**Working**

1. Net NPA = 4,600 − 3,100 = 1,500
2. Net advances = 1,10,000 − 3,100 = 1,06,900
3. Net NPA ratio = 1.40%

**Formula:** Net NPA % = (GNPA − Provisions) ÷ (Gross advances − Provisions)  
**Trap:** Deduct provisions from both numerator and denominator.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-103 · L4 · hard · Asset classification, NPA and divergence disclosure

**Case — Tapti Commercial Bank Ltd (fictional)** — identified by RBI as a D-SIB in bucket 2 (CET1 surcharge 0.40% of RWA). Figures as at 31 March (₹ crore):

| Item | ₹ crore |
|---|---:|
| CET1 capital (after regulatory adjustments) | 9,800 |
| Additional Tier 1 instruments | 1,400 |
| Tier 2 instruments (eligible) | 1,600 |
| General/floating provisions | 1,500 |
| Credit RWA | 96,000 |
| Market RWA | 8,000 |
| Operational RWA | 12,000 |
| Leverage exposure measure | 2,70,000 |
| Gross advances | 1,10,000 |
| Gross NPAs | 4,600 |
| Specific provisions held on NPAs | 3,100 |

Assume RBI minima: CET1 5.5%, CCB 2.5%, Tier 1 7%, total capital 9%; general provisions eligible in Tier 2 up to 1.25% of credit RWA; leverage ratio 4% for D-SIBs; CCyB nil.

The board sets an internal target provision coverage ratio (specific provisions ÷ GNPA, excluding technical write-offs) of 75%. The additional provision required, and its effect on CET1 (ignoring tax), are closest to:

- **A.** ₹350 crore; CET1 ratio falls to 8.15% ✅
- **B.** ₹3,450 crore; CET1 ratio falls to 5.47%  _(error: existing provisions not netted off)_
- **C.** ₹1,125 crore; CET1 ratio falls to 7.48%  _(error: target applied to net NPAs)_
- **D.** ₹350 crore; CET1 ratio unchanged at 8.45%  _(error: provisions charged to P&L do reduce CET1)_

**Working**

1. Present PCR = 3,100 ÷ 4,600 = 67.39%
2. Required provisions = 75% × 4,600 = 3,450; additional = 350
3. CET1 = 9,450 ÷ 1,16,000 = 8.15%

**Formula:** PCR = Provisions ÷ GNPA  
**Trap:** New provisions flow through profit and reduce CET1.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-104 · L4 · hard · Bank advances — cash credit, overdraft, bill discounting

**Case — Vindhya Auto Components Ltd (fictional)** — projected current assets and liabilities for next year (₹ lakh):

| Current assets | ₹ lakh | Current liabilities (other than bank borrowings) | ₹ lakh |
|---|---:|---|---:|
| Raw materials | 180 | Sundry creditors (for goods) | 140 |
| Work-in-progress | 60 | Other current liabilities | 40 |
| Finished goods | 110 |  |  |
| Receivables (of which over 90 days: 30) | 220 |  |  |
| Other current assets | 30 |  |  |
| **Total** | 600 | **Total** | 180 |

Core current assets are estimated at ₹100 lakh. The bank's cash-credit rate is 10.25% p.a.; it lends against stocks at 25% margin (after deducting creditors for goods) and against receivables up to 90 days at 40% margin.

The Maximum Permissible Bank Finance under the second method of lending (Tandon Committee) is:

- **A.** ₹247.50 lakh  _(error: overdue receivables excluded from current assets (a DP adjustment, not MPBF))_
- **B.** ₹270.00 lakh ✅
- **C.** ₹195.00 lakh  _(error: third method: core current assets excluded)_
- **D.** ₹315.00 lakh  _(error: first method: 75% of working-capital gap)_

**Working**

1. Total CA = ₹600.00 lakh; OCL = ₹180.00 lakh
2. Method II: 75% × ₹600.00 lakh − ₹180.00 lakh = ₹270.00 lakh

**Formula:** MPBF (II) = 0.75 × CA − OCL  
**Trap:** Borrower funds 25% of total current assets from long-term sources.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-105 · L4 · hard · Bank advances — cash credit, overdraft, bill discounting

**Case — Vindhya Auto Components Ltd (fictional)** — projected current assets and liabilities for next year (₹ lakh):

| Current assets | ₹ lakh | Current liabilities (other than bank borrowings) | ₹ lakh |
|---|---:|---|---:|
| Raw materials | 180 | Sundry creditors (for goods) | 140 |
| Work-in-progress | 60 | Other current liabilities | 40 |
| Finished goods | 110 |  |  |
| Receivables (of which over 90 days: 30) | 220 |  |  |
| Other current assets | 30 |  |  |
| **Total** | 600 | **Total** | 180 |

Core current assets are estimated at ₹100 lakh. The bank's cash-credit rate is 10.25% p.a.; it lends against stocks at 25% margin (after deducting creditors for goods) and against receivables up to 90 days at 40% margin.

On these figures, the drawing power available under the cash-credit limit (before comparing with the sanctioned limit) is:

- **A.** ₹300.00 lakh  _(error: 25% stock margin applied to receivables too)_
- **B.** ₹289.50 lakh  _(error: receivables over 90 days included)_
- **C.** ₹271.50 lakh ✅
- **D.** ₹376.50 lakh  _(error: creditors for goods not deducted from stock)_

**Working**

1. Stock = ₹350.00 lakh; less creditors ₹140.00 lakh = ₹210.00 lakh; × 75% = ₹157.50 lakh
2. Eligible receivables = ₹190.00 lakh × 60% = ₹114.00 lakh
3. DP = ₹271.50 lakh

**Formula:** DP = (Stock − Creditors)(1 − m₁) + Eligible debtors(1 − m₂)  
**Trap:** Unpaid stock is financed by creditors, not the bank.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-106 · L4 · hard · Commercial paper — eligibility and net worth

**Case — Vindhya Auto Components Ltd (fictional)** — projected current assets and liabilities for next year (₹ lakh):

| Current assets | ₹ lakh | Current liabilities (other than bank borrowings) | ₹ lakh |
|---|---:|---|---:|
| Raw materials | 180 | Sundry creditors (for goods) | 140 |
| Work-in-progress | 60 | Other current liabilities | 40 |
| Finished goods | 110 |  |  |
| Receivables (of which over 90 days: 30) | 220 |  |  |
| Other current assets | 30 |  |  |
| **Total** | 600 | **Total** | 180 |

Core current assets are estimated at ₹100 lakh. The bank's cash-credit rate is 10.25% p.a.; it lends against stocks at 25% margin (after deducting creditors for goods) and against receivables up to 90 days at 40% margin.

The company (net worth and rating eligible) plans to replace part of its cash credit with a 91-day CP of face ₹10 crore issued at ₹98.25, with issue expenses of ₹1.50 lakh. Compared with cash credit on the same net amount for 91 days, the CP route:

- **A.** Saves about ₹6.07 lakh; effective CP cost 7.77% ✅
- **B.** Saves about ₹24.82 lakh; effective CP cost 7.77%  _(error: saving computed for a full year on face value)_
- **C.** Saves about ₹7.60 lakh; effective CP cost 7.14%  _(error: issue expenses ignored)_
- **D.** Costs about ₹6.07 lakh more; effective CP cost 7.77%  _(error: comparison direction reversed)_

**Working**

1. Net proceeds = ₹9,81,00,000
2. Effective cost = 7.77%
3. Saving = ₹9,81,00,000 × (10.25% − 7.77%) × 91/365 = ₹6.07 lakh

**Formula:** Saving = Net funds × (r_CC − r_CP) × d/365  
**Trap:** Compare on the same amount and period.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-107 · L4 · hard · Export credit and trade finance

**Case — Vindhya Auto Components Ltd (fictional)** — projected current assets and liabilities for next year (₹ lakh):

| Current assets | ₹ lakh | Current liabilities (other than bank borrowings) | ₹ lakh |
|---|---:|---|---:|
| Raw materials | 180 | Sundry creditors (for goods) | 140 |
| Work-in-progress | 60 | Other current liabilities | 40 |
| Finished goods | 110 |  |  |
| Receivables (of which over 90 days: 30) | 220 |  |  |
| Other current assets | 30 |  |  |
| **Total** | 600 | **Total** | 180 |

Core current assets are estimated at ₹100 lakh. The bank's cash-credit rate is 10.25% p.a.; it lends against stocks at 25% margin (after deducting creditors for goods) and against receivables up to 90 days at 40% margin.

Vindhya also receives a confirmed export order (FOB ₹4 crore). The bank sanctions packing credit with a 10% margin at 8.5% p.a.; the advance is liquidated by export proceeds after 75 days. Interest on the packing credit is:

- **A.** ₹6,28,767 ✅
- **B.** ₹6,37,500  _(error: 360-day year used)_
- **C.** ₹69,863  _(error: interest computed on the margin instead of the advance)_
- **D.** ₹6,98,630  _(error: margin ignored — interest on full FOB value)_

**Working**

1. Packing credit = ₹4 crore × 90% = ₹3.60 crore
2. Interest = 3,60,00,000 × 8.5% × 75/365 = ₹6,28,767

**Formula:** Interest = FOB × (1 − margin) × r × d/365  
**Trap:** The margin is the exporter's own stake.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-108 · L1 · easy · AIF categories and Angel Funds ⚠

Under the SEBI (Alternative Investment Funds) Regulations, 2012, an Angel Fund is a sub-category of:

- **A.** Category II AIF — Private Equity Fund  _(error: Cat II covers PE/debt funds without specific incentives)_
- **B.** Category I AIF — Venture Capital Fund ✅
- **C.** Category III AIF — Hedge Fund  _(error: Cat III funds use complex/leveraged strategies)_
- **D.** A separate category outside the AIF Regulations, registered as a venture capital undertaking  _(error: angel funds are registered under the AIF Regulations)_

**Working**

1. Category I includes venture capital funds (incl. angel funds), SME funds, social venture funds and infrastructure funds.
2. Angel funds are a sub-category of VCF within Category I.

**Formula:** —  
**Trap:** Cat I = sectors the Government considers socially/economically desirable.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-109 · L3 · hard · AIF categories and Angel Funds ⚠

Consider the following statements regarding AIFs:

1. Category I and II AIFs may not borrow except to meet temporary funding requirements, within limits specified by SEBI.
2. Category III AIFs may employ leverage, subject to SEBI's exposure limits.
3. The minimum investment by an investor in an AIF (other than accredited investors and employees/directors of the manager) is ₹1 crore.
4. Category III AIFs must be close-ended with a minimum tenure of three years.

Which of the statements given above are correct?

- **A.** 1, 2 and 3 only ✅
- **B.** 1, 2, 3 and 4  _(error: Cat III AIFs may be open-ended; the 3-year close-ended rule is for Cat I and II)_
- **C.** 1 and 2 only  _(error: statement 3 correctly states the ₹1 crore minimum)_
- **D.** 2, 3 and 4 only  _(error: statement 4 is wrong; statement 1 is correct)_

**Working**

1. Cat I/II: no leverage except temporary funding (short-term borrowing within limits) — correct.
2. Cat III: leverage permitted within limits — correct.
3. Minimum ticket ₹1 crore (₹25 lakh for employees/directors; exemption for accredited investors in LVFs) — correct.
4. Cat III may be open- or close-ended — statement 4 wrong.

**Formula:** —  
**Trap:** Tenure rule (≥3 years close-ended) applies to Cat I and II.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-110 · L2 · medium · Account Aggregator framework ⚠

**Assertion (A):** An Account Aggregator cannot read, store or use for its own purposes the financial information it transmits.

**Reason (R):** Under RBI's NBFC-AA directions, the Account Aggregator acts only as a consent-based conduit between Financial Information Providers and Financial Information Users, with data flowing encrypted.

Choose the correct option:

- **A.** Both A and R are true, and R correctly explains A ✅
- **B.** Both A and R are true, but R does not explain A  _(error: R is the design basis for the 'data-blind' feature in A)_
- **C.** Only R is true; A is a false statement of fact  _(error: AAs are prohibited from storing or using customer data)_
- **D.** Only A is true; R is a false statement of fact  _(error: R correctly describes the AA's role)_

**Working**

1. AA = consent manager; data is end-to-end encrypted; AA is 'data blind'.
2. It may not undertake any other business or use the data.

**Formula:** —  
**Trap:** The AA moves data; it does not hold or analyse it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-111 · L3 · hard · Account Aggregator framework ⚠

Consider the following statements about the Account Aggregator (AA) ecosystem:

1. An AA must be a company registered with the RBI as an NBFC-AA.
2. Entities regulated by SEBI, IRDAI and PFRDA can participate as Financial Information Providers or Users.
3. A customer's consent artefact specifies the purpose, the data sought, the duration and the frequency of access, and can be revoked.
4. An AA may offer credit to customers on the basis of the data it aggregates.

Which of the statements given above are correct?

- **A.** 1, 2, 3 and 4  _(error: an AA cannot use the data or undertake lending)_
- **B.** 2, 3 and 4 only  _(error: statement 1 is correct; statement 4 is wrong)_
- **C.** 1, 2 and 3 only ✅
- **D.** 1 and 3 only  _(error: financial-sector regulators other than RBI have notified their entities as FIPs/FIUs)_

**Working**

1. NBFC-AA registration with RBI — correct.
2. SEBI, IRDAI, PFRDA entities participate — correct.
3. Consent artefact elements and revocability — correct.
4. AA cannot lend or use data — statement 4 wrong.

**Formula:** —  
**Trap:** AA = conduit; FIU = lender/user.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-112 · L2 · medium · Alternate sources of finance

Match the financing source (List I) with its key feature (List II):

| List I | List II |
|---|---|
| P. Venture debt | 1. Asset sold to a financier and taken back on lease, releasing locked-up capital |
| Q. Sale and leaseback | 2. Receivables pooled and sold to an SPV that issues pass-through certificates |
| R. Securitisation | 3. Term loan to a VC-backed startup, often with warrants, complementing equity |
| S. Invoice discounting on TReDS | 4. MSME receivables from large buyers auctioned to financiers on an electronic platform |

Codes:

- **A.** P-3, Q-1, R-4, S-2  _(error: securitisation and TReDS swapped)_
- **B.** P-1, Q-3, R-2, S-4  _(error: venture debt and sale-leaseback swapped)_
- **C.** P-3, Q-2, R-1, S-4  _(error: sale-leaseback and securitisation swapped)_
- **D.** P-3, Q-1, R-2, S-4 ✅

**Working**

1. Venture debt: debt for equity-backed startups with warrants.
2. Sale & leaseback: sell asset, lease back.
3. Securitisation: SPV issues PTCs against pooled receivables.
4. TReDS: MSME invoice discounting platform (RBI-authorised).

**Formula:** —  
**Trap:** TReDS is buyer-accepted receivables finance for MSMEs.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-113 · L3 · hard · Alternate sources of finance

A supplier offers credit terms of '2/10, net 45'. A buyer that forgoes the cash discount and pays on day 45 is effectively using trade credit as a source of finance. Its approximate annualised cost (365-day year, simple) is:

- **A.** 20.86%  _(error: discount divided by invoice value instead of the net amount (1 − d))_
- **B.** 21.28% ✅
- **C.** 23.45%  _(error: compound (effective) rate reported instead of the simple approximation asked)_
- **D.** 16.55%  _(error: full credit period (45 days) used instead of the extra 35 days)_

**Working**

1. Cost per period = 2 ÷ 98 = 2.0408%
2. Extra days of credit = 45 − 10 = 35
3. Annualised = 2.0408% × 365/35 = 21.28%

**Formula:** Cost = d/(1 − d) × 365/(N − D)  
**Trap:** Trade credit that looks 'free' is usually expensive once the discount is forgone.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-114 · L2 · medium · Anchor investors and lock-in ⚠

In a main-board book-built IPO, shares allotted to anchor investors are subject to which lock-in?

- **A.** 100% of the anchor shares for 30 days, from the date of allotment  _(error: pre-2022 anchor lock-in)_
- **B.** 100% of the anchor shares for 90 days, from the date of listing  _(error: lock-in runs from allotment and is staggered)_
- **C.** 50% of shares for 30 days and 50% for 90 days, from the date of allotment ✅
- **D.** 50% of shares for 90 days and 50% for 180 days, from the date of allotment  _(error: periods overstated; 6-month lock-in applies to pre-issue non-promoter shareholders)_

**Working**

1. SEBI amended ICDR (effective April 2022) to add a 90-day lock-in on 50% of anchor shares.
2. The other 50% remains locked for 30 days.

**Formula:** —  
**Trap:** Staggered lock-in: 30 days / 90 days.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-115 · L3 · hard · Anchor investors and lock-in ⚠

Consider the following statements about anchor investors in a main-board IPO:

1. An anchor investor must apply for at least ₹10 crore.
2. Anchor bidding takes place one working day before the issue opens.
3. If the final issue price is lower than the anchor allocation price, the difference is refunded to anchor investors.
4. Anchor investors must be qualified institutional buyers.

Which of the statements given above are correct?

- **A.** 1, 2 and 4 only ✅
- **B.** 2, 3 and 4 only  _(error: statement 1 is correct; statement 3 is wrong)_
- **C.** 1 and 2 only  _(error: anchor investors are QIBs — statement 4 is correct)_
- **D.** 1, 2, 3 and 4  _(error: no refund if the issue price is lower — anchors are allotted at the anchor price)_

**Working**

1. Minimum application ₹10 crore — correct.
2. Anchor bid/allocation one working day before opening — correct.
3. If issue price < anchor price: no refund; if higher: anchors pay the difference — statement 3 wrong.
4. Anchors are QIBs — correct.

**Formula:** —  
**Trap:** The price adjustment works only one way (against the anchor).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-116 · L1 · easy · BOT variants and risk allocation ⚠

Under the Hybrid Annuity Model (HAM) used for national highway projects, which of the following is correct?

- **A.** Authority pays 40% of bid project cost in construction; developer funds the rest, recovered via annuities; traffic risk stays with authority ✅
- **B.** The authority funds 100% of construction in milestone instalments, and the contractor has no financing or traffic-risk role at all  _(error: describes EPC)_
- **C.** The developer bears full traffic risk and collects toll from road users over the whole concession period to recover its investment  _(error: describes BOT-toll)_
- **D.** The developer pays an upfront lump sum to the authority for the right to collect tolls on an already built and operational highway  _(error: describes TOT)_

**Working**

1. HAM (2016): 40% construction support from the authority; 60% arranged by developer (equity + debt).
2. Developer receives semi-annual annuities with interest; toll collected by the authority.

**Formula:** —  
**Trap:** HAM mixes EPC (authority funding) and annuity-BOT features.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-117 · L2 · medium · BOT variants and risk allocation

Match the PPP/contract model (List I) with the party bearing TRAFFIC (demand) risk (List II):

| List I | List II |
|---|---|
| P. BOT (Toll) | 1. Private developer |
| Q. BOT (Annuity) | 2. Public authority |
| R. EPC | 3. Private developer who paid an upfront concession fee |
| S. TOT (Toll-Operate-Transfer) |  |

Codes:

- **A.** P-1, Q-2, R-2, S-3 ✅
- **B.** P-2, Q-2, R-1, S-3  _(error: BOT-toll and EPC risk assignment reversed)_
- **C.** P-1, Q-2, R-1, S-2  _(error: EPC contractor and TOT concessionaire risk reversed)_
- **D.** P-1, Q-1, R-2, S-3  _(error: annuity BOT wrongly assigned traffic risk to developer)_

**Working**

1. BOT-toll: developer collects toll ⇒ bears traffic risk.
2. BOT-annuity and EPC: authority bears traffic risk.
3. TOT: concessionaire pays upfront for toll rights ⇒ bears traffic risk.

**Formula:** —  
**Trap:** Whoever keeps the toll bears traffic risk.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-118 · L3 · hard · BOT variants and risk allocation ⚠

A HAM highway project has a bid project cost of ₹1,200 crore. The authority provides 40% of the cost as construction support. The developer funds its share with debt and equity in the ratio 70:30. The developer's equity requirement is:

- **A.** ₹309 crore  _(error: 30/70 ratio (equity/debt) applied as a share of funding)_
- **B.** ₹360 crore  _(error: debt:equity applied to the full bid project cost)_
- **C.** ₹144 crore  _(error: developer's share taken as 40% instead of 60%)_
- **D.** ₹216 crore ✅

**Working**

1. Developer's share = 60% × ₹1,200 crore = ₹720 crore
2. Equity = 30% × ₹720 crore = ₹216 crore

**Formula:** Equity = BPC × (1 − construction support) × Equity share  
**Trap:** Apply the financing mix only to the developer-funded part.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-119 · L1 · easy · CBDC, stablecoins and crypto policy ⚠

The RBI's pilots of the Central Bank Digital Currency (e₹) began in:

- **A.** April 2021 for both wholesale and retail segments simultaneously  _(error: predates the Finance Act 2022 enabling amendment)_
- **B.** November 2023 for retail (e₹-R) only; wholesale not yet piloted  _(error: wholesale pilot came first, in 2022)_
- **C.** December 2022 for wholesale (e₹-W) and November 2022 for retail (e₹-R)  _(error: sequence reversed)_
- **D.** November 2022 for wholesale (e₹-W) and December 2022 for retail (e₹-R) ✅

**Working**

1. e₹-W pilot: 1 November 2022 (settlement of secondary G-sec trades).
2. e₹-R pilot: 1 December 2022.

**Formula:** —  
**Trap:** Wholesale first, retail a month later.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-120 · L3 · hard · CBDC, stablecoins and crypto policy ⚠

Consider the following statements:

1. The Finance Act, 2022 amended the RBI Act, 1934 to include a digital form of bank notes.
2. Retail e₹ earns interest for holders in the same manner as a savings deposit.
3. The e₹ is a direct liability of the Reserve Bank of India.
4. Virtual digital asset service providers are covered as 'reporting entities' under the Prevention of Money-laundering Act, 2002.

Which of the statements given above are correct?

- **A.** 1, 2, 3 and 4  _(error: the e₹ is non-interest-bearing, like cash)_
- **B.** 2, 3 and 4 only  _(error: statement 2 is wrong; statement 1 is correct)_
- **C.** 1, 3 and 4 only ✅
- **D.** 1 and 3 only  _(error: PMLA coverage of VDA service providers was notified in March 2023)_

**Working**

1. 1: Finance Act 2022 amended RBI Act (s.22 etc.) to cover digital currency — correct.
2. 2: e₹ is non-remunerated to avoid disintermediation — wrong.
3. 3: CBDC is RBI's liability, like physical currency — correct.
4. 4: VDA SPs brought under PMLA (March 2023) — correct.

**Formula:** —  
**Trap:** Interest-bearing CBDC would compete with bank deposits.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-121 · L2 · medium · CPI components and trends

Group indices and weights of an illustrative consumer price index:

| Group | Weight | Index (last year) | Index (this year) |
|---|---:|---:|---:|
| Food and beverages | 40 | 190.0 | 205.2 |
| Housing | 12 | 176.0 | 183.0 |
| Fuel and light | 7 | 182.0 | 185.6 |
| Clothing and footwear | 7 | 188.0 | 194.6 |
| Miscellaneous | 34 | 180.0 | 188.1 |

Headline year-on-year inflation is closest to:

- **A.** 10.39%  _(error: index-point change read as a percentage)_
- **B.** 5.64% ✅
- **C.** 4.39%  _(error: simple average of group inflation rates (weights ignored))_
- **D.** 8%  _(error: food inflation reported as headline)_

**Working**

1. Combined index last year = Σ wI/100 = 184.22
2. This year = 194.61
3. Inflation = 194.61/184.22 − 1 = 5.64%

**Formula:** CPI = Σ wᵢIᵢ / Σ wᵢ; π = CPI₁/CPI₀ − 1  
**Trap:** Weight group indices, then compute the change.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-122 · L3 · hard · CPI components and trends

Using the same illustrative index:

| Group | Weight | Index (last year) | Index (this year) |
|---|---:|---:|---:|
| Food and beverages | 40 | 190.0 | 205.2 |
| Housing | 12 | 176.0 | 183.0 |
| Fuel and light | 7 | 182.0 | 185.6 |
| Clothing and footwear | 7 | 188.0 | 194.6 |
| Miscellaneous | 34 | 180.0 | 188.1 |

The share of headline inflation contributed by 'Food and beverages' is closest to:

- **A.** 40.0%  _(error: weight taken as contribution)_
- **B.** 56.7%  _(error: weight × group inflation ÷ headline inflation (relative index levels ignored))_
- **C.** 36.4%  _(error: share in the unweighted sum of group inflation rates)_
- **D.** 58.5% ✅

**Working**

1. Food: weight × Δindex = 40 × 15.2 / 100 = 6.080 points
2. Headline change = 10.388 points
3. Contribution = 58.5%

**Formula:** Contributionᵢ = wᵢ ΔIᵢ ÷ Σ wⱼ ΔIⱼ  
**Trap:** Food's share of inflation can greatly exceed its weight when food prices surge.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-123 · L3 · hard · CPI components and trends

An index stood at 180.0 (January last year), 183.6 (February last year), 190.8 (January this year) and 191.8 (February this year). Year-on-year inflation in February this year and the main reason for its change from January are:

- **A.** 4.47%; favourable base effect as last February's 2% jump drops out ✅
- **B.** 4.47%; a sharp fall in price levels during February this year  _(error: prices actually rose m-o-m this February)_
- **C.** 0.52%; a sharp slowdown in current month price momentum  _(error: month-on-month change taken as y-o-y inflation)_
- **D.** 6%; unchanged, as prices rose again this February  _(error: January's y-o-y rate reported for February)_

**Working**

1. Jan y-o-y = 190.8/180.0 − 1 = 6%
2. Feb y-o-y = 191.8/183.6 − 1 = 4.47%
3. This February m-o-m = +0.52% (prices rose); last February m-o-m = +2% (high base)

**Formula:** π_yoy(t) ≈ Σ last 12 m-o-m changes  
**Trap:** Inflation can fall even as prices keep rising, if the base month was high.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-124 · L2 · medium · Circuit breakers and trading halts ⚠

Under SEBI's index-based market-wide circuit breaker, if the benchmark index falls by 10% at 12:15 pm, trading in all equity and equity-derivative segments is halted for:

- **A.** 15 minutes  _(error: halt applicable if the 10% trigger is hit between 1:00 pm and 2:30 pm)_
- **B.** 1 hour 45 minutes  _(error: halt for a 15% trigger before 1:00 pm)_
- **C.** The remainder of the day  _(error: applies to a 20% trigger (or 15% after 2:00 pm))_
- **D.** 45 minutes ✅

**Working**

1. 10% trigger: before 1 pm → 45 min; 1–2:30 pm → 15 min; after 2:30 pm → no halt.
2. Trading resumes with a pre-open call auction session.

**Formula:** —  
**Trap:** The halt length depends on the time of the breach.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-125 · L3 · hard · Circuit breakers and trading halts ⚠

The benchmark index closed at 24,380 yesterday. Today it falls to 21,902 at 11:20 am (trading halts, then resumes) and later touches 20,663 at 1:40 pm. With circuit levels computed on the previous close, the consequence of the 1:40 pm fall is:

- **A.** The 15% level (20,723) is breached before 2:00 pm — trading halts for 1 hour 45 minutes  _(error: 1h45m halt applies only to a 15% breach before 1:00 pm)_
- **B.** The 15% level (20,723) is breached after 1:00 pm but before 2:00 pm — trading halts for 45 minutes ✅
- **C.** Only the 10% level (21,942) matters as it was already triggered; trading continues  _(error: each successive level triggers its own halt)_
- **D.** The 20% level (19,504) is breached — trading halts for the rest of the day  _(error: a 20% fall would take the index to the 20% level, not reached)_

**Working**

1. Levels: 10% → 21,942; 15% → 20,723; 20% → 19,504
2. 20,663 is below the 15% level but above the 20% level
3. 15% breach at/after 1:00 pm and before 2:00 pm → 45-minute halt.

**Formula:** Trigger level = Previous close × (1 − x%)  
**Trap:** Match both the depth of fall and the clock time.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-126 · L2 · medium · Clearing corporations and settlement

A clearing member's trades in the cash segment on one day (all for T+1 settlement) are:

| Side | Security | Quantity | Price (₹) |
|---|---:|---:|---:|
| Buy | Stock P | 12,000 | 410.00 |
| Sell | Stock P | 9,000 | 412.50 |
| Sell | Stock Q | 5,000 | 1250.00 |
| Buy | Stock Q | 2,000 | 1248.00 |

After multilateral netting by the clearing corporation, the member's net funds obligation is:

- **A.** Net pay-out (receive) of ₹12,07,500  _(error: netting done only for Stock P, Stock Q ignored)_
- **B.** Gross settlement of ₹1,73,78,500  _(error: gross value of trades — netting ignored)_
- **C.** Net pay-in (pay) of ₹25,46,500  _(error: direction reversed)_
- **D.** Net pay-out (receive) of ₹25,46,500 ✅

**Working**

1. Stock P: pay 49,20,000 − receive 37,12,500 = net pay 12,07,500
2. Stock Q: receive 62,50,000 − pay 24,96,000 = net receive 37,54,000
3. Net funds = ₹25,46,500 receivable

**Formula:** Net funds = Σ sell value − Σ buy value (across securities)  
**Trap:** Novation + netting collapse many obligations into one per member.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-127 · L3 · hard · Clearing corporations and settlement

A client buys shares worth ₹2 crore. The clearing corporation's upfront margin comprises VaR margin of 12.5% and extreme loss margin of 3.5% of position value. Before pay-in, the share price falls 6%; margins are recomputed on the new value and the mark-to-market loss is also collected. Total margin + MTM required at that point is:

- **A.** ₹32,00,000  _(error: initial upfront margin only; MTM ignored)_
- **B.** ₹42,08,000 ✅
- **C.** ₹35,50,000  _(error: extreme loss margin omitted)_
- **D.** ₹44,00,000  _(error: margins not revalued on the lower position value)_

**Working**

1. Initial margin = 16% × ₹2 crore = ₹32,00,000
2. New value = ₹1,88,00,000; margin = ₹30,08,000
3. MTM loss = ₹12,00,000; total = ₹42,08,000

**Formula:** Requirement = (VaR + ELM) × Current value + MTM loss  
**Trap:** MTM is collected on top of the VaR/ELM margin.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-128 · L1 · easy · Credit rating agencies and sovereign ratings

On the long-term rating scales used by S&P/Fitch and Moody's, the LOWEST investment-grade rating is:

- **A.** BB+ (S&P/Fitch) and Ba1 (Moody's)  _(error: highest speculative grade)_
- **B.** BBB− (S&P/Fitch) and Baa3 (Moody's) ✅
- **C.** A− (S&P/Fitch) and A3 (Moody's)  _(error: upper-medium grade, above the cut-off)_
- **D.** BBB (S&P/Fitch) and Baa2 (Moody's)  _(error: one notch above the lowest investment grade)_

**Working**

1. Investment grade: AAA to BBB− / Aaa to Baa3.
2. BB+ / Ba1 and below: speculative ('junk').

**Formula:** —  
**Trap:** BBB− and Baa3 are the equivalent notches.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-129 · L3 · hard · Credit rating agencies and sovereign ratings ⚠

Consider the following statements:

1. A credit rating agency registered with SEBI must have a minimum net worth of ₹25 crore.
2. A 'D' rating indicates that the instrument is in default or expected to be in default soon.
3. A sovereign's local-currency rating is typically equal to or higher than its foreign-currency rating.
4. A SEBI-registered CRA may rate securities issued by its promoter if it discloses the relationship.

Which of the statements given above are correct?

- **A.** 1, 2 and 4 only  _(error: statement 4 is wrong; statement 3 is correct)_
- **B.** 2 and 3 only  _(error: ₹25 crore net-worth requirement (2018 amendment) is correct)_
- **C.** 1, 2, 3 and 4  _(error: rating a promoter's securities is prohibited, not merely disclosed)_
- **D.** 1, 2 and 3 only ✅

**Working**

1. Net worth ₹25 crore (raised from ₹5 crore in 2018) — correct.
2. D = default — correct.
3. Sovereigns can print/borrow in own currency ⇒ LC ≥ FC typically — correct.
4. CRA Regulations prohibit rating securities of its promoter — statement 4 wrong.

**Formula:** —  
**Trap:** Conflict-of-interest rules bar promoter ratings outright.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-130 · L2 · medium · Depositories Act 1996 ⚠

Match the section of the Depositories Act, 1996 (List I) with its subject (List II):

| List I | List II |
|---|---|
| P. Section 9 | 1. Depository deemed registered owner; beneficial owner entitled to all rights and benefits |
| Q. Section 10 | 2. Securities in depositories to be in fungible form |
| R. Section 14 | 3. Depository to indemnify beneficial owner for loss caused by negligence of the depository or participant |
| S. Section 16 | 4. Option to opt out of a depository |

Codes:

- **A.** P-2, Q-1, R-4, S-3 ✅
- **B.** P-1, Q-2, R-4, S-3  _(error: sections 9 and 10 swapped)_
- **C.** P-2, Q-4, R-1, S-3  _(error: section 10 confused with opting out)_
- **D.** P-2, Q-1, R-3, S-4  _(error: sections 14 and 16 swapped)_

**Working**

1. s.9 fungibility; s.10 rights of depositories and beneficial owners; s.14 opting out; s.16 indemnity.

**Formula:** —  
**Trap:** Legal ownership (depository) vs beneficial ownership (investor) — s.10.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-131 · L3 · hard · Depositories Act 1996 ⚠

Consider the following statements under the Depositories Act, 1996:

1. A depository is deemed to be the registered owner for effecting transfer of ownership, but has no voting rights in respect of securities held by it.
2. The beneficial owner is entitled to all rights and liabilities in respect of securities held by a depository.
3. A depository must obtain a certificate of registration from the Reserve Bank of India before commencing business.
4. Securities held in a depository are not identified by distinctive numbers.

Which of the statements given above are correct?

- **A.** 1, 2 and 4 only ✅
- **B.** 1 and 2 only  _(error: fungibility means no distinctive numbers — statement 4 is correct)_
- **C.** 2, 3 and 4 only  _(error: statement 3 is wrong; statement 1 is correct)_
- **D.** 1, 2, 3 and 4  _(error: registration/certificate of commencement is from SEBI, not RBI)_

**Working**

1. s.10(1)–(2): depository is registered owner for transfer; no voting rights — correct.
2. s.10(3): beneficial owner has all rights — correct.
3. Registration and certificate of commencement: SEBI — statement 3 wrong.
4. s.9: fungible, no distinctive numbers — correct.

**Formula:** —  
**Trap:** SEBI, not RBI, regulates depositories.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-132 · L2 · medium · Depositories and dematerialisation ⚠

**Assertion (A):** Shareholders of a listed company holding physical share certificates cannot transfer them to a buyer in physical form, though they can still dematerialise them.

**Reason (R):** SEBI amended the Listing Regulations so that, from 1 April 2019, requests for transfer of securities of listed companies are processed only in dematerialised form (extended to transmission and transposition from January 2022).

Choose the correct option:

- **A.** Both A and R are true, but R does not explain A  _(error: R is the rule that produces A)_
- **B.** Only A is true; R is a false statement of fact  _(error: R correctly states the SEBI amendment)_
- **C.** Only R is true; A is a false statement of fact  _(error: A follows from R; demat of physical shares remains allowed)_
- **D.** Both A and R are true, and R correctly explains A ✅

**Working**

1. Reg 40(1) of LODR (amended 2018, effective 1 April 2019): transfers only in demat.
2. Proviso substituted by LODR (Amendment) Regulations, 24 January 2022: transmission and transposition also only in demat.
3. Holders of physical certificates may still dematerialise them.

**Formula:** —  
**Trap:** Holding in physical form is not banned — transfer is.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-133 · L2 · medium · Digital Public Infrastructure and India Stack

Match the India Stack component (List I) with its layer/function (List II):

| List I | List II |
|---|---|
| P. Aadhaar e-KYC | 1. Consent-based sharing of financial data |
| Q. UPI | 2. Presence-less identity verification |
| R. DigiLocker | 3. Interoperable real-time payments |
| S. Account Aggregator | 4. Issuer-verified digital documents |

Codes:

- **A.** P-4, Q-3, R-2, S-1  _(error: Aadhaar e-KYC and DigiLocker swapped)_
- **B.** P-2, Q-3, R-4, S-1 ✅
- **C.** P-2, Q-1, R-4, S-3  _(error: UPI and AA swapped)_
- **D.** P-2, Q-3, R-1, S-4  _(error: DigiLocker and AA swapped)_

**Working**

1. Identity layer: Aadhaar/e-KYC; payments layer: UPI; data layer: DigiLocker, AA (DEPA).

**Formula:** —  
**Trap:** India Stack = identity + payments + data layers.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-134 · L3 · hard · Dilution and further issue of capital

A company announces a rights issue of 2 shares for every 7 held at ₹330. The cum-rights market price is ₹450. The theoretical ex-rights price (TERP) and the value of one rights entitlement (right to buy one new share) are:

- **A.** TERP ₹423.33; value of a rights entitlement ₹26.67  _(error: value per existing share given instead of per rights entitlement)_
- **B.** TERP ₹544.29; value of a rights entitlement ₹214.29  _(error: divided by old shares only)_
- **C.** TERP ₹390.00; value of a rights entitlement ₹60.00  _(error: simple average of market and subscription price)_
- **D.** TERP ₹423.33; value of a rights entitlement ₹93.33 ✅

**Working**

1. TERP = (7 × 450 + 2 × 330) ÷ 9 = ₹423.33
2. Value of entitlement = 423.33 − 330 = ₹93.33
3. Value per existing share = 450 − 423.33 = ₹26.67 (= 93.33 × 2/7)

**Formula:** TERP = (N·P_cum + n·S)/(N + n); RE value = TERP − S  
**Trap:** Per entitlement vs per existing share differ by the ratio n/N.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-135 · L3 · hard · Dilution and further issue of capital

For the same rights issue (TERP ₹423.33, subscription ₹330), an investor holding 1,400 shares wants neither to invest new cash nor to let her rights lapse. She sells just enough entitlements (at their theoretical value) to fund subscription of the rest. The maximum number of new shares she can take up is:

- **A.** 88 shares ✅
- **B.** 113 shares  _(error: sale proceeds of ALL entitlements divided by subscription price (double counts))_
- **C.** 32 shares  _(error: entitlements valued at value per existing share)_
- **D.** 200 shares  _(error: sells half the entitlements (value ignored))_

**Working**

1. Entitlements = 1,400 × 2/7 = 400
2. Sell (E − x), subscribe x: x × 330 = (400 − x) × 93.33
3. x = 400 × 93.33 ÷ (330 + 93.33) = 88.19 → 88 shares

**Formula:** x = E × V_RE ÷ (S + V_RE)  
**Trap:** Entitlements sold are not available for subscription.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-136 · L3 · hard · Dilution and further issue of capital

A company's profit attributable to equity holders is ₹120 crore with 10 crore weighted average shares. There are 50,00,000 outstanding employee stock options, exercisable at ₹300, and the average market price during the year was ₹450. Under the treasury stock method (Ind AS 33), diluted EPS is:

- **A.** ₹11.61  _(error: shares 'bought back' added instead of the net incremental shares)_
- **B.** ₹12.00  _(error: basic EPS; options ignored)_
- **C.** ₹11.43  _(error: all options added as shares without treasury-stock adjustment)_
- **D.** ₹11.80 ✅

**Working**

1. Incremental shares = 50,00,000 × (1 − 300/450) = 16,66,667
2. Diluted EPS = ₹120 crore ÷ 10,16,66,667 = ₹11.80

**Formula:** Incremental shares = Options × (1 − Exercise price ÷ Average market price)  
**Trap:** Only the 'free' shares dilute.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-137 · L2 · medium · FDI caps and sectoral limits ⚠

Match the sector (List I) with the FDI limit and route (List II) under the consolidated FDI policy:

| List I | List II |
|---|---|
| P. Private sector banking | 1. 20% — Government route |
| Q. Public sector banking | 2. 74% — up to 49% automatic, beyond via Government route |
| R. Multi-brand retail trading | 3. 74% automatic; beyond 74% Government route |
| S. Defence manufacturing | 4. 51% — Government route |

Codes:

- **A.** P-2, Q-1, R-4, S-3 ✅
- **B.** P-3, Q-1, R-4, S-2  _(error: private banking and defence routes swapped)_
- **C.** P-2, Q-4, R-1, S-3  _(error: public sector banking and multi-brand retail swapped)_
- **D.** P-1, Q-2, R-4, S-3  _(error: private and public sector banking swapped)_

**Working**

1. Private banks: 74% (49% automatic).
2. PSBs: 20% government route.
3. Multi-brand retail: 51% government route.
4. Defence: 74% automatic (2020), beyond via government route.

**Formula:** —  
**Trap:** Banking caps differ sharply between private and public sector banks.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-138 · L3 · hard · FDI caps and sectoral limits ⚠

Consider the following statements on India's FDI policy:

1. An entity of a country sharing a land border with India can invest only under the Government route.
2. FDI is prohibited in lottery business and in gambling and betting.
3. FDI up to 100% in telecom services is permitted under the automatic route.
4. FDI up to 100% in print media dealing with news and current affairs is permitted under the automatic route.

Which of the statements given above are correct?

- **A.** 2, 3 and 4 only  _(error: statement 1 (Press Note 3 of 2020) is correct; statement 4 is wrong)_
- **B.** 1 and 2 only  _(error: telecom was moved to 100% automatic in 2021)_
- **C.** 1, 2, 3 and 4  _(error: news print media is capped at 26% under the Government route)_
- **D.** 1, 2 and 3 only ✅

**Working**

1. Press Note 3 (2020) — land-border countries: Government route — correct.
2. Lottery, gambling/betting: prohibited — correct.
3. Telecom: 100% automatic (Oct 2021) — correct.
4. News print media: 26% Government route — statement 4 wrong.

**Formula:** —  
**Trap:** Media caps remain restrictive.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-139 · L1 · easy · FEMA framework and Master Directions ⚠

Under Section 13 of FEMA, 1999, a person contravening its provisions is liable to a penalty of:

- **A.** Imprisonment of up to seven years in every case, in addition to a monetary fine  _(error: FEMA is civil; imprisonment arises only for non-payment of penalty after notice)_
- **B.** Up to thrice the sum involved (or ₹2 lakh if not quantifiable), plus up to ₹5,000 per day if continuing ✅
- **C.** Up to twice the sum involved, with no additional penalty for continuing contraventions  _(error: multiple and continuing penalty misstated)_
- **D.** A fixed penalty of ₹10 lakh per contravention, irrespective of the sum involved or its duration  _(error: penalty is linked to the sum involved)_

**Working**

1. s.13(1): up to thrice the sum involved (if quantifiable) or up to ₹2 lakh; continuing: up to ₹5,000 per day.

**Formula:** —  
**Trap:** FEMA replaced the criminal approach of FERA with civil penalties.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-140 · L3 · hard · FEMA framework and Master Directions ⚠

Consider the following statements:

1. Current account transactions are freely permitted, subject to reasonable restrictions the Central Government may impose in consultation with the RBI.
2. Capital account transactions in debt instruments are regulated by the RBI, while those in non-debt instruments are regulated by the Central Government.
3. Under the Liberalised Remittance Scheme, resident individuals may remit up to USD 2,50,000 per financial year for permissible transactions.
4. Compounding of contraventions under FEMA is not permitted.

Which of the statements given above are correct?

- **A.** 1, 2 and 3 only ✅
- **B.** 1, 2, 3 and 4  _(error: compounding is available under s.15 FEMA)_
- **C.** 2, 3 and 4 only  _(error: statement 1 is correct (s.5); statement 4 is wrong)_
- **D.** 1 and 3 only  _(error: the 2015 amendment to s.6 (effective October 2019) split debt/non-debt powers)_

**Working**

1. s.5 current account — correct.
2. s.6 as amended: RBI (debt), Central Govt (non-debt) — correct.
3. LRS limit USD 2,50,000 per FY — correct.
4. s.15 allows compounding — statement 4 wrong.

**Formula:** —  
**Trap:** Non-debt instruments rules are notified by the Central Government (NDI Rules 2019).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-141 · L3 · hard · FRBM Act targets and fiscal rules

Stylised Union Government accounts (₹ lakh crore): revenue receipts 30.2; non-debt capital receipts 0.9; revenue expenditure 35.6 (of which interest 11.3 and grants for creation of capital assets 2.9); capital expenditure 10.4; nominal GDP 330.0. The fiscal deficit and primary deficit as % of GDP are:

- **A.** Fiscal deficit 4.79%; primary deficit 1.36%  _(error: non-debt capital receipts not deducted)_
- **B.** Fiscal deficit 4.52%; primary deficit 0.21%  _(error: grants for capital assets also deducted for primary deficit)_
- **C.** Fiscal deficit 4.52%; primary deficit 1.09% ✅
- **D.** Fiscal deficit 1.64%; primary deficit -1.79%  _(error: revenue deficit taken as fiscal deficit)_

**Working**

1. Total expenditure = 35.6 + 10.4 = 46.0
2. FD = 46.0 − (30.2 + 0.9) = 14.9 → 4.52%
3. PD = FD − interest = 3.6 → 1.09%

**Formula:** FD = Total exp − (Revenue receipts + Non-debt capital receipts); PD = FD − Interest  
**Trap:** Borrowings are the balancing item, not a receipt.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-142 · L3 · hard · FRBM Act targets and fiscal rules

A government's debt is 57.0% of GDP. The effective interest rate on debt is 7.5%, nominal GDP growth is 10.5%, and it runs a primary deficit of 1.2% of GDP. Next year's debt-to-GDP ratio is closest to:

- **A.** 56.65% ✅
- **B.** 55.45%  _(error: primary deficit ignored)_
- **C.** 59.79%  _(error: interest and growth factors inverted)_
- **D.** 58.20%  _(error: interest–growth differential ignored)_

**Working**

1. d₁ = 0.57 × 1.075/1.105 + 0.012 = 0.5665
2. g > i helps reduce the ratio despite the primary deficit.

**Formula:** d₁ = d₀(1 + i)/(1 + g) + pd  
**Trap:** A favourable i − g gap can offset a moderate primary deficit.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-143 · L1 · easy · FSDC and regulatory coordination ⚠

The Financial Stability and Development Council (FSDC) is:

- **A.** A non-statutory body chaired by the Cabinet Secretary, with a sub-committee under the RBI Governor  _(error: chaired by the Finance Minister)_
- **B.** A statutory body under the SEBI Act, chaired by the SEBI Chairperson with RBI as a member  _(error: not statutory; not chaired by SEBI)_
- **C.** A statutory body under the RBI Act, chaired by the RBI Governor with the FM as a member  _(error: FSDC was set up by executive decision (2010), chaired by the FM)_
- **D.** A non-statutory body chaired by the Finance Minister; its sub-committee is chaired by the RBI Governor ✅

**Working**

1. Set up in December 2010 by government notification.
2. Chair: Finance Minister; members include heads of RBI, SEBI, IRDAI, PFRDA, IBBI.
3. FSDC Sub-Committee chaired by the RBI Governor.

**Formula:** —  
**Trap:** It coordinates; it does not regulate.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-144 · L3 · hard · Finance Commission and devolution criteria

A Finance Commission uses the following horizontal-devolution criteria. State X's share in each criterion (computed by the Commission) is given:

| Criterion | Weight | State X share |
|---|---:|---:|
| Income distance | 45.0% | 9.2% |
| Population | 15.0% | 7.1% |
| Area | 15.0% | 5.8% |
| Forest and ecology | 10.0% | 4.3% |
| Demographic performance | 12.5% | 4.9% |
| Tax and fiscal effort | 2.5% | 6.6% |

State X's share in the States' divisible-pool devolution is closest to:

- **A.** 6.317%  _(error: simple average of criterion shares)_
- **B.** 7.282% ✅
- **C.** 8.768%  _(error: tax & fiscal effort weighted at 25% instead of 2.5%)_
- **D.** 5.714%  _(error: income distance excluded and weights re-scaled)_

**Working**

1. Share = Σ weight × criterion share
2. 0.45×0.092 + 0.15×0.071 + 0.15×0.058 + 0.1×0.043 + 0.125×0.049 + 0.025×0.066 = 0.07283

**Formula:** sᵢ = Σₖ wₖ · sᵢₖ  
**Trap:** Weights must be applied; a simple average misrepresents the formula.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-145 · L2 · medium · Financial Inclusion Index and schemes ⚠

The RBI's Financial Inclusion Index combines three sub-indices — Access (weight 35%), Usage (45%) and Quality (20%). If the sub-index scores are Access 78.0, Usage 55.0 and Quality 60.0, the FI-Index is:

- **A.** 64.33  _(error: equal weights)_
- **B.** 65.30  _(error: usage and quality weights swapped)_
- **C.** 66.35  _(error: access and usage weights swapped)_
- **D.** 64.05 ✅

**Working**

1. FI = 0.35×78.0 + 0.45×55.0 + 0.20×60.0 = 64.05

**Formula:** FI-Index = 0.35 A + 0.45 U + 0.20 Q  
**Trap:** Usage carries the highest weight.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-146 · L3 · hard · Financial Inclusion Index and schemes ⚠

Consider the following statements:

1. The RBI's FI-Index ranges from 0 to 100 and is constructed without any base year.
2. The FI-Index is published annually, in July, for the financial year ended March.
3. Pradhan Mantri Jeevan Jyoti Bima Yojana provides accident insurance cover of ₹2 lakh for an annual premium of ₹20.
4. Income-tax payers are not eligible to join the Atal Pension Yojana from 1 October 2022.

Which of the statements given above are correct?

- **A.** 1 and 2 only  _(error: APY exclusion of income-tax payers (from Oct 2022) is correct)_
- **B.** 2, 3 and 4 only  _(error: statement 1 is correct; statement 3 is wrong)_
- **C.** 1, 2, 3 and 4  _(error: ₹2 lakh accident cover for ₹20 is PMSBY; PMJJBY is life cover)_
- **D.** 1, 2 and 4 only ✅

**Working**

1. FI-Index: 0–100, no base year — correct.
2. Published annually in July — correct.
3. PMJJBY = life cover (₹2 lakh, ₹436 p.a.); ₹20 accident cover is PMSBY — statement 3 wrong.
4. APY: income-tax payers barred from 1 Oct 2022 — correct.

**Formula:** —  
**Trap:** PMJJBY (life) vs PMSBY (accident).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-147 · L2 · medium · Fiscal policy — instruments and stance

**Assertion (A):** Progressive income taxes and unemployment-linked transfers moderate business-cycle fluctuations without any fresh policy decision.

**Reason (R):** During a downturn, tax collections fall and transfers rise automatically, supporting disposable income.

Choose the correct option:

- **A.** Only A is true; R is a false statement of fact  _(error: R is correct)_
- **B.** Both A and R are true, and R correctly explains A ✅
- **C.** Both A and R are true, but R does not explain A  _(error: R is the mechanism of automatic stabilisers)_
- **D.** Only R is true; A is a false statement of fact  _(error: these are automatic (built-in) stabilisers)_

**Working**

1. Automatic stabilisers work through the tax-transfer system with no discretionary action.
2. R describes their counter-cyclical mechanism.

**Formula:** —  
**Trap:** Discretionary vs automatic fiscal policy.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-148 · L3 · hard · Fiscal policy — instruments and stance

In an open economy the marginal propensity to consume is 0.8, the proportional tax rate 0.25 and the marginal propensity to import 0.1. Government raises spending by ₹50,000 crore. The resulting increase in equilibrium income is:

- **A.** ₹2,50,000 crore  _(error: closed-economy multiplier with no taxes (1/(1 − c)))_
- **B.** ₹1,25,000 crore  _(error: imports ignored)_
- **C.** ₹1,00,000 crore ✅
- **D.** ₹1,66,667 crore  _(error: taxes ignored)_

**Working**

1. k = 1 ÷ [1 − 0.8(1 − 0.25) + 0.10] = 1 ÷ 0.50 = 2.00
2. ΔY = 2.00 × 50,000 = ₹1,00,000 crore

**Formula:** k = 1 ÷ [1 − c(1 − t) + m]  
**Trap:** Taxes and imports are leakages that shrink the multiplier.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-149 · L1 · easy · Fund of Funds for Startups ⚠

Consider the following statements about the Fund of Funds for Startups (FFS):

1. It is operated by SIDBI.
2. It invests directly in DPIIT-recognised startups.
3. It contributes to SEBI-registered Alternative Investment Funds, which in turn invest in startups.

Which of the statements given above is/are correct?

- **A.** 1 and 3 only ✅
- **B.** 3 only  _(error: SIDBI manages the FFS — statement 1 is correct)_
- **C.** 1 and 2 only  _(error: the fund-of-funds route is via AIFs (daughter funds))_
- **D.** 1, 2 and 3  _(error: FFS does not invest directly in startups)_

**Working**

1. FFS (₹10,000 crore, approved 2016) is managed by SIDBI.
2. It commits capital to SEBI-registered AIFs, which invest in startups.

**Formula:** —  
**Trap:** A fund of funds invests in funds, not companies.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-150 · L4 · hard · Anchor investors and lock-in ⚠

**Case — Narmada Green Energy Ltd (fictional)** — main-board book-built IPO; the issuer satisfies the profitability track-record route (Reg 6(1), ICDR).

| Item | Data |
|---|---|
| Pre-issue equity shares | 18 crore (promoters 15 crore) |
| Fresh issue | 4 crore shares |
| Offer for sale by promoters | 2 crore shares |
| Price band / final issue price | ₹310–326 / ₹326 |
| Anchor allocation price | ₹320 |
| Profit after tax (latest year) | ₹540 crore |
| Employee / shareholder reservation | Nil |

Assume allocation norms: QIBs not more than 50% of the net offer; anchor investors up to 60% of the QIB portion, 40% of the anchor portion reserved — one-third for domestic mutual funds and the balance for life insurers and pension funds (any unsubscribed part of the latter available to mutual funds).

The maximum number of shares that can be allocated to anchor investors, and the minimum reserved for domestic mutual funds within it, are:

- **A.** 1.80 crore shares; 0.60 crore shares ✅
- **B.** 3.60 crore shares; 1.20 crore shares  _(error: 60% applied to the whole offer instead of the QIB portion)_
- **C.** 1.80 crore shares; 0.90 crore shares  _(error: half (not one-third) reserved for mutual funds)_
- **D.** 1.20 crore shares; 0.40 crore shares  _(error: offer for sale excluded from the offer size)_

**Working**

1. Offer = 4 + 2 = 6 crore shares
2. QIB portion ≤ 50% = 3.0 crore
3. Anchor ≤ 60% × 3.0 = 1.80 crore; MF ≥ one-third = 0.60 crore
4. Total reservation 40% of anchor = 0.72 crore, of which life insurers/pension funds 0.12 crore

**Formula:** Anchor ≤ 0.6 × QIB portion; reservation = 40% of anchor (⅓ MFs + balance LI/PF)  
**Trap:** The offer includes both fresh issue and OFS.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-151 · L4 · hard · Anchor investors and lock-in ⚠

**Case — Narmada Green Energy Ltd (fictional)** — main-board book-built IPO; the issuer satisfies the profitability track-record route (Reg 6(1), ICDR).

| Item | Data |
|---|---|
| Pre-issue equity shares | 18 crore (promoters 15 crore) |
| Fresh issue | 4 crore shares |
| Offer for sale by promoters | 2 crore shares |
| Price band / final issue price | ₹310–326 / ₹326 |
| Anchor allocation price | ₹320 |
| Profit after tax (latest year) | ₹540 crore |
| Employee / shareholder reservation | Nil |

Assume allocation norms: QIBs not more than 50% of the net offer; anchor investors up to 60% of the QIB portion, one-third of the anchor portion reserved for domestic mutual funds.

Anchors are allotted the maximum permissible shares. Which statement about their payment and lock-in is correct?

- **A.** No adjustment — anchors are allotted at the anchor price; 50% locked for 30 days and 50% for 90 days  _(error: anchors must pay the difference when the issue price is higher)_
- **B.** They receive a refund of ₹10.80 crore; all their shares are locked in for 30 days from allotment  _(error: direction of price adjustment reversed and old lock-in)_
- **C.** They pay an additional ₹10.80 crore; 50% locked for 30 days and 50% for 90 days from allotment ✅
- **D.** They pay an additional ₹10.80 crore; all shares locked in for 90 days from listing  _(error: lock-in is staggered and runs from allotment)_

**Working**

1. Issue price ₹326 > anchor price ₹320 ⇒ anchors pay ₹6 × 1.80 crore = ₹10.80 crore
2. Lock-in: 50% for 30 days, 50% for 90 days from allotment.

**Formula:** Top-up = (Issue price − Anchor price) × Anchor shares  
**Trap:** A lower issue price gives no refund; a higher one requires a top-up.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-152 · L4 · hard · Dilution and further issue of capital

**Case — Narmada Green Energy Ltd (fictional)** — main-board book-built IPO; the issuer satisfies the profitability track-record route (Reg 6(1), ICDR).

| Item | Data |
|---|---|
| Pre-issue equity shares | 18 crore (promoters 15 crore) |
| Fresh issue | 4 crore shares |
| Offer for sale by promoters | 2 crore shares |
| Price band / final issue price | ₹310–326 / ₹326 |
| Anchor allocation price | ₹320 |
| Profit after tax (latest year) | ₹540 crore |
| Employee / shareholder reservation | Nil |

Assume allocation norms: QIBs not more than 50% of the net offer; anchor investors up to 60% of the QIB portion, one-third of the anchor portion reserved for domestic mutual funds.

The promoters' post-issue shareholding is closest to:

- **A.** 59.09% ✅
- **B.** 54.17%  _(error: OFS shares treated as newly issued)_
- **C.** 72.22%  _(error: fresh issue ignored in post-issue capital)_
- **D.** 68.18%  _(error: offer for sale ignored)_

**Working**

1. Post-issue shares = 18 + 4 = 22 crore (OFS does not add shares)
2. Promoters = 15 − 2 = 13 crore
3. Holding = 13 ÷ 22 = 59.09%

**Formula:** Post-issue holding = (Pre-issue holding − OFS) ÷ (Pre-issue shares + Fresh issue)  
**Trap:** OFS transfers existing shares; only the fresh issue dilutes.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-153 · L4 · hard · Dilution and further issue of capital

**Case — Narmada Green Energy Ltd (fictional)** — main-board book-built IPO; the issuer satisfies the profitability track-record route (Reg 6(1), ICDR).

| Item | Data |
|---|---|
| Pre-issue equity shares | 18 crore (promoters 15 crore) |
| Fresh issue | 4 crore shares |
| Offer for sale by promoters | 2 crore shares |
| Price band / final issue price | ₹310–326 / ₹326 |
| Anchor allocation price | ₹320 |
| Profit after tax (latest year) | ₹540 crore |
| Employee / shareholder reservation | Nil |

Assume allocation norms: QIBs not more than 50% of the net offer; anchor investors up to 60% of the QIB portion, one-third of the anchor portion reserved for domestic mutual funds.

On the latest profit, the P/E multiple at the issue price on a fully diluted post-issue basis is closest to:

- **A.** 12.07×  _(error: OFS shares added instead of the fresh issue)_
- **B.** 10.87×  _(error: pre-issue share count used)_
- **C.** 13.28× ✅
- **D.** 14.49×  _(error: OFS shares added to post-issue capital)_

**Working**

1. Post-issue EPS = ₹540 crore ÷ 22 crore = ₹24.55
2. P/E = 326 ÷ 24.55 = 13.28×

**Formula:** Post-issue P/E = Issue price ÷ (PAT ÷ Post-issue shares)  
**Trap:** Investors pay for a larger share base after the fresh issue.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-154 · L4 · hard · FRBM Act targets and fiscal rules

**Case — Stylised Union Budget (illustrative figures, ₹ lakh crore)**

| Item | ₹ lakh crore |
|---|---:|
| Tax revenue (net to Centre) | 28.4 |
| Non-tax revenue | 5.6 |
| Recovery of loans | 0.3 |
| Disinvestment receipts | 0.5 |
| Revenue expenditure | 39.4 |
|   of which interest payments | 12.8 |
|   of which grants for creation of capital assets | 3.2 |
| Capital expenditure | 11.2 |
| Gross tax revenue | 42.0 |
|   of which cesses and surcharges | 5.6 |
| Cost of collection | 0.5 |
| Nominal GDP | 356.0 |

The Finance Commission award: 41% of the divisible pool to States; State Y's horizontal share 7.85%.

The fiscal deficit as a percentage of GDP is:

- **A.** 4.58%  _(error: disinvestment treated as financing, not a receipt)_
- **B.** 4.66%  _(error: non-debt capital receipts not deducted)_
- **C.** 4.44% ✅
- **D.** 0.84%  _(error: primary deficit reported)_

**Working**

1. Revenue receipts = 34.0; non-debt capital receipts = 0.8
2. Total expenditure = 50.6
3. FD = 50.6 − 34.8 = 15.8 → 4.44% of GDP

**Formula:** FD = Total expenditure − (RR + NDCR)  
**Trap:** Disinvestment and loan recoveries are non-debt capital receipts.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-155 · L4 · hard · FRBM Act targets and fiscal rules

**Case — Stylised Union Budget (illustrative figures, ₹ lakh crore)**

| Item | ₹ lakh crore |
|---|---:|
| Tax revenue (net to Centre) | 28.4 |
| Non-tax revenue | 5.6 |
| Recovery of loans | 0.3 |
| Disinvestment receipts | 0.5 |
| Revenue expenditure | 39.4 |
|   of which interest payments | 12.8 |
|   of which grants for creation of capital assets | 3.2 |
| Capital expenditure | 11.2 |
| Gross tax revenue | 42.0 |
|   of which cesses and surcharges | 5.6 |
| Cost of collection | 0.5 |
| Nominal GDP | 356.0 |

The Finance Commission award: 41% of the divisible pool to States; State Y's horizontal share 7.85%.

The effective revenue deficit and primary deficit (₹ lakh crore) are:

- **A.** ERD 2.2; PD 15.8  _(error: interest not deducted — fiscal deficit reported as primary deficit)_
- **B.** ERD 2.2; PD -0.2  _(error: grants for capital assets also deducted in computing primary deficit)_
- **C.** ERD 5.4; PD 3.0  _(error: revenue deficit reported as ERD (capital-asset grants not deducted))_
- **D.** ERD 2.2; PD 3.0 ✅

**Working**

1. RD = 39.4 − 34.0 = 5.4
2. ERD = RD − grants for capital assets = 5.4 − 3.2 = 2.2
3. PD = FD − interest = 15.8 − 12.8 = 3.0

**Formula:** ERD = RD − Grants for creation of capital assets; PD = FD − Interest  
**Trap:** ERD was introduced by the 2012 FRBM amendment.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-156 · L4 · hard · Finance Commission and devolution criteria

**Case — Stylised Union Budget (illustrative figures, ₹ lakh crore)**

| Item | ₹ lakh crore |
|---|---:|
| Tax revenue (net to Centre) | 28.4 |
| Non-tax revenue | 5.6 |
| Recovery of loans | 0.3 |
| Disinvestment receipts | 0.5 |
| Revenue expenditure | 39.4 |
|   of which interest payments | 12.8 |
|   of which grants for creation of capital assets | 3.2 |
| Capital expenditure | 11.2 |
| Gross tax revenue | 42.0 |
|   of which cesses and surcharges | 5.6 |
| Cost of collection | 0.5 |
| Nominal GDP | 356.0 |

The Finance Commission award: 41% of the divisible pool to States; State Y's horizontal share 7.85%.

State Y's share of central taxes under the award is closest to:

- **A.** ₹1.1715 lakh crore  _(error: cost of collection not deducted)_
- **B.** ₹1.3518 lakh crore  _(error: 41% applied to gross tax revenue (cesses/surcharges not excluded))_
- **C.** ₹1.1554 lakh crore ✅
- **D.** ₹0.9141 lakh crore  _(error: 41% applied to Centre's net tax revenue)_

**Working**

1. Divisible pool = 42.0 − 5.6 − 0.5 = 35.9
2. States' share = 41% × 35.9 = 14.719
3. State Y = 7.85% × 14.719 = 1.1554

**Formula:** Divisible pool = GTR − Cesses & surcharges − Cost of collection  
**Trap:** Cesses and surcharges are outside the divisible pool.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-157 · L4 · hard · Fiscal policy — instruments and stance

**Case — Stylised Union Budget (illustrative figures, ₹ lakh crore)**

| Item | ₹ lakh crore |
|---|---:|
| Tax revenue (net to Centre) | 28.4 |
| Non-tax revenue | 5.6 |
| Recovery of loans | 0.3 |
| Disinvestment receipts | 0.5 |
| Revenue expenditure | 39.4 |
|   of which interest payments | 12.8 |
|   of which grants for creation of capital assets | 3.2 |
| Capital expenditure | 11.2 |
| Gross tax revenue | 42.0 |
|   of which cesses and surcharges | 5.6 |
| Cost of collection | 0.5 |
| Nominal GDP | 356.0 |

The Finance Commission award: 41% of the divisible pool to States; State Y's horizontal share 7.85%.

The government reallocates ₹1.0 lakh crore from revenue expenditure to capital expenditure within the same total. If the capital-expenditure multiplier is 2.45 and the revenue-expenditure multiplier 0.99, the effect is:

- **A.** Fiscal deficit unchanged; GDP higher by about ₹1.46 lakh crore; ERD rises by ₹1.0 lakh crore  _(error: direction of ERD change reversed)_
- **B.** Fiscal deficit unchanged; GDP higher by about ₹2.45 lakh crore; ERD also unchanged  _(error: revenue-expenditure cut's negative effect ignored)_
- **C.** Fiscal deficit unchanged; GDP higher by about ₹1.46 lakh crore; ERD falls by ₹1.0 lakh crore ✅
- **D.** Fiscal deficit falls by ₹1.0 lakh crore; GDP higher by about ₹2.45 lakh crore; ERD unchanged  _(error: reallocation treated as additional capex financed by deficit reduction)_

**Working**

1. Total expenditure constant ⇒ FD unchanged
2. ΔGDP ≈ 2.45 × 1.0 − 0.99 × 1.0 = 1.46
3. Revenue expenditure falls ⇒ RD and ERD fall by the same amount.

**Formula:** ΔY = k_cap·ΔG_cap + k_rev·ΔG_rev  
**Trap:** Composition of spending matters even at an unchanged deficit.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-158 · L2 · medium · DTAA and tax administration bodies ⚠

Match the body (List I) with its constitutional/statutory basis or function (List II):

| List I | List II |
|---|---|
| P. Central Board of Direct Taxes | 1. Article 279A of the Constitution; recommends GST rates and rules to the Union and States |
| Q. GST Council | 2. Central Boards of Revenue Act, 1963; administers income-tax |
| R. Income Tax Appellate Tribunal | 3. Administers customs and central GST |
| S. Central Board of Indirect Taxes and Customs | 4. Second appellate authority on facts in income-tax disputes |

Codes:

- **A.** P-2, Q-4, R-1, S-3  _(error: GST Council confused with ITAT)_
- **B.** P-3, Q-1, R-4, S-2  _(error: CBDT and CBIC functions swapped)_
- **C.** P-2, Q-1, R-3, S-4  _(error: ITAT and CBIC swapped)_
- **D.** P-2, Q-1, R-4, S-3 ✅

**Working**

1. CBDT and CBIC: Central Boards of Revenue Act 1963.
2. GST Council: Art. 279A (101st Amendment, 2016).
3. ITAT: second appellate and final fact-finding authority in income-tax appeals (Income-tax Act 2025).

**Formula:** —  
**Trap:** Two revenue boards under one 1963 Act.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-159 · L3 · hard · DTAA and tax administration bodies ⚠

For FY 2024-25, a resident individual's total income of ₹24,00,000 includes ₹6,00,000 earned in Country Z, with which India has no tax treaty; tax of ₹1,50,000 was paid in Country Z on that income. Indian tax on total income (including surcharge and health & education cess) is ₹5,14,800. Relief under Section 91 of the Income-tax Act, 1961 is:

- **A.** ₹96,525  _(error: Indian rate applied to foreign income net of foreign tax)_
- **B.** ₹1,23,750  _(error: Indian average rate computed excluding health & education cess)_
- **C.** ₹1,50,000  _(error: full foreign tax allowed as credit)_
- **D.** ₹1,28,700 ✅

**Working**

1. Indian average rate = 5,14,800 ÷ 24,00,000 = 21.45%
2. Foreign rate = 1,50,000 ÷ 6,00,000 = 25%
3. Relief = 6,00,000 × lower rate (21.45%) = ₹1,28,700

**Formula:** s.91 relief = Doubly taxed income × lower of (Indian average rate, foreign rate)  
**Trap:** Relief is capped at the Indian average rate, not the tax actually paid abroad.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-160 · L1 · easy · Direct vs indirect taxes ⚠

Which of the following taxes is administered by the Central Board of Direct Taxes (CBDT)?

- **A.** Customs duty on imported gold  _(error: administered by CBIC)_
- **B.** Central excise duty on petrol  _(error: excise on petroleum is an indirect tax under CBIC)_
- **C.** GST compensation cess  _(error: levied under the GST (Compensation to States) Act; CBIC)_
- **D.** Securities Transaction Tax ✅

**Working**

1. STT is levied under Chapter VII of the Finance (No.2) Act, 2004 and administered by CBDT.
2. It is classified among direct taxes in Union Budget documents.

**Formula:** —  
**Trap:** Levy on a transaction does not by itself make a tax 'indirect' in India's classification.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-161 · L3 · hard · Direct vs indirect taxes

Illustrative data (₹ lakh crore): direct taxes rose from 16.6 to 19.1, indirect taxes from 14.8 to 15.9, and nominal GDP from 300 to 330. Which statement is correct?

- **A.** Direct-tax buoyancy is 1.51 and indirect-tax buoyancy 0.74; the share of direct taxes rises from 52.9% to 54.6% ✅
- **B.** Direct-tax buoyancy is 0.08 and indirect-tax buoyancy 0.04; direct-tax share unchanged  _(error: absolute changes used instead of growth rates)_
- **C.** Direct-tax buoyancy is 1.51 and indirect-tax buoyancy 0.74; the share of direct taxes falls to 45.4%  _(error: indirect share reported as direct share)_
- **D.** Direct-tax buoyancy is 0.66 and indirect-tax buoyancy 1.35; the share of direct taxes rises from 52.9% to 54.6%  _(error: buoyancy inverted (GDP growth ÷ tax growth))_

**Working**

1. GDP growth = 10.0%
2. Direct growth = 15.06% ⇒ buoyancy 1.51
3. Indirect growth = 7.43% ⇒ buoyancy 0.74
4. Direct share: 52.9% → 54.6%

**Formula:** Buoyancy = %ΔTax revenue ÷ %ΔNominal GDP  
**Trap:** Buoyancy > 1 means revenue grows faster than the economy.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-162 · L2 · medium · GST returns and TCS by e-commerce operators ⚠

Match the GST return (List I) with its purpose (List II):

| List I | List II |
|---|---|
| P. GSTR-1 | 1. Statement of tax collected at source by an e-commerce operator |
| Q. GSTR-3B | 2. Statement of outward supplies |
| R. GSTR-8 | 3. Annual return of a regular taxpayer |
| S. GSTR-9 | 4. Summary return with self-assessed tax payment |

Codes:

- **A.** P-4, Q-2, R-1, S-3  _(error: GSTR-1 and GSTR-3B swapped)_
- **B.** P-2, Q-4, R-3, S-1  _(error: GSTR-8 and GSTR-9 swapped)_
- **C.** P-2, Q-1, R-4, S-3  _(error: GSTR-3B confused with the TCS statement)_
- **D.** P-2, Q-4, R-1, S-3 ✅

**Working**

1. GSTR-1: outward supplies (11th monthly / 13th quarterly under QRMP).
2. GSTR-3B: summary return + payment (20th; 22nd/24th for QRMP).
3. GSTR-8: ECO TCS statement (10th).
4. GSTR-9: annual return (31 December).

**Formula:** —  
**Trap:** GSTR-8 is filed by the operator, not the seller.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-163 · L3 · hard · GST returns and TCS by e-commerce operators ⚠

An e-commerce operator's platform records the following for one seller in a month (values exclusive of GST): intra-State taxable supplies ₹30,00,000, inter-State taxable supplies ₹12,00,000, intra-State goods returned during the month ₹3,00,000, and restaurant services ₹6,00,000 on which the operator itself pays tax under Section 9(5). At the TCS rate of 0.5% (0.25% CGST + 0.25% SGST, or 0.5% IGST), total TCS to be collected is:

- **A.** ₹21,000 (CGST ₹7,500 + SGST ₹7,500 + IGST ₹6,000)  _(error: returns not deducted from net taxable supplies)_
- **B.** ₹22,500 (CGST ₹8,250 + SGST ₹8,250 + IGST ₹6,000)  _(error: Section 9(5) supplies included in the TCS base)_
- **C.** ₹39,000 (CGST ₹13,500 + SGST ₹13,500 + IGST ₹12,000)  _(error: pre-July 2024 rate of 1% applied)_
- **D.** ₹19,500 (CGST ₹6,750 + SGST ₹6,750 + IGST ₹6,000) ✅

**Working**

1. Net intra-State = 30,00,000 − 3,00,000 = 27,00,000; 9(5) supplies excluded
2. CGST = SGST = 0.25% × 27,00,000 = ₹6,750
3. IGST = 0.5% × 12,00,000 = ₹6,000
4. Total = ₹19,500

**Formula:** TCS = rate × (Taxable supplies − Returns), excluding s.9(5) supplies  
**Trap:** The rate was halved to 0.5% from 10 July 2024.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-164 · L2 · medium · GST — supply, input tax credit, zero-rated, exports ⚠

Under Section 17(5) of the CGST Act, input tax credit is AVAILABLE on which of the following, for a manufacturer?

- **A.** GST paid on a sedan (seating capacity 5) used by directors for business travel  _(error: motor vehicles ≤ 13 persons are blocked unless used for specified businesses)_
- **B.** GST on outdoor catering for an employees' annual party, not obligatory under any law  _(error: food/outdoor catering blocked unless statutorily obligatory)_
- **C.** GST on membership of a club for senior managers  _(error: club membership is a blocked credit)_
- **D.** GST paid on a goods carriage (truck) used to transport the manufacturer's goods ✅

**Working**

1. s.17(5)(a) blocks motor vehicles for ≤13 persons (with exceptions); goods-transport vehicles are outside the block.
2. s.17(5)(b) blocks food, outdoor catering and club membership (subject to the statutory-obligation exception).

**Formula:** —  
**Trap:** Blocked-credit list is specific — goods transport vehicles are not in it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-165 · L3 · hard · GST — supply, input tax credit, zero-rated, exports ⚠

A registered person's output tax and input tax credit for a month are (₹ lakh):

| Head | Output tax | ITC available |
|---|---:|---:|
| IGST | 2.00 | 3.00 |
| CGST | 4.00 | 5.50 |
| SGST | 4.00 | 1.00 |

Applying Sections 49 and 49A and Rule 88A of the CGST framework, the MINIMUM cash payment and the credit carried forward are:

- **A.** Cash ₹0.50 lakh; no credit carried forward  _(error: CGST credit cross-utilised against SGST liability)_
- **B.** Cash ₹2.00 lakh (SGST); CGST credit ₹1.50 lakh carried forward ✅
- **C.** Cash ₹3.00 lakh (SGST); IGST ₹1.00 lakh and CGST ₹1.50 lakh carried forward  _(error: IGST credit wrongly restricted to IGST liability)_
- **D.** Cash ₹3.00 lakh (SGST); CGST credit ₹2.50 lakh carried forward  _(error: balance IGST credit set off against CGST instead of SGST)_

**Working**

1. IGST credit ₹3.00 lakh: first against IGST ₹2.00 lakh; balance ₹1.00 lakh must be used (s.49A) — apply to SGST.
2. CGST credit ₹5.50 lakh against CGST ₹4.00 lakh; excess ₹1.50 lakh cannot be used for SGST.
3. SGST: 4.00 − 1.00 (IGST) − 1.00 (SGST credit) = ₹2.00 lakh cash.

**Formula:** IGST → IGST, then CGST/SGST in any order; CGST ↛ SGST  
**Trap:** Direct IGST balance to the head whose own credit is insufficient.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-166 · L3 · hard · GST — supply, input tax credit, zero-rated, exports ⚠

Common input tax credit (C2) of a manufacturer for a month is ₹9,00,000. Its turnover in the State is: taxable domestic supplies ₹1,20,00,000, exempt supplies ₹30,00,000 and exports under LUT ₹50,00,000. Under Rule 42, the credit attributable to exempt supplies (D1) to be reversed is:

- **A.** ₹2,25,000  _(error: exempt turnover divided by taxable domestic turnover only)_
- **B.** ₹1,35,000 ✅
- **C.** ₹1,80,000  _(error: zero-rated turnover excluded from total turnover)_
- **D.** ₹3,60,000  _(error: exports treated as exempt supplies)_

**Working**

1. Total turnover F = 1,20,00,000 + 30,00,000 + 50,00,000 = 2,00,00,000
2. D1 = C2 × E/F = 9,00,000 × 30,00,000/2,00,00,000 = ₹1,35,000

**Formula:** D1 = C2 × (Exempt turnover ÷ Total turnover)  
**Trap:** Zero-rated supplies are not exempt — they stay in F but not in E.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-167 · L4 · hard · GST — supply, input tax credit, zero-rated, exports ⚠

**Case — Sutlej Precision Tools Ltd (fictional), registered in Punjab — data for October**

| Inward supply | GST paid (₹) |
|---|---:|
| Raw materials (used for both domestic and export production) | 14,00,000 |
| Input services — job work, freight, testing | 2,00,000 |
| CNC machine (capital goods) | 3,00,000 |
| Sedan car for the Managing Director | 1,50,000 |
| Outdoor catering for staff canteen (not obligatory under any law) | 40,000 |

Outward supplies: domestic taxable ₹2,40,00,000; exports of goods under LUT (without payment of IGST) ₹1,50,00,000. No exempt supplies. Assume all documentary conditions of Section 16 are satisfied and the electronic credit ledger has sufficient balance.

The input tax credit Sutlej can avail for October is:

- **A.** ₹16,00,000  _(error: credit on capital goods wrongly excluded)_
- **B.** ₹20,90,000  _(error: blocked credits on car and catering included)_
- **C.** ₹19,00,000 ✅
- **D.** ₹20,50,000  _(error: passenger car (≤13 seats) treated as eligible)_

**Working**

1. Eligible: raw materials 14,00,000 + input services 2,00,000 + capital goods 3,00,000 = ₹19,00,000
2. Blocked under s.17(5): MD's car, outdoor catering.

**Formula:** Eligible ITC = Total ITC − Blocked credits (s.17(5))  
**Trap:** Capital goods credit is available in full upfront.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-168 · L4 · hard · GST — supply, input tax credit, zero-rated, exports ⚠

**Case — Sutlej Precision Tools Ltd (fictional), registered in Punjab — data for October**

| Inward supply | GST paid (₹) |
|---|---:|
| Raw materials (used for both domestic and export production) | 14,00,000 |
| Input services — job work, freight, testing | 2,00,000 |
| CNC machine (capital goods) | 3,00,000 |
| Sedan car for the Managing Director | 1,50,000 |
| Outdoor catering for staff canteen (not obligatory under any law) | 40,000 |

Outward supplies: domestic taxable ₹2,40,00,000; exports of goods under LUT (without payment of IGST) ₹1,50,00,000. No exempt supplies. Assume all documentary conditions of Section 16 are satisfied and the electronic credit ledger has sufficient balance.

The maximum refund of unutilised ITC on account of exports under LUT, as per Rule 89(4), is closest to:

- **A.** ₹10,00,000  _(error: adjusted total turnover taken as domestic turnover only)_
- **B.** ₹6,15,385 ✅
- **C.** ₹7,30,769  _(error: capital-goods credit included in Net ITC)_
- **D.** ₹16,00,000  _(error: entire Net ITC claimed as refund)_

**Working**

1. Net ITC (inputs + input services) = 16,00,000
2. Adjusted total turnover = 2,40,00,000 + 1,50,00,000 = 3,90,00,000
3. Refund = 1,50,00,000 × 16,00,000 ÷ 3,90,00,000 = ₹6,15,385

**Formula:** Refund = Zero-rated turnover × Net ITC ÷ Adjusted total turnover  
**Trap:** Capital goods credit is excluded from 'Net ITC'.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-169 · L4 · hard · GST — supply, input tax credit, zero-rated, exports ⚠

**Case — Sutlej Precision Tools Ltd (fictional), registered in Punjab — data for October**

| Inward supply | GST paid (₹) |
|---|---:|
| Raw materials (used for both domestic and export production) | 14,00,000 |
| Input services — job work, freight, testing | 2,00,000 |
| CNC machine (capital goods) | 3,00,000 |
| Sedan car for the Managing Director | 1,50,000 |
| Outdoor catering for staff canteen (not obligatory under any law) | 40,000 |

Outward supplies: domestic taxable ₹2,40,00,000; exports of goods under LUT (without payment of IGST) ₹1,50,00,000. No exempt supplies. Assume all documentary conditions of Section 16 are satisfied and the electronic credit ledger has sufficient balance.

Sutlej is considering exporting on payment of IGST instead of under LUT. Which statement is correct?

- **A.** Exporting under LUT requires the exporter to furnish a bank guarantee equal to the IGST foregone on every export consignment it ships  _(error: a bond (with guarantee) is an alternative for ineligible exporters; LUT needs no bank guarantee)_
- **B.** IGST route: shipping bill is deemed the refund claim for IGST paid; LUT route: unutilised ITC refund is claimed within two years of relevant date ✅
- **C.** Under the IGST-payment route, IGST on exports must be paid only in cash and cannot be discharged from the electronic credit ledger balance  _(error: IGST on exports can be paid from ITC)_
- **D.** Exports are exempt supplies, so under either route the common input tax credit attributable to exports must be reversed under Rule 42  _(error: exports are zero-rated, not exempt; credit is available)_

**Working**

1. IGST Act s.16(3): export under LUT (refund of unutilised ITC) or on payment of IGST (refund of IGST).
2. Rule 96: shipping bill deemed refund application for IGST paid on goods exported.
3. s.54(1): refund claim within two years of the relevant date.

**Formula:** —  
**Trap:** Zero-rating means credit is preserved — either by refund of ITC or refund of IGST.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINA-170 · L4 · hard · GST returns and TCS by e-commerce operators ⚠

**Case — Sutlej Precision Tools Ltd (fictional), registered in Punjab — data for October**

| Inward supply | GST paid (₹) |
|---|---:|
| Raw materials (used for both domestic and export production) | 14,00,000 |
| Input services — job work, freight, testing | 2,00,000 |
| CNC machine (capital goods) | 3,00,000 |
| Sedan car for the Managing Director | 1,50,000 |
| Outdoor catering for staff canteen (not obligatory under any law) | 40,000 |

Outward supplies: domestic taxable ₹2,40,00,000; exports of goods under LUT (without payment of IGST) ₹1,50,00,000. No exempt supplies. Assume all documentary conditions of Section 16 are satisfied and the electronic credit ledger has sufficient balance.

Sutlej also sells spare parts intra-State through an e-commerce operator: taxable value ₹12,00,000 with returns of ₹1,20,000 in the month. The TCS collected on Sutlej's supplies and its treatment are:

- **A.** ₹6,000; available in Sutlej's electronic cash ledger once the operator files GSTR-8  _(error: returns not deducted)_
- **B.** ₹5,400; credited to Sutlej's electronic credit ledger as input tax credit for the month  _(error: TCS is credited to the cash ledger, not the credit ledger)_
- **C.** ₹5,400; in Sutlej's electronic cash ledger once the operator files GSTR-8 and Sutlej accepts it ✅
- **D.** ₹10,800; available in Sutlej's electronic cash ledger once the operator files GSTR-8  _(error: old 1% TCS rate applied)_

**Working**

1. Net value = 12,00,000 − 1,20,000 = 10,80,000
2. TCS = 0.5% × 10,80,000 = ₹5,400 (CGST + SGST 0.25% each)
3. Operator files GSTR-8 by the 10th; supplier claims credit in its electronic cash ledger (s.52(7)).

**Formula:** TCS = 0.5% × Net taxable supplies  
**Trap:** TCS is a cash credit, usable to pay any tax liability.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:
