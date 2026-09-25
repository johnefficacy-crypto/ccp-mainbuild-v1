"""ECO part 2 — Keynesian macro, multiplier, IS-LM, money supply (46 Q: L1 9, L2 14, L3 15, L4 8)."""
from eco_common import mk, cr, n, tbl, items, stmts, inr, R, pct

RBIM = "RBI monetary aggregates (Second Working Group on Money Supply definitions: M0, M1, M2, M3, M4)."


def add_all(B):
    q = mk(B)

    # ======================= L1 =======================
    q("say-s-law", "L1", "Say's law of markets is best summarised as:",
      "Supply creates its own demand, so no general glut can persist",
      [("Demand creates its own supply, so output follows spending", "this is the Keynesian principle of effective demand"),
       ("Prices are sticky, so markets need not clear at all", "Keynesian/new-Keynesian assumption, opposite of Say"),
       ("Money is neutral only in the long run, not the short run", "a monetarist proposition, not Say's law")],
      ["Classical view: production generates income equal to the value of output.", "That income is spent (consumption or, via interest-rate adjustment, investment).",
       "Hence partial gluts may occur but not general over-production."],
      "Aggregate supply = Aggregate demand at all output levels", "Keynes reversed the causation.", kind="conceptual")

    q("consumption-function", "L1", "According to Keynes' psychological law of consumption, when income rises:",
      "Consumption rises, but by less than the rise in income",
      [("Consumption rises in the same proportion as income", "implies constant APC — not Keynes' short-run law"),
       ("Consumption rises by more than income at high incomes", "MPC > 1 contradicts the law"),
       ("Saving falls as a share of income", "APS rises with income under the law")],
      ["0 < MPC < 1: part of every extra rupee is saved.", "With autonomous consumption, APC falls as income rises."],
      "C = a + bY, 0 < b < 1", "MPC < 1 is what makes the multiplier finite.", kind="conceptual")

    q("liquidity-trap", "L1", "An economy is said to be in a liquidity trap when:",
      "Money demand is perfectly elastic at a floor rate, so more money fails to lower r",
      [("Demand for money is perfectly interest-inelastic, making the LM curve vertical", "that is the classical case"),
       ("Investment is completely insensitive to the interest rate, making IS vertical", "that is the investment trap"),
       ("Banks must keep 100% reserves against all their deposits", "a reserve-requirement regime, unrelated")],
      ["At a floor interest rate everyone expects bond prices to fall, so all extra money is hoarded.", "LM is horizontal; monetary expansion is ineffective, fiscal policy is fully effective."],
      "LM horizontal at r_min", "Horizontal LM ≠ vertical IS; both weaken monetary policy for different reasons.", kind="conceptual")

    q("demand-for-money", "L1", "In Keynes' liquidity-preference theory, the speculative demand for money is:",
      "Inversely related to the rate of interest",
      [("Directly related to the level of income", "that describes transactions demand"),
       ("Directly related to the rate of interest", "sign reversed"),
       ("Independent of the rate of interest and held for emergencies", "that describes precautionary demand in the basic version")],
      ["High interest rate ⇒ low bond prices ⇒ expected capital gains ⇒ hold bonds, not money.", "Low interest rate ⇒ expected fall in bond prices ⇒ hold money."],
      "L2 = f(r), f′ < 0", "Transactions and precautionary demand depend on income.", kind="conceptual")

    q("money-supply-measures", "L1", "Under RBI's traditional money-supply measures, broad money M3 equals:",
      "M1 plus net time deposits with banks",
      [("M1 plus savings deposits with post-office savings banks", "that is M2"),
       ("M3 plus total post-office deposits (excluding NSCs)", "that is M4"),
       ("Currency in circulation plus bankers' deposits with RBI plus other deposits with RBI", "that is reserve money M0")],
      ["M1 = Currency with public + Demand deposits with banks + Other deposits with RBI.", "M3 = M1 + Time deposits with banks."],
      "M3 = M1 + TD", "M2 and M4 add post-office deposits; M3 adds bank time deposits.", kind="conceptual", verify_fact=True, ref=RBIM)

    q("monetary-base", "L1", "Reserve money (high-powered money) as compiled by RBI comprises:",
      "Currency in circulation + bankers' deposits with RBI + 'other' deposits with RBI",
      [("Currency with the public + demand deposits with banks + 'other' deposits with RBI", "that is M1"),
       ("Currency in circulation + time deposits with banks", "mixes base money with broad money"),
       ("Bankers' deposits with RBI only", "only one component — bank reserves")],
      ["M0 is the monetary liability of the central bank.", "Currency in circulation includes cash held by banks."],
      "M0 = CiC + Bankers' deposits with RBI + Other deposits with RBI", "Bank deposits of the public are not central-bank liabilities.",
      kind="conceptual", verify_fact=True, ref=RBIM)

    q("keynesian-effective", "L1", "In Keynes' theory, effective demand is the level of aggregate demand:",
      "Where the aggregate demand and aggregate supply functions intersect",
      [("That corresponds to full employment of the whole labour force", "equilibrium need not be at full employment"),
       ("At which aggregate saving of households becomes zero", "that is the break-even income level of the consumption function"),
       ("At which the marginal efficiency of capital equals zero", "MEC relates to investment, not to effective demand")],
      ["Entrepreneurs' expected proceeds (AD) equal the minimum proceeds they need (AS) at that point.", "It fixes output and employment — possibly below full employment."],
      "ADF = ASF", "Keynesian equilibrium can coexist with involuntary unemployment.", kind="conceptual")

    q("investment-function", "L1", "The marginal efficiency of capital (MEC) is:",
      "The discount rate equating PV of expected yields to the asset's supply price",
      [("The market rate of interest on long-term government bonds", "that is the cost of funds, compared against MEC"),
       ("Accounting profit divided by the book value of the firm's capital stock", "backward-looking accounting return"),
       ("Extra physical output obtained from one more unit of capital", "physical marginal product, not a rate of return")],
      ["MEC is forward-looking: it uses expected yields and the replacement (supply) price.", "Invest while MEC > rate of interest."],
      "Supply price = Σ Rₜ / (1 + MEC)ᵗ", "MEC is an internal rate of return.", kind="conceptual")

    q("opportunity-cost", "L1", "The opportunity cost of holding wealth in the form of currency is best measured by:",
      "The nominal interest rate on alternative assets",
      [("The real interest rate on alternative assets", "ignores that currency also loses to inflation — cost = r + π = i"),
       ("The inflation rate alone, as currency loses value", "bonds also lose to inflation; the forgone return is the nominal rate"),
       ("The cash reserve ratio set by the central bank", "a bank regulatory ratio, not a holder's cost")],
      ["Holding currency forgoes the nominal yield i ≈ r + πᵉ.", "Hence money demand falls as the nominal interest rate rises."],
      "Opportunity cost = i", "Nominal, not real.", kind="conceptual")

    # ======================= L2 =======================
    mpc, dI = 0.8, 500
    k = 1 / (1 - mpc)
    q("multiplier", "L2", f"MPC is {mpc}. Autonomous investment rises by {cr(dI)}. The increase in equilibrium income is:",
      cr(dI * k),
      [(cr(dI * mpc / (1 - mpc)), "tax-multiplier formula c/(1−c) used"),
       (cr(dI / mpc), "multiplier taken as 1/MPC"),
       (cr(dI * mpc), "only the first round of induced consumption")],
      [f"k = 1/(1 − {mpc}) = {n(k)}", f"ΔY = {dI} × {n(k)} = {inr(dI*k)}"],
      "k = 1/(1 − MPC)", "The multiplier uses MPS in the denominator.")

    a, b, Y = 200, 0.75, 2000
    Cn = a + b * Y; S = Y - Cn
    q("consumption-function", "L2", f"The consumption function is C = {a} + {b}Y. At Y = {inr(Y)}, the average propensity to save is:",
      n(S / Y, 4),
      [(n(1 - b, 4), "MPS reported instead of APS"),
       (n(Cn / Y, 4), "APC reported"),
       (n(S / Cn, 4), "saving divided by consumption")],
      [f"C = {a} + {b}×{inr(Y)} = {inr(Cn)}", f"S = {inr(Y)} − {inr(Cn)} = {inr(S)}", f"APS = {inr(S)} ÷ {inr(Y)} = {n(S/Y,4)}"],
      "APS = S/Y; MPS = ΔS/ΔY", "With positive autonomous consumption, APS < MPS.")

    a2, b2, I2 = 100, 0.8, 150
    Ye = (a2 + I2) / (1 - b2)
    q("two-sector", "L2", f"In a two-sector economy, C = {a2} + {b2}Y and planned investment I = {I2} (₹ crore). Equilibrium income is:",
      cr(Ye),
      [(cr((a2 + I2) / b2, 1), "autonomous spending divided by MPC"),
       (cr(a2 / (1 - b2) + I2), "multiplier applied to autonomous consumption only"),
       (cr(a2 + b2 * Ye), "equilibrium consumption reported instead of income")],
      [f"Y = C + I ⇒ Y = {a2} + {b2}Y + {I2}", f"Y = {a2+I2} ÷ {n(1-b2)} = {inr(Ye)}"],
      "Y* = (a + I)/(1 − b)", "Both autonomous components are multiplied.")

    dep, crr, ex = 1000, 0.04, 0.01
    q("money-multiplier", "L2",
      f"A bank receives a fresh cash deposit of {cr(dep)}. CRR is {pct(crr)} and banks voluntarily hold excess reserves of {pct(ex)} of deposits; there is no currency drain. Total deposits that the banking system can finally support are:",
      cr(dep / (crr + ex)),
      [(cr(dep / crr), "excess reserves ignored"),
       (cr(dep / (crr + ex) - dep), "additional loans/derivative deposits reported instead of total deposits"),
       (cr(dep * (1 - crr - ex)), "only the first-round loan")],
      [f"Reserve ratio = {pct(crr)} + {pct(ex)} = {pct(crr+ex)}", f"Deposits = {inr(dep)} ÷ {crr+ex} = {inr(dep/(crr+ex))}"],
      "ΔD = ΔReserves ÷ (required + excess reserve ratio)", "Voluntary excess reserves are a leakage too.")

    c_, r_ = 0.25, 0.05
    m = (1 + c_) / (c_ + r_)
    q("money-multiplier", "L2", f"The public's currency-deposit ratio is {c_} and banks' reserve-deposit ratio is {r_}. The money multiplier (M/H) is:",
      n(m, 2),
      [(n(1 / r_, 2), "currency drain ignored (simple deposit multiplier)"),
       (n(1 / (c_ + r_), 2), "numerator (1 + c) omitted"),
       (n((1 + r_) / (c_ + r_), 2), "numerator uses r instead of c")],
      [f"m = (1 + {c_}) ÷ ({c_} + {r_}) = {n(1+c_)} ÷ {n(c_+r_)} = {n(m)}"],
      "m = (1 + c)/(c + r)", "The currency ratio appears in both numerator and denominator.")

    M, V, M2, V2, T = 5000, 4, 2000, 2, 1200
    P = (M * V + M2 * V2) / T
    q("fisher-equation", "L2",
      f"In Fisher's extended equation, currency M = {inr(M)} with velocity {V}, bank (credit) money M′ = {inr(M2)} with velocity {V2}, and the volume of transactions T = {inr(T)}. The price level is:",
      n(P, 2),
      [(n(M * V / T, 2), "bank money ignored"),
       (n((M + M2) * (V + V2) / T, 2), "money stocks and velocities summed separately"),
       (n((M * V + M2) / T, 2), "bank money entered without its velocity")],
      [f"P = (MV + M′V′)/T = ({inr(M*V)} + {inr(M2*V2)}) ÷ {inr(T)} = {n(P)}"],
      "PT = MV + M′V′", "Each money stock carries its own velocity.")

    v_, y0, y1 = 3, 500, 560
    q("accelerator", "L2", f"The capital-output ratio (accelerator) is {v_}. Output rises from {cr(y0)} to {cr(y1)}. Induced net investment is:",
      cr(v_ * (y1 - y0)),
      [(cr(v_ * y1), "accelerator applied to output level, not change"),
       (cr((y1 - y0) / v_), "change in output divided by accelerator"),
       (cr(v_ * y0), "accelerator applied to previous output level")],
      [f"I_net = v × ΔY = {v_} × {y1-y0} = {v_*(y1-y0)}"],
      "I_induced = v · ΔY", "Accelerator links investment to the CHANGE in output.")

    kY, kr, Msn, Pl, Yq = 0.25, 50, 625, 1.25, 2400
    rq = (kY * Yq - Msn / Pl) / kr
    q("lm-curve", "L2",
      f"Real money demand is Md/P = {kY}Y − {kr}r (r in per cent). Nominal money supply is {inr(Msn)} and the price level is {Pl}. At Y = {inr(Yq)}, the interest rate that clears the money market is:",
      f"{n(rq)}%",
      [(f"{n((kY*Yq + Msn/Pl)/kr)}%", "money supply added instead of equated"),
       (f"{n((kY*Yq - Msn)/kr)}%", "nominal money supply not deflated"),
       (f"{n(kY*Yq/kr)}%", "money supply ignored")],
      [f"Real Ms = {inr(Msn)} ÷ {Pl} = {inr(Msn/Pl)}", f"{kY}×{inr(Yq)} − {kr}r = {inr(Msn/Pl)} ⇒ r = ({inr(kY*Yq)} − {inr(Msn/Pl)}) ÷ {kr} = {n(rq)}"],
      "LM: M/P = kY − hr", "Deflate the nominal money stock first.")

    a3, b3, I0, d3, G3, r3 = 100, 0.8, 300, 20, 200, 5
    k3 = 1 / (1 - b3)
    Yis = k3 * (a3 + I0 + G3 - d3 * r3)
    q("is-curve", "L2",
      f"C = {a3} + {b3}Y, I = {I0} − {d3}r, G = {G3} (no taxes). At r = {r3}%, the output level on the IS curve is:",
      cr(Yis),
      [(cr(k3 * (a3 + I0 + G3)), "interest-rate term ignored"),
       (cr(k3 * (a3 + I0 + G3) - d3 * r3), "interest term not multiplied"),
       (cr((a3 + I0 + G3 - d3 * r3) / b3), "multiplier taken as 1/MPC")],
      [f"Y = {n(k3)} × ({a3} + {I0} + {G3} − {d3}×{r3}) = {n(k3)} × {a3+I0+G3-d3*r3} = {inr(Yis)}"],
      "IS: Y = k(A − dr)", "The whole autonomous term, including −dr, is multiplied.")

    kk, Yd, L2a, L2b, rd = 0.2, 5000, 400, 40, 6
    Lt = kk * Yd; Ls = L2a - L2b * rd
    q("demand-for-money", "L2",
      f"Transactions-cum-precautionary demand is L₁ = {kk}Y and speculative demand is L₂ = {L2a} − {L2b}r. At Y = {inr(Yd)} and r = {rd}%, total demand for money is:",
      cr(Lt + Ls),
      [(cr(Lt), "speculative demand ignored"),
       (cr(Lt + L2a), "interest term in L₂ ignored"),
       (cr(Lt + L2a + L2b * rd), "speculative demand treated as rising with r")],
      [f"L₁ = {kk}×{inr(Yd)} = {inr(Lt)}", f"L₂ = {L2a} − {L2b}×{rd} = {Ls}", f"L = {inr(Lt+Ls)}"],
      "L = L₁(Y) + L₂(r)", "Speculative demand falls as r rises.")

    cp, cb, bd, od, dd = 2900, 100, 800, 50, 1500
    rm = cp + cb + bd + od
    q("monetary-base", "L2",
      "From the following (₹ '000 crore), reserve money is:\n\n" + items([
          ("Currency with the public", cp), ("Cash in hand with banks", cb), ("Bankers' deposits with the central bank", bd),
          ("'Other' deposits with the central bank", od), ("Demand deposits of the public with banks", dd)], unit="₹ '000 crore"),
      f"₹{inr(rm)} thousand crore",
      [(f"₹{inr(rm - cb)} thousand crore", "cash held by banks excluded from currency in circulation"),
       (f"₹{inr(rm - od)} thousand crore", "'other' deposits with the central bank omitted"),
       (f"₹{inr(rm + dd)} thousand crore", "public's demand deposits with banks included")],
      [f"Currency in circulation = {inr(cp)} + {cb} = {inr(cp+cb)}", f"M0 = {inr(cp+cb)} + {bd} + {od} = {inr(rm)}"],
      "M0 = CiC + Bankers' deposits + Other deposits with CB", "Vault cash is currency in circulation (outside the central bank).",
      verify_fact=True, ref=RBIM)

    cu, ddp, oth, tdp, posb = 3000, 2200, 40, 8000, 300
    m3 = cu + ddp + oth + tdp
    q("money-supply-measures", "L2",
      f"Currency with the public {cr(cu)}; demand deposits with banks {cr(ddp)}; 'other' deposits with RBI {cr(oth)}; time deposits with banks {cr(tdp)}; savings deposits with post-office savings banks {cr(posb)}. Broad money M3 is:",
      cr(m3),
      [(cr(m3 + posb), "post-office savings deposits added (M2 component)"),
       (cr(m3 - tdp), "time deposits excluded — this is M1"),
       (cr(m3 - oth), "'other' deposits with RBI omitted")],
      [f"M1 = {inr(cu)} + {inr(ddp)} + {oth} = {inr(cu+ddp+oth)}", f"M3 = M1 + {inr(tdp)} = {inr(m3)}"],
      "M3 = M1 + Time deposits with banks", "Post-office deposits are never in M3.", verify_fact=True, ref=RBIM)

    sal, i_, pi_ = 60000, 0.06, 0.04
    avg = sal / 2
    q("opportunity-cost", "L2",
      f"A household receives ₹{inr(sal)} at the start of each month and spends it evenly over the month, holding it as currency. "
      f"Deposits yield {pct(i_)} a year and expected inflation is {pct(pi_)}. The annual opportunity cost of this currency holding is approximately:",
      R(avg * i_),
      [(R(sal * i_), "full monthly receipt used instead of average balance"),
       (R(avg * (i_ - pi_)), "real instead of nominal interest rate used"),
       (R(avg * i_ / 12), "annual rate applied as if monthly cost were asked")],
      [f"Average currency held = {inr(sal)} ÷ 2 = {inr(avg)}", f"Cost = {inr(avg)} × {pct(i_)} = ₹{inr(avg*i_)} a year"],
      "Opportunity cost = i × average money balance", "Currency pays zero nominal return, so the forgone yield is nominal.")

    Yo, Cp, Ip = 1000, 850, 120
    q("keynesian-effective", "L2",
      f"At an output of {cr(Yo)}, planned consumption is {cr(Cp)} and planned investment is {cr(Ip)}. Which describes the situation?",
      f"Unplanned inventories rise by {cr(Yo-Cp-Ip)}; output tends to fall",
      [(f"Unplanned inventories fall by {cr(Yo-Cp-Ip)}; output tends to rise", "direction of disequilibrium reversed"),
       ("Output is in equilibrium because actual saving always equals actual investment", "confuses ex-post identity with ex-ante equilibrium"),
       (f"Unplanned inventories rise by {cr(Yo-Cp)}; output tends to fall", "saving taken as the unplanned inventory change")],
      [f"Planned AD = {Cp} + {Ip} = {Cp+Ip} < output {inr(Yo)}", f"Unsold output = {Yo-Cp-Ip} piles up as unplanned stock; firms cut production."],
      "AD < Y ⇒ unplanned inventory accumulation ⇒ Y falls", "Planned S (150) > planned I (120) says the same thing.")

    # ======================= L3 =======================
    c4, t4, dG4 = 0.8, 0.25, 400
    k4 = 1 / (1 - c4 * (1 - t4))
    q("multiplier", "L3",
      f"MPC out of disposable income is {c4} and there is a proportional income tax at {pct(t4)}. Government purchases rise by {cr(dG4)}. The rise in equilibrium income is:",
      cr(dG4 * k4),
      [(cr(dG4 / (1 - c4)), "tax leakage ignored"),
       (cr(dG4 / (1 - c4 + t4), 2), "tax rate added to MPS instead of scaling the MPC"),
       (cr(dG4 * c4 * (1 - t4) * k4), "tax-multiplier numerator c(1−t) applied to a spending change")],
      [f"k = 1/[1 − {c4}(1 − {t4})] = 1/{n(1-c4*(1-t4))} = {n(k4)}", f"ΔY = {dG4} × {n(k4)} = {inr(dG4*k4)}"],
      "k = 1/[1 − c(1 − t)]", "Proportional tax lowers the effective MPC to c(1−t).")

    c5, dg5 = 0.75, 300
    kG = 1 / (1 - c5); kT = c5 / (1 - c5)
    q("multiplier", "L3",
      f"Government raises spending by {cr(dg5)} and finances it fully by a lump-sum tax of {cr(dg5)}. MPC is {c5}. Equilibrium income rises by:",
      cr(dg5 * (kG - kT)),
      [("Zero, because the tax exactly offsets the spending", "ignores that part of the tax comes out of saving"),
       (cr(dg5 * kG), "tax effect ignored"),
       (cr(dg5 * (kG + kT)), "tax multiplier added instead of subtracted")],
      [f"G multiplier = {n(kG)}; tax multiplier = −{n(kT)}", f"ΔY = {dg5}×{n(kG)} − {dg5}×{n(kT)} = {inr(dg5*(kG-kT))}"],
      "Balanced-budget multiplier = 1 (lump-sum tax)", "Tax cuts consumption by only c × ΔT in the first round.")

    c6, m6, dX = 0.8, 0.2, 200
    k6 = 1 / (1 - c6 + m6)
    q("multiplier", "L3",
      f"In an open economy with no taxes, MPC is {c6} and marginal propensity to import is {m6}. Exports rise by {cr(dX)}. Equilibrium income rises by:",
      cr(dX * k6),
      [(cr(dX / (1 - c6)), "import leakage ignored"),
       (cr(dX / (c6 + m6)), "multiplier taken as 1/(c + m)"),
       (cr(dX * (1 - m6) / (1 - c6)), "multiplier computed as (1 − m)/(1 − c)")],
      [f"k = 1/(1 − {c6} + {m6}) = 1/{n(1-c6+m6)} = {n(k6)}", f"ΔY = {dX} × {n(k6)} = {inr(dX*k6)}"],
      "k_open = 1/(s + m)", "Imports are a second leakage alongside saving.")

    d7, crr7, slr7 = 10000, 0.04, 0.18
    dep7 = d7 / (crr7 + slr7); loans7 = dep7 * (1 - crr7 - slr7)
    q("money-multiplier", "L3",
      f"A primary cash deposit of {cr(d7)} enters the banking system. Banks keep CRR of {pct(crr7)} with the central bank and invest {pct(slr7)} of every deposit in SLR "
      "government securities (treated as a leakage from the loan chain); they hold no excess reserves and the public holds no additional cash. "
      "Total loans (credit) created by the banking system are:",
      cr(loans7),
      [(cr(dep7), "total deposits reported instead of loans"),
       (cr(d7 / crr7 * (1 - crr7)), "SLR leakage ignored"),
       (cr(d7 * (1 - crr7 - slr7)), "only the first-round loan")],
      [f"Leakage per round = {pct(crr7)} + {pct(slr7)} = {pct(crr7+slr7)}", f"Total deposits = {inr(d7)} ÷ {crr7+slr7} = {inr(dep7)}",
       f"Loans = {inr(dep7)} × (1 − {crr7+slr7}) = {inr(loans7)}"],
      "D = ΔR/(CRR + SLR); Loans = D × (1 − CRR − SLR)", "Under the stated assumption both CRR and SLR leak out of lending.")

    cpu, dtot, res = 25000, 125000, 10000
    cc, rr = cpu / dtot, res / dtot
    mm = (1 + cc) / (cc + rr); dH = 2000
    Mt, Ht = cpu + dtot, cpu + res
    assert abs(Mt / Ht - mm) < 1e-9
    q("money-multiplier", "L3",
      "Monetary data (₹ crore):\n\n" + items([("Currency with the public", cpu), ("Deposits of the public with banks", dtot),
                                                ("Reserves of banks with the central bank (incl. vault cash)", res)]) +
      f"\n\nWith behavioural ratios unchanged, the central bank injects {cr(dH)} of high-powered money. Money supply rises by about:",
      cr(dH * mm),
      [(cr(dH / rr), "simple deposit multiplier 1/r"),
       (cr(dH / (cc + rr)), "numerator (1 + c) dropped"),
       (cr(dH / cc), "multiplier taken as 1/c")],
      [f"c = {inr(cpu)}/{inr(dtot)} = {cc}; r = {inr(res)}/{inr(dtot)} = {rr}", f"m = (1 + {cc})/({cc} + {rr}) = {n(mm,4)} (check: M/H = {inr(Mt)}/{inr(Ht)})",
       f"ΔM = {inr(dH)} × {n(mm,4)} = {inr(dH*mm)}"],
      "ΔM = ΔH × (1 + c)/(c + r)", "Derive c and r from the data before applying the formula.")

    a8, b8, T8, I8, d8, G8 = 150, 0.8, 100, 400, 25, 250
    k8 = 1 / (1 - b8)
    A8 = a8 - b8 * T8 + I8 + G8
    q("is-curve", "L3",
      f"C = {a8} + {b8}(Y − T), T = {T8} (lump sum), I = {I8} − {d8}r, G = {G8}. The IS curve is:",
      f"Y = {inr(k8*A8)} − {n(k8*d8)}r",
      [(f"Y = {inr(k8*(a8 - T8 + I8 + G8))} − {n(k8*d8)}r", "tax not multiplied by MPC"),
       (f"Y = {inr(k8*A8)} − {d8}r", "interest term not multiplied"),
       (f"Y = {inr(k8*(a8 + I8 + G8))} − {n(k8*d8)}r", "tax ignored")],
      [f"Y = {a8} + {b8}(Y − {T8}) + {I8} − {d8}r + {G8}", f"0.2Y = {inr(A8)} − {d8}r", f"Y = {inr(k8*A8)} − {n(k8*d8)}r"],
      "IS: Y = [a − cT + I₀ + G − dr]/(1 − c)", "Lump-sum tax reduces autonomous spending by c·T, not T.")

    kL, hL, MsL, PL = 0.4, 80, 1440, 1.2
    y0L, slL = MsL / PL / kL, hL / kL
    q("lm-curve", "L3",
      f"Real money demand is Md/P = {kL}Y − {hL}r; nominal money supply is {inr(MsL)} and P = {PL}. The LM curve is:",
      f"Y = {inr(y0L)} + {n(slL)}r",
      [(f"Y = {inr(MsL/kL)} + {n(slL)}r", "nominal money supply not deflated"),
       (f"Y = {inr(y0L)} − {n(slL)}r", "sign of the interest term reversed"),
       (f"Y = {inr(y0L)} + {hL}r", "interest coefficient not divided by k")],
      [f"Real Ms = {inr(MsL)}/{PL} = {inr(MsL/PL)}", f"{kL}Y − {hL}r = {inr(MsL/PL)} ⇒ Y = {inr(y0L)} + {n(slL)}r"],
      "LM: Y = (M/P)/k + (h/k) r", "LM slopes upward: higher Y needs higher r to keep money demand = supply.")

    q("shifts-in-the-is", "L3",
      "Consider the following statements about the IS-LM model:\n\n" + stmts([
          "The IS curve is flatter the more interest-sensitive investment is.",
          "A higher marginal propensity to consume makes the IS curve steeper.",
          "The LM curve is flatter the more interest-sensitive the demand for money is.",
          "Fiscal expansion raises output more when the LM curve is flatter."]) + "\n\nWhich are correct?",
      "1, 3 and 4 only",
      [("1 and 3 only", "misses that flatter LM means less crowding out"),
       ("1, 2, 3 and 4", "higher MPC raises the multiplier and flattens IS"),
       ("2, 3 and 4 only", "rejects the investment-sensitivity result")],
      ["IS slope ∝ −(1 − c)/d: larger d or larger c ⇒ flatter IS (1 true, 2 false).", "LM slope = k/h: larger h ⇒ flatter LM (3 true).",
       "Flatter LM ⇒ smaller rise in r ⇒ less crowding out (4 true)."],
      "IS: r = A/d − (1−c)Y/d; LM: r = (kY − M/P)/h", "Higher MPC → flatter, not steeper, IS.", kind="statement")

    q("liquidity-trap", "L3",
      "**Assertion (A):** In a liquidity trap, a bond-financed increase in government spending raises output by the full simple multiplier.\n\n"
      "**Reason (R):** With a horizontal LM curve, the higher transactions demand for money is met out of idle balances without any rise in the interest rate.",
      "Both A and R are true and R is the correct explanation of A",
      [("Both A and R are true but R is not the correct explanation of A", "R is exactly why there is no crowding out"),
       ("A is true but R is false", "misreads the horizontal LM"),
       ("A is false because crowding out is complete in a liquidity trap", "complete crowding out is the classical (vertical LM) case")],
      ["Horizontal LM ⇒ r unchanged as IS shifts.", "No fall in investment ⇒ ΔY = k·ΔG."],
      "ΔY = ΔG/(1 − c) when LM is horizontal", "Liquidity trap and classical case are mirror images.", kind="assertion-reason")

    a9, b9, I9, dA = 100, 0.75, 150, 100
    Y0 = (a9 + I9) / (1 - b9); Y1 = (a9 - dA + I9) / (1 - b9)
    q("two-sector", "L3",
      f"In a two-sector economy C = {a9} + {b9}Y and investment is fixed at {cr(I9)}. Households decide to save more: autonomous consumption falls by {cr(dA)} at every income level. In the new equilibrium:",
      f"Income falls by {cr(Y0-Y1)} and total saving stays at {cr(I9)}",
      [(f"Income falls by {cr(dA)} and total saving rises by {cr(dA)}", "multiplier ignored; saving treated as rising one-for-one"),
       (f"Income falls by {cr(Y0-Y1)} and total saving rises by {cr(dA)}", "misses the paradox — saving must equal fixed investment"),
       (f"Income is unchanged and total saving rises by {cr(dA)}", "classical view: interest rate channels saving into investment")],
      [f"Y₀ = {a9+I9}/0.25 = {inr(Y0)}; Y₁ = {a9-dA+I9}/0.25 = {inr(Y1)}", f"ΔY = −{inr(Y0-Y1)}", f"Equilibrium S = I = {I9} in both cases."],
      "S = I in equilibrium; ΔY = ΔA/(1 − c)", "Paradox of thrift: attempt to save more leaves actual saving unchanged.")

    out = [100, 120, 150, 170, 180]; vv = 2
    inv = [vv * (out[i] - out[i - 1]) for i in range(1, len(out))]
    first_fall = next(i + 2 for i in range(1, len(inv)) if inv[i] < inv[i - 1])
    assert inv == [40, 60, 40, 20] and first_fall == 4
    q("accelerator", "L3",
      "Output of consumer goods over five periods is given below; the capital-output ratio is 2 and there is no replacement investment.\n\n" +
      tbl(["Period", "1", "2", "3", "4", "5"], [["Output (₹ crore)"] + out]) +
      "\n\nIn which period does induced net investment FIRST decline?",
      f"Period {first_fall}",
      [("Period 5", "looked for the first fall in output growth rate below 10%"),
       ("Period 3", "confused the period of peak investment with the first decline"),
       ("It never declines, because output keeps rising", "accelerator depends on the change, not the level, of output")],
      [f"Net investment = 2 × ΔY: periods 2–5 = {inv}", f"It first falls in period {first_fall} (60 → 40) though output is still rising."],
      "Iₜ = v(Yₜ − Yₜ₋₁)", "A mere slowdown in output growth cuts investment — source of cycles.")

    s, vco, dl = 0.24, 4, 0.02
    g = s / vco - dl
    q("accelerator", "L3",
      f"In a Harrod-Domar framework the saving rate is {pct(s)}, the incremental capital-output ratio is {vco} and capital depreciates at {pct(dl)} a year. The growth rate of output is:",
      pct(g),
      [(pct(s / vco), "depreciation ignored"),
       (pct(s / vco + dl), "depreciation added instead of deducted"),
       (pct(vco / s - dl), "ratio inverted (v/s)")],
      [f"g = s/v − δ = {s}/{vco} − {dl} = {pct(g)}"],
      "g = s/v − δ", "ICOR is the accelerator coefficient; a higher ICOR means slower growth.")

    cost, y1_, y2_, rm_ = 10000, 5500, 6050, 0.08
    mec = 0.10
    assert abs(y1_ / (1 + mec) + y2_ / (1 + mec) ** 2 - cost) < 1e-6
    q("investment-function", "L3",
      f"A machine costs {R(cost)} and is expected to yield {R(y1_)} at the end of year 1 and {R(y2_)} at the end of year 2, with no scrap value. The market rate of interest is {pct(rm_)}. The MEC and the investment decision are:",
      f"{pct(mec)} — invest",
      [(f"{pct((y1_ + y2_ - cost) / cost)} — invest", "undiscounted total return used"),
       (f"{pct((y1_ + y2_ - cost) / cost / 2)} — do not invest", "simple average annual return, undiscounted"),
       (f"{pct(mec)} — do not invest", "decision rule reversed")],
      [f"Try 10%: {inr(y1_)}/1.1 + {inr(y2_)}/1.21 = 5,000 + 5,000 = {inr(cost)} ⇒ MEC = 10%", "MEC 10% > r 8% ⇒ invest."],
      "Cost = R₁/(1+m) + R₂/(1+m)²", "MEC is an IRR, compared with the market interest rate.")

    gm, gv, gy = 0.12, -0.01, 0.06
    infl = gm + gv - gy
    q("fisher-equation", "L3",
      f"Money supply grows at {pct(gm)}, velocity falls by {pct(-gv)} and real output grows at {pct(gy)}. Using the growth-rate form of the quantity equation, inflation is approximately:",
      pct(infl),
      [(pct(gm - gy), "change in velocity ignored"),
       (pct(gm - gv - gy), "velocity change sign reversed"),
       (pct(gm + gv + gy), "real output growth added instead of subtracted")],
      [f"π ≈ %ΔM + %ΔV − %ΔY = {pct(gm)} − {pct(-gv)} − {pct(gy)} = {pct(infl)}"],
      "%ΔM + %ΔV = %ΔP + %ΔY", "Falling velocity absorbs part of the money growth.")

    q("say-s-law", "L3",
      "**Assertion (A):** In the classical system based on Say's law, persistent involuntary unemployment cannot occur.\n\n"
      "**Reason (R):** A flexible rate of interest equates saving with investment, so income withdrawn as saving returns to the spending stream.",
      "Both A and R are true and R is the correct explanation of A",
      [("Both A and R are true but R is not the correct explanation of A", "R is the classical mechanism behind Say's law"),
       ("A is true but R is false", "the interest-rate mechanism is central to the classical model"),
       ("A is false but R is true", "classical economists accepted only voluntary/frictional unemployment")],
      ["Saving is a leakage; classical interest-rate flexibility turns it into investment.", "With flexible wages and prices too, the economy returns to full employment."],
      "S(r) = I(r)", "Keynes attacked both links: saving depends on income, and money wages are rigid.", kind="assertion-reason")

    # ======================= L4 case D (IS-LM) =======================
    GD = "ECO-ISLM-CASE-D"
    aD, bD, I0D, dD, GD0 = 100, 0.75, 700, 50, 200
    kD, hD, MsD, PD = 0.5, 150, 1200, 1.2
    kmD = 1 / (1 - bD)

    def solve(Ais, sis, y0lm, slm):  # IS: Y = Ais − sis r ; LM: Y = y0lm + slm r
        r = (Ais - y0lm) / (sis + slm)
        return Ais - sis * r, r

    Ais, sis = kmD * (aD + I0D + GD0), kmD * dD
    y0lm, slm = MsD / PD / kD, hD / kD
    Y0D, r0D = solve(Ais, sis, y0lm, slm)
    assert (round(Y0D), round(r0D, 6)) == (3200, 4)
    stemD = ("**Case — Economy of Tarsha.** Goods market: C = 100 + 0.75Y, I = 700 − 50r, G = 200 (no taxes, closed economy). "
             "Money market: real money demand Md/P = 0.5Y − 150r; nominal money supply 1,200; price level fixed at 1.2. "
             "(Y in ₹ crore, r in per cent.)\n\n")
    fmt = lambda Y, r: f"Y = {cr(Y, 2 if abs(Y-round(Y))>1e-6 else 0)}, r = {n(r)}%"
    e1 = solve(kmD * (aD + I0D + GD0) , dD, y0lm, slm)
    e2 = solve(Ais, sis, MsD / kD, slm)
    e3 = solve(Ais, sis, MsD / PD, hD)
    q("equilibrium-in-goods", "L4", stemD + "**Q.** The simultaneous equilibrium in the goods and money markets is:",
      fmt(Y0D, r0D),
      [(fmt(*e1), "interest term of investment not multiplied in the IS curve"),
       (fmt(*e2), "nominal money supply not deflated by P"),
       (fmt(*e3), "LM equation not divided by the income coefficient 0.5")],
      [f"IS: Y = 4(1,000 − 50r) = {inr(Ais)} − {n(sis)}r", f"LM: 0.5Y − 150r = 1,000 ⇒ Y = {inr(y0lm)} + {n(slm)}r",
       f"{inr(Ais)} − 200r = {inr(y0lm)} + 300r ⇒ r = {n(r0D)}%, Y = {inr(Y0D)}"],
      "Solve IS and LM together", "Each distractor comes from one algebra slip.", kind="case", group=GD)
    dG = 100
    Y1D, r1D = solve(Ais + kmD * dG, sis, y0lm, slm)
    Yw, rw = solve(Ais + dG / bD, sis, y0lm, slm)
    q("shifts-in-the-is", "L4", stemD + f"**Q.** Government spending rises by {cr(dG)} (bond-financed). The new equilibrium income is:",
      cr(Y1D),
      [(cr(Y0D + kmD * dG), "interest rate held at 4% — no crowding out"),
       (cr(Y0D + dG), "spending increase added without any multiplier"),
       (cr(Yw), "IS shift computed with multiplier 1/MPC")],
      [f"IS shifts right by 4 × 100 = 400: Y = {inr(Ais+400)} − 200r", f"With LM: 500r = {inr(Ais+400-y0lm)} ⇒ r = {n(r1D)}%, Y = {inr(Y1D)}",
       f"ΔY = {inr(Y1D-Y0D)} < 400 because r rose."],
      "ΔY = k(ΔG − dΔr)", "Upward-sloping LM ⇒ partial crowding out.", kind="case", group=GD)
    dI_ = dD * (r1D - r0D)
    q("shifts-in-the-is", "L4", stemD + f"**Q.** In the fiscal expansion of {cr(dG)} above, private investment is crowded out by:",
      cr(dI_),
      [(cr(kmD * dG - (Y1D - Y0D)), "income-equivalent crowding-out (400 − 240) reported instead of investment"),
       ("Zero, because investment depends only on income", "investment here depends on r"),
       (cr(kmD * dG), "full IS shift reported")],
      [f"Δr = {n(r1D)} − {n(r0D)} = {n(r1D-r0D)} points", f"ΔI = −50 × {n(r1D-r0D)} = −{n(dI_)}",
       f"Check: ΔY = 4 × (100 − {n(dI_)}) = {inr(Y1D-Y0D)}"],
      "ΔI = −d · Δr", "Crowding-out in investment (40) is multiplied into the output shortfall (160).", kind="case", group=GD)
    dMn = 180
    Y2D, r2D = solve(Ais, sis, (MsD + dMn) / PD / kD, slm)
    Yn, rn = solve(Ais, sis, (MsD / PD + dMn) / kD, slm)
    Yh, rh = solve(Ais, sis, y0lm + dMn / PD, slm)
    q("equilibrium-in-goods", "L4", stemD + f"**Q.** Instead of the fiscal change, the central bank raises the nominal money supply by {inr(dMn)} (P stays 1.2). The new equilibrium is:",
      fmt(Y2D, r2D),
      [(fmt(Yn, rn), "nominal increase not deflated by P"),
       (fmt(Yh, rh), "LM shift not divided by the income coefficient 0.5"),
       (fmt(Y0D + (dMn / PD) / kD, r0D), "income rises by full LM shift at unchanged r")],
      [f"Real money rises by {dMn}/1.2 = {n(dMn/PD)} ⇒ LM shifts right by {n(dMn/PD)}/0.5 = {n(dMn/PD/kD)}",
       f"New LM: Y = {inr(y0lm + dMn/PD/kD)} + 300r", f"Solve: r = {n(r2D)}%, Y = {inr(Y2D)}"],
      "LM shift = Δ(M/P)/k", "Falling r moves the economy down the IS curve.", kind="case", group=GD)

    # ======================= L4 case E (money supply) =======================
    GE = "ECO-MONEY-CASE-E"
    rowsE = [("Currency with the public", 30.0), ("Cash in hand with banks", 2.0), ("Bankers' deposits with the central bank", 8.0),
             ("'Other' deposits with the central bank", 0.5), ("Demand deposits of the public with banks", 25.0),
             ("Time deposits of the public with banks", 110.0), ("Savings deposits with post-office savings banks", 3.0),
             ("Total post-office deposits (excluding NSCs)", 12.0)]
    cp, cb, bd, od, dd, td, posb, tpo = [x[1] for x in rowsE]
    M0 = cp + cb + bd + od; M1 = cp + dd + od; M3 = M1 + td; M4 = M3 + tpo
    stemE = ("**Case — Central Bank of Rivasa.** Monetary data at end-March (₹ lakh crore), compiled on the same definitions as RBI's traditional aggregates:\n\n" +
             tbl(["Item", "₹ lakh crore"], [(a, n(b, 1)) for a, b in rowsE]) + "\n\n")
    L = lambda x: f"₹{n(x,1)} lakh crore"
    q("monetary-base", "L4", stemE + "**Q.** Reserve money (M0) is:",
      L(M0),
      [(L(M0 - cb), "cash with banks excluded from currency in circulation"),
       (L(M0 - od), "'other' deposits with the central bank omitted"),
       (L(cp + dd + bd + od), "public's demand deposits used in place of bank cash")],
      [f"Currency in circulation = 30.0 + 2.0 = 32.0", f"M0 = 32.0 + 8.0 + 0.5 = {n(M0,1)}"],
      "M0 = CiC + Bankers' deposits + Other deposits", "Vault cash belongs in M0.", kind="case", group=GE, verify_fact=True, ref=RBIM)
    q("money-supply-measures", "L4", stemE + "**Q.** Narrow money (M1) is:",
      L(M1),
      [(L(M1 + cb), "cash with banks added (it is not with the public)"),
       (L(M1 - od), "'other' deposits with the central bank omitted"),
       (L(M1 + posb), "post-office savings deposits added — that is M2")],
      [f"M1 = 30.0 + 25.0 + 0.5 = {n(M1,1)}"],
      "M1 = Currency with public + Demand deposits + Other deposits with CB", "Currency with public, not currency in circulation.",
      kind="case", group=GE, verify_fact=True, ref=RBIM)
    q("money-supply-measures", "L4", stemE + "**Q.** Broad money (M3) is:",
      L(M3),
      [(L(M3 + posb), "post-office savings deposits added"),
       (L(M4), "total post-office deposits added — that is M4"),
       (L(M3 - dd), "demand deposits left out")],
      [f"M3 = M1 + time deposits = {n(M1,1)} + 110.0 = {n(M3,1)}"],
      "M3 = M1 + Time deposits with banks", "Post-office deposits never enter M3.", kind="case", group=GE, verify_fact=True, ref=RBIM)
    q("money-multiplier", "L4", stemE + "**Q.** The broad-money multiplier (M3 ÷ M0) is approximately:",
      n(M3 / M0, 2),
      [(n(M1 / M0, 2), "narrow money used in the numerator"),
       (n(M3 / cp, 2), "currency with public used as the base"),
       (n(M3 / (cb + bd), 2), "bank reserves alone used as the base")],
      [f"m = {n(M3,1)} ÷ {n(M0,1)} = {n(M3/M0,2)}"],
      "m = M3/M0", "Base = the whole of reserve money.", kind="case", group=GE)
