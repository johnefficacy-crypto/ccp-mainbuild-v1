"""Part 4: company accounts (shares, premium, calls, rights, bonus, buy-back, preference, debentures, amalgamation),
partnership, Schedule III, statement of profit and loss."""
from acc_common import S, R, inr, pct, ar, stmt, match, table, lakh, crore


def add_all(B):
    # ================= Share issue journal entries =================
    offered, applied, app, allot = 100000, 150000, 3, 4
    excess = (applied - offered) * app
    cash_allot = offered * allot - excess
    assert cash_allot == 250000
    B.add(micro=S("journal-entries-for"), level="L2",
          stem=(f"A company offered {inr(offered)} equity shares of ₹10 each at a premium of ₹2, payable ₹{app} on application and ₹{allot} "
                f"(including premium) on allotment. Applications were received for {inr(applied)} shares; allotment was made pro rata to all "
                "applicants and excess application money was adjusted towards allotment. Cash received on allotment (all paid) is:"),
          correct=R(cash_allot),
          wrongs=[(R(offered * allot), "excess application money not adjusted"),
                  (R(offered * (allot - 2) - excess), "premium excluded from allotment money"),
                  (R(applied * allot - excess), "allotment computed on shares applied for")],
          steps=[f"Allotment due = {inr(offered)} × {allot} = {inr(offered*allot)}",
                 f"Excess application money = {inr(applied-offered)} × {app} = {inr(excess)} adjusted",
                 f"Cash on allotment = {inr(cash_allot)}"],
          formula="Cash on allotment = Allotment due − Excess application adjusted", trap="Premium is part of allotment money here.")

    held, app2, prem, forf_n, reiss_n, reiss_p = 400, 3, 2, 400, 300, 8
    forf_amt = forf_n * app2
    loss_re = reiss_n * (10 - reiss_p)
    cr = reiss_n * app2 - loss_re
    assert cr == 300
    B.add(micro=S("journal-entries-for"), level="L3",
          stem=(f"Shares of ₹10 each were issued at a premium of ₹{prem}: ₹{app2} on application, ₹5 on allotment (including premium) and ₹4 on first and final call. "
                f"A holder of {forf_n} shares paid only the application money; his shares were forfeited after the call. Of these, {reiss_n} shares were "
                f"reissued as fully paid at ₹{reiss_p} each. The amount transferred to capital reserve is:"),
          correct=R(cr),
          wrongs=[(R(forf_amt - loss_re), "forfeited amount on all 400 shares used instead of the 300 reissued"),
                  (R(reiss_n * app2), "discount on reissue not set off"),
                  (R(forf_amt), "entire share forfeiture balance transferred")],
          steps=[f"Forfeiture credit = {forf_n} × ₹{app2} = {inr(forf_amt)} (premium not received is reversed from securities premium)",
                 f"On 300 reissued shares: forfeited {inr(reiss_n*app2)}; discount on reissue {reiss_n} × 2 = {inr(loss_re)}",
                 f"Capital reserve = {inr(reiss_n*app2)} − {inr(loss_re)} = {inr(cr)}; balance {inr(forf_amt - reiss_n*app2)} stays in forfeiture"],
          formula="Capital reserve = Forfeited amount on reissued shares − Discount on reissue",
          trap="Only the forfeited amount relating to reissued shares is transferred.")

    # ================= Securities premium =================
    B.add(micro=S("issue-at-premium"), level="L1",
          stem="Under Section 52 of the Companies Act, 2013, securities premium can NOT be applied for:",
          correct="Payment of dividend to equity shareholders",
          wrongs=[("Issue of fully paid bonus shares", "a permitted use (s.52(2)(a))"),
                  ("Writing off commission paid on issue of shares", "a permitted use (s.52(2)(c))"),
                  ("Providing premium payable on redemption of debentures", "a permitted use (s.52(2)(d))")],
          steps=["s.52(2): bonus shares; preliminary expenses; expenses/commission/discount on issue of shares or debentures; premium on redemption of preference shares or debentures; buy-back under s.68.",
                 "Dividend is not a permitted use."],
          formula="Companies Act s.52(2)", trap="Securities premium is treated like capital, not distributable profit.", kind="conceptual",
          verify_fact=True, ref="Companies Act, 2013 s.52(2)")

    op, nsh, pr, exp_, bon, red_pr, div = 1000000, 50000, 15, 120000, 400000, 100000, 300000
    cl = op + nsh * pr - exp_ - bon - red_pr
    assert cl == 1130000
    B.add(micro=S("issue-at-premium"), level="L3",
          stem=("Securities premium of Ketan Ltd for FY 2025-26:\n\n" +
                table(["Event", "₹"], [["Opening balance", inr(op)], [f"Issue of {inr(nsh)} shares at a premium of ₹{pr}", inr(nsh * pr)],
                                       ["Share issue expenses", inr(exp_)], ["Fully paid bonus shares issued", inr(bon)],
                                       ["Premium payable on redemption of debentures", inr(red_pr)],
                                       ["Final dividend the board wishes to pay out of securities premium", inr(div)]]) +
                "\n\nApplying only permissible uses under Section 52, the closing balance of securities premium is:"),
          correct=R(cl),
          wrongs=[(R(cl - div), "dividend charged to securities premium"),
                  (R(cl + exp_), "issue expenses not written off against premium"),
                  (R(cl + bon), "bonus issue assumed to be made from general reserve")],
          steps=[f"{inr(op)} + {inr(nsh*pr)} − {inr(exp_)} − {inr(bon)} − {inr(red_pr)} = {inr(cl)}", "Dividend cannot be paid from securities premium."],
          formula="Closing SPR = Opening + premium received − permitted applications", trap="Dividend is not a permitted use.",
          verify_fact=True, ref="Companies Act, 2013 s.52(2)")

    # ================= Calls in advance / arrears =================
    B.add(micro=S("calls-in-advance"), level="L1",
          stem="Where a company's articles adopt Table F of Schedule I, the maximum rates of interest on calls in arrears (charged by the company) and on calls in advance (paid by the company) are respectively:",
          correct="10% p.a. and 12% p.a.",
          wrongs=[("12% p.a. and 10% p.a.", "rates interchanged"),
                  ("6% p.a. and 6% p.a.", "Partnership Act rate for partners' loans"),
                  ("5% p.a. and 6% p.a.", "rates from the repealed Table A of the 1956 Act")],
          steps=["Table F: interest on unpaid calls not exceeding 10% p.a.; interest on calls in advance not exceeding 12% p.a."],
          formula="Table F, Schedule I", trap="Advance earns more than arrears is charged.", kind="conceptual",
          verify_fact=True, ref="Companies Act, 2013 Schedule I, Table F, regulations 13(ii) and 18(b)")

    B.add(micro=S("calls-in-advance"), level="L2",
          stem="In a balance sheet under Schedule III (Division I), calls in arrears and calls in advance are shown respectively as:",
          correct="Deducted from subscribed capital; shown under 'Other current liabilities'",
          wrongs=[("Under 'Other current assets'; under 'Share capital' as paid-up capital", "arrears treated as a receivable and advances as capital"),
                  ("Deducted from subscribed capital; added to the paid-up share capital", "calls in advance are not share capital until called"),
                  ("Under 'Short-term loans and advances'; under 'Reserves and surplus'", "neither item is a loan or reserve")],
          steps=["Calls unpaid are deducted from 'subscribed but not fully paid' capital.",
                 "Calls in advance are a liability until the call is made — shown under other current liabilities (with interest accrued)."],
          formula="Schedule III presentation", trap="Advances are not capital until due.", kind="conceptual",
          verify_fact=True, ref="Schedule III Division I; ICAI Guidance Note on Schedule III")

    a_sh, a_call, a_m, b_sh, b_call, b_m = 500, 3, 6, 300, 2, 3
    int_ar = a_sh * a_call * 0.10 * a_m / 12
    int_ad = b_sh * b_call * 0.12 * b_m / 12
    assert (int_ar, int_ad) == (75, 18)
    B.add(micro=S("calls-in-advance"), level="L3",
          stem=(f"A company (Table F rates) made the first call of ₹{a_call} per share on 1 July 2025 and the final call of ₹{b_call} per share on 1 October 2025. "
                f"Mira, holding {a_sh} shares, paid the first call only on 31 December 2025. Neel, holding {b_sh} shares, paid the final call along with "
                "the first call on 1 July 2025. Interest receivable from Mira and payable to Neel (at the maximum Table F rates) is:"),
          correct=f"Receivable ₹{int_ar:.0f}; payable ₹{int_ad:.0f}",
          wrongs=[(f"Receivable ₹{a_sh*a_call*0.12*a_m/12:.0f}; payable ₹{b_sh*b_call*0.10*b_m/12:.0f}", "Table F rates interchanged"),
                  (f"Receivable ₹{a_sh*a_call*0.10:.0f}; payable ₹{b_sh*b_call*0.12:.0f}", "full-year interest, period ignored"),
                  (f"Receivable ₹{int_ar:.0f}; payable ₹{b_sh*b_call*0.12*6/12:.0f}", "advance interest computed up to 31 December")],
          steps=[f"Mira: {a_sh} × {a_call} = {inr(a_sh*a_call)} × 10% × 6/12 = ₹{int_ar:.0f}",
                 f"Neel: {b_sh} × {b_call} = {inr(b_sh*b_call)} × 12% × 3/12 (1 July to 1 October) = ₹{int_ad:.0f}"],
          formula="Interest = Amount × rate × period", trap="Advance interest runs only until the call falls due.")

    # ================= Rights issue: TERP =================
    n_old, cum, n_new, ip = 4, 180, 1, 130
    terp = (n_old * cum + n_new * ip) / (n_old + n_new)
    vr = cum - terp
    assert (terp, vr) == (170, 10)
    B.add(micro=S("rights-issue-ex-right"), level="L2",
          stem=f"A company makes a rights issue of {n_new} share for every {n_old} held at ₹{ip}. The cum-right market price is ₹{cum}. The theoretical value of a right per EXISTING share is:",
          correct=f"₹{vr:.0f}",
          wrongs=[(f"₹{terp - ip:.0f}", "value of right per NEW share"),
                  (f"₹{cum - ip:.0f}", "cum-right price less issue price, unadjusted"),
                  (f"₹{terp:.0f}", "theoretical ex-right price reported")],
          steps=[f"TERP = (4 × {cum} + 1 × {ip}) ÷ 5 = ₹{terp:.0f}", f"Value per existing share = {cum} − {terp:.0f} = ₹{vr:.0f}"],
          formula="TERP = (N·P + n·S) ÷ (N + n); Value of right = Cum-right price − TERP", trap="Per new share it is TERP − issue price.")

    eps0 = 12
    adj = cum / terp
    eps_r = eps0 / adj
    B.add(micro=S("rights-issue-ex-right"), level="L3",
          stem=(f"Continuing the rights issue above (1 for 4 at ₹{ip}; cum-right fair value ₹{cum}; TERP ₹{terp:.0f}), last year's reported basic EPS was ₹{eps0}. "
                "Under Ind AS 33 / AS 20, last year's EPS restated for the bonus element of the rights issue is:"),
          correct=f"₹{eps_r:.2f}",
          wrongs=[(f"₹{eps0*n_old/(n_old+n_new):.2f}", "treated like a bonus issue (full 1-for-4 dilution)"),
                  (f"₹{eps0:.2f}", "no restatement for the bonus element"),
                  (f"₹{eps0*ip/cum:.2f}", "EPS scaled by issue price ÷ cum-right price")],
          steps=[f"Adjustment factor = Fair value cum-right ÷ TERP = {cum} ÷ {terp:.0f} = {adj:.4f}",
                 f"Restated EPS = {eps0} ÷ {adj:.4f} = ₹{eps_r:.2f}"],
          formula="Restated EPS = Previous EPS ÷ (Cum-right price ÷ TERP)", trap="Only the bonus element of a rights issue restates EPS.",
          ref="Ind AS 33 para 27, A2; AS 20")

    # ================= Rights issue procedure =================
    B.add(micro=S("rights-issue-offer"), level="L1",
          stem="Under Section 62(1)(a)(i) of the Companies Act, 2013, a rights offer to existing equity shareholders must be open for:",
          correct="Not less than 15 days and not more than 30 days from the offer date",
          wrongs=[("Not less than 30 days and not more than 60 days from the offer date", "periods not in s.62"),
                  ("Exactly 21 days from the date of dispatch of the offer letter", "the clear-days notice for general meetings is a different rule"),
                  ("Not less than 7 days and not more than 15 days from the offer date", "understates the minimum")],
          steps=["s.62(1)(a)(i): offer by notice specifying number of shares, time not less than 15 days and not exceeding 30 days."],
          formula="Companies Act s.62(1)(a)(i)", trap="A shorter period is possible only in special cases prescribed (e.g. consent of 90% members for unlisted/private companies).",
          kind="conceptual", verify_fact=True, ref="Companies Act, 2013 s.62(1)(a)(i)")

    stmt(B, S("rights-issue-offer"), "L2", "Regarding a rights issue under Section 62(1)(a):",
         ["Unless the articles provide otherwise, the offer includes a right to renounce the shares in favour of any other person.",
          "The notice of offer must be dispatched at least three days before the opening of the issue.",
          "Shares not taken up may be disposed of by the board in a manner not disadvantageous to the shareholders and the company."],
         [1, 2, 3], [([1, 2], "misses the board's power to dispose of unsubscribed shares"),
                     ([2, 3], "denies the default right of renunciation"),
                     ([1, 3], "misses the three-day dispatch requirement")],
         ["All three reflect s.62(1)(a)(ii)–(iii) and the explanation on dispatch of notice."],
         "Renunciation is the default unless the articles exclude it.", verify_fact=True, ref="Companies Act, 2013 s.62(1)(a)")

    # ================= Bonus issue =================
    stmt(B, S("bonus-issue"), "L2", "A company makes a 1-for-1 bonus issue of fully paid equity shares out of free reserves. Consider:",
         ["Total shareholders' funds of the company are unchanged.",
          "Each shareholder's proportionate ownership is unchanged.",
          "Earnings per share for all periods presented is restated for the increased number of shares.",
          "Cash of the company decreases by the nominal value of bonus shares."],
         [1, 2, 3], [([1, 2, 3, 4], "treats capitalisation as a cash outflow"),
                     ([1, 2], "misses the retrospective EPS adjustment"),
                     ([2, 3, 4], "believes shareholders' funds change")],
         ["Reserves convert to capital — total equity unchanged; no cash moves.", "Proportions unchanged.",
          "EPS is restated retrospectively (Ind AS 33 / AS 20)."],
         "Bonus is a capitalisation, not a distribution of cash.", question="Select the correct answer:")

    sh_b, spr_b, gr_b, rr_b = 200000, 120000, 600000, 200000
    bonus_amt = sh_b / 4 * 10
    gr_after = gr_b - (bonus_amt - spr_b)
    assert gr_after == 220000
    B.add(micro=S("bonus-issue"), level="L3",
          stem=(f"Tulsi Ltd has {inr(sh_b)} fully paid equity shares of ₹10 each. Reserves: securities premium {R(spr_b)}, general reserve {R(gr_b)}, "
                f"revaluation reserve {R(rr_b)}. It issues bonus shares 1 for 4, using securities premium first and then general reserve. "
                "The general reserve after the bonus issue is:"),
          correct=R(gr_after),
          wrongs=[(R(gr_b - (bonus_amt - spr_b - rr_b)), "revaluation reserve capitalised"),
                  (R(gr_b - bonus_amt), "entire bonus charged to general reserve"),
                  (R(gr_b - (sh_b / 5 * 10 - spr_b)), "ratio applied as 1 for 5")],
          steps=[f"Bonus = {inr(sh_b)} ÷ 4 × 10 = {inr(bonus_amt)}", f"From securities premium {inr(spr_b)}; balance {inr(bonus_amt-spr_b)} from general reserve",
                 f"General reserve left = {inr(gr_after)}"],
          formula="Bonus sources: free reserves, securities premium, CRR — not revaluation reserve", trap="Revaluation reserve cannot fund bonus shares.",
          verify_fact=True, ref="Companies Act, 2013 s.63(1)")

    # ================= Buy-back =================
    B.add(micro=S("buy-back"), level="L1",
          stem="Under Section 68 of the Companies Act, 2013, a buy-back authorised by a special resolution cannot exceed:",
          correct="25% of the aggregate of paid-up capital and free reserves",
          wrongs=[("10% of the aggregate of paid-up capital and free reserves", "limit for a board-resolution buy-back"),
                  ("50% of free reserves, excluding the paid-up capital", "no such limit"),
                  ("25% of free reserves only, excluding paid-up capital", "the base includes paid-up capital")],
          steps=["s.68(2)(b)–(c): board resolution up to 10%; special resolution up to 25% of paid-up capital + free reserves.",
                 "For equity shares, not more than 25% of paid-up equity capital in a financial year."],
          formula="Companies Act s.68(2)", trap="Distinguish the 10% board route and 25% special resolution route.", kind="conceptual",
          verify_fact=True, ref="Companies Act, 2013 s.68(2)")

    pu, fr, spr, price, nshares = 100000000, 300000000, 50000000, 250, 10000000
    lim = 0.25 * (pu + fr + spr)
    assert lim == 112500000 and lim / price <= 0.25 * nshares
    B.add(micro=S("buy-back"), level="L3",
          stem=(f"Dhruv Ltd (1 crore equity shares of ₹10 each, paid-up {crore(pu)}) has free reserves of {crore(fr)} and securities premium of "
                f"{crore(spr)}. A special resolution authorises a buy-back at ₹{price} per share. Ignoring the debt-equity test (debt is negligible), "
                "the maximum amount of buy-back is:"),
          correct=crore(lim),
          wrongs=[(crore(0.25 * (pu + fr)), "securities premium excluded from free reserves"),
                  (crore(0.10 * (pu + fr + spr)), "10% board-route limit applied despite a special resolution"),
                  (crore(0.25 * pu), "25% applied to paid-up capital alone, free reserves ignored")],
          steps=["For s.68, 'free reserves' includes securities premium (Explanation to s.68).",
                 f"Limit = 25% × ({crore(pu)} + {crore(fr)} + {crore(spr)}) = {crore(lim)}",
                 f"Shares = {crore(lim)} ÷ ₹{price} = {inr(lim/price)} ≤ 25 lakh (25% of equity shares) — satisfied"],
          formula="Max buy-back = 25% × (Paid-up capital + Free reserves incl. securities premium)",
          trap="The share-count limit is a separate test on the number of shares.", verify_fact=True,
          ref="Companies Act, 2013 s.68(2)(c) and Explanation")

    stmt(B, S("buy-back"), "L2", "With reference to buy-back of shares:",
         ["Where shares are bought back out of free reserves or securities premium, a sum equal to the nominal value of shares bought back is transferred to the capital redemption reserve.",
          "No offer of buy-back may be made within one year from the date of closure of a preceding buy-back offer.",
          "Every buy-back must be completed within one year from the date of passing the special resolution or board resolution."],
         [1, 2, 3], [([1, 2], "misses the one-year completion requirement"),
                     ([2, 3], "misses the s.69 CRR transfer"),
                     ([1, 3], "misses the one-year cooling-off between offers")],
         ["s.69(1): CRR transfer.", "s.68(2) proviso: one-year gap between offers.", "s.68(4): completion within one year."],
         "Two separate one-year rules: gap between offers and completion period.", verify_fact=True,
         ref="Companies Act, 2013 ss.68(2), 68(4), 69")

    # ================= Preference redemption =================
    npref, pv_, prem_r, fresh = 50000, 100, 0.10, 2000000
    crr = npref * pv_ - fresh
    B.add(micro=S("redemption-of-preference"), level="L2",
          stem=(f"A company redeems {inr(npref)} preference shares of ₹{pv_} each at a premium of {pct(prem_r,0)}. For this purpose it issues equity "
                f"shares of face value {R(fresh)} at par. The amount to be transferred to capital redemption reserve is:"),
          correct=R(crr),
          wrongs=[(R(npref * pv_), "fresh issue proceeds not deducted"),
                  (R(npref * pv_ * (1 + prem_r)), "redemption premium included in CRR base"),
                  (R(crr + npref * pv_ * prem_r), "premium on redemption added to CRR")],
          steps=[f"Nominal value redeemed = {inr(npref*pv_)}", f"Less fresh issue proceeds {inr(fresh)}",
                 f"CRR = {inr(crr)} out of distributable profits"],
          formula="CRR = Nominal value redeemed − Proceeds of fresh issue", trap="Premium on redemption is never part of CRR.",
          verify_fact=True, ref="Companies Act, 2013 s.55(2)(c)")

    red, gr_av, keep, spr_av = 1000000, 600000, 200000, 150000
    need = red - (gr_av - keep)
    assert need == 600000
    B.add(micro=S("redemption-of-preference"), level="L3",
          stem=(f"A company must redeem preference shares of {R(red)} at par. It has a general reserve of {R(gr_av)} (the board wishes to retain {R(keep)} "
                f"of it) and securities premium of {R(spr_av)}. The minimum number of equity shares of ₹10 each to be issued at par to finance the balance "
                "of the redemption, consistent with Section 55, is:"),
          correct=f"{inr(need/10)} shares",
          wrongs=[(f"{inr((red-gr_av)/10)} shares", "board's retention of general reserve ignored"),
                  (f"{inr(red/10)} shares", "entire redemption financed by fresh issue"),
                  (f"{inr((need-spr_av)/10)} shares", "securities premium treated as a source for redemption of nominal value")],
          steps=[f"Profits available = {inr(gr_av)} − {inr(keep)} = {inr(gr_av-keep)} (transferred to CRR)",
                 f"Fresh issue needed = {inr(red)} − {inr(gr_av-keep)} = {inr(need)} → {inr(need/10)} shares",
                 "Securities premium can fund only premium on redemption, not the nominal value."],
          formula="Fresh issue = Nominal redemption − Divisible profits used", trap="Securities premium is not a divisible profit.",
          verify_fact=True, ref="Companies Act, 2013 s.55(2)")

    B.add(micro=S("redemption-of-preference"), level="L1",
          stem="Under Section 55 of the Companies Act, 2013, a company (other than one engaged in infrastructure projects) may issue preference shares that are:",
          correct="Redeemable within a period not exceeding 20 years from issue",
          wrongs=[("Irredeemable, if the articles of association so permit", "irredeemable preference shares are prohibited"),
                  ("Redeemable within a period not exceeding 30 years from issue", "30 years applies to infrastructure projects"),
                  ("Redeemable within a period not exceeding 10 years from issue", "understates the limit")],
          steps=["s.55(1): no irredeemable preference shares; s.55(2): redeemable within 20 years (infrastructure: up to 30 years with annual 10% redemption from the 21st year)."],
          formula="Companies Act s.55", trap="The 30-year limit is only for infrastructure companies.", kind="conceptual",
          verify_fact=True, ref="Companies Act, 2013 s.55(1)–(2); Rule 10 Share Capital Rules")

    # ================= Debentures =================
    B.add(micro=S("debentures-features"), level="L1",
          stem="A company issues debentures of ₹100 each at ₹95, redeemable at ₹110. At the time of issue, the amount debited to 'Loss on issue of debentures' per debenture is:",
          correct="₹15",
          wrongs=[("₹5", "only the discount on issue recognised"),
                  ("₹10", "only the premium on redemption recognised"),
                  ("₹110", "redemption value debited")],
          steps=["Discount ₹5 + Premium payable on redemption ₹10 = ₹15."],
          formula="Loss on issue = Discount on issue + Premium on redemption", trap="The premium on redemption is a liability from the date of issue.")

    ndeb, fv, iss, redv, yrs = 10000, 100, 0.95, 1.10, 5
    loss_tot = ndeb * fv * ((1 - iss) + (redv - 1))
    assert round(loss_tot) == 150000
    B.add(micro=S("debentures-features"), level="L2",
          stem=(f"{inr(ndeb)} debentures of ₹{fv} each are issued at a {pct(1-iss,0)} discount, redeemable at a {pct(redv-1,0)} premium after {yrs} years "
                "in one lot. Under the equal-instalment (straight-line) write-off used under AS, the loss on issue written off each year is:"),
          correct=R(loss_tot / yrs),
          wrongs=[(R(ndeb * fv * (1 - iss) / yrs), "premium on redemption left out"),
                  (R(loss_tot), "entire loss written off in year 1"),
                  (R(ndeb * fv * (redv - 1) / yrs), "discount on issue left out")],
          steps=[f"Total loss = {inr(ndeb)} × (₹5 + ₹10) = {inr(loss_tot)}", f"Per year = {inr(loss_tot)} ÷ {yrs} = {inr(loss_tot/yrs)}"],
          formula="Annual write-off = Total loss on issue ÷ Years (bullet redemption)",
          trap="Under Ind AS 109 the same cost is spread by the effective interest method instead.")

    stmt(B, S("debentures-features"), "L2", "Regarding the Debenture Redemption Reserve (DRR) under Rule 18(7) of the Share Capital and Debentures Rules (as amended in 2019):",
         ["Listed companies are not required to create DRR for debentures issued by public issue or private placement.",
          "Unlisted companies (other than NBFCs and HFCs) must create DRR of 10% of the value of outstanding debentures.",
          "DRR may be created by transfer from securities premium."],
         [1, 2], [([1, 3], "allows DRR from securities premium"), ([2, 3], "denies the listed-company exemption"),
                  ([1, 2, 3], "allows DRR from securities premium")],
         ["1 and 2 reflect the August 2019 amendment.", "3 false — DRR is created out of profits available for dividend."],
         "DRR comes out of distributable profits.", verify_fact=True,
         ref="Companies Act s.71(4); Companies (Share Capital and Debentures) Rules, 2014, Rule 18(7) as amended 16-08-2019")

    # ================= Amalgamation =================
    tsh, rn, rd, ipx, cash_ps, deb = 50000, 3, 2, 15, 2, 200000
    pc = tsh * rn / rd * ipx + tsh * cash_ps
    assert pc == 1225000
    B.add(micro=S("amalgamation-and"), level="L3",
          stem=(f"Under a scheme of amalgamation (AS 14, purchase method), Big Ltd will issue {rn} equity shares of ₹10 each at ₹{ipx} for every {rd} shares "
                f"held in Small Ltd ({inr(tsh)} shares) and pay ₹{cash_ps} in cash per Small Ltd share. Small Ltd's debentures of {R(deb)} will be discharged "
                "by Big Ltd issuing its own 12% debentures. The purchase consideration is:"),
          correct=R(pc),
          wrongs=[(R(tsh * rn / rd * 10 + tsh * cash_ps), "shares valued at par instead of issue price"),
                  (R(pc + deb), "discharge of debentures included in purchase consideration"),
                  (R(tsh * rd / rn * ipx + tsh * cash_ps), "exchange ratio inverted")],
          steps=[f"Shares = {inr(tsh)} × 3/2 = {inr(tsh*rn/rd)} × ₹{ipx} = {inr(tsh*rn/rd*ipx)}",
                 f"Cash = {inr(tsh)} × ₹{cash_ps} = {inr(tsh*cash_ps)}", f"PC = {inr(pc)}; debentures are liabilities taken over, not consideration"],
          formula="PC = consideration payable to transferor's shareholders only", trap="Payments to debenture holders are excluded.",
          ref="AS 14 para 3(g)")

    stmt(B, S("amalgamation-and"), "L2", "For an amalgamation to be in the nature of merger under AS 14:",
         ["Shareholders holding not less than 90% of the face value of the transferor's equity shares (other than those already held by the transferee) become equity shareholders of the transferee.",
          "Assets and liabilities are recorded by the transferee at their fair values.",
          "Consideration may include cash in respect of fractional shares."],
         [1, 3], [([1, 2], "applies purchase-method measurement to a merger"), ([2, 3], "misses the 90% condition"),
                  ([1, 2, 3], "applies purchase-method measurement to a merger")],
         ["1 and 3 are AS 14 conditions.", "2 false — pooling uses existing carrying amounts (only uniform-policy adjustments)."],
         "Pooling of interests = carrying amounts.", ref="AS 14 para 3(e)")

    nsh_r, fv_old, fv_new, pl, gw, mach = 100000, 10, 4, 350000, 120000, 80000
    red_amt = nsh_r * (fv_old - fv_new)
    capres = red_amt - pl - gw - mach
    assert capres == 50000
    B.add(micro=S("amalgamation-and"), level="L3",
          stem=(f"Under internal reconstruction, {inr(nsh_r)} fully paid equity shares of ₹{fv_old} each are reduced to ₹{fv_new} each (fully paid). The amount "
                f"is used to write off the debit balance of profit and loss of {R(pl)}, goodwill of {R(gw)} and to write down machinery by {R(mach)}. "
                "The balance transferred to capital reserve is:"),
          correct=R(capres),
          wrongs=[(R(capres + mach), "machinery write-down omitted"),
                  (R(capres + gw), "goodwill not written off"),
                  (R(nsh_r * fv_old - pl - gw - mach), "entire paid-up capital treated as reduced")],
          steps=[f"Reduction = {inr(nsh_r)} × (10 − 4) = {inr(red_amt)}",
                 f"Used: {inr(pl)} + {inr(gw)} + {inr(mach)} = {inr(pl+gw+mach)}", f"Capital reserve = {inr(capres)}"],
          formula="Capital reserve = Capital reduction − losses and assets written off", trap="Reduction is ₹6 per share, not ₹10.")

    # ================= Partnership =================
    B.add(micro=S("partnership-accounts"), level="L1",
          stem="In the absence of a partnership deed, under the Indian Partnership Act, 1932, a partner who advances a loan to the firm is entitled to interest at:",
          correct="6% per annum",
          wrongs=[("12% per annum", "calls-in-advance style rate"),
                  ("No interest unless agreed", "the Act provides a default loan rate"),
                  ("The bank rate prevailing", "no such link")],
          steps=["s.13(d): interest at 6% p.a. on advances beyond agreed capital; no interest on capital (s.13(c)); no remuneration (s.13(a)); equal sharing (s.13(b))."],
          formula="Indian Partnership Act, 1932 s.13", trap="Interest on loan is a charge, payable even from losses.", kind="conceptual",
          verify_fact=True, ref="Indian Partnership Act, 1932 s.13(d)")

    prof, g_min = 270000, 60000
    c_sh = prof / 6
    a_sh_ = prof * 3 / 6 - (g_min - c_sh)
    assert a_sh_ == 120000
    B.add(micro=S("partnership-accounts"), level="L3",
          stem=(f"A, B and C share profits 3:2:1. C is guaranteed a minimum profit of {R(g_min)}; any deficiency is to be borne by A alone. "
                f"The firm's profit for the year is {R(prof)}. A's share of profit is:"),
          correct=R(a_sh_),
          wrongs=[(R(prof * 3 / 6), "guarantee ignored"),
                  (R(prof * 3 / 6 - (g_min - c_sh) * 3 / 5), "deficiency shared by A and B in 3:2"),
                  (R(prof * 3 / 6 - (g_min - c_sh) / 2), "deficiency shared equally by A and B")],
          steps=[f"C's share = {inr(prof)} × 1/6 = {inr(c_sh)}; deficiency = {inr(g_min-c_sh)}",
                 f"A = {inr(prof*3/6)} − {inr(g_min-c_sh)} = {inr(a_sh_)}"],
          formula="Guaranteed partner's deficiency borne as agreed", trap="Read who bears the deficiency.")

    dq, rate_d = 6000, 0.10
    int_dr = dq * 4 * rate_d * 7.5 / 12
    assert int_dr == 1500
    B.add(micro=S("partnership-accounts"), level="L2",
          stem=(f"A partner withdraws {R(dq)} at the beginning of each quarter of the financial year. Interest on drawings is charged at {pct(rate_d,0)} p.a. "
                "Interest on drawings for the year is:"),
          correct=R(int_dr),
          wrongs=[(R(dq * 4 * rate_d * 4.5 / 12), "average period for end-of-quarter drawings (4.5 months) used"),
                  (R(dq * 4 * rate_d * 6 / 12), "average period of 6 months used"),
                  (R(dq * 4 * rate_d), "full-year interest on total drawings")],
          steps=[f"Total drawings = {inr(dq*4)}", "Beginning-of-quarter drawings: average period = (12 + 3) ÷ 2 = 7.5 months",
                 f"Interest = {inr(dq*4)} × 10% × 7.5/12 = {inr(int_dr)}"],
          formula="Interest = Total drawings × rate × average period", trap="Beginning of quarter → 7.5 months; end → 4.5 months.")

    # ---- Case C6: partnership ----
    g = "ACC-C6-ARJUN"
    capA, capB, loanA, pbl = 500000, 300000, 200000, 186000
    intl = loanA * 0.06 * 6 / 12
    dist = pbl - intl
    assert (intl, dist) == (6000, 180000)
    case = (f"**Case — Arjun & Bela.** Arjun and Bela started a firm on 1 April 2025 without any written or oral agreement on profit sharing or interest. "
            f"Capitals: Arjun {R(capA)}, Bela {R(capB)}. On 1 October 2025 Arjun advanced a loan of {R(loanA)} to the firm. Bela, who manages the firm, "
            f"claims a salary of ₹5,000 a month; Arjun claims interest on capital at 10% p.a. Profit for FY 2025-26 before any interest on the loan was {R(pbl)}.\n\n")
    B.add(micro=S("partnership-accounts"), level="L4", group=g, stem=case + "Interest payable to Arjun on his loan for FY 2025-26 is:",
          correct=R(intl),
          wrongs=[(R(loanA * 0.06), "interest for a full year"),
                  (R(loanA * 0.10 * 6 / 12), "10% claimed rate applied to the loan"),
                  ("Nil", "loan interest treated as requiring an agreement")],
          steps=[f"s.13(d): 6% p.a. → {inr(loanA)} × 6% × 6/12 = {inr(intl)}"],
          formula="Interest on partner's loan = Loan × 6% × period", trap="Only from the date of the advance.", verify_fact=True,
          ref="Indian Partnership Act, 1932 s.13(d)")
    B.add(micro=S("partnership-accounts"), level="L4", group=g, stem=case + "Bela's share of profit for FY 2025-26 is:",
          correct=R(dist / 2),
          wrongs=[(R(pbl / 2), "loan interest not charged before sharing"),
                  (R(dist * capB / (capA + capB)), "profits shared in capital ratio"),
                  (R(60000 + (dist - 60000) / 2), "salary allowed to Bela before sharing")],
          steps=["No deed: no salary, no interest on capital, equal sharing.", f"Divisible profit = {inr(pbl)} − {inr(intl)} = {inr(dist)}; Bela = {inr(dist/2)}"],
          formula="Indian Partnership Act s.13 defaults", trap="Management by one partner does not create a right to salary.")
    ioc = (capA * 0.10, capB * 0.10)
    sal, p2 = 60000, 300000
    rem2 = p2 - sum(ioc) - sal
    a_tot = ioc[0] + rem2 * 3 / 5
    assert a_tot == 146000
    B.add(micro=S("partnership-accounts"), level="L4", group=g,
          stem=case + (f"From 1 April 2026 they sign a deed: interest on (fixed) capital at 10% p.a., salary to Bela ₹60,000 a year, and profits in the ratio 3:2. "
                       f"If FY 2026-27 profit (after loan interest) is {R(p2)}, Arjun's total credit for the year (interest on capital plus share of profit) is:"),
          correct=R(a_tot),
          wrongs=[(R(ioc[0] + (p2 - sum(ioc)) * 3 / 5), "Bela's salary not appropriated before sharing"),
                  (R(ioc[0] + rem2 / 2), "old equal ratio used"),
                  (R(p2 * 3 / 5), "appropriations ignored; whole profit split 3:2")],
          steps=[f"Interest on capital: A {inr(ioc[0])}, B {inr(ioc[1])}; salary B {inr(sal)}",
                 f"Residual = {inr(p2)} − {inr(sum(ioc))} − {inr(sal)} = {inr(rem2)}; A's 3/5 = {inr(rem2*3/5)}",
                 f"A total = {inr(a_tot)}"],
          formula="Residual profit = Profit − IOC − Salary; shared in agreed ratio", trap="Appropriations come before the residual split.")
    stmt(B, S("partnership-accounts"), "L4", case + "Under the deed from 1 April 2026 the firm maintains fixed capital accounts. Consider:",
         ["Interest on capital, Bela's salary and shares of profit are credited to the partners' current accounts.",
          "Drawings are debited to the partners' capital accounts.",
          "A partner's current account may show a debit balance."],
         [1, 3], [([1, 2], "debits drawings to fixed capital"), ([2, 3], "denies current-account credits"),
                  ([1, 2, 3], "debits drawings to fixed capital")],
         ["Fixed capital method: capital changes only for additions/withdrawals of capital.",
          "Recurring items — interest, salary, profit, drawings — go to current accounts, which can turn debit."],
         "Drawings go to current accounts under the fixed capital method.", group=g)

    # ================= Schedule III standalone =================
    match(B, S("schedule-iii"), "L2", "Match each item with its head under Schedule III (Division I, as amended in 2021):",
          ["Current maturities of long-term borrowings", "Unpaid dividends", "Capital advances", "Loose tools"],
          ["Inventories", "Long-term loans and advances", "Other current liabilities", "Short-term borrowings"],
          [4, 3, 2, 1],
          [([3, 4, 2, 1], "pre-2021 placement of current maturities under other current liabilities"),
           ([4, 3, 1, 2], "loose tools treated as non-current and advances as inventory"),
           ([4, 2, 3, 1], "unpaid dividend and capital advances interchanged")],
          ["Current maturities of long-term debt → short-term borrowings (2021 amendment).", "Unpaid dividends → other current liabilities.",
           "Capital advances → long-term loans and advances (Division I).", "Loose tools → inventories."],
          "The 2021 amendment moved current maturities to short-term borrowings.", verify_fact=True,
          ref="Schedule III Division I (amended 24-03-2021) — Part I; capital advances under long-term loans and advances")

    tl, inst_n, inst, acc_int = 6000000, 12, 500000, 120000
    ltb = tl - 2 * inst
    B.add(micro=S("schedule-iii"), level="L3",
          stem=(f"At 31 March 2026 a term loan of {lakh(tl)} is outstanding, repayable in {inst_n} equal half-yearly instalments of {lakh(inst)} starting "
                f"30 September 2026. Interest accrued but not due is {lakh(acc_int)}. The operating cycle is 12 months. Under Schedule III the amount shown "
                "under 'Long-term borrowings' is:"),
          correct=lakh(ltb),
          wrongs=[(lakh(tl), "current maturities not reclassified"),
                  (lakh(tl - inst), "only one instalment treated as due within 12 months"),
                  (lakh(ltb + acc_int), "accrued interest added to long-term borrowings")],
          steps=["Instalments due within 12 months: 30 Sep 2026 and 31 Mar 2027 = 2 × ₹5 lakh.",
                 f"Long-term borrowings = {lakh(tl)} − {lakh(2*inst)} = {lakh(ltb)}; accrued interest → other current (financial) liabilities."],
          formula="Current if due within 12 months after the reporting date", trap="Half-yearly instalments: two fall within 12 months.",
          ref="Schedule III — current/non-current classification")

    # ---- Case C7: Meridian ----
    g = "ACC-C7-MERIDIAN"
    esc, arrears, spr_m, gr_m, op_s, pfy, idv, sam = 5000000, 40000, 800000, 1200000, 350000, 920000, 250000, 150000
    debs, cur_deb, int_due, cred, bp, ud, grat_nc, grat_c = 2000000, 400000, 120000, 740000, 160000, 30000, 210000, 40000
    rs = spr_m + gr_m + (op_s + pfy - idv)
    shc = esc - arrears
    ocl = int_due + ud
    tcl = cur_deb + (cred + bp) + ocl + grat_c
    assert (rs, shc, ocl, tcl) == (3020000, 4960000, 150000, 1490000)
    case = ("**Case — Meridian Ltd (Schedule III, Division I).** Extract of balances at 31 March 2026:\n\n" +
            table(["Item", "₹"], [["Equity share capital: 5,00,000 shares of ₹10 each, called up", inr(esc)],
                                  ["Calls in arrears", inr(arrears)], ["Securities premium", inr(spr_m)], ["General reserve", inr(gr_m)],
                                  ["Surplus in P&L, 1 April 2025", inr(op_s)], ["Profit for the year", inr(pfy)],
                                  ["Interim dividend paid during the year", inr(idv)],
                                  ["Share application money pending allotment (not refundable)", inr(sam)],
                                  [f"12% Debentures (of which {inr(cur_deb)} redeemable on 30 September 2026)", inr(debs)],
                                  ["Interest accrued and due on debentures", inr(int_due)], ["Trade creditors", inr(cred)],
                                  ["Bills payable (to suppliers)", inr(bp)], ["Unpaid (unclaimed) dividend", inr(ud)],
                                  ["Provision for gratuity — payable beyond 12 months", inr(grat_nc)],
                                  ["Provision for gratuity — payable within 12 months", inr(grat_c)]]) + "\n\n")
    B.add(micro=S("schedule-iii"), level="L4", group=g, stem=case + "'Reserves and surplus' in the balance sheet amounts to:",
          correct=R(rs),
          wrongs=[(R(rs + sam), "share application money pending allotment included"),
                  (R(rs + idv), "interim dividend not deducted from surplus"),
                  (R(rs - spr_m), "securities premium shown with share capital")],
          steps=[f"Surplus = {inr(op_s)} + {inr(pfy)} − {inr(idv)} = {inr(op_s+pfy-idv)}",
                 f"R&S = {inr(spr_m)} + {inr(gr_m)} + {inr(op_s+pfy-idv)} = {inr(rs)}",
                 "Share application money pending allotment is a separate line under shareholders' funds."],
          formula="R&S = Capital reserves + SPR + Other reserves + Surplus", trap="SAM pending allotment is not a reserve.")
    B.add(micro=S("schedule-iii"), level="L4", group=g, stem=case + "Share capital (subscribed and paid-up) shown on the face of the balance sheet is:",
          correct=R(shc),
          wrongs=[(R(esc), "calls in arrears not deducted"),
                  (R(esc - arrears + sam), "share application money added to share capital"),
                  (R(esc + arrears), "calls in arrears added")],
          steps=[f"Called-up {inr(esc)} − calls in arrears {inr(arrears)} = {inr(shc)}"],
          formula="Paid-up = Called-up − Calls unpaid", trap="SAM becomes capital only on allotment.")
    B.add(micro=S("schedule-iii"), level="L4", group=g, stem=case + "Applying Schedule III as amended in 2021 (current maturities of long-term borrowings are shown under 'Short-term borrowings'), 'Other current liabilities' amount to:",
          correct=R(ocl),
          wrongs=[(R(ocl + cur_deb), "current maturities of debentures shown here (pre-2021 presentation)"),
                  (R(ocl + bp), "bills payable to suppliers shown here instead of trade payables"),
                  (R(ocl + grat_c), "current gratuity provision shown here instead of short-term provisions")],
          steps=[f"Interest accrued and due {inr(int_due)} + unpaid dividend {inr(ud)} = {inr(ocl)}",
                 "Current maturities → short-term borrowings; bills payable → trade payables; gratuity → short-term provisions."],
          formula="Schedule III Division I classification", trap="Each current item has its own specific head.",
          verify_fact=True, ref="Schedule III Division I (amended 2021)")
    B.add(micro=S("schedule-iii"), level="L4", group=g, stem=case + "Total current liabilities are:",
          correct=R(tcl),
          wrongs=[(R(tcl - cur_deb), "debentures redeemable within 12 months left in long-term borrowings"),
                  (R(tcl - bp), "bills payable omitted from trade payables"),
                  (R(tcl + grat_nc), "non-current gratuity provision included")],
          steps=[f"Short-term borrowings {inr(cur_deb)} + trade payables {inr(cred+bp)} + OCL {inr(ocl)} + short-term provisions {inr(grat_c)} = {inr(tcl)}"],
          formula="Current liabilities = STB + Trade payables + OCL + Short-term provisions", trap="Classify by 12-month settlement.")

    # ================= Statement of profit and loss =================
    B.add(micro=S("statement-of-profit"), level="L2",
          stem="Under Schedule III (Division I), the correct sequence in the statement of profit and loss is:",
          correct="Before exceptional & extraordinary items and tax → Exceptional → Extraordinary → Profit before tax",
          wrongs=[("Profit before tax → Exceptional items → Extraordinary items → Profit after tax", "exceptional and extraordinary items placed after tax line"),
                  ("Before exceptional & extraordinary items and tax → Exceptional and extraordinary combined → PBT", "exceptional and extraordinary items merged into one line"),
                  ("Before exceptional & extraordinary items and tax → Extraordinary → Exceptional → Profit before tax", "extraordinary items before exceptional items")],
          steps=["Division I presents exceptional items first, then extraordinary items, both above tax.",
                 "Division II (Ind AS) has exceptional items only — Ind AS 1 prohibits extraordinary items."],
          formula="Schedule III Part II format", trap="Ind AS formats have no extraordinary items.", kind="conceptual",
          verify_fact=True, ref="Schedule III Division I, Part II")

    gross, gst, oi, mat, ofg, cfg, emp, fin, dep, oth, exc = 9440000, 0.18, 200000, 4200000, 500000, 650000, 1200000, 300000, 400000, 750000, 200000
    rev = gross / (1 + gst)
    chg = ofg - cfg
    expn = mat + chg + emp + fin + dep + oth
    pbt = rev + oi - expn - exc
    assert round(rev) == 8000000 and round(pbt) == 1300000
    B.add(micro=S("statement-of-profit"), level="L3",
          stem=("Extracts for Pallav Ltd (FY 2025-26):\n\n" +
                table(["Item", "₹"], [["Sales invoiced, inclusive of GST at 18%", inr(gross)], ["Interest income", inr(oi)],
                                      ["Cost of materials consumed", inr(mat)], ["Opening finished goods", inr(ofg)], ["Closing finished goods", inr(cfg)],
                                      ["Employee benefits expense", inr(emp)], ["Finance costs", inr(fin)], ["Depreciation", inr(dep)],
                                      ["Other expenses", inr(oth)], ["Uninsured loss of stock in a fire (disclosed as exceptional)", inr(exc)]]) +
                "\n\nProfit before tax in the statement of profit and loss is:"),
          correct=R(pbt),
          wrongs=[(R(pbt + gross - rev), "GST included in revenue from operations"),
                  (R(pbt - 2 * (cfg - ofg)), "change in inventories taken with the wrong sign"),
                  (R(pbt + exc), "exceptional loss excluded from PBT")],
          steps=[f"Revenue from operations = {inr(gross)} ÷ 1.18 = {inr(rev)}",
                 f"Change in inventories = {inr(ofg)} − {inr(cfg)} = {inr(chg)} (a credit)",
                 f"Expenses = {inr(expn)}; Profit before exceptional items = {inr(rev + oi - expn)}",
                 f"PBT = {inr(rev + oi - expn)} − {inr(exc)} = {inr(pbt)}"],
          formula="PBT = Revenue + Other income − Expenses ± Exceptional items", trap="GST collected is not revenue; an inventory increase reduces expenses.")
