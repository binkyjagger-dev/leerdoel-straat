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
    "ingested_at": "2026-10-11T10:00:00Z",
    "exam_allocation": [                   // the source's CE/SE table, complete (P4); null if the source has none
      { "code": "D1", "title": "Vraag en aanbod", "in_ce": true, "must_in_se": false, "ingested": true },
      { "code": "C1", "title": "Interne organisatie", "in_ce": false, "must_in_se": true, "ingested": false }
    ]
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
      "page": 14,
      "exam": "CE"                         // "CE" | "SE" | "CE+SE" (P4); set where the source's table assigns it,
                                           // inherited by descendants; null/absent elsewhere
    },
    {
      "unit_id": "D1.1",
      "parent_id": "D1",
      "kind": "eindterm",
      "code": "D1.1",
      "title": null,
      "text": "De kandidaat kan de werking van vraag en aanbod ... verklaren.",
      "is_leaf": true,
      "page": 14,
      "concepts": ["vraag", "aanbod", "evenwichtsprijs"]   // literal terms from the source's concept list
                                                           // printed for this unit (P5); null if the source prints none
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
- `exam` (decided 2026-10-21, correction 1 of run 3) records whether a unit's
  content belongs to the central exam, the school exam, or both: `"CE"`,
  `"SE"`, `"CE+SE"`. It is set on the unit the source's allocation table names
  (a subdomein, or a domein without subdomeinen) and **inherited** by every
  descendant: `common.exam_for(unit)` walks up `parent_id` to the nearest
  ancestor with a value. Leaves therefore need no copy. It is **metadata
  only**: planner, generator, student-language and verifier ignore it; it
  travels to the groups' export (05 §1 column `examen`) and the coverage
  report. `source.exam_allocation` holds the source's complete table, including
  rows the ingest did not turn into units, so the report can say what the
  source leaves to the school exam.
- `concepts` (decided 2026-10-21, correction 2 of run 3): the **literal** terms
  of the concept list the source prints for this unit ("Belangrijkste
  begrippen" in CvTE bedrijfseconomie), one string per printed bullet, spelling
  as printed, no additions. Attached at the level the source prints them: a
  block that follows a specification → on that leaf; a block printed for a
  whole subdomein, or one that cannot be attributed → on the subdomein. `null` when the source
  prints no list for that unit. These lists are coverage targets (04 §1 C3)
  and the pool the generator draws from (02 §5).

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
- **P5 — Concept lists are source data (decided 2026-10-21).** Where the
  syllabus prints a list of key concepts next to a specification or
  subdomein, the ingest copies it literally into that unit's `concepts`. In
  CvTE bedrijfseconomie the block "Belangrijkste begrippen" is printed
  directly **below** a specification and its sub-items, before the next
  specification starts (it may run over a page break): the list belongs to the
  specification it follows. A list that cannot be attributed to one
  specification goes on the subdomein with a note. Nothing
  is paraphrased, merged, singularised or de-duplicated across units. A source
  without concept lists (economie) has no `concepts` fields; the concepts of
  its goals are then taken from the eindterm text itself (02 §5).
- **P4 — Exam allocation is recorded, not interpreted (decided 2026-10-21).**
  CvTE syllabi open with a table "Toedeling van de examenstof … aan centraal
  examen en schoolexamen" with, per (sub)domein, the columns *in CE* and *moet
  in SE*. The ingest copies that table **completely** to
  `source.exam_allocation` (one row per printed (sub)domein, `ingested: true`
  for rows that became units) and sets `exam` on the matching unit: both
  columns marked → `"CE+SE"`, only *in CE* → `"CE"`, only *moet in SE* →
  `"SE"`. Only the table counts: the sentence that a school *may* also test CE
  content in the SE is not recorded (that is the school's choice, not the
  source's). SE-only (sub)domeinen keep P2: they have no specifications in a
  CE syllabus and are not ingested; they appear in `exam_allocation` with
  `ingested: false` and in the coverage report under *Niet in deze bron*. A
  source without such a table sets `exam_allocation: null` and no `exam`
  fields; downstream treats that as "unknown", never as CE.

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
2c. Collect the source's concept lists (P5): every "Belangrijkste begrippen"
   block, attached to the specification it follows (also across a page
   break), else to the subdomein. Record in the notes how many lists were
   attached per level and which could not be attributed.
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
- `unit_id` unique;
- S3 (P4): when `source.exam_allocation` is present, every leaf resolves to an
  `exam` value through its ancestors, and every allocation row with
  `ingested: true` matches a unit `code`; when it is absent, no unit carries
  `exam` (info: "exam allocation unknown").

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
