"""QRE-GK-B part 1: General Science (7 microtopics)."""


def add_all(g):
    F, O = "foundation", "officer"

    # ------------------------------------------------------------------ astronomy
    g.m("gk-astronomy", "NCERT Class 6/8 Science & Class 11 Physics; IAU official naming conventions")
    g.f("L1", "Which star is the nearest to Earth after the Sun?", "Proxima Centauri",
        ["Sirius|brightest night-sky star, not nearest", "Betelgeuse|a distant red supergiant",
         "Polaris|confuses Pole Star with nearest star"],
        "Proxima Centauri, about 4.24 light-years away, is the closest known star to the Sun.",
        "Brightness in the sky is not the same as nearness.")
    g.f("L1", "The brightest star in the night sky, also called the Dog Star, is:", "Sirius",
        ["Canopus|second-brightest star", "Vega|bright summer star in Lyra", "Polaris|Pole Star is only moderately bright"],
        "Sirius (Alpha Canis Majoris) is the brightest star seen at night; it is nicknamed the Dog Star.",
        "Polaris is famous for its position, not its brightness.")
    g.f("L1", "A light-year is a unit of:", "Distance",
        ["Time|misreads 'year' as time", "Speed|confuses with speed of light", "Luminosity|confuses with brightness"],
        "A light-year is the distance light travels in one year, about 9.46 trillion km.",
        "The word 'year' makes many pick time.")
    g.f("L1", "The Pole Star (Polaris) belongs to which constellation?", "Ursa Minor",
        ["Ursa Major|the pointer stars are in Ursa Major, not Polaris itself", "Orion|prominent winter constellation",
         "Cassiopeia|circumpolar constellation near Polaris"],
        "Polaris is the brightest star of Ursa Minor (Little Bear); two stars of Ursa Major point towards it.",
        "Ursa Major only points to Polaris.")
    g.f("L2", "Which body officially assigns names to stars, planets and surface features of celestial bodies?",
        "International Astronomical Union",
        ["NASA|a national space agency, not a naming authority", "European Space Agency|regional space agency",
         "UN Office for Outer Space Affairs|keeps the launch registry, not names"],
        "The IAU (founded 1919, secretariat in Paris) is the recognised authority for astronomical nomenclature.",
        "Space agencies propose names but the IAU approves them.")
    g.st(O, "L3", "Consider the following statements about astronomical units of distance:",
         [("One parsec is longer than one light-year.", True),
          ("A light-year is the distance light travels in one Earth day.", False),
          ("One astronomical unit is roughly the mean Earth–Sun distance, about 150 million km.", True)],
         ["1 parsec ≈ 3.26 light-years, so a parsec is longer.",
          "A light-year is defined over one Julian year, not a day.",
          "1 AU ≈ 1.496 × 10^8 km, the mean Earth–Sun distance."],
         "Order of size: AU < light-year < parsec.")
    g.mt(O, "L3", "Match the traditional Indian names with the corresponding star or star group:",
         "Indian name", "Star / group",
         [("Saptarishi", "Big Dipper (Ursa Major)"), ("Dhruva", "Polaris"),
          ("Kritika", "Pleiades"), ("Mriga", "Orion")],
         "Saptarishi = seven bright stars of Ursa Major; Dhruva = Pole Star; Kritika = Pleiades cluster; Mriga = Orion.",
         "Kritika (Pleiades) is a star cluster, often confused with Orion.")
    g.ar(O, "L3", "Stars twinkle but planets generally do not.",
         "Stars are so distant that they act as point sources, so atmospheric refraction fluctuations change their apparent brightness and position, whereas planets present tiny discs whose fluctuations average out.",
         True, True, True,
         "Twinkling is caused by turbulent refraction; the extended disc of a planet averages it out — R explains A.",
         "Do not attribute twinkling to the star's own variability.", ref="NCERT Class 10 Science, Ch. 11")
    g.o("L2", "The Chandrasekhar limit refers to:", "The maximum mass of a stable white dwarf",
        ["The minimum mass a star needs to begin hydrogen fusion|confuses with the hydrogen-burning limit",
         "The maximum mass of a stable, non-rotating neutron star|that is the Tolman–Oppenheimer–Volkoff limit",
         "The radius of the event horizon of a black hole|that is the Schwarzschild radius"],
        "S. Chandrasekhar showed that electron-degeneracy pressure cannot support a white dwarf above ~1.4 solar masses.",
        "Neutron-star and black-hole limits have different names.")
    g.st(O, "L3", "Consider the following statements about stars:",
         [("The Sun is a G-type main-sequence star.", True),
          ("Red stars have higher surface temperatures than blue stars.", False),
          ("A supernova explosion can leave behind a neutron star or a black hole.", True)],
         ["The Sun is classified G2V (main sequence).", "Blue stars are hotter; red stars are cooler.",
          "Core-collapse supernovae leave neutron stars or black holes."],
         "Colour–temperature order is the reverse of everyday 'red = hot'.")
    g.o("L2", "The boundary around a black hole beyond which nothing, not even light, can escape is called the:",
        "Event horizon",
        ["Accretion disc|matter spiralling outside the horizon", "Singularity|the central point, not the boundary",
         "Photon sphere|region where light can orbit, outside the horizon"],
        "The event horizon (at the Schwarzschild radius for a non-rotating hole) is the point of no return.",
        "The singularity is inside the horizon.")
    g.st(O, "L3", "Consider the following statements about galaxies:",
         [("The Milky Way is a barred spiral galaxy.", True),
          ("The Solar System lies close to the centre of the Milky Way.", False),
          ("The Large and Small Magellanic Clouds are best seen from the Southern Hemisphere.", True)],
         ["The Milky Way is a barred spiral.", "The Sun lies in the Orion Arm, about 26,000 light-years from the centre.",
          "The Magellanic Clouds are southern-sky objects."],
         "The Solar System is in the outer disc, not the core.")
    g.ar(O, "L3", "Light from most distant galaxies shows a redshift.",
         "The universe is expanding, so distant galaxies are receding from us.",
         True, True, True,
         "Recession stretches the wavelength of light (cosmological redshift) — Hubble's observation; R explains A.",
         "Blueshift would mean approach, not recession.")
    g.mt(O, "L3", "Match the bright star with the constellation in which it lies:", "Star", "Constellation",
         [("Betelgeuse", "Orion"), ("Sirius", "Canis Major"), ("Aldebaran", "Taurus"), ("Antares", "Scorpius")],
         "Betelgeuse—Orion; Sirius—Canis Major; Aldebaran—Taurus; Antares—Scorpius.",
         "Betelgeuse and Rigel are both in Orion; Antares is the 'heart of the scorpion'.")
    g.ar(O, "L3", "The tail of a comet always points away from the Sun.",
         "A comet's tail always trails behind it along its direction of motion.",
         True, False, False,
         "Tail direction is set by the solar wind and radiation pressure, not by the comet's direction of travel.",
         "A receding comet's tail leads it — it does not trail behind.")

    # ------------------------------------------------------------------ computing & AI
    g.m("gk-computing", "Standard computer-science history and textbooks (NCERT Class 11 Computer Science)")
    g.f("L1", "Who is known as the 'father of the computer' for designing the Analytical Engine?", "Charles Babbage",
        ["Alan Turing|theory of computation", "John von Neumann|stored-program architecture",
         "Tim Berners-Lee|inventor of the World Wide Web"],
        "Charles Babbage designed the Difference Engine and the general-purpose Analytical Engine in the 19th century.",
        "Turing and von Neumann are 20th-century pioneers.")
    g.f("L1", "One byte consists of how many bits?", "8",
        ["4|that is a nibble", "16|a 16-bit word", "1024|confuses bytes in a kilobyte"],
        "1 byte = 8 bits.", "A nibble is 4 bits.", kind="numerical")
    g.f("L1", "The World Wide Web was invented by:", "Tim Berners-Lee",
        ["Vint Cerf|co-designer of TCP/IP", "Bill Gates|Microsoft co-founder", "Charles Babbage|19th-century computing pioneer"],
        "Tim Berners-Lee proposed the WWW at CERN in 1989.", "The Internet (TCP/IP) and the Web are different things.")
    g.f("L1", "The programming language C was developed at Bell Labs by:", "Dennis Ritchie",
        ["James Gosling|created Java", "Guido van Rossum|created Python", "John Backus|led FORTRAN"],
        "Dennis Ritchie created C in the early 1970s, closely tied to the development of Unix.",
        "Each language is linked to a different creator.")
    g.f("L2", "The term 'artificial intelligence' was coined by:", "John McCarthy",
        ["Alan Turing|proposed the Turing test", "Marvin Minsky|co-organiser of Dartmouth, not the coiner",
         "Geoffrey Hinton|deep-learning pioneer"],
        "John McCarthy coined the term in the 1955 proposal for the 1956 Dartmouth workshop.",
        "Turing's 1950 paper predates the term.")
    g.o("L2", "The Turing test, proposed in 1950, is intended to assess:",
        "Whether a machine's replies can pass for a human's",
        ["Whether an algorithm will halt on a given input|that is the halting problem",
         "The raw processing speed of a computer's CPU|confuses with benchmarking",
         "The strength of a cipher against brute-force attack|confuses with cryptanalysis"],
        "Turing's 'imitation game' asks whether an evaluator can tell machine from human in conversation.",
        "Turing also posed the halting problem, which is a different idea.")
    g.st(O, "L3", "Consider the following statements about number systems:",
         [("The binary system uses base 2.", True),
          ("In the binary (base-2) convention used for memory sizes, 1 kilobyte equals 1,000 bytes.", False),
          ("The hexadecimal system uses base 16.", True)],
         ["Binary = base 2; hexadecimal = base 16.", "In the binary convention 1 KB = 2^10 = 1,024 bytes."],
         "1,000 bytes is the decimal (SI) kilobyte, not the binary one.", ref="NCERT Class 11 Computer Science")
    g.mt(O, "L3", "Match the pioneer with the contribution:", "Pioneer", "Contribution",
         [("Alan Turing", "Abstract model of computation"), ("John von Neumann", "Stored-program architecture"),
          ("Ada Lovelace", "First published algorithm for the Analytical Engine"), ("Tim Berners-Lee", "World Wide Web")],
         "Turing machine; von Neumann architecture; Lovelace's notes on the Analytical Engine; WWW at CERN.",
         "Ada Lovelace worked on Babbage's machine, not on modern computers.")
    g.ar(O, "L2", "Data stored on a hard disk is lost when a computer is switched off.", "RAM is a volatile memory.",
         False, True, False, "A hard disk is non-volatile, so A is false; RAM is indeed volatile, so R is true.",
         "ROM and flash are non-volatile.")
    g.o("L3", "Grouping customers into segments from purchase data without any pre-assigned labels is an example of:",
        "Unsupervised learning",
        ["Supervised learning|needs labelled examples", "Reinforcement learning|learns from rewards",
         "Transfer learning|reuses a pre-trained model"],
        "Clustering discovers structure in unlabelled data — the classic unsupervised task.",
        "No labels means not supervised.")
    g.st(O, "L3", "Consider the following statements about machine learning:",
         [("In supervised learning the model is trained on labelled data.", True),
          ("Reinforcement learning relies on reward signals from interaction with an environment.", True),
          ("Deep learning uses artificial neural networks with many layers.", True)],
         ["All three are standard definitions."], "All statements can be true — do not assume one must be false.")
    g.mt(O, "L3", "Match the generation of computers with its core technology:", "Generation", "Technology",
         [("First", "Vacuum tubes"), ("Second", "Transistors"), ("Third", "Integrated circuits"), ("Fourth", "Microprocessors")],
         "Vacuum tubes (1940s–50s) → transistors → ICs → microprocessors (VLSI).",
         "Transistors preceded integrated circuits.")
    g.o("L2", "Moore's law observes that:", "Transistor count on a chip doubles about every two years",
        ["Processor clock speed doubles roughly every single year|misstates the quantity",
         "The price of a chip falls by half every six months|invented trend",
         "Memory capacity grows linearly with time|linear, not exponential"],
        "Gordon Moore (1965, revised 1975) described the doubling of transistor counts on ICs.",
        "It is about transistor density, not clock speed.")
    g.o("L2", "The Linux kernel was first released in 1991 by:", "Linus Torvalds",
        ["Richard Stallman|founded the GNU project", "Ken Thompson|co-creator of Unix", "Dennis Ritchie|creator of C"],
        "Linus Torvalds released the Linux kernel in 1991.", "GNU supplied tools; the kernel is Torvalds'.")
    g.o("L2", "In the acronym GPT used for large language models, the letter 'T' stands for:", "Transformer",
        ["Tensor|a data structure", "Turing|confuses with the Turing test", "Training|a process, not the architecture"],
        "GPT = Generative Pre-trained Transformer; the transformer architecture was introduced in 2017.",
        "The architecture name, not the process.")

    # ------------------------------------------------------------------ digital public platforms
    g.m("gk-digital-public", "Aadhaar Act, 2016; NPCI / MeitY official descriptions")
    g.f("L1", "How many digits does an Aadhaar number have?", "12",
        ["10|confuses with mobile/PAN length", "16|confuses with card number length", "14|random length"],
        "Aadhaar is a 12-digit unique identity number issued by UIDAI.", "PAN is 10 characters.", kind="numerical")
    g.f("L1", "The Unified Payments Interface (UPI) was developed by:", "National Payments Corporation of India",
        ["Reserve Bank of India|regulator, not developer", "Unique Identification Authority of India|runs Aadhaar",
         "Ministry of Electronics and IT|policy ministry"],
        "NPCI developed UPI, launched in 2016.", "RBI regulates payment systems; NPCI operates retail payments.")
    g.f("L1", "The Digital India programme was launched in:", "2015",
        ["2014|Jan Dhan / Make in India year", "2016|UPI launch year", "2012|random year"],
        "Digital India was launched on 1 July 2015.", "Several flagship schemes cluster in 2014–2016.", kind="numerical")
    g.f("L1", "DigiLocker is primarily meant for:", "Storing officially issued digital documents",
        ["Filing income-tax returns and paying taxes online|that is the e-filing portal", "Booking railway tickets|that is IRCTC",
         "Making peer-to-peer payments|that is UPI"],
        "DigiLocker (MeitY, Digital India) lets citizens receive and store issued documents in digital form.",
        "Do not confuse document wallet with payment wallet.")
    g.f("L2", "The BHIM app, launched in 2016, stands for:", "Bharat Interface for Money",
        ["Bharat Integrated Mobile banking|invented expansion", "Bank Handled Instant Money|invented expansion",
         "Bharat Instant Money transfer|invented expansion"],
        "BHIM — Bharat Interface for Money — is NPCI's UPI app.", "Named after B. R. Ambedkar; expansion is 'Interface for Money'.")
    g.st(O, "L3", "Consider the following statements about Aadhaar:",
         [("UIDAI is a statutory authority established under the Aadhaar Act, 2016.", True),
          ("An Aadhaar number is proof of citizenship.", False),
          ("A person who has resided in India for 182 days or more in the twelve months before applying is eligible to obtain Aadhaar.", True)],
         ["UIDAI became statutory under the 2016 Act.", "The Act expressly says Aadhaar is not proof of citizenship or domicile.",
          "Eligibility is based on residence (182 days in preceding 12 months)."],
         "Aadhaar is residence-based, not citizenship-based.", ref="Aadhaar Act, 2016, ss. 2(v), 9, 11")
    g.mt(O, "L3", "Match the digital platform with its purpose:", "Platform", "Purpose",
         [("UMANG", "Single mobile app for many government services"), ("GeM", "Online public procurement"),
          ("e-Sanjeevani", "Telemedicine"), ("DIKSHA", "School education content")],
         "UMANG—unified app; GeM—Government e-Marketplace; e-Sanjeevani—teleconsultation; DIKSHA—teachers/students content.",
         "GeM is for government buying, not citizen services.")
    g.o("L2", "The Open Network for Digital Commerce (ONDC) is an initiative of:",
        "DPIIT, Ministry of Commerce and Industry",
        ["Ministry of Electronics and IT|runs Digital India, not ONDC", "National Payments Corporation of India|payments body",
         "Reserve Bank of India|financial regulator"],
        "ONDC was incorporated in 2021 as a not-for-profit company promoted by DPIIT.",
        "ONDC is about commerce interoperability, not payments.")
    g.o("L2", "The Account Aggregator framework for consent-based sharing of financial data is regulated by:",
        "Reserve Bank of India",
        ["Securities and Exchange Board of India|regulates securities markets", "National Payments Corporation of India|payments operator",
         "Ministry of Electronics and IT|designed DEPA concepts, not the regulator"],
        "Account Aggregators are licensed as NBFC-AA under RBI's 2016 master directions.",
        "AAs cannot see or store data; they only route it with consent.")
    g.ar(O, "L3", "Documents in the 'Issued Documents' section of DigiLocker are treated at par with the original physical documents.",
         "Rules notified under the Information Technology Act, 2000 recognise documents issued through the digital locker as legally valid.",
         True, True, True,
         "The 2016 digital-locker rules (as amended in 2017) give issued documents legal parity; R explains A.",
         "Self-uploaded scans do not enjoy the same status as issued documents.")
    g.o("L2", "e-RUPI, launched in 2021, is best described as:", "A purpose-specific, prepaid digital voucher",
        ["The RBI's central bank digital currency|that is the e-rupee (CBDC)", "A new debit-card network|confuses with RuPay",
         "A regulated exchange for trading cryptocurrency|unrelated"],
        "e-RUPI (NPCI) is a person- and purpose-specific QR/SMS voucher redeemable without a bank app.",
        "e-RUPI (voucher) is not the RBI's e-rupee (CBDC).")
    g.o("L2", "FASTag electronic toll collection works on which technology?", "RFID",
        ["NFC|short-range contactless payments", "QR codes|visual codes, not tags",
         "Bluetooth|short-range wireless pairing"],
        "FASTag is a passive RFID tag read at toll plazas under the NETC programme.", "NFC is a subset of RFID but not what FASTag uses.")
    g.st(O, "L3", "Consider the following statements about e-governance in India:",
         [("The National e-Governance Plan (NeGP) was approved in 2006.", True),
          ("MCA21 is a Mission Mode Project of the Ministry of Railways.", False),
          ("Common Services Centres act as front-end access points for services in villages.", True)],
         ["NeGP was approved in May 2006.", "MCA21 belongs to the Ministry of Corporate Affairs.",
          "CSCs are village-level delivery points."], "MCA = Ministry of Corporate Affairs.",
         ref="MeitY: National e-Governance Plan documents")
    g.o("L2", "The national nodal agency for responding to cyber-security incidents in India is:", "CERT-In",
        ["NCIIPC|protects critical information infrastructure", "NIC|builds government IT systems",
         "C-DAC|R&D organisation"],
        "CERT-In (under MeitY, operational since 2004) is designated under s. 70B of the IT Act.",
        "NCIIPC covers critical infrastructure specifically.", ref="Information Technology Act, 2000, s. 70B")
    g.mt(O, "L3", "Match the NPCI product with its function:", "Product", "Function",
         [("RuPay", "Domestic card payment network"), ("NACH", "Bulk and recurring payments"),
          ("AePS", "Aadhaar-based transactions at micro-ATMs"), ("NETC", "Electronic toll collection")],
         "RuPay cards; NACH for salaries/EMIs/subsidies; AePS via biometric authentication; NETC behind FASTag.",
         "NETC is the system; FASTag is the tag.", ref="NPCI product descriptions")

    # ------------------------------------------------------------------ scientific institutions
    g.m("gk-scientific-and-research", "Official institutional histories (ISRO, DAE, CSIR, ICAR, ICMR)")
    g.f("L1", "The headquarters of ISRO is located in:", "Bengaluru",
        ["Sriharikota|launch centre", "Thiruvananthapuram|Vikram Sarabhai Space Centre", "Ahmedabad|Space Applications Centre"],
        "ISRO HQ (Antariksh Bhavan) is in Bengaluru.", "Launch site ≠ headquarters.")
    g.f("L1", "The Bhabha Atomic Research Centre (BARC) is located at:", "Trombay, Mumbai",
        ["Kalpakkam|IGCAR", "Kolkata|Variable Energy Cyclotron Centre", "Hyderabad|Nuclear Fuel Complex"],
        "BARC is at Trombay, Mumbai.", "Kalpakkam hosts IGCAR, not BARC.")
    g.f("L1", "The Indian Institute of Science, Bengaluru (1909), owes its founding vision to:", "Jamsetji Tata",
        ["Homi J. Bhabha|founded TIFR", "C. V. Raman|later director of IISc", "Vikram Sarabhai|founded PRL"],
        "IISc was established in 1909 following Jamsetji Nusserwanji Tata's initiative.", "Raman was a director, not the founder.")
    g.f("L2", "Which institution maintains Indian Standard Time as the national timekeeper?", "CSIR-National Physical Laboratory",
        ["India Meteorological Department|weather service", "ISRO|space agency", "Bhabha Atomic Research Centre|nuclear research"],
        "CSIR-NPL, New Delhi, keeps the national standard of time and measurement.", "IMD does weather, not time.")
    g.f("L2", "The Physical Research Laboratory, founded in 1947 by Vikram Sarabhai, is located in:", "Ahmedabad",
        ["Bengaluru|ISRO HQ city", "Pune|IUCAA/NCL city", "Hyderabad|CCMB city"],
        "PRL is in Ahmedabad and is called the cradle of Indian space sciences.", "Sarabhai's institutions are Ahmedabad-based.")
    g.mt(O, "L3", "Match the CSIR laboratory with its city:", "Laboratory", "City",
         [("CCMB", "Hyderabad"), ("NCL", "Pune"), ("CDRI", "Lucknow"), ("IMTech", "Chandigarh")],
         "Centre for Cellular & Molecular Biology—Hyderabad; National Chemical Laboratory—Pune; Central Drug Research Institute—Lucknow; Institute of Microbial Technology—Chandigarh.",
         "CDRI (drugs) is Lucknow, not Hyderabad.")
    g.mt(O, "L3", "Match the institution with its founder:", "Institution", "Founder",
         [("Tata Institute of Fundamental Research", "Homi J. Bhabha"), ("Physical Research Laboratory", "Vikram Sarabhai"),
          ("Bose Institute", "J. C. Bose"), ("Raman Research Institute", "C. V. Raman")],
         "Institutions largely carry their founders' names except TIFR (Bhabha) and PRL (Sarabhai).",
         "TIFR and PRL are the two to memorise.")
    g.st(O, "L3", "Consider the following statements about CSIR:",
         [("It is an autonomous society registered under the Societies Registration Act, 1860.", True),
          ("It was established after Independence, in 1950.", False),
          ("The Prime Minister is its President.", True)],
         ["CSIR is a registered society.", "It was established in 1942.", "The PM is the ex-officio President."],
         "CSIR predates Independence (1942).")
    g.o("L2", "ICAR functions under which department?", "Department of Agricultural Research and Education",
        ["Department of Science and Technology|DST", "Department of Scientific and Industrial Research|parent of CSIR",
         "Department of Biotechnology|DBT"],
        "ICAR (est. 1929) is under DARE, Ministry of Agriculture and Farmers Welfare.", "DSIR is CSIR's department.")
    g.o("L3", "The Indian Council of Medical Research traces its origin to a body set up in 1911 called:",
        "Indian Research Fund Association",
        ["Imperial Council of Agricultural Research|ICAR's former name", "Indian Medical Service Board|invented",
         "All India Institute of Hygiene|a different institute"],
        "ICMR began as the Indian Research Fund Association (1911) and was renamed in 1949.",
        "The 'Imperial Council' name belongs to ICAR.")
    g.mt(O, "L3", "Match the ISRO centre with its location:", "Centre", "Location",
         [("Vikram Sarabhai Space Centre", "Thiruvananthapuram"), ("Space Applications Centre", "Ahmedabad"),
          ("U R Rao Satellite Centre", "Bengaluru"), ("Satish Dhawan Space Centre", "Sriharikota")],
         "VSSC—launch vehicles; SAC—payloads/applications; URSC—satellites; SDSC SHAR—launch port.",
         "Satellites are built in Bengaluru, launched from Sriharikota.")
    g.ar(O, "L3", "India's three-stage nuclear power programme ultimately aims at using thorium as fuel.",
         "India has large thorium reserves but comparatively limited uranium reserves.",
         True, True, True, "Bhabha's plan targets thorium because of resource endowment; R explains A.",
         "The first stage uses natural uranium; thorium comes in the third.", ref="Department of Atomic Energy programme description")
    g.st(O, "L3", "Consider the following statements about astronomy facilities in India:",
         [("ARIES is located at Nainital.", True),
          ("IUCAA is located in Pune.", True),
          ("The Giant Metrewave Radio Telescope is located near Ooty.", False)],
         ["ARIES—Nainital; IUCAA—Pune.", "GMRT is near Narayangaon, Pune district; Ooty has a separate radio telescope."],
         "Ooty Radio Telescope and GMRT are different facilities.")
    g.o("L2", "CSIR-National Institute of Oceanography is headquartered in:", "Goa",
        ["Visakhapatnam|a regional centre city", "Kochi|a regional centre city", "Chennai|NIOT city"],
        "CSIR-NIO is at Dona Paula, Goa.", "NIOT (Chennai) is a different MoES institute.")
    g.st(O, "L3", "Consider the following statements about India's space programme:",
         [("INCOSPAR was set up in 1962 under the Defence Research and Development Organisation.", False),
          ("ISRO was formed in 1969.", True),
          ("The Department of Space was created in 1972.", True)],
         ["INCOSPAR (1962) was under the Department of Atomic Energy.", "ISRO: 15 August 1969; DoS and Space Commission: 1972."],
         "DRDO was not the parent of INCOSPAR.")

    # ------------------------------------------------------------------ solar system
    g.m("gk-solar-system", "NCERT Class 6 Geography & Class 8 Science; IAU 2006 planet definition")
    g.f("L1", "The largest planet of the Solar System is:", "Jupiter",
        ["Saturn|second largest", "Neptune|ice giant", "Uranus|ice giant"], "Jupiter is the largest planet.", "Saturn is second.")
    g.f("L1", "Which planet is the hottest in the Solar System?", "Venus",
        ["Mercury|closest to the Sun, but not hottest", "Mars|cold desert planet", "Jupiter|gas giant"],
        "Venus's dense CO2 atmosphere traps heat, making it hotter than Mercury.", "Closest is not hottest.")
    g.f("L1", "Which planet is known as the 'Red Planet'?", "Mars",
        ["Venus|'Morning/Evening Star'", "Jupiter|largest planet", "Mercury|closest planet"],
        "Iron oxide on its surface gives Mars its red colour.", "Venus is the bright 'star'.")
    g.f("L2", "Which planet has a mean density lower than that of water?", "Saturn",
        ["Jupiter|largest but denser than water", "Neptune|denser than water", "Earth|densest planet"],
        "Saturn's mean density is about 0.69 g/cm³, less than water's 1 g/cm³.", "Earth is the densest planet.")
    g.f("L2", "The largest moon in the Solar System is:", "Ganymede",
        ["Titan|second largest (Saturn)", "Callisto|third largest", "Earth's Moon|fifth largest"],
        "Ganymede (Jupiter) is larger than Mercury.", "Titan is famous for its thick atmosphere, not size rank.")
    g.st(O, "L3", "Consider the following statements:",
         [("Mercury has a thick atmosphere.", False),
          ("Venus rotates in a retrograde (east-to-west) direction.", True),
          ("Uranus has an axial tilt of nearly 98 degrees.", True)],
         ["Mercury has only a tenuous exosphere.", "Venus rotates retrograde; Uranus effectively rotates on its side."],
         "Only Venus and Uranus show 'unusual' rotation.")
    g.ar(O, "L3", "Venus is hotter than Mercury although it is farther from the Sun.",
         "Venus has a dense carbon-dioxide atmosphere that produces a runaway greenhouse effect.",
         True, True, True, "The greenhouse effect of Venus's atmosphere explains its higher temperature.",
         "Distance alone does not decide surface temperature.")
    g.o("L3", "Pluto was reclassified as a dwarf planet in 2006 mainly because it:",
        "Has not cleared the neighbourhood around its orbit",
        ["Does not orbit the Sun directly but a planet|it does orbit the Sun", "Is not massive enough to become round|it is round",
         "Is a captured satellite that orbits Neptune|it is not a satellite"],
        "IAU criteria: orbits Sun, nearly round, cleared its orbit — Pluto fails the third.",
        "Pluto meets the first two criteria.", ref="IAU General Assembly Resolution B5 (2006)")
    g.mt(O, "L3", "Match the moon with its planet:", "Moon", "Planet",
         [("Titan", "Saturn"), ("Io", "Jupiter"), ("Triton", "Neptune"), ("Phobos", "Mars")],
         "Titan—Saturn; Io—Jupiter; Triton—Neptune (retrograde orbit); Phobos—Mars.", "Triton, not Titan, orbits Neptune.")
    g.st(O, "L3", "Consider the following statements about small bodies of the Solar System:",
         [("The main asteroid belt lies between Mars and Jupiter.", True),
          ("The Kuiper Belt lies inside the orbit of Neptune.", False),
          ("Ceres is classified as a dwarf planet.", True)],
         ["Asteroid belt: Mars–Jupiter; Ceres is its largest body and a dwarf planet.", "Kuiper Belt lies beyond Neptune."],
         "Kuiper Belt is trans-Neptunian.")
    g.o("L2", "Arrange Uranus, Saturn, Neptune and Jupiter in increasing order of distance from the Sun:",
        "Jupiter, Saturn, Uranus, Neptune",
        ["Saturn, Jupiter, Uranus, Neptune|swaps Jupiter and Saturn", "Jupiter, Saturn, Neptune, Uranus|swaps Uranus and Neptune",
         "Jupiter, Uranus, Saturn, Neptune|misplaces Uranus"],
        "Order of outer planets: Jupiter, Saturn, Uranus, Neptune.", "Uranus comes before Neptune.")
    g.o("L3", "Earth moves fastest in its orbit when it is at perihelion. This occurs around:", "Early January",
        ["Early July|that is aphelion", "21 March|equinox", "21 June|summer solstice"],
        "By Kepler's second law, orbital speed is greatest at perihelion (~3 January).",
        "Northern winter coincides with perihelion.", ref="NCERT Class 11 Physics (Kepler's laws); Class 11 Geography")
    g.o("L2", "The Great Red Spot, a giant long-lived storm, is found on:", "Jupiter",
        ["Saturn|has a hexagonal polar storm", "Neptune|had a Great Dark Spot", "Mars|dust storms"],
        "The Great Red Spot is an anticyclone on Jupiter.", "Neptune's spot was dark, not red.")
    g.ar(O, "L2", "The Moon has practically no atmosphere.", "The Moon is the largest natural satellite in the Solar System.",
         True, False, False, "A is true (weak gravity cannot hold gases); R is false — Ganymede is the largest moon.", "Absence of air also means no sound on the Moon.",
         ref="NCERT Class 9 Science (Gravitation)")
    g.st(O, "L3", "Consider the following statements about tides:",
         [("Spring tides occur around new moon and full moon.", True),
          ("The Moon's tide-raising effect on Earth is weaker than the Sun's.", False),
          ("Neap tides occur when the Sun and the Moon are at right angles with respect to Earth.", True)],
         ["Spring tides at syzygy; neap tides at quadrature.", "The Moon's tidal effect is about twice the Sun's, because it is much closer."],
         "Tidal force falls with the cube of distance, favouring the Moon.", ref="NCERT Class 11 Geography")

    # ------------------------------------------------------------------ space missions
    g.m("gk-space-missions", "ISRO official mission pages; NASA mission history")
    g.f("L1", "India's first satellite, launched in 1975, was:", "Aryabhata",
        ["Bhaskara|first experimental remote-sensing satellite (1979)", "Rohini|first satellite on an Indian rocket",
         "INSAT-1A|first INSAT"], "Aryabhata was launched on 19 April 1975 by a Soviet launcher.",
        "Rohini was the first launched by an Indian rocket.")
    g.f("L1", "The first human to travel into space was:", "Yuri Gagarin",
        ["Neil Armstrong|first on the Moon", "Alan Shepard|first American in space",
         "Valentina Tereshkova|first woman in space"], "Yuri Gagarin orbited Earth aboard Vostok 1 in 1961.",
        "First in space ≠ first on the Moon.")
    g.f("L1", "The first Indian citizen to travel into space was:", "Rakesh Sharma",
        ["Kalpana Chawla|first Indian-born woman in space (US citizen)", "Sunita Williams|American astronaut of Indian origin",
         "Ravish Malhotra|backup cosmonaut"], "Rakesh Sharma flew on Soyuz T-11 in 1984.", "Ravish Malhotra was the backup.")
    g.f("L1", "India's first mission to the Moon was:", "Chandrayaan-1",
        ["Mangalyaan|Mars mission", "Aditya-L1|solar mission", "Chandrayaan-2|second lunar mission"],
        "Chandrayaan-1 was launched in 2008 by PSLV-C11.", "Mangalyaan went to Mars.")
    g.f("L2", "India's Mars Orbiter Mission (Mangalyaan) was launched in:", "2013",
        ["2014|year of Mars orbit insertion", "2008|Chandrayaan-1 year", "2016|random year"],
        "MOM was launched on 5 November 2013 and entered Mars orbit on 24 September 2014.",
        "Launch year and arrival year differ.", kind="numerical")
    g.st(O, "L3", "Consider the following statements about Chandrayaan-3:",
         [("Its lander and rover were named Vikram and Pragyan respectively.", True),
          ("It landed near the lunar north pole.", False),
          ("It was launched by the LVM3 rocket.", True)],
         ["Vikram lander, Pragyan rover; launched by LVM3-M4 in July 2023.", "It landed near the lunar south pole on 23 August 2023."],
         "South pole, not north.")
    g.o("L2", "Aditya-L1, India's first space-based solar observatory, is stationed in a halo orbit around:",
        "The Sun–Earth Lagrange point L1",
        ["The Earth–Moon Lagrange point L1|wrong two-body system", "The Sun–Earth Lagrange point L2|where JWST is",
         "A geostationary orbit above India|confuses with communication satellites"],
        "Aditya-L1 (launched 2023) sits ~1.5 million km from Earth towards the Sun, giving an uninterrupted view of the Sun.",
        "L2 faces away from the Sun.")
    g.mt(O, "L3", "Match the spacecraft with its notable target or achievement:", "Spacecraft", "Target / achievement",
         [("Voyager 1", "First probe to enter interstellar space"), ("Juno", "Jupiter orbiter"),
          ("Cassini", "Saturn orbiter"), ("New Horizons", "Pluto flyby")],
         "Voyager 1 crossed the heliopause in 2012; Juno—Jupiter; Cassini—Saturn; New Horizons—Pluto (2015).",
         "Juno (Jupiter) vs Cassini (Saturn).")
    g.st(O, "L3", "Consider the following statements about Indian launch vehicles:",
         [("PSLV has four stages that alternate between solid and liquid propulsion.", True),
          ("The upper stage of PSLV uses cryogenic propulsion.", False),
          ("SLV-3 placed a Rohini satellite in orbit in 1980.", True)],
         ["PSLV: solid–liquid–solid–liquid.", "Cryogenic upper stages are used on GSLV and LVM3, not PSLV.",
          "SLV-3's successful flight in July 1980 orbited Rohini."], "Cryogenic = GSLV family.")
    g.o("L3", "During the Apollo 11 mission (1969), which astronaut remained in lunar orbit in the command module?",
        "Michael Collins",
        ["Buzz Aldrin|second person on the Moon", "Neil Armstrong|first person on the Moon", "Yuri Gagarin|Soviet, first in space"],
        "Armstrong and Aldrin landed; Collins piloted Columbia in orbit.", "Only two of the three walked on the Moon.")
    g.ar(O, "L3", "A geostationary satellite appears stationary over a point on the equator.",
         "Its orbital period equals Earth's rotation period and it orbits in the equatorial plane in the direction of Earth's rotation.",
         True, True, True, "Matching period, plane and direction make it fixed relative to the ground.",
         "A geosynchronous but inclined orbit would trace a figure-8.", ref="NCERT Class 11 Physics (Gravitation)")
    g.o("L3", "Remote-sensing satellites are usually placed in sun-synchronous polar orbits mainly because such orbits:",
        "Pass over a place at the same local solar time",
        ["Keep the satellite fixed over one point|that is geostationary", "Can be reached without any upper-stage rocket|false",
         "Keep the satellite permanently out of Earth's shadow|not generally true"],
        "Constant local time gives consistent illumination for comparing images across dates.",
        "Geostationary is for communication/weather over one region.")
    g.mt(O, "L3", "Match the space telescope with its description:", "Telescope", "Description",
         [("Hubble", "Launched 1990 into low Earth orbit"), ("James Webb", "Infrared observatory at Sun–Earth L2"),
          ("AstroSat", "India's first multi-wavelength space observatory"), ("Chandra", "NASA X-ray observatory")],
         "Hubble (1990, LEO); JWST (2021, L2, infrared); AstroSat (ISRO, 2015); Chandra (NASA, X-ray, 1999).",
         "JWST is at L2, Hubble in LEO.")
    g.o("L2", "Kalpana Chawla lost her life in 2003 in the disaster involving the Space Shuttle:", "Columbia",
        ["Challenger|1986 disaster", "Discovery|flew safely", "Atlantis|flew safely"],
        "Columbia broke up during re-entry on 1 February 2003.", "Challenger was 1986.")
    g.o("L3", "With the SpaDeX mission (docking achieved in January 2025), India became which country to demonstrate in-space docking?",
        "Fourth", ["Third|misses one earlier country", "Fifth|over-counts", "Second|ignores Russia/China"],
        "After the USA, Russia and China, India became the fourth nation to achieve satellite docking.",
        "Count USA, Russia, China first.", kind="numerical")

    # ------------------------------------------------------------------ units & scales
    g.m("gk-units-and-scales", "SI Brochure (BIPM, 9th ed., 2019); NCERT Class 11 Physics Ch. 1")
    g.f("L1", "The SI unit of force is the:", "Newton",
        ["Joule|unit of energy", "Pascal|unit of pressure", "Watt|unit of power"], "1 N = 1 kg·m/s².", "Joule is work.")
    g.f("L1", "Which of the following is an SI base unit?", "Ampere",
        ["Volt|derived unit", "Newton|derived unit", "Ohm|derived unit"],
        "The ampere (electric current) is one of the seven SI base units.", "Volt and ohm are derived from the ampere.")
    g.f("L1", "One nautical mile is equal to:", "1,852 metres",
        ["1,609 metres|statute mile", "1,000 metres|kilometre", "1,760 metres|confuses with yards per mile"],
        "The international nautical mile is exactly 1,852 m.", "The land mile is ~1,609 m.", kind="numerical")
    g.f("L1", "The Richter scale is used to measure the:", "Earthquake magnitude",
        ["Intensity of wind|Beaufort scale", "Hardness of minerals|Mohs scale", "Loudness of sound|decibel scale"],
        "Richter's logarithmic scale measures the energy-related magnitude of earthquakes.", "Different scales for different quantities.")
    k0 = -273.15
    g.f("L2", "Absolute zero on the Celsius scale is:", f"{k0} °C",
        ["0 °C|freezing point of water", "-100 °C|round-number guess", "-459.67 °C|Fahrenheit value quoted in °C"],
        "0 K = −273.15 °C by definition of the kelvin offset.", "−459.67 is °F, not °C.", kind="numerical")
    g.st(O, "L3", "Consider the following statements about the SI system:",
         [("The candela is an SI base unit.", True),
          ("The newton is an SI base unit.", False),
          ("The mole is an SI base unit.", True)],
         ["Seven base units: metre, kilogram, second, ampere, kelvin, mole, candela.", "Newton is derived (kg·m/s²)."],
         "Units named after scientists are often derived — but the ampere and kelvin are base units.")
    g.mt(O, "L3", "Match the scale with the quantity it measures:", "Scale", "Quantity",
         [("Beaufort", "Wind speed"), ("Mohs", "Mineral hardness"), ("Decibel", "Sound level"),
          ("Saffir–Simpson", "Hurricane intensity")],
         "Beaufort 0–12 wind force; Mohs 1–10 hardness; decibel logarithmic sound level; Saffir–Simpson categories 1–5.",
         "Saffir–Simpson is for hurricanes, not earthquakes.", ref="WMO / standard physics references")
    t = -40
    assert t * 9 / 5 + 32 == t
    g.o("L2", "At what temperature do the Celsius and Fahrenheit scales show the same reading?", "−40°",
        ["0°|Celsius freezing point", "−32°|confuses the 32° offset", "40°|drops the sign"],
        ["Set F = C in F = 9C/5 + 32: C = 9C/5 + 32 ⇒ −4C/5 = 32 ⇒ C = −40."],
        "The sign matters: +40 °C is 104 °F.", kind="numerical", formula="F = 9C/5 + 32")
    g.o("L3", "Since the 2019 redefinition of SI units, the kilogram is defined by fixing the numerical value of the:",
        "Planck constant",
        ["Avogadro constant|now defines the mole", "Boltzmann constant|now defines the kelvin",
         "Elementary charge|now defines the ampere"],
        "Since 20 May 2019 the kilogram is defined through h = 6.626 070 15 × 10⁻³⁴ J·s, replacing the platinum-iridium prototype.",
        "Each redefined unit is tied to a different constant.")
    g.o("L2", "Which of the following is NOT a unit of energy?", "Pascal",
        ["Electron-volt|energy unit", "Calorie|energy unit", "Kilowatt-hour|energy unit"],
        "Pascal is a unit of pressure (N/m²); the others measure energy.", "kWh is energy, not power.")
    g.ar(O, "L3", "An increase of 20 dB corresponds to a 20-fold increase in sound intensity.",
         "The decibel scale is logarithmic, with every 10 dB representing a tenfold change in intensity.",
         False, True, False, "20 dB = 2 × 10 dB ⇒ 10 × 10 = 100 times, not 20 times; A is false, R is true.", "Do not treat decibels as linear.")
    g.st(O, "L3", "Consider the following statements about earthquake scales:",
         [("The Richter magnitude scale is logarithmic.", True),
          ("A magnitude-6 earthquake releases ten times the energy of a magnitude-5 earthquake.", False),
          ("The Mercalli scale rates intensity based on observed effects.", True)],
         ["Each unit of magnitude = 10× amplitude but ≈ 31.6× energy.", "Mercalli uses Roman numerals I–XII for observed effects."],
         "Tenfold is amplitude, not energy.", ref="NCERT Class 11 Geography; USGS")
    ratio = 10 ** (5 - 2)
    g.o("L3", "A solution with pH 2 has how many times the hydrogen-ion concentration of a solution with pH 5?",
        f"{ratio:,} times", ["3 times|subtracts pH values linearly", "100 times|one power of ten short",
                             "30 times|multiplies the difference by 10"],
        ["pH = −log[H⁺]; a difference of 3 units ⇒ 10³ = 1,000."], "pH is logarithmic.",
        kind="numerical", ref="NCERT Class 10 Science, Ch. 2", formula="[H⁺] ratio = 10^(ΔpH)")
    g.o("L2", "One imperial (mechanical) horsepower is approximately equal to:", "746 watts",
        ["1,000 watts|confuses with a kilowatt", "550 watts|550 ft·lbf/s read as watts", "373 watts|half the true value"],
        "1 hp = 550 ft·lbf/s ≈ 745.7 W.", "550 is in foot-pounds per second, not watts.", kind="numerical")
    purity = 22 / 24
    g.o("L2", "What is the approximate percentage of pure gold in 22-carat gold?", f"{purity*100:.2f}%",
        ["22%|reads carat as percent", "88%|uses 25 as the base", f"{24/22*100:.2f}%|inverts the ratio"],
        ["Pure gold is 24 carat; 22/24 = 0.9167 ⇒ 91.67%."], "Base is 24, not 100.", kind="numerical",
        formula="Purity = carat ÷ 24")
