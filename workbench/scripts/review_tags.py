"""Promote optional PYQ primary topic tags to reviewer_status='verified'.

    python review_tags.py [--execute]

WHY A SEPARATE PASS
    Verifying a question does NOT verify its tags. The question review RPC
    (update_pyq_question_review_atomic) cascades reviewer_status to the
    question's pyq_options only. Tag review is its own gate, and
    score_snapshots.py counts primary tags at reviewer_status='verified'.

WHAT IT PROMOTES
    Primary tags whose question is already 'verified'. A tag on a question
    still pending or rejected is left alone - the question is the thing that
    was reviewed, and a tag on an unreviewed question has no standing.

WHAT 'verified' MEANS FOR A TAG HERE
    The topic was chosen by reading the question against its paper's syllabus
    spine, one primary topic per question, validated against the subject's own
    catalogue so it cannot cross the GS/optional boundary. It is a judgement
    about fit, not a fact that can be checked against a source.

    Route: PATCH /api/admin/exam-intelligence/items/pyq_question_topic_tag/
    {tag_id}/review with a FLAT body - not the {reason, payload} CMS envelope.
    reviewer_notes is dropped server-side (supports_notes=False).
"""
import json, os, sys, time
import requests

EXECUTE = "--execute" in sys.argv
BASE = os.environ.get("CCP_API_BASE")
TOK = os.environ.get("CCP_ADMIN_JWT", "")
if not BASE or not TOK:
    sys.exit("error: set CCP_API_BASE and CCP_ADMIN_JWT")

EXAM = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
CMS = "/api/admin/exam-intelligence-cms"
INTEL = "/api/admin/exam-intelligence"

s = requests.Session()
s.headers["Authorization"] = "Bearer " + TOK
s.headers["Content-Type"] = "application/json; charset=utf-8"


def get_all(path, params):
    out, offset = [], 0
    while True:
        r = s.get(BASE + path, params=dict(params, limit=200, offset=offset), timeout=120)
        r.raise_for_status()
        d = r.json()
        items = d.get("items", d if isinstance(d, list) else [])
        out.extend(items)
        total = d.get("total", d.get("count"))
        offset += len(items)
        if not items or (total is not None and offset >= total):
            return out


print("fetching optional questions ...")
papers = get_all(CMS + "/pyq-papers", {"exam_id": EXAM})
opt_paper_ids = set()
qs = {}
for p in papers:
    rows = get_all(CMS + "/pyq-questions", {"pyq_paper_id": p["id"]})
    for q in rows:
        if (q.get("metadata") or {}).get("paper_kind") == "optional":
            opt_paper_ids.add(p["id"])
            qs[q["id"]] = q.get("reviewer_status")
print("optional papers  : %d" % len(opt_paper_ids))
print("optional questions: %d" % len(qs))

print("fetching tags ...")
tags = get_all(CMS + "/pyq-question-topic-tags", {})
mine = [t for t in tags
        if t.get("question_id") in qs
        and t.get("tag_role") == "primary"]
pending = [t for t in mine if t.get("reviewer_status") == "pending"]
eligible = [t for t in pending if qs.get(t["question_id"]) == "verified"]
held = [t for t in pending if qs.get(t["question_id"]) != "verified"]

print()
print("primary tags on optional questions : %d" % len(mine))
print("  already verified                 : %d" % sum(1 for t in mine if t.get("reviewer_status") == "verified"))
print("  pending, question verified       : %d   <- will promote" % len(eligible))
print("  pending, question not verified   : %d   <- held" % len(held))

if not EXECUTE:
    print()
    print("DRY RUN. Re-run with --execute to promote.")
    sys.exit(0)

ok = fail = 0
errs = []
for i, t in enumerate(eligible, 1):
    body = json.dumps({"reviewer_status": "verified"})
    try:
        r = s.patch(BASE + INTEL + "/items/pyq_question_topic_tag/%s/review" % t["id"],
                    data=body.encode("utf-8"), timeout=60)
        if r.status_code < 300:
            ok += 1
        else:
            fail += 1
            errs.append((t["id"], r.status_code, r.text[:140]))
    except Exception as e:                      # noqa: BLE001
        fail += 1
        errs.append((t["id"], "EXC", str(e)[:140]))
        time.sleep(2)
    if i % 200 == 0:
        print("  %d/%d  ok=%d fail=%d" % (i, len(eligible), ok, fail))

print()
print("verified : %d" % ok)
print("failed   : %d" % fail)
for tid, code, msg in errs[:10]:
    print("  %s %s %s" % (tid, code, msg))
if fail:
    print()
    print("Re-run - already-verified tags drop out of the eligible set.")
