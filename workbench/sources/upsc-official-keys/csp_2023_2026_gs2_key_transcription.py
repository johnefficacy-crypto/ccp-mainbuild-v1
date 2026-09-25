# UPSC CS(P) GS Paper II (CSAT) keys, transcribed from the upsc.gov.in scans. All four series per year. X = dropped.
# Every scan states "No. of Questions Dropped 0". Series B/C/D are 10-question block permutations of Series A;
# the transcription was checked for that: every 10-question block of B, C and D equals a block of A exactly.
# Sources (fetched 2026-09-25):
#   2023 final       https://www.upsc.gov.in/sites/default/files/AnsKey-CSP-2023-Paper-II-090524.pdf
#   2024 final       https://www.upsc.gov.in/sites/default/files/AnsKey-CivilServicesPExam-2024-GeneralStudies-II-210525.pdf
#   2025 final       https://www.upsc.gov.in/sites/default/files/AnsKeyCivilServicesP-Exam-2025-GeneralStudies-II-130526.pdf
#   2026 PROVISIONAL https://www.upsc.gov.in/sites/default/files/ProvAnsKey%E2%80%93GS-II-CSP-Exam-2026-270526.pdf
FINAL = {2023: True, 2024: True, 2025: True, 2026: False}
def K(s,n):
    v=s.split(); assert len(v)==n,(len(v),n); return dict(enumerate(v,1))
KEY={}
KEY[(2023,'A')]=K("A D C D B B A A D C C A B A D A D A C A  B B B A C B A C B C D C B C B C D D C D  A A A C D C A C A B D A A B B D C A D B  D D B C D C D D C B B B D D D A D A A C",80)
KEY[(2023,'B')]=K("D C B C B C D D C D B B B A C B A C B C  C A B A D A D A C A A D C D B B A A D C  B B D D D A D A A C D D B C D C D D C B  D A A B B D C A D B A A A C D C A C A B",80)
KEY[(2023,'C')]=K("B B B A C B A C B C A D C D B B A A D C  D C B C B C D D C D C A B A D A D A C A  D D B C D C D D C B A A A C D C A C A B  B B D D D A D A A C D A A B B D C A D B",80)
KEY[(2023,'D')]=K("C A B A D A D A C A D C B C B C D D C D  A D C D B B A A D C B B B A C B A C B C  D A A B B D C A D B B B D D D A D A A C  A A A C D C A C A B D D B C D C D D C B",80)
KEY[(2024,'A')]=K("B C C D B D C C D B A A B C B A D C B C  D C D C A B D B A D D B C A D B A C D C  C D A A B B D A D C B C C C C C D D C C  A D C C C D A D C D D D A C D D A D B B",80)
KEY[(2024,'B')]=K("D B C A D B A C D C D C D C A B D B A D  A A B C B A D C B C B C C D B D C C D B  D D A C D D A D B B A D C C C D A D C D  B C C C C C D D C C C D A A B B D A D C",80)
KEY[(2024,'C')]=K("D C D C A B D B A D B C C D B D C C D B  D B C A D B A C D C A A B C B A D C B C  A D C C C D A D C D C D A A B B D A D C  D D A C D D A D B B B C C C C C D D C C",80)
KEY[(2024,'D')]=K("A A B C B A D C B C D B C A D B A C D C  B C C D B D C C D B D C D C A B D B A D  B C C C C C D D C C D D A C D D A D B B  C D A A B B D A D C A D C C C D A D C D",80)
KEY[(2025,'A')]=K("C D D C C D C B D A D A D A C C B C D C  A D A D C D B D B C D A B B B B B B C B  B A C B D C C D D C B C D D C A D B B C  A C C C C B A D D D B D D B D C C A A C",80)
KEY[(2025,'B')]=K("D A B B B B B B C B A D A D C D B D B C  D A D A C C B C D C C D D C C D C B D A  B D D B D C C A A C A C C C C B A D D D  B C D D C A D B B C B A C B D C C D D C",80)
KEY[(2025,'C')]=K("A D A D C D B D B C C D D C C D C B D A  D A B B B B B B C B D A D A C C B C D C  A C C C C B A D D D B A C B D C C D D C  B D D B D C C A A C B C D D C A D B B C",80)
KEY[(2025,'D')]=K("D A D A C C B C D C D A B B B B B B C B  C D D C C D C B D A A D A D C D B D B C  B C D D C A D B B C B D D B D C C A A C  B A C B D C C D D C A C C C C B A D D D",80)
KEY[(2026,'A')]=K("A D C D A A A B D D D B D A B D A D B C  B B B A B B D B C B D A D C B A A B B C  C C B D C C C D B D A C D C D D D B C D  C B A B A B B A A A D B C C D C D A B D",80)
KEY[(2026,'B')]=K("D B C C D C D A B D C B A B A B B A A A  A C D C D D D B C D C C B D C C C D B D  D A D C B A A B B C B B B A B B D B C B  D B D A B D A D B C A D C D A A A B D D",80)
KEY[(2026,'C')]=K("D A D C B A A B B C B B B A B B D B C B  D B D A B D A D B C A D C D A A A B D D  D B C C D C D A B D C B A B A B B A A A  A C D C D D D B C D C C B D C C C D B D",80)
KEY[(2026,'D')]=K("B B B A B B D B C B D A D C B A A B B C  C C B D C C C D B D A C D C D D D B C D  C B A B A B B A A A D B C C D C D A B D  A D C D A A A B D D D B D A B D A D B C",80)
