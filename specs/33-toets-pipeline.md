# 33 — Toets-straat: command, roles, run files, orchestration

## 1. Command

```
/toets [<toetsopdracht.json>] --subject <slug> [--run-id <id>] [--from-blueprint <run_id>]
/toets --formulier <slug>
```

- `--from-blueprint`: start at T3 from an approved blueprint of an earlier run (rewrite with the same
  plan, e.g. a B version of a toets). It copies `31_order.json`, `32_blueprint.json` and the review.
- Run id default `YYYYMMDD-HHMM-toets-<subject>`. Python command and scratch directory as in
  `/examen` (`.claude/commands/examen.md`). Agents unknown in the session → general-purpose agent
  that reads `.claude/agents/<name>.md` first (CLAUDE.md, koppel lesson).

## 2. Roles

| Role | Kind | Reads | Writes |
|---|---|---|---|
| orchestrator (`/toets`) | command | everything | `run.json`, copies, the review file (§3 T2b), never content |
| `toets-planner` | agent | order, criteria, catalogue, knobs, reference profile, context history, `contexten.md`, decisions snapshot | `32_blueprint.json` |
| `toets-writer` | agent, 1 per opgave | blueprint (own opgave), criteria of its scorepunten, catalogue, `conventions.md`, style examples, decisions snapshot, glossary | `33_items/<opgave>.json` |
| `toets-solver` | agent, fresh, 1 per opgave | **student version only** (`34_student/<opgave>.md` + figure PNGs) | `34_solutions/<opgave>.json` |
| `item-labeller` | agent, A and B, toets mode | student version + cv of one opgave, knobs, catalogue (no blueprint) | `34_labels.{A,B}/<opgave>.json` |
| `toets-verifier` | agent, fresh | order, blueprint, items, check reports, solver comparison, merged labels, criteria | `35_verification.json` |
| `toets-writer` (letter R) | agent, repair | as writer + its own items + the verifier findings for that opgave | `33_items/<opgave>.json` (previous kept as `.round<N>.json`) |

The labeller is the **same agent** as in `/examen` E7 (specs/26). Realised knob values are measured
with the same instrument as the reference profile, so "realised vs central exam" compares like with
like. The labeller never sees the blueprint.

## 3. Steps

### T0 Set up
- `decisions.py init <s>`; bank `B = subjects/<s>/examenbank` must exist with `criteria.json`. Without a
  bank, stop: the toets-straat needs a criteria version (specs/30 §2).
- Create `R = runs/<run_id>/` with `input/`, `output/`, `33_items/`, `34_student/`, `figures/`.
- Copy `B/criteria.json` → `R/30_criteria.json`, the reference profile (or seed) →
  `R/30_reference_profile.json`, the catalogue (base + subject merged by `patterns.py merged`) →
  `R/30_patterns.json`, `data/toets/knobs.json` → `R/30_knobs.json`, the toetsbank context history →
  `R/30_context_history.json`; `decisions.py snapshot <s> R`.
- `run.json`: `{run_id, subject, level, criteria_run, reference, max_repair_rounds: 2,
  writer_batch: 4, status: "running", started_at}`. Task list T1–T6.

### T1 Order — pause 1
specs/32 §3. `validate_toets.py order R/31_order.json` must pass.

### T2 Blueprint — pause 2

**T2a plan.** Agent `toets-planner` → `R/32_blueprint.json`. Then `blueprint_check.py R` (specs/34
§2). On failure, relaunch the planner with the report (max 2 retries), else abort.

Blueprint (schema `blueprint`):
```json
{"opgaven": [
  {"opgave_id": "O1", "title": "Kapsalon Knipkunst", "context": "kapsalon met twee vestigingen, ...",
   "context_tags": ["dienstverlening", "kapsalon"], "sources_planned": 2, "reused_from": null,
   "vragen": [
     {"vraag_id": "O1-V1", "number": 1, "points": 2, "pattern": "P14",
      "knobs": {"solo": "multistructureel", "route": null, "steps": "2", "sources": "in vraagtekst", "noise": "nee",
                "claim": "nee", "new_concept": "nee", "schema": null, "builds_on": "nee"},
      "builds_on_vragen": [],
      "scorepunten": [{"seq": 1, "points": 1, "criterion_id": "F2.30.3-01-c", "bloom": "begrijpen"},
                      {"seq": 2, "points": 1, "criterion_id": "F2.30.3-01-c", "bloom": "begrijpen"}],
      "intent": "Leerling herkent te betalen en te vorderen btw in de kassabon en de inkoopfactuur.",
      "example_refs": ["vwo-2026-tv1 v5"]}]}],
 "coverage": {"per_group": [{"group_id": "...", "points": 6, "criteria_tested": ["..."], "criteria_not_tested": ["..."]}]},
 "planned_shares": {"bloom": {...}, "knobs": {...}},     // computed by blueprint_check.py --write, not by the planner
 "planner_notes": "..."}
```

Planner responsibilities (prompt content of `.claude/agents/toets-planner.md`):
- hit the matrix exactly; spread the vragen over the opgaven (2–5 per opgave, the last vraag of an
  opgave may be a P15);
- choose patterns and Bloom per scorepunt so that the Bloom mix and the knob shares fit; use the
  P07/P08 choice for `route` and B02 for `schema`;
- one coherent context per opgave in which all its vragen fit; avoid every context in
  `30_context_history.json` (same `context_tags` pair) and in `avoid_contexts`; prefer
  `contexten.md`; vary the branche over the opgaven of one toets;
- pick 1–2 `example_refs` per pattern from `patronen_stats.json`, `example_quality` *goed* first;
- prefer criteria that the matrix would otherwise leave untested inside a group (the blueprint shows
  them, decision 7 of specs/30).

**T2b report and review.** `blueprint_report.py R` → `R/output/bouwplan.md` (Dutch): per opgave the
context and per vraag points, pattern, criteria, Bloom and knobs; then the matrix, the Bloom mix and
the knob shares **planned (order) vs blueprint vs central exam**; then per leerdoel the tested and
untested criteria. The orchestrator sends the file and summarises it in ≤ 10 lines. Then
AskUserQuestion: **Akkoord** / **Context vervangen** / **Vraag aanpassen** / **Opnieuw plannen**.

Changes are transcribed into `R/32_blueprint_review.json` (schema `blueprint_review`): entries
`{target: "O2" | "O2-V3", field: "context" | "pattern" | "knobs.route" | ..., value, note}` or
`{action: "replan", note}`. The orchestrator reads the entries back to the teacher before applying them.
`blueprint_apply.py R` applies field changes deterministically (no agent); a context change
clears the opgave's `context_tags` and the planner fills only the tags. Then `blueprint_check.py R`.
If the check fails because of a teacher change, report it and ask again; the teacher can accept the
deviation (`accept_deviation: true` on the entry). The deviation then goes to the verantwoording. BP1–BP4 and a
scorepunt Bloom above criterion + 1 (BP5) can never be accepted (decided 2026-11-14, bouwvraag 13).
`replan` relaunches the planner with the review notes. Pause 2 ends with **Akkoord**.

### T3 Write
- `exam_examples.py R` → `R/33_examples/<pattern>.md`: per `example_ref` the question, its sources
  and its cv, extracted from the exam PDFs at the paths in the bank register (parsed with
  `exam_text.py` into `R/text/`, git-ignored). If a PDF is missing, the pattern gets only the
  catalogue description, and this is noted in `run.json`.
- One `toets-writer` per opgave, up to `writer_batch` per message, in parallel. Each writer writes only
  its own file. Input: R, opgave id, output path, Python command, scratch dir.
- After each batch: `items_check.py R --opgave <id>` (schema, blueprint conformity, conventions),
  `calc_check.py R --opgave <id>`, `figures.py R --opgave <id>`, `overlap_check.py R --opgave <id>`
  (specs/34 §3). A failing writer is relaunched once with the report; a second failure goes to T5 as
  a finding.

Items (schema `toets_items`), per opgave:
```json
{"opgave_id": "O1", "title": "...", "intro": "...",
 "data": {"prijs_incl": 34.88, "btw": 0.09, "vk_per_knipbeurt": 6.40, "ck_maand": 12000},  // every given number, named
 "noise_data": ["..."],                    // data in the intro (no bron number) a noise = ja vraag does not need
 "sources": [{"n": 1, "title": "...", "kind": "text|table|figure", "text": "...", "table": [[...]], "figure_id": null,
              "uses_data": ["prijs_incl"], "noise_data": ["..."]}],
 "figures": [{"figure_id": "f1", "spec": {...}, "answer_spec": {...}}],     // specs/35 §3
 "vragen": [{"vraag_id": "O1-V2", "number": 2, "points": 3, "stem": "Bereken ... Bereken hiervoor eerst ...",
             "uitwerkbijlage": {"kind": "table", "rows": [...]} ,
             "cv": {"maximumscore": 3, "model_answer": "...",
                    "calc": [{"name": "db", "expr": "prijs_incl / (1 + btw) - vk_per_knipbeurt", "round": 2, "shown": "€ 25,60"},
                             {"name": "bea", "expr": "ck_maand / db", "round": 0, "rounding": "up", "shown": "469"}],
                    "scorepunten": [{"seq": 1, "points": 1, "text": "berekening dekkingsbijdrage", "criterion_id": "...", "calc_ref": "db"}],
                    "rules": ["Voor elke fout 1 scorepunt in mindering brengen."],
                    "alternatives": ["..."], "follow_through": "Een doorrekenfout uit vraag 1 niet opnieuw aanrekenen."},
             "noise_data": [],              // data in this vraag's stem it does not need; only with noise = ja
             "new_concepts": [], "builds_on_vragen": [1]}],
 "writer_notes": "..."}
```

Writer responsibilities: write the stem, sources and cv in the subject's exam conventions; name every
given number in `data` and every computed number in `calc` (the cv's printed numbers are the `shown`
values); put noise data only where `noise = ja` and list them in
`noise_data` — on the source when they sit in a numbered informatiebron, on the opgave when they sit in the
intro, on the vraag when they sit in its stem (specs/34 IT4); make the vraag realise every planned knob and the scorepunten realise the criterion at
the planned Bloom level; use the style examples for **form only**, never their context, numbers or
sentences; use the glossary terms; `level` decides the reading level of stem and context.

### T4 Solve and label (blind, in parallel)
- `student_build.py R` → `R/34_student/<opgave>.md` (stem, sources, uitwerkbijlage, figure paths; no
  cv, no data block, no notes).
- Per opgave in the same message: one `toets-solver` and `item-labeller` A and B (toets mode),
  separate Agent calls. The solver writes per vraag a full answer, with every computed number named
  `{vraag, answer_text, numbers: [{label, value}], confidence, ambiguity_notes}`.
- `solver_compare.py R` → `R/34_solver_compare.json`: per calculation vraag, match the solver's final
  and intermediate numbers against `calc` values (tolerance: equal after the cv's rounding; € to the
  cent); for explanation vragen it lists the solver answer next to the model answer for the verifier.
- `label_merge.py R --toets` → `R/34_labels.json` (the same merge rules and R round as specs/26 §3).
  `realized.py R` → `R/34_realized.json`: realised knob shares and Bloom mix (Bloom per scorepunt from
  the blueprint as written, corrected by verifier V3 findings after T5), with `combination` computed.

### T5 Verify and repair (max 2 rounds)
1. Agent `toets-verifier` (fresh) → `R/35_verification.json` (specs/34 §5); `validate_toets.py
   verification`.
2. Per opgave with a `repair` verdict: `toets-writer` letter R with the findings. It rewrites only the
   failing vragen, but rereads the whole opgave for consistency (CLAUDE.md, run 4 lesson). Keep
   `33_items/<opgave>.round<N>.json`.
3. Rerun T3's checks for that opgave, then T4 for that opgave, then the verifier **only on the
   repaired opgaven** (`--only O2,O3`), merged into `35_verification.roundN.json`.
4. After round 2, every remaining finding goes to `R/output/twijfellijst.md` and the toets is
   exported with the finding marked in the verantwoording. Nothing is dropped.
5. Verifier `proposed_decisions` → `R/35_proposed_decisions.json` → `decisions.py add` (open).

### T6 Export and bank
`export_toets.py R` (specs/35 §1–2), then `toetsbank_add.py R` (specs/35 §4). `status: "done"`.

### Report (≤ 10 lines)
Points per leerdoel (exact?), Bloom mix and knob shares outside tolerance, solver mismatches left,
doubt list count, contexts used, files: `output/<title>-leerling.docx`, `-correctievoorschrift.docx`,
`-verantwoording.docx`, `bouwplan.md`, `twijfellijst.md`.

## 4. Run folder

```
runs/<run_id>/
  run.json  input/toetsopdracht.json
  30_criteria.json 30_reference_profile.json 30_patterns.json 30_knobs.json 30_context_history.json decisions_snapshot.json
  31_order.json
  32_blueprint.json 32_blueprint.check.json 32_blueprint_review.json 32_blueprint.round<N>.json
  33_examples/<pattern>.md  text/ (exam text, git-ignored)
  33_items/<opgave>.json 33_checks/<opgave>.json
  34_student/<opgave>.md 34_solutions/<opgave>.json 34_solver_compare.json
  34_labels.A/ 34_labels.B/ 34_labels.R/ 34_labels.json 34_realized.json
  35_verification.json 35_verification.round<N>.json 35_proposed_decisions.json
  figures/<figure_id>.png figures/<figure_id>-cv.png
  output/
```

## 5. Cost (estimate per toets of 4 opgaven)

1 planner (+ ≤ 2 retries), 4 writers, 4 solvers, 8 labellers (+ ~2 R), 1 verifier, ~2 repair writers
plus their re-solve/re-label (~6) and 1 partial verifier ≈ 30 agent calls. Labelling existing
bedrijfseconomie exams (specs/26) is a one-off of ~50 calls.

## 6. Rules

- Paths not contents in prompts. The orchestrator never writes a vraag, a cv, a label or a verdict.
- Teacher changes go only through `32_blueprint_review.json` and `blueprint_apply.py`.
- The solver and the labellers never see the blueprint or the cv (the labeller sees the cv only to
  read the scoring structure; it gets no blueprint and no writer notes).
- Exam text stays in `R/text/` and `R/33_examples/` (git-ignored). The toetsbank holds no exam text.
- Every intermediate file is kept (`.round<N>`).
