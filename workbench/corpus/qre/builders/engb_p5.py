"""ENG-B part 5: synonyms, antonyms, commonly confused pairs, formal/business register (incl. email set), one-word substitution."""

SY = "eng-synonyms-6113204e"
AN = "eng-antonyms-af017948"
CF = "eng-commonly-confused-word-pairs-f6bc9a52"
RG = "eng-formal-and-business-register-f2975b74"
OW = "eng-one-word-substitution-13964bb4"


def add_all(B, H):
    mc = H["mc"]
    F, O = "foundation", "officer"
    REF = "Standard dictionary sense (Oxford/Cambridge learner's dictionaries)."

    def syn(tier, level, word, key, wrongs, meaning, ctx=None):
        stem = (f"Choose the word most similar in meaning to the word in bold:\n\n{ctx}" if ctx
                else f"Choose the word most similar in meaning to **{word}**.")
        mc(SY, tier, level, stem, key, wrongs, [f"{word.capitalize()}: {meaning}.", f"Closest synonym: {key}."], REF,
           "Look-alike and opposite-meaning options are placed as traps.")

    def ant(tier, level, word, key, wrongs, meaning, ctx=None):
        stem = (f"Choose the word most nearly OPPOSITE in meaning to the word in bold:\n\n{ctx}" if ctx
                else f"Choose the word most nearly OPPOSITE in meaning to **{word}**.")
        mc(AN, tier, level, stem, key, wrongs, [f"{word.capitalize()}: {meaning}.", f"Opposite: {key}."], REF,
           "Synonyms of the given word are the commonest trap in antonym questions.")

    def cf(tier, level, sentence, key, wrongs, note):
        mc(CF, tier, level, "Choose the word that correctly fills the blank:\n\n" + sentence, key, wrongs, [note], REF,
           "The options sound or look alike; only one fits the meaning.")

    def ows(tier, level, phrase, key, wrongs, note):
        mc(OW, tier, level, f"Choose the one word for: '{phrase}'.", key, wrongs, [note], REF,
           "Distractors share a prefix or a related field.")

    # ---------------- Synonyms ----------------
    syn(F, "L1", "candid", "Frank", [("Cunning", "opposite in spirit: deceitful"), ("Careful", "unrelated quality"), ("Cheerful", "sound-alike start only")],
        "truthful and straightforward")
    syn(F, "L1", "abandon", "Desert", [("Adopt", "opposite: take up"), ("Protect", "opposite: look after"), ("Absorb", "look-alike prefix")],
        "leave behind completely")
    syn(F, "L1", "meticulous", "Painstaking", [("Careless", "antonym"), ("Timid", "unrelated"), ("Hasty", "near antonym")],
        "showing great attention to detail")
    syn(F, "L2", "prudent", "Judicious", [("Reckless", "antonym"), ("Arrogant", "unrelated"), ("Prudish", "look-alike: excessively proper")],
        "acting with care and good judgement")
    syn(F, "L2", "lucid", "Clear", [("Lucky", "look-alike"), ("Vague", "antonym"), ("Liquid", "sound-alike")],
        "expressed clearly; easy to understand")

    syn(O, "L2", "ephemeral", "Transient", [("Eternal", "antonym"), ("Ethereal", "look-alike: delicate, heavenly"), ("Elusive", "hard to catch, not short-lived")],
        "lasting a very short time")
    syn(O, "L3", "obdurate", "Intransigent", [("Obedient", "look-alike; near opposite"), ("Obscure", "look-alike prefix"), ("Contrite", "remorseful; opposite attitude")],
        "stubbornly refusing to change one's opinion")
    syn(O, "L3", "cryptic", "Enigmatic", [("Critical", "sound-alike"), ("Candid", "antonym"), ("Crude", "unrelated")],
        "having a hidden or ambiguous meaning",
        ctx="The minister's **cryptic** remark left reporters guessing.")
    syn(O, "L3", "sanguine", "Optimistic", [("Gloomy", "antonym"), ("Sanitary", "look-alike"), ("Sluggish", "unrelated")],
        "hopeful, especially in a difficult situation")
    syn(O, "L3", "deferred", "Postponed", [("Referred", "rhyme-alike"), ("Deflected", "look-alike"), ("Declared", "opposite outcome")],
        "put off to a later time",
        ctx="The committee **deferred** its decision until the audit report arrived.")
    syn(O, "L3", "perfunctory", "Cursory", [("Thorough", "antonym"), ("Punctual", "unrelated"), ("Perpetual", "look-alike prefix")],
        "carried out with minimum effort or care")
    syn(O, "L3", "alacrity", "Eagerness", [("Reluctance", "antonym"), ("Alarm", "look-alike start"), ("Accuracy", "unrelated")],
        "brisk and cheerful readiness")
    syn(O, "L3", "laconic", "Terse", [("Lengthy", "antonym"), ("Lazy", "sound-alike start"), ("Lyrical", "unrelated")],
        "using very few words",
        ctx="Her **laconic** reply suggested she had no wish to discuss the matter.")
    syn(O, "L3", "exacerbate", "Aggravate", [("Alleviate", "antonym"), ("Exaggerate", "look-alike: overstate"), ("Exonerate", "look-alike: clear of blame")],
        "make a problem worse")
    syn(O, "L3", "specious", "Deceptively plausible", [("Spacious", "look-alike: roomy"), ("Specific", "look-alike"), ("Well-founded", "antonym")],
        "superficially plausible but actually wrong",
        ctx="The auditor found the explanation **specious**.")

    # ---------------- Antonyms ----------------
    ant(F, "L1", "ancient", "Modern", [("Old", "synonym"), ("Antique", "synonym"), ("Historic", "related, not opposite")], "very old")
    ant(F, "L1", "generous", "Stingy", [("Kind", "near synonym"), ("Liberal", "synonym"), ("Gentle", "unrelated")], "willing to give freely")
    ant(F, "L1", "victory", "Defeat", [("Triumph", "synonym"), ("Success", "synonym"), ("Conquest", "synonym")], "success in a contest")
    ant(F, "L2", "transparent", "Opaque", [("Clear", "synonym"), ("Translucent", "partly transparent; not opposite"), ("Lucid", "synonym (of expression)")],
        "allowing light to pass through; easily seen through")
    ant(F, "L2", "diligent", "Indolent", [("Industrious", "synonym"), ("Intelligent", "look-alike"), ("Assiduous", "synonym")],
        "hard-working and careful")

    ant(O, "L2", "verbose", "Concise", [("Wordy", "synonym"), ("Verbal", "look-alike"), ("Vocal", "related field")], "using more words than needed")
    ant(O, "L3", "acrimonious", "Cordial", [("Bitter", "synonym"), ("Acrid", "look-alike, also harsh"), ("Rancorous", "synonym")],
        "angry and bitter")
    ant(O, "L3", "candid", "Evasive", [("Frank", "synonym"), ("Detailed", "unrelated"), ("Brief", "unrelated")], "open and honest",
        ctx="The CEO gave a **candid** account of the losses.")
    ant(O, "L3", "zenith", "Nadir", [("Apex", "synonym"), ("Summit", "synonym"), ("Horizon", "related field")], "the highest point")
    ant(O, "L3", "magnanimous", "Petty", [("Generous", "synonym"), ("Enormous", "sound-alike"), ("Unanimous", "look-alike")],
        "generous or forgiving, especially towards a rival")
    ant(O, "L3", "ameliorate", "Worsen", [("Improve", "synonym"), ("Mitigate", "synonym"), ("Moderate", "near synonym")], "make better")
    ant(O, "L3", "curb", "Encourage", [("Restrain", "synonym"), ("Curtail", "synonym"), ("Monitor", "related, not opposite")], "restrain or keep in check",
        ctx="The policy was designed to **curb** wasteful expenditure.")
    ant(O, "L3", "ostentatious", "Unpretentious", [("Showy", "synonym"), ("Ostensible", "look-alike: apparent"), ("Pompous", "near synonym")],
        "designed to impress; showy")
    ant(O, "L3", "taciturn", "Garrulous", [("Reserved", "synonym"), ("Tactful", "look-alike"), ("Silent", "synonym")], "saying little")
    ant(O, "L3", "placate", "Provoke", [("Pacify", "synonym"), ("Appease", "synonym"), ("Explain", "unrelated")], "make less angry",
        ctx="Her remarks were intended to **placate** the angry depositors.")

    # ---------------- Commonly confused word pairs ----------------
    cf(F, "L1", "'The medicine had no ___ on the fever.'", "effect",
       [("affect", "verb, not noun"), ("affection", "fondness"), ("effort", "exertion")],
       "'Effect' (noun) = result; 'affect' (verb) = influence.")
    cf(F, "L1", "'Please ___ my apology.'", "accept",
       [("except", "means excluding"), ("expect", "means anticipate"), ("excerpt", "means an extract")],
       "'Accept' = receive willingly.")
    cf(F, "L1", "'He was asked to write on official ___.'", "stationery",
       [("stationary", "means not moving"), ("statutory", "means required by law"), ("station", "a place")],
       "'Stationery' = writing materials; 'stationary' = still.")
    cf(F, "L2", "'A judge must remain ___ in a dispute between two parties.'", "disinterested",
       [("uninterested", "means not interested/bored"), ("uninteresting", "means dull"), ("disinteresting", "not a standard word")],
       "'Disinterested' = impartial; 'uninterested' = not interested.")
    cf(F, "L2", "'The ___ of the school addressed the students.'", "principal",
       [("principle", "a rule or belief"), ("principality", "a state ruled by a prince"), ("principled", "adjective: having principles")],
       "'Principal' = head of a school; 'principle' = rule.")

    cf(O, "L2", "'The two firms agreed ___ themselves to share the costs.'", "between",
       [("among", "used for more than two"), ("amongst", "variant of 'among'"), ("amid", "means in the middle of")],
       "'Between' is used for two parties; 'among' for three or more.")
    cf(O, "L3", "'The river's ___ flow powers the mill day and night without a break.'", "continuous",
       [("continual", "repeated with breaks"), ("contiguous", "adjacent"), ("contingent", "dependent on something")],
       "'Continuous' = without interruption; 'continual' = recurring.")
    cf(O, "L3", "'The questions were framed to ___ honest answers from the witnesses.'", "elicit",
       [("illicit", "means unlawful"), ("elucidate", "means explain"), ("implicit", "means implied")],
       "'Elicit' = draw out (a response); 'illicit' = illegal.")
    cf(O, "L3", "'After the incident, he had a guilty ___.'", "conscience",
       [("conscious", "adjective: aware"), ("consciousness", "state of being awake"), ("conscientious", "adjective: diligent")],
       "'Conscience' = moral sense of right and wrong.")
    cf(O, "L3", "'The new software is designed to ___ the existing system, not replace it.'", "complement",
       [("compliment", "means praise"), ("complimentary", "means free or praising"), ("completion", "means finishing")],
       "'Complement' = complete or enhance; 'compliment' = praise.")
    cf(O, "L3", "'He is ___ to taking unnecessary risks with public money.'", "averse",
       [("adverse", "means harmful/unfavourable"), ("aversive", "causing avoidance; not used with 'to taking'"), ("adversely", "adverb")],
       "'Averse to' = opposed to; 'adverse' = unfavourable (adverse effects).")
    cf(O, "L3", "'The regulator has ___ the sale of unregistered products.'", "proscribed",
       [("prescribed", "means laid down or recommended"), ("subscribed", "means signed up"), ("described", "means depicted")],
       "'Proscribe' = forbid; 'prescribe' = recommend or lay down.")
    cf(O, "L3", "'With the river rising fast, the danger of flooding was ___.'", "imminent",
       [("eminent", "means distinguished"), ("immanent", "means inherent"), ("prominent", "means conspicuous")],
       "'Imminent' = about to happen.")
    cf(O, "L3", "'The engineer devised an ___ solution that cut costs by half.'", "ingenious",
       [("ingenuous", "means innocent/naive"), ("indigenous", "means native"), ("ingenue", "noun: an innocent young woman (theatre)")],
       "'Ingenious' = clever and inventive; 'ingenuous' = naive.")
    cf(O, "L3", "'The lawyer's ___ was to settle the matter out of court.'", "counsel",
       [("council", "an advisory or governing body"), ("consul", "a diplomatic official"), ("cancel", "a verb: call off")],
       "'Counsel' = advice (or a lawyer); 'council' = a body of people.")

    # ---------------- Formal and business register ----------------
    mc(RG, F, "L1", "Which is the most appropriate salutation for a formal letter to a bank manager whose name you do not know?",
       "Dear Sir/Madam,", [("Hi there,", "casual greeting"), ("Hey Manager,", "casual and unconventional"), ("My dear friend,", "personal letter")],
       "Formal letters to an unnamed recipient open with 'Dear Sir/Madam'.", "Formal salutation", "Friendliness is not formality.")
    mc(RG, F, "L1", "Choose the most formal replacement for the words in bold:\n\n'Please **get in touch with** the branch for details.'",
       "contact", [("buzz", "slang"), ("ring up", "informal phrasal verb"), ("hit up", "slang")],
       "'Contact' is the neutral-formal verb.", "Formal single verb over informal phrasal verb", "Phrasal verbs are usually less formal.")
    mc(RG, F, "L2", "In British convention, a formal letter that begins 'Dear Sir' should close with:",
       "Yours faithfully", [("Yours lovingly", "personal letter"), ("Cheers", "informal"), ("Yours affectionately", "personal letter")],
       "'Dear Sir/Madam' -> 'Yours faithfully'; 'Dear Mr X' -> 'Yours sincerely'.", "Salutation-closing pairing", "Sincerely/faithfully mix-up.")
    mc(RG, F, "L2", "Choose the most formal replacement for the words in bold:\n\n'We need to **find out** why the system crashed.'",
       "ascertain", [("figure", "incomplete and informal"), ("suss out", "slang"), ("dig", "informal and wrong sense")],
       "'Ascertain' = find out for certain (formal).", "Latinate verb for formal writing", "Informal alternatives are shorter.")
    mc(RG, F, "L2", "Which sentence is written in a formal register suitable for an official letter?",
       "We regret to inform you that your application has not been successful.",
       [("Sorry mate, looks like your application didn't make the cut this time round.", "slang and contractions"),
        ("Bad news, we're afraid: your application has gone nowhere, so tough luck.", "blunt and colloquial"),
        ("Your application? Not happening this time, unfortunately, so do try again.", "fragmented, conversational")],
       "Formal register: complete sentences, no contractions or slang, polite set phrases ('We regret to inform you').",
       "Formal: complete, impersonal, polite", "Tone, not content, differs between the options.")

    mc(RG, O, "L3", "Choose the word most suitable for a formal business letter:\n\n'The firm will ___ the contract at the end of the next quarter.'",
       "terminate", [("ditch", "slang"), ("axe", "journalistic/informal"), ("scrap", "informal")],
       "'Terminate' is the formal verb for ending a contract.", "Formal verb choice", "Headline words are informal.")
    mc(RG, O, "L3", "Which phrase is too informal for a report to the board of directors?",
       "a bunch of issues cropped up", [("several issues emerged in the review", "formal and suitable"), ("the committee observed", "formal and suitable"),
                                        ("pending further review", "formal and suitable")],
       "'A bunch of' and 'cropped up' are colloquial.", "Colloquialisms are out of place in board reports", "Identify the odd one out.")
    mc(RG, O, "L3", "Which is the most appropriate way to decline a vendor's proposal in writing?",
       "Thank you for your proposal; after due consideration, we will not be proceeding with it.",
       [("Your proposal is not good enough for us, so please do not send us any more of them.", "rude and dismissive"),
        ("We have gone through your proposal and, frankly, it was a waste of our valuable time.", "insulting"),
        ("Thanks, but no thanks; we're going with someone else, so don't bother following up.", "slangy and curt")],
       "Polite refusal: thanks + reason/consideration + clear decision.", "Courteous refusal formula", "Clarity and courtesy together.")
    mc(RG, O, "L3", "Choose the most formal way to complete the sentence:\n\n'Owing to unforeseen circumstances, the meeting has been ___.'",
       "deferred", [("put on the back burner", "informal idiom"), ("shoved back", "slang"), ("pushed off", "informal phrasal verb")],
       "'Deferred' = postponed (formal).", "Formal verb over idiom", "Idioms reduce formality.")
    mc(RG, O, "L3", "Which sentence best suits an official circular?",
       "Staff are requested to complete the training module by 30 June.",
       [("You guys really need to get that training module done by 30 June, okay?", "slang and tag question"),
        ("Hey all, do the training by 30 June or else!", "threatening and casual"),
        ("Can everybody please, please finish the training soon?", "pleading tone and vague deadline")],
       "Circulars use impersonal, polite passive forms ('Staff are requested to ...').", "Impersonal request formula", "Informal urgency is not formality.")
    mc(RG, O, "L3", "In a formal complaint letter, which verb best replaces 'fix' in 'Please fix the error in my account statement'?",
       "rectify", [("sort", "informal and incomplete ('sort out')"), ("patch", "informal"), ("tweak", "informal, implies minor change")],
       "'Rectify' = put right (formal).", "Formal verb choice", "Everyday verbs lower the register.")
    mc(RG, O, "L3", "Which is the most appropriate subject line for a formal email requesting leave?",
       "Request for casual leave on 12 and 13 March",
       [("hey boss, need a couple of days off next week, ok?", "casual, vague"), ("Leave!!!", "uninformative, emotional punctuation"),
        ("Urgent pls read", "vague, abbreviated")],
       "Formal subject lines are specific and neutral.", "Specific, neutral subject line", "Urgency markers do not replace content.")
    stim = ("A junior officer has drafted the following email to a senior official of another department.\n\n"
            "> Hi Mr Rao,\n> (1) Hope you're doing good. (2) I wanted to check if you could send across the pending utilisation "
            "certificates ASAP. (3) Our audit is coming up and we're kind of stuck without them. (4) Thanks a ton!\n> Cheers,\n> Anil")
    G = "ENB-G04"
    mc(RG, O, "L4", "Which is the most appropriate replacement for sentence (1)?", "I hope this email finds you well.",
       [("Hope you're doing great, buddy!", "still casual and exclamatory"), ("Wassup, hope all's cool.", "slang"),
        ("Trust you are doing good these days.", "'doing good' used for 'doing well'")],
       ["A formal opener is complete and grammatical: 'I hope this email finds you well.'"], "Formal opening line",
       "'Doing good' is a grammar slip as well as a register slip.", group=G, stim=stim)
    mc(RG, O, "L4", "Which version best replaces sentences (2) and (3)?",
       "I would be grateful if you could send the pending utilisation certificates at the earliest, as they are needed for our audit.",
       [("Please send the pending utilisation certificates ASAP because our audit is coming and we're kind of stuck.", "abbreviation and colloquialisms"),
        ("Send us the pending utilisation certificates immediately, since without them our audit simply cannot go ahead.", "peremptory tone to a senior"),
        ("Could you, like, maybe send the pending utilisation certificates soon-ish, since our audit is coming up quickly?", "fillers and slang")],
       ["Polite request formula to a senior: 'I would be grateful if you could ...'", "Give the reason neutrally."], "Polite indirect request",
       "Directness that suits a peer can sound peremptory to a senior.", group=G, stim=stim)
    mc(RG, O, "L4", "If the salutation is changed to 'Dear Mr Rao,', which closing should replace 'Cheers,'?", "Yours sincerely,",
       [("Cheers again,", "informal"), ("Love,", "personal"), ("Take care,", "informal")],
       ["A named salutation pairs with 'Yours sincerely' in British convention."], "Dear Mr X -> Yours sincerely",
       "'Yours faithfully' is for unnamed recipients.", group=G, stim=stim)

    # ---------------- One-word substitution ----------------
    ows(F, "L1", "One who cannot read or write", "Illiterate",
        [("Ignorant", "lacking knowledge in general"), ("Innocent", "free of guilt"), ("Illegible", "not readable (of writing)")],
        "Illiterate = unable to read or write.")
    ows(F, "L1", "A person who does not eat meat", "Vegetarian",
        [("Cannibal", "eats human flesh"), ("Carnivore", "eats meat"), ("Omnivore", "eats both plants and meat")],
        "Vegetarian = one who does not eat meat.")
    ows(F, "L1", "A speech delivered without preparation", "Extempore",
        [("Soliloquy", "speaking one's thoughts aloud alone (drama)"), ("Monologue", "a long speech by one person"), ("Epilogue", "concluding section")],
        "Extempore = spoken without preparation.")
    ows(F, "L2", "Handwriting that cannot be read", "Illegible",
        [("Ineligible", "not qualified"), ("Illiterate", "unable to read"), ("Inaudible", "cannot be heard")],
        "Illegible = not clear enough to be read.")
    ows(F, "L2", "One who lives at the expense of others", "Parasite",
        [("Philanthropist", "one who gives to others"), ("Hermit", "one who lives alone"), ("Pedestrian", "one who walks")],
        "Parasite (figurative) = one who lives off others.")

    ows(O, "L2", "Government by the wealthy few", "Plutocracy",
        [("Autocracy", "rule by one person"), ("Bureaucracy", "rule by officials"), ("Theocracy", "rule by religious authority")],
        "Plutocracy = rule by the rich.")
    ows(O, "L3", "A remedy for all ills", "Panacea",
        [("Placebo", "inactive substance given for psychological effect"), ("Antidote", "remedy for a specific poison"), ("Pandemic", "widespread disease")],
        "Panacea = cure-all.")
    ows(O, "L3", "One who is indifferent to pleasure or pain", "Stoic",
        [("Cynic", "one who distrusts others' motives"), ("Epicure", "one devoted to fine food"), ("Sceptic", "one who doubts")],
        "Stoic = enduring without complaint or show of feeling.")
    ows(O, "L3", "A list of items to be discussed at a meeting", "Agenda",
        [("Minutes", "record of what was discussed"), ("Memorandum", "internal written note"), ("Itinerary", "travel plan")],
        "Agenda = items to be discussed.")
    ows(O, "L3", "A regular payment made to a person who has retired from service", "Pension",
        [("Bonus", "extra payment for performance"), ("Gratuity", "lump-sum paid on leaving service"), ("Stipend", "allowance for a trainee or student")],
        "Pension = periodic payment after retirement.")
    ows(O, "L3", "Incapable of being corrected or reformed", "Incorrigible",
        [("Incredible", "unbelievable"), ("Indelible", "cannot be erased"), ("Invincible", "cannot be defeated")],
        "Incorrigible = beyond correction.")
    ows(O, "L3", "Present everywhere at the same time", "Omnipresent",
        [("Omniscient", "all-knowing"), ("Omnipotent", "all-powerful"), ("Omnivorous", "eating everything")],
        "Omnipresent = present everywhere.")
    ows(O, "L3", "The practice of favouring one's relatives in appointments", "Nepotism",
        [("Cronyism", "favouring friends, not relatives"), ("Nihilism", "rejection of all principles"), ("Altruism", "selfless concern for others")],
        "Nepotism = favouritism shown to relatives.")
    ows(O, "L3", "A statement that seems self-contradictory but may be true", "Paradox",
        [("Irony", "saying the opposite of what is meant"), ("Hyperbole", "exaggeration"), ("Allegory", "story with a hidden meaning")],
        "Paradox = apparently contradictory yet possibly true statement.")
    ows(O, "L3", "A formal written statement made on oath", "Affidavit",
        [("Testimony", "evidence, often oral"), ("Petition", "formal request"), ("Warrant", "authorisation, e.g. for arrest")],
        "Affidavit = sworn written statement.")
