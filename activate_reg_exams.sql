begin;
update exams set is_active = true where slug in ('ifsca-grade-a','pfrda-grade-a') and is_active = false;
select slug, name, is_active from exams where slug in ('ifsca-grade-a','pfrda-grade-a','sebi-grade-a','rbi-grade-b') order by slug;
commit;
