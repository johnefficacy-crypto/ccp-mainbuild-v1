"""Apply thematic-corpus topic tags, keyed by source_question_ref.

    python apply_thematic_tags.py <tags.csv> [--execute]

The thematic rows were loaded with `source_question_ref` (PSIR-P1-1991-T001)
and no question_number, so the tag file keys on the ref rather than on a
worksheet row_id. This resolves ref -> question_id from the server, then posts
one primary tag each.

Resume-safe by construction: it asks which questions already carry a primary
tag and posts only the remainder. That matters because the CMS tag route is a
plain INSERT - a duplicate surfaces as an unhandled 500, not a 409 - so a
naive re-run spends its whole time colliding with its own work.
"""
import csv, io, json, os, sys, time
import requests

if len(sys.argv) < 2:
    sys.exit(__doc__)
TAGS = sys.argv[1]
EXECUTE = "--execute" in sys.argv

BASE = os.environ.get("CCP_API_BASE")
TOK = os.environ.get("CCP_ADMIN_JWT", "")
if not BASE or not TOK:
    sys.exit("error: set CCP_API_BASE and CCP_ADMIN_JWT")
CMS = "/api/admin/exam-intelligence-cms"

s = requests.Session()
s.headers["Authorization"] = "Bearer " + TOK
s.headers["Content-Type"] = "application/json; charset=utf-8"


def get_all(path, params):
    out, offset = [], 0
    while True:
        r = s.get(BASE + CMS + path, params=dict(params, limit=200, offset=offset),
                  timeout=120)
        r.raise_for_status()
        d = r.json()
        items = d.get("items", d if isinstance(d, list) else [])
        out.extend(items)
        offset += len(items)
        if len(items) < 200:
            return out


want = list(csv.DictReader(io.open(TAGS, encoding="utf-8-sig")))
print("tag rows in file :", len(want))

print("resolving refs -> question ids ...")
papers = [p for p in get_all("/pyq-papers", {"exam_id": "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"})
          if (p.get("metadata") or {}).get("corpus_half") == "thematic"]
ref_to_id = {}
for p in papers:
    for q in get_all("/pyq-questions", {"pyq_paper_id": p["id"]}):
        if q.get("source_question_ref"):
            ref_to_id[q["source_question_ref"]] = q["id"]
print("thematic questions on the server :", len(ref_to_id))

print("checking existing primary tags ...")
tagged = {t["question_id"] for t in get_all("/pyq-question-topic-tags", {})
          if t.get("tag_role") == "primary"}

todo, missing = [], []
for row in want:
    qid = ref_to_id.get(row["ref"])
    if not qid:
        missing.append(row["ref"]); continue
    if qid in tagged:
        continue
    todo.append((qid, row["topic_id"], row["ref"]))

print()
print("already tagged        :", len(want) - len(todo) - len(missing))
print("to tag                :", len(todo))
print("ref not found on server:", len(missing), missing[:5])

if not EXECUTE:
    print()
    print("DRY RUN. Re-run with --execute to post.")
    sys.exit(0)

ok = fail = 0
errs = []
for i, (qid, tid, ref) in enumerate(todo, 1):
    body = json.dumps({
        "reason": "thematic optional corpus, pre-2011: primary topic tag",
        "payload": {
            "question_id": qid, "topic_id": tid, "tag_role": "primary",
            "tagging_source": "manual", "confidence_score": 0.9,
        },
    })
    try:
        r = s.post(BASE + CMS + "/pyq-question-topic-tags",
                   data=body.encode("utf-8"), timeout=60)
        if r.status_code < 300:
            ok += 1
        else:
            fail += 1; errs.append((ref, r.status_code, r.text[:110]))
    except Exception as e:                       # noqa: BLE001
        fail += 1; errs.append((ref, "EXC", str(e)[:110])); time.sleep(3)
    if i % 100 == 0:
        print("  %d/%d  ok=%d fail=%d" % (i, len(todo), ok, fail))

print()
print("tagged :", ok)
print("failed :", fail)
for ref, code, msg in errs[:10]:
    print("  ", ref, code, msg)
if fail:
    print()
    print("Re-run - already-tagged questions drop out of the work set.")
