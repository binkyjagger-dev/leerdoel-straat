# 25 — Exam bank and export

## 1. Layout (`subjects/<vak>/examenbank/`, committed)

```
examenbank/
  register.json          criteria_run, created_at, exams[]
  links/<exam_id>.json   links of one exam (no exam text)
  output/                rebuilt by bank_export.py after every change
```

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
| `punten_per_criterium.csv` | one per criterion of the criteria run (+ row *buiten huidige syllabus*) | criterium_id, leerdoel_id, criterium_leerling, criterium_bloom, then per exam: `<exam>_punten`, `<exam>_pct` |
| `punten_per_leerdoel.csv` | one per group | leerdoel_id, leerdoel_leerling, subdomein, then per exam punten / pct |
| `punten_per_domein.csv` | one per subdomein and per domein (column `niveau`) | niveau, code, titel, then per exam punten / pct |
| `opzoekindex.csv` | one per link (scorepunt), sorted by criterion, exam, question | criterium_id, leerdoel_id, criterium_leerling, examen, jaar, tijdvak, opgave, opgave_titel, vraag, scorepunt, punten, bloom_examen, bloom_criterium, citaat, raakt_ook, zekerheid |
| `examenbank.xlsx` | the four tables above as sheets, header frozen, autofilter | only when `openpyxl` is installed |
| `overzicht.md` | per domein → leerdoel → criterium: points per exam and the questions (exam · vraag n · p) | |
| `bevindingen.md` | *buiten huidige syllabus* (per exam: question, scorepunt, points, note), *examen boven/onder criterium*, *nooit getoetst* (criteria without any link in the bank) | |

Every exam column in the three point tables sums to the exam's `max_score` (the
*buiten huidige syllabus* row included); `bank_export.py` checks this and fails
otherwise.
