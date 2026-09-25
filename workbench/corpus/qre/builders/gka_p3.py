"""QRE-GK-A part 3 — International Relations (5 microtopics x 15)."""
from gka_h import H


def add_all(B):
    h = H(B, "")
    F, S, N, M, C, A = h.F, h.S, h.N, h.M, h.C, h.A

    # ================= International agreements and declarations =================
    h.topic("gk-international-agreements", "UNEP / UNFCCC / treaty secretariat websites; MEA treaty database; NCERT Class 12 Political Science")
    F("The Montreal Protocol (1987) deals with:",
      "Ozone-depleting substances", [("Greenhouse gas emission targets", "Kyoto Protocol"), ("Transboundary hazardous waste", "Basel Convention"),
                                     ("Conservation of wetlands", "Ramsar Convention")],
      "The Montreal Protocol phases out substances that deplete the ozone layer (CFCs, halons etc.).", "Kyoto is the climate treaty; Montreal is ozone.")
    F("The Ramsar Convention (1971) relates to the conservation of:",
      "Wetlands", [("Endangered species in trade", "CITES"), ("Drylands against desertification", "UNCCD"), ("Migratory species", "CMS (Bonn Convention)")],
      "The Convention on Wetlands was signed at Ramsar, Iran, in 1971.", "Named after the Iranian city where it was signed.")
    F("The Universal Declaration of Human Rights was adopted by the UN General Assembly in:",
      "1948", [("1945", "UN Charter"), ("1950", "European Convention on Human Rights"), ("1966", "the two International Covenants")],
      "The UDHR was adopted on 10 December 1948 — now Human Rights Day.", "1966 covenants are binding treaties that followed the Declaration.")
    F("The Simla Agreement of 1972 was signed between:",
      "India and Pakistan", [("India and China", "Panchsheel, 1954"), ("India and Bangladesh", "Treaty of Friendship, 1972"),
                             ("India and Sri Lanka", "Indo-Sri Lanka Accord, 1987")],
      "Indira Gandhi and Z. A. Bhutto signed the Simla Agreement after the 1971 war.", "Indo-Bangladesh friendship treaty was also 1972 — different treaty.")
    F("The Panchsheel principles were first formally set out in a 1954 agreement between India and:",
      "China", [("Nepal", "1950 Treaty of Peace and Friendship"), ("Soviet Union", "1971 Treaty of Friendship"), ("Pakistan", "no such agreement")],
      "The Five Principles of Peaceful Coexistence appear in the 1954 India–China agreement on trade with the Tibet region.",
      "Panchsheel is India–China, 1954.", lv="L2")
    M("Convention", "Subject",
      [("CITES", "International trade in endangered species"), ("Basel Convention", "Transboundary movement of hazardous wastes"),
       ("Stockholm Convention", "Persistent organic pollutants"), ("Minamata Convention", "Mercury")],
      "Stockholm Convention (2001) should not be confused with the 1972 Stockholm Conference.", lv="L2")
    C("Arrange the following in chronological order:",
      [("Vienna Convention for the Protection of the Ozone Layer", 1985, "1985"), ("Montreal Protocol", 1987, "1987"),
       ("Kyoto Protocol", 1997, "1997"), ("Paris Agreement", 2015, "2015")],
      "The Vienna Convention (framework) came before the Montreal Protocol.")
    S("Consider the following statements about the Paris Agreement:",
      [("It assigns legally binding emission-reduction targets only to developed countries, as the Kyoto Protocol did.", False,
        "all parties submit nationally determined contributions (NDCs)"),
       ("It was adopted at COP21 of the UNFCCC.", True, "December 2015"),
       ("It aims to hold warming well below 2°C and pursue efforts to limit it to 1.5°C.", True, "Art. 2")],
      "The top-down Annex I targets belong to Kyoto; Paris is bottom-up.")
    A("The Kigali Amendment to the Montreal Protocol contributes to tackling climate change.",
      "It phases down hydrofluorocarbons, which are potent greenhouse gases though they do not deplete ozone.",
      True, True, True, "HFCs replaced CFCs but have high global-warming potential; the 2016 Kigali Amendment targets them.",
      "An ozone treaty being used for a climate goal is the key idea.")
    M("Export-control regime", "Focus",
      [("Missile Technology Control Regime", "Missiles and unmanned delivery systems"), ("Wassenaar Arrangement", "Conventional arms and dual-use goods"),
       ("Australia Group", "Chemical and biological weapons precursors"), ("Nuclear Suppliers Group", "Nuclear-related exports")],
      "India is a member of the first three but not the NSG.")
    N("Consider the following statements about India:",
      [("India has not signed the Nuclear Non-Proliferation Treaty.", True, "India regards it as discriminatory"),
       ("India has not signed the Comprehensive Nuclear-Test-Ban Treaty.", True, "not a signatory"),
       ("India is a member of the Missile Technology Control Regime.", True, "joined in 2016"),
       ("India is a member of the Nuclear Suppliers Group.", False, "India's application is pending")],
      "MTCR, Wassenaar and Australia Group — yes; NSG — no.")
    C("Arrange the following India–Pakistan agreements in chronological order:",
      [("Indus Waters Treaty", 1960, "1960"), ("Tashkent Declaration", 1966, "1966"), ("Simla Agreement", 1972, "1972"),
       ("Lahore Declaration", 1999, "1999")],
      "Tashkent followed the 1965 war; Simla followed the 1971 war.")
    A("The Kyoto Protocol reflected the principle of common but differentiated responsibilities.",
      "Under it, only Annex I (developed) countries had binding emission-reduction targets.",
      True, True, True, "Placing binding targets only on developed countries is the differentiation that CBDR requires.", "R illustrates how CBDR was applied.")
    S("Consider the following statements about the 1992 Rio Earth Summit:",
      [("The UNFCCC was opened for signature there.", True, "June 1992"),
       ("The Kyoto Protocol was adopted there.", False, "Kyoto was adopted at COP3 in 1997"),
       ("The Convention on Biological Diversity was opened for signature there.", True, "June 1992")],
      "Rio produced the framework conventions; protocols came later.")
    M("Protocol / amendment", "Parent instrument",
      [("Kyoto Protocol", "UNFCCC"), ("Cartagena Protocol", "Convention on Biological Diversity"),
       ("Montreal Protocol", "Vienna Convention for the Protection of the Ozone Layer"), ("Kigali Amendment", "Montreal Protocol")],
      "Cartagena (biosafety) and Nagoya (access and benefit-sharing) both sit under the CBD.")

    # ================= International organisations and groupings =================
    h.topic("gk-international-organisations", "Official websites of the UN system and regional organisations; UN Charter")
    F("The headquarters of UNESCO is in:",
      "Paris", [("Geneva", "WHO, ILO"), ("Rome", "FAO"), ("New York", "UN Secretariat")],
      "UNESCO is headquartered in Paris.", "Geneva hosts many UN bodies, but not UNESCO.")
    F("The SAARC Secretariat is located in:",
      "Kathmandu", [("Dhaka", "SAARC was founded there; BIMSTEC secretariat"), ("New Delhi", "incorrect"), ("Colombo", "incorrect")],
      "SAARC (founded Dhaka, 1985) has its Secretariat at Kathmandu.", "Founding city ≠ secretariat city.")
    F("The headquarters of the International Solar Alliance is at:",
      "Gurugram, India", [("Paris, France", "where the ISA was launched at COP21"), ("Abu Dhabi, UAE", "IRENA headquarters"),
                          ("Bonn, Germany", "UNFCCC secretariat")],
      "The ISA secretariat is at Gwal Pahari, Gurugram (Haryana).", "IRENA (Abu Dhabi) is a different body.")
    F("The United Nations Environment Programme is headquartered in:",
      "Nairobi", [("Geneva", "incorrect"), ("Vienna", "IAEA, UNIDO"), ("Bonn", "UNFCCC")],
      "UNEP, created after the 1972 Stockholm Conference, is based in Nairobi.", "Nairobi also hosts UN-Habitat.")
    F("The New Development Bank set up by BRICS countries is headquartered in:",
      "Shanghai", [("Beijing", "AIIB headquarters"), ("Moscow", "incorrect"), ("New Delhi", "incorrect")],
      "The NDB is headquartered in Shanghai.", "AIIB (Beijing) and NDB (Shanghai) are both in China.", lv="L2")
    M("Organisation", "Headquarters",
      [("Food and Agriculture Organization", "Rome"), ("International Atomic Energy Agency", "Vienna"),
       ("International Civil Aviation Organization", "Montreal"), ("International Maritime Organization", "London")],
      "ICAO is the only UN specialised agency in Canada.", lv="L2")
    S("Consider the following statements about the UN Security Council:",
      [("It has 15 members.", True, "5 permanent and 10 non-permanent"),
       ("A retiring non-permanent member is eligible for immediate re-election.", False, "Art. 23(2) bars immediate re-election"),
       ("Non-permanent members are elected by the General Assembly for two-year terms.", True, "Art. 23")],
      "No back-to-back terms for non-permanent members.", ref="Charter of the United Nations, Art. 23")
    C("Arrange the following organisations in the order of their founding:",
      [("League of Nations", 1920, "1920"), ("United Nations", 1945, "1945"), ("NATO", 1949, "1949"), ("ASEAN", 1967, "1967")],
      "NATO (1949) came four years after the UN.")
    A("India is a founding member of the United Nations although it became independent only in 1947.",
      "British India signed the Declaration by United Nations (1942) and took part in the San Francisco Conference of 1945.",
      True, True, True, "India signed the Charter in 1945 as one of the 51 original members.", "Membership pre-dates independence.")
    M("Grouping", "Year and place of founding",
      [("SAARC", "1985, Dhaka"), ("BIMSTEC", "1997, Bangkok"), ("ASEAN", "1967, Bangkok"), ("OPEC", "1960, Baghdad")],
      "Both ASEAN and BIMSTEC were founded in Bangkok — the year separates them.")
    N("Consider the following statements about the International Court of Justice:",
      [("It sits at The Hague.", True, "Peace Palace"), ("It has 15 judges elected for nine-year terms.", True, "Statute of the ICJ"),
       ("Judges are elected by the General Assembly and the Security Council voting separately.", True, "absolute majority in both"),
       ("Only states may be parties in contentious cases before it.", True, "Art. 34 of the Statute")],
      "All four are correct.", ref="Statute of the International Court of Justice")
    A("The Hague hosts both the International Court of Justice and the International Criminal Court.",
      "The International Criminal Court is a principal organ of the United Nations.",
      True, False, False, ["A is true.", "R is false: the ICC is an independent treaty-based court under the Rome Statute; the ICJ is the UN organ."],
      "ICJ (UN, disputes between states) vs ICC (Rome Statute, individuals).")
    S("Consider the following statements about BIMSTEC:",
      [("Pakistan is a member.", False, "members: Bangladesh, Bhutan, India, Myanmar, Nepal, Sri Lanka, Thailand"),
       ("Its members include countries of South Asia and Southeast Asia.", True, "Myanmar and Thailand are Southeast Asian"),
       ("Its secretariat is at Dhaka.", True, "since 2014")],
      "BIMSTEC bridges South and Southeast Asia and excludes Pakistan.", ask="incorrect")
    M("Specialised agency", "Headquarters",
      [("World Intellectual Property Organization", "Geneva"), ("Universal Postal Union", "Bern"),
       ("UN Industrial Development Organization", "Vienna"), ("International Fund for Agricultural Development", "Rome")],
      "UPU is in Bern, not Geneva.")
    S("Consider the following statements:",
      [("The IMF and the World Bank (IBRD) originated at the Bretton Woods Conference of 1944.", True, "July 1944"),
       ("Both are headquartered in Washington, D.C.", True, "yes"),
       ("The International Development Association is part of the World Bank Group.", True, "the soft-loan window")],
      "All three statements are correct.")

    # ================= International summits and forums =================
    h.topic("gk-international-summits", "Official forum websites; MEA briefs; NCERT Class 12 Political Science (Contemporary World Politics)")
    F("The first summit of the Non-Aligned Movement was held in 1961 at:",
      "Belgrade", [("Bandung", "1955 Asian–African Conference"), ("Cairo", "second NAM summit, 1964"), ("New Delhi", "seventh NAM summit, 1983")],
      "The first NAM summit was held in Belgrade, Yugoslavia, in September 1961.", "Bandung (1955) was the precursor, not a NAM summit.")
    F("The Raisina Dialogue, a conference on geopolitics and geoeconomics, is held annually in:",
      "New Delhi", [("Singapore", "Shangri-La Dialogue"), ("Munich", "Munich Security Conference"), ("Davos", "World Economic Forum")],
      "The Raisina Dialogue is co-hosted by the Observer Research Foundation and MEA in New Delhi (since 2016).",
      "Raisina Hill is in New Delhi.")
    F("The Shangri-La Dialogue, an Asian security summit, is held in:",
      "Singapore", [("Jakarta", "ASEAN Secretariat"), ("Tokyo", "incorrect"), ("Kuala Lumpur", "first East Asia Summit, 2005")],
      "Organised by the IISS, it is named after the Shangri-La Hotel in Singapore.", "Named after its hotel venue.")
    F("The annual meeting of the World Economic Forum is held at:",
      "Davos", [("Geneva", "WEF headquarters (Cologny)"), ("Vienna", "incorrect"), ("Zurich", "incorrect")],
      "The WEF annual meeting is held in Davos-Klosters, Switzerland.", "The WEF's headquarters are near Geneva, but the meeting is in Davos.")
    F("The first summit of BRIC countries was held in 2009 at:",
      "Yekaterinburg", [("Brasília", "second summit, 2010"), ("Durban", "fifth summit, 2013"), ("Goa", "eighth summit, 2016")],
      "The first BRIC summit was held in Yekaterinburg, Russia, in June 2009.", "South Africa joined later, making it BRICS.", lv="L2")
    C("Arrange the following in chronological order:",
      [("Bandung Conference", 1955, "1955"), ("First NAM summit, Belgrade", 1961, "1961"),
       ("UN Conference on the Human Environment, Stockholm", 1972, "1972"), ("UN Conference on Environment and Development, Rio", 1992, "1992")],
      "Stockholm (1972) is twenty years before Rio (1992).")
    N("Consider the following statements about the G20:",
      [("It was created in 1999 as a forum of finance ministers and central bank governors.", True, "after the Asian financial crisis"),
       ("Its first leaders' summit was held in Washington, D.C., in 2008.", True, "November 2008"),
       ("The African Union became a permanent member at the New Delhi summit in 2023.", True, "September 2023"),
       ("It has a permanent secretariat.", False, "it works through a rotating presidency and troika")],
      "G20 has no permanent secretariat.")
    A("UNEP was established following the 1972 Stockholm Conference.",
      "World Environment Day (5 June) marks the opening day of the Stockholm Conference.",
      True, True, False, ["Both statements are true.", "The date of World Environment Day does not explain why UNEP was established."],
      "Two outcomes of the same event do not explain each other.")
    M("Forum", "Year founded / first held",
      [("World Economic Forum", "1971"), ("Asia-Pacific Economic Cooperation", "1989"), ("Shanghai Cooperation Organisation", "2001"),
       ("East Asia Summit", "2005")],
      "SCO (2001) grew out of the 'Shanghai Five' of 1996.")
    S("Consider the following statements about the Shanghai Cooperation Organisation:",
      [("It was founded in 2001 in Shanghai.", True, "June 2001"), ("India and Pakistan became full members in 2017.", True, "Astana summit"),
       ("Its secretariat is in Beijing.", True, "yes")],
      "All three statements are correct.")
    A("The G7 began as a group of six countries.",
      "Canada was a participant at the first summit at Rambouillet in 1975.",
      True, False, False, ["A is true.", "R is false: Canada joined only in 1976; Rambouillet (1975) had six members."], "Canada is the seventh, added a year later.")
    S("Consider the following statements:",
      [("The first Conference of the Parties (COP1) to the UNFCCC was held in Berlin in 1995.", True, "yes"),
       ("The Kyoto Protocol was adopted at COP3.", True, "1997"),
       ("COP26 was held in Paris.", False, "COP26 was held in Glasgow (2021); Paris hosted COP21")],
      "Glasgow = COP26; Paris = COP21.")
    C("Arrange the following Second World War conferences and declarations in chronological order:",
      [("Atlantic Charter", 1941, "August 1941"), ("Tehran Conference", 1943, "November 1943"),
       ("Yalta Conference", 1945.1, "February 1945"), ("Potsdam Conference", 1945.6, "July 1945")],
      "Yalta and Potsdam were both in 1945 — Yalta first.")
    A("The Bandung Conference of 1955 is regarded as a precursor of the Non-Aligned Movement.",
      "It brought together newly independent Asian and African states that discussed decolonisation and peaceful coexistence.",
      True, True, True, "Bandung's Afro-Asian solidarity and principles fed directly into NAM (1961).", "R explains the link.")
    S("Consider the following statements about the Quad:",
      [("Its members are India, the United States, Japan and Australia.", True, "Quadrilateral Security Dialogue"),
       ("Its first leaders' summit was held virtually in 2021.", True, "March 2021"),
       ("It is based on a founding treaty with a permanent secretariat.", False, "it is an informal grouping without a treaty or secretariat")],
      "The Quad is informal.")

    # ================= Sustainable Development Goals =================
    h.topic("gk-sustainable-development-goals", "UN, 'Transforming our World: the 2030 Agenda for Sustainable Development' (A/RES/70/1); NITI Aayog SDG India Index")
    F("How many Sustainable Development Goals are there?",
      "17", [("8", "number of Millennium Development Goals"), ("15", "incorrect"), ("169", "number of SDG targets")],
      "The 2030 Agenda has 17 goals and 169 targets.", "8 = MDGs; 169 = targets.")
    F("SDG 14 is:",
      "Life below water", [("Life on land", "SDG 15"), ("Climate action", "SDG 13"), ("Clean water and sanitation", "SDG 6")],
      "SDG 14 concerns oceans, seas and marine resources.", "13, 14, 15 = climate, sea, land.")
    F("The target year for achieving the SDGs is:",
      "2030", [("2025", "incorrect"), ("2035", "incorrect"), ("2047", "India's centenary of independence, not the SDG target")],
      "The SDGs form the 2030 Agenda.", "The agenda's name gives the year.")
    F("SDG 5 is:",
      "Gender equality", [("Quality education", "SDG 4"), ("Reduced inequalities", "SDG 10"), ("Decent work and economic growth", "SDG 8")],
      "SDG 5 aims to achieve gender equality and empower all women and girls.", "Reduced inequalities (10) is broader, between and within countries.")
    F("The SDG India Index is released by:",
      "NITI Aayog", [("Ministry of Statistics and Programme Implementation", "maintains the National Indicator Framework"),
                     ("Finance Commission", "constitutional body for fiscal transfers"), ("Reserve Bank of India", "monetary authority")],
      "NITI Aayog has published the SDG India Index since 2018.", "MoSPI's role is the indicator framework, not the index.", lv="L2")
    M("SDG", "Theme",
      [("SDG 7", "Affordable and clean energy"), ("SDG 11", "Sustainable cities and communities"),
       ("SDG 12", "Responsible consumption and production"), ("SDG 16", "Peace, justice and strong institutions")],
      "SDG 12 is consumption/production; SDG 11 is cities.", lv="L2")
    S("Consider the following statements about the SDGs:",
      [("They apply only to developing countries.", False, "they are universal"),
       ("They were adopted by the UN General Assembly in 2015.", True, "September 2015"),
       ("They comprise 169 targets.", True, "yes")],
      "Universality is a defining feature of the SDGs.")
    A("The SDGs are described as universal, unlike the MDGs.",
      "The MDGs focused mainly on developing countries, while the SDGs apply to all countries.",
      True, True, True, "The difference in scope explained in R is what 'universal' means.", "R explains A.")
    N("Consider the following and state how many are among the '5 Ps' of the 2030 Agenda:",
      [("Planet", True, "one of the 5 Ps"), ("Prosperity", True, "one of the 5 Ps"),
       ("Productivity", False, "not one of them; the 5 Ps are People, Planet, Prosperity, Peace and Partnership"),
       ("Partnership", True, "one of the 5 Ps")],
      "Productivity is a plausible-sounding intruder.")
    C("Arrange the following in chronological order:",
      [("Stockholm Conference on the Human Environment", 1972, "1972"), ("UN Millennium Declaration", 2000, "2000"),
       ("Rio+20 Conference", 2012, "2012"), ("Adoption of the 2030 Agenda", 2015, "2015")],
      "Rio+20 (2012) initiated the SDG process completed in 2015.")
    M("SDG", "Theme",
      [("SDG 2", "Zero hunger"), ("SDG 6", "Clean water and sanitation"), ("SDG 9", "Industry, innovation and infrastructure"),
       ("SDG 10", "Reduced inequalities")],
      "Zero hunger is SDG 2, not SDG 1 (no poverty).", lv="L2")
    A("SDG 17 focuses on means of implementation rather than a single sectoral outcome.",
      "It covers finance, technology, capacity building, trade and systemic issues through a global partnership.",
      True, True, True, "SDG 17 (Partnerships for the Goals) is the implementation goal; R lists its components.", "R explains A.")
    S("Consider the following statements:",
      [("The High-Level Political Forum is the central UN platform for follow-up and review of the 2030 Agenda.", True, "yes"),
       ("Voluntary National Reviews are legally binding compliance reports.", False, "they are voluntary and state-led"),
       ("Countries present Voluntary National Reviews at the High-Level Political Forum.", True, "yes")],
      "VNRs are voluntary by name and nature.")
    N("Consider the following statements about the Millennium Development Goals:",
      [("There were eight MDGs.", True, "yes"), ("They covered the period 2000–2015.", True, "yes"),
       ("Ensuring environmental sustainability was one of them.", True, "MDG 7"), ("They comprised 17 goals.", False, "17 is the number of SDGs")],
      "8 MDGs vs 17 SDGs.")
    A("MoSPI has developed a National Indicator Framework to monitor the SDGs in India.",
      "NITI Aayog is the nodal body for coordinating the SDGs in India.",
      True, True, False, ["Both statements are true.", "NITI Aayog's coordinating role does not explain why MoSPI built the indicator framework — that is MoSPI's statistical mandate."],
      "Two bodies with parallel roles.")

    # ================= World affairs and geopolitical terms =================
    h.topic("gk-world-affairs-and-geopolitical", "NCERT Class 12 Political Science (Contemporary World Politics); standard reference atlases")
    F("The Durand Line is the boundary between:",
      "Afghanistan and Pakistan", [("India and China", "McMahon Line / LAC"), ("India and Pakistan", "Radcliffe Line"),
                                   ("Pakistan and Iran", "Goldsmid Line")],
      "The Durand Line (1893) separates Afghanistan and Pakistan.", "Radcliffe = India–Pakistan.")
    F("The McMahon Line is associated with the boundary between India and:",
      "China", [("Pakistan", "Radcliffe Line"), ("Nepal", "Sugauli-based boundary"), ("Myanmar", "not the McMahon Line")],
      "The McMahon Line was drawn at the 1914 Simla Conference; China does not accept it.", "Line of Actual Control vs McMahon Line both concern China.")
    F("The term 'Iron Curtain' was popularised in a 1946 speech at Fulton by:",
      "Winston Churchill", [("Harry Truman", "Truman Doctrine, 1947"), ("Joseph Stalin", "Soviet leader"),
                            ("Franklin D. Roosevelt", "died in 1945")],
      "Churchill's 'Sinews of Peace' speech at Fulton, Missouri used the phrase.", "Truman attended the speech but did not give it.")
    F("'Glasnost' and 'Perestroika' are associated with:",
      "Mikhail Gorbachev", [("Nikita Khrushchev", "de-Stalinisation"), ("Boris Yeltsin", "first President of Russia"),
                            ("Leonid Brezhnev", "Brezhnev Doctrine")],
      "Openness (glasnost) and restructuring (perestroika) were Gorbachev's reforms.", "Yeltsin succeeded after the USSR's collapse.")
    F("The 'Golden Triangle', known for illicit opium production, comprises:",
      "Myanmar, Laos and Thailand", [("Afghanistan, Iran and Pakistan", "Golden Crescent"), ("Colombia, Peru and Bolivia", "coca-growing region"),
                                     ("India, Nepal and Bhutan", "not a drug region")],
      "The Golden Triangle is where Myanmar, Laos and Thailand meet.", "Golden Crescent lies to India's west.", lv="L2")
    M("Boundary line", "Countries separated",
      [("Radcliffe Line", "India and Pakistan"), ("38th Parallel", "North Korea and South Korea"),
       ("49th Parallel", "United States and Canada"), ("Oder–Neisse Line", "Germany and Poland")],
      "38th parallel = Korea; 17th parallel = former Vietnam divide.", lv="L2")
    M("Term", "Meaning",
      [("Finlandisation", "A small state accommodating a powerful neighbour's foreign policy"),
       ("Brinkmanship", "Pushing a dangerous situation to the verge of conflict to gain advantage"),
       ("Détente", "Easing of tension between rivals"), ("Balkanisation", "Fragmentation of a region into small hostile states")],
      "Détente usually refers to US–Soviet relaxation in the 1970s.")
    C("Arrange the following in chronological order:",
      [("Monroe Doctrine", 1823, "1823"), ("Truman Doctrine", 1947, "1947"), ("Marshall Plan", 1948, "1948"),
       ("India's Look East Policy", 1991, "early 1990s")],
      "Truman Doctrine (1947) preceded the Marshall Plan (1948).")
    A("The Siliguri Corridor is called the 'Chicken's Neck'.",
      "It is a narrow strip of land connecting India's north-eastern region with the rest of the country.",
      True, True, True, "Its narrowness and strategic role explain the nickname.", "R explains A.")
    N("Consider the following statements:",
      [("The Strait of Hormuz connects the Persian Gulf with the Gulf of Oman.", True, "yes"),
       ("The Bab-el-Mandeb connects the Red Sea with the Gulf of Aden.", True, "yes"),
       ("The Strait of Malacca separates the Malay Peninsula from Sumatra.", True, "yes"),
       ("The Palk Strait separates India from the Maldives.", False, "it separates India from Sri Lanka")],
      "Palk Strait = India–Sri Lanka.", ref="Standard reference atlas")
    A("India's Look East Policy was upgraded to the Act East Policy in 2014.",
      "The Look East Policy was launched in the early 1990s under Prime Minister P. V. Narasimha Rao.",
      True, True, False, ["Both statements are true.", "The launch date does not explain the 2014 upgrade."],
      "Origin is not cause.")
    S("Consider the following statements:",
      [("The term 'soft power' was coined by Joseph Nye.", True, "yes"),
       ("The term 'Thucydides Trap' was popularised by Graham Allison.", True, "yes"),
       ("The term 'Third World' was coined by Alfred Sauvy.", True, "1952")],
      "All three attributions are correct.")
    M("Diplomacy term", "Association",
      [("Ping-pong diplomacy", "US–China thaw in the early 1970s"), ("Shuttle diplomacy", "Henry Kissinger in the Middle East"),
       ("Dollar diplomacy", "US President William Howard Taft"), ("Gunboat diplomacy", "Display of naval power to coerce")],
      "Dollar diplomacy (Taft) vs gunboat diplomacy (coercion).")
    A("The 'Nine-Dash Line' is a contested maritime claim.",
      "China uses it to claim most of the South China Sea, a claim that a 2016 arbitral tribunal under UNCLOS found had no legal basis.",
      True, True, True, "R explains what the claim is and why it is contested.", "R explains A.")
    S("Consider the following statements about the Cold War:",
      [("The Warsaw Pact was formed before NATO.", False, "NATO 1949; Warsaw Pact 1955"),
       ("The Truman Doctrine is associated with the policy of containment.", True, "1947"),
       ("The Marshall Plan provided economic aid to rebuild Western Europe.", True, "1948")],
      "The Warsaw Pact was the Soviet response to NATO.")
