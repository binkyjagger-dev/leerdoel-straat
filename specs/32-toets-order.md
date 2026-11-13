# 32 — The order (toetsopdracht), the form and the button dialogue

## 1. The order (`toetsopdracht.json`, schema `toets_order`)

```json
{"subject": "bedrijfseconomie", "level": "5vwo", "title": "Toets F2 Kosten en winst",
 "criteria_run": "20261021-1647-bedrijfseconomie-vwo-2028-run2",
 "n_opgaven": 3, "n_vragen": 11,
 "duration_minutes": 50,                                   // optional, goes to the student version
 "matrix": [{"group_id": "F2.30.3-01", "points": 6},
            {"group_id": "F2.30.4-01", "points": 9},
            {"group_id": "F2.31.1-01", "points": 12}],
 "criteria_include": null,                                 // optional: restrict to these criterion ids
 "criteria_exclude": ["F2.30.3-01-d"],                     // optional
 "bloom_mix": {"onthouden": 0, "begrijpen": 0.25, "toepassen": 0.55, "analyseren": 0.20, "evalueren": 0},  // optional, by points
 "knobs": {
   "pattern":     {"P07": 0.25, "P08": 0.15, "B02": 0.30, "P14": 0.15, "P15": 0.15},   // or "vrij"
   "solo":        {"multistructureel": 0.6, "relationeel": 0.4},
   "route":       {"gegeven": 0.6, "zelf vinden": 0.4},
   "steps":       {"1": 0.2, "2": 0.4, "3": 0.3, "4+": 0.1},
   "sources":     {"in vraagtekst": 0.3, "één bron zonder ruis": 0.5, "meerdere bronnen met ruis": 0.2},
   "claim":       {"nee": 0.8, "ja": 0.2},
   "new_concept": {"nee": 1.0},
   "schema":      {"voorgestructureerd": 0.7, "deels ingevuld": 0.3},
   "builds_on":   {"nee": 0.5, "ja": 0.5}},
 "contexts": [{"opgave": 1, "context": null}],             // optional: a fixed context per opgave
 "avoid_contexts": ["fietsen", "verzekeringen"],           // optional, on top of the history
 "reuse": [],                                              // optional: [{"toets_id": "...", "opgave_id": "..."}] from the toetsbank
 "reference": "bank-2-examens",                            // filled by the straat: which reference profile was shown
 "conventions": {"btw": 0.21}}                             // optional subject-convention overrides
```

Rules:
- `matrix` totals give the toets's maximum score. A group with points must exist in the criteria run.
- `bloom_mix` is optional. When it is absent, the planner chooses the Bloom level per scorepunt within
  pattern and criterion limits, and the verantwoording shows the result.
- Every knob is either a share map (values sum to 1.0 ± 0.001) or the string `"vrij"` (the planner
  chooses). The form and the dialogue always show the reference next to it. There is **no implicit
  default**: a knob missing from the file is asked in the dialogue (§3).
- Shares are **by points**, conditional on applicability (as the reference profile, specs/26 §4):
  `route` over the points of calculation and schema vragen, `schema` over schema vragen, `builds_on`
  over vragen that are not the first of their opgave.
- `level` (`4vwo` | `5vwo` | `6vwo`) sets no knob. It goes to the planner and writer for student
  language, the complexity of the context and the numbers.
- `reuse`: reused opgaven are taken verbatim (stem, sources, vragen, cv). Their points count in the
  matrix and their labels count in the shares. The planner plans only the remainder.
- An order can be saved as a template: `subjects/<s>/toets/sjablonen/<name>.json` (same schema, without
  `title`, `contexts`, `reuse`). The form can load a template.

## 2. The form (`/toets --formulier <subject>` → `scripts/toets/form_build.py`)

One self-contained HTML file `subjects/<s>/toets/toetsformulier-<s>.html` (git-ignored, rebuilt on
demand). It embeds, as JSON in a `<script>` tag:
- the leerdoelen and criteria of the bank's criteria version (id, student text, Bloom, subdomein);
- the reference profile (or the seed, labelled "voorlopig"), per knob value, pooled and per exam;
- the catalogue (base + subject), with name, kind and Bloom list;
- the context history (last 20 contexts) and the templates.

Sections (Dutch UI):
1. **Toets**: title, level (buttons 4/5/6 VWO), number of opgaven, number of vragen, duration.
2. **Toetsmatrijs**: the leerdoelen grouped per domein → subdomein, a points field per leerdoel, a
   live total; per leerdoel a fold-out of its criteria with Bloom and an exclude checkbox.
3. **Bloom-mix** (optional toggle): a slider per level with the live points per level, and
   the central-exam mix of the linked points next to it.
4. **Knoppen**: per knob a row of value buttons with a slider per value (shares sum to 100 %).
   Next to it, in grey, the **central-exam share** and per-exam spread ("eindexamen: 62 %, 2025-I 58 %,
   2026-I 66 %"). Buttons per knob: *Zet op eindexamen*, *Vrij*, *Reset*. Not-applicable notes
   ("telt alleen over rekenvragen").
5. **Contexten**: optional fixed context per opgave, extra contexts to avoid; the history is shown.
6. **Hergebruik**: optional opgaven from the toetsbank (list with title, points, leerdoelen).
7. **Download** `toetsopdracht.json` (+ *Opslaan als sjabloon* downloads a template file).

Light validation in the page itself: the matrix total is > 0, shares sum to 100 %, the number of
vragen is ≥ the number of opgaven. The full validation is `validate_toets.py order` in T1.
No network calls; works from `file://`. Storage: none required. If a draft is remembered, use
`localStorage` inside try/catch only.

## 3. The button dialogue (T1 in `/toets`)

`/toets [<toetsopdracht.json>] --subject <s>`:

- Without a file: ask everything except the matrix with AskUserQuestion. The matrix cannot be entered
  well with buttons, so the orchestrator then runs `form_build.py`, gives the path and stops. It
  offers to continue with a matrix given in chat (`F2.30.3-01: 6, …`), which it transcribes, reads back
  and writes.
- With a file: validate it, then ask only for the missing or `null` fields, ≤ 4 per AskUserQuestion
  call. Per knob, offer 3–4 options built from the reference: *Zoals eindexamen (62 % zelf vinden)*,
  *Lichter (≈ 30 %)*, *Zwaarder (≈ 80 %)*, *Vrij*. The teacher can always type their own shares.
- Then read the whole order back in a short Dutch summary (matrix total, Bloom mix, per knob order vs
  reference) and ask: **Akkoord / Aanpassen**. This is **pause 1**. The confirmed order is
  `R/31_order.json`; the teacher's file is copied to `R/input/toetsopdracht.json`.

## 4. Tolerances (decided 2026-11-13)

| What | Planned vs blueprint (T2) | Planned vs realised (T5) |
|---|---|---|
| Points per leerdoel | exact | exact |
| Total points, number of opgaven and vragen | exact | exact |
| Bloom mix per level | ±5 pp | ±5 pp |
| Knob shares per value | ±10 pp | ±10 pp |

Slack rule: a deviation is still within tolerance when moving one vraag (or one scorepunt for Bloom)
to the right value would overshoot on the other side. This matters for a small toets: with 10 points of
calculation vragen, one 3-point vraag is already 30 pp.

At T2, a deviation outside tolerance is a blueprint error (the planner repairs). At T5 it is a verifier
finding (V9) and gets a repair; after 2 rounds it goes to the verantwoording with the reason.
