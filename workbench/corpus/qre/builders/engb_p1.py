"""ENG-B part 1: active/passive voice, correlatives & parallelism, narration, prepositions & articles."""

AP = "eng-active-and-passive-voice-e6437f9d"
CP = "eng-correlative-conjunctions-and-parallelism-ff6bd046"
DI = "eng-direct-and-indirect-narration-1d250c23"
PA = "eng-preposition-and-article-errors-000b76d8"


def add_all(B, H):
    mc, es = H["mc"], H["es"]
    F, O = "foundation", "officer"
    PV = "Choose the correct passive form of the sentence:"
    AV = "Choose the correct active form of the sentence:"

    # ---------------- Active and passive voice ----------------
    mc(AP, F, "L1", PV + "\n\n'The clerk types the letters.'",
       "The letters are typed by the clerk.",
       [("The letters were typed by the clerk.", "tense shifted from present to past"),
        ("The letters are being typed by the clerk.", "simple present turned into continuous"),
        ("The letters have been typed by the clerk.", "simple present turned into present perfect")],
       ["Simple present active (types) -> is/are + past participle.",
        "Object 'the letters' (plural) becomes subject: 'are typed'."],
       "Passive = be (in the tense of the active verb) + past participle",
       "Keep the tense of the original verb unchanged.")
    mc(AP, F, "L1", PV + "\n\n'They are painting the gate.'",
       "The gate is being painted by them.",
       [("The gate is painted by them.", "continuous aspect dropped"),
        ("The gate was being painted by them.", "tense shifted to past"),
        ("The gate has been painted by them.", "continuous turned into perfect")],
       ["Present continuous active -> is/am/are + being + past participle.",
        "'The gate' is singular: 'is being painted'."],
       "Present continuous passive = is/are + being + V3",
       "'being' is essential to retain the continuous sense.")
    mc(AP, F, "L2", PV + "\n\n'Who wrote this report?'",
       "By whom was this report written?",
       [("Who was this report written?", "'by' omitted before the agent"),
        ("By whom this report was written?", "statement word order used in a question"),
        ("By whom is this report written?", "tense changed from past to present")],
       ["'Who' as subject becomes 'By whom' in the passive.",
        "Past simple -> was + past participle, with question order: 'was this report written'."],
       "Who + V (active) -> By whom + aux + subject + V3 (passive)",
       "Interrogative passives keep auxiliary-before-subject order.")
    es(AP, F, "L2", ["The new bridge", "was inaugurate by", "the Chief Minister last week."], 1,
       "The new bridge was inaugurated by the Chief Minister last week.",
       "Passive = be + past participle",
       "After 'was' in a passive, the main verb must be the past participle 'inaugurated', not the base form.",
       "Readers often skim past a missing -d ending.")
    mc(AP, F, "L2", PV + "\n\n'Close the window.'",
       "Let the window be closed.",
       [("The window is closed.", "command turned into a statement"),
        ("Let the window is closed.", "finite 'is' used after 'let' instead of 'be'"),
        ("The window should close.", "intransitive active; not a passive of the command")],
       ["Imperative passive pattern: Let + object + be + past participle.",
        "'Close the window' -> 'Let the window be closed.'"],
       "Imperative -> Let + object + be + V3",
       "After 'let' the verb is the bare infinitive 'be', never 'is'.")

    es(AP, O, "L2", ["The proposal has been discussed at length,", "but no decision has taken", "so far by the board."], 1,
       "The proposal has been discussed at length, but no decision has been taken so far by the board.",
       "Passive present perfect = has/have + been + V3",
       "A decision does not 'take' anything; the subject receives the action, so the passive 'has been taken' is required.",
       "Part (A) is a correct passive and draws attention away from (B).")
    mc(AP, O, "L3", PV + "\n\n'People believe that the fort was built in the twelfth century.'",
       "The fort is believed to have been built in the twelfth century.",
       [("The fort is believed to be built in the twelfth century.", "simple infinitive loses the earlier (past) time of building"),
        ("The fort was believed to have been built in the twelfth century.", "tense of 'believe' shifted to past"),
        ("The fort is believed that it was built in the twelfth century.", "double subject: 'fort' and 'it'")],
       ["Reporting verb 'believe' is present -> 'is believed'.",
        "The building happened earlier than the believing -> perfect infinitive 'to have been built'."],
       "Subject + is believed + to have been V3 (earlier action)",
       "Use the perfect infinitive when the reported action precedes the reporting verb.")
    es(AP, O, "L3", ["The complaint of the depositors", "was being looked by the vigilance cell", "when the manager was transferred."], 1,
       "The complaint of the depositors was being looked into by the vigilance cell when the manager was transferred.",
       "Prepositional verbs keep their particle in the passive",
       "'Look into' (investigate) is a prepositional verb; in the passive the preposition stays: 'was being looked into by'.",
       "The continuous passive 'was being' is correct and may distract from the missing 'into'.")
    mc(AP, O, "L3", AV + "\n\n'The staff were made to work on Sunday by the manager.'",
       "The manager made the staff work on Sunday.",
       [("The manager made the staff to work on Sunday.", "'to' retained after active 'make'"),
        ("The manager was making the staff work on Sunday.", "tense changed to past continuous"),
        ("The manager had made the staff work on Sunday.", "tense changed to past perfect")],
       ["Passive 'were made to work' comes from active 'made ... work'.",
        "In the active, 'make' takes the bare infinitive (no 'to')."],
       "Active: make + object + bare infinitive; Passive: be made + to-infinitive",
       "The 'to' appears only in the passive form.")
    es(AP, O, "L3", ["Ticket prices have been risen", "twice this year", "owing to higher fuel costs."], 0,
       "Ticket prices have risen (or: have been raised) twice this year owing to higher fuel costs.",
       "Intransitive verbs have no passive",
       "'Rise' is intransitive and cannot be passive; use 'have risen', or the transitive 'raise' in the passive: 'have been raised'.",
       "'Risen' looks like a valid past participle, which hides the voice error.")
    mc(AP, O, "L2", PV + "\n\n'The bank granted him a loan.' (use the person as subject)",
       "He was granted a loan by the bank.",
       [("He was granted with a loan by the bank.", "superfluous 'with' added"),
        ("He is granted a loan by the bank.", "tense shifted to present"),
        ("He was being granted a loan by the bank.", "simple past turned into continuous")],
       ["With two objects, the indirect object (him) can become the subject: 'He'.",
        "Past simple -> was + granted; the direct object 'a loan' stays."],
       "S + V + IO + DO -> IO(subject) + was + V3 + DO + by agent",
       "No preposition is needed before the retained object.")
    mc(AP, O, "L3", PV + "\n\n'Someone must have left the vault open.'",
       "The vault must have been left open.",
       [("The vault must be left open.", "perfect aspect lost; becomes a present obligation"),
        ("The vault must had been left open.", "'had' used after a modal"),
        ("The vault must have been leaving open.", "active continuous form, not passive")],
       ["Modal perfect active 'must have left' -> passive 'must have been left'.",
        "Agent 'someone' is dropped as it is indefinite."],
       "Modal + have + been + V3",
       "A modal is always followed by the base form ('have'), never 'had'.")
    es(AP, O, "L2", ["The applications received after the deadline", "will not be considered", "under any circumstances."], None,
       "The applications received after the deadline will not be considered under any circumstances.",
       "Future passive = will be + V3",
       "'Received' is a correct reduced passive participle and 'will not be considered' is a correct future passive; 'under any circumstances' correctly follows a negative.",
       "Candidates wrongly expect 'under no circumstances' after 'not', which would create a double negative.")
    mc(AP, O, "L3", PV + "\n\n'Do not insult the weak.'",
       "Let the weak not be insulted.",
       [("The weak should not insult.", "meaning reversed; the weak become the doers"),
        ("Let not the weak insulted.", "'be' omitted before the participle"),
        ("The weak are not insulted.", "command turned into a statement of fact")],
       ["Negative imperative passive: Let + object + not + be + V3 (or Let not + object + be + V3).",
        "'Do not insult the weak' -> 'Let the weak not be insulted.'"],
       "Negative imperative -> Let + object + not be + V3",
       "The passive of a command must remain a command.")
    mc(AP, O, "L3", "In which sentence is the passive voice used incorrectly?",
       "The thief was escaped from the police van.",
       [("The minutes were circulated to all members.", "correct passive of transitive 'circulate'"),
        ("The road is being widened by the municipality.", "correct present continuous passive"),
        ("The parcel has been delivered to the wrong address.", "correct present perfect passive")],
       ["'Escape' (in the sense of getting away) is intransitive here and cannot be passivised.",
        "Correct: 'The thief escaped from the police van.'"],
       "Only transitive verbs form passives",
       "A sentence can look formal and still misuse the passive.")

    # ---------------- Correlatives and parallelism ----------------
    es(CP, F, "L1", ["Not only she sings", "but also dances", "beautifully."], 0,
       "She not only sings but also dances beautifully. (or: Not only does she sing but she also dances beautifully.)",
       "Not only ... but also: parallel placement; fronted 'not only' needs inversion",
       "When 'not only' opens the clause it needs inversion ('Not only does she sing'); otherwise place it before the verb: 'She not only sings'.",
       "Part (B) looks incomplete but is correct once (A) is fixed.")
    mc(CP, F, "L1", "Fill in the blank:\n\n'He is neither intelligent ___ hardworking.'",
       "nor", [("or", "'neither' pairs with 'nor', not 'or'"), ("but", "contrast connector, not a correlative pair"),
               ("and", "additive connector; breaks the neither-nor pair")],
       "Neither is always paired with nor.", "Neither ... nor", "'Either ... or' and 'neither ... nor' must not be mixed.")
    es(CP, F, "L2", ["The job requires", "typing, filing and", "to answer the phone."], 2,
       "The job requires typing, filing and answering the phone.",
       "Items in a series take the same grammatical form",
       "'Typing' and 'filing' are gerunds, so the third item must also be a gerund: 'answering'.",
       "The infinitive 'to answer' is grammatical on its own; the error is the broken parallelism.")
    mc(CP, F, "L2", "Fill in the blank:\n\n'Hardly had we reached the station ___ the train left.'",
       "when", [("than", "'than' pairs with 'no sooner', not 'hardly'"), ("then", "adverb of time, not a correlative"),
                ("that", "not used with 'hardly'")],
       "Hardly/Scarcely ... when; No sooner ... than.", "Hardly ... when", "Do not import 'than' from 'no sooner ... than'.")
    es(CP, F, "L2", ["No sooner did the bell ring", "when the students", "rushed out of the class."], 1,
       "No sooner did the bell ring than the students rushed out of the class.",
       "No sooner ... than",
       "'No sooner' is always followed by 'than', not 'when'.",
       "Part (A) uses correct inversion, so the error is missed if one checks only word order.")

    es(CP, O, "L3", ["She is not only known", "for her honesty", "but also for her tact."], 0,
       "She is known not only for her honesty but also for her tact.",
       "Correlatives must stand immediately before parallel elements",
       "'But also' precedes a prepositional phrase ('for her tact'), so 'not only' must also precede one: 'known not only for her honesty'.",
       "Every word is correct; only the position of 'not only' is faulty.")
    es(CP, O, "L3", ["The committee must decide", "whether to raise the fee", "or keeping it unchanged."], 2,
       "The committee must decide whether to raise the fee or to keep it unchanged.",
       "Whether ... or: both limbs in the same form",
       "'Whether to raise' is an infinitive, so the second limb must be 'or (to) keep', not the gerund 'keeping'.",
       "'Keeping it unchanged' is a natural phrase in isolation.")
    mc(CP, O, "L2", "Which sentence is grammatically parallel?",
       "The trainee was told to check the vouchers, update the ledger and file the returns.",
       [("The trainee was told to check the vouchers, updating the ledger and file the returns.", "gerund inserted in an infinitive series"),
        ("The trainee was told to check the vouchers, update the ledger and filing the returns.", "last item switched to a gerund"),
        ("The trainee was told checking the vouchers, to update the ledger and file the returns.", "first item not an infinitive")],
       ["All three tasks depend on 'to': check, update, file (bare infinitives after a single 'to')."],
       "Series after one 'to': to V1, V2 and V3",
       "All options share vocabulary; only verb forms differ.")
    es(CP, O, "L3", ["Both the manager as well as", "the cashier", "were questioned by the auditors."], 0,
       "Both the manager and the cashier were questioned by the auditors.",
       "Both ... and (never 'both ... as well as')",
       "'Both' pairs only with 'and'; 'as well as' cannot complete it.",
       "Part (C) has a plural verb, which is correct once 'both ... and' is used.")
    es(CP, O, "L3", ["Scarcely had the auditors from Mumbai", "left the branch", "than the error was discovered."], 2,
       "Scarcely had the auditors from Mumbai left the branch when the error was discovered.",
       "Scarcely ... when",
       "'Scarcely' (like 'hardly') is followed by 'when', not 'than'.",
       "Correct inversion in (A) makes the sentence look well-formed.")
    mc(CP, O, "L3", ("Choose the alternative that best replaces the part in bold:\n\n"
                                 "'He would rather resign **than to accept** the transfer.'"),
       "than accept",
       [("than accepting", "gerund does not match bare infinitive 'resign'"),
        ("then accept", "'then' confused with 'than'"),
        ("but to accept", "wrong connector and form")],
       ["'Would rather' takes a bare infinitive (resign); the item after 'than' must match: 'than accept'."],
       "would rather + V1 + than + V1", "Parallelism across 'than' is tested.")
    es(CP, O, "L3", ["The climate of Shimla", "is cooler than", "Chennai."], 2,
       "The climate of Shimla is cooler than that of Chennai.",
       "Compare like with like",
       "The climate of one city must be compared with the climate of another: 'than that of Chennai'.",
       "The comparative 'cooler than' in (B) is correct.")
    es(CP, O, "L3", ["Neither the files nor the register", "was found", "in the almirah."], None,
       "Neither the files nor the register was found in the almirah.",
       "Neither ... nor: verb agrees with the nearer subject",
       "The nearer subject is 'the register' (singular), so 'was found' is correct.",
       "Seeing 'files' first tempts candidates to demand 'were'.")
    es(CP, O, "L3", ["The audit found", "that the branch neither maintained", "the cash book nor the stock register properly."], 1,
       "The audit found that the branch maintained neither the cash book nor the stock register properly.",
       "Correlatives placed before parallel elements",
       "'Nor' precedes a noun phrase (the stock register), so 'neither' must precede the parallel noun phrase 'the cash book', i.e. after 'maintained'.",
       "Misplaced correlatives read smoothly in speech.")
    mc(CP, O, "L3", "Choose the correctly constructed sentence.",
       "It is not so much the cost as the delay that worries the client.",
       [("It is not so much the cost but the delay that worries the client.", "'not so much' paired with 'but'"),
        ("It is not so much the cost than the delay that worries the client.", "'not so much' paired with 'than'"),
        ("It is not as much the cost but the delay that worries the client.", "'as much' left without its 'as'")],
       ["The fixed pair is 'not so much ... as'."],
       "not so much X as Y", "'But' and 'than' sound natural but break the correlative.")

    # ---------------- Direct and indirect narration ----------------
    NAR = "Choose the correct indirect (reported) form:"
    mc(DI, F, "L1", NAR + "\n\nHe said, \"I am tired.\"",
       "He said that he was tired.",
       [("He said that I was tired.", "first-person pronoun not changed"),
        ("He said that he is tired.", "present tense not backshifted"),
        ("He told that he was tired.", "'told' used without an object")],
       ["Past reporting verb -> backshift: am -> was.", "'I' -> 'he' (refers to the speaker)."],
       "said (past) -> present becomes past; pronouns follow the speaker", "'Tell' needs an object: told me/him.")
    mc(DI, F, "L1", NAR + "\n\nShe said to me, \"Where do you live?\"",
       "She asked me where I lived.",
       [("She asked me where did I live.", "question word order retained"),
        ("She asked me that where I lived.", "'that' used with a wh-question"),
        ("She said to me where I lived.", "reporting verb not changed to 'asked'")],
       ["Question -> 'asked'; wh-word acts as the link.", "Statement order: 'where I lived' (do -> past, no inversion)."],
       "said to + question -> asked + wh-word + S + V (backshifted)", "No 'that' and no auxiliary 'did' in reported questions.")
    mc(DI, F, "L2", NAR + "\n\nThe teacher said, \"The earth revolves around the sun.\"",
       "The teacher said that the earth revolves around the sun.",
       [("The teacher said that the earth revolved around the sun.", "universal truth wrongly backshifted"),
        ("The teacher said that the earth had revolved around the sun.", "past perfect for a permanent truth"),
        ("The teacher told that the earth revolves around the sun.", "'told' without an object")],
       ["Universal truths keep the present tense even after a past reporting verb."],
       "Universal truth: no backshift", "Automatic backshifting is the trap.")
    mc(DI, F, "L2", NAR + "\n\nHe said to them, \"Please wait here.\"",
       "He requested them to wait there.",
       [("He requested them to wait here.", "'here' not changed to 'there'"),
        ("He ordered them to please wait there.", "'please' retained and verb implies command"),
        ("He said them to wait there.", "'said' used with an object and infinitive")],
       ["'Please' signals a request -> 'requested' + to-infinitive; 'please' is dropped.", "'here' -> 'there'."],
       "Imperative request -> requested + object + to + V1", "Remove 'please' once 'requested' carries the politeness.")
    es(DI, F, "L2", ["She asked me", "what was my name", "and where I came from."], 1,
       "She asked me what my name was and where I came from.",
       "Reported questions use statement order",
       "In an indirect question the subject comes before the verb: 'what my name was'.",
       "Part (C) is already in correct statement order, which highlights the error in (B).")

    mc(DI, O, "L3", NAR + "\n\nHe said, \"I met her yesterday.\"",
       "He said that he had met her the previous day.",
       [("He said that he met her yesterday.", "no tense or time-word change"),
        ("He said that he had met her the next day.", "'yesterday' converted as if it were 'tomorrow'"),
        ("He said that he has met her the previous day.", "present perfect with a past time phrase")],
       ["Past simple -> past perfect (met -> had met).", "'yesterday' -> 'the previous day' / 'the day before'."],
       "Past -> past perfect; yesterday -> the previous day", "Time adverbs change along with tense.")
    mc(DI, O, "L3", NAR + "\n\n\"Let's take a break,\" said Ravi.",
       "Ravi suggested that they should take a break.",
       [("Ravi suggested to them to take a break together.", "'suggest' used with object + infinitive"),
        ("Ravi said let them take a break.", "imperative form carried into reported speech"),
        ("Ravi ordered that they must take a break at once.", "suggestion reported as an order")],
       ["'Let's' expresses a proposal -> 'suggested/proposed that + they should + V1'."],
       "Let's -> suggested that ... should", "'Suggest' never takes object + to-infinitive.")
    mc(DI, O, "L3", NAR + "\n\nShe said, \"How beautiful the valley is!\"",
       "She exclaimed that the valley was very beautiful.",
       [("She exclaimed that how beautiful the valley was.", "exclamatory 'how' retained after 'that'"),
        ("She said that how beautiful the valley is.", "'how' retained and no backshift"),
        ("She exclaimed that the valley is very beautiful.", "present tense not backshifted")],
       ["Exclamation -> 'exclaimed that'; 'How beautiful' -> 'very beautiful'.", "is -> was."],
       "Exclamatory: exclaimed that + S + V (backshifted) with 'very'", "Exclamatory words do not survive into reported speech.")
    es(DI, O, "L3", ["He asked me", "that whether I would", "join the new project."], 1,
       "He asked me whether I would join the new project.",
       "Yes/no questions reported with if/whether (no 'that')",
       "'That' cannot introduce a reported question; 'whether' alone is the link.",
       "'Would' is a correctly backshifted 'will', drawing attention to (C).")
    mc(DI, O, "L3", NAR + "\n\nHe said to me, \"Did you see the match last night?\"",
       "He asked me if I had seen the match the previous night.",
       [("He asked me if I saw the match last night.", "no backshift and time phrase unchanged"),
        ("He asked me did I see the match the previous night.", "question form retained"),
        ("He asked me if I had seen the match that night.", "'last night' converted to 'that night', changing meaning")],
       ["Yes/no question -> 'asked if/whether'.", "Past simple -> past perfect; 'last night' -> 'the previous night'."],
       "Did + V1 -> if + had + V3", "'That night' refers to the night of speaking, not the night before.")
    mc(DI, O, "L3", "Choose the correct direct form:\n\nThe clerk told the visitor that he could not meet the manager that day.",
       "The clerk said to the visitor, \"You cannot meet the manager today.\"",
       [("The clerk said to the visitor, \"He cannot meet the manager today.\"", "pronoun for the listener not restored to 'you'"),
        ("The clerk said to the visitor, \"You could not meet the manager that day.\"", "tense and time word not restored"),
        ("The clerk said to the visitor, \"You cannot meet the manager that day.\"", "'that day' not restored to 'today'")],
       ["'He' refers to the visitor (the listener) -> 'you'.", "could -> can; that day -> today."],
       "Reverse the backshift and the pronoun/time changes", "All three changes must be reversed together.")
    mc(DI, O, "L3", NAR + "\n\nShe said, \"I may go to Pune next week.\"",
       "She said that she might go to Pune the following week.",
       [("She said that she may go to Pune the following week.", "modal 'may' not changed to 'might'"),
        ("She said that she might have gone to Pune the following week.", "perfect infinitive alters the meaning"),
        ("She said that she might go to Pune the previous week.", "'next week' converted to 'the previous week'")],
       ["may -> might after a past reporting verb.", "'next week' -> 'the following week'."],
       "may -> might; next week -> the following week", "Direction of time words must be preserved.")
    es(DI, O, "L3", ["My friend said on the phone", "that he has been waiting", "for over an hour at the gate."], 1,
       "My friend said on the phone that he had been waiting for over an hour at the gate.",
       "Backshift: present perfect continuous -> past perfect continuous",
       "After the past reporting verb 'said', 'has been waiting' must become 'had been waiting'.",
       "The sentence sounds natural in speech, which hides the sequence-of-tense error.")
    mc(DI, O, "L3", NAR + "\n\nHe said, \"Alas! I have lost my wallet.\"",
       "He exclaimed with sorrow that he had lost his wallet.",
       [("He exclaimed alas that he had lost his wallet.", "interjection retained"),
        ("He exclaimed with sorrow that he has lost his wallet.", "present perfect not backshifted"),
        ("He exclaimed with joy that he had lost his wallet.", "emotion misread")],
       ["'Alas' conveys sorrow -> 'exclaimed with sorrow'.", "have lost -> had lost; my -> his."],
       "Interjection -> 'exclaimed with sorrow/joy' + that-clause", "The interjection is replaced, not copied.")
    mc(DI, O, "L3", NAR + "\n\nThe officer said to the peon, \"Don't open the door until I return.\"",
       "The officer told the peon not to open the door until he returned.",
       [("The officer told the peon that don't open the door until he returned.", "imperative retained after 'that'"),
        ("The officer told the peon not to open the door until he returns.", "verb in the time clause not backshifted"),
        ("The officer requested the peon not to open the door until I returned.", "first-person pronoun not changed")],
       ["Negative command -> told/ordered + object + not to + V1.", "'I return' -> 'he returned'."],
       "Don't + V1 -> not to + V1", "Every clause, including 'until ...', is backshifted.")

    # ---------------- Prepositions and articles ----------------
    es(PA, F, "L1", ["He has been working", "in this office", "since five years."], 2,
       "He has been working in this office for five years.",
       "for + period; since + point of time",
       "'Five years' is a period of time, so 'for' is required; 'since' takes a starting point (since 2020).",
       "Part (A) correctly uses the perfect continuous, which goes with both.")
    mc(PA, F, "L1", "Fill in the blank:\n\n'She is ___ honest officer.'",
       "an", [("a", "'honest' begins with a vowel sound (silent h)"), ("the", "no specific officer is identified"),
              ("no article", "singular countable noun needs an article")],
       "'Honest' is pronounced with a vowel sound /ɒ/, so 'an' is used.", "an + vowel sound", "The article depends on sound, not spelling.")
    es(PA, F, "L1", ["She is a university lecturer", "who is also known as", "an European art historian."], 2,
       "She is a university lecturer who is also known as a European art historian.",
       "a + consonant sound",
       "'European' begins with the sound /j/ (a consonant sound), so it takes 'a'.",
       "'A university' in (A) follows the same rule and is correct.")
    mc(PA, F, "L2", "Fill in the blank:\n\n'The meeting was postponed ___ lack of quorum.'",
       "for", [("by", "'by' does not express cause here"), ("with", "not idiomatic for cause"),
               ("from", "'from lack of' does not follow 'postponed'")],
       "'For lack of' is the fixed phrase meaning 'because there was not enough'.", "for lack of", "Fixed phrases take fixed prepositions.")
    es(PA, F, "L2", ["He is senior", "than me", "by two years."], 1,
       "He is senior to me by two years.",
       "senior/junior/superior/inferior + to",
       "Latin comparatives such as 'senior' take 'to', not 'than'.",
       "'By two years' in (C) is correct.")

    es(PA, O, "L3", ["The committee comprises of", "five members drawn", "from different departments."], 0,
       "The committee comprises five members drawn from different departments.",
       "comprise (no 'of'); consist of / be composed of",
       "'Comprise' is transitive and takes no preposition; 'consists of' or 'is comprised of' are the alternatives.",
       "'Consists of' is correct, so 'comprises of' sounds acceptable by analogy.")
    es(PA, O, "L3", ["Unless you apply", "for the post before", "the last date, you will not be considered."], None,
       "Unless you apply for the post before the last date, you will not be considered.",
       "apply for (a post); unless = if not",
       "'Apply for the post' is idiomatic, 'unless' is not followed by another negative, and the main clause correctly uses the future.",
       "Candidates who expect every sentence to contain an error pick (B).")
    es(PA, O, "L3", ["The ministry has", "laid emphasis over", "the need for fiscal prudence."], 1,
       "The ministry has laid emphasis on the need for fiscal prudence.",
       "emphasis on / lay stress on",
       "The noun 'emphasis' takes 'on' (or 'upon').",
       "'The need for' in (C) is correct and may be wrongly suspected.")
    mc(PA, O, "L3", "Fill in the blanks:\n\n'He was accused ___ fraud and was later acquitted ___ all charges.'",
       "of, of",
       [("for, from", "both prepositions wrong"), ("with, of", "'accused with' is not idiomatic"),
        ("of, from", "'acquitted from' is not idiomatic")],
       ["accuse someone of something; acquit someone of a charge."],
       "accused of; acquitted of", "Opposites can share the same preposition.")
    es(PA, O, "L3", ["The Taj Mahal in Agra attracts", "a large number of tourists", "from the all parts of the world."], 2,
       "The Taj Mahal in Agra attracts a large number of tourists from all parts of the world.",
       "Article position: 'all' precedes 'the' (all the parts) or stands alone",
       "'The' cannot come before 'all'; write 'from all parts of the world'.",
       "'The Taj Mahal' correctly takes the definite article.")
    es(PA, O, "L3", ["The honesty is", "rarer than talent", "in public life today."], 0,
       "Honesty is rarer than talent in public life today.",
       "No article before abstract nouns used in a general sense",
       "'Honesty' here is a general quality, so it takes no article (just like 'talent' in (B)).",
       "'Talent' without an article in (B) is the clue that (A) is inconsistent.")
    mc(PA, O, "L3", "Choose the correct sentence.",
       "She has been absent from office since Monday.",
       [("She has been absent in office since Monday.", "'absent in' is not idiomatic"),
        ("She has been absent from office from Monday.", "'from Monday' with a perfect tense"),
        ("She has been absent at office since Monday.", "'absent at' is not idiomatic")],
       ["'Absent from' is fixed; a perfect tense with a starting point takes 'since'."],
       "absent from; perfect tense + since", "Two prepositions are tested at once.")
    es(PA, O, "L3", ["The chairman,", "along with his colleagues,", "insisted for a fresh audit."], 2,
       "The chairman, along with his colleagues, insisted on a fresh audit.",
       "insist on",
       "'Insist' takes 'on' (or 'upon'), never 'for'.",
       "'Along with' in (B) raises a subject-verb doubt that is not the issue here ('insisted' has no number).")
    es(PA, O, "L3", ["He was the first Indian mountaineer", "who managed to", "reach at the summit without oxygen."], 2,
       "He was the first Indian mountaineer who managed to reach the summit without oxygen.",
       "reach (transitive, no preposition); arrive at",
       "'Reach' takes a direct object; 'at' is used with 'arrive', not 'reach'.",
       "'The first Indian' correctly takes 'the' with an ordinal.")
    mc(PA, O, "L3", "Fill in the blanks:\n\n'The report is ___ useful document, but ___ data in its annexure is outdated.'",
       "a, the",
       [("an, the", "'useful' begins with the consonant sound /j/"),
        ("a, a", "specific data in the annexure needs 'the'"),
        ("the, a", "'data' used as a mass noun cannot take 'a'")],
       ["'Useful' is pronounced /ˈjuːs-/, so 'a useful'.", "The data meant is specific (in its annexure), so 'the data'."],
       "a + consonant sound; the + specific reference", "Letter 'u' does not always take 'an'.")
