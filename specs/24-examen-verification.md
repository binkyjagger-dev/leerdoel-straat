# 24 — Exam mapping verification

## 1. Deterministic checks (`scripts/exam/check_exam_mappings.py`)

| Id | Check | Severity |
|---|---|---|
| ES1 | schemas: exam units, candidates, judgements, mappings | fail |
| EQ1 | every link's quote is verbatim in its question text (whitespace/punctuation normalised) and ≤ 25 words | link voided (`invalid_quote`) |
| EP1 | every scorepunt of every exam appears exactly once in `24_mappings.json` (linked or unlinked) | fail |
| EP2 | per exam: Σ linked points + Σ unlinked points = `max_score` | fail |
| EP3 | every link's `points` equals its scorepunt's `points` | fail |
| EC1 | every `criterion_id` / `also_touches` id exists in `20_criteria.json`; `also_touches` never contains the linked criterion | fail |
| EC2 | confidence computed per 22 §4 | fail |
| MB1 | `bloom` in the effective verb levels; answer-form rule applied (22 §3) | fail |
| MB2 | `bloom_verb` is the question's own asking verb (found in the question text; separable verbs and stem variants such as *motiveer/motiveren* included) | warn |

## 2. Judge rubric (`exam-judge`)

- Judge per **scorepunt**: what must the candidate deliver for this point (22 §2)?
  Read the scorepunt line and the model answer, not only the question.
- One criterion per scorepunt; a genuinely co-tested second criterion goes to
  `also_touches`, never as a second link.
- No criterion fits ⇒ `criterion_id: null` with a one-line `note` (what is tested and
  why no criterion covers it).
- Judge against the criterion's expert text; the student text is context.
- Quote from the question text; the shared context above the question only when the
  question line itself carries no ask.
- Decisions in the snapshot apply (glossary, syllabus notes).
- Repair mode (`R`): only the listed scorepunten; decide each (link or null) and say
  in `reason` what settled it.

## 3. Mapping-verifier, exam mode (fresh context)

Inputs: exam units and text, `20_criteria.json`, `24_mappings.json`,
`24_findings.json`, `22_candidates.json`, decisions snapshot, subject profile.

- **Precision** — every `low` and `medium` link plus a seeded random 20 % of `high`
  (seed = run id): is this the criterion the scorepunt tests, is the Bloom level
  right, does the quote carry the ask? Verdict `pass | dispute` with
  `criterion_should_be` / `bloom_should_be` and reason.
- **Recall** — every scorepunt without criterion: does a criterion cover it after all
  (`missing_links`)? And per question: does a scorepunt test a criterion the judges
  missed?
- **Points sanity** — per exam, the top 10 criteria by points: plausible given the
  exam? (Report only.)
- `proposed_decisions` in intake-question shape for recurring issues (e.g. a
  performance the exams test every year that no criterion names). Do not repeat
  decisions already open.

Verifier never rewrites links; it judges.
