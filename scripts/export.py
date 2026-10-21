#!/usr/bin/env python3
"""Exporter (specs/05): CSV per criterion, CSV per group, coverage report, doubt list.

Usage: export.py <run_dir>

Reads from <run_dir>: run.json, 01_source_units.json, 02_plan.json, 04_groups_student.json,
05_verification.round*.json (latest), 01_ingest_notes.md (optional), bloom-check warnings (optional).
Writes to <run_dir>/output/.
"""
from __future__ import annotations

import csv
import glob
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from common import BLOOM_ORDER, corrected_concept, exam_for, load_json
from coverage import compute as compute_coverage

CSV_COLUMNS = [
    "run_id", "source_id", "source_type", "domein_code", "domein_titel", "subdomein_code", "subdomein_titel",
    "examen", "unit_id", "unit_tekst", "group_id", "leerdoel_expert", "leerdoel_leerling", "leerdoel_bloom",
    "criterium_id", "criterium_volgorde", "criterium_expert", "criterium_leerling", "criterium_bloom",
    "criterium_bloom_werkwoord", "bron_citaat", "kernbegrippen", "status", "verificatie_opmerking",
]


def ancestors(by_id: dict, uid: str) -> list[dict]:
    chain, cur = [], by_id.get(uid)
    while cur is not None and cur["parent_id"] is not None:
        cur = by_id.get(cur["parent_id"])
        if cur:
            chain.append(cur)
    return list(reversed(chain))  # top-down


def latest_verification(run_dir: Path) -> dict | None:
    files = sorted(glob.glob(str(run_dir / "05_verification.round*.json")))
    if not files:
        f = run_dir / "05_verification.json"
        return load_json(f) if f.exists() else None
    return load_json(files[-1])


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    out = run_dir / "output"
    out.mkdir(exist_ok=True)

    run = load_json(run_dir / "run.json") if (run_dir / "run.json").exists() else {"run_id": run_dir.name}
    src = load_json(run_dir / "01_source_units.json")
    plan_path = run_dir / "02_plan.json"
    groups = load_json(run_dir / "04_groups_student.json")["groups"]
    ver = latest_verification(run_dir)
    by_id = {u["unit_id"]: u for u in src["units"]}

    verdict, issues, fixes = {}, defaultdict(list), {}
    if ver:
        for v in ver["groups"]:
            verdict[v["group_id"]] = v["verdict"]
            fixes[v["group_id"]] = v.get("suggested_fix")
            for i in v["issues"]:
                issues[v["group_id"]].append(f"{i['rule']}: {i['reason']}")

    # --- CSV per criterion
    rows = []
    for g in groups:
        anc = ancestors(by_id, g["unit_id"])
        dom = anc[0] if anc else {}
        sub = anc[1] if len(anc) > 1 else {}
        status = g.get("status") or verdict.get(g["group_id"], "")
        for i, c in enumerate(g["criteria"], 1):
            rows.append({
                "run_id": run.get("run_id", ""), "source_id": src["source"]["source_id"],
                "source_type": src["source"]["source_type"],
                "domein_code": dom.get("code", ""), "domein_titel": dom.get("title", ""),
                "subdomein_code": sub.get("code", ""), "subdomein_titel": sub.get("title", ""),
                "examen": exam_for(by_id, g["unit_id"]) or "",
                "unit_id": g["unit_id"], "unit_tekst": by_id[g["unit_id"]]["text"],
                "group_id": g["group_id"],
                "leerdoel_expert": g["goal"]["text_expert"], "leerdoel_leerling": g["goal"].get("text_student", ""),
                "leerdoel_bloom": g["goal"].get("bloom", ""),
                "criterium_id": c["criterion_id"], "criterium_volgorde": i,
                "criterium_expert": c["text_expert"], "criterium_leerling": c.get("text_student", ""),
                "criterium_bloom": c["bloom"], "criterium_bloom_werkwoord": c["bloom_verb"],
                "bron_citaat": g["source_quote"], "kernbegrippen": " | ".join(corrected_concept(t, src) for t in g.get("concepts") or []), "status": status,
                "verificatie_opmerking": " | ".join(issues.get(g["group_id"], [])),
            })
    with open(out / "leerdoelgroepen.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)

    # --- CSV per group
    gcols = ["run_id", "domein_code", "subdomein_code", "unit_id", "examen", "group_id", "groep_n_van_m", "leerdoel_leerling", "leerdoel_bloom",
             "succescriteria_leerling", "kernbegrippen", "bloom_per_criterium", "status"]
    per_unit_ids = defaultdict(list)
    for g in groups:
        per_unit_ids[g["unit_id"]].append(g["group_id"])
    with open(out / "leerdoelgroepen_per_leerdoel.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=gcols, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writeheader()
        for g in groups:
            anc = ancestors(by_id, g["unit_id"])
            w.writerow({
                "run_id": run.get("run_id", ""),
                "domein_code": anc[0].get("code", "") if anc else "",
                "subdomein_code": anc[1].get("code", "") if len(anc) > 1 else "",
                "unit_id": g["unit_id"], "examen": exam_for(by_id, g["unit_id"]) or "", "group_id": g["group_id"],
                "groep_n_van_m": f"{per_unit_ids[g['unit_id']].index(g['group_id']) + 1} van {len(per_unit_ids[g['unit_id']])}",
                "leerdoel_leerling": g["goal"].get("text_student", ""), "leerdoel_bloom": g["goal"].get("bloom", ""),
                "succescriteria_leerling": " | ".join(c.get("text_student", "") for c in g["criteria"]),
                "kernbegrippen": " | ".join(corrected_concept(t, src) for t in g.get("concepts") or []),
                "bloom_per_criterium": " | ".join(c["bloom"] for c in g["criteria"]),
                "status": g.get("status") or verdict.get(g["group_id"], ""),
            })

    # --- coverage report
    cov = compute_coverage(str(run_dir / "01_source_units.json"), str(run_dir / "04_groups_student.json"),
                           str(plan_path) if plan_path.exists() else None)
    lines = [f"# Dekkingsrapport — {run.get('run_id', run_dir.name)}", "",
             f"- Bron: {src['source']['title']} (`{src['source']['source_id']}`)",
             f"- Gegenereerd: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
             f"- Verificatierondes: {ver['round'] if ver else 'n.v.t.'}",
             f"- Eindtermen: {cov['units_total']} · gedekt: {cov['units_covered']} ({cov['coverage_pct']}%)",
             f"- Leerdoelgroepen: {cov['groups_total']} · criteria: {sum(cov['bloom_distribution'].values())}"]
    alloc = src["source"].get("exam_allocation")
    leaves = [u for u in src["units"] if u["is_leaf"]]
    if alloc:
        dist = defaultdict(int)
        for u in leaves:
            dist[exam_for(by_id, u["unit_id"]) or "onbekend"] += 1
        parts = [f"{k}: {dist[k]}" for k in ("CE", "CE+SE", "SE", "onbekend") if dist.get(k)]
        lines.append(f"- Examen (eindtermen): {' · '.join(parts)}")
    else:
        lines.append("- Examen: de bron heeft geen toedelingstabel CE/SE; kolom `examen` is leeg")
    if cov["concepts_total"]:
        n_cov = cov["concepts_total"] - len(cov["concepts_uncovered"])
        lines.append(f"- Kernbegrippen uit de bron: {cov['concepts_total']} · bij een leerdoel: {n_cov} ({cov['concept_coverage_pct']}%)")
    lines.append("")
    if cov["concepts_uncovered"]:
        lines += ["## Begrippen zonder leerdoel", "",
                  "Begrippen uit de begrippenlijst van de bron die geen leerdoelgroep noemt (C3).", "",
                  "| Eenheid | Begrip |", "|---|---|"]
        lines += [f"| {c['unit_id']} | {corrected_concept(c['concept'], src)} |" for c in cov["concepts_uncovered"]]
        lines.append("")
    if alloc:
        rest = [r for r in alloc if not r["ingested"]]
        if rest:
            lines += ["## Niet in deze bron", "",
                      "(Sub)domeinen die de toedelingstabel wel noemt maar die deze bron niet specificeert — "
                      "stof voor het schoolexamen uit een andere bron.", "",
                      "| Code | Titel | CE | SE |", "|---|---|---|---|"]
            lines += [f"| {r['code']} | {r.get('title') or ''} | {'x' if r['in_ce'] else ''} | {'x' if r['must_in_se'] else ''} |" for r in rest]
            lines.append("")
    if cov["units_uncovered"]:
        lines += ["## Niet gedekt", ""] + [f"- {u}" for u in cov["units_uncovered"]] + [""]
    snap_path = run_dir / "decisions_snapshot.json"
    snap = load_json(snap_path)["decisions"] if snap_path.exists() else []
    if snap:
        lines += ["## Toegepaste vakbeslissingen", "", "| id | status | vraag | antwoord |", "|---|---|---|---|"]
        for d in snap:
            st = "voorlopig (voorstel)" if d["provisional"] else "beantwoord"
            lines += [f"| {d['id']} | {st} | {d['question']} | {d['effective_answer']} |"]
        lines.append("")
    lines += ["## Bloom-verdeling (criteria)", "", "| Niveau | Aantal |", "|---|---|"]
    lines += [f"| {lvl} | {cov['bloom_distribution'][lvl]} |" for lvl in BLOOM_ORDER]
    lines += ["", "## Per eindterm", "", "| Domein | Eindterm | Examen | Gepland | Gemaakt | Geaccepteerd | Bloom-niveaus |", "|---|---|---|---|---|---|---|"]
    for pu in cov["per_unit"]:
        anc = ancestors(by_id, pu["unit_id"])
        lines.append(f"| {anc[0].get('code', '') if anc else ''} | {pu['unit_id']} | {exam_for(by_id, pu['unit_id']) or ''} | {pu['planned'] or ''} | "
                     f"{pu['produced']} | {pu['accepted']} | {', '.join(pu['bloom_levels'])} |")
    (out / "coverage_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # --- doubt list
    d = [f"# Twijfellijst — {run.get('run_id', run_dir.name)}", ""]
    open_groups = [g for g in groups if (g.get("status") or verdict.get(g["group_id"])) in ("revise", "reject")]
    if open_groups:
        d += ["## Leerdoelgroepen die na de laatste ronde nog niet goed zijn", ""]
        for g in open_groups:
            st = g.get("status") or verdict.get(g["group_id"])
            d.append(f"- **{g['group_id']}** ({st}) — {g['goal'].get('text_student') or g['goal']['text_expert']}")
            for i in issues.get(g["group_id"], []):
                d.append(f"  - {i}")
            if fixes.get(g["group_id"]):
                d.append(f"  - *Voorstel:* {fixes[g['group_id']]}")
        d.append("")
    if cov["units_uncovered"]:
        d += ["## Eindtermen zonder leerdoelgroep", ""] + [f"- {u}: {by_id[u]['text'][:120]}…" for u in cov["units_uncovered"]] + [""]
    if cov["concepts_uncovered"]:
        by_u = defaultdict(list)
        for c in cov["concepts_uncovered"]:
            by_u[c["unit_id"]].append(c["concept"])
        d += ["## Begrippen uit de bron zonder leerdoel (C3)", ""]
        d += [f"- {uid}: {', '.join(cs)}" for uid, cs in by_u.items()] + [""]
    if ver and ver.get("unit_findings"):
        d += ["## Bevindingen op eindterm-niveau", ""] + [f"- {f['unit_id']}: {f['finding']}" for f in ver["unit_findings"]] + [""]
    bloom_report = run_dir / "bloom_check.json"
    if bloom_report.exists():
        warns = [i for i in load_json(bloom_report)["items"] if i["severity"] == "warn"]
        if warns:
            d += ["## Bloom-waarschuwingen (G6)", ""] + [f"- {w['message']}" for w in warns] + [""]
    open_dec = [d for d in snap if d["provisional"]]
    if open_dec:
        d += ["## Openstaande vakbeslissingen (voorlopig op voorstel gedraaid)", ""]
        for x in open_dec:
            units = ", ".join(x.get("affects_units") or []) or "—"
            d += [f"- **{x['id']}** — {x['question']}", f"  - *Voorlopig:* {x['effective_answer']}  (eenheden: {units})"]
        d.append("")
    notes = run_dir / "01_ingest_notes.md"
    if notes.exists() and notes.read_text(encoding="utf-8").strip():
        d += ["## Opmerkingen uit de ingest", "", notes.read_text(encoding="utf-8").strip(), ""]
    if len(d) == 2:
        d.append("Geen openstaande twijfels.")
    (out / "doubt_list.md").write_text("\n".join(d) + "\n", encoding="utf-8")

    print(f"[export] {len(rows)} criterion rows, {len(groups)} groups -> {out}")
    print(f"[export] coverage {cov['coverage_pct']}% · open doubts: {len(open_groups)} groups, {len(cov['units_uncovered'])} uncovered units")


if __name__ == "__main__":
    main(sys.argv)
