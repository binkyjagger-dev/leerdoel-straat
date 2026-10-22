# 11 — Method units

## 1. Model

Flat list, hierarchy by `parent_id`, same style as the syllabus source units.

```json
{
  "method": {
    "method_id": "lweo-economie-vwo-vraag-en-aanbod-2024",
    "subject": "economie",
    "publisher": "LWEO", "title": "Vraag en aanbod", "edition": "2024", "level": "vwo",
    "volume_order": 3,                      // position in the book order declared in the method profile
    "files": ["input/lesbrief-vraag-en-aanbod.pdf", "input/antwoorden-vraag-en-aanbod.pdf"],
    "text_extraction": "pdftotext|ocr",     // how text was obtained; ocr ⇒ quote matching is tolerant
    "ingested_at": "2026-10-23T09:00:00Z"
  },
  "units": [
    {"unit_id": "H1",     "parent_id": null, "kind": "hoofdstuk", "code": "1",   "title": "Vraag",            "page_from": 5,  "page_to": 18},
    {"unit_id": "H1.2",   "parent_id": "H1", "kind": "paragraaf", "code": "1.2", "title": "Betalingsbereidheid", "page_from": 8, "page_to": 10,
     "order": 2,                              // reading order across the whole method (volume_order, chapter, paragraph)
     "concepts": ["betalingsbereidheid", "individuele vraaglijn"],   // bold terms / margin terms as printed
     "text_ref": "text/H1.2.txt"},            // run-local only; never exported
    {"unit_id": "H1.2-opg7",   "parent_id": "H1.2",      "kind": "opgave",   "code": "7",  "page_from": 10},
    {"unit_id": "H1.2-opg7b",  "parent_id": "H1.2-opg7", "kind": "deelvraag","code": "7b", "page_from": 10,
     "text_ref": "text/H1.2-opg7b.txt", "answer_ref": "text/H1.2-opg7b.answer.txt"}
  ]
}
```

Rules
- `paragraaf` is the linking unit for part A; `deelvraag` for part B. Chapters
  are containers. Kaders/boxes stay inside the paragraph text.
- `order` is a global integer: book order declared in the method profile
  (volume order) × chapter × paragraph. The gradation script sorts on it.
- `concepts`: terms the method itself marks (bold, margin, "begrippen" list).
  First retrieval key for candidates, next to the criterion's own `concepts`.
- Text lives under `runs/<run>/text/` and is git-ignored. Exported artefacts
  carry only ids, codes, titles, page numbers and quotes ≤ 25 words.
- Exercises without a sub-question get one synthetic `deelvraag` with code
  equal to the exercise code, so part B always links at the same level.

## 2. Ingest adapters

### 2.1 LWEO lesbrief (v1)

- PDF may be image-based: run `pdftotext`; if a page yields < 50 characters,
  rasterise and OCR it (Tesseract `nld`); record `text_extraction: "ocr"` and
  the OCR pages in the notes.
- Structure: chapter headings ("Hoofdstuk 1 …"), paragraph headings ("1.2 …"),
  exercises numbered per chapter ("Opgave 7", sub-questions "a", "b", …).
  Exercises sit inside paragraphs in LWEO; the adapter attaches each exercise
  to the paragraph it appears in.
- Answer PDF (separate): parse "Opgave 7 … a … b …" and attach `answer_ref`
  per sub-question. Missing answers are allowed.
- Notes list: OCR pages, exercises that could not be attached to a paragraph,
  headings that did not parse.

### 2.2 Other methods (later)

Same model; new adapter per publisher layout. Separate workbooks become a
second file with `kind: opgave/deelvraag` units attached to paragraphs by the
workbook's own references ("bij §2.3").

## 3. Method profile

`subjects/<subject>/methodes/<method_id>/profile.md` (human), suggested headings:
*Boekvolgorde* (volumes and years, which decides `order`), *Opbouw* (where
exercises live, how boxes are used), *Terminologie* (method-specific terms vs
syllabus terms), *Niet koppelen* (chapters out of scope). Read by every role;
never written by the straat. Subject-level `profile.md` and `decisions.json`
still apply.

## 4. Validation (`scripts/mapping/validate_method.py`)

- schema; unique ids; parents exist; `order` strictly increasing over
  paragraphs in one method; every paragraph has `text_ref` and the file
  exists (run-local); every `deelvraag` has `text_ref`; page ranges sane.
