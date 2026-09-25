# REG-FIX-1 brief (batch owners)

A statutory fact-check (REG-FACTCHECK-1, law as of Sept 2026) produced corrections for your batch:
/home/claude/corpus/factcheck/fix_<BATCH>.json — each row: id, verdict (wrong_key | fix_needed), fact, source, note.

NOTE: your builder files were re-synced to the repo versions (repo-relative _REG paths, no /home/claude). Edit those.
Keep them free of /home/claude paths.

Rules:
- Edit ONLY the listed ids, in your builder part modules. Keep question ORDER and COUNT unchanged (ids must not shift).
- wrong_key: make the correct option the one that is right under current law. Answer letters are assigned by reglib
  position balancing, so ignore the checker's suggested letter — change which option TEXT is correct / the figures.
  If no option was correct, rewrite options (and stem if needed) so exactly one is right, keeping named-error distractors.
  If the law changed, prefer testing the CURRENT rule; an old value may become a named distractor ("pre-2026 value").
- fix_needed: correct the section numbers, ref, explanation, stem assumption or wording exactly as the note says.
  Where the note flags ambiguity (two defensible options), add the missing assumption to the stem.
- Update ref= with the corrected provision/amendment. Keep verify_fact=True.
- Numbers stay computed in Python; add asserts for new key values.
- Rebuild your batch; then run the length-cue check (must print 0):
  python3 -c "import json;q=json.load(open('/home/claude/corpus/out/<BATCH_FILE>.json'))['questions'];print(sum(1 for x in q if (lambda L,c:L[-1]>=25 and c==L[-1] and c>1.15*L[-2])(sorted(len(o['text']) for o in x['options']),[len(o['text']) for o in x['options'] if o['is_correct']][0])))"
- Report: one line per id — what changed. Nothing else.
