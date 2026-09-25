# REG-FACTCHECK-1 brief (all checkers)

Input: /home/claude/corpus2/factcheck/in_<GROUP>.json — MCQs whose keyed answer depends on a factual (static GK) fact
(section, threshold, %, rate, time limit, date, composition, penalty). Each item: id, stem, options, keyed, ref, explanation.

Task per item: decide whether the KEYED answer is correct under the law/regulation IN FORCE AS OF SEPTEMBER 2026.
- Use WebSearch/WebFetch against primary/official sources first: indiacode.nic.in, egazette, mca.gov.in, rbi.org.in
  (Master Directions/Circulars), sebi.gov.in, irdai.gov.in, pfrda.org.in, ifsca.gov.in, ibbi.gov.in, cbic/incometax.gov.in,
  cci.gov.in, fiu.gov.in. Secondary (Indian Kanoon, taxguru, PRS, ICAI/ICSI material) acceptable when primary text is not reachable.
- Check every fact the key depends on, including amendments (e.g. 2019–2026 amendments, Income-tax Act 2025, Banking Laws
  (Amendment) Act 2025, Sabka Bima Sabki Raksha insurance amendment 2025, PRB replacing BPSS).
- Also flag: stem ambiguity where two options are defensible; wrong section number cited in stem/explanation even if key OK.
- Group items by Act/topic and check each provision once, then apply to all items that use it — be efficient.
- Do NOT edit any builder or output file.

Output: /home/claude/corpus2/factcheck/out_<GROUP>.json — list, one entry per input id, EVERY id present:
{"id", "verdict": "confirmed" | "fix_needed" | "wrong_key" | "unverifiable",
 "fact": short statement of the provision checked (with number/threshold),
 "source": URL (required for confirmed/fix_needed/wrong_key),
 "note": what is wrong and the exact fix (new key letter, corrected figure/section/wording) — required unless confirmed}
Verdict meanings: confirmed = key right & facts current; fix_needed = key right but stem/explanation/ref/section has an
error or ambiguity; wrong_key = keyed answer is wrong under current law (give the correct letter or say none is correct);
unverifiable = could not find a reliable source (say what you tried).

Report back only: counts per verdict, and the list of wrong_key ids with one-line reasons.
