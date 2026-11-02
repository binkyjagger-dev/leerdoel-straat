# 13 — Methode-straat pipeline

## 1. Command

`/koppel <method.pdf | image-folder> [--workbook <file.docx|pdf> ...] [--answers <answers.pdf> ...] --subject <slug> --method <method_id> --from <generate-run-id> [--chapters 1,2] [--run-id <id>] [--part A|AB|B] [--extend <finished-run-id>]` (extend: §5)

- The book is a PDF or a folder of page images (11 §2.2). `--workbook` names a
  separate exercise file (.docx or PDF) whose exercises refer to paragraphs.

- `--from` names the `/generate` run whose `04_groups_student.json` provides
  the criteria (ids, texts, Bloom, concepts). The orchestrator copies that file
  into the koppel run as `10_criteria.json` so the run is self-contained.
- `--chapters` limits scope (baseline runs: `1,2`). Criteria outside scope are
  not a gap.
- `scope_criteria` in `run.json` (optional, set by the orchestrator from an
  intake decision): the criterion `unit_id`s this method part is expected to
  teach. Candidates and judges still consider every criterion and links to
  other criteria are kept, but only criteria of these units can be a gap
  (`niet in deze methode`, `alleen geoefend`, `alleen genoemd`) and MG1 only
  checks them. Absent = all criteria. `12_candidates.json` carries the
  resolved criterion ids as `scope_criteria`; `per_criterion` lists only
  those, so criteria outside it reach a judge only through a paragraph's own
  top list (`per_paragraph`).
- `scope_exclude_groups` in `run.json` (optional, set by the orchestrator from an
  intake decision, added 2026-10-28): group ids (`F2.31.1-02`) taken out of
  `scope_criteria` although their unit is in it. Their criteria are not in
  `scope_criteria` of `12_candidates.json`, so they are never a gap; links to them
  are kept like links to any criterion outside the scope.
- `verb_level_exceptions` in `run.json` (optional, set by the orchestrator from
  an answered intake decision, added 2026-11-02): a list of
  `{"verbs": [...], "bloom": <level>, "decision": <id>}`. In part B a link whose
  `bloom_verb` is one of `verbs` and whose `bloom` equals `bloom` keeps its
  confidence although the verb table gives another level (12 §6.2). Mapping
  only: the verb table and `/generate` are untouched. Carried over by `--extend`.
- `--part A` (default) stops after M6; `AB` continues with exercises.

Run folder: `runs/<run_id>/` with `run.json`, `text/` (git-ignored), numbered
artefacts 10–19, `output/`.

## 2. Roles

| # | Role | Reads | Writes | Kind |
|---|---|---|---|---|
| M1 | `method-ingest` | PDF(s), method profile | `11_method_units.json`, `text/*.txt`, `11_ingest_notes.md` | agent (sonnet) + OCR tooling |
| M1b | `intake` (existing role, mapping mode) | units, criteria, profiles, decisions | `11b_intake_questions.json` → pause → `decisions.json` | agent (opus) |
| M2 | candidates | units + criteria | `12_candidates.json` | script |
| M3 | `mapping-judge` ×2 | one paragraph's candidates (text + criteria) | `13_judgements.A/<unit>.json`, `…B/…` | agents (opus), fresh, parallel per paragraph |
| M4 | gradation + confidence | all judgements | `14_mappings.json` | script |
| M5 | `mapping-verifier` | units, criteria, mappings, text | `15_verification.json` | agent (opus), fresh |
| M5r | `mapping-judge` (repair) | disputed links + verifier reasons | updated judgements | agent, one round |
| M6 | export | mappings, verification | `output/*` | script |

### M1 method-ingest
Per 11 §2.1 (PDF lesbrief) or §2.2 (page images + workbook), as the method
profile's *Opbouw* says. Writes paragraph texts to `text/<unit_id>.txt`; sub-question
texts and answers likewise. Validates with `validate_method.py`.

### M1b intake (mapping mode)
Same agent and pause mechanism as `/generate`; questions typical for mapping:
book order confirmation, chapters out of scope, how to treat boxes/kaders,
method terms that differ from syllabus terms, a criterion the method seems not
to cover at all (ask before declaring a gap), OCR pages that are unreadable.
Answers go to `subjects/<subject>/decisions.json` with `scope: method_id`.

### M2 candidates (`scripts/mapping/candidates.py`)
Per criterion, score every paragraph in scope:
- concept overlap: criterion `concepts` and goal/criterion text terms vs
  paragraph `concepts` and text (stemmed, lower-case; subject glossary applied
  before stemming, entries with scope null or the method id — 06 §8);
- lexical similarity (TF-IDF cosine on paragraph text vs criterion expert text);
- optional structural prior: syllabus domain ↔ chapter mapping from the
  method profile when given.
Keep top 6 (min score threshold), always ≥ 3. Also the reverse list per
paragraph (top criteria) for the verifier's recall test. No LLM call.

### M3 mapping-judge
Called **per paragraph** with: paragraph text, its candidate criteria (ids,
expert + student text, Bloom), the method profile, decisions. For each
candidate: `treatment` + `quote` (+ optional second quote, + `aspect` note
when the explanation covers only part of the criterion). The judge does not
know about other paragraphs and does not assign gradations. Two judges, A and
B, same prompt, separate contexts; the orchestrator launches both.

### M4 gradation (`scripts/mapping/gradation.py`)
Quote check (12 §3) → merge A/B → confidence (12 §4) → sort by `order` →
gradation (12 §2) → `14_mappings.json` + `14_findings.json` (gaps, oefent vóór
uitleg, duplicates across groups).

### M5 mapping-verifier
See 14. Outputs per link `pass | dispute` with reason, per paragraph the
recall findings, and confidence adjustments. Disputed links go once to a
repair judge (fresh context, sees both judgements + the dispute); the result
replaces the judgement(s) that disagree with it — R decides the pair; when
R disagrees with both, confidence is at most medium — and M4 reruns. What is still disputed goes to
the sample list.

### M6 export
See 15.

## 3. Orchestration rules
Identical to `/generate`: paths not contents in prompts; validator after each
step; one pause (M1b); nothing deleted; `.round<N>` copies before overwrite;
report ≤ 10 lines at the end (criteria in scope, paragraphs, links by
gradation, confidence split, gaps, outside-syllabus, sample size, paths).

## 4. Part B (exercises) — M7–M9

| # | Role | Writes |
|---|---|---|
| M7 | exercise candidates (script) | `17_ex_candidates.json`: per sub-question the criteria its paragraph or earlier paragraphs *leert/oefent*, ranked by concept overlap |
| M8 | `exercise-judge` ×2 (agents, per paragraph's exercises) | `18_ex_judgements.A/B` : criterion(s), `bloom`, quote, `answer_checked` |
| M8b | merge + confidence + Bloom reconciliation (script) | `18_ex_mappings.json` |
| M9 | `mapping-verifier` (exercise mode) + export | `19_ex_verification.json`, `output/koppelingen_opgaven.csv`, `bloom_gaten.md` |

Bloom reconciliation: judge's `bloom` is checked against the subject's
effective verb table (`verb_table.py effective`) and, when an answer exists,
against the answer form (12 §6). Disagreement ⇒ medium confidence and a note.

Part B scope: every paragraph of the chapters in scope, including those taken
out of part A (Transfer/Zelftest: their exercises are the point). Scripts:
`ex_candidates.py` (M7), `ex_merge.py` (M8b), `check_ex_mappings.py`
(MQ2, MB1, MC1, verdicts), `export_exercises.py` (M9 export);
`export_mappings.py` is rerun so the gap report sees exercise links.
Judges: agent `exercise-judge`, letters A/B per paragraph, R for repair
(one round: disputed links and `missing_links` of `19_ex_verification.json`).
Files: `17_ex_candidates.json`, `18_ex_judgements.<J>/<paragraph>.json`,
`18_ex_mappings.json`, `19_ex_verification.json`; `.round1` copies before
the repair rerun.

## 5. Extending a finished run (`--extend <run_id>`, decided 2026-10-28)

Adds chapters of the same method to a finished run `P` without re-judging what
`P` already judged. The result is a **new run** `R` that contains `P` plus the
new chapters; `P` stays untouched.

**Invariant.** Every candidate pair (paragraph × criterion) of `R` has a judgement
of judge A and of judge B. Pairs judged in `P` keep `P`'s judgements (and repairs);
only pairs without them are judged in `R`. Gradation, findings and export are
recomputed over all paragraphs, so a criterion that was a gap in `P` gets its
*leert* in a new chapter, and *leert* can move when a new chapter comes earlier in
book order.

Steps (`scripts/mapping/koppel_extend.py`):

| # | What | Files |
|---|---|---|
| X0 | `koppel_extend.py prepare R P` — copy from `P`: `10_criteria.json`, `run.json` fields (`method_id`, `from_run`, `scope_criteria`, `ex_scope_*`, `verb_level_exceptions`, `part`), `text/` (incl. `_pages_*`), `input/`, `13_judgements.{A,B,R}/`, `18_ex_judgements.{A,B,R}/`, `11_ingest_notes.md`, `16_teacher_review.json` (14 §5.1); `11_method_units.json` → `11_method_units.prev.json`; `15_verification.json` → `15_verification.prev.json`, `19_ex_verification.json` → `19_ex_verification.prev.json`. New book files go to `R/input/ext/` (images in `R/input/ext/book/`). `run.json` gets `extend: {from_run_id: P}`. | |
| X1 | `method-ingest` in **extend mode**: only the new chapters → `11_method_units.new.json` (same schema), text files in `text/` (OCR pages in `text/_pages_ext/`), notes appended to `11_ingest_notes.md`. | |
| X1b | `koppel_extend.py merge-units R` — `prev` + `new` → `11_method_units.json`. Unit ids must not collide. Paragraph `order` is renumbered by book order: (chapter number, paragraph number) unless the method profile declares another order. `run.json`: `scope_paragraphs` = old ∪ new, `extend.new_paragraphs`. Then `validate_method.py`. | |
| X1c | Intake (mapping mode) on the new units only; scope answers *add* to `scope_criteria`. | |
| X2 | `candidates.py R` over all paragraphs; then `koppel_extend.py todo R` → `12_extend_todo.json`: `new_paragraphs` (full A/B judging) and `delta` (old paragraph → criteria in its candidate union without an A or B judgement). | |
| X3 | `mapping-judge` A and B per new paragraph (as M3), and per old paragraph in `delta` with the listed criteria only, written to `13_judgements.<J>/<unit>.ext.json` (gradation reads every file of the judge folder). | |
| X4 | `gradation.py R`, `check_mappings.py R`. | |
| X5 | `mapping-verifier` with scope = new paragraphs + `delta` pairs → `15_verification.ext.json`; `koppel_extend.py merge-verification R` → `15_verification.json` (`prev` + `ext`); `check_mappings.py R --verification 15_verification.json`. Repair once as M5, R judgements as `13_judgements.R/<unit>.ext.json`. | |
| X6 | Part B, when `P` had it: new chapters' exercises (if any) as M7–M9 for their paragraphs only; `ex_candidates.py` and `ex_merge.py` rerun over everything. When `scope_criteria` grew, the exercise verifier runs a **recall-only** pass for the added criteria over all sub-questions → `19_ex_verification.ext.json`, merged like X5; one repair round. Without new exercises and without scope growth, `P`'s part B is carried over and only recomputed. | |
| X7 | Export as M6 (+ part B export). `steekproef.md` samples only links on new paragraphs and `delta` pairs (`run.json` `extend`). | |
