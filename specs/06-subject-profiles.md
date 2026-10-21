# 06 — Subject profiles and the intake step

**Decided 2026-10-11:** the straat stays autonomous except for **one** human
checkpoint, the intake (option A). The straat writes only to `decisions.json`;
`profile.md` is written by humans.

## 1. Why

Every subject has conventions, scope choices and interpretations that a
generic pipeline cannot know and should not guess twice: which term to use
(*moral hazard* vs *moreel risico*), how to read an ambiguous syllabus phrase,
what "normaal goed" means in this school's textbook, whether the domain verb or
the subdomain lead-in sets the Bloom ceiling. Run 1 surfaced six such questions
in the doubt list, after the fact. The intake step surfaces them **before**
generation and records the answers so later runs don't ask again.

## 2. Files

```
subjects/<subject>/
  profile.md        human-written context, read by every agent (free text)
  decisions.json    straat-written record of intake questions and answers
  bloom_verbs.json  optional, straat-written (verb_table.py install): the subject's
                    verb → Bloom table adopted from the source, overrides the generic table (§7)
  glossary.json     optional: preferred terms and forbidden synonyms
```

`<subject>` is a slug (`economie`, `bedrijfseconomie`, `wiskunde-a`). A run is
tied to one subject via `--subject` (default: the `subject` field of the
source metadata, lower-cased).

### 2.1 `profile.md` (human)

Free-form Markdown, written by the teacher before the first run. Suggested
headings: *Scope* (levels, exam programme, what to skip), *Methode* (textbook
and its conventions), *Terminologie* (preferred terms), *Afspraken* (school or
section agreements on interpretation), *Niet doen*. Agents receive its path and
read it; it is never modified by the straat. Anything the straat learns goes to
`decisions.json`, and the human may later fold it into `profile.md`.

### 2.2 `decisions.json` (straat)

```json
{
  "subject": "economie",
  "decisions": [
    {
      "id": "econ-001",
      "question": "Telt het domeinwerkwoord 'analyseren' mee als Bloom-plafond, of alleen de subdomein-aanhef 'herkennen en toepassen'?",
      "context": "Alle domeinen D–I zeggen 'analyseren'; 19 van 21 subdomeinen zeggen 'herkennen en toepassen'. Raakt target_bloom_max van ~120 eenheden.",
      "options": ["subdomein-aanhef (plafond toepassen)", "domeinwerkwoord (plafond analyseren)"],
      "proposed": "subdomein-aanhef (plafond toepassen)",
      "impact": "high",
      "applies_to": ["planner"],
      "affects_units": ["*"],
      "status": "open",
      "answer": null,
      "answered_by": null,
      "answered_at": null,
      "source_run": "20261011-1150-economie-vwo-2026",
      "raised_by": "verifier"
    }
  ]
}
```

Fields: `status` ∈ `open | answered | superseded`; `impact` ∈ `high | medium | low`;
`applies_to` lists the roles that must read the answer; `affects_units` lists
unit ids or `["*"]`; `raised_by` ∈ `intake | verifier | ingest | human`.
Schema: `schemas/decisions.schema.json`. Decisions are append-only; a changed
answer supersedes the old decision (new id, old `status: superseded`).

## 3. The intake step (1b)

Position: after ingest, before planner. Role `intake` (fresh context).

Inputs: `01_source_units.json`, `01_ingest_notes.md`, `subjects/<subject>/profile.md`,
`subjects/<subject>/decisions.json`.

What it does:
1. Reads the source units and the profile. Lists **ambiguities and
   subject-specific observations that change the output**: Bloom-ceiling
   interpretation, ambiguous or possibly erroneous source text, specifications
   that are only a heading, terms with competing definitions, overlaps between
   units that need a scope decision, anything the profile is silent on but the
   generator will need.
2. Drops every question that `decisions.json` already answers (same meaning,
   not just same wording) and every question `profile.md` already settles.
3. Writes `<run_dir>/01b_intake_questions.json` (schema
   `schemas/intake_questions.schema.json`): each question with context,
   options, a proposed default, impact and the roles it applies to. Target:
   the questions that matter, typically 3–10; never a question per unit.

The orchestrator then **pauses** (option A):
- Shows the questions to the user (AskUserQuestion when available, otherwise a
  numbered list in the terminal; options plus free text).
- Writes every answer to `subjects/<subject>/decisions.json` with
  `status: answered`, `answered_by`, `answered_at`, `source_run`.
- Unanswered questions (user skips, or no user present in a headless run) are
  written with `status: open` and `answer: <proposed>`; the run continues on
  the proposed default and the doubt list marks the affected groups
  *"provisional: decision econ-00x open"*.
- Then continues to the planner. No other checkpoint exists.

## 4. How agents use the profile and decisions

Every role prompt gets two extra lines in its input: the profile path and the
decisions path. Rules:
- Decisions with `status: answered` are **binding** for the roles in `applies_to`.
  A generator that deviates must say so in `generator_notes`; the verifier
  treats a deviation from an answered decision as a J1 failure.
- `profile.md` is context, read in full; where it conflicts with a decision,
  the decision wins (it is more specific and dated).
- The verifier may **raise** new decisions: in `05_verification.roundN.json`
  a `proposed_decisions[]` list (same shape as intake questions). The
  orchestrator appends them to `decisions.json` with `status: open` after the
  run; they are presented at the next run's intake. The verifier never answers
  them.
- Nothing in the straat writes `profile.md`. Only `scripts/decisions.py`
  writes `decisions.json` and only `scripts/verb_table.py install` writes
  `bloom_verbs.json`, and the latter only against an *answered* decision.

## 5. Orchestration changes

`/generate <pdf> [--subject <slug>] [--run-id <id>]`
- `--subject` resolves `subjects/<slug>/`; if the folder does not exist, the
  orchestrator creates it with an empty `decisions.json` and a `profile.md`
  template, and tells the user to fill the profile (the run continues).
- Step 1b inserted; `run.json` gets `subject` and `decisions_snapshot` (the
  decision ids and answers used in this run, for reproducibility).
- Export: `coverage_report.md` lists the decisions applied; `doubt_list.md`
  lists open decisions and the groups they affect.

## 6. Backfill from run 1

The six questions run 1 raised in its doubt list are entered in
`subjects/economie/decisions.json` with `status: open`, `raised_by: verifier`,
`source_run: 20261011-1150-economie-vwo-2026`, so Martijn can answer them in
one pass and run 2 starts from settled ground.

## 7. Subject verb table (decided 2026-10-21)

**Why.** Run 3 (bedrijfseconomie VWO 2028) showed that the verb → Bloom table
is subject-bound: the CvTE syllabus carries its own table (*Bijlage 3*) that
puts "opstellen" at toepassen and "indelen"/"vergelijken" at analyseren, where
`data/bloom_verbs_nl.json` says creëren and begrijpen. Economie's syllabus has
no such table. Decision bedrijfsecon-002 ("pas bijlage 3 toe") could not be
executed because `bloom_check.py` G3 only knew the generic table. Rule: 02 §2
rule 6.

**How the straat finds out whether a subject table is needed** — three steps,
each in an existing role, no new checkpoint:

1. **Ingest detects and transcribes.** `scripts/verb_table.py scan <pdf>`
   reports the pages that mention *handelingswerkwoord*, *beheersingsniveau*
   or *taxonomie van Bloom*. If those pages hold a table mapping verbs to
   levels, the ingest agent transcribes it **literally** to
   `<run_dir>/01_verb_table.json` (schema `schemas/verb_table.schema.json`) and
   validates it (`verb_table.py validate`). No table → no file; the notes say
   so. The file is a candidate: nothing reads it yet.
2. **Intake compares and asks.** If `01_verb_table.json` exists and
   `subjects/<subject>/bloom_verbs.json` does not, the intake runs
   `verb_table.py diff <run_dir>/01_verb_table.json --subject <subject>` and
   puts **one** question in `01b_intake_questions.json`, key
   `handelingswerkwoorden-tabel`, impact `high`, `affects_units: ["*"]`,
   `applies_to: ["planner", "generator", "verifier"]`: adopt the source's table
   (proposed), keep the generic table, or adopt it with named exceptions. The
   context lists the conflicts the diff found (verb, source level, generic
   level). If the subject already has a table, the intake lists the question
   under `skipped_as_already_decided`.
3. **Orchestrator installs, after the answer.** When the decision is answered
   with adoption, the orchestrator runs
   `verb_table.py install <subject> <run_dir>/01_verb_table.json --decision <id>`,
   which refuses unless that decision is `answered` and refuses to overwrite an
   existing table without `--force`. Exceptions named in the answer are applied
   by the orchestrator as `--drop <verb>` (the verb keeps its generic level).
   Then, always: `verb_table.py effective <subject> --out <run_dir>/bloom_verbs_effective.json`.
   Every later role reads that file; `bloom_check.py` recomputes the same merge
   from `--subject`.

**Merge semantics** (`verb_table.py effective`, `common.load_bloom_rules`):
generic table first; every verb in the subject table is removed from all
generic levels and from `ambiguous`, then placed at its subject level
(two subject levels → ambiguous between them); `source_verb_hints` gets the
subject level for those verbs; `forbidden_criterion_verbs_extra` is appended;
everything else stays generic. The effective file records the overrides under
`_effective.overrides` so a reader can see what changed and why
(`_effective.decision`).

**Later runs of the same subject** skip steps 2 and 3: the decision is answered
and the table is installed. A new syllabus version with a changed table shows
up as a diff against the installed table; the intake then asks again (new
decision, old one superseded).

**Backfill for bedrijfseconomie.** Bijlage 3 of the 2028 v2 syllabus is
transcribed to the run's `01_verb_table.json` and installed against
bedrijfsecon-002 (answered 2026-10-21). The bedrijfseconomie run of 2026-10-13
predates this and must be regenerated to honour it.
