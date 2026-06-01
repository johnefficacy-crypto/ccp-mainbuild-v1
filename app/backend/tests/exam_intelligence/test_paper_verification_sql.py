"""Paper #1 PYQ verification SQL.

This test is documentation-as-code for the canonical operator SQL used to
verify paper #1 ingest completeness.

It intentionally records the current known state:
- total_rows = 100
- non_rejected_rows = 98
- rejected_rows = 2
- duplicate_question_numbers = 0
- missing_question_numbers = 2
- bad_mcq_option_rows = 1
- verification_status = FAIL

The current paper is therefore not activation-ready.
"""

from __future__ import annotations


PAPER_1_PYQ_PAPER_ID = "22ea7f1b-d40b-46e2-b111-efdfc20e6f94"

EXPECTED_PAPER_1_VERIFICATION = {
    "total_rows": 100,
    "non_rejected_rows": 98,
    "rejected_rows": 2,
    "duplicate_question_numbers": 0,
    "missing_question_numbers": 2,
    "bad_mcq_option_rows": 1,
    "verification_status": "FAIL",
}

PAPER_1_VERIFICATION_SQL = f"""
with q as (
  select *
  from public.pyq_questions
  where pyq_paper_id = '{PAPER_1_PYQ_PAPER_ID}'
),
active_q as (
  select *
  from q
  where reviewer_status <> 'rejected'
),
dup_numbers as (
  select question_number
  from active_q
  group by question_number
  having count(*) > 1
),
missing_numbers as (
  select gs.question_number
  from generate_series(1, 100) gs(question_number)
  left join (
    select distinct question_number
    from active_q
    where question_number is not null
  ) a using (question_number)
  where a.question_number is null
),
bad_mcq_options as (
  select q.id
  from active_q q
  left join public.pyq_options o on o.question_id = q.id
  where q.question_type = 'mcq'
  group by q.id
  having count(o.id) < 4
      or sum(case when o.is_correct then 1 else 0 end) <> 1
)
select
  (select count(*) from q) as total_rows,
  (select count(*) from active_q) as non_rejected_rows,
  (select count(*) from q where reviewer_status = 'rejected') as rejected_rows,
  (select count(*) from dup_numbers) as duplicate_question_numbers,
  (select count(*) from missing_numbers) as missing_question_numbers,
  (select count(*) from bad_mcq_options) as bad_mcq_option_rows,
  case
    when (select count(*) from q) = 100
     and (select count(*) from dup_numbers) = 0
     and (select count(*) from missing_numbers) = 0
     and (select count(*) from bad_mcq_options) = 0
    then 'PASS'
    else 'FAIL'
  end as verification_status;
""".strip()


def test_paper_1_verification_expected_counts_are_documented():
    assert PAPER_1_PYQ_PAPER_ID == "22ea7f1b-d40b-46e2-b111-efdfc20e6f94"
    assert EXPECTED_PAPER_1_VERIFICATION == {
        "total_rows": 100,
        "non_rejected_rows": 98,
        "rejected_rows": 2,
        "duplicate_question_numbers": 0,
        "missing_question_numbers": 2,
        "bad_mcq_option_rows": 1,
        "verification_status": "FAIL",
    }


def test_paper_1_verification_sql_contains_required_gates():
    assert "from public.pyq_questions" in PAPER_1_VERIFICATION_SQL
    assert "left join public.pyq_options" in PAPER_1_VERIFICATION_SQL
    assert "duplicate_question_numbers" in PAPER_1_VERIFICATION_SQL
    assert "missing_question_numbers" in PAPER_1_VERIFICATION_SQL
    assert "bad_mcq_option_rows" in PAPER_1_VERIFICATION_SQL
    assert "verification_status" in PAPER_1_VERIFICATION_SQL
    assert PAPER_1_PYQ_PAPER_ID in PAPER_1_VERIFICATION_SQL
    
    