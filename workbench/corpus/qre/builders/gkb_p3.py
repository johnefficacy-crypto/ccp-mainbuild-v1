"""QRE-GK-B part 3: Indian Economy — schemes, missions and institutions (8 microtopics).
Only durable facts: launch year, ministry, objective, stable design features. No current figures or moving targets."""


def add_all(g):
    F, O = "foundation", "officer"

    # ------------------------------------------------------------------ agriculture & rural energy schemes
    g.m("gk-agriculture-and-rural-energy", "Scheme guidelines — Ministry of Agriculture & Farmers Welfare / MNRE / MoPNG / Ministry of Power (PIB releases)")
    g.f("L1", "Under PM-KISAN, eligible farmer families receive income support of ₹6,000 a year paid in:",
        "Three equal instalments",
        ["Two equal instalments|miscounts instalments", "Twelve monthly instalments|confuses with pension schemes",
         "One annual lump sum|ignores instalment design"],
        "PM-KISAN (2019) pays ₹6,000 a year in three instalments of ₹2,000 by direct benefit transfer.",
        "₹2,000 × 3 = ₹6,000.")
    g.f("L1", "The Soil Health Card scheme was launched in:", "2015",
        ["2014|Jan Dhan year", "2016|PMFBY year", "2019|PM-KISAN year"],
        "Launched on 19 February 2015 at Suratgarh, Rajasthan.", "Several farm schemes cluster in 2015–16.", kind="numerical")
    g.f("L1", "Under PMFBY, the maximum premium payable by farmers for kharif food and oilseed crops is:", "2% of the sum insured",
        ["1.5% of the sum insured|rabi rate", "5% of the sum insured|commercial/horticultural rate",
         "10% of the sum insured|invented rate"],
        "PMFBY (2016): 2% kharif, 1.5% rabi, 5% annual commercial/horticultural crops.", "1.5% is for rabi.")
    g.f("L1", "PM-KUSUM, for solar pumps and solar power on farms, is implemented by the:",
        "Ministry of New and Renewable Energy",
        ["Ministry of Power|DDUGJY/Saubhagya", "Ministry of Agriculture and Farmers Welfare|beneficiary sector, not nodal",
         "Ministry of Jal Shakti|water ministry"],
        "PM-KUSUM (2019) is an MNRE scheme.", "Farm-related but energy-ministry run.")
    g.f("L1", "The Saubhagya scheme (2017) aimed at:", "Universal household electrification",
        ["Free LPG connections to poor women|Ujjwala", "Solar pumps for farmers|PM-KUSUM", "Separating farm and village power feeders|DDUGJY component"],
        "Pradhan Mantri Sahaj Bijli Har Ghar Yojana targeted last-mile household connections.", "Ujjwala is LPG.")
    g.st(O, "L3", "Consider the following statements about the Pradhan Mantri Fasal Bima Yojana:",
         [("It replaced the PM-KISAN scheme.", False),
          ("The farmer's premium for rabi food and oilseed crops is 1.5%.", True),
          ("The farmer's premium for annual commercial and horticultural crops is 5%.", True)],
         ["PMFBY replaced NAIS and modified NAIS, not PM-KISAN.", "Premium caps: 2% kharif, 1.5% rabi, 5% commercial."],
         "PM-KISAN is income support, still running.")
    g.mt(O, "L3", "Match the scheme with its nodal ministry:", "Scheme", "Ministry",
         [("Soil Health Card", "Agriculture and Farmers Welfare"), ("PM Ujjwala Yojana", "Petroleum and Natural Gas"),
          ("Deendayal Upadhyaya Gram Jyoti Yojana", "Power"), ("PM-KUSUM", "New and Renewable Energy")],
         "SHC—MoA&FW; PMUY—MoPNG; DDUGJY—Power; PM-KUSUM—MNRE.", "Ujjwala is LPG, hence petroleum ministry.")
    g.o("L2", "Under the Pradhan Mantri Ujjwala Yojana (2016), LPG connections are released in the name of:",
        "An adult woman of a poor household",
        ["The male head of the household|scheme targets women", "The gram panchayat|not individual",
         "Any adult member of the household|ignores the women-centric design"],
        "PMUY aims to replace unclean cooking fuels and is women-centric.", "Connection in the woman's name.")
    g.o("L2", "'Per Drop More Crop' is a component of which scheme?", "Pradhan Mantri Krishi Sinchayee Yojana",
        ["Pradhan Mantri Fasal Bima Yojana|insurance", "Paramparagat Krishi Vikas Yojana (organic)|organic farming",
         "Rashtriya Krishi Vikas Yojana – RAFTAAR|state-plan flexibility scheme"],
        "PMKSY (2015) — 'Har Khet Ko Pani' and micro-irrigation under 'Per Drop More Crop'.", "Irrigation, not insurance.")
    g.st(O, "L3", "Consider the following statements about e-NAM:",
         [("It is a pan-India electronic trading portal linking regulated APMC mandis.", True),
          ("It was launched in 2020.", False),
          ("The Small Farmers' Agribusiness Consortium is its lead implementing agency.", True)],
         ["e-NAM was launched on 14 April 2016.", "SFAC implements it under MoA&FW."], "2016, not 2020.")
    g.o("L2", "The Kisan Credit Card scheme was introduced in:", "1998",
        ["2004|random", "2014|Jan Dhan era", "1992|SHG-bank linkage year"],
        "KCC was introduced in 1998 (NABARD model scheme).", "1992 is SHG-BLP.", kind="numerical",
        ref="NABARD / RBI Master Circular on KCC")
    g.o("L2", "GOBARdhan, launched in 2018, is associated with:", "Turning cattle dung and bio-waste into biogas",
        ["Distributing high-yielding indigenous cattle breeds|Rashtriya Gokul Mission", "Insuring livestock against death|livestock insurance",
         "Setting up bulk milk-chilling centres in villages|dairy infrastructure"],
        "GOBARdhan (under Swachh Bharat Mission–Grameen) promotes biogas/CBG and organic manure.", "Not a cattle-breeding scheme.")
    g.ar(O, "L3", "Neem-coating was made mandatory for all domestically produced urea from 2015.",
         "Neem coating slows nitrogen release and discourages diversion of subsidised urea to industrial use.",
         True, True, True, "Both efficiency and anti-diversion benefits explain the policy.", "Neem coating ≠ nano urea.",
         ref="Department of Fertilizers notifications, 2015")
    g.o("L3", "The Agriculture Infrastructure Fund (2020) provides interest subvention of:", "3% a year on loans up to ₹2 crore",
        ["5% a year on loans up to ₹5 crore|inflated figures", "2% a year on loans up to ₹1 crore|understated figures",
         "Full interest waiver on all loans|not the design"],
        "AIF is a medium-long term financing facility with 3% subvention and CGTMSE guarantee on loans up to ₹2 crore.",
        "₹1 lakh crore is the fund size, not the loan cap.")
    g.o("L2", "Paramparagat Krishi Vikas Yojana (2015) promotes:", "Cluster-based organic farming",
        ["Crop insurance|PMFBY", "Micro-irrigation|PMKSY", "Farm mechanisation subsidies|SMAM"],
        "PKVY supports organic farming through farmer clusters and PGS certification.", "Organic, via clusters.")

    # ------------------------------------------------------------------ biofuel & renewable energy
    g.m("gk-biofuel-and-renewable", "National Policy on Biofuels 2018 (amended 2022); MNRE / MoPNG official descriptions")
    g.f("L1", "The nodal ministry for renewable energy in India is the:", "Ministry of New and Renewable Energy",
        ["Ministry of Power|conventional power", "Ministry of Petroleum and Natural Gas|oil and gas",
         "Ministry of Environment, Forest and Climate Change|environment"],
        "MNRE handles solar, wind, bioenergy, green hydrogen and related programmes.", "Ethanol blending is MoPNG, but RE overall is MNRE.")
    g.f("L1", "Under India's ethanol blending programme, ethanol is blended with:", "Petrol",
        ["Diesel|biodiesel blending", "Kerosene|not blended", "Aviation turbine fuel|SAF, separate"],
        "The Ethanol Blended Petrol (EBP) programme blends ethanol in petrol.", "Biodiesel goes with diesel.")
    g.f("L1", "The Bhadla Solar Park is located in:", "Rajasthan",
        ["Gujarat|Charanka", "Karnataka|Pavagada", "Madhya Pradesh|Rewa"], "Bhadla is in Jodhpur district, Rajasthan.",
        "Each state has a flagship solar park.")
    g.f("L1", "The headquarters of the International Solar Alliance is in:", "Gurugram, India",
        ["Paris, France|ISA launched at COP21 in Paris", "Abu Dhabi, UAE|IRENA HQ", "Geneva, Switzerland|many UN bodies"],
        "ISA HQ is at Gwal Pahari, Gurugram.", "IRENA is in Abu Dhabi.")
    g.f("L1", "Jatropha is promoted in India as a source of:", "Biodiesel",
        ["Ethanol|from sugarcane/grains", "Natural rubber|Hevea", "Edible oil|non-edible seed"],
        "Jatropha curcas seeds yield non-edible oil used for biodiesel.", "Non-edible oilseed.")
    g.st(O, "L3", "Consider the following statements about the National Policy on Biofuels:",
         [("It was adopted in 2018.", True),
          ("It permits ethanol production only from sugarcane juice.", False),
          ("The 2022 amendment advanced the 20% ethanol-blending target to ethanol supply year 2025–26.", True)],
         ["2018 policy; 2022 amendment brought E20 forward from 2030.", "Feedstocks include B-heavy molasses, damaged grains, maize, etc."],
         "Feedstock widening was central to the policy.")
    g.o("L2", "Second-generation (2G) ethanol is produced mainly from:", "Crop residues such as rice straw",
        ["Sugarcane juice|1G feedstock", "Edible vegetable oils like palm oil|biodiesel, not ethanol", "Algae grown in open ponds or bioreactors|3G feedstock"],
        "2G ethanol uses lignocellulosic biomass — crop residue, stalks, bagasse.", "1G = sugar/starch; 3G = algae.")
    g.mt(O, "L3", "Match the renewable energy project with its state:", "Project", "State",
         [("Pavagada Solar Park", "Karnataka"), ("Kurnool Ultra Mega Solar Park", "Andhra Pradesh"),
          ("Rewa Ultra Mega Solar", "Madhya Pradesh"), ("Muppandal Wind Farm", "Tamil Nadu")],
         "Pavagada (Tumakuru); Kurnool (AP); Rewa (MP); Muppandal (Kanyakumari).", "Muppandal is a wind, not solar, site.")
    g.ar(O, "L3", "Green hydrogen is produced by electrolysis of water using renewable electricity.",
         "Grey hydrogen is produced from natural gas by steam methane reforming without carbon capture.",
         True, True, False, "Both are correct definitions, but R describes a different pathway and does not explain A.",
         "Colour labels describe production routes.")
    g.o("L2", "The National Green Hydrogen Mission was approved by the Union Cabinet in:", "2023",
        ["2021|announced on Independence Day, approved later", "2019|random", "2025|random"],
        "Approved in January 2023; MNRE is the nodal ministry.", "Announcement (2021) vs approval (2023).", kind="numerical")
    g.o("L2", "The SATAT initiative (2018) promotes:", "Compressed biogas as vehicle fuel",
        ["Rooftop solar panels for households|PM Surya Ghar", "Ethanol distilleries using surplus grains|EBP programme", "Offshore wind farms|offshore wind policy"],
        "SATAT (MoPNG) invites entrepreneurs to set up CBG plants with offtake by oil companies.", "CBG, not ethanol.")
    g.o("L2", "PM JI-VAN Yojana (2019) provides viability support for:", "Integrated 2G bioethanol projects",
        ["Solar pumps on farms|PM-KUSUM", "Family-size household biogas plants|biogas programme", "Subsidy on electric vehicle purchase|FAME"],
        "Pradhan Mantri JI-VAN supports commercial and demonstration 2G ethanol plants.", "JI-VAN is about bio-ethanol.")
    g.o("L2", "PM Surya Ghar: Muft Bijli Yojana (2024) is focused on:", "Rooftop solar for homes",
        ["Utility-scale solar parks for industry|solar park scheme", "Solar pumps for farmers|PM-KUSUM", "Solar street-lighting in village lanes|different scheme"],
        "The scheme gives central financial assistance for household rooftop solar (MNRE).", "Households, not farms.")
    g.st(O, "L3", "Consider the following statements about the International Solar Alliance:",
         [("It was launched by India and France at COP21 in Paris in 2015.", True),
          ("Its membership is open only to countries lying between the Tropics.", False),
          ("Its headquarters is in India.", True)],
         ["Launched 2015 at COP21.", "A 2020 amendment opened membership to all UN member states.", "HQ Gurugram."],
         "The tropics-only restriction was removed.", ref="ISA Framework Agreement (as amended)")
    g.o("L2", "Puga Valley in Ladakh is known for its potential in:", "Geothermal energy",
        ["Tidal energy|coastal", "Wind energy|Tamil Nadu/Gujarat", "Offshore oil|Mumbai High"],
        "Hot springs at Puga make it India's best-known geothermal site.", "Ladakh has no coast.")

    # ------------------------------------------------------------------ environmental clearance
    g.m("gk-environmental-clearance", "Environment (Protection) Act 1986; EIA Notification 2006; NGT Act 2010; MoEFCC / CPCB")
    g.f("L1", "The Environment (Protection) Act was enacted in:", "1986",
        ["1974|Water Act", "1981|Air Act", "1972|Wildlife Act"], "Enacted after the Bhopal gas tragedy.", "Water 1974, Air 1981.",
        kind="numerical")
    g.f("L1", "The EIA Notification currently in force was issued in:", "2006",
        ["1994|first EIA notification", "1986|EP Act year", "2020|draft notification"],
        "EIA Notification 2006 replaced the 1994 notification.", "2020 was only a draft.", kind="numerical")
    g.f("L1", "The Central Pollution Control Board was first constituted under the:", "Water Act, 1974",
        ["Air Act, 1981|later entrusted functions", "Environment (Protection) Act, 1986|later law",
         "Factories Act, 1948|labour law"],
        "CPCB was constituted in 1974 under the Water (Prevention and Control of Pollution) Act.", "Air Act functions were added later.")
    g.f("L1", "PARIVESH is a single-window portal for:", "Environment and forest clearances",
        ["Company incorporation and annual filings|MCA21", "Filing income-tax returns and refunds|e-filing", "GST registration|GSTN"],
        "PARIVESH (MoEFCC, 2018) handles environment, forest, wildlife and CRZ clearances.", "MoEFCC portal.")
    g.f("L1", "The National Green Tribunal was established in:", "2010",
        ["2006|EIA notification year", "2002|Biodiversity Act year", "1986|EP Act year"], "Under the NGT Act, 2010.",
        "NGT is a specialised court.", kind="numerical")
    g.st(O, "L3", "Consider the following statements about the EIA Notification, 2006:",
         [("Category A projects are appraised at the central level.", True),
          ("Public consultation is mandatory for all Category B2 projects.", False),
          ("Category B projects are appraised by State-level authorities (SEIAA).", True)],
         ["Category A: MoEFCC/EAC; Category B: SEIAA/SEAC.", "B2 projects need neither EIA report nor public consultation."],
         "B2 is the lighter track.")
    g.o("L3", "The correct sequence of stages under the EIA Notification, 2006 for a project requiring EIA is:",
        "Screening, scoping, public consultation, appraisal",
        ["Scoping, screening, appraisal, public consultation|reverses first and last pairs",
         "Screening, public consultation, scoping, appraisal|consultation before scoping",
         "Public consultation, screening, scoping, appraisal|consultation first"],
        "Four stages in order: screening (B1/B2), scoping (ToR), public consultation, appraisal.", "Scoping fixes the ToR before consultation.")
    g.o("L2", "Coastal Regulation Zone notifications are issued under the:", "Environment (Protection) Act, 1986",
        ["Indian Ports Act, 1908|ports law", "Forest (Conservation) Act, 1980|forest law", "Biological Diversity Act, 2002|biodiversity law"],
        "CRZ notifications (1991, 2011, 2019) are made under the EP Act.", "Ports law does not regulate the CRZ.")
    g.st(O, "L3", "Consider the following statements about forest clearance:",
         [("The Forest (Conservation) Act was enacted in 1980.", True),
          ("It requires prior approval of the Central Government for using forest land for non-forest purposes.", True),
          ("A 2023 amendment renamed it the Van (Sanrakshan Evam Samvardhan) Adhiniyam.", True)],
         ["All three are correct."], "All can be true.", ref="Forest (Conservation) Act, 1980 as amended in 2023")
    g.o("L2", "Which of the following is NOT a zonal bench of the National Green Tribunal?", "Hyderabad",
        ["Bhopal|zonal bench", "Pune|zonal bench", "Kolkata|zonal bench"],
        "Principal bench New Delhi; zonal benches Bhopal, Pune, Kolkata and Chennai.", "No bench at Hyderabad.")
    g.ar(O, "L3", "The 'polluter pays' principle is applied by the National Green Tribunal.",
         "The NGT Act requires the Tribunal to apply the principles of sustainable development, precaution and polluter pays.",
         True, True, True, "Section 20 of the NGT Act mandates these principles.", "It is statutory, not only judicial.",
         ref="National Green Tribunal Act, 2010, s. 20")
    g.o("L2", "Consent to Establish and Consent to Operate for industries are granted by:", "State Pollution Control Boards",
        ["Ministry of Environment, Forest and Climate Change|grants EC, not consents", "National Green Tribunal|adjudicates",
         "District Collector|revenue authority"],
        "SPCBs grant consents under the Water and Air Acts.", "Environmental clearance ≠ consent to operate.")
    g.o("L3", "Under the CPCB categorisation of industries (2016), which category does NOT require Consent to Operate?", "White",
        ["Green|low pollution, still needs consent", "Orange|moderate pollution", "Red|high pollution"],
        "White-category (practically non-polluting) units only need intimation.", "Green still needs consent.")
    g.mt(O, "L3", "Match the Act with its year of enactment:", "Act", "Year",
         [("Water (Prevention and Control of Pollution) Act", "1974"), ("Air (Prevention and Control of Pollution) Act", "1981"),
          ("Environment (Protection) Act", "1986"), ("Biological Diversity Act", "2002")],
         "Water 1974; Air 1981; EP 1986; BD 2002.", "Air (1981) comes after Water (1974).")
    g.o("L2", "The National Single Window System for investor approvals was launched in 2021 by:",
        "DPIIT, Ministry of Commerce and Industry",
        ["Ministry of Environment, Forest and Climate Change|runs PARIVESH", "Ministry of Corporate Affairs|runs MCA21",
         "Reserve Bank of India|financial regulator"],
        "NSWS (with Invest India) is a DPIIT initiative.", "PARIVESH is the environment single window.")

    # ------------------------------------------------------------------ multilateral development finance
    g.m("gk-multilateral-development", "Articles of Agreement / official sites of World Bank Group, ADB, AIIB, NDB")
    g.f("L1", "The headquarters of the World Bank is in:", "Washington, D.C.",
        ["New York|UN HQ", "Geneva|WTO", "Manila|ADB"], "World Bank HQ: Washington, D.C.", "IMF is also in Washington.")
    g.f("L1", "The Asian Development Bank is headquartered in:", "Manila",
        ["Beijing|AIIB", "Tokyo|largest shareholder's capital", "Shanghai|NDB"], "ADB HQ: Manila, Philippines.", "Japan is a major shareholder.")
    g.f("L1", "The Asian Infrastructure Investment Bank is headquartered in:", "Beijing",
        ["Shanghai|NDB", "Manila|ADB", "Singapore|no MDB HQ"], "AIIB HQ: Beijing.", "Shanghai hosts the BRICS bank.")
    g.f("L1", "The New Development Bank (BRICS bank) is headquartered in:", "Shanghai",
        ["Beijing|AIIB", "Moscow|BRICS member capital", "New Delhi|BRICS member capital"], "NDB HQ: Shanghai.", "Beijing is AIIB.")
    g.f("L1", "The IMF and the World Bank were conceived at the Bretton Woods Conference held in:", "1944",
        ["1945|UN founding", "1947|GATT signing", "1950|random"], "July 1944, New Hampshire, USA.", "1945 is the UN.",
        kind="numerical")
    g.mt(O, "L3", "Match the World Bank Group institution with its main function:", "Institution", "Function",
         [("IBRD", "Loans to middle-income countries"), ("IDA", "Concessional finance to the poorest countries"),
          ("IFC", "Investment in the private sector"), ("MIGA", "Political-risk insurance and guarantees")],
         "IBRD market-based loans; IDA soft credits/grants; IFC private sector; MIGA guarantees.", "IFC lends to firms, not governments.")
    g.st(O, "L3", "Consider the following statements:",
         [("India is a founding member of the IBRD.", True),
          ("India is not a member of the Asian Development Bank.", False),
          ("India is a founding member of the AIIB.", True)],
         ["India was an original IBRD member (1944–45).", "India is a founding ADB member (1966).", "India is a founding AIIB member."],
         "India is a borrower in both ADB and AIIB.")
    g.o("L2", "The agreement establishing the New Development Bank was signed at the BRICS summit held in 2014 at:", "Fortaleza",
        ["Durban|2013 summit", "Ufa|2015 summit", "Goa|2016 summit"], "The Fortaleza Declaration (2014) created the NDB.",
        "Operations began in 2015.")
    g.o("L2", "After China, the second-largest shareholder in the AIIB is:", "India",
        ["Russia|third largest", "Germany|largest non-regional", "Japan|not a member"], "India holds the second-largest share.",
        "Japan and the USA are not members.")
    g.o("L3", "India graduated from IDA (concessional) lending at the end of fiscal year:", "2014",
        ["2004|too early", "2010|too early", "2020|too late"],
        "India's income crossed the IDA threshold; it graduated at the end of FY2014.", "India remains an IBRD borrower.",
        kind="numerical")
    g.o("L2", "India is NOT a member of which World Bank Group institution?", "ICSID",
        ["MIGA|India is a member", "IFC|India is a member", "IDA|India is a member"],
        "India has not signed the ICSID Convention on investment dispute settlement.", "India joined MIGA in 1994.")
    g.ar(O, "L3", "IDA credits carry zero or very low interest and long maturities.",
         "IDA is funded largely by contributions from donor member governments rather than market borrowing.", True, True, True,
         "Donor funding allows concessional terms; R explains A.", "IBRD borrows in markets, so it charges more.")
    g.o("L2", "The Asian Development Bank was established in:", "1966",
        ["1956|IFC year", "1960|IDA year", "1976|random"], "ADB began in 1966.", "IDA is 1960.", kind="numerical")
    g.mt(O, "L3", "Match the development institution with its headquarters:", "Institution", "Headquarters",
         [("IFAD", "Rome"), ("EBRD", "London"), ("African Development Bank", "Abidjan"), ("Islamic Development Bank", "Jeddah")],
         "IFAD—Rome; EBRD—London; AfDB—Abidjan; IsDB—Jeddah.", "India joined the EBRD in 2018.")
    g.ar(O, "L3", "JICA loans for projects such as the Delhi Metro are a form of multilateral development finance.",
         "JICA is the Japanese government's agency for official development assistance.", False, True, False,
         "JICA finance is bilateral (Japan–India), not multilateral; R is true.", "Multilateral = many shareholder countries.")

    # ------------------------------------------------------------------ rural livelihood & skill missions
    g.m("gk-rural-livelihood", "MGNREGA 2005 (repealed w.e.f. 1 July 2026 by the VB-G RAM G Act, 2025); MoRD / MSDE / MSME scheme guidelines (PIB)")
    g.f("L1", "DAY-NRLM (Aajeevika) was launched by the Ministry of Rural Development in:", "2011",
        ["2005|MGNREGA year", "2015|Skill India year", "1999|SGSY year"], "NRLM launched June 2011; renamed DAY-NRLM in 2015.",
        "It replaced SGSY (1999).", kind="numerical")
    g.f("L1", "Under MGNREGA, 2005 (in force until 30 June 2026), each rural household was guaranteed at least how many days of wage employment in a financial year?", "100",
        ["125|guarantee under the VB-G RAM G Act, 2025, which replaced MGNREGA", "150|extra days in some cases, not the guarantee",
         "200|invented"],
        ["MGNREGA, s. 3 guaranteed 100 days per household per financial year.",
         "The Viksit Bharat–Guarantee for Rozgar and Ajeevika Mission (Gramin) Act, 2025 repealed MGNREGA w.e.f. 1 July 2026 and guarantees 125 days."],
        "The question asks about MGNREGA (100), not the 2025 Act (125); per household, not per person.", kind="numerical",
        ref="MGNREGA 2005, s. 3 (repealed w.e.f. 1 July 2026); VB-G RAM G Act, 2025")
    g.f("L1", "Pradhan Mantri Kaushal Vikas Yojana is the flagship scheme of the:", "Ministry of Skill Development and Entrepreneurship",
        ["Ministry of Rural Development (DDU-GKY wing)|DDU-GKY", "Ministry of Labour and Employment (DGE)|labour laws",
         "Ministry of Education|schooling/higher education"],
        "PMKVY (2015) is implemented by MSDE through NSDC.", "Rural skilling (DDU-GKY) is MoRD.")
    g.f("L2", "DDU-GKY provides placement-linked skilling to rural youth of the age group:", "15–35 years",
        ["18–25 years|too narrow", "21–40 years|shifted range", "10–18 years|school age"],
        "Deen Dayal Upadhyaya Grameen Kaushalya Yojana (2014) targets poor rural youth aged 15–35 (higher for special groups).",
        "Starts at 15.", kind="numerical")
    g.f("L2", "Rural Self Employment Training Institutes (RSETIs) are managed by:", "Banks",
        ["Gram panchayats|local bodies", "Private universities|not the model", "Industrial Training Institutes|formal vocational training"],
        "RSETIs are bank-led, one per district, with MoRD support.", "Sponsor banks run them.")
    g.st(O, "L3", "Consider the following statements about MGNREGA, 2005 (as in force until 30 June 2026):",
         [("If work was provided beyond 5 km from the residence, extra wages of 10% were payable.", True),
          ("Unemployment allowance was payable if work was not provided within 30 days of application.", False),
          ("At least one-third of the beneficiaries were to be women.", True)],
         ["5 km rule with 10% extra wages; one-third women priority.", "Allowance was due if work was not provided within 15 days.",
          "MGNREGA was repealed w.e.f. 1 July 2026 by the VB-G RAM G Act, 2025."],
         "15 days, not 30.", ref="MGNREGA 2005, Schedules I–II (repealed w.e.f. 1 July 2026 by VB-G RAM G Act, 2025)")
    g.o("L2", "The National Rural Livelihoods Mission was created by restructuring:", "Swarnjayanti Gram Swarozgar Yojana",
        ["Sampoorna Grameen Rozgar Yojana|merged into MGNREGA", "Integrated Rural Development Programme|merged into SGSY earlier",
         "Jawahar Rozgar Yojana|wage employment scheme"],
        "SGSY (1999) was restructured as NRLM in 2011.", "IRDP → SGSY → NRLM.")
    g.o("L2", "World Youth Skills Day, also the launch date of the Skill India Mission (2015), is observed on:", "15 July",
        ["12 January|National Youth Day", "5 June|World Environment Day", "1 May|Labour Day"],
        "Skill India was launched on 15 July 2015.", "12 January is Vivekananda's birthday.")
    g.o("L2", "The National Skill Development Corporation (2008) is:", "A not-for-profit PPP company",
        ["A statutory regulator of all vocational training|NCVET's role", "A department of the Ministry of Education|not a department",
         "A constitutional body|not constitutional"],
        "NSDC is a PPP company under the Finance Ministry's initiative, now under MSDE.", "NCVET is the regulator.")
    g.mt(O, "L3", "Match the programme with its focus:", "Programme", "Focus",
         [("SVEP", "Rural enterprises under DAY-NRLM"), ("MKSP", "Empowerment of women farmers"),
          ("DDU-GKY", "Placement-linked skilling"), ("RSETI", "Self-employment training")],
         "Start-up Village Entrepreneurship Programme; Mahila Kisan Sashaktikaran Pariyojana; DDU-GKY; RSETI.",
         "MKSP targets women farmers, not enterprises.")
    g.ar(O, "L2", "MGNREGA, as in force until 30 June 2026, was a demand-driven programme.",
         "Under MGNREGA, work had to be provided when a registered household demanded it, as a legal entitlement.", True, True, True,
         ["The legal right to demand work made MGNREGA demand-driven.",
          "Its successor, the VB-G RAM G Act, 2025 (from 1 July 2026), uses Centre-fixed state allocations instead."],
         "Unlike supply-driven schemes with fixed allocations.",
         ref="MGNREGA 2005 (repealed w.e.f. 1 July 2026); VB-G RAM G Act, 2025")
    g.o("L2", "PM Vishwakarma (2023), covering artisans in 18 traditional trades, is implemented by the:", "Ministry of MSME",
        ["Ministry of Textiles|handloom schemes", "Ministry of Rural Development|NRLM", "Ministry of Culture|heritage"],
        "PM Vishwakarma offers recognition, toolkit incentive, skilling and collateral-free credit.", "MSME is nodal.")
    g.o("L2", "Industrial Training Institutes come under the:", "DGT, under MSDE",
        ["University Grants Commission|higher education", "AICTE|technical education", "NSDC|short-term skilling"],
        "Craftsmen Training Scheme through ITIs is administered by DGT under MSDE.", "AICTE regulates engineering colleges.")
    g.o("L2", "Apprenticeship training in India is governed by the:", "Apprentices Act, 1961",
        ["Factories Act, 1948|workplace safety", "Industrial Disputes Act, 1947|labour disputes", "Skill India Act, 2015|no such Act"],
        "The Apprentices Act, 1961; NAPS (2016) promotes apprenticeships.", "There is no 'Skill India Act'.")
    g.st(O, "L3", "Consider the following statements about DAY-NRLM:",
         [("It is funded entirely by the State Governments.", False),
          ("It is implemented by the Ministry of Rural Development.", True),
          ("SHGs are federated into village organisations and cluster-level federations.", True)],
         ["It is centrally sponsored (typically 60:40; 90:10 for NE/Himalayan states).", "MoRD; SHG → VO → CLF."],
         "Centrally sponsored, not state-funded.")

    # ------------------------------------------------------------------ rural roads
    g.m("gk-rural-road", "PMGSY Programme Guidelines (MoRD / NRIDA)")
    g.f("L1", "Pradhan Mantri Gram Sadak Yojana was launched in:", "2000",
        ["2005|Bharat Nirman", "1995|random", "2015|random"], "PMGSY was launched on 25 December 2000.",
        "Bharat Nirman (2005) later subsumed rural roads as a component.", kind="numerical")
    g.f("L1", "The main objective of PMGSY is to provide:", "All-weather roads to unlinked habitations",
        ["Four-lane highways linking all district towns|NH programme", "Railway links to every block headquarters|railways",
         "Urban ring roads for cities|urban scheme"],
        "PMGSY gives all-weather road connectivity to eligible unconnected habitations.", "Rural, all-weather, habitations.")
    g.f("L1", "PMGSY is administered by the:", "Ministry of Rural Development",
        ["Ministry of Road Transport and Highways|national highways", "Ministry of Panchayati Raj|local bodies",
         "Ministry of Housing and Urban Affairs|urban"], "MoRD runs PMGSY through NRIDA.", "MoRTH handles NHs.")
    g.f("L2", "Under original PMGSY norms, habitations in plain areas became eligible if their population was at least:", "500",
        ["250|special-category norm", "1,000|earlier phase priority", "100|too low"],
        "500+ in plains; 250+ in hill, desert, tribal and NE areas.", "250 applies to special areas.", kind="numerical")
    g.f("L2", "The online system used to manage and monitor PMGSY works is called:", "OMMAS",
        ["PFMS|public financial management", "e-NAM|agri markets", "GeM|procurement"],
        "Online Management, Monitoring and Accounting System.", "PFMS is for fund flows generally.")
    g.st(O, "L3", "Consider the following statements about PMGSY:",
         [("It was a 100% centrally sponsored scheme at launch.", True),
          ("It covers the upgrading of National Highways.", False),
          ("Contractors are responsible for routine maintenance of roads for five years after construction.", True)],
         ["Fully central at launch; later 60:40 (90:10 NE/Himalayan).", "NHs are outside PMGSY.", "Five-year maintenance contract."],
         "PMGSY is rural roads only.")
    g.o("L2", "The agency providing technical and management support for PMGSY is the:",
        "National Rural Infrastructure Development Agency",
        ["National Highways Authority of India|NH agency", "NABARD's Rural Infrastructure Development Fund|RIDF funding", "Central Road Research Institute|research lab"],
        "NRIDA (formerly NRRDA) under MoRD.", "NHAI builds highways.")
    g.mt(O, "L3", "Match the PMGSY phase or vertical with its focus:", "Phase / vertical", "Focus",
         [("PMGSY-I (2000)", "New connectivity to unconnected habitations"), ("PMGSY-II (2013)", "Upgradation of the existing rural network"),
          ("PMGSY-III (2019)", "Consolidating through routes to markets, schools and hospitals"),
          ("RCPLWEA (2016)", "Roads in Left Wing Extremism-affected areas")],
         "I—new connectivity; II—upgradation; III—through routes/major rural links; RCPLWEA—LWE areas.", "III is about consolidation.")
    g.o("L2", "RCPLWEA, launched in 2016 as a vertical under PMGSY, targets:", "Roads in LWE-affected areas",
        ["Border roads along the LAC|BRO", "Coastal roads for fishermen|coastal scheme", "Roads to tourist circuits|tourism scheme"],
        "Road Connectivity Project for Left Wing Extremism Affected Areas.", "Security-focused rural roads.")
    g.ar(O, "L3", "Under PMGSY, the unit for planning connectivity is the habitation rather than the revenue village.",
         "A revenue village may contain several habitations, and connectivity is planned for population clusters.", True, True, True,
         "Habitation-based planning reaches scattered clusters within villages.", "Habitation ≠ village.")
    g.o("L3", "Under PMGSY's three-tier quality mechanism, the third tier consists of:", "National Quality Monitors",
        ["Contractors' site engineers|first tier", "State Quality Monitors|second tier", "Social audit by the gram sabha|not a formal tier"],
        "Tier 1: PIU/contractor; Tier 2: SQMs; Tier 3: NQMs deployed by NRIDA.", "SQM is the second tier.")
    g.o("L2", "'Meri Sadak' (2015) is:", "A citizen app for PMGSY road complaints",
        ["A toll payment system for highways|FASTag", "A scheme for naming rural highways|invented", "A road-safety insurance scheme|invented"],
        "Meri Sadak lets citizens report complaints on PMGSY roads.", "Grievance app.")
    g.o("L2", "Which of the following is NOT a rural road connectivity scheme?", "Bharatmala Pariyojana",
        ["PMGSY-III|rural", "RCPLWEA|rural (LWE)", "PMGSY-II|rural"], "Bharatmala (MoRTH, 2017) is a highways programme.",
        "Bharatmala = national corridors.")
    g.o("L3", "In PMGSY terminology, the 'Core Network' means:", "The minimal network linking all eligible habitations",
        ["All roads maintained by the state PWD|too broad", "Only rural roads carrying over 1,000 vehicles a day|traffic criterion invented",
         "District roads linking to highways|partial"],
        "The Core Network is the least network needed for one all-weather link to each eligible habitation.", "Minimal, not total.")
    g.o("L3", "Rural roads as a subject fall under which list of the Seventh Schedule?", "State List",
        ["Union List|national highways", "Concurrent List|not roads", "Residuary powers|not needed"],
        "State List Entry 13 covers roads, bridges and ferries other than those in the Union List.",
        "National highways are Union List (Entry 23).", ref="Constitution of India, Seventh Schedule, List II Entry 13")

    # ------------------------------------------------------------------ SHGs & rural women
    g.m("gk-self-help-groups", "NABARD SHG-BLP documents; DAY-NRLM guidelines; Ministry of WCD")
    g.f("L1", "The SHG–Bank Linkage Programme was launched in 1992 by:", "NABARD",
        ["RBI|regulator, supported it", "SIDBI|MSME finance", "State Bank of India|a lender, not launcher"],
        "NABARD piloted SHG-BLP in 1992.", "RBI issued supportive guidelines.")
    g.f("L1", "A typical self-help group has how many members?", "10–20",
        ["2–5|too small", "50–100|federation size", "25–40|too large"], "SHGs usually have 10–20 members (5 for special groups).",
        "Federations are larger.", kind="numerical")
    g.f("L1", "Kudumbashree, the poverty-eradication and women-empowerment mission, belongs to:", "Kerala",
        ["Bihar|Jeevika", "Odisha|Mission Shakti", "Tamil Nadu|Mahalir Thittam"], "Launched in 1998 by the Kerala government.",
        "Each state has its own SHG mission.")
    g.f("L1", "The Grameen Bank model of microcredit was pioneered by:", "Muhammad Yunus",
        ["Ela Bhatt|SEWA", "Amartya Sen|welfare economist", "Verghese Kurien|dairy cooperatives"],
        "Yunus founded Grameen Bank in Bangladesh (Nobel Peace Prize 2006).", "Ela Bhatt founded SEWA.")
    g.f("L2", "Rashtriya Mahila Kosh, a microfinance body for poor women, was set up in:", "1993",
        ["1985|random", "2001|random", "2011|NRLM year"], "RMK was set up in 1993 under the Ministry of Women and Child Development.",
        "2011 is NRLM.", kind="numerical")
    g.st(O, "L3", "Consider the following statements about the SHG–Bank Linkage Programme:",
         [("It began as a NABARD pilot in 1992.", True),
          ("All members of an SHG must belong to the same family.", False),
          ("SHGs can obtain bank credit without collateral.", True)],
         ["Pilot 1992.", "Members are from different households with similar socio-economic background.", "Collateral-free group credit."],
         "Same family defeats the group principle.")
    g.mt(O, "L3", "Match the state livelihood / SHG mission with its state:", "Mission", "State",
         [("Kudumbashree", "Kerala"), ("Jeevika", "Bihar"), ("Mission Shakti", "Odisha"), ("Mahalir Thittam", "Tamil Nadu")],
         "Kudumbashree—Kerala; Jeevika—Bihar; Mission Shakti—Odisha; Mahalir Thittam—TN.", "Jeevika is Bihar's.")
    g.o("L2", "Under DAY-NRLM, the grant given to SHGs to strengthen their corpus and credit history is the:", "Revolving Fund",
        ["Community Investment Fund|given to federations", "Vulnerability Reduction Fund|given to VOs",
         "Interest Subvention|interest relief, not a corpus grant"],
        "The Revolving Fund is given to eligible SHGs; CIF flows through federations.", "CIF goes to federations.")
    g.o("L2", "Which of the following is NOT part of the 'Panchasutra' of SHGs?", "Collective farming",
        ["Regular meetings|Panchasutra", "Regular savings|Panchasutra", "Timely repayment|Panchasutra"],
        "Panchasutra: regular meetings, regular savings, regular inter-loaning, timely repayment, up-to-date books.",
        "Collective farming is optional activity, not a norm.")
    g.ar(O, "L3", "SHG lending has historically shown high repayment rates.",
         "Group members share responsibility and peer pressure encourages repayment.", True, True, True,
         "Joint responsibility and peer monitoring explain repayment.", "Social collateral substitutes for physical collateral.")
    g.o("L2", "Joint Liability Groups promoted by NABARD usually have:", "4–10 members",
        ["10–20 members|SHG size", "25–50 members|federation", "2–3 members|too few"],
        "JLGs (2006 scheme) of 4–10 tenant farmers/oral lessees take loans with mutual guarantee.", "JLGs are smaller than SHGs.",
        kind="numerical")
    g.o("L2", "The 'Namo Drone Didi' initiative provides:", "Drones to women SHGs for farm services",
        ["Scooters to rural women health workers|invented", "Loans to women for drone start-ups|misstates",
         "Drone pilot jobs in the armed forces|unrelated"],
        "Approved in 2023, it supplies agricultural drones to women SHGs for renting out spraying services.", "SHG-based, agri services.")
    g.o("L2", "Stand-Up India (2016) facilitates bank loans for greenfield enterprises to:", "SC/ST and women entrepreneurs",
        ["Only ex-servicemen|different scheme", "Only start-ups registered with DPIIT|Startup India",
         "Only micro-enterprises in rural areas|narrower than design"],
        "At least one SC/ST and one woman borrower per bank branch (₹10 lakh–₹1 crore).", "Stand-Up ≠ Startup India.")
    g.o("L2", "The Self-Employed Women's Association (SEWA) was founded in 1972 by:", "Ela Bhatt",
        ["Aruna Roy|MKSS", "Medha Patkar|Narmada Bachao Andolan", "Kiran Mazumdar-Shaw|biotech entrepreneur"],
        "Ela Bhatt founded SEWA in Ahmedabad.", "Aruna Roy is associated with RTI (MKSS).")
    g.o("L3", "A Gender Budget Statement was first included in the Union Budget in:", "2005–06",
        ["1991–92|reform budget", "2000–01|random", "2014–15|random"],
        "Gender budgeting was formally introduced in 2005–06.", "It is a statement, not a separate budget.", kind="numerical",
        ref="Union Budget documents (Statement 13 / Gender Budget)")

    # ------------------------------------------------------------------ urban missions
    g.m("gk-urban-development", "Constitution of India, Part IXA (74th Amendment); MoHUA mission guidelines")
    g.f("L1", "The Smart Cities Mission was launched in:", "2015",
        ["2014|SBM year", "2017|random", "2021|AMRUT 2.0 year"], "Launched on 25 June 2015 with AMRUT and PMAY-U.",
        "Three urban missions share the launch date.", kind="numerical")
    g.f("L1", "In AMRUT, the letter 'R' stands for:", "Rejuvenation",
        ["Reform|confuses with reforms agenda", "Renewal|JNNURM's word", "Rural|urban scheme"],
        "Atal Mission for Rejuvenation and Urban Transformation.", "JNNURM used 'Renewal'.")
    g.f("L1", "PMAY-Urban, 'Housing for All', is implemented by the:", "Ministry of Housing and Urban Affairs",
        ["Ministry of Rural Development|PMAY-Gramin", "Ministry of Finance (Expenditure)|funds", "NITI Aayog's urban vertical|think tank"],
        "MoHUA runs PMAY-U; MoRD runs PMAY-G.", "Urban vs rural split.")
    g.f("L1", "The Swachh Bharat Mission was launched on:", "2 October 2014",
        ["15 August 2014|Independence Day", "26 January 2015|Republic Day", "25 June 2015|Smart Cities launch"],
        "Launched on Gandhi Jayanti, 2014.", "Gandhi Jayanti link.")
    g.f("L1", "Constitutional status to urban local bodies was given by the:", "74th Amendment, 1992",
        ["73rd Amendment, 1992|panchayats", "42nd Amendment, 1976|many changes", "61st Amendment, 1988|voting age"],
        "The 74th Amendment inserted Part IXA (Municipalities).", "73rd is for panchayats.", ref="Constitution of India, Part IXA")
    g.st(O, "L3", "Consider the following statements about the 74th Constitutional Amendment:",
         [("It added the Eleventh Schedule.", False),
          ("It inserted Part IXA into the Constitution.", True),
          ("It added the Twelfth Schedule with 18 functional items.", True)],
         ["Eleventh Schedule came with the 73rd Amendment (panchayats, 29 items).", "74th: Part IXA and the Twelfth Schedule (18 items)."],
         "11th—panchayats; 12th—municipalities.", ref="Constitution of India, Part IXA, Twelfth Schedule")
    g.mt(O, "L3", "Match the urban mission with its focus:", "Mission", "Focus",
         [("AMRUT", "Water supply and sewerage in cities"), ("HRIDAY", "Development of heritage cities"),
          ("PMAY-Urban", "Affordable urban housing"), ("DAY-NULM", "Urban livelihoods")],
         "AMRUT—basic services; HRIDAY—heritage; PMAY-U—housing; DAY-NULM—livelihoods.", "HRIDAY is heritage, not health.")
    g.o("L2", "Swachh Survekshan, conducted since 2016, is:", "An annual cleanliness ranking of cities",
        ["A census of sanitation workers|not a census", "A survey of household toilets in villages|SBM-G tools", "A water-quality test of rivers and lakes|not SBM"],
        "MoHUA's Swachh Survekshan ranks cities on sanitation and cleanliness.", "Urban ranking survey.")
    g.o("L2", "AMRUT 2.0, launched in 2021, primarily aims to make cities:", "Water secure, with universal taps",
        ["Free of all slums and shanties|PMAY aim", "Fully powered by rooftop solar energy|energy aim", "Connected by metro rail networks|metro policy"],
        "AMRUT 2.0 targets universal water supply in all statutory towns and sewerage in AMRUT cities.", "Water-focused.")
    g.o("L3", "Under the Smart Cities Mission, projects are implemented at the city level through:",
        "A Special Purpose Vehicle company",
        ["The State Election Commission|conducts elections", "The District Planning Committee|plans districts",
         "A Central PSU under MoHUA|not the model"],
        "Each city forms an SPV incorporated under the Companies Act, 2013.", "SPV is a company, not a committee.")
    g.o("L2", "PM SVANidhi (2020) provides collateral-free working-capital loans to:", "Street vendors",
        ["Small farmers|KCC", "Women SHGs|NRLM", "MSME exporters|export credit"],
        "PM Street Vendor's AtmaNirbhar Nidhi, launched June 2020 by MoHUA.", "Urban street vendors.")
    g.ar(O, "L3", "The State Finance Commission also reviews the financial position of municipalities.",
         "Article 243Y applies the State Finance Commission constituted under Article 243I to municipalities as well.",
         True, True, True, "Article 243Y extends the SFC's mandate to municipalities.", "243I is for panchayats; 243Y extends it.",
         ref="Constitution of India, Arts. 243I, 243Y")
    g.o("L3", "Under Article 243Q, a 'Nagar Panchayat' is constituted for:", "A transitional area",
        ["A smaller urban area|Municipal Council", "A larger urban area|Municipal Corporation", "A rural village|Gram Panchayat"],
        "243Q: Nagar Panchayat — transitional area; Municipal Council — smaller urban; Corporation — larger urban.",
        "Nagar Panchayat is urban, not rural.", ref="Constitution of India, Art. 243Q")
    g.o("L3", "Article 243S requires Wards Committees in municipalities with a population of:", "Three lakh or more",
        ["One lakh or more|too low", "Five lakh or more|too high", "Ten lakh or more|metropolitan threshold"],
        "Wards Committees are mandatory for municipalities of 3 lakh+ population.", "10 lakh relates to metropolitan areas (243ZE).",
        kind="numerical", ref="Constitution of India, Art. 243S")
    g.o("L2", "Elections to municipalities are conducted by the:", "State Election Commission",
        ["Election Commission of India|Parliament/State legislatures", "State Finance Commission|finances",
         "District Collector|administrative officer"],
        "Article 243ZA vests municipal elections in the State Election Commission (Art. 243K).", "ECI does not hold local elections.",
        ref="Constitution of India, Arts. 243K, 243ZA")
