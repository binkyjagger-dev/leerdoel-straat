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

Input: a text-based PDF from CvTE. Steps performed by the ingest agent:

1. Extract text per page (`pdftotext -layout` or PyMuPDF; the agent uses whatever is available).
2. Locate the specification section ("Specificatie van de globale eindtermen"
   or equivalent). Ignore front matter, toelichting and appendices unless they
   contain eindtermen.
3. Build domein / subdomein / eindterm units using the printed codes. If the
   syllabus numbers eindtermen only within a subdomein, compose
   `unit_id` as `<subdomein>.<n>`.
4. Where a subdomein lists bullet-level specifications under one eindterm,
   keep them inside the eindterm's `text` (one eindterm = one leaf). Do not
   split bullets into separate leaves; the planner decides how many groups a
   leaf needs.
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
