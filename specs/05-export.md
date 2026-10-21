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
| examen | CE+SE | CE / SE / CE+SE from the source's allocation table (01 §2 P4), inherited from the (sub)domein; empty when the source has no table |
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
| kernbegrippen | evenwichtsprijs \| vraag \| aanbod | the group's `concepts` (02 §5), joined with ` \| `; repeats per criterion row |
| status | pass / revise / reject | final verdict |
| verificatie_opmerking | | issues joined, empty when pass |

Encoding UTF-8, `;` delimiter (Dutch Excel default), quoted fields, header row.
A second file `leerdoelgroepen_per_leerdoel.csv` with one row per group (no
criteria columns, criteria concatenated with ` | `) is written as a
convenience for quick reading; it carries `examen` as well, after `unit_id`,
and `kernbegrippen` after `succescriteria_leerling`.

## 2. Coverage report (`output/coverage_report.md`)

- Header: run id, source, date, rounds, totals, coverage %; when the source
  has an allocation table also the split of leaves over CE / SE / CE+SE.
- Table per domein: subdomein / eindterm → examen, planned, produced, Bloom
  levels present, status.
- *Niet in deze bron*: the allocation rows with `ingested: false` (SE-only
  (sub)domeinen a CE syllabus does not specify), code and title, so the
  teacher sees what the school exam still has to cover from another source.
- Concept coverage (C3) when the source has concept lists: totals and the
  list *Begrippen zonder leerdoel* per unit.
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
