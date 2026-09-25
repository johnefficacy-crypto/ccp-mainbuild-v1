"""Part 3: capital — prospectus, RHP, shelf, s.39, private placement, s.23/62/63, demat,
preference shares, s.52, reduction, charges, s.71, s.44, s.46, transfer."""
from cab_common import *  # noqa


def add_all(B):
    # ------------------------------------------------------------------ preference shares
    B.add(M["pref"], "L1",
          "Under s.55 of the Companies Act, 2013, a company limited by shares (other than one engaged in infrastructure projects) may issue preference shares that are:",
          "Redeemable within 20 years from the date of issue",
          [("Irredeemable, if authorised by the articles", "irredeemable preference shares are prohibited"),
           ("Redeemable within a period not exceeding 30 years", "infrastructure-project tenure applied to all companies"),
           ("Redeemable within a period not exceeding 10 years", "confuses with the tenure of secured debentures")],
          ["s.55(1): no company limited by shares shall issue irredeemable preference shares.",
           "s.55(2): preference shares liable to be redeemed within 20 years (infrastructure companies: up to 30 years, subject to Rule 10)."],
          "s.55(1), (2)", "The 30-year tenure is only for Schedule VI infrastructure projects.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.55(1), (2)")

    face = 300e7
    ann = 0.10 * face
    B.add(M["pref"], "L2",
          f"Setu Highways Ltd, engaged in a Schedule VI infrastructure project, issues preference shares of {cr(face)} with a 30-year tenure. Under Rule 10 of the Companies (Share Capital and Debentures) Rules, 2014, the redemption requirement is:",
          f"At least 10% ({cr(ann)}) a year from the 21st year onwards",
          [(f"Redemption of 5% ({cr(0.05*face)}) per year from the 11th year onwards", "wrong percentage and start year"),
           (f"Bullet redemption of {cr(face)} at the end of the 30th year", "ignores the mandatory annual redemption from year 21"),
           (f"Redemption of 10% ({cr(ann)}) per year from the 1st year", "starts redemption from issue")],
          ["Rule 10: infrastructure companies may issue preference shares for up to 30 years subject to redemption of minimum 10% annually beginning from the 21st year onwards or earlier, proportionately, at the option of the holders.",
           f"10% of {cr(face)} = {cr(ann)} per year; years 21–30 = 10 instalments."],
          "Annual redemption ≥ 10% from year 21", "Ten annual tranches of 10% exactly exhaust the issue by year 30.",
          verify_fact=True, ref="Companies (Share Capital and Debentures) Rules 2014, Rule 10; s.55(2) proviso; Schedule VI")

    # ------------------------------------------------------------------ private placement
    offered = [("Individual investors (identified persons)", 180), ("Qualified institutional buyers", 30), ("Employees under an ESOP scheme (s.62(1)(b))", 25)]
    cnt = 180
    B.add(M["pp"], "L2",
          "Nirmal Agrotech Ltd (unlisted public company) proposes a private placement of equity shares in FY 2026-27, its first private offer of equity in the year:\n\n"
          + table(["Offerees", "Number"], [[a, b] for a, b in offered], ["---", "---:"])
          + "\n\nFor the ceiling on the number of persons under s.42(2) read with Rule 14, the number of persons counted is:",
          f"{cnt}, within the ceiling of 200",
          [(f"{cnt+30+25}, exceeding the ceiling of 200", "QIBs and ESOP employees counted"),
           (f"{cnt+25}, exceeding the ceiling of 200", "ESOP employees counted"),
           (f"{cnt}, exceeding the ceiling of 50 persons", "repealed 49/50-person private-offer limit applied")],
          ["s.42(2) proviso and Rule 14(2)(b): offer to not more than 200 persons in aggregate in a FY, excluding QIBs and employees offered under an ESOP scheme under s.62(1)(b).",
           f"Counted = {cnt} individuals ≤ 200."],
          "Count = offerees − QIBs − ESOP employees; ceiling 200 per FY", "The ceiling is per kind of security per financial year.",
          verify_fact=True, ref="Companies Act 2013 s.42(2); PAS Rules 2014, Rule 14(2)(b)")

    B.add(M["pp"], "L1",
          stmts("Consider the following regarding a private placement offer under s.42:",
                ["The private placement offer-cum-application letter is issued in Form PAS-4 and is addressed specifically to identified persons.",
                 "The offer may be renounced in favour of any other person by the addressee.",
                 "Payment for securities shall be made from the bank account of the subscriber and not in cash."]),
          "1 and 3 only",
          [("1, 2 and 3", "treats a private placement offer as renounceable like a rights offer"),
           ("1 only", "overlooks the bar on cash payment"),
           ("2 and 3 only", "overlooks PAS-4 and identified persons")],
          ["Rule 14: offer letter in PAS-4, serially numbered and addressed to the identified person.",
           "s.42(7)/Rule 14: not renounceable; a person other than the addressee cannot apply.",
           "s.42(4): payment through cheque/demand draft/other banking channels, not cash."],
          "s.42; Rule 14", "Renounceability is a feature of rights issues under s.62, not private placement.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.42(4), (7); PAS Rules 2014, Rule 14")

    # ------------------------------------------------------------------ prospectus matters
    filed = d(2026, 2, 10)
    B.add(M["prosp"], "L1",
          f"A copy of the prospectus of Everest Solar Ltd was delivered to the Registrar on {ds(filed)}. Under s.26(8), the prospectus will not be valid if it is issued after:",
          f"90 days from delivery, i.e. after {ds(plus(filed,90))}",
          [(f"30 days from delivery, i.e. after {ds(plus(filed,30))}", "wrong period"),
           (f"180 days from delivery, i.e. after {ds(plus(filed,180))}", "wrong period"),
           ("One year from the date of delivery to the Registrar", "confuses with shelf-prospectus validity")],
          ["s.26(8): no prospectus shall be valid if issued more than 90 days after the date on which a copy is delivered to the Registrar."],
          "s.26(8)", "One year is the shelf prospectus validity (s.31), not s.26.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.26(8)")

    B.add(M["prosp"], "L2",
          stmts("A prospectus of Meghna Foods Ltd includes a valuation statement purporting to be made by an expert. Consider:",
                ["The expert must be a person who is not, and has not been, engaged or interested in the formation or promotion or management of the company.",
                 "The expert must have given written consent to the issue of the prospectus containing the statement and must not have withdrawn it before delivery to the Registrar.",
                 "A statement that the expert has given and not withdrawn consent must appear in the prospectus."]),
          "1, 2 and 3",
          [("1 and 2 only", "misses the requirement to state consent in the prospectus"),
           ("2 and 3 only", "misses the independence requirement"),
           ("2 only", "treats consent as the only condition")],
          ["s.26(5): expert must not be engaged/interested in formation, promotion or management.",
           "s.26(5): written consent given and not withdrawn before delivery; statement to that effect in the prospectus."],
          "s.26(5)", "All three conditions are cumulative.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.26(5)")

    # ------------------------------------------------------------------ s.23 / rights / bonus
    B.add(M["s23"], "L1",
          "Under s.23 of the Companies Act, 2013, a private company may issue securities:",
          "By way of rights issue or bonus issue, or through private placement",
          [("Through a public offer by prospectus, private placement, or rights/bonus issue", "public-company modes attributed to a private company"),
           ("Only through a rights issue", "omits bonus and private placement"),
           ("Through a public offer if its articles permit", "private company prohibited from inviting the public")],
          ["s.23(1): public company — prospectus (public offer), private placement, or rights/bonus.",
           "s.23(2): private company — rights or bonus issue, or private placement."],
          "s.23(1), (2)", "A private company can never make a public offer.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.23")

    B.add(M["s23"], "L3",
          stmts("Tara Instruments Ltd makes a rights offer to existing equity shareholders under s.62(1)(a). Consider:",
                ["The offer must be made by notice specifying the number of shares offered and limiting a time within which it must be accepted, which cannot exceed 30 days.",
                 "Unless the articles provide otherwise, the offer includes a right to renounce the shares in favour of any other person.",
                 "The notice must be dispatched at least three days before the opening of the issue.",
                 "Shares not taken up may be disposed of by the Board in a manner not dis-advantageous to shareholders and the company."]),
          "1, 2, 3 and 4",
          [("1, 2 and 3 only", "overlooks disposal of unsubscribed shares by the Board"),
           ("1 and 3 only", "treats renunciation as available only if articles expressly permit"),
           ("2, 3 and 4 only", "overlooks the 30-day upper limit")],
          ["s.62(1)(a)(i): offer period — at most 30 days.",
           "s.62(1)(a)(ii): right of renunciation unless articles provide otherwise.",
           "s.62(2): notice dispatched at least three days before opening.",
           "s.62(1)(a)(iii): Board may dispose of unsubscribed shares in a non-disadvantageous manner."],
          "s.62(1)(a), (2)", "Renunciation is the default; articles can exclude it.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.62(1)(a), (2)")

    res = [("Securities premium", 18e7, True), ("General reserve (free)", 42e7, True), ("Capital redemption reserve", 6e7, True),
           ("Revaluation reserve", 15e7, False), ("Retained earnings (free)", 9e7, True)]
    cap = sum(v for _, v, ok in res if ok)
    pu = 60e7
    ratio_num = cap / pu
    assert round(cap) == 75e7
    B.add(M["s23"], "L3",
          f"Vasudha Textiles Ltd has fully paid-up equity capital of {cr(pu)} (shares of ₹10). Its reserves are:\n\n"
          + table(["Reserve", "₹ crore"], [[n, f"{v/1e7:.0f}"] for n, v, _ in res], ["---", "---:"])
          + "\n\nIgnoring any cushion the Board may choose to retain, the maximum amount available for a bonus issue under s.63(1) is:",
          cr(cap),
          [(cr(cap + 15e7), "revaluation reserve included"),
           (cr(cap - 6e7), "capital redemption reserve excluded"),
           (cr(cap - 18e7), "securities premium excluded")],
          ["s.63(1): bonus shares may be issued out of (i) free reserves, (ii) securities premium account, (iii) capital redemption reserve account.",
           "Proviso: no bonus shares by capitalising reserves created by revaluation of assets.",
           f"Available = 18 + 42 + 6 + 9 = {cr(cap)} (a 5 : 4 bonus at most on {cr(pu)})."],
          "Bonus sources = Free reserves + SP + CRR (excluding revaluation reserve)",
          "CRR and securities premium are not free reserves but are expressly allowed for bonus.",
          verify_fact=True, ref="Companies Act 2013 s.63(1)")

    B.add(M["s23"], "L3",
          stmts("Consider the conditions for a bonus issue under s.63(2):",
                ["The bonus issue must be authorised by the articles and, on the recommendation of the Board, authorised in general meeting.",
                 "The company must not have defaulted in payment of interest or principal on fixed deposits or debt securities issued by it.",
                 "The company must not have defaulted in payment of statutory dues of employees such as provident fund, gratuity and bonus.",
                 "Bonus shares may be issued in lieu of dividend if the shareholders so resolve."]),
          "1, 2 and 3 only",
          [("1 and 2 only", "overlooks the employee statutory-dues condition"),
           ("1, 2, 3 and 4", "bonus in lieu of dividend allowed"),
           ("2, 3 and 4 only", "drops articles/GM authorisation and allows bonus in lieu of dividend")],
          ["s.63(2)(a)-(f): articles authorisation; GM authorisation on Board recommendation; no default on FD/debt securities; no default on employee statutory dues; partly paid shares made fully paid; other prescribed conditions.",
           "s.63(5): bonus shares shall not be issued in lieu of dividend."],
          "s.63(2), (5)", "Bonus cannot substitute a dividend.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.63(2), (5)")

    # ------------------------------------------------------------------ demat
    B.add(M["demat"], "L1",
          "Section 29(1) of the Companies Act, 2013 requires securities to be issued only in dematerialised form by:",
          "Every company making a public offer, and other prescribed classes",
          [("Only listed companies, and only for fresh issues of shares", "restricts to listed companies"),
           ("Only companies with paid-up capital of ₹100 crore or more", "invented capital threshold"),
           ("All companies, including OPCs and small companies, without exception", "prescribed-class exemptions ignored")],
          ["s.29(1): every company making public offer and such other class of companies as prescribed shall issue securities only in dematerialised form under the Depositories Act, 1996.",
           "Rules 9A (unlisted public companies) and 9B (private companies other than small companies) of the PAS Rules prescribe additional classes."],
          "s.29(1)", "Small companies and OPCs are outside Rule 9B.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.29(1); PAS Rules 2014, Rules 9A, 9B")

    B.add(M["demat"], "L2",
          stmts("Kritika Plastics Ltd is an unlisted public company (not a Nidhi, government company or wholly owned subsidiary). Under Rule 9A of the Companies (Prospectus and Allotment of Securities) Rules, 2014:",
                ["It shall issue securities only in dematerialised form and facilitate dematerialisation of all its existing securities.",
                 "Before making an offer of securities, or a buy-back, bonus or rights issue, it shall ensure that the entire holding of securities of its promoters, directors and key managerial personnel is dematerialised.",
                 "Any holder of its securities who intends to transfer them after the Rule's commencement must get them dematerialised before the transfer."]),
          "1, 2 and 3",
          [("1 and 2 only", "overlooks the demat-before-transfer requirement"),
           ("1 only", "overlooks the promoter/director/KMP holding condition"),
           ("2 and 3 only", "overlooks the issue-only-in-demat requirement")],
          ["Rule 9A(1): issue only in demat; facilitate demat of existing securities.",
           "Rule 9A(2): promoters, directors, KMP holdings to be demat before offer/buy-back/bonus/rights.",
           "Rule 9A(4): holder intending to transfer must get securities dematerialised."],
          "PAS Rule 9A", "Nidhis, government companies and WOS are excluded from Rule 9A.",
          kind="statement", verify_fact=True, ref="PAS Rules 2014, Rule 9A")

    # ------------------------------------------------------------------ shelf / abridged
    B.add(M["shelf"], "L3",
          stmts("A public sector bank files a shelf prospectus under s.31. Consider:",
                ["The shelf prospectus is valid for a period not exceeding one year from the date of opening of the first offer of securities under it.",
                 "No further prospectus is required for second and subsequent offers during the validity period.",
                 "Before each subsequent offer, an information memorandum containing material facts such as new charges created and changes in financial position must be filed.",
                 "Only public financial institutions can file a shelf prospectus."]),
          "1, 2 and 3 only",
          [("1 and 2 only", "overlooks the information memorandum requirement"),
           ("1, 2, 3 and 4", "restricts shelf prospectus to PFIs only"),
           ("2 and 3 only", "overlooks the one-year validity")],
          ["s.31(1): class of companies as SEBI may provide by regulations may file a shelf prospectus; validity ≤ one year from opening of first offer; no further prospectus for subsequent offers.",
           "s.31(2): information memorandum on material changes before each subsequent offer.",
           "Banks and PFIs are among eligible issuers, not the only ones."],
          "s.31", "Validity runs from opening of the first offer, not from filing.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.31")

    B.add(M["shelf"], "L1",
          "Under s.33(1), no form of application for the purchase of securities of a company shall be issued unless it is accompanied by:",
          "An abridged prospectus (memorandum of salient features)",
          [("A copy of the red herring prospectus filed with the RoC", "confuses with s.32"),
           ("The full prospectus signed by every director", "full prospectus need be supplied only on request"),
           ("The information memorandum filed for the issue", "confuses with shelf-prospectus filings")],
          ["s.33(1): application form must be accompanied by an abridged prospectus.",
           "Exception: form issued in connection with bona fide underwriting or where securities are not offered to the public.",
           "s.33(2): a copy of the prospectus is furnished on request before closing of the subscription list."],
          "s.33(1)", "Full prospectus = on request; abridged prospectus = with every form.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.33")

    # ------------------------------------------------------------------ RHP s.32
    op = d(2026, 11, 16)
    last = plus(op, -3)
    B.add(M["rhp"], "L2",
          f"The subscription list of Parth Digital Ltd's public issue is to open on {ds(op)}. Under s.32(2), the latest date by which its red herring prospectus must be filed with the Registrar is:",
          ds(last),
          [(ds(plus(op, -1)), "one day instead of three days before opening"),
           (ds(plus(op, -7)), "seven days used"),
           (ds(plus(op, -30)), "thirty days used")],
          ["s.32(2): RHP shall be filed with the Registrar at least three days prior to the opening of the subscription list and the offer.",
           f"{ds(op)} − 3 days = {ds(last)}."],
          "Filing date ≤ Opening date − 3 days", "Count back three clear days from the opening date.",
          verify_fact=True, ref="Companies Act 2013 s.32(2)")

    B.add(M["rhp"], "L1",
          stmts("Regarding a red herring prospectus under s.32, consider:",
                ["It carries the same obligations as are applicable to a prospectus.",
                 "Any variation between the red herring prospectus and the prospectus shall be highlighted as variations in the prospectus.",
                 "On closing of the offer, a prospectus stating the total capital raised, the closing price of the securities and other details not included in the RHP is filed with the Registrar and SEBI."]),
          "1, 2 and 3",
          [("1 and 2 only", "overlooks post-issue prospectus filing"),
           ("2 and 3 only", "believes RHP carries lesser obligations"),
           ("1 and 3 only", "overlooks highlighting of variations")],
          ["s.32(3): same obligations as a prospectus; variations highlighted.",
           "s.32(4): upon closing, prospectus with total capital raised, closing price etc. filed with Registrar and SEBI."],
          "s.32(3), (4)", "RHP lacks price/quantity details, not legal obligations.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.32(3), (4)")

    # ------------------------------------------------------------------ s.39
    fv, ip = 10, 150
    B.add(M["s39"], "L2",
          f"Under s.39(2), in the absence of any other percentage or amount specified by SEBI, the minimum amount payable on application for an equity share of face value ₹{fv} issued at ₹{ip} is:",
          f"₹{0.05*fv:.2f} per share (5% of nominal amount)",
          [(f"₹{0.05*ip:.2f} per share (5% of issue price)", "5% applied to issue price instead of nominal amount"),
           (f"₹{0.25*ip:.2f} per share (25% of issue price)", "SEBI ICDR requirement applied in place of the Act's default"),
           (f"₹{0.25*fv:.2f} per share (25% of nominal amount)", "25% applied to the nominal amount")],
          ["s.39(2): amount payable on application on every security shall not be less than 5% of the nominal amount of the security or such other percentage/amount as SEBI may specify.",
           f"5% × ₹{fv} = ₹{0.05*fv:.2f}."],
          "Min application money = 5% × nominal value (s.39(2) default)", "The base is nominal (face) value, not issue price.",
          verify_fact=True, ref="Companies Act 2013 s.39(2)")

    B.add(M["s39"], "L1",
          "Under s.39(4) read with Rule 12 of the PAS Rules, a company making an allotment of securities (other than under private placement) must file the return of allotment in Form PAS-3 within:",
          "30 days of allotment",
          [("15 days of allotment", "private-placement period applied"),
           ("60 days of allotment", "confuses with the private-placement allotment period"),
           ("7 days of allotment", "invented period")],
          ["Rule 12(1): return of allotment in PAS-3 within 30 days of allotment.",
           "For private placement, Rule 14 requires PAS-3 within 15 days of allotment."],
          "Rule 12: 30 days", "15 days is the private-placement rule.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.39(4); PAS Rules 2014, Rules 12, 14")

    amt, late = 3.6e7, 40
    B.add(M["s39"], "L3",
          f"Shaurya Pumps Ltd's public issue failed to receive the minimum subscription. Application money of {cr(amt)} that should have been refunded within 15 days of closure of the issue was repaid {late} days after the expiry of that 15-day period. The interest for which the directors who are officers in default are jointly and severally liable under s.39(3) read with Rule 11 is (365-day year):",
          R(interest(amt, 0.15, late)),
          [(R(interest(amt, 0.12, late)), "12% private-placement rate applied"),
           (R(interest(amt, 0.18, late)), "18% dividend-default rate applied"),
           (R(interest(amt, 0.15, late + 15)), "interest counted from closure of the issue")],
          ["Rule 11(2) PAS: if application money is not repaid within 15 days from closure of issue, officers in default are jointly and severally liable to repay with interest @ 15% p.a.",
           f"Interest = {inr(amt)} × 15% × {late}/365 = {R(interest(amt,0.15,late))}."],
          "Interest = Amount × 15% × days of delay/365",
          "15% (s.39 refund), 12% (s.42 refund), 18% (s.127 dividend) — keep the three rates apart.",
          verify_fact=True, ref="Companies Act 2013 s.39(3); PAS Rules 2014, Rule 11")

    # ------------------------------------------------------------------ reduction of capital
    sh, fv0 = 20_00_000, 10
    loss, gw = 1.30e7, 0.20e7
    new_fv = fv0 - (loss + gw) / sh
    assert abs(new_fv - 2.5) < 1e-9
    B.add(M["red"], "L3",
          f"Ojas Foods Ltd has {inr(sh)} fully paid equity shares of ₹{fv0} each. Its balance sheet shows accumulated losses of {cr(loss)} and goodwill of {cr(gw)} with no realisable value. A scheme under s.66 proposes to write off both by reducing the face value of every share. The face value per share after reduction will be:",
          f"₹{new_fv:.2f}",
          [(f"₹{fv0 - loss/sh:.2f}", "goodwill (capital unrepresented by assets) not written off"),
           (f"₹{(loss+gw)/sh:.2f}", "amount of reduction per share reported as the new face value"),
           (f"₹{fv0 - (loss-gw)/sh:.2f}", "goodwill netted off against losses instead of added")],
          [f"Capital to be cancelled = {cr(loss)} + {cr(gw)} = {cr(loss+gw)}.",
           f"Per share = {inr(loss+gw)} ÷ {inr(sh)} = ₹{(loss+gw)/sh:.2f}.",
           f"New face value = ₹{fv0} − ₹{(loss+gw)/sh:.2f} = ₹{new_fv:.2f}. s.66(1)(b)(i): cancel paid-up capital lost or unrepresented by available assets."],
          "New FV = Old FV − (Losses + fictitious assets) ÷ Number of shares",
          "Goodwill with no value is 'capital unrepresented by available assets' and is written off too.",
          verify_fact=True, ref="Companies Act 2013 s.66(1)(b)(i)")

    B.add(M["red"], "L3",
          stmts("Consider the following regarding reduction of share capital under s.66:",
                ["It requires a special resolution and confirmation by the Tribunal.",
                 "No reduction shall be made if the company is in arrears in repayment of any deposits accepted by it or interest payable thereon.",
                 "The Tribunal gives notice to the Central Government, Registrar, SEBI (for listed companies) and creditors; if no representation is received within three months, it is presumed they have no objection.",
                 "Buy-back of shares under s.68 is also governed by s.66."]),
          "1, 2 and 3 only",
          [("1 and 2 only", "overlooks the three-month deemed no-objection"),
           ("1, 2, 3 and 4", "applies s.66 to buy-back"),
           ("2, 3 and 4 only", "overlooks the special resolution + Tribunal route")],
          ["s.66(1): SR + Tribunal confirmation; proviso — no reduction while deposit arrears exist.",
           "s.66(2): notice to CG, Registrar, SEBI (listed) and creditors; representations within three months, else presumed no objection.",
           "s.66(8): nothing in s.66 applies to buy-back under s.68."],
          "s.66(1), (2), (8)", "Buy-back is a separate code under s.68–70.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.66")

    # ------------------------------------------------------------------ charges
    c0 = d(2026, 1, 10)
    fdate = d(2026, 3, 25)
    gap = (fdate - c0).days
    assert 60 < gap <= 120
    B.add(M["chg"], "L2",
          f"Arjun Forgings Ltd created a charge on its plant in favour of a bank on {ds(c0)} but files Form CHG-1 on {ds(fdate)} ({gap} days after creation). Under s.77 (as amended in 2019), registration is:",
          "Possible with ad valorem fees, within the further 60-day window",
          [("Possible with normal fees, as it is within 90 days of creation", "invented 90-day normal window"),
           ("Possible only with additional fees, as it is within 120 days of creation", "additional-fee window (31–60 days) confused with ad valorem window"),
           ("Not possible; only the Tribunal can condone the delay", "Registrar's power under the third proviso overlooked")],
          ["s.77(1): register within 30 days of creation.",
           "First proviso (b): Registrar may allow within 60 days of creation on payment of additional fees.",
           "Third proviso: if not registered within 60 days, Registrar may allow within a further 60 days on payment of ad valorem fees.",
           f"{gap} days falls in the 61–120 day band → ad valorem fees."],
          "30 days (normal) → up to 60 days (additional fees) → up to 120 days (ad valorem fees)",
          "The 2019 amendment replaced the old 300-day window.",
          verify_fact=True, ref="Companies Act 2013 s.77(1) and provisos (Companies (Amendment) Act 2019)")

    B.add(M["chg"], "L2",
          stmts("Consider the following in respect of registration of charges:",
                ["A charge required to be registered but not registered shall not be taken into account by the liquidator or any creditor, but the obligation to repay the money secured is not affected.",
                 "The company must intimate the Registrar of payment or satisfaction in full of a registered charge within 30 days of such payment or satisfaction.",
                 "Registration of a charge operates as constructive notice of the charge to any person acquiring the property."]),
          "1, 2 and 3",
          [("1 and 3 only", "overlooks the 30-day satisfaction intimation"),
           ("2 and 3 only", "believes the debt itself is extinguished if unregistered"),
           ("1 and 2 only", "overlooks constructive notice under s.80")],
          ["s.77(3): unregistered charge ignored by liquidator/creditors; s.77(4) debt remains.",
           "s.82(1): satisfaction intimated within 30 days (Form CHG-4).",
           "s.80: registration = notice of the charge to anyone acquiring the property."],
          "s.77(3)-(4), s.80, s.82", "Non-registration voids the security, not the debt.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.77(3), (4); s.80; s.82")

    # ------------------------------------------------------------------ s.71 debentures
    out_d, mat = 50e7, 20e7
    drr, dep15 = 0.10 * out_d, 0.15 * mat
    B.add(M["s71"], "L3",
          f"Gaurav Cables Pvt Ltd (unlisted; not an NBFC or HFC) has privately placed secured debentures outstanding of {cr(out_d)}. Debentures of {cr(mat)} mature during the year ending 31 March 2028. Under Rule 18(7) of the Companies (Share Capital and Debentures) Rules, 2014, the Debenture Redemption Reserve required and the amount to be invested/deposited on or before 30 April 2027 are, respectively:",
          f"{cr(drr)} and {cr(dep15)}",
          [(f"{cr(0.25*out_d)} and {cr(dep15)}", "pre-2019 25% DRR rate used"),
           (f"{cr(drr)} and {cr(0.15*out_d)}", "15% applied on total outstanding instead of amount maturing"),
           (f"Nil and {cr(dep15)}", "listed-company DRR exemption applied to an unlisted company")],
          ["Rule 18(7)(b)(iv)(B): unlisted companies (other than NBFC/HFC) — DRR of 10% of outstanding debentures.",
           f"DRR = 10% × {cr(out_d)} = {cr(drr)}.",
           f"Rule 18(7)(vii): invest/deposit ≥ 15% of debentures maturing during the year ending 31 March of the next year, on or before 30 April → 15% × {cr(mat)} = {cr(dep15)}."],
          "DRR = 10% of outstanding; deposit = 15% of amount maturing next year",
          "Listed companies are exempt from DRR but not from the 15% deposit.",
          verify_fact=True, ref="Companies (Share Capital and Debentures) Rules 2014, Rule 18(7) (as amended 2019)")

    B.add(M["s71"], "L1",
          "Under s.71(5), a company must appoint one or more debenture trustees before issuing a prospectus or making an offer or invitation for subscription of its debentures:",
          "To the public, or to its members exceeding five hundred",
          [("To more than 200 persons in a financial year", "private-placement ceiling confused"),
           ("Only where the debentures are unsecured", "security status is not the trigger"),
           ("To the public, or to its members exceeding fifty", "old 49/50 limit used")],
          ["s.71(5): no company shall issue a prospectus or make an offer/invitation to the public or to its members exceeding 500 for subscription of debentures unless it has appointed debenture trustee(s)."],
          "s.71(5)", "Trigger = public offer or offer to > 500 members.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.71(5)")

    B.add(M["s71"], "L3",
          stmts("Consider the following regarding debentures under s.71:",
                ["Debentures carrying an option to convert wholly or partly into shares may be issued only with the approval of a special resolution passed at a general meeting.",
                 "A company may issue debentures carrying voting rights if its articles so permit.",
                 "Secured debentures may be issued only if the security is created on specific movable or immovable property of the company, or of its holding/subsidiary/associate, of value sufficient for due repayment of the amount and interest."]),
          "1 and 3 only",
          [("1, 2 and 3", "allows voting rights on debentures"),
           ("1 only", "overlooks the security-cover condition in Rule 18"),
           ("2 and 3 only", "overlooks the special-resolution requirement for convertibles")],
          ["s.71(1): conversion option — special resolution in general meeting.",
           "s.71(2): no company shall issue debentures carrying voting rights.",
           "Rule 18(1): security by charge on specific assets (including those of holding/subsidiary/associate) sufficient for repayment of principal and interest."],
          "s.71(1), (2); Rule 18(1)", "Debentures never carry voting rights.",
          kind="statement", verify_fact=True, ref="Companies Act 2013 s.71(1), (2); SCD Rules 2014, Rule 18(1)")

    # ------------------------------------------------------------------ s.44
    B.add(M["s44"], "L1",
          "Under s.44 of the Companies Act, 2013, the shares, debentures or other interest of any member in a company are:",
          "Movable property, transferable as provided by the articles",
          [("Immovable property, transferable only by registered deed", "wrong nature of property"),
           ("Actionable claims, not transferable without consent of the company", "wrong classification and restriction"),
           ("Movable property, freely transferable irrespective of the articles", "ignores the articles' role")],
          ["s.44: shares/debentures/other interest of a member are movable property transferable in the manner provided by the articles."],
          "s.44", "The articles regulate the manner of transfer (subject to s.56/s.58).",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.44")

    # ------------------------------------------------------------------ s.46
    B.add(M["s46"], "L2",
          "A shareholder of Chandan Paints Ltd (an unlisted public company holding physical certificates) applies for a duplicate share certificate. Under Rule 6 of the Companies (Share Capital and Debentures) Rules, 2014, the company must issue it within:",
          "3 months (lost/destroyed); 30 days (defaced/mutilated, surrendered)",
          [("30 days from application in every case, lost or mutilated", "uniform period assumed"),
           ("Three months from application in every case, lost or mutilated", "uniform period assumed"),
           ("15 days if lost or destroyed; 7 days if defaced or mutilated", "invented periods")],
          ["Rule 6(3)(a): duplicate within 3 months of submission of complete documents (lost/destroyed) or within 30 days of application (defaced, mutilated, torn, decrepit, worn out, or transfer pages fully used)."],
          "SCD Rule 6(3)(a)", "Loss cases need more time for verification; mutilated certificates are surrendered.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.46(2); SCD Rules 2014, Rule 6(3)")

    n, fvv = 80_000, 10
    face = n * fvv
    mn = 5 * face
    mx = max(10 * face, 10e7)
    B.add(M["s46"], "L3",
          f"Chandan Paints Ltd, with intent to defraud, issued a duplicate certificate for {inr(n)} shares of face value ₹{fvv} each. Under s.46(5), the company is punishable with fine of:",
          f"Not less than {R(mn)} but which may extend to {cr(mx)}",
          [(f"Not less than {R(face)} but which may extend to {R(10*face)}", "minimum taken as 1× face value and ₹10 crore alternative ignored"),
           (f"Not less than {R(mn)} but which may extend to {R(10*face)}", "₹10 crore 'whichever is higher' alternative ignored"),
           (f"Not less than {cr(10e7)} but which may extend to {cr(25e7)}", "invented fixed band")],
          [f"Face value involved = {inr(n)} × ₹{fvv} = {R(face)}.",
           f"Minimum = 5 × face value = {R(mn)}.",
           f"Maximum = higher of 10 × face value ({R(10*face)}) and ₹10 crore = {cr(mx)}.",
           "Every officer in default is liable under s.447."],
          "Fine: ≥ 5 × FV; ≤ max(10 × FV, ₹10 crore)", "The ₹10 crore is an alternative maximum, 'whichever is higher'.",
          verify_fact=True, ref="Companies Act 2013 s.46(5)")

    # ------------------------------------------------------------------ s.52
    op_sp = 8e7
    uses = [("Fully paid bonus shares issued", 3e7, True), ("Expenses of a share issue written off", 0.4e7, True),
            ("Premium on redemption of debentures provided", 0.6e7, True), ("Interim dividend proposed", 1e7, False)]
    close = op_sp - sum(v for _, v, ok in uses if ok)
    assert round(close) == 4e7
    B.add(M["s52"], "L3",
          f"Pallavi Cements Ltd (not a company of any class prescribed under s.52(3)) has a securities premium balance of {cr(op_sp)}. The Board proposes the following applications:\n\n"
          + table(["Proposed application", "₹ crore"], [[a, f"{v/1e7:.2f}"] for a, v, _ in uses], ["---", "---:"])
          + "\n\nIf only the applications permitted by s.52(2) are carried out, the closing balance of securities premium will be:",
          cr(close),
          [(cr(close - 1e7), "interim dividend treated as a permitted application"),
           (cr(close + 0.6e7), "premium on redemption of debentures treated as impermissible"),
           (cr(close + 0.4e7), "share-issue expenses treated as impermissible")],
          ["s.52(2): (a) fully paid bonus shares; (b) writing off preliminary expenses; (c) writing off expenses/commission/discount on issue of shares or debentures; (d) premium on redemption of preference shares or debentures; (e) buy-back under s.68.",
           f"Permitted: 3.00 + 0.40 + 0.60 = 4.00; dividend not permitted. Closing = {cr(close)}."],
          "Closing SP = Opening − permitted s.52(2) applications", "Securities premium can never fund a dividend.",
          verify_fact=True, ref="Companies Act 2013 s.52(2)")

    B.add(M["s52"], "L2",
          "Which of the following is a permitted application of the securities premium account under s.52(2)?",
          "Purchase of the company's own shares under s.68",
          [("Payment of dividend on preference shares", "dividend not permitted"),
           ("Writing off accumulated trading losses", "loss write-off is a reduction of capital requiring s.66"),
           ("Paying up partly paid shares held by existing members to make them fully paid", "only unissued shares may be issued as fully paid bonus")],
          ["s.52(2)(e): buy-back under s.68 is a permitted application.",
           "Writing off losses against securities premium amounts to reduction of capital under s.66 (Tribunal route)."],
          "s.52(2)", "s.52(2)(a) covers unissued shares issued as fully paid bonus shares only.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.52(1), (2)")

    # ------------------------------------------------------------------ transfer & transmission
    ex = d(2026, 6, 2)
    B.add(M["xfer"], "L2",
          f"An instrument of transfer (Form SH-4) of physical shares of Vikas Sugar Ltd was executed on {ds(ex)}. Under s.56(1), it must be delivered to the company within:",
          f"60 days from the date of execution, i.e. by {ds(plus(ex,60))}",
          [(f"30 days from execution, i.e. by {ds(plus(ex,30))}", "wrong period"),
           (f"One month from execution, the period for issue of certificates", "confuses with company's certificate-delivery period"),
           (f"90 days from execution, i.e. by {ds(plus(ex,90))}", "confuses with the appeal period on refusal by a public company")],
          ["s.56(1): proper instrument of transfer, duly stamped, dated and executed, delivered within 60 days from date of execution along with the certificate.",
           "s.56(4)(c): company delivers certificates within one month of receipt of the instrument."],
          "s.56(1): 60 days", "60 days (transferor/transferee) vs one month (company).",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.56(1), (4)")

    dl = d(2026, 4, 6)
    B.add(M["xfer"], "L3",
          f"A transferee delivered an instrument of transfer to Saket Enterprises Pvt Ltd (a private company) on {ds(dl)}. The company did not send any notice of refusal and did not register the transfer. Under s.58, the transferee may appeal to the Tribunal within:",
          f"60 days from the date of delivery, i.e. by {ds(plus(dl,60))}",
          [(f"30 days from the date of delivery, i.e. by {ds(plus(dl,30))}", "30-day period (applicable after receipt of a refusal notice) applied"),
           (f"90 days from the date of delivery, i.e. by {ds(plus(dl,90))}", "public-company period of s.58(4) applied"),
           (f"45 days from the date of delivery, i.e. by {ds(plus(dl,45))}", "NCLAT appeal period confused")],
          ["s.58(1)-(3): private company — if refusal notice sent (within 30 days of delivery), appeal within 30 days of receipt of notice; if no notice, within 60 days of delivery.",
           "s.58(4): public company — 60 days from notice, or 90 days from delivery if no notice."],
          "Private: 30 days (notice) / 60 days (no notice); Public: 60 / 90",
          "No-notice periods are longer; private company periods are shorter than public.",
          verify_fact=True, ref="Companies Act 2013 s.58(3), (4)")

    B.add(M["xfer"], "L1",
          "Where an application for transfer of partly paid shares is made by the transferor alone, s.56(3) requires that the transfer shall not be registered unless:",
          "Company notifies the transferee, who gives no objection within two weeks",
          [("The transferee pays the unpaid calls in full before registration", "invented pre-condition"),
           ("The Board passes a special resolution approving the transfer", "confuses with members' resolutions"),
           ("The transferor gives notice to the Registrar in Form SH-4", "SH-4 is the instrument, not a notice to Registrar")],
          ["s.56(3): partly paid shares — application by transferor alone → company notifies transferee; transferee must give no objection within two weeks."],
          "s.56(3)", "Protects the transferee who will become liable for unpaid calls.",
          kind="conceptual", verify_fact=True, ref="Companies Act 2013 s.56(3)")
