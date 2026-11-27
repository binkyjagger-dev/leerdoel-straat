# 38 — Toets-straat v3: knowledge-driven toets (misconceptions, exam mechanisms, variants)

**Status:** approved 2026-11-27 (§2.1 and §2.2 decided by Martijn; one open question in §11). Amends specs/06, 26, 30, 31, 32, 33, 34 and 35. Where this
spec and an older one differ, this spec wins. It takes over specs/37 D10 (`focus` per leerdoel, §5.4). The rest of
specs/37 stays a separate spec, still on hold. Domain language is English; teacher-facing text is Dutch.

**Order of work.** Spec approved 2026-11-27; build in the order of §10.

## 1. Why: the proef of 2026-11-25/27

Plan: `docs/proef-kennisgestuurde-toets.md`. Run: `runs/20261125-2236-proef-kennis-bedrijfseconomie`. Report:
`output/proefrapport.md`. The order was the same as run `20261119-0943` (36 p, 6 leerdoelen, 17 vragen). The
proef changed no code; it steered only through agent prompts and extra input files.

| Element of the proef | What it did | Measured |
|---|---|---|
| **Misconception cards** per leerdoel, approved by the teacher (pause K) | The planner gave every vraag one card. The writer built the vraag so that the card's wrong route gives a different answer, and the cv denies that answer the point | 18 proposed, 12 approved, 6 rejected |
| **Mechanism cards** per exam question (6 exams, p-values from Cito TIA) | The planner gave every vraag one thinking move (*terugredeneren vanuit een uitkomst*, *veranderde voorwaarde doorrekenen*, …) with an exam question as example of form | 31 cards. No mechanism scored *weg* |
| **Old school toetsen** with school p-values | Evidence for the cards; `overlap_check` also guards them | 5 toetsen |
| **Two variants per opgave** (pause V) | The teacher chose per vraag | A 9×, B 6×, neither 2×; remarks on 9 vragen |
| **Misconception solver** (advisory) | Answers as a student who holds the card's misconception; compared with the cv | catches 11, partly 6, misses 0 |
| **Blind comparison** with run 0943 | Teacher judged 34 vragen without knowing their origin | **new 16/17 goed**, 1 aanpassen, 0 weg · old 10/17 goed, 2 aanpassen, 5 weg (3× "te makkelijk") |

The bar was ≥ 10 of 16 *goed*, so the proef passed. The gain did not come from the knobs. It came from a planned
trap per vraag and from a real thinking move. Specs/37 F7 ("te makkelijk") was deferred for lack of a lever; this
spec is that lever.

**Done by hand in the proef** (the reason for this spec): the knowledge cards and their merge, the p-values, the
varianten.md overview, assembling the chosen variants, the misconception check (`34_misconcept_check.json`,
compared through a copy of the run), the blind comparison, and the teacher's review after the export. A cv-only
repair still ran T4 in full.

## 2. Decisions

### 2.1 Decided (Martijn, 2026-11-27)

| Id | Decision |
|---|---|
| K1 | Misconceptions and mechanisms are **subject knowledge** in `subjects/<vak>/kennis/`, reused across toetsen. Pause K asks only about new or changed cards. |
| K2 | Mechanism cards are made by a new **`/examen` step E8**, next to the E7 labels. Each exam is done once, and the knowledge grows with the bank. |
| K3 | **Pause V** (two variants per vraag) is an order setting, **on by default**, that the form can switch off. |
| K4 | Specs/38 takes over specs/37 D10 (`focus`); the rest of specs/37 stays separate. |

### 2.2 Decided (Martijn, 2026-11-27; all ten as proposed)

| Id | Decision | § |
|---|---|---|
| D1 | A misconception card's status changes only through `kennis.py review` against a transcribed teacher review, never through an agent (as teacher review in specs/14 §5.1). Status: `voorstel` → `goedgekeurd` / `afgewezen` / `vervallen`. | 3.2 |
| D2 | Mechanism names come from a **controlled vocabulary** `data/toets/mechanisms.json` (base) plus `subjects/<vak>/kennis/mechanismen_vak.json` (subject). A name outside it is a proposal (`NIEUW`), added only through `kennis.py mechanism-add` against an answered decision, the same route as patterns (specs/31 §6). | 3.3 |
| D3 | E8 uses **one mechanist per exam**, without A/B: the cards are hints for the planner, not measurements. The bank-wide summary and pause K show the teacher what came out. | 4 |
| D4 | p-values: the teacher downloads Cito's TIA Excel per exam, and `tia_import.py` reads it into `B/tia/<exam>.json`. Tijdvak 2 has no TIA, so `p_value` is null. School p-values of old toetsen go into `kennis/oude_toetsen.json`. | 4.3 |
| D5 | Every vraag of a toets has `intent.misconcept` (an approved card of its leerdoel) and `intent.mechanism` (a vocabulary name). This is a hard BP rule. Exception: `intent.misconcept: null` with a reason, allowed for at most 1 vraag in 6 (an opening vraag, a P16). No mechanism more than 3 times per toets. | 5.2 |
| D6 | The trap is computed, not described: the writer gives per vraag `trap: {card_id, calc: [...], conclusion}`. `calc_check.py` recomputes the wrong route and fails when it equals the correct answer (number and conclusion). The cv must hold a rule that names the trap (IT13). | 5.3 |
| D7 | The misconception solver becomes a mode of `toets-solver` (`--mode misconcept`), and `misconcept_check.py` makes `34_misconcept_check.json` deterministically. A vraag that does not catch its card → finding V13 (`must` if the misconception answer earns all points, else `should`). | 6 |
| D8 | When a repair changes only cv fields, T4 is shortened: `student_build.py --check-unchanged` compares, and only `solver_compare`, `misconcept_check` and `realized` run again (lesson of 2026-11-27, O3-V10). | 7.2 |
| D9 | `blind_compare.py` (build and tally) becomes a straat tool for later proeven and for comparing two toetsen. It is not a step of every run. | 8 |
| D10 | The `focus` of a matrix row (specs/37 D10) becomes a misconception card with `source: docent` and status `goedgekeurd` as soon as T1 has read it back. The planner must use it (BP). | 5.4 |

## 3. Subject knowledge (`subjects/<vak>/kennis/`, committed)

### 3.1 Files

```
subjects/<vak>/kennis/
  misconcepten.json        misconception cards (schema misconception_cards), straat-written by kennis.py only
  mechanismen.json         merged mechanism cards of the bank's exams, rebuilt by kennis.py merge (never by hand)
  mechanismen_vak.json     subject additions to the mechanism vocabulary (via kennis.py mechanism-add)
  oude_toetsen.json        per vraag of the teacher's old toetsen: group_ids, form, mechanism, school p — no text
  reviews/<date>.json      transcribed pause-K reviews (input to kennis.py review), kept
  output/kennis-kaartjes.md  readable overview (Dutch), rebuilt by kennis.py report
B/mechanismen/<exam>.json  E8 output per exam (examenbank, beside labels/)
B/tia/<exam>.json          p-value and Rit per vraag (tia_import.py)
input/toetsen-<vak>-<level>/  the teacher's old toetsen (docx/pdf) — not committed; text goes to the run's text/
```

Exam text and old-toets text never enter `kennis/`. A card may quote a few words, not a sentence (KN3).

### 3.2 Misconception card

```json
{"card_id": "F1.28.1-02-m1", "group_id": "F1.28.1-02", "criteria": ["F1.28.1-02-b"],
 "misconception": "De leerling denkt dat …", "typical_wrong_answer": "(aanschafprijs incl. btw − restwaarde) / n …",
 "catching_question": "Bereken-vraag waarbij de bron een factuur incl. btw en aparte installatiekosten geeft …",
 "sources": [{"kind": "docent|examen|cv|oude_toets", "ref": "vwo-2024-tv1 v22", "p_value": 0.20}],
 "evidence_strength": "sterk|matig|zwak", "levels": null, "status": "voorstel|goedgekeurd|afgewezen|vervallen",
 "criteria_version": "<criteria_run>", "proposed_in": "<run_id>", "reviewed_at": "2026-11-26",
 "review_note": "…", "used_in": [{"toets_id": "…", "vraag_id": "O1-V1", "catches": "ja|deels|nee", "teacher": "goed|aanpassen|weg|null"}]}
```

- `card_id = <group_id>-m<n>`, never reused. A card that is changed after approval gets a new id. The old card
  becomes `vervallen` with `replaced_by`.
- `used_in` is appended by `toetsbank_add.py` (catch result from `34_misconcept_check.json`) and by the teacher
  review (teacher verdict, specs/37 T7 once it is built). Over time this shows which cards make good vragen.
- `levels` null = the card applies to every toets of the subject; else a list (`["5vwo"]`) limits it (decided 2026-11-27).
- Cards are bound to `criteria_version`. When the bank moves to another criteria run, `kennis.py rebind` maps them
  by criterion id and marks the unmapped ones `vervallen`.

### 3.3 Mechanism card (E8 output) and vocabulary

```json
{"exam": "vwo-2024-tv1", "vraag": 18, "points": 2, "group_ids": ["F2.30.4-01"], "criteria": ["F2.30.4-01-a"],
 "p_value": 0.58, "rit": 0.41, "mechanism": "terugredeneren vanuit een uitkomst", "mechanism_detail": "…",
 "move": "…", "skeleton": "… (abstract: what is given, what is asked, which trap; no exam wording or numbers)",
 "why_hard": "…", "cv_signal": "…", "status": "actief|randgeval"}
```

`data/toets/mechanisms.json` (base, seed from the proef): `{name, description, example_skeleton}` for, at least,
*rechtstreekse toepassing*, *grondslag kiezen*, *tijdsafbakening*, *terugredeneren vanuit een uitkomst*,
*veranderde voorwaarde doorrekenen*, *twee tegengestelde effecten afwegen*, *zelf de relevante gegevens kiezen*,
*irrelevante gegevens negeren*, *een half juiste redenering beoordelen*. *Rechtstreekse toepassing* is allowed and
honest. The planner may plan it only where D5 allows it.

## 4. `/examen` step E8: mechanism cards

After E7, for the exams of the run (or `/examen --mechanisms --subject <s> [--exam …]` on exams already in the bank):

1. **TIA.** `tia_import.py <s> <exam> <xlsx>` writes `B/tia/<exam>.json` from the sheet `item_info`, rows
   *Totaal / Alle kandidaten*. If the file is missing, the orchestrator asks the teacher once. Without it the step
   goes on with `p_value: null`.
2. Agent **`exam-mechanist`**, one per exam, in parallel. Input: the exam's text in `R/text/`, the scorepunt→criterion
   links `B/links/<exam>.json` (the only scope signal: a vraag is in scope when one of its scorepunten has a link),
   the vocabulary, `B/tia/<exam>.json`. Output: `B/mechanismen/<exam>.json` `{exam, cards, skipped, proposed_mechanisms, notes}`.
   The card rules are those of the proef brief `kennis/brief_mechanismen.md`, which becomes `.claude/agents/exam-mechanist.md`.
3. `check_mechanisms.py <s> <exam>`:
   - MC1 schema.
   - MC2 every in-scope vraag has a card or is in `skipped` with a reason.
   - MC3 `mechanism` is in the vocabulary or is `NIEUW` with a proposal.
   - MC4 `skeleton`/`move` share no 8-word shingle with the exam text (overlap_check's shingler).
   - MC5 `p_value` equals the TIA value.
   A failure → relaunch once.
4. NIEUW proposals → `decisions.py add` (open, `applies_to: ["mechanisms"]`).
5. `kennis.py merge <s>` → `kennis/mechanismen.json` and `kennis.py report <s>`.

Cost: 1 agent per exam (≈ 6 for the current bedrijfseconomie material). This is a one-off; new exams add one each.

## 5. `/toets` changes

### 5.1 T1b Knowledge (pause K), after the order and before the blueprint

1. `kennis.py scope <s> R` → `R/30_kennis.json`. It holds the approved cards for the matrix's groups, the mechanism
   cards of those groups, the old-toets notes, and per group a `need`:
   - `none`: ≥ 2 approved cards, and nothing new since the last review.
   - `propose`: fewer than 2 approved cards, a new exam in the bank since the group's last review, or a matrix
     `focus` that does not match a card yet.
2. Only for groups with `need: propose`: agent **`misconcept-proposer`** (one for all those groups). Its sources are
   the cv remarks, low p-values, old toetsen and the focus texts. It writes new cards as `voorstel` →
   `R/30_kennis.proposals.json`. It never changes approved cards; it may *propose* `vervallen` with a reason.
3. `kennis.py report <s> --run R` → `R/output/kennis-kaartjes.md`. Per leerdoel it shows: the approved cards (with
   `used_in`), the new proposals, the mechanisms with p-values, and what the old toetsen did.
4. **Pause K** (only when there are proposals). Per proposal the teacher chooses *goedkeuren* / *aanpassen (tekst)* /
   *afwijzen*, and may add cards of their own. The orchestrator transcribes the answers to
   `subjects/<s>/kennis/reviews/<date>.json` and **reads them back**. Then `kennis.py review <s> <file>` writes the
   statuses and `kennis.py scope <s> R` runs again.
5. No proposals → no pause, and T1 reports "kennis: n kaartjes per leerdoel, geen nieuwe voorstellen".

### 5.2 Planner (T2a)

Extra input: `R/30_kennis.json`. Per vraag `intent` becomes an object:

```json
"intent": {"text": "De leerling berekent …", "misconcept": "F1.28.1-02-m1",
           "mechanism": "grondslag kiezen", "mechanism_example": "vwo-2025-tv1 v12", "no_misconcept_reason": null}
```

`blueprint_check.py`:

| Id | Rule |
|---|---|
| BP10 | Error: `misconcept` is not an approved card of a group that one of the vraag's scorepunten belongs to. |
| BP11 | Error: `misconcept` is null without a reason, or more than ⌊n_vragen/6⌋ vragen have no misconcept. |
| BP12 | Error: `mechanism` is not in the vocabulary. Warning: a mechanism is used more than 3× in the toets. |
| BP13 | Error: a matrix `focus` card (§5.4) has no vraag. |
| BP14 | Warning: a pittige vraag (Bloom ≥ analyseren or steps ≥ 3) has a mechanism whose example has p ≥ 0.7. |

`bouwplan.md` shows per vraag the card (short text) and the mechanism.

### 5.3 Writer (T3)

The proef addendum (`kennis/brief_writer.md`) moves into `.claude/agents/toets-writer.md`. Input: its vragen's
cards and mechanism cards from `R/30_kennis.json`, and the exam questions the mechanism cards name (`R/text/`,
form only). New in the items schema, per vraag:

```json
"trap": {"card_id": "F1.28.1-02-m1",
         "calc": [{"name": "afschr_fout", "expr": "(prijs_incl - restwaarde) / n", "round": 0}],
         "wrong_shown": "€ 15.730", "wrong_conclusion": null, "cv_rule_index": 2}
```

- `calc_check.py` (IT14) recomputes `trap.calc` with the vraag's `data`. It fails when the final trap value equals
  the correct final value after rounding, or when `wrong_conclusion` equals the model answer's conclusion **and**
  the vraag scores the conclusion alone. When the misconception leads to the same conclusion by chance, it gives
  a warning (proef O3-V10).
- IT13 (`items_check.py`): `cv.rules[cv_rule_index]` exists, names no "misconcept", and has the CvTE form
  "Als … , het … scorepunt niet toekennen".
- An explanation vraag has `trap.calc: []` and a `wrong_conclusion` text; the misconception solver judges it.
- No defusing cue (the IT9 phrases plus card-specific phrases in `catching_question`). Exception: a teacher remark
  at pause V that knowingly adds one (`trap.defused_by_teacher: true`, shown in the verantwoording).

### 5.4 `focus` per matrix row (specs/37 D10)

A matrix row may carry `focus` (Dutch teacher text). The form gets a text field per leerdoel. In T1 the orchestrator
reads it back and makes it a card `{source: docent, status: goedgekeurd}` through `kennis.py review` (with the T1
transcript as the review file). If an approved card already says the same, the teacher picks that card instead.
BP13 enforces it.

### 5.5 Variants and pause V (T3b, when `order.variants` is true; default true)

- Order schema: `variants: true|false` (form: "Twee varianten per vraag laten maken en zelf kiezen", default *ja*).
- Each writer writes A → `33_varianten/<opgave>.A.json` and B → `33_varianten/<opgave>.B.json`. They share the
  blueprint and the context. B uses another mechanism or angle for the **same** card (`writer_notes`:
  `B-mechanisme: …`). The checks run on both. The scripts get `--file`, so a variant is no longer copied into
  `33_items/`.
- `variants_report.py R` → `R/output/varianten.md`: per vraag A and B side by side, with the card, the mechanism and
  the trap value.
- Pause V: per vraag *A* / *B* / *geen van beide* plus a remark → `R/33_varianten/keuze.json` (schema
  `variant_choice`), transcribed and read back. A choice that needs a replan (as in the proef for O3-V10 and O4)
  goes through `32_blueprint_review.json` and `blueprint_apply.py` first.
- **Assemble**: `toets-writer` letter R, mode `assemble` (the proef addendum `kennis/brief_assemble.md` moves into
  the definition). It writes `33_items/<opgave>.json` from the choices and rereads the whole opgave. Then the T3
  checks.
- Variants off: a writer writes one variant straight into `33_items/`, as in specs/33.

## 6. Misconception check (T4)

- Per opgave, in the same message as the blind solver and the labellers: `toets-solver` in **mode `misconcept`**.
  Input: `34_student/<opgave>.md` and `R/34_misconcept_cards/<opgave>.json` (written by `misconcept_cards.py R`:
  per vraag only the card's `misconception` and `typical_wrong_answer`; no cv, no trap). Output: `34_misconcept/<opgave>.json`.
- `misconcept_check.py R` → `R/34_misconcept_check.json`. Per vraag it compares the misconception answer with the cv
  the way `solver_compare` does:
  - `catches: ja`: a different number, or a different conclusion that is scored.
  - `deels`: a different number but the same conclusion, or only the toelichting differs.
  - `nee`: equal to the correct answer, or it would earn all points.
  It also checks that the solver's wrong value equals `trap.wrong_shown` (`trap_realised`).
- Verifier **V13**: `nee` → `must` (repair, `fix_hint` from the card's `catching_question`). `deels` → `should`,
  unless a cv rule demonstrably denies the point (then pass). The proef case O3-V10: a rule against dividing by
  € 8 / € 72 made it *pass*.

## 7. T5 and repair

### 7.1 As specs/33 §T5, plus

- Writer R gets V13 findings and the card.
- The verifier may propose a card change (`proposed_cards`). That goes to pause K of the next toets, never into the
  current one.

### 7.2 cv-only repair (D8)

`student_build.py R --opgave <id> --check-unchanged` exits with 0 when `34_student/<opgave>.md` is unchanged. The
orchestrator then reruns only `solver_compare.py`, `misconcept_check.py`, `realized.py` and the verifier (`--only`).
Solver, labellers and the misconception solver keep their output (the labeller reads the cv only for the scoring
structure: a changed number of scorepunten → full T4 after all; the script checks that too).

## 8. Export, bank and comparison

- Verantwoording: a column *misconcept / mechanisme / vangt* per vraag. The twijfellijst gets V13 findings and
  `deels` catches.
- `toetsbank_add.py`: per vraag `misconcept`, `mechanism`, `catches` in `toetsen/<id>.json`, plus `used_in` on the card.
- `blind_compare.py build R --against <run_id> [--seed n]` → `R/output/blind-vergelijking.md` + `R/blind-sleutel.json`
  (the proef's ad-hoc script, kept as `docs/tools/blind_build_proef.py` until this is built). `blind_compare.py tally R <oordeel.json>` → a table per origin,
  plus mechanisms and cards of the *goed* vragen. The cv summary shows the scorepunten only, without rules, because
  trap rules would give away the origin.

## 9. Files, schemas and scripts

| New | Kind |
|---|---|
| `schemas/misconception_cards.schema.json`, `mechanism_cards.schema.json`, `tia.schema.json`, `variant_choice.schema.json`, `kennis_review.schema.json` | schema |
| `data/toets/mechanisms.json` | rule file (seed: the 9 names of §3.3 + the proef's unified names) |
| `scripts/toets/kennis.py` `scope|review|merge|report|rebind|mechanism-add|validate` | script |
| `scripts/exam/tia_import.py`, `scripts/exam/check_mechanisms.py` | script |
| `scripts/toets/misconcept_cards.py`, `misconcept_check.py`, `variants_report.py`, `blind_compare.py` | script |
| `.claude/agents/exam-mechanist.md`, `misconcept-proposer.md` | agent |
| `toets-solver` mode `misconcept`, `toets-writer` trap rules + mode `assemble`, `toets-planner` intent object, `toets-verifier` V13 | agent changes |

| Changed | What |
|---|---|
| `schemas/blueprint` | `intent` object (§5.2). Old blueprints keep a string; `blueprint_check` reads both. |
| `schemas/toets_items` | `trap` per vraag |
| `schemas/toets_order` / form | `variants`, `focus` per matrix row |
| `blueprint_check.py` | BP10–BP14 |
| `items_check.py`, `calc_check.py` | IT13, IT14 |
| `items_check`/`calc_check`/`figures`/`overlap_check` | `--file <path>` for variants. `overlap_check` also reads `text/oudetoets-*.txt` |
| `student_build.py` | `--check-unchanged` |
| `export_toets.py`, `toetsbank_add.py` | §8 |
| `tests/run_toets_fixture.py` | a small kennis fixture: 2 cards, 2 mechanism cards, 1 variant pair, one trap that equals the correct answer (IT14 must fail) |

**Cost per toets (4 opgaven, variants on).** 1 proposer (only with need), 1 planner, 8 writers (A+B), 4 assemble,
4 solvers, 4 misconception solvers, 8 labellers (+ ~2 R), 1 verifier, ~2 repairs (+ their T4) ≈ 40 agent calls.
That is ≈ 10 more than specs/33 §5, and ≈ 15 fewer than the proef (≈ 55, with knowledge built from scratch).
Variants off: ≈ 28.

## 10. Build order

1. Schemas, `data/toets/mechanisms.json`, `kennis.py` (validate/merge/report/review), and migration of the proef's
   files to `subjects/bedrijfseconomie/kennis/` (12 approved + 6 rejected cards, 31 mechanism cards → `B/mechanismen/`
   per exam, TIA → `B/tia/`). Fixture.
2. E8: `tia_import.py`, `exam-mechanist`, `check_mechanisms.py`, `/examen --mechanisms`.
3. T1b: `kennis.py scope`, `misconcept-proposer`, pause K in `/toets`.
4. Planner intent object + BP10–BP14; writer `trap` + IT13/IT14.
5. Misconception check (solver mode, `misconcept_cards.py`, `misconcept_check.py`, V13); cv-only shortcut.
6. Variants: `--file` on the checks, `variants_report.py`, pause V, assemble mode.
7. Export, toetsbank, `blind_compare.py`; HANDLEIDING-toets.md (a section on knowledge cards and pause K).
8. Test run: the same order again (bedrijfseconomie 5 VWO P2), from the migrated knowledge; pause K should not
   be needed. Compare cost and result with the proef.

## 11. Open questions

- Economie has no TIA import yet and no old toetsen. Does E8 run on the five economie exams before the first economie
  toets with cards?
- *Decided 2026-11-27:* a card applies within the subject, with an optional `levels` (§3.2).
- *Decided 2026-11-27:* `used_in.teacher` never retires a card on its own; the overview shows the tally, and only the
  teacher sets `vervallen` (via pause K).
