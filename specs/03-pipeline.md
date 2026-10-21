# 03 — Pipeline: roles and orchestration

## 1. Orchestrator (`/generate`)

Slash command `.claude/commands/generate.md`. Invoked as
`/generate input/syllabus.pdf [--run-id <id>]`. It:

1. Creates `runs/<run_id>/` (default `run_id` = `YYYYMMDD-HHMM-<slug>`), copies
   the input, writes `run.json` (config, timestamps, model, round counters).
2. Calls each role in order through the Agent tool, **passing file paths, not
   content**. After each role it runs the deterministic validator for that
   step. A validation failure is fed back to the same role once; a second
   failure aborts the run with the validator output in `run.json`.
3. Runs the repair loop (§3) and the exporter.
4. Prints a 10-line summary: units, groups, coverage %, doubt-list size, paths.

The orchestrator never edits content itself. It owns control flow and files.

## 2. Roles

Each role is a subagent in `.claude/agents/<role>.md` with its own system
prompt, allowed tools and model. Prompts reference the spec sections they
implement; they do not restate rules that live in `data/*.json`, they read them.

| # | Role | Reads | Writes | Tools | Model |
|---|---|---|---|---|---|
| 1 | `ingest` | input PDF | `01_source_units.json`, `01_ingest_notes.md`, `01_verb_table.json` (only if the source defines a verb table) | Bash (pdftotext/python), Read, Write | sonnet |
| 1b | `intake` | `01_source_units.json`, `01_ingest_notes.md`, `01_verb_table.json` (if present), `subjects/<s>/profile.md`, `subjects/<s>/decisions.json`, `subjects/<s>/bloom_verbs.json` (if present) | `01b_intake_questions.json` → orchestrator pauses, writes answers to `decisions.json`; an adopted verb table is installed to `subjects/<s>/bloom_verbs.json` and `bloom_verbs_effective.json` is written | Read, Write | opus, fresh context |
| 2 | `planner` | `01_source_units.json`, `bloom_verbs_effective.json` | `02_plan.json` | Read, Write | opus |
| 3 | `generator` | `02_plan.json` (one unit), unit text, `bloom_verbs_effective.json`, `data/*.json`, spec §02 | `03_groups_raw/<unit_id>.json` | Read, Write | opus |
| 4 | `student-language` | `03_groups_raw.json` (merged), `data/student_language_rules.json` | `04_groups_student.json` | Read, Write | sonnet |
| 5 | `verifier` | `01_source_units.json`, `04_groups_student.json`, `02_plan.json`, `bloom_verbs_effective.json`, `data/*.json`, spec §02/§04 | `05_verification.json` | Read, Write, Bash (run scripts) | opus, **fresh context** |
| 6 | exporter | `04_groups_student.json`, `05_verification.json`, `01_ingest_notes.md` | `output/*` | script, no model | — |

### 2.1 ingest
See 01-source-units §2. Outputs literal text per leaf. Never infers goals.
Reads the source's CE/SE allocation table into `source.exam_allocation` and
sets `exam` on the (sub)domein units it names (01 §2 P4). No later role reads
`exam`; it is carried to the export unchanged.
Also runs `scripts/verb_table.py scan` on the PDF and, when the source defines
its own handelingswerkwoorden table, transcribes it to `01_verb_table.json`
(01 §2 step 2b). The file is a candidate; nothing uses it until the teacher
adopts it at the intake.

### 2.1b intake
See [06-subject-profiles.md](06-subject-profiles.md) §3. The only human checkpoint of the straat.
If `01_verb_table.json` exists and the subject has no `bloom_verbs.json` yet,
the intake runs `verb_table.py diff` and asks **one** question (impact high)
whether to adopt the source's table, listing the conflicts with the generic
table in the context (06 §7). After the pause the orchestrator installs an
adopted table and always writes `<run_dir>/bloom_verbs_effective.json`
(`verb_table.py effective`), the single verb table every later step reads.

### 2.2 planner
For every leaf unit decides:
- `n_groups` (1–4): one per distinct concept/skill bundled in the eindterm.
  Signals: multiple main verbs, enumerations, "en"/"of" joining concepts.
- `target_bloom_max`: highest level implied by the eindterm's own verbs
  (lookup in the effective verb table's `source_verb_hints`; ambiguous verbs
  resolved by context, resolution noted).
- `focus` per planned group: one line stating the concept/skill the group
  must address, so parallel generators do not overlap. When the unit (or its
  subdomein) carries a source concept list (01 §1 `concepts`), the foci
  together name every concept of that list, so pool coverage (02 §5) is
  designed in.
- `rationale`: one or two sentences, for the audit trail.

Output `02_plan.json`: `{ "units": [ { "unit_id", "target_bloom_max", "groups": [ { "slot": 1, "focus": "…" } ], "rationale": "…" } ] }`.
Validation: every leaf appears exactly once; slots ≥ 1; `target_bloom_max` is a valid level.

### 2.3 generator
Runs **once per parent of leaves** (a subdomein: all its specifications in
one call; parallel Agent calls, batched by the orchestrator, e.g. 4 at a time).
Working per subdomein keeps the groups of neighbouring specifications distinct
(rule J5) and consistent in terminology, at a fraction of the calls of
per-leaf generation. Input is only that subdomein: its global eindterm, its
leaves, their plan entries and the rule files. Output stays one file per leaf
(`03_groups_raw/<unit_id>.json`), so repair rounds can target a single leaf. It writes expert-language goal and criteria per
planned slot, with `bloom_verb` and `bloom` per criterion and the literal
`source_quote`. It does **not** write student language and does not set
`goal.bloom` (computed later).

Hard requirements it must satisfy before writing:
- Exactly the planned number of groups, `focus` honoured.
- 2–4 criteria per group; verbs from the list; no forbidden verbs.
- `source_quote` is a verbatim substring of the unit `text`.
- `concepts` per group (02 §5): 1–10 source terms from the unit's concept pool
  or verbatim from the unit/subdomein text (G8).

The orchestrator merges `03_groups_raw/*.json` into `03_groups_raw.json` and
runs `bloom_check.py --subject <s>` (verb-in-effective-table, forbidden verbs,
compute `goal.bloom`, alignment with `target_bloom_max` + 1). Without
`--subject` the script reads `subject` from the nearest `run.json`; without
either it uses the generic table.

### 2.4 student-language
Rewrites `text_expert` → `text_student` for all goals and criteria, per
02 §4. Works on the whole file (consistency of phrasing across groups
matters). Must not change `bloom`, `bloom_verb`, `concepts`, ids, or the number of
criteria. Validator: `student_language_check.py` (openers, forbidden verbs,
sentence length, forbidden phrases).

### 2.5 verifier
Launched with **no access to previous agents' transcripts** — it gets file
paths only. It first runs `scripts/coverage.py` and reads the result, then
judges each group against the rubric in 04-verification §3. For each group it
emits `verdict: pass | revise | reject`, `issues[]` with rule ids, and a
`suggested_fix` (one line). It also emits unit-level findings (uncovered
units, over-coverage, duplicate groups across units).

### 2.6 exporter
`scripts/export.py`: CSV + coverage report + doubt list. No model call.

## 3. Repair loop

```
round = 1
loop:
  verify → 05_verification.json
  if no group has verdict in {revise, reject} and no unit uncovered: break
  if round == 2: break            # max 2 repair rounds
  for each unit with uncovered status or any revise/reject group:
      re-run generator for that unit with the verifier's issues + suggested_fix appended
      (generator sees its previous output for that unit and the critique; nothing else)
  re-run student-language for changed groups only
  round += 1
export
```

Items still `revise`/`reject` after the loop, plus uncovered units, plus
ingest doubts, go to `output/doubt_list.md`. Nothing is deleted: rejected
groups stay in the CSV with `status = rejected` so the teacher sees them.

## 4. Configuration (`run.json`)

```json
{
  "run_id": "20261011-1100-economie-vwo",
  "input": "input/syllabus.pdf",
  "source_type": "syllabus",
  "max_repair_rounds": 2,
  "generator_batch_size": 4,
  "models": { "ingest": "sonnet", "planner": "opus", "generator": "opus", "student_language": "sonnet", "verifier": "opus" },
  "rounds_completed": 0,
  "status": "running"
}
```

## 5. Portability to a product (later)

What stays as-is when moving to the Agent SDK: `data/*.json`, `schemas/*.json`,
`scripts/*.py`, the role prompts (body of each `.claude/agents/*.md`), the
file contract per step. What is rewritten: the orchestrator (slash command →
service), tool wiring, storage (run folder → database/bucket), and the
Doelstellr import at the end of the exporter.
