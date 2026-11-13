# Plan van aanpak — toets-straat (`/toets`, Toetsgenerator-straat)

**Status:** vastgesteld 2026-11-13 · **Eigenaar:** Martijn (docent, beslist) · **Architect/PO:** Claude ·
**Specs:** [26](../specs/26-examen-labels.md), [30–35](../specs/30-toets-overview.md)

## 1. Doel

Een vierde straat in deze repo. Je stelt per vak een toets samen: de **toetsmatrijs** (punten per
leerdoel, eventueel met een Bloom-mix), het **aantal opgaven en vragen** en het **niveau** met
knoppen. Bij elke knop zie je wat het **centraal examen** doet. De straat maakt een bouwplan dat jij
goedkeurt. Daarna schrijft de straat de opgaven met correctievoorschrift. Een blinde oplosser maakt
de toets, scripts rekenen alles na en een verse verifier beoordeelt het resultaat.

Je krijgt:
- een leerlingversie;
- een correctievoorschrift;
- een verantwoording (gepland vs gerealiseerd vs eindexamen) in Word en Markdown.

Elke toets komt in een **toetsbank** per vak, zodat contexten niet terugkomen en je opgaven kunt
hergebruiken.

## 2. Beslissingen (2026-11-13, door Martijn)

| # | Onderwerp | Besluit |
|---|---|---|
| 1 | Plek | 4e straat in deze repo: `/toets`, specs 30–35, plus specs 26 als uitbreiding van `/examen`. |
| 2 | Niveau | Geen vaste presets. Per knop staat het **eindexamenaandeel** als referentie. Jij zet het aandeel voor jouw toets, de straat verdeelt dat over de vragen en in het bouwplan kun je per vraag overschrijven. |
| 3 | Toetsmatrijs | Punten per leerdoel + optioneel een Bloom-mix voor de hele toets. |
| 4 | Bediening | **Beide**: een HTML-formulier (matrijs en knoppen) en keuzeknoppen in `/toets` voor wat open blijft. |
| 5 | Referentieprofiel | Nieuwe stap in `/examen` labelt elke examenvraag met patroon + knopwaarden (twee beoordelaars). Het profiel wordt **per vak opgeslagen** en wordt **bij elk nieuw examen bijgewerkt**. |
| 6 | Pauzes | Twee: opdracht bevestigen en bouwplan goedkeuren. |
| 7 | Begripscriteria | Geen aparte regel; de Bloom-mix bepaalt het. Het bouwplan toont per leerdoel welke criteria wel en niet getoetst worden. |
| 8 | Output | Word + Markdown: leerlingversie, correctievoorschrift, verantwoording met knoppen **gepland vs gerealiseerd vs eindexamen**. |
| 9 | Context | De straat stelt voor en vermijdt contexten uit eerdere toetsen. Jij kunt vervangen in het bouwplan. |
| 10 | Controle | Blinde oplosser + scripts (alle berekeningen nagerekend, punten tegen de matrijs) + verse verifier; max. 2 reparatierondes, de rest naar de twijfellijst. |
| 11 | Formulier | Lokaal HTML-bestand per vak, zonder server. |
| 12 | Figuren | De straat tekent ze: de schrijver levert figuurdata, een script tekent (matplotlib). |
| 13 | Voorbeelden | De schrijver ziet 1–2 echte examenvragen per patroon, met een overlapcheck tegen kopiëren. |
| 14 | Toetsbank | Per vak, in git; opgaven herbruikbaar; contexthistorie. |
| 15 | Scope v1 | Bedrijfseconomie + economie, VWO 4–6; referentie = VWO-eindexamen. HAVO later. |
| 16 | Aandelen | Per **punt** (zoals matrijs en referentieprofiel). |
| 17 | Onthouden | Nieuw basispatroon **P16 Kennisvraag (noem of omschrijf)**, gemarkeerd als *niet in centraal examen*. |
| 18 | Tolerantie | Bloom-mix ±5 procentpunt, knoppen ±10 pp, altijd minstens één vraag speling; punten per leerdoel exact. |
| 19 | Voortbouwen | Alleen binnen een opgave. |

Door de architect als standaard gekozen (graag bevestigen of wijzigen):

| # | Standaard | Waarom |
|---|---|---|
| A1 | Hergebruikte opgaven blijven letterlijk en tellen mee in matrijs en aandelen. | Een herbruikte opgave is al gecontroleerd. |
| A2 | Het niveau (4/5/6 VWO) zet geen knoppen; het stuurt alleen taal, context en getallen. | Jij zet de knoppen zelf tegen de eindexamenreferentie (besluit 2). |
| A3 | Een opdracht kan als **sjabloon** per vak worden bewaard ("mijn 4 VWO-toets"). | Dan hoef je het niveau niet elke keer opnieuw te zetten. |
| A4 | Word via python-docx. | Eén taal (Python) in deze repo. |
| A5 | `combinatie` (aantal leerdoelen per vraag) en Bloom worden berekend uit de koppelingen, niet gelabeld. | Deterministisch; de labels blijven geldig bij nieuwe criteria. |
| A6 | Het label-geschil wordt beslecht door een derde beoordelaar (R), zonder verifier. | Dat is goedkoper; knoplabels zijn minder zwaar dan criteriumkoppelingen. |
| A7 | Contexthistorie: de laatste 24 maanden. | Dat dekt twee schooljaren. |

## 3. Wat de tests van november 2026 ons leerden (en waar het in de specs zit)

| Bevinding | Maatregel | Spec |
|---|---|---|
| Zonder expliciete profielen raadt de AI het niveau | Knoppen met eindexamenreferentie, bouwplan met knoppen per vraag | 31, 32, 33 |
| Context convergeert (vier keer e-bike) | Contexthistorie, `avoid_contexts`, branchevariatie per toets, bouwplancheck BP8 | 33, 34 |
| Begripscriteria bleven ongetoetst bij een vast patroon | Bloom-mix in de matrijs + overzicht van getoetste/ongetoetste criteria per leerdoel | 32, 33 |
| SOLO-zelfrapportage van de agent klopt niet altijd | Gerealiseerde knoppen worden gelabeld door aparte, blinde beoordelaars | 34 |
| Een 'nieuw begrip in de stam' viel buiten de set | Knop `new_concept` + verifiercheck V7 | 31, 34 |
| Eén beoordelaar drijft (analyseren 9 vs 29 punten) | Twee labellers + R-ronde | 26 |
| Rekenfouten en dubbelzinnige beweringen (6 VWO vraag 3) | Alle getallen benoemd, script rekent na, blinde oplosser | 33, 34 |

## 4. Bouwvolgorde (voor de bouwer)

1. **Data en schema's**: `data/toets/knobs.json`, `patterns_base.json` en `subjects/*/toets/patterns.json`
   (seed bijgeleverd), `scripts/toets/patterns.py` (seed-validatie, `merged`, `add`, `retire`).
   Schema's: `toets_order`, `blueprint`, `blueprint_review`, `toets_items`, `solver_answers`,
   `item_labels`, `toets_verification`, `reference_profile`, `patterns`, `knobs`, `toetsbank`.
2. **`/examen` E7** (specs 26): agent `item-labeller`, `label_merge.py`, `check_labels.py`,
   `bank_labels_add.py`, `profile_build.py`, `/examen --label`. **Eerste run:** bedrijfseconomie
   2025-I + 2026-I labelen. Daarna staat het eerste echte referentieprofiel klaar.
3. **Opdracht en formulier**: `form_build.py`, `validate_toets.py order`, de knoppendialoog in
   `/toets`.
4. **Bouwplan**: agent `toets-planner`, `blueprint_check.py`, `blueprint_report.py`,
   `blueprint_apply.py`.
5. **Schrijven en controleren**:
   - agent `toets-writer`;
   - `exam_examples.py`, `items_check.py`, `calc_check.py`, `figures.py`, `overlap_check.py`;
   - `student_build.py`, agent `toets-solver`, `solver_compare.py`;
   - `realized.py`, agent `toets-verifier`.
6. **Export en bank**: `export_toets.py` (python-docx), `toetsbank_add.py`.
7. **Fixture**: `tests/run_toets_fixture.py` met een kleine synthetische opdracht, een bouwplan en
   items met een bewuste rekenfout, een overlap en een tolerantie-afwijking. De scripts moeten die
   vinden.
8. **Eerste echte run**: bedrijfseconomie 5 VWO, F2-leerdoelen, 3 opgaven, 11 vragen. Daarna economie
   (`/examen` op de vijf examens, dan E7).

## 5. Open punten voor later (niet in v1)

- Nakijkr-export zodra het importformaat vastligt.
- HAVO (vraagt HAVO-examenbank en -referentie).
- Parallelversies (A/B) via `--from-blueprint`.
