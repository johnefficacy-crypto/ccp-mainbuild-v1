"""QRE-QA-A part 2: Profit and Loss incl. SI/CI (5 microtopics; case-set items in qa_a_cases)."""
from fractions import Fraction as Fr
from qa_a_common import N, D, P, Rs, RsD, ratio, make_q


def add_all(B):
    q = make_q(B)

    # ===================== Cost price, selling price and margin =====================
    q("cpsp", "L1", "f", "An article bought for ₹640 is sold for ₹736. The profit percentage is:",
      P(Fr(96, 640) * 100),
      [(P(D(Fr(96, 736) * 100)), "profit divided by selling price"), (P(96), "profit amount read as a percentage"),
       (P(115), "SP as a percentage of CP")],
      ["Profit = 736 − 640 = 96", "96/640 × 100 = 15%"],
      "Profit % = Profit ÷ CP × 100", "Profit % is on cost unless stated otherwise.")

    q("cpsp", "L1", "f", "A chair costing ₹1,250 is sold at a loss of 12%. Its selling price is:",
      Rs(1250 * Fr(88, 100)),
      [(Rs(1250 * Fr(112, 100)), "loss treated as profit"), (Rs(D(Fr(1250) / Fr(112, 100))), "divided by 1.12"),
       (Rs(1250 * Fr(12, 100)), "loss amount reported")],
      ["SP = 1,250 × 0.88 = 1,100"],
      "SP = CP × (1 − loss%)", "Loss reduces the cost by 12%.")

    cp = Fr(1008) / Fr(112, 100)
    assert cp == 900
    q("cpsp", "L2", "f", "Selling a watch for ₹1,008 gives a profit of 12%. To earn 20% profit, it should be sold for:",
      Rs(cp * Fr(12, 10)),
      [(Rs(D(Fr(1008) * Fr(12, 10))), "20% applied on the old SP"), (Rs(D(Fr(1008) * Fr(108, 100))), "extra 8% applied on the old SP"),
       (Rs(Fr(1008) / Fr(12, 10)), "divided by 1.2")],
      ["CP = 1,008/1.12 = 900", "SP = 900 × 1.2 = 1,080"],
      "Find CP first, then apply new margin", "Both margins are on cost.")

    q("cpsp", "L2", "f", "The selling price of 12 articles equals the cost price of 15 articles. The profit percentage is:",
      P(25),
      [(P(20), "gain divided by 15"), (P(3), "difference in counts read as %"), (P(80), "12/15 reported")],
      ["12 SP = 15 CP ⇒ SP/CP = 15/12 = 1.25", "Profit = 25%"],
      "Profit % = (CP-count − SP-count)/SP-count × 100", "Divide by the smaller (SP) count.")

    q("cpsp", "L2", "f", "A trader claims to sell at a profit of 20%, but uses a 900 g weight in place of 1 kg. His actual profit percentage is:",
      P((Fr(12, 10) / Fr(9, 10) - 1) * 100),
      [(P(30), "20% + 10% added"), (P(20), "false weight ignored"), (P(8), "1.2 × 0.9 − 1")],
      ["Customer pays for 1,000 g at 1.2 × cost, receives 900 g", "Gain factor = 1.2/0.9 = 4/3", "Profit = 33 1/3%"],
      "Profit factor = (1 + p) × true/false weight", "Divide by 0.9, do not add 10%.")

    C = Fr(1480 + 3 * 1160, 4)
    assert C == 1240
    q("cpsp", "L3", "o", "The profit on selling an article for ₹1,480 is three times the loss on selling it for ₹1,160. The cost price is:",
      Rs(C),
      [(Rs(Fr(1480 + 1160, 2)), "profit taken equal to loss (midpoint)"), (Rs(Fr(3 * 1480 + 1160, 4)), "factor 3 put on the profit side"),
       (Rs(1160 + Fr(1480 - 1160, 3)), "gap split in 1 : 2 instead of 1 : 3")],
      ["1,480 − C = 3(C − 1,160)", "4C = 1,480 + 3,480 = 4,960", "C = 1,240"],
      "Profit = SP − CP; Loss = CP − SP", "The cost lies 1/4 of the way from 1,160 to 1,480.")

    m = (100 - 88) / Fr(100) * 100
    q("cpsp", "L3", "o", "A trader's margin is 20% of the selling price. If his cost rises by 10% and the selling price is unchanged, his new margin as a percentage of the selling price is:",
      P(m),
      [(P(10), "margin cut point-for-point"), (P(D(Fr(12, 88) * 100)), "new margin measured on cost"), (P(18), "10% taken of the margin")],
      ["SP 100, CP 80", "New CP = 88", "Margin = 12/100 = 12%"],
      "Margin on SP = (SP − CP)/SP", "A 10% cost rise is 8 points of SP here.")

    cp, sp = Fr(12, 5), Fr(11, 4)
    q("cpsp", "L3", "o", "A vendor buys oranges at 5 for ₹12 and sells them at 4 for ₹11. His profit percentage is:",
      P((sp - cp) / cp * 100),
      [(P((sp - cp) / sp * 100), "profit on SP"), (P(25), "counts 5 and 4 compared only"), (P(Fr(1, 12) * 100), "(12 − 11)/12 used")],
      ["CP each = 12/5 = 2.40", "SP each = 11/4 = 2.75", "Profit = 0.35/2.40 = 14 7/12%"],
      "Compare per-unit CP and SP", "Convert both rates to one orange.")

    q("cpsp", "L3", "o", "By selling 33 m of cloth, a shopkeeper gains the selling price of 11 m. His gain percentage is:",
      P(50),
      [(P(Fr(100, 3)), "gain measured on SP"), (P(25), "11/(33 + 11) used"), (P(Fr(200, 3)), "22/33 used")],
      ["33 SP − 33 CP = 11 SP ⇒ 22 SP = 33 CP", "SP/CP = 1.5 ⇒ gain 50%"],
      "Gain = SP of 11 m ⇒ cost of 33 m = SP of 22 m", "Gain % is on cost.")

    C = Fr(30) / (Fr(125, 100) * Fr(9, 10) - Fr(11, 10))
    assert C == 1200
    q("cpsp", "L3", "o", "A man sells a cycle at 10% profit. Had he bought it 10% cheaper and sold it for ₹30 more, he would have gained 25%. The cost price is:",
      Rs(C),
      [(Rs(Fr(30) / (Fr(125, 100) - Fr(11, 10))), "cheaper purchase ignored"), (Rs(Fr(30) / (Fr(115, 100) - Fr(11, 10))), "1.25 × 0.9 taken as 1.15"),
       (Rs(Fr(30) / Fr(2, 100)), "₹30 treated as 2% of cost")],
      ["Actual SP = 1.1C", "New CP = 0.9C; new SP = 1.25 × 0.9C = 1.125C", "1.125C − 1.1C = 30 ⇒ C = 1,200"],
      "Equate the two SP expressions", "The 25% gain is on the reduced cost.")

    c = Fr(2250) / (Fr(12, 10) * Fr(125, 100))
    assert c == 1500
    q("cpsp", "L3", "o", "A manufacturer sells to a dealer at 20% profit and the dealer sells to a customer at 25% profit. The customer pays ₹2,250. The manufacturer's cost is:",
      Rs(c),
      [(Rs(D(Fr(2250) / Fr(145, 100))), "margins added (45%)"), (Rs(D(Fr(2250) * Fr(75, 100))), "25% deducted from customer price"),
       (Rs(D(Fr(2250) * Fr(55, 100))), "45% deducted from customer price")],
      ["2,250 = C × 1.2 × 1.25 = 1.5C", "C = 1,500"],
      "Chain the markups", "Divide by the product of factors.")

    rise = Fr(45, 100) * 20 + Fr(35, 100) * 10
    assert rise == Fr(25, 2)
    q("cpsp", "L3", "o", "A product's cost is 45% materials, 35% labour and 20% overheads. Material prices rise 20% and wages 10%; overheads are unchanged. To keep the same profit percentage, the selling price must rise by:",
      P(rise),
      [(P(15), "average of 20% and 10%"), (P(30), "rises added"), (P(D(rise * Fr(125, 100))), "cost rise grossed up by a 25% margin")],
      ["Cost rise = 0.45 × 20 + 0.35 × 10 = 9 + 3.5 = 12.5%", "Same profit % ⇒ SP rises by the same 12.5%"],
      "Weighted rise = Σ share × rise", "Weight each rise by its cost share.")

    c = Fr(8160) / (Fr(85, 100) * Fr(12, 10))
    assert c == 8000
    q("cpsp", "L3", "o", "A sells a bicycle to B at a 15% loss; B sells it to C at a 20% profit. C pays ₹8,160. A's cost price was:",
      Rs(c),
      [(Rs(D(Fr(8160) / Fr(105, 100))), "net +5% (rates added)"), (Rs(Fr(8160) / Fr(12, 10)), "B's cost reported"),
       (Rs(D(Fr(8160) * Fr(102, 100))), "net factor multiplied")],
      ["Net factor = 0.85 × 1.2 = 1.02", "A's cost = 8,160/1.02 = 8,000"],
      "CP = Final price ÷ Π factors", "Loss then gain: multiply 0.85 × 1.2.")

    q("cpsp", "L2", "o", "The cost price of 25 pens equals the selling price of x pens. If the profit is 25%, x equals:",
      "20",
      [("31.25", "25 multiplied by 1.25"), ("30", "5 pens added for 25%"), ("18.75", "25 reduced by 25%")],
      ["25 CP = x × 1.25 CP", "x = 25/1.25 = 20"],
      "x = n ÷ (1 + p)", "Divide, since each SP is larger than CP.")

    # ===================== Discount and marked price =====================
    q("disc", "L1", "f", "A jacket is marked ₹2,400 and sold at a 15% discount. The selling price is:",
      Rs(2400 * Fr(85, 100)),
      [(Rs(360), "discount amount reported"), (Rs(2400 * Fr(115, 100)), "15% added"), (Rs(D(Fr(2400) / Fr(115, 100))), "MP divided by 1.15")],
      ["Discount = 15% of 2,400 = 360", "SP = 2,040"],
      "SP = MP × (1 − d)", "Discount is on marked price.")

    q("disc", "L1", "f", "A shopkeeper marks goods 25% above cost and allows a 12% discount. His profit percentage is:",
      P((Fr(125, 100) * Fr(88, 100) - 1) * 100),
      [(P(13), "percentages subtracted"), (P(12), "discount read as profit"), (P(D(Fr(25 - 12, 125) * 100)), "gap measured on MP")],
      ["CP 100 ⇒ MP 125", "SP = 125 × 0.88 = 110", "Profit = 10%"],
      "SP = CP × (1 + m)(1 − d)", "Discount acts on the marked price.")

    mp = Fr(3570) / Fr(85, 100)
    assert mp == 4200
    q("disc", "L2", "f", "After a 15% discount, a phone sells for ₹3,570. Its marked price is:",
      Rs(mp),
      [(Rs(D(Fr(3570) * Fr(115, 100))), "15% of SP added"), (Rs(D(Fr(3570) * Fr(85, 100))), "15% deducted again"),
       (Rs(D(Fr(3570) * Fr(15, 100))), "discount on SP reported")],
      ["MP × 0.85 = 3,570", "MP = 4,200"],
      "MP = SP ÷ (1 − d)", "The discount was 15% of MP, not of SP.")

    m = (Fr(12, 10) / Fr(8, 10) - 1) * 100
    q("disc", "L2", "f", "A trader gives a 20% discount and still makes a 20% profit. By what percentage is the marked price above cost?",
      P(m),
      [(P(40), "percentages added"), (P(44), "1.2 × 1.2 − 1"), (P(25), "20/80 only")],
      ["MP × 0.8 = 1.2 CP", "MP = 1.5 CP ⇒ 50% above cost"],
      "MP/CP = (1 + p)/(1 − d)", "Divide by 0.8.")
    assert m == 50

    q("disc", "L2", "f", "A 'buy 3, get 1 free' offer is equivalent to a discount of:",
      P(25),
      [(P(Fr(100, 3)), "free item divided by items paid for"), (P(20), "buy 4, get 1 free"), (P(75), "share paid for")],
      ["Customer pays for 3, gets 4", "Discount = 1/4 = 25%"],
      "Discount = free ÷ total received", "Base is all items received.")

    f = Fr(14, 10) * Fr(9, 10) * Fr(95, 100)
    q("disc", "L3", "o", "A trader marks goods 40% above cost and allows successive discounts of 10% and 5%. His profit percentage is:",
      P(D((f - 1) * 100)),
      [(P(25), "discounts subtracted from markup"), (P(26), "second discount missed"), (P(19), "discounts added into 15%")],
      ["1.4 × 0.9 = 1.26", "1.26 × 0.95 = 1.197 ⇒ 19.7% profit"],
      "SP/CP = (1 + m) Π(1 − d)", "Successive discounts compound.")

    ratio_ = Fr(11, 10) / Fr(88, 100)
    assert ratio_ * Fr(8, 10) == 1
    q("disc", "L3", "o", "By allowing a 12% discount a shopkeeper earns 10% profit. If he allows a 20% discount instead, he will:",
      "Neither gain nor lose",
      [("Gain 2%", "discount change netted against profit"), ("Lose 2%", "sign flipped"), ("Lose 8%", "extra discount taken as loss")],
      ["MP/CP = 1.10/0.88 = 1.25", "At 20% off: SP = 1.25 × 0.8 = 1.00 CP", "No profit, no loss"],
      "MP/CP from the first condition", "Recompute the MP/CP ratio.")

    mp = Fr(4200) / Fr(84, 100)
    cp = Fr(4200) / Fr(105, 100)
    new = (mp * Fr(9, 10) - cp) / cp * 100
    assert new == Fr(25, 2)
    q("disc", "L3", "o", "An article sold at a 16% discount fetches ₹4,200 and gives a 5% profit. If it were sold at a 10% discount, the profit would be:",
      P(new),
      [(P(11), "6-point discount cut added to profit"), (P(D(Fr(300, 4200) * 100 + 5)), "extra ₹300 measured on old SP then added"),
       (P(10), "discount read as profit")],
      ["MP = 4,200/0.84 = 5,000; CP = 4,200/1.05 = 4,000", "SP at 10% off = 4,500", "Profit = 500/4,000 = 12.5%"],
      "Recover MP and CP separately", "Profit changes by more than the discount change.")

    cp = 1600
    mp = cp * Fr(125, 100) / Fr(8, 10)
    assert mp == 2500
    q("disc", "L3", "o", "An article costs ₹1,600. At what price must it be marked so that after a 20% discount the seller still gains 25%?",
      Rs(mp),
      [(Rs(cp * Fr(145, 100)), "markup = 25 + 20"), (Rs(cp * Fr(125, 100) * Fr(12, 10)), "20% added instead of dividing by 0.8"),
       (Rs(cp * Fr(125, 100)), "discount ignored")],
      ["Required SP = 1,600 × 1.25 = 2,000", "MP = 2,000/0.8 = 2,500"],
      "MP = CP(1 + p)/(1 − d)", "Grossing up for 20% off is 25%, not 20%.")

    a, b = 12000 * Fr(8, 10) * Fr(9, 10), 12000 * Fr(75, 100)
    q("disc", "L3", "o", "On a marked price of ₹12,000, scheme A offers successive discounts of 20% and 10%; scheme B offers a flat 25% discount. Which is better for the buyer, and by how much?",
      f"Scheme A, by {Rs(b - a)}",
      [(f"Scheme B, by {Rs(b - a)}", "comparison reversed"), (f"Scheme A, by {Rs(12000 * Fr(5, 100))}", "A treated as flat 30%"),
       ("Both cost the same", "28% and 25% confused")],
      ["A: 12,000 × 0.8 × 0.9 = 8,640", "B: 12,000 × 0.75 = 9,000", "A cheaper by 360"],
      "Equivalent of 20% and 10% = 28%", "Successive discounts are less than their sum but still beat 25% here.")

    m = Fr(12, 10) / (Fr(5, 6) * Fr(9, 10)) - 1
    assert m == Fr(3, 5)
    q("disc", "L3", "o", "A shopkeeper gives one article free with every five bought and also allows a 10% discount on the marked price. He still gains 20%. The marked price is what percentage above cost?",
      P(m * 100),
      [(P((Fr(12, 10) / Fr(9, 10) - 1) * 100), "free article ignored"), (P((Fr(12, 10) / (Fr(8, 10) * Fr(9, 10)) - 1) * 100), "free article treated as a 20% discount"),
       (P(D((Fr(12, 10) / (1 - Fr(1, 6) - Fr(1, 10)) - 1) * 100)), "the two discounts added")],
      ["For 6 articles he receives 5 × 0.9 MP = 4.5 MP", "Per article: 0.75 MP = 1.2 CP", "MP = 1.6 CP ⇒ 60% above cost"],
      "Effective discount = 1 − (5/6)(0.9) = 25%", "1 free with 5 is a 1/6 discount, not 1/5.")

    d = (5 - Fr(42, 10)) / 5 * 100
    assert d == 16
    q("disc", "L3", "o", "The ratio of marked price to cost price of an item is 5 : 4. What is the maximum discount percentage the seller can allow and still earn a profit of at least 5%?",
      P(d),
      [(P(20), "break-even discount"), (P(15), "5% profit taken on MP"), (P(25), "markup percentage reported")],
      ["CP 4, MP 5", "Minimum SP = 4 × 1.05 = 4.2", "Max discount = 0.8/5 = 16%"],
      "d = 1 − CP(1 + p)/MP", "Profit is on cost; discount is on MP.")

    f = Fr(12, 10) * Fr(13, 10) * Fr(7, 10)
    q("disc", "L3", "o", "A shop used to sell at the marked price and earn 20% profit. It now raises the marked price by 30% and then offers a 30% discount. Its new profit percentage is:",
      P(D((f - 1) * 100)),
      [(P(11), "20 − 9 subtracted"), (P(20), "believes raise and discount cancel"), (P(9), "buyer's 9% saving read as profit")],
      ["New SP = MP × 1.3 × 0.7 = 0.91 MP", "MP = 1.2 CP ⇒ SP = 1.092 CP", "Profit = 9.2%"],
      "SP/CP = 1.2 × 0.91", "Equal raise and discount leave a 9% net cut in price.")

    bill = 3000 * Fr(75, 100) - 150
    q("disc", "L3", "o", "A store gives 25% off the marked price and a further ₹150 off any bill above ₹2,000 after that discount. A customer buys goods marked ₹3,000. The effective discount is:",
      P((3000 - bill) / 3000 * 100),
      [(P(25), "₹150 off not applied"), (P(D(Fr(150, 2250) * 100 + 25)), "₹150 measured on discounted bill then added"),
       (P(D((3000 - (3000 - 150) * Fr(75, 100)) / 3000 * 100)), "₹150 deducted before the 25% discount")],
      ["After 25%: 2,250", "After ₹150: 2,100", "Discount = 900/3,000 = 30%"],
      "Effective discount = (MP − final bill)/MP", "Measure the total saving against MP.")

    # ===================== Combined transactions and overall gain =====================
    q("comb", "L1", "f", "A trader buys two items for ₹500 each. He sells one at 20% profit and the other at 10% loss. His overall result is:",
      "5% profit",
      [("10% profit", "rates netted without averaging"), ("5% loss", "sign reversed"), ("15% profit", "loss treated as a smaller gain")],
      ["SP = 600 + 450 = 1,050 on cost 1,000", "Profit = 5%"],
      "Equal costs ⇒ overall % = average of the two %", "Equal CPs give a simple average.")

    cp = Fr(20 * 40 + 30 * 50, 50)
    q("comb", "L2", "f", "A grocer mixes 20 kg of rice at ₹40/kg with 30 kg at ₹50/kg and sells the mixture at ₹54/kg. His profit percentage is:",
      P(D((54 - cp) / cp * 100)),
      [(P(20), "simple average cost ₹45 used"), (P(8), "compared with ₹50 grade only"), (P(D((54 - cp) / 54 * 100)), "profit measured on SP")],
      ["Total cost = 800 + 1,500 = 2,300 for 50 kg ⇒ ₹46/kg", "Profit = 8/46 = 17.39%"],
      "Weighted average cost", "Weights are 20 and 30 kg.")

    q("comb", "L2", "f", "A vendor buys 120 eggs at ₹6 each. 20 break, and he sells the rest at ₹8 each. His profit percentage is:",
      P(Fr(800 - 720, 720) * 100),
      [(P(Fr(2, 6) * 100), "breakage ignored"), (P(10), "profit measured on SP"), (P(25), "₹2 margin per ₹8 SP")],
      ["Cost = 720; revenue = 100 × 8 = 800", "Profit = 80/720 = 11 1/9%"],
      "Profit % = (Revenue − Total cost)/Total cost", "Broken eggs still cost money.")

    cps, rs = [300, 400, 500], [10, 20, 30]
    pr = sum(c * r for c, r in zip(cps, rs)) / Fr(100)
    q("comb", "L2", "f", "Three items bought for ₹300, ₹400 and ₹500 are sold at profits of 10%, 20% and 30% respectively. The overall profit percentage is:",
      P(pr / 1200 * 100),
      [(P(20), "simple average of rates"), (P(Fr(90 + 80 + 50, 12)), "rates matched to wrong items"),
       (P(D(pr / (1200 + pr) * 100)), "profit measured on total SP")],
      ["Profits: 30 + 80 + 150 = 260", "260/1,200 = 21 2/3%"],
      "Overall % = Σ profit ÷ Σ cost", "Weight by cost.")

    cp = 50 * 400
    sp = 30 * 500 + 20 * 360
    q("comb", "L2", "f", "A shop buys 50 shirts at ₹400 each, sells 30 at ₹500 each and the rest at ₹360 each. The overall profit percentage is:",
      P(Fr(sp - cp, cp) * 100),
      [(P(Fr(25 - 10, 2)), "average of +25% and −10%"), (P(25), "second lot ignored"), (P(D(Fr(sp - cp, sp) * 100)), "profit measured on SP")],
      ["Cost = 20,000", "Revenue = 15,000 + 7,200 = 22,200", "Profit = 11%"],
      "Σ SP vs Σ CP", "Weights are 30 and 20 shirts.")

    x = Fr(42000 * 3, 5)
    assert x * Fr(2, 10) == (42000 - x) * Fr(3, 10)
    q("comb", "L3", "o", "Two horses cost ₹42,000 together. One is sold at a 20% loss and the other at a 30% gain, and overall there is neither gain nor loss. The cost of the horse sold at a loss is:",
      Rs(x),
      [(Rs(42000 - x), "cost of the other horse"), (Rs(21000), "equal costs assumed"), (Rs(Fr(42000 * 2, 3)), "costs split 2 : 1")],
      ["0.2x = 0.3(42,000 − x)", "0.5x = 12,600 ⇒ x = 25,200"],
      "Loss amount = gain amount", "The loss-making horse must cost more.")

    x = Fr(80 * 18 - 30 * 12, 50)
    q("comb", "L3", "o", "A trader sells 30 kg of an 80 kg stock at 12% profit. At what profit percentage must he sell the rest to earn 18% overall?",
      P(x),
      [(P(24), "unweighted: 2 × 18 − 12"), (P(Fr(80 * 18 - 30 * 12, 80)), "divided by the whole 80 kg"), (P(Fr(80 * 18, 50)), "profit on first 30 kg ignored")],
      ["30 × 12 + 50x = 80 × 18", "50x = 1,080 ⇒ x = 21.6%"],
      "Weighted average of rates", "Weights are 30 and 50 kg.")
    assert x == Fr(108, 5)

    cost = 400 * 25 + 1000
    rev = 20 * Fr(25, 2) + 380 * 32
    q("comb", "L3", "o", "A dealer buys 400 units at ₹25 each and pays ₹1,000 transport. 5% of the units are damaged and sold at half the cost price; the rest are sold at ₹32 each. His profit percentage is:",
      P(D((rev - cost) / cost * 100)),
      [(P(D((rev - 10000) / 10000 * 100)), "transport cost ignored"), (P(D((400 * 32 - cost) / Fr(cost) * 100)), "damaged units sold at full price"),
       (P(D((380 * 32 - cost) / Fr(cost) * 100)), "damaged units written off entirely")],
      ["Total cost = 10,000 + 1,000 = 11,000", "Revenue = 20 × 12.5 + 380 × 32 = 250 + 12,160 = 12,410", "Profit = 1,410/11,000 = 12.82%"],
      "Include every cost and every sale", "Transport belongs to cost.")

    avgc = Fr(30 * 180 + 20 * 240, 50)
    q("comb", "L3", "o", "A merchant blends 30 kg of tea at ₹180/kg with 20 kg at ₹240/kg. To earn 25% on the blend, his selling price per kg should be:",
      Rs(avgc * Fr(125, 100)),
      [(Rs(D(Fr(180 + 240, 2) * Fr(125, 100))), "unweighted average cost"), (Rs(avgc / Fr(75, 100)), "25% taken as margin on SP"),
       (Rs(180 * Fr(125, 100)), "cheaper tea's cost used")],
      ["Average cost = (5,400 + 4,800)/50 = ₹204", "SP = 204 × 1.25 = ₹255"],
      "Weighted average cost × (1 + p)", "Weights are the quantities.")

    x = (12 - Fr(20, 2) + Fr(10, 3)) * 6
    assert x == 32
    q("comb", "L3", "o", "A shopkeeper sells half his stock at 20% profit and one-third at 10% loss. At what profit percentage must he sell the rest to make 12% overall?",
      P(x),
      [(P(12 * 3 - 20 + 10), "unweighted average of three rates"), (P(D(12 - 10 + Fr(10, 3))), "forgot to divide by the one-sixth share"),
       (P((12 - Fr(20, 3) + 5) * 6), "weights 1/2 and 1/3 swapped")],
      ["Rest = 1/6 of stock", "(1/2)(20) − (1/3)(10) + (1/6)x = 12", "10 − 3.33 + x/6 = 12 ⇒ x = 32%"],
      "Σ share × rate = overall rate", "The last share is only 1/6.")

    pr = 2 * 10 + 3 * 20 + 5 * 16
    q("comb", "L3", "o", "A retailer buys three kinds of goods in value ratio 2 : 3 : 5 and earns 10%, 20% and 16% on them respectively. His overall profit percentage is:",
      P(Fr(pr, 10)),
      [(P(D(Fr(10 + 20 + 16, 3))), "simple average"), (P(Fr(5 * 10 + 3 * 20 + 2 * 16, 10)), "weights reversed"),
       (P(D(Fr(pr, 10) / Fr(116, 100))), "profit measured on SP")],
      ["2 × 10 + 3 × 20 + 5 × 16 = 160", "160/10 = 16%"],
      "Value-weighted average", "Weights are cost values.")

    q("comb", "L3", "o", "A trader buys 60 kg of grain at ₹30/kg. 10% of the weight is lost in handling, and he sells the rest at ₹36/kg. His profit percentage is:",
      P(Fr(54 * 36 - 1800, 1800) * 100),
      [(P(20), "handling loss ignored"), (P(10), "20 − 10 subtracted"), (P(D(Fr(54 * 36 - 1800, 54 * 36) * 100)), "profit measured on SP")],
      ["Cost = 1,800", "Revenue = 54 × 36 = 1,944", "Profit = 144/1,800 = 8%"],
      "Profit on total cost", "Only 54 kg is sold.")

    x = Fr(6200 - Fr(9, 10) * 6000, Fr(25, 100))
    assert x == 3200
    q("comb", "L3", "o", "Two articles cost ₹6,000 together. The first is sold at 15% profit and the second at 10% loss; total sales are ₹6,200. The cost of the first article is:",
      Rs(x),
      [(Rs(6000 - x), "cost of the second article"), (Rs(3000), "equal costs assumed"), (Rs(Fr(600, Fr(25, 100))), "₹200 overall gain ignored")],
      ["1.15x + 0.9(6,000 − x) = 6,200", "0.25x = 800 ⇒ x = 3,200"],
      "Σ SP equation", "Set up SP, not profit, equations.")

    q("comb", "L2", "o", "A dealer sells 40% of his stock at 25% profit and the remainder at 5% loss. His overall result is:",
      "7% profit",
      [("10% profit", "simple average of +25% and −5%"), ("13% profit", "weights 40 : 60 swapped"), ("7% loss", "sign reversed")],
      ["0.4 × 25 − 0.6 × 5 = 10 − 3 = 7", "Overall profit 7%"],
      "Overall % = Σ share × rate (shares by cost)", "The loss applies to the larger share.")
    assert Fr(4, 10) * 25 - Fr(6, 10) * 5 == 7

    # ===================== Equal profit and loss conditions =====================
    q("eqpl", "L1", "f", "The profit on selling an article for ₹850 equals the loss on selling it for ₹650. Its cost price is:",
      Rs(750),
      [(Rs(800), "rounded towards the higher SP"), (Rs(700), "rounded towards the lower SP"), (Rs(1500), "SPs added, not averaged")],
      ["850 − C = C − 650", "C = 750"],
      "CP = average of the two SPs", "Equal profit and loss put CP midway.")

    q("eqpl", "L2", "f", "Two items are sold for ₹1,200 each, one at 20% profit and the other at 20% loss. The overall result is:",
      "4% loss",
      [("No profit, no loss", "equal rates assumed to cancel"), ("4% profit", "sign reversed"), ("2% loss", "x²/100 halved")],
      ["CPs: 1,000 and 1,500; total 2,500", "SP total 2,400 ⇒ loss 100 = 4%"],
      "Equal SP, ±x% ⇒ loss x²/100 %", "Equal SPs mean unequal costs.")

    C = Fr(1340 + 1780, 2)
    q("eqpl", "L1", "f", "The loss on selling a table for ₹1,340 equals the profit on selling it for ₹1,780. At what price should it be sold to gain 25%?",
      Rs(C * Fr(125, 100)),
      [(Rs(C), "cost price reported"), (Rs(1780 * Fr(125, 100)), "25% applied to the higher SP"), (Rs(1340 * Fr(125, 100)), "25% applied to the lower SP")],
      ["CP = (1,340 + 1,780)/2 = 1,560", "SP = 1,560 × 1.25 = 1,950"],
      "CP = average of SPs", "Find CP first.")

    C = Fr(1440 + 2 * 960, 3)
    assert C == 1120
    q("eqpl", "L2", "f", "The profit on selling an item for ₹1,440 is twice the loss on selling it for ₹960. The cost price is:",
      Rs(C),
      [(Rs(1200), "profit taken equal to loss"), (Rs(Fr(2 * 1440 + 960, 3)), "factor 2 put on the profit side"), (Rs(Fr((1440 + 960) * 2, 3)), "SPs added then scaled")],
      ["1,440 − C = 2(C − 960)", "3C = 3,360 ⇒ C = 1,120"],
      "Profit = k × Loss", "CP lies closer to the loss-side SP.")

    C = Fr(510) / Fr(85, 100)
    q("eqpl", "L2", "f", "Selling a lamp for ₹510 causes a 15% loss. To gain 15%, it should be sold for:",
      Rs(C * Fr(115, 100)),
      [(Rs(D(Fr(510) * Fr(115, 100))), "15% added to the loss-making SP"), (Rs(510 * Fr(130, 100)), "30% added to ₹510"), (Rs(C), "cost price reported")],
      ["CP = 510/0.85 = 600", "SP = 600 × 1.15 = 690"],
      "CP = SP ÷ (1 − loss%)", "Recover CP before applying the gain.")

    c1, c2 = Fr(4800) / Fr(125, 100), Fr(4800) / Fr(75, 100)
    loss = c1 + c2 - 9600
    assert loss == 640
    q("eqpl", "L3", "o", "Two lots of goods are sold for ₹4,800 each, one at 25% profit and the other at 25% loss. The overall loss in rupees is:",
      Rs(loss),
      [(Rs(D(Fr(9600) * Fr(625, 10000))), "6.25% applied to total SP"), (Rs(1200), "25% of one SP"), ("₹0", "equal rates assumed to cancel")],
      ["CPs: 4,800/1.25 = 3,840 and 4,800/0.75 = 6,400", "Total CP 10,240 vs SP 9,600", "Loss = ₹640"],
      "Loss% = x²/100 on total CP", "The 6.25% is of cost, not of sales.")

    C = Fr(1000) / Fr(20, 100)
    q("eqpl", "L3", "o", "Two articles have the same cost. One is sold at 12% profit and the other at 8% loss; the difference in their selling prices is ₹1,000. The cost of each is:",
      Rs(C),
      [(Rs(Fr(1000) / Fr(4, 100)), "difference taken as (12 − 8)%"), (Rs(D(Fr(1000) / Fr(12, 100))), "difference taken as 12%"),
       (Rs(2 * C), "combined cost reported")],
      ["SP difference = (1.12 − 0.92)C = 0.20C", "0.2C = 1,000 ⇒ C = 5,000"],
      "SP gap = (p + l)% of CP", "Profit and loss percentages add across the gap.")

    tot_cp = Fr(99) / Fr(11, 10) + Fr(99) / Fr(9, 10)
    loss = tot_cp - 198
    assert loss == 2
    q("eqpl", "L3", "o", "A builder sells two flats for ₹99 lakh each, gaining 10% on one and losing 10% on the other. His overall result is:",
      "Loss of ₹2 lakh",
      [("No gain, no loss", "equal rates assumed to cancel"), ("Loss of ₹1.98 lakh", "1% applied to total SP"), ("Gain of ₹2 lakh", "sign reversed")],
      ["CPs: 99/1.1 = 90 and 99/0.9 = 110 (₹ lakh)", "Total CP 200 vs SP 198", "Loss ₹2 lakh"],
      "Equal SP ⇒ loss x²/100 % of CP", "1% of cost (200), not of sales.")

    C = Fr(450) / Fr(30, 100)
    q("eqpl", "L3", "o", "Selling a machine at a certain price yields 20% profit; selling it for ₹450 less yields a 10% loss. At what price will the seller neither gain nor lose?",
      Rs(C),
      [(Rs(Fr(450) / Fr(20, 100)), "₹450 taken as 20% of CP"), (Rs(C * Fr(12, 10)), "price at 20% profit"), (Rs(C * Fr(9, 10)), "price at 10% loss")],
      ["(1.2 − 0.9)C = 450", "C = 1,500 = no-loss price"],
      "SP gap = (p + l)% of CP", "Break-even price = CP.")

    p = 20
    sp = Fr(120)
    cpA, cpB = sp / Fr(12, 10), sp / Fr(8, 10)
    assert (cpA + cpB - 2 * sp) / (cpA + cpB) * 100 == 4
    assert (cpA + cpB - 2 * sp) / (2 * sp) * 100 != 4
    q("eqpl", "L3", "o",
      "A trader sells two items at a gain of p% on one and a loss of p% on the other (p > 0). Consider:\n\nI. If the two items cost the same, he neither gains nor loses overall.\nII. If the two items sell for the same price, he always makes an overall loss.\nIII. With equal selling prices, the overall loss equals p²/100 per cent of the total selling price.\n\nWhich are correct?",
      "I and II only",
      [("I, II and III", "III: loss is p²/100 % of total cost, not of total SP"), ("II and III only", "I wrongly rejected"), ("I only", "II wrongly rejected")],
      ["I: gains and losses are equal amounts on equal costs — true", "II: equal SPs force a larger cost on the loss item — true",
       "III: p = 20, SP 120 each ⇒ CPs 100, 150; loss 10 = 4% of cost 250 but 4.17% of SP 240 — false"],
      "Equal SP ⇒ loss% = p²/100 on cost", "Check the base of the p²/100 rule.", kind="statement")

    cp1 = Fr(2000) / Fr(12, 10)
    cp2 = 4000 - cp1
    x = (cp2 - 2000) / cp2 * 100
    q("eqpl", "L3", "o", "Two watches are sold for ₹2,000 each, one at 20% profit. If the trader neither gains nor loses overall, the loss percentage on the other watch is:",
      P(x),
      [(P(20), "equal rates assumed"), (P((cp2 - 2000) / 2000 * 100), "loss measured on SP"), (P(10), "half of 20% taken")],
      ["CP₁ = 2,000/1.2 = 1,666 2/3", "Total CP = 4,000 ⇒ CP₂ = 2,333 1/3", "Loss = 333 1/3 / 2,333 1/3 = 14 2/7%"],
      "Loss amount = profit amount", "The loss item costs more, so its loss % is smaller.")
    assert x == Fr(100, 7)

    C = Fr(180) / Fr(25, 100)
    q("eqpl", "L3", "o", "An article is sold at a 20% loss. Had it been sold for ₹180 more, there would have been a 5% gain. To gain 15%, it must be sold for:",
      Rs(C * Fr(115, 100)),
      [(Rs(C), "cost price reported"), (Rs(D(Fr(180) / Fr(20, 100) * Fr(115, 100))), "₹180 taken as 20% of cost"), (Rs(C * Fr(105, 100)), "price for 5% gain")],
      ["(1.05 − 0.80)C = 180 ⇒ C = 720", "SP = 720 × 1.15 = 828"],
      "SP gap = (g + l)% of CP", "Loss and gain rates add across the gap.")

    cp1, cp2 = 600 - 120, 600 + 120
    q("eqpl", "L3", "o", "Two items are each sold for ₹600. On one the profit equals 20% of its selling price; on the other the loss equals 20% of its selling price. The overall result is:",
      "Neither profit nor loss",
      [("Loss of 4%", "p²/100 rule applied to a margin-on-SP case"), ("Gain of 4%", "sign reversed"), ("Loss of ₹48", "4% of 1,200 applied")],
      ["Profit item: CP = 600 − 120 = 480", "Loss item: CP = 600 + 120 = 720", "Total CP 1,200 = total SP 1,200"],
      "Margin on SP: CP = SP ∓ 20% of SP", "The p²/100 rule needs rates on cost.")
    assert cp1 + cp2 == 1200

    C = Fr(540) / Fr(18, 100)
    q("eqpl", "L3", "o", "A dealer sells an item at a 12% loss. Had he sold it for ₹540 more, he would have gained 6%. For a 12% gain, the price should be:",
      Rs(C * Fr(112, 100)),
      [(Rs(C), "cost price reported"), (Rs(C * Fr(106, 100)), "price for 6% gain"), (Rs(C + 540), "₹540 added to cost")],
      ["(1.06 − 0.88)C = 540 ⇒ C = 3,000", "SP = 3,000 × 1.12 = 3,360"],
      "SP gap = (g + l)% of CP", "18% of cost equals ₹540.")

    C = Fr(1920 + Fr(16, 10) * 1400, Fr(26, 10))
    assert C == 1600
    q("eqpl", "L3", "o", "The profit when an item is sold for ₹1,920 is 60% more than the loss when it is sold for ₹1,400. The cost price is:",
      Rs(C),
      [(Rs(1660), "profit taken equal to loss"), (Rs(Fr(Fr(16, 10) * 1920 + 1400, Fr(26, 10))), "factor 1.6 put on the loss side"),
       (Rs(D(Fr(1920 + Fr(4, 10) * 1400, Fr(14, 10)))), "'60% more' read as 40% of")],
      ["1,920 − C = 1.6(C − 1,400)", "2.6C = 1,920 + 2,240 = 4,160 ⇒ C = 1,600"],
      "Profit = 1.6 × Loss", "60% more means × 1.6.")

    # ===================== Simple and compound interest =====================
    q("sici", "L1", "f", "The simple interest on ₹12,000 at 8% per annum for 3 years is:",
      Rs(12000 * 8 * 3 / 100),
      [(Rs(D(12000 * (Fr(108, 100) ** 3 - 1))), "compound interest computed"), (Rs(960), "one year's interest"), (Rs(14880), "amount reported")],
      ["SI = 12,000 × 8 × 3/100 = 2,880"],
      "SI = PRT/100", "Interest, not amount.")

    q("sici", "L1", "f", "The compound interest on ₹10,000 at 10% per annum for 2 years, compounded annually, is:",
      Rs(2100),
      [(Rs(2000), "simple interest"), (Rs(12100), "amount reported"), (Rs(1000), "one year only")],
      ["A = 10,000 × 1.1² = 12,100", "CI = 2,100"],
      "CI = P[(1 + r)^n − 1]", "Second year earns interest on interest.")

    q("sici", "L2", "f", "A sum doubles in 8 years at simple interest. The rate of interest per annum is:",
      P(Fr(100, 8)),
      [(P(8), "years read as rate"), (P(25), "100/4 used"), (P(Fr(905, 100)), "compound-interest rate for doubling (2^(1/8) − 1)")],
      ["SI = P in 8 years", "R = 100/8 = 12.5%"],
      "R = 100 × (k − 1)/T", "Doubling means interest equals principal.")

    Pp = Fr(40) / Fr(25, 10000)
    assert Pp == 16000
    q("sici", "L2", "f", "The difference between compound and simple interest on a sum for 2 years at 5% per annum is ₹40. The sum is:",
      Rs(Pp),
      [(Rs(800), "40 divided by 5%"), (Rs(8000), "40 divided by 0.5%"), (Rs(160000), "40 divided by 0.025%")],
      ["Difference = P(r/100)² = P × 0.0025", "P = 40/0.0025 = 16,000"],
      "CI − SI (2 yrs) = P(r/100)²", "Square the rate.")

    q("sici", "L2", "f", "The amount on ₹5,000 at 20% per annum for 2 years, compounded half-yearly, is:",
      RsD(5000 * Fr(11, 10) ** 4),
      [(Rs(7200), "compounded annually"), (Rs(7000), "simple interest"), (Rs(6050), "only two half-years")],
      ["Half-yearly rate 10%, periods 4", "5,000 × 1.1⁴ = 7,320.50"],
      "A = P(1 + r/2)^(2n)", "Halve the rate and double the periods.")

    r = Fr(9261, 8820) - 1
    Pp = Fr(8820) / (1 + r) ** 2
    assert r == Fr(1, 20) and Pp == 8000
    q("sici", "L3", "o", "A sum at compound interest amounts to ₹8,820 in 2 years and ₹9,261 in 3 years. The sum is:",
      Rs(Pp),
      [(Rs(8820 - 441), "third-year interest subtracted once"), (Rs(Fr(8820) / Fr(105, 100)), "only one year undone"),
       (Rs(D(Fr(8820) * Fr(9, 10))), "10% deducted from 2-year amount")],
      ["Rate = 441/8,820 = 5%", "P = 8,820/1.05² = 8,000"],
      "r = (A₃ − A₂)/A₂", "Undo two years of compounding.")

    Pp, r = 15000, Fr(1, 10)
    si = Pp * r * 3
    ci = Pp * ((1 + r) ** 3 - 1)
    q("sici", "L3", "o", "The difference between compound and simple interest on ₹15,000 for 3 years at 10% per annum is:",
      Rs(ci - si),
      [(Rs(Pp * r ** 2), "2-year difference formula used"), (Rs(3 * Pp * r ** 2), "2-year difference tripled"), (Rs(ci), "CI reported")],
      ["SI = 4,500", "CI = 15,000 × 0.331 = 4,965", "Difference = 465"],
      "CI − SI (3 yrs) = P r²(3 + r)", "The 3-year gap is not three times the 2-year gap.")

    si = Fr(8400 - 7280, 2)
    Pp = 7280 - 3 * si
    r = si / Pp * 100
    assert r == 10
    q("sici", "L3", "o", "A sum at simple interest amounts to ₹7,280 in 3 years and ₹8,400 in 5 years. The rate of interest is:",
      P(r),
      [(P(D(si / 7000 * 100)), "₹560 divided by a rounded principal of ₹7,000"), (P(D(si / 7280 * 100)), "yearly interest divided by 3-year amount"),
       (P(D(si / 8400 * 100)), "yearly interest divided by 5-year amount")],
      ["Interest for 2 years = 1,120 ⇒ 560 a year", "P = 7,280 − 1,680 = 5,600", "R = 560/5,600 = 10%"],
      "Yearly SI = ΔA ÷ Δt", "Rate is on the principal.")

    x = Fr(20000 * 12 - 196000, 4)
    assert x == 11000
    q("sici", "L3", "o", "₹20,000 is lent partly at 8% and partly at 12% simple interest. The total yearly interest is ₹1,960. The amount lent at 8% is:",
      Rs(x),
      [(Rs(20000 - x), "rates swapped"), (Rs(10000), "equal split assumed"), (Rs(12000), "interest taken as ₹1,920")],
      ["0.08x + 0.12(20,000 − x) = 1,960", "2,400 − 0.04x = 1,960 ⇒ x = 11,000"],
      "Alligation on rates: average 9.8%", "Larger share goes to the rate nearer 9.8%.")

    q("sici", "L3", "o", "At compound interest a sum becomes 3 times itself in 5 years. In how many years will it become 27 times itself?",
      "15 years",
      [("45 years", "27/3 × 5"), ("10 years", "only two tripling periods"), ("65 years", "treated as simple interest")],
      ["27 = 3³", "Three tripling periods = 15 years"],
      "(1 + r)^(kn) = 3^k", "Compounding multiplies; simple interest adds.")

    r = Fr(7290, 6250)
    assert r == Fr(27, 25) ** 2
    q("sici", "L3", "o", "At what rate of compound interest per annum will ₹6,250 amount to ₹7,290 in 2 years?",
      P(8),
      [(P(D(Fr(1040, 6250) / 2 * 100)), "simple-interest rate"), (P(D(Fr(1040, 6250) * 100)), "total growth over 2 years"), (P(9), "rough square root")],
      ["7,290/6,250 = 1.1664 = 1.08²", "Rate = 8%"],
      "(1 + r)² = A/P", "Take the square root of the growth factor.")

    x = Fr(50000) / (Fr(10, 11) + Fr(100, 121))
    q("sici", "L3", "o", "A loan of ₹50,000 at 10% compound interest per annum is repaid in two equal annual instalments. Each instalment is:",
      RsD(x),
      [(Rs(27500), "SI for one year then halved"), (Rs(30250), "2-year amount split equally"),
       (RsD(Fr(50000) / (Fr(10, 11) + Fr(10, 12))), "second instalment discounted at simple interest")],
      ["x/1.1 + x/1.21 = 50,000", "x = 50,000 × 1.21/2.1 = 28,809.52"],
      "Loan = Σ PV of instalments", "Discount each instalment for its own period.")

    Pp = Fr(5400 * 100, 12 * 3)
    assert Pp == 15000
    q("sici", "L3", "o", "The simple interest on a sum for 3 years at 12% per annum is ₹5,400. The compound interest on the same sum for 2 years at 10% per annum is:",
      Rs(Pp * (Fr(121, 100) - 1)),
      [(Rs(Pp * Fr(20, 100)), "SI at 10% for 2 years"), (Rs(Pp * Fr(24, 100)), "SI at 12% for 2 years"),
       (Rs(Pp * (Fr(112, 100) ** 2 - 1)), "CI at 12% instead of 10%")],
      ["P = 5,400 × 100/36 = 15,000", "CI = 15,000 × 0.21 = 3,150"],
      "SI → P; then CI = P[(1 + r)² − 1]", "Switch rates after finding P.")

    Pp = Fr(3900) / Fr(39, 100)
    assert Pp == 10000
    q("sici", "L3", "o", "A sum earns simple interest at 6% per annum for the first 2 years and 9% per annum for the next 3 years. The total interest is ₹3,900. The sum is:",
      Rs(Pp),
      [(Rs(26000), "rates added (15%) and used once"), (Rs(13000), "6% and 9% each applied for 2 years only (30%)"), (Rs(10400), "average rate 7.5% × 5 years")],
      ["Total rate = 6 × 2 + 9 × 3 = 39%", "P = 3,900/0.39 = 10,000"],
      "SI = P Σ(rᵢtᵢ)", "Weight each rate by its years.")

    diff = 40000 * (Fr(121, 100) - Fr(12, 10))
    assert diff == 400
    q("sici", "L3", "o", "On ₹40,000 at 20% per annum for 1 year, the compound interest compounded half-yearly exceeds that compounded annually by:",
      Rs(diff),
      [(Rs(800), "(r/2)² taken as 2%"), (Rs(200), "used 5% per half-year"), ("₹0", "believes same annual rate gives same interest")],
      ["Half-yearly: 40,000 × 1.1² = 48,400 ⇒ CI 8,400", "Annual: 8,000", "Difference = 400"],
      "Extra = P(r/2)²", "Interest on the first half-year's interest.")
