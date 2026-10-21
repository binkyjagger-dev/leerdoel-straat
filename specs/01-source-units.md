# 01 — Source units

## 1. Source-agnostic model

Everything from the planner onwards works on a flat list of **source units**.
Hierarchy is expressed through `parent_id`, not through nested objects, so a
syllabus and a textbook look identical to downstream steps.

```json
{
  "source": {
    "source_id": "cvte-economie-vwo-2027",
    "source_type": "syllabus",            // "syllabus" | "textbook"
    "title": "Syllabus economie VWO centraal examen 2027",
    "subject": "economie",
    "level": "vwo",                        // informational only; no level-specific output
    "file": "input/syllabus.pdf",
    "ingested_at": "2026-10-11T10:00:00Z"
  },
  "units": [
    {
      "unit_id": "D",                      // stable within the run; human-readable
      "parent_id": null,
      "kind": "domein",                    // syllabus: domein | subdomein | eindterm
                                           // textbook: hoofdstuk | paragraaf | blok
      "code": "D",                         // code as printed in the source, if any
      "title": "Concept markt",
      "text": "",                          // literal source text; may be empty for containers
      "is_leaf": false,
      "page": 14
    },
    {
      "unit_id": "D1",
      "parent_id": "D",
      "kind": "subdomein",
      "code": "D1",
      "title": "Vraag en aanbod",
      "text": "",
      "is_leaf": false,
      "page": 14
    },
    {
      "unit_id": "D1.1",
      "parent_id": "D1",
      "kind": "eindterm",
      "code": "D1.1",
      "title": null,
      "text": "De kandidaat kan de werking van vraag en aanbod ... verklaren.",
      "is_leaf": true,
      "page": 14
    }
  ]
}
```

Rules
- `unit_id` is unique within the run and is the join key used everywhere
  downstream (plan, groups, coverage, CSV).
- **Leaf units** (`is_leaf: true`) are the units that must be covered. For a
  syllabus that is the *eindterm*; for a textbook the *paragraaf* (not the
  block — blocks are evidence, not coverage targets).
- `text` of a leaf is **literal**. The ingest agent may fix hyphenation and
  line breaks but must not paraphrase. Downstream steps quote from it.
- Container units carry title and code; their `text` may hold the
  introductory text of the domein if present.

## 2. Syllabus adapter (v1)

### Principles (decided 2026-10-11 on the economie VWO 2026 syllabus)

- **P1 — The leaf is the numbered specification.** CvTE syllabi state one
  global eindterm per subdomein ("De kandidaat kan analyseren welke invloed …")
  followed by numbered specifications (D1.1 … D1.24). Coverage is owed at the
  specification level: `kind: "eindterm"`, `unit_id` = `<subdomein><n>` as
  printed (e.g. `D1.8`). The subdomein unit carries the global eindterm in its
  `text`; its verb(s) give the planner the source-implied Bloom ceiling for all
  its leaves, refined by the specification's own wording.
- **P2 — Only content domains in CE scope.** Skills domains (domein A
  *Vaardigheden* and comparable "vaardigheden"/"onderzoek" domains) are not
  ingested as units. Skills are expressed through the Bloom levels and
  observable performances of the criteria, not as goals of their own. Domains
  that the syllabus marks as school-exam-only and does not specify are skipped
  as well. The ingest notes list every skipped domain.
  Appendices are not units either, with one exception: an appendix (or
  introduction section) that defines the syllabus's own **handelingswerkwoorden
  → Bloom level** table is extracted literally to `<run_dir>/01_verb_table.json`
  (schema `schemas/verb_table.schema.json`; see 02 §2 rule 6 and 06 §7). It is
  source material for a decision, not a unit.
- **P3 — Specification sub-items stay inside the leaf.** Roman-numeral or
  bullet sub-items under one specification (e.g. the four market forms under
  D2.1) remain in that leaf's `text`; the planner decides how many groups the
  leaf needs.

### Steps performed by the ingest agent

1. Extract text per page (`pdftotext -layout` or PyMuPDF; the agent uses whatever is available).
2. Locate the specification chapter ("Specificatie domeinen" or equivalent).
   Ignore front matter, toelichting and appendices unless they contain
   specifications.
2b. Run `scripts/verb_table.py scan <pdf>` (deterministic: pages mentioning
   *handelingswerkwoord*, *beheersingsniveau* or *taxonomie van Bloom*). If it
   finds a table that maps verbs to levels, transcribe it literally into
   `01_verb_table.json` (verbs lower-case, infinitive as printed; the source's
   own level labels in `level_labels`; its overarching verbs in `head_verbs`;
   page numbers) and run `verb_table.py validate` on it. If the scan finds
   nothing, write no file and say so in the notes.
3. Apply P2: select the content domains.
4. Build domein / subdomein / eindterm units using the printed codes (P1).
   Subdomein `text` = the global eindterm sentence(s). Leaf `text` = the
   specification text including sub-items (P3), literal.
5. Record the page number per unit.

Deterministic validation (`scripts/validate.py source_units`):
- schema valid;
- every `parent_id` exists; no cycles;
- every leaf has non-empty `text` (≥ 20 characters);
- at least one leaf exists;
- `unit_id` unique.

The agent also writes `01_ingest_notes.md`: what it skipped, anything it
was unsure about (e.g. an eindterm spread across a page break). Those notes
feed the final doubt list.

## 3. Textbook adapter (future, not built in v1)

Same output model. Planned mapping: hoofdstuk → paragraaf (leaf) → blok
(evidence). Expected extra work, kept out of v1:
- PDF/epub layout extraction and figure/box handling;
- paragraph boundaries from headings rather than printed codes;
- optional `related_unit_ids` on a textbook leaf pointing to syllabus
  eindtermen, so one run can produce goals linked to both. The schema already
  allows this field (nullable array) so adding it later does not break the
  pipeline.
