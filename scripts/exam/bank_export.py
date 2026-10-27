#!/usr/bin/env python3
"""E6 — rebuild the exam bank's output from the whole bank (specs/25 §3).

Usage: bank_export.py <subject> [--bank <dir>]

Reads <bank>/register.json, criteria.json, source_units.json and links/<exam_id>.json for every registered
exam. Writes <bank>/output/: punten_per_criterium.csv, punten_per_leerdoel.csv, punten_per_domein.csv,
opzoekindex.csv, examenbank.xlsx (when openpyxl is installed), overzicht.md, bevindingen.md. Fails when an
exam column does not sum to the exam's max_score.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

from ecommon import ROOT, Report, bloom_rank, load_json

OUTSIDE = "buiten huidige syllabus"


def pct(p: float, mx: int) -> str:
    return f"{100 * p / mx:.1f}".replace(".", ",") if mx else ""


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(header)
        w.writerows(rows)


def write_xlsx(path: Path, sheets: list[tuple[str, list[str], list[list]]]) -> bool:
    try:
        from openpyxl import Workbook
    except ImportError:
        return False
    wb = Workbook()
    wb.remove(wb.active)
    for name, header, rows in sheets:
        ws = wb.create_sheet(name[:31])
        ws.append(header)
        for r in rows:
            ws.append([float(x.replace(",", ".")) if isinstance(x, str) and x.replace(",", "").replace(".", "").isdigit()
                       and "," in x else x for x in r])
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    wb.save(path)
    return True


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    subject = argv[1]
    bank = Path(argv[argv.index("--bank") + 1]) if "--bank" in argv else ROOT / "subjects" / subject / "examenbank"
    rep = Report("bank_export")
    reg = load_json(bank / "register.json")
    groups = load_json(bank / "criteria.json")["groups"]
    src = {u["unit_id"]: u for u in load_json(bank / "source_units.json")["units"]}
    exams = reg["exams"]
    eids = [e["exam_id"] for e in exams]
    mx = {e["exam_id"]: e["max_score"] for e in exams}
    recs = {eid: load_json(bank / "links" / f"{eid}.json")["scorepunten"] for eid in eids}

    def ancestor(uid: str, kind: str) -> dict | None:
        u = src.get(uid)
        while u is not None and u["kind"] != kind:
            u = src.get(u["parent_id"]) if u.get("parent_id") else None
        return u

    crit, order = {}, []
    for g in groups:
        sub, dom = ancestor(g["unit_id"], "subdomein"), ancestor(g["unit_id"], "domein")
        for c in g["criteria"]:
            crit[c["criterion_id"]] = {"group": g, "c": c, "sub": sub, "dom": dom}
            order.append(c["criterion_id"])

    pts = defaultdict(lambda: defaultdict(int))      # criterion -> exam -> points
    outside = defaultdict(int)                       # exam -> unlinked points
    for eid in eids:
        for r in recs[eid]:
            if r["criterion_id"] and r["criterion_id"] in crit:
                pts[r["criterion_id"]][eid] += r["points"]
            else:
                if r["criterion_id"]:
                    rep.warn("EX1", f"{r['scorepunt_id']}: criterion {r['criterion_id']} not in the bank's criteria")
                outside[eid] += r["points"]

    def cols(get) -> list:
        return [x for eid in eids for x in (get(eid), pct(get(eid), mx[eid]))]

    exam_head = [x for eid in eids for x in (f"{eid}_punten", f"{eid}_pct")]
    out = bank / "output"
    out.mkdir(parents=True, exist_ok=True)

    # per criterion
    rows_c = [[cid, crit[cid]["group"]["group_id"], crit[cid]["c"].get("text_student", ""), crit[cid]["c"]["bloom"],
               *cols(lambda e, cid=cid: pts[cid][e])] for cid in order]
    rows_c.append([OUTSIDE, "", "", "", *cols(lambda e: outside[e])])
    head_c = ["criterium_id", "leerdoel_id", "criterium_leerling", "criterium_bloom", *exam_head]
    write_csv(out / "punten_per_criterium.csv", head_c, rows_c)

    # per learning goal group
    rows_g = []
    for g in groups:
        ids = [c["criterion_id"] for c in g["criteria"]]
        sub = ancestor(g["unit_id"], "subdomein")
        rows_g.append([g["group_id"], g["goal"].get("text_student", ""), sub["code"] if sub else "",
                       *cols(lambda e, ids=ids: sum(pts[c][e] for c in ids))])
    rows_g.append([OUTSIDE, "", "", *cols(lambda e: outside[e])])
    head_g = ["leerdoel_id", "leerdoel_leerling", "subdomein", *exam_head]
    write_csv(out / "punten_per_leerdoel.csv", head_g, rows_g)

    # per subdomein and domein
    rows_d = []
    for kind, key in (("domein", "dom"), ("subdomein", "sub")):
        seen = []
        for cid in order:
            u = crit[cid][key]
            if u and u["unit_id"] not in seen:
                seen.append(u["unit_id"])
        for uid in seen:
            ids = [cid for cid in order if (crit[cid][key] or {}).get("unit_id") == uid]
            rows_d.append([kind, src[uid]["code"], src[uid].get("title") or "",
                           *cols(lambda e, ids=ids: sum(pts[c][e] for c in ids))])
    rows_d.append(["", OUTSIDE, "", *cols(lambda e: outside[e])])
    head_d = ["niveau", "code", "titel", *exam_head]
    write_csv(out / "punten_per_domein.csv", head_d, rows_d)

    # checks: every exam column sums to max_score (domein level and criterion level)
    for i, eid in enumerate(eids):
        col = 4 + 2 * i
        s_crit = sum(r[col] for r in rows_c)
        s_dom = sum(r[3 + 2 * i] for r in rows_d if r[0] in ("domein", ""))
        if s_crit != mx[eid] or s_dom != mx[eid]:
            rep.fail("EX2", f"{eid}: criterion column sums to {s_crit}, domein column to {s_dom}, max_score {mx[eid]}")

    # lookup index
    exm = {e["exam_id"]: e for e in exams}
    rank = {cid: i for i, cid in enumerate(order)}
    idx_rows = []
    for eid in eids:
        for r in recs[eid]:
            cid = r["criterion_id"]
            if not cid or cid not in crit:
                continue
            idx_rows.append((rank[cid], eids.index(eid), r["question_number"], r["scorepunt_seq"],
                             [cid, crit[cid]["group"]["group_id"], crit[cid]["c"].get("text_student", ""), eid,
                              exm[eid]["year"], exm[eid]["tijdvak"], r["opgave_number"], r["opgave_title"] or "",
                              r["question_number"], r["scorepunt_seq"], r["points"], r["bloom"],
                              crit[cid]["c"]["bloom"], r["quote"], ", ".join(r["also_touches"]),
                              r["confidence"] or ""]))
    idx_rows.sort(key=lambda x: x[:4])
    head_i = ["criterium_id", "leerdoel_id", "criterium_leerling", "examen", "jaar", "tijdvak", "opgave", "opgave_titel",
              "vraag", "scorepunt", "punten", "bloom_examen", "bloom_criterium", "citaat", "raakt_ook", "zekerheid"]
    write_csv(out / "opzoekindex.csv", head_i, [x[4] for x in idx_rows])

    xlsx = write_xlsx(out / "examenbank.xlsx", [("per criterium", head_c, rows_c), ("per leerdoel", head_g, rows_g),
                                               ("per domein", head_d, rows_d),
                                               ("opzoekindex", head_i, [x[4] for x in idx_rows])])

    # overzicht.md
    by_crit = defaultdict(list)
    for x in idx_rows:
        by_crit[x[4][0]].append(x[4])
    md = [f"# Examenbank {subject}", "",
          f"Criteria: run `{reg['criteria_run']}` · examens: " + ", ".join(f"{e} ({mx[e]} p)" for e in eids), ""]
    cur_dom, cur_g = None, None
    for cid in order:
        info = crit[cid]
        dom = info["dom"]
        if dom and dom["unit_id"] != cur_dom:
            cur_dom = dom["unit_id"]
            md += [f"## {dom['code']} {dom.get('title') or ''}".rstrip(), ""]
        g = info["group"]
        if g["group_id"] != cur_g:
            cur_g = g["group_id"]
            gp = " · ".join(f"{e}: {sum(pts[c['criterion_id']][e] for c in g['criteria'])} p" for e in eids)
            md += [f"### {g['group_id']} — {g['goal'].get('text_student', '')}", "", f"Punten: {gp}", ""]
        hits = by_crit.get(cid, [])
        where = "; ".join(f"{h[3]} vraag {h[8]} ({h[10]} p)" for h in hits) or "niet getoetst"
        md.append(f"- **{cid}** ({info['c']['bloom']}) {info['c'].get('text_student', '')} — {where}")
    md.append("")
    (out / "overzicht.md").write_text("\n".join(md), encoding="utf-8")

    # bevindingen.md
    bv = [f"# Bevindingen examenbank {subject}", "", f"## {OUTSIDE}", ""]
    for eid in eids:
        for r in recs[eid]:
            if not r["criterion_id"]:
                bv.append(f"- {eid} vraag {r['question_number']} scorepunt {r['scorepunt_seq']} ({r['points']} p)"
                          + (f": {r['note']}" if r.get("note") else ""))
    for label, sign in (("examen boven criterium", 1), ("examen onder criterium", -1)):
        bv += ["", f"## {label}", ""]
        for eid in eids:
            for r in recs[eid]:
                cid = r["criterion_id"]
                if cid in crit and r["bloom"]:
                    d = bloom_rank(r["bloom"]) - bloom_rank(crit[cid]["c"]["bloom"])
                    if d * sign > 0:
                        bv.append(f"- {cid} ({crit[cid]['c']['bloom']}) — {eid} vraag {r['question_number']} "
                                  f"scorepunt {r['scorepunt_seq']}: {r['bloom']}")
    never = [cid for cid in order if not any(pts[cid].values())]
    bv += ["", f"## nooit getoetst ({len(never)} van {len(order)} criteria)", ""]
    bv += [f"- {cid} ({crit[cid]['c']['bloom']}) {crit[cid]['c'].get('text_student', '')}" for cid in never]
    bv.append("")
    (out / "bevindingen.md").write_text("\n".join(bv), encoding="utf-8")

    linked = sum(sum(v.values()) for v in pts.values())
    rep.info("EX1", f"{len(eids)} exams, {len(idx_rows)} linked scorepunten, {linked} points linked, "
                    f"{sum(outside.values())} outside; {len(never)} criteria never tested; xlsx={'yes' if xlsx else 'no'}")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
