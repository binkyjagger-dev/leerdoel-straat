#!/usr/bin/env python3
"""Schema + structural validation for each pipeline artefact.

Usage:
  validate.py source_units <01_source_units.json>
  validate.py plan         <02_plan.json> <01_source_units.json>
  validate.py groups       <groups.json>  <01_source_units.json> [<02_plan.json>]
  validate.py verification <05_verification.json> <groups.json>

Rules: S1, S2, P1, G1, G2, G7 (see specs/04-verification.md). Bloom rules are in bloom_check.py.
"""
from __future__ import annotations

import sys
from collections import Counter

from common import Report, load_json, normalise_ws, validate_schema


def check_source_units(path: str) -> Report:
    rep = Report("validate:source_units")
    data = load_json(path)
    for e in validate_schema(data, "source_units.schema.json"):
        rep.fail("S1", e)
    if rep.failed:
        return rep
    units = data["units"]
    ids = [u["unit_id"] for u in units]
    for uid, n in Counter(ids).items():
        if n > 1:
            rep.fail("S2", f"duplicate unit_id {uid}")
    idset = set(ids)
    by_id = {u["unit_id"]: u for u in units}
    for u in units:
        if u["parent_id"] is not None and u["parent_id"] not in idset:
            rep.fail("S2", f"{u['unit_id']}: parent {u['parent_id']} does not exist")
        if u["is_leaf"] and len(u["text"].strip()) < 20:
            rep.fail("S2", f"{u['unit_id']}: leaf text shorter than 20 chars")
        # cycle check
        seen, cur = set(), u
        while cur["parent_id"] is not None:
            if cur["unit_id"] in seen:
                rep.fail("S2", f"cycle at {u['unit_id']}")
                break
            seen.add(cur["unit_id"])
            cur = by_id.get(cur["parent_id"])
            if cur is None:
                break
    leaves = [u for u in units if u["is_leaf"]]
    if not leaves:
        rep.fail("S2", "no leaf units")
    rep.info("S2", f"{len(units)} units, {len(leaves)} leaves")
    return rep


def check_plan(path: str, units_path: str) -> Report:
    rep = Report("validate:plan")
    plan, src = load_json(path), load_json(units_path)
    for e in validate_schema(plan, "plan.schema.json"):
        rep.fail("S1", e)
    if rep.failed:
        return rep
    leaves = {u["unit_id"] for u in src["units"] if u["is_leaf"]}
    planned = Counter(p["unit_id"] for p in plan["units"])
    for uid in leaves - set(planned):
        rep.fail("P1", f"leaf {uid} not planned")
    for uid, n in planned.items():
        if uid not in leaves:
            rep.fail("P1", f"planned unit {uid} is not a leaf (or does not exist)")
        if n > 1:
            rep.fail("P1", f"unit {uid} planned {n} times")
    for p in plan["units"]:
        slots = [g["slot"] for g in p["groups"]]
        if slots != list(range(1, len(slots) + 1)):
            rep.fail("P1", f"{p['unit_id']}: slots must be 1..n, got {slots}")
    rep.info("P1", f"{len(plan['units'])} units planned, {sum(len(p['groups']) for p in plan['units'])} groups")
    return rep


def check_groups(path: str, units_path: str, plan_path: str | None = None) -> Report:
    rep = Report("validate:groups")
    data, src = load_json(path), load_json(units_path)
    for e in validate_schema(data, "groups.schema.json"):
        rep.fail("S1", e)
    if rep.failed:
        return rep
    by_id = {u["unit_id"]: u for u in src["units"]}
    leaves = {u["unit_id"] for u in src["units"] if u["is_leaf"]}
    groups = data["groups"]
    gids = Counter(g["group_id"] for g in groups)
    for gid, n in gids.items():
        if n > 1:
            rep.fail("G1", f"duplicate group_id {gid}")
    per_unit = Counter(g["unit_id"] for g in groups)
    for g in groups:
        gid, uid = g["group_id"], g["unit_id"]
        if uid not in leaves:
            rep.fail("C2", f"{gid}: unit_id {uid} is not a leaf")
            continue
        if not gid.startswith(uid + "-"):
            rep.fail("G1", f"{gid}: group_id must start with '{uid}-'")
        if normalise_ws(g["source_quote"]) not in normalise_ws(by_id[uid]["text"]):
            rep.fail("G7", f"{gid}: source_quote not found verbatim in unit text")
        n = len(g["criteria"])
        if not 2 <= n <= 4:
            rep.fail("G2", f"{gid}: {n} criteria")
        for c in g["criteria"]:
            if not c["criterion_id"].startswith(gid + "-"):
                rep.fail("G1", f"{c['criterion_id']}: criterion_id must start with '{gid}-'")
    if plan_path:
        plan = load_json(plan_path)
        for p in plan["units"]:
            want, got = len(p["groups"]), per_unit.get(p["unit_id"], 0)
            if got != want:
                rep.fail("G1", f"{p['unit_id']}: planned {want} groups, produced {got}")
    rep.info("G1", f"{len(groups)} groups over {len(per_unit)} units")
    return rep


def check_verification(path: str, groups_path: str) -> Report:
    rep = Report("validate:verification")
    ver, grp = load_json(path), load_json(groups_path)
    for e in validate_schema(ver, "verification.schema.json"):
        rep.fail("S1", e)
    if rep.failed:
        return rep
    gids = {g["group_id"] for g in grp["groups"]}
    judged = {v["group_id"] for v in ver["groups"]}
    for gid in gids - judged:
        rep.fail("S1", f"group {gid} has no verdict")
    for gid in judged - gids:
        rep.fail("S1", f"verdict for unknown group {gid}")
    verdicts = Counter(v["verdict"] for v in ver["groups"])
    rep.info("S1", f"verdicts: {dict(verdicts)}")
    return rep


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        print(__doc__)
        sys.exit(2)
    kind, args = argv[1], argv[2:]
    dispatch = {"source_units": check_source_units, "plan": check_plan,
                "groups": check_groups, "verification": check_verification}
    if kind not in dispatch:
        print(__doc__)
        sys.exit(2)
    dispatch[kind](*args).print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
