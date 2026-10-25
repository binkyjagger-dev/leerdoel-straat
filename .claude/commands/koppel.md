---
description: Methode-straat — link the success criteria of a /generate run to the paragraphs of a textbook (part A) and, with --part AB, to its exercises (part B): ingest → intake (one pause) → candidates → two judges → gradation → verifier → export CSV + reports (+ baseline comparison).
argument-hint: <book.pdf> --subject <slug> --method <method_id> --from <generate-run-id> [--answers <pdf> ...] [--chapters 1,2] [--part A|AB|B] [--baseline <csv>] [--run-id <id>]
allowed-tools: Bash, Read, Write, Glob, Agent, AskUserQuestion, TaskCreate, TaskUpdate
---

You are the **orchestrator** of the methode-straat. You own control flow and files; you never judge links yourself. Follow `specs/13-methode-pipeline.md` and `specs/14-mapping-verification.md`. Arguments: `$ARGUMENTS`. Python command: `python3` if it exists, else `python` (Windows) — use that spelling everywhere and tell every subagent which one.

## 0. Set up
- Parse: book pdf, `--subject`, `--method`, `--from` (a run id under `runs/` with `04_groups_student.json`), optional `--answers` (repeatable), `--chapters` (default: all), `--baseline` (csv), `--part` (`A` default, `AB` = A then B, `B` = part B on an existing finished part-A run given as `--run-id`; skip to M7), `--run-id` (default `YYYYMMDD-HHMM-koppel-<method>`).
- `python3 scripts/decisions.py init <subject>` (idempotent). Ensure `subjects/<subject>/methodes/<method>/profile.md` exists; if not, create it from `docs/templates/methode-profile.md` and tell the user in one line to fill it (book order matters) — continue.
- Create `runs/<run_id>/{input,text}`; copy the PDFs into `input/`; copy `runs/<from>/04_groups_student.json` to `runs/<run_id>/10_criteria.json`. Write `run.json`: `{run_id, subject, method_id, from_run, chapters, part: "A", max_repair_rounds: 1, judge_batch: 4, status: "running", started_at}`.
- Check `pdftotext` and `tesseract` (`tesseract --list-langs`); if tesseract is missing, say so in one line — the ingest agent will transcribe scanned pages itself, which is slower.
- Task list with steps M1–M6 (+ baseline).

`R` = `runs/<run_id>`, `S` = subject, `M` = method id. Pass paths, never contents. After each step run its validator; on failure re-launch the same agent once with the output; on a second failure set `status: "aborted"` and stop.

## M1 Ingest
Agent `method-ingest` with R, S, M, chapters → `R/11_method_units.json`, `R/text/*`, `R/11_ingest_notes.md`. Validate: `python3 scripts/mapping/validate_method.py R`.
Write the scope: paragraphs of the chapters in scope → `scope_paragraphs` in `run.json` (list of unit ids).

## M1b Intake — the only pause
Agent `intake` with R, S, mapping mode: it reads `11_method_units.json`, `11_ingest_notes.md`, `10_criteria.json`, both profiles, `decisions.json`; asks only questions that change the mapping (book order, out-of-scope chapters, kaders, method terms vs syllabus terms, criteria that seem absent, unreadable pages). Then exactly as in `/generate` step 1b: `decisions.py add S <questions> --run <run_id>`, present open decisions with AskUserQuestion (≤ 4 per call, high impact first), record answers (`--by user`), `decisions.py snapshot S R`. Apply scope answers to `run.json`: paragraphs taken out of scope → drop from `scope_paragraphs`; criteria expected in this method part → `scope_criteria` (criterion unit ids, specs/13 §1).

## M2 Candidates
`python3 scripts/mapping/candidates.py R` → `R/12_candidates.json`.

## M3 Judges (two, independent, per paragraph)
For every paragraph in scope launch agent `mapping-judge` twice — letter `A` and letter `B` — as **separate Agent calls in the same message** (never one agent doing both), output `R/13_judgements.A/<unit>.json` and `…B/…`. Up to `judge_batch` paragraphs per message (= 2×batch agents). A paragraph whose candidate list is empty in both directions is skipped (it will show as outside-syllabus).

## M4 Gradation
`python3 scripts/mapping/gradation.py R` → `R/13_judgements.json`, `R/14_mappings.json`, `R/14_findings.json`. Then `python3 scripts/mapping/check_mappings.py R` (must pass).

## M5 Verify + one repair round
1. Agent `mapping-verifier` (fresh) with R, S, M, scope "all" → `R/15_verification.json`; then `python3 scripts/mapping/check_mappings.py R --verification 15_verification.json`.
2. Repair, once: collect (a) disputed links and (b) `missing_links` proposals, grouped by paragraph. For each such paragraph launch `mapping-judge` with letter `R`, the list of criteria to re-judge, the A/B judgements and the verifier's reasons → `R/13_judgements.R/<unit>.json`. For missing links the R judge judges the proposed criterion fresh. Copy `14_mappings.json` → `14_mappings.round1.json`; rerun M4 (`gradation.py R` picks up `13_judgements.R`), then `check_mappings.py R --verification 15_verification.json` again. Links still disputed stay flagged (they go to the sample list).

## M6 Export
`python3 scripts/mapping/export_mappings.py R` → `R/output/`. If `--baseline`: `python3 scripts/mapping/compare_baseline.py R <csv>` → `R/output/vergelijking_nulmeting.md`. Set `status: "done"` (part A) or continue with M7 (`--part AB`).

## Part B — exercises (M7–M9, specs/13 §4)
Set `part: "AB"` in `run.json`. Scope = every paragraph of the chapters in scope, including those taken out of part A (`ex_scope_paragraphs` in `run.json` only if a decision limits it).
- **M7** `python3 scripts/mapping/ex_candidates.py R` → `R/17_ex_candidates.json`.
- **M8** For every paragraph with sub-questions launch agent `exercise-judge` twice — `A` and `B`, separate Agent calls in the same message — output `R/18_ex_judgements.<letter>/<paragraph>.json`. Up to `judge_batch` paragraphs per message. Tell them the python command and that decisions_snapshot applies.
- **M8b** `python3 scripts/mapping/ex_merge.py R` → `R/18_ex_mappings.json`; then `python3 scripts/mapping/check_ex_mappings.py R` (must pass).
- **M9** Agent `mapping-verifier` (fresh) in **exercise mode** with R, S, M → `R/19_ex_verification.json`; then `check_ex_mappings.py R --verification 19_ex_verification.json`.
  Repair, once: collect disputed links and `missing_links`, grouped by paragraph; per paragraph one `exercise-judge` with letter `R`, the pairs, and pointers to the A/B files and the verdicts → `R/18_ex_judgements.R/<paragraph>.json`. Copy `18_ex_mappings.json` → `18_ex_mappings.round1.json`; rerun `ex_merge.py R` and `check_ex_mappings.py R --verification 19_ex_verification.json`. Verifier `proposed_decisions` → `decisions.py add S <file> --run <run_id>` (open, for the next intake).
- **Export** `python3 scripts/mapping/export_exercises.py R`, then `python3 scripts/mapping/export_mappings.py R` again (gap report sees exercise links). Set `status: "done"`.

## 7. Report (≤ 10 lines)
Criteria in scope, paragraphs, links by gradation, confidence split, voided quotes, gaps, outside-syllabus, disputes left, baseline precision/recall if given, paths. Part B: exercise links, Bloom split, sub-questions outside the syllabus, criteria not practised, Bloom not reached, disputes left.

## Rules
- Paths not contents in prompts. Never write a quote or link yourself. Never answer a decision yourself. Keep every intermediate file (`.round<N>` copies). `text/` is git-ignored and never exported.
