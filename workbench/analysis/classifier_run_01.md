# Study-artefact classifier — run 01

Source: `workbench/analysis/classifier_input.json`. Thresholds are stated in `scripts/classify_topic_artefacts.py`.

| Subject | Macro topic | Artefact | Conf. | Key signals | Content backlog |
|---|---|---|---|---|---|
| General Studies IV (Ethics) | Applied Ethics and Case Studies | `ask_record` | high | s1 29 children, 14 never asked, 82 questions (5.47 per asked child); s3 even; fired s9, s10 | none |
| General Studies II | Union and State Executive, Legislature and Judiciary | `form_timeline` | high | s1 17 children, 4 never asked, 78 questions (6.00 per asked child); s3 even; s4 verb shift; fired s9 | none |
| General Studies I | Indian Society | `ask_record` | high | s1 23 children, 4 never asked, 66 questions (3.47 per asked child); s3 even | none |
| General Studies I | Physical Geography of India, Human Geography, and Economic Geography | `ask_record` | high | s1 26 children, 8 never asked, 63 questions (3.50 per asked child); s3 even | map |
| General Studies II | International Relations | `ask_record` | high | s1 15 children, 1 never asked, 59 questions (4.21 per asked child); s3 even; fired s6 | map |
| General Studies III | Agriculture | `ask_record` | high | s1 14 children, 1 never asked, 55 questions (4.23 per asked child); s3 even; fired s10 | none |
| General Studies III | Environment, Ecology and Bio-diversity | `frequency_chart` | medium | s1 30 children, 13 never asked, 37 questions (2.18 per asked child); s3 even; fired s5, s6 | map |
| General Studies IV (Ethics) | Human Values — Contributions of Moral Thinkers and Administrative Thinkers | `ask_record` | medium | s1 6 children, 1 never asked, 38 questions (7.60 per asked child); s3 even; fired s8 | mindmap |
| General Studies I | Indian Culture | `frequency_chart` | low | s1 30 children, 14 never asked, 25 questions (1.56 per asked child); s3 even; fired s5 | timeline |
| General Studies I | Medieval India | `roadmap` | low | s1 15 children, 12 never asked, 4 questions (1.33 per asked child); s3 clustered_recent; fired s5, s8, s9 | timeline |

## Why each call

### Applied Ethics and Case Studies — `ask_record` (high)

- R2 ask_record: 82 questions over 15 asked children = 5.47 each, at or above 2.50
- _2013_ — "You are the District Magistrate of a highly sensitive, drought-prone district that is currently…"
- _2018_ — "As a senior officer in the Ministry, you have access to important policy decisions…"
- _2023_ — "You hold a responsible position in a ministry in the government. One day in…"

### Union and State Executive, Legislature and Judiciary — `form_timeline` (high)

- R1 form_timeline: examine led 2013-2016 at 0.45 and fell to 0.00 by 2021-2025, a drop of 0.45; the ask changed by losing a verb rather than gaining one
- _2013_ — "The role of the Comptroller and Auditor General (CAG) has become increasingly critical in…"
- _2018_ — "Assess the importance of the Panchayat system in India as a part of local…"
- _2023_ — "Account for the legal and political factors responsible for the reduced frequency of using…"

### Indian Society — `ask_record` (high)

- R2 ask_record: 66 questions over 19 asked children = 3.47 each, at or above 2.50
- _2013_ — "Examine the role of the caste system as a barrier to social mobility in…"
- _2018_ — "'Globalisation is generally said to promote cultural homogenisation but due to this cultural specificities…"
- _2023_ — "Does urbanization lead to more segregation and/or marginalization of the poor in Indian metropolises?"

### Physical Geography of India, Human Geography, and Economic Geography — `ask_record` (high)

- R2 ask_record: 63 questions over 18 asked children = 3.50 each, at or above 2.50
- _2013_ — "Explain the origin and distribution of the monsoon climate in India."
- _2020_ — "India has immense potential of solar energy though there are regional variations in its…"
- _2023_ — "Why is the world today confronted with a crisis of availability of and access…"

### International Relations — `ask_record` (high)

- R2 ask_record: 59 questions over 14 asked children = 4.21 each, at or above 2.50
- _2013_ — "Discuss the relevance of the look East Policy in the context of changing geopolitical…"
- _2017_ — "What are the major challenges before the World Trade Organisation (WTO) in the context…"
- _2023_ — "'The expansion and strengthening of NATO and a stronger US-Europe strategic partnership works well…"

### Agriculture — `ask_record` (high)

- R2 ask_record: 55 questions over 13 asked children = 4.23 each, at or above 2.50
- _2013_ — "Discuss the impact of farm subsidies on the fiscal health of state budgets and…"
- _2018_ — "Examine the role of supermarkets in supply chain management of fruits, vegetables and food…"
- _2023_ — "Comment on the National Wetland Conservation Programme initiated by the Government of India and…"

### Environment, Ecology and Bio-diversity — `frequency_chart` (medium)

- R3 frequency_chart: 30 children, 17 asked, 43% never asked, only 2.18 questions per asked child
- _2021_ — "Explain the purpose of the Green Grid Initiative launched at World Leaders Summit of…"
- _2021_ — "Describe the major outcomes of the 26th session of the Conference of the Parties…"
- _2022_ — "Do you think India will meet 50 percent of its energy needs from renewable…"

### Human Values — Contributions of Moral Thinkers and Administrative Thinkers — `ask_record` (medium)

- R2 ask_record: 38 questions over 5 asked children = 7.60 each, at or above 2.50
- _2013_ — ""Seven Sins" according to Mahatma Gandhi are highly relevant to understand contemporary economic anomalies…"
- _2018_ — ""Anger and intolerance are the enemies of correct understanding." - Mahatma Gandhi"
- _2022_ — ""Judge your success by what you had to give up in order to get…"

### Indian Culture — `frequency_chart` (low)

- R3 frequency_chart: 30 children, 16 asked, 47% never asked, only 1.56 questions per asked child
- _2013_ — "Defying the barriers of age, gender and religion, the Bhakti movement opened the doors…"
- _2014_ — "Sufis and Saint movements failed to modify either the religious ideas and practices or…"
- _2018_ — "The Bhakti movement received a remarkable re-orientation with the advent of Sri Chaitanya Mahaprabhu…"

### Medieval India — `roadmap` (low)

- R0 corpus floor: 4 questions < 8; no corpus-derived type
- R4 roadmap: 15 children carry official syllabus wording; no question volume required
- _2020_ — "Pala period is the most significant phase in the history of Buddhism in India…"
- _2023_ — "What were the major technological changes introduced during the Sultanate period? How did those…"
