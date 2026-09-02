"""Diff pyq_*_prelims_gs1_*.json correct_option_label against official UPSC keys.

Official keys transcribed from the UPSC answer-key PDFs, matched to the series
each JSON file claims in its filename. 2018 Set C is absent - no PDF available.
'X' = question dropped by UPSC.
Run from the repo root:  python diff_keys.py
"""
import json, os

OFFICIAL = {
 "2018": ("C",
 "BCBAABCADB CAACBBBBAB CBCBCDACAB BBBDABDCBC ADBBABDDCD "
 "BDBCCBCCCD CCBADCCCCD ACDABBBABB DDAAABDCBA CADCACDADC"),   
"2019": ("B",
 "DDBBBCAAAB DDCDDBBAAC DADBDACDCA DBCACDCADA AAABDDADCA "
 "BBACDABBAB DAADDDACBB BADBBCDAAA CBCCBBCBCC ADABDCACCD"),
"2021": ("C",
 "BBBDDDDCBD DBBDAAAAAD ACDBDDCBCX CBBBCCBCAB BBDDBBACDD "
 "BBACACDBAB CAABDCDACB CBDABCCCAD CABCBABDAC CBBABDAADD"),
"2022": ("A",
 "BCBCADADAC BBBBBBDDBA BDBCBACBBB DDDCBDDCBC ABDBCAAAAC "
 "CBDBBCBDBB XDBBCDCDAC CAADCAADDA DCCBDBCBBA BBBAAADDDB"),
"2023": ("A",
 "ABBADDCADD CCAACDBCBC DABABBCCBC AACXADBBBC ABBDDBBACD "
 "BCACBADDBC ACDDCDACAA BCDBBCBDCA ABADCCCDAD BBDCBBDDCC"),
"2024": ("C",
 "ADABCCDDBB CDCBCDBACD DABDCDDCAC DACCBDACDA AXDBBAXBAC "
 "DCDDBCBCDA BDABDADCDC CADAAADACA AADCDBDBCX DADACBABAB"),
}

def official(year):
    series, blob = OFFICIAL[year]
    keys = "".join(blob.split())
    assert len(keys) == 100, (year, len(keys))
    return series, {i + 1: keys[i] for i in range(100)}

print(f"{'file':<38} {'ser':<4} {'match':>5} {'diff':>5} {'drop-mismatch':>14}")
print("-" * 72)

for year in sorted(OFFICIAL):
    fn = next((f for f in os.listdir(".")
               if f.startswith(f"pyq_{year}_prelims_gs1_")), None)
    if not fn:
        print(f"  MISSING FILE for {year}")
        continue
    series, off = official(year)
    qs = {q["question_number"]: q
          for q in json.load(open(fn, encoding="utf-8"))["questions"]}

    diffs, dropmis = [], []
    for n in range(1, 101):
        o = off[n]
        j = (qs.get(n, {}).get("correct_option_label") or "").upper() or "X"
        if o == "X" and j != "X":
            dropmis.append((n, "official dropped, file has " + j))
        elif j == "X" and o != "X":
            dropmis.append((n, "file dropped, official has " + o))
        elif o != j:
            diffs.append((n, o, j))

    print(f"{fn:<38} {series:<4} {100-len(diffs)-len(dropmis):>5} "
          f"{len(diffs):>5} {len(dropmis):>14}")
    for n, o, j in diffs:
        print(f"      Q{n:<3} official={o}  file={j}")
    for n, msg in dropmis:
        print(f"      Q{n:<3} {msg}")

print("\n2018 Set C not checked - official key PDF not supplied.")
