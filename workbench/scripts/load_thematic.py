"""Load the pre-2011 thematic optional corpus into pyq_questions.

    python load_thematic.py <thematic_pre2011.json> [--papers] [--questions] [--execute]

WHAT THIS LOADS AND WHY IT LOOKS DIFFERENT

The compiler PDFs carry two halves. The year-wise half ("here is the 2019 PSIR
Paper-I, in order") produced the 4,038 questions already loaded. The topic-wise
half ("here is every question ever asked on Political Theory, with years") goes
back to 1980 and contains 4,273 questions that exist in no year-wise section.

Those 4,273 are what this loads. They are ordinary questions and go in
pyq_questions so that scoring, coverage, the explorer and the planner consume
them exactly like the others - that is the whole point of the shape chosen.

WHAT IS DELIBERATELY NOT CLAIMED

- `question_number` is NULL. The source gives no question numbers for these,
  and migration 224 indexes question_number `where not null`, so NULL is legal
  and means "unknown", not "zero".
- The paper rows carry `metadata.paper_reconstructed: false`. There was a 1991
  PSIR Paper-I, but this corpus does not know its composition or order - only
  that these questions were asked that year. The flag says so in the data
  rather than in a doc nobody reads.
- `source_question_ref` uses a T-prefix (PSIR-P1-1991-T003) so a thematic row
  is distinguishable from a year-wise one at a glance.

The 2011+ topic-wise rows are NOT loaded: they are the same questions as the
year-wise half, and loading them would count every topic twice in scoring.

DUPLICATES
Eight questions appear twice within one subject-paper-year because the
compiler indexed them under two topic headings. The first is loaded; the second
is skipped and written to a CSV with the headings it spanned, because "the
compiler saw this as two themes" is worth keeping.
"""
import csv, io, json, os, sys, time
from collections import defaultdict
import requests

if len(sys.argv) < 2:
    sys.exit(__doc__)
SRC = sys.argv[1]
DO_PAPERS = "--papers" in sys.argv
DO_QUESTIONS = "--questions" in sys.argv
EXECUTE = "--execute" in sys.argv
if not (DO_PAPERS or DO_QUESTIONS):
    DO_PAPERS = DO_QUESTIONS = True

BASE = os.environ.get("CCP_API_BASE")
TOK = os.environ.get("CCP_ADMIN_JWT", "")
if not BASE or not TOK:
    sys.exit("error: set CCP_API_BASE and CCP_ADMIN_JWT")

EXAM = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
PHASE = "626ec667-4bbf-4420-8715-48c5b83e0d11"
SOURCE = "87353d96-799f-417e-9670-bdfa844a6762"     # LotusArise optional source
DOCUMENT = "2836107c-880f-42d9-939b-eb5cfcdd0eb6"   # the registered bundle
CMS = "/api/admin/exam-intelligence-cms"

SUBJECT_NAME = {"psir": "Political Science and International Relations",
                "pubad": "Public Administration", "socio": "Sociology",
                "anth": "Anthropology", "hist": "History", "geog": "Geography"}
SLUG = {"psir": "psir", "pubad": "pubad", "socio": "sociology",
        "anth": "anthropology", "hist": "history", "geog": "geography"}
BLOCK = {("psir", 1): 100, ("psir", 2): 150, ("pubad", 1): 200, ("pubad", 2): 250,
         ("socio", 1): 300, ("socio", 2): 350, ("anth", 1): 400, ("anth", 2): 450,
         ("hist", 1): 500, ("hist", 2): 550, ("geog", 1): 600, ("geog", 2): 650}

s = requests.Session()
s.headers["Authorization"] = "Bearer " + TOK
s.headers["Content-Type"] = "application/json; charset=utf-8"


def post(path, payload, reason):
    body = json.dumps({"reason": reason, "payload": payload})
    return s.post(BASE + CMS + path, data=body.encode("utf-8"), timeout=60)


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


rows = json.load(io.open(SRC, encoding="utf-8"))

# ── sections, reused from the year-wise load ─────────────────────────────
print("resolving sections ...")
sections = {}
for sub in get_all("/subjects", {}):
    slug = sub.get("slug") or ""
    if not slug.startswith("upsc-cse-mains-opt-"):
        continue
    for sec in get_all("/exam-phase-sections", {"exam_phase_id": PHASE}):
        if sec.get("subject_id") == sub["id"]:
            stem = slug.replace("upsc-cse-mains-opt-", "")
            sections[stem] = sec["id"]
print("sections resolved :", len(sections))

# ── drop the eight cross-indexed duplicates ──────────────────────────────
seen, load, skipped = set(), [], []
for r in sorted(rows, key=lambda x: (x["year"], x["subj"], x["paper"], x["n"])):
    key = (r["subj"], r["paper"], r["year"], r["text"].lower())
    if key in seen:
        skipped.append(r)
        continue
    seen.add(key)
    load.append(r)
print("rows to load      :", len(load))
print("cross-indexed dupes skipped :", len(skipped))
if skipped:
    with io.open("thematic_skipped.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(skipped[0].keys()))
        w.writeheader(); w.writerows(skipped)
    print("  -> thematic_skipped.csv")

years = sorted({r["year"] for r in load})
print("paper rows needed :", len(years), f"({years[0]}-{years[-1]})")

if not EXECUTE:
    per = defaultdict(int)
    for r in load:
        per[r["year"]] += 1
    print()
    print("questions per year:")
    for y in years:
        print(f"  {y}: {per[y]}")
    print()
    print("DRY RUN. Add --execute to write.")
    sys.exit(0)

# ── 1. paper rows, one per year ──────────────────────────────────────────
papers = {}
if DO_PAPERS:
    print()
    print("creating paper rows ...")
    for y in years:
        payload = {
            "pyq_source_id": SOURCE,
            "exam_id": EXAM,
            "exam_phase_id": PHASE,
            "year": y,
            "paper_code": f"UPSC-CSE-MAINS-OPT-THEMATIC-{y}",
            "source_type": "aggregator",
            "source_document_id": DOCUMENT,
            "metadata": {
                "paper_kind": "optional",
                "corpus_half": "thematic",
                "paper_reconstructed": False,
                "note": ("Questions indexed by theme, not by paper. The source "
                         "records that these were asked in this year; it does "
                         "not record the paper's composition or question order. "
                         "question_number is NULL on every row for that reason."),
                "extraction_source": "LotusArise optional compilation, topic-wise half",
            },
        }
        r = post("/pyq-papers", payload,
                 f"thematic optional corpus {y}; paper composition not claimed")
        if r.status_code < 300:
            papers[y] = r.json()["row"]["id"]
            print(f"  ok {y} -> {papers[y]}")
        else:
            print(f"  FAIL {y}: {r.status_code} {r.text[:160]}")
    with io.open("thematic_papers.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["year", "paper_id"])
        for y, pid in sorted(papers.items()):
            w.writerow([y, pid])
    print("  -> thematic_papers.csv")
else:
    for row in csv.DictReader(io.open("thematic_papers.csv", encoding="utf-8-sig")):
        papers[int(row["year"])] = row["paper_id"]
    print("paper ids loaded from thematic_papers.csv :", len(papers))

# ── 2. questions ─────────────────────────────────────────────────────────
if DO_QUESTIONS:
    print()
    print("loading questions ...")
    # The CMS route is a plain INSERT: a duplicate idempotency_key returns
    # an unhandled 500, not a 409. Ask what is already loaded and skip it,
    # or a resume spends its whole run colliding with itself.
    print("  checking what is already loaded ...")
    have = set()
    for pid in papers.values():
        for q in get_all("/pyq-questions", {"pyq_paper_id": pid}):
            if q.get("source_question_ref"):
                have.add(q["source_question_ref"])
    before = len(load)
    load = [r for r in load if r["ref"] not in have]
    print(f"  already loaded {len(have)}; {len(load)} of {before} remain")

    ok = fail = 0
    errs = []
    ledger = []
    for i, r in enumerate(load, 1):
        pid = papers.get(r["year"])
        if not pid:
            fail += 1; errs.append((r["ref"], "no paper row")); continue
        payload = {
            "pyq_paper_id": pid,
            "section_id": sections[SLUG[r["subj"]]+f"-p{r['paper']}"],
            "question_text": r["text"],
            "question_type": "descriptive",
            "source_question_ref": r["ref"],
            "idempotency_key": f'thematic:{r["ref"]}',
            # question_number and display_order are deliberately omitted:
            # the source gives no ordering for these.
            "metadata": {
                "paper_kind": "optional",
                "corpus_half": "thematic",
                "optional_subject": SUBJECT_NAME[r["subj"]],
                "optional_paper_number": r["paper"],
                "topic_heading": r["heading"],
                "years_asked": [r["year"]],
                "year_source": r.get("year_source"),
                "source_list_index": r.get("idx"),
                "question_number_unknown": True,
                "extraction_source": "LotusArise optional compilation, topic-wise half",
                "verified_against_official": False,
            },
        }
        # Render drops long POST runs; a timeout must not end the load.
        try:
            resp = post("/pyq-questions", payload, "thematic optional corpus, pre-2011")
        except Exception as exc:
            fail += 1; errs.append((r["ref"], f"EXC {exc}"[:140]))
            time.sleep(3)
            continue
        if resp.status_code < 300:
            ok += 1
            # the question POST does not return the same envelope as the
            # paper POST - read the id defensively rather than assuming it
            try:
                d = resp.json()
                qid = (d.get("row") or d).get("id", "")
            except Exception:
                qid = ""
            ledger.append([r["ref"], r["year"], r["subj"], r["paper"], qid])
        else:
            fail += 1; errs.append((r["ref"], f"{resp.status_code} {resp.text[:120]}"))
        if i % 200 == 0:
            print(f"  {i}/{len(load)}  ok={ok} fail={fail}")
    with io.open("thematic_questions.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["ref", "year", "subject", "paper", "question_id"])
        w.writerows(ledger)
    print()
    print("loaded :", ok)
    print("failed :", fail)
    for ref, msg in errs[:12]:
        print("  ", ref, msg)
    print("  -> thematic_questions.csv")
    if fail:
        print()
        print("Re-run with --questions only; idempotency_key makes a repost safe.")
