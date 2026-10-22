#!/usr/bin/env python3
"""Compare 14_mappings.json with the teacher's hand baseline (specs/14 §4).

Usage: compare_baseline.py <run_dir> <baseline.csv>

baseline.csv: criterium_id;paragraaf;gradatie;opmerking  (paragraaf = method code like 1.2, or unit_id like H1.2)
Scores on leert+oefent (and herhaalt) links; 'noemt' excluded unless the baseline marks it.
Writes output/vergelijking_nulmeting.md and prints precision/recall.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from mcommon import load_json


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        print(__doc__)
        sys.exit(2)
    run_dir, base = Path(argv[1]), Path(argv[2])
    method = load_json(run_dir / "11_method_units.json")
    by_code = {u["code"]: u["unit_id"] for u in method["units"] if u["kind"] == "paragraaf"}
    units = {u["unit_id"]: u for u in method["units"]}
    links = load_json(run_dir / "14_mappings.json")["links"]

    baseline = {}
    with open(base, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    for r in rows:
        cid = r["criterium_id"].strip()
        p = r["paragraaf"].strip()
        uid = by_code.get(p, p if p in units else None)
        if uid is None:
            print(f"  ! baseline paragraaf '{p}' not found in method units")
            continue
        baseline[(cid, uid)] = {"gradatie": r["gradatie"].strip().lower(), "opmerking": (r.get("opmerking") or "").strip()}

    straat = {(l["criterion_id"], l["unit_id"]): l for l in links}
    scored_b = {k: v for k, v in baseline.items() if v["gradatie"] != "noemt"}
    scored_s = {k: v for k, v in straat.items() if v["gradation"] != "noemt"}
    tp = set(scored_b) & set(scored_s)
    precision = len(tp) / len(scored_s) if scored_s else 0.0
    recall = len(tp) / len(scored_b) if scored_b else 0.0
    grad_agree = sum(1 for k in tp if baseline[k]["gradatie"] == straat[k]["gradation"])

    L = [f"# Vergelijking met nulmeting — {run_dir.name}", "",
         f"- Nulmeting: {len(scored_b)} koppelingen (excl. noemt) · straat: {len(scored_s)}",
         f"- **Precisie** {precision:.0%} ({len(tp)}/{len(scored_s)}) · **Recall** {recall:.0%} ({len(tp)}/{len(scored_b)})",
         f"- Gradatie gelijk op gedeelde koppelingen: {grad_agree}/{len(tp)}", "",
         "## Alleen in de straat (mogelijk onterecht)", "", "| criterium | paragraaf | gradatie | zekerheid | citaat |", "|---|---|---|---|---|"]
    for k in sorted(set(scored_s) - set(scored_b)):
        l = straat[k]
        L.append(f"| {k[0]} | {units[k[1]]['code']} | {l['gradation']} | {l['confidence']} | {l['quote'][:80]} |")
    L += ["", "## Alleen in de nulmeting (gemist)", "", "| criterium | paragraaf | gradatie | opmerking |", "|---|---|---|---|"]
    for k in sorted(set(scored_b) - set(scored_s)):
        L.append(f"| {k[0]} | {units[k[1]]['code']} | {baseline[k]['gradatie']} | {baseline[k]['opmerking']} |")
    L += ["", "## Gradatie verschilt", "", "| criterium | paragraaf | nulmeting | straat | zekerheid |", "|---|---|---|---|---|"]
    for k in sorted(tp):
        if baseline[k]["gradatie"] != straat[k]["gradation"]:
            L.append(f"| {k[0]} | {units[k[1]]['code']} | {baseline[k]['gradatie']} | {straat[k]['gradation']} | {straat[k]['confidence']} |")
    (run_dir / "output").mkdir(exist_ok=True)
    (run_dir / "output" / "vergelijking_nulmeting.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[baseline] precision {precision:.0%} recall {recall:.0%} gradation-agree {grad_agree}/{len(tp)} -> output/vergelijking_nulmeting.md")


if __name__ == "__main__":
    main(sys.argv)
