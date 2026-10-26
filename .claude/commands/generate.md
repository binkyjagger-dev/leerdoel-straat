---
description: Run the full leerdoel-straat on a syllabus PDF — ingest → intake (one pause for the teacher's decisions) → plan → generate → student language → verify (≤2 repair rounds) → export CSV + reports.
argument-hint: <path/to/syllabus.pdf> --subject <slug> [--run-id <id>] [--source-id <id>]
allowed-tools: Bash, Read, Write, Glob, Agent, AskUserQuestion, TaskCreate, TaskUpdate
---

You are the **orchestrator** of the leerdoel-straat. You own control flow and files; you never write goals, criteria, verdicts or decisions yourself. Follow `specs/03-pipeline.md` and `specs/06-subject-profiles.md` exactly. Arguments: `$ARGUMENTS`.

## 0. Set up the run
- Parse the PDF path, `--subject <slug>` (required; if missing, ask once with AskUserQuestion, default = lower-cased subject of the source), optional `--run-id`, `--source-id`. Default run id: `YYYYMMDD-HHMM-<pdf basename slug>`.
- `python3 scripts/decisions.py init <subject>` (idempotent; creates `subjects/<subject>/` with an empty `decisions.json` and a `profile.md` template if absent). If `profile.md` is still the untouched template, tell the user in one line that the straat runs without subject context and that filling `subjects/<subject>/profile.md` improves later runs — then continue.
- Create `runs/<run_id>/input/` and copy the PDF there. Write `runs/<run_id>/run.json`:
  `{ run_id, subject, input, source_type: "syllabus", source_id, max_repair_rounds: 2, generator_batch_size: 4, models: {...}, rounds_completed: 0, status: "running", started_at }`.
- Determine the Python command once: `python3` if `python3 --version` succeeds, else `python` (on Windows `python3` can be the Microsoft Store stub, which exists but fails). Use that spelling everywhere below where `python3` is written, and tell every subagent in its prompt which one to use. Make sure `<python> -c "import jsonschema"` works (`pip install jsonschema`, with `--break-system-packages` where pip demands it) and `pdftotext` or PyMuPDF is available.
- Create a task list with the seven steps and tick them off as you go.

Below, `R` = `runs/<run_id>`, `S` = `<subject>`. Each step: launch the named subagent via the Agent tool with **file paths only** (always include `R` and `S`), then run the validator yourself. If a validator fails, re-launch the same agent once with the validator output appended. If it fails again, set `status: "aborted"` in `run.json` with the output and stop.

## 1. Ingest
Agent `ingest` → `R/01_source_units.json`, `R/01_ingest_notes.md`, and — only when the source defines its own handelingswerkwoorden table — `R/01_verb_table.json`.
Validate: `python3 scripts/validate.py source_units R/01_source_units.json`; if `R/01_verb_table.json` exists: `python3 scripts/verb_table.py validate R/01_verb_table.json`.

## 1b. Intake — the only pause
1. Agent `intake` (fresh context) → `R/01b_intake_questions.json`.
2. `python3 scripts/decisions.py add S R/01b_intake_questions.json --run <run_id>` (appends new questions as `open`; duplicates of existing decisions are skipped).
3. Collect all **open** decisions: `python3 scripts/decisions.py list S --open`. If there are none, continue to step 2 without pausing.
4. **Pause and ask the user.** Use AskUserQuestion, at most 4 questions per call, `high` impact first; each question's options are the decision's `options` (the proposed one first, marked "(voorgesteld)"); the user can always type a free answer. Repeat calls until all open decisions are presented. Write each answer: `python3 scripts/decisions.py answer S <id> "<answer>" --by user --run <run_id>`. Skipped or unanswered decisions stay `open` — the proposed default applies, and the run is marked provisional for the affected units.
   If no user is present (headless run, or AskUserQuestion unavailable), do not wait: continue on proposed defaults and say so in the final report.
5. **Verb table** (specs/06 §7). If the intake asked `handelingswerkwoorden-tabel` and the user answered with adoption: `python3 scripts/verb_table.py install S R/01_verb_table.json --decision <id>` (add `--drop <verb>` for every verb the answer excepts; the script refuses unless the decision is answered). Then, always: `python3 scripts/verb_table.py effective S --out R/bloom_verbs_effective.json`. Every later agent reads that file as its verb table.
6. `python3 scripts/decisions.py snapshot S R` → `R/decisions_snapshot.json`. Every later agent reads this file; never the live `decisions.json`.

## 2. Plan
Agent `planner` → `R/02_plan.json`.
Validate: `python3 scripts/validate.py plan R/02_plan.json R/01_source_units.json`.

## 3. Generate (parallel per subdomein)
For every subdomein (parent of leaves) launch agent `generator` with: `R`, `S`, the subdomein `unit_id`, round 1, output dir `R/03_groups_raw/`. Split a subdomein with more than ~14 leaves over two calls with explicit leaf lists. Launch up to `generator_batch_size` in parallel (one message with several Agent calls), wait, next batch. Leaves whose file is missing afterwards: launch a generator for those leaf ids.
Then merge: `python3 scripts/merge_groups.py R` → `R/03_groups_raw.json`, and validate:
```
python3 scripts/validate.py groups R/03_groups_raw.json R/01_source_units.json R/02_plan.json
python3 scripts/bloom_check.py R/03_groups_raw.json R/02_plan.json --write --subject S
```
Units whose file fails validation: re-launch their generator once with the output.

## 4. Student language
Agent `student-language` → `R/04_groups_student.json`.
Validate: `python3 scripts/student_language_check.py R/04_groups_student.json R/03_groups_raw.json`.

## 5. Verify + repair loop
```
round = 1
loop:
  python3 scripts/coverage.py R/01_source_units.json R/04_groups_student.json R/02_plan.json --out R/coverage.json
  Agents `verifier` (fresh contexts — new Agent calls, never continued ones), one per domain or per ~50 groups, in parallel,
     each writing R/05_verification.round<round>.part-<scope>.json (round 1) — or ONE verifier for only the repaired group ids (round ≥ 2)
  merge the parts into R/05_verification.round<round>.json (coverage from coverage.json; round ≥ 2: keep round-1 verdicts for untouched groups)
  validate: python3 scripts/validate.py verification R/05_verification.round<round>.json R/04_groups_student.json
  python3 scripts/apply_verdicts.py R <round>      # writes status into 04_groups_student.json, lists units to repair
  if the verification has proposed_decisions[]: python3 scripts/decisions.py add S <file-with-those-as-"questions"> --run <run_id>  (they stay open until the next run's intake)
  if nothing to repair or round == max_repair_rounds: break
  for each unit to repair (batched like step 3): agent `generator` with round = round+1, its previous R/03_groups_raw/<unit_id>.json
     (orchestrator first copies it to <unit_id>.round<round>.json) and the path of R/repair.round<round>.json
  copy R/03_groups_raw.json → .round<round>.json and R/04_groups_student.json → .round<round>.json; merge + validate + bloom_check --write as in step 3
  compute the changed group ids (flagged, or expert text/criteria differ from the previous raw) → R/redo_student.round<round+1>.json
  agent `student-language` for those group ids only (copy the rest from the previous student file) → R/04_groups_student.json; validate
  round += 1
```
Update `rounds_completed` in `run.json` after each round.

## 6. Export
`python3 scripts/export.py R` → `R/output/leerdoelgroepen.csv`, `leerdoelgroepen_per_leerdoel.csv`, `coverage_report.md`, `doubt_list.md`. Set `status: "done"`, `finished_at`.

## 7. Report (≤ 10 lines)
Units, groups, criteria, coverage %, verdict counts per round, decisions answered / still open, verb table (generic, or subject table + number of reclassified verbs), doubt-list size, output paths. Nothing else.

## Rules
- Never paste file contents into agent prompts; pass paths.
- Never edit goal/criteria text yourself. If something is wrong, re-run the responsible agent with the evidence.
- Never answer a decision yourself and never write `profile.md`; only `scripts/decisions.py` touches `decisions.json` and only `scripts/verb_table.py install` touches `subjects/<S>/bloom_verbs.json`.
- Never skip a validator.
- Keep all intermediate files; never overwrite a previous round's file (copy to `.round<N>` first).
