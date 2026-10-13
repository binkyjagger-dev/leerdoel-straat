# Leerdoel-straat — handleiding op één pagina

Van syllabus naar leerdoelgroepen (leerdoel + succescriteria + Bloom) in leerlingentaal, gekoppeld aan eindtermen, met geverifieerde dekking. Eén keer instellen, daarna één commando per syllabus.

## 1. Eenmalig installeren (10 minuten)

```bash
git clone https://github.com/binkyjagger-dev/leerdoel-straat
cd leerdoel-straat
pip install --break-system-packages jsonschema
```
Je hebt ook `pdftotext` nodig (macOS: `brew install poppler`; Ubuntu: `apt install poppler-utils`; Windows: `winget install oschwartz10612.Poppler` of PyMuPDF via `pip install pymupdf`) en Claude Code met toegang tot Opus en Sonnet. Test de installatie: `python tests/run_fixture.py` — de laatste regel moet `RESULT: OK` zijn.

**Windows:** gebruik `python` waar hieronder `python3` staat (of `py -3`); in PowerShell werken alle `python scripts/...`-commando's gewoon. Bash is niet nodig.

## 2. Vakprofiel invullen (5 minuten, per vak)

```bash
python3 scripts/decisions.py init economie      # Windows: python scripts/decisions.py init economie
```
Gebruik een vaknaam in kleine letters zonder spaties (`economie`, `bedrijfseconomie`, `wiskunde-a`); dezelfde naam geef je straks aan `--subject`.
Open `subjects/economie/profile.md` en vul in wat jij als docent weet en de syllabus niet zegt: methode en editie, voorkeurstermen (bijv. *moral hazard* of *moreel risico*), sectie-afspraken, wat buiten scope valt. Dit bestand is van jou; de straat leest het in elke stap en schrijft er nooit in. Een leeg profiel werkt ook, maar dan stelt de straat meer vragen.

## 3. Een run draaien (≈ 45 min machinetijd, 5 min van jou)

Zet de syllabus-pdf in `input/` en start Claude Code in de map:

```
claude
> /generate input/syllabus-economie-vwo-2026.pdf --subject economie
```

Wat er gebeurt:

| Stap | Wie | Jij? |
|---|---|---|
| 1 Inlezen — domein → subdomein → specificatie, letterlijke tekst | agent + validator | nee |
| **1b Intake — vragen die de uitkomst sturen** | agent | **ja: dit is de enige pauze** |
| 2 Plannen — aantal groepen en Bloom-plafond per specificatie | agent + validator | nee |
| 3 Genereren — leerdoel + 2–4 criteria per groep, per subdomein parallel | agents + validators | nee |
| 4 Leerlingentaal — "Ik kan …", betekenis gelijk | agent + validator | nee |
| 5 Verifiëren — dekking twee kanten op, rubric J1–J8, max 2 herstelrondes | onafhankelijke agents | nee |
| 6 Exporteren — CSV, dekkingsrapport, twijfellijst | script | nee |

**De pauze (1b).** De straat toont je een handvol vragen met een voorgesteld antwoord — bijvoorbeeld welk werkwoord het Bloom-plafond bepaalt, of een term die methodes verschillend definiëren. Kies een optie of typ je eigen antwoord. Je antwoorden gaan naar `subjects/economie/decisions.json` en gelden voor alle volgende runs; dezelfde vraag wordt niet opnieuw gesteld. Sla je een vraag over, dan draait de straat op het voorstel en markeert de betrokken leerdoelen als *voorlopig* in de twijfellijst.

## 4. Resultaat lezen (in `runs/<run-id>/output/`)

- `leerdoelgroepen_per_leerdoel.csv` — één rij per leerdoel, criteria erachter. **Begin hier** voor je spot check.
- `leerdoelgroepen.csv` — één rij per succescriterium (Bloom op het criterium), voor import en analyse. Puntkomma-gescheiden, opent direct in Excel.
- `coverage_report.md` — dekking per eindterm, Bloom-verdeling, toegepaste vakbeslissingen.
- `doubt_list.md` — wat de straat niet zelf kon oplossen: afgekeurde groepen met voorstel, bronfouten, openstaande beslissingen. Dit is je nakijklijst; meestal minuten werk.

## 5. Beter worden per run

Zie je een patroon in de spot check? Pas dan de **regel** aan, niet de losse leerdoelen:

| Zie je… | Pas aan |
|---|---|
| een term die anders moet | `subjects/<vak>/profile.md` → Terminologie |
| een werkwoord op het verkeerde Bloom-niveau | `data/bloom_verbs_nl.json` |
| leerlingentaal te lang / te vaag | `data/student_language_rules.json` |
| een interpretatie die je anders wilt | `python3 scripts/decisions.py answer economie <id> "<antwoord>"` |
| openstaande vragen | `python3 scripts/decisions.py list economie --open` |

(Windows: overal `python` in plaats van `python3`.)

Daarna opnieuw `/generate`. Elke run krijgt een eigen map; niets wordt overschreven.

## 6. Veelgestelde vragen

**Kan ik een deel opnieuw draaien?** Ja, elke stap leest en schrijft bestanden in `runs/<id>/`; in Claude Code kun je bijvoorbeeld alleen stap 6 herhalen met `python3 scripts/export.py runs/<id>`.
**Ander vak?** `decisions.py init <vak>`, profiel invullen, `--subject <vak>`.
**Methode/boek als bron?** Komt in een volgende versie; het datamodel is er al op voorbereid (`specs/01-source-units.md §3`).
**Waar staat de verantwoording?** `specs/` — met name `00-overview.md` (wetenschappelijke ankers) en `04-verification.md` (de rubric).
