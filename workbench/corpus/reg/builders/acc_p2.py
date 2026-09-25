"""Part 2: AS 2, AS 10, depreciation, AS 9, AS 13, AS 11, AS 22, leases, provisions, commitments."""
from acc_common import S, R, inr, pct, ar, stmt, match, table


def annuity(r, n):
    return (1 - (1 + r) ** -n) / r


def add_all(B):
    # ================= AS 2 =================
    B.add(micro=S("as-2-"), level="L1",
          stem="Under AS 2, which of the following is INCLUDED in the cost of inventories?",
          correct="Fixed production overheads allocated on the basis of normal capacity",
          wrongs=[("Abnormal amounts of wasted materials and labour", "abnormal wastage is expensed"),
                  ("Storage costs after goods are completed, not necessary for the production process", "post-production storage is excluded"),
                  ("Selling and distribution costs", "selling costs are excluded")],
          steps=["Cost of inventories = purchase + conversion + other costs to bring to present location and condition.",
                 "Fixed production overhead is included, allocated on normal capacity; abnormal wastage, non-production storage, admin (non-production) and selling costs are excluded."],
          formula="AS 2 para 6–13", trap="Storage is included only when necessary in the production process before a further stage.",
          kind="conceptual", ref="AS 2 (revised) — cost of inventories")

    cost_u, esp, sc, units = 500, 540, 60, 1200
    nrv = esp - sc
    B.add(micro=S("as-2-"), level="L2",
          stem=(f"A trader holds {inr(units)} units of an item costing ₹{cost_u} each. The estimated selling price is ₹{esp} per unit and "
                f"estimated costs to sell are ₹{sc} per unit. Closing inventory of this item is valued at:"),
          correct=R(units * min(cost_u, nrv)),
          wrongs=[(R(units * cost_u), "selling costs ignored, so cost appears lower than NRV"),
                  (R(units * esp), "valued at selling price"),
                  (R(units * (cost_u - sc)), "selling costs deducted from cost instead of from selling price")],
          steps=[f"NRV = {esp} − {sc} = ₹{nrv}", f"Lower of cost ₹{cost_u} and NRV ₹{nrv} = ₹{min(cost_u, nrv)}",
                 f"Value = {inr(units)} × {min(cost_u, nrv)} = {inr(units*min(cost_u, nrv))}"],
          formula="Inventory = lower of cost and NRV; NRV = ESP − costs to complete and sell",
          trap="NRV is net of selling costs.")

    ncap, acap, foh, vc, cl = 50000, 40000, 1000000, 60, 8000
    rate_n, rate_a = foh / ncap, foh / acap
    val = cl * (vc + rate_n)
    assert val == 640000
    B.add(micro=S("as-2-"), level="L3",
          stem=(f"Normal capacity of a plant is {inr(ncap)} units a year; owing to a strike only {inr(acap)} units were produced this year. "
                f"Fixed production overheads were {R(foh)} and variable production cost is ₹{vc} per unit. There was no opening stock and "
                f"{inr(cl)} units remain in closing stock (NRV well above cost). Under AS 2 the closing stock is valued at:"),
          correct=R(val),
          wrongs=[(R(cl * (vc + rate_a)), "fixed overhead absorbed on actual (low) production"),
                  (R(cl * vc), "fixed production overhead excluded (marginal costing)"),
                  (R(cl * vc + foh * cl / (cl + acap)), "fixed overhead spread over production plus closing stock")],
          steps=[f"Fixed OH rate on normal capacity = {inr(foh)} ÷ {inr(ncap)} = ₹{rate_n:.0f}",
                 f"Unit cost = {vc} + {rate_n:.0f} = ₹{vc+rate_n:.0f}",
                 f"Closing stock = {inr(cl)} × {vc+rate_n:.0f} = {inr(val)}; unallocated OH ₹{inr(foh - acap*rate_n)} is expensed"],
          formula="Fixed OH allocation rate = Fixed OH ÷ Normal capacity (actual if higher)",
          trap="Low production does not increase the overhead per unit carried in stock.", ref="AS 2 para 9")

    # ---- Case C2: Sunrise ----
    g = "ACC-C2-SUNRISE"
    X_c, X_n, Y_c, Y_n = 320000, 290000, 150000, 120000
    P_acc, stor, spoil, P_nrv = 595000, 20000, 15000, 700000
    Q_c, Q_n = 240000, 210000
    P_c = P_acc - stor - spoil
    assert P_c == 560000
    tot = X_c + Y_n + P_c + Q_n
    assert tot == 1210000
    case = ("**Case — Sunrise Components Ltd.** Inventory at 31 March 2026 (all figures ₹):\n\n" +
            table(["Item", "Cost", "Net realisable value"],
                  [["Raw material X (used only in product P)", inr(X_c), inr(X_n)],
                   ["Raw material Y (used only in product Q)", inr(Y_c), inr(Y_n) + " (= replacement cost)"],
                   ["Finished product P", f"{inr(P_acc)} (accountant's figure)", inr(P_nrv)],
                   ["Finished product Q", inr(Q_c), inr(Q_n)]]) +
            f"\n\nThe accountant's cost of P includes {R(stor)} of warehouse storage after completion (not required by the production "
            f"process) and {R(spoil)} of abnormal spoilage. Product P sells above its cost; product Q sells below its cost.\n\n")
    B.add(micro=S("as-2-"), level="L4", group=g, stem=case + "The cost of finished product P under AS 2 is:",
          correct=R(P_c),
          wrongs=[(R(P_acc), "storage and abnormal spoilage both retained"),
                  (R(P_acc - stor), "abnormal spoilage retained"),
                  (R(P_acc - spoil), "post-completion storage retained")],
          steps=[f"{inr(P_acc)} − storage {inr(stor)} − abnormal spoilage {inr(spoil)} = {inr(P_c)}"],
          formula="AS 2 para 13 exclusions", trap="Both items are period costs.")
    B.add(micro=S("as-2-"), level="L4", group=g, stem=case + "Total inventory to be reported is:",
          correct=R(tot),
          wrongs=[(R(X_n + Y_n + P_c + Q_n), "raw material X written down though P sells above cost"),
                  (R(X_c + Y_n + P_acc + Q_n), "accountant's cost of P used"),
                  (R(X_c + Y_c + P_c + Q_n), "raw material Y kept at cost though Q sells below cost")],
          steps=[f"X: finished P sells above cost → no write-down → {inr(X_c)}",
                 f"Y: Q sells below cost → write down to replacement cost {inr(Y_n)}",
                 f"P: lower of {inr(P_c)} and {inr(P_nrv)} = {inr(P_c)}; Q: {inr(Q_n)}",
                 f"Total = {inr(tot)}"],
          formula="Materials are not written down below cost if the finished products are expected to sell at or above cost",
          trap="The materials exception runs product by product.", ref="AS 2 para 24")
    wd = (Y_c - Y_n) + (Q_c - Q_n)
    B.add(micro=S("as-2-"), level="L4", group=g, stem=case + "The write-down of inventories to net realisable value recognised as an expense is:",
          correct=R(wd),
          wrongs=[(R(wd + (X_c - X_n)), "includes a write-down of material X"),
                  (R(Q_c - Q_n), "material Y write-down missed"),
                  (R(wd + stor + spoil), "excluded costs counted as NRV write-down")],
          steps=[f"Y: {inr(Y_c)} − {inr(Y_n)} = {inr(Y_c-Y_n)}; Q: {inr(Q_c)} − {inr(Q_n)} = {inr(Q_c-Q_n)}",
                 f"Total write-down = {inr(wd)} (storage and spoilage are expensed as period costs, not as write-down)"],
          formula="Write-down = Cost − NRV for items carried at NRV", trap="Excluded costs are not a 'write-down to NRV'.")
    stmt(B, S("as-2-"), "L4", case + "Consider the following statements:",
         ["Material X is not written down because product P is expected to be sold above cost.",
          "Replacement cost may be the best available measure of the NRV of material Y.",
          "The company may value material Y using LIFO if it is applied consistently."],
         [1, 2], [([1, 3], "accepts LIFO under AS 2"), ([2, 3], "rejects the materials exception"),
                  ([1, 2, 3], "accepts LIFO under AS 2")],
         ["1 and 2 reflect AS 2 para 24.", "AS 2 permits only FIFO or weighted average (specific identification where applicable); LIFO is not permitted."],
         "LIFO is not a permitted cost formula.", group=g, ref="AS 2 para 16, 24")

    # ================= AS 10 =================
    B.add(micro=S("as-10-"), level="L1",
          stem="Under AS 10, an increase in carrying amount arising on revaluation of an item of PPE, which does NOT reverse a previous revaluation decrease, is:",
          correct="Credited to revaluation surplus under owners' interests (equity)",
          wrongs=[("Credited to the statement of profit and loss as other income", "only a reversal of an earlier expensed decrease goes to P&L"),
                  ("Credited to general reserve as a free, distributable reserve", "wrong reserve"),
                  ("Deducted from accumulated depreciation only, with no reserve", "ignores the surplus")],
          steps=["Revaluation increase → revaluation surplus (equity), except to the extent it reverses a decrease previously recognised in P&L."],
          formula="AS 10 para 42", trap="The reversal portion goes to P&L; the rest to surplus.", kind="conceptual", ref="AS 10 (2016) para 42–43")

    c, life, rv_date_yrs, rv_val = 1000000, 10, 2, 960000
    ca = c - c / life * rv_date_yrs
    surplus = rv_val - ca
    new_dep = rv_val / (life - rv_date_yrs)
    transfer = new_dep - c / life
    bal = surplus - transfer
    assert (ca, surplus, new_dep, transfer, bal) == (800000, 160000, 120000, 20000, 140000)
    B.add(micro=S("as-10-"), level="L3",
          stem=(f"Plant costing {R(c)} was acquired on 1 April 2023 (life {life} years, SLM, nil residual value). On 31 March 2025 it was revalued "
                f"at {R(rv_val)}, with no change in remaining life. The company transfers the realised part of the revaluation surplus to "
                f"retained earnings each year as the asset is used. The revaluation surplus at 31 March 2026 is:"),
          correct=R(bal),
          wrongs=[(R(surplus), "no transfer of realised surplus"),
                  (R(surplus - new_dep), "entire revised depreciation charged against the surplus"),
                  (R(surplus - surplus / life), "surplus released over the original 10-year life")],
          steps=[f"Carrying amount at 31-3-2025 = {inr(c)} − 2 × {inr(c/life)} = {inr(ca)}",
                 f"Surplus = {inr(rv_val)} − {inr(ca)} = {inr(surplus)}",
                 f"Depreciation FY 2025-26 = {inr(rv_val)} ÷ 8 = {inr(new_dep)}; on cost it would be {inr(c/life)}",
                 f"Transfer = {inr(new_dep)} − {inr(c/life)} = {inr(transfer)}; closing surplus = {inr(bal)}"],
          formula="Annual transfer = Depreciation on revalued amount − Depreciation on original cost",
          trap="The transfer goes directly to retained earnings, not through profit and loss.", ref="AS 10 para 45")

    inc, dec = 50000, 80000
    B.add(micro=S("as-10-"), level="L3",
          stem=(f"Land was revalued upward two years ago, creating a revaluation surplus of {R(inc)} that remains intact. This year it is revalued "
                f"downward by {R(dec)}. The amount charged to the statement of profit and loss this year is:"),
          correct=R(dec - inc),
          wrongs=[(R(dec), "entire decrease charged to P&L ignoring the surplus"),
                  ("Nil", "entire decrease debited to the surplus, creating a debit balance"),
                  (R(inc), "the surplus amount itself charged to P&L")],
          steps=[f"Decrease first debited to the existing surplus: {inr(inc)}",
                 f"Balance {inr(dec)} − {inr(inc)} = {inr(dec-inc)} to P&L"],
          formula="Revaluation decrease: to surplus up to its credit balance, rest to P&L", trap="The surplus cannot go negative.",
          ref="AS 10 para 43")

    stmt(B, S("as-10-"), "L2", "Under AS 10 (revised), consider the following:",
         ["Each part of an item of PPE with a cost significant in relation to the total cost is depreciated separately.",
          "Costs of day-to-day servicing are added to the carrying amount of the item.",
          "The initial estimate of costs of dismantling and removing the item and restoring the site is included in its cost."],
         [1, 3], [([1, 2], "capitalises day-to-day servicing"), ([2, 3], "rejects component accounting"),
                  ([1, 2, 3], "capitalises day-to-day servicing")],
         ["Component approach — true.", "Day-to-day servicing is expensed — false.", "Decommissioning cost is part of cost — true."],
         "Only replacements meeting the recognition criteria are capitalised.", ref="AS 10 paras 12, 16, 44")

    # ================= Depreciation =================
    B.add(micro=S("depreciation-methods"), level="L1",
          stem="Under AS 10 / Ind AS 16, depreciation of an asset begins:",
          correct="When it is available for use in the location and condition intended",
          wrongs=[("When it is first actually used in commercial production by the entity", "actual use is not the trigger"),
                  ("From the date of the supplier's purchase invoice for the asset", "invoice date may precede availability"),
                  ("From the beginning of the next financial year after acquisition", "no such convention in the standards")],
          steps=["Depreciation starts when the asset is available for use and continues even when idle, unless fully depreciated."],
          formula="AS 10 para 57 / Ind AS 16 para 55", trap="Idle assets continue to be depreciated (usage method aside).", kind="conceptual")

    c2, r0, l0, yrs, lnew_rem, r1 = 600000, 60000, 10, 4, 4, 40000
    d0 = (c2 - r0) / l0
    ca2 = c2 - d0 * yrs
    d5 = (ca2 - r1) / lnew_rem
    assert (d0, ca2, d5) == (54000, 384000, 86000)
    B.add(micro=S("depreciation-methods"), level="L3",
          stem=(f"A machine cost {R(c2)} (residual value {R(r0)}, life {l0} years, SLM). At the start of year 5 the remaining useful life is "
                f"re-estimated at {lnew_rem} years and the residual value at {R(r1)}. Depreciation for year 5 is:"),
          correct=R(d5),
          wrongs=[(R((ca2 - r0) / lnew_rem), "old residual value retained"),
                  (R((c2 - r1) / (yrs + lnew_rem)), "revised estimates applied retrospectively from cost"),
                  (R(ca2 / lnew_rem), "revised residual value ignored")],
          steps=[f"Old charge = ({inr(c2)} − {inr(r0)}) ÷ {l0} = {inr(d0)}; after 4 years CA = {inr(ca2)}",
                 f"Year 5 = ({inr(ca2)} − {inr(r1)}) ÷ {lnew_rem} = {inr(d5)}"],
          formula="Revised depreciation = (Carrying amount − Revised residual) ÷ Remaining life",
          trap="Change in estimate is prospective; no catch-up adjustment.", ref="AS 10 para 55; AS 5")

    c3, slm, wdv = 800000, 0.10, 0.15
    ca3 = c3 * (1 - 3 * slm)
    dep_new = ca3 * wdv
    retro_bv = c3 * (1 - wdv) ** 3
    catch = ca3 - retro_bv
    assert (ca3, dep_new) == (560000, 84000) and round(retro_bv) == 491300
    B.add(micro=S("depreciation-methods"), level="L3",
          stem=(f"An asset costing {R(c3)} bought on 1 April 2022 was depreciated at {pct(slm,0)} SLM (nil residual). From 1 April 2025 the company "
                f"changes to the WDV method at {pct(wdv,0)} because it better reflects the pattern of consumption. Under AS 10 (revised), the "
                f"depreciation charge for FY 2025-26 is:"),
          correct=R(dep_new),
          wrongs=[(R(retro_bv * wdv), "WDV applied on a retrospectively recomputed book value"),
                  (R(catch + retro_bv * wdv), "old AS 6 approach: retrospective catch-up plus current charge"),
                  (R(c3 * wdv), "WDV rate applied on original cost")],
          steps=["Revised AS 10: a change in depreciation method is a change in accounting estimate — applied prospectively.",
                 f"Carrying amount at 1-4-2025 = {inr(c3)} − 3 × {inr(c3*slm)} = {inr(ca3)}",
                 f"Charge = {inr(ca3)} × {pct(wdv,0)} = {inr(dep_new)}"],
          formula="Change in method = change in estimate (prospective)",
          trap="Retrospective recomputation was the pre-2016 AS 6 treatment.", verify_fact=True, ref="AS 10 (2016) para 61; AS 5")

    c4, rv4, out_tot, out_y = 1200000, 120000, 360000, 54000
    d4 = (c4 - rv4) / out_tot * out_y
    B.add(micro=S("depreciation-methods"), level="L2",
          stem=(f"A press costing {R(c4)} has an estimated residual value of {R(rv4)} and an estimated total output of {inr(out_tot)} units. "
                f"Output this year is {inr(out_y)} units. Depreciation under the units-of-production method is:"),
          correct=R(d4),
          wrongs=[(R(c4 / out_tot * out_y), "residual value not deducted"),
                  (R((c4 - rv4) * out_y / (out_tot - out_y)), "divided by remaining output instead of total output"),
                  (R((c4 + rv4) / out_tot * out_y), "residual value added instead of deducted")],
          steps=[f"Rate = ({inr(c4)} − {inr(rv4)}) ÷ {inr(out_tot)} = ₹{(c4-rv4)/out_tot:.0f} per unit",
                 f"Depreciation = {inr(out_y)} × {(c4-rv4)/out_tot:.0f} = {inr(d4)}"],
          formula="Depreciable amount ÷ Total estimated output × Output of the year", trap="Depreciable amount excludes residual value.")

    # ================= AS 9 =================
    B.add(micro=S("as-9-"), level="L1",
          stem="Under AS 9, revenue from dividends on investments in shares is recognised:",
          correct="When the owner's right to receive payment is established",
          wrongs=[("When the dividend is actually received in cash by the investor", "cash basis"),
                  ("On a time-proportion basis over the investor's financial year", "the rule for interest"),
                  ("When the investee earns the profits out of which it is paid", "equity-method style recognition, not AS 9")],
          steps=["AS 9: interest — time proportion; royalties — accrual per agreement; dividends — when right to receive is established."],
          formula="AS 9 para 13", trap="Interest is time-based; dividends are event-based.", kind="conceptual", ref="AS 9 para 13")

    stmt(B, S("as-9-"), "L2", "Under AS 9, consider the following:",
         ["In a sale on approval, revenue is recognised when the buyer signifies acceptance or the time for rejection has lapsed.",
          "Goods sent to a consignee are revenue of the consignor when dispatched.",
          "For a 'bill and hold' sale where the buyer takes title and accepts billing but requests delayed delivery, revenue may be recognised if delivery is probable."],
         [1, 3], [([1, 2], "treats dispatch to a consignee as a sale"), ([2, 3], "treats dispatch to a consignee as a sale"),
                  ([3], "misses the sale-on-approval rule")],
         ["1 true.", "2 false — revenue arises when the consignee sells to a third party.", "3 true — per the AS 9 appendix."],
         "Consignment is a transfer of possession, not of ownership.", ref="AS 9 Appendix")

    sor, sor_un, dep_amt, int_r, months, consg, cons_sold, roy_rate, lic_sales = 800000, 0.25, 100000, 0.09, 8, 300000, 2 / 3, 0.05, 2000000
    rev = sor * (1 - sor_un) + dep_amt * int_r * months / 12 + consg * cons_sold + roy_rate * lic_sales
    assert round(rev) == 906000
    B.add(micro=S("as-9-"), level="L3",
          stem=("Data for Himadri Ltd for FY 2025-26:\n\n"
                f"1. Goods of sale value {R(sor)} sent on sale-or-return; buyers have not yet accepted {pct(sor_un,0)} and the return period has not expired.\n"
                f"2. A fixed deposit of {R(dep_amt)} at {pct(int_r,0)} p.a. made on 1 August 2025; interest is payable on maturity in 2026-27.\n"
                f"3. Goods invoiced at {R(consg)} were sent to a consignee, who sold two-thirds of them by 31 March 2026.\n"
                f"4. Royalty of {pct(roy_rate,0)} on a licensee's sales of {R(lic_sales)} for the year is due under the agreement but not yet received.\n\n"
                "Total revenue recognised under AS 9 is:"),
          correct=R(rev),
          wrongs=[(R(rev + sor * sor_un), "unapproved sale-or-return goods treated as sold"),
                  (R(rev + consg * (1 - cons_sold)), "goods with the consignee treated as sold"),
                  (R(rev - roy_rate * lic_sales - dep_amt * int_r * months / 12), "royalty and interest recognised only on receipt")],
          steps=[f"(1) {inr(sor)} × 75% = {inr(sor*(1-sor_un))}", f"(2) {inr(dep_amt)} × 9% × 8/12 = {inr(dep_amt*int_r*months/12)}",
                 f"(3) {inr(consg)} × 2/3 = {inr(consg*cons_sold)}", f"(4) 5% × {inr(lic_sales)} = {inr(roy_rate*lic_sales)}",
                 f"Total = {inr(rev)}"],
          formula="AS 9 recognition by transaction type", trap="Interest and royalty accrue regardless of receipt.")

    # ================= AS 13 =================
    B.add(micro=S("as-13-"), level="L1",
          stem="Under AS 13, current investments are carried in the financial statements at:",
          correct="Lower of cost and fair value, determined individually or by category",
          wrongs=[("Cost less provision for permanent (other than temporary) diminution", "the rule for long-term investments"),
                  ("Fair value, with changes taken directly to reserves in equity", "a fair-value model not in AS 13"),
                  ("Lower of cost and fair value computed on the aggregate portfolio", "global comparison is not permitted")],
          steps=["Current: lower of cost and fair value (individual or category basis, not global).",
                 "Long-term: cost less other-than-temporary decline."],
          formula="AS 13 para 14, 17", trap="Global (portfolio) comparison lets gains hide losses — not allowed.", kind="conceptual",
          ref="AS 13 paras 14–17")

    inv = [("A", 200000, 170000), ("B", 350000, 410000), ("C", 150000, 135000)]
    ind = sum(min(c_, f_) for _, c_, f_ in inv)
    tc, tf = sum(c_ for _, c_, _ in inv), sum(f_ for _, _, f_ in inv)
    assert ind == 655000
    B.add(micro=S("as-13-"), level="L3",
          stem=("A company holds the following current investments (each a separate scrip; valuation on an individual investment basis):\n\n" +
                table(["Scrip", "Cost (₹)", "Fair value (₹)"], [[n, inr(c_), inr(f_)] for n, c_, f_ in inv]) +
                "\n\nThe carrying amount of current investments is:"),
          correct=R(ind),
          wrongs=[(R(min(tc, tf)), "aggregate portfolio comparison (gain on B offsets losses)"),
                  (R(tf), "all scrips carried at fair value"),
                  (R(ind + (150000 - 135000)), "decline in scrip C missed")],
          steps=[f"A: {inr(170000)}; B: {inr(350000)}; C: {inr(135000)}", f"Total = {inr(ind)}"],
          formula="Σ min(cost, FV) per investment", trap="Unrealised gains are not recognised on current investments.")

    stmt(B, S("as-13-"), "L2", "On reclassification of investments under AS 13:",
         ["Long-term to current: transfer at the lower of cost and carrying amount.",
          "Current to long-term: transfer at the lower of cost and fair value on the date of transfer.",
          "Current to long-term: transfer at fair value, with the gain over cost credited to P&L."],
         [1, 2], [([1, 3], "recognises an unrealised gain on transfer"), ([2, 3], "contradictory statements 2 and 3"),
                  ([1], "misses the current-to-long-term rule")],
         ["AS 13 para 24–25: LT → current at lower of cost and carrying amount; current → LT at lower of cost and fair value.",
          "Statement 3 would recognise unrealised gains — not allowed."],
         "Both transfer rules use 'lower of'.", ref="AS 13 paras 24–25")

    # ================= AS 11 =================
    usd, r_tr, r_cl = 25000, 83.20, 84.00
    B.add(micro=S("as-11-"), level="L2",
          stem=(f"Goods were imported on credit for USD {inr(usd)} when the rate was ₹{r_tr:.2f}/USD. The payable remains unpaid at the balance "
                f"sheet date, when the rate is ₹{r_cl:.2f}/USD. Under AS 11 the exchange difference is:"),
          correct=f"Loss of {R(usd*(r_cl-r_tr))} charged to profit and loss",
          wrongs=[(f"Gain of {R(usd*(r_cl-r_tr))} credited to profit and loss", "direction reversed for a liability"),
                  (f"Loss of {R(usd*(r_cl-r_tr))} added to the cost of inventory", "exchange loss capitalised into goods"),
                  ("No adjustment until the payable is settled", "monetary item not retranslated at closing rate")],
          steps=[f"Monetary liability retranslated at closing rate: {inr(usd)} × ({r_cl:.2f} − {r_tr:.2f}) = {inr(usd*(r_cl-r_tr))} increase",
                 "Rupee depreciation increases the liability → loss to P&L."],
          formula="Monetary items at closing rate; difference to P&L", trap="Inventory cost is fixed at the transaction-date rate.",
          ref="AS 11 paras 11, 13")

    loan, r0_, r1_, r2_, n_mon = 100000, 82.0, 84.0, 85.2, 60
    l1 = loan * (r1_ - r0_)
    am1 = l1 * 12 / n_mon
    l2 = loan * (r2_ - r1_)
    am2 = (l1 - am1 + l2) * 12 / (n_mon - 12)
    bal2 = l1 - am1 + l2 - am2
    assert (l1, am1, round(l2), round(am2), round(bal2)) == (200000, 40000, 120000, 70000, 210000)
    B.add(micro=S("as-11-"), level="L3",
          stem=(f"On 1 April 2024 a company borrowed USD {inr(loan)} (repayable in one bullet on 31 March 2029) for working capital, at ₹{r0_:.2f}/USD. "
                f"It exercises the option in para 46A of AS 11 to accumulate differences on long-term foreign currency monetary items in the FCMITDA "
                f"and amortise them over the balance period. Rates: 31 March 2025 ₹{r1_:.2f}; 31 March 2026 ₹{r2_:.2f}. "
                f"The FCMITDA balance at 31 March 2026 is:"),
          correct=R(bal2),
          wrongs=[(R(l1 - am1 + l2 - am1), "only the first-year loss amortised in FY 2025-26"),
                  (R(l1 - am1 + l2), "no amortisation in FY 2025-26"),
                  (R(l1 - am1 + l2 - am1 - l2 * 12 / n_mon), "new loss amortised over the original 60 months")],
          steps=[f"FY 24-25: loss {inr(l1)}; amortise 12/60 = {inr(am1)}; balance {inr(l1-am1)}",
                 f"FY 25-26: further loss {inr(l2)}; pool {inr(l1-am1+l2)} amortised over remaining 48 months → {inr(am2)}",
                 f"Balance = {inr(bal2)}"],
          formula="Amortisation = Unamortised FCMITDA × 12 ÷ remaining months", trap="Each year's balance is spread over the remaining term only.",
          verify_fact=True, ref="AS 11 para 46A")

    stmt(B, S("as-11-"), "L2", "Regarding translation of a non-integral foreign operation under AS 11:",
         ["Assets and liabilities, both monetary and non-monetary, are translated at the closing rate.",
          "Income and expense items are translated at exchange rates at the dates of the transactions (an average rate may be used).",
          "Resulting exchange differences are recognised in profit and loss each year."],
         [1, 2], [([1, 3], "sends translation differences to P&L instead of reserve"),
                  ([2, 3], "applies integral-operation (temporal) logic to assets"),
                  ([1, 2, 3], "sends translation differences to P&L instead of reserve")],
         ["1 and 2 are the closing-rate method rules.",
          "Differences go to a foreign currency translation reserve until disposal of the net investment — 3 is false."],
         "P&L recognition applies to integral operations, not non-integral ones.", ref="AS 11 paras 24–26")

    # ================= AS 22 =================
    B.add(micro=S("as-22-"), level="L1",
          stem="Under AS 22, a deferred tax asset arising from unabsorbed depreciation or carry forward of tax losses is recognised only when:",
          correct="There is virtual certainty, backed by convincing evidence, of future taxable income",
          wrongs=[("There is reasonable certainty of sufficient future taxable income being available", "the test for other timing differences"),
                  ("The company has a history of taxable profits in each of the last three years", "not the AS 22 test"),
                  ("The losses are expected to be set off within eight years under the Income-tax Act", "tax-law period, not the recognition test")],
          steps=["AS 22 para 17: for unabsorbed depreciation/carry-forward losses — virtual certainty with convincing evidence.",
                 "Other DTAs — reasonable certainty."],
          formula="AS 22 paras 15–17", trap="Two different thresholds.", kind="conceptual", ref="AS 22 para 17")

    odtl, r_old, r_new, td_new = 600000, 0.30, 0.25, 200000
    cdtl = odtl / r_old * r_new + td_new * r_new
    assert round(cdtl) == 550000
    B.add(micro=S("as-22-"), level="L3",
          stem=(f"Opening deferred tax liability was {R(odtl)}, computed at {pct(r_old,0)}. During the year the tax rate for future years is "
                f"enacted at {pct(r_new,0)}. Timing differences originating in the year (tax depreciation over book depreciation) are {R(td_new)}. "
                f"The closing deferred tax liability is:"),
          correct=R(cdtl),
          wrongs=[(R(odtl + td_new * r_new), "opening DTL not remeasured at the new rate"),
                  (R(odtl + td_new * r_old), "old rate used throughout"),
                  (R(odtl / r_old * r_new + td_new * r_old), "new timing difference measured at the old rate")],
          steps=[f"Cumulative timing difference = {inr(odtl)} ÷ 30% = {inr(odtl/r_old)}",
                 f"Remeasured at 25% = {inr(odtl/r_old*r_new)} (credit {inr(odtl - odtl/r_old*r_new)} to P&L)",
                 f"Add {inr(td_new)} × 25% = {inr(td_new*r_new)}; closing DTL = {inr(cdtl)}"],
          formula="DT balance = Cumulative timing differences × enacted/substantively enacted rate",
          trap="Rate changes remeasure the whole opening balance.", ref="AS 22 paras 21, 22")

    # ---- Case C3: Navdeep ----
    g = "ACC-C3-NAVDEEP"
    pbt, rt, bd, tdp, pdd, pen = 2000000, 0.25, 300000, 460000, 80000, 50000
    ti = pbt - (tdp - bd) + pdd + pen
    ct = ti * rt
    dtl, dta = (tdp - bd) * rt, pdd * rt
    ndt = dtl - dta
    te = ct + ndt
    assert (ti, ct, ndt, te) == (1970000, 492500, 20000, 512500)
    case = (f"**Case — Navdeep Ltd (FY 2025-26).** Accounting profit before tax is {R(pbt)}; the enacted tax rate is {pct(rt,0)}.\n\n" +
            table(["Item", "₹"], [["Depreciation as per books", inr(bd)], ["Depreciation allowed for tax", inr(tdp)],
                                  ["Provision for doubtful debts (deductible only when debts are written off)", inr(pdd)],
                                  ["Penalty for statutory violation (never deductible)", inr(pen)]]) +
            "\n\nThere are no opening deferred tax balances; realisation of deferred tax assets is reasonably certain.\n\n")
    B.add(micro=S("as-22-"), level="L4", group=g, stem=case + "Current tax for the year is:",
          correct=R(ct),
          wrongs=[(R(pbt * rt), "tax applied on accounting profit"),
                  (R(te), "total tax expense reported as current tax"),
                  (R((pbt - (tdp - bd) + pdd) * rt), "penalty not added back")],
          steps=[f"Taxable income = {inr(pbt)} − ({inr(tdp)} − {inr(bd)}) + {inr(pdd)} + {inr(pen)} = {inr(ti)}",
                 f"Current tax = {inr(ti)} × 25% = {inr(ct)}"],
          formula="Current tax = Taxable income × rate", trap="Add back disallowances, deduct excess tax depreciation.")
    B.add(micro=S("as-22-"), level="L4", group=g, stem=case + "The net deferred tax charge for the year is:",
          correct=f"{R(ndt)} (net deferred tax liability)",
          wrongs=[(f"{R(dtl)} (deferred tax liability)", "deferred tax asset on the provision ignored"),
                  (f"{R(dtl + dta)} (deferred tax liability)", "DTA added to DTL instead of netted"),
                  (f"{R(ndt + pen * rt)} (net deferred tax liability)", "penalty treated as a timing difference")],
          steps=[f"DTL on depreciation = {inr(tdp-bd)} × 25% = {inr(dtl)}",
                 f"DTA on provision = {inr(pdd)} × 25% = {inr(dta)}", f"Net = {inr(ndt)} DTL",
                 "Penalty is a permanent difference — no deferred tax."],
          formula="Deferred tax = Timing differences × rate", trap="Permanent differences never create deferred tax.")
    B.add(micro=S("as-22-"), level="L4", group=g, stem=case + "Total tax expense in the statement of profit and loss is:",
          correct=R(te),
          wrongs=[(R(pbt * rt), "tax expense taken as rate × accounting profit"),
                  (R(ct), "deferred tax omitted"),
                  (R(ct + dtl + dta), "DTA added as a charge")],
          steps=[f"Tax expense = current {inr(ct)} + deferred {inr(ndt)} = {inr(te)}",
                 f"Check: ({inr(pbt)} + permanent {inr(pen)}) × 25% = {inr((pbt+pen)*rt)}"],
          formula="Tax expense = Current tax + Deferred tax", trap="Tax expense differs from rate × PBT only by permanent differences.")
    stmt(B, S("as-22-"), "L4", case + "Consider the following statements under AS 22:",
         ["The deferred tax liability is measured using the enacted or substantively enacted rate.",
          "The deferred tax liability should be discounted to its present value.",
          "Had the company unabsorbed tax losses, a DTA on them would need virtual certainty supported by convincing evidence."],
         [1, 3], [([1, 2], "believes deferred tax is discounted"), ([2, 3], "rejects the enacted-rate rule"),
                  ([1, 2, 3], "believes deferred tax is discounted")],
         ["1 true (para 21).", "2 false — AS 22 para 26 prohibits discounting.", "3 true (para 17)."],
         "Deferred tax is never discounted.", group=g, ref="AS 22 paras 17, 21, 26")

    # ================= Leases =================
    stmt(B, S("leases-"), "L2", "Under AS 19, which of the following would normally indicate a FINANCE lease?",
         ["The lease transfers ownership of the asset to the lessee by the end of the lease term.",
          "The present value of minimum lease payments at inception amounts to substantially all of the fair value of the asset.",
          "The lessor retains the right to replace the asset at any time and bears obsolescence risk."],
         [1, 2], [([1, 3], "treats lessor-retained risk as a finance-lease indicator"), ([2, 3], "misses transfer of ownership"),
                  ([1, 2, 3], "treats lessor-retained risk as a finance-lease indicator")],
         ["1 and 2 are standard AS 19 indicators.", "3 indicates risks stay with the lessor — an operating lease feature."],
         "Classification turns on who bears substantially all risks and rewards.", question="Select the correct answer:",
         ref="AS 19 para 8")

    fv_l, pmt, n_l, ibr = 1000000, 280000, 5, 0.13
    pv = pmt * annuity(ibr, n_l)
    init = min(fv_l, pv)
    int1 = init * ibr
    assert init == pv and 980000 < pv < 990000
    B.add(micro=S("leases-"), level="L3",
          stem=(f"Under a finance lease (AS 19), a lessee pays {R(pmt)} at the end of each of {n_l} years for a machine whose fair value at inception "
                f"is {R(fv_l)}. The rate implicit in the lease is not determinable; the lessee's incremental borrowing rate is {pct(ibr,0)}. "
                f"The finance charge for year 1 is (nearest rupee):"),
          correct=R(int1),
          wrongs=[(R(fv_l * ibr), "asset recognised at fair value although PV of MLP is lower"),
                  (R(pmt * n_l - init), "total finance charge put in year 1"),
                  (R((pmt * n_l - init) / n_l), "finance charge spread straight-line")],
          steps=[f"PV of MLP = {inr(pmt)} × annuity factor({pct(ibr,0)}, {n_l}) {annuity(ibr, n_l):.4f} = {inr(pv)}",
                 f"Recognise at lower of FV {inr(fv_l)} and PV {inr(pv)} = {inr(init)}",
                 f"Year-1 finance charge = {inr(init)} × 13% = {inr(int1)}"],
          formula="Initial liability = lower of FV and PV of MLP; finance charge = opening liability × rate",
          trap="Finance charges follow the constant periodic rate, not straight-line.", ref="AS 19 paras 11, 17")

    # ================= Provisions =================
    B.add(micro=S("provisions-vs"), level="L1",
          stem="Under AS 29 (revised), a contingent asset whose inflow of economic benefits is probable (but not virtually certain) is:",
          correct="Not recognised; disclosed in the report of the approving authority",
          wrongs=[("Recognised as an asset with a matching credit to profit or loss", "recognition requires virtual certainty"),
                  ("Not recognised; disclosed in the notes to the financial statements", "AS 29 moves this disclosure to the approving authority's report"),
                  ("Recognised as income but credited to a reserve until realised", "no such treatment")],
          steps=["When realisation is virtually certain the asset is not contingent and is recognised.",
                 "Probable inflow: no recognition; AS 29 requires disclosure in the report of the approving authority (Ind AS 37 uses the notes)."],
          formula="AS 29 paras 31–35", trap="Ind AS 37 discloses probable contingent assets in the notes; AS 29 does not.",
          kind="conceptual", verify_fact=True, ref="AS 29 (revised 2016) paras 31–35")

    match(B, S("provisions-vs"), "L2", "Match each situation (present obligation or possible obligation from a past event) with its treatment under AS 29 / Ind AS 37:",
          ["Outflow probable, reliable estimate possible", "Outflow possible but not probable",
           "Outflow remote", "Present obligation probable, but no reliable estimate can be made (extremely rare)"],
          ["No disclosure required", "Recognise a provision", "Disclose as contingent liability", "Disclose as contingent liability (inability to measure)"],
          [2, 3, 1, 4],
          [([2, 1, 3, 4], "requires disclosure for remote items and none for possible"),
           ([3, 2, 1, 4], "provision for possible outflows"),
           ([2, 3, 1, 2], "provides even without a reliable estimate")],
          ["Probable + reliable → provision.", "Possible → contingent liability disclosure.", "Remote → nothing.",
           "No reliable estimate → contingent liability."],
          "Remote contingent liabilities need no disclosure.", ref="AS 29 / Ind AS 37")

    units_w, p_min, c_min, p_maj, c_maj = 10000, 0.20, 800, 0.05, 3000
    ev = units_w * (p_min * c_min + p_maj * c_maj)
    assert ev == 3100000
    B.add(micro=S("provisions-vs"), level="L3",
          stem=(f"A company sold {inr(units_w)} appliances under a one-year warranty. Experience: {pct(1-p_min-p_maj,0)} need no repair; "
                f"{pct(p_min,0)} need minor repairs costing ₹{c_min} each; {pct(p_maj,0)} need major repairs costing ₹{inr(c_maj)} each. "
                "The warranty provision at year-end (no repairs yet; ignore discounting) is:"),
          correct=R(ev),
          wrongs=[("Nil", "most likely single outcome (no repair) used for a large population"),
                  (R(units_w * p_maj * c_maj), "only major repairs provided"),
                  (R(units_w * (p_min + p_maj) * c_maj), "all defective units costed at the major-repair rate")],
          steps=[f"Expected cost per unit = 20% × 800 + 5% × 3,000 = ₹{p_min*c_min + p_maj*c_maj:.0f}",
                 f"Provision = {inr(units_w)} × {p_min*c_min + p_maj*c_maj:.0f} = {inr(ev)}"],
          formula="Large population → expected value", trap="Most-likely-outcome is for single obligations.",
          ref="AS 29 / Ind AS 37 — best estimate")

    # ================= Commitments =================
    stmt(B, S("commitments-and"), "L1", "Under Schedule III (Division I/II), which of the following are disclosed as COMMITMENTS (not contingent liabilities)?",
         ["Estimated amount of contracts remaining to be executed on capital account and not provided for.",
          "Uncalled liability on shares and other investments partly paid.",
          "Claims against the company not acknowledged as debts."],
         [1, 2], [([1, 3], "classifies unacknowledged claims as commitments"), ([2, 3], "misses capital commitments"),
                  ([1, 2, 3], "classifies unacknowledged claims as commitments")],
         ["Commitments: capital contracts, uncalled liability on partly paid investments, other commitments.",
          "Claims not acknowledged as debts are contingent liabilities."],
         "Contingent liabilities depend on uncertain events; commitments are contractual.", question="Select the correct answer:",
         verify_fact=True, ref="Schedule III, General Instructions — Contingent liabilities and commitments")

    cont, done, adv = 5000000, 2000000, 500000
    B.add(micro=S("commitments-and"), level="L2",
          stem=(f"A company contracted for a new plant at {R(cont)}. By the balance sheet date work worth {R(done)} has been completed, billed and "
                f"provided for, and an unadjusted capital advance of {R(adv)} has been paid. Per its accounting policy, capital commitments are "
                f"disclosed net of capital advances. The capital commitment to be disclosed is:"),
          correct=R(cont - done - adv),
          wrongs=[(R(cont - done), "capital advance not netted despite the stated policy"),
                  (R(cont - adv), "work already provided for included in commitment"),
                  (R(cont), "entire contract value disclosed")],
          steps=[f"Remaining to be executed = {inr(cont)} − {inr(done)} = {inr(cont-done)}",
                 f"Net of advance {inr(adv)} = {inr(cont-done-adv)}"],
          formula="Commitment = Contract value − amount provided − advances (per policy)", trap="Amounts already provided are liabilities, not commitments.",
          ref="Schedule III — capital commitments")
