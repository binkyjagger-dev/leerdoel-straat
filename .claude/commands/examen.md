---
description: Examen-straat — link central exams (CvTE opgaven + correctievoorschrift) per scorepunt to the success criteria of a /generate run and add them to the subject's cumulative exam bank: ingest → intake (one pause) → candidates → two judges per opgave → merge → verifier + one repair round → bank → export (points per criterion/leerdoel/domein, lookup index) → E7 pattern/knob labels and the reference profile (specs/26). `--label` labels exams already in the bank (E0 + E7 only).
argument-hint: <exam-folder> [<exam-folder> ...] --subject <slug> [--from <generate-run-id>] [--replace] [--rebuild] [--run-id <id>]  |  --label --subject <slug> [--exam <exam_id> ...] [--replace]
allowed-tools: Bash, Read, Write, Glob, Agent, AskUserQuestion, TaskCreate, TaskUpdate
---

You are the **orchestrator** of the examen-straat. You own control flow and files; you never judge links, write quotes or set points yourself. Follow `specs/23-examen-pipeline.md` and `specs/24-examen-verification.md`. Arguments: `$ARGUMENTS`. Python command: `python3` if `python3 --version` succeeds, else `python` (on Windows `python3` can be the Microsoft Store stub) — use that spelling everywhere and tell every subagent which one. Scratch directory for subagents' helper files: the session scratchpad if you have one, else `runs/<run_id>/_scratch/` — tell every subagent; nothing else is written into the run folder by agents.

If a new agent type (`exam-ingest`, `exam-judge`, `item-labeller`) is not available in this session, launch a general-purpose agent whose prompt starts with "Act as the agent defined in `.claude/agents/<name>.md` (read it first)."

## E0 Set up
- With `--label`: follow the section *`--label`* at the end instead (E0 there, then E7 only).
- Parse: one or more exam folders (a folder with `*-o.pdf` and `*-c.pdf`, or a parent folder with one subfolder per exam), `--subject`, optional `--from` (a `/generate` run id), `--replace`, `--rebuild`, `--run-id` (default `YYYYMMDD-HHMM-examen-<subject>`).
- `python3 scripts/decisions.py init <subject>` (idempotent).
- Bank `B = subjects/<subject>/examenbank`. Criteria version:
  - bank exists, no `--rebuild`: `criteria_run` = the register's; `--from`, when given, must equal it — else stop and tell the user to use `--rebuild`.
  - no bank: `--from` is required.
  - `--rebuild --from <new>`: move `B` to `subjects/<subject>/examenbank.<old criteria_run>/` (ask the user first with AskUserQuestion; this is the one destructive step); the exam folders = the folders of every `files.o` in the old register, plus any given on the command line.
- Exams already in the bank (exam id from the file name, `vw-0400-a-25-1-o.pdf` → `vwo-2025-tv1`): without `--replace`, ask the user once (AskUserQuestion) per batch: replace or skip them — before any agent runs.
- Create `R = runs/<run_id>/` with `text/`. Criteria: copy `runs/<criteria_run>/04_groups_student.json` → `R/20_criteria.json` and `runs/<criteria_run>/01_source_units.json` → `R/20_source_units.json`; when the run folder is gone and the bank exists, copy `B/criteria.json` and `B/source_units.json` instead. Write `run.json`: `{run_id, subject, criteria_run, exams: [], judge_batch: 4, max_repair_rounds: 1, status: "running", started_at}`.
- Task list E1–E7.

After each step run its validator; on failure re-launch the same agent once with the output; on a second failure set `status: "aborted"` and stop.

## E1 Ingest
`python3 scripts/exam/exam_text.py R <exam folders…>` → `R/21_exam_units.json`, `R/text/*`, PDFs in `R/input/<exam_id>/`. Put the exam ids in `run.json` `exams`. Then one agent `exam-ingest` per exam, **one after the other** (they edit the same `21_exam_units.json`; parallel agents overwrote each other's edits in run 1), with R and the exam id. Validate: `python3 scripts/exam/validate_exam.py R` (must pass).

## E1b Intake — the only pause
Agent `intake` in **exam mode** with R and the subject → `R/21b_intake_questions.json`. Then as in `/generate` step 1b: `python3 scripts/decisions.py add S R/21b_intake_questions.json --run <run_id>`, present the open decisions with AskUserQuestion (≤ 4 per call, high impact first, the proposal as first option marked "(Aanbevolen)"), record answers (`decisions.py answer-file … --by user --run <run_id>`), `decisions.py snapshot S R`. Apply the answer about each exam's syllabus version to `exams[].syllabus_note` in `21_exam_units.json` (metadata only) and re-run `validate_exam.py`. An answered decision that names synonyms (book/exam term = criterion term) → write the pairs to a JSON list `[{"term": <criterion term>, "synonyms": [...]}]` and run `python3 scripts/glossary.py add S <id> <file>` **before** the candidates step (specs/06 §8).

## E2 Candidates
`python3 scripts/exam/exam_candidates.py R` → `R/22_candidates.json`.

## E3 Judges (two, independent, per opgave)
For every opgave launch agent `exam-judge` twice — letter `A` and letter `B` — as **separate Agent calls in the same message** (never one agent doing both), output `R/23_judgements.A/<opgave_id>.json` and `…B/…`. Up to `judge_batch` opgaven per message (= 2 × batch agents); wait for a batch before the next. Prompt per judge: R, subject, letter, opgave id, output path, Python command, scratch directory, "decisions in `R/decisions_snapshot.json` apply (answers in `effective_answer`)", and "judge every scorepunt of the opgave".

## E4 Merge
`python3 scripts/exam/exam_merge.py R` → `R/24_mappings.json`, `R/24_findings.json`. A judge file missing scorepunten (ES1) → re-launch that judge once for its opgave. Then `python3 scripts/exam/check_exam_mappings.py R` (must pass).

## E5 Verify + one repair round
1. Agent `mapping-verifier` (fresh) in **exam mode** with R and the subject → `R/25_verification.json`; then `python3 scripts/exam/check_exam_mappings.py R --verification 25_verification.json`.
2. Repair, once: collect disputed links (`verdict: dispute`) and `missing_links`, grouped by opgave (scorepunt → question → opgave). Per such opgave one `exam-judge` with letter `R`, the list of scorepunten to re-judge, pointers to the A/B files and `25_verification.json` → `R/23_judgements.R/<opgave_id>.json`. Copy `24_mappings.json` → `24_mappings.round1.json`; rerun `exam_merge.py R`, then `check_exam_mappings.py R --verification 25_verification.json`.
3. Verifier `proposed_decisions` → write them as `{"questions": [...]}` to `R/25_proposed_decisions.json` and `decisions.py add S R/25_proposed_decisions.json --run <run_id>` (open, for the next intake).

## E6 Bank and export
`python3 scripts/exam/bank_add.py R` (add `--replace` when the user chose to replace) → `B/register.json`, `B/links/<exam_id>.json` (and on first use `B/criteria.json`, `B/source_units.json`). Then `python3 scripts/exam/bank_export.py <subject>` → `B/output/`, and `python3 scripts/exam/exam_sample.py R` → `R/output/steekproef.md` (10 high + 10 low/medium links for the teacher).

## E7 Label (specs/26) — pattern and knob labels, reference profile
1. For every opgave launch agent `item-labeller` twice — letter `A` and letter `B` — in **exam mode**, as **separate Agent calls in the same message**, output `R/26_labels.A/<opgave_id>.json` and `…B/…`. Up to `judge_batch` opgaven per message. Prompt per labeller: R, subject, "exam mode", letter, opgave id, output path, Python command, scratch directory, "decisions in `R/decisions_snapshot.json` apply (answers in `effective_answer`)", "label every question of the opgave". Never tell a labeller what the other labeller said.
2. `python3 scripts/exam/label_merge.py R` → `R/26_labels.json`, `R/26_label_findings.json`, `R/26_proposed_patterns.json`. A labeller file missing questions or failing the schema (LB1) → re-launch that labeller once for its opgave. Then `python3 scripts/exam/check_labels.py R`; an LB2–LB5 failure → re-launch that labeller once with the report lines for its opgave, then merge and check again.
3. Repair, once: per opgave with `disputed` fields (`26_label_findings.json`), one `item-labeller` letter `R` with the list of questions and fields, pointers to the A/B files and the findings → `R/26_labels.R/<opgave_id>.json`. Copy `26_labels.json` → `26_labels.round1.json`; rerun `label_merge.py R` and `check_labels.py R`. No verifier: R decides. Disputes left stay `disputed` and are left out of the profile.
4. New patterns: when `R/26_proposed_patterns.json` has `questions`, `python3 scripts/decisions.py add S R/26_proposed_patterns.json --run <run_id>` (open, `applies_to: ["catalogue"]`, for the next intake). Never add a pattern yourself: only `scripts/toets/patterns.py add` against an answered decision changes the catalogue.
5. `python3 scripts/exam/bank_labels_add.py R` (add `--replace` when the user chose to replace) → `B/labels/<exam_id>.json`.
6. `python3 scripts/exam/profile_build.py <subject>` → `B/profiel/referentieprofiel.json`, `referentieprofiel.md`, `patronen_stats.json` (rebuilt from all labels of the bank; fails on a conservation error — then report, do not edit the profile).

Set `status: "done"`, `finished_at`.

## `--label` — label exams already in the bank (E0 + E7 only)
`/examen --label --subject <s> [--exam <exam_id> …] [--replace]`:
- E0 without criteria judgement: bank `B` must exist; `criteria_run` = the register's. Exams = the `--exam` ids, default every exam in `B/register.json` without `B/labels/<exam_id>.json` (with `--replace`: the named exams even when labelled). None left → say so and stop.
- Create `R` with `text/`; `run.json`: `{run_id, subject, criteria_run, exams, label_only: true, judge_batch: 4, status: "running", started_at}` (run id default `YYYYMMDD-HHMM-examen-<subject>-label`). Copy `B/criteria.json` → `R/20_criteria.json`, `B/source_units.json` → `R/20_source_units.json`; `decisions.py snapshot S R`.
- Re-extract the text: `python3 scripts/exam/exam_text.py R <the folders of each exam's files.o in the register>` and `python3 scripts/exam/validate_exam.py R`. When it fails, run `exam-ingest` per exam as in E1 (one after the other) and validate again. A PDF that is missing at its register path → ask the user for the folder; skip that exam if there is none.
- Then E7 steps 1–6. The links come from the bank (`label_merge.py` reads `B/links/` when `R` has no `24_mappings.json`); `bank_labels_add.py` checks that every question's points equal its scorepunten in the bank.
- Report: per exam questions labelled, field confidence split, disputes left, new-pattern proposals, the profile's label and path `B/profiel/referentieprofiel.md`.

## Report (≤ 10 lines)
Per exam: scorepunten, points linked / *buiten huidige syllabus* (of max), confidence split, Bloom split, *examen boven/onder criterium*, disputes left. Labels: questions labelled, disputed fields left, new-pattern proposals. Bank: number of exams (labelled), criteria never tested, the reference profile's label. New open decisions. Paths: `B/output/opzoekindex.csv`, `punten_per_leerdoel.csv`, `examenbank.xlsx`, `overzicht.md`, `bevindingen.md`, `B/profiel/referentieprofiel.md`.

## Rules
- Paths not contents in prompts. Never write a link, quote, Bloom level, point or label yourself. Never answer a decision yourself. Never edit `B/profiel/` by hand.
- Keep every intermediate file (`.round<N>` copies). Exam text stays in `R/text/` (git-ignored) and never goes into the bank or its output beyond quotes ≤ 25 words.
- The bank is bound to one criteria run; never mix.
