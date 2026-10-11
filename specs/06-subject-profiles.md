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
- Nothing in the straat writes `profile.md`.

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
