# 13 — Methode-straat pipeline

## 1. Command

`/koppel <method.pdf> [--answers <answers.pdf>] --subject <slug> --method <method_id> --from <generate-run-id> [--chapters 1,2] [--run-id <id>] [--part A|AB]`

- `--from` names the `/generate` run whose `04_groups_student.json` provides
  the criteria (ids, texts, Bloom, concepts). The orchestrator copies that file
  into the koppel run as `10_criteria.json` so the run is self-contained.
- `--chapters` limits scope (baseline runs: `1,2`). Criteria outside scope are
  not a gap.
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
Per 11 §2.1. Writes paragraph texts to `text/<unit_id>.txt`; sub-question
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
  paragraph `concepts` and text (stemmed, lower-case; subject glossary applied);
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
replaces the weaker judgement and M4 reruns. What is still disputed goes to
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
