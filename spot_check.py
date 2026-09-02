import json, glob

# 3 consecutive per cluster; clusters placed to straddle drops where they exist
CLUSTERS = {
    "2018": [(1, 3), (24, 26), (36, 38), (63, 65), (98, 100)],
    "2019": [(1, 3), (49, 51), (98, 100)],
    "2021": [(29, 32), (49, 51), (98, 100)],
    "2022": [(47, 50), (24, 26), (98, 100)],
    "2023": [(53, 56), (24, 26), (98, 100)],
    "2024": [(41, 44), (46, 49), (89, 92)],
}

for f in sorted(glob.glob("pyq_20*_prelims_gs1_*.json")):
    year = f.split("_")[1]
    qs = {q["question_number"]: q for q in
          json.load(open(f, encoding="utf-8"))["questions"]}
    print("\n=== %s (%s) ===" % (f, year))
    for lo, hi in CLUSTERS.get(year, []):
        for n in range(lo, hi + 1):
            q = qs.get(n)
            if not q:
                print("  %3d  MISSING FROM FILE" % n)
                continue
            key = q.get("correct_option_label") or "-DROPPED-"
            opt = next((o["text"] for o in q["options"]
                        if o["label"] == key), "")
            stem = " ".join(q["question_text"].split())[:70]
            print("  %3d  %s  %-40s | %s" % (n, key, opt[:40], stem))
