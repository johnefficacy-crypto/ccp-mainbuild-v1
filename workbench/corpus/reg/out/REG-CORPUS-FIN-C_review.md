# REG-CORPUS-FIN-C — finance — SME review sheet (75 Q)

Levels {'L1': 15, 'L2': 22, 'L3': 23, 'L4': 15} · key positions {'A': 19, 'C': 19, 'D': 18, 'B': 19} · microtopics covered 13/111
Status `ai_drafted` / `draft`. ⚠ = verify_fact (statute / rate / threshold — check against current official text).


---

## FINC-001 · L1 · easy · Cost of capital — debt, preference and equity

In computing the specific cost of each source of finance, the cost of debentures is taken net of tax while the cost of preference shares is not. The reason is that:

- **A.** Interest is a tax-deductible expense; preference dividend is an appropriation of profit ✅
- **B.** Preference capital is redeemable, so any tax paid is recovered on its redemption  _(error: invents a tax recovery on redemption)_
- **C.** Debentures are secured, so the lender rather than the company bears the tax  _(error: confuses security with tax incidence)_
- **D.** Preference dividend is cumulative, so it is already stated net of corporate tax  _(error: confuses cumulative feature with tax treatment)_

**Working**

1. Debenture interest is charged against profit before tax, so each ₹1 of interest costs the company ₹(1 − t).
2. Preference dividend is paid out of profit after tax, so there is no tax saving; Kp is used without (1 − t).

**Formula:** Kd = I(1 − t) ÷ NP;  Kp = PD ÷ NP  
**Trap:** Applying (1 − t) to preference dividend understates Kp.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-002 · L1 · easy · Cost of capital — debt, preference and equity

A company finances part of its expansion from retained earnings. Ignoring shareholders' personal taxes, the cost of retained earnings is best taken as:

- **A.** Equal to the post-tax cost of debt, the cheapest source available  _(error: confuses opportunity cost with cheapest source)_
- **B.** Equal to the cost of equity after grossing up for flotation cost  _(error: flotation cost applies only to a fresh issue)_
- **C.** Equal to the cost of equity, with no adjustment for flotation cost ✅
- **D.** Nil, since no dividend is contractually payable on retained profits  _(error: treats retained earnings as cost-free)_

**Working**

1. Retained earnings belong to equity shareholders; their opportunity cost is the return shareholders could earn elsewhere, i.e. Ke.
2. No issue expenses are incurred on retained profits, so Kr = Ke without a flotation adjustment (Ke for a new issue is higher).

**Formula:** Kr = Ke = D1 ÷ P0 + g  
**Trap:** Retained earnings are not free; only the flotation cost is saved.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-003 · L2 · medium · Cost of capital — debt, preference and equity

Vedant Textiles Ltd issues 10% irredeemable debentures of face value ₹100 at the current market price of ₹94. Flotation cost is 2% of the issue price and the tax rate is 25%. The post-tax cost of these debentures is:

- **A.** 7.50%  _(error: face value used as net proceeds)_
- **B.** 7.98%  _(error: flotation cost ignored (market price used as net proceeds))_
- **C.** 10.86%  _(error: pre-tax cost; tax shield on interest ignored)_
- **D.** 8.14% ✅

**Working**

1. Net proceeds = 94 × (1 − 0.02) = ₹92.12
2. Post-tax interest = 10 × (1 − 0.25) = ₹7.50
3. Kd = 7.50 ÷ 92.12 = 8.14%

**Formula:** Kd (irredeemable) = I(1 − t) ÷ NP  
**Trap:** Net proceeds, not face value, form the base.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-004 · L2 · medium · Cost of capital — debt, preference and equity

The equity shares of Sarthak Pharma Ltd trade at ₹120. The dividend just paid is ₹6.00 per share and dividends are expected to grow at 8% a year indefinitely. A fresh issue will involve flotation cost of 4% of the market price. The cost of the new equity is:

- **A.** 13.000%  _(error: D0 used and flotation ignored)_
- **B.** 13.625% ✅
- **C.** 13.208%  _(error: D0 used instead of D1 = D0(1 + g))_
- **D.** 13.400%  _(error: flotation cost ignored — this is the cost of retained earnings)_

**Working**

1. D1 = 6.00 × 1.08 = ₹6.48
2. Net proceeds = 120 × (1 − 0.04) = ₹115.20
3. Ke (new) = 6.48 ÷ 115.20 + 8% = 13.625%

**Formula:** Ke = D1 ÷ P0(1 − f) + g  
**Trap:** Gordon's model needs next year's dividend, not the one just paid.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-005 · L3 · hard · Cost of capital — debt, preference and equity

Kaveri Cables Ltd issues redeemable debentures on the following terms:

| Particulars | Data |
|---|---:|
| Face value | ₹1,000 |
| Coupon | 11% |
| Issue price | 2% discount to face value |
| Flotation cost | 3% of face value |
| Redemption | At 5% premium after 8 years |
| Tax rate | 30% |

Using the approximation method, the post-tax cost of the debentures is:

- **A.** 8.54%  _(error: redemption premium ignored (redeemed at par))_
- **B.** 9.42%  _(error: net proceeds used as the denominator instead of the average of RV and NP)_
- **C.** 8.58%  _(error: tax shield also applied to the amortised discount and premium)_
- **D.** 8.95% ✅

**Working**

1. NP = 1000 − 2% discount − 3% flotation = ₹950; RV = ₹1050
2. Annual post-tax interest = 110 × (1 − 0.3) = ₹77; amortisation = (1050 − 950) ÷ 8 = ₹12.50
3. Kd = (77 + 12.50) ÷ [(1050 + 950) ÷ 2] = 8.95%

**Formula:** Kd = [I(1 − t) + (RV − NP)/n] ÷ [(RV + NP)/2]  
**Trap:** Both the issue discount and the flotation cost reduce NP; the premium raises RV.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-006 · L3 · hard · Cost of capital — debt, preference and equity

Anvaya Chemicals Ltd issues 9% preference shares of ₹100 each at par. Flotation cost is 3% of the issue price and the shares are redeemable at a premium of 10% after 10 years. The company's tax rate is 25%. The cost of preference capital is:

- **A.** 10.62%  _(error: net proceeds used as the denominator)_
- **B.** 9.95% ✅
- **C.** 7.78%  _(error: tax shield wrongly applied to preference dividend)_
- **D.** 9.44%  _(error: redemption premium ignored)_

**Working**

1. NP = 100 × (1 − 0.03) = ₹97; RV = ₹110; PD = ₹9
2. Kp = (9 + (110 − 97) ÷ 10) ÷ [(110 + 97) ÷ 2] = 10.30 ÷ 103.5 = 9.95%
3. The tax rate is irrelevant: preference dividend is not tax-deductible.

**Formula:** Kp = [PD + (RV − NP)/n] ÷ [(RV + NP)/2]  
**Trap:** The tax rate in the stem is a lure.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-007 · L3 · hard · Cost of capital — debt, preference and equity

Nirmal Agro Ltd has just reported EPS of ₹20. It retains 60% of earnings and earns a return of 15% on equity, which is expected to continue. The share trades at ₹150. Using the dividend growth model with g = b × r, the cost of equity is:

- **A.** 14.33%  _(error: D0 used instead of D1)_
- **B.** 14.81% ✅
- **C.** 11.65%  _(error: growth computed as payout × r instead of retention × r)_
- **D.** 17.72%  _(error: retained portion taken as the dividend (retention confused with payout))_

**Working**

1. g = b × r = 0.6 × 0.15 = 9%
2. D0 = 20 × (1 − 0.6) = ₹8.00; D1 = 8.00 × 1.09 = ₹8.72
3. Ke = 8.72 ÷ 150 + 9% = 14.81%

**Formula:** g = b × r;  Ke = D1 ÷ P0 + g  
**Trap:** Growth comes from the retained portion; the dividend is the paid-out portion.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-008 · L1 · easy · Weighted average and marginal cost of capital

A firm plans to raise new capital in a fixed target mix. In constructing its marginal cost of capital schedule, a break point occurs at a total new financing equal to:

- **A.** The amount of the cheaper tranche of a source × that source's weight  _(error: multiplies by the weight instead of dividing)_
- **B.** The amount of the cheaper tranche of a source ÷ the firm's current WACC  _(error: divides by WACC instead of the weight)_
- **C.** The amount of the cheaper tranche of a source ÷ that source's weight ✅
- **D.** The total new capital required ÷ the weight of the costliest source  _(error: uses total requirement, not the tranche limit)_

**Working**

1. When a source's cheaper tranche is exhausted, its component cost rises, and so does WACC.
2. Because that source provides only its weight w of every rupee raised, the tranche lasts until total financing = Tranche ÷ w.

**Formula:** Break point = Limit of cheaper funds ÷ Weight of that source  
**Trap:** Dividing by the weight grosses the tranche up to total capital.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-009 · L2 · medium · Weighted average and marginal cost of capital

Ishaan Motors Ltd uses the following target capital structure. Its tax rate is 30%.

| Source | Target weight | Cost |
|---|---:|---:|
| Equity | 60% | 16% |
| Preference | 10% | 11% |
| Debt (pre-tax) | 30% | 12% |

The weighted average cost of capital is:

- **A.** 13.22% ✅
- **B.** 12.89%  _(error: tax shield also applied to preference dividend)_
- **C.** 14.30%  _(error: pre-tax cost of debt used)_
- **D.** 11.80%  _(error: simple average of component costs; weights ignored)_

**Working**

1. Post-tax Kd = 12% × (1 − 0.30) = 8.40%
2. WACC = 0.60 × 16% + 0.10 × 11% + 0.30 × 8.40% = 9.60% + 1.10% + 2.52%
3. = 13.22%

**Formula:** WACC = Σ wᵢ kᵢ with Kd post-tax  
**Trap:** Only debt gets the tax shield.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-010 · L2 · medium · Weighted average and marginal cost of capital

Extract from the books of Tarang Electricals Ltd:

| Source | Book value (₹ lakh) | Market data | Cost |
|---|---:|---:|---:|
| Equity shares (₹10 each) | 50 | 5 lakh shares at ₹36 | 15% |
| Retained earnings | 20 | — | 15% |
| 12% debentures | 30 | ₹105 per ₹100 | 8.40% (post-tax) |

The weighted average cost of capital using market-value weights is:

- **A.** 14.10%  _(error: retained earnings added again to the market value of equity)_
- **B.** 14.02% ✅
- **C.** 14.06%  _(error: debentures taken at book value while equity is at market value)_
- **D.** 13.02%  _(error: book-value weights used)_

**Working**

1. Market value of equity = 5 lakh × ₹36 = ₹180 lakh (this already includes retained earnings)
2. Market value of debentures = 30 × 105/100 = ₹31.5 lakh
3. WACC = (180 × 15% + 31.5 × 8.4%) ÷ 211.5 = 14.02%

**Formula:** Market WACC = (E_m·Ke + D_m·Kd) ÷ (E_m + D_m)  
**Trap:** Retained earnings are part of equity's market value; do not add them twice.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-011 · L3 · hard · Weighted average and marginal cost of capital

Ojas Ceramics Ltd raises new funds in the ratio debt 40 : equity 60. Retained earnings of ₹18 lakh are available at a cost of 15%; beyond that, new equity costs 17%. The first ₹10 lakh of debt costs 7% post-tax and further debt costs 8.4% post-tax. If the company raises ₹28 lakh in total, the marginal cost of capital on the last rupee raised is:

- **A.** 11.80%  _(error: break points ignored; cheapest component costs used throughout)_
- **B.** 11.86%  _(error: average cost over the whole ₹28 lakh instead of the marginal cost)_
- **C.** 13.56%  _(error: tranche limits taken as break points without dividing by weights)_
- **D.** 12.36% ✅

**Working**

1. Break point (debt) = 10 ÷ 0.4 = ₹25 lakh; break point (retained earnings) = 18 ÷ 0.6 = ₹30 lakh
2. At ₹28 lakh: debt is in the costlier tranche (8.4%), equity still from retained earnings (15%)
3. MCC = 0.40 × 8.4% + 0.60 × 15% = 12.36%

**Formula:** Break point = Tranche ÷ Weight; MCC = Σ w × marginal component cost  
**Trap:** ₹28 lakh lies between the ₹25 lakh and ₹30 lakh break points.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-012 · L3 · hard · Weighted average and marginal cost of capital

Capital of Lohit Paper Ltd:

| Source | Book value (₹ lakh) | Market price |
|---|---:|---:|
| Equity shares of ₹10 each | 100 | ₹50 per share |
| 10% irredeemable preference shares | 20 | ₹95 per ₹100 |
| 12% irredeemable debentures | 40 | ₹96 per ₹100 |

The next dividend expected on equity is ₹4 per share, growing at 6% a year. The tax rate is 25%. Using market-value weights and market prices for component costs, WACC is:

- **A.** 13.99%  _(error: ₹4 treated as D0 and grown again)_
- **B.** 13.78%  _(error: pre-tax cost of debentures used)_
- **C.** 13.56% ✅
- **D.** 12.41%  _(error: book-value weights used)_

**Working**

1. Ke = 4/50 + 6% = 14%; Kp = 10/95 = 10.53%; Kd = 12 × 0.75/96 = 9.38%
2. Market values: E = ₹500 lakh, P = ₹19 lakh, D = ₹38.4 lakh; total ₹557.4 lakh
3. WACC = (500 × 14% + 19 × 10.53% + 38.4 × 9.38%) ÷ 557.4 = 13.56%

**Formula:** WACC = Σ (MVᵢ × kᵢ) ÷ Σ MVᵢ  
**Trap:** The stated dividend is already D1.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-013 · L1 · easy · CAPM, beta and the security market line

In the Capital Asset Pricing Model, the beta of a security measures:

- **A.** Its excess return over that predicted by the market model  _(error: that is alpha, not beta)_
- **B.** Its systematic risk — sensitivity of its return to market returns ✅
- **C.** Its unsystematic risk — variation specific to the company  _(error: diversifiable risk is not priced in CAPM)_
- **D.** Its total risk — the standard deviation of its own returns  _(error: total risk, not systematic risk)_

**Working**

1. β = Cov(Ri, Rm) ÷ Var(Rm): the co-movement of the security with the market.
2. Only this non-diversifiable (systematic) risk earns a premium in CAPM.

**Formula:** β = Cov(i, m) ÷ σm²  
**Trap:** Beta is not total risk; a stock can be volatile yet have a low beta.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-014 · L1 · easy · CAPM, beta and the security market line

Consider the following statements:

1. The security market line relates expected return to beta and applies to individual securities as well as portfolios.
2. The capital market line relates expected return to standard deviation and applies only to efficient portfolios.
3. A security whose expected return plots above the security market line is overvalued.

Which of the statements is/are correct?

- **A.** 1 only  _(error: wrongly rejects statement 2: CML uses σ and holds only for efficient portfolios)_
- **B.** 1 and 2 only ✅
- **C.** All of 1, 2 and 3  _(error: wrongly accepts statement 3: above the SML the security offers more than its required return, i.e. it is undervalued)_
- **D.** 2 only  _(error: wrongly rejects statement 1: SML uses beta and holds for every asset)_

**Working**

1. SML: E(R) = Rf + β(Rm − Rf) — valid for any security or portfolio.
2. CML: E(Rp) = Rf + [(Rm − Rf)/σm]σp — valid only for efficient (fully diversified) portfolios.
3. Above the SML → expected return > required return → price too low → undervalued (positive alpha).

**Formula:** SML vs CML  
**Trap:** Above SML means undervalued, not overvalued.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-015 · L2 · medium · CAPM, beta and the security market line

The covariance between the returns of Pranav Steel Ltd and the market index is 0.0216. The standard deviation of the market return is 15% and that of Pranav Steel is 20%. The risk-free rate is 7% and the expected market return is 12.5%. The required return on Pranav Steel is:

- **A.** 14.33%  _(error: ratio of standard deviations used as beta, ignoring correlation)_
- **B.** 10.96%  _(error: correlation coefficient used as beta)_
- **C.** 12.28% ✅
- **D.** 12%  _(error: β × Rm; risk-free rate ignored)_

**Working**

1. β = Cov ÷ σm² = 0.0216 ÷ 0.0225 = 0.96
2. Required return = 7% + 0.96 × (12.5% − 7%) = 12.28%

**Formula:** β = Cov(i,m)/σm²;  k = Rf + β(Rm − Rf)  
**Trap:** Divide the covariance by market variance, not by σm or σi·σm.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-016 · L2 · medium · CAPM, beta and the security market line

An investor holds the following portfolio:

| Stock | Shares held | Price (₹) | Beta |
|---|---:|---:|---:|
| A | 2,000 | 200 | 1.4 |
| B | 5,000 | 70 | 0.8 |
| C | 1,000 | 250 | 1.1 |

The risk-free rate is 6% and the market return 12%. The required return on the portfolio under CAPM is:

- **A.** 11.92%  _(error: betas weighted by number of shares instead of market value)_
- **B.** 13.38%  _(error: portfolio beta × Rm; risk-free rate ignored)_
- **C.** 12.69% ✅
- **D.** 12.60%  _(error: simple average of betas)_

**Working**

1. Market values: A ₹4,00,000, B ₹3,50,000, C ₹2,50,000; total ₹10,00,000
2. βp = (0.40 × 1.4) + (0.35 × 0.8) + (0.25 × 1.1) = 1.115
3. Required return = 6% + 1.115 × 6% = 12.69%

**Formula:** βp = Σ wᵢβᵢ (value weights)  
**Trap:** Weights are market values, not share counts.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-017 · L3 · hard · CAPM, beta and the security market line

The risk-free rate is 6% and the expected market return 13%.

| Stock | Beta | Analyst's expected return |
|---|---:|---:|
| P | 1.2 | 15.0% |
| Q | 0.8 | 11.2% |
| R | 1.5 | 16.0% |
| S | 0.6 | 10.8% |

On the basis of the security market line, which stocks are undervalued?

- **A.** P and S ✅
- **B.** Q and S  _(error: expected return compared with β × Rm, ignoring the risk-free rate)_
- **C.** P and R  _(error: highest expected returns taken as undervalued without adjusting for beta)_
- **D.** Q and R  _(error: sign of alpha reversed — these plot below the SML)_

**Working**

1. Required return = 6% + β × 7%: P = 14.4%; Q = 11.6%; R = 16.5%; S = 10.2%
2. Alpha = expected − required: P = +0.6%; Q = -0.4%; R = -0.5%; S = +0.6%
3. Positive alpha (above SML) → undervalued: P and S

**Formula:** α = E(R) − [Rf + β(Rm − Rf)]  
**Trap:** A high expected return is not a bargain if beta is higher still.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-018 · L3 · hard · CAPM, beta and the security market line

Returns over five years:

| Year | Market return (%) | Return on Hemant Ltd (%) |
|---|---:|---:|
| 1 | 10 | 15 |
| 2 | 6 | 4 |
| 3 | -2 | 1 |
| 4 | 14 | 18 |
| 5 | 12 | 9 |

The beta of Hemant Ltd, estimated from these data, is closest to:

- **A.** 1.13  _(error: ratio of standard deviations (σi/σm), ignoring correlation)_
- **B.** 0.86  _(error: correlation coefficient reported as beta)_
- **C.** 0.76  _(error: covariance divided by the variance of the stock instead of the market)_
- **D.** 0.97 ✅

**Working**

1. Mean market return = 8.0%; mean stock return = 9.4%
2. Cov(i,m) = Σ(dm × di) ÷ 5 = 31.20; Var(m) = Σdm² ÷ 5 = 32.00
3. β = 31.20 ÷ 32.00 = 0.97

**Formula:** β = Cov(i,m) ÷ Var(m)  
**Trap:** Whether n or n − 1 is used cancels out in the ratio.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-019 · L1 · easy · Capital budgeting — payback and discounted payback

Consider the following statements about payback methods:

1. The simple payback period ignores the time value of money.
2. For a conventional project with a positive discount rate, the discounted payback period is longer than the simple payback period.
3. The discounted payback period, unlike the simple payback period, takes into account cash flows arising after the payback year.

Which of the statements is/are correct?

- **A.** 1 and 2 only ✅
- **B.** All of 1, 2 and 3  _(error: wrongly accepts statement 3: both methods ignore post-payback cash flows)_
- **C.** 1 only  _(error: wrongly rejects statement 2: discounted flows are smaller, so recovery takes longer)_
- **D.** 2 only  _(error: wrongly rejects statement 1: payback adds undiscounted flows)_

**Working**

1. Simple payback accumulates undiscounted cash flows → no time value.
2. Each discounted inflow is smaller than its undiscounted value, so cumulative recovery is slower.
3. Both methods stop at the recovery point; later cash flows are ignored — the key weakness shared by both.

**Formula:** Payback = years to recover outlay  
**Trap:** Discounting fixes time value, not the post-payback blind spot.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-020 · L2 · medium · Capital budgeting — payback and discounted payback

A project costing ₹12 lakh is expected to generate:

| Year | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|
| Cash inflow (₹ lakh) | 3 | 4 | 3.5 | 3 | 2.5 |

Its payback period is:

- **A.** 3.50 years ✅
- **B.** 4.00 years  _(error: whole years only; no interpolation)_
- **C.** 3.75 years  _(error: outlay divided by average annual inflow)_
- **D.** 3.43 years  _(error: balance divided by the previous year's inflow)_

**Working**

1. Cumulative inflows: 3, 7, 10.5, 13.5, 16
2. After 3 years ₹10.5 lakh is recovered; balance ₹1.5 lakh
3. Payback = 3 + 1.5/3 = 3.50 years

**Formula:** Payback = Years before recovery + Unrecovered balance ÷ Inflow of recovery year  
**Trap:** Averaging uneven flows misstates payback.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-021 · L2 · medium · Capital budgeting — payback and discounted payback

A machine costing ₹10 lakh has a life of 5 years with no salvage and is depreciated on a straight-line basis. It will add ₹3.6 lakh a year to earnings before depreciation and tax. The tax rate is 30%. The payback period on cash flow after tax is:

- **A.** 3.97 years  _(error: tax charged on earnings before depreciation; tax shield ignored)_
- **B.** 8.93 years  _(error: profit after tax used; depreciation not added back)_
- **C.** 3.21 years ✅
- **D.** 2.78 years  _(error: pre-tax cash flow used)_

**Working**

1. Depreciation = 10/5 = ₹2 lakh
2. CFAT = (3.6 − 2) × (1 − 0.3) + 2 = ₹3.12 lakh
3. Payback = 10 ÷ 3.12 = 3.21 years

**Formula:** CFAT = (EBDT − Dep)(1 − t) + Dep  
**Trap:** Depreciation is non-cash but saves tax.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-022 · L3 · hard · Capital budgeting — payback and discounted payback

A project requires an outlay of ₹8 lakh.

| Year | 1 | 2 | 3 | 4 |
|---|---:|---:|---:|---:|
| Cash inflow (₹ lakh) | 2.5 | 3 | 3.5 | 2 |
| PV factor at 10% | 0.909 | 0.826 | 0.751 | 0.683 |

Its discounted payback period is:

- **A.** 4.00 years  _(error: whole years only; no interpolation)_
- **B.** 3.31 years  _(error: fraction of final year computed on the undiscounted inflow)_
- **C.** 2.71 years  _(error: simple (undiscounted) payback)_
- **D.** 3.45 years ✅

**Working**

1. PVs: 2.2725, 2.4780, 2.6285, 1.3660
2. Cumulative PV after 3 years = 7.3790; balance = 0.6210
3. Discounted payback = 3 + 0.6210/1.3660 = 3.45 years

**Formula:** DPB = Years before recovery + Unrecovered PV ÷ PV of recovery-year inflow  
**Trap:** Interpolate on the discounted inflow of the recovery year.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-023 · L1 · easy · Capital budgeting — NPV, IRR, PI and MIRR

The modified internal rate of return (MIRR) differs from the conventional IRR chiefly because MIRR assumes that intermediate cash inflows are reinvested at:

- **A.** A zero rate, so that only nominal inflows are summed  _(error: confuses MIRR with undiscounted payback logic)_
- **B.** The risk-free rate, so that reinvestment risk is removed  _(error: not the standard MIRR assumption)_
- **C.** The firm's cost of capital (or a specified reinvestment rate) ✅
- **D.** The project's own IRR, as in the conventional method  _(error: that is the IRR reinvestment assumption)_

**Working**

1. MIRR compounds inflows to a terminal value at the cost of capital (or a stated rate).
2. It then finds the rate equating PV of outflows with that terminal value — giving a single, realistic rate.

**Formula:** MIRR = (TV of inflows at k ÷ PV of outflows)^(1/n) − 1  
**Trap:** IRR implicitly assumes reinvestment at the IRR itself.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-024 · L2 · medium · Capital budgeting — NPV, IRR, PI and MIRR

Suryoday Packaging Ltd evaluates a project costing ₹20 lakh.

| Year | 1 | 2 | 3 | 4 |
|---|---:|---:|---:|---:|
| Cash inflow (₹ lakh) | 6 | 7 | 8 | 5 |
| PV factor at 12% | 0.893 | 0.797 | 0.712 | 0.636 |

The NPV of the project is:

- **A.** −₹18,700 ✅
- **B.** ₹2,18,700  _(error: year-1 inflow left undiscounted; factors shifted one year)_
- **C.** −₹25,950  _(error: average inflow multiplied by the 4-year annuity factor)_
- **D.** ₹18,700  _(error: sign reversed (outlay minus PV of inflows))_

**Working**

1. PV of inflows = 6×0.893 + 7×0.797 + 8×0.712 + 5×0.636 = ₹19.813 lakh
2. NPV = 19.813 − 20 = −₹0.187 lakh = −₹18,700

**Formula:** NPV = Σ CFt × PVFt − Outlay  
**Trap:** Undiscounted inflows (₹26 lakh) comfortably exceed cost, but the NPV is negative.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-025 · L2 · medium · Capital budgeting — NPV, IRR, PI and MIRR

A project's NPV is ₹12,400 at a discount rate of 14% and −₹8,600 at 18%. By linear interpolation, its IRR is:

- **A.** 14.59%  _(error: fraction added as percentage points without multiplying by the 4% rate gap)_
- **B.** 16.77%  _(error: ratio of the two NPVs used as the fraction)_
- **C.** 16.36% ✅
- **D.** 15.64%  _(error: NPV at the higher rate placed in the numerator)_

**Working**

1. Total NPV swing = 12,400 + 8,600 = 21,000
2. IRR = 14% + (12,400 ÷ 21,000) × 4% = 16.36%

**Formula:** IRR = L + [NPV_L ÷ (NPV_L − NPV_H)] × (H − L)  
**Trap:** The NPV at the lower rate drives the fraction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-026 · L3 · hard · Capital budgeting — NPV, IRR, PI and MIRR

Dhruv Castings Ltd is appraising a new plant:

| Particulars | Data |
|---|---:|
| Cost of plant | ₹30.00 lakh |
| Working capital (year 0, released year 5) | ₹4.00 lakh |
| Life / estimated and actual salvage | 5 years / ₹3.00 lakh |
| Depreciation | Straight-line on (cost − salvage) |
| Annual earnings before depreciation and tax | ₹10.00 lakh |
| Tax rate | 30% |
| Cost of capital; PVAF(12%, 5); PVF(12%, yr 5) | 12%; 3.605; 0.567 |

The NPV of the project is:

- **A.** ₹1.69 lakh  _(error: depreciation charged on full cost although salvage is recovered)_
- **B.** −₹1.22 lakh  _(error: working capital invested but its release in year 5 omitted)_
- **C.** ₹2.78 lakh  _(error: working capital omitted from both the outlay and the terminal inflow)_
- **D.** ₹1.04 lakh ✅

**Working**

1. Depreciation = (30 − 3)/5 = ₹5.4 lakh; CFAT = (10 − 5.4) × 0.7 + 5.4 = ₹8.62 lakh
2. PV of CFAT = 8.62 × 3.605 = ₹31.075 lakh
3. Terminal inflow = salvage 3 (equals book value, no tax) + WC 4 = ₹7 lakh; PV = ₹3.969 lakh
4. NPV = 31.075 + 3.969 − 34 = ₹1.044 lakh

**Formula:** NPV = PV(CFAT) + PV(salvage + WC) − (Cost + WC)  
**Trap:** Working capital is an outflow at the start and an inflow at the end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-027 · L3 · hard · Capital budgeting — NPV, IRR, PI and MIRR

A machine costing ₹20 lakh is fully depreciated on a straight-line basis over 4 years (nil book value at the end). In year 4, it generates earnings before depreciation and tax of ₹7 lakh, is sold for ₹2.5 lakh, and working capital of ₹1.5 lakh is released. Tax is 30%, and any profit on sale of the asset is taxed at the same rate. The total cash flow in year 4 is:

- **A.** ₹9.65 lakh ✅
- **B.** ₹10.40 lakh  _(error: sale proceeds taken gross; tax on profit on sale ignored)_
- **C.** ₹8.15 lakh  _(error: release of working capital omitted)_
- **D.** ₹9.20 lakh  _(error: tax wrongly charged on the working capital released)_

**Working**

1. Operating CFAT = (7 − 5) × 0.7 + 5 = ₹6.40 lakh
2. Profit on sale = 2.5 − 0 (book value) = ₹2.5; tax = ₹0.75; net salvage = ₹1.75 lakh
3. Year-4 cash flow = 6.40 + 1.75 + 1.5 = ₹9.65 lakh

**Formula:** Terminal CF = Operating CFAT + Salvage − Tax on (Salvage − BV) + WC released  
**Trap:** Release of working capital is not taxable.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-028 · L3 · hard · Capital budgeting — NPV, IRR, PI and MIRR

A project costs ₹10 lakh and yields ₹4 lakh, ₹5 lakh and ₹4 lakh at the end of years 1, 2 and 3. The cost of capital is 10%. The project's MIRR is:

- **A.** 14.33%  _(error: conventional IRR (reinvestment at IRR) reported)_
- **B.** 12.77% ✅
- **C.** 14.47%  _(error: simple average return on terminal value; no compounding)_
- **D.** 16.41%  _(error: every inflow compounded one year too many (terminal value × 1.10))_

**Working**

1. Terminal value at 10% = 4 × 1.21 + 5 × 1.10 + 4 = ₹14.34 lakh
2. MIRR = (14.34 ÷ 10)^(1/3) − 1 = 12.77%
3. Compare IRR = 14.33%: MIRR is lower because inflows earn only 10% on reinvestment.

**Formula:** MIRR = (TV ÷ PV of outlay)^(1/n) − 1  
**Trap:** The final inflow is not compounded.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-029 · L1 · easy · NPV vs IRR conflict and capital rationing

When NPV and IRR rank two mutually exclusive projects differently, the NPV ranking is generally preferred because NPV:

- **A.** Can be computed for uneven cash flows, whereas the IRR cannot be computed  _(error: IRR can be computed for uneven flows)_
- **B.** Measures absolute wealth added, assuming reinvestment at the cost of capital ✅
- **C.** Is always numerically higher than the IRR computed for the same project  _(error: compares a ₹ amount with a %)_
- **D.** Is the only method that properly recognises the time value of money  _(error: IRR also discounts cash flows)_

**Working**

1. NPV measures the ₹ increase in shareholder wealth — the objective of the firm.
2. Its implicit reinvestment rate (cost of capital) is more realistic than the IRR's own-rate assumption.

**Formula:** Mutually exclusive → choose higher NPV  
**Trap:** IRR is a relative measure and ignores scale.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-030 · L2 · medium · NPV vs IRR conflict and capital rationing

Two mutually exclusive projects have the following cash flows:

| Year | 0 | 1 | 2 |
|---|---:|---:|---:|
| Project A (₹ lakh) | -20 | 4 | 24 |
| Project B (₹ lakh) | -20 | 16 | 9 |

The crossover (Fisher's) rate at which both projects have the same NPV is:

- **A.** 25% ✅
- **B.** 19.05%  _(error: simple average of the two IRRs)_
- **C.** 18.10%  _(error: IRR of the lower-IRR project taken as the crossover rate)_
- **D.** 20%  _(error: IRR of the higher-IRR project taken as the crossover rate)_

**Working**

1. Incremental flows (A − B): year 1 = -12, year 2 = +15
2. Set -12/(1 + r) + 15/(1 + r)² = 0 → 1 + r = 15/12 → r = 25%
3. For reference: IRR(A) = 20%, IRR(B) = 18.10%.

**Formula:** Crossover rate = IRR of incremental cash flows  
**Trap:** The Fisher rate is not derived from the two IRRs.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-031 · L2 · medium · NPV vs IRR conflict and capital rationing

Capital available this year is limited to ₹50 lakh. All projects are divisible and independent.

| Project | Outlay (₹ lakh) | NPV (₹ lakh) |
|---|---:|---:|
| P | 20 | 6.0 |
| Q | 15 | 6.0 |
| R | 25 | 7.0 |
| S | 10 | 2.5 |

The maximum total NPV achievable is:

- **A.** ₹15.90 lakh  _(error: projects ranked by smallest outlay)_
- **B.** ₹15.00 lakh  _(error: projects ranked by absolute NPV)_
- **C.** ₹16.20 lakh ✅
- **D.** ₹15.50 lakh  _(error: projects treated as indivisible)_

**Working**

1. PI = 1 + NPV/Outlay: P 1.30, Q 1.40, R 1.28, S 1.25 → rank Q, P, R, S
2. Q (₹15 lakh) + P (₹20 lakh) = ₹35 lakh; balance ₹15 lakh → 15/25 of R
3. NPV = 6.0 + 6.0 + 0.6 × 7.0 = ₹16.20 lakh

**Formula:** Divisible rationing: rank by PI (NPV per ₹ of outlay)  
**Trap:** With divisibility, fractional projects fill the budget exactly.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-032 · L3 · hard · NPV vs IRR conflict and capital rationing

Kshitij Infra Ltd has ₹50 lakh for capital projects this year. The projects are independent and indivisible; unused funds earn nothing extra.

| Project | Outlay (₹ lakh) | NPV (₹ lakh) | PI |
|---|---:|---:|---:|
| A | 35 | 12.6 | 1.36 |
| B | 20 | 6.8 | 1.34 |
| C | 30 | 9.9 | 1.33 |
| D | 15 | 3.9 | 1.26 |
| E | 10 | 3.0 | 1.30 |

Which selection maximises NPV?

- **A.** A and D — NPV ₹16.50 lakh  _(error: projects picked in order of absolute NPV)_
- **B.** B and C — NPV ₹16.70 lakh ✅
- **C.** B, D and E — NPV ₹13.70 lakh  _(error: cheapest projects picked first)_
- **D.** A and E — NPV ₹15.60 lakh  _(error: PI ranking applied greedily to indivisible projects, leaving ₹5 lakh idle)_

**Working**

1. With indivisible projects PI ranking can leave funds idle; test feasible combinations.
2. A + E = 45 → 15.6; A + D = 50 → 16.5; B + C = 50 → 16.7; B + D + E = 45 → 13.7; C + D = 45 → 13.8
3. Best feasible combination: B and C — NPV ₹16.70 lakh

**Formula:** Indivisible rationing: maximise total NPV over feasible combinations  
**Trap:** The highest-PI project (A) is not in the optimal set.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-033 · L3 · hard · NPV vs IRR conflict and capital rationing

Two mutually exclusive projects each have a 4-year life. Cost of capital is 12% (PVAF = 3.037).

| Project | Outlay (₹ lakh) | Annual inflow (₹ lakh) |
|---|---:|---:|
| A | 10 | 4.2 |
| B | 25 | 9.3 |

Which project should be chosen, and why?

- **A.** B, since the incremental IRR of about 13.5% exceeds 12% ✅
- **B.** A, since its PI of 1.28 is higher than B's PI of 1.13  _(error: PI ranking used for mutually exclusive projects without a budget limit)_
- **C.** Either, since both have a positive NPV and an IRR above 12%  _(error: treats mutually exclusive projects as independent accept/reject decisions)_
- **D.** A, since its IRR of about 24.5% exceeds B's IRR  _(error: ranks by IRR, ignoring scale)_

**Working**

1. NPV A = 4.2 × 3.037 − 10 = ₹2.755 lakh; NPV B = 9.3 × 3.037 − 25 = ₹3.244 lakh
2. IRR A ≈ 24.5%; IRR B ≈ 18.0% — a scale conflict
3. Incremental (B − A): outlay ₹15 lakh, inflow ₹5.1 lakh → IRR ≈ 13.5% > 12%, so the extra investment adds value → choose B

**Formula:** Incremental IRR > k ⇒ choose larger project (consistent with NPV)  
**Trap:** Mutually exclusive: only one can be taken, so passing the hurdle is not enough.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-034 · L3 · hard · NPV vs IRR conflict and capital rationing

Consider the following statements:

1. For two conventional mutually exclusive projects whose NPV profiles cross, the NPV and IRR rankings conflict only when the cost of capital is below the crossover rate.
2. A project can have more than one IRR when its cash-flow stream changes sign more than once.
3. Under single-period capital rationing with indivisible projects, ranking by profitability index always maximises total NPV.

Which of the statements is/are correct?

- **A.** 1 only  _(error: wrongly rejects statement 2: multiple sign changes can give multiple IRRs (Descartes' rule))_
- **B.** 1 and 2 only ✅
- **C.** 2 only  _(error: wrongly rejects statement 1: above the crossover rate both methods favour the same project)_
- **D.** All of 1, 2 and 3  _(error: wrongly accepts statement 3: indivisibility can leave funds idle, so combinations must be tested)_

**Working**

1. Above the Fisher rate, the project with higher IRR also has higher NPV; below it, rankings flip.
2. Non-conventional flows (e.g. −, +, −) can yield two or more IRRs.
3. PI ranking is exact only for divisible projects; with indivisible projects evaluate feasible combinations.

**Formula:** Conflict zone: k < crossover rate  
**Trap:** Statement 3 is true only for divisible projects.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-035 · L1 · easy · Capital budgeting under risk

Under the certainty-equivalent approach, the certainty-equivalent cash flows of a project are discounted at the:

- **A.** Weighted average cost of capital  _(error: WACC embeds a risk premium)_
- **B.** Risk-free rate of return ✅
- **C.** Project's internal rate of return  _(error: IRR is an output, not a discount rate)_
- **D.** Risk-adjusted discount rate  _(error: double-counts risk)_

**Working**

1. Risk is removed from the numerator by multiplying each cash flow by its CE coefficient (αt ≤ 1).
2. Discounting at a risk-adjusted rate as well would penalise risk twice, so the risk-free rate is used.

**Formula:** NPV = Σ αt CFt ÷ (1 + Rf)^t − I₀  
**Trap:** Adjust risk in either the numerator or the denominator, never both.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-036 · L2 · medium · Capital budgeting under risk

A project costs ₹10 lakh and yields ₹4 lakh a year for 4 years. The risk-free rate is 8%, the firm's WACC is 12%, and management adds a risk premium of 6% over the risk-free rate for projects of this class. PVAF (4 years): 6% = 3.465, 8% = 3.312, 12% = 3.037, 14% = 2.914. The NPV using the risk-adjusted discount rate is:

- **A.** ₹1.656 lakh ✅
- **B.** ₹3.248 lakh  _(error: risk-free rate used; premium ignored)_
- **C.** ₹3.860 lakh  _(error: risk premium alone used as the discount rate)_
- **D.** ₹2.148 lakh  _(error: WACC used instead of the risk-adjusted rate)_

**Working**

1. RADR = 8% + 6% = 14%
2. NPV = 4 × 2.914 − 10 = ₹1.656 lakh

**Formula:** RADR = Rf + Risk premium  
**Trap:** The premium is added to Rf, not to WACC and not used alone.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-037 · L2 · medium · Capital budgeting under risk

A project costs ₹6 lakh.

| Year | 1 | 2 | 3 |
|---|---:|---:|---:|
| Expected cash flow (₹ lakh) | 3 | 3 | 2.5 |
| Certainty-equivalent coefficient | 0.9 | 0.8 | 0.7 |
| PVF at 6% (risk-free) | 0.943 | 0.89 | 0.84 |
| PVF at 11% (WACC) | 0.901 | 0.812 | 0.731 |

The NPV under the certainty-equivalent approach is:

- **A.** ₹15,210 ✅
- **B.** ₹630  _(error: coefficients applied in reverse year order)_
- **C.** −₹33,925  _(error: CE flows discounted at WACC (risk counted twice))_
- **D.** ₹1,59,900  _(error: CE coefficients ignored)_

**Working**

1. CE cash flows = 2.70, 2.40, 1.75 (₹ lakh)
2. PV at 6% = 2.70×0.943 + 2.40×0.890 + 1.75×0.840 = ₹6.1521 lakh
3. NPV = 6.1521 − 6 = ₹15,210

**Formula:** NPV = Σ αt CFt × PVF(Rf, t) − I₀  
**Trap:** Once flows are made certain, discount at the risk-free rate.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-038 · L2 · medium · Capital budgeting under risk

A project costs ₹12 lakh and has a life of 3 years. The annual cash inflow (same in each year) follows this distribution:

| Annual cash inflow (₹ lakh) | Probability |
|---|---:|
| 4 | 0.3 |
| 5 | 0.5 |
| 8 | 0.2 |

At a discount rate of 10% (PVAF = 2.487), the expected NPV is:

- **A.** ₹0.435 lakh  _(error: most likely outcome used instead of the expected value)_
- **B.** ₹2.093 lakh  _(error: simple average of outcomes; probabilities ignored)_
- **C.** ₹1.181 lakh ✅
- **D.** ₹3.900 lakh  _(error: expected inflows not discounted)_

**Working**

1. Expected annual inflow = 4×0.3 + 5×0.5 + 8×0.2 = ₹5.30 lakh
2. ENPV = 5.30 × 2.487 − 12 = ₹1.181 lakh

**Formula:** ENPV = Σ E(CFt) × PVFt − I₀  
**Trap:** Weight by probabilities before discounting.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-039 · L3 · hard · Capital budgeting under risk

Jivika Appliances Ltd: outlay ₹20 lakh; annual sales 10,000 units at ₹500; variable cost ₹300 per unit; fixed cash cost ₹8 lakh a year; life 5 years; cost of capital 10% (PVAF = 3.791); ignore tax. Using sensitivity analysis, which variable is the most sensitive, and by how much can it change adversely before NPV becomes zero?

- **A.** Selling price: a fall of 50.98%  _(error: NPV compared with one year's undiscounted revenue)_
- **B.** Selling price: a fall of 13.45% ✅
- **C.** Sales volume: a fall of 33.62%  _(error: volume sensitivity (less sensitive than price))_
- **D.** Variable cost: a rise of 22.41%  _(error: variable-cost sensitivity (less sensitive than price))_

**Working**

1. Annual CF = 10,000 × 200 − 8 lakh = ₹12 lakh; NPV = 12 × 3.791 − 20 = ₹25.492 lakh
2. Price: NPV ÷ PV of revenue = 25.492 ÷ 189.55 = 13.45%
3. Variable cost: 25.492 ÷ 113.73 = 22.41%; volume: 25.492 ÷ 75.82 = 33.62%
4. Smallest tolerable change → selling price is most sensitive.

**Formula:** Sensitivity = NPV ÷ PV of the cash-flow element affected  
**Trap:** Volume affects contribution, not revenue, so it is less sensitive than price.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-040 · L3 · hard · Capital budgeting under risk

Two projects have the following NPV distributions:

| NPV of X (₹ lakh) | Probability | NPV of Y (₹ lakh) | Probability  |
|---|---:|---:|---:|
| 2 | 0.2 | 4 | 0.3 |
| 5 | 0.5 | 6 | 0.4 |
| 9 | 0.3 | 8 | 0.3 |

The coefficient of variation of project X is closest to (Y's is 0.26):

- **A.** 2.24  _(error: expected NPV divided by standard deviation (inverted))_
- **B.** 1.11  _(error: variance divided by expected NPV)_
- **C.** 0.54  _(error: unweighted mean and standard deviation; probabilities ignored)_
- **D.** 0.45 ✅

**Working**

1. E(NPV X) = 0.4 + 2.5 + 2.7 = ₹5.60 lakh
2. σ = √[0.2(2 − 5.6)² + 0.5(5 − 5.6)² + 0.3(9 − 5.6)²] = √6.24 = 2.498
3. CV = 2.498 ÷ 5.60 = 0.45 — higher than Y's 0.26, so X is riskier per unit of expected NPV

**Formula:** CV = σ ÷ E(NPV)  
**Trap:** Use probability weights for both the mean and the variance.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-041 · L1 · easy · Leverage — operating, financial and combined

Operating leverage of a firm arises because of the presence of:

- **A.** Fixed financial charges such as interest  _(error: that causes financial leverage)_
- **B.** Variable costs that rise in line with sales  _(error: variable costs do not magnify EBIT)_
- **C.** Fixed operating costs in its cost structure ✅
- **D.** Preference dividend payable out of profits  _(error: a fixed financial charge, not operating)_

**Working**

1. Fixed operating costs do not change with output, so a given % change in sales causes a larger % change in EBIT.
2. DOL = Contribution ÷ EBIT; it exceeds 1 only when fixed operating costs exist.

**Formula:** DOL = %ΔEBIT ÷ %ΔSales = C ÷ EBIT  
**Trap:** Interest and preference dividend drive financial, not operating, leverage.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-042 · L2 · medium · Leverage — operating, financial and combined

Extract for Ananta Foods Ltd:

| Particulars | ₹ lakh |
|---|---:|
| Sales | 50 |
| Variable cost | 30 |
| Fixed operating cost | 12 |
| Interest | 3 |

The degree of combined leverage is:

- **A.** 1.56  _(error: DOL divided by DFL)_
- **B.** 6.25  _(error: contribution ÷ EBIT used for DFL as well)_
- **C.** 4.00 ✅
- **D.** 4.10  _(error: DOL and DFL added instead of multiplied)_

**Working**

1. Contribution = 20; EBIT = 8; EBT = 5
2. DOL = 20/8 = 2.50; DFL = 8/5 = 1.60
3. DCL = 2.50 × 1.60 = 4.00 (= Contribution ÷ EBT = 20/5)

**Formula:** DCL = DOL × DFL = C ÷ EBT  
**Trap:** Leverages multiply; they do not add.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-043 · L2 · medium · Leverage — operating, financial and combined

A company has a degree of operating leverage of 2.2 and a degree of financial leverage of 1.5. If sales rise by 12%, EPS will rise by:

- **A.** 18.0%  _(error: only financial leverage applied)_
- **B.** 44.4%  _(error: DOL and DFL added)_
- **C.** 26.4%  _(error: only operating leverage applied)_
- **D.** 39.6% ✅

**Working**

1. DCL = 2.2 × 1.5 = 3.3
2. %ΔEPS = 3.3 × 12% = 39.6%

**Formula:** %ΔEPS = DCL × %ΔSales  
**Trap:** DFL links %ΔEBIT (not %ΔSales) to %ΔEPS.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-044 · L3 · hard · Leverage — operating, financial and combined

Data for Bhavya Plastics Ltd:

| Particulars | Data |
|---|---:|
| Sales | 4 lakh units at ₹20 |
| Variable cost | ₹12 per unit |
| Fixed operating cost | ₹18 lakh |
| 10% debentures | ₹40 lakh |
| Preference dividend | ₹3 lakh |
| Tax rate | 25% |

The degree of financial leverage is:

- **A.** 2.33 ✅
- **B.** 2.00  _(error: preference dividend deducted without grossing up for tax)_
- **C.** 1.40  _(error: preference dividend ignored)_
- **D.** 1.81  _(error: preference dividend multiplied by (1 − t) instead of divided)_

**Working**

1. Contribution = 4 × 8 = ₹32 lakh; EBIT = 32 − 18 = ₹14 lakh
2. Interest = ₹4 lakh; EBT = ₹10 lakh; pre-tax equivalent of preference dividend = 3/0.75 = ₹4 lakh
3. DFL = 14 ÷ (10 − 4) = 2.33

**Formula:** DFL = EBIT ÷ [EBIT − I − Dp/(1 − t)]  
**Trap:** Preference dividend is paid from post-tax profit, so gross it up.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-045 · L3 · hard · Leverage — operating, financial and combined

Kanak Metals Ltd has a degree of operating leverage of 3, a degree of financial leverage of 2, interest of ₹6 lakh and a P/V ratio of 40%. It has no preference capital. Its fixed operating cost is:

- **A.** ₹30 lakh  _(error: interest deducted from contribution instead of EBIT)_
- **B.** ₹54 lakh  _(error: variable cost (sales − contribution) reported)_
- **C.** ₹36 lakh  _(error: contribution reported as fixed cost)_
- **D.** ₹24 lakh ✅

**Working**

1. DFL = EBIT/(EBIT − I) → 2 = EBIT/(EBIT − 6) → EBIT = ₹12 lakh
2. DOL = C/EBIT → C = 3 × 12 = ₹36 lakh; sales = 36/0.40 = ₹90 lakh
3. Fixed cost = C − EBIT = 36 − 12 = ₹24 lakh

**Formula:** EBIT = I × DFL/(DFL − 1); FC = C − EBIT  
**Trap:** Work back from DFL first to find EBIT.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-046 · L1 · easy · EBIT–EPS analysis and financial indifference point

The financial break-even point of a firm with debt and preference capital is the level of EBIT at which:

- **A.** Contribution exactly equals the fixed operating costs of the firm  _(error: that is the operating break-even point)_
- **B.** EPS is identical under two alternative financing plans being compared  _(error: that is the indifference point)_
- **C.** EBIT just covers interest, with preference dividend left out  _(error: omits the grossed-up preference dividend)_
- **D.** EPS is zero — EBIT just covers interest and pre-tax preference dividend ✅

**Working**

1. Financial BEP = I + Dp/(1 − t).
2. At this EBIT, nothing is left for equity holders, so EPS = 0.

**Formula:** Financial BEP = I + Dp ÷ (1 − t)  
**Trap:** Do not confuse with the indifference point or the operating BEP.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-047 · L2 · medium · EBIT–EPS analysis and financial indifference point

A new company needs ₹50 lakh. Plan A: all equity — 5 lakh shares of ₹10. Plan B: 2 lakh shares of ₹10 plus ₹30 lakh of 10% debentures. Tax rate 25%. The EBIT at which EPS is the same under both plans is:

- **A.** ₹8.33 lakh  _(error: 10% interest charged on the entire ₹50 lakh)_
- **B.** ₹3.00 lakh  _(error: financial break-even point of Plan B reported)_
- **C.** ₹6.67 lakh  _(error: interest grossed up for tax as if it were preference dividend)_
- **D.** ₹5.00 lakh ✅

**Working**

1. EBIT(1 − t)/5 = (EBIT − 3)(1 − t)/2
2. 2 EBIT = 5 EBIT − 15 → EBIT = ₹5 lakh
3. Check: EPS = 5 × 0.75/5 = ₹0.75 under both plans

**Formula:** (EBIT − I₁)(1 − t)/N₁ = (EBIT − I₂)(1 − t)/N₂  
**Trap:** Interest is deducted pre-tax; it is not grossed up.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-048 · L2 · medium · EBIT–EPS analysis and financial indifference point

Under a proposed plan, Lakshya Retail Ltd will have 5 lakh equity shares and ₹30 lakh of 12% preference shares, and no debt. Expected EBIT is ₹12 lakh and the tax rate is 25%. EPS under this plan is:

- **A.** ₹0.84  _(error: preference dividend grossed up and deducted from profit after tax)_
- **B.** ₹1.80  _(error: preference dividend ignored)_
- **C.** ₹1.08 ✅
- **D.** ₹1.26  _(error: preference dividend deducted before tax as if it were interest)_

**Working**

1. PAT = 12 × 0.75 = ₹9.00 lakh
2. Less preference dividend ₹3.60 lakh → ₹5.40 lakh
3. EPS = 5.40 ÷ 5 = ₹1.08

**Formula:** EPS = [(EBIT − I)(1 − t) − Dp] ÷ N  
**Trap:** Preference dividend comes out of PAT, at face amount.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-049 · L3 · hard · EBIT–EPS analysis and financial indifference point

Charvi Textiles Ltd has 4 lakh equity shares and ₹15 lakh of 10% debentures. It needs ₹20 lakh more and is choosing between (i) issuing 2 lakh equity shares at ₹10, and (ii) issuing ₹20 lakh of 12% preference shares. Tax rate 30%. The EBIT at which EPS is the same under both options is:

- **A.** ₹10.29 lakh  _(error: existing debenture interest ignored)_
- **B.** ₹11.79 lakh ✅
- **C.** ₹4.93 lakh  _(error: financial break-even point of the preference option reported)_
- **D.** ₹8.70 lakh  _(error: preference dividend deducted before tax like interest)_

**Working**

1. Equity option: N = 6 lakh; preference option: N = 4 lakh, Dp = ₹2.4 lakh; interest ₹1.5 lakh in both
2. (EBIT − 1.5)(0.7)/6 = [(EBIT − 1.5)(0.7) − 2.4]/4
3. 0.7(EBIT − 1.5) × (1/4 − 1/6) = 0.6 → EBIT − 1.5 = 10.2857 → EBIT = ₹11.79 lakh

**Formula:** (EBIT − I)(1 − t)/N₁ = [(EBIT − I)(1 − t) − Dp]/N₂  
**Trap:** Existing interest appears in both plans and shifts the point.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-050 · L3 · hard · EBIT–EPS analysis and financial indifference point

Suvidha Logistics Ltd, a new company, will raise ₹60 lakh under one of these plans:

| Plan | Equity (₹10 shares) | Debt | Preference |
|---|---:|---:|---:|
| A | ₹60 lakh | — | — |
| B | ₹30 lakh | ₹30 lakh at 12% | — |
| C | ₹30 lakh | — | ₹30 lakh at 11% |

Expected EBIT is ₹20 lakh; tax rate 25%. Which plan ranks second on EPS, and what is that plan's financial break-even point?

- **A.** Plan C; ₹3.30 lakh  _(error: preference dividend not grossed up for tax)_
- **B.** Plan C; ₹4.40 lakh ✅
- **C.** Plan B; ₹3.60 lakh  _(error: top-ranked plan and its break-even reported)_
- **D.** Plan C; ₹2.47 lakh  _(error: preference dividend multiplied by (1 − t))_

**Working**

1. EPS: A = ₹2.50; B = ₹4.10; C = ₹3.90
2. Ranking: B > C > A → second is Plan C
3. Financial BEP (Plan C) = 3.3/0.75 = ₹4.40 lakh

**Formula:** Financial BEP = I + Dp/(1 − t)  
**Trap:** Preference dividend must be grossed up to a pre-tax EBIT equivalent.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-051 · L1 · easy · Capital structure theories — NI, NOI, traditional and MM

Under the Net Operating Income (NOI) approach, as a firm substitutes debt for equity, which of the following remains constant?

- **A.** The cost of equity (Ke) and the market price per share  _(error: Ke rises; only V and Ko are constant)_
- **B.** The equity capitalisation rate and the overall cost of capital  _(error: Ke is not constant under NOI)_
- **C.** The cost of equity (Ke) and the value of equity  _(error: Ke rises with leverage under NOI)_
- **D.** The overall cost of capital (Ko) and the value of the firm ✅

**Working**

1. NOI: V = EBIT ÷ Ko with Ko constant, so V is independent of leverage.
2. Cheaper debt is exactly offset by a rising Ke, so capital structure is irrelevant.

**Formula:** V = EBIT ÷ Ko;  Ke = Ko + (Ko − Kd)D/E  
**Trap:** Under the NI approach, by contrast, Ke and Kd are constant and Ko falls.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-052 · L2 · medium · Capital structure theories — NI, NOI, traditional and MM

Rishabh Engineering Ltd has EBIT of ₹10 lakh and ₹30 lakh of 10% debt. Its equity capitalisation rate is 15%. Under the Net Income approach (no taxes), its overall cost of capital is:

- **A.** 13.04% ✅
- **B.** 10.34%  _(error: value of equity computed by capitalising EBIT instead of net income)_
- **C.** 12.50%  _(error: simple average of Ke and Kd)_
- **D.** 15%  _(error: equity capitalisation rate reported as Ko)_

**Working**

1. Net income = 10 − 3 = ₹7 lakh; E = 7/0.15 = ₹46.67 lakh
2. V = 46.67 + 30 = ₹76.67 lakh
3. Ko = 10 ÷ 76.67 = 13.04%

**Formula:** E = (EBIT − I)/Ke;  Ko = EBIT/V  
**Trap:** Equity holders capitalise net income, not EBIT.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-053 · L3 · hard · Capital structure theories — NI, NOI, traditional and MM

Firms U and L are identical except that L has ₹40 lakh of 8% debt; U is all-equity. Both earn EBIT of ₹12 lakh and U's cost of equity is 12%. Assuming Modigliani–Miller conditions without taxes, L's cost of equity is:

- **A.** 8.80%  _(error: net income divided by total firm value)_
- **B.** 12%  _(error: cost of equity assumed unchanged by leverage)_
- **C.** 13.60%  _(error: debt ÷ total value used instead of debt ÷ equity)_
- **D.** 14.67% ✅

**Working**

1. MM (no tax): VL = VU = 12/0.12 = ₹100 lakh; EL = 100 − 40 = ₹60 lakh
2. KeL = Ku + (Ku − Kd) × D/E = 12% + 4% × 40/60 = 14.67%
3. Check: (EBIT − I)/E = 8.8/60 = 14.67%

**Formula:** KeL = Ku + (Ku − Kd)(D/E)  
**Trap:** The risk premium scales with D/E, not D/V.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-054 · L3 · hard · Capital structure theories — NI, NOI, traditional and MM

Two firms are identical in every respect except capital structure (ignore taxes):

| Particulars | Firm U | Firm L |
|---|---:|---:|
| EBIT (₹ lakh) | 20 | 20 |
| 10% debt (₹ lakh) | — | 50 |
| Equity capitalisation rate | 12.5% | 12% |

An investor owns 10% of L's equity. Under MM arbitrage, he sells his L shares, borrows personally at 10% in proportion to his share of L's debt, and invests the entire amount in U's shares. The increase in his annual income is:

- **A.** ₹1,50,000  _(error: cash saved by buying the same 10% of U reported as income)_
- **B.** ₹18,750 ✅
- **C.** ₹68,750  _(error: interest on the personal borrowing not deducted)_
- **D.** ₹6,250  _(error: no personal borrowing (homemade leverage) undertaken)_

**Working**

1. VU = 20/0.125 = ₹160 lakh; EL = (20 − 5)/0.12 = ₹125 lakh; VL = ₹175 lakh → L is overvalued
2. Sell 10% of L = ₹12.50 lakh (income ₹1.50 lakh); borrow ₹5 lakh; invest ₹17.50 lakh in U
3. New income = 17.50/160 × 20 − 5 × 10% = ₹1.6875 lakh
4. Gain = 1.6875 − 1.50 = ₹0.1875 lakh = ₹18,750

**Formula:** Arbitrage: replicate L's financial risk with personal leverage in U  
**Trap:** Personal borrowing is what keeps the financial risk identical.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-055 · L1 · easy · Dividend policy models — Walter, Gordon and MM

Under Walter's model, for a growth firm whose return on investment (r) exceeds its cost of equity (k), the optimum dividend payout ratio is:

- **A.** 100% — all earnings should be distributed  _(error: optimal for a declining firm (r < k))_
- **B.** Irrelevant — every payout gives the same price  _(error: true only for a normal firm (r = k))_
- **C.** Zero — all earnings should be retained ✅
- **D.** Equal to the ratio of k to r for the firm  _(error: no such rule in Walter's model)_

**Working**

1. Walter: P = [D + (r/k)(E − D)] ÷ k.
2. When r > k, each rupee retained adds more than a rupee to price, so price is maximised at D = 0.

**Formula:** P = [D + (r/k)(E − D)] ÷ k  
**Trap:** Match the payout rule to the firm type: growth (0%), normal (irrelevant), declining (100%).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-056 · L4 · hard · Capital budgeting — NPV, IRR, PI and MIRR

**Case — Ashvik Components Ltd.** The company is appraising a new precision-parts line. Data:

| Item | Data |
|---|---:|
| Machine cost / installation | ₹48 lakh / ₹2 lakh (installation is capitalised) |
| Life; depreciation | 5 years; straight-line on capitalised cost less estimated salvage of ₹5 lakh |
| Actual sale value at end of year 5 | ₹8 lakh; profit over book value taxed at 25% |
| Working capital | ₹6 lakh at start, fully released at end of year 5 |
| Selling price / variable cost | ₹400 / ₹250 per unit |
| Incremental fixed cash cost | ₹12 lakh a year |
| Tax rate; cost of capital | 25%; 12% |

| Year | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|
| Units sold | 20,000 | 24,000 | 28,000 | 28,000 | 22,000 |
| PVF at 12% | 0.893 | 0.797 | 0.712 | 0.636 | 0.567 |

The cash flow after tax from operations in year 2 is:

- **A.** ₹11.25 lakh  _(error: profit after tax; depreciation not added back)_
- **B.** ₹18.00 lakh  _(error: tax charged on EBDT; depreciation tax shield ignored)_
- **C.** ₹20.15 lakh  _(error: installation cost left out of the depreciable base)_
- **D.** ₹20.25 lakh ✅

**Working**

1. Depreciation = (48 + 2 − 5) ÷ 5 = ₹9 lakh
2. Year 2: contribution = 24,000 × ₹150 = ₹36 lakh; EBDT = 36 − 12 = ₹24 lakh
3. CFAT = (24 − 9) × 0.75 + 9 = ₹20.25 lakh

**Formula:** CFAT = (EBDT − Dep)(1 − t) + Dep  
**Trap:** Installation is capitalised and depreciated.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-057 · L4 · hard · Capital budgeting — NPV, IRR, PI and MIRR

**Case — Ashvik Components Ltd.** The company is appraising a new precision-parts line. Data:

| Item | Data |
|---|---:|
| Machine cost / installation | ₹48 lakh / ₹2 lakh (installation is capitalised) |
| Life; depreciation | 5 years; straight-line on capitalised cost less estimated salvage of ₹5 lakh |
| Actual sale value at end of year 5 | ₹8 lakh; profit over book value taxed at 25% |
| Working capital | ₹6 lakh at start, fully released at end of year 5 |
| Selling price / variable cost | ₹400 / ₹250 per unit |
| Incremental fixed cash cost | ₹12 lakh a year |
| Tax rate; cost of capital | 25%; 12% |

| Year | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|
| Units sold | 20,000 | 24,000 | 28,000 | 28,000 | 22,000 |
| PVF at 12% | 0.893 | 0.797 | 0.712 | 0.636 | 0.567 |

The terminal (non-operating) cash inflow at the end of year 5 is:

- **A.** ₹13.25 lakh ✅
- **B.** ₹14.00 lakh  _(error: tax on profit on sale ignored)_
- **C.** ₹12.00 lakh  _(error: tax charged on the entire sale value instead of the profit over book value)_
- **D.** ₹7.25 lakh  _(error: release of working capital omitted)_

**Working**

1. Book value at end = estimated salvage = ₹5 lakh; profit on sale = 8 − 5 = ₹3 lakh
2. Tax = 25% × 3 = ₹0.75 lakh → net salvage = ₹7.25 lakh
3. Terminal inflow = 7.25 + WC 6 = ₹13.25 lakh

**Formula:** Terminal CF = Sale value − t(Sale value − BV) + WC  
**Trap:** Only the gain over book value is taxed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-058 · L4 · hard · Capital budgeting — NPV, IRR, PI and MIRR

**Case — Ashvik Components Ltd.** The company is appraising a new precision-parts line. Data:

| Item | Data |
|---|---:|
| Machine cost / installation | ₹48 lakh / ₹2 lakh (installation is capitalised) |
| Life; depreciation | 5 years; straight-line on capitalised cost less estimated salvage of ₹5 lakh |
| Actual sale value at end of year 5 | ₹8 lakh; profit over book value taxed at 25% |
| Working capital | ₹6 lakh at start, fully released at end of year 5 |
| Selling price / variable cost | ₹400 / ₹250 per unit |
| Incremental fixed cash cost | ₹12 lakh a year |
| Tax rate; cost of capital | 25%; 12% |

| Year | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|
| Units sold | 20,000 | 24,000 | 28,000 | 28,000 | 22,000 |
| PVF at 12% | 0.893 | 0.797 | 0.712 | 0.636 | 0.567 |

The NPV of the project is:

- **A.** ₹27.88 lakh  _(error: working capital ignored at both ends)_
- **B.** ₹26.93 lakh  _(error: installation cost ignored in both the outlay and the depreciable base)_
- **C.** ₹25.29 lakh ✅
- **D.** ₹17.77 lakh  _(error: terminal inflow (net salvage + working capital) omitted)_

**Working**

1. CFAT (₹ lakh): 15.75, 20.25, 24.75, 24.75, 18.00; add terminal ₹13.25 lakh in year 5
2. PV of inflows = 15.75×0.893 + 20.25×0.797 + 24.75×0.712 + 24.75×0.636 + 31.25×0.567 = ₹81.286 lakh
3. Outlay = 50 + 6 = ₹56 lakh; NPV = ₹25.286 lakh

**Formula:** NPV = Σ CFt × PVFt − (Capital cost + WC)  
**Trap:** The outlay includes installation and working capital.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-059 · L4 · hard · Capital budgeting — payback and discounted payback

**Case — Ashvik Components Ltd.** The company is appraising a new precision-parts line. Data:

| Item | Data |
|---|---:|
| Machine cost / installation | ₹48 lakh / ₹2 lakh (installation is capitalised) |
| Life; depreciation | 5 years; straight-line on capitalised cost less estimated salvage of ₹5 lakh |
| Actual sale value at end of year 5 | ₹8 lakh; profit over book value taxed at 25% |
| Working capital | ₹6 lakh at start, fully released at end of year 5 |
| Selling price / variable cost | ₹400 / ₹250 per unit |
| Incremental fixed cash cost | ₹12 lakh a year |
| Tax rate; cost of capital | 25%; 12% |

| Year | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|
| Units sold | 20,000 | 24,000 | 28,000 | 28,000 | 22,000 |
| PVF at 12% | 0.893 | 0.797 | 0.712 | 0.636 | 0.567 |

The discounted payback period of the project is:

- **A.** 3.52 years ✅
- **B.** 2.81 years  _(error: simple (undiscounted) payback)_
- **C.** 3.14 years  _(error: working capital excluded from the amount to be recovered)_
- **D.** 3.33 years  _(error: final fraction computed on the undiscounted year-4 cash flow)_

**Working**

1. Discounted inflows (₹ lakh): 14.065, 16.139, 17.622, 15.741, 17.719
2. Cumulative after 3 years = ₹47.826 lakh; balance = 56 − 47.826 = ₹8.174 lakh
3. DPB = 3 + 8.174/15.741 = 3.52 years

**Formula:** DPB = Years before recovery + Unrecovered PV ÷ PV of next year's inflow  
**Trap:** Working capital is part of the investment to be recovered.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-060 · L4 · hard · Leverage — operating, financial and combined

**Case — Kavera Foods Ltd.** Present capital: 20 lakh equity shares of ₹10 each, reserves ₹50 lakh and ₹100 lakh of 10% debentures. An expansion costing ₹150 lakh is planned. After expansion: sales ₹400 lakh, variable cost 60% of sales, fixed operating cost ₹70 lakh. Two financing plans are considered:

| Plan | Instrument |
|---|---:|
| A | Equity shares issued at ₹25 (6 lakh shares); flotation cost ₹1 per share |
| B | 12% debentures of ₹150 lakh |

Tax rate 25%. The dividend just paid is ₹2.00 per share, expected to grow at 7% a year; the current share price is ₹25.

The degree of combined leverage after expansion under Plan B is:

- **A.** 2.58 ✅
- **B.** 2.00  _(error: Plan A's combined leverage (only existing interest))_
- **C.** 2.22  _(error: only the new debenture interest deducted)_
- **D.** 3.23  _(error: DOL and DFL added instead of multiplied)_

**Working**

1. Contribution = 400 × 40% = ₹160 lakh; EBIT = 160 − 70 = ₹90 lakh
2. Interest under Plan B = 10 + 18 = ₹28 lakh; EBT = ₹62 lakh
3. DCL = 160 ÷ 62 = 2.58 (DOL 1.78 × DFL 1.45)

**Formula:** DCL = Contribution ÷ EBT  
**Trap:** Existing debenture interest continues under both plans.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-061 · L4 · hard · EBIT–EPS analysis and financial indifference point

**Case — Kavera Foods Ltd.** Present capital: 20 lakh equity shares of ₹10 each, reserves ₹50 lakh and ₹100 lakh of 10% debentures. An expansion costing ₹150 lakh is planned. After expansion: sales ₹400 lakh, variable cost 60% of sales, fixed operating cost ₹70 lakh. Two financing plans are considered:

| Plan | Instrument |
|---|---:|
| A | Equity shares issued at ₹25 (6 lakh shares); flotation cost ₹1 per share |
| B | 12% debentures of ₹150 lakh |

Tax rate 25%. The dividend just paid is ₹2.00 per share, expected to grow at 7% a year; the current share price is ₹25.

The EBIT at which EPS is the same under Plans A and B is:

- **A.** ₹44.67 lakh  _(error: existing interest deducted only under Plan A)_
- **B.** ₹88.00 lakh ✅
- **C.** ₹78.00 lakh  _(error: existing debenture interest ignored in both plans)_
- **D.** ₹52.00 lakh  _(error: new shares assumed issued at par (15 lakh shares))_

**Working**

1. Plan A: N = 26 lakh, I = ₹10 lakh; Plan B: N = 20 lakh, I = ₹28 lakh
2. (EBIT − 10)(0.75)/26 = (EBIT − 28)(0.75)/20
3. 20·EBIT − 200 = 26·EBIT − 728 → EBIT = ₹88 lakh

**Formula:** (EBIT − I_A)/N_A = (EBIT − I_B)/N_B  
**Trap:** Expected EBIT (₹90 lakh) is just above the point, so Plan B gives the higher EPS.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-062 · L4 · hard · Cost of capital — debt, preference and equity

**Case — Kavera Foods Ltd.** Present capital: 20 lakh equity shares of ₹10 each, reserves ₹50 lakh and ₹100 lakh of 10% debentures. An expansion costing ₹150 lakh is planned. After expansion: sales ₹400 lakh, variable cost 60% of sales, fixed operating cost ₹70 lakh. Two financing plans are considered:

| Plan | Instrument |
|---|---:|
| A | Equity shares issued at ₹25 (6 lakh shares); flotation cost ₹1 per share |
| B | 12% debentures of ₹150 lakh |

Tax rate 25%. The dividend just paid is ₹2.00 per share, expected to grow at 7% a year; the current share price is ₹25.

The cost of the new equity under Plan A is:

- **A.** 15.23%  _(error: flotation cost added to the price instead of deducted)_
- **B.** 15.56%  _(error: flotation cost ignored)_
- **C.** 15.33%  _(error: D0 used instead of D1)_
- **D.** 15.92% ✅

**Working**

1. D1 = 2.00 × 1.07 = ₹2.14; net proceeds = 25 − 1 = ₹24
2. Ke = 2.14/24 + 7% = 15.92%

**Formula:** Ke(new) = D1 ÷ (P0 − f) + g  
**Trap:** Flotation cost reduces the net proceeds per share.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-063 · L4 · hard · Weighted average and marginal cost of capital

**Case — Kavera Foods Ltd.** Present capital: 20 lakh equity shares of ₹10 each, reserves ₹50 lakh and ₹100 lakh of 10% debentures. An expansion costing ₹150 lakh is planned. After expansion: sales ₹400 lakh, variable cost 60% of sales, fixed operating cost ₹70 lakh. Two financing plans are considered:

| Plan | Instrument |
|---|---:|
| A | Equity shares issued at ₹25 (6 lakh shares); flotation cost ₹1 per share |
| B | 12% debentures of ₹150 lakh |

Tax rate 25%. The dividend just paid is ₹2.00 per share, expected to grow at 7% a year; the current share price is ₹25.

If Plan B is adopted, the cost of equity is expected to rise to 16.5%. Using book-value weights, the WACC after expansion is:

- **A.** 11.98%  _(error: pre-expansion cost of equity (from the dividend-growth model) used)_
- **B.** 13.85%  _(error: pre-tax cost of debentures used)_
- **C.** 12.75%  _(error: all debentures costed at the new 12% coupon)_
- **D.** 12.45% ✅

**Working**

1. Equity (capital + reserves) = ₹250 lakh at 16.5%; old debentures ₹100 lakh at 10% × 0.75 = 7.5%; new ₹150 lakh at 12% × 0.75 = 9%
2. WACC = (250 × 16.5% + 100 × 7.5% + 150 × 9%) ÷ 500 = 12.45%

**Formula:** WACC = Σ (BVᵢ × post-tax kᵢ) ÷ Σ BVᵢ  
**Trap:** Each debt tranche keeps its own coupon.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-064 · L4 · hard · Dividend policy models — Walter, Gordon and MM

**Case — Meridian Tools Ltd.** EPS ₹12; return on investment 18%; cost of equity 14%; 5 lakh equity shares; present payout ratio 40%; current market price ₹100. The company plans capital investment of ₹90 lakh next year and expects net income of ₹60 lakh.

Under Walter's model, the price per share at the present payout ratio is:

- **A.** ₹85.71  _(error: EPS ÷ k — treats payout as irrelevant)_
- **B.** ₹74.29  _(error: r and k interchanged in the retention term)_
- **C.** ₹100.41 ✅
- **D.** ₹78.10  _(error: capitalised at r instead of k)_

**Working**

1. D = 12 × 0.4 = ₹4.80; retained = ₹7.20
2. P = [4.80 + (0.18/0.14) × 7.20] ÷ 0.14 = ₹100.41

**Formula:** P = [D + (r/k)(E − D)] ÷ k  
**Trap:** r/k multiplies the retained part only.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-065 · L4 · hard · Dividend policy models — Walter, Gordon and MM

**Case — Meridian Tools Ltd.** EPS ₹12; return on investment 18%; cost of equity 14%; 5 lakh equity shares; present payout ratio 40%; current market price ₹100. The company plans capital investment of ₹90 lakh next year and expects net income of ₹60 lakh.

Under Walter's model, the optimum payout ratio and the corresponding price per share are:

- **A.** 40%; ₹100.41  _(error: present payout assumed optimal)_
- **B.** 0%; ₹110.20 ✅
- **C.** 100%; ₹85.71  _(error: declining-firm rule applied although r > k)_
- **D.** 0%; ₹85.71  _(error: correct payout but price computed as EPS ÷ k)_

**Working**

1. r (18%) > k (14%) → growth firm → retain everything
2. P = [0 + (0.18/0.14) × 12] ÷ 0.14 = ₹110.20

**Formula:** Walter: r > k ⇒ D/P = 0  
**Trap:** Price rises steadily as payout falls when r > k.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-066 · L4 · hard · Dividend policy models — Walter, Gordon and MM

**Case — Meridian Tools Ltd.** EPS ₹12; return on investment 18%; cost of equity 14%; 5 lakh equity shares; present payout ratio 40%; current market price ₹100. The company plans capital investment of ₹90 lakh next year and expects net income of ₹60 lakh.

Treating ₹12 as next year's EPS, the price per share under Gordon's model at the present payout ratio is:

- **A.** ₹166.20  _(error: dividend grown once more although EPS is already next year's)_
- **B.** ₹150.00 ✅
- **C.** ₹85.71  _(error: growth computed as retention × k instead of retention × r)_
- **D.** ₹70.59  _(error: growth computed as payout × r instead of retention × r)_

**Working**

1. b = 0.6; g = b × r = 0.6 × 18% = 10.8%
2. P = E(1 − b) ÷ (k − br) = 4.80 ÷ (14% − 10.8%) = ₹150.00

**Formula:** P = E₁(1 − b) ÷ (k − br)  
**Trap:** g must be below k; here the spread is only 3.2%.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-067 · L4 · hard · Dividend policy models — Walter, Gordon and MM

**Case — Meridian Tools Ltd.** EPS ₹12; return on investment 18%; cost of equity 14%; 5 lakh equity shares; present payout ratio 40%; current market price ₹100. The company plans capital investment of ₹90 lakh next year and expects net income of ₹60 lakh.

The company decides to pay a dividend of ₹4.80 per share at the end of the year. Under the Modigliani–Miller model, the number of new shares it must issue at year-end to finance the investment is closest to:

- **A.** 49,451 shares ✅
- **B.** 54,000 shares  _(error: new shares priced at the current price instead of P₁)_
- **C.** 26,316 shares  _(error: no-dividend case (P₁ = ₹114, only ₹30 lakh to raise))_
- **D.** 82,418 shares  _(error: entire investment treated as externally financed)_

**Working**

1. P₁ = P₀(1 + k) − D₁ = 100 × 1.14 − 4.80 = ₹109.20
2. Retained earnings = 60 − 4.80 × 5 = ₹36 lakh; funds to raise = 90 − 36 = ₹54 lakh
3. New shares = 54 lakh ÷ 109.20 = 49,451 shares

**Formula:** P₁ = P₀(1 + ke) − D₁;  m = (I − (E − nD₁)) ÷ P₁  
**Trap:** The ex-dividend price P₁, not P₀, is the issue price.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-068 · L4 · hard · Capital structure theories — NI, NOI, traditional and MM

**Case — Rudra Logistics Ltd** is all-equity financed. EBIT is ₹30 lakh a year in perpetuity, all earnings are distributed, and its cost of equity is 15% (unlevered beta 1.0; risk-free rate 7%; expected market return 15%). The corporate tax rate is 25%. It plans to issue ₹60 lakh of perpetual debt at the risk-free rate of 7% and use the proceeds to buy back shares. Assume Modigliani–Miller (1963) conditions with corporate taxes.

The value of the firm after the recapitalisation is:

- **A.** ₹200 lakh  _(error: taxes ignored (MM without taxes))_
- **B.** ₹165 lakh ✅
- **C.** ₹210 lakh  _(error: full amount of debt added instead of the tax shield t × D)_
- **D.** ₹150 lakh  _(error: tax shield on debt ignored)_

**Working**

1. VU = 30 × (1 − 0.25) ÷ 0.15 = ₹150 lakh
2. VL = VU + tD = 150 + 0.25 × 60 = ₹165 lakh

**Formula:** VL = VU + tD  
**Trap:** Only the present value of the interest tax shield is added.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-069 · L4 · hard · Capital structure theories — NI, NOI, traditional and MM

**Case — Rudra Logistics Ltd** is all-equity financed. EBIT is ₹30 lakh a year in perpetuity, all earnings are distributed, and its cost of equity is 15% (unlevered beta 1.0; risk-free rate 7%; expected market return 15%). The corporate tax rate is 25%. It plans to issue ₹60 lakh of perpetual debt at the risk-free rate of 7% and use the proceeds to buy back shares. Assume Modigliani–Miller (1963) conditions with corporate taxes.

The cost of equity after the recapitalisation is:

- **A.** 17.18%  _(error: debt ÷ firm value used instead of debt ÷ equity)_
- **B.** 19%  _(error: equity taken as VU − D, ignoring the tax-shield gain)_
- **C.** 18.43% ✅
- **D.** 19.57%  _(error: (1 − t) factor omitted — MM no-tax formula)_

**Working**

1. E = VL − D = 165 − 60 = ₹105 lakh
2. KeL = 15% + (15% − 7%) × 0.75 × 60/105 = 18.43%
3. Check: net income = (30 − 4.2) × 0.75 = ₹19.35 lakh; ÷ 105 = 18.43%

**Formula:** KeL = Ku + (Ku − Kd)(1 − t)(D/E)  
**Trap:** Equity is VL − D, which already includes the tax shield.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-070 · L4 · hard · CAPM, beta and the security market line

**Case — Rudra Logistics Ltd** is all-equity financed. EBIT is ₹30 lakh a year in perpetuity, all earnings are distributed, and its cost of equity is 15% (unlevered beta 1.0; risk-free rate 7%; expected market return 15%). The corporate tax rate is 25%. It plans to issue ₹60 lakh of perpetual debt at the risk-free rate of 7% and use the proceeds to buy back shares. Assume Modigliani–Miller (1963) conditions with corporate taxes.

The equity beta after recapitalisation, consistent with CAPM and the cost of equity found above, is:

- **A.** 1.27  _(error: debt ÷ firm value used instead of debt ÷ equity)_
- **B.** 1.57  _(error: (1 − t) omitted in relevering)_
- **C.** 1.00  _(error: beta assumed unchanged by financial leverage)_
- **D.** 1.43 ✅

**Working**

1. βL = βU[1 + (1 − t)D/E] = 1.0 × [1 + 0.75 × 60/105] = 1.43
2. CAPM check: 7% + 1.4286 × 8% = 18.43% = KeL

**Formula:** βL = βU[1 + (1 − t)D/E]  
**Trap:** With risk-free debt, Hamada's relevering matches MM's cost of equity.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-071 · L1 · easy · Income-tax — assessment and rectification ⚠

Under the Income-tax Act, 2025, which concept replaces the twin concepts of 'previous year' and 'assessment year' used under the Income-tax Act, 1961?

- **A.** 'Assessment year' alone, with the income of that same year taxed in it  _(error: retains the old term instead of the new 'tax year')_
- **B.** An 'accounting year' that follows each assessee's own books of account  _(error: invents an assessee-specific year)_
- **C.** 'Financial year' replaces 'previous year'; 'assessment year' continues  _(error: assumes only one of the two terms is renamed)_
- **D.** A single 'tax year', the year in which the income is earned ✅

**Working**

1. The 1961 Act taxed income of the previous year in the following assessment year.
2. The 2025 Act, in force from 1 April 2026, uses a single 'tax year' — the income and the year of reference are the same.

**Formula:** Old: PY → AY (next year);  New: tax year = year of earning  
**Trap:** The new Act does not keep 'assessment year' as the reference label.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-072 · L2 · medium · Income-tax — assessment and rectification ⚠

Under the Income-tax Act, 2025, how are the following two periods of Ms Anika's salary income correctly labelled? (i) 1 April 2024 – 31 March 2025, assessed under the Income-tax Act, 1961; (ii) 1 April 2026 – 31 March 2027, taxed under the Income-tax Act, 2025.

- **A.** (i) Assessment year 2025-26; (ii) tax year 2026-27 ✅
- **B.** (i) Assessment year 2025-26; (ii) tax year 2027-28  _(error: AY-style one-year lag carried into the new 'tax year')_
- **C.** (i) Assessment year 2024-25; (ii) tax year 2026-27  _(error: old-Act income labelled by the year of earning rather than the following AY)_
- **D.** (i) Previous year 2025-26; (ii) tax year 2027-28  _(error: both periods shifted forward by a year)_

**Working**

1. Under the 1961 Act, income of PY 2024-25 (FY 2024-25) is assessed in AY 2025-26.
2. Under the 2025 Act, income earned in FY 2026-27 is income of tax year 2026-27 — no lag.

**Formula:** FY of earning = tax year (2025 Act);  AY = FY + 1 (1961 Act)  
**Trap:** The one-year lag disappears under the new Act.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-073 · L1 · easy · Direct vs indirect taxes ⚠

Under the Income-tax Act, 2025, consider the following statements:

1. Income tax under the new Act remains a direct tax, as its impact and incidence fall on the same person.
2. The Goods and Services Tax has been merged into the Income-tax Act, 2025 as part of the simplification.
3. The Income-tax Act, 2025 replaces the Income-tax Act, 1961 with effect from 1 April 2026.

Which of the statements is/are correct?

- **A.** 1 and 3 only ✅
- **B.** 3 only  _(error: wrongly rejects statement 1: income tax is not shifted to another person)_
- **C.** All of 1, 2 and 3  _(error: wrongly accepts statement 2: GST is a separate indirect tax under the GST laws)_
- **D.** 1 only  _(error: wrongly rejects statement 3: the new Act applies from 1 April 2026)_

**Working**

1. Income tax is a direct tax: the person on whom it is imposed bears it.
2. GST remains a separate indirect tax levied under the CGST/SGST/IGST laws; the 2025 Act deals only with income tax.
3. The 2025 Act replaced the 1961 Act from 1 April 2026.

**Formula:** Direct tax: impact = incidence  
**Trap:** Simplification of the income-tax law did not absorb indirect taxes.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-074 · L2 · medium · Income-tax — assessment and rectification ⚠

Under the Income-tax Act, 2025, compute the tax payable for tax year 2026-27 by Mr Devansh, a resident individual under the new regime whose only income is a salary of ₹18,50,000. Assume the following new-regime slabs apply for tax year 2026-27:

| Total income (₹) | Rate |
|---|---:|
| Up to 4,00,000 | Nil |
| 4,00,001 – 8,00,000 | 5% |
| 8,00,001 – 12,00,000 | 10% |
| 12,00,001 – 16,00,000 | 15% |
| 16,00,001 – 20,00,000 | 20% |
| 20,00,001 – 24,00,000 | 25% |
| Above 24,00,000 | 30% |

Assume also: standard deduction from salary ₹75,000; rebate equal to the tax (maximum ₹60,000) where total income does not exceed ₹12,00,000; health and education cess 4% on tax.

- **A.** ₹98,800  _(error: rebate allowed although total income exceeds ₹12,00,000)_
- **B.** ₹1,76,800  _(error: standard deduction not allowed)_
- **C.** ₹1,61,200 ✅
- **D.** ₹1,55,000  _(error: cess omitted)_

**Working**

1. Total income = 18,50,000 − 75,000 = 17,75,000
2. Tax: 4–8 L @5% = 20,000; 8–12 L @10% = 40,000; 12–16 L @15% = 60,000; 16–17.75 L @20% = 35,000 → 1,55,000
3. No rebate (income > 12 L); cess 4% = 6,200 → ₹1,61,200

**Formula:** Tax = Σ slab tax on (Salary − Std deduction) + 4% cess  
**Trap:** Slab rates apply to each band, not to the whole income.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## FINC-075 · L3 · hard · Income-tax — assessment and rectification ⚠

Under the Income-tax Act, 2025, two resident salaried individuals opt for the new regime for tax year 2026-27: Ms Esha (salary ₹12,60,000) and Mr Farhan (salary ₹12,90,000), with no other income. Assume the following new-regime slabs apply for tax year 2026-27:

| Total income (₹) | Rate |
|---|---:|
| Up to 4,00,000 | Nil |
| 4,00,001 – 8,00,000 | 5% |
| 8,00,001 – 12,00,000 | 10% |
| 12,00,001 – 16,00,000 | 15% |
| 16,00,001 – 20,00,000 | 20% |
| 20,00,001 – 24,00,000 | 25% |
| Above 24,00,000 | 30% |

Assume also: standard deduction from salary ₹75,000; rebate equal to the tax (maximum ₹60,000) where total income does not exceed ₹12,00,000; health and education cess 4% on tax. Where total income exceeds ₹12,00,000, marginal relief limits the tax (before cess) to the amount by which total income exceeds ₹12,00,000.

Their tax liabilities respectively are:

- **A.** Nil and ₹2,340  _(error: rebate also given to Farhan although his total income exceeds ₹12,00,000)_
- **B.** Nil and ₹64,740  _(error: marginal relief ignored — full slab tax charged on income just above ₹12,00,000)_
- **C.** Nil and ₹15,600 ✅
- **D.** Nil and ₹15,000  _(error: cess omitted on Farhan's tax)_

**Working**

1. Esha: total income = 11,85,000 ≤ 12,00,000 → tax 58,500 fully rebated → Nil
2. Farhan: total income = 12,15,000 > 12,00,000 → no rebate; slab tax = 60,000 + 15% × 15,000 = 62,250
3. Marginal relief: tax limited to excess over 12,00,000 = 15,000 (< 62,250); + 4% cess = ₹15,600

**Formula:** Rebate if total income ≤ ₹12 lakh; above it, tax ≤ (Total income − ₹12 lakh) (marginal relief)  
**Trap:** Marginal relief removes the cliff: without it Farhan would pay ₹64,740 on income just ₹15,000 over the limit.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:
