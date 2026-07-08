-- 228_pyq_upsc_cse_2025_prelims_csat_canonical.sql
-- Injects the UPSC Civil Services Examination 2025 Prelims Paper II (CSAT)
-- official question paper as a canonical PYQ source.
--
-- Canonical designation lives at the source/paper level via
-- source_type = 'official'. Trust lifecycle stays 'pending' because the
-- provided document has NO exact paper-source URL / source_document_id and
-- NO answer key: promoting to 'verified' without exact provenance would let
-- verified_pyq_papers() surface a verified paper backed only by the UPSC
-- homepage (checkpost P1). So source AND paper are trust_status='pending';
-- question/option/stimulus rows are reviewer_status='pending' and NO correct
-- option is asserted (correct_option_id = null, is_correct = false). Per
-- migration 032/186/223 posture, aspirant-facing reads flow through the mock
-- projection, which gates on reviewer_status='verified' AND exactly one
-- correct option (app/backend/app/admin/pyq_mock_projection.py). An operator
-- attaches the exact official paper (source_url / source_document_id), adds
-- and verifies the answer key, and runs the review lifecycle to 'verified'
-- before this paper reaches learner surfaces. Verdicts come from operator
-- review, never fabricated here (determinism > heuristics).
--
-- Cycle reuse (checkpost P1): the 2025 UPSC CSE cycle is resolved by
-- (exam_id, year) and reused when present (the demo seed creates it as
-- 'CSE 2025'); only created when absent, using the seed's deterministic id so
-- a later seed run no-ops cleanly. A guard asserts exactly one 2025 cycle.
--
-- Idempotent: every insert is keyed on a deterministic UUID with
-- ON CONFLICT (id) DO NOTHING, and the exam cycle/phase upserts are guarded,
-- so re-running the migration is a no-op.
--
-- Hashes (normalized_question_hash / normalized_option_hash) are computed
-- with the same canonical form as app/backend/app/exam_intelligence/
-- option_normalize.py so these rows dedupe consistently against the importer.

do $$
declare
  v_exam_id uuid;
  v_cycle_id uuid;
  v_phase_id uuid;
begin
  select id into v_exam_id from public.exams where slug = 'upsc-cse';
  if v_exam_id is null then
    raise exception 'exam slug upsc-cse not found; seed migration 110 must run first';
  end if;

  -- Exam cycle: reuse the existing UPSC CSE 2025 cycle if one already exists
  -- for this exam+year (the demo seed creates it as 'CSE 2025'); create one
  -- only when absent, reusing the seed's deterministic id so a later seed run
  -- no-ops via ON CONFLICT (id). Guarantees exactly one 2025 cycle.
  select id into v_cycle_id
    from public.exam_cycles
    where exam_id = v_exam_id and year = 2025
    order by created_at asc
    limit 1;

  if v_cycle_id is null then
    insert into public.exam_cycles
      (id, exam_id, year, cycle_name, status, notification_date,
       application_start, application_end, exam_start, source_url)
    values
      ('a0000003-0000-0000-0000-000000000025', v_exam_id, 2025, 'CSE 2025',
       'active', date '2025-01-22', date '2025-01-22', date '2025-02-11',
       date '2025-05-25', 'https://upsc.gov.in/')
    on conflict (id) do nothing;

    select id into v_cycle_id
      from public.exam_cycles
      where exam_id = v_exam_id and year = 2025
      order by created_at asc
      limit 1;
  end if;

  -- Exam phase: Prelims Paper II (CSAT). 80 items, 200 marks, 2 hours.
  insert into public.exam_phases
    (exam_id, exam_cycle_id, phase_name, phase_slug, phase_order, mode,
     duration_mins, total_questions, total_marks, negative_marking, status)
  values
    (v_exam_id, v_cycle_id, 'Prelims Paper II (CSAT)', 'prelims-csat', 2,
     'offline', 120, 80, 200, 'one-third of 2.5 marks per wrong answer', 'completed')
  on conflict (exam_id, exam_cycle_id, phase_slug) where exam_cycle_id is not null
  do update set updated_at = now()
  returning id into v_phase_id;

  -- Canonical official source (trust pending until exact provenance supplied)
  insert into public.pyq_sources (id, exam_id, source_type, source_url, title, trust_status, metadata)
  values ('fceab600-0aed-5052-ab10-89ba36934908', v_exam_id, 'official',
          'https://upsc.gov.in/examinations/previous-question-papers',
          'UPSC CSE 2025 Prelims Paper II (CSAT) — Official Question Paper',
          'pending', jsonb_build_object('paper','UPSC CSE 2025 Prelims Paper II (CSAT)','exam_slug','upsc-cse','canonical', true, 'answer_key_present', false, 'provenance_pending', true))
  on conflict (id) do nothing;

  -- Canonical paper. source_url left null (no exact paper URL in source doc —
  -- operator attaches source_url / source_document_id at verification time).
  insert into public.pyq_papers
    (id, pyq_source_id, exam_id, exam_cycle_id, exam_phase_id, year, paper_date,
     paper_code, source_url, source_type, trust_status, metadata)
  values ('505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'fceab600-0aed-5052-ab10-89ba36934908', v_exam_id, v_cycle_id, v_phase_id, 2025,
          date '2025-05-25', 'GS-PAPER-II-CSAT', null, 'official',
          'pending', jsonb_build_object('title','UPSC CSE 2025 Prelims Paper II (CSAT)','total_questions',80,'total_marks',200,'canonical',true,'answer_key_present',false,'provenance_pending',true,'note','Injected verbatim from official question paper docx. Trust pending: operator must attach the exact official CSAT 2025 paper (source_url or source_document_id) and verify the answer key before promotion to verified.'))
  on conflict (id) do nothing;
end $$;

-- ── Stimuli (shared reading-comprehension passages, verbatim) ─────────────
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('93417197-9b21-5e01-9460-fb5abdac2aa4', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'In our country, regrettably, teaching and learning for the examination have been our forte but the new demands of society and the future of work require critical and independent thinking, learning through doing, asking questions from multiple disciplinary perspectives on the same issue, using evidence for building arguments, and reflecting and articulation. Higher education should not “either be a mere servant of the government policy or a passive respondent to public mood.” Higher learning is all about how to think rather than what to think. Teaching has to be re-invented.', 'en', 1, 'pending', jsonb_build_object('passage_key','p_higher_ed'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('99cb64a4-353b-5d18-beb6-efbc30e55eab', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'In our country, handlooms are equated with a culture that ensures a continuity of tradition. This idea has become part of the public policy-framing and provides a legitimate basis for the State to support the sector. But the notion of tradition as a single, linear entity is being strongly contested today. The narratives dominant in defining culture/tradition in a particular way are seen to have emerged as the identities and histories of large sections. The discounted and, at times, forcibly stifled identities are fighting for their rightful place in history. Against this backdrop, when we promote handloom as a traditional industry, it is not surprising that large sections of our population choose to ignore it.', 'en', 2, 'pending', jsonb_build_object('passage_key','p_handloom'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('08dcce7f-1512-56ff-b2f3-b1186b76c1a3', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'Each State in India faces a distinctive set of challenges regarding the impact of warming, but also offers its own set of opportunities for reducing emissions depending on its natural resources. For example, coastal States need to take action to protect their shores from sea level rise, districts that are drier need to prepare for variable monsoon precipitation. Himalayan regions have their own unique challenges, and selected parts of peninsular India and offshore areas offer great opportunities for harnessing wind power. These various aspects need to be considered for developing clear and sustainable goals for the future.', 'en', 3, 'pending', jsonb_build_object('passage_key','p_climate_states'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('f670371f-c1e5-5dfa-b961-3dffebe4084e', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'If the social inequality is the most acutely felt social problem in India, insecurity, more than poverty, is the most acutely felt economic problem. Besides those below the official poverty line, even those just over the poverty line are subject to multiple economic insecurities of various kinds (due to wealth and/or health risks, market fluctuations, job-related uncertainties). Many Government policies are actually intended towards mitigating these insecurities.', 'en', 4, 'pending', jsonb_build_object('passage_key','p_insecurity'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('710965b5-51f4-54cc-ae11-8b98719b6939', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'Maintaining an ecosystem just to conserve biodiversity will affect its commercial potential as well as the livelihoods dependent on the ecosystem. There is also a conflict between using an ecosystem only for livelihoods, for commercial exploitation, or strictly for conservation. Deforestation caused due to commercial exploitation will lead to indirect harm like floods, siltation problems and microclimatic instability, apart from adversely affecting livelihoods dependent on forests. These conflicts are particularly acute in developing countries where the dependence of people on the ecosystem is significant, and commercial exploitation has the potential to boost national income.', 'en', 5, 'pending', jsonb_build_object('passage_key','p_ecosystem'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('2e4ba4d4-6094-54dc-8ddf-995cf6b5c20b', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'The history of renewable energy suggests there is a steep learning curve, meaning that, as more is produced, costs fall rapidly because of economies of scale and learning by doing. The firms’ green innovation is path-dependent: the more a firm does, the more it is likely to do in the future. The strongest evidence for this is the collapse in the price of solar energy, which became about 90% cheaper during the 2010s, repeatedly beating forecasts. Moving early and gradually gives economies more time to adjust, allowing them to reap the benefits of path-dependent green investment without much disruption. A late, more chaotic transition is costlier.', 'en', 6, 'pending', jsonb_build_object('passage_key','p_renewable'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('085ef831-dde8-5f15-a3df-8b5be6685d8e', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'A single number for inflation is an aggregate across different commodities and services – the price rise differs for different items of consumption. So, the single number is arrived at by assigning weights to different commodities and services. For WPI, the weights in production are used; for CPI, the consumption basket is used. But people are not homogeneous. The consumption basket is vastly different for the poor, the middle classes, and the rich. Hence, the CPI is different for each of these classes and a composite index requires averaging the baskets.', 'en', 7, 'pending', jsonb_build_object('passage_key','p_inflation'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('cb3c57db-6e9c-5c2e-a18c-3ff079b5373d', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'Trust stands commonly defined as being vulnerable to others. Entrepreneurship implies trust in others and willingness to expose oneself to betrayal. Trust in expert systems is the essence of globalizing behaviors; trust itself emerges as a super-commodity in the social market and defines the characteristics of goods and services in a global market. Trusting conduct also means holding others in good esteem, and an optimism that they are, or will be, competent in certain respects.', 'en', 8, 'pending', jsonb_build_object('passage_key','p_trust'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('7d7cdf44-24a2-5a4e-beaa-c9451d8eb5bb', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'There has been no democracy that has grown economically without corporate capitalism. It helps in modernizing the economy and enabling the transition from rural to urban, and agriculture to industry and services, which are inevitable with growth. It generates jobs — and there is no other way to fix a country’s unemployment challenge without a further impetus to private business. Big companies can operate on a large scale and become competitive both domestically and externally. A vibrant corporate capitalist base also leads to additional revenues for the State — which in turn, can be used for greater welfare for the marginalized and creating a more level playing field in terms of opportunities.', 'en', 9, 'pending', jsonb_build_object('passage_key','p_corporate'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('f42e041a-8854-55cf-bb81-156974b33fce', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'A network of voluntary associations stands as a buffer between the relatively powerless individual and the potentially powerful State.', 'en', 10, 'pending', jsonb_build_object('passage_key','p_voluntary'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('4953001e-f983-5f47-b860-c912453947a5', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'It is hard to predict how changes in the climate and the atmosphere’s chemistry will affect the prevalence and virulence of agricultural diseases. But there is a risk that such changes will make some plant infections more common in all climatic zones, perhaps catastrophically so. Part of the problem is that centuries of selective breeding have refined the genomes of most high-value crops. They are spectacular at growing in today’s conditions but genetic variations that are not immediately useful to them have been bred out. This is good for yields but bad for coping with changes. A minor disease or even an unknown one could suddenly rampage through a genetically honed crop.', 'en', 11, 'pending', jsonb_build_object('passage_key','p_agri_disease'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('f7806d43-1c8a-5fa4-abcc-af6ad8ab2a1b', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'A good statesman, like any other sensible human being, learns more from his opponents than from his fervent supporters. For his supporters will push him to disaster unless his opponents show him where the dangers are. So if he is wise he will often pray to be delivered from his friends, because they will ruin him. But, though it hurts, he ought also to pray never to be left without opponents; for they keep him on the path of reason and good sense. The national unity of free people depends upon a sufficiently even balance of political power to make it impracticable for the administration to be arbitrary and for opposition to be revolutionary and irreconcilable.', 'en', 12, 'pending', jsonb_build_object('passage_key','p_statesman'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('2beb3085-faec-5c50-89d4-4bbf61b59ea3', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'Over the next 30 years, many countries are promising to move to net-zero carbon, implying that household emissions will have to be cut to close to nothing. A leading climate scientist reckons that, at best, half the reduction might be achieved through demand-side measures, such as behavioural changes by individuals and households. And even that would require companies and governments to provide more incentives to change through supply-side investments to make low-carbon options cheaper and more widely available.', 'en', 13, 'pending', jsonb_build_object('passage_key','p_netzero'))
on conflict (id) do nothing;
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status, metadata)
values ('2de8943a-ba59-52f2-a531-2a75d9d73d1f', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 'passage', 'In only 50 years, the world’s consumption of raw materials has nearly quadrupled, to more than 100 billion tons. Less than 9% of this is reused. Batteries of old vehicles contain materials such as lithium, cobalt, manganese and nickel that are pricey and can be hard to obtain. Supply chains are long and complicated. Buyers’ risks are being aggravated by their suppliers’ poor environmental and labour standards. Reusing materials makes sense. Once batteries reach the ends of their lives, they should go back to a factory where their ingredients can be recovered and put into new batteries.', 'en', 14, 'pending', jsonb_build_object('passage_key','p_circular'))
on conflict (id) do nothing;

-- ── Questions, options, and question↔stimulus links ──────────────────────
insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('108c4a0e-dd96-5015-9e38-6a63b2cb5ad5', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 1, 'Which one of the following statements best reflects the central idea conveyed by the passage?', 'c88e239ff0d0714a105f41c95eb4c94f5df28ec31d544478d49192e3a8f7cb73',
        'mcq', null, 'pending', 1, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7f688b41-db90-57ec-bf06-e212e0b25b33', '108c4a0e-dd96-5015-9e38-6a63b2cb5ad5', 'A', 'India does not have enough resources for promoting quality education in its universities.', '14869c7dc72c6330dae64b4f58c7cde4c1ecfbbc43b604f6e27f6e49971446c4', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('d541bb72-d7d8-5d6a-b8e0-3b05c7450475', '108c4a0e-dd96-5015-9e38-6a63b2cb5ad5', 'B', 'The institutions of higher learning in the country should not be under the control of the Government.', 'ff5ab22ff20e1f5c79a20bb857a55768378413cb8545ca37ff1e9a5320a01204', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('e7552742-db4a-57fa-9b73-de667829ba70', '108c4a0e-dd96-5015-9e38-6a63b2cb5ad5', 'C', 'Classroom approach to higher education should be done away with.', '28ebf791bdcb8c076681d268e9ded4b614513d56ca95327b0d70b6bf833b51fd', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('cecf377d-7679-578a-bad5-dd7fef80aa54', '108c4a0e-dd96-5015-9e38-6a63b2cb5ad5', 'D', 'Classroom needs to be reimagined and teaching to be re-invented.', 'e6f47550cb12551bfeac1f0caa77795b0e02dbc28fcb12d69c14a1a41ee47e97', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('698f4f68-d953-5411-87e7-48054a0bd677', '108c4a0e-dd96-5015-9e38-6a63b2cb5ad5', '93417197-9b21-5e01-9460-fb5abdac2aa4', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('59e8ec00-7ab1-5146-bf7a-f769f784f17c', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 2, 'With reference to the above passage, the following assumptions have been made: I. Higher education is a constantly evolving subject that needs to align towards new developments in all spheres of society. II. In our country, sufficient funds are not allocated for promoting higher education. Which of the above assumptions is/are valid?', 'c2d89cd98558d2e003860cd39f8a5d3ea323949e880a70ef2a97d79aa1a7b661',
        'mcq', null, 'pending', 2, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f88a5fa7-460e-5c65-a419-0ab49b33d7f0', '59e8ec00-7ab1-5146-bf7a-f769f784f17c', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('42d135f4-74ea-56f6-ad88-2d30fc4ae35b', '59e8ec00-7ab1-5146-bf7a-f769f784f17c', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('12f2a815-1815-5a28-89b6-2029797396ab', '59e8ec00-7ab1-5146-bf7a-f769f784f17c', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9615182c-4f9b-5872-a6df-309d0987f987', '59e8ec00-7ab1-5146-bf7a-f769f784f17c', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('112646f1-38a5-53ec-a772-1f9abde0797e', '59e8ec00-7ab1-5146-bf7a-f769f784f17c', '93417197-9b21-5e01-9460-fb5abdac2aa4', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('55f57180-512f-596a-b7d3-ea6160f1e272', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 3, 'Which one of the following statements best reflects the crux of the passage?', '83afc8e08a55ba1b2720cb2d48d896966889e28a85f4f3d904e2d401267add26',
        'mcq', null, 'pending', 3, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false,'missing_stimulus',true,'source_passage_absent',true,'missing_stimulus_reason','Passage-2 (animal- vs plant-based protein) for items 3–4 was absent from the source document.'))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('0413ab87-4c55-5dc8-af97-49f62e1ff5ba', '55f57180-512f-596a-b7d3-ea6160f1e272', 'A', 'There is an urgent need for a public policy to promote the consumption of cereal-based foods in wealthier societies.', 'b92285fc244243696af8865d95c95265f4ca0456b23c671d7dfd846c0a609878', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('bcd2a64f-33ca-561c-9dd0-37dc677f6953', '55f57180-512f-596a-b7d3-ea6160f1e272', 'B', 'Animal-based food is far less efficient than grain/plant-based food in terms of production and utilization.', '4bb0fcffc34c5c51bb3817935e9685154e53ae56b03cd98b29334a5183561e15', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('d14c1590-5eeb-540f-bdcc-0722f23cf06a', '55f57180-512f-596a-b7d3-ea6160f1e272', 'C', 'Plant-based protein should replace the animal-based protein in our daily diets.', 'fb7715e5c3b0658d37a9e5bf54337a9e22b49aa86f867a19928c6279d47d6243', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a81f873e-fb47-5887-8b6f-821c59400be0', '55f57180-512f-596a-b7d3-ea6160f1e272', 'D', 'Inequality in food production and consumption is inevitable in any fast changing society.', '7dc3cf3382ad3a5996df69bcf387b8398c1b0dec17c044df24762f22d461b7ca', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('70207b87-6621-5341-82e2-01b0f629c952', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 4, 'With reference to the above passage, the following assumptions have been made: I. The food manufacturing and processing industries in every country should align their objectives and processes in accordance with the changing needs of the societies. II. Wealthier societies tend to incur great loss of calories of food materials due to indirect utilization of their agricultural produce. Which of the above assumptions is/are valid?', '1f71d08d51bf219fda9beef7cde33bc96cc8cde8cc82d8924aaa09fdf156ecd1',
        'mcq', null, 'pending', 4, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false,'missing_stimulus',true,'source_passage_absent',true,'missing_stimulus_reason','Passage-2 (animal- vs plant-based protein) for items 3–4 was absent from the source document.'))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9867217b-5880-5c0e-b471-9d0fb06a2acf', '70207b87-6621-5341-82e2-01b0f629c952', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('ed6b1bd8-ce4b-50be-97e3-08da58cfeeaa', '70207b87-6621-5341-82e2-01b0f629c952', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('1fbe7a0e-89de-5eec-8c2e-980ba15f6fe7', '70207b87-6621-5341-82e2-01b0f629c952', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('e56a7b0d-590a-51c0-af6c-cd7116982359', '70207b87-6621-5341-82e2-01b0f629c952', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('8125fee7-06d6-5226-a995-bb31f0c62e45', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 5, 'What is the maximum value of n such that 7 × 343 × 385 × 1000 × 2401 × 77777 is divisible by 35^n?', 'fa4acb676011c0dfc542ec658b6ed40e0bc4e338f1159916039a22b41a42862a',
        'mcq', null, 'pending', 5, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f934f987-05d1-5282-ba62-5451a816d426', '8125fee7-06d6-5226-a995-bb31f0c62e45', 'A', '3', '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('1017792a-b8f3-5851-90bd-ea91b01f0f6e', '8125fee7-06d6-5226-a995-bb31f0c62e45', 'B', '4', '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('8cebb856-ba42-5cf4-8ab6-ccfefa8a1555', '8125fee7-06d6-5226-a995-bb31f0c62e45', 'C', '5', 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7987c73b-b799-5f75-9b27-69bde1a52415', '8125fee7-06d6-5226-a995-bb31f0c62e45', 'D', '7', '7902699be42c8a8e46fbbb4501726517e86b22c56a189f7625a6da49081b2451', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('7477a48b-03c0-568e-b45f-81f6e3e24755', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 6, 'What is X in the sequence 24, X, 12, 18, 36, 90?', 'eaaa2aa855684d12a5066a9e5337311a2e9a778f6267280adab2cbc2868b5db0',
        'mcq', null, 'pending', 6, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('5037663e-14be-5529-9e92-717eb231409d', '7477a48b-03c0-568e-b45f-81f6e3e24755', 'A', '18', '4ec9599fc203d176a301536c2e091a19bc852759b255bd6818810a42c5fed14a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('084d4f0d-1785-5978-95ab-2e9d621ea658', '7477a48b-03c0-568e-b45f-81f6e3e24755', 'B', '12', '6b51d431df5d7f141cbececcf79edf3dd861c3b4069f0b11661a3eefacbba918', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('49a3edb5-e6f0-5c0b-908b-18b6a16eb58e', '7477a48b-03c0-568e-b45f-81f6e3e24755', 'C', '9', '19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f9220636-f03b-52ca-bc3b-9c2df4630e0e', '7477a48b-03c0-568e-b45f-81f6e3e24755', 'D', '6', 'e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('f8487157-c623-59c1-b41b-af2d329a2995', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 7, 'P and Q walk along a circular track. They start at 5:00 a.m. from the same point in opposite directions. P walks at an average speed of 5 rounds per hour and Q walks at an average speed of 3 rounds per hour. How many times will they cross each other between 5:20 a.m. and 7:00 a.m.?', '3ac75a53873e0bf1574c577365a8bc7f4acbf1b7569cf23cf116b968a1d7b5e4',
        'mcq', null, 'pending', 7, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('617b3b0c-1952-5c02-8311-c4d8d1729aa3', 'f8487157-c623-59c1-b41b-af2d329a2995', 'A', '12', '6b51d431df5d7f141cbececcf79edf3dd861c3b4069f0b11661a3eefacbba918', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('fc47e479-41f0-5424-8570-465a51f8811b', 'f8487157-c623-59c1-b41b-af2d329a2995', 'B', '13', '3fdba35f04dc8c462986c992bcf875546257113072a909c162f7e470e581e278', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('556fd79f-7bde-533b-bad3-f67910854e98', 'f8487157-c623-59c1-b41b-af2d329a2995', 'C', '14', '8527a891e224136950ff32ca212b45bc93f69fbb801c3b1ebedac52775f99e61', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9a7e7c30-67c6-5422-8f4c-e8d930f209fc', 'f8487157-c623-59c1-b41b-af2d329a2995', 'D', '15', 'e629fa6598d732768f7c726b4b621285f9c3b85303900aa912017db7617d8bdb', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('a9683fd3-76c6-572b-8534-9709b658301d', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 8, 'If P = +, Q = –, R = ×, S = ÷, then insert the proper notations between the successive numbers in the equation 60_15_3_20_4 = 20:', '6ddb00acea339eaec3fb046f3a1d8558e6fb97f707cc39b0a0a005303cef32bd',
        'mcq', null, 'pending', 8, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('26a2c88b-8f88-57a5-babd-c8195c7ad074', 'a9683fd3-76c6-572b-8534-9709b658301d', 'A', 'SPRQ', 'e8fd2ced58e93f96c4439db0202d544b956cfb2231e68f2ad2b923a9090bbd75', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('0730664d-150b-5707-94c8-975ece29421f', 'a9683fd3-76c6-572b-8534-9709b658301d', 'B', 'QRPS', '6ed5f9057235025e3f54f4a325129a067aa5e24d0477271d57335954014b4bf9', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('39bb0211-d6d5-5d3e-adec-f72b2bcbbebc', 'a9683fd3-76c6-572b-8534-9709b658301d', 'C', 'QRSP', 'a2ee22af570f9fea5b7ece98f38de6a7fd64ef3e1ea4312e9f6a2062ba6802b9', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('d3005a91-1e8c-525f-84ad-07f976060f92', 'a9683fd3-76c6-572b-8534-9709b658301d', 'D', 'SPQR', 'b5c96b261dd197890596f912dee212d74fec5acc5a36874d094927f76da0d47a', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('9fcd2ace-7e32-5a1a-9018-6c59a615cb6d', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 9, 'A tram overtakes 2 persons X and Y walking at an average speed of 3 km/hr and 4 km/hr in the same direction and completely passes them in 8 seconds and 9 seconds respectively. What is the length of the tram?', '5632a8cefdb395bc986834778ad6f845237a3a2c16f004373f7b5e3397e82478',
        'mcq', null, 'pending', 9, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('5d763a1f-5a9f-50ee-a79b-4f3783b6f67d', '9fcd2ace-7e32-5a1a-9018-6c59a615cb6d', 'A', '15 m', '604d10da1d0ba3867832bc71ebda940b12412749005f7dd6b12d4aceb85e2529', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4f9e5d58-2e3b-5150-8530-b7997fc1c907', '9fcd2ace-7e32-5a1a-9018-6c59a615cb6d', 'B', '18 m', 'e8a3450984fc466e00e6afa14411a57864f9d2907ca533e58c30122785667120', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9e549b08-a50e-5c63-93af-245653cf2306', '9fcd2ace-7e32-5a1a-9018-6c59a615cb6d', 'C', '20 m', '379a48e50ebb54fab7b2ba6db28d45bcfac4c2cb962eb588050ed11094f892de', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('ecdac548-3d56-5ed4-9bfc-1f012a7bfc45', '9fcd2ace-7e32-5a1a-9018-6c59a615cb6d', 'D', '24 m', 'd425f131730c85e8ede7c3c541f2b6e06304ca6d9467f4e00a00896786afd79e', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('e258e791-e95b-5b63-a883-af8856c70622', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 10, 'If N^2 = 12345678987654321, then how many digits does the number N have?', '0aa61da67e2106b29edd277754e165d609bf3a430c9452805e295e77748b3128',
        'mcq', null, 'pending', 10, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('903fd694-b5a2-566a-b5e2-de49eec8cd48', 'e258e791-e95b-5b63-a883-af8856c70622', 'A', '8', '2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('3a284115-9128-5388-8d4c-f45a57b54192', 'e258e791-e95b-5b63-a883-af8856c70622', 'B', '9', '19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7f5cc2dc-c3f1-56d9-827c-16dc47f5521e', 'e258e791-e95b-5b63-a883-af8856c70622', 'C', '10', '4a44dc15364204a80fe80e9039455cc1608281820fe2b24f1e5233ade6af1dd5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('db6f307e-55bd-5677-829e-2ca4cdf80471', 'e258e791-e95b-5b63-a883-af8856c70622', 'D', '11', '4fc82b26aecb47d2868c4efbe3581732a3e7cbcc6c2efb32062c08170a05eeb8', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('9f967de9-a961-5556-a986-50b73f1ca23e', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 11, 'Which one of the following statements best reflects the corollary to the above passage?', 'd2a0f59ee5a55c8942541ee5a9089c83a80138a702066df327f259af17e503d3',
        'mcq', null, 'pending', 11, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false,'missing_stimulus',true,'source_passage_absent',true,'missing_stimulus_reason','The agriculture / economic-reforms passage for items 11–12 was absent from the source document.'))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('0badb3b9-6013-5b07-8395-6fec2132146b', '9f967de9-a961-5556-a986-50b73f1ca23e', 'A', 'The benefit of economic reforms percolates down more slowly to the agriculture sector than in other sectors of the economy.', 'a3b2a158350372fa85c2432c4ed0e41aa0ada04a2f43fd8eed90e79187298dfb', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('5ad23548-401a-5505-9bba-a67e3a2ca980', '9f967de9-a961-5556-a986-50b73f1ca23e', 'B', 'For India, the green revolution was not as useful as it was expected to be.', 'a6de1e76a514d4df7718e76576fe7b633990063e990dda6bfdc0eda42f105b94', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('faab820d-196e-5064-820a-b327026769e6', '9f967de9-a961-5556-a986-50b73f1ca23e', 'C', 'India lagged behind other countries in adapting mechanized and modern farming.', 'd05af2a9a5c008dec56b38d6f193bb48f9191de42231f935bcf7e21a699306e5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('ea25a890-c2b4-5041-9aeb-9f787998ca44', '9f967de9-a961-5556-a986-50b73f1ca23e', 'D', 'Rural-to-urban migration resulted in the stagnant agriculture sector.', '55e1e51bea89104f00b3526cfc9c71dec7f2838717d14f5734ae6afe1cafc4f7', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('72bd302c-e9bb-5a1c-a8da-2646fc8bd2d8', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 12, 'With reference to the passage, the following assumptions have been made: The growing divergence between the fortunes of the agricultural and non-agricultural economy in India could have been reduced/contained by: I. adapting large-scale cultivation of commercial crops and viable corporate farming. II. providing free insurance for all crops and heavily subsidizing seeds, fertilizers, electricity and farm machinery at par with developed countries. Which of the above assumptions is/are valid?', '7f33c90d6e9640cbbd9b6471b12dcdfca6a8107a5244e07d4d4642fd0834a433',
        'mcq', null, 'pending', 12, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false,'missing_stimulus',true,'source_passage_absent',true,'missing_stimulus_reason','The agriculture / economic-reforms passage for items 11–12 was absent from the source document.'))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('81d695f0-3f60-592b-adbd-5b2be5a7f817', '72bd302c-e9bb-5a1c-a8da-2646fc8bd2d8', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('d6f70823-c89e-58b8-b0a5-0b26dd1044fd', '72bd302c-e9bb-5a1c-a8da-2646fc8bd2d8', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('6e22a796-0575-5f0e-b2db-2d3d7eb5bc1f', '72bd302c-e9bb-5a1c-a8da-2646fc8bd2d8', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('e174a02d-f46c-5368-836a-f52ba738d78e', '72bd302c-e9bb-5a1c-a8da-2646fc8bd2d8', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('8282d48d-b198-5266-861b-9d2e88060a39', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 13, 'Which one of the following statements best reflects the most logical and rational message conveyed by the author of the passage?', 'be0429edf5577a8a3a57fd81a6af768acb5050dcba2c96489c3fba867019ca91',
        'mcq', null, 'pending', 13, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b92fcef3-698f-55a4-92d3-61d9bd21db71', '8282d48d-b198-5266-861b-9d2e88060a39', 'A', 'We need to free the handloom industry from the limited narrative linked to preserving cultural heritage.', '25738e72f809cc77c541b208dac12e1b5eb88bc237e2b26ca13261275856c922', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a5485ba9-b5af-59f7-b66c-91a1f8eacdcb', '8282d48d-b198-5266-861b-9d2e88060a39', 'B', 'Continued State support to the handloom industry ensures the preservation of some of our glorious art forms and old traditions.', '8daeae8b7805eeac35ab28e217cba3415a315c0a142800f5b21666e3b592d4cb', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('43a47c0c-3336-5d15-a3c9-c66c4563261f', '8282d48d-b198-5266-861b-9d2e88060a39', 'C', 'Household units of the handloom sector should be modernized and made an economically viable organized industry.', 'e5b49d8d619bc25cbf946ad9766d4a9851a3640822a66a654822afae842cf017', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9c532054-e861-5257-98ec-2c7d9ecbc69e', '8282d48d-b198-5266-861b-9d2e88060a39', 'D', 'Handloom products need to be converted to machine-made designer products so as to make them more popular.', '1b5f8b1a9d5a7df08679c3a08308031b787a5392a57d977cf827207bbb524e03', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('9c82bf4e-2684-5cd4-8496-bcfd8df60a1f', '8282d48d-b198-5266-861b-9d2e88060a39', '99cb64a4-353b-5d18-beb6-efbc30e55eab', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('eb26df01-89a8-582e-a5fb-036c8ae0da3b', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 14, 'With reference to the above passage, the following assumptions have been made: I. There is no need for the State to be involved in any manner in the handloom sector. II. Handloom products are no longer appealing and attractive in the rapidly changing modern world. Which of the above assumptions is/are valid?', '3fe932cc324750369e5c4af4e8ca423f7f52f607a06316e2ddedc73c3216a99b',
        'mcq', null, 'pending', 14, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('3f957b6e-627e-5367-9dec-c747b6b2bdf1', 'eb26df01-89a8-582e-a5fb-036c8ae0da3b', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9bc1a758-fbf1-5878-8083-59575a80e17d', 'eb26df01-89a8-582e-a5fb-036c8ae0da3b', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b28f70a7-b914-5c2e-b1d8-9c4aadcf86d7', 'eb26df01-89a8-582e-a5fb-036c8ae0da3b', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('d946c637-67f5-5d31-b47a-5319b383ea8f', 'eb26df01-89a8-582e-a5fb-036c8ae0da3b', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('83658ee5-dbd5-5b47-ae16-7b67c20e3fcc', 'eb26df01-89a8-582e-a5fb-036c8ae0da3b', '99cb64a4-353b-5d18-beb6-efbc30e55eab', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('fbaa593a-af4d-52db-a684-c8d24d0f5370', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 15, 'Consider the first 100 natural numbers. How many of them are not divisible by any one of 2, 3, 5, 7 and 9?', '9f2b13fea0b5f52c965fe5f6a5b17bb4835a0e3e1b4b0e0fd27abaa52c657211',
        'mcq', null, 'pending', 15, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('66cef409-0e07-5605-9151-dbea2014b1e7', 'fbaa593a-af4d-52db-a684-c8d24d0f5370', 'A', '20', 'f5ca38f748a1d6eaf726b8a42fb575c3c71f1864a8143301782de13da2d9202b', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4f3392ac-8e7c-5d80-9f76-cc913b355655', 'fbaa593a-af4d-52db-a684-c8d24d0f5370', 'B', '21', '6f4b6612125fb3a0daecd2799dfd6c9c299424fd920f9b308110a2c1fbd8f443', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4f8e0fed-4988-5d7c-8d46-a6d78dc48196', 'fbaa593a-af4d-52db-a684-c8d24d0f5370', 'C', '22', '785f3ec7eb32f30b90cd0fcf3657d388b5ff4297f2f9716ff66e9b69c05ddd09', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('cc91cb40-7de8-5d30-aa8c-a281fc77072b', 'fbaa593a-af4d-52db-a684-c8d24d0f5370', 'D', '23', '535fa30d7e25dd8a49f1536779734ec8286108d115da5045d77f3b4185d8f790', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('3b78d920-1ca1-59b3-a1f9-0e10e45c345b', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 16, 'If 4 ≤ x ≤ 8 and 2 ≤ y ≤ 7, then what is the ratio of maximum value of (x + y) to minimum value of (x − y)?', '989432012383f1d97a3ba11d9717bd2d23601567de9f650f6861c36fb560ecf8',
        'mcq', null, 'pending', 16, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b2ace935-b2b1-59c6-818c-2342172e816a', '3b78d920-1ca1-59b3-a1f9-0e10e45c345b', 'A', '6', 'e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('80dc8af7-1641-5d95-b6fc-63e764c0a7af', '3b78d920-1ca1-59b3-a1f9-0e10e45c345b', 'B', '15/2', '2a873d587af23c030e609fa2b3fa0db5a4c2fb433222b497b0d0e0819da2d3a6', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('873c8cf3-acef-5ffc-8ecd-b4d6c188671b', '3b78d920-1ca1-59b3-a1f9-0e10e45c345b', 'C', '–15/2', 'd00585437bc23a6832cbb74374cfc6fa9074a6dadb37fd7e193e02f809783487', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('e4a6dfb1-b0b1-5673-af11-bfec84e51742', '3b78d920-1ca1-59b3-a1f9-0e10e45c345b', 'D', 'None of the above', '7af580976d463ec209f8b784d25a4f6ad1a1d7f20706bd396463ccf7b0c455e0', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('c0de0e70-097c-59a7-81d3-3a9846516bbf', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 17, 'Let both p and k be prime numbers such that (p² + k) is also a prime number less than 30. What is the number of possible values of k?', 'f5339f4d65badf7200b40b443c1aae597fe9b7b31be00f6457ebf06e36ce5b19',
        'mcq', null, 'pending', 17, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('038d5dd1-899c-5d9b-a6ac-d4ec7f5780da', 'c0de0e70-097c-59a7-81d3-3a9846516bbf', 'A', '4', '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('d53c72c5-c98e-557f-9f3b-4d47ee13e4c3', 'c0de0e70-097c-59a7-81d3-3a9846516bbf', 'B', '5', 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7718b3dd-5c8e-50dd-a8a0-7fbe1136ff46', 'c0de0e70-097c-59a7-81d3-3a9846516bbf', 'C', '6', 'e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('2cf6d165-1764-5304-86e1-b15193792065', 'c0de0e70-097c-59a7-81d3-3a9846516bbf', 'D', '7', '7902699be42c8a8e46fbbb4501726517e86b22c56a189f7625a6da49081b2451', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('3e9c5b6a-8789-5a61-80e1-5b989ad97402', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 18, 'There are n sets of numbers each having only three positive integers with LCM equal to 1001 and HCF equal to 1. What is the value of n?', 'f0cdd027f620461ebd6ced98c1b71966fa8f99c3877e332a5bc00499c0a43704',
        'mcq', null, 'pending', 18, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('46556d49-ae6b-5aaf-8593-18bb5b56a504', '3e9c5b6a-8789-5a61-80e1-5b989ad97402', 'A', '6', 'e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('bbad5680-d7d8-5d45-97c3-50d221eb07fd', '3e9c5b6a-8789-5a61-80e1-5b989ad97402', 'B', '7', '7902699be42c8a8e46fbbb4501726517e86b22c56a189f7625a6da49081b2451', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('26407349-a920-513e-b1d8-afc1c9a51f49', '3e9c5b6a-8789-5a61-80e1-5b989ad97402', 'C', '8', '2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('c2fb7dcc-a4bc-5419-9dec-d8dc5b19e5d7', '3e9c5b6a-8789-5a61-80e1-5b989ad97402', 'D', 'More than 8', '02ca45996fd2a10fa58732db259fe02aa282f457d68306bc4efb37e7c37c1364', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('bd2d5195-3a61-5b2d-9dad-51d86a6e83c0', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 19, 'Let PQR be a 3-digit number, PPT be a 3-digit number and PS be a 2-digit number, where P, Q, R, S, T are distinct non-zero digits. Further, PQR − PS = PPT. If Q = 3 and T < 6, then what is the number of possible values of (R, S)?', 'f2d8a648adedb9d246b704fe663beb5c1bbca17f5b164bc761bb4cd6f600d014',
        'mcq', null, 'pending', 19, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('43575bdb-6b10-5b22-b99b-1cbd971bb456', 'bd2d5195-3a61-5b2d-9dad-51d86a6e83c0', 'A', '2', 'd4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('382acf70-eb76-5053-ac87-0cb1caf892fe', 'bd2d5195-3a61-5b2d-9dad-51d86a6e83c0', 'B', '3', '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('258db046-2d9c-5b57-b72b-fd3d2ba399a0', 'bd2d5195-3a61-5b2d-9dad-51d86a6e83c0', 'C', '4', '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4fa73975-d1e4-57ec-9b51-73047f701be3', 'bd2d5195-3a61-5b2d-9dad-51d86a6e83c0', 'D', 'More than 4', '21384f19af877bb3084a37dcb2d02899cc08a6480a4d29035a5e77b9b63407bb', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('6adfd0f3-51ac-507e-ad74-8a4ae59d6597', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 20, 'Consider the sequence AB_CC_A_BCCC_BBC_C that follows a certain pattern. Which one of the following completes the sequence?', '828cbf0d3254b050541802587605c88d822402037feead42ef82abdeaf39bdba',
        'mcq', null, 'pending', 20, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('fabffb67-7455-5e79-8117-ab887a2dab49', '6adfd0f3-51ac-507e-ad74-8a4ae59d6597', 'A', 'B, C, B, C, A', '352d2cc588aecec647191724ca38146f1d4cab4f91bc86a9aeb13f9a9801b387', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('c6e51c6a-a9d7-5cae-8c55-50beaee5f662', '6adfd0f3-51ac-507e-ad74-8a4ae59d6597', 'B', 'A, C, B, C, A', 'd6aed58021a85788a49825406fd5ce5957a93e864d405fc21f7efae341a64a82', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('8675502b-e730-52c9-b449-ac264e599e91', '6adfd0f3-51ac-507e-ad74-8a4ae59d6597', 'C', 'B, C, B, A, C', 'a3020890ad076c50d0e8c358a306595c632f3f7a4fb9a5da6b19ac3e7ae42c1f', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4e9a7fea-2a86-5eb6-939b-f833b2d81f7d', '6adfd0f3-51ac-507e-ad74-8a4ae59d6597', 'D', 'C, B, B, A, C', '04fdf808632148cafa53d57ecd7ff4ebc473fed324b59ced964b9dab91e371a9', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('ca729d21-0ec6-5162-9270-ed8d23b20b9a', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 21, 'Which one of the following statements best reflects the most logical, rational and pragmatic message conveyed by the author of the passage?', 'c729873440632f366ba7c001144c505edc9802da1f384d7ee51108ea23098ded',
        'mcq', null, 'pending', 21, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a0764295-d6d9-5feb-a40e-30aee8c319e7', 'ca729d21-0ec6-5162-9270-ed8d23b20b9a', 'A', 'The mitigation and adaptation strategies to address/tackle the climate change is essentially the responsibility of each State.', 'f5c83482804f13335bde086ebe8a205f037693fcd3c2a249e9e8f7b1e80282ae', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('e94561ab-7789-5e06-b5c7-969f91c2510b', 'ca729d21-0ec6-5162-9270-ed8d23b20b9a', 'B', 'India is too diverse to implement any effective strategy or programme to address/tackle the climate change.', '73373b620438a518c1543917a0095447d7a3dcf36f165f9f078278a056ab8d49', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('adbc3378-87ce-59e5-8900-fa5491cc0d7b', 'ca729d21-0ec6-5162-9270-ed8d23b20b9a', 'C', 'It is basically the responsibility of the Union Government to implement the climate action plans and ensure net zero emissions.', '0c1a46d02ffb3c32686c3b77a54abd30feddada9c3ee0e604f87eb9bdb013ddd', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('e9225c45-2117-5d72-b27f-ef7e35aaed7b', 'ca729d21-0ec6-5162-9270-ed8d23b20b9a', 'D', 'India needs to formulate effective climate change mitigation and adaptation strategies at the State/region level.', '3913229d8ac23ab30936886eeeba3be4d9306b3865645ddbf49ef2c84ad30777', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('3d8b6608-8535-59e3-9204-2e5d0c85bb00', 'ca729d21-0ec6-5162-9270-ed8d23b20b9a', '08dcce7f-1512-56ff-b2f3-b1186b76c1a3', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('318fd4c0-c121-5434-8dac-58308680ec3c', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 22, 'With reference to the passage, the following assumptions have been made: I. Green energy production can be linked to/integrated with the climate change mitigation and adaptation strategies. II. Effects of climate change are much more severe in coastal and mountainous regions. Which of the above assumptions is/are valid?', '4757b0782a88e8a240798cc40f6619aef3dbe7e372adbfa343c2d1f53799febb',
        'mcq', null, 'pending', 22, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('cbdddd36-ded9-5e95-9511-2352d5dcf5b8', '318fd4c0-c121-5434-8dac-58308680ec3c', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7ab57798-f1e1-5771-9269-0e746663b449', '318fd4c0-c121-5434-8dac-58308680ec3c', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('3f3b551a-dcd2-517e-8f0c-c72aa3623a38', '318fd4c0-c121-5434-8dac-58308680ec3c', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a997bb6a-477d-563c-b284-91651cafe9d0', '318fd4c0-c121-5434-8dac-58308680ec3c', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('c1e36d2e-5d73-59c3-95ea-bd445d5b4f71', '318fd4c0-c121-5434-8dac-58308680ec3c', '08dcce7f-1512-56ff-b2f3-b1186b76c1a3', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('b3727889-d911-57f0-ac72-e5f5caca79da', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 23, 'Which one of the following statements best reflects the critical message conveyed by the passage?', '4ed34bd808502f3076bd42dd766a3d95914bfc8aaf60c562a5a63304bd2a6a4a',
        'mcq', null, 'pending', 23, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('951fa973-dfce-5c22-872f-081a72515115', 'b3727889-d911-57f0-ac72-e5f5caca79da', 'A', 'India’s political executive should be aware that poverty and social inequality and the consequent sense of insecurity is the main social problem.', 'e612ad93b0b56b2a401b87397d7e0e7098d2d6e2c6e1793e2a3ff8aa976c9061', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('1d04e85c-885a-5824-b596-3c8df27819bf', 'b3727889-d911-57f0-ac72-e5f5caca79da', 'B', 'In India, poverty is the primary reason for social inequality and insecurity.', 'fe11dc97714c0e29a6d158056262b75de63731bd7b1033d9317b4121062991fb', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('99792388-2b59-5639-bff7-0985cd62bdae', 'b3727889-d911-57f0-ac72-e5f5caca79da', 'C', 'Poverty and social inequality are so intricately linked that they pose an unmanageable crisis for India.', '7dce816e8aa0ca665b46a69c96ef6f77d53efca2d47ccf577d326ddb5255f1bc', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('137c81f8-87f5-5b2a-ae29-42b660e19862', 'b3727889-d911-57f0-ac72-e5f5caca79da', 'D', 'Insecurity, more than poverty, is the main economic issue that Government policies must address.', '8460ba8fc2d7f134b101ae3527296e9bee177f8162479c93925fa866e4bc28fc', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('76825dfe-c411-5369-a920-2b6bee95800e', 'b3727889-d911-57f0-ac72-e5f5caca79da', 'f670371f-c1e5-5dfa-b961-3dffebe4084e', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('08bbf282-55d6-5521-909c-9ee51ffc9c6a', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 24, 'With reference to the above passage, the following assumptions have been made: I. People above the poverty line also are prone to suffer from anxiety about economic insecurity. II. Eradication of poverty can result in peace and social equality in the country. Which of the above assumptions is/are valid?', '0324a181e5fc14baef467d5d3aa3bb5f0e048c3ddc0ac70c691d6744460a1685',
        'mcq', null, 'pending', 24, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a7e2eb87-d884-5a85-9ad2-038a1894ea70', '08bbf282-55d6-5521-909c-9ee51ffc9c6a', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('89739e71-1214-5746-8eec-e0078d362171', '08bbf282-55d6-5521-909c-9ee51ffc9c6a', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4c70f203-9c4c-5018-a46d-8360ed9ebbd0', '08bbf282-55d6-5521-909c-9ee51ffc9c6a', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('cfbec5d3-015b-5fb0-9cbf-6e3c6ed7fd4b', '08bbf282-55d6-5521-909c-9ee51ffc9c6a', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('5215b845-4bfd-5708-a6d3-24016d0da468', '08bbf282-55d6-5521-909c-9ee51ffc9c6a', 'f670371f-c1e5-5dfa-b961-3dffebe4084e', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('971766b8-1e5a-5212-821e-fb13b4ff2d71', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 25, 'A solid cube is painted yellow on all its faces. The cube is then cut into 60 smaller but equal pieces by making the minimum number of cuts. Which of the following statements is/are correct? I. The minimum number of cuts is 9. II. The number of smaller pieces which are not painted on any face is 6. Select the correct answer using the code below:', 'b3107fc470bc95f1fdc28f16e09420408e500775b7a32ebd2a514c219b9e16f9',
        'mcq', null, 'pending', 25, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('8421609c-ecd0-5c99-a22d-83598e927d00', '971766b8-1e5a-5212-821e-fb13b4ff2d71', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('603c14d0-3d37-5cac-86d1-30ac015c1f5b', '971766b8-1e5a-5212-821e-fb13b4ff2d71', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('47aa3f8b-6c3a-5964-b320-7fb07d4eb39a', '971766b8-1e5a-5212-821e-fb13b4ff2d71', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('069844c1-83e3-5beb-96db-17f9d164b8be', '971766b8-1e5a-5212-821e-fb13b4ff2d71', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('526f5a2c-bff1-59c2-a869-5af93c6415d5', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 26, 'If 7 * 24 = 25 and 12 * 16 = 20, then what is 16 * 63 equal to?', 'f060e9e52ecf6c0ac7d8ce6a1a3d338f88b51abdd4a47343a9f2eb8910ba8915',
        'mcq', null, 'pending', 26, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('d6d38633-57d3-5b9f-b7b7-f78020ff6e31', '526f5a2c-bff1-59c2-a869-5af93c6415d5', 'A', '70', 'ff5a1ae012afa5d4c889c50ad427aaf545d31a4fac04ffc1c4d03d403ba4250a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('90d4cfda-fb60-57a7-b23a-bfacb4854415', '526f5a2c-bff1-59c2-a869-5af93c6415d5', 'B', '66', '3ada92f28b4ceda38562ebf047c6ff05400d4c572352a1142eedfef67d21e662', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('2e59e277-c90a-516f-88cc-95fdcb1fce12', '526f5a2c-bff1-59c2-a869-5af93c6415d5', 'C', '65', '108c995b953c8a35561103e2014cf828eb654a99e310f87fab94c2f4b7d2a04f', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f3e08a80-c37a-55cc-a88a-d5a03612ed7f', '526f5a2c-bff1-59c2-a869-5af93c6415d5', 'D', '64', 'a68b412c4282555f15546cf6e1fc42893b7e07f271557ceb021821098dd66c1b', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('bdfc9c1b-e68d-509a-aacb-a46d1968a8d8', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 27, 'The petrol price shot up by 10% as a result of the hike in crude oil prices. The price of petrol before the hike was ₹90 per litre. A person travels 2200 km every month and his car gives a mileage of 16 km per litre. By how many km should he reduce his travel if he wants to maintain his expenditure at the previous level?', 'cf37dd144d644d856cd9fa506a03121105b4d3f1140f562822d09aa579878d64',
        'mcq', null, 'pending', 27, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('6d01c431-66c2-5bf1-9a4f-4778abf125ad', 'bdfc9c1b-e68d-509a-aacb-a46d1968a8d8', 'A', '180 km', 'aa4bfd7c34979e380d9cef241b6a3175a755b7491bc6c81d71f42c4a712852aa', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('37cd9f1e-4af3-5ccb-9543-dbf912b8ae11', 'bdfc9c1b-e68d-509a-aacb-a46d1968a8d8', 'B', '200 km', '3dbd69071e6fc02cf26a9cd204c3d747b323ee31a25c99542c8327e273e13db4', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f41b283f-edd5-5b75-a970-3507d5cc5997', 'bdfc9c1b-e68d-509a-aacb-a46d1968a8d8', 'C', '220 km', 'f0c9c73cf4001bab4362bdbcf9132a63a9aaf1dd3c89ca16529040886316cd42', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f8f2d39d-4eb1-5667-a467-c75f26acc00b', 'bdfc9c1b-e68d-509a-aacb-a46d1968a8d8', 'D', '240 km', 'ce43fa770919b37dbe7f22f311a48371ee1d7e17ecc2377a4cfbf8e25628d04e', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('3d20473e-509e-569a-8693-c2905c62bc94', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 28, 'A 4-digit number N is such that when divided by 3, 5, 6, 9 it leaves a remainder of 1, 3, 4, 7 respectively. What is the smallest value of N?', '953830084f500bc37c58d3af0f304c347a5b90d17406348daee886f659368124',
        'mcq', null, 'pending', 28, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('58e5e130-fa1f-5d49-99dd-79c599e04365', '3d20473e-509e-569a-8693-c2905c62bc94', 'A', '1068', '0f0b82fae280ae9fec1905f029b6ee9a9c85bb6cc5151da6dafe38a7902a4a53', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b8acd94e-f864-55dd-88c2-b6fcf44ac0aa', '3d20473e-509e-569a-8693-c2905c62bc94', 'B', '1072', 'f8b2f96ed09b16bfd24ff625c064408fe19143db121b7944763fcbcc69ab4991', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('dc4f1c9f-7a63-52b8-bd7d-a23250c4173b', '3d20473e-509e-569a-8693-c2905c62bc94', 'C', '1078', 'd88c39de46401a311ffda92d37930b4a543eb6286f835afe9d04dd416476434d', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('dee1efaf-b643-5f14-88e4-3c006fe3234b', '3d20473e-509e-569a-8693-c2905c62bc94', 'D', '1082', '3ef58410b868298fcca4ee41144221bf86bc94e810dfdac6f4b502ce5fcd75c6', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('d0ca1c1f-974d-5165-b167-4a06c9ec477d', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 29, 'Consider the following statements: I. If A ≤ B > C < D > E > F ≥ G = H; then B is always greater than E. II. If P > Q = R ≥ S = T ≤ U = V > W; then S is always less than V. Which of the statements above is/are correct?', 'd01dedfd12776ca0e5cd2f9186922e8f0b2a63603b24431a4929047809e2ace3',
        'mcq', null, 'pending', 29, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('35c662d8-bb4f-5226-9d1a-b6e1877c5c10', 'd0ca1c1f-974d-5165-b167-4a06c9ec477d', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('1ee1abe2-e694-5a90-9a3c-96d883754bd1', 'd0ca1c1f-974d-5165-b167-4a06c9ec477d', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('c48088d7-d2e7-5360-ae16-9ab39a3df0a4', 'd0ca1c1f-974d-5165-b167-4a06c9ec477d', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4e2121e3-76f1-5553-9244-bc420179b9cf', 'd0ca1c1f-974d-5165-b167-4a06c9ec477d', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('b42d9250-b047-5b0f-9fbb-b350cb818e13', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 30, 'What is the unit digit in the multiplication of 1 × 3 × 5 × 7 × 9 × … × 999?', '071f9e39bddf9c219e3d6ff46af612bb1189bd1400f778cede095cf125ce1aa0',
        'mcq', null, 'pending', 30, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7e2838e8-73b2-567b-aeec-b222d57a6faa', 'b42d9250-b047-5b0f-9fbb-b350cb818e13', 'A', '1', '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('61e94629-e265-5278-9a44-13c627522ea2', 'b42d9250-b047-5b0f-9fbb-b350cb818e13', 'B', '3', '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f104c946-ed3a-5a2d-a609-a02aa6a0c12a', 'b42d9250-b047-5b0f-9fbb-b350cb818e13', 'C', '5', 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('728dad08-8ed7-5079-94f4-97775619582d', 'b42d9250-b047-5b0f-9fbb-b350cb818e13', 'D', '9', '19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('a606923b-e693-561f-ae15-d81ccebedd10', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 31, 'Which one of the following statements best reflects the critical message conveyed by the author of the passage?', 'a3e2979e5d2ac17bbeba0562c5174ded757574f8343886f596022dc0501f760c',
        'mcq', null, 'pending', 31, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('ae66b9c2-2c41-51c9-8a3c-a04509bc21d9', 'a606923b-e693-561f-ae15-d81ccebedd10', 'A', 'Conservation of biodiversity is not an issue to be worried about when some people depend on ecosystems for their livelihoods.', '8decd5f6cca99adae03d52c32aa07d0398ba31395f99e6346b82ebbade997e20', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('99708ebc-562d-5c1a-ac9b-92ea6c8f1bea', 'a606923b-e693-561f-ae15-d81ccebedd10', 'B', 'Commercial exploitation of forests goes against the fundamental rights of the people dependent on forests for food and shelter.', '5ebfd8aff83342a9f586c4cf0659b4d512a31e7f6b39f482f8e0ddb980a27dd1', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('29f3c500-538d-50a1-b8c3-f57343f9859d', 'a606923b-e693-561f-ae15-d81ccebedd10', 'C', 'Sustenance of livelihood and degradation of ecosystem while being together exacerbate one another, leading to conflicts and imbalance.', 'f16d1ed8cf7dcd6a950cdc90c2cf1dd55f4f7ac07f0dca767e58d26cff70ad2e', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('06058e5f-98e0-5d3e-994c-82a5c145a183', 'a606923b-e693-561f-ae15-d81ccebedd10', 'D', 'Commercial exploitation of ecosystems should be completely stopped.', '2b661be88c0fafdae12dbbf8b80c27335d1d639e19c651b5aa70de844e1c01da', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('42da730c-fd64-5366-a8d4-311fc5f22de5', 'a606923b-e693-561f-ae15-d81ccebedd10', '710965b5-51f4-54cc-ae11-8b98719b6939', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('f1f5296e-3f1a-526a-8011-376c5e04ee5d', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 32, 'With reference to the above passage, the following assumptions have been made: I. No country needs to depend on ecosystems to boost national income. II. Resource-rich countries need to share their resources with those of scant resources so as to prevent the degradation of ecosystems. Which of the above assumptions is/are valid?', 'b33ec28467b9e51d666b1db0114ad6b8c8e7d51b72b2606259d89282dbd262a0',
        'mcq', null, 'pending', 32, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9877b043-fbb7-5fc4-b214-24741c8a8700', 'f1f5296e-3f1a-526a-8011-376c5e04ee5d', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('219522ba-6d83-52c2-b600-6d2328bfbeb9', 'f1f5296e-3f1a-526a-8011-376c5e04ee5d', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('2ff97250-c19c-52a9-8a60-7a2e77e297d8', 'f1f5296e-3f1a-526a-8011-376c5e04ee5d', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('234e0ce5-ca27-5e0e-966f-e5e24440629b', 'f1f5296e-3f1a-526a-8011-376c5e04ee5d', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('6facfffc-36f8-5961-89bc-df1eab944d0e', 'f1f5296e-3f1a-526a-8011-376c5e04ee5d', '710965b5-51f4-54cc-ae11-8b98719b6939', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('3fc4323c-288c-5337-ac91-91069f5f5600', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 33, 'Which one of the following statements best reflects the central idea of the passage?', '17b9f4179dd96ff7c3fbddbb23ce40912d6883f1d8ac7a5292205e4c27acbb24',
        'mcq', null, 'pending', 33, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7780dbc9-6a61-5f1f-9da3-30e0720da283', '3fc4323c-288c-5337-ac91-91069f5f5600', 'A', 'Economies of scale is essential for transition to green growth.', '77dc89e17489ac010ae4684cb83e51b8aaf52114ae82e82a7209cfb8f582ce31', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('21799f19-accc-5955-bac4-83510fba921d', '3fc4323c-288c-5337-ac91-91069f5f5600', 'B', 'Modern technological progress is intensely linked to path-dependent innovations.', '17450d3abdc1ef6419b63415531f82cb8b4271871db87c335ef4eef9864f8555', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a68e3a02-abf8-552f-9e01-419c2d6a6977', '3fc4323c-288c-5337-ac91-91069f5f5600', 'C', 'Countries with large economies are in a better position to adopt green technologies.', 'b28ec4a31a48077e0ea38752221d440e734e21da4b1b030daf59b8a7e4db8fe0', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('2fe03561-5efc-5119-8c25-477b7aa1661c', '3fc4323c-288c-5337-ac91-91069f5f5600', 'D', 'Timing plays a crucial role in the case of green technology development.', 'd0a453e20d2185f9ec789c0f9dda857fedc7dea661f57f0ba375036af307ddb2', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('ef04f68d-9ba9-55ba-9094-f0bce540460a', '3fc4323c-288c-5337-ac91-91069f5f5600', '2e4ba4d4-6094-54dc-8ddf-995cf6b5c20b', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('1b5393a8-e294-58dc-88c4-18ab8f155031', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 34, 'With reference to the above passage, the following assumptions have been made: I. Path-dependent green investments will eventually most likely benefit growth as well as public finances in a country like India. II. If other green technologies follow the same pattern as that of solar energy, there will most likely be an easy green transition. Which of the above assumptions is/are valid?', 'b04fa1376d2ee5455e2a2f2c589095bec7770cc383cec9811c06908c93160d5d',
        'mcq', null, 'pending', 34, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('18734232-e23e-5c20-ac2f-3a92da305ec4', '1b5393a8-e294-58dc-88c4-18ab8f155031', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('2990138d-fd49-5d43-8aee-3b681969654a', '1b5393a8-e294-58dc-88c4-18ab8f155031', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a4757164-fc5a-5bea-bdc0-bf29f3d6e7f0', '1b5393a8-e294-58dc-88c4-18ab8f155031', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('16e99b2e-9660-5690-8e0b-47b865e03680', '1b5393a8-e294-58dc-88c4-18ab8f155031', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('11277432-776c-5e43-8d89-bb3949caa6b3', '1b5393a8-e294-58dc-88c4-18ab8f155031', '2e4ba4d4-6094-54dc-8ddf-995cf6b5c20b', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('51f0367d-818b-5b98-b34d-151d9bc466a7', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 35, 'A natural number N is such that it can be expressed as N = p + q + r, where p, q, and r are distinct factors of N. How many numbers below 50 have this property?', '3bae7852a13d4391bb7e15a7a07dbf27fe5a71e81493b9a106649f3d523ce054',
        'mcq', null, 'pending', 35, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('d4512ffb-896e-54b4-8619-aed7e6a7ae0c', '51f0367d-818b-5b98-b34d-151d9bc466a7', 'A', '6', 'e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b1f91d25-896c-5dbb-9718-2b042f4d3fe1', '51f0367d-818b-5b98-b34d-151d9bc466a7', 'B', '7', '7902699be42c8a8e46fbbb4501726517e86b22c56a189f7625a6da49081b2451', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('d2f12add-da08-5241-a2f6-32cc2dfe6337', '51f0367d-818b-5b98-b34d-151d9bc466a7', 'C', '8', '2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9bd84794-dbc8-564c-b97a-47c69f6068db', '51f0367d-818b-5b98-b34d-151d9bc466a7', 'D', '9', '19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('fccc2486-9218-5a14-ae0b-554aa2e6b040', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 36, 'Three prime numbers p, q, and r, each less than 20, are such that p – q = q – r. How many distinct possible values can we get for (p + q + r)?', 'a3298cdeb2003c891115c543dcb9d5d37dc57bf8a84b37783e7bffe1a7c71d55',
        'mcq', null, 'pending', 36, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('adcdc1a1-d502-50f2-ba65-2b8157d1486e', 'fccc2486-9218-5a14-ae0b-554aa2e6b040', 'A', '4', '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4b74be3b-fcb4-5100-a06f-cec7d83a7c35', 'fccc2486-9218-5a14-ae0b-554aa2e6b040', 'B', '5', 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('c39684c4-12f1-5905-959e-5e4fd538d52d', 'fccc2486-9218-5a14-ae0b-554aa2e6b040', 'C', '6', 'e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a29ae6ea-5f88-5625-978f-1ccaae98a435', 'fccc2486-9218-5a14-ae0b-554aa2e6b040', 'D', 'More than 6', '610caec26952fb658135d7dfae275449c1d52523e6d2737d61bc01ffaf2f83b0', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('6a32a9c7-a091-5a34-994d-2264c58b7bcd', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 37, 'How many possible values of (p + q + r) are there satisfying 1/p + 1/q + 1/r = 1, where p, q, and r are natural numbers (not necessarily distinct)?', 'd6b4269806a5f1519d9f3b011a922e133eab5493bdd8c789a5b6a2feb4953aaa',
        'mcq', null, 'pending', 37, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7fad4799-200e-5ed9-9ac6-8cc9b54b439f', '6a32a9c7-a091-5a34-994d-2264c58b7bcd', 'A', 'None', '140bedbf9c3f6d56a9846d2ba7088798683f4da0c248231336e6a05679e4fdfe', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('18e60a77-b697-5541-877d-28e59c5e5869', '6a32a9c7-a091-5a34-994d-2264c58b7bcd', 'B', 'One', '7692c3ad3540bb803c020b3aee66cd8887123234ea0c6e7143c0add73ff431ed', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('0b766051-4130-58f5-a130-9ada327f4487', '6a32a9c7-a091-5a34-994d-2264c58b7bcd', 'C', 'Three', '8b5b9db0c13db24256c829aa364aa90c6d2eba318b9232a4ab9313b954d3555f', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('980c3f26-8951-5f66-8b0b-6541c457c6ad', '6a32a9c7-a091-5a34-994d-2264c58b7bcd', 'D', 'More than three', 'd808cf257b25613d35a498d2a69bba45b776bdf47ff0e8683cc1ab31072951d8', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('b717f035-63d3-56fd-9345-fef12e7a63c3', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 38, 'What comes at X and Y respectively in the following sequence? January, January, December, October, X, March, October, Y, September', 'b7b998a9662f6178ba378c11f65a462a93719c5eae25b95c742504cc54fc89b8',
        'mcq', null, 'pending', 38, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('08fbd865-40d6-592c-8bcc-6eb4d193afef', 'b717f035-63d3-56fd-9345-fef12e7a63c3', 'A', 'July, May', '3c2c9326f71864c44e4307e92839ab088b5d93438c7c112a7b50274f4af627b1', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b7c08be7-296e-57cc-adbc-09a264a70734', 'b717f035-63d3-56fd-9345-fef12e7a63c3', 'B', 'July, April', '808e119a08ab3513538b945201939d706b3241a151cfde39afe8e0fafafcfcd7', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9a399ddf-483c-5188-91e7-08600460fc39', 'b717f035-63d3-56fd-9345-fef12e7a63c3', 'C', 'June, May', 'b450f6e05304b8b7818e26d1b181d92c86d772f6b823884bba246ceffa1d47ed', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('20d021bf-f933-5ef2-8f57-093f38d1cb23', 'b717f035-63d3-56fd-9345-fef12e7a63c3', 'D', 'June, April', '9690787fad3ce4d837067e4d66a621d5bd408eb9e1f7814fae29bfa61325910a', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('099188fa-547f-578e-af4e-ab51763167d5', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 39, 'Team X scored a total of N runs in 20 overs. Team Y tied the score in 10% less overs. Had Team Y’s average run rate (runs per over) been 50% higher, the scores would have been tied in 12 overs. How many runs were scored by Team X?', '7e586fabf44e470115eb1c69cf0ed013b857b6b113ef4e0269f2c82bbee8dd89',
        'mcq', null, 'pending', 39, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('044adaa2-d5c0-5e0a-9d87-75f2620f261a', '099188fa-547f-578e-af4e-ab51763167d5', 'A', '72', '8722616204217eddb39e7df969e0698aed8e599ba62ed2de1ce49b03ade0fede', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('698d9eda-5bd4-518f-9c13-1f83142b05c9', '099188fa-547f-578e-af4e-ab51763167d5', 'B', '144', '5ec1a0c99d428601ce42b407ae9c675e0836a8ba591c8ca6e2a2cf5563d97ff0', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7a38953c-67fc-5d91-896a-57010accc5fd', '099188fa-547f-578e-af4e-ab51763167d5', 'C', '216', '0f4121d0ef1df4c86854c7ebb47ae1c93de8aec8f944035eeaa6495dd71a0678', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('468547df-4c09-5a77-a6fd-43086edbb35b', '099188fa-547f-578e-af4e-ab51763167d5', 'D', 'Cannot be determined', '7edc73a1b0b4b27a170556560fffc727e48f7b1edc1aa0cfc7f4b9f6e71dacc4', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('df740ba9-3ecf-5245-8420-97ae001e1ca1', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 40, 'The price (p) of a commodity is first increased by k%, then decreased by k%; again increased by k%, and again decreased by k%. If the new price is q, then what is the relation between p and q?', '7d586691e2c0671fec208234582fa4e232dc1fdb095a9cc3ac6c48e6a55b4252',
        'mcq', null, 'pending', 40, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('df677a44-7fe6-59d3-a693-38dc8a095c0a', 'df740ba9-3ecf-5245-8420-97ae001e1ca1', 'A', 'p(10⁴ – k²)² = q × 10⁸', 'f8089793946a146ec4494ce6e8ced3d4af613e5229c870bb14a4d3c3bd13c64d', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('6d5b406f-04f1-5848-9b70-bae71e42803d', 'df740ba9-3ecf-5245-8420-97ae001e1ca1', 'B', 'p(10⁴ – k²)² = q × 10⁴', '74bd77f58881039f4166214e770e2c406848853d6dfec410e9cb6c20bd15b64c', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('94795f55-1ad3-5633-a5d7-5bbb3666868c', 'df740ba9-3ecf-5245-8420-97ae001e1ca1', 'C', 'p(10⁴ – k²) = q × 10⁴', '814c883bade919ec931cfe79eb79fb6081595c3cded9ff29be982c37d501521c', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4027f764-557f-5cce-af3a-e974e654375c', 'df740ba9-3ecf-5245-8420-97ae001e1ca1', 'D', 'p(10⁴ – k²) = q × 10⁸', '0b60292a1767468fa20ac3271c3f670698596d1c9e874be66e387c4854d0b73d', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('30bf27a7-228b-5352-a77d-f0066dbdbfe2', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 41, 'Which one of the following statements best reflects the most logical, rational and crucial message conveyed by the passage?', '24d23444e99bb2790d6f02be7453cb0a5fbf6a74aafc9efd3d79883d2f26aba4',
        'mcq', null, 'pending', 41, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('3f30e8d0-0ba7-57a8-bfb3-93fa9145e8a1', '30bf27a7-228b-5352-a77d-f0066dbdbfe2', 'A', 'We must use WPI exclusively in measuring price rise and CPI should be done away with.', 'a3072f70b417a765266f1a26caaea50a13ebb954a5558a20062ff56dea3fcfef', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('bcfd55c1-1856-52a8-8c2e-74c0fee640a9', '30bf27a7-228b-5352-a77d-f0066dbdbfe2', 'B', 'The present calculation of inflation rate does not correctly measure price rise of individual item/commodity.', '097db9f23830e982dce8acc0180e1678552cff9094efa97a5030f4d9fd2f08c2', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f62ddcf8-e842-5fbf-84e2-012afaca4100', '30bf27a7-228b-5352-a77d-f0066dbdbfe2', 'C', 'Inflation data under-presents services in the consumption basket.', '8a21a0b77f2c689e035a65e245efc80bceb1672ddc30a5db937f28627b44c885', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('35aa114d-94d3-528b-ae7a-02395fdcf6ca', '30bf27a7-228b-5352-a77d-f0066dbdbfe2', 'D', 'Knowledge of inflation rate is not really of any use to anybody in the country.', 'eaa7a07ca1026930b76cf55e34f6b7502dd70f2b613cbaef75fcb97ca5e7ab06', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('79859f28-7081-554d-ab6b-2cd69ceb7710', '30bf27a7-228b-5352-a77d-f0066dbdbfe2', '085ef831-dde8-5f15-a3df-8b5be6685d8e', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('3fdd07ff-9408-5b7f-a8f2-e3822b7cf289', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 42, 'Which one of the following statements best reflects the crux of the passage?', 'e63c2d75cbe271d08c75de5194f4fcf68cdccae6d661b895349d77cbaea3fc82',
        'mcq', null, 'pending', 42, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b6dc74c0-89e3-51b9-b6be-70e09a9fbaff', '3fdd07ff-9408-5b7f-a8f2-e3822b7cf289', 'A', 'Trustworthiness cannot be expected in entrepreneurship.', 'ef74da5d2264f26395b51170e48f16be3b7b9bb6ba426d89633c6143911a45a3', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('ca1591dc-5d02-5a28-97e0-380e42cac21f', '3fdd07ff-9408-5b7f-a8f2-e3822b7cf289', 'B', 'Trustworthy people are the most vulnerable people.', '786e2eef663469d763acfe08f888532ffdce1b4d9913617baead4dbb95a1c76e', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('ea43e386-a860-5025-b627-74a5e4302f79', '3fdd07ff-9408-5b7f-a8f2-e3822b7cf289', 'C', 'No economic activity is possible without being exposed to betrayal.', '35bf71aded89b7c566a7d40341276bc090ded9f69ac3ae3935b3263bcd802128', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('3dbf65c8-0a86-5cf4-b32a-9312e9b02034', '3fdd07ff-9408-5b7f-a8f2-e3822b7cf289', 'D', 'Trust is important though it entails risk.', '8e4e0e1ec5d4a809130121073dd1bd38222f3d699a3f6db334b923e9187b7fbb', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('67434e78-fe1c-52e9-9acc-cca6f67ff102', '3fdd07ff-9408-5b7f-a8f2-e3822b7cf289', 'cb3c57db-6e9c-5c2e-a18c-3ff079b5373d', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('8b22e00b-41f3-57e3-b21a-f0d72cef0cf2', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 43, 'A question is given followed by two Statements I and II. Consider the Question and the Statements and mark the correct option. Question: In a football match, team P playing against Q was behind by 3 goals with 10 minutes remaining. Does team P win the match? Statement I: Team P scored 4 goals in the last 10 minutes. Statement II: Team Q scored a total of 4 goals in the match. Which one of the following is correct in respect of the above Question and the Statements?', 'c86943f2a6adf873a34a278bb6707b447e7687817b185902d64a3439f60754f8',
        'mcq', null, 'pending', 43, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('723c87ed-064a-5148-a795-e163109ab693', '8b22e00b-41f3-57e3-b21a-f0d72cef0cf2', 'A', 'The Question can be answered by using one of the Statements alone, but cannot be answered using the other statement alone.', '9b4a4353a2dad85cb87cd98f12b02d07e0468e09777591eb089629c7dcac19bc', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4aa06748-3479-528b-a9ce-a47b7d646c76', '8b22e00b-41f3-57e3-b21a-f0d72cef0cf2', 'B', 'The Question can be answered by using either Statement alone.', 'c6a52774d6a59cabdee821eccc891f4aa5006009cf6d6e0d8150d2b684f7abcf', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('585a33ba-ad8a-5fc6-93f1-aee843e5941f', '8b22e00b-41f3-57e3-b21a-f0d72cef0cf2', 'C', 'The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone.', '4b0a5a21d244fb76ddc9ee4aeebb7a5b27ab08c133e58717104165819b1f1b96', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('62a9aec0-6466-5903-9cf5-a6017a5ccdc8', '8b22e00b-41f3-57e3-b21a-f0d72cef0cf2', 'D', 'The Question cannot be answered even using any of the Statements.', '554830c70679a892dc3c0de993a837977b8f20a91fe439126de4976fea733e61', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('4115ee5b-d67d-59c7-8a51-f4d6ec494e28', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 44, 'A question is given followed by two Statements I and II. Consider the Question and the Statements and mark the correct option. Question: Is (p + q)² − 4pq, where p, q are natural numbers, positive? Statement I: p < q. Statement II: p > q. Which one of the following is correct in respect of the above Question and the Statements?', '8e3d180554d7c0820916e4cdcb9fe6caf907eec621788acbc5c866b4b535bc56',
        'mcq', null, 'pending', 44, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('eb3900f1-68b3-55e8-8636-4d691e5f7d6c', '4115ee5b-d67d-59c7-8a51-f4d6ec494e28', 'A', 'The Question can be answered by using one of the Statements alone, but cannot be answered using the other statement alone.', '9b4a4353a2dad85cb87cd98f12b02d07e0468e09777591eb089629c7dcac19bc', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('2de347e9-a215-52ea-9dc3-c7b3f08148fb', '4115ee5b-d67d-59c7-8a51-f4d6ec494e28', 'B', 'The Question can be answered by using either Statement alone.', 'c6a52774d6a59cabdee821eccc891f4aa5006009cf6d6e0d8150d2b684f7abcf', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('1915e938-0a0f-580c-8215-78ba8827a03c', '4115ee5b-d67d-59c7-8a51-f4d6ec494e28', 'C', 'The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone.', '4b0a5a21d244fb76ddc9ee4aeebb7a5b27ab08c133e58717104165819b1f1b96', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('ccd436ef-cab8-505c-84f8-2b9df16d978a', '4115ee5b-d67d-59c7-8a51-f4d6ec494e28', 'D', 'The Question can be answered even without using any of the Statements.', 'ccb7d27f2a822f58d7cbf3e348fa57bf3275d9b76ee89efeae7e537a660c30a1', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('11b44cbd-6c88-579b-8394-c58cafe0a7a2', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 45, 'In a T20 cricket match, three players X, Y and Z scored a total of 37 runs. The ratio of number of runs scored by X to the number of runs scored by Y is equal to the ratio of number of runs scored by Y to number of runs scored by Z. Value-I = Runs scored by X; Value-II = Runs scored by Y; Value-III = Runs scored by Z. Which one of the following is correct?', 'be4fb675e5ec3854ab8cb3deef255c9a6a1f60534e723a7e388687fbf58760b8',
        'mcq', null, 'pending', 45, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('3d304744-3a75-54cc-a386-2840051ac9df', '11b44cbd-6c88-579b-8394-c58cafe0a7a2', 'A', 'Value-I < Value-II < Value-III', '3bc42d50f286c6943280419af0c39360b2f84817aa7196b9ef8a77dbeaf0f52f', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('1f6b2899-f52f-57bd-926c-096d9e0b7a57', '11b44cbd-6c88-579b-8394-c58cafe0a7a2', 'B', 'Value-III < Value-II < Value-I', 'c7053450c33ddf1d614624c70806f1f31e7a29126d13a0422f52a52bd73cf1f2', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9dfad3b2-c919-5a4d-93e2-74502ad4d6a4', '11b44cbd-6c88-579b-8394-c58cafe0a7a2', 'C', 'Value-I < Value-III < Value-II', '20ed4ff00a830e61b6eccd699c72e4f9f891525a44185177dcefd3fb389e16cf', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('c6d84a40-2923-520c-967c-f451e3669462', '11b44cbd-6c88-579b-8394-c58cafe0a7a2', 'D', 'Cannot be determined due to insufficient data', '00b114d07fab9bdd1d60350f29081f6497287dec4ca311e2abaa766ed15d1f01', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('71b2d2bb-3629-5ea2-8b5f-f3031726e1be', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 46, 'Let p + q = 10, where p, q are integers. Value-I = Maximum value of p × q when p, q are positive integers. Value-II = Maximum value of p × q when p ≥ −6, q ≥ −4. Which one of the following is correct?', 'cf405c4e50fc4b8404424dc301d4c9df6a37f0faeec8d04a6a8dd2f54c452f72',
        'mcq', null, 'pending', 46, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f72e9da7-5064-574f-aa47-72e2a598c96f', '71b2d2bb-3629-5ea2-8b5f-f3031726e1be', 'A', 'Value-I < Value-II', 'd729538fb8683194bf190ea2935e08ad3ccf0fb257e27a99f07e6c7db2248f4d', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('e4509c3e-403c-55c5-95e7-df1acebde419', '71b2d2bb-3629-5ea2-8b5f-f3031726e1be', 'B', 'Value-II < Value-I', '8e6652098178b73d90cef3e96c5f0963de5b2ca6d1bb7f285e3159a9fb7784af', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('be8de7ab-47da-5be2-9e83-5e36f891cde4', '71b2d2bb-3629-5ea2-8b5f-f3031726e1be', 'C', 'Value-I = Value-II', 'a13c6855fce97904f53f6323d6235fbe99e5de3f28489f41397f65c842fa7db7', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a58f5d84-5ebc-5640-917b-92926c5bb93a', '71b2d2bb-3629-5ea2-8b5f-f3031726e1be', 'D', 'Cannot be determined due to insufficient data', '00b114d07fab9bdd1d60350f29081f6497287dec4ca311e2abaa766ed15d1f01', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('e70186cc-ea81-53a2-8dad-1503c38b526d', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 47, 'Consider a set of 11 numbers: Value-I = Minimum value of the average of the numbers of the set when they are consecutive integers ≥ –5. Value-II = Minimum value of the product of the numbers of the set when they are consecutive non-negative integers. Which one of the following is correct?', '16f33c5439c91c714b0af7afca181115d37266ab7c5d0fccf0d10509e13e5f00',
        'mcq', null, 'pending', 47, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7ab72915-f023-5649-ac32-6faa2c8d5d49', 'e70186cc-ea81-53a2-8dad-1503c38b526d', 'A', 'Value-I < Value-II', 'd729538fb8683194bf190ea2935e08ad3ccf0fb257e27a99f07e6c7db2248f4d', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('5ab39036-1da7-519e-bd53-de8c53ae75eb', 'e70186cc-ea81-53a2-8dad-1503c38b526d', 'B', 'Value-II < Value-I', '8e6652098178b73d90cef3e96c5f0963de5b2ca6d1bb7f285e3159a9fb7784af', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f88ec5e9-f495-5946-9606-fd54e9bcf1b9', 'e70186cc-ea81-53a2-8dad-1503c38b526d', 'C', 'Value-I = Value-II', 'a13c6855fce97904f53f6323d6235fbe99e5de3f28489f41397f65c842fa7db7', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('bf321886-ef4f-5517-b3e6-a75ec496cdc9', 'e70186cc-ea81-53a2-8dad-1503c38b526d', 'D', 'Cannot be determined due to insufficient data', '00b114d07fab9bdd1d60350f29081f6497287dec4ca311e2abaa766ed15d1f01', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('62c33523-061f-552f-8ea8-94afdf284221', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 48, 'The average of three numbers p, q and r is k. p is as much more than the average as q is less than the average. What is the value of r?', '0df0ffc61a3af9766a940f007a0f6270ffab05391b0c446c5a093c6ed1670d5c',
        'mcq', null, 'pending', 48, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('1c0d071c-dbee-5df4-bf6a-fd9e5d52794b', '62c33523-061f-552f-8ea8-94afdf284221', 'A', 'k', '8254c329a92850f6d539dd376f4816ee2764517da5e0235514af433164480d7a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('e6dcd57b-eff1-5ca6-8315-dcbdd42387ec', '62c33523-061f-552f-8ea8-94afdf284221', 'B', 'k – 1', 'b2011b06f168c17a88818c9bd6c025ce3b0d61fb47f34b953f61e28c6f9c5344', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('0415d063-a518-5f15-b6e3-4e92104211e3', '62c33523-061f-552f-8ea8-94afdf284221', 'C', 'k + 1', '829fd13894e3fc52515ed8cc01886dfd8f20a492527f0eff9a0a4114945afde6', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('8343a1af-74dd-5eb8-8cff-3487dfa23d97', '62c33523-061f-552f-8ea8-94afdf284221', 'D', 'k/2', 'f526ee7bcca4cfca6df4250bdedcb6b62f9fe544c7e1318b05443cf5b96e48db', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('15159d2a-b2de-570a-bcbb-ee007be54556', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 49, 'Let x be a real number between 0 and 1. Which of the following statements is/are correct? I. x² > x³ II. x > √x Select the correct answer using the code given below:', 'cac4598b7f8a40360a041c629ee89c5e6e2b297ac6496861dd3657240c40d727',
        'mcq', null, 'pending', 49, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('e5c6054b-a77e-53f5-84fc-77b49731ac54', '15159d2a-b2de-570a-bcbb-ee007be54556', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4da4b572-cff7-5f02-8405-dbd6a6024b3f', '15159d2a-b2de-570a-bcbb-ee007be54556', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('01613443-7bb1-534a-b11a-09e4ee0069ab', '15159d2a-b2de-570a-bcbb-ee007be54556', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('6e8d6420-e9e6-5b31-97b9-74c7e43b9c6c', '15159d2a-b2de-570a-bcbb-ee007be54556', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('7440c9f0-ffd2-5cfa-8622-61309771ad42', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 50, 'The difference between any two natural numbers is 10. What can be said about the natural numbers which are divisible by 5 and lie between these two numbers?', 'ed081e81a74b432e6c7eeb7d63656178e244c95c6b2b5f7d11e8398faba97260',
        'mcq', null, 'pending', 50, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('2d183854-14d2-5e65-bf9d-f39eb99d9463', '7440c9f0-ffd2-5cfa-8622-61309771ad42', 'A', 'There is only one such number.', 'fc9dfbef3136be01740c714bac63e1541db737890c924fe1b4cc6db19dc7354c', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7ef0b075-c8c1-5d34-b9bd-e0ee543859ad', '7440c9f0-ffd2-5cfa-8622-61309771ad42', 'B', 'There are only two such numbers.', 'cb63a69cf6d74ea23475e8d198fc78834ab530dcdcc5ee687f368e45466a1d8a', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('13b05c3a-0a29-5aff-8126-ed326bae64ae', '7440c9f0-ffd2-5cfa-8622-61309771ad42', 'C', 'There can be more than one such number.', 'd128d8ffc0fc38b029103df8d309b5d3dd43e11724052f06dd1247627beb65fb', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f88c6eef-dcd7-5b00-baf3-5979a1f482ee', '7440c9f0-ffd2-5cfa-8622-61309771ad42', 'D', 'No such number exists.', '635b1ad101005ef64de1b4f2feb3c482dd0cf001d224f0952f35aadef84d1528', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('e83d03f7-40a5-57bc-8d46-d48eb99d4ded', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 51, 'Which one of the following statements best reflects the critical message conveyed by the author of the passage?', 'e6479c76922840595b3f5ab68e3451ad6cad556d2a5fb9f970c90f5fae09b2e2',
        'mcq', null, 'pending', 51, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('802c67c8-0545-56a4-b9d8-95b45cee0d92', 'e83d03f7-40a5-57bc-8d46-d48eb99d4ded', 'A', 'Corporate capitalism is important for economic growth of a State and also for democracy.', '77d388670cca1f2378e3f50bc74b514a0876b99b4572e792b172429756693a91', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('5475a123-f2b6-57a3-97f3-7ba6ae23129f', 'e83d03f7-40a5-57bc-8d46-d48eb99d4ded', 'B', 'Corporate capitalism is imperative for a modern State to achieve its political objectives.', 'db00998b0a78093b12c09808528e369928dbaa0f54ca4e85d0dae9558969f2ae', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('2be6b4ca-59f1-5cbe-8206-39281ce8259f', 'e83d03f7-40a5-57bc-8d46-d48eb99d4ded', 'C', 'No State can ensure its economic survival for long without the role of corporate capitalism.', '7b61495dddd28aacda7b7ab9a11c807df6ffb8df311249b2d53eb15fdfba7e00', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('fff2c133-e33d-5989-bba9-8848fa75b576', 'e83d03f7-40a5-57bc-8d46-d48eb99d4ded', 'D', 'Corporate capitalism and democracy have mutual dependence for their continued existence.', '51195e42f941c80377410a7360ba1340bfb623a7894383a2c83bf880c2793d7a', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('e4b6a0d1-ed6f-5292-8f52-a39b1ed118fa', 'e83d03f7-40a5-57bc-8d46-d48eb99d4ded', '7d7cdf44-24a2-5a4e-beaa-c9451d8eb5bb', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('8f9c1e10-dd32-5dc9-ac21-5e266f903082', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 52, 'With reference to the above passage, the following assumptions have been made: I. Corporate capitalism promotes the growth of labour force and provides more employment opportunities. II. Poor and marginalized sections of population are benefited by corporate capitalism due to trickle-down effect. Which of the above assumptions is/are valid?', '074ffcdc54ab1cc94af88e692be701a248ae4c07bb0b895182c72c80b7856264',
        'mcq', null, 'pending', 52, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('3f5befc3-1754-57a2-b51a-800131cc05ab', '8f9c1e10-dd32-5dc9-ac21-5e266f903082', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9adc264b-c619-5380-91cd-8e61a7e1b8df', '8f9c1e10-dd32-5dc9-ac21-5e266f903082', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f99811cb-fbd2-55c1-a5ff-d644fc46c43b', '8f9c1e10-dd32-5dc9-ac21-5e266f903082', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('bcae0582-c563-5434-b643-9bed5bed3d77', '8f9c1e10-dd32-5dc9-ac21-5e266f903082', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('d49e7bab-86c8-5ce0-8df0-e6e50e20484e', '8f9c1e10-dd32-5dc9-ac21-5e266f903082', '7d7cdf44-24a2-5a4e-beaa-c9451d8eb5bb', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('7606b3e0-722d-5ed1-8471-84da1ed3489a', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 53, 'Which one of the following statements reflects the best explanation of the above passage?', 'fd89351357a24951ec8a905ff219696c196d48b6840fc23dc9a1d6481fe28de3',
        'mcq', null, 'pending', 53, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a1dc877f-fa4c-50f8-ad74-0e83949ac0cc', '7606b3e0-722d-5ed1-8471-84da1ed3489a', 'A', 'It emphasizes the inability of the State to enforce its will in practice against the opposition of certain groups within it.', '5bd07993e2f809d7c8d06123afd9f19d24ff8925dccbd39913ff273d0ec27cbd', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9f3b930f-8a7f-5c9c-818e-5a1e3b3717a9', '7606b3e0-722d-5ed1-8471-84da1ed3489a', 'B', 'It is a cooperative organization for the promotion of the well-being and development of the personality of its members.', '97beb733c54a235b3a02e5210c8ec8e37d9eeeb22a5603ccf7fa85a6786e57de', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('8d77844b-a077-5c26-9040-939212ad9c2d', '7606b3e0-722d-5ed1-8471-84da1ed3489a', 'C', 'It takes individuals out of a state of isolation and gives them a chance to participate in the common endeavour.', 'f1b2a4be0a52e3f22bef4aa885192792427b217a139ff3a886af07f141722a3b', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('c2d8af4b-c557-5429-9ee7-4e32258d32c1', '7606b3e0-722d-5ed1-8471-84da1ed3489a', 'D', 'It permits citizens to have a variety of loyalties and allegiance.', '2900a38b83ad0422ee42a2fc1c8c124414fbb626545ee02fd1d57dfee6353e1a', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('c64e2feb-c443-5708-8220-cf0ae4b3e34c', '7606b3e0-722d-5ed1-8471-84da1ed3489a', 'f42e041a-8854-55cf-bb81-156974b33fce', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('8f89546d-0ced-53bc-aa9b-3ea1bd4e075a', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 54, 'Consider the following statements: I. There exists a natural number which when increased by 50% can have its number of factors unchanged. II. There exists a natural number which when increased by 150% can have its number of factors unchanged. Which of the statements given above is/are correct?', '8b9d86a54833d75f5657275ade22bdf467e70ff925e2c8eb9c3285608d3075be',
        'mcq', null, 'pending', 54, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7fd8333d-4a97-562a-a0f9-3910cd0cce07', '8f89546d-0ced-53bc-aa9b-3ea1bd4e075a', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('2bd2d6e8-7eb7-52bd-a58a-2518c8830ae5', '8f89546d-0ced-53bc-aa9b-3ea1bd4e075a', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('fa03bab6-910d-55ad-8deb-ee5a21c7bc58', '8f89546d-0ced-53bc-aa9b-3ea1bd4e075a', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('2faea2a5-6a9f-5e99-9281-4795fb29ed68', '8f89546d-0ced-53bc-aa9b-3ea1bd4e075a', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('45909f5c-f1d9-5649-92f5-0b6e6e4873c7', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 55, 'There are 7 places A, B, C, D, E, F and G in a city connected by various roads AB, AC, CD, DE, BF, EG and FG. A is 6 km south of B. A is 10 km west of C. D is 5 km east of E. C is 6 km north of D. F is 9 km west of B. F is 12 km north of G. A person travels from D to F through these roads. What is the distance covered by the person?', 'bad781ddaf7cdfad97064568abdf800acbb49fb4f50a616b487185928c67a1d3',
        'mcq', null, 'pending', 55, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4009dab8-f5a6-5851-b510-4d7e634c3317', '45909f5c-f1d9-5649-92f5-0b6e6e4873c7', 'A', '20 km', 'cc63f92001687d2542814b143787b54ce50e076ed13d726fc2cd05f7fc88eeaa', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a623e6ba-ba89-5b7c-8f0a-1797756450c4', '45909f5c-f1d9-5649-92f5-0b6e6e4873c7', 'B', '25 km', '488dce20871cfc599922ae1a9838ce4ce71d5f5e495d1c4044133d77e004ced1', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b2a1a5af-5c03-5932-8f4f-a0a2fc2b27fc', '45909f5c-f1d9-5649-92f5-0b6e6e4873c7', 'C', '31 km', 'cdca5bd4a26388ad223074c908b2b42fbf335a9ad36851f1676c60f461ad03eb', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('17d4a672-ff70-544e-b623-21b5f72d7e31', '45909f5c-f1d9-5649-92f5-0b6e6e4873c7', 'D', '37 km', '4cb3016b5bbdf8a2e260dc5bd6866e1c48e7165878d94f35543394c2965f7484', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('8f67701d-a80a-5f2f-a20c-d87fa7565477', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 56, 'In a certain code if 64 is written as 343 and 216 is written as 729, then how is 512 written in that code?', 'b093658e371f739498c5901af56464816eeb757d65888581f74acd318aebc186',
        'mcq', null, 'pending', 56, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('ea1a20a4-6888-56a8-a211-379324a1c388', '8f67701d-a80a-5f2f-a20c-d87fa7565477', 'A', '1000', '40510175845988f13f6162ed8526f0b09f73384467fa855e1e79b44a56562a58', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b7806809-4ad1-503f-8967-9fa6ad631c5b', '8f67701d-a80a-5f2f-a20c-d87fa7565477', 'B', '1331', '7ba7d31bfa1ed86327ecfa9deb2dd8a44488fba943ca78c86c1e21f2d1be0a10', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f511f6d5-4436-51be-a599-0f0bc56e07b1', '8f67701d-a80a-5f2f-a20c-d87fa7565477', 'C', '1728', 'a0bd94956b9f42cde97b95b10ad65bbaf2a8d87142caf819e4c099ed75126d72', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('3e6ff845-69f1-596e-a07b-8f39b853d525', '8f67701d-a80a-5f2f-a20c-d87fa7565477', 'D', '2197', '2bbb0ed9e593487865218631abc18ea0cdd660ca87da8c55382a5cc05f72c1eb', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('7b2cbc06-c889-5205-a669-c5d2c72cc426', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 57, 'What is the remainder when 9³ + 9⁴ + 9⁵ + 9⁶ + ... + 9¹⁰⁰ is divided by 6?', '2ea5c7d88d253de6d0fe0e3805bbe0a17ef15509fac2e195dd7cc85df8f7c2a2',
        'mcq', null, 'pending', 57, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('c9a9c0e1-476f-56ee-a53e-a414578f7cc7', '7b2cbc06-c889-5205-a669-c5d2c72cc426', 'A', '0', '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9327d369-d5c4-5073-a049-3d3624a6a00d', '7b2cbc06-c889-5205-a669-c5d2c72cc426', 'B', '1', '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('dd7b6b26-bdef-56dc-971c-00fa859ca606', '7b2cbc06-c889-5205-a669-c5d2c72cc426', 'C', '2', 'd4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('1824cf6e-c0d5-5754-8e63-88b9324590c3', '7b2cbc06-c889-5205-a669-c5d2c72cc426', 'D', '3', '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('8798cdcd-a73f-5cf5-90d6-216b6a0959c6', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 58, 'A question is given followed by two Statements I and II. Consider the Question and the Statements and mark the correct option. Question: What is the smallest 1-digit number having exactly 4 distinct factors? Statement I: 2 is one of the factors. Statement II: 3 is one of the factors. Which one of the following is correct in respect of the above Question and the Statements?', 'bdd796a79ab27cf6d967b9232521409107624ac98a797acf3c753ee19b79f6c4',
        'mcq', null, 'pending', 58, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b4933200-0ef6-51d4-a7b9-5310f0caa752', '8798cdcd-a73f-5cf5-90d6-216b6a0959c6', 'A', 'The Question can be answered by using one of the Statements alone, but cannot be answered using the other statement alone.', '9b4a4353a2dad85cb87cd98f12b02d07e0468e09777591eb089629c7dcac19bc', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4deb1c37-4563-5e87-b9a5-e11004aff8a3', '8798cdcd-a73f-5cf5-90d6-216b6a0959c6', 'B', 'The Question can be answered by using either Statement alone.', 'c6a52774d6a59cabdee821eccc891f4aa5006009cf6d6e0d8150d2b684f7abcf', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('45c6570e-ad96-5a6e-993b-858dc9a3b168', '8798cdcd-a73f-5cf5-90d6-216b6a0959c6', 'C', 'The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone.', '4b0a5a21d244fb76ddc9ee4aeebb7a5b27ab08c133e58717104165819b1f1b96', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f084fe35-cbde-5de8-925d-e17c1da57eda', '8798cdcd-a73f-5cf5-90d6-216b6a0959c6', 'D', 'The Question can be answered even without using any of the Statements.', 'ccb7d27f2a822f58d7cbf3e348fa57bf3275d9b76ee89efeae7e537a660c30a1', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('c346db98-cdf5-5efd-96e8-a64b9cd4863c', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 59, 'A question is given followed by two Statements I and II. Consider the Question and the Statements and mark the correct option. Question: Let P, Q, R, S be distinct non-zero digits. If PP × PQ = RRSS, where P ≤ 3 and Q ≤ 4, then what is Q equal to? Statement I: R = 1. Statement II: S = 2. Which one of the following is correct in respect of the above Question and the Statements?', 'c6358e297299ef328bf169024cf3736e6181f3c6142cb1edab9821c290396f4e',
        'mcq', null, 'pending', 59, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('c6e518a6-afb4-5d8d-9419-b0c9876a2a9e', 'c346db98-cdf5-5efd-96e8-a64b9cd4863c', 'A', 'The Question can be answered by using one of the Statements alone, but cannot be answered using the other statement alone.', '9b4a4353a2dad85cb87cd98f12b02d07e0468e09777591eb089629c7dcac19bc', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('2734c3f9-1794-57f5-9342-1799eaf805d2', 'c346db98-cdf5-5efd-96e8-a64b9cd4863c', 'B', 'The Question can be answered by using either Statement alone.', 'c6a52774d6a59cabdee821eccc891f4aa5006009cf6d6e0d8150d2b684f7abcf', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f8b68cd1-ffdf-581d-a63a-8b161cda802a', 'c346db98-cdf5-5efd-96e8-a64b9cd4863c', 'C', 'The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone.', '4b0a5a21d244fb76ddc9ee4aeebb7a5b27ab08c133e58717104165819b1f1b96', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('16a4b0b0-d27c-5420-874c-e311a0caa6f4', 'c346db98-cdf5-5efd-96e8-a64b9cd4863c', 'D', 'The Question can be answered even without using any of the Statements.', 'ccb7d27f2a822f58d7cbf3e348fa57bf3275d9b76ee89efeae7e537a660c30a1', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('cc197b14-a56c-5188-9dcd-44be994c31a4', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 60, 'A question is given followed by two Statements I and II. Consider the Question and the Statements and mark the correct option. Question: How is Q related to P? Statement I: P has two sisters, R and S. Statement II: R’s father is the brother of Q. Which one of the following is correct in respect of the above Question and the Statements?', 'bb61f42902b6562be1b697ab502a9dd6362236d8e2efb89b812e8e5600eec174',
        'mcq', null, 'pending', 60, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('41061aa6-2f90-5872-93fd-397bab712b2b', 'cc197b14-a56c-5188-9dcd-44be994c31a4', 'A', 'The Question can be answered by using one of the Statements alone, but cannot be answered using the other statement alone.', '9b4a4353a2dad85cb87cd98f12b02d07e0468e09777591eb089629c7dcac19bc', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('51537135-c9c0-53f5-aadc-eb4b3e88b846', 'cc197b14-a56c-5188-9dcd-44be994c31a4', 'B', 'The Question can be answered by using either Statement alone.', 'c6a52774d6a59cabdee821eccc891f4aa5006009cf6d6e0d8150d2b684f7abcf', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('05b96d1c-73b5-5d18-adf0-fa732a746e3b', 'cc197b14-a56c-5188-9dcd-44be994c31a4', 'C', 'The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone.', '4b0a5a21d244fb76ddc9ee4aeebb7a5b27ab08c133e58717104165819b1f1b96', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7e96530c-fd88-5770-af0a-ac4b4a93d020', 'cc197b14-a56c-5188-9dcd-44be994c31a4', 'D', 'The Question cannot be answered even using any of the Statements.', '554830c70679a892dc3c0de993a837977b8f20a91fe439126de4976fea733e61', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('20b8d1ca-6eee-5fef-b68f-0ee65591b94d', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 61, 'Which one of the following statements best reflects the central idea conveyed by the passage?', '4103aa7d1a5fe39a473aa7bd97a7a2d7dd261c65f4851a0807dec594bb5e23ec',
        'mcq', null, 'pending', 61, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4f33ae82-d427-5136-94f6-89d2ede6df73', '20b8d1ca-6eee-5fef-b68f-0ee65591b94d', 'A', 'Global climate change adversely affects the productivity of crops.', 'd099945c21bc8d96bebefbeb89139749ed29428c378532adea2edeedb332acb5', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('ced2507f-c3a2-58e1-a63f-e924352d99a5', '20b8d1ca-6eee-5fef-b68f-0ee65591b94d', 'B', 'Our total dependence on genetically honed crops entails possible food insecurity.', '22e5aa51d16aa1f9247a1703fc4034ed1e448b0aa93fa3c1fb78ca6fbbd3d760', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('645d15f3-60d2-5a33-b409-56b825715d1b', '20b8d1ca-6eee-5fef-b68f-0ee65591b94d', 'C', 'Our food security should not depend on agricultural productivity alone.', '5bf41590d916a7c713d40df876fc46d2e4a533d0acfd8c75a2b8788f6c81472f', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('31c67257-7fe4-5522-85b7-cb5250007d40', '20b8d1ca-6eee-5fef-b68f-0ee65591b94d', 'D', 'Genetically honed crops should be replaced with their wild varieties in our present cultivation practices.', '7f5c9c9e8975003c2c48470002ddee261f5ee23c5f5b7200da983180304ae0b5', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('81b4e1d5-faa7-5bad-b61f-c0421f6dd9da', '20b8d1ca-6eee-5fef-b68f-0ee65591b94d', '4953001e-f983-5f47-b860-c912453947a5', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('f6a87a91-85ec-5f1d-b592-1206643a6f9f', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 62, 'With reference to the above passage, the following assumptions have been made: I. Global climate change can result in the migration of several plant diseases to new areas. II. Scientific understanding of the wild relatives of our present crops would enable us to strengthen food security. Which of the above assumptions is/are valid?', 'a464603914dde31c7ab31f920087c32c305e60c46fa2d255a4283263723d2f04',
        'mcq', null, 'pending', 62, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4805290b-c6cd-512c-ba09-4701b3a85a31', 'f6a87a91-85ec-5f1d-b592-1206643a6f9f', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('369716fa-7b2b-532c-ba65-f3e5895ea3e8', 'f6a87a91-85ec-5f1d-b592-1206643a6f9f', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('fc93857c-0451-5a54-a8fe-7d38ac6f5907', 'f6a87a91-85ec-5f1d-b592-1206643a6f9f', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('cb7d4b21-e1ef-5a26-b5a5-4437dd1ebaa2', 'f6a87a91-85ec-5f1d-b592-1206643a6f9f', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('60827d97-aed3-51bd-8244-f47686a8566c', 'f6a87a91-85ec-5f1d-b592-1206643a6f9f', '4953001e-f983-5f47-b860-c912453947a5', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('4e0f0a0c-8d00-54a8-9aee-fe5f0adcf4ee', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 63, 'Which one of the following statements best reflects the critical message conveyed by the author of the passage?', 'f4ee272c4559d8c3f604e28b1b5c37cb77c67f1c0e40d846e6913f6ee5710b92',
        'mcq', null, 'pending', 63, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('3d3f1517-e10f-5158-b444-933b1d1bc824', '4e0f0a0c-8d00-54a8-9aee-fe5f0adcf4ee', 'A', 'Without opposition parties, the administration in a democracy gets to become more responsible.', '7d2ef56120b9e228b523909451e4fa930cf165693307181ee3091a9aac3f52eb', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('68810803-aca6-53cd-897f-06bcdd6f557e', '4e0f0a0c-8d00-54a8-9aee-fe5f0adcf4ee', 'B', 'Democracy needs to have revolutionaries in opposition to keep the government alert.', 'b0e7157112abcbb05b02d1b973454cdd1a1c7d6623baac95f276cf9f556c0833', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('6497d0b0-e5cc-5a17-a1b0-117d4556879a', '4e0f0a0c-8d00-54a8-9aee-fe5f0adcf4ee', 'C', 'Rulers in a democracy need the support of opposition for their political survival.', 'a9017b6964f3bbfddba6f6feeb7903a403f5c5a34a6e414f514830b7745c8e79', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('002a3a03-921c-56ef-af8e-6445b14c8aea', '4e0f0a0c-8d00-54a8-9aee-fe5f0adcf4ee', 'D', 'In a democracy, the opposition is indispensable for the balance of political power and good governance.', 'f87932576b733526610347427a9958f35c17a95e21e47a1cef624ea25844a4df', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('8eaa2231-8b35-5496-88ea-591bedc1b940', '4e0f0a0c-8d00-54a8-9aee-fe5f0adcf4ee', 'f7806d43-1c8a-5fa4-abcc-af6ad8ab2a1b', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('52e3d938-1a4d-577f-a81a-aebfc1980eea', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 64, 'With reference to the above passage, the following assumptions have been made: I. In a democracy, a strong opposition is required only if the Head of Government is indifferent. II. The more aggressive the opposition, the better is the governance in a democracy. Which of the above assumptions is/are valid?', '6c1b77904aaae815472d588c087b155b7d9e36e7ce8f5232f7089cd5ba281af8',
        'mcq', null, 'pending', 64, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9566ad2c-8ead-5cc2-a077-f6e3d21a0463', '52e3d938-1a4d-577f-a81a-aebfc1980eea', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('5e725109-a11e-54a4-b4d8-eb11a5c3dd7d', '52e3d938-1a4d-577f-a81a-aebfc1980eea', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('fa1a2533-599c-5952-bc98-c5e791f8f3d8', '52e3d938-1a4d-577f-a81a-aebfc1980eea', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('949e7421-7926-5979-930a-12d6be1e78c6', '52e3d938-1a4d-577f-a81a-aebfc1980eea', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('e41d0145-4fc3-52a6-b046-be13a553c042', '52e3d938-1a4d-577f-a81a-aebfc1980eea', 'f7806d43-1c8a-5fa4-abcc-af6ad8ab2a1b', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('f1a5801c-0a79-57ac-a438-0bc3ae15c169', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 65, 'P is the brother of Q and R. S is R’s mother. T is P’s father. How many of the following statements are definitely true? I. S and T are a couple. II. Q is T’s son. III. T is Q’s father. IV. S is P’s mother. V. R is T’s daughter. VI. P is S’s son. Select the correct answer using the code given below:', 'd02dc4df7d9fbe4c3f736cfc771d330982e77ddb21ee2bf2c2f7f84fba938613',
        'mcq', null, 'pending', 65, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('fa1f7fa4-4622-5148-9f9e-69ef3b43de90', 'f1a5801c-0a79-57ac-a438-0bc3ae15c169', 'A', 'Only two', 'a03709cf4d8b75d281ae5b318d0a94cbece1450caf53b8e7806845dd2240edab', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('99349474-4270-5318-898e-33c6fc168a51', 'f1a5801c-0a79-57ac-a438-0bc3ae15c169', 'B', 'Only three', '75e3b2d1584ef326166fb1fd942592d9d43c09888811e092f8d33a6a8f8de89a', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b4b73a61-2ba2-5d70-a5fd-47ab6c6b05ed', 'f1a5801c-0a79-57ac-a438-0bc3ae15c169', 'C', 'Only four', 'f0a59c2f2927f350aa52576099f6143130be88e9f745ca4776cae89f3af52e0c', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9ff68a3b-3ac0-5cb3-9915-c4aacbee84e0', 'f1a5801c-0a79-57ac-a438-0bc3ae15c169', 'D', 'Only five', '34455a1240f36b8145601660eda4f6d23dd2680e64d3d44ab330a613873a0f8c', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('dcdfa617-1b12-58c7-a85a-51972a6b0d51', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 66, 'If NO is coded as 210, NOT is coded as 4200 and NOTE is coded as 21000, then how is NOTES coded?', 'b1c452c2d7faa47bd4fa7fc9355844d133d2cd83912117da91d07b247e925236',
        'mcq', null, 'pending', 66, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a8902e69-fbcd-5326-9547-9dc205cf0b05', 'dcdfa617-1b12-58c7-a85a-51972a6b0d51', 'A', '399000', '7df63326206b633760bb5924dc85d2da37d24ff5f816a5f38d2b6a7c99ab7365', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('a87b7322-3a1a-51ca-8e0c-3b97ca1c296d', 'dcdfa617-1b12-58c7-a85a-51972a6b0d51', 'B', '420000', 'c74cc85badcf13b0d9704ec9f8645aee901600d4167e32d00527481fcb8aa25f', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('69ddd9fa-d1ba-535b-ad91-773e55771fb8', 'dcdfa617-1b12-58c7-a85a-51972a6b0d51', 'C', '440000', '9c6d03e8a8f97d507233db8890e43f90c6fb9a609fe08ad27f248172524706c1', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('072cdaa4-6df3-5b4a-a681-dc88c6f9ade8', 'dcdfa617-1b12-58c7-a85a-51972a6b0d51', 'D', '630000', '31c06104dd27b91ab298f81ed528caf6f438ecdf1122c7640008d9f9ab4a9943', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('a7d893c8-bfb0-596d-b1a1-b5e6b68f7ae2', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 67, 'If FRANCE is coded as 654321 and GERMANY is coded as 9158437, then how is YEMEN coded?', '0d3fc0f569e65844610a53ad1301e7969c3a5ee8adc51440ebb8ea61be61fda7',
        'mcq', null, 'pending', 67, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('64a79f68-62d2-55c1-84f0-5f9a29de93d3', 'a7d893c8-bfb0-596d-b1a1-b5e6b68f7ae2', 'A', '54321', '20f3765880a5c269b747e1e906054a4b4a3a991259f1e16b5dde4742cec2319a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('d080a3ec-a06a-50fd-a3b4-32edf1758694', 'a7d893c8-bfb0-596d-b1a1-b5e6b68f7ae2', 'B', '81913', 'ad2963452122f4dfb9675f078d56f3daa981b02066efebf76985b5ae451762ed', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('3503ec91-cd54-5df3-a4ae-d605ea056375', 'a7d893c8-bfb0-596d-b1a1-b5e6b68f7ae2', 'C', '71913', 'af7a393ce6a41a571516d092dfdeef8b356c17af76d39e8bc3a8f878f072763c', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b0b3a061-279a-52d0-9e1a-1e84ed2afd76', 'a7d893c8-bfb0-596d-b1a1-b5e6b68f7ae2', 'D', '71813', 'fc2952a7b4cc9b529a76edddf78cf4dffdf5edd318cbd6106fae784ad103c256', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('359f6a10-a8a5-5ad0-af2f-8eaf43c37be0', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 68, 'The 5-digit number PQRST (all distinct digits) is such that T is not equal to 0. P is thrice T. S is greater than Q by 4, while Q is greater than R by 3. How many such 5-digit numbers are possible?', '6621bac8a5a421fc0bb143deb64667a4b05749ffe0dde91b01068d8976f5d046',
        'mcq', null, 'pending', 68, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('539a45f7-61c3-5a03-b23b-c517acbb7e3a', '359f6a10-a8a5-5ad0-af2f-8eaf43c37be0', 'A', '3', '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('88a168a3-91c4-56e7-b479-4e1abdb4be15', '359f6a10-a8a5-5ad0-af2f-8eaf43c37be0', 'B', '4', '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('70ff51d8-b407-53d2-ab5f-6a9b9e84360e', '359f6a10-a8a5-5ad0-af2f-8eaf43c37be0', 'C', '5', 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('29005c6c-01b6-5d0c-8bf3-e3ecad4a5298', '359f6a10-a8a5-5ad0-af2f-8eaf43c37be0', 'D', '6', 'e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('042ace89-c104-5fc9-a407-5f2519196755', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 69, 'X can complete one-third of a certain work in 6 days, Y can complete one-third of the same work in 8 days and Z can complete three-fourth of the same work in 12 days. All of them work together for n days and then X and Z quit and Y alone finishes the remaining work in 8 2/3 days. What is n equal to?', '918c26a854dd83c142baf6b3528ac95cbd1628abdf5cdf67461e8e7cda441b53',
        'mcq', null, 'pending', 69, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('30ac6ca0-8a02-559c-a1e0-1dd849249190', '042ace89-c104-5fc9-a407-5f2519196755', 'A', '3', '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('0f46976c-cb0c-575d-8dc1-a46dedde6c54', '042ace89-c104-5fc9-a407-5f2519196755', 'B', '4', '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b7435cf6-f1ad-561f-a9ea-6371db72c35f', '042ace89-c104-5fc9-a407-5f2519196755', 'C', '5', 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('65217d60-831a-5385-85f6-6b9049ba52c7', '042ace89-c104-5fc9-a407-5f2519196755', 'D', '6', 'e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('63e1255a-7d3d-5c1d-8bb8-2b8b4051c579', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 70, 'What is X in the sequence 1, 3, 6, 11, 18, X, 42?', '6e20905f0dcbae3359a535274e84889f526afcf6bfc4023104a7daa74a9864ef',
        'mcq', null, 'pending', 70, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('c1b89d1b-0e63-5124-a6f6-3d3f525cf7cb', '63e1255a-7d3d-5c1d-8bb8-2b8b4051c579', 'A', '26', '5f9c4ab08cac7457e9111a30e4664920607ea2c115a1433d7be98e97e64244ca', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b05f2b82-4798-51e8-a5f3-7c910308521f', '63e1255a-7d3d-5c1d-8bb8-2b8b4051c579', 'B', '27', '670671cd97404156226e507973f2ab8330d3022ca96e0c93bdbdb320c41adcaf', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('cd0487e6-7529-55b6-aa17-5b1d7a2022da', '63e1255a-7d3d-5c1d-8bb8-2b8b4051c579', 'C', '29', '35135aaa6cc23891b40cb3f378c53a17a1127210ce60e125ccf03efcfdaec458', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7de6ec75-00ba-50e5-baec-fc12cedd7603', '63e1255a-7d3d-5c1d-8bb8-2b8b4051c579', 'D', '30', '624b60c58c9d8bfb6ff1886c2fd605d2adeb6ea4da576068201b6c6958ce93f4', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('872b98f8-b23b-5e16-9e74-32d5098f8610', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 71, 'Which one of the following statements best reflects the central idea conveyed by the passage?', 'a42c8365e839720f8e1cbbe397e077116eca7a0252c0e4564281e3703ef620b6',
        'mcq', null, 'pending', 71, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('5c8fdc24-6e03-5cb7-8e73-9545a945ef64', '872b98f8-b23b-5e16-9e74-32d5098f8610', 'A', 'Moving to net-zero carbon is possible only by the reduction in household emissions.', 'ff56592d04f3fc2e0b0ad36b98afc7aff7390812262b5a18a3f9b66f0612ca79', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('30cdda57-2be7-5cc2-aed9-54455773ccb2', '872b98f8-b23b-5e16-9e74-32d5098f8610', 'B', 'Low-carbon behaviour in people can be brought about by incentivising them.', 'd76990e5d7043875b338cf51de7f261c2e381dfe52ce28cac48020dbecc39960', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('cd068872-863a-512e-bf17-7fe93bc82bb2', '872b98f8-b23b-5e16-9e74-32d5098f8610', 'C', 'Cheaper goods and services can be made available to people by using low-carbon technologies.', 'ef224e013475f017454e6f1d974cb3fa2dc3b0c3d4553c98e0ac1be503a19bf2', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('8b4ba958-a859-5559-ac69-0a0b2ca4900a', '872b98f8-b23b-5e16-9e74-32d5098f8610', 'D', 'Manufacturing industries that use low-carbon technologies should be provided with subsidies.', 'a546c0834e554f314bc74ce72808bd041c2f681a738c77e1282a89175f4f4198', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('6df61db8-5859-560b-8c43-760a9eb7108c', '872b98f8-b23b-5e16-9e74-32d5098f8610', '2beb3085-faec-5c50-89d4-4bbf61b59ea3', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('2835c2ce-f205-5677-a6d6-23fbd0c59508', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 72, 'With reference to the above passage, the following assumptions have been made: I. Supply-side investments in companies can result in low-carbon behaviour in people. II. People are not capable of adapting low-carbon behaviour without the involvement of Government and Companies. Which of the above assumptions is/are valid?', '0519e6b45c38f5152d607cbd937e983b163b546b1ec1f6412486b6da635bc212',
        'mcq', null, 'pending', 72, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('eea8b5f0-9aa9-5643-a336-74b8105917c0', '2835c2ce-f205-5677-a6d6-23fbd0c59508', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('36126f85-4d6f-5dec-9447-934f1dc90d87', '2835c2ce-f205-5677-a6d6-23fbd0c59508', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('8ac0eb33-53c9-5555-9989-221eca1a25ac', '2835c2ce-f205-5677-a6d6-23fbd0c59508', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('e85cf2b6-e77c-508e-b8fa-ed63a67484de', '2835c2ce-f205-5677-a6d6-23fbd0c59508', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('e4c4ad04-3751-58f4-8d3c-16c26a5a664d', '2835c2ce-f205-5677-a6d6-23fbd0c59508', '2beb3085-faec-5c50-89d4-4bbf61b59ea3', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('cbd3ccc1-cc0a-5af0-aa52-f4dfb3e2bcef', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 73, 'Which one of the following statements best reflects the most logical, rational and pragmatic message conveyed by the passage?', '0c1de7ae0fb244378653762882f5ac1db63d965e766a457976056c0112080652',
        'mcq', null, 'pending', 73, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('802daeaa-10dc-5227-a101-f0a62a1734ee', 'cbd3ccc1-cc0a-5af0-aa52-f4dfb3e2bcef', 'A', 'Green economy is not possible without reusing critical minerals.', '9088382756ba9e8579361775963c4ef72a0ad3b1b0cad262d3dada87e8cc2a6a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('66f27608-03b5-5e51-a6ee-8790367bc020', 'cbd3ccc1-cc0a-5af0-aa52-f4dfb3e2bcef', 'B', 'Every sector of economy should adapt the reuse of material resources immediately.', 'fec2f87d8faef878273477cdc4cde3f3a7abdfdf6eb65f2b996edb52dc796bd3', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f33ec312-a422-5b56-a257-781cafc95483', 'cbd3ccc1-cc0a-5af0-aa52-f4dfb3e2bcef', 'C', 'Circular economy can be beneficial for sustainable growth.', 'aff2353c49409dabcada818ed71f314424e066349ca36287da2b98a2b5530b68', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('5e585c47-68f8-5ce5-972e-2463dafb0c60', 'cbd3ccc1-cc0a-5af0-aa52-f4dfb3e2bcef', 'D', 'Circular use of material resources is the only option for some industries for their survival.', '22c42259a384966a414078128f45ba5c337cb41408204ded7dc2be2acbb6a6e0', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('5cb97620-312d-5236-94b3-93c96f145b17', 'cbd3ccc1-cc0a-5af0-aa52-f4dfb3e2bcef', '2de8943a-ba59-52f2-a531-2a75d9d73d1f', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('d883cc60-34ff-5184-b3b3-842c5361d255', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 74, 'With reference to the above passage, the following assumptions have been made: I. Automobile factories are examples of the circular economy. II. Economic growth is compatible with circular use of mineral resources. Which of the above assumptions is/are valid?', '00dd3d2559558ea82caf10dbe84a99fd116866d41c2ce7fed1ccde441dafc682',
        'mcq', null, 'pending', 74, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('5af5fbba-9bbe-5713-94c9-4f0ed09f3c3d', 'd883cc60-34ff-5184-b3b3-842c5361d255', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('94ffff89-1175-5f41-81c1-d3062f39ebe8', 'd883cc60-34ff-5184-b3b3-842c5361d255', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('46b307b6-aa1f-57aa-90b6-09a859159a6a', 'd883cc60-34ff-5184-b3b3-842c5361d255', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('18262abc-0ccd-5c62-afaf-a1d7e5deff6d', 'd883cc60-34ff-5184-b3b3-842c5361d255', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;
insert into public.pyq_question_stimuli (id, question_id, stimulus_id, display_order, reviewer_status)
values ('32db361a-f59b-51a7-859a-8e646654b7af', 'd883cc60-34ff-5184-b3b3-842c5361d255', '2de8943a-ba59-52f2-a531-2a75d9d73d1f', 1, 'pending')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('d5f0d350-7a9e-5ef8-b25e-4a68f882454c', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 75, 'A set (X) of 20 pipes can fill 70% of a tank in 14 minutes. Another set (Y) of 10 pipes fills 3/8th of the tank in 6 minutes. A third set (Z) of 16 pipes can empty half of the tank in 20 minutes. If half of the pipes of set X are closed and only half of the pipes of set Y are open, and all pipes of the set (Z) are open, then how long will it take to fill 50% of the tank?', 'a7c03b1639ed1d6eaecaaaf495cc4603413c31fc261f7e422f3088a367c4e2ba',
        'mcq', null, 'pending', 75, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('7c8c804e-9634-51f3-9524-10bc059fc3a4', 'd5f0d350-7a9e-5ef8-b25e-4a68f882454c', 'A', '8 minutes', '8ff4d5070e53b23b13cdb6d132381296cf25c9bc7ac4bc15ec530ce34f7b466c', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('b1a05364-fc47-5124-8e3d-bcab7896cd33', 'd5f0d350-7a9e-5ef8-b25e-4a68f882454c', 'B', '10 minutes', 'b075b6e113fcf02aecc4e137449091a91a03426c303dbac028511136abe83797', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('6831cd62-091b-58e9-8822-92e1fefcae3c', 'd5f0d350-7a9e-5ef8-b25e-4a68f882454c', 'C', '12 minutes', '3d885b861f2d2959b8c2a12d8b022cf415b6b897de79b32b4b0e01fa250fff85', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('1118027c-8b36-5b11-8d54-a8a37d0b58b3', 'd5f0d350-7a9e-5ef8-b25e-4a68f882454c', 'D', '16 minutes', 'b25cd8c5612e45aa5174c51e551d5c86db77982dbf8d2240589cfff95a9bbc2e', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('2148de4d-18db-5727-af44-9f0bad86e759', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 76, 'If n is a natural number, then what is the number of distinct remainders of (1^n + 2^n) when divided by 4?', '10136dd6ce1cef094bf295dbfe654fcb6e2091bd97ddc980b7935cb37814c98f',
        'mcq', null, 'pending', 76, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('642ebfbb-4716-5440-beba-4ae68f87ce55', '2148de4d-18db-5727-af44-9f0bad86e759', 'A', '0', '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('3c6e5047-3a7d-5a60-b29a-d2f5ed952ec2', '2148de4d-18db-5727-af44-9f0bad86e759', 'B', '1', '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('364de508-77a7-52ec-b800-430ce3e394dd', '2148de4d-18db-5727-af44-9f0bad86e759', 'C', '2', 'd4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('71bd8fc3-12af-52f8-9dea-26deaace662e', '2148de4d-18db-5727-af44-9f0bad86e759', 'D', '3', '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('44b3afee-f382-5568-a948-b56b1afafb0f', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 77, 'Let P = QQQ be a 3-digit number. What is the HCF of P and 481?', '6ee463d341227d19839c0160b3e93f0a265debe2ef607ab76d8e533a36024b1d',
        'mcq', null, 'pending', 77, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f88646f0-3020-5755-b13b-9b8c5b62b5af', '44b3afee-f382-5568-a948-b56b1afafb0f', 'A', '1', '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('1cd87534-501c-51b6-813f-096eda8045b2', '44b3afee-f382-5568-a948-b56b1afafb0f', 'B', '13', '3fdba35f04dc8c462986c992bcf875546257113072a909c162f7e470e581e278', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('441e9f7a-d3de-5a5d-8149-d61094f797f0', '44b3afee-f382-5568-a948-b56b1afafb0f', 'C', '37', '7a61b53701befdae0eeeffaecc73f14e20b537bb0f8b91ad7c2936dc63562b25', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('da05dd1a-a6fe-5f18-a12f-ed218f7e9054', '44b3afee-f382-5568-a948-b56b1afafb0f', 'D', '481', '51d089cdaf0c968c94b80671489d22b6f79b1c57de80df880b008e9b37b49788', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('b5b86096-4927-54a7-a1b4-aaba46708985', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 78, 'What is the 489th digit in the number 123456789101112...?', '852a3257100b04686fe339dd99e46ac7b8edbcba6b391d839f5bb28a991156d3',
        'mcq', null, 'pending', 78, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f55bd8cf-5714-5bb9-88a0-d3a2cabaf6bf', 'b5b86096-4927-54a7-a1b4-aaba46708985', 'A', '0', '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('497874a1-85df-5941-ae4c-089d6d45dc22', 'b5b86096-4927-54a7-a1b4-aaba46708985', 'B', '3', '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('018aa060-2689-5385-80e9-90ccbef50465', 'b5b86096-4927-54a7-a1b4-aaba46708985', 'C', '6', 'e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('9dd58c85-b645-50f9-bfa1-84461528fa13', 'b5b86096-4927-54a7-a1b4-aaba46708985', 'D', '9', '19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('3f94d873-1512-5e63-a7fb-e62585fa9b60', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 79, 'A mobile phone has been stolen. There are 3 suspects P, Q and R. They were questioned knowing that only one of them is guilty. Their responses are as follows: P: I did not steal. Q stole it. Q: R did not steal. I did not steal. R: I did not steal. I do not know who did it. Who stole the mobile phone?', 'd3f3ef4b76aa1810dfb7fa5b597e20b37a10244516a403600f2849f3f5950485',
        'mcq', null, 'pending', 79, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('5039c176-ee92-5498-bc5c-966c83a759b5', '3f94d873-1512-5e63-a7fb-e62585fa9b60', 'A', 'P', '148de9c5a7a44d19e56cd9ae1a554bf67847afb0c58f6e12fa29ac7ddfca9940', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('4ec47de5-70a6-53d0-803c-caf3a785a1ef', '3f94d873-1512-5e63-a7fb-e62585fa9b60', 'B', 'R', '454349e422f05297191ead13e21d3db520e5abef52055e4964b82fb213f593a1', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('5e3b8cb7-f66c-5876-8a14-e127d1693d92', '3f94d873-1512-5e63-a7fb-e62585fa9b60', 'C', 'Q', '8e35c2cd3bf6641bdb0e2050b76932cbb2e6034a0ddacc1d9bea82a6ba57f7cf', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('e72f49cc-1f79-55dd-acbe-e04e864f372a', '3f94d873-1512-5e63-a7fb-e62585fa9b60', 'D', 'Cannot be concluded', 'beb8d5e5796904ef6cb63beb46c2d71b74af7151a0b697993aecb8b05b2124b2', false, 4, '(d)')
on conflict (id) do nothing;

insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, normalized_question_hash,
   question_type, correct_option_id, reviewer_status, display_order, metadata)
values ('4b10a361-2644-5719-abc8-1254acf93473', '505b29a0-0d4d-5230-88aa-3bbc525a6db5', 80, 'Three teams P, Q, R participated in a tournament in which the teams play with one another exactly once. A win fetches a team 2 points and a draw 1 point. A team gets no point for a loss. Each team scored exactly one goal in the tournament. The team P got 3 points, Q got 2 points and R got 1 point. Which of the following statements is/are correct? I. The result of the match between P and Q is a draw with the score 0-0. II. The number of goals scored by R against Q is 1. Which of the statements given above is/are correct?', 'd89470f698e2fb7f721649dcee10df3ae751a222d8c8a8db349de3fa4a8cb125',
        'mcq', null, 'pending', 80, jsonb_build_object('paper','upsc-cse-2025-prelims-csat','answer_key_present',false))
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('482df70e-88d5-502e-9657-6d74e01b86c3', '4b10a361-2644-5719-abc8-1254acf93473', 'A', 'I only', '88322998012363b8450170938f90db78d0ac381e7f827f8966f70bfa403c9f0a', false, 1, '(a)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('6819ef5b-8e74-5481-b711-ea5bfcdbdef9', '4b10a361-2644-5719-abc8-1254acf93473', 'B', 'II only', '053c8e59f6f2eb61ebedbd29aef6d9160ecf15c571be5a76f3cceeb4806cbe52', false, 2, '(b)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('f27577db-9a4d-5717-b048-024d698b57f8', '4b10a361-2644-5719-abc8-1254acf93473', 'C', 'Both I and II', 'b7e055d1f20690b085efc5ba3aba1733b4338c5b586f79b658618ae1a2cebfa5', false, 3, '(c)')
on conflict (id) do nothing;
insert into public.pyq_options
  (id, question_id, option_label, option_text, normalized_option_hash, is_correct, display_order, source_label)
values ('cec52dc7-1377-5c57-aed2-6c966ed01b7e', '4b10a361-2644-5719-abc8-1254acf93473', 'D', 'Neither I nor II', 'd06ae3a9e56cafa0ccbbfeb1f657c28e5acba23091a6306703604f45028f6b9e', false, 4, '(d)')
on conflict (id) do nothing;

-- ── Invariants ───────────────────────────────────────────────────────────
do $$
declare
  v_exam_id uuid;
  v_cycles int;
  v_bad_paper int;
  v_missing int;
begin
  select id into v_exam_id from public.exams where slug = 'upsc-cse';

  -- P1: exactly one 2025 cycle for upsc-cse (no duplicate).
  select count(*) into v_cycles
    from public.exam_cycles where exam_id = v_exam_id and year = 2025;
  if v_cycles <> 1 then
    raise exception 'expected exactly one upsc-cse 2025 exam_cycle, found %', v_cycles;
  end if;

  -- P1: the canonical paper must never be 'verified' without exact provenance
  -- (a non-root source_url or a source_document_id).
  select count(*) into v_bad_paper
    from public.pyq_papers
   where id = '505b29a0-0d4d-5230-88aa-3bbc525a6db5'
     and trust_status = 'verified'
     and source_document_id is null
     and (source_url is null
          or btrim(source_url) = ''
          or source_url in ('https://upsc.gov.in', 'https://upsc.gov.in/'));
  if v_bad_paper > 0 then
    raise exception 'canonical CSAT 2025 paper is verified without an exact source_url or source_document_id';
  end if;

  -- P2: the four items whose passage was absent from the source doc must
  -- carry the machine-readable blocker flag.
  select count(*) into v_missing
    from public.pyq_questions
   where pyq_paper_id = '505b29a0-0d4d-5230-88aa-3bbc525a6db5'
     and (metadata ->> 'missing_stimulus')::boolean is true;
  if v_missing <> 4 then
    raise exception 'expected 4 missing-stimulus questions (items 3,4,11,12), found %', v_missing;
  end if;
end $$;

notify pgrst, 'reload schema';
