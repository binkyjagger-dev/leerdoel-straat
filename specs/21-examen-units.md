# 21 — Exam units

## 1. Input files

One folder per exam under `input/examens-<vak>/` (e.g. `input/examens-bedrijfseconomie-vwo/2025 TV1/`).
Files follow the CvTE naming `<lvl>-<vak>-a-<yy>-<tv>-<part>.pdf`:

| Suffix | Contents | Required |
|---|---|---|
| `-o` | opgavenboekje (questions) | yes |
| `-c` | correctievoorschrift (scoring model) | yes |
| `-b` | bijlage / informatieboekje (formuleblad, informatiebronnen) | when the exam has one |
| `-u` | uitwerkbijlage | optional (the correctievoorschrift shows the filled-in table) |

PDFs are not committed. Text extraction: `pdftotext -enc UTF-8` (both `-layout` and
raw); OCR (`ocr_pdf.py`) only when a page has no text layer.

## 2. Exam id

From the code on every page, `VW-0400-a-25-1` → `vwo-2025-tv1`
(`VW`→`vwo`, `HA`→`havo`; `25`→`2025`; tijdvak `1`). A second exam with the same id
(e.g. a pilot variant) gets a suffix declared at intake (`vwo-2025-tv1-b`).

## 3. Unit model (`21_exam_units.json`, schema `exam_units`)

```
exam       vwo-2025-tv1
 └ opgave  vwo-2025-tv1-o2          context block "Opgave 2"
    └ question  vwo-2025-tv1-q6     question number 6 (numbering runs through the exam)
       └ scorepunt  vwo-2025-tv1-q6-s1 … -s4
```

| Kind | Fields |
|---|---|
| `exam` | `exam_id`, `code` (`VW-0400-a-25-1`), `level`, `year`, `tijdvak`, `subject`, `n_questions`, `max_score` (both from the header), `files` (part → path), `syllabus_note` (intake), `text_extraction` (`text`/`ocr`) |
| `opgave` | `unit_id`, `exam_id`, `number`, `title` (first heading or first line), `sources` (informatiebron numbers named in the block), `text_ref` (context text) |
| `question` | `unit_id`, `opgave_id`, `number`, `points` (from `np` prefix), `text_ref` (question text incl. the context lines directly above it), `sources`, `formula` (formuleblad entry for this number, if any), `cv_ref` (the full correctievoorschrift entry), `cv_notes` (alternatives "of", *Opmerking(en)*) |
| `scorepunt` | `unit_id`, `question_id`, `seq`, `points`, `kind`, `text` (the scorepunt line from the correctievoorschrift, verbatim), `model_ref` (the model answer for this route) |

Text files live in `runs/<run_id>/text/` only (git-ignored):
`<exam>-o<n>.txt` (context), `<exam>-q<n>.txt` (question), `<exam>-q<n>.cv.txt`
(correctievoorschrift entry), `<exam>-bron<n>.txt` (informatiebron), `<exam>-formule.txt`.

## 4. Scorepunt kinds (from the correctievoorschrift, chapter *Beoordelingsmodel*)

Each question entry starts `n maximumscore k`. Then exactly one of:

| `kind` | Recognised by | Scorepunten |
|---|---|---|
| `bullet` | lines starting with `•` (extracted as `U+FFFD`) ending in a point value | one per bullet, `points` = that value |
| `per_item` | "per juist (toegelicht) antwoord / per juiste … `n`" | `k / n` scorepunten of `n` points each; `text` = the per-item line plus the example list |
| `whole` | no bullets and no per-item line (incl. "per gemaakte fout 1 scorepunt in mindering", multiple-choice "Kies de juiste letter") | one scorepunt with `points` = `k` (decision 20 §5.11) |

Alternative routes: the first route defines the scorepunten; text after a line
consisting of `of` up to the next question or *Opmerking* goes to `cv_notes`
(decision 20 §5.12). *Opmerking(en)* never create scorepunten.

## 5. Ingest roles

- `scripts/exam/exam_text.py <run_dir>`: extracts text per file, finds the header
  ("bestaat uit N vragen", "maximaal M punten"), splits opgaven (`Opgave n`),
  questions (`^\s*(\d+)p\s+(\d+)\s`), correctievoorschrift entries
  (`^\s*(\d+)\s+maximumscore\s+(\d+)`), informatiebronnen and formuleblad; writes a
  draft `21_exam_units.json` with a `parse_issues` list.
- Agent `exam-ingest`: resolves every `parse_issue` from the page text (questions
  missed by the regex, tables that fell apart, bullets split over lines, points
  printed in a separate column), fills `title`, `sources`, `formula`, writes
  `21_ingest_notes.md`. It never paraphrases: question and scorepunt texts stay
  verbatim (whitespace may be normalised, tables as `|` rows).

## 6. Ingest checks (`scripts/exam/validate_exam.py`)

| Id | Check | Severity |
|---|---|---|
| EU1 | schema `exam_units` | fail |
| EU2 | number of questions = header `n_questions`; numbers 1..N without gaps | fail |
| EU3 | Σ question `points` = header `max_score` | fail |
| EU4 | per question: `np` prefix in the opgavenboekje = `maximumscore` in the correctievoorschrift | fail |
| EU5 | per question: Σ scorepunt `points` = `maximumscore` | fail |
| EU6 | every question belongs to exactly one opgave; every opgave has ≥ 1 question | fail |
| EU7 | every informatiebron named in a question or opgave exists in the bijlage text | warn |
| EU8 | `parse_issues` empty | fail |
