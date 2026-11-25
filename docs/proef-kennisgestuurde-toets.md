# Proef: knowledge-driven toets (bedrijfseconomie 5 VWO, periode 2)

**What this is.** An experiment, not a spec and not a build. Question: do toets vragen get clearly better when the
planner and writer work from (a) teacher-approved **misconceptions** per leerdoel and (b) **question mechanisms**
taken from real central-exam questions, and the teacher picks between two variants? Decided with Martijn on
2026-11-25. If the proef succeeds, the architect session writes specs/38; until then specs/37 is on hold.

**You are the orchestrator.** Teacher-facing text is Dutch. Follow CLAUDE.md. On every ambiguity, ask the teacher
(AskUserQuestion) and do not decide yourself.

## Rules
- Work on branches; never commit to main, never force-push; the teacher merges.
- Change **no scripts, schemas or specs**. The proef steers only through agent prompts and extra input files.
  If something cannot be done without a code change, stop and report.
- Exam text and old-toets text stay out of git (`input/`, `R/text/`, `R/kennis/bron/` are local only).
  Never edit or move the teacher's originals; copy them.
- Old toetsen and exams are examples of **form and mechanism only**: no context, numbers or sentences are reused.
- Apply answered decisions only (`decisions_snapshot.json`, `effective_answer`).

## Step 0 — Secure the open work
1. `git status`. The work of 18–19 November is uncommitted (specs/37 draft, run 20261119-0943, toetsbank,
   decisions, revised matrix). Commit it on a branch `werk-2026-11-19` (respect `.gitignore`), push, open a PR,
   do not merge.
2. Create branch `proef-kennis` from that branch.

## Step 1 — Ask the teacher (one AskUserQuestion round)
1. Where are the 6 exams (opgaven, correctievoorschrift, bijlage, uitwerkbijlage) and the 5 old toetsen with
   answer models? (folder paths)
2. Are there scores per vraag for the old toetsen? If yes, where?
3. Matrix: `subjects/bedrijfseconomie/toets/toetsmatrijs-p2-26-27-herzien.json` (36 p, 6 leerdoelen) or another?
4. Success bar for the blind comparison: proposal **at least 10 of 16 new vragen "goed"** (run 5 first review: 4 of 16).

## Step 2 — Material
1. Copy the exams to `input/examens-bedrijfseconomie-vwo/<jaar TVn>/` with the CvTE names
   (`-o`, `-c`, `-b`, `-u`). Two exams (2025-I, 2026-I) are already there.
2. Copy the old toetsen to `input/toetsen-bedrijfseconomie-5vwo-p2/`.
3. Run folder `R = runs/<YYYYMMDD-HHMM>-proef-kennis-bedrijfseconomie/` with `kennis/` and `kennis/bron/`.
4. Parse every exam with `scripts/exam/exam_text.py` into `R/text/` (light route: **no** `/examen` run, no bank
   links for the four new exams; that comes later if the proef succeeds).
5. Extract the old toetsen (docx/pdf) to plain text in `R/kennis/bron/`.
6. Cito item analyses (TIA): look up the published "toets- en itemanalyse" per exam on cito.nl
   (examenverslag → resultaten per examen) and record per vraag the p-value and Rit in `R/kennis/tia.json`.
   If a file cannot be fetched, ask the teacher to download it; continue without it and say so.

## Step 3 — Knowledge cards (pause K)
Scope: only the leerdoelen (groups) of the matrix and their criteria (`subjects/bedrijfseconomie/examenbank/criteria.json`).

1. **Mechanism cards** — one general-purpose agent per exam, in parallel, each writing its own file
   `R/kennis/mechanismen.<exam>.json`. For every exam question that tests one of the groups:
   `{exam, vraag, points, group_ids, p_value, mechanism: <short Dutch name>, move: <the thinking step that makes it
   non-obvious, 1–2 sentences>, skeleton: <structure of the question in abstract terms, no exam wording>,
   why_hard: <what a weak student does wrong here>}`.
   Name mechanisms by the thinking move (e.g. terugredeneren vanuit een uitkomst, een half juiste redenering
   beoordelen, twee tegengestelde effecten afwegen, veranderde voorwaarde doorrekenen, zelf de relevante gegevens
   kiezen), not by the asking verb. Merge to `R/kennis/mechanismen.json` and unify the mechanism names.
2. **Old-toets notes** — one agent: per vraag of the 5 old toetsen `{toets, vraag, group_ids, form, mechanism,
   score_p (if known)}` → `R/kennis/oude_toetsen.json`.
3. **Misconception cards** — one agent proposes 2–3 per group from: cv remarks ("niet goed rekenen", "veelgemaakte
   fout"), questions with a low p-value, old-toets vragen, and the teacher's own two (aanschafwaarde incl.
   installatiekosten / restwaarde minus sloopkosten; winstopslag op de kostprijs vs al in de verkoopprijs — see
   the `focus` texts in the revised matrix). Card: `{group_id, misconception, typical_wrong_answer, source,
   catching_question: <what kind of vraag exposes it>, status: "voorstel"}` → `R/kennis/misconcepten.json`.
4. Render `R/output/kennis-kaartjes.md` (Dutch, readable, per leerdoel: misconcepten, then the exam mechanisms
   with p-value, then what the old toetsen did).
5. **Pause K.** Give the file. Ask the teacher per leerdoel: approve, change or reject each misconception, add
   missing ones, and mark old-toets vragen he found good or weak. Transcribe, **read back**, then set
   `status: "goedgekeurd" | "afgewezen"`. Only approved cards are used.

## Step 4 — Make the toets with the straat (`/toets`, same run folder conventions)
Order: the matrix from step 1, template `5vwo-toets`, route and direction 0 % (as run 20261119-0943), level 5vwo.
Run T0–T6 as `.claude/commands/toets.md` says, with these additions in the agent prompts:

- **Planner** (extra input: `R/kennis/misconcepten.json` approved only, `R/kennis/mechanismen.json`): for every
  vraag choose one approved misconception of its leerdoel and one exam mechanism, and write them in `intent` as
  `misconcept: … | mechanisme: … (naar <exam> v<n>)`. No mechanism more than three times in the toets; prefer
  mechanisms with a low p-value for the pittige vragen. A vraag that only asks the criterion literally, without a
  misconception to catch, is not allowed. `bouwplan.md` shows this at pause 2 as usual.
- **Writer**: gets its opgave's cards and the exam questions named in them (from `R/text/`). Writes **two
  variants** of its opgave on the same blueprint and context: `33_items/<opgave>.json` (A) and
  `33_varianten/<opgave>.B.json` (B), B using a different mechanism or angle per vraag. The model answer must
  score the correct reasoning and the cv rules must say that the typical wrong answer of the misconception gets
  no point.
- Run the T3 checks on both variants (copy B into a scratch run copy if a script needs `33_items/`).
- **Pause V (variants).** `R/output/varianten.md`: per vraag variant A and B side by side with the intended
  misconception. The teacher picks A, B or "geen van beide" (+ comment). Transcribe and read back. Writer R then
  assembles the chosen vragen into the final opgave, rereads the whole opgave for consistency and rewrites
  "geen van beide" vragen with the comment. Rerun the T3 checks.
- **Misconception solver** (new, advisory): after T4's blind solver, one extra `toets-solver`-style agent per
  opgave answers as a student who holds the planned misconception of each vraag (student version only, plus the
  card). Compare with the cv: if the misconception answer would earn the scorepunt, or equals the correct answer,
  the vraag does not catch the misconception → finding for the verifier and `twijfellijst.md`
  (`R/34_misconcept_check.json`).
- Put the old-toets texts in `R/text/` as well, so `overlap_check.py` also guards against copying them; if the
  script does not read them there, say so in the report.
- T5 and T6 as usual. Skip `toetsbank_add.py` until the teacher has judged the proef.

## Step 5 — Blind comparison (the measurement)
1. Build `R/output/blind-vergelijking.md`: all vragen of the new toets and all vragen of run
   `20261119-0943-toets-bedrijfseconomie` (final version), grouped per leerdoel, shuffled, numbered 1…n, each with
   its context and cv summary, **without origin**. Keep the key in `R/blind-sleutel.json` (do not show it).
2. The teacher gives per number: goed / aanpassen / weg (+ optional comment). Transcribe and read back.
3. Tally per origin; compare with the success bar. Also list which mechanisms and misconceptions scored "goed".

## Step 6 — Report (Dutch, ≤ 15 lines)
Result against the bar; good/aanpassen/weg per origin; which mechanisms worked; misconception-solver findings;
cost (agent calls); what the proef could not do without a code change; recommendation: go on to specs/38 or stop.
Commit on `proef-kennis` only what `.gitignore` allows (run.json, output/), open a PR, do not merge.
