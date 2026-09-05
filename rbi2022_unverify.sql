begin;
update pyq_questions set reviewer_status = 'pending'
where pyq_paper_id = '06712b2e-5003-4d97-9d77-968c0e5be20d'
  and reviewer_status = 'verified';
select reviewer_status, count(*) from pyq_questions
where pyq_paper_id='06712b2e-5003-4d97-9d77-968c0e5be20d' group by 1;
commit;
