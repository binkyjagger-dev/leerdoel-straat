# 05 — Export and run layout

## 1. Provisional CSV schema (`output/leerdoelgroepen.csv`)

One row per **criterion**; goal fields repeat. This keeps Bloom on the
criterion (where it lives) and makes the file trivially pivotable. Columns are
provisional; they will be redefined when the Doelstellr import is designed.

| Column | Example | Notes |
|---|---|---|
| run_id | 20261011-1100-economie-vwo | |
| source_id | cvte-economie-vwo-2027 | |
| source_type | syllabus | syllabus / textbook |
| domein_code | D | top-level ancestor code |
| domein_titel | Concept markt | |
| subdomein_code | D1 | may be empty |
| subdomein_titel | Vraag en aanbod | |
| unit_id | D1.1 | leaf id (eindterm / paragraaf) |
| unit_tekst | De kandidaat kan … | literal leaf text |
| group_id | D1.1-01 | |
| leerdoel_expert | De leerling kan verklaren … | |
| leerdoel_leerling | Ik kan uitleggen … | |
| leerdoel_bloom | begrijpen | computed max |
| criterium_id | D1.1-01-a | |
| criterium_volgorde | 1 | |
| criterium_expert | Benoemt dat … | |
| criterium_leerling | Ik kan benoemen dat … | |
| criterium_bloom | onthouden | |
| criterium_bloom_werkwoord | benoemen | |
| bron_citaat | … verklaren hoe prijsvorming … | verbatim |
| status | pass / revise / reject | final verdict |
| verificatie_opmerking | | issues joined, empty when pass |

Encoding UTF-8, `;` delimiter (Dutch Excel default), quoted fields, header row.
A second file `leerdoelgroepen_per_leerdoel.csv` with one row per group (no
criteria columns, criteria concatenated with ` | `) is written as a
convenience for quick reading.

## 2. Coverage report (`output/coverage_report.md`)

- Header: run id, source, date, rounds, totals, coverage %.
- Table per domein: subdomein / eindterm → planned, produced, Bloom levels
  present, status.
- List of uncovered units (should be empty).
- Bloom distribution across all criteria (counts per level) — informational,
  no target.

## 3. Run folder layout

```
runs/<run_id>/
  run.json
  input/syllabus.pdf
  01_source_units.json
  01_ingest_notes.md
  02_plan.json
  03_groups_raw/<unit_id>.json
  03_groups_raw.json
  04_groups_student.json
  05_verification.round1.json
  05_verification.round2.json   (if a repair round ran)
  coverage.json
  output/
    leerdoelgroepen.csv
    leerdoelgroepen_per_leerdoel.csv
    coverage_report.md
    doubt_list.md
```

Every file in a run is kept; nothing is overwritten except `goal.bloom`
(computed) and the per-unit raw files that a repair round replaces (the
previous version is kept as `<unit_id>.round1.json`).
