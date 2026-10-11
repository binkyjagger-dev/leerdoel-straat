# Leerdoel-straat — Specification overview

**Status:** draft v0.1 · **Owner:** Martijn · **Domain language:** English (output artefacts in Dutch)

## 1. Purpose

A Claude Code pipeline ("straat") that takes a curriculum source — for v1 a CvTE
syllabus for *economie VWO*; later a textbook/method — and produces **learning
goal groups** (Dutch: *leerdoelgroepen*) in student language, each linked to the
source unit it covers, with coverage verified in both directions.

A learning goal group = one learning goal (*leerdoel*) + 2–4 success criteria
(*succescriteria*), each criterion tagged with a revised-Bloom cognitive level.
The learning goal's Bloom level is the maximum of its criteria.

Output of a run: a CSV of learning goal groups, a coverage report, and a
doubt list for the teacher.

## 2. Scope of v1

In scope
- Input: one text-based PDF of a CvTE syllabus (no OCR).
- Source structure: domein → subdomein → eindterm, with literal text per eindterm.
- Fully autonomous run; no human pause. Teacher reviews afterwards using the
  coverage report and doubt list.
- Each run starts blank — no mapping to existing canonical goals.
- Same formulation for HAVO and VWO (no level-specific variants).

Out of scope for v1 (but designed for)
- Textbook/method ingest (chapter → paragraph → text block). The data model is
  source-agnostic from the planner onwards; only the ingest adapter is
  source-specific. See [01-source-units.md](01-source-units.md).
- Combined syllabus + textbook runs linking a goal to both an eindterm and a paragraph.
- Import into Doelstellr. The CSV schema is provisional (see
  [05-export.md](05-export.md)); columns are redefined when import is designed.
- Knowledge dimension of revised Bloom, SOLO taxonomy, minimum goals per Bloom level.

## 3. Scientific anchors

| Anchor | Used for | Where enforced |
|---|---|---|
| Revised Bloom's taxonomy, cognitive process dimension (Anderson & Krathwohl, 2001) | Bloom level per success criterion; verb lists per level | `data/bloom_verbs_nl.json`, `scripts/bloom_check.py`, verifier |
| Constructive alignment (Biggs, 1996; Biggs & Tang, 2011) | Every goal is traceable to a source unit; the intended level of the goal matches the level implied by the source verb | planner, verifier coverage check |
| Learning intentions & success criteria (Clarke, 2005/2014; Hattie, 2009/2012; Wiliam, 2011) | Goal/criteria split; criteria are observable, student-facing; "Ik kan …" form | generator, student-language agent, verifier rubric |
| Behavioural objectives (Mager, 1962/1997) | Criteria name an observable performance, no "begrijpen/weten/kennen" as criterion verbs | bloom_check (forbidden verbs), verifier |

Student language rules derived from this literature are in
[02-learning-goal-groups.md §4](02-learning-goal-groups.md).

## 4. Architecture in one picture

```
syllabus.pdf
   │
   ▼
[1 ingest]  ──► runs/<id>/01_source_units.json      ─┐ validate (schema)
   │                                                  │
   ▼                                                  │
[2 planner] ──► runs/<id>/02_plan.json               ─┤ validate (schema + every unit planned)
   │                                                  │
   ▼                                                  │
[3 generator] (per unit, parallel) ──► 03_groups_raw.json  ─┤ validate (schema, bloom verbs, bloom max)
   │                                                  │
   ▼                                                  │
[4 student-language] ──► 04_groups_student.json      ─┤ validate (schema, "Ik kan", meaning preserved → verifier)
   │                                                  │
   ▼                                                  │
[5 verifier] (clean context) ──► 05_verification.json ─┤ coverage both ways + rubric
   │        └── gaps → back to [3] for those units, max 2 rounds
   ▼
[6 exporter] ──► output/leerdoelgroepen.csv, coverage_report.md, doubt_list.md
```

Principles
- **Files are the contract.** Every step reads one JSON file and writes one.
  No step depends on another step's chat context.
- **Deterministic where possible.** Schema validation, Bloom-verb checks,
  Bloom-max computation, coverage matrix and CSV export are Python scripts, not
  model judgement.
- **Judgement in a clean context.** The verifier never sees the generator's
  reasoning; it sees only source units and produced groups.
- **Bounded loops.** At most 2 repair rounds; unresolved items go to the doubt
  list, never silently dropped.
- **Portable.** Agent prompts, schemas and validators are plain files so the
  orchestrator can later be replaced by an Agent SDK service without rewriting
  the roles.

## 5. Documents

| File | Contents |
|---|---|
| [01-source-units.md](01-source-units.md) | Source-agnostic unit model; syllabus adapter; textbook adapter (future) |
| [02-learning-goal-groups.md](02-learning-goal-groups.md) | Definition, Bloom rules, student-language rules, quality rules |
| [03-pipeline.md](03-pipeline.md) | Roles, inputs/outputs, prompts' responsibilities, orchestration & repair loop |
| [04-verification.md](04-verification.md) | Deterministic checks, judge rubric, coverage definition, doubt list |
| [05-export.md](05-export.md) | Provisional CSV schema, coverage report, run folder layout |

## 6. Definition of done for v1

1. `/generate <syllabus.pdf>` runs end-to-end without human input on the
   economie VWO syllabus.
2. Every eindterm has ≥ 1 group; every group references exactly one existing
   eindterm (deterministic check passes).
3. All criteria carry a Bloom level whose verb is in the level's verb list;
   goal Bloom = max(criteria).
4. All goals and criteria start with "Ik kan" and pass the student-language
   checks.
5. CSV, coverage report and doubt list are written; doubt list is non-empty
   only for items the verifier still rejected after round 2.
6. A spot check by Martijn of 10 random groups finds them usable in class
   without rewriting (acceptance criterion; not automated).
