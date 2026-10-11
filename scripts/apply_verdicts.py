#!/usr/bin/env python3
"""Write verifier verdicts into the student groups file and list what needs repair.

Usage: apply_verdicts.py <run_dir> <round>

- sets `status` on every group in 04_groups_student.json from 05_verification.round<round>.json
- writes <run_dir>/repair.round<round>.json:
    { "units": [ { "unit_id", "reason": "uncovered" | "verdicts",
                   "groups": [ { "group_id", "verdict", "issues": [...], "suggested_fix" } ] } ] }
- prints the unit ids to repair; exit code 0 when nothing to repair, 1 otherwise
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from common import load_json, save_json


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        print(__doc__)
        sys.exit(2)
    run_dir, rnd = Path(argv[1]), int(argv[2])
    ver = load_json(run_dir / f"05_verification.round{rnd}.json")
    gpath = run_dir / "04_groups_student.json"
    data = load_json(gpath)
    verdicts = {v["group_id"]: v for v in ver["groups"]}

    repair: dict[str, dict] = {}
    for g in data["groups"]:
        v = verdicts.get(g["group_id"])
        if v is None:
            continue
        g["status"] = v["verdict"]
        if v["verdict"] in ("revise", "reject"):
            entry = repair.setdefault(g["unit_id"], {"unit_id": g["unit_id"], "reason": "verdicts", "groups": []})
            entry["groups"].append({"group_id": g["group_id"], "verdict": v["verdict"],
                                    "issues": v["issues"], "suggested_fix": v.get("suggested_fix")})
    for uid in ver.get("coverage", {}).get("units_uncovered", []):
        repair.setdefault(uid, {"unit_id": uid, "reason": "uncovered", "groups": []})
    for f in ver.get("unit_findings", []):
        if f["unit_id"] not in repair and "uncovered" in f["finding"].lower():
            repair[f["unit_id"]] = {"unit_id": f["unit_id"], "reason": "uncovered", "groups": []}

    save_json(gpath, data)
    out = {"round": rnd, "units": sorted(repair.values(), key=lambda r: r["unit_id"])}
    save_json(run_dir / f"repair.round{rnd}.json", out)
    counts = defaultdict(int)
    for g in data["groups"]:
        counts[g.get("status")] += 1
    print(f"[apply_verdicts] round {rnd}: {dict(counts)}; units to repair: {len(repair)}")
    for r in out["units"]:
        print(f"  {r['unit_id']} ({r['reason']}, {len(r['groups'])} groups)")
    sys.exit(0 if not repair else 1)


if __name__ == "__main__":
    main(sys.argv)
