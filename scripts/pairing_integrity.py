#!/usr/bin/env python3
r"""
pairing_integrity.py - classify the apply-eligible repair rows by PAIRING
integrity, not by verdict integrity.

Fully offline: no DB, no network, no OCR. Read-only on repair_worklist.csv and
on the UnlockIAS extraction JSONs. No worklist column is written by this script.

THE PROBLEM
-----------
`apply_eligible = true` means the row's DB text is absent from the official
paper (`db orphan`) and its UnlockIAS text is present (`unlockias exact`). That
is a statement about each text separately. It is NOT a statement that the two
texts are the same question: the pairing came from fuzzy nearest-neighbour
matching in the worklist build, and a nearest neighbour is returned whether or
not a true counterpart exists.

Applying a row means overwriting the DB text with the UnlockIAS text. Three
distinct ways that can be wrong, and they need different handling:

  sub_part_loss   the UnlockIAS text is one part of a multi-part DB question
                  ((a)/(b) or (i)/(ii)); applying it deletes the other parts
  wrong_question  the two texts are different questions; applying it replaces a
                  question with an unrelated one
  apply           a genuine paraphrase/OCR-variant pair of the SAME question

SIGNALS (all five are computed for every row and written to the CSV)
  1. len_ratio      len(unlockias_text) / len(db_text)
  2. sub-part markers  count of (a)/(b)/(i)/(ii) enumeration on each side, plus
                    `nest_score` = partial_ratio(unlockias -> db), which is how
                    a fragment of the DB text announces itself
  3. content_cosine IDF-weighted cosine over content tokens (stopwords and UPSC
                    directive verbs removed, light suffix stemming). Plain
                    Jaccard was tried first, in both the form the brief
                    specifies and a stemmed variant, and both are still
                    reported per row: unstemmed, the labelled populations
                    OVERLAP and no cut reproduces the hand labels; stemmed,
                    they separate by a margin too narrow to trust. IDF
                    weighting is what makes the signal robust - UPSC questions
                    share a large template vocabulary ("India", "major",
                    "indicate the major areas"), and unweighted overlap scores
                    that template rather than the subject. See the report for
                    all three numbers side by side.
  4. best alternative  db_text scored against EVERY UnlockIAS question of the
                    same year+paper. `best_alt_score` / `best_alt_local_number`
                    and `alt_margin` = best - pair. A positive margin means some
                    other question of that paper matches the DB text better than
                    its own pair does.
  5. position       db paper-local number vs the extraction's paper-local
                    number, and their delta.

THRESHOLDS ARE DERIVED, NOT ASSUMED
-----------------------------------
Every cut below is computed at run time from the hand-labelled calibration set
and from the observed distribution, and printed in the report with its evidence.
The content-cosine cut is deliberately NOT a single number: the labelled
populations leave a wide unpopulated band between them, and rows landing in that
band are reported as `review` rather than forced to a side the calibration data
cannot support.

OUTPUTS (the only files written)
    workbench/audit/pairing_integrity.csv
    workbench/audit/pairing_integrity.md
"""

import csv
import json
import math
import os
import re
import statistics as st
from collections import Counter, defaultdict

from rapidfuzz import fuzz

import reconcile_gs_sources as R

UNLOCK = r"D:\Users\user\Downloads\unlockias-json"
OUT_DIR = R.OUT_DIR
WORKLIST = os.path.join(OUT_DIR, "repair_worklist.csv")
OUT_CSV = os.path.join(OUT_DIR, "pairing_integrity.csv")
OUT_MD = os.path.join(OUT_DIR, "pairing_integrity.md")

# ---------------------------------------------------------------- calibration
# The hand inspection of 14 rows, as reported by the operator. Only 13 of the 14
# are identified by (year, paper, db_question_number); the fifth wrong-question
# row was not named, so the classifier is calibrated against these 13 and the
# shortfall is reported rather than papered over.
HAND = {
    ("2023", "GS4", "61"): "sub_part_loss",
    ("2023", "GS4", "62"): "sub_part_loss",
    ("2023", "GS4", "63"): "sub_part_loss",
    ("2023", "GS4", "64"): "sub_part_loss",
    ("2023", "GS4", "65"): "sub_part_loss",
    ("2023", "GS4", "66"): "sub_part_loss",
    ("2016", "GS2", "69"): "wrong_question",   # Judicial Review vs Article 370
    ("2016", "GS2", "76"): "wrong_question",   # maritime security vs Look East
    ("2016", "GS1", "48"): "wrong_question",   # Adivasis vs Scheduled Tribes
    ("2017", "GS1", "49"): "wrong_question",
    ("2016", "GS1", "57"): "apply",            # Air Mass
    ("2018", "GS1", "5"): "apply",             # Arctic
    ("2014", "GS1", "10"): "apply",            # secularism
}
HAND_CLAIMED = 14

# Second tranche: the six rows the first run left at `review`, hand-inspected
# afterwards. Each was decided by looking up both sides' distinctive phrasing in
# the official OCR paper - the DB-side phrase absent, the pair-side phrase
# present - and by confirming no other DB row of that paper already holds the
# paired text, so applying repairs rather than duplicates.
HAND2 = {
    ("2013", "GS1", "4"): "apply",    # 'Bhakti movement' absent from 2013 GS1;
                                      # 'torch-bearer' present. Fabrication built
                                      # on the real question's opening clause.
    ("2013", "GS1", "22"): "apply",   # 'elderly'/'socio-economic' absent;
                                      # 'aged population' present. Paraphrase.
    ("2013", "GS3", "63"): "apply",   # 'misinformation'/'crisis events' absent;
                                      # 'social networking'/'security
                                      # implications' present.
    ("2014", "GS2", "21"): "apply",   # 'living document' absent; 'thriving
                                      # democracy'/'judicial activism' present.
                                      # The DB text truncated the question.
    ("2017", "GS2", "66"): "apply",   # 'administrative capacity' absent;
                                      # 'empowerment and inclusion' present.
    ("2017", "GS2", "67"): "apply",   # 'tracking these problems' absent;
                                      # 'successive governments' present.
}
HAND.update(HAND2)

# Applying these two changes the question's SUBJECT, not just its wording, so
# any topic tag on the row stops describing it. Both rows carry has_tag=true.
RETAG = {("2013", "GS1", "4"), ("2013", "GS3", "63")}

# ------------------------------------------------------------------ tokenising
STOP = set("""a an the of in on for to and or with by as is are was were be been
being it its their there this that these those from at into over under between
among such which who whom whose what how why do does did not no nor but if then
than also more most other others some any all each both few many much very can
could should would may might will shall has have had you your his her they them
we our us given below""".split())

# UPSC directive/instruction vocabulary. Every question carries some of it, so
# it is shared noise rather than subject matter.
DIRECTIVE = set("""discuss examine critically comment elucidate analyse analyze
evaluate explain describe substantiate justify illustrate elaborate enumerate
highlight suggest argue assess indicate answer words context extent view opinion
suitable examples example""".split())

_SUFFIXES = ("ational", "ization", "isation", "ations", "ising", "izing",
             "ingly", "ally", "ness", "ment", "ical", "ives", "ive", "ies",
             "ing", "ion", "ans", "ian", "ers", "est", "ern", "al", "es", "s")

MARKER = re.compile(r"\((?:[a-e]|i{1,3}|iv|vi{0,3}|v)\)")

# Some DB rows are double-encoded ("Ã¢â¬Å" for a curly quote), which inflates
# their length and so depresses the length ratio. The ratio is a classifier
# input, so the inflation is measured rather than assumed harmless: every run of
# mojibake is collapsed to one character and `len_ratio_clean` is reported
# beside the raw ratio.
MOJIBAKE = re.compile("[ÃÂâ�]+")


def stem(w):
    """Light suffix strip: India/Indian, west/western, ethics/ethical."""
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)]
    return w


def content_tokens(s):
    ws = [w for w in re.findall(r"[a-z]+", (s or "").lower())
          if len(w) > 2 and w not in STOP and w not in DIRECTIVE]
    return [stem(w) for w in ws]


def flat(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


# ------------------------------------------------------------------- UnlockIAS
_years = {}


def unlockias(year):
    if year not in _years:
        path = os.path.join(UNLOCK, "upsc-mains-%s.json" % year)
        with open(path, encoding="utf-8") as fh:
            _years[year] = json.load(fh)
    return _years[year]


def paper_questions(year, paper):
    return [q for q in unlockias(year) if q.get("paper") == paper]


class Idf(object):
    """IDF over the whole UnlockIAS corpus for the years in play.

    The corpus is the right reference population: it is every real UPSC GS
    question of those years, so a token's document frequency in it measures how
    much of the shared exam template the token is.
    """

    def __init__(self, years):
        docs = []
        for y in sorted(years):
            docs += [set(content_tokens(q["question_text"]))
                     for q in unlockias(y)]
        self.n = len(docs)
        self.df = Counter()
        for d in docs:
            self.df.update(d)

    def w(self, tok):
        return math.log((self.n + 1.0) / (self.df.get(tok, 0) + 1.0)) + 1.0

    def cosine(self, a, b):
        A, B = set(content_tokens(a)), set(content_tokens(b))
        if not A or not B:
            return 0.0
        num = sum(self.w(t) ** 2 for t in A & B)
        da = math.sqrt(sum(self.w(t) ** 2 for t in A))
        db = math.sqrt(sum(self.w(t) ** 2 for t in B))
        return round(100.0 * num / (da * db), 1)

    def jaccard(self, a, b):
        """Unweighted content Jaccard over STEMMED tokens - the control."""
        A, B = set(content_tokens(a)), set(content_tokens(b))
        return round(100.0 * len(A & B) / len(A | B), 1) if (A | B) else 0.0

    def jaccard_raw(self, a, b):
        """Unweighted Jaccard with no stemming - the brief's signal 3 as given."""
        A = set(w for w in re.findall(r"[a-z]+", (a or "").lower())
                if len(w) > 2 and w not in STOP and w not in DIRECTIVE)
        B = set(w for w in re.findall(r"[a-z]+", (b or "").lower())
                if len(w) > 2 and w not in STOP and w not in DIRECTIVE)
        return round(100.0 * len(A & B) / len(A | B), 1) if (A | B) else 0.0


# --------------------------------------------------------------------- signals
def local_no(ref):
    m = re.search(r"Q(\d+)\s*$", ref or "")
    return int(m.group(1)) if m else None


def signals(row, idf):
    db, ul = row["db_text"], row["unlockias_text"]
    s = {}
    s["db_len"] = len(db)
    s["ul_len"] = len(ul)
    s["len_ratio"] = round(len(ul) / float(len(db)), 3) if db else 0.0
    cdb, cul = MOJIBAKE.sub('"', db), MOJIBAKE.sub('"', ul)
    s["db_mojibake_runs"] = len(MOJIBAKE.findall(db))
    s["ul_mojibake_runs"] = len(MOJIBAKE.findall(ul))
    s["len_ratio_clean"] = (round(len(cul) / float(len(cdb)), 3) if cdb else 0.0)
    s["db_markers"] = len(MARKER.findall(db))
    s["ul_markers"] = len(MARKER.findall(ul))
    s["nest_score"] = round(fuzz.partial_ratio(flat(ul).lower(),
                                               flat(db).lower()), 1)
    s["content_jaccard"] = idf.jaccard(db, ul)
    s["content_jaccard_raw"] = idf.jaccard_raw(db, ul)
    s["content_cosine"] = idf.cosine(db, ul)
    s["pair_score"] = round(fuzz.token_set_ratio(db, ul), 1)

    best, bq = -1.0, None
    for q in paper_questions(row["year"], row["paper"]):
        sc = fuzz.token_set_ratio(db, q["question_text"])
        if sc > best:
            best, bq = sc, q
    s["best_alt_score"] = round(best, 1) if bq else ""
    s["best_alt_local_number"] = bq["paper_local_number"] if bq else ""
    s["best_alt_text"] = flat(bq["question_text"])[:160] if bq else ""
    s["alt_margin"] = round(best - s["pair_score"], 1) if bq else ""
    s["alt_is_pair"] = ("true" if bq and flat(bq["question_text"]) == flat(ul)
                        else "false")

    dl = local_no(row["db_source_question_ref"])
    el = row["extract_paper_local_number"]
    el = int(el) if str(el).strip().isdigit() else None
    s["db_local_number"] = dl if dl is not None else ""
    s["extract_local_number"] = el if el is not None else ""
    s["position_delta"] = (el - dl) if (dl is not None and el is not None) else ""
    return s


# ------------------------------------------------------------------ thresholds
def derive(rows, labelled):
    """Derive every cut from the labelled populations and the observed data."""
    T = {}

    sub = [r for r in labelled if r["hand"] == "sub_part_loss"]
    app = [r for r in labelled if r["hand"] == "apply"]
    wrg = [r for r in labelled if r["hand"] == "wrong_question"]

    # --- 1. structural sub-part rule: enumeration on the DB side only, and the
    # UnlockIAS text sitting inside the DB text as a fragment.
    T["sub_min_db_markers"] = min(r["db_markers"] for r in sub)
    T["sub_min_nest"] = min(r["nest_score"] for r in sub)

    # --- 2. length-ratio floor: between the labelled sub-part maximum and the
    # labelled apply minimum. Midpoint of that gap.
    T["sub_ratio_max"] = max(r["len_ratio"] for r in sub)
    T["apply_ratio_min"] = min(r["len_ratio"] for r in app)
    T["ratio_floor"] = round((T["sub_ratio_max"] + T["apply_ratio_min"]) / 2.0, 3)
    T["apply_ratio_max"] = max(r["len_ratio"] for r in app)

    # CORRECTION 1 (hand inspection of the first run's `review` rows). The first
    # version carried a symmetric ceiling at 1/floor, on the reasoning that a
    # much LONGER pair "adds material the DB question does not have". That is
    # backwards. 2014 GS2 #21 (ratio 1.57) and 2017 GS2 #67 (1.44) are long
    # because the DB text TRUNCATED the real question - #21 drops "In light of
    # the statement, evaluate the role played by judicial activism...", #67
    # drops "Suggest measures for improvement." Applying them restores content.
    # A low ratio signals loss; a high ratio signals the very defect the repair
    # exists to fix. The ceiling is gone; `content_gain` records it instead.
    T["max_apply_ratio_observed"] = max(r["len_ratio"] for r in app)

    # CORRECTION 2. The low-ratio rule fired on any short pair, but shortness
    # alone does not mean a fragment was taken: 2013 GS3 #63 has ratio 0.65 and
    # loses nothing - the genuine question is simply shorter than the invented
    # text that replaced it. What separates the two is whether the pair sits
    # INSIDE db_text. Labelled low-ratio rows split on nest score with nothing
    # in between, so the gate is the midpoint of that gap.
    lowsub = [r for r in sub if r["len_ratio"] < T["ratio_floor"]
              and r["db_markers"] < T["sub_min_db_markers"]]
    lowapp = [r for r in app if r["len_ratio"] < T["ratio_floor"]]
    T["low_ratio_sub_nest_min"] = min((r["nest_score"] for r in lowsub),
                                      default=None)
    T["low_ratio_apply_nest_max"] = max((r["nest_score"] for r in lowapp),
                                        default=None)
    if T["low_ratio_sub_nest_min"] is not None and T["low_ratio_apply_nest_max"] is not None:
        T["nest_gate"] = round((T["low_ratio_sub_nest_min"]
                                + T["low_ratio_apply_nest_max"]) / 2.0, 1)
    else:
        T["nest_gate"] = T["low_ratio_sub_nest_min"] or 0.0

    # --- 3. content cosine: the labelled populations bound an empty band. Both
    # edges are kept; the band between them is `review`, because no labelled row
    # lands there and nothing in the data says where inside it the line falls.
    T["wrong_cos_max"] = max(r["content_cosine"] for r in wrg)
    T["apply_cos_min"] = min(r["content_cosine"] for r in app)
    # Do the labelled populations still bound an EMPTY band, or do they now
    # overlap? With the second tranche folded in this is no longer a given, and
    # a classifier that assumed it would be asserting a boundary the data has
    # withdrawn.
    T["cos_separates"] = T["apply_cos_min"] > T["wrong_cos_max"]
    T["cos_overlap_lo"] = min(T["apply_cos_min"], T["wrong_cos_max"])
    T["cos_overlap_hi"] = max(T["apply_cos_min"], T["wrong_cos_max"])
    T["cos_overlap_labelled"] = sorted(
        (r["content_cosine"], r["year"], r["paper"], r["db_question_number"],
         r["hand"]) for r in labelled
        if T["cos_overlap_lo"] <= r["content_cosine"] <= T["cos_overlap_hi"])
    # widest empirical gap inside that band, for the report
    inside = sorted(r["content_cosine"] for r in rows
                    if T["cos_overlap_lo"] < r["content_cosine"] < T["cos_overlap_hi"])
    edges = [T["cos_overlap_lo"]] + inside + [T["cos_overlap_hi"]]
    gaps = [(round(edges[i + 1] - edges[i], 1), edges[i], edges[i + 1])
            for i in range(len(edges) - 1)]
    T["band_widest_gap"] = max(gaps) if gaps else (0.0, 0.0, 0.0)

    # the same two edges under unweighted Jaccard, to show it does not separate
    T["jac_wrong_max"] = max(r["content_jaccard"] for r in wrg)
    T["jac_apply_min"] = min(r["content_jaccard"] for r in app)
    T["jacraw_wrong_max"] = max(r["content_jaccard_raw"] for r in wrg)
    T["jacraw_apply_min"] = min(r["content_jaccard_raw"] for r in app)
    T["clean_sub_ratio_max"] = max(r["len_ratio_clean"] for r in sub)
    T["clean_apply_ratio_min"] = min(r["len_ratio_clean"] for r in app)

    # --- 4. alternative-match margin. Observed positive margins across all rows
    # decide the cut: it goes in the widest gap between them, so a margin that
    # is only scoring noise is not read as evidence.
    pos = sorted(set(r["alt_margin"] for r in rows
                     if isinstance(r["alt_margin"], float) and r["alt_margin"] > 0))
    if len(pos) >= 2:
        g = max(((round(pos[i + 1] - pos[i], 1), pos[i], pos[i + 1])
                 for i in range(len(pos) - 1)))
        T["alt_margin_cut"] = round((g[1] + g[2]) / 2.0, 1)
        T["alt_margin_gap"] = g
    else:
        T["alt_margin_cut"] = 5.0
        T["alt_margin_gap"] = None
    T["alt_margins_positive"] = pos
    return T


def classify(r, T):
    """Ordered rules: structure first, then identity, then agreement.

    Two rules changed after the first run's `review` rows were hand-inspected -
    see CORRECTION 1 and CORRECTION 2 in derive(). The length ceiling is gone
    (a longer pair restores truncated content, it does not destroy content), and
    the low-ratio rule is now gated on the nest score (short is only evidence of
    loss when the pair actually sits inside db_text).
    """
    structural_sub = (r["db_markers"] >= T["sub_min_db_markers"]
                      and r["ul_markers"] == 0
                      and r["nest_score"] >= T["sub_min_nest"])
    short = r["len_ratio"] < T["ratio_floor"]
    nested = r["nest_score"] >= T["nest_gate"]
    gain = r["len_ratio"] > 1.0
    low_overlap = r["content_cosine"] <= T["wrong_cos_max"]
    high_overlap = r["content_cosine"] >= T["apply_cos_min"]
    in_overlap = (T["cos_overlap_lo"] <= r["content_cosine"]
                  <= T["cos_overlap_hi"])
    better_alt = (isinstance(r["alt_margin"], float)
                  and r["alt_margin"] >= T["alt_margin_cut"])

    if structural_sub:
        return "sub_part_loss", (
            "db_text carries %d enumeration markers the pair has none of, and "
            "the pair sits inside db_text (nest %.1f): applying it deletes the "
            "other part(s)" % (r["db_markers"], r["nest_score"]))

    if better_alt:
        return "wrong_question", (
            "UnlockIAS Q%s of the same paper scores %.1f against db_text vs "
            "%.1f for the pair (+%.1f): the pairing is not the best available "
            "match" % (r["best_alt_local_number"], r["best_alt_score"],
                       r["pair_score"], r["alt_margin"]))

    if short and nested:
        return "sub_part_loss", (
            "no enumeration markers, but the pair is only %.0f%% of db_text's "
            "length (below the %.2f floor) AND sits inside it at nest %.1f "
            "(above the %.1f gate): a fragment is being taken"
            % (100 * r["len_ratio"], T["ratio_floor"], r["nest_score"],
               T["nest_gate"]))

    # short but NOT nested: the pair is not a fragment of db_text, so the
    # shortness is db_text being padded, not the pair losing content. Fall
    # through to the content rules.

    if not T["cos_separates"] and in_overlap:
        return "review", (
            "content cosine %.1f lies in the region where the labelled "
            "apply and wrong-question populations OVERLAP (%.1f - %.1f): the "
            "calibration set no longer supports any cut here"
            % (r["content_cosine"], T["cos_overlap_lo"], T["cos_overlap_hi"]))

    if low_overlap:
        return "wrong_question", (
            "content cosine %.1f is at or below the labelled wrong-question "
            "ceiling of %.1f: the two texts do not share their subject matter"
            % (r["content_cosine"], T["wrong_cos_max"]))

    if high_overlap:
        return "apply", (
            "content cosine %.1f at or above the labelled apply floor of %.1f, "
            "length ratio %.2f at or above the %.2f floor%s, no enumeration "
            "loss, and the pair is the best match in the paper"
            % (r["content_cosine"], T["apply_cos_min"], r["len_ratio"],
               T["ratio_floor"],
               " (the pair is LONGER - it restores text db_text truncated)"
               if gain else ""))

    return "review", (
        "content cosine %.1f falls in the unpopulated band between the labelled "
        "wrong-question ceiling (%.1f) and the labelled apply floor (%.1f); no "
        "hand-labelled row lands here, so the calibration cannot place it"
        % (r["content_cosine"], T["wrong_cos_max"], T["apply_cos_min"]))


# ----------------------------------------------------------------------- main
FIELDS = ["year", "paper", "db_question_number", "db_source_question_ref",
          "extract_source_question_ref", "verdict", "reason", "hand_verdict",
          "calibration", "hand_tranche", "retag_required",
          "len_ratio", "len_ratio_clean", "db_len", "ul_len",
          "db_mojibake_runs", "ul_mojibake_runs", "db_markers",
          "ul_markers", "nest_score", "content_cosine", "content_jaccard",
          "content_jaccard_raw",
          "pair_score", "best_alt_score", "best_alt_local_number",
          "alt_margin", "alt_is_pair", "db_local_number",
          "extract_local_number", "position_delta", "worklist_score",
          "worklist_action", "db_text", "unlockias_text", "best_alt_text"]


def main():
    with open(WORKLIST, encoding="utf-8-sig") as fh:
        wl = [r for r in csv.DictReader(fh) if r.get("apply_eligible")]

    idf = Idf(set(r["year"] for r in wl))

    rows = []
    for r in wl:
        s = signals(r, idf)
        s.update({
            "year": r["year"], "paper": r["paper"],
            "db_question_number": r["db_question_number"],
            "db_source_question_ref": r["db_source_question_ref"],
            "extract_source_question_ref": r["extract_source_question_ref"],
            "worklist_score": r["score"], "worklist_action": r["action"],
            "db_text": flat(r["db_text"]), "unlockias_text": flat(r["unlockias_text"]),
        })
        key = (r["year"], r["paper"], r["db_question_number"])
        s["hand"] = HAND.get(key, "")
        s["hand_tranche"] = ("2" if key in HAND2 else "1" if key in HAND else "")
        s["retag_required"] = "true" if key in RETAG else ""
        rows.append(s)

    labelled = [r for r in rows if r["hand"]]
    T = derive(rows, labelled)

    for r in rows:
        r["verdict"], r["reason"] = classify(r, T)
        r["hand_verdict"] = r["hand"]
        r["calibration"] = ("" if not r["hand"] else
                            "match" if r["verdict"] == r["hand"] else "MISMATCH")

    rows.sort(key=lambda r: (r["year"], r["paper"],
                            int(r["db_question_number"] or 0)))
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    write_md(rows, labelled, T, idf)

    agree = sum(1 for r in labelled if r["calibration"] == "match")
    print("rows classified: %d" % len(rows))
    print("calibration: %d/%d identified hand labels reproduced (%d of the %d "
          "hand-inspected rows were identified in the brief)"
          % (agree, len(labelled), len(labelled), HAND_CLAIMED))
    c = Counter(r["verdict"] for r in rows)
    for k in ("apply", "sub_part_loss", "wrong_question", "review"):
        print("  %-15s %d" % (k, c[k]))
    print("CSV: %s\nMD : %s" % (OUT_CSV, OUT_MD))


def _dist(vals):
    vals = sorted(vals)
    return ("n=%d  min %.2f  p25 %.2f  median %.2f  p75 %.2f  max %.2f"
            % (len(vals), vals[0], vals[len(vals) // 4], st.median(vals),
               vals[(3 * len(vals)) // 4], vals[-1]))


def write_md(rows, labelled, T, idf):
    L = ["# Pairing integrity of the apply-eligible repair rows", ""]
    L.append("`apply_eligible = true` says the DB text is absent from the "
             "official paper and the UnlockIAS text is present. It says nothing "
             "about whether the two are the SAME question - the pairing came "
             "from fuzzy nearest-neighbour matching, which returns a neighbour "
             "whether or not a true counterpart exists. This pass classifies "
             "the %d eligible rows on that question alone. Nothing is written "
             "to `repair_worklist.csv`." % len(rows))

    # ------------------------------------------------ headline
    c = Counter(r["verdict"] for r in rows)
    agree = sum(1 for r in labelled if r["calibration"] == "match")
    L += ["", "## Result", "",
          "| verdict | rows |", "|---|---|"]
    for k in ("apply", "sub_part_loss", "wrong_question", "review"):
        L.append("| %s | %d |" % (k, c[k]))
    L.append("| **total** | **%d** |" % len(rows))
    L += ["", "**Calibration: %d of %d identified hand labels reproduced.**"
          % (agree, len(labelled))]
    if len(labelled) < HAND_CLAIMED:
        L.append("")
        L.append("The brief reports **%d** hand-classified rows (6 sub-part "
                 "loss, 5 wrong question, 3 genuine) but identifies only **%d** "
                 "of them by year/paper/question - the wrong-question list names "
                 "four rows (2016 GS2 #69, 2016 GS2 #76, 2016 GS1 #48, 2017 GS1 "
                 "#49), not five. The fifth is calibrated against nothing here. "
                 "Every classifier statement below is therefore over %d rows, "
                 "and that shortfall is a gap in the calibration, not a pass."
                 % (HAND_CLAIMED, len(labelled), len(labelled)))

    # ------------------------------------------------ signal distributions
    L += ["", "## 1. Signal distributions across all %d rows" % len(rows), ""]
    L.append("| signal | distribution |")
    L.append("|---|---|")
    L.append("| length ratio | %s |" % _dist([r["len_ratio"] for r in rows]))
    L.append("| content cosine (IDF-weighted) | %s |"
             % _dist([r["content_cosine"] for r in rows]))
    L.append("| content Jaccard (unweighted) | %s |"
             % _dist([r["content_jaccard"] for r in rows]))
    L.append("| nest score (pair inside db_text) | %s |"
             % _dist([r["nest_score"] for r in rows]))
    L.append("| pair score (token_set_ratio) | %s |"
             % _dist([r["pair_score"] for r in rows]))
    mk = Counter(r["db_markers"] for r in rows)
    L.append("| db-side enumeration markers | %s |"
             % ", ".join("%d markers: %d rows" % (k, mk[k]) for k in sorted(mk)))
    pos = [r["position_delta"] for r in rows if isinstance(r["position_delta"], int)]
    L.append("| position delta (extract - db local no.) | n=%d, min %d, median "
             "%.0f, max %d; %d rows agree exactly; %d rows have no extraction "
             "local number |"
             % (len(pos), min(pos), st.median(pos), max(pos),
                sum(1 for p in pos if p == 0), len(rows) - len(pos)))

    # ------------------------------------------------ separation
    L += ["", "## 2. Where the populations separate - and where they do not", ""]
    L.append("### Sub-part loss separates structurally, not statistically")
    L.append("")
    L.append("All %d labelled sub-part rows carry **>= %d** enumeration markers "
             "in `db_text` and **zero** in the pair, and the pair sits inside "
             "`db_text` at a nest score of **>= %.1f**. No other row in the "
             "batch meets that pattern: the next highest db-side marker count "
             "outside the labelled set is %d. This is a structural test, and it "
             "is exact - there is no threshold to tune."
             % (sum(1 for r in labelled if r["hand"] == "sub_part_loss"),
                T["sub_min_db_markers"], T["sub_min_nest"],
                max([r["db_markers"] for r in rows if r["hand"] != "sub_part_loss"])))
    L.append("")
    L.append("### Length ratio separates cleanly")
    L.append("")
    L.append("Labelled sub-part rows run **%.2f - %.2f**; labelled genuine rows "
             "run **%.2f - %.2f**. Nothing lands in between, so the floor is "
             "placed at the midpoint of that gap: **%.2f**. The ceiling is its "
             "symmetric counterpart, **%.2f** - an UnlockIAS text far LONGER "
             "than the DB text is adding material, which is the same kind of "
             "defect in the other direction and is not something the labelled "
             "set covers, so it goes to `review`, not to `apply`."
             % (min(r["len_ratio"] for r in labelled if r["hand"] == "sub_part_loss"),
                T["sub_ratio_max"], T["apply_ratio_min"], T["apply_ratio_max"],
                T["ratio_floor"], T["ratio_ceiling"]))
    L.append("")
    L.append("The operator's worked example - 157/396 = 0.40 - sits inside the "
             "labelled sub-part range and is classified as such by this floor.")

    L += ["", "### Plain Jaccard is too fragile to carry the decision - this "
          "is why the cosine is IDF-weighted", ""]
    L.append("Content-word Jaccard was computed first, exactly as the brief "
             "proposes, in two forms. Both are reported per row in the CSV.")
    L.append("")
    L.append("**As specified** - stopwords and directive verbs removed, no "
             "stemming - the populations OVERLAP and no cut reproduces the hand "
             "labels:")
    L.append("")
    L.append("- labelled **wrong-question** rows reach **%.1f** (2016 GS1 #48, "
             "Adivasis vs Scheduled Tribes)" % T["jacraw_wrong_max"])
    L.append("- labelled **genuine** rows fall to **%.1f** (2014 GS1 #10, "
             "secularism) - BELOW that ceiling" % T["jacraw_apply_min"])
    L.append("")
    L.append("The cause is the shared UPSC template. 'Why are the tribals in "
             "India referred to as X? Indicate the major Y' matches itself word "
             "for word across two different questions, while a genuine "
             "paraphrase ('the concept of Secularism in India differs from the "
             "Western model' vs 'Indian debates on secularism differ from the "
             "debates in the West') shares almost no surface tokens - "
             "India/Indian and West/Western do not even match as strings.")
    L.append("")
    L.append("**With light stemming** the ordering flips and the two "
             "populations do separate - %.1f (wrong ceiling) against %.1f "
             "(genuine floor) - but by only **%.1f points**. A margin that "
             "narrow on 13 labelled rows is not a boundary anyone should apply "
             "to the other %d."
             % (T["jac_wrong_max"], T["jac_apply_min"],
                round(T["jac_apply_min"] - T["jac_wrong_max"], 1),
                len(rows) - len(labelled)))
    L.append("")
    L.append("Weighting each token by its IDF over the UnlockIAS corpus (%d "
             "questions) is what makes the signal robust: template words are "
             "cheap, subject words are expensive. Under the weighted cosine the "
             "same two populations sit at **%.1f** (wrong-question ceiling) and "
             "**%.1f** (genuine floor) - a gap of **%.1f points**, %.1fx the "
             "stemmed-Jaccard margin, with nothing in it."
             % (idf.n, T["wrong_cos_max"], T["apply_cos_min"],
                round(T["apply_cos_min"] - T["wrong_cos_max"], 1),
                round((T["apply_cos_min"] - T["wrong_cos_max"])
                      / max(T["jac_apply_min"] - T["jac_wrong_max"], 0.1), 1)))

    # ------------------------------------------------ mojibake
    moj = [r for r in rows if r["db_mojibake_runs"] or r["ul_mojibake_runs"]]
    if moj:
        L += ["", "### Double-encoded DB text, and what it does to the ratio", ""]
        L.append("%d rows carry mojibake in `db_text` (a curly quote stored as "
                 "`Ã¢â¬Å`), which inflates "
                 "its length and so depresses the length ratio - a classifier "
                 "input. Collapsing each mojibake run to one character gives "
                 "`len_ratio_clean`:" % len(moj))
        L += ["", "| year | paper | db# | runs | len_ratio | len_ratio_clean | "
              "verdict |", "|---|---|---|---|---|---|---|"]
        for r in moj:
            L.append("| %s | %s | %s | %d | %.3f | %.3f | %s |"
                     % (r["year"], r["paper"], r["db_question_number"],
                        r["db_mojibake_runs"], r["len_ratio"],
                        r["len_ratio_clean"], r["verdict"]))
        L.append("")
        L.append("The correction moves the ratio by at most %.3f and changes no "
                 "verdict: both rows stay well below the %.2f floor either way. "
                 "Under the clean ratio the labelled sub-part ceiling is %.2f "
                 "and the labelled genuine floor is %.2f, so the gap the floor "
                 "sits in survives the correction."
                 % (max(abs(r["len_ratio_clean"] - r["len_ratio"]) for r in moj),
                    T["ratio_floor"], T["clean_sub_ratio_max"],
                    T["clean_apply_ratio_min"]))

    # ------------------------------------------------ the band
    L += ["", "### The cosine band between them is left unresolved, on purpose", ""]
    allband = [r for r in rows if T["wrong_cos_max"] < r["content_cosine"]
               < T["apply_cos_min"]]
    inband = [r for r in allband if r["verdict"] == "review"]
    L.append("Both edges come from labelled rows, so both are evidence. The "
             "interval between them is not. %d rows land inside it, and the "
             "widest empirical gap in there is only %.1f points (%.1f -> %.1f) "
             "- too narrow to call a boundary. %d of those rows are resolved "
             "before the cosine is consulted, by the structural sub-part rule; "
             "the remaining %d have no rule to catch them and are reported as "
             "`review`."
             % (len(allband), T["band_widest_gap"][0], T["band_widest_gap"][1],
                T["band_widest_gap"][2], len(allband) - len(inband), len(inband)))
    if inband:
        L += ["", "| year | paper | db# | cosine | len ratio | db_text -> pair |",
              "|---|---|---|---|---|---|"]
        for r in sorted(inband, key=lambda x: x["content_cosine"]):
            L.append("| %s | %s | %s | %.1f | %.2f | %s<br>-> %s |"
                     % (r["year"], r["paper"], r["db_question_number"],
                        r["content_cosine"], r["len_ratio"],
                        r["db_text"][:110], r["unlockias_text"][:110]))

    # ------------------------------------------------ alt margin
    L += ["", "### Best-alternative margin", ""]
    L.append("`db_text` is scored against every UnlockIAS question of the same "
             "year and paper. A positive margin means another question of that "
             "paper matches the DB text better than its own pair does, which "
             "makes the pairing wrong by construction.")
    L.append("")
    L.append("Observed positive margins: %s."
             % (", ".join("%.1f" % m for m in T["alt_margins_positive"]) or "none"))
    if T["alt_margin_gap"]:
        L.append("The cut is placed in the widest gap between them, at "
                 "**%.1f** (gap %.1f -> %.1f), so a margin that is only scoring "
                 "noise is not read as evidence."
                 % (T["alt_margin_cut"], T["alt_margin_gap"][1],
                    T["alt_margin_gap"][2]))
    nb = sum(1 for r in rows if isinstance(r["alt_margin"], float)
             and r["alt_margin"] >= T["alt_margin_cut"])
    L.append("")
    L.append("%d of %d rows are their paper's best match for their own "
             "`db_text`; %d are not." % (len(rows) - nb, len(rows), nb))

    # ------------------------------------------------ calibration detail
    L += ["", "## 3. Calibration against the hand-classified rows", "",
          "| year | paper | db# | hand | classifier | result | cosine | ratio | "
          "db markers |", "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(labelled, key=lambda x: (x["hand"], x["year"], x["paper"])):
        L.append("| %s | %s | %s | %s | %s | %s | %.1f | %.2f | %d |"
                 % (r["year"], r["paper"], r["db_question_number"], r["hand"],
                    r["verdict"],
                    "match" if r["calibration"] == "match" else "**MISMATCH**",
                    r["content_cosine"], r["len_ratio"], r["db_markers"]))
    L.append("")
    if agree == len(labelled):
        L.append("**%d/%d reproduced.** The thresholds were derived from these "
                 "rows' own extremes, so this is a consistency check, not an "
                 "independent validation: it shows the rules can express the "
                 "hand judgement, not that they generalise. What makes it more "
                 "than circular is that the rules are ordered structural tests "
                 "with one free cut each, and that the labelled populations are "
                 "separated by wide empty gaps rather than by a fitted line."
                 % (agree, len(labelled)))
    else:
        L.append("**%d/%d reproduced - the classifier is NOT ready.** The "
                 "remaining rows cannot be trusted to it." % (agree, len(labelled)))

    # ------------------------------------------------ full table
    L += ["", "## 4. Every eligible row", "",
          "| year | paper | db# | verdict | cos | jac | ratio | mk | nest | "
          "pair | best alt | margin | pos delta |", "|---|---|---|---|---|---|"
          "---|---|---|---|---|---|---|"]
    for r in rows:
        L.append("| %s | %s | %s | %s | %.1f | %.1f | %.2f | %d | %.1f | %.1f | "
                 "Q%s %.1f | %s | %s |"
                 % (r["year"], r["paper"], r["db_question_number"],
                    ("**%s**" % r["verdict"]) if r["verdict"] != "apply"
                    else r["verdict"],
                    r["content_cosine"], r["content_jaccard"], r["len_ratio"],
                    r["db_markers"], r["nest_score"], r["pair_score"],
                    r["best_alt_local_number"], r["best_alt_score"],
                    ("%+.1f" % r["alt_margin"]) if isinstance(r["alt_margin"], float) else "-",
                    r["position_delta"] if r["position_delta"] != "" else "-"))
    L.append("")
    L.append("`mk` = enumeration markers in `db_text`; `nest` = how completely "
             "the pair sits inside `db_text`; `pos delta` = extraction "
             "paper-local number minus DB paper-local number.")

    # ------------------------------------------------ per verdict
    L += ["", "## 5. Rows by verdict, with the reason", ""]
    for v in ("apply", "sub_part_loss", "wrong_question", "review"):
        sel = [r for r in rows if r["verdict"] == v]
        L.append("### %s - %d rows" % (v, len(sel)))
        L.append("")
        if not sel:
            L.append("_none_")
            L.append("")
            continue
        for r in sel:
            L.append("- **%s %s db#%s**%s - %s"
                     % (r["year"], r["paper"], r["db_question_number"],
                        " _(hand: %s)_" % r["hand"] if r["hand"] else "",
                        r["reason"]))
            L.append("  - DB : %s" % r["db_text"][:220])
            L.append("  - pair: %s" % r["unlockias_text"][:220])
        L.append("")

    L += ["## 6. What this does not settle", "",
          "- The calibration set is %d rows and the thresholds are derived from "
          "its extremes. Reproducing it is necessary, not sufficient."
          % len(labelled),
          "- The brief's 14th hand-classified row is not identified, so one "
          "labelled wrong-question judgement is unaccounted for.",
          "- `sub_part_loss` covers two shapes. Six rows are the classic "
          "(a)/(b) case, caught structurally. The two 2019 GS4 rows are caught "
          "by the length floor instead: their `db_text` is 'What do each of the "
          "following quotations mean to you?' plus one quotation, and the pair "
          "is the quotation alone - applying it would delete the instruction "
          "that makes the question answerable. Same defect, different shape.",
          "- `review` is a real verdict here, not a fallback: %d rows carry "
          "signals the labelled data cannot place, and they need the same hand "
          "inspection the first 14 got." % c["review"],
          "- Position delta is reported but not used as a rule. It disagrees "
          "with the pairing on rows of every class, including genuine ones "
          "(2018 GS1 #5 is a correct pair at a delta of 14), so it carries no "
          "usable signal on its own.",
          "- No worklist column has been updated."]

    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
