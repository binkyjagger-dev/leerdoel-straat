#!/usr/bin/env python3
"""Merge per-unit generator files into one groups file.

Usage: merge_groups.py <run_dir>

Reads <run_dir>/03_groups_raw/<unit_id>.json (ignores *.roundN.json backups),
writes <run_dir>/03_groups_raw.json with groups sorted by unit order in 01_source_units.json.
"""
from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

from common import load_json, save_json


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    src = load_json(run_dir / "01_source_units.json")
    order = {u["unit_id"]: i for i, u in enumerate(src["units"])}
    groups = []
    for f in sorted(glob.glob(str(run_dir / "03_groups_raw" / "*.json"))):
        if re.search(r"\.round\d+\.json$", f):
            continue
        groups.extend(load_json(f)["groups"])
    groups.sort(key=lambda g: (order.get(g["unit_id"], 10**6), g["group_id"]))
    save_json(run_dir / "03_groups_raw.json", {"groups": groups})
    print(f"[merge] {len(groups)} groups from {len(set(g['unit_id'] for g in groups))} units → {run_dir / '03_groups_raw.json'}")


if __name__ == "__main__":
    main(sys.argv)
