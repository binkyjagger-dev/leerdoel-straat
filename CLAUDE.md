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
- **One human checkpoint.** The intake step (1b) asks subject-specific questions and records answers in `subjects/<vak>/decisions.json` via `scripts/decisions.py`; `scripts/verb_table.py install` writes `subjects/<vak>/bloom_verbs.json` and `scripts/glossary.py add` writes `subjects/<vak>/glossary.json` (synonyms for candidate retrieval, specs/06 §8), each only against an answered decision; nothing else writes there, and nothing writes `profile.md`.
- **Bounded loops.** Max 2 repair rounds; leftovers go to the doubt list, nothing is dropped.
- Domain language in code, specs and prompts: English. Output artefacts (goals, criteria, reports): Dutch.

## Layout
```
specs/            00–06 leerdoel-straat (/generate) · 10–15 methode-straat (/koppel) · 20–25 examen-straat (/examen; built and first run 2026-10-27; plan: docs/plan-examen-straat.md) · 26 examen labels (E7) · 30–35 toets-straat (/toets; specified 2026-11-13; build steps 1–6 done 2026-11-14: schemas, catalogue, E7 labels + profile, order form, blueprint, writing and checks, export and toetsbank (T0–T6); first real run pending; open build questions: docs/bouwvragen-toets.md; plan: docs/plan-toets-straat.md)
data/toets/       knobs.json patterns_base.json (toets-straat rule files; seed 2026-11)
subjects/<vak>/toets/  patterns.json (subject layer) conventions.md contexten.md (human) seed_profile.json sjablonen/ — see specs/31
subjects/<vak>/examenbank/labels/ + profiel/  (E7) pattern/knob labels per exam question + reference profile — specs/26
subjects/<vak>/toetsbank/  (toets-straat) register.json toetsen/ contexts.json output/ — specs/35
schemas/          JSON schemas per artefact
data/             rule files (Bloom verbs, student-language rules)
scripts/          validate.py bloom_check.py student_language_check.py coverage.py merge_groups.py apply_verdicts.py export.py decisions.py verb_table.py glossary.py
subjects/<vak>/   profile.md (human) + decisions.json (straat, via decisions.py) + bloom_verbs.json (optional, via verb_table.py) + glossary.json (optional, via glossary.py) — see specs/06
docs/             HANDLEIDING.md (one-page tutorial, Dutch)
.claude/agents/   ingest intake planner generator student-language verifier
.claude/commands/ generate (/generate orchestrator) · koppel (/koppel orchestrator) · examen (/examen orchestrator, incl. E7 and --label) · toets (/toets; T0–T6)
.claude/agents/   method-ingest mapping-judge mapping-verifier exercise-judge   (methode-straat; intake is shared, mapping mode)
.claude/agents/   exam-ingest exam-judge   (examen-straat; intake exam mode, mapping-verifier exam mode) · item-labeller (E7 exam mode, /toets T4 toets mode) · toets-planner toets-writer toets-solver toets-verifier (toets-straat)
scripts/mapping/  ocr_pdf ocr_images docx_text validate_method candidates gradation check_mappings export_mappings compare_baseline · part B: ex_candidates ex_merge check_ex_mappings export_exercises · koppel_extend (/koppel --extend, specs/13 §5)
scripts/exam/     exam_text validate_exam exam_candidates exam_merge check_exam_mappings bank_add bank_export exam_sample (ecommon = shared helpers, reuses scripts/mapping) · E7: label_merge check_labels bank_labels_add profile_build (lcommon)
scripts/toets/    patterns (catalogue) form_build validate_toets (order|blueprint|items|verification) · T2: blueprint_check blueprint_report blueprint_apply · T3: exam_examples items_check calc_check figures overlap_check · T4: student_build solver_compare realized · T6: export_toets (docmodel: md + python-docx) toetsbank_add (+ --history) · reuse_copy (tcommon toetsrun shares nlnum = shared helpers)
subjects/<vak>/examenbank/  (examen-straat) register.json + links/<exam>.json + output/ — bound to one criteria run; see specs/25
input/examens-<vak>/<jaar TVn>/  CvTE exam PDFs (-o opgaven, -c correctievoorschrift, -b bijlage); not committed
subjects/<vak>/methodes/<methode-id>/profile.md   (human) — book order, structure, terms
runs/<run_id>/    one folder per run (git-ignored except .gitkeep)
tests/fixtures/   small synthetic run used to exercise the scripts
```

## Running
```
pip install --break-system-packages jsonschema   # once (toets-straat also: pymupdf matplotlib python-docx)
/generate input/syllabus-economie-vwo.pdf --subject economie
python3 scripts/export.py runs/<run_id>          # re-export only
python3 tests/run_fixture.py                         # exercise all /generate scripts on the fixture
python3 tests/run_koppel_fixture.py                  # exercise all /koppel scripts on the koppel fixture
python3 tests/run_examen_fixture.py                  # exercise all /examen scripts (builds small exam PDFs itself)
python3 tests/run_toets_fixture.py                   # exercise toets-straat steps 1–6 (catalogue, E7, order, form, blueprint, items checks, solver, realised, export, toetsbank)
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

## Toets-straat ground rules (specs/26, 30–35, decided 2026-11-13)
- Two pauses: the order (31_order.json) and the blueprint (32_blueprint_review.json via blueprint_apply.py). Nothing is written before the teacher approves the blueprint.
- Knob shares and the Bloom mix are by points; the reference profile is rebuilt from `examenbank/labels/` by `profile_build.py`, never edited by hand.
- Realised knobs are measured by the same `item-labeller` that labels exam questions (two labellers + R), blind to the blueprint.
- Every given number is named in `data`, every computed number in `calc`; `calc_check.py` recomputes, the blind solver re-solves. Figures are rendered from specs, never drawn by an agent.
- Style examples are form only; `overlap_check.py` fails on any shared 8-word shingle with exam text.
- Patterns are added only by `scripts/toets/patterns.py add` against an answered decision.

## Lessons from koppel run 1 (LWEO Vraag en aanbod H1–H2, 2026-10-22/23)
- The source run's `04_groups_student.json` was gone (only `output/*.csv` is kept); `10_criteria.json` was rebuilt from the export CSV (script in the run folder). Keep the generate run's JSON, or make the CSV rebuild a straat script.
- A lesbrief covers a fraction of the syllabus: `scope_criteria` (decision economie-024) is needed, otherwise ~140 groups land in the gap report and every paragraph gets 250–500 candidates.
- The repair judge must *decide* the pairs it re-judges (both parts). "Replace the weaker judge" let the explains/practises default overrule R in 3 of 5 part-A repairs; found only when part B's findings looked wrong.
- Part B: judges substitute a verb for juist/onjuist and fill-in items (MB2 warns); the "antwoord is een berekening" raise must not fire when the verb gives a level, the number is given in the question, or R set the level.
- Candidates for exercises only offer criteria taught in the own or earlier paragraphs; judges repeatedly found criteria taught *later* (oefent vóór uitleg). Consider adding later-taught criteria at low priority.
- New agent types are not loadable in the session that creates them; run them as general-purpose agents that read the definition file.

## Lessons from examen run 1 (bedrijfseconomie vwo 2025-I + 2026-I, 2026-10-27)
- CvTE PDFs have a text layer, but `pdftotext` turns é/ë/€ and the scorepunt bullet into U+FFFD; PyMuPDF keeps them. The correctievoorschrift has two kinds of "of": a complete alternative route (ends the route once the bullets reach the maximumscore) and an alternative answer inside one scorepunt (→ note). `exam_text.py` parsed both exams with 0 issues; a regex bug (`Opmerkingen?` misses the singular "Opmerking") let remarks into scorepunt texts — fixed and now in the fixture.
- Two `exam-ingest` agents editing the same `21_exam_units.json` in parallel lost part of one agent's edits (10 scorepunt texts of 2026-I kept their remark). Run ingest agents sequentially, or give each exam its own file to merge.
- Agreement was high: 68 of 89 links high after merge; verifier 32/35 pass (sample of high links 14/14), 3 criterion disputes + 1 missing link, all four repairs followed the verifier. Cost 32 agent calls (2 ingest, 1 intake, 24 judges, 1 verifier, 4 repair) for two exams.
- The intake decisions did the heavy lifting: "prestatie telt" (bedrijfsecon-042) decides old-syllabus topics, 043 decides an exam's own assessment model (Collin Credit Score), 044 the meetkundige reeks. Judges cited them consistently. 20 of 124 points stay *buiten huidige syllabus* (SWOT, Porter, bedrijfsmodel, off-balance, resultaatmarge, domein-A arithmetic).
- Recurring disagreement: one scorepunt that tests sibling criteria equally (one point for examples of three groups of fixed assets) or whose alternative model answers fall under different criteria. Open decision proposed (one criterion + "raakt ook" vs. splitting).
- Candidate retrieval misses scorepunten whose line is bare ("voorwaarde b"); the correctievoorschrift table row that explains it should feed the query (verifier found the missing link).
- Judges record the verb of a supporting step (`berekenen`) under an "Analyseer" question; MB2 warns correctly — `bloom_verb` is the question's own asking verb, the level of the step is in `bloom`.
- Judges' prose miscounts points (reported 14 and 8 where the opgave had 9 and 6); scripts take points from the units only — keep it that way.
- Two exams test 54 of 410 criteria; the per-criterion overview becomes meaningful only with more exams.

## Lessons from koppel extend run 1 (In Balans H26–H28 on top of H16–H20, 2026-10-28/29)
- `/koppel --extend` worked end to end (938 candidate pairs, 324 links before review; verifier 35/47 pass, 12 disputes + 4 missing links, one repair round). `prepare` forgot `11_ingest_notes.md` — fixed; it now also carries `16_teacher_review.json`.
- The teacher's sample comments were often about a whole paragraph ("26.5 alleen F2.30.1"), not per row. Teacher review (specs/14 §5.1) records them deterministically — confirm/reject/correct, applied by `gradation.py`, never through an agent — and later extend samples skip reviewed links. Transcribe and read the list back to the teacher before writing it.
- A re-export overwrote a filled-in sample; `export_*` now moves a filled sample to `steekproef.ingevuld.md` first (specs/15 §4). Run part B exports only after the teacher's sample is safe.
- On Windows, an output CSV open in Excel blocks the export (PermissionError); ask the teacher to close it.
- Kostensoorten spread over paragraphs count as *noemt* (bedrijfsecon-053): a decision can be applied as teacher-review `correct` entries with the decision id as source.

## Lessons from koppel extend run 2 (LWEO Vraag en aanbod H3–H4 on top of H1–H2, 2026-10-29/30)
- Scanned PDF without a text layer and no `pdftoppm` on Windows: render pages with PyMuPDF (dpi 200) to PNG, then `ocr_images.py`. A chapter can start in the previous book file (H3 began on the last 4 pages of the H1–H2 PDF); ingest must stitch across files.
- Delta mode is cheap and safe: 84 old-paragraph pairs judged, 6 links added, no *leert* moved. The added criteria were mostly already explained earlier (D1.19-01-c in H1.3).
- Parallel judges sharing the scratchpad overwrote each other's helper files (`ids.json`); tell every judge to use unique scratch names.
- Repair judges applied an open verifier proposal (economie-046, drawing lines with known values) before the teacher answered it. If the intake decides otherwise, those pairs must be re-judged — repair prompts should say "apply answered decisions only".
- A decision that requires a note on the link (economie-043, 'vraagzijde') survives in judge notes but not in merged links; merge should carry decision-required notes.
- Economie has no subject verb table, so "opstellen" stays creëren and MB2 warned 102 times on judged toepassen; open decision economie-047 resolves it.

## Lessons from koppel run Levensloop (LWEO lesbrief 1, H1–H3, 2026-11-02)
- One run per lesbrief, not `--extend`: lesbrieven of one series each start at H1.1 (unit ids collide), cover different domains, and need their own `scope_criteria`, decisions and glossary scope. Cross-lesbrief *leert/herhaalt* needs a merge step over runs in series order (method profile); not built yet.
- The source /generate run again had no `04_groups_student.json`; `10_criteria.json` was copied from the previous koppel run of the same series, which keeps criterion ids identical for a later merge.
- Scanned PDF with pages that are only a 95×95 broken-image placeholder (pp. 40, 52, 53 and 60–89): re-rendering cannot recover them. Check `page.get_images()` sizes before OCR and ask the teacher early; the teacher chose to continue, ingest listed the gaps under "Ontbreekt in bron" and created no units for invisible questions.
- `decisions_snapshot.json` did not carry `scope`, so judges saw the other lesbrief's decisions as binding; fixed (`scope` per decision, specs/06 §4). One judge also misread the snapshot as "unanswered" — tell judges the answer is in `effective_answer`.
- The Windows console shows € as U+FFFD; the files are fine. Tell agents so they do not drop € from quotes.
- Part A verifier 35/42 pass, part B 89/118 (sampled high links 36/36); all disputes resolved in one repair round. Recurring part-B disputes: picking a term in a fill-in counts as practising, and "leg uit" questions answered by a procedure on data (Bloom; open decision economie-063).
- `ex_merge` takes the union of A and B, so a sub-question can end with 3–4 links when the judges chose different second criteria (3 cases); an extra R round capped them at 2. Consider a merge warning for > 2 links.
- Layered repair works: extra R files with a suffix (`H3.2.r046.json`, `H1.4.r2.json`) are read after `<paragraph>.json` and override per pair, so earlier repairs stay auditable.
- A judge found an error in the answer key (1.22e "6 > 3" should be "6 > 5"); report such findings to the teacher.
- Cost: 80 agent calls (5 transcribe, 1 ingest, 1 intake, 20 paragraph judges, 1+7 verify/repair, 32 exercise judges, 1+12 verify/repair).

## Lessons from koppel extend run 3 (Levensloop H4 + missing H2/H3 exercises, 2026-11-06)
- "Add to the last run" means the last run of the *same method*: `--extend` cannot cross lesbrieven. A new PDF can repair an earlier gap: the full scan restored pp. 40, 52, 53 and 60–72. Check `page.get_images()` sizes before assuming a source is still broken, and look for a newer file in the teacher's OneDrive.
- New sub-questions in old paragraphs fit `--extend` without new code: ids under existing parents, A/B as `<paragraph>.ext.json`. Sub-questions that need *re*-judging do not: `.ext.json` sorts before `.json`, so the old judgement wins on the same pair. Use a layered R file (`H2.5.r3.json`), which decides per pair.
- `merge-units` puts every new paragraph in `scope_paragraphs`, also Transfer and Zelftest, against economie-057. Removed by hand from `scope_paragraphs` and `extend.new_paragraphs`; a decision that limits paragraph kinds should be read by the script.
- Fixed in this run: `prepare` dropped `scope_exclude_groups`; a `todo` rerun overwrote `delta` (now cumulative, with `open` as the check before X4); `decisions.py add` silently skipped a generic question with the same text as an older one (now compares text, context and scope, and reports skips).
- The orchestrator forgot one delta paragraph (H1.4); the `todo` rerun exposed it. Always rerun `todo` before gradation.
- An answer like "zoals in de context voorgesteld" does not reach judges: `decisions_snapshot.json` has no `context`, so judges went to `decisions.json`. Add `context` to the snapshot, or record the full answer.
- An answer that names groups where the question named criteria (economie-074) leaves judges to interpret it: they all flagged it and reasoned their way to the same reading. Record the literal ids and state which roles it binds.
- Decision-required remarks still do not survive merge (economie-078 'deels' on 9 links, economie-074 on 5 gaps; same as economie-043); teacher review cannot carry them for exercises or gaps. Written by hand to `output/opmerkingen_besluiten.md`; merge and the gap report need a note channel.
- Criteria outside `scope_criteria` have no `per_criterion` list, so they reach judges only through a paragraph's top 10; the verifier found H1.1-02-a and E1.4-01-a that way. Consider candidates for criteria an answered decision names.
- `verb_level_exceptions` must be set from every answered level decision before `ex_merge` (economie-063 moved 10 links from medium to high). It was missing because the decision came after the previous run.
- H4 had many answer-key errors (4.4a, 4.15a/b, 4.20d, 4.28d, 4.29d); asking exercise judges to report them works, and they recompute. Collect them for the teacher.
- Cost: 63 agent calls (2 transcribe, 1 ingest, 1 intake, 30 paragraph judges, 1+3 verify/repair, 21 exercise judges, 1+3 verify/repair).
