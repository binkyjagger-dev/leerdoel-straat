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
    "files": ["input/lesbrief-vraag-en-aanbod.pdf", "input/antwoorden-vraag-en-aanbod.pdf"],   // or input/book/ (image folder), input/<workbook>.docx
    "text_extraction": "pdftotext|ocr|mixed",  // how text was obtained; ocr/mixed ⇒ quote matching is tolerant (image transcription counts as ocr)
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

### 2.2 Page images + separate workbook (v2)

For methods delivered as photos/scans of pages and a separate exercise file
(first case: Bedrijfseconomie in Balans, H16–H20, photos + a school
opgavenbundel in .docx + answers PDF). The layout comes from the method
profile (*Opbouw*), not from the adapter.

- **Book = folder of images** (jpg/jpeg/png/tif). Page order = natural filename
  order; when the profile says the filenames encode chapter/paragraph (e.g.
  `H16_16.1_2.jpg`), that is a structure hint, the printed headings decide.
  `scripts/mapping/ocr_images.py <dir> <out>` writes a Tesseract draft per
  page plus `pages.json` (page → file). Photos have skew and show-through, so
  the ingest agent reads **every** image itself and overwrites
  `page-NNN.txt` with its transcription of the running text; the draft is a
  reading aid. Judges quote from these text files, so the transcription is
  literal (no paraphrase, no summary); illegible words become `[?]`.
  `text_extraction: "ocr"` (quote matching stays tolerant). `page_from`/
  `page_to` = the printed page number when visible, else the image index;
  the notes say which.
  Long image sets are transcribed by several ingest agents in parallel
  (≤ 15 pages each, *transcribe-only*); each finished page gets a
  `page-NNN.done` marker so the structuring agent skips it.
- **Margin terms** (begrippen in the margin) are the paragraph's `concepts`.
  A paragraph's own goal box ("Je kunt …") stays in the text file under a
  line `[Leerdoelen van de methode]` so judges can tell it from explanation.
- **Workbook = .docx or PDF.** `.docx` goes through
  `scripts/mapping/docx_text.py <file> <out>` → `document.txt` with Word's
  automatic list numbering resolved (sub-question letters are numbering, not
  text) and embedded images extracted to `media/`, marked inline as
  `[afbeelding: media/…]`. A PDF workbook goes through `ocr_pdf.py`.
- **Attachment by reference.** An exercise is attached to the paragraph its
  heading names (`16-1 (§ 16.1)`, "bij §2.3"); exercises without a reference
  (start/intro/review tasks) are not units unless the profile or a decision
  says where they belong — list them in the notes. Exercise codes as printed
  (`16-1`), sub-questions `16-1a`; ids `H16.1-opg16-1`, `H16.1-opg16-1a`.
- **Pictures in the workbook.** An image that carries content the question
  needs (a table, a balance sheet pasted as a picture) is transcribed into the
  sub-question's text file (`[tabel uit afbeelding] …`); icons (level markers
  etc.) are described in the notes only, with their meaning if the workbook
  explains it.
- **Answers**: same as §2.1, matched on exercise code + letter.
- Planning material in the workbook (periodeplan, leerdoelen, lesson
  schedule) is not a unit; discrepancies between it and the book (paragraph
  numbers that do not exist in the images) go to the notes for the intake.

### 2.3 Other methods (later)

Same model; describe the layout in the method profile and reuse §2.1/§2.2
where possible; a new adapter only for a layout neither covers.

## 3. Method profile

`subjects/<subject>/methodes/<method_id>/profile.md` (human), suggested headings:
*Boekvolgorde* (volumes and years, which decides `order`), *Opbouw* (files
and their format, where exercises live and how they refer to paragraphs, how
boxes are used), *Terminologie* (method-specific terms vs
syllabus terms), *Niet koppelen* (chapters out of scope). Read by every role;
never written by the straat. Subject-level `profile.md` and `decisions.json`
still apply.

## 4. Validation (`scripts/mapping/validate_method.py`)

- schema; unique ids; parents exist; `order` strictly increasing over
  paragraphs in one method; every paragraph has `text_ref` and the file
  exists (run-local); every `deelvraag` has `text_ref`; page ranges sane.
