"""Lock v2.0 score snapshots: draft -> reviewed -> locked.

    python lock_snapshots.py [--subjects optional|mains-gs|all] [--execute]

TWO STEPS, NOT ONE
    _SNAPSHOT_TRANSITIONS (admin_exam_intelligence.py:2869) allows
    draft -> {reviewed, rejected} and reviewed -> {locked, rejected, draft}.
    There is no draft -> locked edge, so each snapshot takes two PATCHes.
    Resumable: a snapshot already at 'reviewed' skips step one, one already
    'locked' is left alone.

WHAT LOCKING MEANS
    coverage_derivation reads ONLY locked snapshots, filtered on MODEL_VERSION.
    Locking is the operator saying this score is fit to rank a learner's study
    plan. Everything upstream is verified: papers anchored on a registered
    source document, questions mechanically reviewed, primary tags reviewed.

    What locking does NOT assert: that the score is well-calibrated for this
    corpus. The v2.0 cohort model ranks a topic against its own paper's peers,
    so a topic can outrank a more-asked topic in a larger paper. That is
    deliberate. Read the ranking before locking it.

    Note also that History Paper-I's counts include 180 map items tagged by
    hint category - real questions, but not full-length ones. Its topics sit
    high partly for that reason.

SCOPE
    --subjects optional   the twelve upsc-cse-mains-opt-* subjects (default)
    --subjects mains-gs   the five GS subjects on the Mains phase
    --subjects all        every v2.0 draft in the exam
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
INTEL = "/api/admin/exam-intelligence"
CMS = "/api/admin/exam-intelligence-cms"
MODEL = "v2.0"

s = requests.Session()
s.headers["Authorization"] = "Bearer " + TOK
s.headers["Content-Type"] = "application/json; charset=utf-8"


def get_all(path, params):
    out, offset = [], 0
    while True:
        r = s.get(BASE + path, params=dict(params, limit=200, offset=offset), timeout=120)
        r.raise_for_status()
        d = r.json()
        items = d.get("items", d.get("snapshots", d if isinstance(d, list) else []))
        out.extend(items)
        total = d.get("total", d.get("count"))
        offset += len(items)
        if not items or (total is not None and offset >= total):
            return out


print("fetching subjects and topics ...")
subjects = get_all(CMS + "/subjects", {})
if SCOPE == "optional":
    want = {x["id"] for x in subjects if (x.get("slug") or "").startswith("upsc-cse-mains-opt-")}
elif SCOPE == "mains-gs":
    want = {x["id"] for x in subjects
            if (x.get("slug") or "").startswith("upsc-cse-mains-gs")}
else:
    want = None
print("subjects in scope : %s" % ("all" if want is None else len(want)))

topic_subject = {}
for sub in subjects:
    if want is not None and sub["id"] not in want:
        continue
    for t in get_all(CMS + "/topics", {"subject_id": sub["id"]}):
        topic_subject[t["id"]] = sub.get("slug")
print("topics in scope   : %d" % len(topic_subject))

print("fetching snapshots ...")
MAINS_PHASE = "626ec667-4bbf-4420-8715-48c5b83e0d11"
# Omitting exam_phase_id returns ONLY exam-wide rows (exam_phase_id IS NULL),
# which is 12 legacy snapshots - not the phase-scoped drafts we just computed.
snaps = get_all(INTEL + "/exams/%s/score-snapshots" % EXAM,
                {"exam_phase_id": MAINS_PHASE})
mine = [x for x in snaps
        if x.get("model_version") == MODEL
        and (want is None or x.get("topic_id") in topic_subject)]

drafts = [x for x in mine if x.get("status") == "draft"]
reviewed = [x for x in mine if x.get("status") == "reviewed"]
locked = [x for x in mine if x.get("status") == "locked"]

print()
print("%s snapshots in scope : %d" % (MODEL, len(mine)))
print("  draft    -> needs two PATCHes : %d" % len(drafts))
print("  reviewed -> needs one         : %d" % len(reviewed))
print("  locked   -> nothing to do     : %d" % len(locked))
print("  total calls                   : %d" % (len(drafts) * 2 + len(reviewed)))

if not EXECUTE:
    print()
    print("DRY RUN. Re-run with --execute to lock.")
    sys.exit(0)


NOTE = ("v2.0 cohort model. Evidence chain: papers anchored on a registered "
        "source document, questions mechanically reviewed, primary tags reviewed. "
        "Caveat: History Paper-I counts include 180 map items tagged by hint "
        "category, so its topics rank high partly on those rather than on "
        "full-length questions.")


def patch(sid, status):
    body = json.dumps({"status": status, "reviewer_notes": NOTE})
    r = s.patch(BASE + INTEL + "/score-snapshots/%s/review" % sid,
                data=body.encode("utf-8"), timeout=60)
    return r


ok = fail = 0
errs = []
work = [(x["id"], "draft") for x in drafts] + [(x["id"], "reviewed") for x in reviewed]
for i, (sid, start) in enumerate(work, 1):
    try:
        if start == "draft":
            r = patch(sid, "reviewed")
            if r.status_code >= 300:
                fail += 1; errs.append((sid, "review", r.status_code, r.text[:120])); continue
        r = patch(sid, "locked")
        if r.status_code < 300:
            ok += 1
        else:
            fail += 1; errs.append((sid, "lock", r.status_code, r.text[:120]))
    except Exception as e:                       # noqa: BLE001
        fail += 1; errs.append((sid, "exc", "EXC", str(e)[:120])); time.sleep(2)
    if i % 100 == 0:
        print("  %d/%d  locked=%d fail=%d" % (i, len(work), ok, fail))

print()
print("locked : %d" % ok)
print("failed : %d" % fail)
for sid, step, code, msg in errs[:10]:
    print("  %s %s %s %s" % (sid, step, code, msg))
if fail:
    print()
    print("Re-run - already-locked snapshots drop out of the work set.")
