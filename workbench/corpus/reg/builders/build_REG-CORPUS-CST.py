"""REG-CORPUS-CST: Costing (excluding the marginal-costing/CVP pilot microtopics). 80 original questions.
Every numeric key and distractor is computed here; asserts guard hand-checked keys.
Run: python builders/build_REG-CORPUS-CST.py
"""
import os as _os; _REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, _REG)
from reglib import Batch, inr, R, pct, lakh, crore
from math import sqrt, isclose

B = Batch("REG-CORPUS-CST", subject="costing", prefix="CST")
S = lambda k: {
    "5s": "cost-5s-and-the-sixth-s-12ee6222",
    "pareto": "cost-abc-and-pareto-analysis-for-inventory-control-e0bc1f51",
    "abc": "cost-activity-based-costing-cost-pools-and-drivers-7317fd62",
    "batch": "cost-batch-costing-and-economic-batch-quantity-3984e50e",
    "budget": "cost-budget-concept-and-budgetary-control-617c62f3",
    "cash": "cost-cash-budget-preparation-879c8489",
    "cell": "cost-cellular-manufacturing-one-piece-flow-cf3a35ef",
    "contract": "cost-contract-costing-wip-retention-profit-on-incomplete-contract-102b6dcd",
    "cvf": "cost-cost-accounting-vs-financial-accounting-2f4381c6",
    "behav": "cost-cost-classification-by-behaviour-fixed-variable-semi-variabl-e25ab568",
    "concepts": "cost-cost-concepts-prime-production-conversion-cost-adcadb60",
    "ctrl": "cost-cost-control-vs-cost-reduction-539c755e",
    "direct": "cost-direct-vs-indirect-costs-6ceb3aa3",
    "disposal": "cost-disposal-of-variances-05e3c04b",
    "eoq": "cost-economic-order-quantity-and-ordering-carrying-trade-off-e36a354f",
    "equiv": "cost-equivalent-production-fifo-and-weighted-average-bcff4541",
    "flex": "cost-fixed-vs-flexible-budgets-abb5d990",
    "idle": "cost-idle-time-and-overtime-normal-vs-abnormal-treatment-08bfcf6d",
    "imputed": "cost-imputed-and-notional-costs-dc36d546",
    "interproc": "cost-inter-process-profit-1b0952cf",
    "intro": "cost-introduction-to-cost-and-management-accounting-a93049ae",
    "lean": "cost-introduction-to-lean-system-and-the-wastes-688e6065",
    "job": "cost-job-costing-ae284897",
    "joint": "cost-joint-products-and-by-products-apportionment-bases-a6a74b59",
    "jit": "cost-just-in-time-and-pull-systems-f89f17ff",
    "kanban": "cost-kanban-3f102146",
    "kaizen": "cost-kaizen-and-kaizen-costing-af2ced2a",
    "lto": "cost-labour-turnover-causes-and-measurement-d4cb4ea3",
    "labvar": "cost-labour-variances-rate-and-efficiency-71d9cffe",
    "mrp": "cost-mrp-ii-f6fb71bc",
    "matval": "cost-material-valuation-fifo-and-moving-average-b84d56ab",
    "matvar": "cost-material-variances-price-usage-mix-yield-a9f55959",
    "obj": "cost-objectives-and-scope-of-cost-and-management-accounting-2711c3c3",
    "service": "cost-operating-service-sector-costing-transport-hotel-healthcare-ad2bb07c",
    "ohabs": "cost-overhead-absorption-bases-and-rates-65feb5ec",
    "ohvar": "cost-overhead-variances-variable-and-fixed-f30f7130",
    "process": "cost-process-costing-normal-loss-abnormal-loss-abnormal-gain-18c2fe41",
    "bpr": "cost-process-innovation-and-business-process-re-engineering-b894f4ac",
    "role": "cost-role-of-the-management-accountant-bb3480a3",
    "salesvar": "cost-sales-variances-price-volume-mix-cc222e43",
    "single": "cost-single-output-unit-costing-2222baee",
    "sigma": "cost-six-sigma-dmaic-belts-defect-level-af9d959b",
    "std": "cost-standard-costing-types-of-standards-and-ideal-standard-4097314a",
    "relevant": "cost-sunk-differential-opportunity-and-relevant-costs-52aa27f3",
    "takt": "cost-takt-time-980eeda3",
    "target": "cost-target-costing-and-life-cycle-costing-4c0e5dfb",
    "tpm": "cost-total-productive-maintenance-and-oee-a1de98b7",
    "underover": "cost-under-and-over-absorption-normal-vs-abnormal-factors-c4746f5e",
    "waste": "cost-waste-scrap-spoilage-and-defectives-treatment-8068f1c3",
    "method": "cost-method-selection-by-industry-c24f9d77",
    "zbb": "cost-zero-base-and-performance-budgeting-dfb7b882",
}[k]
Rd = lambda x: R(x, 2)
def AF(x, f="A"): return f"{R(abs(x))} ({f})"
def V(x):  # signed variance: +ve favourable
    return f"{R(abs(x))} ({'F' if x > 0 else 'A'})"
STMT = ["1 only", "2 only", "3 only", "1 and 2 only", "2 and 3 only", "1 and 3 only", "1, 2 and 3"]
AR_OPTS = {
    "both_expl": "Both A and R are true, and R is the correct explanation of A",
    "both_not": "Both A and R are true, but R is not the correct explanation of A",
    "a_true": "A is true, but R is false",
    "a_false": "A is false, but R is true",
}

# =====================================================================
# L1 — recall (16)
# =====================================================================
B.add(S("5s"), "L1",
      "In the 5S workplace-organisation system, the step called **Seiketsu** refers to:",
      "Standardise — fixing norms so that the first three S's become routine",
      [("Sort — removing items that are not needed at the workstation", "confuses Seiketsu with Seiri"),
       ("Shine — cleaning the workplace, machines and equipment daily", "confuses Seiketsu with Seiso"),
       ("Sustain — building self-discipline to keep the system alive", "confuses Seiketsu with Shitsuke")],
      ["5S = Seiri (Sort), Seiton (Set in order), Seiso (Shine), Seiketsu (Standardise), Shitsuke (Sustain).",
       "Seiketsu converts the first three S's into written standards and visual controls.",
       "Many firms add a sixth S — Safety — giving '5S + 1' or 6S."],
      "5S sequence: Sort → Set in order → Shine → Standardise → Sustain (+ Safety)",
      "Standardise (4th S) and Sustain (5th S) are the pair most often swapped.", kind="conceptual")

B.add(S("cell"), "L1",
      "Which of the following best describes **cellular manufacturing**?",
      "Grouping the different machines for a product family so units flow one piece at a time",
      [("Grouping similar machines into separate departments such as a lathe shop and a drilling shop", "describes functional (process) layout"),
       ("Producing in large batches so that set-up costs are spread over more units", "batch-and-queue logic that cells are meant to replace"),
       ("A dedicated automated line built for one product that cannot be switched to other items", "confuses a flexible cell with fixed automation")],
      ["A cell groups dissimilar machines by product family (group technology).",
       "Work moves one piece (or small lot) at a time between adjacent stations — one-piece flow.",
       "This cuts transport, waiting and WIP compared with a functional layout."],
      "Cell = product-family layout + one-piece flow",
      "A functional layout groups SIMILAR machines; a cell groups DIFFERENT machines.", kind="conceptual")

B.add(S("cvf"), "L1",
      "Consider the following statements:\n\n1. Maintenance of cost records is mandatory for every company registered under the Companies Act, 2013.\n"
      "2. Financial accounts report on the business as a whole mainly for external users, whereas cost accounts analyse costs by product, process or department for internal use.\n"
      "3. Notional charges such as interest on owners' capital may be included in cost accounts but are not recorded in financial accounts.\n\nWhich of the statements given above is/are correct?",
      "2 and 3 only",
      [("1, 2 and 3", "treats cost records as mandatory for all companies"),
       ("1 and 2 only", "treats cost records as universal and misses notional costs"),
       ("2 only", "overlooks that notional costs belong only in cost accounts")],
      ["Statement 1 is wrong: under section 148 the Central Government prescribes cost records only for specified classes of companies (Companies (Cost Records and Audit) Rules, 2014), subject to turnover thresholds.",
       "Statement 2 is the standard scope distinction.",
       "Statement 3 is correct: notional costs (interest on own capital, rent of owned premises) are costing adjustments and cause reconciliation items."],
      "Cost records: s.148 — only notified classes of companies",
      "'Every company' is the give-away — cost records apply only to notified industries above thresholds.",
      kind="statement", verify_fact=True,
      ref="Companies Act, 2013 s.148; Companies (Cost Records and Audit) Rules, 2014 (applicability by industry/turnover).")

B.add(S("ctrl"), "L1",
      "Which statement correctly distinguishes **cost reduction** from **cost control**?",
      "Reduction lowers unit cost permanently without impairing utility; control keeps costs within standards",
      [("Cost control aims at a permanent lowering of unit cost; cost reduction aims at keeping costs within standards", "the two definitions reversed"),
       ("Cost reduction works mainly by comparing actual cost with budget and correcting deviations", "describes cost control, not reduction"),
       ("Both accept the existing standards as given; they differ only in the period covered", "misses that cost reduction challenges the standards themselves")],
      ["Cost control: set standards → compare actual → correct deviations (standards accepted).",
       "Cost reduction: questions the standards and seeks lasting savings (value analysis, redesign) without lowering quality or utility."],
      "Control = achieve the standard; Reduction = improve the standard",
      "Cost control is corrective; cost reduction is a challenge to the standard itself.", kind="conceptual")

B.add(S("direct"), "L1",
      "A factory makes several products. Which of the following is normally treated as a **direct** cost of a product?",
      "Royalty paid to a patent holder per unit of that product made",
      [("Rent of the factory building shared by all products", "indirect: shared facility cost"),
       ("Salary of the supervisor overseeing all production lines", "indirect: cannot be traced to one product economically"),
       ("Lubricants used on machines that make all products", "indirect material, not direct")],
      ["A direct cost can be traced to the cost object in an economically feasible way.",
       "Royalty per unit produced is a direct expense of that product.",
       "Rent, common supervision and lubricants are shared overheads."],
      "Direct cost = economically traceable to the cost object",
      "Lubricants are material but are indirect because they cannot be traced to a unit.", kind="conceptual")

B.add(S("imputed"), "L1",
      "Interest on the proprietor's own capital, charged in the cost accounts to compare two projects on equal terms although no cash is paid, is an example of:",
      "Imputed (notional) cost",
      [("Sunk cost", "confuses a notional charge with a past irrecoverable outlay"),
       ("Out-of-pocket cost", "out-of-pocket costs involve a current cash payment"),
       ("Differential cost", "differential cost is the change in total cost between alternatives")],
      ["Imputed costs are hypothetical costs not involving cash outlay and not recorded in financial books.",
       "Interest on own capital and rent of owned premises are classic examples.",
       "They are relevant for comparing alternatives."],
      "Imputed cost = notional charge, no cash outlay",
      "It is excluded from financial accounts, which causes a reconciliation item.", kind="conceptual")

B.add(S("intro"), "L1",
      "Which of the following is a **cost unit** rather than a cost centre?",
      "Tonne-kilometre in a road transport undertaking",
      [("The machine shop of a factory", "a location — cost centre"),
       ("The delivery-van section of a distribution company", "a department — cost centre"),
       ("The factory canteen", "a service cost centre")],
      ["A cost centre is a location, person or item of equipment for which costs are collected.",
       "A cost unit is the unit of product or service in which costs are expressed.",
       "Tonne-km is the cost unit of goods transport."],
      "Cost unit = measure of output; cost centre = where costs are collected",
      "Departments and sections are always centres, never units.", kind="conceptual")

B.add(S("lean"), "L1",
      "Match the lean waste with the example:\n\n| Waste | Example |\n|---|---|\n| P. Over-processing | 1. Polishing an internal surface that the customer never sees |\n"
      "| Q. Motion | 2. An operator walks to a distant rack for tools every cycle |\n| R. Transportation | 3. Moving WIP between two buildings for the next operation |\n"
      "| S. Over-production | 4. Making goods ahead of orders to keep machines busy |\n\nThe correct matching is:",
      "P-1, Q-2, R-3, S-4",
      [("P-1, Q-3, R-2, S-4", "motion (people) confused with transportation (material)"),
       ("P-4, Q-2, R-3, S-1", "over-processing confused with over-production"),
       ("P-2, Q-1, R-3, S-4", "over-processing confused with motion")],
      ["Over-processing: doing more than the customer values.",
       "Motion: unnecessary movement of people; Transportation: unnecessary movement of materials.",
       "Over-production: making more or earlier than required — often called the worst waste."],
      "TIMWOOD: Transport, Inventory, Motion, Waiting, Over-production, Over-processing, Defects",
      "Motion = people; Transport = materials.", kind="match")

B.add(S("jit"), "L1",
      "**Assertion (A):** Under a Just-in-Time system, a manufacturer aims to hold near-zero stocks of raw materials and work-in-progress.\n\n"
      "**Reason (R):** JIT is a push system in which production is scheduled in advance on the basis of sales forecasts.",
      AR_OPTS["a_true"],
      [(AR_OPTS["both_expl"], "accepts JIT as a push system"),
       (AR_OPTS["both_not"], "accepts R as true"),
       (AR_OPTS["a_false"], "reverses the truth values")],
      ["A is true: JIT minimises inventory by receiving/producing only when needed.",
       "R is false: JIT is a PULL system — production is triggered by actual downstream demand (e.g. Kanban).",
       "Forecast-driven scheduling (e.g. MRP) is a push system."],
      "JIT = pull; MRP = push",
      "The reason describes MRP, not JIT.", kind="assertion-reason")

B.add(S("mrp"), "L1",
      "MRP II extends MRP I principally by:",
      "Linking material plans with capacity, finance and marketing in a closed loop",
      [("Replacing sales forecasts with Kanban pull signals from downstream stations", "describes JIT, not MRP II"),
       ("Restricting planning to dependent-demand raw materials only", "describes the narrower scope of MRP I"),
       ("Computing the economic order quantity for independent-demand items", "EOQ is a stock model, not MRP II")],
      ["MRP I (material requirements planning) explodes the master schedule into material needs.",
       "MRP II (manufacturing resource planning) links this to capacity planning, shop-floor control, purchasing, finance and marketing, with feedback (closed loop).",
       "ERP later extended the idea to the whole enterprise."],
      "MRP I = materials; MRP II = all manufacturing resources; ERP = enterprise",
      "MRP II is still a push system.", kind="conceptual")

B.add(S("obj"), "L1",
      "Which of the following is **not** an objective of cost accounting?",
      "Preparation of the statutory balance sheet for shareholders",
      [("Ascertainment of cost per unit of product or service", "a core objective"),
       ("Control of costs through standards and budgets", "a core objective"),
       ("Supplying cost data for pricing and make-or-buy decisions", "a core objective")],
      ["Cost accounting aims at ascertainment, control and reduction of cost and at supporting decisions.",
       "The statutory balance sheet is a financial-accounting output."],
      "Objectives: ascertain, control, reduce, decide",
      "Statutory reporting belongs to financial accounting.", kind="conceptual")

B.add(S("bpr"), "L1",
      "Business Process Re-engineering (BPR), as distinguished from Kaizen, involves:",
      "Radical redesign of processes to achieve dramatic gains in cost, quality and speed",
      [("Continuous, small, incremental improvements suggested by shop-floor teams", "describes Kaizen"),
       ("Automating existing processes without changing their design", "automating a bad process is not re-engineering"),
       ("Cutting headcount by a uniform percentage in every department", "across-the-board cuts are not process redesign")],
      ["BPR (Hammer and Champy) starts from a clean sheet and redesigns around outcomes.",
       "Kaizen is gradual and continuous; BPR is radical and discontinuous."],
      "BPR = radical redesign; Kaizen = incremental improvement",
      "Automation of an unchanged process is the classic BPR anti-pattern.", kind="conceptual")

B.add(S("role"), "L1",
      "Consider the following statements about the role of a management accountant:\n\n1. Provides information for planning, control and decision making.\n"
      "2. Acts as a business partner in formulating and implementing strategy.\n3. Is primarily responsible for the statutory audit of the company's financial statements.\n\nWhich of the statements given above is/are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "treats statutory audit as a management-accounting function"),
       ("1 only", "ignores the strategic business-partner role"),
       ("2 and 3 only", "drops the core information role and adds audit")],
      ["Management accountants inform planning, control and decisions (statement 1).",
       "Modern practice sees them as business partners in strategy (statement 2).",
       "Statutory audit is performed by an independent external auditor, not the management accountant."],
      "Role: inform + partner; not audit",
      "Independence rules out the management accountant as statutory auditor.", kind="statement")

B.add(S("std"), "L1",
      "A standard that assumes no machine breakdowns, no idle time and maximum possible efficiency is known as:",
      "Ideal standard",
      [("Basic standard", "basic standard is a long-term base left unchanged for trend comparison"),
       ("Attainable (expected) standard", "attainable standard allows for normal losses and idle time"),
       ("Current standard", "current standard reflects conditions expected in the current period")],
      ["Ideal standard = perfect conditions; usually produces adverse variances and may demotivate.",
       "Attainable standard is generally recommended for control and motivation."],
      "Ideal = perfection; Attainable = efficient but achievable",
      "Ideal standards are useful as goals but poor for performance evaluation.", kind="conceptual")

B.add(S("method"), "L1",
      "Match the industry with the most suitable costing method:\n\n| Industry | Method |\n|---|---|\n| P. Oil refinery | 1. Process costing |\n"
      "| Q. Shipbuilding | 2. Contract costing |\n| R. Printing press | 3. Job costing |\n| S. City bus service | 4. Operating costing |\n\nThe correct matching is:",
      "P-1, Q-2, R-3, S-4",
      [("P-1, Q-3, R-2, S-4", "job and contract costing swapped"),
       ("P-3, Q-2, R-1, S-4", "printing (customer jobs) treated as continuous process"),
       ("P-4, Q-2, R-3, S-1", "refinery and transport methods swapped")],
      ["Refinery: continuous, homogeneous output through sequential processes.",
       "Shipbuilding: long-duration, site-based contract.",
       "Printing: each order is a separate job to customer specification.",
       "Bus service: operating (service) costing per passenger-km."],
      "Match method to the nature of output",
      "Contract costing = large, long-duration jobs; job costing = short, specific orders.", kind="match")

B.add(S("zbb"), "L1",
      "Under **zero-base budgeting**, a manager is required to:",
      "Justify every activity and its cost afresh as if starting from zero, ranking decision packages",
      [("Take last year's budget as the base and adjust it for inflation and expected changes", "describes incremental budgeting"),
       ("Link budget allocations to outputs and performance measures of programmes", "describes performance budgeting"),
       ("Prepare budgets for several activity levels", "describes flexible budgeting")],
      ["ZBB requires every activity to be justified from scratch each period.",
       "Activities are packaged into decision units and ranked for funding."],
      "ZBB = no carried-forward base; decision packages ranked",
      "Performance budgeting focuses on outputs; ZBB on justification from zero.", kind="conceptual")

# =====================================================================
# L2 — one-step application (24)
# =====================================================================
pool, n_setups, batches_x, bsize = 480000, 160, 12, 600
units_x = batches_x * bsize; total_units, mh_total, mh_x = 80000, 40000, 0.8
abc_u = pool / n_setups * batches_x / units_x
assert isclose(abc_u, 5)
B.add(S("abc"), "L2",
      f"A plant's set-up cost pool is {R(pool)} for {n_setups} set-ups a year. Product X is made in {batches_x} batches of {inr(bsize)} units, each batch needing one set-up. "
      f"Total production of all products is {inr(total_units)} units using {inr(mh_total)} machine hours; X uses {mh_x} machine hour per unit. Under activity-based costing, set-up cost per unit of X is:",
      Rd(abc_u),
      [(Rd(pool / total_units), "pool spread on units produced (volume driver)"),
       (Rd(pool / mh_total * mh_x), "pool spread on machine hours"),
       (Rd(pool / units_x), "entire pool charged to X")],
      [f"Rate per set-up = {inr(pool)} ÷ {n_setups} = {R(pool/n_setups)}",
       f"X's set-up cost = {batches_x} × {inr(pool/n_setups)} = {R(pool/n_setups*batches_x)}",
       f"Per unit = {inr(pool/n_setups*batches_x)} ÷ {inr(units_x)} = {Rd(abc_u)}"],
      "Batch-level cost per unit = (Cost per set-up × Set-ups) ÷ Units", "Set-ups are batch-level: use number of set-ups, not units or hours.")

D, Sc, uc, cr = 36000, 1500, 25, 0.12
C = uc * cr
ebq = sqrt(2 * D * Sc / C)
assert isclose(ebq, 6000)
B.add(S("batch"), "L2",
      f"Annual demand for a component is {inr(D)} units. Set-up cost is {R(Sc)} per batch; the component costs ₹{uc} to make and carrying cost is {pct(cr)} per annum of cost. The economic batch quantity is:",
      f"{inr(ebq)} units",
      [(f"{inr(sqrt(D*Sc/C))} units", "factor 2 omitted from the formula"),
       (f"{inr(sqrt(2*D*Sc/uc))} units", "unit cost used as carrying cost"),
       (f"{inr(sqrt(2*(D/12)*Sc/C))} units", "monthly demand used with annual carrying cost")],
      [f"Carrying cost per unit p.a. = {pct(cr)} × ₹{uc} = ₹{C:g}",
       f"EBQ = √(2 × {inr(D)} × {inr(Sc)} ÷ {C:g}) = {inr(ebq)} units"],
      "EBQ = √(2DS ÷ C)", "Demand and carrying cost must be for the same period.")

B.add(S("budget"), "L2",
      "Consider the following statements:\n\n1. A budget is a quantitative statement, prepared before the period, of the policy to be pursued during that period.\n"
      "2. Budgetary control requires continuous comparison of actual results with budget and corrective action on variances.\n"
      "3. The principal budget factor is always sales demand.\n\nWhich of the statements given above is/are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "treats sales as the only possible key factor"),
       ("2 and 3 only", "rejects the standard definition of a budget"),
       ("1 only", "misses that budgetary control is comparison plus action")],
      ["Statements 1 and 2 are standard definitions of budget and budgetary control.",
       "Statement 3 is false: the principal (key/limiting) budget factor may be sales, materials, labour, plant capacity or finance, whichever limits activity."],
      "Principal budget factor = the factor that limits activity",
      "'Always' is wrong — the key factor is whatever binds in that period.", kind="statement")

hi_u, hi_c, lo_u, lo_c, odd_u, odd_c, est = 9000, 266000, 4000, 156000, 8000, 270000, 7500
vc = (hi_c - lo_c) / (hi_u - lo_u); fc = lo_c - lo_u * vc
vc_w = (odd_c - lo_c) / (odd_u - lo_u); fc_w = lo_c - lo_u * vc_w
assert vc == 22 and fc == 68000
B.add(S("behav"), "L2",
      f"Monthly maintenance cost of a plant:\n\n| Month | Output (units) | Cost (₹) |\n|---|---:|---:|\n| Apr | {inr(6000)} | {inr(200000)} |\n| May | {inr(lo_u)} | {inr(lo_c)} |\n"
      f"| Jun | {inr(odd_u)} | {inr(odd_c)} |\n| Jul | {inr(hi_u)} | {inr(hi_c)} |\n\nUsing the high–low method, the estimated cost at {inr(est)} units is:",
      R(fc + vc * est),
      [(R(fc_w + vc_w * est), "highest and lowest COST months used instead of activity"),
       (R(hi_c / hi_u * est), "all cost treated as variable at the high-point average"),
       (R(vc * est), "fixed element omitted")],
      [f"High and low ACTIVITY: {inr(hi_u)} and {inr(lo_u)} units",
       f"Variable cost = ({inr(hi_c)} − {inr(lo_c)}) ÷ ({inr(hi_u)} − {inr(lo_u)}) = ₹{vc:g} per unit",
       f"Fixed = {inr(lo_c)} − {inr(lo_u)} × {vc:g} = {inr(fc)}",
       f"At {inr(est)}: {inr(fc)} + {inr(est)} × {vc:g} = {inr(fc+vc*est)}"],
      "b = ΔCost ÷ ΔActivity (high/low activity); a = Cost − b × Activity",
      "Pick the high and low ACTIVITY months, not the high and low cost months (June is a trap).")

dm, dl, de, foh, adm, sell, owip, cwip = 240000, 160000, 20000, 130000, 70000, 50000, 30000, 45000
works = dm + dl + de + foh + owip - cwip
assert works == 535000
B.add(S("concepts"), "L2",
      f"From the following data, the **works (factory) cost** is:\n\n| Item | ₹ |\n|---|---:|\n| Direct materials | {inr(dm)} |\n| Direct wages | {inr(dl)} |\n| Direct expenses | {inr(de)} |\n"
      f"| Factory overheads | {inr(foh)} |\n| Administration overheads | {inr(adm)} |\n| Selling overheads | {inr(sell)} |\n| Opening WIP | {inr(owip)} |\n| Closing WIP | {inr(cwip)} |",
      R(works),
      [(R(dm + dl + de + foh - owip + cwip), "WIP adjustment reversed"),
       (R(dm + dl + de + foh), "WIP adjustment omitted"),
       (R(works + adm), "administration overhead included in works cost")],
      [f"Prime cost = {inr(dm)} + {inr(dl)} + {inr(de)} = {inr(dm+dl+de)}",
       f"Add factory OH {inr(foh)} → gross works cost {inr(dm+dl+de+foh)}",
       f"Add opening WIP {inr(owip)}, less closing WIP {inr(cwip)} → works cost {inr(works)}"],
      "Works cost = Prime cost + Factory OH + Opening WIP − Closing WIP",
      "Administration and selling overheads come after works cost.")

D, O, price, cr = 50000, 400, 50, 0.20
C = price * cr
eoq = sqrt(2 * D * O / C); tc = D / eoq * O + eoq / 2 * C
assert eoq == 2000 and tc == 20000
e2 = sqrt(D * O / C); tc2 = D / e2 * O + e2 / 2 * C
B.add(S("eoq"), "L2",
      f"Annual requirement {inr(D)} kg; ordering cost {R(O)} per order; purchase price ₹{price} per kg; carrying cost {pct(cr)} p.a. of average inventory value. "
      "The EOQ and the total annual ordering-plus-carrying cost at EOQ are:",
      f"{inr(eoq)} kg; {R(tc)}",
      [(f"{inr(eoq)} kg; {R(D/eoq*O + eoq*C)}", "carrying cost charged on the full order instead of average stock"),
       (f"{inr(e2)} kg; {R(tc2)}", "factor 2 omitted in the EOQ formula"),
       (f"{inr(eoq)} kg; {R(tc + D*price)}", "purchase cost added to the ordering/carrying total")],
      [f"C = {pct(cr)} × {price} = ₹{C:g}",
       f"EOQ = √(2 × {inr(D)} × {O} ÷ {C:g}) = {inr(eoq)} kg",
       f"Ordering = {inr(D/eoq)} orders × {O} = {inr(D/eoq*O)}; carrying = {inr(eoq/2)} × {C:g} = {inr(eoq/2*C)}",
       f"Total = {inr(tc)} (at EOQ, ordering = carrying)"],
      "EOQ = √(2AO ÷ C); carrying on average stock (Q/2)",
      "At EOQ the two costs are equal — a quick check.")

wk, hrs, rate, booked, norm = 40, 48, 150, 1720, 0.05
paid = wk * hrs; idle = paid - booked; nidle = paid * norm; ab = idle - nidle
assert ab == 104
B.add(S("idle"), "L2",
      f"A department has {wk} workers each paid for a {hrs}-hour week at ₹{rate} per hour. Time booked to jobs in the week was {inr(booked)} hours. "
      f"Normal idle time is {pct(norm)} of hours paid; the rest arose from a power failure. The amount charged to the Costing Profit and Loss Account is:",
      R(ab * rate),
      [(R(idle * rate), "entire idle time charged to Costing P&L"),
       (R(nidle * rate), "normal idle time charged to Costing P&L"),
       (R((idle - booked * norm) * rate), "normal idle time computed on hours booked, not hours paid")],
      [f"Hours paid = {wk} × {hrs} = {inr(paid)}; idle = {inr(paid)} − {inr(booked)} = {inr(idle)}",
       f"Normal idle = {pct(norm)} × {inr(paid)} = {nidle:g} h (absorbed via overhead / inflated wage rate)",
       f"Abnormal idle = {inr(idle)} − {nidle:g} = {ab:g} h × ₹{rate} = {R(ab*rate)} → Costing P&L"],
      "Abnormal idle time cost → Costing P&L; normal idle → product cost",
      "Only the abnormal portion bypasses product cost.")

dm, h, lr, ohr, admr, pm = 38000, 240, 120, 150, 0.20, 0.20
wc = dm + h * lr + h * ohr; cop = wc * (1 + admr); spj = cop / (1 - pm)
assert wc == 102800 and isclose(spj, 154200)
prime = dm + h * lr
B.add(S("job"), "L2",
      f"Job No. 47: direct materials {R(dm)}; direct labour {h} hours at ₹{lr}; factory overhead absorbed at ₹{ohr} per direct labour hour; "
      f"administration overhead {pct(admr)} of works cost. The firm prices jobs to earn a profit of {pct(pm)} on selling price. Price quoted for the job is:",
      R(spj),
      [(R(cop * (1 + pm)), "20% added on cost instead of on selling price"),
       (R((wc + prime * admr) / (1 - pm)), "administration overhead taken on prime cost"),
       (R(wc / (1 - pm)), "administration overhead omitted")],
      [f"Prime cost = {inr(dm)} + {h} × {lr} = {inr(prime)}",
       f"Works cost = {inr(prime)} + {h} × {ohr} = {inr(wc)}",
       f"Cost of production = {inr(wc)} × 1.20 = {inr(cop)}",
       f"Price = {inr(cop)} ÷ 0.80 = {inr(spj)}"],
      "Price = Total cost ÷ (1 − margin on sales)", "20% on sales = 25% on cost.")

jc, bq, bp, bsep, bsell, mq = 600000, 2000, 40, 8, 0.10, 20000
nrv = bq * bp - bq * bsep - bq * bp * bsell
cpu = (jc - nrv) / mq
assert nrv == 56000 and isclose(cpu, 27.2)
B.add(S("joint"), "L2",
      f"A joint process costing {R(jc)} yields {inr(mq)} units of main product M and {inr(bq)} kg of by-product Y. Y sells at ₹{bp} per kg after further processing of ₹{bsep} per kg; "
      f"selling expenses are {pct(bsell)} of Y's sales value. Using the net realisable value (reverse cost) method for the by-product, cost per unit of M is:",
      Rd(cpu),
      [(Rd((jc - bq * bp) / mq), "gross sales value of Y deducted"),
       (Rd((jc - (bq * bp - bq * bp * bsell)) / mq), "Y's further processing cost ignored"),
       (Rd(jc / mq), "no credit for the by-product")],
      [f"Y sales = {inr(bq*bp)}; less processing {inr(bq*bsep)} and selling {inr(bq*bp*bsell)} → NRV {inr(nrv)}",
       f"Net joint cost to M = {inr(jc)} − {inr(nrv)} = {inr(jc-nrv)}",
       f"Per unit = {inr(jc-nrv)} ÷ {inr(mq)} = {Rd(cpu)}"],
      "Main product cost = Joint cost − NRV of by-product", "Both post-separation costs reduce the credit.")

d, lt, ss, cont = 2400, 0.5, 0.25, 150
nk = d * lt * (1 + ss) / cont
assert nk == 10
B.add(S("kanban"), "L2",
      f"A work cell uses {inr(d)} parts a day. Replenishment lead time is {lt} day, the safety factor is {pct(ss)} and each container holds {cont} parts. The number of Kanban cards required is:",
      f"{nk:g}",
      [(f"{d*lt/cont:g}", "safety factor ignored"),
       (f"{d*lt*(1-ss)/cont:g}", "safety factor deducted instead of added"),
       (f"{d*(1+ss)/cont:g}", "lead time not applied (daily demand used)")],
      [f"Demand during lead time = {inr(d)} × {lt} = {inr(d*lt)}",
       f"With safety: {inr(d*lt)} × {1+ss} = {inr(d*lt*(1+ss))}",
       f"Kanbans = {inr(d*lt*(1+ss))} ÷ {cont} = {nk:g}"],
      "N = D × L × (1 + S) ÷ C", "Safety stock increases the number of cards.")

B.add(S("kaizen"), "L2",
      "Which statement best distinguishes **Kaizen costing** from **target costing**?",
      "Kaizen costing cuts costs continuously during manufacture; target costing acts at the design stage",
      [("Kaizen costing works at the design stage, whereas target costing applies during manufacturing", "stages reversed"),
       ("Kaizen costing relies on a one-time radical redesign of the production process", "describes BPR, not Kaizen"),
       ("Kaizen costing derives the allowable cost as target price less required profit margin", "describes target costing")],
      ["Target costing: allowable cost = target price − target profit, achieved through design.",
       "Kaizen costing: after launch, sets period-by-period reduction targets achieved by small improvements.",
       "Together they cover the life cycle: design (target) → production (Kaizen)."],
      "Target cost = Price − Margin (design); Kaizen = continuous reduction (production)",
      "Kaizen is incremental; radical redesign is BPR.", kind="conceptual")

op, cl, sep, repl, newh = 380, 420, 24, 18, 46
assert op - sep + repl + newh == cl
avg = (op + cl) / 2
B.add(S("lto"), "L2",
      f"Workforce data for the year: employees at start {op}, at end {cl}; separations {sep}; replacements {repl}; additional workers recruited for an expansion scheme {newh}. "
      "Labour turnover by the **replacement method** is:",
      pct(repl / avg),
      [(pct(sep / avg), "separation method used"),
       (pct((repl + newh) / avg), "expansion recruits counted as replacements"),
       (pct(repl / op), "divided by opening instead of average workforce")],
      [f"Average workforce = ({op} + {cl}) ÷ 2 = {avg:g}",
       f"Replacement rate = {repl} ÷ {avg:g} = {pct(repl/avg)}",
       "Recruitment for expansion is excluded from replacements."],
      "Replacement method = Replacements ÷ Average number of workers",
      "New posts created by expansion are not turnover.")

sh, sr, out, ah, ar = 2.5, 160, 1800, 4700, 170
std_h = sh * out; eff = (std_h - ah) * sr; ratev = (sr - ar) * ah
assert eff == -32000
B.add(S("labvar"), "L2",
      f"Standard labour: {sh} hours per unit at ₹{sr} per hour. Actual output {inr(out)} units; actual hours worked {inr(ah)} paid at ₹{ar} per hour. The labour efficiency variance is:",
      V(eff),
      [(V((std_h - ah) * ar), "valued at the actual rate"),
       (V(-eff), "direction reversed"),
       (V(ratev), "labour rate variance reported")],
      [f"Standard hours for actual output = {sh} × {inr(out)} = {inr(std_h)}",
       f"Efficiency = ({inr(std_h)} − {inr(ah)}) × {sr} = {V(eff)}"],
      "LEV = (SH − AH) × SR", "Efficiency variances are always valued at the standard rate.")

sq, sp_, out, aq, ap = 4, 60, 2500, 10600, 58
std_q = sq * out; usage = (std_q - aq) * sp_; pricev = (sp_ - ap) * aq
assert usage == -36000
B.add(S("matvar"), "L2",
      f"Standard: {sq} kg of material per unit at ₹{sp_} per kg. Actual output {inr(out)} units; material used {inr(aq)} kg costing ₹{ap} per kg. The material usage variance is:",
      V(usage),
      [(V((std_q - aq) * ap), "valued at actual price"),
       (V(-usage), "direction reversed"),
       (V(std_q * sp_ - aq * ap), "total material cost variance reported")],
      [f"Standard quantity for actual output = {sq} × {inr(out)} = {inr(std_q)} kg",
       f"Usage = ({inr(std_q)} − {inr(aq)}) × {sp_} = {V(usage)}",
       f"(Price variance = {V(pricev)}; cost variance = {V(std_q*sp_-aq*ap)})"],
      "MUV = (SQ − AQ) × SP", "Usage is priced at standard; the price effect sits in the price variance.")

seats, km, trips, days, occ, cost = 50, 40, 4, 25, 0.80, 480000
pkm = seats * occ * km * 2 * trips * days
assert pkm == 320000
B.add(S("service"), "L2",
      f"A bus with {seats} seats runs a {km} km route, making {trips} round trips a day for {days} days a month. Average occupancy is {pct(occ,0)}. Monthly operating cost is {R(cost)}. "
      "Cost per passenger-km is:",
      Rd(cost / pkm),
      [(Rd(cost / (pkm / 2)), "round trips counted as one-way trips"),
       (Rd(cost / (pkm / occ)), "occupancy ignored (full capacity assumed)"),
       (Rd(cost / (pkm / occ / occ)), "occupancy applied as a divisor instead of a multiplier")],
      [f"Distance per day = {km} × 2 × {trips} = {km*2*trips} km; per month = {km*2*trips*days:,} km",
       f"Passenger-km = {km*2*trips*days:,} × {seats} × {pct(occ,0)} = {inr(pkm)}",
       f"Cost per passenger-km = {inr(cost)} ÷ {inr(pkm)} = {Rd(cost/pkm)}"],
      "Passenger-km = Distance × Seats × Occupancy", "A round trip covers the route twice.")

mc, scrap, life, rep, stand, tot_h, maint_h, pw_u, pw_r = 1200000, 120000, 10, 54000, 90000, 2000, 200, 20, 8
dep = (mc - scrap) / life; run = tot_h - maint_h
mhr = (dep + rep + stand) / run + pw_u * pw_r
assert mhr == 300
B.add(S("ohabs"), "L2",
      f"A machine costs {R(mc)}, has a scrap value of {R(scrap)} and a life of {life} years (straight line). Repairs are {R(rep)} p.a. and its share of standing charges {R(stand)} p.a. "
      f"It is available {inr(tot_h)} hours a year, of which {maint_h} hours are for maintenance. It consumes {pw_u} units of power per running hour at ₹{pw_r} per unit. The machine hour rate is:",
      Rd(mhr),
      [(Rd((dep + rep + stand) / tot_h + pw_u * pw_r), "fixed charges spread over total instead of running hours"),
       (Rd((dep + rep + stand) / run), "power cost omitted"),
       (Rd((mc / life + rep + stand) / run + pw_u * pw_r), "scrap value not deducted in depreciation")],
      [f"Depreciation = ({inr(mc)} − {inr(scrap)}) ÷ {life} = {inr(dep)}",
       f"Fixed charges = {inr(dep)} + {inr(rep)} + {inr(stand)} = {inr(dep+rep+stand)} ÷ {run} running h = ₹{(dep+rep+stand)/run:g}",
       f"Power = {pw_u} × {pw_r} = ₹{pw_u*pw_r}; MHR = {Rd(mhr)}"],
      "MHR = Standing charges ÷ Running hours + Running cost per hour",
      "Maintenance hours are not productive hours.")

inp, ip, conv, nl, sv, outp = 5000, 30, 82000, 0.08, 5, 4500
tot = inp * ip + conv; nlu = inp * nl; exp_out = inp - nlu
cpu = (tot - nlu * sv) / exp_out; abl = exp_out - outp
assert cpu == 50 and abl == 100
B.add(S("process"), "L2",
      f"Process A: input {inr(inp)} kg at ₹{ip} per kg; labour and overheads {R(conv)}. Normal loss is {pct(nl,0)} of input, saleable as scrap at ₹{sv} per kg. Actual output {inr(outp)} kg. "
      "The value of abnormal loss credited to the process account is:",
      R(abl * cpu),
      [(R(abl * tot / exp_out), "scrap value of normal loss not deducted"),
       (R(abl * tot / inp), "cost spread over input rather than normal output"),
       (R(abl * (cpu - sv)), "net of scrap value — that is the Costing P&L charge, not the process credit")],
      [f"Normal loss = {pct(nl,0)} × {inr(inp)} = {inr(nlu)} kg → scrap {inr(nlu*sv)}",
       f"Cost per unit of normal output = ({inr(tot)} − {inr(nlu*sv)}) ÷ {inr(exp_out)} = ₹{cpu:g}",
       f"Abnormal loss = {inr(exp_out)} − {inr(outp)} = {abl} kg × {cpu:g} = {R(abl*cpu)}"],
      "Cost per unit = (Total cost − Scrap value of normal loss) ÷ Normal output",
      "Abnormal loss is valued like good output.")

rm, wg, dx, wor, offr, outq = 320000, 240000, 40000, 0.60, 0.10, 400000
wcs = rm + wg + dx + wg * wor; copv = wcs * (1 + offr)
assert isclose(copv, 818400)
B.add(S("single"), "L2",
      f"A single-product factory produced {inr(outq)} units: raw materials {R(rm)}; direct wages {R(wg)}; direct expenses {R(dx)}. "
      f"Works overhead is {pct(wor,0)} of direct wages and office overhead {pct(offr,0)} of works cost. Cost of production per 1,000 units is:",
      R(copv / outq * 1000),
      [(R((rm + wg + dx) * (1 + wor) * (1 + offr) / outq * 1000), "works overhead taken on prime cost"),
       (R((wcs + (rm + wg + dx) * offr) / outq * 1000), "office overhead taken on prime cost"),
       (R(wcs / outq * 1000), "office overhead omitted")],
      [f"Prime cost = {inr(rm+wg+dx)}; works OH = {pct(wor,0)} × {inr(wg)} = {inr(wg*wor)}",
       f"Works cost = {inr(wcs)}; office OH = {inr(wcs*offr)}; cost of production = {inr(copv)}",
       f"Per 1,000 units = {inr(copv)} ÷ {inr(outq)} × 1,000 = {R(copv/outq*1000)}"],
      "Unit cost = Cost of production ÷ Output", "Check the base given for each overhead.")

forms, opp, defects = 120000, 5, 450
dpmo = defects / (forms * opp) * 1e6
assert dpmo == 750
B.add(S("sigma"), "L2",
      f"A back-office processes {inr(forms)} application forms a month. Each form has {opp} fields where an error can occur. {defects} errors were found. The defects per million opportunities (DPMO) is:",
      inr(dpmo),
      [(inr(defects / forms * 1e6), "defects per million units — opportunities ignored"),
       (inr(defects * opp / forms * 1e6), "multiplied by opportunities instead of dividing"),
       ("3.4", "Six Sigma benchmark quoted instead of the actual DPMO")],
      [f"Opportunities = {inr(forms)} × {opp} = {inr(forms*opp)}",
       f"DPMO = {defects} ÷ {inr(forms*opp)} × 10,00,000 = {inr(dpmo)}",
       "Six Sigma performance (with the conventional 1.5σ shift) = 3.4 DPMO."],
      "DPMO = Defects ÷ (Units × Opportunities) × 10⁶", "Divide by opportunities per unit, not multiply.")

orig, wdv, sale_now, sale_after = 800000, 500000, 320000, 270000
B.add(S("relevant"), "L2",
      f"A machine bought three years ago for {R(orig)} has a written-down value of {R(wdv)}. It is idle and can be sold now for {R(sale_now)}. "
      f"If used for a special order it could be sold after the order for {R(sale_after)}. The relevant cost of using the machine for the order is:",
      R(sale_now - sale_after),
      [(R(wdv - sale_after), "written-down value (sunk) used instead of current disposal value"),
       (R(sale_now), "full current disposal value charged"),
       (R(orig - sale_after), "historical cost used")],
      [f"If the order is taken, the firm gives up {R(sale_now)} now and receives {R(sale_after)} later.",
       f"Relevant cost = {inr(sale_now)} − {inr(sale_after)} = {R(sale_now-sale_after)}",
       "Original cost and WDV are sunk."],
      "Relevant cost = Fall in realisable value (opportunity cost)", "Book values are sunk.")

shift, br, lunch, nsh, dem = 480, 2 * 15, 30, 2, 1680
avail = (shift - br - lunch) * nsh; takt = avail * 60 / dem
assert takt == 30
B.add(S("takt"), "L2",
      f"A plant works {nsh} shifts of 8 hours a day. Each shift has two 15-minute tea breaks and a 30-minute lunch break. Daily customer demand is {inr(dem)} units. Takt time is:",
      f"{takt:g} seconds",
      [(f"{shift*nsh*60/dem:.2f} seconds", "breaks not deducted from available time"),
       (f"{(shift-br-lunch)*60/dem:g} seconds", "only one shift counted"),
       (f"{(shift-lunch)*nsh*60/dem:.2f} seconds", "only the lunch break deducted")],
      [f"Available time = ({shift} − {br} − {lunch}) × {nsh} = {avail} minutes = {avail*60:,} s",
       f"Takt = {avail*60:,} ÷ {inr(dem)} = {takt:g} s per unit"],
      "Takt time = Net available time ÷ Customer demand", "Takt is driven by demand, not by machine speed.")

mp, mgn, cur = 2500, 0.20, 2150
tcst = mp * (1 - mgn)
assert tcst == 2000
B.add(S("target"), "L2",
      f"Market research shows a new appliance can sell at ₹{inr(mp)}. The company requires a profit of {pct(mgn,0)} on selling price. The current estimated cost is ₹{inr(cur)}. The cost reduction needed per unit is:",
      Rd(cur - tcst),
      [(Rd(cur - mp / (1 + mgn)), "20% treated as mark-up on cost"),
       (Rd(cur * (1 + mgn) - mp), "cost-plus price compared with market price"),
       (Rd(mp - cur), "price minus current cost taken as the gap")],
      [f"Target cost = {inr(mp)} × (1 − {mgn}) = ₹{inr(tcst)}",
       f"Cost gap = {inr(cur)} − {inr(tcst)} = ₹{inr(cur-tcst)}"],
      "Target cost = Target price − Target profit", "Start from price; profit is on sales here.")

bud_oh, bud_h, act_oh, act_h = 900000, 60000, 948000, 64000
rate = bud_oh / bud_h; absb = act_h * rate
assert absb - act_oh == 12000
B.add(S("underover"), "L2",
      f"Budgeted factory overhead {R(bud_oh)} for {inr(bud_h)} direct labour hours. Actual overhead {R(act_oh)}; actual hours {inr(act_h)}. Overhead for the period was:",
      f"Over-absorbed by {R(absb-act_oh)}",
      [(f"Under-absorbed by {R(absb-act_oh)}", "direction reversed"),
       (f"Under-absorbed by {R(act_oh-bud_oh)}", "actual compared with budgeted overhead"),
       (f"Over-absorbed by {R(absb-bud_oh)}", "absorbed compared with budgeted overhead")],
      [f"Rate = {inr(bud_oh)} ÷ {inr(bud_h)} = ₹{rate:g} per hour",
       f"Absorbed = {inr(act_h)} × {rate:g} = {inr(absb)}",
       f"Absorbed − Actual = {inr(absb)} − {inr(act_oh)} = {inr(absb-act_oh)} → over-absorbed"],
      "Under/over-absorption = Absorbed − Actual overhead", "Compare absorbed with ACTUAL, not with budget.")

B.add(S("waste"), "L2",
      "Consider the following statements:\n\n1. The realisable value of normal scrap is credited to the job or process account.\n"
      "2. The cost of abnormal spoilage is transferred to the Costing Profit and Loss Account.\n"
      "3. The cost of rectifying normal defectives that cannot be identified with particular jobs is charged to the Costing Profit and Loss Account.\n\nWhich of the statements given above is/are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "normal rectification cost treated as abnormal"),
       ("2 and 3 only", "misses normal scrap credit to the process"),
       ("2 only", "rejects the standard normal-scrap treatment")],
      ["Normal scrap: realisable value reduces the cost of the job/process (statement 1).",
       "Abnormal spoilage: charged to Costing P&L so that good units are not burdened (statement 2).",
       "Normal defectives' rectification cost not traceable to jobs is added to production overheads (spread over good output), not Costing P&L."],
      "Normal → product cost; Abnormal → Costing P&L",
      "The normal/abnormal split drives every waste treatment.", kind="statement")

# =====================================================================
# L3 — multi-step / table (24)
# =====================================================================
items = {"P": (4000, 150), "Q": (500, 1600), "R": (20000, 5), "S": (1500, 100),
         "T": (10000, 12), "U": (300, 200), "V": (25000, 2), "W": (800, 150)}
val = {k: u * c for k, (u, c) in items.items()}; TOT = sum(val.values())
by_val = sorted(items, key=lambda k: -val[k])
cum, A = 0, []
for k in by_val:
    if cum / TOT >= 0.70: break
    cum += val[k]; A.append(k)
assert A == ["Q", "P"] and cum / TOT == 0.70
by_units = sorted(items, key=lambda k: -items[k][0])[:2]
by_price = sorted(items, key=lambda k: -items[k][1])[:2]
tbl = "| Item | Annual usage (units) | Unit cost (₹) |\n|---|---:|---:|\n" + "\n".join(f"| {k} | {inr(u)} | {inr(c)} |" for k, (u, c) in items.items())
B.add(S("pareto"), "L3",
      f"A store holds eight items:\n\n{tbl}\n\nUnder ABC analysis, Category A is to cover the items that together account for about 70% of annual usage value. Category A consists of:",
      " and ".join(sorted(A)),
      [(" and ".join(sorted(by_units)), "ranked by quantity consumed"),
       (" and ".join(sorted(by_price)), "ranked by unit price"),
       (", ".join(sorted(A + [by_val[2]])[:-1]) + " and " + sorted(A + [by_val[2]])[-1], "next item added beyond the 70% cut-off")],
      ["Annual usage value = units × unit cost: " + "; ".join(f"{k} {inr(val[k])}" for k in by_val),
       f"Total = {inr(TOT)}; Q + P = {inr(cum)} = {pct(cum/TOT,0)}",
       "Category A = Q and P (2 of 8 items ≈ 25% of items, 70% of value)."],
      "Rank by usage value (quantity × price)", "Neither quantity nor price alone decides the class.")

ob_u, ob_r = 500, 40
p1, p1r, i1, p2, p2r, i2 = 1000, 46, 900, 600, 50, 800
bal_u, bal_v = ob_u + p1, ob_u * ob_r + p1 * p1r
r1 = bal_v / bal_u; bal_u -= i1; bal_v -= i1 * r1
bal_u += p2; bal_v += p2 * p2r; r2 = bal_v / bal_u; bal_u -= i2; bal_v -= i2 * r2
assert bal_u == 400 and isclose(bal_v, 18800)
fifo_close = bal_u * p2r
per_avg = (ob_u * ob_r + p1 * p1r + p2 * p2r) / (ob_u + p1 + p2) * bal_u
B.add(S("matval"), "L3",
      f"Stores ledger of a component for March:\n\n| Date | Transaction |\n|---|---|\n| 1 | Opening stock {ob_u} units @ ₹{ob_r} |\n| 5 | Purchased {inr(p1)} units @ ₹{p1r} |\n"
      f"| 10 | Issued {i1} units |\n| 15 | Purchased {p2} units @ ₹{p2r} |\n| 20 | Issued {i2} units |\n\nThe value of closing stock under the **moving (perpetual) weighted average** method is:",
      R(bal_v),
      [(R(fifo_close), "FIFO — closing stock from the latest purchase"),
       (R(per_avg), "periodic (monthly) weighted average used"),
       (R((ob_r + p1r + p2r) / 3 * bal_u), "simple average of prices")],
      [f"After 5th: {ob_u+p1} units, {inr(ob_u*ob_r+p1*p1r)} → ₹{r1:g}",
       f"Issue {i1} @ {r1:g} = {inr(i1*r1)}; balance {ob_u+p1-i1} units {inr((ob_u+p1-i1)*r1)}",
       f"After 15th: {ob_u+p1-i1+p2} units, {inr((ob_u+p1-i1)*r1+p2*p2r)} → ₹{r2:g}",
       f"Issue {i2} @ {r2:g}; closing {bal_u} units × {r2:g} = {R(bal_v)}"],
      "New average after every receipt = Balance value ÷ Balance units",
      "Moving average recomputes after each purchase; periodic average does it once.")

ppt, dt, ict, tc, good = 480, 60, 0.8, 450, 423
av, pf, ql = (ppt - dt) / ppt, tc * ict / (ppt - dt), good / tc
oee = av * pf * ql
assert isclose(oee, good * ict / ppt)
B.add(S("tpm"), "L3",
      f"Shift data for a packing machine: planned production time {ppt} minutes; unplanned stoppages {dt} minutes; ideal cycle time {ict} minute per unit; total units produced {tc}; good units {good}. "
      "The Overall Equipment Effectiveness (OEE) is:",
      pct(oee),
      [(pct(av * pf), "quality rate ignored"),
       (pct(av * (tc * ict / ppt) * ql), "performance measured against planned time, not run time"),
       (pct(pf * ql), "availability ignored")],
      [f"Availability = ({ppt} − {dt}) ÷ {ppt} = {pct(av)}",
       f"Performance = ({tc} × {ict}) ÷ {ppt-dt} = {pct(pf)}",
       f"Quality = {good} ÷ {tc} = {pct(ql)}",
       f"OEE = {pct(av)} × {pct(pf)} × {pct(ql)} = {pct(oee)} (check: {good} × {ict} ÷ {ppt})"],
      "OEE = Availability × Performance × Quality", "Performance uses run time, not planned time — else stoppages are counted twice.")

D, O, pr, cr, disc, dq = 20000, 400, 80, 0.20, 0.02, 4000
C = pr * cr; e = sqrt(2 * D * O / C)
assert e == 1000
tc_e = D * pr + D / e * O + e / 2 * C
p2_ = pr * (1 - disc); C2 = p2_ * cr
tc_d = D * p2_ + D / dq * O + dq / 2 * C2
sav = tc_e - tc_d
assert isclose(sav, 14640)
tc_d_oldC = D * p2_ + D / dq * O + dq / 2 * C
tc_e_full = D * pr + D / e * O + e * C; tc_d_full = D * p2_ + D / dq * O + dq * C2
B.add(S("eoq"), "L3",
      f"Annual demand {inr(D)} units; ordering cost {R(O)} per order; price ₹{pr} per unit; carrying cost {pct(cr,0)} of average inventory value. "
      f"The supplier offers a {pct(disc,0)} discount on orders of {inr(dq)} units or more. Compared with ordering at EOQ, accepting the discount results in a net annual:",
      f"Saving of {R(sav)}",
      [(f"Saving of {R(tc_e - tc_d_oldC)}", "carrying cost per unit not reduced for the discounted price"),
       (f"Saving of {R(D*pr*disc)}", "only the price saving considered"),
       (f"Loss of {R(tc_d_full - tc_e_full)}", "carrying cost charged on the full order instead of average stock")],
      [f"EOQ = √(2 × {inr(D)} × {O} ÷ {C:g}) = {inr(e)}",
       f"At EOQ: purchase {inr(D*pr)} + ordering {inr(D/e*O)} + carrying {inr(e/2*C)} = {inr(tc_e)}",
       f"At {inr(dq)}: price ₹{p2_:g}, C = ₹{C2:g}; purchase {inr(D*p2_)} + ordering {inr(D/dq*O)} + carrying {inr(dq/2*C2)} = {inr(tc_d)}",
       f"Net saving = {inr(tc_e)} − {inr(tc_d)} = {inr(sav)}"],
      "Compare total cost (purchase + ordering + carrying) at each option",
      "When carrying is a % of price, the discount also lowers carrying cost per unit.")

cp, cert, uncert, cost_td, cashpct = 12000000, 7200000, 400000, 6600000, 0.90
npf = cert + uncert - cost_td; cash = cert * cashpct
prof = 2 / 3 * npf * cash / cert
assert isclose(prof, 600000)
B.add(S("contract"), "L3",
      f"Contract price {crore(cp)}. At the year end: work certified {lakh(cert)}; work done but not certified (at cost) {lakh(uncert)}; total cost incurred to date {lakh(cost_td)} (including the uncertified work). "
      f"The contractee has paid {pct(cashpct,0)} of work certified, the balance being retention money. Using the conventional cost-accounting rule for incomplete contracts, the profit to be credited to the Profit and Loss Account is:",
      lakh(prof),
      [(lakh(2 / 3 * npf), "cash-received ratio ignored"),
       (lakh(1 / 3 * npf * cash / cert), "one-third rule used though the contract is 60% complete"),
       (lakh(npf * cash / cert), "whole notional profit taken, scaled only by cash ratio")],
      [f"Notional profit = ({inr(cert)} + {inr(uncert)}) − {inr(cost_td)} = {lakh(npf)}",
       f"Stage of completion = {inr(cert)} ÷ {inr(cp)} = {pct(cert/cp,0)} (≥ 50%)",
       f"Profit = 2/3 × {lakh(npf)} × ({pct(cashpct,0)} cash ÷ certified) = {lakh(prof)}"],
      "≥ 50% complete: ⅔ × Notional profit × Cash received ÷ Work certified",
      "The balance of notional profit is kept as a reserve against the retention risk.",
      ref="Conventional cost-accounting treatment (ICAI/ICMAI contract costing); not the Ind AS 115 revenue method.")

inp, ip, conv, nl, sv, outp = 10000, 24, 126000, 0.10, 6, 9300
tot = inp * ip + conv; nlu = inp * nl; expo = inp - nlu
cpu = (tot - nlu * sv) / expo; ag = outp - expo
assert cpu == 40 and ag == 300
net = ag * cpu - ag * sv
B.add(S("process"), "L3",
      f"Process B: input {inr(inp)} units at ₹{ip}; conversion cost {R(conv)}. Normal loss {pct(nl,0)} of input, saleable at ₹{sv} per unit. Actual output {inr(outp)} units. "
      "The net amount credited to the Costing Profit and Loss Account from the abnormal gain (after adjusting for scrap sales forgone) is:",
      R(net),
      [(R(ag * cpu), "scrap value forgone on the gain units ignored"),
       (R(ag * cpu + ag * sv), "scrap value added instead of deducted"),
       (R(ag * tot / inp - ag * sv), "gain valued at cost per unit of input")],
      [f"Normal loss = {inr(nlu)}; expected output {inr(expo)}; cost per unit = ({inr(tot)} − {inr(nlu*sv)}) ÷ {inr(expo)} = ₹{cpu:g}",
       f"Abnormal gain = {inr(outp)} − {inr(expo)} = {ag} units × {cpu:g} = {inr(ag*cpu)} (debited to process)",
       f"Scrap not realised on {ag} units = {inr(ag*sv)} (debited to Abnormal Gain a/c)",
       f"Net to Costing P&L = {inr(ag*cpu)} − {inr(ag*sv)} = {R(net)}"],
      "Net gain = Gain units × (Normal cost per unit − Scrap value)",
      "The gain means fewer loss units to sell as scrap.")

ow, ow_c, intro, done, cw, cw_c = 2000, 0.60, 18000, 17000, 3000, 0.40
mat_cur, conv_cur, ow_mat, ow_conv = 540000, 357000, 62000, 29750
assert ow + intro == done + cw
f_mat = (done - ow) + cw; f_conv = ow * (1 - ow_c) + (done - ow) + cw * cw_c
assert f_mat == 18000 and f_conv == 17000
fr_m, fr_c = mat_cur / f_mat, conv_cur / f_conv
f_cwip = cw * fr_m + cw * cw_c * fr_c
w_mat = done + cw; w_conv = done + cw * cw_c
wr_m, wr_c = (ow_mat + mat_cur) / w_mat, (ow_conv + conv_cur) / w_conv
w_cwip = cw * wr_m + cw * cw_c * wr_c
bad_conv = ow * ow_c + (done - ow) + cw * cw_c
b_cwip = cw * fr_m + cw * cw_c * conv_cur / bad_conv
c100 = cw * fr_m + cw * conv_cur / (ow * (1 - ow_c) + (done - ow) + cw)
assert isclose(f_cwip, 115200)
B.add(S("equiv"), "L3",
      f"Process C data for the month (materials added at the start; conversion uniform):\n\n| | Units | Conversion complete | Cost (₹) |\n|---|---:|---:|---:|\n"
      f"| Opening WIP | {inr(ow)} | {pct(ow_c,0)} | Materials {inr(ow_mat)}; conversion {inr(ow_conv)} |\n| Introduced | {inr(intro)} | | Materials {inr(mat_cur)} |\n"
      f"| Conversion cost for the month | | | {inr(conv_cur)} |\n| Completed and transferred | {inr(done)} | | |\n| Closing WIP | {inr(cw)} | {pct(cw_c,0)} | |\n\n"
      "There are no losses. Under the **FIFO** method, the value of closing WIP is:",
      R(f_cwip),
      [(R(w_cwip), "weighted-average method used"),
       (R(b_cwip), "opening WIP given its past 60% instead of the 40% completed this month"),
       (R(c100), "closing WIP treated as fully converted")],
      [f"FIFO EU — materials: 0 + {inr(done-ow)} + {inr(cw)} = {inr(f_mat)}; conversion: {inr(ow*(1-ow_c))} + {inr(done-ow)} + {inr(cw*cw_c)} = {inr(f_conv)}",
       f"Rates (current costs only): materials {inr(mat_cur)} ÷ {inr(f_mat)} = ₹{fr_m:g}; conversion {inr(conv_cur)} ÷ {inr(f_conv)} = ₹{fr_c:g}",
       f"Closing WIP = {inr(cw)} × {fr_m:g} + {inr(cw*cw_c)} × {fr_c:g} = {R(f_cwip)}"],
      "FIFO EU = Work to finish opening WIP + Started & finished + Closing WIP EU",
      "Under FIFO opening WIP cost is kept out of the rate; only the work done this month counts.")

cs2, share1, mk1 = 90000, 0.80, 0.20
urp = cs2 * share1 * mk1 / (1 + mk1)
assert isclose(urp, 12000)
B.add(S("interproc"), "L3",
      f"Output of Process I is transferred to Process II at cost plus {pct(mk1,0)} on cost. At the year end, the closing stock of Process II is valued at {R(cs2)}, "
      f"of which {pct(share1,0)} represents the transfer price of Process I output and the rest Process II's own costs. The provision for unrealised profit on this stock is:",
      R(urp),
      [(R(cs2 * share1 * mk1), "20% applied to transfer price instead of 20/120"),
       (R(cs2 * mk1 / (1 + mk1)), "applied to the whole stock including Process II's own costs"),
       (R(cs2 * mk1), "20% applied to the whole stock value")],
      [f"Process I element = {pct(share1,0)} × {inr(cs2)} = {inr(cs2*share1)} (at transfer price)",
       f"Profit in transfer price = {mk1*100:g}/{(1+mk1)*100:g} of transfer price",
       f"Unrealised profit = {inr(cs2*share1)} × 20/120 = {R(urp)}"],
      "Unrealised profit = Transfer-price element × Mark-up ÷ (100 + Mark-up)",
      "A mark-up on cost becomes 1/6 of the transfer price.")

jc = 480000
prods = {"A": (6000, 50, 60000), "B": (4000, 70, 40000), "C": (10000, 12, 0)}
nrvj = {k: q * p - f for k, (q, p, f) in prods.items()}; TN = sum(nrvj.values())
a_sh = jc * nrvj["A"] / TN; a_pk = (a_sh + prods["A"][2]) / prods["A"][0]
assert a_sh == 192000 and a_pk == 42
tq = sum(q for q, _, _ in prods.values()); sv_ = {k: q * p for k, (q, p, f) in prods.items()}
tbl = "| Product | Output (kg) | Final price (₹/kg) | Further processing cost (₹) |\n|---|---:|---:|---:|\n" + \
      "\n".join(f"| {k} | {inr(q)} | {p} | {inr(f)} |" for k, (q, p, f) in prods.items())
B.add(S("joint"), "L3",
      f"A joint process costs {R(jc)}.\n\n{tbl}\n\nC is sold at split-off. Apportioning joint cost by net realisable value at split-off, the total cost per kg of A is:",
      Rd(a_pk),
      [(Rd((jc * prods['A'][0] / tq + prods['A'][2]) / prods['A'][0]), "physical-units basis"),
       (Rd((jc * sv_['A'] / sum(sv_.values()) + prods['A'][2]) / prods['A'][0]), "final sales value used without deducting further cost"),
       (Rd(a_sh / prods['A'][0]), "further processing cost not added")],
      ["NRV: " + "; ".join(f"{k} {inr(nrvj[k])}" for k in prods) + f" → total {inr(TN)}",
       f"A's joint cost = {inr(jc)} × {inr(nrvj['A'])} ÷ {inr(TN)} = {inr(a_sh)}",
       f"A's total = {inr(a_sh)} + {inr(prods['A'][2])} = {inr(a_sh+prods['A'][2])} ÷ {inr(prods['A'][0])} = {Rd(a_pk)}"],
      "NRV = Final sales value − Further processing cost", "Add A's own further cost after apportioning joint cost.")

pq, pp_, sp_, used, sq_ = 12000, 42, 40, 10500, 10000
mpv = (sp_ - pp_) * pq; muv = (sq_ - used) * sp_
B.add(S("matvar"), "L3",
      f"Standard price of a material is ₹{sp_} per kg. During the month {inr(pq)} kg were purchased at ₹{pp_} per kg and {inr(used)} kg were issued to production; "
      f"standard quantity for the actual output was {inr(sq_)} kg. If the price variance is recognised **at the time of purchase**, the price and usage variances are:",
      f"Price {V(mpv)}; usage {V(muv)}",
      [(f"Price {V((sp_-pp_)*used)}; usage {V(muv)}", "price variance computed on quantity used"),
       (f"Price {V(mpv)}; usage {V((sq_-used)*pp_)}", "usage valued at actual price"),
       (f"Price {V(-mpv)}; usage {V(muv)}", "price variance direction reversed")],
      [f"Price variance on purchases = ({sp_} − {pp_}) × {inr(pq)} = {V(mpv)}",
       f"Usage = ({inr(sq_)} − {inr(used)}) × {sp_} = {V(muv)}",
       "Closing stock is then carried at standard price."],
      "MPV (at purchase) = (SP − AP) × Quantity purchased", "The recognition point decides the quantity base of the price variance.")

sh, sr, out, paid, ar, idle = 3, 120, 2000, 6600, 125, 250
std_h = sh * out; worked = paid - idle
rv = (sr - ar) * paid; iv = -idle * sr; ev = (std_h - worked) * sr
assert rv + iv + ev == std_h * sr - paid * ar and ev == -42000
B.add(S("labvar"), "L3",
      f"Standard: {sh} labour hours per unit at ₹{sr}. Output {inr(out)} units. Workers were paid for {inr(paid)} hours at ₹{ar}, but {idle} hours were lost due to a power breakdown (abnormal idle time). "
      "The labour efficiency variance is:",
      V(ev),
      [(V((std_h - paid) * sr), "idle hours not separated (paid hours used)"),
       (V((std_h - worked) * ar), "valued at actual rate"),
       (V(iv), "idle time variance reported")],
      [f"Standard hours = {sh} × {inr(out)} = {inr(std_h)}; hours worked = {inr(paid)} − {idle} = {inr(worked)}",
       f"Efficiency = ({inr(std_h)} − {inr(worked)}) × {sr} = {V(ev)}",
       f"Check: rate {V(rv)} + idle {V(iv)} + efficiency {V(ev)} = total {V(rv+iv+ev)}"],
      "LEV = (SH − Hours worked) × SR; Idle time variance = Idle hours × SR",
      "Idle hours are paid but not worked — keep them out of efficiency.")

bfo, bu, shu, afo, au, ahh = 600000, 20000, 2, 624000, 18500, 38000
bh = bu * shu; hr = bfo / bh; ur = bfo / bu; sh_act = au * shu
exp_ = bfo - afo; vol = (au - bu) * ur; eff_ = (sh_act - ahh) * hr; cap = (ahh - bh) * hr
assert vol == eff_ + cap and cap == -30000
B.add(S("ohvar"), "L3",
      f"Budgeted fixed overhead {R(bfo)} for {inr(bu)} units; standard time {shu} hours per unit. Actual fixed overhead {R(afo)}; actual output {inr(au)} units in {inr(ahh)} hours. "
      "The fixed overhead **capacity** variance is:",
      V(cap),
      [(V(vol), "total volume variance reported"),
       (V(eff_), "efficiency variance reported"),
       (V(-cap), "direction reversed")],
      [f"Budgeted hours = {inr(bh)}; rate = ₹{hr:g} per hour (₹{ur:g} per unit)",
       f"Capacity = (Actual hours − Budgeted hours) × rate = ({inr(ahh)} − {inr(bh)}) × {hr:g} = {V(cap)}",
       f"Efficiency = ({inr(sh_act)} − {inr(ahh)}) × {hr:g} = {V(eff_)}; volume = {V(vol)}; expenditure = {V(exp_)}"],
      "Volume = Capacity + Efficiency", "Capacity compares actual hours with budgeted hours, not standard hours.")

vr, shu, au, ahh, avoh = 8, 2, 18500, 38000, 296400
vexp = ahh * vr - avoh; veff = (au * shu - ahh) * vr
assert vexp == 7600 and veff == -8000
B.add(S("ohvar"), "L3",
      f"Variable overhead is absorbed at ₹{vr} per labour hour; standard time is {shu} hours per unit. Actual output {inr(au)} units; actual hours {inr(ahh)}; actual variable overhead {R(avoh)}. "
      "The variable overhead expenditure and efficiency variances are:",
      f"Expenditure {V(vexp)}; efficiency {V(veff)}",
      [(f"Expenditure {V(au*shu*vr-avoh)}; efficiency {V(veff)}", "expenditure measured against standard-hours allowance"),
       (f"Expenditure {V(-vexp)}; efficiency {V(-veff)}", "both directions reversed"),
       (f"Expenditure {V(vexp)}; efficiency {V((au*shu-ahh)*avoh/ahh)}", "efficiency valued at actual rate per hour")],
      [f"Expenditure = AH × SR − Actual = {inr(ahh)} × {vr} − {inr(avoh)} = {V(vexp)}",
       f"Efficiency = (SH − AH) × SR = ({inr(au*shu)} − {inr(ahh)}) × {vr} = {V(veff)}",
       f"Total = {inr(au*shu*vr)} − {inr(avoh)} = {V(au*shu*vr-avoh)}"],
      "VOH exp = AH × SR − AVOH; VOH eff = (SH − AH) × SR",
      "The expenditure allowance is based on actual hours.")

bud = {"P": (4000, 50), "Q": (6000, 30)}; act = {"P": (5000, 48), "Q": (5500, 32)}
bt = sum(q for q, _ in bud.values()); at = sum(q for q, _ in act.values())
rsm = {k: at * bud[k][0] / bt for k in bud}
mixv = sum((act[k][0] - rsm[k]) * bud[k][1] for k in bud)
qtyv = sum((rsm[k] - bud[k][0]) * bud[k][1] for k in bud)
volv = sum((act[k][0] - bud[k][0]) * bud[k][1] for k in bud)
mix_ap = sum((act[k][0] - rsm[k]) * act[k][1] for k in bud)
assert mixv == 16000 and isclose(mixv + qtyv, volv)
B.add(S("salesvar"), "L3",
      f"Sales data (value basis):\n\n| Product | Budget units | Budget price (₹) | Actual units | Actual price (₹) |\n|---|---:|---:|---:|---:|\n"
      + "\n".join(f"| {k} | {inr(bud[k][0])} | {bud[k][1]} | {inr(act[k][0])} | {act[k][1]} |" for k in bud) +
      "\n\nThe sales **mix** variance (in terms of sales value) is:",
      V(mixv),
      [(V(qtyv), "sales quantity variance reported"),
       (V(volv), "total sales volume variance reported"),
       (V(mix_ap), "mix valued at actual prices")],
      [f"Actual total {inr(at)} units in budget ratio 4 : 6 → P {inr(rsm['P'])}, Q {inr(rsm['Q'])}",
       f"Mix = (5,000 − {inr(rsm['P'])}) × 50 + (5,500 − {inr(rsm['Q'])}) × 30 = {V(mixv)}",
       f"Quantity = {V(qtyv)}; volume = {V(volv)} = mix + quantity"],
      "Mix = (Actual qty − Revised std mix qty) × Budget price",
      "Mix and quantity together make up the volume variance.")

var, rmst, wip, fg, cogs = 48000, 100000, 60000, 140000, 700000
base = rmst + wip + fg + cogs; to_cogs = var * cogs / base
assert isclose(to_cogs, 33600)
B.add(S("disposal"), "L3",
      f"An adverse material price variance of {R(var)} arose because the standard price was set unrealistically low; it is to be prorated rather than written off. "
      f"Standard material content: closing raw material stock {R(rmst)}; WIP {R(wip)}; finished goods {R(fg)}; cost of goods sold {R(cogs)}. The variance is to be prorated over closing raw material stock, WIP, finished goods and cost of goods sold in proportion to their standard material content. The amount charged to cost of goods sold is:",
      R(to_cogs),
      [(R(var), "entire variance written off to P&L"),
       (R(var * cogs / (wip + fg + cogs)), "raw material stock excluded from proration"),
       (R(var * cogs / (fg + cogs)), "prorated only between finished goods and cost of sales")],
      [f"Proration base = {inr(rmst)} + {inr(wip)} + {inr(fg)} + {inr(cogs)} = {inr(base)}",
       f"To COGS = {inr(var)} × {inr(cogs)} ÷ {inr(base)} = {R(to_cogs)}",
       "A price variance arises at purchase, so raw material still in stock carries its share."],
      "Prorated share = Variance × Standard content in account ÷ Total standard content",
      "Abnormal/controllable variances go to P&L; standard-setting errors are prorated.")

u60, u80 = 12000, 16000
dmu, dlu, vohu, semi, semif, fixo = 40, 25, 10, 240000, 0.50, 360000
sf = semi * semif; sv_u = semi * (1 - semif) / u60
t80 = u80 * (dmu + dlu + vohu) + sf + sv_u * u80 + fixo
assert t80 / u80 == 115
B.add(S("flex"), "L3",
      f"Budget at 60% capacity ({inr(u60)} units): direct materials ₹{dmu}, direct labour ₹{dlu} and variable overhead ₹{vohu} per unit; semi-variable overhead {R(semi)} "
      f"({pct(semif,0)} fixed); fixed overhead {R(fixo)}. The budgeted cost per unit at 80% capacity is:",
      Rd(t80 / u80),
      [(Rd((u80 * (dmu + dlu + vohu) + semi / u60 * u80 + fixo) / u80), "semi-variable overhead treated as fully variable"),
       (Rd((u80 * (dmu + dlu + vohu) + semi / u60 * u80 + fixo / u60 * u80) / u80), "all overheads scaled up with volume"),
       (Rd((u80 * (dmu + dlu + vohu) + semi + fixo) / u80), "semi-variable overhead treated as fully fixed")],
      [f"Variable: {inr(u80)} × ₹{dmu+dlu+vohu} = {inr(u80*(dmu+dlu+vohu))}",
       f"Semi-variable: fixed {inr(sf)} + variable ₹{sv_u:g} × {inr(u80)} = {inr(sf+sv_u*u80)}",
       f"Fixed {inr(fixo)}; total {inr(t80)} ÷ {inr(u80)} = {Rd(t80/u80)}"],
      "Flexed cost = Fixed + Variable rate × Activity",
      "Split semi-variable costs before flexing.")

sales = {"Jan": 400000, "Feb": 500000, "Mar": 600000}; cashp, m1, disc, m2 = 0.20, 0.60, 0.02, 0.38
credit = {k: v * (1 - cashp) for k, v in sales.items()}
coll = sales["Mar"] * cashp + credit["Feb"] * m1 * (1 - disc) + credit["Jan"] * m2
assert isclose(coll, 476800)
B.add(S("cash"), "L3",
      f"Sales: January {R(sales['Jan'])}, February {R(sales['Feb'])}, March {R(sales['Mar'])}. {pct(cashp,0)} of sales are for cash. "
      f"Of credit sales, {pct(m1,0)} are collected in the month after sale (these customers take a {pct(disc,0)} cash discount), {pct(m2,0)} in the second month after sale and the rest are bad debts. "
      "Cash collected from debtors and cash sales in March is:",
      R(coll),
      [(R(sales['Mar'] * cashp + credit['Feb'] * m1 + credit['Jan'] * m2), "cash discount ignored"),
       (R(sales['Mar'] * cashp + credit['Jan'] * m1 * (1 - disc) + credit['Feb'] * m2), "collection lags applied to the wrong months"),
       (R(sales['Mar'] * cashp + sales['Feb'] * m1 * (1 - disc) + sales['Jan'] * m2), "collection percentages applied to total sales, not credit sales")],
      [f"Cash sales (Mar) = {pct(cashp,0)} × {inr(sales['Mar'])} = {inr(sales['Mar']*cashp)}",
       f"February credit {inr(credit['Feb'])} × {pct(m1,0)} × 98% = {inr(credit['Feb']*m1*(1-disc))}",
       f"January credit {inr(credit['Jan'])} × {pct(m2,0)} = {inr(credit['Jan']*m2)}",
       f"Total = {R(coll)}"],
      "Receipts = Cash sales + Σ(Credit sales of month t−k × collection % × (1 − discount))",
      "Cash sales are excluded before applying collection patterns.")

need, stock, hist, repl_, resale = 2000, 1200, 30, 38, 22
rel = stock * resale + (need - stock) * repl_
assert rel == 56800
B.add(S("relevant"), "L3",
      f"A special order needs {inr(need)} kg of material K. {inr(stock)} kg are in stock, bought earlier at ₹{hist} per kg; K is no longer used in regular production and could be sold for ₹{resale} per kg. "
      f"Current replacement price is ₹{repl_} per kg. The relevant cost of material K for the order is:",
      R(rel),
      [(R(need * repl_), "stock valued at replacement cost though it will not be replaced"),
       (R(stock * hist + (need - stock) * repl_), "historical (sunk) cost used for stock"),
       (R((need - stock) * repl_), "stock treated as costless (resale value ignored)")],
      [f"Stock in hand: not needed elsewhere → opportunity cost = resale value {inr(stock)} × {resale} = {inr(stock*resale)}",
       f"Balance {inr(need-stock)} kg must be bought at {repl_} = {inr((need-stock)*repl_)}",
       f"Relevant cost = {R(rel)}"],
      "Relevant cost of stock = Replacement cost if regularly used; otherwise higher of resale / alternative-use value",
      "Historical cost is sunk.")

r, n = 0.10, 5
af = sum(1 / (1 + r) ** t for t in range(1, n + 1)); df5 = 1 / (1 + r) ** n
A_ = (1000000, 200000, 100000); Bm = (700000, 280000, 0)
pv = lambda m, sal_sign=-1: m[0] + m[1] * af + sal_sign * m[2] * df5
pa, pb = pv(A_), pv(Bm)
assert pa < pb
B.add(S("target"), "L3",
      f"Two machines are compared over a {n}-year life at a {pct(r,0)} discount rate:\n\n| | Machine A | Machine B |\n|---|---:|---:|\n| Purchase cost (₹) | {inr(A_[0])} | {inr(Bm[0])} |\n"
      f"| Annual operating cost (₹) | {inr(A_[1])} | {inr(Bm[1])} |\n| Salvage value at end (₹) | {inr(A_[2])} | {inr(Bm[2])} |\n\nOn a discounted life-cycle cost basis:",
      f"Machine A is cheaper by {R(pb-pa)}",
      [(f"Machine A is cheaper by {R((Bm[0]+n*Bm[1]) - (A_[0]+n*A_[1]-A_[2]))}", "undiscounted life-cycle cost"),
       (f"Machine A is cheaper by {R(pb - (A_[0]+A_[1]*af-A_[2]))}", "salvage value not discounted"),
       (f"Machine B is cheaper by {R(pv(A_, +1) - pb)}", "salvage value added instead of deducted")],
      [f"Annuity factor (10%, 5 yrs) = {af:.4f}; PV factor yr 5 = {df5:.4f}",
       f"A = {inr(A_[0])} + {inr(A_[1])} × {af:.4f} − {inr(A_[2])} × {df5:.4f} = {inr(pa)}",
       f"B = {inr(Bm[0])} + {inr(Bm[1])} × {af:.4f} = {inr(pb)}",
       f"A cheaper by {R(pb-pa)}"],
      "Life-cycle cost = Acquisition + PV of operating costs − PV of salvage",
      "Lower purchase price does not mean lower life-cycle cost.")

x0, y0, p1p = 36000, 54000, 120000
X_to = {"Y": 0.25, "P1": 0.45, "P2": 0.30}; Y_to = {"X": 0.40, "P1": 0.30, "P2": 0.30}
Xt = (x0 + Y_to["X"] * y0) / (1 - X_to["Y"] * Y_to["X"]); Yt = y0 + X_to["Y"] * Xt
assert isclose(Xt, 64000) and isclose(Yt, 70000)
P1 = p1p + X_to["P1"] * Xt + Y_to["P1"] * Yt
direct = p1p + x0 * X_to["P1"] / (1 - X_to["Y"]) + y0 * Y_to["P1"] / (1 - Y_to["X"])
step = p1p + x0 * X_to["P1"] + (y0 + x0 * X_to["Y"]) * Y_to["P1"] / (1 - Y_to["X"])
naive = p1p + x0 * X_to["P1"] + y0 * Y_to["P1"]
assert isclose(P1, 169800)
B.add(S("ohabs"), "L3",
      f"Primary overheads: production department P1 {R(p1p)}; service departments X {R(x0)} and Y {R(y0)}. Services are used as follows:\n\n"
      "| From \\ To | X | Y | P1 | P2 |\n|---|---:|---:|---:|---:|\n| X | — | 25% | 45% | 30% |\n| Y | 40% | — | 30% | 30% |\n\n"
      "Using the simultaneous-equation (reciprocal) method, total overhead of P1 after secondary distribution is:",
      R(P1),
      [(R(direct), "direct method (inter-service usage ignored)"),
       (R(step), "step method, X closed first"),
       (R(naive), "primary figures of X and Y used without reciprocal gross-up")],
      [f"X = {inr(x0)} + 0.40Y; Y = {inr(y0)} + 0.25X",
       f"X = ({inr(x0)} + 0.40 × {inr(y0)}) ÷ (1 − 0.25 × 0.40) = {inr(Xt)}; Y = {inr(Yt)}",
       f"P1 = {inr(p1p)} + 45% × {inr(Xt)} + 30% × {inr(Yt)} = {R(P1)}"],
      "Reciprocal: solve X and Y totals, then apply production percentages",
      "Percentages apply to the grossed-up service totals.")

aoh, arrears, absb = 1240000, 40000, 1150000
shares = {"WIP": 115000, "Finished goods": 230000, "Cost of sales": 805000}
assert sum(shares.values()) == absb
normal_under = aoh - arrears - absb; cogs_sh = normal_under * shares["Cost of sales"] / absb
assert isclose(cogs_sh, 35000)
B.add(S("underover"), "L3",
      f"Actual factory overhead for the year was {R(aoh)}, including {R(arrears)} of wage arrears relating to the previous year. Overhead absorbed was {R(absb)}, lying in: "
      + "; ".join(f"{k} {R(v)}" for k, v in shares.items()) +
      ". Normal under-absorption is adjusted through a supplementary rate. The amount added to cost of sales is:",
      R(cogs_sh),
      [(R((aoh - absb) * shares['Cost of sales'] / absb), "prior-year arrears included in the supplementary rate"),
       (R(normal_under), "whole normal under-absorption charged to cost of sales"),
       (R(aoh - absb), "entire under-absorption charged to cost of sales")],
      [f"Total under-absorption = {inr(aoh)} − {inr(absb)} = {inr(aoh-absb)}",
       f"Arrears of previous year ({inr(arrears)}) → Costing P&L (abnormal)",
       f"Normal under-absorption = {inr(normal_under)}; supplementary rate = {normal_under/absb*100:.4f}% of absorbed overhead",
       f"Cost of sales = {inr(normal_under)} × {inr(shares['Cost of sales'])} ÷ {inr(absb)} = {R(cogs_sh)}"],
      "Supplementary rate = Normal under-absorption ÷ Overhead absorbed",
      "Abnormal items and prior-period items are excluded from the supplementary rate.")

sgl, dbl, os_, od, days, dfac, cost_h, pm = 60, 40, 0.80, 0.60, 360, 1.25, 8424000, 0.25
eq = sgl * os_ * days + dbl * od * days * dfac
rent = cost_h / (1 - pm) / eq
assert isclose(rent, 400)
B.add(S("service"), "L3",
      f"A hotel has {sgl} single and {dbl} double rooms. Occupancy: single rooms {pct(os_,0)}, double rooms {pct(od,0)}, over {days} days. Rent of a double room is to be {pct(dfac,0)} of a single room. "
      f"Annual costs are {R(cost_h)} and the hotel wants a profit of {pct(pm,0)} on total rent. The rent per day for a single room is:",
      Rd(rent),
      [(Rd(cost_h * (1 + pm) / eq), "25% treated as mark-up on cost"),
       (Rd(cost_h / (1 - pm) / (sgl * os_ * days + dbl * od * days)), "double rooms not weighted at 125%"),
       (Rd(cost_h / (1 - pm) / (sgl * days + dbl * days * dfac)), "occupancy ignored")],
      [f"Single room-days = {sgl} × {pct(os_,0)} × {days} = {inr(sgl*os_*days)}",
       f"Double room-days = {dbl} × {pct(od,0)} × {days} = {inr(dbl*od*days)} × 1.25 = {inr(dbl*od*days*dfac)} equivalent",
       f"Required rent = {inr(cost_h)} ÷ 0.75 = {inr(cost_h/(1-pm))}",
       f"Single rent = {inr(cost_h/(1-pm))} ÷ {inr(eq)} = {Rd(rent)} (double {Rd(rent*dfac)})"],
      "Rent per equivalent room-day = (Cost ÷ (1 − margin)) ÷ Equivalent room-days",
      "Convert double rooms to single-room equivalents first.")

sp_, sq_, mpv_, muv_ = 25, 8000, 16400, -5000
aq_ = sq_ - muv_ / sp_; ap_ = sp_ - mpv_ / aq_
act_cost = aq_ * ap_
assert aq_ == 8200 and ap_ == 23 and act_cost == 188600
B.add(S("matvar"), "L3",
      f"Standard price of a material is ₹{sp_} per kg and the standard quantity for actual output is {inr(sq_)} kg. The material price variance is {V(mpv_)} and the usage variance {V(muv_)}. "
      "The actual cost of material used is:",
      R(act_cost),
      [(R(sq_ * sp_ - mpv_ - (-muv_)), "usage variance treated as favourable"),
       (R(sq_ * sp_ + mpv_ + muv_), "net favourable variance added to standard cost"),
       (R(aq_ * sp_), "actual quantity at standard price (price variance ignored)")],
      [f"AQ = SQ − MUV ÷ SP = {inr(sq_)} + {inr(-muv_)} ÷ {sp_} = {inr(aq_)} kg",
       f"AP = SP − MPV ÷ AQ = {sp_} − {inr(mpv_)} ÷ {inr(aq_)} = ₹{ap_:g}",
       f"Actual cost = {inr(aq_)} × {ap_:g} = {R(act_cost)} (= std cost {inr(sq_*sp_)} − net favourable {inr(mpv_+muv_)})"],
      "Actual cost = Standard cost of actual output − Net favourable variance",
      "A favourable variance means actual cost is BELOW standard.")

bh, ah = 10000, 9500
outs = {"A": (1200, 4), "B": (900, 5)}
shp = sum(u * h for u, h in outs.values())
act_r = shp / bh
assert shp == 9300
B.add(S("budget"), "L3",
      f"Budgeted hours for the month were {inr(bh)}. Actual hours worked were {inr(ah)}. Output: product A {inr(outs['A'][0])} units (standard {outs['A'][1]} hours each) and "
      f"product B {inr(outs['B'][0])} units (standard {outs['B'][1]} hours each). The **activity ratio** is:",
      pct(act_r),
      [(pct(shp / ah), "efficiency ratio (standard ÷ actual hours)"),
       (pct(ah / bh), "capacity ratio (actual ÷ budgeted hours)"),
       (pct(ah / shp), "actual hours ÷ standard hours (inverse efficiency)")],
      [f"Standard hours produced = {inr(outs['A'][0])} × {outs['A'][1]} + {inr(outs['B'][0])} × {outs['B'][1]} = {inr(shp)}",
       f"Activity ratio = {inr(shp)} ÷ {inr(bh)} = {pct(act_r)}",
       f"Check: efficiency {pct(shp/ah)} × capacity {pct(ah/bh)} = activity"],
      "Activity = Std hours produced ÷ Budgeted hours = Efficiency × Capacity",
      "Three ratios, three different pairs of hours.")

# =====================================================================
# L4 — case sets (4 × 4)
# =====================================================================
# ---- Case 1: Process costing with opening WIP, losses, weighted average ----
ow, ow_c, ow_ti, ow_cc = 1000, 0.40, 42000, 9200
ti_u, ti_c, cc = 9000, 376500, 245800
nl_r, sv = 0.10, 10
done, cw, cw_c = 7400, 1500, 0.60
nlu = ti_u * nl_r; abl = ow + ti_u - done - cw - nlu
assert abl == 200
eu_ti = done + abl + cw; eu_cc = done + abl + cw * cw_c
r_ti = (ow_ti + ti_c - nlu * sv) / eu_ti; r_cc = (ow_cc + cc) / eu_cc
assert eu_cc == 8500 and r_ti == 45 and r_cc == 30
cpeu = r_ti + r_cc
tot_in = ow_ti + ow_cc + ti_c + cc - nlu * sv
assert isclose(done * cpeu + abl * cpeu + cw * r_ti + cw * cw_c * r_cc, tot_in)
# FIFO comparators
f_ti = (done - ow) + abl + cw; f_cc = ow * (1 - ow_c) + (done - ow) + abl + cw * cw_c
fr_ti = (ti_c - nlu * sv) / f_ti; fr_cc = cc / f_cc
# normal loss wrongly given EU
n_ti = eu_ti + nlu; n_cc = eu_cc + nlu
G1 = "CST-CASE-PROC"
st1 = ("**Case — Sarayu Chemicals Ltd (fictional), Process II, March**\n\n"
       "Materials arrive from Process I at the start; conversion is added evenly. Lost units (normal and abnormal) are treated as 100% complete for both elements; normal loss is assigned no equivalent units. "
       "The company uses the **weighted average** method and credits the realisable value of normal loss to the transferred-in (materials) element.\n\n"
       "| Item | Units | Conversion stage | Cost (₹) |\n|---|---:|---:|---:|\n"
       f"| Opening WIP | {inr(ow)} | {pct(ow_c,0)} | Transferred-in {inr(ow_ti)}; conversion {inr(ow_cc)} |\n"
       f"| Received from Process I | {inr(ti_u)} | | {inr(ti_c)} |\n"
       f"| Conversion costs for March | | | {inr(cc)} |\n"
       f"| Transferred to finished stock | {inr(done)} | | |\n"
       f"| Closing WIP | {inr(cw)} | {pct(cw_c,0)} | |\n\n"
       f"Normal loss is {pct(nl_r,0)} of units received from Process I during the month; lost units sell at ₹{sv} each.")
B.add(S("equiv"), "L4", st1 + "\n\n**Q.** Equivalent units for conversion cost are:",
      f"{inr(eu_cc)}",
      [(f"{inr(n_cc)}", "normal loss given equivalent units"),
       (f"{inr(eu_cc - abl)}", "abnormal loss excluded"),
       (f"{inr(f_cc)}", "FIFO equivalent units")],
      [f"Units to account for = {inr(ow)} + {inr(ti_u)} = {inr(ow+ti_u)}",
       f"Normal loss = {pct(nl_r,0)} × {inr(ti_u)} = {inr(nlu)}; abnormal loss = {inr(ow+ti_u)} − {inr(done)} − {inr(cw)} − {inr(nlu)} = {abl}",
       f"WA conversion EU = {inr(done)} + {abl} (abnormal loss, 100% complete) + {inr(cw)} × {pct(cw_c,0)} = {inr(eu_cc)}"],
      "WA EU = Completed + Abnormal loss (at stage) + Closing WIP × % ; normal loss = 0",
      "Normal loss carries no equivalent units; abnormal loss does.", kind="case", group=G1)

B.add(S("equiv"), "L4", st1 + "\n\n**Q.** The total cost per equivalent unit (transferred-in plus conversion) is:",
      Rd(cpeu),
      [(Rd((ow_ti + ti_c) / eu_ti + r_cc), "scrap value of normal loss not deducted"),
       (Rd(fr_ti + fr_cc), "FIFO rates computed"),
       (Rd((ow_ti + ti_c - nlu * sv) / n_ti + (ow_cc + cc) / n_cc), "normal loss given equivalent units")],
      [f"Transferred-in EU = {inr(done)} + {abl} + {inr(cw)} = {inr(eu_ti)}",
       f"Transferred-in rate = ({inr(ow_ti)} + {inr(ti_c)} − {inr(nlu*sv)}) ÷ {inr(eu_ti)} = ₹{r_ti:g}",
       f"Conversion rate = ({inr(ow_cc)} + {inr(cc)}) ÷ {inr(eu_cc)} = ₹{r_cc:g}",
       f"Total = ₹{cpeu:g}"],
      "WA rate = (Opening WIP cost + Current cost − Normal loss scrap) ÷ WA EU",
      "Under WA, opening WIP cost is pooled with current cost.", kind="case", group=G1)

B.add(S("process"), "L4", st1 + "\n\n**Q.** The net amount debited to the Costing Profit and Loss Account in respect of abnormal loss is:",
      R(abl * cpeu - abl * sv),
      [(R(abl * cpeu), "realisable value of abnormal-loss units not credited"),
       (R(abl * cpeu + abl * sv), "realisable value added instead of deducted"),
       (R(abl * (fr_ti + fr_cc) - abl * sv), "abnormal loss valued at FIFO rates")],
      [f"Abnormal loss = {abl} units × ₹{cpeu:g} = {inr(abl*cpeu)} (credited to Process II)",
       f"Sale of {abl} lost units × ₹{sv} = {inr(abl*sv)} credited to Abnormal Loss a/c",
       f"Net to Costing P&L = {R(abl*cpeu - abl*sv)}"],
      "Costing P&L charge = Abnormal loss value − Its realisable value",
      "Process credit is at full cost; only the net hits Costing P&L.", kind="case", group=G1)

B.add(S("equiv"), "L4", st1 + "\n\n**Q.** The value of closing WIP is:",
      R(cw * r_ti + cw * cw_c * r_cc),
      [(R(cw * cpeu), "closing WIP treated as 100% converted"),
       (R(cw * fr_ti + cw * cw_c * fr_cc), "FIFO rates applied"),
       (R(cw * r_ti + cw * ow_c * r_cc), "opening WIP's 40% stage applied to closing WIP")],
      [f"Transferred-in: {inr(cw)} × {r_ti:g} = {inr(cw*r_ti)}",
       f"Conversion: {inr(cw*cw_c)} × {r_cc:g} = {inr(cw*cw_c*r_cc)}",
       f"Closing WIP = {R(cw*r_ti + cw*cw_c*r_cc)}",
       f"Proof: finished {inr(done*cpeu)} + abnormal {inr(abl*cpeu)} + WIP {inr(cw*r_ti+cw*cw_c*r_cc)} = total costs net of scrap {inr(tot_in)}"],
      "Closing WIP = Σ (EU in WIP × rate per element)",
      "Transferred-in material is always 100% complete in Process II WIP.", kind="case", group=G1)

# ---- Case 2: Material mix/yield and labour variances ----
mixs = {"A": (60, 40), "B": (40, 65)}; std_in, std_out = 100, 90
acts = {"A": (5700, 42), "B": (4100, 63)}; aout = 8550
lh_std, lr_std, lh_paid, lr_act, lidle = 0.2, 150, 1800, 156, 60
AQ = sum(q for q, _ in acts.values())
SQ = {k: aout / std_out * mixs[k][0] for k in mixs}
RSQ = {k: AQ * mixs[k][0] / std_in for k in mixs}
mpv = sum((mixs[k][1] - acts[k][1]) * acts[k][0] for k in mixs)
mixv = sum((RSQ[k] - acts[k][0]) * mixs[k][1] for k in mixs)
avg_in = sum(q * p for q, p in mixs.values()) / std_in
yldv = (aout / std_out * std_in - AQ) * avg_in
usev = sum((SQ[k] - acts[k][0]) * mixs[k][1] for k in mixs)
assert mpv == -3200 and mixv == -4500 and yldv == -15000 and isclose(mixv + yldv, usev)
std_cost_out = avg_in * std_in / std_out
lsh = aout * lh_std; lwork = lh_paid - lidle
leff = (lsh - lwork) * lr_std
assert leff == -4500
G2 = "CST-CASE-MIX"
st2 = ("**Case — Nilgiri Coatings Pvt Ltd (fictional), April**\n\n"
       f"Standard mix: {std_in} kg of input yields {std_out} kg of paint base.\n\n"
       "| Material | Standard kg per batch | Standard price (₹/kg) | Actual kg used | Actual price (₹/kg) |\n|---|---:|---:|---:|---:|\n"
       + "\n".join(f"| {k} | {mixs[k][0]} | {mixs[k][1]} | {inr(acts[k][0])} | {acts[k][1]} |" for k in mixs) +
       f"\n\nActual output: {inr(aout)} kg. Standard labour: {lh_std} hour per kg of output at ₹{lr_std} per hour. "
       f"Labour paid: {inr(lh_paid)} hours at ₹{lr_act}, including {lidle} hours of abnormal idle time due to a boiler breakdown.")
B.add(S("matvar"), "L4", st2 + "\n\n**Q.** The material price variance is:",
      V(mpv),
      [(V(sum((mixs[k][1] - acts[k][1]) * SQ[k] for k in mixs)), "price difference applied to standard quantity"),
       (V(-mpv), "direction reversed"),
       (V((mixs['A'][1] - acts['A'][1]) * acts['A'][0]), "only material A's price change considered")],
      [f"A: ({mixs['A'][1]} − {acts['A'][1]}) × {inr(acts['A'][0])} = {V((mixs['A'][1]-acts['A'][1])*acts['A'][0])}",
       f"B: ({mixs['B'][1]} − {acts['B'][1]}) × {inr(acts['B'][0])} = {V((mixs['B'][1]-acts['B'][1])*acts['B'][0])}",
       f"Total = {V(mpv)}"],
      "MPV = Σ (SP − AP) × AQ", "Price variances are on actual quantity.", kind="case", group=G2)

mix_ap = sum((RSQ[k] - acts[k][0]) * acts[k][1] for k in mixs)
B.add(S("matvar"), "L4", st2 + "\n\n**Q.** The material mix variance is:",
      V(mixv),
      [(V(mix_ap), "mix valued at actual prices"),
       (V(usev), "total usage variance reported as mix"),
       (V(-mixv), "direction reversed")],
      [f"Actual input = {inr(AQ)} kg; revised standard mix 60 : 40 → A {inr(RSQ['A'])}, B {inr(RSQ['B'])}",
       f"A: ({inr(RSQ['A'])} − {inr(acts['A'][0])}) × {mixs['A'][1]} = {V((RSQ['A']-acts['A'][0])*mixs['A'][1])}",
       f"B: ({inr(RSQ['B'])} − {inr(acts['B'][0])}) × {mixs['B'][1]} = {V((RSQ['B']-acts['B'][0])*mixs['B'][1])}",
       f"Mix = {V(mixv)}"],
      "Mix = Σ (RSQ − AQ) × SP; RSQ = Actual total input in standard ratio",
      "Using more of the dearer material B makes the mix adverse even though A used equals standard.", kind="case", group=G2)

std_out_from_aq = AQ * std_out / std_in
B.add(S("matvar"), "L4", st2 + "\n\n**Q.** The material yield variance is:",
      V(yldv),
      [(V((aout / std_out * std_in - AQ) * std_cost_out), "input shortfall valued at standard cost per kg of OUTPUT"),
       (V((aout - std_out_from_aq) * avg_in), "output shortfall valued at standard cost per kg of INPUT"),
       (V(usev), "total usage variance reported")],
      [f"Standard input for actual output = {inr(aout)} × {std_in}/{std_out} = {inr(aout/std_out*std_in)} kg; actual input {inr(AQ)} kg",
       f"Standard cost per kg of input = ₹{avg_in:g} (per kg of output ₹{std_cost_out:.2f})",
       f"Yield = ({inr(aout/std_out*std_in)} − {inr(AQ)}) × {avg_in:g} = {V(yldv)}",
       f"Equivalently: ({inr(aout)} − {inr(std_out_from_aq)}) × {std_cost_out:.4f} = {V(yldv)}; mix + yield = usage {V(usev)}"],
      "Yield = (SQ total − AQ total) × Std avg cost per kg input",
      "Match the base: input shortfall × input cost, or output shortfall × output cost.", kind="case", group=G2)

B.add(S("labvar"), "L4", st2 + "\n\n**Q.** The labour efficiency variance is:",
      V(leff),
      [(V((lsh - lh_paid) * lr_std), "idle hours included in hours worked"),
       (V((lsh - lwork) * lr_act), "valued at actual rate"),
       (V(-lidle * lr_std), "idle time variance reported")],
      [f"Standard hours = {inr(aout)} × {lh_std} = {inr(lsh)}",
       f"Hours worked = {inr(lh_paid)} − {lidle} = {inr(lwork)}",
       f"Efficiency = ({inr(lsh)} − {inr(lwork)}) × {lr_std} = {V(leff)}",
       f"(Rate {V((lr_std-lr_act)*lh_paid)}; idle time {V(-lidle*lr_std)})"],
      "LEV = (SH − Hours worked) × SR", "Abnormal idle time is a separate variance.", kind="case", group=G2)

# ---- Case 3: Flexible budget, sales and overhead variances ----
bu, bsp, bvc, voh_h, shu, bfo = 10000, 500, 300, 20, 2, 1200000
foh_u = bfo / bu; foh_h = bfo / (bu * shu); bmargin = bsp - bvc - foh_u
au, asp, ahh, avoh, afoh = 9200, 510, 19000, 370500, 1230000
ash = au * shu
flex_cost = au * bvc + bfo
svv = (au - bu) * bmargin
vexp = ahh * voh_h - avoh; veff = (ash - ahh) * voh_h
ftot = au * foh_u - afoh; feff = (ash - ahh) * foh_h; fcap = (ahh - bu * shu) * foh_h
assert svv == -64000 and vexp == 9500 and veff == -12000 and ftot == -126000 and feff == -36000
G3 = "CST-CASE-FLEX"
st3 = ("**Case — Kaveri Tools Ltd (fictional), June** — standard absorption costing\n\n"
       "| Budget / standard | |\n|---|---|\n"
       f"| Budgeted output and sales | {inr(bu)} units |\n| Standard selling price | ₹{bsp} per unit |\n"
       f"| Standard variable cost | ₹{bvc} per unit (includes variable overhead at ₹{voh_h} per hour, {shu} hours per unit) |\n"
       f"| Budgeted fixed overhead | {R(bfo)} (absorbed per standard hour) |\n\n"
       "| Actual | |\n|---|---|\n"
       f"| Output produced and sold | {inr(au)} units at ₹{asp} |\n| Labour hours worked | {inr(ahh)} |\n"
       f"| Variable overhead | {R(avoh)} |\n| Fixed overhead | {R(afoh)} |")
B.add(S("flex"), "L4", st3 + "\n\n**Q.** The flexed budget total cost for the actual output is:",
      R(flex_cost),
      [(R(au * (bvc + foh_u)), "fixed overhead flexed with output"),
       (R(bu * bvc + bfo), "original (fixed) budget cost not flexed"),
       (R(au * (bvc - shu * voh_h) + ahh * voh_h + bfo), "variable overhead flexed on actual hours instead of output")],
      [f"Variable: {inr(au)} × ₹{bvc} = {inr(au*bvc)}",
       f"Fixed overhead stays at {inr(bfo)}",
       f"Flexed budget cost = {R(flex_cost)}"],
      "Flexed cost = Standard variable cost × Actual output + Budgeted fixed cost",
      "Fixed costs are not flexed; flex on output, not input hours.", kind="case", group=G3)

B.add(S("salesvar"), "L4", st3 + "\n\n**Q.** The sales volume (profit) variance is:",
      V(svv),
      [(V((au - bu) * (bsp - bvc)), "contribution margin used (marginal-costing basis)"),
       (V((au - bu) * bsp), "turnover (sales value) basis"),
       (V((au - bu) * (asp - bvc - foh_u)), "valued at actual-price margin")],
      [f"Standard profit per unit = {bsp} − {bvc} − {foh_u:g} (fixed OH) = ₹{bmargin:g}",
       f"Volume variance = ({inr(au)} − {inr(bu)}) × {bmargin:g} = {V(svv)}",
       f"(Price variance = ({asp} − {bsp}) × {inr(au)} = {V((asp-bsp)*au)})"],
      "Sales volume variance (absorption) = (AQ − BQ) × Standard profit per unit",
      "Absorption costing uses standard PROFIT per unit; marginal costing uses contribution.", kind="case", group=G3)

B.add(S("ohvar"), "L4", st3 + "\n\n**Q.** The variable overhead expenditure and efficiency variances are:",
      f"Expenditure {V(vexp)}; efficiency {V(veff)}",
      [(f"Expenditure {V(ash*voh_h-avoh)}; efficiency {V(veff)}", "expenditure allowance based on standard hours"),
       (f"Expenditure {V(-vexp)}; efficiency {V(-veff)}", "directions reversed"),
       (f"Expenditure {V(vexp)}; efficiency {V((ash-ahh)*avoh/ahh)}", "efficiency valued at actual rate per hour")],
      [f"Standard hours for actual output = {inr(au)} × {shu} = {inr(ash)}",
       f"Expenditure = {inr(ahh)} × {voh_h} − {inr(avoh)} = {V(vexp)}",
       f"Efficiency = ({inr(ash)} − {inr(ahh)}) × {voh_h} = {V(veff)}"],
      "VOH exp = AH × SR − Actual; VOH eff = (SH − AH) × SR",
      "Favourable spending can coexist with adverse efficiency.", kind="case", group=G3)

B.add(S("ohvar"), "L4", st3 + "\n\n**Q.** The total fixed overhead cost variance and the fixed overhead efficiency variance are:",
      f"Total {V(ftot)}; efficiency {V(feff)}",
      [(f"Total {V(ftot)}; efficiency {V(fcap)}", "capacity variance reported as efficiency"),
       (f"Total {V(bfo-afoh)}; efficiency {V(feff)}", "expenditure variance reported as total"),
       (f"Total {V(ftot)}; efficiency {V(veff)}", "variable overhead efficiency reported")],
      [f"Rate = {inr(bfo)} ÷ {inr(bu*shu)} = ₹{foh_h:g} per hour (₹{foh_u:g} per unit)",
       f"Absorbed = {inr(au)} × {foh_u:g} = {inr(au*foh_u)}; total = {inr(au*foh_u)} − {inr(afoh)} = {V(ftot)}",
       f"Efficiency = ({inr(ash)} − {inr(ahh)}) × {foh_h:g} = {V(feff)}; capacity = ({inr(ahh)} − {inr(bu*shu)}) × {foh_h:g} = {V(fcap)}",
       f"Expenditure {V(bfo-afoh)} + capacity {V(fcap)} + efficiency {V(feff)} = {V(ftot)}"],
      "Total FOH = Absorbed − Actual = Expenditure + Capacity + Efficiency",
      "Efficiency uses standard vs actual hours; capacity uses actual vs budgeted hours.", kind="case", group=G3)

# ---- Case 4: Activity-based costing ----
P = {"Standard": dict(u=20000, mh=1, bs=500, ins=2, prime=0), "Deluxe": dict(u=2000, mh=2, bs=100, ins=3, prime=440)}
pools = {"Machining": 480000, "Set-ups": 360000, "Inspection": 210000}
for k in P:
    P[k]["b"] = P[k]["u"] / P[k]["bs"]; P[k]["i"] = P[k]["b"] * P[k]["ins"]; P[k]["M"] = P[k]["u"] * P[k]["mh"]
TMH = sum(p["M"] for p in P.values()); TB = sum(p["b"] for p in P.values()); TI = sum(p["i"] for p in P.values())
rm, rs, ri = pools["Machining"] / TMH, pools["Set-ups"] / TB, pools["Inspection"] / TI
assert rm == 20 and rs == 6000 and ri == 1500
abc = {k: (p["M"] * rm + p["b"] * rs + p["i"] * ri) / p["u"] for k, p in P.items()}
TOH = sum(pools.values()); trad_r = TOH / TMH
trad = {k: trad_r * p["mh"] for k, p in P.items()}
assert abc["Deluxe"] == 145 and abc["Standard"] == 38
assert isclose(sum(abc[k] * P[k]["u"] for k in P), TOH)
TU = sum(p["u"] for p in P.values())
G4 = "CST-CASE-ABC"
st4 = ("**Case — Meghna Instruments Ltd (fictional)**\n\n"
       "| | Standard | Deluxe |\n|---|---:|---:|\n"
       f"| Annual output (units) | {inr(P['Standard']['u'])} | {inr(P['Deluxe']['u'])} |\n"
       f"| Machine hours per unit | {P['Standard']['mh']} | {P['Deluxe']['mh']} |\n"
       f"| Batch size (units; one set-up per batch) | {P['Standard']['bs']} | {P['Deluxe']['bs']} |\n"
       f"| Inspections per batch | {P['Standard']['ins']} | {P['Deluxe']['ins']} |\n\n"
       "| Cost pool | ₹ | Driver |\n|---|---:|---|\n"
       f"| Machining | {inr(pools['Machining'])} | Machine hours |\n| Set-ups | {inr(pools['Set-ups'])} | Number of set-ups |\n| Inspection | {inr(pools['Inspection'])} | Number of inspections |\n\n"
       f"At present all overhead ({R(TOH)}) is absorbed on a single plant-wide machine-hour rate.")
d = P["Deluxe"]
B.add(S("abc"), "L4", st4 + "\n\n**Q.** Overhead cost per unit of Deluxe under activity-based costing is:",
      Rd(abc["Deluxe"]),
      [(Rd(trad["Deluxe"]), "plant-wide machine-hour rate (traditional)"),
       (Rd((d["M"] * rm + pools["Set-ups"] * d["u"] / TU + d["i"] * ri) / d["u"]), "set-up pool spread on units instead of set-ups"),
       (Rd((d["M"] * rm + d["b"] * rs + d["b"] * pools["Inspection"] / TB) / d["u"]), "inspection pool driven by batches instead of inspections")],
      [f"Driver rates: machining {inr(pools['Machining'])} ÷ {inr(TMH)} MH = ₹{rm:g}; set-ups {inr(pools['Set-ups'])} ÷ {TB:g} = ₹{inr(rs)}; inspection {inr(pools['Inspection'])} ÷ {TI:g} = ₹{inr(ri)}",
       f"Deluxe: {d['b']:g} batches, {d['i']:g} inspections, {inr(d['M'])} MH",
       f"Cost = {inr(d['M']*rm)} + {inr(d['b']*rs)} + {inr(d['i']*ri)} = {inr(d['M']*rm+d['b']*rs+d['i']*ri)} ÷ {inr(d['u'])} = {Rd(abc['Deluxe'])}"],
      "ABC cost per unit = Σ (Driver rate × Driver quantity) ÷ Units",
      "Low-volume Deluxe consumes far more set-ups and inspections per unit.", kind="case", group=G4)

diff = trad["Standard"] - abc["Standard"]
B.add(S("abc"), "L4", st4 + "\n\n**Q.** Compared with ABC, the traditional system costs each unit of Standard:",
      f"Higher by {Rd(diff)}",
      [(f"Lower by {Rd(diff)}", "direction reversed"),
       (f"Higher by {Rd(trad['Standard'] - rm * P['Standard']['mh'])}", "only the machining element of ABC deducted"),
       (f"Higher by {Rd(TOH / TU - abc['Standard'])}", "traditional rate taken per unit produced instead of per machine hour")],
      [f"Traditional rate = {inr(TOH)} ÷ {inr(TMH)} MH = ₹{trad_r:g} → Standard ₹{trad['Standard']:g}",
       f"ABC Standard = machining ₹{rm:g} + set-ups ₹{P['Standard']['b']*rs/P['Standard']['u']:g} + inspection ₹{P['Standard']['i']*ri/P['Standard']['u']:g} = ₹{abc['Standard']:g}",
       f"Over-costing = ₹{diff:g} per unit (≈ {inr(diff*P['Standard']['u'])} in total, shifted from Deluxe)"],
      "Cross-subsidy = Traditional cost − ABC cost",
      "Volume-based rates over-cost high-volume simple products.", kind="case", group=G4)

B.add(S("abc"), "L4", st4 + "\n\n**Q.** Consider the following statements:\n\n1. Set-up costs in this case are batch-level costs and vary with the number of batches, not with units produced.\n"
      "2. The single machine-hour rate causes Standard to subsidise Deluxe.\n3. Under ABC, facility-sustaining costs such as factory security should be traced to products using unit-level drivers.\n\n"
      "Which of the statements given above is/are correct?",
      "1 and 2 only",
      [("1, 2 and 3", "facility-sustaining costs assumed traceable by unit drivers"),
       ("1 only", "misses the cross-subsidy shown by the figures"),
       ("2 and 3 only", "rejects the batch-level nature of set-ups")],
      ["Cost hierarchy: unit-level, batch-level, product-sustaining, facility-sustaining.",
       f"Set-ups vary with batches (statement 1). Standard is over-costed by ₹{diff:g}/unit, i.e. it subsidises Deluxe (statement 2).",
       "Facility-sustaining costs have no cause-and-effect driver; they are usually left unallocated or allocated arbitrarily (statement 3 false)."],
      "ABC cost hierarchy", "Facility-level costs have no product-level driver.", kind="case", group=G4)

mk = 0.25
price_abc = (d["prime"] + abc["Deluxe"]) * (1 + mk)
B.add(S("abc"), "L4", st4 + f"\n\n**Q.** Deluxe has a prime cost of ₹{d['prime']} per unit. Pricing at total cost plus {pct(mk,0)} mark-up on cost, the price of Deluxe using ABC overhead is:",
      Rd(price_abc),
      [(Rd((d["prime"] + trad["Deluxe"]) * (1 + mk)), "traditional overhead rate used"),
       (Rd((d["prime"] + abc["Deluxe"]) / (1 - mk)), "25% treated as margin on price"),
       (Rd(d["prime"] * (1 + mk) + abc["Deluxe"]), "mark-up applied to prime cost only")],
      [f"ABC total cost = {d['prime']} + {abc['Deluxe']:g} = ₹{d['prime']+abc['Deluxe']:g}",
       f"Price = {d['prime']+abc['Deluxe']:g} × 1.25 = {Rd(price_abc)}",
       f"(Traditional basis would give {Rd((d['prime']+trad['Deluxe'])*(1+mk))} — under-pricing Deluxe)"],
      "Price = (Prime cost + ABC overhead) × (1 + mark-up)",
      "Under-costed products get under-priced under traditional absorption.", kind="case", group=G4)

# ---------------- checks + output ----------------
from collections import Counter
assert len(B.Q) == 80, len(B.Q)
lv = Counter(q["rubric_level"] for q in B.Q)
assert lv == {"L1": 16, "L2": 24, "L3": 24, "L4": 16}, lv
excluded = {"marginal-costing-contribution-and-p-v-ratio", "break-even-point-in-units-and-value", "margin-of-safety-and-angle-of-incidence",
            "target-profit-sales", "key-factor-and-product-mix-decisions", "make-or-buy-and-shutdown-decisions",
            "absorption-vs-marginal-costing-profit-reconciliation"}
used = {q["microtopic_slug"] for q in B.Q}
for s in used:
    assert not any(e in s for e in excluded), s
missing = [s for s in B.cat if s not in used and not any(e in s for e in excluded)]
assert not missing, missing
B.write()
