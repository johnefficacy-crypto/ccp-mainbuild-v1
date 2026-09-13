"""Apply a tagged worksheet, skipping rows that already carry a primary tag.

    python apply_resume.py <worksheet_tagged.csv> <topic_catalog.json> <subject> <paper>

    e.g. python apply_resume.py ^
           workbench\\worksheets\\opt_socio_p2_tagged.csv ^
           workbench\\catalogs\\opt_socio_p2_topics.json ^
           "Sociology" 2

WHY THIS EXISTS
    pyq_question_review.py apply re-POSTs every row on every run. Rows already
    tagged come back 409 and cost a full round-trip each, so a run interrupted
    at 80% spends most of the next attempt re-colliding with its own work. On a
    backend that drops long connections that can fail to converge at all.

    This asks the server which questions already have a primary tag, subtracts
    them, and POSTs only what is missing. Interrupt it and re-run: the second
    pass starts from wherever the first stopped.

WHAT IT DOES NOT DO
    No decision/difficulty handling - tags only. Use the real tool for those.
    Rows whose assign_topic_id is blank are skipped, as there.
"""
import csv, io, json, os, sys, time
import requests

if len(sys.argv) != 5:
    sys.exit(__doc__)
WS, CAT, SUBJECT, PAPER = sys.argv[1:5]

BASE = os.environ.get("CCP_API_BASE")
TOK = os.environ.get("CCP_ADMIN_JWT", "")
if not BASE or not TOK:
    sys.exit("error: set CCP_API_BASE and CCP_ADMIN_JWT")
CMS = "/api/admin/exam-intelligence-cms"

s = requests.Session()
s.headers["Authorization"] = "Bearer " + TOK
s.headers["Content-Type"] = "application/json; charset=utf-8"


def get_all(path, params):
    """Page through a list endpoint, returning every row."""
    out, offset = [], 0
    while True:
        p = dict(params, limit=200, offset=offset)
        r = s.get(BASE + CMS + path, params=p, timeout=120)
        r.raise_for_status()
        d = r.json()
        items = d.get("items", d if isinstance(d, list) else [])
        out.extend(items)
        total = d.get("total")
        offset += len(items)
        if not items or (total is not None and offset >= total):
            return out


cat = json.load(io.open(CAT, encoding="utf-8"))
cat = cat["items"] if isinstance(cat, dict) and "items" in cat else cat
valid = {c["id"] for c in cat}

rows = [r for r in csv.DictReader(io.open(WS, encoding="utf-8-sig"))
        if (r.get("row_type") or "") == "question" and (r.get("assign_topic_id") or "").strip()]
print("worksheet rows with a topic id : %d" % len(rows))

bad = [r for r in rows if r["assign_topic_id"] not in valid]
if bad:
    sys.exit("error: %d row(s) reference a topic id not in the catalogue, e.g. %s"
             % (len(bad), bad[0]["assign_topic_id"]))

# which of this paper's questions already carry a primary tag
print("asking the server what is already tagged ...")
tags = get_all("/pyq-question-topic-tags", {})
done = {t["question_id"] for t in tags if t.get("tag_role") == "primary"}
print("primary tags already on the server : %d" % len(done))

todo = [r for r in rows if r["row_id"] not in done]
print("to post                            : %d" % len(todo))
if not todo:
    sys.exit("nothing to do - this paper is fully tagged.")

ok = fail = 0
errs = []
for i, r in enumerate(todo, 1):
    body = json.dumps({
        "reason": "optional PYQ primary topic tag (resume-safe apply)",
        "payload": {
            "question_id": r["row_id"],
            "topic_id": r["assign_topic_id"],
            "tag_role": "primary",
            "tagging_source": "manual",
            "confidence_score": 0.9,
        },
    })
    try:
        resp = s.post(BASE + CMS + "/pyq-question-topic-tags",
                      data=body.encode("utf-8"), timeout=60)
        if resp.status_code < 300:
            ok += 1
        elif resp.status_code == 409:
            ok += 1          # already there; same end state
        else:
            fail += 1
            errs.append((r["row_id"], resp.status_code, resp.text[:120]))
    except Exception as e:                      # noqa: BLE001
        fail += 1
        errs.append((r["row_id"], "EXC", str(e)[:120]))
        time.sleep(2)                            # let a flaky backend recover
    if i % 25 == 0:
        print("  %d/%d  ok=%d fail=%d" % (i, len(todo), ok, fail))

print()
print("posted ok : %d" % ok)
print("failed    : %d" % fail)
for q, code, msg in errs[:10]:
    print("  %s %s %s" % (q, code, msg))
if fail:
    print()
    print("Re-run this same command - it will skip everything that landed.")
