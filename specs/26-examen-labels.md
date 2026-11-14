# 26 — Examen-straat extension: pattern and knob labels, reference profile

**Status:** draft v0.1 (2026-11-13) · decided by Martijn as part of the toets-straat (specs/30 §5.5).

## 1. Purpose

The exam bank links every scorepunt to a criterion (specs/22) but says nothing about the *form* of a
question. The toets-straat needs that form in two places:

- the **reference profile**: per knob, the share of each value in the subject's central exams, shown
  to the teacher next to every knob (specs/32);
- the **catalogue statistics**: per pattern, how often it occurs, its point range, Bloom and SOLO
  spread, and which exam questions are good style examples (specs/31 §1, specs/33 §3).

This spec adds step **E7 Label** to `/examen`, an option to label exams already in the bank, and the
deterministic profile build. Labels are stored per exam in the bank and the profile is rebuilt after
every change, so it grows with every exam that is added.

## 2. What is labelled, and what is computed

Per **question** (not per scorepunt):

| Field | Source |
|---|---|
| `pattern` (one code; `+`-combination allowed for two, e.g. `P08+B02`) | labeller |
| `solo` | labeller |
| `route` (only calculation patterns, else `null`) | labeller |
| `steps` | labeller (1, 2, 3, 4+) |
| `sources` | labeller |
| `noise` | labeller (nee/ja) (decided 2026-11-14 after E7 run 1) |
| `claim`, `new_concept` | labeller (boolean) |
| `schema` (only schema patterns, else `null`) | labeller |
| `builds_on` | labeller; plus the referenced question numbers |
| `points` | exam units (never from the labeller) |
| `combination` | **computed**: distinct `group_id`s over the question's linked scorepunten (`also_touches` not counted) |
| `bloom` | **computed**: per scorepunt from the links; question level = max |
| `example_quality` | labeller: `goed` / `bruikbaar` / `ongeschikt` as style example, with one line why |

Every labelled value except `example_quality` carries an evidence quote ≤ 25 words verbatim from the
question, the source text or the correctievoorschrift (`evidence: {field: quote}`), checked as in
specs/24 (verbatim, length).

Because `combination` and `bloom` are computed from the links, **labels do not depend on the criteria
version**: a `--rebuild` of the bank keeps `labels/` and only recomputes those two fields.

## 3. Step E7 in `/examen`

After E6 (bank and export), for the exams of the run:

1. Agent `item-labeller` in **exam mode**, letters A and B as separate Agent calls in the same message,
   one opgave per agent, batch as E3 (`judge_batch`). Input: R, the opgave id, `data/toets/knobs.json`,
   `data/toets/patterns_base.json`, `subjects/<s>/toets/patterns.json`, the opgave's text in `R/text/`.
   Output `R/26_labels.{A,B}/<opgave_id>.json`.
2. `python3 scripts/exam/label_merge.py R` → `R/26_labels.json`, `R/26_label_findings.json`.
   - Agreement per field: equal → `high`; ordinal fields with **three or more values** one step apart →
     `medium` and the lower value; otherwise `disputed`. Two-valued knobs (`claim`, `new_concept`,
     `builds_on`, `route`, `schema`) never get `medium`: any difference is `disputed` and goes to R
     (decided 2026-11-13, bouwvraag 1).
   - `pattern` must agree exactly for `high`; otherwise `disputed`.
3. One repair round: per opgave with disputed fields, `item-labeller` letter R decides those fields
   (both values and their evidence given) → `R/26_labels.R/<opgave_id>.json`; rerun `label_merge.py`.
   No verifier: the R labeller decides, and the decision is final. Disputes left after R stay
   `disputed` and are excluded from the profile.
4. A labeller that finds no fitting pattern sets `pattern: "NIEUW"` with a `proposed_pattern`
   `{name, description, scoring, layer: "base"|"<subject>"}`. `label_merge.py` collects these into
   `R/26_proposed_patterns.json`. The orchestrator adds them as open decisions
   (`decisions.py add`, `applies_to: ["catalogue"]`) for the next intake. A pattern is added to the
   catalogue only via `scripts/toets/patterns.py add <subject> <decision-id> <file>` against an
   answered decision (specs/31 §6).
5. `python3 scripts/exam/bank_labels_add.py R` → `B/labels/<exam_id>.json` (same replace rules as
   `bank_add.py`: never touches other exams' files).
6. `python3 scripts/exam/profile_build.py <subject>` → `B/profiel/` (§4).

Labelling existing exams: `/examen --label --subject <s> [--exam <exam_id> …]` runs E0 (setup, no
criteria copy needed beyond the bank's), re-extracts the text of those exams from the paths in
`register.json` with `exam_text.py`, then E7 only. Default: every exam in the bank without a
`labels/` file.

## 4. Reference profile (`B/profiel/`, rebuilt by `profile_build.py`)

```
profiel/
  referentieprofiel.json   per knob: per value points + share, per exam and pooled; n_exams, n_questions
  referentieprofiel.md     the same as readable tables (Dutch), per knob, with the exams it is based on
  patronen_stats.json      per pattern: n questions, points (sum, min, max), Bloom and SOLO spread,
                           example candidates (exam_id, question_number, example_quality)
```

Rules:
- Shares are **by points**, conditional on applicability: `route` over calculation patterns only,
  `schema` over schema patterns only, `builds_on` over questions that are not the first of an opgave.
- `disputed` fields are left out of their knob's totals; the md shows how many points were left out.
- A combined pattern (`P08+B02`) splits the question's points **evenly** over its patterns, so the
  pattern column still sums to the exam's points; in `patronen_stats.json` the question counts once per
  pattern with its full points for min/max (decided 2026-11-13, bouwvraag 2).
- A question with `pattern: NIEUW` is left out of the pattern column **and** out of `route` and
  `schema` (their applicability depends on the pattern's kind) until the pattern is decided; its other
  knobs count (decided 2026-11-13, bouwvraag 6).
- Pooled = sum over all labelled exams of the bank, every exam weighted by its points.
  Per-exam columns are kept so the teacher sees the spread between exams.
- A seed profile (§6) is used only while the bank has no labels for that subject; the form and the
  verantwoording say which one is used ("referentie: 2 examens (2025-I, 2026-I)" or "referentie:
  voorlopig, analyse nov 2026").
- `profile_build.py` fails if the points in a per-exam column do not sum to that exam's labelled
  points (conservation, as specs/25).

The profile is **never edited by hand**. It changes only when labels change.

## 5. Files and schemas

- `schemas/item_labels.schema.json` — labeller output and merged labels (shared with the toets-straat,
  specs/34 §4).
- `schemas/reference_profile.schema.json`.
- `B/labels/<exam_id>.json`: per question `{question_id, question_number, opgave_id, points, pattern,
  solo, route, steps, sources, noise, claim, new_concept, schema, builds_on, builds_on_questions,
  combination, bloom, example_quality, confidence: {field: high|medium|disputed}, evidence}`.

## 6. Seed and start-up order

- **bedrijfseconomie**: the bank has 2025-I and 2026-I. Run `/examen --label --subject
  bedrijfseconomie` first (≈ 2 × 11 opgaven × 2 labellers + repairs).
- **economie**: no bank yet. Run `/examen` on the five exams (2024-I … 2026-I) against the economie
  criteria run, then E7. Until then `subjects/economie/toets/seed_profile.json` holds the November 2026
  analysis (pattern, SOLO and Bloom per question of five exams; the other knobs unknown → the form
  shows "onbekend" for them and the teacher sets them without reference).
- Seed files carry `"source": "seed-analysis-2026-11"` and are ignored once labels exist.

## 7. Checks (in `check_labels.py`, run after `label_merge.py`)

| Id | Check |
|---|---|
| LB1 | every question of the opgave has a label from A and from B |
| LB2 | `pattern` exists in base + subject catalogue (or is `NIEUW` with a proposal) |
| LB3 | applicability: `route` only on calculation patterns, `schema` only on schema patterns, else `null` |
| LB4 | evidence quotes verbatim and ≤ 25 words |
| LB5 | `builds_on_questions` refer to earlier questions of the same opgave |
| LB6 | points from units; the labeller's points, if present, are ignored |
