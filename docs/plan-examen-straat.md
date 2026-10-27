# Plan van aanpak — examen-straat (`/examen`)

**Status:** vastgesteld 2026-10-27 · **Eigenaar:** Martijn · **Specs:** [20–25](../specs/20-examen-overview.md)

## 1. Doel

Een derde straat in deze repo. Je leest één of meer centrale examens van een vak in
(opgavenboekje, correctievoorschrift, informatieboekje). De straat koppelt elk
**scorepunt** uit het correctievoorschrift aan één succescriterium uit een `/generate`-run,
met Bloom-niveau en een letterlijk citaat. De koppelingen komen in een **examenbank per
vak** die je steeds kunt aanvullen met nieuwe examens.

Opbrengst:
- een overzicht van de punten per examen per succescriterium, leerdoel, subdomein en
  domein (absoluut en als % van de maximumscore);
- een opzoekindex: welke vraag (examen, opgave, vraagnummer, scorepunt) toetst
  criterium X, met citaat en Bloom-niveau.

## 2. Beslissingen (2026-10-27, door Martijn)

| # | Onderwerp | Besluit |
|---|---|---|
| 1 | Puntverdeling | Per **scorepunt** (•) uit het correctievoorschrift; elk scorepunt aan precies één criterium. |
| 2 | Oudere examens | Altijd koppelen aan de huidige criteria; stof die niet (meer) in de syllabus staat wordt gemarkeerd als *buiten huidige syllabus*. Examenjaar en syllabusversie staan bij elk examen. |
| 3 | Nieuwe criteria | De bank hoort bij **één criteriaversie** (één `/generate`-run). Nieuwe criteria ⇒ nieuwe bank: examens opnieuw inlezen (script), alleen de rechters draaien opnieuw. |
| 4 | Opzoeken | Excel/CSV + Markdown. |
| 5 | Bloom | Ja: per scorepunt het niveau dat het examen vraagt; bevinding als het examen hoger of lager toetst dan het criterium. |
| 6 | Controle | Zoals `/koppel`: twee onafhankelijke rechters (A, B), verse verifier, één reparatieronde, zekerheid per koppeling. |
| 7 | Dubbel geraakt | Eén criterium per scorepunt; een tweede geraakt criterium als *raakt ook*, zonder punten. Punten tellen exact op. |
| 8 | Vraagtekst in index | Verwijzing + citaat ≤ 25 woorden. Volledige examentekst blijft in de run (git-ignored). |
| 9 | Toevoegen | Meerdere examens per run, alle intakevragen in één pauze; later losse examens bijvoegen. |
| 10 | Bankplek | `subjects/<vak>/examenbank/`, in git. |
| 11 | Cijfers | Punten per examen en aandeel (%) van de maximumscore, per criterium, leerdoel, subdomein en domein. (Totaal/gemiddelde/frequentie: niet gekozen.) |
| 12 | Start | Bedrijfseconomie vwo, examens 2025-I en 2026-I, tegen de criteria van run `20261021-1647-bedrijfseconomie-vwo-2028-run2`. |
| 13 | Vraag zonder •-opsplitsing (≥ 2 p) | Hele vraag → één criterium, met alle punten. |
| 14 | Alternatieve route ("of") | Alleen de eerste route telt en wordt gekoppeld; alternatieven als notitie. |
| 15 | Uitwerkbijlage | Niet nodig (het correctievoorschrift toont de ingevulde tabel); optioneel als invoer. |

Door de straat-architect als standaard gekozen (bij de goedkeuring van het voorstel
geaccepteerd): examen-id `vwo-2025-tv1` uit de code `VW-0400-a-25-1`; een rechter
beoordeelt één opgave (contextblok); maximaal 4 opgaven per bericht.

## 3. Wat we in de examens zagen (bedrijfseconomie vwo 2025-I, 2026-I)

- Drie PDF's per examen, alle met tekstlaag (geen OCR nodig):
  `-o` opgavenboekje, `-b` informatieboekje (formuleblad + informatiebronnen), `-c`
  correctievoorschrift. De uitwerkbijlage (`-u`) ontbreekt.
- Opgavenboekje: kop met "Dit examen bestaat uit 30 vragen. … maximaal 63 punten";
  contextblokken "Opgave n" (soms "Bij deze opgave horen de informatiebronnen 1 tot en
  met 4"); vragen doorgenummerd met de punten ervoor (`2p 13 Analyseer …`).
- Correctievoorschrift, hoofdstuk 4 *Beoordelingsmodel*: per vraag
  `n maximumscore k`, daarna één van vier vormen:
  1. •-scorepunten van 1 punt (vraag 3, 6, 10, 12);
  2. "per juist (toegelicht) antwoord 1" bij max 2 (vraag 1, 4, 8, 11);
  3. geen opsplitsing, 1 punt (vraag 2, 5, 7, 18);
  4. geen opsplitsing, ≥ 2 punten, "per gemaakte fout 1 scorepunt in mindering" (vraag 9).
  Plus alternatieve routes ("of") en *Opmerking(en)* met aftrek.
- De •-tekens komen uit `pdftotext` als `�`; tabellen in het correctievoorschrift
  (vraag 6, 12) vallen in kolommen uiteen. Een snelle regex vond 29 van de 30 vragen:
  de ingest moet daarom deterministisch tegen de kop controleren.

## 4. Opzet

```
input/examens-<vak>/<jaar TVn>/*-o.pdf, -c.pdf, -b.pdf
   │
[E1 ingest]   exam_text.py + agent exam-ingest ──► 21_exam_units.json (+ tekst in run/text/)
   │          validate_exam.py: vragen/punten = kop, scorepunten = maximumscore
[E1b intake]  intake (exam mode) ──► PAUZE (alle examens samen) ──► decisions.json
[E2 kandidaten] exam_candidates.py ──► 22_candidates.json (top 8 criteria per scorepunt)
[E3 rechters A/B] exam-judge per opgave ──► 23_judgements.{A,B}/<opgave>.json
[E4 samenvoegen] exam_merge.py + check_exam_mappings.py ──► 24_mappings.json, 24_findings.json
[E5 verifier]  mapping-verifier (exam mode) ──► 25_verification.json ──► reparatie (exam-judge R, 1 ronde)
[E6 bank]      bank_add.py ──► subjects/<vak>/examenbank/   bank_export.py ──► examenbank/output/
```

### Hergebruik

| Bestaand onderdeel | Gebruik in de examen-straat |
|---|---|
| `intake` + `decisions.py` | intake in *exam mode*; zelfde pauze en registratie |
| `exercise-judge` | basis voor de nieuwe agent `exam-judge` |
| `mapping-verifier` | nieuwe *exam mode* |
| `ex_merge.py` / `mcommon.py` | zekerheidsregels A/B, citaatcontrole, Bloom-regels (MB1/MB2) |
| `candidates.py` / `ex_candidates.py` | term-overlap en idf voor de kandidaten |
| `ocr_pdf.py` | alleen als een PDF geen tekstlaag heeft |
| `common.load_bloom_rules` | vakeigen werkwoordentabel (bijlage 3) |

### Nieuw

- Specs 20–25; schema's `exam_units`, `exam_candidates`, `exam_judgements`,
  `exam_mappings`, `exam_verification`, `exam_bank`.
- Agents `exam-ingest`, `exam-judge`; *exam mode* in `intake` en `mapping-verifier`.
- Scripts in `scripts/exam/`: `exam_text.py`, `validate_exam.py`, `exam_candidates.py`,
  `exam_merge.py`, `check_exam_mappings.py`, `bank_add.py`, `bank_export.py`.
- Command `/examen`; fixture + `tests/run_examen_fixture.py`; stukje in de handleiding.

## 5. Bouwvolgorde

1. Specs 20–25 en dit plan (deze stap).
2. Schema's en `exam_text.py` + `validate_exam.py`, getest op 2025-I en 2026-I
   (alleen ingest, geen agents).
3. `exam_candidates.py`, `exam_merge.py`, `check_exam_mappings.py`, `bank_add.py`,
   `bank_export.py` + fixture-test.
4. Agents `exam-ingest`, `exam-judge`, de *exam modes* en het command `/examen`.
5. Eerste echte run op 2025-I en 2026-I; steekproef door Martijn; lessen in CLAUDE.md.

## 6. Klaar als (v1)

1. `/examen` verwerkt beide examens zonder menselijke invoer behalve de intake.
2. Voor elk examen: som van de scorepunten = maximumscore uit de kop; elk scorepunt
   heeft een criterium of staat als *buiten huidige syllabus* in de bevindingen.
3. Elk opgeslagen citaat staat letterlijk in de vraagtekst en is ≤ 25 woorden.
4. De bank bevat beide examens; een tweede run met één extra examen voegt toe zonder
   bestaande koppelingen te wijzigen.
5. Steekproef van Martijn (10 hoog / 10 laag): hoog ≥ 95 % juist, laag duidelijk slechter.

## 7. Kosten (schatting)

Per examen ± 5–6 opgaven × 2 rechters + 1 verifier + ± 5 reparaties ≈ 20–25
agent-aanroepen. Voor de twee startexamens ≈ 45.
