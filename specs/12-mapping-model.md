# 12 — Mapping model

## 1. Link (paragraph level)

One link = one criterion × one paragraph.

```json
{
  "criterion_id": "D1.16-01-c",
  "group_id": "D1.16-01",
  "unit_id": "H2.3",                      // method paragraph
  "treatment": "explains",               // judge output: explains | practises | mentions
  "gradation": "leert",                  // script output: leert | herhaalt | oefent | noemt
  "quote": "De totale kosten zijn de som van de constante en de variabele kosten …",
  "quote_page": 24,
  "confidence": "high",                  // high | medium | low  (§4)
  "judges": {"A": "explains", "B": "explains"},
  "note": null,                          // e.g. "breidt uit"
  "status": "proposed"                   // proposed | confirmed | rejected  (teacher, in Doelstellr later)
}
```

## 2. Treatment (judged) → gradation (computed)

Judges answer, per criterion × candidate paragraph, **what the paragraph does
with the criterion**:

| treatment | meaning | evidence required |
|---|---|---|
| `explains` | introduces or explains what the criterion asks: definition, mechanism, worked method | quote from running text that explains it |
| `practises` | applies or calculates it without explaining it again (worked example, exercise text in the paragraph) | quote from the application |
| `mentions` | the term occurs (box, forward reference, aside) but the criterion is neither explained nor practised | quote containing the term |
| `none` | not present | — (no link) |

The gradation script (`scripts/mapping/gradation.py`) then assigns, per
criterion, over all its links sorted by paragraph `order`:

- first `explains` → **leert**; later `explains` → **herhaalt** (note
  "breidt uit" when the judge flagged a different aspect);
- `practises` → **oefent** (before the *leert* paragraph as well — then note
  "oefent vóór uitleg", a method-order finding);
- `mentions` → **noemt** (stored, not shown to students, never counts as first).

Exactly one *leert* per criterion. A criterion with links but no `explains`
goes to the method gap report as *alleen geoefend*; a criterion with no links
at all as *niet in deze methode*.

## 3. Quotes

- Verbatim substring of the paragraph text, ≤ 25 words, whitespace-insensitive;
  when `text_extraction` is `ocr`, matching tolerates a character error rate
  of ≤ 5 % (`scripts/mapping/quote_check.py`, Levenshtein on the normalised
  window). A quote that fails the check voids the link (the judgement stays
  in the file as `invalid_quote` for audit).
- One quote per link. Judges may propose two when `explains` spans two
  places; the script keeps the first and stores the second in `note`.

## 4. Confidence

Two judges (A, B) in fresh contexts, same input, no knowledge of each other.

| A vs B | confidence |
|---|---|
| same treatment, both quotes valid | **high** |
| same treatment, one quote invalid | medium |
| `explains` vs `practises` (either order) | medium — treatment = the one with the stronger quote per verifier; else `practises` |
| one says `none` | low — link kept with the non-none treatment, flagged |
| `mentions` vs anything stronger | low |
| both `none` | no link |

The verifier (14 §3) may raise or lower confidence by one step with a
reason. `low` links go to the sample list regardless.

## 5. Ownership across criteria

A paragraph may explain several criteria (normal). A criterion is explained by
exactly one *leert* paragraph (rule above). Criteria of the same group usually
share paragraphs; that is expected and not a finding. Two criteria of
*different* groups that get the same quote is a finding (J-M5), because the
quote then does not discriminate.

## 6. Part B: exercise link

```json
{"criterion_id": "D1.16-01-c", "unit_id": "H2.3-opg7b", "bloom": "toepassen",
 "quote": "Bereken de totale kosten bij een productie van 400 stuks.", "answer_checked": true,
 "confidence": "high", "judges": {...}, "status": "proposed"}
```

- Candidates for a sub-question = criteria that its own paragraph or any
  earlier paragraph *leert* or *oefent* (part A result), ranked by concept
  overlap. Usually 1 criterion, at most 2 (then both links, note "tevens").
- `bloom` = level of what the question actually asks, from the verb table in
  force for the subject; when the answer is available, the answer form
  corrects the verb (a number as answer ⇒ at least *toepassen*; "leg uit"
  with a mechanism answer ⇒ *begrijpen*/*analyseren*).
- A sub-question that matches no criterion is a finding (*oefenstof buiten
  syllabus*), not an error.
