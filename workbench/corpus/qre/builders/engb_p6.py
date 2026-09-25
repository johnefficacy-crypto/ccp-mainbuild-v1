"""ENG-B part 6: idioms in context (incl. passage set), phrasal verbs, workplace communication (barriers, registers, tools; each with a case set)."""

ID = "eng-meaning-of-an-idiom-in-context-afcdf0c3"
PV = "eng-phrasal-verbs-00cf2c93"
CB = "communication-barriers"
CR = "communication-registers"
CT = "communication-tools"

AR = ["Both A and R are true, and R is the correct explanation of A",
      "Both A and R are true, but R is not the correct explanation of A",
      "A is true, but R is false", "A is false, but R is true"]


def add_all(B, H):
    mc = H["mc"]
    F, O = "foundation", "officer"
    IREF = "Standard idiomatic sense (Oxford Dictionary of Idioms / learner's dictionaries)."

    def idm(tier, level, sentence, key, wrongs, note, group=None, stim=None, stem=None):
        mc(ID, tier, level, stem or ("Choose the meaning of the idiom in bold as used in the sentence:\n\n" + sentence), key, wrongs,
           [note], IREF, "Literal readings of the idiom are the main trap.", group=group, stim=stim)

    def pv(tier, level, stem, key, wrongs, note):
        mc(PV, tier, level, stem, key, wrongs, [note], "Phrasal verb meaning depends on the particle and context.",
           "Same verb with a different particle gives a different meaning.")

    PVM = "Choose the meaning of the phrasal verb in bold:\n\n"
    PVF = "Choose the phrasal verb that correctly fills the blank:\n\n"

    # ---------------- Idioms ----------------
    idm(F, "L1", "He told a joke to **break the ice** at the start of the meeting.", "to ease the initial tension",
        [("to start a quarrel", "opposite effect"), ("to end the meeting early", "unrelated"), ("to cool down the room", "literal reading")],
        "'Break the ice' = make people feel relaxed at the start.")
    idm(F, "L1", "For an experienced accountant, preparing this statement is **a piece of cake**.", "a very easy task",
        [("a tasty snack", "literal reading"), ("a small reward", "unrelated"), ("a matter of luck", "unrelated")],
        "'A piece of cake' = something very easy.")
    idm(F, "L1", "My cousin visits us only **once in a blue moon**.", "very rarely",
        [("every month", "regular, not rare"), ("only at night", "literal reading of 'moon'"), ("never at all", "too absolute")],
        "'Once in a blue moon' = very rarely.")
    idm(F, "L2", "Stop **beating about the bush** and tell us what happened.", "avoiding the main point",
        [("searching the area thoroughly", "literal reading"), ("working very hard", "unrelated"), ("wasting money", "unrelated")],
        "'Beat about the bush' = avoid coming to the point.")
    idm(F, "L2", "You **hit the nail on the head** when you blamed the delay on poor planning.", "described the cause exactly",
        [("made a serious mistake", "opposite"), ("lost your temper", "unrelated"), ("used force unnecessarily", "literal reading")],
        "'Hit the nail on the head' = say exactly the right thing.")

    idm(O, "L3", "After the fraud came to light, the bank went back to **square one** on its lending policy.", "starting again from the beginning",
        [("adopting a rigid final stance", "unrelated"), ("moving to a new head office", "literal reading"), ("closing the matter for good", "opposite")],
        "'Back to square one' = back to the starting point after a failure.")
    idm(O, "L3", "The new manager's promises of quick promotions turned out to be **pie in the sky**.", "an unrealistic hope",
        [("a generous reward", "unrelated"), ("a well-kept secret", "unrelated"), ("an immediate success", "opposite")],
        "'Pie in the sky' = something pleasant that is unlikely to happen.")
    idm(O, "L3", "The proposal to close rural branches was **nipped in the bud** by the finance ministry.", "stopped at an early stage",
        [("delayed for some years", "delay, not stopping"), ("approved after changes", "opposite"), ("sent back for comments", "partial action only")],
        "'Nip in the bud' = stop something before it develops.")
    idm(O, "L3", "He has **burnt his boats** by resigning before securing the new job.", "left himself no way back",
        [("wasted all his savings", "unrelated"), ("lost his temper", "unrelated"), ("destroyed the evidence", "literal-ish misreading")],
        "'Burn one's boats' = commit to a course with no way back.")
    idm(O, "L3", "The auditor's first query **opened a can of worms** in the branch.", "exposed many tangled problems",
        [("solved a long-standing mystery", "opposite effect"), ("started a formal celebration", "unrelated"),
         ("caused a minor, harmless delay", "understates the idiom")],
        "'Open a can of worms' = start something that leads to many complicated problems.")
    idm(O, "L3", "Car sales have been **in the doldrums** since the monsoon failed.", "stagnant and inactive",
        [("rising steadily", "opposite"), ("under investigation", "unrelated"), ("fluctuating wildly", "movement, not stagnation")],
        "'In the doldrums' = in a state of stagnation or low spirits.")
    idm(O, "L3", "After months of litigation, the two partners agreed to **bury the hatchet**.", "end their quarrel",
        [("hide the evidence", "literal reading of 'bury'"), ("suspend the talks", "opposite"), ("stake a claim", "unrelated")],
        "'Bury the hatchet' = make peace.")
    stim = ("Read the passage and answer the question.\n\n"
            "When the merger talks began, both sides **played their cards close to their chest**. The smaller firm's founder, "
            "who had built the company from nothing, was not willing to **sell himself short**. After weeks of haggling, the "
            "bankers found a formula that **cut the Gordian knot**, and the deal was signed within days.")
    G = "ENB-G05"
    idm(O, "L4", None, "kept their plans and intentions secret",
        [("took reckless risks with their offers", "gambling sense misread"), ("tried to cheat each other at every turn", "unrelated"), ("made hasty offers", "opposite of caution")],
        "'Play one's cards close to one's chest' = keep one's intentions secret.", group=G, stim=stim,
        stem="What does 'played their cards close to their chest' mean in the passage?")
    idm(O, "L4", None, "undervalue his own worth",
        [("cheat the buyers", "unrelated"), ("retire early", "unrelated"), ("raise the price unfairly", "opposite")],
        "'Sell oneself short' = fail to recognise or claim one's true worth.", group=G, stim=stim,
        stem="What does 'sell himself short' mean in the passage?")
    idm(O, "L4", None, "resolved the deadlock boldly",
        [("broke off the talks", "opposite outcome"), ("delayed the deal further", "contradicted by 'signed within days'"),
         ("created new legal hurdles", "opposite")],
        "'Cut the Gordian knot' = solve a complex problem by bold, direct action.", group=G, stim=stim,
        stem="What does 'cut the Gordian knot' mean in the passage?")

    # ---------------- Phrasal verbs ----------------
    pv(F, "L1", PVM + "'Please **look after** my bag while I buy the tickets.'", "take care of",
       [("search for", "= look for"), ("examine", "= look over"), ("follow", "unrelated")], "'Look after' = take care of.")
    pv(F, "L1", PVM + "'The meeting was **called off** because of the strike.'", "cancelled",
       [("announced", "unrelated"), ("postponed", "= put off; the meeting is not rescheduled here"), ("shortened", "unrelated")],
       "'Call off' = cancel.")
    pv(F, "L1", PVM + "'He **gave up** smoking last year.'", "stopped",
       [("started", "= took up"), ("reduced", "partial, not complete"), ("hid", "unrelated")], "'Give up' = stop doing something.")
    pv(F, "L2", PVF + "'The fire brigade managed to ___ the fire within an hour.'", "put out",
       [("put off", "= postpone"), ("put up", "= accommodate/erect"), ("put on", "= wear/switch on")], "'Put out' = extinguish.")
    pv(F, "L2", PVM + "'I **ran into** an old friend at the station.'", "met by chance",
       [("collided with", "literal reading"), ("chased", "= ran after"), ("avoided", "opposite")], "'Run into' = meet unexpectedly.")

    pv(O, "L3", PVM + "'The committee will **look into** the complaints of the depositors.'", "investigate",
       [("disregard", "= overlook"), ("respect", "= look up to"), ("anticipate", "= look forward to")], "'Look into' = investigate.")
    pv(O, "L3", PVF + "'The company had to ___ two hundred workers during the slowdown.'", "lay off",
       [("lay out", "= arrange/spend"), ("lay by", "= save"), ("lay down", "= establish (rules)")],
       "'Lay off' = dismiss workers because there is no work.")
    pv(O, "L3", PVM + "'Don't let his rudeness **put you off** applying for the post.'", "discourage",
       [("postpone", "'put off' = postpone takes a thing, not a person + gerund"), ("persuade", "opposite"), ("remind", "unrelated")],
       "'Put somebody off (doing)' = discourage.")
    pv(O, "L3", PVM + "'The minister **brushed aside** the criticism of the scheme.'", "dismissed",
       [("accepted", "opposite"), ("answered in detail", "opposite"), ("cleaned up", "literal reading")], "'Brush aside' = dismiss as unimportant.")
    pv(O, "L3", PVF + "'Negotiations ___ when neither side would compromise.'", "broke down",
       [("broke out", "= began suddenly (war, fire)"), ("broke in", "= entered by force"), ("broke into", "= entered by force / began suddenly")],
       "'Break down' (talks) = fail.")
    pv(O, "L3", PVM + "'The city plans to **phase out** diesel buses over the next five years.'", "withdraw gradually",
       [("introduce gradually", "= phase in"), ("repair periodically", "unrelated"), ("register afresh", "unrelated")],
       "'Phase out' = withdraw in stages.")
    pv(O, "L3", PVM + "'The auditor **came across** a suspicious entry in the ledger.'", "found by chance",
       [("deliberately created", "unrelated"), ("explained", "unrelated"), ("ignored", "opposite")], "'Come across' = find by chance.")
    pv(O, "L3", PVF + "'We cannot ___ such indiscipline any longer.'", "put up with",
       [("put up to", "= incite"), ("put in with", "not a phrasal verb"), ("put across", "= communicate")], "'Put up with' = tolerate.")
    pv(O, "L3", PVM + "'The unpaid loan has to be **written off**.'", "removed from the accounts as unrecoverable",
       [("recorded in writing for future reference", "literal reading"), ("recovered in full from the defaulter", "opposite"),
        ("carried forward to the next year", "unrelated accounting treatment")],
       "'Write off' (a debt) = cancel it as a loss.")
    pv(O, "L3", PVM + "'She **stood in for** the manager during his leave.'", "substituted for",
       [("opposed", "= stood against"), ("supported", "= stood by"), ("waited for", "unrelated")], "'Stand in for' = take someone's place temporarily.")

    # ---------------- Communication barriers ----------------
    CREF = "Standard business-communication concepts (barriers, registers, channels)."

    def cm(micro, tier, level, stem, key, wrongs, steps, trap, kind="conceptual", group=None, stim=None):
        mc(micro, tier, level, stem, key, wrongs, steps, CREF, trap, kind=kind, group=group, stim=stim)

    cm(CB, F, "L1", "A new employee cannot follow a meeting because colleagues keep using unexplained acronyms. This is an example of a:",
       "Semantic barrier", [("Physical barrier", "concerns environment/distance"), ("Emotional barrier", "concerns feelings"),
                            ("Organisational barrier", "concerns structure/hierarchy")],
       ["Barriers arising from words, jargon and meaning are semantic (language) barriers."], "Jargon = semantic.")
    cm(CB, F, "L1", "Noise from construction work next to a meeting room creates a:",
       "Physical barrier", [("Semantic barrier", "not about meaning of words"), ("Psychological barrier", "not about attitudes"),
                            ("Cultural barrier", "not about cultural norms")],
       ["Noise, distance and poor equipment are physical/environmental barriers."], "Environmental interference = physical.")
    cm(CB, F, "L1", "Which practice best helps a manager check that instructions have been understood?",
       "Seeking feedback", [("Speaking faster", "increases misunderstanding"), ("Using more jargon", "adds semantic noise"),
                            ("Avoiding questions", "blocks feedback")],
       ["Feedback lets the sender verify that the message was received as intended."], "Feedback closes the loop.")
    cm(CB, F, "L2", "An angry customer ignores the clerk's explanation of a bank charge. The main barrier is:",
       "Emotional", [("Semantic", "the words are understood"), ("Physical", "no environmental obstacle"), ("Technological", "no channel failure")],
       ["Strong emotions such as anger block reception of the message."], "State of mind = emotional barrier.")
    cm(CB, F, "L2", "Information that gets distorted as it passes through many levels of hierarchy is an example of:",
       "Organisational", [("Semantic", "not about word meaning"), ("Physical", "not environmental"),
                                     ("Personal", "not about one individual's attitude")],
       ["Long chains of command and rigid structures create organisational barriers."], "Structure-related distortion.")

    cm(CB, O, "L3", "A manager reports only the good news about quarterly results to his superiors so that he looks competent. This is best described as:",
       "Filtering", [("Selective perception", "receiver-side bias, not sender manipulation"), ("Information overload", "volume, not manipulation"),
                     ("Semantic noise", "word meaning, not manipulation")],
       ["Filtering = the sender manipulating information so that it is seen more favourably."], "Sender-side vs receiver-side distortion.")
    cm(CB, O, "L3", "An employee who receives about two hundred emails a day misses a key instruction. The barrier is:",
       "Information overload", [("Filtering", "no deliberate manipulation"), ("Status difference", "hierarchy not involved"),
                                ("Selective perception", "no bias involved")],
       ["Volume beyond processing capacity = information overload."], "Too much, not wrong, information.")
    cm(CB, O, "L3", "A reviewer who dislikes a colleague reads her proposal looking only for faults. This reflects:",
       "Selective perception", [("Information overload", "volume is not the issue"), ("Physical noise", "no environmental problem"),
                                ("Channel failure", "the document reached the reviewer")],
       ["Receivers interpreting messages through their own biases = selective perception."], "Receiver-side bias.")
    cm(CB, O, "L3", "Consider the statements:\n1. Jargon can be a barrier even among colleagues of the same organisation.\n"
       "2. Physical barriers cannot arise in virtual meetings.\n3. Premature evaluation by a listener is a psychological barrier.\n\nWhich are correct?",
       "1 and 3 only", [("1 and 2 only", "statement 2 is false"), ("2 and 3 only", "statement 2 is false"), ("1, 2 and 3", "statement 2 is false")],
       ["1: true (different departments use different jargon).", "2: false (poor connectivity and background noise are physical barriers).",
        "3: true (judging before hearing fully is psychological)."], "Virtual channels still have physical barriers.", kind="statement")
    cm(CB, O, "L3", "A junior officer hesitates to point out an error in the director's note. The barrier is:",
       "Status difference", [("Semantic barrier", "language is understood"), ("Information overload", "volume is not the issue"),
                             ("Cultural difference", "not a cross-cultural issue")],
       ["Hierarchy/status gaps discourage upward communication."], "Hierarchy barrier.")
    cm(CB, O, "L3", "Which measure best removes a semantic barrier in a circular sent to rural branch staff?",
       "Use plain, local-language text", [("Dispatch it through registered post", "addresses delivery, not meaning"),
                                          ("Print it in a larger font size", "addresses legibility, not meaning"),
                                          ("Stamp it 'Urgent' in red ink", "addresses priority, not meaning")],
       ["Semantic barriers are removed by simpler words and a language the receiver understands."], "Match the remedy to the barrier type.")
    cm(CB, O, "L3", "Assertion (A): Feedback is essential for overcoming communication barriers.\n"
       "Reason (R): Feedback lets the sender check whether the message was understood as intended.",
       AR[0], [(AR[1], "R directly explains why feedback matters"), (AR[2], "R is true"), (AR[3], "A is true")],
       ["Both statements are true, and R gives the reason for A."], "Check the explanatory link, not just truth.", kind="assertion-reason")
    stim = ("At a regional office, the new head issues all instructions through long emails full of technical terms. Field staff, many of "
            "whom check email once a day on a shared computer, often miss deadlines. When a field supervisor raised the issue in a meeting, "
            "the head replied, 'I have been doing this for twenty years; the system is fine,' and moved to the next item. Since then, few "
            "staff speak up in meetings.")
    G = "ENB-G06"
    cm(CB, O, "L4", "The head's use of technical terms primarily creates which barrier?", "Semantic",
       [("Physical", "not about access or noise"), ("Emotional", "not about feelings"), ("Cultural", "not about cultural norms")],
       ["Unfamiliar technical vocabulary is a semantic barrier."], "Separate the several barriers in the case.", group=G, stim=stim)
    cm(CB, O, "L4", "The head's reply to the supervisor best illustrates:", "Closed-mindedness",
       [("Information overload", "the reply is short"), ("Physical distance", "they are in the same meeting"), ("Semantic noise", "the words are clear")],
       ["Dismissing input without considering it is closed-mindedness (a psychological barrier); it also discourages future feedback."],
       "Its after-effect (staff stop speaking) confirms the barrier.", group=G, stim=stim)
    cm(CB, O, "L4", "Which single change would address the most barriers in the case?",
       "Short plain-language messages on a channel staff can reach, with feedback invited",
       [("Longer and more detailed emails sent twice a day to every member of the field staff", "worsens overload and access"),
        ("Disciplinary action against field staff who miss the deadlines set in the emails", "treats symptoms, deepens fear"),
        ("Fewer meetings so that field staff have more time to read the emails carefully", "removes the feedback channel")],
       ["Plain language fixes the semantic barrier; an accessible channel fixes access; inviting feedback reverses closed-mindedness."],
       "The best remedy addresses the causes, not the missed deadlines.", group=G, stim=stim)

    # ---------------- Communication register by relationship ----------------
    cm(CR, F, "L1", "Which greeting best suits an email to your company's chairperson, Ms Sharma?",
       "Dear Ms Sharma,", [("Hey Sharma!", "casual and omits title"), ("Hi dear,", "over-familiar"), ("Yo, Chairperson!", "slang")],
       ["Senior, formal relationship -> title + surname."], "Formality rises with distance and seniority.")
    cm(CR, F, "L1", "The register normally used among close friends is:",
       "Casual", [("Frozen", "fixed, ritual language"), ("Formal", "official settings"), ("Consultative", "professional two-way exchange")],
       ["Casual register: relaxed vocabulary among peers and friends."], "Match register to relationship.")
    cm(CR, F, "L2", "A doctor explaining a diagnosis to a patient, who asks questions in between, is using which register?",
       "Consultative", [("Frozen", "no fixed ritual text"), ("Intimate", "not a close personal relationship"), ("Casual", "professional context")],
       ["Consultative register: expert-client exchange with feedback."], "Two-way professional talk = consultative.")
    cm(CR, F, "L2", "An oath of office read out word for word at a swearing-in ceremony is an example of which register?",
       "Frozen", [("Casual", "not relaxed talk"), ("Consultative", "no two-way exchange"), ("Intimate", "not private")],
       ["Frozen register: fixed wording that does not change (oaths, prayers, pledges)."], "Unchanging text = frozen.")
    cm(CR, F, "L2", "Which sentence is most appropriate for a bank clerk to say to a customer at the counter?",
       "How may I help you today?", [("What do you want?", "abrupt"), ("Yeah, what is it you want now?", "casual and dismissive"), ("Tell me fast, what?", "rude")],
       ["Service relationships call for polite, consultative language."], "Politeness markers ('may I').")

    cm(CR, O, "L3", "When an officer writes to a subordinate asking for a report, the tone should ideally be:",
       "Polite and direct", [("Curt and commanding", "damages the working relationship"), ("Chatty and informal", "unclear and unprofessional"),
                             ("Apologetic and vague", "unclear expectations")],
       ["Downward communication should be clear and courteous."], "Authority does not require curtness.")
    cm(CR, O, "L3", "Which is the most appropriate way to disagree with a senior officer in a meeting?",
       "I see your point, sir, but may I suggest an alternative?",
       [("That idea simply won't work, and everyone here knows it.", "confrontational"),
        ("Whatever you say, sir; I will just keep quiet then.", "sarcastic withdrawal"),
        ("With respect, that is honestly the worst plan I've heard.", "insult despite a polite opener")],
       ["Acknowledge, then offer an alternative respectfully (consultative-formal)."], "A polite opener does not excuse an insult.")
    cm(CR, O, "L3", "In a first formal letter to a customer, addressing the customer by first name is generally:",
       "Avoided; use title and surname", [("Preferred, as it builds warmth", "too familiar for a first formal contact"),
                                          ("Required by business etiquette", "etiquette requires the opposite"),
                                          ("Acceptable only in legal notices", "legal notices are even more formal")],
       ["Formal first contact uses title + surname; first names follow only when invited."], "Warmth must not replace formality.")
    cm(CR, O, "L3", "Consider the statements:\n1. The same message may need different registers for a peer and for a regulator.\n"
       "2. Consultative register involves a two-way exchange with feedback.\n3. Intimate register is suitable for official press releases.\n\nWhich are correct?",
       "1 and 2 only", [("2 and 3 only", "statement 3 is false"), ("1 and 3 only", "statement 3 is false"), ("1, 2 and 3", "statement 3 is false")],
       ["1: true.", "2: true.", "3: false; press releases need formal register."], "Intimate register is private.", kind="statement")
    cm(CR, O, "L3", "A team lead messages a new colleague on the office chat: 'Welcome aboard! Ping me if you get stuck.' The register is:",
       "Suitable for peer chat", [("Too formal for chat", "it is informal"), ("Frozen register", "not fixed ritual text"),
                                  ("Unacceptable anywhere", "fits informal internal chat")],
       ["Friendly, casual register suits informal internal chat between colleagues."], "Informal is not the same as inappropriate.")
    cm(CR, O, "L3", "When writing to a government department for the first time, a citizen should:",
       "Use a formal, clear tone", [("Use slang to seem friendly", "unsuitable register"), ("Write in all capital letters", "reads as shouting"),
                                    ("Skip the salutation", "discourteous")],
       ["First contact with an institution calls for formal register."], "Distance and officialdom raise formality.")
    cm(CR, O, "L3", "What most distinguishes the language used with an interviewer from that used with a classmate?",
       "Level of formality", [("Length of sentences", "varies in both"), ("Speed of speaking", "incidental"), ("Volume of voice", "incidental")],
       ["Register shifts chiefly in formality of vocabulary and forms of address."], "Register = formality level.")
    stim = ("Priya, a branch officer, must convey the same news (the branch will remain closed on Saturday for a system upgrade) "
            "to three audiences: (i) her regional manager, (ii) her colleague and friend Ravi, and (iii) the bank's customers, through a notice.")
    G = "ENB-G07"
    cm(CR, O, "L4", "Which message best suits audience (i), the regional manager?",
       "Sir, this is to inform you that the branch will remain closed on Saturday for a system upgrade.",
       [("Hey boss, heads up: no branch on Saturday, the system's getting upgraded. Enjoy!", "casual with a superior"),
        ("Dear valued customers, we regret the closure of the branch this Saturday for the upgrade.", "customer register"),
        ("Saturday's off because of some upgrade thing at the branch, just so you know, okay?", "vague and informal")],
       ["Upward communication: formal, precise, respectful."], "One message, three registers.", group=G, stim=stim)
    cm(CR, O, "L4", "Which message best suits audience (ii), her friend Ravi?",
       "Hi Ravi, the branch is shut on Saturday for the system upgrade, so enjoy the day off!",
       [("This is to inform you that the branch shall remain closed on Saturday for a system upgrade.", "stiffly formal for a friend"),
        ("Customers are hereby informed that the branch will remain closed on Saturday for maintenance.", "public-notice register"),
        ("Respected colleague, kindly note the closure of the branch on Saturday as per the directive.", "officialese for a friend")],
       ["A friend and peer: casual but clear."], "Over-formality is also a register error.", group=G, stim=stim)
    cm(CR, O, "L4", "Which text best suits audience (iii), the customer notice?",
       "Customers are informed that the branch will remain closed on Saturday owing to a system upgrade. We regret the inconvenience.",
       [("Guys, branch shut Saturday for an upgrade, so plan your visits around that and don't blame us later!", "casual and defensive"),
        ("Hi all, Priya here! We're closed this Saturday because of some upgrade thing, so see you all on Monday, cheers!", "personal and casual"),
        ("Closure on Saturday. Upgrade work. No services whatsoever. Management is not responsible for any issues arising from this.", "curt and unhelpful")],
       ["Public notice: impersonal, polite, complete, with an apology for inconvenience."], "Customer-facing text must be courteous and complete.",
       group=G, stim=stim)

    # ---------------- Tools of communication ----------------
    cm(CT, F, "L1", "Which document is the formal record of decisions taken at a meeting?",
       "Minutes", [("Agenda", "list of items before the meeting"), ("Invitation", "request to attend"), ("Brochure", "promotional leaflet")],
       ["Minutes record proceedings and decisions."], "Before (agenda) vs after (minutes).")
    cm(CT, F, "L1", "A document circulated before a meeting listing the items to be discussed is called the:",
       "Agenda", [("Minutes", "record after the meeting"), ("Report", "detailed findings"), ("Circular", "general information to many")],
       ["The agenda sets the order of business."], "Timing distinguishes agenda and minutes.")
    cm(CT, F, "L1", "Which tool is most suitable for an urgent two-way discussion with a colleague in another city?",
       "A phone or video call", [("A letter by post", "slow, one-way"), ("The notice board", "one-way, local"), ("The monthly newsletter", "slow, one-way")],
       ["Urgency plus two-way exchange -> synchronous channel."], "Speed and interactivity decide the channel.")
    cm(CT, F, "L2", "A written message sent from one department to another within the same organisation is a:",
       "Memorandum", [("Press release", "external, for media"), ("Tender notice", "external, invites bids"), ("Affidavit", "sworn legal statement")],
       ["A memo is an internal written communication."], "Internal vs external documents.")
    cm(CT, F, "L2", "Which tool is mainly used to inform the media and public about an organisation's announcement?",
       "Press release", [("Memorandum", "internal"), ("Minutes", "meeting record"), ("Office order", "internal directive")],
       ["Press releases are issued to the media for public dissemination."], "Audience decides the tool.")

    cm(CT, O, "L3", "To communicate a new leave policy to 5,000 employees so that it serves as a lasting reference, the best tool is:",
       "A written circular", [("A phone call to each employee", "impractical and leaves no record"), ("A short team huddle", "no lasting record, limited reach"),
                              ("A casual chat message", "informal and easily lost")],
       ["Wide reach + permanence + formality -> written circular."], "Permanence is the key requirement.")
    cm(CT, O, "L3", "Which tool is best for collecting structured feedback from 2,000 customers?",
       "An online questionnaire", [("A press release", "one-way outward"), ("A notice board", "one-way, local"), ("Individual meetings", "impractical at scale")],
       ["Structured, large-scale input -> survey/questionnaire."], "Scale and structure.")
    cm(CT, O, "L3", "A manager must tell an employee that his contract will not be renewed. The most appropriate first channel is:",
       "A private meeting", [("A group email", "breaches privacy"), ("The notice board", "public and insensitive"), ("A text message", "impersonal for sensitive news")],
       ["Sensitive, personal news -> private face-to-face (rich) channel, followed by written confirmation."], "Channel richness should match message sensitivity.")
    cm(CT, O, "L3", "Match each tool with its main purpose:\n\n| Tool | Purpose |\n|---|---|\n| A. Agenda | 1. Periodic update on organisational news |\n"
       "| B. Minutes | 2. Record of proceedings and decisions |\n| C. Memo | 3. Brief internal written communication |\n| D. Newsletter | 4. List of items for a meeting |",
       "A-4, B-2, C-3, D-1", [("A-2, B-4, C-3, D-1", "agenda and minutes swapped"), ("A-4, B-2, C-1, D-3", "memo and newsletter swapped"),
                             ("A-2, B-4, C-1, D-3", "both pairs swapped")],
       ["Agenda lists items; minutes record; memo is internal; newsletter updates periodically."], "Two pairs are commonly confused.", kind="match")
    cm(CT, O, "L3", "Which is a limitation of email compared with face-to-face communication?",
       "Absence of non-verbal cues", [("No written record", "email creates a record"), ("Cannot reach distant people", "email reaches anywhere"),
                                      ("Slower than postal mail", "email is faster")],
       ["Email lacks tone, facial expression and body language."], "Channel richness.")
    cm(CT, O, "L3", "A team spread across four cities must edit a budget document at the same time. The best tool is:",
       "A shared online document", [("Printed copies by courier", "slow; versions diverge"), ("A weekly phone call", "no shared editing"),
                                    ("A notice-board posting", "one-way, local")],
       ["Simultaneous collaboration needs a shared, version-controlled online document."], "Collaboration vs broadcast tools.")
    cm(CT, O, "L3", "Consider the statements:\n1. Video conferencing conveys some non-verbal cues that email cannot.\n"
       "2. A circular is a two-way tool meant for immediate feedback.\n3. A notice board suits information meant for a large group at one location.\n\nWhich are correct?",
       "1 and 3 only", [("1 and 2 only", "statement 2 is false"), ("2 and 3 only", "statement 2 is false"), ("1, 2 and 3", "statement 2 is false")],
       ["1: true.", "2: false; a circular is one-way.", "3: true."], "One-way vs two-way tools.", kind="statement")
    stim = ("A district cooperative bank wants to: (a) announce a new crop-loan scheme to farmers in 300 villages, many with low literacy; "
            "(b) brief its 40 branch managers on the scheme's operating rules and clear their doubts; and (c) keep an authoritative record "
            "of the scheme's terms for audit.")
    G = "ENB-G08"
    cm(CT, O, "L4", "Which is the best tool for task (a)?",
       "Village meetings and local-language radio announcements",
       [("A detailed email sent to each farmer's registered address", "low literacy and access"),
        ("A press release in an English-language national daily", "wrong language and reach"),
        ("A circular uploaded to the bank's website for downloading", "low access and literacy")],
       ["Low-literacy, dispersed audience -> oral, local-language, community channels."], "Audience literacy and access decide.", group=G, stim=stim)
    cm(CT, O, "L4", "Which is the best tool for task (b)?",
       "A video conference with a question-and-answer session",
       [("A poster displayed on each branch's notice board", "one-way; doubts not cleared"),
        ("A press release issued to the regional media", "external audience"),
        ("A brief SMS alert sent to every branch manager", "too brief; one-way")],
       ["Small, dispersed professional group needing clarification -> interactive video conference."], "Two-way need.", group=G, stim=stim)
    cm(CT, O, "L4", "Which is the best tool for task (c)?",
       "A board-approved written scheme document and circular",
       [("Recordings of the radio announcements made in villages", "informal, incomplete record"),
        ("Notes taken by managers during the video conference", "unofficial, inconsistent"),
        ("Messages exchanged in the managers' chat group", "informal, not authoritative")],
       ["Audit needs an authoritative, formal, written, approved record."], "Authority and permanence decide.", group=G, stim=stim)
