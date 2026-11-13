# 34 — Toets-straat: verification

Three layers, in this order: **deterministic checks** (scripts, never skipped), the **blind solver** and
the **labellers** (fresh agents that do not know the plan), and the **verifier** (fresh agent, critiques
only, never rewrites).

## 1. Order checks (`validate_toets.py order`)

| Id | Check |
|---|---|
| O1 | schema `toets_order` |
| O2 | every `group_id` in the matrix exists in `30_criteria.json`; `criteria_include/exclude` ids exist |
| O3 | each knob is `"vrij"` or a share map over valid values that sums to 1 (± 0.001); `bloom_mix` likewise, and no `creëren` |
| O4 | `n_vragen ≥ n_opgaven`; `n_vragen ≤ total points` |
| O5 | `reuse` entries exist in the toetsbank and belong to the same criteria run; their points do not exceed the matrix of their groups |
| O6 | feasibility warnings (not errors): a Bloom level with points but no criterion in the matrix that allows it (criterion Bloom + 1); `route` shares on a toets without calculation groups |

## 2. Blueprint checks (`blueprint_check.py`, writes `32_blueprint.check.json` and, with `--write`, `planned_shares`)

| Id | Check |
|---|---|
| BP1 | schema `blueprint`; ids unique; `number` runs 1…n over the toets |
| BP2 | number of opgaven and vragen = order |
| BP3 | points per group (sum of scorepunten by the criterion's group) = matrix, **exact**; vraag points = sum of its scorepunten |
| BP4 | every criterion in the matrix's groups and not excluded; reused opgaven untouched |
| BP5 | pattern exists, not retired; scorepunt Bloom ∈ pattern `bloom`; scorepunt Bloom ≤ criterion Bloom + 1 |
| BP6 | knob applicability and `knobs_fixed` (specs/31 §5); `builds_on` only to earlier vragen of the same opgave |
| BP7 | Bloom mix within ±5 pp per level; knob shares within ±10 pp per value; slack rule (specs/32 §4); `"vrij"` knobs not checked |
| BP8 | no context with a `context_tags` pair from the history or matching `avoid_contexts`; no two opgaven of the toets with the same first tag |
| BP9 | `needs_figure` patterns have a planned figure; P15 is the last vraag of its opgave |
| BP10 | coverage report per group: tested and untested criteria (information, not an error) |

## 3. Item checks (scripts, per opgave)

`items_check.py`:

| Id | Check |
|---|---|
| IT1 | schema `toets_items`; vraag ids, numbers and points = blueprint; scorepunten (seq, points, criterion) = blueprint |
| IT2 | cv: `maximumscore` = points; scorepunt points sum to it; every scorepunt has text |
| IT3 | every number in stem, sources, tables and the uitwerkbijlage is in `data` (number scanner on the Dutch notation `1.250,50`, `9%`, `€ 3,42`); every number in the cv's `model_answer` is in `data` or a `calc.shown` |
| IT4 | `noise_data` exists only when the vraag's `sources` is *meerdere bronnen met ruis* and then is not empty; every `uses_data` key is used by some `calc` or named in the model answer |
| IT5 | `builds_on_vragen` = blueprint; when `builds_on = ja`, at least one `calc` uses a name from an earlier vraag and the cv has a `follow_through` sentence |
| IT6 | conventions: € notation, btw default from `conventions` / `conventions.md`, a reference "zie informatiebron n" for each source the vraag uses, the uitwerkbijlage sentence for schema vragen |
| IT7 | the stem's asking verb fits the pattern's `stem_forms` (advisory, like MB2) |

`calc_check.py` (CC): evaluates every `calc.expr` with a safe evaluator (Python `ast`, only numbers,
names, `+ - * / ** ( )`, `min`, `max`, `round`, `abs`, `sum`) over `data` plus earlier `calc` names (also
across vragen of the same opgave). The rounding is per `round`/`rounding`. The result, formatted in
Dutch notation, must equal `shown`. It also fails on an unused `calc`, and on a `calc` whose name a
scorepunt `calc_ref` points to but that does not exist.

`figures.py` (FG): renders every figure spec (specs/35 §3) and fails when a spec value is not in `data`
or not computed by a `calc`, or when an answer line in `answer_spec` contradicts a `calc` (e.g. an
equilibrium price that differs from the calculated one).

`overlap_check.py` (OV): 8-word shingles (lower case, numbers masked) of stem + sources + model answer
against the style examples in `33_examples/` **and** against all exam text of the bank's exams in
`R/text/` when present. Any shared shingle fails. A shared ≥ 5-word technical phrase ("voor elke fout 1
scorepunt in mindering brengen") is on an allowlist in `conventions.md`.

## 4. Blind solver and labellers

**Solver.** Fresh agent per opgave. It gets only `34_student/<opgave>.md` and the figure PNGs (and the
formula sheet when the subject has one, `subjects/<s>/toets/formuleblad.md`). It answers every vraag
as a strong student would, names every number, and reports ambiguity: a vraag that allows two
reasonable readings, missing data, a source that contradicts the stem. `solver_compare.py`
(SC) produces per calculation vraag `match | mismatch | partial` and passes the ambiguity notes on.

**Labellers.** `item-labeller` A and B in toets mode label every vraag exactly as exam questions are
labelled (specs/26 §2): pattern, solo, route, steps, sources, claim, new_concept, schema, builds_on,
with evidence. Merge and R round as in specs/26 §3. The merged labels are the **realised** knob
values. `realized.py` computes the realised shares; differences from the blueprint per vraag go to the
verifier as `label_vs_plan` items.

## 5. Verifier (`toets-verifier`, fresh context)

Gets: `31_order.json`, `32_blueprint.json`, `33_items/`, `33_checks/`, `34_solver_compare.json`,
`34_labels.json` + `34_realized.json`, `30_criteria.json`, `30_patterns.json`, the decisions snapshot.
It does not get the writers' notes, planner notes or the style examples. Per vraag a verdict
`pass | repair` with findings; per finding `{id, vraag_id, severity: must|should, evidence (≤ 25 words
quoted), fix_hint}`.

| Id | Judges |
|---|---|
| V1 | **Criterion fit**: each scorepunt tests its criterion: the point is earned exactly when the student shows that performance |
| V2 | **Correctness**: model answer, alternatives and rules are correct and complete; every reasonable correct answer scores (solver mismatches and ambiguity notes are evidence) |
| V3 | **Bloom realised** per scorepunt vs planned (novelty of the context decides, not the verb; specs/02) |
| V4 | **Pattern realised** (the labellers' pattern vs planned; the verifier decides when they differ) |
| V5 | **Knobs realised** per vraag (label vs plan); a deviation is `must` only when it breaks the toets-level tolerance |
| V6 | **Unambiguous**: one reading; the asked quantity, period and unit are clear; the uitwerkbijlage fits the vraag |
| V7 | **Within the criteria**: nothing is needed beyond the order's criteria, except `new_concept` explained in the stem or a source |
| V8 | **Context**: plausible, consistent within the opgave (numbers, names, periods), suitable for the level, no stereotypes |
| V9 | **Toets level**: Bloom mix and knob shares realised within tolerance; matrix exact (from `34_realized.json`) |
| V10 | **Independence**: no vraag gives away the answer of another; a `builds_on` chain does not make a later vraag unanswerable after an early error (follow-through rule present) |

Findings that would need a subject decision go to `proposed_decisions` (as specs/04). The verifier
grades decision deviations as V7 or V8, not V2.

## 6. What the teacher sees

- `output/twijfellijst.md`: every finding left after round 2, every check warning (IT7, O6), solver
  ambiguity notes the verifier marked as `should`, and errors the writers or solver found in the exam
  examples (report them; CLAUDE.md, koppel lesson).
- The verantwoording (specs/35 §2) marks each vraag with an open finding.
