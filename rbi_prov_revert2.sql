begin;
update pyq_papers set source_url = null
where exam_id = 'aded8ee9-e9ec-4287-9015-6db1919fa67e'
  and source_url like 'REAL_URL_%';
select id, year, source_type, source_url from pyq_papers
where exam_id = 'aded8ee9-e9ec-4287-9015-6db1919fa67e' order by year;
commit;
