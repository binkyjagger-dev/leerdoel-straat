# 20 — Examen-straat: overview

**Status:** draft v0.1 (2026-10-27) · **Owner:** Martijn · **Decided:** see §5 and
[docs/plan-examen-straat.md](../docs/plan-examen-straat.md) §2.

## 1. Purpose

A third pipeline in this repo, `/examen`, that links the success criteria produced
by `/generate` to central exams (*centrale examens*, CvTE). The unit of linking is
the **scorepunt** of the correctievoorschrift: every scorepunt is linked to exactly
one criterion (or to none, which is a finding). Links accumulate in a persistent
**exam bank per subject**; every run adds one or more exams to it.

Output (rebuilt from the whole bank after every run):
- points per exam per criterion, learning goal group, subdomein and domein,
  absolute and as % of the exam's maximum score;
- a lookup index: per criterion, every scorepunt that tests it (exam, opgave,
  question number, scorepunt, points, Bloom, quote, confidence).

## 2. What is different from `/koppel`

- **Scorepunt, not question.** The correctievoorschrift splits a question's
  maximum score into scorepunten; points are assigned per scorepunt, so a question
  can test two criteria with an exact point split.
- **Points are conserved.** For every exam: linked points + unlinked points =
  maximum score from the exam header. Checked deterministically.
- **No book order, no gradation.** There is no *leert/oefent*; a link is
  "this scorepunt tests this criterion at this Bloom level".
- **Cumulative.** A run's result is merged into `subjects/<vak>/examenbank/`
  (in git). The bank is bound to one criteria version (one `/generate` run).
- **Whole syllabus in scope.** An exam may test any criterion; candidates are
  drawn from all criteria, not from a paragraph's part-A links.

The principles of `/koppel` carry over unchanged: evidence by verbatim quote
(≤ 25 words), two independent judges, a fresh verifier, one repair round,
confidence from agreement.

## 3. Pipeline in one picture

```
input/examens-<vak>/<dir per exam>/*-o.pdf  *-c.pdf  *-b.pdf     runs/<generate-run>/04_groups_student.json
   │                                                                   │
[E1  exam_text.py + exam-ingest] ──► 21_exam_units.json (+ text/ in run only) ◄── validate_exam.py
   │
[E1b intake, exam mode] ──► PAUSE (all exams of the run) ──► subjects/<s>/decisions.json
   │
[E2  exam_candidates.py] ──► 22_candidates.json           scorepunt → top 8 criteria
   │
[E3  exam-judge ×2 per opgave] ──► 23_judgements.{A,B}/<opgave>.json
   │
[E4  exam_merge.py + check_exam_mappings.py] ──► 24_mappings.json, 24_findings.json
   │
[E5  mapping-verifier, exam mode] ──► 25_verification.json ──► exam-judge R (1 round) ──► E4 again
   │
[E6  bank_add.py] ──► subjects/<s>/examenbank/   [bank_export.py] ──► examenbank/output/*
```

## 4. Documents

| File | Contents |
|---|---|
| [21-examen-units.md](21-examen-units.md) | Input files, exam unit model (exam → opgave → question → scorepunt), parsing rules, ingest checks |
| [22-examen-mapping-model.md](22-examen-mapping-model.md) | Link per scorepunt, Bloom, confidence, findings, point aggregation |
| [23-examen-pipeline.md](23-examen-pipeline.md) | Command, roles, run files, orchestration, repair, rebuild |
| [24-examen-verification.md](24-examen-verification.md) | Deterministic checks, judge rubric, verifier (exam mode) |
| [25-examen-bank-export.md](25-examen-bank-export.md) | Bank layout, merge rules, CSV/xlsx/Markdown outputs |

## 5. Decisions taken 2026-10-27

1. Points per scorepunt; one criterion per scorepunt; a second criterion it touches
   is recorded as `also_touches` without points.
2. Older exams are always linked to the current criteria; content outside the
   current syllabus is a finding, and the exam's syllabus version is registered.
3. The bank is bound to one criteria version; new criteria ⇒ a new bank, rebuilt by
   re-ingesting the exams (scripts) and re-running the judges.
4. Output: CSV (+ xlsx when `openpyxl` is available) and Markdown.
5. Bloom per scorepunt, with findings when the exam tests higher or lower than the
   criterion.
6. Verification as in `/koppel`: judges A and B, fresh verifier, one repair round.
7. The lookup index holds reference + quote ≤ 25 words; exam text stays in the run.
8. Several exams per run, one intake pause for all of them.
9. Bank in `subjects/<vak>/examenbank/`, committed.
10. Figures: points per exam and % of the maximum score, per criterion, group,
    subdomein and domein.
11. A question of ≥ 2 points without scorepunt split is one scorepunt with all points.
12. Alternative routes ("of"): only the first route is linked; alternatives are notes.
13. The uitwerkbijlage is optional input.

## 6. Definition of done (v1)

1. `/examen` processes bedrijfseconomie vwo 2025-I and 2026-I without human input
   except the intake.
2. Per exam, the scorepunten sum to the header's maximum score; every scorepunt has a
   criterion or is listed as *buiten huidige syllabus*.
3. Every stored quote is verbatim in its question text and ≤ 25 words.
4. A second run adding one exam leaves existing bank links unchanged (byte-identical
   `links/<exam>.json` for untouched exams).
5. Martijn's stratified sample (10 high / 10 low confidence): high ≥ 95 % correct;
   low clearly worse.
