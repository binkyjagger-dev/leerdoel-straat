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
specs/            00–06 leerdoel-straat (/generate) · 10–15 methode-straat (/koppel)
schemas/          JSON schemas per artefact
data/             rule files (Bloom verbs, student-language rules)
scripts/          validate.py bloom_check.py student_language_check.py coverage.py merge_groups.py apply_verdicts.py export.py decisions.py verb_table.py
subjects/<vak>/   profile.md (human) + decisions.json (straat, via decisions.py) + bloom_verbs.json (optional, via verb_table.py) — see specs/06
docs/             HANDLEIDING.md (one-page tutorial, Dutch)
.claude/agents/   ingest intake planner generator student-language verifier
.claude/commands/ generate (/generate orchestrator) · koppel (/koppel orchestrator)
.claude/agents/   method-ingest mapping-judge mapping-verifier exercise-judge   (methode-straat; intake is shared, mapping mode)
scripts/mapping/  ocr_pdf ocr_images docx_text validate_method candidates gradation check_mappings export_mappings compare_baseline · part B: ex_candidates ex_merge check_ex_mappings export_exercises
subjects/<vak>/methodes/<methode-id>/profile.md   (human) — book order, structure, terms
runs/<run_id>/    one folder per run (git-ignored except .gitkeep)
tests/fixtures/   small synthetic run used to exercise the scripts
```

## Running
```
pip install --break-system-packages jsonschema   # once
/generate input/syllabus-economie-vwo.pdf --subject economie
python3 scripts/export.py runs/<run_id>          # re-export only
python3 tests/run_fixture.py                         # exercise all /generate scripts on the fixture
python3 tests/run_koppel_fixture.py                  # exercise all /koppel scripts on the koppel fixture
/koppel input/<m>/boek.pdf --subject economie --method <id> --from <generate-run> --chapters 1,2 --baseline nulmeting.csv
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

## Lessons from run 4 (bedrijfseconomie run 2, 2026-10-21) — generic
- Round-1 pass rate rose from ~75 % (runs 1–3) to 89 % (106/119). What changed: all decisions answered before planning, the subject verb table, and previous-run watch-points injected into generator/verifier prompts. Make the watch-point injection systematic (a straat-written `subjects/<vak>/watchpoints.md` from verifier findings) instead of ad hoc in the orchestrator's prompts.
- J6 (student text drops a condition, narrows scope, closes an open list) is structural: 4 of 22 round-1 issues and 2 of the 3 round-2 failures, the latter on groups that had just been repaired with explicit instructions. Recurring shapes: "zoals"/"bijvoorbeeld" → colon (closed list), "respectievelijk" → "of", a dropped middle element of a chain, a verb that lands on a higher Bloom level ("afzetten tegen" → "vergelijken"). Candidate fix: a deterministic L5 that checks list openers and connectors survive, plus a cheap J6 pre-check (sonnet) between student-language and verification.
- Repairs can introduce new errors in criteria the repair did not touch (F2.31.1-02: adding the begroot bezettingsresultaat in -b made -c's composition of the budgetresultaat wrong). The repair generator must re-read the whole group for internal consistency; consider one extra targeted round for repair-induced failures (spec decision).
- Appendices are rule sources: bijlage 3 (verbs) is now data; bijlage 4 (formulas) is not, and both J8 rejects in G.32.2 were wrong denominators. Generic mechanism wanted: ingest extracts a formula appendix to `01_formulas.json`, generators copy literally, verifier checks against it.
- Concept blocks in CvTE syllabi follow the *global eindterm number*, not the specification: 335 of 446 bullets landed on the subdomein (P5 fallback) and the planner distributed them. C3 reached 100 %, but J9 cannot judge leaf-level fit for those. Allow a concept block to carry a `scope` (the leaves of one eindterm number) instead of falling back to the whole subdomein.
- A subdomein split over two generators drifts in terminology (couponrente vs interestpercentage van de obligatie). Fill `subjects/<vak>/glossary.json` (already optional in specs/06) from the concept lists and decisions and have generators read it.
- G8 (0 fails) and C3 (100 % before verdicts) worked without friction; J9 produced 2 issues. Keeping concept assignment in the generator did not cost quality.
- `validate.py verification` on a partial file reports "has no verdict" for every out-of-scope group; add a `--partial` flag.
- L3 fired 352 times; formula criteria and enumerations cannot stay under 20 words. Count a formula as one word or make the limit a subject setting.
- An intake proposal can require a straat change to be executable (019 → `source.concept_corrections`). Intake should flag that so the orchestrator pauses for the build before planning.

## Methode-straat ground rules (specs/10–15, decided 2026-10-22)
- Links are criterion × paragraph; judges output treatment (explains/practises/mentions) + verbatim quote (≤ 25 words); the gradation is computed from book order (first explains = leert). Never let an agent set gradations.
- Two judges (A, B) per paragraph in separate Agent calls; confidence from agreement + quote validity; verifier in fresh context does precision (sample), recall (per paragraph) and gradation checks; one repair round (judge R).
- Method text lives only in `runs/<id>/text/` (git-ignored); PDFs under `input/` are not committed.
- Criterion ids from /generate are the key everywhere; `10_criteria.json` is a copy of the source run's `04_groups_student.json`.

## Lessons from koppel run 1 (LWEO Vraag en aanbod H1–H2, 2026-10-22/23)
- The source run's `04_groups_student.json` was gone (only `output/*.csv` is kept); `10_criteria.json` was rebuilt from the export CSV (script in the run folder). Keep the generate run's JSON, or make the CSV rebuild a straat script.
- A lesbrief covers a fraction of the syllabus: `scope_criteria` (decision economie-024) is needed, otherwise ~140 groups land in the gap report and every paragraph gets 250–500 candidates.
- The repair judge must *decide* the pairs it re-judges (both parts). "Replace the weaker judge" let the explains/practises default overrule R in 3 of 5 part-A repairs; found only when part B's findings looked wrong.
- Part B: judges substitute a verb for juist/onjuist and fill-in items (MB2 warns); the "antwoord is een berekening" raise must not fire when the verb gives a level, the number is given in the question, or R set the level.
- Candidates for exercises only offer criteria taught in the own or earlier paragraphs; judges repeatedly found criteria taught *later* (oefent vóór uitleg). Consider adding later-taught criteria at low priority.
- New agent types are not loadable in the session that creates them; run them as general-purpose agents that read the definition file.
