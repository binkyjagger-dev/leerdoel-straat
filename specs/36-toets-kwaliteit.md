# 36 — Toets-straat v2: central-exam house rules for reading load, cueing, question form and toets size

**Status:** decided 2026-11-17 (Martijn), to build. Amends specs/26, 31, 32, 33, 34 and 35; where this spec
and an older one differ, this spec wins. Domain language English; teacher-facing text Dutch.

## 1. Why (teacher review of toets run 3, economie 4 VWO P2 "Levensloop", 2026-11-17)

The teacher would not use the toets as written. 9 of 17 vragen were good. The faults were:

| # | Observation (teacher) | Measured | Root cause in the straat |
|---|---|---|---|
| F1 | Too much text for 4 VWO | Stems are CE-like (median 58 words vs 63 in the CE), 1,984 words in total | No reading budget per level; the writer copies CE density |
| F2 | Concepts and solution paths are named in the stem ("noemen"): the tested concept defined (grijze druk, informatieasymmetrie), the step given ("koers plus dividend", "gebruik de cpi"), the direction given ("… toch gedaald") | CE economie: route given on 0 % of calculation points | `route` covers only full "bereken hiervoor eerst" lists; the verifier's V6 (unambiguous) and the run-1 lesson push writers to add hints |
| F3 | The question is not crisp: several lines of context and the task mixed; double tasks (4: bereken + kies; 11, 17: two "leg uit") | — | One `stem` field; no rule on the number of tasks per vraag |
| F4 | Loose contexts ("kapstok"): every vraag brings a new person and new numbers | CE: 8–13 p per opgave, 4–6 vragen, one storyline; toets: 6–7 p, 3–4 vragen, five opgaven for 33 p | The planner spreads vragen over `n_opgaven` without a storyline; no CE reference for opgave size |
| F5 | 90 minutes were meant, 33 printed | The order file held `duration_minutes: 33` | The form's duration field is easy to confuse with points; pause 1 never reads the duration back; no time-per-point check |

General principle (decided): **the central exam of the subject is the reference for every house rule**. The straat
measures each rule per subject from the exam bank, records it in the reference profile and applies it as best
practice. The teacher adjusts per level with percentages or knob shares, as for the existing knobs. Nothing is
hard-coded per subject, so a new subject gets the rules as soon as it has an exam bank (`/examen` + E7).

## 2. Decisions (2026-11-17)

| Id | Decision |
|---|---|
| D1 | Reading budget = CE words per point of the subject × a per-level percentage set by the teacher (form, template, order). |
| D2 | The straat proposes the number of opgaven from the CE points per opgave; the teacher can change it at pause 1. |
| D3 | Vragen within an opgave build on one storyline (one situation, fixed actors and data), as in the CE. The number of leerdoelen per opgave and per point is bounded by the CE. |
| D4 | Allowed in a stem and not counted as cueing: explaining a new concept that is not tested (`new_concept`), "gebruik informatiebron n", "gebruik je antwoord op vraag n", a general rounding or basis rule (economie-098). |
| D5 | Double tasks: follow the subject's CE practice (measured per pattern), recorded in the profile, applied as a rule. |
| D6 | Answered: economie-096 (excluded criterion allowed as an input step), 097 (parallel parts = 1 step; planner counts like the labellers), 098 (no named intermediate step), 099 (two sources or an earlier outcome = relationeel). These are generic: apply them for every subject in the planner, labeller and verifier prompts, not only via the economie snapshot. |
| D7 | Spec first, then build in Claude Code; then rerun the economie order (with 90 minutes) and compare. |

## 3. New CE measures (exam bank → reference profile)

### 3.1 Deterministic text metrics — new script `scripts/exam/exam_metrics.py <subject> [--exam <id> …]`

Re-extracts the text of each bank exam from the paths in `register.json` with `exam_text.py` (into a temp dir,
never committed) and writes **counts only** to `B/metrics/<exam_id>.json` (the bank holds no exam text):

- exam: `duration_minutes` (parsed from the cover page "tijdsduur"/"van 13.30 tot 16.30 uur"; when not found,
  `null` and an open intake question; CvTE VWO = 180), `max_score`, `n_opgaven`, `n_vragen`;
- per opgave: `points`, `n_vragen`, `n_groups` (distinct `group_id`s over its linked scorepunten), `words_intro`
  (opgave text before the first vraag), `words_sources` (its informatiebronnen);
- per vraag: `points`, `words_lead` and `words_task` (split as §5.1), `n_tasks` (§5.2), `numbers_lead` (count of
  numbers introduced in the lead that are not in the intro or sources), `pattern` (from labels).

`profile_build.py` reads `B/metrics/` next to `B/labels/` and adds a block `house_rules` to
`referentieprofiel.json` and a section *Huisregels eindexamen* to `referentieprofiel.md`, pooled and per exam:

| Key | Definition |
|---|---|
| `minutes_per_point` | duration / max_score |
| `words_per_point` | (intro + sources + leads + tasks) / points, pooled and p25/p50/p75 per opgave |
| `points_per_opgave` | mean, min, max |
| `vragen_per_opgave` | mean, min, max |
| `groups_per_point` | n distinct groups / points (exam level), and `groups_per_opgave` mean/max |
| `words_task` | p50 and p90 over vragen |
| `words_lead` | p50 and p90 over vragen; share of vragen with an empty lead |
| `numbers_lead` | p50 and p90 over vragen (new data per vraag; storyline proxy) |
| `n_tasks` | per pattern: share of vragen with 1, 2, 3+ tasks; `max_tasks` per pattern = the highest value seen on ≥ 10 % of that pattern's vragen (else 1) |

The conservation check stays. A bank without metrics → the block is absent and the form/order say "geen huisregels
gemeten" and fall back to the seed (`subjects/<s>/toets/seed_profile.json` may carry a `house_rules` block).

### 3.2 Labelled knob changes (specs/26, specs/31 §4)

- **`route` (changed): applies to every pattern**, not only calculation and schema. *gegeven* = the stem names a
  step, method, tool, formula, intermediate quantity or a concept to use, beyond the data and the asked end point
  ("bereken hiervoor eerst", "(koers plus ontvangen dividend)", "gebruik de cpi", "gebruik in je uitleg het begrip
  prijspeil"). *zelf vinden* = only the end point. The D4 items are not route. Shares stay by points; the
  applicability rule in specs/26 §4 and specs/32 §1 becomes "all vragen".
- **`direction` (new, label "Richting", values `open`, `gegeven`)**: *gegeven* = the stem states the conclusion the
  student must explain or show ("leg uit dat …", "toon aan dat …", "… toch …"); *open* = the student must reach the
  conclusion ("leg uit of", "leg uit welk effect", "is … toegenomen of afgenomen?"). Applies to explanation and
  show-that patterns (`kind` in `["explanation", "show"]`), else `null`. Settable; two-valued (disputes go to R).
- Labeller evidence: the stem phrase that gives route or direction.

### 3.3 Relabelling only the changed fields

`/examen --label --subject <s> --fields route,direction [--exam …]`: the labellers get only those fields; `label_merge.py`
updates those fields in `B/labels/<exam_id>.json` and keeps the rest (and its confidence). Then `profile_build.py`.
Same for toetsbank toetsen only when the teacher asks (`toetsbank_relabel` is out of scope).

## 4. Order, form and pause 1 (amends specs/32 and specs/34 §1)

New order fields (schema `toets_order`, also allowed in a template):

```json
"reading_budget_pct": 60,          // % of the CE words per point; null = no budget
"duration_minutes": 90             // existing; now required at pause 1
```

Per-level defaults live in the template (the teacher's `5vwo-toets` gets `reading_budget_pct`); there is no
built-in default per level. `knobs` gains `direction`; `route` shares now count over all vragen.

**Form** (`form_build.py`):
- Section *Toets*: duration with its own label *Toetsduur (minuten)* and a live line "≈ 2,7 min per punt
  (eindexamen: 3,0)"; the matrix total is shown as *Totaal punten (uit de matrijs)*, never as an input next to the
  duration.
- New row *Leesbudget*: slider 30–120 % with the live result "≈ 1.300 woorden (eindexamen: 2.150 voor 33 punten)".
- Next to *Aantal opgaven*: "eindexamen: ≈ 10 punten per opgave → 3 opgaven" with a *Zet op eindexamen* button.
- New knob row *Richting*; the *Route* row loses its "telt alleen over rekenvragen" note.
- Templates load and save `reading_budget_pct`, `duration_minutes` and the new knob.

**Order checks** (`validate_toets.py order`), new:

| Id | Check |
|---|---|
| O7 | warning when minutes per point < 0.75 × CE `minutes_per_point` or > 1.5 ×; error when `duration_minutes` < total points × 0.5 |
| O8 | warning (asked at pause 1, D2) when `n_opgaven` differs from round(total points / CE mean `points_per_opgave`), min 1; the ASK offers *Zoals eindexamen (n)* / *Houden (m)* |
| O9 | warning when the matrix's groups per point > CE `groups_per_point` max over exams, with the options: fewer leerdoelen, more points, or keep |
| O10 | `reading_budget_pct` in 20–150 or null |

**Pause 1 summary** always shows: duration and minutes per point vs CE, the reading budget in words vs CE, the
number of opgaven vs the CE proposal, groups per point vs CE, and the O7–O9 warnings, before *Akkoord / Aanpassen*.

## 5. Blueprint and writing (amends specs/33 T2–T3, specs/31 §5)

### 5.1 Question form: lead + task

Items schema: a vraag has `lead` (optional, the context lines above the vraag: new facts for this step of the
storyline) and `task` (required: the asking sentence(s)), replacing `stem`. Old items with `stem` (toetsbank, reuse)
are read as `lead: ""`, `task: stem`. The export prints the lead as plain paragraphs **above** the points line and
the task on the line "2p **3** <task>", as the CE does. `student_build.py` likewise.

`task` rules (checked, §6): it starts with an asking verb of the pattern's `stem_forms` or is a direct question;
≤ CE `words_task` p90 (economie ≈ 30 words; the exact value comes from the profile); `n_tasks` ≤ the pattern's
`max_tasks` (D5). More tasks than allowed → the planner splits the vraag (two vragen) at T2.

`lead` rules: ≤ CE `words_lead` p90 × `reading_budget_pct`; new numbers in the lead ≤ CE `numbers_lead` p90.

### 5.2 Counting tasks (`n_tasks`)

Deterministic, shared by `exam_metrics.py` and `items_check.py` (`scripts/toets/tasks.py`): split the task into
sentences; count the sentences that start with an asking verb or end in "?"; add 1 for each further asking verb
joined by "en" ("Bereken … en leg uit …"). A follow-up "Licht je antwoord toe" / "Motiveer je antwoord" after a
question counts as part of that task, not as a new one (CE form).

### 5.3 Storyline per opgave (planner)

Blueprint per opgave gets `storyline: {problem, actors[], shared_data[], steps[]}` and per vraag `story_step` (the
index in `steps`). Planner rules:
- number of opgaven as in the confirmed order (D2 proposal applied at pause 1); points per opgave within the CE
  min–max where the total allows;
- the vragen of an opgave are consecutive steps of one problem with the same actors and data; a vraag adds at most
  the CE `numbers_lead` p90 new numbers;
- groups per opgave ≤ CE `groups_per_opgave` max; cluster groups that belong together (same subdomein first);
- plan `n_tasks` per vraag within the pattern's `max_tasks`;
- apply D6 when planning `steps` and `solo`.

`bouwplan.md` shows per opgave the storyline (problem, actors, the steps with their vragen) above the vraag table.

### 5.4 Writer rules (`toets-writer.md`, also letter R)

- Write `lead` and `task` separately; the task is short and has the planned number of tasks.
- **No cueing beyond the plan**: no route and no direction unless the blueprint knob says *gegeven*; never define or
  name, in the intro, lead or task, a concept that a scorepunt of the vraag tests (*term giveaway*); never put a
  solution step in brackets. D4 items are allowed.
- To make a vraag unambiguous, make the **situation** precise (period, unit, basis, who), never the method
  (economie-098). A general rounding or basis rule is allowed.
- Respect the reading budget per opgave given in the prompt (computed by the orchestrator, §6 RB).
- Realism: facts stated as true in the context must be true in the real world for the toets year, or be marked as a
  simplification once in the opgave ("In deze opgave is …").
- Calibration examples: read `subjects/<s>/toets/conventions.md` §*Voorbeelden van de docent* (good and bad vragen
  with the reason); form only.

## 6. Checks (amends specs/34 §2–§3)

| Id | Script | Check |
|---|---|---|
| BP11 | blueprint_check | points per opgave within CE min–max (warning when the total does not allow it); groups per opgave ≤ CE max; every vraag has `story_step`; planned `n_tasks` ≤ `max_tasks` |
| BP12 | blueprint_check | warning when planned knob shares already sit outside tolerance (CLAUDE.md, toets run 2) |
| IT8 | items_check | form: `task` present, starts with an asking verb or is a question, ≤ `words_task` limit; `n_tasks` = planned and ≤ `max_tasks` |
| IT9 | items_check | cue scan (advisory, goes to the verifier): stem phrases from `data/toets/cue_phrases.json` (route: "bereken hiervoor eerst", "gebruik de/het <term>", "(… plus …)", "met behulp van"; direction: "toch", "leg uit dat", "toon aan dat") where the vraag's planned `route`/`direction` is *zelf vinden*/*open*; D4 phrases are allowlisted |
| IT10 | items_check | term giveaway (error when terms are known): a concept of the vraag's scorepunt criteria (group `concepts` ∪ glossary entries matching the criterion text) occurs in the intro, lead or task of the vraag while the scorepunt asks to name, describe, recognise or apply that concept; when the criteria have no concepts (economie restored run), advisory only |
| RB | items_check | reading budget: words of intro + sources + leads + tasks of the opgave ≤ opgave points × CE `words_per_point` × `reading_budget_pct` × 1.1; toets total likewise |
| IT11 | items_check | lead: words ≤ limit, new numbers ≤ limit (§5.1) |

`cue_phrases.json` is a rule file in `data/toets/` (rules live in data), with a per-subject overlay in
`subjects/<s>/toets/cue_phrases.json` when needed.

## 7. Verifier (amends specs/34 §5)

- **V6 changed**: an ambiguity is fixed by making the situation precise; a `fix_hint` that adds a step, method,
  tool, concept or conclusion to the stem is not allowed (the verifier checks its own hints against IT9).
- **V11 new — cueing**: route, direction and term giveaway realised vs plan; uses IT9/IT10 hits and the labels.
  A term giveaway is `must`.
- **V12 new — readability and storyline**: reading level fits `level`; the lead adds only what this step needs; the
  vraag belongs to the opgave's storyline; double tasks only within `max_tasks`.
- V8 gains: facts must be realistic or marked as a simplification (§5.4).
- The verifier's `proposed_decisions` must follow `schemas/decisions.schema.json` (`applies_to` roles,
  `impact` high|medium|low); `validate_toets.py verification` checks it.

## 8. Export and verantwoording (amends specs/35)

- Leerling version: lead above, "2p **3** task" on its own line; the cover prints the duration from the order.
- Verantwoording gains a section *Huisregels* with per rule: ordered, realised, CE: minutes per point, words
  (total and per opgave) vs budget, points and vragen per opgave, groups per opgave, tasks per vraag, route and
  direction shares, term-giveaway hits.

## 9. Migration of existing subjects

1. `exam_metrics.py economie` and `exam_metrics.py bedrijfseconomie` (needs the exam PDFs under `input/`, present
   on the teacher's PC), then `profile_build.py <s>`.
2. `/examen --label --subject <s> --fields route,direction` for economie (3 exams) and bedrijfseconomie (2 exams),
   then `profile_build.py <s>`.
3. Template `subjects/bedrijfseconomie/toets/sjablonen/5vwo-toets.json`: add `reading_budget_pct` (teacher sets the
   value; ask) and `direction` (*Zet op eindexamen* after step 2).
4. `conventions.md` per subject gets a section *Voorbeelden van de docent*. For economie the straat drafts it from
   the 2026-11-17 review (good: vragen 1, 2, 3, 6, 7, 8, 10, 11, 15; bad with reason: 4 double task and wrong price
   index, 5 step in brackets, 9 cumbersome, 12, 13 direction and prescribed concept, 14 step named, 16 term
   giveaway, 17 too long) as `conventions.voorstel.md`; the teacher approves and renames it (the straat never writes
   `conventions.md`).
5. CLAUDE.md: replace the toets-run-1 lesson "Writers should state these in the stem by default" with "Disambiguate
   the situation, never the method (economie-098, specs/36 §5.4)".
6. Toetsbank toetsen are not relabelled.

## 10. Build order and acceptance

1. Schemas: `toets_order` (+ `reading_budget_pct`, `direction`), `toets_items` (`lead`, `task`; `stem` legacy),
   `blueprint` (`storyline`, `story_step`, `n_tasks`), `reference_profile` (`house_rules`), knobs.json (`route`
   applicability, `direction`), `cue_phrases.json`.
2. `scripts/toets/tasks.py`, `scripts/exam/exam_metrics.py`, `profile_build.py` (house rules), `/examen --fields`.
3. Form, order checks O7–O10 and the pause-1 summary; fix the duration field.
4. Planner prompt and blueprint checks BP11–BP12; `blueprint_report.py` storyline.
5. Writer prompt (also R), items checks IT8–IT11 and RB, `student_build.py`, export.
6. Verifier V6/V11/V12, proposed-decision schema.
7. Fixture: extend `tests/run_toets_fixture.py` with a two-opgave toets that has one term giveaway, one route cue,
   one double task and one over-budget opgave; each must be caught by its check. Add a metrics fixture to
   `tests/run_examen_fixture.py`.
8. Migration §9 on the teacher's PC.
9. Acceptance run: the economie 4 VWO P2 order with `duration_minutes: 90`, `reading_budget_pct` as the teacher sets,
   `n_opgaven` as proposed. Compare with run 20261115-2242: total words, words per opgave, IT9/IT10 hits (target 0),
   double tasks (target ≤ CE), vragen per opgave, and the teacher's own ✓-rate (run 3: 9/17).
