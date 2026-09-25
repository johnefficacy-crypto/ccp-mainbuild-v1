"""UPSC-CSAT-KEY-CHECK-01: check every keyed CSAT (Prelims Paper II) question against UPSC's key and an independent solve.

Reads (no DB access):
  workbench/sources/upsc-csat-key-check-input.json                    operator export, 315 keyed questions in 4 papers
  workbench/sources/upsc-official-keys/csp_2023_2026_gs2_key_transcription.py   UPSC Paper II keys, all four series
  workbench/sources/upsc-csat-independent-solve.json                  key-blind solve of every question
  app/supabase/migrations/228_pyq_upsc_cse_2025_prelims_csat_canonical.sql     2025 passage (stimulus) links
Writes:
  workbench/worksheets/UPSC-CSAT-KEY-CHECK.csv
Prints every count quoted in workbench/reports/UPSC-CSAT-KEY-CHECK-FINDINGS.md.

Run from the repo root: python workbench/scripts/upsc_csat_key_check_01.py
"""
import csv
import importlib.util
import itertools
import json
import re
import unicodedata
from collections import Counter

OUT = 'workbench/worksheets/UPSC-CSAT-KEY-CHECK.csv'
PAPERS = {
    2023: '586d515e-2d3d-485d-a944-3983e4569e53',
    2024: '9e191ae4-68b9-47bf-9121-6d9d468a7bc5',
    2025: '505b29a0-0d4d-5230-88aa-3bbc525a6db5',
    2026: 'b06305ad-cc93-4c27-b309-1b590f0a3247',
}

spec = importlib.util.spec_from_file_location(
    'k', 'workbench/sources/upsc-official-keys/csp_2023_2026_gs2_key_transcription.py')
kmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kmod)
KEY, FINAL = kmod.KEY, kmod.FINAL

rows = json.load(open('workbench/sources/upsc-csat-key-check-input.json', encoding='utf-8'))
solve = {(s['year'], s['question_number']): s
         for s in json.load(open('workbench/sources/upsc-csat-independent-solve.json', encoding='utf-8'))}


def ws(t):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', t or '').strip().lower())


def alnum(t):
    return re.sub(r'[^a-z0-9]', '', (t or '').lower())


def opts(r):
    return {o['label'].lower(): o for o in r['options']}


def stored_label(r):
    return next(l for l, o in opts(r).items() if o['id'] == r['correct_option_id'])


# ---------- series identification: stored-key agreement with each series ----------
SERIES = {}
print('series identification (stored key vs UPSC series, by question number)')
for y, pid in PAPERS.items():
    pr = [r for r in rows if r['pyq_paper_id'] == pid]
    assert all(r['year'] == y for r in pr)
    agree = {s: sum(stored_label(r) == KEY[(y, s)][r['question_number']].lower() for r in pr) for s in 'ABCD'}
    best = max(agree, key=agree.get)
    SERIES[y] = best
    drops = {s: [n for n, v in KEY[(y, s)].items() if v == 'X'] for s in 'ABCD'}
    keyless = [r['question_number'] for r in pr if not r['correct_option_id']]
    absent = sorted(set(range(1, 81)) - {r['question_number'] for r in pr})
    print(f'  {y} ({"final" if FINAL[y] else "PROVISIONAL"}): {len(pr)} rows; agreement {agree} -> Series {best}; '
          f'UPSC drops per series {drops}; corpus keyless rows {keyless}; question numbers absent from corpus {absent}')

# ---------- reconcile ----------
out = []
for r in sorted(rows, key=lambda r: (r['year'], r['question_number'])):
    y, n = r['year'], r['question_number']
    o = opts(r)
    st = stored_label(r)
    up = KEY[(y, SERIES[y])][n].lower()
    s = solve[(y, n)]
    sl = s['answer_label'] if s['solvable'] == 'yes' and s.get('answer_label') else None
    mv = bool(s.get('multiple_valid'))
    decisive = sl is not None and not mv
    if s['solvable'] == 'yes':
        solved = s.get('answer_option_text') or f"no option matches: {s['working'][:120]}"
    else:
        solved = f"not solvable: {s.get('stem_defect') or 'see working'}"
    notes, flags = [], []
    src = 'final' if FINAL[y] else 'provisional'
    new, applies = '', 'no'
    if sl and sl != up:
        # Q75 signature test: the solve and UPSC's letter name different option TEXTS.
        flags.append(f"SOLVE_VS_UPSC: solve -> ({sl}) \"{o[sl]['text']}\"; UPSC {src} key -> ({up}) \"{o[up]['text']}\"")
    if st == up:
        verdict = 'MATCH'
        if decisive and sl == up:
            conf = 'high'
        elif sl is None:
            conf = 'medium'
            notes.append('stored key equals UPSC key by letter; not independently solvable')
        elif mv:
            conf = 'medium'
            notes.append('solve has more than one defensible reading; UPSC key selects the stored option')
        else:
            conf = 'low'
            notes.append('UPSC key and stored key agree; the independent solve disagrees (UPSC governs)')
    else:
        if FINAL[y] or (decisive and sl == up):
            verdict, applies, new = 'CORRECTION', 'yes', o[up]['id']
            if decisive and sl == up:
                conf = 'high' if FINAL[y] else 'medium'
                notes.append(f'UPSC {src} key and independent solve agree on ({up}) against stored ({st})')
            elif sl is None:
                conf = 'medium'
                notes.append(f'UPSC {src} key ({up}) against stored ({st}); not independently solvable, so the target '
                             f'text rests on the UPSC letter mapping to the corpus label')
            else:
                conf = 'medium' if mv else 'low'
                notes.append(f'UPSC {src} key ({up}) against stored ({st}); the solve '
                             f'{"has several readings and UPSC selects one of them" if mv else "disagrees"}: UPSC governs')
            if not FINAL[y]:
                notes.append('2026 key is provisional; applied only because the independent solve corroborates it')
        else:
            verdict, conf = 'PROPOSED', 'low'
            notes.append(f'UPSC PROVISIONAL key says ({up}) "{o[up]["text"]}" (option id {o[up]["id"]}) against stored ({st}); '
                         f'not independently solvable; needs a human decision or UPSC\'s final key')
    if s.get('stem_defect'):
        notes.append(f"stem: {s['stem_defect']}")
    out.append({
        'question_id': r['question_id'], 'pyq_paper_id': r['pyq_paper_id'], 'year': y, 'question_number': n,
        'stored_key_label': st, 'stored_key_text': o[st]['text'], 'upsc_key_label': up,
        'upsc_key_text': o[up]['text'], 'solved_answer': solved, 'solvable': s['solvable'],
        'current_correct_option_id': r['correct_option_id'], 'new_correct_option_id': new, 'applies': applies,
        'verdict': verdict, 'confidence': conf,
        'note': '; '.join(flags + notes + [f"working: {s['working']}"]),
    })

FIELDS = ['question_id', 'pyq_paper_id', 'year', 'question_number', 'stored_key_label', 'stored_key_text',
          'upsc_key_label', 'upsc_key_text', 'solved_answer', 'solvable', 'current_correct_option_id',
          'new_correct_option_id', 'applies', 'verdict', 'confidence', 'note']
with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(out)

# ---------- validation ----------
owner = {o['id']: r['question_id'] for r in rows for o in r['options']}
print('\nrows', len(out), '| unique ids', len({x['question_id'] for x in out}),
      '| set-equal to export:', {x['question_id'] for x in out} == {r['question_id'] for r in rows})
print('new_correct_option_id not belonging to its question:',
      sum(1 for x in out if x['new_correct_option_id'] and owner[x['new_correct_option_id']] != x['question_id']))
print('applies=yes with empty new_correct_option_id:', sum(1 for x in out if x['applies'] == 'yes' and not x['new_correct_option_id']))
print('new id equal to current:', sum(1 for x in out if x['new_correct_option_id'] == x['current_correct_option_id']))
for col in ('verdict', 'confidence', 'solvable'):
    print(col, dict(Counter(x[col] for x in out)), {y: dict(Counter(x[col] for x in out if x['year'] == y)) for y in PAPERS})
print('applies=yes', sum(x['applies'] == 'yes' for x in out))

decisive_rows = [x for x in out if solve[(x['year'], x['question_number'])]['solvable'] == 'yes'
                 and solve[(x['year'], x['question_number'])].get('answer_label')
                 and not solve[(x['year'], x['question_number'])].get('multiple_valid')]
agree_up = [x for x in decisive_rows if solve[(x['year'], x['question_number'])]['answer_label'] == x['upsc_key_label']]
print(f'\nunique-answer solves: {len(decisive_rows)}; solved option text == text under UPSC letter: {len(agree_up)}')
print('solves with several readings:', [(x['year'], x['question_number']) for x in out if solve[(x['year'], x['question_number'])].get('multiple_valid')])
print('\nrows needing attention:')
for x in out:
    if x['verdict'] != 'MATCH' or x['confidence'] != 'high' and 'SOLVE_VS_UPSC' in x['note']:
        print(f"  {x['year']} Q{x['question_number']}: {x['verdict']}/{x['confidence']} stored {x['stored_key_label']} "
              f"upsc {x['upsc_key_label']} solve '{x['solved_answer'][:50]}' | {x['note'][:260]}")

# ---------- stems ----------
print('\nstem defects (from the solve pass)')
PASSAGE = re.compile(r'passage', re.I)
for y in PAPERS:
    miss = sorted(n for (yy, n), s in solve.items() if yy == y and s.get('stem_defect') and PASSAGE.search(s['stem_defect']))
    runs = [list(g) for _, g in itertools.groupby(miss, key=lambda n, c=itertools.count(): n - next(c))]
    other = sorted((n, s['stem_defect']) for (yy, n), s in solve.items()
                   if yy == y and s.get('stem_defect') and not PASSAGE.search(s['stem_defect']))
    print(f'  {y}: missing passage {len(miss)} in {len(runs)} runs {[f"{r[0]}-{r[-1]}" if len(r) > 1 else str(r[0]) for r in runs]}')
    for n, sd in other:
        print(f'      Q{n}: {sd}')

mig = open('app/supabase/migrations/228_pyq_upsc_cse_2025_prelims_csat_canonical.sql', encoding='utf-8').read()
qnum = {m.group(1): int(m.group(2)) for m in re.finditer(
    r"insert into public\.pyq_questions.*?values \('([0-9a-f-]+)', '505b29a0[^']*', (\d+),", mig, re.S)}
links = re.findall(r"insert into public\.pyq_question_stimuli \([^)]*\)\s*values \('[0-9a-f-]+', '([0-9a-f-]+)', '([0-9a-f-]+)'", mig)
linked = sorted(qnum[q] for q, _ in links)
miss25 = sorted(n for (yy, n), s in solve.items() if yy == 2025 and s.get('stem_defect') and PASSAGE.search(s['stem_defect']))
print(f'  2025 per migration 228: {len(set(s for _, s in links))} passages linked to {len(linked)} questions; '
      f'passage-dependent questions with no link: {sorted(set(miss25) - set(linked))}')

# ---------- duplicates and overlap ----------
dup = [(r['year'], r['question_number']) for r in rows if len({ws(o['text']) for o in r['options']}) < len(r['options'])]
print('\nduplicate option text (whitespace/case-normalised, symbols kept):', dup)
sig = {r['question_id']: (alnum(r['question_text']), tuple(sorted(ws(o['text']) for o in r['options']))) for r in rows}
for a, b in itertools.combinations(PAPERS, 2):
    shared = [(x['question_number'], z['question_number']) for x in rows if x['year'] == a
              for z in rows if z['year'] == b and sig[x['question_id']] == sig[z['question_id']]]
    print(f'  shared questions {a}~{b}: {len(shared)}')
stems = Counter((r['year'], alnum(r['question_text'])) for r in rows)
print('identical stems within a paper (options differ):',
      {y: sorted(sorted(r['question_number'] for r in rows if r['year'] == y and alnum(r['question_text']) == st)
                 for (yy, st), c in stems.items() if yy == y and c > 1) for y in PAPERS})
