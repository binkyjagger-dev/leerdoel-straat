#!/usr/bin/env python3
"""Coverage matrix C1/C2 (specs/04 §1).

Usage: coverage.py <01_source_units.json> <groups.json> [<02_plan.json>] [--out coverage.json]

Forward:  every leaf unit has >= 1 group with status != rejected.
Backward: every group points to an existing leaf; source_quote verbatim in unit text.
Exit code 1 when coverage is incomplete (so the orchestrator can trigger a repair round).
"""
from __future__ import annotations

import sys
from collections import defaultdict

from common import BLOOM_ORDER, bloom_rank, load_json, normalise_ws, save_json


def compute(units_path: str, groups_path: str, plan_path: str | None = None) -> dict:
    src, grp = load_json(units_path), load_json(groups_path)
    plan = load_json(plan_path) if plan_path else None
    by_id = {u["unit_id"]: u for u in src["units"]}
    leaves = [u for u in src["units"] if u["is_leaf"]]
    planned = {p["unit_id"]: len(p["groups"]) for p in plan["units"]} if plan else {}

    groups_by_unit: dict[str, list] = defaultdict(list)
    orphan, mismatch = [], []
    for g in grp["groups"]:
        uid = g["unit_id"]
        if uid not in by_id or not by_id[uid]["is_leaf"]:
            orphan.append(g["group_id"])
            continue
        if normalise_ws(g["source_quote"]) not in normalise_ws(by_id[uid]["text"]):
            mismatch.append(g["group_id"])
        groups_by_unit[uid].append(g)

    per_unit, uncovered = [], []
    for u in leaves:
        gs = [g for g in groups_by_unit.get(u["unit_id"], []) if g.get("status") != "reject"]
        levels = sorted({c["bloom"] for g in gs for c in g["criteria"]}, key=bloom_rank)
        per_unit.append({"unit_id": u["unit_id"], "planned": planned.get(u["unit_id"]),
                         "produced": len(groups_by_unit.get(u["unit_id"], [])),
                         "accepted": len(gs), "bloom_levels": levels})
        if not gs:
            uncovered.append(u["unit_id"])

    dist = {lvl: 0 for lvl in BLOOM_ORDER}
    for g in grp["groups"]:
        for c in g["criteria"]:
            dist[c["bloom"]] += 1

    return {
        "units_total": len(leaves),
        "units_covered": len(leaves) - len(uncovered),
        "units_uncovered": uncovered,
        "groups_total": len(grp["groups"]),
        "groups_orphan": orphan,
        "groups_quote_mismatch": mismatch,
        "coverage_pct": round(100 * (len(leaves) - len(uncovered)) / max(len(leaves), 1), 1),
        "complete": not uncovered and not orphan and not mismatch,
        "bloom_distribution": dist,
        "per_unit": per_unit,
    }


def main(argv: list[str]) -> None:
    out = None
    if "--out" in argv:
        i = argv.index("--out")
        out = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    args = argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(2)
    cov = compute(*args[:3])
    if out:
        save_json(out, cov)
    print(f"[coverage] {cov['units_covered']}/{cov['units_total']} units covered ({cov['coverage_pct']}%), "
          f"{cov['groups_total']} groups, orphan={len(cov['groups_orphan'])}, quote_mismatch={len(cov['groups_quote_mismatch'])}")
    for uid in cov["units_uncovered"]:
        print(f"  UNCOVERED {uid}")
    for gid in cov["groups_orphan"]:
        print(f"  ORPHAN    {gid}")
    for gid in cov["groups_quote_mismatch"]:
        print(f"  QUOTE     {gid}")
    sys.exit(0 if cov["complete"] else 1)


if __name__ == "__main__":
    main(sys.argv)
