#!/usr/bin/env python3
"""T4 — realised matrix, Bloom mix and knob shares of the written toets (specs/33 §3 T4, specs/34 §4).

Usage: realized.py <run_dir>

Realised knobs are the merged labels of the blind labellers (34_labels.json, toets mode); a disputed field is left
out. Points and criteria per scorepunt come from 33_items; Bloom per scorepunt is the blueprint's, corrected by the
verifier's `bloom_realised` (V3) when 35_verification.json exists. Shares are computed exactly as for the blueprint
(shares.py) and compared with the order: Bloom ±5 pp, knobs ±10 pp, with the slack rule. `label_vs_plan` lists per
vraag every labelled value that differs from the blueprint (for the verifier, V4/V5). Writes 34_realized.json.
Fails only when the matrix is not met exactly (IT1 should have caught that).
"""
from __future__ import annotations

import sys
from pathlib import Path

from shares import as_shares, blueprint_records, group_points, ordered_levels, point_shares, tolerance_report
from tcommon import LABEL_KNOBS, Report, load_json, save_json
from toetsrun import ToetsRun


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    R = Path(argv[1])
    rep = Report("realized")
    run = ToetsRun(R)
    order, bp = run.order, run.blueprint()
    planned = blueprint_records(bp)
    pv = {r["vraag_id"]: r for r in planned}
    labels = {l["question_id"]: l for l in load_json(R / "34_labels.json")["labels"]} if (R / "34_labels.json").exists() else {}
    if not labels:
        rep.warn("RZ", "no 34_labels.json: realised knobs unknown (run label_merge.py --toets)")
    ver = load_json(R / "35_verification.json") if (R / "35_verification.json").exists() else {"vragen": []}
    v3 = {(v["vraag_id"], b["seq"]): b["bloom"] for v in ver["vragen"] for b in v.get("bloom_realised") or []}
    items = run.items()
    real, label_vs_plan, per_vraag = [], [], []
    for oid, it in items.items():
        for v in sorted(it["vragen"], key=lambda x: x["number"]):
            p = pv.get(v["vraag_id"])
            if not p:
                rep.fail("RZ", f"{v['vraag_id']} is in the items but not in the blueprint")
                continue
            bloom_plan = {s["seq"]: s["bloom"] for s in p["scorepunten"]}
            sps = [{"seq": s["seq"], "points": s["points"], "criterion_id": s["criterion_id"],
                    "bloom": v3.get((v["vraag_id"], s["seq"]), bloom_plan.get(s["seq"]))} for s in v["cv"]["scorepunten"]]
            l = labels.get(v["vraag_id"])
            conf = (l or {}).get("confidence", {})
            pat = l["pattern"] if l and conf.get("pattern") != "disputed" else None
            knobs = {k: (l.get(k) if l and conf.get(k) != "disputed" else None) for k in LABEL_KNOBS}
            real.append({"vraag_id": v["vraag_id"], "opgave_id": oid, "number": v["number"], "first": p["first"],
                         "points": v["points"], "pattern": pat, "knobs": knobs, "scorepunten": sps})
            diffs = {}
            if l:
                if pat is not None and pat != p["pattern"]:
                    diffs["pattern"] = {"plan": p["pattern"], "label": pat}
                for k in LABEL_KNOBS:
                    if conf.get(k) != "disputed" and knobs[k] != p["knobs"].get(k):
                        diffs[k] = {"plan": p["knobs"].get(k), "label": knobs[k]}
                for f, c in conf.items():
                    if c == "disputed":
                        diffs.setdefault(f, {"plan": p["knobs"].get(f, p["pattern"] if f == "pattern" else None), "label": "geschil"})
            if diffs:
                label_vs_plan.append({"vraag_id": v["vraag_id"], "differences": diffs})
            per_vraag.append({"vraag_id": v["vraag_id"], "points": v["points"], "pattern_plan": p["pattern"], "pattern_label": pat,
                              "knobs_plan": p["knobs"], "knobs_label": knobs, "combination": (l or {}).get("combination"),
                              "bloom": [s["bloom"] for s in sps], "bloom_changed_by_verifier":
                                  [s["seq"] for s in sps if (v["vraag_id"], s["seq"]) in v3 and v3[(v["vraag_id"], s["seq"])] != bloom_plan.get(s["seq"])]})
    sh_p = point_shares(planned, run.pidx, run.knobs)
    sh_r = point_shares(real, run.pidx, run.knobs)
    matrix = []
    gp = group_points(real, run.crit)
    for m in order.get("matrix", []):
        ok = gp.get(m["group_id"], 0) == m["points"]
        matrix.append({"group_id": m["group_id"], "ordered": m["points"], "realised": gp.get(m["group_id"], 0), "ok": ok})
        if not ok:
            rep.fail("RZ", f"matrix {m['group_id']}: realised {gp.get(m['group_id'], 0)}, ordered {m['points']}")
    devs = tolerance_report(order, sh_r)
    bm = order.get("bloom_mix") or {}
    bloom = {lv: {"ordered": bm.get(lv), "planned": as_shares(sh_p["bloom"]).get(lv, 0.0), "realised": as_shares(sh_r["bloom"]).get(lv, 0.0)}
             for lv in ordered_levels({**{k: 0 for k in bm}, **sh_p["bloom"], **sh_r["bloom"]})}
    knobs = {}
    for k in ["pattern"] + LABEL_KNOBS:
        tgt = (order.get("knobs") or {}).get(k)
        pp, rr = as_shares(sh_p["knobs"].get(k, {})), as_shares(sh_r["knobs"].get(k, {}))
        vals = list(dict.fromkeys([*(tgt.keys() if isinstance(tgt, dict) else []), *pp, *rr]))
        knobs[k] = {"ordered": tgt if tgt == "vrij" else None,
                    "values": {v: {"ordered": tgt.get(v, 0.0) if isinstance(tgt, dict) else None,
                                   "planned": pp.get(v, 0.0), "realised": rr.get(v, 0.0)} for v in vals}}
    out = {"matrix": matrix, "bloom": bloom, "knobs": knobs,
           "outside_tolerance": [d for d in devs if not d["slack"]], "within_slack": [d for d in devs if d["slack"]],
           "label_vs_plan": label_vs_plan, "per_vraag": per_vraag,
           "points": {"total": sum(r["points"] for r in real)}}
    save_json(R / "34_realized.json", out)
    for d in out["outside_tolerance"]:
        rep.warn("RZ", f"{d['what']} '{d['value']}': realised {d['share']:.0%}, ordered {d['ordered']:.0%} (outside tolerance; V9)")
    rep.info("RZ", f"{len(real)} vragen; {len(label_vs_plan)} with label ≠ plan; {len(out['outside_tolerance'])} shares outside tolerance")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
