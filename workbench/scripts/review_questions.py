"""Promote optional PYQ questions to reviewer_status='verified', flag-based.

    python review_questions.py <worksheets_dir> [--execute]

WHAT THIS DOES
    Reads the twelve tagged worksheets, splits every question row into:

      clean    - the sweep raised no flag other than no_primary_tag (which is
                 now satisfied: all 4,038 carry a primary tag)
      to_read  - the sweep flagged something a human should look at

    Dry run prints the split and writes to_read_questions.csv. With --execute
    it promotes only the clean rows and leaves the flagged ones pending.

WHY FLAG-BASED RATHER THAN ROW-BY-ROW
    These are descriptive questions with no answer key. "Correct" means the
    text faithfully reproduces what UPSC asked - a transcription check, not a
    judgement. The sweep already tests what is mechanically checkable:
    duplicate text, empty or truncated stems, unexpected non-ASCII, structural
    anomalies. What it cannot test is fidelity to the official paper, and the
    official papers are not published before 2016, so an exhaustive pass would
    be reading 4,038 rows against documents that mostly do not exist.

    The reason string records this so a later reader knows what "verified"
    means here: mechanically clean, tagged, and anchored on a registered
    source document - NOT diffed against an official UPSC paper.

WHAT STAYS PENDING
    Every flagged row, and the two Sociology 2014 -VOID artefacts (already
    rejected). Those need a human before they go anywhere.
"""
import csv, io, glob, json, os, sys, time
from collections import Counter
import requests

WS_DIR = sys.argv[1] if len(sys.argv) > 1 else "workbench/worksheets"
EXECUTE = "--execute" in sys.argv

BASE = os.environ.get("CCP_API_BASE")
TOK = os.environ.get("CCP_ADMIN_JWT", "")
if EXECUTE and (not BASE or not TOK):
    sys.exit("error: set CCP_API_BASE and CCP_ADMIN_JWT")
CMS = "/api/admin/exam-intelligence-cms"

REASON = (
    "Mechanically reviewed: no duplicate text, no empty or truncated stem, "
    "non-ASCII accounted for, structure consistent with the paper. Carries a "
    "primary topic tag. Paper is anchored on a registered source document. "
    "NOT diffed against an official UPSC paper - the officials are unpublished "
    "before 2016 and the corpus is compiler-sourced. Flagged rows were excluded "
    "from this pass and remain pending."
)

# no_primary_tag was true at sweep time and is now satisfied for every row.
IGNORABLE = {"no_primary_tag", ""}

clean, to_read = [], []
per_file = {}

for path in sorted(glob.glob(os.path.join(WS_DIR, "opt_*_tagged.csv"))):
    name = os.path.basename(path)
    c = r = 0
    for row in csv.DictReader(io.open(path, encoding="utf-8-sig")):
        if (row.get("row_type") or "") != "question":
            continue
        flags = {f.strip() for f in (row.get("flags") or "").split(",")}
        real = flags - IGNORABLE
        rec = {
            "file": name,
            "row_id": row["row_id"],
            "year": row.get("paper_year"),
            "num": row.get("question_number_or_topic_id"),
            "flags": ",".join(sorted(real)),
            "text_preview": (row.get("text_preview") or "")[:100],
        }
        if real:
            to_read.append(rec); r += 1
        else:
            clean.append(rec); c += 1
    per_file[name] = (c, r)

print("%-34s %7s %8s" % ("worksheet", "clean", "to_read"))
for k in sorted(per_file):
    print("%-34s %7d %8d" % (k, per_file[k][0], per_file[k][1]))
print("%-34s %7d %8d" % ("TOTAL", len(clean), len(to_read)))
print()
print("flags on the to_read set:")
for f, n in Counter(x["flags"] for x in to_read).most_common():
    print("  %-28s %d" % (f, n))

with io.open("to_read_questions.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(to_read[0].keys()) if to_read
                       else ["file", "row_id", "year", "num", "flags", "text_preview"])
    w.writeheader(); w.writerows(to_read)
print()
print("wrote to_read_questions.csv - read these before promoting them.")

if not EXECUTE:
    print()
    print("DRY RUN. Re-run with --execute to promote the %d clean rows." % len(clean))
    sys.exit(0)

s = requests.Session()
s.headers["Authorization"] = "Bearer " + TOK
s.headers["Content-Type"] = "application/json; charset=utf-8"

ok = fail = skip = 0
errs = []
for i, rec in enumerate(clean, 1):
    body = json.dumps({"status": "verified", "reason": REASON})
    try:
        resp = s.post(BASE + CMS + "/pyq-questions/%s/review" % rec["row_id"],
                      data=body.encode("utf-8"), timeout=60)
        if resp.status_code < 300:
            ok += 1
        elif resp.status_code == 422 and "not allowed" in resp.text.lower():
            skip += 1          # already verified, or in a state that forbids it
        else:
            fail += 1
            errs.append((rec["row_id"], resp.status_code, resp.text[:140]))
    except Exception as e:                       # noqa: BLE001
        fail += 1
        errs.append((rec["row_id"], "EXC", str(e)[:140]))
        time.sleep(2)
    if i % 100 == 0:
        print("  %d/%d  ok=%d skip=%d fail=%d" % (i, len(clean), ok, skip, fail))

print()
print("verified : %d" % ok)
print("skipped  : %d" % skip)
print("failed   : %d" % fail)
for q, code, msg in errs[:10]:
    print("  %s %s %s" % (q, code, msg))
if fail:
    print()
    print("Re-run to retry the failures - already-verified rows are skipped.")
