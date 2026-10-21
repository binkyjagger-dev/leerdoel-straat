# leerdoel-straat

Claude Code pipeline that turns a curriculum source (v1: CvTE syllabus PDF, economie VWO) into
learning goal groups — leerdoel + 2–4 succescriteria with a revised-Bloom level per criterion — in
student language, linked to eindtermen, with coverage verified both ways. Output: CSV + coverage
report + doubt list.

## Ground rules
- **Spec first.** `specs/` is the source of truth. Change the spec before changing behaviour.
- **Files are the contract.** Each step reads one JSON and writes one; see `specs/03-pipeline.md`.
- **Rules live in data, not prompts.** Bloom verbs: `data/bloom_verbs_nl.json` (generic) overridden per verb by
  `subjects/<vak>/bloom_verbs.json` when the syllabus defines its own table (specs/06 §7); agents read the merged
  `runs/<run_id>/bloom_verbs_effective.json`, validators recompute it from `--subject`. Student language:
  `data/student_language_rules.json`. Agents and validators read the same files.
- **Deterministic where possible.** Scripts in `scripts/` validate; agents never skip them.
- **Verifier is independent.** Always a fresh Agent call; it critiques, never rewrites.
- **One human checkpoint.** The intake step (1b) asks subject-specific questions and records answers in `subjects/<vak>/decisions.json` via `scripts/decisions.py`; `scripts/verb_table.py install` writes `subjects/<vak>/bloom_verbs.json` only against an answered decision; nothing else writes there, and nothing writes `profile.md`.
- **Bounded loops.** Max 2 repair rounds; leftovers go to the doubt list, nothing is dropped.
- Domain language in code, specs and prompts: English. Output artefacts (goals, criteria, reports): Dutch.

## Layout
```
specs/            00-overview … 05-export
schemas/          JSON schemas per artefact
data/             rule files (Bloom verbs, student-language rules)
scripts/          validate.py bloom_check.py student_language_check.py coverage.py merge_groups.py apply_verdicts.py export.py decisions.py verb_table.py
subjects/<vak>/   profile.md (human) + decisions.json (straat, via decisions.py) + bloom_verbs.json (optional, via verb_table.py) — see specs/06
docs/             HANDLEIDING.md (one-page tutorial, Dutch)
.claude/agents/   ingest intake planner generator student-language verifier
.claude/commands/ generate   (the orchestrator)
runs/<run_id>/    one folder per run (git-ignored except .gitkeep)
tests/fixtures/   small synthetic run used to exercise the scripts
```

## Running
```
pip install --break-system-packages jsonschema   # once
/generate input/syllabus-economie-vwo.pdf --subject economie
python3 scripts/export.py runs/<run_id>          # re-export only
python3 tests/run_fixture.py                         # exercise all scripts on the fixture
```

## Conventions
- `unit_id` is the join key everywhere; `group_id = <unit_id>-<nn>`; `criterion_id = <group_id>-<a..d>`.
- Bloom levels (ordinal): onthouden < begrijpen < toepassen < analyseren < evalueren < creëren.
- `goal.bloom` is computed (`bloom_check.py --write`), never hand-set.
- Never paste file contents into subagent prompts; pass paths.

## Lessons from run 1 (economie VWO 2026, 2026-10-11)
- Verification of 163 groups is split over 3 verifier agents by domain (fresh contexts), then merged into one `05_verification.roundN.json`; round 2 re-judges only the repaired groups.
- Most round-1 issues were J6 (student text dropped/softened a performance) and J2 (sorting/predicting criteria labelled toepassen). Repair = generator sharpens expert text where ambiguous, then student-language redoes only the changed groups (`redo_student.roundN.json`).
- `student_language_check.py` counts formula symbols as words; formula criteria trip L3 at 20 words. Advisory only.
- Planner ceiling comes from the subdomein lead-in ("herkennen en toepassen" → toepassen), not the domein verb "analyseren"; the +1 allowance is an allowance, not a target.

## Lessons from run 2 (2026-10-12)
- Decisions drive the Bloom profile: economie-001/007 moved goals from 29 begrijpen → 7, analyseren 6 → 30, with the same verdict rate as run 1 (round 1 ≈ 75 % pass; round 2 ≈ 99 %). Verifiers must be told how to grade decision deviations in the *student* text (economie-012): J7, not J1 — the D verifier used J1 and had to be harmonised at merge.
- The reliable J2 fix for "classification labelled toepassen" is a data-based application inside the unit's own focus; check it does not take over a calculation another unit owns (economie-008).
- The verifier's `proposed_decisions` route works: 2 new questions (aanbodlijn-ondergrens, voluit-is-curve) are open for the next intake.
- economie-012 (spell out abbreviations) lengthens student sentences; L3 warnings rose from 38 to 160. Advisory, but consider raising the limit or exempting the bracketed abbreviation from the word count.

## Lessons from run 3 (bedrijfseconomie VWO 2028 v2, 2026-10-13; reviewed 2026-10-21)
- The run was done without the intake pause: all 10 questions stayed `open` and the proposals were used. The teacher answered all 16 (10 intake + 6 verifier) on 2026-10-21; the run must be regenerated.
- The verb → Bloom table is **subject-bound**: the CvTE bedrijfseconomie syllabus has its own (bijlage 3: "opstellen" = toepassen, "indelen"/"vergelijken" = analyseren, "onderbouwen" = begrijpen, "voorspellen" = toepassen). Economie's syllabus has none. Hence `subjects/<vak>/bloom_verbs.json` + `verb_table.py` (scan → intake question → install → effective). Against bijlage 3, 37 criteria of run 3 fail G3.
- Ingest skipped the bijlagen, so the intake proposed "met gegeven formule" (009) while bijlage 4 says standard formulas are *not* given; the verifier caught it (10 J4 issues, new decision 016). Appendices that define rules (verbs, formulas) are source material even when they are not units.
- J6 (student text drops a condition or element) is again the largest repair category (10 of 27 round-1 issues), as in runs 1 and 2.
