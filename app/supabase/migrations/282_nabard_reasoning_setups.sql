-- Migration 282: restore the missing puzzle setups to 66 NABARD Reasoning stems.
-- Five more cannot be restored and stay needs_correction; see the end.
--
-- Same defect and same fix as migration 280. Twenty-one Reasoning direction
-- blocks carry the setup their questions depend on -- a seating
-- arrangement, a floor puzzle, a family description, a route, the sample
-- sentences of a coded language. None reached the import, so 66 stems ask
-- "Who is sitting on the immediate left of Ginni?" with no Ginni anywhere.
--
-- Every block below is the source direction block verbatim, from its header
-- to the first question marker of its range, page-footer lines dropped and
-- whitespace collapsed to single spaces. Nothing is invented.
--
-- THE COUNT IS 66, NOT 50. The earlier survey put Reasoning at 50 because
-- it only counted direction blocks over 350 characters. That threshold
-- silently dropped every short setup that is nonetheless load-bearing: the
-- two-line family description behind 2020 Q.9-10, the coded-language
-- samples behind 2020 Q.15-17 and 2021 Q.16-17, Mr Wasan's route behind
-- 2022 Q.6. Sixteen more rows, found by reading all 33 Reasoning blocks and
-- classifying each as setup or bare instruction rather than by length.
--
-- One range in the source is printed too narrowly and was widened
-- deliberately. 2021 prints "(Instruction for Q.11)" over the five-plays
-- schedule, but Q.12 ("Which play is to be performed on Monday?") is
-- plainly the same puzzle, so the block is attached to Q.11 and Q.12.
--
-- Twelve of the 33 blocks are bare instructions with no setup -- "assuming
-- the given statements to be true, find which of the following options
-- holds true" -- and are correctly absent from the import. They are not
-- touched.
--
-- ROW COUNTS BY PAPER:
--   NABARD-P1-REASONING-2020              14
--   NABARD-P1-REASONING-2021              14
--   NABARD-P1-REASONING-2022-EVENING      10
--   NABARD-P1-REASONING-2022-MORNING      16
--   NABARD-P1-REASONING-2023              12
--
-- PROJECTION RE-SYNC. question_text changes the content hash, so any
-- projection of these rows goes stale. All five papers above need a re-sync
-- if projected. Unlike the RBI rows in migration 281 these are all
-- reviewer_status pending, so nothing here is in front of a learner either
-- before or after.
--
-- THE 21 SETUP BLOCKS, verbatim as prepended:
--
-- REA-2023 18af Q.1-1  (1 rows) -- the family description and its symbol legend
--   I.1) Directions: Study the following information carefully and answer
--   the questions given beside. A, B, C, D, E, F, and G are family members,
--   and there are two married couples in two generations of people who live
--   in the same house. A is the father of the spouse of C. F is the
--   maternal uncle of G, who is not a male. A is the brother-in-law of F. D
--   and G are sisters of each other. E is the son of B. C is a feminine
--   gender.
--
-- REA-2023 18af Q.2-5  (4 rows) -- the seven individuals with birth months and cities
--   I.2-5) Direction: Study the information and answer the following
--   questions. Seven individuals, X, Y, Z, M, N, O, and H, were born in
--   different months, namely, January, February, April, July, August,
--   September, and December of the same year. They were also born in seven
--   different cities: Indore, Jaipur, Lucknow, Patna, Pune, Surat, and
--   Varanasi. M was born in Pune in a month having less than 31 days. Two
--   persons were born between M and N, who was not born in Lucknow. Three
--   persons were born between X and H, who was born after M. O was born
--   before Y, who was born in Patna. The individual born in Surat was born
--   before the one born in Varanasi, none of them was born in April.
--   Neither O nor H was born in Lucknow or Varanasi. O was born after Z,
--   who was born in Jaipur. The one born in Indore was born in a month with
--   31 days. The individual born in Indore was born immediately before the
--   one born in Surat.
--
-- REA-2023 18af Q.8-10  (3 rows) -- the six-person weight ordering
--   I.8-10) Direction: Study the information carefully and answer the
--   following question. Among the six persons X, Y, Z, M, N, and O, each
--   has a different weight. X is heavier than 3 persons, Z is lighter than
--   M. N is lighter than only Y. Z is not the lightest. The second heaviest
--   person weighs 56 kg, and the second lightest person weighs 28 kg.
--
-- REA-2023 18af Q.16-19  (4 rows) -- the eight-person circular seating with colours
--   I.16-19) Direction: Study the following information carefully to answer
--   the given question. Eight individuals M, N, O, P, Q, R, S, and T are
--   sitting around a circular table facing the table, butnot necessarily in
--   the same order. Each of them has a preference for a different color:
--   lavender, maroon, cyan, emerald, navy, ebony, amber, and ivory, but not
--   necessarily in the same order. The one who favors cyan sits to the
--   immediate left of the person who likes ebony. S does not like ivory. Q
--   sits third to the left of M, who likes lavender, and the individual who
--   likes lavender sits to the immediate left of R. P sits to the immediate
--   right of O, and neither of them prefers emerald. The one who likes
--   maroon and T has two people sitting between them. P, Q, and R, none of
--   them has a liking for maroon. Q and the person who prefers emerald have
--   one person in between them. S sits second to the right of N. O sits
--   opposite the person who likes ivory, and the individual who likes ivory
--   sits immediately next to the one who enjoys navy.
--
-- REA-2022 250d Q.5-5  (1 rows) -- the family description
--   (Instruction for Q.5) Study the following information carefully and
--   answer the questions below: A is sister of B, who is the wife of C. D
--   and E are the daughters of B. F is the son of A and G is the wife of
--   A’s only son. H is married to E and K is a daughter of H. I is the
--   sister of J, who is the son of G.
--
-- REA-2022 250d Q.6-6  (1 rows) -- Mr Wasan's route
--   (Instruction for Q.6) Study the following information carefully and
--   answer the questions below: Mr. Wasan goes 17km in east and reached
--   point Y, then he takes a right turn and goes 52km to reach point Z.
--   Then he takes a left turn and goes 7km and reached point R. Again he
--   takes a left turn and goes 24km and reached point S.
--
-- REA-2022 250d Q.7-10  (4 rows) -- the row of persons with their cricket scores
--   (Instructions for Q.7 to Q.10) Read the following information carefully
--   and answer the questions given below it: There are certain number of
--   persons sitting in a row and all were facing South and all of them
--   scored different runs in a cricket match viz. 20, 27, 33, 38, 40, 43,
--   45 and 50 but not necessarily in the same order. D scored the lowest
--   runs. A is in the middle of the row. B is fifth to the right of C. Two
--   persons sit between D and E who is five places away from F. G scored
--   43. The sum of runs of G and E is equal to sum of runs scored by D and
--   H. One among the four scored the highest runs and one among the four
--   scored the lowest runs. G is third from one of the extreme ends but is
--   not sitting between B and C. G scored more runs than A but less than F.
--   C is at one of the extreme end. H sits to the immediate left of G.
--   Three people sit between E and A who is an immediate right of F. Number
--   of persons between E and A are same as number of persons between A and
--   B. The difference between the runs scored by D and B is equal to the
--   difference between the runs scored by E and C.
--
-- REA-2022 250d Q.11-14  (4 rows) -- the eight friends with birth months and cities
--   (Instruction for Q.11 to Q.14) Read the given information carefully and
--   answer the questions given below: Eight friends namely G, O, T, L, M,
--   K, A and R were born in different months among January, March, April,
--   July, September and November. Three persons were born in same month.
--   Each of them is from different Cities viz. Kolkata, Patna, Nainital,
--   Agra, Lucknow, Dehradun, Pune and Ranchi. All the above information is
--   not necessarily in the same order. The one who is from Dehradun was
--   born in the month having less than 31 days. T is from Kolkata. G and M
--   were born in same month. Persons who is from Agra and Patna were born
--   in November. L is from Lucknow and he was born in the month having 31
--   days but not in March. R is from Ranchi and he was born in April. The
--   one who is from Kolkata was born in the month having 30 days after July
--   but before November. The one who is from Pune was born in month having
--   31 days before April. K was born in July and he is from Nainital. A is
--   from Agra and M is not from Patna.
--
-- REA-2022 250d Q.15-17  (3 rows) -- the seven friends with animated movies and presentation subjects
--   (Instructions for Q.15 to Q.17) Study the following information and
--   answer the questions. Seven friends, namely L, M, N, O, P, Q and R,
--   like different animated movies, namely Finding Nemo, Rio, Frozen, Up,
--   Lion King, Shrek and Cars, but not necessarily in the same order. Each
--   friend also has a presentation on topics of different subjects, namely
--   Civics, History, English, Geography, Chemistry, Physics and Biology but
--   not necessarily in the same order. Q has a presentation on Civics and
--   likes neither Frozen nor Up. The one who likes Finding Nemo has a
--   presentation on History. L likes Rio and has a presentation neither on
--   Geography nor on Chemistry. The one who likes Cars has a presentation
--   on Biology. M has a presentation on Physics and does not like Up. The
--   one who likes Up does not have a presentation on Chemistry. O likes
--   Lion King. R does not have a presentation on History and does not like
--   Up. P does not like Up.
--
-- REA-2022 250d Q.18-20  (3 rows) -- the nine college friends and their three project groups
--   (Instructions for Q.18 to Q.20) Study the following information
--   carefully and answer the questions given below: F, G, H, I, J, K, L, M
--   and N are nine college friends in which K, L, M and N are boys and the
--   remaining five are girls. They are divided into three groups, viz, A, B
--   and C, for three projects. There must be at least three persons with at
--   least one boy in each group. F and L are in the same group. M is in the
--   group which consists of either F or I or both, but M must be in group
--   A. F and G cannot work on the same project. K and J work on the same
--   project. Both G and J are in the same group. I, H and J are members of
--   different groups. J must be in group B. M and L can't be in the same
--   group.
--
-- REA-2020 4c61 Q.1-5  (5 rows) -- circular seating of eight persons with their cities
--   (Instructions for Q.1 to Q.5) Study the following information carefully
--   and answer the questions given below: Eight persons – Rekha, Shubhi,
--   Reeta, Sana, Gudia, Kavya, Nandini and Ginni, were sitting in a circle
--   facing towards the center. Each of them was born in a different city —
--   Chandigarh, Manali, Amritsar, Jaipur, Bihar, Goa, Mumbai and Bangalore,
--   but not necessarily in the same order. Two persons were sitting between
--   the one, who was born in Jaipur and Gudia. Rekha was born in Chandigarh
--   and sits opposite to Gudia. The one, who was born in Bihar, sits
--   opposite to Sana. Ginni was born in Mumbai and sits second to the right
--   of the one, who was born in Jaipur. Reeta was born in Bihar and was an
--   immediate neighbour of the one, who was born in Goa. Nandini sits third
--   right to Shubhi. Sana was born in Jaipur. The one, who was born in
--   Bangalore, sits adjacent to the one, who was born in Jaipur. Gudia was
--   born in Manali and Nandini was born in Bangalore.
--
-- REA-2020 4c61 Q.9-10  (2 rows) -- the family description
--   (Instructions for Q.9 and Q.10) Study the following information
--   carefully and answer the questions given below: In a family, P is the
--   wife of Q. Q is the father of only R and S. T is the daughter-in-law of
--   P. T has only two children U and V. V is the daughter in law of W. U is
--   the aunt of X. X is the daughter of Y. R is unmarried.
--
-- REA-2020 4c61 Q.11-14  (4 rows) -- the nine-person linear row with colours
--   (Instructions for Q.11 to Q.14) Answer the questions based on the
--   information given below: Nine persons P, Q, R, S, T, U, V, W and X are
--   sitting in a linear table and facing the north direction but not
--   necessarily in the same order. Each one of them likes different colours
--   i.e. Blue, Grey, Yellow, Pink, Black, Green, Brown, Red and Orange but
--   not necessarily in the same order. Two persons sit between X and V who
--   does not like Yellow. W sits just to the right of R. One person sits
--   between W and P. R likes Yellow. Two persons sit between the one who
--   likes Black and the one who likes Red. Q likes Black but he does not
--   sit just to the right of W. Three persons sit between X and the one who
--   likes Pink. X sits on an even position from the left end. The one who
--   likes Yellow sits just to the left of the one who likes Pink. The one
--   who likes the Blue color sits just to the right of T. V does not likes
--   Blue color. S likes Grey and T likes Orange color. The one who likes
--   Brown sits immediate left to the V.
--
-- REA-2020 4c61 Q.15-17  (3 rows) -- the coded-language sample sentences
--   (Instruction for Q.15 to Q.17) Study the following information
--   carefully and answer the given questions: In a certain code language,
--   ‘while the challenges explaining’ is written as ‘kue cdw prc bfa’, ‘in
--   investigating terrorism while’ is written as ‘prc jpa pbz ngs’ ‘related
--   the challenges in’ is written as ‘ngs cdw itg kue‘
--
-- REA-2022 5d4d Q.6-9  (4 rows) -- the ten-person two-row seating
--   (Instruction for Q.6 to Q.9) Study the following information carefully
--   and answer the question given below: Ten persons Vaibhav, Sumit, Raman,
--   Pawan, Naman, Dev, Girish, Hitesh, Karan and Naresh are sitting in two
--   parallel rows. Row 1 is facing south and row 2 is facing north.
--   Vaibhav, Sumit, Raman, Pawan and Naman are facing south. Each person of
--   row 1 is facing the other person of row 2. (i) Naresh sits third to the
--   right of Girish. (ii) Dev sits second to the left of Naresh. Dev faces
--   the one who sits on the immediate right of Sumit. (iii) Only one person
--   sits between Pawan and Sumit. (iv) Vaibhav is not an immediate
--   neighbour of Sumit. (v) Only one person sits between Raman and Naman.
--   Naman does not face Dev. (vi) Hitesh is not an immediate neighbour of
--   Girish. (vii) Only two persons sit between Karan and Hitesh.
--
-- REA-2022 5d4d Q.13-16  (4 rows) -- the colour-coding sample phrases
--   (Instruction for Q.13 to Q.16) Read the following information carefully
--   and answer the questions given below. “Purple Black Green Pink” is
--   written as “Sk Rk Tk Nk”, “Green Brown Mustard Orange” is written as
--   “Pk Gk Sk Fk”, “Mustard Black White Red” is written as “Nk Mk Pk Vk”,
--   “White Red Purple Violet” is written as “Vk Mk Rk Dk”
--
-- REA-2022 5d4d Q.17-18  (2 rows) -- the point-to-point distances and directions
--   (Instructions for Q.17 and Q.18) Study the following information
--   carefully and answer the given questions: The distance from point T to
--   point S, which is in its south, is 9 metres. The distance from point U
--   to point T, which is in its east, is 11 metres. The distance from point
--   X to point W, which is in its north, is 4 metres. The distance from
--   point V to point U, which is in its north, is 5 metres. The distance
--   between point W and point V is 15 metres and point V is in its west.
--   The distance between point Y and the point W, where W is in its south,
--   is 5 metres.
--
-- REA-2021 9afd Q.1-5  (5 rows) -- the seven-floor hostel puzzle with home states
--   (Instructions for Q.1 to Q.5) Study the information given below and
--   answer the questions based on it. Seven friends namely – Ramesh,
--   Rajesh, Jayesh, Viresh, Tapesh, Lovish and Ishant – live in a hostel
--   having seven floors. All chose to stay on different floors of the
--   hostel building (numbered 1 to 7) but not necessarily in the same
--   order. They all have come from different states – Odisha, Gujarat,
--   Assam, Goa, Kerala, Delhi and Bihar but not in the same order. Rajesh
--   chose third floor and is from Gujarat. Viresh has chosen the floor
--   immediately below the floor which Tapesh has chosen and immediately
--   above the floor which Jayesh has chosen. There is only one floor
--   between the floors which Rajesh and Lovish have chosen. Viresh has not
--   come from Kerala. The one who chose the top floor has come from Bihar.
--   There is only one floor between the floor which Jayesh has chosen and
--   the one who is from Odisha. The one who is from Delhi has chosen the
--   floor immediately above the floor which the one from Kerala has chosen.
--   The one who is from Goa has not chosen the floor below the one from
--   Odisha.
--
-- REA-2021 9afd Q.6-10  (5 rows) -- the twelve-person two-row seating
--   (Instructions for Q.6 to Q.10) Read the given information carefully and
--   answer the questions: Twelve Persons are sitting in two parallel rows -
--   Q, R, S, T, U and V are sitting in row 1 facing south and P, O, J, W, X
--   and Y are sitting in row 2 facing north. W sits third to the left of P.
--   V does not face P. Neither W nor P sits at extreme ends. O sits at one
--   of the extreme ends. Only two people sit between O and X. V is not an
--   immediate neighbour of U. X does not face V. Two persons sit between R
--   and S. V does not sit at any of the extreme ends. U faces W. S is not
--   an immediate neighbour of U. Q does not face P. J sits left of Y.
--
-- REA-2021 9afd Q.11-12  (2 rows) -- the five-plays Monday-to-Friday schedule
--   (Instruction for Q.11) There are five plays that are to be performed
--   from Monday to Friday. One play is to be performed each day. C is to be
--   performed immediately after D but not on Thursday. Three plays are to
--   be performed between Z and A. A is not be performed at last. N is one
--   of the plays.
--
-- REA-2021 9afd Q.16-17  (2 rows) -- the coded-language sample sentences
--   (Instructions for Q.16 and Q.17) Study the following information
--   carefully and answer the questions given below. In a certain code
--   language, ‘messy room looks bad’ is coded as ‘la ja ta sa’, ‘senior
--   room bad’ is coded as ‘sa ty ta’. ‘messy room feels dirty’ is coded as
--   ‘ja sa op nm’ ‘water save dirty’ is coded as ‘op vs rt’
--
-- BEFORE AND AFTER, the 66 rows. BEFORE is the stem as loaded; AFTER is its block
-- above, a blank line, then that same stem unchanged.
--   REA-2023-Q001    18af  +  427ch  'Q.1) How is D related to C?'
--   REA-2023-Q002    18af  +  913ch  'Q.2) Who among the following was born in April?'
--   REA-2023-Q003    18af  +  913ch  'Q.3) Who among the following was born immediately before'
--   REA-2023-Q004    18af  +  913ch  'Q.4) Four of the five are alike in a certain way and hen'
--   REA-2023-Q005    18af  +  913ch  'Q.5) Which of the following combination is correct?'
--   REA-2023-Q008    18af  +  345ch  'Q.8) Who among the person weighs 56 kg?'
--   REA-2023-Q009    18af  +  345ch  'Q.9) How many persons are lighter than M?'
--   REA-2023-Q010    18af  +  345ch  'Q.10) What is the possible weight of O?'
--   REA-2023-Q016    18af  + 1037ch  'Q.16) Which color does R like?'
--   REA-2023-Q017    18af  + 1037ch  'Q.17) Who among the following is an immediate neighbor o'
--   REA-2023-Q018    18af  + 1037ch  'Q.18) How many persons are sitting between P and the per'
--   REA-2023-Q019    18af  + 1037ch  'Q.19) Which person is sitting opposite the person who li'
--   REA-2022-Q005    250d  +  309ch  'Q.5) How C is related to F?'
--   REA-2022-Q006    250d  +  327ch  'Q.6) What is the shortest possible distance between the '
--   REA-2022-Q007    250d  + 1097ch  'Q.7) How many persons are sitting in the row?'
--   REA-2022-Q008    250d  + 1097ch  'Q.8) What is the sum of runs scored by C and H?'
--   REA-2022-Q009    250d  + 1097ch  'Q.9) How many persons sit between E and C?'
--   REA-2022-Q010    250d  + 1097ch  'Q.10) Who among the following scored the highest runs?'
--   REA-2022-Q011    250d  + 1020ch  'Q.11) Who among the following was born in the month of N'
--   REA-2022-Q012    250d  + 1020ch  'Q.12) Who among the following persons was born in the mo'
--   REA-2022-Q013    250d  + 1020ch  'Q.13) Who among the following persons is from Pune?'
--   REA-2022-Q014    250d  + 1020ch  'Q.14) Which among the following statements is definitely'
--   REA-2022-Q015    250d  +  931ch  'Q.15) On which of the following subjects does P have a p'
--   REA-2022-Q016    250d  +  931ch  'Q.16) Four of the following five form a group as per the'
--   REA-2022-Q017    250d  +  931ch  'Q.17) Which of the following combinations is definitely '
--   REA-2022-Q018    250d  +  709ch  'Q.18) Which of the following groups consists of two male'
--   REA-2022-Q019    250d  +  709ch  'Q.19) Which of the following pairs cannot be the members'
--   REA-2022-Q020    250d  +  709ch  'Q.20) Which of the following are the members of group C?'
--   REA-2020-Q001    4c61  +  968ch  'Q.1) Who is sitting on the immediate left of Ginni?'
--   REA-2020-Q002    4c61  +  968ch  'Q.2) How many persons sit between Kavya and Sana, with l'
--   REA-2020-Q003    4c61  +  968ch  'Q.3) Kavya belongs to which city among the following?'
--   REA-2020-Q004    4c61  +  968ch  'Q.4) Who is an immediate neighbour of Gudia and Kavya?'
--   REA-2020-Q005    4c61  +  968ch  'Q.5) Who is sitting on the third left of Ginni?'
--   REA-2020-Q009    4c61  +  334ch  'Q.9) How is W related to X?'
--   REA-2020-Q010    4c61  +  334ch  'Q.10) How is V related to P?'
--   REA-2020-Q011    4c61  + 1012ch  'Q.11) What is the position of S, according to U in the a'
--   REA-2020-Q012    4c61  + 1012ch  'Q.12) Q is an immediate neighbour of whom among the foll'
--   REA-2020-Q013    4c61  + 1012ch  'Q.13) How many persons are sitting between the one who l'
--   REA-2020-Q014    4c61  + 1012ch  'Q.14) Which pair is an immediate neighbour of each other'
--   REA-2020-Q015    4c61  +  328ch  'Q.15) What is the code for ‘investigating’?'
--   REA-2020-Q016    4c61  +  328ch  'Q.16)‘while in related’ can be coded as'
--   REA-2020-Q017    4c61  +  328ch  'Q.17) What does ‘cdw’ stand for?'
--   REA-2022-Q006    5d4d  +  830ch  'Q.6) Who among the following faces Pawan?'
--   REA-2022-Q007    5d4d  +  830ch  'Q.7) How many persons are there between Karan and Dev?'
--   REA-2022-Q008    5d4d  +  830ch  'Q.8)Which of the following statement is true?'
--   REA-2022-Q009    5d4d  +  830ch  'Q.9) What is the position of Karan with respect to Dev?'
--   REA-2022-Q013    5d4d  +  333ch  'Q.13) What will be the code for “White”?'
--   REA-2022-Q014    5d4d  +  333ch  'Q.14) If Orange is written as “Gk”, then what will be th'
--   REA-2022-Q015    5d4d  +  333ch  'Q.15) The codes “Rk Sk Nk” may represent which of the fo'
--   REA-2022-Q016    5d4d  +  333ch  'Q.16) What does the code “Fk” represents?'
--   REA-2022-Q017    5d4d  +  570ch  'Q.17) Which of the following three points are in a strai'
--   REA-2022-Q018    5d4d  +  570ch  'Q.18) What is the distance between points U and Y?'
--   REA-2021-Q001    9afd  + 1101ch  'Q.1) Ramesh is from which of the following states?'
--   REA-2021-Q002    9afd  + 1101ch  'Q.2) Which of the following combination is true regardin'
--   REA-2021-Q003    9afd  + 1101ch  'Q.3) If Lovish is related to Odisha, Rajesh is related t'
--   REA-2021-Q004    9afd  + 1101ch  'Q.4) The one who is from Goa lives on which of the follo'
--   REA-2021-Q005    9afd  + 1101ch  'Q.5) Which statement is not correct according to given i'
--   REA-2021-Q006    9afd  +  637ch  'Q.6) Who among the following sits diagonally opposite to'
--   REA-2021-Q007    9afd  +  637ch  'Q.7) Who among the following sits third to the left of U'
--   REA-2021-Q008    9afd  +  637ch  'Q.8) Who among the following faces X?'
--   REA-2021-Q009    9afd  +  637ch  'Q.9) Four of the following five form a group, which amon'
--   REA-2021-Q010    9afd  +  637ch  'Q.10) How many persons sit between Y and J?'
--   REA-2021-Q011    9afd  +  296ch  'Q.11) On which day play N is to be performed?'
--   REA-2021-Q012    9afd  +  296ch  'Q.12) Which play is to be performed on Monday?'
--   REA-2021-Q016    9afd  +  327ch  'Q.16) What is the code for ‘Dirty’?'
--   REA-2021-Q017    9afd  +  327ch  'Q.17) Which word is coded as ‘ja’?'
--
-- NOT REPAIRABLE -- NABARD-P1-REASONING-2022-EVENING Q.1-5, the floor-and-
-- flat puzzle. The compendium prints "Evening Shift:" and goes straight
-- into Q.1; there is no direction block and no setup anywhere in the
-- source. Those five stay needs_correction.
--
-- The answer explanations for that set DO print the solved grid --
-- "E(English) H(Science) 1 C(Mathematics) D(Polity)" -- and migration 278
-- did recover DI values from explanations. This is not the same case and
-- the grid was deliberately not used. There, the explanations restated the
-- question's PREMISE. Here the grid is the ANSWER: prepending it would hand
-- the learner every answer in the set, and reconstructing a premise that
-- yields it would be invention. So the set stays flagged.
--   REA-2022-Q001    5d4d  'Q.1) The one who likes Civics lives just above to ____ and b'
--   REA-2022-Q002    5d4d  'Q.2) Who lives immediately below B’s flat?'
--   REA-2022-Q003    5d4d  'Q.3) Which of the following statements is/are true regarding'
--   REA-2022-Q004    5d4d  'Q.4) Four of the following five are alike in a certain way a'
--   REA-2022-Q005    5d4d  'Q.5) Who among the following persons is/are living in Flat X'
--
-- Guarded on the current value: a no-op if the row has already been
-- repaired.

BEGIN;

UPDATE public.pyq_questions q
SET question_text = v.question_text
FROM (VALUES
  ('8b95a6d7-7a04-42e8-ae38-c121ffab69a0'::uuid,
   'I.1) Directions: Study the following information carefully and answer the questions given beside. A, B, C, D, E, F, and G are family members, and there are two married couples in two generations of people who live in the same house. A is the father of the spouse of C. F is the maternal uncle of G, who is not a male. A is the brother-in-law of F. D and G are sisters of each other. E is the son of B. C is a feminine gender.

Q.1) How is D related to C?'),
  ('d97bb2f1-a71a-4328-b0b0-4e24a335b8ac'::uuid,
   'I.2-5) Direction: Study the information and answer the following questions. Seven individuals, X, Y, Z, M, N, O, and H, were born in different months, namely, January, February, April, July, August, September, and December of the same year. They were also born in seven different cities: Indore, Jaipur, Lucknow, Patna, Pune, Surat, and Varanasi. M was born in Pune in a month having less than 31 days. Two persons were born between M and N, who was not born in Lucknow. Three persons were born between X and H, who was born after M. O was born before Y, who was born in Patna. The individual born in Surat was born before the one born in Varanasi, none of them was born in April. Neither O nor H was born in Lucknow or Varanasi. O was born after Z, who was born in Jaipur. The one born in Indore was born in a month with 31 days. The individual born in Indore was born immediately before the one born in Surat.

Q.2) Who among the following was born in April?'),
  ('aec50a66-6abd-45f8-9566-197544e24960'::uuid,
   'I.2-5) Direction: Study the information and answer the following questions. Seven individuals, X, Y, Z, M, N, O, and H, were born in different months, namely, January, February, April, July, August, September, and December of the same year. They were also born in seven different cities: Indore, Jaipur, Lucknow, Patna, Pune, Surat, and Varanasi. M was born in Pune in a month having less than 31 days. Two persons were born between M and N, who was not born in Lucknow. Three persons were born between X and H, who was born after M. O was born before Y, who was born in Patna. The individual born in Surat was born before the one born in Varanasi, none of them was born in April. Neither O nor H was born in Lucknow or Varanasi. O was born after Z, who was born in Jaipur. The one born in Indore was born in a month with 31 days. The individual born in Indore was born immediately before the one born in Surat.

Q.3) Who among the following was born immediately before the one who was born in Indore?'),
  ('f5965424-28e4-4b94-8dc6-93e60ad6e048'::uuid,
   'I.2-5) Direction: Study the information and answer the following questions. Seven individuals, X, Y, Z, M, N, O, and H, were born in different months, namely, January, February, April, July, August, September, and December of the same year. They were also born in seven different cities: Indore, Jaipur, Lucknow, Patna, Pune, Surat, and Varanasi. M was born in Pune in a month having less than 31 days. Two persons were born between M and N, who was not born in Lucknow. Three persons were born between X and H, who was born after M. O was born before Y, who was born in Patna. The individual born in Surat was born before the one born in Varanasi, none of them was born in April. Neither O nor H was born in Lucknow or Varanasi. O was born after Z, who was born in Jaipur. The one born in Indore was born in a month with 31 days. The individual born in Indore was born immediately before the one born in Surat.

Q.4) Four of the five are alike in a certain way and hence form a group, who among the following does not belong to that group?'),
  ('ca1f82d3-94e5-4ce1-957f-35f9e5310994'::uuid,
   'I.2-5) Direction: Study the information and answer the following questions. Seven individuals, X, Y, Z, M, N, O, and H, were born in different months, namely, January, February, April, July, August, September, and December of the same year. They were also born in seven different cities: Indore, Jaipur, Lucknow, Patna, Pune, Surat, and Varanasi. M was born in Pune in a month having less than 31 days. Two persons were born between M and N, who was not born in Lucknow. Three persons were born between X and H, who was born after M. O was born before Y, who was born in Patna. The individual born in Surat was born before the one born in Varanasi, none of them was born in April. Neither O nor H was born in Lucknow or Varanasi. O was born after Z, who was born in Jaipur. The one born in Indore was born in a month with 31 days. The individual born in Indore was born immediately before the one born in Surat.

Q.5) Which of the following combination is correct?'),
  ('5b89d770-413e-4e6e-a491-b442d7fc3b00'::uuid,
   'I.8-10) Direction: Study the information carefully and answer the following question. Among the six persons X, Y, Z, M, N, and O, each has a different weight. X is heavier than 3 persons, Z is lighter than M. N is lighter than only Y. Z is not the lightest. The second heaviest person weighs 56 kg, and the second lightest person weighs 28 kg.

Q.8) Who among the person weighs 56 kg?'),
  ('f78c35f1-7dfd-46a5-9761-8ae1f11b89a2'::uuid,
   'I.8-10) Direction: Study the information carefully and answer the following question. Among the six persons X, Y, Z, M, N, and O, each has a different weight. X is heavier than 3 persons, Z is lighter than M. N is lighter than only Y. Z is not the lightest. The second heaviest person weighs 56 kg, and the second lightest person weighs 28 kg.

Q.9) How many persons are lighter than M?'),
  ('a6114783-b2a8-44bf-8868-2b4acd065b9d'::uuid,
   'I.8-10) Direction: Study the information carefully and answer the following question. Among the six persons X, Y, Z, M, N, and O, each has a different weight. X is heavier than 3 persons, Z is lighter than M. N is lighter than only Y. Z is not the lightest. The second heaviest person weighs 56 kg, and the second lightest person weighs 28 kg.

Q.10) What is the possible weight of O?'),
  ('262e5659-e43a-46d5-aef8-b75511b8a7d9'::uuid,
   'I.16-19) Direction: Study the following information carefully to answer the given question. Eight individuals M, N, O, P, Q, R, S, and T are sitting around a circular table facing the table, butnot necessarily in the same order. Each of them has a preference for a different color: lavender, maroon, cyan, emerald, navy, ebony, amber, and ivory, but not necessarily in the same order. The one who favors cyan sits to the immediate left of the person who likes ebony. S does not like ivory. Q sits third to the left of M, who likes lavender, and the individual who likes lavender sits to the immediate left of R. P sits to the immediate right of O, and neither of them prefers emerald. The one who likes maroon and T has two people sitting between them. P, Q, and R, none of them has a liking for maroon. Q and the person who prefers emerald have one person in between them. S sits second to the right of N. O sits opposite the person who likes ivory, and the individual who likes ivory sits immediately next to the one who enjoys navy.

Q.16) Which color does R like?'),
  ('100b9f1a-41fe-4083-be93-b8d983e93071'::uuid,
   'I.16-19) Direction: Study the following information carefully to answer the given question. Eight individuals M, N, O, P, Q, R, S, and T are sitting around a circular table facing the table, butnot necessarily in the same order. Each of them has a preference for a different color: lavender, maroon, cyan, emerald, navy, ebony, amber, and ivory, but not necessarily in the same order. The one who favors cyan sits to the immediate left of the person who likes ebony. S does not like ivory. Q sits third to the left of M, who likes lavender, and the individual who likes lavender sits to the immediate left of R. P sits to the immediate right of O, and neither of them prefers emerald. The one who likes maroon and T has two people sitting between them. P, Q, and R, none of them has a liking for maroon. Q and the person who prefers emerald have one person in between them. S sits second to the right of N. O sits opposite the person who likes ivory, and the individual who likes ivory sits immediately next to the one who enjoys navy.

Q.17) Who among the following is an immediate neighbor of the one who likes Maroon color?'),
  ('c04d7556-44c7-45ab-b89a-ca7b0cb8c27c'::uuid,
   'I.16-19) Direction: Study the following information carefully to answer the given question. Eight individuals M, N, O, P, Q, R, S, and T are sitting around a circular table facing the table, butnot necessarily in the same order. Each of them has a preference for a different color: lavender, maroon, cyan, emerald, navy, ebony, amber, and ivory, but not necessarily in the same order. The one who favors cyan sits to the immediate left of the person who likes ebony. S does not like ivory. Q sits third to the left of M, who likes lavender, and the individual who likes lavender sits to the immediate left of R. P sits to the immediate right of O, and neither of them prefers emerald. The one who likes maroon and T has two people sitting between them. P, Q, and R, none of them has a liking for maroon. Q and the person who prefers emerald have one person in between them. S sits second to the right of N. O sits opposite the person who likes ivory, and the individual who likes ivory sits immediately next to the one who enjoys navy.

Q.18) How many persons are sitting between P and the persons who likes emerald?'),
  ('fe30b37b-3811-45ff-bcc5-75f12bea881f'::uuid,
   'I.16-19) Direction: Study the following information carefully to answer the given question. Eight individuals M, N, O, P, Q, R, S, and T are sitting around a circular table facing the table, butnot necessarily in the same order. Each of them has a preference for a different color: lavender, maroon, cyan, emerald, navy, ebony, amber, and ivory, but not necessarily in the same order. The one who favors cyan sits to the immediate left of the person who likes ebony. S does not like ivory. Q sits third to the left of M, who likes lavender, and the individual who likes lavender sits to the immediate left of R. P sits to the immediate right of O, and neither of them prefers emerald. The one who likes maroon and T has two people sitting between them. P, Q, and R, none of them has a liking for maroon. Q and the person who prefers emerald have one person in between them. S sits second to the right of N. O sits opposite the person who likes ivory, and the individual who likes ivory sits immediately next to the one who enjoys navy.

Q.19) Which person is sitting opposite the person who likes Navy?'),
  ('5f9dfef9-8c4d-4890-87bb-d9745900f101'::uuid,
   '(Instruction for Q.5) Study the following information carefully and answer the questions below: A is sister of B, who is the wife of C. D and E are the daughters of B. F is the son of A and G is the wife of A’s only son. H is married to E and K is a daughter of H. I is the sister of J, who is the son of G.

Q.5) How C is related to F?'),
  ('9345f6d5-a7a2-4dee-a260-b4e32195a723'::uuid,
   '(Instruction for Q.6) Study the following information carefully and answer the questions below: Mr. Wasan goes 17km in east and reached point Y, then he takes a right turn and goes 52km to reach point Z. Then he takes a left turn and goes 7km and reached point R. Again he takes a left turn and goes 24km and reached point S.

Q.6) What is the shortest possible distance between the final point and the point Z?'),
  ('3accdfd3-a119-4c64-934b-f0913d2cb9a0'::uuid,
   '(Instructions for Q.7 to Q.10) Read the following information carefully and answer the questions given below it: There are certain number of persons sitting in a row and all were facing South and all of them scored different runs in a cricket match viz. 20, 27, 33, 38, 40, 43, 45 and 50 but not necessarily in the same order. D scored the lowest runs. A is in the middle of the row. B is fifth to the right of C. Two persons sit between D and E who is five places away from F. G scored 43. The sum of runs of G and E is equal to sum of runs scored by D and H. One among the four scored the highest runs and one among the four scored the lowest runs. G is third from one of the extreme ends but is not sitting between B and C. G scored more runs than A but less than F. C is at one of the extreme end. H sits to the immediate left of G. Three people sit between E and A who is an immediate right of F. Number of persons between E and A are same as number of persons between A and B. The difference between the runs scored by D and B is equal to the difference between the runs scored by E and C.

Q.7) How many persons are sitting in the row?'),
  ('c84d3b06-d0c0-4791-a6b4-366755550090'::uuid,
   '(Instructions for Q.7 to Q.10) Read the following information carefully and answer the questions given below it: There are certain number of persons sitting in a row and all were facing South and all of them scored different runs in a cricket match viz. 20, 27, 33, 38, 40, 43, 45 and 50 but not necessarily in the same order. D scored the lowest runs. A is in the middle of the row. B is fifth to the right of C. Two persons sit between D and E who is five places away from F. G scored 43. The sum of runs of G and E is equal to sum of runs scored by D and H. One among the four scored the highest runs and one among the four scored the lowest runs. G is third from one of the extreme ends but is not sitting between B and C. G scored more runs than A but less than F. C is at one of the extreme end. H sits to the immediate left of G. Three people sit between E and A who is an immediate right of F. Number of persons between E and A are same as number of persons between A and B. The difference between the runs scored by D and B is equal to the difference between the runs scored by E and C.

Q.8) What is the sum of runs scored by C and H?'),
  ('5fe6fa6b-0e18-4311-b6fe-f450df355058'::uuid,
   '(Instructions for Q.7 to Q.10) Read the following information carefully and answer the questions given below it: There are certain number of persons sitting in a row and all were facing South and all of them scored different runs in a cricket match viz. 20, 27, 33, 38, 40, 43, 45 and 50 but not necessarily in the same order. D scored the lowest runs. A is in the middle of the row. B is fifth to the right of C. Two persons sit between D and E who is five places away from F. G scored 43. The sum of runs of G and E is equal to sum of runs scored by D and H. One among the four scored the highest runs and one among the four scored the lowest runs. G is third from one of the extreme ends but is not sitting between B and C. G scored more runs than A but less than F. C is at one of the extreme end. H sits to the immediate left of G. Three people sit between E and A who is an immediate right of F. Number of persons between E and A are same as number of persons between A and B. The difference between the runs scored by D and B is equal to the difference between the runs scored by E and C.

Q.9) How many persons sit between E and C?'),
  ('87eddf69-32bb-4be0-a103-83bb66414139'::uuid,
   '(Instructions for Q.7 to Q.10) Read the following information carefully and answer the questions given below it: There are certain number of persons sitting in a row and all were facing South and all of them scored different runs in a cricket match viz. 20, 27, 33, 38, 40, 43, 45 and 50 but not necessarily in the same order. D scored the lowest runs. A is in the middle of the row. B is fifth to the right of C. Two persons sit between D and E who is five places away from F. G scored 43. The sum of runs of G and E is equal to sum of runs scored by D and H. One among the four scored the highest runs and one among the four scored the lowest runs. G is third from one of the extreme ends but is not sitting between B and C. G scored more runs than A but less than F. C is at one of the extreme end. H sits to the immediate left of G. Three people sit between E and A who is an immediate right of F. Number of persons between E and A are same as number of persons between A and B. The difference between the runs scored by D and B is equal to the difference between the runs scored by E and C.

Q.10) Who among the following scored the highest runs?'),
  ('903bad90-f9a8-4a92-a049-c6a682627106'::uuid,
   '(Instruction for Q.11 to Q.14) Read the given information carefully and answer the questions given below: Eight friends namely G, O, T, L, M, K, A and R were born in different months among January, March, April, July, September and November. Three persons were born in same month. Each of them is from different Cities viz. Kolkata, Patna, Nainital, Agra, Lucknow, Dehradun, Pune and Ranchi. All the above information is not necessarily in the same order. The one who is from Dehradun was born in the month having less than 31 days. T is from Kolkata. G and M were born in same month. Persons who is from Agra and Patna were born in November. L is from Lucknow and he was born in the month having 31 days but not in March. R is from Ranchi and he was born in April. The one who is from Kolkata was born in the month having 30 days after July but before November. The one who is from Pune was born in month having 31 days before April. K was born in July and he is from Nainital. A is from Agra and M is not from Patna.

Q.11) Who among the following was born in the month of November?'),
  ('3b7faecb-8022-40a6-ac10-04f6f5b13334'::uuid,
   '(Instruction for Q.11 to Q.14) Read the given information carefully and answer the questions given below: Eight friends namely G, O, T, L, M, K, A and R were born in different months among January, March, April, July, September and November. Three persons were born in same month. Each of them is from different Cities viz. Kolkata, Patna, Nainital, Agra, Lucknow, Dehradun, Pune and Ranchi. All the above information is not necessarily in the same order. The one who is from Dehradun was born in the month having less than 31 days. T is from Kolkata. G and M were born in same month. Persons who is from Agra and Patna were born in November. L is from Lucknow and he was born in the month having 31 days but not in March. R is from Ranchi and he was born in April. The one who is from Kolkata was born in the month having 30 days after July but before November. The one who is from Pune was born in month having 31 days before April. K was born in July and he is from Nainital. A is from Agra and M is not from Patna.

Q.12) Who among the following persons was born in the month having 31 days?'),
  ('cb224fc8-e4ec-4bdd-bad4-a8256ef43eaf'::uuid,
   '(Instruction for Q.11 to Q.14) Read the given information carefully and answer the questions given below: Eight friends namely G, O, T, L, M, K, A and R were born in different months among January, March, April, July, September and November. Three persons were born in same month. Each of them is from different Cities viz. Kolkata, Patna, Nainital, Agra, Lucknow, Dehradun, Pune and Ranchi. All the above information is not necessarily in the same order. The one who is from Dehradun was born in the month having less than 31 days. T is from Kolkata. G and M were born in same month. Persons who is from Agra and Patna were born in November. L is from Lucknow and he was born in the month having 31 days but not in March. R is from Ranchi and he was born in April. The one who is from Kolkata was born in the month having 30 days after July but before November. The one who is from Pune was born in month having 31 days before April. K was born in July and he is from Nainital. A is from Agra and M is not from Patna.

Q.13) Who among the following persons is from Pune?'),
  ('bd6864e6-454a-48fa-a157-5f081acb9e60'::uuid,
   '(Instruction for Q.11 to Q.14) Read the given information carefully and answer the questions given below: Eight friends namely G, O, T, L, M, K, A and R were born in different months among January, March, April, July, September and November. Three persons were born in same month. Each of them is from different Cities viz. Kolkata, Patna, Nainital, Agra, Lucknow, Dehradun, Pune and Ranchi. All the above information is not necessarily in the same order. The one who is from Dehradun was born in the month having less than 31 days. T is from Kolkata. G and M were born in same month. Persons who is from Agra and Patna were born in November. L is from Lucknow and he was born in the month having 31 days but not in March. R is from Ranchi and he was born in April. The one who is from Kolkata was born in the month having 30 days after July but before November. The one who is from Pune was born in month having 31 days before April. K was born in July and he is from Nainital. A is from Agra and M is not from Patna.

Q.14) Which among the following statements is definitely true?'),
  ('db0f8650-f587-4342-803a-e9ef53491f6f'::uuid,
   '(Instructions for Q.15 to Q.17) Study the following information and answer the questions. Seven friends, namely L, M, N, O, P, Q and R, like different animated movies, namely Finding Nemo, Rio, Frozen, Up, Lion King, Shrek and Cars, but not necessarily in the same order. Each friend also has a presentation on topics of different subjects, namely Civics, History, English, Geography, Chemistry, Physics and Biology but not necessarily in the same order. Q has a presentation on Civics and likes neither Frozen nor Up. The one who likes Finding Nemo has a presentation on History. L likes Rio and has a presentation neither on Geography nor on Chemistry. The one who likes Cars has a presentation on Biology. M has a presentation on Physics and does not like Up. The one who likes Up does not have a presentation on Chemistry. O likes Lion King. R does not have a presentation on History and does not like Up. P does not like Up.

Q.15) On which of the following subjects does P have a presentation?'),
  ('be88568d-e3ae-4ec1-9ae4-786d21b68f70'::uuid,
   '(Instructions for Q.15 to Q.17) Study the following information and answer the questions. Seven friends, namely L, M, N, O, P, Q and R, like different animated movies, namely Finding Nemo, Rio, Frozen, Up, Lion King, Shrek and Cars, but not necessarily in the same order. Each friend also has a presentation on topics of different subjects, namely Civics, History, English, Geography, Chemistry, Physics and Biology but not necessarily in the same order. Q has a presentation on Civics and likes neither Frozen nor Up. The one who likes Finding Nemo has a presentation on History. L likes Rio and has a presentation neither on Geography nor on Chemistry. The one who likes Cars has a presentation on Biology. M has a presentation on Physics and does not like Up. The one who likes Up does not have a presentation on Chemistry. O likes Lion King. R does not have a presentation on History and does not like Up. P does not like Up.

Q.16) Four of the following five form a group as per the given arrangement. Which of the following does not belong to that group?'),
  ('090e82ae-3952-4395-a8f9-b493f7fbf8b4'::uuid,
   '(Instructions for Q.15 to Q.17) Study the following information and answer the questions. Seven friends, namely L, M, N, O, P, Q and R, like different animated movies, namely Finding Nemo, Rio, Frozen, Up, Lion King, Shrek and Cars, but not necessarily in the same order. Each friend also has a presentation on topics of different subjects, namely Civics, History, English, Geography, Chemistry, Physics and Biology but not necessarily in the same order. Q has a presentation on Civics and likes neither Frozen nor Up. The one who likes Finding Nemo has a presentation on History. L likes Rio and has a presentation neither on Geography nor on Chemistry. The one who likes Cars has a presentation on Biology. M has a presentation on Physics and does not like Up. The one who likes Up does not have a presentation on Chemistry. O likes Lion King. R does not have a presentation on History and does not like Up. P does not like Up.

Q.17) Which of the following combinations is definitely correct?'),
  ('bd66db1e-2b1c-4409-8fbc-3fe048b797ce'::uuid,
   '(Instructions for Q.18 to Q.20) Study the following information carefully and answer the questions given below: F, G, H, I, J, K, L, M and N are nine college friends in which K, L, M and N are boys and the remaining five are girls. They are divided into three groups, viz, A, B and C, for three projects. There must be at least three persons with at least one boy in each group. F and L are in the same group. M is in the group which consists of either F or I or both, but M must be in group A. F and G cannot work on the same project. K and J work on the same project. Both G and J are in the same group. I, H and J are members of different groups. J must be in group B. M and L can''t be in the same group.

Q.18) Which of the following groups consists of two male persons?'),
  ('7556f855-4c7e-467b-a1a5-8c56af7faca7'::uuid,
   '(Instructions for Q.18 to Q.20) Study the following information carefully and answer the questions given below: F, G, H, I, J, K, L, M and N are nine college friends in which K, L, M and N are boys and the remaining five are girls. They are divided into three groups, viz, A, B and C, for three projects. There must be at least three persons with at least one boy in each group. F and L are in the same group. M is in the group which consists of either F or I or both, but M must be in group A. F and G cannot work on the same project. K and J work on the same project. Both G and J are in the same group. I, H and J are members of different groups. J must be in group B. M and L can''t be in the same group.

Q.19) Which of the following pairs cannot be the members of the same group?'),
  ('a5cec718-94be-408e-8f43-7e9ebf2f2eb0'::uuid,
   '(Instructions for Q.18 to Q.20) Study the following information carefully and answer the questions given below: F, G, H, I, J, K, L, M and N are nine college friends in which K, L, M and N are boys and the remaining five are girls. They are divided into three groups, viz, A, B and C, for three projects. There must be at least three persons with at least one boy in each group. F and L are in the same group. M is in the group which consists of either F or I or both, but M must be in group A. F and G cannot work on the same project. K and J work on the same project. Both G and J are in the same group. I, H and J are members of different groups. J must be in group B. M and L can''t be in the same group.

Q.20) Which of the following are the members of group C?'),
  ('a007a91e-b1dd-4a0d-8026-745ba975b4d2'::uuid,
   '(Instructions for Q.1 to Q.5) Study the following information carefully and answer the questions given below: Eight persons – Rekha, Shubhi, Reeta, Sana, Gudia, Kavya, Nandini and Ginni, were sitting in a circle facing towards the center. Each of them was born in a different city — Chandigarh, Manali, Amritsar, Jaipur, Bihar, Goa, Mumbai and Bangalore, but not necessarily in the same order. Two persons were sitting between the one, who was born in Jaipur and Gudia. Rekha was born in Chandigarh and sits opposite to Gudia. The one, who was born in Bihar, sits opposite to Sana. Ginni was born in Mumbai and sits second to the right of the one, who was born in Jaipur. Reeta was born in Bihar and was an immediate neighbour of the one, who was born in Goa. Nandini sits third right to Shubhi. Sana was born in Jaipur. The one, who was born in Bangalore, sits adjacent to the one, who was born in Jaipur. Gudia was born in Manali and Nandini was born in Bangalore.

Q.1) Who is sitting on the immediate left of Ginni?'),
  ('3c6cee47-96b6-494e-bc86-64060a4d3ea2'::uuid,
   '(Instructions for Q.1 to Q.5) Study the following information carefully and answer the questions given below: Eight persons – Rekha, Shubhi, Reeta, Sana, Gudia, Kavya, Nandini and Ginni, were sitting in a circle facing towards the center. Each of them was born in a different city — Chandigarh, Manali, Amritsar, Jaipur, Bihar, Goa, Mumbai and Bangalore, but not necessarily in the same order. Two persons were sitting between the one, who was born in Jaipur and Gudia. Rekha was born in Chandigarh and sits opposite to Gudia. The one, who was born in Bihar, sits opposite to Sana. Ginni was born in Mumbai and sits second to the right of the one, who was born in Jaipur. Reeta was born in Bihar and was an immediate neighbour of the one, who was born in Goa. Nandini sits third right to Shubhi. Sana was born in Jaipur. The one, who was born in Bangalore, sits adjacent to the one, who was born in Jaipur. Gudia was born in Manali and Nandini was born in Bangalore.

Q.2) How many persons sit between Kavya and Sana, with left of Sana?'),
  ('4122dd8d-f1cf-40a6-b3f7-46e17f84d938'::uuid,
   '(Instructions for Q.1 to Q.5) Study the following information carefully and answer the questions given below: Eight persons – Rekha, Shubhi, Reeta, Sana, Gudia, Kavya, Nandini and Ginni, were sitting in a circle facing towards the center. Each of them was born in a different city — Chandigarh, Manali, Amritsar, Jaipur, Bihar, Goa, Mumbai and Bangalore, but not necessarily in the same order. Two persons were sitting between the one, who was born in Jaipur and Gudia. Rekha was born in Chandigarh and sits opposite to Gudia. The one, who was born in Bihar, sits opposite to Sana. Ginni was born in Mumbai and sits second to the right of the one, who was born in Jaipur. Reeta was born in Bihar and was an immediate neighbour of the one, who was born in Goa. Nandini sits third right to Shubhi. Sana was born in Jaipur. The one, who was born in Bangalore, sits adjacent to the one, who was born in Jaipur. Gudia was born in Manali and Nandini was born in Bangalore.

Q.3) Kavya belongs to which city among the following?'),
  ('dcd877f5-a586-4ba0-afd4-0e3100bfcb78'::uuid,
   '(Instructions for Q.1 to Q.5) Study the following information carefully and answer the questions given below: Eight persons – Rekha, Shubhi, Reeta, Sana, Gudia, Kavya, Nandini and Ginni, were sitting in a circle facing towards the center. Each of them was born in a different city — Chandigarh, Manali, Amritsar, Jaipur, Bihar, Goa, Mumbai and Bangalore, but not necessarily in the same order. Two persons were sitting between the one, who was born in Jaipur and Gudia. Rekha was born in Chandigarh and sits opposite to Gudia. The one, who was born in Bihar, sits opposite to Sana. Ginni was born in Mumbai and sits second to the right of the one, who was born in Jaipur. Reeta was born in Bihar and was an immediate neighbour of the one, who was born in Goa. Nandini sits third right to Shubhi. Sana was born in Jaipur. The one, who was born in Bangalore, sits adjacent to the one, who was born in Jaipur. Gudia was born in Manali and Nandini was born in Bangalore.

Q.4) Who is an immediate neighbour of Gudia and Kavya?'),
  ('761951e1-949c-4cd2-8e39-51c41ad3bbd1'::uuid,
   '(Instructions for Q.1 to Q.5) Study the following information carefully and answer the questions given below: Eight persons – Rekha, Shubhi, Reeta, Sana, Gudia, Kavya, Nandini and Ginni, were sitting in a circle facing towards the center. Each of them was born in a different city — Chandigarh, Manali, Amritsar, Jaipur, Bihar, Goa, Mumbai and Bangalore, but not necessarily in the same order. Two persons were sitting between the one, who was born in Jaipur and Gudia. Rekha was born in Chandigarh and sits opposite to Gudia. The one, who was born in Bihar, sits opposite to Sana. Ginni was born in Mumbai and sits second to the right of the one, who was born in Jaipur. Reeta was born in Bihar and was an immediate neighbour of the one, who was born in Goa. Nandini sits third right to Shubhi. Sana was born in Jaipur. The one, who was born in Bangalore, sits adjacent to the one, who was born in Jaipur. Gudia was born in Manali and Nandini was born in Bangalore.

Q.5) Who is sitting on the third left of Ginni?'),
  ('93bd83ff-b9e4-44d7-a309-1665863832f4'::uuid,
   '(Instructions for Q.9 and Q.10) Study the following information carefully and answer the questions given below: In a family, P is the wife of Q. Q is the father of only R and S. T is the daughter-in-law of P. T has only two children U and V. V is the daughter in law of W. U is the aunt of X. X is the daughter of Y. R is unmarried.

Q.9) How is W related to X?'),
  ('e4da73f5-efc2-403d-b6c8-694168e5411b'::uuid,
   '(Instructions for Q.9 and Q.10) Study the following information carefully and answer the questions given below: In a family, P is the wife of Q. Q is the father of only R and S. T is the daughter-in-law of P. T has only two children U and V. V is the daughter in law of W. U is the aunt of X. X is the daughter of Y. R is unmarried.

Q.10) How is V related to P?'),
  ('c8682245-7013-4f4f-9b75-540a1e186463'::uuid,
   '(Instructions for Q.11 to Q.14) Answer the questions based on the information given below: Nine persons P, Q, R, S, T, U, V, W and X are sitting in a linear table and facing the north direction but not necessarily in the same order. Each one of them likes different colours i.e. Blue, Grey, Yellow, Pink, Black, Green, Brown, Red and Orange but not necessarily in the same order. Two persons sit between X and V who does not like Yellow. W sits just to the right of R. One person sits between W and P. R likes Yellow. Two persons sit between the one who likes Black and the one who likes Red. Q likes Black but he does not sit just to the right of W. Three persons sit between X and the one who likes Pink. X sits on an even position from the left end. The one who likes Yellow sits just to the left of the one who likes Pink. The one who likes the Blue color sits just to the right of T. V does not likes Blue color. S likes Grey and T likes Orange color. The one who likes Brown sits immediate left to the V.

Q.11) What is the position of S, according to U in the arrangement?'),
  ('30c13cfa-7423-4059-abb4-73064c4c60da'::uuid,
   '(Instructions for Q.11 to Q.14) Answer the questions based on the information given below: Nine persons P, Q, R, S, T, U, V, W and X are sitting in a linear table and facing the north direction but not necessarily in the same order. Each one of them likes different colours i.e. Blue, Grey, Yellow, Pink, Black, Green, Brown, Red and Orange but not necessarily in the same order. Two persons sit between X and V who does not like Yellow. W sits just to the right of R. One person sits between W and P. R likes Yellow. Two persons sit between the one who likes Black and the one who likes Red. Q likes Black but he does not sit just to the right of W. Three persons sit between X and the one who likes Pink. X sits on an even position from the left end. The one who likes Yellow sits just to the left of the one who likes Pink. The one who likes the Blue color sits just to the right of T. V does not likes Blue color. S likes Grey and T likes Orange color. The one who likes Brown sits immediate left to the V.

Q.12) Q is an immediate neighbour of whom among the following?'),
  ('93d72f0d-5615-4a41-ad07-eda062825f18'::uuid,
   '(Instructions for Q.11 to Q.14) Answer the questions based on the information given below: Nine persons P, Q, R, S, T, U, V, W and X are sitting in a linear table and facing the north direction but not necessarily in the same order. Each one of them likes different colours i.e. Blue, Grey, Yellow, Pink, Black, Green, Brown, Red and Orange but not necessarily in the same order. Two persons sit between X and V who does not like Yellow. W sits just to the right of R. One person sits between W and P. R likes Yellow. Two persons sit between the one who likes Black and the one who likes Red. Q likes Black but he does not sit just to the right of W. Three persons sit between X and the one who likes Pink. X sits on an even position from the left end. The one who likes Yellow sits just to the left of the one who likes Pink. The one who likes the Blue color sits just to the right of T. V does not likes Blue color. S likes Grey and T likes Orange color. The one who likes Brown sits immediate left to the V.

Q.13) How many persons are sitting between the one who likes Orange and the one who likes Green?'),
  ('d03313d9-01ba-4551-9c57-845815d18c69'::uuid,
   '(Instructions for Q.11 to Q.14) Answer the questions based on the information given below: Nine persons P, Q, R, S, T, U, V, W and X are sitting in a linear table and facing the north direction but not necessarily in the same order. Each one of them likes different colours i.e. Blue, Grey, Yellow, Pink, Black, Green, Brown, Red and Orange but not necessarily in the same order. Two persons sit between X and V who does not like Yellow. W sits just to the right of R. One person sits between W and P. R likes Yellow. Two persons sit between the one who likes Black and the one who likes Red. Q likes Black but he does not sit just to the right of W. Three persons sit between X and the one who likes Pink. X sits on an even position from the left end. The one who likes Yellow sits just to the left of the one who likes Pink. The one who likes the Blue color sits just to the right of T. V does not likes Blue color. S likes Grey and T likes Orange color. The one who likes Brown sits immediate left to the V.

Q.14) Which pair is an immediate neighbour of each other?'),
  ('6c6220a5-333e-4688-ac60-2b13abe7906b'::uuid,
   '(Instruction for Q.15 to Q.17) Study the following information carefully and answer the given questions: In a certain code language, ‘while the challenges explaining’ is written as ‘kue cdw prc bfa’, ‘in investigating terrorism while’ is written as ‘prc jpa pbz ngs’ ‘related the challenges in’ is written as ‘ngs cdw itg kue‘

Q.15) What is the code for ‘investigating’?'),
  ('7b897175-3d75-49fd-987d-0e7f28cfce8e'::uuid,
   '(Instruction for Q.15 to Q.17) Study the following information carefully and answer the given questions: In a certain code language, ‘while the challenges explaining’ is written as ‘kue cdw prc bfa’, ‘in investigating terrorism while’ is written as ‘prc jpa pbz ngs’ ‘related the challenges in’ is written as ‘ngs cdw itg kue‘

Q.16)‘while in related’ can be coded as'),
  ('7e80e8bb-cdef-479f-8366-1bfb2d59f0f7'::uuid,
   '(Instruction for Q.15 to Q.17) Study the following information carefully and answer the given questions: In a certain code language, ‘while the challenges explaining’ is written as ‘kue cdw prc bfa’, ‘in investigating terrorism while’ is written as ‘prc jpa pbz ngs’ ‘related the challenges in’ is written as ‘ngs cdw itg kue‘

Q.17) What does ‘cdw’ stand for?'),
  ('479b597e-d919-4dcb-93dc-f439a1761ff1'::uuid,
   '(Instruction for Q.6 to Q.9) Study the following information carefully and answer the question given below: Ten persons Vaibhav, Sumit, Raman, Pawan, Naman, Dev, Girish, Hitesh, Karan and Naresh are sitting in two parallel rows. Row 1 is facing south and row 2 is facing north. Vaibhav, Sumit, Raman, Pawan and Naman are facing south. Each person of row 1 is facing the other person of row 2. (i) Naresh sits third to the right of Girish. (ii) Dev sits second to the left of Naresh. Dev faces the one who sits on the immediate right of Sumit. (iii) Only one person sits between Pawan and Sumit. (iv) Vaibhav is not an immediate neighbour of Sumit. (v) Only one person sits between Raman and Naman. Naman does not face Dev. (vi) Hitesh is not an immediate neighbour of Girish. (vii) Only two persons sit between Karan and Hitesh.

Q.6) Who among the following faces Pawan?'),
  ('52911d47-295a-48c1-a95f-b6e91e0fa1ec'::uuid,
   '(Instruction for Q.6 to Q.9) Study the following information carefully and answer the question given below: Ten persons Vaibhav, Sumit, Raman, Pawan, Naman, Dev, Girish, Hitesh, Karan and Naresh are sitting in two parallel rows. Row 1 is facing south and row 2 is facing north. Vaibhav, Sumit, Raman, Pawan and Naman are facing south. Each person of row 1 is facing the other person of row 2. (i) Naresh sits third to the right of Girish. (ii) Dev sits second to the left of Naresh. Dev faces the one who sits on the immediate right of Sumit. (iii) Only one person sits between Pawan and Sumit. (iv) Vaibhav is not an immediate neighbour of Sumit. (v) Only one person sits between Raman and Naman. Naman does not face Dev. (vi) Hitesh is not an immediate neighbour of Girish. (vii) Only two persons sit between Karan and Hitesh.

Q.7) How many persons are there between Karan and Dev?'),
  ('f254e7d9-2170-4f45-bf81-963dc6881b63'::uuid,
   '(Instruction for Q.6 to Q.9) Study the following information carefully and answer the question given below: Ten persons Vaibhav, Sumit, Raman, Pawan, Naman, Dev, Girish, Hitesh, Karan and Naresh are sitting in two parallel rows. Row 1 is facing south and row 2 is facing north. Vaibhav, Sumit, Raman, Pawan and Naman are facing south. Each person of row 1 is facing the other person of row 2. (i) Naresh sits third to the right of Girish. (ii) Dev sits second to the left of Naresh. Dev faces the one who sits on the immediate right of Sumit. (iii) Only one person sits between Pawan and Sumit. (iv) Vaibhav is not an immediate neighbour of Sumit. (v) Only one person sits between Raman and Naman. Naman does not face Dev. (vi) Hitesh is not an immediate neighbour of Girish. (vii) Only two persons sit between Karan and Hitesh.

Q.8)Which of the following statement is true?'),
  ('7e476994-fae1-4897-8c65-cbc620840b93'::uuid,
   '(Instruction for Q.6 to Q.9) Study the following information carefully and answer the question given below: Ten persons Vaibhav, Sumit, Raman, Pawan, Naman, Dev, Girish, Hitesh, Karan and Naresh are sitting in two parallel rows. Row 1 is facing south and row 2 is facing north. Vaibhav, Sumit, Raman, Pawan and Naman are facing south. Each person of row 1 is facing the other person of row 2. (i) Naresh sits third to the right of Girish. (ii) Dev sits second to the left of Naresh. Dev faces the one who sits on the immediate right of Sumit. (iii) Only one person sits between Pawan and Sumit. (iv) Vaibhav is not an immediate neighbour of Sumit. (v) Only one person sits between Raman and Naman. Naman does not face Dev. (vi) Hitesh is not an immediate neighbour of Girish. (vii) Only two persons sit between Karan and Hitesh.

Q.9) What is the position of Karan with respect to Dev?'),
  ('25209c15-4ce5-41e2-b7e8-287e6fa8a4af'::uuid,
   '(Instruction for Q.13 to Q.16) Read the following information carefully and answer the questions given below. “Purple Black Green Pink” is written as “Sk Rk Tk Nk”, “Green Brown Mustard Orange” is written as “Pk Gk Sk Fk”, “Mustard Black White Red” is written as “Nk Mk Pk Vk”, “White Red Purple Violet” is written as “Vk Mk Rk Dk”

Q.13) What will be the code for “White”?'),
  ('fc7e3a43-f205-4814-8018-4dcff1767fa3'::uuid,
   '(Instruction for Q.13 to Q.16) Read the following information carefully and answer the questions given below. “Purple Black Green Pink” is written as “Sk Rk Tk Nk”, “Green Brown Mustard Orange” is written as “Pk Gk Sk Fk”, “Mustard Black White Red” is written as “Nk Mk Pk Vk”, “White Red Purple Violet” is written as “Vk Mk Rk Dk”

Q.14) If Orange is written as “Gk”, then what will be the code for “Brown”?'),
  ('c999aa6a-65ea-46f0-8045-6c362472bf78'::uuid,
   '(Instruction for Q.13 to Q.16) Read the following information carefully and answer the questions given below. “Purple Black Green Pink” is written as “Sk Rk Tk Nk”, “Green Brown Mustard Orange” is written as “Pk Gk Sk Fk”, “Mustard Black White Red” is written as “Nk Mk Pk Vk”, “White Red Purple Violet” is written as “Vk Mk Rk Dk”

Q.15) The codes “Rk Sk Nk” may represent which of the following?'),
  ('ac39da36-c6f2-4cdc-a149-2431339464b1'::uuid,
   '(Instruction for Q.13 to Q.16) Read the following information carefully and answer the questions given below. “Purple Black Green Pink” is written as “Sk Rk Tk Nk”, “Green Brown Mustard Orange” is written as “Pk Gk Sk Fk”, “Mustard Black White Red” is written as “Nk Mk Pk Vk”, “White Red Purple Violet” is written as “Vk Mk Rk Dk”

Q.16) What does the code “Fk” represents?'),
  ('f5ba5958-4073-4867-8634-71b5bf495919'::uuid,
   '(Instructions for Q.17 and Q.18) Study the following information carefully and answer the given questions: The distance from point T to point S, which is in its south, is 9 metres. The distance from point U to point T, which is in its east, is 11 metres. The distance from point X to point W, which is in its north, is 4 metres. The distance from point V to point U, which is in its north, is 5 metres. The distance between point W and point V is 15 metres and point V is in its west. The distance between point Y and the point W, where W is in its south, is 5 metres.

Q.17) Which of the following three points are in a straight line?'),
  ('9c7dc7ec-2345-41d2-8f84-612efa204ec0'::uuid,
   '(Instructions for Q.17 and Q.18) Study the following information carefully and answer the given questions: The distance from point T to point S, which is in its south, is 9 metres. The distance from point U to point T, which is in its east, is 11 metres. The distance from point X to point W, which is in its north, is 4 metres. The distance from point V to point U, which is in its north, is 5 metres. The distance between point W and point V is 15 metres and point V is in its west. The distance between point Y and the point W, where W is in its south, is 5 metres.

Q.18) What is the distance between points U and Y?'),
  ('04ca7e12-2831-4be9-9330-22369a656ac8'::uuid,
   '(Instructions for Q.1 to Q.5) Study the information given below and answer the questions based on it. Seven friends namely – Ramesh, Rajesh, Jayesh, Viresh, Tapesh, Lovish and Ishant – live in a hostel having seven floors. All chose to stay on different floors of the hostel building (numbered 1 to 7) but not necessarily in the same order. They all have come from different states – Odisha, Gujarat, Assam, Goa, Kerala, Delhi and Bihar but not in the same order. Rajesh chose third floor and is from Gujarat. Viresh has chosen the floor immediately below the floor which Tapesh has chosen and immediately above the floor which Jayesh has chosen. There is only one floor between the floors which Rajesh and Lovish have chosen. Viresh has not come from Kerala. The one who chose the top floor has come from Bihar. There is only one floor between the floor which Jayesh has chosen and the one who is from Odisha. The one who is from Delhi has chosen the floor immediately above the floor which the one from Kerala has chosen. The one who is from Goa has not chosen the floor below the one from Odisha.

Q.1) Ramesh is from which of the following states?'),
  ('6971a72f-d713-401f-ba76-8d5324292b26'::uuid,
   '(Instructions for Q.1 to Q.5) Study the information given below and answer the questions based on it. Seven friends namely – Ramesh, Rajesh, Jayesh, Viresh, Tapesh, Lovish and Ishant – live in a hostel having seven floors. All chose to stay on different floors of the hostel building (numbered 1 to 7) but not necessarily in the same order. They all have come from different states – Odisha, Gujarat, Assam, Goa, Kerala, Delhi and Bihar but not in the same order. Rajesh chose third floor and is from Gujarat. Viresh has chosen the floor immediately below the floor which Tapesh has chosen and immediately above the floor which Jayesh has chosen. There is only one floor between the floors which Rajesh and Lovish have chosen. Viresh has not come from Kerala. The one who chose the top floor has come from Bihar. There is only one floor between the floor which Jayesh has chosen and the one who is from Odisha. The one who is from Delhi has chosen the floor immediately above the floor which the one from Kerala has chosen. The one who is from Goa has not chosen the floor below the one from Odisha.

Q.2) Which of the following combination is true regarding the given options?'),
  ('51e44550-6f2f-46d8-9a63-f7dc31fd1ff3'::uuid,
   '(Instructions for Q.1 to Q.5) Study the information given below and answer the questions based on it. Seven friends namely – Ramesh, Rajesh, Jayesh, Viresh, Tapesh, Lovish and Ishant – live in a hostel having seven floors. All chose to stay on different floors of the hostel building (numbered 1 to 7) but not necessarily in the same order. They all have come from different states – Odisha, Gujarat, Assam, Goa, Kerala, Delhi and Bihar but not in the same order. Rajesh chose third floor and is from Gujarat. Viresh has chosen the floor immediately below the floor which Tapesh has chosen and immediately above the floor which Jayesh has chosen. There is only one floor between the floors which Rajesh and Lovish have chosen. Viresh has not come from Kerala. The one who chose the top floor has come from Bihar. There is only one floor between the floor which Jayesh has chosen and the one who is from Odisha. The one who is from Delhi has chosen the floor immediately above the floor which the one from Kerala has chosen. The one who is from Goa has not chosen the floor below the one from Odisha.

Q.3) If Lovish is related to Odisha, Rajesh is related to Kerala in the same way to whom is Tapesh related to?'),
  ('93dfd0a5-9aab-4d14-acc7-783445ee2d42'::uuid,
   '(Instructions for Q.1 to Q.5) Study the information given below and answer the questions based on it. Seven friends namely – Ramesh, Rajesh, Jayesh, Viresh, Tapesh, Lovish and Ishant – live in a hostel having seven floors. All chose to stay on different floors of the hostel building (numbered 1 to 7) but not necessarily in the same order. They all have come from different states – Odisha, Gujarat, Assam, Goa, Kerala, Delhi and Bihar but not in the same order. Rajesh chose third floor and is from Gujarat. Viresh has chosen the floor immediately below the floor which Tapesh has chosen and immediately above the floor which Jayesh has chosen. There is only one floor between the floors which Rajesh and Lovish have chosen. Viresh has not come from Kerala. The one who chose the top floor has come from Bihar. There is only one floor between the floor which Jayesh has chosen and the one who is from Odisha. The one who is from Delhi has chosen the floor immediately above the floor which the one from Kerala has chosen. The one who is from Goa has not chosen the floor below the one from Odisha.

Q.4) The one who is from Goa lives on which of the following floor?'),
  ('e5d6d5f6-29ed-4712-ab16-80ce76fb9759'::uuid,
   '(Instructions for Q.1 to Q.5) Study the information given below and answer the questions based on it. Seven friends namely – Ramesh, Rajesh, Jayesh, Viresh, Tapesh, Lovish and Ishant – live in a hostel having seven floors. All chose to stay on different floors of the hostel building (numbered 1 to 7) but not necessarily in the same order. They all have come from different states – Odisha, Gujarat, Assam, Goa, Kerala, Delhi and Bihar but not in the same order. Rajesh chose third floor and is from Gujarat. Viresh has chosen the floor immediately below the floor which Tapesh has chosen and immediately above the floor which Jayesh has chosen. There is only one floor between the floors which Rajesh and Lovish have chosen. Viresh has not come from Kerala. The one who chose the top floor has come from Bihar. There is only one floor between the floor which Jayesh has chosen and the one who is from Odisha. The one who is from Delhi has chosen the floor immediately above the floor which the one from Kerala has chosen. The one who is from Goa has not chosen the floor below the one from Odisha.

Q.5) Which statement is not correct according to given information?'),
  ('103253af-51a8-44da-82bd-0473c454f315'::uuid,
   '(Instructions for Q.6 to Q.10) Read the given information carefully and answer the questions: Twelve Persons are sitting in two parallel rows - Q, R, S, T, U and V are sitting in row 1 facing south and P, O, J, W, X and Y are sitting in row 2 facing north. W sits third to the left of P. V does not face P. Neither W nor P sits at extreme ends. O sits at one of the extreme ends. Only two people sit between O and X. V is not an immediate neighbour of U. X does not face V. Two persons sit between R and S. V does not sit at any of the extreme ends. U faces W. S is not an immediate neighbour of U. Q does not face P. J sits left of Y.

Q.6) Who among the following sits diagonally opposite to S?'),
  ('08233e36-b872-4b02-85bd-83402b78a2bb'::uuid,
   '(Instructions for Q.6 to Q.10) Read the given information carefully and answer the questions: Twelve Persons are sitting in two parallel rows - Q, R, S, T, U and V are sitting in row 1 facing south and P, O, J, W, X and Y are sitting in row 2 facing north. W sits third to the left of P. V does not face P. Neither W nor P sits at extreme ends. O sits at one of the extreme ends. Only two people sit between O and X. V is not an immediate neighbour of U. X does not face V. Two persons sit between R and S. V does not sit at any of the extreme ends. U faces W. S is not an immediate neighbour of U. Q does not face P. J sits left of Y.

Q.7) Who among the following sits third to the left of U?'),
  ('1a11f632-d2f5-4a06-b0b1-c8b310f14983'::uuid,
   '(Instructions for Q.6 to Q.10) Read the given information carefully and answer the questions: Twelve Persons are sitting in two parallel rows - Q, R, S, T, U and V are sitting in row 1 facing south and P, O, J, W, X and Y are sitting in row 2 facing north. W sits third to the left of P. V does not face P. Neither W nor P sits at extreme ends. O sits at one of the extreme ends. Only two people sit between O and X. V is not an immediate neighbour of U. X does not face V. Two persons sit between R and S. V does not sit at any of the extreme ends. U faces W. S is not an immediate neighbour of U. Q does not face P. J sits left of Y.

Q.8) Who among the following faces X?'),
  ('d81d49b3-faaa-4dd5-90ae-5093c004dcda'::uuid,
   '(Instructions for Q.6 to Q.10) Read the given information carefully and answer the questions: Twelve Persons are sitting in two parallel rows - Q, R, S, T, U and V are sitting in row 1 facing south and P, O, J, W, X and Y are sitting in row 2 facing north. W sits third to the left of P. V does not face P. Neither W nor P sits at extreme ends. O sits at one of the extreme ends. Only two people sit between O and X. V is not an immediate neighbour of U. X does not face V. Two persons sit between R and S. V does not sit at any of the extreme ends. U faces W. S is not an immediate neighbour of U. Q does not face P. J sits left of Y.

Q.9) Four of the following five form a group, which among the following does not belong to this group?'),
  ('b9f64bc3-fcee-48b7-a6d6-a005ab9437f8'::uuid,
   '(Instructions for Q.6 to Q.10) Read the given information carefully and answer the questions: Twelve Persons are sitting in two parallel rows - Q, R, S, T, U and V are sitting in row 1 facing south and P, O, J, W, X and Y are sitting in row 2 facing north. W sits third to the left of P. V does not face P. Neither W nor P sits at extreme ends. O sits at one of the extreme ends. Only two people sit between O and X. V is not an immediate neighbour of U. X does not face V. Two persons sit between R and S. V does not sit at any of the extreme ends. U faces W. S is not an immediate neighbour of U. Q does not face P. J sits left of Y.

Q.10) How many persons sit between Y and J?'),
  ('e469c10f-2cbf-4448-a8a7-3a7c20da521c'::uuid,
   '(Instruction for Q.11) There are five plays that are to be performed from Monday to Friday. One play is to be performed each day. C is to be performed immediately after D but not on Thursday. Three plays are to be performed between Z and A. A is not be performed at last. N is one of the plays.

Q.11) On which day play N is to be performed?'),
  ('e05ec12c-6d74-4723-b9ed-50783d4fb712'::uuid,
   '(Instruction for Q.11) There are five plays that are to be performed from Monday to Friday. One play is to be performed each day. C is to be performed immediately after D but not on Thursday. Three plays are to be performed between Z and A. A is not be performed at last. N is one of the plays.

Q.12) Which play is to be performed on Monday?'),
  ('ff6b282d-43f6-416a-b364-37e6c2fef95d'::uuid,
   '(Instructions for Q.16 and Q.17) Study the following information carefully and answer the questions given below. In a certain code language, ‘messy room looks bad’ is coded as ‘la ja ta sa’, ‘senior room bad’ is coded as ‘sa ty ta’. ‘messy room feels dirty’ is coded as ‘ja sa op nm’ ‘water save dirty’ is coded as ‘op vs rt’

Q.16) What is the code for ‘Dirty’?'),
  ('539e8fcb-d157-4bd8-9a73-fa87ccd550c5'::uuid,
   '(Instructions for Q.16 and Q.17) Study the following information carefully and answer the questions given below. In a certain code language, ‘messy room looks bad’ is coded as ‘la ja ta sa’, ‘senior room bad’ is coded as ‘sa ty ta’. ‘messy room feels dirty’ is coded as ‘ja sa op nm’ ‘water save dirty’ is coded as ‘op vs rt’

Q.17) Which word is coded as ‘ja’?')
) AS v(question_id, question_text)
WHERE q.id = v.question_id
  AND q.question_text IS DISTINCT FROM v.question_text;

COMMIT;
