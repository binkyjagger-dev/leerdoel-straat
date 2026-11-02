---
description: Examen-straat — link central exams (CvTE opgaven + correctievoorschrift) per scorepunt to the success criteria of a /generate run and add them to the subject's cumulative exam bank: ingest → intake (one pause) → candidates → two judges per opgave → merge → verifier + one repair round → bank → export (points per criterion/leerdoel/domein, lookup index).
argument-hint: <exam-folder> [<exam-folder> ...] --subject <slug> [--from <generate-run-id>] [--replace] [--rebuild] [--run-id <id>]
allowed-tools: Bash, Read, Write, Glob, Agent, AskUserQuestion, TaskCreate, TaskUpdate
---

You are the **orchestrator** of the examen-straat. You own control flow and files; you never judge links, write quotes or set points yourself. Follow `specs/23-examen-pipeline.md` and `specs/24-examen-verification.md`. Arguments: `$ARGUMENTS`. Python command: `python3` if `python3 --version` succeeds, else `python` (on Windows `python3` can be the Microsoft Store stub) — use that spelling everywhere and tell every subagent which one. Scratch directory for subagents' helper files: the session scratchpad if you have one, else `runs/<run_id>/_scratch/` — tell every subagent; nothing else is written into the run folder by agents.

If a new agent type (`exam-ingest`, `exam-judge`) is not available in this session, launch a general-purpose agent whose prompt starts with "Act as the agent defined in `.claude/agents/<name>.md` (read it first)."

## E0 Set up
- Parse: one or more exam folders (a folder with `*-o.pdf` and `*-c.pdf`, or a parent folder with one subfolder per exam), `--subject`, optional `--from` (a `/generate` run id), `--replace`, `--rebuild`, `--run-id` (default `YYYYMMDD-HHMM-examen-<subject>`).
- `python3 scripts/decisions.py init <subject>` (idempotent).
- Bank `B = subjects/<subject>/examenbank`. Criteria version:
  - bank exists, no `--rebuild`: `criteria_run` = the register's; `--from`, when given, must equal it — else stop and tell the user to use `--rebuild`.
  - no bank: `--from` is required.
  - `--rebuild --from <new>`: move `B` to `subjects/<subject>/examenbank.<old criteria_run>/` (ask the user first with AskUserQuestion; this is the one destructive step); the exam folders = the folders of every `files.o` in the old register, plus any given on the command line.
- Exams already in the bank (exam id from the file name, `vw-0400-a-25-1-o.pdf` → `vwo-2025-tv1`): without `--replace`, ask the user once (AskUserQuestion) per batch: replace or skip them — before any agent runs.
- Create `R = runs/<run_id>/` with `text/`. Criteria: copy `runs/<criteria_run>/04_groups_student.json` → `R/20_criteria.json` and `runs/<criteria_run>/01_source_units.json` → `R/20_source_units.json`; when the run folder is gone and the bank exists, copy `B/criteria.json` and `B/source_units.json` instead. Write `run.json`: `{run_id, subject, criteria_run, exams: [], judge_batch: 4, max_repair_rounds: 1, status: "running", started_at}`.
- Task list E1–E6.

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
`python3 scripts/exam/bank_add.py R` (add `--replace` when the user chose to replace) → `B/register.json`, `B/links/<exam_id>.json` (and on first use `B/criteria.json`, `B/source_units.json`). Then `python3 scripts/exam/bank_export.py <subject>` → `B/output/`, and `python3 scripts/exam/exam_sample.py R` → `R/output/steekproef.md` (10 high + 10 low/medium links for the teacher). Set `status: "done"`, `finished_at`.

## Report (≤ 10 lines)
Per exam: scorepunten, points linked / *buiten huidige syllabus* (of max), confidence split, Bloom split, *examen boven/onder criterium*, disputes left. Bank: number of exams, criteria never tested. New open decisions. Paths: `B/output/opzoekindex.csv`, `punten_per_leerdoel.csv`, `examenbank.xlsx`, `overzicht.md`, `bevindingen.md`.

## Rules
- Paths not contents in prompts. Never write a link, quote, Bloom level or point yourself. Never answer a decision yourself.
- Keep every intermediate file (`.round<N>` copies). Exam text stays in `R/text/` (git-ignored) and never goes into the bank or its output beyond quotes ≤ 25 words.
- The bank is bound to one criteria run; never mix.
