# UPSC CS(P) GS Paper I official final keys, transcribed from the upsc.gov.in scans. X = dropped.
# Only the series each corpus year follows is transcribed, except 2018 (all four, to confirm the series).
# Sources (fetched 2026-09-25):
#   2018 https://www.upsc.gov.in/sites/default/files/AnsKey-CSP-18-Paper-I.pdf            (Series A-D, 0 dropped)
#   2019 https://www.upsc.gov.in/sites/default/files/AnsKeyCSP-19-GS_I.pdf                (Series B, NIL dropped)
#   2021 https://www.upsc.gov.in/sites/default/files/Anskey-CSP-21-GS-I-300522.pdf        (Series C, Q30 dropped)
#   2022 https://www.upsc.gov.in/sites/default/files/AnsKey-CSP-2022-Paper-I-040723.pdf   (Series A, Q61 dropped)
#   2023 https://www.upsc.gov.in/sites/default/files/AnsKey-CSP-2023-Paper-I-090524.pdf   (Series A, Q34 dropped)
#   2025 https://www.upsc.gov.in/sites/default/files/AnsKeyCivilServicesP-Exam-2025-GeneralStudies-I-130526.pdf
#        (Series A, 0 dropped; identical to workbench/sources/upsc-official-keys/UPSC-CSE-2025-GS-1-set A-OFFCIAL-ANSWER-KEY.pdf)
def _k(s):
    v = s.split()
    assert len(v) == 100, len(v)
    return dict(enumerate(v, 1))

KEY = {
    (2018, 'A'): _k("B D C B A C A D C A C D A D C  A C D A B B B A B B D D A A A  C A A C B B B B A B C D C B C  "
                    "B C C C D C C B A D C C C C D  A D B B A B D D C D B D B C C  D A C A B B B B D A B D C B C  "
                    "B C B A A B C A D B"),
    (2018, 'B'): _k("D A C A B B B B D A B D C B C  B C C C D C C B A D C C C C D  B C B A A B C A D B B D C B A  "
                    "C A D C A C D A D C C A A C B  B B B A B C D C B C A D B B A  B D D C D B D B C C A C D A B  "
                    "B B A B B D D A A A"),
    (2018, 'C'): _k("B C B A A B C A D B C A A C B  B B B A B C D C B C D A C A B  B B B D A B D C B C A D B B A  "
                    "B D D C D B D B C C B C C C D  C C B A D C C C C D A C D A B  B B A B B D D A A A B D C B A  "
                    "C A D C A C D A D C"),
    (2018, 'D'): _k("A D B B A B D D C D B D B C C  B D C B A C A D C A C D A D C  B C C C D C C B A D C C C C D  "
                    "D A C A B B B B D A B D C B C  A C D A B B B A B B D D A A A  B C B A A B C A D B C A A C B  "
                    "B B B A B C D C B C"),
    (2019, 'B'): _k("D D B B B C A A A B D D C D D  B B A A C D A D B D A C D C A  D B C A C D C A D A A A A B D  "
                    "D A D C A B B A C D A B B A B  D A A D D D A C B B B A D B B  C D A A A C B C C B B C B C C  "
                    "A D A B D C A C C D"),
    (2021, 'C'): _k("B B B D D D D C B D D B B D A A A A A D  A C D B D D C B C X C B B B C C B C A B  "
                    "B B D D B B A C D D B B A C A C D B A B  C A A B D C D A C B C B D A B C C C A D  "
                    "C A B C B A B D A C C B B A B D A A D D"),
    (2022, 'A'): _k("B C B C A D A D A C B B B B B B D D B A  B D B C B A C B B B D D D C B D D C B C  "
                    "A B D B C A A A A C C B D B B C B D B B  X D B B C D C D A C C A A D C A A D D A  "
                    "D C C B D B C B B A B B B A A A D D D B"),
    (2023, 'A'): _k("A B B A D D C A D D C C A A C D B C B C  D A B A B B C C B C A A C X A D B B B C  "
                    "A B B D D B B A C D B C A C B A D D B C  A C D D C D A C A A B C D B B C B D C A  "
                    "A B A D C C C D A D B B D C B B D D C C"),
    (2025, 'A'): _k("B A A B D C A A A A C C B A B  C B D B C B C D D C C A C C C  B C B A A C D C B B C D C C B  "
                    "B C D D A C C A A C D D A D B  D A D C A C C A B D B C B A C  B A A C D A A B B A A C D D A  "
                    "D D C D A D A A A B"),
}
