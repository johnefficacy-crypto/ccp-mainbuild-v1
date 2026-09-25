-- REG-CORPUS: new subject `financial-sector-acts` — 21 Act topics, 105 microtopics.
-- Operator runs live. Idempotent. Slugs hardcoded = workbench/corpus/reg/lists/financial-sector-acts.tsv.
-- subject_group is copied from the `finance` subject so no new enum value is needed.
-- NOTE: if exams link to subjects through a separate table (exam→subject mapping), that link is NOT created here —
--       REG-CORPUS-03 must confirm how a new subject becomes visible to sebi/pfrda/ifsca pools.
BEGIN;

INSERT INTO public.subjects (slug, name, subject_group, description, is_active)
SELECT 'financial-sector-acts', 'Financial Sector Acts', s.subject_group,
       'Statutes governing Indian financial regulators and markets (RBI, BR, SEBI, SCRA, Depositories, PSS, FEMA, IRDA/Insurance, PFRDA, IFSCA, IBC, SARFAESI, PMLA and others).', true
FROM public.subjects s WHERE s.slug = 'finance'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.topics (subject_id, parent_topic_id, slug, name, level, is_active, metadata)
SELECT s.id, NULL, v.slug, v.name, 'topic', true, '{"tier":"official","exams":["sebi","pfrda","ifsca"]}'::jsonb
FROM public.subjects s
CROSS JOIN (VALUES
  ('fsa-reserve-bank-of-india-act-1934-861d88ee', 'Reserve Bank of India Act, 1934'),
  ('fsa-banking-regulation-act-1949-079abfce', 'Banking Regulation Act, 1949'),
  ('fsa-deposit-insurance-and-credit-guarantee-corporation-act-1961-07509c8a', 'Deposit Insurance and Credit Guarantee Corporation Act, 1961'),
  ('fsa-insurance-act-1938-428c3e5e', 'Insurance Act, 1938'),
  ('fsa-insurance-regulatory-and-development-authority-act-1999-42ad0595', 'Insurance Regulatory and Development Authority Act, 1999'),
  ('fsa-pension-fund-regulatory-and-development-authority-act-2013-7fdc634c', 'Pension Fund Regulatory and Development Authority Act, 2013'),
  ('fsa-international-financial-services-centres-authority-act-2019-884ef801', 'International Financial Services Centres Authority Act, 2019'),
  ('fsa-foreign-exchange-management-act-1999-319e7411', 'Foreign Exchange Management Act, 1999'),
  ('fsa-competition-act-2002-a3d02e8b', 'Competition Act, 2002'),
  ('fsa-limited-liability-partnership-act-2008-d061afc6', 'Limited Liability Partnership Act, 2008'),
  ('fsa-payment-and-settlement-systems-act-2007-40326679', 'Payment and Settlement Systems Act, 2007'),
  ('fsa-credit-information-companies-regulation-act-2005-49c7254d', 'Credit Information Companies (Regulation) Act, 2005'),
  ('fsa-factoring-regulation-act-2011-066ba910', 'Factoring Regulation Act, 2011'),
  ('fsa-negotiable-instruments-act-1881-3891e79f', 'Negotiable Instruments Act, 1881'),
  ('fsa-insolvency-and-bankruptcy-code-2016-822c6604', 'Insolvency and Bankruptcy Code, 2016'),
  ('fsa-securitisation-and-reconstruction-of-financial-assets-and-enforcement-of-security-interest-act-2002-229f18c2', 'Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002'),
  ('fsa-recovery-of-debts-and-bankruptcy-act-1993-4167fea6', 'Recovery of Debts and Bankruptcy Act, 1993'),
  ('fsa-prevention-of-money-laundering-act-2002-37bcff0c', 'Prevention of Money-laundering Act, 2002'),
  ('fsa-securities-and-exchange-board-of-india-act-1992-5ed0bcb8', 'Securities and Exchange Board of India Act, 1992'),
  ('fsa-securities-contracts-regulation-act-1956-f8d67ee8', 'Securities Contracts (Regulation) Act, 1956'),
  ('fsa-depositories-act-1996-1df84a70', 'Depositories Act, 1996')
) AS v(slug, name)
WHERE s.slug = 'financial-sector-acts'
  AND NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.subject_id = s.id AND t.parent_topic_id IS NULL AND t.slug = v.slug);

INSERT INTO public.topics (subject_id, parent_topic_id, slug, name, level, is_active, metadata)
SELECT p.subject_id, p.id, v.slug, v.name, 'microtopic', true, '{"tier":"official","exams":["sebi","pfrda","ifsca"]}'::jsonb
FROM (VALUES
  ('fsa-reserve-bank-of-india-act-1934-861d88ee', 'fsa-rbi-act-constitution-central-board-and-governance-99cd7abf', 'RBI Act — Constitution, Central Board and governance'),
  ('fsa-reserve-bank-of-india-act-1934-861d88ee', 'fsa-rbi-act-note-issue-and-minimum-reserve-system-e05c6590', 'RBI Act — Note issue and minimum reserve system'),
  ('fsa-reserve-bank-of-india-act-1934-861d88ee', 'fsa-rbi-act-cash-reserve-ratio-and-penal-interest-under-s-42-b2e98728', 'RBI Act — Cash reserve ratio and penal interest under s.42'),
  ('fsa-reserve-bank-of-india-act-1934-861d88ee', 'fsa-rbi-act-monetary-policy-committee-and-inflation-targeting-0c02d0f7', 'RBI Act — Monetary Policy Committee and inflation targeting'),
  ('fsa-reserve-bank-of-india-act-1934-861d88ee', 'fsa-rbi-act-nbfc-regulation-under-chapter-iiib-ccecfce5', 'RBI Act — NBFC regulation under Chapter IIIB'),
  ('fsa-reserve-bank-of-india-act-1934-861d88ee', 'fsa-rbi-act-business-of-the-bank-and-lender-of-last-resort-9da17137', 'RBI Act — Business of the Bank and lender of last resort'),
  ('fsa-banking-regulation-act-1949-079abfce', 'fsa-br-act-definitions-and-permitted-business-33d31cb6', 'BR Act — Definitions and permitted business'),
  ('fsa-banking-regulation-act-1949-079abfce', 'fsa-br-act-capital-voting-rights-and-reserve-fund-9b96f0b5', 'BR Act — Capital, voting rights and reserve fund'),
  ('fsa-banking-regulation-act-1949-079abfce', 'fsa-br-act-loans-to-directors-and-restrictions-on-shareholding-8b0bb121', 'BR Act — Loans to directors and restrictions on shareholding'),
  ('fsa-banking-regulation-act-1949-079abfce', 'fsa-br-act-licensing-and-statutory-liquidity-ratio-e36b281f', 'BR Act — Licensing and statutory liquidity ratio'),
  ('fsa-banking-regulation-act-1949-079abfce', 'fsa-br-act-rbi-directions-removal-and-supersession-powers-5f4990b9', 'BR Act — RBI directions, removal and supersession powers'),
  ('fsa-banking-regulation-act-1949-079abfce', 'fsa-br-act-moratorium-amalgamation-and-co-operative-banks-d92f4bf2', 'BR Act — Moratorium, amalgamation and co-operative banks'),
  ('fsa-deposit-insurance-and-credit-guarantee-corporation-act-1961-07509c8a', 'fsa-dicgc-act-insured-banks-and-excluded-deposits-0f63be67', 'DICGC Act — Insured banks and excluded deposits'),
  ('fsa-deposit-insurance-and-credit-guarantee-corporation-act-1961-07509c8a', 'fsa-dicgc-act-deposit-insurance-cover-computation-a9b7942a', 'DICGC Act — Deposit insurance cover computation'),
  ('fsa-deposit-insurance-and-credit-guarantee-corporation-act-1961-07509c8a', 'fsa-dicgc-act-premium-payable-by-insured-banks-089b7f66', 'DICGC Act — Premium payable by insured banks'),
  ('fsa-deposit-insurance-and-credit-guarantee-corporation-act-1961-07509c8a', 'fsa-dicgc-act-payment-timelines-and-the-2021-amendment-5de0e63b', 'DICGC Act — Payment timelines and the 2021 amendment'),
  ('fsa-insurance-act-1938-428c3e5e', 'fsa-insurance-act-registration-capital-and-foreign-insurer-restrictions-26783931', 'Insurance Act — registration, capital and foreign insurer restrictions'),
  ('fsa-insurance-act-1938-428c3e5e', 'fsa-insurance-act-investments-loans-and-commission-controls-85c731fd', 'Insurance Act — investments, loans and commission controls'),
  ('fsa-insurance-act-1938-428c3e5e', 'fsa-insurance-act-assignment-and-nomination-under-ss-38-39-c2f8e7b2', 'Insurance Act — assignment and nomination under ss.38–39'),
  ('fsa-insurance-act-1938-428c3e5e', 'fsa-insurance-act-s-45-indisputability-and-s-64vb-premium-in-advance-bb5a2d40', 'Insurance Act — s.45 indisputability and s.64VB premium in advance'),
  ('fsa-insurance-act-1938-428c3e5e', 'fsa-insurance-act-surveyors-penalties-and-appeals-3451a64e', 'Insurance Act — surveyors, penalties and appeals'),
  ('fsa-insurance-regulatory-and-development-authority-act-1999-42ad0595', 'fsa-irda-act-establishment-composition-and-tenure-8cda2ef6', 'IRDA Act — establishment, composition and tenure'),
  ('fsa-insurance-regulatory-and-development-authority-act-1999-42ad0595', 'fsa-irda-act-duties-powers-and-functions-under-s-14-ed4cae4a', 'IRDA Act — duties, powers and functions under s.14'),
  ('fsa-insurance-regulatory-and-development-authority-act-1999-42ad0595', 'fsa-irda-act-funds-accounts-and-reports-06eac95d', 'IRDA Act — funds, accounts and reports'),
  ('fsa-insurance-regulatory-and-development-authority-act-1999-42ad0595', 'fsa-irda-act-central-government-control-and-advisory-committee-6feb8b5c', 'IRDA Act — Central Government control and advisory committee'),
  ('fsa-pension-fund-regulatory-and-development-authority-act-2013-7fdc634c', 'fsa-pfrda-act-constitution-composition-and-tenure-918d5c29', 'PFRDA Act — constitution, composition and tenure'),
  ('fsa-pension-fund-regulatory-and-development-authority-act-2013-7fdc634c', 'fsa-pfrda-act-scope-and-functions-of-the-authority-35af80ab', 'PFRDA Act — scope and functions of the Authority'),
  ('fsa-pension-fund-regulatory-and-development-authority-act-2013-7fdc634c', 'fsa-pfrda-act-national-pension-system-and-intermediaries-d1d3b662', 'PFRDA Act — National Pension System and intermediaries'),
  ('fsa-pension-fund-regulatory-and-development-authority-act-2013-7fdc634c', 'fsa-pfrda-act-penalties-adjudication-and-offences-bcd5f2c2', 'PFRDA Act — penalties, adjudication and offences'),
  ('fsa-pension-fund-regulatory-and-development-authority-act-2013-7fdc634c', 'fsa-pfrda-act-appeals-funds-and-oversight-e53185fa', 'PFRDA Act — appeals, funds and oversight'),
  ('fsa-international-financial-services-centres-authority-act-2019-884ef801', 'fsa-ifsca-act-application-definitions-and-sez-linkage-ea78d532', 'IFSCA Act — application, definitions and SEZ linkage'),
  ('fsa-international-financial-services-centres-authority-act-2019-884ef801', 'fsa-ifsca-act-composition-tenure-and-meetings-7d57cbc8', 'IFSCA Act — composition, tenure and meetings'),
  ('fsa-international-financial-services-centres-authority-act-2019-884ef801', 'fsa-ifsca-act-functions-and-powers-under-first-schedule-acts-4b7dd741', 'IFSCA Act — functions and powers under First Schedule Acts'),
  ('fsa-international-financial-services-centres-authority-act-2019-884ef801', 'fsa-ifsca-act-finance-foreign-currency-and-accountability-5e4b0a57', 'IFSCA Act — finance, foreign currency and accountability'),
  ('fsa-international-financial-services-centres-authority-act-2019-884ef801', 'fsa-ifsca-act-central-government-powers-and-overriding-provisions-95c50cb8', 'IFSCA Act — Central Government powers and overriding provisions'),
  ('fsa-foreign-exchange-management-act-1999-319e7411', 'fsa-fema-residential-status-under-s-2-v-a6cc6289', 'FEMA — residential status under s.2(v)'),
  ('fsa-foreign-exchange-management-act-1999-319e7411', 'fsa-fema-current-and-capital-account-transactions-s-5-s-6-and-lrs-cea4e175', 'FEMA — current and capital account transactions (s.5, s.6) and LRS'),
  ('fsa-foreign-exchange-management-act-1999-319e7411', 'fsa-fema-authorised-persons-and-rbi-directions-s-10-to-s-12-6a68c4c3', 'FEMA — authorised persons and RBI directions (s.10 to s.12)'),
  ('fsa-foreign-exchange-management-act-1999-319e7411', 'fsa-fema-penalties-enforcement-and-compounding-s-13-to-s-15-5d4c30c2', 'FEMA — penalties, enforcement and compounding (s.13 to s.15)'),
  ('fsa-foreign-exchange-management-act-1999-319e7411', 'fsa-fema-adjudication-and-appeals-f3c94c7a', 'FEMA — adjudication and appeals'),
  ('fsa-foreign-exchange-management-act-1999-319e7411', 'fsa-fema-civil-character-and-contrast-with-fera-05cf5ce6', 'FEMA — civil character and contrast with FERA'),
  ('fsa-competition-act-2002-a3d02e8b', 'fsa-competition-act-anti-competitive-agreements-s-3-6365e41c', 'Competition Act — anti-competitive agreements (s.3)'),
  ('fsa-competition-act-2002-a3d02e8b', 'fsa-competition-act-abuse-of-dominant-position-s-4-d2e98375', 'Competition Act — abuse of dominant position (s.4)'),
  ('fsa-competition-act-2002-a3d02e8b', 'fsa-competition-act-combinations-and-merger-control-s-5-s-6-d04b44db', 'Competition Act — combinations and merger control (s.5, s.6)'),
  ('fsa-competition-act-2002-a3d02e8b', 'fsa-competition-act-cci-composition-and-inquiry-process-a6de3bbc', 'Competition Act — CCI composition and inquiry process'),
  ('fsa-competition-act-2002-a3d02e8b', 'fsa-competition-act-penalties-and-lesser-penalty-s-27-s-46-be28b1f6', 'Competition Act — penalties and lesser penalty (s.27, s.46)'),
  ('fsa-competition-act-2002-a3d02e8b', 'fsa-competition-act-settlement-commitment-and-appeals-60379d10', 'Competition Act — settlement, commitment and appeals'),
  ('fsa-limited-liability-partnership-act-2008-d061afc6', 'fsa-llp-act-partners-designated-partners-and-mutual-rights-2fc4debb', 'LLP Act — partners, designated partners and mutual rights'),
  ('fsa-limited-liability-partnership-act-2008-d061afc6', 'fsa-llp-act-incorporation-legal-status-and-liability-4c17408f', 'LLP Act — incorporation, legal status and liability'),
  ('fsa-limited-liability-partnership-act-2008-d061afc6', 'fsa-llp-act-conversion-into-llp-9695455d', 'LLP Act — conversion into LLP'),
  ('fsa-limited-liability-partnership-act-2008-d061afc6', 'fsa-llp-act-small-llp-filings-and-decriminalisation-ea45d566', 'LLP Act — small LLP, filings and decriminalisation'),
  ('fsa-limited-liability-partnership-act-2008-d061afc6', 'fsa-llp-act-winding-up-and-dissolution-81af7b12', 'LLP Act — winding up and dissolution'),
  ('fsa-payment-and-settlement-systems-act-2007-40326679', 'fsa-pss-act-authorisation-revocation-and-appeal-s-4-s-9-s-34-6522ce78', 'PSS Act — authorisation, revocation and appeal (s.4–s.9, s.34)'),
  ('fsa-payment-and-settlement-systems-act-2007-40326679', 'fsa-pss-act-designated-authority-and-payments-regulatory-board-s-3-42d69444', 'PSS Act — designated authority and Payments Regulatory Board (s.3)'),
  ('fsa-payment-and-settlement-systems-act-2007-40326679', 'fsa-pss-act-settlement-finality-netting-and-customer-funds-s-23-s-23a-558d449e', 'PSS Act — settlement finality, netting and customer funds (s.23, s.23A)'),
  ('fsa-payment-and-settlement-systems-act-2007-40326679', 'fsa-pss-act-rbi-directions-and-oversight-s-17-8adadd3b', 'PSS Act — RBI directions and oversight (s.17)'),
  ('fsa-payment-and-settlement-systems-act-2007-40326679', 'fsa-pss-act-offences-penalties-and-eft-dishonour-s-25-s-30-1628f8d5', 'PSS Act — offences, penalties and EFT dishonour (s.25–s.30)'),
  ('fsa-credit-information-companies-regulation-act-2005-49c7254d', 'fsa-cicra-registration-and-minimum-capital-of-credit-information-companies-4adf6a55', 'CICRA — registration and minimum capital of credit information companies'),
  ('fsa-credit-information-companies-regulation-act-2005-49c7254d', 'fsa-cicra-credit-institutions-membership-and-specified-users-68d8c34e', 'CICRA — credit institutions, membership and specified users'),
  ('fsa-credit-information-companies-regulation-act-2005-49c7254d', 'fsa-cicra-privacy-principles-and-unauthorised-access-88b9d2f2', 'CICRA — privacy principles and unauthorised access'),
  ('fsa-credit-information-companies-regulation-act-2005-49c7254d', 'fsa-cicra-correction-of-credit-information-and-dispute-timelines-69b7c986', 'CICRA — correction of credit information and dispute timelines'),
  ('fsa-credit-information-companies-regulation-act-2005-49c7254d', 'fsa-cicra-offences-and-rbi-penalties-1100a1bc', 'CICRA — offences and RBI penalties'),
  ('fsa-factoring-regulation-act-2011-066ba910', 'fsa-factoring-act-factoring-business-assignor-debtor-and-receivables-78348f29', 'Factoring Act — factoring business, assignor, debtor and receivables'),
  ('fsa-factoring-regulation-act-2011-066ba910', 'fsa-factoring-act-registration-of-factors-and-rbi-powers-7084663c', 'Factoring Act — registration of factors and RBI powers'),
  ('fsa-factoring-regulation-act-2011-066ba910', 'fsa-factoring-act-assignment-notice-and-rights-of-the-factor-1e053e13', 'Factoring Act — assignment, notice and rights of the factor'),
  ('fsa-factoring-regulation-act-2011-066ba910', 'fsa-factoring-act-registration-of-assignments-with-cersai-and-treds-072f8843', 'Factoring Act — registration of assignments with CERSAI and TReDS'),
  ('fsa-factoring-regulation-act-2011-066ba910', 'fsa-factoring-act-penalties-2fddcc92', 'Factoring Act — penalties'),
  ('fsa-negotiable-instruments-act-1881-3891e79f', 'fsa-ni-act-promissory-notes-bills-of-exchange-and-cheques-4375664f', 'NI Act — promissory notes, bills of exchange and cheques'),
  ('fsa-negotiable-instruments-act-1881-3891e79f', 'fsa-ni-act-holder-holder-in-due-course-and-negotiation-7e1a816c', 'NI Act — holder, holder in due course and negotiation'),
  ('fsa-negotiable-instruments-act-1881-3891e79f', 'fsa-ni-act-maturity-and-days-of-grace-d0a1b497', 'NI Act — maturity and days of grace'),
  ('fsa-negotiable-instruments-act-1881-3891e79f', 'fsa-ni-act-crossing-of-cheques-and-banker-protection-bc226f72', 'NI Act — crossing of cheques and banker protection'),
  ('fsa-negotiable-instruments-act-1881-3891e79f', 'fsa-ni-act-cheque-dishonour-under-s-138-and-complaint-timelines-24c62cde', 'NI Act — cheque dishonour under s.138 and complaint timelines'),
  ('fsa-negotiable-instruments-act-1881-3891e79f', 'fsa-ni-act-interim-compensation-and-appeal-deposit-s-143a-s-148-25c1830e', 'NI Act — interim compensation and appeal deposit (s.143A, s.148)'),
  ('fsa-insolvency-and-bankruptcy-code-2016-822c6604', 'fsa-ibc-cirp-initiation-default-threshold-and-applicants-s-4-7-9-10-7f5412f4', 'IBC — CIRP initiation, default threshold and applicants (s.4, 7, 9, 10)'),
  ('fsa-insolvency-and-bankruptcy-code-2016-822c6604', 'fsa-ibc-moratorium-irp-rp-and-coc-decision-making-f56b7503', 'IBC — moratorium, IRP/RP and CoC decision-making'),
  ('fsa-insolvency-and-bankruptcy-code-2016-822c6604', 'fsa-ibc-cirp-timelines-resolution-plan-and-s-29a-ineligibility-f0234a1a', 'IBC — CIRP timelines, resolution plan and s.29A ineligibility'),
  ('fsa-insolvency-and-bankruptcy-code-2016-822c6604', 'fsa-ibc-liquidation-waterfall-under-s-53-8a25ca49', 'IBC — liquidation waterfall under s.53'),
  ('fsa-insolvency-and-bankruptcy-code-2016-822c6604', 'fsa-ibc-pre-packaged-insolvency-for-msmes-and-ibbi-11958b40', 'IBC — pre-packaged insolvency for MSMEs and IBBI'),
  ('fsa-securitisation-and-reconstruction-of-financial-assets-and-enforcement-of-security-interest-act-2002-229f18c2', 'fsa-sarfaesi-s-13-demand-notice-representation-and-enforcement-measures-a2da9bf8', 'SARFAESI — s.13 demand notice, representation and enforcement measures'),
  ('fsa-securitisation-and-reconstruction-of-financial-assets-and-enforcement-of-security-interest-act-2002-229f18c2', 'fsa-sarfaesi-consortium-consent-s-13-9-and-cmm-dm-assistance-s-14-c946b8b5', 'SARFAESI — consortium consent (s.13(9)) and CMM/DM assistance (s.14)'),
  ('fsa-securitisation-and-reconstruction-of-financial-assets-and-enforcement-of-security-interest-act-2002-229f18c2', 'fsa-sarfaesi-drt-application-s-17-and-drat-pre-deposit-s-18-cabe157d', 'SARFAESI — DRT application (s.17) and DRAT pre-deposit (s.18)'),
  ('fsa-securitisation-and-reconstruction-of-financial-assets-and-enforcement-of-security-interest-act-2002-229f18c2', 'fsa-sarfaesi-exclusions-under-s-31-and-applicability-9d414489', 'SARFAESI — exclusions under s.31 and applicability'),
  ('fsa-securitisation-and-reconstruction-of-financial-assets-and-enforcement-of-security-interest-act-2002-229f18c2', 'fsa-sarfaesi-asset-reconstruction-companies-and-cersai-39fcd4cb', 'SARFAESI — asset reconstruction companies and CERSAI'),
  ('fsa-recovery-of-debts-and-bankruptcy-act-1993-4167fea6', 'fsa-rdb-act-drt-jurisdiction-and-pecuniary-threshold-21a137a0', 'RDB Act — DRT jurisdiction and pecuniary threshold'),
  ('fsa-recovery-of-debts-and-bankruptcy-act-1993-4167fea6', 'fsa-rdb-act-original-application-procedure-and-limitation-d67663ae', 'RDB Act — original application procedure and limitation'),
  ('fsa-recovery-of-debts-and-bankruptcy-act-1993-4167fea6', 'fsa-rdb-act-drat-appeal-and-pre-deposit-e3ce98e7', 'RDB Act — DRAT appeal and pre-deposit'),
  ('fsa-recovery-of-debts-and-bankruptcy-act-1993-4167fea6', 'fsa-rdb-act-recovery-certificate-and-recovery-officer-296b5aca', 'RDB Act — recovery certificate and recovery officer'),
  ('fsa-prevention-of-money-laundering-act-2002-37bcff0c', 'fsa-pmla-offence-of-money-laundering-and-punishment-s-3-s-4-6b07b190', 'PMLA — offence of money laundering and punishment (s.3, s.4)'),
  ('fsa-prevention-of-money-laundering-act-2002-37bcff0c', 'fsa-pmla-scheduled-offences-and-proceeds-of-crime-f5f7d7ab', 'PMLA — scheduled offences and proceeds of crime'),
  ('fsa-prevention-of-money-laundering-act-2002-37bcff0c', 'fsa-pmla-reporting-entities-record-keeping-and-fiu-ind-39142814', 'PMLA — reporting entities, record-keeping and FIU-IND'),
  ('fsa-prevention-of-money-laundering-act-2002-37bcff0c', 'fsa-pmla-provisional-attachment-and-adjudicating-authority-2705095f', 'PMLA — provisional attachment and Adjudicating Authority'),
  ('fsa-prevention-of-money-laundering-act-2002-37bcff0c', 'fsa-pmla-arrest-bail-s-45-appellate-tribunal-and-s-66-10f83185', 'PMLA — arrest, bail (s.45), Appellate Tribunal and s.66'),
  ('fsa-securities-and-exchange-board-of-india-act-1992-5ed0bcb8', 'fsa-sebi-act-establishment-board-composition-and-functions-117fb99d', 'SEBI Act — establishment, Board composition and functions'),
  ('fsa-securities-and-exchange-board-of-india-act-1992-5ed0bcb8', 'fsa-sebi-act-directions-interim-measures-cis-and-registration-d5e8f953', 'SEBI Act — directions, interim measures, CIS and registration'),
  ('fsa-securities-and-exchange-board-of-india-act-1992-5ed0bcb8', 'fsa-sebi-act-chapter-via-penalties-and-adjudication-1665ac49', 'SEBI Act — Chapter VIA penalties and adjudication'),
  ('fsa-securities-and-exchange-board-of-india-act-1992-5ed0bcb8', 'fsa-sebi-act-sat-appeals-settlement-recovery-and-offences-5dc5f8e7', 'SEBI Act — SAT appeals, settlement, recovery and offences'),
  ('fsa-securities-contracts-regulation-act-1956-f8d67ee8', 'fsa-scra-definitions-of-securities-derivatives-spot-delivery-and-options-c6d22c82', 'SCRA — definitions of securities, derivatives, spot delivery and options'),
  ('fsa-securities-contracts-regulation-act-1956-f8d67ee8', 'fsa-scra-recognition-bye-laws-and-control-of-stock-exchanges-d57338bc', 'SCRA — recognition, bye-laws and control of stock exchanges'),
  ('fsa-securities-contracts-regulation-act-1956-f8d67ee8', 'fsa-scra-contracts-in-notified-areas-and-legality-of-derivatives-6c68e473', 'SCRA — contracts in notified areas and legality of derivatives'),
  ('fsa-securities-contracts-regulation-act-1956-f8d67ee8', 'fsa-scra-listing-delisting-appeals-and-minimum-public-shareholding-9547a88f', 'SCRA — listing, delisting appeals and minimum public shareholding'),
  ('fsa-securities-contracts-regulation-act-1956-f8d67ee8', 'fsa-scra-penalties-and-adjudication-under-s-23-to-s-23h-4a18aa02', 'SCRA — penalties and adjudication under s.23 to s.23H'),
  ('fsa-depositories-act-1996-1df84a70', 'fsa-depositories-act-depository-participant-and-beneficial-owner-9c56d888', 'Depositories Act — depository, participant and beneficial owner'),
  ('fsa-depositories-act-1996-1df84a70', 'fsa-depositories-act-option-to-hold-transfer-fungibility-and-opt-out-61f0883c', 'Depositories Act — option to hold, transfer, fungibility and opt-out'),
  ('fsa-depositories-act-1996-1df84a70', 'fsa-depositories-act-rights-of-depository-and-bo-pledge-and-indemnity-60813add', 'Depositories Act — rights of depository and BO, pledge and indemnity'),
  ('fsa-depositories-act-1996-1df84a70', 'fsa-depositories-act-penalties-sebi-powers-and-appeals-eab300cd', 'Depositories Act — penalties, SEBI powers and appeals')
) AS v(parent_slug, slug, name)
JOIN public.topics p ON p.slug = v.parent_slug
JOIN public.subjects s ON s.id = p.subject_id AND s.slug = 'financial-sector-acts'
WHERE NOT EXISTS (SELECT 1 FROM public.topics t WHERE t.subject_id = p.subject_id AND t.slug = v.slug);

-- verify: expect topic 21, microtopic 105, orphan 0
SELECT t.level, count(*) AS n, count(*) FILTER (WHERE t.metadata ? 'exams') AS with_exams,
       count(*) FILTER (WHERE t.level='microtopic' AND t.parent_topic_id IS NULL) AS orphan
FROM public.topics t JOIN public.subjects s ON s.id = t.subject_id
WHERE s.slug = 'financial-sector-acts' GROUP BY 1 ORDER BY 1;

COMMIT;
