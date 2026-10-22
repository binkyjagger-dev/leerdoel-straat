#!/usr/bin/env python3
"""M6 — export CSVs and reports (specs/15).

Usage: export_mappings.py <run_dir> [--baseline <baseline.csv>] [--sample 20]
"""
from __future__ import annotations

import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from mcommon import load_json

CSV_KW = dict(delimiter=";", quoting=csv.QUOTE_ALL)


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    sample_n = int(argv[argv.index("--sample") + 1]) if "--sample" in argv else 20
    out = run_dir / "output"
    out.mkdir(exist_ok=True)
    run = load_json(run_dir / "run.json")
    method = load_json(run_dir / "11_method_units.json")
    units = {u["unit_id"]: u for u in method["units"]}
    mp = load_json(run_dir / "14_mappings.json")
    links, findings = mp["links"], mp.get("findings", [])
    crit = {}
    for g in load_json(run_dir / "10_criteria.json")["groups"]:
        for c in g["criteria"]:
            crit[c["criterion_id"]] = {"group": g, "c": c}
    mid = method["method"]["method_id"]

    # 1. methode_eenheden.csv
    with open(out / "methode_eenheden.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, **CSV_KW)
        w.writerow(["methode_id", "eenheid_id", "soort", "code", "titel", "ouder_id", "pagina_van", "pagina_tot", "volgorde"])
        for u in method["units"]:
            w.writerow([mid, u["unit_id"], u["kind"], u["code"], u.get("title") or "", u["parent_id"] or "", u.get("page_from") or "", u.get("page_to") or "", u.get("order") or ""])

    # 2. koppelingen_paragraaf.csv
    cols = ["run_id", "bron_run", "methode_id", "criterium_id", "group_id", "unit_id", "criterium_leerling", "criterium_bloom",
            "eenheid_id", "code", "titel", "pagina", "behandeling", "gradatie", "citaat", "zekerheid",
            "beoordelaar_a", "beoordelaar_b", "verifier", "opmerking", "status"]
    with open(out / "koppelingen_paragraaf.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, **CSV_KW)
        w.writeheader()
        for l in sorted(links, key=lambda l: (l["criterion_id"], units[l["unit_id"]].get("order") or 0)):
            c = crit[l["criterion_id"]]
            u = units[l["unit_id"]]
            w.writerow({"run_id": run["run_id"], "bron_run": run.get("from_run", ""), "methode_id": mid,
                        "criterium_id": l["criterion_id"], "group_id": l["group_id"], "unit_id": c["group"]["unit_id"],
                        "criterium_leerling": c["c"].get("text_student") or c["c"]["text_expert"], "criterium_bloom": c["c"]["bloom"],
                        "eenheid_id": u["unit_id"], "code": u["code"], "titel": u.get("title") or "", "pagina": l.get("quote_page") or u.get("page_from") or "",
                        "behandeling": l["treatment"], "gradatie": l["gradation"], "citaat": l["quote"], "zekerheid": l["confidence"],
                        "beoordelaar_a": l["judges"].get("A", {}).get("treatment", ""), "beoordelaar_b": l["judges"].get("B", {}).get("treatment", ""),
                        "verifier": l.get("verifier") or "", "opmerking": l.get("note") or "", "status": l["status"]})

    # 4. reports
    def ctext(cid):
        c = crit[cid]["c"]
        return c.get("text_student") or c["text_expert"]

    gaps = [f for f in findings if f.get("criterion_id") and f["finding"] in ("alleen geoefend", "alleen genoemd", "niet in deze methode")]
    L = [f"# Gaten in de methode — {run['run_id']}", "", f"Criteria in scope zonder *leert*-paragraaf ({len(gaps)}).", ""]
    for kind in ("alleen geoefend", "alleen genoemd", "niet in deze methode"):
        rows = [f for f in gaps if f["finding"] == kind]
        if rows:
            L += [f"## {kind.capitalize()} ({len(rows)})", ""]
            for f in rows:
                L.append(f"- **{f['criterion_id']}** — {ctext(f['criterion_id'])}")
            L.append("")
    (out / "gaten_methode.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    outside = [f for f in findings if f.get("unit_id") and f["finding"].startswith("buiten syllabus")]
    L = [f"# Stof buiten de syllabus — {run['run_id']}", "", f"Paragrafen zonder koppeling aan een criterium ({len(outside)}).", ""]
    for f in outside:
        u = units[f["unit_id"]]
        L.append(f"- **{u['code']} {u.get('title') or ''}** (p. {u.get('page_from') or '?'}) — begrippen: {', '.join(u.get('concepts') or []) or '—'}")
    (out / "buiten_syllabus.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # dekking_methode.md
    by_para = defaultdict(list)
    for l in links:
        by_para[l["unit_id"]].append(l)
    L = [f"# Dekking methode — {run['run_id']}", "", f"- Methode: {method['method']['title']} (`{mid}`)", f"- Bron-run leerdoelen: {run.get('from_run', '')}",
         f"- Criteria in scope: {len({c['criterion_id'] for c in load_json(run_dir / '12_candidates.json')['per_criterion']})} · paragrafen in scope: {len(load_json(run_dir / '12_candidates.json')['scope_paragraphs'])}",
         f"- Koppelingen: {len(links)} — " + ", ".join(f"{k} {v}" for k, v in Counter(l['gradation'] for l in links).items()),
         f"- Zekerheid: " + ", ".join(f"{k} {v}" for k, v in Counter(l['confidence'] for l in links).items()), ""]
    snap = run_dir / "decisions_snapshot.json"
    if snap.exists():
        L += ["## Toegepaste beslissingen", ""] + [f"- {d['id']}: {d['effective_answer']}" for d in load_json(snap)["decisions"]] + [""]
    L += ["## Per paragraaf", "", "| Paragraaf | leert | herhaalt | oefent | noemt |", "|---|---|---|---|---|"]
    for u in sorted((u for u in method["units"] if u["kind"] == "paragraaf"), key=lambda u: u.get("order") or 0):
        ls = by_para.get(u["unit_id"], [])
        cnt = Counter(l["gradation"] for l in ls)
        cell = lambda g: ", ".join(l["criterion_id"] for l in ls if l["gradation"] == g) or "—"
        L.append(f"| {u['code']} {u.get('title') or ''} | {cell('leert')} | {cell('herhaalt')} | {cell('oefent')} | {cnt.get('noemt', 0)} |")
    other = [f for f in findings if f["finding"] not in ("alleen geoefend", "alleen genoemd", "niet in deze methode") and not f["finding"].startswith("buiten syllabus")]
    if other:
        L += ["", "## Overige bevindingen", ""] + [f"- {f.get('criterion_id') or ''} {f.get('unit_id') or ''}: {f['finding']}" for f in other]
    (out / "dekking_methode.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # steekproef.md
    random.seed(run["run_id"])
    high = [l for l in links if l["confidence"] == "high" and l["gradation"] != "noemt"]
    low = [l for l in links if l["confidence"] != "high" or (l.get("verifier") or "").startswith("dispute")]
    pick = random.sample(high, min(sample_n // 2, len(high))) + random.sample(low, min(sample_n - sample_n // 2, len(low)))
    L = [f"# Steekproef koppelingen — {run['run_id']}", "", f"{len(pick)} koppelingen: {min(sample_n//2, len(high))} hoge zekerheid, {len(pick) - min(sample_n//2, len(high))} lage/omstreden. Vul per koppeling J/N in.", "",
         "| # | Vraag |", "|---|---|", "| 1 | **Terecht?** Bedient deze paragraaf dit criterium? |", "| 2 | **Gradatie juist?** leert / herhaalt / oefent / noemt |",
         "| 3 | **Citaat draagt het bewijs?** |", "| 4 | **Zou een leerling hier geholpen zijn?** |", ""]
    for i, l in enumerate(pick, 1):
        u = units[l["unit_id"]]
        L += [f"## {i}. {l['criterion_id']} × {u['code']} {u.get('title') or ''} (p. {l.get('quote_page') or u.get('page_from') or '?'})", "",
              f"**Criterium:** {ctext(l['criterion_id'])}", "", f"**Gradatie:** {l['gradation']} · **zekerheid:** {l['confidence']} · A: {l['judges'].get('A',{}).get('treatment','')} · B: {l['judges'].get('B',{}).get('treatment','')} · verifier: {l.get('verifier') or '—'}", "",
              f"> {l['quote']}", "", "| Terecht? | Gradatie juist? | Citaat draagt bewijs? | Leerling geholpen? |", "|---|---|---|---|", "|  |  |  |  |", "", "Opmerking: ", ""]
    (out / "steekproef.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"[export] {len(links)} links -> {out}; gaps {len(gaps)}, buiten syllabus {len(outside)}, steekproef {len(pick)}")


if __name__ == "__main__":
    main(sys.argv)
