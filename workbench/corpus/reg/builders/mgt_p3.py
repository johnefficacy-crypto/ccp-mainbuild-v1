"""MGT part 3 — leadership theories and group development."""
from mgt_common import cq, nq, stmt, ar, match


def add_all(B):
    # ================================================================ trait / qualities
    cq(B, "trait-approach", "L1",
       "Daniel Goleman's model of emotional intelligence, widely used in trait-based discussions of leadership, comprises self-awareness, self-regulation, motivation, empathy and:",
       "Social skill",
       [("Cognitive intelligence (IQ)", "Goleman's point is that EI is distinct from IQ"),
        ("Charisma", "charisma is a separate leadership concept, not an EI component"),
        ("Conscientiousness", "a Big Five personality trait, not one of Goleman's five EI components")],
       ["Goleman ('What Makes a Leader?', HBR 1998): self-awareness, self-regulation, motivation, empathy, social skill."],
       "Do not mix Big Five traits with EI components.")

    stmt(B, "trait-approach", "L3",
         "Consider the following statements on the trait approach to leadership:",
         [("Stogdill's 1948 review found that traits alone did not reliably predict leadership across situations", True,
           "his review pushed research towards situational factors"),
          ("Among the Big Five, extraversion has been found to be strongly related to leader emergence", True, "meta-analytic evidence (Judge et al., 2002)"),
          ("The 'great man' theory holds that leaders are made through training rather than born", False, "great man theory holds leaders are born with innate qualities"),
          ("A key limitation of the trait approach is that it ignores followers and the situation", True, "standard criticism")],
         "Great man = born leaders; trait approach later refined but still ignores situation.")

    cq(B, "qualities-and-traits", "L1",
       "Which of the following is generally NOT listed among the qualities of a good leader?",
       "Rigidity in the face of changing situations",
       [("Initiative in seizing opportunities", "a standard leadership quality"),
        ("Communication skills and persuasiveness", "a standard leadership quality"),
        ("Integrity and a high sense of ethics", "a standard leadership quality")],
       ["Qualities: physical & mental fitness, knowledge, integrity, initiative, communication skill, motivation skill, self-confidence, decisiveness, social skills.",
        "Flexibility — not rigidity — is valued."],
       "Firmness in decisions is a quality; rigidity towards change is not.")

    ar(B, "qualities-and-traits", "L2",
       "Possessing all the recognised leadership qualities does not guarantee that a person will be an effective leader.",
       "Leadership effectiveness also depends on followers' characteristics and the situation.",
       0,
       ["A true — trait lists are neither necessary nor sufficient for effectiveness.",
        "R true — situational and follower variables moderate effectiveness.",
        "R explains A."],
       "This is the bridge from trait theories to contingency theories.")

    # ================================================================ leader vs manager
    cq(B, "leader-vs-manager", "L1",
       "According to John Kotter, the essential difference between management and leadership is that:",
       "Management copes with complexity; leadership copes with change",
       [("Management copes with change; leadership copes with complexity", "reversed"),
        ("Management is about people; leadership is about systems", "Kotter's framing is the opposite in spirit"),
        ("Management is found only at top levels; leadership only at lower levels", "both are needed at all levels")],
       ["Kotter ('What Leaders Really Do', HBR 1990): management — planning & budgeting, organising & staffing, controlling;",
        "leadership — setting direction, aligning people, motivating & inspiring."],
       "Bennis: 'Managers do things right; leaders do the right thing.' Kotter: complexity vs change.")

    stmt(B, "leader-vs-manager", "L3",
         "In Kotter's framework, consider the following pairings of a management activity with its leadership counterpart:",
         [("Planning and budgeting — Setting a direction", True, "Kotter's first pair"),
          ("Organising and staffing — Aligning people", True, "Kotter's second pair"),
          ("Controlling and problem solving — Setting a direction", False, "its leadership counterpart is motivating and inspiring"),],
         "Kotter's three pairs: plan/budget ↔ direction; organise/staff ↔ align; control ↔ motivate/inspire.",
         ask="Which of the pairings given above is/are correct?")

    # ================================================================ successful vs effective
    cq(B, "successful-leader-vs-effective", "L2",
       "Fred Luthans' 'Real Managers' study compared successful managers (fastest promoted) with effective managers (high unit performance and satisfied, committed subordinates). Which finding is correct?",
       "Successful managers spent the most time on networking; effective managers spent the most on communication",
       [("Successful managers spent the most time on traditional management (planning, controlling)", "traditional management was not their dominant activity"),
        ("Effective managers spent the most time on networking, and successful managers on HR management", "networking dominated for successful, not effective, managers"),
        ("Both groups showed an essentially identical profile of time spent across all activities", "the study's point is that the profiles differed sharply")],
       ["Luthans (1988): successful ≈ networking dominant; effective ≈ communication and HRM dominant; networking least."],
       "Getting promoted and running an effective unit are different — the core insight.")

    stmt(B, "successful-leader-vs-effective", "L3",
         "Consider the distinction between a successful and an effective leader (as drawn by Hersey and Blanchard):",
         [("A leader is 'successful' when the group behaves as the leader intends, even if followers comply only because of position power", True, "success = intended behaviour achieved"),
          ("A leader is 'effective' when followers do what is intended because they find it personally rewarding", True, "effectiveness rests on personal power/internalisation"),
          ("A successful leader is always effective, since the task gets done", False, "compliance under threat can be successful but ineffective in the long run"),],
         "Success can be short-term compliance; effectiveness is willing commitment.")

    # ================================================================ Lewin
    cq(B, "kurt-lewin", "L1",
       "In the leadership experiments by Lewin, Lippitt and White (1939), which style was associated with the lowest productivity and a disorganised group?",
       "Laissez-faire",
       [("Autocratic", "autocratic groups were productive while the leader was present, but hostile/dependent"),
        ("Democratic", "democratic groups showed good quality work and highest satisfaction"),
        ("Paternalistic", "not one of the three styles studied")],
       ["Lewin et al.: autocratic, democratic, laissez-faire leaders in boys' hobby clubs.",
        "Laissez-faire: least work, poorest quality, confusion."],
       "Paternalistic is a common extra label but not part of Lewin's trio.")

    cq(B, "kurt-lewin", "L2",
       "The head of a quantitative research desk gives her team of seasoned PhD analysts full freedom to choose projects and methods, providing resources and advice only when asked. Her style, in Lewin's terms, is:",
       "Laissez-faire (free-rein)",
       [("Democratic (participative)", "a democratic leader involves the group in decisions but still guides and decides with them"),
        ("Autocratic (authoritarian)", "no centralised decision-making"),
        ("Transactional (exchange-based)", "not a Lewin category; transactional is Burns/Bass")],
       ["Full freedom, leader as resource provider → laissez-faire.", "Works when subordinates are highly competent and self-motivated."],
       "Laissez-faire is not always bad — it suits experts; democratic still has the leader actively involved.")

    stmt(B, "kurt-lewin", "L3",
         "With reference to Lewin's leadership styles, consider:",
         [("Autocratic leadership may be appropriate in emergencies requiring quick decisions", True, "speed and clarity"),
          ("Democratic leadership generally produced higher member satisfaction in the original studies", True, "finding of Lewin et al."),
          ("Laissez-faire leadership involves the leader taking decisions after consulting the group", False, "that is democratic/consultative; laissez-faire leaves decisions to the group"),
          ("In the original studies, autocratic groups tended to slack off when the leader left the room", True, "dependence on leader presence")],
         "Consultation = democratic; abdication = laissez-faire.")

    # ================================================================ Goleman
    cq(B, "goleman-s-leadership", "L1",
       "In Goleman's research ('Leadership That Gets Results', 2000), which leadership style had the most strongly positive effect on organisational climate?",
       "Authoritative (visionary)",
       [("Coercive (commanding)", "coercive had the most negative effect on climate"),
        ("Pacesetting (lead by example)", "pacesetting also had a negative effect on climate"),
        ("Democratic (participative)", "positive, but less strongly than authoritative")],
       ["Six styles: coercive, authoritative, affiliative, democratic, pacesetting, coaching.",
        "Authoritative had the strongest positive climate correlation; coercive and pacesetting were negative."],
       "'Authoritative' in Goleman means visionary ('Come with me'), not authoritarian.")

    cq(B, "goleman-s-leadership", "L2",
       "A newly appointed CEO of a distressed NBFC facing a liquidity crisis issues firm instructions, halts all non-essential spending immediately and demands strict compliance. In Goleman's framework, this style is:",
       "Coercive — suited to crises and turnarounds, harmful as a regular style",
       [("Pacesetting — sets high standards by personal example for a competent team", "pacesetting sets high standards by example; not crisis command"),
        ("Authoritative — mobilises people towards a shared long-term vision", "no vision is being articulated; this is command-and-control"),
        ("Democratic — builds consensus and commitment through participation", "no participation")],
       ["'Do what I tell you' → coercive; works in a crisis or to kick-start a turnaround."],
       "Coercive = command; pacesetting = 'do as I do, now'.")

    match(B, "goleman-s-leadership", "L3",
          "Match Goleman's style with its characteristic phrase:",
          ["Coercive", "Authoritative", "Democratic", "Pacesetting"],
          ["\"Do what I tell you.\"", "\"Come with me.\"", "\"What do you think?\"", "\"Do as I do, now.\""],
          [1, 2, 3, 4],
          [((0, 1), "confuses coercive (command) with authoritative (vision)"),
           ((0, 3), "confuses coercive with pacesetting — both negative for climate but different mechanisms"),
           ((1, 2), "confuses vision-led mobilisation with consensus-seeking")],
          ["Coercive — demands immediate compliance.", "Authoritative — mobilises towards a vision.",
           "Democratic — forges consensus.", "Pacesetting — sets high standards by example."],
          "Remaining styles: affiliative ('People come first') and coaching ('Try this').")

    # ================================================================ affiliative & coaching
    cq(B, "affiliative-and-coaching", "L2",
       "After a bitter merger of two brokerages, teams from both sides distrust each other. The new head focuses on praise, harmony and emotional bonds to heal the rift. Goleman would call this the:",
       "Affiliative style",
       [("Coaching style", "coaching develops individuals for the future; the need here is healing relationships"),
        ("Democratic style", "democratic seeks input for decisions, not primarily emotional repair"),
        ("Authoritative style", "no vision-setting described")],
       ["Affiliative ('People come first'): creates harmony, heals rifts, motivates in stressful times."],
       "Affiliative is weak on performance feedback — best combined with authoritative.")

    stmt(B, "affiliative-and-coaching", "L3",
         "With reference to Goleman's affiliative and coaching styles, consider:",
         [("The coaching style works best with employees who want to improve and who recognise their own weaknesses", True, "coaching needs receptive employees"),
          ("The coaching style is the one most frequently used by leaders in Goleman's study because it yields immediate results", False,
           "coaching was the least used style; its payoff is long-term development"),
          ("An exclusive focus on praise in the affiliative style can allow poor performance to go uncorrected", True, "Goleman's caution"),
          ("Coaching is associated with the EI competencies of developing others, empathy and self-awareness", True, "Goleman's mapping")],
         "Coaching = long-term development ('Try this'), least used, positive climate.")

    # ================================================================ Fiedler
    cq(B, "fiedler", "L2",
       "In Fiedler's contingency model, a leader who describes his Least Preferred Co-worker in very harsh, negative terms (low LPC score) is considered to be:",
       "Task-motivated",
       [("Relationship-motivated", "high LPC — describing even the least preferred co-worker favourably — indicates relationship motivation"),
        ("Laissez-faire", "not a Fiedler category"),
        ("Achievement-oriented", "a path-goal (House) leader behaviour, not an LPC type")],
       ["Low LPC → task-motivated; high LPC → relationship-motivated.", "Fiedler treats style as fixed; change the situation, not the leader."],
       "Fiedler's style is fixed — unlike Hersey-Blanchard or path-goal, where the leader adapts.")

    stmt(B, "fiedler", "L3",
         "In Fiedler's contingency model, consider:",
         [("Situational favourableness is determined by leader–member relations, task structure and position power", True, "three situational variables"),
          ("Task-motivated (low LPC) leaders perform best in both highly favourable and highly unfavourable situations", True, "octants I–III and VIII"),
          ("Relationship-motivated leaders perform best in highly favourable situations", False, "they do best in moderately favourable situations"),
          ("Fiedler recommends changing the leader's style to fit the situation through training", False,
           "Fiedler treats style as fixed; he recommends matching leaders to situations or engineering the situation")],
         "Style is fixed in Fiedler — the classic contrast with situational leadership.")

    # ================================================================ Hersey–Blanchard
    cq(B, "hersey-blanchard", "L2",
       "A team of experienced relationship managers is fully able to handle HNI clients but has become reluctant and insecure after a restructuring. Under the Hersey–Blanchard model, the appropriate leadership style is:",
       "Participating (S3) — high relationship, low task behaviour",
       [("Telling (S1) — high task, low relationship behaviour", "for followers unable and unwilling (R1)"),
        ("Selling (S2) — high task, high relationship behaviour", "for followers unable but willing (R2)"),
        ("Delegating (S4) — low task, low relationship behaviour", "for followers able and willing/confident (R4)")],
       ["Readiness R3: able but unwilling/insecure → S3 participating (share ideas, facilitate decisions)."],
       "Able-but-unwilling needs support, not direction.")

    match(B, "hersey-blanchard", "L3",
          "Match follower readiness with the Hersey–Blanchard style:",
          ["R1 — unable and unwilling/insecure", "R2 — unable but willing/confident", "R3 — able but unwilling/insecure", "R4 — able and willing/confident"],
          ["Telling", "Selling", "Participating", "Delegating"],
          [1, 2, 3, 4],
          [((1, 2), "swaps selling and participating — mixing up which readiness needs task direction"),
           ((2, 3), "delegates to followers who are able but insecure"),
           ((0, 1), "tells followers who are already willing")],
          ["R1 → S1 telling.", "R2 → S2 selling.", "R3 → S3 participating.", "R4 → S4 delegating."],
          "As readiness rises, task behaviour falls first; relationship behaviour rises then falls.")

    # ================================================================ path–goal
    cq(B, "path-goal", "L2",
       "Under House's path–goal theory, which leader behaviour is most appropriate for inexperienced subordinates working on an ambiguous, unstructured task?",
       "Directive leadership",
       [("Supportive leadership", "suits structured, routine or stressful tasks"),
        ("Participative leadership", "suits subordinates with an internal locus of control and ability"),
        ("Achievement-oriented leadership", "suits capable subordinates on challenging tasks")],
       ["Directive behaviour clarifies the path where task and role are ambiguous and experience is low."],
       "Directive behaviour is redundant (and resented) for experienced staff on structured tasks.")

    stmt(B, "path-goal", "L3",
         "With reference to path–goal theory, consider:",
         [("Subordinates with an internal locus of control are more satisfied with participative leadership", True, "House's proposition"),
          ("Supportive leadership results in high satisfaction when subordinates perform structured, routine tasks", True, "compensates for tedium"),
          ("Path–goal theory rests on Vroom's expectancy theory", True, "leader clarifies paths and increases payoffs"),
          ("Path–goal theory, like Fiedler's model, treats the leader's style as fixed", False, "House assumes leaders can use all four behaviours")],
         "Path–goal = flexible leader; Fiedler = fixed leader.")

    # ================================================================ transactional vs transformational
    cq(B, "transactional-vs-transformational", "L2",
       "A leader spends time understanding each officer's career aspirations, mentors them individually, and assigns projects that stretch their particular strengths. In Bass's model, this is:",
       "Individualised consideration — a component of transformational leadership",
       [("Contingent reward — a component of transactional leadership", "no exchange of reward for performance described"),
        ("Intellectual stimulation — a component of transformational leadership", "intellectual stimulation challenges assumptions and encourages creativity"),
        ("Active management by exception — a component of transactional leadership", "that is monitoring for deviations")],
       ["Bass's four I's: idealised influence, inspirational motivation, intellectual stimulation, individualised consideration."],
       "Mentoring each person individually = individualised consideration.")

    stmt(B, "transactional-vs-transformational", "L3",
         "Consider the following statements:",
         [("James MacGregor Burns introduced the transactional–transformational distinction in his 1978 book *Leadership*, based on studies of political leaders", True, "Burns (1978)"),
          ("Management by exception, active or passive, is a component of transformational leadership", False, "it is a transactional component"),
          ("Bass viewed transformational leadership as building on transactional leadership rather than replacing it", True, "augmentation effect"),],
         "Burns saw the two as opposite ends; Bass saw them as complementary.")

    # ================================================================ charismatic
    cq(B, "charismatic", "L2",
       "Which of the following is NOT one of the behavioural dimensions of charismatic leadership identified by Conger and Kanungo?",
       "Strict adherence to established procedures",
       [("Articulating an appealing vision", "a core dimension"),
        ("Willingness to take personal risk", "a core dimension"),
        ("Unconventional, counter-normative behaviour", "a core dimension")],
       ["Conger & Kanungo: vision and articulation, personal risk, sensitivity to environment, sensitivity to followers' needs, unconventional behaviour."],
       "Charisma involves breaking with convention, not adhering to it.")

    ar(B, "charismatic", "L3",
       "Charismatic leadership can be dangerous for an organisation in some circumstances.",
       "Charismatic leaders always derive their influence from formal position power, which they tend to misuse.",
       2,
       ["A true — dark side: follower dependence, suppression of dissent, succession vacuum, personal agendas.",
        "R false — charisma rests on personal (referent) power, not position power (Weber contrasted charismatic with legal-rational authority)."],
       "Charismatic influence is personal; that is why succession after a charismatic leader is hard.")

    # ================================================================ Tuckman
    cq(B, "tuckman", "L1",
       "The correct sequence of Tuckman's stages of group development (including the stage added with Jensen in 1977) is:",
       "Forming → storming → norming → performing → adjourning",
       [("Forming → norming → storming → performing → adjourning", "storming precedes norming"),
        ("Storming → forming → norming → performing → adjourning", "a group must form before conflict emerges"),
        ("Forming → storming → performing → norming → adjourning", "norms are established before high performance")],
       ["Tuckman (1965): forming, storming, norming, performing; adjourning added (Tuckman & Jensen, 1977)."],
       "Norming before performing; storming before norming.")

    cq(B, "tuckman", "L2",
       "Three weeks into a new cross-functional task force, members openly challenge the leader's plan, argue over who owns which deliverable and form sub-cliques. The group is in the:",
       "Storming stage",
       [("Forming stage", "forming is marked by politeness, uncertainty and dependence on the leader"),
        ("Norming stage", "norming is when cohesion and shared rules emerge"),
        ("Adjourning stage", "adjourning is disbanding after task completion")],
       ["Intragroup conflict over roles, leadership and approach = storming."],
       "Conflict is a normal stage; it precedes norming.")

    # ================================================================ CASE E — leadership at a branch office
    stemE = ("**Case — Deepa at Northstar Securities' GIFT City office.** Deepa takes charge of three teams:\n\n"
             "- **Team 1:** fresh graduates, eager and confident but with little knowledge of IFSC products.\n"
             "- **Team 2:** veteran dealers, highly skilled, but demotivated and insecure after being passed over in a reorganisation.\n"
             "- **Team 3:** back-office staff doing highly structured, repetitive trade reconciliations under tight daily deadlines.\n\n"
             "Deepa's own LPC score is low. She enjoys good relations with Team 3, their work is highly structured, but she has little formal authority over their pay or postings (these are decided at head office). "
             "Her predecessor ran the office purely through targets, bonuses and intervening only when numbers slipped; Deepa instead talks of making the office 'the IFSC hub of choice', encourages staff to question old routines and mentors individuals.\n\n")
    g = "MGT-CASE-DEEPA"
    cq(B, "hersey-blanchard", "L4", stemE + "Under the Hersey–Blanchard model, the appropriate styles for Team 1 and Team 2 respectively are:",
       "Selling (S2) for Team 1; participating (S3) for Team 2",
       [("Telling (S1) for Team 1; delegating (S4) for Team 2", "Team 1 is willing (R2, not R1); Team 2 is insecure (R3, not R4)"),
        ("Participating (S3) for Team 1; selling (S2) for Team 2", "reverses the two teams' readiness levels"),
        ("Delegating (S4) for Team 1; telling (S1) for Team 2", "Team 1 lacks ability; Team 2 has ability")],
       ["Team 1: unable but willing → R2 → S2 selling.", "Team 2: able but unwilling/insecure → R3 → S3 participating."],
       "Ability and willingness must both be read for each team.", group=g)
    cq(B, "fiedler", "L4", stemE + "Using Fiedler's model, Deepa's situation with Team 3 and the predicted fit of her style are:",
       "Octant II (good relations, structured task, weak power) — favourable; a low-LPC leader fits",
       [("Octant III (good relations, unstructured task, strong power) — favourable; low-LPC fits", "misreads task as unstructured and power as strong"),
        ("Octant V (poor relations, structured task, strong power) — moderate; high-LPC fits", "relations are good, not poor"),
        ("Octant II (good relations, structured task, weak power) — favourable; a high-LPC leader fits", "high-LPC leaders fit moderate, not favourable, situations")],
       ["LMR good, task structured, position power weak → octant II.", "Octants I–III favourable → task-motivated (low LPC) leader fits."],
       "Position power is weak here because pay/postings are decided elsewhere.", group=g)
    cq(B, "path-goal", "L4", stemE + "Under path–goal theory, which leader behaviour is most likely to raise Team 3's satisfaction?",
       "Supportive leadership",
       [("Directive leadership", "the task is already highly structured — more direction is redundant"),
        ("Achievement-oriented leadership", "suits challenging, non-routine tasks"),
        ("Participative leadership", "not the primary prescription for routine, stressful work")],
       ["Structured, repetitive, deadline-pressured task → supportive behaviour compensates for tedium and stress."],
       "Directive behaviour on structured tasks lowers satisfaction.", group=g)
    cq(B, "transactional-vs-transformational", "L4", stemE + "The contrast between Deepa and her predecessor is best described as:",
       "Predecessor transactional; Deepa transformational",
       [("Predecessor laissez-faire; Deepa autocratic", "the predecessor actively used targets and intervention"),
        ("Predecessor transformational; Deepa transactional", "reversed"),
        ("Both transactional, as both pursue performance", "vision, questioning routines and mentoring are transformational")],
       ["Targets + bonuses + intervening when numbers slip = contingent reward + MBE → transactional.",
        "Vision + challenging routines + mentoring = three of Bass's four I's → transformational."],
       "Pursuing performance is common to both; the mechanism differs.", group=g)
    cq(B, "goleman-s-leadership", "L4", stemE + "Deepa's talk of making the office 'the IFSC hub of choice', while leaving teams free to choose how to get there, corresponds most closely to which Goleman style?",
       "Authoritative (visionary)",
       [("Pacesetting (lead by example)", "pacesetting leads by personal example and high standards, not vision"),
        ("Coercive (commanding)", "no demands for immediate compliance"),
        ("Affiliative (people-first)", "focus is vision, not harmony")],
       ["Authoritative: 'Come with me' — sets the destination, leaves the means to people."],
       "Goleman's 'authoritative' is visionary, not authoritarian.", group=g)

    # ================================================================ CASE F — team development
    stemF = ("**Case — Project Setu at Meridian Broking.** A 9-member team from IT, operations, risk and compliance is formed to implement same-day settlement within six months.\n\n"
             "- **Weeks 1–2:** members are polite and cautious, keep asking the project lead what exactly is expected, and avoid disagreeing.\n"
             "- **Weeks 4–6:** IT and compliance clash over testing standards; two members question the lead's authority.\n"
             "- **Weeks 8–10:** the team agrees on working rules, a shared test protocol and a common vocabulary; cohesion rises.\n"
             "- **Month 7:** after go-live, the team is disbanded and members return to their departments.\n\n")
    g = "MGT-CASE-SETU"
    cq(B, "tuckman", "L4", stemF + "The team's behaviour in weeks 1–2 indicates which Tuckman stage?",
       "Forming",
       [("Norming", "no norms or cohesion yet"),
        ("Storming", "no open conflict yet"),
        ("Performing", "the team is not yet functioning autonomously")],
       ["Uncertainty, politeness, dependence on the leader → forming."],
       "Politeness is not cohesion — cohesion comes in norming.", group=g)
    cq(B, "tuckman", "L4", stemF + "Weeks 8–10 and month 7 correspond respectively to:",
       "Norming; adjourning",
       [("Performing; adjourning", "weeks 8–10 describe the setting of norms and rising cohesion, not yet full performance"),
        ("Norming; mourning as a separate sixth stage", "mourning is an informal label for adjourning, not a separate stage"),
        ("Storming; performing", "conflict has already been resolved by weeks 8–10")],
       ["Agreed rules and cohesion → norming.", "Disbanding after task completion → adjourning (Tuckman & Jensen 1977)."],
       "Establishing rules precedes performing.", group=g)
    cq(B, "tuckman", "L4", stemF + "During weeks 4–6, which action by the project lead is most appropriate?",
       "Surface the disagreement, clarify roles and decision rights, and facilitate agreed standards",
       [("Suppress the disagreement and insist on the original plan to avoid any delay to go-live", "suppressing conflict prevents progress to norming"),
        ("Step back and delegate all decisions to the members, since the team is now self-managing", "delegation suits performing, not storming"),
        ("Disband the team and reconstitute it with members who get along better", "storming is a normal stage, not a failure")],
       ["Storming needs conflict management and role clarity to move to norming."],
       "Conflict in storming is healthy if managed, harmful if suppressed.", group=g)
    stmt(B, "hersey-blanchard", "L4", stemF + "Linking group stages to leadership, consider:",
         [("In weeks 1–2, a high-task, directive approach (telling/selling) is appropriate because members lack clarity", True, "low readiness in forming"),
          ("By the performing stage, a delegating style becomes appropriate", True, "high readiness"),
          ("Hersey–Blanchard prescribe the same style throughout a project's life for consistency", False, "the model is explicitly adaptive to follower readiness")],
         "Situational leadership tracks readiness, which rises as the group develops.", group=g)
