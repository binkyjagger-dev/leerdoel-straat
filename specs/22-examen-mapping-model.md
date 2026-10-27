# 22 — Exam mapping model

## 1. Link (one per scorepunt)

```json
{"scorepunt_id": "vwo-2025-tv1-q6-s2", "question_id": "vwo-2025-tv1-q6", "exam_id": "vwo-2025-tv1",
 "criterion_id": "B2.12.2-03-b", "group_id": "B2.12.2-03", "points": 1,
 "bloom": "toepassen", "bloom_verb": "berekenen",
 "quote": "Bereken voor Camping Vogelhof de omzet in 2024 uit de verhuur van standplaatsen.",
 "also_touches": ["B1.11.1-02-a"], "answer_checked": true,
 "confidence": "high", "confidence_judged": "high", "judges": {...}, "verifier": null, "status": "proposed"}
```

- **Exactly one criterion per scorepunt**, or none (`criterion_id: null`, a finding).
  A second criterion the scorepunt touches goes to `also_touches` (0–2 ids), without
  points (decision 20 §5.1).
- `points` is copied from the scorepunt; judges never set points.
- `quote`: verbatim from the **question text** (`<exam>-q<n>.txt`), ≤ 25 words, the
  sentence that carries the ask. Scorepunten of one question normally share the quote.
  The scorepunt's own line (correctievoorschrift) is evidence for the judge but is not
  the quote.
- Scorepunten of one question may link to different criteria (a calculation and an
  explanation); `per_item` scorepunten of one question normally link to the same one.

## 2. What a scorepunt "tests"

The criterion whose performance a candidate must deliver to earn **this** scorepunt,
judged against the criterion's expert text:
- the scorepunt line decides (e.g. "• 41.460 en 84.000 en 50.680" is the weekly
  revenue step, not the whole revenue criterion), the question text gives context;
- a scorepunt that only rewards using a given number or a term practises nothing
  about it;
- a performance outside every criterion (e.g. a spreadsheet skill, content dropped
  from the syllabus) ⇒ no criterion, finding *buiten huidige syllabus*.

## 3. Bloom

As for exercises (12 §6, 6.2): `bloom` is the level the scorepunt actually asks, via
the asking verb (`bloom_verb`, infinitive) in the subject's effective verb table
(`load_bloom_rules`), corrected by the correctievoorschrift where the verb gives none:
a scorepunt whose model answer is a calculation result (number with `=`, `€`, `%` not
given in the question) ⇒ at least *toepassen*; a "leg uit"/"verklaar" scorepunt
answered with a mechanism ⇒ *begrijpen*/*analyseren*. "Analyseer"/"beoordeel"
questions: the level of the question applies to the scorepunt that carries the
conclusion; supporting calculation scorepunten are *toepassen*.

## 4. Merge and confidence (E4)

Judges A and B each give, per scorepunt, `criterion_id` (or null), `bloom`,
`bloom_verb`, `quote`, `also_touches`, `answer_checked`. Repair judge R may set or
clear the criterion of the scorepunten it re-judges; R decides (as 12 §6.2).

| A vs B on a scorepunt | confidence |
|---|---|
| same criterion, same `bloom`, both quotes valid | **high** |
| same criterion, `bloom` differs or one quote invalid | medium |
| different criteria, or one null | low — criterion of A, B's in `alt_criterion`; always in the verifier's sample |
| both null | no link (finding) |
| both quotes invalid | voided |

Bloom on disagreement and MB1/MB2 as 12 §6.2. `also_touches` = union of A and B
minus the linked criterion.

## 5. Findings (`24_findings.json`)

| Finding | When |
|---|---|
| *buiten huidige syllabus* | scorepunt without criterion (with points) |
| *examen boven criterium* | link `bloom` > criterion `bloom` |
| *examen onder criterium* | link `bloom` < criterion `bloom` |
| *nooit getoetst* | (bank level, 25 §4) criterion without links in any exam of the bank |

## 6. Aggregation

- Criterion × exam: Σ `points` of its links; % = points / exam `max_score` × 100.
- Group (leerdoel) = Σ over its criteria; subdomein / domein = Σ over groups by
  `unit_id` prefix from the source units of the criteria run.
- Unlinked points per exam are reported as a separate row (*buiten huidige
  syllabus*) so every column sums to the exam's maximum score.
