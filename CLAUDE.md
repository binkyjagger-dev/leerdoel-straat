# leerdoel-straat

Claude Code pipeline that turns a curriculum source (v1: CvTE syllabus PDF, economie VWO) into
learning goal groups — leerdoel + 2–4 succescriteria with a revised-Bloom level per criterion — in
student language, linked to eindtermen, with coverage verified both ways. Output: CSV + coverage
report + doubt list.

## Ground rules
- **Spec first.** `specs/` is the source of truth. Change the spec before changing behaviour.
- **Files are the contract.** Each step reads one JSON and writes one; see `specs/03-pipeline.md`.
- **Rules live in data, not prompts.** Bloom verbs: `data/bloom_verbs_nl.json`. Student language:
  `data/student_language_rules.json`. Agents and validators read the same files.
- **Deterministic where possible.** Scripts in `scripts/` validate; agents never skip them.
- **Verifier is independent.** Always a fresh Agent call; it critiques, never rewrites.
- **Bounded loops.** Max 2 repair rounds; leftovers go to the doubt list, nothing is dropped.
- Domain language in code, specs and prompts: English. Output artefacts (goals, criteria, reports): Dutch.

## Layout
```
specs/            00-overview … 05-export
schemas/          JSON schemas per artefact
data/             rule files (Bloom verbs, student-language rules)
scripts/          validate.py bloom_check.py student_language_check.py coverage.py merge_groups.py apply_verdicts.py export.py
.claude/agents/   ingest planner generator student-language verifier
.claude/commands/ generate   (the orchestrator)
runs/<run_id>/    one folder per run (git-ignored except .gitkeep)
tests/fixtures/   small synthetic run used to exercise the scripts
```

## Running
```
pip install --break-system-packages jsonschema   # once
/generate input/syllabus-economie-vwo.pdf
python3 scripts/export.py runs/<run_id>          # re-export only
bash tests/run_fixture.sh                         # exercise all scripts on the fixture
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
