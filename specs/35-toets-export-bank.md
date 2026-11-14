# 35 — Toets-straat: export, figures, toetsbank

## 1. Outputs (`export_toets.py R` → `R/output/`)

| File | Contents |
|---|---|
| `<slug>-leerling.docx` / `.md` | Cover (title, level, duration, number of vragen, maximum score), opgaven with vragen ("2p **3** Bereken …"), then *Informatiebronnen* (numbered, per opgave) and the *Uitwerkbijlage* (tables to fill in, figures without answer lines) on separate pages |
| `<slug>-correctievoorschrift.docx` / `.md` | CvTE style: per vraag `maximumscore n`, model answer, scorepunten with bullets, rules, alternatives, follow-through sentence; figures with answer lines |
| `<slug>-verantwoording.docx` / `.md` | §2 |
| `bouwplan.md` | from T2b, final version after the review |
| `twijfellijst.md` | specs/34 §6 |
| `figuren/*.png` | every figure, student and cv version |
| `toets.json` | the toets as one file (items + labels + realised values), the same record that goes into the toetsbank |

Word is built with **python-docx** (one Python stack in this repo). Layout: A4, Arial 11, margins 2 cm,
tables with a light header fill, page break before the sources and before the uitwerkbijlage, figures
at 14 cm width. The Markdown versions are the source; the docx builder renders the same structure.
Verify: convert to PDF (LibreOffice, when available) and check the page count is > 0. On Windows, an
open file blocks the write (CLAUDE.md lesson): ask the teacher to close it.

## 2. The verantwoording (Dutch)

1. **Opdracht**: matrix, Bloom mix, knob shares as ordered; reference used ("2 examens: 2025-I,
   2026-I").
2. **Matrijs**: per leerdoel planned points vs realised points (always equal) and per criterion the
   points and vragen; untested criteria of each leerdoel.
3. **Bloom-mix**: per level, planned (order) · blueprint · realised · central exam (linked points of
   the bank), in points and %. Values outside tolerance are marked.
4. **Knoppen**: one table per knob, with columns value · **gepland (opdracht)** · bouwplan ·
   **gerealiseerd (gelabeld)** · **centraal examen** (pooled, plus the spread over exams). Values
   outside tolerance are marked, with the reason when accepted at pause 2 or left after repair.
5. **Per vraag**: number, points, pattern, criteria per scorepunt, Bloom, knobs planned → realised,
   context, open findings.
6. **Patronen**: points per pattern, toets vs central exam; P16 points as *niet-examenpatroon*.
7. **Controle**: check results, solver matches, verifier rounds, doubt list count.

All figures come from `31_order.json`, `32_blueprint.json`, `34_realized.json` and
`30_reference_profile.json`; the export script computes nothing an agent wrote in prose.

## 3. Figures (`figures.py`, matplotlib)

The writer delivers a spec, never an image:
```json
{"figure_id": "f1", "type": "market_model",               // market_model | line_chart | bar_chart | game_matrix | flow
 "title": "Markt voor ...", "x": {"label": "hoeveelheid (× 1.000)", "min": 0, "max": 100},
 "y": {"label": "prijs (€)", "min": 0, "max": 50},
 "lines": [{"label": "Qv", "points": [[0, 40], [80, 0]]}, {"label": "Qa", "points": [[0, 10], [60, 40]]}],
 "points": [], "areas": [], "grid": true}
```
`answer_spec` holds the extra lines, points and hatched areas of the cv version (P10: the shifted line,
the area to hatch). Every coordinate must be a `data` value or a `calc` result (FG, specs/34 §3).
`game_matrix` and simple tables are rendered as Word tables, not images. Output: `figures/<id>.png`
(student) and `figures/<id>-cv.png`, 200 dpi, black and grey only (they must print well).

## 4. Toetsbank (`subjects/<s>/toetsbank/`, committed)

```
toetsbank/
  register.json            criteria_run, toetsen[] {toets_id, title, level, run_id, created_at, max_score, n_opgaven, n_vragen, reference}
  toetsen/<toets_id>.json  = output/toets.json (items, blueprint per vraag, labels, realised values, findings left)
  contexts.json            history: [{toets_id, opgave_id, title, context_tags, level, date}]
  output/overzicht.md      rebuilt: per leerdoel/criterion the opgaven that test it, per pattern the count
```

- `toetsbank_add.py R` appends; an existing `toets_id` is replaced only with `--replace` (old file
  kept with a date suffix), as `bank_add.py`.
- The toetsbank is bound to the criteria run like the exam bank. A new criteria run ⇒ a new toetsbank;
  the old one is moved to `toetsbank.<criteria_run>/` (ask first, the one destructive step, as `/examen
  --rebuild`). Contexts carry over to the new bank's history.
- **Reuse**: an order's `reuse` entries copy an opgave verbatim (specs/32 §1). The new toets records
  `reused_from` per opgave. A reused opgave is not re-verified unless the criteria run changed, which
  cannot happen inside one bank.
- **Context history**: `30_context_history.json` is `contexts.json` filtered to the last 24 months
  (default; a subject decision can change this).
- The toetsbank holds no exam text; style examples stay in the run folder.

## 5. Later (designed for, not in v1)

- Nakijkr export (JSON per vraag with scorepunten and model answer) once the Nakijkr import format is
  fixed.
- HAVO: a HAVO exam bank gives a HAVO reference profile; `level` gets `4havo`/`5havo`.
- Parallel versions (A/B toets) via `--from-blueprint` with a writer instruction for different
  numbers and context.
