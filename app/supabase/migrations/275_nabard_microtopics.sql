-- Migration 275: NABARD Grade A microtopic catalogues for Computer Knowledge,
-- Decision Making, Economic & Social Issues, and Agriculture & Rural Development.
--
-- Derived from the loaded corpus, not from a syllabus document. The source is
-- workbench/nabard_blocks.json -- the reconciled extraction of the NABARD Grade A
-- compendium -- restricted to the four subjects that had zero microtopics. Every
-- microtopic below has at least one real question behind it; the trailing comment
-- on each row names the paper and printed question number. The full
-- question -> microtopic mapping is workbench/nabard-microtopic-map.csv.
-- Nothing here tags a question; that is a separate, reviewed step.
--
--   Computer Knowledge                 6 topics   32 microtopics   100 questions
--   Decision Making                    5           16              40
--   Economic & Social Issues           9          134             286
--   Agriculture & Rural Development   10          109             268
--
-- Two structural notes.
--
-- 1. topics.level is constrained to ('topic','microtopic','concept') by migration
--    029 -- there is no 'section' value -- so the intermediate layer below is
--    stored as level='topic'.
--
-- 2. Every microtopic gets a parent topic, including Decision Making's, which is
--    small enough that a flat list would have read fine. This is not cosmetic:
--    resolve_primary_topic_split() in app/backend/app/admin/pyq_mock_projection.py
--    keys off `parent_topic_id IS NULL`, not off `level`. A microtopic with a null
--    parent projects as topic_id=<itself> and microtopic_id=NULL -- silently
--    reproducing the microtopic_id defect closed in migration 270. A parent topic
--    is what makes these rows project as microtopics.
--
-- GUARDED, for the reason documented at length in migrations 269 and 273: the four
-- subject rows were created outside the migration set and exist only in the
-- production database. The joins below yield zero rows on a database without them
-- instead of raising topics_subject_id_fkey and taking every later migration down.
--
-- metadata carries no `exams` key. Computer Knowledge, Decision Making and
-- Economic & Social Issues are all sat by more than one recruiter (IBPS, RBI
-- Grade B) and the subject rows themselves are not exam-scoped; scoping the
-- leaves to NABARD would block reuse. No `study_sources` are written -- inventing
-- references for corpus-derived microtopics would put unverified claims in the
-- taxonomy.

BEGIN;

-- 1. Intermediate topic layer.
INSERT INTO public.topics
  (subject_id, parent_topic_id, slug, name, level, is_active, metadata)
SELECT
  s.id,
  NULL,
  v.slug,
  v.name,
  'topic',
  true,
  '{"tier":"official"}'::jsonb
FROM (VALUES

  -- Computer Knowledge
  ('0f2ac69b-bd39-422e-bb0d-a81ac4ad3057', 'ck-computer-fundamentals-and-evolution-18562c14',
   'Computer Fundamentals and Evolution'),
  ('0f2ac69b-bd39-422e-bb0d-a81ac4ad3057', 'ck-hardware-peripherals-and-storage-ffde3773',
   'Hardware, Peripherals and Storage'),
  ('0f2ac69b-bd39-422e-bb0d-a81ac4ad3057', 'ck-operating-systems-and-file-management-ec0b60dc',
   'Operating Systems and File Management'),
  ('0f2ac69b-bd39-422e-bb0d-a81ac4ad3057', 'ck-office-productivity-software-37cf8eb5',
   'Office Productivity Software'),
  ('0f2ac69b-bd39-422e-bb0d-a81ac4ad3057', 'ck-networking-and-the-internet-5a2460b6',
   'Networking and the Internet'),
  ('0f2ac69b-bd39-422e-bb0d-a81ac4ad3057', 'ck-cyber-security-and-digital-literacy-38363a20',
   'Cyber Security and Digital Literacy'),
  -- Decision Making
  ('1f91467a-69bd-4515-b125-d60c4e7ca4a0', 'dm-decision-models-and-rationality-5698f6f3',
   'Decision Models and Rationality'),
  ('1f91467a-69bd-4515-b125-d60c4e7ca4a0', 'dm-cognitive-biases-and-barriers-to-decision-making-13c46d63',
   'Cognitive Biases and Barriers to Decision Making'),
  ('1f91467a-69bd-4515-b125-d60c4e7ca4a0', 'dm-group-decision-making-and-communication-810264c7',
   'Group Decision Making and Communication'),
  ('1f91467a-69bd-4515-b125-d60c4e7ca4a0', 'dm-analytical-tools-and-techniques-51c2c5c6',
   'Analytical Tools and Techniques'),
  ('1f91467a-69bd-4515-b125-d60c4e7ca4a0', 'dm-decision-styles-leadership-and-organisational-context-6493a150',
   'Decision Styles, Leadership and Organisational Context'),
  -- Economic & Social Issues
  ('1a874661-957e-4c81-a90f-b0634834d889', 'esi-welfare-schemes-and-social-security-90c97168',
   'Welfare Schemes and Social Security'),
  ('1a874661-957e-4c81-a90f-b0634834d889', 'esi-rural-development-and-panchayati-raj-ffbdc164',
   'Rural Development and Panchayati Raj'),
  ('1a874661-957e-4c81-a90f-b0634834d889', 'esi-education-health-and-human-development-ae9279b2',
   'Education, Health and Human Development'),
  ('1a874661-957e-4c81-a90f-b0634834d889', 'esi-indian-economy-public-finance-and-industry-241499a6',
   'Indian Economy, Public Finance and Industry'),
  ('1a874661-957e-4c81-a90f-b0634834d889', 'esi-banking-credit-and-financial-inclusion-0390a155',
   'Banking, Credit and Financial Inclusion'),
  ('1a874661-957e-4c81-a90f-b0634834d889', 'esi-population-employment-and-social-indicators-a46a7270',
   'Population, Employment and Social Indicators'),
  ('1a874661-957e-4c81-a90f-b0634834d889', 'esi-constitution-governance-and-institutions-06bc814b',
   'Constitution, Governance and Institutions'),
  ('1a874661-957e-4c81-a90f-b0634834d889', 'esi-international-institutions-indices-and-reports-66941411',
   'International Institutions, Indices and Reports'),
  ('1a874661-957e-4c81-a90f-b0634834d889', 'esi-agricultural-economy-and-food-policy-f212195c',
   'Agricultural Economy and Food Policy'),
  -- Agriculture & Rural Development
  ('dd3d3bf2-9da6-4525-a19f-48bf047adb35', 'ard-agronomy-and-crop-production-3598b738',
   'Agronomy and Crop Production'),
  ('dd3d3bf2-9da6-4525-a19f-48bf047adb35', 'ard-soil-science-water-and-agro-meteorology-d2814b31',
   'Soil Science, Water and Agro-meteorology'),
  ('dd3d3bf2-9da6-4525-a19f-48bf047adb35', 'ard-horticulture-and-plantation-crops-b308828f',
   'Horticulture and Plantation Crops'),
  ('dd3d3bf2-9da6-4525-a19f-48bf047adb35', 'ard-plant-protection-and-crop-health-c4aa551d',
   'Plant Protection and Crop Health'),
  ('dd3d3bf2-9da6-4525-a19f-48bf047adb35', 'ard-animal-husbandry-dairy-and-poultry-833df929',
   'Animal Husbandry, Dairy and Poultry'),
  ('dd3d3bf2-9da6-4525-a19f-48bf047adb35', 'ard-fisheries-and-aquaculture-f734ed79',
   'Fisheries and Aquaculture'),
  ('dd3d3bf2-9da6-4525-a19f-48bf047adb35', 'ard-forestry-and-agroforestry-17f6abac',
   'Forestry and Agroforestry'),
  ('dd3d3bf2-9da6-4525-a19f-48bf047adb35', 'ard-agricultural-economics-credit-and-marketing-fb0da521',
   'Agricultural Economics, Credit and Marketing'),
  ('dd3d3bf2-9da6-4525-a19f-48bf047adb35', 'ard-rural-development-schemes-and-institutions-182b97a8',
   'Rural Development, Schemes and Institutions'),
  ('dd3d3bf2-9da6-4525-a19f-48bf047adb35', 'ard-agricultural-engineering-mechanisation-and-extension-843d09ce',
   'Agricultural Engineering, Mechanisation and Extension')
) AS v(subject, slug, name)
JOIN public.subjects s ON s.id = v.subject::uuid
-- NOT EXISTS rather than ON CONFLICT: the unique index is on
-- (subject_id, parent_topic_id, slug) and Postgres treats a NULL
-- parent_topic_id as distinct, so ON CONFLICT does not deduplicate top-level
-- rows -- the same hole documented in admin_exam_intel_manage.py's create path.
WHERE NOT EXISTS (
  SELECT 1 FROM public.topics t
   WHERE t.subject_id = s.id AND t.parent_topic_id IS NULL AND t.slug = v.slug
);

-- 2. Microtopics, parented by topic slug so this file cannot disagree with step 1.
INSERT INTO public.topics
  (subject_id, parent_topic_id, slug, name, level, is_active, metadata)
SELECT
  p.subject_id,
  p.id,
  v.slug,
  v.name,
  'microtopic',
  true,
  '{"tier":"official"}'::jsonb
FROM (VALUES


  -- ===== Computer Knowledge =====

  -- Computer Fundamentals and Evolution
  ('ck-computer-fundamentals-and-evolution-18562c14', 'ck-computer-fundamentals-and-basic-terminology-d30552ba',
   'Computer fundamentals and basic terminology'),   -- 1q: P1-COMPUTER-KNOWLEDGE-2020 Q66
  ('ck-computer-fundamentals-and-evolution-18562c14', 'ck-generations-of-computers-and-hardware-evolution-c0d1c6dd',
   'Generations of computers and hardware evolution'),   -- 3q: P1-COMPUTER-KNOWLEDGE-2022-EVENING Q59, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q70, P1-COMPUTER-KNOWLEDGE-2023 Q14
  ('ck-computer-fundamentals-and-evolution-18562c14', 'ck-pioneers-and-landmarks-in-computing-history-7da86b59',
   'Pioneers and landmarks in computing history'),   -- 3q: P1-COMPUTER-KNOWLEDGE-2022-EVENING Q60, P1-COMPUTER-KNOWLEDGE-2023 Q4, P1-COMPUTER-KNOWLEDGE-2023 Q18
  ('ck-computer-fundamentals-and-evolution-18562c14', 'ck-programming-languages-and-their-generations-82dc1184',
   'Programming languages and their generations'),   -- 2q: P1-COMPUTER-KNOWLEDGE-2021 Q60, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q62
  ('ck-computer-fundamentals-and-evolution-18562c14', 'ck-emerging-computing-paradigms-7430a4af',
   'Emerging computing paradigms'),   -- 1q: P1-COMPUTER-KNOWLEDGE-2023 Q15

  -- Hardware, Peripherals and Storage
  ('ck-hardware-peripherals-and-storage-ffde3773', 'ck-input-devices-and-pointing-hardware-29b27c37',
   'Input devices and pointing hardware'),   -- 5q: P1-COMPUTER-KNOWLEDGE-2020 Q64, P1-COMPUTER-KNOWLEDGE-2020 Q77, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q58, P1-COMPUTER-KNOWLEDGE-2023 Q13, P1-COMPUTER-KNOWLEDGE-2023 Q17
  ('ck-hardware-peripherals-and-storage-ffde3773', 'ck-printers-printing-metrics-and-display-hardware-67bde690',
   'Printers, printing metrics and display hardware'),   -- 5q: P1-COMPUTER-KNOWLEDGE-2020 Q68, P1-COMPUTER-KNOWLEDGE-2020 Q72, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q61, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q66, P1-COMPUTER-KNOWLEDGE-2023 Q16
  ('ck-hardware-peripherals-and-storage-ffde3773', 'ck-ports-connectors-and-expansion-interfaces-2f979e79',
   'Ports, connectors and expansion interfaces'),   -- 2q: P1-COMPUTER-KNOWLEDGE-2021 Q53, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q62
  ('ck-hardware-peripherals-and-storage-ffde3773', 'ck-microprocessors-registers-and-digital-logic-abc4b913',
   'Microprocessors, registers and digital logic'),   -- 3q: P1-COMPUTER-KNOWLEDGE-2021 Q62, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q68, P1-COMPUTER-KNOWLEDGE-2023 Q8
  ('ck-hardware-peripherals-and-storage-ffde3773', 'ck-number-systems-and-binary-arithmetic-9f34a429',
   'Number systems and binary arithmetic'),   -- 1q: P1-COMPUTER-KNOWLEDGE-2022-MORNING Q55
  ('ck-hardware-peripherals-and-storage-ffde3773', 'ck-memory-types-and-the-memory-hierarchy-dbad8600',
   'Memory types and the memory hierarchy'),   -- 4q: P1-COMPUTER-KNOWLEDGE-2022-MORNING Q65, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q56, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q67, P1-COMPUTER-KNOWLEDGE-2023 Q11
  ('ck-hardware-peripherals-and-storage-ffde3773', 'ck-storage-media-capacity-and-compression-6859be60',
   'Storage media, capacity and compression'),   -- 4q: P1-COMPUTER-KNOWLEDGE-2021 Q70, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q57, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q64, P1-COMPUTER-KNOWLEDGE-2023 Q19

  -- Operating Systems and File Management
  ('ck-operating-systems-and-file-management-ec0b60dc', 'ck-booting-bios-and-system-startup-77819ad1',
   'Booting, BIOS and system startup'),   -- 4q: P1-COMPUTER-KNOWLEDGE-2020 Q71, P1-COMPUTER-KNOWLEDGE-2021 Q59, P1-COMPUTER-KNOWLEDGE-2021 Q69, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q57
  ('ck-operating-systems-and-file-management-ec0b60dc', 'ck-operating-systems-utilities-and-system-software-97034c9c',
   'Operating systems, utilities and system software'),   -- 5q: P1-COMPUTER-KNOWLEDGE-2020 Q80, P1-COMPUTER-KNOWLEDGE-2021 Q63, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q70, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q69, P1-COMPUTER-KNOWLEDGE-2023 Q9
  ('ck-operating-systems-and-file-management-ec0b60dc', 'ck-file-and-folder-management-da299b46',
   'File and folder management'),   -- 4q: P1-COMPUTER-KNOWLEDGE-2020 Q63, P1-COMPUTER-KNOWLEDGE-2021 Q52, P1-COMPUTER-KNOWLEDGE-2021 Q56, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q58
  ('ck-operating-systems-and-file-management-ec0b60dc', 'ck-windows-shortcuts-and-desktop-navigation-030741a2',
   'Windows shortcuts and desktop navigation'),   -- 3q: P1-COMPUTER-KNOWLEDGE-2023 Q2, P1-COMPUTER-KNOWLEDGE-2023 Q6, P1-COMPUTER-KNOWLEDGE-2023 Q20

  -- Office Productivity Software
  ('ck-office-productivity-software-37cf8eb5', 'ck-ms-word-page-setup-and-formatting-d552a60e',
   'MS Word page setup and formatting'),   -- 3q: P1-COMPUTER-KNOWLEDGE-2020 Q69, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q51, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q63
  ('ck-office-productivity-software-37cf8eb5', 'ck-ms-word-ribbon-tabs-and-shortcuts-c27848f8',
   'MS Word ribbon, tabs and shortcuts'),   -- 6q: P1-COMPUTER-KNOWLEDGE-2020 Q73, P1-COMPUTER-KNOWLEDGE-2021 Q54, P1-COMPUTER-KNOWLEDGE-2021 Q61, P1-COMPUTER-KNOWLEDGE-2021 Q65, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q69, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q65
  ('ck-office-productivity-software-37cf8eb5', 'ck-ms-excel-formulas-and-functions-4bfb4eef',
   'MS Excel formulas and functions'),   -- 2q: P1-COMPUTER-KNOWLEDGE-2021 Q64, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q53
  ('ck-office-productivity-software-37cf8eb5', 'ck-ms-excel-cell-references-shortcuts-and-display-behaviour-125ece4e',
   'MS Excel cell references, shortcuts and display behaviour'),   -- 6q: P1-COMPUTER-KNOWLEDGE-2020 Q74, P1-COMPUTER-KNOWLEDGE-2021 Q55, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q54, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q60, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q63, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q67
  ('ck-office-productivity-software-37cf8eb5', 'ck-ms-excel-charts-and-macros-81d631a7',
   'MS Excel charts and macros'),   -- 3q: P1-COMPUTER-KNOWLEDGE-2021 Q67, P1-COMPUTER-KNOWLEDGE-2021 Q68, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q59
  ('ck-office-productivity-software-37cf8eb5', 'ck-ms-powerpoint-views-and-slide-show-controls-be71eae2',
   'MS PowerPoint views and slide show controls'),   -- 2q: P1-COMPUTER-KNOWLEDGE-2022-MORNING Q56, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q54

  -- Networking and the Internet
  ('ck-networking-and-the-internet-5a2460b6', 'ck-network-types-and-scale-dbf6bf7d',
   'Network types and scale'),   -- 1q: P1-COMPUTER-KNOWLEDGE-2020 Q61
  ('ck-networking-and-the-internet-5a2460b6', 'ck-network-topologies-0b6b1ec5',
   'Network topologies'),   -- 3q: P1-COMPUTER-KNOWLEDGE-2020 Q75, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q64, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q61
  ('ck-networking-and-the-internet-5a2460b6', 'ck-networking-devices-3e223e93',
   'Networking devices'),   -- 3q: P1-COMPUTER-KNOWLEDGE-2020 Q67, P1-COMPUTER-KNOWLEDGE-2021 Q58, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q55
  ('ck-networking-and-the-internet-5a2460b6', 'ck-osi-model-and-ip-addressing-15b04d54',
   'OSI model and IP addressing'),   -- 2q: P1-COMPUTER-KNOWLEDGE-2020 Q79, P1-COMPUTER-KNOWLEDGE-2021 Q57
  ('ck-networking-and-the-internet-5a2460b6', 'ck-internet-protocols-and-addressing-d6583563',
   'Internet protocols and addressing'),   -- 2q: P1-COMPUTER-KNOWLEDGE-2020 Q65, P1-COMPUTER-KNOWLEDGE-2021 Q51
  ('ck-networking-and-the-internet-5a2460b6', 'ck-web-browsers-and-browsing-privacy-dc79e064',
   'Web browsers and browsing privacy'),   -- 5q: P1-COMPUTER-KNOWLEDGE-2020 Q78, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q52, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q53, P1-COMPUTER-KNOWLEDGE-2023 Q3, P1-COMPUTER-KNOWLEDGE-2023 Q10
  ('ck-networking-and-the-internet-5a2460b6', 'ck-email-fields-and-conventions-a8a98e6b',
   'Email fields and conventions'),   -- 2q: P1-COMPUTER-KNOWLEDGE-2021 Q66, P1-COMPUTER-KNOWLEDGE-2023 Q12

  -- Cyber Security and Digital Literacy
  ('ck-cyber-security-and-digital-literacy-38363a20', 'ck-malware-types-and-antivirus-software-05eb4896',
   'Malware types and antivirus software'),   -- 3q: P1-COMPUTER-KNOWLEDGE-2020 Q70, P1-COMPUTER-KNOWLEDGE-2020 Q76, P1-COMPUTER-KNOWLEDGE-2022-MORNING Q66
  ('ck-cyber-security-and-digital-literacy-38363a20', 'ck-firewalls-phishing-and-safe-computing-624a87e3',
   'Firewalls, phishing and safe computing'),   -- 3q: P1-COMPUTER-KNOWLEDGE-2020 Q62, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q52, P1-COMPUTER-KNOWLEDGE-2023 Q7
  ('ck-cyber-security-and-digital-literacy-38363a20', 'ck-file-formats-encoding-standards-and-multimedia-19b41cd1',
   'File formats, encoding standards and multimedia'),   -- 4q: P1-COMPUTER-KNOWLEDGE-2022-EVENING Q51, P1-COMPUTER-KNOWLEDGE-2022-EVENING Q68, P1-COMPUTER-KNOWLEDGE-2023 Q1, P1-COMPUTER-KNOWLEDGE-2023 Q5

  -- ===== Decision Making =====

  -- Decision Models and Rationality
  ('dm-decision-models-and-rationality-5698f6f3', 'dm-rational-decision-making-model-and-its-assumptions-4e7de69b',
   'Rational decision-making model and its assumptions'),   -- 2q: P1-DECISION-MAKING-2022-EVENING Q95, P1-DECISION-MAKING-2023 Q9
  ('dm-decision-models-and-rationality-5698f6f3', 'dm-bounded-rationality-and-limits-on-information-processing-5f6bbc58',
   'Bounded rationality and limits on information processing'),   -- 3q: P1-DECISION-MAKING-2022-EVENING Q94, P1-DECISION-MAKING-2022-EVENING Q98, P1-DECISION-MAKING-2023 Q8
  ('dm-decision-models-and-rationality-5698f6f3', 'dm-types-of-decisions-and-decision-levels-89e1bfd5',
   'Types of decisions and decision levels'),   -- 2q: P1-DECISION-MAKING-2021 Q93, P1-DECISION-MAKING-2022-EVENING Q92
  ('dm-decision-models-and-rationality-5698f6f3', 'dm-steps-in-the-decision-making-process-0df42d5e',
   'Steps in the decision-making process'),   -- 3q: P1-DECISION-MAKING-2021 Q92, P1-DECISION-MAKING-2022-EVENING Q100, P1-DECISION-MAKING-2023 Q6

  -- Cognitive Biases and Barriers to Decision Making
  ('dm-cognitive-biases-and-barriers-to-decision-making-13c46d63', 'dm-anchoring-framing-and-presentation-effects-f98cb084',
   'Anchoring, framing and presentation effects'),   -- 3q: P1-DECISION-MAKING-2022-MORNING Q94, P1-DECISION-MAKING-2022-EVENING Q93, P1-DECISION-MAKING-2022-EVENING Q96
  ('dm-cognitive-biases-and-barriers-to-decision-making-13c46d63', 'dm-overconfidence-and-status-quo-bias-05d95d99',
   'Overconfidence and status-quo bias'),   -- 2q: P1-DECISION-MAKING-2021 Q99, P1-DECISION-MAKING-2022-MORNING Q99
  ('dm-cognitive-biases-and-barriers-to-decision-making-13c46d63', 'dm-selective-perception-and-similarity-bias-e03616b7',
   'Selective perception and similarity bias'),   -- 2q: P1-DECISION-MAKING-2021 Q96, P1-DECISION-MAKING-2022-MORNING Q92
  ('dm-cognitive-biases-and-barriers-to-decision-making-13c46d63', 'dm-confirmation-bias-and-debiasing-strategies-0567e8ea',
   'Confirmation bias and debiasing strategies'),   -- 1q: P1-DECISION-MAKING-2023 Q2

  -- Group Decision Making and Communication
  ('dm-group-decision-making-and-communication-810264c7', 'dm-structured-group-decision-making-techniques-3008c348',
   'Structured group decision-making techniques'),   -- 5q: P1-DECISION-MAKING-2021 Q91, P1-DECISION-MAKING-2021 Q98, P1-DECISION-MAKING-2022-EVENING Q91, P1-DECISION-MAKING-2022-EVENING Q97, P1-DECISION-MAKING-2023 Q4
  ('dm-group-decision-making-and-communication-810264c7', 'dm-communication-conflict-and-delay-in-group-decisions-2de1c775',
   'Communication, conflict and delay in group decisions'),   -- 3q: P1-DECISION-MAKING-2022-MORNING Q98, P1-DECISION-MAKING-2023 Q3, P1-DECISION-MAKING-2023 Q10

  -- Analytical Tools and Techniques
  ('dm-analytical-tools-and-techniques-51c2c5c6', 'dm-root-cause-analysis-and-problem-solving-tools-a1ae3806',
   'Root cause analysis and problem-solving tools'),   -- 4q: P1-DECISION-MAKING-2021 Q95, P1-DECISION-MAKING-2022-MORNING Q93, P1-DECISION-MAKING-2022-MORNING Q97, P1-DECISION-MAKING-2023 Q1
  ('dm-analytical-tools-and-techniques-51c2c5c6', 'dm-quantitative-methods-and-analytics-in-decision-making-701a2eb5',
   'Quantitative methods and analytics in decision making'),   -- 2q: P1-DECISION-MAKING-2022-MORNING Q91, P1-DECISION-MAKING-2022-MORNING Q95
  ('dm-analytical-tools-and-techniques-51c2c5c6', 'dm-heuristics-and-judgemental-problems-098fa72f',
   'Heuristics and judgemental problems'),   -- 2q: P1-DECISION-MAKING-2022-MORNING Q96, P1-DECISION-MAKING-2023 Q7

  -- Decision Styles, Leadership and Organisational Context
  ('dm-decision-styles-leadership-and-organisational-context-6493a150', 'dm-decision-making-styles-and-leadership-approaches-b2d84bc0',
   'Decision-making styles and leadership approaches'),   -- 3q: P1-DECISION-MAKING-2021 Q100, P1-DECISION-MAKING-2022-MORNING Q100, P1-DECISION-MAKING-2023 Q5
  ('dm-decision-styles-leadership-and-organisational-context-6493a150', 'dm-decision-theories-from-allied-disciplines-2f9e04a5',
   'Decision theories from allied disciplines'),   -- 2q: P1-DECISION-MAKING-2021 Q97, P1-DECISION-MAKING-2022-EVENING Q99
  ('dm-decision-styles-leadership-and-organisational-context-6493a150', 'dm-individual-and-organisational-factors-affecting-decisions-8af4dac7',
   'Individual and organisational factors affecting decisions'),   -- 1q: P1-DECISION-MAKING-2021 Q94

  -- ===== Economic & Social Issues =====

  -- Welfare Schemes and Social Security
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-life-and-accident-insurance-schemes-for-the-poor-dafd168f',
   'Life and accident insurance schemes for the poor'),   -- 6q: P1-ESI-2022-MORNING Q124, P1-ESI-2022-MORNING Q145, P1-ESI-2022-MORNING Q149, P1-ESI-2022-EVENING Q121, P1-ESI-2022-EVENING Q122, P1-ESI-2022-EVENING Q142
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-pension-schemes-for-unorganised-workers-and-farmers-d8bd0eda',
   'Pension schemes for unorganised workers and farmers'),   -- 9q: P1-ESI-2020 Q158, P1-ESI-2021 Q141, P1-ESI-2022-MORNING Q125, P1-ESI-2022-EVENING Q133, P1-ESI-2022-EVENING Q155, P1-ESI-2022-EVENING Q157 ...
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-employees-provident-fund-esi-and-statutory-social-security-12456dd6',
   'Employees'' provident fund, ESI and statutory social security'),   -- 3q: P1-ESI-2022-MORNING Q134, P1-ESI-2022-MORNING Q135, P1-ESI-2022-EVENING Q138
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-national-social-assistance-programme-and-family-benefits-81ed3eb1',
   'National Social Assistance Programme and family benefits'),   -- 1q: P1-ESI-2022-MORNING Q146
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-women-and-child-welfare-schemes-b322a19f',
   'Women and child welfare schemes'),   -- 5q: P1-ESI-2021 Q122, P1-ESI-2022-EVENING Q139, P1-ESI-2022-EVENING Q158, P1-ESI-2023 Q8, P2-ESI-2020 Q36
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-welfare-schemes-for-senior-citizens-23df6fc0',
   'Welfare schemes for senior citizens'),   -- 1q: P1-ESI-2022-MORNING Q144
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-minority-welfare-schemes-81953b4a',
   'Minority welfare schemes'),   -- 1q: P1-ESI-2022-MORNING Q150
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-street-vendor-credit-and-livelihood-schemes-1f8c2168',
   'Street vendor credit and livelihood schemes'),   -- 3q: P1-ESI-2022-EVENING Q132, P2-ESI-2020 Q31, P2-ARD-2023 Q30
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-artisan-and-traditional-trade-schemes-7f089b75',
   'Artisan and traditional-trade schemes'),   -- 2q: P1-ESI-2023 Q4, P2-ARD-2023 Q26
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-sanitation-worker-welfare-and-mechanised-sanitation-3201cd8f',
   'Sanitation worker welfare and mechanised sanitation'),   -- 3q: P2-ESI-2022 Q2, P2-ESI-2022 Q3, P2-ESI-2022 Q4
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-clean-cooking-fuel-and-energy-access-schemes-14bfe216',
   'Clean cooking fuel and energy access schemes'),   -- 2q: P1-ESI-2022-EVENING Q145, P1-ESI-2023 Q33
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-food-security-pds-and-free-foodgrain-schemes-f4f74cbc',
   'Food security, PDS and free foodgrain schemes'),   -- 2q: P1-ESI-2023 Q32, P2-ESI-2022 Q11
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-pandemic-relief-packages-and-worker-support-fa7351c0',
   'Pandemic relief packages and worker support'),   -- 2q: P1-ESI-2021 Q131, P2-ESI-2021 Q12
  ('esi-welfare-schemes-and-social-security-90c97168', 'esi-poverty-alleviation-packages-and-garib-kalyan-schemes-edf1c6f8',
   'Poverty alleviation packages and Garib Kalyan schemes'),   -- 1q: P1-ESI-2020 Q160

  -- Rural Development and Panchayati Raj
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-mgnrega-design-entitlements-and-performance-91290406',
   'MGNREGA design, entitlements and performance'),   -- 9q: P1-ESI-2022-EVENING Q149, P1-ESI-2023 Q5, P2-ESI-2020 Q37, P2-ESI-2021 Q5, P2-ESI-2022 Q12, P2-ARD-2023 Q9 ...
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-day-nrlm-self-help-groups-and-rural-livelihoods-afd82160',
   'DAY-NRLM, self-help groups and rural livelihoods'),   -- 5q: P1-ESI-2020 Q159, P1-ESI-2021 Q142, P1-ESI-2021 Q160, P1-ESI-2023 Q30, P2-ESI-2020 Q38
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-rural-roads-and-pmgsy-2cb50665',
   'Rural roads and PMGSY'),   -- 5q: P1-ESI-2020 Q154, P1-ESI-2022-MORNING Q154, P1-ESI-2022-EVENING Q129, P1-ESI-2022-EVENING Q153, P1-ESI-2023 Q9
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-rural-and-urban-housing-schemes-92031959',
   'Rural and urban housing schemes'),   -- 4q: P1-ESI-2021 Q145, P1-ESI-2023 Q40, P2-ESI-2022 Q5, P2-ESI-2022 Q6
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-swachh-bharat-and-sanitation-missions-9b655979',
   'Swachh Bharat and sanitation missions'),   -- 5q: P1-ESI-2022-EVENING Q126, P1-ESI-2023 Q11, P2-ESI-2020 Q40, P2-ESI-2021 Q1, P2-ESI-2022 Q7
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-drinking-water-supply-and-jal-jeevan-mission-c4aff951',
   'Drinking water supply and Jal Jeevan Mission'),   -- 2q: P1-ESI-2022-MORNING Q151, P1-ESI-2022-MORNING Q160
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-village-and-gram-panchayat-development-schemes-5199e3ce',
   'Village and Gram Panchayat development schemes'),   -- 1q: P1-ESI-2020 Q123
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-panchayati-raj-institutions-and-rural-governance-96724f0e',
   'Panchayati Raj institutions and rural governance'),   -- 2q: P1-ESI-2020 Q151, P1-ESI-2021 Q159
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-aspirational-districts-programme-6a7644df',
   'Aspirational Districts Programme'),   -- 3q: P1-ESI-2020 Q153, P1-ESI-2022-EVENING Q124, P1-ESI-2022-EVENING Q152
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-rurban-clusters-and-rural-cluster-development-fb33f5cb',
   'Rurban clusters and rural cluster development'),   -- 1q: P2-ESI-2020 Q42
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-rural-skilling-and-livelihood-missions-3289ae30',
   'Rural skilling and livelihood missions'),   -- 1q: P1-ESI-2020 Q127
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-rural-entrepreneurship-and-business-incubation-31c4257a',
   'Rural entrepreneurship and business incubation'),   -- 1q: P1-ESI-2023 Q17
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-rural-development-outreach-campaigns-943bd6d3',
   'Rural development outreach campaigns'),   -- 1q: P1-ESI-2022-MORNING Q136
  ('esi-rural-development-and-panchayati-raj-ffbdc164', 'esi-rural-land-records-and-property-rights-3ca875b7',
   'Rural land records and property rights'),   -- 1q: P2-ARD-2023 Q28

  -- Education, Health and Human Development
  ('esi-education-health-and-human-development-ae9279b2', 'esi-national-education-policy-2020-fd9f53fb',
   'National Education Policy 2020'),   -- 5q: P1-ESI-2020 Q149, P1-ESI-2021 Q135, P2-ESI-2021 Q4, P2-ESI-2021 Q13, P2-ESI-2021 Q14
  ('esi-education-health-and-human-development-ae9279b2', 'esi-school-education-schemes-and-curriculum-frameworks-ce15e747',
   'School education schemes and curriculum frameworks'),   -- 5q: P1-ESI-2021 Q121, P1-ESI-2021 Q128, P1-ESI-2022-EVENING Q140, P1-ESI-2023 Q6, P1-ESI-2023 Q21
  ('esi-education-health-and-human-development-ae9279b2', 'esi-higher-education-enrolment-and-aishe-05a008bf',
   'Higher education, enrolment and AISHE'),   -- 2q: P1-ESI-2021 Q137, P1-ESI-2022-MORNING Q141
  ('esi-education-health-and-human-development-ae9279b2', 'esi-scholarships-and-student-support-schemes-8b26012c',
   'Scholarships and student support schemes'),   -- 3q: P1-ESI-2022-EVENING Q131, P1-ESI-2023 Q37, P2-ARD-2023 Q27
  ('esi-education-health-and-human-development-ae9279b2', 'esi-adult-vocational-and-non-formal-education-e5e53aa8',
   'Adult, vocational and non-formal education'),   -- 1q: P1-ESI-2023 Q28
  ('esi-education-health-and-human-development-ae9279b2', 'esi-tribal-residential-education-f08200bf',
   'Tribal residential education'),   -- 1q: P2-ESI-2020 Q33
  ('esi-education-health-and-human-development-ae9279b2', 'esi-education-sector-market-and-online-learning-de9bb541',
   'Education sector market and online learning'),   -- 2q: P2-ESI-2021 Q6, P2-ESI-2021 Q15
  ('esi-education-health-and-human-development-ae9279b2', 'esi-ayushman-bharat-and-health-insurance-0f8290e9',
   'Ayushman Bharat and health insurance'),   -- 3q: P1-ESI-2023 Q38, P2-ESI-2021 Q10, P2-ESI-2021 Q11
  ('esi-education-health-and-human-development-ae9279b2', 'esi-nutrition-missions-and-poshan-48098655',
   'Nutrition missions and POSHAN'),   -- 1q: P1-ESI-2022-EVENING Q143
  ('esi-education-health-and-human-development-ae9279b2', 'esi-food-safety-and-standards-212bf3e8',
   'Food safety and standards'),   -- 1q: P1-ESI-2022-EVENING Q144
  ('esi-education-health-and-human-development-ae9279b2', 'esi-national-family-health-surveys-and-health-indicators-534c5545',
   'National family health surveys and health indicators'),   -- 1q: P1-ESI-2022-EVENING Q154
  ('esi-education-health-and-human-development-ae9279b2', 'esi-community-health-workers-and-maternal-child-health-programmes-367b24d2',
   'Community health workers and maternal-child health programmes'),   -- 2q: P2-ESI-2022 Q14, P2-ESI-2022 Q15
  ('esi-education-health-and-human-development-ae9279b2', 'esi-disease-elimination-missions-95daea43',
   'Disease elimination missions'),   -- 4q: P2-ARD-2023 Q13, P2-ARD-2023 Q14, P2-ARD-2023 Q15, P2-ARD-2023 Q16
  ('esi-education-health-and-human-development-ae9279b2', 'esi-right-to-education-act-f785667a',
   'Right to Education Act'),   -- 1q: P2-ARD-2020 Q27

  -- Indian Economy, Public Finance and Industry
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-national-income-aggregates-and-growth-estimates-10e4a846',
   'National income aggregates and growth estimates'),   -- 1q: P1-ESI-2020 Q128
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-sectoral-composition-of-the-economy-68abedde',
   'Sectoral composition of the economy'),   -- 2q: P1-ESI-2020 Q152, P1-ESI-2022-MORNING Q122
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-inflation-measurement-and-price-indices-b4ee8a99',
   'Inflation measurement and price indices'),   -- 3q: P1-ESI-2020 Q126, P1-ESI-2021 Q153, P1-ESI-2023 Q1
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-monetary-policy-framework-and-inflation-targeting-b6fadc02',
   'Monetary policy framework and inflation targeting'),   -- 1q: P1-ESI-2022-MORNING Q142
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-union-budget-provisions-and-taxation-f43747fa',
   'Union Budget provisions and taxation'),   -- 6q: P1-ESI-2020 Q139, P1-ESI-2020 Q140, P1-ESI-2021 Q139, P1-ESI-2021 Q144, P1-ESI-2022-MORNING Q143, P2-ARD-2023 Q17
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-fiscal-deficit-and-public-finance-3cbd6dfc',
   'Fiscal deficit and public finance'),   -- 1q: P1-ESI-2021 Q143
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-public-debt-and-external-liabilities-c0e148a4',
   'Public debt and external liabilities'),   -- 1q: P2-ESI-2020 Q34
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-balance-of-payments-and-the-external-sector-a23a8009',
   'Balance of payments and the external sector'),   -- 2q: P1-ESI-2020 Q142, P1-ESI-2021 Q151
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-industrial-production-and-statistical-agencies-cb39c8b6',
   'Industrial production and statistical agencies'),   -- 2q: P1-ESI-2020 Q141, P1-ESI-2023 Q15
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-industrial-policy-and-manufacturing-ea8d14cb',
   'Industrial policy and manufacturing'),   -- 1q: P1-ESI-2020 Q147
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-msme-sector-and-its-contribution-7e42574b',
   'MSME sector and its contribution'),   -- 2q: P1-ESI-2022-MORNING Q139, P1-ESI-2022-EVENING Q127
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-khadi-coir-and-village-industries-8966daf6',
   'Khadi, coir and village industries'),   -- 2q: P1-ESI-2022-EVENING Q128, P1-ESI-2023 Q7
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-ease-of-doing-business-and-reform-rankings-b783fb34',
   'Ease of doing business and reform rankings'),   -- 1q: P1-ESI-2022-MORNING Q130
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-state-and-regional-economic-performance-9e62f78b',
   'State and regional economic performance'),   -- 1q: P1-ESI-2020 Q131
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-infrastructure-transport-and-logistics-dd054b55',
   'Infrastructure, transport and logistics'),   -- 2q: P1-ESI-2022-MORNING Q137, P1-ESI-2022-EVENING Q147
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-national-infrastructure-pipeline-and-project-dashboards-79cb371c',
   'National Infrastructure Pipeline and project dashboards'),   -- 3q: P2-ESI-2020 Q58, P2-ESI-2020 Q59, P2-ESI-2020 Q60
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-renewable-energy-targets-and-efficiency-schemes-27352d93',
   'Renewable energy targets and efficiency schemes'),   -- 2q: P2-ESI-2020 Q46, P2-ESI-2020 Q47
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-economic-reforms-of-1991-and-liberalisation-94cfbdf0',
   'Economic reforms of 1991 and liberalisation'),   -- 1q: P2-ESI-2022 Q13
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-insolvency-and-economic-legislation-e23a20e2',
   'Insolvency and economic legislation'),   -- 1q: P1-ESI-2020 Q130
  ('esi-indian-economy-public-finance-and-industry-241499a6', 'esi-long-term-growth-strategy-and-policy-vision-c7c157e1',
   'Long-term growth strategy and policy vision'),   -- 1q: P1-ESI-2023 Q13

  -- Banking, Credit and Financial Inclusion
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-nabard-ridf-and-development-finance-6429a74d',
   'NABARD, RIDF and development finance'),   -- 2q: P1-ESI-2020 Q134, P1-ESI-2022-EVENING Q150
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-priority-sector-lending-norms-05568a2d',
   'Priority sector lending norms'),   -- 3q: P1-ESI-2021 Q134, P1-ESI-2023 Q23, P1-ESI-2023 Q24
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-kisan-credit-card-and-agricultural-credit-507c08b4',
   'Kisan Credit Card and agricultural credit'),   -- 1q: P1-ESI-2021 Q132
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-differentiated-banks-and-rural-banking-4d20c619',
   'Differentiated banks and rural banking'),   -- 2q: P1-ESI-2021 Q133, P1-ESI-2022-EVENING Q134
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-cooperatives-and-cooperative-banks-64438c62',
   'Cooperatives and cooperative banks'),   -- 6q: P1-ESI-2022-EVENING Q136, P1-ESI-2023 Q20, P2-ARD-2023 Q1, P2-ARD-2023 Q2, P2-ARD-2023 Q3, P2-ARD-2023 Q4
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-microfinance-sector-and-its-regulation-28890afb',
   'Microfinance sector and its regulation'),   -- 3q: P1-ESI-2021 Q129, P1-ESI-2022-EVENING Q146, P1-ESI-2023 Q10
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-mudra-and-micro-enterprise-credit-46158941',
   'MUDRA and micro-enterprise credit'),   -- 1q: P2-ESI-2021 Q2
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-credit-schemes-for-sc-st-and-women-entrepreneurs-16e66d55',
   'Credit schemes for SC, ST and women entrepreneurs'),   -- 2q: P1-ESI-2023 Q34, P1-ESI-2023 Q35
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-financial-inclusion-and-jan-dhan-71aa2972',
   'Financial inclusion and Jan Dhan'),   -- 2q: P1-ESI-2022-EVENING Q159, P1-ESI-2023 Q31
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-public-sector-bank-reforms-3d69d7d1',
   'Public sector bank reforms'),   -- 5q: P1-ESI-2021 Q124, P1-ESI-2021 Q152, P2-ESI-2020 Q52, P2-ESI-2020 Q53, P2-ESI-2020 Q54
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-financial-stability-assessment-and-reporting-4c5c423c',
   'Financial stability assessment and reporting'),   -- 2q: P1-ESI-2020 Q143, P1-ESI-2021 Q123
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-capital-market-instruments-and-regulation-80c7bce4',
   'Capital market instruments and regulation'),   -- 2q: P1-ESI-2021 Q125, P1-ESI-2022-EVENING Q148
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-sovereign-and-infrastructure-funds-e9546148',
   'Sovereign and infrastructure funds'),   -- 1q: P1-ESI-2020 Q144
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-rbi-committees-and-working-groups-c7e79711',
   'RBI committees and working groups'),   -- 1q: P1-ESI-2020 Q145
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-banking-regulation-and-legislation-ecffbc16',
   'Banking regulation and legislation'),   -- 3q: P2-ESI-2021 Q7, P2-ESI-2021 Q8, P2-ESI-2021 Q9
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-bank-fraud-prevention-and-early-warning-6579cda4',
   'Bank fraud prevention and early warning'),   -- 2q: P2-ESI-2020 Q61, P2-ESI-2020 Q62
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-housing-finance-and-house-price-indices-56a4f7bc',
   'Housing finance and house price indices'),   -- 1q: P2-ESI-2020 Q63
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-lead-bank-scheme-and-district-credit-planning-595fb697',
   'Lead Bank Scheme and district credit planning'),   -- 1q: P2-ESI-2020 Q44
  ('esi-banking-credit-and-financial-inclusion-0390a155', 'esi-digital-finance-and-technology-in-banking-a1a8e123',
   'Digital finance and technology in banking'),   -- 1q: P1-ESI-2023 Q22

  -- Population, Employment and Social Indicators
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-census-and-demographic-profile-of-india-f0423777',
   'Census and demographic profile of India'),   -- 7q: P1-ESI-2022-MORNING Q133, P1-ESI-2022-MORNING Q147, P1-ESI-2022-MORNING Q148, P1-ESI-2022-EVENING Q135, P1-ESI-2022-EVENING Q156, P1-ESI-2023 Q12 ...
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-socio-economic-and-caste-surveys-9770ae49',
   'Socio-economic and caste surveys'),   -- 1q: P1-ESI-2022-EVENING Q125
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-population-projections-d1e88ca6',
   'Population projections'),   -- 1q: P1-ESI-2023 Q27
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-population-theories-and-demographic-transition-a323bbe5',
   'Population theories and demographic transition'),   -- 1q: P2-ARD-2020 Q26
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-poverty-measurement-and-multidimensional-poverty-fccf8721',
   'Poverty measurement and multidimensional poverty'),   -- 2q: P1-ESI-2022-MORNING Q158, P2-ARD-2020 Q29
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-employment-statistics-and-employment-services-be746d7a',
   'Employment statistics and employment services'),   -- 2q: P1-ESI-2022-MORNING Q156, P1-ESI-2022-MORNING Q159
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-labour-laws-wages-and-maternity-benefit-4e442e0b',
   'Labour laws, wages and maternity benefit'),   -- 2q: P1-ESI-2021 Q150, P1-ESI-2022-MORNING Q123
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-skill-development-and-apprenticeship-b69d40f8',
   'Skill development and apprenticeship'),   -- 6q: P1-ESI-2022-EVENING Q130, P1-ESI-2023 Q25, P2-ESI-2020 Q48, P2-ESI-2020 Q49, P2-ESI-2020 Q50, P2-ESI-2020 Q51
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-gender-statistics-and-indicators-0e67ccaa',
   'Gender statistics and indicators'),   -- 1q: P1-ESI-2023 Q16
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-tribal-welfare-and-particularly-vulnerable-tribal-groups-8f5bf9f7',
   'Tribal welfare and particularly vulnerable tribal groups'),   -- 1q: P1-ESI-2022-EVENING Q160
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-social-legislation-on-women-children-and-the-elderly-320dd084',
   'Social legislation on women, children and the elderly'),   -- 2q: P1-ESI-2021 Q146, P1-ESI-2022-MORNING Q131
  ('esi-population-employment-and-social-indicators-a46a7270', 'esi-social-movements-and-civil-society-42bade55',
   'Social movements and civil society'),   -- 1q: P1-ESI-2021 Q156

  -- Constitution, Governance and Institutions
  ('esi-constitution-governance-and-institutions-06bc814b', 'esi-fundamental-rights-articles-a7516de6',
   'Fundamental Rights articles'),   -- 2q: P1-ESI-2021 Q157, P1-ESI-2022-MORNING Q126
  ('esi-constitution-governance-and-institutions-06bc814b', 'esi-directive-principles-of-state-policy-7688b1a7',
   'Directive Principles of State Policy'),   -- 3q: P1-ESI-2022-MORNING Q127, P1-ESI-2022-MORNING Q152, P1-ESI-2022-EVENING Q123
  ('esi-constitution-governance-and-institutions-06bc814b', 'esi-constitutional-amendments-and-reservation-aed5ab8e',
   'Constitutional amendments and reservation'),   -- 1q: P1-ESI-2020 Q133
  ('esi-constitution-governance-and-institutions-06bc814b', 'esi-schedules-of-the-constitution-0e22c1f9',
   'Schedules of the Constitution'),   -- 1q: P1-ESI-2021 Q158
  ('esi-constitution-governance-and-institutions-06bc814b', 'esi-finance-commission-and-fiscal-federalism-b65583a6',
   'Finance Commission and fiscal federalism'),   -- 2q: P1-ESI-2021 Q138, P1-ESI-2021 Q140
  ('esi-constitution-governance-and-institutions-06bc814b', 'esi-parliamentary-committees-and-oversight-99a84f1f',
   'Parliamentary committees and oversight'),   -- 1q: P1-ESI-2021 Q154
  ('esi-constitution-governance-and-institutions-06bc814b', 'esi-right-to-information-c8f2300e',
   'Right to Information'),   -- 1q: P1-ESI-2023 Q3
  ('esi-constitution-governance-and-institutions-06bc814b', 'esi-consumer-protection-and-regulatory-law-e0bf0181',
   'Consumer protection and regulatory law'),   -- 1q: P1-ESI-2022-EVENING Q141
  ('esi-constitution-governance-and-institutions-06bc814b', 'esi-ministries-and-organisation-of-government-7ea52ef4',
   'Ministries and organisation of government'),   -- 2q: P1-ESI-2022-EVENING Q151, P2-ESI-2021 Q3

  -- International Institutions, Indices and Reports
  ('esi-international-institutions-indices-and-reports-66941411', 'esi-global-indices-and-india-s-rank-c4195427',
   'Global indices and India''s rank'),   -- 5q: P1-ESI-2020 Q125, P1-ESI-2020 Q146, P1-ESI-2022-MORNING Q121, P1-ESI-2022-MORNING Q128, P1-ESI-2022-MORNING Q129
  ('esi-international-institutions-indices-and-reports-66941411', 'esi-growth-forecasts-by-international-agencies-f9efa8b2',
   'Growth forecasts by international agencies'),   -- 3q: P1-ESI-2020 Q148, P1-ESI-2020 Q156, P1-ESI-2020 Q157
  ('esi-international-institutions-indices-and-reports-66941411', 'esi-global-risk-and-outlook-reports-4882c2f5',
   'Global risk and outlook reports'),   -- 1q: P1-ESI-2020 Q132
  ('esi-international-institutions-indices-and-reports-66941411', 'esi-international-economic-forums-and-summit-declarations-4cfa2293',
   'International economic forums and summit declarations'),   -- 2q: P1-ESI-2020 Q155, P1-ESI-2023 Q19
  ('esi-international-institutions-indices-and-reports-66941411', 'esi-united-nations-agencies-and-campaigns-3b306d64',
   'United Nations agencies and campaigns'),   -- 2q: P1-ESI-2021 Q126, P1-ESI-2021 Q155
  ('esi-international-institutions-indices-and-reports-66941411', 'esi-multilateral-development-banks-and-the-imf-76ca8ef5',
   'Multilateral development banks and the IMF'),   -- 2q: P1-ESI-2021 Q147, P2-ARD-2020 Q24
  ('esi-international-institutions-indices-and-reports-66941411', 'esi-wto-and-global-trade-bodies-8a33bd0d',
   'WTO and global trade bodies'),   -- 1q: P2-ARD-2020 Q25
  ('esi-international-institutions-indices-and-reports-66941411', 'esi-international-groupings-and-their-membership-7b399f83',
   'International groupings and their membership'),   -- 2q: P1-ESI-2021 Q148, P1-ESI-2021 Q149

  -- Agricultural Economy and Food Policy
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-agricultural-trade-and-export-policy-b0c137b5',
   'Agricultural trade and export policy'),   -- 1q: P1-ESI-2020 Q121
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-sustainable-agriculture-missions-75203ccb',
   'Sustainable agriculture missions'),   -- 1q: P1-ESI-2020 Q122
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-irrigation-water-resources-and-river-linking-1923c369',
   'Irrigation, water resources and river linking'),   -- 3q: P1-ESI-2020 Q124, P1-ESI-2021 Q127, P1-ESI-2022-MORNING Q155
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-food-processing-and-value-chain-schemes-62dad586',
   'Food processing and value-chain schemes'),   -- 2q: P1-ESI-2020 Q129, P1-ESI-2020 Q150
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-agricultural-marketing-reform-and-indices-387d7e72',
   'Agricultural marketing reform and indices'),   -- 3q: P1-ESI-2020 Q135, P1-ESI-2020 Q136, P1-ESI-2023 Q26
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-farming-systems-and-operational-land-holdings-dc30542d',
   'Farming systems and operational land holdings'),   -- 1q: P1-ESI-2020 Q137
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-crop-production-estimates-and-agricultural-statistics-cde429a8',
   'Crop production estimates and agricultural statistics'),   -- 3q: P1-ESI-2020 Q138, P1-ESI-2022-MORNING Q153, P1-ESI-2023 Q18
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-agriculture-s-share-in-income-and-employment-dd773776',
   'Agriculture''s share in income and employment'),   -- 1q: P1-ESI-2022-MORNING Q132
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-minimum-support-price-and-procurement-08bf1b90',
   'Minimum Support Price and procurement'),   -- 1q: P1-ESI-2022-MORNING Q140
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-direct-income-support-to-farmers-d6af2ca5',
   'Direct income support to farmers'),   -- 1q: P1-ESI-2023 Q2
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-e-nam-and-electronic-agricultural-markets-5a469ac2',
   'e-NAM and electronic agricultural markets'),   -- 3q: P1-ESI-2023 Q29, P2-ESI-2020 Q55, P2-ESI-2022 Q1
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-solar-and-renewable-energy-schemes-in-agriculture-29cb0ba0',
   'Solar and renewable energy schemes in agriculture'),   -- 1q: P1-ESI-2021 Q130
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-agriculture-infrastructure-financing-4d9c7437',
   'Agriculture infrastructure financing'),   -- 1q: P1-ESI-2021 Q136
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-foreign-investment-in-agriculture-4e63b2f8',
   'Foreign investment in agriculture'),   -- 1q: P1-ESI-2022-EVENING Q137
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-watershed-development-10ea5c65',
   'Watershed development'),   -- 1q: P1-ESI-2022-MORNING Q157
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-regulated-and-licensed-crop-cultivation-4f48f1aa',
   'Regulated and licensed crop cultivation'),   -- 1q: P1-ESI-2022-MORNING Q138
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-biofuel-and-bioenergy-programmes-2179315b',
   'Biofuel and bioenergy programmes'),   -- 1q: P1-ESI-2023 Q14
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-doubling-farmers-income-and-its-committees-2c3e3962',
   'Doubling farmers'' income and its committees'),   -- 1q: P2-ESI-2020 Q39
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-crop-insurance-schemes-96129bd7',
   'Crop insurance schemes'),   -- 1q: P2-ESI-2020 Q41
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-livestock-and-dairy-development-programmes-2c0b8e57',
   'Livestock and dairy development programmes'),   -- 2q: P2-ESI-2020 Q43, P2-ESI-2020 Q64
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-climate-change-initiatives-in-agriculture-3b7a236e',
   'Climate change initiatives in agriculture'),   -- 1q: P2-ESI-2020 Q45
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-contract-farming-and-market-reform-c75445a9',
   'Contract farming and market reform'),   -- 1q: P2-ESI-2020 Q66
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-agricultural-revolutions-f75a3ef4',
   'Agricultural revolutions'),   -- 1q: P2-ESI-2020 Q57
  ('esi-agricultural-economy-and-food-policy-f212195c', 'esi-organic-and-natural-farming-schemes-739ab5db',
   'Organic and natural farming schemes'),   -- 3q: P2-ESI-2022 Q8, P2-ESI-2022 Q9, P2-ESI-2022 Q10

  -- ===== Agriculture & Rural Development =====

  -- Agronomy and Crop Production
  ('ard-agronomy-and-crop-production-3598b738', 'ard-crop-production-statistics-and-leading-states-76bd8597',
   'Crop production statistics and leading states'),   -- 6q: P1-ARD-2020 Q161, P1-ARD-2020 Q162, P1-ARD-2020 Q164, P1-ARD-2020 Q170, P1-ARD-2020 Q192, P1-ARD-2022-EVENING Q196
  ('ard-agronomy-and-crop-production-3598b738', 'ard-field-crops-characteristics-and-composition-0ee2fe15',
   'Field crops: characteristics and composition'),   -- 1q: P1-ARD-2023 Q20
  ('ard-agronomy-and-crop-production-3598b738', 'ard-commercial-and-fibre-crops-fc1cb796',
   'Commercial and fibre crops'),   -- 1q: P1-ARD-2020 Q171
  ('ard-agronomy-and-crop-production-3598b738', 'ard-millets-and-coarse-cereals-5817dc22',
   'Millets and coarse cereals'),   -- 2q: P1-ARD-2020 Q183, P2-ARD-2023 Q8
  ('ard-agronomy-and-crop-production-3598b738', 'ard-crop-physiology-and-productivity-ec35b2e2',
   'Crop physiology and productivity'),   -- 2q: P1-ARD-2020 Q189, P1-ARD-2022-MORNING Q189
  ('ard-agronomy-and-crop-production-3598b738', 'ard-plant-morphology-and-reproduction-11c20a19',
   'Plant morphology and reproduction'),   -- 2q: P1-ARD-2022-MORNING Q171, P1-ARD-2022-EVENING Q188
  ('ard-agronomy-and-crop-production-3598b738', 'ard-cropping-systems-and-cropping-patterns-97da95cc',
   'Cropping systems and cropping patterns'),   -- 9q: P1-ARD-2021 Q182, P1-ARD-2022-EVENING Q184, P1-ARD-2023 Q22, P2-ARD-2020 Q20, P2-ARD-2020 Q21, P2-ARD-2020 Q22 ...
  ('ard-agronomy-and-crop-production-3598b738', 'ard-agro-climatic-zones-and-crop-regions-b02b28dd',
   'Agro-climatic zones and crop regions'),   -- 1q: P1-ARD-2021 Q188
  ('ard-agronomy-and-crop-production-3598b738', 'ard-rainfed-and-dryland-farming-774ca52a',
   'Rainfed and dryland farming'),   -- 1q: P1-ARD-2023 Q19
  ('ard-agronomy-and-crop-production-3598b738', 'ard-organic-and-natural-farming-dd64ed70',
   'Organic and natural farming'),   -- 6q: P1-ARD-2022-MORNING Q166, P2-ARD-2020 Q1, P2-ARD-2021 Q4, P2-ARD-2021 Q5, P2-ARD-2021 Q6, P2-ARD-2021 Q7
  ('ard-agronomy-and-crop-production-3598b738', 'ard-climate-smart-and-sustainable-agriculture-3132752a',
   'Climate-smart and sustainable agriculture'),   -- 2q: P1-ARD-2022-MORNING Q183, P1-ARD-2022-MORNING Q184
  ('ard-agronomy-and-crop-production-3598b738', 'ard-seed-production-classes-and-certification-3edec708',
   'Seed production, classes and certification'),   -- 3q: P1-ARD-2021 Q198, P1-ARD-2022-EVENING Q193, P1-ARD-2023 Q16
  ('ard-agronomy-and-crop-production-3598b738', 'ard-crop-residue-and-by-products-e8e6ca95',
   'Crop residue and by-products'),   -- 1q: P1-ARD-2021 Q200

  -- Soil Science, Water and Agro-meteorology
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-soil-types-and-their-distribution-in-india-f1275c3b',
   'Soil types and their distribution in India'),   -- 4q: P1-ARD-2020 Q166, P1-ARD-2020 Q193, P1-ARD-2021 Q178, P2-ARD-2020 Q12
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-soil-classification-systems-and-soil-orders-6d6328e0',
   'Soil classification systems and soil orders'),   -- 4q: P2-ARD-2020 Q11, P2-ARD-2020 Q13, P2-ARD-2021 Q13, P2-ARD-2022 Q11
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-soil-physical-properties-and-soil-moisture-6599130c',
   'Soil physical properties and soil moisture'),   -- 6q: P1-ARD-2020 Q167, P1-ARD-2022-MORNING Q179, P1-ARD-2022-EVENING Q173, P1-ARD-2022-EVENING Q178, P1-ARD-2023 Q6, P2-ARD-2020 Q14
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-soil-chemical-properties-and-salinity-003f2da2',
   'Soil chemical properties and salinity'),   -- 4q: P1-ARD-2023 Q17, P2-ARD-2023 Q18, P2-ARD-2023 Q19, P2-ARD-2023 Q20
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-rocks-minerals-and-soil-formation-efcf3281',
   'Rocks, minerals and soil formation'),   -- 2q: P1-ARD-2023 Q23, P1-ARD-2023 Q29
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-manures-fertilizers-and-biofertilizers-baa7d9d5',
   'Manures, fertilizers and biofertilizers'),   -- 6q: P1-ARD-2021 Q170, P1-ARD-2021 Q194, P1-ARD-2022-MORNING Q176, P1-ARD-2023 Q7, P2-ARD-2022 Q10, P2-ARD-2023 Q21
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-plant-nutrients-their-functions-and-deficiency-symptoms-55b74392',
   'Plant nutrients, their functions and deficiency symptoms'),   -- 3q: P1-ARD-2020 Q199, P1-ARD-2022-MORNING Q170, P1-ARD-2022-MORNING Q185
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-soil-conservation-and-erosion-control-b50e6128',
   'Soil conservation and erosion control'),   -- 6q: P1-ARD-2020 Q185, P1-ARD-2020 Q190, P1-ARD-2022-MORNING Q177, P1-ARD-2022-EVENING Q183, P1-ARD-2023 Q2, P2-ARD-2021 Q9
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-soil-moisture-conservation-practices-bbf02983',
   'Soil moisture conservation practices'),   -- 2q: P1-ARD-2021 Q177, P1-ARD-2023 Q39
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-soil-health-management-and-testing-a8f440e2',
   'Soil health management and testing'),   -- 2q: P1-ARD-2020 Q177, P1-ARD-2022-MORNING Q197
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-irrigation-methods-d3bd948d',
   'Irrigation methods'),   -- 3q: P1-ARD-2021 Q184, P1-ARD-2022-EVENING Q176, P1-ARD-2023 Q40
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-irrigation-projects-and-command-area-classification-657dc57b',
   'Irrigation projects and command area classification'),   -- 4q: P1-ARD-2020 Q165, P1-ARD-2020 Q195, P1-ARD-2021 Q167, P1-ARD-2023 Q9
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-irrigation-coverage-and-statistics-e7ab50cf',
   'Irrigation coverage and statistics'),   -- 2q: P2-ARD-2020 Q15, P2-ARD-2020 Q16
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-irrigation-and-groundwater-schemes-8c00e4e2',
   'Irrigation and groundwater schemes'),   -- 2q: P1-ARD-2021 Q179, P2-ARD-2021 Q11
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-watershed-management-f736bee0',
   'Watershed management'),   -- 1q: P1-ARD-2022-MORNING Q196
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-agro-meteorology-rainfall-and-instruments-1970b919',
   'Agro-meteorology, rainfall and instruments'),   -- 3q: P1-ARD-2020 Q182, P1-ARD-2021 Q180, P1-ARD-2023 Q3
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-climate-change-and-emission-reports-e3123cf2',
   'Climate change and emission reports'),   -- 3q: P1-ARD-2021 Q181, P1-ARD-2021 Q196, P1-ARD-2023 Q36
  ('ard-soil-science-water-and-agro-meteorology-d2814b31', 'ard-irrigation-engineering-and-lift-irrigation-c3515ee1',
   'Irrigation engineering and lift irrigation'),   -- 1q: P1-ARD-2022-EVENING Q195

  -- Horticulture and Plantation Crops
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-horticulture-production-statistics-4130b769',
   'Horticulture production statistics'),   -- 3q: P1-ARD-2020 Q163, P2-ARD-2021 Q1, P2-ARD-2021 Q3
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-branches-of-horticulture-f05380c6',
   'Branches of horticulture'),   -- 2q: P1-ARD-2021 Q191, P1-ARD-2022-EVENING Q167
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-scientific-names-of-horticultural-crops-9e83e592',
   'Scientific names of horticultural crops'),   -- 3q: P1-ARD-2022-EVENING Q161, P1-ARD-2023 Q1, P2-ARD-2022 Q9
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-plant-propagation-methods-51e57982',
   'Plant propagation methods'),   -- 4q: P1-ARD-2020 Q186, P1-ARD-2022-MORNING Q182, P1-ARD-2022-EVENING Q168, P1-ARD-2022-EVENING Q187
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-tissue-culture-and-nursery-techniques-e76e2be1',
   'Tissue culture and nursery techniques'),   -- 1q: P2-ARD-2021 Q8
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-orchard-planting-systems-764aa89e',
   'Orchard planting systems'),   -- 1q: P1-ARD-2021 Q192
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-training-and-pruning-003a99a3',
   'Training and pruning'),   -- 1q: P1-ARD-2023 Q24
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-plantation-crop-management-6adb2d38',
   'Plantation crop management'),   -- 1q: P1-ARD-2020 Q187
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-floriculture-and-flower-export-0064cb7d',
   'Floriculture and flower export'),   -- 2q: P1-ARD-2021 Q197, P1-ARD-2022-MORNING Q188
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-aromatic-and-medicinal-plants-0b96b116',
   'Aromatic and medicinal plants'),   -- 2q: P1-ARD-2022-MORNING Q178, P1-ARD-2022-MORNING Q180
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-post-harvest-physiology-maturity-and-ripening-b99c260f',
   'Post-harvest physiology, maturity and ripening'),   -- 3q: P1-ARD-2022-MORNING Q168, P2-ARD-2020 Q18, P2-ARD-2020 Q19
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-mushroom-cultivation-cc6618ae',
   'Mushroom cultivation'),   -- 1q: P2-ARD-2020 Q2
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-horticulture-information-systems-2cd5dc9f',
   'Horticulture information systems'),   -- 1q: P2-ARD-2021 Q2
  ('ard-horticulture-and-plantation-crops-b308828f', 'ard-horticulture-development-programmes-afcb6fe0',
   'Horticulture development programmes'),   -- 1q: P2-ARD-2023 Q29

  -- Plant Protection and Crop Health
  ('ard-plant-protection-and-crop-health-c4aa551d', 'ard-crop-diseases-and-their-causal-agents-b59ad874',
   'Crop diseases and their causal agents'),   -- 5q: P1-ARD-2020 Q200, P1-ARD-2022-MORNING Q181, P1-ARD-2022-MORNING Q187, P1-ARD-2022-EVENING Q174, P1-ARD-2022-EVENING Q179
  ('ard-plant-protection-and-crop-health-c4aa551d', 'ard-crop-pests-and-their-management-206db1af',
   'Crop pests and their management'),   -- 1q: P1-ARD-2022-MORNING Q193

  -- Animal Husbandry, Dairy and Poultry
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-cattle-breeds-c6fbb93e',
   'Cattle breeds'),   -- 3q: P1-ARD-2023 Q13, P2-ARD-2020 Q9, P2-ARD-2023 Q22
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-sheep-and-goat-breeds-8d8a2774',
   'Sheep and goat breeds'),   -- 1q: P2-ARD-2020 Q10
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-poultry-breeds-97ff7bd1',
   'Poultry breeds'),   -- 1q: P1-ARD-2022-MORNING Q167
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-poultry-production-and-management-23203b34',
   'Poultry production and management'),   -- 7q: P1-ARD-2020 Q172, P1-ARD-2021 Q174, P1-ARD-2022-EVENING Q177, P1-ARD-2022-EVENING Q180, P1-ARD-2023 Q14, P1-ARD-2023 Q15 ...
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-poultry-housing-systems-b35c4156',
   'Poultry housing systems'),   -- 3q: P2-ARD-2022 Q4, P2-ARD-2022 Q5, P2-ARD-2022 Q6
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-livestock-reproduction-and-gestation-af5125a2',
   'Livestock reproduction and gestation'),   -- 5q: P1-ARD-2022-MORNING Q164, P1-ARD-2022-EVENING Q164, P2-ARD-2022 Q1, P2-ARD-2022 Q2, P2-ARD-2022 Q3
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-dairy-physiology-and-milk-production-67b5201e',
   'Dairy physiology and milk production'),   -- 3q: P1-ARD-2022-MORNING Q169, P1-ARD-2022-EVENING Q169, P2-ARD-2020 Q4
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-animal-breeding-methods-4fd2ac1c',
   'Animal breeding methods'),   -- 2q: P1-ARD-2022-EVENING Q181, P1-ARD-2022-EVENING Q182
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-livestock-terminology-and-management-practices-8ac22bac',
   'Livestock terminology and management practices'),   -- 6q: P1-ARD-2021 Q183, P1-ARD-2021 Q189, P1-ARD-2022-MORNING Q190, P1-ARD-2022-EVENING Q162, P1-ARD-2023 Q10, P1-ARD-2023 Q21
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-livestock-and-poultry-diseases-53ef1f4f',
   'Livestock and poultry diseases'),   -- 1q: P1-ARD-2020 Q198
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-fodder-crops-and-grasses-c1dff30e',
   'Fodder crops and grasses'),   -- 1q: P1-ARD-2020 Q191
  ('ard-animal-husbandry-dairy-and-poultry-833df929', 'ard-livestock-sector-contribution-and-statistics-e5b03188',
   'Livestock sector contribution and statistics'),   -- 2q: P1-ARD-2021 Q190, P1-ARD-2022-EVENING Q175

  -- Fisheries and Aquaculture
  ('ard-fisheries-and-aquaculture-f734ed79', 'ard-fish-species-breeds-and-migration-d80fedd9',
   'Fish species, breeds and migration'),   -- 5q: P1-ARD-2020 Q197, P1-ARD-2021 Q162, P1-ARD-2021 Q187, P1-ARD-2022-MORNING Q200, P1-ARD-2022-EVENING Q171
  ('ard-fisheries-and-aquaculture-f734ed79', 'ard-aquaculture-systems-and-water-quality-8d07f0a7',
   'Aquaculture systems and water quality'),   -- 3q: P1-ARD-2022-MORNING Q191, P1-ARD-2023 Q8, P2-ARD-2023 Q24
  ('ard-fisheries-and-aquaculture-f734ed79', 'ard-fish-processing-and-post-harvest-handling-563597fb',
   'Fish processing and post-harvest handling'),   -- 1q: P1-ARD-2021 Q175
  ('ard-fisheries-and-aquaculture-f734ed79', 'ard-fisheries-institutions-and-marine-exports-48791a80',
   'Fisheries institutions and marine exports'),   -- 2q: P1-ARD-2022-EVENING Q170, P1-ARD-2022-EVENING Q197
  ('ard-fisheries-and-aquaculture-f734ed79', 'ard-fisheries-schemes-and-sector-development-9a439d6d',
   'Fisheries schemes and sector development'),   -- 1q: P1-ARD-2022-EVENING Q186

  -- Forestry and Agroforestry
  ('ard-forestry-and-agroforestry-17f6abac', 'ard-agroforestry-systems-ef1aa2d0',
   'Agroforestry systems'),   -- 4q: P1-ARD-2021 Q169, P1-ARD-2022-MORNING Q192, P1-ARD-2022-EVENING Q172, P2-ARD-2020 Q6
  ('ard-forestry-and-agroforestry-17f6abac', 'ard-types-of-forestry-and-social-forestry-d739d142',
   'Types of forestry and social forestry'),   -- 1q: P2-ARD-2021 Q10
  ('ard-forestry-and-agroforestry-17f6abac', 'ard-forest-management-and-community-forestry-39e845dd',
   'Forest management and community forestry'),   -- 2q: P1-ARD-2022-MORNING Q194, P2-ARD-2020 Q7
  ('ard-forestry-and-agroforestry-17f6abac', 'ard-forest-cover-and-forest-policy-df1fa06d',
   'Forest cover and forest policy'),   -- 1q: P1-ARD-2021 Q163
  ('ard-forestry-and-agroforestry-17f6abac', 'ard-forest-tree-species-and-taxonomy-4809d8c6',
   'Forest tree species and taxonomy'),   -- 2q: P1-ARD-2022-MORNING Q186, P1-ARD-2023 Q18
  ('ard-forestry-and-agroforestry-17f6abac', 'ard-forest-regeneration-and-nursery-practice-9a601f5b',
   'Forest regeneration and nursery practice'),   -- 1q: P1-ARD-2023 Q26

  -- Agricultural Economics, Credit and Marketing
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-production-economics-and-factors-of-production-fffc9645',
   'Production economics and factors of production'),   -- 2q: P1-ARD-2022-MORNING Q161, P2-ARD-2020 Q30
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-farm-management-and-cost-accounting-315421ce',
   'Farm management and cost accounting'),   -- 2q: P1-ARD-2022-MORNING Q175, P1-ARD-2023 Q11
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-operational-land-holdings-and-farm-size-classification-b394fb0e',
   'Operational land holdings and farm size classification'),   -- 2q: P1-ARD-2021 Q166, P2-ARD-2020 Q8
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-minimum-support-price-and-procurement-08bf1b90',
   'Minimum Support Price and procurement'),   -- 5q: P1-ARD-2020 Q174, P1-ARD-2022-MORNING Q162, P1-ARD-2022-EVENING Q189, P1-ARD-2022-EVENING Q190, P1-ARD-2023 Q4
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-kisan-credit-card-and-agricultural-credit-targets-1b663009',
   'Kisan Credit Card and agricultural credit targets'),   -- 4q: P1-ARD-2020 Q180, P1-ARD-2021 Q161, P1-ARD-2023 Q38, P2-ARD-2020 Q28
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-priority-sector-lending-and-ridf-f05ce94f',
   'Priority sector lending and RIDF'),   -- 3q: P1-ARD-2020 Q184, P1-ARD-2021 Q165, P1-ARD-2023 Q27
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-nabard-and-rural-finance-institutions-2bee848c',
   'NABARD and rural finance institutions'),   -- 1q: P2-ARD-2022 Q13
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-crop-insurance-and-yield-thresholds-f90cc0f1',
   'Crop insurance and yield thresholds'),   -- 1q: P1-ARD-2023 Q28
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-e-nam-and-agricultural-marketing-platforms-3c1c5ff6',
   'e-NAM and agricultural marketing platforms'),   -- 5q: P1-ARD-2021 Q176, P1-ARD-2022-MORNING Q172, P1-ARD-2023 Q37, P2-ARD-2022 Q14, P2-ARD-2022 Q15
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-farmer-producer-organisations-8f479c20',
   'Farmer Producer Organisations'),   -- 1q: P1-ARD-2021 Q168
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-value-chain-and-price-stabilisation-initiatives-038079c6',
   'Value-chain and price stabilisation initiatives'),   -- 2q: P1-ARD-2021 Q164, P1-ARD-2021 Q199
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-agriculture-s-contribution-to-gross-value-added-22099611',
   'Agriculture''s contribution to gross value added'),   -- 3q: P1-ARD-2022-MORNING Q174, P1-ARD-2022-MORNING Q195, P2-ARD-2022 Q7
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-union-budget-and-agriculture-allocations-168cd03f',
   'Union Budget and agriculture allocations'),   -- 1q: P1-ARD-2020 Q194
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-doubling-farmers-income-f022e57a',
   'Doubling farmers'' income'),   -- 1q: P1-ARD-2020 Q196
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-agricultural-revolutions-f75a3ef4',
   'Agricultural revolutions'),   -- 1q: P2-ARD-2020 Q3
  ('ard-agricultural-economics-credit-and-marketing-fb0da521', 'ard-agricultural-events-and-industry-associations-5540f0f2',
   'Agricultural events and industry associations'),   -- 2q: P1-ARD-2020 Q169, P1-ARD-2020 Q176

  -- Rural Development, Schemes and Institutions
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-mgnrega-e34273e0',
   'MGNREGA'),   -- 4q: P1-ARD-2020 Q179, P1-ARD-2021 Q186, P1-ARD-2022-MORNING Q163, P1-ARD-2023 Q32
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-self-help-groups-and-day-nrlm-e87b9d68',
   'Self-help groups and DAY-NRLM'),   -- 3q: P1-ARD-2021 Q195, P1-ARD-2022-EVENING Q200, P1-ARD-2023 Q33
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-rural-roads-and-pmgsy-2cb50665',
   'Rural roads and PMGSY'),   -- 3q: P1-ARD-2020 Q168, P1-ARD-2020 Q175, P1-ARD-2022-EVENING Q199
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-rural-housing-pmay-g-d529747c',
   'Rural housing (PMAY-G)'),   -- 1q: P1-ARD-2022-EVENING Q192
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-sanitation-and-drinking-water-missions-1e7dd5d7',
   'Sanitation and drinking water missions'),   -- 3q: P1-ARD-2021 Q185, P1-ARD-2023 Q34, P1-ARD-2023 Q35
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-food-security-and-the-public-distribution-system-da810701',
   'Food security and the public distribution system'),   -- 3q: P1-ARD-2021 Q173, P1-ARD-2023 Q31, P2-ARD-2021 Q12
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-direct-income-support-to-farmers-d6af2ca5',
   'Direct income support to farmers'),   -- 2q: P1-ARD-2020 Q173, P1-ARD-2022-EVENING Q163
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-farmer-welfare-schemes-and-grievance-portals-987321f6',
   'Farmer welfare schemes and grievance portals'),   -- 1q: P1-ARD-2022-MORNING Q199
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-solar-energy-schemes-in-agriculture-db3c8676',
   'Solar energy schemes in agriculture'),   -- 1q: P1-ARD-2021 Q193
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-rural-waste-management-and-bioenergy-10b2ffaf',
   'Rural waste management and bioenergy'),   -- 1q: P1-ARD-2020 Q181
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-panchayati-raj-and-rural-governance-18cc1263',
   'Panchayati Raj and rural governance'),   -- 1q: P1-ARD-2020 Q178
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-rural-employment-and-training-programmes-45432315',
   'Rural employment and training programmes'),   -- 1q: P1-ARD-2022-EVENING Q165
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-rural-artisan-and-handloom-sector-91744e34',
   'Rural artisan and handloom sector'),   -- 1q: P1-ARD-2021 Q171
  ('ard-rural-development-schemes-and-institutions-182b97a8', 'ard-rural-demography-and-census-5176c982',
   'Rural demography and census'),   -- 2q: P1-ARD-2022-MORNING Q173, P1-ARD-2022-EVENING Q198

  -- Agricultural Engineering, Mechanisation and Extension
  ('ard-agricultural-engineering-mechanisation-and-extension-843d09ce', 'ard-farm-implements-and-mechanisation-635cd7ec',
   'Farm implements and mechanisation'),   -- 4q: P1-ARD-2020 Q188, P1-ARD-2021 Q172, P2-ARD-2020 Q5, P2-ARD-2022 Q12
  ('ard-agricultural-engineering-mechanisation-and-extension-843d09ce', 'ard-tillage-systems-and-practices-14643597',
   'Tillage systems and practices'),   -- 4q: P2-ARD-2021 Q15, P2-ARD-2023 Q5, P2-ARD-2023 Q6, P2-ARD-2023 Q7
  ('ard-agricultural-engineering-mechanisation-and-extension-843d09ce', 'ard-farm-power-and-rural-electrification-27dbf73c',
   'Farm power and rural electrification'),   -- 1q: P1-ARD-2023 Q25
  ('ard-agricultural-engineering-mechanisation-and-extension-843d09ce', 'ard-precision-agriculture-and-digital-tools-67493941',
   'Precision agriculture and digital tools'),   -- 1q: P1-ARD-2022-EVENING Q194
  ('ard-agricultural-engineering-mechanisation-and-extension-843d09ce', 'ard-post-harvest-storage-grading-and-losses-cb1ee86d',
   'Post-harvest storage, grading and losses'),   -- 3q: P1-ARD-2023 Q5, P1-ARD-2023 Q30, P2-ARD-2020 Q17
  ('ard-agricultural-engineering-mechanisation-and-extension-843d09ce', 'ard-extension-teaching-methods-d65b9d96',
   'Extension teaching methods'),   -- 2q: P1-ARD-2022-EVENING Q185, P1-ARD-2023 Q12
  ('ard-agricultural-engineering-mechanisation-and-extension-843d09ce', 'ard-agricultural-research-and-extension-system-ef3db2e9',
   'Agricultural research and extension system'),   -- 3q: P1-ARD-2022-MORNING Q198, P1-ARD-2022-EVENING Q191, P2-ARD-2023 Q25
  ('ard-agricultural-engineering-mechanisation-and-extension-843d09ce', 'ard-agricultural-education-and-institutions-24849997',
   'Agricultural education and institutions'),   -- 1q: P1-ARD-2022-MORNING Q165
  ('ard-agricultural-engineering-mechanisation-and-extension-843d09ce', 'ard-scope-and-definition-of-agronomy-fd1e1c14',
   'Scope and definition of agronomy')   -- 1q: P1-ARD-2022-EVENING Q166
) AS v(parent_slug, slug, name)
JOIN public.topics p
  ON p.slug = v.parent_slug AND p.level = 'topic' AND p.parent_topic_id IS NULL
ON CONFLICT DO NOTHING;

COMMIT;
