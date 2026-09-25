"""GIR-B part 4: Critical reasoning (assumption, inference, argument, course of action, cause-effect,
strengthen/weaken). Hand-authored original items; the convention used is stated in every stem and each
item is written to have exactly one defensible answer (rationale in the explanation)."""
from girb_common import *

M_ASM = "reas-statement-and-assumption-f8aa8582"
M_COA = "reas-course-of-action-3f7e5981"
M_ARG = "reas-statement-and-argument-strong-or-weak-c34d0b36"
M_INF = "reas-statement-and-inference-65cdc759"
M_CE = "reas-cause-and-effect-645e5e25"
M_SW = "reas-strengthening-and-weakening-an-argument-d884876b"

ASM_CONV = ("An assumption is something supposed or taken for granted — unstated — on which the statement depends. "
            "Decide which of the assumptions is/are implicit in the statement.")
COA_CONV = ("A course of action is a practicable and feasible step which, if taken, follows logically from the statement and helps "
            "solve, reduce or improve the problem. Assume everything in the statement is true.")
ARG_CONV = ("A strong argument is both important and directly related to the question. A weak argument is of minor importance, "
            "not directly related to the question, or rests on a trivial or false generalisation.")
INF_CONV = ("Consider the statement(s) to be true even if they seem at variance with commonly known facts. An inference follows only if "
            "it can be definitely concluded from the statement(s).")
CE_CONV = ("Read the two statements. They may be related as cause and effect, may both be effects of a common cause, "
           "or may be effects of unrelated causes. Choose the relationship that fits best.")

OPT = {
    "asm": ["Only assumption I is implicit", "Only assumption II is implicit", "Both I and II are implicit", "Neither I nor II is implicit"],
    "coa": ["Only I follows", "Only II follows", "Both I and II follow", "Neither I nor II follows"],
    "arg": ["Only argument I is strong", "Only argument II is strong", "Both I and II are strong", "Neither I nor II is strong"],
    "inf": ["Only I follows", "Only II follows", "Both I and II follow", "Neither I nor II follows"],
}
KEYIDX = {"I": 0, "II": 1, "Both": 2, "Neither": 3}
ERRS = {0: "accepted only I", 1: "accepted only II", 2: "accepted both", 3: "rejected both"}


def pairq(B, micro, fmt_, conv, tier, lvl, head, i1, i2, key, why1, why2, trap, label=("I", "II")):
    opts = OPT[fmt_]
    k = KEYIDX[key]
    stem = f"{conv}\n\n{head}\n\n{label[0]}. {i1}\n{label[1]}. {i2}"
    wr = [(opts[j], ERRS[j] + " — misjudged one of the two") for j in range(4) if j != k]
    q(B, micro, lvl, tier, stem, opts[k], wr, [f"I: {why1}", f"II: {why2}", f"Hence: {opts[k]}."],
      conv.split(".")[0], trap, kind="statement")


def single(B, micro, tier, lvl, stem, key, wrongs, steps, formula, trap):
    q(B, micro, lvl, tier, stem, key, wrongs, steps, formula, trap, kind="statement")


def assumptions(B):
    A = lambda *a: pairq(B, M_ASM, "asm", ASM_CONV, *a)
    A("foundation", "L1", "Statement: The municipal corporation has advised residents to boil drinking water for the next two weeks.",
      "Boiling makes the water safe to drink.", "Residents will ignore the advice.", "I",
      "The advice makes sense only if boiling removes the danger — implicit.", "Nobody gives advice expecting it to be ignored — not implicit.",
      "An assumption must support the statement, not work against it.")
    A("foundation", "L1", "Statement: Advertisement of a coaching institute — \"Join our weekend batch and prepare for bank examinations without leaving your job.\"",
      "The institute's weekday classes are of poor quality.", "Some working people want to prepare for bank examinations.", "II",
      "Nothing about weekday quality is implied — not implicit.", "The weekend batch is aimed at job-holders who want to prepare — implicit.",
      "Do not read criticism of other offerings into an advertisement.")
    A("foundation", "L2", "Statement: Notice in an office — \"Please use the stairs; the lift is under maintenance until 5 p.m.\"",
      "Staff are able to use the stairs.", "The lift is expected to work after 5 p.m.", "Both",
      "Asking people to use the stairs presumes they can — implicit.", "'Until 5 p.m.' presumes the work will be over by then — implicit.",
      "Time limits in a notice carry an assumption about when the situation ends.")
    A("foundation", "L2", "Statement: The railways have introduced a mobile app for booking unreserved tickets in order to shorten queues at booking counters.",
      "Many passengers have access to smartphones.", "Long queues at booking counters are a problem.", "Both",
      "An app can cut queues only if many passengers can use it — implicit.", "The stated purpose presumes queues are a problem — implicit.",
      "Both the means and the purpose of a decision can carry assumptions.")
    A("foundation", "L2", "Statement: Rahul told his friend, \"Buy this laptop; it is the lightest one in its price range.\"",
      "The friend will buy only the lightest laptop available in the market.", "Heavier laptops are always of poor quality.", "Neither",
      "The advice does not presume the friend buys only the lightest laptop in the whole market — too extreme.",
      "Nothing is said about the quality of heavier laptops — 'always' makes it extreme.", "Words like 'only' and 'always' usually make an assumption too strong.")
    A("officer", "L2", "Statement: The government has decided to set up fast-track courts to dispose of pending cases of crimes against women within six months.",
      "Fast-track courts can decide cases faster than regular courts.", "Such crimes will stop as soon as the courts are set up.", "I",
      "The six-month target rests on fast-track courts being quicker — implicit.", "The decision is about disposal of pending cases, not an immediate end to crime — not implicit.",
      "Separate the stated objective (speedy disposal) from a hoped-for side effect.")
    A("officer", "L2", "Statement: A bank has announced that customers who link their accounts to its new app will earn reward points on every digital payment.",
      "Reward points may encourage customers to make digital payments.", "Customers who do not use the app will close their accounts.", "I",
      "An incentive is offered only if it is expected to influence behaviour — implicit.", "No such consequence is presumed — not implicit.",
      "An incentive scheme assumes the incentive works, not that non-users will leave.")
    A("officer", "L3", "Statement: \"Instead of building a new flyover, the city should synchronise its traffic signals,\" said the transport consultant.",
      "Synchronising the signals can ease congestion to a meaningful extent.", "A new flyover can never reduce congestion.", "I",
      "Recommending signal synchronisation presumes it will help — implicit.",
      "Preferring one option does not require believing the other can never work — 'never' is too strong.", "A preference is not a claim that the alternative is useless.")
    A("officer", "L3", "Statement: The company has asked all employees to complete the cyber-security module by Friday; e-mail access will be suspended for those who do not.",
      "Employees are able to complete the module by Friday.", "The threat of suspension will encourage employees to complete the module.", "Both",
      "A deadline is set on the basis that it can be met — implicit.", "The penalty is attached to ensure compliance — implicit.",
      "A penalty clause carries the assumption that it will deter.")
    A("officer", "L2", "Statement: District libraries will remain open till 10 p.m. during the examination season.",
      "Some students may wish to study in libraries in the evening during examinations.", "Students do not study at home.", "I",
      "Extended hours in the examination season presume evening demand from students — implicit.", "Late hours do not presume that nobody studies at home — not implicit.",
      "Reject assumptions that turn 'some' into 'all'.")
    A("officer", "L3", "Statement: The weather department has forecast heavy rain in the coastal districts, and fishermen have been advised not to go out to sea for three days.",
      "The forecast is reasonably reliable.", "Going out to sea during heavy rain is risky.", "Both",
      "Advice is issued on the basis of a forecast considered dependable — implicit.", "The advice exists because the sea is dangerous in such weather — implicit.",
      "An advisory assumes both the reliability of its basis and the risk it guards against.")
    A("officer", "L3", "Statement: To curb absenteeism, the school will send an SMS to parents whenever a student is absent.",
      "Most parents have access to a mobile phone.", "In some cases parents are unaware that their children are absent.", "Both",
      "An SMS alert works only if parents can receive it — implicit.", "Informing parents helps only if some did not already know — implicit.",
      "Check both the channel and the purpose of a measure.")
    A("officer", "L3", "Statement: The state has made helmets compulsory for pillion riders as well.",
      "Pillion riders are more careless than riders.", "Riders who wear helmets never meet with accidents.", "Neither",
      "The rule does not compare carefulness — not implicit.", "Helmets reduce injury, not accidents; 'never' is false and not presumed — not implicit.",
      "The implicit assumption would be that pillion riders also risk head injury — neither option says that.")
    A("officer", "L3", "Statement: Job advertisement — \"Only candidates who have scored at least 60% marks in graduation are eligible to apply.\"",
      "Candidates who scored less than 60% cannot perform the job at all.", "Enough candidates with 60% or more are expected to apply.", "II",
      "A cut-off is a screening tool; it does not presume others are totally incapable — not implicit.",
      "An employer sets a cut-off expecting an adequate pool above it — implicit.", "Eligibility cut-offs assume a sufficient applicant pool, not incompetence below the line.")
    A("officer", "L3", "Statement: Advertisement — \"Our new detergent removes stains even in cold water — save on your electricity bill!\"",
      "Some people heat water to wash clothes.", "Stain removal matters to consumers.", "Both",
      "The electricity-saving claim makes sense only if some people heat washing water — implicit.",
      "The product is sold on its stain-removing ability — implicit.", "An advertisement assumes that its selling points matter to buyers.")


def courses(B):
    C = lambda *a: pairq(B, M_COA, "coa", COA_CONV, *a)
    C("foundation", "L1", "Statement: Many students in a village school fail in mathematics every year.",
      "Remedial classes in mathematics should be arranged for weak students.", "Mathematics should be removed from the school syllabus.", "I",
      "Remedial classes address the cause directly — follows.", "Removing a core subject is impractical and evades the problem — does not follow.",
      "A course of action must solve the problem, not abolish the activity.")
    C("foundation", "L1", "Statement: A large number of commuters were stranded after a bridge on the highway collapsed following heavy rain.",
      "Traffic should immediately be diverted through alternative routes.", "Other old bridges on the route should be inspected for safety.", "Both",
      "Diversion gives immediate relief — follows.", "Inspection prevents a repeat on the same route — follows.",
      "Immediate relief and prevention can both be valid.")
    C("foundation", "L2", "Statement: Stray dogs have bitten several children in a residential colony.",
      "The municipal body should carry out sterilisation and vaccination of stray dogs in the area.", "All residents should be asked to move out of the colony.", "I",
      "Addresses the problem practically — follows.", "Evacuating a colony is impractical and disproportionate — does not follow.",
      "Drastic, impractical steps are not valid courses of action.")
    C("foundation", "L2", "Statement: Sale of spurious medicines has been reported from a few shops in the town.",
      "All medical shops in the state should be closed.", "The drug control department should inspect the shops and act against those found guilty.", "II",
      "Closing every shop in the state punishes the innocent and cuts off medicines — does not follow.", "Targeted inspection and action fit the problem — follows.",
      "The response must be proportionate to the scale of the problem.")
    C("foundation", "L2", "Statement: The prices of vegetables in the town rose slightly this week because of a local festival.",
      "The government should ban the festival.", "The government should immediately import vegetables.", "Neither",
      "Banning a festival for a slight, temporary price rise is disproportionate — does not follow.",
      "Importing for a slight weekly rise is unnecessary — does not follow.", "A minor, temporary problem needs no drastic action.")
    C("officer", "L2", "Statement: A survey shows that a large number of rural bank accounts opened under a financial-inclusion scheme have had no transactions for a year.",
      "Banks should hold financial-literacy camps in these areas to explain the benefits of using the accounts.", "All such accounts should be closed immediately.", "I",
      "Addresses the reason for non-use — follows.", "Closing accounts defeats the purpose of inclusion — does not follow.",
      "The step should advance, not reverse, the objective of the scheme.")
    C("officer", "L2", "Statement: Several cases of food poisoning have been reported after a community feast in a town.",
      "Samples of the food served should be tested to find the source of contamination.", "Those affected should be given immediate medical treatment.", "Both",
      "Identifies the cause and prevents recurrence — follows.", "Immediate relief for victims — follows.",
      "Relief and investigation are complementary.")
    C("officer", "L3", "Statement: Water in the city's reservoirs has fallen to its lowest level in ten years, and the monsoon is still six weeks away.",
      "The civic body should stop supplying water to households until the monsoon arrives.",
      "The civic body should regulate the water supply and appeal to citizens to avoid wastage.", "II",
      "Stopping supply for six weeks is neither feasible nor humane — does not follow.", "Rationing and conservation stretch the available water — follows.",
      "Choose management over total shutdown.")
    C("officer", "L3", "Statement: An audit found that many government hospitals have expensive equipment lying unused because trained technicians are not available.",
      "The government should recruit or train technicians to operate the equipment.", "The unused equipment should be sold to private hospitals.", "I",
      "Removes the cause of non-use — follows.", "Selling deprives public patients of facilities already bought — does not follow.",
      "Solve the bottleneck rather than give up the asset.")
    C("officer", "L3", "Statement: Many first-time investors lost money after following unregistered 'stock tip' channels on social media.",
      "The market regulator should run awareness campaigns urging investors to deal only with registered advisers.",
      "Action should be taken against those running unregistered advisory channels.", "Both",
      "Prevents future losses through awareness — follows.", "Enforcement against the source — follows.",
      "Awareness and enforcement address the problem from two sides.")
    C("officer", "L2", "Statement: A factory on the outskirts of a town has been discharging untreated effluents into a river that nearby villages use for drinking water.",
      "The pollution control board should direct the factory to install an effluent treatment plant and monitor compliance.",
      "The villagers should be told to stop drinking water altogether.", "I",
      "Stops the pollution at source — follows.", "Absurd and impossible — does not follow.", "A course of action must be practicable.")
    C("officer", "L3", "Statement: Attendance at evening adult-literacy classes in a village has fallen because most learners work in the fields until late.",
      "The class timings should be changed to suit the learners.", "The adult-literacy programme in the village should be discontinued.", "I",
      "Addresses the actual cause (timing clash) — follows.", "Abandoning the programme does not solve the problem — does not follow.",
      "Fix the cause identified in the statement.")
    C("officer", "L3", "Statement: Some passengers complained that the air-conditioning in one coach of a train was not working on a particular day.",
      "The railways should replace the air-conditioning systems in all its trains.", "The railways should stop running air-conditioned coaches.", "Neither",
      "An isolated fault does not justify replacing the system across all trains — does not follow.",
      "Withdrawing the service altogether is absurd — does not follow.", "The proper action (repairing that coach) is not among the options.")
    C("officer", "L3", "Statement: A newly built stretch of road developed potholes within three months of being opened.",
      "The road should be closed permanently.", "An inquiry should be held into the quality of work, and the contractor should be made to repair the road.", "II",
      "Permanent closure is impractical — does not follow.", "Fixes accountability and the defect — follows.", "Accountability plus repair is the proportionate response.")
    C("officer", "L3", "Statement: Complaints of cyber fraud involving fake customer-care numbers have risen sharply.",
      "Banks and the police should publicise official helpline numbers and warn customers against searching for such numbers online.",
      "The police should set up a dedicated cell to act quickly on such complaints.", "Both",
      "Prevention through awareness — follows.", "Faster response and enforcement — follows.", "Preventive and remedial steps can both follow.")


def arguments(B):
    A = lambda *a: pairq(B, M_ARG, "arg", ARG_CONV, *a)
    A("foundation", "L1", "Should mobile phones be banned in examination halls?",
      "Yes. They can be used to cheat during the examination.", "No. Students should be free to carry whatever they like.", "I",
      "Directly relevant and important — strong.", "Rests on an unreasonable claim of absolute freedom — weak.",
      "An argument based on unlimited freedom is weak.")
    A("foundation", "L2", "Should the retirement age of government employees be reduced to 55 years?",
      "Yes. It will create more openings for younger job-seekers.", "No. The government will lose experienced employees prematurely, affecting efficiency.", "Both",
      "Important and relevant — strong.", "Important and relevant — strong.", "Both sides can be strong at once.")
    A("foundation", "L1", "Should cycling be encouraged in cities?",
      "No. Cycles are cheaper than cars.", "Yes. Cycling reduces pollution and improves health.", "II",
      "Being cheaper is not a reason against encouraging cycling — weak.", "Relevant and important — strong.",
      "Check that the reason actually supports the side it claims.")
    A("foundation", "L2", "Should every school have a playground?",
      "Yes. Many famous players studied in schools.", "No. Playgrounds make a lot of noise.", "Neither",
      "Irrelevant link — weak.", "Trivial objection — weak.", "Trivial or irrelevant reasons make weak arguments.")
    A("foundation", "L1", "Should plastic carry bags be banned?",
      "Yes. They clog drains and harm animals.", "No. Shopkeepers will have to print new bills.", "I",
      "Relevant and important — strong.", "Irrelevant/trivial — weak.", "A trivial inconvenience is a weak counter-argument.")
    A("officer", "L2", "Should banks be allowed to charge a fee on every ATM withdrawal?",
      "Yes. It will help banks recover the cost of maintaining ATMs.", "No. It will burden small depositors who depend on cash.", "Both",
      "Relevant economic reason — strong.", "Relevant concern of fairness — strong.", "Recognise genuine considerations on both sides.")
    A("officer", "L3", "Should voting be made compulsory in India?",
      "Yes. Some other countries have made it compulsory.",
      "No. Compulsion cannot ensure informed voting, and enforcing it across a vast electorate would be impractical.", "II",
      "Imitation of other countries is not a reason by itself — weak.", "Relevant and important — strong.",
      "'Others do it' is a weak argument.")
    A("officer", "L3", "Should the government privatise all public-sector banks?",
      "Yes. Private banks never have bad loans.", "No. All private companies are corrupt.", "Neither",
      "False generalisation — weak.", "False generalisation — weak.", "Sweeping claims ('never', 'all') make arguments weak.")
    A("officer", "L3", "Should entrance examinations for professional courses be conducted only online?",
      "Yes. Online tests can be evaluated faster and with fewer errors.",
      "No. Candidates in areas with poor connectivity and few centres may be put at a disadvantage.", "Both",
      "Relevant benefit — strong.", "Relevant equity concern — strong.", "Efficiency and access are both important considerations.")
    A("officer", "L2", "Should the export of a food grain be banned whenever its domestic price rises sharply?",
      "Yes. It helps keep domestic supply adequate and prices in check.", "No. The country will then have to import more cars.", "I",
      "Directly relevant — strong.", "Irrelevant consequence — weak.", "The link between cause and consequence must be real.")
    A("officer", "L3", "Should students be promoted to the next class without any assessment up to Class 8?",
      "No. Without any assessment, learning gaps may go unnoticed.", "Yes. This is what most students would like.", "I",
      "Important educational concern — strong.", "Students' preference is not a sound basis for policy — weak.",
      "Popularity with those affected is not by itself a strong reason.")
    A("officer", "L3", "Should offices adopt flexible working hours?",
      "Yes. Employees can balance work and personal needs better, which often improves productivity.",
      "No. It will become impossible to get any work done in offices.", "I",
      "Relevant and important — strong.", "Exaggerated — weak.", "Exaggeration weakens an argument.")
    A("officer", "L3", "Should credit cards be issued only to people above a minimum annual income?",
      "Yes. It reduces the risk of default by borrowers who cannot repay.",
      "No. It will exclude creditworthy young earners and self-employed people who lack formal income proof.", "Both",
      "Relevant risk consideration — strong.", "Relevant inclusion concern — strong.", "Both risk and access are important.")
    A("officer", "L2", "Should the use of loudspeakers in residential areas be banned after 10 p.m.?",
      "Yes. Noise at night disturbs sleep and affects the sick, the elderly and students.", "No. Loudspeakers were invented a long time ago.", "I",
      "Relevant and important — strong.", "Irrelevant — weak.", "Age of an invention has no bearing on the question.")
    A("officer", "L3", "Should elections to Parliament and state assemblies be held simultaneously?",
      "Yes. It would reduce the expense and administrative burden of frequent elections.",
      "No. National issues may overshadow local issues in state elections.", "Both",
      "Relevant and important — strong.", "Relevant and important — strong.", "A policy debate can have strong arguments on both sides.")


def inferences(B):
    I = lambda *a: pairq(B, M_INF, "inf", INF_CONV, *a)
    I("foundation", "L1", "Statements: All the students of Class X passed the examination. Ravi is a student of Class X.",
      "Ravi passed the examination.", "Ravi scored the highest marks in Class X.", "I",
      "Follows directly from 'all passed'.", "Nothing is said about ranks.", "Stay within what is stated.")
    I("foundation", "L1", "Statement: The shop opens at 9 a.m. and closes at 8 p.m. on all days except Sunday, when it stays closed.",
      "The shop is open for eleven hours on Monday.", "The shop is closed on Sunday.", "Both",
      "9 a.m. to 8 p.m. = 11 hours — follows.", "Stated directly — follows.", "Compute where the data allow.")
    I("foundation", "L1", "Statement: Most of the members of the club are doctors.",
      "Some members of the club are doctors.", "All doctors in the city are members of the club.", "I",
      "'Most' includes 'some' — follows.", "The statement says nothing about all doctors — does not follow.", "Do not reverse the direction of a statement.")
    I("foundation", "L2", "Statement: Sales of woollen clothes in the town rose sharply in December.",
      "Every family in the town bought woollen clothes in December.", "Woollen clothes are available only in December.", "Neither",
      "A sharp rise does not mean every family bought — does not follow.", "Nothing about availability — does not follow.",
      "Reject 'every' and 'only' unless the statement supports them.")
    I("foundation", "L1", "Statements: No bird in the zoo is a parrot. Tweety is a bird in the zoo.",
      "Tweety is not a parrot.", "There are no parrots anywhere.", "I",
      "Follows from the two statements.", "The statement is about the zoo only — does not follow.", "Mind the scope of the statement.")
    I("officer", "L3", "Statement: The company's profit this year was ₹50 crore, double that of last year, although its revenue rose by only 10%.",
      "The company's profit last year was ₹25 crore.", "This year the company's costs grew by less than 10%.", "Both",
      "Double of last year = 50 → last year 25 — follows.",
      "Let last year's revenue be R: costs went from R − 25 to 1.1R − 50, and 1.1R − 50 < 1.1(R − 25); so costs grew by less than 10% — follows.",
      "Profit can double on small revenue growth only if costs grew more slowly than revenue.")
    I("officer", "L2", "Statement: Admission records show that 400 ticket-holders entered the museum on Saturday. Children below 12 enter free and need no ticket.",
      "At least 400 people visited the museum on Saturday.", "No child below 12 visited the museum on Saturday.", "I",
      "400 ticket-holders entered — so at least 400 visitors — follows.", "Children need no ticket, so they would not appear in the count — does not follow.",
      "A count of ticket-holders says nothing about those who need no ticket.")
    I("officer", "L2", "Statement: The price of milk rose from ₹50 to ₹55 per litre, while a family's monthly milk consumption stayed at 30 litres.",
      "The family's monthly spending on milk rose by ₹150.", "The family's total monthly spending rose by 10%.", "I",
      "30 × ₹5 = ₹150 — follows.", "Only milk spending rose 10%; total spending is unknown — does not follow.",
      "A 10% rise in one item is not a 10% rise in the total.")
    I("officer", "L2", "Statements: Some managers are engineers. All engineers are graduates.",
      "All graduates are engineers.", "Some managers are graduates.", "II",
      "'All engineers are graduates' cannot be reversed — does not follow.", "The managers who are engineers are graduates — follows.",
      "An 'all' statement does not convert to 'all' in reverse.")
    I("officer", "L3", "Statement: A train left its origin on time but reached its destination 45 minutes late. The scheduled journey time is 5 hours.",
      "The train took 5 hours 45 minutes for the journey.", "The train's average speed over the journey was lower than scheduled.", "Both",
      "Left on time, 45 minutes late → 5 h 45 min — follows.", "Same distance in more time → lower average speed — follows.",
      "Average speed = distance ÷ time.")
    I("officer", "L3", "Statement: No official of the bank who handles cash is allowed to approve loans. Kiran, an official of the bank, approves loans.",
      "Kiran does not handle cash.", "Kiran is not an official of the bank.", "I",
      "Kiran is an official who approves loans, so she cannot be one who handles cash — follows.", "Contradicts the statement — does not follow.",
      "Use the rule on the member described.")
    # single-best inferences
    S = lambda *a: single(B, M_INF, *a)
    S("officer", "L2", INF_CONV + "\n\nStatements: Every member of the audit team is a chartered accountant. Some chartered accountants in the firm are also cost accountants. Meena is a member of the audit team.\n\nWhich of the following definitely follows?",
      "Meena is a chartered accountant.",
      [("Meena is also a cost accountant.", "'some' CAs being cost accountants says nothing about Meena"),
       ("Some members of the audit team are cost accountants.", "the cost-accountant CAs may be outside the team"),
       ("Every cost accountant in the firm is on the audit team.", "reversal / overgeneralisation")],
      ["Meena ∈ audit team ⊂ chartered accountants → Meena is a CA.", "The other options need facts not given."], "Set inclusion", "Only chains of 'all' statements give certain conclusions.")
    S("officer", "L3", INF_CONV + "\n\nStatements: In a town, every school that has a library also has a computer laboratory. School P has no computer laboratory.\n\nWhich of the following definitely follows?",
      "School P does not have a library.",
      [("School P has a library but no laboratory.", "contradicts the rule"), ("Every school with a laboratory also has a library.", "converse of the rule"),
       ("School P will soon set up a laboratory.", "speculation")],
      ["Library → laboratory. No laboratory → no library (contrapositive)."], "If A then B ⇒ if not B then not A", "The converse (B → A) does not follow.")
    hi, en, tot = 35, 30, 60
    both = hi + en - tot
    assert both == 5 and hi - both == 30 and en - both == 25
    S("officer", "L3", INF_CONV + f"\n\nStatement: In an office of {tot} employees, {hi} speak Hindi and {en} speak English. Every employee speaks at least one of the two languages.\n\nWhich of the following definitely follows?",
      f"Exactly {both} employees speak both languages.",
      [(f"{hi} employees speak only Hindi.", "forgot to subtract those who speak both"), ("No employee speaks both languages.", f"{hi} + {en} exceeds {tot}"),
       ("More employees speak only English than only Hindi.", f"only English = {en - both}, only Hindi = {hi - both}")],
      [f"Both = {hi} + {en} − {tot} = {both}.", f"Only Hindi = {hi - both}, only English = {en - both}."], "n(A ∪ B) = n(A) + n(B) − n(A ∩ B)",
      "Everyone speaks at least one language, so the union is the whole office.")
    b0, b1 = 40, 25
    S("officer", "L3", INF_CONV + f"\n\nStatement: After a new metro line opened, the number of buses on Route 12 was cut from {b0} to {b1}. The metro now carries 60,000 passengers a day along the same corridor.\n\nWhich of the following can definitely be inferred?",
      f"The number of buses on Route 12 fell by {fmt((b0 - b1) / b0 * 100)}%.",
      [("Daily bus passengers on Route 12 fell by 60,000.", "metro riders need not all be former bus users"),
       ("All former bus passengers on Route 12 now use the metro.", "not stated"),
       ("The metro line has reduced air pollution in the corridor.", "not stated")],
      [f"({b0} − {b1}) ÷ {b0} = {fmt((b0 - b1) / b0 * 100)}%.", "Nothing is stated about where metro passengers came from."], "Percentage change = change ÷ original",
      "Only computations from given numbers are certain.")


CE = ["Statement I is the cause and statement II is its effect", "Statement II is the cause and statement I is its effect",
      "Both the statements are independent causes", "Both the statements are effects of independent causes",
      "Both the statements are effects of some common cause"]
CE_ERR = ["took I as the cause", "took II as the cause", "treated both as causes", "treated them as unrelated effects", "looked for a common cause"]


def cause_effect(B):
    items = [
        ("foundation", "L1", "Heavy rain lashed the city throughout the night.", "Several low-lying areas of the city were waterlogged in the morning.", 0,
         "Night-long rain directly leads to waterlogging.", 2),
        ("foundation", "L1", "The price of onions has shot up in the local market.", "Unseasonal rain destroyed a large part of the onion crop in the major growing states.", 1,
         "Crop loss reduces supply and raises prices.", 2),
        ("foundation", "L1", "The government reduced the excise duty on petrol and diesel.", "Retail prices of petrol and diesel came down the next day.", 0,
         "Lower duty lowers retail prices.", 2),
        ("foundation", "L2", "Many students of the college failed in the final examination.", "The college hostel mess has started serving breakfast earlier.", 3,
         "The two events have nothing to do with each other; each has its own cause.", 2),
        ("foundation", "L2", "The local football team won the state championship.", "The team had practised for four hours every day throughout the season.", 1,
         "Sustained practice explains the victory.", 2),
        ("officer", "L2", "The central bank raised its policy rate by 50 basis points.", "Several banks increased their home-loan interest rates within a week.", 0,
         "A higher policy rate raises banks' cost of funds, which they pass on.", 2),
        ("officer", "L2", "Most shops in the market pulled down their shutters in the afternoon.", "A traders' association had called a half-day strike against a new local tax.", 1,
         "The strike call explains the closure.", 2),
        ("officer", "L3", "Airlines raised fares on domestic routes this month.", "Long-distance bus operators raised their fares this month.", 4,
         "Neither fare rise causes the other; both point to a shared cost factor such as a rise in fuel prices.", 2),
        ("officer", "L3", "The state announced a large increase in the minimum support price for pulses.", "Farmers in the state sowed a larger area under pulses the following season.", 0,
         "A higher assured price encourages farmers to sow more.", 2),
        ("officer", "L2", "The number of tourists visiting the hill station fell sharply this summer.", "A landslide blocked the only road to the hill station for most of the summer.", 1,
         "A blocked access road keeps tourists away.", 2),
        ("officer", "L3", "Hospitals in the city reported a rise in cases of heatstroke.", "The city's demand for electricity touched a record high.", 4,
         "Neither causes the other; both result from a spell of extreme heat.", 2),
        ("officer", "L3", "A leading car manufacturer cut the prices of its models by up to 8%.", "Another company launched a new brand of toothpaste.", 3,
         "Unrelated business decisions with separate causes.", 4),
        ("officer", "L3", "The government made it mandatory to link mobile numbers to bank accounts used for digital payments.", "Cases of mobile-banking fraud had risen sharply over the past year.", 1,
         "The rise in fraud prompted the regulatory measure.", 2),
        ("officer", "L2", "The catchment area of the river received unusually heavy rainfall for three days in a row.", "The river breached its banks at several places.", 0,
         "Heavy rain in the catchment swells the river.", 2),
        ("officer", "L3", "Gold prices rose sharply in the domestic market.", "The state government announced free bicycles for girl students of Class IX.", 3,
         "Unrelated events with separate causes.", 4),
    ]
    for tier, lvl, s1, s2, key, why, drop in items:
        if drop == key:
            drop = 2 if key != 2 else 3
        opts = [j for j in range(5) if j != drop]
        stem = f"{CE_CONV}\n\nI. {s1}\nII. {s2}"
        q(B, M_CE, lvl, tier, stem, CE[key], [(CE[j], CE_ERR[j]) for j in opts if j != key],
          [why, f"Hence: {CE[key]}."], "Cause precedes and explains effect", "An event reported later in the text can still be the cause.", kind="statement")


def strengthen_weaken(B):
    S = lambda *a: single(B, M_SW, *a)
    S("foundation", "L2", "Argument: Students who eat breakfast regularly score higher in morning tests. So eating breakfast improves concentration.\n\nWhich of the following, if true, most weakens the argument?",
      "Students who eat breakfast also sleep longer, and longer sleep is known to raise test scores.",
      [("Breakfast is usually the first meal that students eat after waking up in the morning.", "irrelevant restatement"),
       ("Some students prefer to drink tea rather than milk with their breakfast on school days.", "irrelevant detail"),
       ("Morning tests in the school are held at 9 a.m. on every working day.", "irrelevant detail")],
      ["The weakener offers an alternative cause (sleep) for the higher scores."], "Alternative cause weakens a causal claim", "Irrelevant details neither strengthen nor weaken.")
    S("foundation", "L2", "Argument: Town X installed street lights on its main roads last year, and night-time thefts on those roads fell by 40%. So street lights reduce theft.\n\nWhich of the following, if true, most strengthens the argument?",
      "Night-time thefts on the unlit roads of the same town did not fall during that period.",
      [("The new street lights were purchased last year from a supplier based in the same town.", "irrelevant"),
       ("Town X has a population of about two lakh people spread over ten wards.", "irrelevant"),
       ("Daytime thefts on the main roads rose slightly during the same period as the lighting work.", "does not bear on night-time effect of lights")],
      ["A comparison group without lights showing no fall supports the lights as the cause."], "Control comparison strengthens a causal claim", "Look for evidence that rules out other explanations.")
    S("foundation", "L2", "Argument: The company should move its office to the suburbs, because rents there are 30% lower.\n\nWhich of the following, if true, most weakens the argument?",
      "Most employees would face two extra hours of commuting, and many have said they would resign.",
      [("The suburbs have more parks, open spaces and quieter streets than the city centre has.", "irrelevant or mildly supportive"),
       ("Rents in the city centre have remained almost unchanged for the last two financial years.", "does not remove the rent saving"),
       ("The company was founded ten years ago by two engineers from the city.", "irrelevant")],
      ["Losing staff can outweigh the rent saving."], "A serious cost of the plan weakens it", "A weakener must bear on the conclusion.")
    S("foundation", "L2", "Argument: Reading a newspaper daily improves general awareness, so aspirants who read a newspaper daily do better in the general-awareness section.\n\nWhich of the following, if true, most strengthens the argument?",
      "Among 2,000 similar aspirants, daily newspaper readers scored far higher in general awareness.",
      [("Newspapers are printed late at night and delivered early in the morning.", "irrelevant"),
       ("Some newspapers cost more than others because they carry more pages and supplements.", "irrelevant"),
       ("Many aspirants now read the news on their phones instead of buying a printed newspaper.", "does not show better performance")],
      ["Comparative evidence with similar backgrounds supports the link."], "Supporting evidence with controls", "Choose evidence that links the cause to the outcome.")
    S("foundation", "L2", "Argument: The new medicine cures this type of fever, because all ten patients who took it recovered within three days.\n\nWhich of the following, if true, most weakens the argument?",
      "Such fevers normally subside within three days even without any medicine.",
      [("The medicine is given as a tablet twice a day, after meals, for three days.", "irrelevant"),
       ("All ten patients in the trial were adults aged between 20 and 50 years.", "limits scope slightly but does not undercut the cure claim"),
       ("The medicine is manufactured by a company based in India.", "irrelevant")],
      ["If recovery happens anyway, the medicine's effect is not shown."], "Natural recovery weakens a cure claim", "Ask what would have happened without the cause.")
    S("officer", "L3", "Argument: Within six months of the city making bus travel free for women, women's use of public transport rose by 25%. Fare-free travel is therefore the key to getting more women onto public transport.\n\nWhich of the following, if true, most weakens the argument?",
      "The city also added 300 buses in that period, and men's ridership rose by a similar 25%.",
      [("Women make up roughly half of the city's population, according to the latest census data.", "irrelevant"),
       ("The scheme costs the city a substantial amount of money every month.", "a cost, not evidence against the effect"),
       ("Some women were already travelling on monthly passes before the scheme began last year.", "does not explain the rise")],
      ["An equal rise among men (who pay) points to better service, not free fares, as the driver."], "Rival explanation with comparison group", "Check whether the change is specific to the group affected.")
    S("officer", "L3", "Argument: Since the bank began offering loans through its mobile app, its loan disbursals have risen by 40%. The app is therefore responsible for the growth.\n\nWhich of the following, if true, most strengthens the argument?",
      "Similar banks without such apps saw flat disbursals, and 90% of new loans came via the app.",
      [("Interest rates on loans fell across the banking industry during the same period.", "rival explanation — weakens"),
       ("The bank also trained all its branch staff in selling loan products during the same year.", "rival explanation — weakens"),
       ("The app was designed and is maintained by an outside technology firm based in Bengaluru.", "irrelevant")],
      ["A flat comparison group and the channel data both tie the growth to the app."], "Eliminate rival explanations", "Industry-wide changes weaken a claim about one cause.")
    S("officer", "L3", "Argument: Company A should acquire Company B, because B's sales grew by 60% last year.\n\nWhich of the following, if true, most weakens the argument?",
      "B's growth came from a one-time government order, and its regular sales are falling.",
      [("B is located in a different state from the one that houses A's headquarters and factories.", "minor"),
       ("A's chief executive officer worked at B as a senior manager several years ago.", "irrelevant"),
       ("B's sales had also grown steadily in each of the three previous years.", "strengthens")],
      ["If the growth will not continue, it is a poor basis for acquisition."], "Unrepresentative data weaken a conclusion", "Ask whether past performance will continue.")
    S("officer", "L3", "Argument: Cities with more gyms have lower rates of heart disease, so building more gyms will reduce heart disease.\n\nWhich of the following, if true, most weakens the argument?",
      "Gyms tend to open in richer cities, where people also eat better and get better healthcare.",
      [("Most gyms in these cities charge a fixed monthly membership fee along with an entry fee.", "irrelevant"),
       ("Some of the gyms in these cities also have swimming pools and saunas.", "irrelevant"),
       ("Heart disease is one of the leading causes of death in many countries around the world.", "irrelevant background")],
      ["A third factor (wealth) may explain both gyms and lower disease."], "Correlation vs causation (confounder)", "A common cause undermines a causal inference from correlation.")
    S("officer", "L3", "Argument: Introducing a congestion charge in the central business district will reduce traffic jams there.\n\nWhich of the following, if true, most strengthens the argument?",
      "In a comparable city, a similar charge cut peak-hour traffic in its zone by about 20%.",
      [("Many motorists say that they dislike paying any charge at all to enter the district.", "dislike does not show reduced traffic"),
       ("The central business district contains a large number of offices.", "irrelevant background"),
       ("The charge will be collected electronically through cameras installed at all entry points.", "implementation detail")],
      ["Evidence from a comparable case supports the predicted effect."], "Analogy with a comparable case", "Evidence of effect beats statements of attitude.")
    S("officer", "L3", "Plan: A state plans to raise farm incomes by distributing high-yield seeds free of cost.\n\nWhich of the following, if true, casts the most doubt on the plan's success?",
      "The high-yield seeds need assured irrigation, which only 20% of the state's farmland has.",
      [("The seeds will be packed in bags printed with sowing instructions in the local language.", "irrelevant/supportive"),
       ("Farmers in the state have generally welcomed free inputs supplied by the government.", "supportive"),
       ("The state is divided into thirty districts and over two hundred blocks for administration.", "irrelevant")],
      ["If most farms cannot use the seeds, incomes will not rise much."], "Missing precondition undermines a plan", "Look for a condition the plan depends on.")
    S("officer", "L3", "Argument: Online classes are as effective as classroom teaching, since the online batch's average score equalled the classroom batch's.\n\nWhich of the following, if true, most weakens the argument?",
      "Students chose their batch, and the online group had scored far higher the previous year.",
      [("The online classes were delivered through a mix of recorded and live video sessions.", "irrelevant"),
       ("Classroom sessions for the other batch were held in the morning hours on weekdays.", "irrelevant"),
       ("Both batches followed the same syllabus and used the same textbooks.", "strengthens comparability")],
      ["A stronger online group only equalling the other suggests online teaching was less effective."], "Selection bias", "Check that the groups compared were alike to begin with.")
    S("officer", "L3", "Argument: A retailer's sales fell last quarter because a competitor opened stores nearby.\n\nWhich of the following, if true, most strengthens the argument?",
      "Sales fell only at outlets near the competitor's new stores; other outlets held steady.",
      [("Overall consumer spending in the country fell sharply during the same quarter.", "rival explanation — weakens"),
       ("The retailer mainly sells groceries and household goods at its outlets across the city.", "irrelevant"),
       ("The competitor's founder is a well-known and widely admired figure in the retail industry.", "irrelevant")],
      ["The fall is localised exactly where the competitor opened — supports the cause."], "Localised effect supports a specific cause", "Economy-wide factors would affect all outlets.")
    S("officer", "L3", "Plan: Giving free bicycles to girls in rural secondary schools will reduce their dropout rate.\n\nWhich of the following, if true, most supports the plan?",
      "Local surveys show that distance to the nearest secondary school is the main reason girls drop out.",
      [("Bicycles are relatively inexpensive compared with most other means of personal transport.", "cost, not effectiveness"),
       ("Boys studying in the same schools have also asked the state for free bicycles of their own.", "irrelevant"),
       ("Secondary schools in these areas begin their classes at 10 a.m. on every working day.", "irrelevant")],
      ["The plan targets the main cause of dropout."], "Plan matches the cause", "Support for a plan shows it addresses the real cause.")
    S("officer", "L3", "Argument: The rise in the number of people filing income-tax returns shows that incomes in the country have risen.\n\nWhich of the following, if true, most weakens the argument?",
      "The rise followed a rule requiring returns for large deposits, even below the taxable limit.",
      [("The income-tax department allows returns to be filed online through its official website.", "irrelevant"),
       ("Some people file their returns after the due date and pay a late fee along with interest.", "irrelevant"),
       ("Salaries in several sectors of the economy rose during the period.", "strengthens")],
      ["A rule change explains the rise without any increase in income."], "Rival explanation", "A procedural change can inflate a count.")


def add_all(B):
    assumptions(B); courses(B); arguments(B); inferences(B); cause_effect(B); strengthen_weaken(B)
