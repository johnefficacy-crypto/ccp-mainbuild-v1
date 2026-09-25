"""ENG-B part 2: pronouns, segment-marked error identification (incl. passage set), subject-verb agreement, tense."""

PR = "eng-pronoun-reference-and-agreement-d6412298"
SM = "eng-segment-marked-error-identification-8879fab9"
SV = "eng-subject-verb-agreement-07be8ac5"
TS = "eng-tense-and-sequence-of-tenses-7e82f0cb"


def add_all(B, H):
    mc, es = H["mc"], H["es"]
    F, O = "foundation", "officer"

    # ---------------- Pronoun reference and agreement ----------------
    es(PR, F, "L1", ["Between you and I,", "the plan", "is unlikely to work."], 0,
       "Between you and me, the plan is unlikely to work.",
       "Object case after a preposition",
       "'Between' is a preposition, so both pronouns must be in the objective case: 'you and me'.",
       "'You and I' sounds polite and formal, which makes the error attractive.")
    mc(PR, F, "L1", "Fill in the blank (formal usage):\n\n'It was ___ who called you.'",
       "she", [("her", "objective case after 'was' is informal, not the formal standard"),
               ("hers", "possessive pronoun does not fit"), ("herself", "reflexive without an antecedent")],
       "In formal grammar the complement of 'be' takes the subjective case: 'It was she'.",
       "It + be + subjective pronoun (formal)", "Exams follow the formal convention.")
    es(PR, F, "L2", ["Ravi and myself", "will attend", "the workshop."], 0,
       "Ravi and I will attend the workshop.",
       "Reflexive pronouns need an antecedent in the same clause",
       "'Myself' cannot act as a subject; the subject form 'I' is needed.",
       "'Myself' is often used to sound modest, but it is ungrammatical here.")
    mc(PR, F, "L2", "Fill in the blank:\n\n'One should keep ___ promises.'",
       "one's", [("ones", "apostrophe missing; 'ones' is a plural noun"), ("their", "shift from 'one' to a plural pronoun"),
                 ("your", "shift from third to second person")],
       "The pronoun 'one' is followed by 'one's' in formal usage.", "one ... one's", "Keep the same pronoun throughout.")
    es(PR, F, "L2", ["The book which", "you gave me", "it is very useful."], 2,
       "The book which you gave me is very useful.",
       "No redundant pronoun after the subject",
       "'The book' is already the subject; 'it' repeats it unnecessarily.",
       "The relative clause in (A)-(B) is correct, so readers look there first.")

    es(PR, O, "L3", ["Everyone except", "him and she", "was present at the meeting."], 1,
       "Everyone except him and her was present at the meeting.",
       "Objective case after 'except'",
       "'Except' is a preposition here; both pronouns take the objective case: 'him and her'.",
       "'Him' is correct, so the case mismatch in the pair is overlooked.")
    es(PR, O, "L3", ["This is the same pen", "which I lost", "at the station yesterday."], 1,
       "This is the same pen that I lost at the station yesterday.",
       "'the same ... that' (exam convention)",
       "After 'the same', the relative pronoun 'that' is used in standard exam convention.",
       "'Which' is the usual relative for things, so the convention is easily missed.")
    es(PR, O, "L3", ["The committee were divided", "in its opinion", "about the proposal."], 1,
       "The committee were divided in their opinion about the proposal.",
       "Collective noun: pronoun must match the verb's number",
       "'Were divided' treats the committee as individuals, so the pronoun must be plural: 'their'.",
       "Both 'its' and 'were' can be right in isolation; the error is the inconsistency.")
    mc(PR, O, "L3", "Choose the grammatically correct sentence.",
       "Whom did the committee select for the post?",
       [("Who did the committee selected for the post?", "past form after auxiliary 'did'"),
        ("Whom did the committee selected for the post?", "past form after auxiliary 'did'"),
        ("Who the committee selected for the post?", "question lacks auxiliary inversion")],
       ["'Whom' is the object of 'select'.", "After 'did' the verb is the base form 'select'."],
       "Object of verb -> whom; did + V1", "Two options share the right pronoun but a wrong verb form.")
    es(PR, O, "L3", ["Let you and I", "discuss the matter", "before the meeting."], 0,
       "Let you and me discuss the matter before the meeting.",
       "'Let' takes the objective case",
       "Pronouns after 'let' are objects: 'let you and me'.",
       "Same trap as 'between you and I'.")
    es(PR, O, "L3", ["None of the two candidates", "was found suitable for", "the post of branch manager."], 0,
       "Neither of the two candidates was found suitable for the post of branch manager.",
       "neither (two) / none (more than two)",
       "With exactly two, use 'neither'; 'none' refers to three or more.",
       "'Was' is correct with both 'neither' and 'none', so (B) looks suspicious but is fine.")
    es(PR, O, "L3", ["He is one of those officers", "who has never", "taken a single day's leave."], 1,
       "He is one of those officers who have never taken a single day's leave.",
       "Relative pronoun agrees with its antecedent",
       "'Who' refers to 'officers' (plural), so the verb must be 'have'.",
       "The singular 'He' at the start misleads readers into 'has'.")
    mc(PR, O, "L3", "Fill in the blanks:\n\n'The company has announced ___ results, and the shareholders are pleased with ___.'",
       "its, them",
       [("their, it", "plural pronoun for 'has announced' company; singular for 'results'"),
        ("it's, them", "'it's' (it is) confused with possessive 'its'"),
        ("its, it", "singular pronoun for plural 'results'")],
       ["'The company has' -> singular 'its'.", "'Results' is plural -> 'them'."],
       "Pronoun number = antecedent number", "'It's' is a contraction, never a possessive.")
    es(PR, O, "L3", ["Every one of the applicants", "who have applied on time", "has been called for interview."], None,
       "Every one of the applicants who have applied on time has been called for interview.",
       "Relative clause agrees with its own antecedent",
       "'Who' refers to 'applicants' (plural) -> 'have applied'; the main subject 'every one' is singular -> 'has been called'.",
       "Seeing two different verb numbers suggests an error where there is none.")
    es(PR, O, "L3", ["I, you and he", "will share", "the responsibility."], 0,
       "You, he and I will share the responsibility.",
       "Order of pronouns: second, third, first (for shared positive actions)",
       "Courtesy order places 'I' last: 'You, he and I'.",
       "All three pronouns are in the correct case, so only order is wrong.")

    # ---------------- Segment-marked error identification ----------------
    es(SM, F, "L1", ["He do not", "know the answer", "to this question."], 0,
       "He does not know the answer to this question.",
       "Third-person singular takes 'does'",
       "'He' needs 'does not', not 'do not'.", "Common in fast reading.")
    es(SM, F, "L1", ["She has", "went to the market", "to buy vegetables."], 1,
       "She has gone to the market to buy vegetables.",
       "has + past participle",
       "After 'has', the past participle 'gone' is needed; 'went' is the simple past.",
       "'Went' and 'gone' are often confused.")
    es(SM, F, "L2", ["He gave me", "many good advices", "before the interview."], 1,
       "He gave me a lot of good advice (or: many pieces of good advice) before the interview.",
       "Uncountable nouns have no plural",
       "'Advice' is uncountable: no plural -s and no 'many'.",
       "In some languages the equivalent word is countable.")
    es(SM, F, "L2", ["The train", "left the station", "exactly on time."], None,
       "The train left the station exactly on time.",
       "on time (punctual)",
       "Subject, verb and the idiom 'on time' are all correct.",
       "'In time' vs 'on time' confusion may make (C) look wrong.")
    es(SM, F, "L2", ["If I was you,", "I would accept", "the offer immediately."], 0,
       "If I were you, I would accept the offer immediately.",
       "Subjunctive 'were' in unreal conditions",
       "For an imaginary situation, formal English uses 'were' with all subjects.",
       "'Was' is common in speech.")

    es(SM, O, "L3", ["Hardly anybody", "attended the meeting,", "didn't they?"], 2,
       "Hardly anybody attended the meeting, did they?",
       "Negative statement -> positive tag",
       "'Hardly' makes the statement negative, so the tag must be positive: 'did they?'.",
       "The sentence has no 'not', so the negative sense is missed.")
    es(SM, O, "L3", ["The number of applicants", "have increased", "sharply this year."], 1,
       "The number of applicants has increased sharply this year.",
       "'The number of' + singular verb; 'a number of' + plural verb",
       "The head noun is 'number', which is singular with 'the'.",
       "The nearby plural 'applicants' attracts a plural verb.")
    es(SM, O, "L3", ["I look forward", "to meet you", "at the conference next week."], 1,
       "I look forward to meeting you at the conference next week.",
       "look forward to + gerund",
       "'To' in 'look forward to' is a preposition, so it takes a gerund: 'meeting'.",
       "Readers mistake 'to' for an infinitive marker.")
    es(SM, O, "L3", ["He prevented me", "to enter", "the server room."], 1,
       "He prevented me from entering the server room.",
       "prevent + object + from + gerund",
       "'Prevent' is followed by 'from' + -ing, not a to-infinitive.",
       "The pattern of 'allow me to enter' is wrongly applied.")
    es(SM, O, "L3", ["Despite of the heavy rain,", "the rally", "went ahead exactly as planned."], 0,
       "Despite the heavy rain, the rally went ahead exactly as planned.",
       "despite / in spite of (never 'despite of')",
       "'Despite' takes no 'of'; 'in spite of' is the alternative.", "Mixing 'despite' and 'in spite of'.")
    es(SM, O, "L3", ["Seldom we see", "such dedication", "in young recruits."], 0,
       "Seldom do we see such dedication in young recruits.",
       "Negative adverb at the start -> inversion",
       "Fronted 'seldom' requires auxiliary-subject inversion: 'Seldom do we see'.",
       "Without inversion the sentence still sounds natural in speech.")
    stim = ("The passage below has four numbered sentences. Each sentence is split into parts (A), (B) and (C); (D) means 'No error'.\n\n"
            "1. (A) The branch has recently introduced | (B) a new token system which | (C) have reduced waiting time considerably.\n"
            "2. (A) Customers who earlier stood in queues | (B) for over an hour now | (C) finish their work within minutes.\n"
            "3. (A) The manager, along with | (B) two senior officers, are planning | (C) to extend the system to other branches.\n"
            "4. (A) If the pilot succeeds, | (B) the bank would roll it out | (C) across the state by March.")
    G = "ENB-G01"
    L4lead = "Which part of sentence {n} contains an error? (Choose (D) if there is none.)"
    es(SM, O, "L4", ["The branch has recently introduced", "a new token system which", "have reduced waiting time considerably."], 2,
       "The branch has recently introduced a new token system which has reduced waiting time considerably.",
       "Relative clause verb agrees with its antecedent",
       "'Which' refers to 'system' (singular), so the verb must be 'has reduced'.",
       "'Has recently introduced' in (A) is correct.", lead=L4lead.format(n=1), group=G, stim=stim)
    es(SM, O, "L4", ["Customers who earlier stood in queues", "for over an hour now", "finish their work within minutes."], None,
       "Customers who earlier stood in queues for over an hour now finish their work within minutes.",
       "Contrast of past habit (stood) with present habit (finish)",
       "The past tense 'stood' is marked by 'earlier', and the simple present 'finish' is marked by 'now'; both are correct.",
       "The shift of tense is deliberate, not an error.", lead=L4lead.format(n=2), group=G, stim=stim)
    es(SM, O, "L4", ["The manager, along with", "two senior officers, are planning", "to extend the system to other branches."], 1,
       "The manager, along with two senior officers, is planning to extend the system to other branches.",
       "'along with' does not make a subject plural",
       "The subject is 'the manager'; the phrase 'along with two senior officers' is parenthetical, so the verb is 'is planning'.",
       "The plural noun just before the verb attracts 'are'.", lead=L4lead.format(n=3), group=G, stim=stim)
    es(SM, O, "L4", ["If the pilot succeeds,", "the bank would roll it out", "across the state by March."], 1,
       "If the pilot succeeds, the bank will roll it out across the state by March.",
       "First conditional: if + present, will + V1",
       "A real future possibility ('succeeds') pairs with 'will', not 'would'.",
       "'Would' sounds polite and tentative, which masks the mismatch.", lead=L4lead.format(n=4), group=G, stim=stim)

    # ---------------- Subject-verb agreement ----------------
    es(SV, F, "L1", ["Each of the boys", "have been given", "a prize."], 1,
       "Each of the boys has been given a prize.",
       "each of + plural noun + singular verb",
       "The subject is 'each', which is singular.", "'Boys' next to the verb attracts a plural.")
    mc(SV, F, "L1", "Fill in the blank:\n\n'Mathematics ___ my favourite subject.'",
       "is", [("are", "subject names ending in -s are singular"), ("were", "plural and past"),
              ("have been", "plural auxiliary and wrong sense")],
       "Names of subjects like mathematics, physics and economics take singular verbs.",
       "Subject names in -ics = singular", "The -s ending is misleading.")
    es(SV, F, "L2", ["The quality of the mangoes", "were not up to", "the mark."], 1,
       "The quality of the mangoes was not up to the mark.",
       "Verb agrees with the head noun, not the noun in the of-phrase",
       "The head noun is 'quality' (singular).", "'Mangoes' just before the verb misleads.")
    es(SV, F, "L2", ["Bread and butter", "is his", "usual breakfast."], None,
       "Bread and butter is his usual breakfast.",
       "Two nouns forming one idea take a singular verb",
       "'Bread and butter' is a single dish, so 'is' is correct.",
       "The rule 'X and Y take a plural verb' is applied mechanically.")
    es(SV, F, "L2", ["The police", "has arrested", "the suspect."], 1,
       "The police have arrested the suspect.",
       "'Police' is always plural",
       "'Police' takes a plural verb: 'have arrested'.", "It looks like a singular collective noun.")

    es(SV, O, "L3", ["A large number of employees", "has opted", "for the new pension scheme."], 1,
       "A large number of employees have opted for the new pension scheme.",
       "'A number of' = many -> plural verb",
       "'A number of employees' means many employees, so the verb is plural.",
       "Confused with 'the number of', which is singular.")
    es(SV, O, "L3", ["The secretary and treasurer", "of the club", "have resigned."], 2,
       "The secretary and treasurer of the club has resigned.",
       "One article before two titles = one person",
       "With a single 'the', 'secretary and treasurer' is one person holding both posts, so the verb is singular.",
       "'X and Y' usually means plural; the single article reverses that.")
    es(SV, O, "L3", ["Ten kilometres", "are a long distance", "to walk in this heat."], 1,
       "Ten kilometres is a long distance to walk in this heat.",
       "Amounts of distance, time or money treated as one unit take a singular verb",
       "'Ten kilometres' is a single distance.", "The plural noun invites 'are'.")
    es(SV, O, "L3", ["The chief minister, as well as", "his cabinet colleagues,", "was present at the ceremony."], None,
       "The chief minister, as well as his cabinet colleagues, was present at the ceremony.",
       "'as well as' does not change the number of the subject",
       "The subject is 'the chief minister', so 'was' is correct.",
       "The plural 'colleagues' tempts candidates to mark (C).")
    es(SV, O, "L3", ["One of the most important reasons", "for the delays", "are the shortage of staff."], 2,
       "One of the most important reasons for the delays is the shortage of staff.",
       "'One of + plural noun' takes a singular verb",
       "The subject is 'one', so the verb is 'is'.", "Two plural nouns before the verb.")
    es(SV, O, "L3", ["The news of the proposed merger", "between the two private banks", "were leaked before the announcement."], 2,
       "The news of the proposed merger between the two private banks was leaked before the announcement.",
       "'News' is singular",
       "'News' takes a singular verb despite its -s ending.", "Looks plural.")
    mc(SV, O, "L3", "Choose the sentence with correct subject-verb agreement.",
       "The majority of the members were against the proposal.",
       [("Many a member were against the proposal.", "'many a' takes a singular verb"),
        ("Neither of the members were against the proposal.", "'neither of' takes a singular verb"),
        ("Each of the members were against the proposal.", "'each of' takes a singular verb")],
       ["'The majority of' + plural noun takes a plural verb.", "'Many a', 'neither of', 'each of' take singular verbs."],
       "majority of + plural noun -> plural verb", "'Many a' looks plural in meaning but is singular in grammar.")
    es(SV, O, "L3", ["Not only the manager", "but also the clerks", "was found guilty."], 2,
       "Not only the manager but also the clerks were found guilty.",
       "not only ... but also: verb agrees with the nearer subject",
       "The nearer subject is 'the clerks', so the verb is 'were'.", "The first subject is singular.")
    es(SV, O, "L3", ["The statistics", "you quoted in your report", "is misleading."], 2,
       "The statistics you quoted in your report are misleading.",
       "'Statistics' = figures (plural); = the subject (singular)",
       "Here 'statistics' means particular figures, so it is plural.",
       "'Statistics is my subject' is also correct, which causes confusion.")
    es(SV, O, "L3", ["Twenty years", "is a long time", "to wait for justice."], None,
       "Twenty years is a long time to wait for justice.",
       "A period of time treated as one unit takes a singular verb",
       "'Twenty years' is a single span of time, so 'is' is correct.",
       "The plural 'years' tempts candidates to mark (B).")

    # ---------------- Tense and sequence of tenses ----------------
    es(TS, F, "L1", ["She is knowing", "the answer", "but will not tell us."], 0,
       "She knows the answer but will not tell us.",
       "Stative verbs are not used in the continuous",
       "'Know' is a stative verb; use the simple present 'knows'.", "Continuous forms feel more vivid.")
    mc(TS, F, "L1", "Fill in the blank:\n\n'By next March, he ___ in this bank for ten years.'",
       "will have worked", [("will work", "future simple ignores completion by a deadline"),
                            ("has worked", "present perfect does not reach into the future"),
                            ("worked", "simple past cannot refer to next March")],
       "'By + future time' with a duration takes the future perfect.", "By + future point -> will have + V3",
       "'By next March' is the signal.")
    es(TS, F, "L2", ["When I reached the station,", "the train already left", "the platform."], 1,
       "When I reached the station, the train had already left the platform.",
       "Earlier of two past actions -> past perfect",
       "The train left before I reached, so it needs the past perfect 'had already left'.",
       "'Already' signals a completed earlier action.")
    mc(TS, F, "L2", "Fill in the blank:\n\n'It is high time we ___ the report.'",
       "submitted", [("submit", "present form after 'it is high time'"), ("have submitted", "perfect form not used here"),
                     ("will submit", "future form not used here")],
       "'It is (high) time + subject' is followed by the past subjunctive.", "It is high time + S + V2",
       "The past form refers to the present or future.")
    es(TS, F, "L2", ["He will call you", "as soon as he", "will reach home."], 2,
       "He will call you as soon as he reaches home.",
       "No 'will' in time clauses",
       "After time conjunctions (as soon as, when, before), the simple present expresses the future.",
       "The main clause 'will call' makes 'will reach' look consistent.")

    es(TS, O, "L3", ["She told me yesterday evening", "that she has finished", "the assignment on time."], 1,
       "She told me yesterday evening that she had finished the assignment on time.",
       "Sequence of tenses after a past main verb",
       "The main verb 'told' is past, so the subordinate clause shifts to the past perfect 'had finished'.",
       "Present perfect sounds natural in conversation.")
    es(TS, O, "L3", ["I wish", "I had attended", "the seminar last week."], None,
       "I wish I had attended the seminar last week.",
       "wish + past perfect for regret about the past",
       "The seminar is in the past, so 'had attended' correctly expresses regret.",
       "Candidates expect 'attended' or 'would attend'.")
    es(TS, O, "L3", ["By the time the auditors arrived,", "the accountant", "has destroyed the records."], 2,
       "By the time the auditors arrived, the accountant had destroyed the records.",
       "By the time + past -> past perfect",
       "The destruction happened before the auditors arrived (past), so 'had destroyed'.",
       "Mixing present perfect with a past time frame.")
    mc(TS, O, "L3", "Fill in the blank:\n\n'If he ___ harder, he would have passed.'",
       "had worked", [("would have worked", "'would have' used in the if-clause"), ("worked", "second-conditional form"),
                      ("has worked", "present perfect in an unreal past condition")],
       "Third conditional: If + past perfect, would have + V3.", "If + had V3, would have V3",
       "'Would' never appears in the if-clause.")
    es(TS, O, "L3", ["He said that", "he will join", "the office the next day."], 1,
       "He said that he would join the office the next day.",
       "will -> would after a past reporting verb",
       "'Said' is past, and 'the next day' confirms reported speech, so 'would join'.",
       "'The next day' is correctly converted, which draws attention away from (B).")
    es(TS, O, "L3", ["Scarcely had he", "finished his long speech to the staff", "when the lights go out."], 2,
       "Scarcely had he finished his long speech to the staff when the lights went out.",
       "Scarcely had + V3 ... when + past simple",
       "The second action in a 'scarcely ... when' sentence is in the simple past.",
       "The correlative is right; the tense is not.")
    mc(TS, O, "L3", "Choose the correct sentence.",
       "I have been waiting for the result since morning.",
       [("I am waiting for the result since this morning.", "present continuous with 'since'"),
        ("I waited for the result since morning.", "simple past with 'since'"),
        ("I have waited for the result from morning.", "'from' instead of 'since' with a perfect tense")],
       ["An action begun in the past and still continuing, with 'since', takes the present perfect continuous."],
       "have been + V-ing + since/for", "'Since' is the signal for a perfect tense.")
    es(TS, O, "L3", ["Ever since he", "joined the firm as a trainee,", "he worked tirelessly."], 2,
       "Ever since he joined the firm as a trainee, he has worked tirelessly.",
       "ever since + past simple, main clause present perfect",
       "The work continues from joining up to now, so the main clause needs 'has worked'.",
       "(A) and (B) are correct past-tense forms.")
    mc(TS, O, "L3", "Fill in the blanks:\n\n'She ___ for two hours when the power ___.'",
       "had been studying, failed",
       [("was studying, had failed", "sequence reversed"), ("has been studying, failed", "present perfect in a past narrative"),
        ("had studied, was failing", "continuous for a sudden event")],
       ["The studying lasted up to a past moment -> past perfect continuous.", "The power failure is a single past event -> simple past."],
       "had been V-ing (duration up to past point) + V2 (event)", "Duration + interruption pattern.")
    es(TS, O, "L3", ["The earth", "moved round the sun,", "the teacher explained."], 1,
       "The earth moves round the sun, the teacher explained.",
       "Universal truths stay in the present",
       "A permanent truth is expressed in the simple present even after a past verb.",
       "Backshifting is wrongly applied.")
