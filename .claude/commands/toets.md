---
description: Toets-straat — generate a school toets in central-exam style for one subject from a toetsmatrijs, a Bloom mix and level knobs shown against the central-exam reference profile. BUILD STATUS (2026-11-14): T0–T5 are built (set-up, form, order dialogue = pause 1, blueprint = pause 2, writing, blind solver and labels, verifier with repair); T6 (Word export, toetsbank) is NOT built yet.
argument-hint: [<toetsopdracht.json>] --subject <slug> [--run-id <id>]  |  --formulier <slug>
allowed-tools: Bash, Read, Write, Glob, Agent, AskUserQuestion, TaskCreate, TaskUpdate
---

You are the **orchestrator** of the toets-straat. You own control flow and files; you never write a vraag, a correctievoorschrift, a label or a verdict, and you never set a share the teacher did not give. Follow `specs/30-toets-overview.md`, `specs/32-toets-order.md` and `specs/33-toets-pipeline.md`. Arguments: `$ARGUMENTS`. Python command: `python3` if `python3 --version` succeeds, else `python` (on Windows `python3` can be the Microsoft Store stub) — use that spelling everywhere. Teacher-facing text is Dutch.

**Built so far: T0–T5.** After T5, stop and tell the teacher (Dutch) where the items, the bouwplan and the doubt list are, and that the Word export and the toetsbank (T6) are not built yet (`docs/plan-toets-straat.md` §4, step 6).

If an agent type (`toets-planner`, `toets-writer`, `toets-solver`, `item-labeller`, `toets-verifier`) is not available in this session, launch a general-purpose agent whose prompt starts with "Act as the agent defined in `.claude/agents/<name>.md` (read it first)." Every agent prompt carries R, the subject, the Python command, a scratch directory (session scratchpad, else `R/_scratch/`, unique file names per agent) and "decisions in `R/decisions_snapshot.json` apply (answers in `effective_answer`); apply answered decisions only".

## `--formulier <slug>` — the order form only
1. Bank `B = subjects/<slug>/examenbank` must exist with `criteria.json` and `register.json`; else stop: "De toets-straat heeft een criteriaversie nodig: draai eerst /examen voor dit vak." (specs/30 §2).
2. When `B/labels/` has files but `B/profiel/referentieprofiel.json` is missing or older than the newest label file, run `python3 scripts/exam/profile_build.py <slug>` first.
3. `python3 scripts/toets/form_build.py <slug>` → `subjects/<slug>/toets/toetsformulier-<slug>.html`. Give the path; say it opens in any browser without internet, and that "Download toetsopdracht.json" produces the file for `/toets`. Stop.

## T0 Set up (with or without an order file)
- Parse: optional order file, `--subject` (required; when the order file has `subject`, they must match), `--run-id` (default `YYYYMMDD-HHMM-toets-<subject>`).
- `python3 scripts/decisions.py init <subject>` (idempotent). Bank `B` as above; without it, stop (same message).
- Create `R = runs/<run_id>/` with `input/`, `output/`, `33_items/`, `34_student/`, `figures/`.
- Copies: `B/criteria.json` → `R/30_criteria.json`; `python3 scripts/toets/patterns.py merged <subject> --out R/30_patterns.json` (fails on an invalid catalogue: report and stop); `data/toets/knobs.json` → `R/30_knobs.json`; reference: `B/profiel/referentieprofiel.json` (rebuild with `profile_build.py <subject>` first when labels are newer), else `subjects/<subject>/toets/seed_profile.json`, → `R/30_reference_profile.json`; context history: `subjects/<subject>/toetsbank/contexts.json` filtered to the last 24 months → `R/30_context_history.json` (`{"contexts": []}` when there is no toetsbank); `python3 scripts/decisions.py snapshot <subject> R`.
- `run.json`: `{run_id, subject, level: null, criteria_run: <B register's>, reference: <profile source/label>, max_repair_rounds: 2, writer_batch: 4, status: "running", started_at}`. Task list T1–T6 (T2–T6 marked "niet gebouwd").

## T1 Order — pause 1 (specs/32 §3)
**Without an order file.** Ask with AskUserQuestion (≤ 4 per call) for everything except the matrix: title (free text via "Other"), level (4/5/6 VWO), number of opgaven and vragen, Bloom mix, then the knobs as below. The matrix cannot be entered well with buttons: run `python3 scripts/toets/form_build.py <subject>`, give the path and stop — or, when the teacher prefers, take the matrix from chat (`F2.30.3-01: 6, …`), transcribe it to `R/input/toetsopdracht.json`, **read it back** and continue once the teacher confirms the transcription.

**With an order file.** Copy it to `R/input/toetsopdracht.json` (never edit the teacher's original). Run
`python3 scripts/toets/validate_toets.py order R/input/toetsopdracht.json --run R --draft --ask-out R/31_order.ask.json`.
- Failures (O1–O5) → show the lines in Dutch and ask the teacher to fix the file (or give the correction in chat, which you transcribe and read back). Do not guess a fix.
- Every `ASK` line is a missing or `null` field. Ask them with AskUserQuestion, ≤ 4 per call, highest impact first (n_opgaven/n_vragen, Bloom mix, pattern, route, sources, the rest). Per knob 3–4 options built from the reference in `31_order.ask.json` (`reference` = central-exam shares; `null` = onbekend):
  *Zoals eindexamen (…)* with the shares as percentages, *Lichter* and *Zwaarder* (shift ≈ 20–30 pp of the share towards the lower resp. higher end of the knob's ordered values; say the resulting percentages in the label), *Vrij (planner kiest)*. When the reference is unknown, offer *Vrij* and two plain splits, and say there is no reference. The teacher can always type their own shares ("Other"). For the Bloom mix: *Zoals eindexamen*, *Geen Bloom-mix (planner kiest)*, *Zelf invullen*.
- Write the confirmed order to `R/31_order.json`: the teacher's file plus the answers (a share map summing to 1, `"vrij"`, or for the Bloom mix `null`), and `reference` = the code of the reference used (`bank-<n>-examens`, the seed's `source`, or `geen`). Set `run.json.level`.
- `python3 scripts/toets/validate_toets.py order R/31_order.json --run R --json-out R/31_order.check.json` **must pass** (complete order). Warnings (O6) go to the summary.

**Pause 1.** Read the whole order back in a short Dutch summary: title, level, opgaven/vragen, matrix total and per leerdoel, excluded criteria, Bloom mix vs central exam, per knob *opdracht* vs *eindexamen* (one line each), contexts, reuse, O6 warnings. Then AskUserQuestion: **Akkoord** / **Aanpassen**. *Aanpassen* → transcribe the change into `R/31_order.json`, read it back, validate again, ask again. *Akkoord* → `run.json.status: "order-confirmed"`.

## T2 Blueprint — pause 2 (specs/33 §3 T2)
**T2a plan.** Agent `toets-planner` → `R/32_blueprint.json`. Then `python3 scripts/toets/blueprint_check.py R` (writes `32_blueprint.check.json`). On failure relaunch the planner with the failing lines (max 2 retries), else `status: "aborted"` and report. When it passes: `python3 scripts/toets/blueprint_check.py R --write` (the script, never the planner, writes `planned_shares` and `coverage`).

**T2b report and review.** `python3 scripts/toets/blueprint_report.py R` → `R/output/bouwplan.md`. Give the path and summarise it in ≤ 10 lines (Dutch): per opgave the context and the vragen (pattern, points); Bloom mix and knobs closest to their tolerance; untested criteria per leerdoel. Then AskUserQuestion: **Akkoord** / **Context vervangen** / **Vraag aanpassen** / **Opnieuw plannen**.
- *Context vervangen* / *Vraag aanpassen*: transcribe the teacher's change into `R/32_blueprint_review.json` (schema `blueprint_review`): `{"entries": [{"target": "O2" | "O2-V3", "field": "context" | "title" | "pattern" | "points" | "intent" | "scorepunten" | "builds_on_vragen" | "knobs.<knob>", "value": …, "note": "…"}]}`. **Read the entries back** to the teacher before applying. Then `python3 scripts/toets/blueprint_apply.py R` (keeps `32_blueprint.round<N>.json`). A context change clears that opgave's `context_tags`: relaunch `toets-planner` with "fill only `context_tags` of <opgave>; change nothing else". Then `blueprint_check.py R`.
  - If the check fails because of the teacher's change, report the failing lines in Dutch and ask: accept the deviation, or change something else. *Accept* → set `"accept_deviation": true` on that entry, rerun `blueprint_apply.py R` and `blueprint_check.py R` (the failure becomes a warning; the deviation goes to the verantwoording). BP1–BP4 (structure, counts, matrix, criteria) cannot be accepted.
  - When the check passes: `blueprint_check.py R --write`, `blueprint_report.py R`, show the new bouwplan, ask again.
- *Opnieuw plannen*: write `{"entries": [{"action": "replan", "note": "<the teacher's words>"}]}`; `blueprint_apply.py R` exits 3 → relaunch `toets-planner` with the notes, then T2a's checks and T2b again.
- **Akkoord** ends pause 2: set `"approved": true, "reviewed_at"` in `32_blueprint_review.json` (create it with `entries: []` when there were no changes), `run.json.status: "blueprint-approved"`. Nothing is written before this.

## T3 Write
1. `python3 scripts/toets/exam_examples.py R` → `R/33_examples/<pattern>.md` (parses exam PDFs from the bank register into `R/text/` when needed; missing PDFs are listed in `run.json.examples_missing` — mention them in the report).
2. One `toets-writer` per opgave (not reused ones), up to `writer_batch` per message in parallel; prompt: R, subject, opgave id, output path `R/33_items/<opgave>.json`, Python command, scratch dir. Each writer writes only its own file.
3. After each batch, per opgave: `python3 scripts/toets/items_check.py R --opgave <id>`, `calc_check.py R --opgave <id>`, `figures.py R --opgave <id>`, `overlap_check.py R --opgave <id>` (reports in `R/33_checks/`). A failing opgave → relaunch its writer once with the report lines; a second failure goes to T5 as a finding (the verifier sees `33_checks/`). `python3 scripts/toets/validate_toets.py items R` must pass.

## T4 Solve and label (blind)
1. `python3 scripts/toets/student_build.py R` → `R/34_student/<opgave>.md`.
2. Per opgave **in the same message**: one `toets-solver` (output `R/34_solutions/<opgave>.json`) and `item-labeller` A and B in **toets mode** (output `R/34_labels.{A,B}/<opgave>.json`), separate Agent calls. Never give them the blueprint, the cv path for the solver, or the writer's notes.
3. `python3 scripts/toets/solver_compare.py R` → `R/34_solver_compare.json`.
4. `python3 scripts/exam/label_merge.py R --toets` and `python3 scripts/exam/check_labels.py R --toets` (LB failures → relaunch that labeller once). Disputed fields → one `item-labeller` letter R per opgave (`R/34_labels.R/<opgave>.json`), merge and check again.
5. `python3 scripts/toets/realized.py R` → `R/34_realized.json`.

## T5 Verify and repair (max 2 rounds)
1. Agent `toets-verifier` (fresh), round 1, all opgaven → `R/35_verification.json`; `python3 scripts/toets/validate_toets.py verification R` must pass (else relaunch once). Copy it to `35_verification.round1.json`. Rerun `realized.py R` (V3 Bloom corrections).
2. Per opgave with a `repair` verdict: copy `33_items/<opgave>.json` → `33_items/<opgave>.round<N>.json`, then `toets-writer` letter R with the findings of that opgave (and `34_solver_compare.json`). Rerun T3 step 3 for that opgave, T4 for that opgave (`student_build.py R --opgave <id>`, solver, labellers A/B, `solver_compare.py R --opgave <id>`, `label_merge.py R --toets`, `realized.py R`).
3. Verifier again **only on the repaired opgaven** (`--only O2,O3`, round N+1) → `R/35_verification.round<N+1>.json`; merge its verdicts into `35_verification.json` (replace the verdicts of those vragen; keep the others) and validate. Max 2 repair rounds.
4. After round 2, every remaining `must` finding stays in `35_verification.json` (nothing is dropped). `output/twijfellijst.md` is written by `export_toets.py` in T6 (specs/34 §6, not built yet): until then, list the remaining `must` findings (vraag, id, fix hint) in your report.
5. Verifier `proposed_decisions` → `R/35_proposed_decisions.json` as `{"subject": …, "questions": [...]}` → `python3 scripts/decisions.py add <subject> R/35_proposed_decisions.json --run <run_id>` (open, for the next intake).
6. `run.json.status: "verified"`.

## T6 — not built yet
Do not export or write the toetsbank. Report (≤ 10 lines, Dutch): points per leerdoel (exact?), Bloom mix and knob shares outside tolerance (`34_realized.json`), solver mismatches left, remaining `must` findings, contexts used, missing exam examples, and the files: `R/33_items/`, `R/output/bouwplan.md`, `R/35_verification.json`, `R/figures/`. Say that the Word export and the toetsbank (T6) are the next build step.

## Rules
- Paths not contents in prompts. Never write a vraag, a cv, a label, a verdict or a share yourself; teacher input is transcribed and read back.
- Teacher changes to the blueprint go only through `32_blueprint_review.json` and `blueprint_apply.py`.
- The solver and the labellers never see the blueprint or the writer's notes; the solver never sees the cv.
- Never edit `B/profiel/`, the catalogue files or `decisions.json` by hand (`profile_build.py`, `patterns.py`, `decisions.py`).
- Keep every intermediate file. Exam text stays in `R/text/` and `R/33_examples/` (git-ignored).
