"""Propose a draft assign_topic_id for each question in an optional worksheet.

    python propose_optional_tags.py <worksheet.csv> <topic_catalog.json> \
           <questions_<paper>.json> <out.csv>

    The worksheet's own text_preview column is TRUNCATED, so the full question
    text is joined in from the split export by row_id. Matching on a preview
    would systematically favour topics whose vocabulary happens to fall in the
    first few words.

WHAT THIS IS
    A first pass, not an answer. It scores each question's text against each
    microtopic's name and writes the best match into assign_topic_id, with the
    score and the runner-up alongside so a human can see how much to trust it.

WHAT IT IS NOT
    A tagger. Every row must be read. The score column exists so you can read
    the weak ones first, not so you can skip the strong ones - a confident
    match on shared vocabulary ("state", "power", "rights") is exactly where
    this is most likely to be confidently wrong.

HOW IT SCORES
    Token overlap weighted by inverse document frequency across the catalogue,
    so a question matching "Saptanga" counts far more than one matching "the".
    Proper nouns and rare terms therefore dominate, which is the behaviour you
    want for a syllabus whose microtopics are largely named thinkers, named
    institutions and named concepts.

OUTPUT COLUMNS ADDED
    assign_topic_id    best match, or blank when nothing clears the floor
    _match_score       0-1; below 0.15 the row is left blank rather than guessed
    _match_topic       the matched microtopic's text, for reading without a join
    _runner_up         second-best topic text
    _runner_score      its score - a close gap means the choice is not obvious

REVIEW ORDER THAT ACTUALLY WORKS
    1. blank assign_topic_id      - nothing matched, tag by hand
    2. _match_score < 0.30        - weak, usually wrong
    3. gap to _runner_up < 0.05   - two plausible topics, pick deliberately
    4. everything else            - still read it, but faster
"""
import csv, io, json, math, re, sys
from collections import Counter

if len(sys.argv) != 5:
    sys.exit(__doc__)
WORKSHEET, CATALOG, QUESTIONS, OUT = sys.argv[1:5]

STOP = set("""a an the of in on to for and or with by from as at is are was were be been
being this that these those it its into their his her our your not no nor but if then than
which who whom what how why when where do does did done can could shall should will would
may might must about over under between among during through against upon within without
discuss explain examine comment elucidate analyse analyze critically evaluate describe
write short notes note following words each what are how does give account bring out
significance role nature concept idea view views main features aspects context light
statement justify substantiate illustrate elaborate""".split())

def toks(t):
    t = re.sub(r"[^A-Za-z0-9\s]", " ", (t or "").lower())
    return [w for w in t.split() if len(w) > 2 and w not in STOP]

cat = json.load(io.open(CATALOG, encoding="utf-8"))
cat = cat["items"] if isinstance(cat, dict) and "items" in cat else cat
topics = [(c["id"], c.get("text") or c.get("slug") or c["id"]) for c in cat]
ttoks = [set(toks(t)) for _, t in topics]

# inverse document frequency over the catalogue
df = Counter()
for s in ttoks:
    for w in s:
        df[w] += 1
N = max(1, len(ttoks))
idf = {w: math.log(1 + N / (1 + c)) for w, c in df.items()}

def score(qset, tset):
    inter = qset & tset
    if not inter:
        return 0.0
    num = sum(idf.get(w, math.log(1 + N)) for w in inter)
    den = sum(idf.get(w, math.log(1 + N)) for w in tset) or 1.0
    return num / den

rows = list(csv.DictReader(io.open(WORKSHEET, encoding="utf-8-sig")))
if not rows:
    sys.exit("worksheet is empty")

qsrc = json.load(io.open(QUESTIONS, encoding="utf-8"))
qsrc = qsrc["items"] if isinstance(qsrc, dict) and "items" in qsrc else qsrc
FULL = {str(q.get("id")): (q.get("question_text") or "") for q in qsrc}

extra = ["_match_score", "_match_topic", "_runner_up", "_runner_score"]
fields = list(rows[0].keys()) + [c for c in extra if c not in rows[0]]

FLOOR = 0.15
filled = blank = weak = close = 0

for r in rows:
    # tag rows are left alone; question text is joined from the export, not
    # taken from the truncated text_preview column
    if (r.get("row_type") or "").strip().lower() != "question":
        for c in extra:
            r.setdefault(c, "")
        continue
    q = FULL.get((r.get("row_id") or "").strip(), "") or (r.get("text_preview") or "")
    if not q.strip():
        for c in extra:
            r.setdefault(c, "")
        continue
    qs = set(toks(q))
    scored = sorted(((score(qs, ts), tid, txt)
                     for ts, (tid, txt) in zip(ttoks, topics)), reverse=True)
    best, second = scored[0], (scored[1] if len(scored) > 1 else (0.0, "", ""))
    if best[0] >= FLOOR:
        r["assign_topic_id"] = best[1]
        r["_match_topic"] = best[2]
        filled += 1
        if best[0] < 0.30:
            weak += 1
        if best[0] - second[0] < 0.05:
            close += 1
    else:
        r["assign_topic_id"] = ""
        r["_match_topic"] = ""
        blank += 1
    r["_match_score"] = f"{best[0]:.3f}"
    r["_runner_up"] = second[2]
    r["_runner_score"] = f"{second[0]:.3f}"

with io.open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

total = filled + blank
print(f"rows with question text : {total}")
print(f"  proposed              : {filled}")
print(f"  left blank (no match) : {blank}")
print(f"  weak, score < 0.30    : {weak}")
print(f"  close call, gap < 0.05: {close}")
print()
print(f"wrote {OUT}")
print("Read the blanks first, then the weak, then the close calls.")
print("Delete the _ columns before `apply` - it validates the header.")
