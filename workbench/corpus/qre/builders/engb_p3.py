"""ENG-B part 3: no-improvement cases, phrase replacement (incl. note set), redundancy, para jumbles (incl. set)."""

NIM = "eng-no-improvement-required-cases-ede5f5eb"
PH = "eng-phrase-replacement-623032a6"
RD = "eng-redundancy-and-wordiness-1787d0ac"
PJ = "eng-sentence-rearrangement-para-jumble-66cc898f"


def add_all(B, H):
    mc, si, pj, pj_stim, NI = H["mc"], H["si"], H["pj"], H["pj_stim"], H["NI"]
    F, O = "foundation", "officer"
    OK = "the bold part is already correct"

    # ---------------- No-improvement-required cases ----------------
    si(NIM, F, "L1", "She **has lived** in Mumbai since 2015.", NI,
       [("is living", "present continuous with 'since'"), ("lived", "simple past with 'since'"),
        ("had lived", "past perfect without a past reference point")],
       "An action from a past point up to now, with 'since', takes the present perfect; the sentence is correct.",
       "since + point of time -> present perfect", "Do not change a correct form just because options exist.")
    si(NIM, F, "L1", "Neither of the answers **is** correct.", NI,
       [("are", "'neither of' takes a singular verb"), ("were", "plural and past"), ("have been", "plural auxiliary")],
       "'Neither of' + plural noun takes a singular verb; 'is' is correct.", "neither of + singular verb",
       "The plural 'answers' tempts a plural verb.")
    si(NIM, F, "L2", "He **insisted on paying** the bill.", NI,
       [("insisted to pay", "'insist' does not take a to-infinitive"), ("insisted for paying", "'insist for' is not idiomatic"),
        ("insisted that paying", "'that' needs a full clause")],
       "'Insist on' + gerund is the correct pattern.", "insist on + V-ing", "Alternatives look formal but are wrong.")
    si(NIM, F, "L2", "I **look forward to hearing** from you.", NI,
       [("look forward to hear", "'to' is a preposition here, needing a gerund"),
        ("look forward for hearing", "wrong preposition"),
        ("am looking forward to hear", "continuous plus base form after preposition 'to'")],
       "'Look forward to' + gerund is correct as written.", "look forward to + V-ing",
       "The base-form option is the most common error.")
    si(NIM, F, "L2", "**The poors** deserve better access to credit.", "The poor",
       [("Poor", "adjective without 'the' cannot act as a noun"), ("The poor people's", "possessive has no noun to govern"),
        (NI, "'poor' used as a plural noun takes no -s")],
       "'The + adjective' denotes a class of people and never takes a plural -s: 'the poor', 'the rich'.",
       "the + adjective = plural class noun (no -s)", "Not every item in this set is already correct.")

    si(NIM, O, "L3", "**Had I known** about the strike, I would have taken the metro.", NI,
       [("If I knew", "second-conditional form with a third-conditional result"),
        ("If I would have known", "'would have' in the if-clause"),
        ("Did I know", "inversion with 'did' is not a conditional form")],
       "Inverted third conditional 'Had I known' = 'If I had known'; it matches 'would have taken'.",
       "Had + S + V3, S + would have + V3", "Inversion looks unusual but is correct.")
    si(NIM, O, "L3", "Scarcely **had the meeting begun when** the fire alarm rang.", NI,
       [("had the meeting begun than", "'scarcely' pairs with 'when'"),
        ("the meeting had begun when", "no inversion after fronted 'scarcely'"),
        ("did the meeting begin than", "wrong auxiliary and wrong correlative")],
       "Fronted 'scarcely' + inversion + past perfect, followed by 'when': the sentence is correct.",
       "Scarcely had + S + V3 + when", "Both the inversion and the correlative are already right.")
    si(NIM, O, "L3", "He is one of the few officers who **have** refused a promotion.", NI,
       [("has", "relative 'who' refers to plural 'officers'"), ("had been", "tense and voice changed"),
        ("is having", "continuous form of a stative/possessive idea")],
       "'Who' refers to 'officers', so 'have' is correct.", "relative pronoun agrees with antecedent",
       "The singular 'He' attracts 'has'.")
    si(NIM, O, "L3", "I would rather you **stayed** at home today.", NI,
       [("stay", "base form after 'would rather + subject' (not standard British usage)"),
        ("will stay", "future form not used after 'would rather'"),
        ("have stayed", "perfect form changes the time reference")],
       "'Would rather + another subject' takes the past subjunctive for present/future reference.",
       "would rather + S + V2", "The past form refers to today, not the past.")
    si(NIM, O, "L3", "The committee **has submitted its** report.", NI,
       [("have submitted its", "plural verb with singular pronoun"), ("has submitted their", "singular verb with plural pronoun"),
        ("have submitted his", "plural verb and wrong pronoun")],
       "Verb and pronoun are both singular, treating the committee as one body: consistent and correct.",
       "Collective noun: verb and pronoun must agree", "The mixed options are the trap.")
    si(NIM, O, "L3", "He **is senior than** me in service.", "is senior to",
       [("is senior from", "wrong preposition"), (NI, "'senior' does not take 'than'"),
        ("was seniors to", "adjective made plural; tense changed")],
       "'Senior' takes 'to'.", "senior/junior/superior + to", "Only some items are correct as they stand.")
    si(NIM, O, "L3", "Each of the three proposals **has its merits**.", NI,
       [("have their merits", "'each of' is singular"), ("has their merits", "plural pronoun for singular 'each'"),
        ("have its merits", "plural verb with singular 'each'")],
       "'Each' is singular: 'has its'.", "each of + singular verb + singular pronoun", "All variants look plausible.")
    si(NIM, O, "L3", "**Being a rainy day**, we stayed indoors.", "It being a rainy day",
       [("Having a rainy day", "still a dangling participle with a changed meaning"),
        ("Since being a rainy day", "no subject for 'being'"),
        (NI, "dangling participle: 'we' were not a rainy day")],
       "Without its own subject the participle attaches to 'we'. The absolute construction 'It being a rainy day' fixes this.",
       "Absolute phrase: noun/pronoun + participle", "Sounds natural but is a dangling modifier.")
    si(NIM, O, "L3", "She **prefers tea to coffee**.", NI,
       [("prefers tea than coffee", "'prefer' takes 'to', not 'than'"),
        ("prefers tea over than coffee", "two prepositions"),
        ("is preferring tea to coffee", "'prefer' is stative")],
       "'Prefer X to Y' is correct.", "prefer + to", "'Than' is attracted by the comparative sense.")
    si(NIM, O, "L3", "The principal, with his staff, **were** present.", "was",
       [("have been", "plural auxiliary"), ("are", "plural and present"), (NI, "'with his staff' does not make the subject plural")],
       "The subject is 'the principal'; the verb is 'was'.", "with / along with / as well as -> verb follows the first subject",
       "The plural 'staff' near the verb misleads.")

    # ---------------- Phrase replacement ----------------
    si(PH, F, "L1", "She **did a mistake** in the calculation.", "made a mistake",
       [("had a mistake", "wrong collocation"), ("took a mistake", "wrong collocation"), (NI, "'do a mistake' is not idiomatic")],
       "The collocation is 'make a mistake'.", "make a mistake / make an effort / do one's duty",
       "Literal translation from Indian languages produces 'do a mistake'.")
    si(PH, F, "L1", "He **gave an exam** yesterday.", "took an exam",
       [("made an exam", "wrong collocation (examiners set exams)"), ("passed an exam", "changes the meaning to success"),
        (NI, "'give an exam' means to set or conduct it, not to sit it")],
       "A candidate takes (or sits) an exam; an examiner gives or sets one.", "take/sit an exam",
       "'Give an exam' is common in Indian speech.")
    si(PH, F, "L2", "The rise in prices **is effecting** the poor.", "is affecting",
       [("has effected", "'effect' (verb) means to bring about"), ("is effected", "passive of the wrong verb"),
        (NI, "'effect' used where 'affect' is meant")],
       "'Affect' (verb) = to influence; 'effect' (verb) = to bring about.", "affect (v.) vs effect (v./n.)",
       "The two words sound alike.")
    si(PH, F, "L2", "Please **discuss about** the matter with the manager.", "discuss",
       [("discuss on", "'discuss' takes no preposition"), ("discuss regarding", "'regarding' is redundant after 'discuss'"),
        (NI, "'discuss' is transitive")],
       "'Discuss' takes a direct object: 'discuss the matter'.", "discuss + object (no preposition)",
       "'Talk about' is correct, so 'discuss about' seems natural.")
    si(PH, F, "L2", "I **am having** two brothers.", "have",
       [("am had", "impossible form"), ("have been having", "continuous of a stative verb"),
        (NI, "possession verb 'have' is stative")],
       "'Have' meaning possess is not used in the continuous.", "stative verbs: simple tenses only",
       "'Am having lunch' is fine, which confuses learners.")

    si(PH, O, "L3", "The auditors **turned a blind eye towards** the discrepancies.", "turned a blind eye to",
       [("turned blind eyes on", "idiom altered"), ("turned a blind eye at", "wrong preposition"), (NI, "idiom takes 'to'")],
       "The fixed idiom is 'turn a blind eye to' (deliberately ignore).", "turn a blind eye to", "Idioms do not allow preposition swaps.")
    si(PH, O, "L3", "The new rule **will come into affect** from April.", "will come into effect",
       [("will come in effect", "preposition changed"), ("will come to effect", "preposition changed"),
        (NI, "'affect' is a verb; the noun is 'effect'")],
       "'Come into effect' uses the noun 'effect'.", "come into effect / take effect", "Affect/effect confusion.")
    si(PH, O, "L3", "He **availed the opportunity** to address the board.", "made use of the opportunity",
       [("availed of the opportunity", "'avail' needs a reflexive: avail oneself of"),
        ("availed the opportunity of", "preposition misplaced"),
        (NI, "'avail' used without the reflexive pronoun")],
       "'Avail' in this sense is reflexive (availed himself of); among the options only 'made use of' is correct.",
       "avail oneself of = make use of", "'Availed of' is common Indian officialese but is non-standard.")
    si(PH, O, "L3", "The shortfall **was made up for** by a special grant.", NI,
       [("was made up with", "wrong particle"), ("was made for up", "particles in the wrong order"),
        ("was made out for", "different phrasal verb (make out)")],
       "'Make up for' = compensate; its passive 'was made up for' is correct.", "make up for (compensate)",
       "Stacked particles look odd but are correct.")
    si(PH, O, "L3", "Kindly **revert back** at the earliest.", "reply",
       [("revert back to us", "'revert back' is redundant and 'revert' means go back"),
        ("return back", "redundant: 'return' already means go back"),
        (NI, "'revert' means return to a former state; 'back' is redundant")],
       "In standard English 'revert' means return to a previous state; 'reply' is the correct word here.",
       "revert = go back to a former state", "Officialese in Indian offices.")
    si(PH, O, "L3", "The scheme **is aimed to benefit** small traders.", "is aimed at benefiting",
       [("is aimed for benefiting", "wrong preposition"), ("aims at benefit", "noun after 'at' changes the structure"),
        (NI, "passive 'aimed' takes 'at' + gerund")],
       "'Be aimed at + gerund' is the idiomatic pattern.", "be aimed at + V-ing", "Active 'aims to benefit' is fine; the passive differs.")
    si(PH, O, "L3", "He was **bent upon to resign** from the post.", "bent upon resigning",
       [("bent to resign upon", "preposition displaced"), ("bent for resigning", "wrong preposition"),
        (NI, "a preposition cannot be followed by a to-infinitive")],
       "'Bent upon' (determined) is followed by a gerund.", "bent on/upon + V-ing", "Preposition + to-infinitive is never correct.")
    stim = ("Read the office note and answer the question that follows.\n\n"
            "'The regional office has **(i) given its approval on** the revised timings. Staff **(ii) who are desirous to avail** "
            "the flexible shift must apply by Friday. Applications received after the deadline "
            "**(iii) will not be entertained under no circumstances**.'")
    G = "ENB-G02"
    mc(PH, O, "L4", "Which is the best replacement for the phrase marked (i)? If none is needed, choose 'No improvement'.",
       "approved",
       [("given its approval at", "wrong preposition"), ("given approval on to", "stacked prepositions"),
        (NI, "'approval' takes 'to' or 'of', not 'on'")],
       ["'Approval on' is not idiomatic; 'approved' says the same thing concisely and correctly."],
       "approve / give approval to", "Replacing a wordy phrase with a single verb is often the right choice.",
       group=G, stim=stim)
    mc(PH, O, "L4", "Which is the best replacement for the phrase marked (ii)?",
       "who wish to avail themselves of",
       [("who are desirous to avail of", "'desirous' takes 'of'; 'avail' needs a reflexive"),
        ("who desire availing", "'avail' still lacks the reflexive"),
        (NI, "'desirous to' and 'avail' without reflexive are both non-standard")],
       ["'Avail' is reflexive (avail oneself of).", "'Wish to' replaces the stilted 'are desirous to'."],
       "avail oneself of", "Two errors sit in one phrase.", group=G, stim=stim)
    mc(PH, O, "L4", "Which is the best replacement for the phrase marked (iii)?",
       "will not be entertained under any circumstances",
       [("will not be entertained in no circumstances", "double negative remains"),
        ("will not entertain under any circumstances", "active voice: applications do not entertain"),
        (NI, "double negative 'not ... no'")],
       ["'Not ... no' is a double negative; after 'not' use 'any'."],
       "not ... any (never not ... no)", "The active option removes the double negative but breaks the meaning.",
       group=G, stim=stim)

    # ---------------- Redundancy and wordiness ----------------
    si(RD, F, "L1", "He **returned back** home at night.", "returned",
       [("returned again back", "adds more redundancy"), ("came back again", "'again' adds a new, wrong meaning"),
        (NI, "'back' repeats the idea in 'returned'")],
       "'Return' already means come back.", "return (not return back)", "Redundant pairs sound emphatic.")
    si(RD, F, "L1", "The **reason why he failed is because** he did not study.", "reason he failed is that",
       [("reason why he failed is due to", "'reason ... due to' is redundant"),
        ("reason for which he failed is because", "'reason ... because' remains"),
        (NI, "'reason' and 'because' repeat the idea of cause")],
       "'The reason is that ...' avoids repeating the idea of cause.", "the reason ... is that", "'Reason ... because' is a classic redundancy.")
    mc(RD, F, "L2", "Choose the sentence that is free from redundancy.",
       "Please repeat the question.",
       [("Kindly repeat the question again.", "'repeat' already means say again"),
        ("Please repeat back the question.", "'back' is superfluous"),
        ("Please once again repeat the question.", "'once again' duplicates 'repeat'")],
       ["'Repeat' includes the idea of 'again'."], "repeat (not repeat again)", "The concise sentence is correct.")
    si(RD, F, "L2", "The **final outcome** of the talks is awaited.", "outcome",
       [("final end outcome", "adds another redundant word"), ("ultimate final outcome", "double redundancy"),
        (NI, "an outcome is by nature final")],
       "'Outcome' already implies the end result.", "outcome (not final outcome)", "'Final' feels natural before 'outcome'.")
    si(RD, F, "L2", "We should **cooperate together** to finish the work.", "cooperate",
       [("co-operate jointly", "'jointly' repeats the idea"), ("cooperate mutually together", "double redundancy"),
        (NI, "'co-' already means together")],
       "'Cooperate' means work together.", "cooperate (not cooperate together)", "Prefix meanings are ignored.")

    si(RD, O, "L3", "The **consensus of opinion** among the members was to defer the vote.", "consensus",
       [("general consensus of opinion", "adds 'general', another redundancy"), ("consensus of opinions", "still redundant"),
        (NI, "'consensus' already means general agreement of opinion")],
       "'Consensus' means agreement of opinion.", "consensus (not consensus of opinion)", "A frequent phrase in reports.")
    si(RD, O, "L3", "The two proposals are **exactly identical in every respect**.", "identical",
       [("exactly identical", "'exactly' repeats 'identical'"), ("identically same", "non-standard and redundant"),
        (NI, "three expressions carry the same meaning")],
       "'Identical' already means exactly alike in every respect.", "identical", "Emphasis creates wordiness.")
    si(RD, O, "L3", "**In my opinion, I think** the plan will fail.", "I think",
       [("In my opinion I feel", "two expressions of opinion"), ("According to me, I think", "non-standard and redundant"),
        (NI, "'in my opinion' and 'I think' say the same thing")],
       "Keep one marker of opinion.", "One opinion marker", "Common in speech.")
    si(RD, O, "L3", "The meeting has been postponed **till a later date in future**.", "to a later date",
       [("until later date in future", "article missing and redundancy retained"), ("till future later date", "ungrammatical"),
        (NI, "'later date' already refers to the future")],
       "'Postponed to a later date' is concise and idiomatic.", "postpone to a later date", "'In future' repeats 'later'.")
    si(RD, O, "L3", "The factory will be closed **for a period of two weeks' duration**.", "for two weeks",
       [("for a period of two weeks' time", "still redundant"), ("for duration of two weeks period", "ungrammatical and redundant"),
        (NI, "'period' and 'duration' both repeat the idea of time")],
       "'For two weeks' conveys the full meaning.", "Cut 'a period of' and 'duration'", "Official drafting loves padding.")
    mc(RD, O, "L3", "Which sentence is free from redundancy?",
       "The committee will reconvene after lunch.",
       [("The committee will reconvene again after lunch.", "'re-' already means again"),
        ("The committee will meet again once more after lunch.", "'again' and 'once more' repeat"),
        ("The committee will again reassemble after lunch.", "'again' repeats 're-'")],
       ["The prefix 're-' carries the meaning 'again'."], "re- = again", "The shortest option is correct here.")
    si(RD, O, "L3", "His **past history** shows that he can be trusted.", "history",
       [("past track history", "adds more redundancy"), ("previous past history", "double redundancy"),
        (NI, "history is by definition past")],
       "'History' already refers to the past.", "history (not past history)", "A very common pleonasm.")
    si(RD, O, "L3", "The bank offers a **free gift** to every new account holder.", "gift",
       [("free complimentary gift", "adds more redundancy"), ("gift for free of cost", "'for free of cost' is redundant and ungrammatical"),
        (NI, "a gift is free by definition")],
       "'Gift' already implies no payment.", "gift (not free gift)", "Advertising language normalises the pleonasm.")
    si(RD, O, "L3", "**The reason for the delay was owing to** heavy traffic.", "The delay was caused by",
       [("The reason for the delay was due to", "'reason ... due to' is redundant"),
        ("The reason of the delay was because of", "wrong preposition and redundancy"),
        (NI, "'reason' and 'owing to' both express cause")],
       "State the cause once: 'The delay was caused by heavy traffic.'", "Express cause once", "Swapping 'owing to' for 'due to' does not help.")
    si(RD, O, "L3", "**Despite the fact that it was raining**, they continued the match.", "Although it was raining",
       [("Despite of it raining", "'despite of' is incorrect"), ("In spite of the fact of raining", "wordy and unidiomatic"),
        (NI, "grammatical but wordy; a concise alternative exists")],
       "'Although' + clause expresses the same contrast in fewer words.", "despite the fact that -> although",
       "Candidates keep grammatical-but-wordy forms.")

    # ---------------- Para jumbles ----------------
    pj(PJ, F, "L1", [
        "Rekha decided to start walking every morning to improve her health.",
        "On the first day, she managed only a slow ten-minute round of the park.",
        "Within a month, however, the ten minutes had grown to forty.",
        "Encouraged by this progress, she persuaded her neighbour to join her.",
        "Now the two of them are rarely seen missing their morning round."], "RPTQS",
       [("RPQTS", "neighbour joins before 'this progress' has been described"),
        ("PRTQS", "'On the first day' placed before the decision it refers to"),
        ("RTPQS", "'Within a month' placed before 'the first day'")],
       ["R introduces Rekha and her decision (opening).", "P 'On the first day' follows the decision.",
        "T 'Within a month, however, the ten minutes' refers back to P.", "Q 'this progress' refers to T.",
        "S 'Now the two of them' needs the neighbour from Q."],
       "Time markers (first day -> within a month -> now) fix the sequence.")
    pj(PJ, F, "L1", [
        "Water from oceans and lakes evaporates when heated by the sun.",
        "The vapour rises and cools as it reaches higher altitudes.",
        "This cooling causes it to condense into tiny droplets that form clouds.",
        "When the droplets grow heavy, they fall back as rain.",
        "The rainwater eventually flows back into the oceans, completing the cycle."], "QSPTR",
       [("QPSTR", "'This cooling' placed before the cooling is mentioned"),
        ("SQPTR", "'The vapour' placed before evaporation produces it"),
        ("QSTPR", "'the droplets' placed before droplets are formed")],
       ["Q (evaporation) starts the process.", "S 'The vapour' needs Q.", "P 'This cooling' refers to S.",
        "T 'the droplets' refers to P.", "R 'completing the cycle' closes."],
       "Definite articles ('the vapour', 'the droplets') point back to earlier sentences.")
    pj(PJ, F, "L2", [
        "Ajay needed a passport urgently for an overseas conference.",
        "He filled in the application online and booked the earliest appointment.",
        "At the passport office, his documents were checked and his photograph taken.",
        "A week later, a police officer visited his home for verification.",
        "Soon afterwards, the passport arrived by speed post, just in time for his trip."], "TRQPS",
       [("TQRPS", "office visit placed before the application and appointment"),
        ("TRPQS", "police verification placed before the office visit it follows"),
        ("RTQPS", "'He' used before Ajay is introduced")],
       ["T introduces Ajay and the need.", "R 'He filled in ... booked appointment'.", "Q the appointment at the office.",
        "P 'A week later' refers to the office visit.", "S 'Soon afterwards' closes with the passport's arrival."],
       "Process order plus pronoun reference ('He' needs Ajay).")
    pj(PJ, F, "L2", [
        "The village had no library until two young teachers took up the cause.",
        "They collected old books from friends and relatives in the city.",
        "A retired postmaster offered them a spare room in his house to store the books.",
        "The room soon became a reading corner where children gathered every evening.",
        "Its success prompted the panchayat to sanction a proper library building."], "SQTRP",
       [("SQRTP", "'The room' placed before the room is offered"),
        ("STQRP", "'the books' stored before they are collected"),
        ("QSTRP", "'They' used before the teachers are introduced")],
       ["S introduces the teachers.", "Q 'They collected old books'.", "T offers a room 'to store the books'.",
        "R 'The room' refers to T.", "P 'Its success' refers to the reading corner."],
       "Track each noun from first mention (a spare room) to later reference (the room).")
    pj(PJ, F, "L2", [
        "Small shopkeepers were once reluctant to accept digital payments.",
        "They feared hidden charges and doubted whether the money would really reach them.",
        "The arrival of free QR codes and instant confirmation messages removed these fears.",
        "As a result, even roadside vendors now display a QR code at their stalls.",
        "For customers, this has made carrying cash almost unnecessary."], "PTRSQ",
       [("PRTSQ", "'these fears' mentioned before the fears are stated"),
        ("PTSRQ", "'As a result' placed before its cause"),
        ("TPRSQ", "'They' used before shopkeepers are introduced")],
       ["P introduces the reluctance.", "T 'They feared ...' explains it.", "R 'removed these fears' refers to T.",
        "S 'As a result' follows R.", "Q 'For customers, this ...' extends the result."],
       "Problem -> reason -> solution -> result -> wider effect.")

    pj(PJ, O, "L3", [
        "When prices rise persistently, the purchasing power of money declines.",
        "To check this, the central bank may raise its policy rate.",
        "A higher policy rate makes borrowing costlier for banks.",
        "Banks, in turn, pass on the cost by charging more on loans to households and firms.",
        "Costlier credit dampens spending, which eases the pressure on prices.",
        "The trade-off, however, is that slower spending can also slow economic growth."], "RUPTQS",
       [("RPUTQS", "effect of a higher rate stated before the rate is raised"),
        ("RUTPQS", "'in turn' placed before the step it follows"),
        ("RUPTSQ", "'The trade-off' placed before the benefit it qualifies")],
       ["R states the problem (no back-reference).", "U 'To check this' refers to R.", "P 'A higher policy rate' follows U.",
        "T 'Banks, in turn' follows P.", "Q 'Costlier credit' follows T.", "S 'The trade-off, however' closes."],
       "Chain of cause and effect; 'in turn' and 'however' are position markers.")
    pj(PJ, O, "L3", [
        "Self-help groups usually consist of ten to twenty women from the same locality.",
        "Members save a small amount every month and pool it into a common fund.",
        "From this fund, loans are given to members for needs such as school fees or seeds.",
        "Once the group has shown a steady record of saving and repayment, it becomes eligible for a bank loan.",
        "This link with formal credit frees members from dependence on moneylenders.",
        "It is for this reason that such groups are widely regarded as a tool of financial inclusion."], "QSUPRT",
       [("QUSPRT", "'this fund' mentioned before the fund is created"),
        ("QSUPTR", "'for this reason' placed before the reason is given"),
        ("SQUPRT", "'Members' introduced before the group is defined")],
       ["Q defines the group.", "S 'Members save ... common fund'.", "U 'From this fund' refers to S.",
        "P 'record of saving and repayment' needs S and U.", "R 'This link with formal credit' refers to the bank loan in P.",
        "T 'for this reason' concludes."],
       "Demonstratives ('this fund', 'this link', 'this reason') each point to the immediately preceding idea.")
    pj(PJ, O, "L3", [
        "Remote work was once regarded as a perk offered by only a few technology firms.",
        "The pandemic changed that almost overnight, as offices across sectors were forced to shut.",
        "Many employers who had resisted the idea discovered that productivity did not collapse.",
        "Some, in fact, reported savings on rent and lower attrition.",
        "Unsurprisingly, a number of them have retained hybrid arrangements even after offices reopened."], "SPTRQ",
       [("SPRTQ", "'Some' placed before the group of employers is introduced"),
        ("PSTRQ", "'changed that' placed before 'that' is stated"),
        ("SPTQR", "'Unsurprisingly' conclusion placed before its supporting evidence")],
       ["S sets the earlier situation.", "P 'changed that' refers to S.", "T introduces employers' discovery.",
        "R 'Some, in fact' narrows T.", "Q 'Unsurprisingly, a number of them' concludes."],
       "'In fact' intensifies the previous sentence; 'Unsurprisingly' signals a conclusion.")
    pj(PJ, O, "L3", [
        "Nearly a third of the food we eat depends on pollination by insects.",
        "Among these insects, honeybees are the most important commercially.",
        "Their numbers, however, have been falling in many regions.",
        "Scientists attribute the decline to pesticides, habitat loss and disease.",
        "Unless these causes are addressed, yields of fruits and oilseeds could suffer.",
        "To avert such losses, farmers are being encouraged to keep flowering hedgerows and to limit spraying."], "TRUPSQ",
       [("TRPUSQ", "'the decline' explained before the decline is stated"),
        ("TRUSPQ", "'these causes' mentioned before the causes are listed"),
        ("RTUPSQ", "'these insects' used before insects are mentioned")],
       ["T introduces insect pollination.", "R 'Among these insects' refers to T.", "U 'Their numbers, however' refers to honeybees.",
        "P 'the decline' refers to U.", "S 'these causes' refers to P.", "Q 'such losses' refers to S."],
       "Every sentence after the first opens with a back-reference; follow the chain.")
    pj(PJ, O, "L3", [
        "A customer who has a complaint against a bank should first write to the bank itself.",
        "The bank is expected to acknowledge the complaint and resolve it within a stipulated time.",
        "If the reply is unsatisfactory, or if no reply is received within that time, the customer may approach the ombudsman.",
        "The ombudsman examines the complaint and first tries to settle it through conciliation.",
        "Where conciliation fails, the ombudsman may pass an award directing the bank to compensate the customer.",
        "This layered arrangement spares customers the cost and delay of going to court."], "UQSPTR",
       [("UQPSTR", "ombudsman examines the complaint before the customer approaches"),
        ("USQPTR", "'that time' used before the time limit is mentioned"),
        ("UQSPRT", "summary placed before the final stage of the process")],
       ["U: first step, write to the bank.", "Q: bank must resolve 'within a stipulated time'.", "S: 'within that time' refers to Q.",
        "P: ombudsman examines.", "T: 'Where conciliation fails' follows P.", "R: 'This layered arrangement' summarises."],
       "Procedural order plus 'that time' and 'conciliation' as linking words.")

    sents = ["Agriculture in many dry regions depends heavily on groundwater.",
             "Flood irrigation, the most common method, wastes much of this water through evaporation and run-off.",
             "Drip irrigation offers an alternative by delivering water drop by drop directly to the roots.",
             "The method can cut water use sharply while also improving yields.",
             "Its high initial cost, however, has kept many small farmers away.",
             "Subsidies and group purchase schemes are now being used to bridge this gap."]
    lab = "SPURQT"
    stim = pj_stim(sents, lab)
    G = "ENB-G03"
    cues = ["Order: S (groundwater) -> P ('this water') -> U ('an alternative') -> R ('The method') -> Q ('Its high initial cost, however') -> T ('this gap')."]
    rule = "Back-references fix each link: this water, an alternative, the method, its, this gap."
    mc(PJ, O, "L4", "Which sentence should come FIRST?", "S",
       [("P", "'this water' needs an earlier mention of water"), ("U", "'an alternative' needs a method to replace"),
        ("Q", "'Its' has no antecedent at the start")],
       cues + ["S is the only sentence with no back-reference."], rule, "Opening sentences introduce, never refer back.",
       group=G, stim=stim)
    mc(PJ, O, "L4", "Which sentence should come THIRD?", "U",
       [("R", "'The method' needs drip irrigation to be named first"), ("P", "P is second, right after S"),
        ("Q", "Q depends on R's claim of benefits")],
       cues, rule, "Count positions only after fixing the whole order.", group=G, stim=stim)
    mc(PJ, O, "L4", "Which sentence comes immediately AFTER R?", "Q",
       [("T", "'this gap' needs the cost problem in Q first"), ("U", "U precedes R"),
        ("S", "S is the opening sentence")],
       cues, rule, "'However' contrasts Q with the benefits stated in R.", group=G, stim=stim)
    mc(PJ, O, "L4", "Which sentence should come LAST?", "T",
       [("Q", "Q states the problem that T solves"), ("R", "R is followed by the contrast in Q"),
        ("U", "U is third")],
       cues, rule, "Solutions usually follow the problem statement.", group=G, stim=stim)
    mc(PJ, O, "L4", "Which pair of sentences appears consecutively, in this order, in the correct paragraph?", "U-R",
       [("P-R", "U must come between P and R"), ("Q-U", "Q comes after U, not before it"),
        ("T-Q", "reverse of the actual order Q-T")],
       cues, rule, "Check direction as well as adjacency.", group=G, stim=stim)
