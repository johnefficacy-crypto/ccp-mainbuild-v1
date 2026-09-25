"""REG-CORPUS pilot: Costing -> Marginal costing / CVP. 20 original questions.
Every numeric key and distractor is computed here; asserts guard the key.
Distractors = named errors, not random numbers.
Run: python build_costing_pilot.py  -> reg_costing_marginal_pilot.json + review sheet .md
"""
import json, random

def inr(n, dec=0):
    neg = n < 0
    n = abs(n)
    if dec:
        whole, frac = f"{n:.{dec}f}".split(".")
    else:
        whole, frac = str(int(round(n))), None
    if len(whole) > 3:
        last3, rest = whole[-3:], whole[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:]); rest = rest[:-2]
        if rest: groups.insert(0, rest)
        whole = ",".join(groups + [last3])
    s = whole + (f".{frac}" if frac else "")
    return ("-" if neg else "") + s

def R(n): return f"₹{inr(n)}"
def pct(x, d=2): return f"{x*100:.{d}f}%".replace(".00%", "%")

Q = []
KEYPOS = [0,1,2,3]*5
random.Random("CST-MC-KEYS").shuffle(KEYPOS)  # balanced: 5 per label
def add(qid, level, micro, stem, correct, wrongs, steps, formula, trap, group=None, kind="numerical"):
    """wrongs: list of (text, error_label)"""
    texts = [correct] + [w[0] for w in wrongs]
    assert len(set(texts)) == len(texts), f"{qid}: duplicate option {texts}"
    assert len(wrongs) == 3, qid
    opts = [{"text": correct, "is_correct": True, "error": None}] + \
           [{"text": t, "is_correct": False, "error": e} for t, e in wrongs]
    wrong = opts[1:]; random.Random(qid).shuffle(wrong)
    pos = KEYPOS[len(Q)]
    opts = wrong[:pos] + [opts[0]] + wrong[pos:]
    for i, o in enumerate(opts): o["label"] = "ABCD"[i]
    Q.append({
        "id": qid, "subject": "costing", "topic_hint": "Marginal costing and CVP analysis",
        "microtopic_hint": micro, "rubric_level": level,
        "difficulty": {"L1": "easy", "L2": "medium", "L3": "hard", "L4": "hard"}[level],
        "question_kind": kind, "stimulus_group": group, "stem": stem, "options": opts,
        "correct_label": next(o["label"] for o in opts if o["is_correct"]),
        "explanation": {"steps": steps, "formula_used": formula, "trap": trap},
        "exams": ["sebi", "pfrda", "ifsca"],
        "source_kind": "authored", "provenance": "ai_drafted",
        "source_refs": [{"type": "pattern_only",
                         "note": "Standard marginal costing/CVP pattern (ICAI/ICMAI cost accounting syllabus). Original figures and entities; no text reproduced."}],
        "review_status": "draft",
    })

# ---------------- L1 ----------------
add("CST-MC-001", "L1", "Treatment of fixed overhead under marginal costing",
    "Under marginal costing, fixed production overhead incurred during a period is:",
    "Charged in full to the profit and loss account of that period",
    [("Included in the cost of closing inventory on normal capacity", "absorption-costing treatment"),
     ("Apportioned to units produced on actual capacity", "absorption on actual basis"),
     ("Carried forward and charged when the goods are sold", "confuses deferral with product cost")],
    ["Marginal costing treats only variable costs as product costs.",
     "Fixed production overhead is a period cost: written off in full against contribution of the period.",
     "Inventory is therefore valued at variable (marginal) cost only."],
    "Profit = Contribution − Fixed cost", "Absorption costing is the one that carries fixed overhead into inventory.",
    kind="conceptual")

sp, vc = 80, 52
pv = (sp - vc) / sp
add("CST-MC-002", "L1", "P/V ratio",
    f"A product sells at ₹{sp} per unit with a variable cost of ₹{vc} per unit. Its P/V ratio is:",
    pct(pv),
    [(pct(vc / sp), "variable cost ratio taken as P/V"),
     (f"{(sp-vc)/vc*100:.2f}%", "contribution divided by variable cost"),
     (f"{(sp-vc)/sp*100*0.8:.0f}%" if False else "28%", "absolute contribution ₹28 read as a percentage")],
    [f"Contribution per unit = {sp} − {vc} = ₹{sp-vc}",
     f"P/V ratio = {sp-vc} ÷ {sp} = {pct(pv)}"],
    "P/V ratio = Contribution ÷ Sales", "Divide by selling price, never by variable cost.")

fc, sp, vc = 420000, 150, 90
bep = fc / (sp - vc)
add("CST-MC-003", "L1", "Break-even point in units",
    f"Fixed costs are {R(fc)}, selling price ₹{sp} and variable cost ₹{vc} per unit. Break-even point in units is:",
    f"{inr(bep)} units",
    [(f"{inr(fc/sp)} units", "fixed cost divided by selling price"),
     (f"{inr(fc/vc)} units", "fixed cost divided by variable cost"),
     (f"{inr(fc/(sp+vc))} units", "divided by (SP + VC) instead of (SP − VC)")],
    [f"Contribution per unit = {sp} − {vc} = ₹{sp-vc}",
     f"BEP = {inr(fc)} ÷ {sp-vc} = {inr(bep)} units"],
    "BEP (units) = Fixed cost ÷ Contribution per unit", "Denominator is contribution, not price.")

actual, be = 50000, 35000
add("CST-MC-004", "L1", "Margin of safety",
    f"Actual sales are {inr(actual)} units and break-even sales are {inr(be)} units. The margin of safety ratio is:",
    pct((actual - be) / actual),
    [(pct(be / actual), "BEP as a share of sales, not the excess"),
     (f"{(actual-be)/be*100:.2f}%", "margin of safety divided by BEP instead of actual sales"),
     (pct((actual - be) / (actual + be)), "divided by (actual + BEP)")],
    [f"Margin of safety = {inr(actual)} − {inr(be)} = {inr(actual-be)} units",
     f"MOS ratio = {inr(actual-be)} ÷ {inr(actual)} = {pct((actual-be)/actual)}"],
    "MOS ratio = (Actual sales − BEP sales) ÷ Actual sales", "The base is actual sales.")

# ---------------- L2 ----------------
s1, p1, s2, p2 = 200000, 20000, 260000, 38000
pv = (p2 - p1) / (s2 - s1)
fc = s1 * pv - p1
assert abs(fc - (s2 * pv - p2)) < 1e-6
add("CST-MC-005", "L2", "P/V ratio from two periods",
    f"A firm reports:\n\n| Period | Sales (₹) | Profit (₹) |\n|---|---:|---:|\n| I | {inr(s1)} | {inr(p1)} |\n| II | {inr(s2)} | {inr(p2)} |\n\nAssuming no change in selling price, variable cost ratio or fixed cost, the fixed cost is:",
    R(fc),
    [(R(s1 * pv + p1), "profit added to contribution instead of subtracted"),
     (R(s1 * pv), "Period I contribution reported as fixed cost"),
     (R(p2 - p1), "change in profit reported as fixed cost")],
    [f"P/V = change in profit ÷ change in sales = {inr(p2-p1)} ÷ {inr(s2-s1)} = {pct(pv)}",
     f"Contribution (Period I) = {inr(s1)} × {pct(pv)} = {inr(s1*pv)}",
     f"Fixed cost = Contribution − Profit = {inr(s1*pv)} − {inr(p1)} = {inr(fc)}"],
    "P/V = ΔProfit ÷ ΔSales; FC = Contribution − Profit", "Profit is subtracted from contribution to get fixed cost.")

fc, pv, tp = 360000, 0.40, 120000
add("CST-MC-006", "L2", "Sales for target profit",
    f"Fixed costs are {R(fc)} and the P/V ratio is {pct(pv)}. Sales required to earn a profit of {R(tp)} are:",
    R((fc + tp) / pv),
    [(R(fc / pv), "break-even sales; target profit ignored"),
     (R((fc + tp) / (1 - pv)), "divided by variable cost ratio"),
     (R(fc / pv + tp), "profit added to BEP sales without grossing up")],
    [f"Required contribution = {inr(fc)} + {inr(tp)} = {inr(fc+tp)}",
     f"Sales = {inr(fc+tp)} ÷ {pct(pv)} = {inr((fc+tp)/pv)}"],
    "Required sales = (FC + Target profit) ÷ P/V", "Target profit must be grossed up by the P/V ratio too.")

prod, sold, foh = 12000, 10000, 240000
rate = foh / prod
diff = (prod - sold) * rate
add("CST-MC-007", "L2", "Marginal vs absorption profit reconciliation",
    f"No opening stock. Production {inr(prod)} units, sales {inr(sold)} units. Fixed production overhead {R(foh)}, absorbed on actual production. Compared with marginal costing, profit under absorption costing is:",
    f"Higher by {R(diff)}",
    [(f"Lower by {R(diff)}", "direction reversed"),
     (f"Higher by {R((prod-sold)*foh/sold)}", "overhead rate computed on units sold"),
     ("The same under both methods", "ignores fixed overhead carried in closing stock")],
    [f"Absorption rate = {inr(foh)} ÷ {inr(prod)} = ₹{rate:.0f} per unit",
     f"Closing stock = {inr(prod-sold)} units carries {inr(prod-sold)} × {rate:.0f} = {inr(diff)} of fixed overhead",
     "That amount is deferred under absorption costing, so absorption profit is higher by it."],
    "Profit difference = Fixed OH in closing stock − Fixed OH in opening stock",
    "When production exceeds sales, absorption profit is higher.")

profit, pv, sales = 90000, 0.30, 1000000
mos = profit / pv
add("CST-MC-008", "L2", "Margin of safety from profit and P/V",
    f"Sales are {R(sales)}, profit {R(profit)} and the P/V ratio {pct(pv)}. The margin of safety ratio is:",
    pct(mos / sales),
    [(pct(profit / sales), "profit-to-sales ratio taken as MOS"),
     (pct(1 - mos / sales), "BEP ratio reported instead of MOS"),
     (pct(profit * pv / sales), "profit multiplied by P/V instead of divided")],
    [f"MOS (₹) = Profit ÷ P/V = {inr(profit)} ÷ {pct(pv)} = {inr(mos)}",
     f"MOS ratio = {inr(mos)} ÷ {inr(sales)} = {pct(mos/sales)}"],
    "Profit = MOS × P/V", "MOS ratio × P/V ratio = Profit ÷ Sales.")

sp, vc, fc, q = 100, 60, 400000, 15000
profit = q * (sp - vc) - fc
nsp = sp * 0.9
need = (profit + fc) / (nsp - vc)
add("CST-MC-009", "L2", "Effect of price change on volume",
    f"Selling price ₹{sp}, variable cost ₹{vc} per unit, fixed cost {R(fc)}, current sales {inr(q)} units. If price is cut by 10%, units needed to keep the present profit are:",
    f"{inr(need)} units",
    [(f"{inr(q*1.1)} units", "volume raised by the same 10% as the price cut"),
     (f"{inr(fc/(nsp-vc))} units", "new break-even point; present profit ignored"),
     (f"{inr((profit+fc)/(nsp-vc*0.9))} units", "variable cost also cut by 10%")],
    [f"Present profit = {inr(q)} × {sp-vc} − {inr(fc)} = {inr(profit)}",
     f"New contribution per unit = {nsp:.0f} − {vc} = ₹{nsp-vc:.0f}",
     f"Units = ({inr(fc)} + {inr(profit)}) ÷ {nsp-vc:.0f} = {inr(need)}"],
    "Units = (FC + Target profit) ÷ New contribution per unit",
    "A 10% price cut lowered unit contribution by 25% here, so volume must rise by a third.")

prods = {"A": (60, 4), "B": (45, 2), "C": (80, 5)}
by_hr = sorted(prods, key=lambda k: -prods[k][0] / prods[k][1])
by_unit = sorted(prods, key=lambda k: -prods[k][0])
tbl = "| Product | Contribution per unit (₹) | Machine hours per unit |\n|---|---:|---:|\n" + \
      "\n".join(f"| {k} | {v[0]} | {v[1]} |" for k, v in prods.items())
add("CST-MC-010", "L2", "Key factor ranking",
    f"Machine hours are the limiting factor.\n\n{tbl}\n\nThe order of priority for production is:",
    ", ".join(by_hr),
    [(", ".join(by_unit), "ranked by contribution per unit"),
     (", ".join(sorted(prods, key=lambda k: prods[k][1])), "ranked by fewest hours per unit"),
     (", ".join(reversed(by_hr)), "ranking reversed")],
    [f"Contribution per hour: " + "; ".join(f"{k} = {v[0]}/{v[1]} = ₹{v[0]/v[1]:g}" for k, v in prods.items()),
     f"Rank highest first: {', '.join(by_hr)}"],
    "Rank by contribution per unit of the key factor", "Contribution per unit is irrelevant once a resource binds.")
assert by_hr != by_unit

# ---------------- L3 ----------------
dem = {"A": 5000, "B": 3000, "C": 2000}
hours, fc = 20000, 150000
def mix(order, cap=True):
    h, c = hours, 0
    for k in order:
        u = min(dem[k] if cap else 10**9, h // prods[k][1]); h -= u * prods[k][1]; c += u * prods[k][0]
    return c
opt = mix(by_hr)
tbl2 = "| Product | Contribution/unit (₹) | Hours/unit | Max demand (units) |\n|---|---:|---:|---:|\n" + \
       "\n".join(f"| {k} | {prods[k][0]} | {prods[k][1]} | {inr(dem[k])} |" for k in prods)
add("CST-MC-011", "L3", "Optimal product mix under a limiting factor",
    f"Available machine hours are {inr(hours)}; fixed cost {R(fc)}.\n\n{tbl2}\n\nMaximum profit is:",
    R(opt - fc),
    [(R(mix(by_unit) - fc), "mix ranked by contribution per unit"),
     (R(mix(by_hr, cap=False) - fc), "demand ceiling ignored for the top-ranked product"),
     (R(opt), "total contribution reported; fixed cost not deducted")],
    [f"Rank by contribution per hour: {', '.join(by_hr)}",
     "B: 3,000 units × 2 h = 6,000 h → ₹1,35,000",
     "C: 2,000 units × 5 h = 10,000 h → ₹1,60,000",
     "A: remaining 4,000 h ÷ 4 = 1,000 units → ₹60,000",
     f"Contribution {inr(opt)} − fixed cost {inr(fc)} = {inr(opt-fc)}"],
    "Allocate the key factor in rank order, capped by demand", "Respect demand limits before moving down the ranking.")
assert opt == 355000

cap, cur, sp, vc = 50000, 40000, 50, 30
so_q, so_p, xfc = 12000, 38, 20000
lost = cur + so_q - cap
gain = so_q * (so_p - vc) - lost * (sp - vc) - xfc
add("CST-MC-012", "L3", "Special order with capacity constraint",
    f"Capacity {inr(cap)} units; current sales {inr(cur)} units at ₹{sp}; variable cost ₹{vc} per unit. A one-time order for {inr(so_q)} units at ₹{so_p} would require an extra {R(xfc)} of fixed cost and, due to capacity, the loss of some regular sales. Net effect on profit of accepting is:",
    f"Increase of {R(gain)}",
    [(f"Increase of {R(so_q*(so_p-vc))}", "displaced sales and extra fixed cost ignored"),
     (f"Increase of {R(so_q*(so_p-vc)-xfc)}", "displaced regular sales ignored"),
     (f"Increase of {R(so_q*(so_p-vc)-lost*(sp-vc))}", "extra fixed cost ignored")],
    [f"Contribution from order = {inr(so_q)} × ({so_p} − {vc}) = {inr(so_q*(so_p-vc))}",
     f"Regular units displaced = {inr(cur)} + {inr(so_q)} − {inr(cap)} = {inr(lost)}; contribution lost = {inr(lost*(sp-vc))}",
     f"Net = {inr(so_q*(so_p-vc))} − {inr(lost*(sp-vc))} − {inr(xfc)} = {inr(gain)}"],
    "Net gain = Order contribution − Displaced contribution − Incremental fixed cost",
    "Spare capacity is only 10,000 units; the last 2,000 units displace full-price sales.")

X = (40, 24); Y = (75, 57); fc = 378000
mixc = 3 * (X[0] - X[1]) + 2 * (Y[0] - Y[1]); mixs = 3 * X[0] + 2 * Y[0]
bep_s = fc / mixc * mixs
pvx, pvy = (X[0]-X[1])/X[0], (Y[0]-Y[1])/Y[0]
add("CST-MC-013", "L3", "Composite break-even for a sales mix",
    f"Two products are sold in the ratio 3 : 2 by units.\n\n| | X | Y |\n|---|---:|---:|\n| Selling price (₹) | {X[0]} | {Y[0]} |\n| Variable cost (₹) | {X[1]} | {Y[1]} |\n\nFixed cost is {R(fc)}. Break-even sales value is:",
    R(bep_s),
    [(R(fc / ((pvx + pvy) / 2)), "simple average of the two P/V ratios"),
     (R(fc / (0.6 * pvx + 0.4 * pvy)), "3 : 2 applied as a value mix, not a unit mix"),
     (R(fc / pvy), "P/V of product Y alone")],
    [f"Contribution per mix (3X + 2Y) = 3×{X[0]-X[1]} + 2×{Y[0]-Y[1]} = ₹{mixc}",
     f"Mixes to break even = {inr(fc)} ÷ {mixc} = {inr(fc/mixc)}",
     f"Sales per mix = 3×{X[0]} + 2×{Y[0]} = ₹{mixs}",
     f"BEP sales = {inr(fc/mixc)} × {mixs} = {inr(bep_s)}"],
    "Composite BEP = FC ÷ Weighted contribution per mix", "Weights must follow the stated mix basis (units here).")

fa, va, fb, vb = 200000, 0.60, 320000, 0.45
ind = (fb - fa) / (va - vb)
add("CST-MC-014", "L3", "Cost indifference point",
    f"Plan A: fixed cost {R(fa)}, variable cost {pct(va)} of sales. Plan B: fixed cost {R(fb)}, variable cost {pct(vb)} of sales. Plan B gives the higher profit above sales of:",
    R(ind),
    [(R(fa / (1 - va)), "break-even of Plan A"),
     (R(fb / (1 - vb)), "break-even of Plan B"),
     (R((fb - fa) / vb), "divided by Plan B's variable ratio instead of the difference")],
    [f"Difference in fixed cost = {inr(fb-fa)}",
     f"Difference in variable ratio = {pct(va)} − {pct(vb)} = {pct(va-vb)}",
     f"Indifference sales = {inr(fb-fa)} ÷ {pct(va-vb)} = {inr(ind)}",
     "Above this point the lower variable-cost plan (B) earns more."],
    "Indifference point = ΔFixed cost ÷ ΔVariable cost ratio", "Not a break-even point; it compares two structures.")

fc, avoid, shut, cu = 600000, 240000, 60000, 20
sd = (fc - (fc - avoid + shut)) / cu
add("CST-MC-015", "L3", "Shut-down point",
    f"Fixed cost is {R(fc)}. If operations are suspended, {R(avoid)} of it is avoidable, but closing and reopening costs {R(shut)}. Contribution is ₹{cu} per unit. The shut-down point is:",
    f"{inr(sd)} units",
    [(f"{inr(fc/cu)} units", "break-even point"),
     (f"{inr(avoid/cu)} units", "shut-down cost ignored"),
     (f"{inr((fc-avoid+shut)/cu)} units", "cost if shut ÷ contribution")],
    [f"Cost if shut = unavoidable {inr(fc-avoid)} + shut-down {inr(shut)} = {inr(fc-avoid+shut)}",
     f"Operating is worthwhile while fixed cost − contribution < {inr(fc-avoid+shut)}",
     f"Shut-down point = ({inr(fc)} − {inr(fc-avoid+shut)}) ÷ {cu} = {inr(sd)} units"],
    "Shut-down point = (Total FC − Cost if shut) ÷ Contribution per unit",
    "Below this volume, closing loses less than operating.")

o_u, o_r, prod, foh, sold = 2000, 18, 10000, 200000, 11000
rate = foh / prod; close = o_u + prod - sold
d = close * rate - o_u * o_r
add("CST-MC-016", "L3", "Profit reconciliation with opening stock",
    f"Opening stock {inr(o_u)} units carried fixed overhead at ₹{o_r} per unit. This period: production {inr(prod)} units, fixed production overhead {R(foh)} absorbed on actual output, sales {inr(sold)} units (FIFO). Compared with absorption costing, marginal costing profit is:",
    f"Higher by {R(-d)}",
    [(f"Higher by {R(o_u*rate - close*rate)}", "opening stock revalued at the current rate"),
     (f"Lower by {R(-d)}", "direction reversed"),
     (f"Higher by {R(o_u*o_r)}", "closing stock overhead ignored")],
    [f"Current rate = {inr(foh)} ÷ {inr(prod)} = ₹{rate:.0f}",
     f"Closing stock = {inr(o_u)} + {inr(prod)} − {inr(sold)} = {inr(close)} units → {inr(close*rate)} fixed OH",
     f"Opening stock fixed OH = {inr(o_u)} × {o_r} = {inr(o_u*o_r)}",
     f"Absorption − Marginal = {inr(close*rate)} − {inr(o_u*o_r)} = −{inr(-d)}, so marginal is higher"],
    "Difference = Fixed OH in closing stock − Fixed OH in opening stock",
    "Opening stock keeps its own (prior) rate.")
assert d < 0

# ---------------- L4 case set ----------------
P = {"Mixer": (20000, 1200, 780), "Iron": (30000, 800, 600), "Kettle": (25000, 600, 540)}
FC = 12600000
sales = {k: u * s for k, (u, s, v) in P.items()}
cont = {k: u * (s - v) for k, (u, s, v) in P.items()}
TS, TC = sum(sales.values()), sum(cont.values())
alloc = {k: FC * sales[k] / TS for k in P}
profit = TC - FC
L = lambda x: f"₹{x/1e5:,.2f} lakh"
stim = ("**Case — Vardhan Home Appliances Ltd (fictional)**\n\nAnnual data:\n\n"
        "| | Mixer | Iron | Kettle |\n|---|---:|---:|---:|\n"
        f"| Units sold | {' | '.join(inr(P[k][0]) for k in P)} |\n"
        f"| Selling price per unit (₹) | {' | '.join(inr(P[k][1]) for k in P)} |\n"
        f"| Variable cost per unit (₹) | {' | '.join(inr(P[k][2]) for k in P)} |\n\n"
        f"Total fixed cost of {R(FC)} is apportioned to products in proportion to sales value. "
        "On this basis the Kettle shows a loss.")
G = "CST-MC-CASE-1"

sp_k = 900000
new_p = profit - cont["Kettle"] + sp_k
add("CST-MC-017", "L4", "Discontinuing a product line", stim +
    f"\n\nIf the Kettle is discontinued, only {R(sp_k)} of its apportioned fixed cost is saved (specific supervision). Company profit after discontinuing will be:",
    L(new_p),
    [(L(profit - (cont['Kettle'] - alloc['Kettle'])), "apportioned 'loss' of Kettle simply removed"),
     (L(profit - cont["Kettle"]), "specific fixed cost saving ignored"),
     (L(profit + sp_k), "saving added but Kettle contribution not given up")],
    [f"Present profit = total contribution {inr(TC)} − fixed cost {inr(FC)} = {inr(profit)}",
     f"Kettle contribution lost = {inr(cont['Kettle'])}; specific cost saved = {inr(sp_k)}",
     f"New profit = {inr(profit)} − {inr(cont['Kettle'])} + {inr(sp_k)} = {inr(new_p)}"],
    "Decision = Contribution forgone vs avoidable fixed cost",
    "Apportioned fixed cost is not saved by dropping a product.", group=G)

wpv = TC / TS
bep = FC / wpv
s_ex = TS - sales["Kettle"]; c_ex = TC - cont["Kettle"]
add("CST-MC-018", "L4", "Break-even for a multi-product firm", stim +
    "\n\nAt the present sales mix, the company's break-even sales value is:",
    L(bep),
    [(L(FC / (cont['Iron'] / sales['Iron'])), "P/V of one product (Iron) used for the whole firm"),
     (L(FC / (sum(cont[k]/sales[k] for k in P) / 3)), "simple average of product P/V ratios"),
     (L(FC / (c_ex / s_ex)), "Kettle excluded from the mix")],
    [f"Total sales = {inr(TS)}; total contribution = {inr(TC)}",
     f"Weighted P/V = {inr(TC)} ÷ {inr(TS)} = {wpv*100:.4f}%",
     f"BEP = {inr(FC)} ÷ {wpv:.6f} = {L(bep)}"],
    "BEP sales = FC ÷ Weighted P/V ratio", "Weight P/V by sales value, not equally.", group=G)

mosr = (TS - bep) / TS
add("CST-MC-019", "L4", "Margin of safety — multi-product", stim +
    "\n\nThe margin of safety ratio at the present sales mix is:",
    pct(mosr),
    [(pct((TS - FC / (cont['Iron']/sales['Iron'])) / TS), "BEP taken from Iron's P/V"),
     (pct(profit / TS), "profit-to-sales ratio"),
     (pct(1 - mosr), "BEP ratio reported instead of MOS")],
    [f"BEP = {L(bep)} (weighted P/V)",
     f"MOS ratio = ({inr(TS)} − {inr(bep)}) ÷ {inr(TS)} = {pct(mosr)}",
     f"Check: MOS ratio × P/V = {pct(mosr)} × {wpv*100:.2f}% ≈ profit/sales {pct(profit/TS)}"],
    "MOS ratio = (Sales − BEP) ÷ Sales", "Close options: the Iron-P/V error shifts MOS by under one point.", group=G)

tq, tsp, tvc, txf = 20000, 700, 520, 1200000
t_net = tq * (tsp - tvc) - txf
k_net = cont["Kettle"] - sp_k
chg = t_net - k_net
add("CST-MC-020", "L4", "Product replacement decision", stim +
    f"\n\nManagement proposes replacing the Kettle with a Toaster on the same capacity: {inr(tq)} units at ₹{tsp}, variable cost ₹{tvc}, and new specific fixed cost of {R(txf)}. The Kettle's specific cost of {R(sp_k)} would be saved. The change in company profit is:",
    f"Increase of {L(chg)}",
    [(f"Increase of {L(tq*(tsp-tvc) - cont['Kettle'])}", "both specific fixed costs ignored"),
     (f"Increase of {L(t_net - cont['Kettle'])}", "Kettle's specific cost saving ignored"),
     (f"Increase of {L(t_net + sp_k)}", "Kettle contribution forgone ignored")],
    [f"Toaster: {inr(tq)} × {tsp-tvc} − {inr(txf)} = {inr(t_net)}",
     f"Kettle given up: contribution {inr(cont['Kettle'])} − specific cost {inr(sp_k)} = {inr(k_net)}",
     f"Change = {inr(t_net)} − {inr(k_net)} = +{inr(chg)}"],
    "Incremental profit = New net contribution − Net contribution given up",
    "Compare specific (avoidable) figures on both sides; ignore apportioned cost.", group=G)

# ---------------- checks + output ----------------
assert len(Q) == 20
from collections import Counter
assert Counter(q["rubric_level"] for q in Q) == {"L1": 4, "L2": 6, "L3": 6, "L4": 4}
kp = Counter(q["correct_label"] for q in Q); print("key positions:", kp)
assert set(kp.values()) == {5}
json.dump({"batch": "REG-CORPUS-PILOT-COSTING-MC", "count": len(Q), "questions": Q},
          open("reg_costing_marginal_pilot.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

md = ["# Costing pilot — Marginal costing / CVP (20 Q) — SME review sheet\n",
      "Status: `ai_drafted`, `draft`. Check each key, stem clarity, and that every distractor is a plausible named error.\n"]
last_group = None
for q in Q:
    md.append(f"\n---\n\n## {q['id']} · {q['rubric_level']} · {q['difficulty']} · {q['microtopic_hint']}\n")
    md.append(q["stem"] + "\n")
    for o in q["options"]:
        tag = " ✅" if o["is_correct"] else f"  _(error: {o['error']})_"
        md.append(f"- **{o['label']}.** {o['text']}{tag}")
    md.append("\n**Working**\n")
    md += [f"{i+1}. {s}" for i, s in enumerate(q["explanation"]["steps"])]
    md.append(f"\n**Formula:** {q['explanation']['formula_used']}  \n**Trap:** {q['explanation']['trap']}")
    md.append("\n**Reviewer:** ☐ key ok ☐ stem ok ☐ distractors ok ☐ level ok — notes:\n")
open("reg_costing_marginal_pilot_review.md", "w", encoding="utf-8").write("\n".join(md))
print("wrote", len(Q), "questions")
