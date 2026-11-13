# Bouwvragen toets-straat (fase 1: bouwstappen 1–3)

**Status:** beslist 2026-11-13 (zie §Besluiten) · **Gesteld door:** de bouwer, 2026-11-13 · **Beslist door:** Martijn

Bij het bouwen van stap 1–3 (`docs/plan-toets-straat.md` §4) bleek de spec op een paar punten niet eenduidig.
Overal is de kleinste technische keuze gemaakt die de beslissing openhoudt. Per vraag staan de context, de opties en
een aanbeveling. Een antwoord verandert alleen een constante of een paar regels code.

---

### 1. Labels: oneens op een knop met twee waarden (nee/ja) — *medium* of *geschil*?

**Context.** specs/26 §3.2 zegt: "ordinal fields one step apart → `medium` and the lower value". Bij knoppen met
maar twee waarden (`claim`, `new_concept`, `builds_on`, `route`, `schema`) liggen twee verschillende antwoorden altijd
één stap uit elkaar. Letterlijk gelezen gaat zo'n verschil dus nooit naar beoordelaar R: het wordt *medium* met de
lagere waarde (`nee`, `gegeven`, `voorgestructureerd`). Zo is het nu gebouwd (`MIN_VALUES_FOR_MEDIUM = 2` in
`scripts/exam/label_merge.py`).

**Opties.**
- a. Zo laten: bij een verschil wint de lagere waarde als *medium*, zonder R.
- b. Bij knoppen met twee waarden wordt een verschil een *geschil*; R beslist (constante op 3).

**Aanbeveling: b.** Bij ja/nee bestaat "één stap ernaast" niet. Een verschil over "zit er een bewering in de stam?"
is een echte onenigheid. Als de lagere waarde automatisch wint, worden `ja`-aandelen in het referentieprofiel
structureel te laag.

### 2. Referentieprofiel: hoe tellen de punten van een gecombineerd patroon (`P08+B02`)?

**Context.** specs/26 §2 staat twee codes per vraag toe, maar §4 zegt niet hoe de punten over de patronen gaan.
Nu worden de punten **gelijk verdeeld** (3 punten → 1,5 bij P08 en 1,5 bij B02). Zo blijft de patroonkolom optellen
tot de examenpunten (conservatie). In `patronen_stats.json` telt de vraag wel mee als één vraag bij elk patroon,
met de volledige punten als min/max.

**Opties.** a. gelijk verdelen (nu) · b. alle punten naar het eerste patroon · c. alle punten naar beide patronen
(dan telt de kolom op tot meer dan 100 %).

**Aanbeveling: a.**

### 3. Bloom-mix in de opdracht: is "ontbreekt" iets anders dan `null`?

**Context.** specs/32 §1 zegt: `bloom_mix` is optioneel en zonder mix kiest de planner. In §3 staat: vraag in de
dialoog naar "missing or null fields". Gebouwd is: **sleutel ontbreekt** = /toets vraagt het. **`null`** = bewust
geen mix, de planner kiest. Het formulier heeft daarom drie standen: *Nog niet gekozen* / *Geen Bloom-mix* /
*Bloom-mix instellen*.

**Opties.** a. zo laten · b. een ontbrekende mix betekent altijd "geen mix" en wordt nooit gevraagd.

**Aanbeveling: a.** Zo vraagt de straat de Bloom-mix nooit stilzwijgend over.

### 4. Economie heeft nog geen examenbank: formulier en /toets kunnen daar nog niet starten

**Context.** Het formulier en T0 lezen de criteria uit `subjects/<vak>/examenbank/criteria.json`. specs/33 T0 zegt:
zonder bank stoppen. Economie heeft wel `seed_profile.json`, maar nog geen bank. Daarom geeft
`form_build.py economie` nu de melding "draai eerst /examen". Voor bedrijfseconomie werkt het formulier al
(119 leerdoelen), maar zonder referentie (zie vraag 5).

**Opties.**
- a. Zo laten: eerst `/examen` voor economie (plan §4 stap 8).
- b. Het formulier mag de criteria ook uit een `/generate`-run halen als er geen bank is. Dan wordt de seed meteen
  bruikbaar.

**Aanbeveling: a.** Een toets hoort aan dezelfde criteriaversie te hangen als de examenbank (specs/30 §2). Optie b
geeft later twee criteriaversies.

### 5. Bedrijfseconomie heeft geen seed-profiel: tot E7 is er geen referentie

**Context.** specs/26 §6 noemt alleen voor economie een seed. Tot de eerste `/examen --label`-run voor
bedrijfseconomie toont het formulier bij elke knop "eindexamen: onbekend". Alleen de Bloom-mix heeft wel een
referentie (de gekoppelde punten in de bank).

**Opties.** a. eerst E7 draaien op 2025-I en 2026-I (plan §4 stap 2, eerste run) · b. ook voor bedrijfseconomie een
seed maken uit de analyse van november 2026.

**Aanbeveling: a.** Dat is toch de volgende stap, en dan is de referentie meteen gemeten met hetzelfde instrument.

### 6. Vraag met een nieuw patroon (`NIEUW`): tellen de andere knoppen wel mee?

**Context.** Een vraag met `pattern: NIEUW` telt niet mee in de patroonkolom (weggelaten als "nieuw patroon"). Zijn
`route` en `schema` hangen af van het soort patroon, maar dat is nog niet beslist. Nu tellen ze mee als de labellers
een waarde gaven.

**Opties.** a. meetellen (nu) · b. `route`/`schema` van zo'n vraag weglaten tot het patroon beslist is.

**Aanbeveling: b**, maar het verschil is klein: het gaat om enkele vragen per examen.

### 7. Bewijscitaat ongeldig: alleen de check laten falen, of ook de zekerheid verlagen?

**Context.** Bij koppelingen (specs/22) verlaagt een ongeldig citaat de zekerheid naar *medium*. specs/26 zegt alleen
"checked as in specs/24". Gebouwd is: `check_labels.py` faalt (LB4) en de orchestrator laat die labeller één keer
opnieuw lopen (zoals bij E4). `label_merge.py` verlaagt niets.

**Opties.** a. zo laten · b. daarnaast in de merge het veld op *medium* zetten als een van de twee citaten ongeldig is.

**Aanbeveling: a.** Na de herstart is het citaat geldig of blijft de check rood. Er sluipt dus niets door.

### 8. O6-waarschuwing "route zonder rekengroepen": hoe herken je een rekengroep?

**Context.** specs/34 O6 waarschuwt bij "`route` shares on a toets without calculation groups". Leerdoelen hebben
geen soort (rekenen/uitleggen). Gebouwd is: een waarschuwing als `route` (of `schema`) aandelen heeft, terwijl de
patroonaandelen geen enkel reken- of schemapatroon bevatten.

**Opties.** a. zo laten · b. ook kijken naar criteria met een rekenwerkwoord (`berekenen`, `opstellen`). Dat vraagt
een lijst werkwoorden per vak.

**Aanbeveling: a.**

### 9. Keuzeknoppen in de dialoog: hoeveel lichter of zwaarder?

**Context.** specs/32 §3 noemt als opties *Zoals eindexamen*, *Lichter (≈ 30 %)*, *Zwaarder (≈ 80 %)* en *Vrij*,
met één voorbeeld (route). In `.claude/commands/toets.md` staat nu als richtlijn: schuif 20–30 procentpunt naar de
lage of de hoge kant van de knop, en noem de percentages in de knop.

**Opties.** a. 20–30 pp (nu) · b. een vaste verschuiving per knop in `knobs.json` (bijv. `lighter`/`heavier`).

**Aanbeveling: b** zodra je de eerste toetsen hebt gemaakt. Tot dan a.

### 10. `label_evidence` per knop ontbreekt in `knobs.json`

**Context.** specs/31 §4 geeft per knop een `label_evidence` (wat de labeller citeert). In de seed staat dat veld
niet. Het schema laat het nu optioneel. De agent `item-labeller` noemt per knop zelf wat als bewijs telt.

**Opties.** a. optioneel laten · b. per knop invullen in `knobs.json` (via een besluit; `knobs.json` is een
regelbestand).

**Aanbeveling: b**, na de eerste E7-run op bedrijfseconomie, met wat de labellers in de praktijk citeerden.

---

## Besluiten (Martijn, 2026-11-13)

| Vraag | Besluit | Gevolg |
|---|---|---|
| 1 | **b** — bij ja/nee-knoppen is elk verschil een geschil; R beslist | `MIN_VALUES_FOR_MEDIUM = 3`; specs/26 §3.2 aangepast |
| 2 | **a** — punten van een gecombineerd patroon gelijk verdelen | zoals gebouwd; specs/26 §4 aangevuld |
| 3 | **a** — ontbrekend = vragen, `null` = bewust geen mix | zoals gebouwd |
| 4 | **a** — economie eerst door `/examen` | zoals gebouwd |
| 5 | **a** — bedrijfseconomie eerst E7, geen seed | volgende run |
| 6 | **b** — `route`/`schema` van een vraag met `NIEUW` weglaten tot het patroon beslist is | `profile_build.py` aanpassen; specs/26 §4 aangevuld |
| 7 | **a** — ongeldig citaat: check faalt, labeller opnieuw; geen zekerheidsverlaging | zoals gebouwd |
| 8 | **a** — rekentoets herkennen aan de patroonaandelen | zoals gebouwd |
| 9 | **a** nu (20–30 pp), **b** (vaste stap per knop in `knobs.json`) na de eerste toetsen | later besluit |
| 10 | **b** — `label_evidence` per knop invullen na de eerste E7-run op bedrijfseconomie, via een besluit | later besluit |

---

# Fase 2: bouwstappen 4–5 (bouwplan, schrijven en controleren)

**Status:** beslist 2026-11-14 · **Gesteld door:** de bouwer, 2026-11-14 · **Beslist door:** Martijn

Ook hier is steeds de kleinste technische keuze gebouwd. Elke keuze staat in één constante of een paar regels.

### 11. Welke getallen hoeven niet in `data` (IT3)?

**Context.** specs/34 IT3 zegt: elk getal in stam, bronnen, tabellen en uitwerkbijlage staat in `data`. Strikt gelezen
geldt dat ook voor "1 + btw", jaartallen ("in 2027") en "100 %". Gebouwd is: verwijsnummers ("informatiebron 2",
"vraag 3 en 4", "figuur 1") tellen niet mee. Ook **0, 1 en 100** zijn altijd toegestaan (`EXEMPT` in
`items_check.py`). Jaartallen moeten nu wel in `data` staan (bijv. `"jaar": 2027`).

**Opties.** a. zo laten · b. ook jaartallen (1900–2100) vrijstellen · c. niets vrijstellen behalve verwijsnummers.

**Aanbeveling: b.** Een jaartal is context, geen rekengegeven. Als je een jaartal moet benoemen, levert dat alleen
ruis op in `data`.

### 12. Rekent een volgende stap met de afgeronde tussenuitkomst?

**Context.** `calc_check.py` rondt elke `calc` af zoals het correctievoorschrift hem toont (`round`). Volgende
berekeningen rekenen verder met die **afgeronde** waarde, zoals de modeluitwerking dat doet. De schrijver en de
controle gebruiken hetzelfde getal.

**Opties.** a. verder met de afgeronde waarde (nu) · b. verder met de onafgeronde waarde (dan kan de modeluitwerking
één cent afwijken van wat er staat).

**Aanbeveling: a.** Een leerling die de modeluitwerking volgt, komt precies op het getal in het cv uit. Een
alternatief antwoord met onafgeronde tussenwaarden hoort in `alternatives`.

### 13. Welke bouwplanfouten mag je bij pauze 2 accepteren?

**Context.** specs/33 T2b: de docent kan een afwijking accepteren (`accept_deviation`). Gebouwd is: BP5–BP9 (Bloom
binnen patroon of criterium, knoppen, tolerantie, context, figuur/P15) worden dan een waarschuwing. **BP1–BP4**
(structuur, aantallen, matrijs, criteria) kun je nooit accepteren. specs/31 §5 noemt Bloom hoger dan criterium + 1
echter "a blueprint error".

**Opties.** a. zo laten (ook Bloom > criterium + 1 accepteren) · b. dat ene deel van BP5 nooit accepteren; de rest
van BP5–BP9 wel.

**Aanbeveling: b.** Een scorepunt boven criterium + 1 toetst iets wat de leerlingen niet hebben geleerd. Dat kan de
verantwoording niet goedmaken.

### 14. Wanneer herhaalt een context een eerdere toets (BP8)?

**Context.** specs/34 BP8 zegt: "no context with a `context_tags` pair from the history". Gebouwd is: **elke** twee
tags die een opgave deelt met een opgave uit de historie (de laatste 24 maanden) tellen als herhaling. Ook geldt: geen
twee opgaven met dezelfde eerste tag (branche) in één toets.

**Opties.** a. elk gedeeld paar (nu) · b. alleen de eerste twee tags (branche + setting).

**Aanbeveling: a.** Dat is strenger, en een herhaalde context was juist het probleem (vier keer e-bike).

### 15. Coördinaten in een figuur: 0 en de aslimieten zonder naam?

**Context.** specs/35 §3 zegt: elke coördinaat is een `data`-waarde of een `calc`-uitkomst. Een vraaglijn begint vaak
bij 0 of loopt tot de rand van de as. Gebouwd is: **0 en de min/max van de assen** zijn altijd toegestaan. Alle andere
coördinaten moeten benoemd zijn (FG).

**Opties.** a. zo laten · b. ook 0 en aslimieten laten benoemen.

**Aanbeveling: a.**

### 16. Oplosser: welke tussenuitkomsten tellen mee?

**Context.** `solver_compare.py` kijkt of de oplosser het eindgetal en **alle** tussenberekeningen van het cv noemt.
In de fixture noemt de oplosser de factor 1,21 niet. De vraag krijgt dan `partial`, terwijl het antwoord goed is.

**Opties.** a. alle `calc`'s (nu) · b. alleen de `calc`'s waarop een scorepunt staat (`calc_ref`), plus het eindgetal.

**Aanbeveling: b.** Een scorepunt is wat de leerling moet laten zien. Hulpgetallen zonder scorepunt zeggen niets over
de juistheid van de vraag.

### 17. Voortbouwen bij een uitlegvraag (IT5)

**Context.** specs/34 IT5 zegt: bij `builds_on = ja` gebruikt minstens één `calc` een naam uit een eerdere vraag. Een
uitlegvraag die voortbouwt ("verklaar de uitkomst van vraag 2") heeft geen `calc` en faalt dan altijd.

**Opties.**
- a. zo laten: voortbouwen alleen bij rekenvragen.
- b. Bij een vraag zonder `calc` geldt het als voortbouwen als de stam "vraag n" noemt (n uit `builds_on_vragen`) en
  het cv een `follow_through`-zin heeft.

**Aanbeveling: b.** Ook in het centraal examen bouwen uitlegvragen voort op een eerdere uitkomst.

### Besluiten fase 2 (Martijn, 2026-11-14)

| Vraag | Besluit | Gevolg |
|---|---|---|
| 11 | **b** — jaartallen 1900–2100 vrijgesteld | `EXEMPT` uitbreiden; specs/34 IT3 |
| 12 | **a** — verder met de afgeronde tussenuitkomst | zoals gebouwd |
| 13 | **b** — Bloom boven criterium + 1 nooit accepteren; rest van BP5–BP9 wel | `blueprint_apply.py`/`blueprint_check.py`; specs/33 T2b |
| 14 | **a** — elk gedeeld tag-paar telt als herhaling | zoals gebouwd |
| 15 | **a** — 0 en aslimieten zonder naam | zoals gebouwd |
| 16 | **b** — alleen eindgetal + `calc`'s met scorepunt | `solver_compare.py`; specs/34 §4 |
| 17 | **b** — uitlegvraag bouwt voort via "vraag n" in de stam + doorrekenzin | `items_check.py`; specs/34 IT5 |

---

# Fase 3: bouwstap 6 (export, toetsbank, hergebruik)

**Status:** open · **Gesteld door:** de bouwer, 2026-11-14 · **Beslist door:** Martijn

### 18. Hergebruikte opgave: "vraag n" in de stam klopt niet meer

**Context.** Een hergebruikte opgave wordt letterlijk overgenomen (besluit A1), maar krijgt de vraagnummers van de
nieuwe toets. Een stam die naar "vraag 3" verwijst, verwijst dan naar het oude nummer. Gebouwd is: `reuse_copy.py`
past `builds_on_vragen` aan, laat de stam letterlijk staan en geeft een waarschuwing die de orchestrator aan jou
voorlegt.

**Opties.** a. zo laten (waarschuwing, jij past aan) · b. het nummer in de stam automatisch aanpassen (dan is de opgave
niet meer helemaal letterlijk) · c. een opgave met zo'n verwijzing alleen hergebruiken op dezelfde vraagnummers.

**Aanbeveling: b.** Het gaat alleen om het nummer, niet om de inhoud. Een verkeerde verwijzing in een toets is erger
dan een kleine afwijking van "letterlijk".

### 19. Nummering van informatiebronnen in de leerlingversie

**Context.** De schrijver nummert de bronnen per opgave (1, 2, …). In het centraal examen lopen de bronnen door over
het hele examen. Gebouwd is: per opgave genummerd, onder de kop van de opgave ("Opgave 2 Bakkerij Kruim" →
"Informatiebron 1"). Zo blijven de verwijzingen in de stam kloppen.

**Opties.** a. per opgave (nu) · b. doorlopend over de toets. Dan moet de export de verwijzingen in stam en cv
hernummeren.

**Aanbeveling: a**, tenzij leerlingen het examenformat met doorlopende nummers moeten oefenen. Dan b.

### 20. toets_id in de toetsbank

**Context.** specs/35 §4 legt de vorm van `toets_id` niet vast. Gebouwd is: `toets_id` = de run-id
(`20301001-1200-toets-bedrijfseconomie`). Die is uniek en verwijst terug naar de run.

**Opties.** a. run-id (nu) · b. een korte code die je zelf kiest (bijv. `5V-P2-F2`) en die in de opdracht staat.

**Aanbeveling: a**, met de titel ernaast in het register (zo staat het er al).
