"""QRE-GK-A part 2 — Indian Polity and Constitution (10 microtopics x 15)."""
from gka_h import H


def add_all(B):
    h = H(B, "")
    F, S, N, M, C, A = h.F, h.S, h.N, h.M, h.C, h.A

    # ================= Civilian awards and the honours system =================
    h.topic("gk-civilian-awards-and-the-honours", "Ministry of Home Affairs — Padma/Bharat Ratna award rules (padmaawards.gov.in); Constitution of India, Art. 18")
    F("The Bharat Ratna was instituted in the year:",
      "1954", [("1950", "year the Republic and the Param Vir Chakra came into being"), ("1952", "year the Ashoka Chakra was instituted"),
               ("1947", "year of independence")],
      "Bharat Ratna and the Padma awards were instituted by Presidential notification in January 1954.",
      "The gallantry awards (1950/1952) came earlier than the civilian ones.")
    F("Which is the highest civilian award of the Republic of India?",
      "Bharat Ratna", [("Padma Vibhushan", "second-highest civilian award"), ("Param Vir Chakra", "highest wartime gallantry award"),
                       ("Ashoka Chakra", "highest peacetime gallantry award")],
      "Bharat Ratna is the highest civilian honour, followed by Padma Vibhushan, Padma Bhushan and Padma Shri.",
      "Gallantry awards are a separate series from civilian awards.")
    F("The Bharat Ratna medallion is shaped like a:",
      "Peepal leaf", [("Lotus", "motif of the Padma awards"), ("Circular disc", "shape of the original 1954 design"),
                      ("Five-pointed star", "not used for Bharat Ratna")],
      "The Bharat Ratna is a peepal-leaf-shaped bronze medallion with a sunburst and 'Bharat Ratna' in Devanagari.",
      "Padma means lotus — that motif belongs to the Padma awards.", lv="L2")
    F("Who was the first woman to receive the Bharat Ratna?",
      "Indira Gandhi", [("Mother Teresa", "received it in 1980"), ("Aruna Asaf Ali", "received it posthumously in 1997"),
                        ("Lata Mangeshkar", "received it in 2001")],
      "Indira Gandhi received the Bharat Ratna in 1971.",
      "Mother Teresa's award (1980) came nine years later.")
    F("The highest peacetime gallantry award in India is the:",
      "Ashoka Chakra", [("Param Vir Chakra", "highest wartime gallantry award"), ("Kirti Chakra", "second in the peacetime series"),
                        ("Maha Vir Chakra", "second in the wartime series")],
      "Ashoka Chakra heads the peacetime series (Ashoka, Kirti, Shaurya Chakra).",
      "Param Vir Chakra is for gallantry in the face of the enemy (wartime).")
    S("Consider the following statements about the Bharat Ratna:",
      [("Not more than three Bharat Ratna awards are ordinarily made in a year.", True, "the number is restricted to a maximum of three per year"),
       ("It must be conferred every year.", False, "it is not mandatory to award it every year; many years have had none"),
       ("It carries no monetary grant along with the medallion and sanad.", True, "the award carries no monetary grant")],
      "A ceiling of three does not mean a minimum of one.")
    A("The Bharat Ratna and Padma awards do not violate Article 18 of the Constitution.",
      "In Balaji Raghavan v. Union of India (1995), the Supreme Court held that these awards are not 'titles' within Article 18, though they must not be used as prefixes or suffixes to names.",
      True, True, True,
      "Art. 18 abolishes titles; the Court held national awards are recognitions of merit, not titles, subject to the no-prefix/suffix condition.",
      "Misuse as a prefix/suffix can lead to forfeiture — that is the condition the Court imposed.")
    C("Arrange the following Bharat Ratna conferments in chronological order:",
      [("C. V. Raman among the first recipients", 1954, "1954"), ("Lal Bahadur Shastri — first posthumous award", 1966, "1966"),
       ("Indira Gandhi — first woman recipient", 1971, "1971"), ("Nelson Mandela", 1990, "1990")],
      "Shastri (1966) precedes Indira Gandhi (1971).")
    M("Award", "Nature",
      [("Param Vir Chakra", "Highest wartime gallantry award"), ("Ashoka Chakra", "Highest peacetime gallantry award"),
       ("Padma Vibhushan", "Second-highest civilian award"), ("Sarvottam Jeevan Raksha Padak", "Award for saving life")],
      "Jeevan Raksha Padak awards recognise life-saving acts, separate from gallantry against the enemy.", lv="L2")
    N("Consider the following statements about the Padma awards:",
      [("They are announced on the eve of Republic Day.", True, "announced annually on 25 January"),
       ("Recommendations are made by a Padma Awards Committee headed by the Cabinet Secretary.", True, "the committee is constituted by the Prime Minister each year"),
       ("Government servants, including PSU employees, other than doctors and scientists, are not eligible.", True, "per the award rules"),
       ("Self-nomination is not permitted.", False, "any citizen may nominate, including self-nomination")],
      "The online nomination process explicitly allows self-nomination.")
    A("No Bharat Ratna or Padma awards were announced for 1978 and 1979.",
      "The civilian awards were discontinued by the Janata government in 1977 and restored in 1980.",
      True, True, True,
      "The awards were discontinued in July 1977 and reinstated in January 1980, explaining the gap.",
      "There was a second suspension in the 1990s due to litigation — a different episode.")
    S("Consider the following statements:",
      [("Sachin Tendulkar is the youngest recipient of the Bharat Ratna.", True, "he was 40 when awarded in 2014"),
       ("Sachin Tendulkar is the first sportsperson to receive the Bharat Ratna.", True, "the criteria were widened in 2011 to include any field"),
       ("Mother Teresa received the Bharat Ratna before she received the Nobel Peace Prize.", False, "Nobel 1979, Bharat Ratna 1980")],
      "Nobel (1979) came first, Bharat Ratna (1980) after.")
    M("Recipient", "Distinction in Bharat Ratna history",
      [("Lal Bahadur Shastri", "First posthumous recipient"), ("Indira Gandhi", "First woman recipient"),
       ("Khan Abdul Ghaffar Khan", "First recipient who was not an Indian citizen"), ("Sachin Tendulkar", "First sportsperson recipient")],
      "Ghaffar Khan (1987) preceded Nelson Mandela (1990) as a non-citizen recipient.")
    A("Bharat Ratna awardees are assigned a place in the Indian Table of Precedence.",
      "The Table of Precedence is laid down in the Constitution of India.",
      True, False, False,
      ["A is true: holders of the Bharat Ratna appear in the Table of Precedence.",
       "R is false: the Table of Precedence is issued by the President's Secretariat/MHA, not contained in the Constitution."],
      "Precedence is an executive arrangement, not a constitutional provision.")
    S("Consider the following statements about gallantry awards:",
      [("The Param Vir Chakra was instituted on 26 January 1950 with effect from 15 August 1947.", True, "retrospective effect from independence"),
       ("The Ashoka Chakra is the peacetime counterpart of the Param Vir Chakra.", True, "both head their respective series"),
       ("The Param Vir Chakra medal was designed by Savitri Khanolkar.", True, "she also designed several other gallantry medals")],
      "All three statements are correct.")

    # ================= Comparative government and world legislatures =================
    h.topic("gk-comparative-government", "M. Laxmikanth, 'Indian Polity' (salient features / sources of the Constitution); official parliament websites")
    F("'Knesset' is the name of the legislature of:",
      "Israel", [("Iran", "Majlis"), ("Japan", "Diet"), ("Denmark", "Folketing")],
      "The Knesset is Israel's unicameral legislature.", "Majlis is Iran's legislature — do not confuse Middle-Eastern names.")
    F("The national legislature of Japan is called the:",
      "Diet", [("Storting", "Norway"), ("Bundestag", "Germany (lower house)"), ("Eduskunta", "Finland")],
      "Japan's bicameral legislature is the National Diet (House of Representatives and House of Councillors).",
      "Diet is also a historical name in some European states, but today it denotes Japan.")
    F("'Storting' is the parliament of:",
      "Norway", [("Sweden", "Riksdag"), ("Denmark", "Folketing"), ("Iceland", "Althing")],
      "The Storting is Norway's parliament.", "Scandinavian names are close — Storting (Norway), Riksdag (Sweden).")
    F("The Directive Principles of State Policy in the Indian Constitution were borrowed from the Constitution of:",
      "Ireland", [("United States", "source of Fundamental Rights"), ("Canada", "source of quasi-federal features"),
                  ("Australia", "source of the Concurrent List")],
      "DPSP were adapted from the Irish Constitution (which itself drew on Spain).",
      "Fundamental Rights (USA) and DPSP (Ireland) are often swapped.")
    F("The idea of a Concurrent List in the Indian Constitution was borrowed from:",
      "Australia", [("Canada", "source of residuary powers with the Centre"), ("United States", "source of judicial review"),
                    ("Weimar Germany", "source of emergency suspension of rights")],
      "The Concurrent List, freedom of trade and commerce, and joint sitting were drawn from Australia.",
      "Canada gave the strong Centre and residuary powers, not the Concurrent List.", lv="L2")
    M("Legislature", "Country",
      [("Riksdag", "Sweden"), ("Folketing", "Denmark"), ("Althing", "Iceland"), ("Eduskunta", "Finland")],
      "Althing (Iceland, founded 930 CE) is among the oldest parliaments.", lv="L2")
    M("Legislature / chamber", "Country",
      [("Bundestag", "Germany"), ("State Duma", "Russia"), ("Sejm", "Poland"), ("Cortes Generales", "Spain")],
      "Sejm is the Polish lower house; Duma is Russian.", lv="L2")
    S("Consider the following statements about the government of the United States:",
      [("The Senate has 100 members, two from each state.", True, "equal representation of 50 states"),
       ("The President can dissolve the House of Representatives.", False, "the US has fixed terms; there is no power of dissolution"),
       ("The 22nd Amendment limits a person to being elected President twice.", True, "ratified in 1951")],
      "Dissolution is a parliamentary-system feature, absent in the US presidential system.")
    M("Feature of the Indian Constitution", "Source",
      [("Fundamental Duties", "Erstwhile USSR"), ("Suspension of Fundamental Rights during Emergency", "Weimar Constitution of Germany"),
       ("Residuary powers with the Centre", "Canada"), ("Procedure for amendment of the Constitution", "South Africa")],
      "Emergency suspension = Weimar; amendment procedure and election of Rajya Sabha members = South Africa.")
    A("The United Kingdom is said to have an uncodified constitution.",
      "Its constitutional rules are found in statutes, conventions, judicial decisions and authoritative works rather than in a single document.",
      True, True, True,
      "'Uncodified' means not collected in one document — exactly what R describes.",
      "Uncodified does not mean entirely unwritten; many parts are statutes.")
    S("Consider the following statements about Switzerland:",
      [("Its executive is a plural body, the Federal Council of seven members.", True, "collegial executive"),
       ("Citizens can use referendums and popular initiatives.", True, "instruments of direct democracy"),
       ("Its national legislature is the Federal Assembly.", True, "bicameral: National Council and Council of States")],
      "All three statements are correct.")
    A("In the United States, members of the Cabinet cannot simultaneously be members of Congress.",
      "The US Constitution follows a strict separation of powers between the executive and the legislature.",
      True, True, True,
      "The Incompatibility Clause (Art. I, Sec. 6) bars executive officers from sitting in Congress — a direct consequence of separation of powers.",
      "Contrast with India, where ministers must be members of Parliament.")
    C("Arrange the following constitutional documents in chronological order:",
      [("Magna Carta", 1215, "1215"), ("Constitution of the United States signed", 1787, "1787"),
       ("French Declaration of the Rights of Man and of the Citizen", 1789, "1789"), ("Weimar Constitution", 1919, "1919")],
      "The US Constitution (1787) precedes the French Declaration (1789) by two years.")
    N("Consider the following pairs (feature of the Indian Constitution — source):",
      [("Judicial review — United States", True, "borrowed from the US"),
       ("Nomination of members to the Rajya Sabha — Ireland", True, "borrowed from the Irish Constitution"),
       ("Joint sitting of the two Houses — Australia", True, "borrowed from Australia"),
       ("Single citizenship — United States", False, "single citizenship is from the UK; the US has dual (federal and state) citizenship")],
      "The US model is dual citizenship — the opposite of India's.", pairs=True)
    S("Consider the following statements about the French Fifth Republic:",
      [("It has both a directly elected President and a Prime Minister.", True, "semi-presidential system"),
       ("Its Parliament consists of the National Assembly and the Senate.", True, "bicameral")],
      "Both statements are correct.", lv="L2")

    # ================= Fundamental Rights =================
    h.topic("gk-fundamental-rights", "Constitution of India, Part III (Arts. 12–35); M. Laxmikanth, 'Indian Polity'")
    F("Which Article of the Constitution abolishes untouchability?",
      "Article 17", [("Article 15", "prohibits discrimination on specified grounds"), ("Article 16", "equality of opportunity in public employment"),
                     ("Article 18", "abolishes titles")],
      "Art. 17 abolishes untouchability and forbids its practice in any form.", "Arts. 14–18 form the Right to Equality; 17 is untouchability.",
      ref="Constitution of India, Art. 17")
    F("The Right to Constitutional Remedies is guaranteed under:",
      "Article 32", [("Article 226", "writ jurisdiction of High Courts — not a Fundamental Right"), ("Article 21", "right to life"),
                     ("Article 19", "six freedoms")],
      "Art. 32 — called the 'heart and soul' of the Constitution by Ambedkar — lets a person move the Supreme Court for enforcement of Fundamental Rights.",
      "Art. 226 is wider but is not itself in Part III.", ref="Constitution of India, Art. 32")
    F("The right to free and compulsory education for children of 6 to 14 years (Art. 21A) was inserted by the:",
      "86th Amendment Act, 2002", [("42nd Amendment Act, 1976", "added Fundamental Duties"), ("44th Amendment Act, 1978", "removed right to property"),
                                   ("73rd Amendment Act, 1992", "Panchayati Raj")],
      "The 86th Amendment inserted Art. 21A, amended Art. 45 and added a Fundamental Duty (Art. 51A(k)).",
      "The 42nd Amendment moved education to the Concurrent List — not Art. 21A.", ref="Constitution (86th Amendment) Act, 2002")
    F("The right to property was removed from the list of Fundamental Rights by the:",
      "44th Amendment Act, 1978", [("42nd Amendment Act, 1976", "added Socialist, Secular to the Preamble"),
                                   ("24th Amendment Act, 1971", "affirmed Parliament's power to amend FRs"),
                                   ("52nd Amendment Act, 1985", "anti-defection law")],
      "The 44th Amendment deleted Arts. 19(1)(f) and 31 and inserted Art. 300A.",
      "42nd and 44th are often swapped; 44th undid many 42nd changes.", ref="Constitution (44th Amendment) Act, 1978")
    F("Which writ is issued to produce a detained person before a court?",
      "Habeas corpus", [("Mandamus", "command to perform a public duty"), ("Quo warranto", "questions the right to hold a public office"),
                        ("Certiorari", "quashes an order of a lower court")],
      "Habeas corpus ('to have the body') secures release from unlawful detention.",
      "Each writ has a distinct purpose — match the Latin meaning.", ref="Constitution of India, Arts. 32 and 226")
    S("Consider the following statements:",
      [("The rights under Article 15 are available only to citizens.", True, "Arts. 15, 16, 19, 29 and 30 are citizen-only rights"),
       ("The right under Article 21 is available only to citizens.", False, "Art. 21 applies to all persons, citizens and foreigners"),
       ("The rights under Article 30 are available only to citizens.", True, "the minority educational rights are classed as citizen-only")],
      "Life and liberty (Art. 21) extend to every person.", ref="Constitution of India, Part III")
    A("The rights under Articles 20 and 21 cannot be suspended even during a National Emergency.",
      "The 44th Amendment provided that the President cannot suspend the right to move courts for enforcement of Articles 20 and 21 under Article 359.",
      True, True, True,
      "After the 1975–77 experience, the 44th Amendment carved Arts. 20 and 21 out of Art. 359 suspension orders.",
      "Art. 19 is automatically suspended under Art. 358 in a war/external aggression emergency — not so Arts. 20 and 21.",
      ref="Constitution of India, Art. 359 (as amended by the 44th Amendment)")
    M("Writ", "Literal meaning",
      [("Mandamus", "We command"), ("Quo warranto", "By what authority or warrant"), ("Certiorari", "To be certified or informed"),
       ("Habeas corpus", "To have the body")],
      "Certiorari (to be informed) is often confused with prohibition.", lv="L2", ref="Constitution of India, Art. 32")
    M("Article", "Subject",
      [("Article 22", "Protection against arrest and detention in certain cases"), ("Article 23", "Prohibition of traffic in human beings and forced labour"),
       ("Article 24", "Prohibition of employment of children in factories"), ("Article 28", "Freedom from religious instruction in certain institutions")],
      "Arts. 23–24 are the Right against Exploitation; Art. 28 is part of freedom of religion.", ref="Constitution of India, Arts. 22–28")
    N("Consider the following protections and state how many are provided under Article 20:",
      [("No ex post facto criminal law increasing punishment", True, "Art. 20(1)"), ("Protection against double jeopardy", True, "Art. 20(2)"),
       ("Protection against self-incrimination for an accused", True, "Art. 20(3)"),
       ("Protection against preventive detention without review", False, "that is Art. 22")],
      "Preventive detention safeguards are in Art. 22, not Art. 20.", ref="Constitution of India, Arts. 20 and 22")
    C("Arrange the following Supreme Court judgments in chronological order:",
      [("A. K. Gopalan v. State of Madras", 1950, "1950"), ("I. C. Golaknath v. State of Punjab", 1967, "1967"),
       ("Kesavananda Bharati v. State of Kerala", 1973, "1973"), ("Maneka Gandhi v. Union of India", 1978, "1978")],
      "Maneka Gandhi (1978) overruled the narrow Gopalan reading of Art. 21.", ref="Supreme Court of India law reports")
    A("The right to privacy is a Fundamental Right.",
      "In Justice K. S. Puttaswamy v. Union of India (2017), the Supreme Court held that privacy is protected only under Article 19.",
      True, False, False,
      ["A is true.", "R is false: the nine-judge bench held privacy intrinsic to Article 21 and to the freedoms of Part III as a whole, not Article 19 alone."],
      "Earlier cases (M. P. Sharma, Kharak Singh) had denied it; Puttaswamy overruled them.", ref="K. S. Puttaswamy v. Union of India (2017) 10 SCC 1")
    S("Consider the following statements about Article 19:",
      [("Freedom of the press is expressly mentioned in Article 19.", False, "it is implied in freedom of speech and expression, Art. 19(1)(a)"),
       ("Article 19 originally guaranteed seven freedoms.", True, "19(1)(f) property was deleted in 1978, leaving six"),
       ("The right to form cooperative societies was added to Article 19(1)(c) by the 97th Amendment.", True, "97th Amendment Act, 2011")],
      "Press freedom is judicially derived, not expressly stated.", ref="Constitution of India, Art. 19")
    S("Consider the following statements about writs:",
      [("The writ jurisdiction of the Supreme Court under Article 32 is wider than that of High Courts under Article 226.", False,
        "HCs can issue writs for FRs and 'for any other purpose', so their writ jurisdiction is wider"),
       ("A writ of quo warranto can be sought by any interested person, not only an aggrieved one.", True, "relaxed locus standi"),
       ("Mandamus cannot be issued against the President or a state Governor acting in official capacity.", True, "they are protected under Art. 361")],
      "Art. 32 is itself a Fundamental Right, but its scope is narrower than Art. 226.", ask="incorrect",
      ref="Constitution of India, Arts. 32, 226 and 361")
    A("The right to property is no longer a Fundamental Right.",
      "It is now a constitutional right under Article 300A.",
      True, True, False,
      ["A is true because the 44th Amendment (1978) deleted Arts. 19(1)(f) and 31.",
       "R states its present status, but the cause of A is the 44th Amendment, not Art. 300A itself."],
      "A description of the current position is not the reason for the change.", ref="Constitution of India, Art. 300A")

    # ================= Judiciary and judicial administration =================
    h.topic("gk-judiciary-and-judicial", "Constitution of India, Part V Ch. IV and Part VI Ch. V; M. Laxmikanth, 'Indian Polity'")
    F("The Supreme Court of India is established under which Article of the Constitution?",
      "Article 124", [("Article 214", "High Courts for states"), ("Article 32", "right to constitutional remedies"),
                      ("Article 226", "writ jurisdiction of High Courts")],
      "Art. 124(1) establishes the Supreme Court.", "Art. 214 is the High Court counterpart.", ref="Constitution of India, Art. 124")
    F("A judge of a High Court holds office until the age of:",
      "62 years", [("65 years", "retirement age of Supreme Court judges"), ("60 years", "common superannuation age in services"),
                   ("58 years", "not applicable")],
      "Art. 217(1): HC judges hold office until 62; SC judges until 65 (Art. 124(2)).",
      "Do not swap HC (62) and SC (65).", ref="Constitution of India, Art. 217")
    F("Who was the first Chief Justice of India?",
      "H. J. Kania", [("M. Patanjali Sastri", "second Chief Justice"), ("K. G. Balakrishnan", "much later CJI"),
                      ("Y. V. Chandrachud", "longest-serving CJI")],
      "Harilal Jekisundas Kania became the first CJI on 26 January 1950.",
      "Patanjali Sastri succeeded Kania in 1951.", ref="Supreme Court of India — former Chief Justices")
    F("Who was the first woman judge of the Supreme Court of India?",
      "M. Fathima Beevi", [("Leila Seth", "first woman Chief Justice of a High Court"), ("Anna Chandy", "first woman High Court judge"),
                           ("Sujata Manohar", "later SC judge")],
      "Justice M. Fathima Beevi was appointed to the Supreme Court in 1989.",
      "Anna Chandy and Leila Seth were High Court firsts.", ref="Supreme Court of India — former judges")
    F("Lok Adalats were given statutory status by the:",
      "Legal Services Authorities Act, 1987", [("Code of Civil Procedure, 1908", "general civil procedure"),
                                                ("Arbitration and Conciliation Act, 1996", "arbitration law"),
                                                ("Gram Nyayalayas Act, 2008", "village courts")],
      "The Legal Services Authorities Act, 1987 (in force 1995) gave Lok Adalats statutory status and set up NALSA.",
      "Gram Nyayalayas are regular courts at the grassroots, not Lok Adalats.", lv="L2", ref="Legal Services Authorities Act, 1987")
    M("Article", "Jurisdiction / power of the Supreme Court",
      [("Article 131", "Original jurisdiction in federal disputes"), ("Article 136", "Special leave to appeal"),
       ("Article 137", "Review of its own judgments"), ("Article 143", "Advisory jurisdiction on reference by the President")],
      "Art. 143 (advisory) and Art. 131 (original) are the most frequently confused.", ref="Constitution of India, Arts. 131–143")
    S("Consider the following statements about the removal of a Supreme Court judge:",
      [("A judge can be removed by the President on an address by Parliament passed by a special majority in each House.", True, "Art. 124(4)"),
       ("The grounds are proved misbehaviour or incapacity.", True, "Art. 124(4)"),
       ("The motion must be passed at a joint sitting of both Houses.", False, "each House must pass it separately; there is no joint sitting")],
      "Joint sittings apply only to ordinary bills (Art. 108).", ref="Constitution of India, Art. 124(4); Judges (Inquiry) Act, 1968")
    A("The Supreme Court is a court of record.",
      "Its judgments are recorded for perpetual memory and testimony, and it has the power to punish for contempt of itself.",
      True, True, True,
      "Art. 129 makes the SC a court of record with contempt powers — the two attributes stated in R.",
      "Art. 215 gives High Courts the same status.", ref="Constitution of India, Art. 129")
    C("Arrange the following Supreme Court cases on judicial appointments in chronological order:",
      [("S. P. Gupta v. Union of India (First Judges case)", 1981, "1981"),
       ("Supreme Court Advocates-on-Record Association v. Union of India (Second Judges case)", 1993, "1993"),
       ("Third Judges case (Presidential reference)", 1998, "1998"), ("NJAC judgment striking down the 99th Amendment", 2015, "2015")],
      "The collegium system dates from the Second Judges case (1993).", ref="Supreme Court of India law reports")
    S("Consider the following statements about High Courts:",
      [("Parliament may establish a common High Court for two or more states.", True, "Art. 231"),
       ("High Court judges are appointed by the Governor of the state.", False, "they are appointed by the President (Art. 217)"),
       ("A High Court has superintendence over all courts and tribunals in its territory except military tribunals.", True, "Art. 227")],
      "The Governor is only consulted; the President appoints.", ref="Constitution of India, Arts. 217, 227, 231")
    M("Article", "Provision",
      [("Article 127", "Appointment of ad hoc judges in the Supreme Court"), ("Article 128", "Attendance of retired judges at sittings of the Supreme Court"),
       ("Article 224", "Additional and acting judges of High Courts"), ("Article 233", "Appointment of district judges")],
      "Art. 224A (retired HC judges) is distinct from Art. 224 (additional judges).", ref="Constitution of India, Arts. 127, 128, 224, 233")
    A("The law declared by the Supreme Court is binding on all courts within the territory of India.",
      "Article 142 empowers the Supreme Court to pass any decree or order necessary for doing complete justice.",
      True, True, False, ["Both statements are true.", "The binding effect of SC law comes from Art. 141, not Art. 142."],
      "Art. 142 (complete justice) is a different power.", lv="L2", ref="Constitution of India, Art. 141")
    N("Consider the following statements about Lok Adalats:",
      [("An award of a Lok Adalat is deemed to be a decree of a civil court.", True, "Sec. 21, LSA Act"),
       ("No appeal lies against an award of a Lok Adalat.", True, "the award is final"),
       ("Court fee already paid is refunded when a pending case is settled in a Lok Adalat.", True, "as per the Act"),
       ("A Lok Adalat can decide non-compoundable criminal offences.", False, "it has no jurisdiction over non-compoundable offences")],
      "Lok Adalats work by compromise — impossible for non-compoundable offences.", ref="Legal Services Authorities Act, 1987")
    A("The Constitution (99th Amendment) Act creating the National Judicial Appointments Commission was struck down.",
      "The Supreme Court held that it violated the independence of the judiciary, which is part of the basic structure.",
      True, True, True,
      "In 2015 a Constitution Bench invalidated the NJAC on basic-structure grounds and restored the collegium.",
      "R gives the precise legal ground for the invalidation.", ref="SCAORA v. Union of India (2015)")
    S("Consider the following statements:",
      [("Article 39A on free legal aid was inserted by the 44th Amendment.", False, "it was inserted by the 42nd Amendment, 1976"),
       ("The curative petition was evolved in Rupa Ashok Hurra v. Ashok Hurra.", True, "2002"),
       ("Article 142 empowers the Supreme Court to pass orders for doing complete justice.", True, "Art. 142(1)")],
      "The 42nd Amendment added Arts. 39A, 43A and 48A.", ref="Constitution of India, Arts. 39A, 142")

    # ================= President and Vice-President of India =================
    h.topic("gk-president-and-vice-president", "Constitution of India, Arts. 52–72; M. Laxmikanth, 'Indian Polity'")
    F("The minimum age for election as President of India is:",
      "35 years", [("25 years", "minimum age for Lok Sabha"), ("30 years", "minimum age for Rajya Sabha"), ("40 years", "no such limit")],
      "Art. 58: a candidate must be 35 and qualified for election to the Lok Sabha.", "25 and 30 are the ages for LS and RS membership.",
      ref="Constitution of India, Art. 58")
    F("Who is the ex officio Chairman of the Rajya Sabha?",
      "Vice-President of India", [("Speaker of the Lok Sabha", "presides over the Lok Sabha"), ("President of India", "part of Parliament but does not preside"),
                                  ("Deputy Chairman of the Rajya Sabha", "presides only in the Chairman's absence")],
      "Art. 64: the Vice-President is ex officio Chairman of the Council of States.", "The Deputy Chairman is elected from among RS members.",
      ref="Constitution of India, Art. 64")
    F("The oath of office of the President is administered by the:",
      "Chief Justice of India", [("Vice-President", "administers no oath to the President"), ("Speaker of the Lok Sabha", "not the oath authority"),
                                 ("Attorney General", "law officer")],
      "Art. 60: the oath is made before the CJI or, in his absence, the senior-most SC judge.",
      "The President's oath is in Art. 60, not in the Third Schedule.", ref="Constitution of India, Art. 60")
    F("The President's power to grant pardons is contained in:",
      "Article 72", [("Article 161", "pardoning power of the Governor"), ("Article 123", "ordinance-making power"),
                     ("Article 74", "Council of Ministers to aid and advise")],
      "Art. 72 covers pardon, reprieve, respite, remission, suspension and commutation.", "Art. 161 is the Governor's analogue.",
      ref="Constitution of India, Art. 72")
    F("Who was the first Vice-President of India?",
      "S. Radhakrishnan", [("Zakir Husain", "second Vice-President"), ("V. V. Giri", "third Vice-President"),
                           ("Rajendra Prasad", "first President")],
      "Dr Sarvepalli Radhakrishnan was Vice-President 1952–62 and then President.",
      "Zakir Husain followed him as Vice-President.", ref="Vice-President's Secretariat — former Vice-Presidents")
    S("Consider the following statements about the election of the President:",
      [("Nominated members of Parliament do not vote in the election.", True, "only elected members of Parliament are in the electoral college"),
       ("Members of state Legislative Councils vote in the election.", False, "only elected members of Legislative Assemblies vote"),
       ("Elected members of the Legislative Assemblies of Delhi and Puducherry vote in the election.", True, "added by the 70th Amendment, 1992")],
      "Councils are excluded; Delhi and Puducherry assemblies are included.", ref="Constitution of India, Arts. 54–55")
    S("Consider the following statements about the Vice-President:",
      [("Nominated members of Parliament vote in the Vice-Presidential election.", True, "the electoral college is all members of both Houses"),
       ("A resolution for removal of the Vice-President can be moved only in the Rajya Sabha.", True, "Art. 67(b)"),
       ("The Vice-President can be removed only by impeachment under the procedure applicable to the President.", False,
        "removal is by an RS resolution passed by an effective majority and agreed to by the LS — not impeachment")],
      "The VP's removal is simpler than the President's impeachment.", ref="Constitution of India, Arts. 66–67")
    A("Nominated members of Parliament can take part in the impeachment of the President though they do not vote in his election.",
      "An impeachment resolution requires a majority of not less than two-thirds of the total membership of the House, which includes nominated members.",
      True, True, True,
      "Art. 61 is framed in terms of the total membership of each House — nominated members are part of it — whereas Art. 54 limits the electoral college to elected members.",
      "Election (Art. 54) and impeachment (Art. 61) have different participants.", ref="Constitution of India, Arts. 54, 61")
    M("Article", "Subject",
      [("Article 54", "Election of the President"), ("Article 61", "Impeachment of the President"),
       ("Article 72", "Pardoning power"), ("Article 123", "Ordinance-making power")],
      "Art. 123 (President) vs Art. 213 (Governor) for ordinances.", lv="L2", ref="Constitution of India")
    C("Arrange the following Presidents in the order in which they took office:",
      [("Zakir Husain", 1967, "1967"), ("V. V. Giri", 1969, "1969"), ("Neelam Sanjiva Reddy", 1977, "1977"), ("R. Venkataraman", 1987, "1987")],
      "Fakhruddin Ali Ahmed (1974) sits between Giri and Reddy but is not listed.", ref="President's Secretariat — former Presidents")
    S("Consider the following statements about the pardoning power:",
      [("The President can grant a pardon in all cases where the sentence is by a court martial.", True, "Art. 72(1)(a); the Governor has no such power"),
       ("The President can grant a pardon for an offence against a law on a Union matter.", True, "Art. 72(1)(b)"),
       ("The exercise of the pardoning power is wholly immune from judicial review.", False, "courts may review it on limited grounds such as mala fides or arbitrariness")],
      "Limited judicial review was affirmed in Kehar Singh (1989) and Epuru Sudhakar (2006).", ref="Constitution of India, Art. 72")
    A("The President can return a non-Money Bill to Parliament for reconsideration only once.",
      "If the Bill is passed again, with or without amendments, the President must give assent.",
      True, True, True, "Art. 111: the suspensive veto can be used once; re-passage compels assent.",
      "Money Bills cannot be returned at all.", ref="Constitution of India, Art. 111")
    M("Type of veto", "Meaning",
      [("Absolute veto", "Withholding assent to a bill"), ("Suspensive veto", "Returning a bill for reconsideration"),
       ("Pocket veto", "Taking no action on a bill indefinitely"), ("Qualified veto", "Veto that the legislature can override by a higher majority")],
      "The Indian President has absolute, suspensive and pocket vetoes, but not a qualified veto.", ref="Constitution of India, Art. 111")
    N("Consider the following statements:",
      [("Rajendra Prasad is the only President to have served two full terms.", True, "1950–62"),
       ("Neelam Sanjiva Reddy is the only President elected unopposed.", True, "1977"),
       ("Zakir Husain was the first President to die in office.", True, "1969"),
       ("Pratibha Patil was the first woman President.", True, "2007")],
      "All four are established firsts.", ref="President's Secretariat — former Presidents")
    A("The President addresses his resignation letter to the Vice-President.",
      "The Vice-President is the ex officio Chairman of the Rajya Sabha.",
      True, True, False,
      ["A is true under Art. 56(1)(a).", "R is true (Art. 64) but unrelated: the VP receives the letter because Art. 56 so provides, not because of his RS role."],
      "Two true constitutional facts need not be causally linked.", ref="Constitution of India, Arts. 56, 64")

    # ================= Recent central legislation and statutory penalties =================
    h.topic("gk-recent-central-legislation", "Gazette of India — Acts of Parliament (2019–2024); PRS Legislative Research bill summaries")
    F("The Bharatiya Nyaya Sanhita, 2023 replaced the:",
      "Indian Penal Code, 1860", [("Code of Criminal Procedure, 1973", "replaced by BNSS"), ("Indian Evidence Act, 1872", "replaced by BSA"),
                                  ("Police Act, 1861", "not replaced by these laws")],
      "BNS is the new substantive criminal code replacing the IPC.", "Nyaya Sanhita = penal code; Nagarik Suraksha Sanhita = procedure.")
    F("The Bharatiya Sakshya Adhiniyam, 2023 replaced the:",
      "Indian Evidence Act, 1872", [("Indian Penal Code, 1860", "replaced by BNS"), ("Code of Criminal Procedure, 1973", "replaced by BNSS"),
                                    ("Code of Civil Procedure, 1908", "not replaced")],
      "Sakshya means evidence; BSA replaced the 1872 Evidence Act.", "Translate the Hindi title to identify the law.")
    F("Under the Constitution (106th Amendment) Act, 2023 (Nari Shakti Vandan Adhiniyam), the share of seats reserved for women in the Lok Sabha is:",
      "One-third", [("One-fourth", "incorrect fraction"), ("One-half", "applies to panchayats in several states by state law, not here"),
                    ("One-fifth", "incorrect fraction")],
      "The Act reserves, as nearly as may be, one-third of seats for women in the Lok Sabha, state assemblies and the Delhi assembly.",
      "Panchayat reservation (73rd Amendment) is also one-third minimum.", ref="Constitution (106th Amendment) Act, 2023")
    F("The Telecommunications Act, 2023 replaced, among others, the:",
      "Indian Telegraph Act, 1885", [("Information Technology Act, 2000", "still in force"), ("TRAI Act, 1997", "still in force"),
                                     ("Indian Post Office Act, 1898", "replaced by the Post Office Act, 2023")],
      "The Telecommunications Act, 2023 replaced the Indian Telegraph Act 1885 and the Indian Wireless Telegraphy Act 1933.",
      "The postal law was replaced by a separate 2023 Act.")
    F("The three new criminal laws (BNS, BNSS, BSA) came into force on:",
      "1 July 2024", [("1 January 2024", "incorrect date"), ("26 January 2024", "Republic Day; not the commencement date"),
                      ("15 August 2024", "Independence Day; not the commencement date")],
      "The Acts received assent in December 2023 and were brought into force from 1 July 2024.",
      "Assent (Dec 2023) and commencement (July 2024) differ.", lv="L2")
    S("Consider the following statements about the Bharatiya Nyaya Sanhita, 2023:",
      [("It contains 358 sections.", True, "fewer than the IPC's 511"),
       ("It retains the offence of sedition under that name.", False, "the term sedition is dropped; Sec. 152 covers acts endangering sovereignty, unity and integrity"),
       ("It introduces community service as a form of punishment.", True, "for certain petty offences")],
      "Sec. 152 BNS is not titled 'sedition'.", ref="Bharatiya Nyaya Sanhita, 2023")
    M("New law", "Law it replaced",
      [("Bharatiya Nyaya Sanhita, 2023", "Indian Penal Code, 1860"), ("Bharatiya Nagarik Suraksha Sanhita, 2023", "Code of Criminal Procedure, 1973"),
       ("Bharatiya Sakshya Adhiniyam, 2023", "Indian Evidence Act, 1872"), ("Post Office Act, 2023", "Indian Post Office Act, 1898")],
      "Nagarik Suraksha (citizen protection) = procedure code.", lv="L2")
    N("Consider the following statements about the Digital Personal Data Protection Act, 2023:",
      [("It establishes the Data Protection Board of India.", True, "adjudicatory body under the Act"),
       ("The individual to whom personal data relates is called the 'Data Principal'.", True, "the processor-controller is the 'Data Fiduciary'"),
       ("The penalty for a single category of breach can extend up to ₹250 crore.", True, "maximum in the Schedule for failure of security safeguards"),
       ("Appeals against the Board's orders lie directly to the Supreme Court.", False, "appeals lie to the Telecom Disputes Settlement and Appellate Tribunal (TDSAT)")],
      "TDSAT is the appellate forum, not the Supreme Court.", ref="Digital Personal Data Protection Act, 2023")
    A("The reservation of seats for women under the 106th Amendment did not take effect immediately on enactment.",
      "It comes into effect after a delimitation exercise based on the first census conducted after the commencement of the Amendment.",
      True, True, True,
      "The Act links operationalisation to census-based delimitation; hence no immediate effect.",
      "Reservation is for 15 years, extendable by Parliament.", ref="Constitution (106th Amendment) Act, 2023")
    S("Consider the following statements about the Nari Shakti Vandan Adhiniyam, 2023:",
      [("It applies to the Rajya Sabha and state Legislative Councils.", False, "it applies to the Lok Sabha, state assemblies and the Delhi assembly only"),
       ("It applies to the Legislative Assembly of the National Capital Territory of Delhi.", True, "Art. 239AA was amended"),
       ("One-third of the seats reserved for SCs and STs will also be reserved for women of those groups.", True, "reservation within reservation")],
      "Indirectly elected upper houses are outside the scheme.", ref="Constitution (106th Amendment) Act, 2023")
    A("The Jan Vishwas (Amendment of Provisions) Act, 2023 is aimed at improving ease of doing business.",
      "It decriminalised minor offences under many central Acts, replacing imprisonment with monetary penalties.",
      True, True, True,
      "The Act amended 183 provisions in 42 central Acts to reduce compliance fear — the mechanism for easing business.",
      "Decriminalisation, not deregulation, is the core of the Act.", ref="Jan Vishwas (Amendment of Provisions) Act, 2023")
    C("Arrange the following Acts in the order of their enactment:",
      [("Right to Information Act", 2005, "2005"), ("Lokpal and Lokayuktas Act", 2013, "2013"),
       ("Consumer Protection Act (new)", 2019, "2019"), ("Digital Personal Data Protection Act", 2023, "2023")],
      "The Consumer Protection Act, 2019 replaced the 1986 Act.")
    M("Act", "Statutory body created",
      [("Digital Personal Data Protection Act, 2023", "Data Protection Board of India"), ("Consumer Protection Act, 2019", "Central Consumer Protection Authority"),
       ("Right to Information Act, 2005", "Central Information Commission"), ("Lokpal and Lokayuktas Act, 2013", "Lokpal")],
      "CCPA is the regulator under the 2019 consumer law.", lv="L2")
    S("Consider the following statements about penalties under the RTI Act, 2005:",
      [("An Information Commission may impose a penalty of ₹250 per day on a PIO for delay.", True, "Sec. 20(1)"),
       ("The total penalty shall not exceed ₹25,000.", True, "Sec. 20(1)"),
       ("The penalty is paid by the public authority out of its budget.", False, "the penalty is personal and is recovered from the PIO")],
      "It is a personal penalty on the Public Information Officer.", ref="Right to Information Act, 2005, Sec. 20")
    A("Under the Bharatiya Nagarik Suraksha Sanhita, 2023, an FIR can be registered irrespective of the area where the offence was committed.",
      "The Sanhita gives statutory recognition to the 'Zero FIR'.",
      True, True, True,
      "A Zero FIR is one registered by any police station regardless of jurisdiction and later transferred — BNSS codifies it.",
      "Zero FIR was earlier a practice; BNSS made it statutory.", ref="Bharatiya Nagarik Suraksha Sanhita, 2023, Sec. 173")

    # ================= Schedules of the Constitution =================
    h.topic("gk-schedules-of-the-constitution", "Constitution of India, First to Twelfth Schedules")
    F("The anti-defection provisions are contained in the:",
      "Tenth Schedule", [("Ninth Schedule", "validation of certain Acts"), ("Eighth Schedule", "languages"), ("Eleventh Schedule", "panchayats")],
      "The Tenth Schedule was added by the 52nd Amendment, 1985.", "Ninth vs Tenth are adjacent and commonly swapped.")
    F("The languages recognised by the Constitution are listed in the:",
      "Eighth Schedule", [("Seventh Schedule", "legislative lists"), ("Sixth Schedule", "tribal areas of the North-East"), ("Third Schedule", "oaths")],
      "The Eighth Schedule lists 22 languages.", "Seventh = lists; Eighth = languages.")
    F("How many Schedules does the Constitution of India now contain?",
      "12", [("8", "number in the original Constitution"), ("10", "incorrect"), ("14", "incorrect")],
      "The original eight grew to twelve with the Ninth (1951), Tenth (1985), Eleventh (1992) and Twelfth (1992) Schedules.",
      "Eight was the original count.")
    F("The allocation of seats in the Rajya Sabha to states and union territories is in the:",
      "Fourth Schedule", [("Third Schedule", "oaths and affirmations"), ("Fifth Schedule", "Scheduled Areas"), ("Second Schedule", "emoluments")],
      "The Fourth Schedule allocates Rajya Sabha seats.", "Rajya Sabha seat allocation is not in the First Schedule (which lists states).")
    F("The 29 subjects devolved to panchayats are listed in the:",
      "Eleventh Schedule", [("Twelfth Schedule", "18 subjects for municipalities"), ("Seventh Schedule", "Union/State/Concurrent lists"),
                            ("Fifth Schedule", "Scheduled Areas")],
      "The Eleventh Schedule (73rd Amendment) has 29 subjects; the Twelfth (74th) has 18.", "Panchayats 29, municipalities 18.", lv="L2")
    M("Schedule", "Content",
      [("Second Schedule", "Emoluments and privileges of constitutional functionaries"), ("Third Schedule", "Forms of oaths and affirmations"),
       ("Fifth Schedule", "Administration of Scheduled Areas and Scheduled Tribes"), ("Ninth Schedule", "Validation of certain Acts and Regulations")],
      "Ninth Schedule — land reform and other laws shielded from challenge (subject to Coelho).", lv="L2")
    C("Arrange the following constitutional changes in chronological order:",
      [("Ninth Schedule added by the First Amendment", 1951, "1951"), ("Sindhi added to the Eighth Schedule (21st Amendment)", 1967, "1967"),
       ("Tenth Schedule added (52nd Amendment)", 1985, "1985"), ("Bodo, Dogri, Maithili and Santhali added (92nd Amendment)", 2003, "2003")],
      "Sindhi (1967) was the first language added after 1950.")
    S("Consider the following statements about the Sixth Schedule:",
      [("It applies to tribal areas in Assam, Meghalaya, Tripura and Mizoram.", True, "Art. 244(2)"),
       ("It applies to Nagaland and Manipur.", False, "Nagaland has Art. 371A; Manipur's hill areas are under Art. 371C, not the Sixth Schedule"),
       ("It provides for Autonomous District Councils.", True, "with legislative, executive and judicial powers")],
      "Only four north-eastern states are covered.")
    A("Laws placed in the Ninth Schedule after 24 April 1973 can be challenged if they violate the basic structure.",
      "The Supreme Court so held in Kesavananda Bharati v. State of Kerala (1973).",
      True, False, False, ["A is true.", "R is false: the holding is from I. R. Coelho (2007); 24 April 1973 is only the date of the Kesavananda judgment used as the cut-off."],
      "24 April 1973 is the date of the Kesavananda Bharati judgment.", ref="I. R. Coelho v. State of Tamil Nadu (2007) 2 SCC 1")
    N("Consider the following statements about the Eighth Schedule:",
      [("It originally contained 14 languages.", True, "14 in 1950"), ("It now contains 22 languages.", True, "after the 92nd Amendment, 2003"),
       ("English is included in it.", False, "English is not in the Eighth Schedule"),
       ("Konkani, Manipuri and Nepali were added by the 71st Amendment.", True, "1992")],
      "English is an official language by Art. 343 read with the Official Languages Act — not an Eighth Schedule language.")
    M("Amendment Act", "Schedule added",
      [("First Amendment", "Ninth Schedule"), ("52nd Amendment", "Tenth Schedule"), ("73rd Amendment", "Eleventh Schedule"),
       ("74th Amendment", "Twelfth Schedule")],
      "73rd = panchayats (11th), 74th = municipalities (12th).", lv="L2")
    A("The Twelfth Schedule contains 18 subjects.",
      "It was added by the 74th Amendment Act.",
      True, True, False, ["Both are true.", "The 74th Amendment inserting the Schedule does not explain why it has 18 subjects."],
      "Origin of a Schedule is not an explanation of its contents.")
    S("Consider the following statements about the Third Schedule:",
      [("It contains the form of oath for Union ministers.", True, "Form I"),
       ("It contains the form of oath for Supreme Court judges and the CAG.", True, "Form IV"),
       ("It contains the form of oath for the President.", False, "the President's oath is in Art. 60; the Vice-President's in Art. 69")],
      "President and VP oaths are in the Articles themselves.", ask="incorrect")
    M("Schedule", "Content",
      [("First Schedule", "Names of states and union territories"), ("Fourth Schedule", "Allocation of Rajya Sabha seats"),
       ("Seventh Schedule", "Union, State and Concurrent Lists"), ("Twelfth Schedule", "Powers of municipalities")],
      "First Schedule also defines state territories.", lv="L2")
    S("Consider the following statements about the Fifth Schedule:",
      [("The President may declare an area to be a Scheduled Area.", True, "para 6"),
       ("A Tribes Advisory Council is to be set up in each state having Scheduled Areas.", True, "para 4"),
       ("The Governor may make regulations for the peace and good government of Scheduled Areas.", True, "para 5(2)")],
      "All three are Fifth Schedule provisions.")

    # ================= Statutory commissions and information oversight =================
    h.topic("gk-statutory-commissions", "RTI Act 2005; Protection of Human Rights Act 1993; Lokpal and Lokayuktas Act 2013; CVC Act 2003")
    F("The Right to Information Act was enacted in:",
      "2005", [("2002", "year of the Freedom of Information Act"), ("2009", "Right to Education Act"), ("1993", "Protection of Human Rights Act")],
      "The RTI Act, 2005 came fully into force on 12 October 2005.", "The Freedom of Information Act, 2002 was never notified and was replaced.")
    F("The National Human Rights Commission was set up under the:",
      "Protection of Human Rights Act, 1993", [("National Commission for Women Act, 1990", "created NCW"),
                                               ("Commissions for Protection of Child Rights Act, 2005", "created NCPCR"),
                                               ("Legal Services Authorities Act, 1987", "created NALSA")],
      "The NHRC was constituted in October 1993 under the PHRA.", "Each commission has its own statute.")
    F("Who was the first Chief Information Commissioner of India?",
      "Wajahat Habibullah", [("Satyananda Mishra", "later CIC"), ("A. N. Tiwari", "later CIC"), ("Shailesh Gandhi", "Information Commissioner, not CIC")],
      "Wajahat Habibullah was the first CIC (2005).", "Shailesh Gandhi was an Information Commissioner.", ref="Central Information Commission — former CICs")
    F("Under the RTI Act, information must normally be provided within:",
      "30 days", [("15 days", "incorrect"), ("45 days", "incorrect"), ("60 days", "incorrect")],
      "Sec. 7(1): within 30 days of the request; within 48 hours where life or liberty is involved.", "48 hours applies only to life/liberty matters.",
      ref="Right to Information Act, 2005, Sec. 7")
    F("The Central Vigilance Commission became a statutory body in:",
      "2003", [("1964", "year it was set up by executive resolution"), ("1988", "Prevention of Corruption Act"), ("2013", "Lokpal Act")],
      "CVC, created in 1964 on the Santhanam Committee's recommendation, got statutory status under the CVC Act, 2003.",
      "1964 is creation, 2003 is statutory status.", lv="L2", ref="Central Vigilance Commission Act, 2003")
    S("Consider the following statements about the Central Information Commission:",
      [("The CJI is a member of the committee that recommends appointments.", False, "the committee is the PM, the LoP in the Lok Sabha and a Union Cabinet Minister nominated by the PM"),
       ("Commissioners are appointed by the President on the recommendation of a committee.", True, "Sec. 12(3)"),
       ("The committee is chaired by the Prime Minister.", True, "Sec. 12(3)")],
      "Unlike the Lokpal, the CIC committee has no judicial member.", ref="Right to Information Act, 2005, Sec. 12")
    M("Body", "Statute",
      [("National Commission for Women", "Act of 1990"), ("National Commission for Protection of Child Rights", "Act of 2005"),
       ("National Commission for Minorities", "Act of 1992"), ("National Green Tribunal", "Act of 2010")],
      "NCW Act 1990 (commission constituted 1992); NCM Act 1992.")
    A("The National Commission for Scheduled Castes is not a statutory body.",
      "It is a constitutional body established under Article 338.",
      True, True, True, "A body created by the Constitution itself is constitutional, not statutory.",
      "Constitutional status is the reason it is not 'statutory'.", ref="Constitution of India, Art. 338")
    S("Consider the following statements about the RTI Act:",
      [("Information concerning the life or liberty of a person must be supplied within 48 hours.", True, "proviso to Sec. 7(1)"),
       ("Applicants below the poverty line are not required to pay the application fee.", True, "Sec. 7(5)"),
       ("Organisations in the Second Schedule are exempt, but information on corruption and human rights violations must still be given.", True, "Sec. 24")],
      "Even exempt security agencies must disclose on corruption/human-rights allegations.", ref="Right to Information Act, 2005")
    C("Arrange the following in chronological order:",
      [("Central Vigilance Commission set up by resolution", 1964, "1964"), ("National Human Rights Commission constituted", 1993, "1993"),
       ("Central Information Commission constituted", 2005, "2005"), ("Lokpal and Lokayuktas Act enacted", 2013, "2013")],
      "CVC (1964) is the oldest of these oversight bodies.")
    N("Consider the following statements about the NHRC:",
      [("Its chairperson can be a former Chief Justice of India or a former Supreme Court judge.", True, "after the 2019 amendment"),
       ("It can take suo motu cognisance of human rights violations.", True, "Sec. 12(a)"),
       ("It can inquire into a matter more than one year after the alleged act.", False, "Sec. 36(2) bars inquiry after one year"),
       ("Its recommendations are binding on the government.", False, "they are recommendatory")],
      "NHRC is recommendatory and subject to a one-year limitation.", ref="Protection of Human Rights Act, 1993")
    A("The Lokpal has jurisdiction over the Prime Minister, subject to certain exclusions.",
      "The Lokpal and Lokayuktas Act, 2013 brings the Prime Minister within its jurisdiction but excludes allegations relating to international relations, security, public order, atomic energy and space.",
      True, True, True, "Sec. 14 includes the PM with specified carve-outs and special procedure.",
      "Inclusion is qualified, not absolute.", ref="Lokpal and Lokayuktas Act, 2013, Sec. 14")
    M("Body", "Basis",
      [("National Commission for Backward Classes", "Article 338B (102nd Amendment)"), ("National Commission for Scheduled Tribes", "Article 338A (89th Amendment)"),
       ("Central Vigilance Commission", "CVC Act, 2003"), ("National Human Rights Commission", "Protection of Human Rights Act, 1993")],
      "NCBC became constitutional only in 2018.")
    S("Consider the following statements about the Lokpal:",
      [("Its first chairperson was Justice Pinaki Chandra Ghose.", True, "appointed in 2019"),
       ("Its members are appointed by the Chief Justice of India.", False, "appointed by the President on the recommendation of a selection committee chaired by the PM"),
       ("At least half of its members must be judicial members.", True, "Sec. 3(2)")],
      "The CJI (or nominee) is only one member of the selection committee.", ref="Lokpal and Lokayuktas Act, 2013")
    A("The tenure and salary of Information Commissioners can now be prescribed by the Central Government.",
      "The RTI (Amendment) Act, 2019 empowered the Centre to prescribe their term and salaries.",
      True, True, True, "Before 2019 these were fixed in the Act itself; the amendment shifted them to rules.",
      "R is the legal change that produced A.", ref="Right to Information (Amendment) Act, 2019")

    # ================= Union ministries and departments =================
    h.topic("gk-union-ministries", "Government of India (Allocation of Business) Rules, 1961 as amended; ministry websites; PIB")
    F("The Ministry of Jal Shakti was formed in:",
      "2019", [("2014", "year the AYUSH ministry was created"), ("2016", "incorrect"), ("2021", "year the Ministry of Cooperation was created")],
      "Jal Shakti was formed in May 2019 by merging two ministries.", "Cooperation is the 2021 ministry.")
    F("The Ministry of Cooperation was created in:",
      "2021", [("2019", "Jal Shakti"), ("2014", "AYUSH"), ("2017", "incorrect")],
      "A separate Ministry of Cooperation was carved out in July 2021.", "Do not confuse with Jal Shakti (2019).")
    F("In 2020 the Ministry of Human Resource Development was renamed as the:",
      "Ministry of Education", [("Ministry of Skill Development and Entrepreneurship", "separate ministry since 2014"),
                                ("Ministry of Youth Affairs and Sports", "separate ministry"), ("Ministry of Culture", "separate ministry")],
      "The MHRD, created in 1985, reverted to the name Ministry of Education in 2020.", "Skill Development is a separate ministry.")
    F("The Central Board of Direct Taxes functions under the:",
      "Department of Revenue", [("Department of Economic Affairs", "budget and macro policy"), ("Department of Expenditure", "public spending"),
                                ("Department of Financial Services", "banks and insurance")],
      "CBDT and CBIC function under the Department of Revenue, Ministry of Finance.", "Economic Affairs prepares the Budget but does not administer taxes.")
    F("The Allocation of Business Rules are made by the President under Article:",
      "77", [("74", "Council of Ministers to aid and advise"), ("75", "appointment of ministers"), ("166", "state counterpart")],
      "Art. 77(3) empowers the President to make rules for allocation of business among ministers.", "Art. 166 is the state equivalent.",
      lv="L2", ref="Constitution of India, Art. 77")
    M("Department", "Ministry",
      [("Department for Promotion of Industry and Internal Trade", "Commerce and Industry"), ("Department of Investment and Public Asset Management", "Finance"),
       ("Department of Military Affairs", "Defence"), ("Department of Food and Public Distribution", "Consumer Affairs, Food and Public Distribution")],
      "DIPAM is under Finance, not Commerce.")
    S("Consider the following statements:",
      [("The Department of Space and the Department of Atomic Energy function under the Prime Minister.", True, "both are placed directly under the PM"),
       ("The Department of Military Affairs is headed by the Chief of Defence Staff as Secretary.", True, "created 2019–20"),
       ("The Department of Atomic Energy was created in 1954.", True, "August 1954")],
      "All three statements are correct.")
    C("Arrange the following ministries in the order of their creation:",
      [("Ministry of Human Resource Development", 1985, "1985"), ("Ministry of Minority Affairs", 2006, "2006"),
       ("Ministry of AYUSH", 2014, "2014"), ("Ministry of Cooperation", 2021, "2021")],
      "Minority Affairs (2006) precedes AYUSH (2014).")
    A("The Ministry of Jal Shakti deals with both water resources and drinking water and sanitation.",
      "It was formed in 2019 by merging the Ministry of Water Resources, River Development and Ganga Rejuvenation with the Ministry of Drinking Water and Sanitation.",
      True, True, True, "The merger is why both portfolios sit in one ministry.", "R directly explains A.")
    S("Consider the following statements about the Allocation of Business Rules:",
      [("They are made by the President under Article 77(3).", True, "Art. 77(3)"),
       ("They are enacted by Parliament as an ordinary law.", False, "they are executive rules, not an Act of Parliament"),
       ("They place the Cabinet Secretariat directly under the Prime Minister.", True, "the Cabinet Secretariat is under the PM")],
      "Rules under Art. 77 are executive instruments.", ref="Constitution of India, Art. 77; Allocation of Business Rules, 1961")
    M("Organisation", "Controlling ministry / department",
      [("Registrar General and Census Commissioner", "Ministry of Home Affairs"), ("Controller General of Accounts", "Department of Expenditure"),
       ("Central Board of Indirect Taxes and Customs", "Department of Revenue"), ("Indian Council of Agricultural Research", "Department of Agricultural Research and Education")],
      "The Census is an MHA function.")
    A("NITI Aayog is not a ministry.",
      "It was set up by a Union Cabinet resolution in January 2015 as a policy think tank replacing the Planning Commission.",
      True, True, True, "Being created by resolution as an advisory body explains why it is not a ministry.",
      "Neither the Planning Commission nor NITI Aayog is constitutional or statutory.", ref="Cabinet Resolution, 1 January 2015")
    S("Consider the following statements:",
      [("The India Meteorological Department functions under the Ministry of Earth Sciences.", True, "IMD is under MoES"),
       ("The Survey of India functions under the Department of Science and Technology.", True, "SoI is under DST"),
       ("The Geological Survey of India functions under the Ministry of Mines.", True, "GSI is under Mines")],
      "All three attachments are correct.")
    M("Organisation", "Ministry",
      [("Archaeological Survey of India", "Culture"), ("Botanical Survey of India", "Environment, Forest and Climate Change"),
       ("National Statistics Office", "Statistics and Programme Implementation"), ("Press Information Bureau", "Information and Broadcasting")],
      "BSI and ZSI are under MoEFCC, not Culture.", lv="L2")
    A("The Department of Personnel and Training is the cadre-controlling authority for the IAS.",
      "The Department of Personnel and Training is part of the Ministry of Personnel, Public Grievances and Pensions.",
      True, True, False, ["Both statements are true.", "Being in a particular ministry does not explain why DoPT controls the IAS cadre; that follows from the Allocation of Business Rules."],
      "Organisational location is not the reason for a function.")

    # ================= Union-State relations and the legislative lists =================
    h.topic("gk-union-state-relations", "Constitution of India, Part XI and Seventh Schedule; M. Laxmikanth, 'Indian Polity'")
    F("Under the Constitution, residuary powers of legislation are vested in:",
      "Parliament", [("State legislatures", "the US model, not India's"), ("Parliament and states jointly", "applies to Concurrent List, not residuary"),
                     ("The President", "not a legislative authority for residuary matters")],
      "Art. 248 and Entry 97 of List I vest residuary power in Parliament.", "The US vests residuary powers in the states — the opposite.",
      ref="Constitution of India, Art. 248")
    F("'Police' is a subject in the:",
      "State List", [("Union List", "incorrect"), ("Concurrent List", "incorrect"), ("Residuary powers", "incorrect")],
      "Police and public order are State List subjects (List II, Entries 1–2).", "Central armed police forces are a Union matter, but 'police' is a state subject.",
      ref="Constitution of India, Seventh Schedule, List II")
    F("The Inter-State Council is provided for under Article:",
      "263", [("262", "inter-state water disputes"), ("280", "Finance Commission"), ("356", "President's Rule")],
      "Art. 263 allows the President to establish an Inter-State Council; it was set up in 1990.", "Art. 262 is water disputes.",
      ref="Constitution of India, Art. 263")
    F("Education was transferred from the State List to the Concurrent List by the:",
      "42nd Amendment Act, 1976", [("44th Amendment Act, 1978", "restored civil liberties"), ("73rd Amendment Act, 1992", "panchayats"),
                                   ("86th Amendment Act, 2002", "right to education")],
      "The 42nd Amendment moved five subjects, including education, to the Concurrent List.", "86th made education a Fundamental Right — different change.",
      ref="Constitution (42nd Amendment) Act, 1976")
    F("'Banking' is a subject in the:",
      "Union List", [("State List", "incorrect"), ("Concurrent List", "incorrect"), ("None of the three lists", "incorrect")],
      "Banking is Entry 45 of List I.", "Cooperative societies are a state subject, but banking is Union.", lv="L2",
      ref="Constitution of India, Seventh Schedule, List I")
    N("Consider the following pairs (subject — list):",
      [("Forests — Concurrent List", True, "moved by the 42nd Amendment"), ("Prisons — State List", True, "List II"),
       ("Stock exchanges — Union List", True, "List I"), ("Marriage and divorce — State List", False, "it is in the Concurrent List")],
      "Personal law matters are concurrent.", pairs=True, ref="Constitution of India, Seventh Schedule")
    S("Consider the following statements about Article 249:",
      [("The Rajya Sabha may pass a resolution, supported by two-thirds of members present and voting, allowing Parliament to legislate on a State List matter.", True, "national interest"),
       ("Such a resolution remains in force for up to one year and may be renewed.", True, "renewable for one year at a time"),
       ("A concurring resolution of the Lok Sabha is also required.", False, "only the Rajya Sabha passes the resolution")],
      "Art. 249 is a Rajya Sabha-specific power.", ref="Constitution of India, Art. 249")
    A("Ordinarily, when a central law and a state law on a Concurrent List subject conflict, the central law prevails.",
      "Article 254 so provides, except where the state law has been reserved for and received the President's assent.",
      True, True, True, "Art. 254 lays down the repugnancy rule and its exception.", "The exception is why A says 'ordinarily'.",
      ref="Constitution of India, Art. 254")
    M("Commission / document", "Description",
      [("Sarkaria Commission", "Set up in 1983; led to the Inter-State Council"), ("Punchhi Commission", "Second commission on Centre–State relations, 2007"),
       ("Rajamannar Committee", "Appointed by the Tamil Nadu government in 1969"), ("Anandpur Sahib Resolution", "Adopted by the Shiromani Akali Dal in 1973")],
      "Rajamannar was a state-appointed committee, unlike Sarkaria and Punchhi.")
    N("Consider the following subjects and state how many were transferred from the State List to the Concurrent List by the 42nd Amendment:",
      [("Forests", True, "transferred"), ("Weights and measures", True, "transferred"), ("Protection of wild animals and birds", True, "transferred"),
       ("Agriculture", False, "agriculture remains in the State List")],
      "The five transferred subjects were education, forests, weights and measures, wildlife protection and administration of justice.",
      ref="Constitution (42nd Amendment) Act, 1976")
    C("Arrange the following in chronological order:",
      [("States Reorganisation Act providing for Zonal Councils", 1956, "1956"), ("Rajamannar Committee", 1969, "1969"),
       ("Sarkaria Commission", 1983, "1983"), ("Inter-State Council set up", 1990, "1990")],
      "The Inter-State Council followed the Sarkaria recommendation.")
    A("Parliament can legislate on a State List subject to implement an international treaty.",
      "Article 253 empowers Parliament to make any law for implementing treaties, agreements or conventions with other countries.",
      True, True, True, "Art. 253 overrides the list division for treaty implementation.", "R is the constitutional basis for A.",
      ref="Constitution of India, Art. 253")
    S("Consider the following statements:",
      [("Zonal Councils are statutory bodies set up under the States Reorganisation Act, 1956.", True, "five zonal councils"),
       ("The Union Home Minister is the chairman of each Zonal Council.", True, "by the Act"),
       ("The North Eastern Council was set up under a separate Act of 1971.", True, "NEC Act, 1971")],
      "All three are correct.", ref="States Reorganisation Act, 1956; North Eastern Council Act, 1971")
    A("The GST Council is a statutory body created under the Central Goods and Services Tax Act, 2017.",
      "Article 279A, inserted by the 101st Amendment Act, 2016, provides for the GST Council.",
      False, True, False, ["A is false: the Council is constitutional, created under Art. 279A, not by the CGST Act.", "R is true."],
      "Constitutional vs statutory origin.",
      ref="Constitution of India, Art. 279A")
    S("Consider the following statements about Article 252:",
      [("A law passed by Parliament at the request of two or more states applies to those states and to any state that later adopts it.", True, "Art. 252(1)"),
       ("Such a law can be amended or repealed only by Parliament.", True, "Art. 252(2)"),
       ("An adopting state can amend such a law by its own legislation.", False, "state legislatures cannot amend or repeal it")],
      "Once states surrender the field, only Parliament can change the law.", ask="incorrect", ref="Constitution of India, Art. 252")
