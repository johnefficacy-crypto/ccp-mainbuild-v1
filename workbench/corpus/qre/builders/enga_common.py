"""Shared helpers for QRE-ENG-A (English: RC, Cloze, Fill in the Blanks). Original passages/sentences only."""

SL = {
    "AE": "eng-argument-evaluation-in-a-passage-3f8c21ba",
    "TONE": "eng-author-tone-attitude-and-purpose-87729e1a",
    "DET": "eng-explicit-detail-retrieval-5825931a",
    "INF": "eng-inference-and-implied-meaning-a005bcd3",
    "MAIN": "eng-main-idea-and-central-theme-59263450",
    "SYN": "eng-passage-based-synonym-and-antonym-b6b1d1e6",
    "VOC": "eng-vocabulary-from-context-within-a-passage-b55df114",
    "CC": "eng-connector-and-transition-cloze-adcb36dd",
    "DB": "eng-double-blank-sentence-completion-86aae4e4",
    "MB": "eng-multi-blank-passage-cloze-85f89037",
    "SB": "eng-single-blank-contextual-cloze-cd934632",
    "CF": "eng-connector-based-completion-cbecd4db",
    "US": "eng-correct-and-incorrect-usage-of-a-word-e7d37216",
    "PP": "eng-preposition-and-phrasal-completion-5c07ccb9",
    "SC": "eng-sentence-completion-with-a-missing-part-71b4f9ef",
    "SW": "eng-single-word-contextual-fit-601cbc5c",
    "WP": "eng-word-pair-fit-32a9e377",
}

FORMULA = {
    "AE": "Isolate the conclusion and its premise; the right option bears directly on the link between them (strengthen / weaken / assume).",
    "TONE": "Judge tone from the author's own evaluative words and qualifiers, not from views the author merely reports.",
    "DET": "Locate the sentence that answers the question; the key restates it, distractors twist or import facts.",
    "INF": "An inference must follow necessarily from the text without new assumptions; reject extreme or out-of-scope claims.",
    "MAIN": "The main idea covers the whole passage including the author's conclusion; reject options that are too narrow, too broad or reversed.",
    "SYN": "Replace the word with each option in its sentence; keep the sense the passage uses, not a different dictionary sense.",
    "VOC": "Read two sentences either side; choose the meaning the context forces, not the literal or most common sense.",
    "CC": "Identify the logical relation between the two ideas (contrast, cause, addition, example, condition, sequence) and pick the connector that signals it.",
    "DB": "Fix the logical signal (though / because / far from / rather than) first; both words must fit it and each other.",
    "MB": "Read the whole passage first; each blank must fit grammar, collocation and the passage's line of argument.",
    "SB": "Find the context clue (cause, contrast, restatement) that decides the blank.",
    "CF": "Match the connector to the relation (contrast, condition, purpose, correlative pair) and to the grammar that follows it (clause vs noun phrase).",
    "US": "Test each sentence against the word's standard dictionary sense and part of speech; watch confusable pairs.",
    "PP": "Prepositions and particles are fixed by the governing word or phrasal verb; recall the standard collocation.",
    "SC": "The missing part must complete the grammar (tense, inversion, agreement, conditional pattern) and the meaning.",
    "SW": "Decide the required sense and register from the context clue, then eliminate reversed, confusable and collocation-misfit words.",
    "WP": "Both words of the pair must independently make the sentence grammatical and meaningful; one misfit disqualifies the pair.",
}


def q(B, m, tier, level, stem, correct, wrongs, why, trap, kind="conceptual", group=None):
    steps = why if isinstance(why, list) else [why]
    return B.add(micro=SL[m], level=level, stem=stem, correct=correct,
                 wrongs=[(w, e) for w, e in wrongs], steps=steps,
                 formula=FORMULA[m], trap=trap, kind=kind, group=group, tier=tier)


def wc(text):
    return len(text.split())


def caseset(B, gid, tier, passage, items, lo=None, hi=None, lead="Read the passage and answer the question that follows."):
    if lo is not None:
        n = wc(passage)
        assert lo <= n <= hi, f"{gid}: passage has {n} words, need {lo}-{hi}"
    stim = lead + "\n\n" + passage.strip()
    assert 3 <= len(items) <= 5, gid
    for m, lvl, qs, c, w, why, trap in items:
        q(B, m, tier, lvl, stim + "\n\n" + qs, c, w, why, trap, kind="case", group=gid)


def std(B, tier, rows):
    """rows: (m, level, stem, correct, wrongs, why, trap)"""
    for m, lvl, stem, c, w, why, trap in rows:
        q(B, m, tier, lvl, stem, c, w, why, trap)
