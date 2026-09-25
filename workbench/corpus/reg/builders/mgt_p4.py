"""MGT part 4 — communication, HRD, corporate governance (incl. SEBI LODR)."""
import math
from datetime import date
from mgt_common import cq, nq, stmt, ar, match, inr, R, pct, lakh

LODR = "SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015"


def add_all(B):
    # ================================================================ communication
    cq(B, "steps-in-the-communication-process", "L1",
       "Which is the correct sequence of elements in the communication process?",
       "Sender → encoding → message → channel → decoding → receiver → feedback",
       [("Sender → message → encoding → channel → receiver → decoding → feedback", "encoding converts the idea into a message; decoding happens by the receiver"),
        ("Sender → channel → encoding → message → decoding → feedback → receiver", "channel carries an already-encoded message"),
        ("Receiver → decoding → message → encoding → sender → feedback", "reversed flow")],
       ["Idea → encoded into symbols → message sent through a medium → decoded by receiver → feedback.",
        "Noise can interfere at any stage."],
       "Encoding comes before the message is transmitted; decoding precedes understanding by the receiver.")

    cq(B, "communication-channels", "L1",
       "According to Daft and Lengel's media richness theory, which channel has the HIGHEST richness?",
       "Face-to-face conversation",
       [("Telephone conversation", "rich, but lacks visual cues"),
        ("E-mail message", "lean — limited cues and delayed feedback"),
        ("Formal numeric report", "the leanest channel")],
       ["Richness = capacity to carry multiple cues, immediate feedback, personal focus, natural language.",
        "Order: face-to-face > telephone > e-mail/electronic > personal written > formal written > formal numeric."],
       "Rich channels for non-routine, ambiguous messages; lean channels for routine ones.")

    stmt(B, "communication-channels", "L3",
         "A bank's head office must communicate several messages. Which of the following channel choices are consistent with media richness theory?",
         [("Announcing a branch closure and redeployment to affected staff — face-to-face town hall with Q&A", True, "sensitive, non-routine, emotional → rich channel"),
          ("Revised holiday calendar for the year — e-mail circular", True, "routine, unambiguous → lean channel is efficient"),
          ("Explaining a complex new incentive scheme that has caused confusion — a numeric table posted on the intranet only", False,
           "ambiguous message needs a richer channel allowing questions and feedback"),
          ("Clarifying disputed appraisal ratings with an individual — a personal meeting", True, "sensitive, personal → rich channel")],
         "Match channel richness to message ambiguity; mismatch either way (too lean or too rich) is inefficient.",
         ask="Select the correct answer using the code given below.")

    ar(B, "oral-vs-written-communication", "L2",
       "Written communication is preferred for conveying policies and contractual terms.",
       "Written communication provides a permanent record that can serve as legal evidence and future reference.",
       0,
       ["A true — policies and contracts need precision and a record.",
        "R true — permanence and evidentiary value are the key advantages of written communication.",
        "R explains A."],
       "Oral communication's speed and immediate feedback suit discussions, not binding terms.")

    cq(B, "verbal-vs-non-verbal", "L1",
       "The study of how people use physical space and distance in communication is called:",
       "Proxemics",
       [("Kinesics", "kinesics is body movement, gestures and posture"),
        ("Paralanguage", "paralanguage is tone, pitch and pace of voice"),
        ("Chronemics", "chronemics is the use of time")],
       ["Proxemics (Edward T. Hall): intimate, personal, social and public distance zones."],
       "Kinesics = body; proxemics = space; paralanguage = voice; chronemics = time.")

    match(B, "verbal-vs-non-verbal", "L3",
          "Match the non-verbal cue with its category:",
          ["A manager keeps visitors waiting 40 minutes as a signal of status", "An officer's voice rises and speeds up while explaining a loss",
           "A trainer leans forward and nods while a trainee speaks", "An interviewer places the desk between herself and the candidate to maintain distance"],
          ["Chronemics", "Paralanguage", "Kinesics", "Proxemics"],
          [1, 2, 3, 4],
          [((0, 3), "confuses use of time with use of space"),
           ((1, 2), "confuses vocal cues with body movement"),
           ((2, 3), "confuses body posture with spatial distance")],
          ["Waiting time → chronemics.", "Pitch/pace of voice → paralanguage.", "Posture, nods → kinesics.", "Distance/barriers → proxemics."],
          "Paralanguage is non-verbal even though it is vocal — it is how, not what, is said.")

    cq(B, "upward-downward-and-lateral", "L1",
       "Suggestion schemes, grievance submissions and performance reports sent to superiors are examples of:",
       "Upward communication",
       [("Downward communication", "downward = orders, policies, instructions from superiors"),
        ("Lateral (horizontal) communication", "lateral = between peers at the same level"),
        ("Diagonal communication", "diagonal = across departments and levels")],
       ["Upward: subordinate → superior (feedback, suggestions, grievances, reports)."],
       "Upward communication is the channel most often blocked by status barriers.")

    stmt(B, "upward-downward-and-lateral", "L3",
         "Consider the following statements on communication flows:",
         [("Lateral communication mainly serves coordination among departments or peers", True, "horizontal coordination"),
          ("Diagonal communication cuts across both functions and levels, e.g., a regional sales manager directly contacting an IT analyst", True, "definition"),
          ("According to Keith Davis, the 'single strand' chain is the most common grapevine pattern", False, "Davis found the cluster chain most common"),
          ("Upward communication is often filtered because subordinates tend to pass on favourable information and hold back bad news", True, "status/filtering barrier")],
         "Grapevine patterns: single strand, gossip, probability, cluster — cluster is the most common.")

    cq(B, "semantic-barriers", "L2",
       "A fund house's circular to retail investors reads: \"Your scheme's TER has been rationalised; exit load now applies on redemption before the lock-in-adjusted NAV cut-off.\" Many investors misunderstand it. The main barrier is:",
       "Semantic barrier — technical jargon that receivers cannot decode",
       [("Psychological barrier — investors distrust the fund house", "the problem is decoding of terms, not attitude"),
        ("Organisational barrier — rigid hierarchy in the fund house", "no internal structural issue is described"),
        ("Cultural barrier — different national cultures", "the audience shares culture; it lacks the technical vocabulary")],
       ["Semantic barriers arise from words, symbols and technical terms understood differently by sender and receiver."],
       "Jargon that is clear inside an industry becomes a semantic barrier to outsiders.")

    match(B, "semantic-barriers", "L3",
          "Match each communication problem with the category of barrier it belongs to:",
          ["A policy translated into Marathi uses a word that means 'penalty' instead of 'charge'",
           "A manager dismisses a subordinate's idea before hearing it fully",
           "A clerk hesitates to approach the general manager because of the status gap",
           "A superior withholds information fearing it may undermine his authority"],
          ["Semantic barrier", "Psychological barrier", "Organisational barrier", "Personal barrier"],
          [1, 2, 3, 4],
          [((1, 3), "confuses premature evaluation (psychological) with fear of challenge to authority (personal)"),
           ((2, 3), "confuses status-based organisational barrier with a superior's personal fear"),
           ((0, 1), "treats faulty translation as an emotional barrier")],
          ["Faulty translation → semantic.", "Premature evaluation → psychological/emotional.",
           "Status gap → organisational.", "Fear of challenge to authority → personal."],
          "Personal barriers are traits/fears of superiors or subordinates; organisational barriers stem from structure, rules, status.")

    cq(B, "psychological-barriers", "L2",
       "A message about a new process passes from the zonal office through the regional office and the branch manager to the clerks; by the time it reaches them, key details are missing. This psychological barrier is called:",
       "Loss by transmission and poor retention",
       [("Premature evaluation of the message", "premature evaluation is judging a message before it is complete"),
        ("Distrust between sender and receiver", "no mistrust between parties is described"),
        ("Faulty translation of the message", "faulty translation is a semantic barrier")],
       ["Successive transmission causes loss of accuracy; people retain only part of what they hear."],
       "Loss by transmission is classed under psychological barriers in the standard classification.")

    cq(B, "cultural-and-background-barriers", "L2",
       "A Japanese partner firm conveys refusal indirectly through silence and polite ambiguity, while an Indian team based in GIFT City, trained in U.S.-style direct writing, misreads this as agreement. Edward T. Hall would explain the gap as a difference between:",
       "High-context and low-context cultures",
       [("Individualism and collectivism, as measured on Hofstede's power distance index", "individualism and power distance are separate Hofstede dimensions — the answer mixes them up"),
        ("Monochronic and polychronic time orientations", "time orientation is about scheduling, not implicit meaning"),
        ("Semantic and psychological barriers", "a cultural background barrier is the specific category here")],
       ["High-context: meaning lies in context, relationships, non-verbal cues.", "Low-context: meaning is explicit in words."],
       "Hall also introduced monochronic/polychronic time — a close distractor.")

    stmt(B, "role-of-information-technology", "L2",
         "With reference to the role of information technology in organisational communication, consider:",
         [("IT enables faster communication across locations and can reduce the number of hierarchical layers that information passes through", True, "speed and flattening"),
          ("Heavy use of e-mail and messaging can cause information overload", True, "a recognised drawback"),
          ("Video conferencing eliminates all non-verbal cues and is therefore leaner than e-mail", False,
           "video carries visual and vocal cues; it is richer than e-mail"),],
         "IT increases speed but also brings overload and security concerns.",
         ask="Select the correct answer using the code given below.")

    # ================================================================ HRD
    cq(B, "concept-and-goals-of-hrd", "L1",
       "Udai Pareek's OCTAPACE framework describes the culture HRD seeks to build. OCTAPACE stands for openness, confrontation, trust, authenticity, proactivity, autonomy, collaboration and:",
       "Experimentation",
       [("Efficiency", "not part of OCTAPACE"),
        ("Empowerment", "not part of OCTAPACE, though related"),
        ("Equity", "not part of OCTAPACE")],
       ["OCTAPACE: Openness, Confrontation, Trust, Authenticity, Proactivity, Autonomy, Collaboration, Experimentation."],
       "The final E is Experimentation.")

    stmt(B, "concept-and-goals-of-hrd", "L2",
         "Consider the following statements about HRD:",
         [("HRD aims at developing the competencies of employees, the organisation's culture, and the dyadic and team relationships", True, "individual, dyadic, team and organisational levels"),
          ("HRD is a one-time training programme conducted at the time of induction", False, "HRD is a continuous process"),
          ("Larsen & Toubro is widely cited as one of the first Indian companies to set up a separate HRD function, with T.V. Rao and Udai Pareek as consultants", True, "L&T (mid-1970s)"),],
         "HRD is continuous, systemic and developmental — not a single training event.",
         ask="Select the correct answer using the code given below.")

    cq(B, "developmental-role-of-hrd", "L2",
       "Which statement best captures the difference between traditional personnel management and HRD?",
       "Personnel management is administrative and reactive; HRD is developmental and proactive",
       [("HRD is concerned only with wage administration, record-keeping and labour-law compliance", "that is the traditional personnel role"),
        ("Personnel management focuses on long-term capability building, HRD on day-to-day discipline", "reversed"),
        ("There is no real difference; HRD is merely a new name for the old personnel function", "HRD is conceptually distinct in its developmental orientation")],
       ["HRD: people as resources to develop; focus on learning, potential, culture, career growth."],
       "Developmental vs administrative orientation is the core contrast.")

    cq(B, "drucker-on-hrd-interventions", "L2",
       "Peter Drucker argued that the most valuable asset of a 21st-century institution — whether business or non-business — will be:",
       "Its knowledge workers and their productivity",
       [("Its physical capital, plant and machinery", "Drucker contrasted this with 20th-century manual-worker productivity and capital"),
        ("Its brand value and market reputation", "not Drucker's claim"),
        ("Its hierarchical systems of control", "Drucker saw knowledge workers as requiring autonomy, not control")],
       ["Drucker ('Knowledge-Worker Productivity: The Biggest Challenge', 1999): knowledge workers are the key asset; they must manage themselves and continuously learn."],
       "Drucker coined 'knowledge worker' (1959) and stressed self-management and continuous learning as HRD priorities.")

    cq(B, "nadler-s-hrd-functions", "L1",
       "Leonard Nadler classified HRD activities into three areas. Learning focused on the employee's PRESENT job is called:",
       "Training",
       [("Education", "education prepares the employee for a future job"),
        ("Development", "development is learning not tied to a specific present or future job — for organisational growth"),
        ("Orientation", "not one of Nadler's three areas")],
       ["Nadler: training (present job), education (future job), development (not job-related; growth of individual and organisation)."],
       "Education in Nadler's scheme is future-job oriented, not general schooling.")

    match(B, "nadler-s-hrd-functions", "L3",
          "Match the activity with Nadler's HRD area:",
          ["A dealer attends a workshop on the exchange's new order-entry screens he uses daily",
           "A branch officer identified for promotion attends a programme on branch management",
           "Employees attend open-ended sessions on emerging technologies with no specific job linkage",
           "The HRD professional who designs and delivers the learning programmes"],
          ["Training", "Education", "Development", "Learning specialist (one of Nadler's HRD roles)"],
          [1, 2, 3, 4],
          [((0, 1), "confuses present-job training with future-job education"),
           ((1, 2), "confuses future-job education with non-job-specific development"),
           ((1, 2, 3), "confuses Nadler's HRD roles with his learning areas")],
          ["Present job → training.", "Future job → education.", "No specific job → development.",
           "Designer/deliverer of learning → learning specialist (Nadler's roles: learning specialist, manager of HRD, consultant)."],
          "Education ≠ general schooling in Nadler's scheme; it is preparation for a future job.")

    cq(B, "hrd-subsystems", "L1",
       "Which of the following is NOT generally listed among the HRD subsystems (Pareek and Rao)?",
       "Collective bargaining with trade unions",
       [("Potential appraisal and development", "a core HRD subsystem"),
        ("Career planning", "a core HRD subsystem"),
        ("Feedback and performance coaching", "a core HRD subsystem")],
       ["Subsystems: performance appraisal, potential appraisal & development, feedback & coaching, career planning, training, OD, rewards, employee welfare & QWL, HR information system."],
       "Collective bargaining belongs to industrial relations, not HRD subsystems.")

    cq(B, "manager-s-role-in-hrd", "L1",
       "A senior officer, outside the employee's reporting line, guides her over several years on career choices, organisational politics and professional growth. This developmental relationship is best called:",
       "Mentoring",
       [("Coaching", "coaching is usually shorter-term, task/performance focused, often by the immediate supervisor"),
        ("Counselling", "counselling addresses personal or emotional problems affecting performance"),
        ("Performance appraisal", "a formal evaluation, not a developmental relationship")],
       ["Mentoring: long-term, career and psychosocial support, often outside the reporting line."],
       "Coaching improves current job performance; mentoring shapes the career.")

    cq(B, "competency-mapping", "L2",
       "In Spencer and Spencer's iceberg model of competencies, which components lie BELOW the surface (hidden and hardest to develop)?",
       "Self-concept, traits and motives",
       [("Knowledge and skills only", "these are visible, surface competencies — easiest to develop through training"),
        ("Skills, traits and motives", "skills are a surface competency"),
        ("Knowledge, self-concept and traits", "knowledge is a surface competency")],
       ["Surface: knowledge, skills.", "Hidden core: self-concept (attitudes, values), traits, motives."],
       "Select for hidden competencies; train for surface competencies.")

    stmt(B, "competency-mapping", "L3",
         "An insurer is mapping competencies for its underwriters. Consider:",
         [("Knowledge of reinsurance treaties and actuarial pricing is a technical (functional) competency", True, "job-specific knowledge/skill"),
          ("Negotiation, teamwork and integrity are behavioural competencies", True, "behavioural / soft competencies"),
          ("Competency mapping was introduced by David McClelland in his 1973 paper arguing for testing competence rather than intelligence", True,
           "McClelland (1973) is the landmark origin"),
          ("Behavioural competencies, being hidden, cannot be assessed and are therefore excluded from competency maps", False,
           "they are assessed through behavioural event interviews, assessment centres and 360° feedback")],
         "Hidden does not mean unmeasurable — BEI and assessment centres target them.")

    cq(B, "training-outcomes", "L2",
       "Three months after a customer-service programme, supervisors observe that tellers now greet customers by name and resolve complaints without escalation. In Kirkpatrick's model, this evidence relates to which level of evaluation?",
       "Level 3 — Behaviour",
       [("Level 1 — Reaction", "reaction is participants' satisfaction with the programme"),
        ("Level 2 — Learning", "learning is knowledge/skill gained, usually tested at the end of training"),
        ("Level 4 — Results", "results are organisational outcomes such as complaint rates, revenue or cost")],
       ["Kirkpatrick: reaction → learning → behaviour (transfer to job) → results."],
       "On-the-job behaviour change is Level 3; business impact is Level 4.")

    stmt(B, "training-outcomes", "L3",
         "Consider the following about training outcomes and organisational benefits:",
         [("Jack Phillips added return on investment (ROI) as a fifth level to Kirkpatrick's model", True, "Phillips ROI methodology"),
          ("Positive Level-1 reaction guarantees Level-3 behaviour change", False, "trainees may enjoy a programme yet not transfer learning"),
          ("Transfer of training depends on the work environment, including supervisor support and opportunity to apply skills", True, "Baldwin & Ford transfer model"),
          ("Reduced errors and lower attrition after training are examples of Level-4 results", True, "organisational outcomes")],
         "Levels are a chain; success at one level does not ensure the next.")

    cq(B, "succession-planning", "L2",
       "Which statement best distinguishes potential appraisal from performance appraisal?",
       "Potential appraisal looks ahead at capacity for higher roles; performance appraisal reviews past performance in the current job",
       [("Potential appraisal measures past output in the job; performance appraisal predicts suitability for future roles", "reversed"),
        ("Both are essentially identical exercises and rely only on the immediate supervisor's ratings", "they differ in purpose and methods (assessment centres, psychometrics for potential)"),
        ("Potential appraisal is used only for fixing annual increments and performance-linked bonuses", "increments are linked to performance appraisal")],
       ["Potential appraisal feeds succession planning, career planning and development.",
        "Tools: assessment centres, psychometric tests, job rotation, 9-box (performance × potential)."],
       "Good performance in the present job does not prove potential for a different, higher job (Peter Principle).")

    # ================================================================ governance
    cq(B, "concept-and-principles-of-corporate-governance", "L1",
       "The Cadbury Committee (UK, 1992) defined corporate governance as:",
       "The system by which companies are directed and controlled",
       [("The system by which shareholders maximise short-term dividends", "not the definition; governance balances interests"),
        ("The process of complying with tax laws", "compliance is only one part of governance"),
        ("The set of rules governing employee conduct", "that is a code of conduct, not governance")],
       ["Cadbury Report (1992): 'Corporate governance is the system by which companies are directed and controlled.'"],
       "Cadbury's definition is the most quoted in exam questions.", verify=True,
       ref="Cadbury Report on the Financial Aspects of Corporate Governance, 1992")

    cq(B, "concept-and-principles-of-corporate-governance", "L2",
       "The promoters of a listed company appoint professional managers who award themselves large bonuses linked to short-term revenue while taking excessive risks, harming long-term shareholder value. This problem is best explained by:",
       "Agency theory — conflict of interest between principals (shareholders) and agents (managers)",
       [("Stewardship theory — managers are intrinsically motivated to act as stewards of owners' interests", "stewardship theory assumes alignment, not conflict"),
        ("Stakeholder theory — the firm must balance the interests of all stakeholders", "the specific issue here is owner–manager divergence"),
        ("Resource dependence theory — the board brings external resources", "not about conflicting incentives")],
       ["Agency costs arise when agents pursue self-interest; remedies include independent boards, incentive alignment, disclosure."],
       "Stewardship theory is the direct opposite assumption to agency theory.")

    match(B, "concept-and-principles-of-corporate-governance", "L3",
          "Match the governance theory with its core premise:",
          ["Agency theory", "Stewardship theory", "Stakeholder theory", "Resource dependence theory"],
          ["Managers may act opportunistically; monitoring and incentive alignment are needed",
           "Managers are trustworthy stewards whose interests align with the organisation",
           "The firm must create value for, and be accountable to, all groups affected by it",
           "Boards help the firm secure critical external resources and linkages"],
          [1, 2, 3, 4],
          [((0, 1), "reverses the core assumptions of agency and stewardship theories"),
           ((2, 3), "confuses accountability to stakeholders with securing external resources"),
           ((1, 2), "confuses aligned-manager stewardship with multi-party stakeholder accountability")],
          ["Agency — monitoring (Jensen & Meckling).", "Stewardship — trust (Davis, Schoorman & Donaldson).",
           "Stakeholder — Freeman.", "Resource dependence — Pfeffer & Salancik."],
          "Agency vs stewardship is the pair most often inverted.")

    cq(B, "internal-vs-external-factors", "L2",
       "Which of the following is an EXTERNAL governance mechanism?",
       "The market for corporate control (takeover threat)",
       [("Board of directors' oversight of management", "internal mechanism"),
        ("Internal audit function and internal controls", "internal mechanism"),
        ("Ownership structure and promoter shareholding", "an internal (firm-level) factor")],
       ["External: market for corporate control, regulators, capital markets, statutory auditors, credit rating agencies, media, institutional investors' activism.",
        "Internal: board, committees, ownership structure, internal controls, executive compensation."],
       "Statutory auditors are appointed by shareholders but act as an external check.")

    stmt(B, "internal-vs-external-factors", "L3",
         "Consider the following statements on factors affecting corporate governance:",
         [("A concentrated promoter shareholding can create a principal–principal conflict between controlling and minority shareholders", True,
           "typical of Indian family-controlled firms"),
          ("Stewardship codes for institutional investors are an external factor influencing a company's governance", True, "outside monitoring pressure"),
          ("The design of executive compensation is an external governance factor", False, "compensation design is an internal mechanism"),],
         "In India the dominant conflict is often promoter vs minority (principal–principal), not only owner vs manager.")

    cq(B, "mechanisms-board-audit-committee", "L2",
       "Which of the following is a core role of the audit committee of a listed company?",
       "Overseeing financial reporting and recommending appointment and remuneration of auditors",
       [("Recommending the remuneration policy for directors and senior management", "that is the nomination and remuneration committee's domain"),
        ("Resolving shareholders' grievances regarding transfer of shares and non-receipt of dividends", "that is the stakeholders' relationship committee"),
        ("Approving the company's annual marketing plan and sales budgets for the year", "operational matter, not audit committee oversight")],
       ["Audit committee: financial reporting oversight, auditor appointment/remuneration, review of financial statements, related party transactions, internal controls, vigil mechanism."],
       "Know which committee does what: AC, NRC, SRC, RMC.", verify=True, ref=f"{LODR}, Reg. 18 read with Part C of Schedule II; Companies Act 2013 s.177")

    stmt(B, "mechanisms-board-audit-committee", "L3",
         "Consider the following about governance mechanisms for listed companies in India:",
         [("Every listed company must establish a vigil (whistle-blower) mechanism for directors and employees to report genuine concerns", True, "Companies Act s.177(9)/LODR Reg. 22"),
          ("A listed company's related party transactions that are material require prior approval of shareholders", True, "LODR Reg. 23(4)"),
          ("The audit committee may be chaired by an executive director if he is financially literate", False, "the audit committee chairperson must be an independent director"),
          ("Disclosure of the report on corporate governance forms part of the annual report", True, "Schedule V of LODR")],
         "Chairperson of the audit committee must be an independent director.", verify=True,
         ref=f"{LODR}, Regs. 18, 22, 23, 34 & Sch. V; Companies Act 2013 s.177")

    n_dir = 11
    need = math.ceil(n_dir / 2)
    assert need == 6
    nq(B, "sebi-lodr-governance-requirements", "L3",
       f"A listed company has a board of {n_dir} directors. Its chairperson is a non-executive director who is a relative of the promoter. Under the SEBI LODR Regulations, the minimum number of independent directors required is:",
       f"{need}",
       [(f"{math.ceil(n_dir/3)}", "applies the one-third rule for a non-executive chair, ignoring the promoter link"),
        (f"{n_dir//2}", "rounds half of the board down instead of up"),
        (f"{math.ceil(n_dir*2/3)}", "applies the audit committee's two-thirds ratio to the board")],
       [f"Non-executive chair who is a promoter/relative of promoter → at least half the board must be independent.",
        f"Half of {n_dir} = {n_dir/2} → round up to {need}."],
       "Reg. 17(1)(b): non-exec chair → ≥ 1/3 IDs; no regular non-exec chair, or non-exec chair who is promoter-related → ≥ 1/2 IDs",
       "The promoter link converts the one-third requirement into one-half.", verify=True, ref=f"{LODR}, Reg. 17(1)(b)")

    ac = 7
    q_ = max(2, math.ceil(ac / 3))
    nq(B, "sebi-lodr-governance-requirements", "L3",
       f"The audit committee of a listed company has {ac} members. Under the SEBI LODR Regulations, the minimum quorum for its meeting is:",
       f"{q_} members, with at least two independent directors present",
       [("2 members, with at least one independent director present", "takes the absolute minimum of two, ignoring the one-third test, and the wrong ID requirement"),
        (f"{q_} members, with at least one independent director present", "borrows the board-meeting ID requirement (one ID)"),
        (f"{math.ceil(ac*2/3)} members, with at least two independent directors present", "applies the two-thirds composition ratio to quorum")],
       [f"Quorum = higher of 2 members or one-third of members = max(2, ⌈{ac}/3⌉) = {q_}.",
        "At least two independent directors must be present."],
       "Reg. 18(2)(b): quorum = 2 or 1/3 of members, whichever is greater, with ≥ 2 IDs present",
       "Composition (2/3 independent) and quorum (1/3 or 2, with 2 IDs) are different tests.", verify=True, ref=f"{LODR}, Reg. 18(2)(b)")

    cq(B, "committees-and-codes", "L1",
       "The Kumar Mangalam Birla Committee on corporate governance (1999), whose recommendations led to Clause 49 of the Listing Agreement, was constituted by:",
       "SEBI",
       [("Confederation of Indian Industry (CII)", "CII issued the voluntary Desirable Corporate Governance Code (1998)"),
        ("Department of Company Affairs", "it set up the Naresh Chandra Committee (2002)"),
        ("Reserve Bank of India", "RBI's governance committees relate to banks")],
       ["Birla Committee → SEBI → Clause 49 (2000).", "Later revised on N.R. Narayana Murthy Committee's recommendations (2003)."],
       "CII code (1998) was voluntary; Birla (SEBI, 1999) made governance mandatory for listed firms.",
       verify=True, ref="SEBI Committee on Corporate Governance (K.M. Birla), 1999; Clause 49 of Listing Agreement")

    match(B, "committees-and-codes", "L3",
          "Match the committee with its outcome or focus:",
          ["Cadbury Committee (1992)", "Kumar Mangalam Birla Committee (1999)", "N.R. Narayana Murthy Committee (2003)", "Uday Kotak Committee (2017)"],
          ["UK report defining governance as the system by which companies are directed and controlled",
           "First SEBI-mandated governance code, implemented as Clause 49",
           "Revision of Clause 49 — stronger audit committee role, whistle-blower policy, risk management disclosure",
           "Recommendations leading to the 2018 amendments to the LODR Regulations"],
          [1, 2, 3, 4],
          [((1, 2), "swaps Birla (original Clause 49) and Narayana Murthy (revision of Clause 49)"),
           ((2, 3), "swaps Narayana Murthy (2003) with Kotak (2017)"),
           ((0, 1), "attributes the UK definition to the Birla Committee")],
          ["Cadbury (UK) 1992 → definition.", "Birla (SEBI) 1999 → Clause 49.", "Narayana Murthy (SEBI) 2003 → revised Clause 49.",
           "Kotak (SEBI) 2017 → LODR amendments 2018."],
          "Birla created Clause 49; Narayana Murthy revised it.", verify=True,
          ref="Cadbury 1992; SEBI Birla 1999; SEBI Narayana Murthy 2003; SEBI Kotak 2017")

    # ================================================================ CASE G — communication
    stemG = ("**Case — Samruddhi Pension Services (an NPS Point of Presence).** Three episodes from a quarterly review:\n\n"
             "(a) A leaflet for rural subscribers said: \"Shift to Tier-II for liquidity; at exit, annuitise 40% of corpus; PRAN seeding mandatory.\" Enquiries showed most readers did not understand it.\n"
             "(b) Field agent Mohan believes the new branch manager is biased against him; he ignores her suggestions without considering them.\n"
             "(c) Head office has decided to close 12 service centres and redeploy the staff; it must inform the affected employees.\n\n")
    g = "MGT-CASE-SAMRUDDHI"
    cq(B, "semantic-barriers", "L4", stemG + "Episode (a) is primarily an example of:",
       "A semantic barrier — technical terms not shared by the receivers",
       [("A psychological barrier — readers' lack of attention to the leaflet", "readers tried to understand; they could not decode the terms"),
        ("An organisational barrier — complex hierarchy of the POP", "no structural cause"),
        ("A personal barrier — the sender's unwillingness to communicate", "the sender did communicate; the code was the problem")],
       ["Tier-II, annuitise, PRAN seeding — jargon unfamiliar to rural subscribers → semantic barrier."],
       "Plain-language drafting is the fix for semantic barriers.", group=g)
    cq(B, "psychological-barriers", "L4", stemG + "Episode (b) reflects which barrier?",
       "Psychological barrier — distrust leading to premature rejection",
       [("Semantic barrier — ambiguous words in the manager's suggestions", "the words are not the problem; the attitude is"),
        ("Organisational barrier — status gap between manager and agent", "the issue is Mohan's perception of bias, not structural status"),
        ("Cultural barrier — different social and regional backgrounds", "no cultural difference is indicated")],
       ["Distrust between communicator and receiver and premature evaluation are psychological (emotional) barriers."],
       "Attitude and emotion-driven filtering → psychological.", group=g)
    cq(B, "communication-channels", "L4", stemG + "For episode (c), which channel is most appropriate according to media richness theory?",
       "Face-to-face meetings with the affected staff, followed by written confirmation of the terms",
       [("A short e-mail circular to all employees announcing the closures", "too lean for a sensitive, non-routine message"),
        ("A notice on each office bulletin board listing the affected centres", "lean, impersonal, no feedback"),
        ("Letting the news spread informally through the grapevine before any announcement", "grapevine causes distortion and anxiety")],
       ["Sensitive, emotional, non-routine → richest channel (face-to-face) with immediate feedback; written confirmation adds a record."],
       "Richness for ambiguity; written follow-up for record — the two are complementary.", group=g)

    # ================================================================ CASE H — LODR
    n = 12
    exec_chair = True
    ids_now = 5
    need_ids = math.ceil(n / 2) if exec_chair else math.ceil(n / 3)
    assert need_ids == 6
    stemH = ("**Case — Zenith Capital Ltd (listed; among the top 500 by market capitalisation).** Board and committee data for FY 2025-26:\n\n"
             f"| Item | Detail |\n|---|---|\n| Board size | {n} directors |\n| Chairperson | Also the Managing Director (executive) |\n"
             "| Other executive directors | 3 |\n| Non-independent non-executive directors | 3 |\n"
             f"| Independent directors | {ids_now} (including one woman) |\n"
             "| Audit committee | 4 members: 2 independent directors, 1 non-independent non-executive director, 1 executive director; chaired by an independent director |\n"
             "| Board meetings held | 10 Apr 2025, 25 Jul 2025, 30 Nov 2025, 20 Feb 2026 |\n\n"
             "Assume the SEBI LODR Regulations as currently in force.\n\n")
    g = "MGT-CASE-ZENITH"
    nq(B, "sebi-lodr-governance-requirements", "L4", stemH + "What is the minimum number of independent directors Zenith needs, and is it compliant?",
       f"{need_ids}; short by {need_ids-ids_now}",
       [(f"{math.ceil(n/3)}; compliant with a surplus of {ids_now-math.ceil(n/3)}", "applies the one-third rule meant for a non-executive chair"),
        (f"{math.ceil(n*2/3)}; short by {math.ceil(n*2/3)-ids_now}", "applies the audit committee's two-thirds ratio to the board"),
        (f"{n//2 + 1}; short by {n//2 + 1 - ids_now}", "reads 'at least half' as 'more than half'")],
       ["Chairperson is executive → no regular non-executive chair → at least half the board must be independent.",
        f"Half of {n} = {need_ids}; Zenith has {ids_now} → short by {need_ids-ids_now}."],
       "Reg. 17(1)(b): executive chair → ≥ 1/2 of board independent",
       "Chair's status (executive vs non-executive) drives the ratio.", group=g, verify=True, ref=f"{LODR}, Reg. 17(1)(b)")
    ac_n, ac_id = 4, 2
    ac_need = math.ceil(ac_n * 2 / 3)
    assert ac_need == 3
    stmt(B, "sebi-lodr-governance-requirements", "L4", stemH + "Regarding Zenith's audit committee, consider:",
         [("It satisfies the minimum size requirement of three directors", True, "4 ≥ 3"),
          (f"It satisfies the requirement that at least two-thirds of members be independent", False,
           f"two-thirds of {ac_n} = {ac_n*2/3:.2f} → {ac_need} IDs needed; only {ac_id}"),
          ("Its chairpersonship complies, since it is chaired by an independent director", True, "chair must be an ID"),],
         "Two-thirds of 4 rounds up to 3 — two IDs are not enough.", group=g, verify=True, ref=f"{LODR}, Reg. 18(1)")
    mtg = [date(2025, 4, 10), date(2025, 7, 25), date(2025, 11, 30), date(2026, 2, 20)]
    gaps = [(mtg[i+1] - mtg[i]).days for i in range(3)]
    worst = max(range(3), key=lambda i: gaps[i])
    assert gaps[worst] > 120 and sum(x > 120 for x in gaps) == 1
    cq(B, "sebi-lodr-governance-requirements", "L4", stemH + "Evaluate Zenith's board meetings against LODR requirements:",
       f"Non-compliant — the gap between 25 Jul and 30 Nov 2025 is {gaps[worst]} days, exceeding the 120-day limit",
       [("Compliant — the board met four times in the year, which is all that is required", "ignores the maximum-gap condition"),
        (f"Non-compliant — the gap between 30 Nov 2025 and 20 Feb 2026 ({gaps[2]} days) exceeds a 60-day limit", "applies a non-existent 60-day limit"),
        ("Non-compliant — a top-500 company must hold at least six board meetings a year", "invents a higher meeting count; the requirement is at least four")],
       [f"Gaps: {gaps[0]}, {gaps[1]}, {gaps[2]} days.", "Reg. 17(2): at least four meetings a year, not more than 120 days between two meetings."],
       "Reg. 17(2): ≥ 4 meetings; max gap 120 days", "Both the count and the gap must be satisfied.",
       kind="numerical", group=g, verify=True, ref=f"{LODR}, Reg. 17(2)")
    cq(B, "sebi-lodr-governance-requirements", "L4", stemH + "Zenith's Managing Director is invited to join the boards of other listed companies as an independent director. Under LODR, in how many listed entities at most may he serve as an independent director?",
       "3",
       [("7", "the general cap for independent directorships, which is reduced for whole-time directors/MDs"),
        ("10", "the cap on committee memberships, not directorships"),
        ("5", "the cap on committee chairpersonships")],
       ["Reg. 17A: a person who is a whole-time director or managing director in any listed entity may be an independent director in not more than three listed entities."],
       "Reg. 17A: ID in ≤ 7 listed entities; if WTD/MD of a listed entity, ≤ 3",
       "Distinguish directorship caps from committee caps (10 memberships / 5 chairs).",
       group=g, verify=True, ref=f"{LODR}, Reg. 17A(2); Reg. 26(1)")

    # ================================================================ CASE I — HRD
    cost = 12e5
    b1, b2 = 9e5, 7.5e5
    ben = b1 + b2
    roi = (ben - cost) / cost
    assert abs(roi - 0.375) < 1e-9
    stemI = ("**Case — Kalpavriksh Pension Fund Managers.** The HRD head reviews a six-week programme for fund accountants and a new talent initiative:\n\n"
             "- End-of-course feedback rated the programme 4.6/5.\n"
             "- Test scores on NAV computation rose from 58% (pre-test) to 84% (post-test).\n"
             "- Three months later, supervisors report accountants now reconcile custodian data before NAV sign-off.\n"
             f"- In the year after training, NAV-error penalties and rework fell by {lakh(b1)} and productivity gains were valued at {lakh(b2)}. Total programme cost was {lakh(cost)}.\n"
             "- High performers are being put through assessment-centre exercises and job rotation to identify future fund-operations heads; each is paired with a senior mentor.\n\n")
    g = "MGT-CASE-KALPAVRIKSH"
    match(B, "training-outcomes", "L4", stemI + "Match the evidence with Kirkpatrick's level:",
          ["Feedback rating 4.6/5", "Pre/post-test score rise", "Reconciling custodian data before sign-off", "Fall in NAV-error penalties"],
          ["Reaction", "Learning", "Behaviour", "Results"],
          [1, 2, 3, 4],
          [((2, 3), "confuses on-the-job behaviour with organisational results"),
           ((1, 2), "treats test scores as behaviour change"),
           ((0, 1), "treats satisfaction as learning")],
          ["Satisfaction → reaction.", "Test gains → learning.", "Job practice → behaviour.", "Penalty/rework savings → results."],
          "Behaviour is what people do on the job; results are what the organisation gains.", group=g)
    nq(B, "training-outcomes", "L4", stemI + "Using the Phillips approach, the ROI of the programme is:",
       pct(roi, 1),
       [(pct(ben / cost, 1), "reports the benefit–cost ratio as ROI"),
        (pct((ben - cost) / ben, 1), "divides net benefit by benefits instead of cost"),
        (pct((b1 - cost) / cost, 1), "counts only the penalty savings, omitting productivity gains")],
       [f"Total benefits = {lakh(b1)} + {lakh(b2)} = {lakh(ben)}", f"Net benefit = {lakh(ben-cost)}", f"ROI = {lakh(ben-cost)} ÷ {lakh(cost)} = {pct(roi,1)}"],
       "ROI = (Benefits − Cost) ÷ Cost × 100", "BCR = Benefits ÷ Cost (here 1.375) is not the same as ROI.", group=g)
    cq(B, "succession-planning", "L4", stemI + "The assessment-centre and job-rotation exercise for high performers is primarily an instance of:",
       "Potential appraisal feeding succession planning",
       [("Performance appraisal for annual increments", "it assesses future capacity, not past performance"),
        ("Level-2 training evaluation", "it is not evaluating a training programme"),
        ("Job evaluation for pay grading", "job evaluation rates jobs, not people")],
       ["Identifying future heads through assessment centres and rotation = potential appraisal → succession pipeline."],
       "High performance now does not guarantee potential; that is why a separate appraisal is used.", group=g)
    cq(B, "hrd-subsystems", "L4", stemI + "Pairing each high-potential employee with a senior mentor for long-term career guidance falls mainly under which HRD subsystem?",
       "Career planning and development",
       [("Performance appraisal", "mentoring is developmental, not evaluative"),
        ("Employee welfare and quality of work life", "welfare concerns amenities and wellbeing"),
        ("Rewards", "no reward is involved")],
       ["Mentoring for future roles supports career planning (with potential appraisal) in the Pareek–Rao HRD system."],
       "Mentoring may also be seen as feedback & coaching, but its long-term career focus places it in career planning.", group=g)
