import csv, io, glob, os
for path in glob.glob(r"workbench\worksheets\opt_*_reviewed.csv"):
    rows = list(csv.DictReader(io.open(path, encoding="utf-8-sig")))
    for r in rows:
        r["assign_topic_id"] = ""      # already applied; re-posting 409s and blocks the decision
    with io.open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("blanked", os.path.basename(path))
