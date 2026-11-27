"""Proef step 5: blind comparison of two toetsen, grouped per leerdoel, shuffled, without origin."""
# Ad-hoc tool of the proef (2026-11-27), kept until specs/38 builds blind_compare.py. Run from the repo root.
import json, glob, random, sys
from collections import Counter

NEW = 'runs/20261125-2236-proef-kennis-bedrijfseconomie'
OLD = 'runs/20261119-0943-toets-bedrijfseconomie'
OUT_MD = NEW + '/output/blind-vergelijking.md'
OUT_KEY = NEW + '/blind-sleutel.json'

crit = json.load(open(NEW + '/30_criteria.json', encoding='utf8'))
goal = {g['group_id']: g['goal']['text_student'] for g in crit['groups']}


def load(run, origin):
    out = []
    for f in sorted(glob.glob(run + '/33_items/O?.json')):
        d = json.load(open(f, encoding='utf8'))
        for v in d['vragen']:
            pts = Counter()
            for s in v['cv']['scorepunten']:
                pts['-'.join(s['criterion_id'].split('-')[:2])] += s['points']
            group = sorted(pts.items(), key=lambda x: (-x[1], x[0]))[0][0]
            out.append({'origin': origin, 'run': run.split('/')[-1], 'opgave': d, 'v': v, 'group': group})
    return out


def table_md(rows):
    lines = ['| ' + ' | '.join(str(c) for c in rows[0]) + ' |', '|' + '---|' * len(rows[0])]
    lines += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows[1:]]
    return '\n'.join(lines)


items = load(NEW, 'nieuw') + load(OLD, 'oud')
rng = random.Random(20261127)

# contexts get neutral letters, shuffled over both toetsen
opg = {}
for it in items:
    opg.setdefault((it['run'], it['opgave']['opgave_id']), it['opgave'])
keys = list(opg)
rng.shuffle(keys)
letter = {k: chr(ord('A') + i) for i, k in enumerate(keys)}

groups = sorted({it['group'] for it in items})
lines = ['# Blinde vergelijking — vragen per leerdoel', '',
         'Beoordeel elke vraag als **goed**, **aanpassen** of **weg** (eventueel met een opmerking). '
         'De vragen komen uit twee toetsen en zijn per leerdoel geschud; de herkomst staat er niet bij. '
         'De context van elke vraag staat achterin onder de letter. Verwijzingen als "je antwoord op vraag 9" '
         'gaan over de nummering in de oorspronkelijke toets.', '']
n = 0
key = []
for g in groups:
    its = [it for it in items if it['group'] == g]
    rng.shuffle(its)
    lines += [f'## {g} — {goal.get(g, "")}', '']
    for it in its:
        n += 1
        v = it['v']
        k = (it['run'], it['opgave']['opgave_id'])
        key.append({'nr': n, 'origin': it['origin'], 'run': it['run'], 'vraag_id': v['vraag_id'], 'group': g})
        lines += [f'### {n}. ({v["points"]}p) — context {letter[k]}', '']
        if v.get('lead'):
            lines += [v['lead'], '']
        lines += [f'**{v["task"]}**', '']
        lines += ['*Correctievoorschrift*', '']
        for s in v['cv']['scorepunten']:
            lines.append(f'- {s["text"]} ({s["points"]}p)')
        lines += ['', 'Oordeel: goed / aanpassen / weg — opmerking:', '']

lines += ['---', '', '# Contexten', '']
for k in sorted(keys, key=lambda k: letter[k]):
    d = opg[k]
    lines += [f'## Context {letter[k]}: {d["title"]}', '', d['intro'], '']
    for s in d.get('sources') or []:
        lines += [f'**Informatiebron {s.get("n")}: {s.get("title", "")}**', '']
        if s.get('table'):
            lines += [table_md(s['table']), '']
        if s.get('text'):
            lines += [s['text'], '']
    if d.get('figures'):
        lines += [f'*(Deze context heeft {len(d["figures"])} figuur/figuren; zie de leerlingversie.)*', '']

open(OUT_MD, 'w', encoding='utf8').write('\n'.join(lines))
json.dump({'note': 'Sleutel blinde vergelijking proef stap 5; niet aan de docent tonen voor het oordeel.',
           'seed': 20261127, 'contexts': {letter[k]: list(k) for k in keys}, 'items': key},
          open(OUT_KEY, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print(n, 'vragen,', len(groups), 'leerdoelen,', len(keys), 'contexten', Counter(i['origin'] for i in key))
for g in groups:
    print(g, Counter(i['origin'] for i in key if i['group'] == g))
