-- Migration 283: restore the missing context to 63 RBI Grade B 2022 questions,
-- and return the ones migration 281 pulled back to verified.
--
-- Migration 281 pulled 85 RBI questions off learners because they asked
-- about a passage, puzzle setup or equation that was nowhere in the
-- database. 65 of those are the 2022 Phase I paper. This recovers 63 of
-- them from docs/reference/pyq/RBI-Grade-B-Phase-1-Previous-Year-Question-
-- Paper-2022.pdf, prepending each set's printed Directions block to every
-- stem in its range. The other two need nothing; see the end.
--
-- Same shape as migration 280, different source. The 2022 paper is one file
-- with a clean text layer, continuous question numbering Q1-Q120 that
-- matches pyq_questions.question_number exactly, and 26 Directions headers.
-- Each block is taken verbatim from its header to the first question marker
-- of its range, whitespace collapsed. Nothing is invented.
--
-- THREE SOURCE DEFECTS CORRECTED IN THE HEADER TEXT, and nowhere else:
--   "Direction (15 -17):" -> "Direction (105-107):" — the source misprints
--   this range as "(15 -17)"; it sits immediately before Q105 and its
--   equations are what Q105-107 solve.
--   "__ASCII_DIGITS_IN_HEADER__" -> "" — the source renders some header
--   digits as mathematical-bold codepoints (Directions ( 115-11<BOLD
--   NINE>)); every non-ASCII digit in a header is mapped to its ASCII
--   equivalent.
--   "Directions (14 -18):" -> "Directions (14-17):" — the source overlaps
--   this range with the next one at Q18, whose stem is a connector
--   question, not a fill-in-the-blank.
-- The first two are printed ranges that would mislead a learner if carried
-- through verbatim. The third is a range that overlaps the next one; every
-- question is asserted to be claimed by exactly one block, which is how the
-- overlap was found.
--
-- RETURN TO VERIFIED: 50 of the 63. The other 13 were
-- already needs_correction BEFORE 281 — mangled fractions, bled-in options
-- and the like — so restoring their context does not clear them. 281's own
-- metadata cannot tell the two apart, so the split comes from
-- review_out_rbi2022/questions_export.json, captured before 281 ran.
--
-- 281 OVER-FLAGGED ONE ROW. Q77 prints its digit-letter-symbol sequence
-- inside its own stem — "the above sequence" refers to text that is there.
-- The back-reference detector could not tell that from a genuine dangling
-- reference. It gets no new text and is returned to verified.
--
-- Q109 stays needs_correction and is not touched. Its series is inline too,
-- so it is not an orphan, but it was already flagged before 281 for a
-- different defect: the source's (Y-18)/5 lost its fraction bar and the
-- stem reads "Y−18 5". That is a real defect and not this migration's.
--
-- ROWS BY SECTION: English Language 23, Quantitative Aptitude 5, Reasoning 35
-- All 63 are on one paper, 06712b2e…, the RBI Grade B 2022 Phase I paper.
-- It is projected and live, so it needs a projection re-sync after this
-- runs. No other paper is touched.
--
-- Statement 2 fires trg_invalidate_pyq_projection_q in reverse: returning a
-- row to verified does not itself republish it. The projection re-sync is
-- what puts these back in front of learners, and it should run only after
-- the text repair has been eyeballed on a sample.
--
-- THE 17 DIRECTIONS BLOCKS, verbatim as prepended:
--
-- Q.1-8  (8 of its questions were flagged)
--   Directions (1 -8): Read the following passage and answer the questions
--   that follow. Some words in the passage have been highlighted to aid in
--   answering the question. The off -cycle meeting of the Monetary Policy
--   Committee (MPC) on May 2 and May 4 and its decision to raise the repo
--   rate to 4.4% sends a clear signal that the Reserve Bank of India (RBI)
--   is committed to its mandate of keeping the consumer price index (CPI)
--   inflation rate at 4% with an upper and lower band of plus or minus 2
--   percentage points. While stating that the policy remains accommodative,
--   it has also expressed its intent to withdraw the accommodative stance.
--   This policy response to global downward risks — including energy price
--   volatility, supply chain disruptions due to geopolitical risks and
--   macroeconomic uncertainties — is welcome. The RBI has re-calibrated the
--   monetary policy corridor. As per the recent MPC off-cycle meeting, the
--   standing deposit facility (SDF) rate stands adjusted to 4.15% and the
--   marginal standing facility (MSF) rate and the Bank Rate to 4.65%.
--   Raising of the cash reserve ratio (CRR) to 4.5% is expected to absorb
--   liquidity of ₹87,000 crore. Till the eruption of conflict in Europe,
--   what was expected on the monetary policy front was a gradual move away
--   from an accommodative stance, spread over a year or so. But the
--   continuing war has necessitated urgent steps. The RBI has thus
--   responded to the charge that it is behind the curve on inflation. High
--   inflation and low growth stare at the global economy, adding to
--   uncertainty. The West is fearing stagflation. The International
--   Monetary Fund (IMF) has revised its global growth forecast for 2022
--   downwards by 0.8 pe rcentage point to 3.6%, in a short period of three
--   months. The fact that the wholesale price index (WPI) inflation rate
--   was continuing at two-digit numbers for a year and the CPI has remained
--   above the upper band of 6% for three consecutive months has been a
--   cause for concern. It is generally agreed that the WPI has a lagged
--   effect on the CPI. So, the RBI will have to tighten the stance further
--   if it is to bring down the CPI inflation rate within the band in the
--   next few months. Hence, more tightening is on the way. High levels of
--   inflation will have a deleterious effect on investment and growth in
--   India. Similarly, the high rate of inflation with very high food and
--   energy components erodes the purchasing power of the common man, and
--   will
--
-- Q.9-10  (2 of its questions were flagged)
--   Directions (9 -10): In the following questions six sentences are given.
--   Further, these sentences may or may not form a contextually meaningful
--   sequence, and one of these sentences is redundant to the context, which
--   has to be eliminated. Rearrange the other sentences to make a
--   contextually meaningful paragraph. The sentence (B), which has already
--   been highlighted, would be the second sentence after rearrangement.
--   Answer the follow-up questions. (A) Thirteen plumes of the gas were
--   observed at the Raspadskya mine, the largest coal mine in Russia, in
--   late January during a single pass of a satellite operated by GHGSat, a
--   commercial emissions-monitoring firm. (B) The finding is another
--   indication of the scope of the problem of curbing emissions of methane,
--   a potent planet-warming gas. (C) By contrast, the highest rate measured
--   at Aliso Canyon, a natural gas storage facility in Southern California
--   that had a major leak for nearly four months in 2015 and 2016, was
--   about 60 metric tons an hour. (D) The total flow rate from all the
--   plumes was estimated at about 87 metric tons (about 95 U.S. tons) an
--   hour. (E) A remote-sensing satellite has detected one of the largest
--   releases of methane from a single industrial site, an underground coal
--   mine in south-central Russia. (F) Mr. Wight said it was not known how
--   long the releases continued at this rate at the mine. But several
--   previous satellite passes had detected emissions in the tens of tons an
--   hour.
--
-- Q.14-17  (4 of its questions were flagged)
--   Directions (14-17): In the following questions, a statement is given
--   with a blank followed by five options. Choose the pair of words that
--   fill in the given blank making the sentence grammatically and
--   contextually correct.
--
-- Q.18-20  (2 of its questions were flagged)
--   Directions (18-20): In each of the following questions, two sentences
--   are given. Five connectors are provided to connect the sentence s. Find
--   the correct option to connect these two sentences without changing the
--   intended meaning.
--
-- Q.21-27  (7 of its questions were flagged)
--   Directions (21 -27): Read the following passage and answer the
--   questions that follow. Some words in the passage have been highlighted
--   to aid in answering the question. Vegetarian diets lower the burden of
--   chronic diseases. Lacto-vegetarians are of ten impressively healthier –
--   sometimes a lot healthier – than meat eaters. It is uncertain whether
--   this advantage extends to vegans. Plant -based diets containing whole
--   grains, nuts, fruits and vegetables are low in saturated fats and
--   cholesterol and higher in fibre, vitamin C, folate, potassium,
--   magnesium, and phytochemicals implicated in the protection against many
--   diseases. Such diets also lower the risk of hypertension and type 2
--   diabetes mellitus. Diets low in fibre and in which chicken and meat are
--   the principal ingredients can dramatically increase the incidence of
--   colorectal cancers. Plant foods are also high in phytochemicals called
--   polyphenols and contain higher proportions of polyunsaturated fatty
--   acids. These substances have recently been shown to have beneficial
--   effects on maintaining the integrity of brain function during the
--   ageing process. Vegetarian diets may help in weight loss and long -term
--   weight control and are associated with longevity. Diets containing
--   animal products are generally higher in fat and calorific value while
--   plant foods are low in energy and are nutrient dense. However, the more
--   limiting a diet is, the more difficult it is to get all the nutrients
--   required by your body. Can vegetarian diets, therefore, be balanced,
--   complete and healthy? The answer is yes. According to the American
--   Dietetic Association “appropriat ely planned vegetarian diets are
--   healthful, nutritionally adequate and may provide health benefits in
--   the prevention and treatment of certain diseases. Well -planned
--   vegetarian diets are suitable for individuals during all stages of the
--   life -cycle and for athletes.” Only the most restrictive vegan diets
--   can perhaps cause nutritional concerns and compromise on calcium, iron,
--   zinc, vitamin B12 and sometimes even protein. Vegetarian meals need not
--   be boring or limiting. Whip up a variety of recipes from plant foods
--   and feast on them. If you can't be a vegetarian, a healthy option would
--   be to limit intake of animal foods and increase intake of fruits and
--   vegetables. Remember what Einstein said: “Nothing will ____________
--   human health and increase chances for survival of life on Earth as much
--   as the evolution to a vegetarian diet.”
--
-- Q.31-35  (5 of its questions were flagged)
--   Direction (31-35): Study the following information carefully and answer
--   the questions given below: Seven classes of different subjects viz.
--   Physics, Hindi, Math, English, Social study, Chemistry and Biology
--   scheduled in school A but not necessarily in the same order. Each of
--   the subject scheduled either for 30 Note: If Subject A scheduled from
--   9:00 am to 10:00 am than its must be scheduled on 9:00/9:30 or 10:00
--   am. Neither scheduled at 9:05 nor scheduled at 9:55. There is 30
--   minutes break given between two classes. Hindi class is scheduled on
--   12:00 noon. No class scheduled betwee n Hindi and Maths. English class
--   scheduled at 2:00pm. There is 1:30 hours gap between English and
--   Biology class which is scheduled after English class. Total time for
--   all subjects is 5 hours. Physics class is scheduled 60 minutes before
--   Maths class. No cla ss is scheduled at 6pm and after 6pm. Chemistry
--   class takes half time than English class and scheduled just after the
--   English class. No class is scheduled at 10:00 am and 5:00 pm. Social
--   study class is scheduled before the class which is scheduled at 3:30
--   pm. English class starts before 2:30pm.
--
-- Q.36-40  (5 of its questions were flagged)
--   Direction ( 36-40): A word arrangement machine when given an input line
--   of words rearranges them following a particular rule in each step. The
--   following is an illustration of input and rearrangement. Input: mgtuh
--   kaops abewm bwxef mctqe aokpw Step I: oivuj maoru adeyo dyzeh oevse
--   aomry Step II: adeyo aomry dyzeh maoru oevse oivuj Step III: adeoy
--   amory dehyz amoru eeosv ijouv Step IV: 26 26 30 22 27 31 Step V: 3 4 4
--   8 8 9 Step V is the final step of given input. Answer the following
--   questions based on the following input: - Input: helof kpest fumap
--   hseub lmodu karlx
--
-- Q.41-42  (2 of its questions were flagged)
--   Directions (41-42): The Delhi government approved a new excise policy ,
--   lowering the minimum age for consumption of alcohol to 21 years.
--   Earlier, the legal age of drinking in New Delhi was 25. With the move,
--   the national capital joins the majority of Indian states in having 21
--   as the legal drinking age. While in some states, the age limit is as
--   low as 18, a few have it at the upper limit of 25. I n some states, the
--   consumption of alcohol is forbidden.
--
-- Q.43-47  (3 of its questions were flagged)
--   Direction (43-47): Study the following information carefully and answer
--   the questions given below. Nine persons live in three floored building
--   marked 1 to 3 from bottom to top respectively. There are three flats on
--   each floor viz. - flat 1, flat 2, and flat 3 from west to east
--   respectively. Only one person lives in each flat. Each person goes to
--   different countries i.e. Iran, USA, Russia, Korea, Oman, Malta, Japan,
--   UK and UAE but not necessarily in the same order. A lives on an odd
--   numbered floor to the immediate west of the one who goes to Korea. F
--   lives two floors below the one who goes to Korea. F lives in an even
--   numbered flat. B lives to the south east flat of the one who goes to
--   USA. B and the one who goes to USA live in odd numbered flat. B lives
--   on an odd numbered floor. C doesn’t go to Korea. C lives to the north
--   east flat of the one who goes t o USA. D lives below A in the same flat
--   with A. The one who goes to UAE lives on the same floor with D but in
--   different flat as F’s flat. The one who goes to Japan lives above B’s
--   flat. E lives to the immediate south west of the one who goes to Japan.
--   G li ves to the east of H in the same floor with E. The one who goes to
--   Oman lives to the west of G. One floor gap is there between I and the
--   one who goes to Malta. The one who goes to Malta lives to the south
--   east of the one who goes to Iran. D doesn’t go to UK.
--
-- Q.48-51  (4 of its questions were flagged)
--   Direction (48-51): Study the following information carefully and answer
--   the questions given below. In a family of three generation there are
--   seven members and three married couples. Each person has different age.
--   Only married couples have child. The one who is sister-in-law of W is
--   20 years old. K is uncle of P who is three years younger than S. W is
--   the only son -in-law of M and has no siblings. T is sister -in-law of K
--   who is 30 years old. K is unmarried and sibling of M. X is grandchild
--   of M and 15 years younger than her aunt. Age of S is not an even
--   number.
--
-- Q.61-65  (2 of its questions were flagged)
--   Direction (61-65): Study the following information carefully and answer
--   the questions given below. Eight persons -A, B, C, D, E, F, G and H
--   were born in different years i.e. 1991, 1995, 2002, 1998, 1985, 2018,
--   2015 and 2010 but not necessarily in the same order. Calculate the age
--   of each person taking the base year 2021. B’s age is a prime number.
--   There is four years gap between B and H. Two persons were born between
--   B and E who was born in odd numbered year. The number of persons born
--   before E is same as the number of persons born after F. G’s age is a
--   multiple of 3 but less than B. The difference between the age of A and
--   D is neither even nor prime number. C’s age is more than E’s age but
--   not less than F’s age. E is older than F.
--
-- Q.66-68  (3 of its questions were flagged)
--   Directions (66-68): Study the following information carefully and
--   answer the questions given below- In a certain code language:
--   “Enforcement directorate would acquitted soon” is coded as “19LG 13LV
--   38FW 4FW 34LM” “Interrogation release completely added stems” is coded
--   as “23LM 23VV 18LB 5VW 39VH” “Prevention corruption allegedly purchase
--   campaigning “is coded as “34LM 18FM 13VB 37FV 4RT”
--
-- Q.69-73  (3 of its questions were flagged)
--   Direction (69-73): Study the following information carefully and answer
--   the questions given below: Eight persons sit in a row face north at
--   consecutive multiple distance of 7m. All the persons face towards
--   north. A sits 63m left of S. R sits immediate right of S. Distance
--   between A and R is same as the distance between F and R. Difference
--   between the total distance of W and D to the total distance of D and Y
--   is 7m. Now F goes in the north and walks 50m to reach point C then,
--   takes right turn and walks 98m to reach at point K after that F in the
--   North-west of U. W goes in the south and walks 20m to reach point Q
--   then he takes his left and walks some distance to reach south of R.
--
-- Q.78-82  (3 of its questions were flagged)
--   Direction (78-82): Study the following information carefully and answer
--   the questions given below: A certain number of persons sit around a
--   circular table facing the centre. Few of them like different colours-
--   Red, Green, Yellow and Black but not necessarily in the same order.
--   More than 9 persons sit around a table. Each of the neighbours sits at
--   equal distance from each other. Two persons sit between Q and A who
--   likes Green. T is an immediate neighbour of U who likes Red. U sits 2nd
--   to the right of A. There are as many persons sit between T and W as
--   between Q and W. R sits 3rd to the right of W and is immediate
--   neighbour of Q. R and the one who likes Black are immediate neighbours.
--   The one who likes yellow sits 2nd to the right of the one who likes
--   Black. U and the one who likes Yellow are not an immediate neighbour.
--   The number of persons sits between T and R is less than five when
--   counted to the right of T.
--
-- Q.86-90  (5 of its questions were flagged)
--   Direction (86-90): Study the following information carefully and answer
--   the questions given below. Eight boxes are kept in eight different
--   shelves such that shelves are marked as 1 to 8 from bottom to top
--   respectively. Each box contains different items i.e., Utensil, Pencil,
--   Pen, Clothes, Marker, Book, Bottle and Toffees but not necessarily in
--   the same order. Box P is kept at an even numbered shelf and above box
--   Q. Two boxes are kept between box P and box Q. The box which contains
--   marker kept four boxes above box W. Box Q doesn’t contain marker. Box W
--   is kept at an odd numbered shelf. The number of boxes kept above the
--   box which contains marker is one less than the number of boxes kept
--   below the box which contains pencil. More than two boxes are kept
--   between box P and box T which is kept just below the box which contains
--   bottle. Box R and box U kept at an adjacent shelf. Three boxes are kept
--   between the box which contains pen and box R. Box W and the box which
--   contains pen are not kept adjacent to each other. Box S is kept below
--   the box which contains book. Three boxes are kept between box V and the
--   box which contains clothes. Box T doesn’t contain utensil.
--
-- Q.105-107  (3 of its questions were flagged)
--   Direction (105-107): There are two equations I and II given, solve
--   these equations and answer the following questions given below.
--   Equation I. px2 −9𝑥 + 7 = 0 Equation II. qy2 – 8y + 4 =0 Note: (A) Both
--   p and q are positive integers. (B) One of the roots of equation II is 2
--   3. (C) The ratio of highest root of equation I to the highest root of
--   equation II is 7 : 4.
--
-- Q.115-119  (2 of its questions were flagged)
--   Directions ( 115-119): Read the following passage carefully and answer
--   the questions given below. In a society, people like three different
--   types of cars i.e. A, B & C. Ratio of people who like car A to car C is
--   29 :42 and people who like only car A&C together is one fourth of the
--   people who like only car B. People who like only car C is 50 more than
--   four times of the people who like only car A & B together. 10 people
--   like all the three types of cars which is equal to people who like only
--   car B&C together. People who like only car C is twice of the people who
--   like only car A and people who like car C is 210 . All people like
--   either of the car.
--
-- BEFORE AND AFTER, the 63 rows. BEFORE is the stem as loaded; AFTER is its block
-- above, a blank line, then that same stem unchanged.
--   Q1    need stays flagged  + 2426ch  'What can be inferred about the economy of th'
--   Q2    veri ->verified     + 2426ch  'Which of the following was/were the objectiv'
--   Q3    veri ->verified     + 2426ch  'Which of the following come(s) under the cha'
--   Q4    need stays flagged  + 2426ch  'Which of the following if correct, most inva'
--   Q5    need stays flagged  + 2426ch  'Which of the following is true according to '
--   Q6    need stays flagged  + 2426ch  'What is the primary focus of the author in t'
--   Q7    need stays flagged  + 2426ch  'From among the following given options, choo'
--   Q8    need stays flagged  + 2426ch  'Which of the following words is most opposit'
--   Q9    need stays flagged  + 1462ch  'Which is the fourth sentence after rearrange'
--   Q10   need stays flagged  + 1462ch  'What is the correct rearrangement of the giv'
--   Q14   veri ->verified     +  223ch  'The king released the lion from its cage int'
--   Q15   veri ->verified     +  223ch  'Observing all the reports, the supervisor no'
--   Q16   veri ->verified     +  223ch  'As soon as he entered the room, he was unabl'
--   Q17   veri ->verified     +  223ch  'Noticing how the dimensions of the bridge we'
--   Q18   veri ->verified     +  232ch  '(i) BIMSTEC has, finally, taken measures to '
--   Q19   veri ->verified     +  232ch  '(i) Earlier in March, Musk said he would put'
--   Q21   veri ->verified     + 2461ch  'Which of the following is not a benefit of a'
--   Q22   veri ->verified     + 2461ch  'Which of the following qualifies as a differ'
--   Q23   veri ->verified     + 2461ch  'How is proper planning important for a veget'
--   Q24   need stays flagged  + 2461ch  'Which of the following ways can help in maki'
--   Q25   need stays flagged  + 2461ch  'Which of the following words can most approp'
--   Q26   need stays flagged  + 2461ch  'Which of the following words is the most sim'
--   Q27   need stays flagged  + 2461ch  'Choose the word from the following options w'
--   Q31   veri ->verified     + 1141ch  'Which of the following time for Chemistry cl'
--   Q32   veri ->verified     + 1141ch  'Which of the following subject is scheduled '
--   Q33   veri ->verified     + 1141ch  'How many classes scheduled between Chemistry'
--   Q34   veri ->verified     + 1141ch  '____ class is scheduled 150 minutes after Ma'
--   Q35   veri ->verified     + 1141ch  'The number of classes scheduled between Phys'
--   Q36   veri ->verified     +  573ch  'Which among the following word is third from'
--   Q37   veri ->verified     +  573ch  'How many letters are there between third let'
--   Q38   veri ->verified     +  573ch  'What is the sum of the even numbers appeared'
--   Q39   veri ->verified     +  573ch  'What is the difference between the numbers w'
--   Q40   veri ->verified     +  573ch  'Which among the following word is second to '
--   Q41   veri ->verified     +  457ch  'What could be the fallout of the new excise '
--   Q42   veri ->verified     +  457ch  'Which of the following can be postulated fro'
--   Q45   veri ->verified     + 1383ch  'Which among the following statement(s) is/ar'
--   Q46   veri ->verified     + 1383ch  'In which among the following floor and flat '
--   Q47   veri ->verified     + 1383ch  'Which a mong the following pair of persons l'
--   Q48   veri ->verified     +  569ch  'How X is related to W?'
--   Q49   veri ->verified     +  569ch  'What is the sum of the ages of X mother’s an'
--   Q50   veri ->verified     +  569ch  'Who among the following is the child of T?'
--   Q51   veri ->verified     +  569ch  'What is the ratio of the ages of P’s uncle a'
--   Q63   veri ->verified     +  743ch  'Who among the following is the youngest pers'
--   Q64   veri ->verified     +  743ch  'Which among the following statement(s) is/ar'
--   Q66   veri ->verified     +  392ch  'What is the code for “Public Health” in the '
--   Q67   veri ->verified     +  392ch  'The code “9RR 28VI” is coded for which of th'
--   Q68   veri ->verified     +  392ch  'What is the code for “German language” in th'
--   Q69   veri ->verified     +  688ch  'Find the sum of the distance walk by W and F'
--   Q70   veri ->verified     +  688ch  'In which direction is point C with respect t'
--   Q71   veri ->verified     +  688ch  'What is the total distance between S and the'
--   Q78   veri ->verified     +  924ch  'Who among the following sits 8th to the righ'
--   Q79   veri ->verified     +  924ch  '___ faces to the one who likes ____ colour?'
--   Q80   need stays flagged  +  924ch  'How many persons sit around the table?'
--   Q86   veri ->verified     + 1177ch  'Which among the following combination is cor'
--   Q87   veri ->verified     + 1177ch  'How many boxes are kept between box S and th'
--   Q88   veri ->verified     + 1177ch  'Which among the following box contains marke'
--   Q89   veri ->verified     + 1177ch  'If all the boxes are arranged from top to bo'
--   Q90   veri ->verified     + 1177ch  'In which of the following shelf does the box'
--   Q105  veri ->verified     +  368ch  'Find the ratio of smallest root of equation '
--   Q106  veri ->verified     +  368ch  'Find the value of (p + q).'
--   Q107  veri ->verified     +  368ch  'Find the both roots of equation (p+q)2a2 + ('
--   Q115  veri ->verified     +  653ch  'Find the ratio of people who like only car C'
--   Q116  veri ->verified     +  653ch  'People like only car A&C together is what pe'
--
-- Guarded on the current value throughout: a no-op if already repaired.

BEGIN;

-- 1. Prepend each set's Directions block to its questions.
UPDATE public.pyq_questions q
SET question_text = v.question_text
FROM (VALUES
  ('7ab77868-58c2-48cd-ab52-a365a4e0beec'::uuid,
   'Directions (1 -8): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. The off -cycle meeting of the Monetary Policy Committee (MPC) on May 2 and May 4 and its decision to raise the repo rate to 4.4% sends a clear signal that the Reserve Bank of India (RBI) is committed to its mandate of keeping the consumer price index (CPI) inflation rate at 4% with an upper and lower band of plus or minus 2 percentage points. While stating that the policy remains accommodative, it has also expressed its intent to withdraw the accommodative stance. This policy response to global downward risks — including energy price volatility, supply chain disruptions due to geopolitical risks and macroeconomic uncertainties — is welcome. The RBI has re-calibrated the monetary policy corridor. As per the recent MPC off-cycle meeting, the standing deposit facility (SDF) rate stands adjusted to 4.15% and the marginal standing facility (MSF) rate and the Bank Rate to 4.65%. Raising of the cash reserve ratio (CRR) to 4.5% is expected to absorb liquidity of ₹87,000 crore. Till the eruption of conflict in Europe, what was expected on the monetary policy front was a gradual move away from an accommodative stance, spread over a year or so. But the continuing war has necessitated urgent steps. The RBI has thus responded to the charge that it is behind the curve on inflation. High inflation and low growth stare at the global economy, adding to uncertainty. The West is fearing stagflation. The International Monetary Fund (IMF) has revised its global growth forecast for 2022 downwards by 0.8 pe rcentage point to 3.6%, in a short period of three months. The fact that the wholesale price index (WPI) inflation rate was continuing at two-digit numbers for a year and the CPI has remained above the upper band of 6% for three consecutive months has been a cause for concern. It is generally agreed that the WPI has a lagged effect on the CPI. So, the RBI will have to tighten the stance further if it is to bring down the CPI inflation rate within the band in the next few months. Hence, more tightening is on the way. High levels of inflation will have a deleterious effect on investment and growth in India. Similarly, the high rate of inflation with very high food and energy components erodes the purchasing power of the common man, and will

What can be inferred about the economy of the world from the passage?'),
  ('ef384cab-d616-4299-8b68-78568d1dca8c'::uuid,
   'Directions (1 -8): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. The off -cycle meeting of the Monetary Policy Committee (MPC) on May 2 and May 4 and its decision to raise the repo rate to 4.4% sends a clear signal that the Reserve Bank of India (RBI) is committed to its mandate of keeping the consumer price index (CPI) inflation rate at 4% with an upper and lower band of plus or minus 2 percentage points. While stating that the policy remains accommodative, it has also expressed its intent to withdraw the accommodative stance. This policy response to global downward risks — including energy price volatility, supply chain disruptions due to geopolitical risks and macroeconomic uncertainties — is welcome. The RBI has re-calibrated the monetary policy corridor. As per the recent MPC off-cycle meeting, the standing deposit facility (SDF) rate stands adjusted to 4.15% and the marginal standing facility (MSF) rate and the Bank Rate to 4.65%. Raising of the cash reserve ratio (CRR) to 4.5% is expected to absorb liquidity of ₹87,000 crore. Till the eruption of conflict in Europe, what was expected on the monetary policy front was a gradual move away from an accommodative stance, spread over a year or so. But the continuing war has necessitated urgent steps. The RBI has thus responded to the charge that it is behind the curve on inflation. High inflation and low growth stare at the global economy, adding to uncertainty. The West is fearing stagflation. The International Monetary Fund (IMF) has revised its global growth forecast for 2022 downwards by 0.8 pe rcentage point to 3.6%, in a short period of three months. The fact that the wholesale price index (WPI) inflation rate was continuing at two-digit numbers for a year and the CPI has remained above the upper band of 6% for three consecutive months has been a cause for concern. It is generally agreed that the WPI has a lagged effect on the CPI. So, the RBI will have to tighten the stance further if it is to bring down the CPI inflation rate within the band in the next few months. Hence, more tightening is on the way. High levels of inflation will have a deleterious effect on investment and growth in India. Similarly, the high rate of inflation with very high food and energy components erodes the purchasing power of the common man, and will

Which of the following was/were the objectives of the off -cycle meeting by RBI?'),
  ('352bd671-f233-4053-8a94-f5cce5050c70'::uuid,
   'Directions (1 -8): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. The off -cycle meeting of the Monetary Policy Committee (MPC) on May 2 and May 4 and its decision to raise the repo rate to 4.4% sends a clear signal that the Reserve Bank of India (RBI) is committed to its mandate of keeping the consumer price index (CPI) inflation rate at 4% with an upper and lower band of plus or minus 2 percentage points. While stating that the policy remains accommodative, it has also expressed its intent to withdraw the accommodative stance. This policy response to global downward risks — including energy price volatility, supply chain disruptions due to geopolitical risks and macroeconomic uncertainties — is welcome. The RBI has re-calibrated the monetary policy corridor. As per the recent MPC off-cycle meeting, the standing deposit facility (SDF) rate stands adjusted to 4.15% and the marginal standing facility (MSF) rate and the Bank Rate to 4.65%. Raising of the cash reserve ratio (CRR) to 4.5% is expected to absorb liquidity of ₹87,000 crore. Till the eruption of conflict in Europe, what was expected on the monetary policy front was a gradual move away from an accommodative stance, spread over a year or so. But the continuing war has necessitated urgent steps. The RBI has thus responded to the charge that it is behind the curve on inflation. High inflation and low growth stare at the global economy, adding to uncertainty. The West is fearing stagflation. The International Monetary Fund (IMF) has revised its global growth forecast for 2022 downwards by 0.8 pe rcentage point to 3.6%, in a short period of three months. The fact that the wholesale price index (WPI) inflation rate was continuing at two-digit numbers for a year and the CPI has remained above the upper band of 6% for three consecutive months has been a cause for concern. It is generally agreed that the WPI has a lagged effect on the CPI. So, the RBI will have to tighten the stance further if it is to bring down the CPI inflation rate within the band in the next few months. Hence, more tightening is on the way. High levels of inflation will have a deleterious effect on investment and growth in India. Similarly, the high rate of inflation with very high food and energy components erodes the purchasing power of the common man, and will

Which of the following come(s) under the changes introduced by the RBI’s new policies?'),
  ('b6c1b177-a3d2-4ed8-8ae3-245e80d9fe1f'::uuid,
   'Directions (1 -8): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. The off -cycle meeting of the Monetary Policy Committee (MPC) on May 2 and May 4 and its decision to raise the repo rate to 4.4% sends a clear signal that the Reserve Bank of India (RBI) is committed to its mandate of keeping the consumer price index (CPI) inflation rate at 4% with an upper and lower band of plus or minus 2 percentage points. While stating that the policy remains accommodative, it has also expressed its intent to withdraw the accommodative stance. This policy response to global downward risks — including energy price volatility, supply chain disruptions due to geopolitical risks and macroeconomic uncertainties — is welcome. The RBI has re-calibrated the monetary policy corridor. As per the recent MPC off-cycle meeting, the standing deposit facility (SDF) rate stands adjusted to 4.15% and the marginal standing facility (MSF) rate and the Bank Rate to 4.65%. Raising of the cash reserve ratio (CRR) to 4.5% is expected to absorb liquidity of ₹87,000 crore. Till the eruption of conflict in Europe, what was expected on the monetary policy front was a gradual move away from an accommodative stance, spread over a year or so. But the continuing war has necessitated urgent steps. The RBI has thus responded to the charge that it is behind the curve on inflation. High inflation and low growth stare at the global economy, adding to uncertainty. The West is fearing stagflation. The International Monetary Fund (IMF) has revised its global growth forecast for 2022 downwards by 0.8 pe rcentage point to 3.6%, in a short period of three months. The fact that the wholesale price index (WPI) inflation rate was continuing at two-digit numbers for a year and the CPI has remained above the upper band of 6% for three consecutive months has been a cause for concern. It is generally agreed that the WPI has a lagged effect on the CPI. So, the RBI will have to tighten the stance further if it is to bring down the CPI inflation rate within the band in the next few months. Hence, more tightening is on the way. High levels of inflation will have a deleterious effect on investment and growth in India. Similarly, the high rate of inflation with very high food and energy components erodes the purchasing power of the common man, and will

Which of the following if correct, most invalidates the arguments in the third passage?'),
  ('b3de135a-e124-4dec-a1aa-90585abbdb45'::uuid,
   'Directions (1 -8): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. The off -cycle meeting of the Monetary Policy Committee (MPC) on May 2 and May 4 and its decision to raise the repo rate to 4.4% sends a clear signal that the Reserve Bank of India (RBI) is committed to its mandate of keeping the consumer price index (CPI) inflation rate at 4% with an upper and lower band of plus or minus 2 percentage points. While stating that the policy remains accommodative, it has also expressed its intent to withdraw the accommodative stance. This policy response to global downward risks — including energy price volatility, supply chain disruptions due to geopolitical risks and macroeconomic uncertainties — is welcome. The RBI has re-calibrated the monetary policy corridor. As per the recent MPC off-cycle meeting, the standing deposit facility (SDF) rate stands adjusted to 4.15% and the marginal standing facility (MSF) rate and the Bank Rate to 4.65%. Raising of the cash reserve ratio (CRR) to 4.5% is expected to absorb liquidity of ₹87,000 crore. Till the eruption of conflict in Europe, what was expected on the monetary policy front was a gradual move away from an accommodative stance, spread over a year or so. But the continuing war has necessitated urgent steps. The RBI has thus responded to the charge that it is behind the curve on inflation. High inflation and low growth stare at the global economy, adding to uncertainty. The West is fearing stagflation. The International Monetary Fund (IMF) has revised its global growth forecast for 2022 downwards by 0.8 pe rcentage point to 3.6%, in a short period of three months. The fact that the wholesale price index (WPI) inflation rate was continuing at two-digit numbers for a year and the CPI has remained above the upper band of 6% for three consecutive months has been a cause for concern. It is generally agreed that the WPI has a lagged effect on the CPI. So, the RBI will have to tighten the stance further if it is to bring down the CPI inflation rate within the band in the next few months. Hence, more tightening is on the way. High levels of inflation will have a deleterious effect on investment and growth in India. Similarly, the high rate of inflation with very high food and energy components erodes the purchasing power of the common man, and will

Which of the following is true according to the data in the passage?'),
  ('75123782-9979-4c2d-8a7d-73120c797eef'::uuid,
   'Directions (1 -8): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. The off -cycle meeting of the Monetary Policy Committee (MPC) on May 2 and May 4 and its decision to raise the repo rate to 4.4% sends a clear signal that the Reserve Bank of India (RBI) is committed to its mandate of keeping the consumer price index (CPI) inflation rate at 4% with an upper and lower band of plus or minus 2 percentage points. While stating that the policy remains accommodative, it has also expressed its intent to withdraw the accommodative stance. This policy response to global downward risks — including energy price volatility, supply chain disruptions due to geopolitical risks and macroeconomic uncertainties — is welcome. The RBI has re-calibrated the monetary policy corridor. As per the recent MPC off-cycle meeting, the standing deposit facility (SDF) rate stands adjusted to 4.15% and the marginal standing facility (MSF) rate and the Bank Rate to 4.65%. Raising of the cash reserve ratio (CRR) to 4.5% is expected to absorb liquidity of ₹87,000 crore. Till the eruption of conflict in Europe, what was expected on the monetary policy front was a gradual move away from an accommodative stance, spread over a year or so. But the continuing war has necessitated urgent steps. The RBI has thus responded to the charge that it is behind the curve on inflation. High inflation and low growth stare at the global economy, adding to uncertainty. The West is fearing stagflation. The International Monetary Fund (IMF) has revised its global growth forecast for 2022 downwards by 0.8 pe rcentage point to 3.6%, in a short period of three months. The fact that the wholesale price index (WPI) inflation rate was continuing at two-digit numbers for a year and the CPI has remained above the upper band of 6% for three consecutive months has been a cause for concern. It is generally agreed that the WPI has a lagged effect on the CPI. So, the RBI will have to tighten the stance further if it is to bring down the CPI inflation rate within the band in the next few months. Hence, more tightening is on the way. High levels of inflation will have a deleterious effect on investment and growth in India. Similarly, the high rate of inflation with very high food and energy components erodes the purchasing power of the common man, and will

What is the primary focus of the author in the passage?'),
  ('df63317c-bdab-4271-9c5a-1b2c2982830c'::uuid,
   'Directions (1 -8): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. The off -cycle meeting of the Monetary Policy Committee (MPC) on May 2 and May 4 and its decision to raise the repo rate to 4.4% sends a clear signal that the Reserve Bank of India (RBI) is committed to its mandate of keeping the consumer price index (CPI) inflation rate at 4% with an upper and lower band of plus or minus 2 percentage points. While stating that the policy remains accommodative, it has also expressed its intent to withdraw the accommodative stance. This policy response to global downward risks — including energy price volatility, supply chain disruptions due to geopolitical risks and macroeconomic uncertainties — is welcome. The RBI has re-calibrated the monetary policy corridor. As per the recent MPC off-cycle meeting, the standing deposit facility (SDF) rate stands adjusted to 4.15% and the marginal standing facility (MSF) rate and the Bank Rate to 4.65%. Raising of the cash reserve ratio (CRR) to 4.5% is expected to absorb liquidity of ₹87,000 crore. Till the eruption of conflict in Europe, what was expected on the monetary policy front was a gradual move away from an accommodative stance, spread over a year or so. But the continuing war has necessitated urgent steps. The RBI has thus responded to the charge that it is behind the curve on inflation. High inflation and low growth stare at the global economy, adding to uncertainty. The West is fearing stagflation. The International Monetary Fund (IMF) has revised its global growth forecast for 2022 downwards by 0.8 pe rcentage point to 3.6%, in a short period of three months. The fact that the wholesale price index (WPI) inflation rate was continuing at two-digit numbers for a year and the CPI has remained above the upper band of 6% for three consecutive months has been a cause for concern. It is generally agreed that the WPI has a lagged effect on the CPI. So, the RBI will have to tighten the stance further if it is to bring down the CPI inflation rate within the band in the next few months. Hence, more tightening is on the way. High levels of inflation will have a deleterious effect on investment and growth in India. Similarly, the high rate of inflation with very high food and energy components erodes the purchasing power of the common man, and will

From among the following given options, choose the word most similar in meaning to the highlighted word “gradual”, as used in the context of the passage.'),
  ('c6e7a666-52f0-4cd0-b42c-4d3c78066736'::uuid,
   'Directions (1 -8): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. The off -cycle meeting of the Monetary Policy Committee (MPC) on May 2 and May 4 and its decision to raise the repo rate to 4.4% sends a clear signal that the Reserve Bank of India (RBI) is committed to its mandate of keeping the consumer price index (CPI) inflation rate at 4% with an upper and lower band of plus or minus 2 percentage points. While stating that the policy remains accommodative, it has also expressed its intent to withdraw the accommodative stance. This policy response to global downward risks — including energy price volatility, supply chain disruptions due to geopolitical risks and macroeconomic uncertainties — is welcome. The RBI has re-calibrated the monetary policy corridor. As per the recent MPC off-cycle meeting, the standing deposit facility (SDF) rate stands adjusted to 4.15% and the marginal standing facility (MSF) rate and the Bank Rate to 4.65%. Raising of the cash reserve ratio (CRR) to 4.5% is expected to absorb liquidity of ₹87,000 crore. Till the eruption of conflict in Europe, what was expected on the monetary policy front was a gradual move away from an accommodative stance, spread over a year or so. But the continuing war has necessitated urgent steps. The RBI has thus responded to the charge that it is behind the curve on inflation. High inflation and low growth stare at the global economy, adding to uncertainty. The West is fearing stagflation. The International Monetary Fund (IMF) has revised its global growth forecast for 2022 downwards by 0.8 pe rcentage point to 3.6%, in a short period of three months. The fact that the wholesale price index (WPI) inflation rate was continuing at two-digit numbers for a year and the CPI has remained above the upper band of 6% for three consecutive months has been a cause for concern. It is generally agreed that the WPI has a lagged effect on the CPI. So, the RBI will have to tighten the stance further if it is to bring down the CPI inflation rate within the band in the next few months. Hence, more tightening is on the way. High levels of inflation will have a deleterious effect on investment and growth in India. Similarly, the high rate of inflation with very high food and energy components erodes the purchasing power of the common man, and will

Which of the following words is most opposite in meaning to the highlighted word “deleterious”?'),
  ('25a6d571-f42d-4421-af84-c420f787c889'::uuid,
   'Directions (9 -10): In the following questions six sentences are given. Further, these sentences may or may not form a contextually meaningful sequence, and one of these sentences is redundant to the context, which has to be eliminated. Rearrange the other sentences to make a contextually meaningful paragraph. The sentence (B), which has already been highlighted, would be the second sentence after rearrangement. Answer the follow-up questions. (A) Thirteen plumes of the gas were observed at the Raspadskya mine, the largest coal mine in Russia, in late January during a single pass of a satellite operated by GHGSat, a commercial emissions-monitoring firm. (B) The finding is another indication of the scope of the problem of curbing emissions of methane, a potent planet-warming gas. (C) By contrast, the highest rate measured at Aliso Canyon, a natural gas storage facility in Southern California that had a major leak for nearly four months in 2015 and 2016, was about 60 metric tons an hour. (D) The total flow rate from all the plumes was estimated at about 87 metric tons (about 95 U.S. tons) an hour. (E) A remote-sensing satellite has detected one of the largest releases of methane from a single industrial site, an underground coal mine in south-central Russia. (F) Mr. Wight said it was not known how long the releases continued at this rate at the mine. But several previous satellite passes had detected emissions in the tens of tons an hour.

Which is the fourth sentence after rearrangement?'),
  ('a59096b1-7614-42ee-a16c-069d2091d0a7'::uuid,
   'Directions (9 -10): In the following questions six sentences are given. Further, these sentences may or may not form a contextually meaningful sequence, and one of these sentences is redundant to the context, which has to be eliminated. Rearrange the other sentences to make a contextually meaningful paragraph. The sentence (B), which has already been highlighted, would be the second sentence after rearrangement. Answer the follow-up questions. (A) Thirteen plumes of the gas were observed at the Raspadskya mine, the largest coal mine in Russia, in late January during a single pass of a satellite operated by GHGSat, a commercial emissions-monitoring firm. (B) The finding is another indication of the scope of the problem of curbing emissions of methane, a potent planet-warming gas. (C) By contrast, the highest rate measured at Aliso Canyon, a natural gas storage facility in Southern California that had a major leak for nearly four months in 2015 and 2016, was about 60 metric tons an hour. (D) The total flow rate from all the plumes was estimated at about 87 metric tons (about 95 U.S. tons) an hour. (E) A remote-sensing satellite has detected one of the largest releases of methane from a single industrial site, an underground coal mine in south-central Russia. (F) Mr. Wight said it was not known how long the releases continued at this rate at the mine. But several previous satellite passes had detected emissions in the tens of tons an hour.

What is the correct rearrangement of the given sentences?'),
  ('25c14b8a-2690-493f-b413-f37607227515'::uuid,
   'Directions (14-17): In the following questions, a statement is given with a blank followed by five options. Choose the pair of words that fill in the given blank making the sentence grammatically and contextually correct.

The king released the lion from its cage into the arena where the champion stood, and by t he end, the champion ultimately turned out to be _______________.'),
  ('e68143e6-4333-414e-bf1c-493ff2df62f7'::uuid,
   'Directions (14-17): In the following questions, a statement is given with a blank followed by five options. Choose the pair of words that fill in the given blank making the sentence grammatically and contextually correct.

Observing all the reports, the supervisor noted that the productivity of the wareho use was _____________ for the company’s needs.'),
  ('8bf962d0-59b7-4432-9b0b-ed8cc1c4d8fd'::uuid,
   'Directions (14-17): In the following questions, a statement is given with a blank followed by five options. Choose the pair of words that fill in the given blank making the sentence grammatically and contextually correct.

As soon as he entered the room, he was unable to see anything due to the stark ____________ inside.'),
  ('5d56b020-e123-4f86-9b50-0838afcb3334'::uuid,
   'Directions (14-17): In the following questions, a statement is given with a blank followed by five options. Choose the pair of words that fill in the given blank making the sentence grammatically and contextually correct.

Noticing how the dimensions of the bridge were different than that of others in the city, my guest asked me why the bridg e was so _____________________.'),
  ('82f16a8f-5894-446b-b16c-b2a82a0f8697'::uuid,
   'Directions (18-20): In each of the following questions, two sentences are given. Five connectors are provided to connect the sentence s. Find the correct option to connect these two sentences without changing the intended meaning.

(i) BIMSTEC has, finally, taken measures to strengthen the Secretariat, (ii) some members are yet to extend adequate personnel support to it.'),
  ('4ff3c2c3-6c64-4d6c-bf0f-447aa3183c49'::uuid,
   'Directions (18-20): In each of the following questions, two sentences are given. Five connectors are provided to connect the sentence s. Find the correct option to connect these two sentences without changing the intended meaning.

(i) Earlier in March, Musk said he would put the deal "temporarily on hold", (ii) he waits for the social media company to provide more of its data.'),
  ('dcdc4a16-21c3-4d49-a088-92378686f825'::uuid,
   'Directions (21 -27): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. Vegetarian diets lower the burden of chronic diseases. Lacto-vegetarians are of ten impressively healthier – sometimes a lot healthier – than meat eaters. It is uncertain whether this advantage extends to vegans. Plant -based diets containing whole grains, nuts, fruits and vegetables are low in saturated fats and cholesterol and higher in fibre, vitamin C, folate, potassium, magnesium, and phytochemicals implicated in the protection against many diseases. Such diets also lower the risk of hypertension and type 2 diabetes mellitus. Diets low in fibre and in which chicken and meat are the principal ingredients can dramatically increase the incidence of colorectal cancers. Plant foods are also high in phytochemicals called polyphenols and contain higher proportions of polyunsaturated fatty acids. These substances have recently been shown to have beneficial effects on maintaining the integrity of brain function during the ageing process. Vegetarian diets may help in weight loss and long -term weight control and are associated with longevity. Diets containing animal products are generally higher in fat and calorific value while plant foods are low in energy and are nutrient dense. However, the more limiting a diet is, the more difficult it is to get all the nutrients required by your body. Can vegetarian diets, therefore, be balanced, complete and healthy? The answer is yes. According to the American Dietetic Association “appropriat ely planned vegetarian diets are healthful, nutritionally adequate and may provide health benefits in the prevention and treatment of certain diseases. Well -planned vegetarian diets are suitable for individuals during all stages of the life -cycle and for athletes.” Only the most restrictive vegan diets can perhaps cause nutritional concerns and compromise on calcium, iron, zinc, vitamin B12 and sometimes even protein. Vegetarian meals need not be boring or limiting. Whip up a variety of recipes from plant foods and feast on them. If you can''t be a vegetarian, a healthy option would be to limit intake of animal foods and increase intake of fruits and vegetables. Remember what Einstein said: “Nothing will ____________ human health and increase chances for survival of life on Earth as much as the evolution to a vegetarian diet.”

Which of the following is not a benefit of adopting a vegetarian diet?'),
  ('7eabd9c3-f15e-4950-84e7-44ecee473a60'::uuid,
   'Directions (21 -27): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. Vegetarian diets lower the burden of chronic diseases. Lacto-vegetarians are of ten impressively healthier – sometimes a lot healthier – than meat eaters. It is uncertain whether this advantage extends to vegans. Plant -based diets containing whole grains, nuts, fruits and vegetables are low in saturated fats and cholesterol and higher in fibre, vitamin C, folate, potassium, magnesium, and phytochemicals implicated in the protection against many diseases. Such diets also lower the risk of hypertension and type 2 diabetes mellitus. Diets low in fibre and in which chicken and meat are the principal ingredients can dramatically increase the incidence of colorectal cancers. Plant foods are also high in phytochemicals called polyphenols and contain higher proportions of polyunsaturated fatty acids. These substances have recently been shown to have beneficial effects on maintaining the integrity of brain function during the ageing process. Vegetarian diets may help in weight loss and long -term weight control and are associated with longevity. Diets containing animal products are generally higher in fat and calorific value while plant foods are low in energy and are nutrient dense. However, the more limiting a diet is, the more difficult it is to get all the nutrients required by your body. Can vegetarian diets, therefore, be balanced, complete and healthy? The answer is yes. According to the American Dietetic Association “appropriat ely planned vegetarian diets are healthful, nutritionally adequate and may provide health benefits in the prevention and treatment of certain diseases. Well -planned vegetarian diets are suitable for individuals during all stages of the life -cycle and for athletes.” Only the most restrictive vegan diets can perhaps cause nutritional concerns and compromise on calcium, iron, zinc, vitamin B12 and sometimes even protein. Vegetarian meals need not be boring or limiting. Whip up a variety of recipes from plant foods and feast on them. If you can''t be a vegetarian, a healthy option would be to limit intake of animal foods and increase intake of fruits and vegetables. Remember what Einstein said: “Nothing will ____________ human health and increase chances for survival of life on Earth as much as the evolution to a vegetarian diet.”

Which of the following qualifies as a difference between a vegetarian and a non -vegetarian diet?'),
  ('3446de24-1e14-47eb-852f-b83170f6e897'::uuid,
   'Directions (21 -27): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. Vegetarian diets lower the burden of chronic diseases. Lacto-vegetarians are of ten impressively healthier – sometimes a lot healthier – than meat eaters. It is uncertain whether this advantage extends to vegans. Plant -based diets containing whole grains, nuts, fruits and vegetables are low in saturated fats and cholesterol and higher in fibre, vitamin C, folate, potassium, magnesium, and phytochemicals implicated in the protection against many diseases. Such diets also lower the risk of hypertension and type 2 diabetes mellitus. Diets low in fibre and in which chicken and meat are the principal ingredients can dramatically increase the incidence of colorectal cancers. Plant foods are also high in phytochemicals called polyphenols and contain higher proportions of polyunsaturated fatty acids. These substances have recently been shown to have beneficial effects on maintaining the integrity of brain function during the ageing process. Vegetarian diets may help in weight loss and long -term weight control and are associated with longevity. Diets containing animal products are generally higher in fat and calorific value while plant foods are low in energy and are nutrient dense. However, the more limiting a diet is, the more difficult it is to get all the nutrients required by your body. Can vegetarian diets, therefore, be balanced, complete and healthy? The answer is yes. According to the American Dietetic Association “appropriat ely planned vegetarian diets are healthful, nutritionally adequate and may provide health benefits in the prevention and treatment of certain diseases. Well -planned vegetarian diets are suitable for individuals during all stages of the life -cycle and for athletes.” Only the most restrictive vegan diets can perhaps cause nutritional concerns and compromise on calcium, iron, zinc, vitamin B12 and sometimes even protein. Vegetarian meals need not be boring or limiting. Whip up a variety of recipes from plant foods and feast on them. If you can''t be a vegetarian, a healthy option would be to limit intake of animal foods and increase intake of fruits and vegetables. Remember what Einstein said: “Nothing will ____________ human health and increase chances for survival of life on Earth as much as the evolution to a vegetarian diet.”

How is proper planning important for a vegetarian li festyle?'),
  ('4c028d7f-9b33-4086-9d43-8d2b5958f84d'::uuid,
   'Directions (21 -27): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. Vegetarian diets lower the burden of chronic diseases. Lacto-vegetarians are of ten impressively healthier – sometimes a lot healthier – than meat eaters. It is uncertain whether this advantage extends to vegans. Plant -based diets containing whole grains, nuts, fruits and vegetables are low in saturated fats and cholesterol and higher in fibre, vitamin C, folate, potassium, magnesium, and phytochemicals implicated in the protection against many diseases. Such diets also lower the risk of hypertension and type 2 diabetes mellitus. Diets low in fibre and in which chicken and meat are the principal ingredients can dramatically increase the incidence of colorectal cancers. Plant foods are also high in phytochemicals called polyphenols and contain higher proportions of polyunsaturated fatty acids. These substances have recently been shown to have beneficial effects on maintaining the integrity of brain function during the ageing process. Vegetarian diets may help in weight loss and long -term weight control and are associated with longevity. Diets containing animal products are generally higher in fat and calorific value while plant foods are low in energy and are nutrient dense. However, the more limiting a diet is, the more difficult it is to get all the nutrients required by your body. Can vegetarian diets, therefore, be balanced, complete and healthy? The answer is yes. According to the American Dietetic Association “appropriat ely planned vegetarian diets are healthful, nutritionally adequate and may provide health benefits in the prevention and treatment of certain diseases. Well -planned vegetarian diets are suitable for individuals during all stages of the life -cycle and for athletes.” Only the most restrictive vegan diets can perhaps cause nutritional concerns and compromise on calcium, iron, zinc, vitamin B12 and sometimes even protein. Vegetarian meals need not be boring or limiting. Whip up a variety of recipes from plant foods and feast on them. If you can''t be a vegetarian, a healthy option would be to limit intake of animal foods and increase intake of fruits and vegetables. Remember what Einstein said: “Nothing will ____________ human health and increase chances for survival of life on Earth as much as the evolution to a vegetarian diet.”

Which of the following ways can help in making vegetarian diets more interesting to adopt according to the passage?'),
  ('4a897f7b-647b-4708-b709-ff7943bb62e7'::uuid,
   'Directions (21 -27): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. Vegetarian diets lower the burden of chronic diseases. Lacto-vegetarians are of ten impressively healthier – sometimes a lot healthier – than meat eaters. It is uncertain whether this advantage extends to vegans. Plant -based diets containing whole grains, nuts, fruits and vegetables are low in saturated fats and cholesterol and higher in fibre, vitamin C, folate, potassium, magnesium, and phytochemicals implicated in the protection against many diseases. Such diets also lower the risk of hypertension and type 2 diabetes mellitus. Diets low in fibre and in which chicken and meat are the principal ingredients can dramatically increase the incidence of colorectal cancers. Plant foods are also high in phytochemicals called polyphenols and contain higher proportions of polyunsaturated fatty acids. These substances have recently been shown to have beneficial effects on maintaining the integrity of brain function during the ageing process. Vegetarian diets may help in weight loss and long -term weight control and are associated with longevity. Diets containing animal products are generally higher in fat and calorific value while plant foods are low in energy and are nutrient dense. However, the more limiting a diet is, the more difficult it is to get all the nutrients required by your body. Can vegetarian diets, therefore, be balanced, complete and healthy? The answer is yes. According to the American Dietetic Association “appropriat ely planned vegetarian diets are healthful, nutritionally adequate and may provide health benefits in the prevention and treatment of certain diseases. Well -planned vegetarian diets are suitable for individuals during all stages of the life -cycle and for athletes.” Only the most restrictive vegan diets can perhaps cause nutritional concerns and compromise on calcium, iron, zinc, vitamin B12 and sometimes even protein. Vegetarian meals need not be boring or limiting. Whip up a variety of recipes from plant foods and feast on them. If you can''t be a vegetarian, a healthy option would be to limit intake of animal foods and increase intake of fruits and vegetables. Remember what Einstein said: “Nothing will ____________ human health and increase chances for survival of life on Earth as much as the evolution to a vegetarian diet.”

Which of the following words can most appropriately be substituted in the blank in the passage?'),
  ('b89cbee0-e42a-4a66-9ac5-eaac6d4fefde'::uuid,
   'Directions (21 -27): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. Vegetarian diets lower the burden of chronic diseases. Lacto-vegetarians are of ten impressively healthier – sometimes a lot healthier – than meat eaters. It is uncertain whether this advantage extends to vegans. Plant -based diets containing whole grains, nuts, fruits and vegetables are low in saturated fats and cholesterol and higher in fibre, vitamin C, folate, potassium, magnesium, and phytochemicals implicated in the protection against many diseases. Such diets also lower the risk of hypertension and type 2 diabetes mellitus. Diets low in fibre and in which chicken and meat are the principal ingredients can dramatically increase the incidence of colorectal cancers. Plant foods are also high in phytochemicals called polyphenols and contain higher proportions of polyunsaturated fatty acids. These substances have recently been shown to have beneficial effects on maintaining the integrity of brain function during the ageing process. Vegetarian diets may help in weight loss and long -term weight control and are associated with longevity. Diets containing animal products are generally higher in fat and calorific value while plant foods are low in energy and are nutrient dense. However, the more limiting a diet is, the more difficult it is to get all the nutrients required by your body. Can vegetarian diets, therefore, be balanced, complete and healthy? The answer is yes. According to the American Dietetic Association “appropriat ely planned vegetarian diets are healthful, nutritionally adequate and may provide health benefits in the prevention and treatment of certain diseases. Well -planned vegetarian diets are suitable for individuals during all stages of the life -cycle and for athletes.” Only the most restrictive vegan diets can perhaps cause nutritional concerns and compromise on calcium, iron, zinc, vitamin B12 and sometimes even protein. Vegetarian meals need not be boring or limiting. Whip up a variety of recipes from plant foods and feast on them. If you can''t be a vegetarian, a healthy option would be to limit intake of animal foods and increase intake of fruits and vegetables. Remember what Einstein said: “Nothing will ____________ human health and increase chances for survival of life on Earth as much as the evolution to a vegetarian diet.”

Which of the following words is the most similar in its definition as the highlighted word adequate , the definition corresponding to its usage in the passage?'),
  ('bd2f12fb-9d9d-4946-ae38-8b2eba66a396'::uuid,
   'Directions (21 -27): Read the following passage and answer the questions that follow. Some words in the passage have been highlighted to aid in answering the question. Vegetarian diets lower the burden of chronic diseases. Lacto-vegetarians are of ten impressively healthier – sometimes a lot healthier – than meat eaters. It is uncertain whether this advantage extends to vegans. Plant -based diets containing whole grains, nuts, fruits and vegetables are low in saturated fats and cholesterol and higher in fibre, vitamin C, folate, potassium, magnesium, and phytochemicals implicated in the protection against many diseases. Such diets also lower the risk of hypertension and type 2 diabetes mellitus. Diets low in fibre and in which chicken and meat are the principal ingredients can dramatically increase the incidence of colorectal cancers. Plant foods are also high in phytochemicals called polyphenols and contain higher proportions of polyunsaturated fatty acids. These substances have recently been shown to have beneficial effects on maintaining the integrity of brain function during the ageing process. Vegetarian diets may help in weight loss and long -term weight control and are associated with longevity. Diets containing animal products are generally higher in fat and calorific value while plant foods are low in energy and are nutrient dense. However, the more limiting a diet is, the more difficult it is to get all the nutrients required by your body. Can vegetarian diets, therefore, be balanced, complete and healthy? The answer is yes. According to the American Dietetic Association “appropriat ely planned vegetarian diets are healthful, nutritionally adequate and may provide health benefits in the prevention and treatment of certain diseases. Well -planned vegetarian diets are suitable for individuals during all stages of the life -cycle and for athletes.” Only the most restrictive vegan diets can perhaps cause nutritional concerns and compromise on calcium, iron, zinc, vitamin B12 and sometimes even protein. Vegetarian meals need not be boring or limiting. Whip up a variety of recipes from plant foods and feast on them. If you can''t be a vegetarian, a healthy option would be to limit intake of animal foods and increase intake of fruits and vegetables. Remember what Einstein said: “Nothing will ____________ human health and increase chances for survival of life on Earth as much as the evolution to a vegetarian diet.”

Choose the word from the following options which most aptly acts as an antonym to the highlighted word beneficial as it is used in the context of the passage.'),
  ('9b27fd99-4311-42aa-a347-9e9f5bd3044d'::uuid,
   'Direction (31-35): Study the following information carefully and answer the questions given below: Seven classes of different subjects viz. Physics, Hindi, Math, English, Social study, Chemistry and Biology scheduled in school A but not necessarily in the same order. Each of the subject scheduled either for 30 Note: If Subject A scheduled from 9:00 am to 10:00 am than its must be scheduled on 9:00/9:30 or 10:00 am. Neither scheduled at 9:05 nor scheduled at 9:55. There is 30 minutes break given between two classes. Hindi class is scheduled on 12:00 noon. No class scheduled betwee n Hindi and Maths. English class scheduled at 2:00pm. There is 1:30 hours gap between English and Biology class which is scheduled after English class. Total time for all subjects is 5 hours. Physics class is scheduled 60 minutes before Maths class. No cla ss is scheduled at 6pm and after 6pm. Chemistry class takes half time than English class and scheduled just after the English class. No class is scheduled at 10:00 am and 5:00 pm. Social study class is scheduled before the class which is scheduled at 3:30 pm. English class starts before 2:30pm.

Which of the following time for Chemistry class is scheduled?'),
  ('1118459d-a10b-4e04-b24e-7274fdb65766'::uuid,
   'Direction (31-35): Study the following information carefully and answer the questions given below: Seven classes of different subjects viz. Physics, Hindi, Math, English, Social study, Chemistry and Biology scheduled in school A but not necessarily in the same order. Each of the subject scheduled either for 30 Note: If Subject A scheduled from 9:00 am to 10:00 am than its must be scheduled on 9:00/9:30 or 10:00 am. Neither scheduled at 9:05 nor scheduled at 9:55. There is 30 minutes break given between two classes. Hindi class is scheduled on 12:00 noon. No class scheduled betwee n Hindi and Maths. English class scheduled at 2:00pm. There is 1:30 hours gap between English and Biology class which is scheduled after English class. Total time for all subjects is 5 hours. Physics class is scheduled 60 minutes before Maths class. No cla ss is scheduled at 6pm and after 6pm. Chemistry class takes half time than English class and scheduled just after the English class. No class is scheduled at 10:00 am and 5:00 pm. Social study class is scheduled before the class which is scheduled at 3:30 pm. English class starts before 2:30pm.

Which of the following subject is scheduled at last?'),
  ('e91fd683-367a-4eef-be0f-113ca19135b6'::uuid,
   'Direction (31-35): Study the following information carefully and answer the questions given below: Seven classes of different subjects viz. Physics, Hindi, Math, English, Social study, Chemistry and Biology scheduled in school A but not necessarily in the same order. Each of the subject scheduled either for 30 Note: If Subject A scheduled from 9:00 am to 10:00 am than its must be scheduled on 9:00/9:30 or 10:00 am. Neither scheduled at 9:05 nor scheduled at 9:55. There is 30 minutes break given between two classes. Hindi class is scheduled on 12:00 noon. No class scheduled betwee n Hindi and Maths. English class scheduled at 2:00pm. There is 1:30 hours gap between English and Biology class which is scheduled after English class. Total time for all subjects is 5 hours. Physics class is scheduled 60 minutes before Maths class. No cla ss is scheduled at 6pm and after 6pm. Chemistry class takes half time than English class and scheduled just after the English class. No class is scheduled at 10:00 am and 5:00 pm. Social study class is scheduled before the class which is scheduled at 3:30 pm. English class starts before 2:30pm.

How many classes scheduled between Chemistry and Maths?'),
  ('a7f11e47-0c7a-428b-8762-34b6f61c6a00'::uuid,
   'Direction (31-35): Study the following information carefully and answer the questions given below: Seven classes of different subjects viz. Physics, Hindi, Math, English, Social study, Chemistry and Biology scheduled in school A but not necessarily in the same order. Each of the subject scheduled either for 30 Note: If Subject A scheduled from 9:00 am to 10:00 am than its must be scheduled on 9:00/9:30 or 10:00 am. Neither scheduled at 9:05 nor scheduled at 9:55. There is 30 minutes break given between two classes. Hindi class is scheduled on 12:00 noon. No class scheduled betwee n Hindi and Maths. English class scheduled at 2:00pm. There is 1:30 hours gap between English and Biology class which is scheduled after English class. Total time for all subjects is 5 hours. Physics class is scheduled 60 minutes before Maths class. No cla ss is scheduled at 6pm and after 6pm. Chemistry class takes half time than English class and scheduled just after the English class. No class is scheduled at 10:00 am and 5:00 pm. Social study class is scheduled before the class which is scheduled at 3:30 pm. English class starts before 2:30pm.

____ class is scheduled 150 minutes after Maths clas s?'),
  ('9f5e7f68-7f12-4b78-8917-1f38f8ed8ff9'::uuid,
   'Direction (31-35): Study the following information carefully and answer the questions given below: Seven classes of different subjects viz. Physics, Hindi, Math, English, Social study, Chemistry and Biology scheduled in school A but not necessarily in the same order. Each of the subject scheduled either for 30 Note: If Subject A scheduled from 9:00 am to 10:00 am than its must be scheduled on 9:00/9:30 or 10:00 am. Neither scheduled at 9:05 nor scheduled at 9:55. There is 30 minutes break given between two classes. Hindi class is scheduled on 12:00 noon. No class scheduled betwee n Hindi and Maths. English class scheduled at 2:00pm. There is 1:30 hours gap between English and Biology class which is scheduled after English class. Total time for all subjects is 5 hours. Physics class is scheduled 60 minutes before Maths class. No cla ss is scheduled at 6pm and after 6pm. Chemistry class takes half time than English class and scheduled just after the English class. No class is scheduled at 10:00 am and 5:00 pm. Social study class is scheduled before the class which is scheduled at 3:30 pm. English class starts before 2:30pm.

The number of classes scheduled between Physics and Chemistry is same as the number of classes scheduled before ____ class .'),
  ('bd2ec363-02ba-4d19-b1a5-23ed5ff724b1'::uuid,
   'Direction ( 36-40): A word arrangement machine when given an input line of words rearranges them following a particular rule in each step. The following is an illustration of input and rearrangement. Input: mgtuh kaops abewm bwxef mctqe aokpw Step I: oivuj maoru adeyo dyzeh oevse aomry Step II: adeyo aomry dyzeh maoru oevse oivuj Step III: adeoy amory dehyz amoru eeosv ijouv Step IV: 26 26 30 22 27 31 Step V: 3 4 4 8 8 9 Step V is the final step of given input. Answer the following questions based on the following input: - Input: helof kpest fumap hseub lmodu karlx

Which among the following word is third from the right end in step III?'),
  ('28000881-0b35-44be-9d28-486f0137e417'::uuid,
   'Direction ( 36-40): A word arrangement machine when given an input line of words rearranges them following a particular rule in each step. The following is an illustration of input and rearrangement. Input: mgtuh kaops abewm bwxef mctqe aokpw Step I: oivuj maoru adeyo dyzeh oevse aomry Step II: adeyo aomry dyzeh maoru oevse oivuj Step III: adeoy amory dehyz amoru eeosv ijouv Step IV: 26 26 30 22 27 31 Step V: 3 4 4 8 8 9 Step V is the final step of given input. Answer the following questions based on the following input: - Input: helof kpest fumap hseub lmodu karlx

How many letters are there between third letter of the second word from the left end in step II and second letter of the fourth word from the right end in step III according to the English alphabetical series?'),
  ('fcb6316e-4b7f-48cd-ac43-40f6cb97bc9f'::uuid,
   'Direction ( 36-40): A word arrangement machine when given an input line of words rearranges them following a particular rule in each step. The following is an illustration of input and rearrangement. Input: mgtuh kaops abewm bwxef mctqe aokpw Step I: oivuj maoru adeyo dyzeh oevse aomry Step II: adeyo aomry dyzeh maoru oevse oivuj Step III: adeoy amory dehyz amoru eeosv ijouv Step IV: 26 26 30 22 27 31 Step V: 3 4 4 8 8 9 Step V is the final step of given input. Answer the following questions based on the following input: - Input: helof kpest fumap hseub lmodu karlx

What is the sum of the even numbers appeared in step IV?'),
  ('a100c4ea-6496-4532-a977-21775de40e48'::uuid,
   'Direction ( 36-40): A word arrangement machine when given an input line of words rearranges them following a particular rule in each step. The following is an illustration of input and rearrangement. Input: mgtuh kaops abewm bwxef mctqe aokpw Step I: oivuj maoru adeyo dyzeh oevse aomry Step II: adeyo aomry dyzeh maoru oevse oivuj Step III: adeoy amory dehyz amoru eeosv ijouv Step IV: 26 26 30 22 27 31 Step V: 3 4 4 8 8 9 Step V is the final step of given input. Answer the following questions based on the following input: - Input: helof kpest fumap hseub lmodu karlx

What is the difference between the numbers which are second from the right end in step IV and third from the left end in step V?'),
  ('db6b34e4-2de1-44c4-a7d1-02ea70d4d773'::uuid,
   'Direction ( 36-40): A word arrangement machine when given an input line of words rearranges them following a particular rule in each step. The following is an illustration of input and rearrangement. Input: mgtuh kaops abewm bwxef mctqe aokpw Step I: oivuj maoru adeyo dyzeh oevse aomry Step II: adeyo aomry dyzeh maoru oevse oivuj Step III: adeoy amory dehyz amoru eeosv ijouv Step IV: 26 26 30 22 27 31 Step V: 3 4 4 8 8 9 Step V is the final step of given input. Answer the following questions based on the following input: - Input: helof kpest fumap hseub lmodu karlx

Which among the following word is second to the left of third word from the right end in step II?'),
  ('5a5fb576-c115-485b-87ac-7474820b7a0f'::uuid,
   'Directions (41-42): The Delhi government approved a new excise policy , lowering the minimum age for consumption of alcohol to 21 years. Earlier, the legal age of drinking in New Delhi was 25. With the move, the national capital joins the majority of Indian states in having 21 as the legal drinking age. While in some states, the age limit is as low as 18, a few have it at the upper limit of 25. I n some states, the consumption of alcohol is forbidden.

What could be the fallout of the new excise policy approved by Delhi government?'),
  ('968c25b2-48d1-4bf7-901c-3c25b66ee02b'::uuid,
   'Directions (41-42): The Delhi government approved a new excise policy , lowering the minimum age for consumption of alcohol to 21 years. Earlier, the legal age of drinking in New Delhi was 25. With the move, the national capital joins the majority of Indian states in having 21 as the legal drinking age. While in some states, the age limit is as low as 18, a few have it at the upper limit of 25. I n some states, the consumption of alcohol is forbidden.

Which of the following can be postulated from the above statement? (I) Central government is not in the favour of move by Delhi Government. (II) Delhi government wants to increase their revenue (III) Annual revenue of states who has forbidden the liquor is less in compare to Delhi.'),
  ('96a1ecb9-6049-4f9d-a048-203f7566ff19'::uuid,
   'Direction (43-47): Study the following information carefully and answer the questions given below. Nine persons live in three floored building marked 1 to 3 from bottom to top respectively. There are three flats on each floor viz. - flat 1, flat 2, and flat 3 from west to east respectively. Only one person lives in each flat. Each person goes to different countries i.e. Iran, USA, Russia, Korea, Oman, Malta, Japan, UK and UAE but not necessarily in the same order. A lives on an odd numbered floor to the immediate west of the one who goes to Korea. F lives two floors below the one who goes to Korea. F lives in an even numbered flat. B lives to the south east flat of the one who goes to USA. B and the one who goes to USA live in odd numbered flat. B lives on an odd numbered floor. C doesn’t go to Korea. C lives to the north east flat of the one who goes t o USA. D lives below A in the same flat with A. The one who goes to UAE lives on the same floor with D but in different flat as F’s flat. The one who goes to Japan lives above B’s flat. E lives to the immediate south west of the one who goes to Japan. G li ves to the east of H in the same floor with E. The one who goes to Oman lives to the west of G. One floor gap is there between I and the one who goes to Malta. The one who goes to Malta lives to the south east of the one who goes to Iran. D doesn’t go to UK.

Which among the following statement(s) is/are not true?'),
  ('84c15ec6-0735-48a9-a993-16c0638ba83d'::uuid,
   'Direction (43-47): Study the following information carefully and answer the questions given below. Nine persons live in three floored building marked 1 to 3 from bottom to top respectively. There are three flats on each floor viz. - flat 1, flat 2, and flat 3 from west to east respectively. Only one person lives in each flat. Each person goes to different countries i.e. Iran, USA, Russia, Korea, Oman, Malta, Japan, UK and UAE but not necessarily in the same order. A lives on an odd numbered floor to the immediate west of the one who goes to Korea. F lives two floors below the one who goes to Korea. F lives in an even numbered flat. B lives to the south east flat of the one who goes to USA. B and the one who goes to USA live in odd numbered flat. B lives on an odd numbered floor. C doesn’t go to Korea. C lives to the north east flat of the one who goes t o USA. D lives below A in the same flat with A. The one who goes to UAE lives on the same floor with D but in different flat as F’s flat. The one who goes to Japan lives above B’s flat. E lives to the immediate south west of the one who goes to Japan. G li ves to the east of H in the same floor with E. The one who goes to Oman lives to the west of G. One floor gap is there between I and the one who goes to Malta. The one who goes to Malta lives to the south east of the one who goes to Iran. D doesn’t go to UK.

In which among the following floor and flat does G live?'),
  ('a27e98ac-8a2d-4f74-8148-ea86944c341c'::uuid,
   'Direction (43-47): Study the following information carefully and answer the questions given below. Nine persons live in three floored building marked 1 to 3 from bottom to top respectively. There are three flats on each floor viz. - flat 1, flat 2, and flat 3 from west to east respectively. Only one person lives in each flat. Each person goes to different countries i.e. Iran, USA, Russia, Korea, Oman, Malta, Japan, UK and UAE but not necessarily in the same order. A lives on an odd numbered floor to the immediate west of the one who goes to Korea. F lives two floors below the one who goes to Korea. F lives in an even numbered flat. B lives to the south east flat of the one who goes to USA. B and the one who goes to USA live in odd numbered flat. B lives on an odd numbered floor. C doesn’t go to Korea. C lives to the north east flat of the one who goes t o USA. D lives below A in the same flat with A. The one who goes to UAE lives on the same floor with D but in different flat as F’s flat. The one who goes to Japan lives above B’s flat. E lives to the immediate south west of the one who goes to Japan. G li ves to the east of H in the same floor with E. The one who goes to Oman lives to the west of G. One floor gap is there between I and the one who goes to Malta. The one who goes to Malta lives to the south east of the one who goes to Iran. D doesn’t go to UK.

Which a mong the following pair of persons live to the south west of G?'),
  ('72689e64-4cf2-4018-a7d7-b24399d16027'::uuid,
   'Direction (48-51): Study the following information carefully and answer the questions given below. In a family of three generation there are seven members and three married couples. Each person has different age. Only married couples have child. The one who is sister-in-law of W is 20 years old. K is uncle of P who is three years younger than S. W is the only son -in-law of M and has no siblings. T is sister -in-law of K who is 30 years old. K is unmarried and sibling of M. X is grandchild of M and 15 years younger than her aunt. Age of S is not an even number.

How X is related to W?'),
  ('de4707c8-6deb-4b4f-8909-71cb7ab75688'::uuid,
   'Direction (48-51): Study the following information carefully and answer the questions given below. In a family of three generation there are seven members and three married couples. Each person has different age. Only married couples have child. The one who is sister-in-law of W is 20 years old. K is uncle of P who is three years younger than S. W is the only son -in-law of M and has no siblings. T is sister -in-law of K who is 30 years old. K is unmarried and sibling of M. X is grandchild of M and 15 years younger than her aunt. Age of S is not an even number.

What is the sum of the ages of X mother’s and K?'),
  ('9f53ba44-75bf-4b06-8d6d-31704a74b8b8'::uuid,
   'Direction (48-51): Study the following information carefully and answer the questions given below. In a family of three generation there are seven members and three married couples. Each person has different age. Only married couples have child. The one who is sister-in-law of W is 20 years old. K is uncle of P who is three years younger than S. W is the only son -in-law of M and has no siblings. T is sister -in-law of K who is 30 years old. K is unmarried and sibling of M. X is grandchild of M and 15 years younger than her aunt. Age of S is not an even number.

Who among the following is the child of T?'),
  ('ba379d86-f144-4f63-8d83-91ba55e1f6fe'::uuid,
   'Direction (48-51): Study the following information carefully and answer the questions given below. In a family of three generation there are seven members and three married couples. Each person has different age. Only married couples have child. The one who is sister-in-law of W is 20 years old. K is uncle of P who is three years younger than S. W is the only son -in-law of M and has no siblings. T is sister -in-law of K who is 30 years old. K is unmarried and sibling of M. X is grandchild of M and 15 years younger than her aunt. Age of S is not an even number.

What is the ratio of the ages of P’s uncle and S’s daughter?'),
  ('204bc12b-6f9f-4786-8c25-02cb317724f8'::uuid,
   'Direction (61-65): Study the following information carefully and answer the questions given below. Eight persons -A, B, C, D, E, F, G and H were born in different years i.e. 1991, 1995, 2002, 1998, 1985, 2018, 2015 and 2010 but not necessarily in the same order. Calculate the age of each person taking the base year 2021. B’s age is a prime number. There is four years gap between B and H. Two persons were born between B and E who was born in odd numbered year. The number of persons born before E is same as the number of persons born after F. G’s age is a multiple of 3 but less than B. The difference between the age of A and D is neither even nor prime number. C’s age is more than E’s age but not less than F’s age. E is older than F.

Who among the following is the youngest person?'),
  ('61555adb-23c8-4bdb-9dc9-1e324d9d5732'::uuid,
   'Direction (61-65): Study the following information carefully and answer the questions given below. Eight persons -A, B, C, D, E, F, G and H were born in different years i.e. 1991, 1995, 2002, 1998, 1985, 2018, 2015 and 2010 but not necessarily in the same order. Calculate the age of each person taking the base year 2021. B’s age is a prime number. There is four years gap between B and H. Two persons were born between B and E who was born in odd numbered year. The number of persons born before E is same as the number of persons born after F. G’s age is a multiple of 3 but less than B. The difference between the age of A and D is neither even nor prime number. C’s age is more than E’s age but not less than F’s age. E is older than F.

Which among the following statement(s) is/are true?'),
  ('d4f02165-e9e3-495e-ae45-b253ea65e79b'::uuid,
   'Directions (66-68): Study the following information carefully and answer the questions given below- In a certain code language: “Enforcement directorate would acquitted soon” is coded as “19LG 13LV 38FW 4FW 34LM” “Interrogation release completely added stems” is coded as “23LM 23VV 18LB 5VW 39VH” “Prevention corruption allegedly purchase campaigning “is coded as “34LM 18FM 13VB 37FV 4RT”

What is the code for “Public Health” in the given code language?'),
  ('1dcf7b49-d44c-473f-88d4-2b50e939334f'::uuid,
   'Directions (66-68): Study the following information carefully and answer the questions given below- In a certain code language: “Enforcement directorate would acquitted soon” is coded as “19LG 13LV 38FW 4FW 34LM” “Interrogation release completely added stems” is coded as “23LM 23VV 18LB 5VW 39VH” “Prevention corruption allegedly purchase campaigning “is coded as “34LM 18FM 13VB 37FV 4RT”

The code “9RR 28VI” is coded for which of the following word?'),
  ('f54d5545-3b91-4480-a7af-c71a5282ec84'::uuid,
   'Directions (66-68): Study the following information carefully and answer the questions given below- In a certain code language: “Enforcement directorate would acquitted soon” is coded as “19LG 13LV 38FW 4FW 34LM” “Interrogation release completely added stems” is coded as “23LM 23VV 18LB 5VW 39VH” “Prevention corruption allegedly purchase campaigning “is coded as “34LM 18FM 13VB 37FV 4RT”

What is the code for “German language” in the given code language?'),
  ('55db1819-1aba-4cd7-b3f5-80e6de631ad6'::uuid,
   'Direction (69-73): Study the following information carefully and answer the questions given below: Eight persons sit in a row face north at consecutive multiple distance of 7m. All the persons face towards north. A sits 63m left of S. R sits immediate right of S. Distance between A and R is same as the distance between F and R. Difference between the total distance of W and D to the total distance of D and Y is 7m. Now F goes in the north and walks 50m to reach point C then, takes right turn and walks 98m to reach at point K after that F in the North-west of U. W goes in the south and walks 20m to reach point Q then he takes his left and walks some distance to reach south of R.

Find the sum of the distance walk by W and F?'),
  ('aec19373-d886-4a49-a548-de39a939ca2a'::uuid,
   'Direction (69-73): Study the following information carefully and answer the questions given below: Eight persons sit in a row face north at consecutive multiple distance of 7m. All the persons face towards north. A sits 63m left of S. R sits immediate right of S. Distance between A and R is same as the distance between F and R. Difference between the total distance of W and D to the total distance of D and Y is 7m. Now F goes in the north and walks 50m to reach point C then, takes right turn and walks 98m to reach at point K after that F in the North-west of U. W goes in the south and walks 20m to reach point Q then he takes his left and walks some distance to reach south of R.

In which direction is point C with respect to point Q?'),
  ('5fc97189-e9a9-45f6-9b13-41ec20ebb0b8'::uuid,
   'Direction (69-73): Study the following information carefully and answer the questions given below: Eight persons sit in a row face north at consecutive multiple distance of 7m. All the persons face towards north. A sits 63m left of S. R sits immediate right of S. Distance between A and R is same as the distance between F and R. Difference between the total distance of W and D to the total distance of D and Y is 7m. Now F goes in the north and walks 50m to reach point C then, takes right turn and walks 98m to reach at point K after that F in the North-west of U. W goes in the south and walks 20m to reach point Q then he takes his left and walks some distance to reach south of R.

What is the total distance between S and the one who sits immediate right of D?'),
  ('c90b371c-7326-4e74-b939-16a6203df5d7'::uuid,
   'Direction (78-82): Study the following information carefully and answer the questions given below: A certain number of persons sit around a circular table facing the centre. Few of them like different colours- Red, Green, Yellow and Black but not necessarily in the same order. More than 9 persons sit around a table. Each of the neighbours sits at equal distance from each other. Two persons sit between Q and A who likes Green. T is an immediate neighbour of U who likes Red. U sits 2nd to the right of A. There are as many persons sit between T and W as between Q and W. R sits 3rd to the right of W and is immediate neighbour of Q. R and the one who likes Black are immediate neighbours. The one who likes yellow sits 2nd to the right of the one who likes Black. U and the one who likes Yellow are not an immediate neighbour. The number of persons sits between T and R is less than five when counted to the right of T.

Who among the following sits 8th to the right of T?'),
  ('73d7b2e7-b70b-4b1d-92fd-469b9bdb14cb'::uuid,
   'Direction (78-82): Study the following information carefully and answer the questions given below: A certain number of persons sit around a circular table facing the centre. Few of them like different colours- Red, Green, Yellow and Black but not necessarily in the same order. More than 9 persons sit around a table. Each of the neighbours sits at equal distance from each other. Two persons sit between Q and A who likes Green. T is an immediate neighbour of U who likes Red. U sits 2nd to the right of A. There are as many persons sit between T and W as between Q and W. R sits 3rd to the right of W and is immediate neighbour of Q. R and the one who likes Black are immediate neighbours. The one who likes yellow sits 2nd to the right of the one who likes Black. U and the one who likes Yellow are not an immediate neighbour. The number of persons sits between T and R is less than five when counted to the right of T.

___ faces to the one who likes ____ colour?'),
  ('bd057ce1-3655-49e3-adb0-bd67a87ded45'::uuid,
   'Direction (78-82): Study the following information carefully and answer the questions given below: A certain number of persons sit around a circular table facing the centre. Few of them like different colours- Red, Green, Yellow and Black but not necessarily in the same order. More than 9 persons sit around a table. Each of the neighbours sits at equal distance from each other. Two persons sit between Q and A who likes Green. T is an immediate neighbour of U who likes Red. U sits 2nd to the right of A. There are as many persons sit between T and W as between Q and W. R sits 3rd to the right of W and is immediate neighbour of Q. R and the one who likes Black are immediate neighbours. The one who likes yellow sits 2nd to the right of the one who likes Black. U and the one who likes Yellow are not an immediate neighbour. The number of persons sits between T and R is less than five when counted to the right of T.

How many persons sit around the table?'),
  ('76ca1621-f5a0-4484-a457-d2ac85385c2e'::uuid,
   'Direction (86-90): Study the following information carefully and answer the questions given below. Eight boxes are kept in eight different shelves such that shelves are marked as 1 to 8 from bottom to top respectively. Each box contains different items i.e., Utensil, Pencil, Pen, Clothes, Marker, Book, Bottle and Toffees but not necessarily in the same order. Box P is kept at an even numbered shelf and above box Q. Two boxes are kept between box P and box Q. The box which contains marker kept four boxes above box W. Box Q doesn’t contain marker. Box W is kept at an odd numbered shelf. The number of boxes kept above the box which contains marker is one less than the number of boxes kept below the box which contains pencil. More than two boxes are kept between box P and box T which is kept just below the box which contains bottle. Box R and box U kept at an adjacent shelf. Three boxes are kept between the box which contains pen and box R. Box W and the box which contains pen are not kept adjacent to each other. Box S is kept below the box which contains book. Three boxes are kept between box V and the box which contains clothes. Box T doesn’t contain utensil.

Which among the following combination is correct?'),
  ('14424d63-fb6b-44e7-a752-46cd178d3f17'::uuid,
   'Direction (86-90): Study the following information carefully and answer the questions given below. Eight boxes are kept in eight different shelves such that shelves are marked as 1 to 8 from bottom to top respectively. Each box contains different items i.e., Utensil, Pencil, Pen, Clothes, Marker, Book, Bottle and Toffees but not necessarily in the same order. Box P is kept at an even numbered shelf and above box Q. Two boxes are kept between box P and box Q. The box which contains marker kept four boxes above box W. Box Q doesn’t contain marker. Box W is kept at an odd numbered shelf. The number of boxes kept above the box which contains marker is one less than the number of boxes kept below the box which contains pencil. More than two boxes are kept between box P and box T which is kept just below the box which contains bottle. Box R and box U kept at an adjacent shelf. Three boxes are kept between the box which contains pen and box R. Box W and the box which contains pen are not kept adjacent to each other. Box S is kept below the box which contains book. Three boxes are kept between box V and the box which contains clothes. Box T doesn’t contain utensil.

How many boxes are kept between box S and the box which contains clothes?'),
  ('0dc05cfa-a1a9-4d82-991d-1221b354acde'::uuid,
   'Direction (86-90): Study the following information carefully and answer the questions given below. Eight boxes are kept in eight different shelves such that shelves are marked as 1 to 8 from bottom to top respectively. Each box contains different items i.e., Utensil, Pencil, Pen, Clothes, Marker, Book, Bottle and Toffees but not necessarily in the same order. Box P is kept at an even numbered shelf and above box Q. Two boxes are kept between box P and box Q. The box which contains marker kept four boxes above box W. Box Q doesn’t contain marker. Box W is kept at an odd numbered shelf. The number of boxes kept above the box which contains marker is one less than the number of boxes kept below the box which contains pencil. More than two boxes are kept between box P and box T which is kept just below the box which contains bottle. Box R and box U kept at an adjacent shelf. Three boxes are kept between the box which contains pen and box R. Box W and the box which contains pen are not kept adjacent to each other. Box S is kept below the box which contains book. Three boxes are kept between box V and the box which contains clothes. Box T doesn’t contain utensil.

Which among the following box contains marker?'),
  ('75b80d7a-d622-4d6f-ab3c-883f57c814cb'::uuid,
   'Direction (86-90): Study the following information carefully and answer the questions given below. Eight boxes are kept in eight different shelves such that shelves are marked as 1 to 8 from bottom to top respectively. Each box contains different items i.e., Utensil, Pencil, Pen, Clothes, Marker, Book, Bottle and Toffees but not necessarily in the same order. Box P is kept at an even numbered shelf and above box Q. Two boxes are kept between box P and box Q. The box which contains marker kept four boxes above box W. Box Q doesn’t contain marker. Box W is kept at an odd numbered shelf. The number of boxes kept above the box which contains marker is one less than the number of boxes kept below the box which contains pencil. More than two boxes are kept between box P and box T which is kept just below the box which contains bottle. Box R and box U kept at an adjacent shelf. Three boxes are kept between the box which contains pen and box R. Box W and the box which contains pen are not kept adjacent to each other. Box S is kept below the box which contains book. Three boxes are kept between box V and the box which contains clothes. Box T doesn’t contain utensil.

If all the boxes are arranged from top to bottom in an alphabetical order then the position of how many boxes remains unchanged?'),
  ('8ad554e3-a31b-497c-825d-d07e6e65acd2'::uuid,
   'Direction (86-90): Study the following information carefully and answer the questions given below. Eight boxes are kept in eight different shelves such that shelves are marked as 1 to 8 from bottom to top respectively. Each box contains different items i.e., Utensil, Pencil, Pen, Clothes, Marker, Book, Bottle and Toffees but not necessarily in the same order. Box P is kept at an even numbered shelf and above box Q. Two boxes are kept between box P and box Q. The box which contains marker kept four boxes above box W. Box Q doesn’t contain marker. Box W is kept at an odd numbered shelf. The number of boxes kept above the box which contains marker is one less than the number of boxes kept below the box which contains pencil. More than two boxes are kept between box P and box T which is kept just below the box which contains bottle. Box R and box U kept at an adjacent shelf. Three boxes are kept between the box which contains pen and box R. Box W and the box which contains pen are not kept adjacent to each other. Box S is kept below the box which contains book. Three boxes are kept between box V and the box which contains clothes. Box T doesn’t contain utensil.

In which of the following shelf does the box contain pen is kept?'),
  ('81da5343-1342-42b1-a837-0a61072d7e5f'::uuid,
   'Direction (105-107): There are two equations I and II given, solve these equations and answer the following questions given below. Equation I. px2 −9𝑥 + 7 = 0 Equation II. qy2 – 8y + 4 =0 Note: (A) Both p and q are positive integers. (B) One of the roots of equation II is 2 3. (C) The ratio of highest root of equation I to the highest root of equation II is 7 : 4.

Find the ratio of smallest root of equation I to the smallest root of equation II. (a) 1 : 2'),
  ('114145a9-20b4-47ab-9dba-0d5996458b97'::uuid,
   'Direction (105-107): There are two equations I and II given, solve these equations and answer the following questions given below. Equation I. px2 −9𝑥 + 7 = 0 Equation II. qy2 – 8y + 4 =0 Note: (A) Both p and q are positive integers. (B) One of the roots of equation II is 2 3. (C) The ratio of highest root of equation I to the highest root of equation II is 7 : 4.

Find the value of (p + q).'),
  ('3e0ea7d9-2960-421b-a530-d917f5e1e89a'::uuid,
   'Direction (105-107): There are two equations I and II given, solve these equations and answer the following questions given below. Equation I. px2 −9𝑥 + 7 = 0 Equation II. qy2 – 8y + 4 =0 Note: (A) Both p and q are positive integers. (B) One of the roots of equation II is 2 3. (C) The ratio of highest root of equation I to the highest root of equation II is 7 : 4.

Find the both roots of equation (p+q)2a2 + (3pq +1) a −6=0.'),
  ('257b64c1-8b8f-45d3-ae06-aae308be4295'::uuid,
   'Directions ( 115-119): Read the following passage carefully and answer the questions given below. In a society, people like three different types of cars i.e. A, B & C. Ratio of people who like car A to car C is 29 :42 and people who like only car A&C together is one fourth of the people who like only car B. People who like only car C is 50 more than four times of the people who like only car A & B together. 10 people like all the three types of cars which is equal to people who like only car B&C together. People who like only car C is twice of the people who like only car A and people who like car C is 210 . All people like either of the car.

Find the ratio of people who like only car C to people who like car B.'),
  ('77751b6a-81ac-4de8-8eee-6c35b9e3969d'::uuid,
   'Directions ( 115-119): Read the following passage carefully and answer the questions given below. In a society, people like three different types of cars i.e. A, B & C. Ratio of people who like car A to car C is 29 :42 and people who like only car A&C together is one fourth of the people who like only car B. People who like only car C is 50 more than four times of the people who like only car A & B together. 10 people like all the three types of cars which is equal to people who like only car B&C together. People who like only car C is twice of the people who like only car A and people who like car C is 210 . All people like either of the car.

People like only car A&C together is what percentage people like at least two cars?')
) AS v(question_id, question_text)
WHERE q.id = v.question_id
  AND q.question_text IS DISTINCT FROM v.question_text;

-- 2. Return the 51 rows that 281 pulled, and only those.
UPDATE public.pyq_questions
SET reviewer_status = 'verified'
WHERE id IN (
  '0dc05cfa-a1a9-4d82-991d-1221b354acde'::uuid,
  '1118459d-a10b-4e04-b24e-7274fdb65766'::uuid,
  '114145a9-20b4-47ab-9dba-0d5996458b97'::uuid,
  '14424d63-fb6b-44e7-a752-46cd178d3f17'::uuid,
  '1dcf7b49-d44c-473f-88d4-2b50e939334f'::uuid,
  '204bc12b-6f9f-4786-8c25-02cb317724f8'::uuid,
  '257b64c1-8b8f-45d3-ae06-aae308be4295'::uuid,
  '25c14b8a-2690-493f-b413-f37607227515'::uuid,
  '28000881-0b35-44be-9d28-486f0137e417'::uuid,
  '3446de24-1e14-47eb-852f-b83170f6e897'::uuid,
  '352bd671-f233-4053-8a94-f5cce5050c70'::uuid,
  '3e0ea7d9-2960-421b-a530-d917f5e1e89a'::uuid,
  '4ff3c2c3-6c64-4d6c-bf0f-447aa3183c49'::uuid,
  '55db1819-1aba-4cd7-b3f5-80e6de631ad6'::uuid,
  '5a5fb576-c115-485b-87ac-7474820b7a0f'::uuid,
  '5d56b020-e123-4f86-9b50-0838afcb3334'::uuid,
  '5fc97189-e9a9-45f6-9b13-41ec20ebb0b8'::uuid,
  '61555adb-23c8-4bdb-9dc9-1e324d9d5732'::uuid,
  '72689e64-4cf2-4018-a7d7-b24399d16027'::uuid,
  '73d7b2e7-b70b-4b1d-92fd-469b9bdb14cb'::uuid,
  '75b80d7a-d622-4d6f-ab3c-883f57c814cb'::uuid,
  '76ca1621-f5a0-4484-a457-d2ac85385c2e'::uuid,
  '77751b6a-81ac-4de8-8eee-6c35b9e3969d'::uuid,
  '7eabd9c3-f15e-4950-84e7-44ecee473a60'::uuid,
  '81da5343-1342-42b1-a837-0a61072d7e5f'::uuid,
  '82f16a8f-5894-446b-b16c-b2a82a0f8697'::uuid,
  '84c15ec6-0735-48a9-a993-16c0638ba83d'::uuid,
  '8ad554e3-a31b-497c-825d-d07e6e65acd2'::uuid,
  '8bf962d0-59b7-4432-9b0b-ed8cc1c4d8fd'::uuid,
  '968c25b2-48d1-4bf7-901c-3c25b66ee02b'::uuid,
  '96a1ecb9-6049-4f9d-a048-203f7566ff19'::uuid,
  '9b27fd99-4311-42aa-a347-9e9f5bd3044d'::uuid,
  '9f53ba44-75bf-4b06-8d6d-31704a74b8b8'::uuid,
  '9f5e7f68-7f12-4b78-8917-1f38f8ed8ff9'::uuid,
  'a100c4ea-6496-4532-a977-21775de40e48'::uuid,
  'a27e98ac-8a2d-4f74-8148-ea86944c341c'::uuid,
  'a7f11e47-0c7a-428b-8762-34b6f61c6a00'::uuid,
  'aec19373-d886-4a49-a548-de39a939ca2a'::uuid,
  'ba379d86-f144-4f63-8d83-91ba55e1f6fe'::uuid,
  'bd2ec363-02ba-4d19-b1a5-23ed5ff724b1'::uuid,
  'c90b371c-7326-4e74-b939-16a6203df5d7'::uuid,
  'd4f02165-e9e3-495e-ae45-b253ea65e79b'::uuid,
  'db6b34e4-2de1-44c4-a7d1-02ea70d4d773'::uuid,
  'dcdc4a16-21c3-4d49-a088-92378686f825'::uuid,
  'de4707c8-6deb-4b4f-8909-71cb7ab75688'::uuid,
  'e68143e6-4333-414e-bf1c-493ff2df62f7'::uuid,
  'e91fd683-367a-4eef-be0f-113ca19135b6'::uuid,
  'ef384cab-d616-4299-8b68-78568d1dca8c'::uuid,
  'f54d5545-3b91-4480-a7af-c71a5282ec84'::uuid,
  'fcb6316e-4b7f-48cd-ac43-40f6cb97bc9f'::uuid,
  '0dc8f7f3-eb01-4163-a56e-d171d886aa50'::uuid
)
  AND reviewer_status = 'needs_correction';

-- 3. Their option rows, which 281 cascaded to.
UPDATE public.pyq_options
SET reviewer_status = 'verified'
WHERE question_id IN (
  '0dc05cfa-a1a9-4d82-991d-1221b354acde'::uuid,
  '1118459d-a10b-4e04-b24e-7274fdb65766'::uuid,
  '114145a9-20b4-47ab-9dba-0d5996458b97'::uuid,
  '14424d63-fb6b-44e7-a752-46cd178d3f17'::uuid,
  '1dcf7b49-d44c-473f-88d4-2b50e939334f'::uuid,
  '204bc12b-6f9f-4786-8c25-02cb317724f8'::uuid,
  '257b64c1-8b8f-45d3-ae06-aae308be4295'::uuid,
  '25c14b8a-2690-493f-b413-f37607227515'::uuid,
  '28000881-0b35-44be-9d28-486f0137e417'::uuid,
  '3446de24-1e14-47eb-852f-b83170f6e897'::uuid,
  '352bd671-f233-4053-8a94-f5cce5050c70'::uuid,
  '3e0ea7d9-2960-421b-a530-d917f5e1e89a'::uuid,
  '4ff3c2c3-6c64-4d6c-bf0f-447aa3183c49'::uuid,
  '55db1819-1aba-4cd7-b3f5-80e6de631ad6'::uuid,
  '5a5fb576-c115-485b-87ac-7474820b7a0f'::uuid,
  '5d56b020-e123-4f86-9b50-0838afcb3334'::uuid,
  '5fc97189-e9a9-45f6-9b13-41ec20ebb0b8'::uuid,
  '61555adb-23c8-4bdb-9dc9-1e324d9d5732'::uuid,
  '72689e64-4cf2-4018-a7d7-b24399d16027'::uuid,
  '73d7b2e7-b70b-4b1d-92fd-469b9bdb14cb'::uuid,
  '75b80d7a-d622-4d6f-ab3c-883f57c814cb'::uuid,
  '76ca1621-f5a0-4484-a457-d2ac85385c2e'::uuid,
  '77751b6a-81ac-4de8-8eee-6c35b9e3969d'::uuid,
  '7eabd9c3-f15e-4950-84e7-44ecee473a60'::uuid,
  '81da5343-1342-42b1-a837-0a61072d7e5f'::uuid,
  '82f16a8f-5894-446b-b16c-b2a82a0f8697'::uuid,
  '84c15ec6-0735-48a9-a993-16c0638ba83d'::uuid,
  '8ad554e3-a31b-497c-825d-d07e6e65acd2'::uuid,
  '8bf962d0-59b7-4432-9b0b-ed8cc1c4d8fd'::uuid,
  '968c25b2-48d1-4bf7-901c-3c25b66ee02b'::uuid,
  '96a1ecb9-6049-4f9d-a048-203f7566ff19'::uuid,
  '9b27fd99-4311-42aa-a347-9e9f5bd3044d'::uuid,
  '9f53ba44-75bf-4b06-8d6d-31704a74b8b8'::uuid,
  '9f5e7f68-7f12-4b78-8917-1f38f8ed8ff9'::uuid,
  'a100c4ea-6496-4532-a977-21775de40e48'::uuid,
  'a27e98ac-8a2d-4f74-8148-ea86944c341c'::uuid,
  'a7f11e47-0c7a-428b-8762-34b6f61c6a00'::uuid,
  'aec19373-d886-4a49-a548-de39a939ca2a'::uuid,
  'ba379d86-f144-4f63-8d83-91ba55e1f6fe'::uuid,
  'bd2ec363-02ba-4d19-b1a5-23ed5ff724b1'::uuid,
  'c90b371c-7326-4e74-b939-16a6203df5d7'::uuid,
  'd4f02165-e9e3-495e-ae45-b253ea65e79b'::uuid,
  'db6b34e4-2de1-44c4-a7d1-02ea70d4d773'::uuid,
  'dcdc4a16-21c3-4d49-a088-92378686f825'::uuid,
  'de4707c8-6deb-4b4f-8909-71cb7ab75688'::uuid,
  'e68143e6-4333-414e-bf1c-493ff2df62f7'::uuid,
  'e91fd683-367a-4eef-be0f-113ca19135b6'::uuid,
  'ef384cab-d616-4299-8b68-78568d1dca8c'::uuid,
  'f54d5545-3b91-4480-a7af-c71a5282ec84'::uuid,
  'fcb6316e-4b7f-48cd-ac43-40f6cb97bc9f'::uuid,
  '0dc8f7f3-eb01-4163-a56e-d171d886aa50'::uuid
)
  AND reviewer_status = 'needs_correction';

COMMIT;
