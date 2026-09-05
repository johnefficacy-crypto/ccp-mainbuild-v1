begin;
update pyq_questions q set observed_difficulty = null
from pyq_papers p
where p.id = q.pyq_paper_id
  and p.exam_id = 'aded8ee9-e9ec-4287-9015-6db1919fa67e'
  and q.observed_difficulty is not null;
select coalesce(observed_difficulty,'(null)') as diff, count(*) from pyq_questions q
join pyq_papers p on p.id=q.pyq_paper_id
where p.exam_id='aded8ee9-e9ec-4287-9015-6db1919fa67e' group by 1;
commit;
