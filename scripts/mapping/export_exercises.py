#!/usr/bin/env python3
"""M9 export — exercise links and Bloom reports (specs/15 §3–4, part B).

Usage: export_exercises.py <run_dir> [--sample 20]

Writes output/koppelingen_opgaven.csv, output/bloom_gaten.md, output/steekproef_opgaven.md.
Run export_mappings.py afterwards so gaten_methode.md sees the exercise links.
"""
from __future__ import annotations

import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from mcommon import load_json, read_text

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
    mid = method["method"]["method_id"]
    crit = {}
    for g in load_json(run_dir / "10_criteria.json")["groups"]:
        for c in g["criteria"]:
            crit[c["criterion_id"]] = c
    data = load_json(run_dir / "18_ex_mappings.json")
    links, findings = data["links"], data["findings"]
    order = {u["unit_id"]: u.get("order") or 0 for u in method["units"]}
    links.sort(key=lambda l: (order.get(l["paragraph_id"], 0), l["unit_id"], l["criterion_id"]))

    def ctext(cid):
        c = crit[cid]
        return c.get("text_student") or c["text_expert"]

    # koppelingen_opgaven.csv
    cols = ["run_id", "methode_id", "criterium_id", "criterium_leerling", "criterium_bloom", "eenheid_id", "opgave_code",
            "deelvraag_code", "paragraaf_id", "pagina", "bloom", "bloom_werkwoord", "citaat", "antwoord_gecontroleerd",
            "zekerheid", "beoordelaar_a", "beoordelaar_b", "verifier", "opmerking", "status"]
    with open(out / "koppelingen_opgaven.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, **CSV_KW)
        w.writerow(cols)
        for l in links:
            u = units[l["unit_id"]]
            opg = units.get(u["parent_id"], {})
            ja, jb = l["judges"].get("A"), l["judges"].get("B")
            w.writerow([run["run_id"], mid, l["criterion_id"], ctext(l["criterion_id"]), crit[l["criterion_id"]]["bloom"],
                        l["unit_id"], opg.get("code", ""), u["code"], l["paragraph_id"], u.get("page_from") or "",
                        l["bloom"], l.get("bloom_verb") or "", l["quote"], "ja" if l["answer_checked"] else "nee",
                        l["confidence"], ja["bloom"] if ja else "", jb["bloom"] if jb else "", l.get("verifier") or "",
                        l.get("note") or "", l["status"]])

    # bloom_gaten.md
    def unit_label(uid):
        u = units[uid]
        return f"{u['code']} (p. {u.get('page_from') or '?'})"

    by_kind = defaultdict(list)
    for f_ in findings:
        by_kind[f_["finding"].split(":")[0].split(" (")[0]].append(f_)
    L = [f"# Bloom-gaten en oefenstof — {run['run_id']}", "",
         f"- Opgavekoppelingen: {len(links)} op {len({l['unit_id'] for l in links})} deelvragen · "
         f"zekerheid: " + ", ".join(f"{k} {v}" for k, v in Counter(l['confidence'] for l in links).items()),
         "- Bloom van de opgaven: " + ", ".join(f"{k} {v}" for k, v in Counter(l['bloom'] for l in links).items()), ""]
    sections = [("bloom niet bereikt", "Bloomniveau niet bereikt in de opgaven"), ("niet geoefend", "Criteria in scope zonder opgave"),
                ("geoefend zonder uitleg", "Geoefend zonder uitleg in de tekst"), ("oefent vóór uitleg", "Oefent vóór uitleg"),
                ("oefenstof buiten syllabus", "Oefenstof buiten de syllabus")]
    for key, title in sections:
        rows = by_kind.get(key, [])
        L += [f"## {title} ({len(rows)})", ""]
        for f_ in rows:
            if f_.get("criterion_id"):
                where = f" — {unit_label(f_['unit_id'])}" if f_.get("unit_id") else ""
                detail = f_["finding"][len(key):].lstrip(": ") if f_["finding"] != key else ""
                L.append(f"- **{f_['criterion_id']}** ({crit[f_['criterion_id']]['bloom']}){where}{' — ' + detail if detail else ''} — {ctext(f_['criterion_id'])}")
            else:
                q = read_text(run_dir, units[f_["unit_id"]].get("text_ref")).strip().splitlines()
                L.append(f"- {unit_label(f_['unit_id'])} — {q[-1][:120] if q else ''}")
        L.append("")
    ver_p = run_dir / "19_ex_verification.json"
    vf = load_json(ver_p).get("findings", []) if ver_p.exists() else []
    if vf:
        L += [f"## Bevindingen controleur ({len(vf)})", ""]
        for f_ in vf:
            L.append("- " + (f_ if isinstance(f_, str) else " · ".join(str(v) for v in f_.values() if v)))
        L.append("")
    (out / "bloom_gaten.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # steekproef_opgaven.md
    random.seed(run["run_id"] + "-ex")
    high = [l for l in links if l["confidence"] == "high"]
    low = [l for l in links if l["confidence"] != "high" or (l.get("verifier") or "").startswith("dispute")]
    pick = random.sample(high, min(sample_n // 2, len(high)))
    pick += random.sample([l for l in low if l not in pick], min(sample_n - len(pick), len([l for l in low if l not in pick])))
    L = [f"# Steekproef opgavekoppelingen — {run['run_id']}", "", f"{len(pick)} koppelingen. Vul per koppeling J/N in.", "",
         "| # | Vraag |", "|---|---|", "| 1 | **Terecht?** Oefent deze deelvraag dit criterium? |", "| 2 | **Bloom juist?** |",
         "| 3 | **Citaat toont de vraag?** |", ""]
    for i, l in enumerate(pick, 1):
        u = units[l["unit_id"]]
        ja, jb = l["judges"].get("A"), l["judges"].get("B")
        L += [f"## {i}. {l['criterion_id']} × opgave {u['code']} (p. {u.get('page_from') or '?'})", "",
              f"**Criterium** ({crit[l['criterion_id']]['bloom']}): {ctext(l['criterion_id'])}", "",
              f"**Bloom opgave:** {l['bloom']} ({l.get('bloom_verb') or '—'}) · **zekerheid:** {l['confidence']} · "
              f"A: {ja['bloom'] if ja else '—'} · B: {jb['bloom'] if jb else '—'} · verifier: {l.get('verifier') or '—'}", "",
              f"> {l['quote']}", "", f"Opmerking straat: {l.get('note') or '—'}", "",
              "| Terecht? | Bloom juist? | Citaat? |", "|---|---|---|", "|  |  |  |", "", "Opmerking: ", ""]
    (out / "steekproef_opgaven.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[export_exercises] {len(links)} exercise links -> {out}; findings { {k: len(v) for k, v in by_kind.items()} }; steekproef {len(pick)}")


if __name__ == "__main__":
    main(sys.argv)
