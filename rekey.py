"""Rewrite correct_option_label in every PYQ GS1 JSON from the official UPSC keys.

Not a patch. The existing field disagrees with the official keys on 104 of 599
questions (17%), and the disagreement is not uniform across papers, so the field
is treated as unsourced and replaced wholesale rather than corrected cell by cell.

Official keys transcribed from the UPSC answer-key PDFs, matched to the series
each filename claims. Series labels for 2021 and 2024 are independently confirmed
by drop position; 2018 and 2019 have no drops to check against; 2022 and 2023
carry drop positions in the JSON that match no official series, so their series
label rests on the filename alone -- see NOTE below.

'X' = dropped by UPSC -> correct_option_label set to None.

Backs each file up to <name>.bak. Run from the repo root:  python rekey.py
"""
import json, os, shutil

KEYS = {
    "2018": ("c",
        "BCBAABCADB CAACBBBBAB CBCBCDACAB BBBDABDCBC ADBBABDDCD "
        "BDBCCBCCCD CCBADCCCCD ACDABBBABB DDAAABDCBA CADCACDADC"),
    "2019": ("b",
        "DDBBBCAAAB DDCDDBBAAC DADBDACDCA DBCACDCADA AAABDDADCA "
        "BBACDABBAB DAADDDACBB BADBBCDAAA CBCCBBCBCC ADABDCACCD"),
    "2021": ("c",
        "BBBDDDDCBD DBBDAAAAAD ACDBDDCBCX CBBBCCBCAB BBDDBBACDD "
        "BBACACDBAB CAABDCDACB CBDABCCCAD CABCBABDAC CBBABDAADD"),
    "2022": ("a",
        "BCBCADADAC BBBBBBDDBA BDBCBACBBB DDDCBDDCBC ABDBCAAAAC "
        "CBDBBCBDBB XDBBCDCDAC CAADCAADDA DCCBDBCBBA BBBAAADDDB"),
    "2023": ("a",
        "ABBADDCADD CCAACDBCBC DABABBCCBC AACXADBBBC ABBDDBBACD "
        "BCACBADDBC ACDDCDACAA BCDBBCBDCA ABADCCCDAD BBDCBBDDCC"),
    "2024": ("c",
        "ADABCCDDBB CDCBCDBACD DABDCDDCAC DACCBDACDA AXDBBAXBAC "
        "DCDDBCBCDA BDABDADCDC CADAAADACA AADCDBDBCX DADACBABAB"),
}

total_changed = total_blocked = 0

for year in sorted(KEYS):
    series, blob = KEYS[year]
    keys = "".join(blob.split())
    if len(keys) != 100:
        print(f"{year}: BAD KEY LENGTH {len(keys)} - fix before running")
        continue

    fn = next((f for f in os.listdir(".")
               if f.startswith(f"pyq_{year}_prelims_gs1_")), None)
    if not fn:
        print(f"{year}: file not found")
        continue

    claimed = fn.split("_")[-1].split(".")[0].replace("set", "").lower()
    if claimed != series:
        print(f"{year}: SERIES MISMATCH - filename says {claimed}, "
              f"key is {series}. Skipping.")
        continue

    doc = json.load(open(fn, encoding="utf-8"))
    qs = {q["question_number"]: q for q in doc["questions"]}

    changed, blocked, dropped = [], [], []
    for n in range(1, 101):
        q = qs.get(n)
        if q is None:
            blocked.append((n, "question absent from file"))
            continue

        want = keys[n - 1]
        old = q.get("correct_option_label")

        if want == "X":
            if old is not None:
                q["correct_option_label"] = None
                dropped.append(n)
            continue

        want = want.lower()
        labels = {o.get("label") for o in q.get("options", [])}
        if want not in labels:
            # Refuse rather than write a label the question does not have.
            blocked.append((n, f"key {want!r} not in options {sorted(labels)}"))
            continue
        if old != want:
            q["correct_option_label"] = want
            changed.append((n, old, want))

    if changed or dropped:
        shutil.copy2(fn, fn + ".bak")
        with open(fn, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    total_changed += len(changed)
    total_blocked += len(blocked)
    print(f"\n{fn}  series {series}  "
          f"{len(changed)} relabelled, {len(dropped)} set to dropped, "
          f"{len(blocked)} blocked")
    for n, old, new in changed:
        print(f"   Q{n:<4} {old} -> {new}")
    for n in dropped:
        print(f"   Q{n:<4} -> dropped (null)")
    for n, why in blocked:
        print(f"   Q{n:<4} BLOCKED: {why}")

print(f"\ntotal: {total_changed} relabelled, {total_blocked} blocked")
print("""
NOTE on 2022 and 2023: their JSON drop positions (Q48, Q54) match no official
series. Official Series A drops Q61 (2022) and Q34 (2023). This script writes
the Series A keys per the filename. If the blocked list is non-empty for those
two years, the series label is likely wrong -- stop and re-derive before loading.
""")
