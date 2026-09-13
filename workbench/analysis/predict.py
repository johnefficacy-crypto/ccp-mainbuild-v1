import json, io, statistics
from collections import defaultdict, Counter

SUBJ = {'psir':'Political Science & International Relations','socio':'Sociology',
        'anth':'Anthropology','pubad':'Public Administration',
        'hist':'History','geog':'Geography'}

data = json.load(io.open('topic_years.json', encoding='utf-8'))
rows = defaultdict(list)
for key, ys in data.items():
    subj, paper, tid, name = key.split('|', 3)
    rows[(subj, int(paper))].append((tid, name, ys))

def measure(ys, lo, hi):
    Y = hi - lo + 1
    breadth = len(ys) / Y
    if len(ys) >= 3:
        gaps = [b - a for a, b in zip(ys, ys[1:])]
        cv = statistics.pstdev(gaps) / (statistics.mean(gaps) or 1)
        regularity = 1 - min(cv, 1.5) / 1.5
    else:
        regularity = 0.0
    last, third = max(ys), Y / 3
    recency = 1.0 if last >= hi - third else (0.5 if last >= hi - 2*third else 0.2)
    return 0.65*breadth + 0.25*regularity + 0.10*recency, breadth, regularity, recency

out = {}
for (subj, paper), items in sorted(rows.items()):
    allys = [y for _, _, ys in items for y in ys]
    lo, hi = min(allys), max(allys)
    scored = [dict(topic=n, years=ys, n=len(ys),
                   **dict(zip(('p','breadth','regularity','recency'),
                              [round(x,3) for x in measure(ys, lo, hi)])))
              for _, n, ys in items]
    scored.sort(key=lambda x: -x['p'])
    # Bands are PERCENTILE-BASED WITHIN THE PAPER. An absolute breadth cut
    # cannot work across papers: History P1 spreads ~660 questions over 127
    # topics and Sociology P1 spreads ~750 over 43, so the same raw breadth
    # means completely different things. Same lesson the v2.0 score model
    # learned about cohort normalisation.
    N = len(scored)
    for i, t in enumerate(scored):
        pct = i / N
        band = ('near_certain' if pct < 0.10 else
                'likely'       if pct < 0.35 else
                'occasional'   if pct < 0.75 else 'rare')
        # Percentile alone mislabels a tight syllabus: Sociology Paper I has 43
        # topics and almost all recur, so its bottom quartile still contains
        # topics asked in 12 separate years. Calling those 'rare' in a public
        # report would be plainly wrong. An absolute floor overrides the
        # percentile upward - never downward, so a sprawling paper like History
        # keeps its honest 'rare' tail.
        if band == 'rare' and t['breadth'] >= 0.12:
            band = 'occasional'
        if band == 'occasional' and t['breadth'] >= 0.40:
            band = 'likely'
        t['band'] = band
    out[f'{subj}_p{paper}'] = dict(subject=SUBJ[subj], paper=paper,
                                   span=f'{lo}-{hi}', years=hi-lo+1, topics=scored)

json.dump(out, io.open('predictability.json','w',encoding='utf-8'),
          indent=1, ensure_ascii=False)

print(f"{'paper':<11}{'topics':>7}{'span':>12}{'med yrs':>9}{'top topic asked':>16}")
for k, v in out.items():
    med = statistics.median(t['n'] for t in v['topics'])
    print(f"{k:<11}{len(v['topics']):>7}{v['span']:>12}{med:>9.0f}"
          f"{v['topics'][0]['n']:>12}y  {v['topics'][0]['topic'][:34]}")
