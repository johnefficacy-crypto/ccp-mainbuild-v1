"""QRE-GK-A part 4 — Miscellaneous (8 microtopics x 15)."""
from gka_h import H


def add_all(B):
    h = H(B, "")
    F, S, N, M, C, A, Q = h.F, h.S, h.N, h.M, h.C, h.A, h.Q

    # ================= Awards and honours (durable aspects) =================
    h.topic("gk-awards-and-honours-", "Official prize websites (nobelprize.org, thebookerprizes.com, pulitzer.org); Ministry of I&B / Youth Affairs award rules")
    F("Who was the first Indian to win a Nobel Prize?",
      "Rabindranath Tagore", [("C. V. Raman", "Physics, 1930"), ("Mother Teresa", "Peace, 1979"), ("Hargobind Khorana", "Medicine, 1968")],
      "Tagore won the Nobel Prize in Literature in 1913 — the first for any Asian.", "Raman (1930) was the first Indian in science.")
    F("The Dadasaheb Phalke Award is India's highest award in the field of:",
      "Cinema", [("Literature", "Jnanpith Award"), ("Sports", "Khel Ratna"), ("Classical music", "Sangeet Natak Akademi awards")],
      "The award honours lifetime contribution to Indian cinema.", "Named after the maker of Raja Harishchandra (1913).")
    F("Who was the first recipient of the Jnanpith Award?",
      "G. Sankara Kurup", [("Tarasankar Bandopadhyay", "second recipient, 1966"), ("Kuvempu", "1967 recipient"),
                           ("Sumitranandan Pant", "1968 recipient")],
      "Malayalam poet G. Sankara Kurup received the first Jnanpith Award (1965) for Odakkuzhal.", "Tarasankar (Bengali) was the second.", lv="L2")
    F("The Ramon Magsaysay Award is presented in:",
      "The Philippines", [("Sweden", "Nobel prizes (except Peace)"), ("Norway", "Nobel Peace Prize"), ("Indonesia", "incorrect")],
      "The award, named after a Philippine President, is presented in Manila (since 1958).", "Often called 'Asia's Nobel'.")
    F("The Pulitzer Prizes are administered by:",
      "Columbia University", [("Harvard University", "incorrect"), ("Stanford University", "incorrect"), ("The Nobel Foundation", "administers Nobel prizes only")],
      "The Pulitzer Prizes, established by Joseph Pulitzer's will, are administered by Columbia University, New York (first awarded 1917).",
      "Pulitzer endowed Columbia's journalism school.", lv="L2")
    M("Nobel laureate", "Field of the prize",
      [("C. V. Raman", "Physics"), ("Hargobind Khorana", "Physiology or Medicine"), ("Amartya Sen", "Economic Sciences"),
       ("Venkatraman Ramakrishnan", "Chemistry")],
      "Ramakrishnan's prize (2009) was in Chemistry for ribosome structure, not Medicine.")
    C("Arrange the following Nobel Prizes in chronological order:",
      [("Rabindranath Tagore — Literature", 1913, "1913"), ("C. V. Raman — Physics", 1930, "1930"),
       ("Mother Teresa — Peace", 1979, "1979"), ("Amartya Sen — Economic Sciences", 1998, "1998")],
      "Mother Teresa (1979) precedes Sen (1998).")
    S("Consider the following statements about the Nobel Prizes:",
      [("They were first awarded in 1901.", True, "yes"),
       ("The prize in Economic Sciences was one of the five prizes named in Alfred Nobel's will.", False, "it was instituted by Sveriges Riksbank in 1968, first awarded 1969"),
       ("The Peace Prize is presented in Oslo.", True, "the others are presented in Stockholm")],
      "The Economics prize is a later addition.")
    M("Author", "Booker Prize-winning novel",
      [("Salman Rushdie", "Midnight's Children"), ("Arundhati Roy", "The God of Small Things"), ("Kiran Desai", "The Inheritance of Loss"),
       ("Aravind Adiga", "The White Tiger")],
      "Kiran Desai (2006) and Aravind Adiga (2008) are two years apart.", lv="L2")
    A("The 2022 International Booker Prize money for 'Tomb of Sand' was shared by Geetanjali Shree and Daisy Rockwell.",
      "The International Booker Prize is divided equally between the author and the translator.",
      True, True, True, "The prize rewards translated fiction and is split equally — hence the sharing.", "R explains A.")
    S("Consider the following statements about national sports awards:",
      [("The Rajiv Gandhi Khel Ratna was renamed the Major Dhyan Chand Khel Ratna in 2021.", True, "August 2021"),
       ("The Dronacharya Award is given to coaches.", True, "instituted 1985"),
       ("The Arjuna Award was instituted in 1961.", True, "yes")],
      "All three statements are correct.")
    A("The Fields Medal is awarded once every four years.",
      "It is presented at the International Congress of Mathematicians, which is held every four years.",
      True, True, True, "The medal's periodicity follows that of the ICM.", "R explains A.")
    M("Prize", "Field",
      [("Abel Prize", "Mathematics"), ("Turing Award", "Computer science"), ("Pritzker Prize", "Architecture"),
       ("Tyler Prize", "Environmental achievement")],
      "Abel and Fields are both mathematics prizes.")
    N("Consider the following statements about the Dadasaheb Phalke Award:",
      [("It was instituted in 1969.", True, "yes"), ("Its first recipient was Devika Rani.", True, "yes"),
       ("It is presented at the National Film Awards ceremony.", True, "yes"),
       ("It is named after the director of Raja Harishchandra (1913), India's first full-length feature film.", True, "yes")],
      "All four are correct.")
    A("The Right Livelihood Award is often called the 'Alternative Nobel Prize'.",
      "It is administered by the Nobel Foundation.",
      True, False, False, ["A is true.", "R is false: it is administered by the independent Right Livelihood Foundation (founded by Jakob von Uexkull, 1980)."],
      "An 'alternative' Nobel is by definition outside the Nobel system.")

    # ================= Books and authors (classics) =================
    h.topic("gk-books-and-authors", "Standard literary references; NCERT Hindi/English literature; publisher records")
    F("'Godan' was written by:",
      "Premchand", [("Jaishankar Prasad", "Kamayani"), ("Bhisham Sahni", "Tamas"), ("Phanishwar Nath Renu", "Maila Anchal")],
      "Godan (1936) is Premchand's last completed novel.", "All four are Hindi writers — match the work.")
    F("'Anandamath' was written by:",
      "Bankim Chandra Chattopadhyay", [("Sarat Chandra Chattopadhyay", "Devdas"), ("Rabindranath Tagore", "Gora"),
                                       ("Dinabandhu Mitra", "Nil Darpan")],
      "Anandamath (1882), which contains 'Vande Mataram', was written by Bankim Chandra.", "Two Chattopadhyays — Bankim vs Sarat.")
    F("'Wings of Fire' is the autobiography of:",
      "A. P. J. Abdul Kalam", [("Kuldip Nayar", "journalist"), ("Amartya Sen", "economist"), ("Khushwant Singh", "novelist")],
      "Wings of Fire (1999) was written by Kalam with Arun Tiwari.", "Kalam's other book is Ignited Minds.")
    F("'The Discovery of India' was written by:",
      "Jawaharlal Nehru", [("M. K. Gandhi", "My Experiments with Truth"), ("Maulana Abul Kalam Azad", "India Wins Freedom"),
                           ("S. Radhakrishnan", "Indian Philosophy")],
      "Nehru wrote it in Ahmednagar Fort prison (1944); published 1946.", "Nehru also wrote Glimpses of World History.")
    F("'Das Kapital' was written by:",
      "Karl Marx", [("Friedrich Engels", "co-author of the Communist Manifesto; edited later volumes"), ("V. I. Lenin", "wrote 'What Is to Be Done?'"),
                    ("Adam Smith", "The Wealth of Nations")],
      "Marx published volume I of Das Kapital in 1867.", "Engels edited volumes II and III after Marx's death.", lv="L2")
    M("Book", "Author",
      [("Gita Rahasya", "Bal Gangadhar Tilak"), ("Hind Swaraj", "M. K. Gandhi"), ("India Wins Freedom", "Maulana Abul Kalam Azad"),
       ("Annihilation of Caste", "B. R. Ambedkar")],
      "Gita Rahasya (Tilak) vs Hind Swaraj (Gandhi) — both nationalist classics.", lv="L2")
    M("Novel", "Author",
      [("Untouchable", "Mulk Raj Anand"), ("Kanthapura", "Raja Rao"), ("The Guide", "R. K. Narayan"), ("Train to Pakistan", "Khushwant Singh")],
      "Anand, Rao and Narayan are the three founding figures of the Indian English novel.")
    M("Book", "Author",
      [("Leviathan", "Thomas Hobbes"), ("The Prince", "Niccolò Machiavelli"), ("The Social Contract", "Jean-Jacques Rousseau"),
       ("The Wealth of Nations", "Adam Smith")],
      "Hobbes and Rousseau are both social-contract theorists; Leviathan is Hobbes'.", lv="L2")
    S("Consider the following statements:",
      [("'The Discovery of India' was written in Ahmednagar Fort prison.", True, "1944"),
       ("'Gita Rahasya' was written in Mandalay jail.", True, "during Tilak's imprisonment 1908–14"),
       ("'Hind Swaraj' was originally written in Gujarati.", True, "1909, later translated into English by Gandhi")],
      "All three statements are correct.")
    N("Consider the following pairs (work — author):",
      [("Kamayani — Jaishankar Prasad", True, "yes"), ("Madhushala — Harivansh Rai Bachchan", True, "yes"),
       ("Rashmirathi — Ramdhari Singh Dinkar", True, "yes"), ("Tamas — Premchand", False, "Tamas is by Bhisham Sahni")],
      "Tamas (Partition novel) is Bhisham Sahni's.", pairs=True)
    A("'Vande Mataram' first appeared in a novel.",
      "The Constituent Assembly adopted 'Vande Mataram' as the National Song in 1950.",
      True, True, False, ["Both statements are true (A: it appeared in Anandamath, 1882).", "Its later adoption as National Song does not explain where it first appeared."],
      "A later event cannot explain an earlier one.")
    C("Arrange the following works in the order of their first publication:",
      [("On the Origin of Species", 1859, "1859"), ("Das Kapital (Vol. I)", 1867, "1867"), ("Hind Swaraj", 1909, "1909"),
       ("The Discovery of India", 1946, "1946")],
      "Darwin (1859) precedes Marx (1867).")
    S("Consider the following statements:",
      [("'Poverty and Un-British Rule in India' was written by Dadabhai Naoroji.", True, "yes"),
       ("'Mother India' (1927) was written by Sarojini Naidu.", False, "it was written by the American author Katherine Mayo"),
       ("'Unhappy India' was written by Lala Lajpat Rai.", True, "as a rebuttal to Mayo")],
      "Unhappy India was a reply to Mother India.")
    A("Jhumpa Lahiri won the Pulitzer Prize for Fiction.",
      "She won it for her novel 'The Namesake'.",
      True, False, False, ["A is true (2000).", "R is false: the prize was for the story collection 'Interpreter of Maladies'."],
      "The Namesake was her later novel.")
    M("Author", "Work",
      [("George Orwell", "Animal Farm"), ("Leo Tolstoy", "War and Peace"), ("Miguel de Cervantes", "Don Quixote"), ("Dante Alighieri", "The Divine Comedy")],
      "Classic works across four languages.", lv="L2")

    # ================= Business and startup terminology =================
    h.topic("gk-business-and-startup", "DPIIT Startup India notifications; standard corporate finance glossaries")
    F("In startup terminology, a 'unicorn' is a privately held startup valued at:",
      "US$1 billion or more", [("US$100 million or more", "too low a threshold"), ("US$10 billion or more", "decacorn"),
                               ("US$1 billion in annual revenue", "confuses valuation with revenue")],
      "A unicorn is a private startup with valuation of at least US$1 billion.", "Valuation, not revenue.")
    F("'Bootstrapping' a startup means:",
      "Funding it from founders' own resources", [("Raising capital through an IPO", "public equity"), ("Borrowing under a government guarantee", "debt"),
                                                  ("Raising money from many small donors", "crowdfunding")],
      "Bootstrapping is building a business with personal savings and internal revenue, without outside investors.", "Crowdfunding is external money.")
    F("'Burn rate' refers to:",
      "The rate at which cash is spent", [("The rate of revenue growth", "growth metric"), ("The rate of employee attrition", "HR metric"),
                                          ("The rate of customer loss", "churn rate")],
      "Burn rate is the net cash outflow per period (usually monthly).", "Churn is customers lost; burn is cash spent.")
    F("An 'angel investor' is typically:",
      "An individual investing personal funds early", [("A fund investing money pooled from limited partners", "venture capital fund"), ("A bank extending secured term loans to firms", "debt financier"),
                                                        ("A government agency awarding research grants", "grant, not investment")],
      "Angels are high-net-worth individuals who invest their own money at an early stage.", "VCs invest pooled money of limited partners.")
    F("National Startup Day in India is observed on:",
      "16 January", [("26 January", "Republic Day"), ("1 April", "start of the financial year"), ("15 September", "Engineers' Day")],
      "The day marks the launch of Startup India (16 January 2016); declared National Startup Day in 2022.", "Linked to Startup India's launch date.", lv="L2")
    M("Term", "Meaning",
      [("Pivot", "Fundamental change in the business model"), ("Minimum viable product", "Version with just enough features to test the market"),
       ("Runway", "Time a company can operate before cash runs out"), ("Churn rate", "Share of customers who stop using a product in a period")],
      "Runway = cash ÷ burn rate.", lv="L2")
    M("Takeover term", "Meaning",
      [("Poison pill", "Issuing rights that dilute a hostile acquirer"), ("White knight", "Friendly acquirer that rescues a target from a hostile bid"),
       ("Golden parachute", "Large payouts to executives if dismissed after a takeover"), ("Bear hug", "Offer at a premium too high for the board to refuse")],
      "White knight (friendly bidder) vs poison pill (dilution defence).")
    pre, inv = 120, 30
    post = pre + inv; stake = inv / post
    assert abs(stake - 0.20) < 1e-9
    Q(f"A startup raises ₹{inv} crore from an investor at a pre-money valuation of ₹{pre} crore. What percentage stake does the investor receive?",
      "20%", [("25%", "divided investment by pre-money instead of post-money valuation"), ("80%", "reported founders' residual stake"),
              ("30%", "read the investment amount as a percentage")],
      [f"Post-money valuation = {pre} + {inv} = ₹{post} crore", f"Investor stake = {inv} ÷ {post} = 20%"],
      "Investor stake = Investment ÷ Post-money valuation", "Use post-money, not pre-money, as the base.")
    S("Consider the following statements about recognition as a 'startup' by DPIIT:",
      [("The entity must not be more than ten years old from its date of incorporation.", True, "10-year limit"),
       ("Its turnover must not have exceeded ₹200 crore in any financial year since incorporation.", True, "the ceiling was raised from ₹100 crore (2019) to ₹200 crore by G.S.R. 108(E), 2026; deep-tech startups have a ₹300 crore ceiling and a 20-year age limit"),
       ("An entity formed by splitting up or reconstructing an existing business is not eligible.", True, "per the notification")],
      "All three conditions apply.", ref="DPIIT notification G.S.R. 108(E), 4 February 2026 (superseding G.S.R. 127(E), 2019)")
    A("A 'down round' reduces the value of earlier investors' holdings.",
      "In a down round, shares are issued at a lower valuation than in the previous round.",
      True, True, True, "Lower issue price reprices the company downward, lowering the value of existing stakes.", "R explains A.")
    S("Consider the following statements:",
      [("Greenfield investment involves building new facilities from scratch.", True, "yes"),
       ("Foreign portfolio investment generally implies a lasting management interest in the enterprise.", False, "that describes FDI; FPI is passive"),
       ("Brownfield investment involves acquiring or leasing existing facilities.", True, "yes")],
      "Management control distinguishes FDI from FPI.")
    M("Term", "Valuation threshold / meaning",
      [("Unicorn", "US$1 billion or more"), ("Decacorn", "US$10 billion or more"), ("Hectocorn", "US$100 billion or more"),
       ("Soonicorn", "Startup expected to become a unicorn soon")],
      "Deca = 10, Hecto = 100 (in billions).", lv="L2")
    A("EBITDA is used to compare the operating performance of firms with different capital structures.",
      "EBITDA includes interest expense so as to reflect each firm's financing costs.",
      True, False, False, ["A is true.", "R is false: EBITDA is earnings BEFORE interest, taxes, depreciation and amortisation — interest is excluded, which is what makes cross-capital-structure comparison possible."],
      "Read the acronym: 'before interest'.")
    grant, months, cliff, left = 4800, 48, 12, 30
    vested = grant * left // months if left >= cliff else 0
    assert vested == 3000
    Q(f"An employee is granted {grant:,} stock options vesting in equal monthly instalments over {months} months, with a {cliff}-month cliff "
      f"(nothing vests before month {cliff}; at month {cliff} the first {cliff} months' options vest together). If the employee leaves after {left} months, how many options have vested?",
      f"{vested:,}", [(f"{grant*12//months:,}", "counted only the cliff tranche"), (f"{grant*24//months:,}", "counted only completed years (2 years)"),
                      (f"{grant*36//months:,}", "rounded up to three years")],
      [f"Monthly vesting = {grant:,} ÷ {months} = {grant//months}", f"Cliff passed (30 ≥ 12), so vested = {grant//months} × {left} = {vested:,}"],
      "Vested = (Grant ÷ Vesting months) × Months served, if months ≥ cliff", "The cliff only delays vesting; it does not reset it.")
    S("Consider the following statements:",
      [("Short selling means buying a security expecting its price to rise.", False, "short selling is selling borrowed securities expecting a fall"),
       ("A bull market is a prolonged period of rising prices.", True, "yes"),
       ("Blue-chip shares are shares of large, well-established and financially sound companies.", True, "yes")],
      "Buying in expectation of a rise is 'going long'.")

    # ================= Climate awareness initiatives =================
    h.topic("gk-climate-awareness-initiatives", "UNEP / UN observances calendar; MoEFCC (NAPCC, Mission LiFE); IPCC; WWF")
    F("'Earth Hour' is an initiative of:",
      "WWF", [("UNEP", "organises World Environment Day"), ("Greenpeace", "separate NGO"), ("IUCN", "publishes the Red List")],
      "Earth Hour began in Sydney in 2007 as a WWF initiative.", "UNEP's flagship observance is World Environment Day.")
    F("World Environment Day is observed on:",
      "5 June", [("22 April", "Earth Day"), ("16 September", "World Ozone Day"), ("22 March", "World Water Day")],
      "World Environment Day (5 June) marks the opening of the 1972 Stockholm Conference.", "Earth Day (22 April) is a different observance.")
    F("In India's 'Mission LiFE', LiFE stands for:",
      "Lifestyle for Environment", [("Living in Forest Ecology", "incorrect expansion"), ("Low-Impact Future Economy", "incorrect expansion"),
                                    ("Life in Future Earth", "incorrect expansion")],
      "Mission LiFE (Lifestyle for Environment) promotes environment-conscious individual behaviour.", "It is about lifestyle choices.")
    F("The Chipko movement began in the 1970s in present-day:",
      "Uttarakhand", [("Karnataka", "Appiko movement"), ("Kerala", "Silent Valley movement"), ("Madhya Pradesh", "Narmada Bachao Andolan (partly)")],
      "Chipko began in Chamoli district (then Uttar Pradesh, now Uttarakhand) in 1973.", "Appiko was Karnataka's Chipko-inspired movement.")
    F("World Ozone Day (International Day for the Preservation of the Ozone Layer) is observed on:",
      "16 September", [("5 June", "World Environment Day"), ("22 April", "Earth Day"), ("8 June", "World Oceans Day")],
      "16 September marks the signing of the Montreal Protocol (1987).", "Linked to the Montreal Protocol date.", lv="L2")
    M("Date", "Observance",
      [("22 April", "Earth Day"), ("2 February", "World Wetlands Day"), ("22 March", "World Water Day"),
       ("17 June", "Desertification and Drought Day")],
      "World Wetlands Day marks the Ramsar Convention signing (2 February 1971).", lv="L2")
    S("Consider the following statements about India's 'Panchamrit' climate commitments:",
      [("They include a target of net-zero emissions by 2070.", True, "yes"),
       ("They were announced at COP21 in Paris.", False, "they were announced at COP26, Glasgow (2021)"),
       ("They include 500 GW of non-fossil energy capacity by 2030.", True, "yes")],
      "Paris (2015) saw India's first NDC; Panchamrit came at Glasgow.")
    A("The IPCC does not conduct its own original research.",
      "It assesses published scientific literature to prepare its assessment reports.",
      True, True, True, "IPCC's role is assessment of existing literature — hence no original research.", "R explains A.")
    C("Arrange the following in chronological order:",
      [("Chipko movement begins", 1973, "1973"), ("IPCC established", 1988, "1988"), ("National Action Plan on Climate Change released", 2008, "2008"),
       ("Mission LiFE launched", 2022, "2022")],
      "NAPCC (2008) predates Mission LiFE by 14 years.")
    N("Consider the following statements about the National Action Plan on Climate Change:",
      [("It was released in 2008.", True, "30 June 2008"), ("It comprises eight national missions.", True, "yes"),
       ("The National Solar Mission is one of them.", True, "yes"),
       ("A National Mission on Coastal Protection is one of the original eight.", False, "not among the original eight")],
      "Original missions: Solar, Energy Efficiency, Sustainable Habitat, Water, Himalayan Ecosystem, Green India, Sustainable Agriculture, Strategic Knowledge.")
    M("Movement / initiative", "Associated person",
      [("Green Belt Movement", "Wangari Maathai"), ("Fridays for Future", "Greta Thunberg"), ("Chipko movement", "Sunderlal Bahuguna"),
       ("Narmada Bachao Andolan", "Medha Patkar")],
      "Wangari Maathai won the Nobel Peace Prize in 2004.", lv="L2")
    A("The Coalition for Disaster Resilient Infrastructure was launched at the UN Climate Action Summit in 2019.",
      "It is an India-led global partnership with its secretariat in New Delhi.",
      True, True, False, ["Both statements are true.", "India's leadership and the secretariat location do not explain the launch venue."],
      "Two true facts about CDRI, not cause and effect.")
    S("Consider the following statements:",
      [("Earth Day was first observed in 1970.", True, "yes"), ("Earth Day is observed on 22 April.", True, "yes"),
       ("Earth Day and Earth Hour are the same observance.", False, "Earth Hour is a separate WWF lights-off event")],
      "Earth Day ≠ Earth Hour.")
    A("Mission LiFE emphasises individual behaviour change.",
      "It seeks to replace 'use-and-dispose' consumption with mindful and deliberate utilisation of resources.",
      True, True, True, "The shift in consumption described in R is achieved through individual behaviour.", "R explains A.")
    S("Consider the following statements about the IPCC:",
      [("It was established in 1988 by WMO and UNEP.", True, "yes"), ("It shared the Nobel Peace Prize in 2007 with Al Gore.", True, "yes"),
       ("Its secretariat is in Geneva.", True, "hosted by WMO")],
      "All three statements are correct.")

    # ================= Commemorative coins and numismatics =================
    h.topic("gk-commemorative-coins-and-numismatics", "RBI (currency management FAQs); Coinage Act, 2011; NCERT Class 12 History Part I")
    F("The study of coins is called:",
      "Numismatics", [("Philately", "study of postage stamps"), ("Epigraphy", "study of inscriptions"), ("Palaeography", "study of ancient scripts")],
      "Numismatics is the study of coins and currency.", "Philately is stamps.")
    F("Under the Coinage Act, 2011, the power to mint coins rests with the:",
      "Central Government", [("Reserve Bank of India", "only distributes coins"), ("State governments", "no minting power"),
                             ("Ministry of Commerce", "incorrect")],
      "Coins are designed and minted by the Government of India; the RBI puts them into circulation.", "RBI issues notes, not coins.")
    F("The Indian rupee symbol (₹), adopted in 2010, was designed by:",
      "D. Udaya Kumar", [("Satish Gujral", "painter"), ("Nandalal Bose", "illuminated the Constitution"), ("M. F. Husain", "painter")],
      "D. Udaya Kumar's design was selected in 2010.", "Nandalal Bose decorated the Constitution manuscript.")
    F("The decimal system of coinage was introduced in India in:",
      "1957", [("1947", "independence"), ("1950", "first coins of the Republic"), ("1964", "'naya' dropped from 'naya paisa'")],
      "Decimal coinage (100 naye paise = 1 rupee) came into effect on 1 April 1957.", "1964 is when 'naya' was dropped.")
    F("The earliest coins of India are the:",
      "Punch-marked coins", [("Kushana gold coins", "1st–3rd century CE"), ("Gupta dinaras", "4th–6th century CE"),
                             ("Indo-Greek coins", "2nd century BCE")],
      "Punch-marked coins (mostly silver, c. 6th century BCE) are the earliest Indian coins.", "Indo-Greek coins came later but were the first with rulers' portraits.", lv="L2")
    S("Consider the following statements:",
      [("Section 22 of the RBI Act gives the RBI the sole right to issue banknotes in India.", True, "yes"),
       ("Coins are minted by the RBI in its own mints.", False, "coins are minted by Government of India mints"),
       ("The one-rupee note is issued by the Government of India and signed by the Finance Secretary.", True, "yes")],
      "Notes (RBI) vs coins and ₹1 notes (Government).", ref="RBI Act, 1934, Sec. 22; Coinage Act, 2011")
    M("Dynasty / ruler", "Coinage feature",
      [("Indo-Greeks", "First coins bearing rulers' portraits and names"), ("Kushanas", "Large-scale issue of gold coins"),
       ("Satavahanas", "Lead coins"), ("Iltutmish", "Silver tanka")],
      "Satavahana lead (and potin) coinage is distinctive.")
    A("Coins are not liabilities of the RBI.",
      "Coins are minted by the Government of India; the RBI only distributes them as the Government's agent.",
      True, True, True, "Because the Government issues coins, they are Government liabilities.", "R explains A.")
    C("Arrange the following in chronological order:",
      [("Punch-marked coins", -500, "c. 6th century BCE"), ("Kushana gold coinage", 100, "c. 1st–2nd century CE"),
       ("Iltutmish's silver tanka", 1220, "13th century"), ("Sher Shah Suri's silver rupiya", 1540, "16th century")],
      "Tanka (13th c.) precedes rupiya (16th c.).")
    N("Consider the following statements about Government of India mints:",
      [("There are four mints: Mumbai, Kolkata, Hyderabad and Noida.", True, "yes"), ("Coins minted at Noida carry a dot below the date.", True, "yes"),
       ("Coins minted at Mumbai carry a diamond mark.", True, "yes"), ("Coins minted at Kolkata carry a star mark.", False, "Kolkata coins carry no mint mark")],
      "Kolkata = no mark.")
    S("Consider the following statements about decimalisation of Indian coinage:",
      [("It came into effect on 1 April 1957.", True, "yes"), ("The rupee was then divided into 100 naye paise.", True, "yes"),
       ("Before decimalisation, one rupee was divided into 16 annas.", True, "yes")],
      "All three statements are correct.")
    A("The Gupta rulers issued a large number of gold coins called dinaras.",
      "The name 'dinara' is derived from the Roman 'denarius'.",
      True, True, False, ["Both statements are true.", "The etymology does not explain why the Guptas issued many gold coins."],
      "Etymology is not causation.")
    S("Consider the following statements about the Coinage Act, 2011:",
      [("Coins of denominations up to ₹1,000 may be issued.", True, "Sec. 4"), ("It repealed the Coinage Act, 1906.", True, "along with other laws"),
       ("Coins are legal tender for payment of any amount.", False, "the Act caps legal tender for coins (e.g. up to ₹1,000 for coins of ₹1 and above)")],
      "Coins are limited legal tender.", ref="Coinage Act, 2011, Secs. 4 and 6")
    M("Numismatic term", "Meaning",
      [("Obverse", "Side of a coin with the principal design"), ("Legend", "Inscription on a coin"),
       ("Exergue", "Space below the main design, often for the date"), ("Reeding", "Grooved edge of a coin")],
      "Obverse = 'heads' side.", lv="L2")
    A("The first commemorative coin of independent India was issued in 1964.",
      "It honoured Jawaharlal Nehru after his death that year.",
      True, True, True, "Nehru's death in May 1964 prompted the commemorative issue.", "R explains A.")

    # ================= Defence forces, exercises and expeditions =================
    h.topic("gk-defence-forces-exercises", "Ministry of Defence annual reports; PIB (Defence); National Centre for Polar and Ocean Research")
    F("The Malabar naval exercise began in 1992 as a bilateral exercise between India and:",
      "The United States", [("Japan", "joined later"), ("Australia", "joined later"), ("France", "Varuna exercise")],
      "Malabar began as an India–US exercise; Japan and Australia joined later.", "Varuna is with France.")
    F("Indian Navy Day is observed on:",
      "4 December", [("15 January", "Army Day"), ("8 October", "Air Force Day"), ("1 February", "Coast Guard Day")],
      "Navy Day commemorates Operation Trident (1971) against Karachi.", "Each service has its own day.")
    F("Who was the first Indian Army officer to be promoted to Field Marshal?",
      "Sam Manekshaw", [("K. M. Cariappa", "second Field Marshal, 1986"), ("Arjan Singh", "Marshal of the Indian Air Force"),
                        ("Bipin Rawat", "first Chief of Defence Staff")],
      "Sam Manekshaw was made Field Marshal in January 1973.", "Cariappa received the rank later, in 1986.")
    F("Operation Meghdoot (1984) is associated with:",
      "Siachen Glacier", [("Kargil", "Operation Vijay, 1999"), ("Goa", "Operation Vijay, 1961"), ("Maldives", "Operation Cactus, 1988")],
      "Operation Meghdoot secured the Siachen Glacier in April 1984.", "Operation Vijay is the name used for both Goa and Kargil.")
    F("India's first research station in Antarctica was:",
      "Dakshin Gangotri", [("Maitri", "second station, 1989"), ("Bharati", "third station, 2012"), ("Himadri", "Arctic station, Svalbard")],
      "Dakshin Gangotri was established in 1983–84.", "Himadri is in the Arctic.", lv="L2")
    M("Exercise", "Partner country",
      [("Yudh Abhyas", "United States"), ("Garuda Shakti", "Indonesia"), ("Mitra Shakti", "Sri Lanka"), ("Nomadic Elephant", "Mongolia")],
      "Garuda Shakti (Indonesia) vs Garuda (France air exercise).")
    M("Exercise", "Partner country",
      [("Varuna", "France"), ("SIMBEX", "Singapore"), ("Dharma Guardian", "Japan"), ("INDRA", "Russia")],
      "SIMBEX = Singapore; SLINEX = Sri Lanka.", lv="L2")
    N("Consider the following statements:",
      [("India's first Antarctic expedition was in 1981–82.", True, "led by S. Z. Qasim"), ("Maitri station was set up in 1989.", True, "yes"),
       ("Bharati station was commissioned in 2012.", True, "yes"), ("Himadri station is located in Antarctica.", False, "Himadri is at Ny-Ålesund, Svalbard, in the Arctic")],
      "Himadri = Arctic.")
    C("Arrange the following military operations in chronological order:",
      [("Operation Vijay (Goa)", 1961, "1961"), ("Operation Meghdoot", 1984, "1984"), ("Operation Cactus (Maldives)", 1988, "1988"),
       ("Operation Rahat (Yemen evacuation)", 2015, "2015")],
      "Meghdoot (1984) precedes Cactus (1988).")
    A("The BrahMos missile derives its name from two rivers.",
      "It is an India–Russia joint venture named after the Brahmaputra and the Moskva.",
      True, True, True, "R gives the two rivers behind the name.", "R explains A.")
    S("Consider the following statements:",
      [("INS Vikrant, commissioned in 2022, is India's first indigenously built aircraft carrier.", True, "yes"),
       ("The Indian Coast Guard functions under the Ministry of Home Affairs.", False, "it functions under the Ministry of Defence"),
       ("INS Arihant is India's first indigenous nuclear-powered ballistic missile submarine.", True, "yes")],
      "Coast Guard: Ministry of Defence (Coast Guard Act, 1978).")
    A("Army Day is celebrated on 15 January.",
      "On 15 January 1949, K. M. Cariappa took over as the first Indian Commander-in-Chief of the Indian Army from General Sir Francis Bucher.",
      True, True, True, "The handover date is commemorated as Army Day.", "R explains A.")
    S("Consider the following statements about the Integrated Guided Missile Development Programme:",
      [("It was launched in 1983.", True, "yes"), ("It was led by DRDO under A. P. J. Abdul Kalam.", True, "yes"),
       ("Its missiles included Prithvi, Agni, Trishul, Akash and Nag.", True, "yes")],
      "All three statements are correct.")
    S("Consider the following statements:",
      [("Tenzing Norgay and Edmund Hillary first reached the summit of Everest in 1953.", True, "29 May 1953"),
       ("Bachendri Pal was the first Indian woman to climb Everest, in 1984.", True, "yes"),
       ("The first successful Indian expedition to Everest, in 1965, was led by M. S. Kohli.", True, "yes")],
      "All three statements are correct.")
    A("Air Force Day is celebrated on 8 October.",
      "The first operational squadron of the Indian Air Force was formed in April 1933.",
      True, True, False, ["Both statements are true.", "Air Force Day marks the IAF's official establishment on 8 October 1932, not the formation of No. 1 Squadron."],
      "Establishment date vs first squadron date.")

    # ================= Sports terminology and Indian sporting history =================
    h.topic("gk-sports-terminology", "Olympic and federation records; Ministry of Youth Affairs and Sports")
    F("In golf, a 'birdie' means a score of:",
      "One stroke under par", [("Two strokes under par", "eagle"), ("One stroke over par", "bogey"), ("Equal to par", "par")],
      "Birdie = −1; eagle = −2; albatross = −3; bogey = +1.", "Eagle is bigger than birdie.")
    F("The Durand Cup is associated with:",
      "Football", [("Hockey", "Beighton Cup, Aga Khan Cup"), ("Cricket", "Ranji Trophy"), ("Polo", "incorrect")],
      "The Durand Cup (1888) is one of the oldest football tournaments in the world.", "Not to be confused with the Durand Line.")
    F("The Thomas Cup is associated with:",
      "Badminton", [("Tennis", "Davis Cup"), ("Table tennis", "Swaythling Cup"), ("Squash", "incorrect")],
      "The Thomas Cup is the men's world team badminton championship; India won it in 2022.", "Uber Cup is the women's equivalent.")
    F("Who won independent India's first individual Olympic gold medal?",
      "Abhinav Bindra", [("Neeraj Chopra", "athletics gold, Tokyo"), ("Rajyavardhan Singh Rathore", "silver, 2004"),
                         ("Leander Paes", "bronze, 1996")],
      "Abhinav Bindra won the 10 m air rifle gold at Beijing 2008.", "Chopra's was the first athletics gold.")
    F("National Sports Day in India is observed on:",
      "29 August", [("23 June", "Olympic Day"), ("2 October", "Gandhi Jayanti"), ("12 January", "National Youth Day")],
      "29 August is the birth anniversary of Major Dhyan Chand.", "Olympic Day (23 June) is international.", lv="L2")
    M("Term", "Sport",
      [("Chukker", "Polo"), ("Googly", "Cricket"), ("Deuce", "Tennis"), ("Snatch", "Weightlifting")],
      "Chukker is a period of play in polo.", lv="L2")
    C("Arrange the following in chronological order:",
      [("India's first Olympic hockey gold", 1928, "1928, Amsterdam"), ("K. D. Jadhav's Olympic bronze", 1952, "1952, Helsinki"),
       ("India wins the Cricket World Cup", 1983, "1983"), ("Viswanathan Anand becomes India's first Grandmaster", 1988, "1988")],
      "1983 World Cup precedes Anand's GM title (1988).")
    S("Consider the following statements:",
      [("K. D. Jadhav won independent India's first individual Olympic medal.", True, "bronze, wrestling, 1952"),
       ("Karnam Malleswari was the first Indian woman to win an Olympic medal.", True, "bronze, weightlifting, 2000"),
       ("Neeraj Chopra won India's first Olympic gold medal in athletics.", True, "javelin, Tokyo")],
      "All three statements are correct.")
    M("Trophy", "Sport",
      [("Ranji Trophy", "Cricket"), ("Santosh Trophy", "Football"), ("Beighton Cup", "Hockey"), ("Uber Cup", "Badminton")],
      "Santosh Trophy is the national football championship.", lv="L2")
    A("National Sports Day is observed on the birth anniversary of athlete Milkha Singh.",
      "29 August, the date of National Sports Day, is the birth anniversary of hockey player Major Dhyan Chand.",
      False, True, False, ["A is false: the day honours Dhyan Chand, not Milkha Singh.", "R is true."], "Dhyan Chand, not Milkha Singh.")
    S("Consider the following statements about golf terms:",
      [("An albatross is one stroke under par.", False, "an albatross is three under par; one under is a birdie"),
       ("An eagle is two strokes under par.", True, "yes"), ("A bogey is one stroke over par.", True, "yes")],
      "Birdie (−1) < eagle (−2) < albatross (−3).")
    N("Consider the following statements about Indian hockey at the Olympics:",
      [("India has won eight Olympic gold medals in hockey.", True, "1928–1980"), ("India's most recent hockey gold was at Moscow in 1980.", True, "yes"),
       ("India's first hockey gold was at Amsterdam in 1928.", True, "yes"), ("India won the hockey gold at Rome in 1960.", False, "India won silver; Pakistan won gold")],
      "1960 was India's first loss in an Olympic hockey final.")
    A("Milkha Singh did not win a medal at the 1960 Rome Olympics.",
      "He finished fourth in the 400 metres final.",
      True, True, True, "A fourth-place finish means no medal.", "R explains A.")
    C("Arrange the following in chronological order:",
      [("First Asian Games, New Delhi", 1951, "1951"), ("Asian Games in Delhi (second time)", 1982, "1982"),
       ("Commonwealth Games in Delhi", 2010, "2010"), ("India wins the Thomas Cup", 2022, "2022")],
      "India hosted the Asian Games in 1951 and 1982.")
    M("Chess term", "Meaning",
      [("Castling", "Moving the king and a rook together in one move"), ("Stalemate", "Player to move has no legal move and is not in check"),
       ("En passant", "Special pawn capture"), ("Gambit", "Sacrificing material in the opening for advantage")],
      "Stalemate is a draw, not a loss.")

    # ================= World currencies =================
    h.topic("gk-world-currencies", "IMF country information; central bank websites; ISO 4217")
    F("The currency of Bhutan is the:",
      "Ngultrum", [("Rufiyaa", "Maldives"), ("Kyat", "Myanmar"), ("Taka", "Bangladesh")],
      "Bhutan's currency is the ngultrum.", "All options are South/Southeast Asian currencies.")
    F("The currency of Bangladesh is the:",
      "Taka", [("Rupee", "India, Nepal, Sri Lanka, Pakistan"), ("Kyat", "Myanmar"), ("Afghani", "Afghanistan")],
      "Bangladesh uses the taka.", "Not a rupee country.")
    F("The currency of South Africa is the:",
      "Rand", [("Naira", "Nigeria"), ("Shilling", "Kenya, Uganda, Tanzania"), ("Kwacha", "Zambia, Malawi")],
      "South Africa's currency is the rand.", "Naira is Nigeria.")
    F("The currency of Brazil is the:",
      "Real", [("Peso", "Argentina, Mexico and others"), ("Sol", "Peru"), ("Bolívar", "Venezuela")],
      "Brazil uses the real.", "Brazil is not a peso country.")
    F("The currency of Poland is the:",
      "Zloty", [("Forint", "Hungary"), ("Koruna", "Czech Republic"), ("Hryvnia", "Ukraine")],
      "Poland's currency is the złoty.", "Central European currencies are easily confused.", lv="L2")
    M("Country", "Currency",
      [("Maldives", "Rufiyaa"), ("Myanmar", "Kyat"), ("Indonesia", "Rupiah"), ("Vietnam", "Dong")],
      "Rupiah (Indonesia) vs rufiyaa (Maldives).", lv="L2")
    M("Country", "Currency",
      [("Nigeria", "Naira"), ("Ghana", "Cedi"), ("Ethiopia", "Birr"), ("Botswana", "Pula")],
      "African currencies — pula (Botswana) means 'rain'.")
    N("Consider the following statements about the Special Drawing Right (SDR):",
      [("It is an international reserve asset created by the IMF.", True, "1969"), ("Its value is based on a basket of five currencies.", True, "USD, EUR, CNY, JPY, GBP"),
       ("The Chinese renminbi was added to the SDR basket in 2016.", True, "October 2016"),
       ("It is used as a currency in day-to-day retail transactions.", False, "it is not a currency for private transactions")],
      "SDR is a reserve asset and unit of account.", ref="IMF SDR factsheet")
    S("Consider the following statements about the euro:",
      [("All members of the European Union use the euro.", False, "several EU members retain national currencies"),
       ("The euro was introduced as an accounting currency in 1999, with notes and coins in 2002.", True, "yes"),
       ("The European Central Bank is headquartered in Frankfurt.", True, "yes")],
      "Eurozone ≠ European Union.")
    M("ISO 4217 code", "Currency",
      [("CHF", "Swiss franc"), ("ZAR", "South African rand"), ("CNY", "Chinese yuan renminbi"), ("BRL", "Brazilian real")],
      "CHF comes from the Latin 'Confoederatio Helvetica'.")
    N("Consider the following pairs (country — currency):",
      [("Ukraine — Hryvnia", True, "yes"), ("Kazakhstan — Tenge", True, "yes"),
       ("Hungary — Koruna", False, "Hungary uses the forint; koruna is Czech"), ("Georgia — Dram", False, "Georgia uses the lari; dram is Armenian")],
      "Neighbouring countries' currencies are the traps.", pairs=True)
    A("The Bhutanese ngultrum and the Indian rupee exchange at par.",
      "The ngultrum is pegged to the Indian rupee at 1:1.",
      True, True, True, "The fixed 1:1 peg means they exchange at par.", "R explains A.")
    S("Consider the following pairs (country — currency):",
      [("United Arab Emirates — Dirham", True, "yes"), ("Kuwait — Dinar", True, "yes"), ("Saudi Arabia — Dinar", False, "Saudi Arabia uses the riyal")],
      "Riyal: Saudi Arabia and Qatar; dinar: Kuwait, Bahrain, Iraq, Jordan.", pairs=True)
    A("China's currency is referred to as both 'renminbi' and 'yuan'.",
      "Renminbi is the name of the currency, while the yuan is its principal unit of account.",
      True, True, True, "The distinction in R explains the dual usage.", "R explains A.")
    M("Country", "Currency",
      [("Sweden", "Krona"), ("Norway", "Krone"), ("Czech Republic", "Koruna"), ("Switzerland", "Franc")],
      "Krona (Sweden) vs krone (Norway, Denmark) vs koruna (Czech).")
