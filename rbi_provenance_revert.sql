begin;
update pyq_papers set source_url = null
where id in (
  '06712b2e-5003-4d97-9d77-968c0e5be20d',
  'e6019bda-45f7-43bf-96d8-aac6f91f383f',
  'ba80e989-e6a2-46e2-98da-8da5966e16bf',
  '6b4c47a8-6488-4729-83ec-ae0c2e9e410a',
  'a2cf30d7-354f-4f88-ac7f-182206519104'
) and source_url like 'URL_%';
select id, year, source_type, source_url from pyq_papers
where id in (
  '06712b2e-5003-4d97-9d77-968c0e5be20d',
  'e6019bda-45f7-43bf-96d8-aac6f91f383f',
  'ba80e989-e6a2-46e2-98da-8da5966e16bf',
  '6b4c47a8-6488-4729-83ec-ae0c2e9e410a',
  'a2cf30d7-354f-4f88-ac7f-182206519104'
);
commit;
