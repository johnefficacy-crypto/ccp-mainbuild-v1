"""UPSC-KEY-APPLY-01: resolve UPSC Prelims 2020/2024 key corrections to option ids by option TEXT.

Reads (no DB access):
  workbench/sources/upsc-explanations-input.json            corpus rows (question_id, options with ids, correct_option_id)
  workbench/sources/upsc-official-keys/*.docx               question booklets (2020 Set C, 2024 Series D)
  workbench/sources/upsc-official-keys/csp20*_key_transcription.py  UPSC final keys
  docs/reference/answer-keys/*.csv, pyq_*_prelims_gs1_*.json         import sources (comparison only)
Writes:
  workbench/worksheets/UPSC-KEY-APPLY-2020-2024.csv
Prints every count quoted in workbench/reports/UPSC-KEY-APPLY-FINDINGS.md.

Run from the repo root: python workbench/scripts/upsc_key_apply_01.py
"""
import csv
import difflib
import glob
import importlib.util
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter

SRC = 'workbench/sources/upsc-official-keys/'
OUT = 'workbench/worksheets/UPSC-KEY-APPLY-2020-2024.csv'
GS_SLUG = 'upsc-cse-prelims-gs'
PAPER_ID = {  # pyq_paper_id per (year, paper); GS ids also appear in docs/pyqprelimsfrontloadnotes.md
    (2020, 'GS'): '980cfb08-efbd-453f-8dbc-251fefb9d3f5',
    (2024, 'GS'): '4d0bed5e-3b8a-4143-92c3-614ede901af5',
    (2024, 'CSAT'): '9e191ae4-68b9-47bf-9121-6d9d468a7bc5',
}
BOOKLET = {2020: 'UPSC_CSE_2020_PRE_GS-1_SET-C.docx', 2024: 'UPSC_CSE_2024_PRE_GS-1_set_D.docx'}
SERIES = {2020: 'C', 2024: 'D'}
URL = {
    2020: 'https://upsc.gov.in/sites/default/files/AnsKey-CSP-20-Paper-I-091121.pdf',
    2024: 'https://upsc.gov.in/sites/default/files/AnsKey-CivilServicesPExam-2024-GeneralStudies-I-210525.pdf',
}
FUZZY_SAME = 0.95  # scan artefacts such as "F�rfections" vs "Perfections"; nothing below this is treated as the same text


def load_py(path):
    spec = importlib.util.spec_from_file_location(path, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.KEY


KEYS = {}
for y in (2020, 2024):
    for s, k in load_py(SRC + f'csp{y}_gs1_key_transcription.py').items():
        KEYS[(y, s)] = k
KEYS.update(load_py(SRC + 'csp_2018_2025_gs1_key_transcription.py'))


def norm(t):
    t = unicodedata.normalize('NFKC', t or '').replace('�', '').lower()
    return re.sub(r'[^a-z0-9]', '', t)


def sim(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


# ---------- booklet parsing: the printed label is authoritative, not the position ----------
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
QPAT = {2020: re.compile(r'^\s*Question\s*:?\s*(\d{1,3})\s*[.:]?\s*(.*)$'),
        2024: re.compile(r'^\s*(\d{1,3})\.\s*(.*)$')}
OPT = re.compile(r'^\s*\(?([a-dA-D])\)\s*|(?<=\s)\(([a-d])\)\s*')


def docx_lines(path):
    root = ET.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
    out = []
    for p in root.iter(W + 'p'):
        t = ''.join((n.text or '') if n.tag == W + 't' else ('\t' if n.tag == W + 'tab' else
                    ('\n' if n.tag in (W + 'br', W + 'cr') else '')) for n in p.iter())
        out.extend(t.split('\n'))
    return out


def parse_booklet(year):
    qs, cur, expect = {}, None, 1
    for ln in docx_lines(SRC + BOOKLET[year]):
        m = QPAT[year].match(ln)
        if m and int(m.group(1)) == expect:  # only the next number opens a question
            cur = {'stem': m.group(2), 'pairs': []}
            qs[expect] = cur
            expect += 1
            continue
        if cur is None:
            continue
        ms = list(OPT.finditer(ln))
        lead = len(ln) - len(ln.lstrip())
        first_a_midline = ms and not cur['pairs'] and ms[0].group(2) == 'a'
        if ms and (ms[0].start() <= lead + 1 or first_a_midline):
            if ms[0].start() > lead + 1:
                cur['stem'] += ' ' + ln[:ms[0].start()].strip()
            for i, mm in enumerate(ms):
                end = ms[i + 1].start() if i + 1 < len(ms) else len(ln)
                cur['pairs'].append([(mm.group(1) or mm.group(2)).lower(), ln[mm.end():end].strip()])
        elif cur['pairs']:
            cur['pairs'][-1][1] += ' ' + ln.strip()
        else:
            cur['stem'] += ' ' + ln.strip()
    assert len(qs) == 100, (year, len(qs))
    return qs


def resolve_labels(pairs):
    """Return {label: text} honouring printed labels; a repeated label is read as the one label never printed."""
    labels = [l for l, _ in pairs]
    notes = []
    missing = [l for l in 'abcd' if l not in labels]
    seen, out = set(), {}
    for l, t in pairs:
        if l in seen and len(missing) == 1:
            notes.append(f'booklet prints "({l})" twice; the second is read as ({missing[0]}), the only label not printed')
            l = missing[0]
        seen.add(l)
        out[l] = t
    return out, labels, notes


# ---------- corpus ----------
rows_all = json.load(open('workbench/sources/upsc-explanations-input.json', encoding='utf-8'))
rows = [r for r in rows_all if r['year'] in (2020, 2024)]
BK = {y: parse_booklet(y) for y in (2020, 2024)}


def stored(r):
    o = [o for o in r['options'] if o['id'] == r['correct_option_id']]
    return o[0] if o else None


def order_check(r, bq):
    """Classify the corpus label->text mapping against the booklet's printed label->text mapping."""
    bmap, printed, notes = resolve_labels(bq['pairs'])
    if sorted(bmap) != list('abcd'):
        return 'UNCHECKABLE', None, notes + [f'booklet options not parseable as a-d: printed {printed}']
    perm, text_diff = {}, []
    for o in r['options']:
        on = norm(o['text'])
        exact = [l for l, t in bmap.items() if norm(t) == on]
        if o['label'] in exact:          # identical text under the same label (also covers duplicated option texts)
            perm[o['label']] = o['label']
        elif len(exact) == 1:
            perm[o['label']] = exact[0]
        elif len(exact) > 1:
            return 'UNCHECKABLE', None, notes + [f'corpus ({o["label"]}) text matches several booklet options {exact}']
        else:
            best = max((sim(on, norm(t)), l) for l, t in bmap.items())
            if best[0] >= FUZZY_SAME:
                perm[o['label']] = best[1]
                notes.append(f'corpus ({o["label"]}) "{o["text"]}" vs booklet ({best[1]}) "{bmap[best[1]]}": '
                             f'scan artefact, same text')
            else:
                text_diff.append(o['label'])
    texts = [norm(o['text']) for o in r['options']]
    if len(set(texts)) < len(texts):
        dup = [o['label'] for o in r['options'] if texts.count(norm(o['text'])) > 1]
        notes.append(f'options {"/".join(dup)} carry identical text in both corpus and booklet (source defect)')
    if text_diff:
        return 'TEXT_DIFFERS', perm, notes + [f'corpus option(s) {text_diff} match no booklet option']
    if all(k == v for k, v in perm.items()):
        return 'ORDER_OK', perm, notes
    moved = ', '.join(f'corpus ({k}) = booklet ({v})' for k, v in sorted(perm.items()) if k != v)
    return 'ORDER_DIFFERS', perm, notes + [f'permutation: {moved}']


out_rows = []
for r in sorted(rows, key=lambda r: (r['year'], r['subject_slug'] != GS_SLUG, r['question_number'])):
    y, n = r['year'], r['question_number']
    paper = 'GS' if r['subject_slug'] == GS_SLUG else 'CSAT'
    so = stored(r)
    row = {
        'question_id': r['question_id'], 'pyq_paper_id': PAPER_ID[(y, paper)], 'year': y, 'paper': paper,
        'question_number': n, 'order_verdict': '', 'stored_key_label': so['label'] if so else '',
        'stored_key_text': so['text'] if so else '', 'upsc_key_label': '', 'upsc_key_text': '',
        'current_correct_option_id': r['correct_option_id'] or '', 'new_correct_option_id': '',
        'applies': 'no', 'verdict': '', 'note': '',
    }
    if paper == 'CSAT':
        row.update(order_verdict='UNCHECKABLE', verdict='UNAVAILABLE',
                   note='No CSAT booklet in the repository, so neither option order nor a text-resolved key can be checked.')
        out_rows.append(row)
        continue
    bq = BK[y][n]
    # question identity by text: the booklet question with the same number must be the best text match
    scores = sorted(((sim(norm(r['question_text'])[:400], norm(q['stem'])[:400]), k) for k, q in BK[y].items()),
                    reverse=True)
    assert scores[0][1] == n and scores[0][0] >= 0.85, (y, n, scores[:2])
    ov, perm, notes = order_check(r, bq)
    row['order_verdict'] = ov
    u = KEYS[(y, SERIES[y])][n]
    row['upsc_key_label'] = u.lower() if u != 'X' else 'X'
    if u == 'X':
        row['verdict'] = 'DROPPED'
        if so:
            row['applies'] = 'yes'
            notes.append('UPSC dropped this item; the stored key must be cleared (no option id to set)')
        else:
            notes.append('UPSC dropped this item; stored key already empty; publish with no correct answer')
        row['note'] = '; '.join(notes)
        out_rows.append(row)
        continue
    bmap, _, _ = resolve_labels(bq['pairs'])
    utext = bmap.get(u.lower(), '')
    row['upsc_key_text'] = utext
    target = [o for o in r['options'] if norm(o['text']) == norm(utext)]
    if len(target) != 1:
        target = [o for o in r['options'] if sim(norm(o['text']), norm(utext)) >= FUZZY_SAME]
    if len(target) != 1:
        row['verdict'] = 'UNAPPLIABLE'
        notes.append(f'UPSC answer text "{utext}" matches {len(target)} corpus options')
    elif so and target[0]['id'] == so['id']:
        row['verdict'] = 'MATCH'
    else:
        row['verdict'] = 'CORRECTION'
        row['applies'] = 'yes'
        row['new_correct_option_id'] = target[0]['id']
        notes.append(f'set to corpus option ({target[0]["label"]}) "{target[0]["text"]}"; source {URL[y]}')
        if so and so['label'] == u.lower():
            notes.append('the letter-based check saw a MATCH here: the stored letter equals UPSC\'s letter but names a different text')
    row['note'] = '; '.join(notes)
    out_rows.append(row)

FIELDS = ['question_id', 'pyq_paper_id', 'year', 'paper', 'question_number', 'order_verdict', 'stored_key_label',
          'stored_key_text', 'upsc_key_label', 'upsc_key_text', 'current_correct_option_id',
          'new_correct_option_id', 'applies', 'verdict', 'note']
with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(out_rows)

# ---------- validation ----------
opt_owner = {o['id']: r['question_id'] for r in rows for o in r['options']}
src_ids = {r['question_id'] for r in rows}
out_ids = [r['question_id'] for r in out_rows]
print('rows', len(out_rows), '| unique ids', len(set(out_ids)), '| set-equal to input 2020+2024:', set(out_ids) == src_ids)
bad_owner = [r['question_id'] for r in out_rows if r['new_correct_option_id'] and opt_owner[r['new_correct_option_id']] != r['question_id']]
print('new_correct_option_id not belonging to its question:', len(bad_owner))
print('applies=yes with empty new_correct_option_id:',
      sum(1 for r in out_rows if r['applies'] == 'yes' and not r['new_correct_option_id']))
print('new_correct_option_id equal to current:', sum(1 for r in out_rows if r['new_correct_option_id'] and r['new_correct_option_id'] == r['current_correct_option_id']))
for key in ('order_verdict', 'verdict'):
    print(key, dict(Counter((r['year'], r['paper'], r[key]) for r in out_rows)))
print('order_verdict total', dict(Counter(r['order_verdict'] for r in out_rows)))
print('verdict total', dict(Counter(r['verdict'] for r in out_rows)), '| applies=yes', sum(r['applies'] == 'yes' for r in out_rows))
prev = {r['question_id']: r for r in csv.DictReader(open('workbench/worksheets/UPSC-KEY-CHECK-2020-2024.csv', encoding='utf-8'))}
for r in out_rows:
    p = prev[r['question_id']]['verdict']
    if (p == 'CORRECTION') != (r['verdict'] == 'CORRECTION') or r['order_verdict'] not in ('ORDER_OK', 'UNCHECKABLE') or r['note'] and r['verdict'] == 'MATCH':
        print(f'  {r["year"]} {r["paper"]} Q{r["question_number"]}: letter-check {p} -> {r["verdict"]} / {r["order_verdict"]} | {r["note"]}')
print('MATCH rows under a non-OK order verdict:',
      [(r['year'], r['question_number']) for r in out_rows if r['verdict'] == 'MATCH' and r['order_verdict'] not in ('ORDER_OK',)])


# ---------- import sources ----------
def csv_key(year):
    f = glob.glob(f'docs/reference/answer-keys/upsc_cse_{year}_*_prelims_gs1.csv')[0]
    return f, {int(r['question_number']): (r['correct_option_label'] or 'X').upper() for r in csv.DictReader(open(f))}


def db_key(year):
    out = {}
    for r in rows_all:
        if r['year'] == year and r['subject_slug'] == GS_SLUG:
            so = stored(r)
            out[r['question_number']] = so['label'].upper() if so else 'X'
    return out


def agree(a, b, scorable=None):
    ns = [n for n in a if n in b and (scorable is None or scorable[n] != 'X')]
    return f'{sum(a[n] == b[n] for n in ns)}/{len(ns)}'


print('\nkey-source agreement (letters, by question number; "scorable" excludes UPSC-dropped items)')
for y in (2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025):
    f, ck = csv_key(y)
    dk = db_key(y)
    line = [f'{y} {f.split("/")[-1].split(chr(92))[-1]}: CSV~DB {agree(ck, dk)}']
    for s in 'ABCD':
        if (y, s) in KEYS:
            k = KEYS[(y, s)]
            line.append(f'{s}: CSV {agree(ck, k, k)} DB {agree(dk, k, k)}')
    print('  ' + ' | '.join(line))
    series = {2018: 'C', 2019: 'B', 2020: 'C', 2021: 'C', 2022: 'A', 2023: 'A', 2024: 'D', 2025: 'A'}[y]
    k = KEYS[(y, series)]
    print(f'    DB != UPSC {series} (scorable):', [n for n in dk if k[n] != 'X' and dk[n] != k[n]],
          '| dropped by UPSC:', [n for n in k if k[n] == 'X'], 'stored there:', [dk.get(n) for n in k if k[n] == 'X'],
          '| CSV != DB:', [n for n in dk if ck.get(n) != dk[n]])

print('\nimport JSONs vs corpus (question text by number)')
for f in sorted(glob.glob('pyq_20*_prelims_gs1_*.json')):
    y = int(f[4:8])
    doc = json.load(open(f, encoding='utf-8'))
    j = {q['question_number']: q for q in (doc['questions'] if isinstance(doc, dict) else doc)}
    for q in j.values():  # the 2025 file is a flat list with option_a..option_d / correct_option
        if 'options' not in q:
            q['options'] = [{'label': l, 'text': q[f'option_{l}']} for l in 'abcd']
            q['correct_option_label'] = q.get('correct_option')
    corp = {r['question_number']: r for r in rows_all if r['year'] == y and r['subject_slug'] == GS_SLUG}
    same = sum(1 for n in corp if n in j and sim(norm(j[n]['question_text'])[:300], norm(corp[n]['question_text'])[:300]) >= 0.9)
    omap = sum(1 for n in corp if n in j and {o['label'].lower(): norm(o['text']) for o in j[n]['options']} ==
               {o['label'].lower(): norm(o['text']) for o in corp[n]['options']})
    jk = {n: (q.get('correct_option_label') or 'X').upper() for n, q in j.items()}
    dk = db_key(y)
    extra = ' | '.join(f'{s}: {agree(jk, KEYS[(y, s)], KEYS[(y, s)])}' for s in 'ABCD' if (y, s) in KEYS)
    print(f'  {f}: {len(j)} q; same question text as corpus by number {same}/{len(corp)}; '
          f'same option label->text map {omap}/{len(corp)}; JSON key~DB {agree(jk, dk)}; JSON key vs UPSC {extra}')
    if y == 2024:
        bk = {k: norm(q['stem'])[:400] for k, q in BK[2024].items()}
        hits = sum(1 for n, q in j.items() if max((sim(norm(q['question_text'])[:400], v), k) for k, v in bk.items())[1] == n)
        print(f'    2024 JSON questions whose best text match in the Series D booklet has the same number: {hits}/{len(j)}')
