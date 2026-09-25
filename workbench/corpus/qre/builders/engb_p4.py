"""ENG-B part 4: sentence-level correctness selection, word interchange, word order & modifier placement."""

SC = "eng-sentence-level-correctness-selection-9d4e07c1"
WI = "eng-word-interchange-within-a-sentence-e4c29104"
WO = "eng-word-order-and-modifier-placement-1b73c44c"

WI_LEAD = ("In the sentence below, four words are in bold and labelled (A) to (D). Which interchange of the bold words "
           "makes the sentence grammatically and contextually correct? If no interchange is needed, choose 'No interchange required'.")
NX = "No interchange required"


def add_all(B, H):
    mc, si, NI = H["mc"], H["si"], H["NI"]
    F, O = "foundation", "officer"
    CS = "Choose the grammatically correct sentence."

    def wi(tier, level, sentence, correct, wrongs, steps, trap):
        mc(WI, tier, level, WI_LEAD + "\n\n" + sentence, correct, wrongs, steps,
           "Swap only words of the same part of speech; read the result for sense.", trap)

    # ---------------- Sentence-level correctness selection ----------------
    mc(SC, F, "L1", CS, "He has been ill since Monday.",
       [("He is ill since Monday.", "simple present with 'since'"), ("He has been ill from Monday.", "'from' with a perfect tense"),
        ("He was ill since Monday.", "simple past with 'since'")],
       "A state continuing from a past point to now takes the present perfect with 'since'.", "have been + since", "Look for the 'since' signal.")
    mc(SC, F, "L1", CS, "Neither of them was ready.",
       [("Neither of them were ready.", "'neither of' takes a singular verb (formal)"), ("Neither of them are ready.", "plural verb and tense change"),
        ("Neither of they was ready.", "subject pronoun after 'of'")],
       "'Neither of them' + singular verb; object pronoun after 'of'.", "neither of + singular verb", "Plural 'them' attracts 'were'.")
    mc(SC, F, "L2", CS, "She is good at mathematics.",
       [("She is good in mathematics.", "'good' + subject/skill takes 'at'"), ("She is good on mathematics.", "wrong preposition"),
        ("She is well at mathematics.", "adverb 'well' used as adjective")],
       "'Good at' + skill or subject.", "good at", "Prepositions after adjectives are fixed.")
    mc(SC, F, "L2", CS, "I have a lot of work to do today.",
       [("I have lot of works to do today.", "article missing; 'work' is uncountable"), ("I have a lots of work to do today.", "'a lots' is ungrammatical"),
        ("I have many work to do today.", "'many' with an uncountable noun")],
       "'Work' (labour) is uncountable: 'a lot of work'.", "a lot of + uncountable noun", "'Works' means factories or artistic works.")
    mc(SC, F, "L2", CS, "The children were playing in the garden.",
       [("The childrens were playing in the garden.", "double plural"), ("The children was playing in the garden.", "singular verb with plural noun"),
        ("The children were play in the garden.", "base form after 'were'")],
       "'Children' is already plural; continuous = were + V-ing.", "irregular plural + plural verb", "'Childrens' is a common slip.")

    mc(SC, O, "L3", CS, "Hardly had I entered the room when the phone rang.",
       [("Hardly I had entered the room when the phone rang.", "no inversion after fronted 'hardly'"),
        ("Hardly had I entered the room than the phone rang.", "'hardly' paired with 'than'"),
        ("Hardly did I enter the room than the phone rang.", "wrong auxiliary and 'than'")],
       "Hardly had + S + V3 ... when + past simple.", "Hardly had ... when", "Each wrong option has exactly one flaw.")
    mc(SC, O, "L3", CS, "The furniture in the conference room has been replaced.",
       [("The furnitures in the conference room have been replaced.", "'furniture' is uncountable"),
        ("The furniture in the conference room have been replaced.", "plural verb with uncountable noun"),
        ("The furnitures in the conference room has been replaced.", "plural -s on an uncountable noun")],
       "'Furniture' is uncountable and takes a singular verb.", "uncountable noun + singular verb", "'Room' next to the verb is singular in all options.")
    mc(SC, O, "L3", CS, "Each of the candidates was given a separate room.",
       [("Each of the candidates were given a separate room.", "'each of' takes a singular verb"),
        ("Each of the candidate was given a separate room.", "'each of' needs a plural noun"),
        ("Each candidates was given a separate room.", "'each' + singular noun without 'of'")],
       "Each of + plural noun + singular verb; each + singular noun.", "each of + plural noun + singular verb", "Two patterns of 'each' are mixed.")
    mc(SC, O, "L3", CS, "He is one of the best officers that have served here.",
       [("He is one of the best officer that have served here.", "'one of' needs a plural noun"),
        ("He is one of the best officers that has served here.", "relative 'that' refers to plural 'officers'"),
        ("He is one of the better officers that have served here.", "comparative used for a group of more than two")],
       "'That' refers to 'officers' -> 'have'; 'one of the best' + plural noun.", "one of + superlative + plural noun + plural verb",
       "The 'has' version is common but departs from the standard rule.")
    mc(SC, O, "L3", CS, "Had the report been filed on time, the penalty would have been avoided.",
       [("If the report would have been filed on time, the penalty would have been avoided.", "'would have' in the if-clause"),
        ("Had the report been filed on time, the penalty would be avoided.", "result clause not in the past conditional"),
        ("Had the report filed on time, the penalty would have been avoided.", "passive 'been' missing; report cannot file")],
       "Inverted third conditional with a passive: Had + S + been + V3, would have been + V3.", "Had + S + been V3, would have been V3",
       "The options differ by one auxiliary each.")
    mc(SC, O, "L3", CS, "Not only did she clear the exam, but she also topped the state.",
       [("Not only she cleared the exam, but she also topped the state.", "no inversion after fronted 'not only'"),
        ("Not only did she cleared the exam, but also topped the state.", "past form after 'did'"),
        ("Not only did she clear the exam, but she also top the state.", "base form where past is needed")],
       "Fronted 'not only' needs 'did + S + V1'; the second clause keeps normal past form.", "Not only did S V1 ..., but S also V2",
       "Tense must switch back to past after the inverted clause.")
    mc(SC, O, "L3", CS, "The manager, together with his deputies, is attending the review.",
       [("The manager, together with his deputies, are attending the review.", "'together with' does not pluralise the subject"),
        ("The manager, together with his deputies, were attending the review.", "plural verb"),
        ("The manager, together with his deputies, have attended the review.", "plural auxiliary")],
       "The subject is 'the manager'; the phrase in commas is parenthetical.", "together with -> verb follows first subject", "'Deputies' sits next to the verb.")
    mc(SC, O, "L3", CS, "I prefer working in a team to working alone.",
       [("I prefer working in a team than working alone.", "'prefer' takes 'to', not 'than'"),
        ("I prefer to work in a team than working alone.", "mixed forms with 'than'"),
        ("I prefer work in a team to working alone.", "bare verb where a gerund is needed")],
       "prefer + V-ing + to + V-ing.", "prefer X-ing to Y-ing", "'Than' appears only in 'prefer to V rather than V'.")
    mc(SC, O, "L3", CS, "Scarcely a week passes without some complaint reaching the office.",
       [("Scarcely a week passes without some complaint reaches the office.", "finite verb after preposition 'without'"),
        ("Scarcely a week passes without some complaint reached the office.", "past form after 'without'"),
        ("Scarcely a week pass without some complaint reaching the office.", "plural verb with 'a week'")],
       "A preposition ('without') is followed by a noun + gerund.", "without + (noun) + V-ing", "Each distractor changes one verb form.")
    mc(SC, O, "L3", CS, "The committee has asked for more time to finalise its recommendations.",
       [("The committee has asked for more time to finalise their recommendations.", "singular verb, plural pronoun"),
        ("The committee have asked for more time to finalise its recommendations.", "plural verb, singular pronoun"),
        ("The committee has asked more time for finalising its recommendations.", "'ask for' needs 'for' before the thing requested")],
       "Collective noun treated as a unit: 'has ... its'; 'ask for more time'.", "Consistent number for collective nouns", "Inconsistency is the error, not either number alone.")

    # ---------------- Word interchange ----------------
    wi(F, "L1", "The **(A) market** went to the **(B) farmer** to sell his **(C) vegetables** early in the **(D) morning**.",
       "A and B", [("A and C", "a market cannot sell vegetables in the farmer's place"), ("C and D", "selling mornings makes no sense"),
                   (NX, "a market cannot go anywhere")],
       ["The farmer went to the market to sell his vegetables early in the morning."], "Check who can perform the action.")
    wi(F, "L1", "She **(A) boiled** the **(B) kettle** in the **(C) water** before **(D) making** tea.",
       "B and C", [("A and D", "swapping verbs leaves the kettle in the water"), ("A and B", "noun and verb cannot swap"),
                   (NX, "a kettle is not boiled inside water")],
       ["She boiled the water in the kettle before making tea."], "Container and contents are reversed.")
    wi(F, "L2", "The **(A) thief** was **(B) climbing** over the **(C) police** when the **(D) wall** caught him.",
       "C and D", [("A and C", "police climbing over a thief is absurd"), ("B and D", "verb and noun cannot swap"),
                   (NX, "a wall cannot catch anyone")],
       ["The thief was climbing over the wall when the police caught him."], "Find the noun that cannot perform its verb.")
    wi(F, "L2", "Please **(A) switch** off the **(B) lights** before you **(C) leave** the **(D) room**.",
       NX, [("A and C", "'leave off the lights ... switch the room' is meaningless"), ("B and D", "'switch off the room' is illogical"),
            ("C and D", "noun and verb cannot swap")],
       ["The sentence is already correct: switch off the lights before you leave the room."], "Not every sentence needs a swap.")
    wi(F, "L2", "After **(A) signing** it carefully, the **(B) letter** posted the **(C) clerk** before **(D) noon**.",
       "B and C", [("A and B", "gerund and noun cannot swap"), ("A and D", "'After noon it carefully' is meaningless"),
                   (NX, "a letter cannot post a clerk")],
       ["After signing it carefully, the clerk posted the letter before noon."], "Subject and object reversal.")

    wi(O, "L3", "The **(A) auditors** found that the **(B) figures** in the **(C) report** did not **(D) match** those in the ledger.",
       NX, [("A and B", "figures cannot find anything"), ("B and C", "'the report in the figures' reverses the container"),
            ("A and C", "a report cannot find anything")],
       ["Each word is already in its logical place."], "Swapping plausible nouns creates nonsense here.")
    wi(O, "L3", "Despite the heavy **(A) shortage**, the town faced a severe **(B) rain** of drinking **(C) water** throughout **(D) summer**.",
       "A and B", [("B and C", "'severe water of drinking rain' is meaningless"), ("A and C", "'heavy water ... severe rain' is meaningless"),
                   (NX, "'heavy shortage' and 'severe rain of water' are illogical")],
       ["Despite the heavy rain, the town faced a severe shortage of drinking water throughout summer."],
       "The contrast signalled by 'Despite' guides the swap.")
    wi(O, "L3", "The rising **(A) budgets** of **(B) onions** has upset the household **(C) price** of many **(D) families**.",
       "A and C", [("B and D", "'rising budgets of families ... price of onions' leaves A wrong"), ("A and B", "'rising onions of budgets' is illogical"),
                   (NX, "budgets of onions cannot rise")],
       ["The rising price of onions has upset the household budgets of many families.", "Singular 'has' also matches 'price'."],
       "Verb agreement ('has') confirms the singular subject 'price'.")
    wi(O, "L3", "The **(A) patient** examined the **(B) doctor** and prescribed a **(C) week** of rest for a **(D) course**.",
       "A-B and C-D", [("A-B only", "'a week of rest for a course' remains illogical"), ("A-C and B-D", "produces nonsense"),
                       ("C-D only", "the patient still examines the doctor")],
       ["The doctor examined the patient and prescribed a course of rest for a week.", "Two independent swaps are needed."],
       "After one swap, reread: a second error may remain.")
    wi(O, "L3", "Only after the **(A) funds** were **(B) sanctioned** did the **(C) work** on the bridge **(D) begin**.",
       NX, [("A and C", "'work were sanctioned' breaks agreement and sense"), ("B and D", "'funds were begin' is ungrammatical"),
            ("A and B", "noun and verb cannot swap")],
       ["Correct inversion after 'Only after ...'; every word is in place."], "Inversion can make a correct sentence look wrong.")
    wi(O, "L3", "Heavy losses forced the **(A) company** to shut its **(B) workers** and lay off **(C) hundreds** of **(D) plants**.",
       "B and D", [("A and C", "'hundreds to shut its workers' is meaningless"), ("C and D", "'lay off plants of hundreds' is meaningless"),
                   (NX, "workers are laid off, plants are shut")],
       ["Heavy losses forced the company to shut its plants and lay off hundreds of workers."], "Collocation: shut plants, lay off workers.")
    wi(O, "L3", "The committee will **(A) review** the **(B) proposal** at its next **(C) decision** and announce its **(D) meeting** by Friday.",
       "C and D", [("A and B", "verb and noun cannot swap"), ("B and C", "'review the decision at its next proposal' is illogical"),
                   (NX, "a meeting is held; a decision is announced")],
       ["The committee will review the proposal at its next meeting and announce its decision by Friday."], "Collocation: announce a decision.")
    wi(O, "L3", "The accountant was **(A) forged** after the audit revealed that he had **(B) suspended** the manager's **(C) signature** on several **(D) cheques**.",
       "A and B", [("C and D", "'forged ... cheques on several signatures' still leaves A-B wrong"), ("B and C", "verb and noun cannot swap"),
                   (NX, "a person is suspended; a signature is forged")],
       ["The accountant was suspended after the audit revealed that he had forged the manager's signature on several cheques."],
       "Both bold verbs are participles, so they are swap candidates.")
    wi(O, "L3", "The unseasonal **(A) crop** damaged the standing **(B) rain**, and the **(C) compensation** demanded **(D) farmers**.",
       "A-B and C-D", [("A-B only", "compensation still demands farmers"), ("C-D only", "the crop still damages the rain"),
                       ("A-C and B-D", "produces nonsense")],
       ["The unseasonal rain damaged the standing crop, and the farmers demanded compensation."], "Two role reversals in one sentence.")
    wi(O, "L3", "The **(A) accounts** of the employees was credited to their **(B) salary** a day **(C) before** the **(D) festival**.",
       "A and B", [("C and D", "'a day festival the before' is ungrammatical"), ("B and D", "'credited to their festival' is illogical"),
                   (NX, "singular 'was' and sense require 'salary' as subject")],
       ["The salary of the employees was credited to their accounts a day before the festival."], "Singular 'was' signals the singular subject.")

    # ---------------- Word order and modifier placement ----------------
    mc(WO, F, "L1", "Choose the sentence with correct word order.", "She always comes to office on time.",
       [("She comes always to office on time.", "frequency adverb after the main verb"), ("Always she comes to office on time.", "frequency adverb fronted without reason"),
        ("She comes to always office on time.", "adverb splits the phrase 'to office'")],
       "Frequency adverbs go before the main verb (after 'be').", "S + frequency adverb + main verb", "Adverb position is the only difference.")
    mc(WO, F, "L1", "Choose the correct order of adjectives.", "a beautiful old wooden table",
       [("a wooden old beautiful table", "material placed before opinion and age"), ("an old beautiful wooden table", "age placed before opinion"),
        ("a beautiful wooden old table", "material placed before age")],
       "Order: opinion - size - age - shape - colour - origin - material - purpose.", "OSASCOMP", "Native-sounding order follows a fixed sequence.")
    si(WO, F, "L2", "Walking along the beach, **the sunset looked breathtaking**.", "we found the sunset breathtaking",
       [("the sunset was breathtaking to see", "the sunset is still the one walking"), ("breathtaking the sunset looked", "inverted but still dangling"),
        (NI, "dangling participle: the sunset was not walking")],
       "The subject after the participial phrase must be the one doing the walking.", "Participle attaches to the next subject",
       "Rewording the predicate does not fix a dangling modifier.")
    mc(WO, F, "L2", "Rearrange into a correct sentence: never / I / such / have / seen / a crowd",
       "I have never seen such a crowd.",
       [("Never I have seen such a crowd.", "fronted 'never' without inversion"), ("I have seen never such a crowd.", "'never' after the main verb"),
        ("I have never such a crowd seen.", "object before the participle")],
       "Negative adverb between auxiliary and main verb.", "S + aux + never + V3 + object", "If 'never' is fronted, inversion is required.")
    mc(WO, F, "L2", "Choose the sentence that says clearly that the book has a red cover.",
       "He gave his friend the book with a red cover.",
       [("He gave the book to his friend with a red cover.", "modifier seems to describe the friend"),
        ("With a red cover, he gave the book to his friend.", "modifier seems to describe him"),
        ("He, with a red cover, gave the book to his friend.", "modifier attached to 'he'")],
       "Place the modifier next to the word it describes.", "Modifier beside its noun", "Misplaced phrases create comic meanings.")

    si(WO, O, "L3", "Having finished the report, **the laptop was switched off by Priya**.", "Priya switched off the laptop",
       [("the laptop was switched off", "still implies the laptop finished the report"),
        ("switching off the laptop was done by Priya", "gerund subject; still dangling"),
        (NI, "dangling participle")],
       "The doer of 'having finished' must be the subject: Priya.", "Participial phrase -> doer as subject", "Passive voice often causes danglers.")
    mc(WO, O, "L3", "The intended meaning is that the results will come out on Monday. Which sentence conveys this without ambiguity?",
       "The officer told the applicants that the results would be declared on Monday.",
       [("On Monday, the officer told the applicants that the results would be declared.", "Monday attaches to 'told'"),
        ("The officer told the applicants on Monday that the results would be declared.", "Monday attaches to 'told'"),
        ("The officer, on Monday, told the applicants the results would be declared.", "Monday attaches to 'told'")],
       "Put the time phrase inside the clause it modifies (would be declared on Monday).", "Modifier inside its clause",
       "All sentences are grammatical; only one matches the meaning.")
    mc(WO, O, "L3", "The intended meaning is that no one other than the auditor saw the file. Choose the sentence that says this.",
       "Only the auditor saw the file.",
       [("The auditor only saw the file.", "suggests he merely saw it, not studied it"), ("The auditor saw only the file.", "means he saw nothing else"),
        ("The auditor saw the only file.", "means there was just one file")],
       "'Only' limits the word immediately after it.", "Place 'only' before the word it limits", "Shifting 'only' changes meaning.")
    si(WO, O, "L3", "To qualify for the scholarship, **an entrance test must be cleared**.", "a student must clear an entrance test",
       [("an entrance test has to be cleared", "still no doer for 'to qualify'"), ("clearing an entrance test is must", "no doer, and 'is must' is ungrammatical"),
        (NI, "dangling infinitive: a test does not qualify")],
       "The doer of the infinitive phrase must be the subject.", "Infinitive phrase -> doer as subject", "The passive hides the doer.")
    si(WO, O, "L3", "Could you tell me **where is the accounts section**?", "where the accounts section is",
       [("where is located the accounts section", "question order retained"), ("that where the accounts section is", "'that' before a wh-clause"),
        (NI, "embedded questions use statement order")],
       "Indirect/embedded questions take subject-verb order.", "wh-word + S + V", "Direct-question order is carried over.")
    mc(WO, O, "L2", "Choose the sentence with correct word order.", "The room is not large enough for the meeting.",
       [("The room is not enough large for the meeting.", "'enough' before the adjective"), ("The room is enough not large for the meeting.", "'enough' before 'not'"),
        ("The room enough is not large for the meeting.", "'enough' before the verb")],
       "'Enough' follows adjectives and adverbs (large enough).", "adjective + enough", "Before nouns, 'enough' precedes (enough chairs).")
    mc(WO, O, "L3", "The intended meaning is that those who often come late are warned. Choose the unambiguous sentence.",
       "Employees who frequently arrive late are warned.",
       [("Employees who arrive late frequently are warned.", "squinting modifier: 'frequently' can go with either verb"),
        ("Employees who arrive late are frequently warned.", "frequency now describes the warning"),
        ("Employees who arrive late are warned frequently.", "frequency describes the warning")],
       "Place the adverb where it can modify only one verb.", "Avoid squinting modifiers", "The first distractor is ambiguous, not simply wrong.")
    si(WO, O, "L3", "Not until the audit was over **the manager did realise** the extent of the loss.", "did the manager realise",
       [("the manager realised", "no inversion after 'Not until ...'"), ("realised the manager", "verb before subject without auxiliary"),
        (NI, "auxiliary placed after the subject")],
       "Fronted 'Not until ...' requires inversion in the main clause: did + S + V1.", "Not until X, aux + S + V", "The inversion comes in the main clause, not the until-clause.")
    si(WO, O, "L3", "On entering the hall, **the portrait of the founder caught my eye**.", "I noticed the portrait of the founder",
       [("the founder's portrait caught my eye", "still dangling: the portrait did not enter"), ("the portrait of the founder was noticed", "no doer"),
        (NI, "dangling gerund phrase")],
       "The person entering must be the subject: 'I noticed ...'.", "Gerund phrase -> doer as subject", "'My eye' is not the subject.")
    mc(WO, O, "L3", "Choose the correct order.", "two large black leather bags",
       [("two black large leather bags", "colour before size"), ("large two black leather bags", "number after size"),
        ("two leather large black bags", "material before size and colour")],
       "Determiner/number - size - colour - material + noun.", "number + size + colour + material", "Numbers come first.")
