# leerdoel-straat

Een Claude Code-straat die van een syllabus (v1: CvTE economie VWO) **leerdoelgroepen** maakt:
leerdoel + 2–4 succescriteria, Bloom-niveau per criterium (leerdoel = hoogste niveau), in
leerlingentaal ("Ik kan …"), gekoppeld aan eindtermen, met dekking in twee richtingen geverifieerd.

Uitvoer per run: `leerdoelgroepen.csv`, `leerdoelgroepen_per_leerdoel.csv`, `coverage_report.md`, `doubt_list.md`.

## Hoe het werkt

```
syllabus.pdf → ingest → planner → generator (parallel per eindterm) → leerlingentaal → verifier ⇄ herstel (max 2) → export
```

Zes rollen, elk een subagent met eigen prompt (`.claude/agents/`), aan elkaar geknoopt door de
slash command `/generate` (`.claude/commands/generate.md`). Tussen elke stap draait een Python-validator;
Bloom-berekening, dekkingsmatrix en CSV zijn deterministisch. De verifier draait altijd in een schone context.

Wetenschappelijke ankers: herziene Bloom (Anderson & Krathwohl), constructive alignment (Biggs),
learning intentions & success criteria (Clarke, Hattie, Wiliam), observeerbare doelen (Mager).
Zie `specs/00-overview.md`.

## Starten

```bash
pip install --break-system-packages jsonschema
# poppler (pdftotext) of PyMuPDF beschikbaar hebben
claude            # in deze map
> /generate input/syllabus-economie-vwo.pdf
```

Scripts los testen op de fixture: `bash tests/run_fixture.sh`.

## Status

v0.1 — spec en scaffold. Nog niet gedraaid op een echte syllabus. Zie `specs/00-overview.md §6` voor de definition of done.
