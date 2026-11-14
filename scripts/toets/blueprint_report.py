#!/usr/bin/env python3
"""T2b — the bouwplan for the teacher (specs/33 §3 T2b), Dutch Markdown.

Usage: blueprint_report.py <run_dir> [--subjects <dir>]

Reads 31_order.json, 32_blueprint.json, 32_blueprint.check.json (when present), 30_criteria.json, 30_patterns.json,
30_knobs.json and 30_reference_profile.json. Writes output/bouwplan.md: per opgave the context and per vraag the
points, pattern, criteria, Bloom and knobs; then the matrix, the Bloom mix and the knob shares **opdracht vs
bouwplan vs centraal examen**; then per leerdoel the tested and untested criteria; accepted deviations and open
check findings. Computes nothing an agent wrote in prose: shares come from shares.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

from shares import BLOOM_TOL, KNOB_TOL, as_shares, blueprint_records, group_points, ordered_levels, point_shares, tolerance_report
from tcommon import LABEL_KNOBS, MIX_LEVELS, load_json
from toetsrun import ToetsRun, subjects_opt

LEVEL_NL = {"4vwo": "4 VWO", "5vwo": "5 VWO", "6vwo": "6 VWO"}


def pct(x) -> str:
    return "–" if x is None else f"{x * 100:.0f} %"


def knob_cell(v) -> str:
    return "–" if v is None else str(v)


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    R = Path(argv[1])
    run = ToetsRun(R, subjects_opt(argv))
    order, bp = run.order, run.blueprint()
    recs = blueprint_records(bp)
    sh = point_shares(recs, run.pidx, run.knobs)
    dev = {(d["what"], d["value"]): d for d in tolerance_report(order, sh)}
    acc_fields = {a["field"].split(".")[-1] for a in bp.get("accepted_deviations") or []}

    def flag(what: str, d) -> str:
        if not d or d["slack"]:
            return ""
        key = "scorepunten" if what == "bloom" else what
        return " **buiten tolerantie (geaccepteerd)**" if key in acc_fields else " **buiten tolerantie**"
    ref = run.reference or {}
    refp = ref.get("pooled") or {}
    unknown = set(ref.get("unknown_knobs") or [])
    names = {c: p["name"] for c, p in run.pidx.items()}
    L = [f"# Bouwplan — {order.get('title') or 'toets'}", "",
         f"{run.subject} · {LEVEL_NL.get(order.get('level'), order.get('level'))} · {len(bp['opgaven'])} opgaven · "
         f"{len(recs)} vragen · {sum(r['points'] for r in recs)} punten · {ref.get('label') or 'referentie: geen'}", "",
         "Controleer het bouwplan. Je kunt een context vervangen, een vraag aanpassen of opnieuw laten plannen. "
         "Er wordt niets geschreven voordat je akkoord geeft.", ""]
    # opgaven
    for o in bp["opgaven"]:
        L += [f"## {o['opgave_id']} {o['title']}" + (f" (hergebruikt uit {o['reused_from']['toets_id']})" if o.get("reused_from") else ""),
              "", f"**Context:** {o['context']}  ", f"*Tags:* {', '.join(o['context_tags']) or '–'} · bronnen gepland: {o['sources_planned']}", "",
              "| vraag | p | patroon | criteria (punten, Bloom) | SOLO | route | stappen | bronnen | ruis | bewering | nieuw begrip | schema | voortbouwen | bedoeling |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for v in sorted(o["vragen"], key=lambda x: x["number"]):
            k = v["knobs"]
            crit = "; ".join(f"{s['criterion_id']} ({s['points']}, {s['bloom']})" for s in v["scorepunten"])
            bo = knob_cell(k.get("builds_on")) + (f" (vraag {', '.join(map(str, v['builds_on_vragen']))})" if v["builds_on_vragen"] else "")
            pat = v["pattern"] + "".join(f" {names[c]}" for c in v["pattern"].split("+") if c in names)
            L.append(f"| {v['number']} | {v['points']} | {pat} | {crit} | {knob_cell(k.get('solo'))} | {knob_cell(k.get('route'))} | "
                     f"{knob_cell(k.get('steps'))} | {knob_cell(k.get('sources'))} | {knob_cell(k.get('noise'))} | {knob_cell(k.get('claim'))} | "
                     f"{knob_cell(k.get('new_concept'))} | {knob_cell(k.get('schema'))} | {bo} | {v['intent']} |")
        L.append("")
    # matrix
    gp = group_points(recs, run.crit)
    L += ["## Toetsmatrijs", "", "| leerdoel | opdracht | bouwplan | |", "|---|---|---|---|"]
    for m in order.get("matrix", []):
        goal = run.groups.get(m["group_id"], {}).get("goal", {})
        L.append(f"| {m['group_id']} {goal.get('text_student') or goal.get('text_expert') or ''} | {m['points']} | "
                 f"{gp.get(m['group_id'], 0)} | {'✓' if gp.get(m['group_id'], 0) == m['points'] else '**afwijking**'} |")
    L.append("")
    # Bloom
    planned = as_shares(sh["bloom"])
    bm = order.get("bloom_mix")
    L += ["## Bloom-mix (per punt)", "", "| niveau | opdracht | bouwplan | centraal examen |", "|---|---|---|---|"]
    for lv in MIX_LEVELS:
        if not (bm or {}).get(lv) and lv not in planned and lv not in (refp.get("bloom") or {}):
            continue
        mark = flag("bloom", dev.get(("bloom", lv)))
        L.append(f"| {lv} | {pct((bm or {}).get(lv)) if bm else 'geen mix'} | {pct(planned.get(lv, 0))}{mark} | "
                 f"{pct((refp.get('bloom') or {}).get(lv, {}).get('share')) if 'bloom' in refp else 'onbekend'} |")
    L += ["", f"Tolerantie ±{BLOOM_TOL * 100:.0f} procentpunt; één scorepunt speling.", ""]
    # knobs
    L += ["## Knoppen (per punt, alleen over de vragen waar de knop telt)", ""]
    for k in ["pattern"] + LABEL_KNOBS:
        kd = run.knobs[k]
        target = (order.get("knobs") or {}).get(k)
        pl = as_shares(sh["knobs"].get(k, {}))
        L += [f"### {kd['label']}" + (" — vrij (planner kiest)" if target == "vrij" else ""), "",
              "| waarde | opdracht | bouwplan | centraal examen |", "|---|---|---|---|"]
        vals = list(dict.fromkeys([*(target.keys() if isinstance(target, dict) else []), *pl.keys()]))
        for v in vals:
            mark = flag(k, dev.get((k, v)))
            refv = "onbekend" if k in unknown or k not in refp else pct((refp[k].get(v) or {}).get("share", 0))
            label = f"{v} {names[v]}" if k == "pattern" and v in names else v
            L.append(f"| {label} | {pct(target.get(v, 0)) if isinstance(target, dict) else 'vrij'} | {pct(pl.get(v, 0))}{mark} | {refv} |")
        if not vals:
            L.append("| – | – | – | – |")
        L.append("")
    L += [f"Tolerantie ±{KNOB_TOL * 100:.0f} procentpunt; één vraag speling.", ""]
    # coverage
    L += ["## Getoetste en niet-getoetste criteria per leerdoel", ""]
    tested = {}
    for r in recs:
        for s in r["scorepunten"]:
            tested.setdefault(s["criterion_id"], 0)
            tested[s["criterion_id"]] += s["points"]
    excl = set(order.get("criteria_exclude") or [])
    for m in order.get("matrix", []):
        g = run.groups.get(m["group_id"])
        if not g:
            continue
        L.append(f"**{m['group_id']}** {g['goal'].get('text_student') or ''}")
        for c in g["criteria"]:
            cid = c["criterion_id"]
            state = f"getoetst ({tested[cid]} p)" if cid in tested else ("uitgesloten" if cid in excl else "**niet getoetst**")
            L.append(f"- {cid} ({c['bloom']}): {state} — {c.get('text_student') or c['text_expert']}")
        L.append("")
    acc = bp.get("accepted_deviations") or []
    if acc:
        L += ["## Geaccepteerde afwijkingen", ""] + [f"- {a['target']} {a['field']} = {a['value']}: {a.get('note') or ''}" for a in acc] + [""]
    ck = R / "32_blueprint.check.json"
    if ck.exists():
        items = [i for i in load_json(ck)["items"] if i["severity"] in ("fail", "warn")]
        L += ["## Controle (blueprint_check)", ""]
        L += [f"- {i['severity']} {i['rule']}: {i['message']}" for i in items] or ["- geen fouten of waarschuwingen"]
        L.append("")
    if bp.get("planner_notes"):
        L += ["## Toelichting planner", "", bp["planner_notes"], ""]
    out = R / "output" / "bouwplan.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[blueprint_report] {out}")


if __name__ == "__main__":
    main(sys.argv)
