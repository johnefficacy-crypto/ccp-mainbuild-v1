# UnlockIAS extraction vs raw DOCX — fidelity cross-check

Offline, read-only, no OCR. Seven papers (2024 GS1-3; 2025 GS1-4). No 2024 GS-4 DOCX exists, so 2024 GS-4 is excluded, not substituted. Match: `rapidfuzz.fuzz.partial_ratio(normalize(unlockias), normalize(docx_question))`, best over the paper's DOCX questions. Thresholds: exact >=95, variant 80-94, orphan <80.

## Per-paper counts

| year | paper | DOCX Qs | UnlockIAS Qs | exact | variant | orphan | score min/med/max |
|---|---|---|---|---|---|---|---|
| 2024 | GS1 | 20 | 20 | 20 | 0 | 0 | 100.0/100.0/100.0 |
| 2024 | GS2 | 20 | 20 | 0 | 0 | 20 | 51.2/61.3/74.1 |
| 2024 | GS3 | 20 | 20 | 0 | 2 | 18 | 57.4/68.5/91.1 |
| 2025 | GS1 | 40 | 20 | 17 | 3 | 0 | 91.2/99.6/100.0 |
| 2025 | GS2 | 40 | 20 | 20 | 0 | 0 | 100.0/100.0/100.0 |
| 2025 | GS3 | 40 | 20 | 20 | 0 | 0 | 97.5/100.0/100.0 |
| 2025 | GS4 | 20 | 18 | 18 | 0 | 0 | 96.4/100.0/100.0 |
| **all** | | | | **95** | **5** | **38** | 51.2/100.0/100.0 |

## Orphans (best_score < 80) — 38 total

### 2024 GS2 local Q1 — best 51.2 (closest DOCX Q12)

- **UnlockIAS**: Right to privacy is intrinsic to life and personal liberty and is inherently protected under Article 21 of the constitution. Explain. In this reference discuss the law relating to D.N.A. testing of child in the womb to establish its paternity.
- **DOCX (closest)**: Q12.         21               DNA         (250  )   15 Right to privacy under Article 21   explain. Discuss law on DNA test for unborn child's paternity. (250 words)   15

### 2024 GS2 local Q2 — best 55.5 (closest DOCX Q5)

- **UnlockIAS**: Analyse the role of local bodies in providing good governance at local level and bring out the pros and cons merging the rural local bodies with the urban local bodies.
- **DOCX (closest)**: Q5.              -         -    (150  )   10 Analyse local bodies' role in local governance. Pros/cons of merging rural-urban local bodies. (150 words)   10

### 2024 GS2 local Q3 — best 63.4 (closest DOCX Q13)

- **UnlockIAS**: What changes has the Union Government recently introduced in the domain of Centre-State relations? Suggest measures to be adopted to build the trust between the Centre and the States and for strengthening federalism.
- **DOCX (closest)**: Q13.  -           ?                   (250  )   15 Recent changes in Centre-State relations? Suggest measures to strengthen federalism & trust. (250 words)   15

### 2024 GS2 local Q4 — best 72.3 (closest DOCX Q15)

- **UnlockIAS**: Discuss India as a secular state and compare with the secular principles of the US constitution.
- **DOCX (closest)**: Q15.                , US               (250  )   15 Discuss India as secular state, compare with US constitution's secular principles. (250 words)   15

### 2024 GS2 local Q5 — best 64.3 (closest DOCX Q3)

- **UnlockIAS**: “The growth of cabinet system has practically resulted in the marginalisation of the parliamentary supremacy.” Elucidate.
- **DOCX (closest)**: Q3. "               "     (150  )   10 "Growth of cabinet system has marginalised parliamentary supremacy." Elucidate. (150 words)   10

### 2024 GS2 local Q6 — best 66.3 (closest DOCX Q14)

- **UnlockIAS**: Explain the reasons for the growth of public interest litigation in India. As a result of it, has the Indian Supreme Court emerged as the world’s most powerful judiciary?
- **DOCX (closest)**: Q14.                                ? (250  )   15 Explain growth of PIL in India. Has Indian SC emerged as world's most powerful judiciary? (250 words)   15

### 2024 GS2 local Q7 — best 59.6 (closest DOCX Q1)

- **UnlockIAS**: Examine the need for electoral reforms as suggested by various committees with particular reference to “one nation – one election” principle.
- **DOCX (closest)**: Q1.    , "   -   "       (150  )   10 Examine need for electoral reforms w.r.t. "one nation-one election". (150 words)   10

### 2024 GS2 local Q8 — best 67.0 (closest DOCX Q2)

- **UnlockIAS**: Explain and distinguish between Lok Adalats and Arbitration Tribunals. Whether they entertain civil as well as criminal cases?
- **DOCX (closest)**: Q2.            ,                  ? (150  )   10 Explain & distinguish Lok Adalats and Arbitration Tribunals. Civil and criminal cases both? (150 words)   10

### 2024 GS2 local Q9 — best 54.9 (closest DOCX Q4)

- **UnlockIAS**: The duty of the Comptroller and Auditor General is not merely to ensure the legality of expenditure but also its propriety.” Comment.
- **DOCX (closest)**: Q4. "CAG            ,          "     (150  )   10 "CAG's duty is not merely legality but also propriety of expenditure." Comment. (150 words)   10

### 2024 GS2 local Q10 — best 71.4 (closest DOCX Q11)

- **UnlockIAS**: What are the aims and objects of recently passed and enforced, The Public Examination (Prevention of Unfair Means) Act, 2024? Whether University/State Education Board examinations, too, are covered under the Act?
- **DOCX (closest)**: Q11.     (     )   2024      ?  /       ? (250  )   15 Public Examination (Prevention of Unfair Means) Act 2024 aims? University/State exams covered? (250 words)   15

### 2024 GS2 local Q11 — best 74.1 (closest DOCX Q6)

- **UnlockIAS**: Public charitable trusts have the potential to make India’s development more inclusive as they relate to certain vital public issues. Comment.
- **DOCX (closest)**: Q6.                           (150  )   10 Public charitable trusts can make India's development more inclusive. Comment. (150 words)   10

### 2024 GS2 local Q12 — best 56.4 (closest DOCX Q17)

- **UnlockIAS**: In a crucial domain like the public healthcare system the Indian State should play a vital role to contain the adverse impact of marketisation of the system. Suggest some measures through which the State can enhance the reach of public healthcare at the grassroots level.
- **DOCX (closest)**: Q17.                                   (250  )   15 State's role to check marketisation harm in public healthcare. Measures for grassroots reach. (250 words)   15

### 2024 GS2 local Q13 — best 65.7 (closest DOCX Q7)

- **UnlockIAS**: Poverty and malnutrition create a vicious cycle, adversely affecting human capital formation. What steps can be taken to break the cycle?
- **DOCX (closest)**: Q7.                                 (150  )   10 Poverty-malnutrition vicious cycle hurts human capital formation. Steps to break it? (150 words)   10

### 2024 GS2 local Q14 — best 59.8 (closest DOCX Q16)

- **UnlockIAS**: The Citizens’ charter has been a landmark initiative in ensuring citizen-centric administration. But it is yet to reach its full potential. Identify the factors hindering the realisation of its promise and suggest measures to overcome them.
- **DOCX (closest)**: Q16.    -                            (250  )   15 Citizens' charter yet to reach full potential. Identify hindering factors, suggest measures. (250 words)   15

### 2024 GS2 local Q15 — best 59.9 (closest DOCX Q18)

- **UnlockIAS**: e-governance is not just about the routine application of digital technology in service delivery process. It is as much about multifarious interactions for ensuring transparency and accountability. In this context evaluate the role of the ‘Interactive Service Model’ of e-governance.
- **DOCX (closest)**: Q18. e-governance            /    "     "     (250  )   15 e-governance not just tech application   for transparency/accountability. Evaluate 'Interactive Service Model'. (250 words)   15

### 2024 GS2 local Q16 — best 62.7 (closest DOCX Q8)

- **UnlockIAS**: The Doctrine of Democratic Governance makes it necessary that the public perception of the integrity and commitment of civil servants becomes absolutely positive. Discuss.
- **DOCX (closest)**: Q8.                             (150  )   10 Democratic governance needs positive public perception of civil servants' integrity. Discuss. (150 words)   10

### 2024 GS2 local Q17 — best 58.7 (closest DOCX Q20)

- **UnlockIAS**: Discuss the geopolitical and geostrategic importance of Maldives for India with a focus on global trade and energy flows. Further also discuss how this relationship affects India’s maritime security and regional stability amidst international competition?
- **DOCX (closest)**: Q20.          - / -    ( ,  )                       (250  )   15 Discuss Maldives' geopolitical/geostrategic importance for India (trade, energy). Also its effect on maritime security & regional stability. (250 words)   15

### 2024 GS2 local Q18 — best 63.0 (closest DOCX Q9)

- **UnlockIAS**: ‘The West is fostering India as an alternative to reduce dependence on China’s supply chain and as a strategic ally to counter China’s political and economic dominance.’ Explain this statement with examples.
- **DOCX (closest)**: Q9.        -                              (150  )   10 West fostering India as alternative to China dependence, strategic ally. Explain with examples. (150 words)   10

### 2024 GS2 local Q19 — best 52.3 (closest DOCX Q10)

- **UnlockIAS**: Critically analyse India’s evolving diplomatic, economic and strategic relations with the Central Asian Republics (CARs) highlighting their increasing significance in regional and global geopolitics.
- **DOCX (closest)**: Q10.       (CARs)        ,  ,                   (150  )   10 Critically analyse India-CARs relations, their growing regional/global geopolitical significance. (150 words)   10

### 2024 GS2 local Q20 — best 53.4 (closest DOCX Q19)

- **UnlockIAS**: ‘Terrorism has become a significant threat to global peace and security.’ Evaluate the effectiveness of the United Nations Security Council’s Counter Terrorism Committee (CTC) and its associated bodies in addressing and mitigating this threat at the international level.
- **DOCX (closest)**: Q19.         UNSC   CTC               (250  )   15 Terrorism global threat   evaluate UNSC Counter Terrorism Committee (CTC) effectiveness. (250 words)   15

### 2024 GS3 local Q1 — best 69.3 (closest DOCX Q1)

- **UnlockIAS**: Examine the pattern and trend of public expenditure on Social Services in the post-reforms period in India. To what extent this has been in consonance with achieving the objective of inclusive growth?
- **DOCX (closest)**: Q1.                                        ? (150  )   10 Examine pattern/trend of public expenditure on social services post-reforms India. Consonance with inclusive growth objective? (150 words)   10

### 2024 GS3 local Q2 — best 76.9 (closest DOCX Q2)

- **UnlockIAS**: What are the causes of persistent high food inflation in India? Comment on the effectiveness of the monetary policy of the RBI to control this type of inflation.
- **DOCX (closest)**: Q2.                ? RBI             (150  )   10 Causes of persistent high food inflation in India? Comment on RBI monetary policy effectiveness. (150 words)   10

### 2024 GS3 local Q4 — best 72.7 (closest DOCX Q14)

- **UnlockIAS**: Elucidate the importance of buffer stocks for stabilizing agricultural prices in India. What are the challenges associated with the storage of buffer stock? Discuss.
- **DOCX (closest)**: Q14.                          ?     (250  )   15 Elucidate importance of buffer stocks for stabilizing agri prices. Storage challenges? Discuss. (250 words)   15

### 2024 GS3 local Q5 — best 63.9 (closest DOCX Q13)

- **UnlockIAS**: What are the major challenges faced by Indian irrigation system in recent times? State the measures taken by the government for efficient irrigation management.
- **DOCX (closest)**: Q13.            ?               (250  )   15 Major challenges of Indian irrigation system? State measures for efficient irrigation management. (250 words)   15

### 2024 GS3 local Q6 — best 74.2 (closest DOCX Q3)

- **UnlockIAS**: What were the factors responsible for the successful implementation of land reforms in some parts of the country? Elaborate.
- **DOCX (closest)**: Q3.                            ?     (150  )   10 Factors responsible for successful land reforms implementation in some parts of country? Elaborate. (150 words)   10

### 2024 GS3 local Q7 — best 68.5 (closest DOCX Q11)

- **UnlockIAS**: Discuss the merits and demerits of the four Labour Codes in the context of labour market reforms in India. What has been the progress so far in this regard?
- **DOCX (closest)**: Q11.               '   '    -            (250  )   15 Discuss merits/demerits of four 'Labour Codes' in labour market reforms. Progress so far? (250 words)   15

### 2024 GS3 local Q8 — best 68.4 (closest DOCX Q12)

- **UnlockIAS**: What is the need for expanding the regional air connectivity in India? In this context, discuss the government’s UDAN Scheme and its achievements.
- **DOCX (closest)**: Q12.                ? ' '           (250  )   15 Need for expanding regional air connectivity in India? Discuss UDAN Scheme and achievements. (250 words)   15

### 2024 GS3 local Q9 — best 57.6 (closest DOCX Q5)

- **UnlockIAS**: What is the present world scenario of intellectual property rights with respect to life materials? Although India is second in the world to file patents, still only a few have been commercialized. Explain the reasons behind this less commercialization.
- **DOCX (closest)**: Q5.                    ?            ,                 (150  )   10 Present world scenario of IPR w.r.t. life materials? India 2nd in patents, explain low commercialization reasons. (150 words)   10

### 2024 GS3 local Q10 — best 62.1 (closest DOCX Q16)

- **UnlockIAS**: What are asteroids? How real is the threat of them causing extinction of life? What strategies have been developed to prevent such a catastrophe?
- **DOCX (closest)**: Q16.   (asteroids)    ?          ?          ? (250  )   15 What are asteroids? How real is extinction threat? What prevention strategies developed? (250 words)   15

### 2024 GS3 local Q11 — best 70.9 (closest DOCX Q6)

- **UnlockIAS**: What is the technology being employed for electronic toll collection on highways? What are its advantages and limitations? What are the proposed changes that will make this process seamless? Would this transition carry any potential hazards?
- **DOCX (closest)**: Q6.        -       -   ?  ,  ,             (150  )   10 Technology for electronic toll collection on highways? Advantages, limitations, proposed changes, potential hazards? (150 words)   10

### 2024 GS3 local Q13 — best 62.6 (closest DOCX Q7)

- **UnlockIAS**: Industrial pollution of river water is a significant environmental issue in India. Discuss the various mitigation measures to deal with this problem and also the government’s initiatives in this regard.
- **DOCX (closest)**: Q7.                                   (150  )   10 Industrial pollution of river water   discuss mitigation measures and government initiatives. (150 words)   10

### 2024 GS3 local Q14 — best 71.1 (closest DOCX Q8)

- **UnlockIAS**: What role do environmental NGOs and activists play in influencing Environmental Impact Assessment (EIA) outcomes for major projects in India? Cite four examples with all important details.
- **DOCX (closest)**: Q8.           EIA       NGO        ?       (150  )   10 Role of environmental NGOs/activists in influencing EIA outcomes for major projects in India? Cite four examples. (150 words)   10

### 2024 GS3 local Q15 — best 65.1 (closest DOCX Q15)

- **UnlockIAS**: The world is facing an acute shortage of clean and safe freshwater. What are the alternative technologies which can solve this crisis? Briefly discuss any three such technologies citing their key merits and demerits.
- **DOCX (closest)**: Q15.                  ?        -        (250  )   15 Alternative technologies for freshwater shortage crisis? Briefly discuss any three with merits/demerits. (250 words)   15

### 2024 GS3 local Q16 — best 57.4 (closest DOCX Q18)

- **UnlockIAS**: Flooding in urban areas is an emerging climate-induced disaster. Discuss the causes of this disaster. Mention the features of two such major floods in the last two decades in India. Describe the policies and frameworks in India that aim at tackling such floods.
- **DOCX (closest)**: Q18.      -                                    (250  )   15 Urban flooding climate-induced disaster   discuss causes. Two major floods (last 2 decades) & Indian policies to tackle. (250 words)   15

### 2024 GS3 local Q17 — best 62.7 (closest DOCX Q17)

- **UnlockIAS**: What is disaster resilience? How is it determined? Describe various elements of a resilience framework. Also mention the global targets of Sendai Framework for Disaster Risk Reduction (2015-2030).
- **DOCX (closest)**: Q17.     (resilience)    ?      ?             (2015-2030)       (250  )   15 What is disaster resilience? How determined? Elements of framework + Sendai Framework 2015-2030 global targets. (250 words)   15

### 2024 GS3 local Q18 — best 77.5 (closest DOCX Q9)

- **UnlockIAS**: Explain how narco-terrorism has emerged as a serious threat across the country. Suggest suitable measures to counter narco-terrorism.
- **DOCX (closest)**: Q9.  -                   ?         (150  )   10 How has narco-terrorism emerged as serious threat across country? Suggest countermeasures. (150 words)   10

### 2024 GS3 local Q19 — best 64.1 (closest DOCX Q19)

- **UnlockIAS**: India has a long and troubled border with China and Pakistan, fraught with contentious issues. Examine the conflicting issues and security challenges along the border. Also give out the development being undertaken in these areas under the Border Area Development Programme (BADP) and Border Infrastructure and Management (BIM) Scheme.
- **DOCX (closest)**: Q19.  - -                BADP   BIM           (250  )   15 Examine conflicting issues/security challenges on China-Pakistan border. Development under BADP and BIM Scheme. (250 words)   15

### 2024 GS3 local Q20 — best 65.4 (closest DOCX Q20)

- **UnlockIAS**: Social media and encrypting messaging services pose a serious security challenge. What measures have been adopted at various levels to address the security implications of social media? Also suggest any other remedies to address the problem.
- **DOCX (closest)**: Q20.                          ?       (250  )   15 Social media/encrypted messaging security challenge   measures adopted at various levels? Suggest other remedies. (250 words)   15


## Verdict on UnlockIAS fidelity

- 138 UnlockIAS questions cross-checked across the seven papers: **95 exact, 5 variant, 38 orphan**.
- **38 orphan(s)** — UnlockIAS questions with no >=80 counterpart in the official DOCX (listed above). They are concentrated, not scattered:
    - 2024 GS2: 20/20 orphan
    - 2024 GS3: 18/20 orphan
- The other 5 papers are clean (0 orphan): 2024 GS1, 2025 GS1, 2025 GS2, 2025 GS3, 2025 GS4.

- **These orphans are wrong-year misfilings in the UnlockIAS source, not an extraction artefact.** The raw `upsc-mains-2024.pdf` header itself labels the question *"Right to privacy is intrinsic to life and personal liberty … Article 21 … D.N.A"* as **"2024 GS-II 15M"**, but that is a 2017-era GS2 question; the actual 2024 GS2 Q1 (in the official DOCX and the DB source) is *"electoral reforms w.r.t. one nation-one election"*. The extractor read the PDF's printed header correctly — the compilation filed the wrong questions under 2024 GS2/GS3.

**Conclusion: UnlockIAS is NOT uniformly faithful.** It transcribes some papers verbatim (2024 GS1 and all four 2025 papers = 0 orphan) yet misfiles entire papers with wrong-year content (2024 GS2 and GS3). Because the misfiling is invisible without an official paper to check against — and that is exactly what is missing for 2016, 2017, 2018 and 2023 — UnlockIAS cannot be trusted as an unverified repair source for those years. **Those four years stay unresolved.**

### Lowest-scoring variant (formatting vs content check)

2024 GS3 local Q3 — score 82.6, DOCX Q4. The English stems match; the score is diluted by the DOCX carrying marks/instructions and stripped bilingual text around the question:
- **UnlockIAS**: Explain the role of millets for ensuring health and nutritional security in India.
- **DOCX (closest)**: Q4.                         (150  )   10 Explain role of millets for health & nutritional security in India. (150 words)   10
