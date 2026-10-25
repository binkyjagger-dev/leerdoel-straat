# 14 — Mapping verification

## 1. Deterministic checks (`scripts/mapping/check_mappings.py`)

| Id | Check | Severity |
|---|---|---|
| MS1 | schemas: method units, candidates, judgements, mappings | fail |
| MQ1 | every link's quote is verbatim in its paragraph text (OCR-tolerant when `text_extraction: ocr`) and ≤ 25 words | link voided (`invalid_quote`) |
| MQ2 | every `deelvraag` link's quote is verbatim in the question text | link voided |
| MG1 | per criterion in scope: exactly one `leert`, or the criterion appears in `14_findings.json` as gap | fail |
| MG2 | `noemt` links never shown as *leert* (first explains is computed on explains only) | fail |
| MG3 | every paragraph in scope has ≥ 1 link with gradation ≠ noemt, or is listed as outside-syllabus | fail |
| MG4 | the same quote (normalised) on criteria of two different groups | finding (J-M5) |
| MC1 | confidence computed per 12 §4 from judges A/B and quote validity | fail |
| MB1 | (part B) `bloom` in the subject's effective verb levels; answer-form rule applied when answer exists | fail |
| MB2 | (part B) `bloom_verb` is the question's own asking verb (found in the question text, separable verbs included) | warn |

## 2. Judge rubric (what a mapping-judge must satisfy)

- Decide treatment from what the paragraph **does**, not from term presence:
  a definition in a box is `mentions` unless the running text explains it.
- The quote must carry the evidence: for `explains` it shows the explanation;
  for `practises` the application; for `mentions` the term.
- When the criterion asks for a performance the paragraph only partly
  explains (the calculation but not the interpretation), still `explains`,
  with `aspect` naming the part covered — the gradation script uses it for
  the "breidt uit" note.
- Never infer from chapter titles; only from paragraph text.
- Criteria texts come from the student version and the expert version; judge
  against the expert version.

## 3. Mapping-verifier (agent, fresh context)

Inputs: units (with text refs), criteria, `14_mappings.json`, `14_findings.json`,
candidates (for the reverse lists), decisions, method profile.

**Precision pass** — over every link with confidence `low` or `medium`, plus a
random 20 % of `high`: is the treatment right and does the quote carry it?
Verdict `pass | dispute` with reason and, on dispute, the treatment the
verifier would give.

**Recall pass** — per paragraph in scope: read the paragraph text and the
reverse candidate list (top 10 criteria by score, including unlinked ones)
and name criteria the paragraph explains or practises that have **no** link
to it. Each becomes a `missing_link` proposal with a quote; the orchestrator
sends proposals to a repair judge (one round).

**Gradation pass** — for each criterion, is the *leert* paragraph plausibly
the first explanation? The verifier checks the paragraphs *before* it in
order that mention any of the criterion's concepts.

**Findings** — gaps that look like candidate-retrieval misses rather than
real gaps (concept phrased differently in the method ⇒ propose a glossary
entry or a decision); outside-syllabus paragraphs that actually belong to a
criterion.

Verdicts: a link `dispute`d twice (judge repair + verifier again) goes to the
sample list with both views.

## 4. Baseline comparison (`scripts/mapping/compare_baseline.py`)

Input: the teacher's hand baseline (CSV: `criterium_id;paragraaf;gradatie;opmerking`)
and `14_mappings.json`. Reports, on *leert* and *oefent* links:

- precision = straat links also in baseline / straat links;
- recall = baseline links found by straat / baseline links;
- gradation agreement on shared links;
- per-link diff table (straat only / baseline only / gradation differs) with
  the straat's quote and confidence, so each disagreement can be settled by
  reading one line.

`noemt` is excluded from both scores unless the baseline marks it.

## 5. Teacher sample (`output/steekproef.md`)

20 links, stratified: 10 `high`, 10 `low`/disputed; each with criterion text,
paragraph code/title/page, quote, gradation, confidence and the judges' and
verifier's views. Four columns to tick, like the spot check.

## 6. Exercise mode (part B, `19_ex_verification.json`)

Same agent, `mode: exercises`. Inputs: `17_ex_candidates.json`,
`18_ex_mappings.json`, sub-question and answer texts, criteria, effective
verb table, decisions.

- **Precision** — every `low`/`medium` link plus a random 20 % of `high`
  (seed = run id): is it the right criterion, does the quote show the ask,
  is `bloom` right given verb and answer? `pass | dispute`, with
  `criterion_should_be` (or `none`) and/or `bloom_should_be`.
- **Recall** — every sub-question in *oefenstof buiten syllabus* and every
  criterion in scope that is *niet geoefend*: is there a sub-question that
  does practise it? ⇒ `missing_links` (unit, criterion, bloom, quote).
- **Bloom gaps** — for *bloom niet bereikt*: is a linked question rated too
  low? ⇒ dispute with `bloom_should_be`.

`check_ex_mappings.py --verification` applies verdicts idempotently
(confidence adjusts from the judged value, never twice). A dispute that the
repair judge settled the verifier's way is recorded as `resolved`; so is a
disputed link the repair judge removed.
