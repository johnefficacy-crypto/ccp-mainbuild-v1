"""Lock exam_topic_coverage rows. THIS IS THE STEP LEARNERS SEE.

    python lock_coverage.py [--subjects optional|mains-gs|all] [--execute]

``locked_topic_coverage`` in the Study OS mission-control path consumes
nothing but locked rows, so every state before this is invisible to an
aspirant and this one is not. Read the ranking before running it with
--execute.

Unlike snapshots, coverage review allows any target state in one PATCH
(admin_exam_intelligence.py:855-889) - draft goes straight to locked, and a
row can be walked back the same way if something looks wrong.

KNOWN CAVEAT, carried from the corpus and visible in the ranking:
History Paper-I's evidence counts include 180 map items (20 a year, tagged by
hint category). They are real questions UPSC asked, but a 20-item map question
is not a 15-mark essay prompt, so History P1 topics sit higher than their
weight in an aspirant's actual paper. Locking publishes that ordering.
"""
import json, os, sys, time
import requests

SCOPE = "optional"
if "--subjects" in sys.argv:
    SCOPE = sys.argv[sys.argv.index("--subjects") + 1]
EXECUTE = "--execute" in sys.argv

BASE = os.environ.get("CCP_API_BASE")
TOK = os.environ.get("CCP_ADMIN_JWT", "")
if not BASE or not TOK:
    sys.exit("error: set CCP_API_BASE and CCP_ADMIN_JWT")

EXAM = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
PHASE = "626ec667-4bbf-4420-8715-48c5b83e0d11"
INTEL = "/api/admin/exam-intelligence"
CMS = "/api/admin/exam-intelligence-cms"

s = requests.Session()
s.headers["Authorization"] = "Bearer " + TOK
s.headers["Content-Type"] = "application/json; charset=utf-8"


def get_all(path, params):
    out, offset = [], 0
    while True:
        PAGE = 100   # this route caps below 200; page by what it actually returns
        r = s.get(BASE + path, params=dict(params, limit=PAGE, offset=offset), timeout=120)
        r.raise_for_status()
        d = r.json()
        items = d.get("items", d.get("rows", d.get("coverage", d if isinstance(d, list) else [])))
        out.extend(items)
        offset += len(items)
        if len(items) < PAGE:     # short page = last page
            return out


print("fetching subjects and topics ...")
subjects = get_all(CMS + "/subjects", {})
if SCOPE == "optional":
    want = {x["id"] for x in subjects
            if (x.get("slug") or "").startswith("upsc-cse-mains-opt-")
            and x.get("is_active") is not False}
elif SCOPE == "mains-gs":
    want = {x["id"] for x in subjects if (x.get("slug") or "").startswith("upsc-cse-mains-gs")}
else:
    want = None

topics = {}
for sub in subjects:
    if want is not None and sub["id"] not in want:
        continue
    for t in get_all(CMS + "/topics", {"subject_id": sub["id"]}):
        topics[t["id"]] = sub.get("slug")
print("topics in scope : %d" % len(topics))

print("fetching coverage ...")
# The route does .limit(limit+offset) then slices in Python, and PostgREST
# caps a select at 1000 rows - so paging past 1000 silently returns nothing.
# Filtering to drafts keeps the result well under that ceiling.
rows = get_all(INTEL + "/topic-coverage",
               {"exam_id": EXAM, "status": "draft"})
mine = [r for r in rows if want is None or r.get("topic_id") in topics]
todo = [r for r in mine if r.get("status") != "locked"]

print()
print("coverage rows in scope : %d" % len(mine))
print("  already locked       : %d" % (len(mine) - len(todo)))
print("  to lock              : %d" % len(todo))

if todo:
    hi = sum(1 for r in todo if r.get("high_yield"))
    print("  of those, high-yield : %d" % hi)

if not EXECUTE:
    print()
    print("DRY RUN. Re-run with --execute to publish.")
    sys.exit(0)

ok = fail = 0
errs = []
for i, r in enumerate(todo, 1):
    body = json.dumps({"reviewer_status": "locked"})
    try:
        resp = s.patch(BASE + INTEL + "/topic-coverage/%s/review" % r["id"],
                       data=body.encode("utf-8"), timeout=60)
        if resp.status_code < 300:
            ok += 1
        else:
            fail += 1; errs.append((r["id"], resp.status_code, resp.text[:130]))
    except Exception as e:                       # noqa: BLE001
        fail += 1; errs.append((r["id"], "EXC", str(e)[:130])); time.sleep(2)
    if i % 100 == 0:
        print("  %d/%d  locked=%d fail=%d" % (i, len(todo), ok, fail))

print()
print("locked : %d" % ok)
print("failed : %d" % fail)
for rid, code, msg in errs[:10]:
    print("  %s %s %s" % (rid, code, msg))
if fail:
    print()
    print("Re-run - already-locked rows drop out of the work set.")
