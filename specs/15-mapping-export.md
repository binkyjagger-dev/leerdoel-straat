# 15 — Mapping export

Column names are chosen to map 1:1 onto the Doelstellr tables proposed in the
plan (methode, methode_eenheid, koppeling_paragraaf, opgave, koppeling_opgave).
`;`-delimited, UTF-8 BOM, quoted.

## 1. `output/methode_eenheden.csv` (one row per chapter/paragraph/exercise/sub-question)

| Column | Example |
|---|---|
| methode_id | lweo-economie-vwo-vraag-en-aanbod-2024 |
| eenheid_id | H2.3 |
| soort | paragraaf |
| code | 2.3 |
| titel | Kosten |
| ouder_id | H2 |
| pagina_van / pagina_tot | 24 / 27 |
| volgorde | 12 |

No text column.

## 2. `output/koppelingen_paragraaf.csv` (one row per link)

| Column | Example |
|---|---|
| run_id, bron_run (generate run) | |
| methode_id | |
| criterium_id / group_id / unit_id (syllabus) | D1.16-01-c / D1.16-01 / D1.16 |
| criterium_leerling | Ik kan TCK, TVK en TK berekenen … |
| criterium_bloom | toepassen |
| eenheid_id / code / titel / pagina | H2.3 / 2.3 / Kosten / 24 |
| behandeling | explains |
| gradatie | leert |
| citaat | ≤ 25 words |
| zekerheid | high |
| beoordelaar_a / beoordelaar_b / verifier | explains / explains / pass |
| opmerking | breidt uit |
| status | proposed |

## 3. `output/koppelingen_opgaven.csv` (part B; one row per sub-question × criterion)

criterium_id, eenheid_id (deelvraag), opgave_code, deelvraag_code, paragraaf_id,
pagina, bloom, citaat, antwoord_gecontroleerd, zekerheid, opmerking, status.

## 4. Reports

- `gaten_methode.md` — criteria in scope without *leert* (split: *alleen
  geoefend* / *niet in deze methode*), with the criterion text and, if any,
  the nearest candidate paragraph and why it was rejected.
- `buiten_syllabus.md` — paragraphs (and in part B: sub-questions) without a
  link, with title, page and the method's own concepts for that paragraph.
- `bloom_gaten.md` (part B) — criteria whose exercises never reach the
  criterion's Bloom level.
- `steekproef.md` — 14 §5.
- `vergelijking_nulmeting.md` — 14 §4, when a baseline file is given.
- `dekking_methode.md` — per paragraph: linked criteria by gradation; per
  criterion: leert / herhaalt / oefent counts; confidence distribution;
  decisions applied.

## 5. Run layout

```
runs/<run_id>/
  run.json                    subject, method_id, from_run, chapters, part
  input/*.pdf
  text/                       git-ignored: paragraph, question, answer texts
  10_criteria.json            copy of the generate run's 04_groups_student.json
  11_method_units.json  11_ingest_notes.md
  11b_intake_questions.json  decisions_snapshot.json
  12_candidates.json
  13_judgements.A/<unit>.json  13_judgements.B/<unit>.json  13_judgements.json (merged)
  14_mappings.json  14_findings.json
  15_verification.json  (15_repair.json)
  17_ex_candidates.json 18_ex_judgements.* 18_ex_mappings.json 19_ex_verification.json   (part B)
  output/
```
