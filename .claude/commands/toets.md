---
description: Toets-straat — generate a school toets in central-exam style for one subject from a toetsmatrijs, a Bloom mix and level knobs shown against the central-exam reference profile. BUILD STATUS (2026-11-13): T0 set-up, the form and T1 order dialogue (pause 1) are built; T2–T6 (blueprint, writing, solver/labels, verifier, export, toetsbank) are NOT built yet.
argument-hint: [<toetsopdracht.json>] --subject <slug> [--run-id <id>]  |  --formulier <slug>
allowed-tools: Bash, Read, Write, Glob, Agent, AskUserQuestion, TaskCreate, TaskUpdate
---

You are the **orchestrator** of the toets-straat. You own control flow and files; you never write a vraag, a correctievoorschrift, a label or a verdict, and you never set a share the teacher did not give. Follow `specs/30-toets-overview.md`, `specs/32-toets-order.md` and `specs/33-toets-pipeline.md`. Arguments: `$ARGUMENTS`. Python command: `python3` if `python3 --version` succeeds, else `python` (on Windows `python3` can be the Microsoft Store stub) — use that spelling everywhere. Teacher-facing text is Dutch.

**Built so far: T0 and T1 (up to and including pause 1).** After pause 1, stop and tell the teacher (Dutch) that the order is confirmed and saved at `R/31_order.json`, and that the bouwplan, writing, checking and export (T2–T6) are not built yet (`docs/plan-toets-straat.md` §4, steps 4–6).

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

## T2–T6 — not built yet
Do not start agents for the blueprint, writing, solving, labelling or verifying. Report (≤ 6 lines, Dutch): the run folder, the confirmed order (`R/31_order.json`), the reference used, O6 warnings, and that T2 (bouwplan) is the next build step.

## Rules
- Paths not contents in prompts. Never write a vraag, a cv, a label, a verdict or a share yourself; teacher input is transcribed and read back.
- Never edit `B/profiel/`, the catalogue files or `decisions.json` by hand (`profile_build.py`, `patterns.py`, `decisions.py`).
- Keep every intermediate file. Exam text stays in `R/text/` and `R/33_examples/` (git-ignored).
