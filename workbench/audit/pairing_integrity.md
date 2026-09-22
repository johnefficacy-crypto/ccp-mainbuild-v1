# Pairing integrity of the apply-eligible repair rows

`apply_eligible = true` says the DB text is absent from the official paper and the UnlockIAS text is present. It says nothing about whether the two are the SAME question - the pairing came from fuzzy nearest-neighbour matching, which returns a neighbour whether or not a true counterpart exists. This pass classifies the 29 eligible rows on that question alone. Nothing is written to `repair_worklist.csv`.

## Result

| verdict | rows |
|---|---|
| apply | 5 |
| sub_part_loss | 8 |
| wrong_question | 10 |
| review | 6 |
| **total** | **29** |

**Calibration: 13 of 13 identified hand labels reproduced.**

The brief reports **14** hand-classified rows (6 sub-part loss, 5 wrong question, 3 genuine) but identifies only **13** of them by year/paper/question - the wrong-question list names four rows (2016 GS2 #69, 2016 GS2 #76, 2016 GS1 #48, 2017 GS1 #49), not five. The fifth is calibrated against nothing here. Every classifier statement below is therefore over 13 rows, and that shortfall is a gap in the calibration, not a pass.

## 1. Signal distributions across all 29 rows

| signal | distribution |
|---|---|
| length ratio | n=29  min 0.17  p25 0.65  median 0.96  p75 1.35  max 2.66 |
| content cosine (IDF-weighted) | n=29  min 0.00  p25 30.30  median 60.90  p75 76.10  max 100.00 |
| content Jaccard (unweighted) | n=29  min 0.00  p25 18.80  median 37.50  p75 55.60  max 100.00 |
| nest score (pair inside db_text) | n=29  min 58.20  p25 64.90  median 76.10  p75 87.20  max 100.00 |
| pair score (token_set_ratio) | n=29  min 41.90  p25 61.20  median 74.90  p75 87.50  max 100.00 |
| db-side enumeration markers | 0 markers: 22 rows, 1 markers: 1 rows, 2 markers: 5 rows, 3 markers: 1 rows |
| position delta (extract - db local no.) | n=24, min -19, median 3, max 14; 1 rows agree exactly; 5 rows have no extraction local number |

## 2. Where the populations separate - and where they do not

### Sub-part loss separates structurally, not statistically

All 6 labelled sub-part rows carry **>= 2** enumeration markers in `db_text` and **zero** in the pair, and the pair sits inside `db_text` at a nest score of **>= 97.3**. No other row in the batch meets that pattern: the next highest db-side marker count outside the labelled set is 1. This is a structural test, and it is exact - there is no threshold to tune.

### Length ratio separates cleanly

Labelled sub-part rows run **0.17 - 0.67**; labelled genuine rows run **0.84 - 1.16**. Nothing lands in between, so the floor is placed at the midpoint of that gap: **0.76**. The ceiling is its symmetric counterpart, **1.32** - an UnlockIAS text far LONGER than the DB text is adding material, which is the same kind of defect in the other direction and is not something the labelled set covers, so it goes to `review`, not to `apply`.

The operator's worked example - 157/396 = 0.40 - sits inside the labelled sub-part range and is classified as such by this floor.

### Plain Jaccard is too fragile to carry the decision - this is why the cosine is IDF-weighted

Content-word Jaccard was computed first, exactly as the brief proposes, in two forms. Both are reported per row in the CSV.

**As specified** - stopwords and directive verbs removed, no stemming - the populations OVERLAP and no cut reproduces the hand labels:

- labelled **wrong-question** rows reach **28.6** (2016 GS1 #48, Adivasis vs Scheduled Tribes)
- labelled **genuine** rows fall to **22.2** (2014 GS1 #10, secularism) - BELOW that ceiling

The cause is the shared UPSC template. 'Why are the tribals in India referred to as X? Indicate the major Y' matches itself word for word across two different questions, while a genuine paraphrase ('the concept of Secularism in India differs from the Western model' vs 'Indian debates on secularism differ from the debates in the West') shares almost no surface tokens - India/Indian and West/Western do not even match as strings.

**With light stemming** the ordering flips and the two populations do separate - 28.6 (wrong ceiling) against 37.5 (genuine floor) - but by only **8.9 points**. A margin that narrow on 13 labelled rows is not a boundary anyone should apply to the other 16.

Weighting each token by its IDF over the UnlockIAS corpus (566 questions) is what makes the signal robust: template words are cheap, subject words are expensive. Under the weighted cosine the same two populations sit at **38.7** (wrong-question ceiling) and **64.2** (genuine floor) - a gap of **25.5 points**, 2.9x the stemmed-Jaccard margin, with nothing in it.

### Double-encoded DB text, and what it does to the ratio

2 rows carry mojibake in `db_text` (a curly quote stored as `Ã¢â¬Å`), which inflates its length and so depresses the length ratio - a classifier input. Collapsing each mojibake run to one character gives `len_ratio_clean`:

| year | paper | db# | runs | len_ratio | len_ratio_clean | verdict |
|---|---|---|---|---|---|---|
| 2019 | GS4 | 71 | 12 | 0.388 | 0.400 | sub_part_loss |
| 2019 | GS4 | 72 | 12 | 0.503 | 0.516 | sub_part_loss |

The correction moves the ratio by at most 0.013 and changes no verdict: both rows stay well below the 0.76 floor either way. Under the clean ratio the labelled sub-part ceiling is 0.67 and the labelled genuine floor is 0.84, so the gap the floor sits in survives the correction.

### The cosine band between them is left unresolved, on purpose

Both edges come from labelled rows, so both are evidence. The interval between them is not. 6 rows land inside it, and the widest empirical gap in there is only 10.4 points (50.5 -> 60.9) - too narrow to call a boundary. 2 of those rows are resolved before the cosine is consulted, by the structural sub-part rule; the remaining 4 have no rule to catch them and are reported as `review`.

| year | paper | db# | cosine | len ratio | db_text -> pair |
|---|---|---|---|---|---|
| 2013 | GS1 | 22 | 44.7 | 0.91 | Discuss the socio-economic impacts of globalization on the elderly population in India.<br>-> Critically examine the effect of globalization on the aged population in India. |
| 2013 | GS1 | 4 | 45.3 | 1.21 | Defying the barriers of age, gender and religion, the Bhakti movement opened the doors of liberation to all. D<br>-> Defying the barriers of age, gender and religion, the Indian women became the torch-bearer during the struggle |
| 2017 | GS2 | 66 | 60.9 | 1.19 | Does the Rights of Persons with Disabilities Act, 2016 ensure mechanism for enhanced administrative capacity f<br>-> Does the Rights of Persons with Disabilities Act, 2016 ensure effective mechanism for empowerment and inclusio |
| 2017 | GS2 | 67 | 61.1 | 1.44 | Hunger and Poverty are the biggest challenges for good governance in India still today. Evaluate how far succe<br>-> Hunger and poverty are the biggest challenges for good governance in India still today. Evaluate how far succe |

### Best-alternative margin

`db_text` is scored against every UnlockIAS question of the same year and paper. A positive margin means another question of that paper matches the DB text better than its own pair does, which makes the pairing wrong by construction.

Observed positive margins: 0.3, 2.8, 6.3, 8.7.
The cut is placed in the widest gap between them, at **4.5** (gap 2.8 -> 6.3), so a margin that is only scoring noise is not read as evidence.

27 of 29 rows are their paper's best match for their own `db_text`; 2 are not.

## 3. Calibration against the hand-classified rows

| year | paper | db# | hand | classifier | result | cosine | ratio | db markers |
|---|---|---|---|---|---|---|---|---|
| 2014 | GS1 | 10 | apply | apply | match | 64.2 | 0.84 | 0 |
| 2016 | GS1 | 57 | apply | apply | match | 100.0 | 0.96 | 0 |
| 2018 | GS1 | 5 | apply | apply | match | 92.8 | 1.16 | 0 |
| 2023 | GS4 | 61 | sub_part_loss | sub_part_loss | match | 63.8 | 0.40 | 2 |
| 2023 | GS4 | 62 | sub_part_loss | sub_part_loss | match | 76.1 | 0.49 | 2 |
| 2023 | GS4 | 63 | sub_part_loss | sub_part_loss | match | 50.5 | 0.17 | 3 |
| 2023 | GS4 | 64 | sub_part_loss | sub_part_loss | match | 93.1 | 0.67 | 2 |
| 2023 | GS4 | 65 | sub_part_loss | sub_part_loss | match | 82.6 | 0.45 | 2 |
| 2023 | GS4 | 66 | sub_part_loss | sub_part_loss | match | 77.9 | 0.43 | 2 |
| 2016 | GS1 | 48 | wrong_question | wrong_question | match | 37.3 | 1.37 | 0 |
| 2016 | GS2 | 69 | wrong_question | wrong_question | match | 9.5 | 2.12 | 0 |
| 2016 | GS2 | 76 | wrong_question | wrong_question | match | 26.2 | 1.31 | 0 |
| 2017 | GS1 | 49 | wrong_question | wrong_question | match | 38.7 | 0.96 | 0 |

**13/13 reproduced.** The thresholds were derived from these rows' own extremes, so this is a consistency check, not an independent validation: it shows the rules can express the hand judgement, not that they generalise. What makes it more than circular is that the rules are ordered structural tests with one free cut each, and that the labelled populations are separated by wide empty gaps rather than by a fitted line.

## 4. Every eligible row

| year | paper | db# | verdict | cos | jac | ratio | mk | nest | pair | best alt | margin | pos delta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2013 | GS1 | 4 | **review** | 45.3 | 26.3 | 1.21 | 0 | 72.4 | 70.7 | Q3 70.7 | +0.0 | -1 |
| 2013 | GS1 | 13 | apply | 73.0 | 55.6 | 0.85 | 0 | 72.6 | 70.1 | Q13 70.1 | +0.0 | 0 |
| 2013 | GS1 | 22 | **review** | 44.7 | 33.3 | 0.91 | 0 | 76.1 | 73.9 | Q17 73.9 | +0.0 | -5 |
| 2013 | GS2 | 27 | **wrong_question** | 0.0 | 0.0 | 2.66 | 0 | 62.3 | 41.9 | Q3 50.6 | +8.7 | 5 |
| 2013 | GS2 | 46 | **wrong_question** | 11.8 | 7.1 | 1.03 | 0 | 59.7 | 59.7 | Q2 59.7 | +0.0 | -19 |
| 2013 | GS3 | 63 | **review** | 30.3 | 18.8 | 0.65 | 0 | 60.9 | 51.4 | Q25 51.7 | +0.3 | 9 |
| 2013 | GS4 | 76 | **wrong_question** | 17.0 | 15.4 | 1.21 | 0 | 58.2 | 57.4 | Q1 57.4 | -0.0 | - |
| 2013 | GS4 | 78 | **wrong_question** | 29.7 | 15.4 | 1.44 | 0 | 64.9 | 53.7 | Q4 53.7 | +0.0 | - |
| 2014 | GS1 | 10 | apply | 64.2 | 37.5 | 0.84 | 0 | 67.6 | 74.1 | Q20 74.1 | +0.0 | 10 |
| 2014 | GS2 | 21 | **review** | 65.9 | 44.0 | 1.57 | 0 | 83.6 | 75.3 | Q3 75.3 | -0.0 | 2 |
| 2014 | GS4 | 61 | apply | 74.7 | 55.6 | 0.96 | 0 | 87.0 | 87.5 | Q1 87.5 | +0.0 | - |
| 2016 | GS1 | 48 | **wrong_question** | 37.3 | 28.6 | 1.37 | 0 | 71.8 | 75.3 | Q8 75.3 | -0.0 | -2 |
| 2016 | GS1 | 57 | apply | 100.0 | 100.0 | 0.96 | 0 | 87.2 | 84.5 | Q16 84.5 | -0.0 | -3 |
| 2016 | GS2 | 59 | **wrong_question** | 30.0 | 17.2 | 2.59 | 0 | 74.6 | 66.0 | Q5 66.0 | -0.0 | 4 |
| 2016 | GS2 | 69 | **wrong_question** | 9.5 | 10.0 | 2.12 | 0 | 61.5 | 55.0 | Q8 61.3 | +6.3 | -10 |
| 2016 | GS2 | 76 | **wrong_question** | 26.2 | 16.7 | 1.31 | 0 | 59.9 | 58.8 | Q19 58.8 | +0.0 | 1 |
| 2017 | GS1 | 49 | **wrong_question** | 38.7 | 19.0 | 0.96 | 0 | 61.5 | 61.2 | Q7 61.2 | +0.0 | -3 |
| 2017 | GS2 | 61 | **wrong_question** | 38.3 | 29.4 | 1.35 | 1 | 69.0 | 63.6 | Q6 63.6 | +0.0 | 4 |
| 2017 | GS2 | 66 | **review** | 60.9 | 46.7 | 1.19 | 0 | 77.5 | 74.9 | Q12 74.9 | +0.0 | 5 |
| 2017 | GS2 | 67 | **review** | 61.1 | 52.4 | 1.44 | 0 | 87.5 | 85.8 | Q14 85.8 | +0.0 | 6 |
| 2018 | GS1 | 5 | apply | 92.8 | 85.7 | 1.16 | 0 | 83.3 | 87.8 | Q19 87.8 | -0.0 | 14 |
| 2019 | GS4 | 71 | **sub_part_loss** | 81.7 | 62.5 | 0.39 | 0 | 76.9 | 83.1 | Q17 83.1 | +0.0 | - |
| 2019 | GS4 | 72 | **sub_part_loss** | 81.2 | 66.7 | 0.50 | 0 | 81.9 | 89.7 | Q18 89.7 | -0.0 | - |
| 2023 | GS4 | 61 | **sub_part_loss** | 63.8 | 42.1 | 0.40 | 2 | 97.5 | 83.3 | Q7 83.3 | +0.0 | 6 |
| 2023 | GS4 | 62 | **sub_part_loss** | 76.1 | 60.0 | 0.49 | 2 | 98.8 | 91.0 | Q11 91.0 | -0.0 | 9 |
| 2023 | GS4 | 63 | **sub_part_loss** | 50.5 | 25.0 | 0.17 | 3 | 97.3 | 92.4 | Q19 95.2 | +2.8 | 14 |
| 2023 | GS4 | 64 | **sub_part_loss** | 93.1 | 88.0 | 0.67 | 2 | 98.6 | 96.9 | Q3 96.9 | +0.0 | -1 |
| 2023 | GS4 | 65 | **sub_part_loss** | 82.6 | 57.9 | 0.45 | 2 | 99.2 | 93.1 | Q9 93.1 | +0.0 | 4 |
| 2023 | GS4 | 66 | **sub_part_loss** | 77.9 | 53.8 | 0.43 | 2 | 100.0 | 100.0 | Q1 100.0 | +0.0 | -5 |

`mk` = enumeration markers in `db_text`; `nest` = how completely the pair sits inside `db_text`; `pos delta` = extraction paper-local number minus DB paper-local number.

## 5. Rows by verdict, with the reason

### apply - 5 rows

- **2013 GS1 db#13** - content cosine 73.0 at or above the labelled apply floor of 64.2, length ratio 0.85 inside [0.76, 1.32], no enumeration loss, and the pair is the best match in the paper
  - DB : The American War of Independence was an economic revolt against British mercantilism. Discuss.
  - pair: "American Revolution was an economic revolt against mercantilism." Substantiate.
- **2014 GS1 db#10** _(hand: apply)_ - content cosine 64.2 at or above the labelled apply floor of 64.2, length ratio 0.84 inside [0.76, 1.32], no enumeration loss, and the pair is the best match in the paper
  - DB : How does the concept of 'Secularism' in India differ from the Western model of secularism?
  - pair: How do the Indian debates on secularism differ from the debates in the West?
- **2014 GS4 db#61** - content cosine 74.7 at or above the labelled apply floor of 64.2, length ratio 0.96 inside [0.76, 1.32], no enumeration loss, and the pair is the best match in the paper
  - DB : All human beings aspire for happiness. What does happiness mean to you? Explain its linkage with ethical living.
  - pair: All human beings aspire for happiness. Do you agree? What does happiness mean to you? Explain with examples.
- **2016 GS1 db#57** _(hand: apply)_ - content cosine 100.0 at or above the labelled apply floor of 64.2, length ratio 0.96 inside [0.76, 1.32], no enumeration loss, and the pair is the best match in the paper
  - DB : Explain the concept of 'Air Mass' and describe its role in macro-climatic changes.
  - pair: Discuss the concept of air mass and explain its role in macro-climatic changes.
- **2018 GS1 db#5** _(hand: apply)_ - content cosine 92.8 at or above the labelled apply floor of 64.2, length ratio 1.16 inside [0.76, 1.32], no enumeration loss, and the pair is the best match in the paper
  - DB : Why is India taking keen interest in the Arctic region?
  - pair: Why is India taking keen interest in resources of Arctic Region?

### sub_part_loss - 8 rows

- **2019 GS4 db#71** - no enumeration markers, but the pair is only 39% of db_text's length - below the 0.76 floor derived from the labelled populations - so content is being dropped
  - DB : What do each of the following quotations mean to you? Ã¢â¬â Ã¢â¬ÅAn unexamined life is not worth livingÃ¢â¬Â. Ã¢â¬â Socrates
  - pair: “An unexamined life is not worth living.” – Socrates
- **2019 GS4 db#72** - no enumeration markers, but the pair is only 50% of db_text's length - below the 0.76 floor derived from the labelled populations - so content is being dropped
  - DB : What do each of the following quotations mean to you? Ã¢â¬â Ã¢â¬ÅA man is but a product of his thoughts. What he thinks he becomes.Ã¢â¬Â Ã¢â¬â M. K. Gandhi
  - pair: “A man is but a product of his thoughts. What he thinks he becomes.” – M. K. Gandhi
- **2023 GS4 db#61** _(hand: sub_part_loss)_ - db_text carries 2 enumeration markers the pair has none of, and the pair sits inside db_text (nest 97.5): applying it deletes the other part(s)
  - DB : (a) What do you understand by 'moral integrity' and 'professional efficiency' in the context of corporate governance in India? Illustrate with suitable examples. (Answer in 150 words) 10 (b) 'International aid' is an acc
  - pair: What do you understand by ‘moral integrity’ and ‘professional efficiency’ in the context of corporate governance in India? Illustrate with suitable examples.
- **2023 GS4 db#62** _(hand: sub_part_loss)_ - db_text carries 2 enumeration markers the pair has none of, and the pair sits inside db_text (nest 98.8): applying it deletes the other part(s)
  - DB : (a) "Corruption is the manifestation of the failure of core values in the society." In your opinion, what measures can be adopted to uplift the core values in the society? (Answer in 150 words) 10 (b) In the context of w
  - pair: “Corruption is the manifestation of the failure of core values in the society.” In your opinion, what measures can be adopted to uplift the core values in the society?
- **2023 GS4 db#63** _(hand: sub_part_loss)_ - db_text carries 3 enumeration markers the pair has none of, and the pair sits inside db_text (nest 97.3): applying it deletes the other part(s)
  - DB : Given below are three quotations of great thinkers. What do each of these quotations convey to you in the present context? (a) "The simplest acts of kindness are by far more powerful than a thousand heads bowing in praye
  - pair: “The simplest acts of kindness are by far more powerful than a thousand heads bowing in prayer.” — Mahatma Gandhi
- **2023 GS4 db#64** _(hand: sub_part_loss)_ - db_text carries 2 enumeration markers the pair has none of, and the pair sits inside db_text (nest 98.6): applying it deletes the other part(s)
  - DB : (a) "What really matters for success, character, happiness and lifelong achievements is a definite set of emotional skills - your EQ - not just purely cognitive abilities that are measured by conventional IQ tests." Do y
  - pair: “What really matters for success, character, happiness and lifelong achievements is a definite set of emotional skills — your EQ — not just purely cognitive abilities that are measured by conventional IQ tests.” Do you a
- **2023 GS4 db#65** _(hand: sub_part_loss)_ - db_text carries 2 enumeration markers the pair has none of, and the pair sits inside db_text (nest 99.2): applying it deletes the other part(s)
  - DB : (a) Is conscience a more reliable guide when compared to laws, rules and regulations in the context of ethical decision making? Discuss. (Answer in 150 words) 10 (b) 'Probity is essential for an effective system of gover
  - pair: Is conscience a more reliable guide when compared to laws, rules and regulations in the context of ethical decision-making? Discuss.
- **2023 GS4 db#66** _(hand: sub_part_loss)_ - db_text carries 2 enumeration markers the pair has none of, and the pair sits inside db_text (nest 100.0): applying it deletes the other part(s)
  - DB : (a) What were the major teachings of Guru Nanak? Explain their relevance in the contemporary world. (Answer in 150 words) 10 (b) Explain the term social capital. How does it enhance good governance? (Answer in 150 words)
  - pair: What were the major teachings of Guru Nanak? Explain their relevance in the contemporary world.

### wrong_question - 10 rows

- **2013 GS2 db#27** - UnlockIAS Q3 of the same paper scores 50.6 against db_text vs 41.9 for the pair (+8.7): the pairing is not the best available match
  - DB : Discuss the scope and limitations of judicial review in India.
  - pair: Discuss the recommendations of the 13th Finance Commission which have been a departure from the previous commissions for strengthening the local government finances.
- **2013 GS2 db#46** - content cosine 11.8 is at or below the labelled wrong-question ceiling of 38.7: the two texts do not share their subject matter
  - DB : Discuss the need for electoral reforms in India with special reference to criminalization of politics.
  - pair: Discuss Section 66A of IT Act, with reference to its alleged violation of Article 19 of the Constitution.
- **2013 GS4 db#76** - content cosine 17.0 is at or below the labelled wrong-question ceiling of 38.7: the two texts do not share their subject matter
  - DB : What do you understand by 'ethical human conduct'? Discuss its determinants and consequences in human actions.
  - pair: What do you understand by 'values' and 'ethics'? In what way is it important to be ethical along with being professionally competent?
- **2013 GS4 db#78** - content cosine 29.7 is at or below the labelled wrong-question ceiling of 38.7: the two texts do not share their subject matter
  - DB : What is emotional intelligence and what are its utilities in civil services administration?
  - pair: What is 'emotional intelligence' and how can it be developed in people? How does it help an individual in taking ethical decisions?
- **2016 GS1 db#48** _(hand: wrong_question)_ - content cosine 37.3 is at or below the labelled wrong-question ceiling of 38.7: the two texts do not share their subject matter
  - DB : Why are the tribals in India referred to as 'Adivasis'? Indicate the major areas of their geographic concentration.
  - pair: Why are the tribals in India referred to as the ‘Scheduled Tribes’? Indicate the major provisions enshrined in the Constitution of India for their upliftment.
- **2016 GS2 db#59** - content cosine 30.0 is at or below the labelled wrong-question ceiling of 38.7: the two texts do not share their subject matter
  - DB : Discuss the Essentials of the 69th Constitutional Amendment Act and controversies surrounding it as a dimensions of federal friction.
  - pair: Discuss the essentials of the 69th Constitutional Amendment Act and anomalies, if any, that have led to recent reported conflicts between the elected representatives and the institution of the Lieutenant Governor in the 
- **2016 GS2 db#69** _(hand: wrong_question)_ - UnlockIAS Q8 of the same paper scores 61.3 against db_text vs 55.0 for the pair (+6.3): the pairing is not the best available match
  - DB : Discuss the procedures and utility of the mechanism of Judicial Review in the context of the Indian Constitution.
  - pair: To what extent is Article 370 of the Indian Constitution, bearing marginal note “temporary provision with respect to the State of Jammu and Kashmir”, temporary? Discuss the future prospects of this provision in the conte
- **2016 GS2 db#76** _(hand: wrong_question)_ - content cosine 26.2 is at or below the labelled wrong-question ceiling of 38.7: the two texts do not share their subject matter
  - DB : Analyze the strategic dimensions of India's maritime security architecture in the Indian Ocean Region.
  - pair: Evaluate the economic and strategic dimensions of India’s Look East Policy in the context of the post-Cold War international scenario.
- **2017 GS1 db#49** _(hand: wrong_question)_ - content cosine 38.7 is at or below the labelled wrong-question ceiling of 38.7: the two texts do not share their subject matter
  - DB : Discuss the various economic and socio-cultural forces that are driving increasing discrimination against the Scheduled Tribes in India.
  - pair: What are the two major legal initiatives by the State since Independence addressing discrimination against Scheduled Tribes (STs)?
- **2017 GS2 db#61** - content cosine 38.3 is at or below the labelled wrong-question ceiling of 38.7: the two texts do not share their subject matter
  - DB : Critically examine the Supreme Court's judgement on 'National Anthem' in Context of Article 19(1)(a) of the Constitution of India.
  - pair: Critically examine the Supreme Court’s judgement on ‘National Judicial Appointments Commission Act, 2014’ with reference to appointment of judges of higher judiciary in India.

### review - 6 rows

- **2013 GS1 db#4** - content cosine 45.3 falls in the unpopulated band between the labelled wrong-question ceiling (38.7) and the labelled apply floor (64.2); no hand-labelled row lands here, so the calibration cannot place it
  - DB : Defying the barriers of age, gender and religion, the Bhakti movement opened the doors of liberation to all. Discuss.
  - pair: Defying the barriers of age, gender and religion, the Indian women became the torch-bearer during the struggle for freedom in India. Discuss.
- **2013 GS1 db#22** - content cosine 44.7 falls in the unpopulated band between the labelled wrong-question ceiling (38.7) and the labelled apply floor (64.2); no hand-labelled row lands here, so the calibration cannot place it
  - DB : Discuss the socio-economic impacts of globalization on the elderly population in India.
  - pair: Critically examine the effect of globalization on the aged population in India.
- **2013 GS3 db#63** - signals disagree: the pair is 65% of db_text's length (sub-part shaped) but content overlap is only 30.3 (wrong-question shaped)
  - DB : Analyze the role of social media networks in driving internal security disruptions and spreading misinformation during crisis events.
  - pair: What are social networking sites and what security implications do these sites present?
- **2014 GS2 db#21** - content matches (cosine 65.9) but the pair is 158% of db_text's length - it adds material the DB question does not have
  - DB : Starting from inventing the 'basic structure' doctrine, the judiciary has played a highly proactive role in ensuring that the Constitution remains a living document. Discuss.
  - pair: Starting from inventing the ‘basic structure’ doctrine, the judiciary has played a highly proactive role in ensuring that India develops into a thriving democracy. In light of the statement, evaluate the role played by j
- **2017 GS2 db#66** - content cosine 60.9 falls in the unpopulated band between the labelled wrong-question ceiling (38.7) and the labelled apply floor (64.2); no hand-labelled row lands here, so the calibration cannot place it
  - DB : Does the Rights of Persons with Disabilities Act, 2016 ensure mechanism for enhanced administrative capacity for their empowerment? Examine.
  - pair: Does the Rights of Persons with Disabilities Act, 2016 ensure effective mechanism for empowerment and inclusion of the intended beneficiaries in the society? Discuss.
- **2017 GS2 db#67** - content cosine 61.1 falls in the unpopulated band between the labelled wrong-question ceiling (38.7) and the labelled apply floor (64.2); no hand-labelled row lands here, so the calibration cannot place it
  - DB : Hunger and Poverty are the biggest challenges for good governance in India still today. Evaluate how far success is achieved in tracking these problems.
  - pair: Hunger and poverty are the biggest challenges for good governance in India still today. Evaluate how far successive governments have progressed in dealing with these humongous problems. Suggest measures for improvement.

## 6. What this does not settle

- The calibration set is 13 rows and the thresholds are derived from its extremes. Reproducing it is necessary, not sufficient.
- The brief's 14th hand-classified row is not identified, so one labelled wrong-question judgement is unaccounted for.
- `sub_part_loss` covers two shapes. Six rows are the classic (a)/(b) case, caught structurally. The two 2019 GS4 rows are caught by the length floor instead: their `db_text` is 'What do each of the following quotations mean to you?' plus one quotation, and the pair is the quotation alone - applying it would delete the instruction that makes the question answerable. Same defect, different shape.
- `review` is a real verdict here, not a fallback: 6 rows carry signals the labelled data cannot place, and they need the same hand inspection the first 14 got.
- Position delta is reported but not used as a rule. It disagrees with the pairing on rows of every class, including genuine ones (2018 GS1 #5 is a correct pair at a delta of 14), so it carries no usable signal on its own.
- No worklist column has been updated.
