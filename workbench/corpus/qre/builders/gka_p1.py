"""QRE-GK-A part 1 — History (5 microtopics x 15)."""
from gka_h import H


def add_all(B):
    h = H(B, "")
    F, S, N, M, C, A = h.F, h.S, h.N, h.M, h.C, h.A

    # ================= Ancient Indian texts and statecraft =================
    h.topic("gk-ancient-indian-texts", "NCERT Class 12 History (Themes in Indian History, Part I); NCERT Class 6 'Our Pasts'")
    F("The Arthashastra, a treatise on statecraft and economic policy, is traditionally attributed to:",
      "Kautilya", [("Kalidasa", "author of Abhijnanashakuntalam, not a political treatise"),
                   ("Banabhatta", "author of Harshacharita"), ("Vishakhadatta", "wrote the play Mudrarakshasa about Chanakya")],
      "The Arthashastra is attributed to Kautilya (Chanakya/Vishnugupta), minister of Chandragupta Maurya.",
      "Vishakhadatta wrote ABOUT Chanakya (Mudrarakshasa); he did not write the Arthashastra.")
    F("The Sanskrit play Mudrarakshasa, which depicts the rise of Chandragupta Maurya, was written by:",
      "Vishakhadatta", [("Bhasa", "early dramatist, Svapnavasavadatta"), ("Sudraka", "author of Mrichchhakatika"),
                        ("Kalidasa", "Gupta-age poet-dramatist")],
      "Mudrarakshasa ('The Signet Ring of Rakshasa') is Vishakhadatta's political drama on Chanakya and Chandragupta.",
      "Do not confuse with Sudraka's Mrichchhakatika (The Little Clay Cart).")
    F("'Indica', an account of Mauryan India, was written by:",
      "Megasthenes", [("Fa-Hien", "Chinese pilgrim in the Gupta period"), ("Hiuen Tsang", "Chinese pilgrim in Harsha's time"),
                      ("Ptolemy", "Greek geographer, 2nd century CE")],
      "Megasthenes, ambassador of Seleucus Nicator at Chandragupta Maurya's court in Pataliputra, wrote Indica (surviving in fragments).",
      "Chinese pilgrims wrote travel records (Fo-kuo-ki, Si-yu-ki), not Indica.")
    F("Harshacharita, a biography of King Harshavardhana, was composed by his court poet:",
      "Banabhatta", [("Harshavardhana himself", "Harsha wrote plays such as Ratnavali, not his biography"),
                     ("Kalhana", "author of Rajatarangini"), ("Bilhana", "wrote Vikramankadevacharita on a Chalukya king")],
      "Banabhatta, court poet of Harsha, wrote Harshacharita (and Kadambari) in Sanskrit.",
      "Harsha authored plays (Ratnavali, Nagananda, Priyadarshika) but not his own biography.")
    F("Rajatarangini, a 12th-century chronicle of the kings of Kashmir, was written by:",
      "Kalhana", [("Bilhana", "Kashmiri poet who wrote on the Chalukya court"), ("Somadeva", "author of Kathasaritsagara"),
                  ("Hemachandra", "Jain scholar of Gujarat")],
      "Kalhana composed Rajatarangini (c. 1148–49 CE) in Sanskrit verse.",
      "Somadeva was also Kashmiri but wrote the story collection Kathasaritsagara.", lv="L2")
    S("Consider the following statements about the Arthashastra:",
      [("Its Saptanga theory describes the state as having seven elements, including Swami, Amatya and Kosha.", True,
        "the seven limbs are Swami, Amatya, Janapada, Durga, Kosha, Danda and Mitra"),
       ("A manuscript of the text was found and published by R. Shamasastry in the early twentieth century.", True,
        "Shamasastry identified the manuscript in 1905 and published it in 1909"),
       ("It was composed mainly in Pali.", False, "it is written in Sanskrit")],
      "Pali is the language of the Buddhist canon, not of the Arthashastra.")
    M("Text", "Author", [("Ashtadhyayi", "Panini"), ("Mahabhashya", "Patanjali"), ("Nitisara", "Kamandaka"),
                         ("Mrichchhakatika", "Sudraka")],
      "Patanjali's Mahabhashya is a commentary on Panini's grammar — keep the two grammarians distinct.",
      notes=["Sanskrit grammar", "commentary on Panini", "treatise on polity", "drama"])
    M("Foreign envoy / pilgrim", "Court or reign visited",
      [("Megasthenes", "Chandragupta Maurya"), ("Deimachus", "Bindusara"), ("Fa-Hien", "Chandragupta II"),
       ("Hiuen Tsang", "Harshavardhana")],
      "Fa-Hien came in the Gupta period (Chandragupta II), Hiuen Tsang two centuries later under Harsha.")
    A("Ashoka's Dhamma was not a new religion.",
      "It stressed ethical conduct — tolerance, non-violence, respect for elders and humane treatment of servants — meant for people of all sects.",
      True, True, True,
      "Ashoka's edicts present Dhamma as a moral code for all subjects; its universal ethical content is why it is not treated as a separate religion.",
      "Ashoka personally followed Buddhism, but Dhamma itself was a general ethical code.")
    C("Arrange the following in chronological order:",
      [("Megasthenes at the court of Pataliputra", -300, "c. 300 BCE (Chandragupta Maurya)"),
       ("Fourth Buddhist Council under Kanishka", 100, "c. 1st–2nd century CE"),
       ("Fa-Hien's travels in India", 405, "c. 399–412 CE"),
       ("Hiuen Tsang's travels in India", 635, "c. 629–645 CE")],
      "The Kushana council precedes both Chinese pilgrims; Fa-Hien (Gupta) precedes Hiuen Tsang (Harsha).")
    S("Consider the following statements about early Tamil (Sangam and post-Sangam) literature:",
      [("Tolkappiyam is a work on Tamil grammar and poetics.", True, "it is the oldest extant Tamil grammar"),
       ("Silappadikaram was composed by Ilango Adigal.", True, "the epic of Kannagi and Kovalan"),
       ("Manimekalai was composed by Kamban.", False, "Manimekalai is by Sittalai Sattanar; Kamban wrote the Tamil Ramayana much later")],
      "Kamban (Ramavataram) belongs to the Chola period, not to the twin epics.", ask="incorrect")
    N("Consider the following pairs of Mauryan officials (as described in the Arthashastra) and their functions:",
      [("Samaharta — chief collector of revenue", True, "Samaharta supervised revenue collection"),
       ("Sannidhata — chief of the treasury and stores", True, "Sannidhata was the treasurer/custodian of stores"),
       ("Sitadhyaksha — superintendent of crown agriculture", True, "Sita = crown lands; Sitadhyaksha supervised agriculture on them"),
       ("Akshapataladhyaksha — superintendent of elephants", False, "Akshapatala was the accounts and records office; elephants were under the Hastyadhyaksha")],
      "The 'aksha' prefix misleads — Akshapatala is the accounts office.", pairs=True)
    A("In Kautilya's Mandala theory, the kingdom lying beyond the immediate neighbour is regarded as a natural ally.",
      "The immediate neighbour is treated as the natural enemy (ari), and the enemy's enemy is treated as a friend.",
      True, True, True,
      "The Mandala is a circle of states: the adjoining state is the ari; the state beyond it (the mitra) shares that enemy and so is a natural ally.",
      "R supplies the logic (enemy's enemy is a friend) that makes A follow.")
    S("Consider the following statements about works of the Gupta age:",
      [("Amarakosha is a Sanskrit lexicon compiled by Amarasimha.", True, "Amarasimha is traditionally placed among the 'nine gems'"),
       ("Aryabhatiya was composed by Aryabhata.", True, "the astronomical-mathematical treatise of 499 CE"),
       ("Brihatsamhita, an encyclopaedic work, was composed by Varahamihira.", True, "covers astronomy, astrology, architecture and more")],
      "All three are genuine Gupta-age attributions; do not assume one must be false.")
    M("Buddhist text", "Content",
      [("Vinaya Pitaka", "Rules for the monastic order"), ("Sutta Pitaka", "Discourses of the Buddha"),
       ("Abhidhamma Pitaka", "Philosophical and doctrinal analysis"), ("Jatakas", "Stories of the Buddha's previous births")],
      "Vinaya = discipline; Sutta = sermons; Abhidhamma = philosophy.", lv="L2")

    # ================= Freedom-movement leaders and their offices =================
    h.topic("gk-freedom-movement-leaders", "NCERT Class 12 History Part III; Bipan Chandra, 'India's Struggle for Independence'; INC session records")
    F("Who presided over the first session of the Indian National Congress held at Bombay in 1885?",
      "W. C. Bonnerjee", [("A. O. Hume", "founder/organiser, not president"), ("Dadabhai Naoroji", "presided in 1886"),
                          ("Surendranath Banerjee", "presided in 1895 and 1902")],
      "Womesh Chunder Bonnerjee presided over the first INC session (Bombay, December 1885).",
      "Hume founded the Congress but never presided over it.")
    F("Who was the first woman to preside over the Indian National Congress?",
      "Annie Besant", [("Sarojini Naidu", "first Indian woman president, 1925"), ("Nellie Sengupta", "presided in 1933"),
                       ("Kasturba Gandhi", "never INC president")],
      "Annie Besant presided over the Calcutta session of 1917.",
      "Sarojini Naidu (Kanpur, 1925) was the first INDIAN woman president.")
    F("Who was elected permanent President of the Constituent Assembly of India?",
      "Dr Rajendra Prasad", [("Dr B. R. Ambedkar", "chaired the Drafting Committee"),
                             ("Dr Sachchidananda Sinha", "temporary (provisional) president"),
                             ("J. B. Kripalani", "INC president in 1947")],
      "Rajendra Prasad was elected permanent President on 11 December 1946.",
      "Sachchidananda Sinha presided only over the first sitting as the oldest member.")
    F("Who was the only Indian to hold the office of Governor-General of India?",
      "C. Rajagopalachari", [("Dr Rajendra Prasad", "first President of India"), ("Vallabhbhai Patel", "first Home Minister"),
                             ("Jawaharlal Nehru", "first Prime Minister")],
      "C. Rajagopalachari succeeded Mountbatten in June 1948 and served until 26 January 1950.",
      "The office was abolished when the Republic came into being; Prasad became President, not Governor-General.")
    F("The 'Purna Swaraj' resolution was adopted at the 1929 Lahore session of the INC, presided over by:",
      "Jawaharlal Nehru", [("Motilal Nehru", "presided at Calcutta, 1928"), ("Subhas Chandra Bose", "presided in 1938 and 1939"),
                           ("M. K. Gandhi", "presided only at Belgaum, 1924")],
      "Jawaharlal Nehru presided at Lahore (December 1929), where complete independence was declared the goal.",
      "Father and son presided over consecutive sessions (1928, 1929) — keep them apart.", lv="L2")
    M("INC session", "President",
      [("Calcutta, 1906", "Dadabhai Naoroji"), ("Belgaum, 1924", "M. K. Gandhi"), ("Karachi, 1931", "Vallabhbhai Patel"),
       ("Haripura, 1938", "Subhas Chandra Bose")],
      "Belgaum 1924 was the only session Gandhi presided over; Karachi 1931 (Fundamental Rights resolution) was Patel's.")
    N("Consider the following statements:",
      [("Sarojini Naidu was the first Indian woman to preside over the INC (Kanpur, 1925).", True, "Kanpur session, 1925"),
       ("Sarojini Naidu was the first woman Governor of an Indian state/province (United Provinces).", True, "appointed in 1947"),
       ("Vijaya Lakshmi Pandit was the first woman President of the UN General Assembly.", True, "elected in 1953"),
       ("Annie Besant presided over the Surat session of 1907.", False, "Surat 1907 was presided over by Rash Behari Ghosh")],
      "The Surat split (1907) had Rash Behari Ghosh in the chair; Besant presided in 1917.")
    C("Arrange the following events in chronological order:",
      [("Formation of the Swaraj Party", 1923, "1923 (C. R. Das and Motilal Nehru)"),
       ("Gandhi–Irwin Pact", 1931, "March 1931"),
       ("Formation of the Forward Bloc", 1939, "1939 (Subhas Chandra Bose)"),
       ("Proclamation of the Provisional Government of Azad Hind", 1943, "October 1943, Singapore")],
      "The Forward Bloc (1939) predates the Azad Hind government (1943).")
    A("Subhas Chandra Bose completed his full term as Congress president after the Tripuri session of 1939.",
      "After his re-election at Tripuri over Gandhi-backed Pattabhi Sitaramayya, he could not secure a Working Committee acceptable to both sides.",
      False, True, False,
      ["A is false: the Working Committee deadlock led Bose to resign in April 1939; Rajendra Prasad took over.",
       "R is true — and it is the reason he resigned rather than completed the term."],
      "The resignation followed the Working Committee impasse, not a defeat in election.")
    M("Leader", "Organisation founded",
      [("Bal Gangadhar Tilak", "Home Rule League (founded April 1916 at the Belgaum conference; HQ Poona)"), ("Gopal Krishna Gokhale", "Servants of India Society"),
       ("Chittaranjan Das", "Swaraj Party"), ("B. R. Ambedkar", "Independent Labour Party")],
      "Tilak and Annie Besant set up separate Home Rule Leagues in 1916; Gokhale founded the Servants of India Society (1905).")
    S("Consider the following statements about the Interim Government formed in 1946:",
      [("Jawaharlal Nehru was Vice-President of the Viceroy's Executive Council.", True, "Nehru held this position and External Affairs"),
       ("Rajendra Prasad held the External Affairs portfolio.", False, "External Affairs was with Nehru; Prasad held Food and Agriculture"),
       ("Liaquat Ali Khan held the Finance portfolio.", True, "the Muslim League's Liaquat Ali Khan was Finance Member")],
      "External Affairs and Commonwealth Relations stayed with Nehru himself.")
    A("B. R. Ambedkar is often called the chief architect of the Indian Constitution.",
      "He was the chairman of the Drafting Committee of the Constituent Assembly.",
      True, True, True,
      "As Drafting Committee chairman, Ambedkar piloted the draft through the Assembly — the basis of the title.",
      "The Assembly President (Prasad) is different from the Drafting Committee chairman.")
    M("First office-holder in independent India", "Office",
      [("Vallabhbhai Patel", "Home Minister"), ("Maulana Abul Kalam Azad", "Education Minister"),
       ("B. R. Ambedkar", "Law Minister"), ("R. K. Shanmukham Chetty", "Finance Minister")],
      "Independent India's first Finance Minister was Shanmukham Chetty, who presented the first Budget (1947).")
    S("Consider the following statements about Dadabhai Naoroji:",
      [("He was the first Indian elected to the British House of Commons.", True, "Finsbury Central, 1892"),
       ("He wrote 'Poverty and Un-British Rule in India'.", True, "exposition of the drain theory"),
       ("He founded the Indian Association in 1876.", False, "the Indian Association was founded by Surendranath Banerjee and Ananda Mohan Bose")],
      "The drain theory is Naoroji's; the Indian Association (Calcutta) is Surendranath Banerjee's.")
    C("Arrange the following INC presidencies in chronological order:",
      [("Badruddin Tyabji presides (Madras)", 1887, "1887 — first Muslim president"),
       ("Annie Besant presides (Calcutta)", 1917, "1917"),
       ("Sarojini Naidu presides (Kanpur)", 1925, "1925"),
       ("Abul Kalam Azad presides (Ramgarh)", 1940, "1940")],
      "Azad also presided over a 1923 special session, but the Ramgarh session is 1940.")

    # ================= Medieval Indian empires =================
    h.topic("gk-medieval-indian-empires", "NCERT Class 7 'Our Pasts II'; NCERT Class 12 History Part II; Satish Chandra, 'Medieval India'")
    F("Who founded the Mamluk (Slave) dynasty of the Delhi Sultanate?",
      "Qutb-ud-din Aibak", [("Iltutmish", "consolidated the Sultanate after Aibak"), ("Ghiyas-ud-din Balban", "later Mamluk sultan"),
                            ("Muhammad Ghori", "Aibak's master; never Sultan of Delhi")],
      "Qutb-ud-din Aibak, a slave-general of Muhammad Ghori, became the first Sultan of Delhi in 1206.",
      "Iltutmish is often called the real consolidator, but Aibak is the founder.")
    F("The Vijayanagara Empire was founded in 1336 by:",
      "Harihara and Bukka", [("Krishnadevaraya", "greatest ruler, early 16th century"), ("Deva Raya II", "15th-century ruler"),
                             ("Alauddin Hasan Bahman Shah", "founder of the Bahmani kingdom")],
      "The brothers Harihara I and Bukka Raya I of the Sangama dynasty founded Vijayanagara in 1336.",
      "The Bahmani kingdom (1347) was Vijayanagara's northern rival, founded by a different ruler.")
    F("In the First Battle of Panipat (1526), Babur defeated:",
      "Ibrahim Lodi", [("Rana Sanga", "defeated at Khanwa, 1527"), ("Hemu", "defeated at the Second Battle of Panipat, 1556"),
                       ("Sher Shah Suri", "defeated Humayun, not Babur")],
      "Babur's victory over Ibrahim Lodi in April 1526 founded Mughal rule.",
      "Khanwa (1527) against Rana Sanga came a year later.")
    F("Which Delhi Sultan introduced a token currency of copper and brass coins?",
      "Muhammad bin Tughluq", [("Alauddin Khalji", "known for market-control measures"), ("Firoz Shah Tughluq", "known for public works and canals"),
                               ("Sher Shah Suri", "introduced the silver rupiya")],
      "Muhammad bin Tughluq issued token coins valued at par with silver; widespread forgery forced their withdrawal.",
      "Sher Shah (a later Afghan ruler) standardised the silver rupiya — a different reform.")
    F("Rajendra Chola I built a new capital named:",
      "Gangaikondacholapuram", [("Thanjavur", "capital under Rajaraja I"), ("Madurai", "Pandya capital"), ("Kanchipuram", "Pallava capital")],
      "Rajendra I commemorated his northern campaign to the Ganga by founding Gangaikondacholapuram.",
      "Thanjavur (Brihadeeswara temple) was his father Rajaraja I's capital.", lv="L2")
    C("Arrange the following battles in chronological order:",
      [("Second Battle of Tarain", 1192, "1192"), ("First Battle of Panipat", 1526, "1526"),
       ("Battle of Talikota", 1565, "1565"), ("Battle of Haldighati", 1576, "1576")],
      "Talikota (1565) precedes Haldighati (1576) by eleven years.")
    M("Ruler", "Measure associated",
      [("Iltutmish", "Silver tanka and copper jital"), ("Alauddin Khalji", "Market control and price regulation"),
       ("Sher Shah Suri", "Silver rupiya"), ("Akbar", "Mansabdari system")],
      "Tanka (Iltutmish) vs rupiya (Sher Shah): both silver, three centuries apart.")
    N("Consider the following statements about the Vijayanagara Empire:",
      [("Krishnadevaraya composed Amuktamalyada in Telugu.", True, "a Telugu work on the Alvar saint Andal"),
       ("Hampi was the site of its capital.", True, "the capital city of Vijayanagara lies at Hampi"),
       ("Its decline set in after the defeat at Talikota (1565) by the Deccan Sultanates.", True, "the capital was sacked afterwards"),
       ("The Persian envoy Abdur Razzaq visited during Krishnadevaraya's reign.", False, "Abdur Razzaq visited under Deva Raya II (1440s)")],
      "Domingo Paes and Nuniz belong to Krishnadevaraya's time; Abdur Razzaq to Deva Raya II's.")
    A("Alauddin Khalji introduced branding of horses (dagh) and descriptive rolls of soldiers (huliya).",
      "These measures were introduced to fix the prices of foodgrains in the markets of Delhi.",
      True, False, False,
      ["A is true.", "R is false: dagh and huliya were anti-fraud checks at military musters; price control was a separate set of market reforms."],
      "These are military reforms, distinct from his market-control measures.")
    S("Consider the following statements about the Cholas:",
      [("Rajaraja I built the Brihadeeswara temple at Thanjavur.", True, "completed c. 1010 CE"),
       ("Rajendra I sent a naval expedition against Srivijaya in Southeast Asia.", True, "c. 1025 CE"),
       ("The Uttaramerur inscriptions describe the working of village assemblies.", True, "inscriptions of Parantaka I on the sabha")],
      "All three are standard Chola facts.")
    M("Monument", "Built by / commissioned by",
      [("Buland Darwaza", "Akbar"), ("Taj Mahal", "Shah Jahan"), ("Tomb of Itimad-ud-Daula", "Nur Jahan"),
       ("Bibi ka Maqbara", "Azam Shah")],
      "Bibi ka Maqbara (Aurangabad) was built by Aurangzeb's son Azam Shah for his mother.")
    C("Arrange the following dynasties of the Delhi Sultanate in the order in which they came to power:",
      [("Khalji", 1290, "1290"), ("Tughluq", 1320, "1320"), ("Sayyid", 1414, "1414"), ("Lodi", 1451, "1451")],
      "Sayyids (1414) preceded the Lodis (1451).", lv="L2")
    A("Sher Shah Suri's administration is regarded as a forerunner of Mughal administration under Akbar.",
      "Sher Shah introduced measurement-based land revenue assessment and the silver rupiya, which Akbar retained and refined.",
      True, True, True,
      "Todar Mal, who had served Sher Shah, later framed Akbar's revenue system on similar lines.",
      "R names the specific continuities that justify A.")
    S("Consider the following statements about the Bahmani kingdom:",
      [("It was founded in 1347 by Alauddin Hasan Bahman Shah.", True, "founded after revolt against Muhammad bin Tughluq"),
       ("Mahmud Gawan, a noted minister, built a madrasa at Bidar.", True, "the Madrasa of Mahmud Gawan survives at Bidar"),
       ("Its first capital was Golconda.", False, "the first capital was Gulbarga (Hasanabad); later Bidar")],
      "Golconda was the Qutb Shahi capital after the Bahmani break-up.", ask="incorrect")
    M("Ashtapradhan office (Shivaji)", "Function",
      [("Peshwa", "Prime minister / general administration"), ("Amatya", "Finance and revenue accounts"),
       ("Sumant", "Foreign affairs"), ("Nyayadhish", "Justice")],
      "Sumant (Dabir) handled foreign affairs; Sachiv handled royal correspondence.")

    # ================= National memorials and samadhis =================
    h.topic("gk-national-memorials-and-samadhis", "Ministry of Culture / Ministry of Housing and Urban Affairs records; PIB releases")
    F("Shantivan in Delhi is the memorial (samadhi) of:",
      "Jawaharlal Nehru", [("Lal Bahadur Shastri", "Vijay Ghat"), ("Indira Gandhi", "Shakti Sthal"), ("Rajiv Gandhi", "Veer Bhumi")],
      "Shantivan, on the banks of the Yamuna, marks Nehru's cremation site.",
      "All four sites are close together along the Yamuna — match names carefully.")
    F("Kisan Ghat in Delhi is the memorial of:",
      "Chaudhary Charan Singh", [("Morarji Desai", "Abhay Ghat, Ahmedabad"), ("Jagjivan Ram", "Samata Sthal"),
                                 ("Giani Zail Singh", "Ekta Sthal")],
      "Kisan Ghat honours Charan Singh, the farmers' leader and fifth Prime Minister.",
      "'Kisan' points to Charan Singh's farmer constituency.")
    F("The Statue of Unity, depicting Sardar Vallabhbhai Patel, stands at:",
      "Ekta Nagar, Gujarat", [("Karamsad, Gujarat", "Patel's ancestral village"), ("Ahmedabad, Gujarat", "site of Sabarmati Ashram"),
                                        ("Nadiad, Gujarat", "Patel's birthplace")],
      "The statue stands near the Sardar Sarovar Dam on the Narmada at Ekta Nagar (Kevadia), Narmada district.",
      "Patel was born at Nadiad and grew up in Karamsad — neither hosts the statue.")
    F("India Gate (originally the All India War Memorial) in New Delhi was designed by:",
      "Edwin Lutyens", [("Herbert Baker", "designed the Secretariat blocks and Parliament House"),
                        ("Robert Tor Russell", "designed Connaught Place"), ("Charles Correa", "post-independence architect")],
      "Sir Edwin Lutyens designed India Gate, completed in 1931.",
      "Baker co-planned New Delhi but India Gate is Lutyens' work.")
    F("The National Police Memorial of India is located in:",
      "Chanakyapuri, New Delhi", [("Hyderabad, Telangana", "home of the SVP National Police Academy"),
                                  ("Mount Abu, Rajasthan", "CRPF/IB training centres"), ("Nashik, Maharashtra", "state police academy")],
      "The National Police Memorial at Chanakyapuri was dedicated to the nation on Police Commemoration Day, 21 October 2018.",
      "The police training academy (Hyderabad) is not the memorial.", lv="L2")
    M("Samadhi (Delhi)", "Leader",
      [("Vijay Ghat", "Lal Bahadur Shastri"), ("Shakti Sthal", "Indira Gandhi"), ("Veer Bhumi", "Rajiv Gandhi"),
       ("Samata Sthal", "Jagjivan Ram")],
      "Shakti Sthal (Indira) and Veer Bhumi (Rajiv) are adjacent — do not swap them.", lv="L2")
    M("Memorial", "Leader commemorated",
      [("Mahaprayan Ghat (Patna)", "Dr Rajendra Prasad"), ("Chaitya Bhoomi (Mumbai)", "Dr B. R. Ambedkar"),
       ("Abhay Ghat (Ahmedabad)", "Morarji Desai"), ("Sadaiv Atal (Delhi)", "Atal Bihari Vajpayee")],
      "Several leaders' memorials are outside Delhi: Prasad in Patna, Ambedkar in Mumbai, Morarji Desai in Ahmedabad.")
    N("Consider the following statements about the National War Memorial, New Delhi:",
      [("It is located in the C-Hexagon around India Gate.", True, "adjacent to India Gate"),
       ("It was inaugurated in 2019.", True, "dedicated on 25 February 2019"),
       ("Its concentric circles are named Amar Chakra, Veerta Chakra, Tyag Chakra and Rakshak Chakra.", True, "four concentric circles"),
       ("It commemorates only soldiers who died in the 1971 war.", False, "it honours soldiers who died in all post-independence conflicts and operations")],
      "The 1971 link is Amar Jawan Jyoti's origin, not the scope of the National War Memorial.")
    A("India Gate carries the names of Indian soldiers.",
      "It was built as the All India War Memorial to commemorate soldiers of the British Indian Army who died in the First World War and the Third Anglo-Afghan War.",
      True, True, True,
      "As a war memorial, India Gate is inscribed with names of fallen soldiers of those wars.",
      "The names are from WWI and the Afghan war, not from post-independence wars.")
    C("Arrange the following in the order in which they were opened/inaugurated:",
      [("Victoria Memorial, Kolkata", 1921, "1921"), ("Statue of Unity", 2018, "31 October 2018"),
       ("National War Memorial", 2019, "February 2019"), ("Pradhanmantri Sangrahalaya (Teen Murti complex)", 2022, "April 2022")],
      "The Statue of Unity (Oct 2018) narrowly precedes the War Memorial (Feb 2019).")
    S("Consider the following statements:",
      [("Mahatma Gandhi was assassinated at Birla House, now known as Gandhi Smriti.", True, "30 January 1948, New Delhi"),
       ("Raj Ghat lies on the banks of the Yamuna.", True, "Gandhi's cremation site in Delhi"),
       ("The Dandi March of 1930 began from Sevagram Ashram, Wardha.", False, "it began from Sabarmati Ashram, Ahmedabad")],
      "Sevagram came later (1936); Dandi March started at Sabarmati.")
    A("The National Martyrs Memorial is located at Hussainiwala in Punjab.",
      "Bhagat Singh, Rajguru and Sukhdev were cremated near Hussainiwala after their execution in 1931.",
      True, True, True,
      "The memorial marks the cremation site of the three revolutionaries on the Sutlej near Ferozepur.",
      "They were executed in Lahore jail but cremated at Hussainiwala.")
    S("Consider the following statements about the Statue of Unity:",
      [("It was inaugurated on 2 October 2018.", False, "it was inaugurated on 31 October 2018, Patel's birth anniversary (Rashtriya Ekta Diwas)"),
       ("It is 182 metres tall.", True, "182 m"),
       ("Its sculptor was Ram V. Sutar.", True, "designed by Ram V. Sutar")],
      "2 October is Gandhi Jayanti; Patel's anniversary is 31 October.")
    M("Memorial / monument", "Location",
      [("Victoria Memorial", "Kolkata"), ("Jallianwala Bagh", "Amritsar"),
       ("Cellular Jail National Memorial", "Andaman and Nicobar Islands"), ("Gateway of India", "Mumbai")],
      "Cellular Jail (Kala Pani) was declared a national memorial in 1979.", lv="L2")
    A("The Amar Jawan Jyoti flame was merged with the eternal flame at the National War Memorial in 2022.",
      "Amar Jawan Jyoti was originally established beneath India Gate after the 1971 war.",
      True, True, False,
      ["The merger (January 2022) was done to have one flame at the National War Memorial, which bears names of all post-independence martyrs.",
       "R only states the flame's origin; it does not explain why it was merged."],
      "True historical background is not the same as the reason for the event in A.")

    # ================= Post-independence revolutions and their pioneers =================
    h.topic("gk-post-independence-revolutions", "NCERT Class 9/12 Economics; NDDB and Ministry of Agriculture publications")
    F("Who is known as the 'Father of the White Revolution' in India?",
      "Verghese Kurien", [("M. S. Swaminathan", "Green Revolution scientist"), ("Tribhuvandas Patel", "founder chairman of the Kaira milk union"),
                          ("Norman Borlaug", "Green Revolution pioneer worldwide")],
      "Verghese Kurien led the National Dairy Development Board and Operation Flood.",
      "Tribhuvandas Patel organised the Kaira cooperative, but the White Revolution is credited to Kurien.")
    F("The 'Yellow Revolution' in India is associated with increased production of:",
      "Oilseeds", [("Eggs", "Silver Revolution"), ("Honey", "often called the 'Sweet Revolution'"), ("Fertilisers", "Grey Revolution")],
      "The Yellow Revolution refers to the drive for self-reliance in edible oilseeds (Technology Mission on Oilseeds, 1986).",
      "Colours map to sectors: yellow = oilseeds (mustard, sunflower).")
    F("The 'Blue Revolution' refers to development of:",
      "Fish production", [("Milk production", "White Revolution"), ("Oilseed production", "Yellow Revolution"),
                                    ("Poultry and eggs", "Silver Revolution")],
      "Blue Revolution = growth of fish production (inland and marine).",
      "Blue for water — fisheries.")
    F("Operation Flood was launched in 1970 by:",
      "National Dairy Development Board", [("NABARD", "set up only in 1982"), ("Indian Council of Agricultural Research", "research body"),
                                           ("Food Corporation of India", "foodgrain procurement agency")],
      "NDDB (Anand, set up 1965) launched and implemented Operation Flood from 1970.",
      "NABARD did not exist in 1970.")
    F("The 'Silver Revolution' is associated with:",
      "Egg production", [("Potato production", "Round Revolution"), ("Fish production", "Blue Revolution"),
                                     ("Jute production", "Golden Fibre Revolution")],
      "Silver Revolution refers to growth in egg/poultry output.",
      "Round = potato; Golden fibre = jute.", lv="L2")
    M("Revolution", "Sector",
      [("Green Revolution", "Foodgrains"), ("Round Revolution", "Potato"), ("Golden Fibre Revolution", "Jute"),
       ("Grey Revolution", "Fertilisers")],
      "Golden FIBRE = jute; 'Golden Revolution' alone usually denotes horticulture/honey.", lv="L2")
    S("Consider the following statements about the Green Revolution in India:",
      [("It relied on high-yielding varieties, especially of wheat.", True, "HYV wheat (Mexican dwarf varieties) was central"),
       ("Norman Borlaug received the Nobel Peace Prize in 1970.", True, "for his work on high-yielding wheat"),
       ("In its early phase it benefited pulses more than wheat.", False, "wheat (and later rice) gained most; pulses lagged")],
      "The Green Revolution was largely a wheat revolution in its first phase.")
    A("Operation Flood is widely referred to as the White Revolution.",
      "The National Dairy Development Board, which implemented it, is headquartered at Anand in Gujarat.",
      True, True, False,
      ["Both statements are true.", "The name 'White Revolution' comes from the surge in milk output, not from NDDB's location."],
      "White = milk.")
    C("Arrange the following in chronological order:",
      [("Formation of the Kaira District Co-operative Milk Producers' Union (Amul)", 1946, "1946"),
       ("Establishment of the National Dairy Development Board", 1965, "1965"),
       ("Launch of Operation Flood", 1970, "1970"), ("Establishment of NABARD", 1982, "1982")],
      "NDDB (1965) predates Operation Flood (1970).")
    S("Consider the following statements about M. S. Swaminathan:",
      [("He was the first recipient of the World Food Prize.", True, "awarded in 1987"),
       ("He was the first Chairman of the National Dairy Development Board.", False, "Verghese Kurien was NDDB's founder chairman"),
       ("He chaired the National Commission on Farmers set up in 2004.", True, "the 'Swaminathan Commission'")],
      "Dairy = Kurien; farmers' commission = Swaminathan.")
    A("The Green Revolution benefited all crops and all regions of India equally.",
      "High-yielding variety technology required assured irrigation, fertilisers and credit.",
      False, True, False,
      ["A is false: gains were concentrated in wheat and in irrigated areas such as Punjab, Haryana and western UP.",
       "R is true — and it is precisely why the gains were uneven."],
      "A true R can undermine a false A.")
    M("Person", "Associated with",
      [("Verghese Kurien", "Operation Flood"), ("M. S. Swaminathan", "Green Revolution in India"),
       ("Sam Pitroda", "Centre for Development of Telematics (C-DOT)"), ("Tribhuvandas Patel", "Founder chairman of the Kaira milk union")],
      "Sam Pitroda's telecom mission is separate from the agricultural 'colour' revolutions.")
    S("Consider the following statements about Amul:",
      [("It is based at Anand in Gujarat.", True, "Kaira District Co-operative Milk Producers' Union, Anand"),
       ("It follows a three-tier cooperative model: village society, district union and state federation.", True, "the 'Anand pattern'"),
       ("Gujarat Cooperative Milk Marketing Federation markets products under the Amul brand.", True, "GCMMF is the apex marketing body")],
      "All three are correct features of the Anand pattern.")
    A("National Milk Day is observed in India on 26 November.",
      "26 November is the birth anniversary of Verghese Kurien.",
      True, True, True,
      "National Milk Day honours Kurien, born on 26 November 1921.",
      "26 November is also Constitution Day — both are observed on the same date.")
    N("Consider the following statements:",
      [("India is the world's largest producer of milk.", True, "India has held first place since the late 1990s"),
       ("Operation Flood was implemented in three phases.", True, "Phase I 1970–80, II 1981–85, III 1985–96"),
       ("Phase I of Operation Flood was financed partly by the sale of donated skimmed milk powder and butter oil.", True, "donated via the World Food Programme"),
       ("Operation Flood was launched by the Ministry of Food Processing Industries in 1990.", False, "it was launched by NDDB in 1970")],
      "Operation Flood predates the food-processing ministry by two decades.")
