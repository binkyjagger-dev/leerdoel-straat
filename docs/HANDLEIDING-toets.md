# Handleiding toets-straat

Deze handleiding is voor docenten zonder technische achtergrond. Je typt twee korte opdrachten; de rest kies je met knoppen.

## Wat de toets-straat doet

Je geeft op welke leerdoelen in de toets moeten en hoe zwaar hij mag zijn. De straat levert dan een complete toets in eindexamenstijl, met correctievoorschrift. Jij beslist op twee momenten; de rest gaat vanzelf.

Wat je krijgt, in Word (en als pdf als LibreOffice op je pc staat):

- **Leerlingversie**: opgaven, informatiebronnen en uitwerkbijlage.
- **Correctievoorschrift**: per vraag de maximumscore, een modelantwoord en de scorepunten.
- **Verantwoording**: hoe de toets aansluit op je matrijs en hoe zwaar hij is, vergeleken met het centraal examen.
- **Twijfellijst**: punten die je nog even moet bekijken voordat je de toets gebruikt.

Een toets van 5 opgaven kost ongeveer een uur machinetijd en 15 tot 30 minuten van jou.

## Eenmalig klaarzetten

Dit doe je één keer per computer.

1. **Claude Code installeren.** Gebruik de desktop-app van Claude (tabblad Code) of Claude Code in de terminal. Je hebt een abonnement met toegang tot Opus nodig.
2. **De straat ophalen.** De map heet `leerdoel-straat`. Ophalen of bijwerken gaat met git (`git clone https://github.com/binkyjagger-dev/leerdoel-straat`, later `git pull` in die map).
3. **Python-onderdelen installeren.** Open PowerShell in de map en typ: `pip install jsonschema pymupdf matplotlib python-docx`.
4. **Testen.** Typ in dezelfde map: `python tests/run_toets_fixture.py`. Onderaan moet **ALL OK** staan. Zie je een foutmelding, kijk dan bij *Als er iets misgaat*.
5. **Optioneel: LibreOffice installeren.** Dan krijg je naast Word-bestanden ook pdf's.

Per vak is één ding nodig: een examenbank. Die maak je met de examen-straat (`/examen`) uit eindexamens van dat vak. Voor bedrijfseconomie bestaat hij al (2025-I en 2026-I). De examen-pdf's staan in `input\examens-bedrijfseconomie-vwo\`; die gaan niet mee via git.

## Een toets maken, stap voor stap

Bedrijfseconomie dient hieronder als voorbeeld; voor een ander vak vervang je dat woord.

1. **Open Claude Code in de map van de straat.** In de desktop-app kies je bij het tabblad Code de map `leerdoel-straat`. In de terminal ga je naar die map en typ je `claude`.
2. **Maak het toetsformulier.** Typ `/toets --formulier bedrijfseconomie`. Claude maakt een formulier en noemt waar het staat (`subjects\bedrijfseconomie\toets\toetsformulier-bedrijfseconomie.html`).
3. **Vul het formulier in.** Open het bestand door erop te dubbelklikken; het werkt in elke browser, ook zonder internet. Vul in:
    - de titel en het leerjaar;
    - per leerdoel hoeveel punten het krijgt (de toetsmatrijs). Het totaal staat bovenaan bij *Totaal punten (uit de matrijs)*; dat getal vul je niet zelf in;
    - het aantal opgaven en vragen. Naast *Aantal opgaven* staat hoeveel opgaven het eindexamen bij dit aantal punten zou hebben (ongeveer 10 punten per opgave). Met **Zet op eindexamen** neem je dat over;
    - de **toetsduur in minuten**: de tijd die leerlingen krijgen, bijvoorbeeld 90. Ernaast zie je hoeveel minuten per punt dat is en wat het eindexamen geeft (ongeveer 3 minuten per punt). Let op: vul hier geen punten in;
    - het **leesbudget**: hoeveel tekst de toets mag hebben, als percentage van het eindexamen. 60 % betekent: per punt 60 % van het aantal woorden dat het eindexamen gebruikt. Ernaast zie je hoeveel woorden dat voor jouw toets is. Kies *Geen leesbudget* als je geen grens wilt, of laat het op *Niet ingesteld*: dan vraagt de straat het;
    - de Bloom-mix en de knoppen. Naast elke knop zie je het eindexamen als referentie; wat je leeg laat, vraagt de straat straks na.
4. **Download de opdracht.** Klik op *Download toetsopdracht.json*. Het bestand komt meestal in je map Downloads.
5. **Start de toets.** Typ in Claude Code: `/toets C:\Users\<jouw naam>\Downloads\toetsopdracht.json --subject bedrijfseconomie`.
6. **Pauze 1: de opdracht.** De straat stelt vragen over wat je open liet, steeds met knoppen als *Zoals eindexamen*, *Lichter* of *Zwaarder*. Daarna leest hij de hele opdracht terug. Daarin staat altijd, telkens naast het eindexamen:
    - de toetsduur en het aantal minuten per punt;
    - het leesbudget in woorden;
    - het aantal opgaven en wat het eindexamen zou voorstellen;
    - hoeveel leerdoelen er per punt zijn.

    Wijkt iets veel af, dan vraagt de straat het, bijvoorbeeld *Zoals eindexamen (3)* of *Houden (5)* voor het aantal opgaven. Klopt het, kies dan **Akkoord**; anders **Aanpassen** en typ wat er anders moet.
7. **Wacht op het bouwplan** (ongeveer 5 minuten). De straat bedenkt per opgave één verhaal: een situatie met vaste personen of bedrijven, waarin de vragen elkaar opvolgen, zoals in het eindexamen. Per vraag staan het type, de punten, de leerdoelen en het aantal opdrachten in de vraag. Je krijgt een korte samenvatting en het bestand `bouwplan.md`. Staat bij een knop *weinig marge*, dan zit het plan al dicht bij de grens van wat je bestelde; na het schrijven valt zo'n knop er makkelijk buiten.
8. **Pauze 2: het bouwplan.** Lees het plan. Kies **Akkoord**, of:
    - **Context vervangen**, als een onderwerp je niet bevalt (bijvoorbeeld "geen fietsen");
    - **Vraag aanpassen**, als een vraag zwaarder, lichter of anders moet;
    - **Opnieuw plannen**, als het helemaal anders moet.

    De straat leest je wijziging terug voordat hij hem doorvoert. Er wordt niets geschreven voordat jij akkoord geeft.
9. **Wacht op de toets** (ongeveer een uur; je hoeft er niet bij te blijven). In die tijd gebeurt het volgende:
    - de straat schrijft de opgaven en rekent alle getallen na;
    - een onafhankelijke "leerling" maakt de toets blind;
    - twee beoordelaars meten hoe zwaar elke vraag is;
    - een controleur keurt elke vraag en laat zwakke vragen maximaal twee keer verbeteren.
10. **Lees het eindbericht.** Claude meldt hoeveel vragen zijn goedgekeurd, wat nog openstaat, en waar de bestanden staan: `runs\<datum>-toets-bedrijfseconomie\output\`.

Tussendoor kan de straat je een vraag stellen, bijvoorbeeld over een besluit dat nog niet genomen is. Je antwoord geldt dan ook voor volgende toetsen.

## Sneller werken met een sjabloon

Een sjabloon bewaart de instellingen die bij elke toets hetzelfde zijn. Per toets vul je dan alleen nog in wat anders is.

| In het sjabloon (blijft gelijk) | Per toets invullen |
|---|---|
| leerjaar | titel |
| aantal opgaven en vragen | toetsmatrijs: punten per leerdoel van deze periode |
| toetsduur | Bloom-mix (de straat stelt *Zoals eindexamen* voor) |
| leesbudget (bijvoorbeeld 60 % voor 4 VWO) | |
| de knoppen (hoe zwaar de vragen zijn) | |
| | contexten die je wilt vermijden of vastleggen |
| | opgaven die je hergebruikt uit de toetsbank |

De Bloom-mix staat bewust niet in het sjabloon. Welke niveaus mogelijk zijn, hangt af van de leerdoelen in de matrijs, en die verschillen per periode.

**Het sjabloon voor 5 VWO bedrijfseconomie** heet `5vwo-toets` en staat in `subjects\bedrijfseconomie\toets\sjablonen\`. Het bevat 5 opgaven, 16 vragen en de knoppen van de proeftoets van periode 2: rekenen iets zwaarder, verder iets lichter dan het eindexamen.

Zo gebruik je het:

1. Maak het formulier: `/toets --formulier bedrijfseconomie`.
2. Kies bij *Sjabloon laden* de optie **5vwo-toets**. Het leerjaar, de aantallen, de toetsduur, het leesbudget en de knoppen staan nu ingevuld (voor zover het sjabloon ze bevat).
3. Vul de titel en de punten per leerdoel in.
4. Pas eventueel een knop aan voor deze ene toets. Het sjabloon zelf verandert daardoor niet.
5. Klik op *Download toetsopdracht.json* en ga verder bij stap 5 hierboven.

Zo maak je een nieuw sjabloon:

1. Stel het formulier in zoals je het vaker wilt gebruiken.
2. Typ onderaan een *Sjabloonnaam*, bijvoorbeeld `4vwo-toets`, en klik op **Opslaan als sjabloon**.
3. Zet het gedownloade bestand in `subjects\<vak>\toets\sjablonen\` en maak het formulier opnieuw. Vanaf dan staat het sjabloon in de keuzelijst.

Een sjabloon kun je ook direct laden met de bestandsknop naast de keuzelijst, zonder het in de map te zetten.

## Wat je met het resultaat doet

Begin altijd met de twijfellijst. Pas daarna de Word-bestanden aan en zet ze in je eigen huisstijl.

| Bestand | Wat je ermee doet |
|---|---|
| `twijfellijst.md` | Lees dit eerst. **must**-punten moet je oplossen, **should**-punten zijn suggesties: vaak een zin die in de vraag ontbreekt ("exclusief btw") of een extra goed antwoord voor het correctievoorschrift. |
| `…-leerling.docx` | De toets voor leerlingen. Lees hem zelf één keer helemaal, alsof je hem maakt. |
| `…-correctievoorschrift.docx` | Voor het nakijken. Vul aan met antwoorden uit de twijfellijst die je ook goed wilt rekenen. |
| `…-verantwoording.docx` | Voor jezelf of de sectie: dekking per leerdoel, Bloom-mix en knoppen naast het eindexamen. Het laatste onderdeel, *Huisregels*, zet de toets naast het eindexamen: minuten per punt, aantal woorden tegen het leesbudget, punten en vragen per opgave, opdrachten per vraag, hoe vaak de vraag de aanpak of de conclusie al geeft, en of een begrip dat getoetst wordt al in de vraag staat. |
| `bouwplan.md` | Het goedgekeurde plan, ter controle. |

De `.md`-bestanden openen in Kladblok of in Claude. De straat zet de toets ook in de toetsbank van het vak. Zo vermijdt hij bij een volgende toets dezelfde contexten.

Wil je iets aan een vraag veranderen? Doe dat in Word. Je kunt het ook in Claude Code vragen ("maak vraag 7 duidelijker over btw"); dan past de straat het bestand aan en exporteert hij opnieuw. Let op: een geopend Word-bestand blokkeert het opnieuw exporteren, dus sluit het eerst.

## Begrippen kort uitgelegd

- **Toetsmatrijs**: per leerdoel het aantal punten. De straat houdt zich hier precies aan.
- **Bloom-mix**: welk deel van de punten onthouden, begrijpen, toepassen of analyseren is. De afwijking mag hooguit 5 procentpunt zijn.
- **Referentieprofiel**: hoe het centraal examen van dit vak scoort op Bloom en op de knoppen. De straat meet het uit echte examens; elk nieuw examen in de examenbank maakt het beter.
- **Patroon**: het soort vraag, zoals *standaardberekening*, *verklaar met een keten* of *noem en omschrijf*. De patronen komen uit de eindexamens.
- **Huisregels**: wat het centraal examen van dit vak gewoon vindt, gemeten uit de echte examens: minuten per punt, woorden per punt, punten per opgave, hoe lang een vraagzin is en hoeveel opdrachten één vraag bevat. De straat houdt zich hieraan; jij stelt alleen het leesbudget en de toetsduur in.
- **Leesbudget**: de hoeveelheid tekst in de toets (inleiding, bronnen en vragen), als percentage van het eindexamen per punt. Een lager percentage geeft kortere teksten, bijvoorbeeld voor 4 VWO.
- **Opbouw van een vraag**: eerst eventueel een paar regels nieuwe informatie voor deze stap van het verhaal, daarna op de regel met de punten de vraag zelf ("2p **3** Bereken …"). Zo staat het ook in het eindexamen.
- **Knoppen**: regelaars voor hoe zwaar een vraag is. De afwijking per knop mag hooguit 10 procentpunt zijn.

| Knop | Wat hij regelt | Lichter → zwaarder |
|---|---|---|
| Stappen | Hoeveel denkstappen achter elkaar | 1 → 4 of meer |
| Route | Noemt de vraag een tussenstap, methode, formule of begrip dat je moet gebruiken ("bereken hiervoor eerst …", "gebruik de cpi")? Geldt voor alle vragen | gegeven → zelf vinden |
| Richting | Noemt de vraag de conclusie al ("leg uit dat …", "toon aan dat …") of moet de leerling die zelf vinden ("leg uit of …")? Geldt voor uitleg- en rekenvragen | gegeven → open |
| Bronnen | Waar de gegevens staan | in de vraag → meerdere informatiebronnen |
| Ruis | Staan er gegevens die je niet nodig hebt? | nee → ja |
| SOLO-doel | Hoeveel samenhang het antwoord vraagt | één punt → verbanden leggen |
| Bewering in de stam | Moet de leerling een bewering beoordelen? | nee → ja |
| Nieuw begrip | Legt de vraag een onbekend begrip uit dat je moet toepassen? | nee → ja |
| Schema | Hoeveel van een schema al klaarstaat | voorgestructureerd → deels ingevuld |
| Voortbouwen | Heb je het antwoord op een eerdere vraag nodig? | nee → ja |

Kies je bij een knop *Vrij*, dan bepaalt de straat zelf de verdeling.

Niet als aanwijzing tellen: "gebruik informatiebron 2", "gebruik je antwoord op vraag 3", een algemene afrondregel ("rond af op één decimaal") en de uitleg van een nieuw begrip dat niet getoetst wordt.

## Als er iets misgaat

| Je ziet | Oplossing |
|---|---|
| `can't open file … No such file or directory` | Je staat in de verkeerde map. Typ `cd leerdoel-straat` en probeer het opnieuw. |
| `ModuleNotFoundError` | Er ontbreekt een Python-onderdeel. Typ `pip install jsonschema pymupdf matplotlib python-docx`. |
| `/toets` wordt niet herkend | Claude Code staat niet in de map `leerdoel-straat`. Sluit af en open het opnieuw in die map. |
| "De toets-straat heeft een criteriaversie nodig" | Dit vak heeft nog geen examenbank. Draai eerst `/examen` met eindexamens van dit vak. |
| Een fout over een bestand dat open is (PermissionError) | Sluit het Word-bestand en vraag Claude de export opnieuw te draaien. |
| "duration_minutes … < half a minute per point" (O7) | De toetsduur is te kort voor het aantal punten; waarschijnlijk staan er punten in het veld *Toetsduur (minuten)*. Vul het aantal minuten in. |
| "geen huisregels gemeten" | Voor dit vak zijn de eindexamens nog niet gemeten. De straat werkt gewoon, maar zonder leesbudget en grenzen per opgave. Vraag Claude `exam_metrics.py` voor dit vak te draaien. |
| € verschijnt als � in het venster | Alleen een weergavefout van Windows; de bestanden zijn goed. |
| De run stopt halverwege | Typ "ga verder met de toets-run". De straat gaat verder waar hij was, want alles staat in de runmap. |
| Na een tijd zonder gebruik werkt iets niet | Haal eerst de nieuwste versie op: `git pull` in de map `leerdoel-straat`. |

Twijfel je over een vraag die de straat stelt? Kies *Other* en typ je twijfel; Claude legt de keuzes dan eerst uit.
