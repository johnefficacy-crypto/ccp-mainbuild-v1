/**
 * English verbal drills — module catalogue and sample question bank.
 *
 * Ported verbatim from the Claude Design handoff "English Practice v2". All
 * questions are original samples modelled on SSC / Banking / UPSC CSAT / State
 * PSC / Railways / Defence verbal-ability patterns; they are NOT past-paper
 * items. Swap BANK for a question-bank read model when one exists.
 */
/* eslint-disable quotes */
export const MODS = [
  { id:'pj', name:'Parajumbles', tag:'Reordering', desc:'Drag jumbled parts of a sentence or paragraph into a logical sequence.' },
  { id:'err', name:'Error Detection', tag:'Spotting errors', desc:'Find the part of the sentence that contains a grammatical error.' },
  { id:'imp', name:'Sentence Improvement', tag:'Replacement', desc:'Replace the underlined phrase with the grammatically correct option.' },
  { id:'cloze', name:'Cloze Test', tag:'Fill in the blanks', desc:'Complete a short passage, one numbered blank at a time.' },
  { id:'rc', name:'Reading Comprehension', tag:'Passages', desc:'Read a short passage and answer inference, vocabulary and tone questions.' },
  { id:'voc', name:'Vocabulary', tag:'Words & phrases', desc:'Synonyms, antonyms, idioms, proverbs, one-word substitution and spelling.' },
  { id:'ce', name:'Common Errors', tag:'Usage & Indianisms', desc:'Everyday sentences that sound right but often aren’t. Correct or not?' },
  { id:'pos', name:'Parts of Speech', tag:'Grammar', desc:'Tag every word, then catch words used as the wrong part of speech.' },
  { id:'sc', name:'Sentence Construction', tag:'Build & transform', desc:'Assemble sentences and convert voice and narration.' }
];
export const TABS = {
  voc: [['syn','Synonyms'],['ant','Antonyms'],['idiom','Idioms'],['prov','Proverbs'],['ows','One-word'],['spell','Spelling']],
  pos: [['tag','Tag words'],['mis','Misused words']],
  sc: [['build','Build'],['voice','Active → Passive'],['speech','Direct → Indirect']]
};
export const TYPES = [['pj','','Parajumble'],['err','','Error detection'],['imp','','Sentence improvement'],['cloze','','Cloze test'],['rc','','Reading comprehension'],['voc','syn','Synonym'],['voc','ant','Antonym'],['voc','idiom','Idiom'],['voc','prov','Proverb'],['voc','ows','One-word substitution'],['voc','spell','Spelling'],['ce','','Common error'],['pos','tag','Parts of speech'],['pos','mis','Misused part of speech'],['sc','build','Sentence construction'],['sc','voice','Active → passive voice'],['sc','speech','Direct → indirect speech']];
export const INSTRUCTIONS = {
  'pj:':'Drag rows (or tap two to swap) into a logical order, then Check.', 'err:':'Tap the part that contains the error, or “No error”.',
  'imp:':'Choose the phrase that best replaces the underlined part.', 'cloze:':'Tap a numbered blank, choose a word, and Check once every blank is filled.',
  'rc:':'Read the passage, then answer the question.', 'voc:syn':'Choose the word closest in meaning.', 'voc:ant':'Choose the word opposite in meaning.',
  'voc:idiom':'Choose the meaning of the idiom.', 'voc:prov':'Choose the meaning of the proverb.', 'voc:ows':'Choose the one word that replaces the phrase.',
  'voc:spell':'Choose the correctly spelt word.', 'ce:':'Is the sentence correct as written?', 'pos:tag':'Pick a tag, tap every word it applies to, then Check.',
  'pos:mis':'One word is the wrong part of speech. Tap it.', 'sc:build':'Tap words in order to build a correct sentence.',
  'sc:voice':'Rebuild the sentence in the passive voice.', 'sc:speech':'Rebuild the sentence in indirect speech.'
};
export const VOC_PROMPT = { syn:'Synonym of', ant:'Antonym of', idiom:'Idiom', prov:'Proverb', ows:'One word for', spell:'Correct spelling for' };
export const POS_TAGS = {
  N:{name:'Noun',short:'N',h:262}, PRON:{name:'Pronoun',short:'PRON',h:300}, V:{name:'Verb',short:'V',h:27},
  ADJ:{name:'Adjective',short:'ADJ',h:150}, ADV:{name:'Adverb',short:'ADV',h:200}, PREP:{name:'Preposition',short:'PREP',h:65},
  CONJ:{name:'Conjunction',short:'CONJ',h:340}, DET:{name:'Determiner',short:'DET',h:100}, INTJ:{name:'Interjection',short:'INTJ',h:230}
};
export const BANK = {
  pj: [
    { kind:'Sentence', parts:['Despite the heavy rain,','the farmers continued','to sow their fields','in the hope of a good harvest.'], given:[2,0,3,1], note:'Concession clause first, then subject + verb, the object, and finally the purpose.' },
    { kind:'Sentence', parts:['Not only did he','finish the project on time,','but he also','kept it within budget.'], given:[3,1,0,2], note:'“Not only … but also” — the inverted auxiliary “did he” opens the sentence.' },
    { kind:'Paragraph', parts:['The Indian monsoon is a seasonal reversal of winds.','It delivers nearly three-quarters of the country’s annual rainfall.','A weak season can therefore push up food prices across the economy.','This is why economists track it as closely as meteorologists do.'], given:[1,3,0,2], note:'Definition → significance → consequence (“therefore”) → conclusion (“This is why”).' },
    { kind:'Sentence', parts:['The report,','which was submitted last week,','has been','praised by the committee.'], given:[1,3,2,0], note:'Subject, then its non-defining relative clause, then the verb phrase.' },
    { kind:'Paragraph', parts:['Digital payments have grown rapidly in India.','UPI alone now processes billions of transactions every month.','However, this growth has also led to more online fraud.','Awareness campaigns are therefore essential for first-time users.'], given:[2,0,3,1], note:'Topic → supporting fact → contrast (“However”) → conclusion (“therefore”).' }
  ],
  err: [
    { parts:['One of my friend','has gone','to Delhi','for an interview.'], e:0, fix:'One of my friends', full:'One of my friends has gone to Delhi for an interview.', rule:'“One of” is always followed by a plural noun.' },
    { parts:['The quality of','these mangoes','are not','very good.'], e:2, fix:'is not', full:'The quality of these mangoes is not very good.', rule:'The verb agrees with the head noun “quality”, not with “mangoes”.' },
    { parts:['Scarcely had I','reached the station','than the train','left.'], e:2, fix:'when the train', full:'Scarcely had I reached the station when the train left.', rule:'“Scarcely” and “hardly” are followed by “when”, not “than”.' },
    { parts:['He is senior','to me','by five years','in service.'], e:4, full:'He is senior to me by five years in service.', rule:'Latin comparatives — senior, junior, superior, prior — take “to”, not “than”.' },
    { parts:['Each of the students','have been','given','a new laptop.'], e:1, fix:'has been', full:'Each of the students has been given a new laptop.', rule:'“Each of” takes a singular verb.' },
    { parts:['I have been living','in this city','since five years','and I love it.'], e:2, fix:'for five years', full:'I have been living in this city for five years and I love it.', rule:'Use “for” with a period of time and “since” with a point in time.' }
  ],
  imp: [
    { pre:'If I ', hl:'was', post:' a bird, I would fly across the ocean.', o:['am','were','had been','No improvement'], a:1, rule:'Hypothetical conditions take the subjunctive “were” for every subject.' },
    { pre:'The manager, along with his assistants, ', hl:'have arrived', post:' for the meeting.', o:['has arrived','are arriving','have been arriving','No improvement'], a:0, rule:'“Along with”, “as well as” and “together with” do not change the number of the subject.' },
    { pre:'No sooner did the bell ring ', hl:'than', post:' the students rushed out.', o:['when','then','that','No improvement'], a:3, rule:'“No sooner” is correctly paired with “than”.' },
    { pre:'She ', hl:'did not knew', post:' the answer.', o:['does not knew','did not know','did not known','No improvement'], a:1, rule:'The auxiliary “did” is followed by the base form of the verb.' },
    { pre:'I look forward to ', hl:'meet you', post:' soon.', o:['meet with you','have met you','meeting you','No improvement'], a:2, rule:'In “look forward to”, “to” is a preposition, so it takes a gerund (-ing).' }
  ],
  cloze: [
    { title:'On preparation', parts:['Success in competitive exams depends less on talent ', { o:['then','than','as','that'], a:1 }, ' on consistency. Aspirants who revise ', { o:['regular','regularity','regularly','regulate'], a:2 }, ' tend to retain far more. It is also ', { o:['wise','wisdom','wisely','wiser'], a:0 }, ' to attempt mock tests under timed conditions, as they ', { o:['conceal','remove','refuse','reveal'], a:3 }, ' weak areas early.'], rule:'Blank 1 completes “less … than”; blank 2 needs an adverb for “revise”; blank 3 an adjective after “is”; blank 4 a verb that fits the meaning.' },
    { title:'The railways', parts:['The Indian Railways is one of the largest networks in the world. Every day it ', { o:['brings','carries','bears','holds'], a:1 }, ' more than twenty million passengers. For many families it is the only ', { o:['expensive','luxurious','affordable','optional'], a:2 }, ' way to travel long distances. Over the years the network has been ', { o:['expanded','expanding','expand','expansion'], a:0 }, ' to remote regions, ', { o:['because','unless','therefore','though'], a:3 }, ' punctuality remains a challenge.'], rule:'Collocation (“carries passengers”), context (“only … way” for families), passive voice (“has been expanded”) and a contrast connector (“though”).' }
  ],
  rcP: {
    gw:{ title:'Water beneath the fields', text:'India draws more groundwater than any other country, and nearly two-thirds of its irrigated farmland depends on it. The shift began in the 1970s, when subsidised electricity made it cheap to run tube-wells around the clock. Farmers gained independence from erratic canal supplies, and yields rose sharply. But the same subsidy removed any incentive to pump carefully. In parts of Punjab and Rajasthan, water tables now fall by more than a metre a year. Recharge programmes such as check dams and rooftop harvesting have shown promise at the village level, yet they cannot keep pace unless pricing changes too. The challenge, therefore, is less technical than political.' },
    dl:{ title:'Beyond access', text:'A smartphone in every pocket does not guarantee a digitally literate population. Many first-time users can make video calls yet struggle to recognise a fraudulent link or to judge whether a forwarded news item is reliable. Literacy, in the digital sense, is the ability to evaluate information, not merely to access it. Schools have begun adding such skills to their curricula, but most adults learn through trial and error — sometimes at considerable cost. Public campaigns that use simple, local-language examples have proved more effective than lengthy advisories.' }
  },
  rc: [
    { p:'gw', q:'Why did groundwater use expand from the 1970s?', o:['Canals were shut down','Subsidised electricity made pumping cheap','Rainfall declined sharply','Tube-wells were banned elsewhere'], a:1, m:'The passage links the shift directly to subsidised electricity for tube-wells.' },
    { p:'gw', q:'The author believes the main obstacle to solving the problem is', o:['a lack of technology','low crop yields','the political will to change pricing','a shortage of check dams'], a:2, m:'The final line: the challenge is “less technical than political”.' },
    { p:'gw', q:'The word “erratic”, as used in the passage, most nearly means', o:['unpredictable','generous','polluted','ancient'], a:0, m:'Erratic canal supplies are irregular and unreliable.' },
    { p:'dl', q:'According to the passage, digital literacy is primarily about', o:['owning a smartphone','making video calls','evaluating information','learning English'], a:2, m:'The passage defines it as the ability to evaluate information, not merely access it.' },
    { p:'dl', q:'Which approach does the author find most effective for adults?', o:['Lengthy advisories','Simple, local-language campaigns','School curricula','Trial and error'], a:1, m:'Local-language campaigns “have proved more effective than lengthy advisories”.' },
    { p:'dl', q:'The tone of the passage is best described as', o:['alarmist','analytical','humorous','indifferent'], a:1, m:'It defines, compares and weighs evidence without exaggeration — analytical.' }
  ],
  voc: {
    syn: [
      { w:'Ephemeral', o:['Eternal','Transient','Robust','Lucid'], a:1, m:'Lasting a very short time.', x:'Fame on social media is often ephemeral.' },
      { w:'Candid', o:['Frank','Secretive','Timid','Careless'], a:0, m:'Truthful and straightforward.', x:'She gave a candid account of her failures.' },
      { w:'Obstinate', o:['Flexible','Obedient','Stubborn','Anxious'], a:2, m:'Refusing to change one’s opinion.', x:'The obstinate clerk refused to accept the form.' },
      { w:'Abate', o:['Intensify','Subside','Abandon','Obey'], a:1, m:'To become less intense.', x:'The storm abated by evening.' },
      { w:'Benevolent', o:['Cruel','Wealthy','Proud','Kind'], a:3, m:'Well-meaning and generous.', x:'A benevolent donor funded the library.' }
    ],
    ant: [
      { w:'Frugal', o:['Thrifty','Extravagant','Careful','Simple'], a:1, m:'Frugal means economical with money; the opposite is extravagant.', x:'He lived a frugal life to save for his exams.' },
      { w:'Verbose', o:['Wordy','Loud','Concise','Clear'], a:2, m:'Verbose means using too many words; the opposite is concise.', x:'The verbose report was cut to two pages.' },
      { w:'Amiable', o:['Friendly','Hostile','Polite','Gentle'], a:1, m:'Amiable means friendly and pleasant; the opposite is hostile.', x:'The amiable officer answered every query.' },
      { w:'Zenith', o:['Peak','Summit','Nadir','Apex'], a:2, m:'Zenith is the highest point; nadir is the lowest.', x:'His career reached its zenith in 2019.' },
      { w:'Opaque', o:['Transparent','Dark','Solid','Thick'], a:0, m:'Opaque means not see-through; the opposite is transparent.', x:'The selection process was opaque to applicants.' }
    ],
    idiom: [
      { w:'A bolt from the blue', o:['A sudden, unexpected event','A stroke of lightning','A long-awaited result','A clear sky'], a:0, m:'Something completely unexpected.', x:'The transfer order came as a bolt from the blue.' },
      { w:'To burn the midnight oil', o:['To waste resources','To work late into the night','To start a fire','To be very angry'], a:1, m:'To stay up late working or studying.', x:'Aspirants burn the midnight oil before the mains.' },
      { w:'To let the cat out of the bag', o:['To free someone','To create confusion','To reveal a secret','To take a risk'], a:2, m:'To reveal a secret, usually by mistake.', x:'He let the cat out of the bag about the surprise.' },
      { w:'To be in the same boat', o:['To travel together','To agree completely','To compete fiercely','To share the same difficult situation'], a:3, m:'To face the same problem as others.', x:'After the exam was postponed, every candidate was in the same boat.' }
    ],
    prov: [
      { w:'Barking dogs seldom bite.', o:['Dogs are dangerous','Those who threaten loudly rarely act','Noise keeps danger away','Silence is golden'], a:1, m:'People who make loud threats seldom carry them out.', x:'Ignore his threats — barking dogs seldom bite.' },
      { w:'Too many cooks spoil the broth.', o:['Too many people handling a task ruin it','Cooking needs skill','Food should be shared','Teamwork always helps'], a:0, m:'When too many people are involved, the result suffers.', x:'The twelve-member committee proved that too many cooks spoil the broth.' },
      { w:'A stitch in time saves nine.', o:['Tailoring is a useful skill','Time is money','Timely action prevents bigger problems','Hard work pays off'], a:2, m:'Fixing a small problem early avoids a bigger one later.', x:'Revise weak topics now — a stitch in time saves nine.' },
      { w:'Empty vessels make the most noise.', o:['Poor people complain the most','Noise is annoying','Silence hides wisdom','Those with the least knowledge talk the most'], a:3, m:'The least knowledgeable are often the loudest.', x:'He boasts constantly; empty vessels make the most noise.' }
    ],
    ows: [
      { w:'One who knows everything', o:['Omnipotent','Omniscient','Omnipresent','Optimist'], a:1, m:'Omniscient = all-knowing. Omnipotent = all-powerful; omnipresent = present everywhere.', x:'No examiner is omniscient.' },
      { w:'Abnormal fear of heights', o:['Hydrophobia','Claustrophobia','Acrophobia','Xenophobia'], a:2, m:'Acrophobia. Hydro- = water, claustro- = closed spaces, xeno- = foreigners.', x:'Her acrophobia kept her off the rooftop.' },
      { w:'A person indifferent to pleasure and pain', o:['Stoic','Cynic','Hedonist','Ascetic'], a:0, m:'Stoic. A hedonist seeks pleasure; an ascetic renounces it.', x:'He remained stoic through the interview.' },
      { w:'Government by the wealthy', o:['Autocracy','Theocracy','Bureaucracy','Plutocracy'], a:3, m:'Plutocracy. Autocracy = rule by one; theocracy = rule by religious leaders.', x:'Critics called the regime a plutocracy.' }
    ],
    spell: [
      { w:'A place to stay', o:['Accomodation','Accommodation','Acommodation','Accommadation'], a:1, m:'Double “c”, double “m”: accommodation.', x:'Hostel accommodation is provided to trainees.' },
      { w:'Got from someone', o:['Recieved','Receeved','Received','Riceived'], a:2, m:'“i before e, except after c” — received.', x:'I received the admit card yesterday.' },
      { w:'A formal promise', o:['Guarantee','Gaurantee','Guarentee','Garantee'], a:0, m:'g-u-a-r-a-n-t-e-e.', x:'The warranty is a guarantee of repair.' },
      { w:'Playfully naughty', o:['Mischievious','Mischevous','Mischeivous','Mischievous'], a:3, m:'Three syllables, no extra “i”: mis-chie-vous.', x:'The mischievous child hid the keys.' },
      { w:'Took place', o:['Occured','Ocurred','Occurred','Occurrd'], a:2, m:'Double “c”, double “r”: occurred.', x:'The error occurred during data entry.' }
    ]
  },
  ce: [
    { s:'I am having two brothers.', fix:'I have two brothers.', tag:'Tense', rule:'Stative verbs like have (possess), know and believe are not used in continuous tenses.' },
    { s:'He is married with my cousin.', fix:'He is married to my cousin.', tag:'Preposition', rule:'One is “married to” someone — never “married with”.' },
    { s:'The furniture in this room is expensive.', fix:null, tag:'Uncountable nouns', rule:'Furniture is uncountable and takes a singular verb — never “furnitures”.' },
    { s:'Kindly revert back at the earliest.', fix:'Kindly reply at the earliest.', tag:'Indianism', rule:'“Revert” means to return to an earlier state. For replies use “reply”; “back” is redundant.' },
    { s:'She is more smarter than her sister.', fix:'She is smarter than her sister.', tag:'Comparison', rule:'Never combine “more” with an -er comparative.' },
    { s:'I prefer tea to coffee.', fix:null, tag:'Preposition', rule:'“Prefer” is followed by “to”, not “than”.' },
    { s:'Let us discuss about the plan.', fix:'Let us discuss the plan.', tag:'Redundancy', rule:'“Discuss” is transitive and takes a direct object — no “about”.' }
  ],
  posTag: [
    { w:[['The','DET'],['clever','ADJ'],['fox','N'],['quickly','ADV'],['jumped','V'],['over','PREP'],['the','DET'],['lazy','ADJ'],['dog.','N']], rule:'Articles (a, an, the) are determiners. “Quickly” modifies the verb, so it is an adverb.' },
    { w:[['Wow!','INTJ'],['She','PRON'],['sang','V'],['beautifully','ADV'],['and','CONJ'],['everyone','PRON'],['cheered.','V']], rule:'“Everyone” is an indefinite pronoun; “and” joins two clauses, so it is a conjunction.' },
    { w:[['They','PRON'],['walked','V'],['slowly','ADV'],['through','PREP'],['the','DET'],['old','ADJ'],['market.','N']], rule:'A preposition (“through”) links a noun phrase to the rest of the sentence.' },
    { w:[['The','DET'],['early','ADJ'],['bird','N'],['catches','V'],['the','DET'],['worm,','N'],['but','CONJ'],['the','DET'],['late','ADJ'],['bird','N'],['goes','V'],['hungry.','ADJ']], rule:'After a linking verb like “goes”, “hungry” describes the subject — an adjective, not an adverb.' }
  ],
  posMis: [
    { w:['She','sings','very','good.'], e:3, fix:'well', pos:'Adjective → Adverb', full:'She sings very well.', rule:'“Good” is an adjective; to modify the verb “sings” use the adverb “well”.' },
    { w:['He','gave','me','some','useful','advise.'], e:5, fix:'advice', pos:'Verb → Noun', full:'He gave me some useful advice.', rule:'“Advise” is a verb; the noun is “advice” (uncountable).' },
    { w:['He','behaved','very','rude','at','the','meeting.'], e:3, fix:'rudely', pos:'Adjective → Adverb', full:'He behaved very rudely at the meeting.', rule:'An adverb must modify the verb “behaved”; “rude” is an adjective.' },
    { w:['I','feel','badly','about','the','delay.'], e:2, fix:'bad', pos:'Adverb → Adjective', full:'I feel bad about the delay.', rule:'Linking verbs (feel, seem, look) take an adjective complement: “feel bad”.' },
    { w:['Success','depends','on','proper','execute.'], e:4, fix:'execution', pos:'Verb → Noun', full:'Success depends on proper execution.', rule:'After the adjective “proper”, a noun is needed: “execution”, not the verb “execute”.' }
  ],
  sc: {
    build: [
      { task:'Arrange the words into a correct sentence', t:['approved','the','policy','has','new','government','the'], ans:['The government has approved the new policy.'], note:'Subject → auxiliary + past participle → object.' },
      { task:'Arrange the words into a correct sentence', t:['I','apologise','if','would','were','I','you'], ans:['If I were you, I would apologise.','I would apologise if I were you.'], note:'The subjunctive “were” is used for hypothetical conditions with every subject.' },
      { task:'Arrange the words into a correct sentence', t:['had','when','hardly','left','we','it','rain','began','to'], ans:['Hardly had we left when it began to rain.'], note:'“Hardly” at the start triggers inversion (“had we left”) and pairs with “when”.' }
    ],
    voice: [
      { task:'Convert to passive voice', source:'Ravi wrote the letter.', t:['by','letter','the','written','was','Ravi'], ans:['The letter was written by Ravi.'], note:'Object becomes subject; simple past → was/were + past participle.' },
      { task:'Convert to passive voice', source:'They are building a new bridge.', t:['a','built','being','is','bridge','new','by','them'], ans:['A new bridge is being built by them.'], note:'Present continuous → is/are being + past participle.' },
      { task:'Convert to passive voice', source:'Who broke the window?', t:['by','was','the','broken','whom','window'], ans:['By whom was the window broken?'], note:'“Who” becomes “by whom”, and question order is kept.' }
    ],
    speech: [
      { task:'Convert to indirect speech', source:'He said, “I am tired.”', t:['he','said','was','that','he','tired'], ans:['He said that he was tired.'], note:'Past reporting verb: “am” → “was”, and “I” → “he”.' },
      { task:'Convert to indirect speech', source:'She said to me, “Please help me.”', t:['me','requested','to','she','help','her'], ans:['She requested me to help her.'], note:'Requests become “requested/asked + object + to-infinitive”; “please” is dropped.' },
      { task:'Convert to indirect speech', source:'The teacher said, “The earth moves round the sun.”', t:['said','the','that','moves','the','round','teacher','earth','the','sun'], ans:['The teacher said that the earth moves round the sun.'], note:'Universal truths keep their original tense.' }
    ]
  }
};
