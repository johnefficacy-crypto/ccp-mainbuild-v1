-- Migration 286: restore the wrapped second line to 124 NABARD option rows.
--
-- The extractor took an option to be one line. Where the compendium wrapped
-- one onto a second line, the second line was dropped, so the option reads
-- as an unfinished sentence -- "India's efforts to build a strong economy
-- will make the UN position an inevitable", where the source continues
-- "outcome." 124 rows across 75 questions and 19 papers. 22 of them are the
-- KEYED option.
--
-- Found the way migration 279 said this class would have to be found:
-- reconstruct every option from the source rather than checking the loaded
-- text for a missing full stop. For each block, walk the lines, open a new
-- option at an option marker and keep appending until the next marker, an
-- Answer or Explanation line, a page footer, a blank line or the next
-- question. That gives 4319 reconstructed option runs. Then match each
-- loaded row by (subject prefix, year, printed number, label) and compare.
--
-- 5275 option rows, all accounted for:
--   5133  already complete -- the loaded text equals the reconstruction
--    124  TRUNCATED -- the loaded text is a strict prefix of the reconstruction
--     17  no source line -- see below
--      1  no prefix match -- see below
--
-- The added text runs from 6 to 339 characters, median 15. The long tail is
-- real: the largest restores 339 characters to an option that had lost most
-- of itself.
--
-- MEASUREMENT REPLACED, NOT REFINED. Migration 279 reported 127 of these by
-- matching each loaded option to a source LINE and testing whether the next
-- line continued it, which could only speak for the 4252 options it matched
-- uniquely and left 1023 unmeasured. This reconstructs the option instead
-- of the line, so the unmeasured residue is 18 rather than 1023, and the
-- count is 124 rather than 127. The three that fell away were line matches
-- that did not survive being reconstructed; the 22 keyed rows are the same
-- 22.
--
-- THE 22 KEYED OPTIONS. These are the answer, so a learner reading a truncated
-- one is reading a truncated answer:
--   CK-2022-Q061     (A)  + 13ch
--       was: 'resolution of the output image or simply the resolution of'
--       now: ' the output image or simply the resolution of the printer.'
--   CK-2023-Q010     (B)  + 17ch
--       was: 'aved to the Downloads folder and can be seen by anyone who'
--       now: 'oads folder and can be seen by anyone who uses the device.'
--   ENG-2020-Q022    (D)  + 10ch
--       was: 'and appraise those projects with respect to the conditions'
--       now: 'se those projects with respect to the conditions laid down'
--   ENG-2020-Q037    (C)  + 43ch
--       was: 'has been a significant rise in the number of Indians aware'
--       now: 'f Indians aware of and concerned over environmental issues'
--   ENG-2020-Q040    (A)  + 24ch
--       was: 'rson only on the life of self or another person on whom he'
--       now: ' self or another person on whom he has insurable interest.'
--   ENG-2020-Q041    (D)  + 77ch
--       was: 'ive of suggesting ways to remove high indebtedness but has'
--       now: 'ways only to facilitate continued credit by money lenders.'
--   ENG-2021-Q021    (C)  +  9ch
--       was: 'd a strong economy will make the UN position an inevitable'
--       now: 'g economy will make the UN position an inevitable outcome.'
--   ENG-2021-Q024    (B)  +  9ch
--       was: 'ternational violations aimed at nuclear weapon development'
--       now: 'al violations aimed at nuclear weapon development control.'
--   ENG-2021-Q025    (A)  + 15ch
--       was: ' the world economy in such a way that self- sustenance has'
--       now: 'omy in such a way that self- sustenance has become a myth.'
--   ENG-2021-Q035    (A)  + 20ch
--       was: 'y provides an individual worker with a group as well as an'
--       now: 'dual worker with a group as well as an individual identity'
--   ENG-2021-Q036    (A)  + 65ch
--       was: 'by the increasing assignment of higher grades for the same'
--       now: 'ic achievement, has led to a rise in overall GPA averages.'
--   ENG-2021-Q037    (B)  + 16ch
--       was: 'ution should be made to experience real pollution to avoid'
--       now: 'made to experience real pollution to avoid dilly dallying.'
--   ENG-2021-Q044    (C)  + 15ch
--       was: 'ls, have great clout in various spheres for the revival to'
--       now: 'clout in various spheres for the revival to be successful.'
--   ENG-2022-Q044    (B)  + 24ch
--       was: 'ment to arrange a well-organised training program in order'
--       now: 'rganised training program in order to reduce risk factors.'
--   ENG-2023-Q027    (D)  +  9ch
--       was: 'iums of the private players is higher as compared to LIC’s'
--       now: 'he private players is higher as compared to LIC’s premium.'
--   REA-2020-Q007    (E)  + 10ch
--       was: ' statements I and II together are sufficient to answer the'
--       now: 's I and II together are sufficient to answer the question.'
--   ARD-2020-Q005    (E)  + 15ch
--       was: 'Disc harrow'
--       now: 'Disc harrow Solution – (e)'
--   ESI-2020-Q034    (E)  + 15ch
--       was: 'USD 558.5 billion'
--       now: 'USD 558.5 billion Solution – (e)'
--   ESI-2020-Q045    (E)  + 15ch
--       was: 'All of the above'
--       now: 'All of the above Solution – (e)'
--   ESI-2020-Q050    (E)  + 37ch
--       was: 'Rs. 3000'
--       now: 'Rs. 3000 Solution – (e) 1 Marks Questionnaire'
--   ESI-2020-Q057    (E)  + 15ch
--       was: 'Evergreen revolution'
--       now: 'Evergreen revolution Solution – (e)'
--   ESI-2020-Q060    (E)  + 15ch
--       was: 'All of the above (1, 2 & 3)'
--       now: 'All of the above (1, 2 & 3) Solution – (e)'
--
-- None of them changes which option is correct. is_correct and
-- correct_option_id are untouched throughout; only the text of the option
-- changes.
--
-- THE 18 ROWS THIS CANNOT SPEAK FOR, and why they are the right residue:
-- ESI-2020 Q.134 and Q.138 and ARD-2021 Q.14 (15 rows) are the three
-- questions whose options were recovered through special-case paths when
-- the corpus was extracted -- numeric option runs and an (f)-(j) label set.
-- Their loaded text does not correspond to a plain option marker in the
-- source, so a plain reconstruction cannot match them. ENG-2023 Q.30 (3
-- rows) is the two-column collapse already on record. Every one of the 18
-- is a question already known to have been repaired by hand.
-- One of those 18 looked like a second defect and is not. ENG-2023-Q030
-- option C is loaded as "Moderate" where the reconstruction at that label
-- reads "None of the above" -- because the source prints the labels A, B,
-- A, B, C. The page collapsed two columns, so the label run restarts mid-
-- question. The extractor's options_resequenced_from_columns repair
-- renumbered them positionally into printed order, which is what is loaded
-- and is correct: Deprived, Excessive, Moderate, Void, None of the above,
-- all five verbatim from the source. The disagreement is between the
-- source's literal labels and the loaded positional ones -- it is the
-- reconstruction that compared the wrong thing, not the data. Nothing to
-- repair.
--
-- PAPERS: 19. All need a projection re-sync; option text is in the content hash.
--   NABARD-P1-ARD-2021                             1
--   NABARD-P1-ARD-2022-MORNING                     2
--   NABARD-P1-COMPUTER-KNOWLEDGE-2022-MORNING      4
--   NABARD-P1-COMPUTER-KNOWLEDGE-2023              2
--   NABARD-P1-ENGLISH-2020                        16
--   NABARD-P1-ENGLISH-2021                        27
--   NABARD-P1-ENGLISH-2022-EVENING                 5
--   NABARD-P1-ENGLISH-2022-MORNING                 2
--   NABARD-P1-ENGLISH-2023                         3
--   NABARD-P1-ESI-2021                             2
--   NABARD-P1-ESI-2022-EVENING                     1
--   NABARD-P1-ESI-2023                             3
--   NABARD-P1-REASONING-2020                       6
--   NABARD-P1-REASONING-2021                       1
--   NABARD-P1-REASONING-2022-MORNING               1
--   NABARD-P1-REASONING-2023                       6
--   NABARD-P2-ARD-2020                            20
--   NABARD-P2-ARD-2021                             1
--   NABARD-P2-ESI-2020                            21
--
-- BEFORE AND AFTER, all 124:
--   ARD-2021-Q179    (C)  + 22ch  …' area through promotion of in situ' + ' moisture conservation'
--   ARD-2022-Q181    (D)  +  7ch  …'then pink when the fungus produces' + ' spores'
--   ARD-2022-Q183    (B)  + 83ch  …'ty on CSA terminology, components,' + ' relevant issues, and how to contextuali'
--   CK-2022-Q061     (A)* + 13ch  …' image or simply the resolution of' + ' the printer.'
--   CK-2022-Q061     (B)  + 13ch  …' image or simply the resolution of' + ' the printer.'
--   CK-2022-Q061     (C)  + 13ch  …' image or simply the resolution of' + ' the printer.'
--   CK-2022-Q061     (D)  + 13ch  …' image or simply the resolution of' + ' the printer.'
--   CK-2023-Q010     (A)  + 11ch  …'nd deleted when the incognito mode' + ' is closed.'
--   CK-2023-Q010     (B)* + 17ch  …'lder and can be seen by anyone who' + ' uses the device.'
--   ENG-2020-Q022    (D)* + 10ch  …'cts with respect to the conditions' + ' laid down'
--   ENG-2020-Q037    (A)  + 51ch  …'ant raise in the number of Indians' + ' aware of, and concerned about environme'
--   ENG-2020-Q037    (B)  + 49ch  …'cant rise in the number of Indians' + ' aware of and concerned over environment'
--   ENG-2020-Q037    (C)* + 43ch  …'ise in the number of Indians aware' + ' of and concerned over environmental iss'
--   ENG-2020-Q037    (D)  + 41ch  …'ise in the number of Indians aware' + ' and concerned about environmental issue'
--   ENG-2020-Q037    (E)  + 38ch  …'ise in the number of Indians aware' + ' and concerned of environmental issues'
--   ENG-2020-Q040    (A)* + 24ch  …' self or another person on whom he' + ' has insurable interest.'
--   ENG-2020-Q040    (B)  + 13ch  …'egal opinion till his professional' + ' fee is paid.'
--   ENG-2020-Q040    (C)  + 69ch  …' for a certain period within which' + " he doesn't anticipate any problem in th"
--   ENG-2020-Q040    (D)  + 12ch  …'the insurance premium also in case' + ' of a claim.'
--   ENG-2020-Q040    (E)  + 12ch  …'ase of change in the prices of any' + ' other good.'
--   ENG-2020-Q041    (B)  + 47ch  …'existing legislative framework and' + ' enforcement machinery governing money l'
--   ENG-2020-Q041    (D)* + 77ch  …'o remove high indebtedness but has' + ' instead suggested ways only to facilita'
--   ENG-2020-Q041    (E)  + 24ch  …'moneylenders to lend more and more' + ' money to needy persons.'
--   ENG-2020-Q042    (C)  + 19ch  …' money lenders who may squeeze the' + ' borrowers further.'
--   ENG-2020-Q060    (A)  +  9ch  …"s a common vision for the nation's" + ' progress'
--   ENG-2021-Q021    (A)  + 18ch  …' to get a permanent seat in the UN' + ' Security Council.'
--   ENG-2021-Q021    (B)  + 22ch  …'on to become a permanent member in' + ' the security council.'
--   ENG-2021-Q021    (C)* +  9ch  …'make the UN position an inevitable' + ' outcome.'
--   ENG-2021-Q021    (E)  + 54ch  …'the countries will be demanding UN' + ' Security Council seat for India due to '
--   ENG-2021-Q024    (A)  + 14ch  …'me international treaties aimed at' + ' arms control.'
--   ENG-2021-Q024    (B)* +  9ch  …'imed at nuclear weapon development' + ' control.'
--   ENG-2021-Q024    (D)  + 20ch  …' solidified, once India becomes an' + ' economic superpower'
--   ENG-2021-Q025    (A)* + 15ch  …'ch a way that self- sustenance has' + ' become a myth.'
--   ENG-2021-Q025    (B)  + 11ch  …'solving disputes between different' + ' countries.'
--   ENG-2021-Q025    (D)  + 24ch  …'essively worried about a potential' + " enemy's nuclear attack."
--   ENG-2021-Q025    (E)  + 15ch  …'to see India as one of the nuclear' + ' weapon states.'
--   ENG-2021-Q035    (A)* + 20ch  …' worker with a group as well as an' + ' individual identity'
--   ENG-2021-Q035    (B)  + 20ch  …'ideally with a group as well as an' + ' individual identity'
--   ENG-2021-Q035    (C)  + 20ch  …' worker with a group as well as an' + ' individual identity'
--   ENG-2021-Q035    (D)  + 18ch  …'h a group as well as an individual' + ' identity ideally.'
--   ENG-2021-Q035    (E)  + 10ch  …'roup as well as ideally individual' + ' identity.'
--   ENG-2021-Q036    (A)* + 65ch  …'ment of higher grades for the same' + ' academic achievement, has led to a rise'
--   ENG-2021-Q036    (B)  + 63ch  …'s, characterized by the increasing' + ' assignment of higher grades for the sam'
--   ENG-2021-Q036    (C)  + 71ch  …'igher grades for the same academic' + ' achievement, Grade inflation has led to'
--   ENG-2021-Q036    (D)  + 73ch  …' inflation is characterized by the' + ' increasing assignment of higher grades '
--   ENG-2021-Q036    (E)  + 17ch  …'s, sparking debates over the high-' + ' grade assignment'
--   ENG-2021-Q037    (B)* + 16ch  …'experience real pollution to avoid' + ' dilly dallying.'
--   ENG-2021-Q037    (C)  + 45ch  …'y at the ongoing UN Climate Change' + ' Conference to expedite the clean-up pro'
--   ENG-2021-Q037    (D)  + 63ch  …' UN Climate Change Conference with' + ' non-toxic stuff as the members know tha'
--   ENG-2021-Q043    (D)  +  6ch  …', and sometimes non- essential for' + ' them.'
--   ENG-2021-Q044    (C)* + 15ch  …'various spheres for the revival to' + ' be successful.'
--   ENG-2021-Q044    (E)  + 18ch  …' not received any support from the' + ' political people.'
--   ENG-2022-Q025    (A)  + 11ch  …'conomically, resulting in economic' + ' Darwinism.'
--   ENG-2022-Q035    (E)  + 51ch  …' the ground and levelling the area' + ' before laying the foundation for the ne'
--   ENG-2022-Q044    (B)* + 24ch  …'rganised training program in order' + ' to reduce risk factors.'
--   ENG-2022-Q044    (D)  +  9ch  …'anagement organises a well-trained' + ' program.'
--   ENG-2022-Q044    (E)  +  8ch  …' conduct a well-organized training' + ' program'
--   ENG-2022-Q039    (B)  +  8ch  …'h are then implemented by the crew' + ' members'
--   ENG-2022-Q039    (D)  + 10ch  …'s of airline staff through various' + ' tutorials'
--   ENG-2023-Q027    (B)  +  9ch  …'t thus giving it up to the private' + ' players.'
--   ENG-2023-Q027    (C)  +  9ch  …' the private players and the LIC’s' + ' premium.'
--   ENG-2023-Q027    (D)* +  9ch  …'ers is higher as compared to LIC’s' + ' premium.'
--   ESI-2021-Q136    (B)  + 39ch  …'ubsidy reaches the beneficiary and' + ' services to farmers remain affordable.'
--   ESI-2021-Q154    (C)  + 16ch  …'he audit report of Comptroller and' + ' Auditor General'
--   ESI-2022-Q130    (E)  + 18ch  …'he emerging areas under Production' + ' Linked Incentive.'
--   ESI-2023-Q021    (A)  + 31ch  …'ng ‘easier’ without any compromise' + ' on assessing genuine learning.'
--   ESI-2023-Q021    (B)  + 22ch  …'red to offer certification through' + ' modular examinations.'
--   ESI-2023-Q021    (C)  + 64ch  …'s on at least two occasions during' + ' any given school year, with only the be'
--   REA-2020-Q006    (A)  + 61ch  …'er the question, while the data in' + ' statement II alone is not sufficient to'
--   REA-2020-Q006    (B)  + 60ch  …'er the question, while the data in' + ' statement I alone is not sufficient to '
--   REA-2020-Q006    (E)  + 10ch  …'ether are sufficient to answer the' + ' question.'
--   REA-2020-Q007    (A)  + 61ch  …'er the question, while the data in' + ' statement II alone is not sufficient to'
--   REA-2020-Q007    (B)  + 60ch  …'er the question, while the data in' + ' statement I alone is not sufficient to '
--   REA-2020-Q007    (E)* + 10ch  …'ether are sufficient to answer the' + ' question.'
--   REA-2021-Q005    (B)  + 26ch  …'ove of the one on which the person' + ' belongs to Gujarat stays.'
--   REA-2022-Q014    (B)  + 10ch  …'onths of R and the one who is from' + ' Nainital.'
--   REA-2023-Q014    (A)  + 61ch  …'er the question, while the data in' + ' statement II alone is not sufficient to'
--   REA-2023-Q014    (B)  + 60ch  …'er the question, while the data in' + ' statement I alone is not sufficient to '
--   REA-2023-Q014    (C)  + 10ch  …' alone is sufficient to answer the' + ' question.'
--   REA-2023-Q015    (A)  + 61ch  …'er the question, while the data in' + ' statement II alone is not sufficient to'
--   REA-2023-Q015    (B)  + 60ch  …'er the question, while the data in' + ' statement I alone is not sufficient to '
--   REA-2023-Q015    (C)  + 10ch  …' alone is sufficient to answer the' + ' question.'
--   ARD-2020-Q001    (E)  + 15ch  …'Green farming' + ' Solution – (b)'
--   ARD-2020-Q002    (E)  + 15ch  …'White button Mushroom' + ' Solution – (a)'
--   ARD-2020-Q003    (E)  + 15ch  …'Water resource' + ' Solution – (a)'
--   ARD-2020-Q005    (E)* + 15ch  …'Disc harrow' + ' Solution – (e)'
--   ARD-2020-Q006    (E)  + 15ch  …'Ranching' + ' Solution – (b)'
--   ARD-2020-Q007    (E)  + 15ch  …'Social forestry' + ' Solution – (a)'
--   ARD-2020-Q008    (E)  + 15ch  …'< 4.0 ha' + ' Solution – (a)'
--   ARD-2020-Q010    (E)  + 15ch  …'Ramanadhapuram white' + ' Solution – (c)'
--   ARD-2020-Q012    (E)  + 15ch  …'Peaty soils' + ' Solution – (d)'
--   ARD-2020-Q013    (E)  + 15ch  …'Histosols' + ' Solution – (a)'
--   ARD-2020-Q016    (E)  + 15ch  …'Kerala' + ' Solution – (a)'
--   ARD-2020-Q017    (E)  + 15ch  …'70-85%' + ' Solution – (c)'
--   ARD-2020-Q018    (E)  + 15ch  …'Pomegranates, pear' + ' Solution – (a)'
--   ARD-2020-Q020    (E)  + 15ch  …'Alternate cropping' + ' Solution – (a)'
--   ARD-2020-Q023    (E)  + 15ch  …'1-3.5 weeks' + ' Solution – (b)'
--   ARD-2020-Q024    (E)  + 15ch  …'1943' + ' Solution – (b)'
--   ARD-2020-Q026    (E)  + 15ch  …'Demographic Quotient' + ' Solution – (a)'
--   ARD-2020-Q027    (E)  + 15ch  …'1st April 2015' + ' Solution – (c)'
--   ARD-2020-Q029    (E)  + 15ch  …'Bansal Commitee' + ' Solution – (d)'
--   ARD-2020-Q030    (E)  + 15ch  …'1,2 and 3 only' + ' Solution – (d)'
--   ARD-2021-Q015    (E)  + 15ch  …'Fallowing' + ' Solution – (c)'
--   ESI-2020-Q031    (B)  + 25ch  …'rovided benefits under PM SVANIDHI' + ' Scheme by December 2024.'
--   ESI-2020-Q031    (D)  +123ch  …'ing to only those States/UTs which' + ' have notified Rules and Scheme under St'
--   ESI-2020-Q034    (E)* + 15ch  …'USD 558.5 billion' + ' Solution – (e)'
--   ESI-2020-Q037    (E)  + 15ch  …'Muncipalities' + ' Solution – (c)'
--   ESI-2020-Q038    (E)  + 15ch  …'SWAMITVA' + ' Solution – (c)'
--   ESI-2020-Q039    (E)  + 15ch  …'Justice Ranjana Desai committee' + ' Solution – (a)'
--   ESI-2020-Q040    (E)  + 15ch  …'Namami Gange' + ' Solution – (a)'
--   ESI-2020-Q041    (E)  + 15ch  …'KCC' + ' Solution – (c)'
--   ESI-2020-Q042    (E)  + 15ch  …'PRASADH' + ' Solution – (a)'
--   ESI-2020-Q044    (E)  + 15ch  …'Every month' + ' Solution – (a)'
--   ESI-2020-Q045    (E)* + 15ch  …'All of the above' + ' Solution – (e)'
--   ESI-2020-Q046    (E)  + 15ch  …'190' + ' Solution – (a)'
--   ESI-2020-Q047    (E)  + 15ch  …'Nai Roshni' + ' Solution – (a)'
--   ESI-2020-Q050    (E)* + 37ch  …'Rs. 3000' + ' Solution – (e) 1 Marks Questionnaire'
--   ESI-2020-Q051    (E)  + 15ch  …'None of the above' + ' Solution – (a)'
--   ESI-2020-Q054    (E)  + 16ch  …'120' + ' Solution – (a).'
--   ESI-2020-Q057    (E)* + 15ch  …'Evergreen revolution' + ' Solution – (e)'
--   ESI-2020-Q060    (E)* + 15ch  …'All of the above (1, 2 & 3)' + ' Solution – (e)'
--   ESI-2020-Q061    (E)  +171ch  …'Sight (Early Warning Sight)' + ' Solution – (d) Three things you can’t m'
--   ESI-2020-Q065    (E)  + 15ch  …'0-14 years' + ' Solution – (a)'
--   ESI-2020-Q066    (E)  +339ch  …'Telangana' + ' Solution – (a) Tamil Nadu became the fi'
--   (* = the keyed option)
--
-- Guarded on the current value: a no-op if the row has already been
-- repaired.

BEGIN;

UPDATE public.pyq_options o
SET option_text = v.option_text
FROM (VALUES
  ('a9544021-0a17-4125-b3ef-37f3eee11c8c'::uuid,
   'To restore ecological balance of the catchments area through promotion of in situ moisture conservation'),
  ('72d3ed5e-1da4-495d-84a7-86fe27e31d16'::uuid,
   'The centres of these spots later turn black and then pink when the fungus produces spores'),
  ('c46ec6e3-2669-4e45-9556-83562ffe108f'::uuid,
   'Bridge a knowledge gap by providing clarity on CSA terminology, components, relevant issues, and how to contextualize them under different country conditions.'),
  ('b1cb39ed-1860-416b-af8f-6730969e3291'::uuid,
   'Dots per inch refers to the resolution of the output image or simply the resolution of the printer.'),
  ('912c75d0-a3b0-48a4-ad8d-e130e021c03d'::uuid,
   'Disc per inch refers to the resolution of the output image or simply the resolution of the printer.'),
  ('253025e5-1325-4b0e-93bf-a6ad50b35929'::uuid,
   'Dots per inch refers to the resolution of the input image or simply the resolution of the printer.'),
  ('6aac1ce3-c21a-468c-aaa8-28bce0010c74'::uuid,
   'Disc per inch refers to the resolution of the input image or simply the resolution of the printer.'),
  ('87f855d1-8b81-4cde-b9a1-414375fba13f'::uuid,
   'The documents will be saved to a temporary folder and deleted when the incognito mode is closed.'),
  ('756308c6-f799-48ad-99a7-8127a710271c'::uuid,
   'The documents will be saved to the Downloads folder and can be seen by anyone who uses the device.'),
  ('886bf55c-fa6d-4ac5-9d37-7608c7621582'::uuid,
   'finance development projects and appraise those projects with respect to the conditions laid down'),
  ('c35acbef-1980-464e-b954-d46c3d78994b'::uuid,
   'There is little doubt that there has been a significant raise in the number of Indians aware of, and concerned about environmental issues'),
  ('1203acd7-0e20-4819-8fb8-d6e73a37a4ff'::uuid,
   'There is a little doubt that there has been a significant rise in the number of Indians aware of and concerned over environmental issues'),
  ('6dc7e5e3-0af8-48f9-b1de-6e1a2ba11d1e'::uuid,
   'There is little doubt that there has been a significant rise in the number of Indians aware of and concerned over environmental issues'),
  ('2ea49680-0dc7-4c50-9c40-7bb983716179'::uuid,
   'There is little doubt that there has been a significant rise in the number of Indians aware and concerned about environmental issues'),
  ('b0e19306-c835-4fdf-bc80-a5db3c48677f'::uuid,
   'There is little doubt that there has been a significant rise in the number of Indians aware and concerned of environmental issues'),
  ('0a876aaa-8ccc-4737-8256-8f04cbdde00a'::uuid,
   'Insurance can be taken by a person only on the life of self or another person on whom he has insurable interest.'),
  ('c46cd0e4-6535-4b69-9ad2-31c78b8b24ba'::uuid,
   'A lawyer withholding the documents given to him for legal opinion till his professional fee is paid.'),
  ('fd636136-2525-4cfb-b298-1c1ce85ef27a'::uuid,
   'A dealer providing a guarantee for the product he sells for a certain period within which he doesn''t anticipate any problem in the functioning of the product.'),
  ('c00ba2b1-8ed1-46b7-ab70-f6a65808869f'::uuid,
   'An exporter overvaluing his goods in order to cover the insurance premium also in case of a claim.'),
  ('55535c86-2386-46e1-8420-492a0378f31a'::uuid,
   'A shopkeeper selling his goods at higher prices in case of change in the prices of any other good.'),
  ('daad8210-a528-454f-ae59-993e8c4563e7'::uuid,
   'It has not effectively reviewed the efficacy of the existing legislative framework and enforcement machinery governing money lending.'),
  ('86e624c4-11c3-4472-9710-c633eb3e6f85'::uuid,
   'It has not stuck to its objective of suggesting ways to remove high indebtedness but has instead suggested ways only to facilitate continued credit by money lenders.'),
  ('f75da995-d517-4cbf-a16a-8d7455bb6c8c'::uuid,
   'It has not suggested any idea how to convince moneylenders to lend more and more money to needy persons.'),
  ('3a582d78-502a-41f3-8425-064a7c3bf90a'::uuid,
   'it may place more funds at the disposal of the money lenders who may squeeze the borrowers further.'),
  ('b038bc1d-455d-44a2-9fb8-c362b85d2ecf'::uuid,
   'should overcome challenges and work towards a common vision for the nation''s progress'),
  ('05453d39-f9fb-49b1-b784-e714098a1c39'::uuid,
   'Instead of begging, we should apply judicious clout to get a permanent seat in the UN Security Council.'),
  ('8a8085e6-1ac5-48ee-aab7-9248c946ae96'::uuid,
   'By virtue of becoming a nuclear power, India is soon to become a permanent member in the security council.'),
  ('de5e2a27-44cf-4262-8996-020005cf14c7'::uuid,
   'India''s efforts to build a strong economy will make the UN position an inevitable outcome.'),
  ('87bc8499-579e-44f9-ab4d-42e8243ef25f'::uuid,
   'If India becomes a nuclear power, the rest of the countries will be demanding UN Security Council seat for India due to consternation.'),
  ('2b1e5266-8a47-445f-98b1-28fdc2a261d2'::uuid,
   'China''s assistance to Pakistan might have violated some international treaties aimed at arms control.'),
  ('ad5ec2b6-bf4c-42aa-94d5-cc688695aaef'::uuid,
   'The USA retarded certain international violations aimed at nuclear weapon development control.'),
  ('e065eaa7-2601-4c96-9960-222df531e11b'::uuid,
   'India''s permanent position at the UNSC will be solidified, once India becomes an economic superpower'),
  ('33be4628-a2e8-4bcf-960f-8251770b1749'::uuid,
   'The globalisation has changed the world economy in such a way that self- sustenance has become a myth.'),
  ('3ba8465e-83d5-470e-a115-b5684e39c80b'::uuid,
   'UN Security Council has seldom been successful in solving disputes between different countries.'),
  ('98d7f298-e33c-4c53-8529-8fe3a73d8046'::uuid,
   'People who support Indian nuclear programs are excessively worried about a potential enemy''s nuclear attack.'),
  ('4a35cd36-fb3e-4cb0-9b70-3864a2119549'::uuid,
   'UN Security Council permanent members are willing to see India as one of the nuclear weapon states.'),
  ('cf823913-e0b5-41ba-a4e0-71bb052b1e37'::uuid,
   'Corporate culture ideally provides an individual worker with a group as well as an individual identity'),
  ('071c8610-9644-4a13-a52b-476273c8288c'::uuid,
   'Corporate culture provides an individual worker ideally with a group as well as an individual identity'),
  ('d33c2676-5965-4296-9805-8ae65d8962ab'::uuid,
   'Corporate culture provides ideally an individual worker with a group as well as an individual identity'),
  ('6de2e0f4-3d7c-49b3-ba6b-142d5585dbfd'::uuid,
   'Corporate culture provides an individual worker with a group as well as an individual identity ideally.'),
  ('8b5094d6-edaf-4823-87ec-2f540ce0750a'::uuid,
   'Corporate culture provides an individual worker with a group as well as ideally individual identity.'),
  ('6e019910-80fa-44f5-ab6a-b4cb50968005'::uuid,
   'Grade inflation, characterized by the increasing assignment of higher grades for the same academic achievement, has led to a rise in overall GPA averages.'),
  ('5d42af56-ba2c-4486-be94-620e283844e5'::uuid,
   'Grade inflation has led to a rise in overall GPA averages, characterized by the increasing assignment of higher grades for the same academic achievement.'),
  ('c184f7ea-f8b5-49a9-8492-53835abb5e14'::uuid,
   'Characterized by the increasing assignment of higher grades for the same academic achievement, Grade inflation has led to a rise in overall GPA averages'),
  ('61a7babe-7e69-4020-8994-c90e85db128b'::uuid,
   'Led to a rise in overall GPA averages, the Grade inflation is characterized by the increasing assignment of higher grades for the same academic achievement'),
  ('0f352730-20fe-428a-8d8c-9ebc6820088b'::uuid,
   'Grade inflation has led to a rise in overall GPA averages, sparking debates over the high- grade assignment'),
  ('cdcd1bac-a46d-4eae-8fc3-d1d7c8c11766'::uuid,
   'Those who can control pollution should be made to experience real pollution to avoid dilly dallying.'),
  ('664ef76f-5023-48cc-b044-c064d903c3d9'::uuid,
   'There is nothing like a good ingestion of real bad day at the ongoing UN Climate Change Conference to expedite the clean-up process.'),
  ('b0050bb7-287d-4bb5-b50f-4c463e3c778b'::uuid,
   'It makes no sense to recreate polluted fug at the UN Climate Change Conference with non-toxic stuff as the members know that the fug is innocuous.'),
  ('e1f88a8f-791e-43b2-9120-9aefa9381c28'::uuid,
   'The concept of originality is essential sometimes, and sometimes non- essential for them.'),
  ('7178262d-e1c9-4ab4-b7cc-773ef80bde42'::uuid,
   'People, at the core of music revivals, have great clout in various spheres for the revival to be successful.'),
  ('814cb99f-4a9d-4bcf-8222-3886f7dad58e'::uuid,
   'These people at the core of music revivals have not received any support from the political people.'),
  ('43fb4fce-b28b-4e29-9205-0ba9b97c60e6'::uuid,
   'Markets select companies that best perform economically, resulting in economic Darwinism.'),
  ('2a071ea0-30ed-44a6-9bf4-d64f6c30735b'::uuid,
   'The construction crew prepared the site by clearing the ground and levelling the area before laying the foundation for the new building.'),
  ('bf554067-f7e3-4786-87d9-007ca9f711bb'::uuid,
   'It is necessary for the management to arrange a well-organised training program in order to reduce risk factors.'),
  ('d4a5fe91-c2e8-4646-a683-cdf6f92f5a3b'::uuid,
   'A reduction of risk factors can be achieved if the management organises a well-trained program.'),
  ('c5a4679d-c336-4d16-a01d-7c3acd7adc99'::uuid,
   'To reduce the risk factors, management should conduct a well-organized training program'),
  ('0a083396-9c57-4326-93b8-a0c5126b4628'::uuid,
   'New safety measures are formulated using AI, which are then implemented by the crew members'),
  ('dfeac3c0-2041-4c42-83ae-ba07cd762fee'::uuid,
   'AI has been implemented to improve the work ethos of airline staff through various tutorials'),
  ('37dd3a51-75f4-454f-ba46-76dc45186d58'::uuid,
   'LIC failed to maintain the premiums in the Indian market thus giving it up to the private players.'),
  ('22a512a5-3235-4952-b067-a67d5f461f57'::uuid,
   'There is an inverse relation between the premiums of the private players and the LIC’s premium.'),
  ('31675719-d623-4791-bc5e-5055c291d15d'::uuid,
   'The growth in the premiums of the private players is higher as compared to LIC’s premium.'),
  ('1194b0f0-c471-42da-8252-207e04a19c61'::uuid,
   'Cap on lending rate, so that benefit of interest subsidy reaches the beneficiary and services to farmers remain affordable.'),
  ('abb7593a-cf3b-4118-a498-054715c63c6c'::uuid,
   'the primary function of the PAC is to examine the audit report of Comptroller and Auditor General'),
  ('1b91360f-2c9f-4dcc-a357-5026a9086570'::uuid,
   'Scheme will also provide apprenticeships in the emerging areas under Production Linked Incentive.'),
  ('dcfb59ba-1290-4d32-b574-80c8e9362a81'::uuid,
   'All Board examinations must move towards becoming ‘easier’ without any compromise on assessing genuine learning.'),
  ('325e8e80-95b5-455a-9e68-c06251bbf029'::uuid,
   'In ten years, Boards of Examination should be prepared to offer certification through modular examinations.'),
  ('b5ed9be4-46bc-4dc2-8254-1117898a1091'::uuid,
   'All students will be allowed to take Board examinations on at least two occasions during any given school year, with only the best score being retained.'),
  ('945e73a7-4378-4839-96ee-5313cbf4e4b0'::uuid,
   'If the data in statement I alone is sufficient to answer the question, while the data in statement II alone is not sufficient to answer the question.'),
  ('8e95b271-e768-40a2-ad8b-1bff2bbf450f'::uuid,
   'If the data in statement II alone is sufficient to answer the question, while the data in statement I alone is not sufficient to answer the question.'),
  ('5fa9b7cf-0319-4f73-b959-bd329aa27591'::uuid,
   'If the data given in both the statements I and II together are sufficient to answer the question.'),
  ('be3c9c36-1c9b-4adb-a23a-c583eb3385cf'::uuid,
   'If the data in statement I alone is sufficient to answer the question, while the data in statement II alone is not sufficient to answer the question.'),
  ('46505292-d244-472c-bff2-b72cd27939eb'::uuid,
   'If the data in statement II alone is sufficient to answer the question, while the data in statement I alone is not sufficient to answer the question.'),
  ('54d8a68a-b1b7-4d03-8d12-24ea1c49e2b6'::uuid,
   'If the data given in both the statements I and II together are sufficient to answer the question.'),
  ('ed3c6ca4-da40-4fd9-bd4c-116af94c10e4'::uuid,
   'The person from Kerala lives on the floor just above of the one on which the person belongs to Gujarat stays.'),
  ('4c53ad6b-96ea-4986-bf35-828b6f933bd8'::uuid,
   'There is a gap of six months between the birth months of R and the one who is from Nainital.'),
  ('5a6bdacb-5aee-4c9f-a177-247f3a6708e1'::uuid,
   'If the data in statement I alone is sufficient to answer the question, while the data in statement II alone is not sufficient to answer the question.'),
  ('ab21556a-26bb-467b-8981-c48b3c8666db'::uuid,
   'If the data in statement II alone is sufficient to answer the question, while the data in statement I alone is not sufficient to answer the question.'),
  ('63d056e0-9b7e-4b02-8804-42243ecabfa9'::uuid,
   'If the data either in statement I alone or in statement II alone is sufficient to answer the question.'),
  ('e6a5bebb-adf8-4137-a599-76393b648eca'::uuid,
   'If the data in statement I alone is sufficient to answer the question, while the data in statement II alone is not sufficient to answer the question.'),
  ('63f5dd23-233b-4576-98c0-d1047ce3d1d2'::uuid,
   'If the data in statement II alone is sufficient to answer the question, while the data in statement I alone is not sufficient to answer the question.'),
  ('a720ffe8-2e53-403e-a3ea-95ad45590c2d'::uuid,
   'If the data either in statement I alone or in statement II alone is sufficient to answer the question.'),
  ('5f5709f7-6b02-4f27-bcb8-1fe8d83089fb'::uuid,
   'Green farming Solution – (b)'),
  ('dd5bf4a9-c501-4737-a087-4d9a258b7c98'::uuid,
   'White button Mushroom Solution – (a)'),
  ('e8b76c3f-7dfe-46f4-8dc0-d39f4815ebd3'::uuid,
   'Water resource Solution – (a)'),
  ('5c12d514-4d75-4415-b19d-7f9fd9838eb5'::uuid,
   'Disc harrow Solution – (e)'),
  ('afa58a51-1fd1-4485-81db-fd517dcf3849'::uuid,
   'Ranching Solution – (b)'),
  ('c373fa85-5f1e-4c68-b6a9-a9f8182c8de8'::uuid,
   'Social forestry Solution – (a)'),
  ('bce5d27d-fb28-469f-929b-8168ec38255c'::uuid,
   '< 4.0 ha Solution – (a)'),
  ('49b7f4a3-8eb0-4d51-a08d-6f2ee04c42b8'::uuid,
   'Ramanadhapuram white Solution – (c)'),
  ('f813b99f-4def-4277-adfd-11a477507230'::uuid,
   'Peaty soils Solution – (d)'),
  ('a902e7a4-7033-496c-b0db-7003a8d59081'::uuid,
   'Histosols Solution – (a)'),
  ('9d671332-2fca-4805-ae1f-2c4a365207d5'::uuid,
   'Kerala Solution – (a)'),
  ('d8a8b16e-db8d-4a41-abc9-43a1a7dfeea5'::uuid,
   '70-85% Solution – (c)'),
  ('7b60ef28-14c1-40e9-a2ad-4ccfc0b99c69'::uuid,
   'Pomegranates, pear Solution – (a)'),
  ('c82434d1-65fc-4288-a432-2368bdcb214c'::uuid,
   'Alternate cropping Solution – (a)'),
  ('06bd5c9d-1748-4116-aa29-0555fb401735'::uuid,
   '1-3.5 weeks Solution – (b)'),
  ('3d8f9c73-bb8a-4611-b2ea-05a063b326db'::uuid,
   '1943 Solution – (b)'),
  ('a5398dc7-99f6-4e61-bdf9-d3531430d156'::uuid,
   'Demographic Quotient Solution – (a)'),
  ('5943bd7e-981e-46fd-84b9-c7dd20142fea'::uuid,
   '1st April 2015 Solution – (c)'),
  ('cf52ebd9-67fd-4dc3-95ed-d4abee215bc3'::uuid,
   'Bansal Commitee Solution – (d)'),
  ('472d7076-e4e1-4534-9dbd-aff52a21696d'::uuid,
   '1,2 and 3 only Solution – (d)'),
  ('159c8d61-8164-4701-96b0-a5eb3b16addb'::uuid,
   'Fallowing Solution – (c)'),
  ('089f2651-97ac-4123-a704-c8cf6d2c88e7'::uuid,
   'About 42 lakh street vendors are to be provided benefits under PM SVANIDHI Scheme by December 2024.'),
  ('6e351014-3bac-4a16-aec1-ec24cc0b9382'::uuid,
   'The Scheme is available for beneficiaries belonging to only those States/UTs which have notified Rules and Scheme under Street Vendors (Protection of Livelihood and Regulation of Street Vending) Act, 2014.'),
  ('8d4b75d8-9ad1-4285-8be8-490d827ad473'::uuid,
   'USD 558.5 billion Solution – (e)'),
  ('e11be989-fa54-4b2c-942f-46ddda720e4d'::uuid,
   'Muncipalities Solution – (c)'),
  ('a4a3175a-3c81-4a20-becc-6901bdf1467d'::uuid,
   'SWAMITVA Solution – (c)'),
  ('250688f9-8ef4-4b5a-8345-fc77167acaef'::uuid,
   'Justice Ranjana Desai committee Solution – (a)'),
  ('2a6821ff-7134-4f3d-979f-67a9e5738c0b'::uuid,
   'Namami Gange Solution – (a)'),
  ('5e725b22-2ebe-4207-bb1d-3bf685422957'::uuid,
   'KCC Solution – (c)'),
  ('79a7c38f-6840-4e3b-b11e-7708898de86b'::uuid,
   'PRASADH Solution – (a)'),
  ('cf2ed95e-755b-4bf5-971d-33c8aa2d67a5'::uuid,
   'Every month Solution – (a)'),
  ('39a4a1e9-2cf0-40bc-8d19-66f01d3a2f1f'::uuid,
   'All of the above Solution – (e)'),
  ('f18f9a0a-ec3b-4477-a25b-a44c759e9534'::uuid,
   '190 Solution – (a)'),
  ('e2ae7685-d500-44cb-9a0d-b608233c9783'::uuid,
   'Nai Roshni Solution – (a)'),
  ('e9238b9c-5ca2-42c9-b68e-18fb9b2f79f4'::uuid,
   'Rs. 3000 Solution – (e) 1 Marks Questionnaire'),
  ('f559e27e-3dfe-47ce-b9f6-19b00a44ae68'::uuid,
   'None of the above Solution – (a)'),
  ('1a7ecfe4-b9e3-42a7-baca-c1a90add74dc'::uuid,
   '120 Solution – (a).'),
  ('21e50ab5-454c-4a15-85c9-0246e48180f0'::uuid,
   'Evergreen revolution Solution – (e)'),
  ('b8efb55b-466a-46fc-b141-dcc41d98414a'::uuid,
   'All of the above (1, 2 & 3) Solution – (e)'),
  ('d1f05d18-33ef-4f2a-8746-e07a848e53c8'::uuid,
   'Sight (Early Warning Sight) Solution – (d) Three things you can’t miss – Daily current affairs sessions, PIB sessions and Governmental schemes sessions on daily basis. To solve such type of question'),
  ('15a824f0-30c9-4959-b4a6-8b3ba2634868'::uuid,
   '0-14 years Solution – (a)'),
  ('2962591f-b173-4fd7-af6d-3a074674d3ea'::uuid,
   'Telangana Solution – (a) Tamil Nadu became the first Indian state to introduce a law governing contract farming practice. The law has been drafted based on the Model Contract Farming Act, namely “The … State/UT Agricultural Produce and Livestock Contract Farming and Services (Promotion & Facilitation) Act 2018” released by the Centre in May 2018.')
) AS v(option_id, option_text)
WHERE o.id = v.option_id
  AND o.option_text IS DISTINCT FROM v.option_text;

COMMIT;
