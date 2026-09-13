"""Promote thematic-corpus questions to reviewer_status='verified'.

    python review_thematic_questions.py [--subject <stem>] [--execute]

    stems: psir_p1 psir_p2 socio_p1 socio_p2 anth_p1 anth_p2
           pubad_p1 pubad_p2 hist_p1 hist_p2 geog_p1 geog_p2
           (omit --subject to do all twelve)

WHY NOT THE WORKSHEET ROUTE
The year-wise corpus went export -> sweep -> worksheet -> apply. That was worth
it there because the sweep's flags were the review: duplicate text, truncated
stems, unexpected non-ASCII.

For the thematic half those checks were already run at load time, on the source
rather than on the database:
  - duplicate text within a subject-paper-year was detected and 8 rows were
    skipped, with a ninth refused by the server's own content hash;
  - every row carries exactly one year, verified across all 9,117 source rows;
  - the ligature defect that produced 45 bad rows in the year-wise half was
    fixed in the parser before this half was extracted.

So a second sweep would re-derive what is already known. This promotes directly
and records that basis in the reason string.

WHAT 'verified' MEANS HERE, and it is narrower than the word suggests
The text is what the compiler's topic-wise index printed, de-duplicated, tagged
to a primary topic, on a paper anchored to a registered source document. It has
NOT been diffed against an official UPSC paper - the officials are unpublished
before 2016 and this corpus reaches back to 1980. Nor is the paper composition
known: metadata.paper_reconstructed is false on every one of the 31 paper rows.

Route: PATCH /api/admin/exam-intelligence/items/pyq_question/{id}/review with a
FLAT body. Not the CMS {reason, payload} envelope, and not the CMS PATCH, which
strips reviewer_status.
"""
import json, os, sys, time
import requests

SUBJ = None
if "--subject" in sys.argv:
    SUBJ = sys.argv[sys.argv.index("--subject") + 1]
EXECUTE = "--execute" in sys.argv

BASE = os.environ.get("CCP_API_BASE")
TOK = os.environ.get("CCP_ADMIN_JWT", "")
if not BASE or not TOK:
    sys.exit("error: set CCP_API_BASE and CCP_ADMIN_JWT")

EXAM = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
CMS = "/api/admin/exam-intelligence-cms"
INTEL = "/api/admin/exam-intelligence"

PREFIX = {"psir_p1": "PSIR-P1", "psir_p2": "PSIR-P2",
          "socio_p1": "SOCIO-P1", "socio_p2": "SOCIO-P2",
          "anth_p1": "ANTH-P1", "anth_p2": "ANTH-P2",
          "pubad_p1": "PUBAD-P1", "pubad_p2": "PUBAD-P2",
          "hist_p1": "HIST-P1", "hist_p2": "HIST-P2",
          "geog_p1": "GEOG-P1", "geog_p2": "GEOG-P2"}
if SUBJ and SUBJ not in PREFIX:
    sys.exit("unknown subject stem %r; one of %s" % (SUBJ, " ".join(sorted(PREFIX))))

# The route caps reviewer_notes at 500 chars and drops it server-side anyway
# (supports_notes=False); the full basis lives in the defects note.
REASON = (
    "Thematic corpus, pre-2011. De-duplicated at load against the source; one "
    "year per row; parser normalises the ligatures that corrupted the year-wise "
    "half. Carries a primary topic tag; paper anchored on a registered source "
    "document. NOT diffed against an official UPSC paper (unpublished before "
    "2016) and paper composition is not claimed."
)

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
        offset += len(items)
        if len(items) < 200:
            return out


print("finding thematic papers ...")
papers = [p for p in get_all(CMS + "/pyq-papers", {"exam_id": EXAM})
          if (p.get("metadata") or {}).get("corpus_half") == "thematic"]
print("thematic papers :", len(papers))

not_verified = [p for p in papers if p.get("trust_status") != "verified"]
if not_verified:
    print()
    print("WARNING: %d thematic paper(s) are not trust_status='verified'."
          % len(not_verified))
    print("score_snapshots counts questions only on verified papers, so "
          "reviewing these now still leaves them out of scoring.")
    print("Promote the papers first unless you mean to do this out of order.")
    print()

print("collecting questions ...")
todo = []
seen = 0
for p in papers:
    for q in get_all(CMS + "/pyq-questions", {"pyq_paper_id": p["id"]}):
        ref = q.get("source_question_ref") or ""
        if (q.get("metadata") or {}).get("corpus_half") != "thematic":
            continue
        if SUBJ and not ref.startswith(PREFIX[SUBJ] + "-"):
            continue
        seen += 1
        if q.get("reviewer_status") == "pending":
            todo.append((q["id"], ref))

scope = SUBJ or "all twelve subject-papers"
print()
print("scope            : %s" % scope)
print("questions found  : %d" % seen)
print("already reviewed : %d" % (seen - len(todo)))
print("to verify        : %d" % len(todo))

if not EXECUTE:
    print()
    print("DRY RUN. Re-run with --execute to promote.")
    sys.exit(0)

ok = fail = 0
errs = []
for i, (qid, ref) in enumerate(todo, 1):
    body = json.dumps({"reviewer_status": "verified", "reviewer_notes": REASON})
    try:
        r = s.patch(BASE + INTEL + "/items/pyq_question/%s/review" % qid,
                    data=body.encode("utf-8"), timeout=60)
        if r.status_code < 300:
            ok += 1
        else:
            fail += 1; errs.append((ref, r.status_code, r.text[:120]))
    except Exception as e:                        # noqa: BLE001
        fail += 1; errs.append((ref, "EXC", str(e)[:120])); time.sleep(3)
    if i % 200 == 0:
        print("  %d/%d  ok=%d fail=%d" % (i, len(todo), ok, fail))

print()
print("verified :", ok)
print("failed   :", fail)
for ref, code, msg in errs[:10]:
    print("  ", ref, code, msg)
if fail:
    print()
    print("Re-run - already-verified questions drop out of the work set.")
