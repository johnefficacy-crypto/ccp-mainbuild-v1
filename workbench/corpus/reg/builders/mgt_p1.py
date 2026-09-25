"""MGT part 1 — nature of management, schools, managerial roles/skills, functions, Fayol/Taylor,
planning, organising, directing, controlling, environment analysis, process improvement, CPM/PERT."""
import math
from mgt_common import cq, nq, stmt, ar, match, inr, R, pct, lakh


def pert_net(acts):
    """acts: {name: (preds, a, m, b)} -> te, var, ES, EF, LS, LF, T."""
    te = {k: (a + 4 * mm + b) / 6 for k, (_, a, mm, b) in acts.items()}
    var = {k: ((b - a) / 6) ** 2 for k, (_, a, mm, b) in acts.items()}
    ES, EF = {}, {}
    for k in acts:  # insertion order is topological
        ES[k] = max([EF[p] for p in acts[k][0]], default=0)
        EF[k] = ES[k] + te[k]
    T = max(EF.values())
    LF, LS = {}, {}
    for k in reversed(list(acts)):
        succ = [s for s in acts if k in acts[s][0]]
        LF[k] = min([LS[s] for s in succ], default=T)
        LS[k] = LF[k] - te[k]
    return te, var, ES, EF, LS, LF, T


def add_all(B):
    # ================================================================ nature of management
    cq(B, "administration-vs-management", "L1",
       "According to Oliver Sheldon's classical distinction, **administration** is primarily concerned with:",
       "Framing policy and the overall objectives within which management operates",
       [("Executing policies through direction and supervision of operative staff", "reverses Sheldon — that is his 'management'"),
        ("Recruitment, selection, training and placement of employees at all levels", "confuses administration with the staffing function"),
        ("Day-to-day control of production and costs against set standards", "describes lower-level operational control")],
       ["Sheldon (1923): administration = determinative, policy-framing, top-level 'thinking' function.",
        "Management = executive function that puts that policy into action within the limits set."],
       "In the Sheldon/American view administration sits above management; in the British (Brech) view management is the wider term.")

    stmt(B, "administration-vs-management", "L2",
         "Consider the following statements on administration and management:",
         [("The term 'administration' is more commonly used in government and non-profit bodies, while 'management' is more common in business enterprises", True,
           "usage distinction widely accepted"),
          ("In the British view (E.F.L. Brech), administration is the wider term and management is only a part of it", False,
           "Brech treated management as the wider, generic term and administration as a part of management"),
          ("Administration is largely influenced by public opinion and government policy, while management decisions are shaped more by owners' objectives", True,
           "standard basis-of-distinction point")],
         "Students often attach the American (Sheldon) view to Brech; Brech is the British view where management is the broader process.")

    cq(B, "classical-neoclassical", "L1",
       "The Hawthorne experiments, which showed that social and psychological factors influence worker productivity, are the foundation of which school of management thought?",
       "Neoclassical (human relations) school",
       [("Classical school", "classical school (Taylor, Fayol, Weber) focused on structure and efficiency, not social factors"),
        ("Systems approach", "systems thinking (Barnard, Katz & Kahn) came later and views the organisation as an open system"),
        ("Quantitative (management science) school", "uses operations research models, not behavioural findings")],
       ["Elton Mayo and associates, Western Electric's Hawthorne Works (1924–32).",
        "Finding: attention, group norms and informal relations affect output more than physical conditions alone.",
        "This launched the human relations / neoclassical school."],
       "Behavioural science school (Maslow, McGregor, Argyris) built on — but is distinct from — the human relations findings.")

    match(B, "classical-neoclassical", "L3",
          "Match the thinker with the contribution:",
          ["Max Weber", "Chester Barnard", "Joan Woodward", "Mary Parker Follett"],
          ["Ideal-type bureaucracy based on rational-legal authority",
           "Acceptance theory of authority",
           "Structure depends on production technology (contingency view)",
           "Integration as the constructive way of resolving conflict"],
          [1, 2, 3, 4],
          [((1, 3), "swaps Barnard and Follett — both wrote on authority/cooperation, but acceptance theory is Barnard's"),
           ((0, 1), "attributes acceptance theory to Weber, who built on legitimate (rational-legal) authority"),
           ((2, 3), "confuses Woodward's technology-structure studies with Follett's conflict integration")],
          ["Weber — bureaucracy (rules, hierarchy, impersonality).", "Barnard — The Functions of the Executive (1938): authority rests on acceptance by subordinates.",
           "Woodward — South Essex studies: unit, mass and process production need different structures.",
           "Follett — conflict resolved best by integration rather than domination or compromise."],
          "Barnard and Follett are both 'bridge' thinkers; anchor Barnard to acceptance theory and Follett to integration.")

    cq(B, "classical-neoclassical", "L2",
       "A payments company redesigns its structure: the card-processing unit (stable, routine) keeps a tall, rule-bound hierarchy, while the product innovation lab (volatile market) is given a flat, flexible team structure. The management thinking reflected here is closest to:",
       "Contingency approach — there is no one best way; structure should fit the situation",
       [("Classical approach — a single best way of organising applies to every unit", "classical school prescribes universal principles"),
        ("Human relations approach — structure should follow informal group preferences", "human relations focuses on social needs, not fit between structure and environment"),
        ("Scientific management — structure is fixed through time-and-motion study", "Taylor's method is for task design, not organisation design")],
       ["Two different structures inside one firm, each matched to its environment/technology.",
        "Burns & Stalker (mechanistic vs organic) and Lawrence & Lorsch — the contingency view."],
       "The key phrase is 'no one best way'; the systems approach explains interdependence but the fit logic is contingency.")

    cq(B, "management-as-science-and-art", "L1",
       "Management is best described as:",
       "An inexact (behavioural) science as well as an art",
       [("An exact science like physics", "management principles deal with human behaviour and are not universally precise"),
        ("Purely an art based on personal skill with no principles", "ignores the systematised body of knowledge and principles"),
        ("A full-fledged profession with a statutory licence for practice", "management lacks restricted entry and a single statutory licensing body")],
       ["Science: systematic body of knowledge, principles derived from observation — but results vary with people and situations.",
        "Art: personalised application of knowledge and skill; improves with practice.",
        "Hence management = science and art; they are complementary."],
       "Do not say 'exact science'; do not jump to 'profession' — it has some but not all features of a profession.")

    ar(B, "management-as-science-and-art", "L2",
       "Management is regarded as an inexact science.",
       "Its principles deal with human behaviour, so the same principle may not yield the same result in every situation.",
       0,
       ["A is true — management principles are not as universally valid as laws of physical science.",
        "R is true and states exactly why: human behaviour is variable and situational.",
        "So R correctly explains A."],
       "Candidates often pick option (b) thinking any reason offered is 'general'; here R is the precise cause.")

    cq(B, "levels-of-management", "L1",
       "Interpreting top-level policies, assigning duties to supervisors and coordinating the activities of different departments are primarily functions of:",
       "Middle-level management",
       [("Top-level management", "top level frames objectives and policies; it does not interpret them for units"),
        ("Supervisory / operational management", "supervisors direct operative workers, not other supervisors"),
        ("Board of directors acting as a committee", "the board sets direction and oversees; it does not assign supervisory duties")],
       ["Middle management links top and lower levels.",
        "Tasks: interpret policy, staff and organise the department, assign duties to supervisors, coordinate departments."],
       "'Coordinating departments' tempts candidates towards top management — but day-to-day departmental coordination is middle-level.")

    ops, s1, s2 = 4096, 8, 16

    def mgrs(n, s):
        tot, lv = 0, 0
        while n > 1:
            n = math.ceil(n / s); tot += n; lv += 1
        return tot, lv
    m1, l1 = mgrs(ops, s1); m2, l2 = mgrs(ops, s2)
    assert (m1, l1, m2, l2) == (585, 4, 273, 3)
    nq(B, "levels-of-management", "L3",
       f"An operations centre has {inr(ops)} operative staff. Every manager (at every level) supervises exactly {s1} subordinates, up to a single head. "
       f"If the span of control is widened uniformly to {s2}, what happens to the number of managerial posts and the number of managerial levels?",
       f"Managers fall by {m1-m2}; levels fall from {l1} to {l2}",
       [(f"Managers fall by {ops//s1 - ops//s2}; levels fall from {l1} to {l2}", "compares only the first-line supervisory layer"),
        (f"Managers fall by {m1-m2}; levels remain {l1}", "ignores that a wider span collapses a level"),
        (f"Managers fall by {m1 - m1//2}; levels fall from {l1} to {l1//2}", "assumes doubling the span halves both managers and levels")],
       [f"Span {s1}: {ops}/8 = 512, 512/8 = 64, 64/8 = 8, 8/8 = 1 → {m1} managers in {l1} levels.",
        f"Span {s2}: {ops}/16 = 256, 256/16 = 16, 16/16 = 1 → {m2} managers in {l2} levels.",
        f"Reduction = {m1} − {m2} = {m1-m2}."],
       "Managers at level k = Operatives ÷ span^k; sum over levels until 1",
       "A wider span gives a flatter structure — fewer posts AND fewer levels; the reduction is not a simple halving.")

    cq(B, "katz", "L1",
       "According to Robert L. Katz, which managerial skill becomes relatively MORE important as a manager moves up to the top level?",
       "Conceptual skill",
       [("Technical skill", "technical skill is most important at the supervisory level and declines upwards"),
        ("Human skill", "Katz held human skill to be roughly equally important at all levels"),
        ("Diagnostic skill", "a later addition by other authors, not one of Katz's three skills")],
       ["Katz (HBR, 1955): technical, human, conceptual.", "Conceptual skill — seeing the enterprise as a whole — dominates at the top."],
       "'Human skill matters most at the top' is the classic wrong pick; Katz treats it as essential at every level.")

    cq(B, "katz", "L2",
       "When the regulator revises the risk-weight on unsecured loans, Meera, a zonal head of a bank, immediately works out how the change will affect credit growth, branch targets, capital planning and the collections team, and how these units interact. Meera is displaying mainly:",
       "Conceptual skill",
       [("Technical skill", "she is not performing the specialised calculation/procedure herself"),
        ("Human skill", "the scenario is about seeing interrelationships, not working with or motivating people"),
        ("Design skill of the specialist type only", "design (problem-solving) skill is a later add-on and is narrower than seeing the organisation as a whole")],
       ["Conceptual skill = ability to see the organisation as a whole and how its parts depend on one another and on the environment.",
        "Meera maps one external change onto all interdependent units."],
       "Analytical-sounding tasks are not automatically 'technical'; technical skill concerns methods and procedures of a specialised activity.")

    stmt(B, "katz", "L3",
         "With reference to Katz's three-skill approach, consider:",
         [("Technical skill is most important for first-line supervisors who directly guide operative work", True, "technical proficiency needed to instruct and check work"),
          ("Human skill is required at all levels because every manager works with and through people", True, "Katz: human skill is essential across levels"),
          ("Conceptual skill can be dispensed with at the supervisory level since it is exercised only by the board", False,
           "Katz saw conceptual skill as needed in some measure at every level; it only becomes relatively more important higher up"),
          ("Katz later argued that at the very top, conceptual skill can compensate for a lack of technical skill", True,
           "his 1974 retrospective noted top executives can manage with limited technical skill if conceptual/human skills are strong")],
         "The 'relative importance' pattern is about proportions, not presence/absence of a skill at a level.")

    cq(B, "mintzberg-interpersonal", "L2",
       "The managing director of an asset management company inaugurates a new investor-service centre, signs statutory certificates, and hosts a long-service award function. These activities illustrate Mintzberg's:",
       "Figurehead role",
       [("Liaison role", "liaison is maintaining a network of outside contacts for information/favours"),
        ("Spokesperson role", "spokesperson transmits information about the organisation to outsiders"),
        ("Leader role", "leader role concerns motivating, staffing and guiding subordinates")],
       ["Figurehead: symbolic, ceremonial, legal duties performed because of the position.",
        "Inaugurations, signing documents and hosting ceremonies are the textbook examples."],
       "Figurehead vs spokesperson: ceremony and symbolism (figurehead) vs conveying information outward (spokesperson, an informational role).")

    cq(B, "mintzberg-informational", "L2",
       "Every morning the compliance head of a stockbroking firm scans the regulator's circulars, exchange notices, rival firms' disclosures and internal exception reports to stay aware of what is happening. In Mintzberg's framework this is the:",
       "Monitor role",
       [("Disseminator role", "disseminator passes information to subordinates inside the organisation"),
        ("Spokesperson role", "spokesperson sends information to outsiders"),
        ("Liaison role", "liaison builds external contacts; the monitor role is the seeking/receiving of information")],
       ["Informational roles: monitor (seeks & receives), disseminator (passes inside), spokesperson (transmits outside).",
        "Scanning and gathering = monitor."],
       "Information coming IN = monitor; going to insiders = disseminator; going OUT = spokesperson.")

    match(B, "mintzberg-informational", "L3",
          "Match the managerial activity with Mintzberg's role:",
          ["Briefs the media on the quarterly results", "Keeps up a network of contacts in other exchanges and industry bodies",
           "Reads regulatory circulars and market data to track developments", "Bargains with the employees' union on a wage settlement"],
          ["Liaison", "Monitor", "Negotiator", "Spokesperson"],
          [4, 1, 2, 3],
          [((0, 1), "confuses spokesperson (informing outsiders) with liaison (maintaining outside contacts)"),
           ((1, 2), "confuses liaison (network building, interpersonal) with monitor (information seeking)"),
           ((0, 2), "confuses spokesperson (outward flow) with monitor (inward flow)")],
          ["Media briefing → spokesperson (informational).", "External network → liaison (interpersonal).",
           "Scanning circulars → monitor (informational).", "Union bargaining → negotiator (decisional)."],
          "Liaison is interpersonal even though it yields information; the information-handling itself is monitor/disseminator/spokesperson.")

    cq(B, "mintzberg-decisional", "L2",
       "A sudden system outage halts trading at a broker's branch network. The operations head sets aside her plans, convenes an emergency team and takes corrective decisions to restore services. Mintzberg would classify this as the:",
       "Disturbance handler role",
       [("Entrepreneur role", "entrepreneur initiates planned, voluntary change and improvement projects"),
        ("Resource allocator role", "resource allocator decides who gets what resources as a routine matter"),
        ("Monitor role", "monitor is an informational role, not corrective decision-making")],
       ["Decisional roles: entrepreneur, disturbance handler, resource allocator, negotiator.",
        "Responding to unexpected crises/pressures beyond immediate control = disturbance handler."],
       "Planned change = entrepreneur; involuntary, unexpected change = disturbance handler.")

    stmt(B, "mintzberg-decisional", "L3",
         "With reference to Mintzberg's managerial roles, consider:",
         [("Scheduling one's own time and approving the budgets of units are part of the resource allocator role", True,
           "Mintzberg includes the manager's own time among resources allocated"),
          ("The entrepreneur role is limited to starting a new business venture", False,
           "in Mintzberg's sense it means initiating improvement projects and change within the organisation"),
          ("Mintzberg grouped his ten roles into interpersonal, informational and decisional categories", True, "The Nature of Managerial Work (1973)"),
          ("Negotiator is an interpersonal role because it involves dealing with people", False,
           "negotiator is a decisional role — the manager commits organisational resources in real time")],
         "Roles are classified by what the manager does with authority/information, not merely by whether people are involved.")

    cq(B, "koontz", "L1",
       "Koontz and O'Donnell classified the functions of a manager as:",
       "Planning, organising, staffing, directing (leading) and controlling",
       [("Planning, organising, commanding, coordinating and controlling", "this is Fayol's POCCC"),
        ("Planning, organising, staffing, directing, coordinating, reporting and budgeting", "this is Gulick's POSDCORB"),
        ("Forecasting, organising, motivating, communicating and controlling", "mixes elements of directing into a non-standard list")],
       ["Koontz & O'Donnell: five functions P-O-S-D-C.", "Coordination is treated as the essence of management, not a separate function."],
       "Know the three lists apart: Fayol (POCCC), Gulick (POSDCORB), Koontz & O'Donnell (POSDC).")

    ar(B, "koontz", "L2",
       "Koontz and O'Donnell did not list coordination as a separate function of management.",
       "They regarded coordination as the essence of managership, achieved through the performance of all managerial functions.",
       0,
       ["A true — their five functions omit coordination as a separate item.",
        "R true — coordination is 'the essence of managership'; each function contributes to it.",
        "R is exactly why they left it out as a separate function."],
       "Fayol did list coordination separately; Koontz & O'Donnell absorbed it into all functions.")

    cq(B, "linking-function", "L2",
       "Rensis Likert described managers as 'linking pins' in an organisation. This means that each manager:",
       "Heads his own work group and is also a member of his superior's group, linking the two",
       [("Links the organisation with outside stakeholders such as regulators and suppliers", "that is the boundary-spanning/liaison idea, not Likert's linking pin"),
        ("Acts only as a one-way messenger carrying the board's decisions down to all workers", "reduces the linking pin to one-way transmission"),
        ("Links the formal organisation to the informal grapevine so that rumours are controlled", "Likert's model links overlapping formal work groups")],
       ["Likert (System 4, participative): organisation = overlapping groups.",
        "Each manager belongs to a lower group (as leader) and a higher group (as member) — the linking pin."],
       "Do not confuse Likert's vertical linking pin with Mintzberg's liaison role (external network).")

    stmt(B, "linking-function", "L3",
         "Regarding the linking function of a manager, consider:",
         [("A middle manager links top management's objectives with the operative level by translating them into departmental targets", True, "vertical linking"),
          ("A manager also links the organisation with its external environment — customers, suppliers, regulators", True, "boundary / environmental linking"),
          ("Likert's linking-pin model is associated with his exploitative-authoritative System 1", False,
           "the linking-pin model belongs to System 4 (participative group)"),],
         "Likert's four systems run from exploitative-authoritative (1) to participative-group (4); the linking pin is a System 4 feature.")

    cq(B, "drucker-on-management", "L1",
       "Peter Drucker's distinction between efficiency and effectiveness is best captured by:",
       "Efficiency is doing things right; effectiveness is doing the right things",
       [("Efficiency is doing the right things; effectiveness is doing things right", "the two are reversed"),
        ("Efficiency concerns outputs; effectiveness concerns inputs", "efficiency is the input-output ratio; effectiveness is goal achievement"),
        ("Efficiency is a leader's concern; effectiveness is a manager's concern", "mixes in the Bennis leader-manager quote")],
       ["Efficiency = optimum use of resources (ratio of output to input).", "Effectiveness = achieving the right goals."],
       "Bennis used a similar line for manager vs leader; Drucker's line is about efficiency vs effectiveness.")

    stmt(B, "drucker-on-management", "L3",
         "According to Peter Drucker, consider:",
         [("Management is a multi-purpose organ that manages a business, manages managers, and manages workers and work", True, "The Practice of Management (1954)"),
          ("The only valid purpose of a business is to create a customer", True, "Drucker's classic formulation"),
          ("Setting objectives, organising, motivating and communicating, measuring, and developing people are the basic operations of a manager", True,
           "Drucker's five basic operations"),
          ("Management by objectives was first proposed by Drucker as a purely top-down system of assigned targets", False,
           "Drucker proposed 'management by objectives and self-control', with managers participating in setting their own objectives")],
         "MBO in Drucker's original form stresses self-control and participation, not imposed targets.")

    cq(B, "primary-functions-of-management", "L1",
       "In the commonly accepted sequence of the primary functions of management, the function that immediately follows organising is:",
       "Staffing",
       [("Directing", "directing follows staffing — people must be in position first"),
        ("Controlling", "controlling comes last"),
        ("Coordinating", "coordination runs through all functions rather than following organising")],
       ["Sequence: planning → organising → staffing → directing → controlling.",
        "Organising creates positions; staffing fills them."],
       "Coordination is the essence of management, not a step in the sequence.")

    cq(B, "primary-functions-of-management", "L2",
       "At the quarterly review, the credit head of a small finance bank compares actual gross NPA of 4.8% against the budgeted 4.0%, analyses reasons branch by branch, and orders tighter follow-up of overdue accounts. Which management function is being performed?",
       "Controlling",
       [("Planning", "the target (4.0%) was set earlier; here performance is being measured against it"),
        ("Directing", "issuing the follow-up order is part of the corrective step of controlling, not the main function here"),
        ("Organising", "no change in structure, roles or authority relationships")],
       ["Controlling steps: set standards → measure → compare → analyse deviation → corrective action.",
        "The whole sequence is visible in the scenario."],
       "Corrective action involves instructions, but the function driving it is controlling.")

    cq(B, "fayol-s-functions", "L1",
       "Which of the following is NOT one of the five elements of management identified by Henri Fayol?",
       "Staffing",
       [("Coordinating", "Fayol did list coordination (one of POCCC)"),
        ("Commanding", "commanding is Fayol's term for directing"),
        ("Planning (prévoyance)", "forecasting and planning is Fayol's first element")],
       ["Fayol: planning, organising, commanding, coordinating, controlling (POCCC).",
        "Staffing was added separately by later writers (Gulick, Koontz & O'Donnell)."],
       "Fayol lists coordination but not staffing; Koontz & O'Donnell list staffing but not coordination.")

    stmt(B, "fayol-s-functions", "L3",
         "Fayol classified the activities of an industrial undertaking into six groups. Consider:",
         [("Protection of property and persons falls under 'security activities'", True, "security = protection of property and persons"),
          ("Raising and optimum use of capital falls under 'commercial activities'", False,
           "that is 'financial activities'; commercial = buying, selling and exchange"),
          ("Stocktaking, balance sheet, costing and statistics fall under 'accounting activities'", True, "Fayol's accounting group"),
          ("Managerial activities comprise planning, organising, commanding, coordinating and controlling", True, "the sixth group")],
         "Commercial (buying/selling) and financial (capital) are separate Fayol groups.")

    cq(B, "fayol-s-14", "L1",
       "Fayol's principle of 'esprit de corps' emphasises:",
       "Promoting team spirit, harmony and unity among the staff — 'union is strength'",
       [("Each employee should receive orders from one superior only", "that is unity of command"),
        ("A place for everything and everyone, and everything and everyone in its place", "that is the principle of order"),
        ("Employees should be encouraged to think out and execute plans", "that is the principle of initiative")],
       ["Esprit de corps: management should foster team spirit and cohesion; replace 'I' with 'we'.",
        "Fayol warned against 'divide and rule' and excessive written communication."],
       "Esprit de corps is an extension of unity of command in Fayol's own exposition, but the principle itself is about team spirit.")

    cq(B, "fayol-s-14", "L2",
       "A bank runs two separate retail-deposit campaigns for the same savings product — one planned by the marketing department and another by the branch-banking vertical — each with its own head, plan and budget, confusing customers. Which Fayol principle is violated?",
       "Unity of direction",
       [("Unity of command", "no single employee is shown receiving orders from two bosses"),
        ("Scalar chain", "the issue is duplicate plans, not bypassing the line of authority"),
        ("Centralisation and decentralisation", "the degree of concentration of authority is not the problem")],
       ["Unity of direction: one head and one plan for a group of activities having the same objective.",
        "Two plans and two heads for one objective (the same product) breach it."],
       "Unity of command = one employee, one boss; unity of direction = one objective, one plan, one head.")

    ar(B, "fayol-s-14", "L3",
       "Fayol permitted the use of a 'gang plank' for direct communication between employees at the same level in different departments.",
       "Under the gang plank, the employees communicate without informing their respective superiors, because speed is more important than the scalar chain.",
       2,
       ["A true — gang plank is Fayol's exception to the scalar chain, for emergencies.",
        "R false — the superiors must be kept informed (their prior consent/subsequent intimation); it does not dispense with the chain secretly.",
        "Hence A true, R false."],
       "Gang plank shortens the chain but does not hide the communication from superiors.")

    match(B, "fayol-s-14", "L3",
          "Match the situation with the Fayol principle it best illustrates or violates:",
          ["A sales officer is transferred four times in a year, lowering productivity", "Promotions are decided on caste and personal loyalty rather than merit",
           "A clerk gets instructions from both the branch manager and the regional audit officer", "An officer is given responsibility for a target but no authority to sanction the needed expenses"],
          ["Equity", "Unity of command", "Authority and responsibility", "Stability of tenure of personnel"],
          [4, 1, 2, 3],
          [((0, 1), "confuses stability of tenure with equity"),
           ((2, 3), "confuses unity of command with parity of authority and responsibility"),
           ((1, 2), "treats unfair treatment as a command problem")],
          ["Frequent transfers → stability of tenure.", "Favouritism → equity (kindliness + justice).",
           "Two bosses → unity of command.", "Responsibility without matching authority → authority and responsibility."],
          "Authority–responsibility parity is a separate principle from unity of command.")

    cq(B, "taylor", "L1",
       "F.W. Taylor's *The Principles of Scientific Management* was published in:",
       "1911",
       [("1903", "1903 is Taylor's paper 'Shop Management'"),
        ("1916", "1916 is Fayol's Administration Industrielle et Générale"),
        ("1938", "1938 is Barnard's The Functions of the Executive")],
       ["Taylor: Shop Management (1903); The Principles of Scientific Management (1911)."],
       "Match the year to the book: 1903 Taylor (Shop Mgmt), 1911 Taylor (Principles), 1916 Fayol, 1938 Barnard.",
       verify=True, ref="Publication dates of classical management texts")

    stmt(B, "taylor", "L3",
         "Under Taylor's functional foremanship, consider which of the following foremen work in the PLANNING department:",
         [("Route clerk", True, "decides the route/sequence of production"),
          ("Instruction card clerk", True, "draws up instructions for workers"),
          ("Speed boss", False, "speed boss is a production (shop-floor) foreman"),
          ("Disciplinarian", True, "Taylor placed the disciplinarian in the planning department")],
         "Planning dept: route clerk, instruction card clerk, time & cost clerk, disciplinarian; Production: speed boss, gang boss, repair boss, inspector.",
         ask="Which of the above are part of the planning department?")

    ar(B, "taylor", "L2",
       "Taylor advocated a 'mental revolution' on the part of both management and workers.",
       "Taylor held that the conflict over the division of surplus should be replaced by cooperation to increase the surplus itself.",
       0,
       ["A true — mental revolution is central to scientific management.",
        "R true — both sides should stop quarrelling over sharing profit and jointly enlarge it.",
        "R explains A."],
       "'Harmony, not discord' and 'cooperation, not individualism' are the principles that express the mental revolution.")

    # ================================================================ planning
    ar(B, "planning-as-a-prerequisite", "L2",
       "Planning is called the primary function of management.",
       "Planning is a continuous process that is performed at all levels of management.",
       1,
       ["A true — planning precedes and provides the base for all other functions (primacy of planning).",
        "R true — planning is pervasive and continuous.",
        "But R does not explain primacy; the reason is that other functions are carried out within the framework planning lays down."],
       "Both are standard features of planning; only 'primacy' explains why it is the primary function.")

    cq(B, "planning-premises", "L1",
       "For a housing finance company preparing a five-year plan, the expected growth of urban population is an example of which type of planning premise?",
       "External and uncontrollable premise",
       [("Internal and controllable premise", "population growth is outside the firm and cannot be controlled"),
        ("External and controllable premise", "a firm cannot control demographic change"),
        ("Internal and semi-controllable premise", "it is not an internal factor at all")],
       ["Premises: assumptions about the future on which plans are based.",
        "Population growth, government policy, natural calamities → external, uncontrollable."],
       "Market share / pricing are semi-controllable; internal policies and capital are controllable.")

    stmt(B, "planning-premises", "L3",
         "Consider the following statements about planning premises:",
         [("Planning premises are assumptions about the future environment in which plans are expected to operate", True, "definition"),
          ("A firm's share in the market is usually classed as a semi-controllable premise", True, "influenced but not fully determined by the firm"),
          ("Forecasting and premising are the same thing; premises are simply numerical forecasts", False,
           "forecasting is a tool for developing premises; premises also include qualitative assumptions and policy decisions"),
          ("Premises should be agreed upon by all managers involved in planning so that plans are coordinated", True, "Koontz: consistent premising aids coordination")],
         "Forecasts feed premises, but premises are the agreed assumptions — not merely forecasts.")

    cq(B, "planning-steps", "L2",
       "Arrange the following planning steps in the correct sequence:\n\n"
       "P. Evaluating alternative courses\nQ. Developing premises\nR. Setting objectives\nS. Selecting an alternative\nT. Identifying alternative courses of action",
       "R → Q → T → P → S",
       [("Q → R → T → P → S", "develops premises before objectives; premises are built for the stated objectives"),
        ("R → T → Q → P → S", "identifies alternatives before premises are established"),
        ("R → Q → P → T → S", "evaluates before identifying alternatives")],
       ["Setting objectives → developing premises → identifying alternatives → evaluating alternatives → selecting an alternative → implementing → follow-up."],
       "Objectives come first; premises are assumptions for achieving those objectives.")

    p_hi, p_lo = 0.6, 0.4
    L_hi, L_lo = 50, -20
    U_hi, U_lo = 28, 8
    emv_L = p_hi * L_hi + p_lo * L_lo
    emv_U = p_hi * U_hi + p_lo * U_lo
    assert abs(emv_L - 22) < 1e-9 and abs(emv_U - 20) < 1e-9
    nq(B, "planning-steps", "L3",
       "At the 'evaluating alternatives' step of planning, a mutual fund distributor compares two options (payoffs in ₹ lakh over the plan period):\n\n"
       f"| Option | High demand (p = {p_hi}) | Low demand (p = {p_lo}) |\n|---|---:|---:|\n"
       f"| Launch a new digital platform | {L_hi} | {L_lo} |\n| Upgrade the existing branch network | {U_hi} | {U_lo} |\n\n"
       "Using the expected monetary value (EMV) criterion, which option should be selected and what is its EMV?",
       f"Launch the platform; EMV ₹{emv_L:g} lakh",
       [(f"Upgrade the network; EMV ₹{emv_U:g} lakh", "applies the maximin (pessimistic) rule — upgrade has the better worst case — but reports EMV"),
        (f"Launch the platform; EMV ₹{L_hi} lakh", "maximax — picks the best single payoff and ignores probabilities"),
        (f"Launch the platform; EMV ₹{(L_hi+L_lo)/2:g} lakh", "Laplace (equal probabilities) instead of the given probabilities")],
       [f"EMV(launch) = {p_hi}×{L_hi} + {p_lo}×({L_lo}) = {emv_L:g}",
        f"EMV(upgrade) = {p_hi}×{U_hi} + {p_lo}×{U_lo} = {emv_U:g}",
        "Highest EMV → launch."],
       "EMV = Σ (probability × payoff)",
       "Maximin favours the upgrade; the question asks for EMV, which favours the launch.")

    cq(B, "smart-goal", "L2",
       "A branch manager sets this goal for her team: \"Increase SIP registrations by 20% over last year's figure through the new mobile onboarding flow.\" Judged against the SMART criteria, which element is clearly missing?",
       "Time-bound — no deadline is stated",
       [("Specific — the goal does not name what is to be improved", "it names SIP registrations and the channel"),
        ("Measurable — no metric is given", "20% over last year is a measurable metric"),
        ("Relevant — SIP growth is unrelated to a branch's objectives", "SIP growth is plainly relevant to a distribution branch")],
       ["S: SIP registrations via mobile flow ✔; M: +20% ✔; A: plausibly achievable ✔; R: aligned ✔.",
        "T: no 'by when' — missing."],
       "'Over last year's figure' is the baseline, not a deadline.")

    stmt(B, "smart-goal", "L3",
         "Consider the following about SMART goal setting:",
         [("The SMART acronym is commonly traced to George T. Doran's 1981 article in Management Review", True, "Doran (1981)"),
          ("An 'achievable' goal should be so easy that it is certain to be met, to protect morale", False,
           "achievable means realistic yet challenging; goal-setting research (Locke) finds specific, difficult goals raise performance"),
          ("A goal can be specific and measurable yet still fail the 'relevant' test if it does not support the organisation's objectives", True, "relevance = alignment"),],
         "Locke's goal-setting theory favours specific AND challenging goals — easy goals are not what 'achievable' means.")

    cq(B, "organising-meaning", "L1",
       "Which is the correct sequence of steps in the organising process?",
       "Identification and division of work → departmentalisation → assignment of duties → establishing reporting relationships",
       [("Departmentalisation → identification of work → establishing reporting relationships → assignment of duties", "departments cannot be formed before work is identified"),
        ("Assignment of duties → identification of work → departmentalisation → reporting relationships", "duties assigned before work is defined"),
        ("Recruitment → selection → placement → training", "these are staffing steps, not organising")],
       ["Organising: identify/divide work, group into departments, assign duties to positions, set up authority-reporting relationships."],
       "Staffing steps are a common distractor.")

    ar(B, "organising-meaning", "L2",
       "When a manager delegates authority to a subordinate, the manager is relieved of accountability for the delegated task.",
       "Authority can be delegated, but accountability cannot be delegated.",
       3,
       ["A false — the superior remains answerable for the outcome even after delegating.",
        "R true — authority (and responsibility to perform) can be passed down; ultimate accountability cannot.",
        "Hence A is false, R is true (R in fact contradicts A)."],
       "Many texts say 'responsibility cannot be delegated'; the precise NCERT formulation is accountability cannot be delegated.")

    cq(B, "formal-vs-informal", "L2",
       "News of a likely restructuring spreads through a bank within hours through lunch-table conversations and personal chats, well before any circular is issued. This communication network is characteristic of:",
       "The informal organisation (grapevine)",
       [("The formal organisation's scalar chain", "the scalar chain is the official line of authority"),
        ("Lateral communication through the gang plank", "gang plank is an official, sanctioned shortcut in the formal structure"),
        ("Downward communication through the line", "no official downward message has been issued")],
       ["Informal organisation arises spontaneously from social interaction; its channel is the grapevine.",
        "Grapevine is fast but may distort messages."],
       "Speed and absence of official sanction point to the grapevine.")

    stmt(B, "formal-vs-informal", "L3",
         "Consider the following statements about formal and informal organisation:",
         [("The informal organisation arises from the formal organisation and cannot exist without it", True,
           "informal groups form among people brought together by the formal structure"),
          ("The formal organisation is deliberately designed by management, while the informal organisation emerges spontaneously", True, "standard distinction"),
          ("Norms of informal groups are always opposed to organisational goals and should be suppressed", False,
           "informal norms may support or resist goals; management should use informal groups constructively"),
          ("In the informal organisation, leaders are chosen by group members rather than appointed by management", True, "informal leaders emerge")],
         "Informal groups can help (speed, social satisfaction) or hurt (resistance to change); 'always opposed' is too strong.")

    cq(B, "staffing-vs-organising", "L1",
       "The basic difference between organising and staffing is that:",
       "Organising creates positions and relationships; staffing fills them with suitable people",
       [("Staffing creates the structure of positions; organising recruits people to fill them", "the two are reversed"),
        ("Organising is a line function, whereas staffing is performed only by HR specialists", "staffing is a function of every manager, even if HR assists"),
        ("Organising is done once at inception; staffing is done only when a new firm starts up", "both are continuous")],
       ["Organising: identify activities, group them, define authority relationships.",
        "Staffing: manpower planning, recruitment, selection, placement, training, appraisal, compensation."],
       "Staffing is also a continuous function of every manager.")

    cq(B, "directing-as-the-life-spark", "L2",
       "Directing is often described as the 'life-spark' or heart of the management process mainly because:",
       "It initiates action — plans and structures turn into performance only through people",
       [("It is performed only by top management, which issues all orders and instructions", "directing is performed at all levels"),
        ("It is the first function in the management process, preceding even planning", "planning comes first"),
        ("It sets the standards against which actual performance is later measured", "standards are set by planning / controlling")],
       ["Planning, organising and staffing are preparatory; directing sets the organisation in motion.",
        "Elements: supervision, motivation, leadership, communication."],
       "'Initiates action' is the defining phrase.")

    stmt(B, "directing-as-the-life-spark", "L3",
         "Consider the following statements about directing:",
         [("Directing is a continuous activity performed throughout the life of the organisation", True, "continuous"),
          ("Directing flows from top to bottom along the hierarchy", True, "each manager directs his subordinates"),
          ("Supervision, motivation, leadership and communication are the elements of directing", True, "four elements"),
          ("Directing is the exclusive responsibility of first-line supervisors", False, "every manager at every level directs subordinates")],
         "Supervision is only one element of directing; directing itself is pervasive.")

    cq(B, "controlling-and-supervision", "L2",
       "Which of the following is the correct sequence of steps in the controlling process?",
       "Setting standards → measuring actual performance → comparing with standards → analysing deviations → taking corrective action",
       [("Measuring actual performance → setting standards → comparing with standards → taking corrective action → analysing deviations", "standards must exist before measurement; analysis precedes correction"),
        ("Setting standards → comparing with standards → measuring actual performance → analysing deviations → taking corrective action", "cannot compare before measuring"),
        ("Setting standards → measuring actual performance → taking corrective action → comparing with standards → analysing deviations", "corrects before identifying the deviation")],
       ["Standards → measure → compare → analyse (critical point control, management by exception) → correct."],
       "Analyse deviations BEFORE acting on them.")

    items = [("Staff cost", 400, 412), ("Rent", 150, 150), ("Technology", 200, 216), ("Travel", 50, 46), ("Marketing", 120, 127)]
    tol = 0.05
    devs = [(n, a - b, (a - b) / b) for n, b, a in items]
    exc = [n for n, d, p in devs if abs(p) > tol]
    exc_unfav = [n for n, d, p in devs if p > tol]
    big_abs = [n for n, d, p in sorted(devs, key=lambda x: -abs(x[1]))[:3]]
    assert exc == ["Technology", "Travel", "Marketing"]
    tbl = "\n".join(f"| {n} | {b} | {a} |" for n, b, a in items)
    fmt = lambda L: ", ".join(L[:-1]) + " and " + L[-1] if len(L) > 1 else L[0]
    nq(B, "controlling-and-supervision", "L3",
       f"A regional office practises *management by exception*: any cost head whose actual differs from budget by more than {pct(tol,0)} (either way) is reported to the regional head.\n\n"
       f"| Cost head | Budget (₹ lakh) | Actual (₹ lakh) |\n|---|---:|---:|\n{tbl}\n\nWhich heads should be reported?",
       fmt(exc),
       [(fmt(exc_unfav), "reports only unfavourable (overspent) deviations; significant favourable deviations are also exceptions"),
        (fmt(sorted(big_abs, key=lambda n: [i[0] for i in items].index(n))), "ranks by absolute rupee deviation instead of the percentage tolerance"),
        ("All five heads", "reports every deviation — defeats the purpose of management by exception")],
       [f"{n}: deviation {d:+g} = {p*100:+.2f}%" for n, d, p in devs] + [f"|dev| > {pct(tol,0)}: {fmt(exc)}"],
       "Deviation % = (Actual − Budget) ÷ Budget",
       "A large favourable deviation (Travel −8%) can signal poor planning or skipped activity; it is an exception too.")

    cq(B, "pestel", "L1",
       "In a PESTEL scan, the enactment of a new personal data protection law affecting how an insurer stores customer data falls under:",
       "Legal factors",
       [("Political factors", "political = government stability, policy stance; the enacted statute itself is legal"),
        ("Technological factors", "technology is affected, but the driver is a law"),
        ("Social factors", "social = demographics, attitudes, lifestyle")],
       ["PESTEL: Political, Economic, Social, Technological, Environmental, Legal.",
        "Statutes and regulations in force → Legal."],
       "Political vs Legal: policy intentions/stability vs enacted law and regulation.")

    cq(B, "pestel", "L2",
       "A pension fund manager notes that the share of population above 60 is rising and that younger workers increasingly prefer gig employment without employer pension. For the manager's PESTEL analysis, these trends are:",
       "Social factors",
       [("Economic factors", "economic = growth, inflation, interest rates, income; demographics and lifestyle are social"),
        ("Political factors", "no government stance or policy change is described"),
        ("Environmental factors", "environmental = ecological/climate issues")],
       ["Ageing population and work-lifestyle preferences are demographic/cultural → Social."],
       "Gig work has an economic angle, but the preference/demographic trend is classed as social.")

    cq(B, "swot", "L2",
       "An IFSC-based fund administrator has strong in-house analytics (S), a thin sales force (W), a new regulatory regime allowing new fund structures (O) and aggressive global competitors entering (T). A strategy of 'hiring a partner distribution network to exploit the new fund structures' is, in TOWS terms, a:",
       "WO strategy — overcoming a weakness by exploiting an opportunity",
       [("SO strategy — using a strength to exploit an opportunity", "the strategy addresses the weak sales force, not the analytics strength"),
        ("ST strategy — using a strength to counter a threat", "no strength or threat is being used/countered"),
        ("WT strategy — minimising weaknesses and avoiding threats", "WT is defensive; this move chases an opportunity")],
       ["Weakness: thin sales force → fixed by partner network.", "Opportunity: new fund structures → exploited.", "W + O → WO (mini-maxi)."],
       "Identify which quadrant each element of the strategy touches before labelling it.")

    stmt(B, "swot", "L3",
         "Consider the following statements on SWOT analysis:",
         [("Strengths and weaknesses are internal to the organisation, whereas opportunities and threats arise in the external environment", True, "core SWOT logic"),
          ("A new competitor's entry is a weakness of the firm", False, "it is an external threat, not an internal weakness"),
          ("Findings of a PESTEL scan feed mainly into the O and T quadrants of SWOT", True, "PESTEL is an external scan"),
          ("The TOWS matrix converts SWOT findings into four strategy types: SO, WO, ST and WT", True, "Weihrich's TOWS matrix")],
         "Classify by origin (internal vs external), not by whether it is good or bad news.")

    units, opp, defects = 2000, 5, 38
    dpmo = defects / (units * opp) * 1e6
    assert round(dpmo) == 3800
    nq(B, "process-improvement", "L2",
       f"Under a Six Sigma project, a loan-processing team checks {inr(units)} loan files. Each file has {opp} defect opportunities (KYC, income proof, valuation, signatures, data entry). {defects} defects are found. The defects per million opportunities (DPMO) is:",
       inr(dpmo),
       [(inr(defects / units * 1e6), "ignores opportunities per unit (defects per million units)"),
        (inr(defects * opp / units * 1e6), "multiplies instead of dividing by opportunities"),
        (inr((1 - defects / (units * opp)) * 1e6), "reports defect-free opportunities (yield) per million")],
       [f"Total opportunities = {inr(units)} × {opp} = {inr(units*opp)}", f"DPMO = {defects} ÷ {inr(units*opp)} × 10,00,000 = {inr(dpmo)}"],
       "DPMO = Defects ÷ (Units × Opportunities per unit) × 10^6",
       "Six Sigma quality ≈ 3.4 DPMO; always divide by total opportunities.")

    match(B, "process-improvement", "L3",
          "Match the process-improvement approach with its defining feature:",
          ["Kaizen", "Business Process Re-engineering", "Six Sigma", "PDCA cycle"],
          ["Continuous, small, incremental improvements involving all employees",
           "Fundamental rethinking and radical redesign of processes for dramatic gains",
           "Data-driven reduction of variation using the DMAIC cycle",
           "Iterative Plan–Do–Check–Act loop popularised by Deming"],
          [1, 2, 3, 4],
          [((0, 1), "confuses incremental Kaizen with radical BPR — the classic incremental-vs-radical trap"),
           ((2, 3), "confuses DMAIC (Six Sigma) with PDCA (Deming cycle)"),
           ((1, 2), "confuses radical redesign with statistical variation reduction")],
          ["Kaizen — incremental, continuous.", "BPR (Hammer & Champy) — radical, dramatic.",
           "Six Sigma — DMAIC, variation reduction.", "PDCA — Shewhart/Deming cycle."],
          "Incremental vs radical is the most tested contrast.")

    nt, nc, ct_, cc = 12, 8, 60000, 84000
    slope = (cc - ct_) / (nt - nc)
    assert slope == 6000
    nq(B, "cpm-and-pert", "L2",
       f"An activity can be completed in {nt} days at a normal cost of {R(ct_)}, or crashed to {nc} days at a cost of {R(cc)}. Its cost slope is:",
       f"{R(slope)} per day",
       [(f"{R(cc/nc)} per day", "crash cost divided by crash time"),
        (f"{R((cc-ct_)/nt)} per day", "incremental cost divided by normal time instead of time saved"),
        (f"{R(cc-ct_)} per day", "total incremental cost treated as per-day slope")],
       [f"Cost slope = ({inr(cc)} − {inr(ct_)}) ÷ ({nt} − {nc}) = {inr(cc-ct_)} ÷ {nt-nc} = {R(slope)} per day"],
       "Cost slope = (Crash cost − Normal cost) ÷ (Normal time − Crash time)",
       "Crash the critical activity with the lowest cost slope first.")

    stmt(B, "cpm-and-pert", "L1",
         "Consider the following about PERT and CPM:",
         [("PERT uses three time estimates and treats activity times as probabilistic", True, "optimistic, most likely, pessimistic"),
          ("CPM is generally used for repetitive projects with fairly certain activity durations and emphasises time-cost trade-off", True, "deterministic times; crashing"),
          ("The critical path is the shortest path through the network", False, "it is the longest path — it fixes the minimum project duration")],
         "Longest path = critical path = minimum completion time.")

    # ================================================================ CASE A — PERT
    acts = {"A": ([], 2, 4, 6), "B": ([], 3, 5, 13), "C": (["A"], 4, 6, 8), "D": (["A"], 1, 2, 9),
            "E": (["B", "D"], 5, 8, 11), "F": (["C"], 2, 3, 4), "G": (["E", "F"], 3, 4, 11)}
    te, var, ES, EF, LS, LF, T = pert_net(acts)
    paths = {"A-C-F-G": ["A", "C", "F", "G"], "A-D-E-G": ["A", "D", "E", "G"], "B-E-G": ["B", "E", "G"]}
    plen = {k: sum(te[x] for x in v) for k, v in paths.items()}
    crit = max(plen, key=plen.get)
    assert crit == "A-D-E-G" and abs(T - 20) < 1e-9
    cvar = sum(var[x] for x in paths[crit]); csd = math.sqrt(cvar)
    sum_sd = sum(math.sqrt(var[x]) for x in paths[crit])
    all_var = sum(var.values())
    assert abs(cvar - 5) < 1e-9
    tbl = "\n".join(f"| {k} | {', '.join(v[0]) or '—'} | {v[1]} | {v[2]} | {v[3]} |" for k, v in acts.items())
    stemA = ("**Case — Vistara Depository Services.** Vistara is migrating its client-onboarding system. The project team has estimated activity times (weeks):\n\n"
             "| Activity | Immediate predecessor(s) | Optimistic (a) | Most likely (m) | Pessimistic (b) |\n|---|---|---:|---:|---:|\n" + tbl +
             "\n\nUse PERT: $t_e = (a + 4m + b)/6$, variance $= ((b-a)/6)^2$.\n\n")
    g = "MGT-CASE-PERT"
    nq(B, "cpm-and-pert", "L4", stemA + "The expected time of activity B is:",
       f"{te['B']:g} weeks",
       [(f"{acts['B'][2]:g} weeks", "takes the most likely time as expected time"),
        (f"{(3+5+13)/3:g} weeks", "simple average of a, m, b (no weight of 4 on m)"),
        (f"{(3+13)/2:g} weeks", "mid-point of optimistic and pessimistic, ignoring m")],
       ["t_e(B) = (3 + 4×5 + 13)/6 = 36/6 = 6 weeks"], "t_e = (a + 4m + b)/6",
       "Skewed estimates (b far above m) pull t_e above m.", group=g)
    nq(B, "cpm-and-pert", "L4", stemA + "The critical path and the expected project duration are:",
       f"{crit}; {T:g} weeks",
       [(f"B-E-G; {plen['B-E-G']:g} weeks", "picks the path with the longest single activity (B) rather than the longest total"),
        (f"A-C-F-G; {plen['A-C-F-G']:g} weeks", "picks the path with most activities / uses most-likely times"),
        (f"{crit}; {sum(te.values()):g} weeks", "adds all activity times as if performed in series")],
       [f"Expected times: " + ", ".join(f"{k}={v:g}" for k, v in te.items()),
        *[f"{k}: {v:g}" for k, v in plen.items()], f"Longest = {crit} = {T:g} weeks"],
       "Critical path = longest expected-time path", "Only activities on one path add up; parallel paths do not.", group=g)
    nq(B, "cpm-and-pert", "L4", stemA + "The standard deviation of the expected project duration is approximately:",
       f"{csd:.2f} weeks",
       [(f"{sum_sd:.2f} weeks", "adds activity standard deviations instead of variances"),
        (f"{cvar:.2f} weeks", "reports the path variance as the standard deviation"),
        (f"{math.sqrt(all_var):.2f} weeks", "includes variances of non-critical activities")],
       [f"Critical activities A, D, E, G: variances {var['A']:.3f}, {var['D']:.3f}, {var['E']:.3f}, {var['G']:.3f}",
        f"Path variance = {cvar:.3f}; σ = √{cvar:.3f} = {csd:.2f}"],
       "σ_project = √(Σ variances on critical path)", "Variances add; standard deviations do not.", group=g)
    Td = 23
    z = (Td - T) / csd
    nq(B, "cpm-and-pert", "L4", stemA + f"Vistara's board wants the system live within {Td} weeks. The Z-value used to find the probability of meeting this deadline is:",
       f"{z:.2f}",
       [(f"{(Td-T)/sum_sd:.2f}", "uses the sum of standard deviations as σ"),
        (f"{(Td-T)/cvar:.2f}", "divides by variance instead of standard deviation"),
        (f"{(T-Td)/csd:.2f}", "sign reversed (T_e − T_s)")],
       [f"Z = (T_s − T_e)/σ = ({Td} − {T:g})/{csd:.3f} = {z:.2f}"], "Z = (Scheduled time − Expected time) ÷ σ",
       "A positive Z means probability above 50%.", group=g)
    tfC, ffC = LS["C"] - ES["C"], ES["F"] - EF["C"]
    tfB = LS["B"] - ES["B"]
    assert (tfC, ffC) == (2, 0)
    nq(B, "cpm-and-pert", "L4", stemA + "Using expected times, the total float and free float of activity C are:",
       f"Total float {tfC:g} weeks; free float {ffC:g} weeks",
       [(f"Total float {ffC:g} weeks; free float {tfC:g} weeks", "swaps total and free float"),
        (f"Total float {tfC:g} weeks; free float {tfC:g} weeks", "assumes free float always equals total float"),
        (f"Total float {tfB:g} weeks; free float {ffC:g} weeks", "measures slack against path B-E-G instead of the critical path")],
       [f"C: ES = {ES['C']:g}, EF = {EF['C']:g}; LS = {LS['C']:g} → TF = {tfC:g}",
        f"Successor F has ES = {ES['F']:g} = EF(C) → FF = {ffC:g}", "C's slack is shared with F along A-C-F-G."],
       "TF = LS − ES; FF = ES(successor) − EF", "Free float can be zero even when total float is positive.", group=g)

    # ================================================================ CASE B — Fayol/Taylor
    std, lo, hi = 40, 12, 15
    x, y = 38, 42
    ex, ey = x * lo, y * hi
    stemB = ("**Case — Kaveri Pumps Ltd.** A consultant's review of Kaveri's Hosur plant records these observations:\n\n"
             "(i) Assembly workers receive instructions from both the production supervisor and the quality supervisor, which often conflict.\n"
             "(ii) When castings ran short, the stores in-charge (reporting to the purchase head) directly contacted the foundry supervisor (reporting to the production head), keeping both heads informed; the problem was fixed the same day.\n"
             "(iii) Domestic and export sales of the same pump range are run under two separate plans by two different heads.\n"
             "(iv) Sales officers are rotated every four months, and several good officers have resigned.\n"
             f"(v) Following time-and-motion study, standard output is fixed at {std} units a day; workers producing below standard are paid ₹{lo} per unit and those reaching or exceeding it are paid ₹{hi} per unit for all units.\n\n")
    g = "MGT-CASE-KAVERI"
    cq(B, "fayol-s-14", "L4", stemB + "Observation (i) is a violation of:",
       "Unity of command",
       [("Unity of direction", "unity of direction concerns one plan per objective — that is observation (iii)"),
        ("Scalar chain", "no bypassing of the hierarchy is described"),
        ("Division of work", "specialisation is not the issue; conflicting orders are")],
       ["Each worker should receive orders from one superior only; two supervisors issuing conflicting orders breaches this."],
       "(i) and (iii) are deliberately paired to test command vs direction.", group=g)
    cq(B, "fayol-s-14", "L4", stemB + "The practice in observation (ii) is best described as:",
       "Use of a gang plank — a permitted exception to the scalar chain",
       [("A violation of the scalar chain that Fayol never permitted", "Fayol expressly allowed the gang plank in emergencies"),
        ("A violation of unity of command", "each person still has one boss"),
        ("An example of the grapevine in the informal organisation", "this is an official, work-related, informed-superiors contact")],
       ["Same-level employees of different departments communicate directly, with superiors informed, to save time — Fayol's gang plank."],
       "Superiors being informed is what separates a gang plank from bypassing the chain.", group=g)
    cq(B, "fayol-s-14", "L4", stemB + "Observations (iii) and (iv) respectively violate which principles?",
       "Unity of direction; stability of tenure of personnel",
       [("Unity of command; stability of tenure of personnel", "(iii) concerns one plan per objective, not one boss per worker"),
        ("Unity of direction; equity", "frequent rotation breaches stability of tenure, not equity"),
        ("Centralisation; order", "neither concentration of authority nor 'right place' order is the issue")],
       ["(iii) same objective, two plans/heads → unity of direction.", "(iv) frequent transfers, resignations → stability of tenure."],
       "Read each observation separately; do not carry the (i) answer into (iii).", group=g)
    nq(B, "taylor", "L4", stemB + f"Under the scheme in (v), what are the daily earnings of worker X ({x} units) and worker Y ({y} units)?",
       f"X {R(ex)}; Y {R(ey)}",
       [(f"X {R(ex)}; Y {R(std*lo + (y-std)*hi)}", "pays the high rate only on units above standard (a premium-bonus logic)"),
        (f"X {R(x*hi)}; Y {R(ey)}", "pays the high rate to both, ignoring the below-standard penalty"),
        (f"X {R(ex)}; Y {R(y*lo)}", "pays the low rate to both — no differential")],
       [f"X below standard: {x} × {lo} = {R(ex)}", f"Y at/above standard: {y} × {hi} = {R(ey)} (high rate on all units)"],
       "Taylor's differential piece rate: low rate if output < standard, high rate on all units if ≥ standard",
       "The higher rate applies to ALL units once standard is achieved — that is what makes the scheme 'differential'.", group=g)
    stmt(B, "taylor", "L4", stemB + "With reference to the case, consider:",
         [("Observation (v) reflects Taylor's techniques of time study, standardisation of output and differential piece wage", True, "all three visible"),
          ("Observation (i) would be permitted under Taylor's functional foremanship, which Fayol also endorsed", False,
           "functional foremanship does give multiple bosses, but Fayol criticised it as violating unity of command"),
          ("Fayol's principle of initiative is directly violated by observation (ii)", False,
           "(ii) actually shows initiative within a sanctioned gang plank")],
         "Functional foremanship vs unity of command is the classic Taylor–Fayol conflict.", group=g)
