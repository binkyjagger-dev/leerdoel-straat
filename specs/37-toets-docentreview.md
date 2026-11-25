# 37 — Toets-straat v2.1: teacher review step, subject knob defaults, wider cue and giveaway checks

**Status:** draft 2026-11-18 (Martijn to approve §2). Amends specs/31, 32, 33, 34, 35 and 36; where this spec and
an older one differ, this spec wins. Domain language English; teacher-facing text Dutch.

**Order of work (decided 2026-11-18).** Spec first, then **stop**. The teacher first reruns the same order on the
*current* straat with different knob settings (pause 1) to see what the knobs alone change. The outcome of that rerun
may amend this spec (§9) before anything is built.

## 1. Why (teacher review of toets run 5, bedrijfseconomie 5 VWO P2, run `20261117-1909`, 2026-11-18)

Transcript: `runs/20261117-1909-toets-bedrijfseconomie/36_teacher_review.json`. The toets as a whole was fine
(length, structure, storyline, contexts, layout). Of 16 vragen 4 were good (1, 7, 10, 16), 12 need changes.

| # | Observation (teacher) | Vragen | Measured / found | Root cause in the straat | Class |
|---|---|---|---|---|---|
| F1 | "Quitte gebruiken we niet bij bedrijfseconomie, dat noemen we break-even." | 2, 3 | Criteria: break-evenafzet 13×, break-evenomzet 8×, quitte 0×. The writer chose "quitte" itself. | No rule that student text uses the criteria's term; the glossary only feeds retrieval (specs/06 §8) | B + C |
| F2 | The solution path is named: "Bereken hiervoor eerst …", "Trek hiervoor per drukpers … af" | 3, 6, 11 | Five vragen were *planned* route gegeven (order: route = eindexamen, CE 34,7 % gegeven): 3, 6, 11, 13, 14. The teacher objected to 3, 6, 11 and 14 (F4); 13's route ("Toon met een berekening van het werkelijke resultaat … aan") passed. 11's cue sits in the lead and has no `bereken` | The teacher's practice for school toetsen differs from the CE; IT9 only fires where route was planned *zelf vinden*; the route regex knows only `bereken hiervoor eerst` | B + C |
| F3 | "Te sturend" | 8, 15 | 8: "Leg uit dat Daan op beide punten ongelijk heeft" (direction gegeven, planned). 15: "Leg uit dat het resultaat … met € 53 stijgt" (answer given) | As F2, for direction (CE 18 % gegeven) | B |
| F4 | A toelichting instruction steers: "Licht je antwoord toe door per post informatiebron 1 en 2 te vergelijken" makes the vraag a list of posts instead of an explanation of the difference | 14 | Not a route cue in `cue_phrases.json` | "How to justify" instructions are not counted as route | C |
| F5 | "Je hoeft niet weer de informatiebron te noemen" | 13 | Intro: "Bij deze opgave horen informatiebron 1 en 2"; task names "(informatiebron 2)" and "(informatiebron 1)" again | No rule on repeated bron references | C |
| F6 | The lead of 12 ("De aanschafwaarde en de restwaarde blijven gelijk") gives away "restwaarde", the answer to 9 | 9, 12 | Found by the verifier only in round 3; left as must on the twijfellijst | IT10 checks a vraag's *own* criterion concepts only, not the answers of other vragen | C |
| F7 | "Te makkelijk (voor VWO)" | 4, 6, 9, 12, 15 | 4 and 12: binary choice + toelichting (P05); 9: "noem twee begrippen" (P16, onthouden); 15: answer given | The straat has no level parameters beyond Bloom and the knobs | C, **deferred** (§8 W1) |
| F8 | Points too high | 5 (3 → 2), 11 (4 → 2) | — | Only these vragen (teacher, 2026-11-18) | A |
| F9 | Doubt whether the leerdoel of 16 belongs to period 2 | 16 | Matrix from the teacher's order file | — | A (§8 W4) |
| F10 | At pause 1 the teacher chose "route = eindexamen" without seeing what a given route looks like in a vraag | (3, 6) | The pause-1 options show shares only | Knob values have a definition, no example sentence | C |
| F11 | (straat, run 5) Labellers kept citing generic economie-099 (two sources = relationeel) against bedrijfsecon-071 (calculation chain = multistructureel) | — | — | specs/36 D6 made 096–099 generic; there is no precedence rule when a subject decision answers the same question | C |
| F13 | (matrix review, 2026-11-19) "Een belangrijk misconcept dat getoetst moet worden …" on two leerdoelen (aanschafwaarde incl. installatiekosten / restwaarde minus sloopkosten; winstopslag op de kostprijs vs al in de verkoopprijs) | — | Revised matrix `subjects/bedrijfseconomie/toets/toetsmatrijs-p2-26-27-herzien.json` | A matrix row holds only `group_id` + `points` (`additionalProperties: false`); a teacher focus per leerdoel has no channel to planner, writer or verifier | C |
| F12 | (straat) The feedback round itself had no straat step: transcription, classification and the route back to repair were done ad hoc | all | — | No teacher-review step after T6 (the koppel straat has one, specs/14 §5.1) | C |

Classes: **A** this toets only · **B** subject rule (bedrijfseconomie) · **C** generic straat rule · **D** taste/one-off.

General principle (unchanged from specs/36): the central exam of the subject is the reference. New here: **a subject
may set a house default that deviates from the CE** (F2, F3). The deviation is an answered decision, shown next to the
CE at pause 1, never hard-coded.

## 2. Decisions to approve (proposals, 2026-11-18)

| Id | Proposal | From |
|---|---|---|
| D1 | New layer **subject knob defaults** between the CE reference and the template/order (§3). Bedrijfseconomie: route = zelf vinden 1.0, direction = open 1.0 (teacher, 2026-11-18). | F2, F3 |
| D2 | The glossary gets an **avoid list per term** for toets text; a toets check flags avoided words (§4.1). Bedrijfseconomie: term *break-even* (break-evenafzet, -omzet, -punt), avoid *quitte (spelen)*. | F1 |
| D3 | The route cue scan reads intro, lead, task **and the bronnen**, and knows any imperative + *hiervoor/daarvoor* and toelichting instructions (*licht … toe door …*, *vergelijk hiervoor …*). When the order share of *route gegeven* (resp. *direction gegeven*) is 0, every hit is an **error**, not a warning (§4.2). | F2, F3, F4 |
| D4 | A bron is referenced at most once per vraag and not at all in the task when the opgave intro already ties all its bronnen to the opgave and the vraag uses all of them; warning (§4.3). | F5 |
| D5 | **Cross-vraag giveaway**: a concept that is (part of) the answer of vraag *n* must not occur in the intro, a bron or the text of any other vraag of the toets; error when vraag *n*'s scorepunt is onthouden or begrijpen, warning otherwise (§4.4). | F6 |
| D6 | Every value of a settable knob gets a short Dutch **example sentence** in `data/toets/knobs.json`; pause 1 shows it next to the options (§5). | F10 |
| D7 | **Decision precedence**: a subject decision that answers the same question as a generic one wins for that subject. The subject decision names it (`overrides: ["economie-099"]`); the snapshot marks the generic one `overridden_by` and agents read only the effective one (§6). | F11 |
| D8 | New step **T7 Teacher review** (`/toets --review <run>`) with `36_teacher_review.json`, classification A–D, and the route back: A → writer R + verifier, B → decisions, C → straat backlog (§7). | F12 |
| D10 | A matrix row may carry **`focus`** (teacher text, Dutch: a misconception or aspect that must be tested). The form gets a text field per leerdoel; T1 reads it back; the planner must plan at least one scorepunt whose `intent` tests it (BP check: a focus without a vraag whose intent cites it → error); the writer builds the vraag so the misconception leads to a wrong answer (a trap, W1 candidate 7); the verifier checks it (V1). Until built: pass it at pause 2 as a `32_blueprint_review.json` `intent` entry. | F13 |
| D9 | F7 (VWO level) is **deferred** to a separate session; candidate parameters in §8 W1. Nothing in this spec changes difficulty directly. | F7 |

## 3. Subject knob defaults (D1; amends specs/31 §4, specs/32 §3)

**File** `subjects/<subject>/toets/knob_defaults.json` (schema `schemas/knob_defaults.schema.json`), straat-written
only, like the glossary and the verb table:

```json
{"subject": "bedrijfseconomie",
 "defaults": [{"knob": "route", "shares": {"gegeven": 0.0, "zelf vinden": 1.0},
               "levels": null, "decision": "bedrijfsecon-0xx", "added_at": "2026-11-18"},
              {"knob": "direction", "shares": {"gegeven": 0.0, "open": 1.0},
               "levels": null, "decision": "bedrijfsecon-0xx", "added_at": "2026-11-18"}]}
```

- `levels` null = every level; else a list (`["4vwo", "5vwo"]`).
- **Install**: `python scripts/toets/knob_defaults.py add <subject> <decision_id> <entries.json>` refuses unless the
  decision is `answered`; re-adding the same decision replaces its entries. `list|validate <subject>`.
- **Precedence** (low → high): CE reference profile → subject knob default → template → order file → pause-1 answer.
  `validate_toets.py order --draft` fills a `null` knob from the subject default and marks it `source: vakstandaard`
  in `31_order.ask.json`; the knob is still read back at pause 1.
- **Pause 1**: per knob one line *opdracht · vakstandaard · eindexamen*. The ask options get a fourth choice
  *Vakstandaard (…)* first when a default exists. O6 (share outside CE range) becomes **info** when the share equals
  the subject default ("afwijking van het eindexamen is vakstandaard, besluit bedrijfsecon-0xx").
- **Planner and verifier**: a share of 0 for a value is a hard constraint (BP: no vraag planned with that value).
- The verantwoording lists the subject defaults used, with the decision ids.
- Template `5vwo-toets.json` keeps its CE copy; it is the teacher's file. The teacher may save a new template.

## 4. Checks (amends specs/36 §6; items_check / house_checks)

### 4.1 IT12 — avoided term (D2)

- `glossary.json` entry gains optional `avoid_in_toets: ["quitte", "quitte spelen"]` (schema bump; `glossary.py add`
  accepts it; installed only against an answered decision). Retrieval is unchanged: synonyms still map to the term.
- IT12 scans intro, bronnen, lead, task, model answer and scorepunt texts with the glossary normaliser
  (`mcommon` stemming, plural, accents). Hit → **error** with the preferred term: "gebruik *break-even…*".
- Generic rule for the writer prompt: use the criterion's term for the concept; a synonym only when a glossary entry
  allows it. Never replace a term by a synonym to avoid IT10 — rephrase or drop the sentence.

### 4.2 IT9 wider (D3)

- Text scanned: intro, lead, task **and every bron the vraag uses** (route cues only in bronnen; direction cues in
  bronnen are context, not counted).
- New route patterns in `data/toets/cue_phrases.json`:
  - `hiervoor-imperatief`: an imperative at sentence start followed within 3 words by *hiervoor/daarvoor/daarbij*
    ("Trek hiervoor per drukpers … af", "Deel daarvoor …"). The D4 allowlist (gebruik informatiebron n, rond af,
    ga uit van) stays.
  - `toelichting-door`: *licht … toe door … te* and *door … te vergelijken/berekenen/gebruiken* in a task.
  - `vergelijk-hiervoor`: *vergelijk hiervoor / vergelijk daarvoor*.
- Severity: when the order share of route *gegeven* is 0 (from a subject default or the order), a route hit is an
  **error** in every vraag; same for direction *gegeven*. Otherwise as specs/36 (warning to V11 where the vraag's
  planned value is zelf vinden/open).
- `toets-writer.md` and the R letter: with route 0 % no helper sentence that says how, anywhere in the opgave text.

### 4.3 IT13 — repeated bron reference (D4)

- Warning when a vraag names the same informatiebron twice, or names a bron in its task while the opgave intro already
  says "Bij deze opgave horen informatiebron …" and the vraag uses all bronnen of the opgave.
- Allowed: one "Gebruik informatiebron n" when the opgave has more bronnen than the vraag uses.
- Measure later in the CE (`exam_metrics.py`: bron references per task) to set the subject practice; until then the
  rule is a warning, never an error.

### 4.4 IT14 — cross-vraag giveaway (D5)

- For each vraag *n*: answer concepts = criterion concepts ∪ glossary terms (with synonyms) that occur in vraag *n*'s
  scorepunt texts or model answer.
- Hit when such a concept occurs in the intro, any bron, or the lead/task of another vraag *m* of the toets
  (before or after *n*), excluding concepts the writer lists in `new_concepts` and concepts in *n*'s own task object.
- Severity: error when a scorepunt of *n* is onthouden or begrijpen (the concept *is* the answer), warning otherwise.
  The message names both vragen ("V12 lead noemt 'restwaarde', het antwoord op V9").
- Runs per opgave and once over the whole toets (`items_check.py R` without `--opgave`), so it also catches a later
  repair that moves a term into another vraag (F6 appeared after repair round 2).

## 5. Knob examples at pause 1 (D6)

- `data/toets/knobs.json`: each settable value gets `example_nl` (≤ 15 words, generic, no exam text; e.g. route
  *gegeven*: "Bereken hiervoor eerst de dekkingsbijdrage per stuk."; direction *gegeven*: "Leg uit dat de winst
  daalt."). A subject overlay may add its own (`subjects/<s>/toets/knob_examples.json`).
- The ask options and the pause-1 read-back show the example of the value that carries the share
  ("route gegeven 35 % — bv. 'Bereken hiervoor eerst …'").
- `form_build.py` shows the same examples as a tooltip in the form.

## 6. Decision precedence (D7; amends specs/06 §4 and specs/36 D6)

- `decisions.py answer <subject> <id> … --overrides <other_id>[,…]` records `overrides` on the subject decision.
  `decisions.py add` lets the verifier or intake propose it (`overrides` field in the question).
- `decisions.py snapshot` puts the generic decisions of specs/36 D6 into every subject's snapshot (as now) and marks
  each overridden one `overridden_by: "<subject id>"`, `effective: false`.
- Agent prompts (planner, labeller, verifier, writer): "apply only decisions with `effective` not false".
- To record now (bedrijfseconomie): bedrijfsecon-071 overrides economie-099 for calculation chains. The open question
  for the next intake is whether 099's *two sources* part still applies to bedrijfseconomie.

## 7. T7 Teacher review (D8; new step, amends specs/33 and specs/35)

`/toets --review <run>` after T6, any time later.

1. **Collect.** The orchestrator shows the leerling text per opgave (with its bronnen and the uitwerkbijlage reference)
   and asks for a verdict per vraag: *goed* / *aanpassen* / *weg*, plus a free remark, then the toets as a whole.
2. **Transcribe** into `R/36_teacher_review.json` (schema `schemas/teacher_review.schema.json`):
   `{run_id, reviewer, reviewed_at, entries: [{target: "O1-V3" | "O2" | "toets", verdict, comment, class, decision?,
   reading?, follow_up?}], workpoints: [{id, from, topic, note}]}`. `comment` is the teacher's words; the
   orchestrator adds facts it measured in the run only under `found` (never in `comment`). Read the entries back
   after each opgave; ambiguous remarks are asked with the possible readings (as F4), never guessed.
3. **Classify.** The orchestrator proposes a class A–D per entry and shows the A/B/C overview; the teacher confirms.
   A question whose answer is a subject rule (F2, F3) is asked explicitly: *vakstandaard* or *alleen deze vraag*.
4. **Route back.**
   - **A** → a review repair round: each *aanpassen* entry becomes a `must` finding (`source: docent`) for writer R,
     then T3 checks, T4 and the verifier on the changed opgaven only (counts as a repair round of its own; max 2).
     *weg* removes the vraag only when the matrix still holds; else the teacher chooses which leerdoel loses points.
   - **B** → `decisions.py add` + `answer` (raised_by `docent`), then the installer (`knob_defaults.py`,
     `glossary.py`, `patterns.py`).
   - **C** → appended to `docs/toets-backlog.md` (date, run, F-number, proposal); a spec like this one is written from it.
   - **D** → kept in the review file only.
5. **Export.** The verantwoording gets a section *Docentreview* (counts per verdict, what changed, open workpoints);
   `toetsbank_add.py` stores the review with the toets record (`review` field), so the next planner can read which
   contexts and patterns the teacher rejected.
6. `run.json.status: "reviewed"` (then `"revised"` after an A round).

## 8. Workpoints (not in this build)

| Id | From | Topic |
|---|---|---|
| W1 | F7 (4, 6, 9, 12, 15) | **VWO level**: parameters beyond Bloom and the knobs, measured in the CE, set per level by the teacher relative to the CE. Candidates: guessing chance and where the points sit (choice vs justification); direction of reasoning (forward / inverse); change of representation (read / convert / produce); data preparation (convert units, incl./excl. btw); abstraction (with numbers / without / general); transfer distance; trap; length of an explanation chain; cv strictness; realistic vs round numbers. First choice: 1, 2, 3, 5. |
| W4 | F9 (16) | Does F2.30.5-01-c (tax on the profit of an eenmanszaak) belong to period 2? Teacher checks the order. |

## 9. Build order and acceptance (after the knob rerun)

0. **Knob rerun (no build).** Same order file with the teacher's revised matrix
   (`subjects/bedrijfseconomie/toets/toetsmatrijs-p2-26-27-herzien.json`: 6 leerdoelen, 36 p, F2.30.3-02-c tested
   again; transcribed at T1 and read back; the two `focus` texts go in at pause 2 as `intent` entries), new run id; at pause 1 the teacher sets route 0 %, direction 0 % and
   any other knob as wanted. Compare with run 5: per vraag the teacher's F-items of §1 (does F2/F3/F4 disappear by
   knobs alone?), total words, IT9/IT10 hits, verifier rounds. Amend this spec with the outcome.
1. Schemas: `knob_defaults`, `teacher_review`, glossary `avoid_in_toets`, decision `overrides`; `knobs.json`
   `example_nl`; order `matrix_row.focus` (D10) with the form field, the BP check and the planner/writer/verifier
   prompt lines.
2. `knob_defaults.py`, `glossary.py` (avoid list), `decisions.py --overrides` + snapshot `effective`.
3. `validate_toets.py order` (defaults layer, O6 info), pause-1 read-back and options (orchestrator), `form_build.py`.
4. `house_checks.py`: IT9 wider + severity, IT12, IT13, IT14; `cue_phrases.json` patterns.
5. Prompts: writer (also R), planner (0-share = hard), verifier (V11 with IT12–IT14), labeller/verifier (effective
   decisions).
6. T7: `/toets --review`, review repair round, export section, toetsbank `review`, `docs/toets-backlog.md`.
7. Fixture (`tests/run_toets_fixture.py`): an item with "Trek hiervoor …" in a lead (IT9 error at route 0 %), "quitte"
   (IT12), a bron named twice (IT13), an answer term in another vraag's lead (IT14), a snapshot with an overridden
   generic decision, a review file with one A entry.
8. Acceptance on run 5's items (`items_check.py` on a copy, with route and direction at 0 %): IT9 flags route in
   3, 6, 11 and 14 and direction in 8 and 15; open question for the teacher whether 13's "Toon met een berekening van
   X aan" counts as a route (it passed the review); IT12 flags 2 and 3; IT13
   flags 13; IT14 flags 12 → 9. Then T7 on run 5 (or on the knob rerun, teacher's choice): repair the A entries and
   compare with the teacher's verdicts.
