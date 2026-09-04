-- CSAT 2024 rebuild: replace 71 mis-numbered rows with 75 paper-numbered questions
-- paper 9e191ae4-68b9-47bf-9121-6d9d468a7bc5
-- Missing from source, recorded as gaps: Q49, Q55, Q56, Q57, Q58
begin;

-- 1. clear existing rows (options and tags cascade via FK; verify before commit)
delete from public.pyq_question_stimuli where question_id in (select id from public.pyq_questions where pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5');
delete from public.pyq_stimuli where pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5';
delete from public.pyq_question_topic_tags where question_id in (select id from public.pyq_questions where pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5');
delete from public.pyq_options where question_id in (select id from public.pyq_questions where pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5');
delete from public.pyq_questions where pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5';

-- 2. insert questions + options
-- Q1
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 1, 1, 'Q1', $q$Which of the following statements best reflect the most logical and rational inferences that can be made from the passage? The current methods of food distribution are solely responsible for the loss and wastage of food. Land productivity is adversely affected by the prevailing trend of food loss and wastage. Reduction in the loss and wastage of food results in lesser carbon footprint. Post-harvest technologies to prevent or reduce the loss and wattage of food are not available. Select the correct answer using the code given below :$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1, 2 and 3$o$, 1, false, 'pending'),
    ('b', $o$2 and 3 only$o$, 2, true, 'pending'),
    ('c', $o$1, 3 and 4$o$, 3, false, 'pending'),
    ('d', $o$1, 2 and 4$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q2
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 2, 2, 'Q2', $q$Based on the above passage, the following assumptions have been made : 1.The food distribution mechanism needs to be reimagined and made effective to reduce the loss and wastage of food. 2.Ensuring the reduction of wastage and loss of food is a social and moral responsibility of all citizens. Which of the assumptions given above is/are valid?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, true, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, false, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q3
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 3, 3, 'Q3', $q$Which of the following statements best reflects/reflect the most logical and rational inference/inferences that can be made from the passage? Central banks cannot bring down inflation without budgetary backing. The effects of monetary policy depend on the fiscal policies pursued by the government. Select the correct answer using the code given below :$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, false, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, true, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q4
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 4, 4, 'Q4', $q$Based on the above passage, the following assumptions have been made : 1. Fiscal policies of governments are solely responsible for higher prices. 2. Higher prices do not affect the long-term government bonds. Which of the assumptions given above is/are valid?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, false, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, false, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q5
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 5, 5, 'Q5', $q$What is the least possible number of cuts required to cut a cube into 64 identical pieces?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$8$o$, 1, false, 'pending'),
    ('b', $o$9$o$, 2, true, 'pending'),
    ('c', $o$12$o$, 3, false, 'pending'),
    ('d', $o$16$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q6
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 6, 6, 'Q6', $q$In the expression 5 * 4* 3* 2* 1, * is chosen from +, -, × each at most two times. What is the smallest non-negative value of the expression?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$3$o$, 1, false, 'pending'),
    ('b', $o$2$o$, 2, false, 'pending'),
    ('c', $o$1$o$, 3, false, 'pending'),
    ('d', $o$0$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q7
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 7, 7, 'Q7', $q$A certain number of men can complete a piece of work in 6k days, where k is a natural number. By what percent should the number of men be increased so that the work can be completed in 5k days?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$10%$o$, 1, false, 'pending'),
    ('b', $o$(50/3)%$o$, 2, false, 'pending'),
    ('c', $o$20%$o$, 3, true, 'pending'),
    ('d', $o$25%$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q8
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 8, 8, 'Q8', $q$X, Y and Z can complete a piece of work individually in 6 hours, 8 hours and 8 hours respectively. However, only one person at a time can work in each hour and nobody can work for two consecutive hours. All are engaged to finish the work. What is the minimum amount of time that they will take to finish the work.$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$6 hours 15 minutes$o$, 1, false, 'pending'),
    ('b', $o$6 hours 30 minutes$o$, 2, false, 'pending'),
    ('c', $o$6 hours 45 minutes$o$, 3, true, 'pending'),
    ('d', $o$7 hours$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q9
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 9, 9, 'Q9', $q$How many consecutive zeros are there at the end of the integer obtained in the product 12 × 24 × 36 × 48 ×.... × 2550?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$50$o$, 1, false, 'pending'),
    ('b', $o$55$o$, 2, false, 'pending'),
    ('c', $o$100$o$, 3, false, 'pending'),
    ('d', $o$200$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q10
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 10, 10, 'Q10', $q$On January 1st, 2023, a person saved Rs 1. On January 2nd, 2023, he saved Rs. 2 more than that on the previous day. On January 3rd, 2023, he saved Rs. 2 more than that on the previous day and so on. At the end of which date was his total savings a perfect square as well a perfect cube?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$7th January, 2023$o$, 1, false, 'pending'),
    ('b', $o$8th January, 2023$o$, 2, true, 'pending'),
    ('c', $o$9th January, 2023$o$, 3, false, 'pending'),
    ('d', $o$Not possible$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q11
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 11, 11, 'Q11', $q$Which one of the following statements best reflects the most logical and rational inference that can be made from the above passage?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$Curriculum for urban planning courses should have diverse and interdisciplinary approach.$o$, 1, true, 'pending'),
    ('b', $o$In India, city administration is under bureaucracy which lacks formal training in urban planning and management.$o$, 2, false, 'pending'),
    ('c', $o$In India, the management of urban areas is a local affair with a chronic problem of insufficient funds.$o$, 3, false, 'pending'),
    ('d', $o$With high density of population and widespread poverty in our urban areas, planned development in them is very difficult.$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q12
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 12, 12, 'Q12', $q$Based on the above passage, the following assumptions have been made : India needs a new generation of urban professionals with knowledge relevant to modern urban practice. Indian universities at present have no capacity or potential to impart training in systems approach. Which of the assumptions given above is/are correct?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, true, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, false, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q13
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 13, 13, 'Q13', $q$Which one of the following statements best reflects the central idea of the above passage ?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$Constructed as a marketplace of views, social media ensures instant access to information.$o$, 1, false, 'pending'),
    ('b', $o$Social media are not ideal or moral institutions but the products built by companies to make profits.$o$, 2, true, 'pending'),
    ('c', $o$Social media have been created to strengthen democracies.$o$, 3, false, 'pending'),
    ('d', $o$In today's world, social media are inevitable for well-informed social life.$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q14
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 14, 14, 'Q14', $q$Based on the above passage, the following assumptions have been made : 1. Internet is not inclusive enough. 2. Internet can adversely affect the quality of policies in a country. Which of the assumptions given above is/are valid?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, false, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, true, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q15
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 15, 15, 'Q15', $q$222333 + 333222 is divisible by which of the following numbers ?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$2 and 3 but not 37$o$, 1, false, 'pending'),
    ('b', $o$3 and 37 but not 2$o$, 2, true, 'pending'),
    ('c', $o$2 and 37 but not 3$o$, 3, false, 'pending'),
    ('d', $o$2, 3 and 37$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q16
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 16, 16, 'Q16', $q$What percent of water must be mixed with honey so as to gain 20% by selling the mixture at the cost price of honey ?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$20%$o$, 1, true, 'pending'),
    ('b', $o$10%$o$, 2, false, 'pending'),
    ('c', $o$5%$o$, 3, false, 'pending'),
    ('d', $o$4%$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q17
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 17, 17, 'Q17', $q$What is the rightmost digit preceding the zeros in the value of 3030?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1$o$, 1, false, 'pending'),
    ('b', $o$3$o$, 2, false, 'pending'),
    ('c', $o$7$o$, 3, false, 'pending'),
    ('d', $o$9$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q18
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 18, 18, 'Q18', $q$421 and 427, when divided by the same number, leave the same remainder 1. How many numbers can be used as the divisor in order to get the same remainder 1 ?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1$o$, 1, false, 'pending'),
    ('b', $o$2$o$, 2, false, 'pending'),
    ('c', $o$3$o$, 3, true, 'pending'),
    ('d', $o$4$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q19
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 19, 19, 'Q19', $q$A can X contains 399 litres of petrol and a can Y contains 532 litres of diesel. They are to be bottled in bottles of equal size so that whole of petrol and diesel would be separately bottled. The bottle capacity in terms of litres is an integer. How many different bottle sizes are possible?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$3$o$, 1, false, 'pending'),
    ('b', $o$4$o$, 2, true, 'pending'),
    ('c', $o$5$o$, 3, false, 'pending'),
    ('d', $o$6$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q20
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 20, 20, 'Q20', $q$Consider the following statements in respect of the sum S = x + y + z, where x, y and z are distinct prime numbers each less than 10 : 1. The unit digit of S can be 0. 2. The unit digit of S can be 9. 3. The unit digit of S can be 5. Which of the statements given above are correct?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 and 2 only$o$, 1, false, 'pending'),
    ('b', $o$2 and 3 only$o$, 2, false, 'pending'),
    ('c', $o$1 and 3 only$o$, 3, true, 'pending'),
    ('d', $o$1, 2 and 3$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q21
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 21, 21, 'Q21', $q$Based on the above passage, the following assumptions have been made : For effective school education, parents have greater role than the governments. School curriculum that conforms to today’s requirements and is uniform for the entire country may address the issues brought out. Which of the assumptions given above is/are valid?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, false, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, false, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q22
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 22, 22, 'Q22', $q$Which one of the following statements best reflects the central idea conveyed by the passage?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$Total eradication of poverty in the country will resolve the issue of under-performance of our school-children.$o$, 1, false, 'pending'),
    ('b', $o$Monetary incentives to parents and teachers is a strategy to improve the children’s academic performance.$o$, 2, false, 'pending'),
    ('c', $o$Public policy should ensure that competencies and achievements of young people are aligned with their expectations.$o$, 3, true, 'pending'),
    ('d', $o$India is not going to take advantage of the demographic dividend unless some school passouts go back to agriculture.$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q23
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 23, 23, 'Q23', $q$Which one of the following statements best reflects the thinking of the author about the science?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$Science must value the commitment of the scientists.$o$, 1, false, 'pending'),
    ('b', $o$Science is a product of civilized society and must be used for the promotion of scientific awareness in people.$o$, 2, false, 'pending'),
    ('c', $o$Industrial revolution was made possible by the advancements in science.$o$, 3, false, 'pending'),
    ('d', $o$Science must pursue truth but be responsible for social welfare.$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q24
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 24, 24, 'Q24', $q$Consider the sequence A_BCD_BBCDABC_DABC_D that follows a certain pattern. Which one of the following completes the sequence?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$B, A, D, C$o$, 1, false, 'pending'),
    ('b', $o$B, A, C, D$o$, 2, false, 'pending'),
    ('c', $o$A, A, C, D$o$, 3, true, 'pending'),
    ('d', $o$A, A, D, C$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q25
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 25, 25, 'Q25', $q$Two persons P and Q enter into a business. P puts ₹ 14,000 more than Q, but P has invested for 8 months and Q has invested for 10 months. If P's share is ₹ 400 more than Q's share out of the total profit of ₹ 2,000, what is the capital contributed by P?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$₹ 30,000$o$, 1, true, 'pending'),
    ('b', $o$₹ 26,000$o$, 2, false, 'pending'),
    ('c', $o$₹ 24,000$o$, 3, false, 'pending'),
    ('d', $o$₹ 20,000$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q26
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 26, 26, 'Q26', $q$P’s salary is 20% lower than Q’s salary which is 20% lower than R’s salary. By how much percent is R’s salary more than P’s salary?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$48.75%$o$, 1, false, 'pending'),
    ('b', $o$56.25%$o$, 2, true, 'pending'),
    ('c', $o$60.50%$o$, 3, false, 'pending'),
    ('d', $o$62.25%$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q27
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 27, 27, 'Q27', $q$A number is mistakenly divided by 4 instead of multiplying by 4. What is the percentage change in the result due to this mistake?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$25%$o$, 1, false, 'pending'),
    ('b', $o$50%$o$, 2, false, 'pending'),
    ('c', $o$72.75%$o$, 3, false, 'pending'),
    ('d', $o$93.75%$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q28
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 28, 28, 'Q28', $q$In an examination, 80% of students passed in English, 70% of students passed in Hindi and 15% failed in both the subjects. What is the percentage of students who failed in only one subject?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$15%$o$, 1, false, 'pending'),
    ('b', $o$20%$o$, 2, true, 'pending'),
    ('c', $o$25%$o$, 3, false, 'pending'),
    ('d', $o$35%$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q29
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 29, 29, 'Q29', $q$A father said to his son, “n years back I was as old as you are now. My present age is four times your age n years back”. If the sum of the present ages of the father and the son is 130 years, what is the difference of their ages?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$30 years$o$, 1, true, 'pending'),
    ('b', $o$32 years$o$, 2, false, 'pending'),
    ('c', $o$34 years$o$, 3, false, 'pending'),
    ('d', $o$36 years$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q30
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 30, 30, 'Q30', $q$Consider the following : 1. 1000 litres = 1m3 2. 1 metric ton = 1000 kg 3. 1 hectare = 10000 m2 Which of the above are correct?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 and 2 only$o$, 1, false, 'pending'),
    ('b', $o$2 and 3 only$o$, 2, false, 'pending'),
    ('c', $o$1 and 3 only$o$, 3, false, 'pending'),
    ('d', $o$1, 2 and 3$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q31
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 31, 31, 'Q31', $q$Which of the following is/are emphatically conveyed by the author of the passage? 1. Without science, mankind could not have continued to exist till today. 2. It is the science that will ultimately determine the destiny of mankind. Select the correct answer using the code given below.$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, false, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, false, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q32
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 32, 32, 'Q32', $q$Based on the above passage, the following assumptions have been made: 1. The horrors of modern life are the inevitable result of the progress of science. 2. The aspect of truth likely to be overlooked is that science is what man has made it. Which of the assumptions given above is/are correct?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, false, 'pending'),
    ('b', $o$2 only$o$, 2, true, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, false, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q33
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 33, 33, 'Q33', $q$When we meet other people while we travel, we learn to differentiate between$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$imagination and understanding$o$, 1, false, 'pending'),
    ('b', $o$communities and nationalities$o$, 2, false, 'pending'),
    ('c', $o$local values and universal values$o$, 3, true, 'pending'),
    ('d', $o$friends and foes$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q34
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 34, 34, 'Q34', $q$With reference to the above passage, the following assumptions have been made : 1. Travel leads to an understanding of humans. 2. Travel helps those who wish to learn fundamental common values. 3. A person with long experience in travel can resolve differences amongst people. Which of the assumptions given above are valid?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 and 2 only$o$, 1, true, 'pending'),
    ('b', $o$2 and 3 only$o$, 2, false, 'pending'),
    ('c', $o$1 and 3 only$o$, 3, false, 'pending'),
    ('d', $o$1, 2 and 3$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q35
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 35, 35, 'Q35', $q$Let X be a two-digit number and Y be another two-digit number formed by interchanging the digits of X. If (X + Y) is the greatest two-digit number, then what is the number of possible values of X?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$2$o$, 1, false, 'pending'),
    ('b', $o$4$o$, 2, false, 'pending'),
    ('c', $o$6$o$, 3, false, 'pending'),
    ('d', $o$8$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q36
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 36, 36, 'Q36', $q$Consider the following : Weight of 6 boys = Weight of 7 girls = Weight of 3 men = Weight of 4 women If the average weight of the women is 63 kg, then what is the average weight of the boys?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$40 kg$o$, 1, false, 'pending'),
    ('b', $o$42 kg$o$, 2, true, 'pending'),
    ('c', $o$45 kg$o$, 3, false, 'pending'),
    ('d', $o$63 kg$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q37
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 37, 37, 'Q37', $q$How many times the hour hand and the minute hand coincide in a clock between 10:00 a.m. and 2.00 p.m. (same day)?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$3 times$o$, 1, true, 'pending'),
    ('b', $o$4 times$o$, 2, false, 'pending'),
    ('c', $o$5 times$o$, 3, false, 'pending'),
    ('d', $o$6 times$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q38
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 38, 38, 'Q38', $q$The calendar for the year 2025 is same for$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$2029$o$, 1, false, 'pending'),
    ('b', $o$2030$o$, 2, false, 'pending'),
    ('c', $o$2031$o$, 3, true, 'pending'),
    ('d', $o$2033$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q39
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 39, 39, 'Q39', $q$Let p, q, r and s be distinct positive integers. Let p, q be odd and r, s be even. Consider the following statements : (p-r)2 (qs) is even. (q-s)q2 s is even. (q + r)2 (p + s) is odd. Which of the statements given above are correct?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 and 2 only$o$, 1, false, 'pending'),
    ('b', $o$2 and 3 only$o$, 2, false, 'pending'),
    ('c', $o$1 and 3 only$o$, 3, false, 'pending'),
    ('d', $o$1, 2 and 3$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q40
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 40, 40, 'Q40', $q$What is the angle between the minute hand and hour hand when the clock shows 4:25 hours?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$12.5°$o$, 1, false, 'pending'),
    ('b', $o$15°$o$, 2, false, 'pending'),
    ('c', $o$17.5°$o$, 3, true, 'pending'),
    ('d', $o$20°$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q41
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 41, 41, 'Q41', $q$Which of the following statements best reflects/reflect the most logical and rational inference/inferences that can be made from the passage? In conventional classroom learning, the central goal is duration of learning rather than attainment of competency. Conventional classrooms encourage one-size-fits-all approach and stamp out all differentiation. Select the correct answer using the code given below.$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, false, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, true, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q42
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 42, 42, 'Q42', $q$Based on the above passage, the following assumptions have been made : As a large number of workers in our country are employed in unorganized sector, India does not need to change its present conventional classroom system of education. Even with its present conventional classroom system of education, India produces sufficient number of skilled workers to fully realize the benefits of demographic dividend. Which of the assumptions given above is/are valid?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, false, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, false, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q43
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 43, 43, 'Q43', $q$Based on the above passage, the following assumptions have been made : The adolescent does not feel comfortable with his parents because they tend to be dominating and assertive. The adolescent of modern times does not have much respect for parents. Which of the assumptions given above is/are valid?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, true, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, false, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q44
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 44, 44, 'Q44', $q$Which one of the following statements best reflects the central idea of the above passage?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$Parents in general may not be of much help when children are on their way to becoming adults.$o$, 1, true, 'pending'),
    ('b', $o$When children reach adolescence, involvement of parents in their lives is unnecessary.$o$, 2, false, 'pending'),
    ('c', $o$Modern-day nuclear families are not capable of bringing up children properly.$o$, 3, false, 'pending'),
    ('d', $o$In modern societies, adolescents tend to be stubborn, disobedient and careless.$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q45
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 45, 45, 'Q45', $q$What is the number of fives used in numbering a 260-page book?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$55$o$, 1, false, 'pending'),
    ('b', $o$56$o$, 2, true, 'pending'),
    ('c', $o$57$o$, 3, false, 'pending'),
    ('d', $o$60$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q46
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 46, 46, 'Q46', $q$What is the sum of the first 28 terms in the following sequence? 1, 1, 2, 1, 3, 2, 1, 4, 3, 2, 1, 5, 4, 3, 2,......$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$83$o$, 1, false, 'pending'),
    ('b', $o$84$o$, 2, true, 'pending'),
    ('c', $o$85$o$, 3, false, 'pending'),
    ('d', $o$86$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q47
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 47, 47, 'Q47', $q$A person buys three articles P, Q and R for ₹ 3,330. If P costs 25% more than R and R costs 20% more than Q, then what is the cost of P?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$₹ 1,000$o$, 1, false, 'pending'),
    ('b', $o$₹ 1,200$o$, 2, false, 'pending'),
    ('c', $o$₹ 1,250$o$, 3, false, 'pending'),
    ('d', $o$₹ 1,350$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q48
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 48, 48, 'Q48', $q$If the sum of the two-digit numbers AB and CD is the three-digit number 1CE, where the letters A, B, C, D, E denote distinct digits, then what is the value of A?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$9$o$, 1, true, 'pending'),
    ('b', $o$8$o$, 2, false, 'pending'),
    ('c', $o$7$o$, 3, false, 'pending'),
    ('d', $o$Cannot be determined due to insufficient data$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q50
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 50, 50, 'Q50', $q$The total cost of 4 oranges, 6 mangoes and 8 apples is equal to twice the total cost of 1 orange, 2 mangoes and 5 apples. Consider the following statements : 1. The total cost of 3 oranges, 5 mangoes and 9 apples is equal to the total cost of 4 oranges, 6 mangoes and 8 apples. 2. The total cost of one orange and one mango is equal to the cost of one apple. Which of the statements given above is/are correct?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, false, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, true, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q51
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 51, 51, 'Q51', $q$Which one of the following statements best reflects the most logical, rational and practical suggestion implied by the passage?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$It is a cheap and practical method to produce limestone at commercial level for building purposes.$o$, 1, false, 'pending'),
    ('b', $o$This can be used as one of the methods of carbon sequestration.$o$, 2, true, 'pending'),
    ('c', $o$Basalt rock can be made a good source of calcium and magnesium minerals by this method.$o$, 3, false, 'pending'),
    ('d', $o$Good rock-dissolving acid can be produced by mixing carbon dioxide and water.$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q52
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 52, 52, 'Q52', $q$Based on the above passage, the following assumptions have been made : 1. Giant icebergs have a bearing on primary productivity and food chains of the Southern Ocean. 2. Melting of giant icebergs can produce climate change effects and impact world fisheries. Which of the assumptions given above is/ are valid?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, true, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, false, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q53
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 53, 53, 'Q53', $q$Which one of the following statements best reflect the most logical and rational and practical message conveyed by the passage?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$Farmers can use caterpillars to feed on weeds in their crop fields/plantations.$o$, 1, false, 'pending'),
    ('b', $o$This finding can help in the development of clinically useful antimicrobial compounds.$o$, 2, false, 'pending'),
    ('c', $o$This finding can help in the development of organic, ecologically sustainable pesticides.$o$, 3, true, 'pending'),
    ('d', $o$Caterpillars can be genetically modified to be predators of the other plant pests.$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q54
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 54, 54, 'Q54', $q$325 + 227 is divisible by$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$3$o$, 1, false, 'pending'),
    ('b', $o$7$o$, 2, false, 'pending'),
    ('c', $o$10$o$, 3, true, 'pending'),
    ('d', $o$11$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q59
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 59, 59, 'Q59', $q$A Question is given followed by two Statements I and II. Consider the Questions and the Statements. Question : What are the values of m and n, where m and n are natural numbers? Statement-I : m + n > mn and m > n. Statement-II : The product of m and n is 24. Which one of the following is correct in respect of the above Question and the Statements?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$The Question can be answered by using one of the Statements alone, but cannot be answered using the other Statement alone$o$, 1, false, 'pending'),
    ('b', $o$The Question can be answered by using either Statement alone$o$, 2, false, 'pending'),
    ('c', $o$The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone$o$, 3, true, 'pending'),
    ('d', $o$The Question cannot be answered even by using both the Statements together$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q60
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 60, 60, 'Q60', $q$A Question is given followed by two Statements I and II. Consider the Questions and the Statements. Question : What is the time required to download the software? Statement-I : The size of the software is 12 megabytes. Statement-II : The transfer rate is 2.4 kilobytes per second. Which one of the following is correct in respect of the above Question and the Statements?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$The Question can be answered by using one of the Statements alone, but cannot be answered using the other Statement alone$o$, 1, false, 'pending'),
    ('b', $o$The Question can be answered by using either Statement alone$o$, 2, false, 'pending'),
    ('c', $o$The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone$o$, 3, true, 'pending'),
    ('d', $o$The Question cannot be answered even by using both the Statements together$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q61
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 61, 61, 'Q61', $q$Which one of the following statements best reflects the crux of the above passage?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$Responsible media should not distort the real in an ideal democracy.$o$, 1, true, 'pending'),
    ('b', $o$Fake news seems inherent in the life of an ideal democracy.$o$, 2, false, 'pending'),
    ('c', $o$There should not be any kind of restrictions on the freedom of expression in an ideal democracy.$o$, 3, false, 'pending'),
    ('d', $o$Irresponsible media and political leaders cannot be effectively controlled in an ideal democracy.$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q62
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 62, 62, 'Q62', $q$Which one of the following statements best reflects the most logical, rational and practical message implied by the passage?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$Knowledge of consumer behaviour leads to more capital expenditure in manufacturing sector.$o$, 1, false, 'pending'),
    ('b', $o$Knowledge of consumer behaviour stimulates the growth of commerce and trade and thus helps in the overall economic development of the country.$o$, 2, false, 'pending'),
    ('c', $o$Interconnected devices give a lot of comfort to home users and improve the overall quality of life.$o$, 3, false, 'pending'),
    ('d', $o$Interconnected devices can be at security risk and home users may have privacy risk.$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q63
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 63, 63, 'Q63', $q$Which one of the following statements best reflects the crux of the above passage?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$Environmental sustainability is inimical to our objective of achieving a high rate of GDP growth.$o$, 1, false, 'pending'),
    ('b', $o$Poverty eradication is not possible without a rapid economic growth and the consequent environmental degradation.$o$, 2, false, 'pending'),
    ('c', $o$Maintaining high environmental standards is now a prerequisite for achieving a steady, sufficient and inclusive growth.$o$, 3, true, 'pending'),
    ('d', $o$With large populations, rampant poverty and limited resources of today's world, environmental degradation cannot be prevented and inequalities are inevitable.$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q64
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 64, 64, 'Q64', $q$A question is given followed by two Statements I and II. Consider the Question and the Statements. Question : What are the unique values of x and y, where x, y are distinct natural numbers? Statement-I : x/y is odd. Statement-II : xy = 12 Which one of the following is correct in respect of the above Question and the Statements?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$The question can be answered by using one of the Statements alone, but cannot be answered using the other Statement alone$o$, 1, false, 'pending'),
    ('b', $o$The Question can be answered by using either Statement alone$o$, 2, false, 'pending'),
    ('c', $o$The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone$o$, 3, true, 'pending'),
    ('d', $o$The Question cannot be answered even by using both the Statements together$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q65
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 65, 65, 'Q65', $q$A Question is given followed by two Statements I and II. Consider the Question and the Statements. A certain amount was distributed among X, Y and Z. Question : Who received the least amount? Statement-I : X received 4/5 of what Y and Z together received. Statement-II: Y received 2/7 of what X and Z together received. Which one of the following is correct in respect of the above Question and the Statements?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$The Question can be answered by using one of the Statements alone, but cannot be answered using the other Statement alone$o$, 1, false, 'pending'),
    ('b', $o$The Question can be answered by using either Statement alone$o$, 2, false, 'pending'),
    ('c', $o$The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone$o$, 3, true, 'pending'),
    ('d', $o$The Question cannot be answered even by using both the Statements together$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q66
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 66, 66, 'Q66', $q$A Question is given followed by two Statements I and II. Consider the Question and the Statements. Question : If the average marks in a class are 60, them what is the number of students in the class? Statement-I : The highest marks in the class are 70 and the lowest marks are 50. Statement-II : Exclusion of highest and lowest marks from the class does not change the average. Which one of the following is correct in respect of the above Question and the Statements?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$The Question can be answered by using one of the Statements alone, but cannot be answered using the other Statement alone$o$, 1, false, 'pending'),
    ('b', $o$The Question can be answered by using either Statement alone$o$, 2, false, 'pending'),
    ('c', $o$The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone$o$, 3, false, 'pending'),
    ('d', $o$The Question cannot be answered even by using both the Statements together$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q67
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 67, 67, 'Q67', $q$A Question is given followed by two Statements I and II. Consider the Question and the Statements. There are three distinct prime numbers whose sum is a prime number. Question : What are those three numbers? Statement-I : Their sum is less than 23. Statement-II : One of the numbers is 5. Which one of the following is correct in respect of the above Question and the Statements?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$The Question can be answered by using one of the Statements alone, but cannot be answered using the other Statement alone$o$, 1, true, 'pending'),
    ('b', $o$The Question can be answered by using either Statement alone$o$, 2, false, 'pending'),
    ('c', $o$The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone$o$, 3, false, 'pending'),
    ('d', $o$The Question cannot be answered even by using both the Statements together$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q68
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 68, 68, 'Q68', $q$A Question if given followed by two Statements I and II. Consider the Question and the Statements. Question : Is (x+y) an integer? Statement-I : (2x+y) is an integer. Statement-II : (x+2y) is an integer. Which one of the following is correct in respect of the above Question and the Statements?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$The Question can be answered by using one of the Statements alone, but cannot be answered using the other Statement alone$o$, 1, false, 'pending'),
    ('b', $o$The Question can be answered by using either Statement alone$o$, 2, false, 'pending'),
    ('c', $o$The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone$o$, 3, false, 'pending'),
    ('d', $o$The Question cannot be answered even by using both the Statements together$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q69
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 69, 69, 'Q69', $q$A Question is given followed by two Statement I and II. Consider the Question and the Statements. A person buys three articles p, q and r for ₹50. The price of the article q is ₹16 which is the least. Question : What is the price of the article p? Statement-I : The cost of p is not more than that of r. Statement-II : The cost of r is not more than that of p. Which one of the following is correct in respect of the above Question and the Statements?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$The Question can be answered by using one of the Statements alone, but cannot be answered using the other Statement alone$o$, 1, false, 'pending'),
    ('b', $o$The Question can be answered by using either Statement alone$o$, 2, false, 'pending'),
    ('c', $o$The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone$o$, 3, true, 'pending'),
    ('d', $o$The Question cannot be answered even by using both the Statements together$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q70
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 70, 70, 'Q70', $q$A Question is given followed by two Statements I and II. Consider the Question and the Statements. P, Q, R and S appeared in a test. Question : Has P scored more marks than Q ? Statement-I : The sum of the marks scored by P and Q is equal to the sum of the marks scored by R and S. Statement-II : The sum of the marks scored by P and S is more than the sum of the marks scored by Q and R. Which one of the following is correct in respect of the above Question and the Statements?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$The Question can be answered by using one of the Statements alone, but cannot be answered using the other Statement alone$o$, 1, false, 'pending'),
    ('b', $o$The Question can be answered by using either Statement alone$o$, 2, false, 'pending'),
    ('c', $o$The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone$o$, 3, false, 'pending'),
    ('d', $o$The Question cannot be answered even by using both the Statements together$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q71
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 71, 71, 'Q71', $q$Which one of the following statements best reflects the most logical and rational message conveyed by the above passage?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$It is the poetry, not science or religion, which recognizes and accepts imperfections in humans.$o$, 1, true, 'pending'),
    ('b', $o$Truth is revealed through science or religion and poetry is anathema to truth.$o$, 2, false, 'pending'),
    ('c', $o$Poetry is romantic, imaginary and is about feeling whereas science and religion are about truth.$o$, 3, false, 'pending'),
    ('d', $o$In a world of violence, tyranny and bigotry, poetry is a form of dynamic resistance.$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q72
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 72, 72, 'Q72', $q$Based on the above passage, the following assumptions have been made : 1. The author of the passage believes that flowers are creations of Nature's luxury. 2. The author of the passage does not believe in the usefulness of flowers except as things of beauty. Which of the assumptions given above is/are valid?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, false, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, false, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q73
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 73, 73, 'Q73', $q$Question is given followed by two Statements I and II. Consider the Question and the Statements. Age of each of P and Q is less than 100 years but more than 10 years. If you interchange the digits of the age of P, the number represents the age of Q. Question : What is the difference of their ages? Statement-I : The age of P is greater than the age of Q. Statement-II : The sum of their ages is 11/6 times their difference. Which one of the following is correct in respect of the above Question and the Statements?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$The Question can be answered by using one of the Statements alone, but cannot be answered using the other Statement alone$o$, 1, true, 'pending'),
    ('b', $o$The Question can be answered by using either Statement alone$o$, 2, false, 'pending'),
    ('c', $o$The Question can be answered by using both the Statements together, but cannot be answered using either Statement alone$o$, 3, false, 'pending'),
    ('d', $o$The Question cannot be answered even by using both the Statements together$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q74
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 74, 74, 'Q74', $q$Main Statement is followed by four Statements labelled P, Q, R and S. Choose the ordered pair of the Statements where the first Statement implies the second, and the two Statements are logically consistent with the Main Statement. Main Statement : Pradeep becomes either a Director or a Producer. Statement P : Pradeep is a Director. Statement Q : Pradeep is a Producer. Statement R : Pradeep is not a Director. Statement S : Pradeep is not a Producer. Select the correct answer.$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$SP only$o$, 1, false, 'pending'),
    ('b', $o$RQ only$o$, 2, false, 'pending'),
    ('c', $o$Both SP and RQ$o$, 3, true, 'pending'),
    ('d', $o$Neither SP nor RQ$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q75
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 75, 75, 'Q75', $q$a + b means a – b; a – b means a x b; a x b means a ÷ b; a ÷ b; means a + b, then what is the value of 10 + 30 – 100 x 50 ÷ 25? (Operations are to be replaced simultaneously)$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$15$o$, 1, false, 'pending'),
    ('b', $o$0$o$, 2, false, 'pending'),
    ('c', $o$–15$o$, 3, false, 'pending'),
    ('d', $o$–25$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q76
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 76, 76, 'Q76', $q$If P means ‘greater than (>)’; Q means ‘less than (<)’; R means ‘not greater than ( )’; S means ‘not less than ( )’ and T means ‘equal to (=)’, then consider the following statements : 1. If 2x(S)3y and 3x(T)4z, then 9y(P)8z. 2. If x(Q)2y and y(R)z, then x(R)z. Which of the statements given above is/are correct?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1 only$o$, 1, false, 'pending'),
    ('b', $o$2 only$o$, 2, false, 'pending'),
    ('c', $o$Both 1 and 2$o$, 3, false, 'pending'),
    ('d', $o$Neither 1 nor 2$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q77
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 77, 77, 'Q77', $q$If in a certain code, ‘ABCD’ is written as 24 and ‘EFGH’ is written as 1680, then how is ‘IJKL’ written in that code?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$11880$o$, 1, true, 'pending'),
    ('b', $o$11240$o$, 2, false, 'pending'),
    ('c', $o$7920$o$, 3, false, 'pending'),
    ('d', $o$5940$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q78
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 78, 78, 'Q78', $q$If in a certain code, 'POT' is written as ATOP and 'TRAP' is written as APART, then how is 'ARENA' written in that code?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$AARENA$o$, 1, false, 'pending'),
    ('b', $o$AANREA$o$, 2, false, 'pending'),
    ('c', $o$AANEAR$o$, 3, false, 'pending'),
    ('d', $o$AANERA$o$, 4, true, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q79
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 79, 79, 'Q79', $q$What will come in place of * in the sequence 3, 14, 39, 84, *, 258?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$150$o$, 1, false, 'pending'),
    ('b', $o$155$o$, 2, true, 'pending'),
    ('c', $o$160$o$, 3, false, 'pending'),
    ('d', $o$176$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- Q80
with q as (
  insert into public.pyq_questions
    (pyq_paper_id, question_number, display_order, source_question_ref, question_text, question_type, reviewer_status, source_kind)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 80, 80, 'Q80', $q$In some code, letters P, Q, R, S, T represent numbers 4, 5, 10, 12, 15. It is not known which letter represents which number. If Q – S = 2S and T = R + S + 3, then what is the value of P + R – T?$q$, 'mcq', 'pending', 'manual')
  returning id
)
insert into public.pyq_options (question_id, option_label, option_text, display_order, is_correct, reviewer_status)
select v.* from q, (values
    ('a', $o$1$o$, 1, false, 'pending'),
    ('b', $o$2$o$, 2, true, 'pending'),
    ('c', $o$3$o$, 3, false, 'pending'),
    ('d', $o$Cannot be determined due to insufficient data$o$, 4, false, 'pending')
) as v(option_label, option_text, display_order, is_correct, reviewer_status);

-- 3. passages as stimuli, linked by block structure
-- passage 1 -> Q1,2
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$According to the Food and Agriculture Organization, one-third of food produced for human consumption is lost or wasted globally. Food is lost or wasted throughout the supply chain, from initial agricultural production to final household consumption. The increasing wastage also results in land degradation by about 45%, mainly due to deforestation, unsustainable agricultural practices, and excessive groundwater extraction. The energy spent over wasted food results in about 3.5 billion tonnes of carbon dioxide production every year. Decay also leads to harmful emissions of other gases in the atmosphere. Addressing the loss and wastage of food in all forms is critical to complete the cycle of food efficiency and food sustainability.$stim$, 'en', 1, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (1,2);

-- passage 2 -> Q3,4
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$As inflation rises, even governments previously committed to budget discipline are spending freely to help households. Higher interest rates announced by central banks are supposed to help produce modest fiscal austerity, because to maintain stable debts while paying more to borrow, governments must cut spending or raise taxes. Without the fiscal backup, monetary policy eventually loses traction. Higher interest rates become inflationary, not disinflationary, because they simply lead governments to borrow more to pay rising debt-service costs. The risk of monetary unmooring is greater when public debt rises, because interest rates become more important to budget deficits.$stim$, 'en', 2, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (3,4);

-- passage 3 -> Q11,12
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$Today, if we consider cities such as New York, London and Paris as some of the most iconic cities in the world, it is because plans carrying a heavy systems approach were imposed on their precincts. The backbone of the systems theory is the process of translating social, spatial and cultural desirables into mathematical models using computing, statistics, optimization and an algorithmic way of formulating and solving problems. The early universities of the West which began to train professionals in planning, spawned some of the most ingenious planners, who were experts in these domains. This was because these very subjects were absorbed into the planning curriculum that had its roots in the social sciences, geography and architecture. Planning in India, and its education differ from the West.$stim$, 'en', 3, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (11,12);

-- passage 4 -> Q21,22
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$By the time children reach class 8, the bulk of them tend to be in the age range of 13 years to 15 years. But in our country, about a quarter of all children in class 8 struggle with reading simple texts and more than half are still unable to do basic arithmetic operations like division. Every year about 25 million young boys and girls from elementary school move into the life that lies for them beyond compulsory schooling. They cannot enter the workforce at least in the organized sector till they are 18. For many families, these children are the first from their families ever to get this far in school. Parents and children expect that such ‘graduates’ from school will go on to high school and college. Hardly anyone wants to go back to agriculture. On the other hand, abilities in terms of academic competencies are far lower than they should be even based on curricular expectations of class 8.$stim$, 'en', 4, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (21,22);

-- passage 5 -> Q23
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$We take it for granted now that science has a social responsibility. The idea would not have occurred to Newton or Galileo. They thought of science as an account of the world as it is, and the only responsibility that they acknowledged was to tell the truth. The idea that science is a social enterprise is modern, and it begins at the industrial revolution. We are surprised that we cannot trace a social sense further back, because we nurse the illusion that the industrial revolution ended a golden age.$stim$, 'en', 5, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (23);

-- passage 6 -> Q31,32
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$“The history of science is the real history of mankind.” In this striking epigram, a nineteenth-century writer links science with its background. Like most epigrams, its power lies in emphasizing by contrast an aspect of truth which may be easily overlooked. In this case, it is easy to overlook the relations between science and mankind, and to treat the former has some abstract third party, which can sometimes be praised for its beneficial influences, but frequently and conveniently blamed for the horrors of war. Science and mankind cannot be divorced from time to time at men’s convenience. Yet we have seen that, in spite of countless opportunities of improvement, the opening years of the present period of civilization have been dominated by international conflict. Is this the inevitable result of the progress of science or does the fault lie elsewhere?$stim$, 'en', 6, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (31,32);

-- passage 7 -> Q33,34
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$Only with long experience and opening of his wares on many a beach where his language is not spoken, will the merchant come to know the worth of what he carries, and what is parochial and what is universal in his choice. Such delicate goods as justice, love and honour, courtesy, and indeed all the things we care for, are valid everywhere but they are variously moulded and often differently handled, and sometimes nearly unrecognizable if you meet them in a foreign land, and the art of learning fundamental common values is perhaps the greatest gain of travel to those who wish to live at ease among their fellows.$stim$, 'en', 7, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (33,34);

-- passage 8 -> Q41,42
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$Conventional classrooms, by emphasizing fixed duration over learning effectiveness, resign themselves to variable outcomes. The tyranny of the classroom is that every learner is subjected to the same set of lectures in the same way for the same duration. In the end, a few learners shine, some survive, and the rest are left behind. After the fixed duration, the classroom model moves on, with not a thought spared for those left behind. This is how we end up with 10 percent employability in our graduates after a decade and half of formal education. Repeating the same ineffectual script in the realm of skill education will not produce different results.$stim$, 'en', 8, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (41,42);

-- passage 9 -> Q43,44
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$When a child reaches adolescence, there is apt to be a conflict between the parents and the child, since the latter considers himself to be by now quite capable of managing his own affairs, while the former are filled with parental solicitude, which is often a disguise for love of power. Parents consider, usually, that the various moral problems which arise in adolescence are peculiarly their province. The options they express, however, are so dogmatic that the young seldom confide in them, and usually go their own way in secret.$stim$, 'en', 9, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (43,44);

-- passage 10 -> Q51
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$When an international team of pumped a carbon dioxide and water mix into underground basalt rocks, basic chemistry took over. The acidic mixture dissolved rocks' calcium and magnesium and formed limestone Basically carbon dioxide is converted into stone, exclaimed the scientists.$stim$, 'en', 10, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (51);

-- passage 11 -> Q52
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$Geographers analyzed 175 satellite images of ocean colour, which is an indicator of Phytoplankton productivity at the ocean's surface, and found that giant icebergs are responsible for storing up to 20 percent of carbon in the Southern Ocean. The researchers discovered that melting water from giant icebergs which contains iron and other nutrients, supports hitherto unexpectedly high levels of phytoplankton growth.$stim$, 'en', 11, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (52);

-- passage 12 -> Q53
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$Evolution has endowed caterpillars that feed on corn with a unique ability, they can induce the plant to turn off its defence against insect predators. This helps caterpillars to eat more and grow faster. The agent that causes this effect is the caterpillar's faeces or frass. The find could throw new light on compounds associated with plant response to pathogens like fungi or bacteria.$stim$, 'en', 12, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (53);

-- passage 13 -> Q62
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$Now-a-days there is a growing trend to use interconnected home devices. As consumers increasingly network their homes, the connected home device manufacturers and service providers will seek to overcome "thin profit margins by gathering more of our personal data-with or without our agreementturning the home into a corporate storefront". Corporate marketers will have powerful incentives to observe consumer behaviour to understand the buying needs and preferences of the device owners.$stim$, 'en', 13, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (62);

-- passage 14 -> Q63
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$Green growth involves rethinking growth strategies with regard to the impacts on environmental sustainability and the environmental resources available to poor and vulnerable groups. In rethinking growth, we need to focus on the current reality of a resource-constrained world. Resource intensive and, in particular energy intensive processes will need to make way for more efficient and resource frugal development strategies if we are to avoid an economic dead end or a world in which only a small elite is able to enjoy affluence in the midst of a sea of poverty.$stim$, 'en', 14, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (63);

-- passage 15 -> Q71
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$Unlike religion and science, poetry does not posit or expect any belief in absolute truths. Those forces or individuals who claim to have absolute truths in their grasp tend to turn dictatorial and tyrannical. Truth usually does not admit any contradictions or imperfections. It is unitarian. It is, therefore, not of much use for poetry. Poetry abides by the plurality of life and existence. Perhaps poetry follows reality which is plural, anachronistic, full of contradictions. Against the tyranny of truth, poetry remains a partisan of democratic reality. Against the arrogance of power, wealth and hierarchy, poetry proposes both humility and defiance.$stim$, 'en', 15, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (71);

-- passage 16 -> Q72
with s as (
  insert into public.pyq_stimuli (pyq_paper_id, stimulus_type, content_text, language, display_order, reviewer_status)
  values ('9e191ae4-68b9-47bf-9121-6d9d468a7bc5', 'passage', $stim$The flower was not invented to please us. It flaunted its petals and spread its perfume to attract an insect. The insect carries the pollen from flower to flower so that pollen is not carried away by wind and thus not wasted. What we call a flower's beauty is merely a by-product and a human invention. The perfume is not there to please us, it pleases us because it is there and we have been conditioned to it.$stim$, 'en', 16, 'pending')
  returning id
)
insert into public.pyq_question_stimuli (question_id, stimulus_id, display_order, reviewer_status)
select q.id, s.id, 1, 'pending' from public.pyq_questions q, s
where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5' and q.question_number in (72);

-- 4. record the gap
update public.pyq_papers
set source_url = 'https://www.upsc.gov.in/sites/default/files/QP-CSP-24-GENERAL-STUDIES-PAPER-II-180624.pdf',
    source_type = 'official',
    metadata = coalesce(metadata,'{}'::jsonb) || jsonb_build_object(
      'expected_question_count', 80,
      'missing_questions', '49,55,56,57,58',
      'rebuild_note', 'Rebuilt 2026-09-03 from solution docx with true paper numbering; prior 71 rows were mis-numbered (offsets +4/+5/+9). Q49,55-58 absent from source. Two passages (internet/fake-news serving Q13-14, media/reality serving Q61) also absent.')
where id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5';

-- 5. verify before commit
select (select count(*) from public.pyq_questions where pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5') as questions,
       (select count(*) from public.pyq_options o join public.pyq_questions q on q.id=o.question_id where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5') as options,
       (select count(*) from public.pyq_stimuli where pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5') as stimuli,
       (select count(*) from public.pyq_question_stimuli qs join public.pyq_questions q on q.id=qs.question_id where q.pyq_paper_id='9e191ae4-68b9-47bf-9121-6d9d468a7bc5') as links;
-- expect: questions=75  options=300  stimuli=16  links=24

-- commit;   -- uncomment after verifying