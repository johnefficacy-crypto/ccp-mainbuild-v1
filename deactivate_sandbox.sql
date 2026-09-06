begin;
update exams set is_active = false where slug = 'ssc-cgl-legacy-sandbox-do-not-use';
select slug, name, is_active from exams where slug = 'ssc-cgl-legacy-sandbox-do-not-use';
commit;
