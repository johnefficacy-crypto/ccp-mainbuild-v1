# Editorial answer-key / rationale fixtures (correction prompts)

Human-authored **reference answers + rationales** for every *correction-type*
English writing prompt in this seed — the fixture the checklist "Prompt bank
seed" row tracked as `REMAINING: a documented editorial answer-key/rationale
fixture per correction prompt still to add`.

These files are **editorial documentation, not runtime data**. They are NOT
imported into any database, NOT parsed by the Bulk Import UI, and NOT consumed
by the evaluator. The importable content is the sibling `NN_*.json` row arrays;
these `answer_keys/*.answers.json` files exist so a Content Studio reviewer (and,
later, an evaluator gold-set author) has a canonical "what a good answer looks
like, and why" reference for each prompt.

## Files

| File | Covers seed batch | Entries |
|---|---|---|
| `02_sentence_correction.answers.json` | `02_sentence_correction.json` | 50 |
| `03_grammar.answers.json` | `03_grammar.json` | 100 |
| `04_vocabulary.answers.json` | `04_vocabulary.json` (source-bearing rows only) | 35 |
| **Total** | | **185** |

**Scope = one entry per source-bearing (correction) prompt.** Every row that
carries a `source_text` (a sentence to fix/replace/rewrite) has an answer key.
The 15 open-ended *production* rows in `04_vocabulary.json` (the
`Use the word "…" correctly in a sentence` prompts) carry no `source_text` and
have no single canonical answer, so they are intentionally excluded — there is
no answer *key* for an open composition. Sentence-construction (`01`) and
paragraph (`05`) are likewise production tasks, not corrections, and are out of
scope.

## Shape

```json
{
  "_meta": { "batch": "…", "scope": "…", "count": N, "entry_fields": { … } },
  "keys": {
    "ewp-seed-scor-001": {
      "source_text": "Because the train was late.",
      "exercise_type": "sentence_correction",
      "error_type": "sentence fragment",
      "reference_answer": "The train was late.",
      "acceptable_variants": ["We cancelled our plans because the train was late."],
      "rationale": "The dependent clause has no main clause; removing the subordinator 'Because' (or attaching an independent clause) makes it a complete sentence."
    }
  }
}
```

Entries are **keyed by `external_key`**, so each answer key lines up 1:1 with the
seed row of the same key. The `source_text` is echoed verbatim from the seed row
for reviewer cross-check.

## What `reference_answer` / `acceptable_variants` are (and are not)

They are **illustrative gold answers**, not an exhaustive accept-list. Correction
prompts admit many valid rewrites; a reviewer judges a learner's answer on
whether it fixes the named error while preserving meaning — **not** by
string-matching these fixtures. `acceptable_variants` lists a few additional
correct rewrites where they are common; `[]` means one natural fix dominates
(typical for spelling and subject–verb agreement).

## Keeping them in sync with the seed

The `source_text` in every entry must byte-match the same-key row in the batch
file. To re-check after any seed edit:

```bash
python3 - <<'PY'
import json
for ans, seed in [("02_sentence_correction.answers.json","02_sentence_correction.json"),
                  ("03_grammar.answers.json","03_grammar.json"),
                  ("04_vocabulary.answers.json","04_vocabulary.json")]:
    sd = {r["external_key"]: r.get("source_text") for r in json.load(open("../"+seed))}
    ad = json.load(open(ans))["keys"]
    mism = [k for k,v in ad.items() if sd.get(k) != v["source_text"]]
    missing = [k for k,v in sd.items() if v is not None and k not in ad]
    print(ans, "mismatch", mism, "missing", missing)
PY
```

If a seed sentence changes, update the matching answer key in the same PR.
