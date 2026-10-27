#!/usr/bin/env python3
"""E6 — sample of exam links for the teacher (specs/23 §3 E6).

Usage: exam_sample.py <run_dir> [--high 10] [--low 10]

Reads 24_mappings.json, 21_exam_units.json, 20_criteria.json. Writes <run_dir>/output/steekproef.md:
seeded (run id) random `high` links plus `low`/`medium` links (all low first, then medium), each with the
scorepunt line from the correctievoorschrift, the quote and four J/N questions. Stays in the run folder.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from ecommon import Units, criteria_index, load_json


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    opt = lambda f, d: int(argv[argv.index(f) + 1]) if f in argv else d
    n_high, n_low = opt("--high", 10), opt("--low", 10)
    run = load_json(run_dir / "run.json")
    units = Units(run_dir)
    crit = criteria_index(load_json(run_dir / "20_criteria.json"))
    links = [l for l in load_json(run_dir / "24_mappings.json")["links"] if l["criterion_id"]]
    rng = random.Random(run["run_id"])
    high = [l for l in links if l["confidence"] == "high"]
    rest = sorted((l for l in links if l["confidence"] in ("low", "medium")),
                  key=lambda l: (l["confidence"] != "low", l["scorepunt_id"]))
    pick = rng.sample(high, min(n_high, len(high))) + rest[:n_low]

    L = [f"# Steekproef examenkoppelingen — {run['run_id']}", "",
         f"{len(pick)} koppelingen: {min(n_high, len(high))} hoge zekerheid (willekeurig, seed = run-id), "
         f"{min(n_low, len(rest))} lage/middelmatige. Vul per koppeling J/N in.", "",
         "| # | Vraag |", "|---|---|",
         "| 1 | **Juist criterium?** Toetst dit scorepunt dit succescriterium? |",
         "| 2 | **Bloom juist?** Het niveau dat het scorepunt vraagt |",
         "| 3 | **Citaat draagt de vraag?** |",
         "| 4 | **Bruikbaar?** Zou een leerling die dit criterium oefent iets hebben aan deze examenvraag? |", ""]
    for i, l in enumerate(pick, 1):
        sp, q, og = units.by_id[l["scorepunt_id"]], units.by_id[l["question_id"]], units.by_id[l["opgave_id"]]
        c = crit[l["criterion_id"]]
        js = " · ".join(f"{j}: {(v or {}).get('criterion_id') or '—'}" for j, v in l["judges"].items())
        L += [f"## {i}. {l['criterion_id']} × {l['exam_id']} vraag {q['number']} scorepunt {sp['seq']} "
              f"({l['points']} p) — {og.get('title') or ''}", "",
              f"**Criterium** ({c['bloom']}): {c['text_student'] or c['text_expert']}", "",
              f"**Scorepunt** ({sp['scoring']}): {sp['text'][:400]}", "",
              f"> {l['quote']}", "",
              f"**Bloom examen:** {l['bloom']} · **zekerheid:** {l['confidence']} · {js} · "
              f"verifier: {(l['verifier'] or '—')[:200]}"
              + (f" · raakt ook: {', '.join(l['also_touches'])}" if l["also_touches"] else "")
              + (f" · noot: {l['note']}" if l.get("note") else ""), "",
              "| Juist criterium? | Bloom juist? | Citaat draagt vraag? | Bruikbaar? |", "|---|---|---|---|",
              "|  |  |  |  |", "", "Opmerking: ", ""]
    out = run_dir / "output"
    out.mkdir(exist_ok=True)
    (out / "steekproef.md").write_text("\n".join(L), encoding="utf-8")
    print(f"[exam_sample] {len(pick)} links -> {out / 'steekproef.md'}")


if __name__ == "__main__":
    main(sys.argv)
