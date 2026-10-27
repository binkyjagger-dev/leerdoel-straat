# 23 — Examen-straat pipeline

## 1. Command

`/examen <exam-folder> [<exam-folder> ...] --subject <slug> [--from <generate-run-id>] [--run-id <id>] [--rebuild]`

- Each `<exam-folder>` holds one exam's PDFs (21 §1); a parent folder with one
  subfolder per exam is expanded.
- `--from`: the `/generate` run whose `04_groups_student.json` provides the criteria.
  When the bank exists, `--from` must equal its `criteria_run` (else stop with a
  message); when it does not, `--from` creates it.
- `--rebuild --from <new run>`: start a new bank for new criteria (decision 20 §5.3):
  the old bank is moved to `examenbank.<old criteria_run>/`; every exam in the old
  register is re-ingested from its `files` and re-judged in this run.
- `--run-id` default `YYYYMMDD-HHMM-examen-<subject>`.
- `--replace`: exams already in the bank are replaced (25 §2). Without it the
  orchestrator asks the user once, before any agent runs, whether to replace or skip
  them.
- Criteria source: `runs/<criteria_run>/04_groups_student.json` and
  `01_source_units.json`; when that run folder is gone (runs are git-ignored) and the
  bank exists, the bank's own copies `criteria.json` / `source_units.json`.

Run folder `runs/<run_id>/`: `run.json`, `text/` (git-ignored), artefacts 20–25.
`run.json`: `{run_id, subject, criteria_run, exams: [exam_id], judge_batch: 4,
max_repair_rounds: 1, status, started_at}`.

## 2. Roles and files

| # | Role | Reads | Writes | Kind |
|---|---|---|---|---|
| E0 | setup | args, bank register | `run.json`, `20_criteria.json` (copy of the run's `04_groups_student.json`), `20_source_units.json` (copy of `01_source_units.json`, for subdomein/domein) | orchestrator |
| E1 | `exam_text.py` + `exam-ingest` | PDFs | `21_exam_units.json`, `text/*`, `21_ingest_notes.md` | script + agent (sonnet) |
| E1b | `intake` (exam mode) | units, notes, criteria, profile, decisions | `21b_intake_questions.json` → pause → `decisions.json` | agent (opus) |
| E2 | `exam_candidates.py` | units, criteria | `22_candidates.json` | script |
| E3 | `exam-judge` ×2 | one opgave: its questions, scorepunten, sources, candidates | `23_judgements.{A,B}/<opgave>.json` | agents (opus), fresh, parallel |
| E4 | `exam_merge.py`, `check_exam_mappings.py` | judgements, units, criteria | `24_mappings.json`, `24_findings.json` | scripts |
| E5 | `mapping-verifier` (exam mode) | units, text, criteria, mappings | `25_verification.json` | agent (opus), fresh |
| E5r | `exam-judge` R | disputed / missing scorepunten + reasons | `23_judgements.R/<opgave>.json` | agent, one round |
| E6 | `bank_add.py`, `bank_export.py` | mappings, verification, units | `subjects/<s>/examenbank/…` | scripts |

## 3. Steps

- **E1.** `exam_text.py` per exam, then one `exam-ingest` per exam (sequentially: they edit the same units file) to
  resolve `parse_issues`; `validate_exam.py` must pass (21 §6).
- **E1b.** One pause for all exams of the run. Typical exam-mode questions: syllabus
  version the exam was written for (`syllabus_note`); content in the exam that the
  current syllabus no longer has; exam terms that differ from criterion terms
  (glossary); duplicate exam ids. Answers via `decisions.py` (`scope: exam_id` when
  exam-specific); snapshot into the run.
- **E2.** Per scorepunt, rank all criteria by term overlap (idf over criteria) between
  the criterion (expert text + goal + concepts) and: scorepunt text ×3, question text
  ×2, opgave context and named sources ×1. Top 8, at least 3 when any score > 0.
  Judges may link any other criterion and say why.
- **E3.** Per opgave two judges (`A`, `B`) as separate Agent calls in the same
  message; up to `judge_batch` opgaven per message. Python command and decisions
  snapshot are passed in the prompt.
- **E4.** Merge per 22 §4; checks per 24 §1 must pass.
- **E5.** Verifier (exam mode, 24 §3), then `check_exam_mappings.py --verification`.
  Repair once: disputed links and `missing_links`, grouped by opgave, one `exam-judge`
  R per opgave; copy `24_mappings.json` → `24_mappings.round1.json`; rerun E4.
  Verifier `proposed_decisions` → `decisions.py add` (open).
- **E6.** `bank_add.py R` merges the run's exams into the bank (25 §2);
  `bank_export.py <subject>` rebuilds `examenbank/output/` from the whole bank.
  `exam_sample.py R` writes `R/output/steekproef.md` for the teacher: 10 `high`
  links and 10 `low`/`medium` links (low first), seeded on the run id, each with
  the scorepunt line from the correctievoorschrift, the quote, the judges, the
  verifier, and four J/N questions (right criterion? right Bloom? quote carries the
  ask? would a student practising this criterion be helped by this question?).
  It stays in the run folder (it contains correctievoorschrift text).
  `status: done`.

## 4. Report (≤ 10 lines)

Exams added, scorepunten and points linked / unlinked per exam, confidence split,
Bloom split, findings (buiten huidige syllabus, boven/onder criterium), disputes left,
bank size (exams), paths.

## 5. Rules

Paths not contents in prompts. The orchestrator never writes a link, quote or point.
Keep every intermediate file. Exam text never leaves the run folder.
