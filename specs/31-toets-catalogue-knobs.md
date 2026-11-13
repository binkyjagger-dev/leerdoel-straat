# 31 — Pattern catalogue and level knobs

## 1. Files (rules live in data)

```
data/toets/knobs.json              knob definitions (generic, all subjects)
data/toets/patterns_base.json      base layer: P01–P09, P12, P14, P15, P16
subjects/<s>/toets/patterns.json   subject layer (economie: P10, P11, P13; bedrijfseconomie: B01–B03)
subjects/<s>/toets/conventions.md  human: exam conventions of the subject (sources, uitwerkbijlage, cv phrases, € notation, btw)
subjects/<s>/toets/contexten.md    human, optional: preferred branches/settings, contexts to avoid
subjects/<s>/toets/seed_profile.json  seed reference profile (specs/26 §6), ignored once labels exist
```

`patterns_base.json` and `subjects/<s>/toets/patterns.json` are written only by
`scripts/toets/patterns.py` (seed + `add` against an answered decision). `conventions.md` and
`contexten.md` are written by humans, like `profile.md`. Statistics (frequency, examples) are not
stored here but computed into `examenbank/profiel/patronen_stats.json` (specs/26 §4).

Seed versions of all JSON files are delivered with this spec (`data/toets/*.json`,
`subjects/*/toets/patterns.json`) and come from the November 2026 analyses (economie 5 exams,
bedrijfseconomie 2 exams).

## 2. Pattern record

```json
{"code": "P08", "layer": "base", "name": "Berekening met zelf te vinden route",
 "kind": "calculation",                    // explanation | calculation | schema | drawing | choice
 "description": "De tussenstappen staan niet in de vraag; de leerling combineert gegevens uit tekst en bronnen.",
 "stem_forms": ["Bereken …", "Bereken … Gebruik informatiebron n en m."],
 "scoring": "1 punt per tussenstap of 'voor elke fout 1 scorepunt in mindering'",
 "points": [2, 4],                          // typical range in the central exam
 "bloom": ["toepassen", "analyseren"],      // levels this pattern can carry (scorepunt level)
 "solo": ["multistructureel", "relationeel"],
 "knobs_fixed": {"route": "zelf vinden"},   // a pattern can fix a knob value
 "needs_figure": false,
 "in_central_exam": true,
 "examples_seed": ["bedrijfseconomie vwo-2026-tv1 v15", "bedrijfseconomie vwo-2025-tv1 v9"]}
```

`kind` decides knob applicability: `route` applies to `calculation` and `schema`; `schema` applies to
`schema` (and to `drawing` when the drawing is a table to fill in). `knobs_fixed` makes some
combinations impossible: P07 fixes `route = gegeven`, P08 fixes `route = zelf vinden`. The planner
therefore satisfies the `route` share partly by the choice between P07 and P08 (specs/33 §3).

## 3. Seed catalogue (summary of the delivered JSON)

| Code | Layer | Name | Kind | Bloom | Points | Fixed |
|---|---|---|---|---|---|---|
| P01 | base | Mechanismeketen uitleggen | explanation | begrijpen, toepassen | 2 | |
| P02 | base | Keten met verplichte contextconditie | explanation | toepassen, analyseren | 2–3 | claim=nee |
| P03 | base | Stelling of conclusie onderbouwen | explanation | begrijpen, toepassen, analyseren | 2 | claim=ja |
| P04 | base | Begrip toetsen aan een casus (leg uit of) | explanation | toepassen | 2 | |
| P05 | base | Classificeren met onderbouwing | choice | begrijpen, toepassen | 1–2 | |
| P06 | base | Voorbeeld plus mechanisme | explanation | begrijpen | 2 | |
| P07 | base | Standaardberekening | calculation | toepassen | 1–3 | route=gegeven |
| P08 | base | Berekening met zelf te vinden route | calculation | toepassen, analyseren | 2–4 | route=zelf vinden |
| P09 | base | Berekenen en concluderen (bereken of / toon aan of) | calculation | toepassen, analyseren | 2–3 | |
| P12 | base | Afwegen en standpunt kiezen | explanation | analyseren, evalueren | 2 | |
| P14 | base | Noemen met toelichting in de context | explanation | begrijpen, toepassen | 1–2 | |
| P15 | base | Besluit aan de hand van meerdere voorwaarden | calculation | toepassen, analyseren, evalueren | 3–5 | builds_on=ja |
| P16 | base | Kennisvraag: noem of omschrijf | explanation | onthouden | 1–2 | in_central_exam=false |
| P10 | economie | Tekenen of arceren in een marktmodel | drawing | toepassen, analyseren | 1–3 | needs_figure |
| P11 | economie | Speltheorie: matrix of spelboom analyseren | choice | toepassen, analyseren | 2–3 | needs_figure (matrix as table) |
| P13 | economie | Dynamiek in het IS-MB-GA-model | explanation | toepassen, analyseren | 2–3 | |
| B01 | bedrijfseconomie | Effect van een financieel feit op een kengetal of overzicht | explanation | begrijpen, toepassen, analyseren | 2 | |
| B02 | bedrijfseconomie | Financieel overzicht opstellen in een gegeven schema | schema | toepassen | 2–4 | |
| B03 | bedrijfseconomie | Financiële rekenkunde met formuleblad | calculation | toepassen | 1–3 | |

Bloom per pattern is taken from where the analyses found it (economie: P02 46 points of which 32
analyseren; P07 29 points all toepassen; P06 only begrijpen). *Creëren* has no pattern; the form does
not offer it in the Bloom mix.

## 4. Knob record (`data/toets/knobs.json`)

```json
{"id": "route", "label": "Route", "ordinal": true,
 "values": ["gegeven", "zelf vinden"],
 "applies_to_kinds": ["calculation", "schema"],
 "definition": {"gegeven": "de vraag noemt de tussenstappen ('bereken hiervoor eerst …') of het schema bevat de rijen",
                "zelf vinden": "de vraag noemt alleen het eindpunt"},
 "label_evidence": "the stem sentence that gives or omits the intermediate steps",
 "settable": true}
```

Knobs: `pattern` (categorical, values = catalogue codes), `solo`, `route`, `steps`, `sources`,
`claim`, `new_concept`, `schema`, `builds_on` (settable), and `combination` (computed, shown in the
form and the verantwoording, not settable). The definitions are the ones used in the November 2026
tests (instructie_beco_5vwo §Niveauprofiel), merged for both subjects:

- `sources` replaces the economie test's "context" knob: *in vraagtekst* = all data in the stem;
  *één bron zonder ruis* = one numbered source whose data are all used; *meerdere bronnen met ruis* =
  two or more sources, also holding data the vraag does not need.
- `claim` replaces the "met bewering" half of the economie test's context knob.
- `steps`: values `1`, `2`, `3`, `4+`; counted as the reasoning or calculation steps of a complete
  answer (one scorepunt is not necessarily one step).

## 5. Compatibility rules (checked by `blueprint_check.py`, specs/34 §2)

- A scorepunt's Bloom level must be in its vraag's pattern `bloom` list.
- A scorepunt's Bloom level must be ≤ the criterion's Bloom level + 1 (the +1 allowance of
  `/generate`; the exam bank shows exams test higher than the criterion on 41 % of linked points in
  economie). A higher level is a blueprint error.
- `knobs_fixed` values are binding; a knob that does not apply to the pattern's kind is `null`.
- `builds_on = ja` requires an earlier vraag in the same opgave whose outcome is used.
- `new_concept = ja` requires the concept to be defined in the stem or a source (the writer states it
  in `new_concepts[]`; the verifier checks it is outside the criteria and explained, V7).
- `needs_figure` patterns require a figure spec in the items (specs/35 §3).
- P16 counts as `in_central_exam = false`: its points appear in the verantwoording as
  "niet-examenpatroon".

## 6. Adding or changing a pattern

1. A labeller (specs/26 §3.4), the verifier (specs/34 §5) or the teacher proposes a pattern.
2. It becomes an open decision (`applies_to: ["catalogue"]`) with the proposed record as context.
3. After the teacher answers it, `python3 scripts/toets/patterns.py add <subject|base> <decision-id>
   <record.json>` validates the record (`schemas/patterns.schema.json`) and writes it.
   `patterns.py retire <code> <decision-id>` marks a pattern `retired` (never deleted: labels in the
   bank still refer to it).
4. The next `profile_build.py` recomputes the statistics.
