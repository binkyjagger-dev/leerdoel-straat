# Ingest notes

## Skipped (P2)
- Domein A Vaardigheden (p9-11, subdomeinen A1, A5, A6; eindtermen 1, 5-10): skills domain, not ingested.
- Domein H Keuze-onderwerpen: school exam only, no specification in the syllabus.
- Subdomeinen outside the CE (table p7): C1 Interne organisatie, D1 Investeren, E1 Doel en organisatie van marketingactiviteiten, E3 Marketing vanuit het perspectief van de consument en de samenleving. Only their domein intro sentences appear (C, D, E intro text mentions them). No eindterm numbers 15-16, 18-19, 23-24, 26-27 exist in the PDF.
- Front matter, hoofdstuk 1, 4 and bijlagen 1-4 (bijlage 3 handelingswerkwoorden, bijlage 4 formules) not ingested.
- "Belangrijkste begrippen" lists (two-column layout, cannot be reliably attached to one specification) are not in any unit text.

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
