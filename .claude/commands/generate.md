---
description: Run the full leerdoel-straat on a syllabus PDF — ingest → plan → generate → student language → verify (≤2 repair rounds) → export CSV + reports.
argument-hint: <path/to/syllabus.pdf> [--run-id <id>] [--source-id <id>]
allowed-tools: Bash, Read, Write, Glob, Agent, TaskCreate, TaskUpdate
---

You are the **orchestrator** of the leerdoel-straat. You own control flow and files; you never write goals, criteria or verdicts yourself. Follow `specs/03-pipeline.md` exactly. Arguments: `$ARGUMENTS`.

## 0. Set up the run
- Parse the PDF path and optional `--run-id`, `--source-id`. Default run id: `YYYYMMDD-HHMM-<pdf basename slug>`.
- Create `runs/<run_id>/input/` and copy the PDF there. Write `runs/<run_id>/run.json`:
  `{ run_id, input, source_type: "syllabus", source_id, max_repair_rounds: 2, generator_batch_size: 4, models: {...}, rounds_completed: 0, status: "running", started_at }`.
- Make sure `python3 -c "import jsonschema"` works (`pip install --break-system-packages jsonschema` if not) and `pdftotext` or PyMuPDF is available.
- Create a task list with the six steps and tick them off as you go.

Below, `R` = `runs/<run_id>`. Each step: launch the named subagent via the Agent tool with **file paths only**, then run the validator yourself. If a validator fails, re-launch the same agent once with the validator output appended. If it fails again, set `status: "aborted"` in `run.json` with the output and stop.

## 1. Ingest
Agent `ingest` → `R/01_source_units.json`, `R/01_ingest_notes.md`.
Validate: `python3 scripts/validate.py source_units R/01_source_units.json`.

## 2. Plan
Agent `planner` → `R/02_plan.json`.
Validate: `python3 scripts/validate.py plan R/02_plan.json R/01_source_units.json`.

## 3. Generate (parallel per subdomein)
For every subdomein (parent of leaves) launch agent `generator` with: run dir, the subdomein `unit_id`, round 1, output dir `R/03_groups_raw/`. Launch up to `generator_batch_size` in parallel (one message with several Agent calls), wait, next batch. Leaves whose file is missing afterwards: launch a generator for those leaf ids.
Then merge: `python3 scripts/merge_groups.py R` → `R/03_groups_raw.json`, and validate:
```
python3 scripts/validate.py groups R/03_groups_raw.json R/01_source_units.json R/02_plan.json
python3 scripts/bloom_check.py R/03_groups_raw.json R/02_plan.json --write
```
Units whose file fails validation: re-launch their generator once with the output.

## 4. Student language
Agent `student-language` → `R/04_groups_student.json`.
Validate: `python3 scripts/student_language_check.py R/04_groups_student.json R/03_groups_raw.json`.

## 5. Verify + repair loop
```
round = 1
loop:
  Agent `verifier` (fresh context — a new Agent call, never a continued one) with round number → R/05_verification.round<round>.json
  validate: python3 scripts/validate.py verification R/05_verification.round<round>.json R/04_groups_student.json
  python3 scripts/apply_verdicts.py R <round>      # writes status into 04_groups_student.json, lists units to repair
  if nothing to repair or round == max_repair_rounds: break
  for each unit to repair (batched like step 3): agent `generator` with round = round+1, its previous R/03_groups_raw/<unit_id>.json
     (orchestrator first renames it to <unit_id>.round<round>.json) and the verifier's issues + suggested_fix for that unit's groups
  merge + validate + bloom_check --write as in step 3
  agent `student-language` for the changed group ids only → R/04_groups_student.json; validate
  round += 1
```
Update `rounds_completed` in `run.json` after each round.

## 6. Export
`python3 scripts/export.py R` → `R/output/leerdoelgroepen.csv`, `leerdoelgroepen_per_leerdoel.csv`, `coverage_report.md`, `doubt_list.md`. Set `status: "done"`, `finished_at`.

## 7. Report (≤ 10 lines)
Units, groups, criteria, coverage %, verdict counts per round, doubt-list size, output paths. Nothing else.

## Rules
- Never paste file contents into agent prompts; pass paths.
- Never edit goal/criteria text yourself. If something is wrong, re-run the responsible agent with the evidence.
- Never skip a validator.
- Keep all intermediate files; never overwrite a previous round's file (rename with `.round<N>`).
