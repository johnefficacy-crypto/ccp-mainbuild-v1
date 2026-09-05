begin;
insert into topics (subject_id, parent_topic_id, slug, name, level, metadata)
values
  ((select id from subjects where slug='english-language'),
   '66666666-6666-6666-6666-666666666665',
   'eng-argument-evaluation-in-a-passage-3f8c21ba',
   'Argument evaluation in a passage', 'microtopic', '{}'::jsonb),
  ((select id from subjects where slug='english-language'),
   '00ee2e5e-8040-49bc-a6bb-4646a15f4867',
   'eng-sentence-level-correctness-selection-9d4e07c1',
   'Sentence-level correctness selection', 'microtopic', '{}'::jsonb),
  ((select id from subjects where slug='general-intelligence-reasoning'),
   'c1d7181a-a5c2-4301-9b7d-e785166127c3',
   'reas-clock-time-scheduling-puzzle-6b2a94df',
   'Clock-time scheduling puzzle', 'microtopic', '{}'::jsonb),
  ((select id from subjects where slug='quantitative-aptitude'),
   '66666666-6666-6666-6666-666666666663',
   'qa-set-based-data-interpretation-8e13c5a7',
   'Set-based data interpretation', 'microtopic', '{}'::jsonb);
select t.id, t.name, t.slug, p.name as parent from topics t join topics p on p.id=t.parent_topic_id
where t.slug in ('eng-argument-evaluation-in-a-passage-3f8c21ba','eng-sentence-level-correctness-selection-9d4e07c1','reas-clock-time-scheduling-puzzle-6b2a94df','qa-set-based-data-interpretation-8e13c5a7');
commit;
