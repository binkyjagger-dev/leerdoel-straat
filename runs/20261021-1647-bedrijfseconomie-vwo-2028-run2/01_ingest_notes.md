# Ingest notes (run 2, corrections 1 and 2 in force)

Units, unit_ids, leaf choices and skipped domains are identical to the previous run (notes below, carried over). All 79 unit texts were re-checked against the PDF with the tracked-changes geometry (01_tracked_changes_detector.py, output in 01_tracked_changes.txt; 01_clean_pages.txt = pages 12-31 with struck characters removed). Only difference with the previous texts: none.

## New in this run
- Verb table: scan found pp 2, 5, 6, 37; p37 (Bijlage 3) has the table. Transcribed to 01_verb_table.json (pages [37]); validated. P5 (explanation of the scheme) not part of the table. Note: 'vormgeven vragen formuleren' is printed without a comma; read as two verbs.
- Exam allocation (table p7) copied completely: 16 rows (A, B1-B4, C1, C2, D1, D2, E1, E2, E3, F1, F2, G, H). Printed: A, B1-B4 = CE+SE; C1, D1, E1, E3, H = SE only; C2, D2, E2, F1, F2, G = CE only.  exam set on subdomeinen B1-B4 (CE+SE), C2, D2, E2, F1, F2 (CE) and domein G (CE). Domein titles in the table: F "Financieel beheer" (units use the chapter title "Financieel beleid"). Not ingested (ingested: false): A, C1, D1, E1, E3, H. Leaves: 11 CE+SE, 53 CE.
- Concepts: 16 units carry concepts (446 bullets in total). The PDF prints them in a table (heading cell 'Belangrijkste begrippen' / 'Belangrijke begrippen' on p27 and p29, bullets in cells, some with sub-bullets). Every bullet and sub-bullet is one string, in reading order, literal, duplicates within a block kept (e.g. 'nominale waarde' twice in D2). Struck bullet dropped: 'carrièreperspectief' (p19, leaving an empty bullet). Added (highlighted) bullets kept: depositogarantiestelsel, bruto uitgaven, netto uitgaven, Full Time Equivalent / FTE, promotie (p19), bruto dividend, netto dividend. Struck 'wijzen' in the first bullet of 20.1: 'financieringsmogelijkheden'.
  - Attached to a leaf (9 blocks, 111 bullets): B1.11.2 (24), B1.11.3 (17), B1.11.4 (22; starts p13, continues p14), B2.12.2 (14), B2.12.3 (3), B3.13.1 (22), D2.20.1 (6), D2.22.2 (6), F1.29.2 (11).
  - NOT attributable to one specification (7 blocks, 335 bullets): the block is printed after the last specification of an eindterm (or subdomein) but its terms cover several specifications of it. Attached to the subdomein (G: domein, it has no subdomein), per the P5 fallback: B4 (15; follows 14.3 but covers 14.2 and 14.3), C2 (56; follows 17.10, covers all of 17.1-17.10, p18-19), D2 (41 = block after 20.2.5 [19, covers 20.2.1-20.2.5, which are separate leaves] + block after 21.10 [22, covers 21.1-21.10], in that order), E2 (53; follows 25.6, p23-24), F1 (31; follows 28.4, covers 28.1-28.4), F2 (48 = block after 30.6.2 [21, p27-28] + block after 31.2.1 [27, p29]), G (77; follows 32.5, p30-31). Judgement call by me: if you want the strict 'block belongs to the specification directly above', move these to B4.14.3, C2.17.10, D2.20.2.5, D2.21.10, E2.25.6, F1.28.4, F2.30.6.2 / F2.31.2.1, G.32.5. I attached to a leaf only where the block's first terms repeat that leaf's own text (22.2, 29.2) or the leaf is the whole specification the block follows (11.2, 11.3, 11.4, 12.2, 12.3, 13.1, 20.1).
  - No list printed for: B1.11.1, B2.12.1, B4.14.1/14.2, C2.17.1-17.9 (own), D2.21.x (own), E2.25.1-25.5, F1.28.1-28.3, F1.29.1, F2.30.1-30.5, F2.31.1-31.2, G.32.1-32.4 (own). 11.1 has no block.
  - Literal oddities kept: 'explotatiebegroting' (p25), 'liquiditatiewaarde' (p29), 'lening overige vermogensverschaffers,' (trailing comma, p20), 'aandelenkapitaal, reserves en resultaat lopende boekjaar(bij bv en nv)', 'bestuurverslag', 'solvabiliteitsratio's' etc. The G table has an unbulleted left-hand cell 'eigen vermogen' (before 'eigen vermogen (bij eenmanszaak)'); included as its own string, as is 'te vorderen btw' (sub-bullet of 'liquide middelen'). In G the first word of the sub-block 'immateriële vaste activa:' is flagged by the strike detector on its first letter ('i'); the render shows an ordinary word (detector false positive), kept as 'immateriële vaste activa:'.
  - B1.11.2: B1 CE sentence: the dangling ')' after the struck '(korte en lange termijn' is dropped (as in the previous run).

# Carried over from previous run

## Skipped (P2)
- Domein A Vaardigheden (p9-11, subdomeinen A1, A5, A6; eindtermen 1, 5-10): skills domain, not ingested.
- Domein H Keuze-onderwerpen: school exam only, no specification in the syllabus.
- Subdomeinen outside the CE (table p7): C1 Interne organisatie, D1 Investeren, E1 Doel en organisatie van marketingactiviteiten, E3 Marketing vanuit het perspectief van de consument en de samenleving. Only their domein intro sentences appear (C, D, E intro text mentions them). No eindterm numbers 15-16, 18-19, 23-24, 26-27 exist in the PDF.
- Front matter, hoofdstuk 1, 4 and bijlagen 1-4 (bijlage 3 handelingswerkwoorden, bijlage 4 formules) not ingested.

## Structure choices
- The syllabus prints global eindtermen as plain numbers (11, 12, ... 32) and specifications as 11.1, 11.2 ... with sub-items 11.2.1 ... No letter prefix is printed, so `unit_id` = subdomein code + printed number: `B1.11.2`, `F2.30.4`, `G.32.1`. `code` is the printed number (`11.2`).
- Leaf = the two-level specification (11.2); its three-level sub-items (11.2.1 ...) stay in `text` (P3). Exception D2 eindterm 20: the printed specifications have no sub-items (20.1, 20.2.1-20.2.5), so those are the leaves.
- Leaf `text` starts at the printed verb phrase (the lead-in "In dat verband kan de kandidaat" is not repeated; it sits implicitly in the subdomein text).
- Subdomeinen with several global eindtermen (D2: 20, 21, 22; F1: 28, 29; F2: 30, 31) carry all of them in `text`, each with its "Voor het centraal examen betekent dit" clarification. F2 has no CE clarification printed for 30 and 31.
- Domein G has no subdomein; eindterm 32 and its CE clarification are in the domein `text`, specifications hang directly under G.
- Footnote 1 in 30.5 is rendered as "(1)" and its text appended to the leaf.

## Tracked changes in the PDF (resolved)
The PDF shows added text (yellow) and deleted text (strikethrough). Struck text was identified by geometry (thin strike rectangles over characters, found by script and checked against page images) and dropped from all unit texts; everything else is kept. Resolved changes:
- B1 CE sentence: struck "uitleggen en berekenen (korte en lange termijn"; kept "onderbouwen".
- B1 11.4.4: struck comma after "schenkovereenkomst".
- B3 13.1: leading "in" struck.
- C2 17.3: "noemen" struck.
- D2 20.1: printed number is "20.1" (trailing ".1" struck); leaf is `D2.20.1`. 20.1: "financieringswijzen" -> "financieringsmogelijkheden" ("wijzen" struck).
- D2 21 CE sentence: "redenen" struck; kept "de keuze voor een financieringsmogelijkheid".
- D2 21.2 and 21.8: "het onderscheid" struck.
- D2 21.9: "en disagio" struck.
- F1 29 CE sentence: the tail "het noemen van financiële en niet-financiële informatie en het belang ervan uitleggen voor het besturen van een organisatie." struck; text ends "... om het functioneren van een organisatie uitleggen."
- F2 30.6.2: "systeem" struck (text reads "afschrijvingsperiode en", grammar off, kept literally).
- G 32.1: "winst- en verlies" struck.
- G 32.4: struck: parentheses around "kengetallen van", "winst- en verlies", "financiële structuur". Repair by me: the dangling comma left by the struck phrase was dropped ("op het terrein van liquiditeit, solvabiliteit, ...").
- G "32.85": the "8" is struck, so 32.5.
- Struck text in skipped domein A (eindterm 10) and in begrippen lists is irrelevant.

## Other uncertainties
- B4 eindterm 14: the labels 14.2 and 14.3 are misplaced in the layout. The sentence on MVO ("de betekenis van maatschappelijk verantwoord ondernemen (MVO) ...") has no printed number; I kept it inside 14.2 after 14.2.1. "het concept true pricing uitleggen" carries the printed number 14.3.
- B4: the "In dat verband kan de kandidaat" lead-in is at the bottom of p16, the specifications start on p17.
- B1 11.2: the printed text is capitalised ("Analyseren van ...") and has no verb phrase of its own; sub-items 11.2.1-11.2.12 carry the performances.
- F2 30.6: the head has no text of its own; both sub-items start with "de kandidaat kan" and end with remnants "(31.1.4 oude versie)" / "(31.1.5 oude versie)", kept literally.
- F2 30.2.1 and 30.4.2 / 30.4.3 contain "kunnen" in the printed text ("grafisch kunnen opstellen"); kept literally.
- D2 20-2 CE sentence says "kan begrijpen" (printed).
- Domein F title: the contents page says "Financieel beleid", the table p7 says "Financieel beheer". Used "Financieel beleid" (the chapter heading).
- Eindterm numbering has gaps by design (CE scope): 11-14, 17, 20-22, 25, 28-32.
- Page numbers are the printed "Pagina x van 41" numbers, which equal the PDF page numbers.

## Concept corrections (bedrijfsecon-019)
`source.concept_corrections` maps printed bullet to corrected text (7 entries); the `concepts` arrays stay literal. All 446 concepts scanned; no others found (REV, RTV, IVV and bracketed abbreviations are legitimate).
- "explotatiebegroting" -> "exploitatiebegroting"
- "liquiditatiewaarde" -> "liquidatiewaarde"
- "bestuurverslag" -> "bestuursverslag"
- "lening overige vermogensverschaffers," -> without trailing comma
- "immateriële vaste activa:" -> without trailing colon
- "financiële vaste activa:" -> without trailing colon
- "constante/variabele Kosten" -> "constante/variabele kosten"
