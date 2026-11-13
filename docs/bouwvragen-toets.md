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
