"""MGT part 2 — motivation theories, reinforcement, incentives, morale, perception, Pygmalion."""
from mgt_common import cq, nq, stmt, ar, match, inr, R, pct


def add_all(B):
    # ================================================================ Maslow
    cq(B, "maslow", "L1",
       "In Maslow's hierarchy, the need for friendship, affection and acceptance by a group is classified as:",
       "Social (belongingness) need",
       [("Esteem (recognition) need", "esteem = self-respect, status, recognition"),
        ("Safety (security) need", "safety = protection from physical and economic harm"),
        ("Self-actualisation (growth) need", "self-actualisation = realising one's full potential")],
       ["Order: physiological → safety → social (belongingness) → esteem → self-actualisation."],
       "Recognition and status are esteem, not social, needs.")

    cq(B, "maslow", "L2",
       "Ravi, an officer with a secure job, good pay and close friends at work, says: \"I want colleagues to respect my expertise and I want a title that reflects it.\" According to Maslow, the need now dominating Ravi's behaviour is:",
       "Esteem need",
       [("Social need", "his belongingness needs are already met (close friends at work)"),
        ("Self-actualisation need", "he seeks respect and status from others, not realisation of potential for its own sake"),
        ("Safety need", "his job security is already satisfied")],
       ["Lower needs (physiological, safety, social) are largely satisfied.",
        "Desire for respect, recognition and title = esteem."],
       "A satisfied need no longer motivates; look for the lowest unsatisfied need.")

    stmt(B, "maslow", "L3",
         "Consider the following statements on Maslow's need hierarchy:",
         [("A substantially satisfied need no longer motivates behaviour", True, "core proposition"),
          ("If a higher-order need is frustrated, a person regresses to a lower-order need — the frustration-regression principle — is a central part of Maslow's theory", False,
           "frustration-regression is Alderfer's ERG addition, not Maslow's"),
          ("Physiological and safety needs are called lower-order needs, while social, esteem and self-actualisation needs are higher-order needs", True,
           "common classification (Robbins)"),
          ("Maslow did not require a need to be fully (100%) satisfied before the next higher need begins to emerge", True,
           "he described partial, overlapping satisfaction of needs")],
         "ERG (Alderfer) adds frustration-regression; do not attribute it to Maslow.")

    # ================================================================ Herzberg
    cq(B, "herzberg", "L1",
       "According to Herzberg, which of the following is a MOTIVATOR?",
       "Recognition for achievement",
       [("Salary", "salary is a hygiene factor in Herzberg's classification"),
        ("Company policy and administration", "the most frequently cited hygiene factor"),
        ("Working conditions", "hygiene (extrinsic, context) factor")],
       ["Motivators (intrinsic, job content): achievement, recognition, work itself, responsibility, advancement, growth."],
       "Salary is the most-tested trap: it is hygiene.")

    stmt(B, "herzberg", "L3",
         "An HR team classifies the following as hygiene factors under Herzberg's theory:",
         [("Job security", True, "security is a hygiene factor"),
          ("Relationship with supervisor", True, "interpersonal relations with supervisor = hygiene"),
          ("Opportunity for advancement", False, "advancement is a motivator"),
          ("Status", True, "Herzberg lists status among hygiene factors")],
         "Status sounds like esteem (a 'higher' need) but Herzberg lists it as hygiene.",
         ask="Which of the above are correctly classified as hygiene factors?")

    ar(B, "herzberg", "L2",
       "According to Herzberg, improving working conditions and pay may remove dissatisfaction without necessarily motivating employees.",
       "Herzberg held that the opposite of 'satisfaction' is 'no satisfaction' and the opposite of 'dissatisfaction' is 'no dissatisfaction'.",
       0,
       ["A true — hygiene factors only prevent dissatisfaction.",
        "R true — satisfaction and dissatisfaction are separate continua in Herzberg's model.",
        "R is precisely why better hygiene yields 'no dissatisfaction' rather than motivation."],
       "The dual-continuum idea is the reason, not just another fact.")

    cq(B, "herzberg", "L3",
       "A fintech doubles its office amenities and gives an across-the-board pay revision. Complaints drop sharply, but productivity and initiative remain unchanged. Six months later, it redesigns roles so that analysts own client portfolios end-to-end with visible results, and initiative rises. Which theory best explains BOTH outcomes?",
       "Herzberg's two-factor theory — hygiene fixes cut dissatisfaction; enrichment (motivators) raised motivation",
       [("Maslow's hierarchy — pay satisfied physiological needs, so employees then moved to self-actualisation", "Maslow would predict pay/amenities could motivate while those needs were unmet; it does not explain 'complaints drop, motivation unchanged'"),
        ("McGregor's Theory X — employees inherently dislike work and respond only once they are closely controlled", "the firm used enrichment, not control, and it worked — a Theory Y outcome at most"),
        ("Vroom's expectancy theory — expectancy was zero for the amenities, so motivational force stayed at zero", "expectancy concerns effort-performance belief, not amenities vs job content")],
       ["Pay/amenities = hygiene → 'no dissatisfaction' (fewer complaints) but no motivation.",
        "Ownership, responsibility, visible achievement = motivators → higher initiative."],
       "The two-stage pattern (complaints fall first, motivation rises only with job content) is Herzberg's signature.")

    # ================================================================ McGregor
    cq(B, "mcgregor", "L1",
       "Douglas McGregor presented Theory X and Theory Y in:",
       "The Human Side of Enterprise (1960)",
       [("Motivation and Personality (1954)", "that is Maslow's book"),
        ("Theory Z: How American Business Can Meet the Japanese Challenge (1981)", "that is William Ouchi's Theory Z"),
        ("The Motivation to Work (1959)", "that is Herzberg, Mausner and Snyderman")],
       ["McGregor, The Human Side of Enterprise, 1960."],
       "Theory Z is Ouchi, not McGregor.", verify=True, ref="Publication details of classical OB texts")

    match(B, "mcgregor", "L3",
          "Match the managerial assumption with the theory it belongs to:",
          ["The average person inherently dislikes work and will avoid it if possible",
           "People will exercise self-direction and self-control towards objectives to which they are committed",
           "Long-term employment, collective decision-making and holistic concern for employees",
           "Employees are motivated primarily by money and need close supervision"],
          ["Theory X", "Theory Y", "Theory Z (Ouchi)", "Scientific management's 'economic man'"],
          [1, 2, 3, 4],
          [((2, 1), "attributes Ouchi's Japanese-style Theory Z to McGregor's Theory Y"),
           ((0, 3), "treats Theory X as identical to Taylor's economic-man view"),
           ((0, 1), "reverses Theory X and Theory Y")],
          ["Dislike of work → Theory X.", "Self-direction when committed → Theory Y.",
           "Lifetime employment, consensus → Ouchi's Theory Z.", "Money + close supervision → economic man (Taylorist)."],
          "Theory X overlaps with economic-man thinking, but the specific 'inherent dislike of work' statement is McGregor's Theory X.")

    cq(B, "mcgregor", "L2",
       "A branch head removes attendance registers, lets officers set their own quarterly targets with her, and expects them to seek responsibility. McGregor would say she operates on:",
       "Theory Y assumptions",
       [("Theory X assumptions", "Theory X managers rely on control and threat"),
        ("Theory Z assumptions", "Theory Z (Ouchi) concerns lifetime employment and collective decisions"),
        ("Hygiene assumptions", "hygiene is Herzberg's term, not an assumption set about human nature")],
       ["Self-direction, participation, seeking responsibility → Theory Y."],
       "Theory Z is a common trap because it sounds like 'the next step' after Y.")

    # ================================================================ McClelland
    cq(B, "mcclelland", "L2",
       "Anita prefers tasks with moderate risk, wants quick and concrete feedback on her performance, and likes to take personal responsibility for solving problems. According to McClelland, she has a high need for:",
       "Achievement (nAch)",
       [("Power (nPow)", "nPow is the desire to influence and control others"),
        ("Affiliation (nAff)", "nAff is the desire for friendly, close relationships"),
        ("Self-actualisation", "a Maslow need, not one of McClelland's three")],
       ["High achievers: moderate risk, feedback, personal responsibility."],
       "High achievers avoid very easy AND very hard tasks — moderate risk is the tell.")

    stmt(B, "mcclelland", "L3",
         "With reference to McClelland's acquired-needs theory, consider:",
         [("Needs are measured using projective techniques such as the Thematic Apperception Test (TAT)", True, "TAT is McClelland's method"),
          ("A high need for achievement automatically makes a person an effective manager of a large organisation", False,
           "high achievers focus on their own accomplishment; effective large-organisation managers tend to have high institutional power and low affiliation"),
          ("Needs are learned through life experiences rather than being innate", True, "hence 'acquired' or 'learned' needs"),
          ("McClelland distinguished personalised power from socialised (institutional) power", True, "socialised power serves organisational goals")],
         "Best managers: high socialised nPow, low nAff — not necessarily high nAch.")

    cq(B, "mcclelland", "L3",
       "For the post of zonal head of a large public-sector bank, which need profile would McClelland's research suggest is most likely to lead to managerial effectiveness?",
       "High socialised power, low affiliation, moderate achievement",
       [("High achievement, low power, high affiliation", "high nAch favours individual contribution; high nAff hampers tough decisions"),
        ("High personalised power, low affiliation, high achievement", "personalised power seeks personal dominance, not organisational goals"),
        ("High affiliation, high socialised power, low achievement", "high affiliation leads to favouritism and avoidance of conflict")],
       ["McClelland & Burnham ('Power is the Great Motivator', HBR 1976): good managers have high institutional power, low affiliation, and self-control."],
       "The 'leadership motive pattern' is power-dominant, not achievement-dominant.")

    # ================================================================ Vroom
    E, I, V = 0.7, 0.6, -0.5
    mf = E * I * V
    nq(B, "vroom", "L2",
       f"An officer believes there is a {E} probability that extra effort will lead to top performance, and a {I} probability that top performance will lead to a transfer to the head office. He dislikes the head-office posting (valence {V}). Under Vroom's model, his motivational force towards extra effort is:",
       f"{mf:.2f}",
       [(f"{abs(mf):.2f}", "ignores the negative sign of valence"),
        (f"{E+I+V:.2f}", "adds E, I and V instead of multiplying"),
        (f"{E*I:.2f}", "ignores valence altogether")],
       [f"MF = E × I × V = {E} × {I} × ({V}) = {mf:.2f}", "Negative MF → he will avoid extra effort."],
       "Motivational force = Expectancy × Instrumentality × Valence",
       "A negatively valued outcome makes the product negative — strong expectancy then strengthens avoidance.")

    ar(B, "vroom", "L3",
       "Under Vroom's expectancy theory, an employee who values a promotion highly may still exert little effort.",
       "Motivational force is the product of expectancy, instrumentality and valence, so if any one of them is near zero, the force is near zero.",
       0,
       ["A true — high valence alone is insufficient.",
        "R true — the multiplicative form means a zero E or I makes MF ≈ 0.",
        "R explains A."],
       "Additive reasoning ('high valence compensates') is the trap.")

    match(B, "vroom", "L3",
          "Match the employee statement with the Vroom component it reflects:",
          ["\"However hard I try, I can't meet this target with the current software.\"",
           "\"Even if I hit the target, the bonus goes to whoever the manager likes.\"",
           "\"A trip to the head office conference means nothing to me.\"",
           "\"Hitting the target also gets me a meeting with the CEO, which leads to promotion.\""],
          ["Low expectancy", "Low instrumentality", "Low valence", "Second-level outcome linked through instrumentality"],
          [1, 2, 3, 4],
          [((0, 1), "confuses the effort→performance link (E) with the performance→reward link (I)"),
           ((1, 2), "confuses distrust of the reward system (I) with not valuing the reward (V)"),
           ((2, 3), "treats a valued second-level outcome as a valence problem")],
          ["E: effort → performance belief.", "I: performance → reward belief.", "V: value of the reward.",
           "First-level outcome (meeting target) is instrumental to second-level outcomes (promotion)."],
          "E and I are both probabilities — distinguish by which link the employee doubts.")

    # ================================================================ reward & punishment / reinforcement
    cq(B, "reward-and-punishment", "L1",
       "The 'carrot and stick' approach to motivation relies on:",
       "Rewards for desired performance and threat of penalties for poor performance",
       [("Making the work itself intrinsically satisfying through job enrichment", "that is Herzberg's motivator route"),
        ("Participative goal setting jointly with subordinates for each period", "that is MBO / Theory Y"),
        ("Deliberately removing hygiene factors to create productive tension", "not a recognised approach")],
       ["Carrot = reward (usually money); stick = fear of punishment (loss of job, pay cut)."],
       "It is an external (extrinsic) approach resting largely on Theory X assumptions.")

    cq(B, "reward-and-punishment", "L3",
       "A regional manager tells officers: \"Anyone who clears all pending KYC cases by Thursday will be exempted from the mandatory Saturday review meeting.\" In reinforcement terms, the exemption is:",
       "Negative reinforcement — an unpleasant condition is removed",
       [("Punishment — an unpleasant consequence is imposed", "nothing unpleasant is imposed; one is taken away"),
        ("Positive reinforcement — a pleasant consequence is added", "no reward is added; an aversive meeting is removed"),
        ("Extinction — reinforcement is withheld to weaken behaviour", "extinction weakens behaviour by withholding reinforcement")],
       ["Removing an aversive stimulus (Saturday meeting) contingent on desired behaviour increases that behaviour → negative reinforcement."],
       "'Negative' means removal, not 'bad'; negative reinforcement strengthens behaviour, punishment weakens it.")

    match(B, "reward-and-punishment", "L3",
          "Match each manager action with the reinforcement type (Skinner / operant conditioning):",
          ["Public praise and a gift voucher for the month's best service score",
           "Ignoring an officer's attention-seeking jokes in meetings until they stop",
           "Deducting incentive points for repeated late logins",
           "Waiving an officer's evening report once her error rate falls below 1%"],
          ["Positive reinforcement", "Extinction", "Punishment", "Negative reinforcement"],
          [1, 2, 3, 4],
          [((2, 3), "confuses punishment with negative reinforcement — the most common error"),
           ((1, 2), "confuses withholding reinforcement (extinction) with punishment"),
           ((0, 3), "treats removal of an aversive task as a positive reinforcer")],
          ["Adding pleasant → positive reinforcement.", "Withholding reinforcement → extinction.",
           "Taking away something valued / adding unpleasant → punishment.", "Removing unpleasant → negative reinforcement."],
          "Two strengthen (positive & negative reinforcement), two weaken (punishment, extinction).")

    # ================================================================ incentives
    cq(B, "incentives-vs-rewards", "L2",
       "Which statement best distinguishes an incentive from a reward?",
       "An incentive is announced in advance to induce behaviour; a reward is given after performance",
       [("An incentive is always non-monetary in nature, whereas a reward is always paid out in money", "both can be monetary or non-monetary"),
        ("An incentive is given for past performance, while a reward is promised for future performance", "the timing is reversed"),
        ("Incentives are meant only for groups of employees; rewards are given only to individuals", "either can be individual or group")],
       ["Incentive: ex-ante, conditional ('achieve X, get Y').", "Reward: ex-post, recognition of results or behaviour already shown."],
       "Timing (before vs after) is the key axis, not money vs non-money.")

    stmt(B, "incentives-vs-rewards", "L3",
         "Consider the following:",
         [("A pre-announced sales contest prize is primarily an incentive", True, "announced before performance to induce effort"),
          ("A surprise 'thank-you' award after a crisis is primarily a reward", True, "given after the fact, not promised in advance"),
          ("Once an incentive is paid on achievement of the target, it also functions as a reward for that performance", True,
           "the same payment is incentive ex-ante and reward ex-post"),
          ("Rewards that are unexpected cannot influence future behaviour", False, "they signal valued behaviour and can reinforce it")],
         "Incentive and reward can be the same payment seen from different points in time.")

    cq(B, "financial-vs-non-financial", "L1",
       "Which of the following is a NON-financial incentive?",
       "Employee empowerment",
       [("Co-partnership / employee stock option", "gives a financial stake in the company"),
        ("Productivity-linked wage incentive", "a direct monetary payment"),
        ("Retirement benefits such as provident fund and gratuity", "monetary benefits")],
       ["Non-financial: status, organisational climate, career advancement, job enrichment, recognition, job security, participation, empowerment."],
       "Perquisites (car, housing) are financial even though they are not cash.")

    stmt(B, "financial-vs-non-financial", "L3",
         "In the commonly used classification of incentives, consider which are FINANCIAL incentives:",
         [("Perquisites such as a company car and housing", True, "monetary value; classed as financial"),
          ("Job security", False, "classified as a non-financial incentive"),
          ("Profit sharing", True, "share in profits → financial"),
          ("Career advancement opportunity", False, "non-financial, even though promotion brings pay")],
         "Job security and career advancement bring money indirectly but are classed as non-financial.",
         ask="Which of the above are financial incentives?")

    st, tt, rate = 10, 8, 150
    saved = st - tt
    halsey = tt * rate + 0.5 * saved * rate
    rowan = tt * rate + saved / st * tt * rate
    assert (halsey, rowan) == (1350, 1440)
    nq(B, "financial-vs-non-financial", "L3",
       f"A job has a standard time of {st} hours. A worker completes it in {tt} hours; the time rate is ₹{rate} per hour. What are the worker's earnings under the Halsey plan (50% sharing) and the Rowan plan?",
       f"Halsey {R(halsey)}; Rowan {R(rowan)}",
       [(f"Halsey {R(rowan)}; Rowan {R(halsey)}", "swaps the two plans"),
        (f"Halsey {R(tt*rate + saved*rate)}; Rowan {R(rowan)}", "gives 100% of time saved under Halsey (that is straight piece rate)"),
        (f"Halsey {R(halsey)}; Rowan {R(tt*rate + saved/tt*tt*rate)}", "Rowan ratio taken as time saved ÷ time taken")],
       [f"Time saved = {st} − {tt} = {saved} h", f"Halsey = {tt}×{rate} + 50%×{saved}×{rate} = {R(halsey)}",
        f"Rowan = {tt}×{rate} + ({saved}/{st})×{tt}×{rate} = {R(rowan)}"],
       "Halsey = TT×R + 50%×TS×R;  Rowan = TT×R + (TS/ST)×TT×R",
       "Rowan's bonus ratio uses standard time as the base; it self-limits as time saved grows.")

    cq(B, "role-of-incentives-in-building-morale", "L2",
       "A plant replaces individual piece-rate bonuses (which caused workers to hoard jobs and refuse to help each other) with a plan under which savings in labour cost are shared with all employees and suggestions are reviewed by joint committees. This plan is known as, and mainly aims at:",
       "Scanlon plan — building group cooperation and morale through shared gains",
       [("Rowan plan — rewarding each worker's time saved in proportion", "Rowan is an individual premium bonus"),
        ("Halsey plan — sharing each worker's time saved 50:50 with the firm", "Halsey is an individual premium bonus"),
        ("Merrick multiple piece rate — graded rates for efficiency bands", "an individual differential rate plan")],
       ["Scanlon plan: plant-wide gainsharing on labour-cost savings with suggestion committees.",
        "Group incentives reinforce cooperation and morale where individual schemes create rivalry."],
       "Individual schemes can hurt group morale; the fix here is a group gainsharing plan.")

    ar(B, "role-of-incentives-in-building-morale", "L3",
       "A well-designed incentive system can raise employee morale.",
       "Incentives only raise morale when they are purely financial, since non-financial incentives do not affect attitudes.",
       2,
       ["A true — fair, performance-linked, understood incentives raise confidence and group spirit.",
        "R false — recognition, participation, job security and climate (non-financial) strongly shape morale."],
       "Morale is an attitude; non-financial incentives often affect it more than money.")

    # ================================================================ morale
    cq(B, "concept-of-morale", "L1",
       "Employee morale is best described as:",
       "The collective attitude, confidence and team spirit of employees towards the organisation",
       [("The inner drive that makes an individual act towards achieving a personal goal", "that is motivation"),
        ("The total monetary and non-monetary compensation received by employees in a year", "compensation is only one factor affecting morale"),
        ("The formal authority vested in a manager to command and discipline subordinates", "unrelated — that is authority")],
       ["Morale = group/collective mental state of enthusiasm, confidence and willingness to cooperate."],
       "Motivation is individual and goal-directed; morale is attitudinal and largely collective.")

    stmt(B, "concept-of-morale", "L3",
         "Consider the following statements on morale:",
         [("High morale always results in high productivity", False,
           "high morale with low productivity is possible when goals are unclear or supervision is weak"),
          ("Rising absenteeism, labour turnover and grievances are common indicators of low morale", True, "standard indicators"),
          ("Morale can be measured through attitude surveys and exit interviews", True, "standard methods"),
          ("Low morale can co-exist with high productivity for a time under strict supervision or fear of job loss", True, "Davis's combinations")],
         "The morale–productivity link is not automatic; all four combinations are possible.")

    cq(B, "factors-determining-morale", "L2",
       "A survey at an insurer shows employees find the work interesting and pay competitive, yet morale is low. Comments repeatedly mention 'managers take credit for our ideas' and 'no one explains decisions'. The factor most responsible is:",
       "Quality of supervision and management attitude",
       [("Nature of work and task variety", "employees find the work interesting"),
        ("Compensation levels relative to the market", "pay is described as competitive"),
        ("Physical working conditions in the office", "not mentioned in the survey")],
       ["Credit-taking and lack of explanation point to supervisory behaviour and communication.",
        "Supervision is one of the strongest determinants of morale."],
       "Eliminate factors the stem says are satisfactory before choosing.")

    stmt(B, "factors-determining-morale", "L2",
         "Which of the following are generally recognised as factors determining employee morale?",
         [("Organisational policies and their fairness in application", True, "fair policies build confidence"),
          ("Peer relationships and group cohesiveness", True, "social factors shape collective attitude"),
          ("The employee's self-perception, health and personal circumstances", True, "individual factors also influence morale"),],
         "Morale is shaped by organisational, group and individual factors together.",
         ask="Select the correct answer using the code given below.")

    cq(B, "morale-vs-motivation", "L1",
       "Which of the following correctly contrasts morale and motivation?",
       "Motivation is an individual's inner drive to act; morale is a group's collective attitude",
       [("Morale is an individual's inner drive; motivation is a group's collective attitude", "reversed"),
        ("Both mean the same thing and the terms can be used interchangeably in HR practice", "they are related but distinct concepts"),
        ("Motivation is measured by attitude surveys, while morale is measured by output per worker", "morale is measured by attitude surveys; output is a result, not a direct measure of either")],
       ["Motivation = drive to act (individual, goal-directed).", "Morale = attitude/feeling of a group (collective)."],
       "Motivation raises willingness to work; morale reflects the mood about work and the organisation.")

    ar(B, "morale-vs-motivation", "L2",
       "It is possible for a highly motivated individual to work in a group whose morale is low.",
       "Motivation is primarily an individual phenomenon, while morale is primarily a group phenomenon.",
       0,
       ["A true — an ambitious officer may be driven by personal goals even in a demoralised team.",
        "R true — the distinction between individual drive and collective attitude is exactly why they can diverge.",
        "R explains A."],
       "Because they operate at different levels, one can be high while the other is low.")

    # ================================================================ perception & Pygmalion
    cq(B, "perception", "L2",
       "In a classic study, executives from sales, production and accounting read the same business case; each group identified problems in its own functional area as the key issue. This illustrates:",
       "Selective perception",
       [("Halo effect", "halo is generalising from one trait of a person"),
        ("Projection", "projection attributes one's own traits to others"),
        ("Contrast effect", "contrast effect is evaluation influenced by comparison with recently seen others")],
       ["Dearborn & Simon (1958): people perceive what fits their background, interests and experience."],
       "Selective perception filters information; halo distorts evaluation of a person.")

    match(B, "perception", "L3",
          "Match the perceptual error with the example:",
          ["Halo effect", "Contrast effect", "Projection", "Stereotyping"],
          ["An interviewer rates a candidate 'excellent in all respects' because she is very articulate",
           "An average candidate is rated poor because he was interviewed right after two outstanding ones",
           "A manager who dislikes change assumes his team also resists all change",
           "A recruiter assumes all candidates from a particular city are unreliable"],
          [1, 2, 3, 4],
          [((0, 1), "confuses halo (one trait → overall) with contrast (comparison with others)"),
           ((2, 3), "confuses projection (own traits) with stereotyping (group traits)"),
           ((0, 3), "confuses generalising from one trait with generalising from group membership")],
          ["Halo: one salient trait colours overall judgement.", "Contrast: judged relative to others just seen.",
           "Projection: own feelings attributed to others.", "Stereotyping: judged by group membership."],
          "Halo = one trait → whole person; stereotype = group → individual.")

    stmt(B, "perception", "L3",
         "With reference to attribution theory (Kelley), consider:",
         [("High distinctiveness, high consensus and low consistency lead to an external attribution", True, "classic external pattern"),
          ("The fundamental attribution error is the tendency to underestimate external factors and overestimate internal factors when judging others' behaviour", True, "definition"),
          ("Self-serving bias is attributing one's own successes to external factors and failures to internal factors", False,
           "reversed — own successes to internal, failures to external factors")],
         "Self-serving bias protects self-esteem: success = me, failure = circumstances.")

    cq(B, "pygmalion", "L1",
       "The Pygmalion effect in management refers to:",
       "A manager's high expectations leading to higher performance by subordinates",
       [("An employee's own strong belief in her ability raising her performance", "that is the Galatea effect"),
        ("Low expectations of a manager depressing subordinates' performance", "that is the Golem effect"),
        ("Rating an employee high on all traits because of one outstanding trait", "that is the halo effect")],
       ["Rosenthal & Jacobson (1968) in classrooms; J. Sterling Livingston, 'Pygmalion in Management' (HBR, 1969).",
        "Others' high expectations → self-fulfilling prophecy of high performance."],
       "Pygmalion (others' high expectations), Galatea (self-expectation), Golem (others' low expectations).")

    ar(B, "pygmalion", "L2",
       "The Pygmalion effect refers to an employee's own high expectations of herself raising her performance.",
       "Expectations are communicated through a manager's behaviour — more attention, feedback, challenging assignments — and can become self-fulfilling prophecies.",
       3,
       ["A false — self-expectation raising performance is the Galatea effect; Pygmalion is the effect of OTHERS' (e.g., the manager's) high expectations.",
        "R true — the behavioural mechanism behind Pygmalion-type self-fulfilling prophecies."],
       "Pygmalion = others' expectations; Galatea = self-expectation; Golem = others' low expectations.")

    # ================================================================ CASE C — call centre motivation
    stemC = ("**Case — Arcadia General Insurance, Pune service hub.** Attrition among 300 claims associates has risen. HR's findings:\n\n"
             "- Associates rate pay and canteen facilities as 'satisfactory' but describe the work as 'repetitive and invisible'.\n"
             "- Two incentive schemes are proposed. Associates' average estimates are:\n\n"
             "| Scheme | Expectancy (E) | Instrumentality (I) | Valence (V) |\n|---|---:|---:|---:|\n"
             "| P — top-10 league-table cash prize | 0.9 | 0.4 | 1.0 |\n| Q — skill-based pay step on certification | 0.6 | 0.8 | 0.8 |\n\n"
             "- Team leader Sunita sets hard-but-reachable personal targets, asks for daily feedback on her numbers and dislikes delegating.\n"
             "- Manager Kiran told a new team: \"You are the best batch we have hired.\" Within months they outperformed older teams.\n\n")
    g = "MGT-CASE-ARCADIA"
    Ps = (0.9, 0.4, 1.0); Qs = (0.6, 0.8, 0.8)
    mfP = Ps[0] * Ps[1] * Ps[2]; mfQ = Qs[0] * Qs[1] * Qs[2]
    assert mfQ > mfP and sum(Ps) > sum(Qs)
    nq(B, "vroom", "L4", stemC + "Using Vroom's model, which scheme generates the higher motivational force, and what is it?",
       f"Scheme Q; {mfQ:.3f}",
       [(f"Scheme P; {sum(Ps):.1f}", "adds E + I + V, which favours P"),
        (f"Scheme P; {mfP:.3f}", "reports P's product though it is lower than Q's"),
        (f"Scheme P; {Ps[0]*Ps[2]:.2f}", "ignores instrumentality (the weak link in P)")],
       [f"MF(P) = 0.9 × 0.4 × 1.0 = {mfP:.3f}", f"MF(Q) = 0.6 × 0.8 × 0.8 = {mfQ:.3f}", "Q is higher."],
       "MF = E × I × V", "P's low instrumentality (only 10 winners) drags the product down despite high E and V.", group=g)
    cq(B, "herzberg", "L4", stemC + "Based on Herzberg's theory, the associates' comments on pay and on the work suggest that HR should mainly:",
       "Enrich the job — responsibility, visible outcomes, recognition — as hygiene is already adequate",
       [("Raise pay further, since pay is the strongest and most lasting motivator of associates", "pay is hygiene; associates already call it satisfactory"),
        ("Improve canteen and working conditions, as better amenities will raise motivation", "hygiene improvements remove dissatisfaction but do not motivate"),
        ("Tighten supervision and attendance monitoring to reduce attrition quickly", "supervision is a hygiene factor and control does not create motivation")],
       ["Pay/facilities (hygiene) are adequate → no dissatisfaction.", "'Repetitive and invisible' work → motivators missing → enrich job content."],
       "Treat the stem's 'satisfactory' as a signal that hygiene is not the lever.", group=g)
    cq(B, "mcclelland", "L4", stemC + "Sunita's behaviour most closely matches which McClelland profile, and what is the likely risk as she is promoted?",
       "High nAch — she may struggle to delegate and develop others in a larger role",
       [("High nPow — she may misuse her power over the team as she rises higher", "she seeks personal accomplishment and feedback, not influence over others"),
        ("High nAff — she may avoid hard decisions in order to stay liked by all", "no sign of seeking approval or close ties"),
        ("High socialised power — the ideal profile for promotion to larger roles", "reluctance to delegate is not a power-motive pattern")],
       ["Moderate-risk targets + feedback + personal responsibility → nAch.",
        "Research: high achievers may not make the best managers of large units because they prefer doing to delegating."],
       "nAch predicts entrepreneurial/individual success, not necessarily managerial success.", group=g)
    cq(B, "pygmalion", "L4", stemC + "The outcome in Kiran's team is best explained by:",
       "Pygmalion effect — the manager's high expectations became a self-fulfilling prophecy",
       [("Galatea effect — the associates' own self-expectations rose independently", "the trigger is the manager's expectation"),
        ("Hawthorne effect — performance rose merely because they were being observed", "observation is not the described cause"),
        ("Halo effect — the manager rated the team high because of one trait", "halo is a rating error, not a performance change")],
       ["The manager communicated high expectations; performance rose — Pygmalion."],
       "Hawthorne is about being observed/attended to; Pygmalion is about expectations.", group=g)
    stmt(B, "reward-and-punishment", "L4", stemC + "HR also considers these measures. Which are correctly labelled?",
         [("Dropping the monthly 'error review' meeting for associates with zero errors — negative reinforcement", True, "aversive event removed to strengthen behaviour"),
          ("Publishing the names of bottom-10 associates on the notice board — positive reinforcement", False, "it adds an unpleasant consequence → punishment"),
          ("Scheme Q (pay step on certification) — a pre-announced incentive that also becomes a reward once earned", True, "incentive ex-ante, reward ex-post"),],
         "Naming and shaming is punishment regardless of intent.", group=g,
         ask="Which of the labels given above is/are correct?")

    # ================================================================ CASE D — morale at a bank
    op, cl, sep, acc, repl = 180, 220, 24, 64, 18
    assert op + acc - sep == cl
    avg = (op + cl) / 2
    sep_rate = sep / avg; repl_rate = repl / avg; flux = (sep + repl) / avg
    days, lost = 25, 350
    sched = avg * days
    abs_rate = lost / sched
    stemD = ("**Case — Sahyadri Co-operative Bank, Nashik region.** The regional manager suspects falling morale. Data for the half-year:\n\n"
             f"| Item | Figure |\n|---|---:|\n| Staff at start | {op} |\n| Staff at end | {cl} |\n| Separations (resignations + discharges) | {sep} |\n"
             f"| Accessions (all joinings) | {acc} |\n| of which replacements for separations | {repl} |\n"
             f"| Scheduled working days in a sample month | {days} |\n| Man-days lost to absence in that month (average staff) | {lost} |\n\n"
             "Exit interviews cite 'favouritism in postings', 'no one listens to suggestions' and 'good salary but no pride in the bank'.\n\n")
    g = "MGT-CASE-SAHYADRI"
    nq(B, "concept-of-morale", "L4", stemD + "The labour turnover rate by the separation method for the half-year is:",
       pct(sep_rate),
       [(pct(sep / op), "uses opening staff instead of average staff"),
        (pct(repl_rate), "replacement method, not separation method"),
        (pct(flux), "flux method (separations + replacements)")],
       [f"Average staff = ({op} + {cl})/2 = {avg:g}", f"Separation rate = {sep}/{avg:g} = {pct(sep_rate)}"],
       "Separation rate = Separations ÷ Average number of employees × 100",
       "Always use average staff as the base unless told otherwise.", group=g)
    nq(B, "factors-determining-morale", "L4", stemD + "The absenteeism rate for the sample month is:",
       pct(abs_rate),
       [(pct(lost / (avg * 30)), "uses 30 calendar days instead of scheduled working days"),
        (pct(lost / (sched - lost)), "divides by days actually worked instead of days scheduled"),
        (pct(lost / (op * days)), "uses opening staff instead of average staff")],
       [f"Scheduled man-days = {avg:g} × {days} = {sched:g}", f"Absenteeism = {lost}/{sched:g} = {pct(abs_rate)}"],
       "Absenteeism rate = Man-days lost ÷ Man-days scheduled × 100",
       "Base is scheduled working days, not calendar days or days worked.", group=g)
    cq(B, "factors-determining-morale", "L4", stemD + "The exit-interview comments point mainly to which determinants of morale?",
       "Fairness of policies and quality of supervision, not compensation",
       [("Compensation levels — salaries should be raised across the region", "employees say salary is good"),
        ("Physical working conditions and amenities at the bank's branches", "not mentioned"),
        ("Nature of work — routine banking tasks are inherently dull ones", "the complaints are about favouritism and not being heard")],
       ["Favouritism → policy fairness / equity; no listening → supervision and upward communication; 'no pride' → identification with the organisation."],
       "Eliminate what the stem says is fine (salary).", group=g)
    cq(B, "morale-vs-motivation", "L4", stemD + "One officer in the region continues to exceed targets because she is preparing for a promotion exam. This shows that:",
       "Individual motivation can stay high even when group morale is low",
       [("Group morale in the region must actually be high after all", "one person's motivation does not measure group morale"),
        ("Morale and motivation are really one and the same concept", "they are distinct — individual drive vs group attitude"),
        ("Low morale must always lower every employee's productivity", "morale–productivity link is not automatic")],
       ["Her drive comes from a personal goal (motivation); the group's attitude (morale) remains low."],
       "Do not infer group morale from one individual's performance.", group=g)
    stmt(B, "role-of-incentives-in-building-morale", "L4", stemD + "The regional manager proposes the following. Which would most directly address the causes identified?",
         [("A transparent, rule-based posting and transfer policy", True, "tackles favouritism (equity)"),
          ("A suggestion scheme with published responses and recognition for adopted ideas", True, "tackles 'no one listens' (participation, recognition)"),
          ("A uniform across-the-board salary increase", False, "salary is already described as good; a hygiene fix won't cure the stated causes"),],
         "Match the remedy to the diagnosed cause.", group=g,
         ask="Select the correct answer using the code given below.")
