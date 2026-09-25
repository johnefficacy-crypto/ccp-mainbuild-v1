"""Option-length balancing (audit: correct option must not be a length cue). Maps generated option text -> balanced text.
Keys/stems/order unchanged; each distractor keeps its named error."""
OVR = {
# CAA-001
"Stands adjourned to the same day in the next week at the same time and place, or to another date, time and place fixed by the Board":
 "Stands adjourned to the same day next week, same time and place, or as the Board fixes",
"Stands dissolved and must be called afresh with 21 clear days' notice": "Stands dissolved and must be called afresh by a new notice of 21 clear days to members",
"Proceeds immediately, the members present being deemed the quorum": "Proceeds at once, the members present being deemed to constitute the quorum for it",
"Stands adjourned to the same day in the next month": "Stands adjourned to the same day in the next month, same time and place, or as fixed",
# CAA-002
"Quorum is 15 members personally present; at least 3 days' notice of the adjourned meeting must be given individually or by newspaper advertisement":
 "Quorum 15 members personally present; 3 days' notice, individually or by advertisement",
"Quorum is 15 members; a fresh 21 clear days' notice is needed": "Quorum 15 members personally present; a fresh notice of 21 clear days to all members",
"Quorum is 5 members; at least 3 days' notice": "Quorum 5 members personally present; 3 days' notice, individually or by advertisement",
"Quorum is 30 members; at least 3 days' notice": "Quorum 30 members personally present; 3 days' notice, individually or by advertisement",
# CAA-005
"He may be appointed by a special resolution, with the explanatory statement to the notice indicating the justification for appointing him":
 "He may be appointed by special resolution, with justification in the explanatory statement",
"He cannot be appointed at all, having attained 70": "He cannot be appointed at all, since he has already attained the age of 70 years",
"He can be appointed only with Central Government approval in every case, in addition to a special resolution":
 "Central Government approval is needed in every case, in addition to a special resolution",
"An ordinary resolution with Board recommendation suffices": "An ordinary resolution suffices, provided the Board recommends his appointment",
# CAA-007
"Jatin must himself satisfy the independence criteria of s.149(6), and he vacates office when Kavya returns on 15 October 2026":
 "Jatin must meet the s.149(6) criteria, and he vacates office on Kavya's return on 15 October 2026",
"Jatin need not be independent, since he only substitutes for Kavya": "Jatin need not meet s.149(6) criteria, since he only substitutes for Kavya during her absence",
"Jatin continues until the originally planned five-month absence ends": "Jatin continues in office until Kavya's originally planned five-month absence ends",
"Jatin holds office until the next AGM, like an additional director": "Jatin holds office until the next AGM, like an additional director appointed by the Board",
# CAA-008
"Within 60 days from receipt of the order, on any question of law arising out of it": "Within 60 days of receipt of the order, on any question of law",
"Within 30 days, on any question": "Within 30 days of receipt of the order, on any question arising",
"Within 45 days, on questions of fact and law": "Within 45 days of receipt of the order, on questions of fact and law",
"Within 90 days, on any question of law": "Within 90 days of receipt of the order, on any question of law",
# CAA-010
"45 days from the date the copy of the order is made available, extendable by up to 45 days for sufficient cause":
 "45 days from availability of the order copy, plus up to 45 days for sufficient cause",
"90 days, with no extension": "90 days from availability of the order copy, with no further extension allowed",
"60 days, extendable by 60 days": "60 days from availability of the order copy, plus up to 60 days for sufficient cause",
"30 days, extendable by 15 days": "30 days from availability of the order copy, plus up to 15 days for sufficient cause",
# CAA-012
"Filed on day 67: beyond 45 days but within the further 45 days, so the NCLAT may entertain it if satisfied that there was sufficient cause":
 "Filed on day 67: late, but within the further 45 days; NCLAT may admit it on sufficient cause",
"Filed on day 67: time-barred, as the outer limit including extension is 60 days": "Filed on day 67: time-barred, since the outer limit including any extension is only 60 days",
"Filed on day 67: within time, as 90 days is available as of right": "Filed on day 67: within time, since a 90-day period is available to the appellant as of right",
"Filed on day 67: time-barred, as the NCLAT has no power to condone delay": "Filed on day 67: time-barred, since the NCLAT has no power at all to condone any delay",
# CAA-014
"The members in general meeting": "The members of the company by ordinary resolution in general meeting",
"The Board of Directors in all cases": "The Board of Directors in all cases, irrespective of any committee",
"The Insolvency and Bankruptcy Board of India": "The Insolvency and Bankruptcy Board of India, as registering authority",
# CAA-016
"Allotted once to an individual by the Central Government and used for all his directorships": "Allotted once by the Central Government; valid for all his directorships",
"Allotted by the company that first appoints the individual": "Allotted by the company that first appoints the individual as its director",
"Required to be surrendered and re-obtained every five years": "Allotted by the Central Government but to be re-obtained every five years",
# CAA-035
"180 days; next 30 days; next 60 days": "180 days from registration; next 30 days; next 60 days",
"30 days; next 60 days; next 90 days": "30 days from registration; next 60 days; next 90 days",
"60 days; next 60 days; next 30 days": "60 days from registration; next 60 days; next 30 days",
# CAA-037
"By the CAG within 30 days; if the CAG does not, by the Board within the next 30 days": "CAG within 30 days; failing which, the Board within the next 30 days",
"By the Board within 30 days, with approval of members within three months": "Board within 30 days, with approval of members within three months",
"By the CAG within 60 days": "CAG within 60 days; failing which, the members at a general meeting",
"By members at a general meeting within three months": "Members at a general meeting within three months of the vacancy",
# CAA-052
"The 10% limit for executive directors, the 1% limit for non-executive directors and the 11% overall ceiling":
 "All three: the 10% executive, the 1% NED and the 11% overall limits",
"None of the limits": "None of the limits, since each is within its ceiling on this profit",
"Only the 1% NED limit; executive pay is tested against 11%": "Only the 1% NED limit; executive pay is tested against the 11% ceiling",
"Only the 10% executive-director limit; NED commission is within the 3% limit": "Only the 10% executive limit; NED commission is within the 3% limit",
# CAA-063
"Cost audit applies; the Board must appoint a cost accountant in practice within 180 days of the start of the financial year, and the statutory auditor cannot be appointed":
 "Cost audit applies; Board appoints a practising cost accountant within 180 days; statutory auditor barred",
"Cost audit applies; the cost auditor is appointed by shareholders at the AGM": "Cost audit applies; shareholders appoint a practising cost accountant at the AGM within 180 days",
"Cost audit applies; the statutory auditor may also be the cost auditor": "Cost audit applies; Board appoints within 180 days, and the statutory auditor may be the cost auditor",
"Only cost records apply; Table B cost audit needs overall turnover of ₹150 crore": "Only cost records apply, since Table B cost audit needs overall turnover of ₹150 crore or more",
# CAA-068
"Pay the company twice the gain, i.e., ₹24 lakh": "Pay the company twice the gain, i.e., ₹24 lakh, as disgorgement",
"Only removal from office; no repayment is required": "Only removal from office; no repayment to the company is required",
"Pay ₹12 lakh to the Central Government": "Pay an amount equal to the gain, ₹12 lakh, to the Central Government",
# CAA-071
"Shares up to 15% of existing paid-up equity capital, i.e., ₹9 crore (higher than the ₹5 crore issue-value limit)":
 "15% of existing paid-up equity capital, i.e., ₹9 crore (the higher limit)",
"Shares of issue value ₹5 crore (the lower of the two limits)": "Shares of issue value ₹5 crore, being the lower of the two annual limits",
"Shares up to 50% of paid-up equity capital, i.e., ₹30 crore": "50% of existing paid-up equity capital, i.e., ₹30 crore (start-up limit)",
"Shares up to 25% of paid-up equity capital, i.e., ₹15 crore": "25% of existing paid-up equity capital, i.e., ₹15 crore (the overall cap)",
# CAA-073
"The ₹1 lakh limit for a relative's holding is exceeded; corrective action must be taken within 60 days of the acquisition, failing which she is disqualified":
 "₹1 lakh relative limit exceeded; corrective action within 60 days, else disqualified",
"There is no issue; a relative may hold up to ₹5 lakh": "No issue, since a relative of the auditor may hold securities of face value up to ₹5 lakh",
"The restriction covers only shares of Tulsi itself, not its subsidiary": "No issue, since the restriction covers shares of Tulsi itself and not of its subsidiary",
"She is disqualified immediately with no scope for correction": "She is disqualified at once, with no window for corrective action by her relative",
# CAA-080
"Matured deposits and debentures with companies that remain unclaimed for seven years": "Matured deposits and debentures unclaimed for seven years",
"Unspent CSR amounts of a company": "Unspent CSR amounts of a company at the end of the year",
"Penalties collected by the NCLT under the Act": "Penalties collected by the NCLT under the Companies Act",
"Sitting fees that directors decline to accept": "Sitting fees that directors decline to accept from the company",
# CAA-082
"Not eligible — the transactions (11.25% of his total income) exceed 10% of his total income": "Not eligible — transactions are 11.25% of his income, above the 10% limit",
"Eligible — only transactions above ₹50 lakh are counted": "Eligible — only transactions above ₹50 lakh count towards the limit",
"Eligible — pecuniary relationship tests apply only to relatives": "Eligible — pecuniary relationship tests apply only to his relatives",
"Eligible — the ceiling for pecuniary relationships is 25% of total income": "Eligible — the ceiling for pecuniary relationships is 25% of income",
# CAA-085
"He can be re-appointed as an independent director from 1 April 2029, and meanwhile cannot be associated with Zeal in any other capacity":
 "Re-appointable from 1 April 2029; meanwhile no association with Zeal in any capacity",
"He can be re-appointed immediately for a third term by special resolution": "Re-appointable immediately for a third term by passing a special resolution",
"He can be re-appointed from 1 April 2031": "Re-appointable from 1 April 2031, after a five-year cooling-off from Zeal",
"He can be re-appointed from 1 April 2029, and may meanwhile act as a paid consultant to Zeal": "Re-appointable from 1 April 2029; meanwhile may act as a paid consultant to Zeal",
# CAA-087
"Profits generated in the financial year up to the quarter preceding the date of declaration": "Profits of the FY up to the quarter preceding the declaration",
"General reserve built up in earlier years": "General reserve built up out of profits of earlier years",
"Securities premium account": "Securities premium account, to the extent of cash received",
"Revaluation reserve": "Revaluation reserve arising on revaluation of land and buildings",
# CAA-091
"The issue is void; the company must refund ₹8,00,000 with interest at 12% p.a. from the date of issue, and the company and officers in default are liable to a penalty up to the lower of the amount raised and ₹5 lakh (i.e., ₹5,00,000)":
 "Void; refund ₹8,00,000 with 12% p.a. interest; penalty up to lower of amount raised and ₹5 lakh",
"The issue is valid; the discount is written off against securities premium": "Valid; the discount is written off against the securities premium account; no penalty arises",
"The issue is voidable at the option of the allottees; interest at 18% p.a. applies": "Voidable at the allottees' option; refund with 18% p.a. interest; penalty up to ₹5 lakh",
"The issue is void; the company must refund ₹8,00,000 without interest": "Void; refund ₹8,00,000 without interest, and officers in default face a penalty up to ₹5 lakh",
# CAA-092
"Two kinds — equity (with voting rights, or with differential rights as to dividend, voting or otherwise) and preference":
 "Two kinds — equity (with voting or differential rights) and preference",
"Two kinds — ordinary and redeemable": "Two kinds — ordinary (voting) and redeemable (non-voting) shares",
# CAA-096
"s.185 applies — borrowings exceed the lower of twice paid-up capital (₹20 crore) and ₹50 crore, so the private-company exemption is lost":
 "s.185 applies — borrowings exceed lower of 2× paid-up (₹20 crore) and ₹50 crore",
"Exempt — all private companies are outside s.185": "Exempt — all private companies are outside s.185 without any condition",
"Exempt — borrowings are below ₹50 crore": "Exempt — borrowings are below ₹50 crore, which is the only borrowing test",
"Exempt — borrowings are below three times paid-up capital": "Exempt — borrowings are below three times the company's paid-up capital",
# CAA-100
"She cannot accept, because a whole-time director of a listed entity can be an independent director in not more than three listed entities":
 "No — as a listed-entity WTD she can be an ID in at most three listed entities",
"She can accept, because only the Companies Act limit of 20 companies applies": "Yes — only the Companies Act limit of 20 companies applies to her case",
"She cannot accept, because a whole-time director cannot be an independent director anywhere": "No — a whole-time director cannot be an independent director anywhere",
"She can accept, because the limit is seven listed entities": "Yes — the LODR limit is seven listed entities, and she would hold five",
# CAA-102
"A person who had consented to become a director but withdrew his consent before the issue, the prospectus being issued without his authority or consent":
 "One who withdrew consent to be a director before issue, which was without his authority",
"A director who did not read the prospectus before it was issued": "A director who did not read the prospectus before it was issued to the public",
"A promoter who relied on the lead manager's draft": "A promoter who relied in good faith on the lead manager's draft of the prospectus",
# CAA-103
"Imprisonment of not less than 3 years up to 10 years, and fine not less than ₹2 crore up to ₹6 crore": "Imprisonment 3–10 years (minimum 3), and fine of ₹2 crore to ₹6 crore",
"Imprisonment of 6 months to 10 years, and fine of ₹2 crore to ₹6 crore": "Imprisonment 6 months–10 years, and fine of ₹2 crore to ₹6 crore",
"Imprisonment of not less than 3 years up to 10 years, and fine up to ₹2 crore only": "Imprisonment 3–10 years (minimum 3), and fine up to ₹2 crore only",
"Imprisonment up to 5 years or fine up to ₹50 lakh, or both": "Imprisonment up to 5 years, or fine up to ₹50 lakh, or both of these",
# CAA-107
"Valid under the Companies Act but not under SEBI LODR, which requires at least two-thirds independent directors": "Valid under the Act; invalid under LODR (two-thirds IDs needed)",
"Invalid under the Companies Act but valid under SEBI LODR": "Invalid under the Act (majority IDs needed); valid under SEBI LODR",
"Valid under both the Companies Act and SEBI LODR": "Valid under both the Companies Act and the SEBI LODR Regulations",
"Invalid under both, since a majority of independent directors is required": "Invalid under both, since a majority of IDs is required by each",
# CAA-109
"Must be circulated to all directors and become final only on ratification by at least one independent director": "Circulated to all directors; final only on ratification by at least one ID",
"Must be ratified by the members at the next general meeting": "Must be ratified by the members at the next general meeting to be final",
"Are void, since shorter notice is not permitted": "Are void, since a Board meeting cannot be called at shorter notice",
"Are final, since urgency justifies shorter notice": "Are final, since urgency by itself justifies calling at shorter notice",
# CAA-113
"Making calls on shareholders in respect of money unpaid on their shares": "Making calls on shareholders for money unpaid on their shares",
"Affixing the common seal to a share certificate": "Affixing the common seal to a share certificate of the company",
"Opening a salary bank account": "Opening a salary bank account for the company's employees",
"Approving registration of transmission of shares": "Approving registration of transmission of shares on death",
# CAA-114
"Borrowing money, investing the company's funds, and granting loans or giving guarantees/security": "Borrowing money, investing funds, and granting loans/guarantees/security",
"All s.179(3) powers, if the articles so provide": "All s.179(3) powers without exception, if the articles so provide",
# CAA-119
"K&M cannot be re-appointed; it is eligible again only after a five-year cooling-off (i.e., from the 2031 AGM), and a firm having a common partner with K&M at the end of its term is also barred during that period":
 "No; eligible again from the 2031 AGM (5-year cooling-off); common-partner firms barred too",
"K&M can be re-appointed for a third term if members pass a special resolution": "Yes; K&M can be re-appointed for a third term if members pass a special resolution",
"K&M can be re-appointed because rotation applies only to listed companies": "Yes; K&M can be re-appointed, since auditor rotation applies only to listed companies",
"K&M cannot be re-appointed; it becomes eligible again after three years (the 2029 AGM)": "No; eligible again from the 2029 AGM after a three-year cooling-off, as for IDs",
# CAA-120
"The Board refers the recommendation back to the Audit Committee citing reasons; if the Committee does not reconsider, the Board records its reasons for disagreement and sends its own recommendation to the members at the AGM":
 "Board refers it back to the AC with reasons; if unchanged, Board sends its own reasoned recommendation to the AGM",
"The Board must place only the Audit Committee's recommendation before members": "Board must place only the AC's recommendation before the AGM; it cannot send its own recommendation",
"The Board appoints its preferred firm directly, since the Board is the appointing authority": "Board appoints its preferred firm directly, since the Board is the appointing authority for auditors",
"The dispute is referred to the Registrar for a decision": "Board refers the dispute to the Registrar, whose decision on the choice of auditor is binding",
# CAA-122
"The Board fills the vacancy within 30 days; the appointment must be approved by members at a general meeting convened within three months of the Board's recommendation, and the appointee holds office till the conclusion of the next AGM":
 "Board fills within 30 days; members approve at a GM within 3 months; office till next AGM",
"Members fill the vacancy at an EGM within 90 days for a fresh five-year term": "Members fill the vacancy at an EGM within 90 days for a fresh five-year term of office",
"The Audit Committee fills the vacancy within 60 days; no members' approval is needed": "Audit Committee fills within 60 days; no members' approval needed; office till next AGM",
"The Board fills the vacancy within 30 days and the appointee serves the balance of the five-year term": "Board fills within 30 days; the appointee serves the balance of the original five-year term",
# CAA-130
"Rohan's consent to act must be filed with the Registrar within 30 days of appointment (by 10 December 2026), and Sundaram must file the return of particulars of the appointment within 30 days":
 "Consent to be filed within 30 days (by 10 December 2026); company's return also within 30 days",
"Consent and return both within 60 days (by 9 January 2027)": "Consent and return both to be filed within 60 days of appointment (by 9 January 2027)",
"Sundaram must obtain a fresh DIN for Rohan for this company": "Sundaram must obtain a fresh DIN for Rohan specific to this company before he can act",
"No filing is needed because an additional director holds office only till the next AGM": "No filing is needed, since an additional director holds office only till the next AGM",
}
