"""QRE-ENG-A part 1: foundation RC case sets (7 passages x 5 Q)."""
from enga_common import caseset

F = "foundation"
P = {}

P["F0"] = """Five years ago, most shopkeepers in Rampur's weekly market dealt only in cash. Today, a laminated QR code hangs beside almost every stall, from the vegetable seller's to that of the man who repairs umbrellas. The change did not arrive because traders suddenly fell in love with technology. It arrived because customers, many of them young workers returning from cities, stopped carrying notes and asked to pay by phone. A trader who refused risked losing a sale to the stall next door.

The benefits are real. Traders no longer need to keep large amounts of change, and the daily trip to deposit cash at the bank has become less frequent. A digital record of sales has also helped some of them obtain small loans, because lenders can now see how much money actually passes through a shop.

Yet the shift is not free of problems. Network failures on crowded market days can leave a payment hanging for minutes, and older traders complain that they cannot always tell whether money has actually reached their accounts. A few have been cheated by customers who show a fake confirmation screen. For these reasons, many shopkeepers still keep a cash box under the counter, treating the phone as a convenient partner rather than a complete replacement."""

P["F1"] = """On a summer afternoon, the difference between a tree-lined street and a bare one can be felt through the soles of one's shoes. Surfaces of concrete and asphalt absorb sunlight during the day and release the stored heat slowly after dark, which is why many city neighbourhoods stay uncomfortably warm long after sunset. Trees counter this in two ways. Their canopies shade the ground, and the water that evaporates from their leaves cools the surrounding air, much as sweat cools the skin.

City planners have long treated trees as decoration, to be planted once a road is finished and removed whenever it needs widening. That view is slowly changing. Studies in several cities have found that neighbourhoods with dense tree cover record lower night-time temperatures and fewer heat-related hospital visits than comparable areas without them. Some municipal bodies now count trees as part of their basic infrastructure, alongside drains and streetlights.

Planting saplings, however, is the easy part. A young tree needs regular watering, protection from cattle and space for its roots, and many saplings planted with great publicity die within two years. A city that wants cooler streets must therefore budget for years of care, not just for a single planting drive."""

P["F2"] = """For decades, millets such as ragi, jowar and bajra were dismissed as 'coarse grains', food for those who could not afford rice or wheat. Government procurement favoured the two big cereals, and as incomes rose, many families abandoned millets altogether. The result was a diet that grew richer in calories but, in many households, poorer in fibre, iron and other minerals.

Millets deserve a second look. They grow on poor soils, need far less water than paddy and tolerate heat better than wheat, qualities that matter more each year as rainfall becomes less predictable. Nutritionists point out that they release sugar into the blood more slowly than polished rice, which may help people managing diabetes.

The recent enthusiasm for millets, however, carries its own risk. Supermarket shelves now display millet cookies and noodles, often mixed with refined flour and sugar and sold at high prices to urban buyers. Such products may do little for health and even less for the small farmers who grow the grain. If the revival is to mean anything, millets must return to ordinary kitchens as affordable staples, supported by fair procurement prices and inclusion in school meals, rather than remain a fashionable snack for the few."""

P["F3"] = """When a group of twelve women in a village first began saving fifty rupees each month, their husbands laughed. Three years later, the same self-help group had lent money to its members for a sewing machine, a buffalo and two children's school fees, and had repaid a bank loan ahead of schedule. Stories like this explain why self-help groups have become one of the most widely praised tools for bringing rural women into the formal financial system.

The model works because it replaces collateral with trust. Members know one another, meet regularly and feel responsible for the group's reputation, so repayment rates are often higher than those of individual borrowers. Banks, in turn, find it cheaper to lend to one group than to twelve separate customers.

Success, however, should not be confused with transformation. Many groups remain stuck at small loans for consumption and never move on to building businesses that could lift their members out of poverty. Training in book-keeping, links to markets and access to larger loans are often missing. Without them, a self-help group can become a useful savings club but little more."""

P["F4"] = """A vaccine is only as good as the journey it takes. Most vaccines must be kept between two and eight degrees Celsius from the moment they leave the factory until they are injected, and even a few hours of heat or freezing can make them useless without any visible change. This unbroken sequence of refrigerated storage and transport is known as the cold chain.

In a large country with patchy electricity, maintaining the cold chain is a formidable task. Vaccines travel from national stores to state and district depots and then, in insulated boxes packed with ice, to village health centres. Health workers record temperatures at every stage, and many storage points now use digital sensors that send alerts when a refrigerator warms up.

Technology helps, but people matter more. A sensor can raise an alarm; someone must still respond to it. A solar refrigerator can work without the grid; someone must still keep its panels clean. Experts who study immunisation programmes often find that failures occur not because equipment is absent but because it is poorly maintained or its warnings ignored. Investing in trained, adequately staffed health workers is therefore as important as buying new machines."""

P["F5"] = """In an age when almost any book can be downloaded onto a phone, it is tempting to regard the public library as a relic. Several municipal libraries in Indian cities have seen their budgets cut on precisely this argument, their reading rooms left to gather dust while funds go to more visible projects.

The argument misreads what libraries do. For a student from a crowded one-room home, a library offers what no phone can: a quiet, well-lit place to study for hours. For a job seeker without a printer or reliable internet, it may be the only free place to fill in an online application. For elderly residents living alone, a reading room is also a place to meet others. The books, in other words, are only part of the service.

Some cities have understood this. Libraries that have extended their hours, added computer terminals and set aside space for students preparing for examinations report a steady rise in visitors, many of them young. Their experience suggests that the problem was never that people had stopped needing libraries, but that libraries had stopped offering what people needed."""

P["F6"] = """For farmers who depend on diesel pumps, every irrigation is a cash expense, and a sudden rise in fuel prices can wipe out a season's profit. Solar pumps promise an escape. Once installed, they draw water using free sunlight, cost little to run and produce no smoke. With government subsidies covering a large share of the purchase price, lakhs of farmers have switched in recent years.

The benefits are clear, but so is a hidden danger. A diesel pump's running cost acts as a natural brake: farmers pump only as much water as they must. When pumping becomes almost free, that brake disappears. In regions where groundwater is already falling, cheap solar pumping could hasten the day when wells run dry.

Some states have tried a clever remedy. Farmers are connected to the grid and paid for any surplus electricity their panels generate. Water left in the ground thus becomes money in the bank, and a farmer has a reason to pump only what the crop needs. Such schemes are still young, and their payments must be prompt and fair if farmers are to trust them. But they show that a good technology works best when the incentives around it are designed with equal care."""


def add_all(B):
    caseset(B, "ENA-RCF-0", F, P["F0"], [
        ("DET", "L1", "According to the passage, why did traders in Rampur begin accepting digital payments?",
         "Customers stopped carrying cash and wanted to pay by phone",
         [("Traders were attracted by the novelty of the technology", "reversed - the passage says the change did not come from traders loving technology"),
          ("Banks required every trader to display a QR code", "out of scope - no bank requirement is mentioned"),
          ("Keeping loose change had become too costly for traders", "distortion - reduced need for change is a later benefit, not the reason")],
         "Para 1: 'It arrived because customers ... stopped carrying notes and asked to pay by phone.'",
         "A benefit listed in para 2 is not the cause given in para 1."),
        ("INF", "L2", "Which of the following can be inferred about the small loans mentioned in the passage?",
         "Lenders value verifiable information about a shop's turnover",
         [("Lenders refuse loans to traders who deal only in cash", "extreme - the passage says records helped some traders, not that cash traders are refused"),
          ("Digital payments have made loans cheaper for all traders", "out of scope - loan cost is never discussed; 'all' is extreme"),
          ("Only young traders have been able to borrow money", "out of scope - age of borrowers is not linked to loans")],
         "Loans came 'because lenders can now see how much money actually passes through a shop' - so lenders value verifiable sales data.",
         "An inference must follow from the stated reason; 'refuse' and 'all' go beyond it."),
        ("MAIN", "L2", "Which of the following best expresses the central idea of the passage?",
         "Digital payments have spread in the market but have not wholly displaced cash",
         [("Technology has completely transformed the way small-town markets trade", "extreme - the last paragraph says cash boxes remain"),
          ("Older traders are being cheated through fake payment screens", "too narrow - one problem from para 3"),
          ("Young workers from cities are changing rural shopping habits", "too narrow - only the cause in para 1")],
         "Para 1 describes the spread, para 2 the benefits, para 3 the limits and the continued use of cash: spread without full replacement.",
         "'Completely' ignores the closing sentence."),
        ("SYN", "L1", "Which word is most similar in meaning to 'hanging' as used in the passage ('leave a payment hanging')?",
         "pending",
         [("dangling", "literal sense - physically suspended, not the contextual sense"),
          ("drooping", "physical sense - sagging, unrelated to an incomplete payment"),
          ("completed", "antonym - the payment is stuck, not finished")],
         "A payment left 'hanging' because of network failure is unresolved - pending.",
         "Do not pick the literal meaning of the word."),
        ("VOC", "L2", "The phrase 'treating the phone as a convenient partner rather than a complete replacement' means that shopkeepers are",
         "using digital payment alongside cash, not instead of it",
         [("sharing their phones with their business partners", "literal misreading of 'partner'"),
          ("preferring cash and refusing to accept phone payments", "reversed - they do accept phone payments"),
          ("planning to give up cash altogether in the near future", "reversed - the cash box is being kept")],
         "The phone works together with (partner) the cash box; it has not replaced cash.",
         "'Partner' is figurative here."),
    ], 180, 250)

    caseset(B, "ENA-RCF-1", F, P["F1"], [
        ("AE", "L2", "Which of the following, if true, would most strengthen the claim that tree cover reduces heat-related illness?",
         "Heat-related hospital visits fell where tree cover was added",
         [("Tree-lined streets are more popular with morning walkers", "irrelevant - popularity says nothing about illness"),
          ("Hospitals in greener areas tend to be better equipped", "weakens - offers another explanation for the difference"),
          ("Many saplings die because of cattle and a lack of water", "irrelevant - concerns sapling survival, not illness")],
         "A before-and-after fall in hospital visits where trees were added links trees to reduced illness directly.",
         "An alternative cause (better hospitals) weakens rather than strengthens."),
        ("INF", "L2", "It can be inferred that a city which plants many saplings but does not care for them will most likely",
         "gain little lasting relief from heat",
         [("see night temperatures rise sharply", "extreme - the passage predicts no sharp rise"),
          ("have to widen its roads more often", "out of scope - road widening is unrelated to sapling care"),
          ("reduce hospital visits within two years", "reversed - the saplings are likely to die within two years")],
         "Many uncared-for saplings die within two years, so the cooling benefit will not last.",
         "Do not stretch 'little benefit' into 'sharp rise'."),
        ("MAIN", "L1", "What is the main idea of the passage?",
         "Trees cool cities and must be maintained as infrastructure",
         [("Concrete and asphalt are the main causes of urban heat", "too narrow - only the opening explanation"),
          ("Most saplings planted in cities die within two years", "distortion - the passage says 'many', and this is a detail"),
          ("Road widening is the chief reason cities lose their trees", "out of scope - mentioned only in passing")],
         "The passage explains how trees cool, reports the shift to seeing them as infrastructure and ends by demanding long-term care.",
         "A detail from one paragraph is not the main idea."),
        ("SYN", "L1", "Which word is closest in meaning to 'counter' as used in 'Trees counter this in two ways'?",
         "offset",
         [("tally", "wrong sense - 'counter' as something that counts"),
          ("worsen", "reversed - trees reduce heat"),
          ("imitate", "unrelated meaning")],
         "Trees work against (offset) the heat stored by concrete.",
         "Choose the verb sense 'act against'."),
        ("VOC", "L2", "In the passage, 'basic infrastructure' refers to",
         "essential public services a city must maintain",
         [("decorative features added after roads are built", "reversed - that is the old view the passage rejects"),
          ("large construction projects such as flyovers", "distortion - the examples are drains and streetlights"),
          ("the simplest and cheapest kinds of public works", "misreads 'basic' as 'simple'")],
         "Trees are counted 'alongside drains and streetlights' - essential services.",
         "'Basic' here means fundamental, not simple."),
    ], 180, 250)

    caseset(B, "ENA-RCF-2", F, P["F2"], [
        ("AE", "L3", "Which of the following, if true, would most weaken the author's hope that millets can return as affordable staples?",
         "Farmers cannot grow millets profitably at affordable prices",
         [("Urban buyers happily pay high prices for millet snacks", "does not weaken - consistent with the passage and irrelevant to staples"),
          ("Millets need much less water than paddy in most regions", "strengthens - supports the case for millets"),
          ("Several states have already added millets to school meals", "strengthens - one of the author's proposed supports")],
         "If millets cannot be grown profitably at affordable prices, the author's goal of cheap everyday staples becomes unworkable.",
         "Options that support the author strengthen, not weaken."),
        ("TONE", "L2", "The author's attitude towards the packaged millet cookies and noodles is best described as",
         "sceptical",
         [("enthusiastic", "reversed - the author doubts their value"),
          ("indifferent", "wrong - the author clearly takes a position"),
          ("contemptuous", "extreme - the criticism is measured ('may do little')")],
         "'Such products may do little for health and even less for the small farmers' - doubtful, not hostile.",
         "Measured doubt is scepticism, not contempt."),
        ("MAIN", "L2", "Which of the following best states the central idea of the passage?",
         "Millets merit revival as affordable staples, not as costly fashionable snacks",
         [("Millets were abandoned because government procurement favoured rice and wheat", "too narrow - only the history in para 1"),
          ("Millets are the best food available for people managing diabetes", "extreme - the passage says they 'may help'"),
          ("Supermarkets have made millets popular among urban consumers", "partial and not endorsed by the author")],
         "The passage argues millets deserve revival but warns against the snack trend; the conclusion calls for affordable staples.",
         "The conclusion of the final paragraph carries the main idea."),
        ("SYN", "L1", "Which word is most similar in meaning to 'dismissed' as used in the passage?",
         "disregarded",
         [("discharged", "wrong sense - dismissal from a job"),
          ("welcomed", "antonym"),
          ("released", "wrong sense - dismissing a class or assembly")],
         "Millets were 'dismissed as coarse grains' - treated as unworthy, disregarded.",
         "Keep the sense of rejecting an idea."),
        ("VOC", "L2", "As used in the passage, the word 'staples' means",
         "basic foods eaten regularly",
         [("wire fasteners for paper", "wrong dictionary sense"),
          ("expensive speciality items", "reversed - the author wants affordable everyday foods"),
          ("grains stored for emergencies", "distortion - not about storage")],
         "'Affordable staples' in 'ordinary kitchens' are everyday basic foods.",
         "Context rules out the stationery meaning."),
    ], 180, 250)

    caseset(B, "ENA-RCF-3", F, P["F3"], [
        ("AE", "L3", "The claim that 'the model works because it replaces collateral with trust' would be most weakened if it were found that",
         "groups of near-strangers repay loans just as reliably",
         [("banks find lending to groups cheaper than to individuals", "consistent - this is stated and does not touch the trust claim"),
          ("many groups spend their loans mainly on consumption", "irrelevant - about loan use, not repayment"),
          ("close-knit groups repay more reliably than strangers do", "strengthens - supports trust as the cause")],
         "If groups without mutual trust repay equally well, trust cannot be what makes the model work.",
         "Removing the proposed cause without changing the effect weakens a causal claim."),
        ("TONE", "L2", "The author's attitude towards self-help groups is best described as",
         "appreciative but cautionary",
         [("wholly dismissive", "reversed - the author praises their record"),
          ("uncritically celebratory", "ignores the warning in the last paragraph"),
          ("detached and uninterested", "wrong - the author evaluates them")],
         "Paragraphs 1-2 praise; paragraph 3 warns that success is not transformation.",
         "Balance of praise and caution rules out one-sided options."),
        ("DET", "L1", "According to the passage, why do banks prefer lending to groups?",
         "One group loan costs less to handle than many small ones",
         [("Groups always pledge their land as collateral for loans", "reversed - the model replaces collateral"),
          ("Groups borrow only for productive business purposes", "reversed - many borrow for consumption"),
          ("The government guarantees every group loan in full", "out of scope - no guarantee is mentioned")],
         "'Banks ... find it cheaper to lend to one group than to twelve separate customers.'",
         "Stick to the stated reason."),
        ("SYN", "L1", "Which word is most nearly OPPOSITE in meaning to 'praised' as used in the passage?",
         "criticised",
         [("applauded", "synonym, not antonym"),
          ("ignored", "absence of attention, not the opposite of praise"),
          ("rewarded", "related positive idea, not an opposite")],
         "The opposite of speaking well of something is speaking badly of it - criticised.",
         "'Ignored' is neutral, not opposite."),
        ("VOC", "L2", "The phrase 'stuck at small loans' suggests that many groups are",
         "unable to progress beyond small loans",
         [("legally barred from taking small loans", "distortion - no legal bar is mentioned"),
          ("burdened with small loans they cannot repay", "out of scope - repayment is described as good"),
          ("content to take small loans purely by choice", "distortion - the passage blames missing training and access")],
         "They 'never move on' to building businesses because support is missing - they cannot progress.",
         "'Stuck' implies inability, not choice."),
    ], 180, 250)

    caseset(B, "ENA-RCF-4", F, P["F4"], [
        ("AE", "L2", "Which of the following, if true, would best support the author's view that people matter more than technology in the cold chain?",
         "Most spoiled batches came from sites that ignored alarms",
         [("Digital sensors have become cheaper in recent years", "irrelevant - cost of equipment is not the issue"),
          ("Solar refrigerators work well in villages without grid power", "supports technology, not the role of people"),
          ("Some vaccines tolerate short periods outside the cold chain", "out of scope - vaccine properties")],
         "If spoilage traces to ignored alarms, human response, not equipment, is decisive.",
         "Evidence about equipment performance does not show that people matter more."),
        ("TONE", "L1", "The tone of the passage is mainly",
         "explanatory",
         [("alarmist", "extreme - no panic is conveyed"),
          ("nostalgic", "out of scope - no longing for the past"),
          ("sarcastic", "wrong - no mockery")],
         "The passage explains what the cold chain is, how it works and what matters most.",
         "A recommendation at the end does not make the tone alarmist."),
        ("DET", "L1", "According to the passage, a vaccine damaged by heat",
         "may look exactly the same as a usable one",
         [("changes colour and can be discarded easily", "reversed - there is no visible change"),
          ("can be restored by putting it back in a refrigerator", "out of scope - not stated"),
          ("loses its effect only after several days", "reversed - a few hours can ruin it")],
         "'... can make them useless without any visible change.'",
         "'Without any visible change' is the key phrase."),
        ("INF", "L2", "It can be inferred from the passage that buying more solar refrigerators, by itself, would",
         "not ensure a reliable cold chain",
         [("make health workers unnecessary", "reversed - someone must clean the panels"),
          ("eliminate all vaccine wastage", "extreme"),
          ("cause vaccines to freeze more often", "out of scope")],
         "Failures come from poor maintenance and ignored warnings, so equipment alone is not enough.",
         "Reject 'all' and 'unnecessary'."),
        ("VOC", "L2", "In the passage, 'patchy electricity' means",
         "a power supply that is uneven and unreliable",
         [("electricity produced from patches of solar panels", "literal misreading of 'patchy'"),
          ("power that is too expensive for villagers", "out of scope - cost is not mentioned"),
          ("electricity that is available only in cities", "extreme distortion")],
         "Patchy = irregular in quality or availability; hence the need for ice boxes and solar fridges.",
         "Do not read 'patchy' literally."),
    ], 180, 250)

    caseset(B, "ENA-RCF-5", F, P["F5"], [
        ("AE", "L3", "The author's conclusion in the last sentence would be most weakened if",
         "visits fell even at libraries that added the new services",
         [("most visitors to renovated libraries were young students", "consistent - matches the passage"),
          ("e-books have become cheaper than printed books", "irrelevant - does not address what libraries offer"),
          ("some libraries could not afford computer terminals", "irrelevant - says nothing about demand")],
         "The author concludes that people still need libraries if libraries adapt; falling visits despite adaptation would undercut this.",
         "Consistent facts cannot weaken a conclusion."),
        ("TONE", "L2", "The author's attitude towards those who regard the public library as a relic is",
         "critical",
         [("supportive", "reversed"),
          ("mocking", "extreme - the author argues, does not ridicule"),
          ("apologetic", "out of scope")],
         "'The argument misreads what libraries do' - a reasoned rejection.",
         "Disagreement without ridicule is criticism, not mockery."),
        ("DET", "L1", "Which of the following is NOT mentioned in the passage as something a library offers?",
         "home delivery of books",
         [("a quiet place to study", "mentioned - for students from crowded homes"),
          ("free access to the internet", "mentioned - for job seekers without internet"),
          ("a place for elderly people to meet", "mentioned - for elderly residents")],
         "Paragraph 2 lists study space, free online access and a meeting place; delivery is never mentioned.",
         "In NOT questions, tick off each listed item first."),
        ("INF", "L2", "It can be inferred that the budget cuts mentioned in the passage were based on",
         "an assumption that phones had replaced libraries",
         [("evidence that library visits had increased sharply", "reversed"),
          ("complaints from students about noise", "out of scope"),
          ("a shortage of books in reading rooms", "out of scope")],
         "Budgets were cut 'on precisely this argument' - that books can be downloaded onto phones.",
         "Link 'this argument' back to the first sentence."),
        ("MAIN", "L2", "Which of the following best captures the main idea of the passage?",
         "Libraries stay relevant when they adapt to what their users need",
         [("Digital books have made public libraries largely obsolete", "reversed - the view the author rejects"),
          ("Municipal budgets should fund libraries instead of other projects", "extreme - not argued"),
          ("Students preparing for examinations are libraries' main users", "distortion - one group among several")],
         "The passage rejects the 'relic' view and ends by saying libraries lost users only when they stopped offering what people needed.",
         "The rejected view is not the main idea."),
    ], 180, 250)

    caseset(B, "ENA-RCF-6", F, P["F6"], [
        ("TONE", "L2", "The author's attitude towards solar pumps is best described as",
         "cautiously supportive",
         [("unreservedly enthusiastic", "ignores the 'hidden danger' the author raises"),
          ("firmly opposed", "reversed - the benefits are called clear"),
          ("wholly indifferent", "wrong - the author evaluates them")],
         "Benefits are 'clear', but a 'hidden danger' needs incentives - support with caution.",
         "Balance rules out both extremes."),
        ("DET", "L1", "According to the passage, the running cost of a diesel pump",
         "keeps farmers from pumping excess water",
         [("is largely covered by government subsidies", "reversed - subsidies cover solar pump purchases"),
          ("has fallen sharply in recent years", "reversed - fuel price rises are the worry"),
          ("is lower than that of a solar pump", "reversed - solar pumps cost little to run")],
         "'A diesel pump's running cost acts as a natural brake: farmers pump only as much water as they must.'",
         "Subsidies attach to solar purchase, not diesel running cost."),
        ("INF", "L3", "It can be inferred that grid-connected schemes would fail to save water if",
         "payments for surplus electricity were delayed or too small",
         [("diesel prices rose sharply in the same season", "irrelevant to the solar incentive"),
          ("more farmers in the area installed solar panels", "irrelevant - does not remove the incentive"),
          ("groundwater levels recovered after good monsoon rains", "out of scope")],
         "The scheme saves water only by making unused water valuable; unreliable payments remove that reason ('must be prompt and fair').",
         "Identify the mechanism, then ask what breaks it."),
        ("MAIN", "L2", "Which of the following best expresses the main idea of the passage?",
         "Solar pumps help farmers but need incentives against overuse",
         [("Diesel pumps should be banned to protect groundwater", "out of scope and extreme"),
          ("Farmers should sell electricity instead of growing crops", "distortion of the grid scheme"),
          ("Subsidies have made solar pumps popular with farmers", "too narrow - only para 1")],
         "Benefits (para 1), danger of overuse (para 2), incentive-based remedy (para 3).",
         "The concluding line ties technology to incentives."),
        ("SYN", "L1", "Which word is closest in meaning to 'hasten' as used in the passage?",
         "accelerate",
         [("postpone", "antonym"),
          ("predict", "unrelated meaning"),
          ("announce", "unrelated meaning")],
         "Cheap pumping could bring the day of dry wells sooner - accelerate.",
         "Substitute each option in the sentence."),
    ], 180, 250)
