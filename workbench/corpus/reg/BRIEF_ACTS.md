# REG-CORPUS Acts addendum (read BRIEF.md first; everything there applies)

New subject: `financial-sector-acts`. Topic = one Act. Microtopics = 3–6 per Act, defined by YOU.

## Catalogue file (you create it)
- Write /home/claude/corpus/lists/fsa.<BATCH>.tsv with header: `slug\texams\tname\tact`
- slug = reglib.make_slug(name, "fsa")  (microtopic names must be unique across all Acts: prefix each with a short Act tag,
  e.g. "RBI Act — Central Board and governance", "BR Act — licensing under s.22").
- exams = `ifsca,pfrda,sebi` for every row. act = full Act name (e.g. "Reserve Bank of India Act, 1934").
- Build with: `B = Batch("<BATCH>", "financial-sector-acts", "<PREFIX>", list_file="/home/claude/corpus/lists/fsa.<BATCH>.tsv")`
  but in the builder compute that path repo-relatively: `_os.path.join(_REG, 'lists', 'fsa.<BATCH>.tsv')`
  where `_REG = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))`; `sys.path.insert(0, _REG)`. NO /home/claude paths in builders.

## Question design for Acts
- Hard = APPLICATION: fact-pattern stems ("Bank X fails to maintain CRR for 3 days…", "A secured creditor holding 70% by value…",
  "A payment system operator without authorisation…"), computations where the Act gives numbers (penal interest, limits, timelines,
  thresholds, penalties, voting percentages, days), statement combinations, assertion–reason, match section↔provision, and ≥1 case set (3–5 Q) per Act where the Act allows.
- Mix per Act: ~20% L1, 30% L2, 30% L3, 20% L4.
- verify_fact=True on EVERY question; ref = "<Act>, s.<n>" (and amendment year if relied on). Use only provisions you are confident are current as of mid-2026, including amendments you are sure of (e.g. Banking Laws (Amendment) Act 2025 only if certain of the specific change). If unsure of a number, don't use it — or give it in the stem as data.
- Distractors: pre-amendment values, neighbouring sections, the other regulator's power, wrong timeline.
- Run the length-cue check at the end (must print 0):
  python3 -c "import json;q=json.load(open('/home/claude/corpus/out/<BATCH>.json'))['questions'];print(sum(1 for x in q if (lambda L,c:L[-1]>=25 and c==L[-1] and c>1.15*L[-2])(sorted(len(o['text']) for o in x['options']),[len(o['text']) for o in x['options'] if o['is_correct']][0])))"

## Report
Count per Act, microtopics per Act (names), levels, case sets, least-confident items (id + fact to check). Don't paste questions.
