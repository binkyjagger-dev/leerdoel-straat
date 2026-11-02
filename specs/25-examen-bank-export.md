# 25 — Exam bank and export

## 1. Layout (`subjects/<vak>/examenbank/`, committed)

```
examenbank/
  register.json          criteria_run, created_at, exams[]
  criteria.json          copy of the criteria run's 04_groups_student.json (the bank's criteria version)
  source_units.json      copy of its 01_source_units.json (domein/subdomein titles)
  links/<exam_id>.json   links of one exam (no exam text)
  output/                rebuilt by bank_export.py after every change
```

`runs/` is git-ignored, so the bank keeps its own copy of the criteria it is bound
to (written once, when the bank is created). Both bank scripts take `--bank <dir>`
(default `subjects/<subject>/examenbank`), used by the fixture test.

`register.json` (schema `exam_bank`):
```json
{"subject": "bedrijfseconomie", "criteria_run": "20261021-1647-bedrijfseconomie-vwo-2028-run2",
 "created_at": "2026-10-27",
 "exams": [{"exam_id": "vwo-2025-tv1", "code": "VW-0400-a-25-1", "year": 2025, "tijdvak": 1,
            "level": "vwo", "n_questions": 30, "max_score": 63, "syllabus_note": "…",
            "files": {"o": "input/examens-bedrijfseconomie-vwo/2025 TV1/vw-0400-a-25-1-o.pdf", "…": "…"},
            "added_by_run": "20261027-…", "added_at": "2026-10-27"}]}
```

`links/<exam_id>.json`: per scorepunt `{scorepunt_id, question_id, opgave_id, question_number,
opgave_number, opgave_title, scorepunt_seq, scorepunt_kind, points, criterion_id | null,
group_id, also_touches, bloom, bloom_verb, quote, confidence, verifier, note}`. No
question text beyond the quote.

## 2. Merge rules (`bank_add.py <run_dir>`)

- The run's `criteria_run` must equal the register's; else fail.
- A new `exam_id` is appended; an existing `exam_id` is replaced only with
  `--replace` (then the old file is kept as `links/<exam_id>.<date>.json`).
- Other exams' files are never touched (20 §6.4).

## 3. Outputs (`bank_export.py <subject>` → `examenbank/output/`)

`;`-delimited, UTF-8 with BOM, quoted. Exam columns in register order, named by
`exam_id`.

| File | Rows | Columns |
|---|---|---|
| `punten_per_criterium.csv` | one per criterion of the criteria run (+ rows *vaardigheid domein A* and *buiten huidige syllabus*) | criterium_id, leerdoel_id, criterium_leerling, criterium_bloom, then per exam: `<exam>_punten`, `<exam>_pct`, then per exam `<exam>_raakt_ook` (number of scorepunten with this criterion in `also_touches`; 0 points, not in the sums) |
| `punten_per_leerdoel.csv` | one per group (+ rows *vaardigheid domein A* and *buiten huidige syllabus*) | leerdoel_id, leerdoel_leerling, subdomein, then per exam punten / pct |
| `punten_per_domein.csv` | one per subdomein and per domein (column `niveau`) (+ rows *vaardigheid domein A* and *buiten huidige syllabus*) | niveau, code, titel, then per exam punten / pct |
| `opzoekindex.csv` | one per link (scorepunt), plus one per `also_touches` id of a link (`rol` *raakt ook*, `punten` 0, `raakt_ook` = the linked criterion), sorted by criterion, exam, question | criterium_id, leerdoel_id, criterium_leerling, examen, jaar, tijdvak, opgave, opgave_titel, vraag, scorepunt, punten, bloom_examen, bloom_criterium, citaat, raakt_ook, zekerheid, rol (*gekoppeld* / *raakt ook*) |
| `examenbank.xlsx` | the four tables above as sheets, header frozen, autofilter | only when `openpyxl` is installed |
| `overzicht.md` | per domein → leerdoel → criterium: points per exam and the questions (exam · vraag n · p; touched-only questions as *raakt ook*) | |
| `bevindingen.md` | *vaardigheid domein A* and *buiten huidige syllabus* (per exam: question, scorepunt, points, note), *examen boven/onder criterium*, *nooit getoetst* (criteria without any link in the bank) | |

Every exam column in the three point tables sums to the exam's `max_score` (the
*vaardigheid domein A* and *buiten huidige syllabus* rows included); `bank_export.py`
checks this and fails otherwise.

**Vaardigheid domein A** (bedrijfsecon-047, added 2026-11-02): a scorepunt without
criterion whose `note` contains *vaardigheid uit domein A* (the note text of
bedrijfsecon-043; case-insensitive, so *rekenvaardigheid uit domein A* counts) is
skill work from the syllabus's domein A, which has no criteria. Its points go to the
row *vaardigheid domein A*, not to *buiten huidige syllabus*.

**Raakt ook** (bedrijfsecon-046, added 2026-11-02): a scorepunt keeps one criterion
with all its points; the criteria in `also_touches` are shown with 0 points — the
`<exam>_raakt_ook` count per criterion, a *raakt ook* row in the lookup index and in
`overzicht.md`. A criterion that is only touched is not *nooit getoetst* but listed
under *alleen geraakt* in `bevindingen.md`.
