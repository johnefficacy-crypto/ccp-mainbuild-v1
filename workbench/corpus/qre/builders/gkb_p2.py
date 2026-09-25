"""QRE-GK-B part 2: Geography (12 microtopics)."""


def add_all(g):
    F, O = "foundation", "officer"

    # ------------------------------------------------------------------ biodiversity
    g.m("gk-biodiversity", "Wildlife (Protection) Act, 1972; MoEFCC / NTCA official descriptions; NCERT Class 12 Biology Ch. 13")
    g.f("L1", "Project Tiger was launched in India in:", "1973",
        ["1972|year of the Wildlife (Protection) Act", "1992|Project Elephant", "1986|Environment Protection Act year"],
        "Project Tiger began on 1 April 1973 at Jim Corbett National Park.", "1972 is the WPA, not Project Tiger.", kind="numerical")
    g.f("L1", "The only natural habitat of the Asiatic lion in the wild is in:", "Gir, Gujarat",
        ["Kaziranga, Assam|rhino habitat", "Sundarbans, West Bengal|tiger habitat", "Ranthambore, Rajasthan|tiger reserve"],
        "Asiatic lions survive in the wild only in the Gir landscape of Gujarat.", "Tigers and lions share no wild range in India.")
    g.f("L1", "Which national park holds the largest population of the one-horned rhinoceros?", "Kaziranga",
        ["Jim Corbett|tiger reserve", "Bandipur|elephant/tiger habitat", "Gir|lion habitat"],
        "Kaziranga (Assam) holds about two-thirds of the world's greater one-horned rhinos.", "Corbett is associated with tigers.")
    g.f("L1", "The national aquatic animal of India is the:", "Ganges river dolphin",
        ["Dugong|marine mammal, not the national aquatic animal", "Olive Ridley turtle|marine turtle",
         "Gharial|fish-eating crocodilian"],
        "The Gangetic dolphin was declared the national aquatic animal in 2009.", "It is a freshwater dolphin.")
    g.f("L1", "The Wildlife (Protection) Act was enacted in:", "1972",
        ["1980|Forest (Conservation) Act", "1986|Environment (Protection) Act", "2002|Biological Diversity Act"],
        "The WPA, 1972 provides for protected areas and schedules of protected species.", "Each environmental law has a distinct year.",
        kind="numerical")
    g.st(O, "L3", "Consider the following statements about the IUCN Red List:",
         [("It is legally binding on all member states.", False),
          ("'Critically Endangered' indicates a higher risk of extinction than 'Endangered'.", True),
          ("IUCN is headquartered in Gland, Switzerland.", True)],
         ["The Red List is an assessment, not a treaty.", "Risk order: VU < EN < CR < EW < EX.", "IUCN HQ: Gland."],
         "CITES is binding; the Red List is not.", ref="IUCN official documentation")
    g.mt(O, "L3", "Match the national park with its state:", "National park", "State",
         [("Keibul Lamjao", "Manipur"), ("Silent Valley", "Kerala"), ("Dudhwa", "Uttar Pradesh"), ("Namdapha", "Arunachal Pradesh")],
         "Keibul Lamjao (floating park, sangai); Silent Valley (Kerala); Dudhwa (Terai, UP); Namdapha (Arunachal).",
         "Keibul Lamjao floats on Loktak Lake, Manipur.")
    g.o("L2", "Which of the following is NOT one of the four biodiversity hotspots that extend into India?", "Eastern Ghats",
        ["Western Ghats and Sri Lanka|recognised hotspot", "Indo-Burma|recognised hotspot", "Sundaland|recognised hotspot (Nicobar)"],
        "India's hotspots: Himalaya, Indo-Burma, Western Ghats–Sri Lanka and Sundaland.", "Eastern Ghats is not a listed hotspot.",
        ref="Conservation International hotspot list")
    g.st(O, "L3", "Consider the following statements about the Biological Diversity Act, 2002:",
         [("The National Biodiversity Authority is headquartered in Chennai.", True),
          ("The Act was enacted to give effect to the Convention on Biological Diversity.", True),
          ("Biodiversity Management Committees are constituted at the national level.", False)],
         ["NBA—Chennai; the Act implements CBD.", "BMCs are constituted by local bodies (three-tier: NBA, SBB, BMC)."],
         "BMCs are the local tier.", ref="Biological Diversity Act, 2002")
    g.mt(O, "L3", "Match the international convention with its subject:", "Convention", "Subject",
         [("CITES", "International trade in endangered species"), ("Ramsar", "Wetlands of international importance"),
          ("CMS (Bonn)", "Migratory species of wild animals"), ("CBD", "Conservation and sustainable use of biodiversity")],
         "CITES 1973; Ramsar 1971; CMS 1979; CBD 1992 (Rio).", "CITES is about trade, not habitats.")
    g.ar(O, "L3", "Mass nesting (arribada) of Olive Ridley turtles takes place at Gahirmatha on the Odisha coast.",
         "Olive Ridley turtles are freshwater turtles that breed in river channels.",
         True, False, False, "Gahirmatha is a major arribada site; Olive Ridleys are marine turtles, so R is false.",
         "They nest on sea beaches.")
    g.st(O, "L3", "Consider the following statements:",
         [("Project Elephant was launched in 1992.", True),
          ("The Asian elephant is listed in Schedule I of the Wildlife (Protection) Act, 1972.", True),
          ("The National Tiger Conservation Authority is a statutory body.", True)],
         ["Project Elephant: 1992.", "Elephant: Schedule I.", "NTCA was constituted in 2006 under the WPA amendment."],
         "All three are true.")
    g.o("L2", "India's first biosphere reserve, designated in 1986, is:", "Nilgiri",
        ["Nanda Devi|designated 1988", "Sundarbans|designated 1989", "Gulf of Mannar|designated 1989"],
        "The Nilgiri Biosphere Reserve spans Tamil Nadu, Kerala and Karnataka.", "Nilgiri is also the first Indian MAB listing (2000).",
        ref="MoEFCC biosphere reserve list")
    g.o("L2", "Which of the following is an ex-situ method of conservation?", "Seed or gene bank",
        ["National park|in-situ", "Sacred grove|in-situ", "Biosphere reserve|in-situ"],
        "Ex-situ = outside the natural habitat (zoos, botanical gardens, gene banks).", "Protected areas are in-situ.")
    g.mt(O, "L3", "Match the species with its characteristic habitat region:", "Species", "Region",
         [("Great Indian Bustard", "Thar desert grasslands"), ("Hoolock gibbon", "North-eastern forests"),
          ("Nilgiri tahr", "Western Ghats montane grasslands"), ("Snow leopard", "Trans-Himalaya")],
         "GIB—arid grasslands; Hoolock—India's only ape, NE; Nilgiri tahr—Western Ghats; snow leopard—high Himalaya.",
         "Hoolock gibbon is India's only ape.")

    # ------------------------------------------------------------------ climate
    g.m("gk-climate-and-ocean", "NCERT Class 11 Geography (Fundamentals of Physical Geography; India—Physical Environment)")
    g.f("L1", "El Niño refers to the abnormal warming of surface waters in the:", "Central and eastern equatorial Pacific",
        ["Western equatorial Indian Ocean off East Africa|positive IOD", "North Atlantic Ocean near Iceland|NAO region",
         "Bay of Bengal near Sri Lanka|cyclone basin"],
        "El Niño is anomalous warming off Peru and across the central–eastern tropical Pacific.", "IOD is the Indian Ocean analogue.")
    g.f("L1", "In the Northern Hemisphere, the Coriolis force deflects moving air to the:", "Right",
        ["Left|Southern Hemisphere", "Upwards|not a horizontal deflection", "Neither side|it does act"],
        "Coriolis deflection is to the right in the NH and left in the SH.", "Reversed in the Southern Hemisphere.")
    g.f("L1", "'Mango showers' are pre-monsoon showers common in:", "Kerala and coastal Karnataka",
        ["Punjab and Haryana|western disturbances", "Assam and sub-Himalayan West Bengal|Nor'westers", "Western Rajasthan and Kutch|arid region"],
        "Late-summer thunder showers in Kerala and Karnataka help early ripening of mangoes.", "Kalbaisakhi is Bengal/Assam.")
    g.f("L1", "'Loo' is a:", "Hot, dry wind of the northern plains",
        ["Cold winter wind of the Kashmir valley|opposite nature", "Rain-bearing monsoon wind|moist wind", "Local sea breeze of Kerala|coastal breeze"],
        "Loo blows over the northern plains in May–June.", "It is a hot wind.")
    g.f("L1", "Tropical cyclones that form over the North Atlantic are called:", "Hurricanes",
        ["Typhoons|western Pacific", "Willy-willies|Australia", "Tornadoes|small-scale land vortices"],
        "Hurricane (Atlantic/eastern Pacific), typhoon (western Pacific), cyclone (Indian Ocean).", "Tornadoes are not tropical cyclones.")
    g.st(O, "L3", "Consider the following statements about the Indian Ocean Dipole (IOD):",
         [("A positive IOD means the western Indian Ocean is warmer than the eastern part.", True),
          ("The IOD is a phenomenon of the Pacific Ocean.", False),
          ("A positive IOD generally favours the Indian south-west monsoon.", True)],
         ["Positive IOD: warm west, cool east; generally good for monsoon.", "IOD is in the Indian Ocean."],
         "IOD can offset El Niño's effect.")
    g.ar(O, "L3", "Tropical cyclones rarely form within about 5° of the equator.", "The Coriolis force is negligible near the equator.",
         True, True, True, "Cyclonic spin needs Coriolis force, which is near zero at the equator.",
         "Warm water alone is not enough.")
    g.mt(O, "L3", "Match the local wind with its region:", "Wind", "Region",
         [("Chinook", "Eastern slopes of the Rockies"), ("Foehn", "Alps"), ("Sirocco", "Sahara to the Mediterranean"),
          ("Mistral", "Rhône valley, France")],
         "Chinook and Foehn are warm dry descending winds; Sirocco hot dusty wind; Mistral cold northerly.",
         "Chinook (N. America) vs Foehn (Europe).")
    g.o("L3", "The sudden onset of the south-west monsoon over north India is associated with:",
        "Northward shift of the westerly jet beyond the Himalaya",
        ["Southward shift of the westerly jet over the plains|opposite movement",
         "Formation of western disturbances over Iran|winter phenomenon",
         "Strengthening of the north-east trade winds|winter monsoon"],
        "The subtropical westerly jet withdraws north of the Himalaya and the tropical easterly jet sets in.",
        "Western disturbances are winter systems.")
    g.o("L2", "Which part of India receives most of its annual rainfall during October–December?", "Tamil Nadu coast",
        ["Konkan coast|SW monsoon", "Meghalaya plateau|SW monsoon", "Punjab plains|SW monsoon plus WDs"],
        "The Coromandel coast gets the bulk of its rain from the retreating/north-east monsoon.", "Tamil Nadu is in the rain shadow in June–Sept.")
    g.st(O, "L3", "Consider the following statements about western disturbances:",
         [("They are driven eastward by the tropical easterly trade winds.", False),
          ("They originate over the Mediterranean region.", True),
          ("They bring winter rain to the north-western plains and snow to the western Himalaya.", True)],
         ["They are carried by the westerlies, not the easterlies.", "Origin: Mediterranean; effect: winter rain, good for rabi."],
         "Name 'western' reflects the westerlies.")
    g.mt(O, "L3", "Match the ocean current with its ocean:", "Current", "Ocean",
         [("Kuroshio", "North Pacific"), ("Benguela", "South Atlantic"), ("Agulhas", "Indian Ocean"), ("Labrador", "North Atlantic")],
         "Kuroshio (warm, off Japan); Benguela (cold, SW Africa); Agulhas (warm, SE Africa); Labrador (cold, off Canada).",
         "Benguela (Atlantic side) vs Agulhas (Indian Ocean side) of South Africa.")
    g.ar(O, "L3", "The Atacama Desert on the west coast of South America is among the driest places on Earth.",
         "The cold Humboldt (Peru) current cools and stabilises the air above it, suppressing rainfall.",
         True, True, True, "Cold currents create stable air and fog but little rain; R explains A.", "Cold currents flank west-coast deserts.")
    g.o("L2", "Which of the following surfaces has the highest albedo?", "Fresh snow",
        ["Dense forest|low albedo", "Open ocean|very low albedo", "Asphalt road|very low albedo"],
        "Fresh snow reflects up to about 80–90% of incoming sunlight.", "Dark surfaces absorb more.")
    g.st(O, "L3", "Consider the following statements about the atmosphere:",
         [("The troposphere is thicker at the equator than at the poles.", True),
          ("Temperature generally increases with height in the troposphere.", False),
          ("The ozone layer lies in the stratosphere.", True)],
         ["Troposphere ~18 km at equator vs ~8 km at poles.", "Temperature falls ~6.5 °C/km in the troposphere.",
          "Ozone layer: stratosphere."], "Temperature rises with height in the stratosphere, not troposphere.")

    # ------------------------------------------------------------------ countries & capitals
    g.m("gk-countries-capitals", "NCERT Class 9 Geography (India—Size and Location); standard world atlas")
    g.f("L1", "The capital of Australia is:", "Canberra",
        ["Sydney|largest city", "Melbourne|former seat of parliament", "Perth|western city"], "Canberra is Australia's capital.",
        "Largest city is not always the capital.")
    g.f("L1", "The capital of Canada is:", "Ottawa",
        ["Toronto|largest city", "Montreal|major city", "Vancouver|Pacific port"], "Ottawa, Ontario, is the capital.",
        "Toronto is the largest city.")
    g.f("L1", "The largest country in the world by area is:", "Russia",
        ["Canada|second largest", "China|third/fourth", "United States|third/fourth"], "Russia covers about 17.1 million km².",
        "Canada is second.")
    g.f("L1", "India shares its longest international land border with:", "Bangladesh",
        ["China|second longest", "Pakistan|third longest", "Nepal|shorter border"],
        "The India–Bangladesh border is about 4,097 km long.", "China is second.")
    g.f("L2", "The Tropic of Cancer passes through how many Indian states?", "8",
        ["6|undercount", "7|misses Mizoram or Tripura", "9|over-count"],
        "Gujarat, Rajasthan, Madhya Pradesh, Chhattisgarh, Jharkhand, West Bengal, Tripura, Mizoram.",
        "Tripura and Mizoram are often missed.", kind="numerical")
    g.mt(O, "L3", "Match the country with its capital:", "Country", "Capital",
         [("Türkiye", "Ankara"), ("Myanmar", "Naypyidaw"), ("Nigeria", "Abuja"), ("Brazil", "Brasília")],
         "Each is a planned/relocated capital: Ankara, Naypyidaw, Abuja, Brasília.",
         "Istanbul, Yangon, Lagos and Rio are former/largest cities, not capitals.")
    g.st(O, "L3", "Consider the following statements about India's location and extent:",
         [("The southernmost point of mainland India is Indira Point.", False),
          ("The Standard Meridian of India, 82°30′E, passes through Mirzapur in Uttar Pradesh.", True),
          ("India's north–south extent is greater than its east–west extent.", True)],
         ["Indira Point is in Great Nicobar; the mainland tip is Kanyakumari.", "IST meridian: Mirzapur.",
          "N–S ≈ 3,214 km; E–W ≈ 2,933 km."], "Mainland vs territory including islands.")
    g.o("L2", "Which of the following states does NOT share a border with Nepal?", "Himachal Pradesh",
        ["Sikkim|borders Nepal", "Bihar|borders Nepal", "Uttarakhand|borders Nepal"],
        "Nepal borders Uttarakhand, UP, Bihar, West Bengal and Sikkim.", "Himachal borders China, not Nepal.")
    g.o("L3", "Which of the following is a doubly landlocked country (surrounded only by landlocked countries)?", "Uzbekistan",
        ["Kazakhstan|landlocked but borders Russia/China", "Mongolia|borders Russia and China", "Nepal|borders India and China"],
        "Uzbekistan and Liechtenstein are the two doubly landlocked countries.", "Singly landlocked is not doubly landlocked.")
    g.mt(O, "L3", "Match the water body with what it separates:", "Strait / channel", "Separates",
         [("Palk Strait", "India and Sri Lanka"), ("Ten Degree Channel", "Andaman and Nicobar groups"),
          ("Duncan Passage", "South Andaman and Little Andaman"), ("Eight Degree Channel", "Minicoy and the Maldives")],
         "Standard NCERT locational facts.", "Ten Degree (Andaman–Nicobar) vs Eight Degree (Minicoy–Maldives).")
    g.o("L2", "Which of the following states does NOT share a border with Bangladesh?", "Manipur",
        ["Tripura|borders Bangladesh", "Meghalaya|borders Bangladesh", "Mizoram|borders Bangladesh"],
        "Bangladesh borders West Bengal, Assam, Meghalaya, Tripura and Mizoram.", "Manipur borders Myanmar.")
    g.ar(O, "L3", "The sun rises in Arunachal Pradesh about two hours earlier than in western Gujarat.",
         "India spans about 30° of longitude, and local time changes by 4 minutes for each degree.",
         True, True, True, "30° × 4 min = 120 min; R explains A.", "Longitude, not latitude, drives local time.",
         ref="NCERT Class 9 Geography, Ch. 1")
    g.o("L2", "Which country–capital pair is correctly matched?", "Sri Lanka – Sri Jayawardenepura Kotte",
        ["Switzerland – Geneva (seat of many UN bodies)|capital is Bern", "New Zealand – Auckland (largest city)|capital is Wellington",
         "Türkiye – Istanbul|capital is Ankara"],
        "Sri Jayawardenepura Kotte is Sri Lanka's legislative capital; Colombo is the commercial capital.",
        "Famous cities are often not capitals.")
    g.st(O, "L3", "Consider the following statements:",
         [("Rajasthan is the largest state of India by area.", True),
          ("Goa is the smallest state of India by area.", True),
          ("Ladakh is the largest Union Territory of India by area.", True)],
         ["All three are correct."], "Do not assume one statement must be false.", ref="Census of India / Survey of India")
    g.o("L2", "The Equator does NOT pass through which of the following countries?", "Nigeria",
        ["Kenya|on the Equator", "Indonesia|on the Equator", "Ecuador|named after the Equator"],
        "Nigeria lies entirely north of the Equator (about 4°–14°N).", "Gulf of Guinea countries are close but not all on it.")

    # ------------------------------------------------------------------ crops
    g.m("gk-crops-cropping", "NCERT Class 10 Geography (Agriculture); Ministry of Agriculture statistics — leading states are long-standing")
    g.f("L1", "Which of the following is a rabi crop?", "Wheat",
        ["Rice|kharif", "Cotton|kharif", "Jowar|kharif (in most regions)"],
        "Rabi crops are sown in winter (Oct–Dec) and harvested in spring; wheat is the main rabi crop.",
        "Rice is the typical kharif crop.")
    g.f("L1", "Watermelon and cucumber grown in the short season between rabi and kharif are called:", "Zaid crops",
        ["Kharif crops|monsoon season", "Rabi crops|winter season", "Plantation crops|estate crops"],
        "The zaid season falls in summer (March–June).", "Zaid is the third, short season.")
    g.f("L1", "Which state is the largest producer of tea in India?", "Assam",
        ["West Bengal|second (Darjeeling/Dooars)", "Kerala|smaller producer", "Tamil Nadu|Nilgiris producer"],
        "Assam produces over half of India's tea.", "Darjeeling fame does not mean largest output.")
    g.f("L1", "Which state is the largest producer of coffee in India?", "Karnataka",
        ["Kerala|second", "Tamil Nadu|third", "Assam|tea state"], "Karnataka accounts for about 70% of India's coffee.",
        "Kerala is second.")
    g.f("L1", "Jute, the 'golden fibre', is produced mainly in:", "West Bengal",
        ["Punjab|wheat/rice state", "Gujarat|cotton/groundnut", "Kerala|rubber/coconut"],
        "West Bengal leads jute production (Ganga–Brahmaputra delta).", "Golden fibre = jute.")
    g.mt(O, "L3", "Match the crop with the state that is its leading producer:", "Crop", "State",
         [("Natural rubber", "Kerala"), ("Sugarcane", "Uttar Pradesh"), ("Bajra", "Rajasthan"), ("Saffron", "Jammu and Kashmir")],
         "Long-standing leaders: Kerala rubber; UP sugarcane; Rajasthan bajra; J&K (Pampore) saffron.",
         "Maharashtra is second in sugarcane, not first.")
    g.ar(O, "L3", "Black (regur) soil is well suited for cotton cultivation.",
         "Black soil has a high capacity to retain moisture.", True, True, True,
         "Moisture retention supports cotton through the dry spells; R explains A.", "Black soil forms from Deccan basalt.")
    g.st(O, "L3", "Consider the following statements:",
         [("Rice requires high temperature and generally more than 100 cm of rainfall.", True),
          ("Tea is grown on well-drained, gently sloping land.", True),
          ("Wheat is primarily a kharif crop in India.", False)],
         ["Rice: high temperature and humidity.", "Tea: well-drained slopes.", "Wheat is rabi."], "Wheat = rabi.")
    g.o("L2", "Which crop–season pair is INCORRECTLY matched?", "Mustard – Kharif",
        ["Paddy – Kharif|correct pair", "Gram – Rabi|correct pair", "Watermelon – Zaid|correct pair"],
        "Mustard is a rabi oilseed.", "Mustard is sown in winter.")
    g.mt(O, "L3", "Match the 'revolution' with its sector:", "Revolution", "Sector",
         [("Green", "Food grains"), ("White", "Milk"), ("Blue", "Fisheries"), ("Yellow", "Oilseeds")],
         "Green—grains; White (Operation Flood)—milk; Blue—fish; Yellow—oilseeds.", "Yellow is oilseeds, not eggs.")
    g.st(O, "L3", "Consider the following statements about coffee in India:",
         [("Coffee in India is mostly grown without shade trees.", False),
          ("Arabica and Robusta are the two main varieties grown.", True),
          ("Coffee is grown mainly in the Western Ghats of Karnataka, Kerala and Tamil Nadu.", True)],
         ["Indian coffee is shade-grown.", "Arabica and Robusta; southern Western Ghats."], "Indian coffee is shade-grown.")
    g.o("L2", "Minimum Support Prices for crops are announced by the Government on the recommendation of:",
        "Commission for Agricultural Costs and Prices",
        ["Food Corporation of India through its regional offices|procurement agency", "NABARD|development bank", "NITI Aayog's agriculture vertical|policy think tank"],
        "The CACP recommends MSPs; the Union Government announces them.", "FCI buys; CACP recommends.")
    g.o("L3", "According to standard geography texts, cotton requires about how many frost-free days?", "210",
        ["90|too short", "120|too short", "365|year-round"],
        "Cotton needs high temperature, light rainfall and about 210 frost-free days.", "Frost damages the bolls.",
        kind="numerical", ref="NCERT Class 10 Geography, Ch. 4")
    g.ar(O, "L3", "Pulses are grown in rotation with other crops to help restore soil fertility.",
         "Leguminous crops fix atmospheric nitrogen through bacteria in their root nodules.", True, True, True,
         "Nitrogen fixation explains the soil benefit.", "Rhizobium lives in the root nodules.")
    g.ar(O, "L3", "Sugarcane is grown in both tropical and sub-tropical parts of India.",
         "Sugarcane is a rabi crop sown and harvested within the winter season.", True, False, False,
         "Sugarcane is a long-duration crop (about a year); R is false.", "It is not a short rabi crop.")

    # ------------------------------------------------------------------ GI tags
    g.m("gk-geographical-indication", "Geographical Indications of Goods (Registration and Protection) Act, 1999; GI Registry journal")
    g.f("L1", "The first product in India to receive a Geographical Indication tag was:", "Darjeeling tea",
        ["Basmati rice|GI came later", "Mysore silk|GI came later", "Nagpur orange|GI came later"],
        "Darjeeling tea was registered in 2004–05.", "It was the first under the 1999 Act.")
    g.f("L1", "The Geographical Indications Registry of India is located in:", "Chennai",
        ["Mumbai|patent office branch", "New Delhi|patent office branch", "Kolkata|patent office HQ"],
        "The GI Registry functions at Chennai.", "Kolkata hosts the Patent Office HQ.")
    g.f("L1", "Pochampally Ikat is a GI-tagged textile from:", "Telangana",
        ["Odisha|Sambalpuri ikat", "Gujarat|Patola", "Tamil Nadu|Kanchipuram silk"],
        "Pochampally (Bhoodan Pochampally), Telangana, is famed for ikat.", "Several states have ikat traditions.")
    g.f("L1", "Kanchipuram silk sarees are a GI product of:", "Tamil Nadu",
        ["Karnataka|Mysore silk", "Andhra Pradesh|Venkatagiri/Dharmavaram", "Kerala|Kasavu"],
        "Kanchipuram is in Tamil Nadu.", "Mysore silk is Karnataka.")
    g.f("L1", "Madhubani painting is associated with:", "Bihar",
        ["Maharashtra|Warli", "Odisha|Pattachitra", "Rajasthan|Phad"], "Madhubani (Mithila) painting is from Bihar.",
        "Each folk art has a home state.")
    g.mt(O, "L3", "Match the GI textile with its state:", "Textile", "State",
         [("Muga silk", "Assam"), ("Chanderi saree", "Madhya Pradesh"), ("Banarasi brocade", "Uttar Pradesh"),
          ("Paithani saree", "Maharashtra")],
         "Muga—Assam; Chanderi—MP; Banarasi—UP; Paithani—Maharashtra.", "Chanderi (MP) vs Chettinad (TN).")
    g.mt(O, "L3", "Match the GI food product with its state:", "Product", "State",
         [("Bikaneri bhujia", "Rajasthan"), ("Dharwad pedha", "Karnataka"), ("Tirupati laddu", "Andhra Pradesh"),
          ("Odisha rasagola", "Odisha")],
         "Bikaner (Rajasthan); Dharwad (Karnataka); Tirupati (AP); Odisha rasagola.",
         "Tirupati is in Andhra Pradesh, not Tamil Nadu.")
    g.st(O, "L3", "Consider the following statements about GI protection in India:",
         [("GI registration is valid for ten years and can be renewed.", True),
          ("The governing law was enacted in 1999.", True),
          ("Geographical indications are protected under the WTO TRIPS Agreement.", True)],
         ["10-year validity, renewable.", "GI Act 1999 (in force 2003).", "TRIPS Arts. 22–24 cover GIs."],
         "All three are correct.")
    g.mt(O, "L3", "Match the painting tradition with its state:", "Painting", "State",
         [("Warli", "Maharashtra"), ("Gond", "Madhya Pradesh"), ("Phad", "Rajasthan"), ("Tanjore", "Tamil Nadu")],
         "Warli—Maharashtra; Gond—MP; Phad scroll—Rajasthan; Tanjore—TN.", "Phad (Rajasthan) vs Pattachitra (Odisha).")
    g.o("L2", "Channapatna toys, a GI-tagged lacquered wooden craft, belong to:", "Karnataka",
        ["Andhra Pradesh|Kondapalli / Etikoppaka toys", "Telangana|Nirmal toys", "West Bengal|terracotta"],
        "Channapatna is in Ramanagara district, Karnataka.", "South India has several toy GIs.")
    g.ar(O, "L3", "Darjeeling tea was the first product to receive a GI tag in India.",
         "The Geographical Indications Act came into force in 2003.", True, True, False,
         "Both are facts, but the Act's commencement does not explain why Darjeeling was first.",
         "True + true need not mean causal.")
    g.mt(O, "L3", "Match the embroidery or weave with its state:", "Craft", "State",
         [("Chikankari", "Uttar Pradesh"), ("Phulkari", "Punjab"), ("Kasuti", "Karnataka"), ("Kota Doria", "Rajasthan")],
         "Chikankari—Lucknow; Phulkari—Punjab; Kasuti—Karnataka; Kota Doria—Kota, Rajasthan.", "Kasuti is Karnataka.")
    g.o("L2", "The Kani shawl is a GI product of:", "Jammu and Kashmir",
        ["Himachal Pradesh|Kullu shawl", "Punjab|Phulkari", "Nagaland|Naga shawls"],
        "Kani shawls are woven with small wooden sticks (kanis) in Kashmir.", "Kullu shawl is Himachal.")
    g.o("L2", "Which craft–state pair is INCORRECTLY matched?", "Dokra metal craft – Kerala",
        ["Bidriware – Karnataka|correct", "Blue pottery – Rajasthan|correct", "Thanjavur art plate – Tamil Nadu|correct"],
        "Dokra is from central/eastern India (Chhattisgarh, West Bengal, Odisha).", "Bidriware is from Bidar.")
    g.o("L2", "Aranmula Kannadi, a GI-tagged metal mirror, is from:", "Kerala",
        ["Tamil Nadu|Thanjavur crafts", "Odisha|silver filigree", "Goa|no such mirror craft"],
        "Aranmula (Pathanamthitta, Kerala) makes metal-alloy mirrors.", "It is a metal, not glass, mirror.")

    # ------------------------------------------------------------------ landmarks
    g.m("gk-landmarks-and-monuments", "NCERT Class 7/12 History; Archaeological Survey of India descriptions")
    g.f("L1", "Construction of the Qutb Minar was begun by:", "Qutb-ud-din Aibak",
        ["Iltutmish|completed it", "Alauddin Khalji|began Alai Minar", "Firoz Shah Tughlaq|repaired it"],
        "Aibak began it c. 1199; Iltutmish completed the upper storeys.", "Iltutmish completed it.")
    g.f("L1", "The Taj Mahal stands on the bank of the river:", "Yamuna",
        ["Ganga|different river", "Chambal|further south", "Gomti|Lucknow's river"],
        "The Taj Mahal is in Agra on the Yamuna.", "Agra is on the Yamuna.")
    g.f("L1", "The Gateway of India in Mumbai commemorates the visit of:", "King George V and Queen Mary",
        ["Queen Victoria|never visited India", "Lord Mountbatten, the last Viceroy|last Viceroy", "King Edward VII and Queen Alexandra|visited as Prince of Wales"],
        "It marks the 1911 royal visit; completed in 1924.", "Also the site of the last British troops' departure (1948).")
    g.f("L1", "The Charminar is located in:", "Hyderabad",
        ["Lucknow|Bara Imambara", "Bijapur|Gol Gumbaz", "Golconda|fort"], "Built in 1591 by Muhammad Quli Qutb Shah.",
        "Golconda is near but distinct.")
    g.f("L1", "The Sun Temple at Konark is in:", "Odisha",
        ["Gujarat|Modhera sun temple", "Tamil Nadu|Chola temples", "Madhya Pradesh|Khajuraho"],
        "Built by Narasimhadeva I of the Eastern Ganga dynasty (13th c.).", "Modhera (Gujarat) also has a sun temple.")
    g.mt(O, "L3", "Match the monument with the ruler who built it:", "Monument", "Builder",
         [("Buland Darwaza", "Akbar"), ("Red Fort, Delhi", "Shah Jahan"), ("Gol Gumbaz", "Muhammad Adil Shah"),
          ("Hawa Mahal", "Sawai Pratap Singh")],
         "Buland Darwaza (Fatehpur Sikri, Akbar); Red Fort (Shah Jahan); Gol Gumbaz (Adil Shah); Hawa Mahal (1799).",
         "Hawa Mahal is by Pratap Singh, not Jai Singh.")
    g.mt(O, "L3", "Match the landmark with its city:", "Landmark", "City",
         [("Victoria Memorial", "Kolkata"), ("Vidhana Soudha", "Bengaluru"), ("Statue of Unity", "Kevadia (Ekta Nagar)"),
          ("India Gate", "New Delhi")],
         "Direct locational facts.", "Vidhana Soudha is Karnataka's legislature.")
    g.st(O, "L3", "Consider the following statements:",
         [("The Brihadeeswarar Temple at Thanjavur was built by Rajaraja Chola I.", True),
          ("The Kailasa temple at Ellora was built under the Rashtrakutas.", True),
          ("The Khajuraho temples were built by the Chalukyas.", False)],
         ["Brihadeeswarar—Rajaraja I (c. 1010).", "Kailasa—Krishna I (Rashtrakuta).", "Khajuraho—Chandelas."],
         "Khajuraho = Chandela.")
    g.o("L2", "The Statue of Unity, depicting Sardar Vallabhbhai Patel, is how tall?", "182 metres",
        ["93 metres|Statue of Liberty with pedestal", "128 metres|Spring Temple Buddha", "240 metres|invented figure"],
        "At 182 m it is the world's tallest statue, near the Sardar Sarovar Dam.", "182 also matches Gujarat's Assembly seats.",
        kind="numerical")
    g.ar(O, "L3", "The Gol Gumbaz at Vijayapura is famous for its whispering gallery.",
         "The Gol Gumbaz was built by the Mughal emperor Shah Jahan.",
         True, False, False, "A is true; R is false — it is the tomb of Muhammad Adil Shah of the Adil Shahi dynasty.", "It is in Karnataka.")
    g.o("L2", "The Great Stupa at Sanchi was originally commissioned by:", "Ashoka",
        ["Kanishka|Kushana ruler", "Harsha|7th-century ruler", "Pushyamitra Shunga|Shunga period enlargement"],
        "Ashoka built the original brick stupa (3rd c. BCE); it was enlarged later.", "Shungas enlarged; Ashoka founded.")
    g.o("L2", "Which city does NOT have a Jantar Mantar built by Sawai Jai Singh II?", "Agra",
        ["Ujjain|has one", "Varanasi|has one", "Mathura|had one"],
        "Jai Singh II built observatories at Delhi, Jaipur, Ujjain, Varanasi and Mathura.", "Agra was not among them.")
    g.ar(O, "L3", "The Iron Pillar at Mehrauli has resisted corrosion for over 1,500 years.",
         "A thin protective layer formed on it because of the high phosphorus content of the iron.", True, True, True,
         "Metallurgical studies attribute the passive film to phosphorus-rich iron.", "It dates to the Gupta period.",
         ref="ASI; metallurgical studies (IIT Kanpur)")
    g.o("L2", "Howrah Bridge over the Hooghly was officially renamed:", "Rabindra Setu",
        ["Vidyasagar Setu|second Hooghly bridge", "Vivekananda Setu|Bally bridge", "Nivedita Setu|second Bally bridge"],
        "Howrah Bridge was renamed Rabindra Setu in 1965.", "Vidyasagar Setu is a different bridge.")
    g.o("L2", "The tomb of Itimad-ud-Daulah at Agra was built by:", "Nur Jahan",
        ["Mumtaz Mahal|died before", "Shah Jahan|built Taj Mahal", "Aurangzeb|Bibi Ka Maqbara linked to his son"],
        "Nur Jahan built it for her father Mirza Ghiyas Beg.", "Often called the 'Baby Taj'.")

    # ------------------------------------------------------------------ dams
    g.m("gk-major-dams", "NCERT Class 10 Geography (Water Resources); Central Water Commission descriptions")
    g.f("L1", "The Bhakra Nangal Dam is built on the river:", "Sutlej",
        ["Beas|Pong dam", "Ravi|Ranjit Sagar dam", "Chenab|Salal/Baglihar"], "Bhakra is on the Sutlej in Himachal Pradesh.",
        "Beas has Pong Dam.")
    g.f("L1", "The Hirakud Dam is on the river:", "Mahanadi",
        ["Godavari|Polavaram", "Brahmani|different river", "Subarnarekha|different river"], "Hirakud, near Sambalpur, Odisha.",
        "One of the longest earthen dams.")
    g.f("L1", "Rihand Dam (Govind Ballabh Pant Sagar) is located in:", "Uttar Pradesh",
        ["Madhya Pradesh|reservoir extends there", "Bihar|nearby state", "Jharkhand|nearby state"],
        "Rihand Dam is in Sonbhadra district, UP.", "The reservoir touches MP.")
    g.f("L1", "The Sardar Sarovar Dam is built on the river:", "Narmada",
        ["Tapi|Ukai dam", "Mahi|Kadana", "Sabarmati|Dharoi"], "Sardar Sarovar is in Gujarat on the Narmada.", "Ukai is Tapi.")
    g.f("L1", "The Nagarjuna Sagar Dam is on the river:", "Krishna",
        ["Godavari|different basin", "Kaveri|Mettur", "Tungabhadra|Tungabhadra dam"], "Nagarjuna Sagar is on the Krishna (Telangana–AP).",
        "Tungabhadra is a tributary, not the dam's river.")
    g.mt(O, "L3", "Match the dam with its river:", "Dam", "River",
         [("Mettur", "Kaveri"), ("Srisailam", "Krishna"), ("Indira Sagar", "Narmada"), ("Salal", "Chenab")],
         "Mettur—Kaveri; Srisailam—Krishna; Indira Sagar—Narmada (MP); Salal—Chenab (J&K).", "Srisailam is Krishna, not Godavari.")
    g.st(O, "L3", "Consider the following statements about the Damodar Valley Corporation:",
         [("The Damodar was known as the 'Sorrow of Bihar'.", False),
          ("DVC was set up in 1948.", True),
          ("It was modelled on the Tennessee Valley Authority of the USA.", True)],
         ["Damodar = 'Sorrow of Bengal'; Kosi = 'Sorrow of Bihar'.", "DVC: 1948, modelled on TVA."],
         "Damodar–Bengal, Kosi–Bihar.")
    g.ar(O, "L2", "The Kosi is called the 'Sorrow of Bihar'.",
         "The Kosi is a right-bank tributary of the Yamuna.", True, False, False,
         "A is true (frequent course shifts and floods); R is false — the Kosi joins the Ganga in Bihar.", "Damodar is the 'Sorrow of Bengal'.")
    g.o("L2", "The tallest dam in India is:", "Tehri Dam",
        ["Bhakra Dam|tallest straight gravity dam", "Idukki Dam|arch dam", "Sardar Sarovar Dam|large concrete gravity dam"],
        "Tehri (about 260 m) on the Bhagirathi, Uttarakhand.", "Bhakra is tallest of its type, not overall.")
    g.o("L2", "The Idukki arch dam is built across the river:", "Periyar",
        ["Pamba|different Kerala river", "Bharathapuzha|different Kerala river", "Chaliyar|different Kerala river"],
        "Idukki arch dam is on the Periyar in Kerala.", "Mullaperiyar is also on the Periyar.")
    g.o("L3", "The main purpose of the Farakka Barrage on the Ganga is to:",
        "Divert water to the Hooghly for Kolkata port",
        ["Generate hydroelectricity for Bangladesh|not its purpose", "Store water for irrigation in Bihar|not a storage dam",
         "Control floods on the Brahmaputra|wrong river"],
        "Farakka (West Bengal, 1975) diverts flow into the Bhagirathi–Hooghly through a feeder canal.", "It is a barrage, not a storage dam.")
    g.st(O, "L3", "Consider the following statements about the Indus Waters Treaty:",
         [("It was signed in 1960 with the World Bank as a signatory facilitator.", True),
          ("The Chenab is one of the eastern rivers.", False),
          ("The Ravi, Beas and Sutlej are the eastern rivers.", True)],
         ["Signed 1960, World Bank-brokered.", "Eastern rivers: Ravi, Beas, Sutlej; western: Indus, Jhelum, Chenab."],
         "Chenab is western.", ref="Indus Waters Treaty, 1960")
    g.mt(O, "L3", "Match the dam with its state:", "Dam", "State",
         [("Ukai", "Gujarat"), ("Almatti", "Karnataka"), ("Pong", "Himachal Pradesh"), ("Maithon", "Jharkhand")],
         "Ukai (Tapi, Gujarat); Almatti (Krishna, Karnataka); Pong (Beas, HP); Maithon (Barakar, DVC, Jharkhand).",
         "Maithon is DVC, in Jharkhand.")
    g.o("L3", "The Mullaperiyar Dam is located in Kerala but is operated and maintained by:", "Tamil Nadu",
        ["Karnataka|no role", "Kerala|location state, not operator", "Central Water Commission|monitoring role"],
        "A 1886 lease gives Tamil Nadu control to divert Periyar water eastwards.", "Location and control differ.")
    g.o("L2", "Which of the following dams is NOT on the Chambal river?", "Ukai",
        ["Gandhi Sagar|on Chambal", "Rana Pratap Sagar|on Chambal", "Jawahar Sagar|on Chambal"],
        "Chambal project: Gandhi Sagar (MP), Rana Pratap Sagar and Jawahar Sagar (Rajasthan).", "Ukai is on the Tapi.")

    # ------------------------------------------------------------------ minerals
    g.m("gk-mineral-resources", "NCERT Class 10 Geography (Minerals and Energy Resources); Indian Bureau of Mines")
    g.f("L1", "The Kolar Gold Fields are located in:", "Karnataka",
        ["Andhra Pradesh|Ramagiri", "Jharkhand|Subarnarekha sands", "Kerala|monazite"],
        "KGF (Kolar district, Karnataka) was a historic gold mine (closed 2001).", "Hutti is the active gold mine, also Karnataka.")
    g.f("L1", "The Jharia coalfield is located in:", "Jharkhand",
        ["Odisha|Talcher", "Chhattisgarh|Korba", "West Bengal|Raniganj"], "Jharia (Dhanbad) is India's key coking-coal field.",
        "Raniganj is West Bengal.")
    g.f("L1", "Khetri is famous for mining:", "Copper",
        ["Gold|Kolar/Hutti", "Mica|Koderma", "Coal|Jharia"], "Khetri (Rajasthan) copper belt.", "Malanjkhand is the other copper site.")
    g.f("L1", "Bauxite is the main ore of:", "Aluminium",
        ["Iron|hematite/magnetite", "Copper|chalcopyrite", "Zinc|sphalerite"], "Bauxite yields alumina, then aluminium.",
        "Iron ores are hematite/magnetite.")
    g.f("L1", "Digboi, one of the oldest oil fields in India, is in:", "Assam",
        ["Gujarat|Ankleshwar", "Maharashtra|Mumbai High offshore", "Rajasthan|Barmer"], "Digboi (1889) in Assam.",
        "Mumbai High is offshore.")
    g.mt(O, "L3", "Match the mining site with its mineral:", "Site", "Mineral",
         [("Bailadila", "Iron ore"), ("Malanjkhand", "Copper"), ("Hutti", "Gold"), ("Zawar", "Lead-zinc")],
         "Bailadila (Chhattisgarh) iron; Malanjkhand (MP) copper; Hutti (Karnataka) gold; Zawar (Rajasthan) lead-zinc.",
         "Zawar is lead-zinc, not copper.")
    g.mt(O, "L3", "Match the mining area with its state:", "Area", "State",
         [("Kudremukh", "Karnataka"), ("Neyveli", "Tamil Nadu"), ("Singareni", "Telangana"), ("Talcher", "Odisha")],
         "Kudremukh iron ore; Neyveli lignite; Singareni coal; Talcher coal.", "Singareni is in Telangana.")
    g.st(O, "L3", "Consider the following statements about ores:",
         [("Bauxite is an ore of copper.", False),
          ("Hematite and magnetite are ores of iron.", True),
          ("Magnetite has a higher iron content than hematite.", True)],
         ["Bauxite is aluminium ore.", "Magnetite (up to ~70% Fe) is the finest iron ore; hematite 50–60%."],
         "Magnetite > hematite in iron content.")
    g.st(O, "L3", "Consider the following statements about coal in India:",
         [("Most of India's coal comes from Gondwana formations.", True),
          ("Tertiary coal occurs in the north-eastern states.", True),
          ("Gondwana coal is geologically younger than Tertiary coal.", False)],
         ["Gondwana (~200 million years) is older than Tertiary (~55 million years)."], "Gondwana is older.")
    g.ar(O, "L3", "Many of India's iron and steel plants are located in the Chota Nagpur plateau region.",
         "The region has iron ore, coking coal, manganese and limestone close to one another.", True, True, True,
         "Proximity of raw materials explains the location.", "Raw-material orientation of heavy industry.")
    g.o("L2", "Jaduguda in Jharkhand is known for mining of:", "Uranium",
        ["Thorium|Kerala monazite", "Mica|Koderma", "Copper|Ghatsila"], "UCIL operates the Jaduguda uranium mine.",
        "Ghatsila nearby is copper.")
    g.o("L2", "The monazite sands of the Kerala coast are an important source of:", "Thorium",
        ["Uranium|Jaduguda", "Gold|placer gold elsewhere", "Bauxite|laterite"], "Monazite is a thorium-bearing mineral.",
        "Thorium, not uranium.")
    g.o("L2", "Mumbai High is:", "An offshore oil field",
        ["An onshore coal field|not coal", "An iron-ore mine in the Konkan|not ore", "A natural gas pipeline hub|not a pipeline"],
        "Mumbai High (discovered 1974) lies off the Maharashtra coast.", "Offshore, not onshore.")
    g.o("L2", "Balaghat district is known for deposits of:", "Manganese",
        ["Bauxite|Amarkantak/Odisha", "Mica|Koderma", "Lignite|Neyveli"], "Balaghat (MP) is a major manganese area.",
        "Manganese is used in steel-making.")
    g.o("L2", "Koderma is known for the production of:", "Mica",
        ["Copper|Khetri", "Coal|Jharia", "Uranium|Jaduguda"], "Koderma (Jharkhand) is a traditional mica belt.", "All are in Jharkhand except Khetri.")

    # ------------------------------------------------------------------ mountains
    g.m("gk-mountain-ranges", "NCERT Class 9 & 11 Geography (Physiography); standard world atlas")
    g.f("L1", "The highest mountain peak in the world is:", "Mount Everest",
        ["K2|second highest", "Kangchenjunga|third highest", "Lhotse|fourth highest"], "Everest (8,848.86 m).", "K2 is second.")
    g.f("L1", "The highest peak of the Western Ghats (and of peninsular India) is:", "Anamudi",
        ["Doddabetta|Nilgiris' highest", "Mahendragiri|Eastern Ghats", "Guru Shikhar|Aravalli"], "Anamudi (2,695 m), Kerala.",
        "Doddabetta is the Nilgiris' highest.")
    g.f("L1", "Guru Shikhar, the highest peak of the Aravalli range, is at:", "Mount Abu",
        ["Nainital|Kumaon hills", "Pachmarhi|Satpura", "Ooty|Nilgiris"], "Guru Shikhar (1,722 m) in Rajasthan.", "Aravalli is in Rajasthan.")
    g.f("L1", "The longest continental mountain range in the world is:", "Andes",
        ["Himalaya|highest, not longest", "Rockies|North America", "Alps|Europe"], "The Andes run about 7,000 km.", "Highest ≠ longest.")
    g.f("L1", "Mount Kilimanjaro, the highest peak of Africa, is in:", "Tanzania",
        ["Kenya|neighbour", "Uganda|Rwenzori", "Ethiopia|Ras Dashen"], "Kilimanjaro (5,895 m) is in Tanzania.", "Close to the Kenya border.")
    g.st(O, "L3", "Consider the following statements about the Himalaya:",
         [("The Greater Himalaya (Himadri) has the lowest average elevation of the three ranges.", False),
          ("The Shiwaliks form the outermost range.", True),
          ("The Lesser Himalaya is also called the Himachal.", True)],
         ["Himadri is the highest (avg ~6,000 m).", "Shiwaliks outermost; Himachal = Lesser Himalaya."], "Himadri is highest.")
    g.mt(O, "L3", "Match the peak with its state:", "Peak", "State",
         [("Kangchenjunga", "Sikkim"), ("Nanda Devi", "Uttarakhand"), ("Saramati", "Nagaland"), ("Dhupgarh", "Madhya Pradesh")],
         "Kangchenjunga—Sikkim; Nanda Devi—Uttarakhand; Saramati—Nagaland; Dhupgarh (Satpura)—MP.", "Dhupgarh is in Pachmarhi, MP.")
    g.mt(O, "L3", "Match the mountain pass with its state:", "Pass", "State",
         [("Shipki La", "Himachal Pradesh"), ("Nathu La", "Sikkim"), ("Bomdi La", "Arunachal Pradesh"), ("Lipulekh", "Uttarakhand")],
         "Shipki La—HP; Nathu La—Sikkim; Bomdi La—Arunachal; Lipulekh—Uttarakhand.", "Lipulekh is the Kailash route pass.")
    g.ar(O, "L3", "The Narmada flows westward through a rift valley.",
         "The Narmada flows between the Vindhya range to its north and the Satpura range to its south.", True, True, False,
         "Both are true, but its westward flow is explained by the rift (faulting), not by the flanking ranges.",
         "Flanking ranges do not set flow direction.")
    g.o("L2", "Which of the following is a block mountain?", "Black Forest",
        ["Himalaya|fold", "Alps|fold", "Rockies|fold"], "The Black Forest (Germany) and Vosges are horsts.", "Young ranges are fold mountains.")
    g.o("L2", "The highest peak of the Nilgiri hills is:", "Doddabetta",
        ["Anamudi|Anaimalai hills", "Mahendragiri|Eastern Ghats", "Mullayanagiri|Karnataka (Chikmagalur)"],
        "Doddabetta (2,637 m) near Ooty.", "Anamudi is in the Anaimalai hills.")
    g.st(O, "L3", "Consider the following statements:",
         [("K2 is the second-highest peak in the world.", True),
          ("K2 lies in the Karakoram range.", True),
          ("Kangchenjunga is the third-highest peak in the world.", True)],
         ["All three are correct."], "All can be true.")
    g.o("L2", "Which of the following is NOT part of the Purvanchal hills?", "Cardamom Hills",
        ["Patkai Bum|Purvanchal", "Naga Hills|Purvanchal", "Mizo Hills|Purvanchal"], "Cardamom Hills are in the south (Kerala–TN).",
        "Purvanchal = eastern hills.")
    g.mt(O, "L3", "Match the mountain range with its continent or location:", "Range", "Location",
         [("Atlas", "North-west Africa"), ("Appalachians", "Eastern North America"), ("Urals", "Europe–Asia boundary"),
          ("Great Dividing Range", "Eastern Australia")],
         "Standard atlas facts.", "Urals mark the Europe–Asia boundary.")
    g.o("L2", "Aconcagua, the highest peak of South America, lies in the:", "Andes, Argentina",
        ["Andes, Peru|wrong country", "Rockies, Chile|wrong range", "Andes, Bolivia|wrong country"],
        "Aconcagua (about 6,961 m) is in Mendoza, Argentina.", "Highest in both Western and Southern Hemispheres.")

    # ------------------------------------------------------------------ rivers of the world
    g.m("gk-rivers-of-the-world", "Standard world atlas; NCERT Class 11 Geography")
    g.f("L1", "The river with the largest discharge of water in the world is the:", "Amazon",
        ["Nile|long but lower discharge", "Congo|second largest discharge", "Yangtze|Asia's longest"],
        "The Amazon carries roughly a fifth of global river discharge to the ocean.", "Length and discharge differ.")
    g.f("L1", "London stands on the river:", "Thames",
        ["Seine|Paris", "Rhine|Germany/Netherlands", "Danube|Vienna/Budapest"], "London is on the Thames.", "Seine is Paris.")
    g.f("L1", "Which river flows through or along the borders of the most countries (ten)?", "Danube",
        ["Nile|about eleven basin countries, not along", "Rhine|six countries", "Amazon|mainly Brazil/Peru/Colombia"],
        "The Danube flows through or borders ten countries, the most for any river.", "Basin countries ≠ countries the channel touches.")
    g.f("L1", "The longest river in Europe is the:", "Volga",
        ["Danube|second longest", "Rhine|shorter", "Dnieper|shorter"], "The Volga (~3,530 km) drains into the Caspian Sea.", "Danube is second.")
    g.f("L1", "The longest river in Asia is the:", "Yangtze",
        ["Yellow River|second in China", "Mekong|Southeast Asia", "Ganga|Indian subcontinent"], "The Yangtze (~6,300 km).",
        "Yellow River (Huang He) is second in China.")
    g.mt(O, "L3", "Match the river with a city on its banks:", "River", "City",
         [("Seine", "Paris"), ("Tigris", "Baghdad"), ("Danube", "Budapest"), ("Hudson", "New York")],
         "Standard pairs.", "Baghdad is on the Tigris, not the Euphrates.")
    g.mt(O, "L3", "Match the river with the water body into which it drains:", "River", "Drains into",
         [("Volga", "Caspian Sea"), ("Nile", "Mediterranean Sea"), ("Mekong", "South China Sea"), ("Amur", "Sea of Okhotsk")],
         "Volga—Caspian; Nile—Mediterranean; Mekong—South China Sea; Amur—Tatar Strait/Sea of Okhotsk.", "Volga is endorheic (Caspian).")
    g.st(O, "L3", "Consider the following statements:",
         [("The Congo crosses the Equator twice.", True),
          ("The Limpopo crosses the Tropic of Capricorn twice.", True),
          ("The Mahi crosses the Tropic of Cancer twice.", True)],
         ["All three are standard 'crosses twice' facts."], "All can be true.")
    g.ar(O, "L3", "The Amazon has the largest discharge of any river.",
         "The Amazon empties into the Atlantic Ocean.", True, True, False,
         "Both are true, but where it drains does not explain its discharge (basin size and rainfall do).", "Equatorial rainfall is year-round.")
    g.o("L2", "The Rio Grande forms part of the boundary between:", "USA and Mexico",
        ["USA and Canada|Great Lakes/49th parallel", "Brazil and Argentina|Iguazu/Uruguay rivers", "Mexico and Guatemala|Usumacinta"],
        "The Rio Grande (Río Bravo) marks much of the US–Mexico border.", "Not a South American river.")
    g.o("L2", "The Victoria Falls lie on the river:", "Zambezi",
        ["Congo|Boyoma Falls", "Nile|Murchison Falls", "Limpopo|no major falls"], "Victoria Falls on the Zambia–Zimbabwe border.",
        "Zambezi flows into the Indian Ocean.")
    g.st(O, "L3", "Consider the following statements about the Brahmaputra:",
         [("In Tibet it is known as the Yarlung Tsangpo.", True),
          ("In Bangladesh it is known as the Meghna before it meets the Ganga.", False),
          ("It enters India in Arunachal Pradesh, where it is called the Siang or Dihang.", True)],
         ["Tsangpo in Tibet; Siang/Dihang in Arunachal.", "In Bangladesh it is the Jamuna; the combined flow later becomes the Meghna."],
         "Jamuna (Bangladesh) ≠ Yamuna (India).", ref="NCERT Class 11 Geography (India—Physical Environment)")
    g.o("L2", "The Mekong does NOT flow through which of the following?", "Malaysia",
        ["Laos|on the Mekong", "Cambodia|on the Mekong", "Vietnam|delta"], "Mekong: China, Myanmar, Laos, Thailand, Cambodia, Vietnam.",
        "Malaysia is not on the Mekong.")
    g.o("L2", "The port of Rotterdam lies near the mouth of the:", "Rhine",
        ["Seine|Le Havre", "Elbe|Hamburg", "Thames|London"], "Rotterdam sits in the Rhine–Meuse delta.", "Hamburg is Elbe.")
    g.o("L2", "Which of the following rivers flows into the Arctic Ocean?", "Lena",
        ["Amur|Pacific", "Volga|Caspian", "Mekong|South China Sea"], "Siberian rivers Ob, Yenisei and Lena drain north to the Arctic.",
        "Amur drains to the Pacific side.")

    # ------------------------------------------------------------------ transport
    g.m("gk-transport-corridors", "NCERT Class 10/12 Geography (Transport); Ministry of Ports/Railways official descriptions")
    g.f("L1", "Jawaharlal Nehru Port (Nhava Sheva) is located near:", "Mumbai",
        ["Chennai|Chennai port", "Kochi|Cochin port", "Visakhapatnam|Vizag port"], "JNPA is in Navi Mumbai, Maharashtra.",
        "India's busiest container port.")
    g.f("L1", "Kandla Port, renamed Deendayal Port, is in:", "Gujarat",
        ["Maharashtra|JNPA/Mumbai", "Goa|Mormugao", "Karnataka|New Mangalore"], "Kandla/Deendayal is on the Gulf of Kutch.",
        "Tidal port in Gujarat.")
    g.f("L1", "The Golden Quadrilateral highway network connects:", "Delhi, Mumbai, Chennai and Kolkata",
        ["Delhi, Mumbai, Bengaluru and Kolkata|Bengaluru is en route, not a corner",
         "Srinagar, Kanyakumari, Silchar and Porbandar|that is the NS-EW corridor",
         "Delhi, Mumbai, Chennai and Hyderabad|Hyderabad not a corner"],
        "The four metros form the corners of the quadrilateral.", "NS–EW corridor has different termini.")
    g.f("L1", "The Konkan Railway passes through which set of states?", "Maharashtra, Goa and Karnataka",
        ["Gujarat, Maharashtra and Goa|Gujarat not included", "Goa, Karnataka and Kerala|Kerala not included",
         "Maharashtra, Karnataka and Kerala|Goa missing"], "It runs from Roha (Maharashtra) to Thokur (Karnataka) via Goa.",
        "It does not reach Kerala or Gujarat.")
    g.f("L1", "The Suez Canal connects the:", "Mediterranean Sea and Red Sea",
        ["Atlantic and Pacific Oceans|Panama Canal", "Black Sea and Mediterranean|Bosporus/Dardanelles",
         "Red Sea and Arabian Sea|Bab-el-Mandeb"], "Opened 1869, Egypt.", "Panama links Atlantic–Pacific.")
    g.st(O, "L3", "Consider the following statements about Dedicated Freight Corridors:",
         [("The Eastern DFC connects Punjab with Tamil Nadu.", False),
          ("The Western DFC terminates at Jawaharlal Nehru Port.", True),
          ("DFCCIL is a public sector undertaking under the Ministry of Railways.", True)],
         ["Eastern DFC: Ludhiana (Sahnewal) to Sonnagar, Bihar.", "Western DFC: Dadri to JNPT.", "DFCCIL is a Railways PSU."],
         "Eastern DFC runs to Bihar, not south India.")
    g.mt(O, "L3", "Match the port with its state:", "Port", "State",
         [("Paradip", "Odisha"), ("Kamarajar (Ennore)", "Tamil Nadu"), ("Mormugao", "Goa"), ("New Mangalore", "Karnataka")],
         "Direct locational facts.", "Mormugao is Goa's major port.")
    g.ar(O, "L3", "The Panama Canal uses a system of locks.",
         "Gatun Lake, part of the canal route, lies about 26 m above sea level, so ships must be raised and lowered.",
         True, True, True, "Elevation difference requires locks; Suez is a sea-level canal.", "Suez has no locks.")
    g.o("L2", "The Sagarmala programme primarily aims at:", "Port-led development",
        ["Building rural roads|PMGSY", "Inland air connectivity|UDAN", "Expanding national highways|Bharatmala"],
        "Sagarmala (Ministry of Ports, Shipping and Waterways, 2015) promotes port modernisation and connectivity.",
        "Bharatmala is highways.")
    g.mt(O, "L3", "Match the National Waterway with its river system:", "Waterway", "River system",
         [("NW-1", "Ganga–Bhagirathi–Hooghly"), ("NW-2", "Brahmaputra"), ("NW-3", "West Coast Canal, Kerala"),
          ("NW-4", "Krishna–Godavari canals")],
         "NW-1 Prayagraj–Haldia; NW-2 Dhubri–Sadiya; NW-3 Kollam–Kottapuram; NW-4 Godavari/Krishna with canals.",
         "NW-2 is the Brahmaputra in Assam.")
    g.o("L2", "Which major port of India is a riverine port?", "Kolkata",
        ["Mumbai|natural harbour", "Visakhapatnam|landlocked harbour", "Chennai|artificial harbour"],
        "Syama Prasad Mookerjee Port, Kolkata, is on the Hooghly.", "Haldia is its dock complex.")
    g.o("L2", "The International North–South Transport Corridor links India with Russia through:", "Iran",
        ["Pakistan|no transit", "Afghanistan|landlocked", "China|different corridor"],
        "INSTC (agreement 2000: India, Iran, Russia) is a multimodal ship-rail-road route.", "Iran is the transit hub.",
        ref="INSTC agreement (2000)")
    g.o("L2", "The deepest landlocked and protected port of India is:", "Visakhapatnam",
        ["Kochi|natural harbour", "Paradip|Odisha", "Tuticorin|Tamil Nadu"], "Vizag is described as India's deepest landlocked port.",
        "Landlocked harbour = protected by land.", ref="NCERT Class 12 Geography (India—People and Economy)")
    g.o("L2", "The Grand Trunk Road was extensively rebuilt in the 16th century by:", "Sher Shah Suri",
        ["Akbar|expanded postal system", "Babur|founded Mughal rule", "Muhammad bin Tughlaq|moved capital"],
        "Sher Shah rebuilt the road with sarais from Sonargaon to Peshawar.", "Mughals used, not rebuilt, it.")
    g.o("L2", "Chabahar port, in whose development India is involved, is located in:", "Iran",
        ["Pakistan|Gwadar", "Oman|Duqm", "Afghanistan|landlocked"], "Chabahar is on the Gulf of Oman in Sistan-Baluchestan, Iran.",
        "Gwadar is Pakistan.")

    # ------------------------------------------------------------------ world heritage
    g.m("gk-world-heritage", "UNESCO World Heritage List; Ramsar Convention records")
    g.f("L1", "UNESCO is headquartered in:", "Paris",
        ["Geneva|many UN bodies", "New York|UN HQ", "Rome|FAO"], "UNESCO HQ: Paris.", "Geneva hosts WHO/ILO.")
    g.f("L1", "Which of the following is a natural World Heritage Site in India?", "Kaziranga National Park",
        ["Ajanta Caves|cultural", "Group of Monuments at Hampi|cultural", "Khajuraho Group of Monuments|cultural"],
        "Kaziranga (1985) is inscribed under natural criteria.", "Temples and caves are cultural.")
    g.f("L1", "The Ajanta Caves are located in:", "Maharashtra",
        ["Madhya Pradesh|Bhimbetka", "Karnataka|Badami", "Odisha|Udayagiri"], "Ajanta (Chhatrapati Sambhajinagar district).",
        "Ellora is nearby, also Maharashtra.")
    g.f("L1", "Hampi, a World Heritage Site, was the capital of the:", "Vijayanagara Empire",
        ["Chola Empire|Thanjavur", "Rashtrakuta dynasty|Manyakheta", "Bahmani Sultanate|Gulbarga/Bidar"],
        "Hampi (Karnataka) was Vijayanagara's capital.", "Bahmani were rivals.")
    g.f("L1", "The Sundarbans National Park is known for:", "Mangrove forests",
        ["Alpine meadows|Valley of Flowers", "Coral reefs|Gulf of Mannar", "Desert dunes|Thar"],
        "Largest mangrove forest; home of the Royal Bengal tiger.", "Mangroves grow in tidal deltas.")
    g.o("L2", "India's only 'mixed' World Heritage Site (natural and cultural) is:", "Khangchendzonga National Park",
        ["Great Himalayan National Park|natural", "Western Ghats|natural", "Sundarbans National Park|natural"],
        "Khangchendzonga (Sikkim) was inscribed in 2016 as a mixed site.", "Others are purely natural.")
    g.o("L2", "The World Heritage Convention was adopted by UNESCO in:", "1972",
        ["1945|UNESCO founding", "1971|Ramsar Convention", "1992|Rio Earth Summit"], "Adopted in Paris, 1972.",
        "1971 is Ramsar.", kind="numerical")
    g.mt(O, "L3", "Match the World Heritage Site with its state:", "Site", "State",
         [("Rani-ki-Vav", "Gujarat"), ("Great Living Chola Temples", "Tamil Nadu"), ("Pattadakal", "Karnataka"),
          ("Rock Shelters of Bhimbetka", "Madhya Pradesh")],
         "Rani-ki-Vav (Patan); Chola temples; Pattadakal (Chalukya); Bhimbetka.", "Pattadakal is Karnataka.")
    g.st(O, "L3", "Consider the following statements about World Heritage Sites in India:",
         [("Dholavira, a Harappan city, is in Gujarat.", True),
          ("Santiniketan is in Odisha.", False),
          ("Ramappa (Rudreswara) Temple is in Telangana.", True)],
         ["Dholavira (2021) Gujarat; Ramappa (2021) Telangana.", "Santiniketan (2023) is in West Bengal."],
         "Santiniketan is Tagore's West Bengal.")
    g.mt(O, "L3", "Match the natural World Heritage Site with its state:", "Site", "State",
         [("Great Himalayan National Park", "Himachal Pradesh"), ("Manas Wildlife Sanctuary", "Assam"),
          ("Keoladeo National Park", "Rajasthan"), ("Valley of Flowers", "Uttarakhand")],
         "GHNP—Kullu, HP; Manas—Assam; Keoladeo—Bharatpur; Valley of Flowers—Chamoli.", "Keoladeo is Rajasthan's bird park.")
    g.o("L2", "India's first Ramsar sites, designated in 1981, were:", "Chilika Lake and Keoladeo",
        ["Wular Lake and Loktak|later sites", "Sambhar Lake and Chilika|Sambhar later", "Loktak and Keoladeo|Loktak 1990"],
        "Chilika (Odisha) and Keoladeo (Rajasthan) were designated in 1981.", "Loktak came in 1990.")
    g.st(O, "L3", "Consider the following statements:",
         [("The Montreux Record lists Ramsar sites where changes in ecological character have occurred or are likely.", True),
          ("Chilika Lake was removed from the Montreux Record.", True),
          ("The Ramsar Convention was signed in the city of Ramsar in Iran.", True)],
         ["Montreux Record—threatened Ramsar sites.", "Chilika removed in 2002.", "Ramsar, Iran, 1971."], "All three are true.")
    g.ar(O, "L3", "Kaziranga National Park is inscribed as a natural World Heritage Site.",
         "Kaziranga is famous chiefly for its population of Asiatic lions.", True, False, False,
         "Kaziranga is known for one-horned rhinos; lions are in Gir.", "Rhino, not lion.")
    g.o("L2", "Which of these is NOT part of the 'Mountain Railways of India' World Heritage property?", "Matheran Hill Railway",
        ["Darjeeling Himalayan Railway|included", "Nilgiri Mountain Railway|included", "Kalka–Shimla Railway|included"],
        "The property includes DHR (1999), NMR (2005) and Kalka–Shimla (2008).", "Matheran is only on the tentative list.")
    g.o("L2", "The Moidams, inscribed as a World Heritage Site in 2024, are burial mounds of the:", "Ahom dynasty",
        ["Chola dynasty|Tamil Nadu", "Koch dynasty|Cooch Behar", "Pala dynasty|Bengal"],
        "The Moidams of Charaideo, Assam, are royal Ahom mound burials.", "First NE cultural site.")
