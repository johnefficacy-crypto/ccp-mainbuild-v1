"""ECO part 3 — Micro: demand, elasticity, surplus, tax incidence, market structures (44 Q: L1 9, L2 14, L3 13, L4 8)."""
from eco_common import mk, cr, n, tbl, items, stmts, inr, R, pct


def lin_eq(a, b, c, d):
    """Qd = a − bP, Qs = c + dP  →  (P, Q)."""
    P = (a - c) / (b + d)
    return P, a - b * P


def add_all(B):
    q = mk(B)
    PQ = lambda P, Q: f"P = ₹{n(P)}, Q = {n(Q)} units"

    # ======================= L1 =======================
    q("bandwagon", "L1", "A good whose demand rises as its price rises because consumers value it for conspicuous display of wealth exhibits:",
      "The Veblen effect",
      [("The Giffen paradox", "Giffen goods are inferior goods with a dominant income effect, not status goods"),
       ("The bandwagon effect", "bandwagon depends on how many others buy, not on price as a status signal"),
       ("The snob effect", "snob demand falls as more people buy the good")],
      ["Veblen goods: the high price itself is the source of utility (conspicuous consumption).", "Their demand curve can slope upward over a range."],
      "—", "Veblen = price as status; Giffen = inferior staple.", kind="conceptual")

    q("law-of-demand", "L1", "Which feature distinguishes a Giffen good from other exceptions to the law of demand?",
      "It is an inferior good whose income effect outweighs the substitution effect",
      [("It is a luxury good bought mainly to display wealth and social status", "that describes a Veblen good"),
       ("Its demand rises simply because many others are also buying it", "bandwagon effect"),
       ("Buyers expect its price to keep rising further in the near future", "speculative/expectational exception")],
      ["Price rise → real income falls → poor households buy MORE of the inferior staple.", "Negative substitution effect is swamped by the income effect."],
      "Price effect = Substitution effect + Income effect", "All Giffen goods are inferior; not all inferior goods are Giffen.", kind="conceptual")

    q("perfect-competition", "L1", "For a firm under perfect competition:",
      "Average revenue, marginal revenue and price are all equal",
      [("Marginal revenue is less than price", "that is true of a firm facing a downward-sloping demand"),
       ("The firm's demand curve is downward sloping", "the firm's demand is perfectly elastic at the market price"),
       ("The firm earns supernormal profits in the long run", "free entry drives long-run profits to normal")],
      ["The firm is a price taker: every unit sells at P.", "Hence AR = MR = P and the firm's demand curve is horizontal."],
      "AR = MR = P", "The industry demand curve slopes down; the firm's does not.", kind="conceptual")

    q("monopoly", "L1", "A profit-maximising monopolist with positive marginal cost always produces where:",
      "Demand is price-elastic (|e| > 1), because MR = MC > 0",
      [("Demand is price-inelastic, so it can raise price freely", "with inelastic demand MR < 0, so output should be cut"),
       ("Demand has unit elasticity", "unit elasticity gives MR = 0, optimal only if MC = 0"),
       ("Price equals marginal cost", "that is the competitive outcome")],
      ["MR = P(1 − 1/|e|).", "MR = MC > 0 ⇒ 1 − 1/|e| > 0 ⇒ |e| > 1."],
      "MR = P(1 − 1/|e|)", "No monopolist operates on the inelastic part of demand.", kind="conceptual")

    q("kinked-demand", "L1", "Sweezy's kinked demand curve model explains:",
      "Price rigidity in oligopoly: rivals match price cuts but not price rises",
      [("Price leadership by a dominant firm with smaller followers", "a different oligopoly model"),
       ("Output determination when each firm treats the rival's output as fixed", "that is Cournot"),
       ("Price discrimination across markets with different elasticities", "third-degree price discrimination")],
      ["Demand is elastic above the ruling price (rivals don't follow a rise) and inelastic below (they match a cut).",
       "The kink creates a gap in MR; MC can shift within it without changing price."],
      "Discontinuous MR at the kink", "The model explains why price sticks, not how it was first set.", kind="conceptual")

    q("monopolistic-competition", "L1", "In long-run equilibrium under monopolistic competition, each firm:",
      "Earns only normal profit and operates with excess capacity",
      [("Earns supernormal profit protected by product differentiation", "free entry erodes supernormal profit"),
       ("Produces at the minimum point of its long-run average cost curve", "that is perfect competition"),
       ("Charges a price equal to marginal cost", "P > MC because demand slopes down")],
      ["Entry shifts each firm's demand left until it is tangent to LAC.", "Tangency occurs on the falling part of LAC ⇒ output below minimum-cost level (excess capacity)."],
      "LR: P = LAC > MC", "Chamberlin's tangency solution.", kind="conceptual")

    q("consumer-surplus", "L1", "Consumer surplus is:",
      "The excess of willingness to pay over the price actually paid",
      [("The excess of the market price over marginal cost", "that is the mark-up / producer-side measure"),
       ("Total expenditure of consumers on the good concerned", "that is price × quantity"),
       ("The area above the supply curve and below the price line", "that is producer surplus")],
      ["Graphically: area below the demand curve and above the price line, up to the quantity bought."],
      "CS = Σ(willingness to pay) − P × Q", "Producer surplus lies below the price line.", kind="conceptual")

    q("law-of-supply", "L1", "A rise in the price of a good, other things constant, leads to:",
      "An extension of supply along the same supply curve",
      [("A rightward shift of the whole supply curve", "shifts are caused by non-price determinants"),
       ("A leftward shift of the whole supply curve", "wrong direction and wrong concept"),
       ("A contraction of supply along the same curve", "higher price raises quantity supplied")],
      ["Own-price changes move the firm along the curve.", "Technology, input prices, taxes etc. shift the curve."],
      "Qs = f(P | other determinants fixed)", "Movement vs shift is the standard trap.", kind="conceptual")

    q("price-and-income", "L1", "A negative income elasticity of demand indicates that the good is:",
      "An inferior good",
      [("A luxury good", "luxuries have income elasticity above 1"),
       ("A necessity", "necessities have income elasticity between 0 and 1"),
       ("A Veblen good", "Veblen is about price, not income")],
      ["e_Y = %ΔQ ÷ %ΔY < 0 ⇒ demand falls as income rises."],
      "e_Y = (ΔQ/Q) ÷ (ΔY/Y)", "Inferior ≠ Giffen.", kind="conceptual")

    # ======================= L2 =======================
    P, Q = lin_eq(100, 2, -20, 4)
    Pw, Qw = lin_eq(100, 2, 20, 4)
    Ps_ = (100 + 20) / (4 - 2)
    q("equilibrium-from-demand", "L2", "Demand and supply functions are Qd = 100 − 2P and Qs = −20 + 4P. Equilibrium price and quantity are:",
      PQ(P, Q),
      [(PQ(Pw, Qw), "sign of the supply intercept reversed"),
       (PQ(Ps_, -20 + 4 * Ps_), "slope of demand taken as positive"),
       (PQ(P, 4 * P), "quantity computed from supply with its intercept dropped")],
      ["100 − 2P = −20 + 4P ⇒ 6P = 120 ⇒ P = 20", "Q = 100 − 40 = 60"],
      "Qd = Qs", "Check Q in BOTH functions.")

    p0, p1, q0, q1 = 10, 12, 100, 80
    mid = abs((q1 - q0) / ((q0 + q1) / 2) / ((p1 - p0) / ((p0 + p1) / 2)))
    q("price-and-income", "L2", f"When the price of a good rises from ₹{p0} to ₹{p1}, quantity demanded falls from {q0} to {q1} units. The arc (mid-point) price elasticity of demand, in absolute value, is:",
      n(mid),
      [(n(abs((q1 - q0) / q0 / ((p1 - p0) / p0))), "initial values used as base (point method)"),
       (n(abs((q1 - q0) / q1 / ((p1 - p0) / p1))), "final values used as base"),
       (n(1 / mid), "ratio inverted (%ΔP ÷ %ΔQ)")],
      [f"%ΔQ = −20/90 = {n(-20/90*100)}%", f"%ΔP = 2/11 = {n(2/11*100)}%", f"|e| = {n(mid)}"],
      "e_arc = [ΔQ/((Q₀+Q₁)/2)] ÷ [ΔP/((P₀+P₁)/2)]", "Arc elasticity uses averages so the answer is the same either direction.")

    y0, y1, qa, qb = 40000, 50000, 20, 23
    ey = ((qb - qa) / qa) / ((y1 - y0) / y0)
    q("price-and-income", "L2", f"When monthly income rises from ₹{inr(y0)} to ₹{inr(y1)}, a household's purchase of a good rises from {qa} to {qb} units. Using initial values as base, the income elasticity and the nature of the good are:",
      f"{n(ey)}; normal good — necessity",
      [(f"{n(1/ey)}; normal good — luxury", "ratio inverted"),
       (f"{n(ey)}; inferior good", "positive elasticity misread"),
       (f"{n(ey)}; normal good — luxury", "luxury requires e_Y > 1")],
      [f"%ΔQ = 3/20 = 15%; %ΔY = 10,000/40,000 = 25%", f"e_Y = 15/25 = {n(ey)} ⇒ 0 < e_Y < 1 ⇒ necessity"],
      "e_Y = %ΔQ ÷ %ΔY", "Between 0 and 1: normal necessity.")

    q("price-and-income", "L2", "The price of tea rises by 10% and, other things equal, the quantity of coffee demanded rises by 6%. The cross elasticity and the relationship are:",
      "+0.6; substitutes",
      [("−0.6; complements", "sign of the coffee response reversed"),
       ("+1.67; substitutes", "ratio inverted"),
       ("+0.6; complements", "positive cross elasticity misinterpreted")],
      ["e_xy = %ΔQ_coffee ÷ %ΔP_tea = 6/10 = +0.6", "Positive ⇒ substitutes."],
      "e_xy = %ΔQ_x ÷ %ΔP_y", "Complements have negative cross elasticity.")

    e_, cut = 1.5, 0.10
    dtr = (1 - cut) * (1 + e_ * cut) - 1
    q("price-and-income", "L2", f"Price elasticity of demand is {e_} (absolute) and is assumed constant over the range. If the firm cuts price by {pct(cut)}, total revenue changes by:",
      f"+{pct(dtr,1)}",
      [(f"−{pct(dtr,1)}", "direction reversed — revenue rises when elastic demand faces a price cut"),
       (f"+{pct(e_*cut - cut,1)}", "approximation: %ΔQ − %ΔP"),
       (f"+{pct(e_*cut,1)}", "change in quantity reported as change in revenue")],
      [f"%ΔQ = 1.5 × 10% = 15%", f"TR ratio = 0.90 × 1.15 = {n(0.9*1.15,3)} ⇒ +{pct(dtr,1)}"],
      "TR₁/TR₀ = (1 + %ΔP)(1 + %ΔQ)", "Elastic demand: price and revenue move in opposite directions.")

    Pc, Qc = 20, (50 - 20) / 0.5
    cs = 0.5 * Qc * (50 - Pc)
    q("consumer-surplus", "L2", "Inverse demand is P = 50 − 0.5Q and the market price is ₹20. Consumer surplus is:",
      R(cs),
      [(R(Qc * (50 - Pc)), "triangle taken as a rectangle (½ omitted)"),
       (R(0.5 * Qc * Pc), "height taken as the price instead of (choke price − price)"),
       (R(0.5 * (Qc / 2) * (50 - Pc)), "quantity halved (misread slope)")],
      [f"Q = (50 − 20)/0.5 = {n(Qc)}", f"CS = ½ × {n(Qc)} × (50 − 20) = {inr(cs)}"],
      "CS = ½ × Q × (P_choke − P)", "Height = choke price minus market price.")

    Qs_ = (20 - 10) / 0.25
    ps = 0.5 * Qs_ * (20 - 10)
    q("consumer-surplus", "L2", "Inverse supply is P = 10 + 0.25Q and the market price is ₹20. Producer surplus is:",
      R(ps),
      [(R(2 * ps), "½ omitted"),
       (R(20 * Qs_), "total revenue reported"),
       (R(20 * Qs_ - ps), "area under the supply curve (variable cost) reported")],
      [f"Q = (20 − 10)/0.25 = {n(Qs_)}", f"PS = ½ × {n(Qs_)} × (20 − 10) = {inr(ps)}"],
      "PS = ½ × Q × (P − P_min)", "Producer surplus lies above supply, below price.")

    ed, es, tax = 0.5, 1.5, 8
    cons = tax * es / (es + ed)
    q("tax-incidence", "L2", f"At the equilibrium, price elasticity of demand is {ed} and of supply is {es} (absolute values). A specific tax of ₹{tax} per unit is levied on sellers. The part borne by consumers is about:",
      f"₹{n(cons)} per unit",
      [(f"₹{n(tax*ed/(es+ed))} per unit", "shares interchanged — consumers bear the SUPPLY-elasticity share"),
       (f"₹{tax} per unit", "statutory incidence taken as economic incidence"),
       (f"₹{n(tax/2)} per unit", "equal split assumed")],
      [f"Consumer share = e_s/(e_s + e_d) = 1.5/2.0 = 75%", f"₹{tax} × 75% = ₹{n(cons)}"],
      "Buyers' share = e_s ÷ (e_s + e_d)", "The less elastic side bears more.")

    P9, avc, tfc, Q9 = 20, 22, 1000, 100
    loss_run = (P9 - avc) * Q9 - tfc
    q("perfect-competition", "L2",
      f"A competitive firm faces a market price of ₹{P9}. At its best output of {Q9} units, AVC is ₹{avc}; total fixed cost is ₹{inr(tfc)}. In the short run the firm should:",
      f"Shut down — its loss is limited to fixed cost of ₹{inr(tfc)}",
      [(f"Continue — the loss is only ₹{inr(-(P9-avc)*Q9)} on variable cost", "fixed cost ignored in comparing losses"),
       (f"Continue — the loss of ₹{inr(-loss_run)} is unavoidable anyway", "fails to compare with the shut-down loss"),
       ("Shut down — its loss becomes zero", "fixed cost is sunk in the short run")],
      [f"If it produces: TR − TC = {inr(P9*Q9)} − ({inr(avc*Q9)} + {inr(tfc)}) = {inr(loss_run)}", f"If it shuts down: loss = TFC = {inr(tfc)}",
       "P < min AVC ⇒ shut down."],
      "Shut-down rule: P < AVC", "Compare losses, not profits.")

    Qm, Pm = (100 - 20) / 4, 100 - 2 * 20
    q("monopoly", "L2", "A monopolist faces P = 100 − 2Q and has constant marginal cost of ₹20. Profit-maximising output and price are:",
      f"Q = {n(Qm)}, P = ₹{n(100-2*Qm)}",
      [(f"Q = {n((100-20)/2)}, P = ₹20", "P = MC (competitive) rule used"),
       (f"Q = {n(Qm)}, P = ₹20", "price read off the MC/MR curve instead of demand"),
       (f"Q = 25, P = ₹50", "revenue maximised (MR = 0) instead of profit")],
      ["MR = 100 − 4Q", "MR = MC ⇒ 100 − 4Q = 20 ⇒ Q = 20", "P = 100 − 40 = 60"],
      "MR = MC; price from demand curve", "Price is read from the demand curve at the optimal Q.")

    Pl, MCl = 60, 20
    q("monopoly", "L2", f"A profit-maximising monopolist charges ₹{Pl} with marginal cost of ₹{MCl}. The absolute price elasticity of demand at this point is:",
      n(Pl / (Pl - MCl)),
      [(n((Pl - MCl) / Pl), "Lerner index reported instead of elasticity"),
       (n(Pl / MCl), "price-to-MC ratio reported"),
       (n(MCl / Pl), "MC/P ratio reported")],
      [f"Lerner index = (P − MC)/P = 40/60 = {n((Pl-MCl)/Pl)}", f"= 1/|e| ⇒ |e| = {n(Pl/(Pl-MCl))}"],
      "(P − MC)/P = 1/|e|", "Lerner index is the reciprocal of elasticity.")

    a, c = 120, 0
    qc = (a - c) / 3
    q("cournot", "L2", "Two identical firms produce a homogeneous good with zero cost. Market demand is P = 120 − Q. In the Cournot–Nash equilibrium, total output and price are:",
      f"Q = {n(2*qc)}, P = ₹{n(a-2*qc)}",
      [("Q = 60, P = ₹60", "joint monopoly (cartel) outcome"),
       ("Q = 120, P = ₹0", "competitive / Bertrand outcome"),
       ("Q = 90, P = ₹30", "Stackelberg leader-follower outcome")],
      ["Reaction: q₁ = (120 − q₂)/2", "Symmetry ⇒ q = 40 each", "Q = 80, P = 40"],
      "q_i = (a − c)/3 each", "Cournot lies between monopoly and competition.")

    q("bandwagon", "L2", "When a bandwagon effect is present, the market demand curve compared with the horizontal sum of individual demand curves (drawn assuming others' purchases fixed) is:",
      "More elastic",
      [("Less elastic", "that is the snob effect"),
       ("Upward sloping", "that is a Veblen / Giffen property"),
       ("Perfectly inelastic", "no basis")],
      ["A price fall raises quantity through the price effect AND because more people are buying.", "The extra 'bandwagon' response flattens market demand."],
      "Market response = price effect + bandwagon effect", "Snob effect works the other way.", kind="conceptual")

    ps0, ps1, qs0, qs1 = 40, 44, 200, 230
    esup = ((qs1 - qs0) / qs0) / ((ps1 - ps0) / ps0)
    q("law-of-supply", "L2", f"Price rises from ₹{ps0} to ₹{ps1} and quantity supplied rises from {qs0} to {qs1} units. Price elasticity of supply (initial base) is:",
      n(esup),
      [(n(((qs1-qs0)/((qs0+qs1)/2))/((ps1-ps0)/((ps0+ps1)/2)), 4), "mid-point formula used when initial base was asked"),
       (n(1 / esup), "ratio inverted"),
       (n((qs1 - qs0) / (ps1 - ps0)), "slope ΔQ/ΔP reported, not elasticity")],
      [f"%ΔQs = 30/200 = 15%; %ΔP = 4/40 = 10%", f"e_s = {n(esup)}"],
      "e_s = %ΔQs ÷ %ΔP", "Elasticity is unit-free; slope is not.")

    # ======================= L3 =======================
    P0, Q0 = lin_eq(120, 2, -30, 3)
    t = 5
    Pc1, Q1 = lin_eq(120, 2, -30 - 3 * t, 3)
    Pw1, Qw1 = lin_eq(120, 2, -30 - t, 3)
    assert (P0, Q0, Pc1, Q1) == (30, 60, 33, 54)
    q("tax-incidence", "L3",
      f"Qd = 120 − 2P and Qs = −30 + 3P (P = price received by sellers). A specific tax of ₹{t} per unit is imposed on sellers. The new price paid by consumers and quantity traded are:",
      f"₹{n(Pc1)}; {n(Q1)} units",
      [(f"₹{n(P0+t)}; {n(120-2*(P0+t))} units", "tax fully passed on to consumers"),
       (f"₹{n(Pc1-t)}; {n(Q1)} units", "sellers' net price reported"),
       (f"₹{n(Pw1)}; {n(Qw1)} units", "tax treated as a 5-unit fall in quantity supplied instead of a ₹5 price wedge")],
      [f"Pre-tax: P = {n(P0)}, Q = {n(Q0)}", f"With tax: Qs = −30 + 3(P − 5) ⇒ 120 − 2P = −45 + 3P ⇒ P = {n(Pc1)}",
       f"Q = {n(Q1)}; sellers get ₹{n(Pc1-t)}"],
      "Replace P by (P − t) in the supply function", "Consumers bear ₹3, sellers ₹2 — ratio of slopes.")

    dwl = 0.5 * t * (Q0 - Q1)
    q("tax-incidence", "L3", f"In the previous market (Qd = 120 − 2P, Qs = −30 + 3P, specific tax ₹{t}), the deadweight loss of the tax is:",
      R(dwl),
      [(R(2 * dwl), "½ omitted from the Harberger triangle"),
       (R(t * Q1), "tax revenue reported"),
       (R(0.5 * t * Q1), "½ × tax × post-tax quantity used")],
      [f"ΔQ = {n(Q0)} − {n(Q1)} = {n(Q0-Q1)}", f"DWL = ½ × {t} × {n(Q0-Q1)} = {n(dwl)}"],
      "DWL = ½ × t × ΔQ", "Revenue is a transfer; only the triangle is lost.")

    qa_, qb_ = 100 - 20, 100 - 30
    dcs = (qa_ + qb_) / 2 * 10
    q("consumer-surplus", "L3", "Demand is Q = 100 − P. Price rises from ₹20 to ₹30. Consumer surplus falls by:",
      R(dcs),
      [(R(qa_ * 10), "initial quantity × price rise (rectangle only on old Q)"),
       (R(qb_ * 10), "new quantity × price rise — triangle omitted"),
       (R(0.5 * (qa_ - qb_) * 10), "only the small triangle counted")],
      [f"Q falls from {qa_} to {qb_}", f"ΔCS = trapezium = ½ × ({qa_} + {qb_}) × 10 = {inr(dcs)}"],
      "ΔCS = ½(Q₀ + Q₁)ΔP", "Loss = rectangle on new Q + triangle on lost units.")

    Qmo, Pmo, Qco = 40, 60, 80
    dwlm = 0.5 * (Qco - Qmo) * (Pmo - 20)
    q("monopoly", "L3", "Market demand is P = 100 − Q and marginal cost is constant at ₹20. Compared with perfect competition, the deadweight loss under a single-price monopoly is:",
      R(dwlm),
      [(R((Pmo - 20) * Qmo), "monopoly profit reported"),
       (R(0.5 * Qco * (100 - 20)), "consumer surplus under competition reported"),
       (R(dwlm / 2), "base of the triangle taken as half the output gap")],
      ["Monopoly: MR = 100 − 2Q = 20 ⇒ Q = 40, P = 60", "Competition: P = MC ⇒ Q = 80",
       f"DWL = ½ × (80 − 40) × (60 − 20) = {inr(dwlm)}"],
      "DWL = ½ (Q_c − Q_m)(P_m − MC)", "Monopoly profit is a transfer from consumers, not a deadweight loss.")

    qmin, acmin = 10, 100 / 10 + 4 + 10
    Nf = (1000 - 20 * acmin) / qmin
    q("perfect-competition", "L3",
      "Each firm in a perfectly competitive industry has TC = 100 + 4q + q² (identical firms, free entry). Market demand is Q = 1,000 − 20P. In long-run equilibrium the number of firms is:",
      f"{n(Nf)}",
      [(f"{n((1000 - 20*4)/qmin)}", "minimum AVC (₹4) used as the long-run price"),
       (f"{n((1000 - 20*acmin)/20)}", "MC taken as 4 + q, giving firm output 20"),
       (f"{n(1000 - 20*acmin)}", "market quantity reported as number of firms")],
      ["AC = 100/q + 4 + q; minimum where 100/q² = 1 ⇒ q = 10, AC = 24", "Long-run price = min AC = ₹24",
       f"Market Q = 1,000 − 480 = 520 ⇒ firms = 520/10 = {n(Nf)}"],
      "LR: P = min LAC; N = Q_market / q*", "Check: MC = 4 + 2q = 24 at q = 10.")

    mr_up, mr_lo = 80 - 2 * 20, 110 - 5 * 20
    q("kinked-demand", "L3",
      "An oligopolist's demand curve has a kink at Q = 20, P = ₹60. Above the kink demand is P = 80 − Q; below it demand is P = 110 − 2.5Q. The firm will keep its price at ₹60 so long as marginal cost at Q = 20 lies between:",
      f"₹{mr_lo} and ₹{mr_up}",
      [(f"₹{mr_up} and ₹60", "upper bound taken as price instead of MR of the upper segment"),
       (f"₹{mr_lo} and ₹60", "upper bound taken as price"),
       ("Any value below ₹60", "price at the kink treated as the only bound on MC")],
      [f"Upper MR = 80 − 2Q = {mr_up} at Q = 20", f"Lower MR = 110 − 5Q = {mr_lo} at Q = 20", "MC anywhere in the gap keeps P = 60."],
      "MR of linear P = a − bQ is a − 2bQ", "The gap is vertical, between the two MR values.")

    a7, c1, c2 = 100, 10, 16
    q1_ = (a7 - 2 * c1 + c2) / 3; q2_ = (a7 - 2 * c2 + c1) / 3
    assert (q1_, q2_) == (32, 26)
    q("cournot", "L3",
      f"Two Cournot duopolists face P = {a7} − (q₁ + q₂). Firm 1's marginal cost is ₹{c1} and Firm 2's is ₹{c2} (both constant). Equilibrium outputs are:",
      f"q₁ = {n(q1_)}, q₂ = {n(q2_)}; P = ₹{n(a7-q1_-q2_)}",
      [(f"q₁ = {n((a7-(c1+c2)/2)/3)}, q₂ = {n((a7-(c1+c2)/2)/3)}; P = ₹{n(a7-2*(a7-(c1+c2)/2)/3)}", "average cost used for both firms"),
       (f"q₁ = {n(q2_)}, q₂ = {n(q1_)}; P = ₹{n(a7-q1_-q2_)}", "costs assigned to the wrong firms"),
       (f"q₁ = {n((a7-c1)/2)}, q₂ = {n((a7-c2)/2)}; P = ₹{n(a7-(a7-c1)/2-(a7-c2)/2)}", "each firm acts as if it were a monopolist")],
      ["Reaction functions: q₁ = (90 − q₂)/2, q₂ = (84 − q₁)/2", f"Solve: q₁ = {n(q1_)}, q₂ = {n(q2_)}", f"P = 100 − 58 = {n(a7-q1_-q2_)}"],
      "q_i = (a − 2c_i + c_j)/3", "Lower-cost firm produces more.")

    q("monopolistic-competition", "L3",
      "Consider the following statements about long-run equilibrium under monopolistic competition:\n\n" + stmts([
          "Price equals long-run average cost.",
          "Price exceeds marginal cost.",
          "Each firm produces at the minimum point of its long-run average cost curve.",
          "Selling costs (advertising) are a characteristic feature of the market."]) + "\n\nWhich are correct?",
      "1, 2 and 4 only",
      [("1 and 2 only", "misses selling costs, a hallmark of Chamberlin's model"),
       ("1, 2, 3 and 4", "excess capacity means output is below the minimum-LAC level"),
       ("2, 3 and 4 only", "long-run profits are normal (P = LAC)")],
      ["Tangency with LAC ⇒ P = LAC (1).", "Downward-sloping demand ⇒ P > MC (2).", "Tangency on falling LAC ⇒ not minimum (3 false).", "Differentiation is promoted through selling costs (4)."],
      "LR tangency: P = LAC, MR = LMC", "Excess capacity is the key contrast with perfect competition.", kind="statement")

    q("oligopoly", "L3",
      "Match the oligopoly model with its behavioural assumption:\n\n" + tbl(["Model", "", "Assumption"], [
          ("A. Cournot", "", "1. Rivals match price cuts but ignore price increases"),
          ("B. Bertrand", "", "2. Leader chooses output anticipating the follower's reaction"),
          ("C. Sweezy", "", "3. Each firm takes the rival's output as given"),
          ("D. Stackelberg", "", "4. Each firm takes the rival's price as given")], right=set()) + "\n\nCodes (A-B-C-D):",
      "3-4-1-2",
      [("4-3-1-2", "Cournot and Bertrand interchanged"),
       ("3-4-2-1", "Sweezy and Stackelberg interchanged"),
       ("3-1-4-2", "Bertrand and Sweezy interchanged")],
      ["Cournot: quantity competition, rival output fixed (3).", "Bertrand: price competition, rival price fixed (4).",
       "Sweezy: kinked demand (1).", "Stackelberg: sequential leader-follower (2)."],
      "—", "Cournot ↔ quantity, Bertrand ↔ price.", kind="conceptual")

    q("bandwagon", "L3",
      "Match the demand phenomenon with its description:\n\n" + tbl(["Effect", "", "Description"], [
          ("A. Bandwagon", "", "1. Demand falls as more people consume the good"),
          ("B. Snob", "", "2. Inferior staple whose demand rises when its price rises"),
          ("C. Veblen", "", "3. Demand rises because others are consuming the good"),
          ("D. Giffen", "", "4. Demand rises because a higher price signals status")], right=set()) + "\n\nCodes (A-B-C-D):",
      "3-1-4-2",
      [("1-3-4-2", "bandwagon and snob interchanged"),
       ("3-1-2-4", "Veblen and Giffen interchanged"),
       ("3-4-1-2", "snob and Veblen interchanged")],
      ["Bandwagon: join the crowd (3).", "Snob: exclusivity (1).", "Veblen: conspicuous price (4).", "Giffen: income effect on inferior staple (2)."],
      "Leibenstein (1950) external effects on demand", "Snob and Veblen are both about exclusivity but respond to different signals.", kind="conceptual")

    q("tax-incidence", "L3",
      "Consider the following statements on tax incidence:\n\n" + stmts([
          "If demand is perfectly inelastic, a per-unit tax is borne entirely by buyers and causes no deadweight loss.",
          "The economic incidence of a tax depends on whether it is legally levied on buyers or on sellers.",
          "The side of the market with the more elastic response bears the smaller share of the tax.",
          "For small taxes with linear curves, deadweight loss rises roughly with the square of the tax rate."]) + "\n\nWhich are correct?",
      "1, 3 and 4 only",
      [("1 and 3 only", "misses the square rule of excess burden"),
       ("1, 2, 3 and 4", "statutory incidence does not determine economic incidence"),
       ("2, 3 and 4 only", "rejects the perfectly inelastic case")],
      ["Perfectly inelastic demand: quantity unchanged ⇒ no DWL; price rises by full tax (1).", "Incidence is independent of statutory point (2 false).",
       "Burden shares ∝ inverse elasticities (3).", "DWL = ½ t ΔQ and ΔQ ∝ t ⇒ DWL ∝ t² (4)."],
      "Buyer share = e_s/(e_s + e_d); DWL ≈ ½ t² × e_d e_s/(e_d+e_s) × Q/P", "Who writes the cheque does not matter.", kind="statement")

    Pq = 30; Qq = 200 - 4 * Pq; eq = 4 * Pq / Qq
    q("price-and-income", "L3", f"Demand is Q = 200 − 4P. At P = ₹{Pq}, the absolute price elasticity of demand and the effect of a small price increase on total revenue are:",
      f"{n(eq)}; total revenue falls",
      [(f"{n(eq)}; total revenue rises", "elastic demand misinterpreted"),
       (f"{n(1/eq)}; total revenue rises", "P/Q ratio inverted, giving inelastic reading"),
       (f"{n(4*Qq/Pq)}; total revenue falls", "slope multiplied by Q/P instead of P/Q")],
      [f"Q = 200 − 120 = {Qq}", f"|e| = 4 × {Pq}/{Qq} = {n(eq)} > 1 ⇒ elastic", "Price rise ⇒ TR falls (TR max at P = 25)."],
      "|e| = |dQ/dP| × P/Q", "Elasticity changes along a linear demand curve.")

    P0s, Q0s = lin_eq(120, 2, -30, 3)
    P1s, Q1s = lin_eq(150, 2, -30, 3)
    Pr, Qr = lin_eq(90, 2, -30, 3)
    q("law-of-supply", "L3", "Supply is Qs = −30 + 3P. Demand rises from Qd = 120 − 2P to Qd = 150 − 2P. The new equilibrium is:",
      PQ(P1s, Q1s),
      [(PQ(P0s, 150 - 2 * P0s), "price not allowed to adjust — new quantity demanded at old price"),
       (PQ(Pr, Qr), "demand shift entered with the wrong sign"),
       (PQ(P1s, 120 - 2 * P1s), "quantity read off the old demand curve")],
      ["150 − 2P = −30 + 3P ⇒ P = 36", "Q = 150 − 72 = 78 (check: −30 + 108 = 78)", f"Old equilibrium was P = {n(P0s)}, Q = {n(Q0s)}."],
      "Qd' = Qs", "Demand shift ⇒ movement ALONG supply (extension).")

    # ======================= L4 case F (market) =======================
    GF = "ECO-MKT-CASE-F"
    aF, bF, cF, dF = 240, 4, -60, 6
    PF, QF = lin_eq(aF, bF, cF, dF)
    assert (PF, QF) == (30, 120)
    stemF = ("**Case — Kavera widget market.** Market demand is Qd = 240 − 4P and market supply is Qs = −60 + 6P "
             "(Q in thousand units, P in ₹ per unit, P = price received by sellers).\n\n")
    Pa, Qa = lin_eq(aF, bF, -cF, dF)
    Pb = (aF - cF) / (dF - bF)
    q("equilibrium-from-demand", "L4", stemF + "**Q.** The market equilibrium is:",
      PQ(PF, QF),
      [(PQ(Pa, Qa), "sign of the supply intercept reversed"),
       (PQ(PF, dF * PF), "supply intercept dropped when computing Q"),
       (PQ(Pb, aF + bF * Pb), "demand slope taken as positive")],
      ["240 − 4P = −60 + 6P ⇒ P = 30", "Q = 240 − 120 = 120"],
      "Qd = Qs", "Plug P back into both curves.", kind="case", group=GF)
    tF = 5
    PcF, QtF = lin_eq(aF, bF, cF - dF * tF, dF)
    burden = PcF - PF
    assert (PcF, QtF) == (33, 108)
    q("tax-incidence", "L4", stemF + f"**Q.** The government levies a specific tax of ₹{tF} per unit on sellers. The part of the tax borne by consumers is:",
      f"₹{n(burden)} per unit ({pct(burden/tF,0)})",
      [(f"₹{n(tF-burden)} per unit ({pct((tF-burden)/tF,0)})", "consumers' and producers' shares interchanged"),
       (f"₹{tF} per unit (100%)", "statutory incidence assumed to be the economic incidence"),
       (f"₹{n(tF/2)} per unit (50%)", "equal split assumed")],
      ["Qs = −60 + 6(P − 5) ⇒ 240 − 4P = −90 + 6P ⇒ P = 33", f"Consumers pay 33 vs 30 ⇒ ₹{n(burden)}; sellers get 28 ⇒ ₹{n(tF-burden)}",
       "Shares follow slopes: 6/(4+6) = 60% on buyers."],
      "Buyer share = supply slope ÷ (demand slope + supply slope) in Q-on-P form", "The flatter (more responsive) supply pushes the burden onto buyers.",
      kind="case", group=GF)
    dcsF = burden * (QF + QtF) / 2
    q("consumer-surplus", "L4", stemF + f"**Q.** Because of the ₹{tF} tax, consumer surplus falls by (₹ thousand):",
      f"₹{inr(dcsF)} thousand",
      [(f"₹{inr(burden*QF)} thousand", "price rise × original quantity"),
       (f"₹{inr(burden*QtF)} thousand", "price rise × post-tax quantity (triangle omitted)"),
       (f"₹{inr(tF*(QF+QtF)/2)} thousand", "full tax used instead of the consumers' price rise")],
      [f"ΔP to consumers = ₹{n(burden)}", f"ΔCS = ½ × ({n(QF)} + {n(QtF)}) × {n(burden)} = {inr(dcsF)}"],
      "ΔCS = ½(Q₀ + Q₁) × ΔP_c", "Only the consumer-side price change matters for CS.", kind="case", group=GF)
    ceil = 25
    qd_c, qs_c = aF - bF * ceil, cF + dF * ceil
    q("law-of-supply", "L4", stemF + f"**Q.** Instead of the tax, the government fixes a maximum price of ₹{ceil}. The resulting shortage is (thousand units):",
      f"{n(qd_c-qs_c)}",
      [(f"{n(qd_c-QF)}", "measured from equilibrium quantity to quantity demanded only"),
       (f"{n(QF-qs_c)}", "measured from equilibrium quantity to quantity supplied only"),
       ("0 — a price ceiling never creates a shortage", "ceiling below equilibrium is binding")],
      [f"Qd at ₹25 = 240 − 100 = {qd_c}", f"Qs at ₹25 = −60 + 150 = {qs_c}", f"Shortage = {qd_c} − {qs_c} = {qd_c-qs_c}"],
      "Shortage = Qd(P_ceiling) − Qs(P_ceiling)", "A binding ceiling must be below the equilibrium price.", kind="case", group=GF)

    # ======================= L4 case G (monopoly) =======================
    GG = "ECO-MONO-CASE-G"
    stemG = ("**Case — Arvan Power Ltd.** Arvan is the sole electricity distributor in a region. Its demand is P = 200 − 2Q and total cost is "
             "TC = 500 + 40Q (Q in lakh units, P in ₹ per unit; money figures in ₹ lakh).\n\n")
    Qg = (200 - 40) / 4; Pg = 200 - 2 * Qg; prof = Pg * Qg - 500 - 40 * Qg
    Qr_ = 50; Pr_ = 100; profr = Pr_ * Qr_ - 500 - 40 * Qr_
    assert (Qg, Pg, prof, profr) == (40, 120, 2700, 2500)
    trip = lambda Q, P, pr: f"Q = {n(Q)}, P = ₹{n(P)}, profit = {'−' if pr < 0 else ''}₹{inr(abs(pr))} lakh"
    q("monopoly", "L4", stemG + "**Q.** Arvan's profit-maximising output, price and profit are:",
      trip(Qg, Pg, prof),
      [(trip(80, 40, -500), "P = MC (competitive) rule applied"),
       (trip(Qr_, Pr_, profr), "revenue maximised (MR = 0)"),
       (trip(Qg, Pg, prof + 500), "fixed cost ignored in profit")],
      ["MR = 200 − 4Q = MC = 40 ⇒ Q = 40", "P = 200 − 80 = 120", f"Profit = 120×40 − (500 + 40×40) = {inr(prof)}"],
      "MR = MC", "Fixed cost does not change Q or P but does change profit.", kind="case", group=GG)
    Lr = (Pg - 40) / Pg
    q("monopoly", "L4", stemG + "**Q.** At Arvan's profit-maximising point, the Lerner index and the absolute price elasticity of demand are:",
      f"Lerner = {n(Lr)}; |e| = {n(1/Lr)}",
      [(f"Lerner = {n(40/Pg)}; |e| = {n(Pg/40)}", "MC/P used as the Lerner index"),
       (f"Lerner = {n(Lr)}; |e| = {n(Lr)}", "elasticity taken equal to the index, not its reciprocal"),
       (f"Lerner = {n(1/Lr)}; |e| = {n(Lr)}", "values interchanged")],
      [f"L = (120 − 40)/120 = {n(Lr)}", f"|e| = 1/L = {n(1/Lr)}; check: |e| = (1/2)×120/40 = 1.5"],
      "L = (P − MC)/P = 1/|e|", "Monopoly sits on the elastic segment (|e| > 1).", kind="case", group=GG)
    dwlG = 0.5 * (80 - Qg) * (Pg - 40)
    q("monopoly", "L4", stemG + "**Q.** The deadweight loss caused by monopoly pricing, compared with marginal-cost pricing, is:",
      f"₹{inr(dwlG)} lakh",
      [(f"₹{inr(2*dwlG)} lakh", "½ omitted"),
       (f"₹{inr(prof)} lakh", "monopoly profit reported as welfare loss"),
       (f"₹{inr(0.5*80*(200-40))} lakh", "consumer surplus under MC pricing reported")],
      ["MC pricing: 200 − 2Q = 40 ⇒ Q = 80", f"DWL = ½ × (80 − 40) × (120 − 40) = {inr(dwlG)}"],
      "DWL = ½ (Q_c − Q_m)(P_m − MC)", "Profit is a transfer, DWL is a net loss.", kind="case", group=GG)
    q("monopoly", "L4", stemG + "**Q.** The regulator orders Arvan to price at marginal cost. Arvan's profit then becomes:",
      "A loss of ₹500 lakh (equal to its fixed cost)",
      [("Zero — MC pricing always yields normal profit", "true only if there are no fixed costs"),
       (f"A loss of ₹{inr(dwlG)} lakh", "deadweight loss confused with the firm's loss"),
       (f"A profit of ₹{inr(prof)} lakh", "regulation effect ignored")],
      ["P = MC = 40 ⇒ Q = 80", "TR = 3,200; TC = 500 + 3,200 = 3,700 ⇒ loss 500"],
      "With AC > MC (fixed cost), MC pricing produces a loss", "Why regulators use average-cost pricing or subsidies for natural monopolies.",
      kind="case", group=GG)
