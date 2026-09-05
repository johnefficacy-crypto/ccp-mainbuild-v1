begin;
update pyq_papers set source_url = v.url
from (values
  ('06712b2e-5003-4d97-9d77-968c0e5be20d'::uuid, 'REAL_URL_2022'),
  ('e6019bda-45f7-43bf-96d8-aac6f91f383f'::uuid, 'REAL_URL_2023'),
  ('ba80e989-e6a2-46e2-98da-8da5966e16bf'::uuid, 'REAL_URL_2024'),
  ('6b4c47a8-6488-4729-83ec-ae0c2e9e410a'::uuid, 'REAL_URL_2025'),
  ('a2cf30d7-354f-4f88-ac7f-182206519104'::uuid, 'REAL_URL_2026')
) as v(id, url)
where pyq_papers.id = v.id;
select id, year, source_type, source_url from pyq_papers
where exam_id = 'aded8ee9-e9ec-4287-9015-6db1919fa67e' order by year;
commit;
