"""Part 3: Ind AS 16/36/105/113/21, consolidation, control/NCI, ESOP, sweat equity."""
from acc_common import S, R, inr, pct, ar, stmt, match, table


def add_all(B):
    # ================= Ind AS 16 =================
    B.add(micro=S("ind-as-16-"), level="L1",
          stem="Under Ind AS 16, if an entity chooses the revaluation model for an item of property, plant and equipment:",
          correct="The entire class of PPE to which that item belongs must be revalued",
          wrongs=[("Only that item is revalued; other items of the class stay at cost", "cherry-picking items is prohibited"),
                  ("All PPE of the entity, of every class, must be revalued", "the choice operates class by class"),
                  ("Revaluation gains are credited to profit or loss", "gains go to OCI / revaluation surplus")],
          steps=["Ind AS 16 para 29/36: accounting policy (cost or revaluation) applied to an entire class of PPE."],
          formula="Ind AS 16 para 36", trap="Selective revaluation would allow a mix of costs and values within a class.",
          kind="conceptual", ref="Ind AS 16 paras 29, 36")

    cst, dism, yrs, dr = 5000000, 800000, 10, 0.10
    pv = dism / (1 + dr) ** yrs
    init = cst + pv
    dep1 = init / yrs
    unw = pv * dr
    tot = dep1 + unw
    assert 308000 < pv < 309000 and round(tot) == 561687
    B.add(micro=S("ind-as-16-"), level="L3",
          stem=(f"On 1 April 2025 an oil company installs a rig at a cost of {R(cst)}. It is legally obliged to dismantle it at the end of its "
                f"{yrs}-year life; the dismantling cost then is estimated at {R(dism)}. The appropriate pre-tax discount rate is {pct(dr,0)}. "
                "Using SLM with nil residual value, the total charge to profit or loss for FY 2025-26 (depreciation plus unwinding) is (nearest rupee):"),
          correct=R(tot),
          wrongs=[(R((cst + dism) / yrs), "undiscounted dismantling cost capitalised; no unwinding"),
                  (R(dep1), "unwinding of discount on the provision omitted"),
                  (R(cst / yrs), "decommissioning cost not capitalised at all")],
          steps=[f"PV of dismantling = {inr(dism)} ÷ 1.10^10 = {inr(pv)}",
                 f"Cost of rig = {inr(cst)} + {inr(pv)} = {inr(init)}",
                 f"Depreciation = {inr(init)} ÷ 10 = {inr(dep1)}; unwinding = {inr(pv)} × 10% = {inr(unw)}",
                 f"Total = {inr(tot)}"],
          formula="Cost includes PV of decommissioning; finance cost = provision × discount rate",
          trap="Unwinding of the provision is a finance cost every year.", ref="Ind AS 16 para 16(c); Ind AS 37 para 45, 60")

    ca_g, fv_g, cash = 400000, 520000, 30000
    B.add(micro=S("ind-as-16-"), level="L2",
          stem=(f"A company exchanges an old machine (carrying amount {R(ca_g)}, fair value {R(fv_g)}) plus cash of {R(cash)} for a new machine. "
                "The exchange has commercial substance and fair values are reliably measurable. The new machine is recognised at:"),
          correct=R(fv_g + cash),
          wrongs=[(R(ca_g + cash), "carrying-amount basis used (applies only without commercial substance)"),
                  (R(fv_g), "cash paid ignored"),
                  (R(fv_g - cash), "cash paid deducted instead of added")],
          steps=[f"Cost = FV of asset given up + cash paid = {inr(fv_g)} + {inr(cash)} = {inr(fv_g+cash)}",
                 f"Gain on derecognition = {inr(fv_g)} − {inr(ca_g)} = {inr(fv_g-ca_g)} to P&L"],
          formula="Ind AS 16 para 24–26", trap="Commercial substance → fair value measurement.", ref="Ind AS 16 paras 24–26")

    # ================= Ind AS 105 standalone =================
    B.add(micro=S("ind-as-105-"), level="L1",
          stem="A non-current asset classified as held for sale under Ind AS 105 is measured at:",
          correct="Lower of carrying amount and fair value less costs to sell; not depreciated",
          wrongs=[("Fair value less costs to sell, even if higher than carrying amount", "gains above carrying amount are not recognised on classification"),
                  ("Carrying amount, with depreciation continuing until the date of sale", "depreciation stops on classification"),
                  ("Value in use, with depreciation continuing until the date of sale", "value in use is an Ind AS 36 concept")],
          steps=["Ind AS 105 para 15: lower of carrying amount and FVLCTS; para 25: no depreciation while held for sale."],
          formula="Ind AS 105 paras 15, 25", trap="Depreciation stops even though the asset is still in use.", kind="conceptual",
          ref="Ind AS 105 paras 15, 25")

    # ---- Case C5: Orion ----
    g = "ACC-C5-ORION"
    c0, life, fv1, cts1, fv2, cts2 = 4000000, 8, 2400000, 100000, 2550000, 120000
    d_yr = c0 / life
    ca_hfs = c0 - d_yr * 2.5
    imp = ca_hfs - (fv1 - cts1)
    fvl2 = fv2 - cts2
    rev = min(fvl2 - (fv1 - cts1), imp)
    ca_end = fv1 - cts1 + rev
    assert (d_yr, ca_hfs, imp, fvl2, ca_end) == (500000, 2750000, 450000, 2430000, 2430000)
    case = (f"**Case — Orion Plastics Ltd.** A moulding machine was bought on 1 April 2023 for {R(c0)} (life {life} years, SLM, nil residual; cost model). "
            f"On 1 October 2025 the board committed to a plan to sell it; the machine was available for immediate sale in its present condition and "
            f"a sale within twelve months was highly probable. On that date its fair value was {R(fv1)} and costs to sell {R(cts1)}. "
            f"At 31 March 2026 (year-end), still unsold, fair value was {R(fv2)} and costs to sell {R(cts2)}.\n\n")
    B.add(micro=S("ind-as-16-"), level="L4", group=g, stem=case + "Depreciation on the machine for FY 2025-26 is:",
          correct=R(d_yr / 2),
          wrongs=[(R(d_yr), "depreciation continued for the full year despite classification"),
                  ("Nil", "depreciation stopped from the start of the year of classification"),
                  (R(d_yr / 2 + imp), "impairment on classification added to depreciation")],
          steps=[f"Annual depreciation = {inr(c0)} ÷ 8 = {inr(d_yr)}", f"Charged for April–September 2025 only = {inr(d_yr/2)}"],
          formula="Depreciate until the date of classification as held for sale", trap="Depreciation ceases on classification, not at year-end.")
    B.add(micro=S("ind-as-105-"), level="L4", group=g, stem=case + "The impairment loss recognised on classification as held for sale is:",
          correct=R(imp),
          wrongs=[(R(ca_hfs - fv1), "costs to sell ignored"),
                  (R(c0 - d_yr * 2 - (fv1 - cts1)), "carrying amount taken at 1 April 2025 (six months' depreciation missed)"),
                  ("Nil", "asset retained at carrying amount since it is still in use")],
          steps=[f"Carrying amount at 1-10-2025 = {inr(c0)} − 2.5 × {inr(d_yr)} = {inr(ca_hfs)}",
                 f"FVLCTS = {inr(fv1)} − {inr(cts1)} = {inr(fv1-cts1)}", f"Impairment = {inr(imp)}"],
          formula="Impairment = Carrying amount − FVLCTS (if lower)", trap="Update the carrying amount to the classification date first.")
    B.add(micro=S("ind-as-105-"), level="L4", group=g, stem=case + "The carrying amount of the machine at 31 March 2026 is:",
          correct=R(ca_end),
          wrongs=[(R(fv1 - cts1), "subsequent increase in FVLCTS not recognised"),
                  (R(fv2), "measured at fair value without costs to sell"),
                  (R(ca_hfs - d_yr / 2), "Ind AS 105 ignored; depreciation simply continued")],
          steps=[f"FVLCTS at year-end = {inr(fv2)} − {inr(cts2)} = {inr(fvl2)}",
                 f"Gain {inr(fvl2 - (fv1-cts1))} recognised — within cumulative impairment {inr(imp)}",
                 f"Carrying amount = {inr(ca_end)}"],
          formula="Subsequent gain recognised up to cumulative impairment previously recognised", trap="Reversal is capped by cumulative impairment, not by fair value.",
          ref="Ind AS 105 paras 20–21")
    stmt(B, S("ind-as-105-"), "L4", case + "Consider the following statements:",
         ["The machine is presented separately from other assets in the balance sheet.",
          "Had the sale been expected only after 18 months with no events beyond the entity's control, the machine could not be classified as held for sale.",
          "Had the board instead decided to abandon (scrap) the machine, it would be classified as held for sale."],
         [1, 2], [([1, 3], "treats abandonment as held for sale"), ([2, 3], "rejects separate presentation"),
                  ([1, 2, 3], "treats abandonment as held for sale")],
         ["1: Ind AS 105 para 38 — separate presentation.", "2: sale expected within one year is a classification criterion.",
          "3: assets to be abandoned are not held for sale (para 13)."],
         "Abandonment is recovery through use, not sale.", group=g, ref="Ind AS 105 paras 7–8, 13, 38")

    # ================= Ind AS 36 =================
    B.add(micro=S("ind-as-36-"), level="L1",
          stem="Under Ind AS 36, the recoverable amount of an asset is:",
          correct="The higher of its fair value less costs of disposal and its value in use",
          wrongs=[("The lower of its fair value less costs of disposal and its value in use", "confuses with a 'lower of' rule"),
                  ("Its value in use only", "fair value less costs of disposal is also considered"),
                  ("Its net realisable value", "an inventory (Ind AS 2) measure")],
          steps=["Recoverable amount = max(FVLCD, VIU); impairment = carrying amount − recoverable amount if positive."],
          formula="Ind AS 36 para 18", trap="An entity would pick the better of selling or using.", kind="conceptual", ref="Ind AS 36 para 18")

    ca_i, fvlcd_i, viu_i = 1200000, 950000, 1040000
    B.add(micro=S("ind-as-36-"), level="L2",
          stem=(f"An asset has a carrying amount of {R(ca_i)}, fair value less costs of disposal of {R(fvlcd_i)} and value in use of {R(viu_i)}. "
                "The impairment loss is:"),
          correct=R(ca_i - max(fvlcd_i, viu_i)),
          wrongs=[(R(ca_i - min(fvlcd_i, viu_i)), "lower of the two used as recoverable amount"),
                  (R(viu_i - fvlcd_i), "difference between VIU and FVLCD taken"),
                  ("Nil", "value in use compared with FVLCD instead of carrying amount")],
          steps=[f"Recoverable amount = max({inr(fvlcd_i)}, {inr(viu_i)}) = {inr(viu_i)}",
                 f"Impairment = {inr(ca_i)} − {inr(viu_i)} = {inr(ca_i-viu_i)}"],
          formula="Impairment = CA − max(FVLCD, VIU)", trap="Use the higher measure.")

    cfs, dr2, disp, ca2, fvlcd2 = [400000, 500000, 300000], 0.10, 100000, 1150000, 980000
    viu = sum(cf / (1 + dr2) ** (i + 1) for i, cf in enumerate(cfs)) + disp / (1 + dr2) ** 3
    viu_nod = viu - disp / (1 + dr2) ** 3
    imp2 = ca2 - max(viu, fvlcd2)
    assert round(viu) == 1077385 and round(imp2) == 72615
    B.add(micro=S("ind-as-36-"), level="L3",
          stem=("For a specialised machine (carrying amount " + R(ca2) + ", fair value less costs of disposal " + R(fvlcd2) + ") management's approved budgets show:\n\n" +
                table(["Year", "Net cash inflow from use (₹)"], [[str(i + 1), inr(cf)] for i, cf in enumerate(cfs)]) +
                f"\n\nNet disposal proceeds at the end of year 3 are expected to be {R(disp)}. The pre-tax discount rate is {pct(dr2,0)}. "
                "The impairment loss (nearest rupee) is:"),
          correct=R(imp2),
          wrongs=[(R(ca2 - fvlcd2), "FVLCD used though value in use is higher"),
                  (R(ca2 - viu_nod), "terminal disposal proceeds left out of value in use"),
                  ("Nil", "undiscounted cash flows compared with carrying amount")],
          steps=[f"PV of inflows = 3,63,636 + 4,13,223 + 2,25,394 = {inr(viu_nod)}",
                 f"PV of disposal = {inr(disp)} ÷ 1.331 = {inr(disp/1.331)}; VIU = {inr(viu)}",
                 f"Recoverable amount = max({inr(viu)}, {inr(fvlcd2)}) = {inr(viu)}",
                 f"Impairment = {inr(ca2)} − {inr(viu)} = {inr(imp2)}"],
          formula="VIU = Σ CFt/(1+r)^t + terminal net disposal/(1+r)^n", trap="VIU includes net cash flows on disposal at the end of useful life.",
          ref="Ind AS 36 paras 30–39")

    ar(B, S("ind-as-36-"), "L3",
       "An impairment loss recognised for goodwill is not reversed in a subsequent period even if the recoverable amount of the CGU increases.",
       "Any subsequent increase in the recoverable amount of goodwill is likely to be an increase in internally generated goodwill, which cannot be recognised.",
       "both_explains",
       ["Ind AS 36 para 124 prohibits reversal of goodwill impairment.",
        "Para 125 gives the reason: the increase is likely internally generated goodwill (Ind AS 38 prohibits recognition). R explains A."],
       "Reversal is allowed for other assets, capped at depreciated historical carrying amount.", ref="Ind AS 36 paras 124–125")

    # ---- Case C4: Vistara CGU ----
    g = "ACC-C4-VISTARA"
    gw, bld, plt, pat, ra, pat_floor = 200000, 600000, 400000, 200000, 1000000, 180000
    tot_ca = gw + bld + plt + pat
    loss = tot_ca - ra
    rem = loss - gw
    alloc = {k: rem * v / (bld + plt + pat) for k, v in (("b", bld), ("p", plt), ("t", pat))}
    pat_loss = min(alloc["t"], pat - pat_floor)
    excess = alloc["t"] - pat_loss
    b_loss = alloc["b"] + excess * bld / (bld + plt)
    p_loss = alloc["p"] + excess * plt / (bld + plt)
    assert loss == 400000 and pat_loss == 20000 and round(b_loss) == 108000 and round(p_loss) == 72000
    case = ("**Case — Vistara Foods Ltd.** A cash-generating unit (CGU) acquired in a business combination has these carrying amounts at 31 March 2026:\n\n" +
            table(["Asset", "Carrying amount (₹)"], [["Goodwill allocated", inr(gw)], ["Building", inr(bld)], ["Plant", inr(plt)],
                                                     ["Patent", inr(pat)], ["Total", inr(tot_ca)]]) +
            f"\n\nThe recoverable amount of the CGU is {R(ra)}. The patent's fair value less costs of disposal is reliably determined at {R(pat_floor)}; "
            "the recoverable amounts of the building and plant individually cannot be determined.\n\n")
    B.add(micro=S("ind-as-36-"), level="L4", group=g, stem=case + "The impairment loss of the CGU and the part allocated to goodwill are:",
          correct=f"{R(loss)}, of which {R(gw)} to goodwill",
          wrongs=[(f"{R(loss)}, of which {R(loss*gw/tot_ca)} to goodwill", "loss allocated pro rata to all assets including goodwill"),
                  (f"{R(tot_ca - gw - ra)}, all to goodwill", "goodwill excluded from the CGU carrying amount"),
                  (f"{R(loss)}, none to goodwill", "goodwill spared; loss spread over other assets only")],
          steps=[f"Loss = {inr(tot_ca)} − {inr(ra)} = {inr(loss)}", f"First reduce goodwill fully: {inr(gw)}; balance {inr(rem)} to other assets pro rata"],
          formula="Ind AS 36 para 104: goodwill first, then pro rata", trap="Goodwill absorbs the loss first.")
    B.add(micro=S("ind-as-36-"), level="L4", group=g, stem=case + "The carrying amount of the patent after allocation of the impairment loss is:",
          correct=R(pat - pat_loss),
          wrongs=[(R(pat - alloc["t"]), "floor of fair value less costs of disposal ignored"),
                  (R(pat), "patent excluded from allocation"),
                  (R(pat - loss * pat / tot_ca), "pro rata allocation including goodwill")],
          steps=[f"Pro rata share = {inr(rem)} × 2/12 = {inr(alloc['t'])}",
                 f"Cannot reduce below FVLCD {inr(pat_floor)} → loss limited to {inr(pat_loss)}; carrying amount {inr(pat-pat_loss)}"],
          formula="No asset below the highest of FVLCD, VIU and zero", trap="The floor applies asset by asset.", ref="Ind AS 36 para 105")
    B.add(micro=S("ind-as-36-"), level="L4", group=g, stem=case + "The carrying amount of the building after allocation of the impairment loss is:",
          correct=R(bld - b_loss),
          wrongs=[(R(bld - alloc["b"]), "patent's unabsorbed share not reallocated"),
                  (R(bld - loss * bld / tot_ca), "pro rata allocation including goodwill"),
                  (R(bld - alloc["b"] - excess), "patent's unabsorbed share loaded entirely on building")],
          steps=[f"Initial share = {inr(rem)} × 6/12 = {inr(alloc['b'])}",
                 f"Patent's unabsorbed {inr(excess)} reallocated 6:4 → building +{inr(excess*0.6)}",
                 f"Building loss = {inr(b_loss)}; carrying amount = {inr(bld-b_loss)}"],
          formula="Unallocated amount spread pro rata over other assets of the CGU", trap="Reallocation goes to remaining assets in their carrying-amount ratio.",
          ref="Ind AS 36 para 105")
    stmt(B, S("ind-as-36-"), "L4", case + "If next year the CGU's recoverable amount rises to ₹12,00,000, consider:",
         ["The impairment loss on goodwill may be reversed to the extent of the increase.",
          "Any reversal for the building cannot raise it above the carrying amount it would have had (net of depreciation) had no impairment been recognised.",
          "The current year's impairment loss (cost model) is recognised in profit or loss."],
         [2, 3], [([1, 2], "allows goodwill reversal"), ([1, 3], "allows goodwill reversal and ignores the reversal cap"),
                  ([1, 2, 3], "allows goodwill reversal")],
         ["1 false — goodwill impairment is never reversed.", "2 true — para 117 cap.", "3 true — para 60."],
         "Reversals are capped and never apply to goodwill.", group=g, ref="Ind AS 36 paras 60, 117, 124")

    # ================= Ind AS 113 =================
    stmt(B, S("ind-as-113-"), "L2", "Under Ind AS 113, which of the following are Level 2 inputs?",
         ["Quoted price in an active market for an identical listed share held by the entity.",
          "Quoted price in an active market for a similar (not identical) bond.",
          "Observable interest-rate yield curves at commonly quoted intervals used to value a swap.",
          "The entity's own projections of cash flows used to value an unlisted equity investment."],
         [2, 3], [([1, 2, 3], "classifies an identical-asset quoted price as Level 2"),
                  ([2, 3, 4], "classifies unobservable own projections as Level 2"),
                  ([3], "misses that quoted prices for similar assets are Level 2")],
         ["1: Level 1.", "2 and 3: observable inputs other than Level 1 quoted prices — Level 2.", "4: unobservable — Level 3."],
         "Similar ≠ identical; own data = Level 3.", question="Select the correct answer:", ref="Ind AS 113 paras 76–90")

    B.add(micro=S("ind-as-113-"), level="L2",
          stem="Under Ind AS 113, the fair value of a non-financial asset is measured by considering:",
          correct="Its highest and best use by market participants, whatever the entity intends",
          wrongs=[("The entity's intended current use of the asset only, as decided by management", "fair value is market-participant based"),
                  ("The transaction price the entity paid to acquire it (an entry price)", "fair value is an exit price"),
                  ("The value in use of the asset to the entity, based on its own cash flows", "an entity-specific Ind AS 36 measure")],
          steps=["Ind AS 113 para 27: highest and best use — physically possible, legally permissible, financially feasible — from market participants' perspective.",
                 "Current use is presumed HBU unless market factors suggest otherwise."],
          formula="Ind AS 113 paras 27–30", trap="Fair value is an exit price from the market's viewpoint.", kind="conceptual",
          ref="Ind AS 113 paras 24, 27–30")

    pA, tA, trA, pB, tB, trB = 26, 3, 2, 25, 1, 2
    B.add(micro=S("ind-as-113-"), level="L3",
          stem=("An asset is traded in two markets:\n\n" +
                table(["", "Market A", "Market B"], [["Price (₹)", pA, pB], ["Transaction costs (₹)", tA, tB], ["Transport costs to market (₹)", trA, trB]]) +
                "\n\nMarket A has the greatest volume and level of activity for the asset. Its fair value per unit under Ind AS 113 is:"),
          correct=f"₹{pA - trA}",
          wrongs=[(f"₹{pA - tA - trA}", "transaction costs deducted"),
                  (f"₹{pB - trB}", "most advantageous market used although a principal market exists"),
                  (f"₹{pA}", "transport costs not deducted")],
          steps=["Principal market (A) governs.", f"FV = price − transport = {pA} − {trA} = ₹{pA-trA}; transaction costs are not an attribute of the asset."],
          formula="FV = price in principal market − transport costs", trap="Transaction costs are used only to identify the most advantageous market.",
          ref="Ind AS 113 paras 16, 25–26")

    # ================= Ind AS 21 =================
    B.add(micro=S("ind-as-21-"), level="L1",
          stem="Under Ind AS 21, an entity's functional currency is:",
          correct="Currency of the primary economic environment in which the entity operates",
          wrongs=[("The currency in which its financial statements are presented to users", "that is the presentation currency"),
                  ("Always the currency of the country in which the entity is incorporated", "not automatically"),
                  ("The currency in which most of the entity's borrowings are denominated", "financing currency is only a secondary indicator")],
          steps=["Primary indicators: currency influencing sales prices and costs; secondary: financing and retention of receipts."],
          formula="Ind AS 21 paras 8–12", trap="Functional and presentation currency may differ.", kind="conceptual", ref="Ind AS 21 para 8")

    adv, r_adv, r_gr, r_ye = 10000, 82.0, 83.0, 84.0
    B.add(micro=S("ind-as-21-"), level="L2",
          stem=(f"On 1 February an Indian company pays a non-refundable advance of USD {inr(adv)} to a foreign supplier (₹{r_adv:.0f}/USD). "
                f"The goods (fully covered by the advance) are received on 1 March (₹{r_gr:.0f}/USD) and remain in stock at the year-end 31 March (₹{r_ye:.0f}/USD). "
                "The inventory is carried at:"),
          correct=R(adv * r_adv),
          wrongs=[(R(adv * r_gr), "translated at the date goods were received"),
                  (R(adv * r_ye), "non-monetary inventory retranslated at closing rate"),
                  (f"{R(adv*r_adv)} plus an exchange loss of {R(adv*(r_gr-r_adv))} in P&L", "advance treated as a monetary item")],
          steps=["A non-refundable advance is a non-monetary asset; the date of transaction is the date of the advance.",
                 f"Inventory = {inr(adv)} × {r_adv:.0f} = {inr(adv*r_adv)}; no exchange difference."],
          formula="Appendix B to Ind AS 21 — advance consideration", trap="Non-monetary items are not retranslated.",
          ref="Ind AS 21 para 23, Appendix B")

    usd_c, r_c, usd_n, r_n = 10000, 80.0, 10400, 76.0
    ca_inr = min(usd_c * r_c, usd_n * r_n)
    assert ca_inr == 790400
    B.add(micro=S("ind-as-21-"), level="L3",
          stem=(f"An Indian entity (functional currency INR) holds imported inventory costing USD {inr(usd_c)}, bought when the rate was ₹{r_c:.0f}/USD. "
                f"At the reporting date its net realisable value is USD {inr(usd_n)} and the closing rate is ₹{r_n:.0f}/USD. The inventory is carried at:"),
          correct=R(ca_inr),
          wrongs=[(R(usd_c * r_c), "cost and NRV compared in USD, so no write-down"),
                  (R(usd_n * r_c), "NRV translated at the historical rate"),
                  (R(usd_c * r_n), "cost retranslated at the closing rate")],
          steps=[f"Cost in INR (historical rate) = {inr(usd_c*r_c)}", f"NRV in INR (closing rate) = {inr(usd_n*r_n)}",
                 f"Lower = {inr(ca_inr)}; write-down {inr(usd_c*r_c-ca_inr)} even though NRV exceeds cost in USD"],
          formula="Ind AS 21 para 25: compare cost at historical rate with NRV at the rate on the date NRV is determined",
          trap="The comparison is made in the functional currency.", ref="Ind AS 21 para 25")

    # ================= Consolidation =================
    B.add(micro=S("consolidation-when"), level="L1",
          stem="Under Section 129(3) of the Companies Act, 2013, a company having one or more subsidiaries, associates or joint ventures must:",
          correct="Prepare consolidated statements in addition to its standalone statements",
          wrongs=[("Prepare consolidated statements instead of its standalone statements", "CFS are in addition, not a substitute"),
                  ("Prepare consolidated statements only if the company is itself listed", "requirement applies to all such companies (subject to exemptions)"),
                  ("Only attach the subsidiaries' audited accounts to its own accounts", "attachment alone does not satisfy s.129(3)")],
          steps=["s.129(3): CFS of the company and all subsidiaries, associates and JVs, in addition to its own financial statements; plus salient features in Form AOC-1."],
          formula="Companies Act, 2013 s.129(3)", trap="Associates and JVs also trigger CFS.", kind="conceptual",
          verify_fact=True, ref="Companies Act, 2013 s.129(3); Companies (Accounts) Rules, 2014 Rule 5–6")

    stmt(B, S("consolidation-when"), "L2", "Under Ind AS 110, an investor controls an investee when it has:",
         ["Power over the investee.", "Exposure, or rights, to variable returns from its involvement with the investee.",
          "The ability to use its power over the investee to affect the amount of the investor's returns.",
          "Ownership of more than 50% of the equity shares in every case."],
         [1, 2, 3], [([1, 2, 3, 4], "treats majority shareholding as a necessary condition"),
                     ([1, 4], "equates control with power plus majority shares"),
                     ([1, 2], "omits the link between power and returns")],
         ["Control requires all three elements (Ind AS 110 para 7).",
          "Majority shareholding is neither necessary nor always sufficient (de facto control, potential voting rights, agency)."],
         "Control can exist below 50% (de facto control).", question="Select the correct answer:", ref="Ind AS 110 para 7")

    cons, stake, fvna, bvna, nci_fv = 2000000, 0.80, 2200000, 2000000, 500000
    nci = (1 - stake) * fvna
    gwc = cons + nci - fvna
    gwc = round(gwc)
    assert gwc == 240000
    B.add(micro=S("consolidation-when"), level="L3",
          stem=(f"H Ltd acquires {pct(stake,0)} of S Ltd for {R(cons)} in cash. On that date S Ltd's net assets have a book value of {R(bvna)} and a "
                f"fair value (identifiable) of {R(fvna)}. The fair value of the non-controlling interest is {R(nci_fv)}. H Ltd measures NCI at the "
                "proportionate share of identifiable net assets. Goodwill on consolidation is:"),
          correct=R(gwc),
          wrongs=[(R(cons + (1 - stake) * bvna - bvna), "book values used instead of fair values"),
                  (R(cons + nci_fv - fvna), "NCI measured at fair value contrary to the chosen policy"),
                  (f"Capital reserve {R(fvna - cons)}", "consideration compared with 100% of net assets, NCI ignored")],
          steps=[f"NCI = 20% × {inr(fvna)} = {inr(nci)}", f"Goodwill = {inr(cons)} + {inr(nci)} − {inr(fvna)} = {inr(gwc)}"],
          formula="Goodwill = Consideration + NCI − FV of identifiable net assets", trap="The NCI measurement choice changes goodwill.",
          ref="Ind AS 103 paras 19, 32")

    # ================= Control / NCI presentation =================
    B.add(micro=S("control-of-subsidiaries"), level="L1",
          stem="In consolidated financial statements under Ind AS 110, non-controlling interest is presented:",
          correct="Within equity, separately from the equity of the owners of the parent",
          wrongs=[("As a non-current liability, separately from other borrowings", "old 'minority interest as liability' view"),
                  ("Between liabilities and equity as a separate mezzanine line item", "not permitted under Ind AS"),
                  ("Only in the notes to accounts, not on the face of the balance sheet", "must be presented on the face")],
          steps=["Ind AS 110 para 22: NCI within equity, separately from parent owners' equity."],
          formula="Ind AS 110 para 22", trap="NCI is equity of the group.", kind="conceptual", ref="Ind AS 110 para 22")

    post, divs = 300000, 100000
    nci_end = nci + (1 - stake) * (post - divs)
    nci, nci_end = round(nci), round(nci_end)
    assert nci_end == 480000
    B.add(micro=S("control-of-subsidiaries"), level="L3",
          stem=(f"Continuing the above: H Ltd acquired {pct(stake,0)} of S Ltd when S Ltd's identifiable net assets were {R(fvna)} at fair value (NCI at "
                f"proportionate share, {R(nci)}). In the first year after acquisition S Ltd earns profit of {R(post)} and pays a dividend of {R(divs)}. "
                "Ignoring fair-value adjustments' depreciation, NCI in the consolidated balance sheet at the year-end is:"),
          correct=R(nci_end),
          wrongs=[(R(nci + (1 - stake) * post), "dividend paid to NCI not deducted"),
                  (R(nci), "post-acquisition changes not attributed to NCI"),
                  (R(nci - (1 - stake) * divs), "dividend deducted but profit share omitted")],
          steps=[f"NCI share of post-acquisition retained profit = 20% × ({inr(post)} − {inr(divs)}) = {inr((1-stake)*(post-divs))}",
                 f"NCI = {inr(nci)} + {inr((1-stake)*(post-divs))} = {inr(nci_end)}"],
          formula="NCI = NCI at acquisition + NCI% × post-acquisition change in equity", trap="Dividends to NCI reduce NCI.")

    stmt(B, S("control-of-subsidiaries"), "L2", "Under Ind AS 110, consider:",
         ["Profit or loss is attributed to owners of the parent and to NCI, and both amounts are presented.",
          "Total comprehensive income is attributed to NCI even if this results in NCI having a deficit balance.",
          "Changes in a parent's ownership interest that do not result in loss of control are recognised in profit or loss."],
         [1, 2], [([1, 3], "treats a without-loss-of-control change as a P&L event"), ([2, 3], "denies the attribution requirement"),
                  ([1, 2, 3], "treats a without-loss-of-control change as a P&L event")],
         ["1 and 2 true (paras B94).", "3 false — such changes are equity transactions (para 23)."],
         "Partial disposals without loss of control are equity transactions.", ref="Ind AS 110 paras 23, B94")

    # ================= ESOP vesting =================
    B.add(micro=S("esop-vesting"), level="L1",
          stem="Under the Companies (Share Capital and Debentures) Rules, 2014 and SEBI (SBEB & SE) Regulations, 2021, the minimum period between grant and vesting of employee stock options is:",
          correct="One year",
          wrongs=[("Three years", "the lock-in period for sweat equity"),
                  ("Six months", "no such minimum"),
                  ("There is no minimum; it is left to the scheme", "a minimum is prescribed")],
          steps=["Rule 12(6)(a) and SBEB Regulations: minimum vesting period of one year (with limited exceptions such as death/permanent incapacity)."],
          formula="Minimum vesting = 1 year", trap="Do not confuse with the sweat equity lock-in.", kind="conceptual",
          verify_fact=True, ref="Companies (Share Capital and Debentures) Rules, 2014, Rule 12(6)(a); SEBI (SBEB & SE) Regulations, 2021, Reg. 18")

    emp, opt, fvo, vp, lv1, lv2 = 500, 100, 30, 3, 0.20, 0.15
    cum1 = emp * (1 - lv1) * opt * fvo * 1 / vp
    cum2 = emp * (1 - lv2) * opt * fvo * 2 / vp
    exp2 = cum2 - cum1
    assert (cum1, cum2, exp2) == (400000, 850000, 450000)
    B.add(micro=S("esop-vesting"), level="L3",
          stem=(f"On 1 April 2024 a company grants {opt} options each to {emp} employees, vesting after {vp} years of service. Grant-date fair value is "
                f"₹{fvo} per option. At 31 March 2025 it expects {pct(lv1,0)} of employees to leave before vesting; at 31 March 2026 the estimate is revised "
                f"to {pct(lv2,0)}. Under Ind AS 102 the expense for FY 2025-26 is:"),
          correct=R(exp2),
          wrongs=[(R(emp * (1 - lv2) * opt * fvo / vp), "revised estimate applied only to the current year without catch-up"),
                  (R(cum2), "cumulative expense reported as the year's charge"),
                  (R(emp * opt * fvo / vp), "expected leavers ignored")],
          steps=[f"Cumulative to 31-3-2025 = 400 × 100 × 30 × 1/3 = {inr(cum1)}",
                 f"Cumulative to 31-3-2026 = 425 × 100 × 30 × 2/3 = {inr(cum2)}", f"Expense FY 25-26 = {inr(exp2)}"],
          formula="Expense = Cumulative (revised estimate × FV × elapsed/vesting) − previously recognised",
          trap="Service-condition estimates are trued up cumulatively.", ref="Ind AS 102 paras 19–20")

    stmt(B, S("esop-vesting"), "L2", "Under Ind AS 102 for equity-settled options, consider:",
         ["If options vest but later lapse unexercised, the expense already recognised is not reversed (a transfer within equity is permitted).",
          "For a market-based performance condition, expense is not reversed merely because the market condition is not met.",
          "Grant-date fair value is remeasured at each reporting date."],
         [1, 2], [([1, 3], "remeasures equity-settled awards"), ([2, 3], "reverses expense on lapse"),
                  ([1, 2, 3], "remeasures equity-settled awards")],
         ["1 true (para 23).", "2 true (para 21).", "3 false — equity-settled awards are fixed at grant date."],
         "Only cash-settled awards are remeasured.", ref="Ind AS 102 paras 16–23")

    # ================= ESOP valuation =================
    B.add(micro=S("esop-valuation"), level="L1",
          stem="The intrinsic value of an employee stock option is:",
          correct="The excess of the market price of the share over the exercise price",
          wrongs=[("The fair value of the option determined by an option-pricing model", "fair value includes time value"),
                  ("The exercise price payable by the employee under the option", "exercise price is an input only"),
                  ("The market price of the underlying share on the vesting date", "ignores exercise price")],
          steps=["Intrinsic value = Market price − Exercise price (if positive).", "Fair value = intrinsic value + time value."],
          formula="IV = P − X", trap="An at-the-money option has zero intrinsic value but positive fair value.", kind="conceptual")

    n_o, xp, mp, fvbs, vy = 10000, 150, 200, 72, 4
    B.add(micro=S("esop-valuation"), level="L2",
          stem=(f"{inr(n_o)} options are granted at an exercise price of ₹{xp} when the share price is ₹{mp}. The Black-Scholes fair value is ₹{fvbs} per "
                f"option; vesting period {vy} years, all expected to vest. The annual expense under the fair value method is:"),
          correct=R(n_o * fvbs / vy),
          wrongs=[(R(n_o * (mp - xp) / vy), "intrinsic value method used"),
                  (R(n_o * fvbs), "entire fair value expensed in year 1"),
                  (R(n_o * mp / vy), "share price used as the option's value")],
          steps=[f"Total fair value = {inr(n_o)} × {fvbs} = {inr(n_o*fvbs)}", f"Per year = {inr(n_o*fvbs)} ÷ {vy} = {inr(n_o*fvbs/vy)}"],
          formula="Annual expense = Options × FV ÷ Vesting years", trap="Intrinsic value omits time value.")

    B.add(micro=S("esop-valuation"), level="L3",
          stem="Which of the following is NOT an input to the Black-Scholes value of a single employee option under Ind AS 102?",
          correct="Expected rate of employee attrition before vesting",
          wrongs=[("Expected volatility of the share price", "a core model input"),
                  ("Expected dividends on the shares", "reduces option value — an input"),
                  ("Risk-free interest rate for the option's expected term", "a core model input")],
          steps=["Option-pricing inputs: share price, exercise price, expected term, volatility, dividends, risk-free rate (Ind AS 102 B6).",
                 "Service-condition forfeitures affect the NUMBER of options expected to vest, not the per-option fair value."],
          formula="Ind AS 102 para 19–20, B6", trap="Vesting conditions other than market conditions are not in the fair value.",
          kind="conceptual", ref="Ind AS 102 paras 19, B6")

    # ================= Sweat equity =================
    B.add(micro=S("sweat-equity"), level="L1",
          stem="Under Section 2(88) of the Companies Act, 2013, sweat equity shares are shares issued by a company to its directors or employees:",
          correct="At a discount or for non-cash consideration, for know-how, IPR or value additions",
          wrongs=[("Only for cash at a premium, under an approved employee stock option scheme", "describes ESOP-style issues, not sweat equity"),
                  ("Free of cost, by capitalising free reserves or securities premium", "that is a bonus issue"),
                  ("To existing shareholders in proportion to their holdings, with renunciation", "that is a rights issue")],
          steps=["s.2(88) defines sweat equity; s.54 lays down conditions (special resolution, class of shares already issued, etc.)."],
          formula="Companies Act s.2(88), s.54", trap="Discount or non-cash consideration is the defining feature.", kind="conceptual",
          verify_fact=True, ref="Companies Act, 2013 ss.2(88), 54")

    stmt(B, S("sweat-equity"), "L2", "Regarding sweat equity shares under Section 54 and Rule 8 of the Share Capital Rules:",
         ["The issue must be authorised by a special resolution of the company.",
          "Sweat equity shares are locked in for three years from the date of allotment.",
          "Sweat equity shares can be issued only for cash at a premium."],
         [1, 2], [([1, 3], "misreads sweat equity as a cash issue"), ([2, 3], "misses the special resolution"),
                  ([1, 2, 3], "misreads sweat equity as a cash issue")],
         ["1 true — s.54(1)(a).", "2 true — Rule 8(5).", "3 false — issued at a discount or for non-cash consideration."],
         "Sweat equity rewards know-how or value addition, not cash.", verify_fact=True,
         ref="Companies Act s.54; Companies (Share Capital and Debentures) Rules, 2014, Rule 8")

    sh, fvs, fmv = 10000, 10, 85
    B.add(micro=S("sweat-equity"), level="L3",
          stem=(f"A company issues {inr(sh)} sweat equity shares of ₹{fvs} each to its technical director, without cash, in recognition of services. "
                f"The fair value per share determined by a registered valuer is ₹{fmv}. The services do not qualify as an asset. The accounting entry credits securities premium by:"),
          correct=R(sh * (fmv - fvs)),
          wrongs=[(R(sh * fmv), "entire fair value credited to premium, nothing to share capital"),
                  (R(sh * fvs), "face value credited to premium"),
                  ("Nil (share capital credited at face value only)", "fair value of services ignored")],
          steps=[f"Expense (employee benefits) Dr {inr(sh*fmv)}", f"Share capital Cr {inr(sh*fvs)}; Securities premium Cr {inr(sh*(fmv-fvs))}"],
          formula="Sweat equity at fair value: capital at face value, excess to securities premium",
          trap="The fair value is expensed when the services are not an asset.", ref="Rule 8(13) Share Capital Rules; Ind AS 102")
