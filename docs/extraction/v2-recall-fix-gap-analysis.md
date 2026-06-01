# v2 Recall Fix — Gap Analysis

Produced by: Phase 1 diagnostic, branch `claude/pr9-v2-recall-fix`  
Fixture: 2026 GS-I, 92 expected questions  
Failing result: recall 0.707 (65/92), precision 0.774 (19 spurious / 84 extracted)

---

## Missed-Q breakdown

| Q#  | Page | Column | y_span | Reason class          | Evidence                                                    |
|-----|------|--------|--------|-----------------------|-------------------------------------------------------------|
| 1   | 3    | LEFT   | 0.075  | Bbox-inflate / small  | Stem extends to Q2 anchor; centroid (y≈0.15) outside fix bbox [0.066,0.141] |
| 2   | 3    | LEFT   | 0.103  | Bbox-inflate / small  | Stem extends to Q3 anchor; centroid (y≈0.38) outside fix bbox [0.236,0.339] |
| 3   | 3    | LEFT   | 0.275  | Bbox-inflate cascade  | Stem extends to column end; likely centroid or text-sim failure |
| 5   | 3    | RIGHT  | 0.082  | Bbox-inflate / small  | Stem extends to Q6 anchor; centroid outside fix bbox [0.432,0.514] |
| 6   | 3    | RIGHT  | 0.070  | Bbox-inflate / small  | Stem extends to column end; centroid outside fix bbox [0.658,0.728] |
| 7   | 5    | LEFT   | 0.255  | Bbox-inflate cascade  | Stem extends to Q8 anchor; cascade from un-stopped options |
| 8   | 5    | LEFT   | 0.278  | Bbox-inflate cascade  | Stem extends to column end; centroid outside fix bbox      |
| 9   | 5    | RIGHT  | 0.066  | Bbox-inflate / small  | Stem extends to Q10 anchor; centroid outside fix bbox [0.055,0.121] |
| 12  | 7    | LEFT   | 0.060  | Bbox-inflate / small  | Stem extends to Q13 anchor; centroid (y≈0.51) outside [0.437,0.497] |
| 13  | 7    | LEFT   | 0.075  | Bbox-inflate / small  | Stem extends to column end; centroid outside fix bbox [0.591,0.666] |
| 19  | 9    | RIGHT  | 0.089  | Bbox-inflate / small  | Stem extends to Q20 anchor; centroid outside [0.497,0.587] |
| 20  | 9    | RIGHT  | 0.084  | Bbox-inflate / small  | Stem extends to column end; centroid outside [0.703,0.787] |
| 22  | 11   | RIGHT  | 0.299  | Text-sim + spatial    | Inflated bbox reduces IoU; option text in question_text lowers text_sim below 0.95; question_number fallback may also fail if extracted qnum differs |
| 27  | 13   | RIGHT  | 0.358  | Text-sim + spatial    | Same mechanism as Q22 |
| 31  | 15   | RIGHT  | 0.118  | Bbox-inflate / small  | Stem extends to next anchor; centroid outside [0.065,0.183] |
| 40  | 19   | RIGHT  | 0.074  | Bbox-inflate / small  | Bottom of right column; centroid outside [0.714,0.787] |
| 54  | 29   | LEFT   | 0.245  | Bbox-inflate cascade  | All left-column questions on page 29 missed; same gate failure |
| 55  | 29   | LEFT   | 0.342  | Bbox-inflate cascade  | Stem extends to column end; cascade from Q54 |
| 64  | 35   | LEFT   | 0.248  | Bbox-inflate cascade  | Left column page 35; stem extends past options |
| 66  | 35   | RIGHT  | 0.207  | Text-sim + spatial    | Inflated bbox; text-sim degraded by option text inclusion |
| 80  | 43   | RIGHT  | 0.375  | Text-sim + spatial    | Large question but text_sim < 0.95 due to option text; spatial borderline |
| 81  | 43   | RIGHT  | 0.122  | Bbox-inflate / small  | Stem extends to column end; centroid outside [0.639,0.761] |
| 88  | 47   | LEFT   | 0.094  | Bbox-inflate / small  | Bottom of left column; centroid outside [0.665,0.758] |
| 90  | 47   | RIGHT  | 0.078  | Bbox-inflate / small  | Stem extends to Q91; centroid outside [0.236,0.314] |
| 92  | 49   | LEFT   | 0.079  | Bbox-inflate / small  | Stem extends to Q93 anchor; centroid (y≈0.24) outside [0.059,0.138] |
| 93  | 49   | LEFT   | 0.268  | Bbox-inflate cascade  | Stem extends to Q94 anchor; centroid outside [0.225,0.493] |
| 94  | 49   | LEFT   | 0.078  | Bbox-inflate / small  | Stem extends to column end; centroid outside [0.586,0.665] |

**Method note**: This analysis is static (code trace + fixture geometry). The extractor was not run against the live PDF; patterns are inferred from the known missed Q#s, their fixture bboxes, and the PR #528 code change described below.

---

## Spurious-extraction breakdown

19 extractions matched no fixture question. Likely sources:

| Source | Count (est.) | Why it passed gates |
|--------|-------------|---------------------|
| Skipped questions (Q63, Q67, Q71, Q72, Q73, Q76, Q83, Q98) | up to 8 | These were previously absorbed into adjacent stems; when those stems now extend past option labels, the scan continues and picks up these question ordinals as anchors |
| Text fragments inside un-stopped option blocks | ~8–11 | Lines in the extended-stem option area may carry ordinal-like tokens that pass the anchor gate with monotonicity satisfied |

---

## Root-cause buckets

**Bucket A — `find_stem_end` left-edge gate rejects genuine option labels** (affects all 27 missed Q#s)

PR #528 added a left-edge spatial gate to `find_stem_end`:

```python
# segmentation.py, find_stem_end (PR #528)
if _OPTION_RE.match(content_word.text):
    if content_word.bbox[0] <= column_left_edge + _ANCHOR_X_GAP:  # ← NEW gate
        return i
```

`_ANCHOR_X_GAP = 0.04`. In the 2026 GS-I corpus, option labels `(a)/(b)/(c)/(d)` are printed with ~5–8 mm indentation from the column text-block edge, equivalent to x ≈ effective_left + 0.05–0.08 in normalised coordinates. They consistently fall outside the 0.04 gate, so `find_stem_end` no longer stops at them.

When `find_stem_end` does not stop at option labels, it runs to the next question anchor. The question's stem bbox inflates vertically (y_max extends to the start of the next question). For questions shorter than ~0.15 normalised height, this pushes the extracted centroid outside the fixture bbox. The acceptance-test spatial gate (`IoU ≥ 0.50 OR centroid_inside`) then fails, and the `question_number == fix_qnum` fallback has no effect because the spatial precondition is AND'd in.

**Bucket B — Cascade within column** (contributes to pages 3, 5, 29, 49 all-missed left columns)

Once question N's stem inflates past question N+1's anchor, question N+1's stem similarly inflates (its own options are also rejected by the gate). This cascade multiplies the miss count within a column beyond what a single-question gate failure would cause.

**Bucket C — Spurious from previously-masked content** (19 spurious extractions)

In v1, option lines following a question were within that question's stem (because `find_stem_end` stopped at `(a)`). Any ordinal-like text inside option lines was invisible to `find_anchor_lines`. In v2, those option lines are now in free space (between `stem_end` and `next_anchor_idx`) and `extract_options` processes them — but crucially, the option lines are also still scannable for anchors on the NEXT `find_anchor_lines` call... actually this is the `option_lines` range, which is separate from `find_anchor_lines` (which was already run). The true source of spurious extractions is more likely the 8 skipped questions whose ordinals are now reachable as anchors.

---

## Proposed single-strategy fix

Remove the left-edge gate from `find_stem_end`. The function should stop at **any** `(a)/(b)/(c)/(d)` line at the start of a visual line, regardless of its x-position — identical to v1 behaviour. This is a one-line change in `segmentation.py`. The Module B left-edge gate (x ≤ effective_left + 0.04) correctly belongs only inside `extract_options`, where it discriminates genuine option markers from body enumerators when building the option tuple. It must not live in `find_stem_end`, whose only job is to bound the stem region for bbox computation.

Expected outcome: stem bboxes revert to v1 geometry, spatial matching recovers, recall ≥ 0.815 restored. Option extraction behaviour in `extract_options` is unaffected.
