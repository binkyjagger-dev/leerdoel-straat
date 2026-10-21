# 04 — Verification

Two layers: deterministic checks (scripts, always run, hard fail) and
judgement checks (verifier agent in a clean context, rubric-based).

## 1. Coverage definition

"Covered" means **both**:

- **Forward:** every leaf unit has ≥ 1 group with `status != rejected`.
- **Backward:** every group references exactly one `unit_id` that exists and is
  a leaf, and its `source_quote` is a verbatim substring of that unit's `text`.

No minimum per Bloom level. Over-coverage (more groups than planned) is
reported, not failed.

`scripts/coverage.py` produces `coverage.json`:

```json
{
  "units_total": 48, "units_covered": 47, "units_uncovered": ["E3.2"],
  "groups_total": 93, "groups_orphan": [], "groups_quote_mismatch": ["D2.1-02"],
  "per_unit": [ { "unit_id": "D1.1", "planned": 2, "produced": 2, "bloom_levels": ["begrijpen","toepassen"] } ],
  "coverage_pct": 97.9
}
```

## 2. Deterministic checks (`scripts/validate.py`, `bloom_check.py`, `student_language_check.py`)

| Id | Check | Stage | Severity |
|---|---|---|---|
| S1 | JSON validates against schema | each step | fail |
| S2 | `unit_id` unique; parents exist; leaves have text | ingest | fail |
| P1 | every leaf planned exactly once; slots ≥ 1 | planner | fail |
| G1 | #groups per unit == planned slots | generator | fail (retry once) |
| G2 | 2 ≤ #criteria ≤ 4 | generator | fail |
| G3 | `bloom_verb` in the **effective** verb table for `bloom` (generic table + subject overrides, 02 §2 rule 6; ambiguous verbs: level in allowed set) | generator | fail |
| G4 | no forbidden verb as criterion main verb | generator | fail |
| G5 | `goal.bloom` == max(criteria.bloom) (computed & overwritten) | generator | auto-fix |
| G6 | `goal.bloom` ≤ `target_bloom_max` + 1 | generator | warn → verifier |
| G7 | `source_quote` verbatim in unit text (whitespace-normalised) | generator | fail |
| L1 | every `text_student` starts with "Ik kan " | student-language | fail |
| L2 | no forbidden student verbs/phrases (list in rules file) | student-language | fail |
| L3 | sentence ≤ 20 words; single sentence | student-language | warn |
| L4 | ids, bloom, counts unchanged vs. raw file | student-language | fail |
| C1 | forward coverage 100 % | verifier | gap → repair |
| C2 | backward coverage 100 % | verifier | gap → repair |

## 3. Judgement rubric (verifier agent)

Applied per group; each rule yields pass/fail with a one-line reason.

| Id | Rule | Anchor |
|---|---|---|
| J1 | **Alignment:** the goal addresses what the eindterm asks, at the implied cognitive level — not a neighbouring topic, not a generalisation. | Biggs |
| J2 | **Bloom fit:** each criterion's level matches the performance actually described (not just the verb). "Uitleggen" that is really reproduction of a definition is onthouden. | Anderson & Krathwohl |
| J3 | **Observability:** each criterion names a performance a teacher could check from student work. | Mager, Clarke |
| J4 | **Sufficiency:** meeting all criteria means the goal is met; no essential performance from the eindterm is missing. | Clarke, Wiliam |
| J5 | **Distinctness:** criteria are not restatements; groups of the same unit do not overlap in focus. | — |
| J6 | **Meaning preserved:** `text_student` says the same as `text_expert`; no performance softened, dropped or added; Bloom category of the verb survives. | — |
| J7 | **Student usability:** a 16-year-old can read it unaided and decide "kan ik dit al?"; economic terms kept, curriculum jargon gone. | Hattie, Clarke, SLO |
| J8 | **Economic correctness:** the content is economically correct and consistent with how the syllabus uses the term. | domain |

Verdict per group: `pass` (all J pass or only J7 soft issues), `revise`
(fixable; ≤ 2 failing rules, none J1/J8), `reject` (J1 or J8 fails, or ≥ 3
rules fail).

Output `05_verification.json`:

```json
{
  "round": 1,
  "coverage": { "...": "copied from coverage.json" },
  "groups": [
    { "group_id": "D1.1-01", "verdict": "revise",
      "issues": [ { "rule": "J3", "criterion_id": "D1.1-01-b", "reason": "…" } ],
      "suggested_fix": "Vervang 'inzicht hebben in' door een waarneembare handeling, bv. 'uitleggen aan de hand van een grafiek'." }
  ],
  "unit_findings": [ { "unit_id": "E3.2", "finding": "uncovered" } ]
}
```

The verifier must **not** rewrite content; it only critiques. This keeps
generation and judgement separated.

## 4. Doubt list

`output/doubt_list.md` collects, grouped by unit:
- groups still `revise`/`reject` after the last round, with issues and
  suggested fix;
- uncovered units;
- G6 warnings (goal level above source-implied level);
- ingest notes (uncertain extraction).

Each entry is one line plus the suggested fix, so Martijn can work through it
in minutes, not hours.
