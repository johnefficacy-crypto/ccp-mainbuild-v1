#!/usr/bin/env python3
"""Classify which study-artefact page type a macro syllabus topic earns.

Offline and pure: reads one JSON file of macro topics (children + tagged PYQ
questions), returns one verdict row per topic. No DB, no network, no
credentials. `classify_rows` is a pure function from input rows to output rows
so every threshold below can be retuned and the whole set re-run.

    python3 scripts/classify_topic_artefacts.py workbench/analysis/classifier_input.json

Writes <input-dir>/classifier_run_01.json and .md unless --out-prefix is given.

THE FIVE VERDICTS
  ask_record      every question asked here, grouped by child topic and year
  frequency_chart which children get asked, which never have, how recently
  roadmap         the macro's children in official syllabus wording
  form_timeline   how the ASK changed across years, where it demonstrably did
  none            no in-scope type fits; a valid and expected verdict

Only corpus- and syllabus-derived types are in scope. Anything needing authored
subject content is out, and is recorded separately in `content_artefact_needed`,
which is backlog metadata and never feeds the artefact_type decision.
"""

import argparse
import collections
import io
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Thresholds. Every number the classifier turns on is here and is arbitrary by
# admission - the point is that it is visible and tunable, not that it is
# derived. Each carries the reasoning that picked it.
# ---------------------------------------------------------------------------

T = {
    # -- corpus floor ------------------------------------------------------
    # Below this many tagged questions the corpus cannot carry any
    # corpus-derived artefact: an ask record of 7 questions is a paragraph, and
    # a frequency chart over 7 is noise. Syllabus-derived roadmap is still
    # available below the floor because it needs no questions at all.
    "min_questions_for_corpus_type": 8,

    # -- ask_record --------------------------------------------------------
    # An ask record is worth a page when a reader opening a child topic finds
    # more than a lone question under it. Mean questions per ASKED child, not
    # per child, so a macro is not punished for carrying never-asked children.
    "ask_record_min_questions": 15,
    "ask_record_min_q_per_asked_child": 2.5,

    # -- frequency_chart ---------------------------------------------------
    # A frequency chart earns its place when the interesting fact is the spread
    # across children rather than the questions themselves: enough children to
    # plot, enough of them asked to make bars, and a real asked/never-asked
    # split. Above the upper share bound the chart is mostly empty and would be
    # reporting the platform's own tagging gap to a learner, which the
    # frontend-governance rule in CLAUDE.md forbids.
    "freq_min_children": 10,
    "freq_min_asked_children": 4,
    "freq_min_never_asked_share": 0.25,
    "freq_max_never_asked_share": 0.85,

    # -- roadmap -----------------------------------------------------------
    # The handoff's own rule: a syllabus unit with many children is a roadmap.
    "roadmap_min_children": 8,

    # -- form_timeline (s4) ------------------------------------------------
    # Deliberately hard to earn. A verb mix wobbles on small samples, so a
    # shift counts only if every window carries enough verb-bearing questions
    # to mean anything, the leading verb actually changes end to end, and both
    # the old and the new leader move by a visible margin.
    "form_windows": ((2013, 2016), (2017, 2020), (2021, 2025)),
    "form_min_verb_questions_per_window": 10,
    "form_min_leader_share_delta": 0.15,
    # A verb that led the first window and then vanished is a change in the ask
    # even when its replacement was already present. That one-sided case needs
    # a wider margin than the two-sided one, because nothing corroborates it.
    "form_min_leader_collapse": 0.30,

    # -- s3 year spread ----------------------------------------------------
    # "clustered recent" = this share or more of the questions land in the last
    # `recent_window` years. "dried up" = nothing asked in the last
    # `dried_up_gap` years. Otherwise the spread is called even.
    "recent_window": 5,
    "clustered_recent_share": 0.60,
    "dried_up_gap": 3,

    # -- s5..s10 lexical signals ------------------------------------------
    # A lexical signal "fires" when this share of the macro's questions (or its
    # own title) contains a term from the signal's vocabulary. One in five is
    # low enough to catch a real theme and high enough to ignore stray words.
    "lexical_fire_share": 0.20,

    # -- confidence --------------------------------------------------------
    # A verdict is high-confidence when the corpus is large and the deciding
    # test cleared its threshold comfortably; low when it squeaked through or
    # the corpus is thin.
    "confidence_high_questions": 40,
    "confidence_low_questions": 12,
    "confidence_margin": 0.25,
    # s2 and s3 do not pick the artefact type - the corpus shape does - but they
    # temper how much to trust the pick. A macro whose ASKED children are mostly
    # rare, or whose record went quiet years ago, gets one step less confidence.
    "confidence_min_high_yield_share": 0.20,
}

# ---------------------------------------------------------------------------
# Lexicons. Explicit word lists, not model output. A term absent here is a term
# the classifier cannot see - that is a tuning surface, not a hidden default.
# ---------------------------------------------------------------------------

# s4 - UPSC Mains directive verbs, longest first so "critically analyse" is not
# double-counted as "analyse".
VERBS = [
    "critically analyse", "critically analyze", "critically examine",
    "critically comment", "discuss", "examine", "analyse", "analyze",
    "comment", "elucidate", "elaborate", "evaluate", "explain", "describe",
    "justify", "substantiate", "illustrate", "enumerate", "compare",
    "contrast", "suggest", "highlight", "assess",
]

# s5 - dates, periods, era words.
ERA_WORDS = [
    "ancient", "medieval", "modern", "colonial", "pre-colonial",
    "post-colonial", "pre-independence", "post-independence", "century",
    "centuries", "era", "period", "dynasty", "dynasties", "empire", "reign",
    "vedic", "mauryan", "gupta", "mughal", "sultanate", "harappan",
    "chalcolithic", "neolithic", "bhakti", "sufi", "renaissance",
    "freedom struggle", "partition", "independence", "medieval india",
]
YEAR_RE = re.compile(r"\b(1[0-9]{3}|20[0-2][0-9])\b")

# s6 - place, region and country names. Indian states and unions first, then
# physiographic regions, then the countries that recur in the GS corpus.
# "India", "Indian", "region" and "regional" are deliberately absent: every GS
# Mains question is about India, so including them made s6 fire on all ten
# macros and carry no information. s6 must mean a NAMED place.
PLACE_WORDS = [
    "andhra", "arunachal", "assam", "bihar",
    "chhattisgarh", "goa", "gujarat", "haryana", "himachal", "jharkhand",
    "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur",
    "meghalaya", "mizoram", "nagaland", "odisha", "punjab", "rajasthan",
    "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh",
    "uttarakhand", "west bengal", "delhi", "ladakh", "jammu", "kashmir",
    "himalaya", "himalayan", "deccan", "gangetic", "peninsular", "coastal",
    "western ghats", "eastern ghats", "north-east", "northeast", "monsoon",
    "basin", "plateau", "plain", "plains", "river",
    "delta", "desert", "china", "pakistan", "bangladesh", "nepal",
    "sri lanka", "myanmar", "afghanistan", "bhutan", "maldives", "russia",
    "japan", "africa", "asia", "europe", "america", "indo-pacific",
    "arctic", "antarctic", "ocean", "sea", "strait",
]

# s7 - contrastive structure.
CONTRAST_WORDS = [
    " vs ", " vs. ", "versus", "compare", "comparison", "contrast",
    "difference between", "differentiate", "as against", "on the one hand",
    "distinguish between", "trade-off", "tradeoff",
]

# s8 - named persons and thinkers that recur in the GS Mains corpus.
THINKER_WORDS = [
    "gandhi", "gandhian", "ambedkar", "nehru", "patel", "tagore",
    "vivekananda", "raja ram mohan roy", "tilak", "gokhale", "bose",
    "kautilya", "chanakya", "buddha", "mahavira", "kabir", "guru nanak",
    "akbar", "ashoka", "shivaji", "aurangzeb", "socrates", "plato",
    "aristotle", "kant", "mill", "bentham", "rawls", "nozick", "marx",
    "weber", "durkheim", "confucius", "aurobindo", "jp narayan",
    "lohia", "naoroji", "vidyasagar", "phule", "periyar", "sen",
    "thinker", "thinkers", "philosopher", "philosophers",
]

# s9 - enumeration words.
ENUM_WORDS = [
    "types", "kinds", "forms", "categories", "classification", "classify",
    "institutions", "institution", "commission", "commissions", "schedule",
    "schedules", "act", "acts", "article", "articles", "bodies", "body",
    "amendment", "amendments", "list", "enumerate", "components",
    "instruments", "organs", "agencies", "authorities", "pillars",
]

# s10 - process words.
PROCESS_WORDS = [
    "process", "processes", "stages", "stage", "mechanism", "mechanisms",
    "cycle", "formulation", "implementation", "procedure", "procedures",
    "steps", "workflow", "lifecycle", "pathway", "chain", "sequence",
    "evolution", "transition", "how does", "how do",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _words(text):
    return text.lower()


def _hits(text, vocabulary):
    """Terms from `vocabulary` present in `text`. Multi-word terms are matched
    as substrings, single words on word boundaries so 'act' does not match
    'action'."""
    low = _words(text)
    found = []
    for term in vocabulary:
        if " " in term or not term.isalpha():
            if term in low:
                found.append(term.strip())
        elif re.search(r"\b" + re.escape(term) + r"\b", low):
            found.append(term)
    return found


def _questions(row):
    return [q for child in row["children"] for q in child["questions"]]


def _verb_counts(texts):
    """Directive verbs per text, longest match first so a compound verb is
    counted once. Returns (counter, number of texts carrying any verb)."""
    counter = collections.Counter()
    bearing = 0
    for text in texts:
        low = _words(text)
        seen = set()
        for verb in VERBS:
            if re.search(r"\b" + re.escape(verb) + r"\b", low):
                if any(verb in s and verb != s for s in seen):
                    continue
                seen.add(verb)
        # drop a short verb wholly contained in a longer one already matched
        seen = {v for v in seen
                if not any(v != o and v in o for o in seen)}
        if seen:
            bearing += 1
            counter.update(seen)
    return counter, bearing


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

def compute_signals(row):
    """All ten signals for one macro topic. Every entry carries the observed
    value that a rule may later act on. A signal that the input cannot support
    is recorded as not_computable with the reason, never guessed."""
    children = row["children"]
    questions = _questions(row)
    texts = [q["question_text"] for q in questions]
    years = sorted(q["year"] for q in questions)
    asked = [c for c in children if c["questions"]]
    never = [c for c in children if not c["questions"]]
    n_q, n_child = len(questions), len(children)

    sig = {}

    # s1 - child count and never-asked share
    sig["s1"] = {
        "child_count": n_child,
        "asked_children": len(asked),
        "never_asked_children": len(never),
        "never_asked_share": round(len(never) / n_child, 3) if n_child else None,
        "total_questions": n_q,
        "questions_per_asked_child": round(n_q / len(asked), 2) if asked else 0.0,
    }

    # s2 - band distribution
    bands = collections.Counter(
        (c.get("band") or "null") for c in children)
    asked_bands = collections.Counter(
        (c.get("band") or "null") for c in asked)
    high_yield = sum(asked_bands[b] for b in ("near_certain", "likely"))
    sig["s2"] = {
        "bands": dict(bands),
        "asked_band_mix": dict(asked_bands),
        "dominant_band": bands.most_common(1)[0][0] if bands else None,
        "high_yield_share": round(high_yield / len(asked), 3) if asked else None,
        "graded": len([b for b in bands if b != "null"]) >= 2,
    }

    # s3 - year spread
    if not years:
        sig["s3"] = {"not_computable": "no tagged questions, no years to spread"}
    else:
        lo, hi = _window(row)
        recent_from = hi - T["recent_window"] + 1
        recent_share = sum(1 for y in years if y >= recent_from) / len(years)
        gap = hi - max(years)
        per_year = collections.Counter(years)
        if gap >= T["dried_up_gap"]:
            shape = "dried_up"
        elif recent_share >= T["clustered_recent_share"]:
            shape = "clustered_recent"
        else:
            shape = "even"
        sig["s3"] = {
            "shape": shape,
            "first_year": min(years),
            "last_year": max(years),
            "years_absent": sorted(set(range(lo, hi + 1)) - set(years)),
            f"share_in_last_{T['recent_window']}_years": round(recent_share, 3),
            "years_since_last_asked": gap,
            "questions_per_year": dict(sorted(per_year.items())),
        }

    # s4 - directive verb mix and whether it shifts across windows
    sig["s4"] = _verb_shift(texts, questions)

    # s5..s10 - lexical signals over question text plus the macro title
    corpus_text = row["macro_topic"] + " " + " ".join(
        c["name"] for c in children)
    sig["s5"] = _lexical(texts, corpus_text, ERA_WORDS, extra_re=YEAR_RE)
    sig["s6"] = _lexical(texts, corpus_text, PLACE_WORDS)
    sig["s7"] = _lexical(texts, corpus_text, CONTRAST_WORDS)
    sig["s8"] = _lexical(texts, corpus_text, THINKER_WORDS)
    sig["s9"] = _lexical(texts, corpus_text, ENUM_WORDS)
    sig["s10"] = _lexical(texts, corpus_text, PROCESS_WORDS)
    return sig


def _window(row):
    """Corpus year window. Taken from the input when it states one, otherwise
    from the questions themselves - never assumed."""
    span = row.get("corpus_window")
    if span and "-" in str(span):
        lo, hi = str(span).split("-", 1)
        return int(lo), int(hi)
    years = [q["year"] for q in _questions(row)]
    return (min(years), max(years)) if years else (0, 0)


def _lexical(texts, title_text, vocabulary, extra_re=None):
    """Share of questions carrying a vocabulary term, plus whether the topic's
    own title and child names carry one."""
    if not texts:
        return {"not_computable": "no tagged questions to scan"}
    hit_texts, terms = 0, collections.Counter()
    for text in texts:
        found = _hits(text, vocabulary)
        if extra_re is not None and extra_re.search(text):
            found = found + ["<year-literal>"]
        if found:
            hit_texts += 1
            terms.update(found)
    title_terms = _hits(title_text, vocabulary)
    share = hit_texts / len(texts)
    return {
        "question_share": round(share, 3),
        "fired": share >= T["lexical_fire_share"],
        "top_terms": [t for t, _ in terms.most_common(5)],
        "in_topic_title_or_children": sorted(set(title_terms))[:5],
    }


def _verb_shift(texts, questions):
    """s4: the directive-verb mix, and whether it demonstrably moved.

    A shift is recorded only when every window carries enough verb-bearing
    questions, the leading verb changes from first window to last, and both the
    departing and arriving leader move by at least the margin. Anything short
    of that is reported as no shift with the reason."""
    counts, bearing = _verb_counts(texts)
    out = {
        "verb_mix": dict(counts.most_common()),
        "verb_bearing_questions": bearing,
        "shift_detected": False,
    }
    if not texts:
        return {"not_computable": "no tagged questions to read verbs from"}

    windows = []
    for lo, hi in T["form_windows"]:
        w_texts = [q["question_text"] for q in questions if lo <= q["year"] <= hi]
        w_counts, w_bearing = _verb_counts(w_texts)
        windows.append({"window": f"{lo}-{hi}", "verb_questions": w_bearing,
                        "counts": w_counts})
    out["windows"] = [
        {"window": w["window"], "verb_questions": w["verb_questions"],
         "leader": (w["counts"].most_common(1)[0][0] if w["counts"] else None),
         "leader_share": (round(w["counts"].most_common(1)[0][1] / w["verb_questions"], 3)
                          if w["verb_questions"] and w["counts"] else None)}
        for w in windows
    ]

    thin = [w["window"] for w in windows
            if w["verb_questions"] < T["form_min_verb_questions_per_window"]]
    if thin:
        out["shift_reason"] = (
            "window(s) %s carry fewer than %d verb-bearing questions; a verb mix "
            "that thin cannot demonstrate a change"
            % (", ".join(thin), T["form_min_verb_questions_per_window"]))
        return out

    first, last = windows[0], windows[-1]
    lead_first = first["counts"].most_common(1)[0][0]
    lead_last = last["counts"].most_common(1)[0][0]
    def share(w, verb):
        return w["counts"][verb] / w["verb_questions"]
    fall = share(first, lead_first) - share(last, lead_first)
    rise = share(last, lead_last) - share(first, lead_last)
    out["leader_first_window"] = lead_first
    out["leader_last_window"] = lead_last
    out["departing_leader_share_fall"] = round(fall, 3)
    out["arriving_leader_share_rise"] = round(rise, 3)
    if (lead_first != lead_last
            and fall >= T["form_min_leader_share_delta"]
            and rise >= T["form_min_leader_share_delta"]):
        out["shift_detected"] = True
        out["shift_path"] = "two_sided"
        out["shift_reason"] = (
            "leading directive verb moved %s -> %s; %s fell %.2f and %s rose %.2f"
            % (lead_first, lead_last, lead_first, fall, lead_last, rise))
    elif (lead_first != lead_last
            and share(first, lead_first) >= T["form_min_leader_collapse"]
            and fall >= T["form_min_leader_collapse"]):
        out["shift_detected"] = True
        out["shift_path"] = "one_sided_collapse"
        out["shift_reason"] = (
            "%s led %s at %.2f and fell to %.2f by %s, a drop of %.2f; the ask "
            "changed by losing a verb rather than gaining one"
            % (lead_first, first["window"], share(first, lead_first),
               share(last, lead_first), last["window"], fall))
    else:
        out["shift_reason"] = (
            "leading verb %s -> %s with fall %.2f and rise %.2f; below the %.2f "
            "two-sided and %.2f collapse margins required to call the ask changed"
            % (lead_first, lead_last, fall, rise,
               T["form_min_leader_share_delta"], T["form_min_leader_collapse"]))
    return out


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

def decide(sig):
    """Return (artefact_type, [rule trace strings]).

    Rules are ordered by specificity. The first that matches wins, so a topic
    that could support two types gets the more specific one.
    s2 (bands) and s3 (year spread) deliberately do not appear here. Which
    artefact a topic earns is a question about the shape of its corpus; how much
    to trust that answer is where band mix and staleness belong, so they enter
    through `confidence` instead.

      R1 form_timeline  the ask demonstrably changed
      R2 ask_record     dense corpus; the questions themselves are the value
      R3 frequency_chart many children, thin per child; the spread is the value
      R4 roadmap        syllabus unit with many children; needs no questions
      R5 none
    """
    s1 = sig["s1"]
    n_q = s1["total_questions"]
    n_child = s1["child_count"]
    density = s1["questions_per_asked_child"]
    never_share = s1["never_asked_share"]
    trace = []

    corpus_ok = n_q >= T["min_questions_for_corpus_type"]
    if not corpus_ok:
        trace.append("R0 corpus floor: %d questions < %d; no corpus-derived type"
                     % (n_q, T["min_questions_for_corpus_type"]))

    if corpus_ok and sig["s4"].get("shift_detected"):
        trace.append("R1 form_timeline: " + sig["s4"]["shift_reason"])
        return "form_timeline", trace

    if corpus_ok and n_q >= T["ask_record_min_questions"] \
            and density >= T["ask_record_min_q_per_asked_child"]:
        trace.append(
            "R2 ask_record: %d questions over %d asked children = %.2f each, "
            "at or above %.2f" % (n_q, s1["asked_children"], density,
                                  T["ask_record_min_q_per_asked_child"]))
        return "ask_record", trace

    if (corpus_ok and n_child >= T["freq_min_children"]
            and s1["asked_children"] >= T["freq_min_asked_children"]
            and never_share is not None
            and T["freq_min_never_asked_share"] <= never_share
            <= T["freq_max_never_asked_share"]):
        trace.append(
            "R3 frequency_chart: %d children, %d asked, %.0f%% never asked, "
            "only %.2f questions per asked child"
            % (n_child, s1["asked_children"], never_share * 100, density))
        return "frequency_chart", trace

    if n_child >= T["roadmap_min_children"]:
        trace.append("R4 roadmap: %d children carry official syllabus wording; "
                     "no question volume required" % n_child)
        return "roadmap", trace

    trace.append("R5 none: %d questions and %d children clear no rule"
                 % (n_q, n_child))
    return "none", trace


def confidence(artefact_type, sig):
    """How far the deciding test cleared its threshold, tempered by corpus size."""
    s1 = sig["s1"]
    n_q = s1["total_questions"]
    if artefact_type == "none":
        return "high" if n_q == 0 else "medium"
    if n_q and n_q < T["confidence_low_questions"] and artefact_type != "roadmap":
        return "low"

    margin = None
    if artefact_type == "ask_record":
        margin = (s1["questions_per_asked_child"]
                  / T["ask_record_min_q_per_asked_child"]) - 1
    elif artefact_type == "frequency_chart":
        share = s1["never_asked_share"]
        lo, hi = T["freq_min_never_asked_share"], T["freq_max_never_asked_share"]
        margin = min(share - lo, hi - share) / ((hi - lo) / 2)
    elif artefact_type == "roadmap":
        margin = (s1["child_count"] / T["roadmap_min_children"]) - 1
    elif artefact_type == "form_timeline":
        if sig["s4"].get("shift_path") == "one_sided_collapse":
            margin = (sig["s4"]["departing_leader_share_fall"]
                      / T["form_min_leader_collapse"]) - 1
        else:
            margin = (min(sig["s4"]["departing_leader_share_fall"],
                          sig["s4"]["arriving_leader_share_rise"])
                      / T["form_min_leader_share_delta"]) - 1

    if margin is None:
        level = "medium"
    elif margin >= T["confidence_margin"] and n_q >= T["confidence_high_questions"]:
        level = "high"
    elif margin < 0.05 or n_q < T["confidence_low_questions"]:
        level = "low"
    else:
        level = "medium"

    # s2 and s3 temper the result without ever changing the verdict
    steps = ["low", "medium", "high"]
    share = sig["s2"].get("high_yield_share")
    if share is not None and share < T["confidence_min_high_yield_share"]:
        level = steps[max(0, steps.index(level) - 1)]
    if sig["s3"].get("shape") == "dried_up":
        level = steps[max(0, steps.index(level) - 1)]
    return level


def content_artefact_needed(sig):
    """BACKLOG FIELD ONLY.

    What this topic would earn if authored subject content were in scope. It is
    computed from the lexical signals alone, is never consulted by `decide`,
    and must not be read as a recommendation to build anything now.
    """
    # priority breaks a share tie toward the more specific artefact
    CANDIDATES = (("s8", "mindmap", 3, True), ("s7", "comparison", 2, False),
                  ("s6", "map", 1, True), ("s5", "timeline", 0, False))
    ranked = []
    for key, kind, priority, title_counts in CANDIDATES:
        s = sig.get(key, {})
        if "not_computable" in s:
            continue
        # The syllabus wording is evidence too - a unit whose children name three
        # or more places would need a map whether or not the questions said so -
        # but only for s6 and s8, whose vocabularies are proper nouns. s5 and s7
        # contain generic words ("period", "modern", "compare") that appear in
        # syllabus prose without meaning the topic is about an era or a contrast,
        # so those two need the question evidence.
        by_title = (title_counts
                    and len(s.get("in_topic_title_or_children", [])) >= 3)
        if s.get("fired") or by_title:
            ranked.append((1 if s.get("fired") else 0,
                           s.get("question_share", 0.0), priority, kind))
    if not ranked:
        return "none"
    ranked.sort(reverse=True)
    return ranked[0][3]


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

# A question whose text is mostly non-ASCII is a Hindi translation the corpus
# stored with broken encoding. It is unusable as a quoted snippet, so such
# questions sink to the back of the evidence pool - never rewritten, only
# deprioritised.
MOJIBAKE_NON_ASCII_SHARE = 0.15


def _legible(text):
    """False for a question whose stored text is garbled: a Hindi translation
    the corpus double-encoded, or an English stem carrying the unmistakable
    "\u00e2\u20ac" mojibake run in place of a quote or dash."""
    if not text:
        return False
    if "\u00e2\u20ac" in text:
        return False
    return sum(1 for ch in text if ord(ch) > 127) / len(text) <= MOJIBAKE_NON_ASCII_SHARE


def evidence(row, artefact_type, limit=3, max_words=14):
    """Two or three verbatim snippets, each the opening of a real question,
    truncated to whole words. Snippets are selected, never rewritten.

    Selection follows the verdict: a frequency chart is justified by the
    children that carry the questions, an ask record by spread across years."""
    pairs = []
    for child in row["children"]:
        for q in child["questions"]:
            pairs.append((child, q))
    if not pairs:
        return []

    # Quote only questions whose text survived the corpus encoding intact. A
    # topic with too few legible questions falls back to the full set rather
    # than returning nothing - evidence is selected, never rewritten.
    legible = [p for p in pairs if _legible(p[1]["question_text"])]
    pool = legible if len(legible) >= min(limit, 2) else pairs

    if artefact_type == "frequency_chart":
        weight = collections.Counter(
            c["topic_id"] for c, _ in pool)
        pool = sorted(pool, key=lambda p: (-weight[p[0]["topic_id"]], p[1]["year"]))
    elif artefact_type in ("form_timeline", "ask_record"):
        # both calls rest on the record spanning years, so sample the ends and
        # the middle of the window rather than three questions from one year
        pool = sorted(pool, key=lambda p: p[1]["year"])
        picks, used_children = [], set()
        for idx in (0, len(pool) // 2, len(pool) - 1):
            for step in range(len(pool)):
                for cand in (idx + step, idx - step):
                    if 0 <= cand < len(pool) and pool[cand] not in picks \
                            and pool[cand][0]["topic_id"] not in used_children:
                        picks.append(pool[cand])
                        used_children.add(pool[cand][0]["topic_id"])
                        break
                else:
                    continue
                break
        pool = picks or pool
    else:
        pool = sorted(pool, key=lambda p: p[1]["year"])

    out, seen = [], set()
    for child, q in pool:
        words = q["question_text"].split()
        snippet = " ".join(words[:max_words])
        if len(words) > max_words:
            snippet = snippet.rstrip(".,;:") + "…"
        key = snippet.lower()[:40]
        if key in seen:
            continue
        seen.add(key)
        out.append({"year": q["year"], "child_topic": child["name"][:90],
                    "snippet": snippet})
        if len(out) == limit:
            break
    return out


# ---------------------------------------------------------------------------
# Pure entry point
# ---------------------------------------------------------------------------

def classify_rows(rows):
    """Pure function: input topic rows in, verdict rows out. No IO."""
    results = []
    for row in rows:
        sig = compute_signals(row)
        artefact_type, trace = decide(sig)
        results.append({
            "subject": row.get("subject"),
            "macro_topic": row["macro_topic"],
            "artefact_type": artefact_type,
            "signals_fired": _reportable(sig),
            "decision_trace": trace,
            "confidence": confidence(artefact_type, sig),
            "content_artefact_needed": content_artefact_needed(sig),
            "evidence": evidence(row, artefact_type),
        })
    return results


def _reportable(sig):
    """Flatten the signal block into the reporting shape: one entry per signal
    with the observed value that drove it, and an explicit note where the input
    could not support the computation."""
    labels = {
        "s1": "child count and never-asked share",
        "s2": "predictability band distribution",
        "s3": "year spread of the questions",
        "s4": "directive verb mix and whether it shifts",
        "s5": "dates, periods and era words",
        "s6": "place, region and country names",
        "s7": "contrastive structure",
        "s8": "named persons or thinkers",
        "s9": "enumeration words",
        "s10": "process words",
    }
    out = []
    for key in ("s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"):
        value = sig[key]
        entry = {"signal": key, "reads": labels[key]}
        if isinstance(value, dict) and "not_computable" in value:
            entry["not_computable"] = value["not_computable"]
        else:
            entry["observed"] = value
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def to_markdown(results):
    head = ("| Subject | Macro topic | Artefact | Conf. | Key signals | "
            "Content backlog |\n|---|---|---|---|---|---|\n")
    body = []
    for r in results:
        by_id = {e["signal"]: e for e in r["signals_fired"]}
        s1 = by_id["s1"].get("observed", {})
        s3 = by_id["s3"].get("observed", {})
        keys = ("s1 %d children, %d never asked, %d questions (%.2f per asked child)"
                % (s1.get("child_count", 0), s1.get("never_asked_children", 0),
                   s1.get("total_questions", 0),
                   s1.get("questions_per_asked_child", 0.0)))
        if s3:
            keys += "; s3 %s" % s3.get("shape")
        if by_id["s4"].get("observed", {}).get("shift_detected"):
            keys += "; s4 verb shift"
        fired = [k for k in ("s5", "s6", "s7", "s8", "s9", "s10")
                 if by_id[k].get("observed", {}).get("fired")]
        if fired:
            keys += "; fired " + ", ".join(fired)
        body.append("| %s | %s | `%s` | %s | %s | %s |"
                    % (r["subject"], r["macro_topic"].replace("|", "/"),
                       r["artefact_type"], r["confidence"], keys,
                       r["content_artefact_needed"]))
    table = head + "\n".join(body) + "\n"

    detail = ["\n## Why each call\n"]
    for r in results:
        detail.append("### %s — `%s` (%s)\n" % (r["macro_topic"],
                                                r["artefact_type"],
                                                r["confidence"]))
        for line in r["decision_trace"]:
            detail.append("- %s" % line)
        for ev in r["evidence"]:
            detail.append("- _%d_ — \"%s\"" % (ev["year"], ev["snippet"]))
        detail.append("")
    return table + "\n".join(detail)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="path to the classifier input JSON")
    ap.add_argument("--out-prefix", default=None,
                    help="output path prefix; default <input-dir>/classifier_run_01")
    args = ap.parse_args(argv)

    with io.open(args.input, encoding="utf-8-sig") as fh:
        rows = json.load(fh)
    results = classify_rows(rows)

    prefix = args.out_prefix or os.path.join(
        os.path.dirname(os.path.abspath(args.input)), "classifier_run_01")
    with io.open(prefix + ".json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with io.open(prefix + ".md", "w", encoding="utf-8") as fh:
        fh.write("# Study-artefact classifier — run 01\n\n")
        fh.write("Source: `%s`. Thresholds are stated in "
                 "`scripts/classify_topic_artefacts.py`.\n\n" % args.input)
        fh.write(to_markdown(results))

    counts = collections.Counter(r["artefact_type"] for r in results)
    print("%d topics classified -> %s" % (len(results), dict(counts)))
    print("wrote %s.json and %s.md" % (prefix, prefix))
    return 0


if __name__ == "__main__":
    sys.exit(main())
